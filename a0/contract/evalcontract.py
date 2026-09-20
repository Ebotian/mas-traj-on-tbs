#!/usr/bin/env python3
"""Canonical evaluator identity EID* (step A-1).

EID* = H(EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition)

Every component digest is a pure function of a recorded, machine-portable input
record.  Nothing in a digest depends on absolute paths, file modification times,
ownership, hostname, process id, or traversal order, so the same logical input
yields the same EID* on any machine and from any working directory.

Runtime-agnostic by construction: this module imports nothing from KAPSO, EvE or
Loreley, and has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from pathlib import Path

SCHEMA = "a0.evalcontract/v1"
SPEC_SCHEMA = "a0.evalcontract.spec/v1"
DOMAIN = "a0/evalcontract/v1"
COMPONENTS = (
    "EvaluatorSource",
    "DependencyLock",
    "DataManifest",
    "Config",
    "MetricDefinition",
)

DEFAULT_EXCLUDES = (
    ".git/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/.venv/**",
    "**/node_modules/**",
    "**/.DS_Store",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
)

DEFAULT_INCLUDES = ("**/*",)

_ABS_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_DRIVE_PATH_RE = re.compile(r"(?:^|[^A-Za-z0-9_])[A-Za-z]:[\\/]")


class ContractError(Exception):
    """Raised for any input that cannot yield a well-defined EID*."""


# --------------------------------------------------------------------------
# canonical serialization
# --------------------------------------------------------------------------


def canonical_json(obj) -> bytes:
    """Deterministic JSON bytes: sorted keys, no whitespace, ASCII-only output.

    ``allow_nan=False`` forbids NaN/Infinity, which have no portable encoding.
    Keys are stringified recursively so that ``{1: x}`` and ``{"1": x}`` collide
    rather than ordering unpredictably.
    """
    try:
        text = json.dumps(
            _stringify_keys(obj),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except ValueError as exc:
        raise ContractError(f"value is not canonicalizable: {exc}") from exc
    return text.encode("ascii")


def _stringify_keys(obj):
    if isinstance(obj, dict):
        return {str(k): _stringify_keys(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify_keys(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, float, str)):
        return obj
    raise ContractError(f"value of type {type(obj).__name__!r} is not canonicalizable")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_file_digest(path) -> str:
    """Digest of a JSON document's canonical form.

    Used for values that must be frozen by reference rather than by bytes, such
    as ``fr.spec_hash``: reformatting or reordering the declaration file must not
    change the frozen identity, but editing any value must.
    """
    return sha256_hex(canonical_json(json.loads(Path(path).read_text(encoding="utf-8"))))


def domain_digest(domain: str, payload: bytes) -> str:
    """Hash with explicit domain separation so digests of different kinds of
    object never collide even if their payload bytes coincide."""
    return sha256_hex(domain.encode("ascii") + b"\x00" + payload)


def component_digest(name: str, payload_obj) -> str:
    if name not in COMPONENTS:
        raise ContractError(f"unknown component {name!r}")
    return domain_digest(f"{DOMAIN}/{name}", canonical_json(payload_obj))


def combined_eid_star(digests: dict[str, str]) -> str:
    missing = [c for c in COMPONENTS if c not in digests]
    if missing:
        raise ContractError(f"missing component digests: {missing}")
    payload = canonical_json({c: digests[c] for c in COMPONENTS})
    return domain_digest(f"{DOMAIN}/EID*", payload)


# --------------------------------------------------------------------------
# path hygiene
# --------------------------------------------------------------------------


def posix_rel(rel: str) -> str:
    """Normalize a root-relative path: forward slashes, no ``./``, no trailing ``/``."""
    p = rel.replace(os.sep, "/").replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.rstrip("/")
    if not p:
        raise ContractError("empty relative path")
    if p == ".." or p.startswith("../") or _ABS_PATH_RE.match(p):
        raise ContractError(f"path escapes the declared root: {rel!r}")
    parts = [seg for seg in p.split("/") if seg not in ("", ".")]
    if any(seg == ".." for seg in parts):
        raise ContractError(f"path escapes the declared root: {rel!r}")
    return "/".join(parts)


def assert_no_absolute_paths(value, where: str) -> None:
    """Config and MetricDefinition must be location-independent, otherwise the
    same logical evaluator would hash differently on two machines."""
    if isinstance(value, str):
        if _ABS_PATH_RE.match(value) or _DRIVE_PATH_RE.search(value):
            raise ContractError(f"{where}: absolute path leaked into hashed input: {value!r}")
    elif isinstance(value, dict):
        for k, v in value.items():
            assert_no_absolute_paths(v, f"{where}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            assert_no_absolute_paths(v, f"{where}[{i}]")


# --------------------------------------------------------------------------
# glob matching
# --------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def _glob_to_regex(pattern: str) -> re.Pattern:
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                j = i + 2
                if j < n and pattern[j] == "/":
                    out.append("(?:.*/)?")
                    i = j + 1
                    continue
                out.append(".*")
                i = j
                continue
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _selected(rel: str, include, exclude) -> bool:
    if any(_glob_to_regex(p).match(rel) for p in exclude):
        return False
    return any(_glob_to_regex(p).match(rel) for p in include)


# --------------------------------------------------------------------------
# file hashing
# --------------------------------------------------------------------------


def hash_file(path: Path) -> dict:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return {"sha256": h.hexdigest(), "size": size}


def collect_tree(root: Path, include, exclude) -> list[dict]:
    if not root.exists():
        raise ContractError(f"declared root does not exist: {root}")
    if not root.is_dir():
        raise ContractError(f"declared root is not a directory: {root}")
    records: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in filenames:
            full = Path(dirpath) / name
            rel = posix_rel(str(full.relative_to(root)))
            if not _selected(rel, include, exclude):
                continue
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                target = os.readlink(full)
                if os.path.isabs(target):
                    raise ContractError(f"symlink escapes declared root: {rel} -> {target}")
                records.append({"path": rel, "kind": "symlink", "target": posix_rel(target)})
                continue
            rec = {"path": rel, "kind": "file"}
            rec.update(hash_file(full))
            records.append(rec)
    records.sort(key=lambda r: r["path"])
    return records


# --------------------------------------------------------------------------
# component builders
# --------------------------------------------------------------------------


def build_evaluator_source(cfg: dict, base: Path) -> dict:
    root_rel = posix_rel(cfg.get("root", "."))
    includes = tuple(cfg.get("include", DEFAULT_INCLUDES))
    excludes = tuple(cfg.get("exclude", DEFAULT_EXCLUDES)) + tuple(DEFAULT_EXCLUDES)
    records = collect_tree(base / root_rel, includes, excludes)
    if cfg.get("require_nonempty", True) and not records:
        raise ContractError(f"EvaluatorSource root {root_rel!r} selected zero files")
    payload = {"root": root_rel, "records": records}
    return {
        "kind": "source_tree",
        "declared": cfg,
        "root": root_rel,
        "include": list(includes),
        "records": records,
        "digest": component_digest("EvaluatorSource", payload),
    }


def _lock_entries_uv(path: Path) -> list[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    out = []
    for pkg in data.get("package", []):
        if "name" not in pkg:
            continue
        out.append(f"{pkg['name']}=={pkg.get('version', 'unknown')}")
    return out


def _lock_entries_requirements(path: Path) -> list[str]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        out.append(re.sub(r"\s+", "", line))
    return out


def _lock_entries_pyproject(path: Path) -> list[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    reqs = list(project.get("dependencies", []))
    for group in (project.get("optional-dependencies", {}) or {}).values():
        reqs.extend(group)
    for group in (data.get("dependency-groups", {}) or {}).values():
        reqs.extend(x for x in group if isinstance(x, str))
    out = []
    for req in reqs:
        stripped = req.strip()
        name = re.split(r"[<>=!~\[ (;]", stripped, maxsplit=1)[0]
        out.append(f"{name.lower()}{stripped[len(name):].strip()}")
    return out


def _lock_entries_package_lock(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for key, meta in (data.get("packages", {}) or {}).items():
        if not key:
            continue
        name = key.rsplit("node_modules/", 1)[-1]
        if name:
            out.append(f"{name}=={meta.get('version', 'unknown')}")
    for name, meta in (data.get("dependencies", {}) or {}).items():
        out.append(f"{name}=={meta.get('version', 'unknown')}")
    return out


_LOCK_KINDS = {
    "uv.lock": _lock_entries_uv,
    "requirements.txt": _lock_entries_requirements,
    "requirements-dev.txt": _lock_entries_requirements,
    "pyproject.toml": _lock_entries_pyproject,
    "package-lock.json": _lock_entries_package_lock,
}


def build_dependency_lock(cfg: dict, base: Path) -> dict:
    files = cfg.get("files", [])
    records = []
    for spec in files:
        if isinstance(spec, str):
            spec = {"path": spec}
        rel = posix_rel(spec["path"])
        path = base / rel
        if not path.exists():
            raise ContractError(f"DependencyLock file missing: {rel}")
        kind = spec.get("kind") or _LOCK_KINDS.get(os.path.basename(rel), "raw")
        if kind == "raw":
            file_hash = hash_file(path)
            records.append({"lock": rel, "kind": "raw", "sha256": file_hash["sha256"],
                            "size": file_hash["size"]})
            continue
        fn = _LOCK_KINDS.get(kind) if kind in _LOCK_KINDS else None
        if fn is None:
            raise ContractError(f"unknown DependencyLock kind {kind!r} for {rel}")
        for entry in fn(path):
            records.append({"lock": rel, "kind": kind, "entry": entry})
    for entry in cfg.get("entries", []):
        assert_no_absolute_paths(entry, "DependencyLock.entries")
        records.append({"kind": "inline", "entry": entry})
    records.sort(key=canonical_json)
    if not records:
        raise ContractError("DependencyLock resolved to zero entries; refusing to hash nothing")
    return {
        "kind": "lock_entries",
        "declared": cfg,
        "records": records,
        "digest": component_digest("DependencyLock", records),
    }


def build_data_manifest(cfg: dict, base: Path) -> dict:
    records = []
    for spec in cfg.get("files", []):
        if isinstance(spec, str):
            spec = {"path": spec}
        rel = posix_rel(spec["path"])
        path = base / rel
        if not path.exists():
            raise ContractError(f"DataManifest file missing: {rel}")
        rec = {"data": rel, "kind": "file"}
        rec.update(hash_file(path))
        records.append(rec)
    for entry in cfg.get("entries", []):
        assert_no_absolute_paths(entry, "DataManifest.entries")
        records.append({"kind": "inline", "entry": entry})
    if not records:
        raise ContractError("DataManifest requires at least one file or inline entry")
    records.sort(key=canonical_json)
    return {
        "kind": "data_manifest",
        "declared": cfg,
        "records": records,
        "digest": component_digest("DataManifest", records),
    }


def build_config(cfg: dict, base: Path) -> dict:
    value = _resolve_value_component(cfg, base, "Config")
    assert_no_absolute_paths(value, "Config")
    return {
        "kind": "value",
        "declared": cfg,
        "value": value,
        "digest": component_digest("Config", value),
    }


def _find_metric(value):
    if isinstance(value, dict):
        if "name" in value and "direction" in value:
            return value
        for nested in value.values():
            found = _find_metric(nested)
            if found is not None:
                return found
    return None


def build_metric_definition(cfg: dict, base: Path) -> dict:
    value = _resolve_value_component(cfg, base, "MetricDefinition")
    assert_no_absolute_paths(value, "MetricDefinition")
    metric = _find_metric(value)
    if metric is None:
        raise ContractError("MetricDefinition requires a 'name' and a 'direction'")
    if metric["direction"] not in ("maximize", "minimize"):
        raise ContractError("MetricDefinition requires direction in {maximize, minimize}")
    return {
        "kind": "value",
        "declared": cfg,
        "value": value,
        "metric_name": metric["name"],
        "direction": metric["direction"],
        "digest": component_digest("MetricDefinition", value),
    }


def _resolve_value_component(cfg: dict, base: Path, name: str):
    if "value" in cfg:
        return cfg["value"]
    if "files" in cfg:
        merged = {}
        for spec in cfg["files"]:
            if isinstance(spec, str):
                spec = {"path": spec}
            rel = posix_rel(spec["path"])
            path = base / rel
            if not path.exists():
                raise ContractError(f"{name} file missing: {rel}")
            kind = spec.get("kind") or os.path.splitext(rel)[1].lstrip(".") or "raw"
            if kind in ("json", "jsonc"):
                merged[rel] = json.loads(path.read_text(encoding="utf-8"))
            elif kind == "toml":
                merged[rel] = tomllib.loads(path.read_text(encoding="utf-8"))
            else:
                merged[rel] = {"raw_sha256": hash_file(path)["sha256"]}
        return merged
    raise ContractError(f"{name} requires either 'value' or 'files'")


_BUILDERS = {
    "EvaluatorSource": build_evaluator_source,
    "DependencyLock": build_dependency_lock,
    "DataManifest": build_data_manifest,
    "Config": build_config,
    "MetricDefinition": build_metric_definition,
}


# --------------------------------------------------------------------------
# top level
# --------------------------------------------------------------------------


def resolve_base(spec: dict, spec_path: Path, cli_base: str | None) -> Path:
    if cli_base:
        return Path(cli_base).resolve()
    declared = spec.get("base", ".")
    if os.path.isabs(declared):
        raise ContractError("spec 'base' must be relative so the spec stays portable")
    return (spec_path.parent / declared).resolve()


def build_contract(spec: dict, spec_path: Path, cli_base: str | None = None) -> dict:
    if spec.get("schema") != SPEC_SCHEMA:
        raise ContractError(f"spec schema must be {SPEC_SCHEMA}, got {spec.get('schema')!r}")
    base = resolve_base(spec, spec_path, cli_base)
    declared = spec.get("components", {})
    missing = [c for c in COMPONENTS if c not in declared]
    if missing:
        raise ContractError(f"spec omits components: {missing}")
    components = {}
    for name in COMPONENTS:
        components[name] = _BUILDERS[name](declared[name], base)
    digests = {c: components[c]["digest"] for c in COMPONENTS}
    try:
        spec_ref = spec_path.resolve().relative_to(base).as_posix()
    except ValueError:
        spec_ref = spec_path.name
    return {
        "schema": SCHEMA,
        "task": spec.get("task"),
        "spec": spec_ref,
        "base_declared": spec.get("base", "."),
        "components": components,
        "eid_star": combined_eid_star(digests),
        "eid_star_derivation": {
            "algorithm": "sha256",
            "domain": f"{DOMAIN}/EID*",
            "payload_canonical": canonical_json(digests).decode("ascii"),
        },
    }


def recompute_from_records(doc: dict) -> dict:
    """Recompute every component digest and EID* from the recorded inputs alone.

    Touches no filesystem, so it succeeds identically on any machine holding the
    EID*.json document.
    """
    if doc.get("schema") != SCHEMA:
        raise ContractError(f"document schema must be {SCHEMA}, got {doc.get('schema')!r}")
    components = doc.get("components", {})
    digests = {}
    for name in COMPONENTS:
        comp = components.get(name)
        if comp is None:
            raise ContractError(f"document omits component {name}")
        kind = comp.get("kind")
        if kind in ("source_tree", "data_manifest", "lock_entries"):
            payload = ({"root": comp["root"], "records": comp["records"]}
                       if kind == "source_tree" else comp["records"])
        elif kind == "value":
            payload = comp["value"]
        else:
            raise ContractError(f"component {name} has unknown kind {kind!r}")
        digests[name] = component_digest(name, payload)
    return {"components": digests, "eid_star": combined_eid_star(digests)}


def verify_against_filesystem(doc: dict, base: Path) -> list[str]:
    """Re-read the declared inputs and report any drift from the recorded hashes."""
    drift: list[str] = []
    components = doc["components"]
    for name in COMPONENTS:
        comp = components[name]
        try:
            fresh = _BUILDERS[name](comp["declared"], base)
        except ContractError as exc:
            drift.append(f"{name}: {exc}")
            continue
        if fresh["digest"] != comp["digest"]:
            drift.append(f"{name}: digest changed {comp['digest'][:12]} -> {fresh['digest'][:12]}")

    src = components["EvaluatorSource"]
    includes = tuple(src.get("include", DEFAULT_INCLUDES))
    excludes = tuple(src.get("exclude", DEFAULT_EXCLUDES))
    try:
        current = collect_tree(base / src["root"], includes, excludes)
    except ContractError as exc:
        return drift + [f"EvaluatorSource: {exc}"]
    recorded = {r["path"]: r for r in src["records"]}
    live = {r["path"]: r for r in current}
    for path in sorted(set(recorded) | set(live)):
        if path not in live:
            drift.append(f"EvaluatorSource: missing {src['root']}/{path}")
        elif path not in recorded:
            drift.append(f"EvaluatorSource: untracked new file {src['root']}/{path}")
        elif canonical_json(recorded[path]) != canonical_json(live[path]):
            drift.append(f"EvaluatorSource: content changed {src['root']}/{path}")
    return drift


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _cmd_compute(args) -> int:
    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        raise ContractError(f"spec not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    doc = build_contract(spec, spec_path, args.base)
    out = Path(args.out) if args.out else spec_path.parent / f"{spec_path.stem}.EID.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"EID* = {doc['eid_star']}")
    for name in COMPONENTS:
        print(f"  {name:<18} {doc['components'][name]['digest']}")
    print(f"written: {out}")
    return 0


def _cmd_recompute(args) -> int:
    doc = json.loads(Path(args.eid_file).read_text(encoding="utf-8"))
    recomputed = recompute_from_records(doc)
    ok = True
    for name in COMPONENTS:
        recorded = doc["components"][name]["digest"]
        got = recomputed["components"][name]
        flag = "ok " if recorded == got else "BAD"
        ok &= recorded == got
        print(f"  [{flag}] {name:<18} recorded={recorded[:16]} recomputed={got[:16]}")
    flag = "ok " if doc["eid_star"] == recomputed["eid_star"] else "BAD"
    ok &= doc["eid_star"] == recomputed["eid_star"]
    print(f"  [{flag}] EID*               recorded={doc['eid_star'][:16]} "
          f"recomputed={recomputed['eid_star'][:16]}")
    return 0 if ok else 1


def _cmd_verify(args) -> int:
    eid_path = Path(args.eid_file).resolve()
    doc = json.loads(eid_path.read_text(encoding="utf-8"))
    candidates = []
    if args.spec:
        candidates.append(Path(args.spec))
    candidates.append(eid_path.parent / doc["spec"])
    if args.base:
        candidates.append(Path(args.base) / doc["spec"])
    spec_path = next((p for p in candidates if p.exists()), None)
    if spec_path is None:
        print("cannot locate the spec: looked in "
              + ", ".join(str(p) for p in candidates)
              + "; pass --spec or --base", file=sys.stderr)
        return 2
    spec_path = spec_path.resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = resolve_base(spec, spec_path, args.base)
    drift = verify_against_filesystem(doc, base)
    live = build_contract(spec, spec_path, str(base))
    if live["eid_star"] != doc["eid_star"]:
        drift.append(f"EID* changed {doc['eid_star'][:16]} -> {live['eid_star'][:16]}")
    if drift:
        for item in drift:
            print(f"DRIFT {item}")
        return 1
    print(f"clean: all recorded inputs match; EID* = {doc['eid_star']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="evalcontract", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compute = sub.add_parser("compute", help="hash inputs and write the EID* document")
    p_compute.add_argument("--spec", required=True)
    p_compute.add_argument("--base", default=None,
                           help="override the spec's relative 'base' (IO only, never hashed)")
    p_compute.add_argument("--out", default=None)
    p_compute.set_defaults(fn=_cmd_compute)

    p_recompute = sub.add_parser("recompute", help="recompute EID* from recorded inputs only")
    p_recompute.add_argument("--eid-file", required=True)
    p_recompute.set_defaults(fn=_cmd_recompute)

    p_verify = sub.add_parser("verify", help="re-read declared inputs and report drift")
    p_verify.add_argument("--eid-file", required=True)
    p_verify.add_argument("--spec", default=None,
                          help="spec to re-run; defaults to a sibling of the EID* document")
    p_verify.add_argument("--base", default=None)
    p_verify.set_defaults(fn=_cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
