#!/usr/bin/env python3
"""Run the *real* pinned NetworkX ``one_exchange`` and print its answer.

This is the reference arm of ``verify_pc_identity.py``.  It is meant to be run
by an interpreter that has NetworkX installed, and it prints what that
installed NetworkX did:

    {"networkx_version": ..., "networkx_maxcut_sha256": ...,
     "graph_id": ..., "seed": ..., "initial_cut_size": ...,
     "cut_value": ..., "partition": [0,1,...]}

``networkx_maxcut_sha256`` is the sha256 of the ``maxcut.py`` the executing
install actually loaded, so the caller can check the install against the pin
rather than trusting ``__version__``.
"""

import argparse
import hashlib
import inspect
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    import networkx as nx
    from networkx.algorithms.approximation import one_exchange

    with open(args.graph, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    graph_id = document["graph_id"]
    n = int(document["n"])
    edges = [(int(u), int(v)) for u, v in document["edges"]]

    # b_i, exactly as ../baseline/solution.py emits it:
    #     splitmix64(seed ^ BACKBONE),  BACKBONE = 0xA5A5A5A5A5A5A5A5
    mask = (1 << 64) - 1
    state = (int(args.seed) ^ 0xA5A5A5A5A5A5A5A5 ^ 0x9E3779B97F4A7C15) & mask
    bits = []
    for _ in range(n):
        state = (state + 0x9E3779B97F4A7C15) & mask
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & mask
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & mask
        bits.append((z ^ (z >> 31)) & 1)
    initial_cut = {v for v in range(n) if bits[v] == 1}

    graph = nx.Graph()
    graph.add_nodes_from(range(n))          # insertion order 0..n-1, as the pin assumes
    graph.add_edges_from(edges)

    cut_value, partition = one_exchange(graph, initial_cut=initial_cut, seed=args.seed)
    cut_set = set(partition[0])
    assignment = [1 if v in cut_set else 0 for v in range(n)]

    from networkx.algorithms.approximation import maxcut as maxcut_module
    if getattr(maxcut_module, "__file__", None):
        maxcut_sha256 = hashlib.sha256(open(maxcut_module.__file__, "rb").read()).hexdigest()
    else:                                    # namespace-package installs
        maxcut_sha256 = hashlib.sha256(
            inspect.getsource(maxcut_module).encode("utf-8")
        ).hexdigest()

    print(json.dumps({
        "networkx_version": nx.__version__,
        "networkx_file": getattr(nx, "__file__", None),
        "networkx_maxcut_file": getattr(maxcut_module, "__file__", None),
        "networkx_maxcut_sha256": maxcut_sha256,
        "python": sys.version.split()[0],
        "graph_id": graph_id,
        "seed": int(args.seed),
        "initial_cut_size": len(initial_cut),
        "cut_value": int(cut_value),
        "partition": assignment,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
