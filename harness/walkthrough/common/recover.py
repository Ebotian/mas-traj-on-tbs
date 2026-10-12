#!/usr/bin/env python3
# recover.py — 收口机制补充(2026-10-12;用户裁定「只做机制补充;先更新配置,不运行」)。
#
# 背景(动机,来自 2026-10-12 对既有跑 git 现场的机械核对与只读回放):
#   m1 = duty 未完成:main 停在 "M1 merge b";缺 ckpt-m2 与 main:consensus.md;两侧分支均未并入;
#   m2 = duty 已完成:ckpt-m1/m2 齐、consensus on main,仅"双停握手"竞速(abort-b 在场、stop-b 缺),
#        但残留短分支 p3-r8-b 引用未删;
#   结构门裁定(2026-10-12,用户):「正常退出要求 git:1.仅剩主分支 2.正好包含 ckpt-m1 和
#   ckpt-m2 两个标签」;晚补:随 v3 前段加入 ckpt-m00/m01,终签集默认扩为四签、门参数化——
#   任务无关要求,检查实现于 common/git_structure.py(本脚本复用同一模块);
#   只读回放(w4/w5/w6/tumor-1/2/microarch-1/2 的 protocol.bundle):w5/w6 的 b 分支停着未并入的
#   P2 r4/r5 内容(review-b-to-a.md 不在 main);tumor-1 叠 b 的 r6 提交与两个短分支残引;
#   全部历史跑都残留 a/b 分支与 ckpt-final 标签 ⇒ 均不满足新终态。
#
# 本脚本由 tasks/*/run.sh 在两会话退出后调用一次:
#   (A) duty 审计(git 机械事实,纯读):--expect-tags(默认 ckpt-m00/m01/m1/m2)/consensus-on-main;记录两分支尖;
#   (B) 结构审计(复用 git_structure.py):仅剩 main + 正好两个标签 + 标签在 main 且为真合并;
#   (C) 受限唤醒(≤1 次/侧):续原会话(同一 session-id)——补 duty、按"先并入、再删除"把结构收到终态
#       (分支/worktree/多余标签);中止侧(abort-<x> 在场且无 stop)另给一次复核;
#   (D) 全部结果写 $X/recover.json(run.sh 的 state 收集并入 state 的 recover 字段;
#       结构终态另由 wrapper 直接调用 git_structure.py 独立复核,作为 normal 判据的一部分)。
#
# 硬约束(写死在唤醒 prompt 里):只许新增提交、写标记文件、删除残留分支/标签引用及 worktree
#   (删引用不改写历史);禁止 rebase/amend/force;不动交付物字节;不提/不改科学结论。
#   开关与上限:WT_RECOVER=0 关闭唤醒(wrapper 的结构门独立,不随此开关);
#   WT_WAKE_TIMEOUT 秒(默认 900);每侧 ≤1;距 SESSION_WALL 预算不足时自动跳过(记 skipped)。
# 用法(容器内): python3 recover.py <repo> <xdir> <logs> <uuid-a> <uuid-b>
# 状态:机制补充 v4(前段 ckpt-m00/m01 并入;终签集参数化);尚未运行(首次使用前建议 walkthrough 排练一次)。

import json
import os
import pathlib
import subprocess
import sys
import time

try:
    import git_structure
except Exception:
    git_structure = None

MODEL = {"a": "deepseek-flash", "b": "qwen3.8-flash"}
KEYENV = {"a": "A_KEY", "b": "B_KEY"}
BASEENV = {"a": "A_BASE", "b": "B_BASE"}
TAGS = tuple(t for t in os.environ.get("WT_EXPECT_TAGS", "ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2").split(",") if t)
MILESTONES = tuple(t.replace("-", "_") for t in TAGS) + ("consensus_on_main",)
LBL = {t.replace("-", "_"): "缺少 %s 标签" % t for t in TAGS}
LBL["consensus_on_main"] = "main 上没有 consensus.md"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=60)
        return r.returncode == 0, (r.stdout or "").strip()
    except Exception:
        return False, ""


def audit(repo):
    f = {}
    for t in TAGS:
        ok, _ = git(repo, "rev-parse", "-q", "--verify", "refs/tags/" + t)
        f[t.replace("-", "_")] = ok
    ok, _ = git(repo, "show", "main:consensus.md"); f["consensus_on_main"] = ok
    for s in ("a", "b"):
        ok, tip = git(repo, "rev-parse", "--short", s)
        if ok:
            _, subj = git(repo, "log", "-1", "--format=%s", s)
            f["tip_" + s] = ("%s %s" % (tip, subj)).strip()
        else:
            f["tip_" + s] = "(无此引用)"
    f["pending"] = [k for k in MILESTONES if not f[k]]
    return f


def structure(repo):
    if git_structure is None:
        return {"skip": True, "ok": True, "heads": [], "remotes": [], "tags": [], "violations": {}}
    try:
        return git_structure.check(repo, mode="final", expect_tags=TAGS)
    except Exception:
        return {"skip": True, "ok": True, "heads": [], "remotes": [], "tags": [], "violations": {}}


def structure_clause(side, st):
    if st.get("skip") or st.get("ok"):
        return ""
    v = st.get("violations", {})
    L = ["Git 终态结构检查未通过(任务无关要求;不通过会阻止正常退出)。要求:仓库只保留 main 分支(本地与 origin 镜像都算);标签正好等于协议检查点集(" + ",".join(TAGS) + ",共 %d 个);任何分支上的内容必须先并入 main 再删除。当前违规:" % len(TAGS)]
    if v.get("missing_main"):
        L.append("- main 分支缺失")
    if v.get("extra_heads"):
        L.append("- 多余本地分支: " + ", ".join(v["extra_heads"]) + " —— 内容并入 main 后删除;若其 worktree 还在,先 `git worktree remove --force /root/wt/<侧>` 再 `git branch -D <名>`")
    if v.get("extra_remotes"):
        L.append("- 多余远端分支引用: " + ", ".join(v["extra_remotes"]) + " —— `git push origin --delete <分支名>`")
    if v.get("extra_tags"):
        L.append("- 多余标签: " + ", ".join(v["extra_tags"]) + " —— `git tag -d <名>`;origin 有则 `git push origin :refs/tags/<名>`")
    if v.get("missing_tags"):
        L.append("- 缺少标签: " + ", ".join(v["missing_tags"]) + " —— 按协议在对应里程碑的合并提交上补打")
    if v.get("tags_not_in_main"):
        L.append("- 标签未并入 main 历史: " + ", ".join(v["tags_not_in_main"]))
    if v.get("tags_not_merge"):
        L.append("- 标签未指向真合并提交(≥2 父): " + ", ".join(v["tags_not_merge"]))
    L.append("处理原则:先核对并把未并入的内容经 merge 并入 main(只新增提交);确认对侧分支没有未并入提交之前,不得删除对侧分支;最后把分支/多余标签/worktree 清理到只剩 main 与协议标签集。你侧= %s。" % side)
    return "\n".join(L)


def compose_prompt(side, f, st, x, has_abort, has_stop):
    peer = "b" if side == "a" else "a"
    if f["pending"]:
        duty = "\n".join("- " + LBL[k] for k in f["pending"])
        duty_clause = ("git 现场核对,协议里程碑待办:\n" + duty +
                       "\n请严格按你已掌握的协议,仅用**新增提交**补齐以上待办(合并、打 ckpt 标签、consensus.md 落 main)。")
    else:
        duty_clause = "git 现场显示机械里程碑均已齐(无待办)。"
    parts = ["【恢复会话·仅补收口 duty】actor %s,这是你原会话的续会(历史与协议上下文都在);对侧为 %s。" % (side, peer),
             duty_clause,
             "分支尖: a=`%s`;b=`%s`。" % (f["tip_a"], f["tip_b"])]
    sc = structure_clause(side, st)
    if sc:
        parts.append(sc)
    if has_abort:
        parts.append("你此前写过 abort-%s。请按完整 git 事实复核一次:若撤回中止 → 写 `%s/abort-%s.withdrawn`(一行理由)并写 `%s/stop-%s`;若维持 → 什么都不写。" % (side, x, side, x, side))
    elif not has_stop:
        parts.append("若你判断整跑此刻可以正常收口 → 写 `%s/stop-%s`;否则直接结束。" % (x, side))
    parts.append("硬约束:只允许新增提交、写上述标记文件、删除残留分支/标签引用及 worktree(删引用≠改写历史);禁止 rebase/amend/force,不得改写任何既有提交;不得改动交付物字节;不得提出或修改科学结论。完成后立即结束会话,不做范围外的工作。")
    return "\n\n".join(parts)


def wake(side, repo, x, logs, uuid, timeout_s, prompt):
    wt = os.path.dirname(os.path.abspath(repo))
    env = os.environ.copy()
    out = os.path.join(logs, "wa-%s-wake.out" % side)
    cmd = ["qwen", "-p", prompt,
           "--auth-type", "openai",
           "--openai-api-key", env.get(KEYENV[side], ""),
           "--openai-base-url", env.get(BASEENV[side], ""),
           "-m", MODEL[side],
           "--approval-mode", "yolo", "--chat-recording",
           "-r", uuid,
           "--telemetry", "--telemetry-outfile", os.path.join(logs, "otel-%s-wake.json" % side)]
    t0 = time.time()
    cwd = os.path.join(wt, side)
    note = ""
    try:
        if not os.path.isdir(cwd):
            # A duty/structure wake may have removed this side's worktree
            # (`git worktree remove`).  The chat store is keyed by the cwd
            # path string, so recreating an empty dir keeps `-r <uuid>` able
            # to resume.  Never crash here (w7: wake-b hit FileNotFoundError
            # and recorded a crash-y rc=125, silently skipping the duty).
            os.makedirs(cwd, exist_ok=True)
            note = "cwd recreated (was missing)"
    except OSError as e:
        note = "cwd unavailable: %r" % e
        try:
            with open(out, "a") as fo:
                fo.write("\n[recover] wake skipped: %s\n" % note)
        except Exception:
            pass
        return {"side": side, "rc": None, "dur_s": round(time.time() - t0, 1),
                "skip": note}
    try:
        with open(out, "a") as fo:
            r = subprocess.run(cmd, cwd=cwd, stdout=fo, stderr=subprocess.STDOUT,
                               timeout=timeout_s, env=env)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    except Exception as e:
        rc = 125
        try:
            with open(out, "a") as fo:
                fo.write("\n[recover] wake failed: %r\n" % e)
        except Exception:
            pass
    rec = {"side": side, "rc": rc, "dur_s": round(time.time() - t0, 1)}
    if note:
        rec["note"] = note
    return rec


def main():
    if len(sys.argv) < 6:
        print("usage: recover.py <repo> <xdir> <logs> <uuid-a> <uuid-b>", file=sys.stderr)
        return 1
    repo, x, logs, ua, ub = sys.argv[1:6]
    xp = pathlib.Path(x)
    session_wall = int(os.environ.get("WT_SESSION_WALL", "13500") or "13500")
    cfg = {"enabled": os.environ.get("WT_RECOVER", "1") == "1",
           "timeout_s": int(os.environ.get("WT_WAKE_TIMEOUT", "900") or "900"),
           "max_per_side": 1}
    rec = {"at": now(), "cfg": cfg, "notes": []}
    try:
        f0 = audit(repo)
        s0 = structure(repo)
        rec["duties_before"] = f0
        rec["structure_before"] = s0
        wakes = []
        if not cfg["enabled"]:
            rec["notes"].append("recover disabled (WT_RECOVER=0)")
        else:
            # 预算守卫:距 SESSION_WALL 太近则不唤醒(以仓库根提交时间为近似起点)
            _, ct = git(repo, "log", "--format=%ct", "--all")
            try:
                start_ts = min(int(t) for t in ct.splitlines() if t.strip())
                elapsed = time.time() - start_ts
            except Exception:
                elapsed = 0
            budget_left = session_wall - elapsed - 300
            if budget_left < 120:
                rec["notes"].append("skipped: only %ds of session budget left" % int(budget_left))
            else:
                uuids = {"a": ua, "b": ub}
                for side in ("a", "b"):
                    has_abort = (xp / ("abort-" + side)).exists()
                    has_stop = (xp / ("stop-" + side)).exists()
                    duty = bool(f0["pending"])
                    reconcile = has_abort and not has_stop
                    struct_bad = not (s0.get("skip") or s0.get("ok"))
                    if not (duty or reconcile or struct_bad):
                        continue
                    tags = (["duty"] if duty else []) + (["structure"] if struct_bad else []) + (["reconcile"] if reconcile else [])
                    prompt = compose_prompt(side, f0, s0, x, has_abort, has_stop)
                    w = wake(side, repo, x, logs, uuids.get(side, ""), cfg["timeout_s"], prompt)
                    w["mode"] = "+".join(tags)
                    w["at"] = now()
                    wakes.append(w)
                    f0 = audit(repo)
                    s0 = structure(repo)
        rec["wakes"] = wakes
        fa = audit(repo)
        sa = structure(repo)
        rec["duties_after"] = fa
        rec["structure_after"] = sa
        rec["stop_after"] = {s: (xp / ("stop-" + s)).exists() for s in ("a", "b")}
        rec["abort_withdrawn"] = {s: (xp / ("abort-" + s + ".withdrawn")).exists() for s in ("a", "b")}
    except Exception as e:
        rec["error"] = repr(e)
    finally:
        try:
            (xp / "recover.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        except Exception:
            pass
    print("RECOVER", json.dumps(rec, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
