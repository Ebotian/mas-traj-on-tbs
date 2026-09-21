"""Two-round KAPSO bridge: is a real campaign's next parent derived from E*_t?

The separate evidence base already shows (a) the selection kernel consumes an
externally produced score correctly when a score enters it (A0.2, seam-driven)
and (b) one real codex session can carry ``LLM -> candidate -> E*`` end to end
(``runs/e2e-real``).  Neither connects the two: no real ``E*_t -> parent_{t+1}``
transition inside an actual campaign has been observed.  This script buys that
transition in two rounds.

Round 1 prepares a campaign (workspace, KAPSO's own ``EvaluationMaintainer``
registration over the registered tree built from ``EID*``, baseline on ``main``)
and runs ONE iteration of the runtime's own ``GenericSearch.run``.  The ideation
phase is seamed and hands the implementation session a frozen ``C*`` candidate to
install; the implementation phase is the runtime's real ``run_implementation``,
so a genuine codex session clones the parent branch, writes ``solution.py``, runs
the registered evaluation in its own session folder, and commits/pushes.

Round 2 resumes that campaign **in a fresh process** (the orchestrator's own
resume shape: ``GenericSearch(import_from_checkpoint=True)`` + ``load_state`` +
adopt the registered head, no ``EvaluationMaintainer.setup``) and runs a second
iteration.  Round 2's parent is whatever KAPSO's own ``_select_parent`` returns
over the restored ``node_history``.

Every claim is derived from KAPSO's own recorded state — the restored node
history, the recorded parent branch of each node, the git ancestry of the
branches the sessions pushed, and the runtime's own selectors re-executed on
that state.  The model's own claims are never used as evidence.

A fresh process per round is what makes the per-round wall-clock cap a hard one:
each round is launched as its own background task under ``timeout`` (1500 s in
the real run; the bridge prints its cap in the round report, and ``--cap``
records the value the launching shell enforced).

Usage::

    .venv/bin/python runs/bridge-2round/bridge.py round1 \
        --run-dir runs/bridge-2round/real --cap 1500
    .venv/bin/python runs/bridge-2round/bridge.py round2 \
        --run-dir runs/bridge-2round/real --cap 1500

``--seam-implementation`` swaps the implementation phase for the adapter's own
in-process seam as well, which is how the dry run exercises exactly the same
round/report/resume/verify code paths without spending a model call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
KAPSO_ADAPTER_DIR = HERE.parent.parent
sys.path.insert(0, str(KAPSO_ADAPTER_DIR))

from a0_adapter.channels import run_reference_e_star  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig,
    bootstrap_kapso,
    check_candidate_integrity,
    load_candidate_set,
    load_eid_star,
    write_json,
)
from a0_adapter.runtime import (  # noqa: E402
    GOAL,
    PROBLEM,
    KapsoRuntime,
    _tree_fingerprint,
)
from a0_adapter.seams import SeamFeedbackJudge, install_seams  # noqa: E402
from a0_adapter.registered_tree import install_registered_tree  # noqa: E402

# What the ideation seam hands the implementation session.  Round 1: the frozen
# candidate that is a decidable improvement over the baseline on `main`.
# Round 2: the frozen candidate that is a decidable improvement (1.0000000000021e-4,
# the documented near-tied pair of C*) over round 1's winner.
ROUNDS: Dict[int, Dict[str, str]] = {
    1: {
        "candidate_id": "c04_near_tie",
        "expected_score": "2.451820520843313",
        "role": "round 1: a decidable improvement over the baseline on main",
    },
    2: {
        "candidate_id": "c01_good_hex",
        "expected_score": "2.4519205208433132",
        "role": "round 2: a decidable improvement over round 1's winner",
    },
}


# --------------------------------------------------------------------------- #
# campaign construction
# --------------------------------------------------------------------------- #

def _install_entry(candidate, expected: float, *,
                   run_evaluation: bool) -> Dict[str, Any]:
    code = (candidate.path / "solution.py").read_text("utf-8")
    return {
        "candidate_id": candidate.candidate_id,
        "fidelity": "full",
        "fraction": 1.0,
        "tamper": None,
        "commit_tamper": False,
        # Real lane: the session runs the registered command itself, so the
        # seam must not.  Dry run: the implementation phase is seamed too, so
        # the seam runs exactly the command the real session would run.
        "run_evaluation": run_evaluation,
        "solution_text": (
            "Do exactly two things, immediately, without investigating anything:\n"
            "1. Overwrite solution.py with EXACTLY the code below, byte for byte.\n"
            "2. Run `python kapso_evaluation/kapso_eval.py --fidelity full "
            "--fraction 1.0 --seed 1337` in the foreground and copy its complete "
            "stdout into your <evaluation_output> tag, with the score from its "
            "KAPSO_EVAL_MANIFEST line in <score>.\n"
            "Do not read or analyse the evaluator, do not explore other files, and "
            "do not create extra files — in particular write nothing at all "
            "inside kapso_evaluation/. The expected score is "
            f"{expected!r}.\n\n"
            "```python\n" + code + "\n```\n"
        ),
    }


def _build_strategy_resumed(rt: KapsoRuntime) -> None:
    """``KapsoRuntime._build_strategy`` with ``import_from_checkpoint=True``.

    The orchestrator's resume path skips the workspace/dir setup (which would
    overwrite the campaign's own state) and restores the strategy from the run
    checkpoint.  The adapter has no resumed variant, so the same three
    constructor arguments are assembled here; nothing else differs.
    """
    from kapso.environment.handlers.generic import GenericProblemHandler
    from kapso.execution.search_strategies.base import SearchStrategyConfig
    from kapso.execution.search_strategies.generic.strategy import GenericSearch

    rt.problem_handler = GenericProblemHandler(problem_description=PROBLEM)
    config = SearchStrategyConfig(
        problem_handler=rt.problem_handler,
        llm=None,
        coding_agent_config=rt._coding_agent_config(rt.mode_config["coding_agent"]),
        params=dict(rt.mode_config["search_strategy"]["params"]),
        initial_repo=None,
        eval_dir=str(rt.tree_source),
        data_dir=None,
        feedback_generator=SeamFeedbackJudge(),
        goal=GOAL,
    )
    rt.strategy = GenericSearch(
        config,
        workspace_dir=str(rt.workspace_dir),
        import_from_checkpoint=True,
    )
    rt.seams = install_seams(
        rt.strategy, rt.config, rt,
        patch=("ideation",) if rt.real_implementation else None,
    )


def _make_maintainer(rt: KapsoRuntime):
    from kapso.execution.evaluation_maintainer.maintainer import EvaluationMaintainer
    from kapso.execution.fidelity import FidelitySpec

    block = rt.mode_config["evaluation_maintainer"]
    fidelity_spec = FidelitySpec.resolve(rt.mode_config["budget"].get("fidelity"))
    maintainer = EvaluationMaintainer(
        coding_agent_config=rt._coding_agent_config(block),
        workspace_dir=str(rt.workspace_dir),
        fast_fraction=fidelity_spec.eval_fast_fraction,
        subsample_seed=block.get("subsample_seed", 1337),
        calibration_fraction=block.get("calibration_fraction", 0.03),
        calibration_timeout_seconds=block.get("calibration_timeout_seconds", 900),
        fast_variant_threshold_seconds=(
            block.get("fast_variant_threshold_minutes", 20) * 60
        ),
        overhead_factor=block.get("overhead_factor", 1.25),
        protected_data_paths=block.get("protected_data_paths", []),
    )
    maintainer._run_agent = lambda prompt: 0.0  # the documented setup seam
    return maintainer


def _adopt_registered(rt: KapsoRuntime) -> Dict[str, Any]:
    """Point the strategy at the registry head — the orchestrator's
    ``_ensure_evaluation_registered`` on resume, without re-running setup.

    The head must match the workspace's live evaluation tree; if it does not,
    the campaign is not resumable and the bridge stops here rather than
    measuring against a ruler nobody registered.
    """
    from kapso.execution.evaluation_integrity import (
        build_evaluation_manifest,
        manifest_fingerprint,
        verify_data_manifest,
    )
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    rt.maintainer = _make_maintainer(rt)
    head = rt.maintainer.registry.head()
    if head is None:
        raise RuntimeError("no registered evaluator head in the campaign workspace")
    live_manifest = build_evaluation_manifest(rt.maintainer.evaluation_dir)
    live_fingerprint = manifest_fingerprint(live_manifest)
    if live_fingerprint != head.evaluator_id:
        raise RuntimeError(
            "workspace evaluation tree does not match the registered head: "
            f"{live_fingerprint} != {head.evaluator_id}"
        )
    if head.data_manifest:
        problem = verify_data_manifest(str(rt.workspace_dir), head.data_manifest)
        if problem:
            raise RuntimeError(f"registered data manifest mismatch: {problem}")
    rt.strategy.set_registered_evaluation(
        manifest=live_manifest,
        command=rt.maintainer.evaluation_command(fidelity="full", fraction=1.0),
        evaluator_id=head.evaluator_id,
        subsample_seed=rt.maintainer.subsample_seed,
        data_manifest=head.data_manifest,
    )
    rt.strategy.record_eval_duration = rt.maintainer.record_run
    rt.strategy.observe_fidelity(FULL_PASSTHROUGH)
    rt.registration = None
    return {
        "head_evaluator_id": head.evaluator_id,
        "head_version": head.version,
        "live_tree_fingerprint": live_fingerprint,
        "command_full": rt.maintainer.evaluation_command(fidelity="full", fraction=1.0),
        "subsample_seed": rt.maintainer.subsample_seed,
        "data_manifest_entries": len(head.data_manifest or {}),
        "setup_called": False,
    }


def _resume(rt: KapsoRuntime, mode_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    from kapso.core.config import load_mode_config

    bootstrap_kapso(rt.config)
    rt.mode_config = load_mode_config(str(rt.config.mode_config), mode_name)
    rt.run_dir = Path(rt.run_dir).resolve()
    rt.workspace_dir = (rt.run_dir / "workspace").resolve()
    rt.state_root = Path(rt.state_root).resolve()
    rt.tree_source = (rt.run_dir / "registered_evaluation_source").resolve()
    os.environ["A0_KAPSO_EVAL_STATE_ROOT"] = str(rt.state_root)
    _build_strategy_resumed(rt)
    adopted = _adopt_registered(rt)
    rt.strategy.load_state(state)
    return adopted


# --------------------------------------------------------------------------- #
# observation helpers
# --------------------------------------------------------------------------- #

def _git(workspace: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True, text=True,
    )
    return out.stdout.strip()


def _git_rc(workspace: Path, *args: str) -> int:
    return subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True, text=True,
    ).returncode


def _node_record(node: Any) -> Dict[str, Any]:
    return {
        "node_id": node.node_id,
        "parent_node_id": node.parent_node_id,
        "parent_branch_name": node.parent_branch_name,
        "branch_name": node.branch_name,
        "score": node.score,
        "evaluation_valid": node.evaluation_valid,
        "had_error": node.had_error,
        "evaluation_integrity_error": node.evaluation_integrity_error,
        "build_fidelity": node.build_fidelity,
        "eval_fidelity": node.eval_fidelity,
        "should_stop": node.should_stop,
        "iteration_duration_seconds": node.duration_seconds,
        "attempts": [attempt.to_dict() for attempt in node.evaluation_attempts],
        "manifest_lines": [
            line.strip()
            for line in (node.evaluation_output or "").splitlines()
            if line.strip().startswith("KAPSO_EVAL_MANIFEST")
        ],
        "code_diff_stat": _diff_stat(node.branch_name, node.parent_branch_name, node),
        "code_diff": _trim(node.code_diff, 4000),
        "code_changes_summary": _trim(node.code_changes_summary, 800),
        "technical_difficulties": _trim(node.technical_difficulties, 400),
        "agent_output_tail": (node.agent_output or "")[-1500:],
    }


def _trim(text: Optional[str], limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[-limit:]


def _diff_stat(branch: str, parent: str, node: Any) -> Dict[str, Any]:
    """The session's own change against its parent branch (from git)."""
    return {
        "branch": branch,
        "parent_branch": parent,
        "recorded_in_node": bool(node.code_diff.strip()),
    }


def _selection_probe(strategy: Any) -> Dict[str, Any]:
    """Re-execute KAPSO's own selectors over the current node history."""
    best = strategy.get_best_experiment()
    deliverable = strategy.get_deliverable_experiment()
    return {
        "get_best_experiment": (
            None if best is None
            else {"node_id": best.node_id, "branch_name": best.branch_name,
                  "score": best.score}
        ),
        "get_deliverable_experiment": (
            None if deliverable is None
            else {"node_id": deliverable.node_id,
                  "branch_name": deliverable.branch_name,
                  "score": deliverable.score}
        ),
        "get_deliverable_score": strategy.get_deliverable_score(),
        "parent_policy": getattr(strategy, "parent_policy", None),
        "registered_evaluator_id": strategy.registered_evaluator_id,
    }


def _branch_facts(workspace: Path, branches: List[str]) -> Dict[str, Any]:
    """The branches the sessions pushed, as git knows them.

    ``merge_base[<a>|<b>] == head[a]`` is the precise statement that ``b`` was
    branched off exactly ``a``'s tip — the campaign's own lineage, not a claim
    read out of a model transcript.
    """
    facts: Dict[str, Any] = {
        "heads": {},
        "ancestry": {},
        "commits": {},
        "merge_base": {},
    }
    for name in branches:
        facts["heads"][name] = _git(workspace, "rev-parse", name)
        facts["commits"][name] = _git(
            workspace, "log", "--format=%H %P %s", "-10", name
        ).splitlines()
    for child in branches:
        for parent in branches:
            if child == parent:
                continue
            facts["ancestry"][f"{parent}->{child}"] = (
                _git_rc(workspace, "merge-base", "--is-ancestor", parent, child) == 0
            )
            facts["merge_base"][f"{parent}|{child}"] = _git(
                workspace, "merge-base", parent, child
            )
    return facts


def _independent_reference(config, eid, run_dir: Path, branch: str, workspace: Path,
                           tag: str) -> Dict[str, Any]:
    """E* run outside KAPSO on the branch's committed solution.py."""
    worktree = _materialize(workspace, branch)
    try:
        solution = Path(worktree) / "solution.py"
        payload = {
            "branch": branch,
            "solution_present": solution.is_file(),
            "solution_sha256": (
                hashlib.sha256(solution.read_bytes()).hexdigest()
                if solution.is_file() else None
            ),
        }
        if solution.is_file():
            probe = run_dir / "independent" / tag
            probe.mkdir(parents=True, exist_ok=True)
            (probe / "solution.py").write_bytes(solution.read_bytes())
            reference = run_reference_e_star(
                config, eid, tag, probe,
                {"seed": 1337, "fidelity": "full", "fraction": 1.0},
                run_dir / "state",
            )
            payload["reference"] = {
                "exit_code": reference.exit_code,
                "status": reference.status,
                "objective": reference.objective,
                "failure_kind": reference.failure_kind,
                "command": reference.command,
            }
        else:
            payload["reference"] = None
        return payload
    finally:
        _dematerialize(workspace, worktree)


def _materialize(workspace: Path, ref: str) -> str:
    import tempfile

    path = tempfile.mkdtemp(prefix="a0_bridge_")
    os.rmdir(path)
    subprocess.run(
        ["git", "-C", str(workspace), "worktree", "add", "--detach", path, ref],
        check=True, capture_output=True, text=True,
    )
    return path


def _dematerialize(workspace: Path, path: str) -> None:
    subprocess.run(
        ["git", "-C", str(workspace), "worktree", "remove", "--force", path],
        capture_output=True, text=True,
    )


def _branch_tree(workspace: Path, branch: str) -> Dict[str, Any]:
    worktree = _materialize(workspace, branch)
    try:
        manifest, fingerprint = _tree_fingerprint(Path(worktree) / "kapso_evaluation")
        return {"fingerprint": fingerprint, "files": manifest}
    finally:
        _dematerialize(workspace, worktree)


# --------------------------------------------------------------------------- #
# rounds
# --------------------------------------------------------------------------- #

def _runtime(config, eid, candidates, run_dir: Path, real: bool, mode_name: str):
    return KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=run_dir,
        state_root=run_dir / "state",
        real_implementation=real,
        mode_name=mode_name,
    )


def round1(config, eid, candidates, baseline, args) -> int:
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    entry = ROUNDS[1]
    candidate = next(c for c in candidates if c.candidate_id == entry["candidate_id"])

    runtime = _runtime(config, eid, candidates, run_dir,
                       not args.seam_implementation, args.mode_name)
    prepared_at = time.monotonic()
    runtime.prepare(baseline)
    prepared_sec = time.monotonic() - prepared_at

    plan = runtime.seams["plan"]
    plan.queue.append(_install_entry(
        candidate, float(entry["expected_score"]),
        run_evaluation=bool(args.seam_implementation),
    ))

    selections: List[Dict[str, Any]] = []
    _tap_select_parent(runtime.strategy, selections, "inside_run")
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    runtime.strategy.observe_fidelity(FULL_PASSTHROUGH)

    started = time.monotonic()
    node = runtime.strategy.run(PROBLEM)
    elapsed = time.monotonic() - started

    report = {
        "schema": "a0.kapso.bridge_2round.round/v1",
        "round": 1,
        "lane": (
            "real run_implementation (strategy.py:1036) over a codex/"
            "deepseek-flash session; ideation and judge seamed"
            if not args.seam_implementation else
            "seam implementation (dry run): the adapter's own _Plan drives the "
            "session folder; the run/resume/report code path is the real one"
        ),
        "mode_name": args.mode_name,
        "mode_config": str(Path(args.mode_config).resolve()),
        "wall_clock_cap_sec": args.cap,
        "cap_enforced_by": "the launching shell (`timeout <cap>` on this process)",
        "prepared_sec": round(prepared_sec, 3),
        "run_sec": round(elapsed, 3),
        "evaluator_calls": runtime.evaluator_calls,
        "eid_star": eid.eid_star,
        "registration": {
            "evaluator_id": runtime.registration.evaluator_id,
            "version": runtime.registration.version,
            "provenance": runtime.registration.provenance,
            "command_full": runtime.registration.command_full,
            "command_calibration": runtime.registration.command_calibration,
            "calibration_seconds": round(runtime.registration.calibration_seconds, 3),
            "setup_agent_seam": runtime.registration.setup_agent_seam,
            "registry_head_evaluator_id": runtime.registration.registry_head_evaluator_id,
        },
        "plan": {
            "candidate_id": candidate.candidate_id,
            "expected_score": float(entry["expected_score"]),
            "role": entry["role"],
            "solution_sha256": candidate.solution_sha256,
        },
        "baseline": {
            "candidate_id": baseline.candidate_id,
            "solution_sha256": baseline.solution_sha256,
        },
        "parent_selection_observed": selections,
        "node": _node_record(node),
        "selection_after_round": _selection_probe(runtime.strategy),
    }

    workspace = runtime.workspace_dir
    branch = node.branch_name
    report["git"] = _branch_facts(workspace, ["main", branch])
    report["branch_tree"] = _branch_tree(workspace, branch)
    report["independent_reference"] = _independent_reference(
        config, eid, run_dir, branch, workspace, f"round1-{branch}"
    )

    node0 = runtime.strategy.node_history[0]
    reference = (report["independent_reference"] or {}).get("reference") or {}
    report["checks"] = {
        "session_score_is_the_frozen_candidate": bool(
            node0.score is not None
            and abs(node0.score - float(entry["expected_score"])) <= eid.epsilon
        ),
        "independent_e_star_matches_node_score": bool(
            reference.get("objective") is not None
            and node0.score is not None
            and abs(reference["objective"] - node0.score) <= eid.epsilon
        ),
        "manifest_triple_matches_grant": _manifest_triple_ok(
            report["node"]["manifest_lines"], runtime.maintainer.subsample_seed
        ),
        "branch_tree_is_registered_head": bool(
            report["branch_tree"]["fingerprint"]
            == runtime.registration.registry_head_evaluator_id
        ),
    }
    report["round_ok"] = all(report["checks"].values())

    write_json(run_dir / "round1.json", report)
    write_json(run_dir / "campaign-state-round1.json", runtime.strategy.dump_state())
    write_json(run_dir / "state-after-round1.json", _state_summary(runtime))

    print(json.dumps({
        "round": 1,
        "node": report["node"]["node_id"],
        "branch": branch,
        "parent_branch": report["node"]["parent_branch_name"],
        "score": node0.score,
        "independent": reference.get("objective"),
        "round_ok": report["round_ok"],
        "checks": report["checks"],
        "run_sec": report["run_sec"],
        "prepared_sec": report["prepared_sec"],
    }, indent=1, default=str))
    return 0 if report["round_ok"] else 5


def round2(config, eid, candidates, baseline, args) -> int:
    run_dir = Path(args.run_dir).resolve()
    state_path = run_dir / "campaign-state-round1.json"
    if not state_path.is_file():
        print(f"round 1 state missing: {state_path}", file=sys.stderr)
        return 2
    state = json.loads(state_path.read_text("utf-8"))
    entry = ROUNDS[2]
    candidate = next(c for c in candidates if c.candidate_id == entry["candidate_id"])

    runtime = _runtime(config, eid, candidates, run_dir,
                       not args.seam_implementation, args.mode_name)
    adopted = _resume(runtime, args.mode_name, state)

    # KAPSO's own selectors, re-executed on the restored history, before the
    # iteration runs: this is the parent the campaign *will* use.
    parent_on_restored_state = runtime.strategy._select_parent()

    selections: List[Dict[str, Any]] = []
    _tap_select_parent(runtime.strategy, selections, "inside_run")
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    runtime.strategy.observe_fidelity(FULL_PASSTHROUGH)

    plan = runtime.seams["plan"]
    plan.queue.append(_install_entry(
        candidate, float(entry["expected_score"]),
        run_evaluation=bool(args.seam_implementation),
    ))

    started = time.monotonic()
    node = runtime.strategy.run(PROBLEM)
    elapsed = time.monotonic() - started

    workspace = runtime.workspace_dir
    branch = node.branch_name
    report = {
        "schema": "a0.kapso.bridge_2round.round/v1",
        "round": 2,
        "lane": (
            "real run_implementation (strategy.py:1036) over a codex/"
            "deepseek-flash session; ideation and judge seamed"
            if not args.seam_implementation else
            "seam implementation (dry run): the adapter's own _Plan drives the "
            "session folder; the run/resume/report code path is the real one"
        ),
        "mode_name": args.mode_name,
        "mode_config": str(Path(args.mode_config).resolve()),
        "wall_clock_cap_sec": args.cap,
        "cap_enforced_by": "the launching shell (`timeout <cap>` on this process)",
        "run_sec": round(elapsed, 3),
        "evaluator_calls": runtime.evaluator_calls,
        "eid_star": eid.eid_star,
        "resume": {
            "state_file": str(state_path),
            "state_file_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
            "restored_node_ids": [n.node_id for n in runtime.strategy.node_history],
            "restored_iteration_count": runtime.strategy.iteration_count,
            "adopted_registered_head": adopted,
        },
        "parent_selection_on_restored_state": {
            "branch_name": parent_on_restored_state.branch_name,
            "node_id": parent_on_restored_state.node_id,
        },
        "parent_selection_observed": selections,
        "plan": {
            "candidate_id": candidate.candidate_id,
            "expected_score": float(entry["expected_score"]),
            "role": entry["role"],
            "solution_sha256": candidate.solution_sha256,
        },
        "node": _node_record(node),
        "selection_after_round": _selection_probe(runtime.strategy),
    }

    report["git"] = _branch_facts(
        workspace, ["main"] + [n.branch_name for n in runtime.strategy.node_history]
    )
    report["branch_tree"] = _branch_tree(workspace, branch)
    report["independent_reference"] = _independent_reference(
        config, eid, run_dir, branch, workspace, f"round2-{branch}"
    )

    # The campaign's own end-of-run move: checkout the deliverable branch.
    active_before = _git(workspace, "rev-parse", "--abbrev-ref", "HEAD")
    deliverable_branch = runtime.strategy.checkout_to_best_experiment_branch()
    report["checkout_to_best_experiment_branch"] = {
        "returned": deliverable_branch,
        "active_before": active_before,
        "active_after": _git(workspace, "rev-parse", "--abbrev-ref", "HEAD"),
    }

    reference = (report["independent_reference"] or {}).get("reference") or {}
    check_manifest = _manifest_triple_ok(
        report["node"]["manifest_lines"], adopted["subsample_seed"]
    )
    report["checks"] = {
        "session_score_is_the_frozen_candidate": bool(
            node.score is not None
            and abs(node.score - float(entry["expected_score"])) <= eid.epsilon
        ),
        "independent_e_star_matches_node_score": bool(
            reference.get("objective") is not None
            and node.score is not None
            and abs(reference["objective"] - node.score) <= eid.epsilon
        ),
        "manifest_triple_matches_grant": check_manifest,
        "branch_tree_is_registered_head": bool(
            report["branch_tree"]["fingerprint"] == adopted["head_evaluator_id"]
        ),
        "parent_is_the_only_restored_node": bool(
            node.parent_node_id == runtime.strategy.node_history[0].node_id
        ),
    }
    report["round_ok"] = all(report["checks"].values())

    write_json(run_dir / "round2.json", report)
    write_json(run_dir / "campaign-state-final.json", runtime.strategy.dump_state())
    write_json(run_dir / "state-after-round2.json", _state_summary(runtime))

    print(json.dumps({
        "round": 2,
        "node": report["node"]["node_id"],
        "branch": branch,
        "parent_branch": report["node"]["parent_branch_name"],
        "parent_node_id": report["node"]["parent_node_id"],
        "parent_on_restored_state": report["parent_selection_on_restored_state"],
        "score": node.score,
        "independent": reference.get("objective"),
        "deliverable": report["selection_after_round"]["get_deliverable_experiment"],
        "checkout": report["checkout_to_best_experiment_branch"],
        "round_ok": report["round_ok"],
        "checks": report["checks"],
        "run_sec": report["run_sec"],
    }, indent=1, default=str))
    return 0 if report["round_ok"] else 5


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def _tap_select_parent(strategy: Any, sink: List[Dict[str, Any]], phase: str) -> None:
    original = strategy._select_parent

    def wrapper():
        selection = original()
        sink.append({
            "phase": phase,
            "branch_name": selection.branch_name,
            "node_id": selection.node_id,
        })
        return selection

    strategy._select_parent = wrapper


def _manifest_triple_ok(lines: List[str], seed: int) -> bool:
    if not lines:
        return False
    payload = json.loads(lines[-1][len("KAPSO_EVAL_MANIFEST"):].strip())
    return bool(
        payload.get("fidelity") == "full"
        and abs(float(payload.get("fraction", 0.0)) - 1.0) <= 1e-9
        and int(payload.get("seed", 0)) == int(seed)
    )


def _state_summary(runtime: KapsoRuntime) -> Dict[str, Any]:
    return {
        "iteration_count": runtime.strategy.iteration_count,
        "nodes": [
            {
                "node_id": n.node_id,
                "parent_node_id": n.parent_node_id,
                "parent_branch_name": n.parent_branch_name,
                "branch_name": n.branch_name,
                "score": n.score,
                "evaluation_valid": n.evaluation_valid,
                "had_error": n.had_error,
                "attempts": [a.to_dict() for a in n.evaluation_attempts],
            }
            for n in runtime.strategy.node_history
        ],
        "registered_evaluator_id": runtime.strategy.registered_evaluator_id,
        "scores_evaluator_id": runtime.strategy.scores_evaluator_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("round", choices=["round1", "round2"])
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--mode-config", default=str(HERE / "mode.bridge.yaml"))
    parser.add_argument("--mode-name", default="BRIDGE_2ROUND")
    parser.add_argument("--cap", type=float, default=1500.0,
                        help="the wall-clock cap this process was launched under")
    parser.add_argument("--seam-implementation", action="store_true",
                        help="dry run: seam the implementation phase too")
    args = parser.parse_args()

    config = AdapterConfig.load()
    config.mode_config = Path(args.mode_config)
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    check_candidate_integrity(candidates)
    baseline = next(c for c in candidates if c.role == "baseline")

    if args.round == "round1":
        return round1(config, eid, candidates, baseline, args)
    return round2(config, eid, candidates, baseline, args)


if __name__ == "__main__":
    sys.exit(main())
