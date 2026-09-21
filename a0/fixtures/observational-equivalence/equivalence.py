#!/usr/bin/env python3
"""Compare two sweeps of C* (see `sweep.py`) candidate by candidate.

Establishes the fixture's central claim mechanically: whether evaluator B agrees
with evaluator A on every member of C* -- same exit code, same status, same
verdict kind, same objective *bit for bit* (float equality, with the hex form of
the value printed so a one-ULP difference cannot hide behind repr rounding).

    python3 equivalence.py --a out/e_star/sweep.json --b out/e_prime/sweep.json \
                           --out out/equivalence.full.json

Exit code 0 when every compared field agrees exactly, 3 otherwise.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

COMPARED = ("exit_code", "status", "failure_kind", "objective_value")


def bits(value) -> str | None:
    if value is None:
        return None
    return struct.pack(">d", float(value)).hex()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="reference sweep.json")
    parser.add_argument("--b", required=True, help="mutant sweep.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--label-a", default=None)
    parser.add_argument("--label-b", default=None)
    args = parser.parse_args(argv)

    a_doc = json.loads(Path(args.a).read_text())
    b_doc = json.loads(Path(args.b).read_text())
    label_a = args.label_a or a_doc["label"]
    label_b = args.label_b or b_doc["label"]
    b_by_id = {row["candidate_id"]: row for row in b_doc["candidates"]}

    rows = []
    disagreeing = []
    for row_a in a_doc["candidates"]:
        cid = row_a["candidate_id"]
        row_b = b_by_id.get(cid)
        if row_b is None:
            rows.append({"candidate_id": cid, "agree": False, "problems": ["missing from B"]})
            disagreeing.append(cid)
            continue
        problems = []
        for field in COMPARED:
            if row_a[field] != row_b[field]:
                problems.append(f"{field}: A={row_a[field]!r} B={row_b[field]!r}")
        if bits(row_a["objective_value"]) != bits(row_b["objective_value"]):
            problems.append(
                f"objective bits: A={bits(row_a['objective_value'])} B={bits(row_b['objective_value'])}"
            )
        rows.append(
            {
                "candidate_id": cid,
                "status": row_a["status"],
                "failure_kind": row_a["failure_kind"],
                "objective_value": row_a["objective_value"],
                "objective_bits": bits(row_a["objective_value"]),
                "structure_a": row_a.get("structure"),
                "structure_b": row_b.get("structure"),
                "structure_identical": row_a.get("structure") == row_b.get("structure"),
                "agree": not problems,
                "problems": problems,
            }
        )
        if problems:
            disagreeing.append(cid)

    doc = {
        "schema": "a0.fixture.observational-equivalence.equivalence/v1",
        "a": {"label": label_a, "sweep": str(args.a), "evaluator_dir": a_doc["evaluator_dir"],
              "evaluator_script_sha256": _sha(a_doc["evaluator_script"])},
        "b": {"label": label_b, "sweep": str(args.b), "evaluator_dir": b_doc["evaluator_dir"],
              "evaluator_script_sha256": _sha(b_doc["evaluator_script"])},
        "theta_e": a_doc["theta_e"],
        "compared_fields": list(COMPARED) + ["objective_value as float bits"],
        "candidates_compared": len(rows),
        "agreeing_on_all_compared_fields": not disagreeing,
        "disagreeing": disagreeing,
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n")

    print(f"{'candidate':<26} {'status':<8} {'objective':<22} {'compared':<10} structure")
    for row in rows:
        print(
            f"  {row['candidate_id']:<24} {str(row['status']):<8} {str(row['objective_value']):<22} "
            f"{'AGREE' if row['agree'] else 'DISAGREE':<10} "
            f"{'same' if row.get('structure_identical') else 'DIFFERS'}"
        )
    for row in rows:
        for problem in row.get("problems") or []:
            print(f"    !! {row['candidate_id']}: {problem}")
    print(f"{label_a} vs {label_b}: {len(rows) - len(disagreeing)}/{len(rows)} candidates agree exactly "
          f"on {list(COMPARED)}")
    print(f"written: {args.out}")
    return 3 if disagreeing else 0


def _sha(path: str) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
