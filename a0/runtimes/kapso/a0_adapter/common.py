"""Shared plumbing for the A0 KAPSO adapter.

Everything a third party needs to re-derive this adapter's claims lives here:
path resolution, the mandatory pre-run ``EID*`` checks, ``C*`` loading with
integrity enforcement, the ``EID_r -> EID*`` mapping record, and the trace
writer/validator.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Exit codes from a0/contract/adapter_contract.md section 3.1.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EID = 3
EXIT_CANDIDATE = 4
EXIT_CONFORMANCE = 5
EXIT_CLOSURE = 6
EXIT_BUDGET = 7
EXIT_NO_CANDIDATE = 8
EXIT_INTERNAL = 10


class AdapterError(RuntimeError):
    def __init__(self, message: str, code: int = EXIT_INTERNAL):
        super().__init__(message)
        self.code = code


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def write_json(path: Path, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# adapter configuration
# --------------------------------------------------------------------------- #

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "adapter.json"


@dataclass
class AdapterConfig:
    a0_root: Path
    e_star_dir: Path
    e_star_python: Path
    kapso_src: Path
    candidate_set: Path
    eid_star_file: Path
    evalcontract: Path
    trace_validate: Path
    fr_spec: Path
    mode_config: Path
    state_root: Path
    registered_tree: Path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AdapterConfig":
        raw = json.loads(Path(path or DEFAULT_CONFIG_PATH).read_text("utf-8"))
        return cls(
            a0_root=Path(raw["a0_root"]),
            e_star_dir=Path(raw["e_star_dir"]),
            e_star_python=Path(raw["e_star_python"]),
            kapso_src=Path(raw["kapso_src"]),
            candidate_set=Path(raw["candidate_set"]),
            eid_star_file=Path(raw["eid_star_file"]),
            evalcontract=Path(raw["evalcontract"]),
            trace_validate=Path(raw["trace_validate"]),
            fr_spec=Path(raw["fr_spec"]),
            mode_config=Path(raw["mode_config"]),
            state_root=Path(raw["state_root"]),
            registered_tree=Path(raw["registered_tree"]),
        )

    def kapso_pythonpath(self) -> str:
        return str(self.kapso_src)


# --------------------------------------------------------------------------- #
# EID* : loading, verification, mapping
# --------------------------------------------------------------------------- #

@dataclass
class EidStar:
    document: Dict[str, Any]
    path: Path

    @property
    def eid_star(self) -> str:
        return self.document["eid_star"]

    @property
    def components(self) -> Dict[str, Any]:
        return self.document["components"]

    def component_digest(self, name: str) -> str:
        return self.components[name]["digest"]

    @property
    def epsilon(self) -> float:
        return float(
            self.components["Config"]["value"]["conformance"]["epsilon"]["value"]
        )

    @property
    def canonical_theta(self) -> Dict[str, Any]:
        return self.components["Config"]["value"]["theta_e_canonical"]

    @property
    def primary_field(self) -> str:
        return self.components["MetricDefinition"]["metric_name"]

    def evaluator_source_records(self) -> List[Dict[str, Any]]:
        return self.components["EvaluatorSource"]["records"]

    def data_manifest_records(self) -> List[Dict[str, Any]]:
        return self.components["DataManifest"].get("records", [])


def load_eid_star(path: Path) -> EidStar:
    document = json.loads(Path(path).read_text("utf-8"))
    for key in ("eid_star", "components", "spec"):
        if key not in document:
            raise AdapterError(f"{path} is not an EID* document: missing {key}",
                               EXIT_EID)
    return EidStar(document=document, path=Path(path))


def verify_eid_star(config: AdapterConfig, eid: EidStar) -> Dict[str, Any]:
    """Run the contract's own `verify` (drift) and `recompute` (derivation).

    Both are executed as subprocesses so the recorded output is the contract
    tool's, not this adapter's re-implementation.
    """
    spec = eid.document.get("spec")
    base = eid.document.get("base_declared")
    spec_relative = eid.document.get("spec")
    spec_path = None
    for candidate_path in (
        config.a0_root / spec_relative if spec_relative else None,
        eid.path.parent / spec_relative if spec_relative else None,
    ):
        if candidate_path and candidate_path.is_file():
            spec_path = candidate_path
            break
    verify_cmd = [
        sys.executable, str(config.evalcontract), "verify",
        "--eid-file", str(eid.path),
    ]
    if spec_path is not None:
        verify_cmd += ["--spec", str(spec_path)]
    if base and spec_path is not None:
        base_path = (spec_path.parent / base).resolve()
        verify_cmd += ["--base", str(base_path)]
    verify = subprocess.run(verify_cmd, capture_output=True, text=True)
    recompute_cmd = [
        sys.executable, str(config.evalcontract), "recompute",
        "--eid-file", str(eid.path),
    ]
    recompute = subprocess.run(recompute_cmd, capture_output=True, text=True)
    report = {
        "verify": {
            "cmd": " ".join(verify_cmd[1:]),
            "returncode": verify.returncode,
            "stdout": verify.stdout.strip(),
            "stderr": verify.stderr.strip(),
        },
        "recompute": {
            "cmd": " ".join(recompute_cmd[1:]),
            "returncode": recompute.returncode,
            "stdout": recompute.stdout.strip(),
            "stderr": recompute.stderr.strip(),
        },
    }
    if verify.returncode != 0 or recompute.returncode != 0:
        raise AdapterError(
            "EID* verification failed: " + json.dumps(report), EXIT_EID
        )
    return report


# --------------------------------------------------------------------------- #
# C* : the frozen candidate set
# --------------------------------------------------------------------------- #

@dataclass
class Candidate:
    candidate_id: str
    path: Path
    solution_sha256: str
    role: str
    raw: Dict[str, Any] = field(default_factory=dict)


def load_candidate_set(manifest_path: Path) -> List[Candidate]:
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise AdapterError(f"candidate set manifest not found: {manifest_path}",
                           EXIT_USAGE)
    manifest = json.loads(manifest_path.read_text("utf-8"))
    if manifest.get("schema") != "a0.candidateset/v1":
        raise AdapterError(
            f"unexpected candidate-set schema {manifest.get('schema')!r}",
            EXIT_USAGE,
        )
    candidates: List[Candidate] = []
    for entry in manifest["candidates"]:
        path = (manifest_path.parent / entry["path"]).resolve()
        candidates.append(
            Candidate(
                candidate_id=entry["candidate_id"],
                path=path,
                solution_sha256=entry["solution_sha256"],
                role=entry.get("role", ""),
                raw=entry,
            )
        )
    return candidates


def check_candidate_integrity(candidates: List[Candidate]) -> None:
    """Recompute sha256(solution.py) before any evaluation (contract section 2)."""
    problems = []
    for candidate in candidates:
        solution = candidate.path / "solution.py"
        if not solution.is_file():
            problems.append(f"{candidate.candidate_id}: missing {solution}")
            continue
        digest = sha256_file(solution)
        if digest != candidate.solution_sha256:
            problems.append(
                f"{candidate.candidate_id}: solution.py sha256 {digest} != "
                f"manifest {candidate.solution_sha256}"
            )
    if problems:
        raise AdapterError("candidate integrity failure: " + "; ".join(problems),
                           EXIT_CANDIDATE)


# --------------------------------------------------------------------------- #
# theta_E
# --------------------------------------------------------------------------- #

def e_star_identity(config: AdapterConfig) -> Dict[str, Any]:
    """E*'s own identity material, asked of E* itself (`e_star.py digest`).

    The `theta_E.extra` block of a trace must name *the evaluator* when it
    carries a source digest, and there are two different digests in play in this
    adapter:

    * `kapso_eval.py` — the adapter's registered **wrapper**, i.e. the input to
      `EID_r` (recorded as `registered_wrapper_sha256`);
    * E*'s own evaluator source digest — the value E* prints in its own manifest
      line and in every Outcome (`e_star_evaluator_source_sha256`).

    Conflating them makes a run look like evaluator drift when only the wrapper
    changed (audit finding F1).  This helper obtains the second one from E*'s
    `digest` subcommand rather than recomputing E*'s algorithm here, and returns
    the command and exit code so the value is reproducible.  On failure it
    returns `pass: false` and no digest: an identity is never guessed.
    """
    command = [str(config.e_star_python), str(config.e_star_dir / "e_star.py"),
               "digest"]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=120,
            cwd=str(config.e_star_dir),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"pass": False, "cmd": " ".join(command), "returncode": None,
                "error": f"{type(exc).__name__}: {exc}"}
    payload: Dict[str, Any] = {
        "pass": completed.returncode == 0,
        "cmd": " ".join(command),
        "returncode": completed.returncode,
        "stderr_tail": completed.stderr.strip()[-400:],
    }
    if completed.returncode != 0:
        payload["error"] = "E* `digest` returned non-zero"
        return payload
    material = json.loads(completed.stdout)
    payload.update({
        "e_star_evaluator_source_sha256": material["evaluator_source_sha256"],
        "e_star_version": material.get("e_star_version"),
        "source_files": material.get("source_files"),
    })
    return payload


@dataclass
class ThetaE:
    seed: int
    fidelity: str
    fraction: float
    defaults_applied: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, text: str) -> "ThetaE":
        parts: Dict[str, str] = {}
        for item in text.split(","):
            if not item.strip():
                continue
            if "=" not in item:
                raise AdapterError(f"--theta item {item!r} is not k=v",
                                   EXIT_USAGE)
            key, value = item.split("=", 1)
            parts[key.strip()] = value.strip()
        if parts.get("seed") in (None, "none", "null"):
            seed = None
        else:
            seed = int(parts["seed"])
        fidelity = parts.get("fidelity")
        if fidelity in ("none", "null", ""):
            fidelity = None
        fraction = parts.get("fraction")
        fraction = None if fraction in (None, "none", "null", "") else float(fraction)
        defaults: Dict[str, Any] = {}
        if seed is None:
            defaults["seed"] = {
                "value": "evaluator-internal-unseeded",
                "source": "KAPSO receives no seed",
            }
        if fidelity is None:
            defaults["fidelity"] = {
                "value": "full",
                "source": "KAPSO's registered class under budget.fidelity.mode=off "
                          "is full (fidelity.py:318-324 FULL_PASSTHROUGH)",
            }
        if fraction is None:
            defaults["fraction"] = {
                "value": 1.0,
                "source": "KAPSO's registered class under budget.fidelity.mode=off "
                          "is fraction 1.0 (fidelity.py:318-324)",
            }
        return cls(seed=seed, fidelity=fidelity, fraction=fraction,
                   defaults_applied=defaults)

    def payload(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "fidelity": self.fidelity,
            "fraction": self.fraction,
            "defaults_applied": self.defaults_applied,
            "extra": dict(extra or self.extra),
        }


# --------------------------------------------------------------------------- #
# EID_r  (native scheme) + mapping declaration
# --------------------------------------------------------------------------- #

def eid_r_payload(eid_star: str, fingerprint: str, declaration: str) -> Dict[str, Any]:
    return {
        "value": f"manifest:{fingerprint}",
        "native_scheme": "manifest_fingerprint",
        "mapping_mode": "native",
        "derives_from_eid_star": eid_star,
        "declaration": declaration,
        "recomputable": True,
    }


# --------------------------------------------------------------------------- #
# the A0-wide frozen tables (adapter_contract.md section 5.3)
# --------------------------------------------------------------------------- #

ADAPTER_ROOT = Path(__file__).resolve().parent.parent

#: KAPSO's own `contract/selection/kapso.selection.json`.  The `scalarization`
#: and `failure_stage_mapping` blocks in it are copied verbatim from the frozen
#: A0-wide declaration `a0/contract/selection/simpleloop.selection.json`, so
#: that the per-runtime FailureStage counts (plan:577, plan:628) are joinable.
SELECTION_DECLARATION = ADAPTER_ROOT / "contract" / "selection" / "kapso.selection.json"

#: `E*` verdict -> `failure_stage`, identical in all four runtimes.
FAILURE_STAGE_MAPPING: Dict[str, str] = {
    "exit_0_ok": "none",
    "exit_2_invalid": "verify_failed",
    "exit_3_error_candidate_import_failed": "resolve_failed",
    "exit_3_error_non_deterministic": "verify_failed",
    "exit_3_error_runtime_budget_exceeded": "timeout",
    "exit_3_error_candidate_call_raised": "evaluator_failed",
    "exit_3_error_child_terminated_early": "evaluator_failed",
    "exit_3_error_other": "evaluator_failed",
    "solver_lane_produced_no_proposal": "search_failed",
}

#: The trace schema's `failure_stage` enum (trace_validate.py:FAILURE_STAGES).
FAILURE_STAGE_ENUM = (
    "none", "evaluator_failed", "search_failed", "resolve_failed",
    "verify_failed", "comprehension_failed", "mechanism_mismatch",
    "injection_failed", "used_not_improved", "timeout", "boundary_violation",
    "budget_exhausted",
)


def failure_stage(status: Optional[str], exit_code: Optional[int],
                  failure_kind: Optional[str]) -> str:
    """The shared `E*` verdict -> `failure_stage` mapping.

    Keyed on the same three things the trace carries: the verdict, the exit
    code (`2` = invalid, `3` = error) and the failure kind.  An `exit 3` kind
    the table does not name (a future E* failure mode) maps to
    `evaluator_failed`, the table's "other" row -- never to `none`.
    """
    if (status or "").strip() == "ok":
        return FAILURE_STAGE_MAPPING["exit_0_ok"]
    if exit_code == 2:
        return FAILURE_STAGE_MAPPING["exit_2_invalid"]
    key = f"exit_3_error_{(failure_kind or '').strip()}"
    return FAILURE_STAGE_MAPPING.get(key, FAILURE_STAGE_MAPPING["exit_3_error_other"])


def selection_payload(config: "AdapterConfig") -> Dict[str, Any]:
    """KAPSO's selection declaration + proof it carries the shared blocks.

    Read at run time and compared (a) block-by-block with the frozen A0-wide
    declaration and (b) whole-document with the contract owner's canonical copy
    at `a0/contract/selection/kapso.selection.json`, so neither the shared tables
    nor the runtime-side declaration can drift silently.
    """
    declared = json.loads(SELECTION_DECLARATION.read_text("utf-8"))
    canonical = _canonical(declared)
    frozen_path = config.a0_root / "contract" / "selection" / "simpleloop.selection.json"
    frozen: Dict[str, Any] = {}
    frozen_note = None
    if Path(frozen_path).is_file():
        frozen = json.loads(Path(frozen_path).read_text("utf-8"))
    else:
        # The frozen copy is another workstream's artifact; a missing file is
        # recorded as "could not compare", never as a silent pass and never as a
        # crash of the adapter.
        frozen_note = f"{frozen_path} is absent: the shared blocks could not be compared"
    shared = {}
    for block in ("scalarization", "failure_stage_mapping"):
        shared[block] = {
            "identical": (
                None if not frozen
                else _canonical(declared.get(block)) == _canonical(frozen.get(block))
            ),
            "digest": sha256_text(_canonical(declared.get(block)).decode("ascii")),
        }
    canonical_copy = _frozen_canonical_compare(config, canonical)
    return {
        "path": str(SELECTION_DECLARATION),
        "schema": declared.get("schema"),
        "policy_id": declared.get("policy_id"),
        "status": declared.get("status"),
        "canonical_digest": sha256_text(canonical.decode("ascii")),
        "digest_rule": "sha256 over the contract's canonical JSON "
                       "(sorted keys, no whitespace, ASCII) -- evalcontract.py:102",
        "shared_blocks_from": str(frozen_path),
        "shared_blocks_note": frozen_note,
        "shared_blocks": shared,
        "frozen_canonical_copy": canonical_copy,
        "failure_stage_mapping": declared.get("failure_stage_mapping"),
    }


def _frozen_canonical_compare(config: "AdapterConfig",
                              canonical: bytes) -> Dict[str, Any]:
    """Does the contract owner's canonical `kapso.selection.json` match ours?

    The contract owner froze a copy under `a0/contract/selection/` from the
    workstream's proposal; the two must stay canonically identical, and a
    divergence is a drift signal rather than an adapter error, so it is
    *reported* (a joiner can read the boolean) instead of aborting the run.
    """
    path = config.a0_root / "contract" / "selection" / "kapso.selection.json"
    if not Path(path).is_file():
        return {"path": str(path), "present": False,
                "identical_to_this_declaration": None,
                "note": "the contract owner has not frozen a canonical copy; this "
                        "run's declaration is the runtime-side source of truth"}
    frozen = json.loads(Path(path).read_text("utf-8"))
    frozen_canonical = _canonical(frozen)
    identical = frozen_canonical == canonical
    result: Dict[str, Any] = {
        "path": str(path),
        "present": True,
        "canonical_digest": sha256_text(frozen_canonical.decode("ascii")),
        "identical_to_this_declaration": identical,
    }
    if not identical:
        # Name what moved, so a reader cannot mistake this drift signal for an
        # unexplained failure.  The normative blocks are reported separately in
        # `shared_blocks`; a difference here is a documentation change the
        # contract owner has to re-freeze.
        declared = json.loads(SELECTION_DECLARATION.read_text("utf-8"))
        result["differing_top_level_keys"] = sorted(
            key for key in set(declared) | set(frozen)
            if _canonical(declared.get(key)) != _canonical(frozen.get(key))
        )
        result["note"] = (
            "the runtime-side declaration changed after the contract owner froze "
            "their copy; the frozen copy must be re-adopted (see "
            "differing_top_level_keys). The normative A0-wide blocks are checked "
            "separately in shared_blocks and are unaffected by this note."
        )
    return result


def _canonical(payload: Any) -> bytes:
    """`a0/contract/evalcontract.py:68-88` canonicalisation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


# --------------------------------------------------------------------------- #
# traces
# --------------------------------------------------------------------------- #

TRACE_KINDS = ("score", "selection", "resource")
MERGED_KIND = "all"


def _count_stages(units) -> Dict[str, int]:
    counts = {stage: 0 for stage in FAILURE_STAGE_ENUM}
    for _iteration, _candidate, stage in sorted(units, key=str):
        counts[stage] = counts.get(stage, 0) + 1
    return {stage: n for stage, n in sorted(counts.items()) if n}


class TraceWriter:
    """Appends the three A0 traces plus the run's merged stream."""

    def __init__(
        self,
        run_dir: Path,
        runtime: str,
        run_id: str,
        task: str,
        eid_star: str,
        eid_r: Dict[str, Any],
        kinds: List[str],
    ) -> None:
        self.run_dir = Path(run_dir)
        self.runtime = runtime
        self.run_id = run_id
        self.task = task
        self.eid_star = eid_star
        self.eid_r = eid_r
        self.kinds = list(kinds)
        self.traces_dir = self.run_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._handles: Dict[str, Any] = {}
        self._paths: Dict[str, Path] = {}
        for kind in self.kinds:
            path = self.traces_dir / f"{runtime}.{run_id}.{kind}.jsonl"
            self._paths[kind] = path
            self._handles[kind] = path.open("w", encoding="utf-8")
        # The run's merged stream: the validation unit (adapter_contract.md
        # section 6.3).  A selection event's `source_score_event_id` points at a
        # score event in a *different* per-kind file, so it can only be resolved
        # in this stream.
        merged = self.traces_dir / f"{runtime}.{run_id}.{MERGED_KIND}.jsonl"
        self._paths[MERGED_KIND] = merged
        self._handles[MERGED_KIND] = merged.open("w", encoding="utf-8")
        self.counts = {"score": 0, "selection": 0, "resource": 0}
        self.score_event_ids: List[str] = []
        self._units: set = set()
        self._score_units: set = set()

    def paths(self) -> Dict[str, str]:
        return {kind: str(path) for kind, path in self._paths.items()}

    def _envelope(
        self,
        kind: str,
        candidate_id: str,
        iteration: int,
        parent_id: Optional[str],
        theta_e: Dict[str, Any],
        failure_stage: str,
        failure_detail: Optional[str],
    ) -> Dict[str, Any]:
        self._seq += 1
        event_id = (
            f"{self.runtime}-{self.run_id}-{kind[0]}-i{iteration}-"
            f"n{self._seq:05d}"
        )
        event: Dict[str, Any] = {
            "trace": kind,
            "event_id": event_id,
            "event_seq": self._seq - 1,
            "run_id": self.run_id,
            "task": self.task,
            "runtime": self.runtime,
            "iteration": iteration,
            "candidate_id": candidate_id,
            "parent_id": parent_id,
            "eid_star": self.eid_star,
            "eid_r": self.eid_r,
            "theta_E": theta_e,
            "failure_stage": failure_stage,
            "failure_detail": failure_detail,
        }
        return event

    def _write(self, kind: str, event: Dict[str, Any]) -> None:
        line = json.dumps(event, sort_keys=True) + "\n"
        self._handles[kind].write(line)
        self._handles[kind].flush()
        self._handles[MERGED_KIND].write(line)
        self._handles[MERGED_KIND].flush()
        self.counts[kind] += 1
        if kind == "score":
            self.score_event_ids.append(event["event_id"])
        # One unit per (iteration, candidate); a failure is reported on both the
        # score and the resource event of the same unit, so counting lines
        # would double it (trace_validate.py:count_failure_stages).
        unit = (event["iteration"], event["candidate_id"],
                event.get("failure_stage") or "none")
        self._units.add(unit)
        if kind == "score":
            self._score_units.add(unit)

    def failure_stage_counts(self) -> Dict[str, int]:
        """Counts over the run's merged stream (the validation unit)."""
        return _count_stages(self._units)

    def failure_stage_counts_score_trace(self) -> Dict[str, int]:
        """Counts over the score trace alone -- the runner's fallback rule.

        Reported alongside so a joiner can use one rule consistently across
        runtimes; the two agree whenever selection events carry no failure.
        """
        return _count_stages(self._score_units)

    def emit_score(
        self,
        *,
        candidate_id: str,
        iteration: int,
        parent_id: Optional[str],
        theta_e: Dict[str, Any],
        outcome: Dict[str, Any],
        fr: Dict[str, Any],
        search_signal: Any,
        evaluator_evidence: Dict[str, Any],
        failure_stage: str = "none",
        failure_detail: Optional[str] = None,
    ) -> str:
        event = self._envelope("score", candidate_id, iteration, parent_id,
                              theta_e, failure_stage, failure_detail)
        event["outcome"] = outcome
        event["fr"] = fr
        event["search_signal"] = search_signal
        event["evaluator_evidence"] = evaluator_evidence
        self._write("score", event)
        return event["event_id"]

    def emit_selection(
        self,
        *,
        candidate_id: str,
        iteration: int,
        parent_id: Optional[str],
        theta_e: Dict[str, Any],
        selection: Dict[str, Any],
        failure_stage: str = "none",
        failure_detail: Optional[str] = None,
    ) -> None:
        event = self._envelope("selection", candidate_id, iteration, parent_id,
                              theta_e, failure_stage, failure_detail)
        event["selection"] = selection
        self._write("selection", event)

    def emit_resource(
        self,
        *,
        candidate_id: str,
        iteration: int,
        parent_id: Optional[str],
        theta_e: Dict[str, Any],
        t_wall_sec: float,
        n_evaluator_calls: int,
        concurrency_cap: int,
        concurrency_observed: int,
        scope: str = "iteration",
        secondary: Optional[Dict[str, Any]] = None,
        budget_hard: Optional[Dict[str, Any]] = None,
        failure_stage: str = "none",
        failure_detail: Optional[str] = None,
    ) -> None:
        event = self._envelope("resource", candidate_id, iteration, parent_id,
                              theta_e, failure_stage, failure_detail)
        event["T_wall"] = {
            "value_sec": round(float(t_wall_sec), 6),
            "clock": "monotonic",
            "scope": scope,
        }
        event["N_evaluatorCalls"] = int(n_evaluator_calls)
        event["concurrency"] = {
            "cap": int(concurrency_cap),
            "observed_max": int(concurrency_observed),
        }
        if secondary is not None:
            event["secondary"] = secondary
        if budget_hard is not None:
            event["budget_hard"] = budget_hard
        self._write("resource", event)

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()

    def validate(self, config: AdapterConfig) -> Dict[str, Any]:
        """Validate the run, not the file (adapter_contract.md section 6.3).

        `validate-run` validates every run under the run directory as one
        stream, using the merged `<runtime>.<run_id>.all.jsonl`, and
        additionally checks each per-kind file for event-level validity and
        kind purity.  The per-file rule (`validate --trace <per-kind file>`)
        cannot resolve a cross-file `source_score_event_id` and is no longer
        used here.
        """
        proc = subprocess.run(
            [sys.executable, str(config.trace_validate), "validate-run",
             "--run-dir", str(self.run_dir)],
            capture_output=True, text=True,
        )
        report: Dict[str, Any] = {
            "unit": "run",
            "cmd": " ".join(
                ["python", str(config.trace_validate), "validate-run",
                 "--run-dir", str(self.run_dir)]
            ),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "per_kind": {},
        }
        for kind in self.kinds:
            path = self._paths[kind]
            stats = subprocess.run(
                [sys.executable, str(config.trace_validate), "stats",
                 "--trace", str(path)],
                capture_output=True, text=True,
            )
            report["per_kind"][kind] = {
                "path": str(path),
                "stats_stdout": stats.stdout.strip(),
            }
        report["merged"] = {
            "path": str(self._paths[MERGED_KIND]),
            "events": sum(self.counts.values()),
        }
        return report


# --------------------------------------------------------------------------- #
# KAPSO import bootstrap
# --------------------------------------------------------------------------- #

def bootstrap_kapso(config: AdapterConfig) -> None:
    """Make the pinned KAPSO checkout importable without installing it.

    The pinned snapshot is read-only: it is added to ``sys.path`` rather than
    installed, so no ``*.egg-info`` or build directory is ever written into it.
    """
    src = str(config.kapso_src)
    if src not in sys.path:
        sys.path.insert(0, src)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def fr_payload(fr_spec_path: Path, declared_in: str) -> Dict[str, Any]:
    """The frozen F_r declaration, hashed exactly as the contract hashes it."""
    spec = json.loads(Path(fr_spec_path).read_text("utf-8"))
    canonical = canonical_json(spec)
    return {
        "name": spec["name"],
        "version": spec["version"],
        "applies": spec["applies"],
        "spec_hash": sha256_text(canonical),
        "declared_in": declared_in,
    }
