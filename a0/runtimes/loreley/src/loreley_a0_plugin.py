"""A0 Loreley evaluator plugin: run the frozen canonical evaluator ``E*``.

This module is loaded by Loreley through ``WORKER_EVALUATOR_PLUGIN=module:attr``
(``loreley/core/worker/evaluator.py:1813`` imports the module, ``:1863`` resolves
the callable), spawned in a separate process by ``Evaluator._execute_with_timeout``
(``loreley/core/worker/evaluator.py:1859``) and called with a real
``EvaluationContext``.

Contract duties, all enforced here and nowhere else:

* hard constraint 1 (``plan:544``) - the plugin never uses ``cwd`` or ``PATH``.
  Every path it needs is absolute and comes from the environment; ``E*`` is
  invoked with an explicit interpreter path and an explicit candidate path.
* hard constraint 3 (``plan:549``) - the plugin returns ``E*``'s **multi-field**
  output intact.  Scalarization is ``F_r``'s job (the adapter's), not ``E*``'s
  and not the plugin's.
* the three false-green traps (``plan:551-552``) - the plugin never fabricates a
  score.  A timeout raises (Loreley then synthesizes a candidate failure, which
  is the behaviour under test) and every evaluation leaves a machine-readable
  evidence record in ``A0_EVIDENCE_DIR`` so the adapter can label the score
  event ``ok`` / ``timeout`` / ``truncated_metrics`` / ``cache_hit`` instead of
  guessing from a number.

The plugin writes nothing inside ``context.worktree``: ``E*`` copies the
candidate source below its own ``--state-dir`` before executing it
(``e_star.py`` outcome field ``Config.cwd_independence``), and the evidence
records go to ``A0_EVIDENCE_DIR`` which the adapter keeps outside every
candidate tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

from loreley.core.worker.evaluator import EvalFail, EvalPass, EvaluationContext

__all__ = ["plugin", "evaluation_protocol", "A0PluginError"]

EVIDENCE_SCHEMA = "a0.loreley.plugin_evidence/v1"

# E* exit codes (frozen contract: 0 ok, 2 invalid, 3 error).
E_STAR_EXIT_OK = 0
E_STAR_EXIT_INVALID = 2
E_STAR_EXIT_ERROR = 3

# E* failure kind -> Loreley EvalFail kind.  ``_VALID_EVAL_FAIL_KINDS`` is
# ``{compile, typecheck, lint, test, validation, benchmark, other}``
# (loreley/core/worker/evaluator.py:98-106).
_FAIL_KIND_MAP = {
    "invalid_configuration": "validation",
    "candidate_import_failed": "compile",
    "candidate_call_raised": "test",
    "non_deterministic": "test",
    "runtime_budget_exceeded": "benchmark",
    "child_terminated_early": "other",
}

# Fields of E*'s Outcome that are never emitted as metrics: they are bookkeeping
# about the audit, not objectives, and E* itself marks them as such.
_NON_METRIC_FIELDS = frozenset({"audit_coverage", "items_audited", "pairs_audited"})


class A0PluginError(RuntimeError):
    """The plugin could not produce an evidence-backed result."""


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise A0PluginError(
            f"{name} is not set; the A0 adapter must pin every path the plugin uses "
            "(hard constraint 1 forbids relying on cwd or PATH)."
        )
    return value


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _evidence_dir() -> Path | None:
    raw = os.environ.get("A0_EVIDENCE_DIR", "").strip()
    return Path(raw) if raw else None


def _write_evidence(record: Mapping[str, Any], *, candidate_dir: Path) -> None:
    """Append one evidence record; never raise into the evaluation path."""

    directory = _evidence_dir()
    if directory is None:
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(str(candidate_dir).encode("utf-8")).hexdigest()[:16]
        payload = dict(record)
        payload.setdefault("schema", EVIDENCE_SCHEMA)
        payload["plugin_pid"] = os.getpid()
        path = directory / f"{key}.json"
        path.write_text(json.dumps(payload, sort_keys=True, indent=1), encoding="utf-8")
    except Exception:  # pragma: no cover - evidence must never break evaluation
        pass


def _evaluate_command(candidate_dir: Path, out_path: Path, resources_path: Path) -> list[str]:
    python = _require_env("A0_E_STAR_PY")
    script = _require_env("A0_E_STAR_SCRIPT")
    seed = os.environ.get("A0_E_STAR_SEED", "1337").strip() or "1337"
    fidelity = os.environ.get("A0_E_STAR_FIDELITY", "full").strip() or "full"
    fraction = os.environ.get("A0_E_STAR_FRACTION", "1.0").strip() or "1.0"
    command = [
        python,
        script,
        "evaluate",
        "--candidate",
        str(candidate_dir),
        "--seed",
        seed,
        "--fidelity",
        fidelity,
        "--fraction",
        fraction,
        "--out",
        str(out_path),
    ]
    # The remaining theta_E coordinates are passed through when the adapter has
    # them, so the frozen (seed, fidelity, fraction, n, runs, runtime_budget_ms,
    # timeout_s) is what E* actually runs at rather than E*'s own defaults.
    for env_name, flag in (
        ("A0_E_STAR_N", "--n"),
        ("A0_E_STAR_RUNS", "--runs"),
        ("A0_E_STAR_RUNTIME_BUDGET_MS", "--runtime-budget-ms"),
        ("A0_E_STAR_TIMEOUT_S", "--timeout-s"),
    ):
        value = os.environ.get(env_name, "").strip()
        if value:
            command += [flag, value]
    state_dir = os.environ.get("A0_E_STAR_STATE_DIR", "").strip()
    if state_dir:
        command += ["--state-dir", state_dir]
    if _flag("A0_LORELEY_EMIT_TIMING", default=False):
        command += ["--emit-resources", str(resources_path)]
    return command


def _parse_manifest_line(stdout: str) -> tuple[str | None, dict[str, Any] | None]:
    """Return E*'s own manifest line verbatim plus its parsed form.

    The verbatim line is kept because it is the one piece of evidence a third party
    can check without trusting the adapter: it names the evaluator source digest, the
    candidate digest and the theta_E E* actually ran at
    (a0/conformance/README.md, `E-star-manifest-echo`).
    """

    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped.startswith("E_STAR_MANIFEST "):
            try:
                return stripped, json.loads(stripped[len("E_STAR_MANIFEST ") :])
            except json.JSONDecodeError:
                return stripped, None
    return None, None


def _metrics_from_outcome(
    outcome: Mapping[str, Any],
    *,
    resources: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], int]:
    """Project E*'s multi-field Outcome onto Loreley metrics, keeping every field."""

    fields = outcome.get("fields") or {}
    objective = outcome.get("objective") or {}
    primary_field = objective.get("name")
    # E* declares one signed objective (``objective.direction``) and an audit
    # surface of unsigned measurements.  Loreley metrics are unsigned too, and
    # the direction conflict is caught downstream by
    # ``ObjectiveContract.resolve`` (loreley/core/map_elites/objectives.py:118-133),
    # so the primary field follows E* and everything else stays max-oriented.
    primary_higher_is_better = str(objective.get("direction", "max")) != "min"

    metrics: list[dict[str, Any]] = []
    for name in sorted(fields):
        value = fields[name]
        if value is None or isinstance(value, bool):
            continue
        if not isinstance(value, (int, float)):
            continue
        if name in _NON_METRIC_FIELDS:
            continue
        metrics.append(
            {
                "name": name,
                "value": float(value),
                "unit": objective.get("unit") if name == primary_field else None,
                "higher_is_better": (
                    primary_higher_is_better if name == primary_field else True
                ),
                # ``details`` carries provenance so a reader can tell which field
                # of E*'s Outcome a metric came from without re-running E*.
                "details": {"source": "E*.outcome.fields", "e_star_field": name},
            }
        )
    if resources is not None and _flag("A0_LORELEY_EMIT_TIMING", default=False):
        p50 = resources.get("runtime_ms_p50")
        if isinstance(p50, (int, float)):
            metrics.append(
                {
                    "name": "runtime_p50_ms",
                    "value": float(p50),
                    "unit": "ms",
                    "higher_is_better": False,
                    "details": {
                        "source": "E*.resources.runtime_ms_p50",
                        "note": "timing sidecar; never part of the canonical Outcome",
                    },
                }
            )

    # F_r lives here because Loreley's ObjectiveContract reads the *evaluator's*
    # metric vector and nothing else (loreley/core/map_elites/objectives.py:100-133);
    # the runtime has no other channel through which a declared F_r could reach
    # selection.  ``F_r = scalar(E*)`` therefore appears as one extra metric named
    # by the frozen --fr declaration, while E*'s own fields stay untouched.
    if _flag("A0_FR_MODE_SCALAR", default=False):
        name = os.environ.get("A0_FR_METRIC_NAME", "composite_score").strip() or "composite_score"
        if primary_field and isinstance(fields.get(primary_field), (int, float)):
            metrics.append(
                {
                    "name": name,
                    "value": float(fields[primary_field]),
                    "unit": objective.get("unit"),
                    "higher_is_better": primary_higher_is_better,
                    "details": {
                        "source": "F_r",
                        "fr_spec_hash": os.environ.get("A0_FR_SPEC_HASH", ""),
                        "fold": f"scalar(E*) = outcome.fields.{primary_field}",
                    },
                }
            )
    return metrics, len(fields)


def _run_e_star(candidate_dir: Path) -> dict[str, Any]:
    """Execute ``E*`` once and return the canonical Outcome plus provenance."""

    tmp_root = os.environ.get("A0_E_STAR_OUT_DIR", "").strip()
    workdir = Path(tmp_root) if tmp_root else Path(tempfile.mkdtemp(prefix="a0-loreley-plugin-"))
    workdir.mkdir(parents=True, exist_ok=True)
    token = hashlib.sha256(
        f"{candidate_dir}:{os.getpid()}:{time.monotonic_ns()}".encode("utf-8")
    ).hexdigest()[:16]
    out_path = workdir / f"{token}.outcome.json"
    resources_path = workdir / f"{token}.resources.json"

    command = _evaluate_command(candidate_dir, out_path, resources_path)
    timeout_raw = os.environ.get("A0_E_STAR_TIMEOUT_S", "").strip()
    timeout = float(timeout_raw) if timeout_raw else None

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            # hard constraint 1: no inherited cwd dependency; PATH is emptied
            # because E* resolves every interpreter it spawns by absolute path.
            cwd=str(workdir),
            env=_child_env(),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        detail = f"E* timed out after {timeout}s (A0_E_STAR_TIMEOUT_S)"
        _write_evidence(
            {
                "status": "timeout",
                "detail": detail,
                "candidate_dir": str(candidate_dir),
                "timeout_s": timeout,
                "command": command,
            },
            candidate_dir=candidate_dir,
        )
        raise A0PluginError(detail) from exc
    elapsed = time.monotonic() - started

    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")
    manifest_line, manifest = _parse_manifest_line(stdout)

    outcome: dict[str, Any] | None = None
    if out_path.is_file():
        try:
            outcome = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            outcome = None

    resources: dict[str, Any] | None = None
    if resources_path.is_file():
        try:
            resources = json.loads(resources_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            resources = None

    if outcome is None:
        detail = (
            f"E* produced no readable Outcome JSON (exit={completed.returncode}, "
            f"stderr={stderr.strip()[:400]!r})"
        )
        _write_evidence(
            {
                "status": "synthesized_failure",
                "detail": detail,
                "candidate_dir": str(candidate_dir),
                "exit_code": completed.returncode,
                "command": command,
                "stderr": stderr[-2000:],
            },
            candidate_dir=candidate_dir,
        )
        raise A0PluginError(detail)

    return {
        "outcome": outcome,
        "resources": resources,
        "manifest": manifest,
        "manifest_line": manifest_line,
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_s": elapsed,
        "command": command,
        "outcome_path": str(out_path),
    }


def _child_env() -> dict[str, str]:
    """A minimal, explicit child environment for ``E*``."""

    keep = (
        "A0_E_STAR_STATE_DIR",
        "CIRCLE_PACKING_RUNTIME_BUDGET_MS",
        "CIRCLE_PACKING_RUNTIME_RUNS",
    )
    env = {
        "PATH": "",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
        "HOME": os.environ.get("A0_E_STAR_HOME", "/tmp"),
        "TMPDIR": os.environ.get("A0_E_STAR_TMPDIR", "/tmp"),
        "LANG": "C.UTF-8",
    }
    for name in keep:
        value = os.environ.get(name)
        if value:
            env[name] = value
    return env


def plugin(context: EvaluationContext) -> EvalPass | EvalFail:
    """A0 evaluator plugin: ``EvaluationContext`` -> ``EvalPass`` / ``EvalFail``."""

    candidate_dir = Path(context.worktree)
    if not (candidate_dir / "solution.py").is_file():
        raise A0PluginError(
            f"context.worktree {candidate_dir!s} does not contain solution.py; "
            "C* members are directories laid out like the task repository."
        )

    result = _run_e_star(candidate_dir)
    outcome = result["outcome"]
    status = str(outcome.get("status", ""))
    fields = outcome.get("fields") or {}
    failure = outcome.get("failure") or {}
    failure_kind = failure.get("kind")
    metrics, field_count = _metrics_from_outcome(outcome, resources=result["resources"])

    max_metrics_raw = os.environ.get("WORKER_EVALUATOR_MAX_METRICS", "64").strip()
    try:
        max_metrics = int(max_metrics_raw)
    except ValueError:
        max_metrics = 64
    dropped = max(0, len(metrics) - max_metrics)

    base_evidence = {
        "candidate_dir": str(candidate_dir),
        "candidate_source_sha256": (outcome.get("candidate") or {}).get("source_sha256"),
        "e_star_status": status,
        "e_star_exit_code": result["exit_code"],
        "e_star_canonical_digest": outcome.get("canonical_digest"),
        "e_star_manifest": result["manifest"],
        "e_star_manifest_line": result["manifest_line"],
        "outcome_fields": dict(fields),
        "outcome_field_count": field_count,
        "metrics_returned": len(metrics),
        "metrics_returned_names": [item["name"] for item in metrics],
        "worker_evaluator_max_metrics": max_metrics,
        "metrics_dropped": dropped,
        "elapsed_s": result["elapsed_s"],
        "command": result["command"],
    }

    if status != "ok" or outcome.get("scored") is not True:
        # A measured non-scoring verdict.  E* ran and audited the candidate; this
        # is NOT the timeout/synthesized-failure trap, and the evidence says so by
        # carrying E*'s real (all-null where unmeasurable) field map.
        detail = (
            f"E* status={status!r} kind={failure_kind!r}: "
            f"{str(failure.get('message', '')).strip()[:400]}"
        )
        _write_evidence(
            {
                **base_evidence,
                "status": "ok",
                "measured_scoring": False,
                "detail": detail,
                "e_star_failure": failure,
            },
            candidate_dir=candidate_dir,
        )
        return EvalFail(
            kind=_FAIL_KIND_MAP.get(str(failure_kind), "other"),
            summary=f"E* reported status={status} ({failure_kind or 'unclassified'})",
            details=detail,
        )

    _write_evidence(
        {
            **base_evidence,
            "status": "ok",
            "measured_scoring": True,
            "detail": None,
        },
        candidate_dir=candidate_dir,
    )
    return EvalPass(
        summary=(
            f"E* status=ok sum_radii={(fields.get('sum_radii'))} "
            f"fields={field_count} canonical_digest={outcome.get('canonical_digest')}"
        ),
        metrics=metrics,
        extra={
            "e_star_canonical_digest": outcome.get("canonical_digest"),
            "e_star_outcome_fields": dict(fields),
            "e_star_manifest": result["manifest"],
        },
        candidate_identity=str((outcome.get("candidate") or {}).get("source_sha256") or "")
        or None,
    )


# The plugin is callable, so Loreley never consults this attribute; it is here so
# that a phased-capable audit plugin can be selected by name if one is ever built.
evaluation_protocol = "one_shot-v1"
