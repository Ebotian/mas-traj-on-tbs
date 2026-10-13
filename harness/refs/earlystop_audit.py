#!/usr/bin/env python3
# earlystop_audit.py — retrospective early-stop accounting over all collected dual-agent runs.
# Read-only; stdlib only. Token conventions reused from tasks/walkthrough/metrics.py:
#   uncached = prompt - cached ; cache = cached ; out = candidates + thoughts.
# Usage: python3 /home/ebt/harbor-runs/refs/earlystop_audit.py
import json, re, datetime, statistics as st
from pathlib import Path

JOBS = Path("/home/ebt/harbor-runs/jobs/agent")
OUT = Path("/home/ebt/harbor-runs/refs/audit-2026-10-12")
OUT.mkdir(parents=True, exist_ok=True)

RATE_A_OFF = {"uncached": 0.15, "cache": 0.003, "out": 0.60}   # USD / M
RATE_A_PEAK = {"uncached": 0.30, "cache": 0.006, "out": 1.20}  # USD / M (x2)
RATE_B = {"uncached": 0.8, "cache": 0.1, "out": 2.7}           # CNY / M

MECH = {
    "walkthrough-7": "peer-dead(a, 402) -> b abort -> recovery closeout",
    "microarch-1": "b early-stop (skipped M2 duty) -> a abort",
    "microarch-2": "b abort on perceived a-stall (~900s x2); a stop later (race)",
}

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
        u = c / "x" / ("session-%s.uuid" % s)
        if u.exists() and u.read_text().strip() == chat.stem:
            return s
    txt = chat.read_text(errors="replace")[:300000]
    na, nb = txt.count("/root/wt/a"), txt.count("/root/wt/b")
    return "a" if na > nb else ("b" if nb > na else "?")

def side_metrics(chat_path, side):
    steps = 0
    step_ts = []
    ev = []
    first = last = None
    text = chat_path.read_text(errors="replace")
    for line in text.splitlines():
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
    def med(xs):
        return round(st.median(xs), 1) if xs else None
    def p90(xs):
        if not xs:
            return None
        xs2 = sorted(xs)
        return round(xs2[min(len(xs2) - 1, int(len(xs2) * 0.9))], 1)
    tot = {k: sum(e[k] for e in ev) for k in ("p", "cache", "unc", "out")}
    def tailsum(comp, cut):
        vals = [e.get(comp, 0) for e in ev]
        t = sum(vals)
        if t <= 0 or len(vals) < 8:
            return None
        k = int(len(vals) * cut)
        return sum(vals[k:])
    def wall_frac(cut):
        tser = [x for x in (parse_iso(e["ts"]) for e in ev) if x]
        if len(tser) < 8:
            return None
        k = int(len(tser) * cut)
        t = (tser[-1] - tser[0]).total_seconds()
        return round(100.0 * (tser[-1] - tser[k]).total_seconds() / t, 1) if t > 0 else None
    dec = []
    if ev:
        n = len(ev)
        for f in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
            idx = min(n - 1, max(0, int(n * f) - 1))
            dec.append(ev[idx]["p"])
    d = {
        "side": side, "steps": steps, "usage_events": len(ev),
        "first": first, "last": last,
        "wall_s": (parse_iso(last) - parse_iso(first)).total_seconds() if (first and last) else None,
        "unc": tot["unc"], "cache": tot["cache"], "out": tot["out"], "prompt": tot["p"],
        "gap_med_s": med(gaps), "gap_p90_s": p90(gaps), "gap_max_s": round(max(gaps), 1) if gaps else None,
        "prompt_deciles": dec,
    }
    for cut in (0.5, 0.75, 0.9):
        tag = "%d" % int(cut * 100)
        for comp in ("out", "unc", "cache"):
            tv = tailsum(comp, cut)
            d["saved_%s_pct_%s" % (comp, tag)] = round(100.0 * tv / tot[comp], 1) if (tv is not None and tot[comp] > 0) else None
        d["wall_res_pct_%s" % tag] = wall_frac(cut)
    ts75 = {c: tailsum(c, 0.75) for c in ("out", "unc", "cache")}
    d["tail75"] = {c: (ts75[c] or 0) for c in ts75}
    dt0 = parse_iso(first) if first else None
    if side == "a":
        rate = RATE_A_PEAK if (dt0 and is_peak(dt0)) else RATE_A_OFF
        d["cost"] = (tot["unc"] * rate["uncached"] + tot["cache"] * rate["cache"] + tot["out"] * rate["out"]) / 1e6
        d["cost_unit"] = "USD"
        d["peak"] = bool(dt0 and is_peak(dt0))
        d["tail_cost"] = (ts75["unc"] * rate["uncached"] + ts75["cache"] * rate["cache"] + ts75["out"] * rate["out"]) / 1e6
    else:
        d["cost"] = (tot["unc"] * RATE_B["uncached"] + tot["cache"] * RATE_B["cache"] + tot["out"] * RATE_B["out"]) / 1e6
        d["cost_unit"] = "CNY"
        d["tail_cost"] = (ts75["unc"] * RATE_B["uncached"] + ts75["cache"] * RATE_B["cache"] + ts75["out"] * RATE_B["out"]) / 1e6
    return d

def family(job):
    if job.startswith(("walkthrough", "bump", "w6n", "w6r")):
        return "rehearsal"
    if job.startswith("tumor"):
        return "tumor"
    if job.startswith("microarch"):
        return "microarch"
    return "other"

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
            sig[name] = {"ts": mm.group(0) if mm else None, "head": t[:200]}
    rec = None
    rp = c / "x" / "recover.json"
    if rp.exists():
        try:
            r = json.loads(rp.read_text())
            rec = {"wakes": [{k: w.get(k) for k in ("side", "rc", "dur_s", "mode")} for w in r.get("wakes", [])]}
        except Exception:
            rec = {"wakes": []}
    return {"job": job, "family": family(job), "normal": normal,
            "rc": [stt.get("rc_a"), stt.get("rc_b")],
            "stop": [bool(stt.get("stop_a")), bool(stt.get("stop_b"))],
            "abort": [bool(stt.get("abort_a")), bool(stt.get("abort_b"))],
            "recovered": stt.get("recovered_run"), "mech": MECH.get(job, ""),
            "signals": sig, "recover": rec}

def main():
    runs = []
    sides = []
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
        r["n_chats"] = len(chats)
        for chat in chats:
            s = side_of(c, chat)
            d = side_metrics(chat, s)
            d["job"] = jd.name
            d["family"] = r["family"]
            sides.append(d)
        runs.append(r)

    # ---- aggregates ----
    pool = [s for s in sides if s["steps"] >= 12 and s["usage_events"] >= 8]
    lines = []
    def pr(x=""):
        lines.append(str(x))
        print(x)

    pr("# Early-stop audit over collected dual-agent runs (2026-10-12)")
    pr()
    pr("runs=%d  side-transcripts=%d  pool(sides>=12 steps)=%d" % (len(runs), len(sides), len(pool)))
    pr()
    pr("## Inventory by family")
    fams = {}
    for r in runs:
        fams.setdefault(r["family"], []).append(r)
    for fam, rs in sorted(fams.items()):
        ss = [s for s in sides if s["family"] == fam]
        pr("- %-10s runs=%2d sides=%2d steps=%5d out_tok=%8.2fM unc_tok=%6.2fM cache_tok=%8.1fM" % (
            fam, len(rs), len(ss),
            sum(s["steps"] for s in ss),
            sum(s["out"] for s in ss) / 1e6,
            sum(s["unc"] for s in ss) / 1e6,
            sum(s["cache"] for s in ss) / 1e6))
    pr("- totals     runs=%2d sides=%2d steps=%5d out=%.2fM unc=%.2fM cache=%.1fM" % (
        len(runs), len(sides), sum(s["steps"] for s in sides),
        sum(s["out"] for s in sides) / 1e6, sum(s["unc"] for s in sides) / 1e6,
        sum(s["cache"] for s in sides) / 1e6))
    costA = sum(s["cost"] for s in sides if s["side"] == "a")
    costB = sum(s["cost"] for s in sides if s["side"] == "b")
    tailA = sum(s["tail_cost"] for s in sides if s["side"] == "a")
    tailB = sum(s["tail_cost"] for s in sides if s["side"] == "b")
    pr("- pool cost: A=$%.3f(USD) B=%.1f(CNY) total~CNY %.1f ; tail75 of cost: A=$%.3f B=%.1f" % (
        costA, costB, costA * 7 + costB, tailA, tailB))
    pr()
    pr("## Perfect-halt saving upper bound (median over pool, cut at k%% of steps)")
    for tag, cutlabel in (("50", "50%"), ("75", "75%"), ("90", "90%")):
        vals = lambda key: [s[key] for s in pool if s.get(key) is not None]
        pr("- cut %s : saved out=%.1f%%  unc=%.1f%%  cache=%.1f%%  wall-residue=%.1f%%" % (
            cutlabel,
            st.median(vals("saved_out_pct_%s" % tag)),
            st.median(vals("saved_unc_pct_%s" % tag)),
            st.median(vals("saved_cache_pct_%s" % tag)),
            st.median(vals("wall_res_pct_%s" % tag))))
    pr()
    pr("## Context growth (median prompt tokens at deciles of the run)")
    n_dec = min(len(s["prompt_deciles"]) for s in pool)
    for i in range(n_dec):
        vals = [s["prompt_deciles"][i] for s in pool]
        pr("- decile %2d%% : median prompt %8.0f tok" % (int((i + 1) * 10), st.median(vals)))
    pr()
    pr("## Existing stop/abort signals vs verdicts")
    ab = [r for r in runs if r["signals"].get("abort-a") or r["signals"].get("abort-b")]
    pr("- runs with abort files: %d ; of them abnormal: %d" % (len(ab), sum(1 for r in ab if not r["normal"])))
    for r in ab:
        for k, v in r["signals"].items():
            if k.startswith("abort"):
                pr("    %s %s @ %s | %s" % (r["job"], k, v["ts"], v["head"][:140]))
    normal_runs = [r for r in runs if r["normal"]]
    pr("- normal runs: %d ; runs with any abort among them: %d" % (
        len(normal_runs), sum(1 for r in normal_runs if r["signals"].get("abort-a") or r["signals"].get("abort-b"))))
    rec_runs = [r for r in runs if r["recover"] is not None]
    pr("- runs with recover.json: %s" % ", ".join(
        "%s[wakes=%d]" % (r["job"], len(r["recover"]["wakes"])) for r in rec_runs))
    pr("- abnormal runs and mechanism:")
    for r in runs:
        if not r["normal"]:
            pr("    %s : %s" % (r["job"], r["mech"] or "(no label)"))
    pr()
    pr("## Side A (deepseek) vs side B (qwen) descriptive")
    for sd in ("a", "b"):
        ss = [s for s in pool if s["side"] == sd]
        if not ss:
            continue
        pr("- side %s : n=%d  gap med=%.1fs p90=%.1fs max=%.1fs  out/step=%.0f tok  steps med=%.0f" % (
            sd, len(ss), st.median([s["gap_med_s"] for s in ss]), st.median([s["gap_p90_s"] for s in ss]),
            st.median([s["gap_max_s"] for s in ss]), st.median([s["out"] / max(1, s["steps"]) for s in ss]),
            st.median([s["steps"] for s in ss])))
    pr()
    pr("## Per-run table")
    for r in runs:
        pr("- %-18s %-8s normal=%-5s rc=%s stop=%s abort=%s mech=%s" % (
            r["job"], r["family"], r["normal"], r["rc"], r["stop"], r["abort"], r["mech"][:60]))
    pr()
    pr("## Per-side table (pool only)")
    for s in sorted(pool, key=lambda x: (x["job"], x["side"])):
        pr("- %-18s %s steps=%3d out=%6.2fM unc=%5.2fM cache=%7.1fM wall=%.0fs gapmax=%.0fs saved_out75=%s%% saved_unc75=%s%%" % (
            s["job"], s["side"], s["steps"], s["out"] / 1e6, s["unc"] / 1e6, s["cache"] / 1e6,
            s["wall_s"] or 0, s["gap_max_s"] or 0, s.get("saved_out_pct_75"), s.get("saved_unc_pct_75")))

    (OUT / "per_side.jsonl").write_text("\n".join(json.dumps(s) for s in sides))
    (OUT / "per_run.jsonl").write_text("\n".join(json.dumps(r) for r in runs))
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\nwrote: %s" % OUT)

if __name__ == "__main__":
    main()
