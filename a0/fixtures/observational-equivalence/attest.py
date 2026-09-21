#!/usr/bin/env python3
"""Execution attestation: measure the evaluator that actually ran, out of band.

This is the fixture's own equivalent of `a0/attestation/` (that workstream was
mid-flight when this was written; see REPORT.md, "Second direction").  It exists
to answer exactly one question that the A0.1 checker cannot answer from an
adapter's output:

    were the numbers produced by the evaluator whose identity EID* freezes?

The difference from the conformance checker is not cosmetic.  `conformance.py`
reads identity material *the adapter wrote down* (a `canonical_digest` string, an
optional `E_STAR_MANIFEST` echo).  Here the *harness* chooses the evaluator
files, hashes the bytes it is about to execute, launches those bytes itself,
reads the outcome files it created, and recomputes each outcome's canonical
digest from the file contents.  Nothing in the chain is taken from the adapter.

    attest  --evaluator-dir DIR --out RECORD [--eid-file FILE]
            [--no-stage] [--delay-before-exec SECONDS] [--label NAME]
    verify  --record RECORD --adapter-doc DOC --out VERDICT

`attest` stages the evaluator's declared source files into a private directory
and executes *the staged copies*, so a modification of the original between
hashing and execution cannot change what ran (this is E*'s own trick for
candidate bytes, applied to the evaluator itself).  `--no-stage` skips the copy
and launches the named path directly; that mode exists only to drive the TOCTOU
control in `run_attestation_probe.sh`.

Self-tests printed by every `attest` run, so the measurement cannot be silently
wrong:

  * the frozen E* tree must measure to EID*'s `EvaluatorSource` records, and to
    the `evaluator_source_sha256` frozen in `E_STAR.json`;
  * each outcome file must re-hash to its own `canonical_digest`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
A0 = HERE.parents[1]
TASK = A0 / "tasks" / "circle-packing"
DEFAULT_EID = A0 / "contract" / "out" / "plumbing.EID.json"
DEFAULT_CONTRACT = A0 / "contract" / "evalcontract.py"
DEFAULT_INTERPRETER = TASK / ".venv" / "bin" / "python"
FROZEN_E_STAR_TABLE = TASK / "E_STAR.json"
DEFAULT_MANIFEST = TASK / "C_STAR" / "manifest.json"

THETA = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
         "runtime_budget_ms": 250.0, "timeout_s": 120.0}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def e_star_canonical_json(payload) -> bytes:
    """E*'s own canonical form (indent=2, sort_keys, trailing newline) -- needed to
    recompute `canonical_digest` and `evaluator_source_sha256` independently of E*."""
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def evaluator_source_sha256(records: list[dict]) -> str:
    """E*'s `evaluator_source_digest()`: digest over [(name, sha256, bytes), ...]."""
    entries = [{"name": r["name"], "sha256": r["sha256"], "bytes": r["bytes"]} for r in records]
    return sha256_bytes(e_star_canonical_json(entries))


def load_contract(path: Path):
    spec = importlib.util.spec_from_file_location("evalcontract_readonly", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def eid_records(eid_doc: dict) -> tuple[list[dict], dict, str, dict]:
    component = eid_doc["components"]["EvaluatorSource"]
    declared = component.get("declared") or {}
    records = [
        {"name": r["path"], "sha256": r["sha256"], "bytes": r["size"]}
        for r in component["records"] if r.get("kind") == "file"
    ]
    return records, declared, component["digest"], component


def measure_tree(contract, root: Path, declared: dict) -> list[dict]:
    """The contract's own walker over `root`, with the declared include/exclude."""
    include = tuple(declared.get("include") or ("**/*",))
    exclude = tuple(declared.get("exclude") or ()) + tuple(contract.DEFAULT_EXCLUDES)
    records = contract.collect_tree(Path(root), include, exclude)
    return [{"name": r["path"], "sha256": r["sha256"], "bytes": r["size"]}
            for r in records if r.get("kind") == "file"]


def candidate_rows() -> list[dict]:
    manifest = json.loads(DEFAULT_MANIFEST.read_text())
    return [{"candidate_id": c["candidate_id"], "dir": c["path"],
             "solution_sha256": c["solution_sha256"]} for c in manifest["candidates"]]


def run_evaluator(script: Path, candidate_dir: Path, out_json: Path, state_dir: Path,
                  interpreter: str, theta: dict, cwd: Path) -> dict:
    argv = [interpreter, str(script), "evaluate", "--candidate", str(candidate_dir),
            "--seed", str(theta["seed"]), "--fidelity", str(theta["fidelity"]),
            "--fraction", str(theta["fraction"]), "--n", str(theta["n"]),
            "--runs", str(theta["runs"]), "--runtime-budget-ms", str(theta["runtime_budget_ms"]),
            "--timeout-s", str(theta["timeout_s"]), "--out", str(out_json), "--state-dir", str(state_dir)]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(cwd),
                          timeout=float(theta["timeout_s"]) + 60.0, check=False)
    outcome = json.loads(out_json.read_text()) if out_json.exists() else None
    recomputed = None
    if outcome is not None:
        payload = {k: v for k, v in outcome.items() if k != "canonical_digest"}
        recomputed = sha256_bytes(e_star_canonical_json(payload))
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "outcome_file": str(out_json) if out_json.exists() else None,
        "outcome_file_sha256": sha256_file(out_json) if out_json.exists() else None,
        "status": (outcome or {}).get("status"),
        "objective_value": ((outcome or {}).get("objective") or {}).get("value"),
        "failure_kind": ((outcome or {}).get("failure") or {}).get("kind"),
        "canonical_digest": (outcome or {}).get("canonical_digest"),
        "canonical_digest_recomputed": recomputed,
        "canonical_digest_internally_consistent": bool(outcome) and recomputed == outcome.get("canonical_digest"),
        "outcome_self_reported_source_sha256": (outcome or {}).get("evaluator_source_sha256"),
        "outcome_self_reported_interpreter": (outcome or {}).get("interpreter"),
        "outcome_self_reported_theta_e": (outcome or {}).get("theta_e"),
    }


def cmd_attest(args) -> int:
    evaluator_dir = Path(args.evaluator_dir).resolve()
    script = evaluator_dir / "e_star.py"
    if not script.is_file():
        print(f"attest: no e_star.py under {evaluator_dir}", file=sys.stderr)
        return 2
    eid_doc = json.loads(Path(args.eid_file).read_text())
    expected_records, declared, expected_component_digest, _ = eid_records(eid_doc)
    contract = load_contract(Path(args.contract))

    out_root = Path(args.out).resolve().parent
    stage = out_root / "stage" if args.stage else evaluator_dir
    if args.stage:
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        for rec in expected_records:
            shutil.copy2(evaluator_dir / rec["name"], stage / rec["name"])
    staged_script = stage / "e_star.py"

    # 1. hash the bytes that will be executed (the staged copies, or the named path)
    measured_records = measure_tree(contract, stage, declared)
    measured_source_digest = evaluator_source_sha256(measured_records)
    if args.delay_before_exec:
        print(f"attest: sleeping {args.delay_before_exec}s between hashing and execution "
              f"(TOCTOU-probe hook)", file=sys.stderr)
        time.sleep(float(args.delay_before_exec))

    # 2. execute those bytes over C*, into an attestation-owned state root
    run_root = out_root / "attested-run"
    if run_root.exists():
        shutil.rmtree(run_root)
    (run_root / "outcomes").mkdir(parents=True)
    rows = []
    for cand in candidate_rows():
        cdir = DEFAULT_MANIFEST.parent / cand["dir"]
        measured_candidate = sha256_file(cdir / "solution.py")
        row = run_evaluator(staged_script, cdir, run_root / "outcomes" / f"{cand['candidate_id']}.json",
                            run_root / "state", args.interpreter, THETA, stage)
        row.update({
            "candidate_id": cand["candidate_id"],
            "candidate_dir": str(cdir),
            "candidate_source_sha256_measured": measured_candidate,
            "candidate_source_sha256_matches_manifest": measured_candidate == cand["solution_sha256"],
        })
        rows.append(row)

    # 3. re-hash the executed bytes: a mid-run modification shows up here
    rehashed = measure_tree(contract, stage, declared)
    stage_unchanged = rehashed == measured_records

    # 4. compare against EID*
    identity_ok = measured_records == expected_records
    component_payload = {"root": declared.get("root", "."), "records": [
        {"path": r["name"], "kind": "file", "sha256": r["sha256"], "size": r["bytes"]}
        for r in measured_records
    ]}
    component_digest = contract.component_digest("EvaluatorSource", component_payload)

    frozen = json.loads(FROZEN_E_STAR_TABLE.read_text()).get("evaluator", {})
    record = {
        "schema": "a0.fixture.observational-equivalence.attestation/v1",
        "label": args.label or evaluator_dir.name,
        "eid_document": str(args.eid_file),
        "eid_star": eid_doc.get("eid_star"),
        "interpreter": args.interpreter,
        "staged": bool(args.stage),
        "stage_dir": str(stage),
        "measured_records": measured_records,
        "expected_records": expected_records,
        "measured_evaluator_source_sha256": measured_source_digest,
        "measured_evaluator_source_component_digest": component_digest,
        "expected_evaluator_source_component_digest": expected_component_digest,
        "evaluator_source_matches_eid_star": identity_ok,
        "evaluator_source_component_matches_eid_star": component_digest == expected_component_digest,
        "outcome_self_reports_match_launched_bytes": sorted({
            r["outcome_self_reported_source_sha256"] for r in rows} ) == [measured_source_digest],
        "self_test_frozen_e_source_sha256": (
            "the frozen table's evaluator.evaluator_source_sha256 for E* is "
            f"{frozen.get('evaluator_source_sha256')!r}; this attestor recomputes E*'s source digest as "
            f"{evaluator_source_sha256(expected_records)!r} from EID*'s own records -- equal: "
            f"{evaluator_source_sha256(expected_records) == frozen.get('evaluator_source_sha256')}"
        ),
        "stage_unchanged_after_run": stage_unchanged,
        "outcomes_internally_consistent": all(r["canonical_digest_internally_consistent"] for r in rows),
        "rows": rows,
    }
    verdict = ("ACCEPT: the executed evaluator is the one EID* freezes"
               if identity_ok and stage_unchanged else
               ("REJECT: the executed evaluator's source records are not EID*'s EvaluatorSource"
                if not identity_ok else "REJECT: the executed bytes changed under the run"))
    record["verdict"] = verdict
    Path(args.out).write_text(json.dumps(record, indent=2) + "\n")

    print(f"attestation of {evaluator_dir} (staged={bool(args.stage)}, label={record['label']})")
    print(f"  measured EvaluatorSource component digest : {component_digest}")
    print(f"  EID* EvaluatorSource component digest     : {expected_component_digest}")
    for rec in measured_records:
        match = next((e for e in expected_records if e["name"] == rec["name"]), None)
        print(f"  {rec['name']:<20} measured {rec['sha256']}  expected {match['sha256'] if match else None}"
              f"  {'MATCH' if match and match['sha256'] == rec['sha256'] else 'DIFFER'}")
    print(f"  outcomes re-hash to their own canonical_digest: {record['outcomes_internally_consistent']}")
    print(f"  VERDICT: {verdict}")
    print(f"written: {args.out}")
    return 0 if identity_ok and stage_unchanged else 3


def cmd_verify(args) -> int:
    """Compare an adapter's own A0.1 answer against the attestation record."""
    record = json.loads(Path(args.record).read_text())
    doc = json.loads(Path(args.adapter_doc).read_text())
    rows = {r.get("candidate_id"): r for r in doc.get("candidates") or []}
    problems = []
    if not record["evaluator_source_matches_eid_star"]:
        problems.append(
            "the evaluator the harness measured and executed is NOT the one EID* freezes: measured "
            f"EvaluatorSource component digest {record['measured_evaluator_source_component_digest']} != "
            f"EID*'s {record['expected_evaluator_source_component_digest']}"
        )
    if not record.get("outcome_self_reports_match_launched_bytes", True):
        problems.append("the evaluator's own outcome self-reports a source digest different from the bytes "
                        "the harness executed")
    for row in record["rows"]:
        cid = row["candidate_id"]
        claimed = rows.get(cid)
        if claimed is None:
            problems.append(f"{cid}: the adapter reported no row")
            continue
        if claimed.get("objective_value") != row["objective_value"]:
            problems.append(f"{cid}: adapter objective_value {claimed.get('objective_value')!r} != "
                            f"attested {row['objective_value']!r}")
        if claimed.get("status") != row["status"]:
            problems.append(f"{cid}: adapter status {claimed.get('status')!r} != attested {row['status']!r}")
        if claimed.get("failure_kind") != row["failure_kind"]:
            problems.append(f"{cid}: adapter failure_kind {claimed.get('failure_kind')!r} != "
                            f"attested {row['failure_kind']!r}")
        if claimed.get("canonical_digest") and claimed["canonical_digest"] != row["canonical_digest"]:
            problems.append(f"{cid}: adapter canonical_digest {claimed['canonical_digest']!r} != attested "
                            f"{row['canonical_digest']!r}")
        if claimed.get("source_sha256") and claimed["source_sha256"] != row["candidate_source_sha256_measured"]:
            problems.append(f"{cid}: adapter source_sha256 {claimed['source_sha256']!r} != the bytes the "
                            f"harness fed {row['candidate_source_sha256_measured']!r}")
    verdict = {
        "schema": "a0.fixture.observational-equivalence.attestation-verdict/v1",
        "attestation_record": str(args.record),
        "adapter_doc": str(args.adapter_doc),
        "attested_evaluator_identity_ok": record["evaluator_source_matches_eid_star"],
        "attested_evaluator": {
            "measured_records": record["measured_records"],
            "measured_component_digest": record["measured_evaluator_source_component_digest"],
            "expected_component_digest": record["expected_evaluator_source_component_digest"],
        },
        "adapter_claim_matches_attested_execution": not problems or all(
            "is NOT the one EID* freezes" not in p for p in problems),
        "problems": problems,
        "verdict": "ACCEPT" if not problems else "REJECT",
    }
    Path(args.out).write_text(json.dumps(verdict, indent=2) + "\n")
    print(f"attestation-based check of {args.adapter_doc}")
    print(f"  attested evaluator identity is EID*'s: {record['evaluator_source_matches_eid_star']}")
    for problem in problems:
        print(f"  !! {problem}")
    print(f"  VERDICT: {verdict['verdict']}")
    print(f"written: {args.out}")
    return 0 if verdict["verdict"] == "ACCEPT" else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    at = sub.add_parser("attest")
    at.add_argument("--evaluator-dir", required=True)
    at.add_argument("--out", required=True)
    at.add_argument("--eid-file", default=str(DEFAULT_EID))
    at.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    at.add_argument("--interpreter", default=str(DEFAULT_INTERPRETER))
    at.add_argument("--label", default=None)
    at.add_argument("--stage", dest="stage", action="store_true", default=True)
    at.add_argument("--no-stage", dest="stage", action="store_false")
    at.add_argument("--delay-before-exec", type=float, default=0.0)
    at.set_defaults(func=cmd_attest)

    ve = sub.add_parser("verify")
    ve.add_argument("--record", required=True)
    ve.add_argument("--adapter-doc", required=True)
    ve.add_argument("--out", required=True)
    ve.set_defaults(func=cmd_verify)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
