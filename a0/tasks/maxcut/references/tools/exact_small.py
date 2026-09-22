#!/usr/bin/env python3
"""Exhaustive Max-Cut optimum for tiny graphs (n <= ~26).  Validation only.

Used to check the whole chain (MQLib output -> partition.json -> independent
recomputation -> R_i) against a ground truth that shares no code with it.

    python3 exact_small.py <graph.json>
    # prints {"optimal_cut": k, "assignment": [...]}
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import load_graph  # noqa: E402


def brute_force(graph, chunk=1 << 20):
    n = graph["n"]
    edges = graph["edges"]
    U = np.array([e[0] for e in edges], dtype=np.int64)
    V = np.array([e[1] for e in edges], dtype=np.int64)
    # node 0 is pinned to part 0 by the sign-flip symmetry
    free = n - 1
    best, best_idx = -1, None
    for start in range(0, 1 << free, chunk):
        stop = min(start + chunk, 1 << free)
        idx = np.arange(start, stop, dtype=np.int64)
        bits = ((idx[:, None] >> np.arange(free, dtype=np.int64)[None, :]) & 1).astype(np.uint8)
        A = np.concatenate([np.zeros((bits.shape[0], 1), dtype=np.uint8), bits], axis=1)
        cut = (A[:, U] != A[:, V]).sum(axis=1)
        loc = int(np.argmax(cut))
        if int(cut[loc]) > best:
            best = int(cut[loc])
            best_idx = int(idx[loc])
    bits = [(best_idx >> k) & 1 for k in range(free)]
    return best, [0] + bits


def main():
    graph = load_graph(sys.argv[1])
    if graph["n"] > 30:
        raise SystemExit("n too large for brute force: %d" % graph["n"])
    best, asm = brute_force(graph)
    print(json.dumps({"graph_id": graph["graph_id"], "n": graph["n"],
                      "edges_total": len(graph["edges"]),
                      "optimal_cut": best, "assignment": asm},
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
