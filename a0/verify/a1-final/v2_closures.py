#!/usr/bin/env python3
"""Item 2 — the closures, probed from a candidate spawned by the *service*.

Lanes, each one `eval_service.py evaluate` on my own hostile candidate:

* `service`  — the default (`--candidate-isolation sandbox`), the lane that
  matters: the candidate is a grandchild of the service, not of a bare E* call.
* `none`     — `--candidate-isolation none`, the labelled control. A closure
  probe that cannot show the leak in the open lane is not measuring anything.
* `honest`   — C*(T1)'s `c02_ok_low_baseline` through the same service, to show
  the honest path still books a real number.

    python3 a0/verify/a1-final/v2_closures.py [--quick]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROBE = HERE / "hostile" / "cand_probe"
HONEST = REPO / "a0/tasks/maxcut/candidates/c02_ok_low_baseline"
GRAPH = REPO / "a0/tasks/maxcut/suite/dev/G_dev_0001.json"
SERVICE = REPO / "a0/a1/eval_service.py"
ROOT_BASE = Path("/tmp/a1final-closures")


def run_lane(name: str, *, candidate: Path, isolation: str, timeout_s: float = 600.0) -> dict:
    root = ROOT_BASE / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    if isolation == "host":
        # The non-vacuity control for the *network*: the same candidate script,
        # the same targets, no harness and no namespace at all.
        out_path = root / "partition.json"
        command = [sys.executable, str(candidate / "solution.py"),
                   "--graph", str(GRAPH), "--out", str(out_path), "--seed", "1337"]
        proc = subprocess.run(command, cwd=str(root), capture_output=True, text=True,
                              timeout=timeout_s)
        findings = None
        for line in proc.stdout.splitlines():
            if line.startswith("HOSTILE_FINDINGS "):
                findings = json.loads(line[len("HOSTILE_FINDINGS "):])
        return {"lane": name, "isolation": isolation, "returncode": proc.returncode,
                "command": " ".join(command), "root": str(root),
                "stderr_tail": proc.stderr[-600:], "response": None, "findings": findings,
                "stdout_txt": None, "receipt_path": None}
    request = {
        "schema": "a0.a1.eval_request/v1",
        "request_id": f"req-{name}",
        "campaign_id": "C_a1final",
        "arm_id": "A_verify",
        "iteration": 1,
        "candidate_id": f"cand_{name}",
        "candidate_path": str(candidate),
        "graph_path": str(GRAPH),
        "seed": 1337,
        "timeout_s": 10.0,
    }
    request_path = root / "request.json"
    request_path.write_text(json.dumps(request, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    command = [sys.executable, str(SERVICE), "evaluate", "--root", str(root),
               "--candidate-isolation", isolation, "--request", str(request_path)]
    proc = subprocess.run(command, cwd=str(REPO), capture_output=True, text=True, timeout=timeout_s)
    result = {"lane": name, "isolation": isolation, "returncode": proc.returncode,
              "command": " ".join(command), "root": str(root),
              "stderr_tail": proc.stderr[-600:]}
    try:
        result["response"] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result["response"] = None
        result["stdout_head"] = proc.stdout[:600]

    findings = None
    matches = sorted((root / "estate").rglob("run1/stdout.txt"))
    if matches:
        for line in matches[0].read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("HOSTILE_FINDINGS "):
                findings = json.loads(line[len("HOSTILE_FINDINGS "):])
    result["findings"] = findings
    result["stdout_txt"] = str(matches[0]) if matches else None
    receipt = sorted((root / "estate").rglob("sandbox_receipt.json"))
    result["receipt_path"] = str(receipt[0]) if receipt else None
    if receipt:
        result["receipt"] = json.loads(receipt[0].read_text(encoding="utf-8"))
    return result


def summary(result: dict) -> None:
    print(f"\n=== lane {result['lane']} (--candidate-isolation {result['isolation']}) ===")
    print(f"rc={result['returncode']}")
    response = result.get("response") or {}
    if response:
        outcome = response.get("outcome") or response.get("handed_outcome") or {}
        print("response keys:", sorted(response))
        print("  status:", outcome.get("status"), "| cut_edges:", outcome.get("cut_edges"),
              "| failure:", outcome.get("failure_kind"))
        print("  isolation:", json.dumps(response.get("candidate_isolation")
                                        or response.get("isolation"))[:220])
    findings = result.get("findings")
    if not findings:
        print("  (no candidate findings captured)")
        return
    for key in ("handed_graph", "own_environment", "proc_environ", "proc_visible_pids",
                "partition_sweep", "bundle_archive_sweep", "witness_glob::*BURER2002*"):
        pass
    print("  handed_graph:", json.dumps(findings.get("handed_graph"))[:200])
    for key in sorted(findings):
        if key.startswith(("net_", "dns_")):
            print(f"  {key}: {json.dumps(findings[key])}")
    for key in ("witness_by_name", "targets_json", "witness_commitments", "suite_file",
                "suite_manifest", "generators_provenance", "credential_file",
                "credential_file_literal", "partition_sweep", "bundle_archive_sweep",
                "own_environment", "proc_environ", "proc_visible_pids",
                "proc::/proc/1/environ", "proc::/proc/self/root/home/ebt/gptapi.md",
                "git_show_head", "git_log_all", "git_rev_parse", "git_cat_file"):
        if key in findings:
            print(f"  {key}: {json.dumps(findings[key])[:300]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    lanes = [
        ("service", PROBE, "sandbox"),
        ("honest", HONEST, "sandbox"),
    ]
    if not args.quick:
        lanes.append(("none", PROBE, "none"))
        lanes.append(("host", PROBE, "host"))
    out = []
    for name, candidate, isolation in lanes:
        result = run_lane(name, candidate=candidate, isolation=isolation)
        out.append(result)
        summary(result)
    (HERE / "out_v2_closures.json").write_text(
        json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {HERE / 'out_v2_closures.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
