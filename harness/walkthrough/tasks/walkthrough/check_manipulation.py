#!/usr/bin/env python3
"""check_manipulation.py — did each run actually apply its handoff mode?

For each finished job: clone the collected protocol.bundle, then inspect the
peer-directed handoff texts:
  - review-<actor>-to-<peer>.md  (Round 4; on branch <actor>, fallback main)
  - work-<actor>-1.md            (its "## revised" tail, Round 5)
Counts the R-arm marker tokens in the opening lines of the review and the tail
of the work note; R runs should show the structured block, N runs are not
required to (accidental hits are reported, not judged). Also prints the first
lines of each review for a human read.

Usage: python3 check_manipulation.py <job> [<job> ...]
"""
import json, pathlib, re, subprocess, sys, tempfile

BASE = pathlib.Path(__file__).resolve().parents[3] / "jobs" / "agent"   # <harbor-runs>/jobs/agent
MARKERS = ["schema", "act", "operation", "objective", "state", "checkpoint",
           "artifact_refs", "evidence_refs", "acceptance"]
WORDY = {"act", "state", "operation", "objective", "schema", "acceptance"}

def hits(text):
    low = text.lower()
    got = []
    for m in MARKERS:
        if m in WORDY:
            if re.search(rf"\b{m}\b", low):
                got.append(m)
        elif m in low:
            got.append(m)
    return got

def git_show(repo, branch, path, mode):
    r = subprocess.run(["git", "show", f"{branch}:{path}"], cwd=repo,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    lines = r.stdout.splitlines()
    return lines[:30] if mode == "head" else lines[-30:]

def check(job):
    jd = BASE / job
    bundle = next(jd.rglob("protocol.bundle"), None)
    out = {"job": job}
    vp = next((p for p in jd.rglob("prompt-variant") if "x" in str(p)), None)
    out["variant"] = vp.read_text().strip() if vp else None
    if not bundle:
        out["error"] = "no protocol.bundle"
        return out
    with tempfile.TemporaryDirectory() as t:
        repo = str(pathlib.Path(t) / "repo")
        subprocess.run(["git", "clone", "-q", str(bundle), repo], check=True)
        docs = out.setdefault("docs", {})
        for actor, peer in (("a", "b"), ("b", "a")):
            for path, mode in ((f"review-{actor}-to-{peer}.md", "head"),
                               (f"work-{actor}-1.md", "tail")):
                seg = None
                for branch in (actor, f"origin/{actor}", "main", "origin/main"):
                    seg = git_show(repo, branch, path, mode)
                    if seg is not None:
                        break
                key = f"{path}[{mode}]"
                if seg is None:
                    docs[key] = {"found": False}
                else:
                    text = "\n".join(seg)
                    docs[key] = {"found": True, "markers": hits(text),
                                 "sample": [l for l in seg[:8]]}
    return out

def main():
    for job in sys.argv[1:]:
        r = check(job)
        print(f"=== {r['job']} variant={r.get('variant')}")
        if "error" in r:
            print("   ", r["error"]); continue
        for key, d in r.get("docs", {}).items():
            if not d.get("found"):
                print(f"    {key}: NOT FOUND"); continue
            print(f"    {key}: markers={len(d['markers'])} {d['markers']}")
            for l in d["sample"][:4]:
                print(f"        | {l}")
        print()

if __name__ == "__main__":
    main()
