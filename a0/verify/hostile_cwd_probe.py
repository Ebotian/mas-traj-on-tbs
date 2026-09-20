#!/usr/bin/env python3
"""Hostile-environment invariance probe for E* (cwd + PATH).

Claim under attack: "evaluator 不得依赖 cwd 或 PATH" (plan:533-537).

Three variants, each scored by E*'s own canonical_digest against the clean control:
  A  hostile cwd (decoys: solution.py, e_star.py, e_star_child.py, C_STAR/c01_good_hex/solution.py)
     + PATH whose first entry is a shim dir of fake `python`/`python3`/`sh`/`bash`/`env`/`git`
  B  A + PYTHONPATH pointing at the hostile cwd (sitecustomize trap)  -- beyond the stated claim
  C  hostile cwd with a *relative* candidate path  -- documented expectation: resolves in cwd
Checks that no shim executed and that E* wrote nothing into the hostile cwd.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/ebt/rsi-dev/a0")
TP = ROOT / "tasks/circle-packing"
PY = TP / ".venv/bin/python"
E_STAR = TP / "e_star.py"
CAND = TP / "C_STAR/c01_good_hex"
REAL_SHA = "bca4286ed3b15035675f3f2bb2ed0ac8b9e53649f370bf3e5768b5105e3f4a6d"
CLEAN_DIGEST = "1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8"

SHIM = '#!/bin/sh\necho "SHIM $0 $@" >> "$SENTINEL"\nexit 127\n'
DECOY_SOLUTION = 'def pack_circles(n):\n    raise RuntimeError("DECOY")\n'
DECOY_E_STAR = 'import json,sys\nprint("E_STAR_MANIFEST "+json.dumps({"status":"ok","objective":{"value":999.0}}))\nsys.exit(0)\n'
SITECUSTOMIZE = 'import os\no=os.environ.get("SENTINEL")\n' \
                'open(o,"a").write("SITECUSTOMIZE_IN_CWD\\n") if o else None\n'


def build(tdp: Path):
    cwd = tdp / "cwd"
    shim = tdp / "shim"
    cwd.mkdir()
    shim.mkdir()
    sentinel = tdp / "sentinel.log"
    sentinel.write_text("")
    (cwd / "solution.py").write_text(DECOY_SOLUTION)
    (cwd / "e_star.py").write_text(DECOY_E_STAR)
    (cwd / "e_star_child.py").write_text("raise SystemExit('decoy child')\n")
    (cwd / "sitecustomize.py").write_text(SITECUSTOMIZE)
    d = cwd / "C_STAR/c01_good_hex"
    d.mkdir(parents=True)
    (d / "solution.py").write_text(DECOY_SOLUTION)
    (d / "candidate.json").write_text('{"id":"DECOY"}')
    for name in ("python", "python3", "sh", "bash", "env", "uname", "git", "node", "uv"):
        p = shim / name
        p.write_text(SHIM)
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return cwd, shim, sentinel


def snapshot(d: Path):
    return sorted(str(p.relative_to(d)) for p in d.rglob("*"))


def main():
    results = {}
    with tempfile.TemporaryDirectory(prefix="hostile-") as td:
        tdp = Path(td)
        cwd, shim, sentinel = build(tdp)
        before = snapshot(cwd)
        base_env = {k: v for k, v in os.environ.items() if k in ("LANG",)}
        base_env["PATH"] = f"{shim}:{os.environ.get('PATH','')}"
        base_env["SENTINEL"] = str(sentinel)

        def go(tag, env, candidate, cwd_used):
            out = tdp / f"out-{tag}.json"
            cmd = [str(PY), str(E_STAR), "evaluate", "--candidate", candidate,
                   "--seed", "1337", "--fidelity", "full", "--fraction", "1.0",
                   "--out", str(out), "--state-dir", str(tdp / f"state-{tag}")]
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd_used),
                               env=env, timeout=180)
            man = None
            for line in p.stdout.splitlines():
                if line.startswith("E_STAR_MANIFEST "):
                    man = json.loads(line[len("E_STAR_MANIFEST "):])
            o = json.loads(out.read_text()) if out.exists() else None
            return {"exit": p.returncode, "manifest": man, "outcome": o,
                    "stderr": p.stderr[-400:], "cmd": cmd}

        # control
        ctrl = go("ctrl", {**base_env, "PATH": os.environ.get("PATH", ""),
                           "SENTINEL": str(sentinel)},
                  str(CAND), TP)
        results["control"] = {"digest": (ctrl["manifest"] or {}).get("canonical_digest"),
                              "objective": (ctrl["manifest"] or {}).get("objective"),
                              "exit": ctrl["exit"]}

        results["A_hostile_cwd_path"] = go("A", base_env, str(CAND), cwd)

        envB = dict(base_env)
        envB["PYTHONPATH"] = str(cwd)
        envB["HOME"] = str(cwd)
        envB["TMPDIR"] = str(cwd)
        results["B_plus_pythonpath"] = go("B", envB, str(CAND), cwd)

        results["C_relative_candidate"] = go("C", base_env, "C_STAR/c01_good_hex", cwd)

        sentinel_text = sentinel.read_text()
        after = snapshot(cwd)
        new_files = sorted(set(after) - set(before))

    out = {}
    for k, r in results.items():
        if k == "control":
            out[k] = r
            continue
        m = r["manifest"] or {}
        o = r["outcome"] or {}
        out[k] = {
            "exit": r["exit"],
            "canonical_digest": m.get("canonical_digest"),
            "objective": m.get("objective"),
            "status": m.get("status"),
            "digest_equals_control": m.get("canonical_digest") == results["control"]["digest"],
            "objective_equals_control": m.get("objective") == results["control"]["objective"],
            "candidate_source_sha256": (o.get("candidate") or {}).get("source_sha256"),
            "used_real_candidate": (o.get("candidate") or {}).get("source_sha256") == REAL_SHA,
            "stderr": r["stderr"],
        }
    out["sentinel_log"] = sentinel_text
    out["shim_never_executed"] = "SHIM" not in sentinel_text
    out["new_files_in_hostile_cwd"] = new_files
    out["wrote_nothing_to_cwd"] = new_files == []

    v = out
    verdict = {
        "A_invariant": v["A_hostile_cwd_path"]["digest_equals_control"]
                       and v["A_hostile_cwd_path"]["used_real_candidate"],
        "B_invariant": v["B_plus_pythonpath"]["digest_equals_control"]
                       and v["B_plus_pythonpath"]["used_real_candidate"],
        "no_shim_executed": v["shim_never_executed"],
        "cwd_untouched": v["wrote_nothing_to_cwd"],
    }
    out["verdict"] = verdict
    (ROOT / "verify/out/hostile_cwd.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("\nVERDICT:", json.dumps(verdict))
    return 0 if all(verdict.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
