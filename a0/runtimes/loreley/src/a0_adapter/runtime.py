"""Real Loreley wiring: settings, the evaluator process, and the archive.

Nothing in this module re-implements runtime behaviour.  It constructs the
pinned checkout's own objects and calls their own methods:

* ``loreley.config.Settings`` (with the frozen environment applied),
* ``loreley.core.worker.evaluator.Evaluator`` - the real plugin spawn and
  timeout envelope,
* ``loreley.core.map_elites.pareto_archive.ParetoGridArchive`` - the real QD
  archive,
* ``loreley.core.map_elites.objectives.ObjectiveContract`` - the real
  metrics -> objective-vector resolution.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import (
    A0_ROOT,
    AdapterError,
    EXIT_INTERNAL,
    Candidate,
    ThetaE,
)

LORELYELEY_CHECKOUT = Path(__file__).resolve().parents[2] / "checkout"
PLUGIN_SOURCE = Path(__file__).resolve().parents[1] / "loreley_a0_plugin.py"
PLUGIN_REF = "loreley_a0_plugin:plugin"

E_STAR_DIR = A0_ROOT / "tasks" / "circle-packing"
E_STAR_PY = E_STAR_DIR / ".venv" / "bin" / "python"
E_STAR_SCRIPT = E_STAR_DIR / "e_star.py"

DEFAULT_ISLAND = "circle_packing_alpha"
# The runtime's own default objective contract is a single `composite_score`
# (loreley/config.py:916-919). The adapter's F_r supplies that scalar, so the
# default run and the default objective agree by construction.
OBJECTIVES_DEFAULT = ({"name": "composite_score", "direction": "max"},)
# The checkout's own circle-packing example objective list
# (examples/evol_circle_packing.py:80-84): genuinely multi-objective.
OBJECTIVES_MULTI = (
    {"name": "sum_radii", "direction": "max"},
    {"name": "runtime_p50_ms", "direction": "min"},
)


@dataclass(slots=True)
class FrozenEnvironment:
    """The environment the adapter pins, recorded verbatim with every run."""

    run_dir: Path
    theta: ThetaE
    objectives: Sequence[Mapping[str, str]] = field(default_factory=lambda: OBJECTIVES_DEFAULT)
    islands: Sequence[str] = (DEFAULT_ISLAND,)
    pareto_front_max_size: int = 8
    pareto_epsilon: float = 1.0e-9
    admission_policy: str = "pareto"
    experiment_root_commit: str = "b91c0906c9f676eb661990d881144909d99f2d72"
    campaign_program_hash: str = ""
    experiment_id: str = "a0-loreley-loreley"
    plugin_ref: str = PLUGIN_REF
    worker_evaluator_timeout_seconds: int = 900
    worker_evaluator_max_metrics: int = 64
    emit_timing: bool = False

    def as_dict(self) -> dict[str, Any]:
        seed, fidelity, fraction = self.theta.for_e_star()
        return {
            "WORKER_EVALUATOR_PLUGIN": self.plugin_ref,
            "WORKER_EVALUATOR_PYTHON_PATHS": [str(PLUGIN_SOURCE.parent)],
            "WORKER_EVALUATOR_PLUGIN_SOURCE": str(PLUGIN_SOURCE),
            "WORKER_EVALUATOR_TIMEOUT_SECONDS": self.worker_evaluator_timeout_seconds,
            "WORKER_EVALUATOR_MAX_METRICS": self.worker_evaluator_max_metrics,
            "MAPELITES_OBJECTIVES": [dict(item) for item in self.objectives],
            "MAPELITES_ISLANDS": list(self.islands),
            "MAPELITES_PARETO_FRONT_MAX_SIZE": self.pareto_front_max_size,
            "MAPELITES_PARETO_EPSILON": self.pareto_epsilon,
            "MAPELITES_ADMISSION_POLICY": self.admission_policy,
            "MAPELITES_EXPERIMENT_ROOT_COMMIT": self.experiment_root_commit,
            "A0_CAMPAIGN_PROGRAM_HASH": self.campaign_program_hash,
            "APP_NAME": "loreley-a0",
            "APP_ENV": "development",
            "EXPERIMENT_ID": self.experiment_id,
            "A0_E_STAR_PY": str(E_STAR_PY),
            "A0_E_STAR_SCRIPT": str(E_STAR_SCRIPT),
            "A0_E_STAR_SEED": seed,
            "A0_E_STAR_FIDELITY": fidelity,
            "A0_E_STAR_FRACTION": fraction,
            "A0_E_STAR_STATE_DIR": str(self.run_dir / "e-star-state"),
            "A0_E_STAR_OUT_DIR": str(self.run_dir / "e-star-out"),
            **{
                name: value
                for name, value in (
                    ("A0_E_STAR_N", self.theta.extra.get("n")),
                    ("A0_E_STAR_RUNS", self.theta.extra.get("runs")),
                    ("A0_E_STAR_RUNTIME_BUDGET_MS", self.theta.extra.get("runtime_budget_ms")),
                    ("A0_E_STAR_TIMEOUT_S", self.theta.extra.get("timeout_s")),
                )
                if value is not None
            },
            "A0_EVIDENCE_DIR": str(self.run_dir / "evaluator-evidence"),
            "A0_LORELEY_EMIT_TIMING": "1" if self.emit_timing else "0",
            "DATABASE_URL": os.environ.get(
                "A0_DATABASE_URL", "postgresql+psycopg://loreley:loreley@127.0.0.1:5432/loreley"
            ),
            "TASKS_REDIS_URL": os.environ.get(
                "A0_TASKS_REDIS_URL", "redis://127.0.0.1:6379/0"
            ),
        }

    def apply(self) -> dict[str, Any]:
        payload = self.as_dict()
        for key, value in payload.items():
            if isinstance(value, (list, dict)):
                os.environ[key] = json.dumps(value)
            else:
                os.environ[key] = str(value)
        return payload


def ensure_importable() -> None:
    checkout = str(LORELYELEY_CHECKOUT)
    if checkout not in sys.path:
        sys.path.insert(0, checkout)


def build_settings(env: FrozenEnvironment):
    """Construct the pinned checkout's real ``Settings`` from the frozen env."""

    ensure_importable()
    from loreley.config import Settings

    return Settings(
        worker_evaluator_plugin=env.plugin_ref,
        worker_evaluator_python_paths=[str(PLUGIN_SOURCE.parent)],
        worker_evaluator_timeout_seconds=int(env.worker_evaluator_timeout_seconds),
        worker_evaluator_max_metrics=int(env.worker_evaluator_max_metrics),
        mapelites_objectives=tuple(dict(item) for item in env.objectives),
        mapelites_islands=tuple(env.islands),
        mapelites_pareto_front_max_size=int(env.pareto_front_max_size),
        mapelites_pareto_epsilon=float(env.pareto_epsilon),
        mapelites_admission_policy=str(env.admission_policy),
        mapelites_experiment_root_commit=str(env.experiment_root_commit),
    )


def build_evaluator(env: FrozenEnvironment):
    ensure_importable()
    from loreley.core.worker.evaluator import Evaluator

    return Evaluator(build_settings(env))


@dataclass(slots=True)
class RuntimeEvaluation:
    """What the runtime actually did with one candidate."""

    candidate_id: str
    iteration: int
    outcome_kind: str
    protocol: str
    evaluator_name: str | None
    evaluator_version: str | None
    metrics: tuple[dict[str, Any], ...]
    reuse_kind: str
    reused_from_attempt_id: str | None
    measurement_reused: bool | None
    summary: str
    failure_summary: str | None
    detail: str | None
    candidate_failed: bool
    evidence: dict[str, Any] | None
    elapsed_s: float
    raw_result_extra: dict[str, Any]


def _load_evidence(env: FrozenEnvironment, candidate: Candidate) -> dict[str, Any] | None:
    directory = Path(env.as_dict()["A0_EVIDENCE_DIR"])
    key = hashlib.sha256(str(candidate.path).encode("utf-8")).hexdigest()[:16]
    path = directory / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_through_loreley(
    env: FrozenEnvironment,
    candidate: Candidate,
    *,
    iteration: int,
    parent_id: str | None = None,
) -> RuntimeEvaluation:
    """Drive one candidate through the real ``Evaluator.evaluate_outcome`` path.

    The plugin executes inside ``Evaluator._execute_with_timeout``'s spawned
    process (``loreley/core/worker/evaluator.py:1859-1912``), so a plugin timeout
    takes the runtime's own synthetic-failure branch
    (``evaluator.py:1513-1520``).
    """

    ensure_importable()
    from loreley.core.worker.evaluator import EvaluationContext

    evaluator = build_evaluator(env)
    context = EvaluationContext(
        worktree=candidate.path,
        candidate_commit_hash=candidate.solution_sha256[:40],
        job_id=f"a0-{candidate.candidate_id}",
        metadata={
            "campaign_program_hash": _campaign_hash(env),
            "a0_candidate_id": candidate.candidate_id,
            "a0_parent_id": parent_id,
        },
    )
    started = time.monotonic()
    outcome = evaluator.evaluate_outcome(context)
    elapsed = time.monotonic() - started

    result = outcome.result
    metrics: tuple[dict[str, Any], ...] = ()
    raw_extra: dict[str, Any] = {}
    if result is not None:
        metrics = tuple(metric.as_dict() for metric in result.metrics)
        raw_extra = dict(result.extra or {})

    return RuntimeEvaluation(
        candidate_id=candidate.candidate_id,
        iteration=iteration,
        outcome_kind=str(outcome.outcome_kind),
        protocol=str(getattr(outcome, "protocol", "one_shot") or "one_shot"),
        evaluator_name=getattr(outcome, "evaluator_name", None),
        evaluator_version=getattr(outcome, "evaluator_version", None),
        metrics=metrics,
        reuse_kind=str(getattr(outcome, "reuse_kind", "none") or "none"),
        reused_from_attempt_id=getattr(outcome, "reused_from_attempt_id", None),
        measurement_reused=getattr(outcome, "measurement_reused", None),
        summary=str(getattr(outcome, "summary", "") or ""),
        failure_summary=(
            getattr(outcome.failure, "safe_failure_summary", None)
            if getattr(outcome, "failure", None) is not None
            else None
        ),
        detail=(
            getattr(outcome.failure, "details", None)
            if getattr(outcome, "failure", None) is not None
            else None
        ),
        candidate_failed=(str(outcome.outcome_kind) == "candidate_failed"),
        evidence=_load_evidence(env, candidate),
        elapsed_s=elapsed,
        raw_result_extra=raw_extra,
    )


def _campaign_hash(env: FrozenEnvironment) -> str:
    if env.campaign_program_hash:
        return env.campaign_program_hash
    program = env.run_dir / "loreley.program.md"
    if program.is_file():
        return hashlib.sha256(program.read_bytes()).hexdigest()
    return ""


# --------------------------------------------------------------------------
# Reference side of A0.1: E* executed outside every runtime
# --------------------------------------------------------------------------


@dataclass(slots=True)
class ReferenceEvaluation:
    candidate_id: str
    exit_code: int
    outcome: dict[str, Any]
    resources: dict[str, Any] | None
    manifest: dict[str, Any] | None
    command: list[str]
    elapsed_s: float

    @property
    def status(self) -> str:
        return str(self.outcome.get("status"))

    @property
    def scored(self) -> bool:
        return bool(self.outcome.get("scored"))

    @property
    def fields(self) -> dict[str, Any]:
        return dict(self.outcome.get("fields") or {})

    @property
    def primary(self) -> float | None:
        value = self.fields.get("sum_radii")
        return float(value) if isinstance(value, (int, float)) else None


def reference_evaluation(
    candidate: Candidate,
    theta: ThetaE,
    *,
    workdir: Path,
) -> ReferenceEvaluation:
    """Run the frozen ``E*`` directly - the A0.1 reference, outside any runtime."""

    seed, fidelity, fraction = theta.for_e_star()
    workdir.mkdir(parents=True, exist_ok=True)
    out_path = workdir / f"{candidate.candidate_id}.reference.json"
    res_path = workdir / f"{candidate.candidate_id}.reference.resources.json"
    command = [
        str(E_STAR_PY),
        str(E_STAR_SCRIPT),
        "evaluate",
        "--candidate",
        str(candidate.path),
        "--seed",
        str(seed),
        "--fidelity",
        str(fidelity),
        "--fraction",
        str(fraction),
        "--out",
        str(out_path),
        "--state-dir",
        str(workdir / "state"),
        "--emit-resources",
        str(res_path),
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd="/",  # hard constraint 1: the reference must not depend on cwd
        env={
            "PATH": "",
            "HOME": str(workdir),
            "TMPDIR": "/tmp",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    elapsed = time.monotonic() - started
    outcome = json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else {}
    resources = json.loads(res_path.read_text(encoding="utf-8")) if res_path.is_file() else None
    manifest = None
    for line in reversed(completed.stdout.splitlines()):
        line = line.strip()
        if line.startswith("E_STAR_MANIFEST "):
            manifest = json.loads(line[len("E_STAR_MANIFEST ") :])
            break
    if not outcome:
        raise AdapterError(
            f"E* produced no Outcome for candidate {candidate.candidate_id!r} "
            f"(exit={completed.returncode}, stderr={completed.stderr.strip()[:400]!r})",
            code=EXIT_INTERNAL,
        )
    return ReferenceEvaluation(
        candidate_id=candidate.candidate_id,
        exit_code=completed.returncode,
        outcome=outcome,
        resources=resources,
        manifest=manifest,
        command=command,
        elapsed_s=elapsed,
    )


# --------------------------------------------------------------------------
# The real archive and the real objective contract
# --------------------------------------------------------------------------


def build_archive(env: FrozenEnvironment, *, target_dims: int, cells_per_dim: int):
    """Return the real ``ParetoGridArchive`` built the way the manager builds it.

    ``build_archive`` is the manager's own constructor
    (``loreley/core/map_elites/archive_ops.py:41-60``); the feature bounds are its
    own default template ``[0, 1]^target_dims`` (``archive_ops.py:31-33``).
    """

    ensure_importable()
    import numpy as np
    from loreley.core.map_elites.archive_ops import build_archive as real_build_archive
    from loreley.core.map_elites.archive_ops import build_feature_bounds

    settings = build_settings(env)
    lower, upper = build_feature_bounds(target_dims=int(target_dims))
    return real_build_archive(
        settings=settings,
        target_dims=int(target_dims),
        cells_per_dim=int(cells_per_dim),
        lower_template=np.asarray(lower, dtype=np.float64),
        upper_template=np.asarray(upper, dtype=np.float64),
    )


def resolve_objectives(env: FrozenEnvironment, metrics: Sequence[Mapping[str, Any]]):
    """Real ``ObjectiveContract.resolve``: metrics -> (values, dominance scores)."""

    ensure_importable()
    from loreley.core.map_elites.objectives import ObjectiveContract

    settings = build_settings(env)
    contract = ObjectiveContract(settings.mapelites_objectives)
    resolved = contract.resolve(list(metrics))
    return resolved.values, resolved.scores


def make_candidate(
    *,
    commit_hash: str,
    objective_values: Sequence[float],
    objective_scores: Sequence[float],
    measures: Sequence[float],
    timestamp: float,
):
    ensure_importable()
    from loreley.core.map_elites.pareto_archive import ParetoCandidate

    return ParetoCandidate(
        commit_hash=commit_hash,
        objective_values=tuple(float(v) for v in objective_values),
        objective_scores=tuple(float(v) for v in objective_scores),
        measures=tuple(float(m) for m in measures),
        timestamp=float(timestamp),
    )


def workspace_paths(env: FrozenEnvironment) -> dict[str, Path]:
    payload = env.as_dict()
    return {
        "e_star_state": Path(payload["A0_E_STAR_STATE_DIR"]),
        "e_star_out": Path(payload["A0_E_STAR_OUT_DIR"]),
        "evidence": Path(payload["A0_EVIDENCE_DIR"]),
    }


def reset_workspace(env: FrozenEnvironment) -> None:
    """Clear per-run scratch dirs so no stale evaluation can leak into a new run."""

    for path in workspace_paths(env).values():
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
