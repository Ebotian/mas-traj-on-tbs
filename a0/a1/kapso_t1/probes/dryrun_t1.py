#!/usr/bin/env python3
"""T1 dry run: the tree loads, the class triple is derived, the harness's line is the score.

Model-free. The adapter's documented seams drive ideation and implementation
(`a0/runtimes/kapso/a0_adapter/seams.py`), so no model call is made and no spend is
incurred; the *harness* does run the frozen T1 `E*` (`a0/tasks/maxcut/e_star.py`) —
that is the harness's own job, and running it here is what makes the scores real.

    a0/runtimes/kapso/.venv/bin/python a0/a1/kapso_t1/probes/dryrun_t1.py \
        --out-dir /tmp/a1t1/dryrun

The three things the assignment asks for, each as checks over recorded state:

(a) **the tree loads** — `build_tree.py check` passes, KAPSO's own
    `EvaluationMaintainer.setup` calibrated the registered command (the T1 stub) inside
    the workspace, and KAPSO's own `registration.evaluator_id` equals the fingerprint
    this workstream records for `tree/` — i.e. `EID_r` is T1's tree, computed by KAPSO;
(b) **the class triple is derived from the runtime, not hardcoded** — under a
    `fast/0.15` grant, `class_triple(strategy)` reads `fast/0.15` from the strategy and
    a line built from it is adopted, while a hardcoded `full/1.0/1337` line is
    discarded (`None`, silently, `registered_evaluation.py:87-99`); the stub echoes the
    triple it is invoked with, so the class triple exists in the tree as well as in the
    harness;
(c) **the harness manifest line lands as the score of record and selection follows it**
    — the session prints its own `KAPSO_EVAL_MANIFEST` line and the harness's line is
    appended after the session, so the recorded score is the harness's; with an
    override that inverts the true ranking the parent selection follows the harness's
    number, not E*'s.

Plus the T1-specific controls that make the tree *T1's* rather than a stub: the 24 dev
instances and no hold-out bytes in the workspace, the dev instances inside KAPSO's
registered data manifest, a candidate that rewrites one getting no score at all, and a
candidate that doctors the registered tree getting no score at all.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
KAPSO_DIR = REPO_ROOT / "a0" / "runtimes" / "kapso"
for path in (str(ROOT), str(KAPSO_DIR), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import build_tree  # noqa: E402
import runtime_t1  # noqa: E402
import task as t1_task  # noqa: E402
import tree as t1_tree  # noqa: E402
import t1_binding  # noqa: E402
from a0_adapter.common import sha256_file  # noqa: E402

E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"
ADAPTER_PYTHON = KAPSO_DIR / ".venv" / "bin" / "python"

#: Who gets what from the harness: `E*` measures both candidates, and the harness
#: hands node 0 a small number and node 1 a huge one, i.e. the *inverse* of the true
#: ranking (c01 is the high-scoring candidate, c02 the frozen low baseline). 9999 is
#: a value `E*` cannot produce on a 128-node graph (`|E| <= 713`), so "the runtime
#: consumes, it does not measure" is observable rather than argued.
ROUNDS = [
    {"candidate_id": "c01_ok_high_pc", "run_evaluation": True, "tamper": None},
    {"candidate_id": "c02_ok_low_baseline", "run_evaluation": True, "tamper": None},
    {"candidate_id": "c01_ok_high_pc", "run_evaluation": True, "tamper": None},
    {"candidate_id": "c03_ok_zero_all_one_side", "run_evaluation": True,
     "tamper": "A0-KAPSO-T1-TAMPER: the candidate edited the registered evaluator"},
]
OVERRIDE = {"c01_ok_high_pc": 3, "c02_ok_low_baseline": 9999}
SESSION_CLAIM = 777777.0        # what the session says its own score is
GRAPH_ID = "G_dev_0001"


class HarnessService:
    """The harness-owned evaluation service, as its own process over the ABI directory."""

    def __init__(self, root: Path, campaign_id: str, arm_id: str, run_id: str,
                 override: Dict[str, int], e_star_python: Path, timeout_s: float = 10.0):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root.parent / f"{self.root.name}.stop"
        override_path = self.root.parent / "override.json"
        override_path.write_text(json.dumps(override, sort_keys=True) + "\n", encoding="utf-8")
        self.command = [
            str(ADAPTER_PYTHON), str(E_SERVICE), "serve",
            "--root", str(self.root),
            "--evaluator", "maxcut",
            "--e-star", str(REPO_ROOT / "a0" / "tasks" / "maxcut" / "e_star.py"),
            "--python", str(e_star_python),
            "--campaign-id", campaign_id,
            "--arm-id", arm_id,
            "--harness-run-id", run_id,
            "--seed", "1337",
            "--timeout-s", str(timeout_s),
            "--override", str(override_path),
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
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def ledger(self) -> List[dict]:
        path = self.root / "ledger.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]


def session_that_prints_its_own_line(plan, claim: float) -> List[dict]:
    """Make the *session* print a manifest line of its own, claiming `claim`.

    The session is not authenticated: `HARNESS-OWNED-EVAL.md` §1 says a candidate
    session can print the same line. This is the ordering test's counterpart.
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
        reason="T1 dry run: a deliberately non-default grant",
    )


def run_stub(stub: Path, candidate: Path, fidelity: str, fraction: float, seed: int,
             python: Path) -> dict:
    proc = subprocess.run(
        [str(python), str(stub), "--fidelity", fidelity,
         "--fraction", repr(float(fraction)), "--seed", str(seed),
         "--candidate", str(candidate)],
        capture_output=True, text=True, timeout=120,
    )
    manifest = None
    for line in proc.stdout.splitlines():
        if line.strip().startswith("KAPSO_EVAL_MANIFEST"):
            manifest = json.loads(line.strip()[len("KAPSO_EVAL_MANIFEST"):])
    return {
        "cmd": [str(python), str(stub), "--fidelity", fidelity, "--fraction",
                repr(float(fraction)), "--seed", str(seed), "--candidate", str(candidate)],
        "exit_code": proc.returncode,
        "manifest": manifest,
        "stdout_lines": len(proc.stdout.splitlines()),
        "stderr_tail": proc.stderr.strip()[-400:],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.kapso_t1.probes.dryrun_t1")
    parser.add_argument("--out-dir", default="/tmp/a1t1/dryrun")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    report: Dict[str, Any] = {
        "schema": "a0.a1.kapso_t1.dryrun/v1",
        "task_id": t1_binding.TASK_ID,
        "graph_id": GRAPH_ID,
        "override": OVERRIDE,
        "session_claim": SESSION_CLAIM,
        "model_calls": 0,
        "checks": {},
    }

    # -- 1. the tree, as committed -----------------------------------------
    report["tree_check"] = build_tree.check()

    config = t1_binding.load_config()
    eid = t1_binding.load_eid(config)
    candidates = t1_binding.load_candidates(config)
    report["eid_star"] = eid.eid_star
    report["binding"] = t1_binding.binding_record(config, eid, candidates)
    report["eid_contract_verification"] = t1_binding.verify_eid(config, eid)
    report["tree_record"] = json.loads(
        (ROOT / "tree_record.json").read_text(encoding="utf-8")
    )

    dev_graphs = runtime_t1.graph_paths(config, "dev")
    graph = Path(next(item for item in dev_graphs if item["graph_id"] == GRAPH_ID)["path"])
    report["graph"] = {"graph_id": GRAPH_ID, "path": str(graph),
                       "sha256": sha256_file(graph)}
    locator_on_disk = json.loads((ROOT / "tree" / t1_tree.LOCATOR_NAME).read_text(
        encoding="utf-8"))
    report["declaration_agreement"] = {
        "candidate_abi": {
            "task_py": t1_task.CANDIDATE_ABI,
            "locator": locator_on_disk["candidate_abi"],
            "identical": t1_task.CANDIDATE_ABI == locator_on_disk["candidate_abi"],
        },
        "score_semantics": {
            "task_py": t1_task.SCORE_SEMANTICS,
            "locator": locator_on_disk["score_semantics"],
            "identical": t1_task.SCORE_SEMANTICS == locator_on_disk["score_semantics"],
        },
        "suite_manifest": {
            "locator_sha256": locator_on_disk["graph_sets"]["suite_manifest"]["sha256"],
            "eid_star_declared_prefixes": {
                entry["name"]: entry.get("manifest_sha256_prefix")
                for entry in (
                    (eid.components["DataManifest"].get("declared") or {}).get("entries", [])
                )
                if entry.get("manifest_sha256_prefix")
            },
            "matches_the_eid_declared_prefix": locator_on_disk["graph_sets"][
                "suite_manifest"
            ]["sha256"].startswith("47324fcc"),
        },
    }

    service = HarnessService(out_dir / "harness", "C_t1_dryrun", "A_kapso", "t1-dryrun-1",
                             OVERRIDE, Path(config.e_star_python))
    service.start()
    try:
        runtime = runtime_t1.build_runtime(run_dir=out_dir / "campaign")
        report["task_binding"] = runtime_t1.prepare(runtime)
        report["setup_log"] = runtime.setup_log
        report["config_evidence"] = runtime.config_evidence
        report["registration"] = {
            "evaluator_id": runtime.registration.evaluator_id,
            "version": runtime.registration.version,
            "provenance": runtime.registration.provenance,
            "command_full": runtime.registration.command_full,
            "command_calibration": runtime.registration.command_calibration,
            "tree_fingerprint": runtime.registration.tree_fingerprint,
            "tree_files": sorted(runtime.registration.registered_tree_manifest),
            "calibration_fraction": runtime.registration.calibration_manifest["fast_fraction"],
            "calibration_total_items": runtime.registration.calibration_manifest["total_items"],
            "setup_agent_seam": runtime.registration.setup_agent_seam,
        }
        report["registered_tree_on_disk"] = {
            "tree_source": str(runtime.tree_source),
            "files": sorted(p.name for p in Path(runtime.tree_source).iterdir()
                            if p.is_file()),
            "stub_is_the_committed_source": (
                (Path(runtime.tree_source) / t1_tree.WRAPPER_NAME).read_bytes()
                == t1_tree.WRAPPER_SOURCE.read_bytes()
            ),
        }
        report["workspace"] = {
            "dev_materialization": {
                key: value for key, value in runtime.dev_materialization.items()
                if key != "members"
            },
            "dev_members_sha256_checked": len(runtime.dev_materialization.get("members", [])),
            "holdout_bytes_in_workspace": runtime.holdout_bytes_in_workspace,
            "protected_data_manifest_entries": sorted(
                key for key in (runtime.strategy.registered_data_manifest or {})
                if key.startswith("kapso_datasets/maxcut/dev")
            ),
        }

        # -- 2. the class triple, from the runtime -------------------------
        class_probe: Dict[str, Any] = {}
        stub = Path(runtime.tree_source) / t1_tree.WRAPPER_NAME
        c01 = next(c for c in candidates if c.candidate_id == "c01_ok_high_pc")
        from kapso.execution.search_strategies.generic.registered_evaluation import (
            manifest_of_record,
        )
        from a0_adapter.harness_manifest import class_triple, manifest_line

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
                "stub_echoes_the_grant": run_stub(
                    stub, c01.path, grant.eval_fidelity, grant.eval_fraction,
                    runtime.strategy.registered_subsample_seed, Path(config.e_star_python),
                ),
            }
        runtime.strategy.observe_fidelity(full_grant())
        report["class_probe"] = class_probe

        # -- 3. the harness's line, after the session ----------------------
        plan = runtime.seams["plan"]
        for entry in ROUNDS:
            plan.push(entry["candidate_id"], run_evaluation=entry["run_evaluation"],
                      tamper=entry["tamper"], commit_tamper=bool(entry["tamper"]))
        report["session_claims"] = session_that_prints_its_own_line(plan, SESSION_CLAIM)

        client = runtime_t1.harness_client(
            harness_root=service.root, campaign_id="C_t1_dryrun", arm_id="A_kapso",
            seed=int(runtime.maintainer.subsample_seed),
            label_resolver=runtime_t1.plan_label_resolver(runtime),
        )
        client.identity()   # fail-closed: no harness identity, no run
        report["harness_client"] = {
            "class": "a0/a1/kapso_t1/runtime_t1.py::T1HarnessEvalClient",
            "why": (
                "the adapter's injector labels its request node<N>; the harness's ledger and "
                "the --override map are keyed by candidate id, so the probe relabels on its "
                "side rather than editing another workstream's adapter"
            ),
        }
        injector = runtime_t1.post_session_injector(
            runtime=runtime, client=client, graph_path=graph,
            resolver=runtime_t1.plan_resolver(runtime), run_id="t1-dryrun-1",
        )
        injector.install()

        started = time.monotonic()
        for _ in ROUNDS:
            runtime.strategy.run(t1_task.T1_PROBLEM)
        report["elapsed_sec"] = round(time.monotonic() - started, 3)

        nodes = list(runtime.strategy.node_history)
        report["nodes"] = [
            {
                "node_id": node.node_id,
                "branch_name": node.branch_name,
                "parent_node_id": node.parent_node_id,
                "score": node.score,
                "evaluation_valid": node.evaluation_valid,
                "evaluation_integrity_error": node.evaluation_integrity_error,
                "manifest_lines": [
                    json.loads(line.strip()[len("KAPSO_EVAL_MANIFEST"):])
                    for line in (node.evaluation_output or "").splitlines()
                    if line.strip().startswith("KAPSO_EVAL_MANIFEST")
                ],
                "evaluation_attempts": [
                    {"evaluator_id": attempt.evaluator_id, "fidelity": attempt.fidelity,
                     "fraction": attempt.fraction, "seed": attempt.seed,
                     "score": attempt.score}
                    for attempt in node.evaluation_attempts
                ],
            }
            for node in nodes
        ]
        report["injector"] = injector.as_dict()
        report["harness_ledger"] = service.ledger()
        report["harness_ledger_rows_by_node"] = [
            {"node_id": index, "seq": row["seq"], "candidate_id": row["candidate_id"],
             "candidate_source_sha256": row["candidate_source_sha256"],
             "true_value": row["true_value"], "handed_value": row["handed_value"],
             "override_applied": row["override_applied"], "status": row["status"],
             "measurement_oid": row["measurement_oid"]}
            for index, row in enumerate(service.ledger())
        ]
        report["relabelled_requests"] = list(client.relabelled)
        report["harness_calls"] = client.calls
        report["best"] = _best_record(runtime)
        report["selection"] = _selection_record(runtime)
        report["deliverable_score"] = runtime.strategy.get_deliverable_score()

        # the stub alone carries no score of record; the same bytes plus the
        # harness's line do
        stub_run = run_stub(stub, c01.path, "full", 1.0,
                            int(runtime.maintainer.subsample_seed), Path(config.e_star_python))
        report["stub_standalone"] = stub_run
        stub_only = manifest_of_record(
            SimpleNamespace(evaluation_output=_line_of(stub_run)),
            registered_evaluation_command=runtime.strategy.registered_evaluation_command,
            fidelity_decision=full_grant(),
            registered_subsample_seed=runtime.strategy.registered_subsample_seed,
        )
        report["stub_standalone_score_of_record"] = stub_only
        report["stub_plus_harness_score_of_record"] = manifest_of_record(
            SimpleNamespace(evaluation_output=_line_of(stub_run) + _harness_line(report)),
            registered_evaluation_command=runtime.strategy.registered_evaluation_command,
            fidelity_decision=full_grant(),
            registered_subsample_seed=runtime.strategy.registered_subsample_seed,
        )

        # -- 4. T1-specific controls ---------------------------------------
        report["controls"] = {}
        report["controls"]["e_star_drift"] = _drift_control(out_dir, runtime, config, c01)
        report["controls"]["frame_run"] = _frame_run_control(runtime, nodes[0])
        report["controls"]["protected_dev_graph_rewrite"] = _protected_data_control(
            runtime, nodes[2], runtime.dev_materialization["members"][0]["file"]
        )
    finally:
        service.stop()
        report["harness_ledger"] = service.ledger()

    checks = report["checks"]
    nodes = report["nodes"]
    node0, node1, node2, node3 = nodes[0], nodes[1], nodes[2], nodes[3]
    by_node = {row["node_id"]: row for row in report["harness_ledger_rows_by_node"]}
    true_by_candidate = {row["candidate_id"]: row["true_value"]
                         for row in report["harness_ledger"]}
    handed_by_candidate = {row["candidate_id"]: row["handed_value"]
                           for row in report["harness_ledger"]}

    checks["the_tree_check_passes"] = report["tree_check"]["pass"] is True
    checks["kapsos_own_registration_equals_the_t1_tree_fingerprint"] = (
        report["registration"]["evaluator_id"]
        == report["tree_record"]["manifest_fingerprint"]
    )
    checks["the_registered_command_is_kapsos_own_composition"] = (
        report["registration"]["command_full"]
        == "python kapso_evaluation/kapso_eval.py --fidelity full --fraction 1.0 --seed 1337"
    )
    checks["the_registered_tree_in_the_run_is_the_t1_stub"] = (
        report["registered_tree_on_disk"]["stub_is_the_committed_source"] is True
        and report["task_binding"]["tree_source_is_the_t1_stub"] is True
        and report["task_binding"]["eid_r_matches_the_t1_tree_record"] is True
    )
    checks["the_maintainer_calibrated_the_t1_stub"] = (
        report["registration"]["calibration_total_items"] == 1
        and report["registration"]["provenance"] == "provided"
    )
    checks["the_class_triple_is_derived_from_the_runtime"] = (
        report["class_probe"]["fast_grant"]["derived_triple"]["fidelity"] == "fast"
        and abs(report["class_probe"]["fast_grant"]["derived_triple"]["fraction"] - 0.15) < 1e-12
        and report["class_probe"]["fast_grant"]["derived_line_adopted"] is True
    )
    checks["a_hardcoded_triple_is_discarded_under_a_foreign_grant"] = (
        report["class_probe"]["fast_grant"]["hardcoded_full_1_0_1337_adopted"] is False
        and report["class_probe"]["full_passthrough"]["hardcoded_full_1_0_1337_adopted"] is True
    )
    checks["the_stub_echoes_the_grant_it_is_invoked_with"] = all(
        item["stub_echoes_the_grant"]["manifest"]["fidelity"] == item["grant"]["fidelity"]
        and abs(item["stub_echoes_the_grant"]["manifest"]["fraction"] - item["grant"]["fraction"]) < 1e-12
        and item["stub_echoes_the_grant"]["exit_code"] == 0
        for item in report["class_probe"].values()
    )
    checks["the_session_printed_its_own_manifest_line"] = bool(
        report["session_claims"]
        and report["session_claims"][0]["claimed_score"] == SESSION_CLAIM
        and all(claim["claimed_score"] == SESSION_CLAIM for claim in report["session_claims"])
    )
    checks["the_harness_ledger_is_keyed_by_the_candidate"] = all(
        by_node[index]["candidate_id"] == ROUNDS[index]["candidate_id"]
        for index in range(len(ROUNDS))
    )
    checks["the_score_of_record_is_the_harness_s"] = all(
        node["score"] == by_node[node["node_id"]]["handed_value"]
        for node in (node0, node1, node2)
    ) and SESSION_CLAIM not in (node0["score"], node1["score"], node2["score"])
    checks["the_score_of_record_is_not_what_e_star_measured"] = (
        by_node[1]["handed_value"] == 9999
        and by_node[0]["handed_value"] == 3
        and by_node[1]["true_value"] is not None
        and by_node[1]["true_value"] < by_node[0]["true_value"]
    )
    checks["the_last_manifest_line_is_the_harness_s"] = all(
        event.get("last_line_is_the_harness_s") is True
        for event in report["injector"]["events"]
        if event.get("status") == "written"
    )
    checks["selection_follows_the_harnesss_number_not_the_true_ranking"] = (
        node1["parent_node_id"] == node0["node_id"]
        and node2["parent_node_id"] == node1["node_id"]
        and report["best"]["node_id"] == node1["node_id"]
        and report["deliverable_score"] == 9999
    )
    checks["the_stub_alone_carries_no_score_of_record"] = (
        report["stub_standalone_score_of_record"] is None
        and report["stub_standalone"]["manifest"].get("measurement") == "none"
        and "score" not in report["stub_standalone"]["manifest"]
    )
    checks["with_the_harness_line_the_score_of_record_is_the_harness_s"] = (
        report["stub_plus_harness_score_of_record"] is not None
        and abs(report["stub_plus_harness_score_of_record"]["score"]
                - by_node[0]["handed_value"]) < 1e-12
    )
    checks["kapsos_ledger_attributes_it_to_the_registered_evaluator"] = all(
        node["evaluation_attempts"]
        and node["evaluation_attempts"][0]["evaluator_id"]
        == report["registration"]["evaluator_id"]
        for node in (node0, node1, node2)
    )
    checks["the_candidate_abi_declaration_is_one_declaration"] = (
        report["declaration_agreement"]["candidate_abi"]["identical"] is True
    )
    checks["the_score_semantics_declaration_is_one_declaration"] = (
        report["declaration_agreement"]["score_semantics"]["identical"] is True
    )
    checks["the_trees_suite_manifest_is_the_one_eid_star_names"] = (
        report["declaration_agreement"]["suite_manifest"][
            "matches_the_eid_declared_prefix"
        ] is True
    )
    checks["the_24_dev_instances_are_in_the_workspace_and_sha_checked"] = (
        report["workspace"]["dev_materialization"]["count"] == 24
        and report["workspace"]["dev_members_sha256_checked"] == 24
    )
    checks["no_holdout_bytes_are_in_the_workspace"] = (
        report["workspace"]["holdout_bytes_in_workspace"] == []
    )
    checks["the_dev_instances_are_kapsos_registered_protected_data"] = (
        len(report["workspace"]["protected_data_manifest_entries"]) == 25
    )
    checks["a_rewritten_dev_graph_scores_nothing"] = (
        report["controls"]["protected_dev_graph_rewrite"]["valid_after"] is False
        and report["controls"]["protected_dev_graph_rewrite"]["score_after"] is None
        and "kapso_datasets/maxcut/dev" in
        report["controls"]["protected_dev_graph_rewrite"]["integrity_error"]
    )
    checks["a_doctored_registered_tree_scores_nothing"] = (
        node3["evaluation_valid"] is False and node3["score"] is None
        and "kapso_eval.py" in (node3["evaluation_integrity_error"] or "")
    )
    checks["a_drifted_e_star_is_refused_by_the_tree"] = (
        report["controls"]["e_star_drift"]["exit_code"] == 3
        and report["controls"]["e_star_drift"]["manifest"] is None
        and "drifted" in report["controls"]["e_star_drift"]["stderr_tail"]
    )
    report["verdict"] = "pass" if all(checks.values()) else "fail"
    (out_dir / "dryrun_t1.json").write_text(
        json.dumps(report, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "verdict": report["verdict"],
        "checks": checks,
        "failed": [name for name, value in checks.items() if not value],
        "nodes": [{"node_id": n["node_id"], "score": n["score"],
                   "valid": n["evaluation_valid"]} for n in nodes],
        "best": report["best"],
        "harness_ledger": [
            {"candidate_id": row["candidate_id"], "true_value": row["true_value"],
             "handed_value": row["handed_value"], "override_applied": row["override_applied"]}
            for row in report["harness_ledger"]
        ],
        "out": str(out_dir / "dryrun_t1.json"),
    }, indent=1, default=str))
    return 0 if report["verdict"] == "pass" else 5


# ---------------------------------------------------------------------------
# small helpers for the controls and the selection record
# ---------------------------------------------------------------------------
def _line_of(stub_run: dict) -> str:
    if stub_run["manifest"] is None:
        return ""
    return "KAPSO_EVAL_MANIFEST " + json.dumps(stub_run["manifest"], sort_keys=True) + "\n"


def _harness_line(report: dict) -> str:
    for node in report["nodes"]:
        for payload in node["manifest_lines"]:
            if payload.get("harness_supplied"):
                return "KAPSO_EVAL_MANIFEST " + json.dumps(payload, sort_keys=True) + "\n"
    return ""


def _best_record(runtime) -> dict:
    best = runtime.strategy.get_best_experiment()
    if best is None:
        return {"node_id": None, "score": None}
    return {"node_id": best.node_id, "branch_name": best.branch_name, "score": best.score}


def _selection_record(runtime) -> dict:
    nodes = list(runtime.strategy.node_history)
    return {
        "parent_of_each_node": {node.node_id: node.parent_node_id for node in nodes},
        "best_by_score": max((node.score for node in nodes if node.score is not None),
                             default=None),
        "get_best_experiment": _best_record(runtime),
        "get_deliverable_score": runtime.strategy.get_deliverable_score(),
        "note": (
            "with 9999 handed to the true-low candidate and 3 to the true-high one, a "
            "parent chain 0 -> 1 -> 1 is the harness's ranking, not E*'s"
        ),
    }


def _drift_control(out_dir: Path, runtime, config, candidate) -> dict:
    """The same stub, pointed at an E* whose bytes differ from EID*'s records."""
    scratch = out_dir / "controls" / "e_star_drift"
    drift_tree = scratch / "tree"
    drift_e = scratch / "e_star"
    shutil.copytree(runtime.tree_source, drift_tree)
    drift_e.mkdir(parents=True, exist_ok=True)
    for name in ("e_star.py", "e_star_child.py"):
        shutil.copyfile(Path(config.e_star_dir) / name, drift_e / name)
    mutated = drift_e / "e_star.py"
    mutated.write_text(mutated.read_text(encoding="utf-8") + "\n# drift: one byte more\n",
                       encoding="utf-8")
    locator_path = drift_tree / t1_tree.LOCATOR_NAME
    locator = json.loads(locator_path.read_text(encoding="utf-8"))
    locator["e_star"]["dir"] = str(drift_e)
    locator_path.write_text(json.dumps(locator, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    result = run_stub(drift_tree / t1_tree.WRAPPER_NAME, candidate.path, "full", 1.0, 1337,
                      Path(config.e_star_python))
    result["why"] = (
        "a0_locator.json still records EID*'s digests while e_star.py's bytes changed: the "
        "stub must refuse, because otherwise EID_r would name a tree that can run a "
        "different evaluator"
    )
    return result


def _frame_run_control(runtime, node) -> dict:
    """Measure what KAPSO's frame run does with a score-less registered line.

    A frame run is `execute_registered_evaluation` (`registered_evaluation.py:162-285`),
    reached from exactly two places: a VALIDATE fidelity grant (`_run_validate`) and an
    evaluator transition (`run_bridge_evaluation`). With `budget.fidelity.mode = off` the
    grant is always FULL_PASSTHROUGH, and `max_change_requests = 0` means no accepted
    change request can move the head — so in this configuration the frame run is
    unreachable. It is executed here anyway, so the behaviour is *measured* rather than
    assumed: the stub's line has no `score` key, and the frame run's `float(manifest["score"])`
    is what would raise.
    """
    record: Dict[str, Any] = {
        "reachable_in_this_configuration": False,
        "because": (
            "budget.fidelity.mode=off grants FULL_PASSTHROUGH only (no VALIDATE), and "
            "max_change_requests=0 admits no change request, so no evaluator transition "
            "and no bridge evaluation can occur"
        ),
    }
    try:
        value = runtime.frame_eval(node, fidelity="full", fraction=1.0,
                                   deadline_seconds=30.0)
        record["outcome"] = {"returned": value, "raised": None}
    except Exception as exc:  # noqa: BLE001 - the point is to record what happens
        record["outcome"] = {"returned": None, "raised": f"{type(exc).__name__}: {exc}"}
    record["note"] = (
        "recorded as measured, not as desired: a bridge or VALIDATE grant with this tree "
        "would raise at float(manifest['score']). Closing it means giving the stub a "
        "declared scalar for the frame-run path, which the harness-owned design does not "
        "need and this workstream did not do (see DEVIATIONS.md D-KT1-6)"
    )
    return record


def _protected_data_control(runtime, node, filename: str) -> dict:
    """Rewrite one protected dev graph on a candidate's branch, then re-run the gate."""
    repo = runtime.strategy.workspace.repo
    branch = node.branch_name
    record: Dict[str, Any] = {"branch_name": branch, "file": filename,
                              "valid_before": node.evaluation_valid,
                              "score_before": node.score}
    runtime.strategy.workspace.switch_branch(branch)
    target = Path(runtime.workspace_dir) / "kapso_datasets/maxcut/dev" / filename
    original = target.read_text(encoding="utf-8")
    document = json.loads(original)
    document["edges"] = document["edges"] + [[0, 1]]
    document["notes"] = "control: the candidate rewrote a protected input"
    target.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    repo.git.add(["-f", f"kapso_datasets/maxcut/dev/{filename}"])
    repo.git.commit("-m", "control: candidate rewrote a protected dev graph")
    runtime.strategy.workspace.switch_branch("main")
    valid = runtime.strategy.enforce_evaluation_integrity(node)
    record["valid_after"] = valid
    record["evaluation_valid_after"] = node.evaluation_valid
    record["score_after"] = node.score
    record["integrity_error"] = node.evaluation_integrity_error
    record["note"] = (
        "the dev instances are KAPSO's registered protected data "
        "(evaluation_maintainer.protected_data_paths), so a candidate scored on a "
        "rewritten graph gets no score at all — the graph it was scored on would not be T1"
    )
    return record


if __name__ == "__main__":
    sys.exit(main())
