#!/usr/bin/env python3
"""Derive tau the way INTERFACE.md section 7 says to, instead of guessing it.

    tau = min(30 s, max(10 s, 10 x p99))

Section 9 gives the calibration set exactly one job: measure per-arm resource
rates, including "the candidate latency distribution (giving p99 -> tau)".  No
p99 was ever published for this task, so `gate_config.theta.timeout_s` carried
the band maximum, 30 s, and `DEVIATIONS.md` D-GATE-4 recorded that as a guess.
This script measures the distribution and computes the compliant tau.

It measures latency only.  **No calibration graph takes part in any selection**
(section 9): nothing here informs which candidates are better, only how long
they take.

What counts as "the candidate latency distribution".  The candidates the task
will actually run: the frozen baseline `b_i`, the contract's positive control, its
truncations, and the `ok` members of `C*(T1)` that a conformance run executes.
`C*(T1)`'s deliberately-sleeping `timeout` candidate is excluded by
construction -- it exists to *exceed* tau, so including it would make the
percentile meaningless.

**Which control, 2026-09-23.**  The map below was written when the contract's
control was the unbounded `positive_control/pc/`, so its key `"PC_i"` names that
artifact -- the control that is superseded now and labelled `PC_∞`.  The adopted
control is the variant at `variants/pc_exchange_k10/`, keyed `"PC_k10"`
(`PC-REVISION.md`).  That key is part of the stored output
(`tau_calibration.json`, `per_candidate[].candidate`), so it is kept: **read
`"PC_i"` here as `PC_∞`.**  The derivation does not depend on the label -- the
stored run gives pooled `p99 = 146 ms`, so `10 x p99 = 1.46 s` and the 10 s floor
binds.

Timings come from E* itself (`--emit-resources`), i.e. the same numbers the
harness records in `resources.runs[].wall_ms`, and the 99th percentile is the
nearest-rank order statistic of the pooled sample with the definition stated in
the output (`ceil(0.99 n)`-th smallest, 1-based).

    python3 gates/tau_calibration.py                     # measure + print
    python3 gates/tau_calibration.py --out gates/tau_calibration.json
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
E_STAR = MAXCUT / "e_star.py"
SUITE = MAXCUT / "suite"
POSITIVE_CONTROL = MAXCUT / "positive_control"

CANDIDATES = {
    "b_i": POSITIVE_CONTROL / "baseline",
    "PC_i": POSITIVE_CONTROL / "pc",
    "PC_k25": POSITIVE_CONTROL / "variants" / "pc_exchange_k25",
    "PC_k10": POSITIVE_CONTROL / "variants" / "pc_exchange_k10",
    "PC_k05": POSITIVE_CONTROL / "variants" / "pc_exchange_k05",
    "PC_k02": POSITIVE_CONTROL / "variants" / "pc_exchange_k02",
    "PC_k01": POSITIVE_CONTROL / "variants" / "pc_exchange_k01",
    "C*_c01": MAXCUT / "candidates" / "c01_ok_high_pc",
    "C*_c02": MAXCUT / "candidates" / "c02_ok_low_baseline",
    "C*_c03": MAXCUT / "candidates" / "c03_ok_zero_all_one_side",
    "C*_c04": MAXCUT / "candidates" / "c04_tie_a_pc_optimum",
    "C*_c05": MAXCUT / "candidates" / "c05_tie_b_pc_complement",
    "C*_c18": MAXCUT / "candidates" / "c18_ok_inflation_attempt",
    "C*_c20": MAXCUT / "candidates" / "c20_env_probe",
    "C*_c21": MAXCUT / "candidates" / "c21_ok_parity_probe",
}


def calibration_graphs():
    manifest = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
    return [SUITE / e["path"] for e in manifest["graphs"] if e.get("role") == "calibration"]


def percentile(values, fraction):
    """Nearest rank: the ceil(fraction * n)-th smallest, 1-based (n >= 1)."""
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(fraction * len(ordered))))
    return ordered[rank - 1]


def measure(candidates, graphs, seed, timeout_s, scratch):
    samples = {}
    for label, directory in candidates.items():
        if not (directory / "solution.py").is_file():
            samples[label] = {"missing": True, "path": str(directory), "wall_ms": []}
            continue
        walls, statuses = [], []
        for graph in graphs:
            out = scratch / f"{label}__{graph.stem}.outcome.json"
            resources = scratch / f"{label}__{graph.stem}.resources.json"
            subprocess.run(
                [sys.executable, str(E_STAR), "evaluate",
                 "--candidate", str(directory), "--graph", str(graph),
                 "--seed", str(seed), "--timeout", str(timeout_s),
                 "--out", str(out), "--emit-resources", str(resources),
                 "--state-dir", str(scratch / "state")],
                capture_output=True, text=True,
            )
            if out.is_file():
                statuses.append(json.loads(out.read_text(encoding="utf-8"))["status"])
            if resources.is_file():
                for run in json.loads(resources.read_text(encoding="utf-8")).get("runs", []):
                    if run.get("wall_ms") is not None:
                        walls.append(float(run["wall_ms"]))
        samples[label] = {
            "candidate_dir": str(directory),
            "graphs": len(graphs),
            "invocations": len(walls),
            "statuses": sorted(set(statuses)),
            "wall_ms": walls,
        }
    return samples


def summarise(walls):
    if not walls:
        return None
    return {
        "n": len(walls),
        "min": min(walls),
        "p50": percentile(walls, 0.50),
        "p95": percentile(walls, 0.95),
        "p99": percentile(walls, 0.99),
        "max": max(walls),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=None)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="tau used while *measuring*; it does not change wall times here")
    parser.add_argument("--candidates", nargs="*", default=None)
    args = parser.parse_args()

    selected = {k: v for k, v in CANDIDATES.items()
                if args.candidates is None or k in args.candidates}
    graphs = calibration_graphs()
    scratch = Path(tempfile.mkdtemp(prefix="tau-calibration-"))
    try:
        samples = measure(selected, graphs, args.seed, args.timeout, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    pooled = [w for s in samples.values() for w in s.get("wall_ms", [])]
    rows = []
    for label, sample in samples.items():
        summary = summarise(sample.get("wall_ms", []))
        rows.append({"candidate": label, **{k: v for k, v in sample.items() if k != "wall_ms"},
                     "summary_ms": summary})

    pooled_summary = summarise(pooled)
    if pooled_summary is None:
        raise SystemExit("no wall times measured")
    p99 = pooled_summary["p99"]
    ten_p99_ms = 10.0 * p99
    tau = min(30.0, max(10.0, ten_p99_ms / 1000.0))

    document = {
        "schema": "a0.maxcut.tau_calibration/v1",
        "authority": "INTERFACE.md section 7 (tau = min(30s, max(10s, 10 x p99))) and section 9",
        "graph_set": "calibration",
        "graphs": len(graphs),
        "selection_caveat": ("the calibration set is used for latency only; no calibration graph "
                             "informs any choice among candidates (INTERFACE.md section 9)"),
        "p99_definition": "nearest rank: the ceil(0.99 * n)-th smallest value of the pooled sample",
        "measurement_seed": args.seed,
        "measurement_tau_s": args.timeout,
        "per_candidate": rows,
        "pooled": pooled_summary,
        "ten_times_p99_ms": ten_p99_ms,
        "tau_s": tau,
        "tau_band": {"min": 10.0, "max": 30.0},
        "binding_clause": ("the 10 s floor" if tau == 10.0 else
                           ("the 30 s ceiling" if tau == 30.0 else "10 x p99")),
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out = Path(args.out) if args.out else HERE / "tau_calibration.json"
    out.write_text(text, encoding="utf-8")

    print("| candidate | invocations | p50 ms | p95 ms | p99 ms | max ms |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        s = row["summary_ms"]
        if s is None:
            print(f"| {row['candidate']} | — | — | — | — | — |")
        else:
            print(f"| {row['candidate']} | {s['n']} | {s['p50']:.1f} | {s['p95']:.1f} | "
                  f"{s['p99']:.1f} | {s['max']:.1f} |")
    p = pooled_summary
    print(f"| **pooled** | {p['n']} | {p['p50']:.1f} | {p['p95']:.1f} | {p['p99']:.1f} | {p['max']:.1f} |")
    print()
    print(f"pooled p99 = {p99:.1f} ms; 10 x p99 = {ten_p99_ms:.1f} ms; "
          f"tau = min(30, max(10, {ten_p99_ms / 1000.0:.2f})) = **{tau} s** "
          f"(binding clause: {document['binding_clause']})")
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
