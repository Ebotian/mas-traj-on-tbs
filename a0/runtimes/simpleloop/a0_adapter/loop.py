"""The SimpleLoop search policy: propose, score with E*, select by frozen argmax.

Frozen definition (open_world_plan_review.typ:605-614):

    c_0    = baseline
    c_{t+1} = Agent(c_t, H_t)
    c*_t   = argmax_{i <= t} E(c_i)
    parent_{t+1} = c*_t

Forbidden: archive/QD, evolved harness or guidance, multi-island, learned operator
selection, external retrieval (A1 stage), undeclared special prompt. Nothing in
this module does any of those; the only state carried across iterations is the
running champion (`c*_t`) and the raw history `H_t`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import traces as trace_mod
from .candidates import CandidateSet
from .estareval import EStarEvaluator, EXIT_ERROR, EXIT_INVALID, EXIT_OK
from .policy import (
    TIE_BREAK_LEXICOGRAPHIC_ID,
    PolicyError,
    choose,
    fr_for_events,
    primary_field,
    scalar_of,
)
from .solvers import Proposal, Solver, SolverError

SELECTION_POLICY = "argmax_{i<=t} E(c_i)"


@dataclass
class Budget:
    T_wall_sec: float = 3600.0
    N_evaluatorCalls: int = 200
    concurrency: int = 1

    def as_dict(self) -> dict:
        return {
            "T_wall_sec": self.T_wall_sec,
            "N_evaluatorCalls": self.N_evaluatorCalls,
            "concurrency_cap": self.concurrency,
        }


@dataclass
class RunOutcome:
    exit_code: int
    iterations: int
    champion_id: str | None
    champion_scalar: float | None
    scored_candidates: int
    failure_counts: dict
    trace_paths: dict
    stopped_because: str
    history: list[dict] = field(default_factory=list)


class SimpleLoop:
    def __init__(
        self,
        *,
        candidate_set: CandidateSet,
        evaluator: EStarEvaluator,
        solver: Solver,
        writer: trace_mod.TraceWriter,
        policy: dict,
        epsilon: float,
        budget: Budget,
        run_dir: Path,
        max_iterations: int = 64,
        inject_scores: dict | None = None,
        check_point: str | None = None,
    ) -> None:
        self.candidate_set = candidate_set
        self.evaluator = evaluator
        self.solver = solver
        self.writer = writer
        self.policy = policy
        self.field = primary_field(policy)
        self.epsilon = epsilon
        self.budget = budget
        self.run_dir = Path(run_dir)
        self.max_iterations = max_iterations
        self.inject_scores = dict(inject_scores or {})
        self.injected_mode = bool(self.inject_scores)
        self.solver_failure: str | None = None
        self.check_point = check_point or (
            "SimpleLoop A0.2: c*_t = argmax_{i<=t} E(c_i) with frozen tie-break"
        )
        self.fr = fr_for_events(policy, injected=self.injected_mode)
        self.history: list[dict] = []
        self.scalar_running: dict[str, float | None] = {}
        self._proposal_paths: dict[str, Path] = {}

    # -- one iteration ----------------------------------------------------
    def _evaluate(self, proposal: Proposal, *, iteration: int,
                  iteration_started: float) -> dict:
        candidate = proposal.as_candidate()
        result = self.evaluator.evaluate(candidate, iteration=iteration)

        if result.exit_code == EXIT_OK:
            failure_stage = "none"
            failure_detail = None
        elif result.exit_code == EXIT_INVALID:
            failure_stage = trace_mod.failure_stage_for(EXIT_INVALID, result.failure_kind)
            failure_detail = (
                f"E* exit 2 status=invalid failure.kind={result.failure_kind}: "
                f"{result.failure_message}"
            )
        elif result.exit_code == EXIT_ERROR:
            failure_stage = trace_mod.failure_stage_for(EXIT_ERROR, result.failure_kind)
            failure_detail = (
                f"E* exit 3 status=error failure.kind={result.failure_kind}: "
                f"{result.failure_message}"
            )
        else:
            failure_stage = "evaluator_failed"
            failure_detail = f"E* exited {result.exit_code} with no Outcome; stderr={result.stderr[:400]}"

        try:
            e_star_scalar = scalar_of(result.outcome, self.field)
        except PolicyError as exc:
            e_star_scalar = None
            failure_stage = "evaluator_failed"
            failure_detail = str(exc)

        injected = self.inject_scores.get(candidate.candidate_id)
        search_signal = injected if self.injected_mode else e_star_scalar
        if self.injected_mode:
            failure_note = (
                f"injected={injected!r} e_star={e_star_scalar!r} "
                f"source=--inject-scores"
            )
            failure_detail = (
                f"{failure_detail} | {failure_note}" if failure_detail else failure_note
            )

        fields = result.fields or {}
        event_id = self.writer.score(
            iteration=iteration,
            candidate_id=candidate.candidate_id,
            parent_id=proposal.detail.get("parent_id"),
            outcome=result.outcome,
            fields=fields,
            search_signal=search_signal,
            evaluator_evidence=trace_mod.evaluator_evidence_for(result),
            fr=self.fr,
            failure_stage=failure_stage,
            failure_detail=failure_detail,
        )
        self.writer.resource(
            iteration=iteration,
            candidate_id=candidate.candidate_id,
            parent_id=proposal.detail.get("parent_id"),
            # `scope: "iteration"` must mean the whole iteration, not just the E*
            # call: with the agent lane the proposal dominates (one real run spent
            # 394.45 s in the solver and 0.096 s in E*), and a T_wall that omits it
            # under-reports the substrate's cost by four orders of magnitude.
            T_wall={"value_sec": round(time.monotonic() - iteration_started, 6),
                    "clock": "monotonic", "scope": "iteration"},
            N_evaluatorCalls=self.evaluator.calls,
            concurrency={"cap": self.budget.concurrency, "observed_max": 1},
            secondary={
                "N_modelCalls": proposal.model_calls,
                "T_in": proposal.tokens_in,
                "T_out": proposal.tokens_out,
                "C_usd": proposal.cost_usd,
            },
            budget_hard=self.budget.as_dict(),
            failure_stage=failure_stage,
            failure_detail=failure_detail,
        )
        record = {
            "iteration": iteration,
            "candidate_id": candidate.candidate_id,
            "solution_sha256": candidate.solution_sha256,
            "proposal_source": proposal.source,
            "e_star_exit_code": result.exit_code,
            "e_star_status": result.status,
            "e_star_failure_kind": result.failure_kind,
            "e_star_scalar": e_star_scalar,
            "injected_scalar": injected,
            "search_signal": search_signal,
            "fields": fields,
            # The evaluator's own structural measurements. For an `invalid`
            # candidate these carry a *nominal* sum_radii that must never be
            # mistaken for a score (the A0.2 "highest nominal score must lose"
            # control reads them).
            "structure": (result.outcome or {}).get("structure"),
            "failure_stage": failure_stage,
            "failure_detail": failure_detail,
            "score_event_id": event_id,
            "evaluation_sec": round(result.wall_sec, 6),
            "proposal_sec": round(proposal.latency_sec, 6),
            "tokens_total": (proposal.detail or {}).get("tokens_total"),
            "iteration_sec": round(time.monotonic() - iteration_started, 6),
        }
        self.history.append(record)
        self.scalar_running[candidate.candidate_id] = search_signal
        self._proposal_paths[candidate.candidate_id] = proposal.path
        return record

    def _select(self, *, iteration: int, current_candidate_id: str,
                parent_id: str | None) -> tuple[str | None, dict]:
        chosen, tie_note = choose(self.scalar_running)
        considered = [
            {"candidate_id": row["candidate_id"], "search_signal": row["search_signal"]}
            for row in self.history
        ]
        source_event = None
        if chosen is not None:
            source_event = next(
                (row["score_event_id"] for row in self.history if row["candidate_id"] == chosen),
                None,
            )
        unscored = sorted(
            cid for cid, s in self.scalar_running.items() if s is None
        )
        reason_bits = [
            f"argmax over {len(self.scalar_running)} candidate(s) seen so far",
            f"chosen={chosen!r}",
        ]
        if unscored:
            reason_bits.append(
                f"excluded {len(unscored)} unscored candidate(s) "
                f"(E* status != ok, no scalar): {unscored}"
            )
        if tie_note:
            reason_bits.append(tie_note)
        if self.injected_mode:
            reason_bits.append(
                "search signal came from --inject-scores, not from F_r = scalar(E*)"
            )
        event_id = self.writer.selection(
            iteration=iteration,
            candidate_id=current_candidate_id,
            parent_id=parent_id,
            policy=SELECTION_POLICY,
            chosen_candidate_id=chosen,
            considered=considered,
            reason="; ".join(reason_bits),
            tie_break=TIE_BREAK_LEXICOGRAPHIC_ID if tie_note else None,
            source_score_event_id=source_event,
            check_point=self.check_point,
        )
        return chosen, {"event_id": event_id, "chosen": chosen, "tie": tie_note, "source": source_event}

    # -- the loop ---------------------------------------------------------
    def execute(self) -> RunOutcome:
        started = time.monotonic()
        champion: str | None = None
        champion_scalar: float | None = None
        stopped_because = "solver_exhausted"
        iteration = 0
        candidate: dict | None = None

        baseline = self.candidate_set.baseline()
        while iteration < self.max_iterations:
            iteration_started = time.monotonic()
            elapsed = iteration_started - started
            if elapsed > self.budget.T_wall_sec:
                stopped_because = "budget_exhausted:T_wall_sec"
                break
            if self.evaluator.calls >= self.budget.N_evaluatorCalls:
                stopped_because = "budget_exhausted:N_evaluatorCalls"
                break

            input_candidate = (
                self.candidate_set_or_proposal(candidate) if candidate is not None else None
            )
            try:
                if iteration == 0:
                    proposal = self.solver.initial_proposal(baseline, iteration=0)
                else:
                    proposal = self.solver.propose(
                        iteration=iteration,
                        input_candidate=input_candidate,
                        parent=self.candidate_set_or_proposal(champion),
                        history=self.history,
                    )
            except SolverError as exc:
                stopped_because = f"solver_failed:{exc}"
                self.solver_failure = str(exc)
                # The search lane failed to produce a candidate at all. That is a
                # result, not a crash: record it at the stratum where it stopped
                # (plan:628) so the search-failure rate is countable, then exit 8.
                self.writer.resource(
                    iteration=iteration,
                    candidate_id=(candidate["candidate_id"] if candidate else baseline.candidate_id),
                    parent_id=champion,
                    T_wall={"value_sec": round(time.monotonic() - started, 6),
                            "clock": "monotonic", "scope": "iteration"},
                    N_evaluatorCalls=self.evaluator.calls,
                    concurrency={"cap": self.budget.concurrency, "observed_max": 1},
                    secondary={"N_modelCalls": None, "T_in": None, "T_out": None, "C_usd": None},
                    budget_hard=self.budget.as_dict(),
                    failure_stage="search_failed",
                    failure_detail=f"solver lane {self.solver.lane!r} produced no proposal: {exc}",
                )
                break
            if proposal is None:
                stopped_because = "solver_exhausted"
                break

            if iteration == 0 and proposal.candidate_id != baseline.candidate_id:
                raise PolicyError(
                    f"c_0 must be the C* baseline {baseline.candidate_id!r}, "
                    f"the solver returned {proposal.candidate_id!r}"
                )
            proposal.detail["parent_id"] = champion
            proposal.detail["input_candidate_id"] = (
                candidate["candidate_id"] if candidate else None
            )

            record = self._evaluate(
                proposal, iteration=iteration, iteration_started=iteration_started
            )
            chosen, sel = self._select(
                iteration=iteration,
                current_candidate_id=proposal.candidate_id,
                parent_id=champion,
            )
            if chosen is not None:
                champion = chosen
                champion_scalar = self.scalar_running[chosen]
            candidate = record
            iteration += 1

        # Final run-scope resource line: the adapter's own counters, and no
        # budget_hard (a run-scope line exceeding its own declared budget is a
        # validation error, and this line is exactly where a run reports that).
        final_wall = time.monotonic() - started
        self.writer.resource(
            iteration=max(iteration - 1, 0),
            candidate_id=(candidate["candidate_id"] if candidate else "none"),
            parent_id=None,
            T_wall={"value_sec": round(final_wall, 6), "clock": "monotonic", "scope": "run"},
            N_evaluatorCalls=self.evaluator.calls,
            concurrency={"cap": self.budget.concurrency, "observed_max": 1},
            secondary=None,
            budget_hard=None,
        )

        scored = sum(1 for s in self.scalar_running.values() if s is not None)
        counts: dict[str, int] = {}
        for row in self.history:
            if row["failure_stage"] != "none":
                counts[row["failure_stage"]] = counts.get(row["failure_stage"], 0) + 1
        if self.solver_failure is not None:
            counts["search_failed"] = counts.get("search_failed", 0) + 1

        if scored == 0 or stopped_because.startswith("solver_failed"):
            # Exit 8: the runtime never produced an evaluable candidate — either
            # every candidate it did produce stopped at an earlier stratum, or the
            # search lane produced nothing at all.
            exit_code = 8
        elif stopped_because.startswith("budget_exhausted"):
            exit_code = 7
        else:
            exit_code = 0

        return RunOutcome(
            exit_code=exit_code,
            iterations=iteration,
            champion_id=champion,
            champion_scalar=champion_scalar,
            scored_candidates=scored,
            failure_counts=counts,
            trace_paths={k: str(v) for k, v in self.writer.paths.items()},
            stopped_because=stopped_because,
            history=self.history,
        )

    def candidate_set_or_proposal(self, record_or_id):
        """Resolve either a history record or a candidate id to a Candidate."""
        if record_or_id is None:
            return None
        cid = record_or_id if isinstance(record_or_id, str) else record_or_id["candidate_id"]
        for row in self.history:
            if row["candidate_id"] == cid:
                return self._candidate_for(row)
        for cand in self.candidate_set.candidates:
            if cand.candidate_id == cid:
                return cand
        return None

    def _candidate_for(self, row: dict):
        from .candidates import Candidate

        path = self._proposal_paths.get(row["candidate_id"])
        if path is None:
            return None
        return Candidate(
            candidate_id=row["candidate_id"],
            path=path,
            solution_sha256=row["solution_sha256"],
            role="proposal",
            kind="solver_output",
            note=row["proposal_source"],
            expected_status=None,
            raw={},
        )


def write_run_meta(run_dir: Path, payload: dict) -> Path:
    path = Path(run_dir) / "run_meta.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return path
