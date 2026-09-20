"""Offline generator for the frozen good-packing candidate geometry.

Objective being maximised (equal-radius max-min packing of n circles in the
unit square):

    r* = max_config min( min_i b_i , min_{i<j} d_ij / 2 )

where b_i is the distance from centre i to the nearest square side.  The
upstream task objective is sum_radii; with equal radii it is exactly n * r*, so
this generator only has to find one number.

Method: fix the circle radius at 1 and bisect on the side s of the enclosing
square.  "Feasible at s" means the overlap-projection relaxation converges to a
point set inside [1, s-1]^2 whose pairwise distances are all >= 2.  The answer is
r* = 1 / s*.  Feasible configurations are kept and rescaled into each smaller
candidate box as a warm start, so the relaxation only has to repair the tight
pairs.

The result is written as a Python literal table so the frozen candidate carries
the exact binary64 coordinates this run produced (CPython repr round-trips
binary64), which makes the frozen candidate reproducible anywhere.

This is offline provenance tooling only: it needs numpy, which the evaluator
(`e_star.py`) and every candidate in `C_STAR/` do not.  Use `.venv-tools`:

    .venv-tools/bin/python tools/make_good_packing.py --n 26 --seed 0
"""

from __future__ import annotations

import argparse
import json
import math

import numpy as np

TOL = 1e-9


def violation(pts: np.ndarray, radius: float) -> float:
    """Largest pairwise overlap: <= 0 means every pair constraint holds."""
    diff = pts[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff**2).sum(-1))
    np.fill_diagonal(dist, np.inf)
    return float((2.0 * radius - dist).max())


def _sweep(pts: np.ndarray, radius: float, lo: float, hi: float, steps: int) -> np.ndarray:
    for _ in range(steps):
        diff = pts[:, None, :] - pts[None, :, :]
        dist = np.sqrt((diff**2).sum(-1))
        np.fill_diagonal(dist, np.inf)
        overlap = np.maximum(0.0, 2.0 * radius - dist)
        np.fill_diagonal(overlap, 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            push = np.where(dist > 1e-15, (overlap * 0.5) / dist, 0.0)
        pts = pts + (push[:, :, None] * diff).sum(1)
        pts = np.clip(pts, lo, hi)
    return pts


def separate(pts: np.ndarray, radius: float, side: float, budgets: tuple[int, ...]) -> tuple[np.ndarray, float]:
    """Relax until the violation stops improving, trying each budget in turn."""
    lo, hi = radius, side - radius
    for budget in budgets:
        pts = _sweep(pts, radius, lo, hi, budget)
        if violation(pts, radius) <= TOL:
            return pts, violation(pts, radius)
    return pts, violation(pts, radius)


def feasible(n: int, rng: np.random.Generator, side: float, budgets: tuple[int, ...], radius: float = 1.0) -> np.ndarray | None:
    """Return a feasible configuration at `side`, or None."""
    for _ in range(6):
        pts = rng.uniform(radius, side - radius, size=(n, 2))
        pts, v = separate(pts, radius, side, budgets)
        if v <= TOL:
            return pts
        side *= 1.05
    return None


def _rescale(pts: np.ndarray, old_side: float, new_side: float, radius: float) -> np.ndarray:
    span_old = old_side - 2.0 * radius
    span_new = new_side - 2.0 * radius
    return radius + (pts - radius) * (span_new / span_old)


def _grid_start(n: int, side: float, radius: float, rng: np.random.Generator) -> np.ndarray:
    """A `k x k` grid (k = ceil(sqrt(n))) plus the leftover points, jittered.

    The dense basin for n = 26 is a deformed square lattice, not a hexagonal
    lattice, so this start matters: slow compression keeps the basin it starts
    in, and a random start lands in a worse one.
    """
    k = math.ceil(math.sqrt(n))
    span = side - 2.0 * radius
    pts: list[list[float]] = []
    for idx in range(k * k):
        row, col = divmod(idx, k)
        pts.append([radius + span * col / (k - 1), radius + span * row / (k - 1)])
    rng.shuffle(pts)
    pts = pts[:n]
    out = np.asarray(pts, dtype=float)
    out += rng.uniform(-0.02, 0.02, size=out.shape) * span
    return np.clip(out, radius, side - radius)


def _compress(
    pts: np.ndarray,
    radius: float,
    side: float,
    budgets: tuple[int, ...],
    shrink_budgets: tuple[int, ...],
) -> tuple[float, np.ndarray]:
    """Monotonically shrink the box, reverting whenever separation fails."""
    step = 0.05 * side
    best_side, best_pts = side, pts.copy()
    while step > 1e-7 * side:
        trial_side = best_side - step
        cand, v = separate(_rescale(best_pts, best_side, trial_side, radius), radius, trial_side, shrink_budgets)
        if v <= TOL:
            best_side, best_pts = trial_side, cand
            step = min(step * 1.25, 0.02 * trial_side)
        else:
            step *= 0.5
    return best_side, best_pts


def optimise(
    n: int,
    seed: int,
    trials: int,
    iters: int,
    budgets: tuple[int, ...],
    shrink_budgets: tuple[int, ...],
    hi_side: float,
    lo_side: float,
) -> tuple[float, np.ndarray]:
    best_side = float("inf")
    best_pts: np.ndarray | None = None
    for t in range(trials):
        rng = np.random.default_rng(seed + t)
        side = hi_side
        for _ in range(12):
            pts = _grid_start(n, side, 1.0, rng)
            pts, v = separate(pts, 1.0, side, budgets)
            if v <= TOL:
                break
            side *= 1.05
        else:
            continue
        side, pts = _compress(pts, 1.0, side, budgets, shrink_budgets)
        # Polish: bisect between the shrunk side and its lower bracket.
        lo, hi, cur = lo_side, side, side
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            cand, v = separate(_rescale(pts, cur, mid, 1.0), 1.0, mid, budgets)
            if v <= TOL:
                pts, cur, lo = cand, mid, mid
            else:
                hi = mid
            if hi - lo <= 1e-9 * hi:
                break
        if cur < best_side:
            best_side, best_pts = cur, pts
    if best_pts is None:
        raise RuntimeError("no feasible configuration found")
    return 1.0 / best_side, best_pts / best_side


def _min_pair_half_distance(centres: list[list[float]]) -> float:
    pts = np.asarray(centres)
    diff = pts[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff**2).sum(-1))
    np.fill_diagonal(dist, np.inf)
    return float(dist.min() / 2.0)


def _min_boundary_margin(centres: list[list[float]]) -> float:
    pts = np.asarray(centres)
    return float(min(pts[:, 0].min(), (1.0 - pts[:, 0]).min(), pts[:, 1].min(), (1.0 - pts[:, 1]).min()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=26)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--iters", type=int, default=40)
    ap.add_argument("--budgets", type=str, default="200,2000,20000")
    ap.add_argument("--shrink-budgets", type=str, default="100,1000,6000")
    ap.add_argument("--hi-side", type=float, default=12.0)
    ap.add_argument("--lo-side", type=float, default=9.0)
    ap.add_argument("--safety", type=float, default=1e-7)
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()

    budgets = tuple(int(x) for x in args.budgets.split(","))
    shrink_budgets = tuple(int(x) for x in args.shrink_budgets.split(","))
    r_opt, centres = optimise(
        args.n,
        args.seed,
        args.trials,
        args.iters,
        budgets,
        shrink_budgets,
        args.hi_side,
        args.lo_side,
    )
    centres = [[float(x), float(y)] for x, y in centres]
    pair_half = _min_pair_half_distance(centres)
    boundary = _min_boundary_margin(centres)
    achieved = min(pair_half, boundary)
    r_used = achieved - args.safety
    if r_used <= 0.0:
        raise RuntimeError(f"non-positive radius after safety margin: {r_used}")
    payload = {
        "n": args.n,
        "seed": args.seed,
        "trials": args.trials,
        "iters": args.iters,
        "budgets": list(budgets),
        "shrink_budgets": list(shrink_budgets),
        "hi_side": args.hi_side,
        "lo_side": args.lo_side,
        "r_opt": r_opt,
        "achieved_min_pair_half_distance": pair_half,
        "achieved_min_boundary_margin": boundary,
        "achieved_min_margin": achieved,
        "safety": args.safety,
        "r_used": r_used,
        "sum_radii": r_used * args.n,
        "centres": centres,
    }
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
