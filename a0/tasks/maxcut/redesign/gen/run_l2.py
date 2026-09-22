#!/usr/bin/env python3
"""L2: measure Delta and rho for positive controls of decreasing strength.

Reads the frozen dev suite and the frozen reference targets read-only, runs each
generated candidate through the harness-owned evaluator E* (`../e_star.py
evaluate`, theta = seed 1337, tau 30 s), and reduces the resulting integer
`cut_edges` with `fractions.Fraction` only -- the gate's own quantities:

    delta_i = (p_i - b_i) / |E_i|
    rho_i   = (T_i - p_i) / (T_i - b_i),  T_i = OPT_i if certified else R_i

Baseline b_i is taken from the frozen E* Outcomes in `../gates/values/` (the same
numbers the gate used), so this measurement is comparable to `verdict.dev.json`
graph by graph.  The `exchange_opt` variant must reproduce the frozen PC's
`cut_edges` on all 24 graphs; that equality is asserted, not assumed.

    python3 gen/run_l2.py            # measure (cached outcomes reused)
    python3 gen/run_l2.py --force    # re-run E* for every graph
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
E_STAR = TASK / "e_star.py"
MANIFEST = TASK / "suite" / "manifest.json"
TARGETS = TASK / "references" / "targets.json"
FROZEN_BASELINE = TASK / "gates" / "values" / "dev.baseline.json"
FROZEN_PC = TASK / "gates" / "values" / "dev.positive-control.json"

SEED = 1337
TIMEOUT = 30.0
FAMILIES = ("ER", "RR", "BA", "Planted")
VARIANT_ORDER = ["exchange_opt", "exchange_k25", "exchange_k10", "exchange_k5",
                 "exchange_k2", "exchange_k1", "greedy", "rand_part"]

DELTA_OVERALL_MIN = Fraction(3, 100)
DELTA_FAMILY_MIN = Fraction(2, 100)
DELTA_FAMILIES_REQUIRED = 3
RHO_MIN = Fraction(3, 10)
RHO_FAMILIES_REQUIRED = 3


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #

def dev_graphs():
    man = json.loads(MANIFEST.read_text())
    root = MANIFEST.parent
    out = []
    for e in man["graphs"]:
        if e["role"] != "dev":
            continue
        out.append({"graph_id": e["graph_id"], "family": e["family"],
                    "stratum": e["stratum"], "edges": e["edges"],
                    "path": str(root / e["path"]),
                    "graph_sha256": e["graph_sha256"]})
    out.sort(key=lambda g: g["graph_id"])
    return out


def targets_by_graph():
    doc = json.loads(TARGETS.read_text())
    out = {}
    for gid, e in doc["graphs"].items():
        T = e["OPT"] if e.get("opt_certified") else e["R"]
        out[gid] = {"T": T, "opt_certified": bool(e.get("opt_certified")),
                    "R": e["R"], "U": e.get("U")}
    return out


def frozen_values(path):
    doc = json.loads(path.read_text())
    out = {}
    for o in doc["outcomes"]:
        if o["status"] != "ok":
            raise SystemExit(f"frozen outcome not ok: {o['graph_id']} {o['status']}")
        out[o["graph_id"]] = int(o["cut_edges"])
    return out


# --------------------------------------------------------------------------- #
# E* invocation
# --------------------------------------------------------------------------- #

def outcome_path(variant, graph_id):
    return REDESIGN / "out" / "l2_outcomes" / variant / f"{graph_id}.outcome.json"


def evaluate(variant, graph, force=False):
    path = outcome_path(variant, graph["graph_id"])
    if path.is_file() and not force:
        return json.loads(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_dir = REDESIGN / "candidates" / variant
    command = [sys.executable, str(E_STAR), "evaluate",
               "--candidate", str(candidate_dir),
               "--graph", graph["path"],
               "--seed", str(SEED), "--timeout", str(TIMEOUT),
               "--out", str(path),
               "--state-dir", str(REDESIGN / "out" / "e-star-state" / variant)]
    proc = subprocess.run(command, capture_output=True, text=True)
    if not path.is_file():
        raise SystemExit(f"E* wrote no Outcome for {variant} {graph['graph_id']}: "
                         f"{proc.stdout}\n{proc.stderr}")
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- #
# exact reductions (mirroring gates/gate_runner.py, re-implemented)
# --------------------------------------------------------------------------- #

def mean(xs):
    return sum(xs, Fraction(0)) / len(xs) if xs else None


def median(xs):
    s = sorted(xs)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def raw(x):
    if x is None:
        return None
    return {"numerator": x.numerator, "denominator": x.denominator}


def dec(x, places=9):
    if x is None:
        return None
    return f"{float(x):.{places}f}"


def measure(variant, graphs, targets, baseline, frozen_pc):
    rows = []
    for g in graphs:
        gid = g["graph_id"]
        o = evaluate(variant, g)
        p = o.get("cut_edges") if o["status"] == "ok" else None
        b = baseline[gid]
        T = targets[gid]["T"]
        row = {"graph_id": gid, "family": g["family"], "stratum": g["stratum"],
               "edges": g["edges"], "b": b, "p": p, "T": T,
               "opt_certified": targets[gid]["opt_certified"],
               "status": o["status"], "candidate_source_sha256": o.get("candidate_source_sha256")}
        if p is None:
            row["scored"] = False
        else:
            row["scored"] = True
            row["delta"] = Fraction(p - b, g["edges"])
            gap = T - b
            row["rho"] = Fraction(T - p, gap) if gap != 0 else None
            row["delta_vs_frozen_pc"] = p - frozen_pc[gid]
        rows.append(row)

    scored = [r for r in rows if r["scored"]]
    per_family = {}
    for fam in FAMILIES:
        fr = [r for r in scored if r["family"] == fam]
        deltas = [r["delta"] for r in fr if r.get("delta") is not None]
        rhos = [r["rho"] for r in fr if r.get("rho") is not None]
        per_family[fam] = {
            "graphs": len(fr),
            "mean_delta": raw(mean(deltas)), "mean_delta_display": dec(mean(deltas)),
            "median_rho": raw(median(rhos)), "median_rho_display": dec(median(rhos)),
            "delta_pass": (mean(deltas) is not None and mean(deltas) >= DELTA_FAMILY_MIN),
            "rho_pass": (median(rhos) is not None and median(rhos) >= RHO_MIN),
        }
    overall_deltas = [r["delta"] for r in scored if r.get("delta") is not None]
    overall_rhos = [r["rho"] for r in scored if r.get("rho") is not None]
    mean_delta = mean(overall_deltas)
    med_rho = median(overall_rhos)
    n_delta_fams = sum(1 for f in per_family.values() if f["delta_pass"])
    n_rho_fams = sum(1 for f in per_family.values() if f["rho_pass"])
    return {
        "variant": variant,
        "rows": [{k: (raw(v) if isinstance(v, Fraction) else v) for k, v in r.items()}
                 for r in rows],
        "mean_delta": raw(mean_delta), "mean_delta_display": dec(mean_delta),
        "median_rho": raw(med_rho), "median_rho_display": dec(med_rho),
        "mean_rho_display": dec(mean(overall_rhos)),
        "min_rho_display": dec(min(overall_rhos)) if overall_rhos else None,
        "max_rho_display": dec(max(overall_rhos)) if overall_rhos else None,
        "graphs_rho_ge_030": sum(1 for r in overall_rhos if r >= RHO_MIN),
        "per_family": per_family,
        "delta_gate_pass": bool(mean_delta is not None and mean_delta >= DELTA_OVERALL_MIN
                                and n_delta_fams >= DELTA_FAMILIES_REQUIRED),
        "rho_gate_pass": bool(med_rho is not None and med_rho >= RHO_MIN
                              and n_rho_fams >= RHO_FAMILIES_REQUIRED),
        "families_passing_delta": n_delta_fams,
        "families_passing_rho": n_rho_fams,
        "max_targets_uncertified": sum(1 for r in rows if not r["opt_certified"]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--variants", nargs="*", default=VARIANT_ORDER)
    args = ap.parse_args(argv)

    graphs = dev_graphs()
    targets = targets_by_graph()
    baseline = frozen_values(FROZEN_BASELINE)
    frozen_pc = frozen_values(FROZEN_PC)

    if args.force:
        for v in args.variants:
            for g in graphs:
                evaluate(v, g, force=True)

    result = {"schema": "a0.maxcut.redesign.l2/v1", "seed": SEED, "timeout_s": TIMEOUT,
              "graph_set": "dev (frozen suite, read-only)",
              "thresholds": {"delta_overall_mean_min": raw(DELTA_OVERALL_MIN),
                             "delta_family_mean_min": raw(DELTA_FAMILY_MIN),
                             "rho_median_min": raw(RHO_MIN)},
              "reference_pc_note": "the frozen PC's own p_i (exchange_opt) is reproduced "
                                   "here and cross-checked against gates/values/dev.positive-control.json",
              "variants": {}}
    print(f"{'variant':14s} {'meanDelta':>10s} {'medRho':>9s} {'Δfam':>5s} {'ρfam':>5s} "
          f"{'Δgate':>6s} {'ρgate':>6s}  Δp-vs-frozenPC")
    for v in args.variants:
        m = measure(v, graphs, targets, baseline, frozen_pc)
        result["variants"][v] = m
        diffs = [r.get("delta_vs_frozen_pc") for r in m["rows"] if r.get("delta_vs_frozen_pc") is not None]
        print(f"{v:14s} {m['mean_delta_display']:>10s} {m['median_rho_display']:>9s} "
              f"{m['families_passing_delta']:>5d} {m['families_passing_rho']:>5d} "
              f"{str(m['delta_gate_pass']):>6s} {str(m['rho_gate_pass']):>6s}  "
              f"min={min(diffs)} max={max(diffs)}")

    out = REDESIGN / "out" / "l2_results.json"
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"wrote {out}")

    # the internal-consistency assertion: exchange_opt == frozen PC, graph by graph
    opt = result["variants"]["exchange_opt"]
    bad = [r["graph_id"] for r in opt["rows"] if r.get("delta_vs_frozen_pc") not in (None, 0)]
    if bad:
        raise SystemExit(f"exchange_opt differs from the frozen PC on {len(bad)} graphs: {bad}")
    print("OK: exchange_opt reproduces the frozen PC cut_edges on all 24 dev graphs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
