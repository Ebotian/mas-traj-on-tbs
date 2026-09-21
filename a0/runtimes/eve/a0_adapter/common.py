"""Shared plumbing: frozen paths, theta_E, F_r, the candidate set, and the E* runner.

Nothing in this module touches the runtime; it is the *contract side* of the adapter
(a0/contract/adapter_contract.md §1, §2, §4).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ADAPTER_DIR = Path(__file__).resolve().parent.parent


def resolve_repo_root() -> Path:
    """The checkout this adapter runs from: ``$A0_REPO_ROOT`` or this file's location.

    ``ADAPTER_DIR`` is ``<repo>/a0/runtimes/eve``; walking two levels up from it was
    already location-derived, but an explicit override keeps the resolution honest when
    the tree is copied or relocated.
    """

    override = os.environ.get("A0_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return ADAPTER_DIR.parent.parent.parent  # a0/runtimes/eve -> a0 -> <repo>


REPO_ROOT = resolve_repo_root()  # rsi-dev/
A0_ROOT = REPO_ROOT / "a0"

CONTRACT_DIR = A0_ROOT / "contract"
TASK_DIR = A0_ROOT / "tasks" / "circle-packing"
E_STAR_SCRIPT = TASK_DIR / "e_star.py"
E_STAR_PYTHON = TASK_DIR / ".venv" / "bin" / "python"
E_STAR_TABLE = TASK_DIR / "E_STAR.json"
DEFAULT_CANDIDATE_SET = TASK_DIR / "C_STAR" / "manifest.json"
DEFAULT_EID = CONTRACT_DIR / "out" / "plumbing.EID.json"
DEFAULT_SPEC = CONTRACT_DIR / "plumbing.contract.json"
DEFAULT_FR = CONTRACT_DIR / "fr" / "scalar.json"

# Binding decision 2: the frozen theta_E. `fidelity=full`, `fraction=1.0`; the seed is an
# evaluator input that full-fidelity evaluation does not consume (e_star.py docstring).
FROZEN_THETA = {
    "seed": 1337,
    "fidelity": "full",
    "fraction": 1.0,
    "n": 26,
    "runs": 5,
    "runtime_budget_ms": 250.0,
    "timeout_s": 120.0,
}

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONTRACT = 3
EXIT_CANDIDATE_SET = 4
EXIT_A01_FAILURE = 5
EXIT_CLOSURE = 6
EXIT_BUDGET = 7
EXIT_NO_CANDIDATE = 8
EXIT_INTERNAL = 10

# The declared mapping EvE adapter -> EID* lives in a0_adapter/eidmap.py (EID_R_DECLARATION),
# next to the derivation it describes: EID_r.value is a hash whose payload carries `eid_star`
# as an argument, not the sha256 of an adapter-generated artefact.


def canonical_file_digest(path: Path) -> str:
    """sha256 of a JSON document's canonical form (evalcontract.canonical_file_digest)."""
    spec = _load_evalcontract()
    return spec.canonical_file_digest(path)


def _load_evalcontract():
    if "_a0_evalcontract" in sys.modules:
        return sys.modules["_a0_evalcontract"]
    path = CONTRACT_DIR / "evalcontract.py"
    spec = importlib.util.spec_from_file_location("_a0_evalcontract", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_a0_evalcontract"] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------------------
# theta_E
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Theta:
    seed: int | None
    fidelity: str | None
    fraction: float | None
    n: int
    runs: int
    timeout_s: float
    runtime_budget_ms: float
    defaults_applied: dict[str, dict[str, Any]]
    source: str

    def trace_payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "seed": self.seed,
            "fidelity": self.fidelity,
            "fraction": self.fraction,
            "defaults_applied": dict(self.defaults_applied),
        }
        merged = {
            "source": self.source,
            "n": self.n,
            "runs": self.runs,
            "runtime_budget_ms": self.runtime_budget_ms,
            "timeout_s": self.timeout_s,
        }
        if extra:
            merged.update(extra)
        payload["extra"] = merged
        return payload

    def declaration_payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """The flat, harness-readable declaration (a0/conformance frozen shape).

        The conformance runner requires every frozen parameter to be visible either at the
        top level or under ``extra``; it also tolerates the nested form used on the traces.
        This emits both, so a reader never has to reconstruct theta_E from E*'s manifest
        echoes.
        """
        payload: dict[str, Any] = {
            "seed": self.seed,
            "fidelity": self.fidelity,
            "fraction": self.fraction,
            "n": self.n,
            "runs": self.runs,
            "runtime_budget_ms": self.runtime_budget_ms,
            "timeout_s": self.timeout_s,
            "defaults_applied": dict(self.defaults_applied),
        }
        merged: dict[str, Any] = {"source": self.source}
        if extra:
            merged.update(extra)
        payload["extra"] = merged
        return payload


def parse_theta(text: str) -> Theta:
    """Parse ``--theta seed=1337,fidelity=full,fraction=1.0``.

    A parameter EvE cannot receive must be passed as ``none`` and is then recorded in
    ``defaults_applied`` with the fixed equivalent actually used (adapter_contract.md §3).
    EvE injects no seed into the evaluation step (the step's environment is exactly
    EVE_WORKSPACE_ROOT/EVE_SOLVER_ROOT/EVE_EVAL_LOG_ROOT/PYTHONDONTWRITEBYTECODE,
    workflow/evaluation.py:290-318), so ``seed=none`` is the honest EvE value.
    """
    raw: dict[str, str] = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"--theta item {item!r} is not key=value")
        key, value = item.split("=", 1)
        raw[key.strip()] = value.strip()

    def as_none(value: str) -> bool:
        return value.lower() in {"none", "null", ""}

    defaults: dict[str, dict[str, Any]] = {}
    if "seed" in raw and as_none(raw["seed"]):
        seed = None
        defaults["seed"] = {
            "value": FROZEN_THETA["seed"],
            "source": (
                "EvE passes no seed to the evaluation step; the fixed equivalent used is the "
                "frozen E* theta_E.seed=1337, which full-fidelity evaluation does not consume "
                "(e_star.py: '--fidelity full audits every item, so the seed is inert there')"
            ),
        }
    else:
        seed = int(raw["seed"]) if "seed" in raw else FROZEN_THETA["seed"]

    fidelity = raw.get("fidelity", FROZEN_THETA["fidelity"])
    fraction = raw.get("fraction", FROZEN_THETA["fraction"])
    theta = Theta(
        seed=seed,
        fidelity=None if as_none(str(fidelity)) else str(fidelity),
        fraction=None if as_none(str(fraction)) else float(fraction),
        n=int(raw.get("n", FROZEN_THETA["n"])),
        runs=int(raw.get("runs", FROZEN_THETA["runs"])),
        timeout_s=float(raw.get("timeout_s", FROZEN_THETA["timeout_s"])),
        runtime_budget_ms=float(
            raw.get("runtime_budget_ms", FROZEN_THETA["runtime_budget_ms"])
        ),
        defaults_applied=defaults,
        source="adapter CLI --theta",
    )
    if theta.fidelity != FROZEN_THETA["fidelity"] or theta.fraction != FROZEN_THETA["fraction"]:
        raise ValueError(
            "theta_E must stay at the frozen values "
            f"fidelity={FROZEN_THETA['fidelity']} fraction={FROZEN_THETA['fraction']}; "
            f"got fidelity={theta.fidelity} fraction={theta.fraction}"
        )
    if theta.seed is not None and theta.seed != FROZEN_THETA["seed"]:
        raise ValueError(f"theta_E.seed must be {FROZEN_THETA['seed']}; got {theta.seed}")
    return theta


# --------------------------------------------------------------------------------------
# F_r
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Fr:
    name: str
    version: str
    applies: str
    primary_field: str
    direction: str
    spec_hash: str
    declared_in: str

    def trace_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "applies": self.applies,
            "spec_hash": self.spec_hash,
            "declared_in": self.declared_in,
        }

    def scalar(self, outcome_fields: dict[str, Any]) -> float | None:
        value = outcome_fields.get(self.primary_field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None


def load_fr(path: Path) -> Fr:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return Fr(
        name=doc["name"],
        version=doc["version"],
        applies=doc["applies"],
        primary_field=doc["primary_field"],
        direction=doc.get("direction", "maximize"),
        spec_hash=canonical_file_digest(Path(path)),
        declared_in=doc.get("declared_in", "a0/contract/fr/scalar.json"),
    )


# --------------------------------------------------------------------------------------
# Candidate set C*
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    path: Path
    solution_sha256: str
    role: str
    note: str


def load_candidates(manifest_path: Path) -> list[Candidate]:
    """Load and integrity-check C*. Raises CandidateSetError on any problem (exit 4)."""
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise CandidateSetError(f"candidate set manifest not found: {manifest_path}")
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise CandidateSetError(f"candidate set manifest is not valid JSON: {exc!r}") from exc
    if doc.get("schema") != "a0.candidateset/v1":
        raise CandidateSetError(f"unexpected candidate-set schema: {doc.get('schema')!r}")
    entries = doc.get("candidates")
    if not isinstance(entries, list) or not entries:
        raise CandidateSetError("candidate set has no candidates")

    base = manifest_path.parent
    candidates: list[Candidate] = []
    seen: set[str] = set()
    for raw in entries:
        cid = raw.get("candidate_id")
        if not isinstance(cid, str) or not cid:
            raise CandidateSetError(f"candidate entry without candidate_id: {raw!r}")
        if cid in seen:
            raise CandidateSetError(f"duplicate candidate_id {cid!r}")
        seen.add(cid)
        rel = raw.get("path")
        if not isinstance(rel, str) or not rel:
            raise CandidateSetError(f"candidate {cid} has no path")
        cdir = (base / rel).resolve()
        solution = cdir / "solution.py"
        if not solution.is_file():
            raise CandidateSetError(f"candidate {cid}: {solution} is missing")
        expected = raw.get("solution_sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            raise CandidateSetError(f"candidate {cid} has no solution_sha256")
        actual = sha256_file(solution)
        if actual != expected:
            raise CandidateSetError(
                f"candidate {cid}: solution.py sha256 mismatch "
                f"(manifest {expected}, on disk {actual})"
            )
        candidates.append(
            Candidate(
                candidate_id=cid,
                path=cdir,
                solution_sha256=actual,
                role=str(raw.get("role", "")),
                note=str(raw.get("note", "")),
            )
        )
    return candidates


class CandidateSetError(RuntimeError):
    pass


def read_eid(eid_path: Path) -> dict[str, Any]:
    doc = json.loads(Path(eid_path).read_text(encoding="utf-8"))
    eid = doc.get("eid_star")
    if not isinstance(eid, str) or len(eid) != 64:
        raise ValueError(f"{eid_path} has no 64-hex eid_star")
    return doc


def verify_eid(eid_path: Path, spec_path: Path, timeout_s: float = 300.0) -> tuple[int, str]:
    """Run the contract's own verifier. Non-zero exit means the adapter must abort (exit 3)."""
    cmd = [
        str(CONTRACT_DIR / ".venv" / "bin" / "python"),
        str(CONTRACT_DIR / "evalcontract.py"),
        "verify",
        "--eid-file",
        str(eid_path),
        "--spec",
        str(spec_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def recompute_eid(eid_path: Path, timeout_s: float = 300.0) -> tuple[int, str]:
    cmd = [
        str(CONTRACT_DIR / ".venv" / "bin" / "python"),
        str(CONTRACT_DIR / "evalcontract.py"),
        "recompute",
        "--eid-file",
        str(eid_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# --------------------------------------------------------------------------------------
# E* runner (the reference side; never inside a runtime)
# --------------------------------------------------------------------------------------


@dataclass
class EStarResult:
    candidate_id: str
    rc: int
    elapsed_s: float
    outcome: dict[str, Any] | None
    outcome_path: Path | None
    resources_path: Path | None
    stdout: str
    stderr: str
    status: str | None
    fields: dict[str, Any]
    scalar: float | None

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "rc": self.rc,
            "elapsed_s": self.elapsed_s,
            "status": self.status,
            "fields": self.fields,
            "scalar": self.scalar,
            "outcome_path": None if self.outcome_path is None else str(self.outcome_path),
            "stdout_tail": self.stdout[-2000:],
            "stderr_tail": self.stderr[-2000:],
        }


def run_e_star(
    candidate_dir: Path,
    *,
    candidate_id: str,
    theta: Theta,
    out_path: Path,
    state_dir: Path,
    emit_resources: bool = False,
    timeout_s: float | None = None,
) -> EStarResult:
    """Invoke the frozen E* exactly as the binding decision specifies (decision 2).

    Every path handed to E* is absolute: E* resolves its own state root against its *child's*
    cwd, and a relative ``--state-dir`` makes every candidate fail with
    ``status=error, failure.kind=child_terminated_early`` (reproduced 2026-09-20, see
    README.md "cross-workstream note").
    """
    out_path = Path(out_path).resolve()
    state_dir = Path(state_dir).resolve()
    candidate_dir = Path(candidate_dir).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    resources = out_path.with_suffix(".resources.json")
    cmd = [
        str(E_STAR_PYTHON),
        str(E_STAR_SCRIPT),
        "evaluate",
        "--candidate",
        str(candidate_dir),
        "--seed",
        str(FROZEN_THETA["seed"] if theta.seed is None else theta.seed),
        "--fidelity",
        str(theta.fidelity),
        "--fraction",
        str(theta.fraction),
        "--n",
        str(theta.n),
        "--runs",
        str(theta.runs),
        "--runtime-budget-ms",
        str(theta.runtime_budget_ms),
        "--timeout-s",
        str(theta.timeout_s),
        "--out",
        str(out_path),
        "--state-dir",
        str(state_dir),
    ]
    if emit_resources:
        cmd += ["--emit-resources", str(resources)]
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s or (theta.timeout_s + 120.0),
        cwd=str(ADAPTER_DIR),
    )
    elapsed = time.monotonic() - started
    outcome = None
    if out_path.is_file():
        try:
            outcome = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            outcome = None
    fields = {} if outcome is None else (outcome.get("fields") or {})
    status = None if outcome is None else outcome.get("status")
    value = fields.get("sum_radii")
    scalar = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return EStarResult(
        candidate_id=candidate_id,
        rc=proc.returncode,
        elapsed_s=elapsed,
        outcome=outcome,
        outcome_path=out_path if out_path.is_file() else None,
        resources_path=resources if resources.is_file() else None,
        stdout=proc.stdout,
        stderr=proc.stderr,
        status=status,
        fields=fields,
        scalar=scalar,
    )


def strip_absolute(value: Any) -> Any:
    """Replace absolute host paths in a payload with ``<abs>/basename`` (adapter_contract §4.4).

    Recursively rewrites every string that starts with ``/``; the trace is a shared artifact
    and must not leak host layout.
    """
    if isinstance(value, dict):
        return {key: strip_absolute(item) for key, item in value.items()}
    if isinstance(value, list):
        return [strip_absolute(item) for item in value]
    if isinstance(value, str) and value.startswith("/"):
        return "<abs>/" + value.rstrip("/").rsplit("/", 1)[-1]
    return value


def parse_kv_list(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in (text or "").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"{item!r} is not key=value")
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def env_without_bytecode() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
