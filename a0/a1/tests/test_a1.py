"""Unit-level invariants of the A1 harness (the parts a probe is too coarse for)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "a0" / "runtimes" / "kapso"))

from a0.a1.blocks import BlockError, BlockScheduler  # noqa: E402
from a0.a1.budget import Budget, BudgetEnforcer, BudgetError, read_meter_ledger  # noqa: E402
from a0.a1.causal import AID, CID, CampaignID, Factor, audit  # noqa: E402
from a0.a1.eval_service import HarnessEvalService, _apply_override, _value_at  # noqa: E402
from a0_adapter.harness_manifest import (  # noqa: E402
    HarnessManifestError,
    amend_evaluation_output,
    class_triple,
    manifest_line,
)


def _row(campaign_id="C", arm_id="A", *, ceq=None, unmetered=None, **usage):
    return {
        "schema": "a0.meter.call/v1", "campaign_id": campaign_id, "arm_id": arm_id,
        "ts": "t", "provider": "deepseek", "endpoint": "e", "model_requested": "deepseek-flash",
        "model_reported": "deepseek-flash", "provider_request_id": "p", "stream": False,
        "usage": (usage or None) if unmetered is None else None,
        "ceq": ceq, "unmetered": bool(unmetered), "reason": unmetered,
    }


def _ledger(tmp_path: Path, rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "ledger.jsonl"
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CampaignID and the causal-role rule
# ---------------------------------------------------------------------------
def test_campaign_id_is_the_ordered_four_tuple():
    campaign = CampaignID("T", "B0", "A1", "R0")
    assert campaign.key == "T/B0/A1/R0"
    assert campaign.as_dict()["campaign_key"] == campaign.key


def test_an_undeclared_object_fails_the_audit():
    cid = CID("T")
    cid.add(Factor("shared", "cid", sha256="aa" * 32))
    aid = AID(CampaignID("T", "B0", "A1", "R0"))
    aid.add(Factor("arm.thing", "aid_r", value=1))
    assert audit(cid, [aid], observed={"shared": "sha256:" + "aa" * 32})["verdict"] == "pass"
    dirty = audit(cid, [aid], observed={"shared": "sha256:" + "aa" * 32, "sneaky": "value:1"})
    assert dirty["verdict"] == "fail"
    assert dirty["problems"][0]["kind"] == "uncontrolled"


def test_a_cid_factor_that_drifted_fails_the_audit():
    cid = CID("T")
    cid.add(Factor("shared", "cid", sha256="aa" * 32))
    aid = AID(CampaignID("T", "B0", "A1", "R0"))
    result = audit(cid, [aid], observed={"shared": "sha256:" + "bb" * 32})
    assert result["verdict"] == "fail"


# ---------------------------------------------------------------------------
# the budget enforcer
# ---------------------------------------------------------------------------
def test_budget_reads_ceq_and_ignores_other_campaigns(tmp_path):
    path = _ledger(tmp_path, [_row(ceq=100, miss=100), _row(campaign_id="C2", ceq=999, miss=999)])
    summary = read_meter_ledger(path, campaign_id="C")
    assert summary["ceq"] == 100 and summary["rows"] == 1


def test_a_gap_row_stops_the_campaign_but_a_refusal_does_not(tmp_path):
    budget = Budget(T_wall_sec=10, N_eval_max=5, CEq_max=10_000)
    gap = BudgetEnforcer(budget=budget,
                         meter_ledger=_ledger(tmp_path, [_row(ceq=10, miss=10),
                                                         _row(unmetered="no_usage_field_in_response")]),
                         harness_eval_ledger=tmp_path / "h.jsonl", campaign_id="C", arm_id="A")
    assert gap.check()["stopped_because"] == "budget_exhausted:unmetered_model_call"
    refusal = BudgetEnforcer(budget=budget,
                             meter_ledger=_ledger(tmp_path / "r",
                                                  [_row(ceq=10, miss=10),
                                                   _row(unmetered="non_allowlisted_host:x")]),
                             harness_eval_ledger=tmp_path / "h.jsonl", campaign_id="C", arm_id="A")
    assert refusal.check()["within"] is True
    assert refusal.check()["observed"]["refused_rows"] == 1


def test_an_absent_ledger_is_refused_not_zeroed(tmp_path):
    with pytest.raises(BudgetError):
        read_meter_ledger(tmp_path / "missing.jsonl", campaign_id="C")


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------
def test_the_plan_is_a_reproducible_complete_block_design():
    first = BlockScheduler.build(task_id="T", arms=["A", "B", "C"], blocks=6, replicates=1, seed=7)
    second = BlockScheduler.build(task_id="T", arms=["A", "B", "C"], blocks=6, replicates=1, seed=7)
    assert first.schedule() == second.schedule()
    for block in first.blocks:
        assert sorted(key.split("/")[2] for key in block.order) == ["A", "B", "C"]


def test_an_outage_invalidates_the_whole_block():
    scheduler = BlockScheduler.build(task_id="T", arms=["A", "B"], blocks=2, replicates=1, seed=1)
    block = scheduler.blocks[0]
    scheduler.complete(block.order[0], evidence={})
    scheduler.outage(block.order[1], reason="relay_down")
    assert scheduler.status()["usable_blocks"] == []
    assert all(record.status in ("outage", "invalidated") for record in block.records.values())
    with pytest.raises(BlockError):
        scheduler.complete(block.order[0])


# ---------------------------------------------------------------------------
# the harness's own outcome authoring
# ---------------------------------------------------------------------------
def test_an_override_authors_the_outcome_and_keeps_the_true_value():
    outcome = {"status": "ok", "cut_edges": 207, "edges_total": 512, "canonical_digest": "x",
               "cut_fraction": "0.4"}
    handed = _apply_override(outcome, "cut_edges", 9999)
    assert handed["cut_edges"] == 9999
    assert handed["harness_authored_overrides"] == {"cut_edges": 9999, "was": 207}
    assert "canonical_digest" not in handed
    assert _value_at(handed, "cut_edges") == 9999


def test_a_field_path_reads_the_plumbing_shape_too():
    outcome = {"status": "ok", "fields": {"sum_radii": 2.5}, "objective": {"value": 2.5}}
    assert _value_at(outcome, "fields.sum_radii") == 2.5
    assert _value_at(outcome, "cut_edges") is None


def test_the_service_refuses_an_unknown_evaluator(tmp_path):
    with pytest.raises(Exception):
        HarnessEvalService(root=tmp_path, evaluator="not-an-evaluator")


# ---------------------------------------------------------------------------
# KAPSO's manifest contract
# ---------------------------------------------------------------------------
def _strategy(fidelity="full", fraction=1.0, seed=1337):
    return SimpleNamespace(
        fidelity_decision=SimpleNamespace(eval_fidelity=fidelity, eval_fraction=fraction),
        registered_subsample_seed=seed,
    )


def test_the_class_triple_comes_from_the_runtime():
    assert class_triple(_strategy("fast", 0.15, 4242))["fidelity"] == "fast"
    assert class_triple(_strategy("fast", 0.15, 4242))["fraction"] == 0.15
    assert class_triple(_strategy("fast", 0.15, 4242))["seed"] == 4242


def test_a_strategy_without_a_grant_is_refused_rather_than_guessed():
    with pytest.raises(HarnessManifestError):
        class_triple(SimpleNamespace(registered_subsample_seed=1337))


def test_the_manifest_line_carries_the_item_counts_and_the_provenance():
    line = manifest_line(strategy=_strategy("fast", 0.15, 4242), score=1.5)
    payload = json.loads(line.split(" ", 1)[1])
    assert payload["items"] == 1 and payload["total_items"] == 1
    assert payload["harness_supplied"] is True
    assert payload["fidelity"] == "fast" and payload["seed"] == 4242


def test_the_harness_line_is_appended_so_it_is_the_last_one():
    node = SimpleNamespace(evaluation_output="session line\nKAPSO_EVAL_MANIFEST {\"score\": 9.0}\n")
    amend_evaluation_output(node, "KAPSO_EVAL_MANIFEST {\"score\": 2.5}")
    last = node.evaluation_output.strip().splitlines()[-1]
    assert json.loads(last.split(" ", 1)[1])["score"] == 2.5
