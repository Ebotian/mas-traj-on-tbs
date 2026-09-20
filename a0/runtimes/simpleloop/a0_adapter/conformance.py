"""A0.1 — Evaluator Integration Conformance.

`plan:513`:

    对每个 runtime r 与每个候选 c:  E_r(c; theta_E) = E*(c; theta_E) ± epsilon
    且 EID_r 由 EID* 派生（adapter 声明 + 可复算的哈希）

For SimpleLoop, `E_r` is "whatever the substrate's evaluator lane returns when it
evaluates a candidate", i.e. the frozen E* CLI executed as a subprocess. The
reference side `E*(c)` is the independently produced table
`a0/tasks/circle-packing/E_STAR.json` (E* applied to every member of C*), not a
re-run through the same code path — otherwise the comparison would be circular.

What is compared per candidate:
  * exit code                (0 / 2 / 3 — the verdict, not just a number)
  * status                   (ok / invalid / error)
  * failure.kind             (for the non-ok verdicts)
  * sum_radii                (|E_r - E*| <= epsilon, only when status == ok)
  * canonical_digest         (E*'s own digest of the whole Outcome, when both sides have one)

A verdict of `invalid` or `error` is never allowed to collapse into a number: the
substrate records `scalar = null` for it and the check fails if a number appears.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import traces as trace_mod
from .eidmap import eid_r_derivation
from .estareval import sha256_file
from .runner import Settings, build_evaluator, validate_run_dir, validate_trace_paths

CHECK_POINT = "A0.1 conformance: E_r(c) vs E*(c) for every c in C* (plan:513)"


def _reference_entries(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        table = json.load(fh)
    return {entry["candidate_id"]: entry for entry in table["candidates"]}, table


def run_conformance(settings: Settings) -> dict:
    reference, table = _reference_entries(settings.reference_table)
    run_dir = settings.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)

    evaluator = build_evaluator(
        settings,
        state_dir=run_dir / "estate",
        out_dir=run_dir / "outcomes",
    )

    theta_extra = {
        "n": int(settings.theta.get("n", 26)),
        "runs": int(settings.theta.get("runs", 5)),
        "runtime_budget_ms": float(settings.theta.get("runtime_budget_ms", 250.0)),
        "timeout_s": float(settings.theta.get("timeout_s", 120.0)),
        "e_star_script_sha256": sha256_file(settings.e_star_script),
        "candidate_set_sha256": settings.candidate_set.manifest_sha256,
        "evaluator_lane": "subprocess: e_star.py evaluate (frozen CLI)",
        "check_point": CHECK_POINT,
    }
    writer = trace_mod.TraceWriter(
        run_dir=run_dir,
        runtime=settings.runtime,
        run_id=settings.run_id,
        task=settings.task,
        eid_star=settings.eid.eid_star,
        eid_r=settings.eid.eid_r(settings.policy),
        theta_E={
            "seed": settings.theta["seed"],
            "fidelity": settings.theta["fidelity"],
            "fraction": settings.theta["fraction"],
            "defaults_applied": {},
            "extra": theta_extra,
        },
        policy=settings.policy,
        kinds=("score", "resource"),
    )
    from .policy import fr_for_events, scalar_of

    fr = fr_for_events(settings.policy)

    rows = []
    for iteration, candidate in enumerate(settings.candidate_set.candidates):
        result = evaluator.evaluate(candidate, iteration=iteration, tag=f"{candidate.candidate_id}.a01")
        ref = reference.get(candidate.candidate_id)
        if ref is None:
            raise RuntimeError(
                f"{candidate.candidate_id} is in C* but not in the reference table {settings.reference_table}"
            )

        scalar = None
        scalar_error = None
        try:
            scalar = scalar_of(result.outcome, settings.primary_field)
        except Exception as exc:  # noqa: BLE001
            scalar_error = str(exc)

        if result.exit_code == 0:
            failure_stage, failure_detail = "none", None
        else:
            failure_stage = trace_mod.failure_stage_for(result.exit_code, result.failure_kind)
            failure_detail = (
                f"E* exit {result.exit_code} status={result.status} "
                f"failure.kind={result.failure_kind}: {result.failure_message}"
            )

        writer.score(
            iteration=iteration,
            candidate_id=candidate.candidate_id,
            parent_id=None,
            outcome=result.outcome,
            fields=result.fields or {},
            search_signal=scalar,
            evaluator_evidence=trace_mod.evaluator_evidence_for(result),
            fr=fr,
            failure_stage=failure_stage,
            failure_detail=failure_detail,
        )
        writer.resource(
            iteration=iteration,
            candidate_id=candidate.candidate_id,
            parent_id=None,
            T_wall={"value_sec": round(result.wall_sec, 6), "clock": "monotonic", "scope": "iteration"},
            N_evaluatorCalls=evaluator.calls,
            concurrency={"cap": settings.budget.concurrency, "observed_max": 1},
            secondary={"N_modelCalls": 0, "T_in": 0, "T_out": 0, "C_usd": 0.0},
            budget_hard=settings.budget.as_dict(),
            failure_stage=failure_stage,
            failure_detail=failure_detail,
        )

        ref_status = ref.get("status")
        ref_objective = ref.get("objective_value")
        checks = {
            "exit_code_match": result.exit_code == ref.get("exit_code"),
            "status_match": result.status == ref_status,
            "failure_kind_match": (result.failure_kind or None) == (ref.get("failure_kind") or None),
        }
        if result.status == "ok":
            checks["scalar_present"] = scalar is not None
            checks["scalar_within_epsilon"] = (
                scalar is not None
                and ref_objective is not None
                and abs(scalar - float(ref_objective)) <= settings.epsilon
            )
            checks["canonical_digest_match"] = (
                (result.manifest or {}).get("canonical_digest") == ref.get("canonical_digest")
            )
            delta = None if scalar is None or ref_objective is None else scalar - float(ref_objective)
        else:
            # The false-green guard: a non-ok verdict must not carry a number.
            checks["no_scalar_for_non_ok"] = scalar is None
            delta = None
        checks["candidate_bytes_match"] = (
            candidate.solution_sha256 == ref.get("source_sha256")
            and (result.manifest or {}).get("candidate_source_sha256") == candidate.solution_sha256
        )

        rows.append({
            "candidate_id": candidate.candidate_id,
            "candidate_role": candidate.role,
            "candidate_expected_verdict": candidate.expected_status,
            "solution_sha256": candidate.solution_sha256,
            # Freshness of *this* row's number, and the raw material a third party
            # needs to attest it without trusting this adapter: E*'s own
            # `E_STAR_MANIFEST` line (it carries the evaluator source digest, the
            # theta_E actually used and the candidate's canonical digest), plus the
            # canonical digest and source hashes the comparison used. `status: ok`
            # means "a fresh measurement" in the trace_schema.md §5 sense; the E*
            # *verdict* for the row is `substrate.status` / `reference.status`.
            "evaluator_evidence": {
                "status": "ok",
                "detail": None,
                "source": "subprocess: e_star.py evaluate (frozen CLI); stdout E_STAR_MANIFEST line",
                "freshness": (
                    "measured in this conformance run: no cache reuse, no synthesized score, "
                    "no truncation, no run inherited from another sweep"
                ),
                "manifest_line": result.manifest_line,
                "manifest": result.manifest,
                "canonical_digest": (result.manifest or {}).get("canonical_digest"),
                "candidate_source_sha256": (result.manifest or {}).get("candidate_source_sha256"),
                "evaluator_source_sha256": (result.manifest or {}).get("evaluator_source_sha256"),
                "theta_e_attempt": {
                    "seed": (result.outcome or {}).get("theta_e", {}).get("seed"),
                    "fidelity": (result.outcome or {}).get("theta_e", {}).get("fidelity"),
                    "fraction": (result.outcome or {}).get("theta_e", {}).get("fraction"),
                    "n": (result.outcome or {}).get("theta_e", {}).get("n"),
                    "runs": (result.outcome or {}).get("theta_e", {}).get("runs"),
                },
                "scored": (result.outcome or {}).get("scored"),
                "e_star_verdict": result.status,
                "e_star_exit_code": result.exit_code,
                "outcome_path": settings.rel(result.out_path),
            },
            "substrate": {
                "exit_code": result.exit_code,
                "status": result.status,
                "failure_kind": result.failure_kind,
                "failure_message": result.failure_message,
                "scalar": scalar,
                "scalar_error": scalar_error,
                "fields": result.fields,
                "structure": (result.outcome or {}).get("structure"),
                "canonical_digest": (result.manifest or {}).get("canonical_digest"),
                "candidate_source_sha256": (result.manifest or {}).get("candidate_source_sha256"),
                "evaluator_source_sha256": (result.manifest or {}).get("evaluator_source_sha256"),
                "evaluation_sec": round(result.wall_sec, 6),
            },
            "reference": {
                "exit_code": ref.get("exit_code"),
                "status": ref_status,
                "failure_kind": ref.get("failure_kind"),
                "objective_value": ref_objective,
                "canonical_digest": ref.get("canonical_digest"),
            },
            "delta": delta,
            "checks": checks,
            "pass": all(checks.values()),
        })

    writer.close()
    combined = run_dir / "traces" / f"{settings.runtime}.{settings.run_id}.all.jsonl"
    with combined.open("w", encoding="utf-8") as out:
        for kind in writer.kinds:
            path = writer.paths.get(kind)
            if path and path.is_file():
                out.write(path.read_text(encoding="utf-8"))

    verdict = "pass" if all(row["pass"] for row in rows) else "fail"
    counts = writer.failure_stage_counts()
    return {
        "schema": "a0.simpleloop.conformance/v1",
        "runtime": settings.runtime,
        "task": settings.task,
        "run_id": settings.run_id,
        "run_dir": settings.rel(run_dir),
        "check_point": CHECK_POINT,
        "primary_field": settings.primary_field,
        "eid_star": settings.eid.eid_star,
        "eid_document": settings.rel(settings.eid.document_path),
        "eid_spec": settings.rel(settings.eid.spec_path) if settings.eid.spec_path else None,
        "eid_verify_returncode": settings.eid.verify_returncode,
        "eid_r": settings.eid.eid_r(settings.policy) | {
            # Document-only enrichment: the trace `eid_r` block is schema-closed
            # (additionalProperties: false), so the published derivation lives here.
            # `(domain, payload_canonical)` is everything a third party needs to
            # recompute `value` with their own sha256.
            "derivation": eid_r_derivation(
                eid_star=settings.eid.eid_star,
                source_records=settings.eid.source_records,
                policy=settings.policy,
            ),
        },
        "fr": fr,
        "epsilon": {"kind": "abs", "value": settings.epsilon, "unit": settings.primary_field,
                    "source": "EID* Config.conformance.epsilon"},
        "theta_E": {
            "seed": settings.theta["seed"],
            "fidelity": settings.theta["fidelity"],
            "fraction": settings.theta["fraction"],
            "extra": theta_extra,
        },
        "evaluator_identity": evaluator.identity.as_dict() if evaluator.identity else None,
        "reference_table": {
            "path": settings.rel(settings.reference_table),
            "sha256": sha256_file(settings.reference_table),
            "schema": table.get("schema"),
            "canonical_theta_e": table.get("canonical_theta_e"),
        },
        "candidates": rows,
        "candidate_count": len(rows),
        "passed": sum(1 for row in rows if row["pass"]),
        "failed": [row["candidate_id"] for row in rows if not row["pass"]],
        "verdict": verdict,
        "traces": {k: settings.rel(v) for k, v in sorted(writer.paths.items())},
        "trace_paths": {k: settings.rel(v) for k, v in sorted(writer.paths.items())}
        | {"combined": settings.rel(combined)},
        "failure_stage_counts": {
            "source": settings.rel(writer.paths["score"]),
            "counts": counts,
            "note": (
                "declared by the adapter from its own score trace, one unit per "
                "(run_id, iteration, candidate_id) so a failure reported on two traces is "
                "counted once (plan:577, plan:628); identical to trace_validate.py's rule"
            ),
        },
        # The frozen validation unit is the run's merged stream (trace_schema.md §1,
        # `validate-run`); the per-kind verdicts are recorded as the reading interface.
        "trace_validation": {
            "run_unit": validate_run_dir(
                settings, run_dir,
                validator_python=settings.work_root / "a0/contract/.venv/bin/python",
                trace_validate_py=settings.work_root / "a0/contract/trace_validate.py",
            ),
            "per_file": validate_trace_paths(
                settings,
                {k: v for k, v in writer.paths.items()} | {"combined": combined},
                validator_python=settings.work_root / "a0/contract/.venv/bin/python",
                trace_validate_py=settings.work_root / "a0/contract/trace_validate.py",
            ),
        },
        "evaluator_calls": evaluator.calls,
    }


def write(result: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return path


def summarise(result: dict) -> dict:
    return {
        "schema": result["schema"],
        "verdict": result["verdict"],
        "candidate_count": result["candidate_count"],
        "passed": result["passed"],
        "failed": result["failed"],
        "epsilon": result["epsilon"],
        "eid_star": result["eid_star"],
        "theta_E": {k: result["theta_E"][k] for k in ("seed", "fidelity", "fraction")},
        "verdicts_seen": {
            row["candidate_id"]: f"{row['substrate']['status']}/exit{row['substrate']['exit_code']}"
            for row in result["candidates"]
        },
        "trace_paths": result["trace_paths"],
    }
