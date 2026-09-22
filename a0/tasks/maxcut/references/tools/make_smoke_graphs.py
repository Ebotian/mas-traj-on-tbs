#!/usr/bin/env python3
"""Generate smoke graphs in the canonical a0.maxcut form.

These are *my own* validation graphs -- never the frozen suite.  The suite is
owned by another worker (a0/tasks/maxcut/suite/); nothing here writes there.

Families follow the INTERFACE.md section 2 vocabulary: ER | RR | BA | Planted.

Usage:
    python3 make_smoke_graphs.py <outdir>
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import write_canonical  # noqa: E402


def _finish(edges, n):
    es = sorted({(u, v) for (u, v) in edges if u != v})
    return [[u, v] for (u, v) in es]


def er(n, p, rng):
    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < p:
                edges.append((u, v))
    return _finish(edges, n)


def rr(n, d, rng):
    """random regular-ish: each node joined to its d nearest-in-a-random-order neighbours"""
    order = list(range(n))
    rng.shuffle(order)
    edges = []
    for i, u in enumerate(order):
        for k in range(1, d // 2 + 1):
            v = order[(i + k) % n]
            edges.append((min(u, v), max(u, v)))
    return _finish(edges, n)


def ba(n, m, rng):
    """Barabasi-Albert preferential attachment, seed core of size m."""
    targets = [0, 1]
    repeated = []
    edges = []
    for u in range(1, m + 1):
        edges.append((0, u))
        repeated.extend((0, u))
    for v in range(m + 1, n):
        chosen = set()
        while len(chosen) < m:
            chosen.add(repeated[rng.randrange(len(repeated))])
        for u in chosen:
            edges.append((min(u, v), max(u, v)))
        repeated.extend(chosen)
        repeated.append(v)
    return _finish(edges, n)


def planted(n, p_in, p_out, rng):
    """planted bisection: the ground-truth partition is the generator seed's, not the data's"""
    side = [rng.randrange(2) for _ in range(n)]
    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            q = p_in if side[u] == side[v] else p_out
            if rng.random() < q:
                edges.append((u, v))
    return _finish(edges, n)


def make(graph_id, family, n, gen_name, params, edges):
    return graph_id, {
        "schema": "a0.maxcut.graph/v1",
        "graph_id": graph_id,
        "family": family,
        "n": n,
        "edges": edges,
        "generator": {"name": gen_name, "version": "1", "params": params,
                      "seed": params.get("seed")},
        "notes": "smoke graph for references-pipeline validation (not the frozen suite)",
    }


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    os.makedirs(outdir, exist_ok=True)
    specs = [
        ("S_er_128", "ER", 128, "er", {"n": 128, "p": 0.5, "seed": 20260922}, lambda r: er(128, 0.5, r)),
        ("S_ba_128", "BA", 128, "ba", {"n": 128, "m": 3, "seed": 20260922}, lambda r: ba(128, 3, r)),
        ("S_planted_128", "Planted", 128, "planted",
         {"n": 128, "p_in": 0.8, "p_out": 0.2, "seed": 20260922},
         lambda r: planted(128, 0.8, 0.2, r)),
        ("S_rr_64", "RR", 64, "rr", {"n": 64, "d": 8, "seed": 20260922}, lambda r: rr(64, 8, r)),
        ("S_er_24", "ER", 24, "er", {"n": 24, "p": 0.5, "seed": 20260922}, lambda r: er(24, 0.5, r)),
    ]
    manifest = {"schema": "a0.maxcut.smoke.manifest/v1", "graphs": []}
    for gid, fam, n, gname, params, fn in specs:
        rng = random.Random(params["seed"])
        gid, g = make(gid, fam, n, gname, params, fn(rng))
        path = os.path.join(outdir, gid + ".json")
        sha = write_canonical(path, g)
        deg = [0] * n
        for u, v in g["edges"]:
            deg[u] += 1
            deg[v] += 1
        manifest["graphs"].append({
            "graph_id": gid, "family": fam, "n": n, "edges_total": len(g["edges"]),
            "sha256": sha, "isolated": sum(1 for d in deg if d == 0),
            "path": os.path.relpath(path),
        })
        print(gid, fam, "n=", n, "|E|=", len(g["edges"]), sha[:16])
    write_canonical(os.path.join(outdir, "manifest.json"), manifest)


if __name__ == "__main__":
    main()
