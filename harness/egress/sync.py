#!/usr/bin/env python3
"""Diff the composed policy against a LIVE sidecar's allowlist and, with
--apply, re-apply the full composed list.

The sidecar's `network-policy allow` REPLACES the whole list; this tool always
sends the complete composed set from the manifests, which is what makes the
manifests the single source of truth. Default is a dry check - never touches a
running trial unless --apply is given deliberately.

Run: python3 /home/ebt/harbor-runs/egress/sync.py --task tumor-immune-interface \
       --container <sidecar-name> [--apply]
"""
import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rulelib  # noqa: E402


def exec_in(container, cmd):
    return subprocess.run(
        ["docker", "exec", container] + cmd, capture_output=True, text=True, timeout=60
    )


def read_live(container):
    r = exec_in(container, ["cat", "/opt/egress-sidecar/allowlist.txt"])
    if r.returncode != 0:
        sys.exit(f"cannot read allowlist from {container}: {r.stderr.strip()[:200]}")
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--container", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    composed = rulelib.compose(*rulelib.load_layers(args.task))
    live = read_live(args.container)
    only_manifest = [h for h in composed if h not in live]
    only_live = [h for h in live if h not in composed]
    print(f"composed {len(composed)} | live {len(live)}")
    print(f"  only-in-manifest: {only_manifest}")
    print(f"  only-in-live:     {only_live}")
    if not only_manifest and not only_live:
        print("in sync")
        return
    if not args.apply:
        print("(dry check; pass --apply to re-apply the full composed list)")
        sys.exit(1)

    r = exec_in(args.container, ["network-policy", "allow"] + composed)
    print(r.stdout.strip()[:300] or r.stderr.strip()[:300])
    after = read_live(args.container)
    ok = after == composed
    print(f"after: {len(after)} hosts | match: {ok}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
