#!/usr/bin/env python3
"""traj_index.py — idempotent, incremental indexer for qwen-code session JSONL.

One index row per complete transcript line:
  v, sid, L, ts, type, sub, tool, arg, rsize, usage{in,cache,out,think},
  thought, text_len, anchors[], line_sha

Properties (tested in tests_traj.py):
  - append-only, byte-deterministic output; re-runs change nothing;
  - incremental via a checkpoint (offset, prefix_sha, idx_lines);
    a changed prefix triggers a full rebuild;
  - a partial trailing line is held pending, never indexed;
  - anchors = C-ids, hex shas, paths (capped, sorted) for greppable retrieval.
CLI: traj_index.py build <transcript> <index> [--state S]
"""
import hashlib, json, os, re, sys

V = 1
C_RE = re.compile(r"\bC\d{1,3}\b")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
PATH_RE = re.compile(r"(?:/[\w.\-]+){2,}")
ARG_KEYS = ("command", "file_path", "description", "content", "path", "pattern", "url")
ANCHOR_CAP = 80


def _arg_of(args):
    if isinstance(args, dict):
        for k in ARG_KEYS:
            v = args.get(k)
            if isinstance(v, str) and v:
                return v[:200]
        try:
            return json.dumps(args, ensure_ascii=False)[:200]
        except Exception:
            return str(args)[:200]
    return (str(args) if args is not None else "")[:200]


def _anchors(line):
    a = set(C_RE.findall(line))
    a |= set(SHA_RE.findall(line))
    a |= set(PATH_RE.findall(line))
    return sorted(a)[:ANCHOR_CAP]


def parse_line(raw, sid_fallback, L):
    line = raw.decode("utf-8", "replace")
    d = json.loads(line)
    ts = d.get("timestamp") or ""
    typ = d.get("type") or ""
    sid = d.get("sessionId") or sid_fallback or ""
    sub = tool = None
    arg = None
    usage = None
    thought = False
    tlen = 0
    msg = d.get("message")
    if typ == "system":
        ev = ((d.get("systemPayload") or {}).get("uiEvent") or {})
        name = ev.get("event.name") or ""
        if name.startswith("qwen-code."):
            sub = name.split(".", 1)[1]
        if sub == "tool_call":
            tool = ev.get("function_name")
            arg = _arg_of(ev.get("function_args"))
        elif sub == "api_response":
            usage = {
                "in": ev.get("input_token_count", 0),
                "cache": ev.get("cached_content_token_count", 0),
                "out": ev.get("output_token_count", 0),
                "think": ev.get("thoughts_token_count", 0),
            }
    elif typ == "assistant" and isinstance(msg, dict):
        calls = []
        for p in (msg.get("parts") or []):
            if not isinstance(p, dict):
                continue
            fc = p.get("functionCall")
            if isinstance(fc, dict):
                calls.append(str(fc.get("name") or "?"))
                if arg is None and fc.get("args") is not None:
                    arg = _arg_of(fc.get("args"))
            if p.get("thought"):
                thought = True
            elif isinstance(p.get("text"), str):
                tlen += len(p["text"])
        tool = ",".join(calls) or None
    elif typ == "user" and isinstance(msg, dict):
        for p in (msg.get("parts") or []):
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                tlen += len(p["text"])
    return {
        "v": V, "sid": sid, "L": L, "ts": ts, "type": typ, "sub": sub,
        "tool": tool, "arg": arg,
        "rsize": len(raw) if typ == "tool_result" else 0,
        "usage": usage, "thought": thought, "text_len": tlen,
        "anchors": _anchors(line),
        "line_sha": hashlib.sha256(raw).hexdigest()[:16],
    }


def _parse_range(data, start, end, L0, sid):
    """Parse complete lines in data[start:end] (end must be a line boundary)."""
    rows, bad, L = [], 0, L0
    lines = data[start:end].split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    for raw in lines:
        if raw.strip() == b"":
            L += 1
            continue
        try:
            rows.append(parse_line(raw, sid, L))
        except Exception:
            bad += 1
        L += 1
    return rows, L, bad


def parse_all(transcript):
    """Full in-memory parse (reader path; no files written)."""
    data = open(transcript, "rb").read()
    cut = data.rfind(b"\n") + 1
    rows, L, bad = _parse_range(data, 0, cut, 0, "")
    return rows, {"bytes": len(data), "complete_lines": L, "bad_lines": bad,
                  "pending_bytes": len(data) - cut}


def build(transcript, index, state=None):
    data = open(transcript, "rb").read()
    cut = data.rfind(b"\n") + 1
    st = None
    if state and os.path.exists(state):
        try:
            st = json.load(open(state))
        except Exception:
            st = None
    incremental = False
    off = 0
    idx_lines = 0
    if (st and st.get("v") == V and isinstance(st.get("offset"), int)
            and isinstance(st.get("prefix_sha"), str)
            and os.path.exists(index)):
        off = st["offset"]
        idx_lines = st.get("idx_lines", -1)
        if 0 <= off <= cut:
            if hashlib.sha256(data[:off]).hexdigest() == st["prefix_sha"]:
                with open(index, "rb") as f:
                    have = sum(1 for _ in f)
                if have == idx_lines:
                    incremental = True
    if not incremental:
        off, idx_lines = 0, 0
    rows, newL, bad = _parse_range(data, off, cut, idx_lines, "")
    mode = "ab" if incremental else "wb"
    with open(index, mode) as f:
        for r in rows:
            f.write((json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n").encode())
    if state:
        json.dump({"v": V, "offset": cut,
                   "prefix_sha": hashlib.sha256(data[:cut]).hexdigest(),
                   "idx_lines": newL}, open(state, "w"))
    return {"rows": newL, "new_rows": len(rows), "bytes": len(data),
            "complete_lines": newL, "bad_lines": bad,
            "pending_bytes": len(data) - cut, "rebuilt": not incremental}


def main(argv):
    if not argv or argv[0] != "build" or len(argv) < 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    transcript, index = argv[1], argv[2]
    state = None
    if "--state" in argv:
        state = argv[argv.index("--state") + 1]
    stats = build(transcript, index, state)
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
