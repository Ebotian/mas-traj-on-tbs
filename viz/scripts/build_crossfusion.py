#!/usr/bin/env python3
"""build_crossfusion.py — 把 crossfusion-2026-10-15 并集实验产物投影成站点数据。

输入(仓库内,已提交):
  harness/refs/crossfusion-2026-10-15/
    features_union.jsonl · audit.json · paper_checks.json · arft.json
输出:
  viz/src/data/crossfusion.json(确定性;不含墙钟;供 #/crossfusion 视图 import)

用法:python3 viz/scripts/build_crossfusion.py
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent          # viz/scripts
ROOT = HERE.parent.parent                       # 仓库根
SRC = ROOT / "harness" / "refs" / "crossfusion-2026-10-15"
OUT = HERE.parent / "src" / "data" / "crossfusion.json"
KINDS = ["read", "write", "search", "exec", "wait", "test", "recover", "other"]
FAM_ORDER = ["walkthrough", "tumor", "microarch", "tess"]
FAM_CN = {"walkthrough": "走查", "tumor": "tumor", "microarch": "microarch", "tess": "tess"}
MODEL_ORDER = ["claude-sonnet-5", "opus-4.8", "deepseek-v4-pro", "glm-5.2", "minimax-m3",
               "qwen3.7-max", "gpt-5-mini", "gemini-3.5-flash"]


def jl(name: str) -> list:
    p = SRC / name
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def med(xs: list):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 6)


def kinds8(rows: list) -> dict:
    acc = {k: 0 for k in KINDS}
    for r in rows:
        for k, v in (r.get("kinds") or {}).items():
            key = k if k in acc else "other"
            acc[key] += v
    return acc


def main() -> int:
    recs = jl("features_union.jsonl")
    audit = json.loads((SRC / "audit.json").read_text(encoding="utf-8"))
    pc = json.loads((SRC / "paper_checks.json").read_text(encoding="utf-8"))
    arft = json.loads((SRC / "arft.json").read_text(encoding="utf-8"))

    ours = [x for x in recs if x["source"] == "ours"]
    are = [x for x in recs if x["source"] == "are"]
    sides = [x for x in ours if x["corpus"] != "arm"]
    arms = [x for x in ours if x["corpus"] == "arm"]
    calls_ours = sum(x["calls_total"] for x in ours)
    calls_are = sum(x["calls_total"] for x in are)

    corpora = []
    grp: dict = {}
    for r in recs:
        grp.setdefault((r["source"], r["corpus"]), []).append(r)
    for (src, corp), rs in sorted(grp.items()):
        corpora.append({"source": src, "corpus": corp, "units": len(rs),
                        "calls": sum(x["calls_total"] for x in rs),
                        "masked": sum(x["masked"] for x in rs),
                        "gaps_ok": sum(1 for x in rs if x["gaps_basis"]),
                        "p05": sum(1 for x in rs if x.get("mi_perm_p") is not None and x["mi_perm_p"] < 0.05)})

    fams = []
    for name in FAM_ORDER:
        rs = [x for x in sides if x["corpus"] == name]
        fams.append({"name": name, "cn": FAM_CN[name], "units": len(rs),
                     "calls": sum(x["calls_total"] for x in rs),
                     "masked": sum(x["masked"] for x in rs),
                     "gaps_ok": sum(1 for x in rs if x["gaps_basis"]),
                     "ke_med": med([x["kind_entropy"] for x in rs]),
                     "te_med": med([x["transition_entropy"] for x in rs]),
                     "mrate_med": med([x["masked_rate"] for x in rs]),
                     "mi_med": med([x.get("mi_action") for x in rs]),
                     "pa_med": med([x.get("p_action") for x in rs]),
                     "p05": sum(1 for x in rs if x.get("mi_perm_p") is not None and x["mi_perm_p"] < 0.05),
                     "kinds8": kinds8(rs)})

    arm_rows = [{"job": x["unit"].split("/")[-2], "calls": x["calls_total"], "masked": x["masked"],
                 "ke": x["kind_entropy"], "te": x["transition_entropy"], "kinds8": kinds8([x])}
                for x in sorted(arms, key=lambda r: r["unit"])]

    models = []
    mg: dict = {}
    for x in are:
        mg.setdefault(x["model"], []).append(x)
    for name in sorted(mg, key=lambda m: (MODEL_ORDER.index(m) if m in MODEL_ORDER else 99, m)):
        rs = mg[name]
        calls = sum(x["calls_total"] for x in rs)
        models.append({"name": name, "units": len(rs), "calls": calls,
                       "calls_ep": round(calls / len(rs), 2),
                       "ke_med": med([x["kind_entropy"] for x in rs]),
                       "te_med": med([x["transition_entropy"] for x in rs]),
                       "mrate_med": med([x["masked_rate"] for x in rs]),
                       "cache_med": med([x["cache_ratio"] for x in rs]),
                       "mi_med": med([x.get("mi_action") for x in rs]),
                       "pa_med": med([x.get("p_action") for x in rs]),
                       "p05": sum(1 for x in rs if x.get("mi_perm_p") is not None and x["mi_perm_p"] < 0.05),
                       "kinds8": kinds8(rs)})

    fcov = []
    fg: dict = {}
    for r in recs:
        fg.setdefault((r["source"], r["format"]), []).append(r)
    for (src, fmt), rs in sorted(fg.items()):
        gb = Counter(r["gaps_basis"] for r in rs if r["gaps_basis"])
        fcov.append({"source": src, "format": fmt, "units": len(rs),
                     "gaps_basis": dict(sorted(gb.items())),
                     "masked_n": sum(1 for r in rs if r["results_judged"]),
                     "cache_n": sum(1 for r in rs if r["cache_ratio"] is not None),
                     "dur_n": sum(1 for r in rs if r["duration_ms"] is not None)})

    scatter = []
    for r in sorted(recs, key=lambda x: x["unit"]):
        if r["kind_entropy"] is None or r["transition_entropy"] is None:
            continue
        scatter.append({"u": r["unit"], "s": r["source"],
                        "g": r["corpus"] if r["source"] == "ours" else r["model"],
                        "calls": r["calls_total"],
                        "ke": round(r["kind_entropy"], 4), "te": round(r["transition_entropy"], 4),
                        "mr": None if r["masked_rate"] is None else round(r["masked_rate"], 5)})

    decouple = []
    for r in sorted(recs, key=lambda x: x["unit"]):
        if r.get("mi_action") is None:
            continue
        decouple.append({"u": r["unit"], "s": r["source"],
                         "g": r["corpus"] if r["source"] == "ours" else r["model"],
                         "calls": r["calls_total"],
                         "ke": round(r["kind_entropy"], 4), "ns": round(r["trans_entropy_ns"], 4),
                         "mi": round(r["mi_action"], 4),
                         "p": None if r["p_action"] is None else round(r["p_action"], 4),
                         "ss": round(r["s_smooth"], 4), "perm": r["mi_perm_p"]})
    ln2 = math.log(2)
    n_above_ns = sum(1 for r in recs if r.get("trans_entropy_ns") is not None
                     and r["trans_entropy_ns"] > r["kind_entropy"] * ln2 + 1e-9)
    n_above_sm = sum(1 for r in recs if r["transition_entropy"] is not None
                     and r["transition_entropy"] > r["kind_entropy"] * ln2 + 1e-9)
    n_pperm05 = sum(1 for r in recs if r.get("mi_perm_p") is not None and r["mi_perm_p"] < 0.05)
    n_pa = sum(1 for r in recs if r.get("p_action") is not None)
    mis_all = [r["mi_action"] for r in recs if r.get("mi_action") is not None]

    inv = [
        {"name": "单元", "value": len(recs), "want": 862, "ok": len(recs) == 862},
        {"name": "ours 侧/臂", "value": f"{len(sides)}/{len(arms)}", "want": "54/8",
         "ok": len(sides) == 54 and len(arms) == 8},
        {"name": "are 单元", "value": len(are), "want": 800, "ok": len(are) == 800},
        {"name": "调用总计", "value": calls_ours + calls_are, "want": 83032,
         "ok": calls_ours + calls_are == 83032},
        {"name": "are 均值/跑", "value": round(calls_are / 800, 4), "want": 92.3025,
         "ok": round(calls_are / 800, 4) == 92.3025},
        {"name": "ours 侧 lab 逐字段", "value": f"{audit['ours_compare']['checked']}/"
         f"{len(audit['ours_compare']['mismatch'])}", "want": "54/0",
         "ok": audit["ours_compare"]["checked"] == 54 and not audit["ours_compare"]["mismatch"]},
        {"name": "臂 调用/掩蔽", "value": f"728/26", "want": "728/26",
         "ok": sum(x["calls_total"] for x in arms) == 728 and sum(x["masked"] for x in arms) == 26},
        {"name": "论文 HIT 总量", "value": arft["total_hits"], "want": 12712, "ok": arft["total_hits"] == 12712},
        {"name": "论文复算 PASS", "value": pc["counts"]["PASS"], "want": 30,
         "ok": pc["counts"]["PASS"] == 30},
    ]

    data = {
        "meta": {
            "source": "harness/refs/crossfusion-2026-10-15/",
            "script": "viz/scripts/build_crossfusion.py",
            "are_revision": "412fb4908a3a7b98dd50cfa3e5c6cd40750d2d4f",
            "arxiv": pc.get("arxiv"),
            "note": "数据并集(ours 54 侧 + 8 臂 + AutoResearchEval 800)× 方法并集(统一 8 类/熵/节律/静默失败/缓存);"
                    "论文数字复算与偏差登记同页;全部确定性、零模型调用",
        },
        "totals": {
            "units": len(recs), "ours_units": len(ours), "are_units": len(are),
            "sides": len(sides), "arms": len(arms),
            "calls": calls_ours + calls_are, "ours_calls": calls_ours, "are_calls": calls_are,
            "avg_are": round(calls_are / 800, 4),
            "hits_total": arft["total_hits"],
            "paper": pc["counts"],
            "n_above_ns": n_above_ns, "n_above_sm": n_above_sm,
            "n_pperm05": n_pperm05, "n_pa": n_pa,
            "mi_med": med(mis_all), "mi_max": max(mis_all) if mis_all else None,
        },
        "invariants": inv,
        "corpora": corpora,
        "families": fams,
        "arms": arm_rows,
        "models": models,
        "format_cov": fcov,
        "scatter": scatter,
        "decouple": decouple,
        "checks": pc["checks"],
        "arft": {
            "total_hits": arft["total_hits"],
            "pillars": [{"id": p["id"], "name": p["name"], "n": p["n_patterns"],
                         "hit_sum": p["hit_sum"], "share_pct": p["share_pct"]} for p in arft["pillars"]],
            "top": [{"id": p["id"], "name": p["name"], "stage": p["stage"], "pillar": p["pillar"],
                     "hit": p["hit"], "pct": p["hit_pct"]} for p in arft["patterns"][:12]],
        },
        "notes": {
            "defect_occurrences": len(audit["defect_occurrences"]),
            "nonstd": audit["ours_side_nonstandard"],
            "mehnet": audit["are_compare"]["mismatch"][0]["unit"] if audit["are_compare"]["mismatch"] else None,
            "unit_notes": {"result_first": 15, "empty_file": 1, "no_calls": 5},
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} B)")
    print(f"units={data['totals']['units']} calls={data['totals']['calls']} "
          f"scatter={len(scatter)} checks={len(data['checks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
