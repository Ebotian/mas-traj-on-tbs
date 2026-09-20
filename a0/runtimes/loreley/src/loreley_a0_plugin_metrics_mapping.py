"""T3 test double, second path: a plugin that returns a **Mapping** payload.

``examples/circle_packing_env/evaluate.py`` - the plugin the pinned checkout ships
for this task - returns ``Mapping[str, Any]`` with a ``metrics`` key, not an
``EvalPass``.  A Mapping payload goes through ``Evaluator._coerce_result``
(``loreley/core/worker/evaluator.py:2268``), which is where
``worker_evaluator_max_metrics`` truncation lives (``:2304-2310``); an ``EvalPass``
payload short-circuits at ``:2029-2037`` and never reaches it.

This module exists so the truncation branch can be exercised on the path that
actually applies to it.  It is a declared test double, never used for A0.1/A0.2.
"""

from __future__ import annotations

import os
from pathlib import Path

from loreley.core.worker.evaluator import EvaluationContext

from loreley_a0_plugin import _write_evidence, plugin as _real_plugin

PADDING = int(os.environ.get("A0_T3_PADDING", "70"))


def plugin(context: EvaluationContext) -> dict:
    result = _real_plugin(context)
    if not hasattr(result, "metrics"):
        # EvalFail: forward the failure representation as a mapping payload.
        return {
            "summary": getattr(result, "summary", "candidate failed"),
            "metrics": [],
        }

    metrics = [
        {
            "name": item.name,
            "value": item.value,
            "unit": item.unit,
            "higher_is_better": item.higher_is_better,
        }
        for item in result.metrics
    ]
    for index in range(PADDING):
        metrics.append(
            {
                "name": f"a0_padding_{index:03d}",
                "value": float(index),
                "higher_is_better": True,
            }
        )

    candidate_dir = Path(context.worktree)
    _write_evidence(
        {
            "status": "ok",
            "measured_scoring": True,
            "detail": None,
            "t3_probe": True,
            "t3_payload": "mapping",
            "candidate_dir": str(candidate_dir),
            "metrics_returned": len(metrics),
            "metrics_returned_names": [item["name"] for item in metrics],
        },
        candidate_dir=candidate_dir,
    )
    return {
        "summary": f"{result.summary} [+{PADDING} padding metrics, Mapping payload]",
        "metrics": metrics,
    }
