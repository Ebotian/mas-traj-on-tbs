#!/usr/bin/env python3
"""Decode a shared ChatGPT conversation into plain text.

Why this exists: `web_fetch` refuses these pages because the HTML exceeds its
10 MB limit. The conversation is not in the markup as text — it is a React Router
turbo-stream payload, so it has to be decoded.

Payload format, verified on a 2026-09-30 capture of a 4011-node conversation:
  window.__reactRouterContext.streamController.enqueue("<js string literal>")
The literal decodes to a JSON array of 148184 values. That array is flat:
  - a dict entry is an object; each key is "_<i>" where arr[<i>] is the key string
  - every dict value and every list item is an INDEX into the same array
    (all 427228 dict values are ints; the single non-int list item is the "P"
    promise marker that the second enqueue resolves)
  - -5 is null; keys are deduplicated, so each appears exactly once
  - the conversation lives at
    loaderData["routes/share.$shareId.($)"].serverResponse.data.mapping

Usage:
  decode_share.py <url-or-html-file> <outdir>

Writes into <outdir>: mapping.json, transcript.md, user_turns.md, outline.md.
Nothing else is kept; the 11 MB HTML and the 10 MB flat array are disposable and
regenerable from the link for as long as the link lives.

Caveat: tool outputs are truncated to exactly 20000 characters inside the share
payload. Assistant text and code are not truncated. So the transcript is lossless
with respect to the export, not with respect to the original conversation.
"""
import json
import re
import sys
import datetime
from pathlib import Path

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
NULL_HINT = -5


def obtain_html(src: str) -> str:
    p = Path(src)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8", errors="replace")
    import subprocess
    out = p if p.suffix == ".html" else Path("/tmp/chatgpt_share.html")
    r = subprocess.run(["curl", "-sL", "--compressed", "-A", USER_AGENT,
                        "-o", str(out), "-w", "%{http_code} %{size_download}", src],
                       capture_output=True, text=True)
    print(f"fetch: http/size = {r.stdout.strip()} -> {out}")
    if r.returncode != 0:
        raise SystemExit(f"curl failed: {r.stderr.strip()[:300]}")
    return out.read_text(encoding="utf-8", errors="replace")


def enqueue_payloads(html: str):
    """Pull each streamController.enqueue("<literal>") and decode the JS string."""
    out = []
    for m in re.finditer(r"streamController\.enqueue\(", html):
        i = m.end()
        if html[i] != '"':
            raise SystemExit(f"expected a string literal at {i}, got {html[i-20:i+20]!r}")
        i += 1
        buf = []
        while i < len(html):
            c = html[i]
            if c == "\\":
                buf.append(html[i:i + 2])
                i += 2
                continue
            if c == '"':
                break
            buf.append(c)
            i += 1
        out.append(json.loads('"' + "".join(buf) + '"'))
    if not out:
        raise SystemExit("no streamController.enqueue found — page layout changed?")
    return out


def decode(arr, i, memo):
    """arr is the flat value list; i is an index into it."""
    if not isinstance(i, int):
        return i
    if i == NULL_HINT:
        return None
    if i < 0:
        return f"<hint{i}>"
    if i in memo:
        return memo[i]
    v = arr[i]
    if isinstance(v, dict):
        o = {}
        memo[i] = o
        for k, val in v.items():
            o[arr[int(k[1:])]] = decode(arr, val, memo)
        return o
    if isinstance(v, list):
        o = []
        memo[i] = o
        for x in v:
            o.append(decode(arr, x, memo))
        return o
    memo[i] = v
    return v


def find_key(o, key, depth=0, limit=30):
    if depth > limit:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from find_key(v, key, depth + 1, limit)
    elif isinstance(o, list):
        for v in o[:8]:
            yield from find_key(v, key, depth + 1, limit)


def chain_order(mp):
    roots = [n for n, v in mp.items() if v.get("parent") in (None, "")]
    if len(roots) != 1:
        print(f"warning: {len(roots)} roots; following the first")
    out, cur, seen = [], roots[0], set()
    while cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        ch = mp[cur].get("children") or []
        cur = ch[0] if ch else None
    branches = [n for n, v in mp.items() if len(v.get("children") or []) > 1]
    print(f"nodes={len(mp)} chain={len(out)} roots={len(roots)} branch_points={len(branches)}")
    if len(out) != len(mp):
        print(f"warning: chain covers {len(out)} of {len(mp)} nodes; the rest are off-branch")
    return out


def text_of(m):
    """Extract text from a message. Six content shapes occur, verified by census:
      text                 (3598)  parts: [str]
      thoughts              (194)  thoughts: [{summary, content, chunks, finished}]
      code                  (108)  text, language
      reasoning_recap        (51)  content
      execution_output       (41)  text
      model_editable_context (18)  model_set_context
    Anything else falls back to the first non-empty string field, then to JSON, so
    a shape this script has never seen is preserved rather than dropped.
    """
    c = m.get("content")
    if not isinstance(c, dict):
        return "" if c is None else str(c)
    ct = c.get("content_type")
    if ct == "text":
        p = c.get("parts")
        return "\n".join(x for x in p if isinstance(x, str)) if isinstance(p, list) else ""
    if ct in ("code", "execution_output"):
        return c.get("text") or ""
    if ct == "reasoning_recap":
        return c.get("content") or ""
    if ct == "model_editable_context":
        return c.get("model_set_context") or ""
    if ct == "thoughts":
        out = []
        for th in c.get("thoughts") or []:
            if isinstance(th, str):
                out.append(th)
            elif isinstance(th, dict):
                chunks = th.get("chunks")
                ctxt = ("\n".join(x for x in chunks if isinstance(x, str))
                        if isinstance(chunks, list) else "")
                out.append("\n".join(x for x in (th.get("summary") or "",
                                                 th.get("content") or "", ctxt) if x))
        return "\n".join(out)
    for v in c.values():
        if isinstance(v, str) and v.strip():
            return v
    return json.dumps(c, ensure_ascii=False)


def stamp(t):
    if isinstance(t, (int, float)):
        return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%m-%d %H:%M")
    return "--"


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, outdir = sys.argv[1], Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    sys.setrecursionlimit(200000)

    html = obtain_html(src)
    payloads = enqueue_payloads(html)
    print(f"enqueue payloads: {len(payloads)} sizes={[len(p) for p in payloads]}")
    arr = json.loads(payloads[0])
    print(f"flat array: {len(arr)} values")
    del html

    root = decode(arr, 0, {})
    mapping = next(iter(find_key(root, "mapping")), None)
    if not isinstance(mapping, dict):
        raise SystemExit("mapping not found — payload layout changed?")
    (outdir / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    titles = list(find_key(root, "title"))[:1]
    order = chain_order(mapping)

    full = (outdir / "transcript.md").open("w", encoding="utf-8")
    users = (outdir / "user_turns.md").open("w", encoding="utf-8")
    outline = (outdir / "outline.md").open("w", encoding="utf-8")
    if titles:
        for fh in (full, users, outline):
            fh.write(f"conversation title: {titles[0]}\n")
    nu = na = 0
    truncated = 0
    for n in order:
        node = mapping[n]
        m = node.get("message")
        if not isinstance(m, dict):
            continue
        r = (m.get("author") or {}).get("role")
        ct = (m.get("content") or {}).get("content_type")
        t = text_of(m)
        if not t.strip():
            continue
        if len(t) == 20000:
            truncated += 1
        head = f"[{r}/{ct}] {stamp(m.get('create_time'))} node={n[:8]} len={len(t)}"
        full.write(f"\n\n===== {head} =====\n{t}\n")
        if r == "user":
            nu += 1
            users.write(f"\n\n--- USER #{nu}  {stamp(m.get('create_time'))}  len={len(t)} ---\n{t}\n")
            outline.write(f"\n### USER #{nu} {stamp(m.get('create_time'))} len={len(t)}\n{t[:300]}\n")
        elif r == "assistant" and ct in ("text", "code"):
            na += 1
            heads = [l for l in t.split("\n") if l.strip().startswith(("#", "=", "**"))][:14]
            outline.write(f"\n## ASSIST {stamp(m.get('create_time'))} len={len(t)}\n"
                          + "\n".join("    " + h[:150] for h in heads) + "\n")
    for fh in (full, users, outline):
        fh.close()
    print(f"user turns with text: {nu}   assistant text/code: {na}")
    print(f"messages of exactly 20000 chars (truncated by the export): {truncated}")
    print(f"wrote: {outdir}/mapping.json transcript.md user_turns.md outline.md")


if __name__ == "__main__":
    main()
