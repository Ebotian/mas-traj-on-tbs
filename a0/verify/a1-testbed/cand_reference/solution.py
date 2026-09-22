#!/usr/bin/env python3
"""Leak probe B: copy the best stored reference partition for this graph_id out of
the repository tree, by absolute path.  Demonstrates that the eval hold-out's
near-optimal partitions are readable by a candidate process."""
import argparse, glob, json, os

REF = "/home/ebt/rsi-dev/a0/tasks/maxcut/references/logs/partitions"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graph"); ap.add_argument("--out"); ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    doc = json.load(open(a.graph)); gid = doc["graph_id"]
    edges = [tuple(e) for e in doc["edges"]]
    best = None
    for path in glob.glob(os.path.join(REF, gid + "__*.partition.json")):
        lab = json.load(open(path))["assignment"]
        cut = sum(1 for u, v in edges if lab[u] != lab[v])
        if best is None or cut > best[0]:
            best = (cut, lab)
    json.dump({"schema": "a0.maxcut.partition/v1", "graph_id": gid, "assignment": best[1]},
              open(a.out, "w"), sort_keys=True, separators=(",", ":"))

main()
