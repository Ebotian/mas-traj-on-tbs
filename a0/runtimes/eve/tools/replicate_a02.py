#!/usr/bin/env python
"""Independent replication of the A0.2 N=2 order case (adapter's own quality check).

The single-run A0.2 test can land just under alpha by chance; this script repeats the *same*
case several times against the same real machinery and pools the draws, so the study can see
whether a marginal rejection is sampling noise or a systematic bias in the statistic.

    python tools/replicate_a02.py --replicates 6 --draws 3000 --out out/replication
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ADAPTER_DIR))

from a0_adapter import a02  # noqa: E402
from a0_adapter import common  # noqa: E402
from a0_adapter.eve_runtime import build_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=6)
    parser.add_argument("--draws", type=int, default=3000)
    parser.add_argument("--run-dir", default=str(ADAPTER_DIR / "out" / "replication-work"))
    parser.add_argument("--out", default=str(ADAPTER_DIR / "out" / "replication"))
    args = parser.parse_args()

    theta = common.parse_theta("seed=none,fidelity=full,fraction=1.0")
    fr = common.load_fr(common.DEFAULT_FR)
    eid_star = common.read_eid(common.DEFAULT_EID)["eid_star"]
    candidates = {c.candidate_id: c for c in common.load_candidates(common.DEFAULT_CANDIDATE_SET)}
    ctx = build_context(
        run_dir=Path(args.run_dir).resolve(),
        theta=theta,
        fr=fr,
        eid_star=eid_star,
        pins_sha256=fr.spec_hash,
    )
    sources = {cid: (c.path / "solution.py").read_text(encoding="utf-8") for cid, c in candidates.items()}

    # the E* scalars, exactly as the A0.2 run supplies them
    ref: dict[str, float] = {}
    for cid in ("c01_good_hex", "c02_baseline_upstream"):
        result = common.run_e_star(
            candidates[cid].path,
            candidate_id=cid,
            theta=theta,
            out_path=Path(args.run_dir).resolve() / "reference" / f"{cid}.json",
            state_dir=Path(args.run_dir).resolve() / "e-star-state",
        )
        ref[cid] = result.scalar

    top, second = "c01_good_hex", "c02_baseline_upstream"
    replicates = []
    pooled_success = 0
    pooled_n = 0
    for rep in range(args.replicates):
        pop = a02.build_population(
            ctx,
            Path(args.run_dir).resolve(),
            {top: ref[top], second: ref[second]},
            sources,
        )
        sampler = a02.instantiate_sampler(ctx, "solver_examples")
        runner = a02.make_runner(ctx, pop, sampler)
        success = 0
        for _ in range(args.draws):
            solvers = a02.sample_solvers(runner)
            order, _prefill = a02.read_order_from_readme(ctx, solvers, None)
            if order[0] == top:
                success += 1
        pooled_success += success
        pooled_n += args.draws
        p_hat = success / args.draws
        replicates.append(
            {
                "replicate": rep,
                "draws": args.draws,
                "successes": success,
                "p_hat": p_hat,
                "two_sided_p_vs_0.7310585786300049": a02.exact_two_sided_p(
                    success, args.draws, a02.P0
                ),
            }
        )
        print(f"rep {rep}: p_hat={p_hat:.5f} successes={success}/{args.draws}", flush=True)

    pooled_p = pooled_success / pooled_n
    doc = {
        "schema": "a0.eve.replication/v1",
        "case": "solver_examples order, N=2, num=min(4,2), no_replacement",
        "profile": {
            "draws_per_replicate": args.draws,
            "replicates": args.replicates,
            "population_scores": ref,
            "rng": "solver_pop._rng, unseeded (populations/base.py:40)",
        },
        "replicates": replicates,
        "pooled": {
            "draws": pooled_n,
            "successes": pooled_success,
            "p_hat": pooled_p,
            "expected_p": a02.P0,
            "z": (pooled_p - a02.P0) / ((a02.P0 * (1 - a02.P0) / pooled_n) ** 0.5),
            "two_sided_p": a02.exact_two_sided_p(pooled_success, pooled_n, a02.P0),
            "ci95": a02.norm_ci(pooled_p, pooled_n),
        },
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "e1_replication.json").write_text(
        json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(doc["pooled"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
