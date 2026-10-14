#!/usr/bin/env python3
"""replay.py — traj_stats v4「可得性上界」只读重放(2026-10-14)。

目的:对四个已交付审查包(t3/m5/m3/m4)的 ckpt-m01,以 v4 代码 + --no-fs-avail 在临时目录重生成统计,
逐包核对:
  1) schema = traj-stats/4;
  2) cut_epoch == max(标签提交时间, 全部来源 available_at)(构造性不变量);
  3) 每个已见来源的 available_at ≤ cut_epoch(评审不变量 ∀source ≤ decision);
  4) 新 cut ≥ 旧 cut(修复只推后时基, 不提前);
  5) 新 cut ≥ 评审表列出的 later dependency(分钟精度自述 at 按 v4 向上取整到 :59, 允许恰等于或更晚);
  6) 无显式时间信号的来源(dir 自述 at 缺失 + mtime 通道关闭)恰好进入 unknown 残值清单。

采集包一律只读:仅读 protocol.bundle / x/ / chats/;重放一律在 mktemp 临时目录;证据落在本目录
(<name>-stats/ckpt-m01.{json,md} + summary.txt)。
"""
import calendar
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SELF = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SELF, "..", "..", ".."))
TRAJ = os.path.join(ROOT, "harness", "walkthrough", "common", "traj_stats.py")
B1 = os.path.join(ROOT, "local2gpt", "out", "tumor-3-microarch-5-raw-lite-2026-10-14")
B2 = os.path.join(ROOT, "local2gpt", "out", "microarch-3-4-raw-lite-2026-10-13")

# name, collect 目录, 期望新 cut(ISO), 评审表 later dependency(ISO), 期望 unknown
PACKETS = [
    ("t3", os.path.join(B1, "tumor-3/task-restricted__kmsVE9s/artifacts/root/wt/collect"),
     "2026-10-13T14:44:36", "2026-10-13T14:44:36", ["protocol.dirs.a"]),
    ("m5", os.path.join(B1, "microarch-5/task-microarch__NjyxpAy/artifacts/root/wt/collect"),
     "2026-10-13T14:58:59", "2026-10-13T14:58:00", []),
    ("m3", os.path.join(B2, "microarch-3/task-microarch__pTrPCCa/artifacts/root/wt/collect"),
     "2026-10-12T16:06:36", "2026-10-12T16:06:36", ["protocol.dirs.a", "protocol.dirs.b"]),
    ("m4", os.path.join(B2, "microarch-4/task-microarch__T4uQyxQ/artifacts/root/wt/collect"),
     "2026-10-12T16:32:17", "2026-10-12T16:32:17", ["protocol.dirs.a", "protocol.dirs.b"]),
]


def iso_epoch(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%S"))


def epoch_iso(e):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(e))


def copy_ro(src, dst_dir, name):
    dst = os.path.join(dst_dir, name)
    if os.path.exists(dst):
        os.chmod(dst, 0o644)
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o444)


def run_one(name, collect, exp_cut_iso, dep_iso, exp_unknown):
    exp_cut, dep = iso_epoch(exp_cut_iso), iso_epoch(dep_iso)
    tmp = tempfile.mkdtemp(prefix="traj-v4-replay-%s-" % name)
    checks, notes = [], []
    try:
        repo = os.path.join(tmp, "repo")
        r = subprocess.run(["git", "clone", "-q", os.path.join(collect, "protocol.bundle"), repo],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, ["git clone failed: %s" % r.stderr.strip()[:200]], tmp
        xdir = os.path.join(tmp, "x")
        shutil.copytree(os.path.join(collect, "x"), xdir)
        old = json.load(open(os.path.join(collect, "x", "stats", "ckpt-m01.json")))
        old_cut = old["meta"]["cut_epoch"]
        old_schema = old["meta"].get("schema")
        uu = {}
        for s in ("a", "b"):
            uu[s] = open(os.path.join(xdir, "session-%s.uuid" % s), encoding="utf-8").read().strip()
        cmd = [sys.executable, TRAJ, "gen", repo, xdir, "ckpt-m01",
               "--out", os.path.join(xdir, "stats"), "--no-fs-avail",
               "--transcript-a", os.path.join(collect, "chats", uu["a"] + ".jsonl"),
               "--transcript-b", os.path.join(collect, "chats", uu["b"] + ".jsonl")]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return None, ["traj_stats gen failed: %s" % r.stderr.strip()[:200]], tmp
        new = json.load(open(os.path.join(xdir, "stats", "ckpt-m01.json")))
        av = new["availability"]
        cut = av["cut_epoch"]
        srcs = av.get("sources") or {}
        known = {k: v for k, v in srcs.items() if isinstance(v.get("available_at"), int)}
        max_src = av.get("max_source_available_at")
        carriers = sorted(k for k, v in known.items() if v["available_at"] == max_src)
        checks = [
            ("schema=traj-stats/4", new["meta"]["schema"] == "traj-stats/4"),
            ("cut==max(tag,srcs)", cut == max([av["tag_commit_epoch"]] + [v["available_at"] for v in known.values()])),
            ("∀src<=cut", all(v["available_at"] <= cut for v in known.values())),
            ("cut>=old", cut >= old_cut),
            ("cut>=dep", cut >= dep),
            ("cut==exp", cut == exp_cut),
            ("unknown==exp", sorted(av.get("unknown") or []) == sorted(exp_unknown)),
        ]
        outdir = os.path.join(SELF, name + "-stats")
        os.makedirs(outdir, exist_ok=True)
        copy_ro(os.path.join(xdir, "stats", "ckpt-m01.json"), outdir, "ckpt-m01.json")
        copy_ro(os.path.join(xdir, "stats", "ckpt-m01.md"), outdir, "ckpt-m01.md")
        ol = {s: old["meta"]["transcripts"][s].get("lines_leq_cut") for s in ("a", "b")}
        nl = {s: new["meta"]["transcripts"][s].get("lines_leq_cut") for s in ("a", "b")}
        info = {
            "name": name, "collect": os.path.relpath(collect, ROOT),
            "old_cut": old_cut, "old_schema": old_schema,
            "cut": cut, "max_src": max_src, "carriers": carriers,
            "carrier_basis": {k: known[k].get("basis") for k in carriers},
            "carrier_ref": {k: known[k].get("ref") for k in carriers},
            "unknown": sorted(av.get("unknown") or []), "known_n": len(known),
            "delta": cut - old_cut, "exp_cut": exp_cut, "dep": dep,
            "lines_old": ol, "lines_new": nl, "checks": checks,
        }
        return info, notes, tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    blocks, fails = [], []
    for name, collect, exp_cut_iso, dep_iso, exp_unknown in PACKETS:
        info, notes, _ = run_one(name, collect, exp_cut_iso, dep_iso, exp_unknown)
        if info is None:
            fails.append("%s: %s" % (name, "; ".join(notes)))
            blocks.append("%s: FAIL %s" % (name, "; ".join(notes)))
            continue
        bad = [c for c, ok in info["checks"] if not ok]
        if bad:
            fails.append("%s: checks failed: %s" % (name, ", ".join(bad)))
        car = ", ".join("%s@%s(basis=%s)" % (k, epoch_iso(info["max_src"]) if info["max_src"] else "-",
                                             info["carrier_basis"].get(k, "-")) for k in info["carriers"])
        blk = [
            "%s: 旧 cut %s(%d, %s) → 新 cut %s(%d, traj-stats/4) Δ%+ds"
            % (name, epoch_iso(info["old_cut"]), info["old_cut"], info["old_schema"],
               epoch_iso(info["cut"]), info["cut"], info["delta"]),
            "   承载来源: %s;已知来源 %d 个,unknown 残值: %s"
            % (car or "-", info["known_n"], ", ".join(info["unknown"]) or "-"),
            "   transcript ≤cut 行数 a/b: 旧 %s/%s → 新 %s/%s"
            % (info["lines_old"]["a"], info["lines_old"]["b"], info["lines_new"]["a"], info["lines_new"]["b"]),
            "   核对: " + "; ".join("%s %s" % (c, "✓" if ok else "✗") for c, ok in info["checks"]),
        ]
        blocks.append("\n".join(blk))
        print("\n".join(blk))
        print()

    summary = [
        "traj_stats v4「可得性上界」只读重放样本(2026-10-14)",
        "",
        "来源:对四个已交付审查包的 collect(protocol.bundle + x/ + chats)的 scratch 重算(mktemp 临时目录,",
        "原 collect 未动);脚本:harness/refs/traj-stats-v4-check/replay.py(v4 + --no-fs-avail);",
        "输出:本目录 <name>-stats/ckpt-m01.{json,md}(0444)。",
        "语义:cut_epoch = max(标签提交时间, 全部来源 available_at);--no-fs-avail 关闭 mtime 通道",
        "(归档副本 mtime=采集时刻,不可信,只信自述 at);分钟精度自述 at(「…T14:58Z」)向上取整到 :59。",
        "评审不变量:每个已见来源 available_at ≤ cut(构造性成立);新 cut ≥ 评审表 later dependency(lag ≤ 0)。",
        "",
        "对照(旧 = 包内 v2/v3 产物;新 = v4 重放):",
        "",
    ]
    summary.extend(blocks)
    summary.append("")
    summary.append("VERDICT: " + ("ALL OK" if not fails else "FAIL: " + " | ".join(fails)))
    with open(os.path.join(SELF, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    print("VERDICT: " + ("ALL OK" if not fails else "FAIL: " + " | ".join(fails)))
    print("summary: %s" % os.path.join(SELF, "summary.txt"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
