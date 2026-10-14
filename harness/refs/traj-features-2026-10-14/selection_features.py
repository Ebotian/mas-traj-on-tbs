#!/usr/bin/env python3
"""selection-features (v2 companion, exploratory) — selection-process audit for
microarch-5 from its collected protocol bundle.

Inputs (read-only, deterministic, zero model calls):
  - microarch-5 top-level collect/protocol.bundle: analysis/*.json selection
    surfaces (p1_ladder, p1_terms, p1_variants, p2_window, p3_final_sel,
    r2_combine, v3_sel, blend), pool_spec.json, pool_preds.npy
  - the trial's verifier/test-stdout.txt (hidden truth triple)

Output: selection_features.json (next to this script) + a printed table.

Scope note: the m3/m4 bundles carry NO analysis/ materials (checked), so v2 is
n=1 (m5) — an exploratory slice of the A-stratum (validation-reuse /
selection-fragility), not a corpus-level statistic. Definitions live here.

Usage: python3 selection_features.py [--bundle P] [--verifier D] [--out DIR]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import struct
import subprocess
from pathlib import Path

DEF_BUNDLE = ("/home/ebt/harbor-runs/jobs/agent/microarch-5/task-microarch__NjyxpAy/"
              "artifacts/root/wt/collect/protocol.bundle")
DEF_VERIFIER = ("/home/ebt/harbor-runs/jobs/agent/microarch-5/task-microarch__NjyxpAy/"
                "verifier")
SURFACES = ["analysis/p1_ladder.json", "analysis/p1_terms.json",
            "analysis/p1_variants.json", "analysis/p2_window.json",
            "analysis/p3_final_sel.json", "analysis/r2_combine.json",
            "analysis/v3_sel.json"]


def git_show(repo: str, path: str):
    r = subprocess.run(["git", "-C", repo, "show", f"main:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def load_json(repo: str, path: str):
    s = git_show(repo, path)
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def entries_of(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [v for v in obj.values() if isinstance(v, dict)]
    return []


def surface_stats(entries):
    locos = [e.get("loco") or {} for e in entries]
    taus = [x.get("tau_mean") for x in locos if isinstance(x.get("tau_mean"), (int, float))]
    mapes = [x.get("mape") for x in locos if isinstance(x.get("mape"), (int, float))]
    regrets = [x.get("regret") for x in locos if isinstance(x.get("regret"), (int, float))]
    pairs = [(x.get("picked"), x.get("best")) for x in locos if x.get("picked")]
    regret_pos = sum(1 for r in regrets if r > 1e-12)
    return {
        "n": len(entries),
        "loco_tau_min": min(taus) if taus else None,
        "loco_tau_med": sorted(taus)[len(taus) // 2] if taus else None,
        "loco_tau_max": max(taus) if taus else None,
        "loco_mape_min": min(mapes) if mapes else None,
        "loco_regret_max": max(regrets) if regrets else None,
        "n_loco_regret_pos": regret_pos,
        "picked_distinct": sorted({p for p, _ in pairs}),
        "picked_eq_best_frac": (round(sum(1 for p, b in pairs if p == b) / len(pairs), 4)
                                if pairs else None),
    }


def npy_from_bytes(b: bytes):
    if b[:6] != b"\x93NUMPY":
        return None
    major = b[6]
    if major == 1:
        hlen = struct.unpack("<H", b[8:10])[0]
        header = b[10:10 + hlen].decode("latin-1")
    else:
        hlen = struct.unpack("<I", b[8:12])[0]
        header = b[12:12 + hlen].decode("latin-1")
    meta = ast.literal_eval(header.strip())
    n = 1
    for d in meta["shape"]:
        n *= d
    descr = meta["descr"]
    c = {"<f4": "f", "<f8": "d", "|f4": "f", "|f8": "d"}.get(descr)
    if c is None:
        return {"shape": meta["shape"], "descr": descr, "note": "unsupported dtype"}
    body = b[10 + hlen:] if major == 1 else b[12 + hlen:]
    size = struct.calcsize("<" + c)
    vals = struct.unpack("<" + c * n, body[: n * size])
    imax = max(range(n), key=lambda i: vals[i])
    return {"shape": list(meta["shape"]), "descr": descr,
            "v_min": min(vals), "v_max": max(vals), "argmax": imax}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=DEF_BUNDLE)
    ap.add_argument("--verifier", default=DEF_VERIFIER)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sel-feat-")
    repo = str(Path(tmp) / "repo")
    subprocess.run(["git", "clone", "-q", "--bare", args.bundle, repo], check=True)
    rec: dict = {"run": "microarch-5", "source": "protocol.bundle@main", "surfaces": {}}
    total_entries = 0
    all_picked = []
    for s in SURFACES:
        obj = load_json(repo, s)
        if obj is None:
            continue
        ents = entries_of(obj)
        st = surface_stats(ents)
        rec["surfaces"][s.split("/")[-1]] = st
        total_entries += st["n"]
        all_picked += st["picked_distinct"]
    rec["candidates_total"] = total_entries
    rec["picked_distinct_union"] = sorted(set(all_picked))
    # doc-formula reference at hypothetical sigma (cliodynamics Hill-style bound):
    # E[max eps] <= sigma * sqrt(2 ln K); sigma=0.05 is the doc's illustrative value.
    import math
    if total_entries > 1:
        rec["emax_eps_sigma05_hypothetical"] = round(0.05 * math.sqrt(2 * math.log(total_entries)), 4)

    blend = load_json(repo, "analysis/blend.json")
    if isinstance(blend, dict):
        def mini(x):
            if not isinstance(x, dict):
                return x
            return {"tau_mean": x.get("tau_mean"), "regret": x.get("regret"),
                    "picked": x.get("picked"), "best": x.get("best"), "mape": x.get("mape")}
        rec["blend"] = {k: mini(blend.get(k)) for k in sorted(blend)}

    spec = load_json(repo, "analysis/pool_spec.json")
    if isinstance(spec, dict):
        rec["pool_spec"] = {"variants": spec.get("variants"), "pool_n": len(spec.get("pool") or [])}

    raw = subprocess.run(["git", "-C", repo, "show", "main:analysis/pool_preds.npy"],
                         capture_output=True).stdout
    np_meta = npy_from_bytes(raw) if raw else None
    if np_meta:
        rec["pool_preds"] = np_meta

    tout = Path(args.verifier) / "test-stdout.txt"
    if tout.exists():
        text = tout.read_text(errors="replace")
        m = re.search(r"'ipc_mape':\s*([0-9.eE+-]+).*?'mean_workload_kendall_tau':\s*([0-9.eE+-]+)"
                      r".*?'top_1_regret':\s*([0-9.eE+-]+)", text, re.S)
        if m:
            rec["hidden"] = {"ipc_mape": float(m.group(1)),
                             "mean_workload_kendall_tau": float(m.group(2)),
                             "top_1_regret": float(m.group(3))}
            for k, v in (("true_best_design", r"'true_best_design':\s*'([^']+)'"),
                         ("predicted_best_design", r"'predicted_best_design':\s*'([^']+)'")):
                mm = re.search(v, text)
                if mm:
                    rec["hidden"][k] = mm.group(1)
            a = (rec.get("blend") or {}).get("a_loco") or {}
            if isinstance(a.get("tau_mean"), (int, float)):
                rec["local_vs_hidden_tau_gap"] = round(a["tau_mean"] - rec["hidden"]["mean_workload_kendall_tau"], 6)

    (out / "selection_features.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"surfaces: {len(rec['surfaces'])} | candidates_total={rec['candidates_total']}")
    for name, st in sorted(rec["surfaces"].items()):
        print(f"  {name:22s} n={st['n']:3d} loco_tau[{st['loco_tau_min']},{st['loco_tau_med']},{st['loco_tau_max']}] "
              f"regret_pos={st['n_loco_regret_pos']} max_regret={st['loco_regret_max']}")
    print("picked union:", rec["picked_distinct_union"])
    if "blend" in rec:
        b = rec["blend"]
        print("blend:", {k: (b[k].get("tau_mean"), b[k].get("regret")) if isinstance(b[k], dict) else b[k] for k in b})
    if "hidden" in rec:
        print("hidden:", rec["hidden"], "| local-vs-hidden tau gap:", rec.get("local_vs_hidden_tau_gap"))
    if "pool_preds" in rec:
        print("pool_preds:", rec["pool_preds"])
    shutil.rmtree(tmp, ignore_errors=True)
    print("written:", out / "selection_features.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
