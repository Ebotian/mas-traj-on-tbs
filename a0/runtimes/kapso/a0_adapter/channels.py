"""The two evaluation channels the A0.1 comparison is made of.

* **reference channel** — the frozen ``E*`` invocation (binding decision 2 in
  the study brief) run directly on the pristine ``C*`` directory, with the
  ``EID*`` canonical ``theta_E``.  This is the ``E*(c)`` side.
* **registered channel** — KAPSO's *own* registered-evaluation invocation:
  the command string KAPSO composes (``maintainer.evaluation_command``,
  ``maintainer.py:56-61``) run in a worktree of the candidate's branch, after
  KAPSO's own ``sync_registered_evaluation`` has overwritten the branch's
  ``kapso_evaluation/`` with the registered head.  This is the ``E_r(c)`` side,
  and it captures the exit code and the raw manifest line rather than only a
  float, so a verdict of *invalid*/*error* cannot be collapsed into a number.

Neither channel reads a score from any KAPSO summary field: the score is either
E*'s ``objective.value`` (reference) or the ``score`` key of the manifest line
the wrapper printed from E*'s own manifest (registered).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .common import AdapterConfig, EidStar, sha256_file

MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"


@dataclass
class ReferenceResult:
    candidate_id: str
    exit_code: int
    status: str
    objective: Optional[float]
    outcome: Dict[str, Any]
    outcome_path: str
    stderr_tail: str
    elapsed_sec: float
    command: str
    theta: Dict[str, Any]

    @property
    def fields(self) -> Dict[str, Any]:
        return dict(self.outcome.get("fields") or {})

    @property
    def failure_kind(self) -> Optional[str]:
        failure = self.outcome.get("failure") or {}
        return failure.get("kind")


@dataclass
class RegisteredResult:
    candidate_id: str
    exit_code: int
    manifest: Optional[Dict[str, Any]]
    stdout: str
    stderr: str
    elapsed_sec: float
    command: str
    theta: Dict[str, Any]
    cwd: str
    worktree: Optional[str] = None

    @property
    def status(self) -> Optional[str]:
        if self.manifest is None:
            return None
        return self.manifest.get("e_star_status")

    @property
    def score(self) -> Optional[float]:
        if self.manifest is None:
            return None
        value = self.manifest.get("score")
        return None if value is None else float(value)


def _theta_args(theta: Dict[str, Any]) -> list[str]:
    return [
        "--seed", str(int(theta["seed"])),
        "--fidelity", str(theta["fidelity"]),
        "--fraction", repr(float(theta["fraction"])),
    ]


def run_reference_e_star(
    config: AdapterConfig,
    eid: EidStar,
    candidate_id: str,
    candidate_dir: Path,
    theta: Dict[str, Any],
    state_root: Path,
) -> ReferenceResult:
    """The frozen E* invocation, run outside any runtime.

    Every path handed to E* is absolute: E* executes the candidate from a child
    process with a private cwd, so a relative ``--out``/``--state-dir`` would
    land somewhere else (and possibly inside a candidate tree).
    """
    out_dir = (Path(state_root) / "reference").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    outcome_path = out_dir / f"{candidate_id}.{theta['fidelity']}.json"
    command = [
        str(config.e_star_python),
        str(config.e_star_dir / "e_star.py"),
        "evaluate",
        "--candidate", str(Path(candidate_dir).resolve()),
        "--seed", str(int(theta["seed"])),
        "--fidelity", str(theta["fidelity"]),
        "--fraction", repr(float(theta["fraction"])),
        "--out", str(outcome_path),
        "--state-dir", str((Path(state_root) / "e_star_state").resolve()),
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    completed = subprocess.run(
        command, capture_output=True, text=True, env=env,
        cwd=str(Path(state_root).resolve()),
    )
    elapsed = time.monotonic() - started
    if not outcome_path.is_file():
        raise RuntimeError(
            f"E* wrote no outcome for {candidate_id} (exit "
            f"{completed.returncode}): {completed.stderr[:400]}"
        )
    outcome = json.loads(outcome_path.read_text("utf-8"))
    objective = outcome.get("objective") or {}
    return ReferenceResult(
        candidate_id=candidate_id,
        exit_code=completed.returncode,
        status=outcome["status"],
        objective=(
            None if objective.get("value") is None else float(objective["value"])
        ),
        outcome=outcome,
        outcome_path=str(outcome_path),
        stderr_tail=completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "",
        elapsed_sec=elapsed,
        command=" ".join(command[1:]),
        theta=dict(theta),
    )


def run_registered_channel(
    candidate_id: str,
    *,
    command: str,
    cwd: Path,
    theta: Dict[str, Any],
    env_overrides: Optional[Dict[str, str]] = None,
    timeout_seconds: Optional[float] = None,
) -> RegisteredResult:
    """Run KAPSO's registered command and capture its full evidence."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_overrides:
        env.update(env_overrides)
    started = time.monotonic()
    completed = subprocess.run(
        shlex.split(command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout_seconds,
    )
    elapsed = time.monotonic() - started
    manifest: Optional[Dict[str, Any]] = None
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith(MANIFEST_MARKER):
            manifest = json.loads(stripped[len(MANIFEST_MARKER):].strip())
    return RegisteredResult(
        candidate_id=candidate_id,
        exit_code=completed.returncode,
        manifest=manifest,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_sec=elapsed,
        command=command,
        theta=dict(theta),
        cwd=str(cwd),
    )


def describe_candidate(candidate_id: str, path: Path) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "solution_sha256": sha256_file(path / "solution.py"),
    }
