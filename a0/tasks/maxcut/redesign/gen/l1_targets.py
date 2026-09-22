#!/usr/bin/env python3
"""L1: build reference targets for the size-lever sample and reduce rho(n).

Step 1 runs the project's own builder (`references/tools/build_targets.py`) with
`--skip-ub` on the L1 log tree and SCIP results, so `R_i`, the run accounting and
any SCIP primal/certificate are computed by the project's recipe, not re-invented.

Step 2 merges the tiered `U_i` records written by `gen/l1_ub.py`, mirroring
`build_targets.read_ub` + its OPT determination (a graph is certified only when
`U_i == R_i`).  The merge is separate only because the UB budget is tiered by `n`
and `build_targets` takes one budget for the whole table.

Step 3 reduces rho as a function of n, with the lower-bound caveat made explicit:

    rho(T) = (T - p) / (T - b),  increasing in T exactly when p > b

so with an uncertified `R_i <= OPT <= U_i`, `rho(R)` is a **lower bound** on the
true headroom and `rho(U)` an upper bound; the bracket is reported per graph.

    python3 gen/l1_targets.py
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
BUILD_TARGETS = TASK / "references" / "tools" / "build_targets.py"
INSTANCES = REDESIGN / "instances"
MANIFEST = INSTANCES / "manifest.json"
UB = INSTANCES / "ub"


def raw(x):
    return None if x is None else {"numerator": x.numerator, "denominator": x.denominator}


def dec(x, places=9):
    return None if x is None else f"{float(x):.{places}f}"


def median(xs):
    s = sorted(xs)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def mean(xs):
    return sum(xs, Fraction(0)) / len(xs) if xs else None


def build_raw_targets():
    out = INSTANCES / "targets_raw.json"
    cmd = [sys.executable, str(BUILD_TARGETS),
           "--logs", str(INSTANCES / "logs"),
           "--logs-extra", str(INSTANCES / "logs_topup"),
           "--manifest", str(MANIFEST),
           "--suite-root", str(INSTANCES),
           "--scip", str(INSTANCES / "scip"),
           "--ub-cache", str(UB),
           "--skip-ub",
           "--out", str(out)]
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        raise SystemExit(f"build_targets failed:\n{proc.stderr}")
    return json.loads(out.read_text())


def merge_ub(doc):
    for gid, e in doc["graphs"].items():
        best = e["R"]
        rec_path = UB / f"{gid}.json"
        mine = None
        if rec_path.is_file():
            rec = json.loads(rec_path.read_text())
            ub_min = rec["U_min"]
            mine = int(ub_min - 1e-9) if ub_min >= best else None
            e["U_merge_record"] = {"U_min": rec["U_min"], "U_spectral": rec["U_spectral"],
                                   "U_sdp_dual": rec["U_sdp_dual"],
                                   "U_bm_certificate": rec["U_bm_certificate"],
                                   "params": rec["params"], "wall_s": rec["wall_s"]}
        cands = [x for x in (e.get("U"), mine) if x is not None]
        if cands:
            U = min(cands)
            e["U"] = U
            e["U_minus_R"] = U - best
            e["R_over_U"] = best / U if U else None
            e["U_consistent_with_R"] = bool(U >= best)
            if U == best:
                e["OPT"] = best
                e["opt_certified"] = True
                e["opt_note"] = "certified: U_i == R_i"
            elif not e.get("opt_certified"):
                e["OPT"] = None
                e["opt_certified"] = False
                e["opt_note"] = ("not certified: U_i - R_i = %d > 0; R_i is a LOWER "
                                 "bound on the optimum" % (U - best))
        else:
            e.setdefault("U", None)
            e.setdefault("OPT", None)
            e["opt_certified"] = bool(e.get("opt_certified", False))
    return doc


def reduce_rho(doc, values):
    rows = []
    for g in values["rows"]:
        gid = g["graph_id"]
        e = doc["graphs"][gid]
        b, p = int(g["b"]), int(g["p"])
        R = int(e["R"])
        U = e.get("U")
        T = e["OPT"] if e.get("opt_certified") else R
        rho_R = Fraction(R - p, R - b) if R != b else None
        rho_U = Fraction(U - p, U - b) if (U is not None and U != b) else None
        lo, hi = None, None
        if rho_R is not None and rho_U is not None:
            lo, hi = (rho_R, rho_U) if rho_R <= rho_U else (rho_U, rho_R)
        rows.append({
            "graph_id": gid, "family": g["family"], "stratum": g["stratum"], "n": g["n"],
            "edges": g["edges"], "b": b, "p": p, "R": R, "U": U, "T": T,
            "opt_certified": bool(e.get("opt_certified")),
            "T_is_lower_bound_on_opt": not bool(e.get("opt_certified")),
            "delta": Fraction(p - b, g["edges"]),
            "rho_R": rho_R, "rho_U": rho_U, "rho_lo": lo, "rho_hi": hi,
            "p_over_T": Fraction(p, T) if T else None,
            "headroom_closed": Fraction(p - b, T - b) if T != b else None,
            "U_minus_R": (U - R) if U is not None else None,
        })

    by_cell = {}
    for r in rows:
        key = f"{r['stratum']}|n={r['n']}"
        by_cell.setdefault(key, []).append(r)

    cells = {}
    for key, rs in sorted(by_cell.items()):
        deltas = [r["delta"] for r in rs]
        rhos = [r["rho_R"] for r in rs if r["rho_R"] is not None]
        los = [r["rho_lo"] for r in rs if r["rho_lo"] is not None]
        his = [r["rho_hi"] for r in rs if r["rho_hi"] is not None]
        cells[key] = {
            "graphs": len(rs),
            "n": rs[0]["n"], "stratum": rs[0]["stratum"],
            "mean_delta": raw(mean(deltas)), "mean_delta_display": dec(mean(deltas)),
            "median_rho_R": raw(median(rhos)), "median_rho_R_display": dec(median(rhos)),
            "median_rho_lo_display": dec(median(los)), "median_rho_hi_display": dec(median(his)),
            "median_p_over_T_display": dec(median([r["p_over_T"] for r in rs])),
            "median_headroom_closed_display": dec(median([r["headroom_closed"] for r in rs])),
            "certified": sum(1 for r in rs if r["opt_certified"]),
        }
    return rows, cells


def display_rows(rows):
    return [{k: (raw(v) if isinstance(v, Fraction) else v) for k, v in r.items()} for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args(argv)

    if args.skip_build:
        doc = json.loads((INSTANCES / "targets_raw.json").read_text())
    else:
        doc = build_raw_targets()
    doc = merge_ub(doc)
    (INSTANCES / "targets.json").write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n")

    values = json.loads((REDESIGN / "out" / "l1_values.json").read_text())
    rows, cells = reduce_rho(doc, values)

    print(f"\n{'stratum':10s} {'n':>5s} {'|E|':>6s} {'b':>6s} {'p':>7s} {'R':>7s} {'U':>7s} "
          f"{'cert':>4s} {'Δ':>9s} {'ρ(R)':>9s} {'ρ bracket':>20s} {'p/T':>7s}")
    for r in sorted(rows, key=lambda x: (x["stratum"], x["n"], x["graph_id"])):
        br = (f"[{dec(r['rho_lo'],4)},{dec(r['rho_hi'],4)}]"
              if r["rho_lo"] is not None else "-")
        print(f"{r['stratum']:10s} {r['n']:>5d} {r['edges']:>6d} {r['b']:>6d} {r['p']:>7d} "
              f"{r['R']:>7d} {str(r['U']):>7s} {str(r['opt_certified']):>4s} "
              f"{dec(r['delta'],4):>9s} {dec(r['rho_R'],4):>9s} {br:>20s} {dec(r['p_over_T'],4):>7s}")

    print(f"\n{'stratum':10s} {'n':>5s} {'Δ mean':>9s} {'median ρ(R)':>12s} "
          f"{'ρ bracket median':>22s} {'p/T':>7s} {'gapclosed':>10s}")
    for key, c in sorted(cells.items(), key=lambda kv: (kv[1]["stratum"], kv[1]["n"])):
        br = f"[{c['median_rho_lo_display']},{c['median_rho_hi_display']}]"
        print(f"{c['stratum']:10s} {c['n']:>5d} {c['mean_delta_display']:>9s} "
              f"{c['median_rho_R_display']:>12s} {br:>22s} "
              f"{c['median_p_over_T_display']:>7s} {c['median_headroom_closed_display']:>10s}")

    out = {"schema": "a0.maxcut.redesign.l1/v1",
           "note": "T_i = OPT_i where opt_certified else R_i (a lower bound on the optimum). "
                   "rho(R) is a lower bound on the true headroom when p > b; [rho_lo, rho_hi] "
                   "brackets it using the rigorous U_i. rho values in the gate's sense are rho_R.",
           "targets_sha256_note": "see instances/targets.json",
           "rows": display_rows(rows), "cells": cells}
    (REDESIGN / "out" / "l1_results.json").write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print("\nwrote instances/targets.json and out/l1_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
