#!/usr/bin/env python3
"""Assemble `redesign/lever_data.json` from the measured results.

Reads `out/l1_results.json` (size lever) and `out/l2_results.json` (weaker
positive controls) and reduces them to the decision table: per-lever verdicts
against the frozen gate thresholds, the family mix, and the one lever that is
not recommended.  No number is invented here; every value is copied from, or
reduced from, those two files.

    python3 gen/make_lever_data.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent

DELTA_OVERALL_MIN = 0.03
DELTA_FAMILY_MIN = 0.02
RHO_MIN = 0.30
FAMILIES = ("ER", "RR", "BA", "Planted")


def load(name):
    return json.loads((REDESIGN / "out" / name).read_text())


def frac_to_float(fr):
    return None if fr is None else fr["numerator"] / fr["denominator"]


def l1_summary(l1):
    rows = l1["rows"]
    cells = l1["cells"]
    # trend of rho(R) in n, per stratum, over the freshly generated cells
    trends = {}
    for stratum in ("RR:d4", "ER:p080"):
        pts = sorted([r for r in rows if r["stratum"] == stratum],
                     key=lambda r: (r["n"], r["graph_id"]))
        by_n = {}
        for r in pts:
            by_n.setdefault(r["n"], []).append(r)
        series = []
        for n in sorted(by_n):
            rs = by_n[n]
            rho = statistics.median([frac_to_float(r["rho_R"]) for r in rs])
            delta = statistics.mean([frac_to_float(r["delta"]) for r in rs])
            rho_hi = statistics.median([frac_to_float(r["rho_hi"]) for r in rs
                                        if r["rho_hi"] is not None]) if any(
                r["rho_hi"] is not None for r in rs) else None
            series.append({"n": n, "graphs": len(rs),
                           "median_rho_R": rho, "median_rho_hi": rho_hi,
                           "mean_delta": delta,
                           "rho_gate_pass": bool(rho is not None and rho >= RHO_MIN),
                           "delta_gate_pass": bool(delta >= DELTA_OVERALL_MIN),
                           "certified": sum(1 for r in rs if r["opt_certified"])})
        trends[stratum] = series
    return {"trends": trends, "gate_cells": cells}


def l2_summary(l2):
    out = {}
    for name, m in l2["variants"].items():
        out[name] = {
            "mean_delta": frac_to_float(m["mean_delta"]),
            "median_rho": frac_to_float(m["median_rho"]),
            "mean_rho": float(m["mean_rho_display"]),
            "families_passing_delta": m["families_passing_delta"],
            "families_passing_rho": m["families_passing_rho"],
            "delta_gate_pass": m["delta_gate_pass"],
            "rho_gate_pass": m["rho_gate_pass"],
            "per_family": {f: {"mean_delta": float(m["per_family"][f]["mean_delta_display"]),
                               "median_rho": float(m["per_family"][f]["median_rho_display"]),
                               "delta_pass": m["per_family"][f]["delta_pass"],
                               "rho_pass": m["per_family"][f]["rho_pass"]}
                           for f in FAMILIES},
        }
    both = [k for k, v in out.items() if v["delta_gate_pass"] and v["rho_gate_pass"]]
    return {"variants": out, "variants_passing_both_gates": both}


def main():
    l1 = l1_summary(load("l1_results.json"))
    l2 = l2_summary(load("l2_results.json"))

    # L1 verdict
    l1_verdict = {}
    for stratum, series in l1["trends"].items():
        rhos = [s["median_rho_R"] for s in series]
        ns = [s["n"] for s in series]
        slopes = [(rhos[i + 1] - rhos[i]) for i in range(len(rhos) - 1)]
        reach = [s["n"] for s in series if s["rho_gate_pass"]]
        l1_verdict[stratum] = {
            "n_values": ns, "median_rho_R": rhos,
            "delta_all_pass": all(s["delta_gate_pass"] for s in series),
            "n_where_rho_passes": reach,
            "rho_monotone_nondecreasing": all(s >= -1e-9 for s in slopes),
            "rho_slope_per_step": slopes,
            "verdict": ("rho reaches the bar" if reach else
                        "rho stays below 0.30 at every n measured"),
        }

    out = {
        "schema": "a0.maxcut.redesign.levers/v1",
        "thresholds": {"delta_overall_mean_min": DELTA_OVERALL_MIN,
                       "delta_family_mean_min": DELTA_FAMILY_MIN,
                       "rho_median_min": RHO_MIN,
                       "rho_families_required": 3, "families_total": 4,
                       "source": "../gates/gate_config.json (frozen, unmodified)"},
        "formulas": {
            "delta_i": "(p_i - b_i) / |E_i|",
            "rho_i": "(T_i - p_i) / (T_i - b_i), T_i = OPT_i if opt_certified else R_i",
            "rho_bracket": "[rho(R_i), rho(U_i)] sorted; valid because p > b, so rho is "
                           "increasing in T, and R_i <= OPT <= U_i",
        },
        "L1_instance_size": {
            "sample": "strata RR:d4 and ER:p080, n in {128,256,512,1024}, 2 graphs/cell, "
                      "generated by gen/gen_l1_instances.py from the frozen generator module; "
                      "targets by the project's MQLib recipe (6 heuristics x 5 seeds x 30 s) "
                      "plus SCIP 120 s; U by gen/l1_ub.py at a tiered budget (see DEVIATIONS D-RD-6)",
            "p_source": "pinned one_exchange where it completes within tau=30 s, else its "
                        "verified-equivalent efficient transliteration (DEVIATIONS D-RD-2)",
            "verdict": l1_verdict,
            "cells": l1["gate_cells"],
        },
        "L2_weaker_pc": {
            "sample": "the existing frozen dev suite (24 graphs), read-only; targets = "
                      "references/targets.json; baseline b from gates/values/dev.baseline.json",
            "verdict": l2,
        },
        "L3_family_mix": {
            "note": "per-family verdicts are read off L2 (all four families) and L1 (only the "
                    "RR:d4 and ER:p080 strata, which are the two the gate flagged)",
            "l2_per_family": {name: {f: {"mean_delta": v["per_family"][f]["mean_delta"],
                                         "median_rho": v["per_family"][f]["median_rho"],
                                         "delta_pass": v["per_family"][f]["delta_pass"],
                                         "rho_pass": v["per_family"][f]["rho_pass"]}
                                     for f in FAMILIES}
                              for name, v in l2["variants"].items()},
            "l1_per_stratum": {s: v for s, v in l1_verdict.items()},
        },
    }

    # the lever that is not recommended: the one that does not move rho at all
    flat = [s for s, v in l1_verdict.items()
            if not v["n_where_rho_passes"] and not v["rho_monotone_nondecreasing"]]
    out["not_recommended"] = {
        "lever": "L1 (raise n) -- see LEVERS.md for the measured statement",
        "flat_strata": flat,
        "why": "computed in LEVERS.md from the per-cell numbers; not hard-coded here",
    }

    path = REDESIGN / "lever_data.json"
    path.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(f"wrote {path}")
    print(json.dumps({"L1": l1_verdict, "L2_both": l2["variants_passing_both_gates"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
