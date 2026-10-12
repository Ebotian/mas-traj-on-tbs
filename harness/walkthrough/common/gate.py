#!/usr/bin/env python3
"""PreToolUse round gate for the dual-agent runs (bounded hold).

Hook contract (qwen-code 0.25.1, pinned 726e8d77; exit-2 consumer re-checked
against the 0.25.1 bundle 2026-10-12):
- PreToolUse command hooks run BEFORE the tool call and are awaited; a commit
  attempt is therefore held open while this script waits.
- Exit 0 = allow; exit 2 = BLOCK with the stderr text as the reason.
- HARD 60 s WALL (w7 finding): the client's hook request times out after 60 s
  (`firePreToolUseHook` -> `messageBus.request(..., timeoutMs=6e4)` default)
  and then FAILS OPEN — the tool passes silently and any later verdict is
  dropped. The gate therefore guarantees its verdict within WT_DECIDE_SEC
  (default 45 s, absolute deadline from script start); the settings.json hook
  `timeout` is only a backstop against a hung process and cannot extend the
  client wall.

Barrier rule: a commit whose message carries `Round: N` (N >= 2) from actor X
is allowed only once the peer has published `Round: N-1`
(/root/wt/x/ready-<peer>.round, written by the git post-commit hook).
Two refusal classes (both exit 2; the actor prompt routes on the text):
- dead: the peer PID is gone -> terminal; the actor writes abort + END.
- retry: the peer is alive/unknown but Round N-1 is not published at the end
  of the bounded hold -> the actor runs wait_peer.sh (which owns the long
  working-aware wait and the silence/stall policy) and re-attempts the
  commit; the re-attempt after wait_peer exits 0 is fast-allowed here.
Never a silent pass: every path exits with a verdict inside the wall.

Evidence-reference gate (full-course, 2026-10-11): EVERY `(Round: N)` commit
first runs `refs.py check` for the committing actor; any BROKEN reference
exits 2 immediately (before the barrier — a broken ledger is a local defect,
waiting cannot fix it). Conservative asymmetry: only positively-broken refs
block; a missing or crashing checker degrades to fail-OPEN with a loud
`refs-skip` log line (a checker bug must never brick the run).
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

X = pathlib.Path(os.environ.get("WT_X", "/root/wt/x"))
DECIDE_SEC = min(float(os.environ.get("WT_DECIDE_SEC", "45")), 50.0)
SLICE_SEC = float(os.environ.get("WT_SLICE_SEC", "4"))
REFS_TIMEOUT_SEC = float(os.environ.get("WT_REFS_TIMEOUT", "15"))
WT_ROOT = pathlib.Path(os.environ.get("WT_ROOT", "/root/wt"))
REFS_TOOL = os.environ.get("WT_REFS_TOOL") or str(WT_ROOT / "refs.py")


def refs_check(actor: str, rnd: int) -> tuple:
    """(status, line): ok | block | skip(why).  skip = fail-open."""
    refs = WT_ROOT / actor / f"refs-{actor}.jsonl"
    try:
        r = subprocess.run(
            [sys.executable, REFS_TOOL, "--actor", actor, "--refs", str(refs),
             "--round", str(rnd), "check"],
            capture_output=True, text=True, timeout=REFS_TIMEOUT_SEC,
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


def peer_state(actor: str) -> str:
    """dead | alive | unknown (no pid record yet).  Staleness is not judged
    here — wait_peer.sh owns the working-aware / silence policy."""
    try:
        pid = int((X / f"pid-{actor}").read_text().strip())
    except Exception:
        return "unknown"
    try:
        os.kill(pid, 0)
    except OSError:
        return "dead"
    return "alive"


def block_exit(kind: str, actor: str, peer: str, need: int, when: str) -> None:
    """Exit-2 with the class-specific message (dead = terminal, retry = wait)."""
    if kind == "dead":
        msg = (f"gate: peer-{peer} is not running (pid dead) and its round "
               f"is < {need}; wait abandoned")
        log(f"block actor={actor} peer-{peer} dead {when}")
    else:
        msg = (f"gate: peer-{peer} has not published Round {need} within "
               f"{int(DECIDE_SEC)}s; wait for it "
               f"(bash /root/wt/wait_peer.sh {peer} {need}), then attempt the "
               f"commit again.")
        log(f"block actor={actor} peer-{peer} alive-not-ready {when}")
    print(msg, file=sys.stderr, flush=True)
    sys.exit(2)


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
    t0 = time.time()
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

    # Up-front liveness: a dead peer can never publish, and waiting would
    # waste the (wall-bounded) budget.
    if peer_state(peer) == "dead":
        block_exit("dead", actor, peer, need, "(pre-wait)")

    deadline = t0 + DECIDE_SEC
    log(f"wait-start actor={actor} Round={need_for_me} need peer-{peer}>={need} "
        f"budget={int(DECIDE_SEC)}s")
    # Bounded hold: short slices keep the liveness check fresh; a ready file
    # (or any X event) wakes the slice early. The deadline is absolute.
    w = 0
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        w += 1
        wait_event(int(min(SLICE_SEC, remaining)) or 1)
        if read_round(X / f"ready-{peer}.round") >= need:
            log(f"allow-after-wait actor={actor} Round={need_for_me} wake={w}")
            print(json.dumps(
                {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                        "additionalContext": f"gate: peer round {need} ready"}}),
                flush=True,
            )
            sys.exit(0)
        if peer_state(peer) == "dead":
            block_exit("dead", actor, peer, need, f"after wake={w}")

    # Budget spent with the peer alive/unknown: retry class — the actor waits
    # via wait_peer.sh and re-attempts; the re-attempt is fast-allowed.
    if peer_state(peer) == "dead":
        block_exit("dead", actor, peer, need, "(budget end)")
    block_exit("retry", actor, peer, need, f"(budget end, {int(DECIDE_SEC)}s)")


if __name__ == "__main__":
    main()
