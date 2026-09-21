#!/usr/bin/env python3
"""Independent consistency check for `qualification.json` and the corrected conformance labels.

This does NOT call `build_qualification.py`: it re-reads the evidence files directly and asserts
that the stored qualification and the conformance labels agree with them, that every component
carries value/evidence/justification/provenance, and that the `Eligible` predicate the file
declares is the one `eligibility.py` computes. Exit 0 = all checks pass.

    python3 verify_qualification.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from eligibility import (  # noqa: E402
    COMPONENTS,
    RULES,
    THRESHOLD_VECTORS,
    eligible,
)

QUAL = HERE / "qualification.json"
REPORT = ROOT / "a0/conformance/report.json"
SELFTEST = ROOT / "a0/conformance/selftest_report.json"
RUNTIMES = ("simpleloop", "kapso", "eve", "loreley")

results = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append({"check": name, "ok": bool(ok), "detail": detail})


def main() -> int:
    qual = json.loads(QUAL.read_text())
    report = json.loads(REPORT.read_text())
    verdicts = report["verdicts"]

    # 1. the A0.1 label never reads as a bare PASS: every one carries its measured split
    labels = verdicts["a0_1"]
    check(
        "a0_1_labels_not_bare",
        all(isinstance(v, str) and "measured" in v for v in labels.values()),
        json.dumps(labels, ensure_ascii=False),
    )

    # 2. the review's point 2, at the source
    check(
        "eve_a0_1_is_partial_5_of_14",
        labels.get("eve", "").startswith("PARTIAL") and "5/14 measured" in labels.get("eve", ""),
        f"report.json verdicts.a0_1.eve = {labels.get('eve')!r}",
    )
    check(
        "eve_runtime_state_partial",
        report["runtimes"]["eve"]["state"] == "PARTIAL",
        f"runtimes.eve.state = {report['runtimes']['eve']['state']!r}",
    )
    q_eve = verdicts["a0_1_qualification"]["eve"]
    check(
        "eve_machine_readable_split",
        (q_eve["measured"], q_eve["adapted"], q_eve["total"]) == (5, 9, 14),
        f"measured={q_eve['measured']} adapted={q_eve['adapted']} total={q_eve['total']}",
    )

    # 3. a partial runtime is not in the A0.1 screen set, and the full ones are
    only = verdicts["r_1_a0_1_only"]
    partial = verdicts["r_1_a0_1_partial"]
    check("partial_excluded_from_screen", "eve" not in only and "eve" in partial,
          f"r_1_a0_1_only={only}, r_1_a0_1_partial={partial}")
    check(
        "screen_has_at_least_one",
        len(only) >= 1,
        f"|r_1_a0_1_only| = {len(only)} ({only})",
    )
    check(
        "screen_is_not_qualification",
        "SCREEN" in (verdicts.get("screen_vs_qualification") or "")
        and "Eligible" in (verdicts.get("screen_vs_qualification") or ""),
        "verdicts.screen_vs_qualification names the screen and the predicate separately",
    )

    # 4. qualification.json's A0.1 components equal the runner's, runtime by runtime
    agree = []
    for runtime in RUNTIMES:
        stored = qual["runtimes"][runtime]["Q_r"]
        runner = report["runtimes"][runtime]["qualification"]["a0_1"]
        agree.append(
            stored["a0_1_measured"]["value"] == f"{runner['measured']}/{runner['total']}"
            and stored["a0_1_adapted"]["value"] == f"{runner['adapted']}/{runner['total']}"
            and stored["a0_1_measured"]["state"] == runner["state"]
        )
    check("q_r_a0_1_matches_runner", all(agree), f"per-runtime agreement: {agree}")

    # 5. every component of every Q_r is complete and its evidence path exists
    problems = []
    for runtime in RUNTIMES:
        q_r = qual["runtimes"][runtime]["Q_r"]
        missing = [c for c in COMPONENTS if c not in q_r]
        if missing:
            problems.append(f"{runtime}: missing {missing}")
        for name, comp in q_r.items():
            for key in ("value", "evidence", "justification", "provenance"):
                if comp.get(key) in (None, "", []):
                    problems.append(f"{runtime}.{name}: no {key}")
            if comp.get("provenance") not in qual["provenance_classes"]:
                problems.append(f"{runtime}.{name}: provenance {comp.get('provenance')!r} is not declared")
            paths = comp["evidence"] if isinstance(comp["evidence"], list) else [comp["evidence"]]
            for spec in paths:
                path = (ROOT / spec.split("#")[0])
                if not path.exists():
                    problems.append(f"{runtime}.{name}: evidence path does not exist: {spec}")
    check("q_r_components_complete", not problems, "; ".join(problems) or "all four runtimes carry 5 complete components")

    # 6. the predicate in the file is the predicate the module computes, under every vector
    drift = []
    for vector in THRESHOLD_VECTORS:
        for runtime in RUNTIMES:
            stored = qual["evaluation"][vector][runtime]
            recomputed = eligible(qual["runtimes"][runtime]["Q_r"], vector)
            if stored["eligible"] != recomputed["eligible"] or stored["failed_rules"] != recomputed["failed_rules"]:
                drift.append(f"{vector}/{runtime}: {stored['failed_rules']} != {recomputed['failed_rules']}")
        stored_set = qual["eligible_set"][vector]
        recomputed_set = sorted(
            r for r in RUNTIMES if eligible(qual["runtimes"][r]["Q_r"], vector)["eligible"]
        )
        if stored_set != recomputed_set:
            drift.append(f"{vector}: eligible_set {stored_set} != {recomputed_set}")
    check("predicate_evaluation_matches_module", not drift, "; ".join(drift) or
          f"{len(THRESHOLD_VECTORS)} threshold vectors recomputed identically")
    check("predicate_rules_match_module", qual["predicate"]["rules"] == RULES,
          f"{len(RULES)} rules declared in both")

    # 7. no runtime with a PARTIAL A0.1 is ever reported as fully measured
    bad = [
        r for r in RUNTIMES
        if report["runtimes"][r]["state"] == "PARTIAL"
        and "PARTIAL" not in verdicts["a0_1"][r]
    ]
    check("partial_never_labeled_pass", not bad, f"partial-but-not-labelled: {bad or 'none'}")

    # 8. the 20-fixture self-test still behaves, and it pins the corrected label
    selftest = json.loads(SELFTEST.read_text()) if SELFTEST.exists() else {}
    fixtures = selftest.get("fixtures") or []
    declared = selftest.get("all_fixtures_behaved")
    syn = next((f for f in fixtures if f["fixture"] == "selftest_synthetic_declared"), None)
    check("selftest_all_fixtures_behaved", bool(declared), f"all_fixtures_behaved={declared}")
    check(
        "selftest_pins_partial_label",
        bool(syn) and syn["expected_state"] == "PARTIAL" and syn["actual_state"] == "PARTIAL"
        and (syn.get("a0_1_qualification") or {}).get("measured") == 5,
        f"selftest_synthetic_declared: {json.dumps(syn, ensure_ascii=False)[:200] if syn else 'absent'}",
    )
    check("selftest_fixture_count", len(fixtures) == 20, f"{len(fixtures)} fixtures recorded")

    width = max(len(r["check"]) for r in results)
    print(f"verify_qualification.py: {len(results)} checks over {QUAL.name}")
    print()
    for entry in results:
        print(f"  {'PASS' if entry['ok'] else 'FAIL'}  {entry['check']:<{width}}  {entry['detail']}")
    failed = [r for r in results if not r["ok"]]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks pass")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
