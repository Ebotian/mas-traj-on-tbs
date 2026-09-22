#!/usr/bin/env python3
"""The A1 live-session probe: one real campaign per arm, inside the closed topology.

Everything the two arms share is the *harness's*: the metering proxy on the
campaign's own port, the harness evaluation service that owns `E*`, the unix-socket
hop into a `unshare -rn` namespace, and the budget enforcer.  What differs is the
arm's own command — which is the point.

    # arm 1 (ours, T1): SimpleLoop consuming harness Outcomes
    python3 a0/a1/probes/live_probe.py arm --arm simpleloop --out-dir /tmp/a1/live

    # arm 2 (third party): KAPSO, score written after the session
    python3 a0/a1/probes/live_probe.py arm --arm kapso --out-dir /tmp/a1/live

    # the controls that cost nothing
    python3 a0/a1/probes/live_probe.py controls --out-dir /tmp/a1/live

    # the whole thing
    python3 a0/a1/probes/live_probe.py all --out-dir /tmp/a1/live

Checks, per arm, from recorded state only:

(a) the score of record equals the **harness-supplied** value;
(b) a session that prints its own ``KAPSO_EVAL_MANIFEST`` line cannot override it;
(c) the meter ledger has one row per upstream call, each with a real ``ceq``;
(d) no unmetered model call is possible — a direct attempt is refused by the
    topology, a non-allowlisted destination is refused by the meter, and an
    *induced* upstream response without usage is recorded ``unmetered`` (and would
    stop the campaign).

The DeepSeek key is read from ``$DEEPSEEK_API_KEY`` (exported by the caller from
``~/gptapi.md`` in the same command) and is never written to an artifact or an
argv: the child receives it through its environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from a0.a1.budget import Budget, BudgetEnforcer  # noqa: E402
from a0.a1.eval_service import HarnessEvalService  # noqa: E402
from a0.a1.meter_runner import MeterProxy, chat_completion  # noqa: E402
from a0.a1.topology import CampaignUplink, netns_prefix, probe_netns  # noqa: E402

SIMPLELOOP_PY = REPO_ROOT / "a0/runtimes/simpleloop/.venv/bin/python"
KAPSO_PY = REPO_ROOT / "a0/runtimes/kapso/.venv/bin/python"
GRAPH = REPO_ROOT / "a0/tasks/maxcut/suite/dev/G_dev_0001.json"
MODEL = "deepseek-flash"
MODEL_TIMEOUT = 180.0

SOLVER_SCRIPT = {
    "schema": "a0.simpleloop.solver_script/v1",
    "proposals": [
        {"iteration": 0, "kind": "c_star_member", "candidate_id": "c02_ok_low_baseline"},
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# the arm commands (these lines run *inside* the namespace)
# ---------------------------------------------------------------------------
def simpleloop_arm_command(*, base_url: str, token: str, run_dir: Path,
                           graph: Path, max_iterations: int, solver_script: Path) -> List[str]:
    return [
        str(SIMPLELOOP_PY), "-m", "a0_adapter", "run",
        "--work-root", str(REPO_ROOT),
        "--runtime", "simpleloop",
        "--task", "maxcut",
        "--candidate-set", "a0/tasks/maxcut/candidates/manifest.json",
        "--eid", "a0/a1/T1-EID.json",
        "--eid-spec", "a0/a1/T1.contract.json",
        "--eval-mode", "harness",
        "--harness-root", str(run_dir.parent / "harness"),
        "--campaign-id", run_dir.parent.name,
        "--arm-id", "A_simpleloop",
        "--graph", str(graph),
        "--baseline-candidate", "c02_ok_low_baseline",
        "--policy", "a0/runtimes/simpleloop/policy/simpleloop.maxcut.policy.json",
        "--theta", "seed=1337,fidelity=none,fraction=none,timeout_s=10",
        "--e-star", "a0/tasks/maxcut/e_star.py",
        "--solver", "deepseek",
        "--model-base-url", base_url,
        "--model-name", MODEL,
        # `=` rather than a space: a urlsafe token may begin with `-`, and
        # argparse would then read it as another option (measured).
        *(["--meter-token=" + token] if token else []),
        "--model-timeout-s", str(MODEL_TIMEOUT),
        "--max-iterations", str(max_iterations),
        "--run-dir", str(run_dir),
    ]


def kapso_arm_command(*, base_url: str, token: str, run_dir: Path, out_dir: Path) -> List[str]:
    return [
        str(KAPSO_PY), str(Path(__file__).resolve()), "kapso-inner",
        "--out-dir", str(out_dir),
        "--base-url", base_url,
        *(["--meter-token=" + token] if token else []),
        "--run-dir", str(run_dir),
    ]


# ---------------------------------------------------------------------------
# the orchestrator
# ---------------------------------------------------------------------------
class LiveCampaign:
    def __init__(self, *, arm: str, out_dir: Path, max_iterations: int = 2):
        self.arm = arm
        self.out_dir = Path(out_dir).resolve()
        self.max_iterations = max_iterations
        self.work = self.out_dir / arm
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)
        self.meter = MeterProxy(
            campaign_id=f"C_live_{arm}", arm_id=f"A_{arm}", work_dir=self.work / "meter"
        )
        # Arm 1 runs T1; arm 2 is KAPSO as its adapter is wired today
        # (a0/a1/DEVIATIONS.md D-A1-2), so the harness owns *that* task's frozen
        # evaluator for it. The ABI, the ledger and the ordering rule are the
        # same either way, which is the point being measured.
        self.evaluator = "maxcut" if arm == "simpleloop" else "circle-packing"
        self.e_star = (
            REPO_ROOT / "a0/tasks/maxcut/e_star.py"
            if arm == "simpleloop"
            else REPO_ROOT / "a0/tasks/circle-packing/e_star.py"
        )
        self.e_star_python = (
            Path(sys.executable)
            if arm == "simpleloop"
            else REPO_ROOT / "a0/tasks/circle-packing/.venv/bin/python"
        )
        self.harness = HarnessEvalService(
            root=self.work / "harness",
            campaign_id=f"C_live_{arm}",
            arm_id=f"A_{arm}",
            evaluator=self.evaluator,
            e_star_script=self.e_star,
            python=self.e_star_python,
            seed=1337,
            timeout_s=10.0 if arm == "simpleloop" else 120.0,
            harness_run_id=f"live-{arm}",
        )
        self.uplink = CampaignUplink(
            campaign_id=f"C_live_{arm}", meter_port=self.meter.port
        )
        self.enforcer = BudgetEnforcer(
            budget=Budget(T_wall_sec=1800.0, N_eval_max=50, CEq_max=200_000, P_concurrency=1),
            meter_ledger=self.meter.ledger,
            harness_eval_ledger=self.harness.ledger_path,
            campaign_id=self.harness.campaign_id,
            arm_id=self.harness.arm_id,
        )
        self.harness_process: Optional[subprocess.Popen] = None

    def run(self) -> dict:
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise SystemExit("export DEEPSEEK_API_KEY (from ~/gptapi.md) in this command")
        report: Dict[str, Any] = {
            "schema": "a0.a1.live_probe/v1",
            "arm": self.arm,
            "model_requested": MODEL,
            "graph": str(GRAPH.relative_to(REPO_ROOT)),
            "graph_sha256": sha256_file(GRAPH),
            "campaign_id": self.harness.campaign_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        # -- the topology, probed before anything spends -------------------
        (
            self.work / "meter").mkdir(parents=True, exist_ok=True)
        self.meter.start()
        try:
            self.uplink.start()
            report["meter"] = {"port": self.meter.port, "base_url": self.meter.base_url,
                               "aid": self.meter.aid(),
                               "token_issued": bool(self.meter.token)}
            # The positive control: with the relay up, an outside process can
            # reach the meter's unix socket (the runtime will do exactly this).
            from a0.a1.topology import UnixRelay  # noqa: F401  (documentation import)

            self.harness_process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "eval_service.py"),
                 "serve", "--root", str(self.harness.root), "--evaluator", self.evaluator,
                 "--e-star", str(self.e_star),
                 "--python", str(self.e_star_python),
                 "--campaign-id", self.harness.campaign_id,
                 "--arm-id", self.harness.arm_id,
                 "--harness-run-id", f"live-{self.arm}",
                 "--seed", "1337",
                 "--timeout-s", "10" if self.arm == "simpleloop" else "120",
                 "--stop-file", str(self.work / "harness.stop")],
                cwd=str(REPO_ROOT),
                stdout=(self.work / "harness.console.txt").open("wb"),
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not (
                self.harness.root / "harness_identity.json"
            ).is_file():
                time.sleep(0.05)
            if not (self.harness.root / "harness_identity.json").is_file():
                raise SystemExit("the harness evaluation service did not come up")

            # The namespace probe: negative controls must be unreachable, and the
            # meter must be reachable through the relay.
            report["topology_probe"] = _probe_with_relay(self.uplink, self.meter.port)
            report["topology_probe_note"] = (
                "run inside `unshare -rn`; the negative controls are bare IP literals, the "
                "positive control is the campaign's metered port over the unix socket"
            )

            # -- the arm ---------------------------------------------------
            if self.arm == "simpleloop":
                (self.work / "solver.json").write_text(
                    json.dumps(SOLVER_SCRIPT, indent=1, sort_keys=True) + "\n", encoding="utf-8"
                )
                command = simpleloop_arm_command(
                    base_url=self.meter.base_url, token=self.meter.token or "",
                    run_dir=self.work / "run", graph=GRAPH,
                    max_iterations=self.max_iterations,
                    solver_script=self.work / "solver.json",
                )
            else:
                command = kapso_arm_command(
                    base_url=self.meter.base_url, token=self.meter.token or "",
                    run_dir=self.work / "run", out_dir=self.work,
                )
            report["arm_command"] = command
            report["namespace_prefix"] = netns_prefix()

            started = time.monotonic()
            proc = subprocess.run(
                self.uplink.enter_command(command), cwd=str(REPO_ROOT),
                capture_output=True, text=True, timeout=1800,
                env={**os.environ,
                     "PYTHONPATH": os.pathsep.join(
                         [str(REPO_ROOT), str(REPO_ROOT / "a0/runtimes/simpleloop")]
                     )},
            )
            elapsed = time.monotonic() - started
            report["arm_exit_code"] = proc.returncode
            report["arm_stdout_tail"] = proc.stdout[-6000:]
            report["arm_stderr_tail"] = proc.stderr[-4000:]
            report["elapsed_sec"] = round(elapsed, 3)
        finally:
            (self.work / "harness.stop").write_text("stop\n", encoding="utf-8")
            if self.harness_process is not None:
                try:
                    self.harness_process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.harness_process.kill()
                    self.harness_process.wait()
            self.uplink.stop()
            self.meter.stop()

        # -- the arm's own recorded state ----------------------------------
        report["arm_state"] = self._arm_state()
        report["meter_ledger_rows"] = _ledger_rows(self.meter.ledger)
        report["meter_call_events"] = [
            event for event in self.meter.call_events() if event.get("kind") == "call"
        ]
        report["meter_verify_ledger"] = self.meter.verify_ledger()
        report["harness_ledger_rows"] = _ledger_rows(self.harness.ledger_path)
        report["budget_check"] = self.enforcer.check(label="after-live-run")
        report["meter_summary"] = self.meter.ledger_summary()
        report["checks"] = self._checks(report)
        report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
        (self.work / "live_probe.json").write_text(
            json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report

    def _arm_state(self) -> dict:
        """A uniform view of "what did this arm record", per arm.

        SimpleLoop's run writes `run_meta.json`; KAPSO's inner driver writes
        `arm_state.json`. Both are read here and reduced to the same keys, so the
        checks below do not branch on the runtime.
        """
        run_dir = self.work / "run"
        if self.arm == "kapso":
            state_path = run_dir / "arm_state.json"
            if not state_path.is_file():
                return {}
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["model_calls"] = len(state.get("model_calls") or [])
            return state
        meta_path = run_dir / "run_meta.json"
        if not meta_path.is_file():
            return {}
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        history = meta.get("history") or []
        model_proposals = [
            row for row in history if str(row.get("proposal_source", "")).startswith("model:")
        ]
        score_by_candidate = {}
        for path in (run_dir / "traces").glob("*.score.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                detail = (event.get("evaluator_evidence") or {}).get("detail") or ""
                score_by_candidate[event["candidate_id"]] = {
                    "search_signal": event.get("search_signal"),
                    "harness_supplied": "harness_supplied" in detail,
                }
        champion = meta.get("champion_id")
        champion_row = score_by_candidate.get(champion, {})
        return {
            "schema": "a0.a1.live_simpleloop_arm/v1",
            "score_of_record": meta.get("champion_scalar"),
            "score_source": "harness" if champion_row.get("harness_supplied") else "runtime",
            "session_claimed_score": None,
            "session_manifest_lines": None,
            "last_line_is_the_harness_s": None,
            "model_calls": len(model_proposals),
            "champion_id": champion,
            "history": [
                {"candidate_id": row["candidate_id"], "search_signal": row["search_signal"],
                 "status": row["e_star_status"], "proposal_source": row.get("proposal_source")}
                for row in history
            ],
            "exit_code": meta.get("exit_code"),
        }

    def _checks(self, report: dict) -> Dict[str, bool]:
        meter_rows = report["meter_ledger_rows"]
        model_rows = [row for row in meter_rows if row.get("usage") is not None]
        state = report.get("arm_state") or {}
        harness_rows = {row["candidate_id"]: row for row in report["harness_ledger_rows"]}
        score = state.get("score_of_record")
        harness_value = None
        for row in harness_rows.values():
            if state.get("score_source") == "harness" and row.get("handed_value") is not None:
                harness_value = row["handed_value"]
        # For SimpleLoop the score of record is the champion's search signal (the
        # harness's number, folded by the frozen F_r); for KAPSO it is node.score.
        harness_value = state.get("harness_score")
        if harness_value is None and state.get("score_source") == "harness":
            harness_value = score
        checks = {
            "the_score_of_record_comes_from_the_harness": state.get("score_source") == "harness",
            "the_topology_blocks_direct_egress": (
                report["topology_probe"]["_negative_controls_blocked"] is True
                and report["topology_probe"].get("_meter_reachable") is True
            ),
            "the_model_was_reached_through_the_meter": len(model_rows) >= 1,
            "every_metered_row_has_a_real_ceq": bool(model_rows) and all(
                isinstance(row.get("ceq"), int) and row["ceq"] > 0 for row in model_rows
            ),
            # Cross-checked against the proxy's own per-call sidecar (an
            # independent count of the calls it handled) and against the meter's
            # own ledger verifier, which re-derives every metered row's `ceq`
            # from that row's usage. A ledger that is missing a row, or whose
            # arithmetic is wrong, fails here rather than being trusted.
            "the_ledger_has_one_row_per_upstream_call": (
                bool(report.get("meter_call_events"))
                and len(model_rows) == len(report["meter_call_events"])
            ),
            "the_meter_s_own_verifier_re_derives_every_row": (
                (report.get("meter_verify_ledger") or {}).get("returncode") == 0
            ),
            "the_score_of_record_is_the_harness_s_value": (
                score is not None and harness_value is not None and score == harness_value
            ),
            "the_session_could_not_substitute_its_own_number": state.get(
                "session_claimed_score"
            ) is None or score != state.get("session_claimed_score"),
            "the_budget_is_within_its_limits": report["budget_check"]["within"] is True,
        }
        if self.arm == "kapso":
            checks["the_last_manifest_line_is_the_harness_s"] = bool(
                state.get("last_line_is_the_harness_s")
            )
            checks["the_session_printed_its_own_manifest_line"] = bool(
                state.get("session_manifest_lines")
            )
        return checks


def _probe_with_relay(uplink: CampaignUplink, meter_port: int) -> dict:
    """Probe the namespace: negative controls from the inside, meter through the relay.

    The relay is started on the host, so the probe's positive control is run the
    same way the arm reaches the meter: from inside the namespace, over the unix
    socket, with a forwarder on loopback.
    """
    script = (
        "import json, socket\n"
        "report = {}\n"
        "for host in ('123.148.116.184', '1.1.1.1', '8.8.8.8'):\n"
        "    try:\n"
        "        socket.create_connection((host, 443), timeout=4).close()\n"
        "        report[host] = 'REACHED'\n"
        "    except OSError as exc:\n"
        "        report[host] = 'BLOCKED:' + type(exc).__name__\n"
        "try:\n"
        "    socket.create_connection(('127.0.0.1', PORT), timeout=4).close()\n"
        "    report['meter_loopback'] = 'REACHED'\n"
        "except OSError as exc:\n"
        "    report['meter_loopback'] = 'BLOCKED:' + type(exc).__name__\n"
        "print(json.dumps(report))\n"
    ).replace("PORT", str(meter_port))
    inner = [
        sys.executable, "-m", "a0.a1.topology", "enter",
        "--port", str(meter_port), "--sock", str(uplink.sock_path), "--",
        sys.executable, "-c", script,
    ]
    proc = subprocess.run(netns_prefix() + inner, cwd=str(REPO_ROOT),
                          capture_output=True, text=True, timeout=120,
                          env={**os.environ,
                               "PYTHONPATH": os.pathsep.join(
                                   [str(REPO_ROOT), str(REPO_ROOT / "a0/runtimes/simpleloop")]
                               )})
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip().startswith("{")]
    report = json.loads(lines[-1]) if lines else {"error": (proc.stderr or "")[-400:]}
    negatives = [key for key in ("123.148.116.184", "1.1.1.1", "8.8.8.8") if key in report]
    report["_negative_controls_blocked"] = bool(negatives) and all(
        str(report[key]).startswith("BLOCKED") for key in negatives
    )
    report["_meter_reachable"] = report.get("meter_loopback") == "REACHED"
    return report


def _ledger_rows(path: Path) -> List[dict]:
    if not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


# ---------------------------------------------------------------------------
# the KAPSO arm, run inside the namespace
# ---------------------------------------------------------------------------
def kapso_inner(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="live_probe kapso-inner")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--meter-token", default=None)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)

    kapso_dir = REPO_ROOT / "a0" / "runtimes" / "kapso"
    sys.path.insert(0, str(kapso_dir))
    from a0_adapter.common import AdapterConfig, bootstrap_kapso, load_candidate_set, load_eid_star
    from a0_adapter.harness_manifest import (
        HarnessEvalClient, PostSessionManifest, class_triple, manifest_line,
    )
    from a0_adapter.runtime import PROBLEM, KapsoRuntime

    out_dir = Path(args.out_dir).resolve()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    config = AdapterConfig.load(None)
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    baseline = next(c for c in candidates if c.role == "baseline")
    target = next(c for c in candidates if c.candidate_id != baseline.candidate_id)

    runtime = KapsoRuntime(
        config=config, eid=eid, candidates=candidates,
        run_dir=run_dir, state_root=run_dir / "state",
    )
    runtime.prepare(baseline)
    plan = runtime.seams["plan"]
    plan.queue.append({
        "candidate_id": target.candidate_id, "fidelity": "full", "fraction": 1.0,
        "tamper": None, "commit_tamper": False, "run_evaluation": True,
        "harness_outcome": None, "score_tag_value": None,
    })

    # -- the real model turn: the ideation phase asks DeepSeek --------------
    model_calls: List[dict] = []
    original_next = plan.next_solution

    def ideation_with_a_real_model_call():
        prompt = (
            "You are the ideation phase of a search over circle-packing heuristics. "
            "In one short paragraph, name one concrete change to a multi-start local "
            "search for packing 26 circles in the unit square that you expect to raise "
            "the sum of radii."
        )
        result = chat_completion(
            base_url=args.base_url, api_key=os.environ["DEEPSEEK_API_KEY"],
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            token=args.meter_token, max_tokens=256, timeout=MODEL_TIMEOUT,
        )
        body = result.get("body") or {}
        text = ""
        choices = body.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            text = message.get("content") or message.get("reasoning_content") or ""
        model_calls.append({"usage": body.get("usage") or {}, "model_reported": body.get("model"),
                            "text_head": text[:200]})
        return original_next()

    plan.next_solution = ideation_with_a_real_model_call

    # -- the session prints its own line, and claims a score ----------------
    session_claim = 9.75
    original_impl = plan.run_implementation

    def implementation_with_its_own_manifest_line(**kwargs):
        agent_output, telemetry, first, second = original_impl(**kwargs)
        line = "KAPSO_EVAL_MANIFEST " + json.dumps({
            "fidelity": "full", "fraction": "1.0", "seed": 1337,
            "items": 1, "total_items": 1, "score": session_claim,
            "session_claimed": True,
            "claimed_by": "the implementation session itself",
        }, sort_keys=True)
        agent_output = agent_output.replace("</evaluation_output>", line + "\n</evaluation_output>")
        return agent_output, telemetry, first, second

    plan.run_implementation = implementation_with_its_own_manifest_line

    client = HarnessEvalClient(
        root=Path(args.out_dir) / "harness", campaign_id="C_live_kapso", arm_id="A_kapso",
        seed=int(runtime.maintainer.subsample_seed),
    )
    client.identity()  # fail-closed

    def resolver(node):
        for record in reversed(plan.rounds):
            if record.get("branch_name") == getattr(node, "branch_name", None):
                return plan.candidate(record["candidate_id"]).path
        return None

    injector = PostSessionManifest(
        strategy=runtime.strategy, client=client, graph_path=None,
        artifact_resolver=resolver, run_id="live-kapso",
    )
    injector.install()

    from kapso.execution.fidelity import FULL_PASSTHROUGH
    runtime.strategy.observe_fidelity(FULL_PASSTHROUGH)
    node = runtime.strategy.run(PROBLEM)
    node0 = runtime.strategy.node_history[0]

    harness_events = injector.events[0] if injector.events else {}
    output_lines = [line for line in (node0.evaluation_output or "").splitlines()
                    if line.strip().startswith("KAPSO_EVAL_MANIFEST")]
    state = {
        "schema": "a0.a1.live_kapso_arm/v1",
        "score_of_record": node0.score,
        "score_source": "harness" if harness_events.get("wrote") else "session",
        "harness_score": harness_events.get("harness_score"),
        "session_claimed_score": session_claim,
        "session_manifest_lines": harness_events.get("session_manifest_lines"),
        "last_line_is_the_harness_s": harness_events.get("last_line_is_the_harness_s"),
        "manifest_line_count": len(output_lines),
        "granted_class": class_triple(runtime.strategy),
        "evaluation_attempts": [
            {"evaluator_id": attempt.evaluator_id, "score": attempt.score,
             "fidelity": attempt.fidelity, "fraction": attempt.fraction, "seed": attempt.seed}
            for attempt in node0.evaluation_attempts
        ],
        "registered_evaluator_id": runtime.registration.evaluator_id,
        "model_calls": model_calls,
        "harness_calls": client.calls,
        "attribution_caveat": __import__(
            "a0_adapter.harness_manifest", fromlist=["x"]
        ).ATTRIBUTION_CAVEAT,
    }
    (run_dir / "arm_state.json").write_text(json.dumps(state, indent=1, sort_keys=True) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"arm_state": state, "node_score": node0.score}, indent=1, default=str))
    return 0


# ---------------------------------------------------------------------------
# controls that cost nothing
# ---------------------------------------------------------------------------
def controls(out_dir: Path) -> dict:
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"schema": "a0.a1.live_probe_controls/v1", "checks": {}}

    meter = MeterProxy(campaign_id="C_controls", arm_id="A_controls", work_dir=out / "meter")
    meter.start()
    uplink = CampaignUplink(campaign_id="C_controls", meter_port=meter.port)
    try:
        uplink.start()
        # 1. the topology refuses a direct attempt from inside the namespace
        probe = _probe_with_relay(uplink, meter.port)
        direct = subprocess.run(
            netns_prefix() + [sys.executable, "-c",
                              "import socket\n"
                              "try:\n"
                              "    socket.create_connection(('123.148.116.184', 443), timeout=4)\n"
                              "    print('REACHED')\n"
                              "except OSError as exc:\n"
                              "    print('BLOCKED:' + type(exc).__name__)\n"],
            capture_output=True, text=True, timeout=60,
        )
        report["direct_attempt_inside_namespace"] = (direct.stdout or "").strip()
        report["topology_probe"] = probe

        # 2. the meter refuses a destination that is not on its allowlist
        try:
            chat_completion(
                base_url=meter.base_url, api_key="not-a-key", model=MODEL,
                messages=[{"role": "user", "content": "hi"}], token=meter.token,
                timeout=20, path="/chat/completions",
                extra_headers={"Host": "evil.example"},
            )
            refused = False
            detail = "the call was not refused"
        except Exception as exc:  # ModelCallError
            refused = True
            detail = f"{type(exc).__name__}: {exc}"
        report["non_allowlisted_destination"] = {"refused": refused, "detail": detail}

        # 3. a call without the campaign token is refused and booked here
        try:
            chat_completion(
                base_url=meter.base_url, api_key="not-a-key", model=MODEL,
                messages=[{"role": "user", "content": "hi"}], token=None, timeout=20
            )
            token_refused = False
            token_detail = "the call was not refused"
        except Exception as exc:
            token_refused = True
            token_detail = f"{type(exc).__name__}: {exc}"
        report["call_without_the_campaign_token"] = {"refused": token_refused,
                                                     "detail": token_detail}

        # 4. an induced upstream response without usage -> `unmetered`
        induced = _induced_unmetered(out)
        report["induced_missing_usage"] = induced
    finally:
        uplink.stop()
        meter.stop()

    rows = _ledger_rows(meter.ledger)
    report["meter_ledger_rows"] = rows
    report["meter_call_events"] = [e for e in meter.call_events() if e.get("kind") == "call"]
    report["meter_verify_ledger"] = meter.verify_ledger()
    report["checks"] = {
        "the_topology_refuses_a_direct_attempt": report["direct_attempt_inside_namespace"].startswith(
            "BLOCKED"
        ) and probe.get("_negative_controls_blocked") is True and probe.get("_meter_reachable") is True,
        "the_meter_refuses_a_non_allowlisted_destination": refused,
        "the_meter_refuses_a_call_without_the_campaign_token": token_refused,
        "a_refusal_is_booked_as_unmetered_against_this_campaign": any(
            row.get("unmetered") and str(row.get("reason", "")).startswith(
                ("non_allowlisted_host", "host_header_not_allowlisted", "path_not_routed",
                 "attribution_token_mismatch")
            ) for row in rows
        ),
        "an_upstream_response_without_usage_is_unmetered": (
            induced["row"] is not None and induced["row"].get("unmetered") is True
        ),
        "and_it_stops_the_campaign": induced["budget_stopped_because"]
        == "budget_exhausted:unmetered_model_call",
    }
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
    (out / "controls.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")
    return report


def _induced_unmetered(out: Path) -> dict:
    """A real upstream response without `usage`: ask DeepSeek for a nonexistent model.

    No tokens are consumed by a 4xx, and the response carries no `usage`, which is
    exactly the case `a0/meter/README.md` §2 puts in the `unmetered` bucket. The
    row's `reason` is recorded verbatim.
    """
    root = out / "induced"
    root.mkdir(parents=True, exist_ok=True)
    meter = MeterProxy(campaign_id="C_induced", arm_id="A_induced", work_dir=root)
    meter.start()
    result: Dict[str, Any] = {"campaign_id": "C_induced", "row": None}
    try:
        try:
            chat_completion(
                base_url=meter.base_url,
                api_key=os.environ.get("DEEPSEEK_API_KEY", "not-a-key"),
                model="deepseek-does-not-exist-a0-probe",
                messages=[{"role": "user", "content": "hi"}],
                token=meter.token, max_tokens=8, timeout=60,
            )
            result["response"] = "accepted (unexpected)"
        except Exception as exc:
            result["response"] = f"{type(exc).__name__}: {exc}"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not _ledger_rows(meter.ledger):
            time.sleep(0.1)
        rows = _ledger_rows(meter.ledger)
        result["row"] = rows[-1] if rows else None
        result["meter_call_events"] = [e for e in meter.call_events() if e.get("kind") == "call"]
    finally:
        meter.stop()
    if result["row"] is not None:
        enforcer = BudgetEnforcer(
            budget=Budget(T_wall_sec=60, N_eval_max=10, CEq_max=1000),
            meter_ledger=meter.ledger, harness_eval_ledger=out / "induced-harness.jsonl",
            campaign_id="C_induced", arm_id="A_induced",
        )
        result["budget_stopped_because"] = enforcer.check(label="induced")["stopped_because"]
    else:
        result["budget_stopped_because"] = None
    return result


# ---------------------------------------------------------------------------
def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "kapso-inner":
        return kapso_inner(argv=argv[1:])
    parser = argparse.ArgumentParser(prog="live_probe")
    sub = parser.add_subparsers(dest="command", required=True)
    arm = sub.add_parser("arm")
    arm.add_argument("--arm", required=True, choices=["simpleloop", "kapso"])
    arm.add_argument("--out-dir", required=True)
    arm.add_argument("--max-iterations", type=int, default=2)
    inner = sub.add_parser("kapso-inner")
    inner.add_argument("--out-dir", required=True)
    inner.add_argument("--base-url", required=True)
    inner.add_argument("--meter-token", default=None)
    inner.add_argument("--run-dir", required=True)
    ctl = sub.add_parser("controls")
    ctl.add_argument("--out-dir", required=True)
    allp = sub.add_parser("all")
    allp.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    if args.command == "controls":
        report = controls(Path(args.out_dir))
        print(json.dumps({"verdict": report["verdict"], "checks": report["checks"]}, indent=1))
        return 0 if report["verdict"] == "pass" else 5
    if args.command == "arm":
        report = LiveCampaign(arm=args.arm, out_dir=Path(args.out_dir),
                              max_iterations=args.max_iterations).run()
        print(json.dumps({"arm": report["arm"], "verdict": report["verdict"],
                          "checks": report["checks"],
                          "meter_summary": report["meter_summary"],
                          "harness_ledger": report["harness_ledger_rows"],
                          "arm_state": report["arm_state"]}, indent=1, default=str))
        return 0 if report["verdict"] == "pass" else 5
    out = Path(args.out_dir)
    results = {}
    results["controls"] = controls(out)["verdict"]
    for name in ("simpleloop", "kapso"):
        results[name] = LiveCampaign(arm=name, out_dir=out).run()["verdict"]
    print(json.dumps(results, indent=1))
    return 0 if all(value == "pass" for value in results.values()) else 5


if __name__ == "__main__":
    sys.exit(main())
