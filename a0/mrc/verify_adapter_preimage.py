#!/usr/bin/env python3
"""Recompute every `RuntimeAdapters[].adapter_source_sha256` from its preimage.

    python3 a0/mrc/verify_adapter_preimage.py

Deliberately shares no code with `mrc.py` and imports nothing from this
directory: it reads the declarations, asks `git` for the blobs the preimages
name at the recorded commit, hashes them, and applies the rule recorded in each
adapter's `adapter_source_rule`.  No network, no model calls, no credentials.

Exit 0 iff every recorded digest is reproduced from the bytes it claims.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
ROUTES = [
    "codex-deepseek-responses",
    "claude-deepseek-anthropic",
    "kilo-deepseek-chat",
    "opencode-deepseek-chat",
]
DOMAIN = b"a0/mrc/v1/RuntimeAdapters/adapter_source"


def blob(commit: str, path: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{commit}:{path}"],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git show {commit}:{path} failed: {proc.stderr.decode().strip()}")
    return proc.stdout


def digest(files: list) -> str:
    payload = json.dumps([[e["path"], e["sha256"]] for e in files],
                         sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(DOMAIN + b"\x00" + payload).hexdigest()


def main() -> int:
    bad = 0
    for route in ROUTES:
        doc = json.loads((HERE / "declarations" / f"{route}.mrc.json").read_text(encoding="utf-8"))
        for adapter in doc["components"]["RuntimeAdapters"]["adapters"]:
            commit, root = adapter["adapter_commit"], adapter["adapter_source_root"]
            listing = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "ls-tree", "-r", "--name-only", commit, "--", root],
                capture_output=True, text=True)
            if listing.returncode != 0:
                raise SystemExit(f"git ls-tree failed: {listing.stderr.strip()}")
            paths = sorted(p for p in listing.stdout.splitlines() if p)
            from_repo = [{"path": p, "sha256": hashlib.sha256(blob(commit, p)).hexdigest()}
                         for p in paths]
            recorded = adapter["adapter_source_sha256"]
            got = digest(from_repo)
            in_declaration = from_repo == adapter["adapter_source_files"]
            ok = got == recorded and in_declaration
            bad += not ok
            print(f"[{'ok  ' if ok else 'BAD '}] {route:<28} {adapter['runtime']:<11} "
                  f"{root:<40} {len(paths):>2} files  {got}")
            if not in_declaration:
                print("       the recorded manifest is not the repo's file set at "
                      f"{commit}: {root}")
            elif got != recorded:
                print(f"       recorded={recorded} recomputed={got}")
    print("every adapter digest is reproduced from its preimage" if not bad
          else f"{bad} adapter digest(s) NOT reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
