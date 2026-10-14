#!/usr/bin/env python3
"""Build a light raw review packet under local2gpt/out/ (the review-packet pipeline).

Canon, calibrated from microarch-3-4-raw-lite-2026-10-13 and tumor-raw-lite-2026-10-13:

  out/<name>/          name = "<runs>-raw-lite-<build-date>", no fingerprint in the dir
    README.md          rendered last; NOT covered by SHA256SUMS
    MANIFEST.txt       "<bytes>\\t<relpath>" per regular payload file, path-sorted
    SHA256SUMS         "<sha256>  <relpath>" over MANIFEST.txt + payload, path-sorted
    <dest>/ ...        job trees: hardlinked where possible, byte-copied otherwise;
                       <exclude> globs dropped; symlinks recreated as symlinks
  fingerprint = sha256(SHA256SUMS)[:8];  archive = out/<name>-<fp>.tar.gz

Sources are never written; a before/after metadata digest proves it.
Self-checks abort on failure: count parity, fallback-copy hash equality,
sha256sum -c on the directory and on the extracted archive, secret reverse-scan.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

DEFAULT_ENVS = [os.path.expanduser(p) for p in (
    "~/harbor-runs/walkthrough/walkthrough.env",
    "~/harbor-runs/config/agent.env",
    "~/harbor-runs/config/agent-tokenplan.env",
)]
DEFAULT_EXCLUDES = ["*/agent/otel*"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_meta_digest(root):
    """Digest of (relpath, mode, size, mtime_ns) over every entry; proves sources untouched."""
    h = hashlib.sha256()
    n = 0
    for dp, dns, fns in os.walk(root):
        dns.sort()
        fns.sort()
        for fn in fns:
            fp = os.path.join(dp, fn)
            st = os.lstat(fp)
            h.update(
                f"{os.path.relpath(fp, root)}|{st.st_mode}|{st.st_size}|{st.st_mtime_ns}\n".encode()
            )
            n += 1
    return h.hexdigest(), n


def human_bytes(n):
    if n >= 10**9:
        return f"{n / 10**9:.2f} GB"
    return f"{n / 10**6:.0f} MB"


def build_run(src, dst, excludes):
    stats = {"hard": 0, "copy": 0, "link": 0, "dir": 0, "excl": 0, "excl_bytes": 0}
    fallback = []
    for dp, dns, fns in os.walk(src):
        dns.sort()
        fns.sort()
        rel_dp = os.path.relpath(dp, src)
        d = dst if rel_dp == "." else os.path.join(dst, rel_dp)
        os.makedirs(d, exist_ok=True)
        stats["dir"] += 1
        for fn in fns:
            sp = os.path.join(dp, fn)
            rel = os.path.relpath(sp, src)
            st = os.lstat(sp)
            if any(fnmatch.fnmatch(rel, pat) for pat in excludes):
                stats["excl"] += 1
                stats["excl_bytes"] += st.st_size
                continue
            tgt = os.path.join(dst, rel)
            if stat.S_ISLNK(st.st_mode):
                os.symlink(os.readlink(sp), tgt)
                stats["link"] += 1
                continue
            try:
                os.link(sp, tgt)
                stats["hard"] += 1
            except OSError:
                shutil.copy2(sp, tgt)
                stats["copy"] += 1
                fallback.append((sp, tgt))
    return stats, fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help='e.g. "tumor-3-microarch-5-raw-lite-2026-10-14"')
    ap.add_argument("--date", default=None, help="build date for README (default: today, local)")
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--run", action="append", required=True, metavar="SRC:DEST",
                    help="job tree source and its directory name inside the packet (repeatable)")
    ap.add_argument("--exclude", action="append", default=None, metavar="GLOB",
                    help="fnmatch pattern on the path relative to SRC (default: */agent/otel*)")
    ap.add_argument("--env-file", action="append", default=None, metavar="PATH")
    ap.add_argument("--readme-template", required=True, help="README template with {{PLACEHOLDER}}s")
    ap.add_argument("--readme-data", default=None, help="JSON file with extra {{PLACEHOLDER}} string fields")
    ap.add_argument("--no-tar", action="store_true")
    args = ap.parse_args()

    date = args.date or time.strftime("%Y-%m-%d")
    excludes = args.exclude or DEFAULT_EXCLUDES
    envs = args.env_file or DEFAULT_ENVS

    runs = []
    for spec in args.run:
        src, sep, dest = spec.rpartition(":")
        if not sep or not os.path.isdir(src):
            sys.exit(f"bad --run {spec!r} (need existing SRC:DEST)")
        runs.append((os.path.abspath(src), dest))

    pkt = os.path.join(args.outdir, args.name)
    if os.path.exists(pkt):
        sys.exit(f"refusing to overwrite existing {pkt}")
    os.makedirs(pkt)

    print(f"== build {args.name} ==")
    src_before = {src: tree_meta_digest(src) for src, _ in runs}

    all_fallback = []
    run_stats = {}
    for src, dest in runs:
        s, fb = build_run(src, os.path.join(pkt, dest), excludes)
        run_stats[dest] = s
        all_fallback += fb
        print(f"  {dest}: hard={s['hard']} copy={s['copy']} symlink={s['link']} "
              f"dir={s['dir']} excluded={s['excl']} ({human_bytes(s['excl_bytes'])})")

    # fallback copies must equal their sources byte-for-byte
    for sp, tp in all_fallback:
        if sha256_file(sp) != sha256_file(tp):
            sys.exit(f"COPY MISMATCH {sp} -> {tp}")
    # count parity: dst regular files = src regular files - excluded; symlinks equal
    for src, dest in runs:
        src_f = src_l = 0
        for dp, dns, fns in os.walk(src):
            for fn in fns:
                st = os.lstat(os.path.join(dp, fn))
                if stat.S_ISLNK(st.st_mode):
                    src_l += 1
                else:
                    rel = os.path.relpath(os.path.join(dp, fn), src)
                    if not any(fnmatch.fnmatch(rel, pat) for pat in excludes):
                        src_f += 1
        dst_f = dst_l = 0
        for dp, dns, fns in os.walk(os.path.join(pkt, dest)):
            for fn in fns:
                st = os.lstat(os.path.join(dp, fn))
                if stat.S_ISLNK(st.st_mode):
                    dst_l += 1
                else:
                    dst_f += 1
        s = run_stats[dest]
        if dst_f != src_f or dst_l != src_l or dst_f != s["hard"] + s["copy"] or dst_l != s["link"]:
            sys.exit(f"COUNT MISMATCH {dest}: src f/l = {src_f}/{src_l}, dst = {dst_f}/{dst_l}")
    print("  count parity + fallback-copy hashes: OK")

    # payload (regular files under the run dirs), path-sorted from the packet root
    payload = []
    for _, dest in runs:
        for dp, dns, fns in os.walk(os.path.join(pkt, dest)):
            dns.sort()
            fns.sort()
            for fn in fns:
                fp = os.path.join(dp, fn)
                st = os.lstat(fp)
                if stat.S_ISLNK(st.st_mode):
                    continue
                payload.append((os.path.relpath(fp, pkt), st.st_size))
    payload.sort()
    total_bytes = sum(sz for _, sz in payload)
    links_total = sum(s["link"] for s in run_stats.values())

    with open(os.path.join(pkt, "MANIFEST.txt"), "w") as f:
        for rel, sz in payload:
            f.write(f"{sz}\t{rel}\n")

    entries = ["MANIFEST.txt"] + [rel for rel, _ in payload]
    entries.sort()
    with open(os.path.join(pkt, "SHA256SUMS"), "w") as f:
        for rel in entries:
            f.write(f"{sha256_file(os.path.join(pkt, rel))}  {rel}\n")

    fp = sha256_file(os.path.join(pkt, "SHA256SUMS"))[:8]
    archive = f"{args.name}-{fp}.tar.gz"
    print(f"  payload: {len(payload)} files, {links_total} symlinks, {human_bytes(total_bytes)}")
    print(f"  fingerprint: {fp}")

    # README from template, last (never covered by SHA256SUMS)
    computed = {
        "NAME": args.name, "DATE": date, "FP": fp, "ARCHIVE": archive,
        "FILES": str(len(payload)), "SIZE_MB": str(round(total_bytes / 10**6)),
        "LINKS": str(links_total),
        "EXCL_COUNT": str(sum(s["excl"] for s in run_stats.values())),
        "EXCL_BYTES_H": human_bytes(sum(s["excl_bytes"] for s in run_stats.values())),
        "RUNS_LABEL": " / ".join(d for _, d in runs),
        "RUNS_DIRS_LINE": "、".join(f"`{d}/`" for _, d in runs),
    }
    extra = {}
    if args.readme_data:
        extra = json.load(open(args.readme_data))
        extra = {k: str(v) for k, v in extra.items()}
    tpl = open(args.readme_template).read()
    out = tpl
    for k, v in {**extra, **computed}.items():
        out = out.replace("{{" + k + "}}", v)
    if "{{" in out:
        sys.exit(f"unfilled placeholder(s) remain: {sorted(set(re.findall(r'{{([A-Z_]+)}}', out)))}")
    with open(os.path.join(pkt, "README.md"), "w") as f:
        f.write(out)

    # sources untouched?
    for src, _ in runs:
        now = tree_meta_digest(src)
        if now != src_before[src]:
            sys.exit(f"SOURCE CHANGED DURING BUILD: {src}")

    # secret reverse-scan (values never printed)
    values = set()
    for ef in envs:
        try:
            for line in open(ef, errors="ignore"):
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    if v and re.search(r"KEY|TOKEN|SECRET", k.upper()):
                        values.add(v.encode())
        except FileNotFoundError:
            print(f"  note: env file missing: {ef}")
    hits = {}
    for dp, dns, fns in os.walk(pkt):
        for fn in fns:
            fp2 = os.path.join(dp, fn)
            if stat.S_ISLNK(os.lstat(fp2).st_mode):
                continue
            data = open(fp2, "rb").read()
            for v in values:
                if v in data:
                    hits.setdefault(v, []).append(os.path.relpath(fp2, pkt))
    if hits:
        for v, files in hits.items():
            print(f"  SECRET HIT {hashlib.sha256(v).hexdigest()[:8]}: {files[:5]}")
        sys.exit("secret reverse-scan failed")
    print(f"  secret reverse-scan: {len(values)} values, 0 hits")

    # directory self-check via sha256sum -c
    res = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=pkt,
                         capture_output=True, text=True)
    ok = res.stdout.count(": OK")
    bad = res.stdout.count("FAILED")
    if res.returncode != 0 or bad or ok != len(entries):
        print(res.stdout[-2000:])
        sys.exit(f"sha256sum -c failed (ok={ok}/{len(entries)}, bad={bad})")
    print(f"  sha256sum -c: {ok}/{len(entries)} OK")

    if args.no_tar:
        print(f"DONE (no tar): {pkt}")
        return

    tarpath = os.path.join(args.outdir, archive)
    subprocess.run(["tar", "-czf", tarpath, "-C", args.outdir, args.name], check=True)
    listing = subprocess.run(["tar", "-tzf", tarpath], capture_output=True, text=True, check=True)
    n_entries = len(listing.stdout.splitlines())
    tar_sha = sha256_file(tarpath)
    tar_size = os.path.getsize(tarpath)
    print(f"  tar: {archive}  {n_entries} entries  {human_bytes(tar_size)}  sha256 {tar_sha}")

    # extract-and-verify: what a reviewer unpacks must pass the same checks
    tmp = os.path.join(args.outdir, f".verify-{args.name}")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    subprocess.run(["tar", "-xzf", tarpath, "-C", tmp], check=True)
    res = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=os.path.join(tmp, args.name),
                         capture_output=True, text=True)
    ok = res.stdout.count(": OK")
    if res.returncode != 0 or res.stdout.count("FAILED") or ok != len(entries):
        sys.exit("extracted-tree sha256sum -c failed")
    d = subprocess.run(["diff", "-rq", os.path.join(tmp, args.name), pkt], capture_output=True, text=True)
    if d.returncode != 0 or d.stdout.strip():
        sys.exit(f"extracted tree differs (rc={d.returncode}):\n{d.stdout[:2000]}{d.stderr[:500]}")
    shutil.rmtree(tmp)
    print("  extract-verify: sha256sum -c + diff -rq clean")
    print(f"DONE: {tarpath}")


if __name__ == "__main__":
    main()
