"""T3 test double: a plugin that emits more metrics than Loreley keeps.

This is *not* the A0 evaluator.  It wraps the real plugin and returns its result
with extra synthetic metrics appended, so that the runtime's own truncation branch
(``loreley/core/worker/evaluator.py:2304-2310``, cap
``worker_evaluator_max_metrics`` default 64 at ``config.py:565-568``) can be
observed on real runtime code.  Using it is recorded explicitly in
``out/loreley-traps.json``; no A0.1 or A0.2 result is produced with it.

It rewrites the evidence record with ``metrics_returned = 64 + PADDING`` so the
adapter can compute how many metrics the runtime dropped
(``emitted - len(runtime_metrics)``) instead of guessing.
"""

from __future__ import annotations

import os

from loreley.core.worker.evaluator import EvalFail, EvalPass, EvaluationContext

from loreley_a0_plugin import _write_evidence, plugin as _real_plugin

PADDING = int(os.environ.get("A0_T3_PADDING", "70"))


def plugin(context: EvaluationContext) -> EvalPass | EvalFail:
    result = _real_plugin(context)
    if isinstance(result, EvalFail):
        return result
    padded = list(result.metrics)
    for index in range(PADDING):
        padded.append(
            {
                "name": f"a0_padding_{index:03d}",
                "value": float(index),
                "unit": None,
                "higher_is_better": True,
                "details": {"source": "T3 truncation probe"},
            }
        )

    from pathlib import Path

    candidate_dir = Path(context.worktree)
    # Overwrite the record the real plugin just wrote: the count must describe what
    # this plugin emitted, not what the inner call emitted.
    _write_evidence(
        {
            "status": "ok",
            "measured_scoring": True,
            "detail": None,
            "t3_probe": True,
            "candidate_dir": str(candidate_dir),
            "metrics_returned": len(padded),
            "metrics_returned_names": [
                item.get("name") if isinstance(item, dict) else item.name for item in padded
            ],
        },
        candidate_dir=candidate_dir,
    )
    return EvalPass(
        summary=f"{result.summary} [+{PADDING} padding metrics for the T3 probe]",
        metrics=padded,
        extra=dict(result.extra or {}),
        candidate_identity=result.candidate_identity,
    )
