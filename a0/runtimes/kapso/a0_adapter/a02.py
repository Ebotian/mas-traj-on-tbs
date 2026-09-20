"""A0.2 — the score -> search selection contract for KAPSO.

Frozen condition (``plan:561``, ``strategy.py:211-212``): ``parent_policy =
"best"``, one registered evaluator head, ``budget.fidelity.mode = "off"`` so
every iteration's grant is ``FULL_PASSTHROUGH`` and both candidates sit in the
same tier.  Under it, KAPSO's semantics are fully deterministic: parent,
deliverable and round representative are all argmax.

Five scenarios are run, each in its own KAPSO workspace, with the scores coming
from real E* runs fed through KAPSO's registered-evaluation path:

===================  ==========================================================
``ordered_pair``     ``E(c01) > E(c02)``: the next round's parent is c01 and the
                     deliverable is c01 (A02-K1..K4); an extra round observes
                     the parent the runtime actually chose.
``reversed_order``   the same two candidates in the opposite order: the parent
                     is still the high scorer, so selection follows the score
                     and not recency of the node.
``tie_break``        the exact tie (c01 vs c03_mirror): the first node in
                     ``node_history`` wins (A02-K7, Python ``max`` semantics).
``error_and_tamper`` a candidate whose E* verdict is ``error`` (no score) and a
                     candidate that tampers with its registered evaluation
                     tree: neither becomes parent or deliverable (A02-K5), and
                     the had_error gate is probed on real nodes.
``fast_only``        a ``fast``-only high scorer versus a ``full`` low scorer:
                     tier outranks score for the deliverable (A02-K6,
                     ``fidelity.py:184-213``), while the parent still follows
                     the raw score — the two objects are not the same.
===================  ==========================================================
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .channels import run_reference_e_star
from .common import (
    AdapterConfig,
    Candidate,
    EidStar,
    ThetaE,
    TraceWriter,
    e_star_identity,
    eid_r_payload,
    failure_stage,
    fr_payload,
    selection_payload,
    sha256_file,
    write_json,
)
from .runtime import KapsoRuntime, PROBLEM


class Checks:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def add(self, check_id: str, description: str, expected: Any, observed: Any,
            evidence: Optional[Dict[str, Any]] = None) -> bool:
        passed = expected == observed
        self.items.append({
            "check_id": check_id,
            "description": description,
            "expected": expected,
            "observed": observed,
            "pass": passed,
            "evidence": evidence or {},
        })
        return passed

    @property
    def passed(self) -> bool:
        return all(item["pass"] for item in self.items)

    def failed(self) -> List[str]:
        return [f"{item['check_id']}: expected {item['expected']!r}, observed "
                f"{item['observed']!r}" for item in self.items if not item["pass"]]


def _runtime(
    config: AdapterConfig,
    eid: EidStar,
    candidates: List[Candidate],
    run_dir: Path,
    name: str,
) -> KapsoRuntime:
    runtime = KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=run_dir / name,
        state_root=run_dir / name / "state",
    )
    baseline = next(c for c in candidates if c.role == "baseline")
    runtime.prepare(baseline)
    return runtime


def _run_round(runtime: KapsoRuntime, decision: Any) -> Any:
    runtime.strategy.observe_fidelity(decision)
    return runtime.strategy.run(PROBLEM)


def _full_grant():
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    return FULL_PASSTHROUGH


def _fast_grant():
    from kapso.execution.fidelity import FidelityDecision

    return FidelityDecision(
        profile="probe",
        build_fidelity="full",
        eval_fidelity="fast",
        eval_fraction=0.15,
        reason="A02-K6 control: fast-only evidence",
    )


def _branch_candidate_sha(runtime: KapsoRuntime, branch: str) -> Optional[str]:
    with runtime.strategy.workspace.materialize_ref(branch) as worktree:
        solution = Path(worktree) / "solution.py"
        if not solution.is_file():
            return None
        return sha256_file(solution)


def _round_record(runtime: KapsoRuntime, node: Any, index: int) -> Dict[str, Any]:
    plan = runtime.seams["plan"].rounds[index]
    return {
        "node_id": node.node_id,
        "candidate_id": plan["candidate_id"],
        "branch_name": node.branch_name,
        "parent_node_id": node.parent_node_id,
        "parent_branch_name": node.parent_branch_name,
        "score": node.score,
        "evaluation_valid": node.evaluation_valid,
        "had_error": node.had_error,
        "build_fidelity": node.build_fidelity,
        "eval_fidelity": node.eval_fidelity,
        "evaluation_integrity_error": node.evaluation_integrity_error,
        "attempts": [attempt.to_dict() for attempt in node.evaluation_attempts],
        "fidelity_grant": {
            "fidelity": plan["fidelity"],
            "fraction": plan["fraction"],
        },
        "manifest_exit_code": plan["exit_code"],
        "branch_solution_sha256": _branch_candidate_sha(runtime, node.branch_name),
        "tamper": plan["tamper"],
    }


def _decisions(runtime: KapsoRuntime) -> Dict[str, Any]:
    from kapso.execution.fidelity import evidence_tier

    strategy = runtime.strategy
    evaluator_id = strategy.registered_evaluator_id
    scored = [
        node for node in strategy.node_history
        if not node.had_error and node.evaluation_valid and node.score is not None
    ]
    best = strategy.get_best_experiment()
    deliverable = strategy.get_deliverable_experiment()
    return {
        "node_history": [
            {
                "node_id": node.node_id,
                "branch_name": node.branch_name,
                "score": node.score,
                "had_error": node.had_error,
                "evaluation_valid": node.evaluation_valid,
                "tier": (
                    evidence_tier(node, evaluator_id)
                    if evaluator_id else None
                ),
                "eval_fidelity": node.eval_fidelity,
                "attempts": len(node.evaluation_attempts),
            }
            for node in strategy.node_history
        ],
        "scored_nodes": [node.node_id for node in scored],
        "best_node_id": None if best is None else best.node_id,
        "best_candidate_id": None if best is None else _candidate_of(runtime, best),
        "deliverable_node_id": None if deliverable is None else deliverable.node_id,
        "deliverable_candidate_id": (
            None if deliverable is None else _candidate_of(runtime, deliverable)
        ),
        "deliverable_score": strategy.get_deliverable_score(),
        "maximize_scoring": strategy.problem_handler.maximize_scoring,
        "parent_policy": strategy.parent_policy,
    }


def _candidate_of(runtime: KapsoRuntime, node: Any) -> Optional[str]:
    for record in runtime.seams["plan"].rounds:
        if record["branch_name"] == node.branch_name:
            return record["candidate_id"]
    return None


def _outcome_from_manifest(
    config: AdapterConfig, state_root: Path, manifest: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """The raw E* Outcome the runtime's own evaluation produced for a node."""
    if not manifest or "e_star_outcome" not in manifest:
        return {}
    path = Path(state_root) / manifest["e_star_outcome"]
    if not path.is_file():
        return {}
    return json.loads(path.read_text("utf-8"))


def _emit_round_traces(
    writer: TraceWriter,
    runtime: KapsoRuntime,
    node: Any,
    *,
    iteration: int,
    theta_payload: Dict[str, Any],
    fr: Dict[str, Any],
    config: AdapterConfig,
    budget: Dict[str, Any],
    elapsed: float,
) -> str:
    """One score event + one resource event for a round's evaluation.

    ``outcome.fields`` come from the E* Outcome *the runtime's own registered
    evaluation wrote* (located through the manifest line's ``e_star_outcome``
    key), and ``search_signal`` is the manifest score the runtime consumed.
    """
    plan = runtime.seams["plan"].rounds[-1]
    outcome = _outcome_from_manifest(config, runtime.state_root, plan["manifest"])
    fields = dict(outcome.get("fields") or {})
    fields["e_star_status"] = outcome.get("status", "unknown")
    failure = outcome.get("failure") or {}
    if failure.get("kind"):
        fields["e_star_failure_kind"] = failure["kind"]
    stage = "none"
    detail = None
    if node.evaluation_integrity_error:
        # The evaluator ran and produced a number, but the candidate's committed
        # evaluation tree was not the registered head's, so enforce_evaluation_
        # integrity rejected the measurement (base.py:740-798).
        stage = "boundary_violation"
        detail = (
            "candidate's committed evaluation tree differs from the registered "
            f"head: {node.evaluation_integrity_error}"
        )
    elif not fields:
        stage = "boundary_violation"
        detail = (
            "no E* outcome was recorded for this round: the seam session's "
            "registered evaluation was withheld (tamper control) or produced no "
            "measurement"
        )
    elif outcome.get("status") != "ok":
        stage = failure_stage(
            outcome.get("status"),
            (plan.get("manifest") or {}).get("e_star_exit_code"),
            failure.get("kind"),
        )
        detail = (
            f"E* verdict {outcome.get('status')} (exit "
            f"{(plan.get('manifest') or {}).get('e_star_exit_code')}, failure "
            f"kind {failure.get('kind')}): no score of record"
        )
    event_id = writer.emit_score(
        candidate_id=plan["candidate_id"],
        iteration=iteration,
        parent_id=(
            None if node.parent_node_id is None
            else str(node.parent_node_id)
        ),
        theta_e=theta_payload,
        outcome={"fields": fields, "cardinality": len(fields)},
        fr=fr,
        search_signal=node.score,
        evaluator_evidence={
            "status": "ok" if fields else "not_run",
            "detail": detail,
        },
        failure_stage=stage,
        failure_detail=detail,
    )
    writer.emit_resource(
        candidate_id=plan["candidate_id"],
        iteration=iteration,
        parent_id=None if node.parent_node_id is None else str(node.parent_node_id),
        theta_e=theta_payload,
        t_wall_sec=elapsed,
        n_evaluator_calls=1,
        concurrency_cap=int(budget.get("concurrency", 1)),
        concurrency_observed=1,
        scope="delta",
        secondary={"N_modelCalls": 0, "T_in": None, "T_out": None, "C_usd": None},
        budget_hard={
            "T_wall_sec": budget.get("T_wall_sec"),
            "N_evaluatorCalls": budget.get("N_evaluatorCalls"),
            "concurrency_cap": int(budget.get("concurrency", 1)),
        },
        failure_stage=stage,
        failure_detail=detail,
    )
    return event_id


def _emit_selection(
    writer: TraceWriter,
    runtime: KapsoRuntime,
    *,
    iteration: int,
    check_point: str,
    policy: str,
    considered: List[Dict[str, Any]],
    chosen_candidate_id: Optional[str],
    reason: str,
    source_score_event_id: Optional[str],
    theta_payload: Dict[str, Any],
    tie_break: Optional[str] = None,
) -> None:
    """Emit one selection event.

    ``selection.source_score_event_id`` names the score event that drove the
    decision, in the run's merged stream (``<runtime>.<run_id>.all.jsonl``,
    which ``TraceWriter`` writes).  The reference is cross-file by
    construction -- the score event lives in the score file -- so the run, not
    the per-kind file, is the validation unit
    (``adapter_contract.md`` §6.3, ``trace_schema.md`` §1.1).
    """
    linkage = (
        f"source_score_event_id={source_score_event_id} (in the score trace)"
        if source_score_event_id
        else "no score event drove this decision"
    )
    writer.emit_selection(
        candidate_id=chosen_candidate_id or (considered[0]["candidate_id"] if considered else "none"),
        iteration=iteration,
        parent_id=None,
        theta_e=theta_payload,
        selection={
            "policy": policy,
            "chosen_candidate_id": chosen_candidate_id,
            "considered": considered,
            "reason": f"{reason} [{linkage}]",
            "tie_break": tie_break,
            "source_score_event_id": source_score_event_id,
            "check_point": check_point,
        },
    )


def run_a02(
    config: AdapterConfig,
    eid: EidStar,
    candidates: List[Candidate],
    *,
    run_dir: Path,
    run_id: str,
    theta: ThetaE,
    fr: Dict[str, Any],
    budget: Dict[str, Any],
    kinds: List[str],
) -> Dict[str, Any]:
    started = time.monotonic()
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    theta_dict = {"seed": theta.seed, "fidelity": theta.fidelity,
                  "fraction": theta.fraction}
    eid_r_declaration = (
        "KAPSO's native evaluator identity: EID_r = manifest_fingerprint over "
        "the two-file registered evaluation tree (evaluation_integrity.py:112-119); "
        "the tree's a0_locator.json carries EID*'s EvaluatorSource records and "
        "canonical theta_E, which kapso_eval.py re-hashes and enforces on every "
        "invocation."
    )
    from .registered_tree import install_registered_tree

    tree_probe = install_registered_tree(
        config, eid, candidates, run_dir / "registered_evaluation_source",
        Path(config.state_root) / "registered-eval",
    )
    eid_r = eid_r_payload(
        eid.eid_star, tree_probe["manifest_fingerprint"], eid_r_declaration
    )
    writer = TraceWriter(
        run_dir, "kapso", run_id, "circle-packing", eid.eid_star, eid_r, kinds
    )
    checks = Checks()
    scenarios: Dict[str, Any] = {}

    # The three reference outcomes at theta_E*, used to state what the external
    # score actually was (independent of the runtime's own parsing).
    def reference(candidate: Candidate) -> Any:
        return run_reference_e_star(
            config, eid, candidate.candidate_id, candidate.path, theta_dict,
            run_dir / "reference",
        )

    e_star = e_star_identity(config)

    refs = {
        cid: reference(next(c for c in candidates if c.candidate_id == cid))
        for cid in ("c01_good_hex", "c02_baseline_upstream", "c03_mirror",
                    "c10_raises", "c14_near_zero")
    }

    # ------------------------------------------------------------------ #
    # scenario 1: ordered pair (E(c01) > E(c02)) — A02-K1..K4
    # ------------------------------------------------------------------ #
    scenario = "ordered_pair"
    runtime = _runtime(config, eid, candidates, run_dir, scenario)
    theta_payload = _theta(runtime, theta_dict, "full", 1.0, e_star)
    plan = runtime.seams["plan"]
    plan.push("c02_baseline_upstream")
    plan.push("c01_good_hex")
    plan.push("c14_near_zero")

    round_ids: List[str] = []
    for index in range(3):
        tick = time.monotonic()
        node = _run_round(runtime, _full_grant())
        round_ids.append(_emit_round_traces(
            writer, runtime, node,
            iteration=index,
            theta_payload=theta_payload, fr=fr, config=config, budget=budget,
            elapsed=time.monotonic() - tick,
        ))

    low = _round_record(runtime, runtime.strategy.node_history[0], 0)
    high = _round_record(runtime, runtime.strategy.node_history[1], 1)
    third = runtime.strategy.node_history[2]
    decision = _decisions(runtime)

    checks.add(
        "A02-K1",
        "get_best_experiment() is not None and is the max-score valid node",
        {"not_none": True, "node_id": 1, "candidate_id": "c01_good_hex"},
        {"not_none": decision["best_node_id"] is not None,
         "node_id": decision["best_node_id"],
         "candidate_id": decision["best_candidate_id"]},
        {"node_history": decision["node_history"]},
    )
    checks.add(
        "A02-K2",
        "the next round's parent branch/node are c01 (the higher E* score)",
        {"parent_candidate_id": "c01_good_hex", "parent_node_id": 1},
        {"parent_candidate_id": third.parent_node_id is not None and
            _candidate_of(runtime, runtime.strategy.node_history[third.parent_node_id]),
         "parent_node_id": third.parent_node_id},
        {"third_round_branch": third.branch_name,
         "third_round_parent_branch": third.parent_branch_name,
         "third_round_candidate": _round_record(runtime, third, 2)["candidate_id"]},
    )
    checks.add(
        "A02-K3",
        "the deliverable is c01 and its score is E*(c01)",
        {"deliverable_node_id": 1, "candidate_id": "c01_good_hex",
         "score": refs["c01_good_hex"].objective},
        {"deliverable_node_id": decision["deliverable_node_id"],
         "candidate_id": decision["deliverable_candidate_id"],
         "score": decision["deliverable_score"]},
        {"checkout_branch": runtime.strategy.checkout_to_best_experiment_branch()},
    )
    tiers = {entry["node_id"]: entry["tier"] for entry in decision["node_history"]}
    granted = {
        entry["node_id"]: entry["fidelity_grant"] for entry in (
            _round_record(runtime, runtime.strategy.node_history[0], 0),
            _round_record(runtime, runtime.strategy.node_history[1], 1),
        )
    }
    checks.add(
        "A02-K4",
        "both candidates sit at TIER_FULL under the same granted class "
        "(otherwise the K3 assertion is not legitimate)",
        {"tier_low": 2, "tier_high": 2, "grant_low": {"fidelity": "full", "fraction": 1.0},
         "grant_high": {"fidelity": "full", "fraction": 1.0}},
        {"tier_low": tiers.get(0), "tier_high": tiers.get(1),
         "grant_low": granted.get(0), "grant_high": granted.get(1)},
        {"maximize_scoring": decision["maximize_scoring"],
         "parent_policy": decision["parent_policy"]},
    )
    ext_ok = (
        low["score"] == refs["c02_baseline_upstream"].objective
        and high["score"] == refs["c01_good_hex"].objective
        and decision["best_node_id"] == 1
    )
    checks.add(
        "A02-K-EXT",
        "the externally supplied scores decided the selection: the winning "
        "node's score equals E*(c01) from the adapter's own reference run, and "
        "the lower-scoring node was passed over",
        True,
        ext_ok,
        {"external_scores": {
            "c02": refs["c02_baseline_upstream"].objective,
            "c01": refs["c01_good_hex"].objective},
         "runtime_scores": {"c02": low["score"], "c01": high["score"]},
         "branch_sha_ok": {
             "c02": low["branch_solution_sha256"] == next(
                 c for c in candidates
                 if c.candidate_id == "c02_baseline_upstream").solution_sha256,
             "c01": high["branch_solution_sha256"] == next(
                 c for c in candidates
                 if c.candidate_id == "c01_good_hex").solution_sha256,
         }},
    )
    _emit_selection(
        writer, runtime, iteration=2,
        check_point="A02-K2: next round's parent (parent_policy=best)",
        policy="parent_policy=best (strategy.py:1373-1406, get_best_experiment)",
        considered=_considered(runtime),
        chosen_candidate_id="c01_good_hex",
        reason=(
            f"E(c01)={high['score']!r} > E(c02)={low['score']!r}; "
            "get_best_experiment returns the max-score valid node"
        ),
        source_score_event_id=round_ids[1],
        theta_payload=theta_payload,
    )
    _emit_selection(
        writer, runtime, iteration=2,
        check_point="A02-K3: deliverable / best-experiment return",
        policy="select_committed_candidate (fidelity.py:184-213) via "
               "get_deliverable_experiment",
        considered=_considered(runtime),
        chosen_candidate_id="c01_good_hex",
        reason=(
            "both candidates are TIER_FULL under the same granted class, so the "
            "tier keys tie and the score decides"
        ),
        source_score_event_id=round_ids[1],
        theta_payload=theta_payload,
    )
    scenarios[scenario] = {
        "rounds": [low, high, _round_record(runtime, third, 2)],
        "decisions": decision,
        "checks": [c for c in checks.items],
        "pass": checks.passed,
        "workdir": str(runtime.workspace_dir),
    }

    # ------------------------------------------------------------------ #
    # scenario 2: reversed order — selection follows the score, not recency
    # ------------------------------------------------------------------ #
    scenario = "reversed_order"
    checks2 = Checks()
    runtime = _runtime(config, eid, candidates, run_dir, scenario)
    theta_payload = _theta(runtime, theta_dict, "full", 1.0, e_star)
    plan = runtime.seams["plan"]
    plan.push("c01_good_hex")
    plan.push("c02_baseline_upstream")
    plan.push("c14_near_zero")
    ids: List[str] = []
    for index in range(3):
        tick = time.monotonic()
        node = _run_round(runtime, _full_grant())
        ids.append(_emit_round_traces(
            writer, runtime, node, iteration=100 + index,
            theta_payload=theta_payload, fr=fr, config=config, budget=budget,
            elapsed=time.monotonic() - tick,
        ))
    third = runtime.strategy.node_history[2]
    decision2 = _decisions(runtime)
    checks2.add(
        "A02-K2-REVERSED",
        "with the low scorer evaluated *last*, the next round's parent is still "
        "the high scorer (c01, node 0)",
        {"parent_node_id": 0, "parent_candidate_id": "c01_good_hex"},
        {"parent_node_id": third.parent_node_id,
         "parent_candidate_id": _candidate_of(
             runtime, runtime.strategy.node_history[third.parent_node_id])},
        {"node_history": decision2["node_history"]},
    )
    checks2.add(
        "A02-K3-REVERSED",
        "the deliverable is likewise the high scorer, not the newest node",
        {"deliverable_node_id": 0, "candidate_id": "c01_good_hex"},
        {"deliverable_node_id": decision2["deliverable_node_id"],
         "candidate_id": decision2["deliverable_candidate_id"]},
        {},
    )
    _emit_selection(
        writer, runtime, iteration=102,
        check_point="A02-K2-REVERSED: recency control",
        policy="parent_policy=best",
        considered=_considered(runtime),
        chosen_candidate_id="c01_good_hex",
        reason=(
            "the high scorer was evaluated first and is still the parent after a "
            "lower-scoring node was added: the decision tracks the score, not "
            "node recency"
        ),
        source_score_event_id=ids[0],
        theta_payload=theta_payload,
    )
    scenarios[scenario] = {"decisions": decision2, "checks": checks2.items,
                           "pass": checks2.passed,
                           "workdir": str(runtime.workspace_dir)}
    checks.items.extend(checks2.items)

    # ------------------------------------------------------------------ #
    # scenario 3: exact tie — A02-K7
    # ------------------------------------------------------------------ #
    scenario = "tie_break"
    checks3 = Checks()
    runtime = _runtime(config, eid, candidates, run_dir, scenario)
    theta_payload = _theta(runtime, theta_dict, "full", 1.0, e_star)
    plan = runtime.seams["plan"]
    plan.push("c01_good_hex")
    plan.push("c03_mirror")
    plan.push("c14_near_zero")
    ids = []
    for index in range(3):
        tick = time.monotonic()
        node = _run_round(runtime, _full_grant())
        ids.append(_emit_round_traces(
            writer, runtime, node, iteration=200 + index,
            theta_payload=theta_payload, fr=fr, config=config, budget=budget,
            elapsed=time.monotonic() - tick,
        ))
    history = runtime.strategy.node_history
    third = history[2]
    decision3 = _decisions(runtime)
    checks3.add(
        "A02-K7",
        "with exactly equal scores the first node in node_history wins "
        "(Python max semantics), for parent and deliverable alike",
        {"scores": [refs["c01_good_hex"].objective, refs["c03_mirror"].objective],
         "best_node_id": 0, "deliverable_node_id": 0, "parent_node_id": 0},
        {"scores": [history[0].score, history[1].score],
         "best_node_id": decision3["best_node_id"],
         "deliverable_node_id": decision3["deliverable_node_id"],
         "parent_node_id": third.parent_node_id},
        {"distinct_candidates": [history[0].branch_name, history[1].branch_name]},
    )
    _emit_selection(
        writer, runtime, iteration=202,
        check_point="A02-K7: equal-score tie-break",
        policy="parent_policy=best; max() over node_history order",
        considered=_considered(runtime),
        chosen_candidate_id="c01_good_hex",
        reason=(
            "the two candidates are an exact tie (c03 is c01 mirrored: identical "
            "metrics, different bytes); max() returns the first maximal element"
        ),
        source_score_event_id=ids[0],
        theta_payload=theta_payload,
        tie_break="first node in node_history order (insertion order)",
    )
    scenarios[scenario] = {"decisions": decision3, "checks": checks3.items,
                           "pass": checks3.passed,
                           "workdir": str(runtime.workspace_dir)}
    checks.items.extend(checks3.items)

    # ------------------------------------------------------------------ #
    # scenario 4: null / error score and a tampering candidate — A02-K5
    # ------------------------------------------------------------------ #
    scenario = "error_and_tamper"
    checks4 = Checks()
    runtime = _runtime(config, eid, candidates, run_dir, scenario)
    theta_payload = _theta(runtime, theta_dict, "full", 1.0, e_star)
    plan = runtime.seams["plan"]
    plan.push("c01_good_hex")
    plan.push("c10_raises")
    plan.push("c02_baseline_upstream", tamper="A0-TAMPER: modified evaluator")
    plan.push("c14_near_zero")
    ids = []
    for index in range(4):
        tick = time.monotonic()
        node = _run_round(runtime, _full_grant())
        ids.append(_emit_round_traces(
            writer, runtime, node, iteration=300 + index,
            theta_payload=theta_payload, fr=fr, config=config, budget=budget,
            elapsed=time.monotonic() - tick,
        ))
    history = runtime.strategy.node_history
    error_node, tamper_node = history[1], history[2]
    decision4 = _decisions(runtime)
    checks4.add(
        "A02-K5-ERROR",
        "a candidate whose E* verdict is error carries no score of record "
        "(None, never 0.0) and never becomes parent or deliverable",
        {"score": None, "best_node_id": 0, "deliverable_node_id": 0,
         "attempts": 0},
        {"score": error_node.score, "best_node_id": decision4["best_node_id"],
         "deliverable_node_id": decision4["deliverable_node_id"],
         "attempts": len(error_node.evaluation_attempts)},
        {"verdict": error_node.feedback or None,
         "evaluation_valid": error_node.evaluation_valid},
    )
    checks4.add(
        "A02-K5-TAMPER",
        "a candidate whose committed evaluation tree differs from the "
        "registered head is rejected by enforce_evaluation_integrity and cannot "
        "become parent or deliverable",
        {"evaluation_valid": False, "score": None,
         "integrity_error_present": True, "best_node_id": 0,
         "deliverable_node_id": 0},
        {"evaluation_valid": tamper_node.evaluation_valid,
         "score": tamper_node.score,
         "integrity_error_present": bool(tamper_node.evaluation_integrity_error),
         "best_node_id": decision4["best_node_id"],
         "deliverable_node_id": decision4["deliverable_node_id"]},
        {"integrity_error": tamper_node.evaluation_integrity_error},
    )
    checks4.add(
        "A02-K5-NEXT-PARENT",
        "the next round's parent is the surviving high scorer (c01, node 0), not "
        "the rejected or scoreless nodes",
        {"parent_node_id": 0, "parent_candidate_id": "c01_good_hex"},
        {"parent_node_id": history[3].parent_node_id,
         "parent_candidate_id": _candidate_of(
             runtime, history[history[3].parent_node_id])},
        {},
    )
    checks4.add(
        "A02-K5-HAD-ERROR-GATE",
        "had_error nodes are invisible to the parent argmax (the third gate of "
        "get_best_experiment, strategy.py:1429-1433), probed on real nodes",
        {"best_node_id_ignoring_had_error": 0},
        {"best_node_id_ignoring_had_error": _had_error_gate_probe(runtime)},
        {"note": "a constructed node with had_error=True and a 9.0 score is "
                 "appended to node_history, the real get_best_experiment() is "
                 "called, and the append is reverted"},
    )
    _emit_selection(
        writer, runtime, iteration=303,
        check_point="A02-K5: scoreless and rejected candidates are ineligible",
        policy="parent_policy=best + enforce_evaluation_integrity "
               "(base.py:740-798)",
        considered=_considered(runtime, include_invalid=True),
        chosen_candidate_id="c01_good_hex",
        reason=(
            "c10_raises has score=None (E* verdict error) and the tampering "
            "candidate has evaluation_valid=False; neither is eligible"
        ),
        source_score_event_id=ids[0],
        theta_payload=theta_payload,
    )
    scenarios[scenario] = {"decisions": decision4, "checks": checks4.items,
                           "pass": checks4.passed,
                           "workdir": str(runtime.workspace_dir)}
    checks.items.extend(checks4.items)

    # ------------------------------------------------------------------ #
    # scenario 5: fast-only high scorer vs full low scorer — A02-K6
    # ------------------------------------------------------------------ #
    scenario = "fast_only"
    checks5 = Checks()
    runtime = _runtime(config, eid, candidates, run_dir, scenario)
    plan = runtime.seams["plan"]
    plan.push("c02_baseline_upstream")
    plan.push("c01_good_hex", fidelity="fast", fraction=0.15)
    plan.push("c14_near_zero")
    full_payload = _theta(runtime, theta_dict, "full", 1.0, e_star)
    fast_payload = _theta(runtime, theta_dict, "fast", 0.15, e_star)
    ids = []
    tick = time.monotonic()
    node = _run_round(runtime, _full_grant())
    ids.append(_emit_round_traces(
        writer, runtime, node, iteration=400,
        theta_payload=full_payload, fr=fr, config=config, budget=budget,
        elapsed=time.monotonic() - tick,
    ))
    tick = time.monotonic()
    node = _run_round(runtime, _fast_grant())
    ids.append(_emit_round_traces(
        writer, runtime, node, iteration=401,
        theta_payload=fast_payload, fr=fr, config=config, budget=budget,
        elapsed=time.monotonic() - tick,
    ))
    tick = time.monotonic()
    node = _run_round(runtime, _full_grant())
    ids.append(_emit_round_traces(
        writer, runtime, node, iteration=402,
        theta_payload=full_payload, fr=fr, config=config, budget=budget,
        elapsed=time.monotonic() - tick,
    ))
    history = runtime.strategy.node_history
    fast_node, full_node = history[1], history[0]
    decision5 = _decisions(runtime)
    from kapso.execution.fidelity import TIER_FULL, TIER_PROBE, evidence_tier

    evaluator_id = runtime.strategy.registered_evaluator_id
    checks5.add(
        "A02-K6",
        "a fast-only high scorer does not win the deliverable against a "
        "full-tier candidate, but it does win the parent (the two objects are "
        "not the same)",
        {"fast_tier": TIER_PROBE, "full_tier": TIER_FULL,
         "parent_node_id": 1, "deliverable_node_id": 0,
         "fast_score_higher": True},
        {"fast_tier": evidence_tier(fast_node, evaluator_id),
         "full_tier": evidence_tier(full_node, evaluator_id),
         "parent_node_id": history[2].parent_node_id,
         "deliverable_node_id": decision5["deliverable_node_id"],
         "fast_score_higher": (
             fast_node.score is not None and full_node.score is not None
             and fast_node.score > full_node.score
         )},
        {"fast_score": fast_node.score, "full_score": full_node.score,
         "fast_attempts": [a.to_dict() for a in fast_node.evaluation_attempts],
         "full_attempts": [a.to_dict() for a in full_node.evaluation_attempts],
         "manifest_class_matched_the_grant": True,
         "note": "the fast node's manifest triple matched its fast grant, so "
                 "this is K06's eligibility rule and not a manifest mismatch"},
    )
    checks5.add(
        "A02-K6-CLASS",
        "the fast node's recorded attempt carries the fast class the grant "
        "issued (fidelity fast, fraction 0.15)",
        {"fidelity": "fast", "fraction": 0.15},
        {"fidelity": fast_node.evaluation_attempts[0].fidelity,
         "fraction": fast_node.evaluation_attempts[0].fraction},
        {"grant": {"fidelity": "fast", "fraction": 0.15}},
    )
    _emit_selection(
        writer, runtime, iteration=402,
        check_point="A02-K6: tier outranks score for the deliverable",
        policy="select_committed_candidate (fidelity.py:184-213), tier walk",
        considered=_considered(runtime),
        chosen_candidate_id="c02_baseline_upstream",
        reason=(
            "the fast-only node is TIER_PROBE and ineligible for the committed "
            "slot, so the TIER_FULL low scorer takes the deliverable while the "
            "fast node remains the parent"
        ),
        source_score_event_id=ids[0],
        theta_payload=full_payload,
        tie_break=None,
    )
    scenarios[scenario] = {"decisions": decision5, "checks": checks5.items,
                           "pass": checks5.passed,
                           "workdir": str(runtime.workspace_dir)}
    checks.items.extend(checks5.items)

    writer.close()
    validation = writer.validate(config)

    report = {
        "schema": "a0.kapso.selection/v1",
        "runtime": "kapso",
        "run_id": run_id,
        "eid_star": eid.eid_star,
        "eid_r": eid_r,
        "theta_E": theta_dict,
        "selection_declaration": selection_payload(config),
        "e_star_identity": e_star,
        "frozen_conditions": {
            "parent_policy": "best",
            "fidelity_mode": "off",
            "maximize_scoring": True,
            "one_registered_evaluator_head": True,
        },
        "external_scores": {
            candidate_id: {
                "exit_code": result.exit_code,
                "status": result.status,
                "objective": result.objective,
            }
            for candidate_id, result in refs.items()
        },
        "scenarios": scenarios,
        "checks": checks.items,
        "failures": checks.failed(),
        "pass": checks.passed,
        "seams": {
            "ideation": runtime.seams["ideation"],
            "implementation": runtime.seams["implementation"],
            "judge": runtime.seams["judge"],
            "note": runtime.seams["note"],
        },
        "unverified": (
            "the LLM-driven end-to-end path (a real ideation session proposing a "
            "change and a real implementation session writing and evaluating it) "
            "is UNVERIFIED on this host; the scores that drove these selections "
            "were produced by real E* runs through KAPSO's registered-evaluation "
            "command, and the selection code that consumed them is unmodified "
            "runtime code."
        ),
        "contract_note": (
            "selection.source_score_event_id is now populated (it names the "
            "score event of the run's merged stream, traces/"
            "<runtime>.<run_id>.all.jsonl). The earlier record's "
            "`contract_defect` note is void: the 2026-09-20 arbitration made "
            "the RUN the validation unit (contract/README.md section 8, item 3; "
            "adapter_contract.md section 6.3), and this adapter validates with "
            "`trace_validate.py validate-run`."
        ),
        "failure_stage_counts": {
            "counts": writer.failure_stage_counts(),
            "counts_score_trace_only": writer.failure_stage_counts_score_trace(),
            "note": "declared by the adapter from its own emitted events, one "
                    "unit per (iteration, candidate_id, stage) so a failure "
                    "reported on both the score and the resource event of a "
                    "unit is counted once (plan:577, plan:628). `counts` is over "
                    "the run's merged stream (the validation unit); "
                    "`counts_score_trace_only` is the same rule over the score "
                    "trace alone. The mapping is the A0-wide table in "
                    "contract/selection/kapso.selection.json.",
            "source": str(run_dir / "traces" / f"kapso.{run_id}.score.jsonl"),
        },
        "trace_validation": validation,
        "trace_paths": writer.paths(),
        "elapsed_sec": round(time.monotonic() - started, 6),
    }
    write_json(run_dir / "a02.json", report)
    return report


def _theta(runtime: KapsoRuntime, theta: Dict[str, Any], fidelity: str,
           fraction: float, e_star: Dict[str, Any]) -> Dict[str, Any]:
    extra = {
        "registered_command": runtime.registration.command_full,
        "registered_subsample_seed": runtime.maintainer.subsample_seed,
        "fidelity_mode": runtime.config_evidence["fidelity_mode"],
        "parent_policy": runtime.config_evidence["parent_policy_param"],
        "max_change_requests": runtime.config_evidence["max_change_requests"],
        "granted_class": {"eval_fidelity": fidelity,
                          "eval_fraction": fraction},
        # See a01.py:_theta_payload: the wrapper (EID_r input) and E*'s own
        # evaluator-source digest are different files and are named apart
        # (audit finding F1).
        "registered_wrapper_sha256": runtime.tree_record["files"][
            "kapso_eval.py"
        ],
    }
    if e_star.get("pass"):
        extra["e_star_evaluator_source_sha256"] = e_star[
            "e_star_evaluator_source_sha256"
        ]
        extra["e_star_version"] = e_star.get("e_star_version")
    return {
        "seed": int(theta["seed"]),
        "fidelity": fidelity,
        "fraction": fraction,
        "defaults_applied": {},
        "extra": extra,
    }


def _considered(runtime: KapsoRuntime, include_invalid: bool = False
                ) -> List[Dict[str, Any]]:
    considered = []
    for node in runtime.strategy.node_history:
        if not include_invalid and (
            node.had_error or not node.evaluation_valid or node.score is None
        ):
            continue
        candidate_id = _candidate_of(runtime, node)
        if candidate_id is None:
            continue
        considered.append({"candidate_id": candidate_id,
                           "search_signal": node.score})
    if not considered:
        considered.append({"candidate_id": "none", "search_signal": None})
    return considered


def _had_error_gate_probe(runtime: KapsoRuntime) -> Optional[int]:
    """Probe get_best_experiment()'s had_error gate on real nodes, then revert."""
    from kapso.execution.search_strategies.base import SearchNode

    strategy = runtime.strategy
    decoy = SearchNode(node_id=9999, branch_name="decoy_had_error")
    decoy.score = 9.0
    decoy.had_error = True
    decoy.evaluation_valid = True
    strategy.node_history.append(decoy)
    try:
        best = strategy.get_best_experiment()
        return None if best is None else best.node_id
    finally:
        strategy.node_history.remove(decoy)
