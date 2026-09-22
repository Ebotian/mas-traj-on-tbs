#!/usr/bin/env python3
"""Byte-identical, mode-normalised mirror of the two frozen candidates.

Why this exists (see DEVIATIONS.md D-RD-1): `positive_control/{baseline,pc}/
solution.py` were `chmod +x`'d at 17:08 on 2026-09-22, *after* the gate ran at
17:03.  `e_star_child.resolve_candidate` then selects `exec_prefix = []` (run the
entry directly, because it is executable and starts with `#!`), while
`e_star.stage_candidate` copies the staged entry with `Path.write_bytes`, which
does **not** preserve the executable bit.  The spawn then fails with
`PermissionError [Errno 13]` and E* returns `candidate_entry_failed`.  The gate's
own `--force` re-run is broken by this today.

This script copies the two candidate directories into `redesign/frozen_mirror/`
with **byte-identical contents** and mode 0644 (so E* selects
`exec_prefix = [sys.executable]`, the path that worked at gate time).  Content is
the identity (`INTERFACE.md` §2: sha256 of the bytes); the file mode is not, and
the mirror's `candidate_source_sha256` is asserted equal to the frozen one, so
every Outcome produced from the mirror is directly comparable to the gate's.

    python3 gen/make_frozen_mirror.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REDESIGN = HERE.parent
TASK = REDESIGN.parent
sys.path.insert(0, str(TASK))
import e_star_child as child  # noqa: E402

SOURCES = {"baseline": TASK / "positive_control" / "baseline",
           "pc": TASK / "positive_control" / "pc"}
MIRROR = REDESIGN / "frozen_mirror"
#: the frozen digests recorded by the gate's own Outcomes
EXPECTED = {"baseline": "6bfd919ed73c49dbb27fd2eb8f1f7224fac131773d7c8e1aa1f8b6ed09b24d97",
            "pc": "d3c12b54999415a199bdcd1c9bfed715a8e28147014a14083fe0bd502be3987f"}


def main():
    report = {}
    for name, src in SOURCES.items():
        dst = MIRROR / name
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            if any(part == "__pycache__" or part.startswith(".") for part in rel.parts):
                continue
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.read_bytes())
            os.chmod(target, 0o644)
        spec = child.resolve_candidate(dst)
        got = spec["source_sha256"]
        if got != EXPECTED[name]:
            raise SystemExit(f"{name}: mirror digest {got} != frozen {EXPECTED[name]}")
        report[name] = {"mirror": str(dst.relative_to(TASK)), "source_sha256": got,
                        "exec_prefix": spec["exec_prefix"],
                        "frozen_source_sha256_match": True}
        print(f"{name}: {got[:16]}  exec_prefix={spec['exec_prefix']}  -> OK")
    (REDESIGN / "out" / "frozen_mirror.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(f"wrote {REDESIGN / 'out' / 'frozen_mirror.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
