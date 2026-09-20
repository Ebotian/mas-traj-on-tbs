#!/usr/bin/env python3
"""Stand-in reference evaluator used to exercise the EID* machinery.

Not the plumbing task's E*: it exists only so that the contract implementation
has a concrete, self-contained input to hash.  The plumbing E* is produced by
the circle-packing workstream under a0/tasks/circle-packing/.
"""

import json
import math
import sys


def evaluate(candidate: dict, *, seed: int, fidelity: str, fraction: float) -> dict:
    n = len(candidate["centers"])
    r = float(candidate["radius"])
    boxes = math.floor(1.0 / (2.0 * r)) if r > 0 else 0
    packed = min(n, boxes * boxes)
    coverage = packed * math.pi * r * r
    return {
        "coverage": coverage,
        "packed": packed,
        "feasible": bool(packed == n and r > 0),
        "seed": seed,
        "fidelity": fidelity,
        "fraction": fraction,
    }


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(evaluate(payload["candidate"], seed=payload["seed"],
                              fidelity=payload["fidelity"], fraction=payload["fraction"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
