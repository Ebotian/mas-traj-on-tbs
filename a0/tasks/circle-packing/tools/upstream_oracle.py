"""Run upstream's own evaluator plugin on one candidate, as an oracle.

Loads `examples/circle_packing_env/evaluate.py` from the pinned Loreley checkout
and calls its `plugin(context)` with a minimal stub context, exactly as the
Loreley worker would.  Prints one JSON object describing what upstream did:

    {"verdict": "returned", "sum_radii": ..., "packing_density": ..., ...}
    {"verdict": "raised", "error": "ValueError: ..."}

This exists so that E*'s objective and validity verdicts can be compared against
upstream's own code instead of against a description of it.  It is a tool: it
needs loguru and rich (upstream imports them at module level) and is run from
`.venv-tools`, never from E*'s interpreter.

    .venv-tools/bin/python tools/upstream_oracle.py --candidate C_STAR/c01_good_hex
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPSTREAM_PLUGIN = ROOT / "upstream" / "loreley" / "examples" / "circle_packing_env" / "evaluate.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("upstream_circle_packing_evaluate", UPSTREAM_PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, help="candidate directory containing solution.py")
    args = parser.parse_args()

    module = load_plugin()
    worktree = Path(args.candidate).expanduser().resolve()
    try:
        result = module.plugin(SimpleNamespace(worktree=worktree))
    except BaseException as exc:  # noqa: BLE001 - reporting what upstream does
        print(json.dumps({"verdict": "raised", "error": f"{type(exc).__name__}: {exc}"}))
        return 0

    metrics = {entry["name"]: entry["value"] for entry in result["metrics"]}
    print(
        json.dumps(
            {
                "verdict": "returned",
                "sum_radii": metrics.get("sum_radii"),
                "packing_density": metrics.get("packing_density"),
                "num_circles": metrics.get("num_circles"),
                "runtime_p50_ms": metrics.get("runtime_p50_ms"),
                "tests_executed": list(result["tests_executed"]),
                "deterministic": result["extra"]["runtime_deterministic"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
