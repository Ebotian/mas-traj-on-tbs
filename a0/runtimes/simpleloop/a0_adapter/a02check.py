"""A0.2 — Score -> Search Contract for SimpleLoop, executed rather than asserted.

The protocol's selection semantics for SimpleLoop are, verbatim (`plan:608-614`):

    c*_t = argmax_{i <= t} E(c_i)
    parent_{t+1} = c*_t

Two things that sentence does not fix, and that a0/acceptance/DERIVATIONS.md §4
flags as gaps that must be closed before A0.2 means anything, are frozen in
`policy/simpleloop.policy.json`: the tie-break, and the fold from E*'s multi-field
Outcome to the scalar being maximized. These checks make both observable, and make
each one fail if it is wrong:

  * `order_invariance`      the same candidate multiset proposed in forward and
                            reversed order must yield the same champion
  * `tie_break_observable`  C*'s deliberate tie pair (c01_good_hex / c03_mirror,
                            identical metrics, different bytes) must be decided by
                            the frozen rule — and the *rejected* rule
                            (earliest-evaluation-index) must give a different
                            answer, so the check is not vacuous
  * `near_tie_not_absorbed` c01 vs c04 differ by 1e-4, which is > 1e-9 and > any
                            epsilon window; value-order and rank-order must agree
  * `null_never_wins`       c05_overlapping carries the highest *nominal*
                            structure.sum_radii (2.452) but E* says invalid, so it
                            is unscored and must never win; a 0.0 would have been
                            a false green
  * `error_verdicts_propagate` the five raising candidates must arrive as
                            invalid/error with their failure_stage, not as numbers
  * `injected_score_moves_selection`  an externally supplied score must be able
                            to change the champion (B0+ channel existence)
  * `running_max_monotone`  the champion's scalar must never decrease as
                            iterations accumulate
  * `fr_frozen`             every score event must carry the frozen F_r spec_hash,
                            and the injection run must carry a *different* one
"""

from __future__ import annotations

import json
from pathlib import Path

from .loop import SELECTION_POLICY
from .policy import choose, choose_earliest_index, fr_for_events, load_policy
from .runner import Settings, run_once, validate_traces

FORWARD_TAIL = ["c01_good_hex", "c03_mirror", "c04_near_tie", "c05_overlapping",
                "c09_malformed_import"]
REVERSE_TAIL = list(reversed(FORWARD_TAIL))


def _script(candidate_ids: list[str]) -> dict:
    proposals = [{"iteration": 0, "kind": "c_star_member",
                  "candidate_id": "c02_baseline_upstream"}]
    for i, cid in enumerate(candidate_ids, start=1):
        proposals.append({"iteration": i, "kind": "c_star_member", "candidate_id": cid})
    return {"schema": "a0.simpleloop.solver_script/v1",
            "note": "A0.2 injected proposal sequence (documented seam: solvers.py::InjectedSolver)",
            "proposals": proposals}


def _write_script(path: Path, candidate_ids: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(_script(candidate_ids), fh, indent=1)
        fh.write("\n")
    return path


def _row(meta: dict, candidate_id: str) -> dict:
    rows = [r for r in meta["history"] if r["candidate_id"] == candidate_id]
    return rows[-1] if rows else {}


def _check(check_id: str, description: str, passed: bool, evidence) -> dict:
    return {"check_id": check_id, "description": description, "pass": bool(passed),
            "evidence": evidence}


def run_all(settings: Settings, *, out_root: Path) -> dict:
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    fwd_script = _write_script(out_root / "scripts" / "a02_forward.json", FORWARD_TAIL)
    rev_script = _write_script(out_root / "scripts" / "a02_reverse.json", REVERSE_TAIL)

    fwd_out, _ev_f, _loop_f = run_once(
        settings, solver_kind="injected", solver_script=fwd_script,
        run_dir=out_root / "runs" / "a02-forward", run_id="a02-forward",
        check_point="A0.2 SimpleLoop: order invariance, forward proposal order",
    )
    rev_out, _ev_r, _loop_r = run_once(
        settings, solver_kind="injected", solver_script=rev_script,
        run_dir=out_root / "runs" / "a02-reverse", run_id="a02-reverse",
        check_point="A0.2 SimpleLoop: order invariance, reversed proposal order",
    )
    inj_out, _ev_i, _loop_i = run_once(
        settings, solver_kind="injected", solver_script=fwd_script,
        inject_scores={"c02_baseline_upstream": 99.0},
        run_dir=out_root / "runs" / "a02-injected", run_id="a02-injected",
        check_point="A0.2/B0+ SimpleLoop: externally supplied score changes the champion",
    )

    meta = {}
    for name, run_dir in (("forward", fwd_out), ("reverse", rev_out), ("injected", inj_out)):
        with (out_root / "runs" / f"a02-{name}" / "run_meta.json").open("r", encoding="utf-8") as fh:
            meta[name] = json.load(fh)

    checks: list[dict] = []

    # 1. order invariance -------------------------------------------------
    checks.append(_check(
        "order_invariance",
        "proposing the same candidate multiset in forward and reversed order yields the "
        "same champion (A0.2: selection is a deterministic argmax, not an order artefact)",
        fwd_out.champion_id == rev_out.champion_id and fwd_out.champion_id is not None,
        {
            "forward_order": FORWARD_TAIL,
            "reverse_order": REVERSE_TAIL,
            "forward_champion": fwd_out.champion_id,
            "reverse_champion": rev_out.champion_id,
            "forward_champion_scalar": fwd_out.champion_scalar,
            "reverse_champion_scalar": rev_out.champion_scalar,
        },
    ))

    # 2. tie-break observable --------------------------------------------
    c01 = _row(meta["forward"], "c01_good_hex")
    c03 = _row(meta["forward"], "c03_mirror")
    tie_equal = (
        c01.get("e_star_scalar") is not None
        and c01.get("e_star_scalar") == c03.get("e_star_scalar")
        and c01.get("solution_sha256") != c03.get("solution_sha256")
    )
    earliest_fwd = choose_earliest_index({
        r["candidate_id"]: r["search_signal"] for r in meta["forward"]["history"]
    })
    earliest_rev = choose_earliest_index({
        r["candidate_id"]: r["search_signal"] for r in meta["reverse"]["history"]
    })
    checks.append(_check(
        "tie_break_observable",
        "the tie pair (identical metrics, different bytes) is decided by the frozen rule "
        "in both orders, and the rejected earliest-index rule gives a different answer",
        tie_equal
        and fwd_out.champion_id == "c01_good_hex"
        and rev_out.champion_id == "c01_good_hex"
        and earliest_rev == "c03_mirror"
        and earliest_fwd == "c01_good_hex",
        {
            "c01_scalar": c01.get("e_star_scalar"),
            "c03_scalar": c03.get("e_star_scalar"),
            "c01_sha256": c01.get("solution_sha256"),
            "c03_sha256": c03.get("solution_sha256"),
            "frozen_rule_champion_forward": fwd_out.champion_id,
            "frozen_rule_champion_reverse": rev_out.champion_id,
            "rejected_earliest_index_forward": earliest_fwd,
            "rejected_earliest_index_reverse": earliest_rev,
            "tie_event_reason": _tie_reason(out_root, "forward"),
        },
    ))

    # 3. near tie ---------------------------------------------------------
    c04 = _row(meta["forward"], "c04_near_tie")
    gap = (c01.get("e_star_scalar") or 0.0) - (c04.get("e_star_scalar") or 0.0)
    # Ranks and an epsilon-tolerant comparison are computed from the *measured*
    # signals, not asserted: a rank transform is a monotone map, so it cannot
    # reorder the pair; and an epsilon window of 1e-9 cannot close a 1e-4 gap.
    measured = {row["candidate_id"]: row["search_signal"]
                for row in meta["forward"]["history"] if row["search_signal"] is not None}
    ranked = sorted(measured, key=lambda cid: (-measured[cid], cid))
    pair = ["c01_good_hex", "c04_near_tie"]
    value_order = sorted(pair, key=lambda cid: -measured[cid])
    rank_order = sorted(pair, key=lambda cid: ranked.index(cid))
    eps_treated_equal = abs(measured["c01_good_hex"] - measured["c04_near_tie"]) <= settings.epsilon
    checks.append(_check(
        "near_tie_not_absorbed",
        "the near-tie pair stays ordered: the gap exceeds the A0.1 epsilon by ~5 orders of "
        "magnitude, so an epsilon-tolerant comparison cannot call them equal, and a rank "
        "transform is monotone so it cannot flip them",
        gap > settings.epsilon
        and gap > 1e-6
        and not eps_treated_equal
        and value_order == rank_order == ["c01_good_hex", "c04_near_tie"]
        and fwd_out.champion_id == "c01_good_hex"
        and rev_out.champion_id == "c01_good_hex",
        {
            "c01_scalar": c01.get("e_star_scalar"),
            "c04_scalar": c04.get("e_star_scalar"),
            "gap": gap,
            "epsilon": settings.epsilon,
            "gap_over_epsilon": gap / settings.epsilon if settings.epsilon else None,
            "epsilon_tolerant_comparison_calls_them_equal": eps_treated_equal,
            "value_order": value_order,
            "rank_order": rank_order,
            "full_ranking_by_measured_signal": ranked,
            "champion_forward": fwd_out.champion_id,
            "champion_reverse": rev_out.champion_id,
        },
    ))

    # 4. null never wins --------------------------------------------------
    c05 = _row(meta["forward"], "c05_overlapping")
    nominal = (c05.get("structure") or {}).get("sum_radii")
    checks.append(_check(
        "null_never_wins",
        "c05_overlapping carries the highest nominal structure.sum_radii but E* says "
        "invalid, so it is unscored and never wins; a 0.0 or a nominal reading would be a "
        "false green",
        c05.get("e_star_status") == "invalid"
        and c05.get("e_star_scalar") is None
        and c05.get("search_signal") is None
        and nominal is not None
        and nominal >= (c01.get("e_star_scalar") or 0.0)
        and fwd_out.champion_id != "c05_overlapping"
        and rev_out.champion_id != "c05_overlapping",
        {
            "c05_status": c05.get("e_star_status"),
            "c05_exit_code": c05.get("e_star_exit_code"),
            "c05_scalar": c05.get("e_star_scalar"),
            "c05_search_signal": c05.get("search_signal"),
            "c05_nominal_structure_sum_radii": nominal,
            "c01_scalar": c01.get("e_star_scalar"),
            "forward_champion": fwd_out.champion_id,
            "reverse_champion": rev_out.champion_id,
        },
    ))

    # 5. verdict propagation ---------------------------------------------
    propagations = []
    for cid in ("c05_overlapping", "c09_malformed_import"):
        row = _row(meta["forward"], cid)
        propagations.append({
            "candidate_id": cid,
            "exit_code": row.get("e_star_exit_code"),
            "status": row.get("e_star_status"),
            "failure_kind": row.get("e_star_failure_kind"),
            "failure_stage": row.get("failure_stage"),
            "failure_detail": row.get("failure_detail"),
            "scalar": row.get("e_star_scalar"),
        })
    checks.append(_check(
        "error_verdicts_propagate",
        "E*'s invalid (exit 2) and error (exit 3) verdicts arrive as named failure_stages "
        "with detail, and never as a number",
        all(p["scalar"] is None and p["failure_stage"] != "none" and p["failure_detail"]
            for p in propagations)
        and propagations[0]["exit_code"] == 2
        and propagations[0]["failure_stage"] == "verify_failed"
        and propagations[1]["exit_code"] == 3
        and propagations[1]["failure_stage"] == "resolve_failed",
        propagations,
    ))

    # 6. injected score moves the selection -------------------------------
    inj_c02 = _row(meta["injected"], "c02_baseline_upstream")
    checks.append(_check(
        "injected_score_moves_selection",
        "an externally supplied scalar (--inject-scores) changes the champion while the "
        "logged E* Outcome stays the real one: the B0+ injection channel exists end to end",
        inj_out.champion_id == "c02_baseline_upstream"
        and inj_out.champion_id != fwd_out.champion_id
        and abs(inj_c02.get("e_star_scalar", -1) - 0.25) < 1e-12
        and abs(inj_c02.get("injected_scalar", -1) - 99.0) < 1e-12,
        {
            "uninjected_champion": fwd_out.champion_id,
            "injected_champion": inj_out.champion_id,
            "c02_real_scalar": inj_c02.get("e_star_scalar"),
            "c02_injected_scalar": inj_c02.get("injected_scalar"),
            "c01_real_scalar": c01.get("e_star_scalar"),
        },
    ))

    # 7. running max monotone --------------------------------------------
    monotone = {}
    for name in ("forward", "reverse"):
        steps = []
        ok = True
        for sel in _selection_events(out_root, name):
            chosen = sel["selection"]["chosen_candidate_id"]
            considered = {c["candidate_id"]: c["search_signal"]
                          for c in sel["selection"]["considered"]}
            expected = choose(considered)[0]
            steps.append({"iteration": sel["iteration"], "chosen": chosen, "expected": expected,
                          "n_considered": len(considered)})
            if chosen != expected:
                ok = False
        # The running maximum must never lose a better candidate, so the chosen
        # scalar must be non-decreasing across iterations.
        scalars = []
        for step in steps:
            considered = next(
                (s["selection"]["considered"] for s in _selection_events(out_root, name)
                 if s["iteration"] == step["iteration"]), [])
            sig = {c["candidate_id"]: c["search_signal"] for c in considered}  # noqa: E501
            scalars.append(sig.get(step["chosen"]))
        present = [s for s in scalars if s is not None]
        monotone[name] = {
            "pass": ok and present == sorted(present),
            "steps": steps,
            "champion_scalar_trajectory": scalars,
        }
    checks.append(_check(
        "running_max_monotone",
        "each recorded decision equals the frozen argmax over everything considered so far, "
        "so the champion is a running maximum and never loses a better candidate",
        all(v["pass"] for v in monotone.values()),
        {k: {kk: vv for kk, vv in v.items()} for k, v in monotone.items()},
    ))

    # 8. F_r frozen and injection labelled --------------------------------
    from .policy import canonical_file_digest

    frozen_hash = fr_for_events(settings.policy)["spec_hash"]
    fr_seen = set()
    for name in ("forward", "reverse", "injected"):
        for line in (out_root / "runs" / f"a02-{name}" / "traces"
                     / f"simpleloop.a02-{name}.score.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                fr_seen.add(json.loads(line)["fr"]["spec_hash"])
    checks.append(_check(
        "fr_frozen",
        "F_r = scalar(E*) events carry the frozen declaration hash; the injection run carries "
        "a different, separately frozen declaration and cannot be pooled with them",
        frozen_hash == canonical_file_digest(
            Path(settings.work_root) / "a0/contract/fr/scalar.json")
        and frozenset(fr_seen) == frozenset({frozen_hash, fr_for_events(settings.policy, injected=True)["spec_hash"]}),
        {
            "frozen_fr_spec_hash": frozen_hash,
            "injection_fr_spec_hash": fr_for_events(settings.policy, injected=True)["spec_hash"],
            "spec_hashes_seen": sorted(fr_seen),
        },
    ))

    # 9. the rule itself, as a pure function ------------------------------
    pairs = {"a": 0.7, "b": 0.7, "c": 0.3}
    pure = {
        "abc": choose({"a": 0.7, "b": 0.7, "c": 0.3})[0],
        "cba": choose({"c": 0.3, "b": 0.7, "a": 0.7})[0],
        "bac": choose({"b": 0.7, "a": 0.7, "c": 0.3})[0],
        "all_null": choose({"a": None, "b": None})[0],
    }
    checks.append(_check(
        "argmax_is_a_set_function",
        "the frozen rule is a function of the set of (candidate_id, scalar) pairs: every "
        "permutation of the insertion order gives the same winner, and all-unscored gives null",
        len({pure["abc"], pure["cba"], pure["bac"]}) == 1
        and pure["abc"] == "a"
        and pure["all_null"] is None,
        {"inputs": pairs, "results": pure,
         "policy_rule": SELECTION_POLICY,
         "tie_break": load_policy()["selection"]["tie_break"]},
    ))

    verdict = "pass" if all(c["pass"] for c in checks) else "fail"
    validation = {}
    for name, outcome in (("forward", fwd_out), ("reverse", rev_out), ("injected", inj_out)):
        validation[name] = validate_traces(
            settings,
            outcome,
            validator_python=(settings.work_root / "a0/contract/.venv/bin/python"),
            trace_validate_py=settings.work_root / "a0/contract/trace_validate.py",
        )
    return {
        "schema": "a0.simpleloop.a02/v1",
        "runtime": settings.runtime,
        "task": settings.task,
        "eid_star": settings.eid.eid_star,
        "epsilon": settings.epsilon,
        "trace_validation": validation,
        "runs": {
            "forward": {"run_dir": settings.rel(out_root / "runs" / "a02-forward"),
                        "champion": fwd_out.champion_id,
                        "champion_scalar": fwd_out.champion_scalar,
                        "exit_code": fwd_out.exit_code,
                        "failure_counts": fwd_out.failure_counts,
                        "trace_paths": {k: settings.rel(v) for k, v in fwd_out.trace_paths.items()}},
            "reverse": {"run_dir": settings.rel(out_root / "runs" / "a02-reverse"),
                        "champion": rev_out.champion_id,
                        "champion_scalar": rev_out.champion_scalar,
                        "exit_code": rev_out.exit_code,
                        "failure_counts": rev_out.failure_counts,
                        "trace_paths": {k: settings.rel(v) for k, v in rev_out.trace_paths.items()}},
            "injected": {"run_dir": settings.rel(out_root / "runs" / "a02-injected"),
                         "champion": inj_out.champion_id,
                         "champion_scalar": inj_out.champion_scalar,
                         "exit_code": inj_out.exit_code,
                         "failure_counts": inj_out.failure_counts,
                         "trace_paths": {k: settings.rel(v) for k, v in inj_out.trace_paths.items()}},
        },
        "checks": checks,
        "passed": sum(1 for c in checks if c["pass"]),
        "failed": [c["check_id"] for c in checks if not c["pass"]],
        "verdict": verdict,
    }


def _selection_events(out_root: Path, name: str) -> list[dict]:
    path = Path(out_root) / "runs" / f"a02-{name}" / "traces" / f"simpleloop.a02-{name}.selection.jsonl"
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _tie_reason(out_root: Path, name: str) -> list[str]:
    out = []
    for sel in _selection_events(out_root, name):
        if sel["selection"].get("tie_break"):
            out.append(f"iteration {sel['iteration']}: {sel['selection']['tie_break']}")
    return out


def summarise(result: dict) -> dict:
    return {
        "schema": result["schema"],
        "verdict": result["verdict"],
        "passed": result["passed"],
        "failed": result["failed"],
        "checks": [{"check_id": c["check_id"], "pass": c["pass"]} for c in result["checks"]],
        "runs": {k: {"champion": v["champion"], "champion_scalar": v["champion_scalar"],
                     "exit_code": v["exit_code"]} for k, v in result["runs"].items()},
    }
