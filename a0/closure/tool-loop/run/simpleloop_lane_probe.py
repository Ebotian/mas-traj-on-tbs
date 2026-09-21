#!/usr/bin/env python3
"""Run SimpleLoop's SHIPPED solver-lane argv with the closure-probe prompt.

The argv is not retyped here: it is built by `a0_adapter.solvers.CliSolver._command`
from the substrate's own code, so this probe cannot drift from the lane the study
ships (`["codex", "exec", "--sandbox", "workspace-write", "--skip-git-repo-check",
prompt]`). Run inside the worker container; the model endpoint then comes from the
container's network posture (CODEX_HOME / HTTPS_PROXY) exactly as it does for the
adapter.

    python3 simpleloop_lane_probe.py --tag <TAG> --prompt <file>

stdout is the agent's transcript; the exit code is the lane's.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ADAPTER_DIR = Path(os.environ.get("A0SL_ADAPTER", "/home/ebt/rsi-dev/a0/runtimes/simpleloop"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--out-root", default="/work/runs")
    args = parser.parse_args()

    sys.path.insert(0, str(ADAPTER_DIR))
    from a0_adapter.solvers import CliSolver  # noqa: PLC0415 - after sys.path setup

    run_dir = Path(args.out_root) / args.tag
    work_dir = run_dir / "wd"
    work_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.prompt).read_text(encoding="utf-8").replace("__TAG__", args.tag)

    solver = CliSolver("codex", work_dir, timeout_s=args.timeout)
    cmd = solver._command(prompt)  # noqa: SLF001 - the point is the shipped argv

    print("SHIPPED_ARGV %r" % (cmd[:len(cmd) - 1],), flush=True)
    started = time.monotonic()
    timed_out = False
    with (work_dir / "lane.stdout.txt").open("wb") as out_fh, \
            (work_dir / "lane.stderr.txt").open("wb") as err_fh:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out_fh, stderr=err_fh,
                                cwd=str(work_dir))
        try:
            rc = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            rc = proc.wait()
    wall = time.monotonic() - started
    print("LANE_EXIT rc=%d timed_out=%s wall_sec=%.1f" % (rc, timed_out, wall), flush=True)
    # `codex exec` writes its session transcript to stderr and the final message
    # to stdout; both are part of the record, so both are printed.
    print("---- stdout ----")
    print((work_dir / "lane.stdout.txt").read_text(encoding="utf-8", errors="replace"))
    print("---- stderr ----")
    print((work_dir / "lane.stderr.txt").read_text(encoding="utf-8", errors="replace"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
