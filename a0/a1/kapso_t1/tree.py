"""Build T1's KAPSO registered evaluation tree (`EID_r`), and fingerprint it.

**What the tree is.**  `kapso_evaluation/` in a KAPSO workspace: the two files
KAPSO's `EvaluationMaintainer.setup` fingerprints and registers
(`maintainer.py:209-236`) —

* `kapso_eval.py` — the registered command's implementation for T1,
  `tree_src/kapso_eval.py` (the declared stub: identity + class triple, no
  measurement);
* `a0_locator.json` — T1's constants: EID*, E*'s source records, the canonical
  `theta_E`, the metric, the candidate ABI, the graph sets and their visibility, and
  C*(T1)'s members.

Nothing else, so the fingerprint `EID_r` is exactly `manifest_fingerprint` over an
input set this workstream controls and a third party can recompute from `EID*` alone.

**Why not `a0/runtimes/kapso/a0_adapter/registered_tree.py`.**  That module is the
plumbing task's: its `WRAPPER_SOURCE` is the plumbing `kapso_eval.py` (which runs the
plumbing `E*` with `--fidelity/--fraction/--n/--runs/…`), and its `build_locator`
reads `theta["n"]`, `theta["runs"]` and `theta["runtime_budget_ms"]`, which T1's
`theta_e_canonical` does not carry (`{seed, timeout_s}` — T1 has no fidelity classes
and no subsampling). Both files are another workstream's, so this module supplies
T1's counterpart instead of editing them (`DEVIATIONS.md` D-KT1-1). The contract it
implements is the same one: two files, a locator that pins the evaluator's identity,
and `EID_r = manifest_fingerprint(tree)` computed by KAPSO's own function
(`evaluation_integrity.py:112-119`), imported rather than re-implemented.

    python3 a0/a1/kapso_t1/build_tree.py build     # write a0/a1/kapso_t1/tree/
    python3 a0/a1/kapso_t1/build_tree.py check     # rebuild in memory and compare
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import task as t1_task  # noqa: E402
from t1_binding import (  # noqa: E402
    CONFIG_PATH,
    TASK_ID,
    binding_record,
    load_candidates,
    load_config,
    load_eid,
)
from a0_adapter.common import (  # noqa: E402
    AdapterConfig,
    Candidate,
    EidStar,
    sha256_file,
)

WRAPPER_SOURCE = HERE / "tree_src" / "kapso_eval.py"
WRAPPER_NAME = "kapso_eval.py"
LOCATOR_NAME = "a0_locator.json"
TREE_FILES = (WRAPPER_NAME, LOCATOR_NAME)


def e_star_self_identity(config: AdapterConfig) -> Dict[str, Any]:
    """E*'s own identity material, asked of E* itself (`e_star.py digest`)."""
    command = [str(config.e_star_python), str(config.e_star_dir / "e_star.py"), "digest"]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=120,
        cwd=str(config.e_star_dir),
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"`e_star.py digest` failed with {config.e_star_python}: "
            f"{completed.stderr.strip()[:400]}"
        )
    document = json.loads(completed.stdout)
    return {
        "cmd": " ".join(command),
        "returncode": completed.returncode,
        "e_star_version": document.get("e_star_version"),
        "evaluator_source_sha256": document["evaluator_source_sha256"],
        "source_files": document.get("source_files"),
        "note": (
            "E*'s own digest recipe over the same two files; it is NOT the same number as "
            "EID*'s EvaluatorSource digest, and the two must not be compared as if they "
            "were (a0/a1/t1_eid.py:217-220). What must agree — and is checked by "
            "kapso_eval.py on every invocation — is the file-level material."
        ),
    }


def graph_set_block(config: AdapterConfig) -> Dict[str, Any]:
    """The three graph sets, their frozen counts and the visibility rule."""
    suite_root = Path(config.e_star_dir) / "suite"
    manifest_path = suite_root / "manifest.json"
    manifest = t1_task.load_suite_manifest(suite_root)
    counts = manifest["counts"]
    block: Dict[str, Any] = {}
    for role in ("dev", "eval", "calibration"):
        rows = [row for row in manifest["graphs"] if row.get("role") == role]
        block[role] = {
            "root": f"a0/tasks/maxcut/suite/{role}",
            "count": len(rows),
            "declared_count": counts.get(role),
            "visible_to_the_agent": role == "dev",
            "use": {
                "dev": "visible development instances; materialized into the workspace "
                       "as kapso_datasets/maxcut/dev (protected_data_paths)",
                "eval": "frozen hold-out; never in an agent workspace, scored once at the end",
                "calibration": "resource-rate calibration only; no algorithmic selection",
            }[role],
            "graph_sha256": {row["graph_id"]: row["graph_sha256"] for row in rows},
        }
    block["suite_manifest"] = {
        "path": "a0/tasks/maxcut/suite/manifest.json",
        "sha256": sha256_file(manifest_path),
        "schema": manifest.get("schema"),
        "suite_version": manifest.get("suite_version"),
        "canonical_form": manifest.get("canonical_form"),
    }
    return block


def build_locator(config: AdapterConfig, eid: EidStar, candidates: List[Candidate],
                  state_root: Path) -> Dict[str, Any]:
    """T1's `a0_locator.json`: everything kapso_eval.py needs, and nothing run-dependent."""
    theta = eid.canonical_theta
    metric = eid.components["MetricDefinition"]
    binding = binding_record(config, eid, candidates)
    return {
        "schema": "a0.kapso.registered_locator/v2",
        "runtime": "kapso",
        "task": TASK_ID,
        "produced_by": "a0/a1/kapso_t1/tree.py",
        # The candidate-set gate.  It is a *tree* property, not an environment
        # variable, precisely so that a coding-agent session cannot switch it on: the
        # registered tree is fingerprinted (it is EID_r) and re-synced into every
        # frame-run worktree before the evaluation executes.  The T1 stub reports C*
        # membership but never enforces it (DEVIATIONS.md D-KT1-5), so this flag is
        # carried for the record rather than as a refusal switch.
        "allow_unfrozen_candidate": False,
        "eid_star": eid.eid_star,
        "eid_star_file": str(eid.path),
        "eid_star_components": binding["eid_star_components"],
        "e_star": {
            "dir": str(config.e_star_dir.resolve()),
            "entry": "e_star.py",
            "helper": "e_star_child.py",
            "python": str(config.e_star_python),
            "self_identity": e_star_self_identity(config),
            "source_records": binding["evaluator"]["source_records"],
        },
        "theta_e_canonical": {
            "seed": int(theta["seed"]),
            "timeout_s": float(theta["timeout_s"]),
            "fidelity": "none — T1 has no fidelity classes (EID* Config theta_e_semantics)",
            "fraction": "none — every candidate is measured on the whole graph",
        },
        "metric": {
            "name": metric["metric_name"],
            "direction": metric["direction"],
            "epsilon": eid.epsilon,
            "unit": metric["value"]["objective"].get("unit"),
            "authoritative": metric["value"]["objective"].get("authoritative"),
            "aggregation": metric["value"]["objective"].get("aggregation"),
            "display_only": metric["value"]["objective"].get("display_only"),
            "outcome_schema": "a0.maxcut.outcome/v1",
            "failure_semantics": metric["value"]["failure_semantics"],
        },
        "candidate_abi": t1_task.CANDIDATE_ABI,
        "score_semantics": t1_task.SCORE_SEMANTICS,
        "graph_sets": graph_set_block(config),
        "candidate_set": {
            "manifest": "a0/tasks/maxcut/candidates/manifest.json",
            "manifest_sha256": sha256_file(config.candidate_set),
            "candidate_set_id": json.loads(
                Path(config.candidate_set).read_text(encoding="utf-8")
            ).get("candidate_set_id"),
            "candidate_count": len(candidates),
            "members": {
                candidate.candidate_id: {
                    "dir": candidate.path.name,
                    "solution_sha256": candidate.solution_sha256,
                    "role": candidate.role,
                    "kind": getattr(candidate, "kind", ""),
                }
                for candidate in candidates
            },
        },
        "evaluation": {
            "mode": "harness_owned",
            "runtime_measures": False,
            "this_stub": (
                "the registered command verifies E*'s identity and prints the granted "
                "class triple; it does not run E* and prints no `score` key"
            ),
            "score_of_record": (
                "the harness's KAPSO_EVAL_MANIFEST line, appended to "
                "node.evaluation_output after the session ends "
                "(a0/runtimes/kapso/a0_adapter/harness_manifest.py)"
            ),
            "harness_service": "a0/a1/eval_service.py (--evaluator maxcut)",
        },
        "state_root_default": str(Path(state_root)),
    }


def _kapso_fingerprint(manifest: Dict[str, str]) -> tuple:
    """KAPSO's own manifest fingerprint, imported, never re-invented.

    ``execution/evaluation_integrity.py:112-119``.  Importing `kapso.*` needs the
    pinned checkout's dependencies (GitPython among them), which only the adapter's
    own interpreter has; outside it the local fallback recomputes the same rule and
    says so, so a caller can tell "KAPSO computed this" from "this module recomputed
    it".  `build_tree.py check` and the T1 dry run run under the adapter's
    interpreter, where the imported branch is the one taken and the two agree.
    """
    try:
        from kapso.execution.evaluation_integrity import manifest_fingerprint

        return manifest_fingerprint(manifest), (
            "kapso.execution.evaluation_integrity.manifest_fingerprint (imported)"
        )
    except Exception as exc:  # noqa: BLE001 - any import failure falls back, and says so
        import hashlib

        encoded = json.dumps(
            dict(manifest), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest(), (
            "local recomputation of KAPSO's rule "
            f"(kapso.execution.evaluation_integrity import failed: {type(exc).__name__})"
        )


def mode_name(mode_config: Path) -> str:
    """The mode this config's `default_mode` names (read, not hardcoded)."""
    for line in Path(mode_config).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("default_mode:"):
            return line.split(":", 1)[1].strip()
    return ""


def binding_document(record: Dict[str, Any], eid: EidStar, config: AdapterConfig,
                     candidates: List[Candidate]) -> Dict[str, Any]:
    """The hand-over artifact: `EID_r -> EID* -> T1`, plus the declaration factors.

    `a0/a1/declaration.py` builds `CID` and the two arms' `AID_r`; before this
    workstream, the KAPSO arm's `AID_r` named only the *mechanism*
    (`runtime.outcome_lane`) and the checkout, so two different registered trees could
    sit under one `AID_r`. The factors proposed here are the ones the retarget adds, for
    the declaration's owner to adopt — this workstream does not edit that file.
    """
    binding = binding_record(config, eid, candidates)
    locator = build_locator(config, eid, candidates, Path(config.state_root) / "registered-eval")
    dev = locator["graph_sets"]["dev"]
    eval_set = locator["graph_sets"]["eval"]
    return {
        "schema": "a0.kapso_t1.binding/v1",
        "task_id": TASK_ID,
        "runtime": "kapso",
        "arm_id": "A_kapso",
        "eid_star": eid.eid_star,
        "eid_star_file": str(eid.path),
        "eid_r": f"manifest:{record['manifest_fingerprint']}",
        "eid_r_value": record["manifest_fingerprint"],
        "registered_tree": {
            "tree_dir": record["tree_dir"],
            "files": record["files"],
            "fingerprint_rule": record["fingerprint_rule"],
            "manifest_fingerprint_source": record.get("manifest_fingerprint_source"),
            "binding": record.get("mapping"),
        },
        "eid_mapping": record.get("eid_mapping"),
        "evaluator": binding["evaluator"],
        "metric": binding["metric"],
        "theta_e_canonical": binding["theta_e_canonical"],
        "candidate_set": {
            key: value for key, value in binding["candidate_set"].items() if key != "members"
        },
        "graph_visibility": {
            "dev": {"count": dev["count"], "visible_to_the_agent": True,
                    "root": dev["root"]},
            "eval": {"count": eval_set["count"], "visible_to_the_agent": False,
                     "root": eval_set["root"]},
            "suite_manifest_sha256": locator["graph_sets"]["suite_manifest"]["sha256"],
        },
        "config": {
            "adapter_config": str(CONFIG_PATH),
            "mode_config": str(config.mode_config),
            "mode_name": mode_name(config.mode_config),
            "protected_data_paths": ["kapso_datasets/maxcut/dev"],
        },
        "proposed_aid_r_factors": [
            {
                "name": "runtime.registered_evaluation_tree",
                "role": "aid_r",
                "identity": f"manifest:{record['manifest_fingerprint']}",
                "rationale": (
                    "the registered tree is what produces (or, in A1, is replaced by) the "
                    "score the arm consumes; two trees under one AID_r would be one arm "
                    "with two measurements"
                ),
                "note": f"built by a0/a1/kapso_t1/build_tree.py from {eid.eid_star}",
            },
            {
                "name": "runtime.registered_evaluation_tree_files",
                "role": "aid_r",
                "identity": "value:" + json.dumps(record["files"], sort_keys=True),
                "rationale": "the fingerprint's inputs, so a rebuild can be checked without running it",
            },
        ],
        "not_covered_by_this_artifact": [
            "no A1 campaign has run on this tree; the calibration pilot and the frozen "
            "B_hard come later (a0/tasks/maxcut/INTERFACE.md §9)",
            "the AID_r factors above are a proposal: a0/a1/declaration.py is another "
            "workstream's file",
            "the frame-run path (a VALIDATE grant or an evaluator bridge) is not "
            "supported by the score-less stub — see DEVIATIONS.md D-KT1-6",
        ],
    }


def verify_tree_fingerprint(tree_dir: Path) -> tuple:
    tree_dir = Path(tree_dir)
    manifest = {
        path.name: sha256_file(path)
        for path in sorted(tree_dir.iterdir())
        if path.is_file()
    }
    fingerprint, source = _kapso_fingerprint(manifest)
    return manifest, fingerprint, source


def install_t1_tree(config: AdapterConfig, eid: EidStar, candidates: List[Candidate],
                    tree_dir: Path, state_root: Path,
                    allow_unfrozen_candidate: bool = False) -> Dict[str, Any]:
    """Write T1's two-file registered tree and return its `EID_r` record.

    Same positional signature as the adapter's plumbing
    `registered_tree.install_registered_tree`, so `KapsoRuntime.prepare` can be
    pointed at this function unchanged (`runtime_t1.bind_tree_builder`).
    """
    tree_dir = Path(tree_dir)
    tree_dir.mkdir(parents=True, exist_ok=True)
    (tree_dir / WRAPPER_NAME).write_bytes(WRAPPER_SOURCE.read_bytes())
    locator = build_locator(config, eid, candidates, state_root)
    locator["allow_unfrozen_candidate"] = bool(allow_unfrozen_candidate)
    (tree_dir / LOCATOR_NAME).write_text(
        json.dumps(locator, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = {name: sha256_file(tree_dir / name) for name in TREE_FILES}
    fingerprint, fingerprint_source = _kapso_fingerprint(files)
    return {
        "schema": "a0.kapso.registered_tree/v1",
        "task": TASK_ID,
        "tree_dir": str(tree_dir),
        "files": files,
        "manifest_fingerprint": fingerprint,
        "manifest_fingerprint_source": fingerprint_source,
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
            "a0_locator.json carries EID*'s component digests and E*'s source "
            "records, and kapso_eval.py re-hashes e_star.py and e_star_child.py on "
            "every invocation and aborts with exit 3 without a manifest line if "
            "either differs, so EID_r cannot be produced from a different E*."
        ),
        "produced_by": "a0/a1/kapso_t1/tree.py::install_t1_tree",
    }


def mapping_document(record: Dict[str, Any], eid: EidStar) -> Dict[str, Any]:
    """`EID_r -> EID*`, in the adapter's mapping shape, for a T1 campaign's traces."""
    return {
        "schema": "a0.kapso.eid_mapping/v1",
        "runtime": "kapso",
        "task": TASK_ID,
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
                "a0_locator.json embeds EID*'s EvaluatorSource records (per-file "
                "sha256) and the five component digests; kapso_eval.py re-hashes both "
                "E* source files on every invocation and aborts with exit 3 without a "
                "manifest line if either differs"
            ),
            "eid_star_components": record["eid_star_component_digests"],
        },
        "recomputable": True,
        "recompute_recipe": [
            "read EID* (a0/a1/T1-EID.json): eid_star, the EvaluatorSource records, the "
            "five component digests",
            "regenerate a0_locator.json with a0/a1/kapso_t1/tree.py::build_locator",
            "sha256(kapso_eval.py) and sha256(a0_locator.json), then apply KAPSO's "
            "manifest_fingerprint over the sorted name->sha256 map",
            "compare with the value the adapter recorded on every trace event "
            "(eid_r.value) and with runtime.registration.evaluator_id, which KAPSO "
            "computes itself from the workspace tree",
        ],
    }
