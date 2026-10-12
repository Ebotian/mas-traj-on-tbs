#!/usr/bin/env python3
"""PreToolUse round gate for the dual-agent runs (hybrid wait).

Hook contract (qwen-code 0.25.1, pinned 726e8d77; event set + exit-2/non-blocking
strings re-checked against the 0.25.1 bundle 2026-10-12):
- PreToolUse command hooks run BEFORE the tool call and are awaited; a commit
  attempt is therefore held open while this script waits.
- Exit 0 = allow; exit 2 = BLOCK with the stderr text as the reason.
- A timed-out hook is classified non-blocking (exit 124) and would PASS the
  tool, so the gate must exit cleanly before its hook `timeout` (set to 940 s
  in settings.json; internal budget is 3 x 300 s windows + checks).

Barrier rule: a commit whose message carries `Round: N` (N >= 2) from actor X
is allowed only once the peer has published `Round: N-1`
(/root/wt/x/ready-<peer>.round, written by the git post-commit hook).
Between windows the peer is liveness-checked (PID + its session JSONL mtime);
a dead or stalled peer exits 2 early ("peer-stalled"), three quiet windows
exit 2 ("exhausted"). Everything else passes instantly.

Evidence-reference gate (full-course, 2026-10-11): EVERY `(Round: N)` commit
first runs `refs.py check` for the committing actor; any BROKEN reference
exits 2 immediately (before the barrier — a broken ledger is a local defect,
waiting cannot fix it). Conservative asymmetry: only positively-broken refs
block; a missing or crashing checker degrades to fail-OPEN with a loud
`refs-skip` log line (a checker bug must never brick the run).
"""
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import time

X = pathlib.Path(os.environ.get("WT_X", "/root/wt/x"))
WINDOW_SEC = int(os.environ.get("WT_WINDOW_SEC", "300"))
WINDOWS = 3
STALE_AFTER_SEC = int(os.environ.get("WT_STALE_SEC", "360"))
WT_ROOT = pathlib.Path(os.environ.get("WT_ROOT", "/root/wt"))
REFS_TOOL = os.environ.get("WT_REFS_TOOL") or str(WT_ROOT / "refs.py")


def refs_check(actor: str, rnd: int) -> tuple:
    """(status, line): ok | block | skip(why).  skip = fail-open."""
    refs = WT_ROOT / actor / f"refs-{actor}.jsonl"
    try:
        r = subprocess.run(
            [sys.executable, REFS_TOOL, "--actor", actor, "--refs", str(refs),
             "--round", str(rnd), "check"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as e:
        return "skip", f"checker unusable: {e!r}"
    summary, broken = "", []
    for line in (r.stdout or "").splitlines():
        if line.startswith("refs check"):
            summary = line
        elif line.strip().startswith("BROKEN"):
            broken.append(line.strip())
    if r.returncode == 0:
        return "ok", summary or "no ledger"
    if r.returncode == 1:
        return "block", "; ".join(broken)[:300] or (summary or "broken refs")
    return "skip", f"checker rc={r.returncode}: {(r.stderr or '').strip()[:160]}"


def read_round(p: pathlib.Path) -> int:
    try:
        return int(p.read_text().strip())
    except Exception:
        return -1


def log(msg: str) -> None:
    try:
        with open(X / "gate.log", "a") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def peer_alive(actor: str) -> bool | None:
    """True alive, False dead, None unknown (no pid record yet)."""
    try:
        pid = int((X / f"pid-{actor}").read_text().strip())
    except Exception:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        uu = (X / f"session-{actor}.uuid").read_text().strip()
    except Exception:
        return True
    if not uu:
        return True
    files = glob.glob(f"/root/.qwen/projects/*/chats/{uu}.jsonl")
    if not files:
        return True  # no transcript yet: give the benefit of the doubt
    age = time.time() - max(os.path.getmtime(f) for f in files)
    return age < STALE_AFTER_SEC


def wait_event(secs: int) -> bool:
    """Block up to `secs` on a filesystem event in X (kernel-side wait)."""
    try:
        r = subprocess.run(
            ["inotifywait", "-q", "-t", str(secs),
             "-e", "close_write", "-e", "moved_to", "-e", "create", str(X)],
            capture_output=True,
        )
        return r.returncode == 0
    except FileNotFoundError:
        # No inotifywait: single bounded nap, then re-check (never a tight loop).
        time.sleep(min(secs, 20))
        return False


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except Exception:
        sys.exit(0)
    if payload.get("hook_event_name") != "PreToolUse":
        sys.exit(0)
    ti = payload.get("tool_input") or {}
    cmd = str(ti.get("command") or "")
    if "git commit" not in cmd:
        sys.exit(0)
    m = re.search(r"Round:\s*(\d+)", cmd)
    if not m:
        sys.exit(0)
    need_for_me = int(m.group(1))
    actor = ""
    sid = str(payload.get("session_id") or "")
    if sid:
        for cand in ("a", "b"):
            try:
                if sid == (X / f"session-{cand}.uuid").read_text().strip():
                    actor = cand
            except Exception:
                pass
    if not actor:
        cwd = str(ti.get("cwd") or payload.get("cwd") or "")
        actor = pathlib.Path(cwd).name if pathlib.Path(cwd).name in ("a", "b") else ""
    if not actor:
        mm = re.search(r"/root/wt/([ab])\b", cmd)
        actor = mm.group(1) if mm else ""
    if not actor:
        sys.exit(0)

    # Evidence-reference gate: applies to EVERY round commit, before the
    # barrier (a broken local ledger should not wait on the peer).
    status, why = refs_check(actor, need_for_me)
    if status == "block":
        log(f"refs-block actor={actor} Round={need_for_me}: {why[:220]}")
        print(
            f"gate: evidence references broken at Round {need_for_me} — {why}. "
            f"Fix the broken entries in refs-{actor}.jsonl, or record them as "
            f"declared `unresolved` entries with a reason, then commit again.",
            file=sys.stderr, flush=True,
        )
        sys.exit(2)
    if status == "ok":
        log(f"refs-ok actor={actor} Round={need_for_me} [{why[:160]}]")
    else:
        log(f"refs-skip actor={actor} Round={need_for_me}: {why[:160]}")

    if need_for_me < 2:
        sys.exit(0)
    peer = "b" if actor == "a" else "a"
    need = need_for_me - 1

    if read_round(X / f"ready-{peer}.round") >= need:
        log(f"fast-allow actor={actor} Round={need_for_me} peer={peer}>={need}")
        sys.exit(0)

    log(f"wait-start actor={actor} Round={need_for_me} need peer-{peer}>={need}")
    # Deadline-based wait: unrelated filesystem events in X only cause a cheap
    # re-check; the wall budget is WINDOWS x WINDOW_SEC regardless of how noisy
    # the directory is (counting events as "windows" collapsed the wait).
    deadline = time.time() + WINDOW_SEC * WINDOWS
    w = 0
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        w += 1
        wait_event(int(min(WINDOW_SEC, remaining)) or 1)
        if read_round(X / f"ready-{peer}.round") >= need:
            log(f"allow-after-wait actor={actor} Round={need_for_me} wake={w}")
            print(json.dumps(
                {"additionalContext": f"gate: peer round {need} ready"}),
                flush=True,
            )
            sys.exit(0)
        alive = peer_alive(peer)
        if alive is False:
            log(f"block actor={actor} peer-{peer} dead after wake={w}")
            print(
                f"gate: peer-{peer} is not running (pid dead) and its round "
                f"is < {need}; wait abandoned",
                file=sys.stderr, flush=True,
            )
            sys.exit(2)
    log(f"block actor={actor} exhausted budget for peer-{peer} round {need}")
    print(
        f"gate: exhausted {WINDOWS} x {WINDOW_SEC}s budget waiting for "
        f"peer-{peer} round {need}",
        file=sys.stderr, flush=True,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
