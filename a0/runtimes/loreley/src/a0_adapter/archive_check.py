"""A0.2 for Loreley: does the archive consume scores the way it claims?

The claimed semantics (protocol §4.3, ``plan:562``; acceptance A02-L1..L8):

* admission replaces **only inside the candidate's own cell**;
* the cell is fixed by ``measures`` alone - score can never move a candidate
  between cells (``pareto_archive.py:168-189``);
* within a cell the front is the non-dominated set under an epsilon, truncated by
  crowding distance when it exceeds ``max_front_size``;
* the report branch is a global argmax over *retained* members, so it must not be
  used as the cross-cell control.

Everything below runs the pinned checkout's own ``ParetoGridArchive`` and its own
``ObjectiveContract``.  Two configurations are exercised, because the protocol's
own claim ("no global-argmax guarantee") is configuration-dependent - see
``REGIME_NOTE``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import CandidateSet, EvalContract, ThetaE
from .report_branch import probe_report_branch
from .runtime import (
    FrozenEnvironment,
    build_archive,
    make_candidate,
    resolve_objectives,
    run_through_loreley,
)

A02_SCHEMA = "a0.a02.loreley/v1"
TARGET_DIMS = 2
CELLS_PER_DIM = 16
ISLAND = "circle_packing_alpha"

CONFIG_S_OBJECTIVES: tuple[Mapping[str, str], ...] = (
    {"name": "composite_score", "direction": "max"},
)
CONFIG_M_OBJECTIVES: tuple[Mapping[str, str], ...] = (
    {"name": "sum_radii", "direction": "max"},
    {"name": "runtime_p50_ms", "direction": "min"},
)

REGIME_NOTE = (
    "Under a single objective every cell front has exactly one member, so the archive "
    "IS the per-cell argmax and the report is the global argmax over retained members: "
    "the protocol's 'no global-argmax guarantee' does not hold there. The cross-cell "
    "non-eviction control therefore only discriminates under a multi-objective "
    "configuration, where two non-dominated candidates can coexist in one cell and a "
    "high primary score can coexist with a retained worse primary. Config M (the "
    "checkout's own circle-packing example objective list, "
    "examples/evol_circle_packing.py:80-84) is that configuration."
)


def _m(name: str, value: float, higher_is_better: bool = True) -> dict[str, Any]:
    """One metric the way ``ObjectiveContract._parse_metric`` insists on it.

    ``objectives.py:238`` calls ``parse_higher_is_better`` with no default, so the
    runtime itself rejects a metric mapping without an explicit direction - which is
    why the adapter never omits it.
    """

    return {"name": name, "value": float(value), "higher_is_better": bool(higher_is_better)}


@dataclass(slots=True)
class CheckResult:
    check_id: str
    description: str
    passed: bool
    config: str
    observations: dict[str, Any] = dc_field(default_factory=dict)
    inputs: dict[str, Any] = dc_field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "description": self.description,
            "config": self.config,
            "passed": self.passed,
            "inputs": self.inputs,
            "observations": self.observations,
        }


def _env_for(base: FrozenEnvironment, run_dir: Path, objectives: Sequence[Mapping[str, str]],
             *, emit_timing: bool, front_max_size: int) -> FrozenEnvironment:
    return FrozenEnvironment(
        run_dir=run_dir,
        theta=base.theta,
        objectives=tuple(dict(item) for item in objectives),
        islands=(ISLAND,),
        pareto_front_max_size=front_max_size,
        pareto_epsilon=base.pareto_epsilon,
        admission_policy="pareto",
        experiment_root_commit=base.experiment_root_commit,
        campaign_program_hash=base.campaign_program_hash,
        worker_evaluator_timeout_seconds=base.worker_evaluator_timeout_seconds,
        worker_evaluator_max_metrics=base.worker_evaluator_max_metrics,
        emit_timing=emit_timing,
    )


def _pick(fields: Mapping[str, Any], objective_values: Sequence[float],
          objective_scores: Sequence[float], measures: Sequence[float], commit: str, ts: float):
    return make_candidate(
        commit_hash=commit,
        objective_values=objective_values,
        objective_scores=objective_scores,
        measures=measures,
        timestamp=ts,
    )


def collection_run(
    env: FrozenEnvironment,
    candidate_set: CandidateSet,
    *,
    candidate_ids: Sequence[str],
) -> dict[str, Any]:
    """Score chosen C* members through the real Evaluator with the real objectives."""

    env.apply()
    collected: dict[str, Any] = {}
    for candidate_id in candidate_ids:
        candidate = candidate_set.by_id(candidate_id)
        runtime_result = run_through_loreley(env, candidate, iteration=0)
        metrics = [dict(item) for item in runtime_result.metrics]
        resolved_values: Sequence[float] = ()
        resolved_scores: Sequence[float] = ()
        error: str | None = None
        try:
            resolved_values, resolved_scores = resolve_objectives(env, metrics)
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            error = f"{type(exc).__name__}: {exc}"
        collected[candidate_id] = {
            "outcome_kind": runtime_result.outcome_kind,
            "metrics": metrics,
            "metric_names": [item["name"] for item in metrics],
            "objective_values": list(resolved_values),
            "objective_scores": list(resolved_scores),
            "objective_resolution_error": error,
            "reuse_kind": runtime_result.reuse_kind,
            "protocol": runtime_result.protocol,
        }
    return collected


def run_a02(
    *,
    contract: EvalContract,
    candidate_set: CandidateSet,
    theta: ThetaE,
    base_run_dir: Path,
) -> dict[str, Any]:
    """Run every A0.2 archive check against the real archive."""

    env_s = _env_for(
        FrozenEnvironment(run_dir=base_run_dir / "config-s", theta=theta),
        base_run_dir / "config-s",
        CONFIG_S_OBJECTIVES,
        emit_timing=False,
        front_max_size=8,
    )
    env_m = _env_for(
        FrozenEnvironment(run_dir=base_run_dir / "config-m", theta=theta),
        base_run_dir / "config-m",
        CONFIG_M_OBJECTIVES,
        emit_timing=True,
        front_max_size=4,
    )

    collected_s = collection_run(env_s, candidate_set, candidate_ids=("c01_good_hex", "c02_baseline_upstream"))
    collected_m = collection_run(
        env_m, candidate_set, candidate_ids=("c01_good_hex", "c02_baseline_upstream")
    )

    checks: list[CheckResult] = []
    checks.append(_same_cell_replacement(env_s, collected_s))
    checks.append(_cross_cell_control(env_s, "config-s-single-objective", {"composite_score": 0.75},
                                      {"composite_score": 0.25}))
    checks.append(_report_branch(env_s, selected_check=checks[0]))
    checks.append(_regime_control(env_s, env_m))
    checks.append(_cross_cell_control_multi(env_m))
    checks.append(_sampling_score_independent(env_m))
    checks.append(_report_branch_reflects_multi(env_m))

    return {
        "schema": A02_SCHEMA,
        "runtime": "loreley",
        "task": "circle-packing",
        "eid_star": contract.eid_star,
        "theta_E": theta.as_trace(),
        "frozen_conditions": {
            "single_island": ISLAND,
            "target_dims": TARGET_DIMS,
            "cells_per_dim": CELLS_PER_DIM,
            "cell_grid": f"{CELLS_PER_DIM}^{TARGET_DIMS}",
            "mapelites_pareto_epsilon": env_s.pareto_epsilon,
            "admission_policy": "pareto",
            "config_s": {
                "objectives": [dict(item) for item in CONFIG_S_OBJECTIVES],
                "pareto_front_max_size": env_s.pareto_front_max_size,
                "note": "the runtime's default objective name; the regime the acceptance work analysed",
            },
            "config_m": {
                "objectives": [dict(item) for item in CONFIG_M_OBJECTIVES],
                "pareto_front_max_size": env_m.pareto_front_max_size,
                "note": "the checkout's own circle-packing example objective list",
            },
        },
        "regime_note": REGIME_NOTE,
        "meaningful_control_config": "config-m-multi-objective",
        "real_evaluations": {"config_s": collected_s, "config_m": collected_m},
        "checks": [check.as_dict() for check in checks],
        "verdict": "pass" if all(check.passed for check in checks) else "fail",
        "failed_checks": [check.check_id for check in checks if not check.passed],
    }


# --------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------


def _same_cell_replacement(env: FrozenEnvironment, collected: Mapping[str, Any]) -> CheckResult:
    """A02-L1: c_1 replaces c_2 inside one cell; measured on real evaluated scores."""

    archive = build_archive(env, target_dims=TARGET_DIMS, cells_per_dim=CELLS_PER_DIM)

    def _scalar(entry: Mapping[str, Any]) -> float:
        metrics = entry["metrics"]
        explicit = [item for item in metrics if item["name"] == "composite_score"]
        if explicit:
            return float(explicit[0]["value"])
        by_name = {item["name"]: item["value"] for item in metrics}
        return float(by_name["sum_radii"])

    value_1 = _scalar(collected["c01_good_hex"])
    value_2 = _scalar(collected["c02_baseline_upstream"])
    c1_metrics = [_m("composite_score", value_1)]
    c2_metrics = [_m("composite_score", value_2)]

    values_1, scores_1 = resolve_objectives(env, c1_metrics)
    values_2, scores_2 = resolve_objectives(env, c2_metrics)

    measures = (0.25, 0.25)  # frozen condition: identical descriptor/measures => same cell
    cell = int(archive.index_of([measures])[0])

    alpha_2 = _pick(values_2, values_2, scores_2, measures, "c02_baseline_upstream", 1.0)
    outcome_2 = archive.add(alpha_2)
    alpha_1 = _pick(values_1, values_1, scores_1, measures, "c01_good_hex", 2.0)
    outcome_1 = archive.add(alpha_1)

    front = [item.commit_hash for item in archive.front(cell)]
    members = [item.commit_hash for item in archive.records()]
    gap = abs(value_1 - value_2)
    passed = (
        outcome_2.retained
        and outcome_2.removed_commit_hashes == ()
        and outcome_1.retained
        and tuple(outcome_1.removed_commit_hashes) == ("c02_baseline_upstream",)
        and front == ["c01_good_hex"]
        and "c02_baseline_upstream" not in members
        and gap > env.pareto_epsilon
    )
    return CheckResult(
        check_id="A02-L1",
        description=(
            "same cell (identical measures): c_1 admitted as a replacement and c_2 removed "
            "from that cell; |delta| > epsilon so the outcome is score-decided"
        ),
        config="config-s-single-objective",
        passed=passed,
        inputs={
            "measures": list(measures),
            "cell_index": cell,
            "source": "real evaluation of C* members",
            "c01_good_hex_scalar": value_1,
            "c02_baseline_upstream_scalar": value_2,
            "gap": gap,
            "epsilon": env.pareto_epsilon,
        },
        observations={
            "add_c2": {
                "retained": outcome_2.retained,
                "cell_index": outcome_2.cell_index,
                "removed_commit_hashes": list(outcome_2.removed_commit_hashes),
            },
            "add_c1_after_c2": {
                "retained": outcome_1.retained,
                "cell_index": outcome_1.cell_index,
                "removed_commit_hashes": list(outcome_1.removed_commit_hashes),
            },
            "front_in_cell": front,
            "archive_members": members,
            "single_candidate_batch": True,
            "batch_note": (
                "candidates are added one at a time because _build_add_outcomes only fills "
                "removed_commit_hashes for a single-candidate batch (pareto_archive.py:407)"
            ),
        },
    )


def _cross_cell_control(
    env: FrozenEnvironment,
    config_label: str,
    c1_value: Mapping[str, float],
    c2_value: Mapping[str, float],
) -> CheckResult:
    """A02-L3 under a single objective: a higher score in another cell must not evict."""

    archive = build_archive(env, target_dims=TARGET_DIMS, cells_per_dim=CELLS_PER_DIM)
    values_2, scores_2 = resolve_objectives(
        env, [_m(k, v) for k, v in c2_value.items()]
    )
    values_1, scores_1 = resolve_objectives(
        env, [_m(k, v) for k, v in c1_value.items()]
    )

    measures_c2 = (0.25, 0.25)
    measures_c1 = (0.75, 0.25)
    cell_c2 = int(archive.index_of([measures_c2])[0])
    cell_c1 = int(archive.index_of([measures_c1])[0])

    archive.add(_pick(values_2, values_2, scores_2, measures_c2, "c02_baseline_upstream", 1.0))
    outcome = archive.add(_pick(values_1, values_1, scores_1, measures_c1, "c01_good_hex", 2.0))

    passed = (
        cell_c1 != cell_c2
        and outcome.retained
        and outcome.removed_commit_hashes == ()
        and [item.commit_hash for item in archive.front(cell_c2)] == ["c02_baseline_upstream"]
        and "c02_baseline_upstream" in [item.commit_hash for item in archive.records()]
    )
    return CheckResult(
        check_id="A02-L3",
        description=(
            "different cells: a strictly higher score must NOT evict the other cell's member"
        ),
        config=config_label,
        passed=passed,
        inputs={
            "c1": dict(c1_value),
            "c2": dict(c2_value),
            "measures_c1": list(measures_c1),
            "measures_c2": list(measures_c2),
            "cell_c1": cell_c1,
            "cell_c2": cell_c2,
        },
        observations={
            "add_c1_retained": outcome.retained,
            "add_c1_removed": list(outcome.removed_commit_hashes),
            "front_c2_cell": [item.commit_hash for item in archive.front(cell_c2)],
            "front_c1_cell": [item.commit_hash for item in archive.front(cell_c1)],
        },
    )


def _cross_cell_control_multi(env: FrozenEnvironment) -> CheckResult:
    """A02-L3 under two objectives: the configuration where the control discriminates."""

    archive = build_archive(env, target_dims=TARGET_DIMS, cells_per_dim=CELLS_PER_DIM)
    # Frozen control vectors: c_1 is better on the primary objective, c_2 on the
    # secondary one, and they sit in different cells.
    c2 = [{"name": "sum_radii", "value": 2.0, "higher_is_better": True},
          {"name": "runtime_p50_ms", "value": 1.0, "higher_is_better": False}]
    c1 = [{"name": "sum_radii", "value": 3.0, "higher_is_better": True},
          {"name": "runtime_p50_ms", "value": 9.0, "higher_is_better": False}]
    values_2, scores_2 = resolve_objectives(env, c2)
    values_1, scores_1 = resolve_objectives(env, c1)

    measures_c2 = (0.25, 0.25)
    measures_c1 = (0.75, 0.25)
    cell_c2 = int(archive.index_of([measures_c2])[0])
    cell_c1 = int(archive.index_of([measures_c1])[0])

    archive.add(_pick(values_2, values_2, scores_2, measures_c2, "c2", 1.0))
    outcome = archive.add(_pick(values_1, values_1, scores_1, measures_c1, "c1", 2.0))

    passed = (
        outcome.retained
        and outcome.removed_commit_hashes == ()
        and [item.commit_hash for item in archive.front(cell_c2)] == ["c2"]
    )
    return CheckResult(
        check_id="A02-L3-M",
        description=(
            "different cells, multi-objective: c_1 has the higher primary score and still "
            "does not evict c_2"
        ),
        config="config-m-multi-objective",
        passed=passed,
        inputs={
            "c1_objective_values": list(values_1),
            "c2_objective_values": list(values_2),
            "c1_objective_scores": list(scores_1),
            "c2_objective_scores": list(scores_2),
            "cell_c1": cell_c1,
            "cell_c2": cell_c2,
        },
        observations={
            "add_c1_retained": outcome.retained,
            "add_c1_removed": list(outcome.removed_commit_hashes),
            "front_c2_cell": [item.commit_hash for item in archive.front(cell_c2)],
            "members": [item.commit_hash for item in archive.records()],
        },
    )


def _regime_control(env_s: FrozenEnvironment, env_m: FrozenEnvironment) -> CheckResult:
    """The same cell, the same two candidates, opposite outcomes in the two configs.

    Under one objective the archive is the per-cell argmax, so the better primary
    replaces the worse. Under two objectives the pair is non-dominated, so both are
    retained and the front has two members. This is the test that shows *which*
    configuration makes the cross-cell control meaningful.
    """

    measures = (0.25, 0.25)
    c1 = {"sum_radii": 2.4519205208433132, "runtime_p50_ms": 9.0}
    c2 = {"sum_radii": 0.25, "runtime_p50_ms": 1.0}

    def _run(env: FrozenEnvironment, primary_name: str) -> dict[str, Any]:
        archive = build_archive(env, target_dims=TARGET_DIMS, cells_per_dim=CELLS_PER_DIM)
        metrics_2 = [_m(primary_name, c2["sum_radii"])]
        metrics_1 = [_m(primary_name, c1["sum_radii"])]
        if env.objectives and len(env.objectives) > 1:
            metrics_2 = [
                {"name": "sum_radii", "value": c2["sum_radii"], "higher_is_better": True},
                {"name": "runtime_p50_ms", "value": c2["runtime_p50_ms"], "higher_is_better": False},
            ]
            metrics_1 = [
                {"name": "sum_radii", "value": c1["sum_radii"], "higher_is_better": True},
                {"name": "runtime_p50_ms", "value": c1["runtime_p50_ms"], "higher_is_better": False},
            ]
        values_2, scores_2 = resolve_objectives(env, metrics_2)
        values_1, scores_1 = resolve_objectives(env, metrics_1)
        archive.add(_pick(values_2, values_2, scores_2, measures, "c2", 1.0))
        outcome = archive.add(_pick(values_1, values_1, scores_1, measures, "c1", 2.0))
        cell = int(archive.index_of([measures])[0])
        return {
            "removed": list(outcome.removed_commit_hashes),
            "front": [item.commit_hash for item in archive.front(cell)],
            "objective_values_c2": list(values_2),
            "objective_values_c1": list(values_1),
        }

    single = _run(env_s, "composite_score")
    multi = _run(env_m, "sum_radii")
    passed = (
        single["front"] == ["c1"]
        and multi["front"] == ["c1", "c2"]
    )
    return CheckResult(
        check_id="A02-L8",
        description=(
            "regime control: same cell, same pair; single objective replaces (per-cell "
            "argmax), two objectives retain both (non-dominated front of size 2)"
        ),
        config="config-s-single-objective vs config-m-multi-objective",
        passed=passed,
        inputs={"c1": c1, "c2": c2, "measures": list(measures)},
        observations={
            "single_objective": single,
            "multi_objective": multi,
            "interpretation": REGIME_NOTE,
        },
    )


def _sampling_score_independent(env: FrozenEnvironment) -> CheckResult:
    """A02-L7: the base-candidate sampler ignores score."""

    archive = build_archive(env, target_dims=TARGET_DIMS, cells_per_dim=CELLS_PER_DIM)
    metrics_a = [
        {"name": "sum_radii", "value": 1.0, "higher_is_better": True},
        {"name": "runtime_p50_ms", "value": 1.0, "higher_is_better": False},
    ]
    metrics_b = [
        {"name": "sum_radii", "value": 99.0, "higher_is_better": True},
        {"name": "runtime_p50_ms", "value": 1.0, "higher_is_better": False},
    ]
    values_a, scores_a = resolve_objectives(env, metrics_a)
    values_b, scores_b = resolve_objectives(env, metrics_b)
    archive.add(_pick(values_a, values_a, scores_a, (0.25, 0.25), "aaa", 1.0))
    archive.add(_pick(values_b, values_b, scores_b, (0.75, 0.75), "bbb", 2.0))

    rng = random.Random(20260920)
    draws = archive.sample(4000, rng=rng)
    counts = {"aaa": 0, "bbb": 0}
    for item in draws:
        counts[item.commit_hash] = counts.get(item.commit_hash, 0) + 1
    total = sum(counts.values()) or 1
    frequency = {key: value / total for key, value in counts.items()}
    # two occupied cells, uniform cell pick then uniform member => 0.5 each
    passed = all(abs(value - 0.5) < 0.05 for value in frequency.values())
    return CheckResult(
        check_id="A02-L7",
        description="sampling is score-independent: per-cell pick frequency is ~0.5/0.5",
        config="config-m-multi-objective",
        passed=passed,
        inputs={"draws": total, "rng_seed": 20260920, "cell_a": "aaa", "cell_b": "bbb"},
        observations={"frequency": frequency, "counts": counts},
    )


def _report_branch(env: FrozenEnvironment, *, selected_check: CheckResult) -> CheckResult:
    """A02-L5: the report branch points at c_1 after the same-cell replacement."""

    observations = selected_check.observations
    cell_index = observations["add_c1_after_c2"]["cell_index"]
    c1_value = selected_check.inputs["c01_good_hex_scalar"]
    c2_value = selected_check.inputs["c02_baseline_upstream_scalar"]
    members = [
        {
            "commit_hash": "c02_baseline_upstream",
            "value": c2_value,
            "cell_index": cell_index,
            "objective_values": [c2_value],
            "measures": selected_check.inputs["measures"],
            "timestamp": 1.0,
        },
        {
            "commit_hash": "c01_good_hex",
            "value": c1_value,
            "cell_index": cell_index,
            "objective_values": [c1_value],
            "measures": selected_check.inputs["measures"],
            "timestamp": 2.0,
        },
    ]
    probe = probe_report_branch(env, island_id=ISLAND, members=members)
    passed = probe.best_commit_hash == "c01_good_hex"
    return CheckResult(
        check_id="A02-L5",
        description=(
            "report branch (best-primary-commit query over archive membership) resolves to c_1"
        ),
        config="config-s-single-objective",
        passed=passed,
        inputs={"members": members, "island_id": ISLAND,
                "primary_metric_name": probe.primary_metric_name},
        observations={
            "resolved_best_commit_hash": probe.best_commit_hash,
            "meta": dict(probe.meta),
            "note": (
                "the report is a global argmax over retained members, so it must not be used "
                "as the cross-cell control"
            ),
        },
    )


def _report_branch_reflects_multi(env: FrozenEnvironment) -> CheckResult:
    """The report branch under Config M: it follows the retained primary, not the eviction.

    With two members kept in one cell and a third, higher-primary member kept in
    another, the report still returns the global best *retained* primary - which is
    the behaviour that makes the report branch unusable as a cross-cell control.
    """

    members = [
        {"commit_hash": "c_low", "value": 1.0, "cell_index": 68,
         "objective_values": [1.0, 50.0], "measures": [0.25, 0.25], "timestamp": 1.0},
        {"commit_hash": "c_mid", "value": 2.0, "cell_index": 68,
         "objective_values": [2.0, 40.0], "measures": [0.25, 0.25], "timestamp": 2.0},
        {"commit_hash": "c_high", "value": 9.0, "cell_index": 196,
         "objective_values": [9.0, 60.0], "measures": [0.75, 0.25], "timestamp": 3.0},
    ]
    probe = probe_report_branch(env, island_id=ISLAND, members=members)
    passed = probe.best_commit_hash == "c_high"
    return CheckResult(
        check_id="A02-L5-M",
        description=(
            "report branch under two objectives returns the global best primary among "
            "retained members (why it cannot serve as the cross-cell control)"
        ),
        config="config-m-multi-objective",
        passed=passed,
        inputs={"members": members},
        observations={
            "resolved_best_commit_hash": probe.best_commit_hash,
            "primary_metric_name": probe.primary_metric_name,
        },
    )
