#!/usr/bin/env python3
"""Independent re-derivation of MRC adapter-source digests and MRC* (verifier's own code).

Shares no code with a0/mrc. Implements the rule quoted in each declaration's
`adapter_source_rule` from scratch and compares against the declared values.
"""
import hashlib, json, subprocess, sys
from pathlib import Path

REPO = Path("/home/ebt/rsi-dev")
MRC = REPO / "a0/mrc"
ROUTES = ["codex-deepseek-responses", "claude-deepseek-anthropic",
          "kilo-deepseek-chat", "opencode-deepseek-chat"]
DOMAIN = "a0/mrc/v1"
COMPONENTS = ("ApiSurface", "Cli", "Endpoint", "Network", "Params",
              "Permissions", "Prompt", "Provider", "RequestedModel",
              "RuntimeAdapters", "TaskSnapshot", "Tools")

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def dom(domain, payload):
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + payload).hexdigest()

def git(*a):
    p = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True)
    if p.returncode: raise SystemExit(f"git {' '.join(a)}: {p.stderr.decode()}")
    return p.stdout

def entries_from_repo(commit, root):
    listing = git("ls-tree", "-r", "--name-only", commit, "--", root).decode()
    paths = sorted(p for p in listing.splitlines() if p)
    return [{"path": p, "sha256": hashlib.sha256(git("show", f"{commit}:{p}")).hexdigest()} for p in paths]

def adapter_digest(files):
    pairs = [[e["path"], e["sha256"]] for e in files]
    return dom(f"{DOMAIN}/RuntimeAdapters/adapter_source", canon(pairs))

def mrc_star(digests):
    return dom(f"{DOMAIN}/MRC*", canon({c: digests[c] for c in COMPONENTS}))

bad = 0
seen = {}
for route in ROUTES:
    doc = json.loads((MRC / "declarations" / f"{route}.mrc.json").read_text())
    # 1. adapter_source_sha256 reproduced from git bytes
    for a in doc["components"]["RuntimeAdapters"]["adapters"]:
        commit, root = a["adapter_commit"], a["adapter_source_root"]
        repo_files = entries_from_repo(commit, root)
        got = adapter_digest(repo_files)
        declared = a["adapter_source_sha256"]
        same_list = repo_files == a["adapter_source_files"]
        ok = got == declared and same_list
        bad += not ok
        seen[a["runtime"]] = got
        print(f"[{'ok ' if ok else 'BAD'}] {route:<28}{a['runtime']:<11} n={len(repo_files):>2} "
              f"recomputed={got} declared={declared} list_matches_repo={same_list}")
    # 2. MRC* reproduced from component digests
    cds = doc["component_digests"]
    got_mrc = mrc_star(cds)
    declared_mrc = doc["mrc_star"]
    ok = got_mrc == declared_mrc
    bad += not ok
    print(f"      MRC* recomputed={got_mrc} declared={declared_mrc} match={ok}")

print()
print("distinct adapter digests:", json.dumps(seen, indent=1))
print("RESULT:", "ALL REPRODUCED" if not bad else f"{bad} MISMATCH(ES)")
sys.exit(1 if bad else 0)
