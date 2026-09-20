"""Numerically search for high-sum 26-circle packings in the unit square."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


N = 26
PAIR_I, PAIR_J = np.triu_indices(N, 1)


def constraints(values: np.ndarray) -> np.ndarray:
    x = values[:N]
    y = values[N : 2 * N]
    radii = values[2 * N :]
    dx = x[PAIR_I] - x[PAIR_J]
    dy = y[PAIR_I] - y[PAIR_J]
    distances = np.hypot(dx, dy)
    return np.concatenate(
        (
            x - radii,
            1.0 - x - radii,
            y - radii,
            1.0 - y - radii,
            distances - radii[PAIR_I] - radii[PAIR_J],
        )
    )


def constraints_jac(values: np.ndarray) -> np.ndarray:
    x = values[:N]
    y = values[N : 2 * N]
    dx = x[PAIR_I] - x[PAIR_J]
    dy = y[PAIR_I] - y[PAIR_J]
    distances = np.maximum(np.hypot(dx, dy), 1e-15)

    jac = np.zeros((4 * N + len(PAIR_I), 3 * N))
    indices = np.arange(N)
    jac[indices, indices] = 1.0
    jac[indices, 2 * N + indices] = -1.0
    jac[N + indices, indices] = -1.0
    jac[N + indices, 2 * N + indices] = -1.0
    jac[2 * N + indices, N + indices] = 1.0
    jac[2 * N + indices, 2 * N + indices] = -1.0
    jac[3 * N + indices, N + indices] = -1.0
    jac[3 * N + indices, 2 * N + indices] = -1.0

    rows = 4 * N + np.arange(len(PAIR_I))
    ux = dx / distances
    uy = dy / distances
    jac[rows, PAIR_I] = ux
    jac[rows, PAIR_J] = -ux
    jac[rows, N + PAIR_I] = uy
    jac[rows, N + PAIR_J] = -uy
    jac[rows, 2 * N + PAIR_I] = -1.0
    jac[rows, 2 * N + PAIR_J] = -1.0
    return jac


def objective(values: np.ndarray) -> float:
    return -float(np.sum(values[2 * N :]))


def objective_jac(values: np.ndarray) -> np.ndarray:
    result = np.zeros(3 * N)
    result[2 * N :] = -1.0
    return result


def seed_from_rows(rows: tuple[int, ...], phase: int = 0) -> np.ndarray:
    points = []
    row_count = len(rows)
    for row, count in enumerate(rows):
        y = (row + 0.5) / row_count
        offset = 0.5 * ((row + phase) % 2)
        for column in range(count):
            x = (column + 0.5 + offset) / (count + offset)
            points.append((x, y))
    centers = np.asarray(points, dtype=float)
    if len(centers) != N:
        raise ValueError(f"rows must contain {N} circles")

    boundary = np.min(np.column_stack((centers, 1.0 - centers)), axis=1)
    distances = np.hypot(
        centers[PAIR_I, 0] - centers[PAIR_J, 0],
        centers[PAIR_I, 1] - centers[PAIR_J, 1],
    )
    initial_radius = 0.88 * min(float(np.min(boundary)), float(np.min(distances)) / 2.0)
    return np.concatenate((centers[:, 0], centers[:, 1], np.full(N, initial_radius)))


def optimize(values: np.ndarray, maxiter: int = 2500):
    return minimize(
        objective,
        values,
        jac=objective_jac,
        bounds=[(0.0, 1.0)] * (2 * N) + [(0.0, 0.5)] * N,
        constraints={"type": "ineq", "fun": constraints, "jac": constraints_jac},
        method="SLSQP",
        options={"ftol": 2e-12, "maxiter": maxiter, "disp": False},
    )


def perturb(values: np.ndarray, rng: np.random.Generator, scale: float) -> np.ndarray:
    result = values.copy()
    radii = result[2 * N :]
    # Opening a small amount of clearance lets SLSQP move away from the current
    # contact graph and settle into a neighboring basin.
    radii *= 0.94
    result[: 2 * N] += rng.normal(0.0, scale, 2 * N)
    result[:N] = np.clip(result[:N], radii, 1.0 - radii)
    result[N : 2 * N] = np.clip(result[N : 2 * N], radii, 1.0 - radii)
    pair_clearance = constraints(result)[4 * N :]
    if np.min(pair_clearance) < 0.0:
        radii *= 0.90
    return result


def format_result(values: np.ndarray) -> str:
    x = values[:N]
    y = values[N : 2 * N]
    radii = values[2 * N :]
    lines = [f"score={sum(radii):.15f} min_constraint={np.min(constraints(values)):.3e}"]
    lines.append("PACKING_26 = (")
    for index in range(N):
        lines.append(f"    ({x[index]:.17g}, {y[index]:.17g}, {radii[index]:.17g}),")
    lines.append(")")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    patterns = (
        (4, 5, 4, 5, 4, 4),
        (4, 4, 5, 4, 5, 4),
        (5, 4, 4, 5, 4, 4),
        (3, 4, 5, 5, 5, 4),
        (4, 5, 5, 5, 4, 3),
        (3, 4, 4, 4, 4, 4, 3),
        (4, 4, 4, 4, 4, 3, 3),
    )
    rng = np.random.default_rng(args.seed)
    best = None
    for pattern in patterns:
        for phase in (0, 1):
            result = optimize(seed_from_rows(pattern, phase))
            score = -result.fun if np.min(constraints(result.x)) >= -2e-8 else -math.inf
            print(pattern, phase, result.success, result.nit, f"{score:.12f}", result.message, flush=True)
            if best is None or score > -best.fun:
                best = result

    assert best is not None
    for round_index in range(args.rounds):
        starts = [perturb(best.x, rng, 0.004 + 0.003 * round_index) for _ in range(8)]
        for start_index, start in enumerate(starts):
            result = optimize(start)
            score = -result.fun if np.min(constraints(result.x)) >= -2e-8 else -math.inf
            print("perturb", round_index, start_index, result.success, result.nit, f"{score:.12f}", flush=True)
            if score > -best.fun:
                best = result
                print("new best", format_result(best.x), flush=True)

    rendered = format_result(best.x)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n")


if __name__ == "__main__":
    main()
