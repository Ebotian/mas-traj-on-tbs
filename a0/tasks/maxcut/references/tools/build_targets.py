#!/usr/bin/env python3
"""Assemble references/targets.json from the ensemble logs.

R_i  = maximum *independently recomputed* cut over all (heuristic, seed) runs of
       graph i, with the winning (heuristic, seed) recorded as its source.  A
       feasible solution found by the SCIP certification pass is folded in the
       same way -- recomputed from a stored canonical partition before it is
       allowed to change any number.
OPT_i = the value of R_i only when a certificate closes the gap (SCIP proving
        optimality, or an upper bound equal to R_i), otherwise null.  A feasible
        value is a lower bound on the optimum, never an upper bound.
U_i  = the minimum over the rigorous upper bounds available: the spectral
       eigenvalue bound, the SDP/Delorme-Poljak dual bound, a Burer-Monteiro
       dual certificate, and SCIP's dual bound.

Usage:
    python3 build_targets.py --logs logs --manifest ../suite/manifest.json \
        --out targets.json [--scip scip] [--ub-iters 4000] [--skip-ub]
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from canonical import cut_fraction_display, file_sha256, load_graph  # noqa: E402
from fractions import Fraction  # noqa: E402
from run_ensemble import HEURISTICS, SEEDS, TIME_LIMIT_S  # noqa: E402


def load_runs(logs, extra=()):
    """Load every per-run record, from the primary log dir plus any extra dirs.

    Extra directories hold runs executed under a *different* budget (the 300 s
    top-up pass in `logs_topup/`).  They are folded into the same pool because
    R_i is a maximum over feasible solutions and a longer run can only ever
    tighten it; each record keeps its own `time_limit_s`, so a consumer can
    still tell which budget produced the winner, and the run's provenance is
    carried into `R_source`.
    """
    runs = {}
    seen = set()
    for d in (logs,) + tuple(extra):
        rdir = os.path.join(d, "runs")
        if not os.path.isdir(rdir):
            if d == logs:
                raise SystemExit("no runs dir at %s" % rdir)
            print("note: no extra runs dir at %s (skipped)" % rdir, file=sys.stderr)
            continue
        for fn in sorted(os.listdir(rdir)):
            if not fn.endswith(".json"):
                continue
            key = os.path.abspath(os.path.join(rdir, fn))
            if key in seen:
                continue
            seen.add(key)
            with open(key) as fh:
                rec = json.load(fh)
            rec["_log_dir"] = d
            runs.setdefault(rec["graph_id"], []).append(rec)
    return runs


def merge_scip(graphs, sdir, here):
    """Fold the SCIP attempt into the table.

    SCIP contributes two independent things:
      * a rigorous upper bound (its dual bound at the end of the run), which can
        only tighten `U_i`;
      * a feasible solution, which is only accepted as `R_i` after being
        recomputed from the stored canonical partition -- and, if SCIP closed
        the gap, a genuine optimality certificate.
    """
    if not os.path.isdir(sdir):
        return 0
    merged = 0
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(sdir, fn)) as fh:
            rec = json.load(fh)
        if rec.get("schema") != "a0.maxcut.scip_attempt/v1":
            continue          # skips the *.partition.json witnesses in the same dir
        e = graphs.get(rec.get("graph_id"))
        if e is None or e.get("R") is None:
            continue
        merged += 1
        e["scip"] = {
            "status": rec.get("status"),
            "solved_to_optimality": rec.get("solved_to_optimality"),
            "OPT_scip": rec.get("OPT_scip"),
            "dual_bound": rec.get("dual_bound"),
            "dual_bound_floor": rec.get("dual_bound_floor"),
            "gap_percent": rec.get("gap"),
            "wall_s": rec.get("wall_s"),
            "time_limit_s": rec.get("time_limit_s"),
            "formulation": rec.get("formulation"),
            "triangle_inequalities": rec.get("triangle_inequalities"),
            "primal_recomputed_cut": rec.get("primal_recomputed_cut"),
            "primal_recomputed_matches_scip": rec.get("primal_recomputed_matches_scip"),
            "primal_partition_path": rec.get("primal_partition_path"),
            "primal_partition_sha256": rec.get("primal_partition_sha256"),
            "record": os.path.relpath(os.path.join(sdir, fn), here),
        }
        sp = rec.get("primal_recomputed_cut")
        if sp is not None and sp > e["R"]:
            e["R_ensemble"] = e["R"]
            e["R"] = sp
            e["R_source"] = {"tool": "SCIP 10.0.3 (SoPlex 8.0.3)",
                             "run_id": rec.get("graph_id"),
                             "partition_sha256": rec.get("primal_partition_sha256")}
            e["R_source_note"] = ("SCIP's primal solution beat every ensemble run; "
                                  "accepted only after independent recomputation")
            e["R_source_is_ensemble"] = False
        ub = [x for x in (e.get("U"),
                          (int(math.floor(rec["dual_bound"] + 1e-9))
                           if rec.get("dual_bound") is not None else None))
              if x is not None]
        if ub:
            e["U"] = min(ub)
        if rec.get("status") == "certified_optimal" and rec.get("OPT_scip") is not None:
            e["OPT"] = rec["OPT_scip"]
            e["opt_certified"] = True
            e["opt_note"] = ("certified: SCIP closed the MIP gap; the dual bound "
                             "equals the recomputed feasible reference")
        if e.get("U") is not None:
            e["U_minus_R"] = e["U"] - e["R"]
            e["R_over_U"] = e["R"] / e["U"] if e["U"] else None
            e["U_consistent_with_R"] = bool(e["U"] >= e["R"])
        if e.get("opt_certified") and e["OPT"] != e["R"]:
            e["R_is_optimal"] = False
            e["mismatch_note"] = ("SCIP certified OPT=%s but the best feasible value "
                                  "recorded is %s; the two must agree, so inspect the "
                                  "solution parse" % (e["OPT"], e["R"]))
        elif e.get("opt_certified"):
            e["R_is_optimal"] = True
        else:
            e["R_is_optimal"] = None
    return merged


def read_ub(args, gid, best, graph_path):
    """Upper-bound record for one graph: from the `ub/` cache if valid, else live.

    The cache is written by tools/ub_parallel.py, which computes the same bound
    function but across cores and with one file per graph.  A cache entry is
    only used when its key (graph sha256 + bound parameters) and the feasible
    lower bound it was anchored to both match the current build; otherwise the
    bound is recomputed here serially, so a stale cache can never leak into
    targets.json unnoticed.
    """
    if args.skip_ub or not graph_path or not os.path.exists(graph_path):
        return None
    if args.ub_cache:
        rec_path = os.path.join(args.ub_cache, gid + ".json")
        if os.path.exists(rec_path):
            with open(rec_path) as fh:
                rec = json.load(fh)
            expected = {"graph_sha256": rec.get("graph_sha256_observed"),
                        "iters": args.ub_iters, "bm_rank": args.bm_rank,
                        "bm_iters": args.bm_iters}
            if rec.get("keys") == expected and rec.get("feasible_lower_used") == best:
                rec = dict(rec)
                rec["from_cache"] = os.path.relpath(rec_path, HERE)
                return rec
            print("ub cache miss for %s (key or lower bound changed); "
                  "recomputing" % gid, file=sys.stderr)
    from upper_bounds import upper_bounds
    g = load_graph(graph_path)
    ub = upper_bounds(g, feasible_lower=best, iters=args.ub_iters,
                      bm_rank=args.bm_rank, bm_iters=args.bm_iters)
    ub["from_cache"] = None
    return ub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--logs-extra", nargs="*", default=["logs_topup"],
                    help="additional log dirs holding runs under a different "
                         "time budget; folded into the R_i maximum")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--suite-root", default=None)
    ap.add_argument("--out", default="targets.json")
    ap.add_argument("--scip", default="scip", help="dir of scip_maxcut.py results")
    ap.add_argument("--ub-iters", type=int, default=4000)
    ap.add_argument("--bm-rank", type=int, default=8)
    ap.add_argument("--bm-iters", type=int, default=3000)
    ap.add_argument("--ub-cache", default="ub",
                    help="dir written by tools/ub_parallel.py; used when its key "
                         "and anchored lower bound match this build")
    ap.add_argument("--skip-ub", action="store_true")
    args = ap.parse_args()

    with open(args.manifest) as fh:
        man = json.load(fh)
    root = args.suite_root or os.path.dirname(os.path.abspath(args.manifest))
    meta = {}
    for e in man["graphs"]:
        meta[e["graph_id"]] = {
            "role": e["role"], "family": e["family"], "stratum": e["stratum"],
            "n": e["n"], "edges_total": e["edges"],
            "manifest_graph_sha256": e["graph_sha256"],
            "abs_path": os.path.join(root, e["path"]),
            "path": os.path.relpath(os.path.join(root, e["path"]), HERE),
        }

    runs = load_runs(args.logs, args.logs_extra)
    t0 = time.time()
    graphs = {}
    for gid in sorted(runs):
        recs = runs[gid]
        ok = [r for r in recs if r.get("status") == "ok"]
        if not ok:
            graphs[gid] = {"graph_id": gid, "R": None,
                           "reason": "no successful run", **meta.get(gid, {})}
            continue
        best = max(r["cut_edges"] for r in ok)
        ties = [{"heuristic": r["heuristic"], "seed": r["seed"],
                 "run_id": "%s__%s__s%d" % (gid, r["heuristic"], r["seed"]),
                 "wall_ms": r["interpreted"]["wall_ms"],
                 "time_limit_s": r.get("time_limit_s"),
                 "log_dir": r.get("_log_dir"),
                 "partition_sha256": r.get("partition_sha256")}
                for r in sorted(ok, key=lambda r: (r["heuristic"], r["seed"]))
                if r["cut_edges"] == best]
        ties.sort(key=lambda t: (t["time_limit_s"] or 0, t["heuristic"], t["seed"]))
        by_h = {}
        for h in HEURISTICS:
            vals = [r["cut_edges"] for r in ok if r["heuristic"] == h]
            if vals:
                by_h[h] = {"best": max(vals), "worst": min(vals), "runs": len(vals)}
        src = ties[0]
        best_budget = max(r.get("time_limit_s") or 0 for r in ok)
        distinct_limits = sorted({r.get("time_limit_s") for r in ok
                                  if r.get("time_limit_s") is not None})
        graph_path = meta[gid]["abs_path"] if gid in meta else None
        entry = {
            "graph_id": gid, "n": meta.get(gid, {}).get("n"),
            "family": meta.get(gid, {}).get("family"),
            "role": meta.get(gid, {}).get("role"),
            "stratum": meta.get(gid, {}).get("stratum"),
            "edges_total": ok[0]["edges_total"],
            "graph_sha256": ok[0]["graph_sha256"],
            "manifest_graph_sha256": meta.get(gid, {}).get("manifest_graph_sha256"),
            "graph_sha256_matches_manifest": (
                meta.get(gid, {}).get("manifest_graph_sha256") == ok[0]["graph_sha256"]),
            "graph_path": (os.path.relpath(graph_path, HERE)
                           if graph_path else None),
            "R": best,
            "R_ensemble": best,
            "R_source_is_ensemble": True,
            "R_fraction_display": cut_fraction_display(best, ok[0]["edges_total"]),
            "R_fraction_exact": "%d/%d" % (Fraction(best, ok[0]["edges_total"]).numerator,
                                           Fraction(best, ok[0]["edges_total"]).denominator),
            "R_fraction_exact_note": "R_i / |E_i|, reduced; this is the authoritative "
                                     "fraction -- R_fraction_display is a decimal "
                                     "display field and no verdict may use it "
                                     "(INTERFACE.md section 5)",
            "R_source": {"heuristic": src["heuristic"], "seed": src["seed"],
                         "run_id": "%s__%s__s%d" % (gid, src["heuristic"], src["seed"]),
                         "partition_sha256": src["partition_sha256"],
                         "wall_ms": src["wall_ms"],
                         "time_limit_s": src["time_limit_s"],
                         "log_dir": src["log_dir"]},
            "R_ties": ties,
            "R_from_topup": bool(src["time_limit_s"] and src["time_limit_s"] > TIME_LIMIT_S),
            "budgets_applied_s": distinct_limits,
            "largest_budget_that_reached_R_s": best_budget,
            "runs": {"ok": len(ok), "total": len(recs),
                     "expected_total": len(HEURISTICS) * len(SEEDS)},
            "best_by_heuristic": by_h,
        }
        ub = read_ub(args, gid, best, graph_path)
        if ub is not None:
            ub_min = ub["U_min"]
            entry["U"] = int(ub_min - 1e-9) if ub_min >= best else None
            entry["U_sources"] = {
                "spectral": ub["U_spectral"],
                "sdp_dual": ub["U_sdp_dual"],
                "bm_certificate": ub["U_bm_certificate"],
                "lambda_min": ub["lambda_min"],
                "n_effective": ub["n_effective"],
                "sdp_info": ub["sdp_info"],
                "bm_info": ub["bm_info"],
                "from_cache": ub.get("from_cache"),
            }
            entry["U_consistent_with_R"] = bool(ub_min + 1e-9 >= best)
            if entry["U"] is not None:
                entry["U_minus_R"] = entry["U"] - best
                entry["R_over_U"] = best / entry["U"] if entry["U"] else None
                if entry["U"] == best:
                    entry["OPT"] = best
                    entry["opt_certified"] = True
                    entry["opt_note"] = ("certified: the relaxation upper bound "
                                         "equals the feasible reference")
                else:
                    entry["OPT"] = None
                    entry["opt_certified"] = False
                    entry["opt_note"] = ("not certified: U_i - R_i = %d > 0; R_i is a "
                                         "feasible value, i.e. a LOWER bound on the "
                                         "optimum" % entry["U_minus_R"])
            else:
                entry["OPT"] = None
                entry["opt_certified"] = False
                entry["R_over_U"] = None
                entry["opt_note"] = ("not certified: the computed upper bound fell below "
                                     "the feasible reference, which means the bound "
                                     "computation is wrong; reported rather than hidden")
        else:
            entry["U"] = None
            entry["U_sources"] = None
            entry["OPT"] = None
            entry["opt_certified"] = False
            entry["opt_note"] = "upper bounds not computed in this build"
        graphs[gid] = entry

    merge_scip(graphs, args.scip, HERE)

    # print only after the SCIP pass: before it, `U` and `OPT` are still the
    # relaxation-only values and a reader would reasonably misread them
    for gid in sorted(graphs):
        e = graphs[gid]
        print("%-14s R=%-5s U=%-6s OPT=%-5s %s (%.0fs)"
              % (gid, e.get("R"), e.get("U"), e.get("OPT"),
                 "certified" if e.get("opt_certified") else "feasible-only",
                 time.time() - t0), flush=True)

    doc = {
        "schema": "a0.maxcut.references/v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "definition": {
            "R_i": "best feasible cut found by the diverse heuristic ensemble; the "
                   "authoritative value is the integer recomputed from graph.json + "
                   "partition.json by tools/verify_partition.py, never MQLib's own "
                   "reported objective",
            "OPT_i": "the value of R_i if and only if an upper bound closes the gap "
                     "(U_i == R_i); otherwise null",
            "U_i": "minimum of the rigorous upper bounds actually computed "
                   "(spectral eigenvalue bound, SDP/Delorme-Poljak dual bound)",
            "lower_bound_warning": "a feasible cut is a LOWER bound on the optimum; "
                                   "it is never an upper bound",
        },
        "ensemble": {
            "tool": "MQLib",
            "commit_pin": "585496274af5abb0849d0d47e135496b4688680b",
            "build": "build/build_mqlib.sh",
            "heuristics": HEURISTICS,
            "seeds": SEEDS,
            "time_limit_s": TIME_LIMIT_S,
            "seeds_note": "five fixed seeds spread over MQLib's 0..65535 seed range; "
                          "MQLib's time-based termination makes an individual run "
                          "non-reproducible in principle, but R_i is a maximum over "
                          "runs and is reported together with the partitions that "
                          "witness it",
            "provenance": json.load(open(os.path.join(HERE, "..", "build",
                                                      "PROVENANCE.json"))),
        },
        "graphs": graphs,
    }
    with open(args.out + ".tmp", "w") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(args.out + ".tmp", args.out)
    print("wrote %s (%d graphs) in %.0fs" % (args.out, len(graphs), time.time() - t0))


if __name__ == "__main__":
    main()
