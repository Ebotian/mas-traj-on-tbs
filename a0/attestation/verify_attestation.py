#!/usr/bin/env python3
"""Verify an execution/load attestation against a declared evaluator identity.

Two questions, answered separately, plus the third leg that makes the first two
mean anything:

  Q1  does it recompute?           Rebuild `EID_execution` from the attestation's
                                   own payload with an independently written
                                   canonicalizer, and (when given) compare it to
                                   an externally declared value.
  Q2  does its semantic component  Compare `EID_semantic` to the frozen value,
      match the frozen value?      and -- when the repository is reachable --
                                   recompute it from the live inputs with the
                                   contract owner's own code.
  Q3  is the declared identity     The realization check: were the declared
      actually realized?           evaluator sources the artifacts that ran? Was
                                   anything loaded from outside the declared
                                   sources? Did the two invocation routes agree?

Q3 exists because Q1 and Q2 alone are not sufficient, and the review's `⊨` is not
implementable as written: an attestation can recompute perfectly and carry the
frozen `EID_semantic` while the process that produced the numbers executed
different bytes.  That is the gap this workstream exists to close, so the
verifier reports it as its own verdict instead of folding it into "semantic".

This file deliberately does not import `attest_lib.py`: a verifier that shares
the producer's serializer cannot detect a bug in it.  `selftest.py` checks the
two implementations agree.

Exit codes: 0 all three verdicts good; 1 does not recompute; 2 semantic
mismatch; 3 not realized; 4 malformed attestation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

FROZEN_EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"
# E*'s own scheme for its source files (`e_star.py::evaluator_source_digest`),
# reimplemented here so the self-reported value is checked rather than trusted.
EXPECTED_SELF_REPORTED_SOURCE_SHA256 = "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532"
COMPONENTS = ("EvaluatorSource", "DependencyLock", "DataManifest", "Config", "MetricDefinition")
DOMAIN = "a0/attestation/v1"


def canonical_json(obj) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def domain_digest(domain: str, payload: bytes) -> str:
    return sha256_hex(domain.encode("ascii") + b"\x00" + payload)


def recompute_eid_execution(payload: dict) -> str:
    return domain_digest(f"{DOMAIN}/EID_execution", canonical_json(payload))


def recompute_eid_star(components: dict) -> str:
    """`a0/contract/evalcontract.py`'s own combination step, reimplemented."""
    return domain_digest(
        "a0/evalcontract/v1/EID*", canonical_json({name: components[name] for name in COMPONENTS})
    )


def e_star_self_reported_digest(source_records: list[dict]) -> str:
    """`e_star.py::evaluator_source_digest`, reimplemented.

    E*'s canonical JSON differs from the contract's: pretty-printed, sorted keys,
    and `ensure_ascii=False`.  The entry order follows E*'s `SOURCE_FILES`
    (`e_star.py`, `e_star_child.py`), which sorting by file name reproduces.
    """
    entries = [
        {"name": Path(record["origin"]).name, "sha256": record["file_sha256"],
         "bytes": record["file_size"]}
        for record in sorted(source_records, key=lambda item: Path(item["origin"]).name)
    ]
    text = json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return sha256_hex(text.encode("utf-8"))


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def check(self, question: str, name: str, ok, detail=None, severity="gate") -> None:
        self.checks.append(
            {"question": question, "name": name, "passed": ok, "detail": detail, "severity": severity}
        )

    def failed(self, question: str) -> list[dict]:
        return [c for c in self.checks if c["question"] == question and c["passed"] is not True]

    def gate_failures(self, question: str) -> list[dict]:
        return [c for c in self.failed(question) if c["severity"] == "gate"]


def verify(document: dict, *, declared_eid_star: str | None, declared_eid_execution: str | None,
           repo_root: Path | None) -> Report:
    report = Report()
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("attestation has no payload object")

    # ---- Q1: does it recompute? -----------------------------------------
    recomputed = recompute_eid_execution(payload)
    attested = document.get("eid_execution")
    report.check("Q1", "eid_execution recomputes from the payload",
                 recomputed == attested, {"recomputed": recomputed, "attested": attested})
    if declared_eid_execution:
        report.check("Q1", "recomputed value equals the externally declared EID_execution",
                     recomputed == declared_eid_execution,
                     {"declared": declared_eid_execution})

    # ---- Q2: does the semantic component match the frozen value? ---------
    semantic = document.get("eid_semantic")
    components = document.get("eid_semantic_components")
    frozen = declared_eid_star or FROZEN_EID_STAR
    report.check("Q2", "EID_semantic equals the declared/frozen value", semantic == frozen,
                 {"attested": semantic, "frozen": frozen})
    report.check("Q2", "EID_semantic equals the document's own top-level field",
                 semantic == payload.get("eid_semantic"))
    if isinstance(components, dict) and all(name in components for name in COMPONENTS):
        report.check("Q2", "EID_semantic is the digest of the five components it carries",
                     recompute_eid_star(components) == semantic)
        declared_components = payload.get("declared_component_digests")
        if declared_components:
            report.check("Q2", "the live component digests equal the declared ones",
                         components == declared_components,
                         {name: {"live": components[name], "declared": declared_components.get(name)}
                          for name in COMPONENTS if components[name] != declared_components.get(name)})
        else:
            report.check("Q2", "the payload carries the declared component digests", False,
                         "payload.declared_component_digests is absent")
    else:
        report.check("Q2", "EID_semantic carries all five components", False, components)

    # independent recomputation from the live tree, using the owner's code
    if repo_root:
        live = _recompute_live(repo_root, report)
        if live is not None:
            report.check("Q2", "live recomputation of EID_semantic agrees with the attestation",
                         live["eid_star"] == semantic, {"live": live["eid_star"]})
            report.check("Q2", "live recomputation of EID_semantic agrees with the frozen value",
                         live["eid_star"] == frozen)
            report.check("Q2", "every live component digest equals the attested component digest",
                         live["components"] == components,
                         {name: {"live": live["components"][name], "attested": (components or {}).get(name)}
                          for name in COMPONENTS
                          if live["components"][name] != (components or {}).get(name)})

    # ---- Q3: is the declared identity realized by this execution? --------
    artifacts = payload.get("loaded_artifacts", {})
    execution = payload.get("evaluator_execution", {})
    declared_paths = artifacts.get("declared_source_paths") or []
    declared_entry = artifacts.get("declared_evaluator_entry")
    records = (artifacts.get("evaluator_sources") or []) + (artifacts.get("evaluator_child_sources") or [])

    report.check("Q3", "no module was loaded from outside the declared sources and the runtime",
                 artifacts.get("foreign_modules") == [],
                 artifacts.get("foreign_modules"))
    report.check("Q3", "no sys.path entry shadows a stdlib name",
                 artifacts.get("shadowing_hazards") == [], artifacts.get("shadowing_hazards"))
    report.check("Q3", "the authoritative CLI route and the captured route agree",
                 execution.get("routes_agree") is True,
                 {"authoritative": execution.get("authoritative_route"),
                  "captured": execution.get("capture_route")})

    for declared in declared_paths:
        matching = [record for record in records if record.get("declared_path") == declared]
        if not matching:
            report.check("Q3", f"declared source {declared} was loaded by the evaluator", False,
                         "no loaded module has this declared path")
            continue
        for record in matching:
            report.check("Q3", f"{declared}: loaded from the declared path",
                         record.get("origin") == declared,
                         {"origin": record.get("origin")})
            report.check("Q3", f"{declared}: on-disk bytes match the declared hash",
                         record.get("declared_match") is True,
                         {"file_sha256": record.get("file_sha256"),
                          "declared_sha256": record.get("declared_sha256")})
            report.check("Q3", f"{declared}: the bytecode that ran matches the declared source",
                         record.get("bytecode_matches_source") is True,
                         {"loaded_code_sha256": record.get("loaded_code_sha256"),
                          "fresh_compile_sha256": record.get("fresh_compile_sha256"),
                          "pyc_path": record.get("pyc_path"),
                          "loaded_from_cache_path": record.get("loaded_from_cache_path")})
    if declared_entry:
        entry_records = [record for record in records if record.get("is_entry")]
        report.check("Q3", "the entry module that ran is the declared entry file",
                     any(record.get("origin") == declared_entry for record in entry_records),
                     {"declared_entry": declared_entry,
                      "entries_seen": [record.get("origin") for record in entry_records]})

    # the evaluator's self-report, recomputed here rather than believed
    self_reported = execution.get("self_reported_evaluator_source_sha256")
    report.check("Q3", "the evaluator's self-reported source digest equals E*'s frozen value",
                 self_reported == EXPECTED_SELF_REPORTED_SOURCE_SHA256,
                 {"self_reported": self_reported})
    declared_reports = [record for record in records if record.get("is_entry")]
    if declared_reports and all(record.get("file_sha256") for record in declared_reports):
        report.check("Q3", "the self-reported digest follows from the declared file hashes",
                     e_star_self_reported_digest(declared_reports) == self_reported,
                     {"recomputed": e_star_self_reported_digest(declared_reports)})
    report.check(
        "Q3",
        "the self-report is not contradicted by the bytecode that ran",
        all(record.get("bytecode_matches_source") is not False for record in records),
        "a frozen self-reported hash next to bytecode that does not match its source is exactly "
        "the declared-vs-executed gap",
    )

    candidate = payload.get("candidate", {})
    for name, value in (candidate.get("checks") or {}).items():
        report.check("Q3", f"candidate identity check: {name}", value is True, value)
    for record in candidate.get("files") or []:
        report.check("Q3", f"candidate data file {record['path']} matches its declared hash",
                     record.get("declared_match") is not False, record)
    environment = payload.get("environment", {})
    report.check("Q3", "the child environment matches the frozen environment policy",
                 environment.get("child_policy_ok") is True,
                 environment.get("child_policy_checks"))
    report.check("Q3", "no network events during evaluation",
                 (document.get("observations", {}).get("socket_events") or []) == [])

    if execution.get("reference_comparison_applicable"):
        report.check("Q3", "the outcome matches the frozen reference table row for this candidate",
                     execution.get("reference_comparison_matches") is True,
                     {"expected": execution.get("reference_table_row_expected_digest"),
                      "observed": execution.get("authoritative_route", {}).get("outcome_canonical_digest"),
                      "expected_status": execution.get("reference_table_row_expected_status"),
                      "observed_status": execution.get("outcome_status")})
    return report


def _recompute_live(repo_root: Path, report: Report):
    contract_path = repo_root / "a0/contract/evalcontract.py"
    spec_path = repo_root / "a0/tasks/circle-packing/plumbing.contract.proposed.json"
    if not (contract_path.is_file() and spec_path.is_file()):
        report.check("Q2", "live recomputation with the contract owner's code", None,
                     "evalcontract.py or the spec is not present", severity="warn")
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("a0_verify_evalcontract", contract_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    contract = module.build_contract(json.loads(spec_path.read_text(encoding="utf-8")), spec_path, None)
    return {
        "eid_star": contract["eid_star"],
        "components": {name: contract["components"][name]["digest"] for name in COMPONENTS},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="verify_attestation.py", description=__doc__.splitlines()[0])
    parser.add_argument("--attestation", required=True)
    parser.add_argument("--declared-eid-star", default=None,
                        help=f"the frozen semantic identity to check against (default {FROZEN_EID_STAR[:16]}...)")
    parser.add_argument("--declared-eid-execution", default=None,
                        help="an externally registered execution identity to compare against")
    parser.add_argument("--repo-root", default=None,
                        help="repository root; enables independent recomputation of EID_semantic")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.attestation)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"malformed attestation: {exc}", file=sys.stderr)
        return 4

    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    try:
        report = verify(document, declared_eid_star=args.declared_eid_star,
                        declared_eid_execution=args.declared_eid_execution, repo_root=repo_root)
    except ValueError as exc:
        print(f"malformed attestation: {exc}", file=sys.stderr)
        return 4

    q1_fail = report.gate_failures("Q1")
    q2_fail = report.gate_failures("Q2")
    q3_fail = report.gate_failures("Q3")
    verdicts = {
        "Q1_recomputes": "RECOMPUTES" if not q1_fail else "DOES_NOT_RECOMPUTE",
        "Q2_semantic": "SEMANTIC_MATCH" if not q2_fail else "SEMANTIC_MISMATCH",
        "Q3_realization": "REALIZED" if not q3_fail else "NOT_REALIZED",
    }

    if not args.quiet:
        print(f"attestation: {path}")
        print(f"  EID_semantic  {document.get('eid_semantic')}")
        print(f"  EID_execution {document.get('eid_execution')}")
        print()
        for question, title in (("Q1", "does it recompute?"),
                                ("Q2", "does EID_semantic match the frozen value?"),
                                ("Q3", "is the declared identity realized by this execution?")):
            print(f"{question}: {title}")
            for check in [c for c in report.checks if c["question"] == question]:
                mark = {True: "ok  ", False: "FAIL", None: "??  "}[check["passed"]]
                print(f"  [{mark}] {check['name']}")
                if check["passed"] is not True and check["detail"] is not None:
                    print(f"         {json.dumps(check['detail'], sort_keys=True, default=str)[:600]}")
            print()
        for key, value in verdicts.items():
            print(f"{key:<16} {value}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                {"schema": "a0.attestation.verdict/v1", "attestation": str(path), "verdicts": verdicts,
                 "checks": report.checks},
                indent=2, sort_keys=True, default=str,
            ) + "\n",
            encoding="utf-8",
        )

    if q1_fail:
        return 1
    if q2_fail:
        return 2
    if q3_fail:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
