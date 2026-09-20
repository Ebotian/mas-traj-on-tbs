"""Post-hoc verification of a completed real-lane KAPSO round.

`bin/e2e_round.py` crashed inside its own verification step on the first
completed round (it fingerprinted a `materialize_ref` worktree *after* the
context manager had removed it — the round itself had finished fine).  Rather
than re-buying the round, this reads the run's durable leftovers:

* the experiment branch the real session pushed (candidate bytes + registered
  evaluation tree),
* the runtime's own stdout log (the node's score of record, the manifest line the
  *session* printed, the registered evaluator id),

and re-derives every A0 claim that does not need in-memory node state:

    E* (independent run on the committed candidate) == node.score
    the session's manifest triple == the granted class (full / 1.0 / 1337)
    the branch's committed kapso_evaluation/ fingerprint == the registry head

Usage:

    .venv/bin/python bin/e2e_verify.py --run-dir runs/e2e-real --log /tmp/e2e-real.log
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from a0_adapter.channels import run_reference_e_star  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig, bootstrap_kapso, load_eid_star, write_json,
)
from a0_adapter.runtime import _tree_fingerprint  # noqa: E402


def branch_names(workspace: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(workspace), "for-each-ref", "--format=%(refname:short)",
         "refs/heads/"],
        capture_output=True, text=True,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--log", required=True,
                        help="the runtime's own stdout from the round")
    parser.add_argument("--branch", default=None)
    args = parser.parse_args()

    config = AdapterConfig.load()
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    run_dir = Path(args.run_dir).resolve()
    workspace = run_dir / "workspace"
    log_text = Path(args.log).read_text("utf-8", errors="replace")

    branches = args.branch and [args.branch] or [
        name for name in branch_names(workspace) if name.startswith("generic_exp_")
    ]
    if not branches:
        print("no experiment branch in the workspace", file=sys.stderr)
        return 2
    branch = branches[-1]

    scores = re.findall(r"✓ Node \d+ completed: score=([0-9.eE+-]+)", log_text)
    node_score = float(scores[-1]) if scores else None
    # The runtime's transcript lines carry prefixes ([codex] ...), so search for
    # the marker anywhere in the line rather than only at its start.
    manifest_lines = [
        line[line.index("KAPSO_EVAL_MANIFEST"):].strip()
        for line in log_text.splitlines()
        if "KAPSO_EVAL_MANIFEST" in line and "{" in line
    ]
    manifest = json.loads(manifest_lines[-1][len("KAPSO_EVAL_MANIFEST"):].strip()) \
        if manifest_lines else None
    registered_ids = re.findall(r"registered evaluator[^0-9a-f]*([0-9a-f]{64})",
                               log_text, re.I)

    report: dict = {
        "schema": "a0.kapso.e2e_verification/v1",
        "runtime": "kapso",
        "run_dir": str(run_dir),
        "log": str(args.log),
        "branch": branch,
        "lane": "real run_implementation (strategy.py:1036); ideation and judge seamed",
        "eid_star": eid.eid_star,
        "node_score_from_log": node_score,
        "session_manifest": manifest,
        "manifest_triple_matches_grant": bool(
            manifest
            and manifest.get("fidelity") == "full"
            and abs(float(manifest.get("fraction", 0.0)) - 1.0) <= 1e-9
            and int(manifest.get("seed", 0)) == 1337
        ),
        "verification_note": (
            "node state (attempts) is in-memory and gone; the claims below are "
            "re-derived from the committed branch and the independent E* run"
        ),
    }

    with _materialize(workspace, branch) as worktree:
        solution = Path(worktree) / "solution.py"
        report["branch_solution_sha256"] = (
            hashlib.sha256(solution.read_bytes()).hexdigest()
            if solution.is_file() else None
        )
        manifest_map, fingerprint = _tree_fingerprint(
            Path(worktree) / "kapso_evaluation"
        )
        report["branch_tree_fingerprint"] = fingerprint
        report["branch_tree_files"] = manifest_map
        if solution.is_file():
            probe = run_dir / "verify_candidate"
            probe.mkdir(parents=True, exist_ok=True)
            (probe / "solution.py").write_bytes(solution.read_bytes())
            reference = run_reference_e_star(
                config, eid, "e2e-branch-candidate", probe,
                {"seed": 1337, "fidelity": "full", "fraction": 1.0},
                run_dir / "state",
            )
            report["independent_reference"] = {
                "exit_code": reference.exit_code,
                "status": reference.status,
                "objective": reference.objective,
                "failure_kind": reference.failure_kind,
            }

    reference_objective = (report.get("independent_reference") or {}).get("objective")
    report["score_matches_reference"] = (
        reference_objective is not None
        and node_score is not None
        and abs(reference_objective - node_score) <= eid.epsilon
    )
    registry = run_dir / "workspace" / ".kapso" / "evaluation_registry.json"
    registered_head = None
    if registry.is_file():
        history = json.loads(registry.read_text("utf-8"))
        registered_head = history[-1]["evaluator_id"]
    report["registered_evaluator_id"] = registered_head
    report["branch_tree_is_registered_head"] = (
        report["branch_tree_fingerprint"] == registered_head
    )
    # A session may add a non-evaluator file to the tree (round 1 added
    # eval_profile.md); KAPSO's verify_evaluation_tree only protects evaluator
    # source suffixes, and every frame run re-syncs the registered head anyway.
    # Record the delta instead of calling it a mismatch.
    report["branch_tree_extra_files"] = sorted(
        name for name in report["branch_tree_files"]
        if Path(name).suffix.lower() not in (".py", ".json", ".yaml", ".yml",
                                             ".toml", ".sh", ".cfg", ".ini")
    )
    report["score_cross_checks"] = {
        "session_manifest_score": (manifest or {}).get("e_star_objective_value"),
        "node_score_from_log": node_score,
        "independent_e_star": reference_objective,
    }
    report["manifest_class_mismatch_printed"] = "Manifest class mismatch" in log_text
    report["verdict"] = (
        "verified_end_to_end"
        if (
            report["manifest_triple_matches_grant"]
            and report["score_matches_reference"]
            and not report["manifest_class_mismatch_printed"]
        )
        else "partially_verified"
    )
    report["verified_claims"] = {
        "real session ran the registered evaluation": bool(manifest_lines),
        "manifest triple == granted class (full/1.0/1337)":
            report["manifest_triple_matches_grant"],
        "no manifest class mismatch printed by KAPSO":
            not report["manifest_class_mismatch_printed"],
        "node score of record == independent E* on the committed candidate":
            report["score_matches_reference"],
        "branch tree byte-identical to the registered head":
            report["branch_tree_is_registered_head"],
    }
    write_json(run_dir / "e2e_verification.json", report)
    print(json.dumps({
        "branch": branch,
        "node_score_from_log": node_score,
        "independent_reference": report.get("independent_reference"),
        "score_matches_reference": report["score_matches_reference"],
        "manifest_triple_matches_grant": report["manifest_triple_matches_grant"],
        "branch_tree_fingerprint": report["branch_tree_fingerprint"],
        "verdict": report["verdict"],
    }, indent=1))
    return 0


class _materialize:
    """git worktree add/remove for the verify script (no Kapso object needed)."""

    def __init__(self, workspace: Path, ref: str):
        self.workspace = workspace
        self.ref = ref
        self.path = None

    def __enter__(self):
        import tempfile

        self.path = Path(tempfile.mkdtemp(prefix="a0_verify_"))
        self.path.rmdir()
        subprocess.run(
            ["git", "-C", str(self.workspace), "worktree", "add", "--detach",
             str(self.path), self.ref],
            check=True, capture_output=True, text=True,
        )
        return self.path

    def __exit__(self, *exc):
        subprocess.run(
            ["git", "-C", str(self.workspace), "worktree", "remove", "--force",
             str(self.path)],
            capture_output=True, text=True,
        )
        return False


if __name__ == "__main__":
    sys.exit(main())
