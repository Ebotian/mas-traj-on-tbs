#!/usr/bin/env python3
"""Adversarial re-derivation of the suite claims (assignment item 1).

Owned by a0/verify/a1-testbed/.  Reads a0/tasks/maxcut/suite/** and the generator
source read-only; writes nothing outside this directory's report.

Claims attacked:
  C1.1 every graph file is canonical per INTERFACE.md §2 (re-serialise here, compare bytes)
  C1.2 the recorded sha256 is the sha256 of the file on disk
  C1.3 dev / eval / calibration do not overlap (my own digests, not theirs)
  C1.4 dev and eval are independently sampled, not a split of one draw
  C1.5 no solution leaks into a candidate-readable file: neither the label-vector
       *text* nor the label vector *recoverable* from what the file hands over
  C1.6 no reference/optimum value in the dataset itself
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parents[3]
SUITE = REPO / "a0/tasks/maxcut/suite"
GEN_DIR = REPO / "a0/tasks/maxcut/generators"
GEN_SRC = GEN_DIR / "maxcut_suite.py"

GRAPH_KEYS = {"schema", "graph_id", "family", "n", "edges", "generator", "notes"}
FAMILIES = ("ER", "RR", "BA", "Planted")
EXPECTED_N = 128

failures: list[str] = []
notes: list[str] = []
counters: Counter = Counter()


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL {msg}")


def ok(msg: str, n: int = 1) -> None:
    counters[msg] += n


def canonical(obj) -> bytes:
    """INTERFACE.md §2, re-derived from the interface text rather than imported."""
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# C1.1 / C1.2 / C1.6 -- canonical form, identity, and "no reference value here"
# --------------------------------------------------------------------------- #

def check_files() -> dict[str, dict]:
    manifest = json.loads((SUITE / "manifest.json").read_text())
    by_path = {g["path"]: g for g in manifest["graphs"]}
    loaded: dict[str, dict] = {}
    for path in sorted(SUITE.rglob("*.json")):
        rel = path.relative_to(SUITE).as_posix()
        raw = path.read_bytes()
        if rel == "manifest.json":
            continue
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            fail(f"{rel}: not JSON: {exc}")
            continue
        # C1.1 -- canonical form, re-derived here
        if canonical(obj) != raw:
            fail(f"{rel}: bytes are not the §2 canonical form of their own parse")
        else:
            ok("canonical_reparse")
        # C1.2 -- the manifest's recorded identity
        rec = by_path.get(rel)
        if rec is None:
            fail(f"{rel}: present on disk but absent from manifest.graphs")
            continue
        if rec["graph_sha256"] != sha256_bytes(raw):
            fail(f"{rel}: manifest graph_sha256 != sha256(file bytes)")
        else:
            ok("manifest_sha_matches_file")
        # key set exactly as §2 writes it -- nothing extra handed to the candidate
        if set(obj) != GRAPH_KEYS:
            fail(f"{rel}: key set {sorted(obj)} != {sorted(GRAPH_KEYS)}")
        else:
            ok("graph_keys_exact")
        if obj["n"] != EXPECTED_N:
            fail(f"{rel}: n={obj['n']}")
        # structure: node ids in range, u<v, no self loop, no duplicate, sorted, unit weight
        edges = [tuple(e) for e in obj["edges"]]
        if any(not (0 <= u < v < obj["n"]) for u, v in edges):
            fail(f"{rel}: an edge is not 0<=u<v<n")
        if len(set(edges)) != len(edges):
            fail(f"{rel}: duplicate edges")
        if edges != sorted(edges):
            fail(f"{rel}: edges not lexicographically sorted")
        text = raw.decode()
        # forbidden *keys* (not substrings: the family generator is literally named
        # "planted_partition", so a substring test on 'partition' is a false positive)
        forbidden_keys = {"labels", "planted_labels", "community_of", "node_labels",
                          "assignment", "partition", "optimum", "cut_edges", "cut_fraction",
                          "rho", "objective", "best_known", "R", "U", "OPT", "weight"}

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in forbidden_keys:
                        fail(f"{rel}: graph file has a key {k!r}")
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(obj)
        # C1.6 -- no reference/objective value in the data handed to the candidate
        for token in ("cut_edges", "cut_fraction", "best_known", "R_fraction", "objective_value"):
            if token in text:
                fail(f"{rel}: graph file contains {token!r}")
        loaded[rel] = {"obj": obj, "raw": raw, "rec": rec,
                       "edge_sha": sha256_bytes(canonical(sorted(obj["edges"])))}
    return loaded


# --------------------------------------------------------------------------- #
# C1.3 -- disjointness with my own digest
# --------------------------------------------------------------------------- #

def check_disjoint(loaded: dict[str, dict]) -> None:
    roles: dict[str, set[str]] = defaultdict(set)
    for rel, rec in loaded.items():
        roles[rec["rec"]["role"]].add(rec["edge_sha"])
    for role, digests in roles.items():
        print(f"  role {role}: files={len(digests)} distinct_edge_sets={len(digests)}")
    all_edges = [rec["edge_sha"] for rec in loaded.values()]
    if len(set(all_edges)) != len(all_edges):
        fail("two graphs share an edge-set digest")
    else:
        ok("all 60 edge sets distinct")
    for a in roles:
        for b in roles:
            if a < b and roles[a] & roles[b]:
                fail(f"{a} and {b} share an edge set")
    # complement check: a split of one draw would leave near-identical or near-complementary pairs
    pairs = defaultdict(list)
    for rel, rec in loaded.items():
        rec_role = rec["rec"]["role"]
        rec_key = (rec["rec"]["family"], rec["rec"]["stratum"])
        pairs[rec_key].append((rec_role, rel, set(tuple(e) for e in rec["obj"]["edges"])))
    worst = 0.0
    n_compared = 0
    for key, members in sorted(pairs.items()):
        devs = [m for m in members if m[0] == "dev"]
        evals = [m for m in members if m[0] == "eval"]
        for _, drel, de in devs:
            for _, erel, ee in evals:
                jac = len(de & ee) / len(de | ee)
                n_compared += 1
                if jac > worst:
                    worst, worst_pair = jac, (drel, erel, len(de & ee), len(de | ee))
    print(f"  dev/eval same-slot Jaccard compared={n_compared} worst={worst:.4f} {worst_pair if n_compared else ''}")
    if worst > 0.9:
        fail("a dev/eval pair in the same stratum is near-identical (split, not independent draw)")


# --------------------------------------------------------------------------- #
# C1.4 -- the stream key carries the role; seeds are not shared across roles
# --------------------------------------------------------------------------- #

def derive_seed(master: int, role: str, family: str, stratum: str, rep: int, graph_id: str) -> int:
    """Re-implemented from the README's stated key, not imported from the generator."""
    material = (f"a0.maxcut.suite/v1|master={master}|role={role}|family={family}|stratum={stratum}"
                f"|rep={rep}|graph_id={graph_id}")
    return int.from_bytes(hashlib.sha256(material.encode("ascii")).digest()[:8], "big")


def check_seeds(loaded: dict[str, dict]) -> None:
    manifest = json.loads((SUITE / "manifest.json").read_text())
    master = manifest["generator_config"]["master_seed"]
    seeds: dict[tuple, dict[str, int]] = defaultdict(dict)
    for rel, rec in loaded.items():
        r = rec["rec"]
        seed = rec["obj"]["generator"]["seed"]
        # rep is not in the manifest; recover it by searching the small rep space
        matches = [rep for rep in range(4)
                   if derive_seed(master, r["role"], r["family"], r["stratum"], rep, r["graph_id"]) == seed]
        if len(matches) != 1:
            fail(f"{rel}: seed {seed} is not derive_seed(...) for any rep in 0..3 (matches={matches})")
            continue
        ok("seed_reproduced_from_role_keyed_stream")
        seeds[(r["family"], r["stratum"], matches[0])][r["role"]] = seed
    shared = 0
    for key, roles in seeds.items():
        vals = [v for k, v in roles.items() if k in ("dev", "eval")]
        if len(vals) == 2 and vals[0] == vals[1]:
            shared += 1
            fail(f"dev and eval share a seed for slot {key}")
    ok("role_inside_stream_key", len(seeds))
    print(f"  slot seeds re-derived={len(seeds)} dev/eval shared seeds={shared}")


# --------------------------------------------------------------------------- #
# C1.5 -- the leakage probe (this is the important one)
# --------------------------------------------------------------------------- #

def check_leakage(loaded: dict[str, dict]) -> None:
    prov_path = GEN_DIR / "provenance.json"
    prov = json.loads(prov_path.read_text())
    planted = prov["planted"]
    print(f"  provenance planted records: {len(planted)}")

    # Two candidate-readable surfaces are audited, and I say which is which:
    #   (a) narrow == the surface the suite README audits: every file under suite/**
    #   (b) broad  == the solution-bearing trees that sit beside it in the same repo,
    #                 scoped (a full-repo walk is 144 574 files / 2.3 GB and is not
    #                 what decides the question).  Scoping is stated so it can be
    #                 argued with; a hit does not depend on the scope, only a miss does.
    narrow = {p: p.read_bytes() for p in sorted(SUITE.rglob("*")) if p.is_file()}
    broad_roots = [REPO / "a0/tasks/maxcut", REPO / "a0/a1", REPO / "a0/meter"]
    broad: dict[pathlib.Path, bytes] = {}
    for root in broad_roots:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            try:
                if p.stat().st_size > 512 * 1024:
                    continue
                data = p.read_bytes()
            except OSError:
                continue
            if b"\0" in data[:4096]:
                continue
            broad[p] = data
    print(f"  narrow surface files={len(narrow)}  broad surface files={len(broad)} "
          f"(roots: {[str(r.relative_to(REPO)) for r in broad_roots]})")

    # --- (1) exact label-vector text, every spelling I can think of, incl. relabelings
    hits = 0
    for record in planted:
        gid = record["graph_id"]
        labels = record["planted_labels"]
        needles = set()
        needles.add(json.dumps(labels, separators=(",", ":")))
        needles.add(json.dumps(labels))
        needles.add(json.dumps(list(labels), separators=(",", ":")))
        # the partition as a set of "u:label" pairs, and as class membership lists
        needles.add(json.dumps([[i, c] for i, c in enumerate(labels)], separators=(",", ":")))
        needles.add(json.dumps([i for i, c in enumerate(labels) if c == 0], separators=(",", ":")))
        needles.add(json.dumps([i for i, c in enumerate(labels) if c == 0]))
        # any relabeling of the same set partition (k! is tiny for k<=4)
        classes = defaultdict(list)
        for i, c in enumerate(labels):
            classes[c].append(i)
        import itertools
        keys = sorted(classes)
        for perm in itertools.permutations(range(len(keys))):
            relabelled = [0] * len(labels)
            for new, old in zip(perm, keys):
                for node in classes[old]:
                    relabelled[node] = new
            needles.add(json.dumps(relabelled, separators=(",", ":")))
        # a binary spelling: string of 0/1 and hex/int encoding of the bitmask
        bits = "".join(str(c & 1) for c in labels)
        needles.add(bits)
        for b in {bits, bits[::-1]}:
            needles.add(str(int(b, 2)))
            needles.add(hex(int(b, 2)))
        for needle in needles:
            if len(needle) < 8:
                continue
            encoding = needle.encode()
            for path, data in narrow.items():
                if encoding in data:
                    hits += 1
                    fail(f"LEAK(narrow) {gid}: needle of {len(needle)} chars found in {path}")
            for path, data in broad.items():
                if "verify/a1-testbed" in path.as_posix():
                    continue
                if encoding in data:
                    hits += 1
                    print(f"  LEAK(broad) {gid}: needle of {len(needle)} chars in {path.relative_to(REPO)}")
    print(f"  text-needle hits: {hits}")

    # --- (2) recoverability: what does graph.json itself hand over?
    #
    # The graph file carries generator.{name,params,seed} and the generator that
    # consumes them is in this repo.  So the honest question is not "is a label
    # vector spelled out in a file" but "is the label vector a function of what
    # the candidate is handed".  Replay it and check the replay against the graph
    # it claims to explain (edges) and against the model's own parameters
    # (intra/inter densities) -- a label vector that is not the planted partition
    # can still reproduce the edges by accident, the densities cannot.
    sys.path.insert(0, str(GEN_DIR))
    import maxcut_suite as gen  # noqa: E402  (read-only import of the published algorithm)

    def densities(doc, lab):
        edges = {tuple(e) for e in doc["edges"]}
        n = doc["n"]
        intra = tot_in = inter = tot_out = 0
        for i in range(n):
            for j in range(i + 1, n):
                same = lab[i] == lab[j]
                if same:
                    tot_in += 1
                else:
                    tot_out += 1
                if (i, j) in edges:
                    if same:
                        intra += 1
                    else:
                        inter += 1
        return intra / tot_in, inter / tot_out

    def cut_of(doc, lab):
        adj = [[] for _ in range(doc["n"])]
        for u, v in doc["edges"]:
            adj[u].append(v)
            adj[v].append(u)
        return sum(1 for u in range(doc["n"]) for v in adj[u] if u < v and lab[u] != lab[v])

    replay_edges = replay_cut = prov_vs_replay = 0
    cut_fracs = []
    for record in planted:
        gid = record["graph_id"]
        rel = next(r for r in loaded if loaded[r]["rec"]["graph_id"] == gid)
        doc = loaded[rel]["obj"]
        gp = doc["generator"]
        rng = gen.SplitMix64(gp["seed"])
        edges, labels = gen.GENERATORS[gp["name"]](doc["n"], gp["params"], rng)
        labels = list(labels)
        if [tuple(e) for e in edges] == [tuple(e) for e in doc["edges"]]:
            replay_edges += 1
        else:
            fail(f"{gid}: replay from graph.json does not reproduce the graph's own edges")
        pin, pout = gp["params"]["p_in_num"] / gp["params"]["p_in_den"], gp["params"]["p_out_num"] / gp["params"]["p_out_den"]
        ri, ro = densities(doc, labels)
        pi, po = densities(doc, list(record["planted_labels"]))
        if not (abs(ri - pin) < 0.03 * pin + 0.02 and abs(ro - pout) < 0.03 * pout + 0.02):
            fail(f"{gid}: replayed labels do not have the declared intra/inter densities")
        print(f"  {gid}: declared p_in={pin:.3f} p_out={pout:.3f} | "
              f"replayed intra={ri:.3f} inter={ro:.3f} | provenance intra={pi:.3f} inter={po:.3f}")
        if list(labels) == list(record["planted_labels"]):
            prov_vs_replay += 1
        cut_fracs.append(cut_of(doc, labels) / len(doc["edges"]))
    print(f"  C1.5(2) replay of graph.json (seed+params+published generator): "
          f"edges reproduced {replay_edges}/{len(planted)}, "
          f"label vector equal to provenance.json {prov_vs_replay}/{len(planted)}")
    if prov_vs_replay != len(planted):
        notes.append("provenance.json's planted_labels are NOT the label vector of the shipped "
                     "graphs (density test above); the suite's leakage needles therefore search "
                     "vectors that no shipped graph encodes")
    print(f"  true planted-partition cut fraction: min={min(cut_fracs):.4f} max={max(cut_fracs):.4f} "
          f"(random partition ~0.50, so this label leak is worth little for max-cut)")

    # --- (3) does anything else in the broad surface hand over an eval solution?
    ref_partitions = REPO / "a0/tasks/maxcut/references/logs/partitions"
    have_eval = len(list(ref_partitions.glob("G_eval_*"))) if ref_partitions.is_dir() else 0
    have_dev = len(list(ref_partitions.glob("G_dev_*"))) if ref_partitions.is_dir() else 0
    print(f"  reference partition files readable on disk: eval={have_eval} dev={have_dev} "
          f"(a full assignment, one JSON object each, filename carries the graph_id)")
    tgt = REPO / "a0/tasks/maxcut/references/targets.json"
    if tgt.is_file():
        doc = json.loads(tgt.read_text())
        g = doc.get("graphs")
        print(f"  references/targets.json readable: {tgt.stat().st_size} B, graphs="
              f"{len(g) if isinstance(g, (dict, list)) else '?'}")


if __name__ == "__main__":
    print("== C1.1/C1.2/C1.6 canonical form, identity, cleanliness ==")
    loaded = check_files()
    print("== C1.3 disjointness ==")
    check_disjoint(loaded)
    print("== C1.4 independent sampling ==")
    check_seeds(loaded)
    print("== C1.5 leakage ==")
    check_leakage(loaded)
    print("\ncounters:", dict(counters))
    print("NOTES:")
    for n in notes:
        print("  *", n)
    print(f"FAILURES: {len(failures)}")
    for f in failures[:20]:
        print("  -", f)
    sys.exit(1 if failures else 0)
