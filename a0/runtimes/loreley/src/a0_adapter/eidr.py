"""``EID_r -> EID*``: Loreley's native evaluator identity and its derivation.

Loreley's native identity is ``evaluator_name + version + campaign_program_hash``
(protocol §4.2.1, ``plan:507``; ``adapter_contract.md`` §5.2).  Concretely, in the
pinned checkout:

* ``evaluator_name``   - ``Evaluator._evaluator_label()`` returns ``plugin_ref``,
  i.e. whatever ``WORKER_EVALUATOR_PLUGIN`` names
  (``loreley/core/worker/evaluator.py:1481-1485``, ``:1793-1796``).
* ``evaluator_version`` - ``evaluator_identity_version`` resolves an explicit
  ``WORKER_EVALUATOR_VERSION`` first, then the distribution version, then a
  source fingerprint of the plugin module
  (``loreley/core/worker/evaluator_identity.py:16-36``, ``:90-105``).
* ``campaign_program_hash`` - the raw sha256 of ``loreley.program.md``
  (``loreley/core/campaign_program.py:125-126``, ``:212``).

The adapter makes the derivation from ``EID*`` real rather than nominal by
**generating** the campaign program from the frozen ``EID*`` document and then
recording the resulting triple.  Change any of the five ``EID*`` inputs that the
program renders, and the program hash - hence ``EID_r`` - changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import ContractError, EvalContract, canonical_json

MAPPING_SCHEMA = "a0.eidr.loreley/v1"
NATIVE_SCHEME = "evaluator_name_version_campaign_program_hash"
MAPPING_MODE = "native"

DECLARATION = (
    "Loreley computes its own identity: evaluator_name = WORKER_EVALUATOR_PLUGIN "
    "(evaluator.py:1481-1485), evaluator_version = source fingerprint of that module "
    "(evaluator_identity.py:90-105), campaign_program_hash = sha256 of loreley.program.md "
    "(campaign_program.py:212). The adapter renders loreley.program.md from the frozen "
    "EID* document (Goal / Primary metric / Correctness gates / Evaluation budget sections "
    "come from EID*.Config and EID*.MetricDefinition), so the triple is a function of EID*; "
    "eidr_derivation is the sha256 over (eid_star, plugin_source_sha256, campaign_program_sha256, "
    "native_scheme) and recomputes."
)


def plugin_source_sha256(plugin_source: Path) -> str:
    return hashlib.sha256(Path(plugin_source).read_bytes()).hexdigest()


def campaign_program_hash(program_path: Path) -> str:
    return hashlib.sha256(Path(program_path).read_bytes()).hexdigest()


def component_digests(contract: EvalContract) -> dict[str, str]:
    """The five `EID*` component digests, in the contract's own component order.

    `evalcontract.py` names the components `EvaluatorSource`, `DependencyLock`,
    `DataManifest`, `Config`, `MetricDefinition` and combines them in that order
    (`evalcontract.py:118-129`, `:504-506`); the same order is used here so the
    rendered provenance block is a canonical function of the frozen document.
    """

    components = contract.document.get("components") or {}
    order = ("EvaluatorSource", "DependencyLock", "DataManifest", "Config",
             "MetricDefinition")
    digests: dict[str, str] = {"EID*": contract.eid_star}
    for name in order:
        entry = components.get(name) or {}
        digest = entry.get("digest")
        if digest is None:
            raise ContractError(
                f"{contract.path.name} carries no digest for component {name!r}, so the "
                "campaign program cannot be a function of all five EID* inputs"
            )
        digests[name] = str(digest)
    return digests


def render_campaign_program(contract: EvalContract, theta_e_trace: Mapping[str, Any]) -> str:
    """Render ``loreley.program.md`` from the frozen ``EID*`` document.

    The rendered sections are exactly the ones ``parse_campaign_program``
    recognises (``loreley/core/campaign_program.py:32-45``), so Loreley's own
    parser reads the same primary metric and gates the frozen contract declares.
    """

    document = contract.document
    metric_value = (
        document.get("components", {}).get("MetricDefinition", {}).get("declared", {}).get("value")
        or {}
    )
    config_value = (
        document.get("components", {}).get("Config", {}).get("declared", {}).get("value") or {}
    )
    primary = str(metric_value.get("name") or "sum_radii")
    direction = str(metric_value.get("direction") or "maximize")
    unit = str(metric_value.get("unit") or "")
    gates = [str(item) for item in (metric_value.get("validity_gates") or [])]
    budget = config_value.get("theta_e_canonical") or {}
    seed, fidelity, fraction = (
        theta_e_trace.get("seed"),
        theta_e_trace.get("fidelity"),
        theta_e_trace.get("fraction"),
    )

    lines: list[str] = [
        "# Circle-packing campaign program (rendered from EID*)",
        "",
        f"Rendered by the A0 Loreley adapter from {contract.path.name} "
        f"(EID* = {contract.eid_star}).",
        "",
        "## Goal",
        "",
        "Evolve the circle-packing candidate so that pack_circles(26) returns 26 valid, "
        "non-overlapping circles inside the unit square, maximising the sum of radii.",
        "",
        "## Primary metric",
        "",
        f"- name: {primary}",
        f"- direction: {direction}",
    ]
    if unit:
        lines.append(f"- unit: {unit}")
    lines += [
        f"- evaluator: E* ({document.get('components', {}).get('EvaluatorSource', {}).get('digest', '')[:12]})",
        "",
        "## Correctness gates",
        "",
    ]
    lines += [f"- {gate}" for gate in (gates or ["valid_circle_packing"])]
    lines += [
        "",
        "## Provenance",
        "",
        "EID* component digests (a0/evalcontract/v1). Rendered from the frozen document so",
        "that loreley.program.md - and therefore campaign_program_hash, and therefore EID_r -",
        "is a function of all five EID* inputs and not only of the ones the prose sections",
        "happen to quote:",
        "",
    ]
    lines += [f"- {name}: {digest}" for name, digest in component_digests(contract).items()]
    lines += [
        "",
        "## Editable scope",
        "",
        "- solution.py",
        "",
        "## Protected scope",
        "",
        "- loreley.program.md",
        "",
        "## Evaluation budget",
        "",
        f"- seed: {seed}",
        f"- fidelity: {fidelity}",
        f"- fraction: {fraction}",
        f"- n: {budget.get('n', 26)}",
        f"- runs: {budget.get('runs', 5)}",
        f"- runtime_budget_ms: {budget.get('runtime_budget_ms', 250.0)}",
        f"- timeout_s: {budget.get('timeout_s', 120.0)}",
        "",
        "## Complexity policy",
        "",
        "- deterministic on repeated calls; no unbounded local search",
        "",
        "## Failure policy",
        "",
        "- a non-ok E* status is a candidate failure, never a score of 0.0",
        "",
        "## Logging policy",
        "",
        "- the adapter records traces outside every candidate worktree",
        "",
    ]
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class EidRMapping:
    value: str
    native_scheme: str
    mapping_mode: str
    derives_from_eid_star: str
    declaration: str
    recomputable: bool
    plugin_ref: str
    plugin_source_sha256: str
    campaign_program_sha256: str
    eidr_derivation: str

    def as_trace(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "native_scheme": self.native_scheme,
            "mapping_mode": self.mapping_mode,
            "derives_from_eid_star": self.derives_from_eid_star,
            "declaration": self.declaration,
            "recomputable": self.recomputable,
        }

    def as_document(self) -> dict[str, Any]:
        return {
            "schema": MAPPING_SCHEMA,
            "eid_star": self.derives_from_eid_star,
            "eid_r": {
                "value": self.value,
                "native_scheme": self.native_scheme,
                "mapping_mode": self.mapping_mode,
                "declaration": self.declaration,
                "recomputable": self.recomputable,
            },
            "native_components": {
                "evaluator_name": self.plugin_ref,
                "plugin_source_sha256": self.plugin_source_sha256,
                "campaign_program_sha256": self.campaign_program_sha256,
            },
            "eidr_derivation": self.eidr_derivation,
            "derivation_inputs": ["eid_star", "plugin_source_sha256",
                                  "campaign_program_sha256", "native_scheme"],
        }


def derive_eidr(
    contract: EvalContract,
    *,
    plugin_ref: str,
    plugin_source: Path,
    campaign_program: Path,
) -> EidRMapping:
    source_digest = plugin_source_sha256(plugin_source)
    program_digest = campaign_program_hash(campaign_program)
    value = f"loreley:v1:{plugin_ref}@source-sha256:{source_digest}#{program_digest}"
    derivation = hashlib.sha256(
        canonical_json(
            {
                "eid_star": contract.eid_star,
                "plugin_source_sha256": source_digest,
                "campaign_program_sha256": program_digest,
                "native_scheme": NATIVE_SCHEME,
            }
        ).encode("utf-8")
    ).hexdigest()
    return EidRMapping(
        value=value,
        native_scheme=NATIVE_SCHEME,
        mapping_mode=MAPPING_MODE,
        derives_from_eid_star=contract.eid_star,
        declaration=DECLARATION,
        recomputable=True,
        plugin_ref=plugin_ref,
        plugin_source_sha256=source_digest,
        campaign_program_sha256=program_digest,
        eidr_derivation=derivation,
    )


def recompute_eidr(mapping: Mapping[str, Any], *, contract: EvalContract,
                   plugin_source: Path, campaign_program: Path) -> tuple[bool, list[str]]:
    """Third-party recomputation of ``EID_r.value`` and its derivation digest."""

    problems: list[str] = []
    native = mapping.get("native_components") or {}
    expected = derive_eidr(
        contract,
        plugin_ref=str(native.get("evaluator_name") or ""),
        plugin_source=plugin_source,
        campaign_program=campaign_program,
    )
    recorded_value = (mapping.get("eid_r") or {}).get("value")
    if recorded_value != expected.value:
        problems.append(f"eid_r.value {recorded_value!r} != recomputed {expected.value!r}")
    if mapping.get("eidr_derivation") != expected.eidr_derivation:
        problems.append(
            f"eidr_derivation {mapping.get('eidr_derivation')!r} != recomputed "
            f"{expected.eidr_derivation!r}"
        )
    if str(native.get("plugin_source_sha256")) != expected.plugin_source_sha256:
        problems.append("plugin_source_sha256 does not match the file on disk")
    if str(native.get("campaign_program_sha256")) != expected.campaign_program_sha256:
        problems.append("campaign_program_sha256 does not match the file on disk")
    if str(mapping.get("eid_star")) != contract.eid_star:
        problems.append("mapping does not name the EID* it was derived from")
    return (not problems), problems


def write_mapping(path: Path, mapping: EidRMapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping.as_document(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def load_mapping(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
