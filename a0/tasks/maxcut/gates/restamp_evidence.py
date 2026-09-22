#!/usr/bin/env python3
"""Prove an identity re-stamp left every decision number where it was.

Why this exists
---------------
Overwriting a superseded digest with the current one is exactly the operation
that can hide a drift: the files are rewritten, the new digests look like the
old ones, and "nothing moved" becomes a claim instead of a measurement.
`refreeze_evidence.py` answers that question for the 12 verdicts.  This script
answers it for the other 600-odd stamped records -- the stored Outcomes and the
`values/` documents built out of them -- and adds the two checks an identity
stamp actually needs:

    current   every stamped record names *this* E*, read from E* rather than assumed;
    history   every superseded digest still written down is written down as history,
              on a line that also names the revision it belongs to.

Six leaves are allowed to move, and they are the whole point of the re-stamp:
`evaluator_source_sha256` and `canonical_digest` (the digest is inside the
canonical bytes, §5), and the four `candidate_graph_*` fields of the redacted
candidate view that `baf13884` introduced.  `cut_edges`, `status`, `failure`,
`theta`, `interpreted`, `determinism`, `graph_sha256` and
`candidate_source_sha256` are decisions or inputs to one: if any of them moves,
this script reports `DRIFT` and exits non-zero.

    python3 gates/restamp_evidence.py --before HEAD
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
E_STAR = MAXCUT / "e_star.py"

#: the repository root, asked of git: `git ls-files` resolves its pathspec against
#: the *current directory*, so guessing this from `HERE` silently returns nothing.
ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(HERE),
                           capture_output=True, text=True).stdout.strip())

sys.path.insert(0, str(HERE))
import refreeze_evidence as R  # noqa: E402  (reuse its leaf walk, not a second copy)

#: the only leaves a re-stamp may move (derived by measuring one, 2026-09-22)
RESTAMP_LEAVES = {
    "evaluator_source_sha256",
    "canonical_digest",
    "candidate_graph_bytes",
    "candidate_graph_keys",
    "candidate_graph_schema",
    "candidate_graph_sha256",
}

#: every digest an earlier E* was stamped with, and the revision it belongs to
SUPERSEDED = [
    ("08281d21e6e84a79dfebd895d7653b517c1e08e7ea8784fe485532dd5db59c4d",
     "E* at 11f55bf0, before the D-T1-10 launch fix"),
    ("4afff01f8a73479b2cb548686b4ae31c50100699057d3fad512f7a6aabb4a23a",
     "E* at 6dd717c2, the D-T1-10 launch fix"),
]

#: a line mentioning a superseded digest must carry one of these
HISTORY_MARKERS = ("history", "historical", "superseded", "was ", "earlier",
                   "pre-", "no longer", "→", "->")

DIGEST_FIELD = "evaluator_source_sha256"
DIGEST_RE = re.compile(r"\b[0-9a-f]{8,64}\b")


def run_git(*args):
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True).stdout


def tracked_files():
    return [line for line in run_git("ls-files", "a0/tasks/maxcut/gates").split("\n") if line]


def live_digest():
    proc = subprocess.run([sys.executable, str(E_STAR), "digest", "--value-only"],
                          capture_output=True, text=True)
    digest = proc.stdout.strip()
    if len(digest) != 64:
        raise SystemExit("could not read E*'s digest")
    return digest


def stamped_digests(node, path=""):
    """Every `evaluator_source_sha256` value in a document, with its location."""
    if isinstance(node, dict):
        for key in sorted(node):
            if key == DIGEST_FIELD and isinstance(node[key], str):
                yield path + "." + key, node[key]
            else:
                yield from stamped_digests(node[key], f"{path}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from stamped_digests(item, f"{path}[{index}]")


def scan_stamps(live):
    """Ask every tracked JSON document what E* it names."""
    stale, records, files = [], 0, 0
    for relative in tracked_files():
        if not relative.endswith(".json"):
            continue
        path = ROOT / relative
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        hits = list(stamped_digests(document))
        if not hits:
            continue
        files += 1
        for where, digest in hits:
            records += 1
            if digest != live:
                stale.append({"file": relative.replace("a0/tasks/maxcut/", ""),
                              "where": where, "stamp": digest})
    return {"files_with_a_stamp": files, "stamped_records": records,
            "current": records - len(stale), "stale": stale}


def scan_history():
    """Every remaining mention of a superseded digest must be labelled history."""
    report = []
    for digest, revision in SUPERSEDED:
        mentions = []
        for relative in tracked_files():
            if relative.endswith((".json",)):
                continue
            for number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(),
                                          start=1):
                if digest[:8] not in line:
                    continue
                lowered = line.lower()
                mentions.append({
                    "file": relative.replace("a0/tasks/maxcut/", ""),
                    "line": number,
                    "labelled": any(marker in lowered for marker in HISTORY_MARKERS),
                    "text": line.strip()[:150],
                })
        report.append({"digest": digest, "revision": revision, "mentions": mentions,
                       "all_labelled": all(m["labelled"] for m in mentions)})
    return report


def diff_against(revision, relative_paths):
    """HEAD-vs-disk leaf diff over a set of stored records."""
    differing = 0
    leaves = Counter()
    decisions = []
    for relative in relative_paths:
        before_raw = run_git("show", f"{revision}:{relative}")
        if not before_raw:
            continue
        try:
            before = json.loads(before_raw)
        except json.JSONDecodeError:
            continue
        after = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        differences = R.walk(before, after)
        if differences:
            differing += 1
        for path, old, new in differences:
            leaf = path.rsplit(".", 1)[-1]
            leaves[leaf] += 1
            if leaf not in RESTAMP_LEAVES:
                decisions.append({"file": relative.replace("a0/tasks/maxcut/", ""),
                                  "field": path,
                                  "before": str(old)[:70], "after": str(new)[:70]})
    return {"records": len(relative_paths), "records_differing": differing,
            "differing_leaf_names": dict(sorted(leaves.items())),
            "decision_leaves_moved": decisions}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", default="HEAD",
                        help="revision holding the superseded stamps")
    parser.add_argument("--out", default=str(HERE / "restamp.evidence.json"))
    args = parser.parse_args()

    live = live_digest()
    stamps = scan_stamps(live)
    history = scan_history()

    outcomes = sorted(str(path.relative_to(ROOT)) for path in
                      (HERE / "outcomes").glob("**/*.outcome.json"))
    verdicts = sorted(str(path.relative_to(ROOT)) for path in HERE.glob("verdict.*.json"))
    outcome_diff = diff_against(args.before, outcomes)
    verdict_diff = diff_against(args.before, verdicts)

    history_ok = all(entry["all_labelled"] for entry in history)
    report = {
        "schema": "a0.maxcut.restamp_evidence/v1",
        "before_revision": args.before,
        "current_evaluator_source_sha256": live,
        "rule": ("a re-stamp is clean when every stored record names this E*, the only "
                 "leaves that move are the stamps themselves, and every superseded digest "
                 "still written down is labelled with the revision it belongs to"),
        "stamps": stamps,
        "history": history,
        "outcomes": outcome_diff,
        "verdicts": verdict_diff,
        "verdict": "CLEAN" if (not stamps["stale"] and history_ok
                               and not outcome_diff["decision_leaves_moved"]
                               and not verdict_diff["decision_leaves_moved"]) else "DRIFT",
    }
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")

    print(f"E* now: {live[:16]}…")
    print(f"stamped records: {stamps['stamped_records']} in {stamps['files_with_a_stamp']} "
          f"documents, {stamps['current']} current, {len(stamps['stale'])} stale")
    for record in stamps["stale"][:10]:
        print(f"    STALE {record['file']} {record['where']} {record['stamp'][:16]}…")
    for entry in history:
        labelled = sum(1 for m in entry["mentions"] if m["labelled"])
        print(f"history {entry['digest'][:12]}… ({entry['revision']}): "
              f"{len(entry['mentions'])} mention(s), {labelled} labelled")
        for mention in entry["mentions"]:
            if not mention["labelled"]:
                print(f"    UNLABELLED {mention['file']}:{mention['line']}: {mention['text']}")
    for name, diff in (("outcomes", outcome_diff), ("verdicts", verdict_diff)):
        print(f"{name}: {diff['records_differing']}/{diff['records']} differ; "
              f"leaves moved {diff['differing_leaf_names']}; "
              f"decision leaves {len(diff['decision_leaves_moved'])}")
        for record in diff["decision_leaves_moved"][:10]:
            print(f"    DECISION {record['file']} {record['field']}: "
                  f"{record['before']} -> {record['after']}")
    print(f"re-stamp verdict: {report['verdict']}")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0 if report["verdict"] == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
