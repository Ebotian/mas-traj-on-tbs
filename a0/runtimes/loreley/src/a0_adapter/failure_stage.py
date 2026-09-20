"""The frozen E* verdict -> FailureStage table, and the unit basis of the counts.

``adapter_contract.md`` §5.3 freezes the table A0-wide, because ``plan:577``'s
per-runtime ``FailureStage`` totals are only joinable if every runtime stages the
same verdicts the same way.  The canonical copy is
``a0/contract/selection/simpleloop.selection.json``; this adapter adopts it verbatim
in ``a0/runtimes/loreley/policy/loreley.selection.json`` and **recomputes both the
"`block's canonical digest and the frozen value on every run**, refusing to report a
run in which they differ (the KAPSO workstream does the same).

Two things are deliberately separated here:

* ``stage_for`` - the *staging*: which stage an ``E*`` verdict belongs to.  Pure
  function of ``(status, failure.kind)``, taken from the frozen table.
* ``score_trace_counts`` - the *unit basis*: one unit per member of ``C*``, read
  from the score trace, which is exactly the runner's own counting rule
  (``conformance.py::count_failure_stages`` reads ``trace_paths["score"]`` and keys
  by ``(run_id, candidate_id, iteration)``).  Adapter-level events that are not
  candidates - the run-level resource event and the report-branch selection row -
  are therefore not units, and a count that included them would describe a
  different basis from every other runtime's.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FROZEN_MAPPING_DIGEST = "201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f"
FROZEN_SCALARIZATION_DIGEST = (
    "d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c"
)
FROZEN_SOURCE = "a0/contract/selection/simpleloop.selection.json"
ADOPTED_COPY = "a0/runtimes/loreley/policy/loreley.selection.json"

# The table, verbatim (a0/contract/selection/simpleloop.selection.json ->
# failure_stage_mapping).  Kept as data rather than as code so that the digest
# check below can be run against the file the adapter actually reads.
FROZEN_FAILURE_STAGE_MAPPING: dict[str, str] = {
    "exit_0_ok": "none",
    "exit_2_invalid": "verify_failed",
    "exit_3_error_candidate_call_raised": "evaluator_failed",
    "exit_3_error_candidate_import_failed": "resolve_failed",
    "exit_3_error_child_terminated_early": "evaluator_failed",
    "exit_3_error_non_deterministic": "verify_failed",
    "exit_3_error_other": "evaluator_failed",
    "exit_3_error_runtime_budget_exceeded": "timeout",
    "note": (
        "E* verdict -> trace failure_stage. The trace schema fixes the enum but not this "
        "per-runtime mapping; SimpleLoop freezes it here and reports it to the contract owner "
        "so the other runtimes can adopt the same one."
    ),
    "solver_lane_produced_no_proposal": "search_failed",
}

# E* failure.kind -> table row.  A kind outside this map is the table's
# `exit_3_error_other` -> evaluator_failed.
_KIND_ROWS = {
    "candidate_call_raised": "exit_3_error_candidate_call_raised",
    "candidate_import_failed": "exit_3_error_candidate_import_failed",
    "child_terminated_early": "exit_3_error_child_terminated_early",
    "non_deterministic": "exit_3_error_non_deterministic",
    "runtime_budget_exceeded": "exit_3_error_runtime_budget_exceeded",
}

# The stages this adapter can emit, in the trace schema's vocabulary.
LORELEY_STAGES = ("none", "verify_failed", "resolve_failed", "evaluator_failed", "timeout")


def canonical_block_digest(block: Mapping[str, Any]) -> str:
    """``sha256(canonical_json(block))`` - the digest convention the contract uses."""

    payload = json.dumps(block, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def adopted_document_path() -> Path:
    return Path(__file__).resolve().parents[2] / "policy" / "loreley.selection.json"


def adopt() -> dict[str, Any]:
    """Verify that the adopted copy still carries the frozen blocks; raise if not.

    Returns a small block that is recorded on every conformance document, so a
    reader can see the adoption was checked rather than asserted.
    """

    path = adopted_document_path()
    document = json.loads(path.read_text(encoding="utf-8"))
    mapping = document.get("failure_stage_mapping") or {}
    scalarization = document.get("scalarization") or {}
    mapping_digest = canonical_block_digest(mapping)
    scalarization_digest = canonical_block_digest(scalarization)
    in_code_digest = canonical_block_digest(FROZEN_FAILURE_STAGE_MAPPING)
    problems: list[str] = []
    if mapping_digest != FROZEN_MAPPING_DIGEST:
        problems.append(
            f"{path.name}: failure_stage_mapping digest {mapping_digest} != frozen "
            f"{FROZEN_MAPPING_DIGEST} ({FROZEN_SOURCE})"
        )
    if scalarization_digest != FROZEN_SCALARIZATION_DIGEST:
        problems.append(
            f"{path.name}: scalarization digest {scalarization_digest} != frozen "
            f"{FROZEN_SCALARIZATION_DIGEST} ({FROZEN_SOURCE})"
        )
    if in_code_digest != FROZEN_MAPPING_DIGEST:
        problems.append(
            "the in-code copy of the table has drifted from the frozen digest "
            f"({in_code_digest} != {FROZEN_MAPPING_DIGEST})"
        )
    if problems:
        raise RuntimeError(
            "the adopted failure_stage_mapping is not the frozen one: " + "; ".join(problems)
        )
    return {
        "adopted_copy": str(path),
        "frozen_source": FROZEN_SOURCE,
        "failure_stage_mapping_digest": mapping_digest,
        "failure_stage_mapping_digest_expected": FROZEN_MAPPING_DIGEST,
        "scalarization_digest": scalarization_digest,
        "scalarization_digest_expected": FROZEN_SCALARIZATION_DIGEST,
        "verified": True,
    }


def stage_for(status: str | None, failure_kind: str | None) -> str | None:
    """The frozen table applied to one ``E*`` verdict.

    ``status`` is ``E*``'s own verdict (``ok`` / ``invalid`` / ``error``) and
    ``failure_kind`` is ``E*``'s ``failure.kind``; both come from the same Outcome.
    A verdict with no stage (nothing was evaluated) returns ``None``.
    """

    normalized = (status or "").strip().lower()
    if normalized == "ok":
        return FROZEN_FAILURE_STAGE_MAPPING["exit_0_ok"]
    if normalized == "invalid":
        return FROZEN_FAILURE_STAGE_MAPPING["exit_2_invalid"]
    if normalized == "error":
        row = _KIND_ROWS.get((failure_kind or "").strip())
        if row is None:
            row = "exit_3_error_other"
        return FROZEN_FAILURE_STAGE_MAPPING[row]
    return None


def is_frozen_stage(stage: str | None) -> bool:
    return stage in LOREley_STAGES if stage is not None else False


def score_trace_counts(paths: Iterable[Path]) -> tuple[dict[str, int], int]:
    """One unit per ``(run_id, iteration, candidate_id)`` in the **score** trace.

    The score trace carries exactly one event per member of ``C*``, so this is the
    basis the conformance runner compares against the frozen map.  Returns
    ``(counts, units)``.
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
            if event.get("trace") != "score":
                continue
            stage = event.get("failure_stage") or "none"
            unit = (event.get("run_id"), event.get("iteration"), event.get("candidate_id"))
            if unit in seen:
                continue
            seen.add(unit)
            counts[stage] = counts.get(stage, 0) + 1
    return counts, len(seen)


def expected_from_candidates(candidates: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """The frozen map applied to a list of ``{"status", "failure_kind"}`` records.

    Used by the adapter's own report so it can state the expectation next to the
    measurement without asking the runner.
    """

    expected: dict[str, int] = {}
    for item in candidates:
        stage = stage_for(item.get("status"), item.get("failure_kind"))
        if stage:
            expected[stage] = expected.get(stage, 0) + 1
    return expected


def unit_basis_note(units: int, candidates: int) -> str:
    return (
        f"one unit per member of C*: {units} unit(s) for {candidates} candidate(s), counted from the "
        "score trace by (run_id, iteration, candidate_id) - the same rule the conformance runner uses "
        "in count_failure_stages(). Adapter-level events that are not candidates (the run-level "
        "resource event, the report-branch selection row) are not units."
    )
