#!/usr/bin/env python3
"""check.py — determinism + invariant gate for the 2026-10-14 trajectory-feature
numerical experiment.

1) Re-runs extract.py into a temp dir and byte-compares all four outputs with
   the copies next to this script (determinism gate).
2) Re-asserts the pinned invariants over the extracted records:
   - arms (single-agent ATIF): calls_total == 728 and masked == 26
   - tumor-1 (twin): calls_total == 430

Exit 0 = PASS (all outputs identical + invariants hold).

Usage: python3 check.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTS = ["features_sides.jsonl", "features_runs.jsonl", "features_arms.jsonl", "summary.md"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            [sys.executable, str(HERE / "extract.py"), "--out", td],
            capture_output=True, text=True,
        )
        print(r.stdout.strip())
        if r.returncode != 0:
            print("extract.py failed:", r.stderr[-2000:])
            return 2
        for name in OUTS:
            a, b = HERE / name, Path(td) / name
            if not a.exists() or not b.exists():
                print(f"MISSING {name}")
                ok = False
                continue
            same = sha(a) == sha(b)
            print(f"{name}: {'IDENTICAL' if same else 'DIFF'} ({sha(a)[:12]})")
            ok = ok and same

    arms = [json.loads(l) for l in (HERE / "features_arms.jsonl").read_text().splitlines() if l.strip()]
    calls = sum(a["calls_total"] for a in arms)
    mask = sum(a["masked"] for a in arms)
    inv = [("arms.calls_total", calls, 728), ("arms.masked", mask, 26)]
    runs = [json.loads(l) for l in (HERE / "features_runs.jsonl").read_text().splitlines() if l.strip()]
    t1 = next((r for r in runs if r["job"] == "tumor-1"), None)
    if t1 is not None:
        inv.append(("tumor-1.calls_total", t1.get("calls_total"), 430))
    for name, got, want in inv:
        good = got == want
        print(f"INVARIANT {name} = {got} (want {want}) {'OK' if good else 'FAIL'}")
        ok = ok and good
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
