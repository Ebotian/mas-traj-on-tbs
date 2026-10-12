#!/usr/bin/env python3
# build_process.py — 过程观测后端:对 jobs/agent 全部已采集跑次做只读审计,
# 产出 viz/src/data/process.json(前缀级序列 + 池账本 + 门决策账本)。
#
# 吸收自 EarlyEval 的观测设计(前缀化视图 / 统一特征 / 决策-记账分离),只观测不截断:
#   · 截尾账本:若结局在 k% 步已知,能省多少 out/uncached/cache/墙钟(完美停上限);
#   · 上下文增长:每步 prompt 中位数(为什么尾贵);
#   · 停/收口信号:abort/stop/recover 与判决的对照;
#   · 门决策账本:gate.log 各类判定计数 + refs-block→修复闭环(拒绝精度);
#   · 逐跑前缀级序列(每条单侧轨迹的逐步 cache/unc/out/gap),供前端探索。
#
# 口径与 tasks/walkthrough/metrics.py 同源:
#   uncached = prompt - cached ; cache = cached ; out = candidates + thoughts;
#   A 侧 deepseek-flash USD/M(峰值×2 周一至五 01–04/06–10 UTC);B 侧 qwen3.8-flash CNY/M。
# 用法: python3 viz/scripts/build_process.py   (由 refresh_replays.sh 末尾自动调用)
import json, re, datetime, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOBS = Path("/home/ebt/harbor-runs/jobs/agent")
OUT = HERE.parent / "src" / "data" / "process.json"

RATE_A_OFF = {"uncached": 0.15, "cache": 0.003, "out": 0.60}
RATE_A_PEAK = {"uncached": 0.30, "cache": 0.006, "out": 1.20}
RATE_B = {"uncached": 0.8, "cache": 0.1, "out": 2.7}

# job -> (exp, label) 与 refresh_replays.sh 的 SRC/LABEL 对齐(w7/w8 为 v3 全链 E2E)
EXP = {
    "bump-0251-flow": ("bump0251", "bump-0251-flow 走查(0.25.1 全流程验证)"),
    "microarch-1": ("microarch1", "microarch-modeling · microarch-1"),
    "microarch-2": ("microarch2", "microarch-modeling · microarch-2"),
    "tumor-1": ("tumor1", "tumor-immune-interface · tumor-1"),
    "tumor-2": ("tumor2", "tumor-immune-interface · tumor-2"),
    "walkthrough-4": ("w4", "walkthrough-4(首份 NORMAL 走查)"),
    "walkthrough-5": ("w5", "walkthrough-5(干净重跑,no-ff)"),
    "walkthrough-6": ("w6", "walkthrough-6(机制排练)"),
    "walkthrough-7": ("w7", "walkthrough-7(v3 全链 E2E 首跑 · ABNORMAL)"),
    "walkthrough-8": ("w8", "walkthrough-8(v3 全链 E2E 重跑 · NORMAL)"),
    "w6n-pilot": ("w6np", "w6-4×2·N冒烟"),
    "w6n1": ("w6n1", "w6-4×2·N#1"),
    "w6n2": ("w6n2", "w6-4×2·N#2"),
    "w6n3": ("w6n3", "w6-4×2·N#3"),
    "w6n4": ("w6n4", "w6-4×2·N#4"),
    "w6r-pilot": ("w6rp", "w6-4×2·R冒烟"),
    "w6r1": ("w6r1", "w6-4×2·R#1"),
    "w6r2": ("w6r2", "w6-4×2·R#2"),
    "w6r3": ("w6r3", "w6-4×2·R#3"),
    "w6r4": ("w6r4", "w6-4×2·R#4"),
}
MECH = {
    "walkthrough-7": "peer-dead(a, 402) → b abort → recovery closeout",
    "microarch-1": "b early-stop(缺 M2 duty)→ a abort",
    "microarch-2": "b 依对侧静默(~900s×2)abort;a stop 后到(竞速)",
}
SIDE_MODEL = {"a": "deepseek-flash", "b": "qwen3.8-flash"}


def parse_iso(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def is_peak(dt):
    return dt.weekday() < 5 and (1 <= dt.hour < 4 or 6 <= dt.hour < 10)


def walk_usage(obj, out):
    if isinstance(obj, dict):
        u = obj.get("usageMetadata")
        if isinstance(u, dict):
            out.append(u)
        for v in obj.values():
            walk_usage(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_usage(v, out)


def side_of(c, chat):
    for s in ("a", "b"):
        u = c / "x" / f"session-{s}.uuid"
        if u.exists() and u.read_text().strip() == chat.stem:
            return s
    txt = chat.read_text(errors="replace")[:300000]
    na, nb = txt.count("/root/wt/a"), txt.count("/root/wt/b")
    return "a" if na > nb else ("b" if nb > na else "?")


def side_metrics(chat_path, side):
    steps, step_ts, ev = 0, [], []
    first = last = None
    for line in chat_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = d.get("timestamp")
        if isinstance(ts, str):
            if first is None:
                first = ts
            last = ts
        t = d.get("type")
        m = d.get("message")
        if t == "assistant" or (isinstance(m, dict) and m.get("role") == "model" and t != "assistant"):
            steps += 1
            step_ts.append(ts)
        us = []
        walk_usage(d, us)
        for u in us:
            p = u.get("promptTokenCount", 0) or 0
            cc = u.get("cachedContentTokenCount", 0) or 0
            cand = u.get("candidatesTokenCount", 0) or 0
            th = u.get("thoughtsTokenCount", 0) or 0
            ev.append({"i": max(1, steps), "ts": ts, "p": p, "cache": cc,
                       "unc": max(p - cc, 0), "out": cand + th})
    gaps = []
    tss = [x for x in (parse_iso(x) for x in step_ts if x) if x]
    for x, y in zip(tss, tss[1:]):
        gaps.append((y - x).total_seconds())
    tot = {k: sum(e[k] for e in ev) for k in ("p", "cache", "unc", "out")}
    t0 = parse_iso(first) if first else None
    peaks = bool(t0 and is_peak(t0))
    rate = (RATE_A_PEAK if peaks else RATE_A_OFF) if side == "a" else RATE_B
    cost = (tot["unc"] * rate["uncached"] + tot["cache"] * rate["cache"] + tot["out"] * rate["out"]) / 1e6

    def tailsum(comp, cut):
        vals = [e.get(comp, 0) for e in ev]
        t = sum(vals)
        if t <= 0 or len(vals) < 8:
            return 0, t
        k = int(len(vals) * cut)
        return sum(vals[k:]), t

    tail75 = {c: tailsum(c, 0.75)[0] for c in ("out", "unc", "cache")}
    tail_cost = (tail75["unc"] * rate["uncached"] + tail75["cache"] * rate["cache"] + tail75["out"] * rate["out"]) / 1e6
    dec = []
    if ev:
        n = len(ev)
        for f in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
            dec.append(ev[min(n - 1, max(0, int(n * f) - 1))]["p"])
    series = []
    prev = None
    for e in ev:
        et = parse_iso(e["ts"]) if e["ts"] else None
        rel = (et - t0).total_seconds() if (et and t0) else None
        gap = (et - prev).total_seconds() if (et and prev) else None
        series.append([e["i"], round(rel, 1) if rel is not None else None,
                       round(gap, 1) if gap is not None else None,
                       e["cache"], e["unc"], e["out"]])
        if et:
            prev = et
    d = {
        "side": side, "model": SIDE_MODEL.get(side, "?"),
        "steps": steps, "usage_events": len(ev),
        "wall_s": round((parse_iso(last) - parse_iso(first)).total_seconds(), 1) if (first and last) else None,
        "unc": tot["unc"], "cache": tot["cache"], "out": tot["out"],
        "gap_med_s": round(st.median(gaps), 1) if gaps else None,
        "gap_p90_s": round(sorted(gaps)[min(len(gaps) - 1, int(len(gaps) * 0.9))], 1) if gaps else None,
        "gap_max_s": round(max(gaps), 1) if gaps else None,
        "cost": round(cost, 4), "cost_unit": "USD" if side == "a" else "CNY", "peak": peaks,
        "tail75": {c: tail75[c] for c in tail75}, "tail_cost": round(tail_cost, 4),
        "deciles": dec, "series": series,
    }
    return d


def gate_ledger(c):
    out = {"counts": {}, "refusals": [], "blocks": []}
    f = c / "x" / "gate.log"
    if not f.exists():
        return out
    lines = f.read_text(errors="replace").splitlines()
    oks = []
    for idx, ln in enumerate(lines):
        mm = re.match(r"^\d\d:\d\d:\d\d (\S+) ", ln)
        if not mm:
            continue
        kind = mm.group(1)
        out["counts"][kind] = out["counts"].get(kind, 0) + 1
        am = re.search(r"actor=([ab])", ln)
        rm = re.search(r"Round=(\d+)", ln)
        if kind == "refs-ok" and am and rm:
            oks.append((idx, am.group(1), rm.group(1)))
        if kind == "refs-block" and am and rm:
            out["refusals"].append({"actor": am.group(1), "round": int(rm.group(1)), "fixed": False, "at": idx})
        if kind == "block":
            pm = re.search(r"peer-([ab])", ln)
            out["blocks"].append({"actor": am.group(1) if am else "?", "peer": pm.group(1) if pm else "?",
                                  "when": " ".join(ln.split())[9:80]})
    for r in out["refusals"]:
        r["fixed"] = any(i > r["at"] and a == r["actor"] and rd == str(r["round"]) for (i, a, rd) in oks)
        del r["at"]
    return out


def run_metrics(job, c):
    stt = {}
    try:
        stt = json.loads((c / "state.json").read_text())
    except Exception:
        pass
    normal = stt.get("normal")
    if normal is None and stt:
        normal = bool(stt.get("rc_a") == 0 and stt.get("rc_b") == 0 and stt.get("stop_a")
                      and stt.get("stop_b") and stt.get("consensus_on_main"))
    sig = {}
    for name in ("stop-a", "stop-b", "abort-a", "abort-b"):
        p = c / "x" / name
        if p.exists():
            t = " ".join(p.read_text(errors="replace").split())
            mm = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", t)
            sig[name] = {"ts": mm.group(0) if mm else None, "head": t[:170]}
    rec = None
    rp = c / "x" / "recover.json"
    if rp.exists():
        try:
            r = json.loads(rp.read_text())
            rec = {"wakes": [{k: w.get(k) for k in ("side", "rc", "dur_s", "mode")} for w in r.get("wakes", [])]}
        except Exception:
            rec = {"wakes": []}
    variant = None
    vp = c / "x" / "prompt-variant"
    if vp.exists():
        variant = vp.read_text().strip()
    exp, label = EXP.get(job, (None, job))
    return {"job": job, "exp": exp, "label": label, "family": family(job), "normal": normal,
            "rc": [stt.get("rc_a"), stt.get("rc_b")],
            "stop": [bool(stt.get("stop_a")), bool(stt.get("stop_b"))],
            "abort": [bool(stt.get("abort_a")), bool(stt.get("abort_b"))],
            "recovered": stt.get("recovered_run"), "mech": MECH.get(job, ""),
            "variant": variant, "signals": sig, "recover": rec, "gate": gate_ledger(c)}


def family(job):
    if job.startswith(("walkthrough", "bump", "w6n", "w6r")):
        return "rehearsal"
    if job.startswith("tumor"):
        return "tumor"
    if job.startswith("microarch"):
        return "microarch"
    return "other"


def main():
    runs, sides = [], []
    for jd in sorted(JOBS.iterdir()):
        if not jd.is_dir():
            continue
        colls = list(jd.glob("task-*/artifacts/root/wt/collect"))
        if not colls:
            continue
        c = colls[0]
        chats = sorted((c / "chats").glob("*.jsonl"))
        if not chats:
            continue
        r = run_metrics(jd.name, c)
        for chat in chats:
            d = side_metrics(chat, side_of(c, chat))
            d["job"] = jd.name
            sides.append(d)
            r.setdefault("sides", []).append(d)
        runs.append(r)

    pool = [s for s in sides if s["steps"] >= 12 and s["usage_events"] >= 8]
    families = {}
    for r in runs:
        f = families.setdefault(r["family"], {"runs": 0, "sides": 0, "steps": 0, "out": 0, "unc": 0, "cache": 0,
                                               "cost_a_usd": 0.0, "cost_b_cny": 0.0})
        f["runs"] += 1
        for s in r["sides"]:
            f["sides"] += 1
            f["steps"] += s["steps"]
            f["out"] += s["out"]
            f["unc"] += s["unc"]
            f["cache"] += s["cache"]
            if s["cost_unit"] == "USD":
                f["cost_a_usd"] += s["cost"]
            else:
                f["cost_b_cny"] += s["cost"]
    fam_list = []
    for name, f in sorted(families.items()):
        f = dict(f)
        f["name"] = name
        for k in ("cost_a_usd", "cost_b_cny"):
            f[k] = round(f[k], 4)
        fam_list.append(f)

    def saved_pct(comp, cut):
        vals = []
        for s in pool:
            ser = s["series"]
            if len(ser) < 8:
                continue
            t = sum(e[3 + {"cache": 0, "unc": 1, "out": 2}[comp]] for e in ser)
            if t <= 0:
                continue
            k = int(len(ser) * cut)
            vals.append(100.0 * sum(e[3 + {"cache": 0, "unc": 1, "out": 2}[comp]] for e in ser[k:]) / t)
        return round(st.median(vals), 1) if vals else None

    def wall_res(cut):
        vals = []
        for s in pool:
            ser = [e for e in s["series"] if e[1] is not None]
            if len(ser) < 8:
                continue
            k = int(len(ser) * cut)
            t = ser[-1][1] - ser[0][1]
            vals.append(100.0 * (ser[-1][1] - ser[k][1]) / t if t > 0 else None)
        vals = [v for v in vals if v is not None]
        return round(st.median(vals), 1) if vals else None

    tails = []
    for cut in (0.5, 0.75, 0.9):
        tails.append({"cut": int(cut * 100),
                      "out": saved_pct("out", cut), "unc": saved_pct("unc", cut),
                      "cache": saved_pct("cache", cut), "wall": wall_res(cut)})

    n_dec = min((len(s["deciles"]) for s in pool), default=0)
    growth = [round(st.median([s["deciles"][i] for s in pool]), 0) for i in range(n_dec)]

    ab = {}
    for sd in ("a", "b"):
        ss = [s for s in pool if s["side"] == sd]
        if not ss:
            continue
        ab[sd] = {"model": SIDE_MODEL[sd], "n": len(ss),
                  "gap_med": st.median([s["gap_med_s"] for s in ss]),
                  "gap_p90": st.median([s["gap_p90_s"] for s in ss]),
                  "gap_max": st.median([s["gap_max_s"] for s in ss]),
                  "out_per_step": round(st.median([s["out"] / max(1, s["steps"]) for s in ss])),
                  "steps_med": st.median([s["steps"] for s in ss])}

    aborts, recovers, stops = [], [], []
    for r in runs:
        for k, v in r["signals"].items():
            row = {"job": r["job"], "exp": r["exp"], "file": k, "ts": v["ts"], "head": v["head"]}
            (aborts if k.startswith("abort") else stops).append(row)
        if r["recover"] is not None:
            recovers.append({"job": r["job"], "exp": r["exp"], "wakes": r["recover"]["wakes"]})

    gate_pool = {}
    gate_rows = []
    for r in runs:
        g = r["gate"]
        row = {"job": r["job"], "exp": r["exp"], "counts": g["counts"],
               "refusals": g["refusals"], "blocks": g["blocks"]}
        gate_rows.append(row)
        for k, v in g["counts"].items():
            gate_pool[k] = gate_pool.get(k, 0) + v
    total_ref = sum(len(r["refusals"]) for r in gate_rows)
    fixed_ref = sum(1 for r in gate_rows for x in r["refusals"] if x["fixed"])

    cost_a = sum(s["cost"] for s in sides if s["cost_unit"] == "USD")
    cost_b = sum(s["cost"] for s in sides if s["cost_unit"] == "CNY")
    tail_a = sum(s["tail_cost"] for s in sides if s["cost_unit"] == "USD")
    tail_b = sum(s["tail_cost"] for s in sides if s["cost_unit"] == "CNY")

    data = {
        "meta": {"source": "harbor-runs/jobs/agent(全部含 collect/chats 的跑次),只读",
                 "script": "viz/scripts/build_process.py",
                 "note": "口径同 metrics.py;截尾=完美停上限(结局在 k% 步已知),非承诺;冻结产物不得用早停值"},
        "totals": {"runs": len(runs), "sides": len(sides),
                   "steps": sum(s["steps"] for s in sides),
                   "out": sum(s["out"] for s in sides),
                   "unc": sum(s["unc"] for s in sides),
                   "cache": sum(s["cache"] for s in sides),
                   "cost_a_usd": round(cost_a, 4), "cost_b_cny": round(cost_b, 3),
                   "total_cny_1to7": round(cost_a * 7 + cost_b, 1),
                   "tail75_a_usd": round(tail_a, 4), "tail75_b_cny": round(tail_b, 3),
                   "tail75_total_cny": round(tail_a * 7 + tail_b, 1)},
        "families": fam_list,
        "tails": tails,
        "growth": growth,
        "ab": ab,
        "aborts": aborts, "recovers": recovers, "stops": stops,
        "gate": {"pool_counts": gate_pool, "per_run": gate_rows,
                 "refusal_total": total_ref, "refusal_fixed": fixed_ref},
        "runs": runs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    t = data["totals"]
    print(f"build_process: runs={t['runs']} sides={t['sides']} steps={t['steps']} "
          f"out={t['out']/1e6:.2f}M cost=A${t['cost_a_usd']:.3f}+B¥{t['cost_b_cny']:.1f} "
          f"refusal={fixed_ref}/{total_ref} -> {OUT}")


if __name__ == "__main__":
    main()
