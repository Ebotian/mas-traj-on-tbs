#!/usr/bin/env python3
"""Shared pieces of the A0 execution/load attestation.

The identity scheme of the execution attestation is defined here and used by
`attest.py` (producer), `selftest.py` and `demo.py`.  `verify_attestation.py`
deliberately does **not** import this module: a verifier that shares the
producer's serializer cannot detect a bug in it.  `selftest.py` checks that the
two independently written canonicalizers agree.

Scheme (`a0/attestation/v1`):

    EID_semantic  = the frozen five-component EID* of the study, recomputed at
                    run time from the inputs actually present on disk
    EID_execution = domain_digest("a0/attestation/v1/EID_execution",
                                  canonical_json(payload))

`payload` is the identity-bearing subset of the attestation: the semantic
identity, what was invoked, what the interpreter loaded and executed, the
runtime and dependency environment, the environment variables that can change
behaviour, and the candidate bytes actually evaluated.  Volatile observations
(timings, process ids, temporary paths, audit counts) are kept out of the
payload so that two identical clean runs at the same paths produce the *same*
EID_execution -- that is what makes it an identity rather than a run id.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA_ATTESTATION = "a0.attestation/v1"
SCHEMA_PAYLOAD = "a0.attestation.payload/v1"
DOMAIN = "a0/attestation/v1"
FROZEN_EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"

COMPONENTS = (
    "EvaluatorSource",
    "DependencyLock",
    "DataManifest",
    "Config",
    "MetricDefinition",
)

# The review's literal four-component split.  Carried for traceability; the
# authoritative semantic identity of this study is the frozen five-component
# EID* (see FIELDS.md, "Reconciliation with the review's split").
REVIEW_FOUR = ("EvaluatorSource", "DataManifest", "Config", "MetricDefinition")


class AttestError(Exception):
    """Raised when an attestation cannot be produced faithfully."""


def canonical_json(obj) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


def domain_digest(domain: str, payload: bytes) -> str:
    return sha256_bytes(domain.encode("ascii") + b"\x00" + payload)


def eid_execution(payload: dict) -> str:
    return domain_digest(f"{DOMAIN}/EID_execution", canonical_json(payload))


def review_formula_semantic(component_digests: dict) -> str:
    """`H(Source, Data, Config, Metric)` exactly as the review wrote it."""
    return domain_digest(
        f"{DOMAIN}/EID_semantic_4c",
        canonical_json({name: component_digests[name] for name in REVIEW_FOUR}),
    )


def rel_to(path, root) -> str:
    """Repo-relative POSIX path when possible, else the path text itself."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def fresh_compile_digest(source_path) -> str | None:
    """Digest of compiling the current bytes at `source_path`.

    Computed in this interpreter, so it is only comparable to a captured
    `loaded_code_sha256` when the two interpreters are the same build; callers
    check that and record `null` otherwise.
    """
    import marshal

    try:
        source = Path(source_path).read_bytes()
    except OSError:
        return None
    try:
        code = compile(source, str(source_path), "exec", dont_inherit=True)
    except (SyntaxError, ValueError):
        return None
    return sha256_bytes(marshal.dumps(code))


def is_under(path: str, prefix: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(prefix).resolve())
        return True
    except (ValueError, OSError):
        return False
