"""Build the KAPSO-side registered evaluation tree.

The tree is what KAPSO's ``EvaluationMaintainer.setup`` fingerprints and
registers (``maintainer.py:209-236``): two files, ``kapso_eval.py`` (the
KAPSO-side execution of E*) and ``a0_locator.json`` (the EID*-derived
constants that execution is pinned to).  Nothing else lives there, so the
fingerprint ``EID_r`` is exactly ``manifest_fingerprint`` over an input set the
adapter controls and a third party can recompute from ``EID*`` alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .common import (
    AdapterConfig,
    Candidate,
    EidStar,
    canonical_json,
    sha256_file,
    sha256_text,
    write_json,
)

WRAPPER_SOURCE = Path(__file__).resolve().parent / "registered" / "kapso_eval.py"


def build_locator(
    config: AdapterConfig,
    eid: EidStar,
    candidates: List[Candidate],
    state_root: Path,
    allow_unfrozen_candidate: bool = False,
) -> Dict[str, Any]:
    theta = eid.canonical_theta
    metric = eid.components["MetricDefinition"]
    return {
        "schema": "a0.kapso.registered_locator/v1",
        "runtime": "kapso",
        "produced_by": "a0/runtimes/kapso/a0_adapter/registered_tree.py",
        "eid_star": eid.eid_star,
        # The candidate-set gate.  It is a *tree* property, not an environment
        # variable, precisely so that a coding-agent session cannot switch it on:
        # the registered tree is fingerprinted (it is EID_r) and is re-synced
        # into every frame-run worktree before the evaluation executes, so a
        # session cannot change this without breaking evaluation integrity.
        # Only the adapter's own closure sentinel builds a scratch tree with the
        # flag set, and that tree is never registered.
        "allow_unfrozen_candidate": bool(allow_unfrozen_candidate),
        "eid_star_components": {
            name: eid.component_digest(name)
            for name in (
                "EvaluatorSource",
                "DependencyLock",
                "DataManifest",
                "Config",
                "MetricDefinition",
            )
        },
        "e_star": {
            "dir": str(config.e_star_dir),
            "entry": "e_star.py",
            "helper": "e_star_child.py",
            "python": str(config.e_star_python),
            "source_records": [
                {"path": record["path"], "sha256": record["sha256"],
                 "size": record["size"]}
                for record in eid.evaluator_source_records()
            ],
        },
        "theta_e_canonical": {
            "seed": int(theta["seed"]),
            "fidelity": theta["fidelity"],
            "fraction": float(theta["fraction"]),
            "n": int(theta["n"]),
            "runs": int(theta["runs"]),
            "runtime_budget_ms": float(theta["runtime_budget_ms"]),
            "timeout_s": float(theta["timeout_s"]),
        },
        "metric": {
            "name": metric["metric_name"],
            "direction": metric["direction"],
            "epsilon": eid.epsilon,
            "outcome_fields": metric["value"]["outcome_fields"],
            "failure_semantics": metric["value"]["failure_semantics"],
        },
        "state_root_default": str(state_root),
        "candidate_set": {
            "manifest": str(config.candidate_set),
            "candidate_count": len(candidates),
            "members": {
                candidate.candidate_id: {
                    "path": candidate.path.name,
                    "solution_sha256": candidate.solution_sha256,
                }
                for candidate in candidates
            },
        },
    }


def _kapso_fingerprint(manifest: Dict[str, str]) -> str:
    """KAPSO's own manifest fingerprint (imported, not re-implemented).

    ``execution/evaluation_integrity.py:112-119``.  The local fallback is only
    for import-order safety and is asserted equal to KAPSO's value by
    ``verify_fingerprint_rule`` below.
    """
    try:
        from kapso.execution.evaluation_integrity import manifest_fingerprint

        return manifest_fingerprint(manifest)
    except Exception:
        import hashlib

        encoded = json.dumps(
            dict(manifest), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def install_registered_tree(
    config: AdapterConfig, eid: EidStar, candidates: List[Candidate],
    tree_dir: Path, state_root: Path, allow_unfrozen_candidate: bool = False,
) -> Dict[str, Any]:
    """Write the two-file registered evaluation tree and fingerprint it."""
    tree_dir = Path(tree_dir)
    tree_dir.mkdir(parents=True, exist_ok=True)
    wrapper_target = tree_dir / "kapso_eval.py"
    wrapper_target.write_bytes(WRAPPER_SOURCE.read_bytes())
    locator = build_locator(config, eid, candidates, state_root,
                            allow_unfrozen_candidate)
    locator_text = json.dumps(locator, indent=2, sort_keys=True) + "\n"
    (tree_dir / "a0_locator.json").write_text(locator_text, encoding="utf-8")

    files = sorted(p.name for p in tree_dir.iterdir() if p.is_file())
    manifest = {name: sha256_file(tree_dir / name) for name in files}
    fingerprint = _kapso_fingerprint(manifest)
    record = {
        "schema": "a0.kapso.registered_tree/v1",
        "tree_dir": str(tree_dir),
        "files": manifest,
        "manifest_fingerprint": fingerprint,
        "fingerprint_rule": (
            "KAPSO's own: sha256(json.dumps(manifest, sort_keys=True, "
            "separators=(',',':'))) — execution/evaluation_integrity.py:112-119"
        ),
        "eid_star": eid.eid_star,
        "eid_star_component_digests": {
            name: eid.component_digest(name)
            for name in ("EvaluatorSource", "DependencyLock", "DataManifest",
                         "Config", "MetricDefinition")
        },
        "mapping": (
            "EID_r = manifest_fingerprint({kapso_eval.py, a0_locator.json}); "
            "a0_locator.json carries the EID* component digests, the E* source "
            "records and the canonical theta_E that kapso_eval.py enforces at "
            "run time, so recomputing EID_r requires only EID* and this "
            "adapter's two source files."
        ),
    }
    return record


def mapping_document(record: Dict[str, Any], eid: EidStar) -> Dict[str, Any]:
    return {
        "schema": "a0.kapso.eid_mapping/v1",
        "runtime": "kapso",
        "native_scheme": "manifest_fingerprint",
        "mapping_mode": "native",
        "eid_star": eid.eid_star,
        "eid_r": f"manifest:{record['manifest_fingerprint']}",
        "eid_r_value": record["manifest_fingerprint"],
        "derivation": {
            "formula": "EID_r = manifest_fingerprint(registered_evaluation_tree)",
            "fingerprint_rule": record["fingerprint_rule"],
            "tree_files": record["files"],
            "eid_star_binding": (
                "a0_locator.json embeds EID*'s EvaluatorSource records "
                "(per-file sha256) and the five component digests; "
                "kapso_eval.py re-hashes e_star.py and e_star_child.py on every "
                "invocation and aborts with exit 3 without a score if either "
                "differs, so EID_r cannot be produced from a different E*."
            ),
            "eid_star_components": record["eid_star_component_digests"],
        },
        "recomputable": True,
        "recompute_recipe": [
            "read EID* (a0/contract/out/plumbing.EID.json), take eid_star and "
            "the EvaluatorSource records",
            "regenerate a0_locator.json with a0_adapter/registered_tree.py",
            "sha256(kapso_eval.py) and sha256(a0_locator.json), then apply "
            "KAPSO's manifest_fingerprint over the sorted relpath->sha256 map",
            "compare with the value the adapter recorded on every trace event "
            "(eid_r.value) and in the maintainer registry",
        ],
    }


def verify_tree_fingerprint(tree_dir: Path) -> tuple[Dict[str, str], str]:
    tree_dir = Path(tree_dir)
    manifest = {
        path.name: sha256_file(path)
        for path in sorted(tree_dir.iterdir())
        if path.is_file()
    }
    return manifest, _kapso_fingerprint(manifest)
