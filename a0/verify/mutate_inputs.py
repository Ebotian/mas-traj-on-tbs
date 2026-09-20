#!/usr/bin/env python3
"""Single-input sensitivity test for EID*, run against a staged minimal base.

For each of the five inputs exactly one is mutated relative to a common baseline;
exactly one component digest (and EID*) must change.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from myEID import build  # noqa: E402

ROOT = Path("/home/ebt/rsi-dev/a0")
STAGE = ROOT / "verify/out/mut"
SRC_SPEC = ROOT / "contract/plumbing.contract.json"


def restage():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    base = STAGE / "base"
    tp = base / "tasks/circle-packing"
    (tp / "C_STAR/c01_good_hex").mkdir(parents=True)
    shutil.copy(ROOT / "tasks/circle-packing/e_star.py", tp / "e_star.py")
    shutil.copy(ROOT / "tasks/circle-packing/e_star_child.py", tp / "e_star_child.py")
    shutil.copy(ROOT / "tasks/circle-packing/requirements.lock", tp / "requirements.lock")
    shutil.copy(ROOT / "tasks/circle-packing/C_STAR/c01_good_hex/candidate.json",
                tp / "C_STAR/c01_good_hex/candidate.json")
    shutil.copy(ROOT / "tasks/circle-packing/C_STAR/c01_good_hex/solution.py",
                tp / "C_STAR/c01_good_hex/solution.py")
    spec = json.loads(SRC_SPEC.read_text())
    spec["base"] = "."
    # keep the staged copy small but keep every component exercised
    spec["components"]["DataManifest"]["files"] = [
        "tasks/circle-packing/C_STAR/c01_good_hex/candidate.json",
        "tasks/circle-packing/C_STAR/c01_good_hex/solution.py",
    ]
    spec["components"]["DataManifest"]["entries"] = [
        e for e in spec["components"]["DataManifest"]["entries"]
        if e.get("candidate_set_id") or e.get("reference_table") or e.get("commit")
    ]
    (STAGE / "spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True))
    return STAGE / "spec.json", base


def run(spec_path, base):
    return build(json.loads(spec_path.read_text()), base)


def main():
    spec_path, base = restage()
    b = run(spec_path, base)
    print("BASELINE")
    for k, v in b["digests"].items():
        print(f"  {k:<18} {v}")
    print(f"  {'EID*':<18} {b['eid_star']}")

    results = []

    def case(name, mutate, expect):
        sp, base = STAGE / "spec.json", STAGE / "base"
        restage()
        mutate(sp, base)
        m = run(sp, base)
        changed = sorted(k for k in b["digests"] if b["digests"][k] != m["digests"][k])
        eid_changed = b["eid_star"] != m["eid_star"]
        ok = changed == [expect] and eid_changed
        results.append({"mutation": name, "component_changed": changed,
                        "expected": expect, "eid_star_changed": eid_changed, "ok": ok})
        print(f"\n[{ 'PASS' if ok else 'FAIL' }] {name}: changed={changed} "
              f"expected=[{expect}] eid*_changed={eid_changed}")

    tp = STAGE / "base/tasks/circle-packing"

    def m_source(sp, base):
        with open(tp / "e_star.py", "ab") as fh:
            fh.write(b"\n# adversarial mutation\n")

    def m_lock(sp, base):
        with open(tp / "requirements.lock", "ab") as fh:
            fh.write(b"# adversarial mutation\n")

    def m_data(sp, base):
        p = tp / "C_STAR/c01_good_hex/candidate.json"
        d = json.loads(p.read_text())
        d["__adversarial__"] = 1
        p.write_text(json.dumps(d))

    def m_config(sp, base):
        d = json.loads(sp.read_text())
        d["components"]["Config"]["value"]["conformance"]["epsilon"]["value"] = 0.5
        sp.write_text(json.dumps(d, sort_keys=True))

    def m_metric(sp, base):
        d = json.loads(sp.read_text())
        d["components"]["MetricDefinition"]["value"]["unit"] = "adversarial unit"
        sp.write_text(json.dumps(d, sort_keys=True))

    def m_extra_file_unincluded(sp, base):
        (tp / "unrelated.py").write_text("# not in include list\n")

    case("EvaluatorSource: append byte to e_star.py", m_source, "EvaluatorSource")
    case("DependencyLock: append line to requirements.lock", m_lock, "DependencyLock")
    case("DataManifest: edit candidate.json", m_data, "DataManifest")
    case("Config: change conformance epsilon", m_config, "Config")
    case("MetricDefinition: change unit string", m_metric, "MetricDefinition")

    # negative control: a file outside the include list must NOT perturb anything
    restage()
    m_extra_file_unincluded(STAGE / "spec.json", STAGE / "base")
    m = run(STAGE / "spec.json", STAGE / "base")
    same = m["digests"] == b["digests"] and m["eid_star"] == b["eid_star"]
    print(f"\n[{'PASS' if same else 'FAIL'}] negative control: unrelated.py beside e_star.py "
          f"does not perturb any digest (unchanged={same})")
    results.append({"mutation": "negative control: unrelated.py excluded",
                    "component_changed": [], "expected": None,
                    "eid_star_changed": not same, "ok": same})

    (ROOT / "verify/out/mutation_results.json").write_text(json.dumps(
        {"baseline": b["digests"], "baseline_eid_star": b["eid_star"], "cases": results},
        indent=2))
    print("\nwrote verify/out/mutation_results.json")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
