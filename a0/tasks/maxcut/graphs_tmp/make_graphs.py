#!/usr/bin/env python3
"""Temporary canonical graphs for T1, used until `suite/manifest.json` exists.

The real suite is owned by another worker (`a0/tasks/maxcut/suite/`); this script
never writes there.  It emits `graph.json` files in exactly the canonical form
`INTERFACE.md` §2 freezes, so every measurement taken against them stays valid
when the frozen suite replaces them (the *identity* of a graph is its file
sha256, and the form is the same).

Determinism: the pseudo-random stream comes from SHA-256 over a domain-separated
seed string, not from `random`/`hashlib` internals, so the emitted bytes are a
function of the arguments alone and reproduce on any interpreter.

    python3 graphs_tmp/make_graphs.py            # -> graphs_tmp/tmp_suite/dev + graphs_tmp/tmp_suite/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def stream(key: str) -> "Random":
    return Random(key)


class Random:
    """A tiny counter-mode SHA-256 byte stream: reproducible everywhere."""

    def __init__(self, key: str) -> None:
        self._key = key.encode("utf-8")
        self._counter = 0
        self._buf = b""

    def _next_byte(self) -> int:
        if not self._buf:
            self._buf = hashlib.sha256(
                b"a0.maxcut.tmpgraph/v1\x00" + self._key + self._counter.to_bytes(8, "big")
            ).digest()
            self._counter += 1
        value = self._buf[0]
        self._buf = self._buf[1:]
        return value

    def below(self, bound: int) -> int:
        """Uniform-ish integer in [0, bound) via rejection sampling."""
        assert bound > 0
        size = max(1, (bound - 1).bit_length() // 8 + 1)
        while True:
            value = 0
            for _ in range(size):
                value = (value << 8) | self._next_byte()
            if value < (1 << (8 * size)) - ((1 << (8 * size)) % bound):
                return value % bound

    def unit(self) -> float:
        value = 0
        for _ in range(7):
            value = (value << 8) | self._next_byte()
        return value / float(1 << 56)


def canonical_bytes(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def normalise_edges(n: int, raw: list[tuple[int, int]]) -> list[list[int]]:
    seen = set()
    for u, v in raw:
        assert u != v, "self-loop"
        u, v = (u, v) if u < v else (v, u)
        assert 0 <= u < n and 0 <= v < n, f"node out of range: {(u, v)}"
        seen.add((u, v))
    return [[u, v] for u, v in sorted(seen)]


def er(n: int, m: int, rng: Random) -> list[list[int]]:
    seen: set[tuple[int, int]] = set()
    guard = 0
    while len(seen) < m and guard < 200 * (m + 1):
        guard += 1
        u, v = rng.below(n), rng.below(n)
        if u != v:
            seen.add((min(u, v), max(u, v)))
    return normalise_edges(n, list(seen))


def rr(n: int, degree: int, rng: Random) -> list[list[int]]:
    """Union of `degree` random Hamilton-ish cycles: exactly regular, no multi-edges."""
    raw: list[tuple[int, int]] = []
    for _ in range(max(1, degree // 2)):
        order = list(range(n))
        for i in range(n - 1, 0, -1):
            j = rng.below(i + 1)
            order[i], order[j] = order[j], order[i]
        for i in range(n):
            raw.append((order[i], order[(i + 1) % n]))
    return normalise_edges(n, raw)


def ba(n: int, m: int, rng: Random) -> list[list[int]]:
    """Preferential attachment.  `pool` is the set of *distinct* endpoints seen so
    far; drawing from the raw (duplicate-carrying) preference list can never
    satisfy a distinctness quota when the list holds fewer than `m` distinct
    values, which is an infinite loop."""
    preference = [0, 1]
    raw = [(0, 1)]
    for node in range(2, n):
        pool = sorted(set(preference))
        chosen: set[int] = set()
        while len(chosen) < min(m, len(pool)):
            chosen.add(pool[rng.below(len(pool))])
        for pick in sorted(chosen):
            raw.append((node, pick))
            preference.append(node)
            preference.append(pick)
    return normalise_edges(n, raw)


def planted(n: int, m: int, rng: Random, minority: float = 0.35) -> list[list[int]]:
    """Two planted sides with a controllable crossing rate; labels are not emitted."""
    side = [0 if rng.unit() < minority else 1 for _ in range(n)]
    seen: set[tuple[int, int]] = set()
    guard = 0
    while len(seen) < m and guard < 300 * (m + 1):
        guard += 1
        u, v = rng.below(n), rng.below(n)
        if u == v:
            continue
        crossing = side[u] != side[v]
        if crossing and rng.unit() > 0.3:
            continue
        seen.add((min(u, v), max(u, v)))
    return normalise_edges(n, list(seen))


def build(spec: dict[str, object]) -> dict[str, object]:
    graph_id = str(spec["graph_id"])
    family = str(spec["family"])
    n = int(spec["n"])  # type: ignore[arg-type]
    rng = stream(f"{graph_id}|{family}|{n}|{spec['seed']}")
    if family == "ER":
        edges = er(n, int(spec["m"]), rng)  # type: ignore[arg-type]
    elif family == "RR":
        edges = rr(n, int(spec["degree"]), rng)  # type: ignore[arg-type]
    elif family == "BA":
        edges = ba(n, int(spec["attach"]), rng)  # type: ignore[arg-type]
    elif family == "Planted":
        edges = planted(n, int(spec["m"]), rng)  # type: ignore[arg-type]
    else:
        raise ValueError(f"unknown family {family!r}")
    touching = set()
    for u, v in edges:
        touching.add(u)
        touching.add(v)
    return {
        "schema": "a0.maxcut.graph/v1",
        "graph_id": graph_id,
        "family": family,
        "n": n,
        "edges": edges,
        "generator": {
            "name": "a0/tasks/maxcut/graphs_tmp/make_graphs.py",
            "version": "1.0.0",
            "params": {k: v for k, v in spec.items() if k not in ("graph_id", "family", "seed")},
            "seed": int(spec["seed"]),  # type: ignore[arg-type]
        },
        "notes": "TEMPORARY graph (task-owned stand-in until suite/manifest.json lands)",
    }


# --------------------------------------------------------------------------- #
# the float-vs-rational demonstration sets
# --------------------------------------------------------------------------- #

# The demonstration candidate assigns `vertex % 2`, so an edge is cut exactly
# when its endpoints have opposite parity.  Each graph below is therefore a
# precise number of "cut" edges plus filler edges that the candidate leaves
# uncut, which makes the achieved cut a construction parameter rather than a
# hope.  See `float_tie/README.md`.
FLOAT_TIE_A_CUTS = [1, 1, 2, 4, 5, 7]
FLOAT_TIE_B_CUTS = [0, 0, 1, 2, 2, 2, 3]


def _parity_graph(graph_id: str, edges_total: int, want_cut: int, seed: int) -> dict[str, object]:
    rng = stream(f"float_tie|{graph_id}|{seed}")
    n = 2 * edges_total + 2
    raw: list[tuple[int, int]] = []
    pool_cut = [(u, v) for u in range(n) for v in range(n) if u < v and (u % 2) != (v % 2)]
    pool_same = [(u, v) for u in range(n) for v in range(n) if u < v and (u % 2) == (v % 2)]
    for _ in range(want_cut):
        raw.append(pool_cut.pop(rng.below(len(pool_cut))))
    for _ in range(edges_total - want_cut):
        raw.append(pool_same.pop(rng.below(len(pool_same))))
    return {
        "schema": "a0.maxcut.graph/v1",
        "graph_id": graph_id,
        "family": "Planted",
        "n": n,
        "edges": normalise_edges(n, raw),
        "generator": {
            "name": "a0/tasks/maxcut/graphs_tmp/make_graphs.py::float_tie",
            "version": "1.0.0",
            "params": {"edges_total": edges_total, "cut_edges_under_parity_candidate": want_cut},
            "seed": seed,
        },
        "notes": "DEMONSTRATION graph for the exact-aggregation proof (see float_tie/README.md)",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="emit temporary canonical max-cut graphs")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args(argv)
    out = Path(args.out)
    temp_suite = out / "tmp_suite"
    graph_dir = temp_suite / "dev"
    graph_dir.mkdir(parents=True, exist_ok=True)

    specs: list[dict[str, object]] = []
    plan = [
        ("ER", 64, {"m": 320}), ("ER", 96, {"m": 576}),
        ("RR", 60, {"degree": 6}), ("RR", 80, {"degree": 8}),
        ("BA", 72, {"attach": 3}), ("BA", 100, {"attach": 4}),
        ("Planted", 64, {"m": 320}), ("Planted", 96, {"m": 576}),
    ]
    for index, (family, n, params) in enumerate(plan, start=1):
        specs.append({
            "graph_id": f"G_tmp_{index:04d}", "family": family, "n": n,
            "seed": 20260922 + index, **params,
        })

    entries = []
    for spec in specs:
        document = build(spec)
        payload = canonical_bytes(document)
        target = graph_dir / f"{document['graph_id']}.json"
        target.write_bytes(payload)
        entries.append({
            "graph_id": document["graph_id"],
            "family": document["family"],
            "n": document["n"],
            "edges_total": len(document["edges"]),  # type: ignore[arg-type]
            "isolated_vertices": int(document["n"]) - len({v for e in document["edges"] for v in e}),  # type: ignore[union-attr]
            "path": target.name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "canonical": payload == canonical_bytes(json.loads(payload)),
        })

    tie_root = Path(__file__).resolve().parent
    for name, cuts in (("A", FLOAT_TIE_A_CUTS), ("B", FLOAT_TIE_B_CUTS)):
        size = 7 if name == "A" else 3
        # Laid out as `float_tie_<name>/dev/` so that E*'s frozen `aggregate
        # --graph-set dev --suite-root <root>` CLI shape applies unchanged; the
        # directory stands in for a dev set until the frozen suite lands.
        directory = tie_root / f"float_tie_{name}" / "dev"
        directory.mkdir(parents=True, exist_ok=True)
        for index, want in enumerate(cuts, start=1):
            graph_id = f"G_tie_{name}_{index:02d}"
            document = _parity_graph(graph_id, size, want, 7000 + index + (0 if name == "A" else 100))
            payload = canonical_bytes(document)
            (directory / f"{graph_id}.json").write_bytes(payload)
            entries.append({
                "graph_id": graph_id, "family": "Planted", "n": document["n"],
                "edges_total": len(document["edges"]),  # type: ignore[arg-type]
                "isolated_vertices": int(document["n"]) - len({v for e in document["edges"] for v in e}),  # type: ignore[union-attr]
                "path": f"float_tie_{name}/dev/{graph_id}.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "canonical": payload == canonical_bytes(json.loads(payload)),
                "graph_set": f"float_tie_{name}/dev",
                "expected_parity_cut": want,
            })

    manifest = {
        "schema": "a0.maxcut.manifest/v1",
        "kind": "TEMPORARY (task-owned stand-in; not the frozen suite)",
        "graph_count": len(entries),
        "graphs": sorted(entries, key=lambda entry: entry["graph_id"]),
    }
    (out / "tmp_manifest.json").write_bytes(canonical_bytes(manifest))
    # A manifest in the shape E*'s `discover_graphs` verifies, so the
    # data-identity path is exercised before the frozen suite exists.
    (temp_suite / "manifest.json").write_bytes(canonical_bytes({
        "schema": "a0.maxcut.manifest/v1",
        "kind": "TEMPORARY stand-in for the frozen suite manifest",
        "graph_set": "dev",
        "graph_count": len([entry for entry in entries if entry["path"].startswith("G_tmp_")]),
        "graphs": [
            {k: entry[k] for k in ("graph_id", "family", "n", "edges_total", "isolated_vertices", "sha256")}
            for entry in sorted(entries, key=lambda entry: entry["graph_id"])
            if entry["path"].startswith("G_tmp_")
        ],
    }))
    non_canonical = [entry["graph_id"] for entry in entries if not entry["canonical"]]
    print(f"wrote {len(entries)} graphs under {out}; non-canonical: {non_canonical or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
