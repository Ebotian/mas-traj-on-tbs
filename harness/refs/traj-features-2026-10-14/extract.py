#!/usr/bin/env python3
"""traj-features-2026-10-14 — 轨迹特征数值实验 v1(deterministic, model-independent).

Inputs (bytes only, zero model calls):
  - dual-agent corpus: /home/ebt/harbor-runs/jobs/agent/<job>/<trial>/artifacts/root/wt/collect
    (*/chats/<uuid>.jsonl = the two side transcripts; */x = exchange dir; state.json; verifier/)
  - single-agent arms:  /home/ebt/harbor-runs/jobs/agent/<job>/<trial>/agent/trajectory.json (ATIF)

Outputs (written to --out, default = this script's directory):
  - features_sides.jsonl  one record per dual-run side (a/b)
  - features_runs.jsonl   one record per dual run
  - features_arms.jsonl   one record per single-agent arm
  - summary.md            human-readable digest + invariants

Definitions live in README.md next to this file. Deterministic: sorted traversal,
no wall-clock in outputs; byte-identical re-runs (see check.py).

Usage: python3 extract.py [--root <jobs/agent dir>] [--out <dir>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
from pathlib import Path

KIND_RULES = [
    ("wait", re.compile(r"\b(wait_peer|wait_pos|wait_file)\b|inotifywait")),
    ("recover", re.compile(r"\brecover\b")),
    ("test", re.compile(r"\bpytest\b|\bcheck_[A-Za-z0-9_]*\.py\b")),
]
NAME_KIND = {
    "read_file": "read",
    "list_directory": "read",
    "write_file": "write",
    "edit": "write",
    "notebook_edit": "write",
    "glob": "search",
    "grep_search": "search",
    "tool_search": "search",
}
KINDS8 = ("read", "write", "search", "exec", "wait", "test", "recover", "other")
FAMILY = {
    "task-restricted": "tumor",
    "task-microarch": "microarch",
    "task-tess": "tess",
    "task-walkthrough": "walkthrough",
}
GATE_TOKENS = ("refs-ok", "refs-block", "wait-start", "block")


def family_of(job: str, trial: str) -> str:
    """Job-name aware: the rehearsal (w*) runs also built on task-restricted."""
    base = trial.split("__")[0]
    if job.startswith("microarch"):
        return "microarch"
    if job.startswith("tumor"):
        return "tumor"
    if job.startswith("tess"):
        return "tess"
    if job.startswith(("w", "walkthrough", "bump")) and base == "task-restricted":
        return "walkthrough"
    return FAMILY.get(base, base)


def classify(name: str, args) -> str:
    if name in NAME_KIND:
        return NAME_KIND[name]
    if name == "run_shell_command":
        cmd = ""
        if isinstance(args, dict):
            cmd = str(args.get("command", ""))
        for kind, rx in KIND_RULES:
            if rx.search(cmd):
                return kind
        return "exec"
    return "other"


def _ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _median(v):
    return statistics.median(v) if v else None


def read_side(path: Path) -> dict:
    recs = 0
    types: dict = {}
    calls = []
    results = []
    um_last = None
    out_sum = 0
    thoughts_sum = 0
    t_first = None
    t_last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            recs += 1
            d = json.loads(line)
            t = d.get("type")
            types[t] = types.get(t, 0) + 1
            ts = _ts(d.get("timestamp") or "")
            if ts is not None:
                t_first = ts if t_first is None else min(t_first, ts)
                t_last = ts if t_last is None else max(t_last, ts)
            um = d.get("usageMetadata")
            if isinstance(um, dict):
                um_last = um
                out_sum += int(um.get("candidatesTokenCount") or 0)
                thoughts_sum += int(um.get("thoughtsTokenCount") or 0)
            msg = d.get("message") or {}
            for p in msg.get("parts") or []:
                if isinstance(p, dict) and isinstance(p.get("functionCall"), dict):
                    fc = p["functionCall"]
                    calls.append((ts, str(fc.get("name") or "?"), fc.get("args") or {}))
            if t == "tool_result":
                tcr = d.get("toolCallResult")
                tcr = tcr if isinstance(tcr, dict) else {}
                rd = tcr.get("resultDisplay")
                rd = rd if isinstance(rd, dict) else {}
                out = rd.get("output")
                if not isinstance(out, str):
                    out = "" if out is None else str(out)
                results.append({"status": tcr.get("status"), "exit": rd.get("exitCode"), "out": out})

    kind_counts: dict = {}
    name_counts: dict = {}
    seq = []
    for (_, nm, args) in calls:
        name_counts[nm] = name_counts.get(nm, 0) + 1
        k = classify(nm, args)
        kind_counts[k] = kind_counts.get(k, 0) + 1
        seq.append(k)

    tss = sorted(ts for (ts, _, _) in calls if ts is not None)
    gaps = [b - a for a, b in zip(tss, tss[1:])]
    med = _median(gaps)
    mad = _median([abs(g - med) for g in gaps]) if gaps else None
    cv = (1.4826 * mad / med) if (med and mad is not None and med > 0) else None
    p600 = (sum(1 for g in gaps if g > 600) / len(gaps)) if gaps else None

    n_exit = sum(1 for r in results if r["exit"] is not None)
    masked = sum(1 for r in results if r["exit"] == 0 and "Traceback" in r["out"])
    err_status = sum(1 for r in results if r["status"] not in (None, "success"))

    # kind_entropy(2026-10-15 按数学实际更名,原名 transition_entropy):类别边际熵——
    # 非首调用(c2..cn)的类别分布香农熵;不以上一类为条件。bit。
    kind_ent = None
    nexts = seq[1:]
    if nexts:
        from math import log2
        tot = len(nexts)
        c: dict = {}
        for k in nexts:
            c[k] = c.get(k, 0) + 1
        kind_ent = round(-sum((v / tot) * log2(v / tot) for v in c.values()), 6)

    # transition_entropy(文档《…计算历史学建模》§4.2 条件转移熵):
    # N_ab 计数 + Dirichlet(α=1)平滑;π̂=转移位点经验边际;类集=KINDS8;量纲 nat。
    trans = None
    if len(seq) >= 2:
        from math import log as _ln
        pairs = list(zip(seq, seq[1:]))
        froms: dict = {}
        nab: dict = {}
        for a, b in pairs:
            nab[(a, b)] = nab.get((a, b), 0) + 1
            froms[a] = froms.get(a, 0) + 1
        alpha = 1.0
        tot_tr = len(pairs)
        hc = 0.0
        for a, na in froms.items():
            denom = na + len(KINDS8) * alpha
            inner = 0.0
            for b in KINDS8:
                p = (nab.get((a, b), 0) + alpha) / denom
                inner -= p * _ln(p)
            hc += (na / tot_tr) * inner
        trans = round(hc, 6)

    prompt = int(um_last.get("promptTokenCount") or 0) if um_last else None
    cached = int(um_last.get("cachedContentTokenCount") or 0) if um_last else None
    return {
        "records": recs,
        "types": dict(sorted(types.items(), key=lambda kv: str(kv[0]))),
        "calls_total": len(calls),
        "calls_by_name": dict(sorted(name_counts.items())),
        "kinds": dict(sorted(kind_counts.items())),
        "gaps_n": len(gaps),
        "gaps_median_s": round(med, 3) if med is not None else None,
        "gaps_cv_robust": round(cv, 6) if cv is not None else None,
        "gaps_p600_frac": round(p600, 6) if p600 is not None else None,
        "results_total": len(results),
        "results_with_exit": n_exit,
        "masked": masked,
        "masked_rate": round(masked / n_exit, 6) if n_exit else None,
        "status_error": err_status,
        "prompt_final": prompt,
        "cached_final": cached,
        "cache_ratio": round(cached / prompt, 6) if (prompt and cached is not None) else None,
        "kind_entropy": kind_ent,
        "transition_entropy": trans,
        "out_tokens_sum": out_sum,
        "thoughts_tokens_sum": thoughts_sum,
        "span_s": round(t_last - t_first, 3) if (t_first is not None and t_last is not None) else None,
    }


def read_json_tol(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def run_record(root: Path, job: str, trial_dir: Path) -> dict:
    collect = trial_dir / "artifacts/root/wt/collect"
    x = collect / "x"
    trial = trial_dir.name
    family = family_of(job, trial)
    rec: dict = {"job": job, "trial": trial, "family": family, "sides": {}}

    chats = collect / "chats"
    uuids = {}
    for side in ("a", "b"):
        p = x / f"session-{side}.uuid"
        if p.exists():
            uuids[side] = p.read_text().strip()
    if chats.is_dir():
        for side, uu in sorted(uuids.items()):
            f = chats / f"{uu}.jsonl"
            if f.exists():
                rec["sides"][side] = read_side(f)
        if not uuids:
            for f in sorted(chats.glob("*.jsonl")):
                rec["sides"][f.stem[:8]] = read_side(f)
    if not rec["sides"]:
        rec["note"] = "no-transcripts"

    state = read_json_tol(collect / "state.json")
    if isinstance(state, dict):
        rec["normal"] = state.get("normal")
        rec["rc"] = [state.get("rc_a"), state.get("rc_b")]
        rec["consensus_on_main"] = state.get("consensus_on_main")
        rec["rounds"] = state.get("rounds")
        rec["structure_state"] = state.get("structure_state")
        rec["recovered_run"] = state.get("recovered_run")
        rec["deliverables"] = state.get("deliverables")
    rcs = x / "rcs"
    if rcs.exists():
        rec["rcs"] = rcs.read_text().strip()

    for side in ("a", "b"):
        rf = x / f"ready-{side}.round"
        if rf.exists():
            try:
                rec.setdefault("rounds_file", {})[side] = int(rf.read_text().strip())
            except Exception:
                pass
    rec["pos_rounds"] = {
        side: sorted(
            int(m.group(1))
            for f in x.glob(f"pos-{side}-r*")
            if (m := re.search(r"r(\d+)$", f.name))
        )
        for side in ("a", "b")
    }
    rec["stop"] = {s: (x / f"stop-{s}").exists() for s in ("a", "b")}
    rec["abort"] = {s: (x / f"abort-{s}").exists() for s in ("a", "b")}

    div = read_json_tol(x / "divergence.json")
    if isinstance(div, dict):
        rec["divergence_keys"] = sorted(div.keys())[:20]
        for k in ("differing_count", "count", "differing"):
            if k in div:
                rec["divergence_count"] = div[k]
                break

    gl = x / "gate.log"
    if gl.exists():
        lines = gl.read_text(errors="replace").splitlines()
        rec["gate_lines"] = len(lines)
        rec["gate_tokens"] = {tok: sum(1 for ln in lines if tok in ln) for tok in GATE_TOKENS}

    stats_dir = x / "stats"
    if stats_dir.is_dir():
        ck = sorted(stats_dir.glob("ckpt-*.json"))
        rec["stats_ckpt_files"] = len(ck)
        schemas = set()
        for f in ck:
            d = read_json_tol(f)
            if isinstance(d, dict):
                meta = d.get("meta") or {}
                if isinstance(meta, dict) and meta.get("schema"):
                    schemas.add(meta["schema"])
        if schemas:
            rec["stats_schemas"] = sorted(schemas)

    ver = trial_dir / "verifier"
    if ver.is_dir():
        files = {}
        for name in ("metrics.json", "test-stdout.txt", "reward.txt", "ctrf.json"):
            f = ver / name
            if f.exists():
                files[name] = f.stat().st_size
        rec["verifier_files"] = files
        mj = read_json_tol(ver / "metrics.json")
        if mj is not None:
            rec["verifier_metrics"] = mj

    tot_calls = sum(s["calls_total"] for s in rec["sides"].values())
    tot_mask = sum(s["masked"] for s in rec["sides"].values())
    rec["calls_total"] = tot_calls
    rec["masked_total"] = tot_mask
    return rec


def arm_records(root: Path) -> list:
    out = []
    for f in sorted(root.glob("*/*/agent/trajectory.json")):
        job = f.parts[-4]
        trial = f.parts[-3]
        d = read_json_tol(f) or {}
        calls = 0
        results = 0
        masked = 0
        for st in d.get("steps", []):
            calls += len(st.get("tool_calls") or [])
            for r in (st.get("observation") or {}).get("results") or []:
                results += 1
                c = r.get("content") if isinstance(r, dict) else None
                c = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                if "Exit Code: 0" in c and "Traceback" in c:
                    masked += 1
        out.append({
            "job": job,
            "trial": trial,
            "schema_version": d.get("schema_version"),
            "steps": len(d.get("steps", [])),
            "calls_total": calls,
            "results_total": results,
            "masked": masked,
            "final_metrics": d.get("final_metrics"),
        })
    return out


def write_jsonl(path: Path, records: list) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def build_summary(runs: list, sides: dict, arms: list) -> str:
    lines = []
    lines.append("# traj-features-2026-10-14 — 轨迹特征数值实验 v1(摘要)")
    lines.append("")
    lines.append("确定性、零模型调用:所有数值均为所收集工件的纯函数(定义见 README.md)。")
    lines.append("")
    lines.append("## 语料")
    fam_runs: dict = {}
    for r in runs:
        fam_runs.setdefault(r["family"], []).append(r)
    lines.append("| family | runs | sides | calls | masked | normal |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for fam in sorted(fam_runs):
        rs = fam_runs[fam]
        sides_n = sum(len(r["sides"]) for r in rs)
        calls = sum(r.get("calls_total") or 0 for r in rs)
        mask = sum(r.get("masked_total") or 0 for r in rs)
        normal = sum(1 for r in rs if r.get("normal"))
        lines.append(f"| {fam} | {len(rs)} | {sides_n} | {calls} | {mask} | {normal}/{len(rs)} |")
    lines.append("")
    lines.append("## arms(单 agent ATIF)")
    ac = sum(a["calls_total"] for a in arms)
    am = sum(a["masked"] for a in arms)
    lines.append(f"- arms={len(arms)} calls={ac} masked={am}")
    for a in arms:
        lines.append(f"  - {a['job']}: {a['schema_version']} calls={a['calls_total']} masked={a['masked']}")
    lines.append("")
    lines.append("## 不变式(独立复算)")
    lines.append(f"- arms calls_total == 728 → {ac} ({'OK' if ac == 728 else 'FAIL'})")
    lines.append(f"- arms masked == 26 → {am} ({'OK' if am == 26 else 'FAIL'})")
    t1 = next((r for r in runs if r["job"] == "tumor-1"), None)
    if t1 is not None:
        tc = t1.get("calls_total")
        lines.append(f"- tumor-1 calls_total == 430(机制归因复核口径)→ {tc} ({'OK' if tc == 430 else 'CHECK'})")
    lines.append("")
    lines.append("## 双跑特征表(每跑)")
    lines.append("| job | family | calls | masked | span_s(a/b) | cache_ratio(a/b) | rounds(a/b) | normal |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in runs:
        a = r["sides"].get("a") or {}
        b = r["sides"].get("b") or {}
        sp = f"{a.get('span_s')}/{b.get('span_s')}"
        cr = f"{a.get('cache_ratio')}/{b.get('cache_ratio')}"
        rd = r.get("rounds") or {}
        lines.append(
            f"| {r['job']} | {r['family']} | {r.get('calls_total')} | {r.get('masked_total')} | "
            f"{sp} | {cr} | {rd.get('a')}/{rd.get('b')} | {r.get('normal')} |"
        )
    lines.append("")
    lines.append("## 备注")
    lines.append("- 定义与口径:见 README.md;masked = 工具结果 exitCode==0 且 output 含 Traceback(启发式下界)。")
    lines.append("- 转录记录 schema:Qwen chat JSONL(assistant functionCall / tool_result.toolCallResult.resultDisplay)。")
    lines.append("- 本表不含语义推断类特征(S 类),只收机械可算量;语义特征需单独的证据根映射。")
    lines.append("- 熵:kind_entropy=类别边际熵(非首调用,−Σp·log₂p,bit);transition_entropy=条件转移熵(§4.2,α=1,π̂=经验边际,nat)。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/ebt/harbor-runs/jobs/agent")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    side_records = []
    for job_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for trial_dir in sorted(job_dir.glob("task-*")):
            collect = trial_dir / "artifacts/root/wt/collect"
            if not (collect / "x").is_dir():
                continue
            rec = run_record(root, job_dir.name, trial_dir)
            runs.append(rec)
            for side, srec in sorted(rec["sides"].items()):
                side_records.append({"job": job_dir.name, "trial": rec["trial"], "family": rec["family"], "side": side, **srec})

    arms = arm_records(root)
    write_jsonl(out / "features_sides.jsonl", side_records)
    write_jsonl(out / "features_runs.jsonl", runs)
    write_jsonl(out / "features_arms.jsonl", arms)

    summary = build_summary(runs, {}, arms)
    (out / "summary.md").write_text(summary, encoding="utf-8")

    print(f"runs={len(runs)} sides={len(side_records)} arms={len(arms)}")
    print(f"arms calls={sum(a['calls_total'] for a in arms)} masked={sum(a['masked'] for a in arms)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
