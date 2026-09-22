#!/usr/bin/env python3
"""`b_i`: the frozen baseline candidate for the T1 max-cut task.

One seeded **uniform random bisection** of the graph's `n` nodes, and nothing
else.  There is no search, no local move, no restart: the point of `b_i` is to
be the floor that the positive control `p_i = PC_i` has to clear, and to be
cheap, exact and boring.

    b_i  =  assignment[v] = bit v of splitmix64(seed ^ BACKBONE),  v = 0..n-1

Two properties are load-bearing.

* **Reproducibility is a function of `(graph bytes, seed)`, not of the
  interpreter.**  The stream is the same splitmix64 the frozen suite's
  generators use (`../suite/`, `../generators/maxcut_suite.py`), not CPython's
  `random`: `random`'s algorithm is an implementation detail of one interpreter
  build, and `INTERFACE.md` §2 already settled this question for the data by
  refusing to let an RNG implementation into an identity.
* **`--seed` is the evaluator's, not ours.**  §4 hands the candidate
  `--seed <int>`; the baseline consumes exactly that integer and invents no
  random state of its own.  Two invocations with the same graph bytes and the
  same seed are therefore byte-identical, which is what §6 rule 4 tests.

The candidate never reports a score (§4): it writes §3's `partition.json` and
exits 0.  `cut_edges` is recomputed by E* from the graph and this partition.
"""

import argparse
import json

MASK64 = (1 << 64) - 1

#: Frozen keying constant.  b_i uses the *same* stream and the *same* keying as
#: `C*(T1)`'s `c02_ok_low_baseline`, so the two agree byte-for-byte; that
#: equality is one of the checks in `../build.py`, not an assumption.
BACKBONE = 0xA5A5A5A5A5A5A5A5


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


def load_graph(path):
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    return document["graph_id"], int(document["n"])


def emit_partition(path, graph_id, assignment):
    payload = {
        "schema": "a0.maxcut.partition/v1",
        "graph_id": graph_id,
        "assignment": assignment,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def random_partition(n, seed):
    rng = Rng(int(seed) ^ BACKBONE)
    return [rng.bit() for _ in range(n)]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    graph_id, n = load_graph(args.graph)
    emit_partition(args.out, graph_id, random_partition(n, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
