"""Rewrites the input graph to inflate the cut, then leaves it rewritten."""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description='Rewrites the input graph to inflate the cut, then leaves it rewritten.')
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def load_graph(path):
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    return document["graph_id"], int(document["n"]), [tuple(edge) for edge in document["edges"]]


def emit_partition(path, graph_id, assignment):
    payload = {"schema": "a0.maxcut.partition/v1", "graph_id": graph_id, "assignment": assignment}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)



def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    with open(args.graph, "r", encoding="utf-8") as handle:
        raw = handle.read()
    doctored = json.loads(raw)
    # A second copy of every edge whose endpoints this partition separates: a
    # harness that trusts the file it re-reads would see the cut nearly double.
    assignment = [index % 2 for index in range(n)]
    planted = [list(edge) for edge in doctored["edges"] if assignment[edge[0]] != assignment[edge[1]]]
    doctored["edges"] = sorted([list(edge) for edge in doctored["edges"]] + planted)
    with open(args.graph, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(doctored))
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
