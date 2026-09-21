"""Assembling one SimpleLoop run out of the frozen parts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import traces as trace_mod
from .candidates import CandidateSet
from .eidmap import EID_R_DECLARATION, EidContext, derive_eid_r, sha256_file
from .estareval import EStarEvaluator
from .loop import Budget, RunOutcome, SimpleLoop
from .policy import canonical_bytes, canonical_file_digest, primary_field
from .solvers import make_solver

TRACE_KINDS = ("score", "selection", "resource")

EXIT_CODES = {
    0: "run completed within budget; all three traces written",
    2: "usage / configuration error",
    3: "contract mismatch: EID* does not describe the evaluator wired, or verify reported drift",
    4: "candidate-set integrity failure",
    5: "A0.1 conformance failure: E_r(c) != E*(c) +/- epsilon for at least one c in C*",
    6: "closure violation: the probe observed autonomous external acquisition",
    7: "budget exhausted (B_hard reached); traces written up to the stop",
    8: "no evaluable candidate (every candidate stopped at an earlier stratum)",
    10: "internal adapter error",
}


@dataclass
class Settings:
    work_root: Path
    adapter_dir: Path
    e_star_python: Path
    e_star_script: Path
    candidate_set: CandidateSet
    eid: EidContext
    policy: dict
    theta: dict
    run_dir: Path
    run_id: str
    task: str
    runtime: str
    budget: Budget
    epsilon: float
    solver_kind: str
    solver_script: Path | None = None
    inject_scores: dict = field(default_factory=dict)
    max_iterations: int = 64
    reference_table: Path | None = None
    evalcontract_py: Path | None = None
    #: the harness measurement envelope (external review D3), handed over by the runner as
    #: `A0_ENVELOPE` or `--envelope`. When it is absent the A0.1 rows still report their identity,
    #: but they cannot echo a measurement token -- which the checker treats as non-accepting.
    envelope_path: Path | None = None

    @property
    def primary_field(self) -> str:
        return primary_field(self.policy)

    def rel(self, path) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.work_root.resolve()))
        except ValueError:
            return str(path)


def parse_theta(text: str | None) -> dict:
    theta = {"seed": None, "fidelity": None, "fraction": None}
    if not text:
        return theta
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"bad --theta item {chunk!r}; expected name=value")
        name, value = chunk.split("=", 1)
        name = name.strip()
        value = value.strip()
        if value.lower() in ("none", "null", ""):
            theta[name] = None
        elif name == "fraction":
            theta[name] = float(value)
        elif name == "seed":
            theta[name] = int(value)
        else:
            theta[name] = value
    return theta


def theta_block(settings: Settings, *, injected: bool, theta_extra: dict, defaults: dict) -> dict:
    """The `theta_E` envelope recorded on every event.

    A parameter the runtime cannot receive is recorded as null together with the
    fixed equivalent value actually used (trace_schema.md §3.2). SimpleLoop *can*
    receive all three: E*'s CLI takes --seed, --fidelity and --fraction, so
    normally nothing needs a default.
    """
    defaults_applied = dict(defaults)
    return {
        "seed": settings.theta["seed"],
        "fidelity": settings.theta["fidelity"],
        "fraction": settings.theta["fraction"],
        "defaults_applied": defaults_applied,
        "extra": theta_extra,
    }


def build_evaluator(settings: Settings, *, state_dir: Path, out_dir: Path) -> EStarEvaluator:
    evaluator = EStarEvaluator(
        python=settings.e_star_python,
        script=settings.e_star_script,
        state_dir=state_dir,
        out_dir=out_dir,
        seed=settings.theta["seed"] if settings.theta["seed"] is not None else 1337,
        fidelity=settings.theta["fidelity"] or "full",
        fraction=settings.theta["fraction"] if settings.theta["fraction"] is not None else 1.0,
        n=int(settings.theta.get("n", 26)),
        runs=int(settings.theta.get("runs", 5)),
        runtime_budget_ms=float(settings.theta.get("runtime_budget_ms", 250.0)),
        timeout_s=float(settings.theta.get("timeout_s", 120.0)),
        expected_source_records=settings.eid.source_records,
        recorded_source_digest=settings.eid.evaluator_source_digest,
    )
    evaluator.verify_wiring()
    return evaluator


def adapter_md(settings: Settings, outcome: RunOutcome, evaluator: EStarEvaluator,
               theta_extra: dict) -> str:
    ident = evaluator.identity
    lines = [
        f"# adapter.md — SimpleLoop, run {settings.run_id}",
        "",
        "Written by the adapter into --run-dir (adapter_contract.md §5.2).",
        "",
        "## Evaluator identity",
        "",
        f"* `EID*` = `{settings.eid.eid_star}` (from `{settings.rel(settings.eid.document_path)}`)",
        f"* `verify` (spec `{settings.rel(settings.eid.spec_path) if settings.eid.spec_path else 'n/a'}`): "
        f"exit {settings.eid.verify_returncode} — {settings.eid.verify_stdout.strip()}",
        f"* `recompute`: exit {settings.eid.recompute_returncode} — "
        f"{settings.eid.recompute_stdout.strip().splitlines()[-1] if settings.eid.recompute_stdout else ''}",
        f"* E* script: `{settings.rel(settings.e_star_script)}` "
        f"(sha256 recomputed and compared with the EID* records: "
        f"{ident.source_verified if ident else 'NOT CHECKED'})",
        f"* E* interpreter: `{settings.rel(settings.e_star_python)}` "
        f"({ident.interpreter_version if ident else 'unknown'})",
        f"* E* self-reported evaluator_source_sha256: "
        f"`{ident.evaluator_source_sha256_self_reported if ident else None}`",
        "",
        "## `EID_r -> EID*` mapping",
        "",
        "* `native_scheme` = `none`, `mapping_mode` = `adapter_declared_injection`.",
        f"* declaration: {EID_R_DECLARATION}",
        f"* `EID_r.value` = `sha256:{derive_eid_r(eid_star=settings.eid.eid_star, source_records=settings.eid.source_records, policy=settings.policy)}`",
        f"* recompute it with: `python -m a0_adapter eidr --eid {settings.eid.document_path.name} "
        f"--eid-spec {settings.eid.spec_path.name if settings.eid.spec_path else 'n/a'}`",
        "",
        "## Frozen policy",
        "",
        f"* policy file: `a0/runtimes/simpleloop/policy/simpleloop.policy.json`",
        f"* canonical policy digest: `{hashlib.sha256(canonical_bytes(settings.policy)).hexdigest()}`",
        f"* frozen `F_r` declaration `a0/contract/fr/scalar.json` canonical digest: "
        f"`{canonical_file_digest(Path(settings.work_root) / 'a0/contract/fr/scalar.json')}`",
        f"* selection: `{settings.policy['selection']['rule_expression']}`, tie-break "
        f"`{settings.policy['selection']['tie_break']}`",
        f"* selection comparison is exact binary64; the A0.1 epsilon ({settings.epsilon}) is not "
        "used in selection",
        "",
        "## Run",
        "",
        f"* solver lane: `{settings.solver_kind}`"
        + (f" (script `{settings.rel(settings.solver_script)}`)" if settings.solver_script else ""),
        f"* theta_E: `{json.dumps({k: settings.theta[k] for k in ('seed', 'fidelity', 'fraction')})}`",
        f"* theta_E.extra: `{json.dumps(theta_extra, sort_keys=True)}`",
        f"* budget: `{json.dumps(settings.budget.as_dict(), sort_keys=True)}`",
        f"* iterations: {outcome.iterations}; evaluator calls: {evaluator.calls}",
        f"* champion: `{outcome.champion_id}` scalar `{outcome.champion_scalar}`",
        f"* stopped because: {outcome.stopped_because}",
        f"* failure_stage counts: `{json.dumps(outcome.failure_counts, sort_keys=True)}`",
        f"* adapter exit code: {outcome.exit_code} — {EXIT_CODES.get(outcome.exit_code, '?')}",
        "",
        "## Traces",
    ]
    for kind, path in sorted(outcome.trace_paths.items()):
        lines.append(f"* {kind}: `{settings.rel(path)}`")
    lines.append("")
    return "\n".join(lines)


def run_once(
    settings: Settings,
    *,
    solver_kind: str | None = None,
    solver_script: Path | None = None,
    inject_scores: dict | None = None,
    run_dir: Path | None = None,
    run_id: str | None = None,
    max_iterations: int | None = None,
    check_point: str | None = None,
    solver_timeout_s: float | None = None,
    traces: tuple[str, ...] | None = None,
    write_artifacts: bool = True,
) -> tuple[RunOutcome, EStarEvaluator, SimpleLoop]:
    run_dir = Path(run_dir or settings.run_dir)
    run_id = run_id or settings.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)

    solver_kind = solver_kind or settings.solver_kind
    solver_script = Path(solver_script) if solver_script else settings.solver_script
    inject = dict(inject_scores if inject_scores is not None else settings.inject_scores)
    injected_mode = bool(inject)

    evaluator = build_evaluator(
        settings,
        state_dir=run_dir / "estate",
        out_dir=run_dir / "outcomes",
    )
    solver = make_solver(
        solver_kind,
        candidate_set=settings.candidate_set,
        work_dir=run_dir / "work",
        script=solver_script,
        timeout_s=solver_timeout_s if solver_timeout_s is not None else 300.0,
    )

    theta_extra = {
        "n": int(settings.theta.get("n", 26)),
        "runs": int(settings.theta.get("runs", 5)),
        "runtime_budget_ms": float(settings.theta.get("runtime_budget_ms", 250.0)),
        "timeout_s": float(settings.theta.get("timeout_s", 120.0)),
        "e_star_script_sha256": sha256_file(settings.e_star_script),
        "candidate_set_sha256": settings.candidate_set.manifest_sha256,
        "evaluator_lane": "subprocess: e_star.py evaluate (frozen CLI)",
        "solver_lane": solver_kind,
    }
    if injected_mode:
        theta_extra["inject_scores_sha256"] = hashlib.sha256(
            json.dumps(inject, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    defaults = {}
    if settings.theta["seed"] is None:
        defaults["seed"] = {
            "value": 1337,
            "source": "E* requires --seed; the canonical theta_E seed (EID* Config.theta_e_canonical) is used",
        }

    writer = trace_mod.TraceWriter(
        run_dir=run_dir,
        runtime=settings.runtime,
        run_id=run_id,
        task=settings.task,
        eid_star=settings.eid.eid_star,
        eid_r=settings.eid.eid_r(settings.policy),
        theta_E=theta_block(settings, injected=injected_mode, theta_extra=theta_extra,
                            defaults=defaults),
        policy=settings.policy,
        kinds=traces or TRACE_KINDS,
    )

    loop = SimpleLoop(
        candidate_set=settings.candidate_set,
        evaluator=evaluator,
        solver=solver,
        writer=writer,
        policy=settings.policy,
        epsilon=settings.epsilon,
        budget=settings.budget,
        run_dir=run_dir,
        max_iterations=max_iterations or settings.max_iterations,
        inject_scores=inject,
        check_point=check_point,
    )
    started = time.monotonic()
    outcome = loop.execute()
    writer.close()
    elapsed = time.monotonic() - started

    if write_artifacts:
        combined = run_dir / "traces" / f"{settings.runtime}.{run_id}.all.jsonl"
        with combined.open("w", encoding="utf-8") as out:
            for kind in writer.kinds:
                path = writer.paths.get(kind)
                if path and path.is_file():
                    out.write(path.read_text(encoding="utf-8"))
        outcome.trace_paths["combined"] = str(combined)

        meta = {
            "schema": "a0.simpleloop.run_meta/v1",
            "run_id": run_id,
            "runtime": settings.runtime,
            "task": settings.task,
            "eid_star": settings.eid.eid_star,
            "eid_document": settings.rel(settings.eid.document_path),
            "eid_spec": settings.rel(settings.eid.spec_path) if settings.eid.spec_path else None,
            "eid_verify_returncode": settings.eid.verify_returncode,
            "eid_recompute_returncode": settings.eid.recompute_returncode,
            "evaluator": evaluator.identity.as_dict() if evaluator.identity else None,
            "theta_E": {
                "seed": settings.theta["seed"],
                "fidelity": settings.theta["fidelity"],
                "fraction": settings.theta["fraction"],
                "extra": theta_extra,
            },
            "policy": settings.policy,
            "solver_lane": solver_kind,
            "solver_script": settings.rel(solver_script) if solver_script else None,
            "inject_scores": inject or None,
            "budget": settings.budget.as_dict(),
            "exit_code": outcome.exit_code,
            "iterations": outcome.iterations,
            "evaluator_calls": evaluator.calls,
            "champion_id": outcome.champion_id,
            "champion_scalar": outcome.champion_scalar,
            "stopped_because": outcome.stopped_because,
            "failure_counts": outcome.failure_counts,
            "wall_sec": round(elapsed, 6),
            "history": outcome.history,
            "trace_paths": {k: settings.rel(v) for k, v in sorted(outcome.trace_paths.items())},
        }
        with (run_dir / "run_meta.json").open("w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=1, sort_keys=True)
            fh.write("\n")
        (run_dir / "adapter.md").write_text(
            adapter_md(settings, outcome, evaluator, theta_extra), encoding="utf-8"
        )
    return outcome, evaluator, loop


def validate_run_dir(settings: Settings, run_dir: Path, *, validator_python: Path,
                     trace_validate_py: Path) -> dict:
    """Validate a whole run as ONE stream — the unit the contract now freezes.

    `trace_schema.md` (updated 2026-09-20 18:14) makes the run's merged stream the
    validation unit and points at `validate-run --run-dir`; the per-kind files stay
    the reading interface. This adapter writes the merged stream, so the frozen unit
    is available directly and a per-kind file is never reported as a run failure.
    """
    proc = subprocess.run(
        [str(validator_python), str(trace_validate_py), "validate-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, cwd=str(settings.work_root),
    )
    return {
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def validate_trace_paths(settings: Settings, paths: dict, *, validator_python: Path,
                        trace_validate_py: Path) -> dict:
    """Run a0/contract/trace_validate.py over every trace file a run wrote.

    The verdict is reported as it comes back. It is deliberately not softened: a
    selection trace whose `source_score_event_id` points at a score event in a
    sibling file is reported as invalid, because that is what the frozen validator
    says (see HANDOFF_to_contract_owner.md §4).
    """
    results = {}
    for kind, path in sorted(paths.items()):
        for cmd in ("validate", "stats"):
            proc = subprocess.run(
                [str(validator_python), str(trace_validate_py), cmd, "--trace", str(path)],
                capture_output=True, text=True, cwd=str(settings.work_root),
            )
            results.setdefault(kind, {})[cmd] = {
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip(),
                "stderr": (proc.stderr or "").strip(),
            }
    return results


def validate_traces(settings: Settings, outcome: RunOutcome, *, validator_python: Path,
                    trace_validate_py: Path) -> dict:
    return validate_trace_paths(settings, outcome.trace_paths,
                               validator_python=validator_python,
                               trace_validate_py=trace_validate_py)
