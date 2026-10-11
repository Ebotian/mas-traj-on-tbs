#!/usr/bin/env python3
"""traj.py — sealed, index-first trajectory reader for the dual-agent runs.

Reading discipline (enforced here, not by convention):
  - --self  (own transcript): opens at Round 3 (x/ready-<actor>.round >= 3);
  - --peer  (peer transcript): opens only after M1 exists (git tag ckpt-m1)
    and reads ONLY the published snapshot x/traj-<peer>.upto-cut.jsonl,
    which the post-commit hook maintains up to the peer's last commit.
  - every command's stdout is hard-capped (default 16 KB, ceiling 64 KB);
    narrow the query instead of dumping.
  - audit-seal scans an actor's own tool calls for reads of the peer's RAW
    transcript: content reads are violations (exit 1), stat/ls are reported
    as metadata touches.

Commands:
  summary | find <regex> | steps [--tool T] [--type K] [--since TS] [--until TS]
  | anchors [C-id] | show --lines A:B [--max B] | digest [--lines A:B |
  --since-commit SHA] [--max-per-step N] | lsha L742 [L740-L745] | since-commit SHA
  | audit-seal

Flags anywhere: --xdir --repo --actor --peer --transcript (--peer uses the
snapshot; --transcript overrides the self path).  Exit: 0 ok, 1 audit hit,
2 usage/io, 3 gate closed.
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import traj_index

DEFAULT_MAX = 16384
HARD_MAX = 65536
LINE_RENDER = 2000


def die(msg, rc):
    sys.stderr.write("traj: %s\n" % msg)
    sys.exit(rc)


class Out:
    def __init__(self, maxb):
        self.maxb = maxb
        self.buf = []
        self.n = 0
        self.capped = False
        self.lines = 0

    def line(self, s):
        b = len(s.encode()) + 1
        if self.n + b > self.maxb:
            self.capped = True
            return False
        self.buf.append(s)
        self.n += b
        self.lines += 1
        return True

    def flush(self):
        if self.buf:
            sys.stdout.write("\n".join(self.buf) + "\n")
        if self.capped:
            sys.stdout.write("[output capped at %d bytes; narrow the query]\n" % self.maxb)


def parse_argv(argv):
    val = {"--xdir", "--repo", "--actor", "--peer", "--transcript", "--max",
           "--limit", "--since", "--until", "--lines", "--max-per-step",
           "--since-commit"}
    boolean = {"--thoughts"}
    opts, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in val:
            if i + 1 >= len(argv):
                die("missing value for %s" % a, 2)
            opts[a[2:].replace("-", "_")] = argv[i + 1]
            i += 2
        elif a in boolean:
            opts[a[2:].replace("-", "_")] = True
            i += 1
        else:
            pos.append(a)
            i += 1
    return opts, pos


def resolve_actor(opts):
    a = opts.get("actor")
    if a:
        return a
    base = os.path.basename(os.getcwd())
    return base if base in ("a", "b") else None


def self_target(actor, xdir, opts):
    if opts.get("transcript"):
        return opts["transcript"]
    uuf = os.path.join(xdir, "session-%s.uuid" % actor)
    try:
        uu = open(uuf).read().strip()
    except OSError:
        die("cannot resolve own transcript: %s missing (pass --transcript)" % uuf, 3)
    return "/root/.qwen/projects/-root-wt-%s/chats/%s.jsonl" % (actor, uu)


def check_self_gate(actor, xdir):
    f = os.path.join(xdir, "ready-%s.round" % actor)
    try:
        n = int(open(f).read().strip())
    except Exception:
        return "self reads open once Round 2 is published (self-review round); %s missing" % f
    if n < 2:
        return "self reads open once Round 2 is published (ready-%s.round = %d < 2)" % (actor, n)
    return None


def check_peer_gate(peer, xdir, repo):
    try:
        r = subprocess.run(["git", "-C", repo, "tag", "-l", "ckpt-m1"],
                           capture_output=True, text=True, timeout=20)
    except Exception as e:
        return None, "git unavailable for %s: %r" % (repo, e)
    if "ckpt-m1" not in r.stdout.split():
        return None, "peer trajectory sealed until M1 (tag ckpt-m1 missing in %s)" % repo
    snap = os.path.join(xdir, "traj-%s.upto-cut.jsonl" % peer)
    if not os.path.exists(snap) or os.path.getsize(snap) == 0:
        return None, "no published snapshot for peer %s yet (%s)" % (peer, snap)
    return snap, None


def load_rows(target):
    if not os.path.exists(target):
        die("no such transcript: %s" % target, 2)
    rows, stats = traj_index.parse_all(target)
    return rows, stats


def raw_lines(target):
    data = open(target, "rb").read()
    cut = data.rfind(b"\n") + 1
    lines = data[:cut].split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    return lines


def parse_range(s, n):
    if not s:
        return 0, n - 1
    parts = re.split(r"[:,-]", s)
    a = int(parts[0]) if parts[0] else 0
    b = int(parts[1]) if len(parts) > 1 and parts[1] else n - 1
    return max(0, a), min(b, n - 1)


def git_iso(repo, sha):
    r = subprocess.run(["git", "-C", repo, "show", "-s", "--format=%cI", sha],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        die("git show failed for %s: %s" % (sha, r.stderr.strip()), 2)
    return r.stdout.strip()[:19]


def render_row(r, per=160):
    seg = r.get("arg") or " ".join(r.get("anchors") or [])
    return "L%d %s/%s: %s" % (r["L"], r["type"], r.get("tool") or r.get("sub") or "-",
                              seg[:per])


def cmd_summary(rows, stats, out):
    out.line("rows=%d bytes=%d pending=%d" % (stats["complete_lines"], stats["bytes"],
                                              stats["pending_bytes"]))
    if rows:
        out.line("time=%s..%s sid=%s" % (rows[0]["ts"], rows[-1]["ts"], rows[0]["sid"]))
    kinds = {}
    for r in rows:
        kinds[r["type"]] = kinds.get(r["type"], 0) + 1
    out.line("types: " + " ".join("%s=%d" % (k, v) for k, v in sorted(kinds.items())))
    tin = tc = tout = tt = calls = 0
    for r in rows:
        u = r.get("usage")
        if u:
            calls += 1
            tin += u.get("in", 0)
            tc += u.get("cache", 0)
            tout += u.get("out", 0)
            tt += u.get("think", 0)
    out.line("usage: in=%s cache=%s out=%s think=%s calls=%d"
             % (format(tin, ","), format(tc, ","), format(tout, ","),
                format(tt, ","), calls))


def cmd_find(rows, pattern, out, limit=None):
    pat = re.compile(pattern)
    hit = 0
    for r in rows:
        hay = " ".join(filter(None, [r.get("arg"), r.get("tool"), r.get("sub"),
                                     " ".join(r.get("anchors") or [])]))
        if pat.search(hay):
            if not out.line(render_row(r)):
                break
            hit += 1
            if limit and hit >= limit:
                break
    if hit == 0:
        out.line("(no matches)")


def cmd_steps(rows, opts, out):
    limit = int(opts.get("limit") or 0)
    n = 0
    for r in rows:
        if opts.get("tool") and opts["tool"] not in (r.get("tool") or ""):
            continue
        if opts.get("type") and opts["type"] != r["type"]:
            continue
        if opts.get("since") and r["ts"] < opts["since"]:
            continue
        if opts.get("until") and r["ts"] > opts["until"]:
            continue
        if not out.line(render_row(r)):
            break
        n += 1
        if limit and n >= limit:
            break
    if n == 0:
        out.line("(no steps)")


def cmd_anchors(rows, cid, out):
    if cid:
        ls = [r["L"] for r in rows if cid in (r.get("anchors") or [])]
        out.line("%s  %s" % (cid, " ".join("L%d" % x for x in ls) or "(none)"))
        return
    cnt = {}
    for r in rows:
        for a in r.get("anchors") or []:
            cnt[a] = cnt.get(a, 0) + 1
    for a, c in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:40]:
        out.line("%s  %d" % (a, c))


def cmd_lsha(rows, anchors, out):
    """Print line shas for anchors like L742 or L740-L745 (capped at 50/arg)."""
    for a in anchors:
        m = re.match(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", a)
        if not m:
            out.line("(bad anchor %s)" % a)
            continue
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        for L in range(lo, min(hi, lo + 49) + 1):
            row = next((r for r in rows if r["L"] == L), None)
            out.line("L%d %s" % (L, row["line_sha"] if row else "(no line)"))


def cmd_show(target, opts, out):
    lines = raw_lines(target)
    a, b = parse_range(opts.get("lines"), len(lines))
    for i in range(a, b + 1):
        s = lines[i].decode("utf-8", "replace")
        if len(s) > LINE_RENDER:
            s = s[:LINE_RENDER] + "…"
        if not out.line("L%d %s" % (i, s)):
            break


def cmd_digest(target, rows, opts, out):
    if opts.get("since_commit"):
        cut = git_iso(opts.get("repo") or "/root/wt/repo", opts["since_commit"])
        rows = [r for r in rows if r["ts"] >= cut]
    elif opts.get("lines"):
        lines = raw_lines(target)
        a, b = parse_range(opts.get("lines"), len(lines))
        rows = [r for r in rows if a <= r["L"] <= b]
    per = int(opts.get("max_per_step") or 200)
    for r in rows:
        t = r["ts"][11:19] if len(r["ts"]) >= 19 else "??:??:??"
        if r["type"] == "tool_result":
            seg = "result %dB" % r["rsize"]
        elif r.get("arg"):
            seg = "%s: %s" % (r.get("tool") or r.get("sub") or r["type"], r["arg"][:per])
        elif r.get("sub"):
            seg = r["sub"]
        elif r.get("thought"):
            seg = "thought"
        else:
            seg = r["type"]
        if not out.line("L%d %s %s" % (r["L"], t, seg)):
            break


def cmd_since_commit(rows, opts, out):
    cut = git_iso(opts.get("repo") or "/root/wt/repo", opts["since_commit"])
    after = [r for r in rows if r["ts"] >= cut]
    out.line("cut=%s rows_after=%d first=L%s" % (
        cut, len(after),
        ("%d %s" % (after[0]["L"], after[0]["ts"])) if after else "(none)"))


CONTENT_VERBS = {"cat", "head", "tail", "tac", "sed", "awk", "grep", "less", "more",
                 "wc", "md5sum", "sha1sum", "sha256sum", "sha512sum", "strings",
                 "od", "xxd", "base64", "cut", "sort", "uniq", "cp", "tar", "zip",
                 "dd", "python", "python3", "node", "perl", "rsync"}
META_VERBS = {"stat", "ls", "find", "test", "du", "file"}


def audit_blobs(path):
    """Yield (L, ts, command-blob) for every tool invocation in the transcript."""
    data = open(path, "rb").read()
    cut = data.rfind(b"\n") + 1
    lines = data[:cut].split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    L = 0
    for raw in lines:
        if raw.strip() == b"":
            L += 1
            continue
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            L += 1
            continue
        ts = d.get("timestamp") or ""
        blobs = []

        def walk(o):
            if isinstance(o, dict):
                fc = o.get("functionCall")
                if isinstance(fc, dict) and isinstance(fc.get("args"), dict):
                    blobs.append(json.dumps(fc["args"], ensure_ascii=False))
                fa = o.get("function_args")
                if isinstance(fa, (dict, list)):
                    blobs.append(json.dumps(fa, ensure_ascii=False))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(d)
        for b in blobs:
            yield L, ts, b
        L += 1


def cmd_audit_seal(opts, out):
    actor = opts.get("actor")
    peer = opts.get("peer")
    if not actor or not peer:
        die("audit-seal needs --actor <self> and --peer <peer>", 2)
    target = opts.get("transcript")
    if not target:
        xdir = opts.get("xdir") or os.environ.get("WT_X") or "/root/wt/x"
        target = self_target(actor, xdir, opts)
    patterns = ["/root/.qwen/projects/-root-wt-%s" % peer,
                "-root-wt-%s/home/.qwen" % peer]
    n = v = m = x = 0
    for L, ts, blob in audit_blobs(target):
        n += 1
        for seg in re.split(r"[;|&\n]+", blob):
            if not any(p in seg for p in patterns):
                continue
            toks = set(re.findall(r"[A-Za-z0-9_./-]+", seg))
            if toks & CONTENT_VERBS:
                v += 1
                out.line("L%d %s VIOLATION content-read of peer-%s: %s"
                         % (L, ts[11:19], peer, seg.strip()[:140]))
            elif toks & META_VERBS:
                m += 1
                out.line("L%d %s metadata touch of peer-%s: %s"
                         % (L, ts[11:19], peer, seg.strip()[:140]))
            else:
                x += 1
                out.line("L%d %s mention of peer-%s path: %s"
                         % (L, ts[11:19], peer, seg.strip()[:140]))
    out.line("audit-seal %s vs %s: %d rows, %d violations, %d metadata touches, %d mentions — %s"
             % (actor, peer, n, v, m, x, "CLEAN" if v == 0 else "VIOLATIONS FOUND"))
    return 1 if v else 0


def main(argv):
    opts, pos = parse_argv(argv)
    if not pos:
        die("usage: traj.py [flags] <command> [args]", 2)
    cmd = pos[0]
    xdir = opts.get("xdir") or os.environ.get("WT_X") or "/root/wt/x"
    repo = opts.get("repo") or os.environ.get("WT_REPO") or "/root/wt/repo"
    maxb = min(int(opts.get("max") or DEFAULT_MAX), HARD_MAX)

    if cmd == "audit-seal":
        out = Out(maxb)
        rc = cmd_audit_seal(opts, out)
        out.flush()
        return rc

    peer = opts.get("peer")
    if peer:
        target, err = check_peer_gate(peer, xdir, repo)
        if err:
            die(err, 3)
    else:
        actor = resolve_actor(opts)
        if not actor:
            die("cannot tell the actor: pass --actor a|b (cwd is not a worktree)", 3)
        err = check_self_gate(actor, xdir)
        if err:
            die(err, 3)
        target = self_target(actor, xdir, opts)

    out = Out(maxb)
    if cmd == "show":
        cmd_show(target, opts, out)
        out.flush()
        return 0
    rows, stats = load_rows(target)
    if cmd == "summary":
        cmd_summary(rows, stats, out)
    elif cmd == "find":
        if len(pos) < 2:
            die("find needs a regex", 2)
        cmd_find(rows, pos[1], out, int(opts.get("limit") or 0) or None)
    elif cmd == "steps":
        cmd_steps(rows, opts, out)
    elif cmd == "anchors":
        cmd_anchors(rows, pos[1] if len(pos) > 1 else None, out)
    elif cmd == "lsha":
        cmd_lsha(rows, pos[1:], out)
    elif cmd == "digest":
        cmd_digest(target, rows, opts, out)
    elif cmd == "since-commit":
        if len(pos) < 2:
            die("since-commit needs a sha", 2)
        opts["since_commit"] = pos[1]
        cmd_since_commit(rows, opts, out)
    else:
        die("unknown command: %s" % cmd, 2)
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
