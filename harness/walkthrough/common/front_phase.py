#!/usr/bin/env python3
# front_phase.py — v3 前段(P0)的 IaC 载体(任务无关;2026-10-12 用户裁定:
#   「a 可做」「d 和 a 对应同样的 IAC 实现保证」——方向声明/分歧报告/统一认识清单
#   由同一机械面校验;「触发下发 sop」在 ckpt-m00 落签后由看门件完成)。
# 子命令(容器内):
#   declare <xdir> <side>             写 x/declare-<side> 申报标记(free 开窗条件之一)
#   dispatch <repo> <xdir> [logs]     ckpt-m00 落签后写出 x/sop-m00.md(幂等,看门件用)
#   check <repo> <xdir> <out.json>    校验 understanding/forks/dir 声明并产分歧报告
# 口径:violations 为空=通过;divergence 报告=操纵检查证据(硬检查=top 轴不同 + 引用/合理性注记在场)。
# 2026-10-13 修:choice 先归一化(trim+空白折叠+casefold)再比较——"linear model" 与 "Linear Model"
#   是同一假设,不再计为"不同";假设 ID/引用解析/证伪计划的更细检查另议。
# 状态:仅配置;尚未在实际跑中使用。

import json
import os
import re
import subprocess
import sys
import time

SOP_VERSION = "p0-diverge v1 (2026-10-12)"

SOP_TEXT = """# SOP · %s
# 由 m00 门控通过时触发下发;效力范围:P0.2(方向协商)与 m01 前的准备段。

目标:在不越过「合理假设」边界的前提下,把两侧的研究方向在假设空间里尽可能拉开。

规则:
1. 以 main 上统一认识的 forks.json(按优先级排序的开放分歧轴)为工作清单。
2. 双方经自由沟通协商一致:每个高优先分歧轴上,两侧选择的**主攻假设必须不同**
   (禁止同一假设的「双保险」);未被任何一侧选为主攻的轴保持开放记录。
3. 「合理」的边界:每个主攻假设必须 (a) 给出可引用的支持证据(引用式 refs),且
   (b) 说明其可证伪路径;明显不可检验的假设不得成为主攻。
4. 不做分工:两侧都独立走完整链路;一方替另一方承担环节即违约。
5. 产出(双方各自):x/dir-<actor>.json = {"axes":[{"fork_id","choice","plausibility","refs":[...]}]};
   再运行 `front_phase.py check` 生成 x/divergence.json(分歧报告 = 操纵检查证据)。
6. m01 落签后:交流与轨迹互见中止,直至 M1。
""" % SOP_VERSION


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=60)
        return r.returncode == 0, (r.stdout or "").strip()
    except Exception:
        return False, ""


def _norm_choice(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).casefold()


def cmd_declare(xdir, side):
    p = os.path.join(xdir, "declare-%s" % side)
    try:
        with open(p, "a") as f:
            f.write("%s declare-%s\n" % (now(), side))
    except Exception as e:
        print("declare failed: %r" % e, file=sys.stderr)
        return 1
    print(json.dumps({"declared": side, "at": now(), "file": p}, ensure_ascii=False))
    return 0


def cmd_dispatch(repo, xdir, logs):
    _, tags = git(repo, "tag", "-l")
    if "ckpt-m00" not in tags.split():
        return 0
    out = os.path.join(xdir, "sop-m00.md")
    if os.path.exists(out):
        return 0
    try:
        with open(out, "w") as f:
            f.write(SOP_TEXT)
            f.write("\n---\ndispatched: %s (trigger=ckpt-m00; version=%s)\n" % (now(), SOP_VERSION))
        if logs:
            try:
                with open(os.path.join(logs, "front-phase.log"), "a") as lf:
                    lf.write("%s dispatch sop-m00.md\n" % now())
            except Exception:
                pass
        print(json.dumps({"dispatched": out, "at": now()}, ensure_ascii=False))
    except Exception as e:
        print("dispatch failed: %r" % e, file=sys.stderr)
        return 1
    return 0


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except Exception as e:
        return None, repr(e)


def cmd_check(repo, xdir, out):
    violations = []
    forks_doc = None
    ok, text = git(repo, "show", "main:forks.json")
    if not ok:
        violations.append("forks.json missing on main (m00 deliverable)")
    else:
        try:
            forks_doc = json.loads(text)
        except Exception as e:
            violations.append("forks.json parse error: %r" % e)
    forks = []
    if isinstance(forks_doc, dict):
        forks = forks_doc.get("forks") or []
    elif isinstance(forks_doc, list):
        forks = forks_doc
    forks = [f for f in forks if isinstance(f, dict) and f.get("id")]
    forks.sort(key=lambda f: f.get("priority", 999))
    fork_ids = [str(f["id"]) for f in forks]

    dirs = {}
    for side in ("a", "b"):
        d, err = _load_json(os.path.join(xdir, "dir-%s.json" % side))
        if err:
            violations.append("dir-%s.json missing/unreadable: %s" % (side, err))
            dirs[side] = []
            continue
        axes = d.get("axes") if isinstance(d, dict) else None
        if not isinstance(axes, list):
            violations.append("dir-%s.json: axes[] missing" % side)
            dirs[side] = []
            continue
        clean = []
        for ax in axes:
            if not isinstance(ax, dict) or not ax.get("fork_id"):
                violations.append("dir-%s.json: axis without fork_id" % side)
                continue
            fid = str(ax.get("fork_id"))
            if fid not in fork_ids:
                violations.append("dir-%s.json: fork_id %s not in forks.json" % (side, fid))
            refs = ax.get("refs")
            if not isinstance(refs, list) or not refs:
                violations.append("dir-%s.json: fork %s has no refs (引用式要求)" % (side, fid))
            if not ax.get("plausibility"):
                violations.append("dir-%s.json: fork %s has no plausibility note" % (side, fid))
            clean.append({"fork_id": fid, "choice": str(ax.get("choice", "")), "refs": refs or []})
        dirs[side] = clean

    divergence = {}
    for fid in fork_ids:
        ca = [x["choice"] for x in dirs["a"] if x["fork_id"] == fid]
        cb = [x["choice"] for x in dirs["b"] if x["fork_id"] == fid]
        # 归一化后比较:仅大小写/空白不同 ⇒ 同一假设("linear model" vs "Linear Model")
        divergence[fid] = {"a": ca, "b": cb,
                           "differ": bool(ca and cb and _norm_choice(ca[0]) != _norm_choice(cb[0]))}
    top = fork_ids[0] if fork_ids else None
    if top and not (divergence[top]["a"] and divergence[top]["b"]):
        violations.append("top fork %s not covered by both sides" % top)
    elif top and not divergence[top]["differ"]:
        violations.append("top fork %s: both sides chose the same primary hypothesis (SOP rule 2)" % top)
    differing = sum(1 for f in fork_ids if divergence[f]["differ"])
    report = {"at": now(), "ok": not violations, "violations": violations,
              "sop_version": SOP_VERSION, "forks": fork_ids,
              "divergence": divergence, "differing_count": differing, "compared": len(fork_ids)}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    print(text)
    try:
        with open(out, "w") as f:
            f.write(text + "\n")
    except Exception as e:
        print("write %s failed: %r" % (out, e), file=sys.stderr)
    return 0 if report["ok"] else 1


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "declare" and len(sys.argv) >= 4:
        return cmd_declare(sys.argv[2], sys.argv[3])
    if len(sys.argv) >= 2 and sys.argv[1] == "dispatch" and len(sys.argv) >= 4:
        return cmd_dispatch(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) >= 5 else "")
    if len(sys.argv) >= 2 and sys.argv[1] == "check" and len(sys.argv) >= 5:
        return cmd_check(sys.argv[2], sys.argv[3], sys.argv[4])
    print("usage: front_phase.py declare <xdir> <side> | dispatch <repo> <xdir> [logs] | "
          "check <repo> <xdir> <out.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
