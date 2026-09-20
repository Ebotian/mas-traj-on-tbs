"""Circle packing candidate — place 26 circles in a unit square to maximize sum of radii.

The AlphaEvolve benchmark target is 2.635.
"""

from __future__ import annotations

import numpy as np


def construct_packing() -> tuple[np.ndarray, np.ndarray]:
    """Construct an arrangement of 26 circles in a unit square.

    Returns (centers, radii) where:
    - centers is (26, 2) array of circle center positions in [0, 1]^2
    - radii is (26,) array of circle radii

    Circles must not overlap each other or extend outside the unit square.
    """

    centers = np.zeros((26, 2))
    centers[0] = [0.5, 0.5]

    for index in range(8):
        angle = 2 * np.pi * index / 8
        centers[index + 1] = [0.5 + 0.3 * np.cos(angle), 0.5 + 0.3 * np.sin(angle)]

    for index in range(16):
        angle = 2 * np.pi * index / 16
        centers[index + 9] = [0.5 + 0.7 * np.cos(angle), 0.5 + 0.7 * np.sin(angle)]

    centers = np.clip(centers, 0.01, 0.99)
    radii = compute_max_radii(centers)
    return centers, radii


def compute_max_radii(centers: np.ndarray) -> np.ndarray:
    """Compute the largest non-overlapping radius for each center."""

    circle_count = centers.shape[0]
    radii = np.ones(circle_count)

    for index in range(circle_count):
        x_value, y_value = centers[index]
        radii[index] = min(x_value, y_value, 1 - x_value, 1 - y_value)

    for left in range(circle_count):
        for right in range(left + 1, circle_count):
            distance = np.sqrt(np.sum((centers[left] - centers[right]) ** 2))
            if radii[left] + radii[right] > distance:
                scale = distance / (radii[left] + radii[right])
                radii[left] *= scale
                radii[right] *= scale

    return radii
