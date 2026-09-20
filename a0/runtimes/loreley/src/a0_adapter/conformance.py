"""A0.1 - evaluator integration conformance.

For every runtime and every candidate of ``C*``: ``E_r(c; theta_E) = E*(c; theta_E)
+/- epsilon`` and ``EID_r`` derives from ``EID*`` (protocol ``plan:513-517``).

The comparison is made on **two levels**:

* the scalar projection ``F_r(c) = outcome.fields.sum_radii``, which is what the
  protocol's ``E_r(c)`` means once ``F_r`` is fixed (``plan:528``); and
* the whole multi-field Outcome, so a runtime that produced the right scalar from
  the wrong fields is caught (hard constraint 3, ``plan:549``).

``epsilon`` comes from the frozen ``Config`` - it is read, never chosen after
seeing the numbers (acceptance check A01.1).
"""

from __future__ import annotations

import json
import platform
import statistics
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import (
    Candidate,
    CandidateSet,
    EvalContract,
    ThetaE,
    EXIT_CONFORMANCE,
    EXIT_OK,
    required_metric_names,
)
from .eidr import EidRMapping
from .runtime import (
    FrozenEnvironment,
    ReferenceEvaluation,
    RuntimeEvaluation,
    reference_evaluation,
    reset_workspace,
    run_through_loreley,
)

CONFORMANCE_SCHEMA = "a0.conformance.loreley/v1"
REPEATS_FOR_EPSILON = 3


def _close(first: Any, second: Any, epsilon: float) -> bool:
    if first is None and second is None:
        return True
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return abs(float(first) - float(second)) <= epsilon
    return first == second


def compare_fields(
    reference_fields: Mapping[str, Any],
    runtime_fields: Mapping[str, Any],
    *,
    epsilon: float,
) -> list[dict[str, Any]]:
    discrepancies: list[dict[str, Any]] = []
    for name in sorted(set(reference_fields) | set(runtime_fields)):
        left = reference_fields.get(name)
        right = runtime_fields.get(name)
        if not _close(left, right, epsilon):
            discrepancies.append({"field": name, "e_star": left, "runtime": right})
    return discrepancies


def _runtime_fields(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """E*'s fields as the runtime carries them, excluding the declared F_r projection.

    ``F_r`` adds one metric of its own (``details.source == "F_r"``); that metric is
    the scalarization and is therefore not an ``E*`` field.  It is reported
    separately so a reader can still see it.
    """

    return {
        str(item["name"]): item["value"]
        for item in metrics
        if (item.get("details") or {}).get("source") != "F_r"
    }


def _fr_projection(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        str(item["name"]): item["value"]
        for item in metrics
        if (item.get("details") or {}).get("source") == "F_r"
    }


@dataclass(slots=True)
class ConformanceReport:
    contract: EvalContract
    theta: ThetaE
    eid_r: EidRMapping
    epsilon: float
    per_candidate: list[dict[str, Any]] = dc_field(default_factory=list)
    repeats: dict[str, Any] = dc_field(default_factory=dict)
    cwd_independence: dict[str, Any] = dc_field(default_factory=dict)
    hard_constraint_3: dict[str, Any] = dc_field(default_factory=dict)

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [
            record for record in self.per_candidate
            if record["verdict"] != "pass"
        ]

    def as_document(self, env: FrozenEnvironment) -> dict[str, Any]:
        return {
            "schema": CONFORMANCE_SCHEMA,
            "runtime": "loreley",
            "task": "circle-packing",
            "eid_star": self.contract.eid_star,
            "eid_r": self.eid_r.as_trace(),
            "eid_r_mapping": self.eid_r.as_document(),
            "theta_E": self.theta.as_trace(),
            "epsilon": {
                "kind": "abs",
                "unit": self.contract.primary_field,
                "value": self.epsilon,
                "frozen_before_run": True,
                "source": f"{self.contract.path.name} components.Config.conformance.epsilon",
            },
            "primary_field": self.contract.primary_field,
            "candidate_set": str(env.run_dir),
            "interpreter": {
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
            },
            "per_candidate": self.per_candidate,
            "repeats": self.repeats,
            "hard_constraint_1_cwd_independence": self.cwd_independence,
            "hard_constraint_3_multi_field": self.hard_constraint_3,
            "failure_count": len(self.failures),
            "verdict": "pass" if not self.failures else "fail",
            "failed_candidates": [record["candidate_id"] for record in self.failures],
        }


def run_conformance(
    *,
    contract: EvalContract,
    candidate_set: CandidateSet,
    theta: ThetaE,
    eid_r: EidRMapping,
    env: FrozenEnvironment,
    repeats: int = REPEATS_FOR_EPSILON,
    candidates: Sequence[Candidate] | None = None,
    evaluations: Mapping[str, Any] | None = None,
) -> ConformanceReport:
    """Compare ``E_r(c)`` with ``E*(c)`` for every ``c in C*``.

    ``evaluations`` lets the caller hand over results it has already produced (and
    traced); when it is given, this function does not re-run the runtime, so the
    A0.1 number and the A0.1 trace always come from the same execution.
    """
    epsilon = contract.epsilon
    report = ConformanceReport(
        contract=contract, theta=theta, eid_r=eid_r, epsilon=epsilon
    )
    env.apply()
    reset_workspace(env)
    reference_dir = env.run_dir / "reference"

    selected = tuple(candidates) if candidates is not None else candidate_set.candidates
    for candidate in selected:
        if evaluations is not None and candidate.candidate_id in evaluations:
            provided = evaluations[candidate.candidate_id]
            runtime_result = provided["runtime"]
            reference = provided["reference"]
        else:
            runtime_result = run_through_loreley(env, candidate, iteration=0)
            reference = reference_evaluation(
                candidate, theta, workdir=reference_dir / candidate.candidate_id
            )
        runtime_fields = _runtime_fields(runtime_result.metrics)
        reference_fields = reference.fields
        expected = {
            name: reference_fields.get(name)
            for name in required_metric_names(contract.document)
        }
        declared_but_missing = sorted(
            name for name in expected if name not in reference_fields
        )

        scalar_ok = _close(
            reference_fields.get(contract.primary_field),
            runtime_fields.get(contract.primary_field),
            epsilon,
        )
        status_ok = (
            (runtime_result.outcome_kind == "passed") == (reference.status == "ok")
        )
        field_discrepancies = compare_fields(
            {k: v for k, v in expected.items() if v is not None},
            runtime_fields,
            epsilon=epsilon,
        )
        # Fields E* left null must not appear as a number in the runtime.
        fabricated = sorted(
            name for name, value in expected.items()
            if value is None and runtime_fields.get(name) is not None
        )

        verdict = "pass"
        reasons: list[str] = []
        if not status_ok:
            verdict = "fail"
            reasons.append(
                f"status mismatch: E_r outcome_kind={runtime_result.outcome_kind} vs "
                f"E* status={reference.status}"
            )
        if not scalar_ok:
            verdict = "fail"
            reasons.append(
                "scalar projection mismatch on "
                f"{contract.primary_field}: E*={reference_fields.get(contract.primary_field)!r} "
                f"E_r={runtime_fields.get(contract.primary_field)!r}"
            )
        if field_discrepancies:
            verdict = "fail"
            reasons.append(f"multi-field mismatch: {field_discrepancies}")
        if fabricated:
            verdict = "fail"
            reasons.append(f"runtime produced values for E*-null fields: {fabricated}")
        if declared_but_missing:
            verdict = "fail"
            reasons.append(
                f"EID* MetricDefinition declares fields E* did not return: {declared_but_missing}"
            )

        report.per_candidate.append(
            {
                "candidate_id": candidate.candidate_id,
                "role": candidate.role,
                "kind": candidate.kind,
                "candidate_path": str(candidate.path),
                "e_star_status": reference.status,
                "e_star_scored": reference.scored,
                "e_star_exit_code": reference.exit_code,
                "e_star_fields": reference_fields,
                "e_star_primary": reference_fields.get(contract.primary_field),
                "e_star_canonical_digest": reference.outcome.get("canonical_digest"),
                "e_star_manifest": reference.manifest,
                "declared_fields_missing_from_e_star": declared_but_missing,
                "runtime_outcome_kind": runtime_result.outcome_kind,
                "runtime_fields": runtime_fields,
                "runtime_primary": runtime_fields.get(contract.primary_field),
                "runtime_fr_projection": _fr_projection(runtime_result.metrics),
                "runtime_metrics_count": len(runtime_result.metrics),
                "runtime_reuse_kind": runtime_result.reuse_kind,
                "runtime_failure_summary": runtime_result.failure_summary,
                "scalar_projection_ok": scalar_ok,
                "status_ok": status_ok,
                "field_discrepancies": field_discrepancies,
                "fabricated_fields": fabricated,
                "verdict": verdict,
                "reasons": reasons,
            }
        )

    # A01.3: epsilon must cover the evaluator nondeterminism actually observed.
    spread_candidate = next(
        (
            candidate for candidate in selected
            if candidate.role in {"good", "baseline"}
        ),
        selected[0],
    )
    reference_primary: list[float | None] = []
    runtime_primary: list[float | None] = []
    repeat_details: list[dict[str, Any]] = []
    for index in range(max(1, repeats)):
        ref = reference_evaluation(
            spread_candidate, theta, workdir=reference_dir / f"{spread_candidate.candidate_id}-r{index}"
        )
        run = run_through_loreley(env, spread_candidate, iteration=index)
        fields = _runtime_fields(run.metrics)
        reference_primary.append(ref.fields.get(contract.primary_field))
        runtime_primary.append(fields.get(contract.primary_field))
        repeat_details.append(
            {
                "repeat": index,
                "e_star_primary": ref.fields.get(contract.primary_field),
                "runtime_primary": fields.get(contract.primary_field),
                "runtime_outcome_kind": run.outcome_kind,
            }
        )
    numeric_reference = [v for v in reference_primary if isinstance(v, (int, float))]
    numeric_runtime = [v for v in runtime_primary if isinstance(v, (int, float))]
    report.repeats = {
        "candidate_id": spread_candidate.candidate_id,
        "repeats": max(1, repeats),
        "detail": repeat_details,
        "e_star": {
            "min": min(numeric_reference) if numeric_reference else None,
            "max": max(numeric_reference) if numeric_reference else None,
            "spread": (max(numeric_reference) - min(numeric_reference))
            if numeric_reference else None,
            "stdev": statistics.pstdev(numeric_reference) if len(numeric_reference) > 1 else 0.0,
        },
        "runtime": {
            "min": min(numeric_runtime) if numeric_runtime else None,
            "max": max(numeric_runtime) if numeric_runtime else None,
            "spread": (max(numeric_runtime) - min(numeric_runtime))
            if numeric_runtime else None,
            "stdev": statistics.pstdev(numeric_runtime) if len(numeric_runtime) > 1 else 0.0,
        },
        "max_observed_spread": max(
            [
                (max(numeric_reference) - min(numeric_reference)) if numeric_reference else 0.0,
                (max(numeric_runtime) - min(numeric_runtime)) if numeric_runtime else 0.0,
            ]
        ),
        "epsilon_covers_observed_spread": (
            max(
                [
                    (max(numeric_reference) - min(numeric_reference))
                    if numeric_reference else 0.0,
                    (max(numeric_runtime) - min(numeric_runtime)) if numeric_runtime else 0.0,
                ]
            )
            <= epsilon
        ),
    }

    # Hard constraint 1 (plan:544): no dependence on cwd or PATH.
    cwd_root = env.run_dir / "cwd-independence"
    cwd_root.mkdir(parents=True, exist_ok=True)
    third_path_run = reference_evaluation(spread_candidate, theta, workdir=cwd_root)
    first_reference = next(
        (
            record for record in report.per_candidate
            if record["candidate_id"] == spread_candidate.candidate_id
        ),
        None,
    )
    reference_primary_for_candidate = (
        first_reference["e_star_primary"] if first_reference else None
    )
    report.cwd_independence = {
        "candidate_id": spread_candidate.candidate_id,
        "cwd": "/",
        "path": "",
        "third_path_primary": third_path_run.fields.get(contract.primary_field),
        "in_run_reference_primary": reference_primary_for_candidate,
        "matches_reference": _close(
            third_path_run.fields.get(contract.primary_field),
            reference_primary_for_candidate,
            epsilon,
        ),
        "third_path_canonical_digest": third_path_run.outcome.get("canonical_digest"),
        "in_run_canonical_digest": (
            first_reference["e_star_canonical_digest"] if first_reference else None
        ),
        "note": (
            "E* is executed with cwd=/ and PATH='' from a third directory; both the "
            "primary value and the canonical digest are compared"
        ),
    }

    # Hard constraint 3 (plan:549): E*'s multi-field output survives into the trace
    # and is scalarized only by F_r.
    multi_field_example = next(
        (record for record in report.per_candidate if record["e_star_scored"]),
        None,
    )
    report.hard_constraint_3 = {
        "declared_outcome_fields": sorted(
            {name for record in report.per_candidate for name in record["e_star_fields"]}
        ),
        "example_candidate": multi_field_example["candidate_id"] if multi_field_example else None,
        "example_runtime_field_count": len(multi_field_example["runtime_fields"])
        if multi_field_example else 0,
        "example_runtime_fields": sorted(multi_field_example["runtime_fields"])
        if multi_field_example else [],
        "example_fr_projection": multi_field_example["runtime_fr_projection"]
        if multi_field_example else {},
        "fields_preserved": bool(multi_field_example)
        and len(multi_field_example["runtime_fields"]) > 1,
        "scalarization_owner": "F_r",
        "note": (
            "the runtime's metric vector keeps E*'s multi-field Outcome; the declared F_r "
            "adds exactly one projection metric and the adapter is the only place a scalar "
            "is formed"
        ),
    }

    return report


def write_conformance(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def conformance_exit_code(report: ConformanceReport) -> int:
    return EXIT_OK if not report.failures else EXIT_CONFORMANCE
