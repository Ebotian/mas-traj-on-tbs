#!/usr/bin/env python3
"""Item 1 — the identity chain, re-derived independently.

Nothing here imports `evalcontract` or `e_star`: the documented recipes are
re-implemented from the prose so a bug in the module that *authors* the
identity cannot hide inside the check.

    python3 a0/verify/a1-final/v1_identity.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MAXCUT = REPO / "a0/tasks/maxcut"
EID_PATH = REPO / "a0/a1/T1-EID.json"
SPEC_PATH = REPO / "a0/a1/T1.contract.json"

DOMAIN = "a0/evalcontract/v1"
COMPONENTS = ("EvaluatorSource", "DependencyLock", "DataManifest", "Config", "MetricDefinition")
EXPECTED_EID = "7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec"
EXPECTED_ESTAR = "dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def domain_digest(domain: str, payload: bytes) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + payload).hexdigest()


def component_digest(name: str, payload) -> str:
    return domain_digest(f"{DOMAIN}/{name}", canon(payload))


def component_payload(comp: dict):
    kind = comp["kind"]
    if kind == "source_tree":
        return {"root": comp["root"], "records": comp["records"]}
    if kind in ("data_manifest", "lock_entries"):
        return comp["records"]
    if kind == "value":
        return comp["value"]
    raise SystemExit(f"unknown kind {kind!r}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    doc = json.loads(EID_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    # -- 1. EID* from the document's own recorded material -------------------
    digests = {}
    for name in COMPONENTS:
        comp = doc["components"][name]
        d = component_digest(name, component_payload(comp))
        digests[name] = d
        check(f"component digest recomputes: {name}",
              d == comp["digest"], f"{d[:16]} vs recorded {comp['digest'][:16]}")
    eid = domain_digest(f"{DOMAIN}/EID*", canon({c: digests[c] for c in COMPONENTS}))
    check("EID* recomputed from recorded records", eid == EXPECTED_EID,
          f"{eid} == {EXPECTED_EID}")

    # the derivation payload the document itself carries must match too
    payload = doc["eid_star_derivation"]["payload_canonical"]
    check("eid_star_derivation.payload_canonical matches recomputation",
          payload == canon({c: digests[c] for c in COMPONENTS}).decode("ascii"))

    # -- 2. EvaluatorSource records vs the files on disk ---------------------
    recs = {r["path"]: r for r in doc["components"]["EvaluatorSource"]["records"]}
    for name in ("e_star.py", "e_star_child.py"):
        rel = f"a0/tasks/maxcut/{name}"
        live = sha256_file(REPO / rel)
        got = recs.get(name, {}).get("sha256")
        check(f"EvaluatorSource record == on-disk bytes: {name}", got == live,
              f"{str(got)[:16]} vs {live[:16]}; size {recs.get(name, {}).get('size')} vs {(REPO / rel).stat().st_size}")

    # the spec's include globs must select exactly these two files
    root = REPO / spec["components"]["EvaluatorSource"]["root"]
    live_files = {
        str(p.relative_to(root))
        for p in root.iterdir()
        if p.is_file() and p.name in ("e_star.py", "e_star_child.py")
    }
    check("EvaluatorSource contains exactly the two declared sources",
          set(recs) == {"e_star.py", "e_star_child.py"} == live_files, str(sorted(recs)))

    # -- 3. E*'s own identity, from its own recipe --------------------------
    own = subprocess.run([sys.executable, "-c", "import e_star,json;print(e_star.evaluator_source_digest())"],
                         cwd=MAXCUT, capture_output=True, text=True)
    got_own = own.stdout.strip()
    check("E*'s own evaluator_source_digest()", got_own == EXPECTED_ESTAR, got_own)

    # reproduce E*'s recipe by hand (canonical json of [{name,bytes,sha256}]
    # *plus E*'s own trailing newline* -- e_star.canonical_json adds "\n",
    # evalcontract.canonical_json does not)
    hand = hashlib.sha256((
        canon([{"name": n, "bytes": (MAXCUT / n).stat().st_size, "sha256": sha256_file(MAXCUT / n)}
               for n in ("e_star.py", "e_star_child.py")]) + b"\n"
    )).hexdigest()
    check("hand-recomputed E* source digest == dc6969ec", hand == EXPECTED_ESTAR, hand)

    cli = subprocess.run([sys.executable, "e_star.py", "digest", "--value-only"],
                         cwd=MAXCUT, capture_output=True, text=True)
    check("e_star.py digest --value-only", cli.stdout.strip() == EXPECTED_ESTAR, cli.stdout.strip())

    # -- 4. the two identities are built from the same file material --------
    rec_material = {p: r["sha256"] for p, r in recs.items()}
    estar_material = {"e_star.py": sha256_file(MAXCUT / "e_star.py"),
                      "e_star_child.py": sha256_file(MAXCUT / "e_star_child.py")}
    check("EvaluatorSource material == E* source material", rec_material == estar_material)

    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
