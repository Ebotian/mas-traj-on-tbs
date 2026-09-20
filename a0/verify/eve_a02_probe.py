#!/usr/bin/env python3
"""Adversarial re-run of EvE's A0.2 frequency claim.

1. closed-form: the frozen sampler's class, config and population size imply
   P(position 0 == higher scorer) = 1 / (1 + exp(-1)) at N=2 and num=min(4,2).
2. fresh draws through the real call site (`Phase2BatchRunner._sample_solvers`)
   with the population's own unseeded RNG -- a different random draw from the
   one the adapter recorded, so a hard-coded answer cannot survive.
3. the score-swap control: same machinery, swapped scores, frequency must move.
4. one draw per iteration: instrument the sampler to count calls per iteration.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from math import lgamma, exp, log
from pathlib import Path

A0 = Path("/home/ebt/rsi-dev/a0")
sys.path.insert(0, str(A0 / "runtimes/eve"))
sys.path.insert(0, "/tmp/eve/src")
os.environ.setdefault("A0_EVE_ROOT", "/tmp/eve")

from a0_adapter import a02, common  # noqa: E402
from a0_adapter.eve_runtime import build_context  # noqa: E402

RUN_DIR = A0 / "verify/out/eve-a02"
TOP, SECOND = "c01_good_hex", "c02_baseline_upstream"
S_TOP, S_LOW = 2.4519205208433132, 0.25
DRAWS = int(os.environ.get("VERIFY_DRAWS", "3000"))


def two_sided_exact(k, n, p0):
    lg = lambda i: (lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1)
                    + i * log(p0) + (n - i) * log(1 - p0))
    mx = max(lg(i) for i in range(n + 1))
    w = lambda i: exp(lg(i) - mx)
    thr = w(k) * (1 + 1e-12)
    return sum(w(i) for i in range(n + 1) if w(i) <= thr) / sum(w(i) for i in range(n + 1))


def main():
    theta = common.parse_theta("seed=none,fidelity=full,fraction=1.0")
    fr = common.load_fr(common.DEFAULT_FR)
    eid_star = common.read_eid(common.DEFAULT_EID)["eid_star"]
    candidates = {c.candidate_id: c for c in common.load_candidates(common.DEFAULT_CANDIDATE_SET)}
    ctx = build_context(run_dir=RUN_DIR.resolve(), theta=theta, fr=fr, eid_star=eid_star,
                        pins_sha256=fr.spec_hash)
    sources = {cid: (c.path / "solution.py").read_text() for cid, c in candidates.items()}

    out = {"draws_per_case": DRAWS, "cases": {}}

    for label, scores in (("E1_frozen_scores", {TOP: S_TOP, SECOND: S_LOW}),
                          ("control_injected_swap", {TOP: S_LOW, SECOND: S_TOP})):
        pop = a02.build_population(ctx, RUN_DIR, scores, sources)
        sampler = a02.instantiate_sampler(ctx, "solver_examples")

        calls = {"n": 0}
        orig = sampler.sample
        def counting_sample(items, sc, num, *, rng):
            calls["n"] += 1
            return orig(items, sc, num, rng=rng)
        sampler.sample = counting_sample

        runner = a02.make_runner(ctx, pop, sampler)
        success = 0
        successes_readme = 0
        for _ in range(DRAWS):
            solvers = a02.sample_solvers(runner)
            if solvers and solvers[0].id == TOP:
                success += 1
            order, _pf = a02.read_order_from_readme(ctx, solvers, None)
            if order and order[0] == TOP:
                successes_readme += 1
        p0 = 1.0 / (1.0 + math.exp(-1.0)) if label == "E1_frozen_scores" else math.exp(-1.0) / (1.0 + math.exp(-1.0))
        out["cases"][label] = {
            "scores": scores,
            "draws": DRAWS,
            "p_hat_sampler_order": success / DRAWS,
            "p_hat_readme_order": successes_readme / DRAWS,
            "closed_form_p": p0,
            "sampler_sample_calls": calls["n"],
            "one_call_per_draw": calls["n"] == DRAWS,
            "sampler_class": type(sampler).__name__,
            "config": json.loads(json.dumps(dict(ctx.cfg.loop.sampling["solver_examples"]), default=str)),
            "exact_two_sided_p_vs_closed_form": two_sided_exact(success, DRAWS, p0),
        }
        print(f"{label}: p_hat={success / DRAWS:.4f} readme={successes_readme / DRAWS:.4f} "
              f"closed_form={p0:.7f} calls={calls['n']} class={type(sampler).__name__}")

    e1 = out["cases"]["E1_frozen_scores"]["p_hat_sampler_order"]
    ctrl = out["cases"]["control_injected_swap"]["p_hat_sampler_order"]
    p1, p2 = e1, ctrl
    n1 = n2 = DRAWS
    pbar = (p1 * n1 + p2 * n2) / (n1 + n2)
    z = (p1 - p2) / math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
    out["score_dependence_z"] = z
    out["score_dependence_two_sided_p"] = math.erfc(abs(z) / math.sqrt(2))
    out["verdict"] = {
        "E1_within_ci_of_closed_form": abs(e1 - 1 / (1 + math.exp(-1))) < 4 * math.sqrt(1 / (1 + math.exp(-1)) * (1 - 1 / (1 + math.exp(-1))) / DRAWS),
        "control_moved": abs(e1 - ctrl) > 0.3,
        "one_call_per_draw": all(v["one_call_per_draw"] for v in out["cases"].values()),
    }
    (A0 / "verify/out/eve_a02_replication.json").write_text(json.dumps(out, indent=2))
    print("\nz =", z, " two-sided p =", out["score_dependence_two_sided_p"])
    print(json.dumps(out["verdict"]))


if __name__ == "__main__":
    main()
