"""Local evaluator for circle packing — runs candidate.py and reports score as JSON."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path


TARGET_SUM_RADII = 2.635
EXPECTED_CIRCLES = 26


def load_candidate(candidate_path: Path):
    spec = importlib.util.spec_from_file_location("candidate_program", candidate_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load candidate module from {candidate_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "construct_packing", None)
    if not callable(fn):
        raise RuntimeError("candidate.py must define a callable construct_packing() function")
    return fn


def validate_packing(centers, radii):
    """Check that circles don't overlap and stay inside [0, 1]^2."""
    n = len(centers)
    for i in range(n):
        x, y = centers[i]
        r = radii[i]
        if not math.isfinite(x) or not math.isfinite(y):
            return False, f"Circle {i} has non-finite center {(x, y)}"
        if not math.isfinite(r):
            return False, f"Circle {i} has non-finite radius {r}"
        if r < 0:
            return False, f"Circle {i} has negative radius {r}"
        if x - r < -1e-9 or y - r < -1e-9 or x + r > 1 + 1e-9 or y + r > 1 + 1e-9:
            return False, f"Circle {i} extends outside unit square"
    for i in range(n):
        for j in range(i + 1, n):
            dist = math.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1])
            if radii[i] + radii[j] > dist + 1e-9:
                return False, f"Circles {i} and {j} overlap"
    return True, "valid"


def coerce_packing(centers, radii):
    """Convert candidate outputs to plain float containers before validation."""
    def _coerce_builtin_real(value, *, name: str) -> float:
        if isinstance(value, bool) or type(value) not in (int, float):
            raise ValueError(f"{name} entries must be builtin int/float values")
        return float(value)

    try:
        coerced_centers = [
            (
                _coerce_builtin_real(x, name="center"),
                _coerce_builtin_real(y, name="center"),
            )
            for x, y in centers
        ]
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"centers must be an iterable of numeric pairs: {e}") from e

    try:
        coerced_radii = [_coerce_builtin_real(radius, name="radius") for radius in radii]
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"radii must be an iterable of numeric values: {e}") from e

    if len(coerced_centers) != len(coerced_radii):
        raise ValueError(
            "centers and radii must have the same length: "
            f"{len(coerced_centers)} != {len(coerced_radii)}"
        )
    if len(coerced_centers) != EXPECTED_CIRCLES:
        raise ValueError(
            f"construct_packing() must return exactly {EXPECTED_CIRCLES} circles: "
            f"got {len(coerced_centers)}"
        )
    return coerced_centers, coerced_radii


def main() -> None:
    candidate_path = Path(__file__).with_name("candidate.py")
    construct_packing = load_candidate(candidate_path)

    try:
        result = construct_packing()
    except Exception as e:
        print(json.dumps({"status": "error", "score": 0.0, "summary": f"construct_packing() crashed: {e}"}))
        return

    if not isinstance(result, tuple) or len(result) != 2:
        print(json.dumps({
            "status": "error",
            "score": 0.0,
            "summary": "construct_packing() must return (centers, radii)",
        }))
        return

    centers, radii = result
    try:
        centers, radii = coerce_packing(centers, radii)
    except ValueError as e:
        print(json.dumps({"status": "error", "score": 0.0, "summary": str(e)}))
        return

    valid, msg = validate_packing(centers, radii)
    if not valid:
        print(json.dumps({"status": "error", "score": 0.0, "summary": f"Invalid packing: {msg}"}))
        return

    calculated_sum_radii = float(sum(radii))
    if not math.isfinite(calculated_sum_radii):
        print(json.dumps({"status": "error", "score": 0.0, "summary": "calculated radii sum is not finite"}))
        return

    score = calculated_sum_radii
    print(json.dumps({
        "status": "ok",
        "score": score,
        "summary": (
            f"sum_radii={calculated_sum_radii:.6f} "
            f"({len(centers)} circles, target={TARGET_SUM_RADII})"
        ),
        "info": {
            "min_radius": float(min(radii)),
            "max_radius": float(max(radii)),
        },
    }, indent=2))


if __name__ == "__main__":
    main()
