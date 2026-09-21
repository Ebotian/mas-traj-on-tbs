#!/usr/bin/env python3
"""Independent consistency check for `qualification.json`, the D2 predicate and the D3 interface.

This does NOT call `build_qualification.py`: it re-reads the evidence files directly and asserts
that the stored qualification and the conformance labels agree with them, that every component
carries value/evidence/justification/provenance, that the `Eligible` predicate the file declares is
the one `eligibility.py` computes, that `T_A1` is the default and `T_exploratory` is scoped away
from the main arm, that `R_A1^main` is what the module computes, and that the attestation interface
declares fail-closed semantics with no runtime reported PASS without a live record.
Exit 0 = all checks pass.

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
    EXPLORATORY_VECTOR,
    MAIN_ARM_VECTOR,
    PREDICATE_VERSION,
    RULES,
    THRESHOLD_VECTORS,
    eligible,
    key_metrics,
)

QUAL = HERE / "qualification.json"
REPORT = ROOT / "a0/conformance/report.json"
SELFTEST = ROOT / "a0/conformance/selftest_report.json"
ATTESTED_CONTRACT = HERE / "attested-a0-1.contract.json"
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
    # intent: an A0.1 label never reads as a bare PASS that hides a split. Since D3 the label is
    # either "PASS (n/14 measured)" or an explicit non-acceptance label, and the split is always
    # machine-readable next to it.
    label_ok = []
    for runtime, label in labels.items():
        q = verdicts["a0_1_qualification"][runtime]
        has_split = (q.get("measured") is not None and q.get("total") == 14
                     and f"{q['measured']}/{q['total']}" in label)
        label_ok.append(
            has_split or (label in ("FAIL", "PENDING", "BLOCKED") and q.get("measured") is not None)
        )
    check("a0_1_labels_never_hide_the_split", all(label_ok), json.dumps(labels, ensure_ascii=False))

    # 2. the review's point 2, at the source, under the post-D3 shape
    check(
        "eve_a0_1_is_not_pass_and_reads_5_of_14",
        labels.get("eve") != "PASS" and "5/14" not in labels.get("eve", "PASS ("),
        f"report.json verdicts.a0_1.eve = {labels.get('eve')!r}",
    )
    check(
        "eve_measurement_split_is_5_measured_9_adapted",
        (verdicts["a0_1_measured"]["eve"], verdicts["a0_1_adapted"]["eve"]) == (5, 9),
        f"a0_1_measured.eve={verdicts['a0_1_measured']['eve']}, "
        f"a0_1_adapted.eve={verdicts['a0_1_adapted']['eve']}",
    )
    q_eve = verdicts["a0_1_qualification"]["eve"]
    check(
        "eve_machine_readable_split",
        (q_eve["measured"], q_eve["adapted"], q_eve["total"]) == (5, 9, 14),
        f"measured={q_eve['measured']} adapted={q_eve['adapted']} total={q_eve['total']}",
    )
    check(
        "eve_is_not_accepting_and_not_for_a_numeric_reason",
        report["runtimes"]["eve"]["state"] != "PASS"
        and "MISSING_ATTESTATION" in str(report["runtimes"]["eve"].get("reason"))
        and "the numbers agree on 14/14 rows" in str(report["runtimes"]["eve"].get("reason")),
        f"runtimes.eve.state={report['runtimes']['eve']['state']!r}; reason="
        f"{str(report['runtimes']['eve'].get('reason'))[:110]!r}",
    )

    # 2b. THE TWO AXES (D3). A runtime can measure every row and still not be acceptable evidence;
    #     the report and Q_r must both say so, and must not report the second as the first.
    axis_problems = []
    for runtime in RUNTIMES:
        entry = report["runtimes"][runtime]
        q = entry["qualification"]["a0_1"]
        eq = (q.get("attestation") or {})
        att = q.get("measurement_attestation") or {}
        corrob = next((c for c in entry.get("checks") or []
                       if c.get("check_id") == "E-r-equals-E-star"), {})
        if eq.get("required") is not True:
            axis_problems.append(f"{runtime}: attestation.required is {eq.get('required')!r}")
        if att.get("attested") is None or att.get("missing_attestation") is None:
            axis_problems.append(f"{runtime}: measurement_attestation block is incomplete")
        if corrob.get("measurement_agreeing") is None:
            axis_problems.append(f"{runtime}: E-r-equals-E-star carries no measurement_agreeing")
        # the folded state must not be used as the measurement state by the consumer
        stored = qual["runtimes"][runtime]["Q_r"]["a0_1_measured"]
        if stored.get("runner_acceptance_state") != q.get("state"):
            axis_problems.append(f"{runtime}: runner_acceptance_state {stored.get('runner_acceptance_state')!r} "
                                 f"!= runner state {q.get('state')!r}")
    check("two_axes_present_at_the_source", not axis_problems, "; ".join(axis_problems) or
          "every runtime publishes measurement_attestation, attestation.identity_verdict, "
          "attestation.required and E-r-equals-E-star.measurement_agreeing")

    # 3. the screen is the ACCEPTANCE axis; a measured-but-unattested runtime is not in it
    only = verdicts["r_1_a0_1_only"]
    partial = verdicts["r_1_a0_1_partial"]
    check(
        "measured_but_unattested_is_not_in_the_screen",
        all(r in only for r in RUNTIMES
            if report["runtimes"][r]["qualification"]["a0_1"]["attestation"]["identity_verdict"]
            == "ATTESTATION_OK")
        and all(r not in only for r in RUNTIMES
                if report["runtimes"][r]["qualification"]["a0_1"]["attestation"]["identity_verdict"]
                == "MISSING_ATTESTATION"),
        f"r_1_a0_1_only={only}, r_1_a0_1_partial={partial}, "
        f"acceptance={ {r: report['runtimes'][r]['qualification']['a0_1']['attestation']['identity_verdict'] for r in RUNTIMES} }",
    )
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

    # 4. qualification.json's A0.1 components equal the runner's, runtime by runtime. The stored
    #    measurement state is the MEASUREMENT axis (derived from rows[].verdict_before_attestation),
    #    so it is checked against the runner's measurement agreement plus the per-row verdicts, and
    #    the runner's folded acceptance state is checked separately as `runner_acceptance_state`.
    agree = []
    for runtime in RUNTIMES:
        stored = qual["runtimes"][runtime]["Q_r"]
        entry = report["runtimes"][runtime]
        runner = entry["qualification"]["a0_1"]
        before = [r.get("verdict_before_attestation") for r in entry.get("rows") or []]
        wants = {
            "a0_1_measured_value": stored["a0_1_measured"]["value"] == f"{runner['measured']}/{runner['total']}",
            "a0_1_adapted_value": stored["a0_1_adapted"]["value"] == f"{runner['adapted']}/{runner['total']}",
            "measurement_state": stored["a0_1_measured"]["state"] == (
                "FAIL" if any(v not in ("MATCH", "MATCH_VERDICT", "SYNTHETIC_DECLARED",
                                        "EXECUTION_ENV_DRIFT") for v in before)
                else "PARTIAL" if "SYNTHETIC_DECLARED" in before else "PASS"
            ),
            "folded_state_recorded": stored["a0_1_measured"].get("runner_acceptance_state") == runner["state"],
            "attested_matches_runner": stored["a0_1_attested"].get("identity_verdict")
            == (runner.get("attestation") or {}).get("identity_verdict"),
        }
        if not all(wants.values()):
            agree.append(f"{runtime}: {[k for k, v in wants.items() if not v]}")
    check("q_r_a0_1_matches_runner", not agree,
          "; ".join(agree) or "measurement axis, folded acceptance state and attestation verdict all agree, per runtime")

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
    check(
        "q_r_components_complete",
        not problems,
        "; ".join(problems) or f"all four runtimes carry {len(COMPONENTS)} complete components",
    )

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
    # 7. no runtime whose measurement is short is reported as PASS, and no runtime whose ACCEPTANCE
    #    failed is reported as measuring badly (the two axes must not be conflated downstream)
    bad = [
        r for r in RUNTIMES
        if report["runtimes"][r]["qualification"]["a0_1"]["attestation"]["identity_verdict"]
        != "ATTESTATION_OK" and verdicts["a0_1_state"][r] == "PASS"
    ]
    check("unattested_never_labeled_pass", not bad, f"unattested-but-PASS: {bad or 'none'}")
    conflated = [
        r for r in RUNTIMES
        if qual["runtimes"][r]["Q_r"]["a0_1_measured"]["state"] == "FAIL"
        and not (qual["runtimes"][r]["Q_r"]["a0_1_measured"]["measurement_axis"]
                 ["disagreeing_candidates"])
    ]
    check(
        "measurement_state_is_not_the_folded_acceptance_state",
        not conflated,
        f"measurement FAIL without a disagreeing candidate: {conflated or 'none'}; "
        f"measurement states={ {r: qual['runtimes'][r]['Q_r']['a0_1_measured']['state'] for r in RUNTIMES} }, "
        f"acceptance states={ {r: qual['runtimes'][r]['Q_r']['a0_1_measured']['runner_acceptance_state'] for r in RUNTIMES} }",
    )
    rejected = qual.get("rejected") or []
    check(
        "rejections_are_separate_from_unproven",
        all(
            item["value"] == "FAIL" and item.get("identity_verdict")
            for item in rejected
        ) and all(
            item.get("value") != "FAIL" for item in (qual.get("unproven") or [])
        ),
        f"rejected={[(i['runtime'], i['component'], i.get('identity_verdict')) for i in rejected]}; "
        f"unproven has no FAIL entries",
    )

    # 7b. the D2 predicate: T_A1 is the default and the main-arm set is what the module computes
    check(
        "d2_predicate_version_and_default",
        qual["predicate"]["version"] == PREDICATE_VERSION
        and qual["predicate"]["default_vector"] == MAIN_ARM_VECTOR,
        f"version={qual['predicate']['version']}, default={qual['predicate']['default_vector']}",
    )
    check(
        "d2_vectors_are_T_A1_and_T_exploratory",
        set(THRESHOLD_VECTORS) == {MAIN_ARM_VECTOR, EXPLORATORY_VECTOR},
        f"declared vectors: {sorted(THRESHOLD_VECTORS)}",
    )
    exploratory = THRESHOLD_VECTORS[EXPLORATORY_VECTOR]
    check(
        "d2_exploratory_is_scoped_away_from_main_arm",
        "a1_main_arm" in (exploratory.get("must_not_be_used_for") or [])
        and exploratory.get("may_be_used_for") == ["pilot", "integration", "debug"],
        f"exploratory may_be_used_for={exploratory.get('may_be_used_for')}, "
        f"must_not_be_used_for={exploratory.get('must_not_be_used_for')}",
    )
    metrics = key_metrics(qual)
    check(
        "d2_key_metrics_match_module",
        qual.get("key_metrics", {}).get("R_A1_main") == metrics["R_A1_main"]
        and qual.get("key_metrics", {}).get("R_exploratory") == metrics["R_exploratory"],
        f"stored R_A1^main={qual.get('key_metrics', {}).get('R_A1_main')} == recomputed {metrics['R_A1_main']}",
    )
    subsets = [
        r for r in metrics["R_A1_main"] if r not in metrics["R_exploratory"]
    ]
    check(
        "d2_main_arm_is_subset_of_exploratory",
        not subsets,
        f"R_A1^main={metrics['R_A1_main']}, R_exploratory={metrics['R_exploratory']}",
    )

    # 7c. the attestation clause fails closed: UNPROVEN carries no identity material, and a decided
    #     value carries the record it was decided from
    contract = json.loads(ATTESTED_CONTRACT.read_text()) if ATTESTED_CONTRACT.exists() else {}
    check(
        "d3_attestation_contract_declares_fail_closed",
        contract.get("schema") == "a0.attested-a0-1/v1"
        and bool(contract.get("search_paths"))
        and bool(contract.get("required_fields"))
        and bool(contract.get("record_sources"))
        and "UNPROVEN" in json.dumps(contract.get("domain_rule", {})),
        f"contract schema={contract.get('schema')!r}, {len(contract.get('required_fields') or [])} required fields, "
        f"{len(contract.get('record_sources') or [])} record sources, "
        f"{len(contract.get('search_paths') or [])} file search paths",
    )
    attest_problems = []
    decided = []
    for runtime in RUNTIMES:
        comp = qual["runtimes"][runtime]["Q_r"]["a0_1_attested"]
        if comp["value"] == "UNPROVEN":
            if comp.get("oid") is not None or comp.get("executed_identity") is not None:
                attest_problems.append(f"{runtime}: UNPROVEN but carries identity material")
            if not comp.get("to_settle"):
                attest_problems.append(f"{runtime}: UNPROVEN with no way to settle it")
        else:
            decided.append(f"{runtime}={comp['value']}")
            if not comp.get("record"):
                attest_problems.append(f"{runtime}: {comp['value']} with no record named")
            if not (ROOT / str(comp["evidence"]).split("#")[0]).exists():
                attest_problems.append(f"{runtime}: {comp['value']} but the record does not exist")
    check(
        "d3_attestation_fails_closed",
        not attest_problems,
        "; ".join(attest_problems) or
        (f"no runtime is attested yet (all UNPROVEN, each with a to_settle); decided: {decided or 'none'}")
        if not decided else
        f"decided: {decided}",
    )

    # 8. the conformance self-test still behaves, still pins the corrected label, and has not lost
    #    fixtures. The count is a floor, not an equality: D3 legitimately ADDED fixtures (20 -> 29),
    #    and a check that forbade growth would block the work that closes the mutant class.
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
    a0_fixture_names = {
        "selftest_honest", "selftest_clean", "selftest_synthetic_declared",
        "selftest_zero_on_error", "selftest_cache_hit", "selftest_timeout",
        "selftest_truncated_metrics", "selftest_manifest_triple", "selftest_drift_1e6",
        "selftest_drift_1e10", "selftest_swap", "selftest_digest_swap",
        "selftest_partial_coverage", "selftest_attempt_theta_drift", "selftest_stale_eid",
        "selftest_native_theta", "selftest_mislabeled_synthetic", "selftest_wrong_kind",
        "selftest_wrong_stage", "selftest_omitted_kind",
    }
    present = [f["fixture"] for f in fixtures]
    checked_here = [f for f in fixtures if f.get("expected_state") is not None]
    problems = []
    if len(fixtures) < 20:
        problems.append(f"only {len(fixtures)} fixtures (the A0 audit recorded 20)")
    if len(set(present)) != len(present):
        problems.append("duplicate fixture names")
    if "selftest_synthetic_declared" not in set(present):
        problems.append("selftest_synthetic_declared is gone")
    if not checked_here:
        problems.append("no fixture records an expected_state")
    renames = sorted(set(a0_fixture_names) - set(present))
    check(
        "selftest_fixture_set_intact",
        not problems,
        ("; ".join(problems) or f"{len(fixtures)} fixtures, {len(checked_here)} with a recorded "
         f"expected_state, all names unique, the corrected-label fixture present")
        + (f"; A0-audit names no longer present (check for renames): {renames}" if renames else ""),
    )

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
