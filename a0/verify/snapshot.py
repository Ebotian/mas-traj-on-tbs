#!/usr/bin/env python3
"""Snapshot (path, size, mtime_ns) for a tree, so an adversarial re-run can prove
which files it touched outside its own directory."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SKIP = {".git", ".venv", ".venv-tools", ".uvcache", "node_modules", "__pycache__", ".pytest_cache"}


def snap(root: Path):
    out = {}
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            p = Path(dp) / fn
            try:
                st = p.lstat()
            except OSError:
                continue
            rel = str(p.relative_to(root))
            out[rel] = [st.st_size, st.st_mtime_ns]
    return out


if __name__ == "__main__":
    root = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    dest.write_text(json.dumps(snap(root)))
    print(f"snapshot {root} -> {dest}: {len(json.loads(dest.read_text()))} files")
