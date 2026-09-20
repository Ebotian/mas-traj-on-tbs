#!/usr/bin/env python3
"""Adversarial re-implementation of EID* (a0/contract/evalcontract.py) from the
written specification only.  Deliberately does NOT import evalcontract.py.

Scheme re-derived from contract/SPEC.md §2 and the observed document shape:
    component = sha256( "a0/evalcontract/v1/<Component>" + b"\x00" + canon(payload) )
    EID*      = sha256( "a0/evalcontract/v1/EID*"      + b"\x00" + canon({comp: digest}) )
    canon(x)  = json.dumps(stringify_keys(x), sort_keys=True, separators=(",",":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii")
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tomllib
from pathlib import Path

DOMAIN = "a0/evalcontract/v1"
COMPONENTS = ("EvaluatorSource", "DependencyLock", "DataManifest", "Config", "MetricDefinition")

DEFAULT_EXCLUDES = (
    ".git/**", "**/.git/**", "**/__pycache__/**", "**/*.pyc", "**/*.pyo",
    "**/.venv/**", "**/node_modules/**", "**/.DS_Store", "**/.mypy_cache/**",
    "**/.pytest_cache/**", "**/.ruff_cache/**",
)


def stringify(o):
    if isinstance(o, dict):
        return {str(k): stringify(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [stringify(v) for v in o]
    if isinstance(o, bool) or o is None or isinstance(o, (int, float, str)):
        return o
    raise TypeError(type(o))


def canon(o) -> bytes:
    return json.dumps(stringify(o), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def dom(name: str, payload: bytes) -> str:
    return hashlib.sha256(name.encode("ascii") + b"\x00" + payload).hexdigest()


def comp(name: str, payload) -> str:
    return dom(f"{DOMAIN}/{name}", canon(payload))


def file_sha(path: Path):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def glob_to_re(p: str):
    import re
    out, i, n = [], 0, len(p)
    while i < n:
        c = p[i]
        if c == "*":
            if i + 1 < n and p[i + 1] == "*":
                j = i + 2
                if j < n and p[j] == "/":
                    out.append("(?:.*/)?"); i = j + 1; continue
                out.append(".*"); i = j; continue
            out.append("[^/]*"); i += 1
        elif c == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(c)); i += 1
    return re.compile("^" + "".join(out) + "$")


def selected(rel, inc, exc):
    if any(glob_to_re(p).match(rel) for p in exc):
        return False
    return any(glob_to_re(p).match(rel) for p in inc)


def tree(root: Path, inc, exc):
    recs = []
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns.sort(); fns.sort()
        for fn in fns:
            full = Path(dp) / fn
            rel = full.relative_to(root).as_posix()
            if not selected(rel, inc, exc):
                continue
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                recs.append({"path": rel, "kind": "symlink", "target": os.readlink(full)})
                continue
            d, s = file_sha(full)
            recs.append({"path": rel, "kind": "file", "sha256": d, "size": s})
    recs.sort(key=lambda r: r["path"])
    return recs


LOCK_KINDS = {
    "uv.lock": "uv", "requirements.txt": "req", "requirements-dev.txt": "req",
    "pyproject.toml": "pyp", "package-lock.json": "npm",
}


def lock_entries(path: Path, kind: str):
    import re
    if kind == "uv":
        d = tomllib.loads(path.read_text())
        return [f"{p['name']}=={p.get('version','unknown')}" for p in d.get("package", []) if "name" in p]
    if kind == "req":
        out = []
        for raw in path.read_text().splitlines():
            line = raw.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                out.append(re.sub(r"\s+", "", line))
        return out
    if kind == "pyp":
        d = tomllib.loads(path.read_text())
        reqs = list(d.get("project", {}).get("dependencies", []))
        for g in (d.get("project", {}).get("optional-dependencies", {}) or {}).values():
            reqs.extend(g)
        for g in (d.get("dependency-groups", {}) or {}).values():
            reqs.extend(x for x in g if isinstance(x, str))
        out = []
        for r in reqs:
            s = r.strip()
            nm = re.split(r"[<>=!~\[ (;]", s, maxsplit=1)[0]
            out.append(f"{nm.lower()}{s[len(nm):].strip()}")
        return out
    raise ValueError(kind)


def build(spec: dict, base: Path):
    C = spec["components"]
    # --- EvaluatorSource
    es = C["EvaluatorSource"]
    root_rel = es.get("root", ".")
    inc = tuple(es.get("include", ("**/*",)))
    exc = tuple(es.get("exclude", DEFAULT_EXCLUDES)) + DEFAULT_EXCLUDES
    recs = tree(base / root_rel, inc, exc)
    d_es = comp("EvaluatorSource", {"root": root_rel, "records": recs})

    # --- DependencyLock
    dl = C["DependencyLock"]
    lrecs = []
    for s in dl.get("files", []):
        s = {"path": s} if isinstance(s, str) else s
        rel = s["path"]
        p = base / rel
        kind = s.get("kind") or LOCK_KINDS.get(os.path.basename(rel), "raw")
        if kind == "raw":
            d, sz = file_sha(p)
            lrecs.append({"lock": rel, "kind": "raw", "sha256": d, "size": sz})
        else:
            for e in lock_entries(p, kind):
                lrecs.append({"lock": rel, "kind": kind, "entry": e})
    for e in dl.get("entries", []):
        lrecs.append({"kind": "inline", "entry": e})
    lrecs.sort(key=canon)
    d_dl = comp("DependencyLock", lrecs)

    # --- DataManifest
    dm = C["DataManifest"]
    mrecs = []
    for s in dm.get("files", []):
        s = {"path": s} if isinstance(s, str) else s
        rel = s["path"]
        d, sz = file_sha(base / rel)
        mrecs.append({"data": rel, "kind": "file", "sha256": d, "size": sz})
    for e in dm.get("entries", []):
        mrecs.append({"kind": "inline", "entry": e})
    mrecs.sort(key=canon)
    d_dm = comp("DataManifest", mrecs)

    d_cfg = comp("Config", C["Config"]["value"])
    d_met = comp("MetricDefinition", C["MetricDefinition"]["value"])

    digs = {"EvaluatorSource": d_es, "DependencyLock": d_dl, "DataManifest": d_dm,
            "Config": d_cfg, "MetricDefinition": d_met}
    eid = dom(f"{DOMAIN}/EID*", canon(digs))
    return {"digests": digs, "eid_star": eid, "es_records": recs,
            "es_paths": [r["path"] for r in recs]}


if __name__ == "__main__":
    spec_path = Path(sys.argv[1] if len(sys.argv) > 1 else
                     "/home/ebt/rsi-dev/a0/contract/plumbing.contract.json")
    base = (spec_path.parent / json.loads(spec_path.read_text())["base"]).resolve()
    out = build(json.loads(spec_path.read_text()), base)
    print(json.dumps({"base": str(base), "digests": out["digests"],
                      "eid_star": out["eid_star"], "es_paths": out["es_paths"]}, indent=2))
