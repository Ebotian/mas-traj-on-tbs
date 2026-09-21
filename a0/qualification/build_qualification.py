#!/usr/bin/env python3
"""Build `qualification.json`: the per-runtime qualification vector `Q_r` and `Eligible(r)`.

`Q_r` carries seven components (decision D2 added three of them):

    a0_1_measured     <measured>/<total> + state  -- the runtime's own evaluator interface
    a0_1_adapted      <adapted>/<total> + all_declared_synthetic -- adapter-supplied semantics
    a0_1_attested     PASS | FAIL | UNPROVEN      -- the D3 harness attestation of the executed bytes
    a0_2_mechanism    PASS | FAIL | UNPROVEN      -- selection follows the score, mechanism level
    a0_2_bridge       PASS | ATTEMPTED | UNPROVEN | NONE -- the same path inside the real campaign
    closure           CLOSED | CONDITIONAL | OPEN | UNPROVEN
    mrc               FROZEN | PRESENT_UNFROZEN | ABSENT -- the model route contract

Every component is derived from **existing evidence** -- `a0/conformance/report.json`,
`a0/closure/*.json`, the A0.2 artifacts, `a0/mrc/declarations/*`, and `a0/verify/verdicts.json` --
not by re-running an experiment. The one exception is `mrc`, whose declaration is validated by
`a0/mrc/mrc.py validate` (read-only, offline). Each component carries the value, the evidence path
it came from, a one-line justification, and a provenance class:

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
    COMPONENTS,
    DEFAULT_VECTOR,
    EXPLORATORY_VECTOR,
    MAIN_ARM_VECTOR,
    PREDICATE_VERSION,
    RULES,
    THRESHOLD_VECTORS,
    evaluate_all,
    eligible,
    key_metrics,
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
ATTESTED_CONTRACT = HERE / "attested-a0-1.contract.json"
MRC_DECLARATIONS = ROOT / "a0" / "mrc" / "declarations"
MRC_FROZEN_ROUTES = ROOT / "a0" / "mrc" / "frozen_routes.json"
MRC_CLI = ROOT / "a0" / "mrc" / "mrc.py"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
#
# Since D3 the runner keeps TWO axes apart, and `qualification.a0_1.basis` says so in the runner's
# own words: `row.verdict_before_attestation` decides whether the runtime MEASURED the row;
# `row.attestation_verdict` decides whether the row is ACCEPTABLE EVIDENCE. The runner's folded
# `state`/`label` are the acceptance state -- KAPSO's numbers agree on 14/14 and its state is FAIL,
# because D3 asks for a token it did not echo. Folding that FAIL into `a0_1_measured` would report
# "this runtime's measurement is wrong" when the truth is "this runtime's evidence is missing", so
# the measurement state is derived here from the runner's own measurement-axis verdict, and the
# acceptance state is carried alongside it and consumed by the `a0_1_attested` component.

# conformance.py's ACCEPTING_VERDICTS: what `verdict_before_attestation` can be for a row that
# agrees on the measurement surface. EXECUTION_ENV_DRIFT is accepting (D1) but is not a measurement
# in the pinned environment, so it is carried as a caveat rather than silently counted.
MEASUREMENT_ACCEPTING_VERDICTS = ("MATCH", "MATCH_VERDICT", "SYNTHETIC_DECLARED", "EXECUTION_ENV_DRIFT")
SYNTHETIC_VERDICT = "SYNTHETIC_DECLARED"


def measurement_axis(entry: dict) -> dict:
    """The measurement state, derived from the runner's own per-row measurement verdicts."""
    rows = entry.get("rows") or []
    before = [str(r.get("verdict_before_attestation")) for r in rows]
    disagreeing = [
        r.get("candidate_id") for r, v in zip(rows, before)
        if v not in MEASUREMENT_ACCEPTING_VERDICTS
    ]
    synthesized = [r.get("candidate_id") for r, v in zip(rows, before)
                   if v == SYNTHETIC_VERDICT]
    env_drift = [r.get("candidate_id") for r in rows
                 if r.get("execution_env_verdict") == "EXECUTION_ENV_DRIFT"]
    if disagreeing:
        state = "FAIL"
    elif synthesized:
        state = "PARTIAL"
    else:
        state = "PASS"
    corroboration = next(
        (c for c in entry.get("checks") or [] if c.get("check_id") == "E-r-equals-E-star"), {})
    return {
        "state": state,
        "disagreeing_candidates": disagreeing,
        "synthesized_candidates": synthesized,
        "execution_env_drift_candidates": env_drift,
        "measurement_agreeing": corroboration.get("measurement_agreeing"),
        "measurement_disagreeing_from_runner": corroboration.get("measurement_disagreeing_candidates"),
        "axis_basis": (
            "derived from runtimes.<r>.rows[].verdict_before_attestation against the runner's own "
            "ACCEPTING_VERDICTS, and corroborated by the E-r-equals-E-star check's "
            "`measurement_agreeing` / `measurement_disagreeing_candidates`. It is deliberately NOT "
            "the runner's folded qualification state, which since D3 also folds in the attestation axis"
        ),
    }


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
    declared = all(
        rows[cid].get("verdict_before_attestation") == SYNTHETIC_VERDICT
        for cid in q.get("adapted_candidates") or []
    )
    axis = measurement_axis(entry)

    measured_comp = component(
        f"{measured}/{total}",
        evidence,
        f"the runtime's own evaluator interface produced a fresh E_r verdict for {measured} of "
        f"{total} members of C*; the runner compared them against the frozen E* table. "
        f"Measurement state = {axis['state']} (runner agreement "
        f"{axis['measurement_agreeing']}/{total}). MEASUREMENT ONLY: the runner's acceptance state is "
        f"{q.get('state')!r} and is a separate axis -- see a0_1_attested",
        "verified_by_running",
        measured=measured,
        total=total,
        state=axis["state"],
        measurement_state=axis["state"],
        measurement_axis=axis,
        runner_acceptance_state=q.get("state"),
        runner_label=q.get("label"),
        runner_acceptance_reason=entry.get("reason"),
        axis_note=(
            "`state` here is the MEASUREMENT axis. The runner's folded `state`/`label` also fold in "
            "the D3 attestation axis and are recorded as `runner_acceptance_state`; a runtime can "
            "measure every row and still not be acceptable evidence, and this component must not "
            "report that as a measurement error"
        ),
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
# A0.1 harness-attested (D3): the identity of the bytes the runtime executed, measured by the
# harness, not self-reported by the adapter. Fail closed -- see attested-a0-1.contract.json.


def _attested_files(runtime: str, root: Path = None) -> list:
    root = root or ROOT
    contract = load(ATTESTED_CONTRACT) or {}
    found = []
    for pattern in contract.get("search_paths") or []:
        found.extend(sorted(root.glob(pattern.replace("<runtime>", runtime))))
    return [p for p in found if p.is_file()]


def _resolve_verdict_payload(payload: dict, spec: dict, where: str) -> tuple:
    """A document whose verdict is stated outright -> (value, detail, extra) or (None, reason)."""
    identity_field = spec.get("identity_verdict_field") or "identity_verdict"
    positive = set(spec.get("positive") or [])
    negative = set(spec.get("negative") or [])
    identity_fields = spec.get("executed_identity_fields") or ["executed_identity"]
    oid_field = spec.get("oid_field") or "oid"

    verdict = payload.get(identity_field)
    if not _present(verdict):
        return None, f"{where}: no {identity_field!r} (omission fails closed)", None
    verdict = str(verdict)
    if verdict not in positive and verdict not in negative:
        return None, f"{where}: verdict {verdict!r} is not in the declared domain", None

    identity = next((payload.get(f) for f in identity_fields if _present(payload.get(f))), None)
    oid = payload.get(oid_field)
    if verdict in positive and not (_present(identity) and _present(oid)):
        return None, (
            f"{where}: verdict {verdict!r} but the executed-bytes identity or the OID token is "
            "absent -- identity is not established by a verdict alone"
        ), None

    extra = {
        "record": where,
        "identity_verdict": verdict,
        "executed_identity": identity,
        "oid": oid,
        "harness": payload.get("harness") or payload.get("issued_by"),
        "report_sha256": payload.get("report_sha256"),
        "identity_verdict_field": identity_field,
    }
    if verdict in positive:
        return "PASS", (
            f"a harness attestation is on record at {where}: verdict {verdict!r}, the executed-bytes "
            "identity and the OID token are present, and no field is omitted"
        ), extra
    return "FAIL", (
        f"an attestation is on record at {where} with verdict {verdict!r}: the bytes the runtime "
        "executed are not the bytes the harness measured as E*. This is FAIL, not UNPROVEN"
    ), extra


def _resolve_runtime_check(check: dict, spec: dict, where: str, entry: dict = None) -> tuple:
    """The D3 runner's own per-runtime `measurement-attestation` check -> verdict, or a reason.

    The runner states the identity verdict twice and consistently: on the check (`ok` plus the
    per-row candidate lists) and in `qualification.a0_1.attestation.identity_verdict`. The decision
    is taken from the check -- it is the thing the run computed -- but the verdict is NAMED from the
    qualification block when present, so the consumer reports `MISSING_ATTESTATION` in the runner's
    own vocabulary rather than an invented synonym.
    """
    required = check.get(spec.get("required_field") or "required")
    ok = check.get(spec.get("ok_field") or "ok")
    envelope = check.get(spec.get("envelope_field") or "envelope") or {}
    run_field = spec.get("harness_run_field") or "harness_run_id"
    positive = check.get(spec.get("positive_candidates_field") or "attested_candidates") or []
    negatives = {
        field: (check.get(field) or [])
        for field in spec.get("negative_candidate_fields") or []
    }
    block = (((entry or {}).get("qualification") or {}).get("a0_1") or {}).get("attestation") or {}
    runner_verdict = block.get("identity_verdict")
    row_verdicts = sorted({
        str(r.get("attestation_verdict")) for r in (entry or {}).get("rows") or []
        if r.get("attestation_verdict")
    })

    if required is None:
        return None, f"{where}: the check does not say whether the token requirement was on", None
    if not required:
        return None, (
            f"{where}: the run was made with the token requirement OFF (`required=false`), so no "
            "attestation was required and none is established"
        ), None
    if ok is None:
        return None, f"{where}: the check carries no verdict", None
    if ok:
        run_id = envelope.get(run_field) or check.get(run_field)
        if not _present(run_id):
            return None, f"{where}: the check reports ok but names no harness run", None
        if not positive:
            return None, f"{where}: the check reports ok but attests no candidate", None
        return "PASS", (
            f"the D3 runner's own `measurement-attestation` check for this runtime is ok: "
            f"{len(positive)} row(s) echo the harness measurement token and attest the evaluator "
            f"bytes, candidate bytes and behaviour digest they used; harness run {run_id}, "
            f"executed identity {block.get('executed_identity')}"
        ), {
            "record": "a0/conformance/report.json#runtimes.<runtime>.checks[measurement-attestation]",
            "identity_verdict": runner_verdict or "ATTESTATION_OK",
            "executed_identity": block.get("executed_identity"),
            "oid": run_id,
            "harness": "a0/conformance/conformance.py",
            "report_sha256": None,
            "attested_candidates": positive,
            "oid_present_rows": check.get("rows_with_oid"),
            "envelope": {
                "path": envelope.get("path"), "sha256": envelope.get("sha256"),
                "nonce": envelope.get("nonce"),
            },
        }
    verdict_name = runner_verdict or (
        "MISSING_ATTESTATION" if negatives.get("missing_attestation_candidates")
        else "MISSING_IDENTITY" if negatives.get("missing_identity_candidates")
        else "MISMATCH_ATTESTATION" if negatives.get("mismatch_attestation_candidates")
        else "ATTESTATION_NOT_OK"
    )
    counts = ", ".join(f"{len(v)} x {k}" for k, v in negatives.items() if v)
    return "FAIL", (
        f"the D3 runner's own `measurement-attestation` check for this runtime FAILED: "
        f"{verdict_name} ({counts or 'no per-candidate list'}). The measurement axis is unaffected "
        "-- the numbers agree -- but no row is acceptable evidence in this state, so this is FAIL, "
        "not UNPROVEN, and never a pass"
    ), {
        "record": "a0/conformance/report.json#runtimes.<runtime>.checks[measurement-attestation]",
        "identity_verdict": verdict_name,
        "executed_identity": block.get("executed_identity"),
        "oid": envelope.get(run_field) or check.get(run_field),
        "harness": "a0/conformance/conformance.py",
        "report_sha256": None,
        "row_attestation_verdicts": row_verdicts,
        **{k: v for k, v in negatives.items() if v},
    }


def a01_attested(runtime: str, report_sha: str, report: dict = None,
                 require_report_sha: bool = True, root: Path = None) -> dict:
    """Resolve `a0_1_attested` by walking the declared sources in order. Total; fails closed."""
    root = root or ROOT
    contract = load(ATTESTED_CONTRACT) or {}
    sources = contract.get("record_sources") or []
    required = contract.get("required_fields") or []
    searched, rejected = [], []
    entry = ((report or {}).get("runtimes") or {}).get(runtime) or {}

    for spec in sources:
        where = str(spec.get("where", "")).replace("<runtime>", runtime)
        kind = spec.get("kind", "file")
        searched.append(where)

        if kind == "runtime_check":
            check = next(
                (c for c in entry.get("checks") or [] if c.get("check_id") == spec.get("check_id")),
                None,
            )
            if check is None:
                rejected.append(f"{where}: the runner emitted no {spec.get('check_id')!r} check")
                continue
            value, detail, extra = _resolve_runtime_check(check, spec, where, entry)
            if value:
                return component(value, "a0/conformance/report.json", detail,
                                 "read_from_source", **extra)
            rejected.append(detail)
            continue

        if kind == "report_block":
            payload = entry
            for key in spec.get("block_path") or []:
                payload = (payload or {}).get(key) if isinstance(payload, dict) else None
            if not isinstance(payload, dict) or not payload:
                rejected.append(f"{where}: no such block in the report")
                continue
        else:  # file
            payload = None
            for path in _attested_files(runtime, root):
                doc = load(path) or {}
                if doc.get("runtime") not in (None, runtime):
                    rejected.append(f"{rel(path)}: runtime field is {doc.get('runtime')!r}")
                    continue
                payload = doc
                where = rel(path)
                searched.append(where)
                break
            if payload is None:
                continue
            if require_report_sha and payload.get("report_sha256") != report_sha:
                rejected.append(
                    f"{where}: pins a different a0/conformance/report.json (not the A0.1 re-run)")
                continue

        value, detail, extra = _resolve_verdict_payload(payload, spec, where)
        if value:
            extra.setdefault("report_sha256", report_sha)
            return component(value, "a0/conformance/report.json", detail,
                             "read_from_source", **extra)
        rejected.append(detail)

    return component(
        "UNPROVEN",
        rel(ATTESTED_CONTRACT),
        "no harness attestation for this runtime on any declared source, so the identity of the "
        "bytes it executed is UNMEASURED. Behavioural agreement with E* on C* is not a substitute "
        "(the observational-equivalence mutant agrees bit-for-bit and omits the identity fields). "
        "This fails T_A1",
        "verified_by_running",
        record_sources=[s.get("where") for s in sources],
        required_fields=required,
        sources_searched=searched,
        rejected_sources=rejected,
        blocks=["R3_a0_1_attested"],
        to_settle=(
            "wire the D3 harness: it owns the reference value and issues the OID measurement token "
            "(a0/envelope/envelope.py), the runtime still evaluates through its own path, and each "
            "runtime must submit an attestation of the bytes it executed. Then re-run A0.1 with the "
            "envelope ON, so the report carries the `measurement-attestation` check. "
            "Contract: a0/qualification/attested-a0-1.contract.json"
        ),
    )


def _present(value) -> bool:
    return value not in (None, "", [], {})


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
# A0.2 bridge (D2): the score->selection path exercised inside the runtime's OWN real campaign.
#
# This replaces the former `a0_2_e2e` component. D2 sharpens it: "a model-lane round happened" is
# not the question -- the question is whether the frozen evaluator's score reached the runtime's own
# selection state and moved the search, with the runtime's own loop in the chair. A round that was
# attempted and did not complete is ATTEMPTED, never PASS.


def a02_bridge(runtime: str, verdicts: dict) -> dict:
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
            "PASS" if ok else "UNPROVEN",
            [rel(live), "a0/runtimes/simpleloop/out/cli-lane-codex-live3.log",
             "a0/runtimes/simpleloop/out/cli-lane/codex-live3/run_meta.json"],
            f"SimpleLoop's own loop ran two real model rounds; a real agent-authored candidate was "
            f"scored by E* ({scalar}, best C* member = 2.4519) and the champion changed on that "
            f"score; audited as {claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            rounds=["codex-live3", "codex-live4"],
            detail=f"champion_id={doc.get('champion_id')}, champion_scalar={scalar}",
            bridge_kind="real campaign round driven by SimpleLoop's own loop (argv reaches E*)",
        )
    if runtime == "kapso":
        path = ROOT / "a0/runtimes/kapso/runs/bridge-2round/real/verification.json"
        doc = load(path) or {}
        ok = doc.get("verdict") == "bridge_verified"
        n_checks = len(doc.get("checks") or [])
        n_ok = sum(1 for c in (doc.get("checks") or []) if c)
        return component(
            "PASS" if ok else "UNPROVEN",
            [rel(path), "a0/runtimes/kapso/BRIDGE-2ROUND.md",
             "a0/runtimes/kapso/runs/e2e-real/e2e_verification.json"],
            f"a two-round real campaign with the runtime's own selection in the chair: E* -> "
            f"node.score -> node_history -> _select_parent -> parent_branch, resumed from a "
            f"checkpoint in a new process; verdict={doc.get('verdict')}, {n_ok}/{n_checks} checks "
            f"true; audited as {claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            detail=f"verdict={doc.get('verdict')}",
            bridge_kind="real KAPSO campaign; KAPSO's own selector picked the deliverable",
            scope_note=(
                "the bridge exercises the real path but does not separate 'the score VALUE' from "
                "'recency/existence' as the driver -- that separation is what the A0.2 mechanism "
                "scenarios are for (declared by the author, confirmed by the auditor)"
            ),
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
            "PASS" if completed else "ATTEMPTED",
            ["a0/runtimes/eve/out/run002/real_round.json",
             "a0/runtimes/eve/out/run003/real_round.json",
             "a0/runtimes/eve/out/run004/real_round.json"],
            f"{len(rounds)} real codex-backed rounds reached iteration-complete, but none wrote back "
            f"an agent-authored solution.py (every post-round solver is the prefill baseline "
            f"18bacee4...), so the score never reached EvE's own selection state; audited as "
            f"{claim} = {audited}",
            "read_from_source",
            audited_claim=claim,
            audited_verdict=audited,
            rounds=rounds,
            bridge_kind="no completed campaign round",
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
        "ATTEMPTED" if planning_real and no_round else "UNPROVEN",
        [rel(path), rel(stage), "a0/runtimes/loreley/llm-round/bounded_round.log"],
        "a real codex planning call succeeded (144.1 s) but the coding call exceeded its 480 s budget "
        f"and the round watchdog stopped the job, so no evaluation and no archive write happened; "
        f"audited as {claim} = {audited}",
        "read_from_source",
        audited_claim=claim,
        audited_verdict=audited,
        detail="planning real, no evaluation, no archive write, evolution_jobs status=RUNNING",
        bridge_kind="planning reached the real model; the score never entered Loreley's archive",
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
# MRC (D2 clause 6): is the model route frozen?


def _mrc_covering_routes(runtime: str) -> list:
    covering = []
    for path in sorted(MRC_DECLARATIONS.glob("*.mrc.json")):
        doc = load(path) or {}
        adapters = ((doc.get("components") or {}).get("RuntimeAdapters") or {}).get("adapters") or []
        if any(a.get("runtime") == runtime for a in adapters):
            covering.append((path, doc))
    return covering


def mrc_component(runtime: str) -> dict:
    covering = _mrc_covering_routes(runtime)
    if not covering:
        return component(
            "ABSENT",
            rel(MRC_FROZEN_ROUTES),
            f"no declaration under a0/mrc/declarations/ covers runtime {runtime!r}",
            "verified_by_running",
            declarations=[],
            to_settle="declare the route this runtime will run on and freeze it against frozen_routes.json",
        )
    import subprocess

    validated, failed = [], []
    for path, doc in covering:
        proc = subprocess.run(
            [sys.executable, str(MRC_CLI), "validate", "--mrc-file", str(path),
             "--frozen", str(MRC_FROZEN_ROUTES)],
            capture_output=True, text=True, cwd=str(MRC_CLI.parent), timeout=300,
        )
        record = {
            "declaration": rel(path),
            "route_id": doc.get("route_id"),
            "mrc_star": doc.get("mrc_star"),
            "validator_exit": proc.returncode,
            "validator_output": (proc.stdout or proc.stderr or "").strip().splitlines()[-1:],
        }
        (validated if proc.returncode == 0 else failed).append(record)

    value = "FROZEN" if validated else "PRESENT_UNFROZEN"
    routes = [r["route_id"] for r in validated] or [r["route_id"] for r in failed]
    caveats = []
    if len(validated) > 1:
        caveats.append(
            {
                "caveat": "more than one covering route validates; the A1 route CHOICE among them is not frozen here",
                "status": "OPEN decision (STATUS.md §9 item 2, D4)",
                "evidence": [r["declaration"] for r in validated],
                "to_settle": "record the chosen lane per runtime in the freeze document",
            }
        )
    return component(
        value,
        [rel(MRC_FROZEN_ROUTES)] + [r["declaration"] for r in (validated or failed)],
        f"{len(validated)}/{len(covering)} covering declaration(s) validate against frozen_routes.json "
        f"(re-derived by `python3 a0/mrc/mrc.py validate`); routes={routes}",
        "verified_by_running",
        validated=validated,
        failed=failed,
        route_ids=routes,
        frozen_routes_digest_source=rel(MRC_FROZEN_ROUTES),
        caveats=caveats,
    )


# --------------------------------------------------------------------------------------


def build() -> dict:
    report = load(CONFORMANCE)
    if report is None:
        raise SystemExit(f"missing {rel(CONFORMANCE)}; run `cd a0/conformance && python3 conformance.py run`")
    verdicts = load(VERDICT_JSON) or {}
    report_sha = sha256_file(CONFORMANCE)

    runtimes = {}
    for runtime in RUNTIMES:
        measured, adapted = a01_components(runtime, report)
        attested = a01_attested(runtime, report_sha, report)
        mechanism = a02_mechanism(runtime, verdicts)
        bridge = a02_bridge(runtime, verdicts)
        closure = closure_component(runtime)
        mrc = mrc_component(runtime)
        q_r = {
            "a0_1_measured": measured,
            "a0_1_adapted": adapted,
            "a0_1_attested": attested,
            "a0_2_mechanism": mechanism,
            "a0_2_bridge": bridge,
            "closure": closure,
            "mrc": mrc,
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
            "a per-runtime qualification vector Q_r and one substantive eligibility predicate, so a "
            "partial result can never be diluted by siblings that passed (external review point 8); "
            "the corrected EvE A0.1 label PARTIAL -- 5/14 measured, never PASS (point 2); and the "
            "redefinition D2 asks for: T_A1 (harness-attested A0.1, A0.2 mechanism + bridge, closure, "
            "frozen MRC) with the old lenient vector renamed T_exploratory and scoped to "
            "integration/pilot/debug only"
        ),
        "review_basis": {
            "point_2": "A0.1 for EvE must read `PARTIAL -- 5/14 measured`, never `PASS`",
            "point_8": "a single global A0 PASS is the wrong output; Q_r and Eligible(r) = f(Q_r)",
            "D1": "an interpreter mismatch is its own verdict (EXECUTION_ENV_DRIFT), never 'the "
                  "evaluator behaviour disagrees' -- landed",
            "D2": "the strict/literal threshold pair is replaced by T_A1; the lenient vector is "
                  "renamed T_exploratory and scoped to integration/pilot/debug",
            "D3": "identity is a harness measurement with fail-closed omission -- landed; this "
                  "predicate reads its output (`measurement-attestation`) and fails closed",
        },
        "two_axes": {
            "what": (
                "since D3 the conformance runner keeps two axes apart, and Q_r must not merge them: "
                "the MEASUREMENT axis (`a0_1_measured` + `a0_1_adapted`) is whether the runtime's own "
                "evaluator interface produced a fresh verdict the runner compared against E*; the "
                "ACCEPTANCE axis (`a0_1_attested`) is whether the row echoes the harness measurement "
                "token and attests the bytes it executed."
            ),
            "why_it_matters": (
                "KAPSO, EvE and Loreley agree with E* on the measurement surface (14/14, 14/14 and "
                "5/14 measured) and are nonetheless non-accepting: 14 x MISSING_ATTESTATION. Folding "
                "that into the measurement component would report 'this runtime's measurement is "
                "wrong' when the truth is 'this runtime's evidence is missing'. A measurement error "
                "and a missing token are different findings with different remedies."
            ),
            "runner_vocabulary": (
                "the runner states the same separation: a0_1.basis ('the attestation verdict is a "
                "separate axis: it decides whether the row is acceptable evidence, never whether the "
                "runtime measured it'), and the E-r-equals-E-star check's `measurement_agreeing` / "
                "`measurement_disagreeing_candidates` fields."
            ),
            "in_q_r": (
                "`a0_1_measured.state` is derived from `rows[].verdict_before_attestation` and is the "
                "measurement state; the runner's folded state/label (which since D3 includes the "
                "acceptance axis) is carried as `runner_acceptance_state` on the same component. "
                "`a0_1_attested` carries the acceptance verdict."
            ),
        },
        "provenance_classes": {
            "verified_by_running": "this workstream executed the thing that produced the evidence",
            "read_from_source": "the value is read out of a stored artifact produced by another workstream",
            "inferred": "derived by rule from other components, not directly observed",
        },
        "component_domains": {
            "a0_1_measured": "`<measured>/<total>`; `state` in PASS | PARTIAL | FAIL | PENDING | BLOCKED. "
                             "`state` is the MEASUREMENT axis; `runner_acceptance_state` carries the "
                             "runner's folded state, which since D3 also folds in the acceptance axis",
            "a0_1_adapted": "`<adapted>/<total>`; `all_declared_synthetic` must be true for acceptance",
            "a0_1_attested": "PASS | FAIL | UNPROVEN -- the ACCEPTANCE axis. "
                             "contract: a0/qualification/attested-a0-1.contract.json",
            "a0_2_mechanism": "PASS | FAIL | UNPROVEN",
            "a0_2_bridge": "PASS | ATTEMPTED | UNPROVEN | NONE (replaces the former a0_2_e2e)",
            "closure": "CLOSED | CONDITIONAL | OPEN | UNPROVEN",
            "mrc": "FROZEN | PRESENT_UNFROZEN | ABSENT",
        },
        "attested_a0_1": load(ATTESTED_CONTRACT),
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
            "main_arm_set": "R_A1^main = {r : Eligible(r; T_A1)}",
            "rules": RULES,
            "threshold_vectors": THRESHOLD_VECTORS,
            "exclusion_is_not_permanent": (
                "r not-in R_A1^main while any component is unmet. It is not a judgement on the "
                "runtime: it names missing evidence, and the runtime re-enters the moment the "
                "evidence exists"
            ),
            "screen_is_a_different_object": (
                "`|R_1| >= 1` (plan:490) is a CANDIDATE SCREEN over runtimes: it answers 'may the "
                "study continue at all?'. Eligible(r) answers 'may THIS runtime's numbers be used in "
                "an A1 statistic?'. They are not the same object, and `|R_1| >= 1` does not imply "
                "that any runtime is in R_A1^main"
            ),
        },
        "runtimes": runtimes,
    }

    evaluation = {vector: evaluate_all(qualification, vector) for vector in THRESHOLD_VECTORS}
    qualification["evaluation"] = evaluation
    qualification["eligible_set"] = {
        vector: sorted(
            runtime for runtime, verdict in evaluation[vector].items() if verdict["eligible"]
        )
        for vector in THRESHOLD_VECTORS
    }
    qualification["key_metrics"] = key_metrics(qualification)
    qualification["screen"] = screen_block(report, runtimes)
    qualification["unproven"] = unproven_block(runtimes)
    qualification["rejected"] = rejected_block(runtimes)
    return qualification


def screen_block(report: dict, runtimes: dict) -> dict:
    v = report.get("verdicts") or {}
    a0_1_pass = v.get("r_1_a0_1_only") or []
    a0_1_partial = v.get("r_1_a0_1_partial") or []
    both = sorted(
        r for r, e in runtimes.items()
        if e["Q_r"]["a0_1_measured"].get("state") in ("PASS", "PARTIAL")
        and e["Q_r"]["a0_2_mechanism"].get("value") == "PASS"
    )
    return {
        "what": "the candidate screen, not the eligibility predicate",
        "r_1_a0_1_only": a0_1_pass,
        "r_1_a0_1_partial": a0_1_partial,
        "screen_source": "a0/conformance/report.json#verdicts (the runner owns the A0.1 half)",
        "screen_counts": {f"n_{k}": v.get(f"n_{k}") for k in ("pass", "partial", "fail", "pending", "blocked")},
        "screen_uses": "the runner's ACCEPTANCE state (PASS), so a runtime that measured every row "
                       "but did not attest it is not in r_1_a0_1_only",
        "r_1_derived_if_a0_2_mechanism_counts": both,
        "r_1_derived_note": (
            "DERIVED here from `a0_1_measured.state in {PASS, PARTIAL} and a0_2_mechanism == PASS`, "
            "i.e. from the MEASUREMENT axis, which is deliberately not the screen's axis; the "
            "authoritative A0.2 judgement is owned by the A0.2 workstream (a0/acceptance), so treat "
            "this as an upper bound on R_1"
        ),
        "screen_passes": len(a0_1_pass) >= 1 or len(a0_1_partial) >= 1,
        "screen_rule": "|R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2",
        "not_the_same_as_eligibility": (
            "a runtime can be in the screen set and still not in R_A1^main. In the other direction "
            "the axes must not be mixed: a runtime whose MEASUREMENT is complete but whose "
            "ACCEPTANCE failed (KAPSO, Eve, Loreley: 14 x MISSING_ATTESTATION) is out of both, and "
            "the reason it is out is R3_a0_1_attested, never a measurement rule"
        ),
    }


UNPROVEN_MARKERS = ("UNPROVEN", "NONE", "ABSENT", "ATTEMPTED")


def rejected_block(runtimes: dict) -> list:
    """Components that FAILED an axis, as opposed to never having been established.

    Kept separate from `unproven` on purpose: 'no evidence' and 'evidence that contradicts' are
    different findings. A FAIL here is a decision the runner already made (e.g. D3's
    MISSING_ATTESTATION); nothing in this file is allowed to soften it, and nothing in this block
    is allowed to read as a measurement error.
    """
    items = []
    for runtime, entry in runtimes.items():
        for name, comp in entry["Q_r"].items():
            if comp.get("value") != "FAIL":
                continue
            items.append(
                {
                    "runtime": runtime,
                    "component": name,
                    "value": comp["value"],
                    "identity_verdict": comp.get("identity_verdict"),
                    "status": "FAIL -- an axis was decided against this runtime, not left unproven",
                    "justification": comp.get("justification"),
                    "evidence": comp.get("evidence"),
                    "to_settle": comp.get("to_settle"),
                }
            )
    return items


def unproven_block(runtimes: dict) -> list:
    items = []
    for runtime, entry in runtimes.items():
        for name, comp in entry["Q_r"].items():
            if comp.get("value") in UNPROVEN_MARKERS or (
                comp.get("value") in ("PARTIAL",) and name == "a0_1_measured"
            ):
                items.append(
                    {
                        "runtime": runtime,
                        "component": name,
                        "value": comp["value"],
                        "status": "not established at the level T_A1 requires",
                        "evidence": comp["evidence"],
                        "to_settle": comp.get("to_settle"),
                    }
                )
            for caveat in comp.get("caveats") or []:
                status = str(caveat.get("status", ""))
                if any(marker in status for marker in ("UNPROVEN", "NOT RECONCILED", "OPEN decision")):
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
    return items


def strip_volatile(doc: dict) -> dict:
    doc = json.loads(json.dumps(doc))
    doc.pop("generated_at", None)
    return doc


# --------------------------------------------------------------------------------------
# self-test for the D3 fail-closed resolution, so the interface is checkable before the
# producer exists. No tree access: `_resolve_attestation` is a pure function of a payload.

ATTESTATION_SELF_TEST_CASES = [
    (
        "positive verdict with the executed-bytes identity and the OID present",
        {"identity_verdict": "IDENTICAL", "executed_identity": "sha256:abc", "oid": "sha256:def"},
        "PASS",
    ),
    (
        "a contradictory identity is FAIL, never a soft pass",
        {"identity_verdict": "MISMATCH", "executed_identity": "sha256:abc", "oid": "sha256:def"},
        "FAIL",
    ),
    (
        "NOT_SUBMITTED is FAIL (the runtime was asked and did not answer with an identity)",
        {"identity_verdict": "NOT_SUBMITTED"},
        "FAIL",
    ),
    (
        "a positive verdict with no OID token does not establish identity",
        {"identity_verdict": "IDENTICAL", "executed_identity": "sha256:abc"},
        None,
    ),
    (
        "a positive verdict with no executed-bytes identity does not establish identity",
        {"identity_verdict": "IDENTICAL", "oid": "sha256:def"},
        None,
    ),
    ("an omitted verdict is UNPROVEN, not PASS", {"oid": "x", "executed_identity": "y"}, None),
    ("a verdict outside the declared domain does not decide", {"identity_verdict": "PROBABLY"}, None),
]


def self_test() -> int:
    spec = {
        "identity_verdict_field": "identity_verdict",
        "positive": ["IDENTICAL", "PASS", "REALIZED"],
        "negative": ["MISMATCH", "NOT_SUBMITTED", "NOT_REALIZED", "FAIL",
                     "MISSING_ATTESTATION", "MISSING_IDENTITY"],
        "executed_identity_fields": ["executed_identity", "attestation_digest"],
        "oid_field": "oid",
        "pins_current_report": True,
    }
    problems = []
    for why, payload, want in ATTESTATION_SELF_TEST_CASES:
        value, detail, _ = _resolve_verdict_payload(payload, spec, "synthetic")
        if value != want:
            problems.append(f"{why}: resolved {value!r} != {want!r} ({detail})")

    # the D3 runner's own per-runtime check, in each of its four states
    check_spec = {
        "check_id": "measurement-attestation", "required_field": "required", "ok_field": "ok",
        "envelope_field": "envelope", "harness_run_field": "harness_run_id",
        "positive_candidates_field": "attested_candidates",
        "negative_candidate_fields": ["missing_attestation_candidates",
                                      "missing_identity_candidates",
                                      "mismatch_attestation_candidates"],
    }
    ok_check = {
        "check_id": "measurement-attestation", "required": True, "ok": True,
        "envelope": {"harness_run_id": "run-1", "nonce": "n"},
        "attested_candidates": ["c01_good_hex"],
        "missing_attestation_candidates": [], "missing_identity_candidates": [],
        "mismatch_attestation_candidates": [],
    }
    check_cases = [
        ("the runner's own passing check", ok_check, "PASS"),
        (
            "the runner's check failing on a missing token",
            dict(ok_check, ok=False, attested_candidates=[],
                 missing_attestation_candidates=["c01_good_hex"]),
            "FAIL",
        ),
        (
            "a run made with the token requirement OFF establishes nothing",
            dict(ok_check, required=False),
            None,
        ),
        (
            "a check that reports ok but names no harness run does not decide",
            dict(ok_check, envelope={}),
            None,
        ),
    ]
    for why, check, want in check_cases:
        value, detail, _ = _resolve_runtime_check(check, check_spec, "synthetic")
        if value != want:
            problems.append(f"{why}: resolved {value!r} != {want!r} ({detail})")

    # a standalone file record must pin the report it describes. Exercised end-to-end through
    # `a01_attested` in a temp tree, so the source order and the pinning rule are both covered.
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory(prefix="a0-attested-selftest-") as tmp:
        drop = _Path(tmp) / "a0/qualification/evidence/a0_1_attested/simpleloop"
        drop.mkdir(parents=True, exist_ok=True)
        rec = drop / "record.json"
        base = {
            "schema": "a0.attested-a0-1/v1", "runtime": "simpleloop",
            "harness": "synthetic", "oid": "sha256:" + "0" * 64,
            "executed_identity": "sha256:" + "1" * 64, "identity_verdict": "IDENTICAL",
            "report_sha256": "other",
        }
        trials = [
            ("a standalone record pinning a different A0.1 run is ignored",
             dict(base, report_sha256="other"), "UNPROVEN"),
            ("a standalone record pinning the current A0.1 run is accepted",
             dict(base, report_sha256="R" * 64), "PASS"),
            ("a standalone record that contradicts the identity is FAIL",
             dict(base, report_sha256="R" * 64, identity_verdict="MISMATCH"), "FAIL"),
            ("a standalone record with no OID does not establish identity",
             dict(base, report_sha256="R" * 64, oid=None), "UNPROVEN"),
        ]
        for why, payload, want in trials:
            rec.write_text(json.dumps(payload))
            got = a01_attested("simpleloop", "R" * 64, {}, root=_Path(tmp))
            if got["value"] != want:
                problems.append(f"{why}: resolved {got['value']!r} != {want!r}")

    contract = load(ATTESTED_CONTRACT) or {}

    if not contract.get("record_sources"):
        problems.append("the contract declares no record sources")
    if not contract.get("domain_rule", {}).get("UNPROVEN"):
        problems.append("the contract does not say what UNPROVEN means")
    if "NOT_SUBMITTED" not in json.dumps(contract.get("record_sources")):
        problems.append("the contract does not classify NOT_SUBMITTED as FAIL")
    if not any(s.get("kind") == "runtime_check" for s in contract.get("record_sources") or []):
        problems.append("the contract does not name the D3 runner check as a source")

    total = len(ATTESTATION_SELF_TEST_CASES) + len(check_cases) + len(trials)
    print(f"attestation resolution self-test: {total} cases "
          f"over {len(contract.get('record_sources') or [])} declared sources")
    for problem in problems:
        print(f"  ! {problem}")
    print("self-test:", "ok" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_qualification.py", description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(HERE / "qualification.json"))
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--check", action="store_true", help="re-derive and diff against --out; exit 1 on drift")
    parser.add_argument("--self-test", action="store_true",
                        help="exercise the D3 fail-closed attestation resolution on synthetic payloads")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

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
        role = THRESHOLD_VECTORS[vector]["role"]
        print(f"  {vector} ({role}): |Eligible| = {len(names)}: {names or 'none'}")
    metrics = built["key_metrics"]
    print(f"  R_A1^main = {metrics['R_A1_main'] or '{} (empty)'}")
    return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


if __name__ == "__main__":
    raise SystemExit(main())
