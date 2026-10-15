#!/usr/bin/env python3
"""dl_test.py — 样本外对数损失与池化 AIS 增量(2026-10-15 追加;确定性、零模型调用)。

三件(口径脚注见 dl_test.md 与 README「校准与探针」节):
1. 逐单元前缀/后缀 ΔL_a:转移序对半(前半训练 / 后半测试);两模型同用 Laplace α=1
   (p₀=训练目标边际;p̂₁=训练逐源行条件分布)。ΔL_a = L₀−L₁(nat/转移;>0=一阶历史
   在样本外仍省编码)。m≥20 才计。
2. 留一任务 ΔL_b:预测器只用【其他任务】(同题全模型/全侧剔除,防同题泄漏)的池化计数
   (边际 + 逐源行,α=1),在本单元全部转移上测试——跨任务可迁移性。m≥8 才计。
3. 池化 ΔA₂ = I(C_{t−1};C_{t+1} | C_t)(二阶主动信息存储的增量,Lizier 2014 口径;
   链式分解 A₂ = A₁ + ΔA₂,A₂ 即两步历史 AIS)与 A₁ = I(C_t;C_{t+1})(nat;两处条件
   分布均 α=1);显著性 = 逐单元保频置换 200 次(固定种子 20261015),单侧 p。
自检:每单元无平滑训练恒等式 L₀_train−L₁_train = Î(全序列),记录最大差(应为 0)。

产物:dl_test.json + dl_test.md(仓库内;check.py 逐字节复现)。
用法:python3 dl_test.py [--are-root DIR] [--ours-root DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract_cross as E  # noqa: E402

KINDS = list(E.KINDS8)
ln = math.log
K = len(KINDS)


def collect(are_root: Path, ours_root: Path) -> list:
    """(unit, source, corpus, g, task_key, seq);顺序与 features_union 单元命名一致。"""
    units = []
    # 源 A 侧(与 extract_cross.main 同发现逻辑)
    for job_dir in sorted(p for p in ours_root.iterdir() if p.is_dir()):
        for trial_dir in sorted(job_dir.glob("task-*")):
            cd = trial_dir / "artifacts/root/wt/collect"
            if not (cd / "x").is_dir():
                continue
            job, trial = job_dir.name, trial_dir.name
            fam = E.family_of(job, trial)
            chats = cd / "chats"
            uuids = {}
            for side in ("a", "b"):
                p = cd / "x" / f"session-{side}.uuid"
                if p.exists():
                    uuids[side] = p.read_text().strip()
            sides = {}
            if chats.is_dir():
                if uuids:
                    for side, uu in sorted(uuids.items()):
                        f = chats / f"{uu}.jsonl"
                        if f.exists():
                            sides[side] = f
                else:
                    for f in sorted(chats.glob("*.jsonl")):
                        sides[f.stem[:8]] = f
            for side, f in sorted(sides.items()):
                a = E.adapt_ours_side(f)
                seq = [c.get("kind") or "other" for c in a["calls"]]
                units.append((f"ours/{job}/{trial}/{side}", "ours", fam, fam, (job, trial), seq))
    for f in sorted(ours_root.glob("*/*/agent/trajectory.json")):
        job, trial = f.parts[-4], f.parts[-3]
        a = E.adapt_ours_arm(f)
        seq = [c.get("kind") or "other" for c in a["calls"]]
        units.append((f"ours/{job}/{trial}/arm", "ours", "arm", "arm", (job, trial), seq))
    # 源 B(are)
    for subset in ("open-ended", "optimization"):
        tdir = are_root / subset / "trajectories"
        if not tdir.is_dir():
            continue
        for mdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            model = E.MODEL_ALIAS.get(mdir.name, mdir.name)
            for f in sorted(mdir.glob("*.jsonl")):
                rec = E._scan_are(f)
                seq = [c.get("kind") or "other" for c in rec["calls"]]
                units.append((f"are/{subset}/{model}/{f.stem}", "are", subset, model,
                              (subset, f.stem), seq))
    units.sort(key=lambda x: x[0])
    return units


def dl_prefix(seq, min_m=20):
    pairs = list(zip(seq, seq[1:]))
    m = len(pairs)
    if m < min_m:
        return None
    h = m // 2
    tr, te = pairs[:h], pairs[h:]
    tgt = Counter(b for _, b in tr)
    rowN = Counter(a for a, _ in tr)
    rowB = Counter(tr)
    nh = len(tr)
    l0 = sum(-ln((tgt[b] + 1) / (nh + K)) for _, b in te) / len(te)
    l1 = sum(-ln((rowB[(a, b)] + 1) / (rowN[a] + K)) for a, b in te) / len(te)
    return round(l0 - l1, 6)


def build_globals(units):
    """全局 + 逐任务聚合(留一任务用)。"""
    G = {"tgt": Counter(), "rowN": Counter(), "rowB": Counter()}          # 全局
    T: dict = {}                                                          # task_key -> 同 G
    for _u, _s, _c, _g, tk, seq in units:
        t = T.setdefault(tk, {"tgt": Counter(), "rowN": Counter(), "rowB": Counter()})
        for a, b in zip(seq, seq[1:]):
            G["tgt"][b] += 1
            G["rowN"][a] += 1
            G["rowB"][(a, b)] += 1
            t["tgt"][b] += 1
            t["rowN"][a] += 1
            t["rowB"][(a, b)] += 1
    return G, T


def dl_leave_task(seq, tk, G, T, min_m=8):
    pairs = list(zip(seq, seq[1:]))
    m = len(pairs)
    if m < min_m:
        return None
    t = T[tk]
    tot_o = sum(G["tgt"].values()) - sum(t["tgt"].values())
    l0 = 0.0
    l1 = 0.0
    for a, b in pairs:
        l0 += -ln((G["tgt"][b] - t["tgt"][b] + 1) / (tot_o + K))
        denom = G["rowN"][a] - t["rowN"][a] + K
        l1 += -ln((G["rowB"][(a, b)] - t["rowB"][(a, b)] + 1) / denom)
    return round((l0 - l1) / m, 6)


def pooled_delta_a2(units):
    N3: Counter = Counter()
    N2: Counter = Counter()
    N1: Counter = Counter()
    for _u, _s, _c, _g, _tk, seq in units:
        for x, y, z in zip(seq, seq[1:], seq[2:]):
            N3[(x, y, z)] += 1
            N2[(y, z)] += 1
            N1[y] += 1
    T2 = sum(N2.values())
    T3v = sum(N3.values())
    Nz = Counter()
    for (y, z), c in N2.items():
        Nz[z] += c
    a1 = 0.0
    for (y, z), c in N2.items():
        a1 += (c / T2) * ln(((c + 1) / (N1[y] + K)) / ((Nz[z] + 1) / (T2 + K)))
    Nxy = Counter()
    for (x, y, z) in N3:
        Nxy[(x, y)] += N3[(x, y, z)]
    delta = 0.0  # ΔA₂ = I(C_{t−1};C_{t+1} | C_t)(链式分解:A₂ = A₁ + ΔA₂)
    for (x, y, z), c in N3.items():
        cond = (c + 1) / (Nxy[(x, y)] + K)
        marg = (N2[(y, z)] + 1) / (N1[y] + K)
        delta += (c / T3v) * ln(cond / marg)
    return round(a1, 6), round(a1 + delta, 6), round(delta, 6)


def i_direct(seq):
    pairs = list(zip(seq, seq[1:]))
    m = len(pairs)
    nx = Counter(a for a, _ in pairs)
    ny = Counter(b for _, b in pairs)
    nxy = Counter(pairs)
    return sum((c / m) * ln((c / m) / ((nx[a] / m) * (ny[b] / m))) for (a, b), c in nxy.items())


def identity_check(seq):
    pairs = list(zip(seq, seq[1:]))
    m = len(pairs)
    if m < 2:
        return None, None
    tgt = Counter(b for _, b in pairs)
    rowN = Counter(a for a, _ in pairs)
    rowB = Counter(pairs)
    l0 = -sum(ln(tgt[b] / m) for _, b in pairs) / m
    l1 = -sum(ln(rowB[(a, b)] / rowN[a]) for a, b in pairs) / m
    return l0 - l1, i_direct(seq)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--are-root", default="/home/ebt/harbor-runs/data/autoresearch-eval")
    ap.add_argument("--ours-root", default="/home/ebt/harbor-runs/jobs/agent")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    out = Path(args.out)

    units = collect(Path(args.are_root), Path(args.ours_root))
    G, T = build_globals(units)
    id_max = 0.0
    rows = []
    for u, s, corpus, g, tk, seq in units:
        m = len(seq) - 1
        da = dl_prefix(seq)
        db = dl_leave_task(seq, tk, G, T)
        ldiff, idirect = identity_check(seq)
        if ldiff is not None:
            id_max = max(id_max, abs(ldiff - idirect))
        rows.append({"u": u, "s": s, "corpus": corpus, "g": g, "m": m,
                     "dl_a": da, "dl_b": db})

    a1, a2, dA2 = pooled_delta_a2(units)
    rng = random.Random(20261015)
    k_perm = 200
    ge = 0
    for _ in range(k_perm):
        shuf = [(u, s, c, g, tk, random.Random(rng.getrandbits(32)).sample(seq, len(seq)))
                for u, s, c, g, tk, seq in units]
        _, _, d2 = pooled_delta_a2(shuf)
        if d2 >= dA2 - 1e-12:
            ge += 1
    p_perm = round((1 + ge) / (1 + k_perm), 6)

    def med(xs):
        xs = sorted(x for x in xs if x is not None)
        return round(xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2, 6) if xs else None

    groups: dict = {}
    for r in rows:
        groups.setdefault(r["corpus"], []).append(r)
    by_corpus = {}
    for cname, rs in sorted(groups.items()):
        das = [r["dl_a"] for r in rs if r["dl_a"] is not None]
        dbs = [r["dl_b"] for r in rs if r["dl_b"] is not None]
        by_corpus[cname] = {"n_a": len(das), "med_a": med(das), "pos_a": sum(1 for v in das if v > 0),
                            "n_b": len(dbs), "med_b": med(dbs), "pos_b": sum(1 for v in dbs if v > 0)}
    das_all = [r["dl_a"] for r in rows if r["dl_a"] is not None]
    dbs_all = [r["dl_b"] for r in rows if r["dl_b"] is not None]
    summary = {"n_units": len(rows), "n_a": len(das_all), "med_a": med(das_all),
               "pos_a": sum(1 for v in das_all if v > 0),
               "n_b": len(dbs_all), "med_b": med(dbs_all),
               "pos_b": sum(1 for v in dbs_all if v > 0), "by_corpus": by_corpus}
    payload = {
        "meta": {"script": "dl_test.py",
                 "note": "前缀/后缀 ΔL_a(m≥20)、留一任务 ΔL_b(m≥8;α=1 两模型)、"
                         "池化 A1/A2/ΔA2 与保频置换 p(k=200,种子 20261015);逐字节可复现"},
        "per_unit": rows, "summary": summary,
        "pooled": {"a1": a1, "a2": a2, "delta_a2": dA2, "perm_p": p_perm, "k_perm": k_perm},
        "identity_max_diff": round(id_max, 12),
    }
    (out / "dl_test.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                      encoding="utf-8")
    lines = ["# dl_test — 样本外对数损失与池化 AIS(2026-10-15;确定性、零模型调用)", ""]
    lines.append(f"- 逐单元前缀/后缀 ΔL_a(m≥{20}):n={summary['n_a']},中位 {summary['med_a']} nat,"
                 f">0 = {summary['pos_a']}/{summary['n_a']}")
    lines.append(f"- 留一任务 ΔL_b(m≥{8}):n={summary['n_b']},中位 {summary['med_b']} nat,"
                 f">0 = {summary['pos_b']}/{summary['n_b']}")
    lines.append(f"- 池化:A1={a1} · A2={a2} · ΔA2={dA2} nat;保频置换 p={p_perm}(k={k_perm})")
    lines.append(f"- 恒等式自检 max|L₀_train−L₁_train−Î| = {payload['identity_max_diff']}")
    lines.append("")
    lines.append("| corpus | n_a | ΔL_a 中位 | >0 | n_b | ΔL_b 中位 | >0 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for cname, r in by_corpus.items():
        lines.append(f"| {cname} | {r['n_a']} | {r['med_a']} | {r['pos_a']} | "
                     f"{r['n_b']} | {r['med_b']} | {r['pos_b']} |")
    (out / "dl_test.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"units={len(rows)} dl_a n={summary['n_a']} med={summary['med_a']} | "
          f"dl_b n={summary['n_b']} med={summary['med_b']}")
    print(f"A1={a1} A2={a2} dA2={dA2} perm_p={p_perm} | identity_max_diff={payload['identity_max_diff']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
