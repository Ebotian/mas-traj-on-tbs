"""End-to-end check: a REAL coding-agent session drives one KAPSO iteration.

Everything the A0 rounds replaced with a seam, this script does not: the
implementation phase is the runtime's own ``run_implementation``
(``strategy.py:1036``), so a genuine coding-agent session clones the branch,
writes the candidate, runs the registered evaluation command inside its own
session and commits/pushes the result.  The ideation phase stays seamed (it
needs a longer, open-ended session) and the judge stays seamed, so this is a
partial end-to-end observation — exactly one phase less seamed than
``a0_adapter run`` — and it is recorded as such.

What it establishes if it succeeds:

* the registered evaluation really is executed *by the session*, and its
  ``KAPSO_EVAL_MANIFEST`` line reaches ``node.evaluation_output``;
* the manifest triple of that real session equals the granted class (A01.4 on
  the real path), and the recorded attempt carries the registered evaluator id;
* the resulting candidate, evaluated independently by ``E*``, matches
  ``node.score`` (A0.1 on the real path);
* whether the session left the registered evaluation tree intact (integrity).

Usage:

    .venv/bin/python bin/e2e_round.py [--timeout 1200]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from a0_adapter.channels import run_reference_e_star  # noqa: E402
from a0_adapter.common import (  # noqa: E402
    AdapterConfig, bootstrap_kapso, check_candidate_integrity,
    load_candidate_set, load_eid_star, write_json,
)
from a0_adapter.registered_tree import install_registered_tree  # noqa: E402
from a0_adapter.runtime import KapsoRuntime, PROBLEM  # noqa: E402
from a0_adapter.seams import _Plan  # noqa: E402

GOAL = (
    "Optimize `solution.py`'s `pack_circles(n=26)` to return deterministic, "
    "non-overlapping circles inside the unit square, maximize `sum_radii`, and "
    "keep default `pack_circles()` equivalent to `pack_circles(26)`."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=1500)
    parser.add_argument("--run-dir", default="runs/e2e-implementation")
    parser.add_argument(
        "--mode-config",
        default=str(HERE / "config" / "mode.circle-packing.codex.yaml"),
    )
    parser.add_argument(
        "--install-candidate",
        default="c04_near_tie",
        help="a frozen C* member whose bytes the session is told to install "
             "(its E* score is then known, so the real path can be checked "
             "against an independent reference)",
    )
    args = parser.parse_args()

    config = AdapterConfig.load()
    config.mode_config = Path(args.mode_config)
    bootstrap_kapso(config)
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    check_candidate_integrity(candidates)
    baseline = next(c for c in candidates if c.role == "baseline")

    run_dir = (HERE / args.run_dir).resolve()
    runtime = KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=run_dir,
        state_root=run_dir / "state",
        real_implementation=True,
        mode_name="CIRCLE_PACKING_CODEX",
    )
    runtime.prepare(baseline)

    # The ideation seam supplies a real task for the session to work on: the
    # upstream baseline as the starting point, with the objective restated.
    plan: _Plan = runtime.seams["plan"]
    install = next(
        (c for c in candidates if c.candidate_id == args.install_candidate), None
    )
    if install is None:
        print(f"unknown candidate {args.install_candidate!r}", file=sys.stderr)
        return 2
    install_code = (install.path / "solution.py").read_text("utf-8")
    plan.queue.append({
        "candidate_id": args.install_candidate,
        "fidelity": "full",
        "fraction": 1.0,
        "tamper": None,
        "commit_tamper": False,
        "run_evaluation": False,
        "solution_text": (
            "Do exactly two things, immediately, without investigating anything:\n"
            "1. Overwrite solution.py with EXACTLY the code below, byte for byte.\n"
            "2. Run `python kapso_evaluation/kapso_eval.py --fidelity full "
            "--fraction 1.0 --seed 1337` in the foreground and copy its complete "
            "stdout into your <evaluation_output> tag, with the score from its "
            "KAPSO_EVAL_MANIFEST line in <score>.\n"
            "Do not read or analyse the evaluator, do not explore other files, and "
            "do not create extra files — in particular write nothing at all "
            "inside kapso_evaluation/. The expected score is 2.451820520843313.\n\n"
            "```python\n" + install_code + "\n```\n"
        ),
    })

    started = time.monotonic()
    from kapso.execution.fidelity import FULL_PASSTHROUGH

    runtime.strategy.observe_fidelity(FULL_PASSTHROUGH)
    node = runtime.strategy.run(PROBLEM)
    elapsed = time.monotonic() - started

    branch_solution = None
    branch_tree_fingerprint = None
    from a0_adapter.runtime import _tree_fingerprint

    with runtime.strategy.workspace.materialize_ref(node.branch_name) as worktree:
        solution_path = Path(worktree) / "solution.py"
        branch_solution = solution_path.read_bytes() if solution_path.is_file() else None
        branch_tree = Path(worktree) / "kapso_evaluation"
        # Inside the with-block: materialize_ref removes the worktree on exit.
        _, branch_tree_fingerprint = _tree_fingerprint(branch_tree)

    report = {
        "schema": "a0.kapso.e2e_implementation/v1",
        "runtime": "kapso",
        "lane": "real run_implementation (strategy.py:1036); ideation and judge seamed",
        "eid_star": eid.eid_star,
        "registered_evaluator_id": runtime.registration.evaluator_id,
        "registered_command": runtime.registration.command_full,
        "elapsed_sec": round(elapsed, 3),
        "node": {
            "node_id": node.node_id,
            "branch_name": node.branch_name,
            "score": node.score,
            "evaluation_valid": node.evaluation_valid,
            "had_error": node.had_error,
            "evaluation_integrity_error": node.evaluation_integrity_error,
            "eval_fidelity": node.eval_fidelity,
            "build_fidelity": node.build_fidelity,
            "attempts": [attempt.to_dict() for attempt in node.evaluation_attempts],
            "agent_output_sha256_prefix": __import__("hashlib").sha256(
                (node.agent_output or "").encode("utf-8")
            ).hexdigest()[:16],
            "agent_output_tail": (node.agent_output or "")[-2000:],
            "manifest_lines": [
                line.strip()
                for line in (node.evaluation_output or "").splitlines()
                if line.strip().startswith("KAPSO_EVAL_MANIFEST")
            ],
            "code_changes_summary": node.code_changes_summary[:1000],
            "technical_difficulties": node.technical_difficulties[:500],
        },
    }

    manifest = None
    for line in report["node"]["manifest_lines"]:
        manifest = json.loads(line[len("KAPSO_EVAL_MANIFEST"):].strip())
    report["manifest_of_record"] = manifest
    report["manifest_triple_matches_grant"] = bool(
        manifest
        and manifest.get("fidelity") == "full"
        and abs(float(manifest.get("fraction", 0.0)) - 1.0) <= 1e-9
        and int(manifest.get("seed", 0)) == runtime.maintainer.subsample_seed
    )

    # Independent E* on what the session committed, at theta_E*.
    if branch_solution is not None:
        probe_dir = run_dir / "independent_candidate"
        probe_dir.mkdir(parents=True, exist_ok=True)
        (probe_dir / "solution.py").write_bytes(branch_solution)
        reference = run_reference_e_star(
            config, eid, "e2e-session-candidate", probe_dir,
            {"seed": 1337, "fidelity": "full", "fraction": 1.0},
            run_dir / "state",
        )
        report["independent_reference"] = {
            "exit_code": reference.exit_code,
            "status": reference.status,
            "objective": reference.objective,
            "failure_kind": reference.failure_kind,
            "solution_sha256": __import__("hashlib").sha256(
                branch_solution
            ).hexdigest(),
        }
        report["score_matches_reference"] = (
            reference.objective is not None
            and node.score is not None
            and abs(reference.objective - node.score) <= eid.epsilon
        )
        report["no_synthetic_score"] = not (
            reference.objective is None and node.score is not None
        )
    else:
        report["independent_reference"] = None
        report["score_matches_reference"] = False
        report["no_synthetic_score"] = False

    report["branch_tree_fingerprint"] = branch_tree_fingerprint
    report["branch_tree_is_registered_head"] = (
        branch_tree_fingerprint == runtime.registration.evaluator_id
    )
    report["verdict"] = (
        "verified_end_to_end"
        if (
            report["manifest_triple_matches_grant"]
            and report["score_matches_reference"]
            and report["branch_tree_is_registered_head"]
            and not node.had_error
        )
        else "not_verified"
    )
    write_json(run_dir / "e2e.json", report)
    print(json.dumps({
        "verdict": report["verdict"],
        "score": node.score,
        "reference": (report["independent_reference"] or {}).get("objective"),
        "manifest_lines": len(report["node"]["manifest_lines"]),
        "manifest_triple_matches_grant": report["manifest_triple_matches_grant"],
        "score_matches_reference": report["score_matches_reference"],
        "branch_tree_is_registered_head": report["branch_tree_is_registered_head"],
        "elapsed_sec": report["elapsed_sec"],
    }, indent=1))
    return 0 if report["verdict"] == "verified_end_to_end" else 5


if __name__ == "__main__":
    sys.exit(main())
