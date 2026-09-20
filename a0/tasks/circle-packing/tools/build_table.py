"""Rebuild `E_STAR.json`: E* applied to every member of `C_STAR/`.

The table is produced by invoking the real CLI once per candidate -- no imports
of `e_star.py` internals -- and recording the exit code, the manifest line and
the canonical Outcome verbatim.  Timings are deliberately not part of the table:
they are environment-dependent and live in the evaluator's state root.

    .venv/bin/python tools/build_table.py --write    # (re)write E_STAR.json
    .venv/bin/python tools/build_table.py --check    # rerun and diff (stability)

`--check` reruns every candidate and compares the freshly built table with the
committed one byte for byte, which is the stability evidence for the frozen
table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
C_STAR = ROOT / "C_STAR"
TABLE_PATH = ROOT / "E_STAR.json"
STATE_ROOT = Path("/tmp/e-star-state-table")
TABLE_VERSION = "1.0.0"

CANONICAL_THETA = {
    "seed": 1337,
    "fidelity": "full",
    "fraction": 1.0,
    "n": 26,
    "runs": 5,
    "runtime_budget_ms": 250.0,
    "timeout_s": 120.0,
}
FAST_THETA = {
    "seed": 1337,
    "fidelity": "fast",
    "fraction": 0.15,
    "n": 26,
    "runs": 5,
    "runtime_budget_ms": 250.0,
    "timeout_s": 120.0,
}


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate_dirs() -> list[Path]:
    return sorted(path for path in C_STAR.iterdir() if path.is_dir())


def evaluate(candidate: Path, theta: dict[str, Any], tag: str) -> dict[str, Any]:
    out_path = STATE_ROOT / "outcomes" / f"{candidate.name}.{tag}.json"
    command = [
        ".venv/bin/python",
        "e_star.py",
        "evaluate",
        "--candidate",
        f"C_STAR/{candidate.name}",
        "--seed",
        str(theta["seed"]),
        "--fidelity",
        theta["fidelity"],
        "--fraction",
        str(theta["fraction"]),
        "--n",
        str(theta["n"]),
        "--runs",
        str(theta["runs"]),
        "--runtime-budget-ms",
        str(theta["runtime_budget_ms"]),
        "--timeout-s",
        str(theta["timeout_s"]),
        "--out",
        str(out_path),
        "--state-dir",
        str(STATE_ROOT / "state"),
    ]
    completed = subprocess.run(
        command, cwd=str(ROOT), capture_output=True, text=True, check=False
    )
    manifest_line = ""
    for line in completed.stdout.splitlines():
        if line.startswith("E_STAR_MANIFEST "):
            manifest_line = line
    outcome = json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else None
    return {
        "exit_code": completed.returncode,
        "command": " ".join(command),
        "manifest_line": manifest_line,
        "outcome": outcome,
    }


def evaluator_identity() -> dict[str, Any]:
    digest = subprocess.run(
        [".venv/bin/python", "e_star.py", "digest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(digest.stdout)


def build() -> dict[str, Any]:
    identity = evaluator_identity()
    candidates = []
    for directory in candidate_dirs():
        record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
        full = evaluate(directory, CANONICAL_THETA, "full")
        fast = evaluate(directory, FAST_THETA, "fast")
        outcome = full["outcome"] or {}
        fast_outcome = fast["outcome"] or {}
        candidates.append(
            {
                "candidate_id": record["candidate_id"],
                "dir": f"C_STAR/{directory.name}",
                "kind": record["kind"],
                "expected_status_at_theta_e_star": record["expected_status_at_theta_e_star"],
                "source_sha256": record["source_sha256"],
                "source_bytes": record["source_bytes"],
                "exit_code": full["exit_code"],
                "command": full["command"],
                "manifest_line": full["manifest_line"],
                "status": outcome.get("status"),
                "canonical_digest": outcome.get("canonical_digest"),
                "objective_value": (outcome.get("objective") or {}).get("value"),
                "failure_kind": (outcome.get("failure") or {}).get("kind"),
                "outcome": outcome,
                "fast_tier": {
                    "exit_code": fast["exit_code"],
                    "command": fast["command"],
                    "status": fast_outcome.get("status"),
                    "objective_value": (fast_outcome.get("objective") or {}).get("value"),
                    "failure_kind": (fast_outcome.get("failure") or {}).get("kind"),
                    "items_audited": (fast_outcome.get("validity") or {}).get("audit", {}).get("items_audited"),
                    "pairs_audited": (fast_outcome.get("validity") or {}).get("audit", {}).get("pairs_audited"),
                    "coverage": (fast_outcome.get("validity") or {}).get("audit", {}).get("coverage"),
                    "canonical_digest": fast_outcome.get("canonical_digest"),
                    "outcome": fast_outcome,
                },
            }
        )

    return {
        "schema": "e_star.table/v1",
        "version": TABLE_VERSION,
        "generated_by": "tools/build_table.py",
        "state_root": str(STATE_ROOT),
        "evaluator": {
            "script": "e_star.py",
            "check_runner": "e_star_child.py",
            "e_star_version": identity["e_star_version"],
            "evaluator_source_sha256": identity["evaluator_source_sha256"],
            "source_files": identity["source_files"],
            "interpreter": {
                "executable": ".venv/bin/python",
                "version": ".".join(str(part) for part in sys.version_info[:3]),
            },
        },
        "canonical_theta_e": dict(CANONICAL_THETA),
        "fast_theta_e": dict(FAST_THETA),
        "command_template": (
            ".venv/bin/python e_star.py evaluate --candidate <CANDIDATE_DIR> "
            "--seed 1337 --fidelity <full|fast> --fraction <1.0|0.15> "
            "--out <STATE_ROOT>/outcomes/<ID>.json --state-dir <STATE_ROOT>/state"
        ),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "notes": {
            "timings": "Runtime measurements are environment-dependent and are "
                       "deliberately excluded: they live in the evaluator state root.",
            "objective": "objective.value is null whenever status != ok; a null "
                         "objective is never a zero score.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    table = build()
    text = canonical_json(table)
    if args.check:
        if not TABLE_PATH.is_file():
            print("E_STAR.json is missing")
            return 1
        current = TABLE_PATH.read_text(encoding="utf-8")
        if current == text:
            print("E_STAR.json is stable: rerun produced byte-identical output")
            _print_summary(table)
            return 0
        print("E_STAR.json DIFFERS from a fresh rerun")
        import difflib

        for line in list(
            difflib.unified_diff(
                current.splitlines(), text.splitlines(), "committed", "rerun", lineterm=""
            )
        )[:80]:
            print(line)
        return 1

    TABLE_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {TABLE_PATH} ({len(text)} bytes)")
    _print_summary(table)
    return 0


def _print_summary(table: dict[str, Any]) -> None:
    print(f"{'candidate':32} {'exit':>4} {'status':>8} {'objective':>22}  fast")
    for entry in table["candidates"]:
        objective = entry["objective_value"]
        fast = entry["fast_tier"]
        print(
            f"{entry['candidate_id']:32} {entry['exit_code']:>4} {str(entry['status']):>8} "
            f"{(f'{objective:.12f}' if isinstance(objective, float) else 'null'):>22}  "
            f"{fast['status']}/{fast['items_audited']}items"
        )


if __name__ == "__main__":
    raise SystemExit(main())
