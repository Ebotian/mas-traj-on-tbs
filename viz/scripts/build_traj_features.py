#!/usr/bin/env python3
"""build_traj_features.py — 把 2026-10-14 夜班「轨迹特征数值实验」的产物投影成站点数据。

输入(仓库内,已提交):
  harness/refs/traj-features-2026-10-14/
    features_sides.jsonl · features_runs.jsonl · features_arms.jsonl · selection_features.json
输出:
  viz/src/data/traj_features.json(确定性;不含墙钟;供 #/features 视图 import)

用法:python3 viz/scripts/build_traj_features.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent          # viz/scripts
ROOT = HERE.parent.parent                       # 仓库根
SRC = ROOT / "harness" / "refs" / "traj-features-2026-10-14"
OUT = HERE.parent / "src" / "data" / "traj_features.json"
KINDS = ["read", "write", "search", "exec", "wait", "test", "recover", "other"]
FAM_ORDER = ["walkthrough", "tumor", "microarch", "tess"]


def jl(name: str) -> list:
    p = SRC / name
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def med(xs: list):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2, 6)


def main() -> int:
    sides = jl("features_sides.jsonl")
    runs = jl("features_runs.jsonl")
    arms = jl("features_arms.jsonl")
    sel = json.loads((SRC / "selection_features.json").read_text(encoding="utf-8"))

    fam: dict = {}
    for s in sides:
        f = fam.setdefault(s["family"], {"name": s["family"], "sides": 0, "calls": 0, "masked": 0,
                                         "kinds": {k: 0 for k in KINDS}, "cache": [], "span": [],
                                         "kind_ent": [], "trans_ent": []})
        f["sides"] += 1
        f["calls"] += s.get("calls_total") or 0
        f["masked"] += s.get("masked") or 0
        for k, v in (s.get("kinds") or {}).items():
            key = k if k in f["kinds"] else "other"
            f["kinds"][key] += v
        if s.get("cache_ratio") is not None:
            f["cache"].append(s["cache_ratio"])
        if s.get("span_s") is not None:
            f["span"].append(s["span_s"])
        if s.get("kind_entropy") is not None:
            f["kind_ent"].append(s["kind_entropy"])
        if s.get("transition_entropy") is not None:
            f["trans_ent"].append(s["transition_entropy"])
    runs_by_fam: dict = {}
    for r in runs:
        runs_by_fam[r["family"]] = runs_by_fam.get(r["family"], 0) + 1
    families = []
    for name in sorted(fam, key=lambda n: (FAM_ORDER.index(n) if n in FAM_ORDER else 99, n)):
        f = fam[name]
        families.append({"name": name, "runs": runs_by_fam.get(name, 0), "sides": f["sides"],
                         "calls": f["calls"], "masked": f["masked"], "kinds": f["kinds"],
                         "cache_med": med(f["cache"]), "span_med": med(f["span"]),
                         "kind_ent_med": med(f["kind_ent"]), "trans_ent_med": med(f["trans_ent"])})

    side_rows = [{"job": s["job"], "family": s["family"], "side": s["side"],
                  "calls": s.get("calls_total"), "masked": s.get("masked"),
                  "masked_rate": s.get("masked_rate"), "cache_ratio": s.get("cache_ratio"),
                  "span_s": s.get("span_s"), "gap_med_s": s.get("gaps_median_s"),
                  "cv": s.get("gaps_cv_robust"), "p600": s.get("gaps_p600_frac"),
                  "kind_entropy": s.get("kind_entropy"), "transition_entropy": s.get("transition_entropy"),
                  "kinds": s.get("kinds")} for s in sides]

    run_rows = []
    for r in runs:
        sd = r.get("sides") or {}
        a = sd.get("a") or {}
        b = sd.get("b") or {}
        rounds = r.get("rounds") or {}
        gt = r.get("gate_tokens") or {}
        run_rows.append({"job": r["job"], "family": r["family"], "calls": r.get("calls_total"),
                         "masked": r.get("masked_total"), "cache_a": a.get("cache_ratio"),
                         "cache_b": b.get("cache_ratio"), "span_a": a.get("span_s"),
                         "span_b": b.get("span_s"), "rounds_a": rounds.get("a"),
                         "rounds_b": rounds.get("b"), "normal": r.get("normal"),
                         "gate_ok": gt.get("refs-ok"), "gate_block": gt.get("block")})
    arm_rows = [{"job": a["job"], "schema": a.get("schema_version"), "steps": a.get("steps"),
                 "calls": a.get("calls_total"), "masked": a.get("masked")} for a in arms]

    arms_calls = sum(a["calls"] or 0 for a in arm_rows)
    arms_masked = sum(a["masked"] or 0 for a in arm_rows)
    t1 = next((r for r in run_rows if r["job"] == "tumor-1"), {})
    invariants = [
        {"name": "arms 调用", "value": arms_calls, "want": 728, "ok": arms_calls == 728},
        {"name": "arms 掩蔽", "value": arms_masked, "want": 26, "ok": arms_masked == 26},
        {"name": "tumor-1 调用", "value": t1.get("calls"), "want": 430, "ok": t1.get("calls") == 430},
        {"name": "选择面候选", "value": sel.get("candidates_total"), "want": 143,
         "ok": sel.get("candidates_total") == 143},
        {"name": "local−hidden τ 差", "value": sel.get("local_vs_hidden_tau_gap"), "want": 0.277174,
         "ok": sel.get("local_vs_hidden_tau_gap") == 0.277174},
    ]

    surf = []
    for name in sorted(sel.get("surfaces") or {}):
        s = sel["surfaces"][name]
        surf.append({"name": name.replace(".json", ""), "n": s.get("n"),
                     "tau_min": s.get("loco_tau_min"), "tau_med": s.get("loco_tau_med"),
                     "tau_max": s.get("loco_tau_max"), "regret_pos": s.get("n_loco_regret_pos"),
                     "regret_max": s.get("loco_regret_max")})

    data = {
        "meta": {"source": "harness/refs/traj-features-2026-10-14/"
                           "(features_sides|runs|arms.jsonl + selection_features.json)",
                 "script": "viz/scripts/build_traj_features.py",
                 "note": "夜班轨迹特征数值实验(确定性、零模型调用;check.py 全 PASS)。定义见 refs/README.md。"},
        "totals": {"runs": len(run_rows), "sides": len(side_rows), "arms": len(arm_rows),
                   "calls": sum(s["calls"] or 0 for s in side_rows),
                   "masked": sum(s["masked"] or 0 for s in side_rows),
                   "arms_calls": arms_calls, "arms_masked": arms_masked},
        "families": families, "runs": run_rows, "sides": side_rows, "arms": arm_rows,
        "invariants": invariants,
        "selection": {"run": sel.get("run"), "candidates_total": sel.get("candidates_total"),
                      "picked_union": sel.get("picked_distinct_union"),
                      "emax_sigma05": sel.get("emax_eps_sigma05_hypothetical"),
                      "blend": sel.get("blend"), "hidden": sel.get("hidden"),
                      "gap": sel.get("local_vs_hidden_tau_gap"), "surfaces": surf,
                      "pool_preds": sel.get("pool_preds")},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    t = data["totals"]
    print(f"wrote {OUT}")
    print(f"runs={t['runs']} sides={t['sides']} arms={t['arms']} "
          f"dual calls={t['calls']} masked={t['masked']} | arms {t['arms_calls']}/{t['arms_masked']}")
    for f in families:
        print(f"  {f['name']}: runs={f['runs']} sides={f['sides']} calls={f['calls']} masked={f['masked']} "
              f"cache_med={f['cache_med']} kinds={f['kinds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
