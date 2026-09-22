"""Raises an uncaught exception: the process dies with a foreign exit code."""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description='Raises an uncaught exception: the process dies with a foreign exit code.')
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
    raise RuntimeError("c11_error_raises: deliberate crash after reading " + str((graph_id, n, len(edges))))


if __name__ == "__main__":
    raise SystemExit(main())
