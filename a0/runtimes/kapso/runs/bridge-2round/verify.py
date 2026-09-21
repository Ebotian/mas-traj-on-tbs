"""Post-hoc verification of the two-round bridge, from KAPSO's own state.

Reads only durable artifacts of a completed bridge run and re-derives every
claim:

* KAPSO's own node history (`campaign-state-{round1,final}.json`, written by
  ``GenericSearch.dump_state``) loaded back through ``GenericSearch.load_state``
  on a campaign resumed the way the orchestrator resumes one;
* KAPSO's own selectors re-executed on that state (`_select_parent`,
  `get_best_experiment`, `get_deliverable_experiment`, `get_deliverable_score`);
* the git ancestry of the branches the sessions pushed;
* fresh independent ``E*`` runs on the baseline, round 1's branch and round 2's
  branch.

Nothing here trusts a round report or the model's own claims; the round reports
are used only as the object under test.

Usage::

    .venv/bin/python runs/bridge-2round/verify.py --run-dir runs/bridge-2round/real
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))

import bridge  # noqa: E402

from a0_adapter.channels import run_reference_e_star  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig,
    bootstrap_kapso,
    load_candidate_set,
    load_eid_star,
    write_json,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_in_branch(workspace: Path, branch: str, relpath: str) -> Optional[bytes]:
    worktree = bridge._materialize(workspace, branch)
    try:
        path = Path(worktree) / relpath
        return path.read_bytes() if path.is_file() else None
    finally:
        bridge._dematerialize(workspace, worktree)


def _e_star_on_branch(config, eid, run_dir: Path, workspace: Path, branch: str,
                      tag: str) -> Dict[str, Any]:
    return bridge._independent_reference(config, eid, run_dir, branch, workspace, tag)


def _codex_tokens(workspace: Path, branches: List[str]) -> Dict[str, Any]:
    """Token counts the codex CLI printed, per branch transcript."""
    out: Dict[str, Any] = {}
    for branch in branches:
        path = workspace / ".kapso" / "sessions" / branch / "stream.jsonl"
        if not path.is_file():
            out[branch] = {"transcript": None, "tokens_used_lines": []}
            continue
        counts = []
        lines = path.read_text("utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            if line.strip() == "tokens used" and index + 1 < len(lines):
                try:
                    counts.append(int(lines[index + 1].strip().replace(",", "")))
                except ValueError:
                    pass
        out[branch] = {
            "transcript": str(path),
            "transcript_bytes": path.stat().st_size,
            "tokens_used_lines": counts,
            "final_tokens_used": counts[-1] if counts else None,
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--mode-config", default=str(HERE / "mode.bridge.yaml"))
    parser.add_argument("--mode-name", default="BRIDGE_2ROUND")
    parser.add_argument("--seam-implementation", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    config = AdapterConfig.load()
    config.mode_config = Path(args.mode_config)
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    by_id = {c.candidate_id: c for c in candidates}
    baseline = next(c for c in candidates if c.role == "baseline")

    round1 = json.loads((run_dir / "round1.json").read_text("utf-8"))
    round2 = json.loads((run_dir / "round2.json").read_text("utf-8"))
    state1 = json.loads((run_dir / "campaign-state-round1.json").read_text("utf-8"))
    state_final = json.loads((run_dir / "campaign-state-final.json").read_text("utf-8"))
    workspace = run_dir / "workspace"

    # ---------------------------------------------------------------- #
    # KAPSO's own state, loaded back through KAPSO's own loader         #
    # ---------------------------------------------------------------- #
    rt = bridge._runtime(config, eid, candidates, run_dir,
                         not args.seam_implementation, args.mode_name)
    adopted = bridge._resume(rt, args.mode_name, state1)
    selection_after_round1 = bridge._selection_probe(rt.strategy)
    nodes_round1 = [n.node_id for n in rt.strategy.node_history]
    restored_parent_after_round1 = rt.strategy._select_parent()

    rt.strategy.load_state(state_final)
    selection_final = bridge._selection_probe(rt.strategy)
    restored_parent_final = rt.strategy._select_parent()
    nodes_final = [n.node_id for n in rt.strategy.node_history]
    node_by_id = {n.node_id: n for n in rt.strategy.node_history}

    # ---------------------------------------------------------------- #
    # git facts                                                         #
    # ---------------------------------------------------------------- #
    branches = sorted(
        {n.branch_name for n in rt.strategy.node_history} | {"main"}
    )
    git_facts = bridge._branch_facts(workspace, branches)

    # ---------------------------------------------------------------- #
    # fresh independent E* on baseline, round 1's branch, round 2's branch
    # ---------------------------------------------------------------- #
    baseline_ref = _e_star_on_branch(config, eid, run_dir, workspace, "main", "verify-main")
    r1_branch = round1["node"]["branch_name"]
    r2_branch = round2["node"]["branch_name"]
    r1_ref = _e_star_on_branch(config, eid, run_dir, workspace, r1_branch,
                               f"verify-{r1_branch}")
    r2_ref = _e_star_on_branch(config, eid, run_dir, workspace, r2_branch,
                               f"verify-{r2_branch}")

    scores = {
        "baseline_main": (baseline_ref.get("reference") or {}).get("objective"),
        f"round1_{r1_branch}": (r1_ref.get("reference") or {}).get("objective"),
        f"round2_{r2_branch}": (r2_ref.get("reference") or {}).get("objective"),
        "round1_node_score": round1["node"]["score"],
        "round2_node_score": round2["node"]["score"],
        "round1_plan_expected": round1["plan"]["expected_score"],
        "round2_plan_expected": round2["plan"]["expected_score"],
    }

    epsilon = float(eid.epsilon)

    def _decidable(high: Optional[float], low: Optional[float]) -> Dict[str, Any]:
        if high is None or low is None:
            return {"decidable": False, "margin": None, "reason": "score missing"}
        margin = float(high) - float(low)
        return {
            "high": float(high),
            "low": float(low),
            "margin": margin,
            "epsilon": epsilon,
            "decidable": bool(margin > epsilon),
            "rule": "margin > EID*'s conformance epsilon",
        }

    improvement_round1 = _decidable(
        scores[f"round1_{r1_branch}"], scores["baseline_main"]
    )
    improvement_round2 = _decidable(
        scores[f"round2_{r2_branch}"], scores[f"round1_{r1_branch}"]
    )

    # ---------------------------------------------------------------- #
    # derivation evidence                                               #
    # ---------------------------------------------------------------- #
    solution_round1 = _file_in_branch(workspace, r1_branch, "solution.py")
    solution_round2 = _file_in_branch(workspace, r2_branch, "solution.py")
    plan1 = by_id[round1["plan"]["candidate_id"]]
    plan2 = by_id[round2["plan"]["candidate_id"]]

    # The diff the round-2 session's own commit carries against its parent: the
    # campaign's recorded lineage, not a re-reading of the model's story.
    diff_r1_r2 = bridge._git(workspace, "diff", "--stat", r1_branch, r2_branch)
    solution_diff = bridge._git(workspace, "diff", r1_branch, r2_branch, "--", "solution.py")

    ancestry = git_facts.get("ancestry", {})
    commit_parents = {
        branch: git_facts.get("commits", {}).get(branch, []) for branch in branches
    }

    r1_tip = git_facts.get("heads", {}).get(r1_branch)
    r1_r2_merge_base = git_facts.get("merge_base", {}).get(f"{r1_branch}|{r2_branch}")
    r2_head_commits = git_facts.get("commits", {}).get(r2_branch, [])
    r2_first_parent_line = r2_head_commits[-1] if r2_head_commits else None

    parent_used_round2 = None
    if round2["parent_selection_observed"]:
        parent_used_round2 = round2["parent_selection_observed"][-1]

    deliverable = selection_final["get_deliverable_experiment"]
    deliverable_branch = (deliverable or {}).get("branch_name")
    deliverable_descends_from_round1 = bool(
        deliverable_branch
        and ancestry.get(f"{r1_branch}->{deliverable_branch}", False)
    )

    checks = {
        "round1_report_round_ok": bool(round1.get("round_ok")),
        "round2_report_round_ok": bool(round2.get("round_ok")),
        "round1_score_reproduced_by_fresh_e_star": bool(
            (r1_ref.get("reference") or {}).get("objective") is not None
            and round1["node"]["score"] is not None
            and abs(float((r1_ref["reference"])["objective"])
                    - float(round1["node"]["score"])) <= epsilon
        ),
        "round2_score_reproduced_by_fresh_e_star": bool(
            (r2_ref.get("reference") or {}).get("objective") is not None
            and round2["node"]["score"] is not None
            and abs(float((r2_ref["reference"])["objective"])
                    - float(round2["node"]["score"])) <= epsilon
        ),
        "round1_branch_bytes_are_the_frozen_candidate": bool(
            solution_round1 is not None
            and _sha256(solution_round1) == plan1.solution_sha256
        ),
        "round2_branch_bytes_are_the_frozen_candidate": bool(
            solution_round2 is not None
            and _sha256(solution_round2) == plan2.solution_sha256
        ),
        "round1_decidable_improvement_over_baseline": bool(
            improvement_round1["decidable"]
        ),
        "round2_parent_is_round1_winner": bool(
            parent_used_round2 is not None
            and parent_used_round2["branch_name"] == r1_branch
            and parent_used_round2["node_id"] == round1["node"]["node_id"]
            and round2["node"]["parent_branch_name"] == r1_branch
            and round2["node"]["parent_node_id"] == round1["node"]["node_id"]
        ),
        "round2_branch_descends_from_round1_branch": bool(
            ancestry.get(f"{r1_branch}->{r2_branch}", False)
        ),
        "round2_session_started_from_round1_artifact": bool(
            # the round-2 branch was branched off EXACTLY round-1's tip: the
            # session cloned the parent branch and committed on top of it
            r1_tip is not None
            and r1_r2_merge_base is not None
            and r1_r2_merge_base == r1_tip
        ),
        "deliverable_descends_from_round1_winner": deliverable_descends_from_round1,
        "restored_history_is_contiguous": nodes_final == list(range(len(nodes_final))),
    }

    verdict = "bridge_verified" if all(checks.values()) else "bridge_unproven"

    report = {
        "schema": "a0.kapso.bridge_2round.verification/v1",
        "runtime": "kapso",
        "run_dir": str(run_dir),
        "lane": round2.get("lane"),
        "eid_star": eid.eid_star,
        "epsilon": epsilon,
        "mode_name": args.mode_name,
        "wall_clock_caps_sec": {
            "round1": round1.get("wall_clock_cap_sec"),
            "round2": round2.get("wall_clock_cap_sec"),
            "enforced_by": round1.get("cap_enforced_by"),
        },
        "rounds": {
            "round1": {
                "run_sec": round1.get("run_sec"),
                "prepared_sec": round1.get("prepared_sec"),
                "candidate_id": round1["plan"]["candidate_id"],
                "node_id": round1["node"]["node_id"],
                "branch": r1_branch,
                "parent_branch": round1["node"]["parent_branch_name"],
                "score": round1["node"]["score"],
                "round_ok": round1.get("round_ok"),
            },
            "round2": {
                "run_sec": round2.get("run_sec"),
                "candidate_id": round2["plan"]["candidate_id"],
                "node_id": round2["node"]["node_id"],
                "branch": r2_branch,
                "parent_branch": round2["node"]["parent_branch_name"],
                "parent_node_id": round2["node"]["parent_node_id"],
                "score": round2["node"]["score"],
                "round_ok": round2.get("round_ok"),
            },
        },
        "scores": scores,
        "improvements": {
            "round1_over_baseline": improvement_round1,
            "round2_over_round1": improvement_round2,
        },
        "restored_state": {
            "adopted_registered_head": adopted,
            "nodes_after_round1_state": nodes_round1,
            "nodes_after_final_state": nodes_final,
            "parent_selection_after_round1_state": {
                "branch_name": restored_parent_after_round1.branch_name,
                "node_id": restored_parent_after_round1.node_id,
            },
            "parent_selection_on_final_state": {
                "branch_name": restored_parent_final.branch_name,
                "node_id": restored_parent_final.node_id,
            },
            "selection_after_round1_state": selection_after_round1,
            "selection_on_final_state": selection_final,
            "node_summary": [
                {
                    "node_id": n.node_id,
                    "parent_node_id": n.parent_node_id,
                    "parent_branch_name": n.parent_branch_name,
                    "branch_name": n.branch_name,
                    "score": n.score,
                    "evaluation_valid": n.evaluation_valid,
                    "had_error": n.had_error,
                    "build_fidelity": n.build_fidelity,
                    "eval_fidelity": n.eval_fidelity,
                    "attempts": [a.to_dict() for a in n.evaluation_attempts],
                }
                for n in rt.strategy.node_history
            ],
        },
        "derivation": {
            "parent_used_in_round2_run": parent_used_round2,
            "round1_branch": r1_branch,
            "round2_branch": r2_branch,
            "round1_branch_tip": r1_tip,
            "round2_branch_head_commits": r2_head_commits,
            "round2_commit_parent_line": r2_first_parent_line,
            "merge_base_round1_round2": r1_r2_merge_base,
            "merge_base": git_facts.get("merge_base", {}),
            "ancestry": ancestry,
            "commit_parents": commit_parents,
            "git_diff_stat_round1_round2": diff_r1_r2,
            "git_diff_solution_round1_round2_tail": solution_diff[-2000:],
            "round1_solution_sha256": _sha256(solution_round1) if solution_round1 else None,
            "round2_solution_sha256": _sha256(solution_round2) if solution_round2 else None,
            "round1_expected_solution_sha256": plan1.solution_sha256,
            "round2_expected_solution_sha256": plan2.solution_sha256,
            "round2_node_code_diff_present": bool(
                (round2["node"].get("code_diff") or "").strip()
            ),
            "deliverable": deliverable,
            "deliverable_branch": deliverable_branch,
            "deliverable_descends_from_round1_branch": deliverable_descends_from_round1,
            "checkout_to_best_experiment_branch": round2.get(
                "checkout_to_best_experiment_branch"
            ),
        },
        "fresh_independent_e_star": {
            "baseline_main": baseline_ref,
            "round1_branch": r1_ref,
            "round2_branch": r2_ref,
            "baseline_candidate_id": baseline.candidate_id,
            "baseline_candidate_sha256": baseline.solution_sha256,
        },
        "model_lane": {
            "tokens": _codex_tokens(
                workspace, [n.branch_name for n in rt.strategy.node_history]
            ),
            "note": (
                "codex reports no billing telemetry to KAPSO; the token counts "
                "are the ones the CLI itself printed into the session transcript"
            ),
        },
        "checks": checks,
        "verdict": verdict,
    }

    write_json(run_dir / "verification.json", report)
    print(json.dumps({
        "verdict": verdict,
        "checks": checks,
        "scores": scores,
        "improvements": report["improvements"],
        "deliverable": deliverable,
        "restored_parent_final": report["restored_state"][
            "parent_selection_on_final_state"
        ],
    }, indent=1, default=str))
    return 0 if verdict == "bridge_verified" else 5


if __name__ == "__main__":
    sys.exit(main())
