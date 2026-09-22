#!/usr/bin/env python3
"""Item 5b — is any superseded digest still asserted as current, anywhere committed?

The earlier verifier's §1c rejection demanded this scan; the fixes then re-stamped the
artifacts it named. This is my own scan, with my own list of what is superseded, over
every tracked file.

*Labelled* means the digest is presented as a past value: a file under a path that names
history, a line carrying the replacement value or a past marker, or — for JSON — a digest
sitting inside an object whose path names a before-side/history (a pretty-printed
`before_side` block can put the marker hundreds of lines away from the digest, so the
structural test is the one that matters).  An unlabelled digest is reported.

    python3 a0/verify/a1-delta/d6_superseded.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MY_DIR = "a0/verify/a1-delta/"
#: digests that were once the current value of an identity field, and what they were.
#: Every one is reachable in git history as the value the field held.
SUPERSEDED = {
    "cddfa64e": "EID* before the T1 fix",
    "eccd859c": "EID* at the D-A1-7 re-freeze",
    "08281d21": "E*'s own digest before 6dd717c2",
    "4afff01f": "E*'s own digest at 6dd717c2..baf13884",
    "670f02ee": "e_star.py before 6dd717c2",
    "fa0932b4": "e_star.py at 6dd717c2",
    "83d55e80": "e_star.py at the D-A1-7 freeze",
    "013f3e33": "e_star_child.py before 6dd717c2",
    "c08f0c36": "e_star_child.py at 6dd717c2",
    "7392915d": "e_star_child.py at the D-A1-7 freeze",
    "5a0c99ff": "tree/a0_locator.json before the KAPSO rebuild",
    "6b1d6fcc": "EID_r before the KAPSO rebuild",
    "fd234f69": "candidate_sandbox.py before the /tmp fix (7a1c0c16)",
}
#: the current values of the fields the list above names — the other half of a lineage line
CURRENT = ("7ce9e72f", "dc6969ec", "f67ecd41", "fdcf425c", "63a9a83c", "1e3b3a75",
           "6759ef05", "f9caa4e0")
PAST_MARKERS = ("superseded", "previous", "history", "historical", "no longer", "drifted",
                "was ", "before ", "pre-", "old ", "earlier", "→", "->", "stale")
#: JSON path components that make every digest below them a past value
LABEL_KEYS = ("before", "before_side", "history", "superseded", "previous", "old",
              "prior", "pre_fix", "raw_pre_fix", "comparison", "differs")
SKIP = {"__pycache__"}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def json_occurrences(node, pattern, path=(), parent=None, ancestors=()):
    """(path, context_text, digest) for every matching string leaf, in document order."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from json_occurrences(value, pattern, path + (str(key),), node,
                                        ancestors + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from json_occurrences(value, pattern, path + (str(index),), node, ancestors)
    elif isinstance(node, str) and pattern.search(node):
        context = json.dumps(parent)[:600] if parent is not None else ""
        yield path, "\n".join(ancestors) + "\n" + context, node


def main() -> int:
    pattern = re.compile("|".join(SUPERSEDED))
    hits: dict[str, list[tuple[int, str, bool]]] = defaultdict(list)
    scanned = 0
    for relative in tracked():
        if relative.startswith(MY_DIR) or any(p in SKIP for p in Path(relative).parts):
            continue
        if relative.startswith(("a0/verify/a1-final/", "a0/verify/a1-testbed/")):
            continue  # earlier verifiers' reports, which quote digests as history
        path = REPO / relative
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        lines = text.splitlines()
        path_labelled = any(part in ("history", "superseded", "history-attempts")
                            or part.startswith("superseded-")
                            for part in Path(relative).parts) or "history" in relative.lower()
        hit_lines = [(i + 1, line.strip()[:170]) for i, line in enumerate(lines)
                     if pattern.search(line)]

        structural: list[bool] = []
        if relative.endswith(".json"):
            try:
                document = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                document = None
            if document is not None:
                for json_path, context_text, _digest in json_occurrences(document, pattern):
                    lowered = context_text.lower()
                    in_label = any(part.lower() in LABEL_KEYS for part in json_path)
                    nearby = (any(marker in lowered for marker in PAST_MARKERS)
                              or any(part in lowered for part in
                                     ("pre_fix", "pre-fix", "comparison", "differs",
                                      "raw_pre")))
                    structural.append(in_label or nearby)

        # For prose the label has to be on the line itself (a lineage table row carries
        # both values) or on the section heading above it; a ±N-line window is too loose,
        # it labels a present-tense claim because an unrelated row nearby names the
        # current value.
        def heading_above(index):
            for candidate in range(index - 1, -1, -1):
                if lines[candidate].lstrip().startswith("#"):
                    return lines[candidate].lower()
            return ""

        for index, (lineno, line) in enumerate(hit_lines):
            own = line.lower()
            labelled = (path_labelled
                        or (structural[index] if index < len(structural) else False)
                        or any(marker in own for marker in PAST_MARKERS)
                        or any(cur in own for cur in CURRENT)
                        or any(marker in heading_above(lineno - 1) for marker in PAST_MARKERS))
            hits[relative].append((lineno, line, labelled))

    total = sum(len(v) for v in hits.values())
    unlabelled = {f: [h for h in v if not h[2]] for f, v in hits.items()}
    unlabelled = {f: v for f, v in unlabelled.items() if v}
    print(f"scanned {scanned} tracked files; {len(hits)} carry a superseded digest "
          f"({total} line(s)); {len(unlabelled)} file(s) with an unlabelled line\n")
    for relative in sorted(hits):
        label = "UNLABELLED" if relative in unlabelled else "labelled history"
        print(f"### [{label}] {relative}  ({len(hits[relative])} line(s))")
        for lineno, line, labelled in hits[relative][:4]:
            if not labelled:
                print(f"    → {lineno}: {line}")
        if len(hits[relative]) > 4:
            print(f"    … {len(hits[relative]) - 4} more")
        print()
    if unlabelled:
        print("UNLABELLED LINES:")
        for relative, rows in sorted(unlabelled.items()):
            for lineno, line, _ in rows:
                print(f"  {relative}:{lineno}: {line}")
    print(f"\nverdict: {'CLEAN' if not unlabelled else 'UNLABELLED DIGESTS REMAIN'}")
    return 1 if unlabelled else 0


if __name__ == "__main__":
    raise SystemExit(main())
