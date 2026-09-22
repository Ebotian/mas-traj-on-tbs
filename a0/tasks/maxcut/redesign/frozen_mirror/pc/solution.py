#!/usr/bin/env python3
"""`PC_i`: the contract's known-effective external artifact, made reproducible.

The contract names it exactly:

    PC_i  =  networkx.algorithms.approximation.one_exchange(
                 G_i, initial_cut = b_i, seed = s_i)

at NetworkX commit ``b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b`` (BSD-3-Clause).
The pinned source of that function is kept verbatim next to this file as
``pinned/networkx_maxcut_b69beb2c.py`` (sha256
``793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb``, which is
also the sha256 of the ``maxcut.py`` shipped in the networkx 3.6.1 wheel).

This file is a **line-for-line transliteration** of the pinned function, not a
re-implementation:

* the shuffle-then-``max`` loop, including that ``max`` is over a *freshly
  shuffled* ``list(range(n))`` on every round and that ``max`` returns the
  **first** maximiser, is transcribed unchanged from the pin;
* ``seed`` is realised exactly as the pin's ``@py_random_state(2)`` does for an
  integer: ``random.Random(seed)``;
* ``nx.algorithms.cut_size(G, cut, weight=None)`` is replaced by an
  unweighted-only equivalent (count the edges with exactly one endpoint in
  ``cut``); the graphs are weight-1 by construction (§2) and the pin's default
  ``weight=None`` means exactly this count.

Why a transliteration rather than ``import networkx``: §4 runs the candidate in
a private scratch directory with a minimal environment and no injected files,
so a candidate that depended on an ambient site-packages would be a candidate
whose identity is whatever happens to be installed.  This file's identity is its
own bytes.  ``../verify_pc_identity.py`` discharges the obvious objection — that
a transliteration might drift from the pin — by running both this file and the
real pinned NetworkX over the whole frozen suite and requiring the returned cut
value *and* the returned partition to be equal on every graph.

Frozen identity of one PC run (see ``../README.md`` §3):

    (graph_sha256, b_i, s_i, networkx_commit, interpreter_version)

``b_i`` is computed here from the same splitmix64 stream as the baseline
candidate ``../baseline/solution.py``, so PC_i is the artifact *applied to*
b_i rather than to something else.  ``../build.py`` checks the two agree
byte-for-byte.  The orientation convention

    initial_cut = { v : b_i[v] == 1 }

is part of the identity: the complement of b_i has the same cut value but a
different search trajectory, so it is fixed here and nowhere else.
"""

import argparse
import json
import random

MASK64 = (1 << 64) - 1
BACKBONE = 0xA5A5A5A5A5A5A5A5


# --------------------------------------------------------------------------- #
# b_i — the baseline, reproduced exactly as ../baseline/solution.py emits it
# --------------------------------------------------------------------------- #

class Rng:
    """splitmix64 — the same bits on every interpreter, given one seed."""

    def __init__(self, seed):
        self.state = (int(seed) ^ 0x9E3779B97F4A7C15) & MASK64

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def bit(self):
        return self.next_u64() & 1


def baseline_assignment(n, seed):
    rng = Rng(int(seed) ^ BACKBONE)
    return [rng.bit() for _ in range(n)]


# --------------------------------------------------------------------------- #
# the pin's two helpers
# --------------------------------------------------------------------------- #

def _swap_node_partition(cut, node):
    return cut - {node} if node in cut else cut.union({node})


def cut_size(edges, cut):
    """``nx.algorithms.cut_size(G, cut, weight=None)`` for a weight-1 graph."""
    return sum(1 for u, v in edges if (u in cut) != (v in cut))


# --------------------------------------------------------------------------- #
# one_exchange, transcribed from the pin
# --------------------------------------------------------------------------- #

def one_exchange(n, edges, initial_cut, seed):
    """Pinned source: ``pinned/networkx_maxcut_b69beb2c.py``, lines 118-143."""
    if initial_cut is None:
        initial_cut = set()
    cut = set(initial_cut)
    current_cut_size = cut_size(edges, cut)
    rounds = 0
    while True:
        nodes = list(range(n))          # G.nodes(), insertion order 0..n-1
        # Shuffling the nodes ensures random tie-breaks in the following call to max
        seed.shuffle(nodes)
        best_node_to_swap = max(
            nodes,
            key=lambda v: cut_size(edges, _swap_node_partition(cut, v)),
            default=None,
        )
        potential_cut = _swap_node_partition(cut, best_node_to_swap)
        potential_cut_size = cut_size(edges, potential_cut)
        rounds += 1

        if potential_cut_size > current_cut_size:
            cut = potential_cut
            current_cut_size = potential_cut_size
        else:
            break

    return current_cut_size, cut, rounds


def load_graph(path):
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    edges = [(int(u), int(v)) for u, v in document["edges"]]
    return document["graph_id"], int(document["n"]), edges


def emit_partition(path, graph_id, assignment):
    payload = {
        "schema": "a0.maxcut.partition/v1",
        "graph_id": graph_id,
        "assignment": assignment,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def run(graph_path, seed):
    """One PC run.  Returns a dict, so nothing depends on tuple order."""
    graph_id, n, edges = load_graph(graph_path)
    assignment = baseline_assignment(n, seed)
    initial_cut = {v for v in range(n) if assignment[v] == 1}
    value, cut, rounds = one_exchange(n, edges, initial_cut, random.Random(int(seed)))
    return {
        "graph_id": graph_id,
        "assignment": [1 if v in cut else 0 for v in range(n)],
        "cut_value": value,
        "baseline_assignment": assignment,
        "rounds": rounds,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    result = run(args.graph, args.seed)
    emit_partition(args.out, result["graph_id"], result["assignment"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
