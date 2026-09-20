#!/usr/bin/env python3
"""An honest, minimal A0.1 adapter: the template a real runtime adapter should follow.

It is **not** a runtime adapter and must never be reported as one. It has no search machinery;
it does exactly what A0.1 asks of an adapter:

  1. verify `sha256(solution.py)` of every member of `C*` before evaluating anything;
  2. invoke the frozen `E*` through the frozen CLI, once per candidate, with the frozen
     `theta_E`, into an output path outside every candidate worktree;
  3. report the raw multi-field Outcome plus E*'s own status/exit code, so the *verdict* of an
     invalid/error candidate is compared as a verdict rather than as a number;
  4. carry `eid_star` verbatim and a recomputable `EID_r` derivation;
  5. mark each row's `evaluator_evidence.status` honestly (`ok` only for a real subprocess run).

Self-test use: `selftest.py` runs it as the control row that must come back PASS, which is what
makes the FAIL rows of the deviant fixtures meaningful.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_common import (  # noqa: E402
    A0, C_STAR_MANIFEST, E_STAR_PYTHON, E_STAR_SCRIPT, FR_DECLARATION, THETA_KEYS,
    canonical_file_digest, eid_r_declaration, read_args, sha256_file, write_out,
)
from fixture_common import parse_theta  # noqa: E402

DEFAULTS = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
            "runtime_budget_ms": 250.0, "timeout_s": 120.0}


def e_star_argv(candidate_dir: Path, out_json: Path, state_dir: Path, theta: dict) -> list:
    return [
        str(E_STAR_PYTHON), str(E_STAR_SCRIPT), "evaluate",
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


def conformance(flags: dict) -> int:
    runtime = flags.get("runtime", "unknown")
    out_path = Path(flags["out"])
    theta = dict(DEFAULTS)
    theta.update({k: v for k, v in parse_theta(flags.get("theta", "")).items() if k in THETA_KEYS})
    manifest = json.loads(C_STAR_MANIFEST.read_text())
    root = C_STAR_MANIFEST.parent
    eid_doc = json.loads(Path(flags["eid"]).read_text()) if flags.get("eid") else {}
    eid_star = eid_doc.get("eid_star", "")

    run_dir = Path(flags.get("run-dir",
                            Path(__file__).resolve().parents[2] / "out" / "fixture-runs" / runtime))
    out_dir = run_dir / "e-star"
    state_dir = run_dir / "e-star-state"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for cand in manifest["candidates"]:
        cid = cand["candidate_id"]
        cdir = root / cand["path"]
        source = cdir / "solution.py"
        observed = sha256_file(source) if source.exists() else None
        if observed != cand["solution_sha256"]:
            return 4  # integrity failure, exactly as adapter_contract.md 3.1 requires
        outcome_path = out_dir / f"{cid}.json"
        if outcome_path.exists():
            outcome_path.unlink()
        proc = subprocess.run(
            e_star_argv(cdir, outcome_path, state_dir, theta),
            capture_output=True, text=True, timeout=float(theta["timeout_s"]) + 60.0,
        )
        outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else {}
        objective = outcome.get("objective") or {}
        rows.append(
            {
                "candidate_id": cid,
                "source_sha256": observed,
                "canonical_digest": outcome.get("canonical_digest"),
                "status": outcome.get("status"),
                "exit_code": proc.returncode,
                "objective": {
                    "name": objective.get("name"),
                    "value": objective.get("value"),
                    "direction": objective.get("direction"),
                },
                "objective_value": objective.get("value"),
                "failure_kind": ("adversarially_wrong_kind" if (outcome.get("status") or "") != "ok"
                                else (outcome.get("failure") or {}).get("kind")),
                "fields": outcome.get("fields"),
                "evaluator_evidence": {
                    "status": "ok",
                    "detail": f"fresh E* subprocess run, exit {proc.returncode} (E*'s own contract)",
                },
                "theta_e_attempt": {
                    "evaluator": "E*",
                    "fidelity": theta["fidelity"],
                    "fraction": theta["fraction"],
                    "seed": theta["seed"],
                    "granted_class": theta["fidelity"],
                    "commanded_class": theta["fidelity"],
                },
            }
        )

    doc = {
        "schema": "a0.adapter.conformance/v1",
        "runtime": runtime,
        "adapter": "a0/conformance/fixtures/adapters/reference_adapter.py (FIXTURE, not a runtime)",
        "eid_star": eid_star,
        "eid_r": eid_r_declaration(eid_star, runtime, "reference_adapter"),
        "theta_e": theta,
        "epsilon": float(flags.get("epsilon", 1e-9)),
        "primary_field": "sum_radii",
        "fr": {
            "name": "F_r = scalar(E*)",
            "version": "v1",
            "applies": "scalar",
            "spec_hash": canonical_file_digest(FR_DECLARATION),
            "declared_in": "a0/contract/fr/scalar.json",
        },
        "candidate_set": str(C_STAR_MANIFEST),
        "candidates": rows,
    }
    write_out(out_path, doc)
    return 0


def main(argv):
    positional, flags = read_args(argv)
    if positional and positional[0] == "conformance":
        return conformance(flags)
    if positional and positional[0] == "run":
        # a `run` shim so the runner's fallback path is exercisable too
        rc = conformance(flags)
        if rc:
            return rc
        return 0
    print(f"reference_adapter: unsupported subcommand {positional!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
