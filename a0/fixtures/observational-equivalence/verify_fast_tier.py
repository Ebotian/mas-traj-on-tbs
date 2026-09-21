#!/usr/bin/env python3
"""Check the cheaper mechanism the independent verifier proposed.

`E_STAR.json` freezes, per candidate, a `fast_tier` row (measured at
`E_STAR.json.fast_theta_e`: `fidelity=fast, fraction=0.15, seed=1337, n=26,
runs=5`).  The A0.1 checker does not read it.  This script establishes three
things with measurements instead of assertions:

  1. the frozen `fast_tier` rows exist, and the A0.1 checker never reads them
     (a source scan of `a0/conformance/conformance.py`, whose hit count is
     recorded in the output);
  2. `E*`'s own fresh fast sweep reproduces those rows -- without that, the
     frozen fast tier would not be a usable oracle;
  3. how each mutant fares against the frozen full table and the frozen fast
     rows, at the level A0.1 compares (`exit_code`, `status`, `failure_kind`,
     `objective_value`) and, separately, at the level of `canonical_digest`.

    python3 verify_fast_tier.py --out out/fast_tier_check.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
A0 = HERE.parents[1]
E_STAR_TABLE = A0 / "tasks" / "circle-packing" / "E_STAR.json"
CHECKER = A0 / "conformance" / "conformance.py"

SWEEPS = {
    "e_star_full": "out/e_star/sweep.json",
    "e_star_fast": "out/e_star.fast/sweep.json",
    "e_prime_full": "out/e_prime/sweep.json",
    "e_prime_fast": "out/e_prime.fast/sweep.json",
    "e_prime_fulltheta_full": "out/e_prime_fulltheta/sweep.json",
    "e_prime_fulltheta_fast": "out/e_prime_fulltheta.fast/sweep.json",
}
COMPARED = ("exit_code", "status", "failure_kind", "objective_value")


def scan_checker(path: Path) -> dict:
    text = path.read_text()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "fast_tier_occurrences": len(re.findall(r"fast_tier", text)),
        "fast_theta_e_occurrences": len(re.findall(r"fast_theta_e", text)),
    }


def frozen_rows(table: dict) -> tuple[dict, dict]:
    full, fast = {}, {}
    for cand in table["candidates"]:
        cid = cand["candidate_id"]
        full[cid] = {
            "exit_code": cand.get("exit_code"),
            "status": cand.get("status"),
            "failure_kind": cand.get("failure_kind"),
            "objective_value": cand.get("objective_value"),
            "canonical_digest": cand.get("canonical_digest"),
        }
        ft = cand.get("fast_tier") or {}
        fast[cid] = {
            "exit_code": ft.get("exit_code"),
            "status": ft.get("status"),
            "failure_kind": ft.get("failure_kind"),
            "objective_value": ft.get("objective_value"),
            "canonical_digest": ft.get("canonical_digest"),
            "items_audited": ft.get("items_audited"),
            "pairs_audited": ft.get("pairs_audited"),
        }
    return full, fast


def compare(sweep: dict, frozen: dict) -> dict:
    rows, verdict_mismatch, digest_mismatch = [], [], []
    for row in sweep["candidates"]:
        cid = row["candidate_id"]
        want = frozen.get(cid) or {}
        got = {k: row.get(k) for k in COMPARED}
        got["canonical_digest"] = row.get("canonical_digest")
        value_problems = [k for k in COMPARED if got.get(k) != want.get(k)]
        digest_problem = got.get("canonical_digest") != want.get("canonical_digest")
        rows.append({
            "candidate_id": cid,
            "equal_on_" + "_".join(COMPARED): not value_problems,
            "differing_fields": value_problems,
            "digest_equal": not digest_problem,
            "sweep": {k: got.get(k) for k in COMPARED},
            "frozen": {k: want.get(k) for k in COMPARED},
        })
        if value_problems:
            verdict_mismatch.append(cid)
        if digest_problem:
            digest_mismatch.append(cid)
    return {
        "candidates": len(rows),
        "equal_on_exit_status_kind_objective": not verdict_mismatch,
        "differing_candidates": verdict_mismatch,
        "digest_equal_everywhere": not digest_mismatch,
        "digest_differing_candidates": digest_mismatch,
        "rows": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="fast-tier check")
    args = parser.parse_args(argv)

    table = json.loads(E_STAR_TABLE.read_text())
    full, fast = frozen_rows(table)
    scan = scan_checker(CHECKER)

    sweeps = {name: json.loads((HERE / rel).read_text()) for name, rel in SWEEPS.items()}
    results = {}
    for name, sweep in sweeps.items():
        frozen = fast if name.endswith("_fast") else full
        results[name] = {
            "sweep": SWEEPS[name],
            "evaluator_dir": sweep["evaluator_dir"],
            "theta_e": sweep["theta_e"],
            "against": "E_STAR.json fast_tier rows" if name.endswith("_fast") else "E_STAR.json full rows",
            **compare(sweep, frozen),
        }

    doc = {
        "schema": "a0.fixture.observational-equivalence.fast-tier-check/v1",
        "label": args.label,
        "frozen_table": {
            "path": str(E_STAR_TABLE),
            "sha256": hashlib.sha256(E_STAR_TABLE.read_bytes()).hexdigest(),
            "fast_theta_e": table.get("fast_theta_e"),
            "candidates_with_fast_tier": sum(1 for c in table["candidates"] if c.get("fast_tier")),
        },
        "checker_scan": scan,
        "results": results,
    }
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n")

    print(f"frozen table {E_STAR_TABLE.name}: {doc['frozen_table']['candidates_with_fast_tier']} candidates carry a "
          f"fast_tier row at {json.dumps(doc['frozen_table']['fast_theta_e'])}")
    print(f"checker scan: 'fast_tier' occurrences = {scan['fast_tier_occurrences']}, "
          f"'fast_theta_e' occurrences = {scan['fast_theta_e_occurrences']}  ({scan['sha256'][:12]})")
    for name, r in results.items():
        print(f"  {name:<26} vs {r['against']:<34} "
              f"values_equal={r['equal_on_exit_status_kind_objective']!s:<5} "
              f"digests_equal={r['digest_equal_everywhere']!s:<5} "
              f"differing_values={r['differing_candidates'] or 'none'}")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
