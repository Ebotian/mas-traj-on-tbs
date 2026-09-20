"""Driver for the EvE A0.2 frequency test.

Runs the real sampling machinery (see ``a02.py`` for the seams) many times over frozen
populations of real `C*` members, reads the draw order out of the rendered Phase-2 README,
and tests the frequency against the pre-registered expectation per sampler class.

The run also carries the study's required demonstration that an *externally supplied score*
drives the selection: one case swaps the two supplied scores while every other input is
held fixed, so the position-0 frequency of the *same* candidate moves from ~0.731 to ~0.269.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from scipy import stats as scipy_stats

from . import a02
from .a02 import (
    CaseResult,
    A02Report,
    FIRST_POSITION_TOP,
    CONDITIONAL_SECOND_TOP_GIVEN_RANK1_FIRST,
    exact_required_n,
    exact_two_sided_p,
    normal_required_n,
    norm_ci,
)
from .eve_runtime import EveContext
from .traces import TraceWriter

EnvelopeFactory = Callable[[int, str], dict[str, Any]]


def _case_required_n(p0: float, alternatives: dict[str, float]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, p_alt in alternatives.items():
        out[label] = {
            "p_alt": p_alt,
            "n_normal_two_sided": normal_required_n(p0, p_alt),
            "n_normal_one_sided": normal_required_n(p0, p_alt, one_sided=True),
            "n_exact_two_sided": exact_required_n(p0, p_alt),
            "recomputed_here": "normal approx + exact binomial search on the same rule as scipy.binomtest",
        }
    return out


def _emit_score_event(
    traces: TraceWriter,
    *,
    iteration: int,
    candidate_id: str,
    envelope: dict[str, Any],
    fields: dict[str, Any],
    fr_payload: dict[str, Any],
    search_signal: Any,
    evidence: dict[str, Any],
) -> str:
    return traces.score(
        iteration=iteration,
        candidate_id=candidate_id,
        envelope=envelope,
        fields=fields,
        fr_payload=fr_payload,
        search_signal=search_signal,
        evidence=evidence,
    )


def run_a02(
    ctx: EveContext,
    *,
    run_dir: Path,
    traces: TraceWriter,
    envelope: EnvelopeFactory,
    fr_payload: dict[str, Any],
    candidate_sources: dict[str, str],
    reference_fields: dict[str, dict[str, Any]],
    reference_scores: dict[str, float],
    n_main: int,
    n_secondary: int,
    on_progress: Callable[[str], None] | None = None,
) -> A02Report:
    say = on_progress or (lambda _msg: None)
    report = A02Report()
    report.seams = [
        {
            "seam": "S1",
            "what": "hydra.utils.instantiate(loop.sampling[...])",
            "where": "src/scaling_evolve/algorithms/eve/factory.py:291-299",
        },
        {
            "seam": "S2",
            "what": "Phase2BatchRunner._sample_solvers (real call site, rng=self.solver_pop._rng)",
            "where": "src/scaling_evolve/algorithms/eve/workflow/phase2.py:597-605",
        },
        {
            "seam": "S3",
            "what": "render_immutable_files -> README {solver_examples_block} order",
            "where": "src/scaling_evolve/algorithms/eve/workspace/immutable_renderers/base.py:179-196",
        },
        {
            "seam": "S4",
            "what": "solver_prefill UniformSampler called with the call site's arguments",
            "where": "src/scaling_evolve/algorithms/eve/workflow/phase2.py:608-618",
        },
    ]
    report.frozen_config = {
        "n_workers_phase2": int(ctx.cfg.loop.n_workers_phase2),
        "n_solver_examples_phase2": int(ctx.cfg.loop.n_solver_examples_phase2),
        "solver_examples._target_": str(ctx.cfg.loop.sampling.solver_examples._target_),
        "solver_examples.replacement_mode": str(ctx.cfg.loop.sampling.solver_examples.replacement_mode),
        "solver_examples.features.score.weight": float(
            ctx.cfg.loop.sampling.solver_examples.features.score.weight
        ),
        "solver_examples.features.score.temperature": float(
            ctx.cfg.loop.sampling.solver_examples.features.score.temperature
        ),
        "solver_prefill._target_": str(ctx.cfg.loop.sampling.solver_prefill._target_),
        "working_optimizer._target_": str(ctx.cfg.loop.sampling.working_optimizer._target_),
        "rng_seed": None,
        "rng_seed_note": "populations/base.py:40 -> random.Random() with no seed; no seed key exists in the config tree",
    }
    report.power_table_reproduced = {
        "uniform_N2_vs_0.5": {
            "p0": a02.P0,
            "p_alt": 0.5,
            "n_normal_two_sided": normal_required_n(a02.P0, 0.5),
            "n_normal_one_sided": normal_required_n(a02.P0, 0.5, one_sided=True),
            "n_exact_two_sided": exact_required_n(a02.P0, 0.5),
        },
        "N4_wrong_population_vs_0.6439142598879724": {
            "p0": a02.P0,
            "p_alt": FIRST_POSITION_TOP[4],
            "n_normal_two_sided": normal_required_n(a02.P0, FIRST_POSITION_TOP[4]),
            "n_normal_one_sided": normal_required_n(a02.P0, FIRST_POSITION_TOP[4], one_sided=True),
            "n_exact_two_sided": exact_required_n(a02.P0, FIRST_POSITION_TOP[4]),
        },
        "N3_wrong_population_vs_0.6652409557748218_binding": {
            "p0": a02.P0,
            "p_alt": FIRST_POSITION_TOP[3],
            "n_normal_two_sided": normal_required_n(a02.P0, FIRST_POSITION_TOP[3]),
            "n_normal_one_sided": normal_required_n(a02.P0, FIRST_POSITION_TOP[3], one_sided=True),
            "n_exact_two_sided": exact_required_n(a02.P0, FIRST_POSITION_TOP[3]),
        },
        "_preregistered_from_acceptance": {
            "source": "a0/acceptance/expected_values.json -> power",
            "uniform_N2_vs_0.5": {"n_normal_two_sided": 43, "n_normal_one_sided": 36,
                                  "n_exact_binomial_two_sided": 46},
            "N4_wrong_population_vs_0.6439142598879724": {"n_normal_two_sided": 290,
                                                          "n_normal_one_sided": 238,
                                                          "n_exact_binomial_two_sided": 295},
            "N3_wrong_population_vs_0.6652409557748218_binding": {"n_normal_two_sided": 502,
                                                                  "n_normal_one_sided": 411,
                                                                  "n_exact_binomial_two_sided": 515},
            "note": (
                "the normal-approximation counts reproduce exactly; the *exact* counts differ "
                "slightly (44 vs 46, 289 vs 295, 496 vs 515 here) because the critical region "
                "used here is the strict probability-ordering rule, verified to agree with "
                "scipy.stats.binomtest to 3.4e-14. The study pre-registered 515, so this run "
                "uses n_main >= 2000 > 515 and satisfies the binding requirement under either "
                "rule."
            ),
        },
        "_p_value_selftest": a02.selftest_pval_against_scipy(
            [(11, 20, a02.P0), (61, 120, 0.5), (496, 700, a02.P0), (466, 700, a02.P0)]
        ),
    }

    case_defs: list[dict[str, Any]] = [
        {
            "name": "A02-E1/E5_solver_examples_order_N2",
            "sampler_key": "solver_examples",
            "population": [TOP, SECOND],
            "scores": {TOP: reference_scores[TOP], SECOND: reference_scores[SECOND]},
            "marked": TOP,
            "p0": FIRST_POSITION_TOP[2],
            "p_alt_tested": 0.5,
            "n": n_main,
            "statistic": "position-0 of the rendered {solver_examples_block} == the higher-scoring member",
            "check_point": "A0.2 EvE: RankExponentialSumSampler, N=2, num=min(4,2)=2, no_replacement",
            "alternatives": {"uniform_no_score_dependence_N2": 0.5},
        },
        {
            "name": "A02-control_solver_examples_order_N2_injected_swap",
            "sampler_key": "solver_examples",
            "population": [TOP, SECOND],
            "scores": {TOP: reference_scores[SECOND], SECOND: reference_scores[TOP]},
            "marked": TOP,
            "p0": 1.0 - FIRST_POSITION_TOP[2],
            "p_alt_tested": 0.5,
            "n": n_main,
            "statistic": "position-0 of the rendered {solver_examples_block} == c01_good_hex (score-injected control)",
            "check_point": "A0.2 EvE: externally supplied score decides the order (score -> selection dependence)",
            "alternatives": {"uniform_no_score_dependence_N2": 0.5},
            "injected": True,
        },
        {
            "name": "A02-E6_solver_prefill_uniform_control_N2",
            "sampler_key": "solver_prefill",
            "population": [TOP, SECOND],
            "scores": {TOP: reference_scores[TOP], SECOND: reference_scores[SECOND]},
            "marked": TOP,
            "p0": 0.5,
            "p_alt_tested": FIRST_POSITION_TOP[2],
            "n": max(120, min(n_secondary, 200)),
            "statistic": "the entry marked '<- prefill' in the rendered block == c01_good_hex",
            "check_point": "A0.2 EvE control: solver_prefill is a score-independent UniformSampler",
            "alternatives": {"rank_softmax_0.731": FIRST_POSITION_TOP[2]},
        },
        {
            "name": "A02-E7_solver_examples_order_N4",
            "sampler_key": "solver_examples",
            "population": [TOP, NEAR_TIE, SECOND, NEAR_ZERO],
            "scores": {
                TOP: reference_scores[TOP],
                NEAR_TIE: reference_scores[NEAR_TIE],
                SECOND: reference_scores[SECOND],
                NEAR_ZERO: reference_scores[NEAR_ZERO],
            },
            "marked": TOP,
            "p0": FIRST_POSITION_TOP[4],
            "p_alt_tested": a02.P0,
            "n": n_main,
            "statistic": "position-0 of the rendered block == c01_good_hex, population size N=4",
            "check_point": "A0.2 EvE: population size N=4 -> 1/(1+e^-1+e^-2+e^-3), not 0.731",
            "alternatives": {"p0_731_wrong_population": a02.P0},
        },
        {
            "name": "A02-E8_solver_examples_second_draw_not_reranked_N4",
            "sampler_key": "solver_examples",
            "population": [TOP, NEAR_TIE, SECOND, NEAR_ZERO],
            "scores": {
                TOP: reference_scores[TOP],
                NEAR_TIE: reference_scores[NEAR_TIE],
                SECOND: reference_scores[SECOND],
                NEAR_ZERO: reference_scores[NEAR_ZERO],
            },
            "marked": TOP,
            "p0": CONDITIONAL_SECOND_TOP_GIVEN_RANK1_FIRST[4],
            "p_alt_tested": CONDITIONAL_SECOND_TOP_GIVEN_RANK1_FIRST[3],
            "n": n_secondary,
            "conditional_on_position0": NEAR_TIE,
            "statistic": "P(position 1 == rank-0 | position 0 == rank-1); a re-ranking sampler returns 0.8807971",
            "check_point": "A0.2 EvE: no-replacement path never recomputes weights (base.py:41-64)",
            "alternatives": {"reranking_0.8807971": CONDITIONAL_SECOND_TOP_GIVEN_RANK1_FIRST[3]},
        },
    ]

    iteration_base = 1000
    for case_index, case in enumerate(case_defs):
        name = case["name"]
        say(f"[a02] {name}")
        pop = a02.build_population(
            ctx,
            run_dir,
            case["scores"],
            {cid: candidate_sources[cid] for cid in case["population"]},
        )
        population_ids = [entry.id for entry in pop.entries()]
        sampler = a02.instantiate_sampler(ctx, case["sampler_key"])
        runner = a02.make_runner(ctx, pop, sampler)

        # score events for this case's population (the decisions below must cite them)
        case_iter_base = iteration_base + case_index * 20000
        score_event_ids: dict[str, str] = {}
        injected = bool(case.get("injected"))
        for cid in population_ids:
            iteration = case_iter_base - 1
            if injected:
                fields = {"sum_radii": float(case["scores"][cid])}
                evidence = {
                    "status": "not_run",
                    "detail": (
                        "A0.2 injected-score control: the value was supplied by the adapter to "
                        "test score -> selection dependence and is NOT an E* measurement "
                        "(a0/contract/trace_schema.md §5 'not_run')"
                    ),
                    "cached_from_run_id": None,
                    "metrics_dropped": None,
                }
            else:
                fields = dict(reference_fields[cid])
                evidence = {
                    "status": "ok",
                    "detail": None,
                    "cached_from_run_id": None,
                    "metrics_dropped": None,
                }
            score_event_ids[cid] = _emit_score_event(
                traces,
                iteration=max(iteration, 0),
                candidate_id=cid,
                envelope=envelope(max(iteration, 0), cid),
                fields=fields,
                fr_payload=fr_payload,
                search_signal=float(case["scores"][cid]),
                evidence=evidence,
            )

        policy = (
            f"{type(sampler).__name__}(replacement_mode={getattr(sampler, 'replacement_mode', None)!r}, "
            f"temperature=1.0, num={int(ctx.cfg.loop.n_solver_examples_phase2)}, N={len(population_ids)})"
        )
        successes = 0
        qualifying = 0
        successes_conditional = 0
        self_check: dict[str, Any] | None = None
        ordered_ids_by_iteration: list[list[str]] = []

        iterations = int(case["n"])
        started_case = time.monotonic()
        for i in range(iterations):
            iteration = case_iter_base + i
            t0 = time.monotonic()
            if case["sampler_key"] == "solver_prefill":
                solvers = a02.sample_solvers(
                    a02.make_runner(ctx, pop, a02.instantiate_sampler(ctx, "solver_examples"))
                )
                prefill = a02.sample_prefill(ctx, solvers)
                order, prefill_marked = a02.read_order_from_readme(ctx, solvers, prefill)
                chosen = prefill_marked
            else:
                solvers = a02.sample_solvers(runner)
                order, prefill_marked = a02.read_order_from_readme(ctx, solvers, None)
                chosen = order[0]
            elapsed = time.monotonic() - t0
            ordered_ids = list(order)

            if self_check is None:
                self_check = {
                    "readme_order": order,
                    "sampler_returned_order": (
                        [entry.id for entry in solvers] if case["sampler_key"] != "solver_prefill" else None
                    ),
                    "order_matches_sampler_return": (
                        order == [entry.id for entry in solvers]
                        if case["sampler_key"] != "solver_prefill"
                        else None
                    ),
                    "prefill_marker": prefill_marked,
                    "block_has_all_members": set(order) == set(entry.id for entry in solvers),
                }
                if case["sampler_key"] == "solver_prefill" and prefill_marked is None:
                    raise RuntimeError(
                        "the prefill marker '<- prefill' is missing from the rendered block; "
                        "the prefill observable would be vacuous"
                    )
            ordered_ids_by_iteration.append(ordered_ids)

            if "conditional_on_position0" in case:
                if chosen == case["conditional_on_position0"]:
                    qualifying += 1
                    if len(order) > 1 and order[1] == case["marked"]:
                        successes_conditional += 1
            else:
                if chosen == case["marked"]:
                    successes += 1

            # one selection event per decision, one resource event per iteration
            traces.selection(
                iteration=iteration,
                candidate_id=chosen or case["marked"],
                envelope=envelope(iteration, chosen or case["marked"]),
                selection={
                    "policy": policy,
                    "chosen_candidate_id": chosen,
                    "considered": [
                        {
                            "candidate_id": cid,
                            "search_signal": float(case["scores"][cid]),
                        }
                        for cid in ordered_ids
                    ],
                    "reason": (
                        "the sampler's draw order is rendered into the Phase-2 README "
                        "{solver_examples_block}; position 0 is the first draw"
                        + (
                            "; the prefill case reads the '<- prefill' marker instead"
                            if case["sampler_key"] == "solver_prefill"
                            else ""
                        )
                    ),
                    "tie_break": None,
                    "source_score_event_id": score_event_ids.get(chosen or case["marked"]),
                    "check_point": case["check_point"],
                },
            )
            traces.resource(
                iteration=iteration,
                candidate_id=chosen or case["marked"],
                envelope=envelope(iteration, chosen or case["marked"]),
                t_wall_s=elapsed,
                n_evaluator_calls=0,
                concurrency_cap=1,
                observed_max=1,
                budget_hard=None,
            )

        if "conditional_on_position0" in case:
            n_obs = qualifying
            succ = successes_conditional
            statistic = case["statistic"]
        else:
            n_obs = iterations
            succ = successes
            statistic = case["statistic"]
        p_hat = succ / n_obs if n_obs else float("nan")
        p0 = float(case["p0"])
        p_value = exact_two_sided_p(succ, n_obs, p0) if n_obs else 1.0
        result = CaseResult(
            name=name,
            check_point=case["check_point"],
            policy=policy,
            observable="rendered README {solver_examples_block} order (immutable_renderers/base.py:179-196)",
            population=population_ids,
            scores={cid: float(score) for cid, score in case["scores"].items()},
            num=min(int(ctx.cfg.loop.n_solver_examples_phase2), len(population_ids)),
            n_iterations=iterations,
            statistic=statistic,
            successes=succ,
            p_hat=p_hat,
            p0=p0,
            p_alt_tested=case.get("p_alt_tested"),
            alternative=(
                "the frozen sampler's predicted frequency for the marked candidate"
            ),
            p_value=p_value,
            reject_h0=bool(p_value <= 0.05),
            ci95=norm_ci(p_hat, n_obs) if n_obs else [float("nan"), float("nan")],
            required_n=_case_required_n(p0, case.get("alternatives", {})),
            extra={
                "case_elapsed_s": round(time.monotonic() - started_case, 3),
                "observable_self_check": self_check,
                "n_effective": n_obs,
                "qualifying_iterations": qualifying if "conditional_on_position0" in case else None,
                "marker": case["marked"],
                "score_dependence_control": bool(case.get("injected")),
                # The scientific statement is two-sided: the frozen class's expectation must
                # NOT be rejected, and the competing expectation must be.
                "alternative_tests": {
                    label: {
                        "p_alt": p_alt,
                        "p_value": exact_two_sided_p(succ, n_obs, p_alt) if n_obs else 1.0,
                        "rejected_at_alpha_0.05": bool(
                            n_obs and exact_two_sided_p(succ, n_obs, p_alt) <= 0.05
                        ),
                    }
                    for label, p_alt in case.get("alternatives", {}).items()
                },
            },
        )
        report.cases.append(result)
        report.iterations_total += iterations
        if report.observable_self_check.get("order_matches_sampler_return") is None:
            report.observable_self_check = dict(self_check or {})

    # The externally-supplied-score contrast, stated as a first-class number.
    by_name = {case.name: case for case in report.cases}
    main = by_name.get("A02-E1/E5_solver_examples_order_N2")
    swap = by_name.get("A02-control_solver_examples_order_N2_injected_swap")
    if main is not None and swap is not None:
        n1, n2 = main.n_iterations, swap.n_iterations
        x1, x2 = main.successes, swap.successes
        p1, p2 = x1 / n1, x2 / n2
        p_pool = (x1 + x2) / (n1 + n2)
        se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
        z = (p1 - p2) / se if se > 0 else float("inf")
        report.observable_self_check["score_dependence_contrast"] = {
            "same_candidate": main.extra.get("marker"),
            "position0_frequency_with_reference_scores": p1,
            "position0_frequency_with_swapped_scores": p2,
            "difference": p1 - p2,
            "two_proportion_z": z,
            "two_sided_p": float(2 * (1 - scipy_stats.norm.cdf(abs(z)))),
            "conclusion": (
                "the only input changed between the two cases is the externally supplied score "
                "payload; the position-0 frequency of the same candidate moved accordingly"
            ),
        }
    return report


TOP = "c01_good_hex"
SECOND = "c02_baseline_upstream"
NEAR_TIE = "c04_near_tie"
NEAR_ZERO = "c14_near_zero"
