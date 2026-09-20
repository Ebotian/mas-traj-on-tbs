#!/usr/bin/env python3
"""A deliberately non-conformant A0.1 adapter, one named fault per `--mode`.

Used only by `a0/conformance/selftest.py` to prove that the checker rejects each fault. A checker
that has never been shown to reject a bad adapter is not evidence of a good one.

Ground truth is the runner's own frozen sweep (`a0/conformance/reference.json`), so every mode is
a conformant answer plus exactly one fault:

  pass                 no fault (control: must stay PASS)
  zero_on_error        EvE trap: an evaluation exception reported as failure_score 0.0, with
                       status ok and the number indistinguishable from a real zero (plan:551)
  cache_hit            Loreley trap: the number is reused from a persistent cache (plan:552)
  timeout              Loreley trap: a timeout-synthesised failure reported as the measurement
  truncated            Loreley trap: metrics beyond the 64-cap silently dropped
  drift_1e_6           0.1 %-of-epsilon-scale value drift, above epsilon -> must fail
  drift_1e_10          a drift inside epsilon -> must still pass (epsilon is enforced both ways)
  swap_near_tie        c04 gets c01's value (the 1e-4 near-tie pair catches sloppy tolerances)
  digest_swap          c04 reports c01's canonical digest: a different file was evaluated
  partial              only 5 of 14 candidates reported: silent skipping must fail
  manifest_triple      granted class fast vs commanded class full (KAPSO D16, plan:532-539)
  attempt_theta_drift  the attempt ran at theta_E fast while the run declares full (plan:518)
  stale_eid            an EID* from the previous, wrong hashing (fac50fc4...): identity drift
  native_theta         a theta_E parameter from the runtime's native lane left undeclared
  synthetic_declared   an honest adapter: the EvE failure_score(0.0) trap hit, detected, declared with
                       detail, and NOT counted as a match -> must PASS (and must not be failed for it)
  synthetic_mislabeled the same synthesis, but the row is still marked as a match: a mislabeled pass
                       must FAIL even though the synthesis was nominally declared (audit:206)
  wrong_failure_kind   `status` truthful but `failure.kind` wrong on every non-ok candidate: the
                       verdict half of adapter_contract.md §4.3.5 agrees while the `why` half lies,
                       which must FAIL (audit R1: only comparing `status` made this a false PASS)
  wrong_failure_stage  `failure.kind` truthful but the declared trace `failure_stage` is not the one
                       the frozen §5.3 table maps that kind to: FAIL, because plan:577's per-runtime
                       FailureStage counts would no longer be joinable
  omit_failure_kind    the honest fixture with `failure.kind` omitted from every row: `status` is
                       truthful and there is no lie to catch, but the (verdict, failure.kind) surface
                       adapter_contract.md §4.3.5 compares is absent, so it must FAIL rather than pass
                       vacuously (audit: the second residual half of R1)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_common import (  # noqa: E402
    A0, C_STAR_MANIFEST, FR_DECLARATION, THETA_KEYS, canonical_file_digest, eid_r_declaration,
    parse_theta, read_args, reference_rows_from_sweep, write_out,
)

STALE_EID = "fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d"
MODES = [
    "pass", "zero_on_error", "cache_hit", "timeout", "truncated", "drift_1e_6", "drift_1e_10",
    "swap_near_tie", "digest_swap", "partial", "manifest_triple", "attempt_theta_drift",
    "stale_eid", "native_theta", "synthetic_declared", "synthetic_mislabeled",
    "wrong_failure_kind", "wrong_failure_stage", "omit_failure_kind",
]


def row_from_sweep(ref: dict) -> dict:
    value = ref["objective_value"]
    return {
        "candidate_id": ref["candidate_id"],
        "source_sha256": ref["source_sha256"],
        "canonical_digest": ref["canonical_digest"],
        "status": ref["status"],
        "exit_code": ref["exit_code"],
        "objective": {"name": "sum_radii", "value": value, "direction": "max"},
        "objective_value": value,
        "failure_kind": ref["failure_kind"],
        "evaluator_evidence": {"status": "ok", "detail": f"deviant fixture baseline (mode={MODE[0]})"},
        "theta_e_attempt": {
            "evaluator": "E*",
            "fidelity": "full",
            "fraction": 1.0,
            "seed": 1337,
            "granted_class": "full",
            "commanded_class": "full",
        },
    }


MODE = [None]


def build_doc(flags: dict) -> dict:
    mode = MODE[0]
    runtime = flags.get("runtime", "unknown")
    theta = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
             "runtime_budget_ms": 250.0, "timeout_s": 120.0}
    theta.update({k: v for k, v in parse_theta(flags.get("theta", "")).items() if k in THETA_KEYS})
    eid_star = json.loads(Path(flags["eid"]).read_text()).get("eid_star") if flags.get("eid") else ""

    rows = [row_from_sweep(ref) for ref in reference_rows_from_sweep()]

    if mode == "zero_on_error":
        for row in rows:
            if row["objective_value"] is None:
                row["objective"] = {"name": "sum_radii", "value": 0.0, "direction": "max"}
                row["objective_value"] = 0.0
                row["status"] = "ok"
                row["evaluator_evidence"] = {
                    "status": "synthesized_failure",
                    "detail": "evaluation exception mapped to failure_score(0.0) -- the EvE trap",
                }
    elif mode == "cache_hit":
        for row in rows:
            row["evaluator_evidence"] = {
                "status": "cache_hit",
                "detail": "persistent metric cache",
                "cached_from_run_id": "loreley-run-0001",
            }
    elif mode == "timeout":
        for row in rows:
            row["evaluator_evidence"] = {
                "status": "timeout",
                "detail": "evaluation deadline reached; failure synthesised from the last cached metric",
            }
    elif mode == "truncated":
        for row in rows:
            row["evaluator_evidence"] = {
                "status": "truncated_metrics",
                "detail": "metrics beyond the cap were dropped",
                "metrics_dropped": 5,
                "metrics_count": 69,
            }
    elif mode == "drift_1e_6":
        for row in rows:
            if row["objective_value"] is not None:
                row["objective_value"] += 1e-6
                row["objective"]["value"] = row["objective_value"]
    elif mode == "drift_1e_10":
        for row in rows:
            if row["objective_value"] is not None:
                row["objective_value"] += 1e-10
                row["objective"]["value"] = row["objective_value"]
    elif mode == "swap_near_tie":
        by_id = {row["candidate_id"]: row for row in rows}
        src, dst = by_id.get("c01_good_hex"), by_id.get("c04_near_tie")
        if src and dst and src["objective_value"] is not None:
            dst["objective_value"] = src["objective_value"]
            dst["objective"]["value"] = src["objective_value"]
    elif mode == "digest_swap":
        by_id = {row["candidate_id"]: row for row in rows}
        src, dst = by_id.get("c01_good_hex"), by_id.get("c04_near_tie")
        if src and dst:
            dst["canonical_digest"] = src["canonical_digest"]
    elif mode == "partial":
        rows = rows[:5]
    elif mode == "manifest_triple":
        for row in rows:
            row["theta_e_attempt"]["granted_class"] = "fast"
    elif mode == "attempt_theta_drift":
        for row in rows:
            row["theta_e_attempt"].update({"fidelity": "fast", "fraction": 0.15})
    elif mode == "stale_eid":
        eid_star = STALE_EID
    elif mode == "wrong_failure_kind":
        # audit R1: every `status` is E*'s own, but the `why` half of the verdict lies. Two runtimes
        # can agree on "invalid" and disagree on the failure kind, and it is the kind that decides
        # the trace `failure_stage` the study's FailureStage counts join on.
        for row in rows:
            if row["objective_value"] is None:
                row["failure_kind"] = "adversarially_wrong_kind"
    elif mode == "wrong_failure_stage":
        # the kind is truthful; the declared trace stage is not the one the frozen table maps it to.
        for row in rows:
            if row["objective_value"] is None:
                row["failure_stage"] = "search_failed"
    elif mode == "omit_failure_kind":
        # audit, second half of R1: the honest fixture with `failure.kind` omitted everywhere, so the
        # checker has nothing to *disagree* with and used to pass vacuously. §4.3.5 requires the
        # field, so an omission is its own non-conformance.
        for row in rows:
            row["failure_kind"] = None
    elif mode in ("synthetic_declared", "synthetic_mislabeled"):
        for row in rows:
            if row["objective_value"] is None:
                row["objective"] = {"name": "sum_radii", "value": 0.0, "direction": "max"}
                row["objective_value"] = 0.0
                row["status"] = "error"
                row["evaluator_evidence"] = {
                    "status": "synthesized_failure",
                    "detail": (
                        "the runtime's lane returned evaluation.failure_score verbatim because a step "
                        "exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic"
                    ),
                }
                row["classification"] = "non_measurable_reported_as_synthetic_failure"
                if mode == "synthetic_mislabeled":
                    row["status"] = None
                    row["classification"] = "match"
                    row["pass"] = True

    doc = {
        "schema": "a0.adapter.conformance/v1",
        "runtime": runtime,
        "adapter": f"a0/conformance/fixtures/adapters/deviant.py --mode {mode} (FIXTURE, not a runtime)",
        "mode": mode,
        "eid_star": eid_star,
        "eid_r": eid_r_declaration(eid_star, runtime, f"deviant/{mode}"),
        "theta_e": theta,
        "epsilon": float(flags.get("epsilon", 1e-9)),
        "primary_field": "sum_radii",
        "fr": {
            "name": "F_r = scalar(E*)",
            "version": "v1",
            "applies": "scalar",
            "spec_hash": canonical_file_digest(FR_DECLARATION),
            "declared_in": "a0/contract/fr/scalar.json",
        },
        "candidate_set": str(C_STAR_MANIFEST),
        "candidates": rows,
    }
    if mode == "native_theta":
        doc["theta_e"] = {"seed": None, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
                          "runtime_budget_ms": 250.0, "timeout_s": 120.0, "defaults_applied": {}}
    return doc


def conformance(flags: dict) -> int:
    write_out(flags["out"], build_doc(flags))
    return 0


def main(argv):
    positional, flags = read_args(argv)
    mode = flags.get("mode", "pass")
    if mode not in MODES:
        print(f"deviant: unknown mode {mode!r}; known: {MODES}", file=sys.stderr)
        return 2
    MODE[0] = mode
    if positional and positional[0] in ("conformance", "run"):
        return conformance(flags)
    print(f"deviant: unsupported subcommand {positional!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
