#!/usr/bin/env python3
"""L1: baseline b_i and one-exchange p_i on the size-lever sample, via E*.

Uses the frozen candidates' byte-identical mode-normalised mirrors in
`frozen_mirror/` (see DEVIATIONS.md D-RD-1 and gen/make_frozen_mirror.py) for
b_i and for p_i (the pinned NetworkX one_exchange).  The mirror's
`candidate_source_sha256` is asserted equal to the frozen one, so these Outcomes
are directly comparable to the gate's.  E* is the authority; nothing here counts
a cut itself.

    python3 gen/l1_eval.py [--force]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
E_STAR = TASK / "e_star.py"
MANIFEST = REDESIGN / "instances" / "manifest.json"
CANDIDATES = {"baseline": REDESIGN / "frozen_mirror" / "baseline",
              "pc": REDESIGN / "frozen_mirror" / "pc",
              # efficient, verified-equivalent transliteration of the pinned one_exchange
              # (see candidates/exchange_opt and gen/run_l2.py's equality assertion)
              "pc_fast": REDESIGN / "candidates" / "exchange_opt"}
SEED = 1337
#: the frozen gate theta for the pinned candidates; the efficient transliteration gets a
#: generous budget so p is the *converged* local optimum (a larger p only lowers rho, so this
#: is the conservative direction).  Every Outcome records its own theta.timeout_s.
TIMEOUTS = {"baseline": 30.0, "pc": 30.0, "pc_fast": 900.0}


def l1_graphs():
    man = json.loads(MANIFEST.read_text())
    root = MANIFEST.parent
    out = []
    for e in man["graphs"]:
        out.append({"graph_id": e["graph_id"], "family": e["family"],
                    "stratum": e["stratum"], "n": e["n"], "edges": e["edges"],
                    "path": str(root / e["path"]), "graph_sha256": e["graph_sha256"]})
    out.sort(key=lambda g: (g["stratum"], g["n"], g["graph_id"]))
    return out


def evaluate(kind, graph, force):
    path = REDESIGN / "out" / "l1_outcomes" / kind / f"{graph['graph_id']}.outcome.json"
    if path.is_file() and not force:
        return json.loads(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(E_STAR), "evaluate",
               "--candidate", str(CANDIDATES[kind]), "--graph", graph["path"],
               "--seed", str(SEED), "--timeout", str(TIMEOUTS[kind]), "--out", str(path),
               "--state-dir", str(REDESIGN / "out" / "e-star-state" / f"l1-{kind}")]
    proc = subprocess.run(command, capture_output=True, text=True)
    if not path.is_file():
        raise SystemExit(f"E* wrote no Outcome for {kind} {graph['graph_id']}: "
                         f"{proc.stdout}\n{proc.stderr}")
    return json.loads(path.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    graphs = l1_graphs()
    rows = []
    for g in graphs:
        b = evaluate("baseline", g, args.force)
        p_pin = evaluate("pc", g, args.force)
        p_fast = evaluate("pc_fast", g, args.force)
        if b["status"] != "ok" or p_fast["status"] != "ok":
            raise SystemExit(f"non-ok E* outcome on {g['graph_id']}")
        pin_ok = p_pin["status"] == "ok"
        if pin_ok and int(p_pin["cut_edges"]) != int(p_fast["cut_edges"]):
            raise SystemExit(f"pc_fast != pinned pc on {g['graph_id']}: "
                             f"{p_fast['cut_edges']} vs {p_pin['cut_edges']}")
        p = int(p_fast["cut_edges"])
        rows.append({"graph_id": g["graph_id"], "family": g["family"],
                     "stratum": g["stratum"], "n": g["n"], "edges": g["edges"],
                     "graph_sha256": g["graph_sha256"],
                     "b": int(b["cut_edges"]), "p": p,
                     "p_source": "pc_fast (verified-equivalent transliteration)",
                     "pinned_pc_status": p_pin["status"],
                     "pinned_pc_cut_edges": p_pin["cut_edges"],
                     "pinned_pc_wall_ms": p_pin["interpreted"]["wall_ms"],
                     "p_fast_wall_ms": p_fast["interpreted"]["wall_ms"],
                     "pinned_pc_agrees": (int(p_pin["cut_edges"]) == p if pin_ok else None)})
        print(f"{g['graph_id']:24s} n={g['n']:5d} |E|={g['edges']:6d} "
              f"b={rows[-1]['b']:6d} p={p:7d}  pinned_pc={p_pin['status']:8s} "
              f"pin_wall={p_pin['interpreted']['wall_ms']} fast_wall={rows[-1]['p_fast_wall_ms']}")
    out = REDESIGN / "out" / "l1_values.json"
    out.write_text(json.dumps({"schema": "a0.maxcut.redesign.l1_values/v1",
                               "seed": SEED, "timeouts": TIMEOUTS,
                               "p_note": "p is the value of the pinned one_exchange, obtained with "
                                         "the efficient equivalent transliteration candidates/"
                                         "exchange_opt where the pin itself exceeds tau (see "
                                         "DEVIATIONS.md D-RD-2). Where the pin completed, the two "
                                         "agree exactly.",
                               "rows": rows},
                              sort_keys=True, indent=2) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
