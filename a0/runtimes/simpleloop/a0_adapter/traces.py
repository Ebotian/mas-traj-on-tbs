"""Trace emission: the three jsonl streams of a0/contract/trace_schema.md.

Trace files carry no host paths, no absolute directories and no runtime-internal
state that the schema does not declare (the schema is closed: unknown top-level
fields are rejected). Everything machine-local goes into `run_meta.json` and
`adapter.md` instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .policy import PolicyError, canonical_bytes, load_policy

TRACE_KINDS = ("score", "selection", "resource")

FAILURE_STAGE_BY_E_STAR_VERDICT = {
    (0, None): "none",
    (2, None): "verify_failed",
    (3, "candidate_import_failed"): "resolve_failed",
    (3, "non_deterministic"): "verify_failed",
    (3, "runtime_budget_exceeded"): "timeout",
    (3, "candidate_call_raised"): "evaluator_failed",
    (3, "child_terminated_early"): "evaluator_failed",
}


def failure_stage_for(exit_code: int, failure_kind: str | None) -> str:
    """Frozen E* verdict -> failure_stage mapping (policy/simpleloop.policy.json).

    The trace schema fixes the enum but not this mapping; SimpleLoop declares it
    rather than inventing a stage per call site.

    One extension for T1: the max-cut ``E*`` gives a timeout **its own exit code**
    (4, ``a0/tasks/maxcut/e_star.py:99``) instead of reporting it as exit 3 with
    ``failure.kind = runtime_budget_exceeded``, so the same trace stage has to be
    reachable from code 4. This is the mapping ``a0/tasks/maxcut/DEVIATIONS.md``
    D-T1-8 declares; the plumbing table above is untouched.
    """
    if exit_code == 0:
        return "none"
    if exit_code == 2:
        return "verify_failed"
    if exit_code == 4:
        return "timeout"
    return FAILURE_STAGE_BY_E_STAR_VERDICT.get((exit_code, failure_kind), "evaluator_failed")


def _safe_id(text: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "._:-") else "_" for ch in str(text))


@dataclass
class TraceWriter:
    """One writer per run; `event_seq` is monotonic across all three streams."""

    run_dir: Path
    runtime: str
    run_id: str
    task: str
    eid_star: str
    eid_r: dict
    theta_E: dict
    policy: dict = field(default_factory=load_policy)
    kinds: tuple[str, ...] = TRACE_KINDS
    _seq: int = 0
    _handles: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def __post_init__(self) -> None:
        trace_dir = Path(self.run_dir) / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir = trace_dir
        for kind in self.kinds:
            path = trace_dir / f"{self.runtime}.{self.run_id}.{kind}.jsonl"
            self._handles[kind] = path.open("w", encoding="utf-8")
        self.paths = {k: self.trace_dir / f"{self.runtime}.{self.run_id}.{k}.jsonl" for k in self.kinds}

    def close(self) -> None:
        for fh in self._handles.values():
            fh.close()

    def failure_stage_counts(self) -> dict:
        """Counts by `(run_id, iteration, candidate_id)` unit, as trace_validate.py does."""
        units: dict[tuple, str] = {}
        for event in self.events:
            stage = event.get("failure_stage") or "none"
            units[(event["run_id"], event["iteration"], event["candidate_id"])] = stage
        counts: dict[str, int] = {}
        for stage in units.values():
            counts[stage] = counts.get(stage, 0) + 1
        return counts

    # -- envelope ---------------------------------------------------------
    def _envelope(self, kind: str, *, iteration: int, candidate_id: str,
                  parent_id: str | None, failure_stage: str,
                  failure_detail: str | None = None) -> dict:
        if failure_stage != "none" and not failure_detail:
            raise PolicyError(f"failure_stage={failure_stage} requires failure_detail")
        seq = self._seq
        self._seq += 1
        # `event_seq` is in the id so that two events about the same (iteration,
        # candidate) — e.g. the per-iteration resource line and the run-scope
        # summary line — can never collide.
        event = {
            "trace": kind,
            "event_id": _safe_id(f"{self.run_id}.{kind[0]}{seq}.i{iteration}.{candidate_id}"),
            "event_seq": seq,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": self.run_id,
            "task": self.task,
            "runtime": self.runtime,
            "iteration": iteration,
            "candidate_id": candidate_id,
            "parent_id": parent_id,
            "eid_star": self.eid_star,
            "eid_r": self.eid_r,
            "theta_E": self.theta_E,
            "failure_stage": failure_stage,
            "failure_detail": failure_detail,
        }
        return event

    def _write(self, event: dict) -> str:
        kind = event["trace"]
        self.events.append(event)
        handle = self._handles.get(kind)
        if handle is None:
            return event["event_id"]
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()
        return event["event_id"]

    # -- trace 1: score ---------------------------------------------------
    def score(self, *, iteration: int, candidate_id: str, parent_id: str | None,
              outcome: dict | None, fields: dict, search_signal,
              evaluator_evidence: dict, fr: dict, failure_stage: str,
              failure_detail: str | None = None, event_id: str | None = None) -> str:
        event = self._envelope(
            "score", iteration=iteration, candidate_id=candidate_id, parent_id=parent_id,
            failure_stage=failure_stage, failure_detail=failure_detail,
        )
        body = {
            "outcome": {"fields": fields, "cardinality": len(fields)},
            "fr": fr,
            "search_signal": search_signal,
            "evaluator_evidence": evaluator_evidence,
        }
        for banned in ("scalar", "scalarized", "search_signal", "score_scalar"):
            if banned in fields:
                raise PolicyError(f"outcome.fields must not carry a scalarized key {banned!r}")
        event.update(body)
        if event_id:
            event["event_id"] = event_id
        return self._write(event)

    # -- trace 2: selection ----------------------------------------------
    def selection(self, *, iteration: int, candidate_id: str, parent_id: str | None,
                  policy: str, chosen_candidate_id: str | None, considered: list[dict],
                  reason: str, tie_break: str | None, source_score_event_id: str | None,
                  check_point: str | None, extra: dict | None = None,
                  failure_stage: str = "none", failure_detail: str | None = None) -> str:
        considered_ids = {c["candidate_id"] for c in considered}
        if chosen_candidate_id is not None and chosen_candidate_id not in considered_ids:
            raise PolicyError(
                f"selection chose {chosen_candidate_id!r} which is not among considered "
                f"{sorted(considered_ids)}"
            )
        event = self._envelope(
            "selection", iteration=iteration, candidate_id=candidate_id, parent_id=parent_id,
            failure_stage=failure_stage, failure_detail=failure_detail,
        )
        event["selection"] = {
            "policy": policy,
            "chosen_candidate_id": chosen_candidate_id,
            "considered": considered,
            "reason": reason,
            "tie_break": tie_break,
            "source_score_event_id": source_score_event_id,
            "check_point": check_point,
        }
        return self._write(event)

    # -- trace 3: resource ------------------------------------------------
    def resource(self, *, iteration: int, candidate_id: str, parent_id: str | None,
                 T_wall: dict, N_evaluatorCalls: int, concurrency: dict,
                 secondary: dict | None = None, budget_hard: dict | None = None,
                 failure_stage: str = "none", failure_detail: str | None = None) -> str:
        event = self._envelope(
            "resource", iteration=iteration, candidate_id=candidate_id, parent_id=parent_id,
            failure_stage=failure_stage, failure_detail=failure_detail,
        )
        event["T_wall"] = T_wall
        event["N_evaluatorCalls"] = N_evaluatorCalls
        event["concurrency"] = concurrency
        if secondary is not None:
            event["secondary"] = secondary
        if budget_hard is not None:
            event["budget_hard"] = budget_hard
        return self._write(event)


def evaluator_evidence_for(result, *, evaluator=None) -> dict:
    """Guard the false-green traps.

    SimpleLoop never synthesizes a score and never reuses a cache, so every real
    E* measurement is `ok` regardless of the verdict: the verdict itself lives in
    `outcome.status`, `failure_stage` and `failure_detail`, and the point of
    recording `ok` here is that a 0.0 in `outcome` would be a real 0.0. A
    candidate with no evaluation at all is `not_run`, never `ok`.

    When the lane is the harness-outcome lane (`harnesseval.py`), the evaluator
    can say *who* produced the number. That string is carried in `detail`,
    because `evaluator_evidence` is a closed object in the trace schema and
    adding a field to it would change the frozen contract; it names the harness
    run id, the `a0/envelope` measurement token and the harness ledger sequence,
    so a reader can tell a harness-authored number from a locally measured one.
    """
    if result is None:
        return {"status": "not_run", "detail": "no evaluation was performed"}
    detail = None
    if evaluator is not None and hasattr(evaluator, "evidence_detail"):
        detail = evaluator.evidence_detail(result.candidate_id)
    return {"status": "ok", "detail": detail}


def policy_digest(policy: dict) -> str:
    import hashlib

    return hashlib.sha256(canonical_bytes(policy)).hexdigest()
