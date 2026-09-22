#!/usr/bin/env python3
"""L1: rigorous upper bounds U_i on the size-lever sample, at a tiered budget.

`U_i` is what turns an uncertified heuristic target `R_i` into a *bracket*
[R_i, U_i] around the true optimum, and therefore what turns a rho computed
against `R_i` into an interval.  Every iterate of the SDP-dual subgradient is a
valid bound, so a reduced iteration count only weakens the bracket; it never
invalidates it (references/tools/upper_bounds.py, module docstring).

Budget by size (recorded per graph in the emitted record):
    n <= 256 : the project recipe (iters 4000, bm_rank 8, bm_iters 3000)
    n == 512 : capped (iters 1500, bm_iters 1500)
    n >= 1024: capped (iters 400,  bm_iters 600)

    python3 gen/l1_ub.py --targets instances/targets.json [--force]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
sys.path.insert(0, str(TASK / "references" / "tools"))
from canonical import load_graph  # noqa: E402
from upper_bounds import upper_bounds  # noqa: E402

MANIFEST = REDESIGN / "instances" / "manifest.json"
OUT = REDESIGN / "instances" / "ub"


def tier(n):
    if n <= 256:
        return {"iters": 4000, "bm_rank": 8, "bm_iters": 3000, "label": "project recipe"}
    if n == 512:
        return {"iters": 1500, "bm_rank": 8, "bm_iters": 1500, "label": "capped (1500)"}
    return {"iters": 400, "bm_rank": 8, "bm_iters": 600, "label": "capped (400/600)"}


def compute_one(job):
    gid, path, sha, feasible_lower, params = job
    graph = load_graph(path)
    t0 = time.time()
    ub = upper_bounds(graph, feasible_lower=feasible_lower, iters=params["iters"],
                      bm_rank=params["bm_rank"], bm_iters=params["bm_iters"])
    rec = {
        "graph_id": gid,
        "graph_sha256_observed": sha,
        "feasible_lower_used": feasible_lower,
        "keys": {"graph_sha256": sha, "iters": params["iters"],
                 "bm_rank": params["bm_rank"], "bm_iters": params["bm_iters"]},
        "params": params,
        "wall_s": round(time.time() - t0, 1),
        "U_min": ub["U_min"], "U_spectral": ub["U_spectral"],
        "U_sdp_dual": ub["U_sdp_dual"], "U_bm_certificate": ub["U_bm_certificate"],
        "lambda_min": ub["lambda_min"], "n_effective": ub["n_effective"],
        "sdp_info": ub["sdp_info"], "bm_info": ub["bm_info"],
    }
    (OUT / f"{gid}.json").write_text(json.dumps(rec, sort_keys=True, indent=2) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    man = json.loads(MANIFEST.read_text())
    root = MANIFEST.parent
    targets = json.loads(Path(args.targets).read_text())["graphs"]
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for e in man["graphs"]:
        gid = e["graph_id"]
        rec_path = OUT / f"{gid}.json"
        params = tier(e["n"])
        if rec_path.is_file() and not args.force:
            old = json.loads(rec_path.read_text())
            if (old.get("graph_sha256_observed") == e["graph_sha256"]
                    and old.get("params") == params
                    and old.get("feasible_lower_used") == targets[gid]["R"]):
                print(f"skip {gid} (cached)")
                continue
        R = targets[gid]["R"]
        jobs.append((gid, str(root / e["path"]), e["graph_sha256"], R, params))
    if not jobs:
        print("nothing to do")
        return 0
    print(f"computing {len(jobs)} upper bounds, jobs={args.jobs}")
    with cf.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for fut in cf.as_completed([pool.submit(compute_one, j) for j in jobs]):
            rec = fut.result()
            print(f"  {rec['graph_id']:24s} U_min={rec['U_min']:10.2f} "
                  f"(spec {rec['U_spectral']:.1f} sdp {rec['U_sdp_dual']:.1f} "
                  f"bm {rec['U_bm_certificate']:.1f}) R={rec['feasible_lower_used']} "
                  f"{rec['wall_s']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
