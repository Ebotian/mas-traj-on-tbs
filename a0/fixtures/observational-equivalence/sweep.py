#!/usr/bin/env python3
"""Run one evaluator over all of C* and record the canonical Outcomes.

This fixture's own driver, used to compare two *evaluators* (E* and a mutant)
over the frozen candidate set.  It is deliberately not the conformance runner:
the equality it establishes is `E'(c) == E*(c)` for every c in C*, which is the
behavioural half of A0.1 with the adapter removed.

    python3 sweep.py --evaluator-dir <dir> --out-root <dir> [--python <exe>]
                     [--seed S] [--fidelity full|fast] [--fraction F]

`--evaluator-dir` must contain `e_star.py`.  Outcomes are written below
`--out-root/outcomes/<id>.json`; the summary (exit code, status, objective,
failure kind, canonical digest, structure) goes to `--out-root/sweep.json`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
A0 = HERE.parents[1]
TASK = A0 / "tasks" / "circle-packing"
C_STAR = TASK / "C_STAR"
MANIFEST = C_STAR / "manifest.json"
DEFAULT_PYTHON = TASK / ".venv" / "bin" / "python"

THETA = {
    "seed": 1337,
    "fidelity": "full",
    "fraction": 1.0,
    "n": 26,
    "runs": 5,
    "runtime_budget_ms": 250.0,
    "timeout_s": 120.0,
}


def manifest_candidates() -> list[dict]:
    return json.loads(MANIFEST.read_text())["candidates"]


def evaluate(python: str, script: Path, candidate_dir: Path, out_json: Path, state_dir: Path,
             theta: dict, timeout: float, cwd: Path) -> dict:
    argv = [
        python, str(script), "evaluate",
        "--candidate", str(candidate_dir),
        "--seed", str(theta["seed"]),
        "--fidelity", str(theta["fidelity"]),
        "--fraction", str(theta["fraction"]),
        "--n", str(theta["n"]),
        "--runs", str(theta["runs"]),
        "--runtime-budget-ms", str(theta["runtime_budget_ms"]),
        "--timeout-s", str(theta["timeout_s"]),
        "--out", str(out_json),
        "--state-dir", str(state_dir),
    ]
    started = time.time()
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(cwd), timeout=timeout, check=False)
    outcome = None
    if out_json.exists():
        outcome = json.loads(out_json.read_text())
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "duration_s": round(time.time() - started, 3),
        "objective_value": ((outcome or {}).get("objective") or {}).get("value"),
        "status": (outcome or {}).get("status"),
        "failure_kind": ((outcome or {}).get("failure") or {}).get("kind"),
        "canonical_digest": (outcome or {}).get("canonical_digest"),
        "evaluator_source_sha256": (outcome or {}).get("evaluator_source_sha256"),
        "interpreter": (outcome or {}).get("interpreter"),
        "structure": (outcome or {}).get("structure"),
        "stderr_tail": "\n".join(proc.stderr.strip().splitlines()[-3:]),
        "outcome": outcome,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluator-dir", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--python", default=str(DEFAULT_PYTHON))
    parser.add_argument("--seed", type=int, default=THETA["seed"])
    parser.add_argument("--fidelity", default=THETA["fidelity"], choices=("full", "fast"))
    parser.add_argument("--fraction", type=float, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)

    theta = dict(THETA)
    theta["seed"] = args.seed
    theta["fidelity"] = args.fidelity
    theta["fraction"] = 1.0 if args.fidelity == "full" else 0.15
    if args.fraction is not None:
        theta["fraction"] = args.fraction

    eval_dir = Path(args.evaluator_dir).resolve()
    script = eval_dir / "e_star.py"
    out_root = Path(args.out_root).resolve()
    (out_root / "outcomes").mkdir(parents=True, exist_ok=True)
    label = args.label or eval_dir.name

    rows = []
    for cand in manifest_candidates():
        cid = cand["candidate_id"]
        cdir = C_STAR / cand["path"]
        row = evaluate(
            args.python, script, cdir, out_root / "outcomes" / f"{cid}.json",
            out_root / "state", theta, args.timeout, eval_dir,
        )
        row["candidate_id"] = cid
        row["candidate_dir"] = str(cdir)
        row["source_sha256"] = cand["solution_sha256"]
        rows.append(row)
        value = row["objective_value"]
        print(f"  {label} {cid:<26} exit={row['exit_code']} status={str(row['status']):<7} "
              f"objective={value!r:<22} kind={row['failure_kind']}")

    summary = {
        "schema": "a0.fixture.observational-equivalence.sweep/v1",
        "label": label,
        "evaluator_dir": str(eval_dir),
        "evaluator_script": str(script),
        "python": args.python,
        "theta_e": theta,
        "candidates": rows,
    }
    (out_root / "sweep.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"written: {out_root / 'sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
