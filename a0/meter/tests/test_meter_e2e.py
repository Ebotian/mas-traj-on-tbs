"""End-to-end tests: the proxy, the allowlist, streaming, attribution and fail-closed behaviour.

The heavy lifting is done by `selftest.py`, which drives a real proxy over real sockets against a
local fake upstream (no model, no spend). This module runs it and asserts every check passed, so
`pytest` is a single command a third party can run to reproduce the whole result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
METER = os.path.dirname(HERE)
SELFTEST = os.path.join(METER, "selftest.py")


@pytest.fixture(scope="module")
def selftest_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("meter-evidence")
    work = tmp_path_factory.mktemp("meter-work")
    proc = subprocess.run([sys.executable, SELFTEST, "--out", str(out), "--work", str(work)],
                          capture_output=True, text=True, timeout=600, cwd=METER)
    checks_path = out / "checks.json"
    payload = json.loads(checks_path.read_text()) if checks_path.exists() else None
    return {"proc": proc, "out": str(out), "checks": payload}


def test_selftest_exits_zero(selftest_run):
    proc = selftest_run["proc"]
    if proc.returncode != 0:
        print(proc.stdout[-8000:])
        print(proc.stderr[-4000:])
    assert proc.returncode == 0, "selftest reported failures"


def test_every_named_check_passed(selftest_run):
    payload = selftest_run["checks"]
    assert payload is not None, "selftest wrote no checks.json"
    failed = [c for c in payload["checks"] if not c["ok"]]
    assert not failed, failed
    assert payload["passed"] == payload["total"] >= 45


def test_ledger_verifier_agrees_on_the_real_ledger(selftest_run):
    ledger = os.path.join(selftest_run["out"], "ledger.jsonl")
    proc = subprocess.run([sys.executable, os.path.join(METER, "verify_ledger.py"), ledger,
                           "--json"], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["failures"] == []
    assert summary["metered"] > 0 and summary["unmetered"] > 0
    assert summary["ceq_total"] > 0


def test_no_two_rows_share_a_usage_object_that_is_none_but_scored(selftest_run):
    ledger = os.path.join(selftest_run["out"], "ledger.jsonl")
    rows = [json.loads(line) for line in open(ledger, encoding="utf-8") if line.strip()]
    for row in rows:
        if row["unmetered"]:
            assert row["ceq"] is None and row["usage"] is None and row["reason"]
        else:
            assert row["ceq"] == (row["usage"]["prompt_cache_miss_tokens"]
                                  + (row["usage"]["prompt_cache_hit_tokens"] * 2) // 100
                                  + 4 * row["usage"]["completion_tokens"])


def test_both_campaigns_appear_in_the_ledger(selftest_run):
    ledger = os.path.join(selftest_run["out"], "ledger.jsonl")
    rows = [json.loads(line) for line in open(ledger, encoding="utf-8") if line.strip()]
    pairs = {(row["campaign_id"], row["arm_id"]) for row in rows}
    assert ("C_0001", "A_base") in pairs
    assert ("C_0002", "A_pc") in pairs
    # Attribution is one-to-one: no arm ever appears under the wrong campaign.
    for campaign, arm in pairs:
        assert (campaign, arm) in {("C_0001", "A_base"), ("C_0002", "A_pc")}


def test_evidence_is_reproducible_and_complete(selftest_run):
    for name in ("ledger.jsonl", "events.jsonl", "upstream.log.jsonl", "aid.json",
                 "highlights.json", "checks.json", "report.txt"):
        assert os.path.exists(os.path.join(selftest_run["out"], name)), name
