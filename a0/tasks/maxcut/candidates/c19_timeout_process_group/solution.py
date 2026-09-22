"""Ignores SIGTERM, forks a heartbeat grandchild, sleeps forever: only a group SIGKILL stops it."""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description='Ignores SIGTERM, forks a heartbeat grandchild, sleeps forever: only a group SIGKILL stops it.')
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
import signal
import time


def main():
    args = parse_args()
    load_graph(args.graph)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    heartbeat = args.out + ".orphan_heartbeat"
    try:
        pid = os.fork()
    except OSError:
        pid = 0
    if pid == 0:
        # The grandchild.  It knows nothing about tau, so it does not try to
        # outlive a deadline; it just proves liveness by counting.  If the
        # harness killed only the direct child, this count keeps rising after
        # the verdict was taken, and the parent's probe sees it move.
        while True:
            with open(heartbeat, "a", encoding="utf-8") as handle:
                handle.write("beat\n")
                handle.flush()
                os.fsync(handle.fileno())
            time.sleep(0.25)
        os._exit(0)
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
