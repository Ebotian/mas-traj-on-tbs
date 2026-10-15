#!/usr/bin/env python3
"""paper_checks.py — AutoResearchEval 论文数字的机械复算(零 LLM,确定性)。

对论文(arXiv 2608.14905v3;表格文本由 parse_paper_tables.py 自 LaTeXML HTML 提取,
sha256 钉于 paper_tables.json)与 HuggingFace 数据卡(README.md)中可机核的数字逐条复算,
并对并集产物 features_union.jsonl 做语料级复算。产物:

  - paper_checks.json / paper_checks.md —— 逐条 {claim, 来源, expected, actual, status}
  - arft.json —— 45 模式 × 四支柱参照表(入库参照;含 per-model HIT 向量)

status:PASS / MISMATCH / RECORD(记录性数字,无可比对断言)。
退出码:仅当 scope=paper 的条目出现 MISMATCH 时为 1(card/data 级偏差照实记录,不判失败)。

复核范围(与 AGENTS.md 一致):核对的是论文所载数字与数据的【自洽/复算】,以及
HF 卡片数字与磁盘数据的一致性;不重跑论文的 LLM judge,不复核正文推断性结论。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

LAB = Path(__file__).resolve().parent
ARE = Path("/home/ebt/harbor-runs/data/autoresearch-eval")


def cells(i: int):
    pt = json.loads((LAB / "paper_tables.json").read_text())
    tabs = pt["tables"]
    return [[" ".join(str(c).split()) for c in row] for row in tabs[i]["rows"]], pt


def pct1(hit: int, denom: int) -> float:
    # 论文 HIT% 用 half-even 舍入(实测 5 处 .25 边界全下舍,如 498→62.2;与其余 40 行一致)
    return float((Decimal(hit) / Decimal(denom) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN))


checks: list = []


def chk(cid, scope, claim, expected, actual, status=None, note=""):
    if status is None:
        status = "PASS" if expected == actual else "MISMATCH"
    checks.append({"id": cid, "scope": scope, "claim": claim, "expected": expected,
                   "actual": actual, "status": status, "note": note})


def main() -> int:
    t3, pt = cells(2)
    t6, _ = cells(5)
    t11, _ = cells(10)
    t12, _ = cells(11)
    t13, _ = cells(12)
    t22, _ = cells(21)
    t23, _ = cells(22)

    # ---- Table 12:45 模式 × HIT ----
    pat12 = []
    for r in t12[1:]:
        if re.match(r"^[A-FX]\.\d+$", r[0]):
            pat12.append((r[0], r[1], int(r[2].replace(",", "")), int(r[3].replace(",", "")), float(r[4])))
    hit_by_id = {p[0]: p[2] for p in pat12}
    total_hits = sum(hit_by_id.values())
    order = [p[2] for p in pat12]
    f4 = next(p for p in pat12 if p[0] == "F.4")

    # ---- Table 13:45 × 8 模型矩阵(+ Σ 行;首格是坏字符,按模式 ID 的正则排除) ----
    hdr = t13[0]
    models = hdr[1:9]
    mat: dict = {}
    sig_row = None
    for r in t13[1:]:
        m = re.match(r"^([A-FX]\.\d+)\b", r[0])
        if not m:
            sig_row = r
            continue
        mat[m.group(1)] = {mm: int(r[1 + i].replace(",", "")) for i, mm in enumerate(models)}
    colsum = {mm: sum(mat[pid][mm] for pid in mat) for mm in models}

    # ---- Table 3:支柱归属 ----
    pillars = []
    for r in t3[1:]:
        m = re.match(r"^(R\d)\.\s*(.*)$", r[0])
        pillars.append({"id": m.group(1), "name": m.group(2).rstrip("."),
                        "patterns": re.findall(r"[A-FX]\.\d+", r[2])})
    pillar_hits = {pl["id"]: sum(hit_by_id[p] for p in pl["patterns"]) for pl in pillars}

    # ---- Table 6:阶段 × 根因 十字表 ----
    long_names: dict = {}
    t6_ids = set()
    t6_pillar: dict = {}
    col_of = {"R1": 1, "R2": 2, "R3": 3, "R4": 4}
    for r in t6[1:]:
        for pl_id, ci in col_of.items():
            parts = re.split(r"(?=[A-F]\.\d+\s)", " " + r[ci])
            for p in parts:
                m = re.match(r"([A-F]\.\d+)\s+(.*)", p.strip())
                if m:
                    t6_ids.add(m.group(1))
                    t6_pillar[m.group(1)] = pl_id
                    long_names[m.group(1)] = m.group(2)

    # ---- Table 11:模型缩写 ----
    abbr = {}
    total11 = None
    for r in t11[1:]:
        if r[0].lower() == "total":
            total11 = int(r[-1])
        else:
            abbr[r[0]] = r[1]

    # ---- Appendix E 表 14–21(逐模型 top-10) ----
    tops_paper = {}
    for mi, model in zip(range(13, 21), models):
        rows, _ = cells(mi)
        ids = []
        for r in rows[1:]:
            m = re.match(r"^([A-FX]\.\d+)\b", r[0])
            if m:
                ids.append(m.group(1))
        tops_paper[model] = ids
    tops_calc = {}
    for mm in models:
        # 并列名次按模式 ID 字母序(与 Table 13 行序一致;实测全部并列处均如此)
        s = sorted(mat, key=lambda pid: (-mat[pid][mm], pid))
        tops_calc[mm] = s[:10]

    # ---- 语料侧(features_union.jsonl + 磁盘) ----
    fu = [json.loads(l) for l in (LAB / "features_union.jsonl").read_text().splitlines() if l.strip()]
    are_units = [r for r in fu if r["source"] == "are"]
    ours_units = [r for r in fu if r["source"] == "ours"]
    calls_are = sum(r["calls_total"] for r in are_units)
    nts = [r["meta"].get("num_turns") for r in are_units
           if isinstance(r["meta"].get("num_turns"), (int, float))]
    oe_tasks = {json.loads(l)["task_id"] for l in
                (ARE / "open-ended/tasks.jsonl").read_text().splitlines() if l.strip()}
    op_tasks = {json.loads(l)["task_id"] for l in
                (ARE / "optimization/tasks.jsonl").read_text().splitlines() if l.strip()}
    op_rolls = [json.loads(l) for l in (ARE / "optimization/rollouts.jsonl").read_text().splitlines() if l.strip()]
    oe_rolls = [json.loads(l) for l in (ARE / "open-ended/rollouts.jsonl").read_text().splitlines() if l.strip()]
    status_c = Counter(r.get("status") for r in op_rolls)
    regime_c = Counter(r.get("regime_move_verified") for r in oe_rolls)

    # ================= 论文级 =================
    chk("t11.models", "paper", "Table 11:8 个 harness–model 组合 ⇒ 800",
        {"n_models": 8, "total": 800},
        {"n_models": len(abbr), "total": total11},
        note="各模型 n=100 见下条")
    chk("t11.each100", "paper", "Table 11 每个模型 n=100", 8,
        sum(1 for r in t11[1:] if r[0].lower() != "total" and r[2] == "100"))
    chk("calls.avg", "paper", "§2.2.3「73k tool calls at an average of 92.3 steps per episode」——均值",
        92.3, round(calls_are / 800, 1))
    chk("calls.total", "paper", "同上——总数(92.3×800=73,840 的口径;±10 容差)",
        73840, calls_are,
        status="PASS" if abs(calls_are - 73840) <= 10 else "MISMATCH",
        note=f"复算 {calls_are}(与 92.3×800 差 {calls_are - 73840:+d};论文「73k」为约记)")
    chk("t12.sum", "paper", "§5.1「12,712 hits across 800 analyses」;Table 12 ΣHIT",
        12712, total_hits)
    chk("t12.pct", "paper", "Table 12:HIT% = HIT/800 四舍五入到 1 位小数(全 45 行)", 45,
        sum(1 for _, _, h, _, p in pat12 if abs(p - pct1(h, 800)) < 1e-9))
    chk("t12.order", "paper", "Table 12 按 HIT 降序排列", True, all(order[i] >= order[i + 1] for i in range(len(order) - 1)))
    chk("t12.f4", "paper", "「F.4 … appearing in 660 of 800 analyses (82.5%)」",
        [660, 82.5], [f4[2], f4[4]])
    chk("t12.top3", "paper", "「Together these three patterns account for 13.0% of all hits」(F.4+F.2+D.7)",
        13.0, pct1(660 + 502 + 486, total_hits))
    for pl in pillars:
        chk(f"pillar.{pl['id']}.share", "paper", f"{pl['id']} 份额(正文声明见 §5.1)",
            {"R1": 31.0, "R2": 27.6, "R3": 33.5, "R4": 7.9}[pl["id"]],
            pct1(pillar_hits[pl["id"]], total_hits),
            note=f"{pl['name']}:{len(pl['patterns'])} 模式,{pillar_hits[pl['id']]} hits")
    chk("pillar.trio", "paper", "「together account for 92.1% of all hits」(R1+R3+R2)",
        92.1, pct1(pillar_hits["R1"] + pillar_hits["R3"] + pillar_hits["R2"], total_hits))
    chk("pillar.coverage", "paper", "Table 3 的 45 个模式归属:不重不漏,且与 Table 12 同集",
        [45, 45], [len(set(sum((pl["patterns"] for pl in pillars), []))),
                   len(set(sum((pl["patterns"] for pl in pillars), [])) & set(hit_by_id))])
    chk("pillar.counts", "paper", "R1/R2/R3/R4 模式数 = 12/13/13/7",
        [12, 13, 13, 7], [len(pl["patterns"]) for pl in pillars])
    chk("t13.rowsum", "paper", "Table 13:45 行「行和 = 8 列之和 = Table 12 对应 HIT」", 45,
        sum(1 for pid in mat if sum(mat[pid].values()) == hit_by_id[pid]))
    chk("t13.colsum", "paper", "Table 13:列和 = Σ 行", True,
        all(str(colsum[mm]) == sig_row[1 + i].replace(",", "") for i, mm in enumerate(models)),
        note=f"Σ 行 = {[sig_row[1+i] for i in range(8)]}")
    mn = min(colsum, key=colsum.get)
    mx = max(colsum, key=colsum.get)
    chk("t13.range", "paper", "「Total hit counts range from 1,396 (opus-4.8) to 1,818 (qwen3.7-max)」",
        [1396, "opu", 1818, "qwn"], [colsum[mn], mn, colsum[mx], mx])
    chk("t14-21.match", "paper", "Appendix E(Tables 14–21)top-10 与 Table 13 列重算一致", 8,
        sum(1 for mm in models if tops_paper[mm] == tops_calc[mm]))
    chk("top10.all8", "paper", "「E.2, D.4, A.5, and C.1 appear in the top 10 of every model」", True,
        all(p in tops_calc[mm] for mm in models for p in ("E.2", "D.4", "A.5", "C.1")),
        note=";".join(f"{p}:{sum(1 for mm in models if p in tops_calc[mm])}/8"
                      for p in ("E.2", "D.4", "A.5", "C.1")))
    chk("top10.f4", "paper", "「F.4 in seven of the eight」", 7,
        sum(1 for mm in models if "F.4" in tops_calc[mm]),
        note="缺 F.4 的模型:" + ",".join(mm for mm in models if "F.4" not in tops_calc[mm]))
    b1 = {mm: mat["B.1"][mm] for mm in models}
    d6 = {mm: mat["D.6"][mm] for mm in models}
    chk("diverge.b1", "paper", "「B.1 ranges from 13 hits (glm-5.2) to 61 (gpt-5-mini)」",
        [13, "glm", 61, "gpt"],
        [min(b1.values()), min(b1, key=b1.get), max(b1.values()), max(b1, key=b1.get)])
    d6_min_models = sorted(mm for mm in models if d6[mm] == min(d6.values()))
    chk("diverge.d6", "paper", "「D.6 ranges from 3 (opus-4.8 and claude-sonnet-5) to 36 (qwen3.7-max)」",
        [3, ["opu", "son"], 36, "qwn"],
        [min(d6.values()), d6_min_models, max(d6.values()), max(d6, key=d6.get)])
    f5 = next(p for p in pat12 if p[0] == "F.5")
    f6 = next(p for p in pat12 if p[0] == "F.6")
    chk("t12.f5f6", "paper", "「F.5 and F.6 … one and three hits respectively」",
        [1, 3], [f5[2], f6[2]])
    chk("rank.c4", "paper", "「execution faults … (C.4), places only 26th of 45」", 26,
        [p[0] for p in pat12].index("C.4") + 1)
    x_ids = sorted(p for p in hit_by_id if p.startswith("X."))
    chk("stage.37", "paper", "Table 6 = 37 个阶段内模式;其余为 8 个跨阶段 X.n",
        [37, 8], [len(t6_ids), len(x_ids)],
        note="集合一致性:" + ("表6 = A–F 全集" if t6_ids == {p for p in hit_by_id if not p.startswith("X.")} else "不一致!"))
    chk("stage.pillar", "paper", "Table 6 十字表列归属 ≈ Table 3 支柱归属(37 个)", 37,
        sum(1 for pid in t6_ids if t6_pillar[pid] == next(pl["id"] for pl in pillars if pid in pl["patterns"])))

    # ================= 卡片级(README.md) =================
    chk("card.sum", "card", "卡片自数:559 + 247 = 806 ≠ 论文 800;磁盘 560 + 240 = 800", 800, 559 + 247,
        note="卡片两处均偏;论文与磁盘一致(见下两条)")
    chk("card.oe", "card", "卡片「70 tasks × 8 models = 559 rollouts」", 559, len(oe_rolls),
        note="磁盘 560 = 70×8;唯一数 (task,model) 亦 560")
    chk("card.opt.n", "card", "卡片「31 tasks × 8 models = 247 rollouts」", [31, 247], [len(op_tasks), len(op_rolls)],
        note="磁盘 30 任务 × 8 = 240;论文 Table 23 亦 n=30")
    chk("card.opt.success", "card", "卡片「195 success / 52 non-success」", [195, 52],
        [status_c.get("success"), len(op_rolls) - status_c.get("success", 0)],
        note="non-success 52 相符;success 实为 188")

    # ================= 数据级(照实记录) =================
    chk("data.tasks", "data", "任务清单:open-ended 70 / optimization 30(论文 Table 22/23 同)", [70, 30],
        [len(t22) - 1, len(t23) - 1], note=f"tasks.jsonl 唯一 task_id:{len(oe_tasks)}/{len(op_tasks)}")
    chk("data.status", "data", "optimization status 分布(磁盘)", None,
        dict(status_c), status="RECORD")
    chk("data.regime", "data", "open-ended regime_move_verified 分布(磁盘)", None,
        {str(k): v for k, v in regime_c.items()}, status="RECORD")
    chk("data.num_turns", "data", "claude 单元级 num_turns 均值(≠ 92.3;论文「steps」指工具调用数)", None,
        {"n": len(nts), "mean": round(sum(nts) / len(nts), 3)}, status="RECORD")
    chk("data.units", "data", "并集单元:800 are + 62 ours 侧/臂", [800, 62], [len(are_units), len(ours_units)],
        note=f"are calls={calls_are}")

    # ================= 产物 =================
    counts = Counter(c["status"] for c in checks)
    paper_bad = [c for c in checks if c["scope"] == "paper" and c["status"] == "MISMATCH"]
    (LAB / "paper_checks.json").write_text(json.dumps(
        {"arxiv": pt.get("arxiv"), "paper_tables_sha256": pt.get("sha256"),
         "counts": dict(counts), "checks": checks}, ensure_ascii=False, indent=1))

    md = ["# paper_checks — 论文/卡片数字机械复算(零 LLM)  ", ""]
    md.append(f"论文 arXiv {pt.get('arxiv')} · 表格 sha256 {pt.get('sha256')[:12]}… · "
              f"结果:PASS {counts['PASS']} / MISMATCH {counts['MISMATCH']} / RECORD {counts['RECORD']}")
    md.append("")
    md.append("| id | scope | 声明 | expected | actual | status | note |")
    md.append("|---|---|---|---|---|---|---|")
    for c in checks:
        cells_join = lambda v: json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        md.append(f"| {c['id']} | {c['scope']} | {c['claim']} | {cells_join(c['expected'])} | "
                  f"{cells_join(c['actual'])} | {c['status']} | {c['note']} |")
    (LAB / "paper_checks.md").write_text("\n".join(md) + "\n")

    arft = {
        "arxiv": pt.get("arxiv"),
        "paper_tables_sha256": pt.get("sha256"),
        "source": "Table 3(支柱↔模式)/Table 6(阶段×根因)/Table 11(缩写)/Table 12(HIT)/Table 13(×模型),自 paper.html 提取",
        "models": {k: v for k, v in abbr.items()},
        "total_hits": total_hits,
        "pillars": [{"id": pl["id"], "name": pl["name"], "n_patterns": len(pl["patterns"]),
                     "hit_sum": pillar_hits[pl["id"]], "share_pct": pct1(pillar_hits[pl["id"]], total_hits),
                     "patterns": pl["patterns"]} for pl in pillars],
        "patterns": [{"id": pid, "name": name, "name_long": long_names.get(pid), "stage": pid[0],
                      "pillar": next(pl["id"] for pl in pillars if pid in pl["patterns"]),
                      "hit": hit, "partial": partial, "hit_pct": pct,
                      "by_model": mat.get(pid, {})} for pid, name, hit, partial, pct in pat12],
    }
    (LAB / "arft.json").write_text(json.dumps(arft, ensure_ascii=False, indent=1))

    print(f"checks: PASS {counts['PASS']} / MISMATCH {counts['MISMATCH']} / RECORD {counts['RECORD']}")
    for c in checks:
        if c["status"] == "MISMATCH":
            print(f"  MISMATCH [{c['scope']}] {c['id']}: expected={c['expected']} actual={c['actual']} — {c['note']}")
    print(f"wrote paper_checks.json / paper_checks.md / arft.json")
    return 1 if paper_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
