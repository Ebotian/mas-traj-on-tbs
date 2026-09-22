#!/usr/bin/env python3
"""Prove that our `PC_i` *is* the pinned NetworkX ``one_exchange``.

The positive control is only usable as a positive control if the thing we froze
is the thing the contract names.  The contract names

    networkx.algorithms.approximation.one_exchange
        at commit b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b

and `pc/solution.py` executes a transliteration of it rather than importing it,
because INTERFACE.md §4 gives the candidate a private scratch directory and a
minimal environment and no site-packages guarantee.  A transliteration can
drift.  This script is how that objection is settled: **run both**, on the whole
frozen suite, and require the returned cut value *and* the returned partition to
be equal on every graph.

Four checks, all executed:

  C1  the pinned bytes we vendored are the pinned bytes
      (`pc/pinned/networkx_maxcut_b69beb2c.py` vs its frozen sha256).
  C2  the NetworkX that the reference interpreter actually imports has that
      same `maxcut.py` sha256 — i.e. the install is at the pin, and this is
      checked by content, not by `__version__`.
  C3  vendored `one_exchange` == that install's `one_exchange`, exactly
      (cut value and partition) on every graph given to `--graphs`.
  C4  the transliteration is a *function of (graph bytes, seed)* only: two
      in-process runs agree, and the value it returns equals the cut recomputed
      from the graph and the partition it wrote.

Usage (the reference interpreter must have NetworkX):

    python3 verify_pc_identity.py \
        --reference-python .venv-pin/bin/python \
        --report pc_identity_report.json
"""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PC_DIR = HERE / "pc"
SOLUTION = PC_DIR / "solution.py"
PINNED = PC_DIR / "pinned" / "networkx_maxcut_b69beb2c.py"
REFERENCE = HERE / "reference_one_exchange.py"

PINNED_COMMIT = "b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b"
PINNED_SHA256 = "793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb"


def load_pc():
    spec = importlib.util.spec_from_file_location("pc_solution", SOLUTION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite_graphs():
    manifest = json.loads((HERE.parent / "suite" / "manifest.json").read_text(encoding="utf-8"))
    root = HERE.parent / "suite"
    return [(entry["graph_id"], str(root / entry["path"]), entry.get("family")) for entry in manifest["graphs"]]


def extra_graphs():
    """A few graphs that are *not* the frozen suite, so C3 is not only a
    statement about 60 files one workstream produced."""
    import random

    out = []
    for n, p, seed in ((64, 0.05, 1), (64, 0.5, 2), (33, 0.3, 3), (128, 0.02, 4)):
        rng = random.Random(seed)
        edges = sorted({(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p})
        target = HERE / "tmp" / f"X_n{n}_p{int(p * 100)}_{seed}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical({
            "schema": "a0.maxcut.graph/v1",
            "graph_id": f"X_n{n}_p{int(p * 100)}_{seed}",
            "family": "ER",
            "n": n,
            "edges": [list(e) for e in edges],
            "generator": {"name": "verify_pc_identity", "version": "1.0.0",
                          "params": {"model": "gnp", "p": str(p)}, "seed": seed},
            "notes": "not part of the frozen suite; used only to widen C3",
        }) + "\n", encoding="utf-8")
        out.append((f"X_n{n}_p{int(p * 100)}_{seed}", str(target), "extra"))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reference-python", required=True,
                        help="interpreter that has the pinned NetworkX installed")
    parser.add_argument("--report", default=None)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--graphs", choices=["suite", "suite+extra"], default="suite+extra")
    args = parser.parse_args()

    module = load_pc()
    rows = []
    failures = []

    # ---- C1 -----------------------------------------------------------------
    pinned_sha = sha256_file(PINNED)
    c1_ok = pinned_sha == PINNED_SHA256
    if not c1_ok:
        failures.append(f"C1 vendored pinned file sha256 {pinned_sha} != {PINNED_SHA256}")

    # ---- C2 / C3 ------------------------------------------------------------
    graphs = suite_graphs()
    if args.graphs == "suite+extra":
        graphs = graphs + extra_graphs()

    reference_sha = None
    reference_version = None
    for graph_id, path, family in graphs:
        result = module.run(path, args.seed)
        vendored_assignment = result["assignment"]
        vendored_value = result["cut_value"]
        rounds = result["rounds"]
        vendored_cut = module.cut_size(
            [(u, v) for u, v in json.loads(Path(path).read_text(encoding="utf-8"))["edges"]],
            {v for v, bit in enumerate(vendored_assignment) if bit == 1},
        )
        # C3's second process: the real thing.
        proc = subprocess.run(
            [args.reference_python, str(REFERENCE), "--graph", path, "--seed", str(args.seed)],
            capture_output=True, text=True, check=True,
        )
        reference = json.loads(proc.stdout)
        reference_sha = reference["networkx_maxcut_sha256"]
        reference_version = reference["networkx_version"]

        agree = (reference["cut_value"] == vendored_cut
                 and reference["partition"] == vendored_assignment)
        # C4: rerun in-process and compare
        rerun = module.run(path, args.seed)
        deterministic = (rerun["cut_value"], rerun["assignment"]) == (vendored_value, vendored_assignment)
        accounted = vendored_value == vendored_cut
        baseline_size = sum(result["baseline_assignment"])
        agrees_with_reference_initial = baseline_size == reference["initial_cut_size"]
        monotone = vendored_cut >= module.cut_size(
            [(u, v) for u, v in json.loads(Path(path).read_text(encoding="utf-8"))["edges"]],
            {v for v, bit in enumerate(result["baseline_assignment"]) if bit == 1},
        )

        rows.append({
            "graph_id": graph_id, "family": family,
            "vendored_cut_value": vendored_cut,
            "reference_cut_value": reference["cut_value"],
            "initial_cut_size": reference["initial_cut_size"],
            "one_exchange_rounds": rounds,
            "partition_sha256": hashlib.sha256(canonical(vendored_assignment).encode()).hexdigest(),
            "reference_equals_vendored": bool(agree),
            "deterministic_rerun": bool(deterministic),
            "returned_value_equals_recomputed_cut": bool(accounted),
            "baseline_size_equals_reference_initial_cut_size": bool(agrees_with_reference_initial),
            "pc_not_worse_than_baseline": bool(monotone),
        })
        if not agree:
            failures.append(f"C3 {graph_id}: vendored {vendored_cut} / {vendored_assignment[:8]}... "
                            f"!= reference {reference['cut_value']} / {reference['partition'][:8]}...")
        if not deterministic:
            failures.append(f"C4 {graph_id}: rerun differed")
        if not accounted:
            failures.append(f"C4 {graph_id}: returned cut value != cut recomputed from the partition")
        if not agrees_with_reference_initial:
            failures.append(f"C0 {graph_id}: b_i has {baseline_size} ones but the reference "
                            f"builds an initial cut of size {reference['initial_cut_size']}")
        if not monotone:
            failures.append(f"C5 {graph_id}: PC_i is worse than b_i")

    c2_ok = reference_sha == PINNED_SHA256
    if not c2_ok:
        failures.append(f"C2 reference install's maxcut.py sha256 {reference_sha} != {PINNED_SHA256}")

    report = {
        "schema": "a0.maxcut.pc_identity/v1",
        "pin": {
            "repository": "https://github.com/networkx/networkx",
            "commit": PINNED_COMMIT,
            "path": "networkx/algorithms/approximation/maxcut.py",
            "function": "one_exchange",
            "maxcut_py_sha256": PINNED_SHA256,
            "license": "BSD-3-Clause",
            "vendored_file": "pc/pinned/networkx_maxcut_b69beb2c.py",
        },
        "seed": args.seed,
        "vendored_solution_sha256": sha256_file(SOLUTION),
        "reference_python": args.reference_python,
        "reference_networkx_version": reference_version,
        "checks": {
            "C0_baseline_matches_reference_initial_cut": all(
                r["baseline_size_equals_reference_initial_cut_size"] for r in rows),
            "C1_vendored_bytes_are_pinned_bytes": c1_ok,
            "C2_reference_install_maxcut_matches_pin": c2_ok,
            "C3_vendored_equals_pinned_networkx": all(r["reference_equals_vendored"] for r in rows),
            "C4_transliteration_is_deterministic_and_self_accounting": all(
                r["deterministic_rerun"] and r["returned_value_equals_recomputed_cut"] for r in rows),
            "C5_pc_is_never_worse_than_baseline": all(r["pc_not_worse_than_baseline"] for r in rows),
        },
        "graphs_checked": len(rows),
        "failures": failures,
        "rows": rows,
    }
    report["verdict"] = "PASS" if not failures else "FAIL"
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    print(f"PC identity: {report['verdict']} over {len(rows)} graphs "
          f"(C1={c1_ok} C2={c2_ok})", file=sys.stderr)
    for failure in failures[:10]:
        print("  " + failure, file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
