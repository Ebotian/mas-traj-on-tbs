#!/usr/bin/env python3
"""Diagnostic: is the gate's outcome an artifact of the single frozen seed?

The gate is pre-registered at one seed (`gate_config.theta.seed`).  That is the
right way to *decide* it — one pre-registered number, not the best of several —
but it is the wrong way to *explain* a failure, because a failure at one seed
could be luck.  This script re-runs the same measurement at additional seeds and
prints Δ and ρ side by side.

It decides nothing.  It exists so that a reviewer can see whether the running
control's verdict is structural or a single-seed accident, and the extra runs are
written to `outcomes/<set>/s<seed>/...` so they never overwrite the
pre-registered ones.

**Which control, 2026-09-23.**  The control is read through
`gate_runner.DEFAULT_PC`, so this script measures the *running* control: the
adopted bounded `PC_i` (`positive_control/variants/pc_exchange_k10/`) since
2026-09-23, and the superseded unbounded `PC_∞` (`positive_control/pc/`) before
that.  The verdict to compare its rows against is
`verdict.<set>.pc_exchange_k10.json`; the un-suffixed `verdict.<set>.json` is the
*superseded* control's verdict and still reads `NOT_ADMISSIBLE`.  The stored
`seed_sensitivity.dev.json` is the earlier run — its rows are `PC_∞` rows — and
its embedded `note` still *starts* by pointing a reader at `verdict.<set>.json`; on
2026-09-23 a dated label note was appended to that string in place, with the `rows`
left unchanged.  `DEVIATIONS.md` carries the same reading.

    python3 gates/seed_sensitivity.py --set dev --seeds 1337 0 1 2 3
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gate_runner as G  # noqa: E402  (reuses its gates verbatim, decides nothing new)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", dest="graph_set", default="dev")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1337, 0, 1, 2, 3])
    parser.add_argument("--targets", default=str(G.DEFAULT_TARGETS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = json.loads(G.CONFIG.read_text(encoding="utf-8"))
    timeout_s = float(config["theta"]["timeout_s"])
    frozen_seed = int(config["theta"]["seed"])
    targets = {}
    if Path(args.targets).is_file():
        document = json.loads(Path(args.targets).read_text(encoding="utf-8"))
        targets = document.get("graphs", document)

    rows = []
    for seed in args.seeds:
        graphs, outcomes = G.collect(args.graph_set, seed, timeout_s, args.force,
                                     tag=f"s{seed}")
        table = G.delta_rows(graphs, outcomes, targets)
        delta = G.delta_gate(table, config)
        rho = G.rho_gate(table, config)
        saturation = G.saturation_gate(table, config)
        rows.append({
            "seed": seed,
            "is_frozen_seed": seed == frozen_seed,
            "delta_overall_mean": delta["overall_mean"],
            "delta_overall_pass": delta["overall_pass"],
            "delta_families_passing": delta["families_passing"],
            "delta_verdict": delta["verdict"],
            "rho_median": rho.get("global_median"),
            "rho_families_passing": rho.get("families_passing"),
            "rho_verdict": rho["verdict"],
            "baseline_headroom_median": saturation.get("baseline_headroom_median"),
            "saturation_verdict": saturation["verdict"],
        })

    document = G.jsonify({
        "schema": "a0.maxcut.seed_sensitivity/v1",
        "diagnostic_only": True,
        "note": ("The pre-registered decision is the single frozen seed's verdict in "
                 "verdict.<set>.json; this table asks only whether that verdict moves "
                 "with the seed."),
        "graph_set": args.graph_set,
        "frozen_seed": frozen_seed,
        "targets_path": args.targets,
        "rows": rows,
    })
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out = Path(args.out) if args.out else HERE / f"seed_sensitivity.{args.graph_set}.json"
    out.write_text(text, encoding="utf-8")

    print(f"# seed sensitivity — set `{args.graph_set}` (diagnostic, decides nothing)")
    print()
    print("| seed | Δ mean | Δ verdict | families Δ pass | ρ median | ρ verdict | families ρ pass |")
    print("|---|---|---|---|---|---|---|")
    for row in document["rows"]:
        mark = " *(frozen)*" if row["is_frozen_seed"] else ""
        print(f"| {row['seed']}{mark} | {row['delta_overall_mean']['decimal']} | "
              f"{row['delta_verdict']} | {len(row['delta_families_passing'])}/4 | "
              f"{(row['rho_median'] or {}).get('decimal', 'n/a')} | {row['rho_verdict']} | "
              f"{len(row['rho_families_passing'])}/4 |")
    print()
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
