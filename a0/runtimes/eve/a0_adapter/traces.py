"""The run's traces (a0/contract/trace_schema.md), written as jsonl.

One ``TraceWriter`` per run appends to ``<run_dir>/traces/eve.<run_id>.{score,selection,
resource}.jsonl`` plus the merged ``<run_dir>/traces/eve.<run_id>.all.jsonl``. ``event_seq`` is
one monotonic counter shared by the three streams, so a reader can order every event of the run
without relying on wall clocks, and the merged file is the run in exactly that order.

The three per-kind files **partition** the run (``trace_schema.md`` §1): a per-kind file carries
only events of its own ``trace`` kind. A ``selection`` event's ``source_score_event_id`` is
resolved against the score events of the **run's stream**, never against one per-kind file, so
validation is run-level (``trace_validate.py validate-run``) and the merged ``.all.jsonl`` -- the
stream in which that reference resolves -- is written here (``adapter_contract.md`` §6.1, §6.3).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from . import common

TRACE_KINDS = ("score", "selection", "resource")
MERGED_KIND = "all"
VALIDATOR = common.CONTRACT_DIR / "trace_validate.py"
VALIDATOR_PYTHON = common.CONTRACT_DIR / ".venv" / "bin" / "python"


class TraceWriter:
    def __init__(self, run_dir: Path, run_id: str, runtime: str = "eve", task: str = "circle-packing"):
        self.run_dir = Path(run_dir)
        self.trace_dir = self.run_dir / "traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.runtime = runtime
        self.task = task
        self._seq = 0
        self.paths: dict[str, Path] = {
            kind: self.trace_dir / f"{runtime}.{run_id}.{kind}.jsonl"
            for kind in TRACE_KINDS + (MERGED_KIND,)
        }
        for path in self.paths.values():
            path.write_text("", encoding="utf-8")
        self.counts: dict[str, int] = {kind: 0 for kind in TRACE_KINDS}

    @property
    def merged_path(self) -> Path:
        """The run's stream: every event of the run, in ``event_seq`` order."""
        return self.paths[MERGED_KIND]

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def _append(self, kind: str, payload: dict[str, Any]) -> None:
        """Append one event to its per-kind file and to the run's merged stream.

        The same bytes go to both, so the union of the per-kind files equals the merged stream
        exactly once (``trace_schema.md`` §1.1). Only ``emit`` writes, so an event is never
        copied into a file of another kind.
        """
        line = json.dumps(payload, sort_keys=True, default=str) + "\n"
        for target in (kind, MERGED_KIND):
            with open(self.paths[target], "a", encoding="utf-8") as handle:
                handle.write(line)

    def emit(self, kind: str, event: dict[str, Any]) -> int:
        if kind not in TRACE_KINDS:
            raise ValueError(f"unknown trace kind {kind!r}")
        payload = dict(event)
        payload["trace"] = kind
        payload["run_id"] = self.run_id
        payload["runtime"] = self.runtime
        payload["task"] = self.task
        payload.setdefault("ts", common.utc_now())
        payload["event_seq"] = self._next_seq()
        payload.setdefault("parent_id", None)
        payload.setdefault("failure_detail", None)
        self._append(kind, payload)
        self.counts[kind] += 1
        return payload["event_seq"]

    def score_event_id(self, iteration: int, candidate_id: str) -> str:
        return f"{self.run_id}-s-i{iteration}-{candidate_id}"

    def score(
        self,
        *,
        iteration: int,
        candidate_id: str,
        envelope: dict[str, Any],
        fields: dict[str, Any],
        fr_payload: dict[str, Any],
        search_signal: Any,
        evidence: dict[str, Any],
        event_id: str | None = None,
    ) -> str:
        event_id = event_id or self.score_event_id(iteration, candidate_id)
        self.emit(
            "score",
            {
                "event_id": event_id,
                "iteration": iteration,
                "candidate_id": candidate_id,
                **envelope,
                "outcome": {"fields": common.strip_absolute(fields), "cardinality": len(fields)},
                "fr": fr_payload,
                "search_signal": common.strip_absolute(search_signal),
                "evaluator_evidence": evidence,
            },
        )
        return event_id

    def selection(
        self,
        *,
        iteration: int,
        candidate_id: str,
        envelope: dict[str, Any],
        selection: dict[str, Any],
        event_id: str | None = None,
    ) -> str:
        event_id = event_id or f"{self.run_id}-sel-i{iteration}-{candidate_id}"
        selection = dict(selection)
        selection["reason"] = str(selection.get("reason", ""))
        self.emit(
            "selection",
            {
                "event_id": event_id,
                "iteration": iteration,
                "candidate_id": candidate_id,
                **envelope,
                "selection": selection,
            },
        )
        return event_id

    def resource(
        self,
        *,
        iteration: int,
        candidate_id: str,
        envelope: dict[str, Any],
        t_wall_s: float,
        n_evaluator_calls: int,
        concurrency_cap: int,
        observed_max: int,
        budget_hard: dict[str, Any] | None,
        scope: str = "iteration",
        event_id: str | None = None,
    ) -> str:
        event_id = event_id or f"{self.run_id}-res-i{iteration}-{candidate_id}"
        self.emit(
            "resource",
            {
                "event_id": event_id,
                "iteration": iteration,
                "candidate_id": candidate_id,
                **envelope,
                "T_wall": {
                    "value_sec": round(float(t_wall_s), 6),
                    "clock": "monotonic",
                    "scope": scope,
                },
                "N_evaluatorCalls": int(n_evaluator_calls),
                "concurrency": {"cap": int(concurrency_cap), "observed_max": int(observed_max)},
                "secondary": {
                    "N_modelCalls": None,
                    "T_in": None,
                    "T_out": None,
                    "C_usd": None,
                },
                "budget_hard": budget_hard,
            },
        )
        return event_id

    def validate(self) -> dict[str, Any]:
        """Validate the run as one stream, and report the per-kind failure counters.

        The validation unit is the **run**, not the file (``adapter_contract.md`` §6.3): a
        selection event names a score event that lives in another per-kind file, so a per-kind
        file cannot resolve that reference on its own. ``validate-run`` checks every run under
        ``run_dir`` -- reading the merged file when it is present, otherwise composing the same
        stream from the per-kind files in ``event_seq`` order -- and additionally checks each
        per-kind file for event-level validity and kind purity. ``validate`` on the merged file
        is the same verdict for this one run.
        """
        run = subprocess.run(
            [str(VALIDATOR_PYTHON), str(VALIDATOR), "validate-run", "--run-dir", str(self.run_dir)],
            capture_output=True,
            text=True,
        )
        merged = subprocess.run(
            [str(VALIDATOR_PYTHON), str(VALIDATOR), "validate", "--trace", str(self.merged_path)],
            capture_output=True,
            text=True,
        )
        results: dict[str, Any] = {
            "run_dir": str(self.run_dir),
            "run": {
                "path": str(self.run_dir),
                "validate_rc": run.returncode,
                "validate_out": (run.stdout or run.stderr).strip(),
            },
            "merged": {
                "path": str(self.merged_path),
                "validate_rc": merged.returncode,
                "validate_out": (merged.stdout or merged.stderr).strip(),
            },
        }
        for kind in TRACE_KINDS:
            path = self.paths[kind]
            stats = subprocess.run(
                [str(VALIDATOR_PYTHON), str(VALIDATOR), "stats", "--trace", str(path)],
                capture_output=True,
                text=True,
            )
            results[kind] = {
                "path": str(path),
                "stats_rc": stats.returncode,
                "stats_out": (stats.stdout or stats.stderr).strip(),
            }
        results["ok"] = run.returncode == 0 and merged.returncode == 0
        return results
