#!/usr/bin/env python3
"""Print the headline numbers of the reference table, per family.

    python3 tools/summarize_targets.py targets.json [logs]
"""
import json
import os
import sys
from collections import defaultdict


def main():
    with open(sys.argv[1]) as fh:
        doc = json.load(fh)
    graphs = doc["graphs"]

    mismatches = []
    if len(sys.argv) > 2:
        rdir = os.path.join(sys.argv[2], "runs")
        for fn in sorted(os.listdir(rdir)):
            with open(os.path.join(rdir, fn)) as fh:
                r = json.load(fh)
            if r.get("status") == "ok" and not r.get("mqlib_reported_matches_recomputed"):
                mismatches.append(fn)

    fam = defaultdict(lambda: {"n": 0, "cert": 0, "gaps": []})
    cert = 0
    gaps = []
    halo = []
    for gid, e in sorted(graphs.items()):
        f = fam[e.get("family") or "?"]
        f["n"] += 1
        if e.get("opt_certified"):
            cert += 1
            f["cert"] += 1
        if e.get("U") is not None:
            g = e["U"] - e["R"]
            gaps.append(g)
            f["gaps"].append(g)
            halo.append((g, gid, e["R"], e["U"]))
        f.setdefault("sr", [])
        f["sr"].append(e.get("graph_sha256_matches_manifest"))

    print("graphs in table            : %d" % len(graphs))
    print("sha256 matches the manifest: %d/%d"
          % (sum(1 for e in graphs.values() if e.get("graph_sha256_matches_manifest")),
             len(graphs)))
    print("OPT certified              : %d/%d" % (cert, len(graphs)))
    if gaps:
        print("U - R gap  : min=%d  median=%s  max=%d  (n=%d)"
              % (min(gaps), sorted(gaps)[len(gaps) // 2], max(gaps), len(gaps)))
    print("MQLib-reported vs recomputed mismatches: %s"
          % (mismatches if mismatches else "none"))
    print()
    print("%-9s %5s %6s  %-22s" % ("family", "n", "cert", "U-R (min/med/max)"))
    for f in sorted(fam):
        v = fam[f]
        if v["gaps"]:
            gs = sorted(v["gaps"])
            span = "%d / %d / %d" % (gs[0], gs[len(gs) // 2], gs[-1])
        else:
            span = "-"
        print("%-9s %5d %6d  %-22s" % (f, v["n"], v["cert"], span))
    if halo:
        halo.sort(reverse=True)
        print()
        print("largest remaining gaps (U-R):")
        for g, gid, r, u in halo[:8]:
            print("  %-14s R=%-5d U=%-5d gap=%d" % (gid, r, u, g))


if __name__ == "__main__":
    main()
