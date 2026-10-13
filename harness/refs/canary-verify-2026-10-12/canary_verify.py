#!/usr/bin/env python3
"""canary hypothesis verification on existing dual-agent assets (read-only).

Checks, from the collected runs under jobs/agent:
  1. per-run/per-side transcript gap table (the pure-silence baseline surface);
  2. every wait_pos/wait_peer/wait_file invocation with wall duration + outcome;
  3. all "silent for ~" / "peer-...dead" exits across the corpus;
  4. the three ABNORMAL cases (w7, m1, m2) with decision-point deltas;
  5. the rendezvous-name table for m2.
Writes cases.json next to this script; prints a bounded report.

No writes into harbor-runs/jobs. stdlib only.
"""
import glob, json, os, re, sys
from datetime import datetime, timezone

BASE = "/home/ebt/harbor-runs/jobs/agent"
HERE = os.path.dirname(os.path.abspath(__file__))
WAIT_RE = re.compile(r"wait_(pos|peer|file)\.sh\s+([^;\"'\n]*)")

def collect(run):
    hits = sorted(glob.glob(f"{BASE}/{run}/task-*/artifacts/root/wt/collect"))
    return hits[0] if hits else None

def chat_path(c, side):
    u = f"{c}/x/session-{side}.uuid"
    if not os.path.exists(u):
        return None
    f = f"{c}/chats/" + open(u).read().strip() + ".jsonl"
    return f if os.path.exists(f) else None

def lines(f):
    for l in open(f, errors="replace"):
        l = l.strip()
        if not l:
            continue
        try:
            yield json.loads(l)
        except Exception:
            pass

def parts(d):
    return (d.get("message") or {}).get("parts") or []

def ts_epoch(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def scan_side(c, side):
    """-> dict(events=[ts], waits=[{argv,dur,out}], texts=[(ts,txt)], silent=[], dead=[])"""
    f = chat_path(c, side)
    out = {"events": [], "waits": [], "silent": [], "dead": [], "max_wait_exits": [], "texts": []}
    if not f:
        return out
    pend = {}
    for d in lines(f):
        ts = d.get("timestamp")
        if ts:
            out["events"].append(ts)
        for p in parts(d):
            if not isinstance(p, dict):
                continue
            fc, fr = p.get("functionCall"), p.get("functionResponse")
            if fc:
                a = fc.get("args") or {}
                cmd = str(a.get("command", ""))
                m = WAIT_RE.search(cmd)
                if m:
                    pend[fc.get("id")] = (ts, m.group(0))
                if d.get("type") == "assistant" and p.get("text"):
                    out["texts"].append((ts, str(p["text"])))
            elif fr:
                rid = fr.get("id")
                if rid in pend:
                    t0, argv = pend.pop(rid)
                    resp = fr.get("response") or {}
                    o = str(resp.get("output") or resp.get("error") or "")
                    dur = None
                    e0, e1 = ts_epoch(t0), ts_epoch(ts)
                    if e0 and e1:
                        dur = round(e1 - e0, 1)
                    rec = {"argv": argv, "t0": t0, "t1": ts, "dur": dur, "out": o}
                    out["waits"].append(rec)
                    head = o.splitlines()[0] if o.splitlines() else ""
                    if "silent for" in o:
                        out["silent"].append(rec)
                    if re.search(r"peer-\w+ dead", o):
                        out["dead"].append(rec)
                    if "max wait" in o:
                        out["max_wait_exits"].append(rec)
            elif d.get("type") == "assistant" and p.get("text"):
                out["texts"].append((ts, str(p["text"])))
    return out

def gaps(evs):
    e = sorted(x for x in (ts_epoch(t) for t in evs) if x)
    if len(e) < 2:
        return {"n": len(e), "max": None, "g300": 0, "g600": 0, "top": []}
    ds = [(round(e[i + 1] - e[i], 1), evs[i] if False else None) for i in range(len(e) - 1)]
    mx = max(d for d, _ in ds)
    top = sorted(d for d, _ in ds if d >= 300)[-3:]
    return {"n": len(e), "max": mx, "g300": sum(1 for d, _ in ds if d >= 300),
            "g600": sum(1 for d, _ in ds if d >= 600), "top": top}

def xfile(c, name, cap=200):
    p = f"{c}/x/{name}"
    if not os.path.exists(p):
        return None
    return open(p, errors="replace").read().strip()[:cap]

def main():
    runs = []
    for d in sorted(os.listdir(BASE)):
        c = collect(d)
        if not c:
            continue
        if not (chat_path(c, "a") and chat_path(c, "b")):
            continue
        runs.append((d, c))

    res = {"runs": {}, "wait_ledger": [], "cases": {}}
    print(f"=== corpus: {len(runs)} collected runs with 2 chats ===")
    for name, c in runs:
        row = {"sides": {}, "x": {}}
        for s in ("a", "b"):
            sc = scan_side(c, s)
            g = gaps(sc["events"])
            row["sides"][s] = {"gaps": g, "n_waits": len(sc["waits"])}
            for w in sc["waits"]:
                res["wait_ledger"].append({"run": name, "side": s, **{k: w[k] for k in ("argv", "t0", "t1", "dur")},
                                           "out_head": (w["out"].splitlines() or [""])[0][:90]})
            for kind in ("silent", "dead", "max_wait_exits"):
                for w in sc[kind]:
                    res["wait_ledger"][-1]  # ledger already holds them; marker below
        for fn in ("stop-a", "stop-b", "abort-a", "abort-b", "m2-done"):
            v = xfile(c, fn, 80)
            row["x"][fn] = v
        res["runs"][name] = row
        da, db = row["sides"]["a"]["gaps"], row["sides"]["b"]["gaps"]
        flags = []
        if row["x"]["abort-a"] or row["x"]["abort-b"]:
            flags.append("ABORT")
        if (row["x"]["stop-a"] and row["x"]["stop-b"]):
            flags.append("stops2")
        print(f"{name:22s} a: n={da['n']:4d} max={da['max']} g300={da['g300']} g600={da['g600']} "
              f"| b: n={db['n']:4d} max={db['max']} g300={db['g300']} g600={db['g600']} "
              f"| {' '.join(flags)}")

    # wait ledger: non-success exits + duration histogram
    print("\n=== wait-call ledger: all invocations ===")
    hist = {}
    for w in res["wait_ledger"]:
        dur = w["dur"]
        b = "<2s" if (dur is not None and dur < 2) else ("2-30s" if dur is not None and dur < 30
             else ("30-299s" if dur is not None and dur < 300 else ("300-310s" if dur is not None and dur <= 310
             else ("310-600s" if dur is not None and dur <= 600 else ">600s"))))
        hist[b] = hist.get(b, 0) + 1
        oh = w["out_head"]
        bad = bool(re.search(r"(peer-\w+ (dead|silent)|max wait|rc=12|rc=2$)", oh + " " + str(w["dur"])))
        if bad or (dur is not None and dur >= 250):
            print(f"  {w['run']:16s} {w['side']} {w['argv'][:38]:38s} {w['t0'][11:19] if w['t0'] else '?'} "
                  f"dur={dur} :: {oh[:78]}")
    print("  histogram:", hist)

    # silent/dead exits anywhere
    print("\n=== corpus-wide 'silent for ~' / 'peer-... dead' exits ===")
    n_sil = n_dead = 0
    for w in res["wait_ledger"]:
        oh = w["out_head"]
        if "silent for" in oh or "silent for" in json.dumps(w):
            pass
    for name, c in runs:
        for s in ("a", "b"):
            sc = scan_side(c, s)
            for w in sc["silent"]:
                n_sil += 1
                print(f"  SILENT {name} {s} {w['argv'][:30]} t0={w['t0']} t1={w['t1']} dur={w['dur']} :: {w['out'].splitlines()[0][:90]}")
            for w in sc["dead"]:
                n_dead += 1
                print(f"  DEAD   {name} {s} {w['argv'][:30]} t0={w['t0']} t1={w['t1']} dur={w['dur']} :: {w['out'].splitlines()[0][:90]}")
    print(f"  totals: silent={n_sil} dead={n_dead}")

    # case extraction helper
    def case(run, side, t0, t1):
        c = collect(run)
        sc = scan_side(c, side)
        picks = [(t, x) for (t, x) in sc["texts"] if t and t0 <= t <= t1]
        calls = [w for w in sc["waits"] if w["t0"] and t0 <= w["t0"] <= t1]
        evs = [t for t in sc["events"] if t and t0 <= t <= t1]
        return c, sc, evs, calls, picks

    # ---- case w7 ----
    print("\n=== case walkthrough-7 (peer death, external) ===")
    c7 = collect("walkthrough-7")
    sa = scan_side(c7, "a")
    a_evs = sorted(t for t in sa["events"] if t and t < "2026-10-12T08:00")
    a_last = a_evs[-1]
    a_after = sorted(t for t in sa["events"] if t and t > "2026-10-12T08:00")
    _, sb, evs_b, calls_b, texts_b = case("walkthrough-7", "b", "2026-10-12T08:08:40", "2026-10-12T08:17:00")
    gate_tail = open(f"{c7}/x/gate.log", errors="replace").read().strip().splitlines()
    dead_line = [l for l in gate_tail if "dead" in l][-1:]
    print(f"  a last event before death : {a_last}   (first after: {a_after[0] if a_after else '-'})")
    print(f"  gate.log dead line        : {dead_line}")
    for w in calls_b:
        print(f"  b call {w['t0'][11:23]} -> {w['t1'][11:23]} dur={w['dur']} {w['argv'][:40]} :: {(w['out'].splitlines() or [''])[0][:100]}")
    for t, x in texts_b[:6]:
        print(f"  b text [{t[11:23]}] {x[:150]}")
    res["cases"]["w7"] = {"a_last": a_last, "a_first_after": a_after[0] if a_after else None,
                          "gate_dead": dead_line, "abort_b": xfile(c7, "abort-b", 300)}

    # ---- case m1 ----
    print("\n=== case microarch-1 (premature self-stop, duty owed) ===")
    c1 = collect("microarch-1")
    _, sa1, evs_a1, calls_a1, texts_a1 = case("microarch-1", "a", "2026-10-11T18:12:00", "2026-10-11T18:19:00")
    _, sb1, evs_b1, calls_b1, texts_b1 = case("microarch-1", "b", "2026-10-11T18:11:30", "2026-10-11T18:15:00")
    print(f"  stop-b content   : {xfile(c1,'stop-b')}")
    print(f"  m2-done / stop-a : {xfile(c1,'m2-done')} / {xfile(c1,'stop-a')}")
    print(f"  abort-a (head)   : {xfile(c1,'abort-a',260)}")
    for w in calls_a1:
        print(f"  a call {w['t0'][11:23]} -> {w['t1'][11:23]} dur={w['dur']} {w['argv'][:44]} :: {(w['out'].splitlines() or [''])[0][:100]}")
    for w in calls_b1:
        print(f"  b call {w['t0'][11:23]} -> {w['t1'][11:23]} dur={w['dur']} {w['argv'][:60]} :: {(w['out'].splitlines() or [''])[0][:80]}")
    for t, x in texts_b1[-2:]:
        print(f"  b last text [{t[11:23]}] {x[:200]}")
    res["cases"]["m1"] = {"stop_b": xfile(c1, "stop-b"), "abort_a": xfile(c1, "abort-a", 400)}

    # ---- case m2 ----
    print("\n=== case microarch-2 (false abandonment of a live peer) ===")
    c2 = collect("microarch-2")
    _, sa2, evs_a2, calls_a2, texts_a2 = case("microarch-2", "a", "2026-10-12T02:44:00", "2026-10-12T02:56:30")
    # a gap boundaries: the MAX-duration gap before 03:00 (the 590 s wait window)
    ts_a = sorted(t for t in scan_side(c2, "a")["events"] if t)
    best = None
    for i in range(len(ts_a) - 1):
        e0, e1 = ts_epoch(ts_a[i]), ts_epoch(ts_a[i + 1])
        if e1 - e0 >= 300 and ts_a[i] < "2026-10-12T03:00":
            if best is None or (e1 - e0) > best[0]:
                best = (e1 - e0, ts_a[i], ts_a[i + 1])
    gap0, gap1 = (best[1], best[2]) if best else (None, None)
    _, sb2, evs_b2, calls_b2, texts_b2 = case("microarch-2", "b", "2026-10-12T02:44:00", "2026-10-12T02:54:30")
    print(f"  a silence window : {gap0} -> {gap1}")
    print(f"  collect x/       : " + ", ".join(f"{n}={xfile(c2,n,30)!r}" for n in
          ("pos-a-r7","pos-a-r8","pos-b-r7","pos-b-r8","stop-a","stop-b","pid-a","pid-b","m2-done")))
    for w in calls_b2:
        print(f"  b call {w['t0'][11:23]} -> {w['t1'][11:23]} dur={w['dur']} {w['argv'][:44]} :: {(w['out'].splitlines() or [''])[0][:100]}")
    for t, x in texts_b2:
        if "silent" in x or "stalled" in x or "window" in x:
            print(f"  b text [{t[11:23]}] {x[:200]}")
    e_gap0, e_gap1 = ts_epoch(gap0), ts_epoch(gap1)
    for w in calls_b2:
        if "wait_pos.sh a 8" in w["argv"]:
            e0 = ts_epoch(w["t0"])
            if e0 and e_gap0:
                print(f"  >> wait exit {w['t1']}: dur={w['dur']}s ; a silent since {gap0} = {round(e0-e_gap0)}s at launch, "
                      f"{round(ts_epoch(w['t1'])-e_gap0)}s at exit; crossing(360s) at +360; exit-minus-crossing = {round(ts_epoch(w['t1'])-e_gap0-360)}s")
    print(f"  abort-b content  : {xfile(c2,'abort-b',300)}")
    res["cases"]["m2"] = {"a_gap": [gap0, gap1], "abort_b": xfile(c2, "abort-b", 400)}

    json.dump(res, open(f"{HERE}/cases.json", "w"), indent=1)
    print(f"\nwrote {HERE}/cases.json")

if __name__ == "__main__":
    main()
