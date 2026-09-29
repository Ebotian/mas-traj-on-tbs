#!/usr/bin/env python3
"""Replay the research_state_control v1->v4 patch chain from a decoded ChatGPT
share payload, then compare the result against the copies on disk.

Input : /tmp/mapping.json   (produced by decode_share.py)
Output: /tmp/replay/mnt/*   (the reconstructed files)

The six mutating messages were identified by a completeness scan: every chain
message that mentions research_state_control AND contains a mutation primitive
(cat >, cat >>, write_text, sed -i, tee, rename, shutil, open(w/a)).  Exactly six
matched, so the chain has no gaps.

LaTeX tooling is neutralised (xelatex/biber/pdftex/pdfinfo -> true) because only
the text artifacts matter and ctex is not installed here.
"""
import json, re, hashlib, subprocess, sys, shutil
from pathlib import Path

MAPPING = Path("/tmp/mapping.json")
CORPUS = Path("/home/ebt/rsi-dev/related_files")
SBX = Path("/tmp/replay/mnt")
WORK = Path("/tmp/replay")

# chain positions of the mutating messages, in create_time order.
# This is the UNION of two scans, because each pattern set had a blind spot:
#   scan A (cat/write_text/tee, absolute paths) missed #2821, which creates v2 by `cp`;
#   scan B (added cp/mv, tightened write_text) missed #2958, whose `p.write_text()` is
#     separated from the filename by other statements.
# The known-answer comparison against the on-disk v4 is the judge of whether the set is right.
POSITIONS = [2775, 2821, 2823, 2831, 2870, 2954, 2958]

# LaTeX tooling is neutralised with PATH shims rather than by text substitution:
# substituting the word `biber` also rewrote `backend=biber` inside a heredoc body.
SHIMS = ["xelatex", "pdflatex", "latexmk", "biber", "bibtex", "pdfinfo"]

# what each step is expected to produce, for the known-answer comparison
EXPECT = [
    ("research_state_control_review.tex", "research_state_control_review.tex"),
    ("research_state_control_refs.bib", "research_state_control_refs.bib"),
    ("research_state_control_review_v2.tex", None),
    ("research_state_control_refs_v2.bib", None),
    ("research_state_control_review_v3.tex", None),
    ("research_state_control_refs_v3.bib", None),
    ("research_state_control_review_v4.tex", "research_state_control_review_v4.tex"),
    ("research_state_control_refs_v4.bib", "research_state_control_refs_v4.bib"),
]


def chain_order(mp):
    roots = [n for n, v in mp.items() if v.get("parent") in (None, "")]
    assert len(roots) == 1, f"expected 1 root, got {len(roots)}"
    out, cur, seen = [], roots[0], set()
    while cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        ch = mp[cur].get("children") or []
        cur = ch[0] if ch else None
    assert len(out) == len(mp), f"chain {len(out)} != mapping {len(mp)}"
    return out


def tool_text(m):
    c = m.get("content") or {}
    p = c.get("parts")
    if isinstance(p, list):
        return "\n".join(x for x in p if isinstance(x, str))
    for k in ("text", "result", "output"):
        if isinstance(c.get(k), str):
            return c[k]
    return ""


DANGER = re.compile(
    r"urllib|requests\b|socket|curl\s|wget\s|subprocess|os\.system|os\.popen|"
    r"shutil\.rmtree|unlink|\.rmdir|eval\(|exec\(|__import__"
)


def sanitise(text):
    """Strip the wrapper, remap the sandbox root, neuter LaTeX."""
    body = text
    for pre in ("bash -lc ", "bash -c "):
        if body.startswith(pre):
            body = body[len(pre):]
            break
    bad = DANGER.findall(body)
    if bad:
        raise SystemExit(f"refusing to run: dangerous constructs {sorted(set(bad))}")
    # `rm -f <latex aux>` is the only rm in the chain; allow it, block everything else.
    # Scan for `rm -` only: LaTeX bodies contain `\rm` (roman font switch), which is not a command.
    for m in re.finditer(r"\brm\s+-[^\n|&;]*", body):
        frag = m.group(0)
        if not re.fullmatch(r"rm -f research_state_control_review_v4\.\{aux,bbl,bcf,blg,log,out,run\.xml,toc\}", frag.strip()):
            raise SystemExit(f"refusing to run: unrecognised rm -> {frag[:120]!r}")
    body = body.replace("/mnt/data", str(SBX))
    return body


def make_shims():
    """Executable no-ops for the LaTeX toolchain, so no tool name is ever substituted
    into a document body. pdfinfo emits a Pages line because scripts pipe it to grep."""
    bindir = WORK / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    for t in SHIMS:
        p = bindir / t
        p.write_text("#!/bin/sh\n" + ('echo "Pages: 0"\n' if t == "pdfinfo" else "") + "exit 0\n")
        p.chmod(0o755)
    return bindir


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    mp = json.loads(MAPPING.read_text())
    order = chain_order(mp)
    if WORK.exists():
        shutil.rmtree(WORK)
    SBX.mkdir(parents=True)
    bindir = make_shims()
    env = dict(__import__("os").environ)
    env["PATH"] = f"{bindir}:" + env.get("PATH", "")
    # the scripts grep these LaTeX logs; create them empty so the greps do not error out
    for lg in ("x1", "x2", "x3", "bib", "v4b", "v4x2", "v4x3"):
        Path(f"/tmp/{lg}.log").write_text("")

    for i, pos in enumerate(POSITIONS, 1):
        raw = tool_text(mp[order[pos]]["message"])
        script = sanitise(raw)
        f = WORK / f"step{i}.sh"
        f.write_text(script)
        r = subprocess.run(["bash", str(f)], capture_output=True, text=True, cwd=str(WORK), env=env)
        after = sorted(p.name for p in SBX.iterdir())
        print(f"step {i} (chain#{pos}) exit={r.returncode} script={len(script)} chars")
        print(f"        sandbox now: {after}")
        if r.returncode != 0:
            print("        stderr tail:", r.stderr.strip()[-300:])

    print("\n=== known-answer comparison against the corpus ===")
    ok = True
    for made, diskname in EXPECT:
        p = SBX / made
        if not p.exists():
            print(f"  {made:44s} MISSING from replay")
            ok = False
            continue
        line = f"  {made:44s} {p.stat().st_size:>7d} B  sha={sha(p)[:16]}"
        if diskname:
            d = CORPUS / diskname
            same = sha(p) == sha(d)
            line += f"  |  disk {d.stat().st_size:>7d} B sha={sha(d)[:16]}  ->  {'IDENTICAL' if same else 'DIFFERS'}"
            if not same:
                ok = False
                a = p.read_text(encoding="utf-8").split("\n")
                b = d.read_text(encoding="utf-8").split("\n")
                import difflib
                diff = [x for x in difflib.unified_diff(b, a, lineterm="", n=0)]
                line += f"  ({len(diff)} diff lines)"
                for x in diff[:8]:
                    line += "\n        " + x[:150]
        else:
            line += "  |  (not in corpus — this is a recovered file)"
        print(line)
    print("\nVERDICT:", "replay reproduces the on-disk v4 exactly" if ok else "replay does NOT reproduce disk")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
