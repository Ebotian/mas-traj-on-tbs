#!/usr/bin/env python3
# tests_stats.py — unit tests for traj_stats.py v2 (2026-10-12):
# adoption merges both sides by event time (b→a recoverable; same-second = concurrent);
# transcript prefix hash is stable under post-cut growth; tokens are per-call sums with
# uncached = prompt - cached; ledger/protocol outputs carry source labels; write_ro is
# 0444 + idempotent; gen writes the traj-stats/2 schema.
# Run: python3 tests_stats.py
import importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "traj_stats", os.path.join(HERE, "traj_stats.py"))
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

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

PH8 = "alpha beta gamma delta epsilon zeta eta theta"  # exactly one 8-gram

def _adopt(texts_a, texts_b, a_cites_b_lines=None):
    m = {"a": {"_texts": [(i, t, x) for (t, i, x) in texts_a]},
         "b": {"_texts": [(i, t, x) for (t, i, x) in texts_b]}}
    led = {"a": {"traj_ranges": {"b": list(a_cites_b_lines or [])}},
           "b": {"traj_ranges": {"a": []}}}
    return ts.adoption_stats(m, led)

def t_b_first_reuse_is_b_to_a():
    r = _adopt([(200, 5, "maybe " + PH8)], [(100, 3, PH8)])
    c = r["counts"]
    assert c["b_to_a"] == 1, c
    assert c["a_to_b"] == 0 and c["concurrent"] == 0, c

def t_a_first_reuse_is_a_to_b():
    r = _adopt([(100, 3, PH8)], [(200, 5, "see " + PH8)])
    c = r["counts"]
    assert c["a_to_b"] == 1, c
    assert c["b_to_a"] == 0 and c["concurrent"] == 0, c

def t_same_second_is_concurrent():
    r = _adopt([(100, 3, PH8)], [(100, 5, PH8)])
    c = r["counts"]
    assert c["concurrent"] == 1, c
    assert c["a_to_b"] == 0 and c["b_to_a"] == 0, c

def t_cited_flag_from_ledger_ranges():
    r = _adopt([(200, 5, "maybe " + PH8)], [(100, 3, PH8)], a_cites_b_lines=[(3, 3)])
    c = r["counts"]
    assert c["cited_b_to_a"] == 1, c

def _jl(ts_str, typ="assistant", text=None, usage=None):
    d = {"timestamp": ts_str, "type": typ}
    if text is not None:
        d["message"] = {"role": "assistant", "parts": [{"text": text}]}
    if usage is not None:
        d["usageMetadata"] = usage
    return json.dumps(d, ensure_ascii=False)

def t_prefix_hash_stable_under_growth():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "chat.jsonl")
        with open(p, "w") as f:
            f.write(_jl("2026-10-12T00:00:10Z", text="one two three four five six seven eight") + "\n")
            f.write(_jl("2026-10-12T00:00:20Z", text=PH8) + "\n")
        cut = ts.tsparse("2026-10-12T00:00:20Z")
        s1 = ts.side_stats(p, cut)
        assert s1["lines_leq_cut"] == 2 and s1["lines_total"] == 2, s1
        with open(p, "a") as f:
            f.write(_jl("2026-10-12T00:00:30Z", text="x y z") + "\n")
        s2 = ts.side_stats(p, cut)
        assert s2["lines_leq_cut"] == 2 and s2["lines_total"] == 3, s2
        assert s1["sha256_leq_cut"] == s2["sha256_leq_cut"], "prefix hash moved"
        s3 = ts.side_stats(p, ts.tsparse("2026-10-12T00:00:10Z"))
        assert s3["lines_leq_cut"] == 1, s3
        assert s3["sha256_leq_cut"] != s1["sha256_leq_cut"], "prefix hash not cut-sensitive"

def t_usage_per_call_sum_and_uncached():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "chat.jsonl")
        with open(p, "w") as f:
            f.write(_jl("2026-10-12T00:00:10Z", text="a b c d e f g h",
                        usage={"promptTokenCount": 100, "cachedContentTokenCount": 60,
                               "candidatesTokenCount": 10, "thoughtsTokenCount": 5}) + "\n")
            f.write(_jl("2026-10-12T00:00:11Z", text="i j k l m n o p",
                        usage={"promptTokenCount": 200, "cachedContentTokenCount": 180,
                               "candidatesTokenCount": 20, "thoughtsTokenCount": 7}) + "\n")
        s = ts.side_stats(p, ts.tsparse("2026-10-12T00:00:20Z"))
        assert s["tokens"] == {"prompt": 300, "candidates": 30, "thoughts": 12, "cached": 240}, s["tokens"]
        assert s["uncached"] == 60, s["uncached"]

def _git(repo, *args):
    subprocess.run(["git", "-C", repo] + list(args), check=True, capture_output=True)

def t_ledger_source_labels():
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "repo"); os.makedirs(repo)
        subprocess.run(["git", "init", "-q", repo], check=True)
        _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
        with open(os.path.join(repo, "README.md"), "w") as f:
            f.write("x\n")
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
        _git(repo, "tag", "ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        wt = os.path.join(td, "wt"); os.makedirs(os.path.join(wt, "a"))
        with open(os.path.join(wt, "a", "refs-a.jsonl"), "w") as f:
            f.write('{"id":"E1","kind":"commit"}\n')
        lines, src = ts.load_ledger(repo, "ckpt-m00", xdir, wt, "a")
        assert src == "file:%s" % os.path.join(wt, "a", "refs-a.jsonl"), src
        assert lines == ['{"id":"E1","kind":"commit"}'], lines
        shutil.copy(os.path.join(wt, "a", "refs-a.jsonl"), os.path.join(repo, "refs-a.jsonl"))
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "refs")
        _git(repo, "tag", "ckpt-m01")
        lines2, src2 = ts.load_ledger(repo, "ckpt-m01", xdir, wt, "a")
        assert src2 == "tag:ckpt-m01", src2
        assert lines2 == ['{"id":"E1","kind":"commit"}'], lines2
        _, src3 = ts.load_ledger(repo, "ckpt-m00", xdir, os.path.join(td, "none"), "b")
        assert src3 == "missing", src3

def t_write_ro_0444_idempotent():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.json")
        assert ts.write_ro(p, "hello\n") == "written"
        assert (os.stat(p).st_mode & 0o777) == 0o444
        assert ts.write_ro(p, "hello\n") == "unchanged"
        assert ts.write_ro(p, "hello2\n") == "written"
        assert (os.stat(p).st_mode & 0o777) == 0o444

def t_gen_writes_v2_schema():
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "repo"); os.makedirs(repo)
        subprocess.run(["git", "init", "-q", repo], check=True)
        _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
        for name in ("brief-a.md", "brief-b.md"):
            with open(os.path.join(repo, name), "w") as f:
                f.write("note\n")
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
        _git(repo, "tag", "ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        with open(ta, "w") as f:
            f.write(_jl("2026-10-12T00:00:10Z", text=PH8,
                        usage={"promptTokenCount": 100, "cachedContentTokenCount": 60,
                               "candidatesTokenCount": 10, "thoughtsTokenCount": 5}) + "\n")
        with open(tb, "w") as f:
            f.write(_jl("2026-10-12T00:00:11Z", text="see " + PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": td, "out": out,
                "transcript_a": ta, "transcript_b": tb}
        rc = ts.gen(repo, xdir, "ckpt-m00", opts)
        assert rc == 0, rc
        jpath = os.path.join(out, "ckpt-m00.json")
        assert os.path.exists(jpath), "json missing"
        d = json.load(open(jpath))
        assert d["meta"]["schema"] == "traj-stats/2", d["meta"].get("schema")
        assert d["meta"]["usage_semantics"] == "per_call"
        assert "sha256_leq_cut" in d["meta"]["transcripts"]["a"]
        assert d["ledger"]["a"]["source"] == "missing"
        assert d["protocol"]["sources"]["forks"] == "missing"
        assert "concurrent" in d["adoption"]["counts"]
        assert os.path.exists(os.path.join(out, "ckpt-m00.md"))
        assert (os.stat(jpath).st_mode & 0o777) == 0o444
        rc2 = ts.auto(repo, xdir, opts)
        assert rc2 == 0

TESTS = [
    ("b_first_reuse_is_b_to_a", t_b_first_reuse_is_b_to_a),
    ("a_first_reuse_is_a_to_b", t_a_first_reuse_is_a_to_b),
    ("same_second_is_concurrent", t_same_second_is_concurrent),
    ("cited_flag_from_ledger_ranges", t_cited_flag_from_ledger_ranges),
    ("prefix_hash_stable_under_growth", t_prefix_hash_stable_under_growth),
    ("usage_per_call_sum_and_uncached", t_usage_per_call_sum_and_uncached),
    ("ledger_source_labels", t_ledger_source_labels),
    ("write_ro_0444_idempotent", t_write_ro_0444_idempotent),
    ("gen_writes_v2_schema", t_gen_writes_v2_schema),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        t(name, fn)
    ok = sum(RESULTS); n = len(RESULTS)
    print("%d/%d passed" % (ok, n))
    sys.exit(0 if ok == n else 1)
