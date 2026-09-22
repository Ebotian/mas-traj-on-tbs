#!/usr/bin/env python3
"""Prove a re-freeze moved identity fields and no decision fields.

Re-freezing is what §12 requires when a dependency or `theta` changes, and it is
also the moment when a real drift could hide: the files are regenerated, so the
new digests look like the old ones and nobody diffs them.  This script diffs them.

It compares a verdict as committed (or as stored anywhere) against the verdict on
disk now, at the level of leaf fields, and separates the two classes:

    identity fields  -- digests, theta, paths: expected to move, and to be the
                        only thing that moves
    decision fields  -- rows, gate reductions, counts, verdict: must not move

The default `--before` is the pre-re-freeze revision the committed evidence
records, not `HEAD`: after the re-freeze has landed, `HEAD` compares the re-frozen
verdicts with themselves, reports 0 differing leaf fields for every verdict, calls
that `CLEAN`, and rewrites the committed evidence with the emptier report.  If the
comparison window is empty the command refuses (exit 2) and writes nothing.

    python3 gates/refreeze_evidence.py --before 7bf8a14b --out gates/refreeze.evidence.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
ROOT = MAXCUT.parent.parent

#: leaf-field names that are allowed to move in a re-freeze.  Anything else is a
#: decision change and is reported as a failure.
IDENTITY_LEAVES = {
    "evaluator_source_sha256", "candidate_source_sha256", "pc_source_sha256",
    "baseline_source_sha256", "gate_config_sha256", "canonical_digest",
    "raw_bytes_identical", "sha256", "timeout_s", "path", "exit_codes",
    "graph_sha256",
}

def verdict_files():
    """Every verdict this directory has issued, not a hand-kept subset.

    The list used to name three files; the sixth positive control's verdicts were
    then outside the diff, which is the one place a stale digest could hide
    unchecked.  Globbing the directory keeps the evidence complete as verdicts
    are added.
    """
    return sorted(f"gates/{path.name}" for path in HERE.glob("verdict.*.json"))


def walk(before, after, path=""):
    out = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if key not in before:
                out.append((f"{path}.{key}", "<absent>", "added"))
            elif key not in after:
                out.append((f"{path}.{key}", "removed", "<absent>"))
            else:
                out += walk(before[key], after[key], f"{path}.{key}")
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            out.append((path, f"len {len(before)}", f"len {len(after)}"))
        else:
            for index, (x, y) in enumerate(zip(before, after)):
                out += walk(x, y, f"{path}[{index}]")
    elif before != after:
        out.append((path, before, after))
    return out


def from_git(revision, relative_path):
    proc = subprocess.run(["git", "show", f"{revision}:{relative_path}"],
                          cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def recorded_before(path):
    """The pre-re-freeze revision the evidence artifact at `path` records, if any."""
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return record.get("before_revision") or None


def resolve_revision(revision):
    """The commit `revision` names, or `None` when this repository has no such revision."""
    proc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", f"{revision}^{{commit}}"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", default=None,
                        help="git revision holding the previously frozen verdicts; defaults to "
                             "the pre-re-freeze revision the evidence artifact records")
    parser.add_argument("--out", default=str(HERE / "refreeze.evidence.json"))
    args = parser.parse_args()

    before = args.before
    if before is None:
        # The committed evidence is the authority on the revision the re-freeze moved
        # off, not `--out` (which may be a scratch path).
        recorded = HERE / "refreeze.evidence.json"
        before = recorded_before(recorded)
        if before is None:
            print(f"refusing: no --before given and none recorded in {recorded}; pass the "
                  "revision the re-freeze moved off, e.g. --before 7bf8a14b", file=sys.stderr)
            return 2
        print(f"no --before given; using the revision {recorded.name} records: {before}")
    if resolve_revision(before) is None:
        print(f"refusing: {before!r} is not a revision in {ROOT}", file=sys.stderr)
        return 2

    documents = []
    for relative in verdict_files():
        current_path = MAXCUT / relative
        if not current_path.is_file():
            continue
        frozen = from_git(before, f"a0/tasks/maxcut/{relative}")
        if frozen is None:
            documents.append({"verdict": relative, "status": "no_frozen_copy",
                              "note": f"not present at {before}"})
            continue
        after = json.loads(current_path.read_text(encoding="utf-8"))
        differences = walk(frozen, after)
        identity, decision = [], []
        for path, old, new in differences:
            leaf = path.rsplit(".", 1)[-1]
            record = {"field": path,
                      "before": old if not isinstance(old, str) or len(old) < 80 else old[:77] + "…",
                      "after": new if not isinstance(new, str) or len(new) < 80 else new[:77] + "…"}
            (identity if leaf in IDENTITY_LEAVES else decision).append(record)
        documents.append({
            "verdict": relative,
            "status": "compared",
            "differing_leaf_fields": len(differences),
            "identity_fields_moved": identity,
            "decision_fields_moved": decision,
            "verdict_value_before": frozen.get("verdict"),
            "verdict_value_after": after.get("verdict"),
            "clean": not decision,
        })

    for document in documents:
        if document["status"] != "compared":
            print(f"{document['verdict']}: {document['status']} (before={before})")
            continue
        print(f"{document['verdict']}: {document['differing_leaf_fields']} differing leaf fields, "
              f"{len(document['identity_fields_moved'])} identity, "
              f"{len(document['decision_fields_moved'])} decision, "
              f"verdict {document['verdict_value_before']} -> {document['verdict_value_after']}")
        for record in document["identity_fields_moved"]:
            print(f"    identity  {record['field']}")
        for record in document["decision_fields_moved"]:
            print(f"    DECISION  {record['field']}: {record['before']} -> {record['after']}")

    # `--before HEAD` (the old default) compares the re-frozen verdicts with
    # themselves once the re-freeze has landed: 0 differing leaf fields for every
    # verdict, `CLEAN`.  A window in which nothing moved cannot show that a
    # re-freeze was clean, so an empty window is a refusal, and nothing is written.
    if not any(document.get("differing_leaf_fields", 0) for document in documents):
        print(f"re-freeze verdict: REFUSED — the comparison window against {before} is empty "
              f"(0 differing leaf fields across {len(documents)} verdicts). Pass the revision "
              "the re-freeze moved off.")
        print(f"nothing written to {args.out}", file=sys.stderr)
        return 2

    report = {
        "schema": "a0.maxcut.refreeze_evidence/v1",
        "before_revision": before,
        "identity_leaf_allowlist": sorted(IDENTITY_LEAVES),
        "rule": ("a re-freeze is clean when every differing leaf field is an identity field "
                 "and the verdict value is unchanged"),
        "documents": documents,
        "verdict": "CLEAN" if all(d.get("clean", True) for d in documents) else "DRIFT",
    }
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"re-freeze verdict: {report['verdict']}")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0 if report["verdict"] == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
