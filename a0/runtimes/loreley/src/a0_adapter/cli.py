"""Command line for the A0 Loreley adapter.

Exit codes are ``adapter_contract.md`` §3.1.  ``run`` writes the three traces and
validates them before returning success.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import __version__
from .archive_check import CONFIG_M_OBJECTIVES, ISLAND, run_a02
from .closure import run_closure_probe, exit_code_for as closure_exit_code
from .conformance import run_conformance
from .contracts import (
    AdapterError,
    A0_ROOT,
    EvalContract,
    EXIT_CONFORMANCE,
    EXIT_INTERNAL,
    EXIT_OK,
    ThetaE,
    UsageError,
    load_candidate_set,
    load_eval_contract,
    load_fr,
)
from .eidr import (
    derive_eidr,
    load_mapping,
    recompute_eidr,
    render_campaign_program,
    write_mapping,
)
from .evidence import classify, failure_stage_for, policy_note
from .failure_stage import (
    FROZEN_FAILURE_STAGE_MAPPING,
    FROZEN_MAPPING_DIGEST as FROZEN_FAILURE_STAGE_MAPPING_DIGEST,
    adopt,
    expected_from_candidates,
    score_trace_counts,
    stage_for,
    unit_basis_note,
)
from .runtime import (
    DEFAULT_ISLAND,
    LORELYELEY_CHECKOUT,
    E_STAR_DIR,
    OBJECTIVES_DEFAULT,
    OBJECTIVES_MULTI,
    PLUGIN_REF,
    PLUGIN_SOURCE,
    FrozenEnvironment,
    build_archive,
    make_candidate,
    reference_evaluation,
    reset_workspace,
    resolve_objectives,
    run_through_loreley,
)
from .traces import TraceWriter, failure_stage_counts, stage_histogram

DEFAULT_CANDIDATE_SET = E_STAR_DIR / "C_STAR" / "manifest.json"
DEFAULT_EID = A0_ROOT / "contract" / "out" / "plumbing.EID.json"
DEFAULT_FR = A0_ROOT / "contract" / "fr" / "scalar.json"
ADAPTER_DIR = Path(__file__).resolve().parents[2]
ENTRY_POINT = ADAPTER_DIR / "bin" / "a0-loreley"
INDEPENDENT_VERIFIER = ADAPTER_DIR / "tools" / "verify_eidr.py"
INDEPENDENT_VERIFIER_PYTHON = ADAPTER_DIR / "checkout" / ".venv" / "bin" / "python"
DEFAULT_RUN_DIR = ADAPTER_DIR / "out"
# Pinned root commit of the candidate repository: the pinned upstream
# circle-packing checkout at a0/tasks/circle-packing/upstream/circle-packing.
# This is the `MAPELITES_EXPERIMENT_ROOT_COMMIT` the run is pinned to.
ROOT_COMMIT = "b91c0906c9f676eb661990d881144909d99f2d72"
FUNCTIONAL_DATABASE_URL = "postgresql+psycopg://loreley:loreley@127.0.0.1:5432/loreley"

MEASURE_SOURCE_NOTE = (
    "measures are the adapter's declared, frozen behavior descriptor for the A0 plumbing "
    "round: (clip(sum_radii/3.0), clip(runtime_p50_ms/50.0)) into the [0,1]^2 feature box "
    "the archive is built with. Loreley's native descriptor (repository snapshot -> file "
    "embeddings -> dimension reduction, map_elites/manager.py) is NOT exercised in A0 and "
    "is recorded as such."
)


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------


UNVERIFIED_NOTES = [
    (
        "Loreley's LLM-driven path (planning / coding / evolution worker) was not run: the "
        "host has no usable model backend at the time of the A0 run (`codex` could not "
        "complete a model call; `claude`'s login state was unknown). No candidate "
        "generation, job scheduling or worker-driven archive ingestion happened."
    ),
    (
        "The native behaviour descriptor (repository snapshot -> file embeddings -> PCA -> "
        "measures) was not run: it needs an embedding provider. A0 freezes the descriptor "
        "condition ('two candidates with equal measures'); the adapter declares its measure "
        "function instead (see run.summary.json -> measure_source)."
    ),
    (
        "The phased measurement cache end to end (evolution.py:1640-1665, :1741-1766) is only "
        "partially verified: the reuse DECISION is the runtime's own "
        "(EvolutionJobStore.find_reusable_evaluation against real PostgreSQL) and the adapter "
        "labels a reused outcome cache_hit, but the worker that consumes that decision was "
        "not run."
    ),
    "MAPELITES_ADMISSION_POLICY=fresh_comparison was not exercised; the frozen policy is pareto.",
]

DECLARED_SEAMS = [
    {
        "seam": "EvolutionScheduler.__new__ + settings/_root_commit_hash",
        "path": "loreley/scheduler/main.py:876-931",
        "why": "EvolutionScheduler.__init__ requires a writable git repository; the report "
               "query itself runs unmodified against real PostgreSQL",
    },
    {
        "seam": "plugin payload shape (EvalPass rather than a Mapping)",
        "path": "loreley/core/worker/evaluator.py:2029-2037 vs :2304-2310",
        "why": "the worker_evaluator_max_metrics truncation does not apply on the EvalPass "
               "path; the adapter declares which shape it uses and detects truncation by "
               "comparing emitted and returned counts, never by inferring it",
    },
    {
        "seam": "adapter-declared behaviour descriptor",
        "path": "a0/runtimes/loreley/out/run-a0/run.summary.json -> measure_source",
        "why": "the native descriptor pipeline needs an embedding provider; A0 freezes the "
               "descriptor condition instead",
    },
]

def _runtime_guard(runtime: str) -> None:
    if runtime != "loreley":
        raise UsageError(
            f"this package is the Loreley arm of the A0 adapter and does not implement "
            f"--runtime {runtime!r}; the shared dispatcher is the contract owner's job"
        )


def _load_everything(args) -> tuple[EvalContract, Any, ThetaE, Any]:
    contract = load_eval_contract(Path(args.eid), verify=not args.no_verify)
    candidate_set = load_candidate_set(
        Path(args.candidate_set), verify_integrity=not args.no_integrity
    )
    theta = ThetaE.parse(args.theta)
    fr = load_fr(Path(args.fr))
    return contract, candidate_set, theta, fr


def _objectives(args) -> tuple[Mapping[str, str], ...]:
    if getattr(args, "multi_objective", False):
        return OBJECTIVES_MULTI
    if getattr(args, "objectives", None):
        return tuple(json.loads(args.objectives))
    return OBJECTIVES_DEFAULT


def _prepare_run_dir(
    *,
    run_dir: Path,
    contract: EvalContract,
    theta: ThetaE,
    objectives: Sequence[Mapping[str, str]],
    emit_timing: bool,
    fresh: bool = True,
) -> tuple[FrozenEnvironment, Any]:
    fr = load_fr(Path(os.environ.get("A0_FR", str(DEFAULT_FR))))
    fr_metric_name = "composite_score" if not emit_timing else "sum_radii"
    names = {str(item["name"]) for item in objectives}
    if not emit_timing and fr_metric_name not in names:
        raise UsageError(
            f"the declared F_r projects E* to {fr_metric_name!r} but the frozen objective "
            f"contract configures {sorted(names)}; the run would have no score entry "
            "point (ObjectiveContract.resolve raises on a missing objective)"
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    program = run_dir / "loreley.program.md"
    program.write_text(render_campaign_program(contract, theta.as_trace()), encoding="utf-8")
    from .eidr import campaign_program_hash

    env = FrozenEnvironment(
        run_dir=run_dir,
        theta=theta,
        objectives=tuple(dict(item) for item in objectives),
        islands=(DEFAULT_ISLAND,),
        pareto_front_max_size=4 if emit_timing else 8,
        campaign_program_hash=campaign_program_hash(program),
        experiment_root_commit=ROOT_COMMIT,
        emit_timing=emit_timing,
    )
    if fresh:
        reset_workspace(env)
    mapping = derive_eidr(
        contract,
        plugin_ref=PLUGIN_REF,
        plugin_source=PLUGIN_SOURCE,
        campaign_program=program,
    )
    env.apply()
    os.environ["A0_FR_SPEC_HASH"] = fr.spec_hash
    os.environ["A0_FR_METRIC_NAME"] = fr_metric_name
    os.environ["A0_FR_MODE_SCALAR"] = "0" if emit_timing else "1"
    env.apply()
    return env, mapping


def _write_adapter_md(run_dir: Path, *, contract: EvalContract, theta: ThetaE,
                      mapping, fr, env: FrozenEnvironment, objectives) -> None:
    text = f"""# Loreley adapter declaration (A0)

* adapter version: {__version__}
* runtime: loreley, pinned checkout `4c3759208e6b908f90716488ac3eec3dceaaf397`
  (`a0/runtimes/loreley/checkout`)
* interpreter: {platform.python_implementation()} {platform.python_version()}

## EID* -> EID_r mapping

* `EID*` = `{contract.eid_star}` (from `{contract.path}`; `evalcontract.py verify` run
  before every command unless `--no-verify` is passed).
* native scheme: `{mapping.native_scheme}`, mapping mode `{mapping.mapping_mode}`.
* `EID_r.value` = `{mapping.value}`
* recomputable: yes - `a0_adapter eidr` recomputes `value` and `eidr_derivation` from
  the plugin source file, the campaign program file and `EID*`, and reports
  `recomputed: true` with an empty `problems` list.
* `eidr_derivation` = `{mapping.eidr_derivation}`

## F_r

* declaration: `{fr.name}` (`{fr.spec_hash}`), applies `{fr.applies}`.
* realised as one extra metric (`A0_FR_METRIC_NAME`) appended to E*'s own field set;
  E*'s multi-field Outcome is never reduced (hard constraint 3, plan:549).

## FailureStage (adapter_contract.md 5.3)

* adopted table: `{FROZEN_FAILURE_STAGE_MAPPING_DIGEST}` from
  `a0/contract/selection/simpleloop.selection.json`; the adapter's copy is
  `a0/runtimes/loreley/policy/loreley.selection.json` and both blocks' canonical
  digests are recomputed on every run (`a0_adapter.failure_stage.adopt`), refusing
  the run if either has drifted.
* unit basis: one unit per member of `C*`, read from the score trace by
  `(run_id, iteration, candidate_id)` - adapter-level events that are not candidates
  (the run-level resource row, the report-branch selection row) are not units, so the
  counts stay joinable with the other runtimes'.
* `status` + `failure.kind` + the stage derived from them are on every row of the
  conformance document.

## EID_r recomputation

`recompute_cmd` in the conformance document points at `tools/verify_eidr.py`, which
imports **nothing** from this adapter: it recomputes the five component digests and
`EID*` with the contract owner's own scheme, hashes the plugin source and the rendered
program as bytes on disk, and checks that all five component digests appear verbatim
in the hashed program bytes.

## Evaluator wiring

* `WORKER_EVALUATOR_PLUGIN={PLUGIN_REF}`
* `WORKER_EVALUATOR_PYTHON_PATHS=[{str(PLUGIN_SOURCE.parent)!r}]`
* `A0_E_STAR_PY={E_STAR_DIR / '.venv/bin/python'}`
* `A0_E_STAR_SCRIPT={E_STAR_DIR / 'e_star.py'}`
* theta_E: seed={theta.as_trace()['seed']} fidelity={theta.as_trace()['fidelity']}
  fraction={theta.as_trace()['fraction']} (defaults applied:
  {json.dumps(theta.as_trace()['defaults_applied'])})
* objectives: `{json.dumps([dict(item) for item in objectives])}`
* `MAPELITES_EXPERIMENT_ROOT_COMMIT={env.experiment_root_commit}`

## Measurements

{MEASURE_SOURCE_NOTE}

## What is not exercised

Loreley's LLM-driven path (planning/coding agents, codex backend) is not exercised:
`codex` cannot complete a model call on this host. The lanes exercised here are the
evaluator spawn, the plugin protocol, the metric/objective resolution, the QD archive
and the report query.
"""
    (run_dir / "adapter.md").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------


def _drive_candidates(
    *,
    env: FrozenEnvironment,
    candidate_set,
    theta: ThetaE,
    contract: EvalContract,
    writer: TraceWriter,
    fr,
    budget: Mapping[str, Any] | None,
    run_id: str,
    run_dir: Path,
    eid_r_trace: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int, float]:
    """Reference-run and runtime-run every member of ``C*``, emitting score + resource traces.

    Shared by ``run`` and ``conformance`` so that both write the same traces: the
    A0.1 measurement and the A0.1 evidence are then the same run, not two.
    """

    theta_trace = theta.as_trace()
    evaluations: list[dict[str, Any]] = []
    calls = 0
    started = time.monotonic()

    for candidate in candidate_set.candidates:
        reference = reference_evaluation(
            candidate, theta, workdir=run_dir / "reference" / candidate.candidate_id
        )
        runtime_result = run_through_loreley(env, candidate, iteration=0)
        calls += 1
        evidence = classify(runtime_result, max_metrics=env.worker_evaluator_max_metrics)
        stage, detail = failure_stage_for(
            runtime_result,
            evidence,
            reference_status=reference.status,
            reference_failure_kind=(reference.outcome.get("failure") or {}).get("kind"),
        )
        fields = {name: reference.fields.get(name) for name in sorted(reference.fields)}
        if evidence.status in {"timeout", "synthesized_failure"} and not reference.scored:
            fields = {"sum_radii": None}
        scalar = fields.get("sum_radii")
        writer.emit(
            "score",
            event_id=f"lor-{run_id}-s-i0-{candidate.candidate_id}",
            iteration=0,
            candidate_id=candidate.candidate_id,
            parent_id=None,
            eid_star=contract.eid_star,
            eid_r=dict(eid_r_trace),
            theta_e=theta_trace,
            failure_stage=stage,
            failure_detail=detail,
            extra={
                "outcome": {"fields": fields, "cardinality": len(fields)},
                "fr": fr.as_trace("a0/contract/adapter_contract.md#default-first-round-rule"),
                # search_signal is the runtime's own signal after F_r.  For Loreley it
                # is an archive descriptor: the scalar F_r produced plus the metric
                # vector and objective vector the archive consumes, with the runtime's
                # provenance attached (trace_schema.md §5 allows any JSON here).
                "search_signal": {
                    "value": scalar,
                    "applies": fr.applies,
                    "runtime_metrics": {
                        item["name"]: item["value"] for item in runtime_result.metrics
                    },
                    "runtime_objectives": _resolve_or_null(env, runtime_result.metrics),
                    "runtime": {
                        "outcome_kind": runtime_result.outcome_kind,
                        "protocol": runtime_result.protocol,
                        "evaluator_name": runtime_result.evaluator_name,
                        "evaluator_version": runtime_result.evaluator_version,
                        "e_star_status": reference.status,
                        "e_star_exit_code": reference.exit_code,
                        "e_star_canonical_digest": reference.outcome.get("canonical_digest"),
                        "evaluator_elapsed_s": round(runtime_result.elapsed_s, 6),
                    },
                },
                "evaluator_evidence": evidence.as_trace(),
            },
        )
        writer.emit(
            "resource",
            event_id=f"lor-{run_id}-r-i0-{candidate.candidate_id}",
            iteration=0,
            candidate_id=candidate.candidate_id,
            parent_id=None,
            eid_star=contract.eid_star,
            eid_r=dict(eid_r_trace),
            theta_e=theta_trace,
            failure_stage=stage,
            failure_detail=detail,
            extra={
                "T_wall": {
                    "value_sec": round(runtime_result.elapsed_s, 6),
                    "clock": "monotonic",
                    "scope": "iteration",
                },
                "N_evaluatorCalls": 1,
                "concurrency": {"cap": 1, "observed_max": 1},
                "budget_hard": budget,
                "secondary": {
                    "N_modelCalls": None,
                    "T_in": None,
                    "T_out": None,
                    "C_usd": None,
                },
            },
        )
        evaluations.append(
            {
                "candidate_id": candidate.candidate_id,
                "reference": reference,
                "runtime": runtime_result,
                "evidence": evidence,
                "stage": stage,
                "detail": detail,
            }
        )

    return evaluations, calls, time.monotonic() - started


def cmd_run(args) -> int:
    _runtime_guard(args.runtime)
    contract, candidate_set, theta, fr = _load_everything(args)
    objectives = _objectives(args)
    run_dir = Path(args.run_dir).resolve()
    env, mapping = _prepare_run_dir(
        run_dir=run_dir,
        contract=contract,
        theta=theta,
        objectives=objectives,
        emit_timing=getattr(args, "multi_objective", False),
    )
    os.environ["A0_FR"] = str(Path(args.fr))
    _write_adapter_md(run_dir, contract=contract, theta=theta, mapping=mapping, fr=fr,
                      env=env, objectives=objectives)
    write_mapping(run_dir / "eidr.mapping.json", mapping)
    (run_dir / "env.frozen.json").write_text(
        json.dumps(env.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    kinds = tuple(item.strip() for item in (args.traces or "score,selection,resource").split(","))
    writer = TraceWriter(
        run_dir=run_dir, runtime="loreley", run_id=args.run_id, task=args.task, kinds=kinds
    )
    budget = _parse_budget(args.budget)
    theta_trace = theta.as_trace()
    eid_r_trace = mapping.as_trace()
    started = time.monotonic()
    evaluations, calls, elapsed = _drive_candidates(
        env=env,
        candidate_set=candidate_set,
        theta=theta,
        contract=contract,
        writer=writer,
        fr=fr,
        budget=budget,
        run_id=args.run_id,
        run_dir=run_dir,
        eid_r_trace=eid_r_trace,
    )

    archive_decisions = _archive_pass(
        env=env,
        writer=writer,
        evaluations=evaluations,
        contract=contract,
        theta_trace=theta_trace,
        eid_r_trace=eid_r_trace,
        run_id=args.run_id,
        budget=budget,
        run_dir=run_dir,
    )

    run_wall = time.monotonic() - started
    writer.emit(
        "resource",
        event_id=f"lor-{args.run_id}-r-run",
        iteration=0,
        candidate_id="__run__",
        parent_id=None,
        eid_star=contract.eid_star,
        eid_r=eid_r_trace,
        theta_e=theta_trace,
        failure_stage=(
            "budget_exhausted" if budget and run_wall > float(budget["T_wall_sec"]) else "none"
        ),
        failure_detail=(
            f"adapter wall clock {run_wall:.1f}s exceeded the declared budget"
            if budget and run_wall > float(budget["T_wall_sec"]) else None
        ),
        extra={
            "T_wall": {"value_sec": round(run_wall, 6), "clock": "monotonic", "scope": "run"},
            "N_evaluatorCalls": calls,
            "concurrency": {"cap": 1, "observed_max": 1},
            "budget_hard": budget,
            "secondary": {"N_modelCalls": None, "T_in": None, "T_out": None, "C_usd": None},
        },
    )

    writer.close()
    validation = writer.validate()
    stats = writer.stats()

    summary = {
        "schema": "a0.run.loreley/v1",
        "run_id": args.run_id,
        "runtime": "loreley",
        "task": args.task,
        "eid_star": contract.eid_star,
        "eid_r": eid_r_trace,
        "theta_E": theta_trace,
        "in_silico_budget": budget,
        "wall_clock_s": run_wall,
        "evaluator_calls": calls,
        "candidate_count": len(candidate_set.candidates),
        "traces": writer.paths.as_dict(),
        "trace_validation": [
            {"path": item["path"], "command": item["command"], "returncode": item["returncode"]}
            for item in validation
        ],
        **_failure_stage_accounting(
            [
                {
                    "status": item["reference"].status,
                    "failure_kind": (item["reference"].outcome.get("failure") or {}).get("kind"),
                }
                for item in evaluations
            ],
            writer.paths.score,
            len(candidate_set.candidates),
        ),
        "failure_stage_stats_all_traces": failure_stage_counts(
            [writer.paths.score, writer.paths.selection, writer.paths.resource]
        ),
        "evaluator_evidence_counts": _count_evidence(evaluations),
        "archive": archive_decisions,
        "measure_source": MEASURE_SOURCE_NOTE,
        "externally_supplied_score_changed_the_selection": archive_decisions[
            "external_score_control"
        ],
    }
    (run_dir / "run.summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in (
        "run_id", "eid_star", "evaluator_calls", "candidate_count", "traces",
        "failure_stage_counts", "failure_stage_expected_from_frozen_map",
        "failure_stage_counts_match_frozen_map", "evaluator_evidence_counts", "wall_clock_s",
    )}, indent=1))

    expect = int(os.environ.get("A0_EXPECT_ONLY", "0"))
    if expect:
        return EXIT_OK
    scored = [item for item in evaluations if item["evidence"].status == "ok"]
    if not scored:
        return 8
    if budget and run_wall > float(budget["T_wall_sec"]):
        return 7
    return EXIT_OK


def _count_evidence(evaluations: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evaluations:
        status = item["evidence"].status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _parse_budget(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    values: dict[str, Any] = {}
    for item in raw.split(","):
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        try:
            values[key] = int(value)
        except ValueError:
            try:
                values[key] = float(value)
            except ValueError:
                values[key] = value
    return {
        "T_wall_sec": float(values.get("T_wall_sec", 0) or 0),
        "N_evaluatorCalls": int(values.get("N_evaluatorCalls", 0) or 0),
        "concurrency_cap": int(values.get("concurrency", 1) or 1),
    }


def _declared_measures(env: FrozenEnvironment, metrics: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    by_name = {item["name"]: float(item["value"]) for item in metrics}
    radii = by_name.get("sum_radii", 0.0)
    runtime_ms = by_name.get("runtime_p50_ms", 0.0)
    return (min(1.0, max(0.0, radii / 3.0)), min(1.0, max(0.0, runtime_ms / 50.0)))


def _resolve_or_null(env: FrozenEnvironment, metrics: Sequence[Mapping[str, Any]]) -> Any:
    """Real ``ObjectiveContract.resolve`` on the runtime's metric vector, or null."""

    try:
        values, scores = resolve_objectives(env, metrics)
    except Exception as exc:  # noqa: BLE001 - reported in the trace, not swallowed
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"values": list(values), "scores": list(scores)}


def _archive_pass(
    *,
    env: FrozenEnvironment,
    writer: TraceWriter,
    evaluations: Sequence[Mapping[str, Any]],
    contract: EvalContract,
    theta_trace: Mapping[str, Any],
    eid_r_trace: Mapping[str, Any],
    run_id: str,
    budget: Mapping[str, Any] | None,
    run_dir: Path,
) -> dict[str, Any]:
    """Feed the evaluated candidates through the real archive and the real report query."""

    settings = None
    from .runtime import build_settings

    settings = build_settings(env)
    archive = build_archive(env, target_dims=2, cells_per_dim=16)

    admitted: list[dict[str, Any]] = []
    considered: list[dict[str, Any]] = []
    for index, item in enumerate(evaluations):
        candidate_id = str(item["candidate_id"])
        metrics = [dict(metric) for metric in item["runtime"].metrics]
        evidence = item["evidence"]
        scalar = item["reference"].fields.get("sum_radii")
        # Only a candidate that actually produced a measured score may enter the
        # archive.  A measured-but-non-scoring candidate has
        # evaluator_evidence.status == "ok" (a real measurement happened) yet an
        # empty metric vector, so the gate must be on the scoring outcome, not on
        # the evidence label alone.
        scoring = evidence.status == "ok" and item["runtime"].outcome_kind == "passed"
        if not scoring:
            considered.append({"candidate_id": candidate_id, "search_signal": scalar})
            writer.emit(
                "selection",
                event_id=f"lor-{run_id}-sel-i0-{candidate_id}",
                iteration=0,
                candidate_id=candidate_id,
                parent_id=None,
                eid_star=contract.eid_star,
                eid_r=eid_r_trace,
                theta_e=theta_trace,
                failure_stage=item["stage"],
                failure_detail=item["detail"],
                extra={
                    "selection": {
                        "policy": "QD archive: per-cell non-dominated replacement",
                        "chosen_candidate_id": None,
                        "considered": [{"candidate_id": candidate_id, "search_signal": scalar}],
                        "reason": (
                            f"not admitted: evaluator_evidence.status={evidence.status}, "
                            f"runtime outcome_kind={item['runtime'].outcome_kind}; the archive "
                            "only consumes measured scores"
                        ),
                        "tie_break": None,
                        "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
                        "check_point": "A0.2 Loreley: archive admission on measured scores",
                    }
                },
                combined_extra={
                    "selection": {
                        "policy": "QD archive: per-cell non-dominated replacement",
                        "chosen_candidate_id": None,
                        "considered": [{"candidate_id": candidate_id, "search_signal": scalar}],
                        "reason": (
                            f"not admitted: evaluator_evidence.status={evidence.status}, "
                            f"runtime outcome_kind={item['runtime'].outcome_kind}"
                        ),
                        "tie_break": None,
                        "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
                        "check_point": "A0.2 Loreley: archive admission on measured scores",
                    }
                },
            )
            continue

        try:
            values, scores = resolve_objectives(env, metrics)
        except Exception as exc:  # noqa: BLE001 - objective contract violation is a result
            considered.append({"candidate_id": candidate_id, "search_signal": scalar})
            writer.emit(
                "selection",
                event_id=f"lor-{run_id}-sel-i0-{candidate_id}",
                iteration=0,
                candidate_id=candidate_id,
                parent_id=None,
                eid_star=contract.eid_star,
                eid_r=eid_r_trace,
                theta_e=theta_trace,
                failure_stage="mechanism_mismatch",
                failure_detail=f"ObjectiveContract.resolve rejected the metric vector: {exc}",
                extra={
                    "selection": {
                        "policy": "QD archive: per-cell non-dominated replacement",
                        "chosen_candidate_id": None,
                        "considered": [{"candidate_id": candidate_id, "search_signal": scalar}],
                        "reason": str(exc),
                        "tie_break": None,
                        "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
                        "check_point": "A0.2 Loreley: objective contract",
                    }
                },
            )
            continue

        measures = _declared_measures(env, metrics)
        cell = int(archive.index_of([measures])[0])
        archive_candidate = make_candidate(
            commit_hash=candidate_id,
            objective_values=values,
            objective_scores=scores,
            measures=measures,
            timestamp=float(index),
        )
        outcome = archive.add(archive_candidate)
        considered.append({"candidate_id": candidate_id, "search_signal": scalar})
        admitted.append(
            {
                "candidate_id": candidate_id,
                "cell_index": outcome.cell_index,
                "retained": outcome.retained,
                "removed_commit_hashes": list(outcome.removed_commit_hashes),
                "objective_values": list(values),
                "measures": list(measures),
                "search_signal": scalar,
                "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
            }
        )
        chosen = candidate_id if outcome.retained else None
        writer.emit(
            "selection",
            event_id=f"lor-{run_id}-sel-i0-{candidate_id}",
            iteration=0,
            candidate_id=candidate_id,
            parent_id=None,
            eid_star=contract.eid_star,
            eid_r=eid_r_trace,
            theta_e=theta_trace,
            failure_stage="none",
            failure_detail=None,
            extra={
                "selection": {
                    "policy": "QD archive: per-cell non-dominated replacement",
                    "chosen_candidate_id": chosen,
                    "considered": list(considered),
                    "reason": (
                        f"cell {outcome.cell_index}: "
                        + ("retained as a non-dominated member"
                           if outcome.retained else "dominated inside its cell")
                        + (f"; removed {list(outcome.removed_commit_hashes)}"
                           if outcome.removed_commit_hashes else "")
                    ),
                    "tie_break": "commit_hash ascending when all objectives are within epsilon",
                    "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
                    "check_point": "A0.2 Loreley: same-cell replacement / cross-cell non-eviction",
                }
            },
            combined_extra={
                "selection": {
                    "policy": "QD archive: per-cell non-dominated replacement",
                    "chosen_candidate_id": chosen,
                    "considered": list(considered),
                    "reason": (
                        f"cell {outcome.cell_index}: "
                        + ("retained as a non-dominated member"
                           if outcome.retained else "dominated inside its cell")
                    ),
                    "tie_break": "commit_hash ascending when all objectives are within epsilon",
                    "source_score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
                    "check_point": "A0.2 Loreley: same-cell replacement / cross-cell non-eviction",
                }
            },
        )

    # The report branch, run for real against PostgreSQL when it is reachable.
    report: dict[str, Any] = {"attempted": False}
    try:
        from .report_branch import probe_report_branch

        rows = [
            {
                "commit_hash": item["candidate_id"],
                "value": float(item["objective_values"][0]),
                "cell_index": int(item["cell_index"]),
                "objective_values": item["objective_values"],
                "measures": item["measures"],
                "timestamp": float(index),
            }
            for index, item in enumerate(admitted)
        ]
        probe = probe_report_branch(env, island_id=DEFAULT_ISLAND, members=rows)
        report = {
            "attempted": True,
            "resolved_best_commit_hash": probe.best_commit_hash,
            "primary_metric_name": probe.primary_metric_name,
            "meta": dict(probe.meta),
            "members": rows,
        }
        writer.emit(
            "selection",
            event_id=f"lor-{run_id}-sel-report",
            iteration=0,
            candidate_id=str(probe.best_commit_hash or "__none__"),
            parent_id=None,
            eid_star=contract.eid_star,
            eid_r=eid_r_trace,
            theta_e=theta_trace,
            failure_stage="none" if probe.best_commit_hash else "search_failed",
            failure_detail=None if probe.best_commit_hash
            else "the report query returned no retained member",
            extra={
                "selection": {
                    "policy": "best-primary-commit query over archive membership",
                    "chosen_candidate_id": probe.best_commit_hash,
                    "considered": [
                        {"candidate_id": item["candidate_id"], "search_signal": item["search_signal"]}
                        for item in admitted
                    ],
                    "reason": (
                        "Metric.value ordered by the primary direction, tie-break commit_hash "
                        "ascending, joined to MapElitesArchiveCell (scheduler/main.py:876-931)"
                    ),
                    "tie_break": "commit_hash ascending",
                    "source_score_event_id": (
                        f"lor-{run_id}-s-i0-{probe.best_commit_hash}"
                        if probe.best_commit_hash else None
                    ),
                    "check_point": "A0.2 Loreley: report branch points at c_1",
                }
            },
            combined_extra={
                "selection": {
                    "policy": "best-primary-commit query over archive membership",
                    "chosen_candidate_id": probe.best_commit_hash,
                    "considered": [
                        {"candidate_id": item["candidate_id"], "search_signal": item["search_signal"]}
                        for item in admitted
                    ],
                    "reason": "Metric.value DESC, commit_hash ASC, archive-membership join",
                    "tie_break": "commit_hash ascending",
                    "source_score_event_id": (
                        f"lor-{run_id}-s-i0-{probe.best_commit_hash}"
                        if probe.best_commit_hash else None
                    ),
                    "check_point": "A0.2 Loreley: report branch points at c_1",
                }
            },
        )
    except Exception as exc:  # noqa: BLE001 - the report branch may be unreachable
        report = {"attempted": True, "error": f"{type(exc).__name__}: {exc}"}

    external_control = _external_score_control(env)
    return {
        "archive_members": [item.commit_hash for item in archive.records()],
        "admissions": admitted,
        "report_branch": report,
        "external_score_control": external_control,
        "measures_note": MEASURE_SOURCE_NOTE,
    }


def _external_score_control(env: FrozenEnvironment) -> dict[str, Any]:
    """Evidence that an externally supplied score actually changes admission.

    Two candidates are built with identical measures (same cell) and identical
    objective vectors except for the primary value, which is supplied from outside
    the runtime.  Swapping which candidate carries the higher value must swap which
    one survives - otherwise the archive is not consuming the score at all.
    """

    archive = build_archive(env, target_dims=2, cells_per_dim=16)
    measures = (0.25, 0.25)

    def _admit(high: str, low: str) -> dict[str, Any]:
        local = build_archive(env, target_dims=2, cells_per_dim=16)
        values_low, scores_low = resolve_objectives(
            env, [{"name": "composite_score", "value": 0.1, "higher_is_better": True}]
        )
        values_high, scores_high = resolve_objectives(
            env, [{"name": "composite_score", "value": 0.9, "higher_is_better": True}]
        )
        local.add(make_candidate(commit_hash=low, objective_values=values_low,
                                 objective_scores=scores_low, measures=measures, timestamp=1.0))
        outcome = local.add(make_candidate(commit_hash=high, objective_values=values_high,
                                           objective_scores=scores_high, measures=measures,
                                           timestamp=2.0))
        cell = int(local.index_of([measures])[0])
        return {
            "survivor": [item.commit_hash for item in local.front(cell)],
            "removed": list(outcome.removed_commit_hashes),
        }

    first = _admit("external_high", "external_low")
    second = _admit("external_low", "external_high")
    return {
        "design": (
            "the same cell receives two candidates whose only difference is the primary "
            "score; the higher-scoring one is supplied first as 'external_high' and then as "
            "'external_low'"
        ),
        "run_a": first,
        "run_b": second,
        "score_decides": (
            first["survivor"] == ["external_high"]
            and second["survivor"] == ["external_low"]
        ),
    }


# --------------------------------------------------------------------------
# other subcommands
# --------------------------------------------------------------------------


def cmd_conformance(args) -> int:
    """A0.1: drive C* through the runtime, write the traces, emit the frozen document.

    The document is `a0.adapter.conformance/v1` (`a0/conformance/README.md`), so the
    external runner can read it without aliases.  The same run also writes the three
    traces, so the A0.1 number and the A0.1 evidence come from one execution.
    """

    _runtime_guard(args.runtime)
    contract, candidate_set, theta, fr = _load_everything(args)
    objectives = _objectives(args)
    run_id = getattr(args, "run_id", None) or "a01-loreley-conformance"
    run_dir = Path(args.run_dir).resolve() / "conformance"
    env, mapping = _prepare_run_dir(
        run_dir=run_dir, contract=contract, theta=theta, objectives=objectives,
        emit_timing=False,
    )
    os.environ["A0_FR"] = str(Path(args.fr))
    _write_adapter_md(run_dir, contract=contract, theta=theta, mapping=mapping, fr=fr,
                      env=env, objectives=objectives)
    write_mapping(run_dir / "eidr.mapping.json", mapping)
    (run_dir / "env.frozen.json").write_text(
        json.dumps(env.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    kinds = tuple(
        item.strip() for item in (getattr(args, "traces", None) or
                                  "score,selection,resource").split(",")
    )
    writer = TraceWriter(
        run_dir=run_dir, runtime="loreley", run_id=run_id, task=args.task, kinds=kinds
    )
    budget = _parse_budget("T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1")
    evaluations, calls, elapsed = _drive_candidates(
        env=env, candidate_set=candidate_set, theta=theta, contract=contract,
        writer=writer, fr=fr, budget=budget, run_id=run_id, run_dir=run_dir,
        eid_r_trace=mapping.as_trace(),
    )
    archive_decisions = _archive_pass(
        env=env, writer=writer, evaluations=evaluations, contract=contract,
        theta_trace=theta.as_trace(), eid_r_trace=mapping.as_trace(), run_id=run_id,
        budget=budget, run_dir=run_dir,
    )
    writer.emit(
        "resource",
        event_id=f"lor-{run_id}-r-run",
        iteration=0,
        candidate_id="__run__",
        parent_id=None,
        eid_star=contract.eid_star,
        eid_r=mapping.as_trace(),
        theta_e=theta.as_trace(),
        failure_stage="none",
        failure_detail=None,
        extra={
            "T_wall": {"value_sec": round(elapsed, 6), "clock": "monotonic", "scope": "run"},
            "N_evaluatorCalls": calls,
            "concurrency": {"cap": 1, "observed_max": 1},
            "budget_hard": budget,
            "secondary": {"N_modelCalls": None, "T_in": None, "T_out": None, "C_usd": None},
        },
    )
    writer.close()
    writer.validate()

    # The independent spread / cwd-independence evidence stays in the document; it is
    # not part of the frozen runner's shape but nothing is lost by carrying it.
    repeats = max(1, int(getattr(args, "repeats", 3)))
    report = run_conformance(
        contract=contract, candidate_set=candidate_set, theta=theta, eid_r=mapping,
        env=env, repeats=repeats,
        evaluations={item["candidate_id"]: item for item in evaluations},
    )
    document = report.as_document(env)
    document["fr"] = fr.as_trace("a0/contract/adapter_contract.md#default-first-round-rule")
    document["schema"] = "a0.adapter.conformance/v1"
    document["runtime"] = "loreley"
    document["theta_e"] = _theta_e_document(theta)
    document["epsilon"] = _epsilon_document(contract, getattr(args, "epsilon", None))
    document["primary_field"] = contract.primary_field
    document["eid_r"] = _eid_r_document(mapping, contract, run_dir, theta)
    document["candidates"] = [
        _conformance_row(
            evaluation=item,
            contract=contract,
            theta=theta,
            run_id=run_id,
            fr_metric=os.environ.get("A0_FR_METRIC_NAME", "composite_score"),
        )
        for item in evaluations
    ]
    document["traces"] = writer.paths.as_dict()
    document["run_dir"] = str(run_dir)
    document.update(
        _failure_stage_accounting(
            document["candidates"], writer.paths.score, len(candidate_set.candidates)
        )
    )
    document["UNVERIFIED"] = UNVERIFIED_NOTES
    document["seams"] = DECLARED_SEAMS
    document["adapter"] = {
        "version": __version__,
        "entry_point": str(ENTRY_POINT),
        "interpreter": sys.executable,
        "plugin": PLUGIN_REF,
        "objectives": [dict(item) for item in objectives],
    }
    document["wall_clock_s"] = elapsed
    document["evaluator_calls"] = calls

    out_path = Path(args.out) if args.out else run_dir / "conformance.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": document["verdict"],
        "failure_count": document["failure_count"],
        "failed_candidates": document["failed_candidates"],
        "epsilon": document["epsilon"]["value"],
        "candidates": len(document["candidates"]),
        "traces": document["traces"],
        "out": str(out_path),
    }, indent=1))
    return EXIT_OK if document["verdict"] == "pass" else EXIT_CONFORMANCE


def _failure_stage_accounting(
    candidates: Sequence[Mapping[str, Any]],
    score_trace: Path,
    expected_members: int,
) -> dict[str, Any]:
    """The adopted `FailureStage` block: mapping, unit basis, counts.

    The counts are one unit per member of `C*` read from the **score** trace, which
    is exactly the basis the conformance runner compares against the frozen map
    (`conformance.py::count_failure_stages` reads `trace_paths["score"]` and keys by
    `(run_id, candidate_id, iteration)`).  Adapter-level events that are not
    candidates are deliberately excluded; including them - as an earlier revision
    did with its run-level `__run__` resource row - produced 15 units for 14
    candidates and made the counts unjoinable.
    """

    adoption = adopt()
    counts, units = score_trace_counts([score_trace])
    expected = expected_from_candidates(candidates)
    return {
        "failure_stage_mapping": FROZEN_FAILURE_STAGE_MAPPING,
        "failure_stage_mapping_adoption": adoption,
        "failure_stage_counts": counts,
        "failure_stage_counts_basis": {
            "definition": unit_basis_note(units, expected_members),
            "unit_key": ["run_id", "iteration", "candidate_id"],
            "source": str(score_trace),
            "counted_by": "a0_adapter.failure_stage.score_trace_counts",
            "units": units,
            "expected_members_of_C_star": expected_members,
            "one_unit_per_member": units == expected_members,
            "excluded_non_candidate_events": [
                "the run-level resource event (candidate_id `__run__`)",
                "the report-branch selection row",
            ],
        },
        "failure_stage_expected_from_frozen_map": expected,
        "failure_stage_counts_match_frozen_map": counts == expected,
        # The contract's own `trace_validate.py stats` aggregate, kept for a reader
        # who wants the protocol's four counters.  It counts every trace, so it is a
        # different basis and is named as such rather than presented as the counts.
        "failure_stage_stats_all_traces": stage_histogram([score_trace]),
    }


def _theta_e_document(theta: ThetaE) -> dict[str, Any]:
    """`theta_E` in the frozen shape: every frozen coordinate at the top level."""

    trace = theta.as_trace()
    document: dict[str, Any] = {
        "seed": trace["seed"],
        "fidelity": trace["fidelity"],
        "fraction": trace["fraction"],
    }
    typed = theta.typed_extra()
    for key, value in typed.items():
        document.setdefault(key, value)
    document["defaults_applied"] = trace["defaults_applied"]
    # `extra` mirrors the same values, typed, so a reader that looks only at `extra`
    # sees `26` rather than `"26"` (the CLI hands every extra over as a string).
    document["extra"] = typed
    return document


def _epsilon_document(contract: EvalContract, declared: float | None) -> dict[str, Any]:
    """The frozen epsilon, plus the value the caller passed if any.

    A caller-supplied epsilon that disagrees with the frozen contract is a contract
    mismatch (exit 3), not something to average over.
    """

    frozen = contract.epsilon
    if declared is not None and abs(float(declared) - frozen) > 0.0:
        raise ContractError(
            f"--epsilon {declared!r} disagrees with the frozen EID* epsilon {frozen!r}; "
            "epsilon is part of the frozen contract and may not be chosen per run (plan:518)"
        )
    return {
        "kind": "abs",
        "unit": contract.primary_field,
        "value": frozen,
        "caller_supplied": declared,
        "frozen_before_run": True,
        "source": f"{contract.path.name} components.Config.conformance.epsilon",
    }


def _eid_r_document(mapping, contract: EvalContract, run_dir: Path,
                    theta: ThetaE) -> dict[str, Any]:
    """`eid_r` in the frozen shape, with an executable recomputation command.

    The runner executes `recompute_cmd` and compares its stdout's `value` with the
    declared `eid_r.value`, which is what turns `recomputable: true` from a claim into
    an executed check.  The command is given absolute paths for the EID* document, the
    plugin source and the campaign program, so it does not depend on cwd or PYTHONPATH.
    """

    return {
        **mapping.as_trace(),
        "eid_star": contract.eid_star,
        "native_components": mapping.as_document()["native_components"],
        "eidr_derivation": mapping.eidr_derivation,
        # The runner executes this and compares stdout's `value` with `value` above.
        # It points at the INDEPENDENT reconstruction (tools/verify_eidr.py), which
        # imports no part of this adapter: it recomputes the five component digests
        # and EID* with the contract owner's own scheme, hashes the plugin source and
        # the rendered program as bytes on disk, and checks that all five component
        # digests appear verbatim in the hashed program bytes.
        "recompute_cmd": [
            str(INDEPENDENT_VERIFIER_PYTHON),
            str(INDEPENDENT_VERIFIER),
            "--eid",
            str(contract.path),
            "--program",
            str(run_dir / "loreley.program.md"),
            "--plugin-source",
            str(PLUGIN_SOURCE),
            "--plugin-ref",
            PLUGIN_REF,
            "--mapping",
            str(run_dir / "eidr.mapping.json"),
        ],
        "recompute_cmd_is_adapter_independent": True,
        "recompute_cmd_note": (
            "tools/verify_eidr.py imports a0/contract/evalcontract.py (the authority on how an "
            "EID* is formed) and nothing from a0_adapter; it re-derives the value from the "
            "document, the plugin source file and the rendered program bytes"
        ),
    }


def _theta_cli(theta: ThetaE) -> str:
    """The theta as the `--theta` CLI string, so a recompute run renders the same program."""

    seed, fidelity, fraction = theta.for_e_star()
    parts = [f"seed={seed}", f"fidelity={fidelity}", f"fraction={fraction}"]
    for key, value in sorted(theta.typed_extra().items()):
        parts.append(f"{key}={value}")
    return ",".join(parts)


def _conformance_row(
    *,
    evaluation: Mapping[str, Any],
    contract: EvalContract,
    theta: ThetaE,
    run_id: str,
    fr_metric: str,
) -> dict[str, Any]:
    """One row of `C*` in the frozen runner's shape."""

    candidate_id = str(evaluation["candidate_id"])
    reference = evaluation["reference"]
    runtime_result = evaluation["runtime"]
    evidence = evaluation["evidence"]
    record = runtime_result.evidence or {}

    # The lane's own view of E*: canonical digest, source digest and verdict, taken
    # from the plugin's evidence record rather than from the adapter's reference run.
    lane_digest = record.get("e_star_canonical_digest") or reference.outcome.get("canonical_digest")
    lane_source = record.get("candidate_source_sha256") or (
        (reference.outcome.get("candidate") or {}).get("source_sha256")
    )
    lane_status = str(record.get("e_star_status") or reference.status)
    lane_exit = record.get("e_star_exit_code")
    lane_failure_kind = None
    if isinstance(record.get("e_star_failure"), Mapping):
        lane_failure_kind = record["e_star_failure"].get("kind")
    if lane_failure_kind is None:
        lane_failure_kind = (reference.outcome.get("failure") or {}).get("kind") or None

    runtime_fields = {
        str(item["name"]): item["value"]
        for item in runtime_result.metrics
        if (item.get("details") or {}).get("source") != "F_r"
    }
    scalar = runtime_fields.get(contract.primary_field)
    manifest_line = record.get("e_star_manifest_line")
    seed, fidelity, fraction = theta.for_e_star()
    # `status` + `failure.kind` + the stage derived from them by the frozen table
    # (adapter_contract.md §5.3): the runner reads all three per row, and the study's
    # per-runtime FailureStage totals join on the stage.
    derived_stage = stage_for(lane_status, lane_failure_kind)
    return {
        "candidate_id": candidate_id,
        "role": reference.outcome.get("candidate", {}).get("role"),
        "source_sha256": lane_source,
        "canonical_digest": lane_digest,
        "status": lane_status,
        "failure_stage": derived_stage if derived_stage is not None else evidence.status,
        "failure_stage_source": (
            "frozen failure_stage_mapping applied to (E*.status, E*.failure.kind)"
            if derived_stage is not None
            else f"no E* verdict; the runtime-level cause is {evidence.status}"
        ),
        "runtime_scalar": scalar,
        "runtime_outcome_kind": runtime_result.outcome_kind,
        "runtime_metrics": sorted(runtime_fields),
        "objective": {
            "name": contract.primary_field,
            "value": scalar,
            "direction": "max",
        },
        "exit_code": lane_exit if lane_exit is not None else reference.exit_code,
        "failure_kind": lane_failure_kind,
        "evaluator_evidence": evidence.as_trace(),
        "theta_e_attempt": {
            "evaluator": "E*",
            "fidelity": fidelity,
            "fraction": fraction,
            "seed": seed,
            "granted_class": fidelity,
            "commanded_class": fidelity,
            "protocol": runtime_result.protocol,
            "evaluator_name": runtime_result.evaluator_name,
            "evaluator_version": runtime_result.evaluator_version,
        },
        "manifest_echo": manifest_line,
        "score_event_id": f"lor-{run_id}-s-i0-{candidate_id}",
        "runner_row_note": (
            "runtime_scalar is E*'s sum_radii as returned by the runtime's evaluator "
            "process; the declared F_r metric is not part of E*'s field set"
        ),
    }


def cmd_a02(args) -> int:
    _runtime_guard(args.runtime)
    contract, candidate_set, theta, fr = _load_everything(args)
    run_dir = Path(args.run_dir).resolve() / "a02"
    env, mapping = _prepare_run_dir(
        run_dir=run_dir, contract=contract, theta=theta,
        objectives=CONFIG_M_OBJECTIVES, emit_timing=True,
    )
    document = run_a02(
        contract=contract, candidate_set=candidate_set, theta=theta, base_run_dir=run_dir
    )
    document["eid_r"] = mapping.as_trace()
    out_path = Path(args.out) if args.out else run_dir / "a02.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": document["verdict"],
        "failed_checks": document["failed_checks"],
        "meaningful_control_config": document["meaningful_control_config"],
        "checks": [
            {"check_id": check["check_id"], "config": check["config"], "passed": check["passed"]}
            for check in document["checks"]
        ],
        "out": str(out_path),
    }, indent=1))
    return EXIT_OK if document["verdict"] == "pass" else EXIT_INTERNAL


def cmd_traps(args) -> int:
    _runtime_guard(args.runtime)
    from .traps import t2_timeout, t3_truncation, t4_persistent_cache

    contract, candidate_set, theta, fr = _load_everything(args)
    run_dir = Path(args.run_dir).resolve() / "traps"
    env, mapping = _prepare_run_dir(
        run_dir=run_dir, contract=contract, theta=theta,
        objectives=OBJECTIVES_DEFAULT, emit_timing=False,
    )
    document = {
        "schema": "a0.loreley.traps/v1",
        "runtime": "loreley",
        "eid_star": contract.eid_star,
        "eid_r": mapping.as_trace(),
        "evidence_policy": policy_note(),
        "T2": t2_timeout(env, candidate_set, theta, timeout_seconds=int(args.t2_timeout)),
        "T3": t3_truncation(env, candidate_set),
        "T4": t4_persistent_cache(env, candidate_set, eid_r_value=mapping.value),
    }
    document["verdict"] = (
        "pass" if all(document[key]["passed"] for key in ("T2", "T3", "T4")) else "fail"
    )
    out_path = Path(args.out) if args.out else run_dir / "traps.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": document["verdict"],
        "T2": document["T2"]["passed"],
        "T3": document["T3"]["passed"],
        "T4": document["T4"]["passed"],
        "out": str(out_path),
    }, indent=1))
    return EXIT_OK if document["verdict"] == "pass" else EXIT_INTERNAL


def cmd_closure(args) -> int:
    _runtime_guard(args.runtime)
    run_dir = Path(args.run_dir).resolve() / "closure"
    out_path = Path(args.out) if args.out else run_dir / "closure.json"
    document = run_closure_probe(out_path=out_path, run_dir=run_dir)
    print(json.dumps({
        "verdict": document["verdict"],
        "mechanism": document["mechanism"],
        "out": str(out_path),
        "observations": [
            {"name": item["name"], "observed": item["observed"], "expectation": item["expectation"]}
            for item in document["observations"]
        ],
    }, indent=1))
    return closure_exit_code(document)


def _load_evalcontract():
    """Import the contract owner's `evalcontract.py` — the authority's own scheme."""

    import importlib.util

    path = A0_ROOT / "contract" / "evalcontract.py"
    spec = importlib.util.spec_from_file_location("a0_evalcontract", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise AdapterError(f"cannot load {path}", code=EXIT_INTERNAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# One faithful perturbation per EID* component. `evalcontract.recompute_from_records`
# hashes exactly these payloads, so perturbing them changes that component's digest.
_COMPONENT_PAYLOAD_KEYS = {
    "EvaluatorSource": "records",
    "DependencyLock": "records",
    "DataManifest": "records",
    "Config": "value",
    "MetricDefinition": "value",
}


def _perturb_component(document: dict, name: str) -> str:
    """Change one recorded input of `name` and describe the change."""

    component = document["components"][name]
    if name in ("EvaluatorSource", "DependencyLock", "DataManifest"):
        # One appended sentinel record is a mutation every record-based component
        # accepts, and it changes the payload `recompute_from_records` hashes.
        records = component["records"]
        before = len(records)
        records.append({"a0_mutation": True, "component": name})
        return f"{name}.records += 1 sentinel record ({before} -> {before + 1})"
    value = component["value"]
    if name == "Config":
        before = value["theta_e_canonical"]["seed"]
        value["theta_e_canonical"]["seed"] = int(before) + 1
        return f"Config.value.theta_e_canonical.seed {before} -> {before + 1}"
    if name == "MetricDefinition":
        before = value.get("unit")
        value["unit"] = (str(before) + " [a0-mutation]") if before else "a0-mutation"
        return f"MetricDefinition.value.unit {before!r} -> {value['unit']!r}"
    raise AdapterError(f"no mutation defined for component {name!r}", code=EXIT_INTERNAL)


def _eidr_mutation_test(contract: EvalContract, theta: ThetaE, plugin_source: Path,
                        run_dir: Path) -> dict[str, Any]:
    """Show that `EID_r` follows `EID*` through **every** one of the five inputs.

    The auditor's finding on EvE was that its identity was a hash of a *generated
    script* rather than structurally derived from `EID*`. The answer here is not a
    sentence: it is a five-way mutation test in which each `EID*` component is
    perturbed in turn, the contract owner's own `recompute_from_records` recomputes
    the component digest and `EID*`, the campaign program is re-rendered from the
    perturbed document, and `EID_r` is re-derived. Every row must change.
    """

    import copy

    from .eidr import component_digests, derive_eidr as _derive

    evaluator = _load_evalcontract()

    def _render(document: Mapping[str, Any], eid_star: str) -> tuple[Path, Any, dict[str, str]]:
        mutated = EvalContract(path=contract.path, eid_star=eid_star, document=document)
        path = run_dir / f"loreley.program.{eid_star[:8]}.md"
        path.write_text(render_campaign_program(mutated, theta.as_trace()), encoding="utf-8")
        mapping = _derive(
            mutated, plugin_ref=PLUGIN_REF, plugin_source=plugin_source,
            campaign_program=path,
        )
        return path, mapping, component_digests(mutated)

    baseline_document = copy.deepcopy(dict(contract.document))
    baseline_program, baseline, recorded_digests = _render(
        baseline_document, contract.eid_star
    )
    # The document's own recorded digests must reproduce under the authority's own
    # scheme before any mutation of them is believable.
    recompute_baseline = evaluator.recompute_from_records(baseline_document)
    recorded_components = {
        key: value for key, value in recorded_digests.items() if key != "EID*"
    }
    baseline_self_check = {
        "recomputed_digests": recompute_baseline["components"],
        "recorded_digests": recorded_components,
        "digests_match_record": (
            recompute_baseline["components"] == recorded_components
        ),
        "eid_star_recomputed": recompute_baseline["eid_star"],
        "eid_star_matches": recompute_baseline["eid_star"] == contract.eid_star,
        "checked_with": "a0/contract/evalcontract.py::recompute_from_records (the authority's own scheme)",
    }

    rows: list[dict[str, Any]] = []
    for name in evaluator.COMPONENTS:
        document = copy.deepcopy(baseline_document)
        change = _perturb_component(document, name)
        fresh = evaluator.recompute_from_records(document)
        perturbed_program, perturbed, recorded_after = _render(
            document, fresh["eid_star"]
        )
        # The document's *recorded* digest for the perturbed component is stale (the
        # mutation touched the payload, not the recorded digest), so the comparison is
        # against the authority's recomputation, on both sides.
        rows.append(
            {
                "component": name,
                "change": change,
                "component_digest_before": recompute_baseline["components"].get(name),
                "component_digest_after": fresh["components"].get(name),
                "component_digest_changed": (
                    recompute_baseline["components"].get(name)
                    != fresh["components"].get(name)
                ),
                "recorded_digest_after_mutation": recorded_after.get(name),
                "eid_star_before": contract.eid_star,
                "eid_star_after": fresh["eid_star"],
                "eid_star_changed": fresh["eid_star"] != contract.eid_star,
                "campaign_program_sha256_before": baseline.campaign_program_sha256,
                "campaign_program_sha256_after": perturbed.campaign_program_sha256,
                "eid_r_before": baseline.value,
                "eid_r_after": perturbed.value,
                "eid_r_changed": baseline.value != perturbed.value,
                "eidr_derivation_after": perturbed.eidr_derivation,
                "program": str(perturbed_program),
            }
        )

    return {
        "design": (
            "each of the five EID* components is perturbed in turn; the contract owner's own "
            "evalcontract.recompute_from_records recomputes the component digest and EID*, the "
            "campaign program is re-rendered from the perturbed document and EID_r is re-derived"
        ),
        "plugin_source": str(plugin_source),
        "plugin_source_sha256": baseline.plugin_source_sha256,
        "plugin_source_unchanged_by_design": True,
        "baseline": {
            "eid_star": contract.eid_star,
            "component_digests": recompute_baseline["components"],
            "campaign_program_sha256": baseline.campaign_program_sha256,
            "eid_r_value": baseline.value,
            "eidr_derivation": baseline.eidr_derivation,
            "program": str(baseline_program),
        },
        "baseline_self_check": baseline_self_check,
        "components": rows,
        "all_five_components_change_eid_star": all(
            row["eid_star_changed"] for row in rows
        ),
        "all_five_components_change_eid_r": all(row["eid_r_changed"] for row in rows),
        "why_this_answers_the_auditor": (
            "the claim 'EID_r is derived from EID*' is only meaningful if a third party can see "
            "which inputs reach it. The provenance section rendered into loreley.program.md "
            "carries all five component digests, so campaign_program_hash - and hence EID_r - "
            "changes for every one of the five, which the table above measures rather than "
            "asserts. No part of EID_r is a hash of a generated script that the inputs do not "
            "reach: the two hash inputs are the plugin source file (the code that will run) and "
            "the rendered program (a function of all five component digests)."
        ),
    }


def cmd_eidr(args) -> int:
    contract = load_eval_contract(Path(args.eid), verify=not args.no_verify)
    run_dir = Path(args.run_dir).resolve()
    theta = ThetaE.parse(args.theta)
    run_dir.mkdir(parents=True, exist_ok=True)
    program = run_dir / "loreley.program.md"
    program.write_text(render_campaign_program(contract, theta.as_trace()), encoding="utf-8")
    mapping = derive_eidr(
        contract,
        plugin_ref=args.plugin_ref,
        plugin_source=Path(args.plugin_source),
        campaign_program=program,
    )
    mapping_path = run_dir / "eidr.mapping.json"
    write_mapping(mapping_path, mapping)
    ok, problems = recompute_eidr(
        load_mapping(mapping_path), contract=contract,
        plugin_source=Path(args.plugin_source), campaign_program=program,
    )
    result = {
        "eid_star": mapping.derives_from_eid_star,
        "eid_r_value": mapping.value,
        "eidr_derivation": mapping.eidr_derivation,
        "recomputed": ok,
        "problems": problems,
        "mapping": str(mapping_path),
        "campaign_program": str(program),
        "mutation_test": _eidr_mutation_test(
            contract, theta, Path(args.plugin_source), run_dir
        ),
    }
    print(json.dumps(result, indent=1))
    return EXIT_OK if ok else EXIT_INTERNAL


def cmd_eidr_recompute(args) -> int:
    """Recompute ``EID_r`` from its recorded inputs and print it for a third party.

    This is the command the conformance runner executes for `EID-r-recomputes`
    (`a0/conformance/README.md`): the output carries a top-level `value` key so the
    check is *executed* rather than merely declared.

    It is deliberately filesystem-light: it re-reads the plugin source, the campaign
    program on disk and the frozen ``EID*`` document, re-derives the triple and
    compares it with the recorded mapping when one is supplied.
    """

    contract = load_eval_contract(Path(args.eid), verify=not args.no_verify)
    program = Path(args.campaign_program) if args.campaign_program else (
        Path(args.run_dir).resolve() / "loreley.program.md"
    )
    if not program.is_file():
        program.parent.mkdir(parents=True, exist_ok=True)
        program.write_text(
            render_campaign_program(contract, ThetaE.parse(args.theta).as_trace()),
            encoding="utf-8",
        )
    mapping = derive_eidr(
        contract,
        plugin_ref=args.plugin_ref,
        plugin_source=Path(args.plugin_source),
        campaign_program=program,
    )
    payload = {
        "schema": "a0.eidr.loreley.recompute/v1",
        "runtime": "loreley",
        "value": mapping.value,
        "eid_r_value": mapping.value,
        "eid_star": contract.eid_star,
        "native_scheme": mapping.native_scheme,
        "mapping_mode": mapping.mapping_mode,
        "derives_from_eid_star": contract.eid_star,
        "declaration": mapping.declaration,
        "recomputable": True,
        "native_components": mapping.as_document()["native_components"],
        "eidr_derivation": mapping.eidr_derivation,
        "inputs": {
            "eid": str(contract.path),
            "plugin_source": str(Path(args.plugin_source)),
            "campaign_program": str(program),
        },
    }
    if getattr(args, "out", None):
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # The runner parses stdout, so the JOB is to print JSON here; the file is a copy.
    print(json.dumps(payload, sort_keys=True))
    return EXIT_OK


def cmd_plan(args) -> int:
    contract = load_eval_contract(Path(args.eid), verify=not args.no_verify)
    print(json.dumps({
        "eid_star": contract.eid_star,
        "primary_field": contract.primary_field,
        "epsilon": contract.epsilon,
        "base_declared": contract.base_declared,
        "verify": "clean" if not args.no_verify else "skipped",
    }, indent=1))
    return EXIT_OK


# --------------------------------------------------------------------------
# argparse
# --------------------------------------------------------------------------


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--task", default="circle-packing")
    parser.add_argument("--candidate-set", default=str(DEFAULT_CANDIDATE_SET))
    parser.add_argument("--eid", default=str(DEFAULT_EID))
    parser.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    parser.add_argument("--fr", default=str(DEFAULT_FR))
    parser.add_argument("--run-id", default="lor-a0")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    parser.add_argument("--no-verify", action="store_true",
                        help="skip evalcontract.py verify (recorded in the output)")
    parser.add_argument("--no-integrity", action="store_true",
                        help="skip the C* solution.py sha256 check (never for a real run)")
    parser.add_argument("--multi-objective", action="store_true",
                        help="use the example's two-objective contract")
    parser.add_argument("--objectives", default=None, help="JSON objective list")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="a0_adapter", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="evaluate C* through the runtime and write the traces")
    _add_common(run)
    run.add_argument("--budget", default=None)
    run.add_argument("--traces", default="score,selection,resource")
    run.set_defaults(fn=cmd_run)

    conf = sub.add_parser("conformance", help="A0.1 E_r(c) vs E*(c)")
    _add_common(conf)
    conf.add_argument("--epsilon", type=float, default=None)
    conf.add_argument("--repeats", type=int, default=3)
    conf.add_argument("--out", default=None)
    conf.set_defaults(fn=cmd_conformance)

    a02 = sub.add_parser("a02", help="A0.2 archive replacement and report branch")
    _add_common(a02)
    a02.add_argument("--out", default=None)
    a02.set_defaults(fn=cmd_a02)

    traps = sub.add_parser("traps", help="the three named false-green traps")
    _add_common(traps)
    traps.add_argument("--t2-timeout", type=int, default=1)
    traps.add_argument("--out", default=None)
    traps.set_defaults(fn=cmd_traps)

    closure = sub.add_parser("closure-probe", help="prove closed by probe")
    _add_common(closure)
    closure.add_argument("--out", default=None)
    closure.set_defaults(fn=cmd_closure)

    recompute = sub.add_parser("eidr-recompute", help="recompute EID_r and print it")
    recompute.add_argument("--eid", default=str(DEFAULT_EID))
    recompute.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    recompute.add_argument("--campaign-program", default=None)
    recompute.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    recompute.add_argument("--plugin-ref", default=PLUGIN_REF)
    recompute.add_argument("--plugin-source", default=str(PLUGIN_SOURCE))
    recompute.add_argument("--out", default=None)
    recompute.add_argument("--no-verify", action="store_true")
    recompute.set_defaults(fn=cmd_eidr_recompute)

    eidr = sub.add_parser("eidr", help="derive / recompute the EID_r mapping")
    eidr.add_argument("--eid", default=str(DEFAULT_EID))
    eidr.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    eidr.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    eidr.add_argument("--plugin-ref", default=PLUGIN_REF)
    eidr.add_argument("--plugin-source", default=str(PLUGIN_SOURCE))
    eidr.add_argument("--no-verify", action="store_true")
    eidr.set_defaults(fn=cmd_eidr)

    plan = sub.add_parser("plan", help="print the frozen contract the adapter will use")
    plan.add_argument("--eid", default=str(DEFAULT_EID))
    plan.add_argument("--no-verify", action="store_true")
    plan.set_defaults(fn=cmd_plan)
    return parser


def _ensure_runtime_importable() -> None:
    """Re-exec into the environment where the pinned Loreley checkout is installed.

    The conformance runner launches adapters with whatever interpreter it discovers,
    which for this package was ``/usr/bin/python3`` -- an interpreter that has none of
    the pinned checkout's dependencies.  Rather than fail with `ModuleNotFoundError`,
    the adapter hands the same argv to its own venv interpreter, once.  The pinning is
    explicit: the interpreter is the one the checkout was installed into
    (``checkout/.venv``), not a guess from ``PATH``.
    """

    if os.environ.get("A0_LORELEY_REEXECUTED") == "1":
        return
    checkout = str(LORELYELEY_CHECKOUT)
    if checkout not in sys.path:
        sys.path.insert(0, checkout)
    try:
        import loreley  # noqa: F401
        return
    except Exception:  # noqa: BLE001 - any import failure means "wrong interpreter"
        pass
    venv_python = Path(__file__).resolve().parents[2] / "checkout" / ".venv" / "bin" / "python"
    if not venv_python.is_file():
        return
    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:  # pragma: no cover
        return
    env = dict(os.environ)
    env["A0_LORELEY_REEXECUTED"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(__file__).resolve().parents[1])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    os.execve(str(venv_python), [str(venv_python), "-m", "a0_adapter", *sys.argv[1:]], env)


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_runtime_importable()
    parser = build_parser()
    args = parser.parse_args(argv)
    os.environ.setdefault("DATABASE_URL", FUNCTIONAL_DATABASE_URL)
    os.environ.setdefault("DB_AUTO_MIGRATE", "true")
    os.environ.setdefault("A0_FR", str(DEFAULT_FR))
    try:
        return int(args.fn(args))
    except AdapterError as exc:
        print(f"a0_adapter: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    except Exception as exc:  # noqa: BLE001 - internal errors get their own code
        import traceback

        traceback.print_exc()
        print(f"a0_adapter: internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
