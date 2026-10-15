#!/usr/bin/env python3
"""check.py — crossfusion-2026-10-15 验收:一条命令,全部确定性、零模型调用。

  cd harness/refs/crossfusion-2026-10-15 && python3 check.py

四层检查:
  1) 逐字节复现——重跑 extract_cross.py 到临时目录,与仓库内 features_union.jsonl /
     audit.json / summary.md 逐字节比对(再跑 paper_checks.py 重建其三个产物)
  2) 不变式——单元数/调用数/格式/notes/审计字段/逐单元自洽(名表=类别表=总数;掩蔽≤可判;
     熵在界内;gaps 数≤调用数-1)
  3) 独立对照——与 traj-features-2026-10-14 lab 的 features_sides.jsonl(54 侧 × 13 字段)
     与 features_arms.jsonl(8 臂 × calls/masked)对读
  4) 论文复算——paper_checks.py 必须 paper 级 0 不一致(4 处 card 级偏差为登记发现,不判失效)
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

LAB = Path(__file__).resolve().parent
TRAJ_LAB = Path("/home/ebt/rsi-dev/harness/refs/traj-features-2026-10-14")

FAILS: list = []


def fail(msg: str) -> None:
    FAILS.append(msg)
    print("FAIL:", msg)


def ok(msg: str) -> None:
    print(" ok :", msg)


def want(cond: bool, msg: str) -> None:
    (ok if cond else fail)(msg)


def jl(path: Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main() -> int:
    # ---------- 1) 逐字节复现 ----------
    tmp = Path(tempfile.mkdtemp(prefix="crossfusion-check-"))
    try:
        r = subprocess.run([sys.executable, str(LAB / "extract_cross.py"), "--out", str(tmp)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"extract_cross.py 非零退出 ({r.returncode}): {r.stderr.strip()[-400:]}")
        for name in ("features_union.jsonl", "audit.json", "summary.md"):
            a, b = LAB / name, tmp / name
            if not b.exists():
                fail(f"{name}: 重跑未产出")
            elif a.read_bytes() != b.read_bytes():
                fail(f"{name}: 逐字节不一致(仓库 {len(a.read_bytes())}B / 重跑 {len(b.read_bytes())}B)")
            else:
                ok(f"逐字节复现 {name} ({len(a.read_bytes())}B, sha256 {sha12(a)}…)")

        r2 = subprocess.run([sys.executable, str(LAB / "paper_checks.py")], capture_output=True, text=True)
        if r2.returncode != 0:
            fail(f"paper_checks.py 非零退出: {r2.stdout.strip()[-400:]}")

        # ---------- 2) 不变式 ----------
        recs = jl(LAB / "features_union.jsonl")
        au = json.loads((LAB / "audit.json").read_text(encoding="utf-8"))
        ours = [x for x in recs if x["source"] == "ours"]
        are = [x for x in recs if x["source"] == "are"]
        sides = [x for x in ours if x["corpus"] != "arm"]
        arms = [x for x in ours if x["corpus"] == "arm"]
        want(len(recs) == 862 and len(ours) == 62 and len(are) == 800,
             f"单元数 862 = 62 ours(54 侧 + 8 臂)/ 800 are(实 {len(recs)}/{len(ours)}/{len(are)})")
        want(len(sides) == 54 and len(arms) == 8, f"ours 侧 54 / 臂 8(实 {len(sides)}/{len(arms)})")
        calls_ours = sum(x["calls_total"] for x in ours)
        calls_are = sum(x["calls_total"] for x in are)
        calls_sides = sum(x["calls_total"] for x in sides)
        want(calls_ours == 9190 and calls_are == 73842 and calls_sides == 8462,
             f"调用:ours {calls_ours}(侧 {calls_sides} + 臂 {calls_ours - calls_sides}) / are {calls_are}")
        want(round(calls_are / 800, 4) == 92.3025, f"are 均值 {calls_are / 800:.4f}/跑(论文 92.3)")
        fmts = Counter(x["format"] for x in are)
        want(dict(fmts) == {"claude_stream": 600, "gemini_text": 69, "codex_text": 70,
                            "codex_items": 30, "gemini_ndjson": 30, "unknown": 1},
             f"are 格式分布 {dict(fmts)}")
        notes = Counter(tuple(x["notes"]) for x in recs)
        want(dict(notes) == {(): 846, ("empty-file",): 1, ("result-first",): 10,
                             ("result-first", "no-calls"): 5},
             f"notes 分布 {dict(notes)}")
        want(sum(1 for x in recs if x["calls_total"] == 0) == 6, "0 调用单元 = 6(1 empty-file + 5 result-first/no-calls)")
        want(au["unmapped"] == {}, f"审计:未映射工具名 {au['unmapped']}（应为空）")
        want(au["ours_side_nonstandard"] == {"bash": 1, "edit_file": 3, "edit_file_path": 1,
                                             "shell_command": 1, "tool_call": 3},
             "审计:ours 侧表外名 9 次(归 other,与 lab 一致)")
        want(len(au["defect_occurrences"]) == 2 and all("qwen3.7-max" in d for d in au["defect_occurrences"]),
             "审计:2 处 __unparsedToolInput 工件(均 qwen3.7-max)")
        oc = au["ours_compare"]
        want(oc["checked"] == 54 and not oc["mismatch"], "审计:ours 侧 54/54 与 lab 逐字段一致")
        ac = au["are_compare"]
        want(ac["gemini_stats_checked"] == 27 and len(ac["mismatch"]) == 1
             and ac["mismatch"][0]["unit"].endswith("mehnet_ccsdt_energy")
             and ac["mismatch"][0]["stats_tool_calls"] == 122 and ac["mismatch"][0]["ours"] == 86,
             "审计:gemini 对账 27 文件,恰 1 处数据自相矛盾(mehnet 122 vs 86)")

        bad_unit = 0
        for x in recs:
            if sum(x["calls_by_name"].values()) != x["calls_total"] or sum(x["kinds"].values()) != x["calls_total"]:
                bad_unit += 1
            if x["masked"] > x["results_judged"]:
                bad_unit += 1
            if x["calls_total"] >= 2:
                if x["kind_entropy"] is None or x["transition_entropy"] is None \
                        or not (0 <= x["kind_entropy"] <= 3 + 1e-9) \
                        or not (0 <= x["transition_entropy"] <= math.log(8) + 1e-9):
                    bad_unit += 1
            if x["gaps_n"] > max(0, x["calls_total"] - 1):
                bad_unit += 1
        want(bad_unit == 0, f"逐单元自洽(名表/类别表/掩蔽/熵界/gaps 界):{bad_unit} 处异常")
        per_model = Counter(x["model"] for x in are)
        want(len(per_model) == 8 and all(v == 100 for v in per_model.values()),
             f"are 逐模型各 100 单元 {dict(per_model)}")

        # ---------- 3) 与 lab 独立对读 ----------
        lab_sides = {(x["job"], x["trial"], x["side"]): x for x in jl(TRAJ_LAB / "features_sides.jsonl")}
        lab_arms = {(x["job"], x["trial"]): x for x in jl(TRAJ_LAB / "features_arms.jsonl")}
        F13 = ("calls_total", "calls_by_name", "kinds", "gaps_n", "gaps_median_s", "gaps_cv_robust",
               "gaps_p600_frac", "masked", "kind_entropy", "transition_entropy", "span_s", "cache_ratio",
               "out_tokens_sum")
        n_side_bad = 0
        for x in sides:
            _, job, trial, side = x["unit"].split("/")
            lab = lab_sides.get((job, trial, side))
            if lab is None:
                n_side_bad += 1
                continue
            for f in F13:
                if x.get(f) != lab.get(f):
                    n_side_bad += 1
        want(n_side_bad == 0, "lab 对读:54 侧 × 13 字段全部相等")
        n_arm_bad = 0
        for x in arms:
            _, job, trial, _ = x["unit"].split("/")
            lab = lab_arms.get((job, trial))
            if lab is None:
                n_arm_bad += 1
                continue
            for f in ("calls_total", "masked"):
                if x.get(f) != lab.get(f):
                    n_arm_bad += 1
        want(n_arm_bad == 0, "lab 对读:8 臂 calls/masked 相等")
        want(sum(x["masked"] for x in arms) == 26, "lab 对读:臂掩蔽合计 26")

        # ---------- 4) 论文复算 ----------
        pc = json.loads((LAB / "paper_checks.json").read_text(encoding="utf-8"))
        cc = Counter(c["status"] for c in pc["checks"])
        bad_paper = [c["id"] for c in pc["checks"] if c["scope"] == "paper" and c["status"] == "MISMATCH"]
        bad_card = [c["id"] for c in pc["checks"] if c["scope"] == "card" and c["status"] == "MISMATCH"]
        want(not bad_paper, f"paper 级 0 不一致(实 {bad_paper})")
        want(len(bad_card) == 4, f"card 级登记偏差恰 4 处({bad_card})")
        want((cc["PASS"], cc["RECORD"]) == (30, 3), f"复算计数 PASS {cc['PASS']} / RECORD {cc['RECORD']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"FAIL:{len(FAILS)} 处")
        return 1
    print("PASS:四层全部通过(逐字节复现 / 不变式 / lab 对读 / 论文复算)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
