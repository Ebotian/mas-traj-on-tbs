"""Frozen SimpleLoop policy: scalarization, tie-break, selection rule.

The protocol's SimpleLoop definition (open_world_plan_review.typ:605-614) fixes
`c*_t = argmax_{i<=t} E(c_i)` and nothing else: it does not say how a multi-field
Outcome folds to a scalar, and it does not say what `argmax` does on a tie. Both
gaps are closed here, in one declared file whose canonical digest is recorded on
every event, so the choice is frozen before the run rather than chosen after it.

Canonical form and digest scheme are copied from a0/contract/evalcontract.py so
that a third party can recompute the digest with the same code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = PACKAGE_DIR.parent

POLICY_PATH = ADAPTER_DIR / "policy" / "simpleloop.policy.json"
INJECT_FR_PATH = ADAPTER_DIR / "policy" / "simpleloop.inject.json"

# The frozen round-one F_r declaration owned by a0/contract (plan:528).
FR_SCALAR_PATH = ADAPTER_DIR.parent.parent / "contract" / "fr" / "scalar.json"

TIE_BREAK_LEXICOGRAPHIC_ID = "smallest_candidate_id_by_utf8_bytes"


class PolicyError(RuntimeError):
    pass


def _stringify_keys(value):
    if isinstance(value, dict):
        return {str(k): _stringify_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_keys(v) for v in value]
    return value


def canonical_bytes(value) -> bytes:
    """Same canonicalization as a0/contract/evalcontract.py::canonical_json."""
    return json.dumps(
        _stringify_keys(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_file_digest(path: Path) -> str:
    """sha256 over the canonical form of the parsed JSON, not over its bytes.

    Reformatting or reordering the file must not change the frozen identity;
    editing any value must.
    """
    with Path(path).open("r", encoding="utf-8") as fh:
        return hashlib.sha256(canonical_bytes(json.load(fh))).hexdigest()


def load_policy(path: Path = POLICY_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        policy = json.load(fh)
    if policy.get("schema") != "a0.simpleloop.policy/v1":
        raise PolicyError(f"unexpected policy schema {policy.get('schema')!r}")
    scalar = policy["scalarization"]
    if scalar["applies"] != "scalar" or scalar["direction"] != "maximize":
        raise PolicyError("round-one F_r must be scalar/maximize (plan:528)")
    # The scalar may name a field of E*'s multi-field Outcome
    # (`outcome.fields.sum_radii`, the plumbing task) or a top-level quantity the
    # Outcome defines (`outcome.cut_edges`, T1's integer-authoritative objective,
    # INTERFACE.md §5). Both are an `outcome.<...>` path; anything else is a
    # scalarization the trace schema cannot describe.
    parts = str(scalar["input"]).split(".")
    if len(parts) == 3 and parts[0] == "outcome" and parts[1] == "fields" and parts[2]:
        pass
    elif len(parts) == 2 and parts[0] == "outcome" and parts[1]:
        pass
    else:
        raise PolicyError(
            f"scalarization.input must be an `outcome.fields.<name>` or `outcome.<name>` "
            f"path; got {scalar['input']!r}"
        )
    if policy["selection"]["tie_break"] != (
        "smallest candidate_id by byte-wise comparison of the UTF-8 encoding of candidate_id"
    ):
        raise PolicyError("tie_break text and TIE_BREAK_LEXICOGRAPHIC_ID have diverged")
    return policy


def primary_field(policy: dict) -> str:
    return policy["scalarization"]["input"].rsplit(".", 1)[1]


def scalar_of(outcome: dict | None, field: str) -> float | None:
    """The frozen F_r fold: fields.<field> iff status == "ok", else None.

    Returning None (never 0.0, never -inf) is what keeps an `invalid` or `error`
    verdict from looking like a bad-but-real score.

    A field is read from `outcome.fields` when the Outcome has one and from the
    Outcome's own top level otherwise. An integer objective (T1's `cut_edges`) is
    returned as an `int`: §5 makes it the only authoritative value, and the
    argmax's exactness is then a property of integer comparison rather than of
    an IEEE-754 equality that happens to be exact at these magnitudes.
    """
    if outcome is None:
        return None
    if outcome.get("status") != "ok":
        return None
    fields = outcome.get("fields") or {}
    value = fields.get(field)
    if value is None:
        value = outcome.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"non-numeric scalar for {field}: {value!r}")
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        raise PolicyError(f"non-finite scalar for {field}: {value!r}")
    objective = (outcome.get("objective") or {}).get("value")
    if objective is not None and objective != value:
        raise PolicyError(
            f"objective.value {objective!r} disagrees with fields.{field} {value!r}"
        )
    return value if isinstance(value, int) else float(value)


def choose(scores: dict[str, float | None]) -> tuple[str | None, str | None]:
    """Frozen selection: argmax over scored candidates, lexicographic-id tie-break.

    `scores` maps candidate_id -> scalar (None = unscored). Returns
    (chosen_candidate_id, tie_break_note). The result is a function of the SET of
    pairs, so it cannot depend on proposal order.
    """
    scored = {cid: s for cid, s in scores.items() if s is not None}
    if not scored:
        return None, None
    best = max(scored.values())
    winners = sorted(cid for cid, s in scored.items() if s == best)
    note = None
    if len(winners) > 1:
        note = (
            f"{len(winners)} candidates share the maximum {best!r}; "
            f"tie_break={TIE_BREAK_LEXICOGRAPHIC_ID} -> {winners[0]!r}"
        )
    return winners[0], note


def choose_earliest_index(scores: dict[str, float | None]) -> str | None:
    """The REJECTED alternative (Python max() over an insertion-ordered sequence
    keeps the first maximum). Implemented only so the A0.2 tie-break check can
    show that it is order-sensitive, i.e. that the frozen rule is not vacuous.
    """
    scored = {cid: s for cid, s in scores.items() if s is not None}
    if not scored:
        return None
    best = max(scored.values())
    for cid, s in scores.items():
        if s is not None and s == best:
            return cid
    return None


def fr_for_events(policy: dict, *, injected: bool = False,
                  policy_path: Path | None = None) -> dict:
    """The `fr` block recorded on every score event."""
    if injected:
        return {
            "name": "F_r = injected external score (B0+ channel probe)",
            "version": "v1",
            "applies": "scalar",
            "spec_hash": canonical_file_digest(INJECT_FR_PATH),
            "declared_in": "a0/runtimes/simpleloop/policy/simpleloop.inject.json",
        }
    if policy.get("task") == "maxcut":
        # T1's F_r: the scalar is E*'s integer objective, which the harness
        # authors (a0/a1/eval_service.py) and the runtime consumes. The frozen
        # declaration is this policy file itself, so a change of what the search
        # maximizes changes the digest the score events carry.
        path = Path(policy_path) if policy_path else POLICY_PATH
        return {
            "name": "F_r = cut_edges(E*_harness_outcome)",
            "version": "v1",
            "applies": "scalar",
            "spec_hash": canonical_file_digest(path),
            "declared_in": (
                f"{path} + a0/tasks/maxcut/INTERFACE.md#5 (cut_edges is the only "
                "authoritative value; cut_fraction is display only)"
            ),
        }
    if not FR_SCALAR_PATH.exists():
        raise PolicyError(f"frozen F_r declaration missing: {FR_SCALAR_PATH}")
    return {
        "name": "F_r = scalar(E*)",
        "version": "v1",
        "applies": "scalar",
        "spec_hash": canonical_file_digest(FR_SCALAR_PATH),
        "declared_in": (
            "a0/contract/fr/scalar.json + "
            "a0/runtimes/simpleloop/policy/simpleloop.policy.json#scalarization"
        ),
    }
