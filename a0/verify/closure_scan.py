#!/usr/bin/env python3
"""Adversarial scan of the closure records.

For every mechanism whose schema_verdict is `closed`, check that the record also
carries an executed two-control observation (an unblocked case that reaches the
network AND a blocked case that fails). Flag any `closed` resting on
`inconclusive`, on a timeout, or on an absent tool.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

A0 = Path("/home/ebt/rsi-dev/a0")
CL = A0 / "closure"

SUSPECT = re.compile(
    r"timed? ?out|rc=124|returncode.?124|command_ran.\"?:? ?false|absent tool|not installed|"
    r"inconclusive|unprobed|never observed|command never ran",
    re.I,
)
BOTH_CONTROLS = re.compile(r"(positive control|unblocked|egress=OPEN|egress_open|OPEN)", re.I)
BLOCKED = re.compile(r"(egress=BLOCKED|egress_blocked|network_reached.\"?:? ?false|egress_ok.\"?:? ?false)", re.I)


def main():
    report = {"closed_mechanisms": [], "suspect": [], "verdict_counts": {}}
    counts = {}
    for f in sorted(CL.glob("closure.??*.json")):
        if f.name == "closure.reconciliation.json":
            continue
        d = json.loads(f.read_text())
        rt = d.get("runtime")
        counts[d["verdict"]] = counts.get(d["verdict"], 0) + 1
        for m in d.get("mechanisms", []):
            sv = m.get("schema_verdict")
            rec = {"runtime": rt, "id": m.get("id"), "schema_verdict": sv,
                   "study_verdict": m.get("study_verdict")}
            blob = json.dumps(m)
            rec["has_unblocked_control"] = bool(BOTH_CONTROLS.search(blob))
            rec["has_blocked_case"] = bool(BLOCKED.search(blob))
            rec["suspect_text"] = sorted(set(SUSPECT.findall(blob)))
            rec["probe_status"] = m.get("probe_status")
            report["closed_mechanisms"].append(rec)
            if sv == "closed" and not (rec["has_unblocked_control"] and rec["has_blocked_case"]):
                report["suspect"].append(
                    {**rec, "why": "schema_verdict=closed without both controls in the record"})
            if sv == "closed" and rec["probe_status"] and "NOT PROBED" in str(rec["probe_status"]):
                report["suspect"].append({**rec, "why": "closed but probe_status says NOT PROBED"})
        # residual channels / unverified blocks
    report["verdict_counts"] = counts

    # scan the raw evidence logs for the two-control pattern
    ev = CL / "evidence"
    log_scan = {}
    for p in sorted(ev.iterdir()):
        if p.suffix not in (".log", ".txt", ".jsonl", ".json"):
            continue
        t = p.read_text(errors="replace")
        if len(t) > 3_000_000:
            t = t[:3_000_000]
        log_scan[p.name] = {
            "mentions_OPEN": bool(re.search(r"egress=OPEN|egress_OK|A0_LANE_EGRESS_OK", t)),
            "mentions_BLOCKED": bool(re.search(r"egress=BLOCKED", t)),
            "mentions_CLOSED_verdict": bool(re.search(r"\bCLOSED\b|\bclosed\b", t)),
            "mentions_CONFIRMED": bool(re.search(r"CONFIRMED", t)),
            "mentions_inconclusive": bool(re.search(r"inconclusive", t, re.I)),
            "mentions_timeout_or_124": bool(re.search(r"timed out|rc=124|returncode.?124", t, re.I)),
        }
    report["evidence_log_scan"] = log_scan

    (A0 / "verify/out/closure_scan.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["verdict_counts"]))
    print("\nCLOSED mechanisms:")
    for r in report["closed_mechanisms"]:
        if r["schema_verdict"] == "closed":
            print(f"  {r['runtime']:<11} {r['id']:<28} unblocked_ctl={r['has_unblocked_control']} "
                  f"blocked_case={r['has_blocked_case']} suspect={r['suspect_text']}")
    print("\nSUSPECT:")
    for s in report["suspect"]:
        print("  ", s.get("runtime"), s.get("id"), "->", s["why"])
    print("\nnon-closed / other verdicts:")
    for r in report["closed_mechanisms"]:
        if r["schema_verdict"] != "closed":
            print(f"  {r['runtime']:<11} {r['id']:<28} {r['schema_verdict']} "
                  f"(study: {str(r['study_verdict'])[:60]})")
    return 1 if report["suspect"] else 0


if __name__ == "__main__":
    sys.exit(main())
