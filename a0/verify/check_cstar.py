#!/usr/bin/env python3
"""Independent recomputation of every C* solution_sha256 against C_STAR/manifest.json."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/home/ebt/rsi-dev/a0")
MAN = ROOT / "tasks/circle-packing/C_STAR/manifest.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    m = json.loads(MAN.read_text())
    bad = []
    rows = []
    for c in m["candidates"]:
        d = ROOT / "tasks/circle-packing/C_STAR" / c["dir"]
        sol = d / "solution.py"
        got = sha(sol) if sol.exists() else None
        got_bytes = sol.stat().st_size if sol.exists() else None
        decl = c["solution_sha256"]
        src = c.get("source", {})
        ok = got == decl
        ok2 = (src.get("sha256") == decl) if src else None
        ok3 = (src.get("bytes") == got_bytes) if src else None
        if not ok:
            bad.append(c["candidate_id"])
        rows.append({"candidate_id": c["candidate_id"], "kind": c["kind"],
                     "declared": decl, "recomputed": got, "match": ok,
                     "source_sha_matches": ok2, "source_bytes_matches": ok3,
                     "bytes": got_bytes})
        print(f"[{'ok ' if ok else 'BAD'}] {c['candidate_id']:<26} {decl[:16] if decl else None} "
              f"recomputed={got[:16] if got else None} bytes={got_bytes} "
              f"src_sha_ok={ok2} src_bytes_ok={ok3}")

    # every directory under C_STAR, and the 14-vs-16 count question
    dirs = sorted(p.name for p in (MAN.parent).iterdir() if p.is_dir())
    files = sorted(p.name for p in (MAN.parent).iterdir() if p.is_file())
    print("\nmanifest candidate_count:", m["candidate_count"], "actual entries:", len(m["candidates"]))
    print("C_STAR subdirectories:", len(dirs), dirs)
    print("C_STAR loose files   :", files)
    extra = [d for d in dirs if d not in {c["dir"] for c in m["candidates"]}]
    missing = [c["dir"] for c in m["candidates"] if c["dir"] not in dirs]
    print("dirs not in manifest :", extra)
    print("manifest dirs missing:", missing)
    print("\nmanifest mtime:", MAN.stat().st_mtime, " size:", MAN.stat().st_size)
    print("BAD count:", len(bad), bad)
    (ROOT / "verify/out/cstar_integrity.json").write_text(json.dumps(
        {"rows": rows, "bad": bad, "extra_dirs": extra, "missing_dirs": missing,
         "manifest_sha256": sha(MAN), "manifest_mtime": MAN.stat().st_mtime,
         "candidate_count_declared": m["candidate_count"],
         "candidate_count_actual": len(m["candidates"])}, indent=2))
    return 1 if bad or extra or missing else 0


if __name__ == "__main__":
    sys.exit(main())
