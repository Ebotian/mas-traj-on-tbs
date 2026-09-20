#!/usr/bin/env python
"""KAPSO registered-evaluation entrypoint (the KAPSO-side execution of E*).

Installed by the A0 KAPSO adapter into a KAPSO workspace as
``kapso_evaluation/kapso_eval.py`` and registered by KAPSO's own
``EvaluationMaintainer`` (``execution/evaluation_maintainer/maintainer.py``).
KAPSO invokes it exactly as ``evaluation_command()`` composes it
(``maintainer.py:56-61``):

    python kapso_evaluation/kapso_eval.py --fidelity F --fraction X --seed S

with ``cwd`` set to the tree whose candidate is being measured (the session
folder for a session run, the branch worktree for a frame run, the workspace
root for the registration calibration).  This file is the *only* place where a
KAPSO score comes from; it never invents one.

Contract implemented here
-------------------------
1. Evaluator identity.  The E* source files are re-hashed and compared with the
   digests the frozen ``EID*`` document recorded (``a0_locator.json``).  A
   mismatch aborts with exit 3 and no score, so the registered evaluator cannot
   silently run as a different E* than the one EID* names.  (This is the
   out-of-band evaluator-identity leg that KAPSO's own manifest triple does not
   carry: ``maintainer.py:64-83`` has no evaluator field.)
2. Candidate identity.  The candidate's ``solution.py`` must hash to a digest in
   ``EID*``'s DataManifest (the frozen ``C*``).  A candidate outside the frozen
   set aborts with exit 3 unless the adapter explicitly declares that it is
   running an out-of-set injection (A0.2 seam rounds record this).
3. One machine-readable line per run: ``KAPSO_EVAL_MANIFEST {...}`` carrying
   ``fidelity, fraction, seed, items, total_items`` (the keys KAPSO's
   ``parse_manifest_line`` requires) plus ``score`` **only when E* returned a
   measurement**.  For ``status=invalid`` / ``status=error`` the line omits
   ``score`` and the process exits non-zero, so KAPSO records *no* mechanical
   score of record instead of a numeric zero
   (``registered_evaluation.py:100-102`` returns None exactly for this shape).
4. No writes anywhere but below the locator's ``state_root`` (E* writes below
   its own ``--state-dir``); nothing is written into the candidate tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCATOR_NAME = "a0_locator.json"
MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"
EXIT_CODES = {"ok": 0, "invalid": 2, "error": 3}


def fail(message: str, code: int = 3) -> int:
    """Abort without printing a manifest line: no measurement was taken."""
    print(f"kapso_eval: {message}", file=sys.stderr)
    return code


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locator() -> dict:
    locator_path = HERE / LOCATOR_NAME
    if not locator_path.is_file():
        raise SystemExit(
            f"kapso_eval: missing locator {locator_path}; the registered "
            "evaluation tree is not the one the adapter installed"
        )
    return json.loads(locator_path.read_text(encoding="utf-8"))


def check_evaluator_identity(locator: dict) -> str:
    """Re-hash E*'s own source against the EID* EvaluatorSource records."""
    e_star = locator["e_star"]
    root = Path(e_star["dir"])
    for record in e_star["source_records"]:
        path = root / record["path"]
        if not path.is_file():
            raise AssertionError(f"E* source file missing: {path}")
        digest = sha256_file(path)
        if digest != record["sha256"]:
            raise AssertionError(
                f"E* source drifted: {record['path']} sha256 {digest} != "
                f"{record['sha256']} recorded in EID* "
                f"({locator['eid_star']})"
            )
    return locator["eid_star_components"]["EvaluatorSource"]


def resolve_candidate(arg: str | None) -> Path:
    root = Path(arg).resolve() if arg else Path.cwd()
    if root.is_file():
        root = root.parent
    solution = root / "solution.py"
    if not solution.is_file():
        raise AssertionError(f"no solution.py below {root}")
    return root


def check_candidate_identity(locator: dict, candidate_root: Path) -> dict:
    solution = candidate_root / "solution.py"
    digest = sha256_file(solution)
    members = locator["candidate_set"]["members"]
    for candidate_id, entry in members.items():
        if entry["solution_sha256"] == digest:
            return {"candidate_id": candidate_id, "in_frozen_set": True,
                    "solution_sha256": digest}
    if os.environ.get("A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE") == "1":
        return {"candidate_id": None, "in_frozen_set": False,
                "solution_sha256": digest}
    raise AssertionError(
        f"solution.py sha256 {digest} is not a member of the frozen "
        f"candidate set C* recorded in EID* ({locator['eid_star']})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="KAPSO registered evaluation over the frozen E*"
    )
    parser.add_argument("--fidelity", required=True, choices=("fast", "full"))
    parser.add_argument("--fraction", required=True, type=float)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--candidate",
        default=None,
        help="candidate root (default: the current working directory)",
    )
    args = parser.parse_args(argv)

    if not 0 < args.fraction <= 1:
        return fail(f"--fraction must be in (0, 1], got {args.fraction}", 1)

    locator = load_locator()
    e_star = locator["e_star"]
    theta = locator["theta_e_canonical"]
    metric = locator["metric"]
    # The E* state root is a property of the run, not of the evaluator: it is
    # overridden per run through the environment so that this tree's fingerprint
    # (KAPSO's EID_r) stays a function of the frozen EID* alone.
    state_root = Path(
        os.environ.get("A0_KAPSO_EVAL_STATE_ROOT")
        or locator["state_root_default"]
    )
    state_root.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
    }
    try:
        source_component = check_evaluator_identity(locator)
        candidate_root = resolve_candidate(args.candidate)
        candidate = check_candidate_identity(locator, candidate_root)
    except AssertionError as exc:
        return fail(str(exc), 3)

    manifest["eid_star"] = locator["eid_star"]
    manifest["eid_star_evaluator_source"] = source_component
    manifest["metric_name"] = metric["name"]
    manifest["candidate_identity"] = candidate
    manifest["theta_e_canonical_match"] = (
        args.fidelity == theta["fidelity"]
        and abs(args.fraction - float(theta["fraction"])) <= 1e-9
        and args.seed == int(theta["seed"])
    )

    outcome_name = (
        f"{candidate['solution_sha256'][:16]}.{args.fidelity}."
        f"{args.fraction:g}.{args.seed}.json"
    )
    outcome_path = state_root / "outcomes" / outcome_name
    outcome_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        e_star["python"],
        str(Path(e_star["dir"]) / e_star["entry"]),
        "evaluate",
        "--candidate",
        str(candidate_root),
        "--seed",
        str(args.seed),
        "--fidelity",
        args.fidelity,
        "--fraction",
        repr(float(args.fraction)),
        "--out",
        str(outcome_path),
        "--state-dir",
        str(state_root / "e_star_state"),
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command, capture_output=True, text=True, env=env, cwd=str(state_root)
    )
    (state_root / "logs").mkdir(parents=True, exist_ok=True)
    (state_root / "logs" / f"{outcome_name}.stdout").write_text(
        completed.stdout, encoding="utf-8"
    )
    (state_root / "logs" / f"{outcome_name}.stderr").write_text(
        completed.stderr, encoding="utf-8"
    )

    e_star_manifest = None
    for line in completed.stdout.splitlines():
        if line.startswith("E_STAR_MANIFEST "):
            e_star_manifest = json.loads(line[len("E_STAR_MANIFEST "):])
    if e_star_manifest is None:
        return fail(
            "E* printed no E_STAR_MANIFEST line (exit "
            f"{completed.returncode}); stderr: {completed.stderr.strip()[:400]}",
            3,
        )

    status = e_star_manifest["status"]
    manifest["items"] = max(1, int(e_star_manifest["items"]))
    manifest["total_items"] = max(1, int(e_star_manifest["total_items"]))
    manifest["e_star_status"] = status
    manifest["e_star_exit_code"] = completed.returncode
    manifest["e_star_items_audited"] = int(e_star_manifest["items"])
    manifest["e_star_evaluator_source_sha256"] = e_star_manifest[
        "evaluator_source_sha256"
    ]
    manifest["e_star_canonical_digest"] = e_star_manifest["canonical_digest"]
    manifest["e_star_outcome"] = str(
        outcome_path.relative_to(state_root)
    )
    if status == "ok":
        objective = e_star_manifest["objective"]["value"]
        manifest["score"] = float(objective)
        manifest["e_star_objective_value"] = float(objective)

    print(f"{MANIFEST_MARKER} " + json.dumps(manifest, sort_keys=True))
    if status != "ok":
        print(
            f"kapso_eval: E* verdict {status} — no score of record "
            f"(exit {EXIT_CODES[status]})",
            file=sys.stderr,
        )
    return EXIT_CODES[status]


if __name__ == "__main__":
    sys.exit(main())
