"""The max-cut `EidStar` binding: T1's frozen identity, as the KAPSO adapter sees it.

`a0/runtimes/kapso/a0_adapter/common.py::EidStar` is a *reader* of an EID*
document: it takes `eid_star`, the five component digests, the canonical
`theta_E`, the metric name and the `EvaluatorSource` / `DataManifest` records, and
refuses anything missing (`load_eid_star`). T1's document
(`a0/a1/T1-EID.json`, `EID* = 7ce9e72f…`, authored by `a0/a1/t1_eid.py`, see
`a0/a1/DEVIATIONS.md` D-A1-1) is such a document, and this module is the binding
that makes the KAPSO adapter carry it:

* ``AdapterConfig.load`` against ``config/adapter.maxcut.json`` — so every path the
  adapter uses (`e_star_dir`, `candidate_set`, `eid_star_file`, `mode_config`) is
  T1's, resolved through the adapter's own config surface;
* ``load_candidates`` — C*(T1) in the adapter's own ``Candidate`` shape;
* ``verify_eid_star`` — the contract owner's `evalcontract.py verify|recompute`
  subprocesses, run by the adapter's own function, so a drifted T1-EID.json fails
  here rather than in a campaign;
* ``binding_record`` — one JSON object naming the evaluator, the grant, the metric
  and the candidate set, for the adapter's artifacts.

Why the candidate loader is here: the KAPSO adapter's
``common.load_candidate_set`` requires ``path`` + ``solution_sha256`` per entry,
while C*(T1)'s manifest carries ``dir`` + a ``files[]`` digest list (the max-cut
workstream's schema). ``load_candidates`` reads T1's schema and re-verifies every
``solution.py`` before returning the adapter's own ``Candidate`` objects, so the
caller gets the adapter's type without the adapter having to know T1's layout —
see ``DEVIATIONS.md`` D-KT1-3.

    python3 a0/a1/kapso_t1/t1_binding.py check      # rebuild + verify the binding
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
KAPSO_DIR = REPO_ROOT / "a0" / "runtimes" / "kapso"
if str(KAPSO_DIR) not in sys.path:
    sys.path.insert(0, str(KAPSO_DIR))

from a0_adapter.common import (  # noqa: E402  (path import on purpose)
    AdapterConfig,
    AdapterError,
    Candidate,
    EidStar,
    load_eid_star,
    sha256_file,
)

CONFIG_PATH = HERE / "config" / "adapter.maxcut.json"
TASK_ID = "T1-maxcut"


def load_config(path: Optional[Path] = None) -> AdapterConfig:
    return AdapterConfig.load(Path(path) if path else CONFIG_PATH)


def load_eid(config: AdapterConfig) -> EidStar:
    return load_eid_star(config.eid_star_file)


def locate_spec(config: AdapterConfig, eid: EidStar) -> Optional[Path]:
    """Find T1's contract spec on disk.

    ``evalcontract.py verify`` looks for the spec relative to the EID document's own
    directory, and the adapter's ``verify_eid_star`` helper additionally tries
    ``config.a0_root / spec`` — both are the *plumbing* convention (its document
    records ``"spec": "contract/plumbing.contract.json"``, a0-root-relative). T1's
    document records ``"spec": "a0/a1/T1.contract.json"``, repository-root-relative,
    so neither of those two lands on it. The spec is located here in that order plus
    the repository root, and ``--spec`` is passed explicitly rather than editing
    another workstream's EID document (`DEVIATIONS.md` D-KT1-4).
    """
    spec = eid.document.get("spec")
    if not spec:
        return None
    for candidate in (
        Path(config.a0_root) / spec,
        REPO_ROOT / spec,
        Path(eid.path).parent / spec,
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def verify_eid(config: AdapterConfig, eid: EidStar) -> Dict[str, Any]:
    """The contract owner's own `verify` + `recompute`, with T1's spec located."""
    spec_path = locate_spec(config, eid)
    verify_cmd = [sys.executable, str(config.evalcontract), "verify",
                  "--eid-file", str(eid.path)]
    if spec_path is not None:
        verify_cmd += ["--spec", str(spec_path)]
    recompute_cmd = [sys.executable, str(config.evalcontract), "recompute",
                     "--eid-file", str(eid.path)]
    verify = subprocess.run(verify_cmd, capture_output=True, text=True)
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
        "spec": str(spec_path) if spec_path else None,
        "spec_locator": "a0/a1/kapso_t1/t1_binding.py::locate_spec (see DEVIATIONS.md D-KT1-4)",
    }
    if verify.returncode != 0 or recompute.returncode != 0:
        raise AdapterError("EID* verification failed: " + json.dumps(report), 3)
    return report


def load_candidates(config: AdapterConfig) -> List[Candidate]:
    """C*(T1) as the adapter's `Candidate` list, with the digests re-verified.

    T1's manifest (``a0.maxcut.candidateset/v1``) records each candidate as a
    directory plus a digest list; the adapter's `Candidate` wants a path and a
    ``solution.py`` sha256. Both are re-derived here and cross-checked against the
    manifest's own record, so a drifted candidate set fails at load time.
    """
    manifest_path = Path(config.candidate_set)
    if not manifest_path.is_file():
        raise AdapterError(f"candidate set manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "a0.candidateset/v1":
        raise AdapterError(
            f"unexpected candidate-set schema {manifest.get('schema')!r} at {manifest_path}"
        )
    candidates: List[Candidate] = []
    for entry in manifest["candidates"]:
        directory = (manifest_path.parent / entry["dir"]).resolve()
        solution = directory / "solution.py"
        if not solution.is_file():
            raise AdapterError(f"{entry['candidate_id']}: missing {solution}")
        actual = sha256_file(solution)
        declared = next(
            (item["sha256"] for item in entry.get("files", []) if item["path"] == "solution.py"),
            None,
        )
        if declared is not None and declared != actual:
            raise AdapterError(
                f"{entry['candidate_id']}: solution.py sha256 {actual} != the manifest's "
                f"{declared}"
            )
        candidate = Candidate(
            candidate_id=entry["candidate_id"],
            path=directory,
            solution_sha256=actual,
            role=entry.get("role", ""),
            raw=entry,
        )
        setattr(candidate, "kind", entry.get("kind", ""))
        candidates.append(candidate)
    return candidates


def baseline_candidate(candidates: List[Candidate]) -> Candidate:
    """T1's c_0: the frozen low-scoring baseline (role ``low``).

    The plumbing set marks its baseline with ``role == "baseline"``; C*(T1) marks it
    ``low`` and names it ``c02_ok_low_baseline`` (a seeded uniform-random bisection —
    the reference the pre-registered gate is measured against). Both are read here so
    a renamed or re-roled set is a failure rather than a silent fallback.
    """
    by_name = [c for c in candidates if c.candidate_id == "c02_ok_low_baseline"]
    if not by_name:
        raise AdapterError("c02_ok_low_baseline is not in C*(T1)")
    if by_name[0].role != "low":
        raise AdapterError(
            f"c02_ok_low_baseline carries role {by_name[0].role!r}, not 'low'; the frozen set "
            "changed shape"
        )
    return by_name[0]


def binding_record(config: AdapterConfig, eid: EidStar,
                   candidates: List[Candidate]) -> Dict[str, Any]:
    theta = eid.canonical_theta
    metric = eid.components["MetricDefinition"]
    return {
        "schema": "a0.kapso_t1.eid_binding/v1",
        "task_id": TASK_ID,
        "runtime": "kapso",
        "eid_star": eid.eid_star,
        "eid_star_file": str(eid.path),
        "eid_star_task": eid.document.get("task"),
        "eid_star_components": {
            name: eid.component_digest(name)
            for name in ("EvaluatorSource", "DependencyLock", "DataManifest",
                         "Config", "MetricDefinition")
        },
        "evaluator": {
            "dir": str(config.e_star_dir),
            "entry": "e_star.py",
            "helper": "e_star_child.py",
            "python": str(config.e_star_python),
            "source_records": [
                {"path": record["path"], "sha256": record["sha256"],
                 "size": record.get("size")}
                for record in eid.evaluator_source_records()
            ],
        },
        "theta_e_canonical": {
            "seed": int(theta["seed"]),
            "timeout_s": float(theta["timeout_s"]),
        },
        "metric": {
            "name": metric["metric_name"],
            "direction": metric["direction"],
            "epsilon": eid.epsilon,
            "failure_semantics": metric["value"]["failure_semantics"],
            "objective": metric["value"]["objective"],
        },
        "candidate_set": {
            "manifest": str(config.candidate_set),
            "manifest_sha256": sha256_file(config.candidate_set),
            "candidate_count": len(candidates),
            "baseline": baseline_candidate(candidates).candidate_id,
            "members": {
                candidate.candidate_id: {
                    "dir": candidate.path.name,
                    "solution_sha256": candidate.solution_sha256,
                    "role": candidate.role,
                    "kind": getattr(candidate, "kind", ""),
                }
                for candidate in candidates
            },
        },
        "mode_config": str(config.mode_config),
        "registered_tree": str(config.registered_tree),
    }


def check() -> Dict[str, Any]:
    config = load_config()
    eid = load_eid(config)
    candidates = load_candidates(config)
    record = binding_record(config, eid, candidates)
    contract = verify_eid(config, eid)
    record["contract_verification"] = {
        "verify_returncode": contract["verify"]["returncode"],
        "recompute_returncode": contract["recompute"]["returncode"],
        "commands": [contract["verify"]["cmd"], contract["recompute"]["cmd"]],
    }
    record["pass"] = (
        contract["verify"]["returncode"] == 0
        and contract["recompute"]["returncode"] == 0
        and eid.eid_star == "7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec"
        and len(candidates) == 21
    )
    return record


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.kapso_t1.t1_binding")
    parser.add_argument("command", choices=["check"])
    args = parser.parse_args(argv)
    record = check()
    print(json.dumps(record, indent=1, sort_keys=True))
    return 0 if record["pass"] else 5


if __name__ == "__main__":
    sys.exit(main())
