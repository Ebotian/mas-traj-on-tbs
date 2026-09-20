#!/usr/bin/env python3
"""Independent numerical cross-check of the A0.2 pre-registered expectations.

This script does three things:

1. It *executes the real runtime source* wherever that is possible without
   installing the runtime:
     - EvE's sampler classes are loaded from the pinned checkout via
       ``importlib`` with a stub ``optree`` module (the samplers need nothing
       from optree on the code paths exercised here).
     - Loreley's ``ParetoGridArchive`` is loaded directly; it is numpy-only.
     - KAPSO's selection keys are transcribed from source with `path:line`
       citations next to the transcription (its modules drag in sqlalchemy /
       loguru / rich, so they cannot be imported here).
2. It prints closed-form vs simulated values side by side with the
   discrepancy, for every probabilistic expectation.
3. It fails loudly (non-zero exit, ``DISAGREEMENT`` lines) if any closed form
   and its simulation disagree beyond tolerance.

Usage:
    python3 simulate.py                 # run the checks, print a report
    python3 simulate.py --emit-json     # additionally rewrite expected_values.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
import types
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent

EVE_ROOT = Path("/tmp/eve")
LOR_ROOT = Path("/tmp/lor")
EVE_COMMIT = "979065fd2cf1b3be9caf70596478fe27df7815ad"
LOR_NOTE = (
    "copy at /tmp/lor, blob-identical to pin "
    "4c3759208e6b908f90716488ac3eec3dceaaf397 (591/592; 1 submodule gitlink)"
)

DRAWS = 1_000_000
TOL = 3.0e-3  # 3 sigma-ish at DRAWS=1e6 for p in [0.25, 0.88]; see tail_check() below


# --------------------------------------------------------------------------
# Loader: real EvE sampler code with a stub `optree`
# --------------------------------------------------------------------------

class _StubOptree(types.ModuleType):
    """Minimal stand-in for the parts of optree the samplers touch.

    EvE's RankExponentialSumSampler calls ``optree.tree_flatten_with_path``
    with an ``is_leaf`` predicate (rank_softmax.py:111-116) and then walks the
    returned key paths with plain dict indexing (rank_softmax.py:136-143), so a
    recursive walk over dict/list/tuple containers is behaviourally identical
    for every tree EvE actually builds. The stub is *validated* by the
    RankExponentialSumSampler-vs-RankSoftmaxSampler equivalence check below:
    RankSoftmaxSampler never touches optree, so a wrong stub would show up as a
    disagreement on that pair.
    """

    PyTree = object

    @staticmethod
    def tree_flatten_with_path(tree, is_leaf=None):
        paths: list[tuple] = []
        leaves: list = []

        def walk(node, path):
            if is_leaf is not None and is_leaf(node):
                paths.append(path)
                leaves.append(node)
                return
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, path + (key,))
                return
            if isinstance(node, (list, tuple)):
                for index, value in enumerate(node):
                    walk(value, path + (index,))
                return
            paths.append(path)
            leaves.append(node)

        walk(tree, ())
        return paths, leaves, None


def _load_eve_samplers():
    """Import EvE's sampler modules straight out of the pinned checkout."""
    for name in (
        "scaling_evolve",
        "scaling_evolve.algorithms",
        "scaling_evolve.algorithms.eve",
        "scaling_evolve.algorithms.eve.populations",
        "scaling_evolve.algorithms.eve.populations.samplers",
    ):
        pkg = types.ModuleType(name)
        pkg.__path__ = []
        sys.modules[name] = pkg
    sys.modules["optree"] = _StubOptree("optree")

    def load(mod_name: str, rel_path: str):
        spec = importlib.util.spec_from_file_location(mod_name, EVE_ROOT / rel_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        return module

    load(
        "scaling_evolve.algorithms.eve.populations.score",
        "src/scaling_evolve/algorithms/eve/populations/score.py",
    )
    load(
        "scaling_evolve.algorithms.eve.populations.samplers.base",
        "src/scaling_evolve/algorithms/eve/populations/samplers/base.py",
    )
    rank = load(
        "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax",
        "src/scaling_evolve/algorithms/eve/populations/samplers/rank_softmax.py",
    )
    unif = load(
        "scaling_evolve.algorithms.eve.populations.samplers.uniform",
        "src/scaling_evolve/algorithms/eve/populations/samplers/uniform.py",
    )
    return rank, unif


def _load_loreley_archive():
    spec = importlib.util.spec_from_file_location(
        "lor_pareto_archive", LOR_ROOT / "loreley/core/map_elites/pareto_archive.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["lor_pareto_archive"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Exact mathematics (no runtime code involved)
# --------------------------------------------------------------------------

def rank_weights(n: int, temperature: float = 1.0, feature_weight: float = 1.0):
    """w_rank = feature_weight * exp(-rank / temperature).

    EvE `rank_softmax.py:181` (RankSoftmaxSampler) and `rank_softmax.py:104`
    (RankExponentialSumSampler, single scalar feature) both reduce to this.
    """
    return [feature_weight * math.exp(-(rank / temperature)) for rank in range(n)]


def first_draw_prob(n: int, temperature: float = 1.0) -> float:
    """P(the rank-0 item is picked by the *first* draw) = w_0 / sum(w).

    The first draw is always taken against the full weight vector regardless
    of `num` and regardless of replacement mode (`samplers/base.py:41-64`
    never rewrites the weights; it only removes the drawn item).
    """
    w = rank_weights(n, temperature)
    return w[0] / sum(w)


def pl_set_probabilities(weights):
    """Exact no-replacement prefix-set distribution (Plackett-Luce).

    `samplers/base.py:41-64` draws the next item proportional to the
    *original* weights restricted to the remaining items, so the probability
    of one ordered sequence is prod_j w_{i_j} / (W - sum_{k<j} w_{i_k}).
    Summing over orderings by subset DP gives the exact set probability.
    `weights` must be positive.
    """
    n = len(weights)
    total = sum(weights)
    # dp[mask] = sum over orderings of `mask` of the ordered-sequence probability
    size = 1 << n
    dp = [0.0] * size
    dp[0] = 1.0
    weight_of = [0.0] * size
    for mask in range(1, size):
        low = mask & -mask
        idx = low.bit_length() - 1
        weight_of[mask] = weight_of[mask ^ low] + weights[idx]
    for mask in range(1, size):
        acc = 0.0
        rest = mask
        while rest:
            low = rest & -rest
            idx = low.bit_length() - 1
            prev = mask ^ low
            acc += dp[prev] * weights[idx] / (total - weight_of[prev])
            rest ^= low
        dp[mask] = acc
    return dp, weight_of


def inclusion_prob(weights, target_index: int, num: int) -> float:
    """P(item `target_index` is among the first `num` no-replacement draws)."""
    n = len(weights)
    m = min(num, n)
    if m >= n:
        return 1.0
    dp, weight_of = pl_set_probabilities(weights)
    others = [i for i in range(n) if i != target_index]
    total = 0.0
    for bits in range(1 << len(others)):
        if bin(bits).count("1") != m:
            continue
        mask = 0
        for j, idx in enumerate(others):
            if bits >> j & 1:
                mask |= 1 << idx
        total += dp[mask]
    return 1.0 - total


def position_prob(weights, target_index: int, position: int) -> float:
    """P(item `target_index` lands in `position` (0-based) of the draw order)."""
    n = len(weights)
    if position >= n:
        return 0.0
    dp, weight_of = pl_set_probabilities(weights)
    total = 0.0
    others = [i for i in range(n) if i != target_index]
    for bits in range(1 << len(others)):
        if bin(bits).count("1") != position:
            continue
        mask = 0
        for j, idx in enumerate(others):
            if bits >> j & 1:
                mask |= 1 << idx
        total += dp[mask] * weights[target_index] / (
            sum(weights) - weight_of[mask]
        )
    return total


# --------------------------------------------------------------------------
# Monte Carlo against the real sampler code
# --------------------------------------------------------------------------

def mc_real_sampler(sampler, items, scores, num, trials, seed, observe):
    """Drive the real sampler `trials` times and fold `observe` over results."""
    rng = random.Random(seed)
    counts = {}
    for _ in range(trials):
        out = sampler.sample(items, scores, num, rng=rng)
        key = observe(out)
        counts[key] = counts.get(key, 0) + 1
    return {key: value / trials for key, value in counts.items()}


def wilson_halfwidth(p: float, n: int, z: float = 3.0) -> float:
    return z * math.sqrt(max(p * (1.0 - p), 1e-12) / n)


# --------------------------------------------------------------------------
# KAPSO: transcribed deterministic keys (source cited inline)
# --------------------------------------------------------------------------

def kapso_best_experiment(nodes):
    """Transcription of GenericSearch.get_best_experiment.

    Source: kapso_ck/kapso src/kapso/execution/search_strategies/generic/strategy.py:1424-1434
      valid = [n for n in node_history
               if not n.had_error and n.evaluation_valid and n.score is not None]
      return max(valid, key=lambda x: x.score if maximize_scoring else -x.score)
    """
    valid = [
        n
        for n in nodes
        if not n["had_error"] and n["evaluation_valid"] and n["score"] is not None
    ]
    if not valid:
        return None
    maximize = True  # kapso/environment/handlers/base.py:48  maximize_scoring: bool = True
    return max(valid, key=lambda x: x["score"] if maximize else -x["score"])


def kapso_select_committed(nodes, evaluator_id, maximize=True):
    """Transcription of select_committed_candidate.

    Source: kapso_ck/kapso src/kapso/execution/fidelity.py:184-213
      eligible = [n for n in nodes
                  if not had_error and evaluation_valid
                  and evidence_tier(n, evaluator_id) > TIER_PROBE]
      return max(eligible, key=lambda n: (evidence_tier(n, evaluator_id),
                                          sign * full_eval_score(n, evaluator_id)))
    evidence_tier: fidelity.py:156-168 (2 full / 1 validated / 0 probe)
    full_eval_score: fidelity.py:171-182 (mean over attempts with
        evaluator_id match and fidelity == "full")
    """
    sign = 1.0 if maximize else -1.0

    def tier(node):
        if not any(
            a["evaluator_id"] == evaluator_id and a["fidelity"] == "full"
            for a in node["attempts"]
        ):
            return 0
        return 2 if node.get("build_fidelity", "full") == "full" else 1

    def full_score(node):
        matching = [
            a["score"]
            for a in node["attempts"]
            if a["evaluator_id"] == evaluator_id and a["fidelity"] == "full"
        ]
        return None if not matching else sum(matching) / len(matching)

    eligible = [
        n
        for n in nodes
        if not n["had_error"] and n["evaluation_valid"] and tier(n) > 0
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda n: (tier(n), sign * full_score(n)))


def kapso_manifest_class_ok(manifest, granted):
    """Transcription of the granted-class gate.

    Source: kapso_ck/kapso src/kapso/execution/search_strategies/generic/registered_evaluation.py:87-91
      manifest["fidelity"] != granted.eval_fidelity
      or abs(manifest["fraction"] - granted.eval_fraction) > 1e-9
      or int(manifest["seed"]) != registered_subsample_seed
    Note: no evaluator field exists in the manifest line.
    """
    return (
        manifest["fidelity"] == granted["eval_fidelity"]
        and abs(float(manifest["fraction"]) - granted["eval_fraction"]) <= 1e-9
        and int(manifest["seed"]) == granted["seed"]
    )


# --------------------------------------------------------------------------
# Power analysis
# --------------------------------------------------------------------------

def n_normal(p0: float, p1: float, alpha: float, power: float, sides: int) -> int:
    z_a = stats.norm.ppf(1 - alpha / sides)
    z_b = stats.norm.ppf(power)
    num = z_b * math.sqrt(p1 * (1 - p1)) + z_a * math.sqrt(p0 * (1 - p0))
    return math.ceil(num**2 / (p1 - p0) ** 2)


def n_exact_binomial(p0: float, p1: float, alpha: float, power: float, sides: int,
                     cap: int = 200_000):
    """Smallest n whose exact binomial test reaches `power` against p1.

    The rejection direction follows the sign of (p1 - p0) for the one-sided
    case; the two-sided case sums both tails' rejection probabilities.
    """
    direction = 1 if p1 > p0 else -1
    n = 1
    while n <= cap:
        if sides == 2:
            crit_hi = int(stats.binom.isf(alpha / 2, n, p0)) + 1
            while crit_hi <= n and stats.binom.sf(crit_hi - 1, n, p0) > alpha / 2:
                crit_hi += 1
            crit_lo = int(stats.binom.ppf(alpha / 2, n, p0))
            while crit_lo >= 0 and stats.binom.cdf(crit_lo, n, p0) > alpha / 2:
                crit_lo -= 1
            realised = stats.binom.sf(crit_hi - 1, n, p0) + stats.binom.cdf(crit_lo, n, p0)
            achieved = stats.binom.sf(crit_hi - 1, n, p1) + stats.binom.cdf(crit_lo, n, p1)
        elif direction > 0:
            crit_hi = int(stats.binom.isf(alpha, n, p0)) + 1
            while crit_hi <= n and stats.binom.sf(crit_hi - 1, n, p0) > alpha:
                crit_hi += 1
            realised = stats.binom.sf(crit_hi - 1, n, p0)
            achieved = stats.binom.sf(crit_hi - 1, n, p1)
        else:
            crit_lo = int(stats.binom.ppf(alpha, n, p0))
            while crit_lo >= 0 and stats.binom.cdf(crit_lo, n, p0) > alpha:
                crit_lo -= 1
            realised = stats.binom.cdf(crit_lo, n, p0)
            achieved = stats.binom.cdf(crit_lo, n, p1)
        if realised <= alpha and achieved >= power:
            return n
        n += 1
    return None


def power_row(label, p0, p1, alpha=0.05, power=0.9, sides=2):
    if p1 == p0:
        return None
    return {
        "alternative": label,
        "p_alt": p1,
        "delta": p1 - p0,
        "n_normal_approx": n_normal(p0, p1, alpha, power, sides),
        "n_exact_binomial": n_exact_binomial(p0, p1, alpha, power, sides),
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-json", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()
    trials = args.draws

    rank, unif = _load_eve_samplers()
    RS = rank.RankSoftmaxSampler
    RES = rank.RankExponentialSumSampler
    U = unif.UniformSampler
    lor = _load_loreley_archive()

    out = {
        "provenance": {
            "eve_checkout": str(EVE_ROOT),
            "eve_commit": EVE_COMMIT,
            "loreley_source": LOR_NOTE,
            "simulated_draws_per_case": trials,
            "tolerance": TOL,
        },
        "eve": {},
        "loreley": {},
        "kapso": {},
        "simpleloop": {},
        "power": {},
    }

    failures = []
    lines = []

    def emit(text=""):
        lines.append(text)
        print(text)

    def check(name, closed, sim, tol=TOL):
        disc = abs(closed - sim)
        ok = disc <= tol
        flag = "ok" if ok else "DISAGREEMENT"
        emit(
            f"  {name:<62s} closed={closed:.6f}  sim={sim:.6f}  "
            f"|diff|={disc:.6f}  {flag}"
        )
        if not ok:
            failures.append(
                f"{name}: closed={closed:.9f} simulated={sim:.9f} diff={disc:.9f}"
            )
        return {"closed_form": closed, "simulated": sim, "abs_diff": disc}

    def fmt_weights(w):
        return "[" + ", ".join(f"{x:.6f}" for x in w) + "]"

    # ---------------------------------------------------------------- header
    emit("=" * 100)
    emit("A0.2 independent cross-check: closed form vs simulation of the real sampler code")
    emit("=" * 100)
    emit(f"EvE checkout      : {EVE_ROOT} @ {EVE_COMMIT[:8]}")
    emit(f"Loreley source    : {LOR_NOTE}")
    emit(f"Draws per case    : {trials:,}")
    emit(f"Agreement tol     : {TOL}")
    emit()
    emit("sanity: the loaded sampler classes really are EvE's")
    emit(f"  RankSoftmaxSampler        -> {RS.__module__}")
    emit(f"  RankExponentialSumSampler -> {RES.__module__}")
    emit(f"  UniformSampler            -> {U.__module__}")
    emit(f"  ParetoGridArchive         -> {lor.ParetoGridArchive.__module__}")
    emit()

    # ------------------------------------------------- EvE closed-form table
    emit("-" * 100)
    emit("1. EvE: induced sampling distribution")
    emit("-" * 100)
    emit("weights w_rank = weight * exp(-rank / T)  [rank_softmax.py:104 and :181]")
    for n in (2, 3, 4):
        emit(f"  N={n}, T=1: {fmt_weights(rank_weights(n))}")
    emit()

    p_claim = first_draw_prob(2, 1.0)
    emit(f"protocol claim 1/(1+e^-1) = {p_claim:.12f}")
    emit()

    items2 = ["c1", "c2"]
    scores2 = [{"score": 10.0}, {"score": 0.0}]  # c1 strictly higher
    items4 = ["c1", "c2", "c3", "c4"]
    scores4 = [{"score": 4.0 - i} for i in range(4)]
    items8 = [f"c{i+1}" for i in range(8)]
    scores8 = [{"score": 100.0 - i} for i in range(8)]
    items10 = [f"c{i+1}" for i in range(10)]
    scores10 = [{"score": 100.0 - i} for i in range(10)]

    emit("1a. RankSoftmaxSampler, k=2, T=1, single draw (num=1, no_replacement)")
    sampler = RS(temperature=1.0, replacement_mode="no_replacement")
    sim = mc_real_sampler(sampler, items2, scores2, 1, trials, 11, lambda o: o[0])
    out["eve"]["rank_softmax_k2_T1_num1_first"] = check(
        "P(first drawn == c1)", p_claim, sim.get("c1", 0.0)
    )
    out["eve"]["rank_softmax_k2_T1_num1_first"]["decision_rule"] = (
        "count how often sample()[0] is the higher-scoring candidate"
    )
    emit()

    emit("1b. RankSoftmaxSampler, k=2, T=1, num=4, no_replacement")
    sampler = RS(temperature=1.0, replacement_mode="no_replacement")
    sim_first = mc_real_sampler(sampler, items2, scores2, 4, trials, 12, lambda o: o[0])
    sim_inc = mc_real_sampler(
        sampler, items2, scores2, 4, trials, 13, lambda o: "c1" if "c1" in o else "c2"
    )
    out["eve"]["rank_softmax_k2_T1_num4_first_position"] = check(
        "P(first position == c1)  [first draw, num capped at N]", p_claim, sim_first.get("c1", 0.0)
    )
    out["eve"]["rank_softmax_k2_T1_num4_inclusion"] = check(
        "P(c1 in returned set)     [num=4 capped to N=2]", 1.0, sim_inc.get("c1", 0.0)
    )
    out["eve"]["rank_softmax_k2_T1_num4_first_position"]["note"] = (
        "num=min(4, N)=2 (samplers/base.py:34): both candidates always returned, "
        "so only the *order* carries score information"
    )
    emit()

    emit("1c. RankSoftmaxSampler, N=4, T=1, num=4, no_replacement (population == candidate set)")
    sampler = RS(temperature=1.0, replacement_mode="no_replacement")
    closed_n4 = first_draw_prob(4, 1.0)
    sim_n4 = mc_real_sampler(sampler, items4, scores4, 4, trials, 14, lambda o: o[0])
    out["eve"]["rank_softmax_N4_T1_num4_first_position"] = check(
        "P(first position == highest scoring)", closed_n4, sim_n4.get("c1", 0.0)
    )
    out["eve"]["rank_softmax_N4_T1_num4_inclusion"] = check(
        "P(highest scoring in returned set)", 1.0,
        mc_real_sampler(sampler, items4, scores4, 4, trials, 15,
                        lambda o: "c1" if "c1" in o else "other").get("c1", 0.0),
    )
    emit()

    emit("1d. RankExponentialSumSampler, features.score weight=1.0 T=1.0 "
         "(solver_examples config, loop/default.yaml:26-34)")
    res = RES(features={"score": {"weight": 1.0, "temperature": 1.0}},
              replacement_mode="no_replacement")
    sim = mc_real_sampler(res, items2, scores2, 1, trials, 16, lambda o: o[0])
    out["eve"]["rank_exp_sum_k2_num1_first"] = check(
        "P(first drawn == c1)      [== RankSoftmaxSampler]", p_claim, sim.get("c1", 0.0)
    )
    sim = mc_real_sampler(res, items2, scores2, 4, trials, 17, lambda o: o[0])
    out["eve"]["rank_exp_sum_k2_num4_first_position"] = check(
        "P(first position == c1)   [n=4, no_replacement, N=2]", p_claim, sim.get("c1", 0.0)
    )
    sim = mc_real_sampler(
        res, items4, scores4, 4, trials, 18,
        lambda o: "c1" if "c1" in o else "other",
    )
    out["eve"]["rank_exp_sum_k2_num4_inclusion_N4"] = check(
        "P(c1 in returned set)     [n=4, N=4 -> deterministic 1]", 1.0, sim.get("c1", 0.0)
    )
    emit()

    emit("1e. second and later draws keep the ORIGINAL weights "
         "(samplers/base.py:41-64 never re-ranks the remainder)")
    items3 = ["c1", "c2", "c3"]
    scores3 = [{"score": 3.0}, {"score": 2.0}, {"score": 1.0}]
    sampler = RS(temperature=1.0, replacement_mode="no_replacement")
    closed_second3 = 1.0 / (1.0 + math.exp(-2.0))
    sim3 = mc_real_sampler(
        sampler, items3, scores3, 2, trials, 19,
        lambda o: f"first={o[0]},second={o[1]}",
    )
    denom3 = sum(
        sim3.get(f"first=c2,second={x}", 0.0) for x in ("c1", "c3")
    )
    cond3 = sim3.get("first=c2,second=c1", 0.0) / denom3
    out["eve"]["conditional_second_draw_N3"] = check(
        "P(c1 2nd | c2 1st), N=3  [weights 1 vs e^-2]", closed_second3, cond3
    )
    emit("    (this is the check that would FAIL if the implementation re-ranked the "
         "remainder: it would give 1/(1+e^-1)=0.7310586 instead)")
    closed_second4 = 1.0 / (1.0 + math.exp(-2.0) + math.exp(-3.0))
    sim4 = mc_real_sampler(
        sampler, items4, scores4, 2, trials, 29,
        lambda o: f"first={o[0]},second={o[1]}",
    )
    denom4 = sum(
        sim4.get(f"first=c2,second={x}", 0.0) for x in ("c1", "c3", "c4")
    )
    cond4 = sim4.get("first=c2,second=c1", 0.0) / denom4
    out["eve"]["conditional_second_draw_N4"] = check(
        "P(c1 2nd | c2 1st), N=4  [weights 1 vs e^-2 vs e^-3]", closed_second4, cond4
    )
    out["eve"]["conditional_second_draw_N4"]["note"] = (
        "the conditional depends on the whole remainder, because the remainder is never "
        "re-ranked; a re-ranking implementation would return 1/(1+e^-2)=0.8807971, i.e. "
        "the N=3 answer, for both populations"
    )
    emit()

    emit("1f. score-independent control: UniformSampler (solver_prefill, "
         "loop/default.yaml:35-38, uniform.py:27-36 discards scores)")
    us = U(replacement_mode="no_replacement")
    sim = mc_real_sampler(us, items2, scores2, 1, trials, 20, lambda o: o[0])
    out["eve"]["uniform_N2_num1_first"] = check("P(first == c1), N=2, num=1", 0.5, sim.get("c1", 0.0))
    sim = mc_real_sampler(us, items4, scores4, 1, trials, 21, lambda o: o[0])
    out["eve"]["uniform_N4_num1_first"] = check("P(first == c1), N=4, num=1", 0.25, sim.get("c1", 0.0))
    # the same sampler fed the *reversed* score order must give the same answer
    sim_rev = mc_real_sampler(us, items4, list(reversed(scores4)), 1, trials, 21, lambda o: o[0])
    out["eve"]["uniform_score_invariance"] = check(
        "P(first == c1) with c1 scored LAST (score independence)", 0.25, sim_rev.get("c1", 0.0)
    )
    emit()

    emit("1g. replacement_mode=auto top-up (working_optimizer, loop/default.yaml:12-16)")
    sampler = RS(temperature=1.0, replacement_mode="auto")
    sim = mc_real_sampler(sampler, items2, scores2, 4, trials, 22, lambda o: o[0])
    out["eve"]["auto_N2_num4_first_position"] = check(
        "P(first == c1) [auto: no_replacement then with-replacement top-up]",
        p_claim, sim.get("c1", 0.0),
    )
    emit("  top-up slots use the ORIGINAL weights, so P(c1) = 0.7310586 at every slot:")
    sim = mc_real_sampler(sampler, items2, scores2, 4, trials, 23, lambda o: o[3])
    out["eve"]["auto_N2_num4_fourth_slot"] = check(
        "P(4th slot == c1)", p_claim, sim.get("c1", 0.0)
    )
    emit()

    emit("1h. N > n: inclusion of the top candidate in the first 4 draws of the "
         "solver_examples population")
    for n, items_n, scores_n in ((8, items8, scores8), (10, items10, scores10)):
        w = rank_weights(n)
        sampler = RS(temperature=1.0, replacement_mode="no_replacement")
        closed = inclusion_prob(w, 0, 4)
        sim = mc_real_sampler(
            sampler, items_n, scores_n, 4, trials, 30 + n,
            lambda o: "c1" if "c1" in o else "other",
        )["c1"]
        out["eve"][f"inclusion_top_in_first4_N{n}"] = check(
            f"P(c1 in first 4 | N={n}, num=4)", closed, sim
        )
        out["eve"][f"inclusion_top_in_first4_N{n}"]["closed_form_note"] = (
            "exact subset DP over the Plackett-Luce set distribution"
        )
    emit()

    emit("1i. exact inclusion / position table for the no_replacement path "
         "(closed form only, subset DP)")
    table = {}
    for n in range(2, 11):
        w = rank_weights(n)
        table[n] = {
            "first_position_top": first_draw_prob(n, 1.0),
            "inclusion_top_num1": inclusion_prob(w, 0, 1),
            "inclusion_top_num4": inclusion_prob(w, 0, 4),
            "second_position_top": position_prob(w, 0, 1),
        }
        emit(f"  N={n:>2d}  P(pos0=c1)={table[n]['first_position_top']:.9f}  "
             f"P(c1 in 1)={table[n]['inclusion_top_num1']:.9f}  "
             f"P(c1 in 4)={table[n]['inclusion_top_num4']:.9f}  "
             f"P(pos1=c1)={table[n]['second_position_top']:.9f}")
    out["eve"]["closed_form_table"] = table
    out["eve"]["closed_form_table_note"] = (
        "all values for a population whose score order is strict, T=1, one scalar feature"
    )
    emit()

    # ------------------------------------------------------ Loreley archive
    emit("-" * 100)
    emit("2. Loreley: archived behaviour of the real ParetoGridArchive "
         "(pareto_archive.py)")
    emit("-" * 100)
    emit("frozen defaults: objectives=((composite_score, max),) [config.py:916-919], "
         "epsilon=1e-9 [config.py:924-927], max_front_size=8 [config.py:920-923], "
         "admission_policy=pareto [config.py:928-930]")
    emit()

    def mk(h, score, measures, ts=0.0):
        return lor.ParetoCandidate(
            commit_hash=h,
            objective_values=(score,),
            objective_scores=(score,),
            measures=tuple(measures),
            timestamp=ts,
        )

    def front(archive, cell):
        return tuple(c.commit_hash for c in archive.front(cell))

    # 2a same cell, higher score replaces
    arc = lor.ParetoGridArchive(dims=(32, 32), ranges=((0.0, 1.0), (0.0, 1.0)),
                                objective_count=1, max_front_size=8, epsilon=1e-9)
    o2 = arc.add(mk("c2", 1.0, (0.10, 0.10)))
    o1 = arc.add(mk("c1", 2.0, (0.11, 0.11)))  # same cell as c2 (0.10/0.11 -> cell 3)
    same_cell = o1.cell_index == o2.cell_index
    emit("2a. same cell, E(c1) > E(c2): c1 must replace c2")
    emit(f"  cell(c2)={o2.cell_index}  cell(c1)={o1.cell_index}  same_cell={same_cell}")
    emit(f"  add(c2): retained={o2.retained} removed={o2.removed_commit_hashes}")
    emit(f"  add(c1): retained={o1.retained} removed={o1.removed_commit_hashes}")
    emit(f"  front(cell)={front(arc, o1.cell_index)}")
    ok = (
        same_cell
        and o2.retained
        and o1.retained
        and o1.removed_commit_hashes == ("c2",)
        and front(arc, o1.cell_index) == ("c1",)
    )
    emit(f"  ASSERTION same-cell replacement: {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("Loreley same-cell replacement assertion failed")
    out["loreley"]["same_cell_replacement"] = {
        "cell_index": o1.cell_index,
        "c1_retained": o1.retained,
        "c1_removed": list(o1.removed_commit_hashes),
        "front_after": list(front(arc, o1.cell_index)),
        "pass": ok,
    }
    emit()

    # 2b different cells: higher score must NOT evict
    arc2 = lor.ParetoGridArchive(dims=(32, 32), ranges=((0.0, 1.0), (0.0, 1.0)),
                                 objective_count=1, max_front_size=8, epsilon=1e-9)
    ob = arc2.add(mk("c2", 1.0, (0.10, 0.10)))   # cell A
    oa = arc2.add(mk("c1", 2.0, (0.80, 0.80)))   # cell B, much higher score
    cross_equal = oa.cell_index != ob.cell_index
    ok = (
        cross_equal
        and oa.retained
        and oa.removed_commit_hashes == ()
        and ob.removed_commit_hashes == ()
        and front(arc2, ob.cell_index) == ("c2",)
        and front(arc2, oa.cell_index) == ("c1",)
    )
    emit("2b. NEGATIVE CONTROL: different cells, E(c1) > E(c2): nothing evicted")
    emit(f"  cell(c2)={ob.cell_index}  cell(c1)={oa.cell_index}  different_cells={cross_equal}")
    emit(f"  add(c1): retained={oa.retained} removed={oa.removed_commit_hashes}")
    emit(f"  front(cell A)={front(arc2, ob.cell_index)}  front(cell B)={front(arc2, oa.cell_index)}")
    emit(f"  ASSERTION cross-cell non-eviction: {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("Loreley cross-cell non-eviction assertion failed")
    out["loreley"]["cross_cell_non_eviction"] = {
        "cell_c2": ob.cell_index,
        "cell_c1": oa.cell_index,
        "c1_removed": list(oa.removed_commit_hashes),
        "front_c2_cell": list(front(arc2, ob.cell_index)),
        "front_c1_cell": list(front(arc2, oa.cell_index)),
        "pass": ok,
    }
    emit()

    # 2b2 stronger control: the WORSE candidate is admitted when its cell is free
    arc2b = lor.ParetoGridArchive(dims=(32, 32), ranges=((0.0, 1.0), (0.0, 1.0)),
                                  objective_count=1, max_front_size=8, epsilon=1e-9)
    oh = arc2b.add(mk("c_high", 9.0, (0.10, 0.10)))
    ol = arc2b.add(mk("c_low", 1.0, (0.70, 0.70)))
    ok = oh.retained and ol.retained and ol.removed_commit_hashes == () and len(arc2b.records()) == 2
    emit("2b2. NEGATIVE CONTROL (strong): a strictly WORSE candidate must still be "
         "admitted when its cell is free -> admission is not a global argmax")
    emit(f"  add(c_low=1.0): retained={ol.retained} removed={ol.removed_commit_hashes}  "
         f"archive members={[c.commit_hash for c in arc2b.records()]}")
    emit(f"  ASSERTION no-global-argmax: {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("Loreley no-global-argmax control failed")
    out["loreley"]["worse_candidate_admitted"] = {
        "c_low_retained": ol.retained,
        "archive_members": sorted(c.commit_hash for c in arc2b.records()),
        "pass": ok,
    }
    emit()

    # 2c epsilon tie: gap <= epsilon is NOT a dominance decision
    arc3 = lor.ParetoGridArchive(dims=(32, 32), ranges=((0.0, 1.0), (0.0, 1.0)),
                                 objective_count=1, max_front_size=8, epsilon=1e-9)
    t2 = arc3.add(mk("zzz", 1.0, (0.10, 0.10)))
    t1 = arc3.add(mk("aaa", 1.0 + 1e-12, (0.10, 0.10)))
    tie_front = front(arc3, t1.cell_index)
    emit("2c. epsilon tie: score gap 1e-12 <= epsilon=1e-9 is NOT dominance; the "
         "commit_hash-ordered representative wins (pareto_archive.py:425-431)")
    emit(f"  incoming 'aaa' (score 1.0+1e-12) vs incumbent 'zzz' (1.0) -> front={tie_front}")
    emit(f"  => the winner is decided by commit_hash, NOT by the score")
    out["loreley"]["epsilon_tie_uses_commit_hash"] = {
        "gap": 1e-12,
        "front_after": list(tie_front),
        "winner": tie_front[0] if tie_front else None,
    }
    emit()

    # 2d single-objective front can never exceed 1 member
    arc4 = lor.ParetoGridArchive(dims=(32,), ranges=((0.0, 1.0),),
                                 objective_count=1, max_front_size=8, epsilon=1e-9)
    for i in range(12):
        arc4.add(mk(f"k{i:02d}", float(i), (0.5,)))
    sizes = {cell: len(arc4.front(cell)) for cell in sorted(arc4._fronts)}
    kept = sorted(c.commit_hash for c in arc4.records())
    ok = all(s == 1 for s in sizes.values()) and kept == ["k11"]
    emit("2d. single objective: every cell front has size 1, so the archive keeps exactly the "
         "per-cell argmax and (via scheduler/main.py:876-931) the report branch is the argmax "
         "over everything evaluated")
    emit(f"  12 candidates all in cell 16, scores 0..11 -> fronts={sizes} members={kept}")
    emit(f"  ASSERTION per-cell argmax (k11 wins, k00..k10 evicted): {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("Loreley per-cell argmax assertion failed")
    out["loreley"]["single_objective_per_cell_argmax"] = {
        "front_sizes": sizes, "members": kept, "pass": ok,
        "note": ("the protocol's 'no global-argmax guarantee' therefore does NOT hold "
                 "under the default single-objective contract; it needs >=2 objectives"),
    }
    emit()

    # 2e crowding truncation needs >=2 objectives
    arc5 = lor.ParetoGridArchive(dims=(32,), ranges=((0.0, 1.0),),
                                 objective_count=2, max_front_size=4, epsilon=1e-9)
    for i in range(8):
        arc5.add(
            lor.ParetoCandidate(
                commit_hash=f"m{i}",
                objective_values=(float(i), float(8 - i)),
                objective_scores=(float(i), float(8 - i)),
                measures=(0.5,),
                timestamp=0.0,
            )
        )
    sizes5 = {cell: len(arc5.front(cell)) for cell in sorted(arc5._fronts)}
    trunc = sizes5 and max(sizes5.values()) <= 4
    emit("2e. crowding truncation only bites with >1 objective: 8 mutually "
         "non-dominated candidates, max_front_size=4 -> sizes={}".format(sizes5))
    emit(f"  ASSERTION truncation to max_front_size: {'PASS' if trunc else 'FAIL'}")
    if not trunc:
        failures.append("Loreley crowding-truncation assertion failed")
    out["loreley"]["crowding_truncation"] = {"front_sizes": sizes5, "pass": bool(trunc)}
    emit()

    # 2f sampling is score independent and reproducible from the sampler seed
    arc6 = lor.ParetoGridArchive(dims=(32, 32), ranges=((0.0, 1.0), (0.0, 1.0)),
                                 objective_count=1, max_front_size=8, epsilon=1e-9)
    arc6.add(mk("a", 1.0, (0.10, 0.10)))
    arc6.add(mk("b", 99.0, (0.60, 0.60)))
    picks = {}
    rng = random.Random(7331)
    for _ in range(trials):
        c = arc6.sample(1, rng=rng)[0].commit_hash
        picks[c] = picks.get(c, 0) + 1
    p_a = picks.get("a", 0) / trials
    p_b = picks.get("b", 0) / trials
    ok = abs(p_a - 0.5) < TOL and abs(p_b - 0.5) < TOL
    emit("2f. archive sampling is score independent (pareto_archive.py:265-278: uniform "
         "over occupied cells, uniform within a front)")
    emit(f"  two occupied cells with scores 1.0 and 99.0 -> P(pick 'a')={p_a:.6f} "
         f"P(pick 'b')={p_b:.6f}")
    emit(f"  ASSERTION uniform / score independent: {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("Loreley score-independent sampling assertion failed")
    out["loreley"]["sampling_score_independent"] = {"p_a": p_a, "p_b": p_b, "pass": ok}
    emit()

    # ---------------------------------------------------------- KAPSO / SL
    emit("-" * 100)
    emit("3. KAPSO: deterministic selection (transcribed keys, source cited in code)")
    emit("-" * 100)
    c1 = {"id": "c1", "score": 2.0, "had_error": False, "evaluation_valid": True,
          "build_fidelity": "full",
          "attempts": [{"evaluator_id": "EID*", "fidelity": "full", "fraction": 1.0,
                        "seed": 1337, "score": 2.0}]}
    c2 = {"id": "c2", "score": 1.0, "had_error": False, "evaluation_valid": True,
          "build_fidelity": "full",
          "attempts": [{"evaluator_id": "EID*", "fidelity": "full", "fraction": 1.0,
                        "seed": 1337, "score": 1.0}]}
    best = kapso_best_experiment([c2, c1])
    deliv = kapso_select_committed([c2, c1], "EID*")
    emit(f"  get_best_experiment([c2, c1])      -> {best['id']}   (expect c1)")
    emit(f"  select_committed_candidate(...)    -> {deliv['id']}   (expect c1)")
    ok = best["id"] == "c1" and deliv["id"] == "c1"
    emit(f"  ASSERTION deterministic argmax: {'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("KAPSO deterministic argmax assertion failed")
    out["kapso"]["deterministic_argmax"] = {"parent": best["id"], "deliverable": deliv["id"], "pass": ok}

    # trap: higher tier beats higher score
    probe_high = {"id": "probe", "score": 9.0, "had_error": False, "evaluation_valid": True,
                  "build_fidelity": "fast",
                  "attempts": [{"evaluator_id": "EID*", "fidelity": "fast", "fraction": 0.15,
                                "seed": 1337, "score": 9.0}]}
    full_low = dict(c2)
    deliv2 = kapso_select_committed([probe_high, full_low], "EID*")
    emit("  TRAP: a FAST-only candidate with score 9.0 vs a FULL candidate with score 1.0")
    emit(f"    select_committed_candidate -> {deliv2['id']}   (expect c2: TIER_PROBE is "
         f"ineligible, fidelity.py:202)")
    ok2 = deliv2["id"] == "c2"
    emit(f"    ASSERTION tier outranks score: {'PASS' if ok2 else 'FAIL'}")
    if not ok2:
        failures.append("KAPSO tier-over-score assertion failed")
    out["kapso"]["tier_outranks_score"] = {"selected": deliv2["id"], "pass": ok2}

    # trap: invalid/errored node must never be best even with a higher score
    bad = {"id": "bad", "score": 99.0, "had_error": True, "evaluation_valid": True,
           "build_fidelity": "full", "attempts": []}
    invalid = {"id": "invalid", "score": 99.0, "had_error": False, "evaluation_valid": False,
               "build_fidelity": "full", "attempts": []}
    unbounded = {"id": "none", "score": None, "had_error": False, "evaluation_valid": True,
                 "build_fidelity": "full", "attempts": []}
    best3 = kapso_best_experiment([bad, invalid, unbounded, c2])
    emit("  TRAP: errored / evaluation_invalid / score=None nodes with a nominal 99.0 or None")
    emit(f"    get_best_experiment -> {best3['id']}   (expect c2)")
    ok3 = best3["id"] == "c2"
    emit(f"    ASSERTION failure nodes cannot win: {'PASS' if ok3 else 'FAIL'}")
    if not ok3:
        failures.append("KAPSO failure-node exclusion assertion failed")
    out["kapso"]["failure_nodes_excluded"] = {"selected": best3["id"], "pass": ok3}

    # manifest class gate
    granted = {"eval_fidelity": "full", "eval_fraction": 1.0, "seed": 1337}
    cases = [
        ({"fidelity": "full", "fraction": 1.0, "seed": 1337}, True, "exact match"),
        ({"fidelity": "full", "fraction": 1.0, "seed": 7}, False, "wrong seed"),
        ({"fidelity": "full", "fraction": 0.15, "seed": 1337}, False, "wrong fraction"),
        ({"fidelity": "fast", "fraction": 1.0, "seed": 1337}, False, "wrong fidelity"),
        ({"fidelity": "full", "fraction": 1.0 + 1e-10, "seed": 1337}, True, "within 1e-9"),
    ]
    mismatches = []
    emit("  manifest granted-class gate (registered_evaluation.py:87-91):")
    for manifest, expected, label in cases:
        got = kapso_manifest_class_ok(manifest, granted)
        emit(f"    {label:<16s} manifest={manifest} -> accepted={got} (expect {expected})")
        if got != expected:
            mismatches.append(label)
    ok4 = not mismatches
    emit(f"    ASSERTION granted-class gate: {'PASS' if ok4 else 'FAIL'}")
    if not ok4:
        failures.append(f"KAPSO granted-class gate mismatch on: {mismatches}")
    out["kapso"]["granted_class_gate"] = {"mismatched_cases": mismatches, "pass": ok4}
    emit()

    emit("4. SimpleLoop (protocol sec 4.4, line ~608): c*_t = argmax_{i<=t} E(c_i)")
    sl_nodes = [{"id": "c1", "score": 2.0}, {"id": "c2", "score": 1.0}]
    sl_best = max(sl_nodes, key=lambda n: n["score"])["id"]
    sl_best_rev = max(list(reversed(sl_nodes)), key=lambda n: n["score"])["id"]
    ok5 = sl_best == "c1" and sl_best_rev == "c1"
    emit(f"  argmax over [c1, c2]      -> {sl_best}")
    emit(f"  argmax over [c2, c1]      -> {sl_best_rev}   (order counterbalance)")
    emit(f"  ASSERTION order-invariant argmax: {'PASS' if ok5 else 'FAIL'}")
    if not ok5:
        failures.append("SimpleLoop argmax order-invariance failed")
    out["simpleloop"]["argmax_order_invariant"] = {
        "forward": sl_best, "reversed": sl_best_rev, "pass": ok5,
        "trials_needed": 1,
        "note": ("deterministic: one trial has power 1 against any alternative that "
                 "changes the selection; the meaningful control is counterbalanced "
                 "candidate order, not repetition"),
    }
    emit()

    # ------------------------------------------------------------- power
    emit("-" * 100)
    emit("5. Power analysis for the EvE frequency test")
    emit("-" * 100)
    p0 = p_claim
    alts = [
        ("uniform / no score dependence, N=2 (== solver_prefill, T->inf)", 0.5),
        ("uniform over N=4 (score-independent, 4 candidates)", 0.25),
        ("first-position p for N=4, num=4 (wrong population size)", first_draw_prob(4)),
        ("first-position p for N=3, num=4 (wrong population size)", first_draw_prob(3)),
        ("T=0.5 mis-set (p=1/(1+e^-2))", 1.0 / (1.0 + math.exp(-2.0))),
        ("T=2.0 mis-set (p=1/(1+e^-0.5))", 1.0 / (1.0 + math.exp(-0.5))),
    ]
    emit(f"H0: p = {p0:.9f}   alpha=0.05, power=0.90")
    emit("observable: the position-0 entry of the rendered solver examples block in the "
         "Phase 2 workspace README (immutable_renderers/base.py:179-196 keeps draw order)")
    emit("test statistic: Z = (p_hat - p0)/sqrt(p0(1-p0)/n); exact binomial used for n_exact")
    emit()

    def emit_power_table(title, rows):
        if title:
            emit(title)
        emit(f"{'alternative':<58s} {'p_alt':>10s} {'n(2s)':>7s} {'n(1s)':>7s} {'n_exact':>8s}")
        for label, p0i, p1i in rows:
            if p1i == p0i:
                emit(f"{label:<58s} {p1i:>10.6f} {'-':>7s} {'-':>7s} "
                     f"{'none':>8s}   (degenerate: no test can separate)")
                out["power"][label] = {
                    "h0": p0i, "p_alt": p1i, "n_normal_two_sided": None,
                    "n_normal_one_sided": None, "n_exact_binomial_two_sided": None,
                    "alpha": 0.05, "power": 0.90,
                    "degenerate": True,
                }
                continue
            r2 = power_row(label, p0i, p1i, sides=2)
            r1 = power_row(label, p0i, p1i, sides=1)
            ne = r2["n_exact_binomial"]
            emit(f"{label:<58s} {p1i:>10.6f} {r2['n_normal_approx']:>7d} "
                 f"{r1['n_normal_approx']:>7d} {str(ne):>8s}")
            out["power"][label] = {
                "h0": p0i,
                "p_alt": p1i,
                "n_normal_two_sided": r2["n_normal_approx"],
                "n_normal_one_sided": r1["n_normal_approx"],
                "n_exact_binomial_two_sided": ne,
                "alpha": 0.05,
                "power": 0.90,
            }
        emit()

    emit_power_table(
        "5a. order statistic (position 0 of the rendered block), H0 = 0.7310586",
        [(label, p0, p1) for label, p1 in alts],
    )

    emit("5b. runtime-level inclusion statistic, H0 = exact Plackett-Luce inclusion of the "
         "top candidate, H1 = score-independent (uniform m/N)")
    emit("    (this is the statistic an auditor who cannot read the README order would use; "
         "for N=4 it is fully degenerate)")
    inc_rows = []
    for n in (4, 5, 6, 8, 10):
        w = rank_weights(n)
        p0i = inclusion_prob(w, 0, 4)
        p1i = 4.0 / n
        label = f"N={n}, num=4: inclusion_top vs uniform"
        inc_rows.append((label, p0i, p1i))
    emit_power_table("", inc_rows)

    emit("5c. can the frequency test tell the two sampler *classes* apart?")
    emit(f"    RankSoftmaxSampler(k=2,T=1,num=1) p = {first_draw_prob(2):.9f}")
    emit(f"    RankExponentialSumSampler(score w=1,T=1,num=1) p = "
         f"{first_draw_prob(2):.9f}  (identical: single scalar feature, same weight/T, "
         f"rank_softmax.py:50-51, :104, :181)")
    emit("    => under the frozen unit-test conditions the two classes induce the SAME "
         "distribution; only N or num distinguishes them, which is why the N=3/N=4 rows "
         "above are the class-distinguishing alternatives.")
    out["power"]["class_distinguishability"] = {
        "rank_softmax_p": first_draw_prob(2),
        "rank_exp_sum_p": first_draw_prob(2),
        "identical": True,
        "note": "same distribution at N=2, num=1, single scalar feature, T=1",
    }
    emit()
    emit("deterministic runtimes (KAPSO, SimpleLoop): n=1 trial has power 1 against a "
         "score-ordering flip; repetitions buy nothing. The controls that matter are "
         "(a) counterbalanced candidate order, (b) a same-score pair to pin the tie-break, "
         "(c) an error/invalid node with the highest nominal score.")
    out["power"]["deterministic_runtimes"] = {
        "trials_needed": 1,
        "rationale": ("deterministic selection: any single observation rejects a "
                      "different-selection alternative with power 1"),
        "required_controls": [
            "counterbalanced candidate order",
            "tie-score pair to freeze the tie-break rule",
            "highest-nominal-score node marked had_error/evaluation_invalid",
        ],
    }
    emit()

    # --------------------------------------------------------- tail check
    emit("-" * 100)
    emit("6. Monte-Carlo resolution check")
    emit("-" * 100)
    worst = sorted(((k, v["abs_diff"], v.get("simulated", 0.0))
                    for k, v in out["eve"].items()
                    if isinstance(v, dict) and "abs_diff" in v),
                   key=lambda t: -t[1])[:5]
    for k, d, p in worst:
        hw = wilson_halfwidth(p if p else 0.5, trials, 3.0)
        emit(f"  {k:<46s} |diff|={d:.6f}  3-sigma MC half-width~{hw:.6f}  "
             f"{'within' if d <= hw else 'OUTSIDE'}")
    emit()

    out["mc_resolution"] = {
        "worst_cases": [{"case": k, "abs_diff": d} for k, d, _ in worst],
        "note": "all differences must sit inside the 3-sigma MC half-width",
    }

    if failures:
        emit("=" * 100)
        emit("DISAGREEMENT: closed form and simulation do not agree")
        for f in failures:
            emit(f"  - {f}")
        emit("=" * 100)
        if args.emit_json:
            (HERE / "expected_values.json").write_text(json.dumps(out, indent=2) + "\n")
        return 2

    emit("=" * 100)
    emit("ALL CHECKS AGREE: every closed form matched its simulation within tolerance.")
    emit("=" * 100)

    if args.emit_json:
        target = HERE / "expected_values.json"
        target.write_text(json.dumps(out, indent=2) + "\n")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
