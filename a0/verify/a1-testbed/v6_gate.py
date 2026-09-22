#!/usr/bin/env python3
"""Adversarial re-derivation of the admissibility-gate claims (assignment item 6).

Recomputes Δ_i, ρ_i, the medians and the family counts from the stored E* values
in gates/values/*.json and references/targets.json, with Fraction only, and
compares against the frozen verdicts.  It also re-reads the pre-registered
thresholds from the contract text and checks that gate_config.json was not
softened against them.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import statistics
import sys
from fractions import Fraction

REPO = pathlib.Path(__file__).resolve().parents[3]
MX = REPO / "a0/tasks/maxcut"
GATES = MX / "gates"

problems: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        problems.append(msg)


def payload(value: Fraction) -> dict:
    return {"numerator": value.numerator, "denominator": value.denominator}


def median(values: list[Fraction]) -> Fraction:
    """gate_config.json's definition: exact midpoint of the two central order
    statistics for an even count, the central value for an odd count."""
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def load_values(name: str) -> dict[str, dict]:
    doc = json.loads((GATES / "values" / name).read_bytes())
    return {o["graph_id"]: o for o in doc["outcomes"]}


def main() -> int:
    targets = json.loads((MX / "references/targets.json").read_bytes())["graphs"]
    baseline = load_values("dev.baseline.json")
    pc = load_values("dev.positive-control.json")
    verdict = json.loads((GATES / "verdict.dev.json").read_bytes())
    config = json.loads((GATES / "gate_config.json").read_bytes())

    print("== A. threshold provenance: is gate_config.json the contract's numbers? ==")
    cfg_delta = config["gates"]["delta_gate"]
    cfg_rho = config["gates"]["rho_gate"]
    check(Fraction(cfg_delta["overall_mean_min"]["numerator"], cfg_delta["overall_mean_min"]["denominator"]) == Fraction(3, 100),
          "Δ overall threshold == 0.03")
    check(Fraction(cfg_delta["per_family_mean_min"]["numerator"], cfg_delta["per_family_mean_min"]["denominator"]) == Fraction(2, 100),
          "Δ per-family threshold == 0.02")
    check(cfg_delta["families_required"] == 3 and cfg_delta["families_total"] == 4, "Δ needs 3 of 4 families")
    check(Fraction(cfg_rho["global_median_min"]["numerator"], cfg_rho["global_median_min"]["denominator"]) == Fraction(3, 10),
          "ρ global-median threshold == 0.30")
    check(Fraction(cfg_rho["per_family_median_min"]["numerator"], cfg_rho["per_family_median_min"]["denominator"]) == Fraction(3, 10),
          "ρ per-family threshold == 0.30")
    check(cfg_rho["families_required"] == 3 and cfg_rho["families_total"] == 4, "ρ needs 3 of 4 families")
    config_sha = hashlib.sha256((GATES / "gate_config.json").read_bytes()).hexdigest()
    check(config_sha == verdict["gate_config_sha256"],
          f"verdict stamps the gate_config.json sha256 {config_sha[:16]}… (a later edit is visible)")
    # the frozen scale must also be documented upstream, not invented here
    audit = (REPO / "a0/A1-CONTRACT-AUDIT.md").read_text()
    check("`Δ_PC ≥ 0.03`" in audit, "the contract audit states Δ_PC ≥ 0.03")
    check("`Δ ≥ 0.02`" in audit, "the contract audit states the per-family Δ ≥ 0.02 variant")
    interim = (REPO / "a0/A1-INTERIM.md").read_text()
    check("中位数 ≥ 0.30 且 ≥3/4 族 ≥0.30" in interim,
          "the pre-registration (A1-INTERIM.md) states the ρ rule as median ≥ 0.30 and ≥3/4 families ≥ 0.30")
    check("（0.30 / 0.03 / 0.02）一个字没动" in interim,
          "the same document records that the frozen thresholds (0.30/0.03/0.02) were not moved")

    print("\n== B. Δ_i and ρ_i recomputed for every dev graph, exact rationals ==")
    rows = {r["graph_id"]: r for r in verdict["rows"]}
    recomputed: dict[str, dict] = {}
    for gid in sorted(rows):
        b = baseline[gid]["cut_edges"]
        p = pc[gid]["cut_edges"]
        edges = baseline[gid]["edges_total"]
        tgt = targets[gid]
        certified = tgt["OPT"] is not None
        t = tgt["OPT"] if certified else tgt["R"]
        delta = Fraction(p - b, edges)
        rho = Fraction(t - p, t - b)
        head = Fraction(t - b, t)
        recomputed[gid] = {"b": b, "p": p, "T": t, "edges": edges, "delta": delta, "rho": rho,
                           "head": head, "family": baseline[gid]["graph_family"],
                           "stratum": None, "certified": certified}
        row = rows[gid]
        closed = Fraction(p - b, t - b)
        same = (row["b"] == b and row["p"] == p and row["T"] == t and row["edges"] == edges
                and Fraction(row["delta"]["numerator"], row["delta"]["denominator"]) == delta
                and Fraction(row["rho"]["numerator"], row["rho"]["denominator"]) == rho
                and Fraction(row["headroom_closed"]["numerator"], row["headroom_closed"]["denominator"]) == closed
                and Fraction(row["baseline_headroom"]["numerator"], row["baseline_headroom"]["denominator"]) == head)
        if not same:
            check(False, f"{gid}: verdict row disagrees with b/p/T/edges recomputation")
    check(True, f"all 24 dev rows: b_i, p_i, T_i, |E_i|, Δ_i, ρ_i agree with the stored verdict rows")

    for gid in ("G_dev_0001", "G_dev_0007", "G_dev_0019"):
        r = recomputed[gid]
        print(f"    {gid}: b={r['b']} p={r['p']} T={r['T']} |E|={r['edges']} "
              f"Δ={r['delta'].numerator}/{r['delta'].denominator}={float(r['delta']):.6f} "
              f"ρ={r['rho'].numerator}/{r['rho'].denominator}={float(r['rho']):.6f} (T from "
              f"{'OPT' if r['certified'] else 'R'})")

    print("\n== C. the aggregates in verdict.dev.json ==")
    deltas = [recomputed[g]["delta"] for g in recomputed]
    overall = sum(deltas, Fraction(0)) / len(deltas)
    stored_overall = Fraction(verdict["delta_gate"]["overall_mean"]["numerator"],
                              verdict["delta_gate"]["overall_mean"]["denominator"])
    check(overall == stored_overall,
          f"Δ overall mean (unweighted) {overall.numerator}/{overall.denominator} == stored ({float(overall):.6f})")
    fams = {}
    for gid, r in recomputed.items():
        fams.setdefault(r["family"], []).append(r)
    fam_means = {f: sum((r["delta"] for r in v), Fraction(0)) / len(v) for f, v in fams.items()}
    for f, m in sorted(fam_means.items()):
        stored = Fraction(verdict["delta_gate"]["per_family"][f]["mean"]["numerator"],
                          verdict["delta_gate"]["per_family"][f]["mean"]["denominator"])
        check(m == stored, f"Δ family {f}: {m.numerator}/{m.denominator} == stored ({float(m):.6f})")
    fam_pass_d = sorted(f for f, m in fam_means.items() if m >= Fraction(2, 100))
    check(fam_pass_d == sorted(verdict["delta_gate"]["families_passing"]),
          f"Δ families passing (≥0.02): {fam_pass_d}")
    check(overall >= Fraction(3, 100) and len(fam_pass_d) >= 3, "Δ gate PASS on recomputation")

    rhos = [recomputed[g]["rho"] for g in recomputed]
    med = median(rhos)
    stored_med = Fraction(verdict["rho_gate"]["global_median"]["numerator"],
                          verdict["rho_gate"]["global_median"]["denominator"])
    check(med == stored_med, f"ρ global median {med.numerator}/{med.denominator} == stored ({float(med):.6f})")
    fam_med = {f: median([r["rho"] for r in v]) for f, v in fams.items()}
    for f, m in sorted(fam_med.items()):
        stored = Fraction(verdict["rho_gate"]["per_family"][f]["median"]["numerator"],
                          verdict["rho_gate"]["per_family"][f]["median"]["denominator"])
        check(m == stored, f"ρ family {f}: {m.numerator}/{m.denominator} == stored ({float(m):.6f})")
    fam_pass_r = sorted(f for f, m in fam_med.items() if m >= Fraction(3, 10))
    check(fam_pass_r == sorted(verdict["rho_gate"]["families_passing"]),
          f"ρ families passing (≥0.30): {fam_pass_r or 'none'}")
    check(not (med >= Fraction(3, 10) and len(fam_pass_r) >= 3), "ρ gate FAILS on recomputation")
    check(verdict["verdict"] == "NOT_ADMISSIBLE" and verdict["rho_gate"]["global_pass"] is False,
          f"frozen verdict is {verdict['verdict']}")

    print("\n== D. the saturation veto ==")
    heads = [recomputed[g]["head"] for g in recomputed]
    check(median(heads) == Fraction(verdict["saturation_no_go"]["baseline_headroom_median"]["numerator"],
                                    verdict["saturation_no_go"]["baseline_headroom_median"]["denominator"]),
          f"baseline-headroom median {float(median(heads)):.6f} == stored")
    check(min(heads) == Fraction(verdict["saturation_no_go"]["baseline_headroom_min"]["numerator"],
                                 verdict["saturation_no_go"]["baseline_headroom_min"]["denominator"]),
          f"baseline-headroom min {float(min(heads)):.6f} == stored")
    check(verdict["saturation_no_go"]["no_go"] is False, "saturation veto not triggered")

    print("\n== E. the revision proposal's table vs the stored k-variants ==")
    tiers = {"one_exchange": "verdict.dev.json", "k25": "verdict.dev.pc_exchange_k25.json",
             "k10": "verdict.dev.pc_exchange_k10.json", "k05": "verdict.dev.pc_exchange_k05.json",
             "k02": "verdict.dev.pc_exchange_k02.json", "k01": "verdict.dev.pc_exchange_k01.json"}
    table = {"one_exchange": (0.247943, 0.158820, "NOT_ADMISSIBLE"),
             "k25": (0.204898, 0.325903, "ADMISSIBLE"),
             "k10": (0.116585, 0.615639, "ADMISSIBLE"),
             "k05": (0.069658, 0.775149, "ADMISSIBLE"),
             "k02": (0.032882, 0.895644, "ADMISSIBLE"),
             "k01": (0.018221, 0.940123, "NOT_ADMISSIBLE")}
    for tag, fname in tiers.items():
        doc = json.loads((GATES / fname).read_bytes())
        d = float(Fraction(doc["delta_gate"]["overall_mean"]["numerator"],
                           doc["delta_gate"]["overall_mean"]["denominator"]))
        r = float(Fraction(doc["rho_gate"]["global_median"]["numerator"],
                           doc["rho_gate"]["global_median"]["denominator"]))
        want_d, want_r, want_v = table[tag]
        match = abs(d - want_d) < 5e-7 and abs(r - want_r) < 5e-7 and doc["verdict"] == want_v
        check(match, f"{tag}: stored Δ={d:.6f} ρ={r:.6f} verdict={doc['verdict']} "
                     f"(proposal says {want_d} / {want_r} / {want_v})")
        if tag != "one_exchange":
            check(doc["gate_config_sha256"] == config_sha,
                  f"{tag}: same gate_config sha256 as the frozen verdict (thresholds not moved)")

    print("\n== F. the eval set is diagnostic, not the gate ==")
    ev = json.loads((GATES / "verdict.eval.json").read_bytes())
    check(ev["role_of_set"] == "diagnostic" and verdict["role_of_set"] == "gate",
          f"dev is the gate ({verdict['role_of_set']}), eval is {ev['role_of_set']}")
    check(ev["verdict"] == "NOT_ADMISSIBLE", f"eval verdict also {ev['verdict']}")

    print("\n== G. the proposal's eval table (§3.2) vs the stored eval variants ==")
    eval_table = {"k25": (0.202023, 0.301163, "NOT_ADMISSIBLE", 2),
                  "k10": (0.116427, 0.600847, "ADMISSIBLE", 4),
                  "k05": (0.070200, 0.762308, "ADMISSIBLE", 4),
                  "k02": (0.033074, 0.894196, "ADMISSIBLE", 4),
                  "k01": (0.017983, 0.942883, "NOT_ADMISSIBLE", 4)}
    for tag, (wd, wr, wv, wfam) in eval_table.items():
        doc = json.loads((GATES / f"verdict.eval.pc_exchange_{tag}.json").read_bytes())
        d = float(Fraction(doc["delta_gate"]["overall_mean"]["numerator"],
                           doc["delta_gate"]["overall_mean"]["denominator"]))
        r = float(Fraction(doc["rho_gate"]["global_median"]["numerator"],
                           doc["rho_gate"]["global_median"]["denominator"]))
        fams_ok = len(doc["rho_gate"]["families_passing"])
        delta_fams = len(doc["delta_gate"]["families_passing"])
        want_delta_fams = 1 if tag == "k01" else 4
        check(abs(d - wd) < 5e-7 and abs(r - wr) < 5e-7 and doc["verdict"] == wv and fams_ok == wfam
              and delta_fams == want_delta_fams,
              f"eval {tag}: Δ={d:.6f} ρ={r:.6f} Δ-families={delta_fams}/4 ρ-families={fams_ok}/4 "
              f"verdict={doc['verdict']} (proposal §3.2 says Δ-families {want_delta_fams}/4, "
              f"ρ-families {wfam}/4, {wv})")

    print(f"\nPROBLEMS: {len(problems)}")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
