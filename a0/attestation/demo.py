#!/usr/bin/env python3
"""Build and run the declared-vs-executed gap demonstrations.

Each demonstration produces an attestation whose `EID_execution` disagrees with
the declared identity **while the declared `E*` source file on disk is
unchanged**, and then runs `verify_attestation.py` over it.

  d0-baseline-control the same candidate with nothing tampered with: the control
  d1-shadow-module    a module earlier on `sys.path` replaces a stdlib name the
                      evaluator uses, so the evaluator's *self-reported* identity
                      hash becomes a value of someone else's choosing
  d2-stale-bytecode   a forged `__pycache__` entry whose header validates against
                      the unchanged source: the executed code is not the source,
                      and E*'s self-report still reads as the frozen value
  d3-other-file       the runtime executes a *different file* under the same name
                      (the incident that motivated this workstream: `local_eval.py`
                      frozen as "the evaluator" while the runtime loaded another)

The baseline (`c05_overlapping` as declared) is `invalid` -- its nominal
`sum_radii` ties the best candidate, which is why it is in `C*` at all.

    python demo.py [--only d0,d1,d2,d3] [--skip-run]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import marshal
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
OUT = HERE / "out"
DEMO = OUT / "demo"
PYTHON = sys.executable
CANDIDATE = "a0/tasks/circle-packing/C_STAR/c05_overlapping"
FROZEN_ENTRY = REPO_ROOT / "a0/tasks/circle-packing/e_star.py"
CHILD = REPO_ROOT / "a0/tasks/circle-packing/e_star_child.py"
FROZEN_EPS_LINE = b"EPS = 1e-9  # evaluate.py:23"
PATCHED_EPS_LINE = b"EPS = 0.5  # DEMO d2/d3: the overlap epsilon is not the frozen one"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def e_star_source_digest(entries: list[dict]) -> str:
    """`e_star.py::evaluator_source_digest`, so the demos can *predict* the hash
    the evaluator will report and then check the prediction against what the
    attestation recorded."""
    text = json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def declared_source_entries() -> list[dict]:
    eid_inputs = json.loads(
        (REPO_ROOT / "a0/tasks/circle-packing/EID_INPUTS.json").read_text(encoding="utf-8")
    )
    records = eid_inputs["components"]["EvaluatorSource"]["canonical_material"]["records"]
    return [{"name": record["path"], "sha256": record["sha256"], "bytes": record["size"]}
            for record in sorted(records, key=lambda item: item["path"])]


def run(argv, **kwargs):
    completed = subprocess.run([str(item) for item in argv], capture_output=True, text=True,
                               cwd=str(REPO_ROOT), **kwargs)
    return {"argv": [str(item) for item in argv], "returncode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def patched_e_star_source() -> bytes:
    """The frozen evaluator with one constant changed, nothing else."""
    text = FROZEN_ENTRY.read_bytes()
    if FROZEN_EPS_LINE not in text:
        raise SystemExit("the frozen evaluator's EPS line moved; update the demo patch")
    return text.replace(FROZEN_EPS_LINE, PATCHED_EPS_LINE)


def build_d0() -> dict:
    """Control: the same candidate, the frozen evaluator, nothing tampered with."""
    return {
        "id": "d0-baseline-control",
        "what": "control: the frozen evaluator, no tampering; every verdict must be good",
        "scenario_dir": ".",
        "evaluator": "a0/tasks/circle-packing/e_star.py",
        "env": {},
        "declared_source_unchanged": True,
        "predictions": {
            "self_reported_evaluator_source_sha256": e_star_source_digest(declared_source_entries()),
        },
        "expect_verdicts": {"Q1_recomputes": "RECOMPUTES", "Q2_semantic": "SEMANTIC_MATCH",
                            "Q3_realization": "REALIZED"},
    }


def build_d1() -> dict:
    """A shadowing `hashlib` on PYTHONPATH.

    The shim forwards everything to the real stdlib module except that the exact
    bytes of `e_star.py` hash to a value of the shim's choosing.  The evaluated
    candidate, its status and its objective are therefore untouched, and the only
    thing that changes is the hash E* reports as its own identity.
    """
    directory = DEMO / "d1-shadow-module"
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True, exist_ok=True)
    real_hashlib = Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "hashlib.py"
    (directory / "hashlib.py").write_text(
        '"""DEMO: a shadowing hashlib. Not part of the study."""\n'
        "import importlib.util as _util, sys as _sys\n"
        f"_REAL_PATH = {str(real_hashlib)!r}\n"
        f"_TARGET = open({str(FROZEN_ENTRY)!r}, 'rb').read()\n"
        "_spec = _util.spec_from_file_location('_demo_real_hashlib', _REAL_PATH)\n"
        "_real = _util.module_from_spec(_spec)\n"
        "_sys.modules['_demo_real_hashlib'] = _real\n"
        "_spec.loader.exec_module(_real)\n"
        "from _demo_real_hashlib import *  # noqa: F401,F403\n"
        "_FAKE = _real.sha256(b'not-the-frozen-evaluator').hexdigest()\n"
        "class _Digest:\n"
        "    def __init__(self, value):\n"
        "        self._value = value\n"
        "    def hexdigest(self):\n"
        "        return self._value\n"
        "    def digest(self):\n"
        "        return bytes.fromhex(self._value)\n"
        "def sha256(data=b'', *args, **kwargs):\n"
        "    if data == _TARGET:\n"
        "        return _Digest(_FAKE)\n"
        "    return _real.sha256(data, *args, **kwargs)\n",
        encoding="utf-8",
    )
    fake = hashlib.sha256(b"not-the-frozen-evaluator").hexdigest()
    entries = declared_source_entries()
    return {
        "id": "d1-shadow-module",
        "what": "a module on PYTHONPATH shadows a stdlib name the evaluator imports",
        "scenario_dir": str(directory.relative_to(REPO_ROOT)),
        "evaluator": "a0/tasks/circle-packing/e_star.py",
        "env": {"PYTHONPATH": str(directory)},
        "declared_source_unchanged": True,
        "mechanism": "the shim returns `fake` whenever the hashed bytes are exactly the frozen "
                     "e_star.py, so only the evaluator's self-reported identity changes",
        "predictions": {
            "self_reported_evaluator_source_sha256": e_star_source_digest(
                [{"name": item["name"],
                  "sha256": fake if item["name"] == "e_star.py" else item["sha256"],
                  "bytes": item["bytes"]}
                 for item in entries]
            ),
            "frozen_self_reported_value": e_star_source_digest(entries),
            "fake_entry_digest": fake,
        },
    }


def build_d2() -> dict:
    """A forged `__pycache__` entry next to a byte-identical copy of the source."""
    directory = DEMO / "d2-stale-bytecode"
    shutil.rmtree(directory, ignore_errors=True)
    (directory / "__pycache__").mkdir(parents=True, exist_ok=True)
    entry = directory / "e_star.py"
    shutil.copy2(FROZEN_ENTRY, entry)
    shutil.copy2(CHILD, directory / "e_star_child.py")

    stat = entry.stat()
    patched = patched_e_star_source()
    code = compile(patched, str(entry), "exec")
    header = (
        importlib.util.MAGIC_NUMBER
        + (0).to_bytes(4, "little")                      # flags: timestamp-based
        + (int(stat.st_mtime) & 0xFFFFFFFF).to_bytes(4, "little")
        + (stat.st_size & 0xFFFFFFFF).to_bytes(4, "little")
    )
    pyc = directory / "__pycache__" / f"e_star.{sys.implementation.cache_tag}.pyc"
    pyc.write_bytes(header + marshal.dumps(code))
    entries = declared_source_entries()
    return {
        "id": "d2-stale-bytecode",
        "what": "a forged __pycache__ entry: the header validates against the unchanged source, "
                "so the interpreter executes bytecode that is not that source",
        "scenario_dir": str(directory.relative_to(REPO_ROOT)),
        "evaluator": str(entry.relative_to(REPO_ROOT)),
        "env": {},
        "declared_source_unchanged": True,
        "mechanism": "the copy of e_star.py is byte-identical to the frozen file, and the forged "
                     ".pyc carries the copy's own mtime and size, so CPython's timestamp validation "
                     "accepts it and never recompiles",
        "predictions": {
            "copied_source_sha256": sha256_file(entry),
            "frozen_source_sha256": entries[0]["sha256"],
            "self_reported_evaluator_source_sha256": e_star_source_digest(entries),
            "loaded_code_sha256": hashlib.sha256(marshal.dumps(code)).hexdigest(),
        },
        "forged_bytecode": {
            "path": str(pyc.relative_to(REPO_ROOT)),
            "patch": PATCHED_EPS_LINE.decode(),
            "pyc_header": {
                "magic_hex": header[:4].hex(),
                "flags": 0,
                "mtime_masked": int(stat.st_mtime) & 0xFFFFFFFF,
                "size_masked": stat.st_size & 0xFFFFFFFF,
            },
            "pyc_sha256": sha256_file(pyc),
        },
    }


def build_d3() -> dict:
    """A different file loaded under the evaluator's name."""
    directory = DEMO / "d3-other-file"
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True, exist_ok=True)
    entry = directory / "e_star.py"
    entry.write_bytes(patched_e_star_source())
    shutil.copy2(CHILD, directory / "e_star_child.py")
    entries = declared_source_entries()
    return {
        "id": "d3-other-file",
        "what": "the runtime executes a different file under the same name; the declared E* source "
                "on disk is untouched",
        "scenario_dir": str(directory.relative_to(REPO_ROOT)),
        "evaluator": str(entry.relative_to(REPO_ROOT)),
        "env": {},
        "declared_source_unchanged": True,
        "mechanism": "one constant is changed (the overlap epsilon), so a candidate whose only "
                     "defect is an overlap is reported `ok` with the best nominal score",
        "patch": PATCHED_EPS_LINE.decode(),
        "predictions": {
            "patched_source_sha256": sha256_file(entry),
            "frozen_source_sha256": entries[0]["sha256"],
            "self_reported_evaluator_source_sha256": e_star_source_digest(
                [{"name": "e_star.py", "sha256": sha256_file(entry), "bytes": entry.stat().st_size},
                 {"name": "e_star_child.py", "sha256": sha256_file(CHILD),
                  "bytes": CHILD.stat().st_size}]
            ),
        },
    }


def run_demo(spec: dict) -> dict:
    attestation = OUT / f"demo/attestation.{spec['id']}.json"
    verdict = OUT / f"demo/verdict.{spec['id']}.json"
    argv = [
        PYTHON, str(HERE / "attest.py"),
        "--candidate", CANDIDATE,
        "--evaluator", spec["evaluator"],
        "--attestation-out", str(attestation.relative_to(REPO_ROOT)),
    ]
    for key, value in spec["env"].items():
        argv += ["--env", f"{key}={value}"]
    attest_run = run(argv)
    spec["attest"] = {
        "returncode": attest_run["returncode"],
        "stdout": attest_run["stdout"],
        "stderr": attest_run["stderr"][-2000:],
        "attestation": str(attestation.relative_to(REPO_ROOT)),
    }
    if not attestation.is_file():
        spec["verdict"] = {"returncode": None, "stdout": "", "stderr": "attestation was not produced"}
        return spec
    document = json.loads(attestation.read_text(encoding="utf-8"))
    spec["eid_semantic"] = document["eid_semantic"]
    spec["eid_execution"] = document["eid_execution"]
    spec["declared_eid_star"] = document["declared_eid_star"]
    verify_run = run([PYTHON, str(HERE / "verify_attestation.py"),
                      "--attestation", str(attestation),
                      "--repo-root", ".", "--json-out", str(verdict), "--quiet"])
    spec["verdict"] = {
        "returncode": verify_run["returncode"],
        "stdout": verify_run["stdout"],
        "stderr": verify_run["stderr"],
        "verdict_file": str(verdict.relative_to(REPO_ROOT)) if verdict.is_file() else None,
    }
    if verdict.is_file():
        spec["verdicts"] = json.loads(verdict.read_text(encoding="utf-8"))["verdicts"]
        spec["failed_checks"] = [
            check["name"] for check in json.loads(verdict.read_text(encoding="utf-8"))["checks"]
            if check["passed"] is not True and check["severity"] == "gate"
        ]
    payload = document["payload"]
    spec["observed"] = {
        "foreign_modules": [item["name"] for item in payload["loaded_artifacts"]["foreign_modules"]],
        "foreign_origins": {item["name"]: item["origin"]
                            for item in payload["loaded_artifacts"]["foreign_modules"]},
        "shadowing_hazards": [item["shadows"] for item in payload["loaded_artifacts"]["shadowing_hazards"]],
        "routes_agree": payload["evaluator_execution"]["routes_agree"],
        "self_reported_evaluator_source_sha256":
            payload["evaluator_execution"]["self_reported_evaluator_source_sha256"],
        "authoritative_route": payload["evaluator_execution"]["authoritative_route"],
        "capture_route": payload["evaluator_execution"]["capture_route"],
        "outcome_status": payload["evaluator_execution"]["outcome_status"],
        "reference_comparison_matches":
            payload["evaluator_execution"]["reference_comparison_matches"],
        "reference_expected_status":
            payload["evaluator_execution"]["reference_table_row_expected_status"],
        "evaluator_sources": [
            {key: record.get(key) for key in ("name", "origin", "declared_path", "declared_match",
                                              "file_sha256", "file_size", "loaded_code_sha256",
                                              "fresh_compile_sha256", "bytecode_matches_source",
                                              "pyc_path", "pyc_sha256", "is_entry")}
            for record in payload["loaded_artifacts"]["evaluator_sources"]
        ],
    }
    spec["declared_source_unchanged_after"] = (
        sha256_file(FROZEN_ENTRY)
        == spec.get("predictions", {}).get("frozen_source_sha256", sha256_file(FROZEN_ENTRY))
    )
    spec["prediction_checks"] = _prediction_checks(spec)
    return spec


def _prediction_checks(spec: dict) -> list[dict]:
    """Did the forgery predict exactly what the attestation recorded?"""
    predictions = spec.get("predictions") or {}
    observed = spec.get("observed") or {}
    entry_records = [record for record in observed.get("evaluator_sources", []) if record.get("is_entry")]
    checks = []
    if "self_reported_evaluator_source_sha256" in predictions:
        checks.append({
            "name": "predicted the evaluator's self-reported identity hash",
            "predicted": predictions["self_reported_evaluator_source_sha256"],
            "observed": observed.get("self_reported_evaluator_source_sha256"),
            "holds": predictions["self_reported_evaluator_source_sha256"]
            == observed.get("self_reported_evaluator_source_sha256"),
        })
    if "frozen_self_reported_value" in predictions:
        checks.append({
            "name": "the falsified hash differs from the frozen self-report",
            "predicted": predictions["self_reported_evaluator_source_sha256"],
            "frozen": predictions["frozen_self_reported_value"],
            "holds": predictions["self_reported_evaluator_source_sha256"]
            != predictions["frozen_self_reported_value"],
        })
    if "loaded_code_sha256" in predictions:
        checks.append({
            "name": "predicted the code object the import route executes",
            "predicted": predictions["loaded_code_sha256"],
            "observed": [record.get("loaded_code_sha256") for record in entry_records],
            "holds": any(record.get("loaded_code_sha256") == predictions["loaded_code_sha256"]
                         for record in entry_records),
        })
        checks.append({
            "name": "the executed bytecode is not a compilation of the source on disk",
            "observed": [{"bytecode_matches_source": record.get("bytecode_matches_source"),
                          "loaded_code_sha256": record.get("loaded_code_sha256"),
                          "fresh_compile_sha256": record.get("fresh_compile_sha256")}
                         for record in entry_records],
            "holds": any(record.get("bytecode_matches_source") is False for record in entry_records),
        })
    if "patched_source_sha256" in predictions:
        checks.append({
            "name": "predicted the source hash of the file that ran",
            "predicted": predictions["patched_source_sha256"],
            "observed": [record.get("file_sha256") for record in observed.get("evaluator_sources", [])],
            "holds": any(record.get("file_sha256") == predictions["patched_source_sha256"]
                         for record in observed.get("evaluator_sources", [])),
        })
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="demo.py", description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="d0,d1,d2,d3")
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args(argv)

    DEMO.mkdir(parents=True, exist_ok=True)
    builders = {"d0": build_d0, "d1": build_d1, "d2": build_d2, "d3": build_d3}
    wanted = [item.strip() for item in args.only.split(",") if item.strip()]
    specs = [builders[key]() for key in wanted]

    frozen_before = sha256_file(FROZEN_ENTRY)
    evidence = {
        "schema": "a0.attestation.demo-evidence/v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_by": "a0/attestation/demo.py",
        "candidate": CANDIDATE,
        "declared_expectation_for_this_candidate": "invalid (its nominal sum_radii ties the best candidate)",
        "declared_source_invariance": {
            "path": str(FROZEN_ENTRY.relative_to(REPO_ROOT)),
            "sha256_before_the_demos": frozen_before,
            "sha256_after_the_demos": None,
            "unchanged": None,
        },
        "demos": specs,
    }
    for spec in specs:
        print(f"== {spec['id']}: {spec['what']}")
        if args.skip_run:
            continue
        run_demo(spec)
        print(f"   attest rc={spec['attest']['returncode']} verdict rc={spec['verdict']['returncode']} "
              f"{spec.get('verdicts')}")
        print(f"   foreign={spec['observed']['foreign_modules']} "
              f"hazards={spec['observed']['shadowing_hazards']} "
              f"routes_agree={spec['observed']['routes_agree']} "
              f"authority={spec['observed']['authoritative_route']['status']} "
              f"capture={spec['observed']['capture_route']['status']}"
              f"({spec['observed']['capture_route']['objective_value']})")
        for name in spec.get("failed_checks", []):
            print(f"   caught: {name}")
        for check in spec.get("prediction_checks", []):
            print(f"   prediction {'holds' if check['holds'] else 'FAILS'}: {check['name']}")
        print(f"   declared E* source unchanged: {spec.get('declared_source_unchanged_after')}")
        expected = spec.get("expect_verdicts")
        if expected:
            spec["matches_expectation"] = spec.get("verdicts") == expected
            print(f"   verdicts match the expectation: {spec['matches_expectation']}")

    evidence["declared_source_invariance"]["sha256_after_the_demos"] = sha256_file(FROZEN_ENTRY)
    evidence["declared_source_invariance"]["unchanged"] = (
        evidence["declared_source_invariance"]["sha256_before_the_demos"]
        == evidence["declared_source_invariance"]["sha256_after_the_demos"]
    )
    (DEMO / "EVIDENCE.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    print(f"\ndeclared E* source unchanged across all demos: "
          f"{evidence['declared_source_invariance']['unchanged']}")
    print(f"wrote {DEMO / 'EVIDENCE.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
