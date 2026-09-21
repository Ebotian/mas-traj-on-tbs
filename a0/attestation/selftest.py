#!/usr/bin/env python3
"""Self-test for the attestation producer and verifier.

Seven properties, each checked by execution:

  1. the producer's canonicalizer and the verifier's independently written one
     agree on a corpus of awkward payloads (including the real payload);
  2. `EID_execution` recomputes deterministically;
  3. the verifier's reimplementation of E*'s own source-digest scheme reproduces
     the value the frozen evaluator reports (`5ae97ad9...`);
  4. the verifier's reimplementation of the contract's EID* combination step
     reproduces the frozen `EID*`;
  5. a payload edited after the fact is rejected by Q1 (it does not recompute);
  6. a document whose `EID_semantic` is not the frozen value is rejected by Q2;
  7. a document with a module loaded from outside the declared sources is
     rejected by Q3.

The fixture is a real attestation produced by `attest.py`; it is generated on
demand if it is not already in `out/`.

    python selftest.py [--quick]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
OUT = HERE / "out"
FIXTURE = OUT / "attestation.c05_overlapping.full.json"
CANDIDATE = "a0/tasks/circle-packing/C_STAR/c05_overlapping"
PYTHON = sys.executable

sys.path.insert(0, str(HERE))
import attest_lib as lib  # noqa: E402
import verify_attestation as verifier  # noqa: E402


CORPUS = [
    {},
    {"a": 1, "b": [1, 2, 3], "c": {"d": None, "e": True, "f": False}},
    {"unicode": "修正 ✓ π", "escaped": "\u0000\u001f", "quote": '"\\\n\t"'},
    {"ints": [0, -1, 2**63, -(2**63)], "floats": [0.0, -0.0, 1e-300, 1.7976931348623157e308]},
    {"nested": [{"x": [{"y": "z"}]}], "empty_list": [], "empty_dict": {}},
]


def ensure_fixture(quick: bool) -> Path:
    if FIXTURE.is_file():
        return FIXTURE
    if quick:
        raise SystemExit(f"fixture missing: {FIXTURE} (run without --quick to generate it)")
    print(f"generating fixture with a real E* invocation on {CANDIDATE} ...")
    subprocess.run([PYTHON, str(HERE / "attest.py"), "--candidate", CANDIDATE], cwd=REPO_ROOT,
                   check=True)
    if not FIXTURE.is_file():
        raise SystemExit(f"attest.py did not produce {FIXTURE}")
    return FIXTURE


def check(name: str, ok, detail=None) -> dict:
    print(f"[{'ok  ' if ok else 'FAIL'}] {name}" + ("" if ok else f"  <- {detail}"))
    return {"name": name, "passed": bool(ok), "detail": None if ok else detail}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="selftest.py", description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="do not run E* to build the fixture")
    args = parser.parse_args(argv)

    results = []
    fixture = ensure_fixture(args.quick)
    document = json.loads(fixture.read_text(encoding="utf-8"))

    # 1. canonicalizers agree
    mismatch = []
    for index, payload in enumerate([*CORPUS, document["payload"]]):
        left = lib.canonical_json(payload)
        right = verifier.canonical_json(payload)
        if left != right:
            mismatch.append(index)
    results.append(check("the two canonicalizers agree on all payloads", not mismatch, mismatch))

    # 2. EID_execution recomputes, deterministically
    first = lib.eid_execution(document["payload"])
    second = lib.eid_execution(json.loads(json.dumps(document["payload"])))
    results.append(check("EID_execution recomputes deterministically", first == second,
                         (first, second)))
    results.append(check("EID_execution matches the document",
                         first == document["eid_execution"],
                         (first, document["eid_execution"])))
    results.append(check("the verifier's recomputation matches the producer's",
                         verifier.recompute_eid_execution(document["payload"]) == first))

    # 3. the verifier reproduces E*'s own source digest from declared records
    entries = json.loads(
        (REPO_ROOT / "a0/tasks/circle-packing/EID_INPUTS.json").read_text(encoding="utf-8")
    )["components"]["EvaluatorSource"]["canonical_material"]["records"]
    fake_records = [{"origin": record["path"], "file_sha256": record["sha256"],
                     "file_size": record["size"]} for record in entries]
    digest = verifier.e_star_self_reported_digest(fake_records)
    results.append(check("the verifier reproduces E*'s self-reported source digest",
                         digest == verifier.EXPECTED_SELF_REPORTED_SOURCE_SHA256, digest))

    # 4. the verifier reproduces the frozen EID* from the five components
    components = document["eid_semantic_components"]
    results.append(check("the verifier reproduces the frozen EID* from the components",
                         verifier.recompute_eid_star(components) == lib.FROZEN_EID_STAR,
                         verifier.recompute_eid_star(components)))

    # 5-7. fault injection: the verifier must reject each mutation
    def verify(document_variant):
        return verifier.verify(document_variant, declared_eid_star=None,
                              declared_eid_execution=None, repo_root=None)

    mutated = json.loads(json.dumps(document))
    mutated["payload"]["runtime"]["version"] = "9.9.9"
    report = verify(mutated)
    results.append(check("Q1 rejects a payload edited after the fact",
                         report.gate_failures("Q1") and not report.gate_failures("Q2")
                         and not report.gate_failures("Q3"),
                         [c["name"] for c in report.gate_failures("Q1")]))

    mutated = json.loads(json.dumps(document))
    mutated["eid_semantic"] = "0" * 64
    report = verify(mutated)
    results.append(check("Q2 rejects a semantic component that is not the frozen value",
                         report.gate_failures("Q2") and not report.gate_failures("Q1"),
                         [c["name"] for c in report.gate_failures("Q2")]))

    mutated = json.loads(json.dumps(document))
    mutated["payload"]["loaded_artifacts"]["foreign_modules"] = [
        {"name": "hashlib", "origin": "/tmp/shadow/hashlib.py", "origin_kind": "source",
         "sha256": "0" * 64, "size": 1, "loaded_by_harness_before_hook": False}
    ]
    report = verify(mutated)
    results.append(check("Q3 rejects a module loaded from outside the declared sources",
                         report.gate_failures("Q3")
                         and any("outside the declared sources" in c["name"]
                                 for c in report.gate_failures("Q3")),
                         [c["name"] for c in report.gate_failures("Q3")]))

    mutated = json.loads(json.dumps(document))
    mutated["payload"]["loaded_artifacts"]["evaluator_sources"][0]["bytecode_matches_source"] = False
    report = verify(mutated)
    results.append(check("Q3 rejects bytecode that is not a compilation of the declared source",
                         any("bytecode that ran matches" in c["name"]
                             for c in report.gate_failures("Q3")),
                         [c["name"] for c in report.gate_failures("Q3")]))

    # the untouched document must still pass everything
    report = verify(json.loads(json.dumps(document)))
    results.append(check("the untouched attestation passes all three verdicts",
                         not report.gate_failures("Q1") and not report.gate_failures("Q2")
                         and not report.gate_failures("Q3")))

    ok = all(item["passed"] for item in results)
    report_doc = {
        "schema": "a0.attestation.selftest/v1",
        "generated_by": "a0/attestation/selftest.py",
        "fixture": str(fixture.relative_to(REPO_ROOT)),
        "checks": results,
        "all_checks_passed": ok,
    }
    (OUT / "selftest_report.json").write_text(json.dumps(report_doc, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8")
    print(f"\nall checks passed: {ok}")
    print(f"wrote {OUT / 'selftest_report.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
