"""Build and drive a real KAPSO campaign workspace for A0.

Nothing here re-implements KAPSO: the workspace, the git session machinery, the
``EvaluationMaintainer`` registration, the registered-evaluation frame run, the
manifest-of-record parser, the integrity check and the selection functions are
all the pinned checkout's own code (``/home/ebt/kapso_ck/kapso`` @ 7d99b152),
imported from ``src`` through ``PYTHONPATH`` so the read-only snapshot is never
installed into or written to.

The model-dependent phases are replaced in ``seams.py``; everything else runs.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .channels import RegisteredResult, run_registered_channel
from .common import (
    AdapterConfig,
    Candidate,
    EidStar,
    AdapterError,
    EXIT_INTERNAL,
    bootstrap_kapso,
    sha256_file,
)
from .registered_tree import install_registered_tree

GOAL = (
    "Optimize `solution.py`'s `pack_circles(n=26)` to return deterministic, "
    "non-overlapping circles inside the unit square, maximize `sum_radii`, and "
    "keep default `pack_circles()` equivalent to `pack_circles(26)`."
)
PROBLEM = (
    "circle-packing: pack 26 non-overlapping circles in the unit square and "
    "maximize the sum of their radii (sum_radii).  The evaluation is "
    "maintained by the system and is read-and-execute only."
)


@dataclass
class RegistrationEvidence:
    evaluator_id: str
    version: int
    provenance: str
    registered_tree_manifest: Dict[str, str]
    tree_fingerprint: str
    calibration_stdout: str
    calibration_exit: int
    calibration_manifest: Dict[str, Any]
    calibration_seconds: float
    command_full: str
    command_calibration: str
    data_manifest_entries: int
    setup_agent_seam: str
    registry_head_evaluator_id: str


@dataclass
class KapsoRuntime:
    config: AdapterConfig
    eid: EidStar
    candidates: List[Candidate]
    run_dir: Path
    state_root: Path
    mode_config: Dict[str, Any] = field(default_factory=dict)
    # False = drive the runtime's real model lanes (no seams).  Only the
    # end-to-end check in bin/e2e_round.py sets it, and only when a model
    # backend is actually reachable.
    use_seams: bool = True
    # True = leave run_implementation real (a genuine coding-agent session
    # writes the candidate and runs the registered evaluation); only the
    # ideation and judge phases stay seamed.
    real_implementation: bool = False
    mode_name: str = "CIRCLE_PACKING"

    # filled by prepare()
    strategy: Any = None
    maintainer: Any = None
    workspace_dir: Path = None  # type: ignore[assignment]
    tree_source: Path = None  # type: ignore[assignment]
    registration: Optional[RegistrationEvidence] = None
    tree_record: Dict[str, Any] = field(default_factory=dict)
    config_evidence: Dict[str, Any] = field(default_factory=dict)
    evaluator_calls: int = 0
    setup_log: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # preparation
    # ------------------------------------------------------------------ #

    def prepare(self, baseline: Candidate) -> None:
        bootstrap_kapso(self.config)
        from kapso.core.config import load_mode_config

        self.mode_config = load_mode_config(
            str(self.config.mode_config), self.mode_name
        )
        # Absolute paths everywhere: KAPSO runs the registered evaluation with
        # cwd set to a worktree, and E* must never receive a path that resolves
        # differently inside that worktree (hard constraint 2 — nothing may be
        # written into a tree a `git checkout` can restore).
        self.run_dir = Path(self.run_dir).resolve()
        self.workspace_dir = (self.run_dir / "workspace").resolve()
        self.state_root = Path(self.state_root).resolve()
        self.tree_source = (self.run_dir / "registered_evaluation_source").resolve()

        # A fresh workspace per run.  Reusing the directory of a previous run
        # makes KAPSO's own baseline-memory commit fail, because it stages one
        # path (`.kapso/repo_memory.json`) but commits when *any* untracked file
        # exists — and a previous run leaves `.kapso/evaluation_registry.json`
        # untracked (strategy/base.py:568-572).  git then exits 1 with "nothing
        # added to commit but untracked files present", which propagates out of
        # the strategy constructor.  The workspace below `--run-dir` is the
        # adapter's own artifact, so it is rebuilt rather than repaired.
        if (self.workspace_dir / ".git").exists():
            import shutil

            shutil.rmtree(self.workspace_dir, ignore_errors=True)
            self.setup_log.append(
                f"removed the previous workspace at {self.workspace_dir} before "
                "rebuilding (a stale untracked .kapso/evaluation_registry.json "
                "makes KAPSO's baseline commit fail: base.py:568-572)"
            )

        self.tree_record = install_registered_tree(
            self.config, self.eid, self.candidates, self.tree_source,
            Path(self.config.state_root) / "registered-eval",
        )
        # The E* state root for this run.  It is passed to every evaluator
        # subprocess through the environment (the registered tree itself stays
        # run-independent, so KAPSO's EID_r is a function of EID* alone), and it
        # is outside every candidate worktree (protocol hard constraint 2).
        os.environ["A0_KAPSO_EVAL_STATE_ROOT"] = str(self.state_root)

        self.config_evidence = {
            "mode_config_path": str(self.config.mode_config),
            "effective_config": self.mode_config,
            "parent_policy_param": self.mode_config["search_strategy"]["params"][
                "parent_policy"
            ],
            "fidelity_mode": self.mode_config["budget"]["fidelity"]["mode"],
            "max_change_requests": self.mode_config["evaluation_maintainer"][
                "max_change_requests"
            ],
            "subsample_seed": self.mode_config["evaluation_maintainer"][
                "subsample_seed"
            ],
        }
        self._build_strategy()
        self._seed_baseline(baseline)
        self._register_evaluator()

    def _coding_agent_config(self, block: Dict[str, Any]):
        from kapso.execution.coding_agents.base import CodingAgentConfig
        from kapso.execution.coding_agents.factory import CodingAgentFactory

        return CodingAgentFactory.build_config(
            agent_type=block.get("type", "claude_code"),
            model=block.get("model"),
            debug_model=block.get("debug_model"),
            agent_specific=block.get("agent_specific", {}),
        )

    def _build_strategy(self) -> None:
        from kapso.environment.handlers.generic import GenericProblemHandler
        from kapso.execution.search_strategies.base import SearchStrategyConfig
        from kapso.execution.search_strategies.generic.strategy import GenericSearch

        from .seams import SeamFeedbackJudge, install_seams

        self.problem_handler = GenericProblemHandler(
            problem_description=PROBLEM
        )
        strategy_config = SearchStrategyConfig(
            problem_handler=self.problem_handler,
            # No model backend is reachable on this host (see README): the
            # adapter does not configure one, and every phase that would call
            # one is replaced by a documented seam (seams.py).  llm=None is
            # therefore the honest value, not a mock.
            llm=None,
            coding_agent_config=self._coding_agent_config(
                self.mode_config["coding_agent"]
            ),
            params=dict(self.mode_config["search_strategy"]["params"]),
            initial_repo=None,
            eval_dir=str(self.tree_source),
            data_dir=None,
            feedback_generator=SeamFeedbackJudge(),
            goal=GOAL,
        )
        self.strategy = GenericSearch(
            strategy_config, workspace_dir=str(self.workspace_dir)
        )
        self.seams = install_seams(
            self.strategy, self.config, self,
            patch=("ideation",) if self.real_implementation else None,
        )

    def _seed_baseline(self, baseline: Candidate) -> None:
        """The `main` branch carries c_0 = the upstream baseline solution.

        A re-run inside an existing run dir finds the same bytes already
        committed; an untracked file (`.gitignore`, `.kapso/`, `kapso_datasets/`)
        must not turn that into a failing commit.
        """
        target = self.workspace_dir / "solution.py"
        target.write_bytes((baseline.path / "solution.py").read_bytes())
        repo = self.strategy.workspace.repo
        repo.git.add("-f", "solution.py")
        self._commit_staged(repo, f"chore(kapso): baseline {baseline.candidate_id}")

    def _commit_staged(self, repo, message: str) -> bool:
        """Commit the index, tolerating 'nothing to commit'.

        Callers stage explicitly; the only failure this hides is an empty
        commit, which git reports as exit 1. Anything else propagates.
        """
        import git as git_module

        if not repo.index.diff("HEAD"):
            self.setup_log.append(
                f"no staged delta for {message!r}: nothing to commit"
            )
            return False
        try:
            repo.git.commit("-m", message)
        except git_module.GitCommandError as exc:
            text = f"{exc}".lower()
            if "nothing to commit" in text or "nothing added to commit" in text:
                self.setup_log.append(
                    f"commit {message!r} was empty (tolerated): {exc}"
                )
                return False
            raise
        return True

    def _register_evaluator(self) -> None:
        """Run KAPSO's EvaluationMaintainer.setup over the provided tree.

        Seam: ``EvaluationMaintainer._run_agent`` (``maintainer.py:206``) is the
        setup session that would verify/build a provided evaluator with a coding
        agent.  The tree is provided and already runnable, so the adapter
        replaces that one call with a no-op and lets every other post-condition
        of the transaction run for real: ``_enforce_provided_immutable``, the
        deadline-bounded calibration run, ``manifest_fingerprint`` over the
        registered tree, ``registry.register`` and ``_commit_evaluation``.
        """
        from kapso.execution.evaluation_integrity import (
            build_evaluation_manifest,
            manifest_fingerprint,
        )
        from kapso.execution.evaluation_maintainer.maintainer import (
            EvaluationMaintainer,
            evaluation_command,
        )
        from kapso.execution.fidelity import FidelitySpec

        maintainer_block = self.mode_config["evaluation_maintainer"]
        fidelity_spec = FidelitySpec.resolve(
            self.mode_config["budget"].get("fidelity")
        )
        maintainer = EvaluationMaintainer(
            coding_agent_config=self._coding_agent_config(maintainer_block),
            workspace_dir=str(self.workspace_dir),
            fast_fraction=fidelity_spec.eval_fast_fraction,
            subsample_seed=maintainer_block.get("subsample_seed", 1337),
            calibration_fraction=maintainer_block.get("calibration_fraction", 0.03),
            calibration_timeout_seconds=maintainer_block.get(
                "calibration_timeout_seconds", 900
            ),
            fast_variant_threshold_seconds=(
                maintainer_block.get("fast_variant_threshold_minutes", 20) * 60
            ),
            overhead_factor=maintainer_block.get("overhead_factor", 1.25),
            protected_data_paths=maintainer_block.get("protected_data_paths", []),
        )
        self.maintainer = maintainer

        seam_note = (
            "EvaluationMaintainer._run_agent monkeypatched to a no-op "
            "(maintainer.py:206): the provided evaluation tree needs no build "
            "session; every other maintainer post-condition runs for real"
        )
        maintainer._run_agent = lambda prompt: 0.0  # documented seam

        registered_dir = Path(self.workspace_dir) / "kapso_evaluation"
        command_full = maintainer.evaluation_command(fidelity="full", fraction=1.0)
        command_calibration = maintainer.evaluation_command(
            fidelity="fast", fraction=maintainer.calibration_fraction
        )

        started = time.monotonic()
        version = maintainer.setup(goal=GOAL, eval_dir=str(self.tree_source),
                                   data_dir=None)
        setup_seconds = time.monotonic() - started

        manifest = build_evaluation_manifest(registered_dir)
        head = maintainer.registry.head()
        live_manifest, live_fingerprint = _tree_fingerprint(registered_dir)
        self.registration = RegistrationEvidence(
            evaluator_id=manifest_fingerprint(manifest),
            version=version.version,
            provenance=version.provenance,
            registered_tree_manifest=manifest,
            tree_fingerprint=live_fingerprint,
            calibration_stdout="",
            calibration_exit=0,
            calibration_manifest={
                "fast_fraction": version.fidelity_support["fast_fraction"],
                "subsample_seed": version.fidelity_support["subsample_seed"],
                "total_items": version.fidelity_support["total_items"],
                "timing_basis": (
                    f"measured(n={len(version.timing.measured_samples)})"
                    if version.timing.measured_samples
                    else "calibration"
                ),
                "per_item_seconds": version.timing.per_item_seconds,
                "startup_seconds": version.timing.startup_seconds,
            },
            calibration_seconds=setup_seconds,
            command_full=command_full,
            command_calibration=command_calibration,
            data_manifest_entries=len(version.data_manifest),
            setup_agent_seam=seam_note,
            registry_head_evaluator_id=head.evaluator_id,
        )

        # Adapter wiring identical to Orchestrator._adopt_registered_evaluation
        # (orchestrator.py:624-645).
        self.strategy.set_registered_evaluation(
            manifest=manifest,
            command=command_full,
            evaluator_id=manifest_fingerprint(manifest),
            subsample_seed=maintainer.subsample_seed,
            data_manifest=head.data_manifest,
        )
        self.strategy.record_eval_duration = maintainer.record_run
        # fidelity.mode = off => the executive's grant is FULL_PASSTHROUGH for
        # every iteration (orchestrator.py:1390; fidelity.py:318-324).
        from kapso.execution.fidelity import FULL_PASSTHROUGH

        self.strategy.observe_fidelity(FULL_PASSTHROUGH)

    # ------------------------------------------------------------------ #
    # candidate branches
    # ------------------------------------------------------------------ #

    def candidate_branch(self, candidate: Candidate) -> str:
        return f"cand_{candidate.candidate_id}"

    def create_candidate_branch(self, candidate: Candidate) -> str:
        """Branch `main` and commit the candidate's bytes on it.

        A candidate identical to the baseline (c02 on `main`) yields a branch
        with no delta; the branch is still created, because the frame run and
        the integrity check address candidates by branch name.
        """
        repo = self.strategy.workspace.repo
        branch = self.candidate_branch(candidate)
        if branch in [head.name for head in repo.heads]:
            return branch
        self.strategy.workspace.switch_branch("main")
        repo.git.checkout("-b", branch)
        target = Path(self.workspace_dir) / "solution.py"
        target.write_bytes((candidate.path / "solution.py").read_bytes())
        repo.git.add("-f", "solution.py")
        self._commit_staged(repo, f"chore(kapso): candidate {candidate.candidate_id}")
        self.strategy.workspace.switch_branch("main")
        return branch

    def registered_channel_for_branch(
        self, candidate_id: str, branch: str, theta: Dict[str, Any]
    ) -> RegisteredResult:
        """KAPSO's registered command, run the way its frame run runs it.

        The command string is ``maintainer.evaluation_command`` and the seed it
        carries is the registered ``subsample_seed`` — exactly as
        ``registered_evaluation.py:185-191`` composes the frame run's command.
        A caller-supplied ``theta_E`` whose seed differs would be a different
        class, so it is refused rather than silently substituted.
        """
        from kapso.execution.search_strategies.generic.registered_evaluation import (
            sync_registered_evaluation,
        )

        if int(theta["seed"]) != int(self.maintainer.subsample_seed):
            raise AdapterError(
                "theta_E seed does not equal the registered subsample seed; "
                "KAPSO's own command composes the registered seed "
                "(registered_evaluation.py:185-191)",
                EXIT_INTERNAL,
            )
        command = self.maintainer.evaluation_command(
            fidelity=theta["fidelity"], fraction=float(theta["fraction"])
        )
        workspace = self.strategy.workspace
        with workspace.materialize_ref(branch) as worktree:
            # The registered head is the only ruler frame runs execute
            # (registered_evaluation.py:193-200).
            sync_registered_evaluation(worktree, str(self.workspace_dir))
            self.evaluator_calls += 1
            result = run_registered_channel(
                candidate_id,
                command=command,
                cwd=Path(worktree),
                theta=theta,
                timeout_seconds=300,
            )
            result.worktree = worktree
        return result

    def frame_eval(
        self,
        node: Any,
        *,
        fidelity: str,
        fraction: float,
        deadline_seconds: Optional[float] = 120.0,
    ) -> Optional[float]:
        """KAPSO's own frame run (``registered_evaluation.py:162-285``)."""
        self.evaluator_calls += 1
        return self.strategy._execute_registered_evaluation(
            node,
            fidelity=fidelity,
            fraction=fraction,
            deadline_seconds=deadline_seconds,
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def disk_manifest(self) -> Dict[str, Any]:
        manifest, fingerprint = _tree_fingerprint(
            Path(self.workspace_dir) / "kapso_evaluation"
        )
        return {"files": manifest, "fingerprint": fingerprint}

    def scratch_tree(self, mutate) -> Path:
        """Copy the registered tree and apply `mutate` to a copy of it."""
        import shutil

        target = Path(self.run_dir) / "controls" / f"tree_{int(time.time()*1e6)}"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.tree_source, target, dirs_exist_ok=True)
        mutate(target)
        return target


def _tree_fingerprint(directory: Path):
    from kapso.execution.evaluation_integrity import (
        build_evaluation_manifest,
        manifest_fingerprint,
    )

    manifest = build_evaluation_manifest(directory)
    return manifest, manifest_fingerprint(manifest)
