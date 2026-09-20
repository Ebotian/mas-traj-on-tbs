from __future__ import annotations

from typing import Iterable, List, Tuple


def pack_circles(n: int = 26) -> Iterable[Tuple[float, float, float]]:
    """
    Construct a very simple packing of n disjoint circles in the unit square.

    - For n == 1 this returns a single circle of radius 0.5 centred at (0.5, 0.5).
    - For n >= 2 this returns n equal-radius circles placed along the main diagonal
      of the square, from the bottom-left corner towards the top-right corner.

    The construction is deliberately simple and only aims to produce a valid
    configuration; it is not intended to be close to optimal for the objective that
    maximises the sum of all radii.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer.")

    if n == 1:
        # One circle touching all four sides of the square.
        return [(0.5, 0.5, 0.5)]

    # For n >= 2, choose a small radius that guarantees non-overlap and that all circles
    # remain inside the unit square. The factor 4 * n keeps centres well separated along
    # the diagonal.
    r = 1.0 / (4.0 * n)

    # Place n centres evenly along the main diagonal segment from (r, r) to (1 - r, 1 - r).
    positions = [i / (n - 1) for i in range(n)]

    step = 1.0 - 2.0 * r
    circles: List[Tuple[float, float, float]] = []
    for t in positions:
        x = r + t * step
        y = r + t * step
        circles.append((x, y, r))

    return circles

