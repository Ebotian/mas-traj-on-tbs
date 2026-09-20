"""A0.2 for EvE: a frequency test on the runtime's real sampling machinery.

Why a frequency test, and why this observable (a0/acceptance/DERIVATIONS.md §1):
EvE's RNG is unseeded (`populations/base.py:40`), so a single run proves nothing. The
`solver_examples` block is rendered into the Phase-2 worker README in *draw order*
(`workspace/immutable_renderers/base.py:179-196`), and with the frozen
`n_solver_examples_phase2 = 4` and a two-member population the *inclusion* statistic is
degenerate (1.0), so only the order statistic carries information.

Seams, all named in the run record:
  S1  ``hydra.utils.instantiate(loop_cfg.sampling[...])`` — the real sampler class with the
      frozen parameters from configs/eve/loop/default.yaml.
  S2  ``Phase2BatchRunner._sample_solvers`` (workflow/phase2.py:597-605) — the real call
      site, including ``rng=self.solver_pop._rng`` (unseeded).
  S3  ``render_immutable_files`` over the real immutable tree, i.e. exactly what
      ``SolverWorkspaceBuilder.write_immutable_assets`` writes into a Phase-2 workspace
      (workspace/solver_workspace.py:194-219); the order is read back out of the rendered
      README, never out of the sampler's return value.
  S4  for the prefill control the sampler is called directly with the arguments the call
      site uses (phase2.py:608-618); ``solver_workspace_builder._rng`` is an unseeded
      ``random.Random()`` (solver_workspace.py:91), which is what is passed here.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats as scipy_stats

from .eve_runtime import EveContext

P0 = 0.7310585786300049  # 1 / (1 + e^-1)

# Pre-registered expected p for the position-0 draw, per population size N (single scalar
# feature, weight 1.0, T = 1.0, no_replacement, num >= N):
#   first_position_top(N) = e^0 / sum_{r<N} e^-r
FIRST_POSITION_TOP = {
    2: 0.7310585786300049,
    3: 0.6652409557748218,
    4: 0.6439142598879724,
    5: 0.6364086465588308,
}
CONDITIONAL_SECOND_TOP_GIVEN_RANK1_FIRST = {
    3: 0.8807970779778823,  # 1 / (1 + e^-2)
    4: 0.8437947344813395,  # 1 / (1 + e^-2 + e^-3)
}


# --------------------------------------------------------------------------------------
# Exact binomial machinery (independent of the pre-registered table)
# --------------------------------------------------------------------------------------


def exact_two_sided_p(k: int, n: int, p0: float) -> float:
    """Two-sided exact binomial p-value, probability-ordering definition (scipy's rule)."""
    if n <= 0:
        return 1.0
    return float(min(1.0, _two_sided_pvals(n, p0)[k]))


def _two_sided_pvals(n: int, p0: float) -> np.ndarray:
    """Vectorised exact two-sided p-value for every k in 0..n (probability-ordering rule).

    An outcome k counts every outcome whose probability is no greater than P(k), which is
    the rule `scipy.stats.binomtest` uses; verified against it in ``selftest`` below.
    """
    k_arr = np.arange(n + 1)
    logpmf = scipy_stats.binom.logpmf(k_arr, n, p0)
    pmf = np.exp(logpmf)
    order = np.argsort(logpmf, kind="stable")
    sorted_log = logpmf[order]
    csum = np.cumsum(pmf[order])
    pos = np.searchsorted(sorted_log, sorted_log + 1e-7, side="right")
    sorted_p = csum[np.clip(pos - 1, 0, None)]
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    return np.minimum(1.0, sorted_p[inverse])


def exact_required_n(
    p0: float, p_alt: float, *, alpha: float = 0.05, power: float = 0.90, n_max: int = 4000
) -> int | None:
    """Smallest n whose exact two-sided test at ``alpha`` reaches ``power`` at ``p_alt``."""
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2)
    z_beta = scipy_stats.norm.ppf(power)
    denom = abs(p_alt - p0)
    if denom == 0:
        return None
    n_start = max(
        2,
        int(
            (
                (z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p_alt * (1 - p_alt)))
                / denom
            )
            ** 2
        )
        - 20,
    )
    for n in range(n_start, n_max + 1):
        k_arr = np.arange(n + 1)
        pvals = _two_sided_pvals(n, p0)
        crit = k_arr[pvals <= alpha]
        if crit.size == 0:
            continue
        power_at = float(np.sum(scipy_stats.binom.pmf(crit, n, p_alt)))
        if power_at >= power:
            return n
    return None


def selftest_pval_against_scipy(samples: list[tuple[int, int, float]]) -> dict[str, Any]:
    """Compare ``exact_two_sided_p`` with ``scipy.stats.binomtest`` on the given samples."""
    out: dict[str, Any] = {}
    worst = 0.0
    for k, n, p0 in samples:
        mine = exact_two_sided_p(k, n, p0)
        theirs = float(scipy_stats.binomtest(k, n, p0).pvalue)
        worst = max(worst, abs(mine - theirs))
        out[f"k={k},n={n},p0={p0}"] = {"mine": mine, "scipy": theirs}
    out["max_abs_diff"] = worst
    out["agree"] = bool(worst < 1e-12)
    return out


def normal_required_n(p0: float, p_alt: float, *, alpha: float = 0.05, power: float = 0.90,
                      one_sided: bool = False) -> int:
    z_alpha = scipy_stats.norm.ppf(1 - (alpha if one_sided else alpha / 2))
    z_beta = scipy_stats.norm.ppf(power)
    return math.ceil(
        (
            (z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p_alt * (1 - p_alt)))
            / abs(p_alt - p0)
        )
        ** 2
    )


def norm_ci(p_hat: float, n: int) -> list[float]:
    se = math.sqrt(max(p_hat * (1 - p_hat), 1e-18) / max(n, 1))
    return [max(0.0, p_hat - 1.96 * se), min(1.0, p_hat + 1.96 * se)]


# --------------------------------------------------------------------------------------
# Population + sampler wiring (the real EvE objects)
# --------------------------------------------------------------------------------------


def build_population(ctx: EveContext, run_dir: Path, scores: dict[str, float],
                     candidate_sources: dict[str, str]):
    """A real ``SolverPopulation`` holding one entry per candidate with a supplied score."""
    from scaling_evolve.algorithms.eve.populations.entry import PopulationEntry
    from scaling_evolve.algorithms.eve.populations.solver_population import SolverPopulation
    from scaling_evolve.storage.artifacts import FSArtifactStore
    from scaling_evolve.storage.sqlite import SQLiteLineageStore

    eve_dir = Path(run_dir) / "eve"
    db_path = eve_dir / "solver_lineage.db"
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()
    lineage = SQLiteLineageStore(db_path)
    artifact_root = eve_dir / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    store = FSArtifactStore(artifact_root, run_id="a0_eve_solver")
    pop = SolverPopulation(lineage, store, run_id="a0_eve_solver", config=ctx.cfg.loop)
    for candidate_id, score in scores.items():
        pop.add(
            PopulationEntry(
                id=candidate_id,
                files={"solution.py": candidate_sources[candidate_id]},
                # a multi-field score, exactly as E*'s Outcome would arrive; scalar() reads
                # the "score" key (populations/score.py:11-33)
                score={"score": float(score), "sum_radii": float(score)},
                logs={},
            )
        )
    return pop


def instantiate_sampler(ctx: EveContext, key: str):
    """Seam S1."""
    from hydra.utils import instantiate

    return instantiate(dict(ctx.cfg.loop.sampling[key]), _convert_="all")


def make_runner(ctx: EveContext, pop, sampler):
    """Seam S2 container: a real Phase2BatchRunner with only the sampling collaborators set."""
    from scaling_evolve.algorithms.eve.workflow.phase2 import Phase2BatchRunner

    return Phase2BatchRunner(
        solver_workspace_builder=None,
        driver=None,
        solver_evaluator=None,
        step_label="a0.2",
        iteration=0,
        total_iterations=None,
        solver_pop=pop,
        optimizer_pop=None,
        n_workers_phase2=int(ctx.cfg.loop.n_workers_phase2),
        n_parallel_phase2=int(ctx.cfg.loop.n_parallel_phase2),
        n_solver_examples_phase2=int(ctx.cfg.loop.n_solver_examples_phase2),
        n_optimizer_examples_phase2=int(ctx.cfg.loop.n_optimizer_examples_phase2),
        n_produced_optimizers_phase2=int(ctx.cfg.loop.n_workers_phase2),
        optimizer_sampler=None,
        solver_sampler=sampler,
        prefill_sampler=None,
        optimizer_examples_sampler=None,
        produced_optimizer_sampler=None,
    )


def sample_solvers(runner):
    """Seam S2: the real call site."""
    return runner._sample_solvers()


def sample_prefill(ctx: EveContext, solvers):
    """Seam S4: the real prefill sampler with the call site's arguments."""
    sampler = instantiate_sampler(ctx, "solver_prefill")
    drawn = sampler.sample(
        solvers, [entry.score for entry in solvers], 1, rng=random.Random()
    )
    return drawn[0] if drawn else None


def read_order_from_readme(ctx: EveContext, solvers, prefill_solver=None) -> list[str]:
    """Seam S3: render the real immutable tree and read the draw order out of README.md."""
    from scaling_evolve.algorithms.eve.workspace.immutable_renderers.base import (
        render_immutable_files,
    )

    rendered = render_immutable_files(
        renderer=ctx.renderer,
        immutable_files=ctx.immutable_files,
        problem=ctx.problem,
        # SolverWorkspaceBuilder stores the *loop* config and passes it here
        # (workspace/solver_workspace.py:49-66, factory.py:323-330), and the renderer reads
        # config.n_optimizer_examples_phase2 from it (immutable_renderers/base.py:113).
        config=ctx.cfg.loop,
        optimizer=None,
        solvers=solvers,
        prefill_solver=prefill_solver,
        optimizer_examples=(),
    )
    readme = rendered.get("README.md")
    if readme is None:
        raise RuntimeError("rendered immutable tree has no README.md")
    order: list[str] = []
    prefill_marked: str | None = None
    for line in readme.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- `solver_examples/"):
            continue
        entry = stripped[len("- `solver_examples/") :].split("`", 1)[0].rstrip("/")
        order.append(entry)
        if "<- prefill" in stripped:
            prefill_marked = entry
    if not order:
        raise RuntimeError(
            "the {solver_examples_block} observable is missing from the rendered README; "
            "the A0.2 order test would measure nothing (DERIVATIONS.md F3)"
        )
    return order, prefill_marked


# --------------------------------------------------------------------------------------
# Case results
# --------------------------------------------------------------------------------------


@dataclass
class CaseResult:
    name: str
    check_point: str
    policy: str
    observable: str
    population: list[str]
    scores: dict[str, float]
    num: int
    n_iterations: int
    statistic: str
    successes: int
    p_hat: float
    p0: float
    p_alt_tested: float | None
    alternative: str
    p_value: float
    reject_h0: bool
    ci95: list[float]
    required_n: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "check_point": self.check_point,
            "policy": self.policy,
            "observable": self.observable,
            "population": self.population,
            "scores": self.scores,
            "num": self.num,
            "n_iterations": self.n_iterations,
            "statistic": self.statistic,
            "successes": self.successes,
            "p_hat": self.p_hat,
            "p0": self.p0,
            "p_alt_tested": self.p_alt_tested,
            "alternative": self.alternative,
            "p_value": self.p_value,
            "reject_h0": self.reject_h0,
            "ci95": self.ci95,
            "required_n": self.required_n,
            "extra": self.extra,
        }


@dataclass
class A02Report:
    cases: list[CaseResult] = field(default_factory=list)
    observable_self_check: dict[str, Any] = field(default_factory=dict)
    seams: list[dict[str, str]] = field(default_factory=list)
    frozen_config: dict[str, Any] = field(default_factory=dict)
    power_table_reproduced: dict[str, Any] = field(default_factory=dict)
    iterations_total: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "cases": [case.to_json() for case in self.cases],
            "observable_self_check": self.observable_self_check,
            "seams": self.seams,
            "frozen_config": self.frozen_config,
            "power_table_reproduced": self.power_table_reproduced,
            "iterations_total": self.iterations_total,
        }
