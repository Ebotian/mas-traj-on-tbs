"""`EID_r -> EID*` for EvE, as a derivation rather than a self-consistency check.

EvE has no native evaluator identity (`adapter_contract.md` §5.2: `native_scheme = none`,
`mapping_mode = adapter_declared_injection`), so the adapter is the sole source of the
identity. An earlier revision of this adapter made `EID_r.value` the sha256 of the
evaluation step script it had itself generated: the value recomputed, but nothing in that
recomputation *derived* it from `EID*` — a step that ignored `EID*` entirely would have
recomputed just as well (audit `verify/VERDICT.md` R3). This module replaces that with a
domain-separated hash **whose payload has `eid_star` as an argument**, so

  * a different `EID*` necessarily yields a different `EID_r` (verified by mutation,
    `tools/recompute-eid-r --eid <mutated EID document>`), and
  * a third party can recompute `value` from published files alone, without importing this
    module (`tools/recompute-eid-r` does exactly that).

The payload is deliberately *run-invariant*: it names the evaluator (`EID*` and the bytes of
the `E*` files EvE actually invokes) and the frozen scalarization declaration, not the
rendered step script — that script embeds the run's absolute paths, so hashing it would make
`EID_r` a per-run-directory value instead of an evaluator identity. The rendered step's own
provenance is published next to `EID_r` in the conformance document (`injected_step`) and is
checked by execution, not by the hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import common

EID_R_SCHEMA = "a0/eve/eid_r/v1"
EID_R_DOMAIN = "a0/eve/eid_r/v1"
EID_R_VALUE_PREFIX = "sha256:"
EID_R_ALGORITHM = (
    "value = 'sha256:' + sha256(\"a0/eve/eid_r/v1\" || 0x00 || canonical_json(payload)); "
    "canonical_json = json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True, "
    "allow_nan=False) encoded ascii (a0/contract/evalcontract.py::canonical_json)"
)
EID_R_DECLARATION = (
    "EvE has no native evaluator identity (native_scheme=none): the evaluator is whichever "
    "shell step evaluation.steps names, and EvE hands that step exactly EVE_WORKSPACE_ROOT, "
    "EVE_SOLVER_ROOT, EVE_EVAL_LOG_ROOT and PYTHONDONTWRITEBYTECODE and no evaluator "
    "parameters (workflow/evaluation.py:290-318). The adapter pins EID* by overriding "
    "evaluation.steps with a generated step that invokes the frozen E* by absolute path and "
    "writes EID* and PINS_SHA256 into the log root it is handed. EID_r.value = 'sha256:' + "
    "sha256(\"a0/eve/eid_r/v1\" || 0x00 || canonical_json(payload)) with payload = "
    "{schema, eid_star, native_scheme, mapping_mode, evaluator_source{digest,files}, "
    "fr_spec_hash}: eid_star is an argument of the hash, so a different EID* necessarily "
    "gives a different EID_r. Recompute from the published inputs alone with "
    "runtimes/eve/tools/recompute-eid-r (recipe: eid_r.derivation in the conformance document)."
)


class EidMappingError(RuntimeError):
    """The bytes EvE is about to run are not the bytes EID* names -> adapter exit 3."""


def canonical_bytes(value: Any) -> bytes:
    """Same canonicalization as `a0/contract/evalcontract.py::canonical_json`."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def source_records(eid_document: dict[str, Any], *, a0_root: Path | None = None) -> list[dict[str, str]]:
    """The `E*` files `EID*` names, re-hashed from the bytes on disk.

    `EID*`'s `EvaluatorSource` component records `(path, sha256)` for the evaluator program.
    Re-hashing the files here is what ties the identity to what EvE will actually invoke: if
    the file changed, the adapter aborts instead of deriving an `EID_r` over stale bytes.
    """
    root = a0_root or common.A0_ROOT
    component = (eid_document.get("components") or {}).get("EvaluatorSource") or {}
    rel_root = str(component.get("root") or "").strip("/")
    records: list[dict[str, str]] = []
    for record in component.get("records") or []:
        rel = f"{rel_root}/{record['path']}" if rel_root else str(record["path"])
        path = Path(root) / rel
        try:
            actual = common.sha256_file(path)
        except OSError as exc:
            raise EidMappingError(f"evaluator source {rel} is unreadable: {exc}") from exc
        if actual != record.get("sha256"):
            raise EidMappingError(
                f"evaluator source {rel} hashes to {actual}, but EID*'s EvaluatorSource "
                f"records {record.get('sha256')}: refusing to derive EID_r over bytes the "
                f"frozen evaluator identity does not name"
            )
        records.append({"path": rel, "sha256": actual})
    if not records:
        raise EidMappingError("EID* document carries no EvaluatorSource records")
    records.sort(key=lambda item: item["path"])
    return records


@dataclass(frozen=True)
class EidInputs:
    """Everything `EID_r` is derived from. Published, so it can be recomputed."""

    eid_star: str
    source_records: list[dict[str, str]]
    source_digest: str
    fr_spec_hash: str


def inputs_from_contract(
    *,
    eid_document: dict[str, Any],
    fr_spec_hash: str,
    a0_root: Path | None = None,
) -> EidInputs:
    eid_star = eid_document.get("eid_star")
    if not isinstance(eid_star, str) or len(eid_star) != 64:
        raise EidMappingError(f"EID document has no 64-hex eid_star: {eid_star!r}")
    component = (eid_document.get("components") or {}).get("EvaluatorSource") or {}
    digest = component.get("digest")
    if not isinstance(digest, str) or not digest:
        raise EidMappingError("EID* document carries no EvaluatorSource digest")
    return EidInputs(
        eid_star=eid_star,
        source_records=source_records(eid_document, a0_root=a0_root),
        source_digest=digest,
        fr_spec_hash=fr_spec_hash,
    )


def eid_r_payload(inputs: EidInputs) -> dict[str, Any]:
    """The canonical payload `EID_r` is derived from (published in full)."""
    return {
        "schema": EID_R_SCHEMA,
        "eid_star": inputs.eid_star,
        "native_scheme": "none",
        "mapping_mode": "adapter_declared_injection",
        "evaluator_source": {
            "digest": inputs.source_digest,
            "files": [dict(record) for record in inputs.source_records],
        },
        "fr_spec_hash": inputs.fr_spec_hash,
    }


def derive_eid_r(inputs: EidInputs) -> str:
    """`'sha256:' + sha256(domain || 0x00 || canonical_json(payload))`.

    Domain separation is not decoration: without it this digest could collide with a digest
    over a different object that happens to serialize the same way, which is why
    `a0/contract/evalcontract.py` separates its own components the same way. The formula in
    `EID_R_DECLARATION` is this line, and `tools/recompute-eid-r` recomputes it without
    importing this module.
    """
    payload = eid_r_payload(inputs)
    digest = hashlib.sha256(
        EID_R_DOMAIN.encode("ascii") + b"\x00" + canonical_bytes(payload)
    ).hexdigest()
    return f"{EID_R_VALUE_PREFIX}{digest}"


def eid_r_derivation(inputs: EidInputs) -> dict[str, Any]:
    """The machine-checkable half of `recomputable: true` (`domain`, `payload_canonical`)."""
    payload = eid_r_payload(inputs)
    return {
        "algorithm": EID_R_ALGORITHM,
        "domain": EID_R_DOMAIN,
        "value": derive_eid_r(inputs),
        "payload": payload,
        "payload_canonical": canonical_bytes(payload).decode("ascii"),
        "inputs_source": {
            "eid_star": "eid_star field of the EID* document",
            "evaluator_source": (
                "components.EvaluatorSource of the EID* document, re-hashed from "
                "a0/tasks/circle-packing/{e_star.py,e_star_child.py} and compared before use"
            ),
            "fr_spec_hash": "canonical_file_digest of a0/contract/fr/scalar.json",
        },
        "recompute_without_this_adapter": (
            "runtimes/eve/tools/recompute-eid-r --eid <EID document> --fr "
            "contract/fr/scalar.json --a0-root a0"
        ),
    }
