#!/usr/bin/env python3
"""Item 1c — does any committed artifact assert a superseded digest as current?

Scans the working tree for the digests that *were* current and are not any more,
and prints, per file, every line that carries one. The judgement (is the line
labelled as history?) is made by hand in REPORT.md against this listing; the
script only makes sure the listing is complete.

    python3 a0/verify/a1-final/v1b_superseded.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# digest prefix -> what it was
SUPERSEDED = {
    "cddfa64e": "EID* #1 (frozen by bfbe74c2, before the T1 fix)",
    "eccd859c": "EID* #2 (D-A1-7's re-freeze)",
    "08281d21": "E*-own digest, pre-6dd717c2",
    "4afff01f": "E*-own digest, at 6dd717c2..baf13884",
    "670f02ee": "e_star.py sha256, pre-6dd717c2",
    "fa0932b4": "e_star.py sha256, at 6dd717c2",
    "83d55e80": "e_star.py sha256, working tree at the D-A1-7 freeze",
    "013f3e33": "e_star_child.py sha256, pre-6dd717c2",
    "c08f0c36": "e_star_child.py sha256, at 6dd717c2",
    "7392915d": "e_star_child.py sha256, working tree at the D-A1-7 freeze",
}

CURRENT = ("7ce9e72f", "dc6969ec", "f67ecd41", "fdcf425c")

SKIP_DIRS = {".git", "__pycache__"}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    pattern = re.compile("|".join(SUPERSEDED))
    hits: dict[str, list[str]] = {}
    for rel in tracked_files():
        parts = Path(rel).parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        if rel.startswith(("a0/verify/a1-final/", "a0/verify/a1-testbed/")):
            continue  # this report, and the previous verifier's report
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                hits.setdefault(rel, []).append(f"{i}: {line.strip()[:200]}")

    print(f"{len(hits)} tracked files carry a superseded digest\n")
    for rel in sorted(hits):
        print(f"### {rel}  ({len(hits[rel])} line(s))")
        for line in hits[rel][:6]:
            print(f"    {line}")
        if len(hits[rel]) > 6:
            print(f"    … {len(hits[rel]) - 6} more")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
