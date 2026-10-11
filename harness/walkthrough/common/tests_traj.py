#!/usr/bin/env python3
# tests_traj.py — TDD suite for traj_index.py / traj.py (sealed trajectory tooling).
# Fixtures: two transcripts captured from a real dual-agent run (fixtures/). Plain asserts, no deps.
# Run: python3 tests_traj.py
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TRAJ = os.path.join(HERE, "traj.py")
INDEX = os.path.join(HERE, "traj_index.py")
FIX = os.path.join(HERE, "fixtures")  # captured from a real dual-agent run (2026-10-10)
FA = os.path.join(FIX, "dual-a.jsonl")  # a, 680 lines
FB = os.path.join(FIX, "dual-b.jsonl")  # b, 1155 lines
PY = sys.executable

def run(args, **kw):
    r = subprocess.run([PY] + args, capture_output=True, text=True, **kw)
    return r.returncode, r.stdout, r.stderr

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def complete_lines(path, n):
    with open(path, "rb") as f:
        out = b""
        for line in f:
            out += line
            n -= 1
            if n == 0:
                break
    return out

def mk_xdir(ready_a=None, ready_b=None):
    d = tempfile.mkdtemp(prefix="traj-x-")
    if ready_a is not None:
        open(os.path.join(d, "ready-a.round"), "w").write(str(ready_a))
    if ready_b is not None:
        open(os.path.join(d, "ready-b.round"), "w").write(str(ready_b))
    return d

def report(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" — " + detail) if detail else ""))
    return ok

RESULTS = []
def t(name, fn):
    try:
        fn()
        RESULTS.append(report(name, True))
    except AssertionError as e:
        RESULTS.append(report(name, False, str(e)))
    except Exception as e:
        RESULTS.append(report(name, False, "exception: %r" % (e,)))

def load_index(path):
    return [json.loads(l) for l in open(path)]

# ---------------------------------------------------------------- tests
def t_build_idempotent():
    d = tempfile.mkdtemp(prefix="traj-t-")
    idx = os.path.join(d, "a.idx.jsonl"); st = os.path.join(d, "a.state.json")
    rc, out, err = run([INDEX, "build", FA, idx, "--state", st])
    assert rc == 0, err
    h1 = sha(idx)
    rc, out, err = run([INDEX, "build", FA, idx, "--state", st])
    assert rc == 0, err
    assert sha(idx) == h1, "re-run changed the index bytes"
    rows = load_index(idx)
    assert len(rows) == 680, "expected 680 rows, got %d" % len(rows)

def t_build_incremental():
    d = tempfile.mkdtemp(prefix="traj-t-")
    part = os.path.join(d, "a.part.jsonl"); idx = os.path.join(d, "a.idx.jsonl"); st = os.path.join(d, "a.state.json")
    open(part, "wb").write(complete_lines(FA, 300))
    rc, _, err = run([INDEX, "build", part, idx, "--state", st]); assert rc == 0, err
    first = load_index(idx)
    assert len(first) == 300
    shutil.copyfile(FA, part)
    rc, _, err = run([INDEX, "build", part, idx, "--state", st]); assert rc == 0, err
    full = load_index(idx)
    assert len(full) == 680, "incremental rebuild got %d rows" % len(full)
    assert full[:300] == first, "prefix rows changed on incremental rebuild"

def t_half_line():
    d = tempfile.mkdtemp(prefix="traj-t-")
    part = os.path.join(d, "a.part.jsonl"); idx = os.path.join(d, "a.idx.jsonl")
    full = complete_lines(FA, 100)
    with open(FA, "rb") as f:
        f.seek(0); f.read(len(full)); tail = f.read(20)  # 20 bytes of line 101, no newline
    open(part, "wb").write(full + tail)
    rc, _, err = run([INDEX, "build", part, idx]); assert rc == 0, err
    rows = load_index(idx)
    assert len(rows) == 100, "partial line leaked into index (%d rows)" % len(rows)
    shutil.copyfile(FA, part)
    rc, _, err = run([INDEX, "build", part, idx]); assert rc == 0, err
    assert len(load_index(idx)) == 680

def t_row_shape_and_known_fields():
    d = tempfile.mkdtemp(prefix="traj-t-")
    idx = os.path.join(d, "a.idx.jsonl")
    rc, _, err = run([INDEX, "build", FA, idx]); assert rc == 0, err
    rows = load_index(idx)
    assert [r["L"] for r in rows] == list(range(680)), "L must be 0..679 strictly"
    for k in ("v", "sid", "L", "ts", "type", "line_sha"):
        assert k in rows[0], "row missing key %s" % k
    r36 = rows[36]
    assert r36["type"] == "system" and r36.get("sub") == "api_response", json.dumps(r36)[:200]
    u = r36["usage"]
    assert (u["in"], u["cache"], u["out"], u["think"]) == (41703, 41088, 351, 53), u
    idxb = os.path.join(d, "b.idx.jsonl")
    rc, _, err = run([INDEX, "build", FB, idxb]); assert rc == 0, err
    rowsb = load_index(idxb)
    assert len(rowsb) == 1155
    assert rowsb[102].get("sub") == "tool_call" and rowsb[102].get("tool") == "write_file"
    assert rowsb[103]["type"] == "tool_result" and rowsb[103]["rsize"] > 1000

def t_usage_totals_match():
    d = tempfile.mkdtemp(prefix="traj-t-")
    idx = os.path.join(d, "a.idx.jsonl")
    rc, _, err = run([INDEX, "build", FA, idx]); assert rc == 0, err
    tin = sum(r["usage"]["in"] for r in load_index(idx) if r.get("usage"))
    tout = sum(r["usage"]["out"] for r in load_index(idx) if r.get("usage"))
    assert tin == 45858234 and tout == 290404, (tin, tout)
    idxb = os.path.join(d, "b.idx.jsonl")
    rc, _, err = run([INDEX, "build", FB, idxb]); assert rc == 0, err
    tin = sum(r["usage"]["in"] for r in load_index(idxb) if r.get("usage"))
    tout = sum(r["usage"]["out"] for r in load_index(idxb) if r.get("usage"))
    assert tin == 97708701 and tout == 400279, (tin, tout)

def t_anchors_and_find():
    d = tempfile.mkdtemp(prefix="traj-t-")
    x = mk_xdir(ready_a=3, ready_b=3)
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "b", "anchors", "C54", "--transcript", FB])
    assert rc == 0, err
    assert "L" in out, "anchors should list step locations: %r" % out[:200]
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "b", "find", "aggregate\\.py", "--transcript", FB])
    assert rc == 0, err
    assert out.count("L") >= 1 and "aggregate" in out, out[:300]

def t_cap_show():
    x = mk_xdir(ready_a=3)
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "a", "show", "--lines", "0:679", "--transcript", FA])
    assert rc == 0, err
    assert len(out.encode()) <= 16384 + 512, "default cap violated: %d bytes" % len(out.encode())
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "a", "show", "--lines", "0:679", "--max", "999999", "--transcript", FA])
    assert rc == 0, err
    assert len(out.encode()) <= 65536 + 512, "hard cap violated: %d bytes" % len(out.encode())
    assert "capped" in out, "cap banner missing"

def t_self_gate():
    x0 = mk_xdir()  # no ready file
    rc, out, err = run([TRAJ, "--xdir", x0, "--actor", "a", "summary", "--transcript", FA])
    assert rc != 0, "self read allowed without Round 2"
    x2 = mk_xdir(ready_a=2)  # w6 finding: Round 3's work period needs self reads (E7 circularity)
    rc, out, err = run([TRAJ, "--xdir", x2, "--actor", "a", "summary", "--transcript", FA])
    assert rc == 0, "self read must open once Round 2 is published: %s" % err
    x3 = mk_xdir(ready_a=3)
    rc, out, err = run([TRAJ, "--xdir", x3, "--actor", "a", "summary", "--transcript", FA])
    assert rc == 0, err
    assert "in=45,858,234" in out and "out=290,404" in out and "rows=680" in out, out[:300]

def t_peer_gate():
    x = mk_xdir(); repo = tempfile.mkdtemp(prefix="traj-repo-")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                   cwd=repo, check=True, env={**os.environ,
                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    rc, out, err = run([TRAJ, "--xdir", x, "--repo", repo, "--peer", "b", "summary"])
    assert rc != 0 and "M1" in (err + out), "peer read allowed before ckpt-m1"
    subprocess.run(["git", "tag", "ckpt-m1"], cwd=repo, check=True)
    rc, out, err = run([TRAJ, "--xdir", x, "--repo", repo, "--peer", "b", "summary"])
    assert rc != 0 and "snapshot" in (err + out), "peer read allowed without snapshot"
    snap = os.path.join(x, "traj-b.upto-cut.jsonl")
    open(snap, "wb").write(complete_lines(FB, 100))
    os.symlink("traj-b.upto-cut.jsonl", os.path.join(x, "traj-b.jsonl"))
    rc, out, err = run([TRAJ, "--xdir", x, "--repo", repo, "--peer", "b", "summary"])
    assert rc == 0, err
    assert "rows=100" in out, "peer summary must see only the snapshot (%r)" % out[:200]

def t_since_commit():
    x = mk_xdir(ready_a=3); repo = tempfile.mkdtemp(prefix="traj-repo-")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_AUTHOR_DATE": "2026-10-10T16:44:00 +0000",
           "GIT_COMMITTER_DATE": "2026-10-10T16:44:00 +0000"}
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "cut"], cwd=repo, check=True, env=env)
    cut_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    d = tempfile.mkdtemp(prefix="traj-t-"); idx = os.path.join(d, "a.idx.jsonl")
    rc, _, err = run([INDEX, "build", FA, idx]); assert rc == 0, err
    rows = load_index(idx)
    expect = next(r["L"] for r in rows if r["ts"] >= "2026-10-10T16:44:00")
    rc, out, err = run([TRAJ, "--xdir", x, "--repo", repo, "--actor", "a",
                        "digest", "--since-commit", cut_sha, "--transcript", FA])
    assert rc == 0, err
    first = out.splitlines()[0]
    assert ("L%d" % expect) in first, "digest should start at L%d, got %r" % (expect, first)

def t_lsha():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import traj_index
    want = next(r["line_sha"] for r in traj_index.parse_all(FA)[0] if r["L"] == 100)
    x = mk_xdir(ready_a=3)
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "a", "lsha", "L100", "--transcript", FA])
    assert rc == 0, err
    assert ("L100 " + want) in out, (want, out[:200])
    rc, out, err = run([TRAJ, "--xdir", x, "--actor", "a", "lsha", "400-402", "--transcript", FA])
    assert rc == 0 and out.count("L") >= 3, out[:200]

def t_audit_clean_real():
    rc, out, err = run([TRAJ, "audit-seal", "--actor", "a", "--peer", "b", "--transcript", FA])
    assert rc == 0, "real transcript a falsely flagged: %s %s" % (out, err)
    rc, out, err = run([TRAJ, "audit-seal", "--actor", "b", "--peer", "a", "--transcript", FB])
    assert rc == 0, "real transcript b falsely flagged: %s %s" % (out, err)

def t_audit_synth_detect():
    d = tempfile.mkdtemp(prefix="traj-t-")
    synth = os.path.join(d, "synth.jsonl")
    inj = json.dumps({
        "uuid": "inj-1", "parentUuid": "x", "sessionId": "bb59b08d-0ed5-45f8-92d7-0aff0edacd1d",
        "timestamp": "2026-10-10T15:50:00.000Z", "type": "assistant",
        "provenance": "assistant_output",
        "message": {"role": "model", "parts": [{"functionCall": {
            "name": "run_shell_command",
            "args": {"command": "cat /root/.qwen/projects/-root-wt-b/chats/deadbeef.jsonl | head -80"}}}]},
    }) + "\n"
    open(synth, "wb").write(complete_lines(FA, 60) + inj.encode())
    rc, out, err = run([TRAJ, "audit-seal", "--actor", "a", "--peer", "b", "--transcript", synth])
    assert rc == 1, "synthetic violation not detected (rc=%d, out=%r)" % (rc, out[:200])
    assert "L60" in out, "hit should anchor to L60: %r" % out[:300]

def t_audit_metadata_tier():
    d = tempfile.mkdtemp(prefix="traj-t-")
    synth = os.path.join(d, "synth2.jsonl")
    inj = json.dumps({
        "uuid": "inj-2", "parentUuid": "x", "sessionId": "bb59b08d-0ed5-45f8-92d7-0aff0edacd1d",
        "timestamp": "2026-10-10T15:51:00.000Z", "type": "assistant",
        "provenance": "assistant_output",
        "message": {"role": "model", "parts": [{"functionCall": {
            "name": "run_shell_command",
            "args": {"command": "stat -c '%y %s' /root/.qwen/projects/-root-wt-b/chats/x.jsonl"}}}]},
    }) + "\n"
    open(synth, "wb").write(complete_lines(FA, 60) + inj.encode())
    rc, out, err = run([TRAJ, "audit-seal", "--actor", "a", "--peer", "b", "--transcript", synth])
    assert rc == 0, "metadata touch must not count as a violation (rc=%d)" % rc
    assert "metadata" in out.lower(), out[:300]

TESTS = [
    ("build_idempotent", t_build_idempotent),
    ("build_incremental", t_build_incremental),
    ("half_line_pending", t_half_line),
    ("row_shape_known_fields", t_row_shape_and_known_fields),
    ("usage_totals_match", t_usage_totals_match),
    ("anchors_and_find", t_anchors_and_find),
    ("hard_caps", t_cap_show),
    ("self_gate_round3", t_self_gate),
    ("peer_gate_m1_snapshot", t_peer_gate),
    ("since_commit_digest", t_since_commit),
    ("lsha_lines", t_lsha),
    ("audit_seal_clean_real", t_audit_clean_real),
    ("audit_seal_detect_synth", t_audit_synth_detect),
    ("audit_seal_metadata_tier", t_audit_metadata_tier),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        t(name, fn)
    ok = sum(RESULTS); n = len(RESULTS)
    print("%d/%d passed" % (ok, n))
    sys.exit(0 if ok == n else 1)
