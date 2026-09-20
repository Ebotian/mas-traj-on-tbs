"""A0.1 for EvE: does the runtime faithfully execute the frozen E*?

The comparison is `E_r(c; theta_E) = E*(c; theta_E) ± epsilon` for every ``c`` in C*
(plan:513), where `E_r` is what *EvE* produced through its own evaluation machinery and
`E*` is an independent run of the frozen evaluator outside any runtime. Since
`adapter_contract.md` §4.5 the row is also owed on the **failure surface**: `status`,
`failure.kind`, and the `failure_stage` the frozen A0-wide table derives from them, so that
`plan:577`'s per-runtime `FailureStage` counts can be summed. The staging adopted here comes
from `a0_adapter/selectionmap.py`, which digest-checks the contract's table at run time.

The runtime's nastiest false-green trap lives here (plan:551-552): an evaluation exception
is silently mapped to ``evaluation.failure_score`` 0.0, so a crash is numerically
indistinguishable from a genuine zero. This module therefore never lets the number decide:
every candidate carries a side-channel verdict read from the step's own ``status.txt`` /
``error.txt`` / the score payload written where EvE writes it. Note the limit that makes the
§4.5 staging a *declaration* rather than a runtime observation: EvE's lane cannot express
`invalid`/`error` at all, so the nine non-`ok` rows report E*'s kind and stage, attributed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import common, selectionmap
from .common import Candidate, Fr, Theta
from .eve_runtime import EveContext, evaluate_candidate_through_eve, build_context

EnvelopeFactory = Callable[[int, str], dict[str, Any]]


@dataclass
class CandidateComparison:
    candidate_id: str
    role: str
    solution_sha256: str
    iteration: int
    reference_status: str | None
    reference_scalar: float | None
    reference_rc: int
    reference_elapsed_s: float
    reference_outcome_path: str | None
    runtime_scalar: float | None
    runtime_score: Any
    runtime_evidence_status: str
    runtime_evidence_detail: str | None
    runtime_elapsed_s: float
    delta: float | None
    within_epsilon: bool | None
    classification: str
    side_channel: dict[str, Any]
    failure_stage: str = "none"
    failure_stage_basis: str = "frozen_table_e_star_verdict"
    failure_kind: str | None = None
    reference_outcome: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["side_channel"] = common.strip_absolute(payload["side_channel"])
        payload["runtime_score"] = common.strip_absolute(payload["runtime_score"])
        outcome = payload.pop("reference_outcome", None) or {}
        payload["reference_outcome_digest"] = outcome.get("canonical_digest")
        payload["reference_outcome_failure"] = outcome.get("failure")
        return payload


@dataclass
class A01Report:
    epsilon: float
    candidates: list[CandidateComparison] = field(default_factory=list)
    trap: dict[str, Any] = field(default_factory=dict)
    verdict: str = "unknown"
    exit_code: int = common.EXIT_OK
    counters: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "epsilon": self.epsilon,
            "verdict": self.verdict,
            "exit_code": self.exit_code,
            "counters": self.counters,
            "failure_stage_counts": self.failure_stage_counts(),
            "failure_stage_extension": self.failure_stage_extension(),
            "agreement_scope": self.agreement_scope(),
            "trap": self.trap,
            "candidates": [candidate.to_json() for candidate in self.candidates],
        }

    def failure_stage_counts(self) -> dict[str, int]:
        """The joinable FailureStage counts over `C*` (§5.3, `plan:577`).

        One unit per candidate, staged by the adopted frozen table. These are the numbers that
        must sum across runtimes; `counters` holds the verdict-side tallies instead.
        """
        counts: dict[str, int] = {}
        for candidate in self.candidates:
            counts[candidate.failure_stage] = counts.get(candidate.failure_stage, 0) + 1
        return counts

    def failure_stage_extension(self) -> dict[str, Any]:
        """Rows staged by a rule the frozen table cannot express — declared, never silent.

        The table maps `E*` verdicts. A candidate E* measured `ok` whose runtime attempt failed
        anyway has no entry there, and staging it `none` would erase a real runtime failure, so
        those rows are `evaluator_failed` and counted here. 0 rows in an A0.1 run where the
        adapter reproduced every measurable candidate.
        """
        rows = [
            candidate.candidate_id
            for candidate in self.candidates
            if candidate.failure_stage_basis != "frozen_table_e_star_verdict"
        ]
        return {
            "rows": rows,
            "count": len(rows),
            "cases": list(ADAPTER_SIDE_FAILURE_STAGE_CLASSIFICATIONS),
            "staged_as": "evaluator_failed",
            "consequence_for_joining_counts": (
                "these rows are the only way this adapter's declared counts can differ from "
                "expected_from_frozen_map; when one fires, the difference IS the finding and is "
                "raised with the contract owner (DECLARATIONS.md §4.2) rather than re-mapped away"
            ),
        }

    def agreement_scope(self) -> dict[str, Any]:
        """What A0.1's formula holds on, stated so nobody can read it as 14 reproduced verdicts.

        Audit F5: `E_r(c) = E*(c) ± epsilon` is checked on the candidates `E*` *measured*
        (`status == "ok"`). The rest are EvE's `failure_score` fallback: EvE's lane returns
        `{score: 0.0, summary: "evaluation failed"}` for every non-measurable candidate and
        cannot express `invalid` / `error` at all, so those rows are a declaration about what
        EvE *could not* produce, never a comparison of runtime and reference verdicts.
        """
        total = len(self.candidates)
        matched = self.counters.get("match", 0)
        synthetic = self.counters.get("synthesized_failure", 0)
        other = total - matched - synthetic
        return {
            "formula": "E_r(c; theta_E) = E*(c; theta_E) +/- epsilon",
            "measured_rows": matched,
            "declared_synthetic_rows": synthetic,
            "neither_measured_nor_synthetic": other,
            "candidates_total": total,
            "holds_on": f"{matched}/{total} candidates — the ones E* measured with status=ok",
            "does_not_hold_on": (
                f"{synthetic}/{total} candidates — EvE returned its failure_score "
                f"(score 0.0, summary 'evaluation failed') because its step raised; E* "
                f"measured none of them"
            ),
            "runtime_can_express_invalid_or_error": False,
            "runner_label_for_the_synthetic_rows": "SYNTHETIC_DECLARED",
            "statement": (
                f"EvE's A0.1 result is {matched} measured row(s) + {synthetic} declared "
                f"synthesised zero(s), NOT {total} reproduced verdicts. On the {matched} "
                f"measured rows agreement is bit-exact; on the {synthetic} others there is no "
                f"E_r value to compare, because EvE's lane has no way to report E*'s "
                f"invalid/error verdict — it substitutes evaluation.failure_score 0.0 "
                f"(workflow/evaluation.py:161-165). A consumer must read this as "
                f"{matched}/{total} measured."
            ),
        }


# adapter_contract.md §5.3 / §4.5 — `E*` verdict -> `failure_stage` comes from the **adopted,
# frozen, A0-wide** table, not from a mapping this adapter invented. The table (and the
# `scalarization` block beside it) is loaded and digest-checked by `a0_adapter/selectionmap.py`
# from `a0/contract/selection/simpleloop.selection.json`, and the adapter refuses to report a run
# whose copy no longer matches it.
#
# Why this replaced a classification-keyed mapping: the previous revision staged every
# non-measurable candidate `resolve_failed`. EvE declared `failure.kind` correctly on all nine
# rows, but collapsed `invalid_configuration` (-> verify_failed), `non_deterministic`
# (-> verify_failed) and `runtime_budget_exceeded` (-> timeout) into `resolve_failed`, so its
# counts were `{none: 5, resolve_failed: 9}` against the frozen map's
# `{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}`. Two runtimes
# that measured the same `C*` could not have their FailureStage counts summed, which is the only
# reason the table exists (`plan:577`, `plan:628`).
#
# Rows whose `E*` verdict is `ok` but whose runtime attempt failed anyway (`mismatch`, or a
# synthesised score for a candidate E* measured) are the one case the frozen table cannot
# describe: it maps `E*` verdicts, and E* assigned `none`. Recording `none` there would erase a
# real runtime failure, so those units are staged `evaluator_failed` and **declared as an
# extension**, never silently: `a01.failure_stage_extension` counts them (0 rows in this run) and
# DECLARATIONS.md §4.2 raises them with the contract owner. If one fires, the declared counts stop
# equalling `expected_from_frozen_map` *by design*, and that is the finding, not a defect.
ADAPTER_SIDE_FAILURE_STAGE_CLASSIFICATIONS = (
    "mismatch",
    "runtime_synthesized_failure_for_a_measurable_candidate",
)


def stage_of(
    *,
    status: str | None,
    failure_kind: str | None,
    rc: int,
    classification: str,
) -> tuple[str, str]:
    """The `failure_stage` for one `C*` row, plus which rule produced it.

    Returns `(stage, basis)` where basis is `frozen_table_e_star_verdict` for every row the
    adopted table covers (i.e. every row whose `E*` verdict is not `ok`), and
    `adapter_extension_runtime_failed_a_measurable_candidate` for the declared extension above.
    """
    stage = selectionmap.failure_stage_for(status, failure_kind, rc)
    if stage == "none" and classification in ADAPTER_SIDE_FAILURE_STAGE_CLASSIFICATIONS:
        return "evaluator_failed", "adapter_extension_runtime_failed_a_measurable_candidate"
    return stage, "frozen_table_e_star_verdict"


def _classify(
    *,
    reference_status: str | None,
    reference_scalar: float | None,
    runtime_scalar: float | None,
    evidence_status: str,
    epsilon: float,
) -> tuple[str, float | None, bool | None]:
    delta = (
        None
        if (reference_scalar is None or runtime_scalar is None)
        else abs(runtime_scalar - reference_scalar)
    )
    within = None if delta is None else bool(delta <= epsilon)
    if reference_status == "ok":
        if evidence_status != "ok":
            return "runtime_synthesized_failure_for_a_measurable_candidate", delta, within
        return ("match" if within else "mismatch"), delta, within
    # E* returned no value: E_r must not present one as a measurement.
    if evidence_status == "synthesized_failure":
        return "non_measurable_reported_as_synthetic_failure", delta, within
    if evidence_status == "not_run":
        return "non_measurable_not_run", delta, within
    return "non_measurable_but_reported_as_ok", delta, within


def failure_detail_for(
    *,
    status: str | None,
    rc: int,
    failure_kind: str | None,
    stage: str,
    basis: str,
    evidence_status: str,
    runtime_score: Any,
) -> str | None:
    """The `failure_detail` a staged unit carries (the trace schema requires one for non-`none`).

    Kept as a function rather than inlined so that a re-materialized record can carry exactly the
    text the running code produces.
    """
    if stage == "none":
        return None
    return (
        f"E* status={status!r} rc={rc} "
        f"failure.kind={failure_kind!r} -> failure_stage={stage!r} "
        f"({basis}, adapter_contract.md §5.3); EvE returned "
        f"{json.dumps(common.strip_absolute(runtime_score), sort_keys=True)} with "
        f"evaluator_evidence.status={evidence_status!r}. "
        "EvE's lane cannot express E*'s invalid/error verdict — it substitutes "
        "evaluation.failure_score 0.0 (workflow/evaluation.py:161-165) — so this unit "
        "is a declared synthesised failure, not a measured comparison (plan:551-552)"
    )


def run_conformance(
    ctx: EveContext,
    *,
    candidates: list[Candidate],
    run_dir: Path,
    theta: Theta,
    fr: Fr,
    epsilon: float,
    traces=None,
    envelope: EnvelopeFactory | None = None,
    fr_payload: dict[str, Any] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> A01Report:
    say = on_progress or (lambda _msg: None)
    report = A01Report(epsilon=epsilon)
    run_dir = Path(run_dir)
    reference_dir = run_dir / "reference"
    state_dir = run_dir / "e-star-state"

    for index, candidate in enumerate(candidates):
        say(f"[a01] {candidate.candidate_id}")
        # --- the reference side: E* outside any runtime -------------------------------
        reference = common.run_e_star(
            candidate.path,
            candidate_id=candidate.candidate_id,
            theta=theta,
            out_path=reference_dir / f"{candidate.candidate_id}.json",
            state_dir=state_dir,
        )
        # --- the runtime side: EvE's own evaluation machinery -------------------------
        runtime = evaluate_candidate_through_eve(ctx, candidate, fr=fr, iteration=index)
        classification, delta, within = _classify(
            reference_status=reference.status,
            reference_scalar=reference.scalar,
            runtime_scalar=runtime.scalar,
            evidence_status=runtime.evidence_status,
            epsilon=epsilon,
        )
        # `E*`'s own failure kind, and the stage the frozen table assigns to it. The stage is
        # derived here, once, and used both for the trace event and for the row the conformance
        # document reports, so the two cannot drift apart (§4.5(c)).
        failure_kind = ((reference.outcome or {}).get("failure") or {}).get("kind")
        failure_stage, failure_stage_basis = stage_of(
            status=reference.status,
            failure_kind=failure_kind,
            rc=reference.rc,
            classification=classification,
        )
        comparison = CandidateComparison(
            candidate_id=candidate.candidate_id,
            role=candidate.role,
            solution_sha256=candidate.solution_sha256,
            iteration=index,
            reference_status=reference.status,
            reference_scalar=reference.scalar,
            reference_rc=reference.rc,
            reference_elapsed_s=round(reference.elapsed_s, 6),
            reference_outcome_path=str(reference.outcome_path) if reference.outcome_path else None,
            runtime_scalar=runtime.scalar,
            runtime_score=runtime.score,
            runtime_evidence_status=runtime.evidence_status,
            runtime_evidence_detail=runtime.evidence_detail,
            runtime_elapsed_s=round(runtime.elapsed_s, 6),
            delta=delta,
            within_epsilon=within,
            classification=classification,
            side_channel=runtime.side_channel,
            failure_stage=failure_stage,
            failure_stage_basis=failure_stage_basis,
            failure_kind=failure_kind,
            reference_outcome=reference.outcome,
        )
        report.candidates.append(comparison)

        if traces is not None and envelope is not None and fr_payload is not None:
            fields = dict(reference.fields) if reference.fields else {
                "sum_radii": None,
                "unmeasurable": {"status": reference.status, "rc": reference.rc},
            }
            # Honest placement of this unit on the protocol's trajectory (plan:628, §4.5). The 9
            # candidates E* cannot measure did not fail A0.1 numerically — no comparison exists —
            # but EvE's lane could not produce the observation either, so the unit carries the
            # stage the **frozen table assigns to E*'s own failure.kind** (`verify_failed` for the
            # four `invalid_configuration` rows and for `non_deterministic`, `resolve_failed` for
            # `candidate_import_failed`, `evaluator_failed` for `candidate_call_raised` /
            # `child_terminated_early`, `timeout` for `runtime_budget_exceeded`) — never `none`,
            # and never the adapter's own preference.
            stage = failure_stage
            detail = failure_detail_for(
                status=reference.status,
                rc=reference.rc,
                failure_kind=failure_kind,
                stage=stage,
                basis=failure_stage_basis,
                evidence_status=runtime.evidence_status,
                runtime_score=runtime.score,
            )
            traces.score(
                iteration=index,
                candidate_id=candidate.candidate_id,
                envelope=envelope(index, candidate.candidate_id, stage, detail),
                fields=fields,
                fr_payload=fr_payload,
                search_signal=runtime.scalar,
                evidence={
                    "status": runtime.evidence_status,
                    "detail": runtime.evidence_detail,
                    "cached_from_run_id": None,
                    "metrics_dropped": None,
                },
            )

    # Verdict-side tallies. `failure_stage_counts` (`A01Report.failure_stage_counts`) is the
    # separate, joinable FailureStage accounting; these keys deliberately do NOT reuse a stage
    # name, because "resolve_failed: 0" beside "failure_stage_counts.resolve_failed: 1" is the
    # kind of ambiguity that produced audit R1.
    counters = {
        "candidates": len(report.candidates),
        "reference_ok": sum(1 for c in report.candidates if c.reference_status == "ok"),
        "reference_non_ok": sum(1 for c in report.candidates if c.reference_status != "ok"),
        "match": sum(1 for c in report.candidates if c.classification == "match"),
        "mismatch": sum(1 for c in report.candidates if c.classification == "mismatch"),
        "synthesized_failure": sum(
            1 for c in report.candidates if c.runtime_evidence_status == "synthesized_failure"
        ),
        "value_mismatch": sum(1 for c in report.candidates if c.classification == "mismatch"),
        "runtime_failed_a_measurable_candidate": sum(
            1
            for c in report.candidates
            if c.classification == "runtime_synthesized_failure_for_a_measurable_candidate"
        ),
        "runtime_reported_ok_where_e_star_did_not": sum(
            1 for c in report.candidates if c.classification == "non_measurable_but_reported_as_ok"
        ),
    }
    report.counters = counters

    measured = [c for c in report.candidates if c.reference_status == "ok"]
    synthetic = [c for c in report.candidates if c.runtime_evidence_status == "synthesized_failure"]
    report.trap = {
        "name": "EvE maps an evaluation exception to evaluation.failure_score 0.0",
        "mechanism_citations": [
            "src/scaling_evolve/algorithms/eve/workflow/evaluation.py:161-165 (except Exception -> evaluation_failure_score)",
            "configs/eve/evaluation/circle_packing.yaml:8-10 (failure_score {score: 0.0, summary: 'evaluation failed'})",
            "configs/eve/application/circle_packing.yaml:12-14 (boundary_failure_score {score: 0.0})",
            "configs/eve/evaluation/circle_packing/evaluation.sh:56-72 (non-zero evaluator exit -> {score: 0.0, summary: 'evaluation command failed'}, exit 0)",
        ],
        "detected": bool(synthetic),
        "candidates_with_synthetic_score": [c.candidate_id for c in synthetic],
        "synthetic_scores": sorted({c.runtime_scalar for c in synthetic}),
        "genuine_measurements": sorted(
            {c.reference_scalar for c in measured if c.reference_scalar is not None}
        ),
        "threshold_separability": (
            None
            if not measured or not synthetic
            else {
                "min_genuine": min(
                    c.reference_scalar for c in measured if c.reference_scalar is not None
                ),
                "synthetic_value": sorted({c.runtime_scalar for c in synthetic}),
                "separable_by_a_score_threshold": False,
                "why": (
                    "the synthetic value 0.0 lies below every genuine measurement in C*; "
                    "no threshold on the score can tell 'crashed' from 'genuinely worthless'"
                ),
            }
        ),
        "side_channel_that_actually_discriminates": {
            "step_status_path_example": (
                str(synthetic[0].side_channel.get("step_status_path")) if synthetic else None
            ),
            "step_status_values": sorted(
                {
                    str(c.side_channel.get("step_status"))
                    for c in report.candidates
                }
            ),
            "error_txt_at_eval_log_root_when_synthetic": sorted(
                {bool(c.side_channel.get("log_root_error_present")) for c in synthetic}
            ),
            "error_txt_at_eval_log_root_when_measured": sorted(
                {bool(c.side_channel.get("log_root_error_present")) for c in measured}
            ),
            "step_error_txt_present_when_synthetic": sorted(
                {bool(c.side_channel.get("error_present")) for c in synthetic}
            ),
            "note": (
                "with the adapter's own step the discriminating files are "
                "logs/evaluate/steps/step_01_<step>/status.txt and logs/evaluate/error.txt "
                "(the eval-log root, per the shipped step contract); the step-level error.txt "
                "is written by EvE only for judge steps"
            ),
            "e_star_outcome_status_when_synthetic": sorted(
                {str(c.side_channel.get("e_star_outcome_status")) for c in synthetic}
            ),
        },
        "verdict_if_the_number_alone_were_trusted": (
            "the synthetic 0.0 would be read as a measurement and the run would look "
            "conformant on all "
            f"{len(report.candidates)} candidates — this is the false green"
        ),
    }
    # A row fails A0.1 on any disagreement with `E*` (§4.5): the score (`mismatch`), a synthesised
    # score where E* measured (`runtime_failed_a_measurable_candidate`), or the runtime claiming
    # `ok` where E* did not. `failure_stage` disagreement is compared by the conformance runner
    # against the row's declared stage and by `trace_validate.py` against the run's stream.
    failing_verdicts = (
        counters["mismatch"]
        + counters["runtime_failed_a_measurable_candidate"]
        + counters["runtime_reported_ok_where_e_star_did_not"]
    )
    if failing_verdicts == 0:
        report.verdict = "PASS"
        report.exit_code = common.EXIT_OK
    else:
        report.verdict = "FAIL"
        report.exit_code = common.EXIT_A01_FAILURE
    return report


# --------------------------------------------------------------------------------------
# The shipped-failure-contract reproduction
# --------------------------------------------------------------------------------------


def reproduce_bundled_failure_contract(
    *,
    bundled_step: Path,
    candidate: Candidate,
    run_dir: Path,
    theta: Theta,
    fr: Fr,
    eid_star: str,
    pins_sha256: str,
    extra_files: dict[str, str] | None = None,
    label: str = "bundled",
    description: str | None = None,
) -> dict[str, Any]:
    """Run one candidate with EvE's *shipped* evaluation.sh step, unmodified.

    Two routes are reachable through this step without changing a byte of it:

    * the evaluator program it runs exits non-zero -> the step writes
      ``{score: 0.0, summary: "evaluation command failed"}`` and exits 0
      (configs/eve/evaluation/circle_packing/evaluation.sh:56-72), so EvE's
      ``except Exception`` branch never fires and the step is recorded as *successful*;
    * the evaluator program succeeds while itself reporting an error with score 0.0 -> the
      step copies that payload through verbatim.

    In both cases the resulting population score is 0.0, indistinguishable by the number
    from a genuine zero.
    """
    ctx = build_context(
        run_dir=Path(run_dir) / label,
        theta=theta,
        fr=fr,
        eid_star=eid_star,
        pins_sha256=pins_sha256,
        step_script_override=Path(bundled_step),
    )
    evaluation = evaluate_candidate_through_eve(
        ctx, candidate, fr=fr, iteration=0, extra_files=extra_files
    )
    return {
        "label": label,
        "description": description
        or (
            "the shipped configs/eve/evaluation/circle_packing/evaluation.sh used as the step, "
            "unmodified"
        ),
        "step_script": str(bundled_step),
        "candidate_id": candidate.candidate_id,
        "extra_files": sorted((extra_files or {}).keys()),
        "returned_score_payload": common.strip_absolute(evaluation.score),
        "returned_scalar": evaluation.scalar,
        "evidence_status": evaluation.evidence_status,
        "evidence_detail": evaluation.evidence_detail,
        "evaluation_failure_score": common.strip_absolute(ctx.failure_score),
        "score_yaml_equals_failure_score": bool(
            json.dumps(evaluation.score, sort_keys=True, default=str)
            == json.dumps(ctx.failure_score, sort_keys=True, default=str)
        ),
        "side_channel": common.strip_absolute(evaluation.side_channel),
        "conclusion": (
            "a failed evaluation yields a numeric 0.0 that EvE accepts as a population score; "
            "the numeric value carries no information about the failure. Which auxiliary signal "
            "survives depends on the route: the step status/error.txt (route R2) or only the "
            "payload's own status field (route R3)."
        ),
    }
