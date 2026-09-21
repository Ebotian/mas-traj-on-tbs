"""Degenerate candidate: pack_circles raises unconditionally."""

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
    raise RuntimeError("this candidate never returns a configuration")
    # unreachable, kept so the module still parses as a solution
    return []  # type: ignore[unreachable]
