#!/usr/bin/env python3
"""Independently reproduce E* for C* and compare against the frozen E_STAR.json table.

Also runs the hostile-environment invariance probe (hostile cwd + poisoned PATH).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/home/ebt/rsi-dev/a0")
TP = ROOT / "tasks/circle-packing"
PY = TP / ".venv/bin/python"
E_STAR = TP / "e_star.py"
OUT = ROOT / "verify/out/e_star"


def run(candidate_dir: str, state_root: Path, cwd: Path | None = None, env: dict | None = None,
        timeout=180):
    out_json = state_root / "outcomes" / (Path(candidate_dir).name + ".json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    sd = state_root / (Path(candidate_dir).name + ".state")
    cmd = [str(PY), str(E_STAR), "evaluate", "--candidate", str(candidate_dir),
           "--seed", "1337", "--fidelity", "full", "--fraction", "1.0",
           "--out", str(out_json), "--state-dir", str(sd)]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=str(cwd) if cwd else str(TP), env=env)
    dt = time.time() - t0
    manifest = None
    for line in p.stdout.splitlines():
        if line.startswith("E_STAR_MANIFEST "):
            manifest = json.loads(line[len("E_STAR_MANIFEST "):])
    outcome = json.loads(out_json.read_text()) if out_json.exists() else None
    n_manifest_lines = sum(1 for l in p.stdout.splitlines() if l.startswith("E_STAR_MANIFEST "))
    return {"cmd": cmd, "exit": p.returncode, "manifest": manifest, "outcome": outcome,
            "stderr": p.stderr[-2000:], "stdout_tail": p.stdout[-1500:], "seconds": round(dt, 3),
            "n_manifest_lines": n_manifest_lines, "out_json": str(out_json)}


def main():
    table = json.loads((TP / "E_STAR.json").read_text())
    frozen = {c["candidate_id"]: c for c in table["candidates"]}
    wanted = sys.argv[1:] or sorted(frozen)
    results = []
    for cid in wanted:
        cand = f"C_STAR/{cid}"
        with tempfile.TemporaryDirectory(prefix="adversarial-e-star-") as td:
            r = run(cand, Path(td))
        f = frozen[cid]
        full = f.get("full", f)
        exp_status = f.get("expected_status_at_theta_e_star")
        exp_exit = f.get("exit_code")
        exp_digest = f.get("canonical_digest")
        got_status = r["manifest"]["status"] if r["manifest"] else None
        got_digest = r["manifest"]["canonical_digest"] if r["manifest"] else None
        got_obj = ((r["manifest"] or {}).get("objective") or {}).get("value")
        fr_obj = (f.get("objective") or {}).get("value")
        verdict = ("MATCH" if (r["exit"] == exp_exit and got_status == exp_status
                               and got_digest == exp_digest) else "MISMATCH")
        row = {"candidate_id": cid, "exit": r["exit"], "expected_exit": exp_exit,
               "status": got_status, "expected_status": exp_status,
               "canonical_digest": got_digest, "expected_digest": exp_digest,
               "objective": got_obj, "frozen_objective": fr_obj,
               "n_manifest_lines": r["n_manifest_lines"], "seconds": r["seconds"],
               "verdict": verdict, "outcome_status": (r["outcome"] or {}).get("status"),
               "outcome_fields": ((r["outcome"] or {}).get("outcome", {}) or {}).get("fields"),
               }
        results.append(row)
        print(f"[{verdict:8}] {cid:<26} exit={r['exit']}(exp {exp_exit}) "
              f"status={got_status} digest_ok={got_digest == exp_digest} "
              f"manifest_lines={r['n_manifest_lines']} obj={got_obj} t={r['seconds']}s")
        if verdict == "MISMATCH":
            print("   stderr:", r["stderr"][:600])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reproduce_results.json").write_text(json.dumps(results, indent=2))
    bad = [r for r in results if r["verdict"] != "MATCH"]
    print(f"\n{len(results) - len(bad)}/{len(results)} reproduced; mismatches: {[b['candidate_id'] for b in bad]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
