"""The EvE side of the adapter: compose the real config, wire the real evaluation path.

Everything here drives EvE's own code. The seams are named explicitly in
``adapter.md`` and reported in ``conformance.json`` as ``seams``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import common, eidmap
from .common import Candidate, Fr, Theta

EVE_ROOT = Path(os.environ.get("A0_EVE_ROOT", "/tmp/eve")).resolve()
EVE_PINNED_COMMIT = "979065fd2cf1b3be9caf70596478fe27df7815ad"
EVE_SRC = EVE_ROOT / "src"

STEP_TEMPLATE = common.ADAPTER_DIR / "steps" / "eve_evaluator_step.sh.tmpl"


class EveWiringError(RuntimeError):
    pass


def eve_head() -> str:
    proc = subprocess.run(
        ["git", "-C", str(EVE_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def require_pinned_eve() -> str:
    head = eve_head()
    if head != EVE_PINNED_COMMIT:
        raise EveWiringError(
            f"EvE checkout at {EVE_ROOT} is at {head}, not the pinned {EVE_PINNED_COMMIT}"
        )
    return head


def add_eve_to_path() -> None:
    """Make /tmp/eve importable without installing into (and thus mutating) the snapshot."""
    import sys

    entry = str(EVE_SRC)
    if entry not in sys.path:
        sys.path.insert(0, entry)
    parts = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    if entry not in parts:
        os.environ["PYTHONPATH"] = os.pathsep.join([p for p in [entry, *parts] if p])
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


# --------------------------------------------------------------------------------------
# The generated evaluation step
# --------------------------------------------------------------------------------------


@dataclass
class StepScript:
    path: Path
    sha256: str
    pins: dict[str, Any]


def render_step_script(
    *,
    path: Path,
    e_star_python: Path,
    e_star_script: Path,
    state_dir: Path,
    theta: Theta,
    primary_field: str,
    eid_star: str,
    pins_sha256: str,
) -> StepScript:
    template = STEP_TEMPLATE.read_text(encoding="utf-8")
    values = {
        "@E_STAR_PYTHON@": str(e_star_python),
        "@E_STAR_SCRIPT@": str(e_star_script),
        "@E_STAR_STATE_DIR@": str(state_dir),
        "@SEED@": str(common.FROZEN_THETA["seed"] if theta.seed is None else theta.seed),
        "@FIDELITY@": str(theta.fidelity),
        "@FRACTION@": repr(float(theta.fraction)),
        "@N@": str(theta.n),
        "@RUNS@": str(theta.runs),
        "@TIMEOUT_S@": str(theta.timeout_s),
        "@RUNTIME_BUDGET_MS@": repr(float(theta.runtime_budget_ms)),
        "@PRIMARY_FIELD@": primary_field,
        "@EID_STAR@": eid_star,
        "@PINS_SHA@": pins_sha256,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(key, value)
    leftover = [line for line in rendered.splitlines() if "@" in line and line.count("@") >= 2]
    if leftover:
        raise EveWiringError(f"unsubstituted placeholder in step script: {leftover[:3]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    path.chmod(0o755)
    return StepScript(path=path, sha256=common.sha256_file(path), pins=values)


def eid_r_inputs(eid_document: dict[str, Any], fr_spec_hash: str) -> "eidmap.EidInputs":
    """The published inputs `EID_r` is derived from (`a0_adapter/eidmap.py`)."""
    return eidmap.inputs_from_contract(eid_document=eid_document, fr_spec_hash=fr_spec_hash)


def eid_r_payload(
    step: StepScript,
    *,
    eid_document: dict[str, Any],
    fr_spec_hash: str,
) -> dict[str, Any]:
    """EID_r for every trace event (trace_schema.md §3.1).

    `EID*` is an *input* of the hash, not a neighbouring field: `value` is
    `sha256(domain || 0x00 || canonical_json(payload))` over a payload carrying `eid_star`,
    the evaluator-source records of `EID*` (re-hashed from the bytes EvE will invoke) and the
    frozen F_r declaration digest. A different `EID*` therefore necessarily yields a different
    `EID_r` (`a0_adapter/eidmap.py`, `tools/recompute-eid-r`).
    """
    inputs = eid_r_inputs(eid_document, fr_spec_hash)
    return {
        "value": eidmap.derive_eid_r(inputs),
        "native_scheme": "none",
        "mapping_mode": "adapter_declared_injection",
        "derives_from_eid_star": step_pins_eid(step),
        "declaration": eidmap.EID_R_DECLARATION,
        "recomputable": True,
    }


def eid_r_enrichment(
    step: StepScript,
    *,
    eid_document: dict[str, Any],
    fr_spec_hash: str,
    eid_path: Path,
    fr_path: Path,
) -> dict[str, Any]:
    """The document-only half: the recompute command, the recipe and the step's provenance.

    The trace `eid_r` block is schema-closed (`trace_schema.json` `$defs/eidR`), so these keys
    live in the conformance document and in `adapter.md` instead of on every event.
    """
    inputs = eid_r_inputs(eid_document, fr_spec_hash)
    return {
        "recompute_cmd": [
            sys.executable,
            str(common.ADAPTER_DIR / "tools" / "recompute-eid-r"),
            "--eid", str(Path(eid_path).resolve()),
            "--fr", str(Path(fr_path).resolve()),
            "--a0-root", str(common.A0_ROOT),
        ],
        "derivation": eidmap.eid_r_derivation(inputs),
        "injected_step": {
            "path": str(step.path),
            "sha256": step.sha256,
            "template": str(STEP_TEMPLATE),
            "template_sha256": common.sha256_file(STEP_TEMPLATE),
            "note": (
                "provenance, deliberately NOT hashed into EID_r: the rendered step embeds the "
                "run's absolute state-dir path, so including it would make EID_r a "
                "per-run-directory value rather than an evaluator identity. The step is what "
                "A0.1 exercises and what `a01` reports on."
            ),
        },
    }


def step_pins_eid(step: StepScript) -> str:
    return step.pins["@EID_STAR@"]


# --------------------------------------------------------------------------------------
# Hydra composition of the real run config
# --------------------------------------------------------------------------------------


@dataclass
class EveContext:
    cfg: Any
    problem: Any
    plan: Any
    evaluator: Any
    renderer: Any
    immutable_files: dict[str, str]
    step: StepScript
    config_source: list[str] = field(default_factory=list)
    snapshot_root: Path = Path("/")
    failure_score: dict[str, Any] = field(default_factory=dict)
    boundary_failure_score: dict[str, Any] = field(default_factory=dict)


def compose_eve_config(*, run_dir: Path, step_script: Path) -> Any:
    """Compose configs/eve/circle_packing.yaml from the pinned checkout.

    The only deviation from the shipped config is ``evaluation.steps`` pointing at the
    adapter's generated step — the declaration required by adapter_contract.md §5.2.
    """
    add_eve_to_path()
    from hydra import compose, initialize_config_dir

    config_dir = EVE_ROOT / "configs" / "eve"
    if not config_dir.is_dir():
        raise EveWiringError(f"EvE config dir not found: {config_dir}")
    overrides = [
        f'evaluation.steps=["{step_script}"]',
        f"loop.workspace_root={run_dir / 'eve' / 'workspaces'}",
    ]
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="circle_packing", overrides=overrides)
    return cfg


def _problem_with_retry(application: dict, *, cache_root: Path, search_root: Path, attempts: int = 3):
    """Build the RepoTaskProblem, retrying the seed-repo clone.

    `RepoTaskProblem._resolve_checkout` (problem/repo.py:141-155) removes the cached checkout
    and re-clones on every call, and it does not retry: one transient `git clone` failure
    (exit 128) aborts the whole adapter run. The adapter therefore retries the *whole*
    construction, which is idempotent, and reports how many attempts it took.

    The (github_url, commit) pair is still the source of truth: the snapshot is produced by
    `git archive <resolved commit>` and `_export_snapshot` re-runs `rev-parse` on the commit,
    so a hash mismatch cannot pass silently.
    """
    import time as _time

    from scaling_evolve.algorithms.eve.problem.repo import RepoTaskProblem

    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            problem = RepoTaskProblem.from_config(
                application, cache_root=cache_root, search_root=search_root
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attempt {attempt}: {exc!r}")
            if attempt < attempts:
                _time.sleep(5 * attempt)
            continue
        return problem
    raise EveWiringError(
        "could not materialise the seed repository from (github_url, commit) "
        f"after {attempts} attempts: " + " | ".join(errors)
    )


def build_context(
    *,
    run_dir: Path,
    theta: Theta,
    fr: Fr,
    eid_star: str,
    pins_sha256: str,
    step_script_override: Path | None = None,
) -> EveContext:
    head = require_pinned_eve()
    run_dir = Path(run_dir).resolve()
    state_dir = run_dir / "e-star-state"
    if step_script_override is None:
        step = render_step_script(
            path=run_dir / "evaluator" / "eve_evaluator_step.sh",
            e_star_python=common.E_STAR_PYTHON,
            e_star_script=common.E_STAR_SCRIPT,
            state_dir=state_dir,
            theta=theta,
            primary_field=fr.primary_field,
            eid_star=eid_star,
            pins_sha256=pins_sha256,
        )
    else:
        # An unmodified foreign step (used only to reproduce the shipped failure contract).
        override = Path(step_script_override)
        step = StepScript(
            path=override,
            sha256=common.sha256_file(override),
            pins={"@EID_STAR@": eid_star},
        )
    cfg = compose_eve_config(run_dir=run_dir, step_script=step.path)

    from omegaconf import OmegaConf
    from scaling_evolve.algorithms.eve.problem.repo import RepoTaskProblem
    from scaling_evolve.algorithms.eve.workflow.evaluation import (
        build_evaluation_plan,
        build_solver_evaluator,
    )

    application = OmegaConf.to_container(cfg.application, resolve=True)
    if not isinstance(application, dict):
        raise EveWiringError("application config did not resolve to a mapping")
    if not application.get("github_url") or not application.get("commit"):
        # The assignment's requirement: the seed repo is the (github_url, commit) pair, and
        # a missing half is an error rather than a silent local-path fallback.
        raise EveWiringError(
            "application must configure BOTH github_url and commit for the seed repo; "
            f"got github_url={application.get('github_url')!r} commit={application.get('commit')!r}"
        )

    problem = _problem_with_retry(
        application,
        cache_root=run_dir / "eve" / "cache",
        search_root=EVE_ROOT,
    )
    plan = build_evaluation_plan(problem, evaluation_config=cfg.evaluation, search_root=EVE_ROOT)
    for index, plan_step in enumerate(plan.steps, start=1):
        if plan_step.is_judge:
            raise EveWiringError(
                f"evaluation step {index} is a judge step; A0 freezes a shell-only plan"
            )
        if plan_step.path is None or plan_step.path.resolve() != step.path.resolve():
            raise EveWiringError(
                f"evaluation step {index} is {plan_step.path}, expected the adapter step "
                f"{step.path}"
            )

    failure_score = OmegaConf.to_container(cfg.evaluation.failure_score, resolve=True)
    boundary_failure_score = OmegaConf.to_container(cfg.application.boundary_failure_score, resolve=True)

    def _no_driver() -> Any:
        raise EveWiringError("a judge step requested an agent driver; A0 freezes a shell-only plan")

    evaluator = build_solver_evaluator(
        problem,
        evaluation_plan=plan,
        evaluation_failure_score=failure_score,
        boundary_failure_score=boundary_failure_score,
        seed_solver_score=OmegaConf.to_container(cfg.evaluation.seed_solver_score, resolve=True)
        if cfg.evaluation.seed_solver_score is not None
        else None,
        seed_solver_skip_evaluation=bool(cfg.evaluation.seed_solver_skip_evaluation),
        include_solver_examples=False,
        evaluation_driver_factory=_no_driver,
    )

    from hydra.utils import instantiate
    from scaling_evolve.algorithms.eve.workspace.file_tree import read_file_tree

    renderer = instantiate(cfg.optimizer.immutable_renderer, _convert_="all")
    immutable_files = read_file_tree(EVE_ROOT / "configs" / "eve" / "optimizer" / "circle_packing" / "immutable")
    return EveContext(
        cfg=cfg,
        problem=problem,
        plan=plan,
        evaluator=evaluator,
        renderer=renderer,
        immutable_files=immutable_files,
        step=step,
        config_source=[
            "configs/eve/circle_packing.yaml",
            "configs/eve/loop/default.yaml",
            "configs/eve/driver/codex_max.yaml",
            "configs/eve/application/circle_packing.yaml",
            "configs/eve/evaluation/circle_packing.yaml",
            "configs/eve/optimizer/circle_packing.yaml",
            f"eve_commit={head}",
        ],
        snapshot_root=Path(problem.snapshot_root),
        failure_score=failure_score,
        boundary_failure_score=boundary_failure_score,
    )


# --------------------------------------------------------------------------------------
# One candidate through EvE's own evaluation machinery
# --------------------------------------------------------------------------------------


@dataclass
class RuntimeEvaluation:
    candidate_id: str
    candidate_sha256: str
    workspace_root: Path
    eval_workspace: Path
    elapsed_s: float
    score: Any
    logs: dict[str, str]
    scalar: float | None
    evidence_status: str
    evidence_detail: str | None
    side_channel: dict[str, Any]
    evaluator_rc: int | None
    e_star_status: str | None
    stdout_tail: str


def side_channel_paths(ctx: EveContext, workspace_root: Path) -> dict[str, Any]:
    """The evidence T1 requires: read the step's own status/error files, not the number."""
    from scaling_evolve.algorithms.eve.workflow.evaluation import (
        _judge_workspace_for_solver_workspace,
        _step_log_dir,
    )

    workspace_root = Path(workspace_root)
    eval_ws = _judge_workspace_for_solver_workspace(workspace_root)
    # plan.steps[0].name is the step file's stem, as _run_shell_step derives it.
    step_dir = _step_log_dir(
        step_name=ctx.plan.steps[0].name, step_index=1, workspace_root=eval_ws
    )
    status_file = step_dir / "status.txt"
    error_file = step_dir / "error.txt"
    stderr_file = step_dir / "stderr.txt"
    outcome_file = eval_ws / "logs" / "evaluate" / "e_star" / "outcome.json"
    note_file = eval_ws / "logs" / "evaluate" / "e_star" / "step_note.txt"
    score_file = eval_ws / "logs" / "evaluate" / "score.yaml"
    # EvE's evaluation contract puts the failure reason at the eval-log ROOT
    # (configs/eve/evaluation/circle_packing/evaluation.sh:10 defines error.txt there).
    root_error_file = eval_ws / "logs" / "evaluate" / "error.txt"
    e_star_stdout_file = eval_ws / "logs" / "evaluate" / "e_star" / "e_star.stdout.txt"

    def read(path: Path, limit: int = 4000) -> str | None:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:limit]

    # E*'s own one-line manifest, captured inside the runtime's own evaluation lane. Handing
    # this to the conformance runner gives it an *independent* confirmation channel for theta_E
    # and for the evaluator source digest (conformance.py:1603-1623 manifest_echoes).
    e_star_manifest_line = None
    stdout_text = read(e_star_stdout_file, 200000) or ""
    for line in reversed(stdout_text.splitlines()):
        if line.startswith("E_STAR_MANIFEST "):
            e_star_manifest_line = line.strip()
            break

    outcome = None
    if outcome_file.is_file():
        try:
            outcome = json.loads(outcome_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            outcome = None
    return {
        "eval_workspace": str(eval_ws),
        "step_status_path": str(status_file),
        "step_status": read(status_file, 64),
        "error_path": str(error_file),
        "error_present": error_file.is_file(),
        "error_text": read(error_file),
        "log_root_error_path": str(root_error_file),
        "log_root_error_present": root_error_file.is_file(),
        "log_root_error_text": read(root_error_file),
        "stderr_present": stderr_file.is_file(),
        "stderr_text": read(stderr_file),
        "score_yaml_present": score_file.is_file(),
        "step_note": read(note_file),
        "e_star_outcome_status": None if outcome is None else outcome.get("status"),
        "e_star_outcome_failure": None if outcome is None else outcome.get("failure"),
        "e_star_manifest_line": e_star_manifest_line,
        "e_star_stdout_path": str(e_star_stdout_file),
    }


def _payloads_equal(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


_FAILURE_STATUS_TOKENS = {
    "error", "failed", "failure", "invalid", "crash", "crashed", "timeout", "timed_out",
    "not_run", "unavailable", "exception",
}
_STATUS_KEYS = ("status", "e_star_status", "evaluation_status", "state", "result_status", "outcome")


def _failure_marker_in_payload(score: Any) -> dict[str, Any] | None:
    """Detect an error-shaped payload that still carries a numeric score.

    The adapter treats the payload's own status vocabulary as evidence: a run is a
    measurement only if nothing in it says otherwise. This is what catches route R3 in the
    trap record — an evaluator that reports ``status: "error"`` alongside ``score: 0.0``.
    """
    if not isinstance(score, dict):
        return None
    markers: dict[str, Any] = {}
    for key in _STATUS_KEYS:
        value = score.get(key)
        if isinstance(value, str) and value.strip().lower() in _FAILURE_STATUS_TOKENS:
            markers[key] = value
    if score.get("error") not in (None, "", False):
        markers["error"] = str(score["error"])[:200]
    return markers or None


def evaluate_candidate_through_eve(
    ctx: EveContext,
    candidate: Candidate,
    *,
    fr: Fr,
    iteration: int,
    extra_files: dict[str, str] | None = None,
) -> RuntimeEvaluation:
    import time

    solution_src = (candidate.path / "solution.py").read_text(encoding="utf-8")
    candidate_files = {"solution.py": solution_src}
    if extra_files:
        candidate_files.update(extra_files)
    workspace_root = Path(ctx.cfg.loop.workspace_root) / "solver_workspaces" / candidate.candidate_id
    workspace_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    score, logs = ctx.evaluator.evaluate(
        workspace_root,
        candidate_files=candidate_files,
        optimize_logs={},
        display_context={"iteration": iteration, "worker_index": 0, "adapter": "a0_eve"},
    )
    elapsed = time.monotonic() - started
    side = side_channel_paths(ctx, workspace_root)

    scalar = None
    if isinstance(score, dict):
        from scaling_evolve.algorithms.eve.populations.score import scalar as to_scalar

        try:
            scalar = to_scalar(score)
        except TypeError:
            scalar = None

    # T1: the numeric value alone is not evidence. Classify from the side channel.
    step_failed = (side.get("step_status") or "").strip() == "failed" or bool(
        side.get("log_root_error_present")
    )
    side_note = (
        f"(side channel: step_status={side['step_status']!r}, "
        f"eval-log-root error.txt present={side['log_root_error_present']}, "
        f"e_star_status={side['e_star_outcome_status']!r})"
    )
    if _payloads_equal(score, ctx.failure_score) or step_failed:
        status = "synthesized_failure"
        route = (
            "EvE returned evaluation.failure_score verbatim "
            f"{json.dumps(ctx.failure_score, sort_keys=True)} because a step exception was "
            "swallowed by SolverEvaluator.evaluate's `except Exception` "
            "(workflow/evaluation.py:161-165)"
        )
        if step_failed and not _payloads_equal(score, ctx.failure_score):
            route = (
                "the step's own side channel reports a failure but the returned payload is "
                f"{json.dumps(score, sort_keys=True)}, i.e. a synthesized zero that does NOT "
                "equal evaluation.failure_score — the shipped evaluation-step convention "
                "(configs/eve/evaluation/circle_packing/evaluation.sh:56-72) writes "
                "{score: 0.0, summary: 'evaluation command failed'} and exits 0, so EvE records "
                "the step as successful and the number is the only thing that would have "
                "looked like a measurement"
            )
        detail = f"{route}; E* did not measure this candidate {side_note}"
    elif _payloads_equal(score, ctx.boundary_failure_score):
        status = "not_run"
        detail = (
            "EvE returned the boundary failure score "
            f"{json.dumps(ctx.boundary_failure_score, sort_keys=True)}; the candidate "
            "violated the editable-path boundary and was never evaluated "
            "(workflow/evaluation.py:183-192)"
        )
    elif _failure_marker_in_payload(score):
        status = "synthesized_failure"
        detail = (
            "the evaluator returned a numeric score while its own payload declares a failure "
            f"({json.dumps(_failure_marker_in_payload(score), sort_keys=True)}); EvE accepted it "
            "because _validate_score_shape only checks that the leaf named by "
            "evaluation.failure_score is numeric (workflow/evaluation.py:924-935). This route "
            "has NO EvE-level side channel: the step status is 'ok' and error.txt is absent, so "
            "only the payload's own status field separates it from a genuine measurement "
            f"{side_note}"
        )
    elif scalar is not None:
        status = "ok"
        detail = None
    else:
        status = "not_run"
        detail = f"EvE returned a score with no numeric view: {json.dumps(score, default=str)}"

    evaluator_rc = None
    note = side.get("step_note") or ""
    if note.startswith("measured="):
        try:
            head = note.split(" ", 1)[0]
            evaluator_rc = 0 if head == "measured=1" else None
        except Exception:  # noqa: BLE001
            evaluator_rc = None
    if evaluator_rc is None and "measured=0" in note:
        try:
            detail_payload = json.loads(note.split(" ", 1)[1])
            evaluator_rc = detail_payload.get("rc")
        except Exception:  # noqa: BLE001
            evaluator_rc = None

    return RuntimeEvaluation(
        candidate_id=candidate.candidate_id,
        candidate_sha256=candidate.solution_sha256,
        workspace_root=workspace_root,
        eval_workspace=Path(side["eval_workspace"]),
        elapsed_s=elapsed,
        score=score,
        logs=logs,
        scalar=scalar,
        evidence_status=status,
        evidence_detail=detail,
        side_channel=side,
        evaluator_rc=evaluator_rc,
        e_star_status=side.get("e_star_outcome_status"),
        stdout_tail="",
    )


def eval_workspace_for(ctx: EveContext, candidate_id: str) -> Path:
    from scaling_evolve.algorithms.eve.workflow.evaluation import (
        _judge_workspace_for_solver_workspace,
    )

    return _judge_workspace_for_solver_workspace(
        Path(ctx.cfg.loop.workspace_root) / "solver_workspaces" / candidate_id
    )


def copy_step_script_backup(ctx: EveContext, run_dir: Path) -> str:
    """Record what actually ran, so a third party can recompute EID_r.value."""
    target = Path(run_dir) / "adapter.md"
    return str(target)


def reset_run_dir(run_dir: Path) -> None:
    for sub in ("eve", "evaluator", "reference", "traces", "e-star-state"):
        path = Path(run_dir) / sub
        if path.exists():
            shutil.rmtree(path)
