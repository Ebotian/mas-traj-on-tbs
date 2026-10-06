#!/usr/bin/env python3
"""Derive src/data/experiments.json from the repro bundle, with the beta-binomial
recomputation that the visualization charts.

Source of truth: related_files/agent_engineering_science_repro_bundle.zip, which is
NOT tracked by git (the corpus whitelist excludes .zip). This script is the reason
that is tolerable: the numbers the app draws are re-derivable from it, and the
derivation is checked in rather than pasted.

Run:  python3 scripts/derive_experiments.py     (from viz/, or pass --zip)

What it computes beyond copying the CSVs:
  exp1  exact majority-vote probability under the exchangeable beta-binomial with
        the same p and pairwise rho, i.e. Theta ~ Beta(a,b), a=p(1/rho-1),
        b=(1-p)(1/rho-1), agents conditionally independent given Theta. This is
        the model the 2026-09-24 independent review constructed as a
        counterexample. Also the binomial standard error at the reported trial
        count, the z-distance, and the divergent table from Pasted markdown.md.
  exp2  nothing added; the defect (adaptive samples saturating above budget 20)
        is annotated from the data itself.
  exp3  nothing added; the saturation is annotated.

Every constant taken from a document is cited in the JSON so the app can show it.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import zipfile
from datetime import date
from pathlib import Path

from scipy.stats import betabinom, binom

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ZIP = REPO / "related_files" / "agent_engineering_science_repro_bundle.zip"
OUT = Path(__file__).resolve().parents[1] / "src" / "data" / "experiments.json"

P_AGENT = 0.7  # marginal accuracy, stated in both the report and Pasted markdown.md

# report.tex:415 (appendix "沙箱实验复现信息"), read verbatim
REPRO = {
    "seed": 42,
    "rng": "NumPy",
    "libs": "NumPy/SciPy/Matplotlib",
    "trials": {"exp1_per_point": 150000, "exp2_per_cell": 25000, "exp3_per_level": 10000},
    "disclaimer": "所有模拟均为机制示例，不应被引用为真实 LLM Agent 的性能证据。",
    "cite": "agent_engineering_science_report.tex:415",
}

# Pasted markdown.md §2 table, transcribed. It claims 30000 runs per cell.
PASTED_MD = {
    "claimed_trials": 30000,
    "cells": {
        "0|5": 0.838, "0|17": 0.961, "0|33": 0.992,
        "0.3|5": 0.773, "0.3|17": 0.812, "0.3|33": 0.820,
        "0.7|5": 0.723, "0.7|17": 0.730, "0.7|33": 0.732,
        "0.9|33": 0.708,
    },
}


def majority_beta_binom(n: int, rho: float, p: float = P_AGENT) -> float:
    """P(strict majority correct) for n agents, marginal p, pairwise correlation rho."""
    k = n // 2 + 1
    if rho <= 0:
        return float(binom.sf(k - 1, n, p))
    a = p * (1.0 / rho - 1.0)
    b = (1.0 - p) * (1.0 / rho - 1.0)
    return float(betabinom.sf(k - 1, n, a, b))


def read_csv(z: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with z.open(name) as fh:
        return list(csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8")))


def f(x: float, nd: int = 6) -> float:
    return round(float(x), nd)


def build(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        e1 = read_csv(z, "exp1_correlated_ensemble.csv")
        e2 = read_csv(z, "exp2_metareasoning.csv")
        e3 = read_csv(z, "exp3_temporal_retrieval.csv")
        members = sorted(names)

    n_trials = REPRO["trials"]["exp1_per_point"]
    se = math.sqrt(P_AGENT * (1 - P_AGENT) / n_trials)

    exp1 = []
    worst_z = 0.0
    worst_cell = None
    for r in e1:
        rho = float(r["rho"])
        n = int(r["N"])
        acc = float(r["majority_accuracy"])
        neff = float(r["N_eff"])
        bb = majority_beta_binom(n, rho)
        neff_theory = n if rho == 0 else n / (1 + (n - 1) * rho)
        z = (acc - bb) / se
        if n >= 3 and abs(z) > abs(worst_z):
            worst_z, worst_cell = z, f"{rho}|{n}"
        key = f"{rho:g}|{n}"
        exp1.append({
            "rho": rho, "N": n,
            "N_eff_csv": f(neff, 4), "N_eff_theory": f(neff_theory, 4),
            "accuracy_csv": f(acc), "accuracy_betabinom": f(bb),
            "delta_pp": f((acc - bb) * 100, 3), "z": f(z, 2),
            "pasted_md": PASTED_MD["cells"].get(key),
        })

    # the cells Pasted markdown.md reports but exp1 does not contain
    csv_keys = {f"{float(r['rho']):g}|{int(r['N'])}" for r in e1}
    se30k = math.sqrt(P_AGENT * (1 - P_AGENT) / PASTED_MD["claimed_trials"])
    pasted = []
    for key, val in sorted(PASTED_MD["cells"].items(), key=lambda kv: (float(kv[0].split("|")[0]), int(kv[0].split("|")[1]))):
        rho_s, n_s = key.split("|")
        rho, n = float(rho_s), int(n_s)
        bb = majority_beta_binom(n, rho)
        pasted.append({
            "rho": rho, "N": n, "accuracy_claimed": val, "accuracy_betabinom": f(bb),
            "delta_pp": f((val - bb) * 100, 3),
            "z_at_claimed_trials": f((val - bb) / se30k, 2),
            "in_exp1": key in csv_keys,
        })

    exp2 = [{
        "budget": int(r["budget_cap"]), "policy": r["policy"],
        "regret": f(float(r["mean_regret"]), 4),
        "samples": f(float(r["mean_samples"]), 3),
        "net_utility": f(float(r["mean_net_utility"]), 4),
    } for r in e2]

    adaptive = [r for r in exp2 if r["policy"] == "adaptive"]
    fixed = [r for r in exp2 if r["policy"] == "fixed_equal"]
    exp2_notes = {
        "adaptive_samples_saturate_at": max(r["samples"] for r in adaptive if r["budget"] >= 40),
        "fixed_regret_keeps_improving_to": min(r["regret"] for r in fixed),
        "adaptive_regret_plateaus_at": min(r["regret"] for r in adaptive if r["budget"] >= 40),
        "fixed_net_utility_peak_budget": max(fixed, key=lambda r: r["net_utility"])["budget"],
        "fixed_net_utility_at_80": next(r["net_utility"] for r in fixed if r["budget"] == 80),
        "adaptive_net_utility_at_80": next(r["net_utility"] for r in adaptive if r["budget"] == 80),
    }

    exp3 = [{
        "semantic_noise": float(r["semantic_noise"]),
        "flat_retrieval": float(r["flat_retrieval_accuracy"]),
        "temporal_projection": float(r["temporal_projection_accuracy"]),
    } for r in e3]
    exp3_notes = {
        "temporal_projection_is_constant": len({r["temporal_projection"] for r in exp3}) == 1,
        "temporal_projection_value": exp3[0]["temporal_projection"] if exp3 else None,
        "flat_retrieval_range": [min(r["flat_retrieval"] for r in exp3), max(r["flat_retrieval"] for r in exp3)],
        "queries_per_level": REPRO["trials"]["exp3_per_level"],
    }

    return {
        "_generated": str(date.today()),
        "_generator": "viz/scripts/derive_experiments.py",
        "_source_zip": str(zip_path.relative_to(REPO)),
        "_zip_members": members,
        "_note": "The zip is untracked (the corpus whitelist excludes .zip), so this derived JSON is the only git-traced copy of the D line's measured data. Re-run `pnpm derive` after any change to the bundle.",
        "repro": REPRO,
        "p_agent": P_AGENT,
        "exp1": {
            "rows": exp1,
            "se_at_reported_trials_pp": f(se * 100, 4),
            "worst_abs_z_over_N_ge_3": f(abs(worst_z), 2),
            "worst_cell": worst_cell,
            "verdict": "consistent with the exchangeable beta-binomial",
            "pasted_md": {
                "rows": pasted,
                "se_at_claimed_trials_pp": f(se30k * 100, 4),
                "rho_values_absent_from_exp1": sorted({r["rho"] for r in pasted if not r["in_exp1"]}),
                "verdict": "not compatible with the same model at the claimed trial count",
            },
        },
        "exp2": {"rows": exp2, "notes": exp2_notes},
        "exp3": {"rows": exp3, "notes": exp3_notes},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    if not a.zip.exists():
        raise SystemExit(f"bundle not found: {a.zip}")
    data = build(a.zip)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    e1 = data["exp1"]
    print(f"wrote {a.out}  ({a.out.stat().st_size} bytes)")
    print(f"  exp1 rows={len(e1['rows'])}  SE={e1['se_at_reported_trials_pp']} pp  worst |z| (N>=3)={e1['worst_abs_z_over_N_ge_3']} at {e1['worst_cell']}")
    pm = e1["pasted_md"]
    print(f"  pasted_md rows={len(pm['rows'])}  SE={pm['se_at_claimed_trials_pp']} pp  rho absent from exp1={pm['rho_values_absent_from_exp1']}")
    print(f"  exp2 {data['exp2']['notes']}")
    print(f"  exp3 {data['exp3']['notes']}")


if __name__ == "__main__":
    main()
