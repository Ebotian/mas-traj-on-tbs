"""Valid but nearly worthless candidate: 26 circles of radius 1e-6 in a
tight cluster at the centre of the square. sum_radii ~ 2.6e-05."""

from __future__ import annotations

from typing import Iterable, List, Tuple


def _fallback(n: int) -> List[Tuple[float, float, float]]:
    """Upstream's baseline construction, valid for any n (solution.py@b91c090)."""
    if n <= 0:
        raise ValueError("n must be a positive integer.")
    if n == 1:
        return [(0.5, 0.5, 0.5)]
    r = 1.0 / (4.0 * n)
    step = 1.0 - 2.0 * r
    return [(r + (i / (n - 1)) * step, r + (i / (n - 1)) * step, r) for i in range(n)]


def pack_circles(n: int = 26) -> Iterable[Tuple[float, float, float]]:
    """Return (x, y, r) triples for n circles in the unit square."""
    if n <= 0:
        raise ValueError("n must be a positive integer.")
    radius = 1e-6
    spacing = 1e-5
    circles: List[Tuple[float, float, float]] = []
    for index in range(n):
        row, col = divmod(index, 13)
        circles.append(
            (
                0.5 - 6.0 * spacing + col * spacing,
                0.5 + (row - 0.5) * spacing,
                radius,
            )
        )
    return circles
