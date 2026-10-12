#!/usr/bin/env python3
"""metrics.py — per-run and per-arm metrics for the w6 N/R two-arm experiment.

Reads harbor job dirs under <harbor-runs>/jobs/agent/<job>/ and reports:
  - wall time (result.json started_at -> finished_at) and agent-phase time
  - wrapper verdict (collect/state.json "normal"), rounds, stops/aborts, exception
  - the prompt variant actually used (collect/x/prompt-variant; audit trail)
  - per-side tokens from the collected chats' usageMetadata (per response):
        uncached_in = prompt - cached ; cache = cached ; out = candidates + thoughts
    (thoughts billed as output on both providers; candidates-only is kept as a
     sensitivity column)
  - cost:
      A side deepseek-flash (USD, rate card 2026-10-10):
        off-peak  miss 0.15 / cache 0.003 / out 0.60 per M
        peak      miss 0.30 / cache 0.006 / out 1.20 per M   (peak = 01-04, 06-10 UTC, Mon-Fri)
      B side qwen3.8-flash (CNY, rate card 2026-10-10):
        miss 0.8 / cache 0.1 / out 2.7 per M ; credits = CNY*200 at k=1 (also k=0.72)
  - per-arm medians and the H verdict (time / A-cost / B-cost: how many of 3 favor R)

Usage: python3 metrics.py <job> [<job> ...]
"""
import json, pathlib, re, statistics, sys

JOBS_BASE = pathlib.Path(__file__).resolve().parents[3] / "jobs" / "agent"   # <harbor-runs>/jobs/agent

def rdjson(p):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except Exception:
        return None

def find_one(root, name):
    for p in pathlib.Path(root).rglob(name):
        return p
    return None

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

def side_tokens(jobdir, side):
    x = find_one(jobdir, "x")
    if not x:
        return None
    u = x / f"session-{side}.uuid"
    if not u.exists():
        return None
    chat = find_one(jobdir, f"{u.read_text().strip()}.jsonl")
    if not chat:
        return None
    rows = [json.loads(l) for l in chat.read_text().splitlines() if l.strip()]
    tok = []
    for d in rows:
        walk_usage(d, tok)
    agg = {"uncached": 0, "cache": 0, "out": 0, "cand": 0, "thoughts": 0, "events": len(tok)}
    for u in tok:
        p = u.get("promptTokenCount", 0) or 0
        c = u.get("cachedContentTokenCount", 0) or 0
        cand = u.get("candidatesTokenCount", 0) or 0
        th = u.get("thoughtsTokenCount", 0) or 0
        agg["uncached"] += max(p - c, 0)
        agg["cache"] += c
        agg["cand"] += cand
        agg["thoughts"] += th
        agg["out"] += cand + th
    return agg

def is_peak(iso):
    # peak = 01:00-04:00 and 06:00-10:00 UTC, Mon-Fri
    import datetime
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    h = t.hour
    return t.weekday() < 5 and (1 <= h < 4 or 6 <= h < 10)

def human(sec):
    return f"{int(sec)//60}m{int(sec)%60:02d}s"

def run_metrics(job):
    jd = JOBS_BASE / job
    r = None
    for p in jd.glob("task-*__*/result.json"):
        r = rdjson(p); break
    m = {"job": job}
    if not r:
        m["error"] = "no result.json"
        return m
    st, fi = r.get("started_at"), r.get("finished_at")
    import datetime
    def parse(s):
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
    if st and fi:
        m["wall_s"] = (parse(fi) - parse(st)).total_seconds()
    ae = r.get("agent_execution") or {}
    if ae.get("started_at") and ae.get("finished_at"):
        m["agent_s"] = (parse(ae["finished_at"]) - parse(ae["started_at"])).total_seconds()
    m["exception"] = bool(r.get("exception_info"))
    m["started_at"] = st
    state = None
    sp = find_one(jd, "state.json")
    if sp and "collect" in str(sp):
        state = rdjson(sp)
    if state:
        n = state.get("normal")
        if n is None:  # state.json written before the "normal" field existed
            n = (state.get("rc_a") == 0 and state.get("rc_b") == 0
                 and state.get("stop_a") and state.get("stop_b")
                 and state.get("consensus_on_main"))
        m["normal"] = n
        m["rounds"] = f"a{state.get('rounds', {}).get('a', '?')}/b{state.get('rounds', {}).get('b', '?')}"
        m["stops"] = bool(state.get("stop_a")) and bool(state.get("stop_b"))
    pv = None
    vp = find_one(jd, "prompt-variant")
    if vp and "x" in str(vp):
        try: pv = vp.read_text().strip()
        except Exception: pv = None
    m["variant"] = pv or "(default prompt.md)"
    g = find_one(jd, "gate.log")
    blocks = 0
    bad = 0
    if g:
        txt = g.read_text(errors="replace")
        blocks = len(re.findall(r"\bblock\b", txt))
        bad = len(re.findall(r"stalled|exhausted", txt))
    m["gate_blocks"] = blocks
    m["gate_bad"] = bad
    toks = {}
    for side in ("a", "b"):
        t = side_tokens(jd, side)
        if t:
            toks[side] = t
    m["tokens"] = toks
    if "a" in toks:
        t = toks["a"]
        rate = 2.0 if (st and is_peak(st)) else 1.0
        m["A_usd"] = (t["uncached"] * 0.15 + t["cache"] * 0.003 + t["out"] * 0.60) * rate / 1e6
        m["A_peak"] = bool(st and is_peak(st))
    if "b" in toks:
        t = toks["b"]
        cny = (t["uncached"] * 0.8 + t["cache"] * 0.1 + t["out"] * 2.7) / 1e6
        m["B_cny"] = cny
        m["B_cr_k1"] = cny * 200
        m["B_cr_k072"] = cny * 144
    return m

def med(vals):
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None

def main():
    jobs = sys.argv[1:]
    if not jobs:
        jobs = [f"w6n{i}" for i in range(1, 5)] + [f"w6r{i}" for i in range(1, 5)]
    rows = [run_metrics(j) for j in jobs]
    print(f"{'job':12s} {'variant':22s} {'wall':>7s} {'agent':>7s} {'rounds':>7s} {'normal':>7s} {'blocks':>6s} {'A$':>8s} {'B¥':>7s} {'B_cr(k1)':>9s}")
    for m in rows:
        print(f"{m['job']:12s} {str(m.get('variant',''))[:22]:22s} "
              f"{human(m['wall_s']) if 'wall_s' in m else '--':>7s} "
              f"{human(m['agent_s']) if 'agent_s' in m else '--':>7s} "
              f"{str(m.get('rounds','')):>7s} {str(m.get('normal','')):>7s} "
              f"{m.get('gate_blocks',''):>6} "
              f"{m.get('A_usd',float('nan')):8.4f} {m.get('B_cny',float('nan')):7.3f} "
              f"{m.get('B_cr_k1',float('nan')):9.0f}")
    print()
    for arm, pref in (("N", "w6n"), ("R", "w6r")):
        arm_rows = [m for m in rows if m["job"].startswith(pref)]
        walls = [m.get("wall_s") for m in arm_rows]
        As = [m.get("A_usd") for m in arm_rows]
        Bs = [m.get("B_cny") for m in arm_rows]
        def fmt(vals, f="{:.4f}"):
            vals = [v for v in vals if v is not None]
            if not vals: return "--"
            return f"med {f.format(statistics.median(vals))} [{f.format(min(vals))}..{f.format(max(vals))}]"
        print(f"arm {arm} (n={len(arm_rows)}): wall {fmt([w/60 if w else None for w in walls],'{:.1f}')} min | "
              f"A$ {fmt(As)} | B¥ {fmt(Bs,'{:.3f}')}")
    print()
    n_walls = med([m.get("wall_s") for m in rows if m["job"].startswith("w6n")])
    r_walls = med([m.get("wall_s") for m in rows if m["job"].startswith("w6r")])
    n_a, r_a = med([m.get("A_usd") for m in rows if m["job"].startswith("w6n")]), med([m.get("A_usd") for m in rows if m["job"].startswith("w6r")])
    n_b, r_b = med([m.get("B_cny") for m in rows if m["job"].startswith("w6n")]), med([m.get("B_cny") for m in rows if m["job"].startswith("w6r")])
    verdicts = []
    for name, nv, rv, lower_better in (("time", n_walls, r_walls, True), ("A$", n_a, r_a, True), ("B¥", n_b, r_b, True)):
        if nv is None or rv is None:
            verdicts.append(f"{name}: n/a"); continue
        win = rv < nv
        pct = (rv - nv) / nv * 100
        verdicts.append(f"{name}: R {'<' if win else '>='} N ({pct:+.1f}%)")
    wins = sum(1 for v in verdicts if "R < N" in v)
    print("H verdict (R improves time & cost): " + " | ".join(verdicts) + f"  => {wins}/3 metrics favor R")

if __name__ == "__main__":
    main()
