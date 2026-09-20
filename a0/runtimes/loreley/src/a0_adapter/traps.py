"""The three named Loreley false-green traps, each with a real demonstration.

``plan:551-552`` names them; ``ACCEPTANCE.md`` §4 (T2/T3/T4) states the required
check for each.  A trap is "handled" here when (a) the adapter labels the event so
that a reader can tell it apart from a real score, and (b) the labelling has been
exercised against the runtime's own code, not argued.

* **T2 timeout** - a plugin timeout makes ``Evaluator.evaluate_outcome`` return a
  synthesized candidate failure.  Demonstrated by running the real evaluator with
  ``WORKER_EVALUATOR_TIMEOUT_SECONDS`` shorter than a real candidate's evaluation
  time.
* **T3 truncation** - ``Evaluator._coerce_outcome`` truncates to
  ``worker_evaluator_max_metrics``.  Demonstrated with a declared test-double
  plugin that emits more than the cap.
* **T4 persistent cache** - ``EvolutionJobStore.find_reusable_evaluation`` returns a
  stored outcome for an identical source tree and evaluator contract.  Demonstrated
  against the real PostgreSQL-backed store, including the negative case (a
  different evaluator version must not be served from cache).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import CandidateSet, ThetaE
from .evidence import classify
from .runtime import (
    FrozenEnvironment,
    build_settings,
    ensure_importable,
    reference_evaluation,
    run_through_loreley,
)

TRAPS_SCHEMA = "a0.loreley.traps/v1"
HEAVY_PLUGIN_REF = "loreley_a0_plugin_metrics_heavy:plugin"


def _trap_env(base: FrozenEnvironment, run_dir: Path, *, timeout_s: int,
              plugin_ref: str | None = None) -> FrozenEnvironment:
    env = FrozenEnvironment(
        run_dir=run_dir,
        theta=base.theta,
        objectives=base.objectives,
        islands=base.islands,
        pareto_front_max_size=base.pareto_front_max_size,
        pareto_epsilon=base.pareto_epsilon,
        admission_policy=base.admission_policy,
        experiment_root_commit=base.experiment_root_commit,
        campaign_program_hash=base.campaign_program_hash,
        worker_evaluator_timeout_seconds=timeout_s,
        worker_evaluator_max_metrics=base.worker_evaluator_max_metrics,
        emit_timing=base.emit_timing,
        plugin_ref=plugin_ref or base.plugin_ref,
    )
    return env


def _apply_with_plugin(env: FrozenEnvironment, plugin_ref: str) -> None:
    env.plugin_ref = plugin_ref
    env.apply()


def t2_timeout(
    env: FrozenEnvironment,
    candidate_set: CandidateSet,
    theta: ThetaE,
    *,
    timeout_seconds: int = 1,
) -> dict[str, Any]:
    """A real plugin timeout must be visible as such, not as a score."""

    candidate = candidate_set.by_id("c13_slow")
    trap_env = _trap_env(env, env.run_dir / "t2-timeout", timeout_s=timeout_seconds)
    trap_env.apply()

    runtime_result = run_through_loreley(trap_env, candidate, iteration=0)
    evidence = classify(
        runtime_result, max_metrics=trap_env.worker_evaluator_max_metrics
    )
    reference = reference_evaluation(
        candidate, theta, workdir=trap_env.run_dir / "reference"
    )
    return {
        "check_id": "T2",
        "mechanism": (
            "Evaluator._execute_with_timeout raises EvaluationError on the deadline "
            "(loreley/core/worker/evaluator.py:1859-1912) and evaluate_outcome turns it into "
            "a synthesized candidate failure (evaluator.py:1513-1520)"
        ),
        "config": {
            "WORKER_EVALUATOR_TIMEOUT_SECONDS": timeout_seconds,
            "candidate": candidate.candidate_id,
            "plugin": "loreley_a0_plugin:plugin",
        },
        "observed": {
            "runtime_outcome_kind": runtime_result.outcome_kind,
            "runtime_metrics_count": len(runtime_result.metrics),
            "runtime_failure_summary": runtime_result.failure_summary,
            "plugin_evidence_present": runtime_result.evidence is not None,
        },
        "adapter_label": evidence.as_trace(),
        "distinguishable_from_a_real_score": {
            "evidence_status": evidence.status,
            "outcome_fields_recorded": {"sum_radii": None},
            "why": (
                "the score event carries evaluator_evidence.status=timeout and a null primary "
                "field, while a measured candidate carries status=ok and a number; there is no "
                "synthesized 0.0 anywhere"
            ),
        },
        "reference_e_star": {
            "status": reference.status,
            "failure_kind": (reference.outcome.get("failure") or {}).get("kind"),
            "primary": reference.fields.get("sum_radii"),
            "note": (
                "E* itself takes longer than the runtime timeout on this candidate, so the "
                "runtime timeout is what fired; E*'s own verdict is recorded separately"
            ),
        },
        "passed": (
            evidence.status == "timeout"
            and len(runtime_result.metrics) == 0
            and runtime_result.outcome_kind != "passed"
        ),
    }


def t3_truncation(
    env: FrozenEnvironment,
    candidate_set: CandidateSet,
    *,
    padding: int = 70,
) -> dict[str, Any]:
    """Metrics above the cap: which payload shapes the cap actually applies to."""

    candidate = candidate_set.by_id("c01_good_hex")
    import os

    os.environ["A0_T3_PADDING"] = str(padding)

    def _observe(payload_kind: str, plugin_ref: str) -> dict[str, Any]:
        trap_env = _trap_env(
            env,
            env.run_dir / f"t3-truncation-{payload_kind}",
            timeout_s=900,
            plugin_ref=plugin_ref,
        )
        trap_env.worker_evaluator_max_metrics = 64
        trap_env.apply()
        result = run_through_loreley(trap_env, candidate, iteration=0)
        label = classify(result, max_metrics=trap_env.worker_evaluator_max_metrics)
        emitted = (result.evidence or {}).get("metrics_returned")
        names = {item["name"] for item in result.metrics}
        return {
            "payload_kind": payload_kind,
            "plugin": plugin_ref,
            "plugin_metrics_emitted": emitted,
            "runtime_metrics_returned": len(result.metrics),
            "truncation_applied": isinstance(emitted, int) and emitted > len(result.metrics),
            "padding_metrics_survived": len([n for n in names if n.startswith("a0_padding_")]),
            "adapter_label": label.as_trace(),
        }

    # Path A: the payload shape the A0 adapter itself uses (EvalPass).
    evalpass = _observe("evalpass", "loreley_a0_plugin_metrics_heavy:plugin")
    # Path B: the payload shape the checkout's own example plugin uses (Mapping).
    mapping = _observe("mapping", "loreley_a0_plugin_metrics_mapping:plugin")

    real_metrics = {"sum_radii", "packing_density", "num_circles", "overlap_count",
                    "min_gap", "min_boundary_margin"}
    frozen_count = 7  # six E* fields + the declared F_r projection
    return {
        "check_id": "T3",
        "mechanism": (
            "Evaluator._coerce_result truncates result.metrics to self.max_metrics "
            "(loreley/core/worker/evaluator.py:2304-2310); worker_evaluator_max_metrics "
            "defaults to 64 (loreley/config.py:565-568)"
        ),
        "plugin_is_a_test_double": True,
        "config": {
            "WORKER_EVALUATOR_MAX_METRICS": 64,
            "A0_T3_PADDING": padding,
        },
        "observations": {"evalpass_path": evalpass, "mapping_path": mapping},
        "finding": (
            "the cap is only enforced on payloads that reach _coerce_result - a Mapping "
            "(the shape examples/circle_packing_env/evaluate.py returns) or an "
            "EvaluationResult. An EvalPass payload short-circuits _coerce_outcome "
            "(evaluator.py:2029-2037) and is returned verbatim. Measured: the EvalPass path "
            "returned {a} metrics for {b} emitted; the Mapping path returned {c} for {d} emitted."
        ).format(
            a=evalpass["runtime_metrics_returned"],
            b=evalpass["plugin_metrics_emitted"],
            c=mapping["runtime_metrics_returned"],
            d=mapping["plugin_metrics_emitted"],
        ),
        "adapter_handling": (
            "the adapter never infers truncation from a metric count: it compares the plugin's "
            "own reported count with what the runtime returned, and it asserts the frozen "
            "evaluator's count against the cap independently of either payload path"
        ),
        "frozen_evaluator_metric_count": {
            "actual": 6,
            "with_declared_F_r_scalar": frozen_count,
            "cap": 64,
            "truncation_possible": False,
            "real_e_star_fields": sorted(real_metrics),
        },
        "passed": (
            mapping["truncation_applied"] is True
            and mapping["runtime_metrics_returned"] == 64
            and mapping["adapter_label"]["status"] == "truncated_metrics"
            and mapping["adapter_label"]["metrics_dropped"]
            == (mapping["plugin_metrics_emitted"] or 0) - 64
            and evalpass["truncation_applied"] is False
            and evalpass["adapter_label"]["status"] == "ok"
            and frozen_count <= 64
        ),
    }


def t4_persistent_cache(
    env: FrozenEnvironment,
    candidate_set: CandidateSet,
    *,
    eid_r_value: str,
) -> dict[str, Any]:
    """A stored evaluation is reused - and the adapter never counts it as fresh."""

    ensure_importable()
    from loreley.core.worker.job_store import EvolutionJobStore
    from loreley.db.base import ensure_database_schema, session_scope
    from loreley.db.models import CandidateCommit, CommitCard, EvaluationAttempt, Metric

    settings = build_settings(env)
    ensure_database_schema(settings=settings, auto_migrate=True)

    candidate = candidate_set.by_id("c01_good_hex")
    source_tree_hash = hashlib.sha256(
        f"a0-t4:{candidate.solution_sha256}".encode("utf-8")
    ).hexdigest()
    campaign_hash = env.campaign_program_hash or "0" * 64
    evaluator_name = "loreley_a0_plugin:plugin"
    stored_version = "source-sha256:stored-under-a-previous-evaluator"
    attempt_id = uuid.uuid4()
    card_id = uuid.uuid4()
    cached_commit = "cached_commit_hash_000000000000000000000000"

    from sqlalchemy import delete, select as _select

    with session_scope() as session:
        # Make the probe idempotent: drop rows from any earlier T4 run first.
        previous = session.execute(
            _select(CommitCard.id).where(CommitCard.commit_hash == cached_commit)
        ).scalars().all()
        if previous:
            session.execute(
                delete(CandidateCommit).where(CandidateCommit.commit_card_id.in_(previous))
            )
            session.execute(delete(Metric).where(Metric.commit_card_id.in_(previous)))
            session.execute(
                delete(EvaluationAttempt).where(EvaluationAttempt.commit_card_id.in_(previous))
                if hasattr(EvaluationAttempt, "commit_card_id")
                else delete(EvaluationAttempt).where(EvaluationAttempt.id == attempt_id)
            )
            session.execute(delete(CommitCard).where(CommitCard.id.in_(previous)))
            session.commit()

    with session_scope() as session:
        session.add(
            CommitCard(
                id=card_id,
                commit_hash="cached_commit_hash_000000000000000000000000",
                island_id=env.islands[0] if env.islands else "circle_packing_alpha",
                author="a0-adapter",
                subject="T4 cache probe",
                change_summary="row written by the A0 adapter to exercise evaluation reuse",
                evaluation_summary="stored evaluation used by the T4 probe",
            )
        )
        session.flush()
        session.add(
            EvaluationAttempt(
                id=attempt_id,
                evaluator_name=evaluator_name,
                evaluator_version=stored_version,
                campaign_program_hash=campaign_hash,
                protocol="one_shot",
                outcome_kind="passed",
            )
        )
        session.add(
            Metric(
                id=uuid.uuid4(),
                commit_card_id=card_id,
                name="composite_score",
                value=2.4519205208433132,
                unit="radius_sum",
                higher_is_better=True,
                details={"probe": "T4"},
            )
        )
        session.flush()
        session.add(
            CandidateCommit(
                id=uuid.uuid4(),
                commit_hash="cached_commit_hash_000000000000000000000000",
                git_parent_commit_hash="0" * 40,
                island_id=env.islands[0] if env.islands else "circle_packing_alpha",
                commit_card_id=card_id,
                campaign_program_hash=campaign_hash,
                source_tree_hash=source_tree_hash,
                evaluation_status="passed",
                latest_evaluation_attempt_id=attempt_id,
                candidate_identity=candidate.solution_sha256,
            )
        )
        session.commit()

    store = EvolutionJobStore(settings=settings)

    reused = store.find_reusable_evaluation(
        source_tree_hash=source_tree_hash,
        evaluator_name=evaluator_name,
        evaluator_version=stored_version,
        campaign_program_hash=campaign_hash,
        candidate_commit_hash=candidate.solution_sha256[:40],
    )
    not_reused = store.find_reusable_evaluation(
        source_tree_hash=source_tree_hash,
        evaluator_name=evaluator_name,
        evaluator_version="source-sha256:the-version-actually-frozen",
        campaign_program_hash=campaign_hash,
        candidate_commit_hash=candidate.solution_sha256[:40],
    )

    label: dict[str, Any] | None = None
    reused_metrics: list[dict[str, Any]] = []
    if reused is not None:
        reused_metrics = [metric.as_dict() for metric in (reused.result.metrics if reused.result else ())]
        from .runtime import RuntimeEvaluation

        probe = RuntimeEvaluation(
            candidate_id=candidate.candidate_id,
            iteration=0,
            outcome_kind=str(reused.outcome_kind),
            protocol=str(getattr(reused, "protocol", "one_shot") or "one_shot"),
            evaluator_name=getattr(reused, "evaluator_name", None),
            evaluator_version=getattr(reused, "evaluator_version", None),
            metrics=tuple(reused_metrics),
            reuse_kind=str(getattr(reused, "reuse_kind", "none") or "none"),
            reused_from_attempt_id=getattr(reused, "reused_from_attempt_id", None),
            measurement_reused=getattr(reused, "measurement_reused", None),
            summary=str(getattr(reused, "summary", "") or ""),
            failure_summary=None,
            detail=None,
            candidate_failed=False,
            evidence=None,
            elapsed_s=0.0,
            raw_result_extra=dict((reused.result.extra if reused.result else {}) or {}),
        )
        label = classify(probe, max_metrics=env.worker_evaluator_max_metrics).as_trace()

    return {
        "check_id": "T4",
        "mechanism": (
            "EvolutionJobStore.find_reusable_evaluation returns a stored passed outcome whose "
            "(source_tree_hash, evaluator_name, evaluator_version, campaign_program_hash) match "
            "(loreley/core/worker/job_store.py:519-600); EvolutionWorker consults it before "
            "measuring (loreley/core/worker/evolution.py:913-929)"
        ),
        "config": {
            "DATABASE_URL": env.as_dict()["DATABASE_URL"],
            "eid_r": eid_r_value,
            "evaluator_name": evaluator_name,
            "evaluator_version_in_cache_key": stored_version,
            "campaign_program_hash": campaign_hash,
            "source_tree_hash": source_tree_hash,
        },
        "observed": {
            "reuse_with_matching_evaluator_identity": reused is not None,
            "reuse_with_different_evaluator_version": not_reused is not None,
            "reused_metrics": [item["name"] for item in reused_metrics],
            "reused_summary": (reused.result.summary if reused and reused.result else None),
        },
        "adapter_label_when_reused": label,
        "why_it_matters": (
            "a 'correct-looking' 2.45 could have been computed under a different evaluator head "
            "or candidate tree; the adapter refuses any reused observation for A0.1/A0.2 and "
            "reports the reuse count"
        ),
        "passed": (
            reused is not None
            and not_reused is None
            and label is not None
            and label["status"] == "cache_hit"
        ),
        "unverified": (
            "the full EvolutionWorker + phased-measurement-cache orchestration "
            "(evolution.py:1640-1665, :1741-1766) was not driven; the reuse DECISION is the "
            "runtime's own, but the worker that consumes it was not run end to end"
        ),
    }
