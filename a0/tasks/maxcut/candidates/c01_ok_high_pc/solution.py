"""Deterministic multi-start local search for unweighted max-cut (the 'PC' candidate)."""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Deterministic multi-start local search for unweighted max-cut (the 'PC' candidate).")
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


MASK64 = (1 << 64) - 1


class Rng:
    """splitmix64: the same bits on every interpreter, so `--seed` alone decides
    the stream (unlike `random`, whose algorithm is a CPython implementation
    detail this candidate must not depend on)."""

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


def adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def cut_size(edges, assignment):
    """The candidate's own search signal.  It is never written to the artifact:
    the harness recomputes the cut from the graph and the partition."""
    return sum(1 for u, v in edges if assignment[u] != assignment[v])


def local_optimum(n, adj, assignment):
    """Steepest-ascent 1-flip descent to a local optimum, in a fixed vertex
    order so the result is a function of the input assignment alone.

    `gain[v]` is the exact change in cut size that flipping v would produce:
    same-side neighbours become cut and cut neighbours stop being cut, so
    `gain[v] = 2*same - degree`.  Positive gain therefore means "flipping
    improves", which is the direction this descent moves.
    """
    gain = [0] * n
    for v in range(n):
        same = sum(1 for w in adj[v] if assignment[w] == assignment[v])
        gain[v] = 2 * same - len(adj[v])
    moved = True
    while moved:
        moved = False
        for v in range(n):
            if gain[v] > 0:
                assignment[v] ^= 1
                moved = True
                gain[v] = -gain[v]
                for w in adj[v]:
                    gain[w] += 2 if assignment[w] == assignment[v] else -2
    return assignment


def best_of_restarts(n, edges, seed, starts, greedy=False):
    adj = adjacency(n, edges)
    rng = Rng(seed)
    best, best_cut = None, -1
    for start in range(starts):
        if greedy and start == 0:
            assignment = [0] * n
        else:
            assignment = [rng.bit() for _ in range(n)]
        local_optimum(n, adj, assignment)
        value = cut_size(edges, assignment)
        if value > best_cut:
            best_cut, best = value, list(assignment)
    return best



def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    assignment = best_of_restarts(n, edges, args.seed, starts=8, greedy=True)
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
