"""The T1 retarget of the KAPSO adapter: bind the task, build the runtime, expose the seams.

`a0/runtimes/kapso/a0_adapter/runtime.py::KapsoRuntime` does the work — the workspace,
the git session machinery, KAPSO's `EvaluationMaintainer` registration, the
manifest-of-record parser, the integrity gate and the selection functions are all the
pinned checkout's own code. Three things in it are the *plumbing* task's, and the
adapter is another workstream's file, so this module rebinds them from T1's side
instead of editing it (`DEVIATIONS.md` D-KT1-2):

===============  ====================================================  ====================================
name             plumbing value                                        T1 binding
===============  ====================================================  ====================================
``PROBLEM``      circle-packing text                                   ``task.T1_PROBLEM``
``GOAL``         ``pack_circles`` goal                                 ``task.T1_GOAL``
``install_registered_tree``  the plumbing two-file tree writer        ``tree.install_t1_tree``
===============  ====================================================  ====================================

``_build_strategy`` and ``_register_evaluator`` read those names as module globals at
call time, so rebinding them before ``prepare()`` makes the run T1's while every other
line of runtime.py — the seams, the frame run, the ordering rule, the integrity gate —
stays exactly the code the plumbing probe verified. ``bind_t1_task()`` records what it
changed, and the probes put that record in their artifacts.

One T1-specific addition, via a subclass rather than a patch:
``T1KapsoRuntime._seed_baseline`` materializes the 24 dev instances into the workspace
(`kapso_datasets/maxcut/dev`) after the baseline commit and before the maintainer hashes
the protected paths, then fails closed if any hold-out instance's bytes are anywhere in
the workspace.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
KAPSO_DIR = REPO_ROOT / "a0" / "runtimes" / "kapso"
if str(KAPSO_DIR) not in sys.path:
    sys.path.insert(0, str(KAPSO_DIR))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import task as t1_task  # noqa: E402
import tree as t1_tree  # noqa: E402
from t1_binding import (  # noqa: E402
    baseline_candidate,
    load_candidates,
    load_config,
    load_eid,
)

from a0_adapter.harness_manifest import HarnessEvalClient, PostSessionManifest, maxcut_score_of  # noqa: E402
from a0_adapter.runtime import KapsoRuntime  # noqa: E402

T1_MODE_NAME = "T1_MAXCUT"


def bind_t1_task() -> Dict[str, Any]:
    """Point the adapter module's task constants and tree builder at T1.

    Idempotent, and it never *unbinds*: the T1 process is a T1 process. What was
    replaced, and with which values, is returned so the artifact can say so.
    """
    from a0_adapter import runtime as runtime_module

    before = {
        "GOAL": runtime_module.GOAL,
        "PROBLEM": runtime_module.PROBLEM,
        "install_registered_tree": getattr(
            runtime_module.install_registered_tree, "__module__", "?"
        ) + "." + getattr(runtime_module.install_registered_tree, "__name__", "?"),
    }
    runtime_module.GOAL = t1_task.T1_GOAL
    runtime_module.PROBLEM = t1_task.T1_PROBLEM
    runtime_module.install_registered_tree = t1_tree.install_t1_tree
    return {
        "schema": "a0.kapso_t1.task_binding/v1",
        "module": "a0/runtimes/kapso/a0_adapter/runtime.py",
        "rebound": {
            "GOAL": {"was": before["GOAL"], "now": t1_task.T1_GOAL},
            "PROBLEM": {"was": before["PROBLEM"], "now": t1_task.T1_PROBLEM},
            "install_registered_tree": {
                "was": before["install_registered_tree"],
                "now": "a0/a1/kapso_t1/tree.py::install_t1_tree",
            },
        },
        "why": (
            "the adapter is another workstream's file and is wired to the plumbing task; "
            "these three names are read as module globals at call time, so rebinding them "
            "makes the run T1's without editing it (DEVIATIONS.md D-KT1-2)"
        ),
        "notice": (
            "the rebound names stay bound for the life of this process, which is why a T1 "
            "run is a separate process from any plumbing run"
        ),
    }


@dataclass
class T1KapsoRuntime(KapsoRuntime):
    """`KapsoRuntime`, with T1's mode name and T1's workspace data."""

    mode_name: str = T1_MODE_NAME
    dev_materialization: Dict[str, Any] = field(default_factory=dict)
    holdout_bytes_in_workspace: List[Dict[str, str]] = field(default_factory=list)

    def _seed_baseline(self, baseline) -> None:
        """Baseline commit, then the visible instances — before the maintainer hashes them.

        `prepare()` runs `_build_strategy` → `_seed_baseline` → `_register_evaluator`,
        and `_register_evaluator` computes `build_data_manifest(workspace_dir,
        protected_data_paths)`. Materializing here is therefore the only point at which
        the dev instances are present *and* still counted as protected inputs: the
        integrity gate can then void a node that rewrites one.
        """
        super()._seed_baseline(baseline)
        suite_root = Path(self.config.e_star_dir) / "suite"
        self.dev_materialization = t1_task.materialize_dev_graphs(self.workspace_dir, suite_root)

        repo = self.strategy.workspace.repo
        repo.git.add(["kapso_datasets/maxcut/dev"])
        self._commit_staged(
            repo, "chore(kapso): materialize the T1 dev instances (protected data)"
        )
        self.setup_log.append(
            f"materialized {self.dev_materialization['count']} dev instances into "
            f"{self.dev_materialization['dest_relative']} (protected_data_paths)"
        )

        # Fail closed: no eval or calibration instance may be reachable in the
        # workspace, under any name (INTERFACE.md §12).
        self.holdout_bytes_in_workspace = t1_task.scan_for_holdout_bytes(
            self.workspace_dir, suite_root
        )
        if self.holdout_bytes_in_workspace:
            raise RuntimeError(
                "a hold-out instance's bytes are present in the workspace: "
                f"{self.holdout_bytes_in_workspace}"
            )


def build_runtime(*, run_dir: Path, state_root: Optional[Path] = None,
                  real_implementation: bool = False,
                  config=None) -> T1KapsoRuntime:
    """A prepared-to-`prepare()` T1 runtime: config, EID*, C*(T1), mode name, task text."""
    config = config or load_config()
    eid = load_eid(config)
    candidates = load_candidates(config)
    runtime = T1KapsoRuntime(
        config=config,
        eid=eid,
        candidates=candidates,
        run_dir=Path(run_dir),
        state_root=Path(state_root) if state_root else Path(run_dir) / "state",
        real_implementation=real_implementation,
        mode_name=T1_MODE_NAME,
    )
    return runtime


def prepare(runtime: T1KapsoRuntime) -> Dict[str, Any]:
    """`bind_t1_task()` then `KapsoRuntime.prepare(baseline)`, with the record.

    The binding record is what an artifact should carry: which names were rebound, that
    the tree source in the run dir is T1's stub, and that C*(T1)'s baseline was used.
    """
    binding = bind_t1_task()
    baseline = baseline_candidate(runtime.candidates)
    runtime.prepare(baseline)
    tree_source = Path(runtime.tree_source)
    stub_on_disk = tree_source / t1_tree.WRAPPER_NAME
    binding["baseline_candidate"] = baseline.candidate_id
    binding["tree_source"] = str(tree_source)
    binding["tree_source_is_the_t1_stub"] = (
        stub_on_disk.is_file()
        and stub_on_disk.read_bytes() == t1_tree.WRAPPER_SOURCE.read_bytes()
    )
    binding["tree_record_manifest_fingerprint"] = runtime.tree_record["manifest_fingerprint"]
    binding["kapsos_registered_evaluator_id"] = runtime.registration.evaluator_id
    binding["eid_r_matches_the_t1_tree_record"] = (
        runtime.registration.evaluator_id == runtime.tree_record["manifest_fingerprint"]
    )
    binding["dev_materialization"] = {
        "count": runtime.dev_materialization.get("count"),
        "dest_relative": runtime.dev_materialization.get("dest_relative"),
        "source_manifest_sha256": runtime.dev_materialization.get("source_manifest_sha256"),
    }
    binding["holdout_bytes_in_workspace"] = runtime.holdout_bytes_in_workspace
    binding["protected_data_paths"] = runtime.mode_config["evaluation_maintainer"].get(
        "protected_data_paths", []
    )
    binding["registered_data_manifest_entries"] = len(
        getattr(runtime.strategy, "registered_data_manifest", {}) or {}
    )
    return binding


def graph_paths(config=None, role: str = "dev") -> List[Dict[str, Any]]:
    config = config or load_config()
    return t1_task.instances_by_role(Path(config.e_star_dir) / "suite", role)


def harness_client(*, harness_root: Path, campaign_id: str, arm_id: str,
                   seed: int, label_resolver=None) -> HarnessEvalClient:
    """The harness ABI client; with `label_resolver`, the T1 relabelling wrapper."""
    if label_resolver is None:
        return HarnessEvalClient(root=Path(harness_root), campaign_id=campaign_id,
                                 arm_id=arm_id, seed=seed)
    return T1HarnessEvalClient(root=Path(harness_root), campaign_id=campaign_id,
                               arm_id=arm_id, seed=seed, label_resolver=label_resolver)


class T1HarnessEvalClient(HarnessEvalClient):
    """`HarnessEvalClient` that labels the harness's ledger with the candidate's identity.

    The adapter's post-session injector composes its request as
    ``candidate_id=f"node{node_id}"`` (``harness_manifest.py::PostSessionManifest.amend``,
    another workstream's file). A1's evaluation ledger is a per-candidate ledger
    (`INTERFACE.md` principle (iii), and `a0/a1/eval_service.py`'s `--override` map is
    keyed by candidate id), so this wrapper maps the node label to the candidate the
    node's artifact actually is. The request's `candidate_path` — and therefore the row's
    `candidate_source_sha256` — is untouched, so both identities stay joinable either
    way; `relabelled` records every substitution.
    """

    def __init__(self, *, label_resolver, **kwargs) -> None:
        super().__init__(**kwargs)
        self.label_resolver = label_resolver
        self.relabelled: List[dict] = []

    def evaluate(self, *, candidate_id, candidate_path, graph_path=None):
        resolved = self.label_resolver(candidate_id)
        if resolved != candidate_id:
            self.relabelled.append({
                "node_label": candidate_id,
                "candidate_id": resolved,
                "artifact": str(candidate_path),
            })
        return super().evaluate(candidate_id=resolved, candidate_path=candidate_path,
                                graph_path=graph_path)


def plan_label_resolver(runtime: T1KapsoRuntime):
    """`"node<N>"` -> the candidate id of the N-th planned round.

    The seam plan appends each round's record before `_absorb_implementation` returns,
    and the injector runs after that, so the mapping is complete when it is needed. A
    label that is not a node label, or a node whose round is unknown, is passed through
    unchanged rather than guessed.
    """
    plan = runtime.seams["plan"]

    def resolve(label: str) -> str:
        if isinstance(label, str) and label.startswith("node") and label[4:].isdigit():
            index = int(label[4:])
            if 0 <= index < len(plan.rounds):
                return plan.rounds[index]["candidate_id"]
        return label

    return resolve


def post_session_injector(*, runtime: T1KapsoRuntime, client: HarnessEvalClient,
                          graph_path: Path, resolver, run_id: str) -> PostSessionManifest:
    """The harness's post-session writer, with T1's score fold (`cut_edges`)."""
    return PostSessionManifest(
        strategy=runtime.strategy,
        client=client,
        graph_path=Path(graph_path),
        artifact_resolver=resolver,
        score_of=maxcut_score_of,
        run_id=run_id,
    )


def plan_resolver(runtime: T1KapsoRuntime):
    """Resolve a node's candidate artifact through the seam plan's own round records."""
    plan = runtime.seams["plan"]

    def resolver(node):
        for record in reversed(plan.rounds):
            if record.get("branch_name") == getattr(node, "branch_name", None):
                return plan.candidate(record["candidate_id"]).path
        return None

    return resolver
