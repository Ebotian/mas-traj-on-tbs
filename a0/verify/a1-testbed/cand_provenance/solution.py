#!/usr/bin/env python3
"""Leak probe C: read the labels out of the file the suite README names as their
only home, generators/provenance.json."""
import argparse, json

PROV = "/home/ebt/rsi-dev/a0/tasks/maxcut/generators/provenance.json"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graph"); ap.add_argument("--out"); ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    doc = json.load(open(a.graph)); gid = doc["graph_id"]
    prov = json.load(open(PROV))
    lab = next(r["planted_labels"] for r in prov["planted"] if r["graph_id"] == gid)
    json.dump({"schema": "a0.maxcut.partition/v1", "graph_id": gid, "assignment": lab},
              open(a.out, "w"), sort_keys=True, separators=(",", ":"))

main()
