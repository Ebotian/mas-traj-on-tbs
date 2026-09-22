#!/usr/bin/env python3
"""One command that re-establishes every A1 harness-wiring claim, model-free.

    python3 a0/a1/verify.py                # everything that costs nothing
    python3 a0/a1/verify.py --list         # what it runs
    python3 a0/a1/verify.py --evidence     # also re-hash the committed evidence

It deliberately excludes the paid arms: those are
``a0/a1/probes/live_probe.py`` and they spend money, so they are run
deliberately and their recorded output is committed under ``a0/a1/evidence/``.
This command re-runs everything a third party can re-derive for free and prints a
single verdict; exit code 0 means every step passed.
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
A1 = REPO_ROOT / "a0" / "a1"
EVIDENCE = A1 / "evidence"
SIMPLELOOP_PY = REPO_ROOT / "a0/runtimes/simpleloop/.venv/bin/python"
KAPSO_PY = REPO_ROOT / "a0/runtimes/kapso/.venv/bin/python"

STEPS = [
    ("t1-eid", ["python3", "a0/a1/t1_eid.py", "check"],
     "T1's EID* recomputes from T1.contract.json and the frozen evaluator bytes"),
    ("declarations", ["python3", "a0/a1/declaration.py", "build"],
     "CID/AID_r are rebuilt from the repository and pass the causal-role audit"),
    ("wiring-simpleloop", [str(SIMPLELOOP_PY), "a0/a1/probes/wiring_simpleloop.py",
                           "--out-dir", "/tmp/a1-verify/wiring-simpleloop"],
     "the runtime consumes the harness's Outcome, including a deliberately wrong one"),
    ("wiring-kapso", [str(KAPSO_PY), "a0/a1/probes/wiring_kapso.py",
                      "--out-dir", "/tmp/a1-verify/wiring-kapso"],
     "the harness's score is written after the session and wins; the class triple is derived"),
    ("skeleton-dryrun", ["python3", "a0/a1/probes/skeleton_dryrun.py",
                         "--out-dir", "/tmp/a1-verify/skeleton-dryrun"],
     "identity, causal audit, budget enforcement and block invalidation, dry-run"),
    ("tests", ["python3", "-m", "pytest", "a0/a1/tests", "-q"],
     "the unit-level invariants"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.verify")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--evidence", action="store_true",
                        help="also print the committed evidence digests")
    args = parser.parse_args(argv)

    if args.list:
        for name, command, purpose in STEPS:
            print(f"{name:20s} {' '.join(command)}\n{'':20s} {purpose}")
        return 0

    results = []
    for name, command, purpose in STEPS:
        proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True)
        results.append({
            "step": name,
            "purpose": purpose,
            "command": command,
            "returncode": proc.returncode,
            "pass": proc.returncode == 0,
            "stdout_tail": (proc.stdout or "")[-1200:],
            "stderr_tail": (proc.stderr or "")[-800:],
        })

    evidence = {}
    if EVIDENCE.is_dir():
        for path in sorted(EVIDENCE.glob("*.json")):
            evidence[path.name] = sha256_file(path)

    verdict = "pass" if all(item["pass"] for item in results) else "fail"
    report = {
        "schema": "a0.a1.verify/v1",
        "verdict": verdict,
        "steps": results,
        "committed_evidence": evidence,
        "paid_runs_are_not_rerun_here": (
            "a0/a1/probes/live_probe.py spends money; its recorded output is under "
            "a0/a1/evidence/live_*.json"
        ),
    }
    print(json.dumps({"verdict": verdict,
                      "steps": {item["step"]: item["pass"] for item in results},
                      "evidence": sorted(evidence)}, indent=1))
    if args.evidence:
        for name, digest in evidence.items():
            print(f"{digest}  {name}")
    return 0 if verdict == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
