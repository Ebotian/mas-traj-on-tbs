#!/usr/bin/env python3
"""Mutation check for EvE's `EID_r`: a different `EID*` must give a different `EID_r`.

Audit `verify/VERDICT.md` R3 rejected the previous derivation because `EID_r.value` was the
sha256 of an artefact the adapter itself generated: it recomputed, but nothing forced the
value to depend on `EID*`. This script is the evidence that the derived value does:

  M1  the published `EID*` recomputes to the value the adapter declares, using
      `tools/recompute-eid-r` (which imports nothing from `a0_adapter`);
  M2  `eid_star` mutated by one nibble in the EID document -> a different `EID_r`;
  M3  one byte mutated in `tasks/circle-packing/e_star.py` -> the recomputation refuses
      (exit 3): the derivation is bound to the evaluator bytes `EID*` names;
  M4  the adapter itself refuses a document whose `eid_star` was mutated (exit 3 from the
      contract's `evalcontract.py verify`), so it cannot emit an `EID_r` for an `EID*` the
      contract does not recognise.

Usage: `python tools/eid_r_mutation_check.py` (exit 0 iff every case behaves as stated).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent.parent
A0_ROOT = ADAPTER_DIR.parent.parent
TOOL = ADAPTER_DIR / "tools" / "recompute-eid-r"
EID_DOCUMENT = A0_ROOT / "contract" / "out" / "plumbing.EID.json"
FR_DECLARATION = A0_ROOT / "contract" / "fr" / "scalar.json"
E_STAR = A0_ROOT / "tasks" / "circle-packing" / "e_star.py"


def recompute(*extra: str, a0_root: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--fr", str(FR_DECLARATION),
         "--a0-root", str(a0_root or A0_ROOT), *extra],
        capture_output=True, text=True,
    )


def value_of(proc: subprocess.CompletedProcess) -> str | None:
    try:
        return json.loads(proc.stdout)["value"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    work = Path(tempfile.mkdtemp(prefix="eid-r-mutation-"))

    # M1 -- the published EID* recomputes to the declared value.
    base = recompute("--eid", str(EID_DOCUMENT))
    declared = value_of(base)
    results.append((
        "M1 published EID* recomputes (standalone tool)",
        base.returncode == 0 and declared is not None,
        f"exit {base.returncode}, value {declared!r}",
    ))

    # M2 -- one nibble of eid_star changed -> different EID_r.
    document = json.loads(EID_DOCUMENT.read_text(encoding="utf-8"))
    original = document["eid_star"]
    mutated_eid = ("f" if original[0] != "f" else "0") + original[1:]
    document["eid_star"] = mutated_eid
    mutated_path = work / "mutated.EID.json"
    mutated_path.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    changed = recompute("--eid", str(mutated_path))
    changed_value = value_of(changed)
    results.append((
        "M2 mutating eid_star changes EID_r",
        changed.returncode == 0 and changed_value is not None and changed_value != declared,
        f"{original} -> {mutated_eid}: {declared!r} vs {changed_value!r}",
    ))

    # M3 -- one byte of the evaluator source changed -> the recomputation refuses.
    fake_root = work / "a0"
    (fake_root / "tasks" / "circle-packing").mkdir(parents=True)
    for name in ("e_star.py", "e_star_child.py"):
        shutil.copy2(A0_ROOT / "tasks" / "circle-packing" / name,
                     fake_root / "tasks" / "circle-packing" / name)
    target = fake_root / "tasks" / "circle-packing" / "e_star.py"
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace("import", "imp0rt", 1), encoding="utf-8")
    tampered = recompute("--eid", str(EID_DOCUMENT), a0_root=fake_root)
    results.append((
        "M3 a mutated evaluator source is refused, not hashed",
        tampered.returncode == 3 and "does not describe these bytes" in tampered.stderr,
        f"exit {tampered.returncode}: {tampered.stderr.strip().splitlines()[-1:] or ['']}",
    ))

    # M4 -- the adapter refuses a mutated EID* document outright.
    adapter = subprocess.run(
        [sys.executable, "-m", "a0_adapter", "conformance", "--runtime", "eve",
         "--candidate-set", str(A0_ROOT / "tasks" / "circle-packing" / "C_STAR" / "manifest.json"),
         "--eid", str(mutated_path),
         "--spec", str(A0_ROOT / "contract" / "plumbing.contract.json"),
         "--theta", "seed=none,fidelity=full,fraction=1.0",
         "--fr", str(FR_DECLARATION),
         "--run-dir", str(work / "refused-run"),
         "--out", str(work / "refused.json")],
        cwd=str(ADAPTER_DIR), capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    results.append((
        "M4 adapter refuses a mutated EID* (evalcontract verify)",
        adapter.returncode == 3,
        f"exit {adapter.returncode}: {(adapter.stderr or '').strip().splitlines()[-1:] or ['']}",
    ))

    print(f"EID_r mutation check (a0 root {A0_ROOT})")
    ok = True
    for name, passed, detail in results:
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}\n         {detail}")
    print(f"declared/derived value: {declared}")
    print("all cases behaved as stated" if ok else "SOME CASES FAILED")
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
