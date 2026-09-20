"""`EID_r -> EID*` for SimpleLoop, and the EID* checks the adapter must run first.

SimpleLoop has no native evaluator identity at all, so per adapter_contract.md §5.2
its `native_scheme` is `none` and its `mapping_mode` is
`adapter_declared_injection`: the adapter is the sole source of the evaluator
identity. That is only a claim until it is checkable, so the adapter

  1. reads `eid_star` out of the EID*.json document and re-runs
     `evalcontract.py verify` against the spec before the run (exit 3 on drift);
  2. re-hashes the evaluator source files the document recorded and compares them
     with the bytes it is about to execute (exit 3 on drift);
  3. derives a recomputable `EID_r` value from those two facts plus the frozen
     SimpleLoop policy digest.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .policy import canonical_bytes

EID_R_SCHEMA = "a0/simpleloop/eid_r/v1"
EID_R_DOMAIN = "a0/simpleloop/eid_r/v1"
EID_R_DECLARATION = (
    "SimpleLoop has no native evaluator identity (adapter_contract.md §5.2: native_scheme=none). "
    "The adapter pins EID* and is the sole source of the identity. EID_r.value is "
    "sha256(\"a0/simpleloop/eid_r/v1\" + 0x00 + canonical_json(payload)) with payload = "
    "{schema, eid_star, evaluator_source_records, policy_digest} — the same domain-separated "
    "construction a0/contract/evalcontract.py uses for its own components. A third party "
    "recomputes it from EID*.json, a0/tasks/circle-packing/{e_star.py,e_star_child.py} and "
    "a0/runtimes/simpleloop/policy/simpleloop.policy.json alone, without running this adapter: "
    "a0/runtimes/simpleloop/tools/recompute-eid-r prints the payload and the digest, and the "
    "adapter publishes the same (domain, payload_canonical) pair in its conformance document. "
    "It changes iff EID*, the evaluator bytes, or the frozen selection/scalarization policy "
    "changes."
)


class EidError(RuntimeError):
    """EID*.json does not describe what is actually wired -> adapter exit 3."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def eid_r_payload(*, eid_star: str, source_records: list[dict], policy: dict) -> dict:
    """The canonical payload EID_r is derived from (published, so it can be recomputed)."""
    return {
        "schema": EID_R_SCHEMA,
        "eid_star": eid_star,
        "evaluator_source_records": [
            {"path": r["path"], "sha256": r["sha256"]} for r in source_records
        ],
        "policy_digest": hashlib.sha256(canonical_bytes(policy)).hexdigest(),
    }


def derive_eid_r(*, eid_star: str, source_records: list[dict], policy: dict) -> str:
    """`sha256(domain || 0x00 || canonical_json(payload))`.

    Domain separation is not decoration: without it a digest over this payload could
    collide with a digest over a different object that happens to serialize the same
    way, which is why a0/contract/evalcontract.py separates its components the same
    way. The declared formula in EID_R_DECLARATION is this line, character for
    character — `tools/recompute-eid-r` recomputes it without importing this module,
    and the A0 conformance runner recomputes it from the published (domain, payload).
    """
    payload = eid_r_payload(eid_star=eid_star, source_records=source_records, policy=policy)
    return hashlib.sha256(
        EID_R_DOMAIN.encode("ascii") + b"\x00" + canonical_bytes(payload)
    ).hexdigest()


def eid_r_derivation(*, eid_star: str, source_records: list[dict], policy: dict) -> dict:
    """The machine-checkable half of `recomputable: true`.

    `(domain, payload_canonical)` is everything a third party needs to recompute
    `value` with their own sha256 and no code of ours.
    """
    payload = eid_r_payload(eid_star=eid_star, source_records=source_records, policy=policy)
    return {
        "algorithm": "sha256(domain || 0x00 || canonical_json(payload))",
        "domain": EID_R_DOMAIN,
        "payload": payload,
        "payload_canonical": canonical_bytes(payload).decode("ascii"),
    }


@dataclass
class EidContext:
    document: dict
    eid_star: str
    document_path: Path
    spec_path: Path | None
    epsilon: float
    primary_field: str | None
    source_records: list[dict]
    evaluator_source_digest: str | None
    verify_stdout: str
    verify_returncode: int
    recompute_stdout: str
    recompute_returncode: int

    def eid_r(self, policy: dict) -> dict:
        return {
            # Bare 64-hex, the same format `eid_star` itself uses and the format
            # evalcontract.py prints for its components. A `sha256:` prefix would be
            # a display choice that a third party's own recomputation cannot guess,
            # and the whole point of `recomputable: true` is that they recompute the
            # value from the published (domain, payload) without asking us.
            "value": derive_eid_r(
                eid_star=self.eid_star,
                source_records=self.source_records,
                policy=policy,
            ),
            "native_scheme": "none",
            "mapping_mode": "adapter_declared_injection",
            "derives_from_eid_star": self.eid_star,
            "declaration": EID_R_DECLARATION,
            "recomputable": True,
        }


def _config_value(document: dict, *keys, default=None):
    node = document
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def load_eid(
    document_path: Path,
    *,
    spec_path: Path | None,
    evalcontract_py: Path,
    python: Path,
    work_root: Path,
) -> EidContext:
    document_path = Path(document_path).resolve()
    if not document_path.is_file():
        raise EidError(f"EID document not found: {document_path}")
    with document_path.open("r", encoding="utf-8") as fh:
        document = json.load(fh)
    eid_star = document.get("eid_star")
    if not isinstance(eid_star, str) or len(eid_star) != 64:
        raise EidError(f"EID document carries no usable eid_star: {eid_star!r}")

    verify_stdout = verify_rc = None
    if spec_path is not None:
        proc = subprocess.run(
            [str(python), str(evalcontract_py), "verify",
             "--eid-file", str(document_path), "--spec", str(spec_path.resolve())],
            capture_output=True, text=True, cwd=str(work_root),
        )
        verify_stdout, verify_rc = (proc.stdout or "") + (proc.stderr or ""), proc.returncode
        if proc.returncode != 0:
            raise EidError(
                f"evalcontract.py verify reported drift against {spec_path.name}: "
                f"{verify_stdout.strip()}"
            )
    else:
        verify_stdout, verify_rc = "verify skipped: no --eid-spec given", -1

    proc = subprocess.run(
        [str(python), str(evalcontract_py), "recompute", "--eid-file", str(document_path)],
        capture_output=True, text=True, cwd=str(work_root),
    )
    recompute_stdout, recompute_rc = (proc.stdout or "") + (proc.stderr or ""), proc.returncode
    if proc.returncode != 0:
        raise EidError(f"evalcontract.py recompute failed: {recompute_stdout.strip()}")

    epsilon = _config_value(
        document, "components", "Config", "value", "conformance", "epsilon", "value"
    )
    if epsilon is None:
        epsilon = _config_value(
            document, "components", "Config", "canonical_material", "value",
            "conformance", "epsilon", "value", 1e-9,
        )
    primary = _config_value(document, "components", "MetricDefinition", "metric_name")
    if primary is None:
        primary = _config_value(document, "components", "MetricDefinition", "value", "name")

    source_records = list(
        _config_value(document, "components", "EvaluatorSource", "records", default=[]) or []
    )
    evaluator_source_digest = _config_value(
        document, "components", "EvaluatorSource", "digest"
    )
    if not source_records:
        raise EidError(
            "EID* document records no EvaluatorSource files; the adapter cannot prove that the "
            "evaluator it is about to run is the frozen one"
        )
    return EidContext(
        document=document,
        eid_star=eid_star,
        document_path=document_path,
        spec_path=Path(spec_path).resolve() if spec_path else None,
        epsilon=float(epsilon),
        primary_field=primary,
        source_records=source_records,
        evaluator_source_digest=evaluator_source_digest,
        verify_stdout=verify_stdout,
        verify_returncode=verify_rc,
        recompute_stdout=recompute_stdout,
        recompute_returncode=recompute_rc,
    )
