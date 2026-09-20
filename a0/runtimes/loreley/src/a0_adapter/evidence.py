"""``evaluator_evidence``: turning the runtime's behaviour into a labelable status.

``trace_schema.md`` §5 requires a score event to say *how* its outcome was
produced, so that a synthesized value can never be read as a measurement.  This
module derives that status from the runtime's own objects - never from a number:

* ``Evaluator.evaluate_outcome`` returns ``outcome_kind`` / ``failure`` /
  ``reuse_kind`` / ``reused_from_attempt_id`` / ``measurement_reused``
  (``loreley/core/worker/evaluator.py:738-796``, ``:1513-1520``, ``:1726-1744``);
* the plugin's own evidence record says whether ``E*`` timed out, how many metrics
  it emitted, and what ``E*`` actually returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .runtime import RuntimeEvaluation

# Order matters: the most specific cause wins.
TIMEOUT_MARKERS = ("timed out", "timeout", "did not return any result")


@dataclass(slots=True)
class Evidence:
    status: str
    detail: str | None = None
    cached_from_run_id: str | None = None
    metrics_dropped: int | None = None

    def as_trace(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "cached_from_run_id": self.cached_from_run_id,
            "metrics_dropped": self.metrics_dropped,
        }

    @property
    def measurable(self) -> bool:
        """True only for a fresh, untruncated, real measurement."""

        return self.status == "ok"


def classify(
    runtime_result: RuntimeEvaluation,
    *,
    max_metrics: int,
    protocol: str = "one_shot",
) -> Evidence:
    """Label one evaluation with the ``trace_schema.md`` §5 status."""

    record = runtime_result.evidence or {}
    emitted = record.get("metrics_returned")
    returned = len(runtime_result.metrics)
    # Truncation is only observable as "the plugin emitted more than the runtime
    # returned".  A count above the cap on its own is NOT evidence: an EvalPass
    # payload short-circuits `_coerce_outcome` (evaluator.py:2029-2037) and never
    # reaches the max_metrics truncation at :2304-2310.
    dropped: int | None = None
    if isinstance(emitted, int) and emitted > returned:
        dropped = emitted - returned

    # 1. Cache reuse.  A reused outcome is never a fresh measurement, even when
    #    its numbers look right (acceptance T4).
    reuse_kind = (runtime_result.reuse_kind or "none").strip().lower()
    reused_from = runtime_result.reused_from_attempt_id
    extra = runtime_result.raw_result_extra or {}
    if reuse_kind not in {"", "none"} or runtime_result.measurement_reused is True:
        source = (
            reused_from
            or str(extra.get("reused_source_commit_hash") or "")
            or str(extra.get("source_tree_hash") or "")
            or None
        )
        return Evidence(
            status="cache_hit",
            detail=(
                f"Loreley reused measurement reuse_kind={runtime_result.reuse_kind!r} "
                f"measurement_reused={runtime_result.measurement_reused!r} "
                f"protocol={protocol}"
            ),
            cached_from_run_id=source,
        )
    if extra.get("evaluation_reused") is True:
        return Evidence(
            status="cache_hit",
            detail="Loreley reused a persisted passed evaluation for an identical source tree",
            cached_from_run_id=str(extra.get("reused_source_commit_hash") or "") or None,
        )

    # 2. Timeout.  The runtime synthesizes a candidate failure; the plugin process
    #    never got to write its own evidence record.
    failure_text = " ".join(
        item for item in (runtime_result.failure_summary, runtime_result.detail) if item
    ).lower()
    if record.get("status") == "timeout":
        return Evidence(
            status="timeout",
            detail=str(record.get("detail") or "E* timed out inside the plugin"),
        )
    if any(marker in failure_text for marker in TIMEOUT_MARKERS):
        return Evidence(
            status="timeout",
            detail=(
                "the runtime synthesized a candidate failure on timeout: "
                f"{runtime_result.failure_summary}"
            ),
        )

    # 3. Truncation.  The runtime kept fewer metrics than the plugin emitted.
    if dropped:
        return Evidence(
            status="truncated_metrics",
            detail=(
                f"worker_evaluator_max_metrics={max_metrics}; the plugin emitted {emitted} "
                f"metrics and the runtime returned {returned}"
            ),
            metrics_dropped=int(dropped),
        )

    # 4. A real measurement.  "ok" means the evaluator actually ran and produced an
    #    Outcome; whether that Outcome scored is a separate question, answered by
    #    `measured_scoring` and by the outcome fields themselves (a measured invalid
    #    candidate has E*'s real, all-null field map - not a synthesized 0.0).
    record_status = str(record.get("status") or "")
    if runtime_result.outcome_kind == "passed" or record_status == "ok":
        if record_status and record_status != "ok":
            return Evidence(status=record_status, detail=str(record.get("detail") or "") or None)
        detail = None
        if record.get("measured_scoring") is False:
            detail = str(record.get("detail") or "") or None
        return Evidence(status="ok", detail=detail, metrics_dropped=dropped)

    # 5. Everything else is a failure the runtime reported without a measurement.
    return Evidence(
        status="synthesized_failure",
        detail=(
            runtime_result.failure_summary
            or runtime_result.detail
            or f"outcome_kind={runtime_result.outcome_kind}"
        ),
        metrics_dropped=dropped,
    )


def failure_stage_for(
    runtime_result: RuntimeEvaluation,
    evidence: Evidence,
    *,
    reference_status: str | None,
    reference_failure_kind: str | None = None,
) -> tuple[str, str | None]:
    """Stage one candidate according to the frozen table (``adapter_contract.md`` §5.3).

    The table maps **E\\*'s** ``(status, failure.kind)`` onto the trace's
    ``failure_stage``; it is not a per-runtime choice, because the study's
    per-runtime ``FailureStage`` totals are joined on it (``plan:577``).  Two cases
    sit outside the table and are labelled as such rather than folded into it:

    * a **runtime-level timeout** - the plugin process was killed before ``E*``
      returned, so there is no ``E*`` verdict to stage; the trace's own ``timeout``
      is used and ``evaluator_evidence.detail`` says which cause fired;
    * a **lane failure** with no readable Outcome at all, which is
      ``resolve_failed`` (nothing runnable came out of the lane).

    Everything else is exactly ``stage_for(E*.status, E*.failure.kind)``.
    """

    from .failure_stage import stage_for

    if evidence.status == "cache_hit":
        return "none", None
    if evidence.status == "truncated_metrics":
        return "none", None
    if evidence.status == "timeout":
        return "timeout", evidence.detail

    reference = (reference_status or "").strip().lower()
    if reference in {"ok", "invalid", "error"}:
        stage = stage_for(reference, reference_failure_kind)
        if stage is not None:
            return stage, evidence.detail if stage != "none" else None

    if runtime_result.outcome_kind == "passed":
        return "none", None
    if evidence.status == "synthesized_failure":
        record_detail = (runtime_result.evidence or {}).get("detail")
        return "resolve_failed", str(record_detail or evidence.detail or "")
    return "evaluator_failed", evidence.detail


def policy_note() -> Mapping[str, str]:
    return {
        "ok": "a fresh measurement of E*; the outcome fields are E*'s own",
        "synthesized_failure": "the runtime reported a failure with no measurement at all",
        "timeout": "the runtime turned a timeout into a candidate failure - not a score",
        "cache_hit": "a persistent cache supplied the value; it is not a fresh measurement",
        "truncated_metrics": "the runtime kept fewer metrics than the plugin emitted",
        "manifest_mismatch": "KAPSO-only; unused by Loreley",
        "not_run": "the evaluation was skipped",
    }
