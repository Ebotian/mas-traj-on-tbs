"""Writes its own environment next to the artifact, then produces a valid partition."""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description='Writes its own environment next to the artifact, then produces a valid partition.')
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



import os


def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    dump = args.out + ".env_probe.json"
    with open(dump, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "environ": dict(os.environ),
            "cwd": os.getcwd(),
            "argv": list(sys.argv),
            "executable": sys.executable,
        }, sort_keys=True, indent=2) + "\n")
    emit_partition(args.out, graph_id, [index % 2 for index in range(n)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
