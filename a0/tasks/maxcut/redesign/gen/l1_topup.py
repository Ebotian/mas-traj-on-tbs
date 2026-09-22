#!/usr/bin/env python3
"""L1: the project's 4x top-up pass, on the large-n graphs.

`references/README.md` §3 gives the 18 graphs SCIP did not certify a 4x-budget
top-up (6 runs of 120 s from the three heuristics that reach R_i there, two
seeds): the purpose is to *test* the 30 s reference, not to raise it.  At large
n the same test matters more, because an uncertified `R_i` is only a lower bound
and the whole rho verdict then rests on how good that incumbent is.

The graphs with `n >= 512` get the top-up; at `n <= 256` the upper-bound bracket
is narrow enough that the incumbent already pins rho below the bar.

    python3 gen/l1_topup.py [--min-n 512]
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
MANIFEST = REDESIGN / "instances" / "manifest.json"
RUN_ENSEMBLE = TASK / "references" / "tools" / "run_ensemble.py"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min-n", type=int, default=512)
    ap.add_argument("--binary", default="/tmp/mcwork/MQLib/bin/MQLib")
    ap.add_argument("--jobs", type=int, default=9)
    ap.add_argument("--time-limit", type=float, default=120.0)
    args = ap.parse_args(argv)
    man = json.loads(MANIFEST.read_text())
    root = MANIFEST.parent
    graphs = [str(root / e["path"]) for e in man["graphs"] if e["n"] >= args.min_n]
    graphs.sort()
    print(f"top-up: {len(graphs)} graphs at n>=%d, 3 heuristics x 2 seeds x %gs"
          % (args.min_n, args.time_limit))
    cmd = [sys.executable, str(RUN_ENSEMBLE), "--binary", args.binary,
           "--graphs", *graphs,
           "--outdir", str(REDESIGN / "instances" / "logs_topup"),
           "--scratch", "/tmp/redesign-mcwork/inputs",
           "--jobs", str(args.jobs), "--time-limit", str(args.time_limit),
           "--heuristics", "BURER2002", "FESTA2002VNSPR", "LAGUNA2009HCE",
           "--seeds", "1337", "4242"]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
