#!/usr/bin/env python3
# tests_gate.py — integration tests for the gate.py x refs.py evidence gate
# and the w7-fix verdict classes: dead peer blocks up-front, live-but-not-
# ready retry class inside the 60 s client wall, allow-after-wait, and the
# refs fail-open asymmetry.  (The gate no longer judges staleness — that
# policy lives in wait_peer.sh.)
# Full-course ruling: every (Round: N) commit runs refs check; broken refs
# exit 2 BEFORE the peer barrier; a broken checker must fail OPEN (log, pass).
# Run: python3 tests_gate.py
import json, os, shutil, subprocess, sys, tempfile, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "gate.py")
PY = sys.executable

def mk_env(decide="3"):
    root = tempfile.mkdtemp(prefix="gate-root-")
    x = os.path.join(root, "x"); os.makedirs(x)
    repo = tempfile.mkdtemp(prefix="gate-repo-")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    env = {**os.environ, "WT_ROOT": root, "WT_X": x, "WT_REPO": repo,
           "WT_DECIDE_SEC": decide, "WT_SLICE_SEC": "1"}
    return root, x, repo, env

def install_tools(root):
    for f in ("refs.py", "traj.py", "traj_index.py"):
        shutil.copyfile(os.path.join(HERE, f), os.path.join(root, f))
    os.makedirs(os.path.join(root, "a"), exist_ok=True)

def write_ledger(root, lines):
    with open(os.path.join(root, "a", "refs-a.jsonl"), "a") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

def run_gate(env, cwd, round_n, extra_env=None):
    payload = {"hook_event_name": "PreToolUse", "session_id": "",
               "tool_input": {"cwd": cwd,
                              "command": 'git commit -m "x (Round: %d)"' % round_n}}
    e = dict(env)
    if extra_env:
        e.update(extra_env)
    t0 = time.time()
    r = subprocess.run([PY, GATE], input=json.dumps(payload), capture_output=True,
                       text=True, env=e, timeout=30)
    return r.returncode, r.stdout, r.stderr, time.time() - t0

def read_log(env):
    p = os.path.join(env["WT_X"], "gate.log")
    return open(p).read() if os.path.exists(p) else ""

def write_ready(path, val):
    with open(path, "w") as fh:
        fh.write(val)

def reaped_pid():
    p = subprocess.Popen(["/bin/true"]); p.wait()
    return p.pid

RESULTS = []
def report(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" — " + detail) if detail else ""))
    return ok

def t(name, fn):
    try:
        fn()
        RESULTS.append(report(name, True))
    except AssertionError as e:
        RESULTS.append(report(name, False, str(e)))
    except Exception as e:
        RESULTS.append(report(name, False, "exception: %r" % (e,)))

def t_no_ledger_round1_pass():
    root, x, repo, env = mk_env(); install_tools(root)
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 1)
    assert rc == 0, "round-1 with no ledger must pass: rc=%d %s" % (rc, err)
    assert "refs-ok" in read_log(env), read_log(env)

def t_broken_blocks_before_barrier():
    root, x, repo, env = mk_env(); install_tools(root)
    write_ledger(root, [{"id": "E1", "kind": "commit", "sha": "0" * 40,
                         "claim": "missing", "r": 4}])
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 2, "broken refs must block: rc=%d" % rc
    assert "references broken" in err and "E1" in err, (err, out)
    assert dt < 10, "block must preempt the barrier wait (took %.1fs)" % dt
    assert "refs-block" in read_log(env), read_log(env)

def t_clean_passes_after_gate():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "ready-b.round"), "w").write("3")
    write_ledger(root, [{"id": "E1", "kind": "unresolved", "reason": "coin-flip", "r": 4}])
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 0, "clean ledger must pass: rc=%d %s" % (rc, err)
    log = read_log(env)
    assert "refs-ok" in log and "fast-allow" in log, log

def t_missing_checker_fails_open():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "ready-b.round"), "w").write("3")
    write_ledger(root, [{"id": "E1", "kind": "commit", "sha": "0" * 40, "claim": "m", "r": 4}])
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4,
                                extra_env={"WT_REFS_TOOL": "/nonexistent/refs.py"})
    assert rc == 0, "missing checker must fail OPEN: rc=%d %s" % (rc, err)
    assert "refs-skip" in read_log(env), read_log(env)

def t_crashing_checker_fails_open():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "ready-b.round"), "w").write("3")
    bad = os.path.join(root, "badrefs.py")
    open(bad, "w").write("import sys\nsys.exit(2)\n")
    write_ledger(root, [{"id": "E1", "kind": "commit", "sha": "0" * 40, "claim": "m", "r": 4}])
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4,
                                extra_env={"WT_REFS_TOOL": bad})
    assert rc == 0, "crashing checker must fail OPEN: rc=%d %s" % (rc, err)
    assert "refs-skip" in read_log(env), read_log(env)

def t_non_round_commit_untouched():
    root, x, repo, env = mk_env(); install_tools(root)
    payload = {"hook_event_name": "PreToolUse", "session_id": "",
               "tool_input": {"cwd": os.path.join(root, "a"),
                              "command": 'git commit -m "no round marker"'}}
    r = subprocess.run([PY, GATE], input=json.dumps(payload), capture_output=True,
                       text=True, env=env, timeout=30)
    assert r.returncode == 0 and "refs" not in read_log(env), (r.returncode, read_log(env))

# ------------------------------------------------- w7-fix verdict classes
def t_dead_peer_blocks_fast():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "pid-b"), "w").write(str(reaped_pid()))
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 2, "dead peer must block: rc=%d %s" % (rc, err)
    assert "is not running (pid dead)" in err, (err, out)
    assert dt < 3, "dead-peer block must be immediate (%.1fs)" % dt
    assert "dead (pre-wait)" in read_log(env), read_log(env)

def t_alive_peer_retry_class_within_wall():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "pid-b"), "w").write(str(os.getpid()))
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 2, "live-but-not-ready must refuse: rc=%d %s" % (rc, err)
    assert "has not published Round 3 within 3s" in err, (err, out)
    assert "wait_peer.sh b 3" in err, (err, out)
    assert "wait abandoned" not in err, "a live peer must not use the dead class"
    assert 2.5 <= dt <= 8, "verdict must land at ~DECIDE and inside the 60 s wall (%.1fs)" % dt
    assert "alive-not-ready" in read_log(env), read_log(env)

def t_allow_after_wait():
    root, x, repo, env = mk_env(); install_tools(root)
    open(os.path.join(x, "pid-b"), "w").write(str(os.getpid()))
    threading.Timer(1.0, write_ready,
                    args=(os.path.join(x, "ready-b.round"), "3")).start()
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 0, "peer publishes mid-hold -> allow: rc=%d %s" % (rc, err)
    assert "allow-after-wait" in read_log(env), read_log(env)
    assert dt < 5, dt

def t_peer_dies_mid_hold():
    root, x, repo, env = mk_env(); install_tools(root)
    p = subprocess.Popen(["sleep", "30"])
    open(os.path.join(x, "pid-b"), "w").write(str(p.pid))
    threading.Timer(1.2, lambda: (p.kill(), p.wait())).start()
    rc, out, err, dt = run_gate(env, os.path.join(root, "a"), 4)
    assert rc == 2 and "is not running (pid dead)" in err, (rc, err, out)
    assert dt < 6, "death during hold must be caught on the next slice (%.1fs)" % dt
    assert "dead after wake=" in read_log(env), read_log(env)

TESTS = [
    ("no_ledger_round1_pass", t_no_ledger_round1_pass),
    ("broken_blocks_before_barrier", t_broken_blocks_before_barrier),
    ("clean_passes_after_gate", t_clean_passes_after_gate),
    ("missing_checker_fails_open", t_missing_checker_fails_open),
    ("crashing_checker_fails_open", t_crashing_checker_fails_open),
    ("non_round_commit_untouched", t_non_round_commit_untouched),
    ("dead_peer_blocks_fast", t_dead_peer_blocks_fast),
    ("alive_peer_retry_class_within_wall", t_alive_peer_retry_class_within_wall),
    ("allow_after_wait", t_allow_after_wait),
    ("peer_dies_mid_hold", t_peer_dies_mid_hold),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        t(name, fn)
    ok = sum(RESULTS); n = len(RESULTS)
    print("%d/%d passed" % (ok, n))
    sys.exit(0 if ok == n else 1)
