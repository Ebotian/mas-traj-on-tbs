"""T1's frozen evaluator identity (`EID*`), computed by `a0/contract/evalcontract.py`.

**Why this file exists.**  Two arms can only be compared on ``Δ`` if the thing
that measured them has one recomputable identity (principle (i)).  For the
plumbing task that identity is `a0/tasks/circle-packing/plumbing.EID.proposed.json`
over the canonical `EvalContract`; for T1 the max-cut worker shipped a frozen
evaluator (`a0/tasks/maxcut/e_star.py`, `suite/` with manifest sha256
``47324fcc…``) but no EID document.  `a0/a1/DEVIATIONS.md` **D-A1-1** records that
this module authors it, and this module provides the recomputation.

The five components are built by the contract owner's own code — this module
supplies a *spec*, never a hash:

===============  ==========================================================
component        T1's material
===============  ==========================================================
EvaluatorSource  `a0/tasks/maxcut/{e_star.py,e_star_child.py}` (source tree)
DependencyLock   the declared interpreter range and "no third-party deps"
DataManifest     `suite/manifest.json` + all 60 frozen graphs + `candidates/manifest.json`
Config           seed 1337, τ, the child environment policy, the exit table
MetricDefinition `cut_edges`, integer, maximize, exact aggregation
===============  ==========================================================

`E*`'s own `evaluator_source_sha256` (`e_star.py digest --value-only`) is checked
against the `EvaluatorSource` digest this document carries, so the two ways of
naming the evaluator cannot drift apart.

    python3 a0/a1/t1_eid.py write     # (re)generate T1-EID.json and T1.contract.json
    python3 a0/a1/t1_eid.py build     # the same command, under the assignment's name
    python3 a0/a1/t1_eid.py check     # recompute everything; non-zero on drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO_ROOT / "a0" / "contract"
MAXCUT_DIR = REPO_ROOT / "a0" / "tasks" / "maxcut"
SUITE_DIR = MAXCUT_DIR / "suite"

if str(CONTRACT_DIR) not in sys.path:
    sys.path.insert(0, str(CONTRACT_DIR))
import evalcontract  # noqa: E402

SPEC_PATH = REPO_ROOT / "a0" / "a1" / "T1.contract.json"
EID_PATH = REPO_ROOT / "a0" / "a1" / "T1-EID.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluator_source_sha256() -> str:
    """E*'s own identity, taken from E* itself (never recomputed by hand here)."""
    proc = subprocess.run(
        [sys.executable, "e_star.py", "digest", "--value-only"],
        cwd=str(MAXCUT_DIR), capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise SystemExit(f"`e_star.py digest` failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def suite_files() -> list:
    files = ["a0/tasks/maxcut/suite/manifest.json"]
    for graph_set in ("dev", "eval", "calibration"):
        files.extend(
            sorted(
                str(path.relative_to(REPO_ROOT))
                for path in (SUITE_DIR / graph_set).glob("*.json")
            )
        )
    files.append("a0/tasks/maxcut/candidates/manifest.json")
    return sorted(files)


def build_spec() -> dict:
    return {
        "schema": "a0.evalcontract.spec/v1",
        "base": "../..",
        "task": "maxcut-t1",
        "components": {
            "EvaluatorSource": {
                "root": "a0/tasks/maxcut",
                "include": ["e_star.py", "e_star_child.py"],
                "exclude": ["**/*.tmp", "**/__pycache__/**"],
            },
            "DependencyLock": {
                "entries": [
                    {
                        "name": "interpreter",
                        "requirement": "cpython >= 3.10, standard library only",
                        "note": (
                            "a0/tasks/maxcut/e_star.py and e_star_child.py import nothing "
                            "outside the standard library; the candidate child is launched "
                            "with the evaluator's own absolute interpreter path"
                        ),
                    },
                    {"name": "third_party_runtime_dependencies", "value": []},
                    {
                        "name": "child_environment",
                        "value": ["PATH", "PYTHONDONTWRITEBYTECODE", "HOME", "LANG"],
                        "note": "INTERFACE.md §4; measured by E*'s child-environment probe",
                    },
                ]
            },
            "DataManifest": {
                "files": suite_files(),
                "entries": [
                    {
                        "name": "suite",
                        "role": "24 dev + 24 eval + 12 calibration canonical graphs",
                        "manifest": "a0/tasks/maxcut/suite/manifest.json",
                        "manifest_sha256_prefix": "47324fcc",
                    },
                    {
                        "name": "candidate_set",
                        "role": "C*(T1): the 21 fixed candidates used for conformance",
                        "manifest": "a0/tasks/maxcut/candidates/manifest.json",
                    },
                ],
            },
            "Config": {
                "value": {
                    "task": "maxcut-t1",
                    "metric": "cut_edges",
                    "theta_e_canonical": {"seed": 1337, "timeout_s": 10.0},
                    "theta_e_semantics": {
                        "seed": "passed to the candidate as --seed; inert for a deterministic candidate",
                        "timeout_s": "tau; at tau the harness SIGKILLs the process group (INTERFACE.md §7)",
                        "fidelity": "none — T1 has no fidelity classes",
                        "fraction": "none — every candidate is measured on the whole graph",
                    },
                    "evaluator": {
                        "cli": (
                            "e_star.py evaluate --candidate <path> --graph <json> "
                            "--seed <S> --timeout <tau> --out <json>"
                        ),
                        "exit_codes": {"ok": 0, "invalid": 2, "error": 3, "timeout": 4},
                        "outcome_is_multi_field": True,
                        "scalarization_owner": "F_r (per runtime)",
                        "numbers_are_the_harness_s": (
                            "the harness runs E* and authors the Outcome; the runtime consumes it"
                        ),
                    },
                    "determinism": {
                        "rule": "INTERFACE.md §6 rule 4: canonical bytes of partition.json over two invocations",
                        "runs": 2,
                        "violation": "non_deterministic (status error)",
                    },
                    "environment_policy": {
                        "allow_network": False,
                        "child_env_specified_by_evaluator": True,
                        "path": "minimal",
                        "private_home_tmpdir_cwd": True,
                        "pythondontwritebytecode": "1",
                        "no_proxy_variables": True,
                    },
                    "conformance": {"epsilon": {"kind": "exact", "unit": "edges", "value": 0}},
                    "revert_safety": {
                        "note": "E* writes only below --state-dir and --out; never inside a candidate tree",
                        "required": True,
                    },
                }
            },
            "MetricDefinition": {
                "value": {
                    "objective": {
                        "name": "cut_edges",
                        "direction": "maximize",
                        "unit": "edges",
                        "authoritative": "integer",
                        "display_only": "cut_fraction",
                        "aggregation": "fractions.Fraction over integers",
                        "weighted": False,
                    },
                    "failure_semantics": (
                        "invalid/error/timeout carry cut_edges: null — never 0; a legitimate 0 "
                        "is reported as 0"
                    ),
                }
            },
        },
    }


def build(spec: dict) -> dict:
    return evalcontract.build_contract(spec, SPEC_PATH, cli_base=str(REPO_ROOT))


def write() -> dict:
    spec = build_spec()
    SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    document = build(spec)
    EID_PATH.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return document


def check() -> dict:
    spec = build_spec()
    if not SPEC_PATH.is_file():
        return {"pass": False, "reason": f"{SPEC_PATH} does not exist"}
    on_disk_spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if on_disk_spec != spec:
        return {"pass": False, "reason": "a0/a1/T1.contract.json no longer matches build_spec()"}
    if not EID_PATH.is_file():
        return {"pass": False, "reason": f"{EID_PATH} does not exist"}
    document = json.loads(EID_PATH.read_text(encoding="utf-8"))
    rebuilt = build(spec)
    if rebuilt["eid_star"] != document["eid_star"]:
        return {
            "pass": False,
            "reason": "eid_star drifted",
            "on_disk": document["eid_star"],
            "recomputed": rebuilt["eid_star"],
        }
    own = evaluator_source_sha256()
    # E*'s own identity is built from the same two files' sha256 values but with
    # its own digest recipe, so the two schemes are *not* the same number and
    # must not be compared as if they were. What must agree is the file-level
    # material both are built from.
    as_recorded = {
        record["path"]: record["sha256"]
        for record in rebuilt["components"]["EvaluatorSource"]["records"]
    }
    as_e_star_sees = _e_star_source_files()
    source_material_agrees = as_recorded == as_e_star_sees
    recompute = evalcontract.recompute_from_records(document)
    return {
        "pass": bool(source_material_agrees) and recompute.get("eid_star") == document["eid_star"],
        "eid_star": document["eid_star"],
        "component_digests": {
            name: component["digest"] for name, component in document["components"].items()
        },
        "evaluator_source_records": as_recorded,
        "evaluator_source_sha256_from_e_star_digest": own,
        "evaluator_source_material_agrees_with_e_star": source_material_agrees,
        "recompute_from_records": recompute,
        "files_hashed": {
            "DataManifest": len(rebuilt["components"]["DataManifest"]["records"]),
            "EvaluatorSource": len(rebuilt["components"]["EvaluatorSource"]["records"]),
        },
    }


def _e_star_source_files() -> dict:
    """What `E*` itself hashes, read from `E*` (not re-implemented here)."""
    proc = subprocess.run(
        [sys.executable, "-c",
         "import json,sys; sys.path.insert(0,'.'); import e_star;"
         "print(json.dumps({r['name']: r['sha256'] for r in e_star.source_file_digests()}))"],
        cwd=str(MAXCUT_DIR), capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise SystemExit(f"could not read E*'s source records: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.t1_eid")
    # `build` and `write` are the same command: both rebuild the spec and the EID
    # document from the evaluator's current bytes. `write` is the original name;
    # `build` is the one the A1 assignment names, and an alias costs nothing.
    parser.add_argument("command", choices=["write", "build", "check", "show"])
    args = parser.parse_args(argv)
    if args.command in ("write", "build"):
        document = write()
        print(json.dumps({"eid_star": document["eid_star"],
                          "eid": str(EID_PATH), "spec": str(SPEC_PATH)}, indent=1))
        return 0
    if args.command == "show":
        print(json.dumps(json.loads(EID_PATH.read_text(encoding="utf-8")), indent=1))
        return 0
    result = check()
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["pass"] else 5


if __name__ == "__main__":
    sys.exit(main())
