"""EvE's adoption of the frozen A0-wide `scalarization` / `failure_stage_mapping` blocks.

`adapter_contract.md` §5.3 makes both blocks A0-wide: all four runtimes must declare the same
null-fold and the same `E*` verdict -> `failure_stage` table, otherwise the per-runtime
`FailureStage` counts that `plan:577` and `plan:628` require cannot be summed. The canonical copy
is `a0/contract/selection/simpleloop.selection.json`; KAPSO's adopted copy is
`a0/contract/selection/kapso.selection.json`; EvE's runtime-side declaration is
`a0/runtimes/eve/selection/eve.selection.json`.

Nothing here trusts any of those files. `check_adoption()` recomputes the canonical digest of each
shared block from the contract's own copy *and* from EvE's copy, compares them with the frozen
values, and the adapter refuses to report a run (exit 3) if any of the three disagrees. That is
what makes the staging below a *declared adoption* rather than a private opinion: a contract owner
who amends the table changes the digest, and every EvE run stops until the copy is re-adopted.

`failure_stage_by_kind()` derives the kind -> stage lookup from the adopted table itself, so the
staging the trace records is a function of the frozen declaration, not of a second hand-written
list that could drift away from it.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import common

# sha256(canonical_json(block)) of the two shared blocks, as frozen by the contract owner.
FROZEN_FAILURE_STAGE_MAPPING_DIGEST = (
    "201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f"
)
FROZEN_SCALARIZATION_DIGEST = (
    "d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c"
)
# Study-relative spellings (what the contract and the reports use); resolved against the repo
# root, which is `common.A0_ROOT`'s parent.
CANONICAL_SOURCE = "a0/contract/selection/simpleloop.selection.json"
RUNTIME_DECLARATION = "a0/runtimes/eve/selection/eve.selection.json"


def _path(relative: str) -> Path:
    return common.REPO_ROOT / relative

# `exit_3_error_<kind>` -> the `E*` failure.kind it names. Derived from the frozen table, never
# hand-maintained: a key the contract adds is picked up, a key it renames disappears.
_KIND_KEY_PREFIX = "exit_3_error_"


class SelectionMappingError(RuntimeError):
    """The adopted A0-wide block does not match the contract's frozen copy -> adapter exit 3."""


def canonical_bytes(value: Any) -> bytes:
    """Same canonicalization as `a0/contract/evalcontract.py::canonical_json`."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def block_digest(block: Any) -> str:
    return hashlib.sha256(canonical_bytes(block)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return _load_cached(str(Path(path)))


@lru_cache(maxsize=None)
def _load_cached(path: str) -> dict[str, Any]:
    """Parsed once per process: the adoption is checked against a fixed snapshot of the contract."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SelectionMappingError(f"cannot read {path}: {exc}") from exc


def check_adoption() -> dict[str, Any]:
    """Recompute both blocks' digests from the contract's copy and from EvE's, and compare.

    Returns the report the conformance document carries; raises `SelectionMappingError` if the
    contract's block differs from the frozen digest, if EvE's copy differs from the contract's, or
    if a block is missing. Refusing to run is the point: a stale adopted table silently produces
    counts that do not join.
    """
    contract_path = _path(CANONICAL_SOURCE)
    eve_path = _path(RUNTIME_DECLARATION)
    contract = _load(contract_path)
    eve = _load(eve_path)
    report: dict[str, Any] = {
        "canonical_source": CANONICAL_SOURCE,
        "runtime_declaration": RUNTIME_DECLARATION,
        "blocks": {},
        "agrees": True,
        "problems": [],
    }
    for name, frozen in (
        ("failure_stage_mapping", FROZEN_FAILURE_STAGE_MAPPING_DIGEST),
        ("scalarization", FROZEN_SCALARIZATION_DIGEST),
    ):
        contract_block = contract.get(name)
        eve_block = eve.get(name)
        contract_digest = block_digest(contract_block) if contract_block else None
        eve_digest = block_digest(eve_block) if eve_block else None
        identical = (
            contract_block is not None
            and eve_block is not None
            and canonical_bytes(contract_block) == canonical_bytes(eve_block)
        )
        report["blocks"][name] = {
            "frozen_digest": frozen,
            "contract_digest": contract_digest,
            "eve_digest": eve_digest,
            "contract_matches_frozen": contract_digest == frozen,
            "eve_matches_contract": identical,
        }
        if contract_digest != frozen:
            report["agrees"] = False
            report["problems"].append(
                f"{name}: {CANONICAL_SOURCE} hashes to {contract_digest}, the frozen contract "
                f"value is {frozen}"
            )
        if not identical:
            report["agrees"] = False
            report["problems"].append(
                f"{name}: {RUNTIME_DECLARATION} does not carry the contract's block "
                f"({eve_digest!r} vs {contract_digest!r})"
            )
    if not report["agrees"]:
        raise SelectionMappingError(
            "the adopted A0-wide selection/scalarization declaration no longer matches the "
            "contract: " + "; ".join(report["problems"])
        )
    return report


def failure_stage_mapping() -> dict[str, Any]:
    """The adopted, verified `failure_stage_mapping` block (contract copy)."""
    check_adoption()
    return _load(_path(CANONICAL_SOURCE))["failure_stage_mapping"]


def failure_stage_by_kind() -> dict[str, str]:
    """`E*` `failure.kind` -> `failure_stage`, derived from the adopted table itself."""
    table = failure_stage_mapping()
    by_kind = {
        key[len(_KIND_KEY_PREFIX):]: value
        for key, value in table.items()
        if key.startswith(_KIND_KEY_PREFIX) and isinstance(value, str)
    }
    if not by_kind:
        raise SelectionMappingError(
            "the adopted failure_stage_mapping carries no exit_3_error_<kind> entries"
        )
    return by_kind


def failure_stage_for(status: str | None, failure_kind: str | None, rc: int) -> str:
    """`E*`'s verdict -> `failure_stage`, per the adopted frozen table (§5.3, §4.5).

    `ok` -> `none`; `invalid` -> `verify_failed`; `error` -> the kind's entry in the adopted
    table, falling back to the table's own `exit_3_error_other` value for a kind it does not
    name. The synthetic check for the nine non-`ok` members of `C*` is then exactly the frozen
    map's `{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}`.
    """
    table = failure_stage_mapping()
    if status == "ok":
        return table["exit_0_ok"]
    if status == "invalid":
        return table["exit_2_invalid"]
    if status == "error":
        return failure_stage_by_kind().get(failure_kind or "", table["exit_3_error_other"])
    # E* wrote no usable Outcome (non-zero rc with no verdict): the table covers this as "other".
    return table["exit_3_error_other"]
