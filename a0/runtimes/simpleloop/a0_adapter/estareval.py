"""The evaluator lane: E* executed exactly through its frozen CLI.

SimpleLoop has no native evaluator of its own, so the adapter is the sole source
of the evaluator identity (adapter_contract.md §5.2). Concretely that means: this
module invokes `a0/tasks/circle-packing/e_star.py` as a subprocess, reads the
machine-readable Outcome it writes with `--out`, and treats its exit code as the
verdict. Nothing else in the adapter ever produces a score.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_ERROR = 3

STATUS_BY_EXIT = {EXIT_OK: "ok", EXIT_INVALID: "invalid", EXIT_ERROR: "error"}


class EvaluatorWiringError(RuntimeError):
    """EID* does not describe the evaluator that is actually wired (exit 3)."""


@dataclass
class EStarResult:
    candidate_id: str
    exit_code: int
    status: str
    outcome: dict | None
    manifest: dict | None
    manifest_line: str | None
    stdout: str
    stderr: str
    wall_sec: float
    out_path: Path
    command: list[str]
    failure_kind: str | None = None
    failure_message: str | None = None
    fields: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.exit_code == EXIT_OK and self.status == "ok"


@dataclass
class EStarIdentity:
    """What the adapter can prove about the evaluator it is about to run."""

    script: Path
    python: Path
    source_records: list[dict]
    source_sha256_recomputed: dict
    source_verified: bool
    recorded_source_digest: str | None
    evaluator_source_sha256_self_reported: str | None
    interpreter_version: str

    def as_dict(self) -> dict:
        return {
            "script": str(self.script),
            "python": str(self.python),
            "source_records": self.source_records,
            "source_sha256_recomputed": self.source_sha256_recomputed,
            "source_verified": self.source_verified,
            "recorded_source_digest": self.recorded_source_digest,
            "evaluator_source_sha256_self_reported": self.evaluator_source_sha256_self_reported,
            "interpreter_version": self.interpreter_version,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mini_env(home: Path) -> dict:
    """A controlled child environment.

    Hard constraint 1 (plan:544) says the evaluator must not depend on cwd or on
    PATH; the adapter therefore runs E* from a scratch cwd with a minimal PATH and
    without any proxy variable, so a pass cannot be an accident of the caller's
    shell.
    """
    home.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(home),
    }


class EStarEvaluator:
    def __init__(
        self,
        *,
        python: Path,
        script: Path,
        state_dir: Path,
        out_dir: Path,
        seed: int,
        fidelity: str,
        fraction: float,
        n: int = 26,
        runs: int = 5,
        runtime_budget_ms: float = 250.0,
        timeout_s: float = 120.0,
        cwd: Path | None = None,
        emit_resources_dir: Path | None = None,
        expected_source_records: list[dict] | None = None,
        recorded_source_digest: str | None = None,
    ) -> None:
        self.python = Path(python)
        self.script = Path(script)
        self.state_dir = Path(state_dir)
        self.out_dir = Path(out_dir)
        self.seed = seed
        self.fidelity = fidelity
        self.fraction = fraction
        self.n = n
        self.runs = runs
        self.runtime_budget_ms = runtime_budget_ms
        self.timeout_s = timeout_s
        self.cwd = Path(cwd) if cwd else self.out_dir.parent / "cwd-neutral"
        self.emit_resources_dir = Path(emit_resources_dir) if emit_resources_dir else None
        self.expected_source_records = expected_source_records
        self.recorded_source_digest = recorded_source_digest
        self.calls = 0
        self.identity: EStarIdentity | None = None

        self.cwd.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    # -- identity ---------------------------------------------------------
    def verify_wiring(self) -> EStarIdentity:
        """Re-hash the evaluator source files the EID* recorded.

        This is adapter_contract.md §1.2/§1.3 in code: it is what makes `EID*`
        true rather than nominal. Raises EvaluatorWiringError (adapter exit 3) when
        a recorded file is missing or its bytes moved.
        """
        if not self.script.is_file():
            raise EvaluatorWiringError(f"E* script not found: {self.script}")
        if not self.python.is_file():
            raise EvaluatorWiringError(f"E* interpreter not found: {self.python}")

        records = list(self.expected_source_records or [])
        recomputed: dict[str, str] = {}
        verified = True
        if records:
            for record in records:
                rel = record["path"]
                path = self.script.parent / rel
                if not path.is_file():
                    raise EvaluatorWiringError(f"EID* records {rel!r} but it is missing at {path}")
                actual = sha256_file(path)
                recomputed[rel] = actual
                if actual != record["sha256"]:
                    verified = False
                    raise EvaluatorWiringError(
                        f"E* source drift: {rel} recorded {record['sha256']} actual {actual}"
                    )
        else:
            recomputed[self.script.name] = sha256_file(self.script)

        digest_out = subprocess.run(
            [str(self.python), str(self.script), "digest"],
            capture_output=True,
            text=True,
            cwd=str(self.cwd),
            env=_mini_env(self.cwd / "home"),
            timeout=120,
        )
        if digest_out.returncode != 0:
            raise EvaluatorWiringError(f"`e_star.py digest` failed: {digest_out.stderr.strip()}")
        digest_doc = json.loads(digest_out.stdout)
        version_probe = subprocess.run(
            [str(self.python), "-c", "import platform;print(platform.python_version())"],
            capture_output=True,
            text=True,
            cwd=str(self.cwd),
            env=_mini_env(self.cwd / "home"),
            timeout=60,
        )

        self.identity = EStarIdentity(
            script=self.script,
            python=self.python,
            source_records=records,
            source_sha256_recomputed=recomputed,
            source_verified=verified,
            recorded_source_digest=self.recorded_source_digest,
            evaluator_source_sha256_self_reported=digest_doc.get("evaluator_source_sha256"),
            interpreter_version=version_probe.stdout.strip(),
        )
        return self.identity

    # -- evaluation -------------------------------------------------------
    def evaluate(self, candidate, *, iteration: int, tag: str | None = None) -> EStarResult:
        cid = candidate.candidate_id
        stem = tag or f"{cid}.i{iteration}"
        out_path = self.out_dir / f"{stem}.outcome.json"
        cmd = [
            str(self.python),
            str(self.script),
            "evaluate",
            "--candidate",
            str(candidate.path),
            "--seed",
            str(self.seed),
            "--fidelity",
            self.fidelity,
            "--fraction",
            str(self.fraction),
            "--n",
            str(self.n),
            "--runs",
            str(self.runs),
            "--runtime-budget-ms",
            str(self.runtime_budget_ms),
            "--timeout-s",
            str(self.timeout_s),
            "--out",
            str(out_path),
            "--state-dir",
            str(self.state_dir),
        ]
        if self.emit_resources_dir is not None:
            self.emit_resources_dir.mkdir(parents=True, exist_ok=True)
            cmd += ["--emit-resources", str(self.emit_resources_dir / f"{stem}.resources.json")]

        started = time.monotonic()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.cwd),
            env=_mini_env(self.cwd / "home"),
            timeout=self.timeout_s + 60.0,
        )
        wall = time.monotonic() - started
        self.calls += 1

        stdout = proc.stdout or ""
        manifest_line = None
        manifest = None
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("E_STAR_MANIFEST "):
                manifest_line = line
                try:
                    manifest = json.loads(line[len("E_STAR_MANIFEST ") :])
                except json.JSONDecodeError:
                    manifest = None
        outcome = None
        if out_path.is_file():
            with out_path.open("r", encoding="utf-8") as fh:
                outcome = json.load(fh)

        status = (outcome or {}).get("status")
        if status is None:
            status = STATUS_BY_EXIT.get(proc.returncode, "error")
        failure = (outcome or {}).get("failure") or {}
        return EStarResult(
            candidate_id=cid,
            exit_code=proc.returncode,
            status=status,
            outcome=outcome,
            manifest=manifest,
            manifest_line=manifest_line,
            stdout=stdout,
            stderr=proc.stderr or "",
            wall_sec=wall,
            out_path=out_path,
            command=cmd,
            failure_kind=failure.get("kind"),
            failure_message=failure.get("message"),
            fields=((outcome or {}).get("fields") or {}),
        )


def strip_absolute_paths(value, *, roots: list[str] | None = None):
    """Rewrite any host path out of a payload before it enters a shared trace."""
    roots = roots or []
    if isinstance(value, dict):
        return {k: strip_absolute_paths(v, roots=roots) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_absolute_paths(v, roots=roots) for v in value]
    if isinstance(value, str):
        out = value
        for root in roots:
            if root and root in out:
                out = out.replace(root.rstrip("/") + "/", "").replace(root, "")
        return out
    return value


def relativize(path: Path | str, work_root: Path | None) -> str:
    """Paths in local run artifacts are reported relative to the work root.

    Traces themselves carry no paths at all (adapter_contract.md §4.4); this
    helper exists for run_meta.json / adapter.md, which stay on this machine.
    """
    resolved = Path(path).resolve()
    if work_root is not None:
        root = Path(work_root).resolve()
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            pass
    return str(resolved)
