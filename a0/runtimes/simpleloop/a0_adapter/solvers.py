"""The solver lane: `c_{t+1} = Agent(c_t, H_t)` (open_world_plan_review.typ:610).

Two implementations, one interface:

* `CliSolver`   — the intended production lane. It shells out to `codex`/`claude`,
                  i.e. it inherits that CLI's model endpoint and its network
                  posture. The `codex` branch is VERIFIED end to end on this
                  machine: two bounded real rounds exited 0 with E* `ok` and a
                  scored proposal, and the shipped argv was independently probed
                  closed by the a0/closure workstream. The earlier "no live
                  endpoint" reading was true when written — the dead port 15722
                  was CC Switch's local proxy, not a dead relay — and no longer
                  is. The `claude` branch is the only part still UNVERIFIED.
                  See the `CliSolver` docstring and README.md "the solver lane".
* `InjectedSolver` — a deterministic, documented *seam*: the proposal sequence is
                  read from a JSON script on disk instead of from a model. This is
                  what makes A0.1/A0.2 executable today. It is a test double for
                  the proposer only — everything downstream of the proposal (the
                  E* invocation, the F_r fold, the selection) is the same code
                  path the CLI lane uses.

Neither lane ever produces a score. A proposal is a directory containing
solution.py; the value of that proposal is decided by E* alone.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .candidates import Candidate, CandidateSet, CandidateSetError, sha256_file


class SolverError(RuntimeError):
    pass


@dataclass
class Proposal:
    """A candidate produced by the solver lane, materialised under the run dir."""

    candidate_id: str
    path: Path
    solution_sha256: str
    source: str
    latency_sec: float
    model_calls: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    detail: dict = field(default_factory=dict)

    def as_candidate(self) -> Candidate:
        return Candidate(
            candidate_id=self.candidate_id,
            path=self.path,
            solution_sha256=self.solution_sha256,
            role="proposal",
            kind="solver_output",
            note=self.source,
            expected_status=None,
            raw={"proposal_source": self.source},
        )


class Solver:
    lane = "abstract"

    def initial_proposal(self, baseline: Candidate, *, iteration: int = 0) -> Proposal:
        """`c_0 = baseline` (open_world_plan_review.typ:608).

        The first candidate is not generated: it *is* the C* baseline. Each lane
        materialises it into the run's work directory so that every candidate the
        run evaluates lives under the run dir and nothing can be mutated in place.
        """
        dest_dir = self.work_dir / f"iter{iteration:03d}" / baseline.candidate_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline.path / "solution.py", dest_dir / "solution.py")
        return Proposal(
            candidate_id=baseline.candidate_id,
            path=dest_dir,
            solution_sha256=sha256_file(dest_dir / "solution.py"),
            source=f"baseline:{baseline.candidate_id}",
            latency_sec=0.0,
            model_calls=0,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            detail={"from_c_star": str(baseline.candidate_id)},
        )

    def propose(self, *, iteration: int, input_candidate: Candidate | None,
                parent: Candidate | None, history: list[dict]) -> Proposal | None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# The injected (deterministic) seam
# ---------------------------------------------------------------------------
class InjectedSolver(Solver):
    """Deterministic proposer driven by a script file — the documented seam.

    Script schema (a0.simpleloop.solver_script/v1):

        {"schema": "a0.simpleloop.solver_script/v1",
         "proposals": [
            {"iteration": 1,
             "kind": "c_star_member", "candidate_id": "c01_good_hex"},
            {"iteration": 2,
             "kind": "literal_solution", "candidate_id": "lit_0001",
             "solution_py": "def pack_circles(n):\n    return []\n"}]}

    A proposal of kind `c_star_member` is a byte copy of that member's directory
    into `<run_dir>/work/iter<k>/<candidate_id>/`; the copy's sha256 is compared
    against the manifest's, so a script cannot smuggle in different bytes under a
    C* id.
    """

    lane = "injected"

    def __init__(self, script_path: Path, work_dir: Path, candidate_set: CandidateSet):
        self.script_path = Path(script_path)
        self.work_dir = Path(work_dir)
        self.candidate_set = candidate_set
        with self.script_path.open("r", encoding="utf-8") as fh:
            script = json.load(fh)
        if script.get("schema") != "a0.simpleloop.solver_script/v1":
            raise SolverError(f"unexpected solver-script schema {script.get('schema')!r}")
        self.proposals = {int(p["iteration"]): p for p in script.get("proposals", [])}
        self.script = script
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def initial_proposal(self, baseline, *, iteration: int = 0) -> Proposal:
        """The script must declare iteration 0, and it must be the C* baseline.

        This is the `c_0 = baseline` rule turned into a check: a solver script
        cannot start the run from an arbitrary candidate.
        """
        proposal = self.propose(iteration=iteration, input_candidate=None, parent=None, history=[])
        if proposal is None:
            raise SolverError(
                "the injected solver script declares no iteration 0; the run must start from the "
                "C* baseline (open_world_plan_review.typ:608)"
            )
        if proposal.candidate_id != baseline.candidate_id:
            raise SolverError(
                f"c_0 must be the C* baseline {baseline.candidate_id!r}; the script starts from "
                f"{proposal.candidate_id!r}"
            )
        return proposal

    def propose(self, *, iteration, input_candidate, parent, history):
        entry = self.proposals.get(iteration)
        if entry is None:
            return None
        started = time.monotonic()
        dest_dir = self.work_dir / f"iter{iteration:03d}" / str(entry.get("candidate_id", "proposal"))
        dest_dir.mkdir(parents=True, exist_ok=True)

        kind = entry.get("kind")
        if kind == "c_star_member":
            member = self.candidate_set.by_id(entry["candidate_id"])
            shutil.copyfile(member.path / "solution.py", dest_dir / "solution.py")
            copied = sha256_file(dest_dir / "solution.py")
            if copied != member.solution_sha256:
                raise CandidateSetError(
                    f"injected copy of {member.candidate_id!r} changed bytes: {copied}"
                )
            candidate_id = entry.get("as_candidate_id", member.candidate_id)
            source = f"injected:c_star_member:{member.candidate_id}"
        elif kind == "literal_solution":
            (dest_dir / "solution.py").write_text(entry["solution_py"], encoding="utf-8")
            copied = sha256_file(dest_dir / "solution.py")
            candidate_id = entry["candidate_id"]
            source = f"injected:literal_solution:{self.script_path.name}"
        else:
            raise SolverError(f"unknown injected proposal kind {kind!r}")

        return Proposal(
            candidate_id=candidate_id,
            path=dest_dir,
            solution_sha256=copied,
            source=source,
            latency_sec=time.monotonic() - started,
            model_calls=0,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            detail={"solver_script": self.script_path.name, "iteration_entry": entry},
        )


# ---------------------------------------------------------------------------
# The intended production lane
# ---------------------------------------------------------------------------
SOLVER_PROMPT = """\
You are improving a solution to the circle-packing task.

The task: write `solution.py` exposing `pack_circles(n)` that returns up to n
circles `(x, y, r)` inside the unit square [0,1]^2, non-overlapping and inside
bounds. The score is the sum of the radii; higher is better. n = {n}.

The current best solution file is `solution.py` in this directory; its score is
{score}.

Write an improved `solution.py` in this directory. Reply only when the file is
written.
"""


def _seed_sha256(dest_dir) -> str | None:
    """sha256 of the seed `solution.py` this lane copied in, if any.

    Recorded before the agent runs so the proposal can say whether the agent
    actually rewrote the file or merely returned it unchanged.
    """
    marker = Path(dest_dir) / ".seed_sha256"
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    return None


def _parse_tokens_used(text: str) -> int | None:
    """Best-effort secondary telemetry: `codex` prints a `tokens used` footer.

    The trace's `secondary.T_in`/`T_out` stay null because the CLI reports one
    total and not a split; the total is recorded in the adapter's own run_meta
    instead of being force-fitted into a field that would mislabel it.
    """
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.lower() == "tokens used" and index + 1 < len(lines):
            digits = re.sub(r"[^0-9]", "", lines[index + 1])
            if digits:
                return int(digits)
    return None


class CliSolver(Solver):
    """`c_{t+1} = Agent(c_t, H_t)` with a real agent CLI.

    VERIFIED end to end for `codex` (2026-09-20). The relay on `127.0.0.1:15722` is
    live once CC Switch's proxy is enabled (`cc-switch -a codex proxy enable &&
    cc-switch daemon start --detach`), and with it:
      * `out/cli-lane/codex-live4/` — exit 0, `codex_i001` scored by E* as `ok`,
        `sum_radii = 2.5414213562373096` against a 0.25 baseline, `validate-run`
        clean (7 events); `out/cli-lane/codex-live3/` — exit 0, `2.6251746109048`.
      * `a0/closure/evidence/13_simpleloop_lane_closed.json` — an independent probe
        that ran a real model turn through *this* argv (rc=0) and whose in-lane
        canary persisted `egress=BLOCKED`; the control
        `13b_simpleloop_lane_open.json` (same lane patched to
        `--sandbox danger-full-access`) persisted `egress=OPEN`, so the probe can
        distinguish the two postures rather than always reporting "blocked".
    The earlier failed rounds remain recorded and are not superseded: against the
    dead relay `out/cli-lane/codex/` exited 8 with `search_failed`, and
    `codex-live`/`codex-live2` were cut by the wall-clock cap before the model
    wrote `solution.py` (`A0_REPORT.md` §6).

    UNVERIFIED: only the `claude` branch. `claude doctor` reports no active
    subscription login (`a0/env/checks/ENV_REPORT.md` §3.2), so `--solver claude`
    is implemented and reviewed but has never been observed producing a proposal.
    Nothing in the A0 verdicts depends on it.
    """

    lane = "cli"

    def __init__(self, cli: str, work_dir: Path, timeout_s: float = 300.0, model: str | None = None):
        self.cli = cli
        self.work_dir = Path(work_dir)
        self.timeout_s = timeout_s
        self.model = model
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _command(self, prompt: str) -> list[str]:
        if self.cli == "codex":
            return ["codex", "exec", "--sandbox", "workspace-write", "--skip-git-repo-check", prompt]
        if self.cli == "claude":
            cmd = ["claude", "-p", prompt, "--permission-mode", "acceptEdits"]
            if self.model:
                cmd += ["--model", self.model]
            return cmd
        raise SolverError(f"unsupported solver CLI {self.cli!r}")

    def propose(self, *, iteration, input_candidate, parent, history):
        dest_dir = self.work_dir / f"iter{iteration:03d}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        seed_dir = input_candidate.path if input_candidate else None
        if seed_dir is not None and (seed_dir / "solution.py").is_file():
            shutil.copyfile(seed_dir / "solution.py", dest_dir / "solution.py")
            (dest_dir / ".seed_sha256").write_text(
                sha256_file(dest_dir / "solution.py"), encoding="utf-8"
            )

        score = None
        if input_candidate is not None:
            for row in history:
                if row.get("candidate_id") == input_candidate.candidate_id:
                    # history rows carry the search signal under `search_signal`;
                    # `c_t`'s score is part of the `H_t` the policy hands to the agent
                    # (plan:610), so losing it here silently weakens the lane.
                    score = row.get("search_signal", row.get("scalar"))
        prompt = SOLVER_PROMPT.format(n=26, score=score if score is not None else "unknown")
        cmd = self._command(prompt)

        started = time.monotonic()
        timed_out = False
        stdout_path = dest_dir / "solver.stdout.txt"
        stderr_path = dest_dir / "solver.stderr.txt"
        # Two things here are deliberate and were both learned from a real run:
        #
        #  * `stdin=DEVNULL` — `codex exec` announces "Reading additional input from
        #    stdin..." and waits for EOF before it starts. Inheriting the caller's
        #    stdin turns a non-interactive run into a hang that looks exactly like a
        #    slow model.
        #  * stdout/stderr go straight to files, not into memory, so a long call can
        #    be watched while it runs and nothing is lost when it is cut off.
        with stdout_path.open("wb") as out_fh, stderr_path.open("wb") as err_fh:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=out_fh,
                stderr=err_fh,
                cwd=str(dest_dir),
            )
            try:
                rc = proc.wait(timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                proc.wait()
                rc = 124
        latency = time.monotonic() - started
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        tokens_total = _parse_tokens_used(stdout + "\n" + stderr)
        if timed_out:
            stderr = f"TimeoutExpired after {self.timeout_s}s (child killed)\n{stderr}"
            stderr_path.write_text(stderr, encoding="utf-8")

        # The transcript is already on disk (streamed while the agent ran); this
        # comment block only records why: a lane that fails is a result (exit 8,
        # failure_stage=search_failed) and the study has to be able to see *where* it
        # stopped, not just that it stopped.

        solution = dest_dir / "solution.py"
        changed = solution.is_file() and sha256_file(solution) != _seed_sha256(dest_dir)
        if rc != 0 or not solution.is_file():
            tail = [line for line in (stdout + "\n" + stderr).splitlines() if line.strip()][-3:]
            raise SolverError(
                f"{self.cli} lane produced no solution.py (exit {rc}"
                f"{', timed out' if timed_out else ''}) after {latency:.1f}s; "
                f"agent output tail: {' | '.join(tail) or 'no output'}; "
                f"full stdout/stderr kept in {dest_dir.name}/solver.stdout.txt and .stderr.txt"
            )
        return Proposal(
            candidate_id=f"{self.cli}_i{iteration:03d}",
            path=dest_dir,
            solution_sha256=sha256_file(solution),
            source=f"cli:{self.cli}",
            latency_sec=latency,
            model_calls=1,
            detail={
                "exit_code": rc,
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
                "solution_changed_from_seed": changed,
                "tokens_total": tokens_total,
            },
        )


def make_solver(kind: str, *, candidate_set: CandidateSet, work_dir: Path, **kwargs) -> Solver:
    if kind == "injected":
        script = kwargs.get("script")
        if not script:
            raise SolverError("--solver injected requires --solver-script")
        return InjectedSolver(Path(script), work_dir, candidate_set)
    if kind in ("codex", "claude"):
        return CliSolver(kind, work_dir, timeout_s=kwargs.get("timeout_s", 300.0))
    raise SolverError(f"unknown solver lane {kind!r}")
