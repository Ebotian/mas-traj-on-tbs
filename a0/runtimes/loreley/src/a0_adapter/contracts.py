"""Frozen contract artefacts: ``EID*``, ``C*``, ``theta_E`` and ``F_r``."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

A0_ROOT = Path("/home/ebt/rsi-dev/a0")

# Exit codes, adapter_contract.md §3.1.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONTRACT = 3
EXIT_INTEGRITY = 4
EXIT_CONFORMANCE = 5
EXIT_CLOSURE = 6
EXIT_BUDGET = 7
EXIT_NO_CANDIDATE = 8
EXIT_INTERNAL = 10


class AdapterError(RuntimeError):
    """An error carrying the adapter exit code the CLI must return."""

    def __init__(self, message: str, code: int = EXIT_INTERNAL) -> None:
        super().__init__(message)
        self.code = code


class UsageError(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=EXIT_USAGE)


class ContractError(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=EXIT_CONTRACT)


class IntegrityError(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=EXIT_INTEGRITY)


# --------------------------------------------------------------------------
# theta_E
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThetaE:
    """``theta_E = (seed, fidelity, fraction, ...)`` (plan:518)."""

    seed: int | None
    fidelity: str | None
    fraction: float | None
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: str) -> "ThetaE":
        values: dict[str, Any] = {}
        for item in (raw or "").split(","):
            item = item.strip()
            if not item:
                continue
            if "=" not in item:
                raise UsageError(f"--theta entry {item!r} is not key=value")
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.lower() in {"none", "null", ""}:
                values[key] = None
            else:
                values[key] = value

        def _int(name: str) -> int | None:
            value = values.get(name)
            if value is None:
                return None
            try:
                return int(value)
            except ValueError as exc:
                raise UsageError(f"--theta {name}={value!r} is not an integer") from exc

        def _float(name: str) -> float | None:
            value = values.get(name)
            if value is None:
                return None
            try:
                return float(value)
            except ValueError as exc:
                raise UsageError(f"--theta {name}={value!r} is not a number") from exc

        fidelity = values.get("fidelity")
        known = {"seed", "fidelity", "fraction"}
        extra = {key: value for key, value in values.items() if key not in known}
        return cls(
            seed=_int("seed"),
            fidelity=str(fidelity) if fidelity is not None else None,
            fraction=_float("fraction"),
            extra=extra,
        )

    def for_e_star(self) -> tuple[int, str, float]:
        """The values E* must actually be invoked with.

        Loreley's ``EvaluationContext`` has no seed field (``plan:530``:
        "Loreley 的 ``EvaluationContext`` 无 seed 字段"), so a ``null`` seed here
        is not an error: the adapter pins E*'s own default and records the
        substitution in ``theta_E.defaults_applied``.
        """

        seed = 1337 if self.seed is None else int(self.seed)
        fidelity = str(self.fidelity or "full")
        fraction = 1.0 if fidelity == "full" else (
            float(self.fraction) if self.fraction is not None else 0.15
        )
        return seed, fidelity, fraction

    def typed_extra(self) -> dict[str, Any]:
        """``extra`` with each value coerced to the JSON type it looks like.

        The harness passes ``--theta seed=1337,...,n=26,runs=5,runtime_budget_ms=250.0``
        on one command line, so every extra arrives as a string.  Emitting ``"26"``
        where the frozen theta says the integer ``26`` would fail the runner's
        equality check on a type difference, so the coercion happens here, once.
        """

        typed: dict[str, Any] = {}
        for key, value in (self.extra or {}).items():
            typed[key] = _coerce_scalar(value)
        return typed

    def as_trace(self) -> dict[str, Any]:
        defaults: dict[str, Any] = {}
        seed, fidelity, fraction = self.for_e_star()
        if self.seed is None:
            defaults["seed"] = {
                "value": seed,
                "source": (
                    "Loreley's EvaluationContext carries no seed field "
                    "(loreley/core/worker/evaluator.py:376-395); the adapter pins E*'s "
                    "documented default seed=1337 and records it here (plan:518)."
                ),
            }
        if self.fidelity is None:
            defaults["fidelity"] = {
                "value": fidelity,
                "source": "no fidelity in theta_E; E*'s full-fidelity default is used",
            }
        if self.fraction is None and fidelity != "full":
            defaults["fraction"] = {
                "value": fraction,
                "source": "fraction is forced to 1.0 at fidelity=full (EID* Config)",
            }
        return {
            "seed": self.seed,
            "fidelity": self.fidelity,
            "fraction": self.fraction,
            "defaults_applied": defaults,
            "extra": dict(self.extra or {}),
        }


# --------------------------------------------------------------------------
# The frozen EvalContract document
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvalContract:
    path: Path
    eid_star: str
    document: Mapping[str, Any]

    @property
    def epsilon(self) -> float:
        config = self.document.get("components", {}).get("Config", {})
        value = (config.get("declared", {}).get("value") or {}).get("conformance", {})
        epsilon = (value.get("epsilon") or {}).get("value")
        if isinstance(epsilon, (int, float)):
            return float(epsilon)
        return 1e-9

    @property
    def primary_field(self) -> str:
        metric = self.document.get("components", {}).get("MetricDefinition", {})
        value = metric.get("declared", {}).get("value") or {}
        name = value.get("name")
        return str(name) if name else "sum_radii"

    @property
    def base_declared(self) -> str:
        return str(self.document.get("base_declared") or ".")

    def verify(self) -> str:
        """Run ``evalcontract.py verify`` and return its stdout.

        A drift report means the document no longer describes the evaluator on
        disk, which is exactly the contract mismatch exit code 3 exists for.
        """

        script = A0_ROOT / "contract" / "evalcontract.py"
        interpreter = A0_ROOT / "contract" / ".venv" / "bin" / "python"
        if not interpreter.is_file():
            interpreter = Path(sys.executable)
        completed = subprocess.run(
            [
                str(interpreter),
                str(script),
                "verify",
                "--eid-file",
                str(self.path),
                "--base",
                str(A0_ROOT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ContractError(
                "evalcontract.py verify reported drift / failed "
                f"(exit={completed.returncode}): {completed.stdout.strip()[:600]}"
            )
        return completed.stdout.strip()


def load_eval_contract(path: Path, *, verify: bool = True) -> EvalContract:
    if not path.is_file():
        raise UsageError(f"--eid file {path!s} does not exist")
    document = json.loads(path.read_text(encoding="utf-8"))
    eid_star = str(document.get("eid_star") or "")
    if len(eid_star) != 64 or any(ch not in "0123456789abcdef" for ch in eid_star):
        raise ContractError(f"{path!s} does not carry a 64-hex eid_star")
    contract = EvalContract(path=path.resolve(), eid_star=eid_star, document=document)
    if verify:
        contract.verify()
    return contract


# --------------------------------------------------------------------------
# C*
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    path: Path
    solution_sha256: str
    role: str
    kind: str
    note: str

    def verify_integrity(self) -> str:
        solution = self.path / "solution.py"
        if not solution.is_file():
            raise IntegrityError(f"candidate {self.candidate_id!r}: {solution!s} is missing")
        digest = hashlib.sha256(solution.read_bytes()).hexdigest()
        if digest != self.solution_sha256:
            raise IntegrityError(
                f"candidate {self.candidate_id!r}: solution.py sha256 {digest} does not match "
                f"the manifest value {self.solution_sha256}"
            )
        return digest


@dataclass(frozen=True, slots=True)
class CandidateSet:
    manifest_path: Path
    candidate_set_id: str
    candidates: tuple[Candidate, ...]

    def by_id(self, candidate_id: str) -> Candidate:
        for candidate in self.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise UsageError(f"candidate {candidate_id!r} is not a member of C*")


def load_candidate_set(path: Path, *, verify_integrity: bool = True) -> CandidateSet:
    if not path.is_file():
        raise UsageError(f"--candidate-set {path!s} does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise IntegrityError(f"{path!s} carries no candidates list")
    root = path.parent
    candidates: list[Candidate] = []
    for item in raw:
        try:
            candidate = Candidate(
                candidate_id=str(item["candidate_id"]),
                path=(root / str(item.get("path") or item["candidate_id"])).resolve(),
                solution_sha256=str(item["solution_sha256"]),
                role=str(item.get("role") or ""),
                kind=str(item.get("kind") or ""),
                note=str(item.get("note") or ""),
            )
        except KeyError as exc:
            raise IntegrityError(f"{path!s}: candidate entry missing {exc}") from exc
        if verify_integrity:
            candidate.verify_integrity()
        candidates.append(candidate)
    declared = payload.get("candidate_count")
    if isinstance(declared, int) and declared != len(candidates):
        raise IntegrityError(
            f"{path!s}: candidate_count={declared} but {len(candidates)} entries are listed"
        )
    return CandidateSet(
        manifest_path=path.resolve(),
        candidate_set_id=str(payload.get("candidate_set_id") or "C*"),
        candidates=tuple(candidates),
    )


# --------------------------------------------------------------------------
# F_r
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrDeclaration:
    path: Path
    document: Mapping[str, Any]
    spec_hash: str

    @property
    def name(self) -> str:
        return str(self.document.get("name") or "F_r")

    @property
    def version(self) -> str:
        return str(self.document.get("version") or "v1")

    @property
    def applies(self) -> str:
        return str(self.document.get("applies") or "scalar")

    def as_trace(self, declared_in: str) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "applies": self.applies,
            "spec_hash": self.spec_hash,
            "declared_in": declared_in,
        }


def _coerce_scalar(value: Any) -> Any:
    """Turn ``"26"`` into ``26`` and ``"250.0"`` into ``250.0``; leave anything else alone."""

    if not isinstance(value, str):
        return value
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return value


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_file_digest(path: Path) -> str:
    """``sha256(canonical_json(json.load(path)))`` - the contract's fr.spec_hash rule."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def load_fr(path: Path) -> FrDeclaration:
    if not path.is_file():
        raise UsageError(f"--fr {path!s} does not exist")
    document = json.loads(path.read_text(encoding="utf-8"))
    return FrDeclaration(path=path.resolve(), document=document,
                         spec_hash=canonical_file_digest(path))


def required_metric_names(document: Mapping[str, Any]) -> Sequence[str]:
    metric = document.get("components", {}).get("MetricDefinition", {})
    value = metric.get("declared", {}).get("value") or {}
    fields = value.get("outcome_fields")
    if isinstance(fields, list) and fields:
        return tuple(str(item) for item in fields)
    return (str(value.get("name") or "sum_radii"),)
