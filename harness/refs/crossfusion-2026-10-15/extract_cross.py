#!/usr/bin/env python3
"""crossfusion-2026-10-15 — 两源并集轨迹机械统计(数据并集 × 方法并集)。

源 A(ours):双跑 54 侧 + 8 臂(与 traj-features-2026-10-14 同口径;check.py 对照逐字段相等)
源 B(are):AutoResearchEval 800 条(下载钉版 412fb490…;5 种日志格式,见 README)

核心口径(两源共用,单一实现):
  - 8 类工具 taxonomy:read/write/search/exec/wait/test/recover/other;
    名称→类映射表分源(README);shell 类(Bash/run_shell_command/exec/command_execution)
    按命令文本细分 wait/test/recover,默认 exec。
  - kind_entropy:非首调用(c2..cn)类别边际熵(bit);transition_entropy:条件转移熵(α=1,K=8,nat)。
  - gaps:相邻"调用事件"时间戳间隔;事件戳取调用行戳,缺则退化为其配对结果行戳(basis 记录)。
  - masked(静默失败):工具报成功而输出含 "Traceback";各格式成功判据见 README。
  - cache_ratio / tokens:各源可得字段见 README(缺则 null)。
确定性、零模型调用;输出逐字节可复现(check.py)。

输出(--out 默认本目录):
  - features_union.jsonl  每单元一条(ours 62 + are 800;按 unit 排序)
  - audit.json             工具名词表未映射审计 + 语料计数
  - summary.md             语料表、覆盖矩阵、不变式摘要

用法:python3 extract_cross.py [--are-root …] [--ours-root …] [--traj-lab …] [--out …]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import re
import statistics
from pathlib import Path

# ---------------------------------------------------------------------------
# 共用分类与统计(与 traj-features-2026-10-14 定义一致)
# ---------------------------------------------------------------------------
KIND_RULES = [
    ("wait", re.compile(r"\b(wait_peer|wait_pos|wait_file)\b|inotifywait")),
    ("recover", re.compile(r"\brecover\b")),
    ("test", re.compile(r"\bpytest\b|\bcheck_[A-Za-z0-9_]*\.py\b")),
]
KINDS8 = ("read", "write", "search", "exec", "wait", "test", "recover", "other")

# 源 A(ours)侧:qwen-code 工具名 → 类(逐名对齐 traj-features-2026-10-14 extract.py 的 NAME_KIND)
OURS_SIDE_NAME_KIND = {
    "read_file": "read",
    "list_directory": "read",
    "write_file": "write",
    "edit": "write",
    "notebook_edit": "write",
    "glob": "search",
    "grep_search": "search",
    "tool_search": "search",
    "run_shell_command": "SHELL",
}
# 源 A(ours)臂:ATIF 转录里出现、侧上未见的名(臂无 lab 对照,按最贴近类归口;
# 侧上的同类表外名如 edit_file/shell_command 则按 lab 惯例归 other,计数见 audit.ours_side_nonstandard)
OURS_ARM_NAME_KIND = {
    **OURS_SIDE_NAME_KIND,
    "edit_file": "write",
    "run_shell": "SHELL",
    "shell_command_placeholder": "SHELL",
    "web_search": "search",
    "web_fetch": "search",
    "agent": "other",
    "tool_call": "other",
    "get_goal": "other",
}
# 源 B(claude-code 会话流)工具名 → 类
CLAUDE_NAME_KIND = {
    "Read": "read",
    "Write": "write",
    "Edit": "write",
    "NotebookEdit": "write",
    "MultiEdit": "write",
    "Glob": "search",
    "Grep": "search",
    "WebSearch": "search",
    "WebFetch": "search",
    "Bash": "SHELL",
    "TaskOutput": "read",
    "Task": "other",
    "TaskCreate": "other",
    "TaskUpdate": "other",
    "TaskList": "other",
    "TaskStop": "other",
    "Monitor": "other",
    "ScheduleWakeup": "other",
    "Agent": "other",
    "SendMessage": "other",
    "CronCreate": "other",
    "CronDelete": "other",
    "CronList": "other",
    "PushNotification": "other",
    "ToolSearch": "search",
}
# 源 B(gemini CLI)工具名 → 类
GEMINI_NAME_KIND = {
    "read_file": "read",
    "list_directory": "read",
    "read_background_output": "read",
    "write_file": "write",
    "replace": "write",
    "glob": "search",
    "grep_search": "search",
    "google_web_search": "search",
    "web_fetch": "search",
    "run_shell_command": "SHELL",
    "update_topic": "other",
    "enter_plan_mode": "other",
    "exit_plan_mode": "other",
    "list_background_processes": "other",
    "invoke_agent": "other",
}
# 源 B(codex)工具名 → 类
CODEX_NAME_KIND = {
    "command_execution": "SHELL",
    "exec": "SHELL",
    "file_change": "write",
}

# 钉版实测的 2 处 __unparsedToolInput 工件(claude 流,均在 qwen3.7-max 开题集):
#   W7128691155:name="nvidia-smi 2";W4396723768:name 缺(适配层以 "?" 占位)。
# 输入未解析 ⇒ 无从按 args 细分,一律归 other;实例记于 audit.defect_occurrences。
DEFECT_NAME_KIND = {"?": "other", "nvidia-smi 2": "other"}
DEFECT_OCCURRENCES: list = []
# are 优化集里两个目录名与论文/卡片的规范模型名不同(同一条 rollout 行亦用目录名):
#   optimization/sonnet-5       → claude-sonnet-5
#   optimization/codex-gpt5mini → gpt-5-mini
# 单元名(unit)保留磁盘路径原样;model 字段归并到规范名,原目录名入 meta.model_dir。
MODEL_ALIAS = {"sonnet-5": "claude-sonnet-5", "codex-gpt5mini": "gpt-5-mini"}
# ours 侧出现、但不在 lab 表里的名(lab 一律归 other;为守「与 lab 逐字段一致」不特判)
OURS_SIDE_NONSTD: collections.Counter = collections.Counter()

UNMAPPED: collections.Counter = collections.Counter()


def classify(name: str, args, table: dict, log_unmapped: bool = True) -> str:
    k = table.get(name)
    if k is None:
        k = DEFECT_NAME_KIND.get(name)
    if k is None:
        if log_unmapped:
            UNMAPPED[name] += 1
        return "other"
    if k == "SHELL":
        cmd = ""
        if isinstance(args, dict):
            cmd = str(args.get("command", ""))
        for kind, rx in KIND_RULES:
            if rx.search(cmd):
                return kind
        return "exec"
    return k


def _ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _median(v):
    return statistics.median(v) if v else None


def _h0_seq(s: list) -> float:
    """无平滑经验条件熵 H⁽⁰⁾(C_{t+1}|C_t)(nat;P⁽⁰⁾_ab=N_ab/N_a,不设先验)。
    与论文式 (2) 的 α=1 版同源;二者之差即平滑敏感度 S_smooth。
    目标端按【实际观察到】的类别求和(不写死 KINDS8——表外类别也须完整计入)。"""
    from math import log as _ln
    fr: dict = {}
    nb: dict = {}
    for a, b in zip(s, s[1:]):
        fr[a] = fr.get(a, 0) + 1
        d = nb.setdefault(a, {})
        d[b] = d.get(b, 0) + 1
    t = len(s) - 1
    if t <= 0:
        return 0.0
    acc = 0.0
    for a, na in fr.items():
        inner = 0.0
        for m in nb[a].values():
            p = m / na
            inner -= p * _ln(p)
        acc += (na / t) * inner
    return acc


def ring_core(calls: list, results: list) -> dict:
    """统一机械统计核心。calls::=[{ts,name,args,…}];results::=[{ok,text,…}]。"""
    kind_counts: dict = {}
    name_counts: dict = {}
    seq = []
    for c in calls:
        name_counts[c["name"]] = name_counts.get(c["name"], 0) + 1
        k = c.get("kind") or "other"
        kind_counts[k] = kind_counts.get(k, 0) + 1
        seq.append(k)

    tss = sorted(t for t in (c.get("ts") for c in calls) if t is not None)
    gaps = [b - a for a, b in zip(tss, tss[1:])]
    med = _median(gaps)
    mad = _median([abs(g - med) for g in gaps]) if gaps else None
    cv = (1.4826 * mad / med) if (med and mad is not None and med > 0) else None
    p600 = (sum(1 for g in gaps if g > 600) / len(gaps)) if gaps else None

    n_judged = sum(1 for r in results if r.get("ok") is not None)
    masked = sum(1 for r in results if r.get("ok") is True and "Traceback" in (r.get("text") or ""))

    kind_ent = None
    nexts = seq[1:]
    if nexts:
        from math import log2
        tot = len(nexts)
        c: dict = {}
        for k in nexts:
            c[k] = c.get(k, 0) + 1
        kind_ent = round(-sum((v / tot) * log2(v / tot) for v in c.values()), 6)

    trans = None
    trans_ns = mi_action = p_action = s_smooth = mi_perm_p = None
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

        # ---- 解耦指标(2026-10-15,据外部建议核对后落地;确定性)----
        # H⁽⁰⁾:无平滑条件熵;I_action = H_kind·ln2 − H⁽⁰⁾ = Î(C_t;C_{t+1})(nat);
        # P_action = I/(H_kind·ln2)(H_kind=0 ⇒ 未定义 None);
        # S_smooth = 平滑熵 − H⁽⁰⁾;mi_perm_p = 保频置换检验单侧 p
        #   (k=200,crc32(seq) 定种 ⇒ 逐字节可复现;p=(1+#{H⁽⁰⁾(perm)≤h0} )/(1+k))。
        h0 = _h0_seq(seq)
        hy = kind_ent * _ln(2) if kind_ent is not None else 0.0
        mi_obs = hy - h0
        if -1e-9 < mi_obs < 0.0:
            mi_obs = 0.0
        if mi_obs == 0.0:
            mi_obs = 0.0  # -0.0 归一为 0.0(kind_ent 本身可能为 -0.0)
        ss = hc - h0
        if -1e-9 < ss < 0.0:
            ss = 0.0
        trans_ns = round(h0, 6)
        mi_action = round(mi_obs, 6)
        p_action = None if hy <= 0 else round(max(0.0, min(1.0, mi_obs / hy)), 6)
        s_smooth = round(ss, 6)
        import random as _random
        import zlib as _zlib
        rng = _random.Random(_zlib.crc32(("|".join(seq)).encode("utf-8")))
        k_perm = 200
        ge = 0
        sh = list(seq)
        h0_target = hy - mi_obs  # = h0(数值保护后)
        for _ in range(k_perm):
            rng.shuffle(sh)
            if _h0_seq(sh) <= h0_target + 1e-12:
                ge += 1
        mi_perm_p = round((1 + ge) / (1 + k_perm), 6)

    return {
        "calls_total": len(calls),
        "calls_by_name": dict(sorted(name_counts.items())),
        "kinds": dict(sorted(kind_counts.items())),
        "gaps_n": len(gaps),
        "gaps_median_s": round(med, 3) if med is not None else None,
        "gaps_cv_robust": round(cv, 6) if cv is not None else None,
        "gaps_p600_frac": round(p600, 6) if p600 is not None else None,
        "results_judged": n_judged,
        "masked": masked,
        "masked_rate": round(masked / n_judged, 6) if n_judged else None,
        "kind_entropy": kind_ent,
        "transition_entropy": trans,
        "trans_entropy_ns": trans_ns,
        "mi_action": mi_action,
        "p_action": p_action,
        "s_smooth": s_smooth,
        "mi_perm_p": mi_perm_p,
    }


def flatten_content(v) -> str:
    """claude tool_result content:str 或 [{type:'text',text:…},…]。"""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        parts = []
        for b in v:
            if isinstance(b, dict):
                t = b.get("text")
                parts.append(t if isinstance(t, str) else json.dumps(b, ensure_ascii=False))
            else:
                parts.append(str(b))
        return "\n".join(parts)
    if v is None:
        return ""
    return json.dumps(v, ensure_ascii=False)


def first_last(ts_iter):
    xs = [t for t in ts_iter if t is not None]
    if not xs:
        return None, None
    return min(xs), max(xs)


# ---------------------------------------------------------------------------
# 源 A(ours):双跑侧转录 + ATIF 臂(口径复制自 traj-features-2026-10-14)
# ---------------------------------------------------------------------------
def family_of(job: str, trial: str) -> str:
    base = trial.split("__")[0]
    if job.startswith("microarch"):
        return "microarch"
    if job.startswith("tumor"):
        return "tumor"
    if job.startswith("tess"):
        return "tess"
    if job.startswith(("w", "walkthrough", "bump")) and base == "task-restricted":
        return "walkthrough"
    return base


def adapt_ours_side(path: Path) -> dict:
    """qwen-code chat JSONL → 事件(calls/results)与行级汇总(字段对齐 lab)。"""
    calls = []
    results = []
    records = 0
    types: dict = {}
    res_ts_by_row = []
    um_last = None
    out_sum = 0
    thoughts_sum = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records += 1
            d = json.loads(line)
            t = d.get("type")
            types[t] = types.get(t, 0) + 1
            ts = _ts(d.get("timestamp") or "")
            res_ts_by_row.append(ts)
            um = d.get("usageMetadata")
            if isinstance(um, dict):
                um_last = um
                out_sum += int(um.get("candidatesTokenCount") or 0)
                thoughts_sum += int(um.get("thoughtsTokenCount") or 0)
            msg = d.get("message") or {}
            for p in msg.get("parts") or []:
                if isinstance(p, dict) and isinstance(p.get("functionCall"), dict):
                    fc = p["functionCall"]
                    nm = str(fc.get("name") or "?")
                    args = fc.get("args") or {}
                    if nm not in OURS_SIDE_NAME_KIND:
                        OURS_SIDE_NONSTD[nm] += 1
                    calls.append({"ts": ts, "name": nm, "args": args,
                                  "kind": classify(nm, args, OURS_SIDE_NAME_KIND, log_unmapped=False)})
            if t == "tool_result":
                tcr = d.get("toolCallResult")
                tcr = tcr if isinstance(tcr, dict) else {}
                rd = tcr.get("resultDisplay")
                rd = rd if isinstance(rd, dict) else {}
                out = rd.get("output")
                out = "" if out is None else (out if isinstance(out, str) else str(out))
                exit_code = rd.get("exitCode")
                ok = None if exit_code is None else (exit_code == 0)
                results.append({"ok": ok, "text": out, "exit": exit_code})
    t_first, t_last = first_last(res_ts_by_row)
    return {
        "calls": calls,
        "results": results,
        "records": records,
        "types": types,
        "um_last": um_last,
        "out_sum": out_sum,
        "thoughts_sum": thoughts_sum,
        "t_first": t_first,
        "t_last": t_last,
    }


def ours_side_record(path: Path) -> dict:
    a = adapt_ours_side(path)
    core = ring_core(a["calls"], a["results"])
    prompt = int(a["um_last"].get("promptTokenCount") or 0) if a["um_last"] else None
    cached = int(a["um_last"].get("cachedContentTokenCount") or 0) if a["um_last"] else None
    span = (a["t_last"] - a["t_first"]) if (a["t_first"] is not None and a["t_last"] is not None) else None
    rec = dict(core)
    rec.update({
        "records": a["records"],
        "types": a["types"],
        "results_total": len(a["results"]),
        "results_with_exit": sum(1 for r in a["results"] if r["exit"] is not None),
        "status_error": sum(1 for r in a["results"] if r.get("status") not in (None, "success")),
        "prompt_final": prompt,
        "cached_final": cached,
        "cache_ratio": round(cached / prompt, 6) if (prompt and cached is not None) else None,
        "out_tokens_sum": a["out_sum"],
        "thoughts_tokens_sum": a["thoughts_sum"],
        "span_s": round(span, 3) if span is not None else None,
    })
    return rec


def adapt_ours_arm(path: Path) -> dict:
    d = json.loads(path.read_text())
    calls = []
    results = []
    step_ts = []
    for st in d.get("steps", []):
        ts = _ts(st.get("timestamp") or "")
        step_ts.append(ts)
        for c in st.get("tool_calls") or []:
            nm = str(c.get("function_name") or "?")
            args = c.get("arguments") or {}
            calls.append({"ts": ts, "name": nm, "args": args, "kind": classify(nm, args, OURS_ARM_NAME_KIND)})
        for r in (st.get("observation") or {}).get("results") or []:
            content = r.get("content") if isinstance(r, dict) else None
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            ok = None
            if "Exit Code:" in text:
                m = re.search(r"Exit Code:\s*(\d+)", text)
                ok = (m.group(1) == "0") if m else None
            results.append({"ok": ok, "text": text})
    t_first, t_last = first_last(step_ts)
    return {
        "calls": calls,
        "results": results,
        "steps": len(d.get("steps", [])),
        "schema_version": d.get("schema_version"),
        "final_metrics": d.get("final_metrics"),
        "t_first": t_first,
        "t_last": t_last,
    }


def ours_arm_record(path: Path) -> dict:
    a = adapt_ours_arm(path)
    core = ring_core(a["calls"], a["results"])
    fm = a["final_metrics"] or {}
    prompt = fm.get("total_prompt_tokens")
    cached = fm.get("total_cached_tokens")
    span = (a["t_last"] - a["t_first"]) if (a["t_first"] is not None and a["t_last"] is not None) else None
    rec = dict(core)
    rec.update({
        "steps": a["steps"],
        "schema_version": a["schema_version"],
        "prompt_final": prompt,
        "cached_final": cached,
        "cache_ratio": round(cached / prompt, 6) if (prompt and cached is not None) else None,
        "out_tokens_sum": fm.get("total_completion_tokens"),
        "span_s": round(span, 3) if span is not None else None,
    })
    return rec


# ---------------------------------------------------------------------------
# 源 B(are):五种日志格式适配器
# ---------------------------------------------------------------------------
def adapt_are_claude(path: Path) -> dict:
    calls = []
    results = []
    row_ts = []
    res_ts_by_id: dict = {}
    n_assistant = 0
    duration_ms = None
    num_turns = None
    um_last = None
    out_sum = 0
    prompt_last = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            ts = _ts(d.get("timestamp"))
            if ts is not None:
                row_ts.append(ts)
            if t == "assistant":
                n_assistant += 1
                msg = d.get("message") or {}
                u = msg.get("usage")
                if isinstance(u, dict):
                    um_last = u
                    out_sum += int(u.get("output_tokens") or 0)
                for b in msg.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        nm = str(b.get("name") or "?")
                        args = b.get("input") or {}
                        if nm in DEFECT_NAME_KIND:
                            DEFECT_OCCURRENCES.append(f"{path}:{nm}")
                        calls.append({"ts": ts, "name": nm, "args": args, "kind": classify(nm, args, CLAUDE_NAME_KIND), "id": b.get("id")})
            elif t == "user":
                for b in (d.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        text = flatten_content(b.get("content"))
                        ok = not bool(b.get("is_error"))
                        results.append({"ok": ok, "text": text})
                        if ts is not None and b.get("tool_use_id"):
                            res_ts_by_id[b["tool_use_id"]] = ts
            elif t == "result":
                duration_ms = d.get("duration_ms")
                num_turns = d.get("num_turns")
    basis = "none"
    if any(c["ts"] is not None for c in calls):
        basis = "call_ts"
    n_fallback = 0
    for c in calls:
        if c["ts"] is None and c.get("id") in res_ts_by_id:
            c["ts"] = res_ts_by_id[c["id"]]
            n_fallback += 1
    if n_fallback:
        basis = "result_ts"
    t_first, t_last = first_last(row_ts)
    return {"calls": calls, "results": results, "row_ts": row_ts, "basis": basis,
            "n_assistant": n_assistant, "duration_ms": duration_ms, "num_turns": num_turns,
            "um_last": um_last, "out_sum": out_sum, "t_first": t_first, "t_last": t_last}


def adapt_are_gemini_nd(path: Path) -> dict:
    calls = []
    results = []
    row_ts = []
    stats = None
    res_status = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            ts = _ts(d.get("timestamp"))
            if ts is not None:
                row_ts.append(ts)
            if t == "tool_use":
                nm = str(d.get("tool_name") or "?")
                args = d.get("parameters") or {}
                calls.append({"ts": ts, "name": nm, "args": args, "kind": classify(nm, args, GEMINI_NAME_KIND)})
            elif t == "tool_result":
                out = d.get("output")
                out = "" if out is None else (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))
                status = d.get("status")
                ok = True if status == "success" else (False if status in ("error", "failed") else None)
                results.append({"ok": ok, "text": out})
            elif t == "result":
                stats = d.get("stats")
    t_first, t_last = first_last(row_ts)
    return {"calls": calls, "results": results, "row_ts": row_ts, "basis": "call_ts" if calls else "none",
            "stats": stats, "t_first": t_first, "t_last": t_last}


def adapt_are_gemini_text(path: Path) -> dict:
    calls = []
    results = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            if t == "action":
                nm = str(d.get("tool") or "?")
                args = {}
                content = d.get("content")
                if isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            args = parsed
                    except Exception:
                        args = {"command": content}
                elif isinstance(content, dict):
                    args = content
                calls.append({"ts": None, "name": nm, "args": args, "kind": classify(nm, args, GEMINI_NAME_KIND)})
            elif t == "observation":
                content = d.get("content")
                text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                ok = None
                m = re.match(r"Tool result \(([^)]+)\)", text)
                if m:
                    ok = (m.group(1).strip().lower() == "success")
                results.append({"ok": ok, "text": text})
    return {"calls": calls, "results": results, "row_ts": [], "basis": "none",
            "t_first": None, "t_last": None}


def adapt_are_codex_text(path: Path) -> dict:
    calls = []
    results = []
    tokens_total = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            marker = d.get("raw_marker")
            content = d.get("content")
            content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            if t == "action" and marker == "exec":
                # 命令文本在首行;取 " in /workspace" 之前的部分做类细分
                head = content.split(" in /workspace")[0]
                args = {"command": head[:2000]}
                calls.append({"ts": None, "name": "exec", "args": args, "kind": classify("exec", args, CODEX_NAME_KIND)})
                ok = None
                if "succeeded in" in content or "exited 0 in" in content:
                    ok = True
                else:
                    m = re.search(r"exited (\d+) in", content)
                    if m:
                        ok = (m.group(1) == "0")
                results.append({"ok": ok, "text": content})
            elif t == "other" and marker == "tokens used":
                first = content.split("\n", 1)[0].strip().replace(",", "")
                if first.isdigit():
                    tokens_total = int(first)
    return {"calls": calls, "results": results, "row_ts": [], "basis": "none",
            "tokens_total": tokens_total, "t_first": None, "t_last": None}


def adapt_are_codex_items(path: Path) -> dict:
    items: dict = {}
    order: list = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            it = d.get("item") or {}
            iid = it.get("id")
            if not iid:
                continue
            kind_state = "completed" if str(d.get("type", "")).endswith("completed") else "started"
            if iid not in items:
                items[iid] = {}
                order.append(iid)
            items[iid][kind_state] = it
    calls = []
    results = []
    for iid in order:
        st = items[iid]
        it = st.get("completed") or st.get("started") or {}
        if it.get("type") == "command_execution":
            cmd = it.get("command") or ""
            args = {"command": cmd}
            calls.append({"ts": None, "name": "command_execution", "args": args, "kind": classify("command_execution", args, CODEX_NAME_KIND)})
            ec = it.get("exit_code")
            ok = None if ec is None else (ec == 0)
            out = it.get("aggregated_output") or ""
            results.append({"ok": ok, "text": out})
    return {"calls": calls, "results": results, "row_ts": [], "basis": "none",
            "t_first": None, "t_last": None}


# ---------------------------------------------------------------------------
# 组装并集表
# ---------------------------------------------------------------------------
def load_jsonl(path: Path):
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for l in fh:
            l = l.strip()
            if l:
                out.append(json.loads(l))
    return out


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--are-root", default="/home/ebt/harbor-runs/data/autoresearch-eval")
    ap.add_argument("--ours-root", default="/home/ebt/harbor-runs/jobs/agent")
    ap.add_argument("--traj-lab", default="/home/ebt/rsi-dev/harness/refs/traj-features-2026-10-14")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    are_root = Path(args.are_root)
    ours_root = Path(args.ours_root)
    traj_lab = Path(args.traj_lab)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    records = []
    audit = {"unmapped": {}, "formats": {}, "notes": {}, "ours_compare": {"checked": 0, "mismatch": []},
             "are_compare": {"gemini_stats_checked": 0, "mismatch": []}}

    # 源 A 侧
    lab_sides = {(r["job"], r["trial"], r["side"]): r for r in load_jsonl(traj_lab / "features_sides.jsonl")}
    lab_runs = {(r["job"], r["trial"]): r for r in load_jsonl(traj_lab / "features_runs.jsonl")}
    for job_dir in sorted(p for p in ours_root.iterdir() if p.is_dir()):
        for trial_dir in sorted(job_dir.glob("task-*")):
            collect = trial_dir / "artifacts/root/wt/collect"
            if not (collect / "x").is_dir():
                continue
            job = job_dir.name
            trial = trial_dir.name
            family = family_of(job, trial)
            chats = collect / "chats"
            uuids = {}
            for side in ("a", "b"):
                p = collect / "x" / f"session-{side}.uuid"
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
                rec = ours_side_record(f)
                run = lab_runs.get((job, trial)) or {}
                unit = f"ours/{job}/{trial}/{side}"
                lab = lab_sides.get((job, trial, side))
                if lab:
                    audit["ours_compare"]["checked"] += 1
                    for k in ("calls_total", "calls_by_name", "kinds", "gaps_n", "gaps_median_s",
                              "gaps_cv_robust", "gaps_p600_frac", "masked", "kind_entropy",
                              "transition_entropy", "span_s", "cache_ratio", "out_tokens_sum"):
                        if rec.get(k) != lab.get(k):
                            audit["ours_compare"]["mismatch"].append({"unit": unit, "field": k,
                                                                      "ours": rec.get(k), "lab": lab.get(k)})
                records.append(_unit(unit, "ours", family, None, "qwen-code", "qwen_chat", rec,
                                     basis="call_ts", meta={"normal": run.get("normal"), "rounds": run.get("rounds")},
                                     notes=[]))
    # 源 A 臂
    for f in sorted(ours_root.glob("*/*/agent/trajectory.json")):
        job = f.parts[-4]
        trial = f.parts[-3]
        rec = ours_arm_record(f)
        unit = f"ours/{job}/{trial}/arm"
        records.append(_unit(unit, "ours", "arm", None, "qwen-code", "atif", rec,
                             basis="step_ts", meta={"schema_version": rec.get("schema_version")}, notes=[]))

    # 源 B
    rollouts = {}
    tasks_meta = {}
    for subset in ("open-ended", "optimization"):
        for r in load_jsonl(are_root / subset / "rollouts.jsonl"):
            mrow = MODEL_ALIAS.get(r.get("model"), r.get("model"))
            rollouts[(subset, mrow, r.get("task_id"))] = r
        for t in load_jsonl(are_root / subset / "tasks.jsonl"):
            tasks_meta[(subset, t.get("task_id"))] = t
    fmt_counts = collections.Counter()
    for subset in ("open-ended", "optimization"):
        tdir = are_root / subset / "trajectories"
        if not tdir.is_dir():
            continue
        for mdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            model = MODEL_ALIAS.get(mdir.name, mdir.name)
            for f in sorted(mdir.glob("*.jsonl")):
                task = f.stem
                rec = _scan_are(f)
                fmt_counts[rec["format"]] += 1
                unit = f"are/{subset}/{model}/{task}"
                notes = list(rec["notes"])
                base = {"calls": rec["calls"], "results": rec["results"]}
                core = ring_core(base["calls"], base["results"])
                extra = {}
                if rec["format"] == "claude_stream":
                    extra = _claude_extra(rec)
                elif rec["format"] == "gemini_ndjson":
                    extra = _gemini_extra(rec)
                elif rec["format"] == "codex_text":
                    extra = {"tokens_total": rec.get("tokens_total")}
                meta = _meta_from_rollout(rollouts.get((subset, model, task)), tasks_meta.get((subset, task)))
                meta.update(extra.get("meta", {}))
                if mdir.name != model:
                    meta["model_dir"] = mdir.name
                cache = extra.get("cache_ratio")
                rec_out = dict(core)
                rec_out.update({k: v for k, v in extra.items() if k != "meta"})
                records.append(_unit(unit, "are", subset, model, rec["harness"], rec["format"], rec_out,
                                     basis=rec["basis"], meta=meta, notes=notes,
                                     duration_ms=extra.get("duration_ms"), span_s=extra.get("span_s"),
                                     cache_ratio=cache, tokens=extra.get("tokens")))
                # gemini stats.tool_calls 对账
                st = extra.get("stats")
                if isinstance(st, dict) and isinstance(st.get("tool_calls"), int):
                    audit["are_compare"]["gemini_stats_checked"] += 1
                    if st["tool_calls"] != core["calls_total"]:
                        audit["are_compare"]["mismatch"].append({"unit": unit, "stats_tool_calls": st["tool_calls"],
                                                                 "ours": core["calls_total"]})

    records.sort(key=lambda r: r["unit"])
    with (out / "features_union.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    audit["unmapped"] = dict(sorted(UNMAPPED.items()))
    audit["ours_side_nonstandard"] = dict(sorted(OURS_SIDE_NONSTD.items()))
    audit["defect_occurrences"] = sorted(DEFECT_OCCURRENCES)
    audit["formats"] = dict(fmt_counts)
    if audit["ours_compare"]["mismatch"]:
        audit["notes"]["ours_mismatch_n"] = len(audit["ours_compare"]["mismatch"])
    if audit["are_compare"]["mismatch"]:
        audit["notes"]["are_mismatch_n"] = len(audit["are_compare"]["mismatch"])
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1))

    # summary.md
    write_summary(records, audit, out)

    # 控制台摘要
    ours_n = sum(1 for r in records if r["source"] == "ours")
    are_n = sum(1 for r in records if r["source"] == "are")
    calls_are = sum(r["calls_total"] for r in records if r["source"] == "are")
    calls_ours = sum(r["calls_total"] for r in records if r["source"] == "ours")
    print(f"units={len(records)} (ours {ours_n} / are {are_n})")
    print(f"calls: ours={calls_ours} are={calls_are} all={calls_ours + calls_are}")
    print(f"are avg calls/episode = {calls_are / max(1, are_n):.4f}")
    print(f"formats: {dict(fmt_counts)}")
    print(f"unmapped names: {dict(UNMAPPED)}")
    print(f"ours compare: {audit['ours_compare']['checked']} checked, {len(audit['ours_compare']['mismatch'])} mismatches")
    print(f"gemini stats compare: {audit['are_compare']['gemini_stats_checked']} checked, {len(audit['are_compare']['mismatch'])} mismatches")
    return 0


def _scan_are(f: Path) -> dict:
    """按行侦测格式并调度适配器。"""
    first_rows = []
    with f.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            first_rows.append(d)
            if len(first_rows) >= 8:
                break
    fmt = None
    for d in first_rows:
        ks = set(d.keys())
        if "item" in ks and str(d.get("type", "")).startswith("item."):
            fmt = "codex_items"
            break
        if "tool_name" in ks and "tool_id" in ks:
            fmt = "gemini_ndjson"
            break
        if "message" in ks:
            fmt = "claude_stream"
            break
        if "raw_marker" in ks:
            fmt = "codex_text"
            break
        if "tool" in ks:
            fmt = "gemini_text"
            break
        if "type" in ks and d.get("type") == "result" and "subtype" in ks:
            fmt = "claude_result_only"
            break
    notes = []
    if fmt == "claude_result_only":
        fmt = "claude_stream"
        notes.append("result-first")
    if fmt is None:
        fmt = "unknown"
        notes.append("empty-file" if not first_rows else "unknown-format")
    harness = "claude"
    if fmt in ("gemini_ndjson", "gemini_text"):
        harness = "gemini"
    elif fmt in ("codex_text", "codex_items"):
        harness = "codex"
    if fmt == "claude_stream":
        a = adapt_are_claude(f)
    elif fmt == "gemini_ndjson":
        a = adapt_are_gemini_nd(f)
    elif fmt == "gemini_text":
        a = adapt_are_gemini_text(f)
    elif fmt == "codex_text":
        a = adapt_are_codex_text(f)
    elif fmt == "codex_items":
        a = adapt_are_codex_items(f)
    else:
        a = {"calls": [], "results": [], "row_ts": [], "basis": "none", "t_first": None, "t_last": None}
    if not a["calls"] and fmt != "unknown":
        notes.append("no-calls")
    a.update({"format": fmt, "harness": harness, "notes": notes})
    return a


def _claude_extra(rec: dict) -> dict:
    um = rec.get("um_last") or {}
    out = int(um.get("output_tokens") or 0) if um else None
    read = int(um.get("cache_read_input_tokens") or 0) if um else None
    creation = int(um.get("cache_creation_input_tokens") or 0) if um else None
    input_t = int(um.get("input_tokens") or 0) if um else None
    prompt = None if input_t is None else (input_t + read + creation)
    cache = round(read / prompt, 6) if (prompt and read is not None) else None
    t_first, t_last = rec.get("t_first"), rec.get("t_last")
    span = (t_last - t_first) if (t_first is not None and t_last is not None) else None
    return {
        "out_tokens_sum": rec.get("out_sum") if um else None,
        "prompt_final": prompt,
        "cached_final": read,
        "cache_ratio": cache,
        "duration_ms": rec.get("duration_ms"),
        "span_s": round(span, 3) if span is not None else None,
        "meta": {"num_turns": rec.get("num_turns")},
    }


def _gemini_extra(rec: dict) -> dict:
    st = rec.get("stats") if isinstance(rec.get("stats"), dict) else {}
    cached = st.get("cached")
    input_tokens = st.get("input_tokens")
    cache = round(cached / input_tokens, 6) if (isinstance(cached, int) and isinstance(input_tokens, int) and input_tokens) else None
    duration = st.get("duration_ms")
    t_first, t_last = rec.get("t_first"), rec.get("t_last")
    span = (t_last - t_first) if (t_first is not None and t_last is not None) else None
    return {
        "out_tokens_sum": st.get("output_tokens"),
        "tokens_total": st.get("total_tokens"),
        "cache_ratio": cache,
        "duration_ms": duration,
        "span_s": round(span, 3) if span is not None else None,
        "stats": st,
    }


def _meta_from_rollout(roll, taskm) -> dict:
    m = {}
    if isinstance(roll, dict):
        for k in ("status", "returncode", "duration_s", "best_aggregate_improvement", "n_evaluations",
                  "wall_clock_s", "gpu_util_max", "n_code_files", "reward", "reason",
                  "regime_move_verified", "tier", "novelty_move", "observable", "conclusion"):
            if k in roll:
                m[k] = roll[k]
    if isinstance(taskm, dict):
        for k in ("domain",):
            if k in taskm and k not in m:
                m[k] = taskm[k]
    return m


def _unit(unit, source, corpus, model, harness, fmt, rec, basis, meta, notes, duration_ms=None,
          span_s=None, cache_ratio=None, tokens=None) -> dict:
    return {
        "unit": unit,
        "source": source,
        "corpus": corpus,
        "model": model,
        "harness": harness,
        "format": fmt,
        "calls_total": rec.get("calls_total", 0),
        "calls_by_name": rec.get("calls_by_name", {}),
        "kinds": rec.get("kinds", {}),
        "kind_entropy": rec.get("kind_entropy"),
        "transition_entropy": rec.get("transition_entropy"),
        "trans_entropy_ns": rec.get("trans_entropy_ns"),
        "mi_action": rec.get("mi_action"),
        "p_action": rec.get("p_action"),
        "s_smooth": rec.get("s_smooth"),
        "mi_perm_p": rec.get("mi_perm_p"),
        "gaps_n": rec.get("gaps_n", 0),
        "gaps_median_s": rec.get("gaps_median_s"),
        "gaps_cv_robust": rec.get("gaps_cv_robust"),
        "gaps_p600_frac": rec.get("gaps_p600_frac"),
        "gaps_basis": basis if rec.get("gaps_n") else None,
        "masked": rec.get("masked", 0),
        "masked_rate": rec.get("masked_rate"),
        "results_judged": rec.get("results_judged", 0),
        "cache_ratio": cache_ratio if cache_ratio is not None else rec.get("cache_ratio"),
        "out_tokens_sum": rec.get("out_tokens_sum"),
        "prompt_final": rec.get("prompt_final"),
        "cached_final": rec.get("cached_final"),
        "span_s": span_s if span_s is not None else rec.get("span_s"),
        "duration_ms": duration_ms,
        "tokens": tokens,
        "meta": meta or {},
        "notes": notes or [],
    }


def write_summary(records: list, audit: dict, out: Path) -> None:
    lines = []
    lines.append("# crossfusion-2026-10-15 — 并集轨迹机械统计(摘要)")
    lines.append("")
    lines.append("数据并集:ours(54 侧 + 8 臂)× are(AutoResearchEval 800 条,钉版 412fb490…);"
                 "方法并集:统一 8 类 taxonomy + 熵/节律/静默失败/缓存(定义见 README,实现即定义)。")
    lines.append("")
    lines.append("## 语料")
    lines.append("| source | corpus | units | calls | masked | gaps 可算 | 说明 |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    grp: dict = {}
    for r in records:
        grp.setdefault((r["source"], r["corpus"]), []).append(r)
    for (src, corp), rs in sorted(grp.items()):
        calls = sum(r["calls_total"] for r in rs)
        mask = sum(r["masked"] for r in rs)
        gaps_ok = sum(1 for r in rs if r["gaps_basis"])
        lines.append(f"| {src} | {corp} | {len(rs)} | {calls} | {mask} | {gaps_ok}/{len(rs)} | |")
    lines.append("")
    lines.append("## 逐模型(are)")
    lines.append("| model | units | calls | calls/ep | kind_entropy 中位 | masked_rate 中位 | cache_ratio 中位 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    mgrp: dict = {}
    for r in records:
        if r["source"] == "are":
            mgrp.setdefault(r["model"], []).append(r)
    for m, rs in sorted(mgrp.items()):
        calls = sum(r["calls_total"] for r in rs)
        ke = _median([r["kind_entropy"] for r in rs if r["kind_entropy"] is not None])
        mr = _median([r["masked_rate"] for r in rs if r["masked_rate"] is not None])
        cr = _median([r["cache_ratio"] for r in rs if r["cache_ratio"] is not None])
        lines.append(f"| {m} | {len(rs)} | {calls} | {calls/len(rs):.2f} | "
                     f"{ke if ke is None else round(ke,4)} | {mr if mr is None else round(mr,6)} | "
                     f"{cr if cr is None else round(cr,4)} |")
    lines.append("")
    lines.append("## 格式覆盖")
    lines.append("| format | units | gaps(basis) | masked 可判 | cache | duration |")
    lines.append("|---|---:|---|---:|---:|---:|")
    fgrp: dict = {}
    for r in records:
        fgrp.setdefault((r["source"], r["format"]), []).append(r)
    for (src, fmt), rs in sorted(fgrp.items()):
        gb = collections.Counter(r["gaps_basis"] for r in rs if r["gaps_basis"])
        judged = sum(1 for r in rs if r["results_judged"])
        cache_n = sum(1 for r in rs if r["cache_ratio"] is not None)
        dur_n = sum(1 for r in rs if r["duration_ms"] is not None)
        lines.append(f"| {src}/{fmt} | {len(rs)} | {dict(gb) or '—'} | {judged} | {cache_n} | {dur_n} |")
    lines.append("")
    lines.append("## 解耦指标(无平滑;2026-10-15 追加,据外部建议核对后落地)")
    lines.append("H⁽⁰⁾=无平滑经验条件熵;I_action=H_kind·ln2−H⁽⁰⁾=Î(C_t;C_{t+1})(nat);"
                 "P_action=I/(H_kind·ln2)(H_kind=0 ⇒ 未定义);S_smooth=平滑熵−H⁽⁰⁾;"
                 "perm p=保频置换单侧 p(200 次,crc32 定种)。")
    lines.append("| source | corpus | 单元 | I_action 中位(nat) | P_action 中位 | S_smooth 中位 | perm p<0.05 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    dg2: dict = {}
    for r in records:
        dg2.setdefault((r["source"], r["corpus"]), []).append(r)
    for (src2, corp2), rs in sorted(dg2.items()):
        mis = [r.get("mi_action") for r in rs if r.get("mi_action") is not None]
        pas = [r.get("p_action") for r in rs if r.get("p_action") is not None]
        sss = [r.get("s_smooth") for r in rs if r.get("s_smooth") is not None]
        p05 = sum(1 for r in rs if r.get("mi_perm_p") is not None and r["mi_perm_p"] < 0.05)
        fmt_cell = lambda xs: (round(_median(xs), 4) if xs else "—")
        lines.append(f"| {src2} | {corp2} | {len(rs)} | {fmt_cell(mis)} | {fmt_cell(pas)} | "
                     f"{fmt_cell(sss)} | {p05} |")
    lines.append("")
    lines.append("## 不变式/审计")
    oc = audit["ours_compare"]
    ac = audit["are_compare"]
    calls_are = sum(r["calls_total"] for r in records if r["source"] == "are")
    nts = [r["meta"].get("num_turns") for r in records
           if r["source"] == "are" and isinstance(r["meta"].get("num_turns"), (int, float))]
    lines.append(f"- ours 侧 vs traj-features lab 逐字段对照:{oc['checked']} 单元,{len(oc['mismatch'])} 处不一致")
    lines.append(f"- ours 侧表外工具名(按 lab 惯例归 other,合计 {sum(audit.get('ours_side_nonstandard', {}).values())} 次):"
                 f"{audit.get('ours_side_nonstandard') or '(无)'}")
    lines.append(f"- gemini stats.tool_calls 对账:{ac['gemini_stats_checked']} 文件,{len(ac['mismatch'])} 处不一致"
                 f"(该处为数据自身矛盾:{ac['mismatch'][0]['unit'] if ac['mismatch'] else '—'})")
    lines.append(f"- 未映射工具名:{audit['unmapped'] or '(无)'};工件名(2 处 __unparsedToolInput,归 other):"
                 f"{audit.get('defect_occurrences') or '(无)'}")
    paper_line = (f"- 论文 §2.2.3 复算:论文「73k tool calls at an average of 92.3 steps per episode」;"
                  f"本复算 calls={calls_are}({calls_are/800:.4f}/跑)")
    if nts:
        paper_line += (f";claude result 行 num_turns 均值 {sum(nts)/len(nts):.3f}(n={len(nts)})"
                       f" —— 与 92.3 吻合的是工具调用均值,不是 num_turns")
    lines.append(paper_line)
    lines.append("")
    lines.append("## 备注")
    lines.append("- 单元=一条 agent 轨迹(ours 侧/臂;are 一次 rollout);确定性、零模型调用;逐字节可复现(check.py)。")
    lines.append("- notes 类目:result-first(opus-4.8 优化集 15 个文件首行为 result 行;其中 5 个仅 1 行、0 调用)/"
                 "empty-file(1 个 0 行文件)/unknown-format —— 均在 audit.json 与单元 notes 中标注。")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
