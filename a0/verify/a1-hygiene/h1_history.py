#!/usr/bin/env python3
"""Check that no stale evaluator digest in this pass's scope is unlabelled.

Two claims, both machine-checked:

A. `a0/tasks/maxcut/redesign/out/HISTORY.json` lists **exactly** the Outcome files
   under `redesign/out/**` that carry a superseded `evaluator_source_sha256`, and
   its path list hashes to the digest it records. This is the marker an automated
   scan reads, so "the 276 files are labelled" is a lookup, not a guess.

B. Every line in `a0/a1/**` (outside `kapso_t1/`, which has its own labelled
   history directory) and `a0/tasks/maxcut/redesign/**` that carries a
   once-current digest is either labelled — by line-scoped wording, or (for JSON
   under `redesign/out/`) structurally, by being listed in `HISTORY.json` — or is
   one of two named, frozen exceptions.

The digest list is this pass's own (the seven once-current values it can name plus
the dangling commit the hostile probe cited). It is deliberately explicit rather
than clever: the point is that a *reader* can see every hit and its label.

    python3 a0/verify/a1-hygiene/h1_history.py [--root .]

Exit 0 iff A and B pass. Nothing is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SUPERSEDED = {
    "08281d21": "E* composite at 11f55bf0 (the redesign study's evaluator)",
    "4afff01f": "E* composite at 6dd717c2 / 75403e8c (the pinned pre-fix evaluator)",
    "cddfa64e": "EID* before the second re-freeze",
    "eccd859c": "EID* before the final re-freeze",
    "5a0c99ff": "tree/a0_locator.json before the KAPSO tree rebuild",
    "6b1d6fcc": "EID_r before the KAPSO tree rebuild",
    "fd234f69": "a0/a1/candidate_sandbox.py before D-A1-14",
    "654d5da2": "the pre-amend 7a1c0c16, reached by no ref (a commit, not a digest)",
}

CURRENT = ("dc6969ec", "7ce9e72f", "63a9a83c", "1e3b3a75", "f9caa4e0", "d069766f",
           "11f55bf0", "670f02ee", "013f3e33", "75403e8c")

MARKERS = ("→", "->", "was ", "history", "historical", "superseded", "pre-rebuild",
           "pre-fix", "before that", "no ref reaches", "dangling", "moved",
           "old ", "earlier", "previous", "not edited", "wrote", "supersede",
           "carried")

#: A digest is written either in full (64 hex) or abbreviated as its first eight
#: characters plus "…". Matching *only* those two shapes keeps a candidate
#: directory named by a 16-character hash prefix from reading as a digest.
_HIT = {digest: re.compile(r"(?<![0-9a-f])" + digest + r"(?:[0-9a-f]{56})?(?![0-9a-f])")
        for digest in SUPERSEDED}
_CURRENT = re.compile("(?<![0-9a-f])(" + "|".join(CURRENT) + r")[0-9a-f]{0,56}(?![0-9a-f])")

#: Files whose stale digest is real and **must not be edited**, so the label lives
#: somewhere else — or, for the frozen procedure, cannot exist in the file at all.
#: Each entry has to say where the reader is told, so the exception is auditable
#: rather than silent.
EXCEPTIONS = {
    "a0/a1/calibration/pilot_procedure.json":
        "FROZEN, deliberately unlabelled in place. The pre-registration; B_hard.json "
        "pins its sha256 (procedure.json_sha256 = 8fcc8795…), so correcting line 69 "
        "would re-freeze B_hard. Labelled in a0/a1/DEVIATIONS.md D-A1-15.",
    "a0/a1/evidence/hostile_candidate.json":
        "the leaves carry the *pinned pre-fix* evaluator's own digest (75403e8c), "
        "written by that evaluator when it ran. Labelled by the enclosing "
        "before_side / evaluator_used_for_the_comparison record, which names the "
        "revision and says it differs from HEAD. See a0/verify/a1-hygiene/"
        "DEVIATIONS.md D-HYG-9.",
    "a0/a1/calibration/evidence/kapso/pilot_arm.json":
        "PAID ARTIFACT, not this pass's. The line carries the pre-D-A1-14 sandbox "
        "module digest; labelling it in place would falsify the pilot's own record. "
        "Labelled by a0/a1/DEVIATIONS.md D-A1-14 §1, which names this file, the "
        "digest and the reason.",
    "a0/a1/calibration/evidence/simpleloop/pilot_arm.json":
        "PAID ARTIFACT, not this pass's. Same digest, same reason as the kapso arm: "
        "labelled by a0/a1/DEVIATIONS.md D-A1-14 §1.",
    "a0/a1/kapso_t1/DEVIATIONS.md":
        "another workstream's log. Line 159 is the continuation of the sentence in "
        "D-KT1-8 whose before/after table names both values, so the line is labelled "
        "by its own sentence and section.",
}

SCAN_ROOTS = ("a0/a1", "a0/tasks/maxcut/redesign")


def tracked_files(root: Path):
    out = subprocess.run(["git", "ls-files", "-z", "--", *SCAN_ROOTS],
                         cwd=str(root), capture_output=True, check=True).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def history_index(root: Path):
    path = root / "a0/tasks/maxcut/redesign/out/HISTORY.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def check_a(root: Path) -> bool:
    path, record = history_index(root)
    listed = sorted(entry["path"] for entry in record["files"])
    sup = set(record["superseded_evaluator_source_sha256"])
    out_dir = path.parent
    found = []
    for candidate in sorted(out_dir.rglob("*.outcome.json")):
        document = json.loads(candidate.read_text(encoding="utf-8"))
        if document.get("evaluator_source_sha256") in sup:
            found.append(str(candidate.relative_to(out_dir)))
    ok_equal = listed == sorted(found)
    ok_digest = (hashlib.sha256(("\n".join(sorted(found)) + "\n").encode()).hexdigest()
                 == record["files_sha256"])
    print(f"A. {path.relative_to(root)}: listed {len(listed)}, found {len(found)}, "
          f"exhaustive {ok_equal}, path-list digest {ok_digest}")
    print(f"   superseded: {', '.join(sorted(sup))}")
    print(f"   current   : {record['current_evaluator_source_sha256']}")
    print(f"   measured against {record['measured_against']['revision']} "
          f"({record['measured_against']['current_from']} .. "
          f"{record['measured_against']['current_until']})")
    return ok_equal and ok_digest


def check_b(root: Path) -> bool:
    _, record = history_index(root)
    structurally_labelled = {f"a0/tasks/maxcut/redesign/out/{entry['path']}"
                             for entry in record["files"]}
    files = tracked_files(root)
    unlabelled, exceptions, labelled_files, total_hits = [], [], [], 0
    for name in files:
        path = root / name
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        hits = [(n, line) for n, line in enumerate(lines, 1)
                if any(pattern.search(line) for pattern in _HIT.values())]
        if not hits:
            continue
        total_hits += len(hits)
        if name in structurally_labelled:
            labelled_files.append((name, len(hits), "listed in out/HISTORY.json"))
            continue
        if "history" in Path(name).parts:
            labelled_files.append((name, len(hits), "under a .../history/ directory"))
            continue
        if name in EXCEPTIONS:
            exceptions.append((name, len(hits), EXCEPTIONS[name]))
            continue
        bad = []
        for number, line in hits:
            window = "\n".join(lines[max(0, number - 4):number + 3])
            if _CURRENT.search(line):
                continue
            if any(marker in window for marker in MARKERS):
                continue
            bad.append((number, line.strip()))
        if bad:
            unlabelled.append((name, bad))
        else:
            labelled_files.append((name, len(hits),
                                   "named the current value / labelled wording"))
    print("\nB. once-current digests in a0/a1/** and redesign/**")
    print(f"   {len(files)} tracked files scanned; {total_hits} digest-carrying lines "
          f"in {len(labelled_files) + len(exceptions) + len(unlabelled)} files")
    for name, count, why in labelled_files:
        print(f"   labelled    {count:4d}  {name}   [{why}]")
    for name, count, why in exceptions:
        print(f"   exception   {count:4d}  {name}\n                        {why}")
    for name, bad in unlabelled:
        print(f"   UNLABELLED  {len(bad):4d}  {name}")
        for number, line in bad:
            print(f"                        {name}:{number}: {line[:140]}")
    return not unlabelled


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="a1-hygiene.h1_history")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    a = check_a(root)
    b = check_b(root)
    verdict = "pass" if (a and b) else "fail"
    print(f"\nverdict: {verdict}")
    return 0 if verdict == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
