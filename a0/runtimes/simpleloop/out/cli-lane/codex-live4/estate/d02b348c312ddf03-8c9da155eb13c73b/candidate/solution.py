from __future__ import annotations

from math import sqrt
from typing import Iterable, List, Tuple


Circle = Tuple[float, float, float]


def pack_circles(n: int = 26) -> Iterable[Circle]:
    """Return a dense, deterministic packing of up to ``n`` circles."""
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("n must be a positive integer.")

    base_radius = 0.1
    circles: List[Circle] = [
        (x, y, base_radius)
        for y in (0.1, 0.3, 0.5, 0.7, 0.9)
        for x in (0.1, 0.3, 0.5, 0.7, 0.9)
    ]

    if n >= 26:
        # This circle is tangent to the four lattice circles around (0.2, 0.2).
        circles.append((0.2, 0.2, sqrt(0.02) - base_radius))

    return circles[:n]
