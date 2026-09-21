#!/usr/bin/env python3
"""Build `qualification.json`: the per-runtime qualification vector `Q_r` and `Eligible(r)`.

Every component is derived from **existing evidence** -- `a0/conformance/report.json`,
`a0/closure/*.json`, the A0.2 artifacts and `a0/verify/verdicts.json` -- not by re-running an
experiment. Each component carries the value, the evidence path it came from, a one-line
justification, and a provenance class:

    verified_by_running   this workstream executed the thing that produced the evidence
    read_from_source      the value is read out of a stored artifact produced by another workstream
    inferred              derived by rule from other components, not directly observed

`--check` re-derives everything in memory and diffs it against the stored file, so a third party can
tell whether the file still matches its evidence without trusting this script's prose.

    python3 build_qualification.py            # write qualification.json
    python3 build_qualification.py --check    # re-derive and diff (exit 1 on drift)
    python3 build_qualification.py --stdout    # print, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

sys.path.insert(0, str(HERE))
from eligibility import (  # noqa: E402
    DEFAULT_VECTOR,
    PREDICATE_VERSION,
    RULES,
    THRESHOLD_VECTORS,
    evaluate_all,
    eligible_set,
)

RUNTIMES = ("simpleloop", "kapso", "eve", "loreley")
SCHEMA = "a0.qualification/v1"

# C*/c02_baseline_upstream/solution.py -- the prefill EvE's rounds seeded the solver population
# with. A round counts as written back only if a post-round solver carries a DIFFERENT source sha.
EVE_PREFILL_SHA256 = "18bacee43b713e5a76941f892c5bd7b6b69d08c1327cb87af8a4094a83d9061f"
EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"

CONFORMANCE = ROOT / "a0" / "conformance" / "report.json"
VERDICT_JSON = ROOT / "a0" / "verify" / "verdicts.json"
RECONCILIATION = ROOT / "a0" / "closure" / "closure.reconciliation.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def component(value, evidence, justification, provenance, **extra):
    doc = {
        "value": value,
        "evidence": evidence,
        "justification": justification,
        "provenance": provenance,
    }
    doc.update(extra)
    return doc


# --------------------------------------------------------------------------------------
# A0.1: measured vs adapted, from the conformance runner's own qualification block


def a01_components(runtime: str, report: dict) -> tuple:
    entry = report["runtimes"][runtime]
    q = (entry.get("qualification") or {}).get("a0_1") or {}
    if not q:
        raise SystemExit(
            f"report.json has no runtimes.{runtime}.qualification.a0_1 -- regenerate it with "
            "`cd a0/conformance && python3 conformance.py run`"
        )
    evidence = f"a0/conformance/report.json#runtimes.{runtime}.qualification.a0_1"
    total = int(q["total"])
    measured = int(q["measured"])
    adapted = int(q["adapted"])
    rows = {r["candidate_id"]: r for r in entry.get("rows") or []}
    declared = all(rows[cid]["verdict"] == "SYNTHETIC_DECLARED" for cid in q.get("adapted_candidates") or [])

    measured_comp = component(
        f"{measured}/{total}",
        evidence,
        f"the runtime's own evaluator interface produced a fresh E_r verdict for {measured} of "
        f"{total} members of C*; the runner compared them against the frozen E* table",
        "verified_by_running",
        measured=measured,
        total=total,
        state=q["state"],
        label=q["label"],
        measured_candidates=q.get("measured_candidates") or [],
        c_measure=q.get("c_measure"),
    )
    adapted_comp = component(
        f"{adapted}/{total}",
        evidence,
        (
            f"{adapted} of {total} rows agree only because the adapter supplied semantics the "
            "runtime's interface cannot represent (declared synthetic failure); they are evidence "
            "for C_adapt, never for C_measure"
            if adapted
            else "no row needed adapter-supplied semantics: every accepting row is a fresh measurement"
        ),
        "verified_by_running",
        adapted=adapted,
        total=total,
        accepted=adapted,
        all_declared_synthetic=declared,
        adapted_candidates=q.get("adapted_candidates") or [],
        c_adapt=q.get("c_adapt"),
    )
    return measured_comp, adapted_comp


# --------------------------------------------------------------------------------------
# A0.2 mechanism: does the runtime consume scores per its claimed selection semantics?


def a02_mechanism(runtime: str, verdicts: dict) -> dict:
    audited = {
        c["id"]: c["verdict"]
        for c in (verdicts or {}).get("claims", [])
        if c["id"] in ("C4.1", "C4.2", "C4.3", "C4.4")
    }
    claim = {"simpleloop": "C4.4", "kapso": "C4.1", "eve": "C4.2", "loreley": "C4.3"}[runtime]

    if runtime == "simpleloop":
        path = ROOT / "a0/runtimes/simpleloop/out/a02/a02_checks.json"
        doc = load(path)
        checks = doc.get("checks") or []
        ok = doc.get("verdict") == "pass" and not doc.get("failed")
        detail = (
            f"verdict={doc.get('verdict')}, {doc.get('passed')}/{len(checks)} checks pass, "
            f"failed={doc.get('failed')}"
        )
        scope = "the adapter's own selection loop over C*: ordering invariance, the frozen tie-break, "
    elif runtime == "kapso":
        path = ROOT / "a0/runtimes/kapso/runs/a0-01/a02/a02.json"
        doc = load(path)
        checks = doc.get("checks") or []
        ok = bool(doc.get("pass")) and not doc.get("failures")
        n_ok = sum(1 for c in checks if c.get("pass"))
        detail = (
            f"pass={doc.get('pass')}, {n_ok}/{len(checks)} checks pass, "
            f"{len(doc.get('scenarios') or {})} scenarios, failures={doc.get('failures')}"
        )
        scope = "real KAPSO selection code (_select_parent / get_deliverable_experiment / "
    elif runtime == "eve":
        path = ROOT / "a0/verify/out/eve_a02_replication.json"
        doc = load(path)
        v = doc.get("verdict") or {}
        keys = ("E1_within_ci_of_closed_form", "control_moved", "one_call_per_draw")
        ok = all(bool(v.get(k)) for k in keys)
        detail = (
            f"auditor's own 3000-draw re-run: {json.dumps(v, sort_keys=True)}, score-dependence "
            f"z={doc.get('score_dependence_z')}"
        )
        scope = "EvE's sampler (solver_examples) only -- EvE has no argmax over an evaluated pool, so "
    else:
        path = ROOT / "a0/runtimes/loreley/out/a02.json"
        doc = load(path)
        checks = doc.get("checks") or []
        ok = doc.get("verdict") == "pass" and not doc.get("failed_checks")
        detail = (
            f"verdict={doc.get('verdict')}, {sum(1 for c in checks if c.get('passed'))}/{len(checks)} "
            f"checks pass, failed_checks={doc.get('failed_checks')}"
        )
        scope = "the real MAP-Elites archive/cell machinery on a separate database: same-cell "
    scope += "the claim runs at mechanism level, not end to end (see a0_2_e2e)"

    caveats = []
    if runtime == "kapso":
        decl_path = ROOT / "a0/contract/selection/kapso.selection.json"
        decl = load(decl_path) or {}
        div = decl.get("selection", {}).get("tie_break_divergence")
        if div:
            caveats.append(
                {
                    "caveat": "tie-break divergence from the A0-wide frozen rule",
                    "status": "MEASURED DIVERGENCE; the frozen tie-break is UNPROVEN for KAPSO",
                    "evidence": [rel(decl_path), "a0/runtimes/kapso/runs/tie-order-probe/outcome.json"],
                    "to_settle": (
                        "none by measurement -- the divergence is already measured in BOTH proposal "
                        "orders (tie-order-probe/outcome.json: diverges_from_frozen_tie_break=true). "
                        "What is undecided is whether the A0-wide frozen tie-break is a requirement "
                        "KAPSO must satisfy; that is a contract decision, not an experiment"
                    ),
                }
            )
    if runtime == "eve":
        caveats.append(
            {
                "caveat": "the PASS covers the sampler, not EvE's shipped loop",
                "status": "SCOPE LIMIT (declared by the EvE workstream), not a failure",
                "evidence": ["a0/runtimes/eve/selection/eve.selection.json#selection.not_claimed"],
            }
        )

    return component(
        "PASS" if ok else "FAIL",
        rel(path),
        f"{detail}; independently audited as claim {claim} = {audited.get(claim, 'not in verdicts.json')}",
        "read_from_source",
        audited_claim=claim,
        audited_verdict=audited.get(claim),
        detail=detail,
        scope=scope,
        caveats=caveats,
    )


# --------------------------------------------------------------------------------------
# A0.2 end-to-end: a real model-lane round through the runtime's own loop


def a02_e2e(runtime: str, verdicts: dict) -> dict:
    claim = {"simpleloop": "C7.2", "kapso": "C7.1", "eve": "C7.3", "loreley": "C7.4"}[runtime]
    audited = {
        c["id"]: c["verdict"] for c in (verdicts or {}).get("claims", []) if c["id"] == claim
    }.get(claim, "not in verdicts.json")

    if runtime == "simpleloop":
        live = ROOT / "a0/runtimes/simpleloop/out/cli-lane/codex-live4/run_meta.json"
        doc = load(live) or {}
        scalar = doc.get("champion_scalar")
        ok = scalar is not None and doc.get("eid_star") == EID_STAR
        return component(
            "COMPLETE" if ok else "UNPROVEN",
            [rel(live), "a0/runtimes/simpleloop/out/cli-lane-codex-live3.log"],
            f"real model lane wrote an agent-authored candidate that E* scored {scalar} "
            f"(best C* member = 2.4519); audited as {claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            rounds=["codex-live3", "codex-live4"],
            detail=f"champion_id={doc.get('champion_id')}, champion_scalar={scalar}",
        )
    if runtime == "kapso":
        path = ROOT / "a0/runtimes/kapso/runs/e2e-real/e2e_verification.json"
        doc = load(path) or {}
        ok = doc.get("verdict") == "verified_end_to_end"
        return component(
            "COMPLETE" if ok else "UNPROVEN",
            rel(path),
            f"real run_implementation round completed and wrote back; three-way score agreement "
            f"{doc.get('score_cross_checks')}; audited as {claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            detail=f"verdict={doc.get('verdict')}",
        )
    if runtime == "eve":
        rounds = []
        for name in ("run002", "run003", "run004"):
            path = ROOT / "a0/runtimes/eve/out" / name / "real_round.json"
            doc = load(path) or {}
            solvers = ((doc.get("populations_after") or {}).get("solver")) or []
            authored = [
                s for s in solvers
                if (s.get("score") or {}).get("e_star_candidate_source_sha256")
                not in (None, EVE_PREFILL_SHA256)
            ]
            rounds.append(
                {
                    "round": name,
                    "iterations_completed": doc.get("iterations_completed"),
                    "agent_authored_solver_written_back": bool(authored),
                    "wall_seconds": doc.get("wall_seconds"),
                    "failure": (doc.get("agent_artifacts") or {}).get("failure"),
                }
            )
        completed = [r for r in rounds if r["agent_authored_solver_written_back"]]
        return component(
            "COMPLETE" if completed else "ATTEMPTED",
            ["a0/runtimes/eve/out/run002/real_round.json",
             "a0/runtimes/eve/out/run003/real_round.json",
             "a0/runtimes/eve/out/run004/real_round.json"],
            f"{len(rounds)} real codex-backed rounds reached iteration-complete, but none wrote back "
            f"an agent-authored solution.py (every post-round solver is the prefill baseline "
            f"18bacee4...); audited as {claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            rounds=rounds,
            to_settle=(
                "a completed round: `a0/runtimes/eve/.venv/bin/python "
                "a0/runtimes/eve/tools/run_one_eve_iteration.py --run-dir a0/runtimes/eve/out/run006 "
                "--turns 14 --turn-timeout 660 --max-seconds 1080` (the documented driver that produced "
                "run002-004; NOT executed here), then require real_round.json to show a post-round "
                "solver whose e_star_candidate_source_sha256 is not the baseline sha"
            ),
        )
    path = ROOT / "a0/runtimes/loreley/llm-round/RESULT.md"
    stage = ROOT / "a0/runtimes/loreley/llm-round/stage_a2_result.json"
    doc = load(stage) or {}
    flat = " ".join(path.read_text().split()) if path.exists() else ""
    planning_real = bool(doc.get("ok")) and "real codex call, succeeded" in flat
    no_round = "no for a completed round inside the cap" in flat
    return component(
        "PLANNING_ONLY" if planning_real and no_round else "UNPROVEN",
        [rel(path), rel(stage), "a0/runtimes/loreley/llm-round/bounded_round.log"],
        "a real codex planning call succeeded (144.1 s) but the coding call exceeded its 480 s budget "
        f"and the round watchdog stopped the job; audited as {claim} = {audited}",
        "read_from_source",
        audited_claim=claim,
        audited_verdict=audited,
        detail="planning real, no evaluation, no archive write, evolution_jobs status=RUNNING",
        to_settle=(
            "a completed round: `cd a0/runtimes/loreley && timeout 1200 ./llm-round/"
            "run_bounded_round.sh` with a coding budget that fits the cap (the 480 s coding attempt "
            "timed out; the round needs a smaller task or a larger cap). NOT executed here"
        ),
    )


# --------------------------------------------------------------------------------------
# Closure


def closure_component(runtime: str) -> dict:
    path = ROOT / "a0/closure" / f"closure.{runtime}.json"
    doc = load(path) or {}
    mechanisms = doc.get("mechanisms") or []
    closed = [m.get("id") for m in mechanisms if m.get("schema_verdict") == "closed"]
    fully_closed = [
        m.get("id") for m in mechanisms
        if m.get("schema_verdict") == "closed" and m.get("study_verdict") == "CLOSED"
    ]
    not_closed = [
        {"mechanism": m.get("id"), "study_verdict": m.get("study_verdict")}
        for m in mechanisms
        if m.get("id") not in closed
    ]
    if doc.get("verdict") == "closed" and doc.get("study_verdict") == "CLOSED":
        value = "CLOSED"
    elif closed:
        value = "CONDITIONAL"
    else:
        value = "OPEN"

    lane = (load(RECONCILIATION) or {}).get("lane_e2e_measurements", {}).get("results") or []
    lane_here = [r for r in lane if r.get("runtime") == runtime]
    justification = (
        f"a0/closure record verdict={doc.get('verdict')}, study_verdict={doc.get('study_verdict')}; "
        f"mechanism(s) with an executed two-control probe = {closed or 'none'}"
        + (f" (of which the study calls CLOSED outright: {fully_closed})" if fully_closed else "")
        + (f"; not probe-proven closed: {[m['mechanism'] for m in not_closed]}" if not_closed else "")
        + (f"; lane e2e on the real model lane (in-lane canary persisted): "
           f"{[r.get('verdict') for r in lane_here]}" if lane_here else "")
    )
    return component(
        value,
        [rel(path), "a0/closure/closure.reconciliation.json"],
        justification,
        "read_from_source",
        verdict=doc.get("verdict"),
        study_verdict=doc.get("study_verdict"),
        probe_proven_closed_mechanisms=closed,
        fully_closed_mechanisms=fully_closed,
        not_closed_mechanisms=not_closed,
        mechanisms=[
            {"mechanism": m.get("id"), "schema_verdict": m.get("schema_verdict"),
             "study_verdict": m.get("study_verdict")}
            for m in mechanisms
        ],
        lane_e2e=lane_here,
        verdict_scope=doc.get("verdict_note") or doc.get("verdict_summary"),
        caveats=[
            {
                "caveat": "these records are dated 2026-09-20",
                "status": "NOT RECONCILED with the newer lane work",
                "evidence": ["a0/notes/exit-closed/proxy-closure/REPORT.md"],
                "to_settle": (
                    "re-run the per-runtime closure verdicts against the docker --internal + "
                    "dual-homed-allowlist-proxy topology and update a0/closure/*.json; the newer "
                    "workstream has no per-runtime closure record yet, so these values stand"
                ),
            }
        ],
    )


# --------------------------------------------------------------------------------------


def build() -> dict:
    report = load(CONFORMANCE)
    if report is None:
        raise SystemExit(f"missing {rel(CONFORMANCE)}; run `cd a0/conformance && python3 conformance.py run`")
    verdicts = load(VERDICT_JSON) or {}

    runtimes = {}
    for runtime in RUNTIMES:
        measured, adapted = a01_components(runtime, report)
        mechanism = a02_mechanism(runtime, verdicts)
        e2e = a02_e2e(runtime, verdicts)
        closure = closure_component(runtime)
        q_r = {
            "a0_1_measured": measured,
            "a0_1_adapted": adapted,
            "a0_2_mechanism": mechanism,
            "a0_2_e2e": e2e,
            "closure": closure,
        }
        entry = {
            "runtime": runtime,
            "Q_r": q_r,
            "Q_r_values": {name: comp["value"] for name, comp in q_r.items()},
        }
        runtimes[runtime] = entry

    qualification = {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generated_by": "a0/qualification/build_qualification.py",
        "purpose": (
            "a per-runtime qualification vector Q_r and an explicit eligibility predicate, so a "
            "partial result can never be diluted by siblings that passed (external review point 8); "
            "and the corrected EvE A0.1 label PARTIAL -- 5/14 measured, never PASS (point 2)"
        ),
        "review_basis": {
            "point_2": "A0.1 for EvE must read `PARTIAL -- 5/14 measured`, never `PASS`",
            "point_8": "a single global A0 PASS is the wrong output; Q_r = (A0.1_measured, "
                       "A0.1_adapted, A0.2_mechanism, A0.2_E2E, Closure) and Eligible(r) = f(Q_r)",
        },
        "provenance_classes": {
            "verified_by_running": "this workstream executed the thing that produced the evidence",
            "read_from_source": "the value is read out of a stored artifact produced by another workstream",
            "inferred": "derived by rule from other components, not directly observed",
        },
        "component_domains": {
            "a0_1_measured": "`<measured>/<total>`; `state` in PASS | PARTIAL | FAIL | PENDING | BLOCKED",
            "a0_1_adapted": "`<adapted>/<total>`; `all_declared_synthetic` must be true for acceptance",
            "a0_2_mechanism": "PASS | FAIL | UNPROVEN",
            "a0_2_e2e": "COMPLETE | PLANNING_ONLY | ATTEMPTED | NONE | UNPROVEN",
            "closure": "CLOSED | CONDITIONAL | OPEN | UNPROVEN",
        },
        "c_measure_vs_c_adapt": {
            "C_measure": "can the RUNTIME'S evaluator interface faithfully represent E*'s outcome "
                         "algebra (so that a row is measured, not reconstructed)?",
            "C_adapt": "can the ADAPTER supply the semantics that interface cannot represent?",
            "not_about_adapters_in_the_loop": (
                "this distinction is about a semantic gap in the runtime's interface -- all four "
                "runtimes run through an adapter, so 'the adapter is in the loop' is not the point. "
                "An adapted row is evidence for C_adapt and never for C_measure"
            ),
            "a1_consequence": (
                "EvE's native numbers must not be used in any statistic that has to distinguish "
                "`invalid`/`error` from a genuine zero: on those rows EvE's interface returns a "
                "synthetic 0.0 and only the adapter's side-channel reading restores the verdict"
            ),
        },
        "predicate": {
            "name": "Eligible",
            "version": PREDICATE_VERSION,
            "signature": "Eligible(r; T) : Q_r x thresholds -> {eligible, not_eligible}",
            "implementation": "a0/qualification/eligibility.py",
            "default_vector": DEFAULT_VECTOR,
            "rules": RULES,
            "threshold_vectors": THRESHOLD_VECTORS,
            "screen_is_a_different_object": (
                "`|R_1| >= 1` (plan:490) is a CANDIDATE SCREEN over runtimes: it answers 'may the "
                "study continue at all?'. Eligible(r) answers 'may THIS runtime's numbers be used in "
                "an A1 statistic?'. They are not the same object, and `|R_1| >= 1` does not imply "
                "that any runtime is Eligible()"
            ),
        },
        "runtimes": runtimes,
    }

    evaluation = {vector: evaluate_all(qualification, vector) for vector in THRESHOLD_VECTORS}
    qualification["evaluation"] = evaluation
    qualification["eligible_set"] = {
        vector: eligible_set(qualification, vector) for vector in THRESHOLD_VECTORS
    }
    qualification["screen"] = screen_block(report, runtimes)
    qualification["unproven"] = unproven_block(runtimes)
    return qualification


def screen_block(report: dict, runtimes: dict) -> dict:
    v = report.get("verdicts") or {}
    a0_1_pass = v.get("r_1_a0_1_only") or []
    a0_1_partial = v.get("r_1_a0_1_partial") or []
    both = sorted(
        r for r, e in runtimes.items()
        if e["Q_r"]["a0_1_measured"].get("state") == "PASS"
        and e["Q_r"]["a0_2_mechanism"].get("value") == "PASS"
    )
    return {
        "what": "the candidate screen, not the eligibility predicate",
        "r_1_a0_1_only": a0_1_pass,
        "r_1_a0_1_partial": a0_1_partial,
        "screen_source": "a0/conformance/report.json#verdicts (the runner owns the A0.1 half)",
        "r_1_derived_if_a0_2_mechanism_counts": both,
        "r_1_derived_note": (
            "DERIVED here from `a0_1_measured.state == PASS and a0_2_mechanism == PASS`; the "
            "authoritative A0.2 judgement is owned by the A0.2 workstream (a0/acceptance), so treat "
            "this as an upper bound on R_1"
        ),
        "screen_passes": len(a0_1_pass) >= 1 or len(a0_1_partial) >= 1,
        "screen_rule": "|R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2",
        "not_the_same_as_eligibility": (
            "a runtime can be in the screen set and still not Eligible() under T_strict, and the "
            "reverse order of dilution is impossible: a PARTIAL runtime is not in r_1_a0_1_only"
        ),
    }


def unproven_block(runtimes: dict) -> list:
    items = []
    for runtime, entry in runtimes.items():
        for name, comp in entry["Q_r"].items():
            if comp.get("value") in ("UNPROVEN", "NONE"):
                items.append(
                    {
                        "runtime": runtime,
                        "component": name,
                        "value": comp["value"],
                        "evidence": comp["evidence"],
                        "to_settle": comp.get("to_settle"),
                    }
                )
            for caveat in comp.get("caveats") or []:
                if "UNPROVEN" in str(caveat.get("status", "")) or "NOT RECONCILED" in str(caveat.get("status", "")):
                    items.append(
                        {
                            "runtime": runtime,
                            "component": name,
                            "caveat": caveat["caveat"],
                            "status": caveat["status"],
                            "evidence": caveat["evidence"],
                            "to_settle": caveat.get("to_settle"),
                        }
                    )
    # A0.2 end to end is the one place where the study's own boundary (mechanism-level verified vs
    # end-to-end unverified) leaves a component short of the strict threshold; record it explicitly.
    for runtime in runtimes:
        e2e = runtimes[runtime]["Q_r"]["a0_2_e2e"]
        if e2e["value"] != "COMPLETE":
            items.append(
                {
                    "runtime": runtime,
                    "component": "a0_2_e2e",
                    "value": e2e["value"],
                    "status": "UNPROVEN for a completed end-to-end round",
                    "evidence": e2e["evidence"],
                    "to_settle": e2e.get("to_settle"),
                }
            )
    return items


def strip_volatile(doc: dict) -> dict:
    doc = json.loads(json.dumps(doc))
    doc.pop("generated_at", None)
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_qualification.py", description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(HERE / "qualification.json"))
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--check", action="store_true", help="re-derive and diff against --out; exit 1 on drift")
    args = parser.parse_args(argv)

    built = build()
    out = Path(args.out)
    if args.stdout:
        print(json.dumps(built, indent=2, ensure_ascii=False))
        return 0
    if args.check:
        if not out.exists():
            print(f"{out} does not exist", file=sys.stderr)
            return 1
        stored = json.loads(out.read_text())
        if strip_volatile(stored) == strip_volatile(built):
            print(f"{out}: matches its evidence (re-derived on {_now()})")
            return 0
        a, b = strip_volatile(stored), strip_volatile(built)
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                print(f"  ! {key} differs", file=sys.stderr)
        print(f"{out}: DRIFT -- the file no longer matches its evidence", file=sys.stderr)
        return 1
    out.write_text(json.dumps(built, indent=2, ensure_ascii=False) + "\n")
    print(f"written: {out}")
    for vector, names in built["eligible_set"].items():
        print(f"  {vector}: |Eligible| = {len(names)}: {names or 'none'}")
    return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


if __name__ == "__main__":
    raise SystemExit(main())
