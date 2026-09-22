#!/usr/bin/env python3
"""Harness-owned recomputation of the cut, from graph.json + partition.json.

This is a deliberate second implementation of the objective, independent of
MQLib and independent of the driver that produced the partition.  The candidate
(here: MQLib) never reports its own score -- this program is the only author of
the authoritative integer.

Usage:
    python3 verify_partition.py <graph.json> <partition.json>
    # prints the integer cut_edges on stdout; exit 0

Exit codes: 0 ok, 2 invalid artifact (per INTERFACE.md section 6 rule 2).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import cut_edges_exact, file_sha256, load_graph  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    gpath, ppath = sys.argv[1], sys.argv[2]
    graph = load_graph(gpath)
    with open(ppath, "rb") as fh:
        raw = fh.read()
    try:
        part = json.loads(raw.decode("ascii"))
    except Exception as exc:
        print("invalid: %r" % (exc,), file=sys.stderr)
        return 2
    if part.get("schema") != "a0.maxcut.partition/v1":
        print("invalid: schema", file=sys.stderr)
        return 2
    if part.get("graph_id") != graph.get("graph_id"):
        print("invalid: graph_id mismatch", file=sys.stderr)
        return 2
    try:
        cut = cut_edges_exact(graph, part.get("assignment"))
    except ValueError as exc:
        print("invalid: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps({
        "graph_id": graph["graph_id"],
        "graph_sha256": file_sha256(gpath),
        "partition_sha256": file_sha256(ppath),
        "cut_edges": cut,
        "edges_total": len(graph["edges"]),
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
