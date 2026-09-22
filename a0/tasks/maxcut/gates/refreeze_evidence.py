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

    python3 gates/refreeze_evidence.py --before HEAD --out gates/refreeze.evidence.json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", default="HEAD",
                        help="git revision holding the previously frozen verdicts")
    parser.add_argument("--out", default=str(HERE / "refreeze.evidence.json"))
    args = parser.parse_args()

    documents = []
    for relative in verdict_files():
        current_path = MAXCUT / relative
        if not current_path.is_file():
            continue
        before = from_git(args.before, f"a0/tasks/maxcut/{relative}")
        if before is None:
            documents.append({"verdict": relative, "status": "no_frozen_copy",
                              "note": f"not present at {args.before}"})
            continue
        after = json.loads(current_path.read_text(encoding="utf-8"))
        differences = walk(before, after)
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
            "verdict_value_before": before.get("verdict"),
            "verdict_value_after": after.get("verdict"),
            "clean": not decision,
        })

    report = {
        "schema": "a0.maxcut.refreeze_evidence/v1",
        "before_revision": args.before,
        "identity_leaf_allowlist": sorted(IDENTITY_LEAVES),
        "rule": ("a re-freeze is clean when every differing leaf field is an identity field "
                 "and the verdict value is unchanged"),
        "documents": documents,
        "verdict": "CLEAN" if all(d.get("clean", True) for d in documents) else "DRIFT",
    }
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for document in documents:
        if document["status"] != "compared":
            print(f"{document['verdict']}: {document['status']} (before={args.before})")
            continue
        print(f"{document['verdict']}: {document['differing_leaf_fields']} differing leaf fields, "
              f"{len(document['identity_fields_moved'])} identity, "
              f"{len(document['decision_fields_moved'])} decision, "
              f"verdict {document['verdict_value_before']} -> {document['verdict_value_after']}")
        for record in document["identity_fields_moved"]:
            print(f"    identity  {record['field']}")
        for record in document["decision_fields_moved"]:
            print(f"    DECISION  {record['field']}: {record['before']} -> {record['after']}")
    print(f"re-freeze verdict: {report['verdict']}")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0 if report["verdict"] == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
