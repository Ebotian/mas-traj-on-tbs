#!/usr/bin/env python3
"""A1 skeleton dry-run: identity, causal audit, budget, blocks, campaign preflight.

No model call, no `E*` run against a candidate and no campaign is started. What
is executed is every *decision* the skeleton makes, on inputs that are either the
repository's real artifacts (identity, declarations) or clearly labelled
synthetic ledgers (the budget cases — a ledger with a usage gap cannot be
produced without spending money, so it is constructed, and said so).

    python3 a0/a1/probes/skeleton_dryrun.py --out-dir /tmp/a1/skeleton-dryrun
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from a0.a1.blocks import BlockError, BlockScheduler  # noqa: E402
from a0.a1.budget import Budget, BudgetEnforcer, BudgetError, read_meter_ledger  # noqa: E402
from a0.a1.causal import AID, CID, CampaignID, Factor, audit  # noqa: E402
from a0.a1.declaration import ARMS, build as build_declarations  # noqa: E402
from a0.a1.eval_service import EVALUATORS  # noqa: E402
from a0.a1.skeleton import A1Campaign, ArmSpec  # noqa: E402


def meter_row(campaign_id: str, arm_id: str, *, ceq=None, unmetered=None,
              miss=0, hit=0, completion=0) -> dict:
    return {
        "schema": "a0.meter.call/v1",
        "campaign_id": campaign_id,
        "arm_id": arm_id,
        "ts": "2026-09-22T00:00:00+08:00",
        "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "model_requested": "deepseek-flash",
        "model_reported": "deepseek-flash",
        "provider_request_id": "synthetic",
        "stream": False,
        "usage": ({"prompt_cache_hit_tokens": hit, "prompt_cache_miss_tokens": miss,
                   "completion_tokens": completion} if unmetered is None else None),
        "ceq": ceq,
        "unmetered": bool(unmetered),
        "reason": unmetered,
    }


def write_ledger(path: Path, rows: List[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def eval_ledger(path: Path, campaign_id: str, count: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps({"schema": "a0.a1.harness_eval_ledger/v1", "seq": index,
                            "campaign_id": campaign_id, "request_id": f"r{index}"},
                           sort_keys=True) + "\n" for index in range(count)),
        encoding="utf-8",
    )
    return path


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="skeleton_dryrun")
    parser.add_argument("--out-dir", default="/tmp/a1/skeleton-dryrun")
    args = parser.parse_args(argv)
    out = Path(args.out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    report: Dict[str, Any] = {
        "schema": "a0.a1.skeleton_dryrun/v1",
        "note": "no model call and no campaign was made; the budget ledgers marked "
                "`synthetic` were constructed because an unmetered call cannot be produced "
                "without spending money",
        "checks": {},
    }

    # ------------------------------------------------------------------ #
    # A. CampaignID
    # ------------------------------------------------------------------ #
    campaign = CampaignID("T1-maxcut", "B000", "A_simpleloop", "R000")
    variants = [
        CampaignID("T1-maxcut", "B000", "A_simpleloop", "R001"),
        CampaignID("T1-maxcut", "B000", "A_kapso", "R000"),
        CampaignID("T1-maxcut", "B001", "A_simpleloop", "R000"),
        CampaignID("T2-other", "B000", "A_simpleloop", "R000"),
    ]
    report["campaign_id"] = {
        "components": ["TaskID", "BlockID", "ArmID", "ReplicateID"],
        "value": campaign.as_dict(),
        "distinct_keys": [candidate.key for candidate in variants],
    }
    report["checks"]["campaign_id_is_the_ordered_four_tuple"] = (
        campaign.as_dict()["campaign_key"] == "T1-maxcut/B000/A_simpleloop/R000"
        and len({campaign.key} | {variant.key for variant in variants}) == 5
    )

    # ------------------------------------------------------------------ #
    # B. the causal-role rule
    # ------------------------------------------------------------------ #
    built = build_declarations()
    cid, aids = built["cid"], built["aids"]
    observed = {name: factor.identity() for name, factor in cid.factors.items()}
    clean = audit(cid, aids, observed=observed)

    # B1: an object the campaign used that is named nowhere.
    undeclared = dict(observed)
    undeclared["runtime.undeclared_knob"] = "value:{\"setting\":1}"
    uncontrolled = audit(cid, aids, observed=undeclared)

    # B2: a *shared* object whose identity actually differs between arms.
    drifting = CID(task_id="T1-maxcut")
    drifting.add(Factor("task.e_star_script", "cid", sha256="de" * 32))
    drift = audit(drifting, aids, observed={"task.e_star_script": "sha256:" + "ad" * 32})

    report["causal_audit"] = {
        "pass_case": clean,
        "undeclared_object_case": uncontrolled,
        "cid_drift_case": drift,
    }
    report["checks"]["causal_audit_passes_on_the_real_declarations"] = clean["verdict"] == "pass"
    report["checks"]["an_undeclared_object_fails_the_audit"] = (
        uncontrolled["verdict"] == "fail"
        and any(problem["kind"] == "uncontrolled" for problem in uncontrolled["problems"])
    )
    report["checks"]["a_drifting_cid_factor_fails_the_audit"] = (
        drift["verdict"] == "fail"
        and any(problem["kind"] == "uncontrolled" for problem in drift["problems"])
    )

    # ------------------------------------------------------------------ #
    # C. the budget enforcer
    # ------------------------------------------------------------------ #
    budget = Budget(T_wall_sec=60.0, N_eval_max=10, CEq_max=100_000, P_concurrency=1)
    cases: Dict[str, dict] = {}

    def enforce(name: str, rows: List[dict], *, eval_count: int = 0,
                wall: float = 1.0, budget_=budget) -> dict:
        root = out / "budget" / name
        meter = write_ledger(root / "ledger.jsonl", rows)
        harness = eval_ledger(root / "harness_ledger.jsonl", "C_dry", eval_count)
        enforcer = BudgetEnforcer(budget=budget_, meter_ledger=meter, harness_eval_ledger=harness,
                                  campaign_id="C_dry", arm_id="A_simpleloop",
                                  started_at=time.monotonic() - wall)
        verdict = enforcer.check(label=name)
        verdict["synthetic"] = True
        return verdict

    good_row = meter_row("C_dry", "A_simpleloop", ceq=11513, miss=10240, hit=1280, completion=312)
    cases["within_budget"] = enforce("within_budget", [good_row, good_row], eval_count=2)
    cases["ceq_over_cap"] = enforce(
        "ceq_over_cap", [meter_row("C_dry", "A_simpleloop", ceq=100_001, miss=100_001)], eval_count=1
    )
    cases["wall_clock_over"] = enforce("wall_clock_over", [good_row], eval_count=1, wall=120.0)
    cases["evaluator_calls_over"] = enforce("evaluator_calls_over", [good_row], eval_count=11)
    cases["usage_gap_is_unmetered_and_stops"] = enforce(
        "usage_gap", [good_row, meter_row("C_dry", "A_simpleloop", unmetered="no_usage_field_in_response")],
        eval_count=2,
    )
    cases["a_refusal_is_not_a_gap"] = enforce(
        "refusal", [good_row, meter_row("C_dry", "A_simpleloop", unmetered="non_allowlisted_host:evil.example")],
        eval_count=1,
    )
    cases["a_foreign_campaign_is_not_this_campaign"] = enforce(
        "foreign", [good_row, meter_row("C_other", "A_other", ceq=999999, miss=999999)], eval_count=1
    )
    report["budget_cases"] = cases
    checks = report["checks"]
    checks["budget_within_is_within"] = cases["within_budget"]["within"] is True
    checks["budget_stops_on_ceq"] = (
        cases["ceq_over_cap"]["stopped_because"] == "budget_exhausted:CEq_max"
        and cases["ceq_over_cap"]["observed"]["CEq"] == 100_001
    )
    checks["budget_stops_on_wall_clock"] = (
        cases["wall_clock_over"]["stopped_because"] == "budget_exhausted:T_wall_sec"
    )
    checks["budget_stops_on_evaluator_calls"] = (
        cases["evaluator_calls_over"]["stopped_because"] == "budget_exhausted:N_evaluatorCalls"
    )
    checks["an_unobservable_usage_gap_stops_the_campaign"] = (
        cases["usage_gap_is_unmetered_and_stops"]["stopped_because"]
        == "budget_exhausted:unmetered_model_call"
    )
    checks["a_policy_refusal_does_not_look_like_spend"] = (
        cases["a_refusal_is_not_a_gap"]["within"] is True
        and cases["a_refusal_is_not_a_gap"]["observed"]["refused_rows"] == 1
    )
    checks["another_campaigns_ledger_rows_are_not_counted"] = (
        cases["a_foreign_campaign_is_not_this_campaign"]["observed"]["CEq"] == 11513
        and cases["a_foreign_campaign_is_not_this_campaign"]["observed"]["CEq_rows"] == 1
    )

    # an absent ledger is a refusal, not a zero
    missing = BudgetEnforcer(
        budget=budget, meter_ledger=out / "budget" / "nope.jsonl",
        harness_eval_ledger=out / "budget" / "nope2.jsonl",
        campaign_id="C_dry", arm_id="A_simpleloop",
    )
    try:
        read_meter_ledger(out / "budget" / "nope.jsonl", campaign_id="C_dry")
        missing_refused = False
        missing_detail = "no exception"
    except BudgetError as exc:
        missing_refused = True
        missing_detail = str(exc)
    checks["an_unreadable_ledger_is_refused_not_zeroed"] = missing_refused
    report["budget_cases"]["missing_ledger"] = {"refused": missing_refused, "detail": missing_detail}

    # ------------------------------------------------------------------ #
    # D. the block scheduler
    # ------------------------------------------------------------------ #
    scheduler = BlockScheduler.build(task_id="T1-maxcut", arms=ARMS, blocks=4, replicates=1, seed=20260922)
    plan_a = scheduler.schedule()
    scheduler_again = BlockScheduler.build(task_id="T1-maxcut", arms=ARMS, blocks=4, replicates=1, seed=20260922)
    plan_b = scheduler_again.schedule()
    per_block_orders = [
        [key.split("/")[2] for key in block.order] for block in scheduler.blocks
    ]

    # one campaign of block B001 completes, then an outage hits B001 on the other arm
    first_key = scheduler.blocks[1].order[0]
    second_key = scheduler.blocks[1].order[1]
    scheduler.complete(first_key, evidence={"score_source": "harness"})
    outage = scheduler.outage(second_key, reason="model_relay_interruption",
                              detail="the metered relay dropped mid-block")
    status = scheduler.status()
    block_b = next(block for block in status["blocks"] if block["block_id"] == "B001")

    # a completed block stays usable; an invalidated one never contributes
    for key in scheduler.blocks[0].order:
        scheduler.complete(key, evidence={"score_source": "harness"})
    status_after = scheduler.status()
    rerun = scheduler.rerun_block("B001", new_block_id="B001r")
    rerun_keys = list(rerun.order)

    report["blocks"] = {
        "planned_order": plan_a,
        "per_block_arm_orders": per_block_orders,
        "outage_event": outage,
        "block_b_after_outage": block_b,
        "status": status_after,
        "rerun_block": {"block_id": "B001r", "order": rerun_keys},
    }
    checks["the_plan_is_reproducible_from_the_seed"] = plan_a == plan_b
    checks["each_block_contains_every_arm_once"] = all(
        sorted(order) == sorted(ARMS) for order in per_block_orders
    )
    checks["blocks_are_not_all_the_same_order"] = len({tuple(order) for order in per_block_orders}) > 1
    checks["an_outage_invalidates_the_whole_block"] = (
        outage["event"] == "block_invalidated"
        and block_b["invalidated"] is True
        and all(record["status"] in ("outage", "invalidated") for record in block_b["records"].values())
    )
    checks["an_already_complete_campaign_in_an_invalidated_block_is_discarded"] = (
        block_b["records"][first_key]["status"] == "invalidated"
    )
    checks["only_complete_blocks_are_usable"] = status_after["usable_blocks"] == ["B000"]
    checks["an_invalidated_block_is_replaced_by_a_new_block"] = (
        "B001" in status_after["invalidated_blocks"]
        and any(block["block_id"] == "B001r" for block in scheduler.status()["blocks"])
        and all("B001r" in key for key in rerun_keys)
    )
    try:
        scheduler.complete(second_key, evidence={})
        rejected = False
    except BlockError:
        rejected = True
    checks["an_invalidated_block_cannot_be_completed"] = rejected

    # ------------------------------------------------------------------ #
    # E. the campaign skeleton's preflight (fail-closed)
    # ------------------------------------------------------------------ #
    campaign_skeleton = A1Campaign(
        campaign=campaign,
        arm=ArmSpec(
            arm_id="A_simpleloop",
            runtime="simpleloop",
            graph=REPO_ROOT / "a0/tasks/maxcut/suite/dev/G_dev_0001.json",
            baseline_candidate="c02_ok_low_baseline",
            command=["python3", "-c", "print('the arm would run here')", "--base-url", "{base_url}"],
        ),
        budget=budget,
        work_dir=out / "campaign",
    )
    plan = campaign_skeleton.run(dry_run=True)
    report["campaign_plan"] = plan
    checks["campaign_preflight_passes_on_the_real_artifacts"] = plan["preflight"]["pass"] is True
    checks["campaign_dry_run_starts_nothing"] = (
        plan.get("dry_run") is True and plan["would_start"] == ["meter_proxy", "harness_eval_service",
                                                               "unix_relay", "arm"]
    )
    checks["the_arm_command_carries_the_campaigns_meter_url"] = any(
        part.startswith("http://127.0.0.1:") for part in plan["arm_command"]
    )
    checks["the_topology_prefix_is_unshare_rn"] = plan["namespace_prefix"][:2] == ["unshare", "-rn"]

    # a missing witness must refuse rather than default
    broken_arm = ArmSpec(arm_id="A_simpleloop", runtime="simpleloop", graph=None, command=[])
    try:
        A1Campaign(campaign=campaign, arm=broken_arm, budget=budget, work_dir=out / "campaign-broken")
        refused = False
        detail = "constructed"
    except Exception as exc:  # PreflightError
        refused = True
        detail = f"{type(exc).__name__}: {exc}"
    checks["a_campaign_without_an_instance_is_refused"] = refused
    report["campaign_broken"] = {"refused": refused, "detail": detail}

    # ------------------------------------------------------------------ #
    report["verdict"] = "pass" if all(checks.values()) else "fail"
    (out / "skeleton_dryrun.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "planned_order": plan_a,
                      "per_block_arm_orders": per_block_orders,
                      "budget_stopped_because": {
                          name: case.get("stopped_because") for name, case in cases.items()},
                      "out": str(out / "skeleton_dryrun.json")}, indent=1))
    return 0 if report["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
