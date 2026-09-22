#!/usr/bin/env python3
"""L1 size-lever sample: regenerate the two worst strata at larger `n`.

The frozen suite has no size variance (all 60 graphs are n=128), and the two
strata that come closest to the rho bar are RR:d4 and ER:p080.  This script
draws fresh instances of exactly those two strata at n in {128,256,512,1024},
using the *frozen* generator module (same SplitMix64 stream, same generator
functions, same canonical writer) so that the only variable is `n`.

Nothing here touches the frozen suite: `generators/maxcut_suite.py` is imported
read-only and every output is written under `redesign/instances/`.

    python3 gen/gen_l1_instances.py            # generate
    python3 gen/gen_l1_instances.py --check    # re-derive + compare digests
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
GEN_MODULE = TASK / "generators" / "maxcut_suite.py"

#: the generation role string.  It enters derive_seed, so these streams are
#: disjoint from the frozen suite's dev/eval/calibration streams by construction.
ROLE = "redesign-L1"
MASTER = 20260922

#: stratum -> (family, generator name, params).  Byte-identical params to
#: generators/config.json for the two strata named by gates/verdict.dev.md.
STRATA = {
    "RR:d4": ("RR", "rr_pairing", {"model": "random_regular", "d": 4}),
    "ER:p080": ("ER", "er_gnp", {"model": "gnp", "p": "0.080", "p_num": 80, "p_den": 1000}),
}
N_VALUES = (128, 256, 512, 1024)
#: more graphs per cell as n grows, because a single cell's rho is an estimate from a
#: small sample (the frozen suite's own 2-graph ER:p080 cell and the fresh n=128 cell
#: differ by ~0.10 -- see LEVERS.md).  n=128 keeps 2, matching the frozen suite's own
#: 2-per-stratum density.
REPS_BY_N = {128: 2, 256: 4, 512: 4, 1024: 4}


def load_generator_module():
    spec = importlib.util.spec_from_file_location("frozen_maxcut_suite", GEN_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def graph_id_for(stratum, n, rep):
    fam, _, _ = STRATA[stratum]
    return f"L1_{fam}{stratum.split(':')[1]}_n{n}_r{rep}"


def build_one(mod, stratum, n, rep):
    family, gen_name, params = STRATA[stratum]
    gid = graph_id_for(stratum, n, rep)
    seed = mod.derive_seed(MASTER, ROLE, family, stratum, rep, gid)
    rng = mod.SplitMix64(seed)
    edges, _labels = mod.GENERATORS[gen_name](n, params, rng)
    edges = sorted((u, v) if u < v else (v, u) for u, v in edges)
    document = {
        "schema": mod.SCHEMA_GRAPH,
        "graph_id": gid,
        "family": family,
        "n": n,
        "edges": [[u, v] for u, v in edges],
        "generator": {"name": gen_name, "version": mod.GENERATOR_VERSION,
                      "params": params, "seed": seed},
        "notes": "L1 size-lever sample (redesign/); canonical form of INTERFACE.md section 2",
    }
    return document, edges


def manifest_entry(mod, document, edges, stratum, n, rep):
    payload = mod.canonical_bytes(document)
    stats = mod.graph_statistics(n, edges)
    gid = document["graph_id"]
    return {
        "graph_id": gid,
        "role": ROLE,
        "path": f"L1/{gid}.json",
        "family": document["family"],
        "stratum": stratum,
        "n": n,
        "rep": rep,
        "edges": stats["edges"],
        "graph_sha256": mod.sha256_bytes(payload),
        "generator": document["generator"],
        "degree": stats["degree"],
        "components": stats["components"],
        "isolated_nodes": stats["isolated_nodes"],
        "edge_set_sha256": mod.sha256_bytes(mod.canonical_bytes([list(e) for e in edges])),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="re-derive every graph and compare to what is on disk")
    args = ap.parse_args(argv)

    mod = load_generator_module()
    out_dir = REDESIGN / "instances"
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for stratum in STRATA:
        for n in N_VALUES:
            for rep in range(REPS_BY_N[n]):
                document, edges = build_one(mod, stratum, n, rep)
                entry = manifest_entry(mod, document, edges, stratum, n, rep)
                payload = mod.canonical_bytes(document)
                target = out_dir / entry["path"]
                if args.check:
                    on_disk = target.read_bytes()
                    if on_disk != payload:
                        raise SystemExit(f"MISMATCH {target}")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                entries.append(entry)
                print(f"{'checked' if args.check else 'wrote'} {entry['graph_id']:28s} "
                      f"n={n:5d} |E|={entry['edges']:6d} "
                      f"iso={entry['isolated_nodes']}")

    manifest = {
        "schema": "a0.maxcut.suite.manifest/v1",
        "suite_version": "L1-redesign-1.0.0",
        "frozen_on": "2026-09-22",
        "n": "mixed (128/256/512/1024)",
        "canonical_form": 'json.dumps(obj, sort_keys=True, separators=(",", ":"), '
                          'ensure_ascii=True) + "\\n"',
        "identity": "graph identity = sha256 of the canonical bytes of L1/<graph_id>.json; "
                    "generator.seed is provenance only (INTERFACE.md section 2)",
        "roles": {ROLE: "L1 size-lever measurement sample; not part of the frozen suite"},
        "generator": {"name": "generators/maxcut_suite.py", "version": mod.GENERATOR_VERSION,
                      "source_sha256": mod.sha256_file(GEN_MODULE)},
        "generator_config": {"role": ROLE, "master_seed": MASTER, "reps_by_n": REPS_BY_N,
                             "n_values": list(N_VALUES),
                             "strata": {k: list(v) for k, v in STRATA.items()}},
        "graphs": entries,
    }
    manifest_path = out_dir / "manifest.json"
    if args.check:
        on_disk = json.loads(manifest_path.read_text())
        if on_disk["graphs"] != entries:
            raise SystemExit("MISMATCH manifest.json")
        print(f"OK: {len(entries)} graphs re-derived and byte-identical; manifest matches")
    else:
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        print(f"wrote {manifest_path} ({len(entries)} graphs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
