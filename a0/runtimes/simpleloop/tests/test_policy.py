"""Unit tests for the frozen SimpleLoop policy (no E* invocation)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a0_adapter.policy import (
    PolicyError,
    choose,
    choose_earliest_index,
    fr_for_events,
    load_policy,
    scalar_of,
)

POLICY = load_policy()


def test_policy_declares_a_tie_break_and_a_fold():
    assert POLICY["scalarization"]["applies"] == "scalar"
    assert POLICY["scalarization"]["direction"] == "maximize"
    assert POLICY["selection"]["rule_expression"] == "argmax_{i<=t} E(c_i)"
    assert POLICY["selection"]["tie_break"].startswith("smallest candidate_id")
    assert POLICY["frozen_before_run"] is True


def test_choose_is_a_function_of_the_set():
    forward = {"a": 0.5, "b": 0.7, "c": 0.7}
    assert choose(forward)[0] == "b"
    for perm in (["c", "b", "a"], ["b", "a", "c"], ["c", "a", "b"]):
        reordered = {k: forward[k] for k in perm}
        assert choose(reordered)[0] == "b"


def test_choose_ignores_unscored_candidates():
    # A null scalar (E* status != ok) is not a low score.
    assert choose({"bad": None, "good": -1.0})[0] == "good"
    assert choose({"bad": None})[0] is None
    assert choose({})[0] is None


def test_choose_reports_the_tie_break_it_used():
    chosen, note = choose({"c10": 1.0, "c02": 1.0})
    assert chosen == "c02"
    assert note and "tie_break" in note
    assert choose({"c10": 1.0, "c02": 2.0})[1] is None


def test_rejected_earliest_index_rule_is_order_sensitive():
    forward = {"c01_good_hex": 1.0, "c03_mirror": 1.0}
    reversed_order = {"c03_mirror": 1.0, "c01_good_hex": 1.0}
    assert choose(forward)[0] == choose(reversed_order)[0] == "c01_good_hex"
    assert choose_earliest_index(forward) == "c01_good_hex"
    assert choose_earliest_index(reversed_order) == "c03_mirror"


def test_scalar_of_gates_on_status():
    assert scalar_of({"status": "ok", "fields": {"sum_radii": 2.5}}, "sum_radii") == 2.5
    assert scalar_of({"status": "invalid", "fields": {"sum_radii": None}}, "sum_radii") is None
    assert scalar_of({"status": "error", "fields": {"sum_radii": None}}, "sum_radii") is None
    assert scalar_of(None, "sum_radii") is None


def test_scalar_of_refuses_to_let_a_nominal_structure_value_become_a_score():
    outcome = {
        "status": "invalid",
        "fields": {"sum_radii": None},
        "structure": {"sum_radii": 2.4519},
    }
    assert scalar_of(outcome, "sum_radii") is None


def test_scalar_of_rejects_non_finite_and_disagreeing_objective():
    with pytest.raises(PolicyError):
        scalar_of({"status": "ok", "fields": {"sum_radii": float("nan")}}, "sum_radii")
    with pytest.raises(PolicyError):
        scalar_of(
            {"status": "ok", "objective": {"value": 3.0}, "fields": {"sum_radii": 2.0}},
            "sum_radii",
        )


def test_fr_declaration_hashes_are_distinct_and_frozen():
    scalar = fr_for_events(POLICY)
    injected = fr_for_events(POLICY, injected=True)
    assert scalar["spec_hash"] == "1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0"
    assert scalar["spec_hash"] != injected["spec_hash"]
    assert injected["declared_in"].endswith("simpleloop.inject.json")
    assert json.loads((Path(__file__).resolve().parent.parent / "policy" / "simpleloop.inject.json")
                      .read_text(encoding="utf-8"))["schema"] == "a0.fr/v1"


def test_declared_rule_and_implementation_are_the_same_rule():
    """The contract owner copies `policy/proposed.a0.contract.simpleloop.selection.json`
    into a0/contract. Pin the two ways it could silently diverge from what runs.
    """
    import itertools

    proposed = json.loads(
        (Path(__file__).resolve().parent.parent / "policy"
         / "proposed.a0.contract.simpleloop.selection.json").read_text(encoding="utf-8")
    )
    assert proposed["scalarization"] == POLICY["scalarization"]
    assert proposed["selection"] == POLICY["selection"]

    # "byte-wise comparison of the UTF-8 encoding" vs Python's code-point comparison:
    # the two orders must coincide, or the declared rule and `choose` are different rules.
    ids = ["c01_good_hex", "c03_mirror", "Z", "a", "A", "~", "_", "0", "é", "中",
           "\u00ff", "\u4e2d\u6587", "ß", "😀", "\U0010ffff", "e\u0301"]
    assert sorted(ids, key=lambda s: s.encode("utf-8")) == sorted(ids)

    # and the tie-break must be a function of the id, not of the insertion order
    for perm in itertools.permutations(["c01_good_hex", "c03_mirror", "bbb"]):
        assert choose({k: 1.0 for k in perm})[0] == "bbb"

    # selection is exact binary64: no tolerance parameter exists to absorb a gap
    assert "epsilon" not in choose.__code__.co_varnames
