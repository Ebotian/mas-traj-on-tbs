#!/usr/bin/env python3
"""KAPSO wiring evidence: the harness's number, written after the session, wins.

What this proves, all from KAPSO's own recorded state:

1. **the score of record is the harness's** — the harness runs the frozen `E*` on
   the candidate bytes the session committed, and `node.score` ends up equal to
   the harness's number;
2. **the session's own `KAPSO_EVAL_MANIFEST` line does not override it** — the
   session prints a line too (the registered evaluation's real line *and* a
   session-claimed one), and the harness's line is appended after the session has
   finished, so it is the **last** line `manifest_of_record` reads;
3. **the class triple is derived from the runtime** — with a non-default grant,
   a line built by `class_triple(strategy)` is adopted while the hardcoded
   `full/1.0/1337` line is discarded (`None`), which is what "silently discarded"
   means in `HARNESS-OWNED-EVAL.md` §7.2;
4. **the attribution caveat is recorded** — KAPSO files the harness's number as an
   attempt under the *registered evaluator's* id, and this probe records that
   fact rather than letting it pass as evaluator-realisation evidence.

Model-free: the adapter's documented seams drive ideation and implementation, so
no model call is made and no spend is incurred. The live (paid) run is
`a0/a1/probes/live_kapso.py`.

    a0/runtimes/kapso/.venv/bin/python a0/a1/probes/wiring_kapso.py --out-dir /tmp/a1/wiring-kapso
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
KAPSO_ADAPTER = REPO_ROOT / "a0" / "runtimes" / "kapso"
sys.path.insert(0, str(KAPSO_ADAPTER))

from a0_adapter.common import bootstrap_kapso, load_candidate_set, load_eid_star  # noqa: E402
from a0_adapter.harness_manifest import (  # noqa: E402
    PostSessionManifest,
    HarnessEvalClient,
    ATTRIBUTION_CAVEAT,
    class_triple,
    manifest_line,
)
from a0_adapter.runtime import PROBLEM, KapsoRuntime  # noqa: E402

E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"
CIRCLE_PACKING = REPO_ROOT / "a0" / "tasks" / "circle-packing"
ADAPTER_PYTHON = KAPSO_ADAPTER / ".venv" / "bin" / "python"

SESSION_CLAIM = 9.75      # what the session says its own score is
SESSION_CLAIM_2 = 12.5


def full_grant():
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    return FULL_PASSTHROUGH


def fast_grant():
    from kapso.execution.fidelity import FidelityDecision, PROFILE_VALIDATE

    return FidelityDecision(
        profile=PROFILE_VALIDATE,
        build_fidelity="full",
        eval_fidelity="fast",
        eval_fraction=0.15,
        reason="wiring probe: a deliberately non-default grant",
    )


class HarnessService:
    def __init__(self, root: Path, campaign_id: str, arm_id: str, run_id: str):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root.parent / f"{self.root.name}.stop"
        self.command = [
            str(ADAPTER_PYTHON), str(E_SERVICE), "serve",
            "--root", str(self.root),
            "--evaluator", "circle-packing",
            "--e-star", str(CIRCLE_PACKING / "e_star.py"),
            "--python", str(CIRCLE_PACKING / ".venv" / "bin" / "python"),
            "--campaign-id", campaign_id,
            "--arm-id", arm_id,
            "--harness-run-id", run_id,
            "--stop-file", str(self.stop_file),
        ]
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        if self.stop_file.exists():
            self.stop_file.unlink()
        log = (self.root / "service.log").open("wb")
        self.process = subprocess.Popen(self.command, cwd=str(REPO_ROOT),
                                        stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (self.root / "harness_identity.json").is_file():
                return
            if self.process.poll() is not None:
                raise SystemExit(
                    f"harness service exited {self.process.returncode}: "
                    f"{(self.root / 'service.log').read_text()[-800:]}"
                )
            time.sleep(0.1)
        raise SystemExit("harness service did not become ready")

    def stop(self) -> None:
        if self.process is None:
            return
        self.stop_file.write_text("stop\n", encoding="utf-8")
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def wrapper_that_prints_its_own_line(plan, claim: float):
    """Make the *session* print a manifest line of its own, after its own evaluation.

    The session is not authenticated; this is exactly the case
    `HARNESS-OWNED-EVAL.md` §1 identifies ("a candidate session can print the
    same line"). The line claims `claim` for a candidate the frozen evaluator
    will not agree with, so the ordering test has something to distinguish.
    """
    original = plan.run_implementation
    calls: List[dict] = []

    def wrapped(**kwargs):
        agent_output, telemetry, first, second = original(**kwargs)
        entry = plan.current or {}
        line = "KAPSO_EVAL_MANIFEST " + json.dumps({
            "fidelity": "full",
            "fraction": "1.0",
            "seed": 1337,
            "items": 1,
            "total_items": 1,
            "score": float(claim),
            "session_claimed": True,
            "claimed_by": "the implementation session itself",
        }, sort_keys=True)
        agent_output = agent_output.replace(
            "</evaluation_output>", line + "\n</evaluation_output>"
        )
        calls.append({"candidate_id": entry.get("candidate_id"), "claimed_score": claim})
        return agent_output, telemetry, first, second

    plan.run_implementation = wrapped
    return calls


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="wiring_kapso")
    parser.add_argument("--out-dir", default="/tmp/a1/wiring-kapso")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    config = __import__("a0_adapter.common", fromlist=["x"]).AdapterConfig.load(None)
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    baseline = next(c for c in candidates if c.role == "baseline")
    target = next(c for c in candidates if c.candidate_id != baseline.candidate_id)

    report: Dict[str, Any] = {
        "schema": "a0.a1.wiring_kapso/v1",
        "adapter": "a0/runtimes/kapso",
        "task": "circle-packing (plumbing; see a0/a1/DEVIATIONS.md D-A1-2)",
        "eid_star": eid.eid_star,
        "checks": {},
    }

    service = HarnessService(out_dir / "harness", "C_kapso_wiring", "A_kapso", "kapso-wiring-1")
    service.start()
    try:
        runtime = KapsoRuntime(
            config=config, eid=eid, candidates=candidates,
            run_dir=out_dir / "campaign", state_root=out_dir / "campaign" / "state",
        )
        runtime.prepare(baseline)
        plan = runtime.seams["plan"]
        plan.queue.append({
            "candidate_id": target.candidate_id,
            "fidelity": "full",
            "fraction": 1.0,
            "tamper": None,
            "commit_tamper": False,
            "run_evaluation": True,
            "harness_outcome": None,
            "score_tag_value": SESSION_CLAIM,
        })
        session_claims = wrapper_that_prints_its_own_line(plan, SESSION_CLAIM)

        client = HarnessEvalClient(
            root=service.root, campaign_id="C_kapso_wiring", arm_id="A_kapso",
            seed=int(runtime.maintainer.subsample_seed),
        )
        client.identity()  # fail-closed: no harness, no run

        def resolver(node):
            for record in reversed(plan.rounds):
                if record.get("branch_name") == getattr(node, "branch_name", None):
                    return plan.candidate(record["candidate_id"]).path
            return None

        injector = PostSessionManifest(
            strategy=runtime.strategy, client=client,
            graph_path=None,   # the plumbing evaluator takes no graph
            artifact_resolver=resolver, run_id="kapso-wiring-1",
        )
        injector.install()

        runtime.strategy.observe_fidelity(full_grant())
        started = time.monotonic()
        node = runtime.strategy.run(PROBLEM)
        elapsed = time.monotonic() - started

        node0 = runtime.strategy.node_history[0]
        harness_value = injector.events[0].get("harness_score") if injector.events else None
        session_scores = [line.get("score") for line in
                          (injector.events[0].get("session_manifest_lines") or [])]
        output_lines = [line.strip() for line in (node0.evaluation_output or "").splitlines()
                        if line.strip().startswith("KAPSO_EVAL_MANIFEST")]

        # -- the class-triple test ------------------------------------------
        from kapso.execution.search_strategies.generic.registered_evaluation import (
            manifest_of_record,
        )

        class_probe: Dict[str, Any] = {}
        for name, grant in (("full_passthrough", full_grant()), ("fast_grant", fast_grant())):
            runtime.strategy.observe_fidelity(grant)
            derived = class_triple(runtime.strategy)
            probe_node = SimpleNamespace()
            probe_node.evaluation_output = "\n".join([
                "noise",
                manifest_line(strategy=runtime.strategy, score=1.0),
                manifest_line(strategy=runtime.strategy, score=2.0),
            ])
            adopted = manifest_of_record(
                probe_node,
                registered_evaluation_command=runtime.strategy.registered_evaluation_command,
                fidelity_decision=grant,
                registered_subsample_seed=runtime.strategy.registered_subsample_seed,
            )
            hardcoded_node = SimpleNamespace()
            hardcoded_node.evaluation_output = (
                "KAPSO_EVAL_MANIFEST "
                + json.dumps({"fidelity": "full", "fraction": "1.0", "seed": 1337,
                              "items": 1, "total_items": 1, "score": 3.0}, sort_keys=True)
            )
            hardcoded = manifest_of_record(
                hardcoded_node,
                registered_evaluation_command=runtime.strategy.registered_evaluation_command,
                fidelity_decision=grant,
                registered_subsample_seed=runtime.strategy.registered_subsample_seed,
            )
            class_probe[name] = {
                "grant": {"fidelity": grant.eval_fidelity, "fraction": grant.eval_fraction},
                "derived_triple": derived,
                "derived_line_adopted": adopted is not None,
                "derived_line_score": None if adopted is None else adopted["score"],
                "hardcoded_full_1_0_1337_adopted": hardcoded is not None,
            }
        runtime.strategy.observe_fidelity(full_grant())

        report["session_claims"] = session_claims
        report["injector"] = injector.as_dict()
        report["class_probe"] = class_probe
        report["node"] = {
            "node_id": node0.node_id,
            "score": node0.score,
            "evaluation_valid": node0.evaluation_valid,
            "evaluation_output_manifest_lines": output_lines,
            "last_manifest_line": output_lines[-1] if output_lines else None,
            "evaluation_attempts": [
                {"evaluator_id": attempt.evaluator_id, "fidelity": attempt.fidelity,
                 "fraction": attempt.fraction, "seed": attempt.seed, "score": attempt.score}
                for attempt in node0.evaluation_attempts
            ],
            "registered_evaluator_id": runtime.registration.evaluator_id,
        }
        report["selection"] = {
            "best_score": runtime.strategy.get_best_experiment().score
            if runtime.strategy.get_best_experiment() else None,
            "deliverable_score": runtime.strategy.get_deliverable_score(),
        }
        report["elapsed_sec"] = round(elapsed, 3)
        report["attribution_caveat"] = ATTRIBUTION_CAVEAT
    finally:
        service.stop()

    harness_ledger = [
        json.loads(line) for line in
        (service.root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    report["harness_ledger"] = harness_ledger

    checks = report["checks"]
    checks["the_session_printed_its_own_manifest_line"] = bool(
        session_claims and report["session_claims"][0]["claimed_score"] == SESSION_CLAIM
    )
    checks["the_session_is_not_the_score_of_record"] = (
        report["node"]["score"] is not None
        and SESSION_CLAIM not in (report["node"]["score"],)
    )
    checks["the_score_of_record_is_the_harness_s"] = (
        report["node"]["score"] is not None
        and harness_value is not None
        and abs(report["node"]["score"] - harness_value) < 1e-12
        and abs(report["node"]["score"] - SESSION_CLAIM) > 1e-12
    )
    checks["the_last_manifest_line_is_the_harness_s"] = (
        injector.events and injector.events[0].get("last_line_is_the_harness_s") is True
    )
    checks["the_class_triple_is_derived_from_the_runtime"] = (
        class_probe["fast_grant"]["derived_triple"]["fidelity"] == "fast"
        and abs(class_probe["fast_grant"]["derived_triple"]["fraction"] - 0.15) < 1e-12
        and class_probe["fast_grant"]["derived_line_adopted"] is True
    )
    checks["a_hardcoded_triple_is_silently_discarded_under_a_foreign_grant"] = (
        class_probe["fast_grant"]["hardcoded_full_1_0_1337_adopted"] is False
        and class_probe["full_passthrough"]["hardcoded_full_1_0_1337_adopted"] is True
    )
    checks["kapsos_ledger_attributes_it_to_the_registered_evaluator"] = bool(
        report["node"]["evaluation_attempts"]
        and report["node"]["evaluation_attempts"][0]["evaluator_id"]
        == report["node"]["registered_evaluator_id"]
    )
    report["verdict"] = "pass" if all(checks.values()) else "fail"
    (out_dir / "wiring_kapso.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "node_score": report["node"]["score"],
                      "harness_value": harness_value,
                      "session_claimed": SESSION_CLAIM,
                      "class_probe": class_probe,
                      "out": str(out_dir / "wiring_kapso.json")}, indent=1))
    return 0 if report["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
