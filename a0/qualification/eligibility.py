#!/usr/bin/env python3
"""`Eligible(r)`: the declared predicate from a runtime's qualification vector `Q_r` to eligible/not.

Why this exists (external review, points 2 and 8)
-------------------------------------------------
A single global `A0 PASS` is the wrong output for this study. `A0` has to be able to say
"runtime X is qualified for A1, runtime Y is not, and Y's partial result is not diluted by X's
full one". The review therefore asked for

    Q_r = (A0.1_measured, A0.1_adapted, A0.2_mechanism, A0.2_E2E, Closure)
    Eligible(r) = f(Q_r)

`Eligible(r)` is a **different object from the `|R_1| >= 1` screen**. `R_1 = {r : A0.1_r and
A0.2_r}` and `|R_1| >= 1` answers "may the study continue at all?" (`plan:490`, and `a0/STATUS.md`
§2 decision 7: A0 is a candidate screen, not a collective gate). `Eligible(r)` answers "may THIS
runtime's numbers be used in an A1 statistic?". The screen can pass while no runtime is
`Eligible()`, and that is not a contradiction.

The rules (explicit, not prose)
-------------------------------
`Eligible(r; T) = R0 and R1 and R2 and R3 and R4 and R5`, where `T` is a declared threshold
vector and every rule is a total function of `Q_r`:

  R0 coverage          measured + adapted == total  and  state in {PASS, PARTIAL}
  R1 measure_floor     measured >= required_measured(T, total)
                         required_measured = T.measured_floor.value            if kind == "rows"
                                           = ceil(T.measured_floor.value*total)  if kind == "fraction"
  R2 adapted_declared  adapted == 0  or  adapted_all_declared_synthetic == True
  R3 a0_2_mechanism    a0_2_mechanism.value == "PASS"
  R4 a0_2_e2e          a0_2_e2e.value in T.e2e_allowed
  R5 closure           closure.value in T.closure_allowed

R0/R2 are about the *shape* of the evidence (nothing missing, nothing undeclared). R1 is the
non-dilution rule the review asked for: a runtime that could not measure `E*`'s outcome algebra on
some of `C*` has not demonstrated A0.1 for those rows, so the floor on how many rows were actually
measured is a threshold, not an afterthought. R3-R5 are the other three components of `Q_r`.

Two threshold vectors are declared. **Choosing between them is the user's decision** (it is
external-review point 2: "is `(passed, measured, total)` the right weakening, or should EvE's A0.1
be FAIL?"), so both are evaluated and reported rather than one being silently assumed:

  T_strict   measured_floor fraction 1.0,  e2e {COMPLETE},                 closure {CLOSED}
             the literal reading: a runtime qualifies only if its own evaluator interface measured
             every row, it completed a real round, and where the driver ships it is probe-proven
             closed. `a0/STATUS.md` §3.3 states the boundary as "mechanism-level verified" vs
             "end-to-end unverified" and §5.5 as closure-by-topology, so this vector is the one
             that does not spend those caveats.

  T_literal  measured_floor rows 1,        e2e {COMPLETE, PLANNING_ONLY, ATTEMPTED},
             closure {CLOSED, CONDITIONAL}
             the reading under which the study's existing wording ("A0.1 = PASS 5/14 measured",
             A0.2 mechanism-level, closure conditional-on-a-named-posture) is already enough.

    python3 eligibility.py --qualification qualification.json   # evaluate Q_r from the file
    python3 eligibility.py --self-test                          # exercise the rules on fixtures
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUALIFICATION = HERE / "qualification.json"

PREDICATE_VERSION = "a0.eligibility/v1"

COMPONENTS = ("a0_1_measured", "a0_1_adapted", "a0_2_mechanism", "a0_2_e2e", "closure")

STATE_DOMAIN = ("PASS", "PARTIAL", "FAIL", "PENDING", "BLOCKED")
MECHANISM_DOMAIN = ("PASS", "FAIL", "UNPROVEN")
E2E_DOMAIN = ("COMPLETE", "PLANNING_ONLY", "ATTEMPTED", "NONE", "UNPROVEN")
CLOSURE_DOMAIN = ("CLOSED", "CONDITIONAL", "OPEN", "UNPROVEN")

THRESHOLD_VECTORS = {
    "T_strict": {
        "measured_floor": {"kind": "fraction", "value": 1.0},
        "e2e_allowed": ["COMPLETE"],
        "closure_allowed": ["CLOSED"],
        "rationale": (
            "a runtime qualifies only if its own evaluator interface measured every row of C*, it "
            "completed a real model-lane round, and its shipped posture is probe-proven closed"
        ),
    },
    "T_literal": {
        "measured_floor": {"kind": "rows", "value": 1},
        "e2e_allowed": ["COMPLETE", "PLANNING_ONLY", "ATTEMPTED"],
        "closure_allowed": ["CLOSED", "CONDITIONAL"],
        "rationale": (
            "the reading under which the study's existing wording is already sufficient: any "
            "native measurement counts, a mechanism-level A0.2 counts, a closure that is reachable "
            "by a named posture counts"
        ),
    },
}

DEFAULT_VECTOR = "T_strict"

RULES = [
    {
        "id": "R0_coverage",
        "expr": "a0_1_measured.measured + a0_1_adapted.adapted == a0_1_measured.total "
                "and a0_1_measured.state in {'PASS','PARTIAL'}",
        "what": "every row of C* is accounted for and nothing failed",
    },
    {
        "id": "R1_measure_floor",
        "expr": "a0_1_measured.measured >= required_measured(thresholds, a0_1_measured.total)",
        "what": "enough rows were measured by the RUNTIME'S OWN evaluator interface (C_measure), "
                "not merely supplied by the adapter (C_adapt)",
    },
    {
        "id": "R2_adapted_declared",
        "expr": "a0_1_adapted.adapted == 0 or a0_1_adapted.all_declared_synthetic",
        "what": "no row was accepted on an undeclared non-fresh number",
    },
    {
        "id": "R3_a0_2_mechanism",
        "expr": "a0_2_mechanism.value == 'PASS'",
        "what": "the runtime consumes scores per its claimed selection semantics (mechanism level)",
    },
    {
        "id": "R4_a0_2_e2e",
        "expr": "a0_2_e2e.value in thresholds.e2e_allowed",
        "what": "a real model-lane round through the runtime's own loop, where the threshold asks "
                "for one",
    },
    {
        "id": "R5_closure",
        "expr": "closure.value in thresholds.closure_allowed",
        "what": "no autonomous external acquisition in the posture the runtime would run under",
    },
]


class VectorError(ValueError):
    pass


def get_vector(name: str) -> dict:
    try:
        return THRESHOLD_VECTORS[name]
    except KeyError:
        raise VectorError(f"unknown threshold vector {name!r}; declared: {sorted(THRESHOLD_VECTORS)}") from None


def required_measured(thresholds: dict, total: int) -> int:
    floor = thresholds["measured_floor"]
    if floor["kind"] == "rows":
        return int(floor["value"])
    if floor["kind"] == "fraction":
        return int(math.ceil(float(floor["value"]) * total))
    raise VectorError(f"measured_floor.kind {floor['kind']!r} is not declared")


def _component(q_r: dict, name: str) -> dict:
    comp = q_r.get(name)
    if not isinstance(comp, dict) or comp.get("value") is None:
        raise VectorError(f"Q_r is missing component {name!r}")
    return comp


def evaluate_rules(q_r: dict, thresholds: dict) -> dict:
    """Total function Q_r x thresholds -> {rule_id: bool}. No I/O, no globals besides RULES."""
    measured = _component(q_r, "a0_1_measured")
    adapted = _component(q_r, "a0_1_adapted")
    mechanism = _component(q_r, "a0_2_mechanism")
    e2e = _component(q_r, "a0_2_e2e")
    closure = _component(q_r, "closure")

    total = int(measured.get("total") or 0)
    n_measured = int(measured.get("measured") or 0)
    n_adapted = int(adapted.get("adapted") or 0)
    need = required_measured(thresholds, total)

    return {
        "R0_coverage": (
            measured.get("state") in ("PASS", "PARTIAL")
            and n_measured + n_adapted == total
            and total > 0
        ),
        "R1_measure_floor": n_measured >= need,
        "R2_adapted_declared": n_adapted == 0 or bool(adapted.get("all_declared_synthetic")),
        "R3_a0_2_mechanism": mechanism.get("value") == "PASS",
        "R4_a0_2_e2e": e2e.get("value") in thresholds["e2e_allowed"],
        "R5_closure": closure.get("value") in thresholds["closure_allowed"],
    }


def eligible(q_r: dict, vector: str = DEFAULT_VECTOR) -> dict:
    """Eligible(r) for one runtime. `eligible` is the conjunction of every rule; nothing is averaged."""
    thresholds = get_vector(vector)
    results = evaluate_rules(q_r, thresholds)
    failed = [rule_id for rule_id in (r["id"] for r in RULES) if not results[rule_id]]
    measured = _component(q_r, "a0_1_measured")
    return {
        "predicate_version": PREDICATE_VERSION,
        "vector": vector,
        "eligible": not failed,
        "rules": results,
        "failed_rules": failed,
        "required_measured": required_measured(thresholds, int(measured.get("total") or 0)),
        "reason": (
            "all rules satisfied"
            if not failed
            else "not eligible: " + ", ".join(failed)
        ),
    }


def evaluate_all(qualification: dict, vector: str = DEFAULT_VECTOR) -> dict:
    return {
        runtime: eligible(entry["Q_r"], vector)
        for runtime, entry in qualification["runtimes"].items()
    }


def eligible_set(qualification: dict, vector: str = DEFAULT_VECTOR) -> list:
    return sorted(
        runtime for runtime, verdict in evaluate_all(qualification, vector).items() if verdict["eligible"]
    )


# --------------------------------------------------------------------------------------
# self-test: the rules must be exactly the declared ones on hand-built vectors


def _q(**kw) -> dict:
    base = {
        "a0_1_measured": {"value": "14/14", "measured": 14, "total": 14, "state": "PASS"},
        "a0_1_adapted": {"value": "0/14", "adapted": 0, "total": 14, "all_declared_synthetic": True},
        "a0_2_mechanism": {"value": "PASS"},
        "a0_2_e2e": {"value": "COMPLETE"},
        "closure": {"value": "CLOSED"},
    }
    for name, value in kw.items():
        if isinstance(value, dict):
            base[name].update(value)
        else:
            base[name]["value"] = value
    return base


SELF_TEST_CASES = [
    ("full pass is eligible under both vectors", _q(), {"T_strict": True, "T_literal": True}),
    (
        "EvE-shaped: 5/14 measured, ATTEMPTED e2e, CONDITIONAL closure",
        _q(
            a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 9, "all_declared_synthetic": True},
            a0_2_e2e="ATTEMPTED",
            closure="CONDITIONAL",
        ),
        {"T_strict": False, "T_literal": True},
    ),
    (
        "one adapted row is enough to leave T_strict",
        _q(
            a0_1_measured={"measured": 13, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 1, "total": 14, "all_declared_synthetic": True},
        ),
        {"T_strict": False, "T_literal": True},
    ),
    (
        "an undeclared adapted row fails R2 under every vector",
        _q(
            a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"},
            a0_1_adapted={"adapted": 9, "all_declared_synthetic": False},
        ),
        {"T_strict": False, "T_literal": False},
    ),
    (
        "a missing row fails R0",
        _q(a0_1_measured={"measured": 5, "total": 14, "state": "PARTIAL"}, a0_1_adapted={"adapted": 0}),
        {"T_strict": False, "T_literal": False},
    ),
    (
        "a FAIL state is never eligible",
        _q(a0_1_measured={"measured": 14, "total": 14, "state": "FAIL"}),
        {"T_strict": False, "T_literal": False},
    ),
    (
        "closure CONDITIONAL is the only thing wrong",
        _q(closure="CONDITIONAL"),
        {"T_strict": False, "T_literal": True},
    ),
    (
        "closure OPEN is never eligible",
        _q(closure="OPEN"),
        {"T_strict": False, "T_literal": False},
    ),
    (
        "an unconsumed A0.2 mechanism is never eligible",
        _q(a0_2_mechanism="FAIL"),
        {"T_strict": False, "T_literal": False},
    ),
    (
        "mechanism-level A0.2 with no completed round passes only T_literal",
        _q(a0_2_e2e="PLANNING_ONLY"),
        {"T_strict": False, "T_literal": True},
    ),
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
    if required_measured(get_vector("T_strict"), 14) != 14:
        problems.append("T_strict floor over 14 rows is not 14")
    if required_measured(get_vector("T_literal"), 14) != 1:
        problems.append("T_literal floor over 14 rows is not 1")
    for why, q_r, want in SELF_TEST_CASES:
        if want.get("T_literal") and not all(
            isinstance(q_r[c], dict) and q_r[c].get("value") is not None for c in COMPONENTS
        ):
            problems.append(f"{why}: fixture is not a total Q_r")

    print(f"predicate {PREDICATE_VERSION}, {len(SELF_TEST_CASES)} cases x "
          f"{len(THRESHOLD_VECTORS)} threshold vectors")
    for problem in problems:
        print(f"  ! {problem}")
    print("self-test:", "ok" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="eligibility.py", description=__doc__.splitlines()[0])
    parser.add_argument("--qualification", default=str(QUALIFICATION))
    parser.add_argument("--vector", default=None, help="evaluate one vector (default: every declared vector)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    qualification = json.loads(Path(args.qualification).read_text())
    vectors = [args.vector] if args.vector else list(qualification.get("threshold_vectors") or THRESHOLD_VECTORS)
    print(f"{PREDICATE_VERSION}: Eligible(r; T) over {len(qualification['runtimes'])} runtimes")
    print()
    header = f"{'runtime':<12}" + "".join(f"{v:<12}" for v in vectors)
    print(header)
    for runtime, entry in qualification["runtimes"].items():
        cells = []
        for vector in vectors:
            verdict = eligible(entry["Q_r"], vector)
            cells.append("ELIGIBLE" if verdict["eligible"] else "not")
        print(f"{runtime:<12}" + "".join(f"{c:<12}" for c in cells))
    print()
    for vector in vectors:
        detail = evaluate_all(qualification, vector)
        names = sorted(r for r, v in detail.items() if v["eligible"])
        print(f"{vector}: |Eligible| = {len(names)}: {names or 'none'}")
        for runtime, verdict in detail.items():
            if not verdict["eligible"]:
                print(f"    {runtime}: {verdict['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
