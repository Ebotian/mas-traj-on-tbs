#!/usr/bin/env python3
"""Canonical Model Route Contract MRC* (external review, point 7).

MRC* = H(Provider, Endpoint, RequestedModel, ApiSurface, Params, Cli, Prompt,
         Tools, Permissions, Network, RuntimeAdapters, TaskSnapshot)

Purpose.  ``EID*`` freezes *what was measured*.  ``MRC*`` freezes *what was
measuring it*: the declared model route a runtime's turns actually take.  The
A1 estimand is therefore

    Δ | same declared model route          (this contract)

and never

    Δ | same model weights                  (not verifiable, see below)

which is the whole point: no provider on this route attests to the weights that
served a request.  The ``model`` field is metadata the server writes back, and
on the Anthropic-compatible surface it is a verbatim echo of the request while
on the OpenAI-compatible surfaces a retired alias is silently rewritten.  Two
surfaces given the *same* alias therefore report *different* "served" ids, so
neither report can be read as proof of identity.  ``RequestedModel.weights_identity``
freezes that non-claim as part of the digest, and ``identity_evidence`` records
what was actually observed.

Every component digest is a pure function of a recorded, machine-portable input
record.  Nothing in a digest depends on absolute paths, file modification times,
ownership, hostname, process id, or traversal order, so the same logical route
yields the same MRC* on any machine.  Credentials never appear: only the *names*
of the environment variables that carry them.  The one digest that covers bytes
outside the declaration is ``RuntimeAdapters[].adapter_source_sha256``: it is
computed over an explicitly listed manifest of (repo-relative path, sha256) pairs
and that manifest is recorded beside it, so anyone holding the declaration can
recompute it (``ADAPTER_SOURCE_RULE``).

Runtime-agnostic by construction: this module has no third-party dependencies
and imports nothing from ``a0/contract``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "a0.mrc/v1"
DOMAIN = "a0/mrc/v1"
COMPONENTS = (
    "Provider",
    "Endpoint",
    "RequestedModel",
    "ApiSurface",
    "Params",
    "Cli",
    "Prompt",
    "Tools",
    "Permissions",
    "Network",
    "RuntimeAdapters",
    "TaskSnapshot",
)

# The EID* this contract is paired with.  A declaration whose TaskSnapshot names
# any other evaluator identity is measuring a different thing and must not be
# accepted; see a0/STATUS.md section 3.1.
FROZEN_EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"

# User decision (2026-09-21): DeepSeek flash is primary, mixed use of
# deepseek-v4-pro is permitted as a calibration arm, OpenRouter is excluded.
POLICY_PRIMARY = "deepseek-flash"
POLICY_EXCLUDED = ("openrouter",)
POLICY_PERMITTED_SECONDARY = ("deepseek-v4-pro",)

_ABS_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_DRIVE_PATH_RE = re.compile(r"(?:^|[^A-Za-z0-9_])[A-Za-z]:[\\/]")
_SECRET_RE = re.compile(r"(?:sk-[A-Za-z0-9_\-]{12,}|Bearer\s+[A-Za-z0-9._\-]{12,})")
# A URL path such as /v1/responses is not a machine-local location and must be
# hashable; a filesystem root such as /home/... must never be.  The two are told
# apart by the first segment, and only a URL-typed key may carry a leading slash.
_URL_PATH_RE = re.compile(r"^/[A-Za-z0-9._~%/-]*$")
_FS_ROOT_RE = re.compile(
    r"^/(?:home|Users|usr|var|tmp|root|opt|etc|mnt|media|srv|proc|sys|dev|bin|sbin|"
    r"lib|lib64|boot|run|Volumes)(?:/|$)"
)
_URLISH_KEY_TOKENS = ("url", "path", "endpoint", "route")
_TIMESTAMPY_KEYS = frozenset(
    {"mtime", "ctime", "atime", "modified", "modified_at", "accessed", "inode",
     "device", "uid", "gid", "owner", "absolute_path", "abspath", "hostname", "pid"}
)


class MRCError(Exception):
    """Raised for any input that cannot yield a well-defined MRC*."""


# --------------------------------------------------------------------------
# canonical serialization (byte-identical in spirit to a0/contract/evalcontract.py)
# --------------------------------------------------------------------------


def _stringify_keys(obj):
    if isinstance(obj, dict):
        return {str(k): _stringify_keys(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify_keys(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, float, str)):
        return obj
    raise MRCError(f"value of type {type(obj).__name__!r} is not canonicalizable")


def canonical_json(obj) -> bytes:
    """Deterministic JSON bytes: sorted keys, no whitespace, ASCII-only output."""
    try:
        text = json.dumps(
            _stringify_keys(obj),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except ValueError as exc:
        raise MRCError(f"value is not canonicalizable: {exc}") from exc
    return text.encode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(obj) -> str:
    return sha256_hex(canonical_json(obj))


def domain_digest(domain: str, payload: bytes) -> str:
    """Hash with explicit domain separation so digests of different kinds of
    object never collide even if their payload bytes coincide."""
    return sha256_hex(domain.encode("ascii") + b"\x00" + payload)


def component_digest(name: str, payload_obj) -> str:
    if name not in COMPONENTS:
        raise MRCError(f"unknown component {name!r}")
    return domain_digest(f"{DOMAIN}/{name}", canonical_json(payload_obj))


def mrc_star_from_digests(digests: dict) -> str:
    missing = [c for c in COMPONENTS if c not in digests]
    if missing:
        raise MRCError(f"missing component digests: {missing}")
    return domain_digest(f"{DOMAIN}/MRC*", canonical_json({c: digests[c] for c in COMPONENTS}))


# --------------------------------------------------------------------------
# the adapter-source preimage
# --------------------------------------------------------------------------

# `RuntimeAdapters.adapters[].adapter_source_sha256` is not "the hash of some
# file": it is the hash of an explicitly listed, ordered manifest of
# (repo-relative path, sha256 of that path's bytes) pairs.  A reader holding the
# declaration alone can therefore recompute it, and the validator rejects a
# digest that has no preimage (``MRC-ADAPTER-PREIMAGE``) or whose preimage does
# not hash to it (``MRC-ADAPTER-DIGEST``).  A digest that cannot be traced to
# bytes is a declaration that cannot be checked, which is the defect class this
# contract exists to remove.
ADAPTER_SOURCE_DOMAIN = f"{DOMAIN}/RuntimeAdapters/adapter_source"

ADAPTER_SOURCE_RULE = (
    "adapter_source_sha256 = sha256(b'a0/mrc/v1/RuntimeAdapters/adapter_source' + b'\\x00' + "
    "canonical_json([[path, sha256(file bytes)], ...])) over the adapter_source_files entries in "
    "the order listed, where canonical_json = json.dumps(obj, sort_keys=True, "
    "separators=(',',':'), ensure_ascii=True). The list is every blob under adapter_source_root "
    "at adapter_commit, taken from `git ls-tree -r <adapter_commit> -- <adapter_source_root>` "
    "and ordered by ascending path."
)


def adapter_preimage(entries) -> list:
    """Normalize a recorded preimage to the ordered ``[[path, sha256], ...]`` payload."""
    if not isinstance(entries, list):
        raise MRCError("adapter_source_files must be a list of {path, sha256} entries")
    pairs = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise MRCError("adapter_source_files entries must be objects with a path and a sha256")
        path, digest = entry.get("path"), entry.get("sha256")
        if not isinstance(path, str) or not path:
            raise MRCError("adapter_source_files entry has no path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise MRCError(f"adapter_source_files entry {path!r} has no sha256 hex digest")
        pairs.append([path, digest])
    if not pairs:
        raise MRCError("adapter_source_files is empty")
    if pairs != sorted(pairs):
        raise MRCError("adapter_source_files must be listed in ascending path order")
    if len({path for path, _ in pairs}) != len(pairs):
        raise MRCError("adapter_source_files repeats a path")
    return pairs


def adapter_source_digest(entries) -> str:
    """The digest of an adapter preimage, by the rule recorded with it."""
    return domain_digest(ADAPTER_SOURCE_DOMAIN, canonical_json(adapter_preimage(entries)))


# --------------------------------------------------------------------------
# hygiene: nothing non-portable or secret may enter a digest
# --------------------------------------------------------------------------


def assert_clean(value, where: str, key: str = "") -> None:
    """Config-like hashed material must be location-independent and carry no
    credential material.  A declaration is a contract, not a key store."""
    if isinstance(value, str):
        if _DRIVE_PATH_RE.search(value):
            raise MRCError(f"{where}: absolute path leaked into hashed input: {value!r}")
        if _ABS_PATH_RE.match(value):
            url_typed = any(tok in key.lower() for tok in _URLISH_KEY_TOKENS)
            if not (url_typed and _URL_PATH_RE.match(value) and not _FS_ROOT_RE.match(value)):
                raise MRCError(f"{where}: absolute path leaked into hashed input: {value!r}")
        if _SECRET_RE.search(value):
            raise MRCError(f"{where}: credential-shaped literal leaked into hashed input")
    elif isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _TIMESTAMPY_KEYS:
                raise MRCError(f"{where}: non-portable key {k!r} may not be hashed")
            assert_clean(v, f"{where}.{k}", str(k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            assert_clean(v, f"{where}[{i}]", key)


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def build_mrc(spec: dict) -> dict:
    if spec.get("schema") != SCHEMA:
        raise MRCError(f"spec schema must be {SCHEMA}, got {spec.get('schema')!r}")
    route_id = spec.get("route_id")
    if not route_id or not isinstance(route_id, str):
        raise MRCError("spec requires a non-empty string route_id")
    components = spec.get("components")
    if not isinstance(components, dict):
        raise MRCError("spec requires a components object")
    missing = [c for c in COMPONENTS if c not in components]
    if missing:
        raise MRCError(f"spec omits components: {missing}")
    extra = [c for c in components if c not in COMPONENTS]
    if extra:
        raise MRCError(f"spec has unknown components: {extra}")

    cleaned = {}
    for name in COMPONENTS:
        payload = components[name]
        if not isinstance(payload, dict):
            raise MRCError(f"component {name} must be an object")
        assert_clean(payload, name)
        cleaned[name] = payload

    digests = {c: component_digest(c, cleaned[c]) for c in COMPONENTS}
    doc = {
        "schema": SCHEMA,
        "route_id": route_id,
        "model_policy": spec.get("model_policy"),
        "components": cleaned,
        "component_digests": digests,
        "mrc_star": mrc_star_from_digests(digests),
        "mrc_star_derivation": {
            "algorithm": "sha256",
            "domain": f"{DOMAIN}/MRC*",
            "payload_canonical": canonical_json(digests).decode("ascii"),
        },
        "identity_evidence": spec.get("identity_evidence"),
        "notes": spec.get("notes", []),
    }
    doc["identity_evidence_digest"] = (
        canonical_digest(doc["identity_evidence"]) if doc["identity_evidence"] is not None else None
    )
    return doc


def recompute_from_records(doc: dict) -> dict:
    """Recompute every component digest and MRC* from the recorded payloads alone.

    Touches no filesystem, so it succeeds identically on any machine holding the
    declaration document.
    """
    if doc.get("schema") != SCHEMA:
        raise MRCError(f"document schema must be {SCHEMA}, got {doc.get('schema')!r}")
    components = doc.get("components")
    if not isinstance(components, dict):
        raise MRCError("document omits components")
    digests = {}
    for name in COMPONENTS:
        if name not in components:
            raise MRCError(f"document omits component {name}")
        digests[name] = component_digest(name, components[name])
    return {"component_digests": digests, "mrc_star": mrc_star_from_digests(digests)}


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------


def _err(out: list, code: str, msg: str) -> None:
    out.append(f"{code}: {msg}")


def check_null_digests(value, where: str, out: list) -> None:
    """A digest-typed field may be null only with a stated reason.

    An unfrozen prompt hash is a real exposure, not a formatting detail: the
    contract must say *that it is unfrozen and why*, so a reader cannot mistake
    a missing digest for a verified one.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).endswith("_sha256") and v is None:
                if f"{str(k)[:-len('_sha256')]}_null_reason" not in value:
                    _err(out, "MRC-NULL-DIGEST",
                         f"{where}.{k} is null without a stated null_reason")
            check_null_digests(v, f"{where}.{k}", out)
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            check_null_digests(v, f"{where}[{i}]", out)


def load_frozen(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {r["route_id"]: r for r in doc["routes"]}


def validate(doc: dict, frozen: dict | None = None, expect_eid: str = FROZEN_EID_STAR) -> list:
    """Return a list of problems; empty list means the declaration is usable.

    Checks, in order: shape and digests, hygiene, the identity-evidence block
    (an echo must not be presented as proof), the frozen route registry, the
    model policy, and the task snapshot's pairing with EID*.
    """
    out: list[str] = []
    if not isinstance(doc, dict):
        return ["MRC-SCHEMA: declaration is not a JSON object"]
    if doc.get("schema") != SCHEMA:
        _err(out, "MRC-SCHEMA", f"schema must be {SCHEMA}, got {doc.get('schema')!r}")
        return out
    if not doc.get("route_id"):
        _err(out, "MRC-SCHEMA", "missing route_id")

    components = doc.get("components")
    if not isinstance(components, dict):
        _err(out, "MRC-MISSING-COMPONENT", "missing components object")
        return out
    for name in COMPONENTS:
        if name not in components:
            _err(out, "MRC-MISSING-COMPONENT", f"component {name} absent")
    if any(p.startswith("MRC-MISSING-COMPONENT") for p in out):
        return out

    # 1. digests recompute exactly
    try:
        recomputed = recompute_from_records(doc)
    except MRCError as exc:
        _err(out, "MRC-DIGEST-MISMATCH", str(exc))
        return out
    recorded = doc.get("component_digests") or {}
    for name in COMPONENTS:
        if recorded.get(name) != recomputed["component_digests"][name]:
            _err(out, "MRC-DIGEST-MISMATCH",
                 f"{name}: recorded={recorded.get(name)} recomputed={recomputed['component_digests'][name]}")
    if doc.get("mrc_star") != recomputed["mrc_star"]:
        _err(out, "MRC-DIGEST-MISMATCH",
             f"MRC*: recorded={doc.get('mrc_star')} recomputed={recomputed['mrc_star']}")

    # 2. hygiene over the hashed payloads
    for name in COMPONENTS:
        try:
            assert_clean(components[name], name)
        except MRCError as exc:
            _err(out, "MRC-HYGIENE", str(exc))
        check_null_digests(components[name], name, out)

    # 3. identity evidence -- an echo is not proof
    ie = doc.get("identity_evidence")
    if not isinstance(ie, dict):
        _err(out, "MRC-IDENTITY-MISSING", "identity_evidence block absent")
    else:
        if ie.get("weights_identity_verifiable") is not False:
            _err(out, "MRC-IDENTITY-WEIGHTS-CLAIM",
                 "weights_identity_verifiable must be exactly false; no surface here attests weights")
        if ie.get("echo_is_not_proof") is not True:
            _err(out, "MRC-IDENTITY-ECHO-AS-PROOF",
                 "echo_is_not_proof must be exactly true")
        obs = ie.get("observations")
        if not isinstance(obs, list) or not obs:
            _err(out, "MRC-IDENTITY-MISSING", "identity_evidence.observations must be non-empty")
        else:
            for i, o in enumerate(obs):
                if not isinstance(o, dict):
                    _err(out, "MRC-IDENTITY-MISSING", f"observations[{i}] is not an object")
                    continue
                for field in ("surface", "requested_model_id", "echoed_model_id", "http_status"):
                    if field not in o:
                        _err(out, "MRC-IDENTITY-MISSING", f"observations[{i}] lacks {field!r}")
                if o.get("echoed_model_id") == o.get("requested_model_id") and o.get("proves_weights"):
                    _err(out, "MRC-IDENTITY-ECHO-AS-PROOF",
                         f"observations[{i}] treats an echo as weight proof")
        if not ie.get("last_observed_utc"):
            _err(out, "MRC-IDENTITY-MISSING", "identity_evidence.last_observed_utc absent")

    # 4. frozen route registry -- drift in provider/endpoint/surface/model fails
    if frozen:
        rid = doc.get("route_id")
        entry = frozen.get(rid)
        if entry is None:
            _err(out, "MRC-ROUTE-UNKNOWN", f"route {rid!r} is not in the frozen registry")
        else:
            checks = (
                ("MRC-PROVIDER-DRIFT", components["Provider"].get("provider_id"), entry["provider_id"]),
                ("MRC-ENDPOINT-DRIFT", components["Endpoint"].get("base_url"), entry["base_url"]),
                ("MRC-SURFACE-DRIFT", components["ApiSurface"].get("surface_path"), entry["surface_path"]),
                ("MRC-MODEL-DRIFT", components["RequestedModel"].get("requested_model_id"),
                 entry["requested_model_id"]),
            )
            for code, got, want in checks:
                if got != want:
                    _err(out, code, f"{rid}: got {got!r}, frozen value is {want!r}")

    # 5. model policy (the user's decision, encoded)
    pol = doc.get("model_policy") or {}
    if pol.get("primary") != POLICY_PRIMARY:
        _err(out, "MRC-POLICY-PRIMARY", f"primary must be {POLICY_PRIMARY!r}, got {pol.get('primary')!r}")
    excluded = {str(x).lower() for x in (pol.get("excluded_providers") or [])}
    for must in POLICY_EXCLUDED:
        if must not in excluded:
            _err(out, "MRC-POLICY-EXCLUDED", f"{must!r} must appear in excluded_providers")
    if pol.get("mixed_secondary_allowed") is not True:
        _err(out, "MRC-POLICY-EXCLUDED", "mixed_secondary_allowed must be true (deepseek-v4-pro permitted)")
    for allowed in pol.get("permitted_secondary") or []:
        if allowed not in POLICY_PERMITTED_SECONDARY:
            _err(out, "MRC-POLICY-SECONDARY", f"permitted secondary {allowed!r} is not on the user's list")

    # 6. task snapshot must name the frozen evaluator identity
    snap = components["TaskSnapshot"]
    if expect_eid and snap.get("eid_star") != expect_eid:
        _err(out, "MRC-EID-DRIFT", f"TaskSnapshot.eid_star is {snap.get('eid_star')!r}, expected {expect_eid!r}")

    rt = components["RuntimeAdapters"]
    adapters = rt.get("adapters") if isinstance(rt, dict) else None
    if not isinstance(adapters, list) or not adapters:
        _err(out, "MRC-ADAPTER-MISSING", "RuntimeAdapters.adapters must be a non-empty list")
    else:
        for i, a in enumerate(adapters):
            if not isinstance(a, dict) or not a.get("runtime") or not a.get("adapter_commit"):
                _err(out, "MRC-ADAPTER-MISSING", f"adapters[{i}] lacks runtime/adapter_commit")
                continue
            check_adapter_preimage(a, i, out)

    return out


def check_adapter_preimage(adapter: dict, i: int, out: list) -> None:
    """A declared adapter digest must be the digest of a declared preimage.

    A ``null`` digest is admissible only with a stated reason, which
    ``check_null_digests`` already enforces; anything else must name the bytes.
    """
    runtime = adapter.get("runtime")
    recorded = adapter.get("adapter_source_sha256")
    if recorded is None:
        return
    if not adapter.get("adapter_source_root"):
        _err(out, "MRC-ADAPTER-PREIMAGE",
             f"adapters[{i}] ({runtime}): adapter_source_sha256 declared with no adapter_source_root")
        return
    try:
        recomputed = adapter_source_digest(adapter.get("adapter_source_files"))
    except MRCError as exc:
        _err(out, "MRC-ADAPTER-PREIMAGE",
             f"adapters[{i}] ({runtime}): adapter_source_sha256 declared with no usable preimage: {exc}")
        return
    if recorded != recomputed:
        _err(out, "MRC-ADAPTER-DIGEST",
             f"adapters[{i}] ({runtime}): adapter_source_sha256={recorded} is not the digest of "
             f"the listed preimage ({recomputed})")
    if not adapter.get("adapter_source_rule"):
        _err(out, "MRC-ADAPTER-PREIMAGE",
             f"adapters[{i}] ({runtime}): adapter_source_sha256 declared with no adapter_source_rule")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _cmd_compute(args) -> int:
    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    doc = build_mrc(spec)
    out = Path(args.out) if args.out else spec_path.with_suffix(".mrc.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MRC* = {doc['mrc_star']}")
    for name in COMPONENTS:
        print(f"  {name:<16} {doc['component_digests'][name]}")
    print(f"written: {out}")
    return 0


def _cmd_recompute(args) -> int:
    doc = json.loads(Path(args.mrc_file).read_text(encoding="utf-8"))
    recomputed = recompute_from_records(doc)
    ok = True
    for name in COMPONENTS:
        rec = (doc.get("component_digests") or {}).get(name)
        got = recomputed["component_digests"][name]
        flag = "ok " if rec == got else "BAD"
        ok &= rec == got
        print(f"  [{flag}] {name:<16} recorded={str(rec)[:16]} recomputed={got[:16]}")
    flag = "ok " if doc.get("mrc_star") == recomputed["mrc_star"] else "BAD"
    ok &= doc.get("mrc_star") == recomputed["mrc_star"]
    print(f"  [{flag}] MRC*             recorded={str(doc.get('mrc_star'))[:16]} "
          f"recomputed={recomputed['mrc_star'][:16]}")
    return 0 if ok else 1


def _cmd_validate(args) -> int:
    doc = json.loads(Path(args.mrc_file).read_text(encoding="utf-8"))
    frozen = load_frozen(Path(args.frozen)) if args.frozen else None
    problems = validate(doc, frozen)
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    print(f"valid: route={doc['route_id']} MRC* = {doc['mrc_star']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mrc", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("compute", help="hash a declaration spec and write the MRC* document")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=_cmd_compute)

    p = sub.add_parser("recompute", help="recompute MRC* from the recorded payloads only")
    p.add_argument("--mrc-file", required=True)
    p.set_defaults(fn=_cmd_recompute)

    p = sub.add_parser("validate", help="check digests, hygiene, identity evidence, and the frozen registry")
    p.add_argument("--mrc-file", required=True)
    p.add_argument("--frozen", default=None,
                   help="frozen route registry; when given, provider/endpoint/model drift fails")
    p.set_defaults(fn=_cmd_validate)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except MRCError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
