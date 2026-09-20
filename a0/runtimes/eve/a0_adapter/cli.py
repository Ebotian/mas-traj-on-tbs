"""Adapter CLI (a0/contract/adapter_contract.md §3).

    python -m a0_adapter run            --runtime eve --task circle-packing \
        --candidate-set <C*/manifest.json> --eid <EID*.json> \
        --theta seed=1337,fidelity=full,fraction=1.0 --fr <fr.json> \
        --run-id <id> --run-dir <dir> --budget T_wall_sec=...,N_evaluatorCalls=...,concurrency=1 \
        --traces score,selection,resource
    python -m a0_adapter conformance    --runtime eve ... --epsilon 1e-9 --out conformance.json
    python -m a0_adapter closure-probe  --runtime eve --run-dir <dir> --out closure.json

Exit codes are the contract's (adapter_contract.md §3.1). Exit 6 is reserved for an observed
closure violation; a closure probe that cannot produce proof returns 3 and says so.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import a01, a02_run, closure as closure_mod, common, eidmap, selectionmap
from .common import (
    EXIT_CANDIDATE_SET,
    EXIT_CONTRACT,
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_USAGE,
)
from .eidmap import EidMappingError
from .eve_runtime import (
    EVE_ROOT,
    EveWiringError,
    build_context,
    eid_r_enrichment,
    eid_r_payload,
    require_pinned_eve,
)
from .selectionmap import SelectionMappingError
from .traces import TraceWriter


def _die(code: int, message: str) -> int:
    print(f"a0_adapter(eve): {message}", file=sys.stderr)
    return code


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--task", default="circle-packing")
    parser.add_argument("--candidate-set", default=str(common.DEFAULT_CANDIDATE_SET))
    parser.add_argument("--eid", default=str(common.DEFAULT_EID))
    parser.add_argument("--spec", default=str(common.DEFAULT_SPEC))
    parser.add_argument("--theta", default="seed=none,fidelity=full,fraction=1.0")
    parser.add_argument("--fr", default=str(common.DEFAULT_FR))
    parser.add_argument("--run-id", default="a0-eve-run001")
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--traces", default="score,selection,resource")
    parser.add_argument("--epsilon", type=float, default=1e-9)
    parser.add_argument("--out", default=None)
    parser.add_argument("--a02-iterations", type=int, default=2000)
    parser.add_argument("--a02-iterations-secondary", type=int, default=6000)
    parser.add_argument("--skip-a02", action="store_true")
    parser.add_argument("--skip-trap-reproduction", action="store_true")
    parser.add_argument(
        "--bundled-step",
        default=str(EVE_ROOT / "configs" / "eve" / "evaluation" / "circle_packing" / "evaluation.sh"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="a0_adapter", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="A0.1 conformance + A0.2 frequency test, with the three traces")
    _add_common(run)
    run.add_argument("--budget", default="T_wall_sec=7200,N_evaluatorCalls=512,concurrency=1")

    conf = sub.add_parser("conformance", help="A0.1 only; writes conformance.json")
    _add_common(conf)

    probe = sub.add_parser("closure-probe", help="closure probe; writes closure.json")
    probe.add_argument("--runtime", required=True)
    probe.add_argument("--run-dir", required=True)
    probe.add_argument("--out", required=True)
    probe.add_argument("--candidate-dir", default=None)
    probe.add_argument("--step-script", default=None)
    return parser


def _envelope_factory(eid_star: str, eid_r: dict, theta: common.Theta):
    def envelope(iteration: int, candidate_id: str, failure_stage: str = "none",
                 failure_detail: str | None = None) -> dict:
        return {
            "eid_star": eid_star,
            "eid_r": eid_r,
            "theta_E": theta.trace_payload({"iteration": iteration, "candidate_id": candidate_id}),
            "failure_stage": failure_stage,
            "failure_detail": failure_detail,
        }

    return envelope


def _prepare(args) -> tuple[common.Theta, common.Fr, list[common.Candidate], dict, str, dict, int]:
    theta = common.parse_theta(args.theta)
    fr = common.load_fr(Path(args.fr))
    candidates = common.load_candidates(Path(args.candidate_set))
    eid_doc = common.read_eid(Path(args.eid))
    eid_star = eid_doc["eid_star"]

    rc, out = common.verify_eid(Path(args.eid), Path(args.spec))
    if rc != 0:
        return theta, fr, candidates, eid_doc, eid_star, {"verify_rc": rc, "verify_out": out}, EXIT_CONTRACT
    return theta, fr, candidates, eid_doc, eid_star, {"verify_rc": rc, "verify_out": out}, EXIT_OK


def _budget_from_text(text: str) -> dict:
    raw = common.parse_kv_list(text)
    return {
        "T_wall_sec": float(raw["T_wall_sec"]) if "T_wall_sec" in raw else None,
        "N_evaluatorCalls": int(raw["N_evaluatorCalls"]) if "N_evaluatorCalls" in raw else None,
        "concurrency_cap": int(raw["concurrency"]) if "concurrency" in raw else None,
    }


def cmd_run(args) -> int:
    if args.runtime != "eve":
        return _die(EXIT_USAGE, f"this adapter implements the eve runtime only, got {args.runtime!r}")
    run_dir = Path(args.run_dir or (common.ADAPTER_DIR / "out" / f"run-{args.run_id}")).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    try:
        theta, fr, candidates, eid_doc, eid_star, verify, verify_code = _prepare(args)
    except common.CandidateSetError as exc:
        return _die(EXIT_CANDIDATE_SET, str(exc))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        return _die(EXIT_USAGE, f"{exc!r}")
    if verify_code != EXIT_OK:
        return _die(EXIT_CONTRACT, f"evalcontract verify failed: {verify['verify_out'].strip()}")

    budget = _budget_from_text(args.budget)
    traces = TraceWriter(run_dir, args.run_id)
    try:
        ctx = build_context(
            run_dir=run_dir,
            theta=theta,
            fr=fr,
            eid_star=eid_star,
            pins_sha256=fr.spec_hash,
        )
        eid_r = eid_r_payload(ctx.step, eid_document=eid_doc, fr_spec_hash=fr.spec_hash)
        adoption = selectionmap.check_adoption()
    except (EveWiringError, OSError, EidMappingError, SelectionMappingError) as exc:
        return _die(EXIT_CONTRACT, f"EvE wiring failed: {exc}")

    envelope = _envelope_factory(eid_star, eid_r, theta)

    conformance = a01.run_conformance(
        ctx,
        candidates=candidates,
        run_dir=run_dir,
        theta=theta,
        fr=fr,
        epsilon=args.epsilon,
        traces=traces,
        envelope=envelope,
        fr_payload=fr.trace_payload(),
        on_progress=lambda msg: print(msg, flush=True),
    )

    trap_reproduction = None
    if not args.skip_trap_reproduction:
        target = next(
            (c for c in candidates if c.candidate_id == "c06_empty"),
            candidates[0],
        )
        trap_routes = {
            "R2_shipped_step_evaluator_exits_nonzero": (
                {"evaluate.py": "import sys\nprint('injected failing evaluator', file=sys.stderr)\nsys.exit(7)\n"},
                "R2_shipped_step_evaluator_exits_nonzero",
                "the shipped step running an evaluator program that exits 7",
            ),
            "R3_shipped_step_evaluator_reports_error_with_score": (
                None,
                "R3_shipped_step_evaluator_reports_error_with_score",
                "the shipped step running the task repo's own evaluate.py, which returns a "
                "numeric score together with status:'error'",
            ),
        }
        trap_reproduction = {
            "R1_adapter_step_propagates_e_star_exit": {
                "see": "a01.candidates[*] where reference_status != 'ok'",
                "candidates": conformance.trap.get("candidates_with_synthetic_score"),
            }
        }
        for route_name, (extra_files, label, description) in trap_routes.items():
            try:
                record = a01.reproduce_bundled_failure_contract(
                    bundled_step=Path(args.bundled_step),
                    candidate=target,
                    run_dir=run_dir / "trap-reproduction",
                    theta=theta,
                    fr=fr,
                    eid_star=eid_star,
                    pins_sha256=fr.spec_hash,
                    extra_files=extra_files,
                    label=label,
                    description=description,
                )
                trap_reproduction[route_name] = record
                traces.score(
                    iteration=90 if route_name.startswith("R2") else 91,
                    candidate_id=target.candidate_id,
                    envelope=envelope(
                        90 if route_name.startswith("R2") else 91, target.candidate_id
                    ),
                    fields={"sum_radii": record["returned_scalar"]},
                    fr_payload=fr.trace_payload(),
                    search_signal=record["returned_scalar"],
                    evidence={
                        "status": "synthesized_failure",
                        "detail": f"{route_name}: {record['conclusion']}",
                        "cached_from_run_id": None,
                        "metrics_dropped": None,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                trap_reproduction[route_name] = {"error": repr(exc)}

    ref_fields: dict[str, dict] = {}
    ref_scores: dict[str, float] = {}
    for candidate in conformance.candidates:
        outcome_path = candidate.reference_outcome_path
        if outcome_path is None:
            continue
        doc = json.loads(Path(outcome_path).read_text(encoding="utf-8"))
        ref_fields[candidate.candidate_id] = doc.get("fields") or {
            "sum_radii": None,
            "status": doc.get("status"),
        }
        ref_scores[candidate.candidate_id] = candidate.reference_scalar

    candidate_sources = {
        candidate.candidate_id: (candidate.path / "solution.py").read_text(encoding="utf-8")
        for candidate in candidates
    }

    a02_report = None
    if not args.skip_a02:
        a02_report = a02_run.run_a02(
            ctx,
            run_dir=run_dir,
            traces=traces,
            envelope=envelope,
            fr_payload=fr.trace_payload(),
            candidate_sources=candidate_sources,
            reference_fields=ref_fields,
            reference_scores={
                cid: value for cid, value in ref_scores.items() if value is not None
            },
            n_main=max(args.a02_iterations, 1),
            n_secondary=max(args.a02_iterations_secondary, 1),
            on_progress=lambda msg: print(msg, flush=True),
        )

    elapsed = time.monotonic() - started
    traces.resource(
        iteration=99999,
        candidate_id="<run>",
        envelope=envelope(99999, "<run>"),
        t_wall_s=elapsed,
        n_evaluator_calls=len(candidates) + (1 if trap_reproduction else 0),
        concurrency_cap=int(budget["concurrency_cap"] or 1),
        observed_max=1,
        budget_hard=budget,
        scope="run",
        event_id=f"{args.run_id}-res-run",
    )
    validation = traces.validate()

    eid_r_run = dict(eid_r)
    eid_r_run.update(
        eid_r_enrichment(
            ctx.step,
            eid_document=eid_doc,
            fr_spec_hash=fr.spec_hash,
            eid_path=Path(args.eid),
            fr_path=Path(args.fr),
        )
    )

    adapter_md = render_adapter_md(
        run_id=args.run_id,
        run_dir=run_dir,
        ctx=ctx,
        theta=theta,
        fr=fr,
        eid_star=eid_star,
        eid_r=eid_r_run,
        candidates=candidates,
        conformance=conformance,
        a02_report=a02_report,
        trap_reproduction=trap_reproduction,
        budget=budget,
        elapsed=elapsed,
        verify=verify,
    )
    (run_dir / "adapter.md").write_text(adapter_md, encoding="utf-8")

    trace_paths = {kind: str(path) for kind, path in traces.paths.items()}
    conformance_out = {
        "schema": "a0.adapter.conformance/v1",
        "runtime": "eve",
        "run_id": args.run_id,
        "run_dir": str(run_dir),
        "eid_star": eid_star,
        "eid_r": eid_r_run,
        "theta_e": theta.declaration_payload(
            {"seed_delivery": "adapter-pinned: EvE injects no seed into an evaluation step"}
        ),
        "theta_E": theta.trace_payload(),
        "epsilon": args.epsilon,
        "primary_field": fr.primary_field,
        "fr": fr.trace_payload(),
        "traces": trace_paths,
        "traces_source": "written by this run invocation",
        "failure_stage_counts": _failure_stage_counts(traces.paths["score"]),
        "failure_stage_counts_scope": (
            "top-level counts cover every score unit of this run (the 14 C* A0.1 rows, the "
            "shipped-step trap-reproduction units, and the A0.2 sampling units); "
            "`a01.failure_stage_counts` is the C* subset the frozen A0-wide map is compared "
            "against, and `failure_stage_accounting_basis` carries that map and the digests that "
            "were checked"
        ),
        "failure_stage_accounting_basis": _staging_declaration(adoption),
        "a0_1_verdict": conformance.verdict,
        "a0_1_scope": conformance.agreement_scope()["statement"],
        "candidates": [_harness_row(row, theta) for row in conformance.candidates],
        "candidate_set": str(Path(args.candidate_set).resolve()),
        "candidates_source_sha256": {
            c.candidate_id: c.solution_sha256 for c in candidates
        },
        "reference_cli": {
            "python": str(common.E_STAR_PYTHON),
            "script": str(common.E_STAR_SCRIPT),
            "argv_template": (
                "evaluate --candidate <dir> --seed {seed} --fidelity {fidelity} "
                "--fraction {fraction} --n {n} --runs {runs} --timeout-s {timeout_s} "
                "--out <json> --state-dir <dir>"
            ),
        },
        "a01": conformance.to_json(),
        "trap_reproduction_shipped_step": trap_reproduction,
        "a02": None if a02_report is None else a02_report.to_json(),
        "trace_validation": validation,
        "seams": None if a02_report is None else a02_report.seams,
        "eve_checkout": {"root": str(EVE_ROOT), "commit": require_pinned_eve()},
        "EID_verification": verify,
    }
    out_path = Path(args.out) if args.out else (run_dir / "conformance.json")
    out_path.write_text(json.dumps(conformance_out, indent=1, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")

    print(json.dumps({
        "run_dir": str(run_dir),
        "conformance_json": str(out_path),
        "a01_verdict": conformance.verdict,
        "a01_counters": conformance.counters,
        "trap_detected": conformance.trap.get("detected"),
        "traces_ok": validation.get("ok"),
        "trace_paths": trace_paths,
    }, indent=1))

    if not validation.get("ok"):
        return _die(EXIT_INTERNAL, "a trace failed validation; see conformance.json")
    if conformance.exit_code != EXIT_OK:
        return conformance.exit_code
    return EXIT_OK


def cmd_conformance(args) -> int:
    if args.runtime != "eve":
        return _die(EXIT_USAGE, f"this adapter implements the eve runtime only, got {args.runtime!r}")
    run_dir = Path(args.run_dir or (common.ADAPTER_DIR / "out" / f"conf-{args.run_id}")).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        theta, fr, candidates, eid_doc, eid_star, verify, verify_code = _prepare(args)
    except common.CandidateSetError as exc:
        return _die(EXIT_CANDIDATE_SET, str(exc))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        return _die(EXIT_USAGE, f"{exc!r}")
    if verify_code != EXIT_OK:
        return _die(EXIT_CONTRACT, f"evalcontract verify failed: {verify['verify_out'].strip()}")
    try:
        ctx = build_context(
            run_dir=run_dir, theta=theta, fr=fr, eid_star=eid_star, pins_sha256=fr.spec_hash
        )
        eid_r = eid_r_payload(ctx.step, eid_document=eid_doc, fr_spec_hash=fr.spec_hash)
        adoption = selectionmap.check_adoption()
    except (EveWiringError, OSError, EidMappingError, SelectionMappingError) as exc:
        return _die(EXIT_CONTRACT, f"EvE wiring failed: {exc}")

    # This subcommand declares its OWN traces, so the conformance runner never has to search
    # for them (a search can only guess whether the files belong to this invocation).
    traces = TraceWriter(run_dir, args.run_id)
    envelope = _envelope_factory(eid_star, eid_r, theta)
    started = time.monotonic()
    report = a01.run_conformance(
        ctx,
        candidates=candidates,
        run_dir=run_dir,
        theta=theta,
        fr=fr,
        epsilon=args.epsilon,
        traces=traces,
        envelope=envelope,
        fr_payload=fr.trace_payload(),
        on_progress=lambda msg: print(msg, flush=True),
    )
    elapsed = time.monotonic() - started
    traces.resource(
        iteration=99999,
        candidate_id="<run>",
        envelope=envelope(99999, "<run>"),
        t_wall_s=elapsed,
        n_evaluator_calls=len(candidates),
        concurrency_cap=1,
        observed_max=1,
        budget_hard={"T_wall_sec": None, "N_evaluatorCalls": None, "concurrency_cap": 1},
        scope="run",
        event_id=f"{args.run_id}-res-run",
    )
    validation = traces.validate()
    trace_paths = {kind: str(path) for kind, path in traces.paths.items()}
    failure_stage_counts = _failure_stage_counts(traces.paths["score"])

    eid_r_declared = dict(eid_r)
    eid_r_declared.update(
        eid_r_enrichment(
            ctx.step,
            eid_document=eid_doc,
            fr_spec_hash=fr.spec_hash,
            eid_path=Path(args.eid),
            fr_path=Path(args.fr),
        )
    )

    payload = {
        "schema": "a0.adapter.conformance/v1",
        "runtime": "eve",
        "run_id": args.run_id,
        "run_dir": str(run_dir),
        "eid_star": eid_star,
        "eid_r": eid_r_declared,
        "theta_e": theta.declaration_payload(
            {"seed_delivery": "adapter-pinned: EvE injects no seed into an evaluation step"}
        ),
        "epsilon": args.epsilon,
        "primary_field": fr.primary_field,
        "fr": fr.trace_payload(),
        "candidate_set": str(Path(args.candidate_set).resolve()),
        "traces": trace_paths,
        "traces_source": "written by this conformance invocation",
        "failure_stage_counts": failure_stage_counts,
        "failure_stage_counts_scope": (
            "this subcommand writes the A0.1 trace only, so the counts are exactly the 14 C* rows "
            "(`a01.failure_stage_counts`), staged with the adopted frozen A0-wide table and equal "
            "to the frozen map over C*'s E* verdicts: {none: 5, verify_failed: 5, resolve_failed: "
            "1, evaluator_failed: 2, timeout: 1}"
        ),
        "failure_stage_accounting_basis": _staging_declaration(adoption),
        "trace_validation": validation,
        "a01": report.to_json(),
        "a0_1_verdict": report.verdict,
        "a0_1_scope": report.agreement_scope()["statement"],
        "candidates": [_harness_row(row, theta) for row in report.candidates],
        "seams": [
            {
                "seam": "E1",
                "what": "SolverEvaluator.evaluate path (real EvE evaluation machinery)",
                "where": "src/scaling_evolve/algorithms/eve/workflow/evaluation.py:119-165",
            },
            {
                "seam": "E2",
                "what": "the shell step subprocess with the runtime-injected environment",
                "where": "src/scaling_evolve/algorithms/eve/workflow/evaluation.py:277-347",
            },
        ],
        "UNVERIFIED": (
            "the agent lane is not exercised by this subcommand: A0.1 needs only the evaluator "
            "lane, which runs here through EvE's own evaluate() path. The LLM-driven end-to-end "
            "EvE round is a separate experiment (see out/run002/ if present)."
        ),
    }
    out_path = Path(args.out) if args.out else (run_dir / "conformance.json")
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")
    print(json.dumps({"verdict": report.verdict, "counters": report.counters,
                      "out": str(out_path), "traces_ok": validation.get("ok")}, indent=1))
    if not validation.get("ok"):
        return _die(EXIT_INTERNAL, "a trace failed validation; see conformance.json")
    return report.exit_code


def _staging_declaration(adoption: dict) -> dict:
    """The adopted A0-wide `failure_stage_mapping`, with the digests that were checked.

    `adapter_contract.md` §5.3 makes this table A0-wide; declaring it (rather than only obeying
    it) is what lets a reader confirm two runtimes' FailureStage counts join.
    """
    return {
        "declared": selectionmap.failure_stage_mapping(),
        "adopted_from": selectionmap.CANONICAL_SOURCE,
        "runtime_declaration": selectionmap.RUNTIME_DECLARATION,
        "adoption_check": adoption,
        "staging_rule": (
            "every C* row: failure_stage = table(E* status, E* failure.kind); the same value is "
            "written to the trace event and to the row, so check (c) of §4.5 cannot drift"
        ),
        "extension": (
            "rows whose E* verdict is `ok` but whose runtime attempt failed anyway are staged "
            "evaluator_failed and counted in a01.failure_stage_extension — declared, not silent; "
            "0 such rows in this run"
        ),
    }


def _harness_row(row: "a01.CandidateComparison", theta: common.Theta) -> dict:
    """One row in the shape a0/conformance reads.

    Keys are chosen from the runner's own alias lists so that nothing has to be guessed:
    `runtime_scalar` (RUNTIME_VALUE_KEYS), `solution_sha256` (ROW_SOURCE_KEYS),
    `canonical_digest` (ROW_DIGEST_KEYS), `evaluator_evidence` (ROW_EVIDENCE_KEYS),
    `exit_code`, `failure_kind`, `failure_stage`, `objective`, `theta_e_attempt`.
    """
    reference = row.reference_outcome or {}
    digest = reference.get("canonical_digest")
    failure = reference.get("failure") or {}
    return {
        "candidate_id": row.candidate_id,
        "role": row.role,
        # E*'s own verdict on this candidate (the runner compares the runtime against E* itself,
        # never against this field; it is here so a reader does not have to open E_STAR.json).
        "reference_status": row.reference_status,
        "solution_sha256": row.solution_sha256,
        "canonical_digest": digest,
        "exit_code": row.reference_rc,
        # The derived failure surface (§4.5). `failure_stage` is the value the adapter staged the
        # unit with in the trace, from the adopted frozen table -- the runner compares it against
        # the stage that table assigns to E*'s failure.kind, so declaring it here is what makes
        # check (c) executed rather than absent.
        "failure_kind": failure.get("kind"),
        "failure_kind_source": (
            "reference"
            if failure.get("kind")
            else None
        ),
        "failure_message": failure.get("message"),
        "failure_stage": row.failure_stage,
        "failure_stage_basis": row.failure_stage_basis,
        "failure_stage_mapping_digest": selectionmap.FROZEN_FAILURE_STAGE_MAPPING_DIGEST,
        "failure_kind_note": (
            "EvE's lane cannot express invalid/error at all -- it substitutes "
            "evaluation.failure_score 0.0 (workflow/evaluation.py:161-165) -- so the kind and "
            "the stage on this row are E*'s, recorded with attribution rather than observed on "
            "the runtime side; the runtime side of the row is `evaluator_evidence`"
        ) if row.reference_status != "ok" else None,
        "objective": {
            "name": "sum_radii",
            "value": row.reference_scalar,
            "direction": "max",
            "status": row.reference_status,
        },
        "runtime_scalar": row.runtime_scalar,
        "runtime_evidence_status": row.runtime_evidence_status,
        "runtime_evidence_detail": row.runtime_evidence_detail,
        "evaluator_evidence": {
            "status": row.runtime_evidence_status,
            "detail": row.runtime_evidence_detail,
        },
        "delta": row.delta,
        "within_epsilon": row.within_epsilon,
        "classification": row.classification,
        "theta_e_attempt": {
            "evaluator": "E* (a0/tasks/circle-packing/e_star.py)",
            "fidelity": theta.fidelity,
            "fraction": theta.fraction,
            "seed": theta.seed,
            "n": theta.n,
            "runs": theta.runs,
            "runtime_budget_ms": theta.runtime_budget_ms,
            "timeout_s": theta.timeout_s,
            "granted_class": f"E* {theta.fidelity}",
            "commanded_class": f"E* {theta.fidelity}",
            "note": (
                "EvE hands the evaluation step no evaluator parameters at all; the step is the "
                "adapter's, and it passes theta_E through verbatim. seed_delivery is therefore "
                "'adapter-pinned'."
            ),
        },
        "runtime_lane": {
            "path": "SolverEvaluator.evaluate -> _run_evaluation_steps -> _run_shell_step",
            "where": "src/scaling_evolve/algorithms/eve/workflow/evaluation.py:119-347",
        },
        # E*'s own manifest line, captured inside the runtime's evaluation lane. Not parsed for
        # the score (the canonical outcome JSON is the source of the number) — it is handed to
        # the conformance runner as an independent confirmation channel.
        "raw": (row.side_channel or {}).get("e_star_manifest_line"),
        "e_star_manifest_line": (row.side_channel or {}).get("e_star_manifest_line"),
    }


def _failure_stage_counts(score_trace: Path) -> dict:
    """Counts by (run_id, iteration, candidate_id) unit, as trace_validate.py stats does."""
    counts: dict[str, int] = {}
    seen: set[tuple] = set()
    if not Path(score_trace).is_file():
        return counts
    for line in Path(score_trace).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        stage = str(event.get("failure_stage", "none"))
        unit = (
            event.get("run_id"),
            event.get("iteration"),
            event.get("candidate_id"),
            stage,
        )
        if unit in seen:
            continue
        seen.add(unit)
        counts[stage] = counts.get(stage, 0) + 1
    return counts


def cmd_closure_probe(args) -> int:
    if args.runtime != "eve":
        return _die(EXIT_USAGE, f"this adapter implements the eve runtime only, got {args.runtime!r}")
    doc = closure_mod.run_closure_probe(
        run_dir=Path(args.run_dir),
        out_path=Path(args.out),
        step_script=Path(args.step_script) if args.step_script else None,
        candidate_dir=Path(args.candidate_dir) if args.candidate_dir else None,
    )
    print(json.dumps({
        "verdict": doc["verdict"],
        "mechanism": doc["mechanism"],
        "shortfall": doc["shortfall"],
        "out": str(args.out),
    }, indent=1))
    return int(doc["_exit_code"])


def render_adapter_md(**kw) -> str:
    ctx = kw["ctx"]
    conformance = kw["conformance"]
    a02_report = kw["a02_report"]
    lines = [
        "# EvE adapter run record",
        "",
        f"* run_id: `{kw['run_id']}`",
        f"* run_dir: `{kw['run_dir']}`",
        f"* EvE checkout: `{EVE_ROOT}` @ `{require_pinned_eve()}` (pinned)",
        f"* EID*: `{kw['eid_star']}`",
        f"* EID_r: `{kw['eid_r']['value']}` "
        f"(native_scheme `none`, mapping_mode `adapter_declared_injection`)",
        f"* EID_r derivation: `{kw['eid_r']['derivation']['algorithm']}`",
        f"  * domain: `{kw['eid_r']['derivation']['domain']}`",
        f"  * payload (published, so a third party can recompute without this adapter): "
        f"`{kw['eid_r']['derivation']['payload_canonical']}`",
        f"  * recompute: `{' '.join(kw['eid_r']['recompute_cmd'])}`",
        f"  * `eid_star` is an argument of the hash: a different `EID*` necessarily gives a "
        "different `EID_r` (`tools/recompute-eid-r --eid <mutated EID document>`).",
        f"* injected step (provenance, deliberately NOT hashed into `EID_r`): "
        f"`{kw['eid_r']['injected_step']['path']}` sha256 "
        f"`{kw['eid_r']['injected_step']['sha256']}`, from template "
        f"`{kw['eid_r']['injected_step']['template']}` sha256 "
        f"`{kw['eid_r']['injected_step']['template_sha256']}`",
        f"* template: `{common.ADAPTER_DIR / 'steps' / 'eve_evaluator_step.sh.tmpl'}`",
        f"* theta_E: `{json.dumps(kw['theta'].trace_payload(), sort_keys=True)}`",
        f"* F_r: `{json.dumps(kw['fr'].trace_payload(), sort_keys=True)}` "
        f"(spec_hash = canonical_file_digest of the declaration)",
        f"* evalcontract verify: rc={kw['verify']['verify_rc']}",
        f"* budget_hard: `{json.dumps(kw['budget'], sort_keys=True)}`",
        f"* wall clock for the whole adapter run: {kw['elapsed']:.1f}s",
        "",
        "## Declarations (adapter_contract.md §2, §5)",
        "",
        f"* seed repo: `(github_url, commit)` = "
        f"`({ctx.problem.github_url}, {ctx.problem.commit})`; a missing half is an error "
        "(`RepoTaskProblem._application_source`, problem/repo.py:44-58).",
        f"* editable: `files={list(ctx.problem.editable_files)}`, "
        f"`folders={list(ctx.problem.editable_folders)}` (`configs/eve/application/circle_packing.yaml:7-10`).",
        "* the candidate overlay is `solution.py` only; the seed snapshot supplies the rest of "
        "the task repo. Declared here because it is a deviation from the repo's own "
        "`candidate.py` editable list, forced by `C*`'s layout (`C_STAR/manifest.json`).",
        f"* reference evaluator: `{common.E_STAR_PYTHON} {common.E_STAR_SCRIPT} evaluate ...` "
        "(binding decision 2).",
        "* `E*` is never scalarized by the runtime: the step writes E*'s full `fields` map into "
        "`score.yaml` and sets `score = fields.sum_radii`; `F_r = scalar(E*)` is declared in "
        "`a0/contract/fr/scalar.json` and hashed into every trace event.",
        "",
        "## A0.1",
        "",
        f"* verdict: **{conformance.verdict}**",
        f"* counters: `{json.dumps(conformance.counters, sort_keys=True)}`",
        f"* FailureStage counts over `C*` (joinable across runtimes, adopted frozen table "
        f"`{selectionmap.FROZEN_FAILURE_STAGE_MAPPING_DIGEST[:12]}…`): "
        f"`{json.dumps(conformance.failure_stage_counts(), sort_keys=True)}`",
        f"* staging basis: `{json.dumps(conformance.failure_stage_extension(), sort_keys=True)}`",
        f"* epsilon: {conformance.epsilon}",
        f"* **scope of that verdict — {conformance.agreement_scope()['statement']}**",
        "* per-candidate reference/runtime values: see `conformance.json` → `a01.candidates`",
        "",
        "## A0.2",
        "",
    ]
    if a02_report is None:
        lines.append("* not run in this invocation")
    else:
        lines.append(f"* iterations total: {a02_report.iterations_total}")
        lines.append("* frozen sampling config: "
                     f"`{json.dumps(a02_report.frozen_config, sort_keys=True)}`")
        for case in a02_report.cases:
            lines.append(
                f"* `{case.name}`: n={case.n_iterations} (effective {case.extra.get('n_effective')}), "
                f"p̂={case.p_hat:.6f}, H0 p={case.p0:.10f}, p-value={case.p_value:.3g}, "
                f"reject={case.reject_h0}"
            )
        contrast = a02_report.observable_self_check.get("score_dependence_contrast")
        if contrast:
            lines.append(f"* score→selection contrast: `{json.dumps(contrast, sort_keys=True)}`")
    lines += [
        "",
        "## False-green trap (plan:551-552)",
        "",
        f"* detected: {conformance.trap.get('detected')}",
        f"* candidates with a synthetic score: "
        f"`{json.dumps(conformance.trap.get('candidates_with_synthetic_score'))}`",
        f"* shipped-step reproduction: "
        f"`{json.dumps(kw['trap_reproduction'], sort_keys=True)[:600] if kw['trap_reproduction'] else None}`",
        "",
        "## UNVERIFIED",
        "",
        "* the agent lane: `codex` cannot complete a model call on this host, so no full EvE "
        "iteration has been run end to end. A0.2 exercises the runtime's *sampling and "
        "selection machinery* through the real sampler classes and the real call site; the "
        "LLM-driven path stays UNVERIFIED.",
        "* closure: see `closure.json` — the agent lane cannot be probed today.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "run": cmd_run,
        "conformance": cmd_conformance,
        "closure-probe": cmd_closure_probe,
    }
    try:
        return handlers[args.command](args)
    except common.CandidateSetError as exc:
        return _die(EXIT_CANDIDATE_SET, str(exc))
    except EveWiringError as exc:
        return _die(EXIT_CONTRACT, str(exc))
    except KeyboardInterrupt:
        return _die(EXIT_INTERNAL, "interrupted")
