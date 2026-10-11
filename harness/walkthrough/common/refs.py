#!/usr/bin/env python3
"""refs.py — LaTeX-style evidence-reference ledger for the dual-agent runs.

The ledger `refs-<actor>.jsonl` is append-only, one pure-reference JSON per
line (no prose): {id, kind, ..., claim, r}.  Prose cites [E17]; this tool is
the "compiler": `check` resolves every reference against the sanctioned
surfaces (own transcript / peer snapshot / git / files / tables) and fails on
broken ones; `declared` unresolved entries are allowed but counted; `replay`
re-runs a kind=run entry; `biblio` prints the evidence map.

Kinds:
  traj     {who, anchor:"L742-L760", sha?}   resolve vs transcript(own, round>=3)
                                              or peer snapshot (sealed cut)
  commit   {sha}                              git cat-file -e <sha>^{commit}
  file     {path, sha256}                     exists + hash matches
  row      {file, match}                      regex match in file
  run      {cwd, cmd, expect}                 structural check; replay runs it
  unresolved {reason}                         allowed, counted as declared

Exit: 0 ok, 1 broken refs, 2 usage.
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import traj
import traj_index

ALLOWED_ROOTS = None  # reserved: restrict file refs later if needed


def die(msg, rc):
    sys.stderr.write("refs: %s\n" % msg)
    sys.exit(rc)


def parse_argv(argv):
    val = {"--actor", "--refs", "--xdir", "--repo", "--round", "--transcript"}
    opts, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in val:
            if i + 1 >= len(argv):
                die("missing value for %s" % a, 2)
            opts[a[2:].replace("-", "_")] = argv[i + 1]
            i += 2
        else:
            pos.append(a)
            i += 1
    return opts, pos


def load_ledger(path):
    """Returns (entries, broken) — broken carries parse-level defects."""
    entries, broken, seen = [], [], set()
    if not os.path.exists(path):
        return entries, broken
    for n, raw in enumerate(open(path, "r", encoding="utf-8", errors="replace"), 1):
        if not raw.strip():
            continue
        try:
            e = json.loads(raw)
        except Exception:
            broken.append({"id": "line%d" % n, "why": "malformed JSON on line %d" % n})
            continue
        eid = e.get("id") or "line%d" % n
        if eid in seen:
            broken.append({"id": eid, "why": "duplicate id %s" % eid})
            continue
        seen.add(eid)
        entries.append(e)
    return entries, broken


def anchor_range(a):
    m = re.fullmatch(r"L(\d+)(?:\s*-\s*L?(\d+))?", a or "")
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    return lo, hi


def resolve_traj(e, actor, opts, xdir):
    who = e.get("who")
    rng = anchor_range(e.get("anchor"))
    if rng is None:
        return "broken", "bad anchor format"
    lo, hi = rng
    if who == actor:
        rnd = opts.get("round")
        if rnd is not None and int(rnd) < 3:
            return "broken", "self trajectory opens at round 3 (this is round %s)" % rnd
        try:
            target = traj.self_target(actor, xdir, opts)
        except SystemExit:
            return "broken", "own transcript not resolvable (no session uuid; pass --transcript)"
        label = "own transcript"
    else:
        if not who:
            return "broken", "traj ref without who"
        target = os.path.join(xdir, "traj-%s.upto-cut.jsonl" % who)
        label = "peer-%s snapshot" % who
        if not os.path.exists(target) or os.path.getsize(target) == 0:
            return "broken", "no published snapshot for peer %s yet" % who
    try:
        rows, stats = traj_index.parse_all(target)
    except OSError:
        return "broken", "cannot read %s" % target
    n = stats["complete_lines"]
    if hi > n - 1:
        if who != actor:
            return "broken", "anchor L%d beyond snapshot (%d lines) — sealed cut" % (hi, n)
        return "broken", "anchor L%d beyond transcript (%d lines)" % (hi, n)
    sha = e.get("sha")
    if sha:
        got = next((r["line_sha"] for r in rows if r["L"] == lo), None)
        if got != sha:
            return "broken", "line sha mismatch at L%d (ledger %s, %s %s)" % (lo, sha, label, got)
    return "ok", label


def resolve(e, actor, opts, xdir, repo):
    kind = e.get("kind")
    if kind == "traj":
        return resolve_traj(e, actor, opts, xdir)
    if kind == "commit":
        sha = e.get("sha") or ""
        r = subprocess.run(["git", "-C", repo, "cat-file", "-e", sha + "^{commit}"],
                           capture_output=True, text=True, timeout=20)
        return ("ok", "commit %s" % sha[:12]) if r.returncode == 0 else ("broken", "commit %s not in %s" % (sha[:12], repo))
    if kind == "file":
        p = e.get("path") or ""
        if not os.path.exists(p):
            return "broken", "file missing: %s" % p
        import hashlib
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        want = e.get("sha256") or ""
        return ("ok", "file %s" % p) if got == want else ("broken", "file sha256 mismatch: %s" % p)
    if kind == "row":
        p = e.get("file") or e.get("path") or ""
        match = e.get("match") or ""
        if not p or not os.path.exists(p):
            return "broken", "row file missing: %s" % p
        txt = open(p, "r", encoding="utf-8", errors="replace").read()
        try:
            hit = re.search(match, txt) is not None
        except re.error:
            hit = match in txt
        return ("ok", "row %r in %s" % (match, p)) if hit else ("broken", "row pattern %r not found in %s" % (match, p))
    if kind == "run":
        cwd = e.get("cwd") or ""
        cmd = e.get("cmd") or ""
        if not cmd or not os.path.isdir(cwd):
            return "broken", "run ref needs existing cwd and cmd"
        return "ok", "replayable: %s" % cmd[:60]
    if kind == "unresolved":
        reason = e.get("reason") or ""
        if not reason:
            return "broken", "unresolved entry needs a reason"
        return "declared", reason
    return "broken", "unknown kind %r" % kind


def cmd_check(opts, entries, parse_broken):
    actor = opts.get("actor") or die("check needs --actor", 2)
    if "round" not in opts:
        die("check needs --round <N>", 2)
    xdir = opts.get("xdir") or os.environ.get("WT_X") or "/root/wt/x"
    repo = opts.get("repo") or os.environ.get("WT_REPO") or "/root/wt/repo"
    resolved = declared = 0
    broken = list(parse_broken)
    for e in entries:
        status, detail = resolve(e, actor, opts, xdir, repo)
        if status == "ok":
            resolved += 1
        elif status == "declared":
            declared += 1
            print("  DECLARED %s: %s" % (e.get("id"), detail))
        else:
            broken.append({"id": e.get("id"), "why": detail})
    print("refs check actor=%s round=%s: %d refs, %d resolved, %d broken, %d declared-unresolved"
          % (actor, opts.get("round"), len(entries) + len(parse_broken), resolved, len(broken), declared))
    for b in broken:
        print("  BROKEN %s: %s" % (b["id"], b["why"]))
    return 1 if broken else 0


def cmd_biblio(entries, parse_broken, opts):
    actor = opts.get("actor") or "?"
    xdir = opts.get("xdir") or os.environ.get("WT_X") or "/root/wt/x"
    repo = opts.get("repo") or os.environ.get("WT_REPO") or "/root/wt/repo"
    print("biblio actor=%s: %d entries" % (actor, len(entries) + len(parse_broken)))
    for e in entries:
        status, detail = resolve(e, actor, opts, xdir, repo)
        tag = {"ok": "resolves", "declared": "unresolved (declared)", "broken": "BROKEN"}[status]
        print("  %-5s %-10s %-26s %s" % (e.get("id"), e.get("kind"), tag, str(detail)[:90]))
    for b in parse_broken:
        print("  %-5s %-10s %-26s %s" % (b["id"], "-", "BROKEN", b["why"]))
    return 0


def cmd_replay(opts, entries, rid):
    for e in entries:
        if e.get("id") == rid:
            if e.get("kind") != "run":
                die("%s is kind=%s, not run" % (rid, e.get("kind")), 2)
            cwd = e.get("cwd") or "."
            cmd = e.get("cmd") or ""
            expect = e.get("expect") or ""
            r = subprocess.run(["bash", "-lc", cmd], cwd=cwd, capture_output=True,
                               text=True, timeout=300)
            out = (r.stdout + r.stderr)[-8192:]
            if expect.startswith("exit "):
                want = int(expect.split()[1])
                ok = r.returncode == want
            else:
                ok = expect in (r.stdout + r.stderr) if expect else r.returncode == 0
            print("%s replay: rc=%d, expect=%r -> %s" % (rid, r.returncode, expect, "OK" if ok else "FAIL"))
            print(out)
            return 0 if ok else 1
    die("no entry %s" % rid, 2)


def main(argv):
    opts, pos = parse_argv(argv)
    if not pos:
        die("usage: refs.py [--actor a] [--refs P] [--xdir X] [--repo R] [--round N] <check|biblio|replay <id>>", 2)
    cmd = pos[0]
    refs_path = opts.get("refs")
    if not refs_path:
        actor = opts.get("actor")
        wd = "/root/wt/%s" % actor if actor else os.getcwd()
        refs_path = os.path.join(wd, "refs-%s.jsonl" % (actor or os.path.basename(os.getcwd())))
    entries, parse_broken = load_ledger(refs_path)
    if cmd == "check":
        return cmd_check(opts, entries, parse_broken)
    if cmd == "biblio":
        return cmd_biblio(entries, parse_broken, opts)
    if cmd == "replay":
        if len(pos) < 2:
            die("replay needs an id", 2)
        return cmd_replay(opts, entries, pos[1])
    die("unknown command %s" % cmd, 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
