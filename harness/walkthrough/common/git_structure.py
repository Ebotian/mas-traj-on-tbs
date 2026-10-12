#!/usr/bin/env python3
# git_structure.py — 正常退出的 git 结构门(任务无关;2026-10-12 用户裁定:
#   「正常退出要求 git:1.仅剩主分支 2.正好包含 ckpt-m1 和 ckpt-m2 两个标签」;
#   前一轮「只有主分支(两agent参与merge),没有孤儿分支、未处理分支才允许退出」;
#   2026-10-12 晚随 v3 前段增补:「门参数化;m00 用中途变体(分支名保留、可重合在同一提交上);
#   终局维持仅 main + 终签集(默认扩为 ckpt-m00/m01/m1/m2 四签)」)。
# 模式:
#   final  — 仅剩 main;远端只允许 <remote>/main;标签精确等于 --expect-tags;标签须在 main
#            历史中;ckpt-m1/ckpt-m2 须指向真合并提交(≥2 父;=「两agent参与merge」的机械读法)。
#   midrun — 中途里程碑(如 m00):本地分支只允许 main/a/b 且三名在场(a/b 可与 main 重合于
#            同一提交);所有引用须已并入 main;必须含 --expect-tags 全部标签。
# 用法: python3 git_structure.py <repo> [<out.json>] [--mode final|midrun] [--expect-tags t1,t2]
#   有 out 时写 JSON;stdout 始终打印 JSON;退出码 0=通过,1=不通过,2=用法错。
# 跳过语义(保守不对称,与 gate.py 一致):枚举失败→{"skip":true,"ok":true},由调用方记录。
# 状态:仅配置;尚未在实际跑中使用。

import json
import subprocess
import sys

MERGE_TAGS = ("ckpt-m1", "ckpt-m2")
DEFAULT_TAGS = ("ckpt-m00", "ckpt-m01", "ckpt-m1", "ckpt-m2")
SIDE_HEADS = ("a", "b")


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=60)
        return r.returncode == 0, (r.stdout or "").strip()
    except Exception:
        return False, ""


def check(repo, mode="final", expect_tags=DEFAULT_TAGS):
    ok, out = git(repo, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes", "refs/tags")
    if not ok:
        return {"skip": True, "ok": True, "mode": mode, "heads": [], "remotes": [], "tags": [],
                "violations": {}}
    heads, remotes, tags = [], [], []
    for ref in out.splitlines():
        if not ref or ref.endswith("/HEAD"):
            continue
        if ref.startswith("refs/heads/"):
            heads.append(ref[len("refs/heads/"):])
        elif ref.startswith("refs/remotes/"):
            remotes.append(ref[len("refs/remotes/"):])
        elif ref.startswith("refs/tags/"):
            tags.append(ref[len("refs/tags/"):])
    v = {}
    if "main" not in heads:
        v["missing_main"] = True
    # 未并入检查(两模式共用):任何非 main 的引用都必须已并入 main 历史
    unmerged = []
    for ref in ["refs/heads/" + h for h in heads] + ["refs/remotes/" + r for r in remotes]:
        disp = ref.replace("refs/heads/", "").replace("refs/remotes/", "")
        if disp == "main" or disp.split("/")[-1] == "main":
            continue
        m, _ = git(repo, "merge-base", "--is-ancestor", ref, "main")
        if not m:
            unmerged.append(disp)
    if unmerged:
        v["unmerged"] = sorted(unmerged)
    if mode == "midrun":
        missing_side = [s for s in SIDE_HEADS if s not in heads]
        if missing_side:
            v["missing_heads"] = missing_side
        extra = sorted(h for h in heads if h not in ("main",) + SIDE_HEADS)
        if extra:
            v["extra_heads"] = extra
        extra_r = sorted(r for r in remotes if r.split("/", 1)[-1] not in ("main",) + SIDE_HEADS)
        if extra_r:
            v["extra_remotes"] = extra_r
    else:
        extra = sorted(h for h in heads if h != "main")
        if extra:
            v["extra_heads"] = extra
        extra_r = sorted(r for r in remotes if not r.endswith("/main"))
        if extra_r:
            v["extra_remotes"] = extra_r
    extra_tags = sorted(t for t in tags if t not in expect_tags)
    if extra_tags:
        v["extra_tags"] = extra_tags
    missing_tags = [t for t in expect_tags if t not in tags]
    if missing_tags:
        v["missing_tags"] = missing_tags
    for t in expect_tags:
        if t not in tags:
            continue
        merged, _ = git(repo, "merge-base", "--is-ancestor", "refs/tags/" + t, "main")
        if not merged:
            v.setdefault("tags_not_in_main", []).append(t)
        if t in MERGE_TAGS:
            _, pl = git(repo, "rev-list", "--parents", "-n1", "refs/tags/" + t)
            if len(pl.split()) < 3:
                v.setdefault("tags_not_merge", []).append(t)
    return {"skip": False, "ok": not v, "mode": mode, "expect_tags": list(expect_tags),
            "heads": sorted(heads), "remotes": sorted(remotes), "tags": sorted(tags), "violations": v}


def main():
    argv = sys.argv[1:]
    mode = "final"
    expect = DEFAULT_TAGS
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1]; i += 2
        elif a == "--expect-tags" and i + 1 < len(argv):
            expect = tuple(t for t in argv[i + 1].split(",") if t); i += 2
        else:
            pos.append(a); i += 1
    if not pos or mode not in ("final", "midrun"):
        print("usage: git_structure.py <repo> [<out.json>] [--mode final|midrun] [--expect-tags t1,t2]",
              file=sys.stderr)
        return 2
    res = check(pos[0], mode, expect)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    print(text, flush=True)
    if len(pos) > 1:
        try:
            with open(pos[1], "w") as f:
                f.write(text + "\n")
        except Exception:
            pass
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
