#!/usr/bin/env python3
"""The frozen Max-Cut instance suite: deterministic generators, canonical writer, verifier.

Owns `a0/tasks/maxcut/{suite,generators}/`.  The binding interface is
`a0/tasks/maxcut/INTERFACE.md` (§1 layout, §2 graph files, §9 calibration); any deviation is
recorded in `generators/DEVIATIONS.md`.

Three facts this file is built around:

1. **Identity is the file.**  A graph's identity is the sha256 of its canonical bytes
   (`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"`,
   INTERFACE.md §2).  `build` writes canonically and `verify` re-serialises every file from its
   parsed object and compares the digest, so the identity is checkable without trusting the writer.
2. **Provenance is not identity.**  `graph.json` carries only
   `schema, graph_id, family, n, edges, generator, notes`.  The generator's parameters and seed are
   *distribution* provenance; the planted partition's node labels are *solution* provenance and go
   to `generators/provenance.json`, never under `suite/`.
3. **Regeneration is a check.**  Every graph is re-derived from its recorded
   (generator, params, seed) and compared edge-by-edge.  A third party can therefore regenerate this
   suite byte-for-byte, or a *different* suite with the same procedure by changing the master seed
   (`build --master-seed`).

All randomness comes from the splitmix64 stream implemented below rather than `random`, so the suite
is byte-reproducible under any CPython build (the project's `E*` orders its audit sample by sha256
for the same reason: no dependence on an interpreter's RNG implementation).

Probability parameters are carried as exact rationals (`p_num / p_den`) and the draws are integer
comparisons (`u64 % p_den < p_num`), so a graph is a function of (params, seed) alone and not of
binary64 rounding.  The decimal spelling (`"p": "0.030"`) travels alongside them for readability.

Subcommands
-----------
    build   --config generators/config.json --suite suite [--master-seed N] [--validate-only]
    verify  --config generators/config.json --suite suite
    stats   --suite suite            # per-family / per-stratum tables (markdown)
    probe   --config ... --suite ... [--out generators/nontriviality_probe.json]
    record  --suite suite [--commit HASH]   # generators/FREEZE.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

SCHEMA_GRAPH = "a0.maxcut.graph/v1"
SCHEMA_MANIFEST = "a0.maxcut.suite.manifest/v1"
SCHEMA_CONFIG = "a0.maxcut.suite.config/v1"
SCHEMA_PROVENANCE = "a0.maxcut.suite.provenance/v1"
SCHEMA_PROBE = "a0.maxcut.suite.nontriviality_probe/v1"
SCHEMA_FREEZE = "a0.maxcut.suite.freeze/v1"

SUITE_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"

#: INTERFACE.md §2: exactly these keys, no more (checked by `verify`).
GRAPH_KEYS = ("schema", "graph_id", "family", "n", "edges", "generator", "notes")

#: role -> on-disk subdirectory of `suite/` (INTERFACE.md §1).
ROLE_DIR = {"dev": "dev", "eval": "eval", "calibration": "calibration"}

#: role -> graph_id prefix.
ROLE_PREFIX = {"dev": "G_dev_", "eval": "G_eval_", "calibration": "C_"}

#: reporting order of the four families (config order).
FAMILY_ORDER = ("ER", "RR", "BA", "Planted")


# ======================================================================================
# canonical form (INTERFACE.md §2)
# ======================================================================================

def canonical_bytes(obj) -> bytes:
    """The frozen canonical byte form of INTERFACE.md §2 (compact, sorted, ASCII, one newline)."""
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def read_json(path):
    return json.loads(Path(path).read_text())


# ======================================================================================
# splitmix64: the one source of randomness, interpreter-independent
# ======================================================================================

MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


class SplitMix64:
    """Deterministic 64-bit stream.  Fixed by the algorithm, not by a stdlib RNG version."""

    __slots__ = ("state",)

    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next_u64(self) -> int:
        self.state = (self.state + _GOLDEN) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def below(self, bound: int) -> int:
        """Uniform-ish integer in [0, bound).  `u64 % bound`; modulo bias < 2**-54 for our bounds."""
        if bound <= 0:
            raise ValueError("bound must be positive")
        return self.next_u64() % bound

    def bernoulli(self, num: int, den: int) -> bool:
        """True with probability `num/den`."""
        return self.below(den) < num

    def shuffle(self, seq) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.below(i + 1)
            seq[i], seq[j] = seq[j], seq[i]


def derive_seed(master: int, role: str, family: str, stratum: str, rep: int, graph_id: str) -> int:
    """Per-graph stream seed.  sha256-derived so it does not depend on draw order or on `random`."""
    material = f"a0.maxcut.suite/v1|master={master}|role={role}|family={family}|stratum={stratum}|rep={rep}|graph_id={graph_id}"
    return int.from_bytes(hashlib.sha256(material.encode("ascii")).digest()[:8], "big")


# ======================================================================================
# generators (each returns an edge list, plus labels for the planted family)
# ======================================================================================

def gen_er_gnp(n: int, params: dict, rng: SplitMix64):
    """Erdos-Renyi G(n,p).  Every pair (i<j) is examined in lexicographic order."""
    num, den = params["p_num"], params["p_den"]
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.bernoulli(num, den)]
    return edges, None


def gen_rr_pairing(n: int, params: dict, rng: SplitMix64, max_attempts: int = 200000):
    """Random d-regular graph by the pairing (stub-matching) model, rejecting non-simple outcomes.

    A uniform-ish sample of simple d-regular graphs; the rejection count is part of the recorded
    stream, so the result is a deterministic function of (n, d, seed).
    """
    d = params["d"]
    if (n * d) % 2:
        raise ValueError("n*d must be even")
    for _ in range(max_attempts):
        stubs = [v for v in range(n) for _ in range(d)]
        rng.shuffle(stubs)
        edges = set()
        ok = True
        for k in range(0, len(stubs), 2):
            a, b = stubs[k], stubs[k + 1]
            if a == b:
                ok = False
                break
            edge = (a, b) if a < b else (b, a)
            if edge in edges:
                ok = False
                break
            edges.add(edge)
        if ok:
            return sorted(edges), None
    raise RuntimeError(f"pairing model failed to produce a simple {d}-regular graph in {max_attempts} attempts")


def gen_ba_preferential(n: int, params: dict, rng: SplitMix64):
    """Barabasi-Albert preferential attachment (documented variant, `generators/README.md`).

    Seed graph = complete graph on m+1 nodes; each later node v attaches m edges, sampled *without
    replacement* from existing nodes with probability proportional to current degree (rejection on
    repeats).  `total_degree` is held exactly, so the target draw is an integer comparison.
    """
    m = params["m"]
    if not 1 <= m < n:
        raise ValueError("need 1 <= m < n")
    m0 = m + 1
    edges = {(i, j) for i in range(m0) for j in range(i + 1, m0)}
    degrees = [m] * m0
    total = m0 * m
    for v in range(m0, n):
        degrees.append(0)
        chosen = set()
        while len(chosen) < m:
            r = rng.below(total)
            acc = 0
            for u in range(v):
                acc += degrees[u]
                if r < acc:
                    chosen.add(u)
                    break
        for u in chosen:
            edges.add((u, v))
            degrees[u] += 1
            degrees[v] += 1
            total += 2
    return sorted(edges), None


def gen_planted_partition(n: int, params: dict, rng: SplitMix64):
    """Planted-partition graph: k communities, intra-probability p_in, inter p_out.

    The community label vector is a random permutation of the size multiset, so neither the labels
    nor anything recoverable from them can be read off the sizes.  The labels are *returned* (for
    `generators/provenance.json`) and never written into `suite/`.
    """
    sizes = list(params["community_sizes"])
    if sum(sizes) != n:
        raise ValueError(f"community sizes {sizes} do not sum to n={n}")
    pin_num, pin_den = params["p_in_num"], params["p_in_den"]
    pout_num, pout_den = params["p_out_num"], params["p_out_den"]
    labels = [c for c, size in enumerate(sizes) for _ in range(size)]
    rng.shuffle(labels)
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if labels[i] == labels[j]:
                if rng.bernoulli(pin_num, pin_den):
                    edges.append((i, j))
            else:
                if rng.bernoulli(pout_num, pout_den):
                    edges.append((i, j))
    return edges, list(labels)


GENERATORS = {
    "er_gnp": gen_er_gnp,
    "rr_pairing": gen_rr_pairing,
    "ba_preferential": gen_ba_preferential,
    "planted_partition": gen_planted_partition,
}


# ======================================================================================
# statistics (integer arithmetic; every reported number is derived from `edges`)
# ======================================================================================

def degrees_of(n: int, edges) -> list:
    deg = [0] * n
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    return deg


def components_of(n: int, edges) -> list:
    """Component sizes, descending, by union-find over the frozen edge list."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[max(ru, rv)] = min(ru, rv)
    sizes = Counter(find(i) for i in range(n))
    return sorted(sizes.values(), reverse=True)


def _decimal(fr: Fraction, places: int) -> str:
    """Exact decimal of a fraction when it terminates within `places`, else half-up rounded."""
    scale = 10 ** places
    q, r = divmod(fr.numerator * scale, fr.denominator)
    if r * 2 >= fr.denominator:
        q += 1
    text = str(q).rjust(places + 1, "0")
    whole, frac = text[:-places], text[-places:]
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def degree_stats(n: int, edges) -> dict:
    deg = degrees_of(n, edges)
    ordered = sorted(deg)
    hist = Counter(deg)
    total = sum(deg)
    mean = Fraction(total, n)
    variance = Fraction(sum(d * d for d in deg), n) - mean * mean
    if variance < 0:
        variance = Fraction(0)
    std_scaled = math.isqrt(max(0, (variance.numerator * 10 ** 12) // variance.denominator))
    std_text = f"{std_scaled // 10 ** 6}.{std_scaled % 10 ** 6:06d}"
    if n % 2:
        median = Fraction(ordered[n // 2])
    else:
        median = Fraction(ordered[n // 2 - 1] + ordered[n // 2], 2)
    return {
        "min": min(deg),
        "max": max(deg),
        "sum": total,
        "median": _decimal(median, 1),
        "mean": _decimal(mean, 10),
        "mean_fraction": [mean.numerator, mean.denominator],
        "std_floor": std_text,
        "histogram": {str(k): hist[k] for k in sorted(hist)},
    }


def graph_statistics(n: int, edges) -> dict:
    comps = components_of(n, edges)
    degree = degree_stats(n, edges)
    return {
        "edges": len(edges),
        "degree": degree,
        "components": {
            "count": len(comps),
            "sizes": comps,
            "largest": comps[0] if comps else 0,
            "connected": len(comps) == 1,
        },
        "isolated_nodes": degree["histogram"].get("0", 0),
    }


def check_simple(n: int, edges) -> list:
    """Structural checks of INTERFACE.md §2; returns a list of problems (empty == clean)."""
    problems = []
    seen = set()
    previous = None
    for edge in edges:
        if not (isinstance(edge, list) and len(edge) == 2 and all(isinstance(x, int) for x in edge)):
            problems.append(f"edge is not a pair of integers: {edge!r}")
            continue
        u, v = edge
        if not (0 <= u < n and 0 <= v < n):
            problems.append(f"endpoint out of range: {edge!r}")
        if u == v:
            problems.append(f"self-loop: {edge!r}")
        if u > v:
            problems.append(f"not written u<v: {edge!r}")
        if (u, v) in seen:
            problems.append(f"duplicate edge: {edge!r}")
        seen.add((u, v))
        if previous is not None and (u, v) <= previous:
            problems.append(f"edges not strictly ascending at {edge!r}")
        previous = (u, v)
    return problems


# ======================================================================================
# suite construction
# ======================================================================================

def iter_slots(config: dict, role: str, master: int):
    """Yield (family, stratum, params, rep, graph_id) in the frozen id order.

    dev/eval: `reps` independent draws per stratum.  calibration: 1 draw per stratum, fresh seeds
    (the `role` enters the seed derivation), so the calibration set is independent of both.
    """
    reps = config["reps"][role]
    index = 0
    for family_entry in config["families"]:
        for stratum_entry in family_entry["strata"]:
            for rep in range(reps):
                index += 1
                graph_id = f"{ROLE_PREFIX[role]}{index:04d}"
                yield family_entry, stratum_entry["stratum"], stratum_entry["params"], rep, graph_id


def build_graph(config: dict, role: str, family_entry: dict, stratum: str, params: dict, rep: int,
                graph_id: str, master: int):
    n = config["n"]
    family = family_entry["family"]
    seed = derive_seed(master, role, family, stratum, rep, graph_id)
    rng = SplitMix64(seed)
    edges, labels = GENERATORS[family_entry["generator"]](n, params, rng)
    edges = sorted((u, v) if u < v else (v, u) for u, v in edges)
    document = {
        "schema": SCHEMA_GRAPH,
        "graph_id": graph_id,
        "family": family,
        "n": n,
        "edges": [[u, v] for u, v in edges],
        "generator": {
            "name": family_entry["generator"],
            "version": GENERATOR_VERSION,
            "params": params,
            "seed": seed,
        },
        "notes": "",
    }
    return document, edges, labels


def build(config: dict, suite_dir: Path, generators_dir: Path, master: int, write: bool = True) -> dict:
    n = config["n"]
    # the manifest must describe the configuration that was actually used, so an overridden master
    # seed is embedded as used: `manifest.generator_config` then fully determines the data.
    config = dict(config)
    config["master_seed"] = master
    graphs = []
    provenance = []
    overlap = {}

    for role in ("dev", "eval", "calibration"):
        for family_entry, stratum, params, rep, graph_id in iter_slots(config, role, master):
            document, edges, labels = build_graph(config, role, family_entry, stratum, params, rep,
                                                  graph_id, master)
            payload = canonical_bytes(document)
            stats = graph_statistics(n, edges)
            entry = {
                "graph_id": graph_id,
                "role": role,
                "path": f"{ROLE_DIR[role]}/{graph_id}.json",
                "family": family_entry["family"],
                "stratum": stratum,
                "n": n,
                "edges": stats["edges"],
                "graph_sha256": sha256_bytes(payload),
                "generator": document["generator"],
                "degree": stats["degree"],
                "components": stats["components"],
                "isolated_nodes": stats["isolated_nodes"],
                "edge_set_sha256": sha256_bytes(canonical_bytes([list(e) for e in edges])),
            }
            graphs.append(entry)
            if labels is not None:
                provenance.append({
                    "graph_id": graph_id,
                    "role": role,
                    "family": family_entry["family"],
                    "stratum": stratum,
                    "seed": document["generator"]["seed"],
                    "planted_labels": labels,
                    "planted_community_sizes": list(params["community_sizes"]),
                })
            if write:
                target = suite_dir / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)

    for key, bucket in (("graph_sha256", [g["graph_sha256"] for g in graphs]),
                        ("edge_set_sha256", [g["edge_set_sha256"] for g in graphs])):
        overlap[key] = {"total": len(bucket), "distinct": len(set(bucket))}

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "suite_version": SUITE_VERSION,
        "frozen_on": config.get("frozen_on"),
        "n": n,
        "counts": {
            "dev": sum(1 for g in graphs if g["role"] == "dev"),
            "eval": sum(1 for g in graphs if g["role"] == "eval"),
            "calibration": sum(1 for g in graphs if g["role"] == "calibration"),
            "total": len(graphs),
        },
        "canonical_form": 'json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n"',
        "identity": "graph identity = sha256 of the canonical bytes of <role>/<graph_id>.json; "
                    "generator.seed is provenance only and no verdict may reference it (INTERFACE.md §2)",
        "roles": {
            "dev": "visible development instances; may inform development work",
            "eval": "frozen hold-out; evaluated once at the end, never injected into an agent workspace",
            "calibration": "resource-rate calibration only (INTERFACE.md §9); MUST NOT be used for any "
                           "algorithmic selection",
        },
        "generator": {
            "name": "generators/maxcut_suite.py",
            "version": GENERATOR_VERSION,
            "source_sha256": sha256_file(Path(__file__)),
        },
        "generator_config": config,
        "separation": {
            "sampling": "dev, eval and calibration are independent draws: each (role, family, stratum, "
                        "rep) slot gets its own sha256-derived stream keyed by the role",
            "overlap_check": overlap,
        },
        "family_summary": family_summary(config, graphs),
        "graphs": graphs,
    }
    if write:
        (suite_dir / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        )
        (generators_dir / "provenance.json").write_text(
            json.dumps({
                "schema": SCHEMA_PROVENANCE,
                "generator": {"name": "generators/maxcut_suite.py", "version": GENERATOR_VERSION},
                "master_seed": master,
                "note": "Solution provenance.  `planted_labels` is the community label of every node of a "
                        "Planted graph.  It is deliberately kept OUT of suite/** so that no file a candidate "
                        "can read carries the planted partition; `verify` greps suite/** for these vectors.",
                "planted": provenance,
            }, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        )
    return manifest


def family_summary(config: dict, graphs: list) -> dict:
    """Per-family / per-stratum edge and degree summary, from the built entries."""
    summary = {}
    for family_entry in config["families"]:
        family = family_entry["family"]
        rows = []
        for stratum_entry in family_entry["strata"]:
            stratum = stratum_entry["stratum"]
            members = [g for g in graphs if g["family"] == family and g["stratum"] == stratum
                       and g["role"] in ("dev", "eval")]
            if not members:
                continue
            edge_counts = [g["edges"] for g in members]
            mean_degrees = [Fraction(g["degree"]["sum"], g["n"]) for g in members]
            rows.append({
                "stratum": stratum,
                "params": stratum_entry["params"],
                "graphs": len(members),
                "edges_min": min(edge_counts),
                "edges_max": max(edge_counts),
                "edges_total": sum(edge_counts),
                "mean_degree_avg": _decimal(sum(mean_degrees, Fraction(0)) / len(mean_degrees), 4),
                "degree_min": min(g["degree"]["min"] for g in members),
                "degree_max": max(g["degree"]["max"] for g in members),
                "isolated_total": sum(g["isolated_nodes"] for g in members),
                "components_min": min(g["components"]["count"] for g in members),
                "components_max": max(g["components"]["count"] for g in members),
            })
        summary[family] = {
            "generator": family_entry["generator"],
            "strata": rows,
            "graphs": sum(1 for g in graphs if g["family"] == family and g["role"] in ("dev", "eval")),
        }
    return summary


# ======================================================================================
# verification
# ======================================================================================

def verify(config: dict, suite_dir: Path, generators_dir: Path, master: int) -> tuple:
    """Recompute the whole suite from (config, master) and compare against what is on disk.

    Checks, in order: canonical identity, key set, structure, regeneration, statistics, manifest
    agreement, cross-role disjointness, and planted-label leakage.
    """
    problems = []
    checks = Counter()
    manifest = read_json(suite_dir / "manifest.json")
    recorded = {g["graph_id"]: g for g in manifest["graphs"]}
    n = config["n"]

    rebuilt = build(config, suite_dir, generators_dir, master, write=False)
    expected = {g["graph_id"]: g for g in rebuilt["graphs"]}

    if set(recorded) != set(expected):
        problems.append(f"manifest graph ids differ from a fresh build: {sorted(set(recorded) ^ set(expected))[:5]}")
    checks["manifest_ids"] += 1

    # the manifest must have been produced by the generator revision that is on disk now
    checks["generator_revision"] += 1
    if manifest.get("generator", {}).get("source_sha256") != sha256_file(Path(__file__)):
        problems.append("manifest was produced by a different generator revision "
                        "(manifest.generator.source_sha256 != sha256 of generators/maxcut_suite.py)")
    if manifest.get("generator_config", {}).get("master_seed") != master:
        problems.append(f"manifest generator_config.master_seed != {master}")

    for graph_id, entry in sorted(expected.items()):
        path = suite_dir / entry["path"]
        checks["graph_files"] += 1
        if not path.is_file():
            problems.append(f"{graph_id}: missing file {path}")
            continue
        raw = path.read_bytes()
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            problems.append(f"{graph_id}: not JSON ({exc})")
            continue
        # 1. canonical identity: re-serialise and compare bytes
        checks["canonical_reparse"] += 1
        if canonical_bytes(document) != raw:
            problems.append(f"{graph_id}: file is not in canonical form")
        if sha256_bytes(raw) != entry["graph_sha256"]:
            problems.append(f"{graph_id}: sha256 differs from a fresh build")
        if entry["graph_sha256"] != recorded.get(graph_id, {}).get("graph_sha256"):
            problems.append(f"{graph_id}: manifest sha256 differs from the file")
        # 2. key set (INTERFACE.md §2)
        checks["graph_keys"] += 1
        if tuple(sorted(document)) != tuple(sorted(GRAPH_KEYS)):
            problems.append(f"{graph_id}: key set is {sorted(document)}, expected {sorted(GRAPH_KEYS)}")
        # 3. structure
        checks["graph_structure"] += 1
        edge_list = [list(e) for e in document["edges"]]
        for problem in check_simple(n, edge_list):
            problems.append(f"{graph_id}: {problem}")
        if document["n"] != n or document["schema"] != SCHEMA_GRAPH:
            problems.append(f"{graph_id}: bad schema/n")
        # 4. regeneration: same (generator, params, seed) -> same edges
        checks["graph_regenerated"] += 1
        family_entry = next(f for f in config["families"] if f["family"] == document["family"])
        rng = SplitMix64(document["generator"]["seed"])
        regen_edges, _ = GENERATORS[family_entry["generator"]](n, document["generator"]["params"], rng)
        regen_edges = sorted((u, v) if u < v else (v, u) for u, v in regen_edges)
        if [list(e) for e in regen_edges] != edge_list:
            problems.append(f"{graph_id}: regeneration from (generator, params, seed) does not reproduce the file")
        # 5. statistics + edges count agree with the manifest
        checks["graph_statistics"] += 1
        stats = graph_statistics(n, regen_edges)
        if entry["edges"] != len(edge_list) or stats["edges"] != len(edge_list):
            problems.append(f"{graph_id}: manifest |E| does not match the file")
        if entry["degree"] != stats["degree"] or entry["components"] != stats["components"]:
            problems.append(f"{graph_id}: degree/component statistics do not match the file")
        if entry["isolated_nodes"] != stats["isolated_nodes"]:
            problems.append(f"{graph_id}: isolated-node count does not match the file")

    # 6. disjointness of graph bytes and of edge sets across the whole suite
    for key in ("graph_sha256", "edge_set_sha256"):
        values = [g[key] for g in expected.values()]
        checks[f"distinct_{key}"] += 1
        if len(set(values)) != len(values):
            duplicated = [v for v, c in Counter(values).items() if c > 1]
            problems.append(f"two graphs share a {key}: {duplicated}")
    role_hashes = {role: {g["graph_sha256"] for g in expected.values() if g["role"] == role}
                   for role in ROLE_DIR}
    checks["role_disjoint"] += 1
    for a in ROLE_DIR:
        for b in ROLE_DIR:
            if a < b and role_hashes[a] & role_hashes[b]:
                problems.append(f"{a} and {b} share an instance")

    # 7. planted-label leakage: no candidate-readable file under suite/ may carry a label vector.
    # Scanned scope = suite/**/*.json (the graph files and the index).  prose (README.md) is excluded:
    # it is not handed to a candidate and it quotes this very check, so it would match itself.
    checks["leakage_scan"] += 1
    provenance = read_json(generators_dir / "provenance.json")
    suite_text = {path: path.read_text() for path in sorted(suite_dir.rglob("*.json")) if path.is_file()}
    for record in provenance["planted"]:
        needles = {
            "compact label vector": json.dumps(record["planted_labels"], separators=(",", ":")),
            "spaced label vector": json.dumps(record["planted_labels"]),
        }
        for label, needle in needles.items():
            for path, text in suite_text.items():
                if needle in text:
                    problems.append(f"{record['graph_id']}: planted {label} found in {path}")
    checks["leakage_needles"] += len(provenance["planted"]) * 2
    for path, text in suite_text.items():
        for forbidden in ('"labels"', '"planted_labels"', '"assignment"', "community_of",
                          "node_labels", "planted_partition_labels"):
            if forbidden in text:
                problems.append(f"forbidden key {forbidden} in {path}")
    checks["leakage_files"] += len(suite_text)

    return problems, checks, {"graphs": len(expected), "manifest": manifest}


# ======================================================================================
# non-normative non-triviality probe
# ======================================================================================

def cut_edges(n: int, adj: list, labels) -> int:
    return sum(1 for u in range(n) for v in adj[u] if u < v and labels[u] != labels[v])


def one_exchange_local_opt(n: int, adj: list, labels) -> int:
    """Steepest-descent single-vertex-flip local optimum; best improvement each pass."""
    labels = list(labels)
    cut = cut_edges(n, adj, labels)
    while True:
        best_delta, best_v = 0, -1
        for v in range(n):
            same = sum(1 for u in adj[v] if labels[u] == labels[v])
            delta = same - (len(adj[v]) - same)
            if delta > best_delta:
                best_delta, best_v = delta, v
        if best_v < 0:
            return cut
        cut += best_delta
        labels[best_v] ^= 1


def probe(config: dict, suite_dir: Path, master: int, seed: int = 20260922) -> dict:
    """Per-graph random-partition and 1-exchange cut fractions.

    NON-NORMATIVE: this is a parameter-justification diagnostic, **not** the frozen reference
    `R_i / OPT_i / U_i`, which `a0/tasks/maxcut/references/` owns.  It exists to show the suite is
    neither degenerate (edges exist, degrees are non-trivial) nor trivially separable (a random
    partition sits near 1/2, far below what a plain local search reaches).
    """
    n = config["n"]
    rows = []
    for role in ("dev", "eval", "calibration"):
        for family_entry, stratum, params, rep, graph_id in iter_slots(config, role, master):
            _, edges, labels = build_graph(config, role, family_entry, stratum, params, rep, graph_id, master)
            adj = [[] for _ in range(n)]
            for u, v in edges:
                adj[u].append(v)
                adj[v].append(u)
            rng = SplitMix64(int.from_bytes(hashlib.sha256(f"probe|{graph_id}".encode()).digest()[:8], "big") ^ seed)
            random_cuts = []
            for _ in range(8):
                random_cuts.append(cut_edges(n, adj, [rng.below(2) for _ in range(n)]))
            local_cuts = []
            for _ in range(4):
                local_cuts.append(one_exchange_local_opt(n, adj, [rng.below(2) for _ in range(n)]))
            row = {
                "graph_id": graph_id,
                "role": role,
                "family": family_entry["family"],
                "stratum": stratum,
                "edges": len(edges),
                "random_cut_fraction_mean": _decimal(Fraction(sum(random_cuts), len(random_cuts) * len(edges)), 6),
                "one_exchange_cut_fraction_best": _decimal(Fraction(max(local_cuts), len(edges)), 6),
            }
            if labels is not None:
                row["planted_partition_cut_fraction"] = _decimal(Fraction(cut_edges(n, adj, labels), len(edges)), 6)
            rows.append(row)
    return {
        "schema": SCHEMA_PROBE,
        "role": "NON-NORMATIVE parameter-justification diagnostic.  NOT the frozen reference "
                "R_i/OPT_i/U_i (owned by a0/tasks/maxcut/references/).",
        "method": "random partition: mean cut fraction over 8 seeded uniform draws; one_exchange: best "
                  "cut fraction over 4 seeded random starts, steepest-descent to a 1-flip local optimum; "
                  "planted: cut fraction of the generator's planted partition",
        "seed": seed,
        "graphs": rows,
    }


# ======================================================================================
# reporting
# ======================================================================================

def degree_distribution_table(manifest: dict, role_filter=("dev", "eval")) -> str:
    """Per-family degree distribution, aggregated over the family's instances of `role_filter`."""
    buckets = ((0, 0), (1, 2), (3, 4), (5, 8), (9, 16), (17, 10 ** 9))
    lines = []
    header = " | ".join("deg 0" if lo == hi else (f"deg {lo}+" if hi > 1000 else f"deg {lo}–{hi}")
                        for lo, hi in buckets)
    lines.append(f"| family | graphs | nodes | {header} | degree mean | degree max | |E| mean |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for family in FAMILY_ORDER:
        members = [g for g in manifest["graphs"] if g["family"] == family and g["role"] in role_filter]
        if not members:
            continue
        counts = [0] * len(buckets)
        nodes = 0
        degree_sum = 0
        for graph in members:
            for degree_text, count in graph["degree"]["histogram"].items():
                degree = int(degree_text)
                nodes += count
                degree_sum += degree * count
                for index, (lo, hi) in enumerate(buckets):
                    if lo <= degree <= hi:
                        counts[index] += count
                        break
        mean = _decimal(Fraction(degree_sum, nodes), 4)
        edge_mean = _decimal(Fraction(sum(g["edges"] for g in members), len(members)), 2)
        cells = " | ".join(str(c) for c in counts)
        lines.append(f"| {family} | {len(members)} | {nodes} | {cells} | {mean} | "
                     f"{max(g['degree']['max'] for g in members)} | {edge_mean} |")
    return "\n".join(lines)


def stats_tables(manifest: dict) -> str:
    lines = []
    lines.append("### Per-stratum statistics (dev + eval)\n")
    lines.append("| family | generator | stratum | dev+eval graphs | |E| min–max | mean degree | degree min–max | isolated | components |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for family in FAMILY_ORDER:
        block = manifest["family_summary"].get(family)
        if not block:
            continue
        for row in block["strata"]:
            params = ", ".join(f"{k}={v}" for k, v in row["params"].items() if k in
                               ("p", "d", "m", "p_in", "p_out", "community_sizes"))
            lines.append(
                f"| {family} | `{block['generator']}` | `{row['stratum']}` ({params}) | {row['graphs']} | "
                f"{row['edges_min']}–{row['edges_max']} | {row['mean_degree_avg']} | "
                f"{row['degree_min']}–{row['degree_max']} | {row['isolated_total']} | "
                f"{row['components_min']}–{row['components_max']} |"
            )
    lines.append("\n### Degree distribution per family (dev + eval, aggregated)\n")
    lines.append(degree_distribution_table(manifest))
    return "\n".join(lines)


def probe_table(probe_document: dict) -> str:
    lines = []
    lines.append("| role | graph | family | stratum | |E| | random cut frac (mean of 8) | 1-exchange cut frac (best of 4) | planted cut frac |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in probe_document["graphs"]:
        lines.append(
            f"| {row['role']} | {row['graph_id']} | {row['family']} | {row['stratum']} | {row['edges']} | "
            f"{row['random_cut_fraction_mean']} | {row['one_exchange_cut_fraction_best']} | "
            f"{row.get('planted_partition_cut_fraction', '—')} |"
        )
    return "\n".join(lines)


def family_probe_summary(probe_document: dict, role_filter=("dev", "eval")) -> str:
    lines = []
    lines.append("| family | graphs | random cut frac (mean) | 1-exchange cut frac (mean of bests) | range of 1-exchange |")
    lines.append("|---|---|---|---|---|")
    for family in FAMILY_ORDER:
        rows = [r for r in probe_document["graphs"]
                if r["family"] == family and r["role"] in role_filter]
        if not rows:
            continue
        random_mean = sum(Fraction(r["random_cut_fraction_mean"]) for r in rows) / len(rows)
        local_mean = sum(Fraction(r["one_exchange_cut_fraction_best"]) for r in rows) / len(rows)
        local_values = [Fraction(r["one_exchange_cut_fraction_best"]) for r in rows]
        lines.append(
            f"| {family} | {len(rows)} | {_decimal(random_mean, 4)} | {_decimal(local_mean, 4)} | "
            f"{_decimal(min(local_values), 4)}–{_decimal(max(local_values), 4)} |"
        )
    return "\n".join(lines)


# ======================================================================================
# CLI
# ======================================================================================

def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    task_dir = here.parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("build", "verify", "stats", "probe", "record"))
    parser.add_argument("--config", default=str(here / "config.json"))
    parser.add_argument("--suite", default=str(task_dir / "suite"))
    parser.add_argument("--generators", default=str(here))
    parser.add_argument("--master-seed", type=int, default=None,
                        help="override config.master_seed (use this to generate a DIFFERENT suite)")
    parser.add_argument("--probe-out", default=str(here / "nontriviality_probe.json"))
    parser.add_argument("--commit", default=None, help="record: the commit that froze the suite")
    parser.add_argument("--detail", action="store_true", help="probe: print the per-graph table too")
    args = parser.parse_args(argv)

    config = read_json(args.config)
    if config.get("schema") != SCHEMA_CONFIG:
        print(f"config schema is {config.get('schema')!r}, expected {SCHEMA_CONFIG!r}", file=sys.stderr)
        return 2
    master = args.master_seed if args.master_seed is not None else config["master_seed"]
    suite_dir, generators_dir = Path(args.suite), Path(args.generators)

    if args.command == "build":
        manifest = build(config, suite_dir, generators_dir, master, write=True)
        print(f"built {manifest['counts']['total']} graphs into {suite_dir} "
              f"(dev={manifest['counts']['dev']} eval={manifest['counts']['eval']} "
              f"calibration={manifest['counts']['calibration']}), master_seed={master}")
        print(f"manifest: {suite_dir / 'manifest.json'} sha256={sha256_file(suite_dir / 'manifest.json')}")
        print(f"provenance: {generators_dir / 'provenance.json'} sha256={sha256_file(generators_dir / 'provenance.json')}")
        return 0

    if args.command == "verify":
        problems, checks, summary = verify(config, suite_dir, generators_dir, master)
        for name in sorted(checks):
            print(f"  {name:<28} {checks[name]}")
        print(f"graphs verified: {summary['graphs']}")
        if problems:
            print(f"FAIL: {len(problems)} problem(s)")
            for problem in problems[:40]:
                print(f"  - {problem}")
            return 1
        print("PASS: canonical identity, structure, regeneration, statistics, disjointness and leakage all clean")
        return 0

    if args.command == "stats":
        manifest = read_json(suite_dir / "manifest.json")
        print(stats_tables(manifest))
        return 0

    if args.command == "probe":
        document = probe(config, suite_dir, master)
        Path(args.probe_out).write_text(json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
        print(probe_table(document) if args.detail else family_probe_summary(document))
        print(f"\nwrote {args.probe_out} sha256={sha256_file(args.probe_out)}")
        return 0

    if args.command == "record":
        manifest_path = suite_dir / "manifest.json"
        document = {
            "schema": SCHEMA_FREEZE,
            "commit": args.commit or git_commit(),
            "suite_version": SUITE_VERSION,
            "generator_source_sha256": sha256_file(Path(__file__)),
            "master_seed": master,
            "manifest_sha256": sha256_file(manifest_path),
            "manifest_counts": read_json(manifest_path)["counts"],
        }
        target = generators_dir / "FREEZE.json"
        target.write_text(json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
        print(json.dumps(document, sort_keys=True, indent=2))
        print(f"wrote {target}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
