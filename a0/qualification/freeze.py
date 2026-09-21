#!/usr/bin/env python3
"""The A0 freeze: a frozen qualification vector with per-artifact digests, and a checker.

Why this exists (decision D2, deliverable 2)
--------------------------------------------
`Eligible(r; T_A1)` says which runtimes are admissible. It says nothing about *when*. A0 has to be
frozen before A1 is designed, and "frozen" has to be a measurement rather than a sentence in a
report -- this repository has already lost a revision pin to a field rename, which is exactly the
class of change an assertion cannot catch.

So the freeze document records, for every component of every runtime, the component's own digest
AND the sha256 of every artifact the component was derived from, plus the digest of the predicate
module and of the rules data. `check` recomputes all of them against the tree and reports:

    FROZEN        every artifact and every component is byte-identical to the frozen state
    UNFROZEN      otherwise, with the exact list of what changed

Any component change, any artifact byte, any rules change unfreezes. There is no partial credit.

Commands
--------
    python3 freeze.py fingerprint        # print the fingerprint; writes nothing
    python3 freeze.py arm                # record the CURRENT tree as A0.freeze.candidate.json
                                         # (state ARMED_NOT_FROZEN: a baseline to diff against,
                                         #  not a freeze)
    python3 freeze.py gates [--json]     # the freeze-readiness gates alone
    python3 freeze.py check [--json]     # does the tree still match the frozen/armed document?
    python3 freeze.py self-test          # prove the drift detection mechanically, in a temp tree

    # the single command the coordinator/user runs to freeze (see --help for the guards):
    python3 freeze.py freeze --reason "A0 measurement chain frozen for A1 design"

`freeze` refuses while any gate is red. A runtime may instead be explicitly excluded, with a written
reason, via `--exclude runtime=reason`; an excluded runtime is exempt from the attestation and MRC
gates and is recorded as excluded in the document. Nothing about exclusion is permanent.

Fail-closed: if a gate cannot be evaluated (file missing, subprocess error) it is RED, never green.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

SCHEMA = "a0.freeze/v1"
FROZEN_DOC = HERE / "A0.freeze.json"
CANDIDATE_DOC = HERE / "A0.freeze.candidate.json"

sys.path.insert(0, str(HERE))
from eligibility import (  # noqa: E402
    COMPONENTS,
    MAIN_ARM_VECTOR,
    PREDICATE_VERSION,
    RULES,
    THRESHOLD_VECTORS,
    key_metrics,
)

RUNTIMES = ("simpleloop", "kapso", "eve", "loreley")
QUALIFICATION = "a0/qualification/qualification.json"

# Files the freeze is *about*, beyond whatever the components cite as evidence. The first group is
# the qualification artifact itself; the second is the A0 measurement chain those components describe
# -- the checker, its own fixture runner, the frozen evaluator, the frozen reference table and the
# frozen candidate set. Hashing the checker as well as its output means a change to the runner
# unfreezes the document even before the report is regenerated.
CORE_ARTIFACTS = (
    QUALIFICATION,
    "a0/qualification/eligibility.py",
    "a0/qualification/build_qualification.py",
    "a0/qualification/verify_qualification.py",
    "a0/qualification/attested-a0-1.contract.json",
    "a0/qualification/freeze.py",
    "a0/conformance/report.json",
    "a0/conformance/selftest_report.json",
    "a0/conformance/conformance.py",
    "a0/conformance/selftest.py",
    "a0/envelope/envelope.py",
    "a0/envelope/execution-set.json",
    "a0/verify/verdicts.json",
    "a0/mrc/frozen_routes.json",
    "a0/closure/closure.reconciliation.json",
    "a0/tasks/circle-packing/e_star.py",
    "a0/tasks/circle-packing/e_star_child.py",
    "a0/tasks/circle-packing/E_STAR.json",
    "a0/tasks/circle-packing/C_STAR/manifest.json",
)


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def digest(obj) -> str:
    return sha256_bytes(canonical(obj).encode())


def load(path: Path):
    return json.loads(Path(path).read_text())


def rel(path: Path, root: Path) -> str:
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return str(path)


def artifact_paths(qual: dict, root: Path = None) -> list:
    """Every file the frozen state depends on: the core set plus every evidence path cited.

    The D3 measurement envelope is included by resolving it out of the report: it is the document
    the harness issued the tokens from, so a freeze that did not cover it would pin the verdict
    without pinning what the verdict was compared against.
    """
    root = root or ROOT
    paths = list(CORE_ARTIFACTS)
    for entry in qual["runtimes"].values():
        for comp in entry["Q_r"].values():
            specs = comp.get("evidence")
            specs = specs if isinstance(specs, list) else [specs]
            for spec in specs:
                if spec:
                    paths.append(str(spec).split("#")[0])
        for comp in entry["Q_r"].values():
            for caveat in comp.get("caveats") or []:
                for spec in caveat.get("evidence") or []:
                    paths.append(str(spec).split("#")[0])
    for runtime in RUNTIMES:
        paths.append(f"a0/closure/closure.{runtime}.json")

    report = root / "a0/conformance/report.json"
    if report.is_file():
        try:
            env = (load(report) or {}).get("envelope") or {}
        except Exception:
            env = {}
        for raw in (env.get("path"),):
            if not raw:
                continue
            candidate = Path(str(raw))
            try:
                paths.append(str(candidate.relative_to(root)))
            except ValueError:
                paths.append(str(candidate))

    resolved = []
    for spec in paths:
        if not spec:
            continue
        if str(spec).startswith("/"):
            try:
                resolved.append(str(Path(spec).relative_to(root)))
            except ValueError:
                continue
        else:
            resolved.append(str(spec))
    return sorted(set(resolved))


def collect_artifacts(root: Path, qual: dict) -> dict:
    out, missing = {}, []
    for spec in artifact_paths(qual, root):
        path = root / spec
        if path.is_file():
            out[spec] = sha256_file(path)
        else:
            missing.append(spec)
    return {"digests": out, "missing": missing}


def component_digests(qual: dict) -> dict:
    return {
        runtime: {
            name: {"value": comp.get("value"), "digest": digest(comp)}
            for name, comp in entry["Q_r"].items()
        }
        for runtime, entry in qual["runtimes"].items()
    }


def predicate_fingerprint(root: Path) -> dict:
    module = root / "a0/qualification/eligibility.py"
    return {
        "version": PREDICATE_VERSION,
        "module": "a0/qualification/eligibility.py",
        "module_sha256": sha256_file(module) if module.is_file() else None,
        "rules_sha256": digest(RULES),
        "threshold_vectors_sha256": digest(THRESHOLD_VECTORS),
        "n_rules": len(RULES),
        "vectors": sorted(THRESHOLD_VECTORS),
    }


EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"


def fingerprint(root: Path = ROOT, qual: dict = None) -> dict:
    qual = qual if qual is not None else load(root / QUALIFICATION)
    artifacts = collect_artifacts(root, qual)
    metrics = key_metrics(qual)
    return {
        "eid_star": EID_STAR,
        "predicate": predicate_fingerprint(root),
        "components": component_digests(qual),
        "artifacts": artifacts["digests"],
        "artifacts_missing_at_build": artifacts["missing"],
        "key_metrics": metrics,
    }


def _git(*args) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=60)
        return (proc.stdout or "").strip()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"<git failed: {exc}>"


# --------------------------------------------------------------------------------------
# gates: what must be true before a freeze is legitimate


def gate_d1_execution_env_drift(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    path = root / "a0/conformance/conformance.py"
    if not path.is_file():
        return False, "a0/conformance/conformance.py is missing"
    src = path.read_text()
    if "EXECUTION_ENV_DRIFT" not in src:
        return False, (
            "a0/conformance/conformance.py does not declare EXECUTION_ENV_DRIFT, so an "
            "interpreter-only mismatch is still reported as MISMATCH_DIGEST (D1 not landed)"
        )
    return True, "EXECUTION_ENV_DRIFT is declared in a0/conformance/conformance.py"


def gate_predicate_self_test(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    proc = subprocess.run(
        [sys.executable, str(root / "a0/qualification/eligibility.py"), "--self-test"],
        capture_output=True, text=True, timeout=120, cwd=str(root),
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:]
    return proc.returncode == 0, " ".join(tail) or f"exit {proc.returncode}"


def gate_qualification_matches_evidence(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    proc = subprocess.run(
        [sys.executable, str(root / "a0/qualification/build_qualification.py"), "--check"],
        capture_output=True, text=True, timeout=600, cwd=str(root),
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:]
    return proc.returncode == 0, " ".join(tail) or f"exit {proc.returncode}"


def gate_attestation_fails_closed(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    proc = subprocess.run(
        [sys.executable, str(root / "a0/qualification/build_qualification.py"), "--self-test"],
        capture_output=True, text=True, timeout=120, cwd=str(root),
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:]
    return proc.returncode == 0, " ".join(tail) or f"exit {proc.returncode}"


def _qual(root: Path) -> dict:
    return load(root / QUALIFICATION)


def gate_a0_1_rerun_with_attestation_required(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    """The A0.1 report on record must be the post-D3 re-run, with the token requirement ON.

    Mechanical and independent of any per-runtime verdict: read `a0/conformance/report.json` and
    require the run to have issued the measurement envelope in required mode. A report from before
    D3 has no `envelope` block at all; a pilot run with the requirement off has `required=false` and
    establishes nothing (its rows are exploratory by the runner's own words).
    """
    path = root / "a0/conformance/report.json"
    if not path.is_file():
        return False, "a0/conformance/report.json is missing"
    report = load(path)
    env = report.get("envelope") or {}
    if not env:
        return False, (
            "a0/conformance/report.json carries no `envelope` block: this A0.1 run predates the D3 "
            "wiring, so no row could have echoed a measurement token"
        )
    if env.get("required") is not True:
        return False, (
            f"the A0.1 run was made with the token requirement OFF (envelope.required="
            f"{env.get('required')!r}, mode={env.get('mode')!r}): its acceptances are exploratory by "
            "the runner's own statement, so it cannot ground a freeze"
        )
    return True, (
        f"A0.1 was re-run with the measurement envelope REQUIRED (run "
        f"{env.get('harness_run_id') or 'unnamed'}, tokens={env.get('tokens')}, envelope "
        f"sha256 {env.get('sha256') or sha256_file(path)}; the freeze pins the envelope document "
        f"itself, not just the verdicts it produced)"
    )


def gate_a0_1_attested(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    """Every required runtime's rows must be ACCEPTABLE evidence, not merely numerically agreeing.

    Distinguishes the two ways this can be unmet, because they have different remedies:
      UNPROVEN -- no attestation on record (the runtime was never wired)
      FAIL     -- the runner asked, and the row did not answer (MISSING_ATTESTATION,
                  MISSING_IDENTITY, MISMATCH_ATTESTATION). A rejection, not a gap.
    """
    qual = _qual(root)
    ok, unproven, rejected = [], [], []
    for runtime in RUNTIMES:
        if runtime in exclude:
            continue
        comp = qual["runtimes"][runtime]["Q_r"]["a0_1_attested"]
        value = comp.get("value")
        if value == "PASS":
            ok.append(runtime)
        elif value == "FAIL":
            rejected.append(f"{runtime} ({comp.get('identity_verdict')})")
        else:
            unproven.append(f"{runtime}={value}")
    if unproven or rejected:
        parts = []
        if rejected:
            parts.append(
                "the A0.1 run asked and the rows did not answer: " + ", ".join(rejected)
                + " -- a rejection to settle, not a gap"
            )
        if unproven:
            parts.append("no attestation on record: " + ", ".join(unproven))
        return False, (
            "not every required runtime's rows are acceptable evidence. " + "; ".join(parts)
        )
    return True, f"harness-attested (PASS) for every required runtime: {ok}"


def gate_runtimes_wired_or_excluded(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    """A DECISION gate, not a measurement: wire the remaining runtimes, or exclude them in writing.

    The evidence cannot decide this. Kapso/Eve/Loreley ran A0.1 with the envelope required and did
    not echo the token, so their rows are not acceptable evidence; whether that is fixed by wiring
    their adapters (the D3 follow-up, cost: change the reader/adapter and re-run A0.1) or accepted
    as "these three are not in the A1 main arm" is the user's call. Whichever it is, the freeze
    document must say so, per runtime.
    """
    qual = _qual(root)
    must_be_excluded = []
    for runtime in RUNTIMES:
        if runtime in exclude:
            if not (excluded_reasons or {}).get(runtime):
                must_be_excluded.append(f"{runtime} excluded without a written reason")
            continue
        if qual["runtimes"][runtime]["Q_r"]["a0_1_attested"].get("value") != "PASS":
            must_be_excluded.append(runtime)
    if must_be_excluded:
        return False, (
            "DECISION REQUIRED, per runtime: wire it (make its lane echo the harness measurement "
            "token and attest the bytes it executed, then re-run A0.1) or exclude it explicitly "
            "(`--exclude runtime=reason`, which is recorded in the freeze document). Neither yet: "
            f"{must_be_excluded}"
        )
    return True, f"wired={[r for r in RUNTIMES if r not in exclude]}, excluded={sorted(exclude)}"


def gate_mrc_frozen(root: Path = ROOT, exclude=(), excluded_reasons=None) -> tuple:
    qual = _qual(root)
    bad = [
        f"{runtime}={qual['runtimes'][runtime]['Q_r']['mrc'].get('value')}"
        for runtime in RUNTIMES
        if runtime not in exclude and qual["runtimes"][runtime]["Q_r"]["mrc"].get("value") != "FROZEN"
    ]
    if bad:
        return False, f"model route not frozen for: {', '.join(bad)}"
    return True, f"model route frozen (MRC* validates against frozen_routes.json) for {[r for r in RUNTIMES if r not in exclude]}"


GATES = [
    {"id": "G1_d1_landed", "kind": "measurement", "owner": "D1 workstream (landed)",
     "what": "D1: an interpreter mismatch is its own verdict, not a behaviour disagreement",
     "check": gate_d1_execution_env_drift},
    {"id": "G2_predicate_self_test", "kind": "measurement", "owner": "a0/qualification",
     "what": "the predicate's own self-test passes", "check": gate_predicate_self_test},
    {"id": "G2b_attestation_fails_closed", "kind": "measurement", "owner": "a0/qualification",
     "what": "the attestation resolution fails closed on omission and contradiction",
     "check": gate_attestation_fails_closed},
    {"id": "G3_qualification_matches_evidence", "kind": "measurement", "owner": "a0/qualification",
     "what": "qualification.json re-derives from its evidence", "check": gate_qualification_matches_evidence},
    {"id": "G4_a0_1_rerun_with_attestation_required", "kind": "measurement",
     "owner": "D3 workstream + a0/conformance (landed: the A0.1 re-run happened with the envelope on)",
     "what": "the A0.1 report on record is the post-D3 re-run with the measurement envelope REQUIRED",
     "check": gate_a0_1_rerun_with_attestation_required},
    {"id": "G5_a0_1_attested", "kind": "measurement",
     "owner": "the runtime adapters (they must echo the token and attest the bytes they executed)",
     "what": "every required runtime's A0.1 rows are acceptable evidence, not merely numerically agreeing",
     "check": gate_a0_1_attested},
    {"id": "G6_runtimes_wired_or_excluded", "kind": "decision", "owner": "the coordinator / user",
     "what": "DECISION: every runtime is wired or explicitly excluded with a reason",
     "check": gate_runtimes_wired_or_excluded},
    {"id": "G7_mrc_frozen", "kind": "measurement", "owner": "a0/mrc",
     "what": "the model route is frozen", "check": gate_mrc_frozen},
]


def run_gates(root: Path = ROOT, exclude=(), excluded_reasons=None) -> list:
    out = []
    for gate in GATES:
        try:
            ok, detail = gate["check"](root, exclude, excluded_reasons)
        except Exception as exc:  # fail closed
            ok, detail = False, f"gate raised {type(exc).__name__}: {exc}"
        out.append({
            "gate": gate["id"], "what": gate["what"], "kind": gate["kind"],
            "owner": gate["owner"], "ok": bool(ok), "detail": detail,
        })
    return out


# --------------------------------------------------------------------------------------
# the frozen document and the checker


def state_payload(doc: dict) -> dict:
    """The part of the document the freeze_id identifies: the state, not the prose about it.

    `gates`, `git_dirty`, `frozen_at` and `reason` are provenance, not state: a gate detail string
    carries a timestamp from `build_qualification.py --check`, and folding that into the id would
    make the id change while the frozen state stood still.
    """
    return {
        key: doc.get(key)
        for key in ("schema", "stage", "eid_star", "predicate", "components", "artifacts",
                    "artifacts_missing_at_build", "key_metrics", "excluded_runtimes")
    }


def build_document(root: Path = ROOT, exclude=(), excluded_reasons=None, state: str = "FROZEN",
                   reason: str = "", by: str = "freeze.py") -> dict:
    qual = _qual(root)
    fp = fingerprint(root, qual)
    doc = {
        "schema": SCHEMA,
        "stage": "A0",
        "state": state,
        "reason": reason,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "frozen_by": by,
        "git_rev": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "eid_star": fp["eid_star"],
        "predicate": fp["predicate"],
        "components": fp["components"],
        "artifacts": fp["artifacts"],
        "artifacts_missing_at_build": fp["artifacts_missing_at_build"],
        "key_metrics": fp["key_metrics"],
        "excluded_runtimes": {r: (excluded_reasons or {}).get(r, "") for r in sorted(exclude)},
        "r_a1_main_empty": not fp["key_metrics"]["R_A1_main"],
        "gates": run_gates(root, exclude, excluded_reasons),
        "components_note": (
            "each runtime component carries its value and the sha256 of the component object as "
            "stored in a0/qualification/qualification.json; `artifacts` carries the sha256 of every "
            "file the component was derived from. Any change to any of them unfreezes the document"
        ),
        "freeze_id_covers": [
            "schema", "stage", "eid_star", "predicate", "components", "artifacts",
            "artifacts_missing_at_build", "key_metrics", "excluded_runtimes",
        ],
    }
    doc["freeze_id"] = digest(state_payload(doc))
    return doc


def compare(doc: dict, root: Path = ROOT) -> dict:
    """Recompute the fingerprint against `root` and diff it against `doc`. Total, no writes."""
    problems, checked = [], {"artifacts": 0, "components": 0}

    for spec, want in (doc.get("artifacts") or {}).items():
        path = root / spec
        checked["artifacts"] += 1
        if not path.is_file():
            problems.append({"kind": "artifact_missing", "path": spec, "frozen": want})
            continue
        got = sha256_file(path)
        if got != want:
            problems.append({"kind": "artifact_changed", "path": spec, "frozen": want, "now": got})

    qual_path = root / QUALIFICATION
    if not qual_path.is_file():
        problems.append({"kind": "artifact_missing", "path": QUALIFICATION, "frozen": None})
    else:
        qual = load(qual_path)
        current = component_digests(qual)
        for runtime, comps in (doc.get("components") or {}).items():
            for name, frozen in comps.items():
                checked["components"] += 1
                now = (current.get(runtime) or {}).get(name)
                if now is None:
                    problems.append({"kind": "component_missing", "component": f"{runtime}.{name}"})
                elif now.get("digest") != frozen.get("digest"):
                    problems.append({
                        "kind": "component_changed",
                        "component": f"{runtime}.{name}",
                        "frozen_value": frozen.get("value"),
                        "now_value": now.get("value"),
                        "frozen": frozen.get("digest"),
                        "now": now.get("digest"),
                    })

    pred_now = predicate_fingerprint(root)
    for key in ("module_sha256", "rules_sha256", "threshold_vectors_sha256", "version", "vectors"):
        if pred_now.get(key) != (doc.get("predicate") or {}).get(key):
            problems.append({
                "kind": "predicate_changed", "field": key,
                "frozen": (doc.get("predicate") or {}).get(key), "now": pred_now.get(key),
            })

    if qual_path.is_file():
        metrics_now = key_metrics(load(qual_path))
        if metrics_now != (doc.get("key_metrics") or {}):
            problems.append({
                "kind": "key_metrics_changed",
                "frozen": doc.get("key_metrics"), "now": metrics_now,
            })

    recorded = digest(state_payload(doc))
    if doc.get("freeze_id") and recorded != doc["freeze_id"]:
        problems.append({"kind": "freeze_id_mismatch", "frozen": doc["freeze_id"], "now": recorded})

    state = doc.get("state", "FROZEN")
    if state == "FROZEN":
        verdict = "FROZEN" if not problems else "UNFROZEN"
    else:
        verdict = "MATCHES_ARMED" if not problems else "DRIFTED_FROM_ARMED"
    return {
        "document": state,
        "frozen_at": doc.get("frozen_at"),
        "freeze_id": doc.get("freeze_id"),
        "checked": checked,
        "match": not problems,
        "verdict": verdict,
        "problems": problems,
    }


def load_document(root: Path = ROOT) -> tuple:
    for path, kind in ((FROZEN_DOC, "frozen"), (CANDIDATE_DOC, "armed")):
        if path.is_file():
            return load(path), path, kind
    return None, None, None


# --------------------------------------------------------------------------------------
# self-test: the drift detection must be mechanical, so prove it on a real byte change


def self_test() -> int:
    problems = []
    doc = build_document(ROOT, state="FROZEN", reason="self-test")
    specs = sorted(doc["artifacts"])

    with tempfile.TemporaryDirectory(prefix="a0-freeze-selftest-") as tmp:
        tmp_root = Path(tmp)
        for spec in specs:
            src = ROOT / spec
            dst = tmp_root / spec
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

        got = compare(doc, tmp_root)
        if got["verdict"] != "FROZEN":
            problems.append(f"a byte-identical copy is reported {got['verdict']}: {got['problems'][:3]}")

        # 1. one byte of one artifact
        victim = "a0/qualification/eligibility.py"
        data = (tmp_root / victim).read_bytes()
        marker = b"def evaluate_rules("
        if marker not in data:
            problems.append("self-test marker missing from the predicate module")
        (tmp_root / victim).write_bytes(data.replace(marker, b"def evaluate_rulesX(", 1))
        got = compare(doc, tmp_root)
        kinds = {p["kind"] for p in got["problems"]}
        if got["verdict"] != "UNFROZEN" or "artifact_changed" not in kinds:
            problems.append(f"a one-byte artifact edit was not caught: {got['problems'][:3]}")
        if "predicate_changed" not in kinds:
            problems.append("a one-byte edit to the predicate module did not report predicate_changed")
        # restore
        (tmp_root / victim).write_bytes(data)

        # 2. a component value changed underneath an unchanged artifact set is impossible without
        #    changing qualification.json, so check that path explicitly
        qual_path = tmp_root / QUALIFICATION
        qual = load(qual_path)
        qual["runtimes"]["kapso"]["Q_r"]["a0_1_attested"]["value"] = "PASS"
        qual_path.write_text(json.dumps(qual, indent=2, ensure_ascii=False))
        got = compare(doc, tmp_root)
        named = [p.get("component") for p in got["problems"] if p["kind"] == "component_changed"]
        if "kapso.a0_1_attested" not in named:
            problems.append(f"a component value change was not named: {got['problems'][:4]}")
        shutil.copyfile(ROOT / QUALIFICATION, qual_path)

        # 3. the artifact set itself changed: a required file is gone
        (tmp_root / "a0/conformance/report.json").unlink()
        got = compare(doc, tmp_root)
        if not any(p["kind"] == "artifact_missing" for p in got["problems"]):
            problems.append("a deleted artifact was not reported as missing")
        shutil.copyfile(ROOT / "a0/conformance/report.json", tmp_root / "a0/conformance/report.json")

        # 4. a tampered freeze document must not validate against its own freeze_id
        tampered = json.loads(json.dumps(doc))
        tampered["key_metrics"]["R_A1_main"] = ["kapso"]
        got = compare(tampered, tmp_root)
        if not any(p["kind"] == "freeze_id_mismatch" for p in got["problems"]):
            problems.append("a tampered document did not trip freeze_id_mismatch")

        # 5. and the clean copy must be clean again after every restore
        got = compare(doc, tmp_root)
        if got["verdict"] != "FROZEN":
            problems.append(f"the restored copy is still {got['verdict']}: {got['problems'][:3]}")

    gates = run_gates(ROOT)
    if len(gates) != len(GATES):
        problems.append("gate count mismatch")
    if any(g["detail"] is None for g in gates):
        problems.append("a gate produced no detail string")

    print(f"{SCHEMA}: {len(specs)} artifacts, {sum(len(c) for c in doc['components'].values())} components")
    for problem in problems:
        print(f"  ! {problem}")
    print("self-test:", "ok" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


# --------------------------------------------------------------------------------------


def print_report(result: dict, doc_path=None) -> None:
    print(f"freeze check: {result['verdict']}"
          + (f"  (document: {doc_path}, state {result['document']}, frozen_at {result['frozen_at']})"
             if doc_path else ""))
    print(f"  checked {result['checked']['artifacts']} artifacts and "
          f"{result['checked']['components']} components")
    if result.get("match"):
        print("  every artifact and every component is byte-identical to the recorded state")
        if result["document"] != "FROZEN":
            print("  NOTE: the document is ARMED, not frozen -- this is a diff baseline, and the "
                  "freeze gates below decide whether a freeze is legitimate")
        return
    for problem in result["problems"]:
        kind = problem["kind"]
        if kind == "artifact_changed":
            print(f"  UNFROZEN  artifact changed: {problem['path']}")
            print(f"            frozen {problem['frozen']}")
            print(f"            now    {problem['now']}")
        elif kind == "artifact_missing":
            print(f"  UNFROZEN  artifact missing: {problem['path']}")
        elif kind == "component_changed":
            print(f"  UNFROZEN  component changed: {problem['component']} "
                  f"({problem['frozen_value']} -> {problem['now_value']})")
        elif kind == "component_missing":
            print(f"  UNFROZEN  component missing: {problem['component']}")
        elif kind == "predicate_changed":
            print(f"  UNFROZEN  predicate changed: {problem['field']} "
                  f"({problem['frozen']} -> {problem['now']})")
        elif kind == "key_metrics_changed":
            print(f"  UNFROZEN  R_A1^main / R_exploratory changed: "
                  f"{problem['frozen']} -> {problem['now']}")
        elif kind == "freeze_id_mismatch":
            print(f"  UNFROZEN  the document does not match its own freeze_id: "
                  f"{problem['frozen']} -> {problem['now']}")
        else:
            print(f"  UNFROZEN  {problem}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="freeze.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fingerprint", help="print the current fingerprint; writes nothing")
    sub.add_parser("arm", help="record the current tree as A0.freeze.candidate.json (not a freeze)")

    p_gates = sub.add_parser("gates", help="freeze-readiness gates alone")
    p_gates.add_argument("--json", action="store_true")
    p_gates.add_argument("--exclude", action="append", default=[], metavar="runtime=reason")

    p_check = sub.add_parser("check", help="does the tree still match the frozen/armed document?")
    p_check.add_argument("--json", action="store_true")

    p_freeze = sub.add_parser("freeze", help="THE freeze command (gated; refuses on a red gate)")
    p_freeze.add_argument("--reason", default="")
    p_freeze.add_argument("--by", default="freeze.py")
    p_freeze.add_argument("--exclude", action="append", default=[], metavar="runtime=reason")
    p_freeze.add_argument("--force", action="store_true", help="freeze even with red gates (records them)")
    p_freeze.add_argument("--no-tag", action="store_true", help="write the document, do not commit/tag")
    p_freeze.add_argument("--tag", default="a0-frozen")

    sub.add_parser("self-test", help="prove the drift detection mechanically")

    args = parser.parse_args(argv)

    if args.cmd == "self-test":
        return self_test()

    exclude, reasons = set(), {}
    for spec in getattr(args, "exclude", []) or []:
        if "=" not in spec:
            print(f"--exclude wants runtime=reason, got {spec!r}", file=sys.stderr)
            return 2
        runtime, reason = spec.split("=", 1)
        exclude.add(runtime.strip())
        reasons[runtime.strip()] = reason.strip()

    if args.cmd == "fingerprint":
        print(json.dumps(fingerprint(ROOT), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "arm":
        doc = build_document(ROOT, exclude, reasons, state="ARMED_NOT_FROZEN",
                             reason="baseline recorded by `freeze.py arm` -- NOT a freeze")
        CANDIDATE_DOC.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"armed: {rel(CANDIDATE_DOC, ROOT)} (state {doc['state']})")
        print(f"  freeze_id {doc['freeze_id']}")
        print(f"  {len(doc['artifacts'])} artifacts, "
              f"{sum(len(c) for c in doc['components'].values())} components")
        for gate in doc["gates"]:
            print(f"  {'PASS' if gate['ok'] else 'FAIL'}  {gate['gate']}: {gate['detail']}")
        return 0

    if args.cmd == "gates":
        gates = run_gates(ROOT, exclude, reasons)
        if args.json:
            print(json.dumps(gates, indent=2, ensure_ascii=False))
            return 0
        for gate in gates:
            mark = "PASS" if gate["ok"] else ("DECIDE" if gate["kind"] == "decision" else "FAIL")
            print(f"{mark:<6} {gate['gate']}: {gate['detail']}")
        red = [g for g in gates if not g["ok"]]
        print(f"\n{len(gates) - len(red)}/{len(gates)} gates pass")
        for gate in red:
            print(f"  red: {gate['gate']} ({gate['kind']}) -- resolved by: {gate['owner']}")
        return 0 if not red else 1

    if args.cmd == "check":
        doc, path, kind = load_document(ROOT)
        if doc is None:
            gates = run_gates(ROOT)
            red = [g for g in gates if not g["ok"]]
            result = {
                "document": "NONE",
                "frozen_at": None,
                "freeze_id": None,
                "checked": {"artifacts": 0, "components": 0},
                "match": False,
                "verdict": "NOT_FROZEN",
                "problems": [{"kind": "no_document",
                              "detail": "no A0.freeze.json and no A0.freeze.candidate.json on record"}],
            }
            if args.json:
                print(json.dumps({**result, "gates": gates}, indent=2, ensure_ascii=False))
                return 1
            print_report(result, None)
            print(f"  {len(gates) - len(red)}/{len(gates)} freeze gates pass")
            for gate in gates:
                print(f"  {'PASS' if gate['ok'] else 'FAIL'}  {gate['gate']}: {gate['detail']}")
            print("\nto record a baseline to diff against: `python3 freeze.py arm`")
            return 1
        result = compare(doc, ROOT)
        if args.json:
            print(json.dumps({**result, "document_path": rel(path, ROOT), "document_kind": kind},
                             indent=2, ensure_ascii=False))
            return 0 if result["match"] else 1
        print_report(result, rel(path, ROOT))
        return 0 if result["match"] else 1

    # freeze
    gates = run_gates(ROOT, exclude, reasons)
    red = [g for g in gates if not g["ok"]]
    if red and not args.force:
        print("REFUSING to freeze: the following gates are red.", file=sys.stderr)
        for gate in red:
            print(f"  FAIL  {gate['gate']}: {gate['detail']}", file=sys.stderr)
        print("\nfix the above, or mark runtimes as explicitly excluded "
              "(`--exclude runtime=reason`), or pass --force to freeze anyway (the red gates are "
              "recorded in the document).", file=sys.stderr)
        return 2

    doc = build_document(ROOT, exclude, reasons, state="FROZEN", reason=args.reason, by=args.by)
    if doc["r_a1_main_empty"] and not args.reason.strip():
        print("REFUSING to freeze: R_A1^main is empty and no --reason was given. An A0 freeze with "
              "no admissible runtime is a legitimate result, but it must say so in words, not by "
              "omission.", file=sys.stderr)
        return 2
    FROZEN_DOC.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"frozen: {rel(FROZEN_DOC, ROOT)}")
    print(f"  freeze_id  {doc['freeze_id']}")
    print(f"  R_A1^main  {doc['key_metrics']['R_A1_main'] or '{} (empty)'}")
    print(f"  artifacts  {len(doc['artifacts'])}")
    print(f"  git_rev    {doc['git_rev']} (dirty={doc['git_dirty']})")
    if doc["r_a1_main_empty"]:
        print("  WARNING: R_A1^main is EMPTY. The freeze records that no runtime has the evidence "
              "T_A1 requires; it does not admit any runtime to A1.")
    for gate in doc["gates"]:
        print(f"  {'PASS' if gate['ok'] else 'FAIL'}  {gate['gate']}")
    if args.no_tag:
        print("\nnot committed or tagged (--no-tag). To record it:")
        print(f"  git add {rel(FROZEN_DOC, ROOT)}")
        print(f"  git commit -m 'freeze: A0 {doc['freeze_id'][:12]}'")
        print(f"  git tag -a {args.tag} -m 'A0 frozen at {doc['freeze_id']}'")
        return 0
    steps = [
        (["add", rel(FROZEN_DOC, ROOT)], "git add"),
        (["commit", "-m", f"freeze: A0 {doc['freeze_id'][:12]}"], "git commit"),
        (["tag", "-a", args.tag, "-m", f"A0 frozen at {doc['freeze_id']}"], "git tag"),
    ]
    for argv_, label in steps:
        proc = subprocess.run(["git", "-C", str(ROOT), *argv_], capture_output=True, text=True)
        print(f"  {label}: exit {proc.returncode} {(proc.stdout or proc.stderr or '').strip()[:200]}")
        if proc.returncode != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
