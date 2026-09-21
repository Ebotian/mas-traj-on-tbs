#!/usr/bin/env python3
"""`Eligible(r; T)`: the declared predicate from a runtime's qualification vector `Q_r`.

Why this file changed (external review, decision D2)
----------------------------------------------------
The first version of this predicate shipped two *dimensionless* threshold vectors, `T_strict` and
`T_literal`, that differed only in how lenient two of the five rules were. An independent verifier
showed the lenient one admits runtimes whose A0.2 end-to-end round is `UNPROVEN` and whose closure
record is `NOT RECONCILED` -- i.e. the lenient vector re-introduced, inside the predicate, exactly
the dilution the predicate was built to prevent. "Is `T_strict` or `T_literal`?" was filed as a
*decision*; D2 is that it was the wrong question.

D2 replaces the pair with one substantive predicate and one explicitly-scoped exploratory vector:

    T_A1(r)  requires  A0.1 measured sufficient
                       A0.1 harness-attested
                       A0.2 mechanism PASS
                       A0.2 bridge PASS
                       Closure PASS
                       MRC FROZEN

    r not-in R_A1^main  while any of those is unmet.

Two properties of that statement are load-bearing and are implemented literally here:

* **Exclusion is not a verdict on the runtime.** `R_A1^main` is the set of runtimes whose *evidence*
  is complete; a runtime missing one component is excluded from the main arm and nothing else. The
  predicate therefore reports `failed_rules` (what evidence is missing) rather than a grade.
* **`T_exploratory` is renamed, not softened into a synonym.** It is the old lenient vector, kept
  because integration/pilot/debug work on a half-instrumented runtime is legitimate, but it is
  scoped by data: `may_be_used_for` names the consumers that are allowed to read `eligible=true` from
  it, and it is *not* `T_A1`. A script that six months from now reads `eligible=true` off the default
  vector gets `T_A1`'s answer, which is the only answer an A1 statistic may consume.

`Eligible` is a different object from the `|R_1| >= 1` candidate screen (plan:490, `a0/STATUS.md`
§2 decision 7). The screen answers "may the study continue at all?"; `Eligible(r)` answers "may THIS
runtime's numbers be used in an A1 statistic?". The screen can pass while `R_A1^main` is empty.

The rules, as data
------------------
`RULES` below is the single source of truth: `evaluate_rules` is a generic interpreter over it, the
stored `qualification.json` carries a byte-identical copy of it, and `verify_qualification.py`
asserts the two agree. Every rule is a total function of `Q_r` x thresholds and **fails closed**: a
component that is absent, empty, or outside its declared domain makes its rule false; nothing is
inferred from a sibling's value and no rule defaults to true.

    R0_coverage          measured + adapted == total, total > 0, state in {PASS, PARTIAL}
    R1_measure_floor     measured >= required_measured(T, total)
    R2_adapted_declared  adapted == 0 or all_declared_synthetic
    R3_a0_1_attested     a0_1_attested.value in T.attested_allowed
    R4_a0_2_mechanism    a0_2_mechanism.value in T.mechanism_allowed
    R5_a0_2_bridge       a0_2_bridge.value in T.bridge_allowed
    R6_closure           closure.value in T.closure_allowed
    R7_mrc               mrc.value in T.mrc_allowed

    python3 eligibility.py --qualification qualification.json   # evaluate every runtime
    python3 eligibility.py --self-test                          # exercise the rules on fixtures
    python3 eligibility.py --main-arm                           # print R_A1^main only
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUALIFICATION = HERE / "qualification.json"

PREDICATE_VERSION = "a0.eligibility/v2"

# The vector's components, in report order. `build_qualification.py` fills every one of them for
# every runtime; an absent component is a rule failure, never a skipped check.
COMPONENTS = (
    "a0_1_measured",
    "a0_1_adapted",
    "a0_1_attested",
    "a0_2_mechanism",
    "a0_2_bridge",
    "closure",
    "mrc",
)

STATE_DOMAIN = ("PASS", "PARTIAL", "FAIL", "PENDING", "BLOCKED")
ATTESTED_DOMAIN = ("PASS", "FAIL", "UNPROVEN")
MECHANISM_DOMAIN = ("PASS", "FAIL", "UNPROVEN")
BRIDGE_DOMAIN = ("PASS", "ATTEMPTED", "UNPROVEN", "NONE")
CLOSURE_DOMAIN = ("CLOSED", "CONDITIONAL", "OPEN", "UNPROVEN")
MRC_DOMAIN = ("FROZEN", "PRESENT_UNFROZEN", "ABSENT")

MAIN_ARM_VECTOR = "T_A1"
EXPLORATORY_VECTOR = "T_exploratory"

THRESHOLD_VECTORS = {
    MAIN_ARM_VECTOR: {
        "role": "main arm",
        "scope": (
            "the vector that `Eligible(r)` means. `eligible=true` here is the licence to put this "
            "runtime's numbers into an A1 statistic."
        ),
        "may_be_used_for": ["a1_main_arm", "a0_freeze"],
        "measured_floor": {"kind": "fraction", "value": 1.0},
        "attested_allowed": ["PASS"],
        "mechanism_allowed": ["PASS"],
        "bridge_allowed": ["PASS"],
        "closure_allowed": ["CLOSED"],
        "mrc_allowed": ["FROZEN"],
        "rationale": (
            "every clause names evidence this study is able to produce, and each was chosen because "
            "D2 asks for it: the runtime's OWN evaluator interface must have measured every row of "
            "C* (fraction 1.0, so an adapted row is not a measurement); the A0.1 row must carry a "
            "HARNESS attestation of the bytes the runtime executed (behaviour alone cannot establish "
            "implementation identity -- see the observational-equivalence mutant); A0.2 must be "
            "proven at mechanism level AND exercised in the runtime's own real campaign (the "
            "bridge); closure must be probe-proven, not reachable-by-a-posture; and the model route "
            "must be frozen."
        ),
    },
    EXPLORATORY_VECTOR: {
        "role": "exploratory",
        "scope": (
            "integration / pilot / debug ONLY. This is the renamed former `T_literal` and it keeps "
            "that vector's leniency on purpose: it exists so a half-instrumented runtime can be "
            "driven while its evidence is still being produced. It is NOT a weaker main arm."
        ),
        "may_be_used_for": ["pilot", "integration", "debug"],
        "must_not_be_used_for": [
            "a1_main_arm",
            "a0_freeze",
            "any statistic whose delta is reported as a study result",
        ],
        "measured_floor": {"kind": "rows", "value": 1},
        "attested_allowed": ["PASS", "UNPROVEN"],
        "mechanism_allowed": ["PASS"],
        "bridge_allowed": ["PASS", "ATTEMPTED"],
        "closure_allowed": ["CLOSED", "CONDITIONAL"],
        "mrc_allowed": ["FROZEN", "PRESENT_UNFROZEN"],
        "fail_is_never_softened": (
            "UNPROVEN is tolerated here (the evidence has not been produced yet); FAIL is not. An "
            "axis that was decided AGAINST the runtime -- a contradicting attestation, an open "
            "closure, an unproven mechanism -- stays decided under every vector. Leniency is about "
            "missing evidence, never about rejected evidence."
        ),
        "rationale": (
            "any native measurement counts (>= 1 row), the A0.2 mechanism check is still required "
            "because a pilot on an unproven selection mechanism measures nothing, an ATTEMPTED round "
            "is enough to exercise the plumbing, a closure that is reachable by a named posture is "
            "enough to run a pilot in, and the route may still be in flux."
        ),
    },
}

DEFAULT_VECTOR = MAIN_ARM_VECTOR

RULES = [
    {
        "id": "R0_coverage",
        "component": "a0_1_measured",
        "field": "state",
        "expr": (
            "a0_1_measured.total > 0 and "
            "a0_1_measured.measured + a0_1_adapted.adapted == a0_1_measured.total and "
            "a0_1_measured.state in {'PASS','PARTIAL'}"
        ),
        "what": "every row of C* is accounted for, nothing failed, and the split is not empty",
        "fail_closed": "a missing row, a zero total, a FAIL state or an absent component is not eligible",
    },
    {
        "id": "R1_measure_floor",
        "component": "a0_1_measured",
        "field": "measured",
        "expr": "a0_1_measured.measured >= required_measured(thresholds, a0_1_measured.total)",
        "what": (
            "enough rows were measured by the RUNTIME'S OWN evaluator interface (C_measure), not "
            "merely supplied by the adapter (C_adapt). `T_A1` requires all of them; an adapted row is "
            "evidence for C_adapt and never for C_measure"
        ),
        "fail_closed": "an absent measured/total counts as 0 and fails",
    },
    {
        "id": "R2_adapted_declared",
        "component": "a0_1_adapted",
        "field": "all_declared_synthetic",
        "expr": "a0_1_adapted.adapted == 0 or a0_1_adapted.all_declared_synthetic == true",
        "what": "no row was accepted on an undeclared non-fresh number",
        "fail_closed": "an absent adapted count reads as 0 only when the component itself is present",
    },
    {
        "id": "R3_a0_1_attested",
        "component": "a0_1_attested",
        "field": "value",
        "expr": "a0_1_attested.value in thresholds.attested_allowed",
        "what": (
            "the harness that owns the reference value also holds a submitted attestation of the "
            "bytes the runtime executed, and the identity check on those bytes passed. This is the "
            "clause D3 adds: behaviour alone cannot establish implementation identity, so identity "
            "must be a harness measurement and its omission must fail"
        ),
        "fail_closed": (
            "no record, or a record that omits the executed-bytes identity or the identity verdict, "
            "reads as UNPROVEN and fails every vector except one that explicitly allows UNPROVEN"
        ),
    },
    {
        "id": "R4_a0_2_mechanism",
        "component": "a0_2_mechanism",
        "field": "value",
        "expr": "a0_2_mechanism.value in thresholds.mechanism_allowed",
        "what": "the runtime consumes scores per its claimed selection semantics (mechanism level)",
        "fail_closed": "UNPROVEN -- and an absent component -- fails",
    },
    {
        "id": "R5_a0_2_bridge",
        "component": "a0_2_bridge",
        "field": "value",
        "expr": "a0_2_bridge.value in thresholds.bridge_allowed",
        "what": (
            "the same score->selection path was exercised inside the runtime's OWN real campaign "
            "(not only in a seam scenario): the frozen evaluator's score reached the runtime's "
            "selection state and moved the search"
        ),
        "fail_closed": "an attempted-but-uncompleted round is ATTEMPTED, never PASS",
    },
    {
        "id": "R6_closure",
        "component": "closure",
        "field": "value",
        "expr": "closure.value in thresholds.closure_allowed",
        "what": "no autonomous external acquisition in the posture the runtime would run under",
        "fail_closed": "an unreconciled closure record is CONDITIONAL at best and OPEN if no mechanism was probed",
    },
    {
        "id": "R7_mrc",
        "component": "mrc",
        "field": "value",
        "expr": "mrc.value in thresholds.mrc_allowed",
        "what": (
            "the model route (MRC*) is frozen: the covering declaration validates against the "
            "external route registry, so two A1 arms can be asserted to be on the same declared route"
        ),
        "fail_closed": "an unvalidated or absent declaration is ABSENT/PRESENT_UNFROZEN and fails T_A1",
    },
]

RULES_BY_ID = {rule["id"]: rule for rule in RULES}


class VectorError(ValueError):
    pass


def get_vector(name: str) -> dict:
    try:
        return THRESHOLD_VECTORS[name]
    except KeyError:
        raise VectorError(
            f"unknown threshold vector {name!r}; declared: {sorted(THRESHOLD_VECTORS)}"
        ) from None


def required_measured(thresholds: dict, total: int) -> int:
    floor = thresholds["measured_floor"]
    if floor["kind"] == "rows":
        return int(floor["value"])
    if floor["kind"] == "fraction":
        return int(math.ceil(float(floor["value"]) * max(0, int(total))))
    raise VectorError(f"measured_floor.kind {floor['kind']!r} is not declared")


# --------------------------------------------------------------------------------------
# component access. Every accessor is total: absent or malformed components read as the
# value that fails the rule, never as an exception and never as a default-true.


def component(q_r: dict, name: str) -> dict:
    comp = (q_r or {}).get(name)
    return comp if isinstance(comp, dict) else {}


def value_of(q_r: dict, name: str):
    return component(q_r, name).get("value")


def int_of(q_r: dict, name: str, key: str) -> int:
    try:
        return int(component(q_r, name).get(key) or 0)
    except (TypeError, ValueError):
        return 0


def evaluate_rules(q_r: dict, thresholds: dict) -> dict:
    """Total function Q_r x thresholds -> {rule_id: bool}. No I/O, no globals besides RULES."""
    total = int_of(q_r, "a0_1_measured", "total")
    measured = int_of(q_r, "a0_1_measured", "measured")
    adapted = int_of(q_r, "a0_1_adapted", "adapted")
    need = required_measured(thresholds, total)

    return {
        "R0_coverage": (
            total > 0
            and measured + adapted == total
            and value_of(q_r, "a0_1_measured") is not None
            and component(q_r, "a0_1_measured").get("state") in ("PASS", "PARTIAL")
        ),
        "R1_measure_floor": measured >= need,
        "R2_adapted_declared": (
            component(q_r, "a0_1_adapted").get("value") is not None
            and (adapted == 0 or bool(component(q_r, "a0_1_adapted").get("all_declared_synthetic")))
        ),
        "R3_a0_1_attested": value_of(q_r, "a0_1_attested") in thresholds["attested_allowed"],
        "R4_a0_2_mechanism": value_of(q_r, "a0_2_mechanism") in thresholds["mechanism_allowed"],
        "R5_a0_2_bridge": value_of(q_r, "a0_2_bridge") in thresholds["bridge_allowed"],
        "R6_closure": value_of(q_r, "closure") in thresholds["closure_allowed"],
        "R7_mrc": value_of(q_r, "mrc") in thresholds["mrc_allowed"],
    }


def eligible(q_r: dict, vector: str = DEFAULT_VECTOR) -> dict:
    """`Eligible(r; T)` for one runtime. The result is the conjunction of every rule; nothing is averaged."""
    thresholds = get_vector(vector)
    results = evaluate_rules(q_r, thresholds)
    failed = [rule["id"] for rule in RULES if not results[rule["id"]]]
    total = int_of(q_r, "a0_1_measured", "total")
    return {
        "predicate_version": PREDICATE_VERSION,
        "vector": vector,
        "vector_role": thresholds["role"],
        "eligible": not failed,
        "rules": results,
        "failed_rules": failed,
        "required_measured": required_measured(thresholds, total),
        "measured": int_of(q_r, "a0_1_measured", "measured"),
        "total": total,
        "missing_components": [
            name for name in COMPONENTS if component(q_r, name).get("value") is None
        ],
        "reason": "all rules satisfied" if not failed else "not eligible: " + ", ".join(failed),
        "component_values": {name: value_of(q_r, name) for name in COMPONENTS},
    }


def evaluate_all(qualification: dict, vector: str = DEFAULT_VECTOR) -> dict:
    return {
        runtime: eligible(entry["Q_r"], vector)
        for runtime, entry in qualification["runtimes"].items()
    }


def eligible_set(qualification: dict, vector: str = DEFAULT_VECTOR) -> list:
    return sorted(
        runtime
        for runtime, verdict in evaluate_all(qualification, vector).items()
        if verdict["eligible"]
    )


def key_metrics(qualification: dict) -> dict:
    """The two sets the study quotes: R_A1^main and R_exploratory."""
    return {
        "R_A1_main": eligible_set(qualification, MAIN_ARM_VECTOR),
        "R_exploratory": eligible_set(qualification, EXPLORATORY_VECTOR),
    }


# --------------------------------------------------------------------------------------
# self-test: the rules must be exactly the declared ones on hand-built vectors


def _q(**kw) -> dict:
    base = {
        "a0_1_measured": {"value": "14/14", "measured": 14, "total": 14, "state": "PASS"},
        "a0_1_adapted": {"value": "0/14", "adapted": 0, "total": 14, "all_declared_synthetic": True},
        "a0_1_attested": {"value": "PASS"},
        "a0_2_mechanism": {"value": "PASS"},
        "a0_2_bridge": {"value": "PASS"},
        "closure": {"value": "CLOSED"},
        "mrc": {"value": "FROZEN"},
    }
    for name, value in kw.items():
        if name == "drop":
            for dropped in value:
                base.pop(dropped, None)
            continue
        if isinstance(value, dict):
            base[name].update(value)
        else:
            base[name]["value"] = value
    return base


SELF_TEST_CASES = [
    ("a fully-evidenced Q_r is eligible under both vectors", _q(),
     {"T_A1": True, "T_exploratory": True}),
    (
        "EvE-shaped: 5/14 measured, ATTEMPTED bridge, CONDITIONAL closure, no attestation",
        _q(
            a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 9, "all_declared_synthetic": True},
            a0_1_attested="UNPROVEN",
            a0_2_bridge="ATTEMPTED",
            closure="CONDITIONAL",
        ),
        {"T_A1": False, "T_exploratory": True},
    ),
    (
        "one adapted row is enough to leave T_A1",
        _q(
            a0_1_measured={"measured": 13, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 1, "total": 14, "all_declared_synthetic": True},
        ),
        {"T_A1": False, "T_exploratory": True},
    ),
    (
        "an undeclared adapted row fails R2 under every vector",
        _q(
            a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 9, "all_declared_synthetic": False},
        ),
        {"T_A1": False, "T_exploratory": False},
    ),
    (
        "a missing row fails R0",
        _q(a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"}, a0_1_adapted={"adapted": 0}),
        {"T_A1": False, "T_exploratory": False},
    ),
    ("a FAIL state is never eligible", _q(a0_1_measured={"state": "FAIL"}),
     {"T_A1": False, "T_exploratory": False}),
    ("closure CONDITIONAL is the only thing wrong", _q(closure="CONDITIONAL"),
     {"T_A1": False, "T_exploratory": True}),
    ("closure OPEN is never eligible", _q(closure="OPEN"),
     {"T_A1": False, "T_exploratory": False}),
    ("an unconsumed A0.2 mechanism is never eligible", _q(a0_2_mechanism="FAIL"),
     {"T_A1": False, "T_exploratory": False}),
    # ------------------------------------------------------------------ the D2 clauses
    (
        "D2: a perfect behavioural row with NO harness attestation is not in the main arm",
        _q(a0_1_attested="UNPROVEN"),
        {"T_A1": False, "T_exploratory": True},
    ),
    (
        "D3 fail-closed: an attestation whose identity verdict failed is FAIL, not UNPROVEN",
        _q(a0_1_attested="FAIL"),
        {"T_A1": False, "T_exploratory": False},
    ),
    (
        "D2: an uncompleted real campaign (ATTEMPTED bridge) is out of the main arm",
        _q(a0_2_bridge="ATTEMPTED"),
        {"T_A1": False, "T_exploratory": True},
    ),
    ("a bridge that was never attempted is out of every vector", _q(a0_2_bridge="NONE"),
     {"T_A1": False, "T_exploratory": False}),
    ("D2: an unfrozen model route is out of the main arm", _q(mrc="PRESENT_UNFROZEN"),
     {"T_A1": False, "T_exploratory": True}),
    ("an absent model route is out of every vector", _q(mrc="ABSENT"),
     {"T_A1": False, "T_exploratory": False}),
    # ------------------------------------------------------------------ fail-closed on omission
    ("an omitted component fails closed under both vectors",
     _q(drop=["a0_1_attested", "mrc"]), {"T_A1": False, "T_exploratory": False}),
    ("an omitted a0_2_mechanism fails closed under both vectors",
     _q(drop=["a0_2_mechanism"]), {"T_A1": False, "T_exploratory": False}),
    ("an empty Q_r fails closed", {}, {"T_A1": False, "T_exploratory": False}),
]


def self_test() -> int:
    problems = []
    for why, q_r, want in SELF_TEST_CASES:
        for vector, want_eligible in want.items():
            got = eligible(q_r, vector)
            if bool(got["eligible"]) != want_eligible:
                problems.append(
                    f"{why} [{vector}]: eligible={got['eligible']} != {want_eligible} "
                    f"(failed {got['failed_rules']})"
                )
    # the floor arithmetic is the non-dilution rule, so check it directly
    if required_measured(get_vector("T_A1"), 14) != 14:
        problems.append("T_A1 floor over 14 rows is not 14")
    if required_measured(get_vector("T_exploratory"), 14) != 1:
        problems.append("T_exploratory floor over 14 rows is not 1")
    # every rule names a declared component and a declared vector key it reads
    for rule in RULES:
        if rule["component"] not in COMPONENTS:
            problems.append(f"{rule['id']}: component {rule['component']!r} is not declared")
        if not rule.get("expr") or not rule.get("what") or not rule.get("fail_closed"):
            problems.append(f"{rule['id']}: rule data is incomplete")
    for vector, thresholds in THRESHOLD_VECTORS.items():
        for key in ("role", "scope", "may_be_used_for", "measured_floor", "rationale",
                    "attested_allowed", "mechanism_allowed", "bridge_allowed",
                    "closure_allowed", "mrc_allowed"):
            if key not in thresholds:
                problems.append(f"{vector}: threshold data is missing {key!r}")
    if THRESHOLD_VECTORS[EXPLORATORY_VECTOR].get("must_not_be_used_for") is None:
        problems.append("T_exploratory does not declare what it must not be used for")
    # no vector may soften an explicit FAIL
    for vector, thresholds in THRESHOLD_VECTORS.items():
        for key, allowed in thresholds.items():
            if key.endswith("_allowed") and "FAIL" in allowed:
                problems.append(f"{vector}.{key} admits FAIL: a decided rejection must not be softened")
    # a self-referential guard: T_exploratory must not become the default
    if DEFAULT_VECTOR != MAIN_ARM_VECTOR:
        problems.append("the default vector is not T_A1")

    print(
        f"predicate {PREDICATE_VERSION}, {len(SELF_TEST_CASES)} cases x "
        f"{len(THRESHOLD_VECTORS)} threshold vectors, {len(RULES)} rules"
    )
    for problem in problems:
        print(f"  ! {problem}")
    print("self-test:", "ok" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="eligibility.py", description=__doc__.splitlines()[0])
    parser.add_argument("--qualification", default=str(QUALIFICATION))
    parser.add_argument("--vector", default=None, help="evaluate one vector (default: every declared vector)")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--main-arm", action="store_true", help="print R_A1^main and what blocks membership")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    qualification = json.loads(Path(args.qualification).read_text())
    if args.main_arm:
        report = {
            "predicate_version": PREDICATE_VERSION,
            "vector": MAIN_ARM_VECTOR,
            **key_metrics(qualification),
            "per_runtime": {
                runtime: eligible(entry["Q_r"], MAIN_ARM_VECTOR)
                for runtime, entry in qualification["runtimes"].items()
            },
        }
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        print(f"{PREDICATE_VERSION}: R_A1^main ({MAIN_ARM_VECTOR})")
        print()
        for runtime, verdict in report["per_runtime"].items():
            mark = "IN " if verdict["eligible"] else "out"
            blockers = ", ".join(verdict["failed_rules"]) or "-"
            print(f"  [{mark}] {runtime:<11} {blockers}")
        print()
        print(f"R_A1^main = {report['R_A1_main'] or '{} (empty)'}")
        return 0

    vectors = [args.vector] if args.vector else list(THRESHOLD_VECTORS)
    print(f"{PREDICATE_VERSION}: Eligible(r; T) over {len(qualification['runtimes'])} runtimes")
    print()
    header = f"{'runtime':<12}" + "".join(f"{v:<16}" for v in vectors)
    print(header)
    for runtime, entry in qualification["runtimes"].items():
        cells = []
        for vector in vectors:
            verdict = eligible(entry["Q_r"], vector)
            cells.append("ELIGIBLE" if verdict["eligible"] else "not")
        print(f"{runtime:<12}" + "".join(f"{c:<16}" for c in cells))
    print()
    for vector in vectors:
        detail = evaluate_all(qualification, vector)
        names = sorted(r for r, v in detail.items() if v["eligible"])
        print(f"{vector} ({THRESHOLD_VECTORS[vector]['role']}): |Eligible| = {len(names)}: {names or 'none'}")
        for runtime, verdict in detail.items():
            if not verdict["eligible"]:
                print(f"    {runtime}: {verdict['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
