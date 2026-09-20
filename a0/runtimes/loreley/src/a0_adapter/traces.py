"""The three A0 traces, written and self-validated.

Layout and field semantics come from ``a0/contract/trace_schema.md``; the
validator is ``a0/contract/trace_validate.py``.  The writer refuses to let the
adapter claim success on an invalid stream (``adapter_contract.md`` §6.3).

One deliberate deviation is recorded here rather than hidden: the mandated
per-kind files are validated *individually* by ``trace_validate.py``, and that
validator resolves ``selection.source_score_event_id`` only against score events
in the same file (``trace_validate.py:169-192``).  A selection file therefore
cannot carry a resolvable reference.  The writer emits

* the three mandated per-kind files, with ``source_score_event_id: null`` and the
  join available through ``(iteration, candidate_id)`` - the keys
  ``trace_schema.md`` §2 prescribes; and
* one combined ``<runtime>.<run_id>.all.jsonl`` stream in which
  ``source_score_event_id`` names the real score event, so
  "the decision was driven by the score" is machine-checkable somewhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .contracts import A0_ROOT, AdapterError, EXIT_INTERNAL

VALIDATOR = A0_ROOT / "contract" / "trace_validate.py"
VALIDATOR_PYTHON = A0_ROOT / "contract" / ".venv" / "bin" / "python"

KINDS = ("score", "selection", "resource")


@dataclass(slots=True)
class TracePaths:
    score: Path
    selection: Path
    resource: Path
    combined: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "score": str(self.score),
            "selection": str(self.selection),
            "resource": str(self.resource),
            "combined": str(self.combined),
        }


class TraceWriter:
    """Append-only jsonl writer for one (runtime, run) pair."""

    def __init__(
        self,
        *,
        run_dir: Path,
        runtime: str,
        run_id: str,
        task: str,
        kinds: Sequence[str] = KINDS,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.runtime = runtime
        self.run_id = run_id
        self.task = task
        self.kinds = tuple(kinds)
        self.traces_dir = self.run_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.paths = TracePaths(
            score=self.traces_dir / f"{runtime}.{run_id}.score.jsonl",
            selection=self.traces_dir / f"{runtime}.{run_id}.selection.jsonl",
            resource=self.traces_dir / f"{runtime}.{run_id}.resource.jsonl",
            combined=self.traces_dir / f"{runtime}.{run_id}.all.jsonl",
        )
        self._seq = 0
        self._handles: dict[str, Any] = {}
        for kind in self.kinds:
            path = self._path_for(kind)
            path.write_text("", encoding="utf-8")
            self._handles[kind] = path.open("a", encoding="utf-8")
        self.paths.combined.write_text("", encoding="utf-8")
        self._combined = self.paths.combined.open("a", encoding="utf-8")

    # -- internals -------------------------------------------------------

    def _path_for(self, kind: str) -> Path:
        return {
            "score": self.paths.score,
            "selection": self.paths.selection,
            "resource": self.paths.resource,
        }[kind]

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def emit(
        self,
        kind: str,
        *,
        event_id: str,
        iteration: int,
        candidate_id: str,
        parent_id: str | None = None,
        eid_star: str,
        eid_r: Mapping[str, Any],
        theta_e: Mapping[str, Any],
        failure_stage: str = "none",
        failure_detail: str | None = None,
        extra: Mapping[str, Any] | None = None,
        combined_extra: Mapping[str, Any] | None = None,
    ) -> str:
        """Emit one event into its per-kind file and into the combined stream."""

        if kind not in self.kinds:
            raise AdapterError(f"trace kind {kind!r} was not enabled for this run")
        seq = self._next_seq()
        common: dict[str, Any] = {
            "trace": kind,
            "event_id": event_id,
            "event_seq": seq,
            "run_id": self.run_id,
            "task": self.task,
            "runtime": self.runtime,
            "iteration": int(iteration),
            "candidate_id": candidate_id,
            "parent_id": parent_id,
            "eid_star": eid_star,
            "eid_r": dict(eid_r),
            "theta_E": dict(theta_e),
            "failure_stage": failure_stage,
            "failure_detail": failure_detail,
        }
        event = {**common, **dict(extra or {})}
        if kind == "selection":
            # trace_validate.py resolves source_score_event_id only against score
            # events in the SAME file (trace_validate.py:169-192), and a per-kind
            # selection file contains none.  The per-kind line therefore carries a
            # null reference and the join is by (iteration, candidate_id); the
            # combined line keeps the real id so the reference is checkable
            # somewhere.  See the module docstring.
            event = _without_score_reference(event)
        self._handles[kind].write(json.dumps(event, sort_keys=False) + "\n")
        self._handles[kind].flush()

        combined_event = {**event, **dict(extra or {}), **dict(combined_extra or {})}
        self._combined.write(json.dumps(combined_event, sort_keys=False) + "\n")
        self._combined.flush()
        return event_id

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._combined.close()

    # -- validation ------------------------------------------------------

    def validate(self) -> list[dict[str, Any]]:
        """Validate every written stream; raise if any stream is invalid."""

        results: list[dict[str, Any]] = []
        for path in (self.paths.score, self.paths.selection, self.paths.resource,
                     self.paths.combined):
            if not path.exists():
                continue
            completed = _run_validator(path)
            results.append(completed)
            if completed["returncode"] != 0:
                raise AdapterError(
                    f"trace {path.name} is invalid: {completed['stdout'].strip()[:800]}",
                    code=EXIT_INTERNAL,
                )
        return results

    def stats(self) -> list[dict[str, Any]]:
        return [_run_validator(path, command="stats") for path in
                (self.paths.score, self.paths.selection, self.paths.resource,
                 self.paths.combined) if path.exists()]


def _without_score_reference(event: Mapping[str, Any]) -> dict[str, Any]:
    """Return the event with ``selection.source_score_event_id`` nulled."""

    selection = event.get("selection")
    if not isinstance(selection, Mapping):
        return dict(event)
    stripped = dict(selection)
    stripped["source_score_event_id"] = None
    return {**dict(event), "selection": stripped}


def _run_validator(path: Path, *, command: str = "validate") -> dict[str, Any]:
    interpreter = VALIDATOR_PYTHON if VALIDATOR_PYTHON.is_file() else Path(sys.executable)
    completed = subprocess.run(
        [str(interpreter), str(VALIDATOR), command, "--trace", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return {
        "path": str(path),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
    }


def failure_stage_counts(paths: Iterable[Path]) -> dict[str, int]:
    """Per-``failure_stage`` counts over the (run, iteration, candidate) units.

    Counting by unit, not by line, is what ``trace_schema.md`` §4 asks for; this
    reuses the contract's own ``stats`` implementation by parsing its output so
    that the adapter cannot invent a different counting rule.
    """

    counts: dict[str, int] = {}
    for path in paths:
        if not path.exists():
            continue
        result = _run_validator(path, command="stats")
        for line in result["stdout"].splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in {
                "search_failed", "resolve_failed", "comprehension_failed",
                "mechanism_mismatch", "other_failures",
            }:
                counts[parts[0]] = int(parts[1])
    return counts


def stage_histogram(paths: Iterable[Path]) -> dict[str, int]:
    """Every ``failure_stage`` value, counted by unit, straight from the events.

    ``trace_validate.py stats`` only prints the four stages the protocol names as
    counters plus one aggregate; this histogram keeps the stages the Loreley
    adapter actually emits (``timeout``, ``verify_failed``, ...) visible.
    """

    seen: set[tuple] = set()
    counts: dict[str, int] = {}
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            stage = event.get("failure_stage", "none")
            unit = (event.get("run_id"), event.get("iteration"), event.get("candidate_id"),
                    stage)
            if unit in seen:
                continue
            seen.add(unit)
            counts[stage] = counts.get(stage, 0) + 1
    return counts
