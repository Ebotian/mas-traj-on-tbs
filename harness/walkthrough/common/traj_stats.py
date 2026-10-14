#!/usr/bin/env python3
# traj_stats.py — 里程碑统计层(任务无关;2026-10-12 用户裁定:
#   「统计结论只能由程序自动生成;跨实验共享同一程序;不包含任何任务相关量;
#     所有统计结论始终对双方只读;由 ckpt-m00/m01/m1 作为钩子自动触发;无联网运算」)。
# 原则:
#   - 纯本地、无网络、无 LLM、无任务先验(无逐任务常量/字段名/白名单);
#   - 两侧对称计算;内容为输入的纯函数(不含墙钟;里程碑身份 = 标签提交 sha/时间);
#   - 幂等:同输入→字节相同;已生成且字节相同则跳过;
#   - 产物 x/stats/<tag>.json(0444)+ 同数字渲染 <tag>.md(0444),单一共享目录。
# 触发:reference-transaction 钩子(committed refs/tags/ckpt-m*)+ wrapper 看门件 + 手工(auto 幂等)。
# 子命令:
#   gen  <repo> <xdir> <tag> [--chats-root D] [--transcript-a P] [--transcript-b P]
#                           [--wt-root D] [--out D] [--no-fs-avail]
#   auto <repo> <xdir> [同上]    # 对全部尚无产物的 ckpt-m* 标签执行 gen
# 环境: WT_CHATS_ROOT(默认 /root/.qwen/projects,与 post-commit.sh 同源)。

# v2(2026-10-12):adoption 按两侧事件时间归并、同刻记并发;tokens=per_call 并派生 uncached;
#   transcript 增 sha256_leq_cut(≤cut 前缀=固定输入身份);ledger/protocol 增来源标注;
#   路径集合更名 observed_paths(工具参数中观察到的路径串);meta 增 schema/usage_semantics。
# v3(2026-10-13):计数与截断样例分离(ledger.unresolved_count、pacing.silences_gt_600s_count,
#   样例列表仍截断,md 同显);里程碑输入钉版:账本与 dir-*.json 首次读取即复制进 <out>/pin/
#   并以 pin:<路径> 标注,旧检查点重生成不再随工作目录增长漂移,缺失记未知(source=missing,
#   计数 null);删除随文件增长漂移的全局字段(全文件行数/全文件 sha256),保留 ≤cut 前缀身份
#   (sha256_leq_cut、lines_leq_cut、cut_last_line);adoption 更名 text_overlap(文本重合计数,
#   非语义采纳——语义采纳需另行绑定读取/改动/验证事件,未实现);schema=traj-stats/3。
# v4(2026-10-14):时基=可得性上界——cut_epoch = max(标签提交时间, 全部来源 available_at);新增
#   availability 块逐源记 {ref, available_at, basis, mtime, declared_at},空值进 unknown(md 同显)。
#   来源可得时间:tag 来源(refs/forks)=提交时间;文件来源首读取 max(fs mtime, 自述 at;分钟精度
#   "…T14:51Z" 向上取整到 :59),随 pin 写 <pin>.meta 侧车(写一次;重生成只读侧车与 pin,不再摸 fs);
#   首读缺失写 <pin>.absent 负标记——重生成不再吸收后到产物(m00 曾把 P0.2 的 dir 吸进来过)。
#   --no-fs-avail:归档/实验重放关闭 mtime 通道(归档副本 mtime 已被重置,只信自述 at);schema=traj-stats/4。

import calendar
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

K_GRAM = 8
SILENCE_S = 600
PATH_RE = re.compile(r"(?:/[A-Za-z0-9_.\-]+){2,}|[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+")
WORD_RE = re.compile(r"[0-9A-Za-z_\u4e00-\u9fff]+")
TRAJ_REF_RE = re.compile(r"traj-([ab])#L(\d+)(?:-L?(\d+))?")
ANCHOR_RE = re.compile(r"^L(\d+)(?:-L?(\d+))?$")


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=60)
        return r.returncode == 0, (r.stdout or "").strip()
    except Exception:
        return False, ""


def tsparse(s):
    if not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1]
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(calendar.timegm(time.strptime(s, fmt)))
        except Exception:
            pass
    return None


def atparse(s):
    """自述 at 解析(可得性上界):全精度原样;分钟精度("…T14:51Z")向上取整到该分钟 :59。"""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1]
    for fmt, adj in (("%Y-%m-%dT%H:%M:%S.%f", 0), ("%Y-%m-%dT%H:%M:%S", 0),
                     ("%Y-%m-%dT%H:%M", 59)):
        try:
            return int(calendar.timegm(time.strptime(s, fmt))) + adj
        except Exception:
            pass
    return None


def declared_at_of(raw):
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None
    return atparse(d.get("at")) if isinstance(d, dict) else None


def compute_avail(mtime=None, declared=None):
    vals = [v for v in (mtime, declared) if v is not None]
    if mtime is not None and declared is not None:
        basis = "mtime+declared_at"
    elif mtime is not None:
        basis = "mtime"
    elif declared is not None:
        basis = "declared_at"
    else:
        basis = "unknown"
    return {"mtime": mtime, "declared_at": declared,
            "available_at": (max(vals) if vals else None), "basis": basis}


def avail_entry(ref, av):
    if av is None:
        return {"ref": ref, "mtime": None, "declared_at": None, "available_at": None,
                "basis": "missing" if ref == "missing" else "unknown"}
    return {"ref": ref, "mtime": av.get("mtime"), "declared_at": av.get("declared_at"),
            "available_at": av.get("available_at"), "basis": av.get("basis", "unknown")}


def live_avail(path, raw, fs_avail=True):
    mtime = None
    if fs_avail:
        try:
            mtime = int(math.ceil(os.stat(path).st_mtime))  # 上界:文件最后写入的整秒不早于实际
        except Exception:
            mtime = None
    return compute_avail(mtime=mtime, declared=declared_at_of(raw))


def meta_or_declared(pin_dir, pin_name, raw):
    """pin 读取路径的可得时间:优先 <pin>.meta 侧车(首读冻结值);无侧车回退自述 at。"""
    m = meta_read(pin_dir, pin_name)
    if m is not None:
        return {"mtime": m.get("mtime"), "declared_at": m.get("declared_at"),
                "available_at": m.get("available_at"), "basis": m.get("basis", "unknown")}
    return compute_avail(mtime=None, declared=declared_at_of(raw))


def walk_collect(o, want_keys, out, depth=0):
    if depth > 10:
        return
    if isinstance(o, dict):
        if any(k in o for k in want_keys):
            out.append(o)
        for v in o.values():
            walk_collect(v, want_keys, out, depth + 1)
    elif isinstance(o, list):
        for v in o:
            walk_collect(v, want_keys, out, depth + 1)


def strings_of(o, out, depth=0):
    if depth > 8:
        return
    if isinstance(o, str):
        out.append(o)
    elif isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str):
                out.append(k)
            strings_of(v, out, depth + 1)
    elif isinstance(o, list):
        for v in o:
            strings_of(v, out, depth + 1)


def assistant_text(d):
    m = d.get("message")
    if not isinstance(m, dict):
        return ""
    parts = m.get("parts")
    if not isinstance(parts, list):
        return ""
    t = []
    for q in parts:
        if isinstance(q, dict) and isinstance(q.get("text"), str):
            t.append(q["text"])
    return "\n".join(t)


def assistant_usage(d):
    u = d.get("usageMetadata")
    if not isinstance(u, dict):
        return None
    m = {"prompt": "promptTokenCount", "candidates": "candidatesTokenCount",
         "thoughts": "thoughtsTokenCount", "cached": "cachedContentTokenCount"}
    got = {}
    for k, kk in m.items():
        v = u.get(kk)
        if isinstance(v, (int, float)):
            got[k] = int(v)
    return got or None


def normalize_cmd(c):
    c = c.strip()
    for _ in range(3):
        c2 = re.sub(r"^(?:cd\s+\S+\s*&&\s*)", "", c)
        c2 = re.sub(r"^(?:timeout\s+\S+\s+)", "", c2)
        c2 = re.sub(r"^(?:\w+=\S+\s+)", "", c2)
        if c2 == c:
            break
        c = c2
    return c


def side_stats(path, cut):
    rows = []
    pref = hashlib.sha256()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f, 1):
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                ts = tsparse(d.get("timestamp"))
                if ts is None or ts > cut:
                    continue
                rows.append((i, ts, d))
                pref.update(ln.encode("utf-8", "replace"))
    by_type, texts = {}, []
    usage = {"prompt": 0, "candidates": 0, "thoughts": 0, "cached": 0}
    usage_events = 0
    paths_seen, cmds = set(), {}
    for i, ts, d in rows:
        t = d.get("type")
        by_type[t] = by_type.get(t, 0) + 1
        if t == "assistant":
            tx = assistant_text(d)
            if tx:
                texts.append((i, ts, tx))
            u = assistant_usage(d)
            if u:
                usage_events += 1
                for k in usage:
                    usage[k] += u.get(k, 0)
        dicts = []
        walk_collect(d, ("function_args", "functionCall"), dicts)
        for dd in dicts:
            ss = []
            strings_of(dd, ss)
            for s in ss:
                for m in PATH_RE.findall(s):
                    tok = m.strip("'\"`,;:")
                    if len(tok) >= 4:
                        paths_seen.add(tok)
            inner = []
            walk_collect(dd, ("command",), inner)
            for idd in inner:
                c = idd.get("command")
                if isinstance(c, str) and c.strip():
                    c = normalize_cmd(c)
                    w = WORD_RE.findall(c.split()[0]) if c.split() else []
                    if w:
                        cmds[w[0]] = cmds.get(w[0], 0) + 1
    gaps = [rows[j][1] - rows[j - 1][1] for j in range(1, len(rows))
            if rows[j][1] >= rows[j - 1][1]]
    silences = [{"from": rows[j - 1][1], "to": rows[j][1], "seconds": rows[j][1] - rows[j - 1][1]}
                for j in range(1, len(rows)) if rows[j][1] - rows[j - 1][1] > SILENCE_S]

    def q(v, p):
        if not v:
            return None
        v = sorted(v)
        return v[min(len(v) - 1, int(p * (len(v) - 1)))]

    return {
        "lines_leq_cut": len(rows), "cut_last_line": (rows[-1][0] if rows else None),
        "by_type": dict(sorted(by_type.items())),
        "assistant_texts": len(texts), "tool_results": by_type.get("tool_result", 0),
        "usage_events": usage_events, "tokens": usage if usage_events else None,
        "gaps": {"count": len(gaps), "median_s": q(gaps, 0.5), "p90_s": q(gaps, 0.9),
                 "p99_s": q(gaps, 0.99), "max_s": (max(gaps) if gaps else None)},
        "silences_gt_600s": silences[:8], "silences_gt_600s_count": len(silences),
        "first_ts": rows[0][1] if rows else None, "last_ts": rows[-1][1] if rows else None,
        "uncached": (usage["prompt"] - usage["cached"]) if usage_events else None,
        "sha256_leq_cut": pref.hexdigest(),
        "observed_paths": sorted(paths_seen),
        "commands_top": sorted(cmds.items(), key=lambda kv: (-kv[1], kv[0]))[:12],
        "_texts": texts,
    }


def pin_write_meta(pin_dir, name, meta):
    """写 <name>.meta 侧车(写一次、0444):把首读判定的可得时间冻结成固定输入。"""
    if not pin_dir or not isinstance(meta, dict):
        return None
    try:
        os.makedirs(pin_dir, exist_ok=True)
        mp = os.path.join(pin_dir, name + ".meta")
        if not os.path.exists(mp):
            with open(mp, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, ensure_ascii=False, sort_keys=True)
                mf.write("\n")
            os.chmod(mp, 0o444)
        return mp
    except Exception:
        return None


def meta_read(pin_dir, name):
    if not pin_dir:
        return None
    try:
        with open(os.path.join(pin_dir, name + ".meta"), encoding="utf-8") as f:
            m = json.load(f)
        return m if isinstance(m, dict) else None
    except Exception:
        return None


def pin_write(pin_dir, name, raw, meta=None):
    if not pin_dir:
        return None
    try:
        os.makedirs(pin_dir, exist_ok=True)
        p = os.path.join(pin_dir, name)
        if not os.path.exists(p):
            with open(p, "wb") as f:
                f.write(raw)
            os.chmod(p, 0o444)
            pin_write_meta(pin_dir, name, meta)
        return p
    except Exception:
        return None


def pin_write_absent(pin_dir, name):
    """首读缺失负标记:存在则重生成一律记 missing,不再吸收后到产物。"""
    if not pin_dir:
        return None
    try:
        os.makedirs(pin_dir, exist_ok=True)
        p = os.path.join(pin_dir, name + ".absent")
        if not os.path.exists(p):
            with open(p, "w") as f:
                f.write("absent\n")
            os.chmod(p, 0o444)
        return p
    except Exception:
        return None


def load_ledger(repo, tag, xdir, wt_root, side, pin_dir=None, fs_avail=True):
    ok, text = git(repo, "show", "%s:refs-%s.jsonl" % (tag, side))
    if ok and text:
        return (text.splitlines(), "tag:%s" % tag, None,
                {"mtime": None, "declared_at": None, "available_at": None, "basis": "commit"})
    name = "%s.refs-%s.jsonl" % (tag, side)
    if pin_dir:
        p = os.path.join(pin_dir, name)
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                return (raw.decode("utf-8", "replace").splitlines(), "pin:%s" % p, None,
                        meta_or_declared(pin_dir, name, raw))
            except Exception:
                pass
        if os.path.exists(os.path.join(pin_dir, name + ".absent")):
            return [], "missing", None, None
    for p in (os.path.join(wt_root, side, "refs-%s.jsonl" % side),
              os.path.join(repo, "refs-%s.jsonl" % side),
              os.path.join(xdir, "refs-%s.jsonl" % side)):
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                avail = live_avail(p, raw, fs_avail)
                return (raw.decode("utf-8", "replace").splitlines(), "file:%s" % p,
                        (name, raw, avail), avail)
            except Exception:
                pass
    pin_write_absent(pin_dir, name)
    return [], "missing", None, None


def ledger_stats(lines):
    by_kind, unresolved, traj_ranges = {}, [], {("a"): [], ("b"): []}
    peer_lines = 0
    for ln in lines:
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        kind = d.get("kind") or d.get("class") or d.get("type") or "?"
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if kind == "unresolved":
            unresolved.append("%s: %s" % (d.get("id", "?"), str(d.get("reason", ""))[:80]))
        if kind == "traj":
            who = d.get("who")
            am = ANCHOR_RE.match(str(d.get("anchor", "")).strip())
            if who in ("a", "b") and am:
                l1 = int(am.group(1)); l2 = int(am.group(2) or am.group(1))
                traj_ranges[who].append((l1, l2))
        for m in TRAJ_REF_RE.finditer(ln):
            tgt, l1, l2 = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
            traj_ranges[tgt].append((l1, l2))
    return {"entries": len(lines), "by_kind": dict(sorted(by_kind.items())),
            "unresolved": unresolved[:10], "unresolved_count": len(unresolved),
            "traj_ranges": traj_ranges}


def text_overlap_stats(b_side_stats_map, ledgers):
    merged = []
    for side in ("a", "b"):
        for (i, ts, tx) in b_side_stats_map[side]["_texts"]:
            merged.append((ts, side, i, tx))
    merged.sort(key=lambda r: (r[0], r[1], r[2]))
    grams = {}
    events = []
    seen = set()
    for ts, side, i, tx in merged:
        words = WORD_RE.findall(tx.lower())
        for j in range(0, max(0, len(words) - K_GRAM + 1)):
            g = " ".join(words[j:j + K_GRAM])
            if g not in grams:
                grams[g] = (side, ts, i)
                continue
            f_side, f_ts, f_line = grams[g]
            if f_side == side or g in seen:
                continue
            seen.add(g)
            if ts == f_ts:
                events.append({"gram": g[:80], "from": f_side, "to": side,
                               "concurrent": True, "first_ts": f_ts, "used_ts": ts,
                               "source_line": f_line, "cited": False})
                continue
            cited = False
            for (l1, l2) in ledgers[side]["traj_ranges"].get(f_side, []):
                if l1 <= f_line <= l2:
                    cited = True
                    break
            events.append({"gram": g[:80], "from": f_side, "to": side,
                           "concurrent": False, "first_ts": f_ts, "used_ts": ts,
                           "source_line": f_line, "cited": cited})
    events.sort(key=lambda e: (e["used_ts"], e["gram"]))
    counts = {"a_to_b": 0, "b_to_a": 0, "cited_a_to_b": 0, "cited_b_to_a": 0, "concurrent": 0}
    for e in events:
        if e["concurrent"]:
            counts["concurrent"] += 1
            continue
        k = "%s_to_%s" % (e["from"], e["to"])
        counts[k] = counts.get(k, 0) + 1
        if e["cited"]:
            counts["cited_" + k] = counts.get("cited_" + k, 0) + 1
    return {"counts": counts, "events": events[:30], "event_total": len(events)}


def surface_stats(stats, repo, tag):
    a, b = set(stats["a"]["observed_paths"]), set(stats["b"]["observed_paths"])
    only_a, only_b, both = sorted(a - b), sorted(b - a), sorted(a & b)
    ok, tree = git(repo, "ls-tree", "-r", "--name-only", tag + "^{commit}")
    untouched = []
    if ok:
        for f in sorted(t for t in tree.splitlines() if t.strip()):
            touched = any(t == f or t.endswith("/" + f) for t in (a | b))
            if not touched:
                untouched.append(f)
    return {"only_a_count": len(only_a), "only_b_count": len(only_b), "both_count": len(both),
            "only_a": only_a[:60], "only_b": only_b[:60], "both": both[:60],
            "untouched_repo_files_count": len(untouched), "untouched_repo_files": untouched[:60]}


def protocol_stats(repo, tag, xdir, pin_dir=None, fs_avail=True):
    forks = []
    ok, text = git(repo, "show", tag + ":forks.json")
    if ok and text:
        try:
            doc = json.loads(text)
            items = doc.get("forks") if isinstance(doc, dict) else doc
            if isinstance(items, list):
                items = [f for f in items if isinstance(f, dict) and f.get("id")]
                items.sort(key=lambda f: f.get("priority", 999))
                forks = [str(f["id"]) for f in items]
        except Exception:
            pass
    dirs, dir_src, pins, avails = {}, {}, {}, {}
    for side in ("a", "b"):
        name = "dir-%s.json" % side
        pin_name = "%s.%s" % (tag, name)
        pinp = os.path.join(pin_dir, pin_name) if pin_dir else None
        absentp = os.path.join(pin_dir, pin_name + ".absent") if pin_dir else None
        d, av = None, None
        if pinp and os.path.exists(pinp):
            try:
                with open(pinp, "rb") as f:
                    raw = f.read()
                d = json.loads(raw.decode("utf-8", "replace"))
                dir_src[side] = "pin:%s" % pinp
                av = meta_or_declared(pin_dir, pin_name, raw)
            except Exception:
                d, av = None, None
        if d is None and not (absentp and os.path.exists(absentp)):
            p = os.path.join(xdir, name)
            if os.path.exists(p):
                try:
                    with open(p, "rb") as f:
                        raw = f.read()
                    d = json.loads(raw.decode("utf-8", "replace"))
                    av = live_avail(p, raw, fs_avail)
                    if pinp:
                        pins[pin_name] = (raw, av)
                        dir_src[side] = "pin:%s" % pinp
                    else:
                        dir_src[side] = "file:%s" % p
                except Exception:
                    d, av = None, None
            elif pinp and not os.path.exists(pinp):
                pin_write_absent(pin_dir, pin_name)
        if isinstance(d, dict):
            dirs[side] = {str(x.get("fork_id")): str(x.get("choice", ""))
                          for x in (d.get("axes") or []) if isinstance(x, dict)}
        else:
            dirs[side] = {}
            av = None
        dir_src.setdefault(side, "missing")
        avails["protocol.dirs.%s" % side] = avail_entry(dir_src[side], av)
    # divergence.json = P0.2 冻结证据:只取可得时间(meta 侧车钉版,不 pin 字节)
    div_name = "%s.divergence.json" % tag
    divp = os.path.join(xdir, "divergence.json")
    div_ref, div_av = "missing", None
    div_meta = meta_read(pin_dir, div_name)
    if div_meta is not None:
        div_ref = "file:%s" % divp
        div_av = {"mtime": div_meta.get("mtime"), "declared_at": div_meta.get("declared_at"),
                  "available_at": div_meta.get("available_at"),
                  "basis": div_meta.get("basis", "unknown")}
    elif not (pin_dir and os.path.exists(os.path.join(pin_dir, div_name + ".absent"))):
        if os.path.exists(divp):
            try:
                with open(divp, "rb") as f:
                    raw = f.read()
                div_ref = "file:%s" % divp
                div_av = live_avail(divp, raw, fs_avail)
                pin_write_meta(pin_dir, div_name, div_av)
            except Exception:
                div_ref, div_av = "missing", None
        else:
            pin_write_absent(pin_dir, div_name)
    avails["protocol.divergence"] = avail_entry(div_ref, div_av)
    divergence, differing = {}, 0
    for fid in forks:
        ca, cb = dirs["a"].get(fid), dirs["b"].get(fid)
        differ = bool(ca and cb and ca != cb)
        divergence[fid] = {"a": ca, "b": cb, "differ": differ}
        if differ:
            differing += 1
    return ({"present": bool(forks or dirs["a"] or dirs["b"]), "forks": forks,
             "divergence": divergence, "differing_count": differing,
             "sources": {"forks": ("tag:%s" % tag) if forks else "missing",
                         "dirs": dir_src}}, pins, avails)


def render_md(res):
    av = res.get("availability") or {}
    L = ["# traj_stats %s" % res["meta"]["tag"],
         "commit: %s  (%s)  cut_epoch: %d" % (res["meta"]["commit"], res["meta"]["commit_time"],
                                              res["meta"]["cut_epoch"]),
         "availability: tag_commit=%s max_source=%s cut=%s unknown=%s"
         % (av.get("tag_commit_epoch"), av.get("max_source_available_at"), av.get("cut_epoch"),
            ",".join(av.get("unknown") or []) or "-"), ""]
    for s in ("a", "b"):
        v = res["volume"][s]
        L.append("volume[%s]: lines<=cut=%d cut_last_line=%s assistant=%d tool_results=%d tokens=%s uncached=%s"
                 % (s, v["lines_leq_cut"], v["cut_last_line"], v["assistant_texts"],
                    v["tool_results"], json.dumps(v["tokens"], ensure_ascii=False),
                       json.dumps(v["uncached"])))
        p = res["pacing"][s]
        L.append("pacing[%s]: median=%ss p90=%ss p99=%ss max=%ss silences>600s=%d"
                 % (s, p["gaps"]["median_s"], p["gaps"]["p90_s"], p["gaps"]["p99_s"],
                    p["gaps"]["max_s"], p.get("silences_gt_600s_count", len(p["silences_gt_600s"]))))
    sf = res["surface"]
    L.append("surface: only_a=%d only_b=%d both=%d untouched_repo_files=%d"
             % (sf["only_a_count"], sf["only_b_count"], sf["both_count"],
                sf["untouched_repo_files_count"]))
    ad = res["text_overlap"]["counts"]
    L.append("text_overlap: a->b=%d (cited %d)  b->a=%d (cited %d)  concurrent=%d  [events listed=%d/%d] (文本重合计数,非语义采纳)"
             % (ad["a_to_b"], ad["cited_a_to_b"], ad["b_to_a"], ad["cited_b_to_a"], ad["concurrent"],
                len(res["text_overlap"]["events"]), res["text_overlap"]["event_total"]))
    for s in ("a", "b"):
        lg = res["ledger"][s]
        if lg.get("unresolved_count") is None:
            u = "unknown"
        elif lg["unresolved_count"] == len(lg["unresolved"]):
            u = "%d" % lg["unresolved_count"]
        else:
            u = "%d(sample %d)" % (lg["unresolved_count"], len(lg["unresolved"]))
        L.append("ledger[%s]: entries=%s kinds=%s unresolved=%s source=%s"
                 % (s, lg["entries"], json.dumps(lg["by_kind"], ensure_ascii=False), u, lg["source"]))
    pr = res["protocol"]
    if pr["present"]:
        L.append("protocol: forks=%d differing=%d/%d" % (len(pr["forks"]), pr["differing_count"], len(pr["forks"])))
    L.append("")
    L.append("note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。")
    return "\n".join(L) + "\n"


def write_ro(path, text):
    data = text.encode("utf-8")
    try:
        with open(path, "rb") as f:
            if f.read() == data:
                return "unchanged"
    except Exception:
        pass
    try:
        with open(path, "wb") as f:
            f.write(data)
    except PermissionError:
        os.chmod(path, 0o644)
        with open(path, "wb") as f:
            f.write(data)
    os.chmod(path, 0o444)
    return "written"


def gen(repo, xdir, tag, opts):
    ok, cut_s = git(repo, "log", "-1", "--format=%ct", tag + "^{commit}")
    if not ok or not cut_s.isdigit():
        print("traj_stats: cannot resolve tag %s in %s" % (tag, repo), file=sys.stderr)
        return 1
    tag_commit = int(cut_s)
    fs_avail = opts.get("fs_avail", True)
    _, csha = git(repo, "rev-parse", tag + "^{commit}")
    ctime = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tag_commit))
    paths, tsrc = {}, {}
    for side in ("a", "b"):
        p = opts.get("transcript_" + side)
        if not p:
            uu = ""
            try:
                with open(os.path.join(xdir, "session-%s.uuid" % side), encoding="utf-8") as f:
                    uu = f.read().strip()
            except Exception:
                pass
            if uu:
                p = os.path.join(opts["chats_root"], "-root-wt-%s" % side, "chats", uu + ".jsonl")
        paths[side] = p
        tsrc[side] = "file" if (p and os.path.exists(p)) else "missing"
    pin_dir = opts.get("pin_dir") or os.path.join(opts["out"], "pin")
    ledgers, ledger_src, ledger_av = {}, {}, {}
    for s in ("a", "b"):
        lines, src, pend, av = load_ledger(repo, tag, xdir, opts["wt_root"], s, pin_dir, fs_avail)
        if pend is not None:
            name, raw, m = pend
            pp = pin_write(pin_dir, name, raw, m)
            if pp is not None:
                src = "pin:%s" % pp
        ledgers[s] = ledger_stats(lines)
        ledger_src[s] = src
        ledger_av[s] = av
    protocol, pins, proto_av = protocol_stats(repo, tag, xdir, pin_dir, fs_avail)
    for pname, (praw, pav) in pins.items():
        pin_write(pin_dir, pname, praw, pav)
    avails = {}
    for s in ("a", "b"):
        av = ledger_av[s]
        if av is None:
            avails["ledger.%s" % s] = avail_entry("missing", None)
        else:
            if av.get("basis") == "commit":
                av = dict(av, available_at=tag_commit)
            avails["ledger.%s" % s] = avail_entry(ledger_src[s], av)
    avails.update(proto_av)
    fs_forks = protocol["sources"]["forks"]
    avails["protocol.forks"] = avail_entry(
        fs_forks, {"mtime": None, "declared_at": None, "available_at": tag_commit,
                   "basis": "commit"} if fs_forks != "missing" else None)
    known = [e["available_at"] for e in avails.values() if e["available_at"] is not None]
    max_src = max(known) if known else None
    cut = max(tag_commit, max_src) if max_src is not None else tag_commit
    unknown = sorted(k for k, e in avails.items()
                     if e["available_at"] is None and e["ref"] != "missing")
    stats = {s: side_stats(paths[s], cut) for s in ("a", "b")}
    ledger_out = {}
    for s in ("a", "b"):
        if ledger_src[s] == "missing":
            ledger_out[s] = {"entries": None, "by_kind": {}, "unresolved": [],
                             "unresolved_count": None, "source": "missing"}
        else:
            lg = ledgers[s]
            ledger_out[s] = {"entries": lg["entries"], "by_kind": lg["by_kind"],
                             "unresolved": lg["unresolved"],
                             "unresolved_count": lg["unresolved_count"],
                             "source": ledger_src[s]}
    res = {
        "meta": {"schema": "traj-stats/4", "usage_semantics": "per_call",
                 "tag": tag, "commit": csha, "commit_time": ctime, "cut_epoch": cut,
                 "transcripts": {s: {"path": paths[s],
                                     "sha256_leq_cut": stats[s]["sha256_leq_cut"],
                                     "lines_leq_cut": stats[s]["lines_leq_cut"],
                                     "cut_last_line": stats[s]["cut_last_line"],
                                     "source": tsrc[s]} for s in ("a", "b")},
                 "method": "mechanical; no network; no LLM; no task priors; content is a pure function of the pinned inputs (tag commit; transcript lines <= cut; ledger/protocol sources pinned under pin/ with .meta availability sidecars, or recorded as missing; cut_epoch = max(tag commit time, availability of all sources))"},
        "availability": {"policy": "cut_epoch = max(tag_commit_epoch, available_at of every present source)",
                         "tag_commit_epoch": tag_commit, "max_source_available_at": max_src,
                         "cut_epoch": cut, "sources": avails, "unknown": unknown},
        "volume": {s: {k: v for k, v in stats[s].items() if k not in ("observed_paths", "_texts")} for s in ("a", "b")},
        "pacing": {s: {"first_ts": stats[s]["first_ts"], "last_ts": stats[s]["last_ts"],
                        "gaps": stats[s]["gaps"], "silences_gt_600s": stats[s]["silences_gt_600s"],
                        "silences_gt_600s_count": stats[s]["silences_gt_600s_count"]}
                   for s in ("a", "b")},
        "surface": surface_stats(stats, repo, tag),
        "text_overlap": text_overlap_stats(stats, ledgers),
        "ledger": ledger_out,
        "protocol": protocol,
    }
    outs = opts["out"]
    jpath = os.path.join(outs, tag + ".json")
    mpath = os.path.join(outs, tag + ".md")
    jw = write_ro(jpath, json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    mw = write_ro(mpath, render_md(res))
    print(json.dumps({"tag": tag, "json": jpath, "json_write": jw,
                      "md": mpath, "md_write": mw}, ensure_ascii=False))
    return 0


def auto(repo, xdir, opts):
    ok, tags = git(repo, "tag", "-l", "ckpt-m*")
    n = 0
    if ok:
        for tag in sorted(t for t in tags.splitlines() if t.strip()):
            if os.path.exists(os.path.join(opts["out"], tag + ".json")):
                continue
            gen(repo, xdir, tag, opts)
            n += 1
    print(json.dumps({"generated": n, "out": opts["out"]}, ensure_ascii=False))
    return 0


def main():
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[0] not in ("gen", "auto"):
        print("usage: traj_stats.py gen|auto <repo> <xdir> [tag] [--chats-root D] "
              "[--transcript-a P] [--transcript-b P] [--wt-root D] [--out D] "
              "[--no-fs-avail]", file=sys.stderr)
        return 2
    cmd = argv[0]
    pos = []
    opts = {"chats_root": os.environ.get("WT_CHATS_ROOT", "/root/.qwen/projects"),
            "wt_root": os.environ.get("WT_WT_ROOT", "/root/wt"), "out": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--chats-root" and i + 1 < len(argv):
            opts["chats_root"] = argv[i + 1]; i += 2
        elif a == "--transcript-a" and i + 1 < len(argv):
            opts["transcript_a"] = argv[i + 1]; i += 2
        elif a == "--transcript-b" and i + 1 < len(argv):
            opts["transcript_b"] = argv[i + 1]; i += 2
        elif a == "--wt-root" and i + 1 < len(argv):
            opts["wt_root"] = argv[i + 1]; i += 2
        elif a == "--out" and i + 1 < len(argv):
            opts["out"] = argv[i + 1]; i += 2
        elif a == "--no-fs-avail":
            opts["fs_avail"] = False; i += 1
        else:
            pos.append(a); i += 1
    if len(pos) < 2:
        print("traj_stats: need <repo> <xdir>", file=sys.stderr)
        return 2
    repo, xdir = pos[0], pos[1]
    if opts["out"] is None:
        opts["out"] = os.path.join(xdir, "stats")
    try:
        os.makedirs(opts["out"], exist_ok=True)
    except Exception as e:
        print("traj_stats: cannot create out dir: %r" % e, file=sys.stderr)
        return 1
    if cmd == "gen":
        if len(pos) < 3:
            print("traj_stats: gen needs <tag>", file=sys.stderr)
            return 2
        return gen(repo, xdir, pos[2], opts)
    return auto(repo, xdir, opts)


if __name__ == "__main__":
    sys.exit(main())
