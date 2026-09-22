"""Harness-owned-evaluation probe for KAPSO — model-free.

Question: can our adapter land a harness-supplied Outcome as KAPSO's *score of
record* with no upstream edit, i.e. can the runtime consume a score it did not
produce?  Every round here is driven through the adapter's documented seams
(``a0_adapter/seams.py``): no model call is made, and the registered evaluation
is deliberately NOT executed in the injection scenarios — the KAPSO_EVAL_MANIFEST
line the runtime parses is synthesised by the harness.

    .venv/bin/python runs/harness-owned-probe/probe.py

Writes ``probe.json`` next to this file.  All KAPSO code is the pinned read-only
checkout (``/home/ebt/kapso_ck/kapso`` @ 7d99b152) imported through PYTHONPATH.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from a0_adapter.channels import run_reference_e_star  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig,
    bootstrap_kapso,
    load_candidate_set,
    load_eid_star,
)
from a0_adapter.runtime import PROBLEM, KapsoRuntime  # noqa: E402

HARNESS_HIGH = 42.0   # a value the registered evaluator could never produce
HARNESS_LOW = 7.0
HARNESS_THIRD = 3.0
TAG_LIE = 1.0         # the <score> tag, deliberately different from the outcome


def full_grant():
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    return FULL_PASSTHROUGH


def make_runtime(config, eid, candidates, name: str) -> KapsoRuntime:
    runtime = KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=HERE / name,
        state_root=HERE / name / "state",
    )
    baseline = next(c for c in candidates if c.role == "baseline")
    runtime.prepare(baseline)
    return runtime


def run_round(runtime: KapsoRuntime):
    runtime.strategy.observe_fidelity(full_grant())
    started = time.monotonic()
    node = runtime.strategy.run(PROBLEM)
    return node, time.monotonic() - started


def node_facts(node) -> Dict[str, Any]:
    return {
        "node_id": node.node_id,
        "branch_name": node.branch_name,
        "parent_node_id": node.parent_node_id,
        "parent_branch_name": node.parent_branch_name,
        "score": node.score,
        "evaluation_valid": node.evaluation_valid,
        "evaluation_integrity_error": node.evaluation_integrity_error,
        "had_error": node.had_error,
        "eval_fidelity": node.eval_fidelity,
        "build_fidelity": node.build_fidelity,
        "evaluation_provenance": node.evaluation_provenance,
        "code_diff_lines": len(node.code_diff.strip().splitlines()),
        "evaluation_attempts": [
            {
                "evaluator_id": attempt.evaluator_id,
                "fidelity": attempt.fidelity,
                "fraction": attempt.fraction,
                "seed": attempt.seed,
                "score": attempt.score,
            }
            for attempt in node.evaluation_attempts
        ],
        "evaluation_output_tail": "\n".join(
            (node.evaluation_output or "").strip().splitlines()[-3:]
        ),
    }


def selection_facts(strategy) -> Dict[str, Any]:
    best = strategy.get_best_experiment()
    deliverable = strategy.get_deliverable_experiment()
    return {
        "parent_policy": strategy.parent_policy,
        "best_node_id": None if best is None else best.node_id,
        "best_score": None if best is None else best.score,
        "deliverable_node_id": None if deliverable is None else deliverable.node_id,
        "deliverable_score": strategy.get_deliverable_score(),
    }


class Checks:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def add(self, check_id, description, expected, observed, evidence=None) -> bool:
        ok = expected == observed
        self.items.append({
            "check_id": check_id,
            "description": description,
            "expected": expected,
            "observed": observed,
            "pass": ok,
            "evidence": evidence or {},
        })
        return ok

    def failed(self) -> List[str]:
        return [
            f"{i['check_id']}: expected {i['expected']!r}, observed {i['observed']!r}"
            for i in self.items if not i["pass"]
        ]


def scenario_1(config, eid, candidates, checks: Checks) -> Dict[str, Any]:
    """A harness Outcome with no in-session E* run becomes the score of record."""
    runtime = make_runtime(config, eid, candidates, "s1_harness_outcome")
    plan = runtime.seams["plan"]
    plan.push("c02_baseline_upstream", harness_outcome=HARNESS_HIGH,
              score_tag_value=TAG_LIE)
    plan.push("c01_good_hex", harness_outcome=HARNESS_LOW)
    plan.push("c14_near_zero", harness_outcome=HARNESS_THIRD)

    nodes = []
    for _ in range(3):
        node, _elapsed = run_round(runtime)
        nodes.append(node)

    facts = [node_facts(n) for n in nodes]
    selection = selection_facts(runtime.strategy)
    records = [dict(r) for r in plan.rounds]

    checks.add(
        "HOE-K1",
        "the harness Outcome is the node's score of record, though the session "
        "never ran the registered evaluation (plan record command is null)",
        {"node0_score": HARNESS_HIGH, "node0_record_command": None},
        {"node0_score": facts[0]["score"],
         "node0_record_command": records[0]["command"]},
        {"record_harness_outcome": records[0]["harness_outcome"],
         "evaluator_calls": runtime.evaluator_calls},
    )
    checks.add(
        "HOE-K2",
        "the <score> tag (1.0) does not survive: the manifest line decides "
        "(strategy.py:624-627 is overwritten by feedback_flow.py:76-93)",
        {"tag_value": TAG_LIE, "score_of_record": HARNESS_HIGH,
         "differs": True},
        {"tag_value": TAG_LIE, "score_of_record": facts[0]["score"],
         "differs": facts[0]["score"] != TAG_LIE},
    )
    checks.add(
        "HOE-K3",
        "the harness-scored node is valid and selectable: the integrity gate "
        "checks the branch's evaluator tree, not the score's provenance",
        {"evaluation_valid": True, "integrity_error": ""},
        {"evaluation_valid": facts[0]["evaluation_valid"],
         "integrity_error": facts[0]["evaluation_integrity_error"]},
    )
    checks.add(
        "HOE-K4",
        "the next round's parent derives from the harness score: round 2 has "
        "one finished node, round 3 chooses node 0 (42.0) over node 1 (7.0)",
        {"round2_parent_node_id": 0, "round3_parent_node_id": 0},
        {"round2_parent_node_id": facts[1]["parent_node_id"],
         "round3_parent_node_id": facts[2]["parent_node_id"]},
        {"round3_parent_branch": facts[2]["parent_branch_name"],
         "node0_branch": facts[0]["branch_name"]},
    )
    checks.add(
        "HOE-K5",
        "best and deliverable follow the harness score",
        {"best_node_id": 0, "best_score": HARNESS_HIGH,
         "deliverable_node_id": 0, "deliverable_score": HARNESS_HIGH},
        {"best_node_id": selection["best_node_id"],
         "best_score": selection["best_score"],
         "deliverable_node_id": selection["deliverable_node_id"],
         "deliverable_score": selection["deliverable_score"]},
    )
    checks.add(
        "HOE-K6",
        "ATTRIBUTION CAVEAT: the harness score is recorded as an "
        "EvaluationAttempt under the registered evaluator id at the granted "
        "class (registered_evaluation.py:124-159)",
        {"attempt_score": HARNESS_HIGH, "attempt_fidelity": "full",
         "attempt_fraction": 1.0,
         "attempt_seed": int(runtime.maintainer.subsample_seed),
         "evaluator_id_is_registered": True},
        {
            "attempt_score": (
                facts[0]["evaluation_attempts"][0]["score"]
                if facts[0]["evaluation_attempts"] else None
            ),
            "attempt_fidelity": (
                facts[0]["evaluation_attempts"][0]["fidelity"]
                if facts[0]["evaluation_attempts"] else None
            ),
            "attempt_fraction": (
                facts[0]["evaluation_attempts"][0]["fraction"]
                if facts[0]["evaluation_attempts"] else None
            ),
            "attempt_seed": (
                facts[0]["evaluation_attempts"][0]["seed"]
                if facts[0]["evaluation_attempts"] else None
            ),
            "evaluator_id_is_registered": bool(
                facts[0]["evaluation_attempts"]
                and facts[0]["evaluation_attempts"][0]["evaluator_id"]
                == runtime.strategy.registered_evaluator_id
            ),
        },
    )

    # Independent E* on the same candidate bytes: what the runtime's own
    # evaluation would have produced for node 0's artifact.
    reference = run_reference_e_star(
        config, eid, "c02_baseline_upstream",
        next(c for c in candidates if c.candidate_id == "c02_baseline_upstream").path,
        dict(eid.canonical_theta), HERE / "s1_harness_outcome" / "reference",
    )
    checks.add(
        "HOE-K7",
        "the score of record is NOT what the harness's own frozen evaluator "
        "reports for this artifact: an independent E* run gives the baseline "
        "value, the runtime recorded 42.0",
        {"e_star_objective": reference.objective,
         "score_of_record_is_harness_value": True,
         "score_of_record": HARNESS_HIGH},
        {"e_star_objective": reference.objective,
         "score_of_record_is_harness_value": (
             reference.objective != facts[0]["score"]
             and facts[0]["score"] == HARNESS_HIGH
         ),
         "score_of_record": facts[0]["score"]},
        {"outcome_path": reference.outcome_path,
         "e_star_status": reference.status},
    )

    return {
        "nodes": facts,
        "selection": selection,
        "seam_records": records,
        "kapso_state": runtime.strategy.dump_state(),
        "independent_e_star": {
            "candidate_id": "c02_baseline_upstream",
            "objective": reference.objective,
            "status": reference.status,
            "outcome_path": reference.outcome_path,
        },
    }


def scenario_2(config, eid, candidates, checks: Checks) -> Dict[str, Any]:
    """No manifest at all: what carries the score then?"""
    runtime = make_runtime(config, eid, candidates, "s2_no_manifest")
    plan = runtime.seams["plan"]
    plan.push("c01_good_hex", run_evaluation=False, score_tag_value=5.0)
    plan.push("c02_baseline_upstream", run_evaluation=False, score_tag_value=5.0)

    nodes = []
    for _ in range(2):
        node, _elapsed = run_round(runtime)
        nodes.append(node)

    facts = [node_facts(n) for n in nodes]
    selection = selection_facts(runtime.strategy)

    checks.add(
        "HOE-K8",
        "with no manifest line the runtime's score of record is the feedback "
        "judge's extraction (feedback_flow.py:66-72), which overrides the "
        "<score> tag (5.0) — here the seam judge has nothing to extract, so the "
        "node is scoreless but still valid",
        {"node0_score": None, "node0_evaluation_valid": True,
         "tag_value_destroyed": True},
        {"node0_score": facts[0]["score"],
         "node0_evaluation_valid": facts[0]["evaluation_valid"],
         "tag_value_destroyed": facts[0]["score"] != 5.0},
        {"record_command": plan.rounds[0]["command"],
         "manifest": plan.rounds[0]["manifest"]},
    )
    checks.add(
        "HOE-K9",
        "a scoreless node is not selectable: no best, no deliverable, no "
        "evaluation attempt",
        {"best_node_id": None, "deliverable_node_id": None,
         "deliverable_score": None, "attempts": 0},
        {"best_node_id": selection["best_node_id"],
         "deliverable_node_id": selection["deliverable_node_id"],
         "deliverable_score": selection["deliverable_score"],
         "attempts": len(facts[0]["evaluation_attempts"])},
    )
    checks.add(
        "HOE-K10",
        "a scoreless but integrity-clean node is still used as the lineage "
        "fallback (strategy.py:1390-1404), and it is NOT marked invalid",
        {"node1_parent_node_id": 0, "node0_integrity_error": "",
         "node0_evaluation_valid": True},
        {"node1_parent_node_id": facts[1]["parent_node_id"],
         "node0_integrity_error": facts[0]["evaluation_integrity_error"],
         "node0_evaluation_valid": facts[0]["evaluation_valid"]},
    )
    return {"nodes": facts, "selection": selection,
            "seam_records": [dict(r) for r in plan.rounds]}


def scenario_3(config, eid, candidates, checks: Checks) -> Dict[str, Any]:
    """The integrity gate: what it actually rejects."""
    runtime = make_runtime(config, eid, candidates, "s3_tamper")
    plan = runtime.seams["plan"]
    plan.push("c01_good_hex", harness_outcome=HARNESS_HIGH,
              tamper="A0-PROBE-TAMPER: harness-supplied score on a doctored tree")

    node, _elapsed = run_round(runtime)
    facts = node_facts(node)
    selection = selection_facts(runtime.strategy)

    checks.add(
        "HOE-K11",
        "a harness-supplied score on a candidate that changed its evaluator "
        "tree is voided by enforce_evaluation_integrity (base.py:740-794): the "
        "gate keys on the tree, and it nulls the score",
        {"evaluation_valid": False, "score": None,
         "integrity_error_nonempty": True},
        {"evaluation_valid": facts["evaluation_valid"],
         "score": facts["score"],
         "integrity_error_nonempty": bool(facts["evaluation_integrity_error"])},
        {"integrity_error": facts["evaluation_integrity_error"],
         "best_node_id": selection["best_node_id"]},
    )
    return {"nodes": [facts], "selection": selection,
            "seam_records": [dict(r) for r in plan.rounds]}


def scenario_4(config, eid, candidates, checks: Checks) -> Dict[str, Any]:
    """The manifest class gate and the registration switch — direct calls."""
    import kapso.execution.fidelity as fidelity_module
    from kapso.execution.search_strategies.generic.registered_evaluation import (
        manifest_of_record,
    )

    runtime = make_runtime(config, eid, candidates, "s4_gates")
    strategy = runtime.strategy
    node = runtime.strategy.node_history[0] if runtime.strategy.node_history else None
    if node is None:
        # Build a node-shaped object from the first round so the parser calls
        # are made against real state rather than a hand-made stub.
        plan = runtime.seams["plan"]
        plan.push("c02_baseline_upstream", harness_outcome=HARNESS_HIGH)
        node, _elapsed = run_round(runtime)

    line = "KAPSO_EVAL_MANIFEST " + json.dumps({
        "fidelity": "full", "fraction": "1.0",
        "seed": int(runtime.maintainer.subsample_seed),
        "items": 1, "total_items": 1, "score": HARNESS_HIGH,
    })

    def parse_with(text: str, *, command: Optional[str], seed: Optional[int] = None,
                   decision=None):
        probe_node = type("N", (), {})()
        probe_node.evaluation_output = text
        return manifest_of_record(
            probe_node,
            registered_evaluation_command=command,
            fidelity_decision=(
                decision if decision is not None
                else strategy.fidelity_decision
            ),
            registered_subsample_seed=(
                strategy.registered_subsample_seed if seed is None else seed
            ),
        )

    granted_command = strategy.registered_evaluation_command
    accepted = parse_with("noise\n" + line, command=granted_command)
    wrong_class = parse_with(
        "KAPSO_EVAL_MANIFEST " + json.dumps({
            "fidelity": "fast", "fraction": "0.15",
            "seed": int(runtime.maintainer.subsample_seed),
            "items": 1, "total_items": 1, "score": HARNESS_HIGH,
        }),
        command=granted_command,
    )
    wrong_seed = parse_with(
        "KAPSO_EVAL_MANIFEST " + json.dumps({
            "fidelity": "full", "fraction": "1.0",
            "seed": int(runtime.maintainer.subsample_seed) + 1,
            "items": 1, "total_items": 1, "score": HARNESS_HIGH,
        }),
        command=granted_command,
    )
    unregistered = parse_with("noise\n" + line, command="")
    missing_class_line = parse_with("plain evaluation output, no manifest",
                                    command=granted_command)
    try:
        parse_with(
            'KAPSO_EVAL_MANIFEST {"fidelity": "full", "fraction": "1.0", '
            f'"seed": {int(runtime.maintainer.subsample_seed)}, "score": 42.0}}',
            command=granted_command,
        )
        malformed = "no exception"
    except Exception as exc:
        # parse_manifest_line requires the item-count keys (maintainer.py:70-79)
        # and raises EvaluationMaintainerError; in the real path that exception
        # is swallowed by generate_feedback's try/except (feedback_flow.py:117),
        # leaving node.score at the judge's extraction and evaluation_valid at
        # the judge's verdict (both assigned at feedback_flow.py:66-72 before
        # the manifest is consulted).
        malformed = f"{type(exc).__name__}: {exc}"

    checks.add(
        "HOE-K12",
        "the injected line is accepted with exactly the granted class triple "
        "(fidelity/fraction/seed) and refused for any other class "
        "(registered_evaluation.py:87-99) — the gate is on the class label, "
        "not on who produced the line",
        {"accepted_score": HARNESS_HIGH, "wrong_class": None,
         "wrong_seed": None,
         "malformed_line": (
             "EvaluationMaintainerError: Evaluation manifest line is "
             "missing 'items'"
         )},
        {
            "accepted_score": (
                None if accepted is None else float(accepted["score"])
            ),
            "wrong_class": wrong_class,
            "wrong_seed": wrong_seed,
            "malformed_line": malformed,
        },
    )
    checks.add(
        "HOE-K13",
        "with no registered evaluation command the whole manifest path is off "
        "(strategy.py:1117-1120, registered_evaluation.py:70-71): the runtime "
        "ignores a perfectly good manifest line",
        {"unregistered_result": None, "no_manifest_result": None},
        {"unregistered_result": unregistered,
         "no_manifest_result": missing_class_line},
    )

    provenance = strategy.evaluation_provenance
    maintainer_keys = None
    try:
        from kapso.execution.orchestrator import _MAINTAINER_BLOCK_KEYS

        maintainer_keys = sorted(_MAINTAINER_BLOCK_KEYS)
    except Exception as exc:  # pragma: no cover
        maintainer_keys = f"{type(exc).__name__}: {exc}"

    checks.add(
        "HOE-K14",
        "no documented configuration turns the session's own evaluation off: "
        "budget.fidelity.mode only selects the granted class, and the "
        "evaluation_maintainer block has no skip-evaluation key",
        {"fidelity_modes": sorted(fidelity_module.FIDELITY_MODES),
         "granted_class": {"fidelity": "full", "fraction": 1.0},
         "maintainer_block_has_skip_key": False},
        {"fidelity_modes": sorted(fidelity_module.FIDELITY_MODES),
         "granted_class": {
             "fidelity": strategy.fidelity_decision.eval_fidelity,
             "fraction": strategy.fidelity_decision.eval_fraction,
         },
         "maintainer_block_has_skip_key": bool(
             isinstance(maintainer_keys, list)
             and any("skip" in k or "no_eval" in k for k in maintainer_keys)
         )},
        {"maintainer_block_keys": maintainer_keys,
         "fidelity_mode_config": runtime.config_evidence["fidelity_mode"],
         "max_change_requests": runtime.config_evidence["max_change_requests"]},
    )
    return {
        "node": node_facts(node),
        "manifest_gate": {
            "accepted": accepted,
            "wrong_class": wrong_class,
            "wrong_seed": wrong_seed,
            "malformed_line": malformed,
            "unregistered_command": unregistered,
            "no_manifest_line": missing_class_line,
        },
        "evaluation_provenance": provenance,
        "fidelity_modes": sorted(fidelity_module.FIDELITY_MODES),
        "maintainer_block_keys": maintainer_keys,
        "config_evidence": runtime.config_evidence,
    }


def scenario_5(config, eid, candidates, checks: Checks) -> Dict[str, Any]:
    """The feedback-judge slot: an external score with no manifest and no run.

    ``feedback_flow.py:66-72`` writes ``node.score`` from
    ``feedback_generator.generate(...)`` before the manifest is consulted, so the
    judge slot is a score-injection point on its own.  The real judge is an LLM
    (its extraction is model output); this stand-in makes the injection explicit
    and deterministic.  Nothing here runs the registered evaluation, and no
    KAPSO_EVAL_MANIFEST line exists anywhere.
    """
    from kapso.execution.search_strategies.generic.feedback_generator import (
        FeedbackResult,
    )

    JUDGE_SCORE = 99.0

    class FixedJudge:
        configured_timeout_seconds = 1.0

        def generate(self, **kwargs):
            return FeedbackResult(
                stop=False,
                evaluation_valid=True,
                feedback="probe: external score handed in through the judge slot",
                score=JUDGE_SCORE,
                cost_usd=0.0,
                duration_seconds=0.0,
            )

    runtime = make_runtime(config, eid, candidates, "s5_judge_slot")
    runtime.strategy.feedback_generator = FixedJudge()
    plan = runtime.seams["plan"]
    plan.push("c02_baseline_upstream", run_evaluation=False)
    plan.push("c01_good_hex", run_evaluation=False)

    nodes = []
    for _ in range(2):
        node, _elapsed = run_round(runtime)
        nodes.append(node)
    facts = [node_facts(n) for n in nodes]
    selection = selection_facts(runtime.strategy)

    checks.add(
        "HOE-K15",
        "the judge slot is a score-injection point: with no manifest and no "
        "evaluator run, the judge's number becomes the score of record "
        "(feedback_flow.py:66-72)",
        {"node0_score": JUDGE_SCORE, "node0_evaluation_valid": True,
         "manifest_line_present": False, "record_command": None},
        {"node0_score": facts[0]["score"],
         "node0_evaluation_valid": facts[0]["evaluation_valid"],
         "manifest_line_present": "KAPSO_EVAL_MANIFEST"
         in (nodes[0].evaluation_output or ""),
         "record_command": plan.rounds[0]["command"]},
    )
    checks.add(
        "HOE-K16",
        "even with NO manifest anywhere, that externally supplied score is "
        "recorded as registered-evaluator full-tier evidence "
        "(record_evaluation_attempt does not consult the manifest) and drives "
        "best/deliverable/parent",
        {"attempt_score": JUDGE_SCORE, "attempt_fidelity": "full",
         "best_node_id": 0, "deliverable_node_id": 0,
         "deliverable_score": JUDGE_SCORE, "round2_parent_node_id": 0},
        {"attempt_score": (
            facts[0]["evaluation_attempts"][0]["score"]
            if facts[0]["evaluation_attempts"] else None
         ),
         "attempt_fidelity": (
            facts[0]["evaluation_attempts"][0]["fidelity"]
            if facts[0]["evaluation_attempts"] else None
         ),
         "best_node_id": selection["best_node_id"],
         "deliverable_node_id": selection["deliverable_node_id"],
         "deliverable_score": selection["deliverable_score"],
         "round2_parent_node_id": facts[1]["parent_node_id"]},
        {"evaluator_id_is_registered": bool(
            facts[0]["evaluation_attempts"]
            and facts[0]["evaluation_attempts"][0]["evaluator_id"]
            == runtime.strategy.registered_evaluator_id
        )},
    )
    return {"nodes": facts, "selection": selection,
            "seam_records": [dict(r) for r in plan.rounds],
            "judge_score": JUDGE_SCORE}


def scenario_6(config, eid, candidates, checks: Checks,
               state: Dict[str, Any]) -> Dict[str, Any]:
    """KAPSO's own durable record: serialize, reload, re-select.

    ``strategy.dump_state()`` is exactly what the run checkpoint stores
    (``orchestrator.py:937-951``); the payload is written through KAPSO's own
    ``RunCheckpoint.create``/``to_dict`` and read back through
    ``RunCheckpoint.from_dict`` (its validator), then restored into a fresh
    strategy the way ``orchestrator.py:308-311`` restores a resume.  The
    selectors that run afterwards are KAPSO's, on KAPSO's recorded numbers.
    """
    from kapso.execution.run_checkpoint import RunCheckpoint, config_fingerprint

    checkpoint = RunCheckpoint.create(
        strategy_type="generic",
        goal=PROBLEM,
        config_fingerprint=config_fingerprint({"params": "a0-harness-owned-probe"}),
        status="running",
        completed_iterations=state.get("iteration_count", 0),
        cumulative_cost=0.0,
        current_feedback=None,
        strategy_state=state,
    )
    path = HERE / "s1_harness_outcome" / "kapso-run-checkpoint.json"
    path.write_text(json.dumps(checkpoint.to_dict(), indent=2) + "\n",
                    encoding="utf-8")

    reloaded = RunCheckpoint.from_dict(json.loads(path.read_text("utf-8")))
    recorded = [
        {
            "node_id": entry["node_id"],
            "score": entry.get("score"),
            "evaluation_valid": entry.get("evaluation_valid"),
            "branch_name": entry.get("branch_name"),
            "parent_node_id": entry.get("parent_node_id"),
            "evaluation_attempts": entry.get("evaluation_attempts"),
        }
        for entry in reloaded.strategy_state["node_history"]
    ]

    runtime = make_runtime(config, eid, candidates, "s6_restored")
    runtime.strategy.load_state(reloaded.strategy_state)
    parent = runtime.strategy._select_parent()
    best = runtime.strategy.get_best_experiment()
    deliverable = runtime.strategy.get_deliverable_experiment()
    restored = {
        "node_scores": {
            f"node{entry['node_id']}": entry["score"] for entry in recorded
        },
        "parent_branch_name": parent.branch_name,
        "parent_node_id": parent.node_id,
        "best_node_id": None if best is None else best.node_id,
        "deliverable_node_id": None if deliverable is None else deliverable.node_id,
        "deliverable_score": runtime.strategy.get_deliverable_score(),
    }

    checks.add(
        "HOE-K17",
        "the harness score survives KAPSO's own checkpoint serializer and "
        "validator: the recorded state carries score=42.0 for node 0 with its "
        "attempt ledger",
        {"node0_score_in_checkpoint": HARNESS_HIGH,
         "node0_attempt_score": HARNESS_HIGH,
         "node1_score_in_checkpoint": HARNESS_LOW},
        {"node0_score_in_checkpoint": recorded[0]["score"],
         "node0_attempt_score": recorded[0]["evaluation_attempts"][0]["score"],
         "node1_score_in_checkpoint": recorded[1]["score"]},
        {"checkpoint_path": str(path),
         "checkpoint_schema_version": reloaded.schema_version},
    )
    checks.add(
        "HOE-K18",
        "restoring that recorded state into a fresh strategy, KAPSO's own "
        "_select_parent returns the harness-scored node and the deliverable "
        "score is the harness value",
        {"parent_node_id": 0, "best_node_id": 0, "deliverable_node_id": 0,
         "deliverable_score": HARNESS_HIGH},
        {"parent_node_id": restored["parent_node_id"],
         "best_node_id": restored["best_node_id"],
         "deliverable_node_id": restored["deliverable_node_id"],
         "deliverable_score": restored["deliverable_score"]},
        {"parent_branch_name": parent.branch_name},
    )
    return {"checkpoint_path": str(path), "recorded_nodes": recorded,
            "restored_selection": restored}


def main() -> int:
    config = AdapterConfig.load()
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)

    checks = Checks()
    results: Dict[str, Any] = {
        "schema": "a0.kapso.harness_owned_probe/v1",
        "runtime": "kapso",
        "kapso_src": str(config.kapso_src),
        "kapso_revision": "7d99b152",
        "model_calls": 0,
        "seams": {
            "ideation": "a0_adapter/seams.py::seam_generate_solution",
            "implementation": "a0_adapter/seams.py::_Plan.run_implementation",
            "judge": "a0_adapter/seams.py::SeamFeedbackJudge",
            "harness_outcome": "a0_adapter/seams.py::_Plan(harness_outcome=…)",
        },
        "harness_values": {
            "high": HARNESS_HIGH, "low": HARNESS_LOW, "third": HARNESS_THIRD,
            "tag_lie": TAG_LIE,
        },
    }

    for name, fn in (
        ("s1_harness_outcome", scenario_1),
        ("s2_no_manifest", scenario_2),
        ("s3_tamper", scenario_3),
        ("s4_gates", scenario_4),
        ("s5_judge_slot", scenario_5),
    ):
        started = time.monotonic()
        results[name] = fn(config, eid, candidates, checks)
        results[name]["elapsed_sec"] = round(time.monotonic() - started, 3)
        print(f"[probe] {name} done in {results[name]['elapsed_sec']}s")

    started = time.monotonic()
    recorded_state = results["s1_harness_outcome"].pop("kapso_state")
    results["s6_restored"] = scenario_6(
        config, eid, candidates, checks, recorded_state
    )
    results["s6_restored"]["elapsed_sec"] = round(time.monotonic() - started, 3)
    print(f"[probe] s6_restored done in {results['s6_restored']['elapsed_sec']}s")

    results["checks"] = checks.items
    results["failed"] = checks.failed()
    results["pass"] = not checks.failed()
    (HERE / "probe.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for item in checks.items:
        print(f"  {'PASS' if item['pass'] else 'FAIL'} {item['check_id']} "
              f"{item['description'][:70]}")
    print(f"[probe] {len(checks.items) - len(checks.failed())}/"
          f"{len(checks.items)} checks passed -> {HERE / 'probe.json'}")
    return 0 if not checks.failed() else 1


if __name__ == "__main__":
    raise SystemExit(main())
