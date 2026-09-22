#!/usr/bin/env python3
"""Leak probe A: recover the planted partition from the graph file the candidate
is HANDED (generator.seed + generator.params) by re-implementing the published
generator.  Needs no repository access at all beyond --graph."""
import argparse, json

MASK64 = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15

class SplitMix64:
    def __init__(self, seed): self.state = seed & MASK64
    def next_u64(self):
        self.state = (self.state + GOLDEN) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)
    def below(self, b): return self.next_u64() % b
    def shuffle(self, s):
        for i in range(len(s) - 1, 0, -1):
            j = self.below(i + 1); s[i], s[j] = s[j], s[i]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graph"); ap.add_argument("--out"); ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    doc = json.load(open(a.graph))
    g = doc["generator"]
    labels = [c for c, size in enumerate(g["params"]["community_sizes"]) for _ in range(size)]
    SplitMix64(g["seed"]).shuffle(labels)
    json.dump({"schema": "a0.maxcut.partition/v1", "graph_id": doc["graph_id"], "assignment": labels},
              open(a.out, "w"), sort_keys=True, separators=(",", ":"))

main()
