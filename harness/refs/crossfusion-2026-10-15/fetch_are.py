#!/usr/bin/env python3
"""fetch_are.py — stage the pinned AutoResearchEval release into harbor-runs/data.

Revision-pinned (412fb490…), resume-capable (curl -C - with an outer retry loop),
size-verified against the HF tree listing. Re-runnable: files already present with
the expected size are skipped. This machine's huggingface.co route breaks large
transfers mid-flight (see memory hf-transfer-curl-retry-resume), hence the loop.

Layout:
  /home/ebt/harbor-runs/data/autoresearch-eval/_meta/{revision.txt,tree.json,fetch.log}
  /home/ebt/harbor-runs/data/autoresearch-eval/<dataset-tree paths…>

Usage: python3 fetch_are.py
Exit 0 iff every file is present at the exact expected size.
"""
import concurrent.futures as cf
import json
import subprocess
import sys
import time
from pathlib import Path

REV = "412fb4908a3a7b98dd50cfa3e5c6cd40750d2d4f"
DST = Path("/home/ebt/harbor-runs/data/autoresearch-eval")
META = DST / "_meta"
BASE = f"https://huggingface.co/datasets/PrentisAI/AutoResearchEval/resolve/{REV}/"
TREE_URL = (
    f"https://huggingface.co/api/datasets/PrentisAI/AutoResearchEval/tree/{REV}?recursive=true"
)
WORKERS = 4
ATTEMPTS = 6


def fetch_tree() -> list:
    out = subprocess.run(
        ["curl", "--http1.1", "-fsSL", "--retry", "5", "--retry-delay", "3", TREE_URL],
        capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"tree fetch failed rc={out.returncode}")
    data = json.loads(out.stdout)
    META.mkdir(parents=True, exist_ok=True)
    (META / "tree.json").write_bytes(out.stdout)
    return data


def one(entry: dict) -> tuple:
    path, size = entry["path"], entry.get("size") or 0
    dest = DST / path
    if dest.exists() and dest.stat().st_size == size:
        return (path, "skip", size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    for a in range(1, ATTEMPTS + 1):
        subprocess.run(
            [
                "curl", "--http1.1", "-sSL",
                "--connect-timeout", "20",
                "--speed-limit", "1024", "--speed-time", "90",
                "--retry", "3", "--retry-delay", "2", "--retry-all-errors",
                "-C", "-", "-o", str(dest), BASE + path,
            ]
        )
        if dest.exists() and dest.stat().st_size == size:
            return (path, f"ok{a}", size)
        time.sleep(min(30, 3 * a))
    return (path, "FAIL", size)


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    (META / "revision.txt").write_text(REV + "\n")
    data = fetch_tree()
    files = [e for e in data if e.get("type") == "file"]
    total = sum(e.get("size") or 0 for e in files)
    print(f"files={len(files)} bytes={total}", flush=True)
    done = bad = 0
    with cf.ThreadPoolExecutor(WORKERS) as ex, open(META / "fetch.log", "a") as log:
        for path, status, size in ex.map(one, files):
            done += 1
            if status.startswith("FAIL"):
                bad += 1
            log.write(f"{status}\t{path}\t{size}\n")
            log.flush()
            if done % 50 == 0 or status.startswith("FAIL"):
                print(f"[{done}/{len(files)}] {status} {path}", flush=True)
    have = sum(
        1
        for e in files
        if (DST / e["path"]).exists() and (DST / e["path"]).stat().st_size == (e.get("size") or 0)
    )
    on_disk = sum(
        (DST / e["path"]).stat().st_size for e in files if (DST / e["path"]).exists()
    )
    print(f"done={done} bad={bad} present_ok={have}/{len(files)}", flush=True)
    print(f"bytes_on_disk={on_disk} expected={total}", flush=True)
    return 0 if bad == 0 and have == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
