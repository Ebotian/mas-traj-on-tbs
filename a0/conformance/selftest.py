#!/usr/bin/env python3
"""Fault-injection self-test for the A0.1 conformance checker.

Drives `conformance.py run` over fixture adapters (`fixtures/adapters/`) and asserts the verdict
each one must receive. This is what makes the FAIL verdicts in `report.json` trustworthy: the
checker has been shown, by execution, to reject a synthetic EvE `failure_score(0.0)`, a Loreley
cache hit / timeout / truncation, a value drift just above epsilon (and to accept one just
below), a candidate swap, a digest swap, silent skipping, a manifest-class mismatch, an
undeclared native `theta_E`, and a stale `EID*`.

`selftest_honest` is the control: `fixtures/adapters/reference_adapter.py`, which really executes
`E*` on all 14 members of `C*` through the frozen CLI. If the control failed, a PASS anywhere else
would mean nothing.

Everything here is exercised **via a seam** (a fixture standing in for a runtime adapter); no real
runtime adapter exists yet in `a0/runtimes/`. See README.md.

    python3 selftest.py [--quick]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "adapters"
PY = sys.executable

HONEST = f"{PY} {FIXTURES / 'reference_adapter.py'}"


def deviant(mode: str) -> str:
    return f"{PY} {FIXTURES / 'deviant.py'} --mode {mode}"


# fixture -> what the checker must say. `findings` are required finding ids, `rows` required
# per-candidate verdicts, `failed_checks` required check ids that must be reported as failed.
EXPECTATIONS = {
    "selftest_honest": {
        "state": "PASS",
        "cmd": HONEST,
        "why": "control: a real E* invocation on all 14 members of C* must pass",
    },
    "selftest_clean": {
        "state": "PASS",
        "cmd": deviant("pass"),
        "why": "no fault injected; a checker that fails this is over-strict",
    },
    "selftest_zero_on_error": {
        "state": "FAIL",
        "cmd": deviant("zero_on_error"),
        "findings": ["FG-EVE-SYNTH"],
        "rows": {cid: "FALSE_GREEN_SYNTHETIC_ZERO" for cid in
                 ("c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import",
                  "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow")},
        "why": "EvE's failure_score(0.0) must never pass as a faithful E* execution (plan:551)",
    },
    "selftest_cache_hit": {
        "state": "FAIL",
        "cmd": deviant("cache_hit"),
        "findings": ["FG-LORELEY-CACHE"],
        "failed_checks": ["evidence-fresh-or-declared"],
        "why": "a cached number is not evidence that E* ran (plan:552)",
    },
    "selftest_timeout": {
        "state": "FAIL",
        "cmd": deviant("timeout"),
        "findings": ["FG-LORELEY-TIMEOUT"],
        "why": "a timeout-synthesised failure must not look like a measurement (plan:552)",
    },
    "selftest_truncated": {
        "state": "FAIL",
        "cmd": deviant("truncated"),
        "findings": ["FG-LORELEY-TRUNCATED", "FG-LORELEY-CAP"],
        "why": "metrics dropped at the 64-cap must not look like E*'s Outcome (plan:552)",
    },
    "selftest_drift_1e_6": {
        "state": "FAIL",
        "cmd": deviant("drift_1e_6"),
        "rows": {cid: "MISMATCH_VALUE" for cid in
                 ("c01_good_hex", "c02_baseline_upstream", "c03_mirror", "c04_near_tie", "c14_near_zero")},
        "failed_checks": ["E-r-equals-E-star"],
        "why": "1e-6 > epsilon = 1e-9",
    },
    "selftest_drift_1e_10": {
        "state": "PASS",
        "cmd": deviant("drift_1e_10"),
        "why": "1e-10 < epsilon: compares equal, so epsilon is enforced from both sides",
    },
    "selftest_swap_near_tie": {
        "state": "FAIL",
        "cmd": deviant("swap_near_tie"),
        "rows": {"c04_near_tie": "MISMATCH_VALUE"},
        "why": "the 1e-4 near-tie pair catches an adapter with a sloppy tolerance",
    },
    "selftest_digest_swap": {
        "state": "FAIL",
        "cmd": deviant("digest_swap"),
        "rows": {"c04_near_tie": "MISMATCH_DIGEST"},
        "why": "evaluating a different file (or stale state) must not pass as conformance",
    },
    "selftest_partial": {
        "state": "FAIL",
        "cmd": deviant("partial"),
        "failed_checks": ["candidate-coverage"],
        "why": "silently skipping 9 of 14 candidates is a FAIL, never a pass (plan:513)",
    },
    "selftest_manifest_triple": {
        "state": "FAIL",
        "cmd": deviant("manifest_triple"),
        "findings": ["FG-MANIFEST-TRIPLE"],
        "why": "granted class != commanded class is an A0.1 failure (plan:532-539, D16)",
    },
    "selftest_attempt_theta_drift": {
        "state": "FAIL",
        "cmd": deviant("attempt_theta_drift"),
        "findings": ["FG-ATTEMPT-THETA-DRIFT"],
        "why": "an attempt at fidelity=fast while the run declares full is not the same theta_E (plan:518)",
    },
    "selftest_stale_eid": {
        "state": "FAIL",
        "cmd": deviant("stale_eid"),
        "failed_checks": ["EID-star-verbatim", "EID-r-derives-from-EID-star"],
        "why": "the superseded EID* (fac50fc4...) must not be accepted",
    },
    "selftest_native_theta": {
        "state": "FAIL",
        "cmd": deviant("native_theta"),
        "failed_checks": ["theta-E-identical"],
        "why": "a missing theta_E parameter must be declared with the fixed equivalent value (plan:518)",
    },
    "selftest_synthetic_declared": {
        "state": "PASS",
        "cmd": deviant("synthetic_declared"),
        "rows": {cid: "SYNTHETIC_DECLARED" for cid in
                 ("c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import",
                  "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow")},
        "why": "an adapter that hits the EvE trap, declares it and does not count it as a match must PASS "
               "-- being honest about the trap is not a conformance failure",
    },
    "selftest_synthetic_mislabeled": {
        "state": "FAIL",
        "cmd": deviant("synthetic_mislabeled"),
        "findings": ["FG-EVE-SYNTH"],
        "rows": {cid: "FALSE_GREEN_SYNTHETIC_ZERO" for cid in ("c05_overlapping", "c10_raises")},
        "why": "a synthesised 0.0 presented on a row labelled as a match must FAIL even though the synthesis "
               "is nominally declared (audit:206: a wrong label must not survive)",
    },
    "selftest_wrong_failure_kind": {
        "state": "FAIL",
        "cmd": deviant("wrong_failure_kind"),
        "findings": ["FG-FAILURE-KIND"],
        "rows": {cid: "MISMATCH_FAILURE_KIND" for cid in
                 ("c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import",
                  "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow")},
        "failed_checks": ["E-r-failure-kind"],
        "why": "adapter_contract.md §4.3.5 compares a non-ok candidate on verdict AND failure.kind; a "
               "truthful status with a lying failure.kind must FAIL (audit R1)",
    },
    "selftest_wrong_failure_stage": {
        "state": "FAIL",
        "cmd": deviant("wrong_failure_stage"),
        "findings": ["FG-FAILURE-STAGE"],
        "rows": {cid: "MISMATCH_FAILURE_STAGE" for cid in
                 ("c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import",
                  "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow")},
        "failed_checks": ["E-r-failure-kind"],
        "why": "the frozen §5.3 table maps E*'s failure.kind to one failure_stage; a row that declares a "
               "different stage would make plan:577's counts non-joinable and must FAIL (audit R1)",
    },
    "selftest_omit_failure_kind": {
        "state": "FAIL",
        "cmd": deviant("omit_failure_kind"),
        "findings": ["FG-FAILURE-KIND-UNDECLARED"],
        "rows": {cid: "UNDECLARED_FAILURE_KIND" for cid in
                 ("c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import",
                  "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow")},
        "failed_checks": ["E-r-failure-kind"],
        "why": "the honest fixture with failure.kind omitted: there is no lie to catch, but the "
               "(verdict, failure.kind) surface adapter_contract.md §4.3.5 requires is absent, so a "
               "vacuous PASS is a hole in the checker (audit: second half of R1)",
    },
}


def integrity_abort_check() -> dict:
    """Exercise `adapter_contract.md` exit code 4 without touching C*.

    Builds a tampered copy of the C* manifest outside the task tree (absolute `path` entries
    point back at the real candidate directories) and runs the runner against it.
    """
    real_manifest = HERE.parent / "tasks" / "circle-packing" / "C_STAR" / "manifest.json"
    root = real_manifest.parent.resolve()
    doc = json.loads(real_manifest.read_text())
    for cand in doc["candidates"]:
        cand["path"] = str(root / cand["path"])
    doc["candidates"][3]["solution_sha256"] = "0" * 64
    with tempfile.TemporaryDirectory(prefix="a0-conformance-integrity-") as tmp:
        manifest = Path(tmp) / "manifest.json"
        manifest.write_text(json.dumps(doc, indent=1))
        report = Path(tmp) / "report.json"
        proc = subprocess.run(
            [PY, str(HERE / "conformance.py"), "run", "--manifest", str(manifest), "--no-controls",
             "--out", str(report)],
            capture_output=True, text=True, cwd=HERE,
        )
        payload = json.loads(report.read_text()) if report.exists() else {}
    problems = [p["candidate_id"] for p in payload.get("integrity", {}).get("problems", [])]
    ok = proc.returncode == 4 and problems == ["c04_near_tie"] and payload.get("integrity", {}).get("ok") is False
    return {
        "check": "candidate-set integrity abort (exit 4)",
        "exit_code": proc.returncode,
        "expected_exit_code": 4,
        "flagged_candidates": problems,
        "stderr_head": proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "",
        "ok": ok,
    }


def build_command(subset=None):
    names = subset or list(EXPECTATIONS)
    argv = [PY, str(HERE / "conformance.py"), "run",
            "--runtimes", ",".join(names),
            "--out", str(HERE / "selftest_runner_report.json")]
    for name in names:
        argv += ["--adapter", f"{name}={EXPECTATIONS[name]['cmd']}"]
    return argv


def check_expectation(entry: dict, expec: dict):
    problems = []
    if entry.get("state") != expec["state"]:
        problems.append(f"state {entry.get('state')} != expected {expec['state']} ({entry.get('reason')})")
    found = {f["finding_id"] for f in entry.get("false_green_findings") or []}
    for want in expec.get("findings", []):
        if want not in found:
            problems.append(f"missing finding {want} (saw {sorted(found) or 'none'})")
    verdicts = {r["candidate_id"]: r["verdict"] for r in entry.get("rows") or []}
    for cid, want in (expec.get("rows") or {}).items():
        if verdicts.get(cid) != want:
            problems.append(f"{cid}: verdict {verdicts.get(cid)!r} != expected {want!r}")
    failed = {c["check_id"] for c in entry.get("checks") or [] if not c["ok"]}
    for want in expec.get("failed_checks", []):
        if want not in failed:
            problems.append(f"check {want} was not reported as failed (failed: {sorted(failed) or 'none'})")
    if expec["state"] == "PASS" and entry.get("checks") and failed:
        problems.append(f"expected no failed checks, saw {sorted(failed)}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="selftest.py")
    parser.add_argument("--only", default=None, help="comma-separated subset of fixtures")
    parser.add_argument("--quick", action="store_true", help="skip the honest-adapter control")
    parser.add_argument("--keep-fixture-runs", action="store_true",
                        help="do not delete the fixture scratch root (its path is printed)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    # F6: the fixtures are test doubles and must not create directories in the study tree. They
    # write only under this root (fixture_common.scratch_root), which is under the system temp
    # directory and is removed when the selftest ends unless --keep-fixture-runs is given.
    scratch = Path(tempfile.mkdtemp(prefix="a0-conformance-selftest-"))
    os.environ["A0_FIXTURE_RUN_ROOT"] = str(scratch)

    try:
        return _run(args, scratch)
    finally:
        if args.keep_fixture_runs:
            print(f"fixture runs kept under {scratch}")
        else:
            shutil.rmtree(scratch, ignore_errors=True)


def _run(args, scratch: Path) -> int:
    subset = args.only.split(",") if args.only else [n for n in EXPECTATIONS if not (args.quick and n == "selftest_honest")]
    cmd = build_command(subset)
    print("running:", " ".join(cmd[:8]), "...")
    print(f"fixture scratch root: {scratch}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    sys.stdout.write(proc.stdout)
    if proc.stderr.strip():
        sys.stderr.write(proc.stderr)
    report_path = HERE / "selftest_runner_report.json"
    if not report_path.exists():
        print("selftest: no report produced", file=sys.stderr)
        return 10
    report = json.loads(report_path.read_text())

    print()
    print("integrity abort check ...", end=" ")
    integrity_abort = integrity_abort_check()
    print(f"exit {integrity_abort['exit_code']} (expected 4), flagged {integrity_abort['flagged_candidates']}"
          f" -> {'ok' if integrity_abort['ok'] else 'MISMATCH'}")
    ok_all = integrity_abort["ok"]

    results = []
    for name in subset:
        entry = report["runtimes"].get(name, {})
        problems = check_expectation(entry, EXPECTATIONS[name])
        ok_all = ok_all and not problems
        results.append(
            {
                "fixture": name,
                "why": EXPECTATIONS[name]["why"],
                "injected_fault": EXPECTATIONS[name]["cmd"].split("--mode")[-1].strip() or "none (honest E* execution)",
                "expected_state": EXPECTATIONS[name]["state"],
                "actual_state": entry.get("state"),
                "actual_reason": entry.get("reason"),
                "findings": [f["finding_id"] for f in entry.get("false_green_findings") or []],
                "failed_checks": [c["check_id"] for c in entry.get("checks") or [] if not c["ok"]],
                "row_verdicts": {r["candidate_id"]: r["verdict"] for r in entry.get("rows") or []},
                "behaved_as_expected": not problems,
                "problems": problems,
            }
        )

    doc = {
        "schema": "a0.conformance.selftest/v1",
        "generated_by": "a0/conformance/selftest.py",
        "command": cmd,
        "runner_report": str(report_path),
        "runner_exit_code": proc.returncode,
        "all_fixtures_behaved": ok_all,
        "integrity_abort": integrity_abort,
        "fixtures": results,
    }
    (HERE / "selftest_report.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    print()
    print(f"{'fixture':<32} {'injected fault':<22} {'expected':<8} {'actual':<8} verdict")
    for row in results:
        print(
            f"{row['fixture']:<32} {row['injected_fault'][:20]:<22} {row['expected_state']:<8} "
            f"{str(row['actual_state']):<8} {'ok' if row['behaved_as_expected'] else 'MISMATCH'}"
        )
        for problem in row["problems"]:
            print(f"    ! {problem}")
    print()
    print(f"all fixtures behaved as expected: {ok_all}")
    print(f"written: {HERE / 'selftest_report.json'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
