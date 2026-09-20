"""Documented seams: the model-dependent phases, replaced by injectors.

The codex and claude lanes cannot complete a model call on this host (see
README.md "Blocked"), so the three phases of KAPSO's iteration that would call a
model are replaced — and only those three:

======================  =============================================  ==========================================
phase                   real call site                                what the seam does instead
======================  =============================================  ==========================================
ideation                ``strategy.py:845`` ``generate_solution(...)``   emits the next frozen ``C*`` candidate id
implementation          ``strategy.py:1036`` ``run_implementation(...)``  drives KAPSO's own ``ExperimentSession``
                                                                       (clone, branch, commit, push): writes the
                                                                       candidate's ``solution.py``, syncs the
                                                                       registered evaluation tree, runs the
                                                                       registered command, returns its output
feedback judge          ``feedback_flow.py:16`` ``generate_feedback``     deterministic judge: validity granted,
                        -> ``feedback_generator.generate``              score extracted from the manifest line
======================  =============================================  ==========================================

What the seams *do not* touch, and therefore what A0.2 still measures with real
runtime code: ``_select_parent`` (``strategy.py:1373-1406``),
``get_best_experiment`` (:1420-1434), ``get_deliverable_experiment``
(:1436-1453), ``get_deliverable_score`` (:1455-1477),
``checkout_to_best_experiment_branch`` (:1479-1495), ``_finalize_nodes``
(:798-838), ``enforce_evaluation_integrity`` (``base.py:740-798``),
``manifest_of_record`` (``registered_evaluation.py:52-102``),
``record_evaluation_attempt`` (:124-159), ``pick_representative``
(``expansion_lanes.py:111-127``), ``FULL_PASSTHROUGH`` (``fidelity.py:318-324``)
and ``select_committed_candidate`` (``fidelity.py:184-213``).

The full LLM-driven path (a real ideation session inventing a change and a real
implementation session writing it) is therefore UNVERIFIED — that is stated on
every artifact this adapter writes.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SEAM_IDEATION = "a0_adapter/seams.py::seam_generate_solution <- strategy.py:845"
SEAM_IMPLEMENTATION = (
    "a0_adapter/seams.py::seam_run_implementation <- strategy.py:1036"
)
SEAM_JUDGE = "a0_adapter/seams.py::SeamFeedbackJudge <- feedback_flow.py:16"


class SeamFeedbackJudge:
    """Deterministic stand-in for the LLM feedback judge.

    ``generate_feedback`` (``feedback_flow.py:16-123``) calls
    ``feedback_generator.generate(...)`` and then re-reads the manifest of
    record, which overrides the judge's extracted score whenever the manifest
    carries one.  This judge therefore emulates only the extraction step
    (reading the score off the session's manifest line) and grants validity;
    the manifest-of-record path that actually decides ``node.score`` is the
    runtime's own.
    """

    def __init__(self, timeout_seconds: Optional[float] = 300.0):
        self._timeout = timeout_seconds

    @property
    def configured_timeout_seconds(self) -> Optional[float]:
        return self._timeout

    def generate(self, **kwargs) -> Any:
        from kapso.execution.search_strategies.generic.feedback_generator import (
            FeedbackResult,
        )

        evaluator_output = kwargs.get("evaluation_result") or ""
        score = None
        for line in evaluator_output.splitlines():
            stripped = line.strip()
            if stripped.startswith("KAPSO_EVAL_MANIFEST"):
                payload = json.loads(stripped[len("KAPSO_EVAL_MANIFEST"):].strip())
                if "score" in payload:
                    score = float(payload["score"])
        return FeedbackResult(
            stop=False,
            evaluation_valid=True,
            feedback=(
                "seam judge: the registered evaluation's manifest line is the "
                "score of record; validity granted, no stop vote"
            ),
            score=score,
            cost_usd=0.0,
            duration_seconds=0.0,
        )


def install_seams(strategy: Any, config: Any, runtime: Any,
                  patch: Optional[tuple] = None) -> Dict[str, Any]:
    """Install the injectors and describe them for the artifacts.

    ``patch`` selects which phases are replaced; the default is all three, and
    ``("ideation",)`` leaves ``run_implementation`` real so a genuine
    coding-agent session drives the candidate and the registered evaluation.
    """
    from kapso.execution.search_strategies.generic import strategy as strategy_module

    plan = _Plan(runtime)
    phases = patch if patch is not None else ("ideation", "implementation")

    def seam_generate_solution(*args, **kwargs):
        return plan.next_solution()

    def seam_run_implementation(*args, **kwargs):
        return plan.run_implementation(**kwargs)

    if "ideation" in phases:
        strategy_module.generate_solution = seam_generate_solution
    if "implementation" in phases:
        strategy_module.run_implementation = seam_run_implementation
    return {
        "patched_phases": list(phases),
        "ideation": SEAM_IDEATION,
        "implementation": SEAM_IMPLEMENTATION,
        "judge": SEAM_JUDGE,
        "plan": plan,
        "note": (
            "the LLM-driven end-to-end path for the patched phases is UNVERIFIED"
        ),
    }


class _Plan:
    """The adapter's per-round plan: which frozen candidate, under which grant."""

    def __init__(self, runtime: Any):
        self.runtime = runtime
        self.queue: List[Dict[str, Any]] = []
        self.index = 0
        self.current: Optional[Dict[str, Any]] = None
        self.rounds: List[Dict[str, Any]] = []

    def push(self, candidate_id: str, *, fidelity: str = "full",
             fraction: float = 1.0, tamper: Optional[str] = None,
             commit_tamper: bool = False, run_evaluation: bool = True) -> None:
        self.queue.append({
            "candidate_id": candidate_id,
            "fidelity": fidelity,
            "fraction": fraction,
            "tamper": tamper,
            "commit_tamper": commit_tamper,
            "run_evaluation": run_evaluation,
        })

    def next_solution(self):
        entry = self.queue[self.index]
        self.index += 1
        self.current = entry
        text = entry.get("solution_text") or (
            f"A0-SEAM-CANDIDATE: {entry['candidate_id']}"
        )
        return (
            [text],
            [],
            {"cost_usd": 0.0, "duration_seconds": 0.0},
        )

    def candidate(self, candidate_id: str):
        for candidate in self.runtime.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise KeyError(candidate_id)

    def run_implementation(self, **kwargs):
        from kapso.execution.search_strategies.generic.registered_evaluation import (
            sync_registered_evaluation,
        )

        entry = self.current
        if entry is None:
            raise RuntimeError("no planned candidate for this iteration")
        candidate = self.candidate(entry["candidate_id"])
        workspace = kwargs["workspace"]
        branch_name = kwargs["branch_name"]
        parent_branch_name = kwargs["parent_branch_name"]

        started = time.monotonic()
        session = workspace.create_experiment_session(
            branch_name=branch_name, parent_branch_name=parent_branch_name
        )
        # What the implementation session would write with its edit tools.
        (Path(session.session_folder) / "solution.py").write_bytes(
            (candidate.path / "solution.py").read_bytes()
        )
        # KAPSO's own sync of the registered head into the session
        # (registered_evaluation.py:288-293).
        sync_registered_evaluation(session.session_folder, self.runtime.workspace_dir)

        stdout = stderr = ""
        exit_code: Optional[int] = None
        if entry["run_evaluation"]:
            command = self.runtime.maintainer.evaluation_command(
                fidelity=entry["fidelity"], fraction=entry["fraction"]
            )
            self.runtime.evaluator_calls += 1
            completed = subprocess.run(
                shlex.split(command),
                cwd=session.session_folder,
                capture_output=True,
                text=True,
                timeout=300,
            )
            stdout, stderr = completed.stdout, completed.stderr
            exit_code = completed.returncode

        if entry["tamper"]:
            tamper_path = Path(session.session_folder) / "kapso_evaluation" / "kapso_eval.py"
            tamper_path.write_text(
                tamper_path.read_text("utf-8") + "\n# " + entry["tamper"] + "\n",
                encoding="utf-8",
            )

        score_tag = "null"
        manifest_payload = None
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("KAPSO_EVAL_MANIFEST"):
                manifest_payload = json.loads(
                    stripped[len("KAPSO_EVAL_MANIFEST"):].strip()
                )
                if "score" in manifest_payload:
                    score_tag = repr(float(manifest_payload["score"]))

        agent_output = (
            "<code_changes_summary>"
            f"seam implementation: installed frozen candidate "
            f"{candidate.candidate_id} (solution.py sha256 "
            f"{candidate.solution_sha256})"
            "</code_changes_summary>\n"
            "<evaluation_script_path>kapso_evaluation/kapso_eval.py"
            "</evaluation_script_path>\n"
            "<score>" + score_tag + "</score>\n"
            "<technical_difficulties>none (seam implementation session)"
            "</technical_difficulties>\n"
            "<evaluation_output>\n" + stdout + "\n</evaluation_output>\n"
        )
        session.close_session()
        elapsed = time.monotonic() - started
        record = {
            "candidate_id": candidate.candidate_id,
            "branch_name": branch_name,
            "parent_branch_name": parent_branch_name,
            "fidelity": entry["fidelity"],
            "fraction": entry["fraction"],
            "exit_code": exit_code,
            "command": (
                self.runtime.maintainer.evaluation_command(
                    fidelity=entry["fidelity"], fraction=entry["fraction"]
                )
                if entry["run_evaluation"] else None
            ),
            "stdout_sha256_prefix": hashlib.sha256(
                stdout.encode("utf-8")
            ).hexdigest()[:16],
            "manifest": manifest_payload,
            "stderr_tail": stderr.strip().splitlines()[-1] if stderr.strip() else "",
            "tamper": entry["tamper"],
            "elapsed_sec": round(elapsed, 6),
        }
        self.rounds.append(record)
        return (agent_output, {"cost_usd": 0.0, "duration_seconds": elapsed},
                None, None)
