#!/usr/bin/env python
"""T1's KAPSO registered-evaluation entrypoint — the **declared stub**.

KAPSO invokes the registered command exactly as `evaluation_command()` composes it
(`maintainer.py:56-61`):

    python kapso_evaluation/kapso_eval.py --fidelity F --fraction X --seed S

with `cwd` set to the tree whose candidate is being measured (the session folder for
a session run, the branch worktree for a frame run, the workspace root for the
registration calibration). This file *is* that registered command for T1.

What it does — and it is deliberately all it does
-------------------------------------------------
1. **Evaluator identity.** Re-hash `e_star.py` and `e_star_child.py` and compare with
   the digests `EID*` recorded (via `a0_locator.json`). A mismatch aborts with exit 3
   and prints no manifest line, so the registered tree cannot silently run as a
   different E* than the one EID* names. This is the one check whose absence would
   make `EID_r` mean nothing (`HARNESS-OWNED-EVAL.md` §1: KAPSO's own triple has no
   evaluator field).
2. **Candidate report.** Report the `solution.py` the run's cwd carries, its sha256,
   and whether those bytes are a member of the frozen C*(T1). Reported, never
   enforced — see `DEVIATIONS.md` D-KT1-5: in an A1 campaign the arm writes *new*
   bytes, and refusing them would make the registered evaluation unrunnable in the
   very campaign this tree exists for.
3. **The class triple, echoed.** Print one `KAPSO_EVAL_MANIFEST` line carrying
   `fidelity`, `fraction`, `seed`, `items`, `total_items` — the five keys
   `parse_manifest_line` requires (`maintainer.py:70-79`) and the three
   `manifest_of_record` class-checks (`registered_evaluation.py:87-99`) — with the
   values **as granted on the command line**, never hardcoded.

What it does *not* do
---------------------
**It does not measure.** No E* run, no score, no `score` key on the line. In A1 the
harness owns the evaluation: `E*` is run by `a0/a1/eval_service.py` on the candidate
bytes, and the harness's own `KAPSO_EVAL_MANIFEST` line is appended to
`node.evaluation_output` *after this session ends*
(`a0/runtimes/kapso/a0_adapter/harness_manifest.py`), so the harness's line is the
last one and therefore the score of record. A line without `score` makes
`manifest_of_record` return `None` (`registered_evaluation.py:100-102`) — the honest
answer for "the runtime took no measurement" — instead of a fabricated zero.

It writes nothing: no file, no state directory, no candidate edit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCATOR_NAME = "a0_locator.json"
MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"

#: The candidate's entry point, per INTERFACE.md §3-§4 (and `a0_locator.json`
#: `candidate_abi.entry`). The stub names it only to report identity; it never runs it.
CANDIDATE_ENTRY = "solution.py"


def fail(message: str, code: int = 3) -> int:
    """Abort without printing a manifest line: the tree is not what it claims."""
    print(f"kapso_eval_t1: {message}", file=sys.stderr)
    return code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_locator() -> dict:
    path = HERE / LOCATOR_NAME
    if not path.is_file():
        raise SystemExit(
            f"kapso_eval_t1: missing locator {path}; the registered evaluation tree "
            "is not the one a0/a1/kapso_t1/build_tree.py installed"
        )
    locator = json.loads(path.read_text(encoding="utf-8"))
    if locator.get("task") != "T1-maxcut":
        raise SystemExit(
            f"kapso_eval_t1: this tree's locator names task {locator.get('task')!r}, "
            "not 'T1-maxcut'"
        )
    return locator


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
                f"{record['sha256']} recorded in EID* ({locator['eid_star']})"
            )
    return locator["eid_star_components"]["EvaluatorSource"]


def candidate_report(locator: dict, candidate_root: Path) -> dict:
    """What the run's cwd carries: the ABI entry's bytes and its C*(T1) status."""
    solution = Path(candidate_root) / CANDIDATE_ENTRY
    if not solution.is_file():
        return {
            "entry": CANDIDATE_ENTRY,
            "present": False,
            "in_frozen_set": False,
            "solution_sha256": None,
            "root": str(candidate_root),
        }
    digest = sha256_file(solution)
    member = None
    for candidate_id, entry in locator["candidate_set"]["members"].items():
        if entry.get("solution_sha256") == digest:
            member = candidate_id
            break
    return {
        "entry": CANDIDATE_ENTRY,
        "present": True,
        "in_frozen_set": member is not None,
        "candidate_id_if_frozen": member,
        "solution_sha256": digest,
        "root": str(candidate_root),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="T1 registered-evaluation stub: identity, class triple, no measurement"
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
    theta = locator["theta_e_canonical"]
    metric = locator["metric"]

    try:
        source_component = check_evaluator_identity(locator)
    except AssertionError as exc:
        return fail(str(exc), 3)

    root = Path(args.candidate).resolve() if args.candidate else Path.cwd()
    if root.is_file():
        root = root.parent

    manifest = {
        # -- the class triple, echoed from the grant (never hardcoded) --------
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
        # -- the keys `parse_manifest_line` requires, and why they are 1 ------
        # T1 has no fidelity classes and no subsampling (EID* Config
        # `theta_e_semantics`): one candidate is measured on one whole graph, so
        # `items == total_items == 1`. `items_measured` below says how many of them
        # this stub actually measured: zero.
        "items": 1,
        "total_items": 1,
        "items_measured": 0,
        # -- identity --------------------------------------------------------
        "task": locator["task"],
        "eid_star": locator["eid_star"],
        "eid_star_evaluator_source": source_component,
        "metric_name": metric["name"],
        "theta_e_canonical_match": args.seed == int(theta["seed"]),
        "theta_e_canonical_seed": int(theta["seed"]),
        "theta_e_canonical_timeout_s": float(theta["timeout_s"]),
        "candidate_identity": candidate_report(locator, root),
        # -- the honesty block: what this line is, and what it is not --------
        "measurement": "none",
        "score_omitted": (
            "the harness owns the evaluation (INTERFACE.md principle (ii), §12): E* is "
            "run by a0/a1/eval_service.py, and the harness appends its own "
            "KAPSO_EVAL_MANIFEST line — the last line — after this session ends"
        ),
        "runtime_is_the_author": False,
        "written_by": "a0/a1/kapso_t1/tree_src/kapso_eval.py",
    }

    # No `score` key: `manifest_of_record` returns None rather than a fabricated
    # number, and the harness's later line is what `node.score` becomes.
    print(f"{MANIFEST_MARKER} " + json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
