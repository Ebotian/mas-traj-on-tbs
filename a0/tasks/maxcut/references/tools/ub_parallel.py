#!/usr/bin/env python3
"""Compute the rigorous upper bounds U_i for every graph of the suite, in parallel.

`build_targets.py --ub-iters N` computes the bounds serially, which costs about
8 s per graph.  This driver does the same work across the available cores and
caches one JSON per graph under `ub/`, so that

  * assembling targets.json is fast and re-runnable without recomputing bounds,
  * a partially finished bound sweep can be topped up rather than restarted,
  * the driving data behind each U_i (lambda_min, the SDP information, the
    Burer-Monteiro certificate) survives in a file instead of only inside
    targets.json.

The cache is keyed by the *graph* sha256 manifest entry and by the parameters of
the bound computation, so changing `--iters` or `--bm-iters` invalidates it
rather than silently mixing bound regimes.

Usage:
    python3 ub_parallel.py --manifest ../suite/manifest.json \
        --targets targets.json --out ub --jobs 11 --iters 4000

    # only the graphs that are still uncertified:
    python3 ub_parallel.py --manifest ../suite/manifest.json \
        --targets targets.json --out ub --only-uncertified
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from canonical import file_sha256, load_graph  # noqa: E402
from upper_bounds import upper_bounds  # noqa: E402

SCHEMA = "a0.maxcut.reference.ub/v1"


def cache_key(graph_sha256, iters, bm_rank, bm_iters):
    return {"graph_sha256": graph_sha256, "iters": iters,
            "bm_rank": bm_rank, "bm_iters": bm_iters}


def compute_one(path, graph_sha256, feasible_lower, iters, bm_rank, bm_iters):
    g = load_graph(path)
    t0 = time.time()
    ub = upper_bounds(g, feasible_lower=feasible_lower, iters=iters,
                      bm_rank=bm_rank, bm_iters=bm_iters)
    return {
        "schema": SCHEMA,
        "graph_id": g["graph_id"],
        "graph_path": path,
        "graph_sha256": graph_sha256,
        "graph_sha256_observed": file_sha256(path),
        "feasible_lower_used": feasible_lower,
        "params": {"iters": iters, "bm_rank": bm_rank, "bm_iters": bm_iters},
        "keys": cache_key(graph_sha256, iters, bm_rank, bm_iters),
        "wall_s": round(time.time() - t0, 3),
        "U_spectral": float(ub["U_spectral"]),
        "U_sdp_dual": float(ub["U_sdp_dual"]),
        "U_bm_certificate": float(ub["U_bm_certificate"]),
        "U_min": float(ub["U_min"]),
        "lambda_min": ub["lambda_min"],
        "n_effective": ub["n_effective"],
        "edges_total": ub["edges_total"],
        "sdp_info": ub["sdp_info"],
        "bm_info": ub["bm_info"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--targets", default="targets.json",
                    help="targets.json already built; supplies R_i as the "
                         "feasible lower bound that anchors the SDP dual step")
    ap.add_argument("--suite-root", default=None)
    ap.add_argument("--out", default="ub")
    ap.add_argument("--roles", nargs="*", default=["dev", "eval", "calibration"])
    ap.add_argument("--jobs", type=int, default=11)
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--bm-rank", type=int, default=8)
    ap.add_argument("--bm-iters", type=int, default=3000)
    ap.add_argument("--only-uncertified", action="store_true",
                    help="skip graphs whose targets.json entry already has "
                         "opt_certified true (their U_i cannot improve)")
    ap.add_argument("--force", action="store_true",
                    help="recompute even if a valid cache entry exists")
    args = ap.parse_args()

    root = args.suite_root or os.path.dirname(os.path.abspath(args.manifest))
    with open(args.manifest) as fh:
        man = json.load(fh)

    refs = {}
    if os.path.exists(args.targets):
        with open(args.targets) as fh:
            refs = json.load(fh).get("graphs", {})

    os.makedirs(args.out, exist_ok=True)
    jobs, skipped = [], 0
    for e in man["graphs"]:
        gid = e["graph_id"]
        if args.roles and e["role"] not in args.roles:
            continue
        ref = refs.get(gid) or {}
        if ref.get("R") is None:
            print("skip %s: no R_i in %s yet" % (gid, args.targets), file=sys.stderr)
            continue
        if args.only_uncertified and ref.get("opt_certified"):
            skipped += 1
            continue
        path = os.path.join(root, e["path"])
        rec_path = os.path.join(args.out, gid + ".json")
        if not args.force and os.path.exists(rec_path):
            with open(rec_path) as fh:
                old = json.load(fh)
            if (old.get("keys") == cache_key(e["graph_sha256"], args.iters,
                                             args.bm_rank, args.bm_iters)
                    and old.get("feasible_lower_used") == ref["R"]
                    and old.get("graph_sha256_observed") == file_sha256(path)):
                skipped += 1
                continue
        jobs.append((gid, rec_path, path, e["graph_sha256"], ref["R"]))

    print("bounds: %d to compute, %d already valid -> %s"
          % (len(jobs), skipped, args.out), flush=True)
    t0 = time.time()
    if not jobs:
        return
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(compute_one, p, s, r, args.iters, args.bm_rank,
                          args.bm_iters): gid for gid, _, p, s, r in jobs}
        done = 0
        for fut in cf.as_completed(futs):
            gid = futs[fut]
            rec = fut.result()
            tmp = os.path.join(args.out, gid + ".json.tmp")
            with open(tmp, "w") as fh:
                json.dump(rec, fh, indent=2, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, os.path.join(args.out, gid + ".json"))
            done += 1
            print("[%d/%d] %-14s U_min=%.2f (spectral %.2f sdp %.2f bm %.2f) %.1fs"
                  % (done, len(jobs), gid, rec["U_min"], rec["U_spectral"],
                     rec["U_sdp_dual"], rec["U_bm_certificate"], rec["wall_s"]),
                  flush=True)
    print("bounds done in %.0fs -> %s" % (time.time() - t0, args.out))


if __name__ == "__main__":
    main()
