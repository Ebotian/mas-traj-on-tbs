#!/usr/bin/env python3
"""The A0.1 measurement envelope: behaviour/execution-environment split, and the measurement token.

Two jobs, both defined here so that the harness (`a0/conformance/conformance.py`) and a runtime
adapter computing the same value cannot drift apart:

**1. The projection (external review D1).** `E*`'s own `canonical_digest` (frozen in
`a0/tasks/circle-packing/e_star.py:654`) hashes the whole Outcome payload, `interpreter` included,
so the same bytes of `E*` under a different interpreter build produce a different digest while
producing the same behaviour (`delta = 0.0` on every row of `C*`). This module separates the two
surfaces that digest conflates:

* `behaviour_digest(outcome)` — a domain-separated digest over the Outcome payload **minus**
  `canonical_digest` and minus `interpreter`: the part of the payload that is `E*`'s *behaviour*.
* `digest_with_interpreter(outcome, interpreter)` — `E*`'s own digest scheme, recomputed with a
  substituted `interpreter` block. This is what lets the checker split behaviour from environment
  for an adapter row that carries only a `canonical_digest` (no payload): if the row's digest equals
  the frozen payload's digest recomputed under some declared interpreter, then the *only* thing
  that differs is the execution environment.

`EXECUTION_ENV_DRIFT` (sanctioned interpreter) and `MISMATCH_EXECUTION_ENV` (interpreter outside the
declared allowed set) are the two verdicts this produces; neither is "`E*`'s behaviour disagrees".
The allowed set is declared in `a0/envelope/execution-set.json`; see README.md for the coupling
question (folding that set into `EID*`'s `Config` would be a re-freeze — undecided, not decided
here).

**2. The measurement token (external review D3).** Per candidate, the harness issues an opaque,
domain-separated id

    OID = sha256("a0.envelope.measurement_token/v1" \\0 canonical_json(binding))
    binding = {candidate_id, candidate_sha256, eid_star, theta_e, behaviour_digest,
               canonical_digest, interpreter, evaluator_source_sha256, harness_run_id, nonce}

into its own state root. An adapter row is acceptable only if it echoes that OID for that candidate
*and* attests the evaluator bytes it executed and the candidate bytes it read. Omission is
non-accepting (fail-closed), never a silent pass.

The canonicalisation is `E*`'s own (`json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True)`
plus a trailing newline, `e_star.py:109`); `selftest.py` proves this function reproduces the frozen
table's `canonical_digest` for all 14 members of `C*` before anything relies on it.

Standard library only, no imports from the rest of the tree, so any adapter can vendor-call it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA_ENVELOPE = "a0.envelope/v1"
SCHEMA_TOKEN = "a0.envelope.measurement_token/v1"
SCHEMA_ATTESTATION = "a0.envelope.measurement_attestation/v1"

DOMAIN_BEHAVIOUR = "a0.envelope.behaviour/v1"
DOMAIN_TOKEN = "a0.envelope.measurement_token/v1"

# The two keys `E*`'s canonical_digest covers that are not behaviour: the digest itself, and the
# execution environment it was produced in. Everything else in the Outcome is behaviour.
BEHAVIOUR_EXCLUDED_KEYS = ("canonical_digest", "interpreter")

# `E*`'s own source-file set (e_star.py:70), for `evaluator_source_digest()`.
E_STAR_SOURCE_FILES = ("e_star.py", "e_star_child.py")

EXECUTION_SET_PATH = Path(__file__).resolve().parent / "execution-set.json"

# verdict codes (the checker's, not the adapter's)
ENV_PINNED = "PINNED"
ENV_SANCTIONED = "SANCTIONED"
ENV_UNSANCTIONED = "UNSANCTIONED"
ENV_UNKNOWN = "UNKNOWN"

EXECUTION_ENV_DRIFT = "EXECUTION_ENV_DRIFT"
MISMATCH_EXECUTION_ENV = "MISMATCH_EXECUTION_ENV"

ATTESTATION_OK = "OK"
MISSING_ATTESTATION = "MISSING_ATTESTATION"
MISMATCH_ATTESTATION = "MISMATCH_ATTESTATION"
MISSING_IDENTITY = "MISSING_IDENTITY"

#: verdicts that carry no disagreement with `E*`'s behaviour; the checker adds
#: `EXECUTION_ENV_DRIFT` to its accepting set, `MISMATCH_EXECUTION_ENV` is not accepting.
ACCEPTING_ENV_VERDICTS = (ENV_PINNED, EXECUTION_ENV_DRIFT)


# --------------------------------------------------------------------------------------
# canonicalisation (E*'s own)
# --------------------------------------------------------------------------------------

def canonical_json_bytes(payload) -> bytes:
    """`E*`'s canonical byte form: `json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True) + "\\n"`.

    Reproducing this exactly is what makes `digest_with_interpreter` comparable with the
    `canonical_digest` an adapter reports; `selftest.py` checks it against the frozen table.
    """
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_canonical_json(payload) -> bytes:
    """The contract-side canonical form (`a0/contract/evalcontract.py`): compact, ASCII, sorted."""
    def stringify(obj):
        if isinstance(obj, dict):
            return {str(k): stringify(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [stringify(v) for v in obj]
        return obj

    return json.dumps(
        stringify(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluator_source_digest(script_dir) -> str:
    """`E*`'s own `evaluator_source_sha256` (`e_star.py:122`), recomputed from bytes on disk."""
    entries = []
    for name in E_STAR_SOURCE_FILES:
        data = (Path(script_dir) / name).read_bytes()
        entries.append({"name": name, "sha256": sha256_hex(data), "bytes": len(data)})
    return sha256_hex(canonical_json_bytes(entries))


# --------------------------------------------------------------------------------------
# the projection
# --------------------------------------------------------------------------------------

def interpreter_of(outcome: dict) -> dict | None:
    block = (outcome or {}).get("interpreter")
    return block if isinstance(block, dict) else None


def behaviour_payload(outcome: dict) -> dict:
    """The Outcome minus the digest and minus the execution environment."""
    return {k: v for k, v in (outcome or {}).items() if k not in BEHAVIOUR_EXCLUDED_KEYS}


def behaviour_digest(outcome: dict) -> str:
    """Domain-separated digest over the behaviour payload.

    Domain-separated so that the value can never be confused with `E*`'s `canonical_digest`, which
    it deliberately is not: it is the same for a byte-identical `E*` run under any interpreter.
    """
    return sha256_hex(DOMAIN_BEHAVIOUR.encode("ascii") + b"\x00" + canonical_json_bytes(behaviour_payload(outcome)))


def digest_with_interpreter(outcome: dict, interpreter: dict) -> str:
    """`E*`'s `canonical_digest` for this payload if it had been produced under `interpreter`.

    It is `E*`'s *own* digest scheme (unprefixed sha256 over the whole payload minus
    `canonical_digest`), because the value it is compared against is an adapter's `canonical_digest`.
    """
    payload = {k: v for k, v in (outcome or {}).items() if k != "canonical_digest"}
    payload["interpreter"] = interpreter
    return sha256_hex(canonical_json_bytes(payload))


def outcome_digest(outcome: dict) -> str:
    """`E*`'s `canonical_digest` for a payload whose `interpreter` block is its own."""
    payload = {k: v for k, v in (outcome or {}).items() if k != "canonical_digest"}
    return sha256_hex(canonical_json_bytes(payload))


# --------------------------------------------------------------------------------------
# the declared allowed execution set
# --------------------------------------------------------------------------------------

def load_execution_set(path=None) -> dict:
    document = json.loads(Path(path or EXECUTION_SET_PATH).read_text())
    document["_path"] = str(path or EXECUTION_SET_PATH)
    return document


def interpreter_blocks(execution_set: dict) -> list:
    blocks = []
    pinned = execution_set.get("pinned")
    if isinstance(pinned, dict) and pinned.get("version"):
        blocks.append({"implementation": pinned.get("implementation", "cpython"),
                       "version": pinned["version"]})
    for entry in execution_set.get("sanctioned") or []:
        if isinstance(entry, dict) and entry.get("version"):
            block = {"implementation": entry.get("implementation", "cpython"), "version": entry["version"]}
            if block not in blocks:
                blocks.append(block)
    return blocks


def normalise_interpreter(interpreter) -> dict | None:
    """Accept `{"implementation","version"}` or a bare version string."""
    if isinstance(interpreter, dict):
        version = interpreter.get("version")
        if not version:
            return None
        return {"implementation": interpreter.get("implementation", "cpython"), "version": str(version)}
    if isinstance(interpreter, str) and interpreter:
        return {"implementation": "cpython", "version": interpreter}
    return None


def classify_interpreter(interpreter, execution_set: dict) -> dict:
    """Where an interpreter block sits relative to the declared allowed execution set.

    `pinned` — the interpreter `E_STAR.json` was measured under (the frozen execution environment).
    `sanctioned` — declared equivalent: measured to produce the same behaviour payload over `C*`.
    `unsanctioned` — a real interpreter outside the declared set.
    `unknown` — nothing to classify (the row declared no interpreter and none could be inferred).
    """
    observed = normalise_interpreter(interpreter)
    pinned = normalise_interpreter(execution_set.get("pinned"))
    allowed = interpreter_blocks(execution_set)
    if observed is None:
        return {"status": ENV_UNKNOWN, "observed": None, "pinned": pinned,
                "allowed": allowed}
    if pinned is not None and observed == pinned:
        return {"status": ENV_PINNED, "observed": observed, "pinned": pinned, "allowed": allowed}
    if observed in allowed:
        entry = next(
            (e for e in (execution_set.get("sanctioned") or [])
             if normalise_interpreter(e) == observed),
            {},
        )
        return {"status": ENV_SANCTIONED, "observed": observed, "pinned": pinned, "allowed": allowed,
                "evidence": entry.get("evidence"), "sanctioned_on": entry.get("measured_on")}
    return {"status": ENV_UNSANCTIONED, "observed": observed, "pinned": pinned, "allowed": allowed}


def behaviour_env_verdict(behaviour_matches: bool, interpreter_class: dict) -> tuple:
    """The D1 verdict for one row, from (does behaviour agree?) x (where did it run?).

    Returns `(verdict, accepting)`. A behaviour mismatch is always `MISMATCH_DIGEST` — the projection
    never rescues a different evaluator; a behaviour match under a drifted interpreter is an
    *environment* verdict, never a behaviour one.
    """
    if not behaviour_matches:
        return "MISMATCH_DIGEST", False
    status = (interpreter_class or {}).get("status")
    if status == ENV_PINNED:
        return ENV_PINNED, True
    if status == ENV_SANCTIONED:
        return EXECUTION_ENV_DRIFT, True
    return MISMATCH_EXECUTION_ENV, False


# --------------------------------------------------------------------------------------
# the measurement token
# --------------------------------------------------------------------------------------

def token_binding(*, candidate_id, candidate_sha256, eid_star, theta_e, behaviour_digest_value,
                  canonical_digest, interpreter, evaluator_source_sha256, harness_run_id, nonce) -> dict:
    return {
        "candidate_id": candidate_id,
        "candidate_sha256": candidate_sha256,
        "eid_star": eid_star,
        "theta_e": theta_e,
        "behaviour_digest": behaviour_digest_value,
        "canonical_digest": canonical_digest,
        "interpreter": normalise_interpreter(interpreter),
        "evaluator_source_sha256": evaluator_source_sha256,
        "harness_run_id": harness_run_id,
        "nonce": nonce,
    }


def token_oid(binding: dict) -> str:
    """The opaque measurement id: domain-separated sha256 over the canonical binding."""
    return sha256_hex(DOMAIN_TOKEN.encode("ascii") + b"\x00" + compact_canonical_json(binding))


def issue_envelope(*, eid_star, theta_e, evaluator, execution_set, harness_run_id, nonce,
                   candidates, envelope_path=None, issued_at=None) -> dict:
    """Build the envelope document from the harness's own reference sweep.

    `candidates` is a list of mappings with at least `candidate_id`, `source_sha256` (measured by
    the harness), `behaviour_digest`, `canonical_digest` and `interpreter`.
    """
    tokens = {}
    for entry in candidates:
        binding = token_binding(
            candidate_id=entry["candidate_id"],
            candidate_sha256=entry.get("source_sha256") or entry.get("candidate_sha256"),
            eid_star=eid_star,
            theta_e=theta_e,
            behaviour_digest_value=entry["behaviour_digest"],
            canonical_digest=entry.get("canonical_digest"),
            interpreter=entry.get("interpreter"),
            evaluator_source_sha256=evaluator.get("evaluator_source_sha256"),
            harness_run_id=harness_run_id,
            nonce=nonce,
        )
        tokens[entry["candidate_id"]] = {
            "oid": token_oid(binding),
            "binding": binding,
            "manifest_solution_sha256": entry.get("manifest_solution_sha256"),
        }
    interpreter_class = classify_interpreter(evaluator.get("interpreter"), execution_set)
    return {
        "schema": SCHEMA_ENVELOPE,
        "issued_at": issued_at,
        "issued_by": "a0/conformance/conformance.py reference sweep",
        "harness_run_id": harness_run_id,
        "nonce": nonce,
        "eid_star": eid_star,
        "theta_e": theta_e,
        "evaluator": dict(evaluator),
        "execution_set": {
            "path": execution_set.get("_path"),
            "sha256": sha256_hex(compact_canonical_json(
                {k: v for k, v in execution_set.items() if k != "_path"})),
            "pinned": execution_set.get("pinned"),
            "sanctioned": execution_set.get("sanctioned"),
        },
        "harness_execution_env": interpreter_class,
        "candidate_count": len(tokens),
        "candidates": tokens,
        "verification": {
            "oid": 'sha256("a0.envelope.measurement_token/v1" 0x00 canonical_json(binding))',
            "binding_fields": sorted(next(iter(tokens.values()))["binding"]) if tokens else [],
            "rule": (
                "a row is acceptable only if it echoes this OID for its candidate and attests the "
                "evaluator source digest, the candidate bytes, the theta_E and the behaviour digest it "
                "produced; a row that omits the token or the identity fields is non-accepting "
                "(MISSING_ATTESTATION / MISSING_IDENTITY), never a silent pass"
            ),
        },
        "path": str(envelope_path) if envelope_path else None,
    }


def load_envelope(path) -> dict:
    document = json.loads(Path(path).read_text())
    document["_path"] = str(path)
    return document


def token_for(envelope: dict, candidate_id: str) -> dict | None:
    return ((envelope or {}).get("candidates") or {}).get(candidate_id)


def envelope_sha256(envelope: dict) -> str:
    return sha256_hex(compact_canonical_json({k: v for k, v in envelope.items() if k not in ("_path", "path")}))
