#!/usr/bin/env python3
"""One command that re-establishes every T1/KAPSO claim that costs nothing.

    python3 a0/a1/kapso_t1/verify.py            # rebuild, dry run, rehearse; exit 0 = pass
    python3 a0/a1/kapso_t1/verify.py --list     # what it runs
    python3 a0/a1/kapso_t1/verify.py --evidence # also print the committed evidence digests

The paid run is `a0/a1/kapso_t1/probes/live_t1.py arm` (one metered model call,
`CEq = 1116` at the commit that ships this); it is **not** re-run here, and its recorded
output is committed under `evidence/`. The *rehearsal* — the same arm, inside the same
closed topology, with the model call skipped — is free and therefore part of this
command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
EVIDENCE = HERE / "evidence"
KAPSO_PY = REPO_ROOT / "a0" / "runtimes" / "kapso" / ".venv" / "bin" / "python"

STEPS = [
    ("tree", [str(KAPSO_PY), "a0/a1/kapso_t1/build_tree.py", "check"],
     "the committed tree rebuilds byte-identically from T1-EID.json + C*(T1), and its "
     "EID_r equals the recorded fingerprint (KAPSO's own manifest_fingerprint)"),
    ("binding", [str(KAPSO_PY), "a0/a1/kapso_t1/t1_binding.py", "check"],
     "the max-cut EidStar binding loads, EID* recomputes (verify + recompute), and "
     "C*(T1) re-verifies its solution digests"),
    ("dryrun", [str(KAPSO_PY), "a0/a1/kapso_t1/probes/dryrun_t1.py",
                "--out-dir", "/tmp/a1t1-verify/dryrun"],
     "the model-free T1 dry run: the tree loads, the class triple is derived from the "
     "runtime, the harness's line is the score of record, selection follows it"),
    ("rehearse", ["python3", "a0/a1/kapso_t1/probes/live_t1.py", "rehearse",
                  "--out-dir", "/tmp/a1t1-verify/rehearse"],
     "the T1 arm inside the closed topology with the model call skipped: the meter, the "
     "harness, the ordering rule and the topology control, all free"),
    ("tests", ["python3", "-m", "pytest", "a0/a1/kapso_t1/tests", "-q"],
     "the unit invariants: a deterministic locator, the committed tree against its own "
     "fingerprint, the dev materializer, and the stub's refusals"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.kapso_t1.verify")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--evidence", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for name, command, purpose in STEPS:
            print(f"{name:10s} {' '.join(command)}\n{'':10s} {purpose}")
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
            "stdout_tail": (proc.stdout or "")[-1500:],
            "stderr_tail": (proc.stderr or "")[-800:],
        })

    evidence = {}
    if EVIDENCE.is_dir():
        for path in sorted(EVIDENCE.glob("*.json")):
            evidence[path.name] = sha256_file(path)

    verdict = "pass" if all(item["pass"] for item in results) else "fail"
    report = {
        "schema": "a0.a1.kapso_t1.verify/v1",
        "verdict": verdict,
        "steps": results,
        "committed_evidence": evidence,
        "paid_run_not_rerun_here": (
            "a0/a1/kapso_t1/probes/live_t1.py arm spends one metered DeepSeek call; its "
            "recorded output is a0/a1/kapso_t1/evidence/live_t1.json"
        ),
    }
    print(json.dumps({"verdict": verdict,
                      "steps": {item["step"]: item["pass"] for item in results},
                      "evidence": sorted(evidence)}, indent=1))
    for item in results:
        if not item["pass"]:
            # A failing step's reason is the whole point of running this, and the
            # summary alone would hide it (a rehearsal failed once, transiently, and
            # the reason was lost with the process).
            print(f"\n--- {item['step']} failed (exit {item['returncode']}) ---")
            print(item["stdout_tail"])
            print(item["stderr_tail"], file=sys.stderr)
    if args.evidence:
        for name, digest in evidence.items():
            print(f"{digest}  {name}")
    return 0 if verdict == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
