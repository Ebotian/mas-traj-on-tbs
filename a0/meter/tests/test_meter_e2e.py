"""End-to-end tests: the proxy, the allowlist, streaming, attribution and fail-closed behaviour.

The heavy lifting is done by `selftest.py`, which drives a real proxy over real sockets against a
local fake upstream (no model, no spend). This module runs it and asserts every check passed, so
`pytest` is a single command a third party can run to reproduce the whole result.
"""

from __future__ import annotations

import hashlib
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
    assert payload["passed"] == payload["total"] >= 65


def test_the_request_framing_checks_are_present_and_not_vacuous(selftest_run):
    """The framing checks are the ones that must not be droppable.

    They are named here so a future edit cannot quietly delete the only request-side assertions in
    the suite -- the same blindness that let an unframed body pass 55/55 checks.
    """
    payload = selftest_run["checks"]
    names = {c["name"]: c for c in payload["checks"]}
    for name in [n for n in names if n.startswith(("S18", "S19"))]:
        assert names[name]["ok"], names[name]
    expected_prefixes = ["S18a", "S18b", "S18c", "S18d", "S18e", "S18f", "S18g",
                         "S19a", "S19b", "S19c"]
    for prefix in expected_prefixes:
        assert any(name.startswith(prefix) for name in names), \
            "selftest lost the %s framing check" % prefix
    # The evidence must say which revision it tested.
    meter_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(meter_dir, "meter_proxy.py"), "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    assert payload["proxy_sha256"] == digest, "checks.json does not describe this proxy"


def test_the_unparseable_error_labelling_checks_are_present_and_not_vacuous(selftest_run):
    """A non-2xx whose body is not JSON must name its status, and the 2xx reasons stay distinct.

    Named here so a future edit cannot quietly drop the checks that pin the label, the way the
    framing checks are named above. `report.txt` is read as well, because the point of these
    checks is the *detail* -- the reason string actually booked.
    """
    payload = selftest_run["checks"]
    names = {c["name"]: c for c in payload["checks"]}
    expected = {
        "S13b": "upstream_http_502_no_usage",
        "S13c": "upstream_http_429_no_usage",
        "S13f": "upstream_http_302_no_usage",
        "S13d": "unparseable_response_body",
        "S13e": "empty_response_body",
    }
    for prefix, reason in expected.items():
        matches = [c for name, c in names.items() if name.startswith(prefix)]
        assert matches, "selftest lost the %s check" % prefix
        assert matches[0]["ok"], matches[0]
        assert reason in matches[0]["detail"], matches[0]["detail"]
    report = open(os.path.join(selftest_run["out"], "report.txt"), encoding="utf-8").read()
    assert "S13b" in report and "upstream_http_502_no_usage" in report


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
