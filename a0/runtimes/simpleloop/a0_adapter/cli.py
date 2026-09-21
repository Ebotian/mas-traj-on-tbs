"""Adapter CLI — the frozen interface of a0/contract/adapter_contract.md §3.

    python -m a0_adapter run            --runtime simpleloop ...
    python -m a0_adapter conformance    --runtime simpleloop ...
    python -m a0_adapter closure-probe  --runtime simpleloop ...
    python -m a0_adapter a02-check      --runtime simpleloop ...
    python -m a0_adapter eidr           --eid <EID.json>

Exit codes are the contract's table (adapter_contract.md §3.1), implemented in
a0_adapter/runner.py::EXIT_CODES.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import a02check, closure, conformance
from .candidates import CandidateSetError, load_candidate_set
from .eidmap import EidError, load_eid
from .estareval import EvaluatorWiringError
from .loop import Budget
from .policy import PolicyError, load_policy
from .runner import (EXIT_CODES, Settings, parse_theta, run_once, validate_run_dir,
                      validate_traces)
from .solvers import SolverError


class UsageError(RuntimeError):
    """Bad flags / unreadable inputs. Adapter exit 2 (adapter_contract.md §3.1)."""


def resolve_repo_root() -> Path:
    """The checkout this adapter runs from: ``$A0_REPO_ROOT`` or this file's location.

    A hard-coded host root makes a copy of the tree read and write the *original*
    contract, candidate and run directories; resolving from ``__file__`` (with an
    explicit environment override) keeps the adapter inside whichever tree it was
    copied to.
    """

    override = os.environ.get("A0_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    # <repo>/a0/runtimes/simpleloop/a0_adapter/cli.py -> parents[4] is <repo>
    return Path(__file__).resolve().parents[4]


#: The repo root every relative default below is joined with (`--work-root`).
DEFAULT_WORK_ROOT = str(resolve_repo_root())
DEFAULT_CANDIDATE_SET = "a0/tasks/circle-packing/C_STAR/manifest.json"
DEFAULT_EID = "a0/tasks/circle-packing/plumbing.EID.proposed.json"
DEFAULT_EID_SPEC = "a0/tasks/circle-packing/plumbing.contract.proposed.json"
DEFAULT_E_STAR = "a0/tasks/circle-packing/e_star.py"
DEFAULT_E_STAR_PYTHON = "a0/tasks/circle-packing/.venv/bin/python"
DEFAULT_REFERENCE_TABLE = "a0/tasks/circle-packing/E_STAR.json"
DEFAULT_EVALCONTRACT = "a0/contract/evalcontract.py"
DEFAULT_TRACE_VALIDATOR = "a0/contract/trace_validate.py"
DEFAULT_VALIDATOR_PYTHON = "a0/contract/.venv/bin/python"


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime", default="simpleloop")
    parser.add_argument("--task", default="circle-packing")
    parser.add_argument("--work-root", default=DEFAULT_WORK_ROOT)
    parser.add_argument("--candidate-set", default=DEFAULT_CANDIDATE_SET)
    parser.add_argument("--eid", default=DEFAULT_EID)
    parser.add_argument("--eid-spec", default=DEFAULT_EID_SPEC)
    parser.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    parser.add_argument("--fr", default="a0/contract/fr/scalar.json")
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--epsilon", type=float, default=None)
    parser.add_argument("--e-star", default=DEFAULT_E_STAR)
    parser.add_argument("--e-star-python", default=DEFAULT_E_STAR_PYTHON)
    parser.add_argument("--evalcontract", default=DEFAULT_EVALCONTRACT)
    parser.add_argument("--trace-validator", default=DEFAULT_TRACE_VALIDATOR)
    parser.add_argument("--validator-python", default=DEFAULT_VALIDATOR_PYTHON)
    parser.add_argument("--budget", default="T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1")
    parser.add_argument("--traces", default="score,selection,resource")
    parser.add_argument(
        "--envelope", default=None,
        help="the harness measurement envelope to join A0.1 to (external review D3): the path the "
             "runner hands over as A0_ENVELOPE. Every conformance row echoes the per-candidate "
             "measurement token it finds there and attests the bytes it executed; without it the "
             "rows carry no token and the checker reports them non-accepting (fail-closed)",
    )


def envelope_path_of(args) -> Path | None:
    """The measurement envelope to use: `--envelope`, else `A0_ENVELOPE`, else none.

    The environment variable is the interface the runner uses (a flag would break adapters whose
    subcommand parser rejects it); the flag exists so a run can be reproduced by hand.
    """
    value = getattr(args, "envelope", None) or os.environ.get("A0_ENVELOPE") or None
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else path.resolve()


def build_settings(args) -> Settings:
    if args.runtime != "simpleloop":
        raise UsageError(
            f"this adapter implements runtime 'simpleloop' only; got {args.runtime!r} "
            f"(the other three runtimes are separate workstreams)"
        )
    work_root = Path(args.work_root).resolve()
    adapter_dir = Path(__file__).resolve().parent.parent

    def abs_of(value: str) -> Path:
        """External artifacts (C*, E*, EID*) are addressed from the work root."""
        path = Path(value)
        return path if path.is_absolute() else (work_root / value)

    def local_of(value: str) -> Path:
        """This adapter's own outputs live under its own directory, never elsewhere."""
        path = Path(value)
        return path if path.is_absolute() else (adapter_dir / value)

    policy = load_policy()
    candidate_set = load_candidate_set(abs_of(args.candidate_set))
    eid = load_eid(
        abs_of(args.eid),
        spec_path=abs_of(args.eid_spec) if args.eid_spec else None,
        evalcontract_py=abs_of(args.evalcontract),
        python=abs_of(args.validator_python) if Path(args.validator_python).is_absolute()
        else Path(sys.executable),
        work_root=work_root,
    )
    theta = parse_theta(args.theta)
    theta.setdefault("n", 26)
    theta.setdefault("runs", 5)
    theta.setdefault("runtime_budget_ms", 250.0)
    theta.setdefault("timeout_s", 120.0)

    epsilon = args.epsilon if args.epsilon is not None else eid.epsilon
    if args.epsilon is not None and abs(args.epsilon - eid.epsilon) > 0:
        raise UsageError(
            f"--epsilon {args.epsilon} disagrees with the frozen EID* Config epsilon {eid.epsilon}; "
            f"a change of tolerance is a change of EID* (protocol line 509)"
        )

    budget = Budget()
    for chunk in args.budget.split(","):
        if not chunk.strip():
            continue
        name, value = chunk.split("=", 1)
        name = name.strip()
        if name == "T_wall_sec":
            budget.T_wall_sec = float(value)
        elif name == "N_evaluatorCalls":
            budget.N_evaluatorCalls = int(value)
        elif name == "concurrency":
            budget.concurrency = int(value)
        else:
            raise UsageError(f"unknown budget key {name!r}")

    run_dir = local_of(args.run_dir) if args.run_dir else (adapter_dir / "out" / "default-run")
    run_id = run_dir.name
    return Settings(
        work_root=work_root,
        adapter_dir=adapter_dir,
        e_star_python=abs_of(args.e_star_python),
        e_star_script=abs_of(args.e_star),
        candidate_set=candidate_set,
        eid=eid,
        policy=policy,
        theta=theta,
        run_dir=run_dir,
        run_id=run_id,
        task=args.task,
        runtime=args.runtime,
        budget=budget,
        epsilon=epsilon,
        solver_kind=getattr(args, "solver", "injected"),
        solver_script=(local_of(args.solver_script) if getattr(args, "solver_script", None) else None),
        inject_scores=(
            json.loads(local_of(args.inject_scores).read_text(encoding="utf-8"))
            if getattr(args, "inject_scores", None)
            else {}
        ),
        max_iterations=getattr(args, "max_iterations", 64),
        reference_table=abs_of(args.reference_table) if getattr(args, "reference_table", None) else None,
        evalcontract_py=abs_of(args.evalcontract),
        envelope_path=envelope_path_of(args),
    )


def cmd_run(args) -> int:
    settings = build_settings(args)
    traces = tuple(t.strip() for t in args.traces.split(",") if t.strip())
    unknown = [t for t in traces if t not in ("score", "selection", "resource")]
    if unknown:
        raise UsageError(f"unknown trace kind(s) {unknown}; --traces takes score,selection,resource")
    outcome, _evaluator, _loop = run_once(
        settings,
        solver_timeout_s=args.solver_timeout,
        run_id=args.run_id or settings.run_id,
        traces=traces,
    )
    validator_python = (
        Path(args.validator_python)
        if Path(args.validator_python).is_absolute()
        else settings.work_root / args.validator_python
    )
    trace_validate_py = settings.work_root / args.trace_validator
    validation = validate_traces(
        settings,
        outcome,
        validator_python=validator_python,
        trace_validate_py=trace_validate_py,
    )
    # The frozen unit is the run's merged stream (trace_schema.md §1, `validate-run`).
    # The per-kind files are the reading interface; a cross-file reference in a
    # selection file is not a run failure.
    run_validation = validate_run_dir(
        settings, settings.run_dir,
        validator_python=validator_python, trace_validate_py=trace_validate_py,
    )
    summary = {
        "schema": "a0.simpleloop.run_summary/v1",
        "run_id": args.run_id or settings.run_id,
        "run_dir": settings.rel(settings.run_dir),
        "exit_code": outcome.exit_code,
        "exit_meaning": EXIT_CODES.get(outcome.exit_code),
        "iterations": outcome.iterations,
        "champion_id": outcome.champion_id,
        "champion_scalar": outcome.champion_scalar,
        "scored_candidates": outcome.scored_candidates,
        "failure_counts": outcome.failure_counts,
        "stopped_because": outcome.stopped_because,
        "trace_paths": {k: settings.rel(v) for k, v in sorted(outcome.trace_paths.items())},
        "trace_validation_run_unit": run_validation,
        "trace_validation_per_file": validation,
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    if run_validation["returncode"] != 0:
        print(
            f"WARNING: the run's merged stream did not validate: {run_validation['stdout']}",
            file=sys.stderr,
        )
    return outcome.exit_code


def cmd_conformance(args) -> int:
    settings = build_settings(args)
    result = conformance.run_conformance(settings)
    out = Path(args.out).resolve() if args.out else (settings.run_dir / "conformance.json")
    conformance.write(result, out)
    print(json.dumps(conformance.summarise(result), indent=1, sort_keys=True))
    print(f"written: {settings.rel(out)}")
    return 0 if result["verdict"] == "pass" else 5


def cmd_closure_probe(args) -> int:
    settings = build_settings(args)
    result = closure.run_probe(
        settings,
        mechanism=getattr(args, "mechanism", "host"),
        out=Path(args.out).resolve() if getattr(args, "out", None) else settings.run_dir / "closure.json",
        probe_script=settings.work_root / (getattr(args, "probe_script", None) or "a0/env/checks/probe_egress.sh"),
        solver_cmd=getattr(args, "probe_cmd", None),
    )
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["verdict"] == "closed" else 6


def cmd_a02(args) -> int:
    settings = build_settings(args)
    out = Path(args.out).resolve() if args.out else (settings.run_dir / "a02_checks.json")
    result = a02check.run_all(settings, out_root=out.parent)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(a02check.summarise(result), indent=1, sort_keys=True))
    print(f"written: {settings.rel(out)}")
    return 0 if result["verdict"] == "pass" else 5


def cmd_eidr(args) -> int:
    work_root = Path(args.work_root).resolve()

    def abs_of(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (work_root / value)

    policy = load_policy()
    eid = load_eid(
        abs_of(args.eid),
        spec_path=abs_of(args.eid_spec) if args.eid_spec else None,
        evalcontract_py=abs_of(args.evalcontract),
        python=Path(sys.executable),
        work_root=work_root,
    )
    print(json.dumps(eid.eid_r(policy), indent=1, sort_keys=True))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="a0_adapter", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="one SimpleLoop run")
    add_common(p_run)
    p_run.add_argument("--run-id", default=None)
    p_run.add_argument("--solver", default="injected",
                       choices=["injected", "codex", "claude"])
    p_run.add_argument("--solver-script", default=None)
    p_run.add_argument("--inject-scores", default=None)
    p_run.add_argument("--max-iterations", type=int, default=64)
    p_run.add_argument("--solver-timeout", type=float, default=300.0,
                       help="wall-clock budget for one solver-lane (agent CLI) call")
    p_run.set_defaults(func=cmd_run)

    p_conf = sub.add_parser("conformance", help="A0.1: E_r(c) vs E*(c) for every c in C*")
    add_common(p_conf)
    p_conf.add_argument("--out", default=None)
    p_conf.add_argument("--reference-table", default=DEFAULT_REFERENCE_TABLE)
    p_conf.set_defaults(func=cmd_conformance)

    p_clo = sub.add_parser("closure-probe", help="prove the runtime has no autonomous egress")
    add_common(p_clo)
    p_clo.add_argument("--mechanism", default="host")
    p_clo.add_argument("--probe-cmd", default=None)
    p_clo.add_argument("--probe-script", default=None)
    p_clo.add_argument("--out", default=None)
    p_clo.set_defaults(func=cmd_closure_probe)

    p_a02 = sub.add_parser("a02-check", help="A0.2: score -> search contract checks")
    add_common(p_a02)
    p_a02.add_argument("--out", default=None)
    p_a02.set_defaults(func=cmd_a02)

    p_eidr = sub.add_parser("eidr", help="print the EID_r -> EID* mapping")
    p_eidr.add_argument("--work-root", default=DEFAULT_WORK_ROOT)
    p_eidr.add_argument("--eid", default=DEFAULT_EID)
    p_eidr.add_argument("--eid-spec", default=DEFAULT_EID_SPEC)
    p_eidr.add_argument("--evalcontract", default=DEFAULT_EVALCONTRACT)
    p_eidr.set_defaults(func=cmd_eidr)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (CandidateSetError,) as exc:
        print(f"adapter: candidate-set integrity failure: {exc}", file=sys.stderr)
        return 4
    except (EidError, EvaluatorWiringError) as exc:
        print(f"adapter: contract mismatch: {exc}", file=sys.stderr)
        return 3
    except (SolverError, PolicyError, UsageError, ValueError) as exc:
        print(f"adapter: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - adapter exit 10 is "internal error"
        import traceback

        traceback.print_exc()
        print(f"adapter: internal error: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
