"""A0.1 — evaluator integration conformance for the KAPSO adapter.

For every candidate ``c`` in the frozen ``C*``:

* ``E*(c)`` — the frozen reference evaluator, run directly on the pristine
  candidate directory (``channels.run_reference_e_star``);
* ``E_r(c)`` — KAPSO's registered evaluation, run through KAPSO's own command
  composition, tree sync and frame run (``channels.run_registered_channel`` +
  ``runtime.frame_eval``);
* the verdict comparison, including the *verdict* (ok / invalid / error) and the
  explicit absence of a numeric score where E* reports none;
* the manifest-triple invariant (A01.4) and the out-of-band evaluator-identity
  leg (A01.5), each recorded from real runtime state.

Two falsification controls are run inside the same invocation: a deliberate E*
source drift (the registered wrapper must refuse to score) and a deliberate
grant/class mismatch (KAPSO's ``manifest_of_record`` must return None).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .channels import run_reference_e_star, run_registered_channel
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
    write_json,
)
from .runtime import KapsoRuntime, _tree_fingerprint

THETA_KEYS = ("seed", "fidelity", "fraction")


def _theta_payload(runtime: KapsoRuntime, theta: Dict[str, Any],
                   granted: Dict[str, Any],
                   e_star: Dict[str, Any]) -> Dict[str, Any]:
    extra = {
        "registered_command": runtime.registration.command_full,
        "registered_subsample_seed": runtime.maintainer.subsample_seed,
        "fidelity_mode": runtime.config_evidence["fidelity_mode"],
        "parent_policy": runtime.config_evidence["parent_policy_param"],
        "max_change_requests": runtime.config_evidence["max_change_requests"],
        "granted_class": {
            "eval_fidelity": granted["eval_fidelity"],
            "eval_fraction": granted["eval_fraction"],
            "profile": granted["profile"],
        },
        # Two different files carry "evaluator source" here, and naming them
        # apart is the point: `registered_wrapper_sha256` is the adapter's
        # `kapso_eval.py` (the input to EID_r), while
        # `e_star_evaluator_source_sha256` is E*'s OWN evaluator-source digest,
        # the same value the manifest line and every Outcome carry. An earlier
        # revision published only the wrapper digest under the ambiguous name
        # `evaluator_source_sha256`, so a run-to-run join on that key read the
        # wrapper's changes as evaluator drift (audit finding F1).
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
        "fidelity": str(theta["fidelity"]),
        "fraction": float(theta["fraction"]),
        "defaults_applied": {},
        "extra": extra,
    }


def run_a01(
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
    repeats: int = 3,
    repeat_candidate: str = "c01_good_hex",
) -> Dict[str, Any]:
    started = time.monotonic()
    run_dir = Path(run_dir)
    # Run state (E* state dirs, reference outcomes, logs) lives inside the run
    # dir, so a caller's invocation is self-contained and two runs never share
    # evaluator state.
    state_root = run_dir / "state"
    runtime = KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=run_dir,
        state_root=state_root,
    )
    baseline = next(c for c in candidates if c.role == "baseline")
    runtime.prepare(baseline)

    theta_dict = {
        "seed": theta.seed,
        "fidelity": theta.fidelity,
        "fraction": theta.fraction,
    }
    eid_r = eid_r_payload(
        eid.eid_star,
        runtime.registration.evaluator_id,
        "KAPSO's native evaluator identity: EID_r = "
        "manifest_fingerprint(kapso_evaluation/) over the two-file registered "
        "tree this adapter installs (execution/evaluation_integrity.py:112-119, "
        "maintainer.py:216-218). a0_locator.json carries EID*'s EvaluatorSource "
        "records and canonical theta_E; kapso_eval.py re-hashes E*'s sources on "
        "every invocation and exits 3 without a score on any mismatch, so "
        "EID_r cannot be produced by a different E*.",
    )
    writer = TraceWriter(
        run_dir, "kapso", run_id, "circle-packing", eid.eid_star, eid_r, kinds
    )
    granted = {"profile": "full", "eval_fidelity": "full", "eval_fraction": 1.0}
    e_star = e_star_identity(config)
    theta_payload = _theta_payload(runtime, theta_dict, granted, e_star)

    per_candidate: List[Dict[str, Any]] = []
    mismatches: List[str] = []
    for index, candidate in enumerate(candidates):
        unit_started = time.monotonic()
        branch = runtime.create_candidate_branch(candidate)
        reference = run_reference_e_star(
            config, eid, candidate.candidate_id, candidate.path, theta_dict,
            state_root,
        )
        registered = runtime.registered_channel_for_branch(
            candidate.candidate_id, branch, theta_dict
        )
        branch_tree = _branch_tree_fingerprint(runtime, branch)

        from kapso.execution.search_strategies.base import SearchNode

        node = SearchNode(node_id=index, branch_name=branch)
        frame_score = runtime.frame_eval(
            node, fidelity="full", fraction=1.0, deadline_seconds=120.0
        )
        attempts = [attempt.to_dict() for attempt in node.evaluation_attempts]

        verdict = _compare(
            reference=reference,
            registered=registered,
            frame_score=frame_score,
            attempts=attempts,
            registered_evaluator_id=runtime.registration.evaluator_id,
            branch_tree_fingerprint=branch_tree,
            epsilon=eid.epsilon,
            granted=granted,
        )
        if not verdict["pass"]:
            mismatches.extend(
                f"{candidate.candidate_id}: {reason}"
                for reason in verdict["reasons"]
            )

        reference_fields = {
            key: value
            for key, value in reference.fields.items()
            if key in set(
                eid.components["MetricDefinition"]["value"]["outcome_fields"]
            )
        }
        scalarization = _scalarization_identity(eid, reference)
        if not scalarization["pass"]:
            mismatches.append(
                f"{candidate.candidate_id}: {scalarization['detail']}"
            )
        reference_fields["e_star_status"] = reference.status
        reference_fields["e_star_exit_code"] = reference.exit_code
        if reference.failure_kind:
            reference_fields["e_star_failure_kind"] = reference.failure_kind
        outcome = {"fields": reference_fields,
                   "cardinality": len(reference_fields)}

        stage, detail = _failure_stage(reference, verdict)
        evidence = {
            "status": verdict["evaluator_evidence_status"],
            "detail": verdict["evaluator_evidence_detail"],
        }
        writer.emit_score(
            candidate_id=candidate.candidate_id,
            iteration=0,
            parent_id=None,
            theta_e=theta_payload,
            outcome=outcome,
            fr=fr,
            search_signal=registered.score,
            evaluator_evidence=evidence,
            failure_stage=stage,
            failure_detail=detail,
        )
        writer.emit_resource(
            candidate_id=candidate.candidate_id,
            iteration=0,
            parent_id=None,
            theta_e=theta_payload,
            t_wall_sec=time.monotonic() - unit_started,
            n_evaluator_calls=3,
            concurrency_cap=int(budget.get("concurrency", 1)),
            concurrency_observed=1,
            scope="delta",
            secondary={"N_modelCalls": 0, "T_in": None, "T_out": None,
                       "C_usd": None},
            budget_hard={
                "T_wall_sec": budget.get("T_wall_sec"),
                "N_evaluatorCalls": budget.get("N_evaluatorCalls"),
                "concurrency_cap": int(budget.get("concurrency", 1)),
            },
            failure_stage=stage,
            failure_detail=detail,
        )

        per_candidate.append(
            {
                "candidate_id": candidate.candidate_id,
                "role": candidate.role,
                "solution_sha256": candidate.solution_sha256,
                "branch": branch,
                "reference": {
                    "exit_code": reference.exit_code,
                    "status": reference.status,
                    "objective": reference.objective,
                    "failure_kind": reference.failure_kind,
                    "canonical_digest": reference.outcome.get("canonical_digest"),
                    "fields": reference.fields,
                    "elapsed_sec": round(reference.elapsed_sec, 6),
                    "command": reference.command,
                },
                "registered_channel": {
                    "exit_code": registered.exit_code,
                    "status": registered.status,
                    "score": registered.score,
                    "manifest": registered.manifest,
                    "manifest_field_check": _manifest_field_check(
                        registered.manifest
                    ),
                    "manifest_triple": _manifest_triple(registered.manifest),
                    "elapsed_sec": round(registered.elapsed_sec, 6),
                    "command": registered.command,
                },
                "frame_run": {
                    "score": frame_score,
                    "attempts": attempts,
                    "attempt_count": len(attempts),
                },
                "branch_registered_tree_fingerprint": branch_tree,
                "scalarization_identity": scalarization,
                "verdict": verdict,
            }
        )

    repeats_evidence = _repeats(
        config, eid, runtime, candidates, repeat_candidate, theta_dict,
        state_root, repeats,
    )
    controls = _controls(config, eid, runtime, candidates, theta_dict)

    writer.close()
    validation = writer.validate(config)

    conformance = {
        "schema": "a0.kapso.conformance/v1",
        "runtime": "kapso",
        "run_id": run_id,
        "eid_star": eid.eid_star,
        "eid_r": eid_r,
        "eid_star_checks": {
            "verify": "run before the evaluation loop (see eid_checks.json)",
            "epsilon": eid.epsilon,
        },
        "theta_E": theta_payload,
        "fr": fr,
        "selection": selection_payload(config),
        "e_star_identity": e_star,
        "frozen_conditions": runtime.config_evidence,
        "registration": runtime.registration.__dict__,
        "capability_note": (
            "A0.1 as run here exercises the runtime's registered-evaluation "
            "path with the real maintainer, real tree sync, real manifest "
            "parser and real frame-run subprocess. The LLM-driven session that "
            "would normally invoke the registered command is replaced by a "
            "documented seam (a0_adapter/seams.py); the full end-to-end path is "
            "UNVERIFIED."
        ),
        "candidates": per_candidate,
        "repeats": repeats_evidence,
        "controls": controls,
        "mismatches": mismatches,
        # A discoverable verdict string, for harnesses that look for "verdict"
        # (a0/conformance/conformance.py:906).  The harness recomputes the
        # comparison from the per-candidate rows and only records this field.
        "verdict": "pass" if not mismatches and controls["pass"] else "fail",
        "adapter_setup_log": list(runtime.setup_log),
        "pass": not mismatches and controls["pass"],
        "failure_stage_counts": {
            "counts": writer.failure_stage_counts(),
            "counts_score_trace_only": writer.failure_stage_counts_score_trace(),
            "note": "declared by the adapter from its own emitted events, one "
                    "unit per (iteration, candidate_id, stage) so a failure "
                    "reported on both the score and the resource event of a "
                    "unit is counted once (plan:577, plan:628, trace_validate.py "
                    "count_failure_stages). `counts` is over the run's merged "
                    "stream (the validation unit); `counts_score_trace_only` is "
                    "the same rule over the score trace alone, which is what "
                    "a0/conformance/conformance.py counts when an adapter "
                    "declares nothing. The mapping is the A0-wide table in "
                    "contract/selection/kapso.selection.json",
            "source": str(run_dir / "traces" /
                          f"kapso.{run_id}.score.jsonl"),
        },
        "trace_validation": validation,
        "elapsed_sec": round(time.monotonic() - started, 6),
    }
    write_json(run_dir / "conformance.json", conformance)
    write_json(run_dir / "eid_mapping.json",
               {"eid_star": eid.eid_star, "eid_r": eid_r,
                "registered_tree": runtime.tree_record})
    write_json(run_dir / "registered_tree.json", runtime.tree_record)
    conformance["trace_paths"] = writer.paths()
    return conformance


def _branch_tree_fingerprint(runtime: KapsoRuntime, branch: str) -> Optional[str]:
    try:
        with runtime.strategy.workspace.materialize_ref(branch) as worktree:
            manifest, fingerprint = _tree_fingerprint(
                Path(worktree) / "kapso_evaluation"
            )
        return fingerprint
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed silently
        return f"<unavailable: {type(exc).__name__}: {exc}>"


def _manifest_field_check(manifest: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trap A01-T2: KAPSO's manifest keys carry no evaluator identity.

    ``parse_manifest_line`` (``maintainer.py:64-83``) requires exactly
    ``fidelity, fraction, seed, items, total_items`` and reads ``score``
    separately, so the protocol's phrase "manifest triple
    ``(evaluator, fidelity, fraction, seed)``" describes a field that does not
    exist.  The adapter's own extra keys are listed separately: they are not
    part of KAPSO's contract, and the evaluator-identity leg is asserted out of
    band instead (registry fingerprint + executed-tree fingerprint).
    """
    if not manifest:
        return {"present": False}
    kapsos_keys = {"fidelity", "fraction", "seed", "items", "total_items", "score"}
    contract_keys = sorted(key for key in manifest if key in kapsos_keys)
    adapter_keys = sorted(key for key in manifest if key not in kapsos_keys)
    return {
        "present": True,
        "kapsos_contract_keys": contract_keys,
        "adapter_extra_keys": adapter_keys,
        "evaluator_identity_field_in_kapsos_keys": any(
            "evaluator" in key.lower() for key in contract_keys
        ),
    }


def _manifest_triple(manifest: Optional[Dict[str, Any]]):
    if not manifest:
        return None
    return {
        "fidelity": manifest.get("fidelity"),
        "fraction": manifest.get("fraction"),
        "seed": manifest.get("seed"),
        "has_score_key": "score" in manifest,
    }


def _compare(
    *,
    reference: Any,
    registered: Any,
    frame_score: Optional[float],
    attempts: List[Dict[str, Any]],
    registered_evaluator_id: str,
    branch_tree_fingerprint: Optional[str],
    epsilon: float,
    granted: Dict[str, Any],
) -> Dict[str, Any]:
    reasons: List[str] = []
    if reference.status != registered.status:
        reasons.append(
            f"status mismatch: E*={reference.status} E_r={registered.status}"
        )
    if reference.exit_code != registered.exit_code:
        reasons.append(
            f"exit-code mismatch: E*={reference.exit_code} "
            f"E_r={registered.exit_code}"
        )
    if reference.objective is not None:
        if registered.score is None:
            reasons.append("E* scored the candidate but E_r reported no score")
        elif abs(registered.score - reference.objective) > epsilon:
            reasons.append(
                f"scalar mismatch: E_r={registered.score!r} "
                f"E*={reference.objective!r}"
            )
        if frame_score is None:
            reasons.append(
                "KAPSO's frame run recorded no score for a scored candidate"
            )
        elif abs(frame_score - reference.objective) > epsilon:
            reasons.append(
                f"frame-run score {frame_score!r} != E* {reference.objective!r}"
            )
        if len(attempts) != 1:
            reasons.append(
                f"expected exactly one recorded attempt, got {len(attempts)}"
            )
    else:
        # The false-green trap: a non-ok verdict must not become a number.
        if registered.score is not None:
            reasons.append(
                f"E_r collapsed the {reference.status} verdict into the score "
                f"{registered.score!r}"
            )
        if frame_score is not None:
            reasons.append(
                f"the frame run produced {frame_score!r} for a "
                f"{reference.status} verdict"
            )
        if attempts:
            reasons.append(
                f"a non-ok verdict produced {len(attempts)} recorded attempt(s)"
            )
        if registered.manifest is not None and "score" in registered.manifest:
            reasons.append("the manifest line carried a score key for a non-ok verdict")

    # A01.4: (fidelity, fraction, seed) == the granted decision. There is no
    # evaluator field in the manifest (trap A01-T2), so identity is asserted
    # separately below.
    triple = _manifest_triple(registered.manifest)
    if triple is None:
        reasons.append("no KAPSO_EVAL_MANIFEST line was parsed")
    else:
        if triple["fidelity"] != granted["eval_fidelity"]:
            reasons.append(
                f"manifest fidelity {triple['fidelity']!r} != granted "
                f"{granted['eval_fidelity']!r}"
            )
        if triple["fraction"] is None or abs(
            float(triple["fraction"]) - granted["eval_fraction"]
        ) > 1e-9:
            reasons.append(
                f"manifest fraction {triple['fraction']!r} != granted "
                f"{granted['eval_fraction']!r}"
            )

    # A01.5: the identity leg, out of band.
    if attempts and any(
        attempt["evaluator_id"] != registered_evaluator_id for attempt in attempts
    ):
        reasons.append(
            "a recorded attempt carries an evaluator_id different from the "
            "registered head"
        )
    if branch_tree_fingerprint != registered_evaluator_id:
        reasons.append(
            f"the branch's evaluation tree fingerprint "
            f"{branch_tree_fingerprint!r} != the registered evaluator id "
            f"{registered_evaluator_id!r}: the executed tree is not the "
            "registered head's"
        )

    status = "ok"
    detail = None
    if reasons:
        status = "manifest_mismatch"
        detail = "; ".join(reasons)
    return {
        "pass": not reasons,
        "reasons": reasons,
        "status_match": reference.status == registered.status,
        "exit_match": reference.exit_code == registered.exit_code,
        "scalar_match": (
            reference.objective is None and registered.score is None
        ) or (
            reference.objective is not None
            and registered.score is not None
            and abs(registered.score - reference.objective) <= epsilon
        ),
        "no_synthetic_score": (
            reference.objective is not None
        ) or (
            registered.score is None and frame_score is None and not attempts
        ),
        "attempt_count": len(attempts),
        "manifest_triple": triple,
        "evaluator_evidence_status": status,
        "evaluator_evidence_detail": detail,
    }


def _scalarization_identity(eid: EidStar, reference: Any) -> Dict[str, Any]:
    """The A0-wide scalarization rule, checked on E*'s own outcome.

    `contract/selection/kapso.selection.json` (adopting
    `a0/contract/adapter_contract.md` section 5.3) says the scalar is defined
    **iff** `status == "ok"`, and that a null scalar is never a number. Both
    halves are asserted here on the reference channel, so the declaration is a
    measurement and not a promise:

    * `status == "ok"`   -> `outcome.fields.sum_radii == outcome.objective.value`
    * `status != "ok"`   -> `outcome.fields.sum_radii` is absent, never `0.0`
    """
    primary = eid.primary_field
    value = reference.fields.get(primary)
    objective = reference.objective
    if reference.status == "ok":
        ok = objective is not None and value is not None and float(value) == float(objective)
        detail = None if ok else (
            f"scalarization identity: status ok but fields.{primary}={value!r} != "
            f"objective.value={objective!r}"
        )
    else:
        ok = value is None and objective is None
        detail = None if ok else (
            f"scalarization identity: status {reference.status} must leave the "
            f"scalar undefined, but fields.{primary}={value!r} / "
            f"objective.value={objective!r} carried a number"
        )
    return {
        "rule": "contract/selection/kapso.selection.json scalarization.status_gate "
                "+ identity_check (A0-wide, adapter_contract.md section 5.3)",
        "status": reference.status,
        "field": primary,
        "field_value": value,
        "objective_value": objective,
        "pass": ok,
        "detail": detail,
    }


def _failure_stage(reference: Any, verdict: Dict[str, Any]):
    """FailureStage for one unit, from the A0-wide mapping table.

    The verdict -> stage table is frozen A0-wide
    (``a0/contract/adapter_contract.md`` section 5.3 and
    ``contract/selection/kapso.selection.json``); this function only picks the
    row, so KAPSO's counts join SimpleLoop's, EvE's and Loreley's.  The one
    KAPSO-specific row precedes the table: ``evaluator_failed`` when the
    adapter's own comparison failed, or the manifest class did not match its
    grant -- the A0.1 conformance failure the protocol names (plan:538,
    ACCEPTANCE A01.6).
    """
    if not verdict["pass"]:
        return "evaluator_failed", "; ".join(verdict["reasons"])
    stage = failure_stage(reference.status, reference.exit_code,
                          reference.failure_kind)
    if stage == "none":
        return stage, None
    return (
        stage,
        f"E* verdict {reference.status} (exit {reference.exit_code}, failure "
        f"kind {reference.failure_kind}): reproduced faithfully by E_r, no "
        f"score of record",
    )


def _repeats(
    config: AdapterConfig,
    eid: EidStar,
    runtime: KapsoRuntime,
    candidates: List[Candidate],
    candidate_id: str,
    theta: Dict[str, Any],
    state_root: Path,
    repeats: int,
) -> Dict[str, Any]:
    candidate = next(c for c in candidates if c.candidate_id == candidate_id)
    branch = runtime.candidate_branch(candidate)
    scores: List[float] = []
    statuses: List[str] = []
    digests: List[str] = []
    for _ in range(repeats):
        result = runtime.registered_channel_for_branch(candidate_id, branch, theta)
        if result.score is not None:
            scores.append(result.score)
        statuses.append(str(result.status))
        digests.append(str((result.manifest or {}).get("e_star_canonical_digest")))
    spread = (max(scores) - min(scores)) if scores else None
    return {
        "candidate_id": candidate_id,
        "repeats": repeats,
        "scores": scores,
        "statuses": statuses,
        "canonical_digests": digests,
        "spread": spread,
        "epsilon": eid.epsilon,
        "within_epsilon": (spread is None) or (spread <= eid.epsilon),
        "distinct_digests": len(set(digests)),
        "verdict": (
            "deterministic at full fidelity (identical canonical digests); the "
            "frozen epsilon=1e-9 covers the observed spread"
            if len(set(digests)) == 1
            else "NON-DETERMINISTIC: E* returned different canonical digests "
                 "for identical inputs"
        ),
    }


def _controls(
    config: AdapterConfig,
    eid: EidStar,
    runtime: KapsoRuntime,
    candidates: List[Candidate],
    theta: Dict[str, Any],
) -> Dict[str, Any]:
    """Falsification controls: the binding must fail when it should."""
    c01 = next(c for c in candidates if c.candidate_id == "c01_good_hex")

    def drift_mutate(tree: Path) -> None:
        locator_path = tree / "a0_locator.json"
        locator = json.loads(locator_path.read_text("utf-8"))
        locator["e_star"]["source_records"][0]["sha256"] = "0" * 64
        locator_path.write_text(
            json.dumps(locator, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    drift_tree = runtime.scratch_tree(drift_mutate)
    control_tree = runtime.scratch_tree(lambda tree: None)
    drift = run_registered_channel(
        "control_e_star_drift",
        command=f"python {drift_tree.name}/kapso_eval.py --fidelity full "
                f"--fraction 1.0 --seed 1337 --candidate {c01.path}",
        cwd=drift_tree.parent,
        theta=theta,
    )
    control = run_registered_channel(
        "control_no_drift",
        command=f"python {control_tree.name}/kapso_eval.py --fidelity full "
                f"--fraction 1.0 --seed 1337 --candidate {c01.path}",
        cwd=control_tree.parent,
        theta=theta,
    )

    # A01.4 enforcement: a fast-class session output against a full grant.
    from kapso.execution.fidelity import FidelityDecision
    from kapso.execution.search_strategies.base import SearchNode
    from kapso.execution.search_strategies.generic.registered_evaluation import (
        manifest_of_record,
    )

    branch = runtime.candidate_branch(c01)
    fast_theta = {"seed": theta["seed"], "fidelity": "fast", "fraction": 0.15}
    fast_run = runtime.registered_channel_for_branch(
        "c01_good_hex", branch, fast_theta
    )
    node = SearchNode(node_id=0, branch_name=branch)
    node.evaluation_output = fast_run.stdout
    full_grant = FidelityDecision(
        profile="full", build_fidelity="full", eval_fidelity="full",
        eval_fraction=1.0, reason="fidelity off",
    )
    fast_grant = FidelityDecision(
        profile="probe", build_fidelity="full", eval_fidelity="fast",
        eval_fraction=0.15, reason="control: the class the session actually ran",
    )
    mismatch = manifest_of_record(
        node,
        registered_evaluation_command=runtime.maintainer.evaluation_command(
            fidelity="full", fraction=1.0
        ),
        fidelity_decision=full_grant,
        registered_subsample_seed=runtime.maintainer.subsample_seed,
    )
    accepted = manifest_of_record(
        node,
        registered_evaluation_command=runtime.maintainer.evaluation_command(
            fidelity="fast", fraction=0.15
        ),
        fidelity_decision=fast_grant,
        registered_subsample_seed=runtime.maintainer.subsample_seed,
    )

    drift_ok = (
        drift.exit_code == 3
        and drift.manifest is None
        and "drifted" in drift.stderr
    )
    control_ok = control.exit_code == 0 and control.score is not None
    mismatch_ok = mismatch is None and accepted is not None
    gauge = _candidate_gate_control(config, runtime, c01, theta)
    return {
        "e_star_source_drift": {
            "what": "the registered wrapper's EID* EvaluatorSource binding, with "
                    "one recorded E* file digest corrupted",
            "exit_code": drift.exit_code,
            "manifest_parsed": drift.manifest is not None,
            "stderr_tail": drift.stderr.strip().splitlines()[-1]
            if drift.stderr.strip() else "",
            "expected": "exit 3, no manifest, no score",
            "pass": drift_ok,
        },
        "e_star_source_intact": {
            "what": "the same wrapper on an unmodified copy of the tree",
            "exit_code": control.exit_code,
            "score": control.score,
            "pass": control_ok,
        },
        "manifest_class_mismatch": {
            "what": "KAPSO's manifest_of_record with a fast-class session "
                    "output against a full grant (registered_evaluation.py:87-99)",
            "session_ran": {
                "fidelity": fast_run.manifest.get("fidelity") if fast_run.manifest else None,
                "fraction": fast_run.manifest.get("fraction") if fast_run.manifest else None,
                "seed": fast_run.manifest.get("seed") if fast_run.manifest else None,
            },
            "grant": {"fidelity": "full", "fraction": 1.0},
            "manifest_of_record_returned": mismatch,
            "accepted_under_matching_grant": accepted,
            "pass": mismatch_ok,
        },
        "candidate_set_gate": gauge,
        "pass": drift_ok and control_ok and mismatch_ok and gauge["pass"],
    }


def _candidate_gate_control(
    config: AdapterConfig,
    runtime: KapsoRuntime,
    c01: Candidate,
    theta: Dict[str, Any],
) -> Dict[str, Any]:
    """The candidate-set gate is a tree property, not an environment variable.

    A coding-agent session can read `kapso_evaluation/kapso_eval.py` and copy the
    adapter's own sentinel candidate, so the gate must not be switchable from
    inside a session.  Three measurements:

    * the registered tree refuses a non-frozen candidate with the session-style
      environment override set (the leak that was closed);
    * the same environment override *also* has no effect on a scratch tree whose
      locator flag is off;
    * a scratch tree whose locator flag is on (the closure sentinel's tree)
      accepts the candidate and records `in_frozen_set: false` in its manifest.
    """
    sentinel_root = Path(runtime.run_dir) / "candidate_gate_sentinel"
    sentinel_root.mkdir(parents=True, exist_ok=True)
    (sentinel_root / "solution.py").write_text(
        "def pack_circles(n=26):\n"
        "    return [((i + 0.5) / n, 0.5, 0.018) for i in range(n)]\n",
        encoding="utf-8",
    )
    gate_args = (
        "--fidelity full --fraction 1.0 --seed 1337 --candidate {candidate}"
    ).format(candidate=sentinel_root)

    registered_tree = Path(runtime.workspace_dir) / "kapso_evaluation"
    leaked = run_registered_channel(
        "gate_env_override_on_registered_tree",
        command=f"python kapso_evaluation/kapso_eval.py {gate_args}",
        cwd=runtime.workspace_dir,
        theta=theta,
        env_overrides={"A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE": "1"},
    )
    scratch_off = runtime.scratch_tree(
        lambda tree: _set_flag(tree, False)
    )
    scratch_on = runtime.scratch_tree(lambda tree: _set_flag(tree, True))
    off_result = run_registered_channel(
        "gate_scratch_flag_off",
        command=f"python {scratch_off.name}/kapso_eval.py {gate_args}",
        cwd=scratch_off.parent,
        theta=theta,
        env_overrides={"A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE": "1"},
    )
    on_result = run_registered_channel(
        "gate_scratch_flag_on",
        command=f"python {scratch_on.name}/kapso_eval.py {gate_args}",
        cwd=scratch_on.parent,
        theta=theta,
    )
    ok = (
        leaked.exit_code == 3
        and leaked.manifest is None
        and "not a member of the frozen candidate set" in leaked.stderr
        and off_result.exit_code == 3
        and on_result.exit_code == 0
        and (on_result.manifest or {}).get("candidate_identity", {}).get(
            "in_frozen_set") is False
    )
    return {
        "what": "the frozen-candidate gate cannot be opened from inside a "
                "session: it lives in the registered tree's locator, which is "
                "fingerprinted as EID_r and re-synced into every frame run",
        "registered_tree_env_override_attempt": {
            "env": {"A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE": "1"},
            "exit_code": leaked.exit_code,
            "manifest_parsed": leaked.manifest is not None,
            "stderr_tail": leaked.stderr.strip().splitlines()[-1]
            if leaked.stderr.strip() else "",
            "expected": "exit 3, no manifest",
        },
        "scratch_tree_flag_off_with_same_env": {
            "exit_code": off_result.exit_code,
            "manifest_parsed": off_result.manifest is not None,
        },
        "scratch_tree_flag_on": {
            "exit_code": on_result.exit_code,
            "candidate_identity": (on_result.manifest or {}).get(
                "candidate_identity"),
        },
        "registered_tree_locator_flag": json.loads(
            (registered_tree / "a0_locator.json").read_text("utf-8")
        ).get("allow_unfrozen_candidate"),
        "pass": ok,
    }


def _set_flag(tree: Path, flag: bool) -> None:
    locator_path = Path(tree) / "a0_locator.json"
    locator = json.loads(locator_path.read_text("utf-8"))
    locator["allow_unfrozen_candidate"] = bool(flag)
    locator_path.write_text(
        json.dumps(locator, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
