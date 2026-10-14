#!/usr/bin/env python3
# tests_stats.py — unit tests for traj_stats.py v4 (2026-10-14):
# text_overlap merges both sides by event time (b→a recoverable; same-second = concurrent);
# transcript prefix hash is stable under post-cut growth (cut pinned; no whole-file fields);
# tokens are per-call sums with uncached = prompt - cached; truncated samples carry the full
# counts (unresolved_count, silences_gt_600s_count); milestone regeneration is byte-stable
# under working-dir growth (pin/ + .meta sidecars) and a missing source is recorded as unknown;
# availability: file sources freeze max(mtime, declared at) at first read (minute precision
# rounds up to :59); cut_epoch = max(tag commit, all available_at); .absent markers block
# absorption of later-appearing sources; fs_avail=False uses declared at only; write_ro is
# 0444 + idempotent; gen writes the traj-stats/4 schema.
# Run: python3 tests_stats.py
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time

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
    return ts.text_overlap_stats(m, led)

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
        assert s1["lines_leq_cut"] == 2 and s1["cut_last_line"] == 2, s1
        assert "lines_total" not in s1, "whole-file line count must not be recorded (drifts)"
        with open(p, "a") as f:
            f.write(_jl("2026-10-12T00:00:30Z", text="x y z") + "\n")
        s2 = ts.side_stats(p, cut)
        assert s2["lines_leq_cut"] == 2 and s2["cut_last_line"] == 2, s2
        assert s1 == s2, "post-cut growth must not move any recorded field"
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


def _git_out(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), check=True,
                       capture_output=True, text=True)
    return r.stdout.strip()

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
        lines, src, pend, av = ts.load_ledger(repo, "ckpt-m00", xdir, wt, "a")
        assert src == "file:%s" % os.path.join(wt, "a", "refs-a.jsonl"), src
        assert lines == ['{"id":"E1","kind":"commit"}'], lines
        assert pend and pend[0] == "ckpt-m00.refs-a.jsonl", pend
        assert av and av["basis"] == "mtime" and av["available_at"] is not None, av
        shutil.copy(os.path.join(wt, "a", "refs-a.jsonl"), os.path.join(repo, "refs-a.jsonl"))
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "refs")
        _git(repo, "tag", "ckpt-m01")
        lines2, src2, pend2, av2 = ts.load_ledger(repo, "ckpt-m01", xdir, wt, "a")
        assert src2 == "tag:ckpt-m01" and pend2 is None, (src2, pend2)
        assert lines2 == ['{"id":"E1","kind":"commit"}'], lines2
        assert av2 and av2["basis"] == "commit", av2
        _, src3, pend3, av3 = ts.load_ledger(repo, "ckpt-m00", xdir, os.path.join(td, "none"), "b")
        assert src3 == "missing" and pend3 is None, (src3, pend3)
        assert av3 is None, av3

def t_write_ro_0444_idempotent():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.json")
        assert ts.write_ro(p, "hello\n") == "written"
        assert (os.stat(p).st_mode & 0o777) == 0o444
        assert ts.write_ro(p, "hello\n") == "unchanged"
        assert ts.write_ro(p, "hello2\n") == "written"
        assert (os.stat(p).st_mode & 0o777) == 0o444

def t_gen_writes_v4_schema():
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
        assert d["meta"]["schema"] == "traj-stats/4", d["meta"].get("schema")
        assert d["meta"]["usage_semantics"] == "per_call"
        assert "sha256_leq_cut" in d["meta"]["transcripts"]["a"]
        assert "lines_total" not in d["meta"]["transcripts"]["a"]
        assert d["meta"]["transcripts"]["a"]["cut_last_line"] == 1
        assert d["ledger"]["a"]["source"] == "missing"
        assert d["ledger"]["a"]["unresolved_count"] is None
        assert d["protocol"]["sources"]["forks"] == "missing"
        av = d["availability"]
        assert av["tag_commit_epoch"] == d["meta"]["cut_epoch"], av
        assert av["max_source_available_at"] is None, av
        assert av["sources"]["protocol.dirs.a"]["basis"] == "missing", av
        assert av["unknown"] == [], av
        assert "concurrent" in d["text_overlap"]["counts"]
        assert os.path.exists(os.path.join(out, "ckpt-m00.md"))
        assert (os.stat(jpath).st_mode & 0o777) == 0o444
        rc2 = ts.auto(repo, xdir, opts)
        assert rc2 == 0


def t_unresolved_count_separates_sample():
    lines = [json.dumps({"kind": "unresolved", "id": "U%02d" % i, "reason": "r%d" % i})
             for i in range(12)]
    r = ts.ledger_stats(lines)
    assert r["unresolved_count"] == 12, r["unresolved_count"]
    assert len(r["unresolved"]) == 10, len(r["unresolved"])


def _fmt(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def t_silences_count_separates_sample():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "chat.jsonl")
        base = ts.tsparse("2026-10-12T00:00:00Z")
        with open(p, "w") as f:
            for i in range(12):
                f.write(_jl(_fmt(base + i * 700), text="a b c d e f g h") + "\n")
        s = ts.side_stats(p, ts.tsparse("2026-10-12T23:00:00Z"))
        assert s["silences_gt_600s_count"] == 11, s["silences_gt_600s_count"]
        assert len(s["silences_gt_600s"]) == 8, len(s["silences_gt_600s"])


def t_regen_pin_stable_under_ledger_growth():
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "repo"); os.makedirs(repo)
        subprocess.run(["git", "init", "-q", repo], check=True)
        _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
        with open(os.path.join(repo, "README.md"), "w") as f:
            f.write("x\n")
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
        _git(repo, "tag", "ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        da = os.path.join(xdir, "dir-a.json")
        with open(da, "w") as f:
            json.dump({"axes": [{"fork_id": "F1", "choice": "alpha"}]}, f)
        wt = os.path.join(td, "wt"); os.makedirs(os.path.join(wt, "a"))
        led = os.path.join(wt, "a", "refs-a.jsonl")
        with open(led, "w") as f:
            f.write('{"id":"E1","kind":"unresolved","reason":"one"}\n')
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        for p in (ta, tb):
            with open(p, "w") as f:
                f.write(_jl("2026-10-12T00:00:10Z", text=PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": wt, "out": out,
                "transcript_a": ta, "transcript_b": tb}
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        jp = os.path.join(out, "ckpt-m00.json")
        b1 = open(jp, "rb").read()
        d1 = json.loads(b1)
        assert d1["ledger"]["a"]["source"].startswith("pin:"), d1["ledger"]["a"]
        assert d1["ledger"]["a"]["unresolved_count"] == 1, d1["ledger"]["a"]
        assert d1["protocol"]["sources"]["dirs"]["a"].startswith("pin:"), d1["protocol"]["sources"]
        assert d1["protocol"]["sources"]["dirs"]["b"] == "missing", d1["protocol"]["sources"]
        # 工作目录账本增长(1→2 条)且方向文件被改写:重生成必须字节稳定(pin/ 固定首次读取)
        with open(led, "a") as f:
            f.write('{"id":"E2","kind":"unresolved","reason":"two"}\n')
        with open(da, "w") as f:
            json.dump({"axes": [{"fork_id": "F1", "choice": "CHANGED"}]}, f)
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        b2 = open(jp, "rb").read()
        assert b1 == b2, "regeneration after working-dir ledger growth must be byte-stable"


def _mk_repo(td, tag="ckpt-m00"):
    repo = os.path.join(td, "repo"); os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "README.md"), "w") as f:
        f.write("x\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
    _git(repo, "tag", tag)
    return repo, int(_git_out(repo, "log", "-1", "--format=%ct"))


def t_avail_minute_precision():
    assert ts.tsparse("2026-10-13T14:51Z") is None
    assert ts.atparse("2026-10-13T14:51Z") == ts.tsparse("2026-10-13T14:51:59Z")
    assert ts.atparse("2026-10-13T14:43:00Z") == ts.tsparse("2026-10-13T14:43:00Z")
    assert ts.atparse(None) is None and ts.atparse("garbage") is None


def t_availability_raises_cut():
    with tempfile.TemporaryDirectory() as td:
        repo, base = _mk_repo(td, tag="ckpt-m01")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        with open(os.path.join(xdir, "dir-a.json"), "w") as f:
            json.dump({"at": _fmt(base + 300),
                       "axes": [{"fork_id": "F1", "choice": "alpha"}]}, f)
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        with open(ta, "w") as f:
            f.write(_jl(_fmt(base + 100), text=PH8) + "\n")
            f.write(_jl(_fmt(base + 400), text="late") + "\n")
        with open(tb, "w") as f:
            f.write(_jl(_fmt(base + 100), text="see " + PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": td, "out": out,
                "transcript_a": ta, "transcript_b": tb}
        assert ts.gen(repo, xdir, "ckpt-m01", opts) == 0
        d = json.load(open(os.path.join(out, "ckpt-m01.json")))
        av = d["availability"]
        assert d["meta"]["cut_epoch"] == base + 300, d["meta"]["cut_epoch"]
        assert av["tag_commit_epoch"] == base, av
        s = av["sources"]["protocol.dirs.a"]
        assert s["available_at"] == base + 300 and s["basis"] == "mtime+declared_at", s
        known = [e["available_at"] for e in av["sources"].values()
                 if e["available_at"] is not None]
        assert max([base] + known) == d["meta"]["cut_epoch"]
        # 转录切片随 cut 上移:base+100 的行纳入、base+400 的行排除
        assert d["volume"]["a"]["lines_leq_cut"] == 1, d["volume"]["a"]["lines_leq_cut"]


def t_absent_marker_blocks_absorption():
    with tempfile.TemporaryDirectory() as td:
        repo, base = _mk_repo(td, tag="ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        for p in (ta, tb):
            with open(p, "w") as f:
                f.write(_jl(_fmt(base + 10), text=PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": td, "out": out,
                "transcript_a": ta, "transcript_b": tb}
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        assert os.path.exists(os.path.join(out, "pin", "ckpt-m00.dir-a.json.absent"))
        b1 = open(os.path.join(out, "ckpt-m00.json"), "rb").read()
        # dir 在首读之后才出现:重生成必须保持 missing(负标记),不吸收后到产物
        with open(os.path.join(xdir, "dir-a.json"), "w") as f:
            json.dump({"at": _fmt(base + 500),
                       "axes": [{"fork_id": "F1", "choice": "alpha"}]}, f)
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        b2 = open(os.path.join(out, "ckpt-m00.json"), "rb").read()
        assert b1 == b2, "later-appearing dir file must not be absorbed"
        d2 = json.loads(b2)
        assert d2["protocol"]["sources"]["dirs"]["a"] == "missing"
        assert d2["availability"]["sources"]["protocol.dirs.a"]["basis"] == "missing"


def t_meta_sidecar_freezes_availability():
    with tempfile.TemporaryDirectory() as td:
        repo, base = _mk_repo(td, tag="ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        da = os.path.join(xdir, "dir-a.json")
        with open(da, "w") as f:
            json.dump({"at": _fmt(base + 100),
                       "axes": [{"fork_id": "F1", "choice": "alpha"}]}, f)
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        for p in (ta, tb):
            with open(p, "w") as f:
                f.write(_jl(_fmt(base + 10), text=PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": td, "out": out,
                "transcript_a": ta, "transcript_b": tb}
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        jp = os.path.join(out, "ckpt-m00.json")
        b1 = open(jp, "rb").read()
        d1 = json.loads(b1)
        assert d1["availability"]["sources"]["protocol.dirs.a"]["available_at"] == base + 100
        assert os.path.exists(os.path.join(out, "pin", "ckpt-m00.dir-a.json.meta"))
        # 首读后来源被改写且 mtime 变动:重生成读侧车,字节稳定
        with open(da, "w") as f:
            json.dump({"at": _fmt(base + 999),
                       "axes": [{"fork_id": "F1", "choice": "CHANGED"}]}, f)
        os.utime(da, (base + 999, base + 999))
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        b2 = open(jp, "rb").read()
        assert b1 == b2, "meta sidecar must freeze availability across regen"


def t_no_fs_avail_declared_only():
    with tempfile.TemporaryDirectory() as td:
        repo, base = _mk_repo(td, tag="ckpt-m00")
        xdir = os.path.join(td, "x"); os.makedirs(xdir)
        with open(os.path.join(xdir, "dir-a.json"), "w") as f:
            json.dump({"at": _fmt(base + 100),
                       "axes": [{"fork_id": "F1", "choice": "alpha"}]}, f)
        db = os.path.join(xdir, "dir-b.json")
        with open(db, "w") as f:
            json.dump({"axes": [{"fork_id": "F1", "choice": "beta"}]}, f)
        os.utime(db, (base + 9999, base + 9999))  # 归档 mtime 不可信:fs 关闭时必须忽略
        ta = os.path.join(td, "ta.jsonl"); tb = os.path.join(td, "tb.jsonl")
        for p in (ta, tb):
            with open(p, "w") as f:
                f.write(_jl(_fmt(base + 10), text=PH8) + "\n")
        out = os.path.join(xdir, "stats"); os.makedirs(out)
        opts = {"chats_root": td, "wt_root": td, "out": out, "fs_avail": False,
                "transcript_a": ta, "transcript_b": tb}
        assert ts.gen(repo, xdir, "ckpt-m00", opts) == 0
        d = json.load(open(os.path.join(out, "ckpt-m00.json")))
        av = d["availability"]
        sa = av["sources"]["protocol.dirs.a"]
        assert sa["available_at"] == base + 100 and sa["basis"] == "declared_at", sa
        assert sa["mtime"] is None, sa
        sb = av["sources"]["protocol.dirs.b"]
        assert sb["available_at"] is None and sb["basis"] == "unknown", sb
        assert "protocol.dirs.b" in av["unknown"], av["unknown"]
        assert d["meta"]["cut_epoch"] == base + 100, d["meta"]["cut_epoch"]


TESTS = [
    ("b_first_reuse_is_b_to_a", t_b_first_reuse_is_b_to_a),
    ("a_first_reuse_is_a_to_b", t_a_first_reuse_is_a_to_b),
    ("same_second_is_concurrent", t_same_second_is_concurrent),
    ("cited_flag_from_ledger_ranges", t_cited_flag_from_ledger_ranges),
    ("prefix_hash_stable_under_growth", t_prefix_hash_stable_under_growth),
    ("usage_per_call_sum_and_uncached", t_usage_per_call_sum_and_uncached),
    ("ledger_source_labels", t_ledger_source_labels),
    ("unresolved_count_separates_sample", t_unresolved_count_separates_sample),
    ("silences_count_separates_sample", t_silences_count_separates_sample),
    ("regen_pin_stable_under_ledger_growth", t_regen_pin_stable_under_ledger_growth),
    ("write_ro_0444_idempotent", t_write_ro_0444_idempotent),
    ("gen_writes_v4_schema", t_gen_writes_v4_schema),
    ("avail_minute_precision", t_avail_minute_precision),
    ("availability_raises_cut", t_availability_raises_cut),
    ("absent_marker_blocks_absorption", t_absent_marker_blocks_absorption),
    ("meta_sidecar_freezes_availability", t_meta_sidecar_freezes_availability),
    ("no_fs_avail_declared_only", t_no_fs_avail_declared_only),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        t(name, fn)
    ok = sum(RESULTS); n = len(RESULTS)
    print("%d/%d passed" % (ok, n))
    sys.exit(0 if ok == n else 1)
