"""A0 adapter CLI: run / conformance / closure-probe (adapter_contract.md §3).

    python -m a0_adapter run           --runtime kapso --task circle-packing ...
    python -m a0_adapter conformance   --runtime kapso --candidate-set ... --out ...
    python -m a0_adapter closure-probe --runtime kapso --run-dir ... --out ...

The KAPSO source is taken from the pinned checkout on ``PYTHONPATH``
(``config/adapter.json: kapso_src``); the snapshot is read-only and is never
installed into.  Run with the adapter's own interpreter:

    .venv/bin/python -m a0_adapter ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import a01, a02, closure
from .common import (
    DEFAULT_CONFIG_PATH,
    EXIT_BUDGET,
    EXIT_CANDIDATE,
    EXIT_CLOSURE,
    EXIT_CONFORMANCE,
    EXIT_EID,
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_USAGE,
    AdapterConfig,
    AdapterError,
    ThetaE,
    bootstrap_kapso,
    check_candidate_integrity,
    fr_payload,
    load_candidate_set,
    load_eid_star,
    verify_eid_star,
    write_json,
)

RUNTIMES = ("kapso",)


def parse_budget(text: str) -> dict:
    budget = {"T_wall_sec": None, "N_evaluatorCalls": None, "concurrency": 1}
    for item in (text or "").split(","):
        if not item.strip():
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key == "concurrency":
            budget["concurrency"] = int(value)
        elif key == "T_wall_sec":
            budget["T_wall_sec"] = float(value)
        elif key == "N_evaluatorCalls":
            budget["N_evaluatorCalls"] = int(value)
        else:
            raise AdapterError(f"unknown budget key {key!r}", EXIT_USAGE)
    return budget


def common_setup(args) -> dict:
    config = AdapterConfig.load(Path(args.config) if args.config else None)
    bootstrap_kapso(config)
    eid = load_eid_star(Path(args.eid) if args.eid else config.eid_star_file)
    candidates = load_candidate_set(
        Path(args.candidate_set) if args.candidate_set else config.candidate_set
    )
    check_candidate_integrity(candidates)
    eid_checks = verify_eid_star(config, eid)
    if args.epsilon is not None and abs(float(args.epsilon) - eid.epsilon) > 1e-18:
        raise AdapterError(
            f"--epsilon {args.epsilon} does not match EID*'s frozen epsilon "
            f"{eid.epsilon}",
            EXIT_USAGE,
        )
    return {
        "config": config,
        "eid": eid,
        "candidates": candidates,
        "eid_checks": eid_checks,
    }


def write_run_adapter_md(run_dir: Path, run_id: str) -> None:
    """Place the adapter's run record in the run dir (contract §5.2)."""
    source = Path(__file__).resolve().parent.parent / "ADAPTER.md"
    text = source.read_text("utf-8").replace(
        "# KAPSO adapter — run record",
        f"# KAPSO adapter — run record (run_id: {run_id})",
    )
    (Path(run_dir) / "adapter.md").write_text(text, encoding="utf-8")


def cmd_conformance(args) -> int:
    out = Path(args.out)
    run_dir = out.parent
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"kapso-a01-{out.parent.name}"
    try:
        return _conformance(args, out, run_dir, run_id)
    except AdapterError as exc:
        _write_failure_document(out, run_id, exc, exc.code)
        raise
    except Exception as exc:  # noqa: BLE001 - exit 10 is the contract's bug code
        _write_failure_document(out, run_id, exc, EXIT_INTERNAL)
        raise


def _write_failure_document(out: Path, run_id: str, exc: Exception,
                            code: int) -> None:
    """Never leave `--out` empty: a harness must get a readable verdict.

    The document says `pass: false` and carries the exception, so a caller can
    tell an adapter failure from a missing file without parsing stderr.
    """
    write_json(out, {
        "schema": "a0.kapso.conformance/v1",
        "runtime": "kapso",
        "run_id": run_id,
        "pass": False,
        "exit_code": code,
        "candidates": [],
        "mismatches": [f"{type(exc).__name__}: {exc}"],
        "error": f"{type(exc).__name__}: {exc}",
        "note": "the adapter failed before completing A0.1; see the run dir and stderr",
    })


def _conformance(args, out: Path, run_dir: Path, run_id: str) -> int:
    ctx = common_setup(args)
    theta = ThetaE.parse(args.theta)
    fr = fr_payload(ctx["config"].fr_spec, "a0/contract/fr/scalar.json")
    write_json(run_dir / "eid_checks.json", ctx["eid_checks"])
    report = a01.run_a01(
        ctx["config"], ctx["eid"], ctx["candidates"],
        run_dir=run_dir,
        run_id=run_id,
        theta=theta,
        fr=fr,
        budget=parse_budget(args.budget),
        kinds=["score", "resource"],
    )
    write_json(run_dir / "adapter.md.json",
               {"adapter": "a0/runtimes/kapso", "run_id": run_id,
                "runtime": "kapso", "report": report["eid_r"]})
    write_run_adapter_md(run_dir, run_id)
    # a01.run_a01 writes conformance.json into the run dir; `--out` may point at
    # it or elsewhere (the A0 conformance harness passes its own path).
    report["run_dir"] = str(run_dir)
    report["out_path"] = str(out)
    write_json(run_dir / "conformance.json", report)
    if out.resolve() != (run_dir / "conformance.json").resolve():
        write_json(out, report)
    print(json.dumps({
        "run_id": run_id,
        "candidates": len(report["candidates"]),
        "pass": report["pass"],
        "mismatches": report["mismatches"],
        "trace_paths": report["trace_paths"],
        "trace_validation": {
            "unit": report["trace_validation"]["unit"],
            "returncode": report["trace_validation"]["returncode"],
        },
    }, indent=1))
    return EXIT_OK if report["pass"] else EXIT_CONFORMANCE


def cmd_run(args) -> int:
    ctx = common_setup(args)
    theta = ThetaE.parse(args.theta)
    fr = fr_payload(ctx["config"].fr_spec, "a0/contract/fr/scalar.json")
    budget = parse_budget(args.budget)
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    kinds = [kind.strip() for kind in args.traces.split(",") if kind.strip()]
    write_json(run_dir / "eid_checks.json", ctx["eid_checks"])
    write_run_adapter_md(run_dir, args.run_id)

    conformance = a01.run_a01(
        ctx["config"], ctx["eid"], ctx["candidates"],
        run_dir=run_dir / "a01",
        run_id=f"{args.run_id}-a01",
        theta=theta,
        fr=fr,
        budget=budget,
        kinds=["score", "resource"],
    ) if not args.skip_a01 else None
    selection = a02.run_a02(
        ctx["config"], ctx["eid"], ctx["candidates"],
        run_dir=run_dir / "a02",
        run_id=f"{args.run_id}-a02" if args.skip_a01 else args.run_id,
        theta=theta,
        fr=fr,
        budget=budget,
        kinds=["score", "selection", "resource"],
    ) if not args.skip_a02 else None
    write_json(run_dir / "run.json", {
        "run_id": args.run_id,
        "a01": None if conformance is None else {
            "pass": conformance["pass"],
            "mismatches": conformance["mismatches"],
            "trace_paths": conformance["trace_paths"]},
        "a02": None if selection is None else {
            "pass": selection["pass"],
            "scenarios": {name: entry["pass"]
                          for name, entry in selection["scenarios"].items()},
            "trace_paths": selection["trace_paths"]},
    })
    print(json.dumps({
        "run_id": args.run_id,
        "a01_pass": None if conformance is None else conformance["pass"],
        "a02_pass": None if selection is None else selection["pass"],
        "a02_scenarios": {} if selection is None else {
            name: entry["pass"] for name, entry in selection["scenarios"].items()},
        "traces": {} if selection is None else selection["trace_paths"],
    }, indent=1))
    ok = all(report["pass"] for report in (conformance, selection)
             if report is not None)
    return EXIT_OK if ok else EXIT_CONFORMANCE


def cmd_closure_probe(args) -> int:
    config = AdapterConfig.load(Path(args.config) if args.config else None)
    report = closure.probe(config, Path(args.run_dir), Path(args.out))
    print(json.dumps({
        "verdict": report["verdict"],
        "mechanism": report["mechanism"],
        "observed": report["observed"],
    }, indent=1))
    return EXIT_OK if report["verdict"] == "closed" else EXIT_CLOSURE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="a0_adapter")
    parser.add_argument("--config", default=None,
                        help=f"adapter config (default: {DEFAULT_CONFIG_PATH})")
    sub = parser.add_subparsers(dest="command", required=True)

    common = dict()
    p_run = sub.add_parser("run", help="A0.1 + A0.2 for one runtime")
    p_run.add_argument("--runtime", required=True, choices=RUNTIMES)
    p_run.add_argument("--task", default="circle-packing")
    p_run.add_argument("--candidate-set", default=None)
    p_run.add_argument("--eid", default=None)
    p_run.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    p_run.add_argument("--fr", default=None)
    p_run.add_argument("--run-id", required=True)
    p_run.add_argument("--run-dir", required=True)
    p_run.add_argument("--budget",
                       default="T_wall_sec=3600,N_evaluatorCalls=500,concurrency=1")
    p_run.add_argument("--traces", default="score,selection,resource")
    p_run.add_argument("--epsilon", type=float, default=None)
    p_run.add_argument("--skip-a01", action="store_true",
                       help="run A0.2 only (harness convenience)")
    p_run.add_argument("--skip-a02", action="store_true",
                       help="run A0.1 only (harness convenience)")
    p_run.set_defaults(fn=cmd_run)

    p_conf = sub.add_parser("conformance", help="A0.1 only")
    p_conf.add_argument("--runtime", required=True, choices=RUNTIMES)
    p_conf.add_argument("--candidate-set", default=None)
    p_conf.add_argument("--eid", default=None)
    p_conf.add_argument("--theta", default="seed=1337,fidelity=full,fraction=1.0")
    p_conf.add_argument("--fr", default=None)
    p_conf.add_argument("--epsilon", type=float, default=None)
    p_conf.add_argument("--run-id", default=None)
    p_conf.add_argument("--budget",
                        default="T_wall_sec=3600,N_evaluatorCalls=500,concurrency=1")
    p_conf.add_argument("--out", required=True)
    p_conf.set_defaults(fn=cmd_conformance)

    p_closure = sub.add_parser("closure-probe", help="closure probe")
    p_closure.add_argument("--runtime", required=True, choices=RUNTIMES)
    p_closure.add_argument("--run-dir", required=True)
    p_closure.add_argument("--out", required=True)
    p_closure.set_defaults(fn=cmd_closure_probe)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except AdapterError as exc:
        print(f"adapter error: {exc}", file=sys.stderr)
        return exc.code
    except Exception as exc:  # noqa: BLE001 - exit 10 is the contract's bug code
        import traceback

        traceback.print_exc()
        print(f"internal adapter error: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
