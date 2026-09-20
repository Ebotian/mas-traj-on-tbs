"""Measure KAPSO's tie-break in the REVERSE proposal order.

The A0.2 `tie_break` scenario proposes `c01_good_hex` first, and in that order
KAPSO's `max()`-over-`node_history` rule and the frozen A0-wide byte-wise rule
(smallest `candidate_id` by UTF-8) coincide -- so that scenario cannot tell the
two rules apart. This probe proposes `c03_mirror` first (both candidates score
bit-identically, 2.4519205208433132) and reads the runtime's own
`get_best_experiment()` / `get_deliverable_experiment()` and the parent the
runtime actually chose for the next round.

Everything except the proposal order is the adapter's A0.2 machinery
(`a02._runtime`, `a02._run_round`, `a02._decisions`); this file only pushes the
candidates in the opposite order.

Run:

    .venv/bin/python runs/tie-order-probe/probe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from a0_adapter import a02  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig,
    e_star_identity,
    load_candidate_set,
    load_eid_star,
)

PLAN = ("c03_mirror", "c01_good_hex", "c14_near_zero")


def main() -> int:
    config = AdapterConfig.load()
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    runtime = a02._runtime(config, eid, candidates, HERE, "reversed_tie")
    plan = runtime.seams["plan"]
    for candidate_id in PLAN:
        plan.push(candidate_id)

    canonical = eid.canonical_theta
    theta_dict = {"seed": canonical["seed"], "fidelity": canonical["fidelity"],
                  "fraction": canonical["fraction"]}
    a02._theta(runtime, theta_dict, "full", 1.0, e_star_identity(config))
    for _ in range(3):
        a02._run_round(runtime, a02._full_grant())

    decisions = a02._decisions(runtime)
    strategy = runtime.strategy
    third = strategy.node_history[2]
    parent_node = strategy.node_history[third.parent_node_id]
    observed = {
        "plan_order": list(PLAN),
        "tie_pair": {"c01_good_hex": 2.4519205208433132,
                     "c03_mirror": 2.4519205208433132},
        "byte_wise_smallest_candidate_id": sorted(["c01_good_hex", "c03_mirror"])[0],
        "node_history": decisions["node_history"],
        "best_node_id": decisions["best_node_id"],
        "best_candidate_id": decisions["best_candidate_id"],
        "deliverable_node_id": decisions["deliverable_node_id"],
        "deliverable_candidate_id": decisions["deliverable_candidate_id"],
        "next_round_parent_node_id": third.parent_node_id,
        "next_round_parent_candidate_id": a02._candidate_of(runtime, parent_node),
        "rule": "KAPSO: max() over node_history -> the FIRST maximal element; "
                "frozen A0-wide rule: smallest candidate_id by UTF-8 bytes",
    }
    observed["diverges_from_frozen_tie_break"] = (
        observed["best_candidate_id"] != observed["byte_wise_smallest_candidate_id"]
    )
    (HERE / "outcome.json").write_text(
        json.dumps(observed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(observed, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
