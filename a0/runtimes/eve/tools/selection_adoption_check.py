#!/usr/bin/env python3
"""Prove the frozen A0-wide staging table is *enforced*, not merely obeyed.

`adapter_contract.md` §5.3 makes `failure_stage_mapping` (and `scalarization`) A0-wide, and
`a0_adapter/selectionmap.py` refuses a run (exit 3) when EvE's copy, the contract's copy and the
frozen digest disagree. This script exercises that refusal by pointing the loader at perturbed
copies in a temporary tree — it never touches `a0/contract/**`.

  N1 the contract's copy stages `runtime_budget_exceeded` as something else  -> refuse
  N2 the contract's copy gains a verdict key                                  -> refuse
  N3 the contract is untouched but EvE's own copy drifts                      -> refuse
  N4 both copies are the frozen ones                                          -> accept
  N5 the real tree's declaration                                              -> accept

Usage: `python tools/selection_adoption_check.py` (exit 0 iff every case behaves as stated).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent.parent
A0_ROOT = ADAPTER_DIR.parent.parent
sys.path.insert(0, str(ADAPTER_DIR))

from a0_adapter import selectionmap  # noqa: E402

CONTRACT = A0_ROOT / "contract" / "selection" / "simpleloop.selection.json"
EVE_COPY = A0_ROOT / "runtimes" / "eve" / "selection" / "eve.selection.json"


def case(label: str, contract_doc: dict, eve_doc: dict, expect: str) -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="selmap-control-"))
    (tmp / "a0" / "contract" / "selection").mkdir(parents=True)
    (tmp / "a0" / "runtimes" / "eve" / "selection").mkdir(parents=True)
    (tmp / "a0" / "contract" / "selection" / CONTRACT.name).write_text(
        json.dumps(contract_doc, indent=1, sort_keys=True), encoding="utf-8")
    (tmp / "a0" / "runtimes" / "eve" / "selection" / EVE_COPY.name).write_text(
        json.dumps(eve_doc, indent=1, sort_keys=True), encoding="utf-8")
    selectionmap._load_cached.cache_clear()
    original = selectionmap._path
    selectionmap._path = lambda relative: tmp / relative
    try:
        report = selectionmap.check_adoption()
        outcome = f"accepted (agrees={report['agrees']})"
        okay = expect == "accept"
    except selectionmap.SelectionMappingError as exc:
        outcome = f"refused: {str(exc)[:160]}"
        okay = expect == "refuse"
    finally:
        selectionmap._path = original
        selectionmap._load_cached.cache_clear()
        shutil.rmtree(tmp, ignore_errors=True)
    return okay, outcome


def main() -> int:
    frozen = json.loads(CONTRACT.read_text(encoding="utf-8"))
    eve_copy = json.loads(EVE_COPY.read_text(encoding="utf-8"))

    restaged = json.loads(json.dumps(frozen))
    restaged["failure_stage_mapping"]["exit_3_error_runtime_budget_exceeded"] = "evaluator_failed"

    extended = json.loads(json.dumps(frozen))
    extended["failure_stage_mapping"]["exit_3_error_brand_new_kind"] = "evaluator_failed"

    cases = [
        ("N1 contract stages runtime_budget_exceeded as evaluator_failed",
         restaged, {**eve_copy, "failure_stage_mapping": restaged["failure_stage_mapping"]}, "refuse"),
        ("N2 contract gains a new verdict key",
         extended, {**eve_copy, "failure_stage_mapping": extended["failure_stage_mapping"]}, "refuse"),
        ("N3 contract untouched, EvE's copy drifts",
         frozen, {**eve_copy, "failure_stage_mapping": restaged["failure_stage_mapping"]}, "refuse"),
        ("N4 both copies are the frozen ones", frozen, eve_copy, "accept"),
    ]
    print("frozen-block adoption controls (a perturbed table must stop the run)")
    all_ok = True
    for label, contract_doc, eve_doc, expect in cases:
        okay, outcome = case(label, contract_doc, eve_doc, expect)
        all_ok = all_ok and okay
        print(f"  [{'PASS' if okay else 'FAIL'}] {label}\n         {outcome}")

    real = selectionmap.check_adoption()
    all_ok = all_ok and real["agrees"]
    print(f"  [{'PASS' if real['agrees'] else 'FAIL'}] N5 the real tree's declaration agrees")
    for name, block in sorted(real["blocks"].items()):
        print(f"         {name}: frozen {block['frozen_digest'][:12]}… == contract "
              f"{str(block['contract_digest'])[:12]}… == eve {str(block['eve_digest'])[:12]}…")
    print("all cases behaved as stated" if all_ok else "SOME CASES FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
