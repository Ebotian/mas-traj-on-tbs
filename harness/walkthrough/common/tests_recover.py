#!/usr/bin/env python3
# tests_recover.py — unit tests for recover.py wake() cwd handling (w7 fix):
# a wake must recreate a removed worktree dir (the chat store is keyed by the
# cwd path string, so `-r <uuid>` still resumes) and must never die with
# FileNotFoundError (w7: wake-b got rc=125 when wake-a's structure fix had
# already removed /root/wt/b).
# v5 (2026-10-13): the remaining budget is recomputed before each wake and the wake
# timeout is truncated to it (a 200 s leftover must not launch a 900 s wake).
# Run: python3 tests_recover.py
import importlib.util, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "recover_mod", os.path.join(HERE, "recover.py"))
recover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recover)

def mk():
    base = tempfile.mkdtemp(prefix="rec-")
    wt = os.path.join(base, "wt"); os.makedirs(wt)
    repo = os.path.join(wt, "repo"); os.makedirs(repo)
    logs = os.path.join(wt, "logs"); os.makedirs(logs)
    x = os.path.join(wt, "x"); os.makedirs(x)
    bind = os.path.join(base, "bin"); os.makedirs(bind)
    q = os.path.join(bind, "qwen")
    with open(q, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(q, 0o755)
    return base, wt, repo, x, logs, bind

class PathStub:
    def __init__(self, bind):
        self.bind = bind
    def __enter__(self):
        self.old = os.environ.get("PATH", "")
        os.environ["PATH"] = self.bind + os.pathsep + self.old
    def __exit__(self, *a):
        os.environ["PATH"] = self.old

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

def t_missing_cwd_recreated():
    base, wt, repo, x, logs, bind = mk()
    with PathStub(bind):
        rec = recover.wake("b", repo, x, logs, "uuid-1", 30, "probe prompt")
    assert rec["rc"] == 0, rec
    assert os.path.isdir(os.path.join(wt, "b")), "cwd was not recreated"
    assert "recreated" in rec.get("note", ""), rec
    assert os.path.exists(os.path.join(logs, "wa-b-wake.out")), "wake log missing"

def t_skip_when_cwd_blocked():
    base, wt, repo, x, logs, bind = mk()
    with open(os.path.join(wt, "b"), "w") as f:
        f.write("not a dir\n")
    rec = recover.wake("b", repo, x, logs, "uuid-1", 30, "probe prompt")
    assert rec.get("rc") is None and "skip" in rec, rec
    assert "cwd unavailable" in rec["skip"], rec

def t_existing_cwd_no_note():
    base, wt, repo, x, logs, bind = mk()
    os.makedirs(os.path.join(wt, "b"))
    with PathStub(bind):
        rec = recover.wake("b", repo, x, logs, "uuid-1", 30, "probe prompt")
    assert rec["rc"] == 0, rec
    assert "note" not in rec, rec  # nothing had to be recreated


def _commit_repo(repo):
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
    with open(os.path.join(repo, "f"), "w") as f:
        f.write("x\n")
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "c"], check=True)


def t_budget_helpers():
    base, wt, repo, x, logs, bind = mk()
    _commit_repo(repo)
    rem = recover.budget_left(repo, 13500)
    assert rem is not None and 13000 < rem <= 13500, rem
    assert recover.clamp_timeout(900, rem) == 900, "ample budget keeps the cap"
    assert recover.clamp_timeout(900, 200) == 200, "short budget truncates the timeout"
    assert recover.clamp_timeout(900, None) == 900


def _run_main(repo, x, logs, wall):
    old_argv = sys.argv
    olds = {k: os.environ.get(k) for k in ("WT_SESSION_WALL", "WT_RECOVER")}
    os.environ["WT_SESSION_WALL"] = str(wall)
    os.environ["WT_RECOVER"] = "1"
    try:
        sys.argv = ["recover.py", repo, x, logs, "u1", "u2"]
        rc = recover.main()
    finally:
        sys.argv = old_argv
        for k, v in olds.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    assert rc == 0, rc
    with open(os.path.join(x, "recover.json")) as f:
        return json.load(f)


def t_main_skips_when_budget_low():
    base, wt, repo, x, logs, bind = mk()
    _commit_repo(repo)
    with open(os.path.join(x, "abort-a"), "w") as f:
        f.write("a\n")
    rec = _run_main(repo, x, logs, 400)  # 剩余 ≈ 100s < 120s → 跳过,不唤醒
    w = [r for r in rec["wakes"] if r["side"] == "a"]
    assert w and w[0].get("skip", "").startswith("budget"), rec["wakes"]
    assert w[0]["budget_left_s"] < 120, w[0]


def t_main_clamps_timeout_to_budget():
    base, wt, repo, x, logs, bind = mk()
    _commit_repo(repo)
    with open(os.path.join(x, "abort-a"), "w") as f:
        f.write("a\n")
    with PathStub(bind):
        rec = _run_main(repo, x, logs, 500)  # 剩余 ≈ 200s < 900s → 超时截断
    w = [r for r in rec["wakes"] if r["side"] == "a"]
    assert w and "timeout_used_s" in w[0], rec["wakes"]
    assert w[0]["timeout_used_s"] < 900, w[0]
    assert w[0]["timeout_used_s"] <= w[0]["budget_left_s"], w[0]
    assert w[0]["rc"] == 0, w[0]

TESTS = [
    ("missing_cwd_recreated", t_missing_cwd_recreated),
    ("skip_when_cwd_blocked", t_skip_when_cwd_blocked),
    ("existing_cwd_no_note", t_existing_cwd_no_note),
    ("budget_helpers", t_budget_helpers),
    ("main_skips_when_budget_low", t_main_skips_when_budget_low),
    ("main_clamps_timeout_to_budget", t_main_clamps_timeout_to_budget),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        t(name, fn)
    ok = sum(RESULTS); n = len(RESULTS)
    print("%d/%d passed" % (ok, n))
    sys.exit(0 if ok == n else 1)
