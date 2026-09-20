#!/usr/bin/env python3
"""A0.1 cross-adapter conformance runner.

Answers one question for the whole study: if every runtime adapter is pointed at the same
frozen evaluator `E*` and the same fixed candidate set `C*`, does it produce the same
numbers (and the same verdicts for the candidates that have no number)?

Protocol: `plan:513-519` (the acceptance formula `E_r(c; theta_E) = E*(c; theta_E) +- epsilon`
and `EID_r` derived from `EID*`), `plan:490` (A0 is a candidate screen: `|R_1| >= 1`), and the
binding decisions recorded in `a0/tasks/circle-packing/README.md`:

  * `E*` is `a0/tasks/circle-packing/e_star.py` (+ `e_star_child.py`), not upstream's
    `scripts/local_eval.py`; `EID* = 664115e0...` (see `EID_INPUTS.json`).
  * `E*` invocation: `e_star.py evaluate --candidate <dir> --seed 1337 --fidelity full
    --fraction 1.0 --out <outcome.json> [--state-dir <dir>]`.
  * first round: `F_r(E*) = scalar(E*) = outcome.objective.sum_radii` (`plan:528`).

The runner never trusts an adapter's own verdict. It reads the adapter's per-candidate numbers
and verdicts, then compares them itself against the frozen table `E_STAR.json` (and against its
own fresh `E*` sweep) -- an adapter that reports "A0.1 ok" for a crash recorded as `0.0` is
caught by the comparison, not by the adapter's self-assessment.

Usage:
    python3 conformance.py reference [--force]      # fresh E* sweep over C*, vs E_STAR.json
    python3 conformance.py run [--runtimes ...]     # the A0.1 run + report.json + report.md
    python3 conformance.py show [--report ...]      # re-render the table from report.json

Exit codes: 0 all four runtimes PASS; 2 runner done, >=1 runtime PENDING/BLOCKED, no FAIL;
3 >=1 runtime FAIL; 4 candidate-set integrity abort; 10 runner bug.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# --------------------------------------------------------------------------------------
# frozen study coordinates

HERE = Path(__file__).resolve().parent
A0 = HERE.parent
TASK = A0 / "tasks" / "circle-packing"
C_STAR_MANIFEST = TASK / "C_STAR" / "manifest.json"
E_STAR_SCRIPT = TASK / "e_star.py"
E_STAR_PYTHON = TASK / ".venv" / "bin" / "python"
E_STAR_TABLE = TASK / "E_STAR.json"
EID_INPUTS = TASK / "EID_INPUTS.json"
# The EID* document the adapters are handed. The canonical one is the contract-owned document:
# it is the only one `evalcontract.py verify --spec a0/contract/plumbing.contract.json` resolves
# without a path override (its `spec` field is `contract/plumbing.contract.json`), so a reader who
# re-derives EID* from the contract side lands on the same bytes the run used.
# `proposed` is the task-side copy (`a0/tasks/circle-packing/plumbing.EID.proposed.json`) the
# runner used first; it carries the same EID* but declares the *proposed* spec
# (`tasks/circle-packing/plumbing.contract.proposed.json`). Keep `--eid-document proposed` for
# runs that must be comparable with the pre-repoint reports.
EID_DOCUMENT_CHOICES = {
    "canonical": A0 / "contract" / "out" / "plumbing.EID.json",
    "proposed": TASK / "plumbing.EID.proposed.json",
}
EID_DOCUMENT_DEFAULT = "canonical"
EID_DOCUMENTS = list(EID_DOCUMENT_CHOICES.values())
EVALCONTRACT = A0 / "contract" / "evalcontract.py"
EVALCONTRACT_PYTHON = A0 / "contract" / ".venv" / "bin" / "python"
FR_DECLARATION = A0 / "contract" / "fr" / "scalar.json"
ADAPTER_ROOT = A0 / "runtimes"
ADAPTER_REGISTRY = HERE / "adapters.json"

RUNTIMES = ["simpleloop", "kapso", "eve", "loreley"]

# The scratch root the fixture adapters write under (audit F6). Set by the runner for its control
# rows and by selftest.py for its fixtures; fixtures never write inside `a0/conformance/out/`.
FIXTURE_RUN_ROOT_ENV = "A0_FIXTURE_RUN_ROOT"

# `plan:513-519` theta_E, frozen: the seed the KAPSO registered-evaluation contract uses
# (evaluation_maintainer.subsample_seed = 1337) plus E*'s own defaults, made explicit.
THETA_E = {
    "seed": 1337,
    "fidelity": "full",
    "fraction": 1.0,
    "n": 26,
    "runs": 5,
    "runtime_budget_ms": 250.0,
    "timeout_s": 120.0,
}
PRIMARY_FIELD = "sum_radii"
DIRECTION = "maximize"
EPSILON = 1e-9  # Config.conformance.epsilon, absolute, sum_radii units
BINDING_EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"
BINDING_FR_SPEC_HASH = "1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0"
BUDGET = "T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1"
TRACES = "score,selection,resource"
ADAPTER_TIMEOUT_SEC = 1800

# Control rows driven through exactly the same checker as the runtimes, so that report.json
# carries evidence that the verdict machinery works on this C*/E* (see README, "Controls").
CONTROL_ADAPTERS = {
    "control_honest": ("fixtures/adapters/reference_adapter.py", "a real E* execution on all of C* -- must PASS"),
    "control_zero_on_error": ("fixtures/adapters/deviant.py --mode zero_on_error",
                              "EvE failure_score(0.0) trap -- must FAIL (plan:551)"),
    "control_cache_hit": ("fixtures/adapters/deviant.py --mode cache_hit",
                          "Loreley cache-reuse trap -- must FAIL (plan:552)"),
}

# E* exit codes (binding decision 2) / adapter exit codes (adapter_contract.md 3.1)
E_STAR_EXIT_OK, E_STAR_EXIT_INVALID, E_STAR_EXIT_ERROR = 0, 2, 3
ADAPTER_EXIT_USAGE, ADAPTER_EXIT_EID, ADAPTER_EXIT_INTEGRITY = 2, 3, 4
ADAPTER_EXIT_CONFORMANCE, ADAPTER_EXIT_CLOSURE, ADAPTER_EXIT_BUDGET = 5, 6, 7
ADAPTER_EXIT_NO_CANDIDATE, ADAPTER_EXIT_INTERNAL = 8, 10

# runtime state
PASS, FAIL, PENDING, BLOCKED = "PASS", "FAIL", "PENDING", "BLOCKED"
# per-candidate verdicts
MATCH, MATCH_VERDICT = "MATCH", "MATCH_VERDICT"
SYNTHETIC_DECLARED = "SYNTHETIC_DECLARED"
ACCEPTING_VERDICTS = (MATCH, MATCH_VERDICT, SYNTHETIC_DECLARED)
MISMATCH_VALUE, MISMATCH_STATUS, MISMATCH_NULL = "MISMATCH_VALUE", "MISMATCH_STATUS", "MISMATCH_NULL"
MISMATCH_DIGEST, MISMATCH_THETA, MISMATCH_EID = "MISMATCH_DIGEST", "MISMATCH_THETA", "MISMATCH_EID"
MISMATCH_KIND, MISMATCH_STAGE = "MISMATCH_FAILURE_KIND", "MISMATCH_FAILURE_STAGE"
UNDECLARED_KIND = "UNDECLARED_FAILURE_KIND"
FALSE_GREEN_ZERO = "FALSE_GREEN_SYNTHETIC_ZERO"
FALSE_GREEN_CACHE = "FALSE_GREEN_CACHE_REUSE"
FALSE_GREEN_TIMEOUT = "FALSE_GREEN_TIMEOUT_SYNTHESIS"
FALSE_GREEN_TRUNCATED = "FALSE_GREEN_TRUNCATED_METRICS"
FALSE_GREEN_TRIPLE = "FALSE_GREEN_MANIFEST_TRIPLE"
FALSE_GREEN_KIND = "FG-FAILURE-KIND"
FALSE_GREEN_STAGE = "FG-FAILURE-STAGE"
FALSE_GREEN_KIND_UNDECLARED = "FG-FAILURE-KIND-UNDECLARED"
MISSING, UNREADABLE = "MISSING", "UNREADABLE"

# adapter_contract.md §5.3, frozen and A0-wide: `E*` verdict -> trace `failure_stage`. A0.1 does not
# require an adapter to re-stage `E*`'s failures, but a runtime whose failures would land in a
# different stage makes `plan:577`/`plan:628`'s per-runtime FailureStage counts non-joinable, so the
# runner derives the expected stage per candidate from this table and compares a stage the adapter
# does declare against it.
FAILURE_STAGE_BY_KIND = {
    "candidate_import_failed": "resolve_failed",
    "non_deterministic": "verify_failed",
    "runtime_budget_exceeded": "timeout",
    "candidate_call_raised": "evaluator_failed",
    "child_terminated_early": "evaluator_failed",
}
FAILURE_STAGES = ("none", "evaluator_failed", "search_failed", "resolve_failed", "verify_failed",
                  "comprehension_failed", "timeout")

# The same facts as an `E_STAR_MANIFEST {...}` line, published as fields (KAPSO: `registered_channel.
# manifest`). Keys are matched case-insensitively; the mapped name is the manifest's own spelling.
FIELD_ECHO_MAP = {
    "e_star_canonical_digest": "canonical_digest",
    "e_star_evaluator_source_sha256": "evaluator_source_sha256",
    "e_star_status": "status",
    "e_star_exit_code": "exit_code",
    "e_star_objective_value": "objective_value",
    "e_star_items_audited": "items",
}

NON_FRESH_EVIDENCE = {"synthesized_failure", "timeout", "cache_hit", "truncated_metrics", "not_run", "manifest_mismatch"}

EXIT_RUNNER = {"pass": 0, "pending": 2, "fail": 3, "integrity": 4, "bug": 10}


# --------------------------------------------------------------------------------------
# small utilities


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> bytes:
    """Same canonicalisation as `a0/contract/evalcontract.py` (SPEC.md [decision])."""
    return json.dumps(
        _stringify_keys(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _stringify_keys(obj):
    if isinstance(obj, dict):
        return {str(k): _stringify_keys(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify_keys(v) for v in obj]
    return obj


def canonical_file_digest(path: Path) -> str:
    return hashlib.sha256(canonical_json(json.loads(Path(path).read_text()))).hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text())


def rel_or_abs(path) -> str:
    """Display a path relative to a0/ when it is inside the tree, else absolutely."""
    try:
        return str(Path(path).resolve().relative_to(A0))
    except ValueError:
        return str(path)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False) + "\n")


def theta_to_flag(theta: dict) -> str:
    parts = []
    for key in ("seed", "fidelity", "fraction", "n", "runs", "runtime_budget_ms", "timeout_s"):
        if key in theta:
            parts.append(f"{key}={theta[key]}")
    return ",".join(parts)


def first_present(obj: dict, names, default=None):
    for name in names:
        if isinstance(obj, dict) and obj.get(name) is not None:
            return obj[name]
    return default


def as_float(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def run_cmd(argv, cwd=None, timeout=ADAPTER_TIMEOUT_SEC, env=None) -> dict:
    started = time.monotonic()
    proc_env = dict(os.environ)
    if env:
        proc_env.update(env)
    try:
        proc = subprocess.run(
            [str(a) for a in argv],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=proc_env,
        )
        return {
            "argv": [str(a) for a in argv],
            "cwd": str(cwd) if cwd else None,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_sec": round(time.monotonic() - started, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": [str(a) for a in argv],
            "cwd": str(cwd) if cwd else None,
            "exit_code": None,
            "stdout": exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            "duration_sec": round(time.monotonic() - started, 3),
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "argv": [str(a) for a in argv],
            "cwd": str(cwd) if cwd else None,
            "exit_code": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "duration_sec": round(time.monotonic() - started, 3),
            "timed_out": False,
            "spawn_failed": True,
        }


# --------------------------------------------------------------------------------------
# C*, EID*, theta_E


def load_candidate_set() -> dict:
    manifest = load_json(C_STAR_MANIFEST)
    candidates = manifest["candidates"]
    return {
        "manifest_path": str(C_STAR_MANIFEST),
        "manifest_sha256": sha256_file(C_STAR_MANIFEST),
        "candidate_set_id": manifest.get("candidate_set_id"),
        "task": manifest.get("task"),
        "schema": manifest.get("schema"),
        "candidates": candidates,
        "ids": [c["candidate_id"] for c in candidates],
    }


def candidate_roles() -> dict:
    """`role` lives in C*'s own manifest (E_STAR.json does not carry it)."""
    try:
        return {c["candidate_id"]: c.get("role") for c in load_json(C_STAR_MANIFEST)["candidates"]}
    except Exception:  # noqa: BLE001
        return {}


def check_integrity(cset: dict) -> dict:
    """`adapter_contract.md` 2.2: sha256(solution.py) must match before any evaluation."""
    rows = []
    problems = []
    root = C_STAR_MANIFEST.parent
    for cand in cset["candidates"]:
        cid = cand["candidate_id"]
        rel = cand.get("path") or cand.get("dir")
        target = root / rel / "solution.py"
        row = {"candidate_id": cid, "path": str(target), "declared": cand.get("solution_sha256")}
        if not target.exists():
            row["observed"] = None
            row["ok"] = False
            row["problem"] = "solution.py missing"
        else:
            observed = sha256_file(target)
            row["observed"] = observed
            row["ok"] = observed == cand.get("solution_sha256")
            if not row["ok"]:
                row["problem"] = "sha256 mismatch"
        if not row["ok"]:
            problems.append(row)
        rows.append(row)
    return {
        "candidate_set": cset["manifest_path"],
        "candidate_set_sha256": cset["manifest_sha256"],
        "checked": len(rows),
        "ok": not problems,
        "problems": problems,
        "rows": rows,
    }


def eid_document_choice(value):
    """Map the `--eid-document` flag onto `(label, path)`.

    A known label (`canonical`, `proposed`) is the intended spelling; an absolute/relative path
    is accepted too, so a future re-freeze can point the runner at a new document without editing
    the constants above. A relative path is resolved against `a0/`.
    """
    if value is None:
        value = EID_DOCUMENT_DEFAULT
    if value in EID_DOCUMENT_CHOICES:
        return value, EID_DOCUMENT_CHOICES[value]
    path = Path(value)
    if not path.is_absolute():
        # `a0/...` (the spelling used everywhere in this study) and `contract/out/...` (relative
        # to a0/) must both work.
        for base in (A0.parent, A0):
            if (base / path).exists():
                path = base / path
                break
        else:
            path = A0 / path
    return "path", path.resolve()


def describe_eid_document(path) -> dict:
    """What was handed to an adapter: label, path, content digest, and the EID* it carries.

    The digest is over the document bytes, so a later reader can tell whether a re-run used the
    same input document even if the file was rewritten with equivalent content (the digest would
    then differ, which is the point of recording it).
    """
    path = Path(path)
    label = next(
        (name for name, known in EID_DOCUMENT_CHOICES.items() if known == path or known.resolve() == path.resolve()),
        f"path:{path}",
    )
    doc = {"label": label, "path": str(path), "exists": path.exists()}
    if path.exists():
        doc["sha256"] = sha256_file(path)
        try:
            doc["eid_star"] = load_json(path).get("eid_star")
        except Exception as exc:  # noqa: BLE001
            doc["eid_star"] = None
            doc["error"] = f"{type(exc).__name__}: {exc}"
    doc["matches_binding"] = doc.get("eid_star") == BINDING_EID_STAR
    return doc


ADAPTER_REVISION_SUFFIXES = (".py", ".json", ".toml", ".sh", ".cfg", ".txt", ".lock")
# Path parts that are artifacts, caches or pinned third-party trees rather than the adapter's own
# source. Hidden directories (`.venv`, `.uvcache`, `.pytest_cache`) are skipped by the dot rule.
ADAPTER_REVISION_EXCLUDE = {
    "checkout", "out", "runs", "llm-round", "scratch", "probe", "state", "workspace", "traces",
    "node_modules", "site-packages", "vendor", "__pycache__",
}


def adapter_revision(adapter_dir) -> dict:
    """Digest and newest mtime of the source files that make up an adapter.

    A verdict is only meaningful for the revision that produced it: the adapters were edited
    throughout this study, and a stored report that does not name the revision cannot be told apart
    from one taken before a fix landed. The runner snapshots this before and after driving a
    runtime, so a report also says whether the revision moved *during* the run.
    """
    root = Path(adapter_dir)
    if not root.is_dir():
        return None
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in ADAPTER_REVISION_SUFFIXES:
            continue
        rel = path.relative_to(root)
        if any(part in ADAPTER_REVISION_EXCLUDE or part.startswith(".") for part in rel.parts):
            continue
        files.append(
            {
                "path": str(rel),
                "sha256": sha256_file(path),
                "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(path.stat().st_mtime)),
            }
        )
    if not files:
        return None
    digest = hashlib.sha256(
        "".join(f"{f['path']}\0{f['sha256']}\n" for f in files).encode("utf-8")
    ).hexdigest()
    return {
        "root": str(root),
        "files": files,
        "file_count": len(files),
        "digest": digest,
        "newest_mtime": max(f["mtime"] for f in files),
    }


def adapter_revision_diff(before, after) -> dict:
    """Which files changed between two snapshots (a run must not straddle an edit)."""
    changed = []
    if before and after:
        left = {f["path"]: f["sha256"] for f in before["files"]}
        right = {f["path"]: f["sha256"] for f in after["files"]}
        for path in sorted(set(left) | set(right)):
            if left.get(path) != right.get(path):
                changed.append(path)
    return {
        "unchanged_during_run": (before or {}).get("digest") == (after or {}).get("digest"),
        "changed_files": changed,
    }


def resolve_eid_document(requested=None) -> dict:
    """Find the EID*.json whose eid_star equals the frozen identity.

    `requested` is the raw `--eid-document` value (label or path); the default is the canonical
    contract-owned document. The requested document wins *only* if it exists and carries EID*;
    otherwise the first candidate that does is used and the substitution is reported in
    `requested_ok`/`substituted` so a report can never silently claim it used the wrong input.
    """
    label, requested_path = eid_document_choice(requested)
    paths = [requested_path] + [
        p for p in EID_DOCUMENT_CHOICES.values() if p.resolve() != requested_path.resolve()
    ]
    listed = []
    for path in paths:
        entry = {"path": str(path), "label": next(
            (n for n, known in EID_DOCUMENT_CHOICES.items() if known.resolve() == path.resolve()),
            f"path:{path}",
        ), "requested": path.resolve() == requested_path.resolve(), "exists": path.exists()}
        if path.exists():
            try:
                entry["eid_star"] = load_json(path).get("eid_star")
            except Exception as exc:  # noqa: BLE001
                entry["eid_star"] = None
                entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["matches_binding"] = entry.get("eid_star") == BINDING_EID_STAR
        listed.append(entry)
    preferred = next((e for e in listed if e.get("requested") and e.get("matches_binding")), None)
    fallback = next((e for e in listed if e.get("matches_binding")), None)
    chosen = preferred or fallback
    return {
        "expected_eid_star": BINDING_EID_STAR,
        "requested": label,
        "requested_path": str(requested_path),
        "requested_ok": (chosen is not None and chosen.get("requested", False)),
        "substituted": bool(chosen is not None and not chosen.get("requested", False)),
        "documents": listed,
        "chosen": chosen,
    }


def resolve_document_spec(eid_path):
    """The `spec` an EID* document declares, resolved against the tree.

    The runner verifies the document it actually hands the adapters against the document's *own*
    declared spec, so that the canonical document is checked against `contract/plumbing.contract.json`
    and the proposed one against `tasks/circle-packing/plumbing.contract.proposed.json`. Paths are
    written relative to `a0/` (both documents do); the other spellings are accepted as a fallback.
    """
    try:
        declared = load_json(Path(eid_path)).get("spec")
    except Exception:  # noqa: BLE001
        return None
    if not declared:
        return None
    raw = Path(declared)
    if raw.is_absolute():
        return raw if raw.is_file() else None
    for base in (A0, A0.parent, Path(eid_path).parent):
        if (base / raw).is_file():
            return (base / raw).resolve()
    return None


def check_eid(requested=None) -> dict:
    """EID*_derivation and EID*_inputs checks: recompute (no filesystem) + verify (re-hash)."""
    out = {"expected_eid_star": BINDING_EID_STAR, "checks": []}

    def add(check_id, ok, detail, **extra):
        out["checks"].append({"check_id": check_id, "ok": bool(ok), "detail": detail, **extra})

    # binding decision 1: EID_INPUTS.json is the authoritative record of EID* and its inputs
    inputs_ok = False
    if EID_INPUTS.exists():
        try:
            doc = load_json(EID_INPUTS)
            inputs_ok = doc.get("eid_star") == BINDING_EID_STAR
            out["eid_inputs"] = {
                "path": str(EID_INPUTS),
                "sha256": sha256_file(EID_INPUTS),
                "eid_star": doc.get("eid_star"),
                "spec_path": doc.get("proposed_spec_path"),
            }
        except Exception as exc:  # noqa: BLE001
            out["eid_inputs"] = {"path": str(EID_INPUTS), "error": f"{type(exc).__name__}: {exc}"}
    add(
        "EID-inputs-match-binding",
        inputs_ok,
        f"EID_INPUTS.json eid_star == binding 664115e0... : {inputs_ok}",
    )

    resolved = resolve_eid_document(requested)
    out["resolution"] = resolved
    out["requested"] = resolved["requested"]
    chosen = resolved["chosen"]
    add(
        "EID-document-found",
        chosen is not None,
        "an EID*.json with eid_star == 664115e0... was found"
        if chosen
        else "no EID*.json carries the frozen identity; candidates: "
        + ", ".join(f"{e['path']}={e.get('eid_star')}" for e in resolved["documents"]),
    )
    add(
        "EID-document-as-requested",
        resolved["requested_ok"],
        f"the document handed to the adapters is the one requested (`--eid-document "
        f"{resolved['requested']}` -> {resolved['requested_path']})"
        if resolved["requested_ok"]
        else (
            f"`--eid-document {resolved['requested']}` -> {resolved['requested_path']} does not carry "
            f"EID*; fell back to {(chosen or {}).get('path')}"
            if resolved["substituted"]
            else f"no document carrying EID* could be resolved for `--eid-document {resolved['requested']}`"
        ),
    )
    if chosen is None:
        return out

    eid_path = Path(chosen["path"])
    supplied = describe_eid_document(eid_path)
    out["eid_document_supplied"] = supplied
    declared_spec = resolve_document_spec(eid_path)
    spec_path = declared_spec or resolve_spec_path(out.get("eid_inputs", {}).get("spec_path"))
    base = A0
    out["spec_resolved"] = str(spec_path) if spec_path else None
    out["spec_source"] = (
        f"the supplied document's own `spec` field ({Path(chosen['path']).name})"
        if declared_spec
        else "EID_INPUTS.json proposed_spec_path (the document declares no resolvable `spec`)"
    )

    exe = str(EVALCONTRACT_PYTHON if EVALCONTRACT_PYTHON.exists() else sys.executable)
    rec = run_cmd([exe, EVALCONTRACT, "recompute", "--eid-file", eid_path], cwd=A0, timeout=300)
    out["recompute"] = {
        "argv": rec["argv"],
        "exit_code": rec["exit_code"],
        "stdout": rec["stdout"],
        "stderr": rec["stderr"],
    }
    # `recompute` prints the first 16 hex characters of each digest, not the full 64
    add(
        "EID-recompute",
        rec["exit_code"] == 0 and BINDING_EID_STAR[:16] in rec["stdout"],
        "evalcontract.py recompute is filesystem-free and recomputed EID* matching 664115e0d63ad2e1 "
        f"(exit {rec['exit_code']})",
    )

    if spec_path:
        ver = run_cmd(
            [exe, EVALCONTRACT, "verify", "--eid-file", eid_path, "--spec", spec_path, "--base", base],
            cwd=A0,
            timeout=300,
        )
        out["verify"] = {
            "argv": ver["argv"],
            "exit_code": ver["exit_code"],
            "stdout": ver["stdout"],
            "stderr": ver["stderr"],
            "spec": str(spec_path),
        }
        add(
            "EID-verify-inputs",
            ver["exit_code"] == 0,
            f"evalcontract.py verify re-hashed the declared inputs of {eid_path.name} against {spec_path} "
            f"[{out['spec_source']}] (exit {ver['exit_code']})",
        )
    else:
        out["verify"] = {"skipped": True, "reason": "no spec path could be resolved for the supplied document"}
        add("EID-verify-inputs", False, "no spec path could be resolved for the supplied document")

    agreeing = [e["path"] for e in resolved["documents"] if e.get("matches_binding")]
    out["eid_document"] = str(eid_path)
    out["eid_star"] = chosen.get("eid_star")
    add(
        "EID-documents-agree",
        len(agreeing) >= 1,
        f"{len(agreeing)} document(s) carry EID* = 664115e0...: {agreeing}; the runner hands "
        f"{eid_path} to the adapters (sha256 {supplied.get('sha256', 'n/a')})",
    )
    return out


def resolve_spec_path(spec_path):
    """EID_INPUTS.json records `proposed_spec_path` relative to a0/; accept several spellings."""
    if not spec_path:
        return None
    raw = Path(spec_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates += [A0 / raw, TASK / raw, TASK / raw.name, A0 / raw.name]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def check_fr() -> dict:
    digest = canonical_file_digest(FR_DECLARATION)
    decl = load_json(FR_DECLARATION)
    return {
        "declaration": str(FR_DECLARATION),
        "spec_hash": digest,
        "pinned_spec_hash": BINDING_FR_SPEC_HASH,
        "matches_pinned": digest == BINDING_FR_SPEC_HASH,
        "name": decl.get("name"),
        "applies": decl.get("applies"),
        "primary_field": decl.get("primary_field"),
        "direction": decl.get("direction"),
        "rule": "F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)",
    }


# --------------------------------------------------------------------------------------
# reference: E* applied to C* through the frozen invocation


def e_star_argv(candidate_dir: Path, out_json: Path, state_dir: Path, theta: dict) -> list:
    return [
        str(E_STAR_PYTHON),
        str(E_STAR_SCRIPT),
        "evaluate",
        "--candidate",
        str(candidate_dir),
        "--seed",
        str(theta["seed"]),
        "--fidelity",
        str(theta["fidelity"]),
        "--fraction",
        str(theta["fraction"]),
        "--n",
        str(theta["n"]),
        "--runs",
        str(theta["runs"]),
        "--runtime-budget-ms",
        str(theta["runtime_budget_ms"]),
        "--timeout-s",
        str(theta["timeout_s"]),
        "--out",
        str(out_json),
        "--state-dir",
        str(state_dir),
    ]


def parse_e_star_stdout(stdout: str):
    manifest = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("E_STAR_MANIFEST "):
            try:
                manifest = json.loads(line[len("E_STAR_MANIFEST ") :])
            except json.JSONDecodeError:
                manifest = None
    return manifest


def check_frozen_toolchain() -> dict:
    """The runner cannot do anything without these; a missing one is a BLOCKED, not a FAIL."""
    items = {
        "e_star_script": E_STAR_SCRIPT.exists(),
        "e_star_interpreter": E_STAR_PYTHON.exists(),
        "c_star_manifest": C_STAR_MANIFEST.exists(),
        "e_star_table": E_STAR_TABLE.exists(),
        "fr_declaration": FR_DECLARATION.exists(),
        "evalcontract": EVALCONTRACT.exists(),
    }
    return {"items": items, "ok": all(items.values()), "missing": [k for k, v in items.items() if not v]}


def reference_rows(theta: dict, out_dir: Path, timeout: float) -> list:
    cset = load_candidate_set()
    rows = []
    for cand in cset["candidates"]:
        cid = cand["candidate_id"]
        cdir = C_STAR_MANIFEST.parent / (cand.get("path") or cand.get("dir"))
        outcome_path = out_dir / "outcomes" / f"{cid}.json"
        state_dir = out_dir / "e-star-state"
        outcome_path.parent.mkdir(parents=True, exist_ok=True)
        if outcome_path.exists():
            outcome_path.unlink()
        argv = e_star_argv(cdir, outcome_path, state_dir, theta)
        res = run_cmd(argv, cwd=TASK, timeout=timeout)
        outcome = None
        read_error = None
        if outcome_path.exists():
            try:
                outcome = load_json(outcome_path)
            except Exception as exc:  # noqa: BLE001
                read_error = f"{type(exc).__name__}: {exc}"
        else:
            read_error = "E* wrote no outcome file"
        manifest = parse_e_star_stdout(res["stdout"])
        obj = (outcome or {}).get("objective") or {}
        rows.append(
            {
                "candidate_id": cid,
                "dir": rel_or_abs(cdir),
                "source_sha256": sha256_file(cdir / "solution.py"),
                "command": " ".join(shlex.quote(a) if " " in a else a for a in argv),
                "exit_code": res["exit_code"],
                "status": (outcome or {}).get("status"),
                "objective_value": as_float(obj.get("value")),
                "objective_name": obj.get("name"),
                "failure_kind": ((outcome or {}).get("failure") or {}).get("kind"),
                "failure_message": ((outcome or {}).get("failure") or {}).get("message"),
                "canonical_digest": (outcome or {}).get("canonical_digest"),
                "fields": (outcome or {}).get("fields"),
                "manifest_objective_value": as_float(((manifest or {}).get("objective") or {}).get("value")),
                "manifest_status": (manifest or {}).get("status"),
                "stdout_manifest_seen": manifest is not None,
                "outcome_read_error": read_error,
                "duration_sec": res["duration_sec"],
                "timed_out": res["timed_out"],
            }
        )
    return rows


def compare_to_table(rows: list, table: dict) -> dict:
    """E_STAR.json is the frozen reference table; the fresh sweep must reproduce it."""
    table_by_id = {c["candidate_id"]: c for c in table["candidates"]}
    checks = []
    ok_all = True
    for row in rows:
        ref = table_by_id.get(row["candidate_id"], {})
        problems = []
        if row["exit_code"] != ref.get("exit_code"):
            problems.append(f"exit_code {row['exit_code']} != table {ref.get('exit_code')}")
        if row["status"] != ref.get("status"):
            problems.append(f"status {row['status']} != table {ref.get('status')}")
        if row["canonical_digest"] != ref.get("canonical_digest"):
            problems.append(
                f"canonical_digest {row['canonical_digest']} != table {ref.get('canonical_digest')}"
            )
        table_value = as_float(ref.get("objective_value"))
        if table_value is None and row["objective_value"] is None:
            pass
        elif table_value is None or row["objective_value"] is None:
            problems.append(f"objective {row['objective_value']} != table {table_value}")
        elif abs(row["objective_value"] - table_value) > 0.0:
            problems.append(f"objective {row['objective_value']!r} != table {table_value!r} (must be exact)")
        if (row["failure_kind"] or None) != (ref.get("failure_kind") or None):
            problems.append(f"failure_kind {row['failure_kind']} != table {ref.get('failure_kind')}")
        if row["outcome_read_error"]:
            problems.append(row["outcome_read_error"])
        ok_all = ok_all and not problems
        checks.append({"candidate_id": row["candidate_id"], "reproduces_table": not problems, "problems": problems})
    return {"reproduces_frozen_table": ok_all, "per_candidate": checks}


def apply_manifest_override(args) -> None:
    """`--manifest` exists so the integrity-abort path can be exercised without touching C*."""
    global C_STAR_MANIFEST
    override = getattr(args, "manifest", None)
    if override:
        C_STAR_MANIFEST = Path(override).resolve()


def cmd_reference(args) -> int:
    apply_manifest_override(args)
    out_dir = Path(args.state_root) if args.state_root else HERE / "out"
    theta = dict(THETA_E)
    if args.fidelity:
        theta["fidelity"] = args.fidelity
        theta["fraction"] = 1.0 if args.fidelity == "full" else 0.15
    cset = load_candidate_set()
    integrity = check_integrity(cset)
    if not integrity["ok"]:
        print("C* integrity failure:", json.dumps(integrity["problems"], indent=2), file=sys.stderr)
        return EXIT_RUNNER["integrity"]

    toolchain = check_frozen_toolchain()
    if not toolchain["ok"]:
        print(f"BLOCKED: frozen toolchain incomplete: {toolchain['missing']}", file=sys.stderr)
        return EXIT_RUNNER["bug"]

    before = c_star_digest()
    print(f"A0.1 conformance: fresh E* sweep over {len(cset['candidates'])} candidates of C*")
    rows = reference_rows(theta, out_dir, args.timeout)
    after = c_star_digest()
    table = load_json(E_STAR_TABLE)
    agreement = compare_to_table(rows, table)

    doc = {
        "schema": "a0.conformance.reference/v1",
        "generated_at": now_iso(),
        "generated_by": "a0/conformance/conformance.py reference",
        "frozen_evaluator": {
            "script": str(E_STAR_SCRIPT.relative_to(A0)),
            "interpreter": str(E_STAR_PYTHON.relative_to(A0)),
            "eid_star": BINDING_EID_STAR,
            "table": str(E_STAR_TABLE.relative_to(A0)),
        },
        "theta_e": theta,
        "primary_field": PRIMARY_FIELD,
        "epsilon": EPSILON,
        "reference_table": str(E_STAR_TABLE),
        "reference_table_sha256": sha256_file(E_STAR_TABLE),
        "fresh_sweep": {"state_root": str(out_dir), "rows": rows},
        "agreement_with_frozen_table": agreement,
        "c_star_unchanged_after_sweep": {"before": before, "after": after, "unchanged": before == after},
    }
    path = Path(args.out) if args.out else HERE / "reference.json"
    write_json(path, doc)

    for row in rows:
        verdict = "ok " if row["objective_value"] is not None else "n/a"
        print(
            f"  {row['candidate_id']:<28} exit={row['exit_code']} status={str(row['status']):<7} "
            f"objective={row['objective_value']!r:<22} {verdict}"
        )
    print(f"reference table reproduced exactly: {agreement['reproduces_frozen_table']}")
    print(f"written: {path}")
    return 0 if agreement["reproduces_frozen_table"] else 3


def c_star_digest() -> str:
    """Digest over the whole C* tree, to prove E* never writes into a candidate worktree."""
    h = hashlib.sha256()
    root = C_STAR_MANIFEST.parent
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode("utf-8"))
        h.update(b"\x00")
        h.update(sha256_file(path).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


# --------------------------------------------------------------------------------------
# adapter discovery and invocation


def adapter_registry() -> dict:
    if ADAPTER_REGISTRY.exists():
        try:
            data = load_json(ADAPTER_REGISTRY)
        except Exception as exc:  # noqa: BLE001
            return {"_error": f"{type(exc).__name__}: {exc}"}
        return data.get("adapters", data)
    return {}


def discover_adapter(runtime: str, adapter_root: Path, overrides: dict, registry_error=None):
    """Find how to launch an adapter. Return (base_argv, info) or (None, info with a reason).

    Discovery order (documented in README.md so the adapter workstreams can rely on it):

      1. `--adapter <name>=<cmd>` on the runner's command line
      2. `a0/conformance/adapters.json` -> `{"adapters": {"<name>": {"cmd": [...]}}}`
      3. `<adapter_dir>/adapter.json` with a `cmd` / `conformance_cmd` list  <- the recommended way
      4. a script at `<adapter_dir>/{a0_adapter,adapter,main,cli}.py` or `<adapter_dir>/bin/*`
      5. a package `<a0_adapter|adapter>` under `<adapter_dir>` or `<adapter_dir>/src`:
         `__main__.py` -> `python -m <pkg>`; else `cli.py` -> `python -m <pkg>.cli`
      6. a bare `python -m a0_adapter` guess with the adapter's own venv (reported as a guess)
      7. otherwise PENDING, with the reason and every entry point candidate that was seen

    `info["pythonpath"]` is the directory the chosen module's parent lives in; the runner
    prepends it to PYTHONPATH and launches with cwd = the adapter directory.
    """
    info = {"adapter_root": str(adapter_root), "runtime_dir": str(adapter_root / runtime)}
    if registry_error:
        info["registry_error"] = registry_error

    override = overrides.get(runtime)
    if override:
        info.update({"source": "cli-override", "cmd": override})
        return list(override), info

    reg = adapter_registry().get(runtime) if runtime not in ("_error",) else None
    if isinstance(reg, dict) and reg.get("cmd"):
        info.update({"source": "adapters.json", "cmd": reg["cmd"]})
        return list(reg["cmd"]), info

    adir = adapter_root / runtime
    if not adir.is_dir():
        info["reason"] = f"no adapter directory at {adir}"
        return None, info

    for name in ("adapter.json", "a0_adapter.json", "config/adapter.json"):
        manifest = adir / name
        if manifest.exists():
            try:
                data = load_json(manifest)
            except Exception as exc:  # noqa: BLE001
                info["reason"] = f"{name} unreadable: {type(exc).__name__}: {exc}"
                return None, info
            cmd = data.get("cmd") or data.get("conformance_cmd")
            if cmd:
                info.update({"source": name, "cmd": cmd, "declared": data,
                             "pythonpath": data.get("pythonpath")})
                return list(cmd), info
            info["declared"] = data

    venv_py = adir / ".venv" / "bin" / "python"
    interpreter = str(venv_py) if venv_py.exists() else sys.executable
    seen = []

    for name in ("a0_adapter.py", "adapter.py", "main.py", "cli.py"):
        if (adir / name).exists():
            seen.append(f"{name} (script)")
            info.update({"source": name, "cmd": [interpreter, str(adir / name)], "pythonpath": str(adir)})
            return list(info["cmd"]), info

    bindir = adir / "bin"
    executables = sorted(p for p in bindir.glob("*") if p.is_file() and os.access(p, os.X_OK)) if bindir.is_dir() else []
    if executables:
        seen.append(f"bin/{executables[0].name} (executable)")
        info.update({"source": f"bin/{executables[0].name}", "cmd": [str(executables[0])],
                     "pythonpath": str(adir)})
        return list(info["cmd"]), info

    for parent in (adir, adir / "src"):
        for pkg_name in ("a0_adapter", "adapter"):
            pkg = parent / pkg_name
            if not (pkg.is_dir() and (pkg / "__init__.py").exists()):
                continue
            files = sorted(p.name for p in pkg.iterdir() if p.is_file())
            base = {"source": f"{pkg_name} package", "package_path": str(pkg),
                    "pythonpath": str(parent), "package_files": files}
            if (pkg / "__main__.py").exists():
                info.update({**base, "cmd": [interpreter, "-m", pkg_name]})
                return list(info["cmd"]), info
            for entry_module in ("cli", "main"):
                if (pkg / f"{entry_module}.py").exists():
                    info.update({**base, "cmd": [interpreter, "-m", f"{pkg_name}.{entry_module}"]})
                    return list(info["cmd"]), info
            seen.append(f"{pkg} package without __main__.py, cli.py or main.py (files: {files})")

    if seen:
        info.update({"files_seen": seen})
        info["reason"] = (
            f"no runnable entry point yet: {'; '.join(seen)}"
        )
        return None, info

    if venv_py.exists():
        info.update({"source": "venv + -m a0_adapter (guess: no package or script found)",
                     "cmd": [str(venv_py), "-m", "a0_adapter"], "pythonpath": str(adir),
                     "files_seen": sorted(p.name for p in adir.iterdir() if not p.name.startswith(".")),
                     "guessed_entry_point": True})
        return list(info["cmd"]), info

    info["reason"] = (
        f"{adir} exists but declares no entry point (looked for adapter.json, a0_adapter.py, "
        f"a0_adapter/{{__main__.py,cli.py}} at {adir} and {adir / 'src'}, .venv/bin/python)"
    )
    return None, info


def summarise_proc(res: dict, out_path: Path | None = None) -> dict:
    summary = {
        "argv": res["argv"],
        "cwd": res.get("cwd"),
        "exit_code": res["exit_code"],
        "duration_sec": res["duration_sec"],
        "timed_out": res.get("timed_out", False),
        "stdout_tail": "\n".join(res["stdout"].splitlines()[-25:]),
        "stderr_tail": "\n".join(res["stderr"].splitlines()[-25:]),
    }
    if res.get("spawn_failed"):
        summary["spawn_failed"] = True
    if out_path is not None:
        summary["out_path"] = str(out_path)
        summary["out_exists"] = out_path.exists()
    return summary


def save_raw(runtime: str, res: dict, out_path: Path, extra_name: str) -> dict:
    raw_dir = HERE / "out" / "adapters"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{runtime}{extra_name}.stdout.txt").write_text(res["stdout"])
    (raw_dir / f"{runtime}{extra_name}.stderr.txt").write_text(res["stderr"])
    (raw_dir / f"{runtime}{extra_name}.exit").write_text(str(res["exit_code"]) + "\n")
    if out_path.exists():
        (raw_dir / f"{runtime}{extra_name}.out.json").write_text(out_path.read_text())
    return {
        "stdout": str(raw_dir / f"{runtime}{extra_name}.stdout.txt"),
        "stderr": str(raw_dir / f"{runtime}{extra_name}.stderr.txt"),
        "exit_code_file": str(raw_dir / f"{runtime}{extra_name}.exit"),
        "output_json": str(out_path) if out_path.exists() else None,
    }


# --------------------------------------------------------------------------------------
# reading an adapter's conformance output


SECTION_KEYS = ("a01", "a0_1", "conformance", "result", "results", "a01_conformance")
# containers the adapter may nest the runtime-side number in, and the keys it may use there
VALUE_CONTAINERS = ("substrate", "runtime", "observed", "e_r_result", "frame_run", "registered_channel")
VALUE_KEYS_IN_CONTAINER = ("scalar", "objective_value", "value", "score", "e_r")
# the runtime-side objective, in the order the implemented adapters spell it
RUNTIME_VALUE_KEYS = ("runtime_scalar", "e_r", "objective_value", "value", "score", "scalar")
RUNTIME_STATUS_KEYS = ("runtime_status", "status", "e_r_status")
ROW_EVIDENCE_KEYS = ("evaluator_evidence", "evidence", "runtime_evidence")
ROW_DIGEST_KEYS = ("canonical_digest", "e_star_canonical_digest")
ROW_SOURCE_KEYS = ("source_sha256", "solution_sha256", "candidate_source_sha256", "candidate_sha256",
                   "e_star_candidate_source_sha256")
# names an adapter may use for the *evaluator identity it actually used* on this row
ROW_IDENTITY_KEYS = ("branch_registered_tree_fingerprint", "registered_tree_fingerprint", "evaluator_id",
                     "manifest_fingerprint", "evaluator_fingerprint", "registered_evaluator_id")
ATTEMPT_CONTAINERS = ("frame_run", "registered_channel", "attempt", "attempts", "substrate", "runtime")


def _nested(rec: dict, container_key: str, key: str):
    container = rec.get(container_key)
    if isinstance(container, dict) and container.get(key) is not None:
        return container[key]
    return None


# Where an adapter may put the two failure-bearing fields `adapter_contract.md` §4.3.5 compares for
# a non-ok candidate. Every runtime spells the container differently (SimpleLoop nests them under
# `reference`/`substrate`, KAPSO under `reference`, EvE and Loreley put them at the top level), so
# the reader looks in all of them before concluding a field is undeclared.
FAILURE_KIND_CONTAINERS = ("substrate", "reference", "runtime", "observed", "frame_run",
                           "registered_channel", "e_r_result", "outcome", "failure", "result",
                           "evaluator_evidence", "evidence")
FAILURE_STAGE_CONTAINERS = FAILURE_KIND_CONTAINERS


def _field_in_containers(rec: dict, names, containers):
    """First non-None value of `names` at the top level or inside a named nested container.

    The nested container may itself be `{"kind": ...}` (EvE's `failure`), so a container whose own
    keys carry the field name is read directly as well.
    """
    for name in names:
        if rec.get(name) is not None:
            return rec[name]
    for container_key in containers:
        for candidate in (rec.get(container_key), _nested(rec, "substrate", container_key),
                          _nested(rec, "reference", container_key)):
            if not isinstance(candidate, dict):
                continue
            for name in names:
                if candidate.get(name) is not None:
                    return candidate[name]
    return None


def declared_failure_kind(rec: dict):
    """The `failure.kind` an adapter's own row declares, wherever it put it."""
    kind = _field_in_containers(rec, ("failure_kind", "failureKind"), FAILURE_KIND_CONTAINERS)
    if isinstance(kind, str):
        return kind
    for container_key in ("failure", "substrate", "reference", "outcome", "result", "observed"):
        block = rec.get(container_key)
        if isinstance(block, dict) and isinstance(block.get("failure"), dict):
            nested = block["failure"].get("kind")
            if isinstance(nested, str):
                return nested
    return None


def declared_failure_stage(rec: dict):
    """The `failure_stage` a row declares, when it declares one at all (most do not)."""
    stage = _field_in_containers(rec, ("failure_stage", "failureStage"), FAILURE_STAGE_CONTAINERS)
    return stage if isinstance(stage, str) and stage in FAILURE_STAGES else None


def failure_stage_for(status, kind):
    """`adapter_contract.md` §5.3: which trace stage an `E*` verdict belongs to."""
    if status == "ok":
        return "none"
    if status == "invalid":
        return "verify_failed"
    if status == "error":
        return FAILURE_STAGE_BY_KIND.get(kind or "", "evaluator_failed")
    return None


def check_failure_kind(row: dict, expected_status, expected_kind, declared_kind, declared_stage):
    """Compare the failure-bearing surface of a row whose `E*` verdict is not `ok` (§4.3.5).

    `status` alone is not enough: two runtimes can agree on "invalid" and disagree on *why* the
    candidate was invalid, and A0-wide `failure_stage` accounting (`plan:577`) is only joinable if
    the kind agrees. Returns a finding dict when the adapter declared something that contradicts
    `E*`, and records what could not be compared on the row itself.

    An adapter that declares **no** kind for a non-ok candidate has not produced the comparison
    surface §4.3.5 asks for, so that row does not agree either: it gets `UNDECLARED_FAILURE_KIND`
    and the `E-r-failure-kind` check reports it (the fatal finding is raised by the caller, which
    also sees rows that took the declared-synthetic-trap path).
    """
    expected_stage = failure_stage_for(expected_status, expected_kind)
    row["e_star_failure_kind"] = expected_kind
    row["e_r_failure_kind"] = declared_kind
    row["e_star_failure_stage"] = expected_stage
    row["e_r_failure_stage"] = declared_stage
    row["failure_kind_declared"] = declared_kind is not None
    if row["verdict"] == MISMATCH_DIGEST:
        # the identity of the evaluated thing already failed; do not stack a second verdict on it
        return None
    if declared_kind is None:
        if expected_kind is not None or expected_status not in (None, "ok"):
            row["verdict"] = UNDECLARED_KIND
            row["notes"].append(
                f"E* reached {expected_status!r} with failure.kind {expected_kind!r}; the adapter "
                "declared no failure.kind for this candidate, so the row does not carry the "
                "(verdict, failure.kind) surface adapter_contract.md §4.3.5 compares"
            )
        return None
    if declared_kind == expected_kind:
        finding = None
    else:
        row["verdict"] = MISMATCH_KIND
        row["notes"].append(
            f"failure.kind {declared_kind!r} != E*'s {expected_kind!r} for a candidate whose E* verdict "
            f"is {expected_status!r}: the verdict agrees but the failure does not, which is exactly the "
            "mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3)"
        )
        finding = {
            "finding_id": FALSE_GREEN_KIND,
            "candidate_id": row["candidate_id"],
            "verdict": MISMATCH_KIND,
            "fatal": True,
            "detail": (
                f"E* verdict {expected_status!r} / failure.kind {expected_kind!r} (stage "
                f"{expected_stage!r}); the adapter reported status {row.get('e_r_status')!r} / "
                f"failure.kind {declared_kind!r}"
            ),
            "protocol": "adapter_contract.md:259 (§4.3.5), plan:577",
        }
    if declared_stage is not None and expected_stage is not None and declared_stage != expected_stage:
        row["verdict"] = MISMATCH_STAGE
        row["notes"].append(
            f"declared failure_stage {declared_stage!r} != the frozen §5.3 stage {expected_stage!r} for "
            f"failure.kind {expected_kind!r}"
        )
        finding = {
            "finding_id": FALSE_GREEN_STAGE,
            "candidate_id": row["candidate_id"],
            "verdict": MISMATCH_STAGE,
            "fatal": True,
            "detail": (
                f"E* failure.kind {expected_kind!r} maps to failure_stage {expected_stage!r} "
                f"(adapter_contract.md §5.3); the adapter declared {declared_stage!r}"
            ),
            "protocol": "adapter_contract.md §5.3, plan:577",
        }
    return finding


def normalise_adapter_output(doc: dict, runtime: str) -> dict:
    """Tolerantly read an adapter's `conformance` output.

    The frozen shape is `a0.adapter.conformance/v1` (README). Two adapters now exist and each
    published its own spelling of the same information, so the reader accepts:

    * the rows at the top level under `candidates` / `results`, or inside a section object
      (`a01`, `conformance`, ...) -- `section_key` records which;
    * the runtime side's number as `runtime_scalar` (`eve`), `substrate.scalar` (`simpleloop`),
      `objective.value`, `e_r`, `value`, `score` or `scalar`;
    * the runtime side's verdict as `runtime_status` / `status` / `substrate.status`;
    * `theta_E` as well as `theta_e`, with `n`/`runs`/... allowed to live under `extra`;
    * evidence from `evaluator_evidence` or as the flat `runtime_evidence_status` +
      `runtime_evidence_detail` pair.

    Aliases exist so that a partly finished adapter is still *measurable* rather than silently
    skipped. They never relax the comparison: the adapter's numbers are still checked against
    `E_STAR.json`, and the adapter's own verdict field is recorded but never used.
    """
    section_key = None
    section = doc
    if not (doc.get("candidates") or doc.get("results")):
        for key in SECTION_KEYS:
            candidate = doc.get(key)
            if isinstance(candidate, dict) and (candidate.get("candidates") or candidate.get("results")):
                section, section_key = candidate, key
                break
        else:
            for key, candidate in doc.items():
                if isinstance(candidate, dict) and (candidate.get("candidates") or candidate.get("results")):
                    section, section_key = candidate, key
                    break

    def pick(*keys, default=None):
        for source in (section, doc):
            for key in keys:
                if isinstance(source, dict) and source.get(key) is not None:
                    return source[key]
        return default

    out = {
        "schema": pick("schema"),
        "section_key": section_key,
        "runtime": pick("runtime", default=runtime),
        "eid_star": pick("eid_star", "eid", "eidStar"),
        "eid_r": doc.get("eid_r") or doc.get("eidR") or section.get("eid_r"),
        "theta_e": pick("theta_e", "thetaE", "theta_E"),
        "epsilon": pick("epsilon"),
        "primary_field": pick("primary_field", "primaryField", default=PRIMARY_FIELD),
        "declared_fr": pick("fr"),
        "declared_state": pick("state"),
        "blocked_reason": pick("blocked_reason", "reason"),
        "traces": pick("traces", "trace_paths"),
        "run_dir": pick("run_dir", "run_root"),
        "failure_stage_counts": pick("failure_stage_counts", "failure_stages", "counters"),
        "adapter_verdict": pick("verdict", "a0_1_verdict") or section.get("verdict"),
        "unverified": doc.get("UNVERIFIED") or doc.get("unverified"),
        "seams": doc.get("seams"),
        "rows": [],
    }
    records = section.get("candidates") or section.get("results") or []
    if isinstance(records, dict):
        records = [dict(v, candidate_id=k) if isinstance(v, dict) else {"candidate_id": k, "value": v}
                   for k, v in records.items()]
    for rec in records:
        if not isinstance(rec, dict):
            continue
        value = None
        status_hint = None
        for container_key in VALUE_CONTAINERS:
            container = rec.get(container_key)
            if not isinstance(container, dict):
                continue
            if any(key in container for key in VALUE_KEYS_IN_CONTAINER):
                for key in VALUE_KEYS_IN_CONTAINER:
                    if key in container:
                        value = container[key]
                        break
                nested_status = container.get("status")
                status_hint = nested_status if isinstance(nested_status, str) else None
                break
        if status_hint is None:
            # e.g. KAPSO records the runtime's verdict on `registered_channel`, not on `frame_run`
            for container_key in VALUE_CONTAINERS:
                container = rec.get(container_key)
                if isinstance(container, dict) and isinstance(container.get("status"), str):
                    status_hint = container["status"]
                    break
        objective = rec.get("objective")
        if value is None and isinstance(objective, dict) and "value" in objective:
            value, status_hint = objective.get("value"), objective.get("status")
        elif value is None and not isinstance(objective, dict) and objective is not None:
            value = objective
        if value is None:
            for key in RUNTIME_VALUE_KEYS:
                if rec.get(key) is not None:
                    value = rec[key]
                    break
        status = None
        for key in RUNTIME_STATUS_KEYS:
            if isinstance(rec.get(key), str):
                status = rec[key]
                break
        if status is None:
            status = status_hint

        evidence = rec.get("evaluator_evidence") or rec.get("evidence") or {}
        if not evidence:
            flat_status = rec.get("runtime_evidence_status") or rec.get("evidence_status")
            if flat_status is not None:
                evidence = {"status": flat_status,
                            "detail": rec.get("runtime_evidence_detail") or rec.get("evidence_detail")}
        if not evidence:
            # KAPSO publishes evidence freshness inside its per-row `verdict` block
            for key in ("verdict", "checks"):
                block = rec.get(key)
                if isinstance(block, dict) and block.get("evaluator_evidence_status") is not None:
                    evidence = {"status": block["evaluator_evidence_status"],
                                "detail": block.get("evaluator_evidence_detail")}
                    break
        if isinstance(evidence, str):
            evidence = {"status": evidence}

        identity_echo = None
        for key in ROW_IDENTITY_KEYS:
            if rec.get(key):
                identity_echo = rec[key]
                break
        attempt = {}
        for container_key in ATTEMPT_CONTAINERS:
            container = rec.get(container_key)
            if not isinstance(container, dict):
                continue
            attempts = container.get("attempts")
            first = attempts[0] if isinstance(attempts, list) and attempts and isinstance(attempts[0], dict) else None
            for candidate in (first, container):
                if isinstance(candidate, dict):
                    for key in ("fidelity", "fraction", "seed"):
                        if candidate.get(key) is not None:
                            attempt.setdefault(key, candidate[key])
            if identity_echo is None and first is not None and first.get("evaluator_id"):
                identity_echo = first["evaluator_id"]
            triple = container.get("manifest_triple")
            if isinstance(triple, dict):
                for key in ("fidelity", "fraction", "seed"):
                    if triple.get(key) is not None:
                        attempt.setdefault(key, triple[key])
                attempt["triple"] = {k: v for k, v in triple.items() if k != "has_score_key"}
            # the class the runtime was *told* to use, parsed from the command it was handed
            command = container.get("command")
            if isinstance(command, str) and "--fidelity" in command:
                commanded = re.search(r"--fidelity[= ]+(\S+)", command)
                if commanded:
                    attempt["commanded_class"] = commanded.group(1)
                told_fraction = re.search(r"--fraction[= ]+(\S+)", command)
                if told_fraction:
                    attempt.setdefault("commanded_fraction", told_fraction.group(1))
                attempt.setdefault("command", command)
                if attempt.get("fidelity"):
                    attempt.setdefault("granted_class", attempt["fidelity"])
            manifest = container.get("manifest")
            if isinstance(manifest, dict):
                if manifest.get("fidelity") is not None and not attempt.get("granted_class"):
                    attempt["granted_class"] = manifest["fidelity"]
                if manifest.get("fraction") is not None and not attempt.get("granted_fraction"):
                    attempt["granted_fraction"] = manifest["fraction"]
        if not attempt:
            attempt = rec.get("theta_e_attempt") or rec.get("theta_E_attempt") or {}

        source = None
        for key in ROW_SOURCE_KEYS:
            source = rec.get(key) or _nested(rec, "substrate", key) or _nested(rec, "runtime_score", key)
            if source:
                break
        digest = None
        for key in ROW_DIGEST_KEYS:
            digest = rec.get(key) or _nested(rec, "substrate", key) or _nested(rec, "runtime_score", key)
            if digest:
                break

        exit_code = None
        for candidate_source in (rec, rec.get("substrate"), rec.get("runtime"), rec.get("observed")):
            if isinstance(candidate_source, dict) and candidate_source.get("exit_code") is not None:
                exit_code = candidate_source["exit_code"]
                break
        if exit_code is None:
            for key in ("runtime_exit_code", "runtime_rc"):
                if rec.get(key) is not None:
                    exit_code = rec[key]
                    break

        out["rows"].append(
            {
                "candidate_id": first_present(rec, ["candidate_id", "id", "candidate"]),
                "status": status,
                "value": as_float(value),
                "exit_code": exit_code,
                "failure_kind": declared_failure_kind(rec),
                "failure_stage": declared_failure_stage(rec),
                "source_sha256": source,
                "canonical_digest": digest,
                "classification": rec.get("classification"),
                "evidence": evidence,
                "identity_echo": identity_echo,
                "theta_e_attempt": attempt,
                "adapter_row_verdict": rec.get("pass") if isinstance(rec.get("pass"), bool) else rec.get("verdict"),
                "raw": rec,
            }
        )
    return out


def parse_output_file(path: Path):
    try:
        return load_json(path), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def find_nested_conformance_doc(run_dir, runtime: str):
    """Find an A0.1 document an adapter wrote inside `--run-dir` instead of to `--out`.

    KAPSO's `run` writes `<run_dir>/a01/conformance.json` (plus `<run_dir>/run.json`, which names
    the traces) while its `conformance` subcommand writes only to `--out`. Both are the adapter's
    own output, so both are usable; the report records which file the numbers came from.
    """
    if not run_dir or not Path(run_dir).is_dir():
        return None, None
    root = Path(run_dir)
    patterns = ("a01/conformance.json", "conformance.json", "a01/*conformance*.json", "*conformance*.json")
    seen = set()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file() or path.stat().st_size == 0:
                continue
            seen.add(path)
            try:
                doc = load_json(path)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(doc, dict) and normalise_adapter_output(doc, runtime)["rows"]:
                return doc, path
    return None, None


def harvest_run_json_traces(run_dir, runtime: str) -> dict:
    """Pull trace paths out of an adapter's own `<run_dir>/run.json` summary."""
    if not run_dir:
        return {}
    path = Path(run_dir) / "run.json"
    if not path.exists():
        return {}
    try:
        data = load_json(path)
    except Exception:  # noqa: BLE001
        return {}
    found = {}

    def walk(node, depth=0):
        if depth > 4:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "trace_paths" and isinstance(value, dict):
                    for kind in ("score", "selection", "resource"):
                        if value.get(kind):
                            found.setdefault(kind, value[kind])
                else:
                    walk(value, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, str):
            for kind in ("score", "selection", "resource"):
                if node.endswith(f".{kind}.jsonl"):
                    found.setdefault(kind, node)

    walk(data)
    return found


def score_trace_rows(trace: Path, primary_field: str):
    """Fallback path: read the adapter's own score trace instead of a conformance document."""
    rows = []
    problems = []
    if not trace.exists():
        return rows, [f"score trace missing: {trace}"]
    for lineno, line in enumerate(trace.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"line {lineno}: {exc}")
            continue
        if event.get("trace") != "score":
            continue
        fields = (event.get("outcome") or {}).get("fields") or {}
        rows.append(
            {
                "candidate_id": event.get("candidate_id"),
                "status": None,
                "value": as_float(fields.get(primary_field)),
                "exit_code": None,
                "failure_kind": declared_failure_kind(event.get("outcome") or event),
                "source_sha256": None,
                "canonical_digest": None,
                "evidence": event.get("evaluator_evidence") or {},
                "theta_e_attempt": {},
                "failure_stage": event.get("failure_stage"),
                "event_id": event.get("event_id"),
                "raw": event,
            }
        )
    if not rows:
        problems.append("no score events in the trace")
    return rows, problems


# --------------------------------------------------------------------------------------
# the A0.1 comparison itself


def evaluate_runtime_rows(runtime: str, obs_rows: list, ref_rows: list, ref_table: dict, expected_eid: str) -> dict:
    ref_by_id = {r["candidate_id"]: r for r in ref_rows}
    table_by_id = {c["candidate_id"]: c for c in ref_table["candidates"]}
    roles = candidate_roles()
    obs_by_id = {}
    duplicates = []
    for row in obs_rows:
        cid = row.get("candidate_id")
        if cid in obs_by_id:
            duplicates.append(cid)
        obs_by_id[cid] = row

    out_rows = []
    findings = []
    for cid in [c["candidate_id"] for c in ref_table["candidates"]]:
        ref = ref_by_id.get(cid, {})
        table = table_by_id.get(cid, {})
        obs = obs_by_id.get(cid)
        row = {
            "runtime": runtime,
            "candidate_id": cid,
            "role": roles.get(cid) or table.get("role"),
            "e_star_status": table.get("status"),
            "e_star_value": as_float(table.get("objective_value")),
            "e_star_failure_kind": table.get("failure_kind"),
            "e_star_failure_stage": failure_stage_for(table.get("status"), table.get("failure_kind")),
            "reference_value_fresh_sweep": ref.get("objective_value"),
            "e_r_status": None,
            "e_r_value": None,
            "e_r_failure_kind": None,
            "e_r_failure_stage": None,
            "failure_kind_declared": None,
            "delta": None,
            "e_r_exit_code": None,
            "evaluator_evidence_status": None,
            "verdict": MISSING,
            "notes": [],
        }
        if obs is None:
            row["notes"].append("adapter reported no row for this candidate")
            out_rows.append(row)
            continue

        evidence = obs.get("evidence") or {}
        ev_status = evidence.get("status")
        row["e_r_status"] = obs.get("status")
        row["e_r_value"] = obs.get("value")
        row["e_r_exit_code"] = obs.get("exit_code")
        row["evaluator_evidence_status"] = ev_status
        if obs.get("value") is not None and table.get("objective_value") is not None:
            row["delta"] = obs["value"] - as_float(table.get("objective_value"))

        expected_status = table.get("status")
        expected_value = as_float(table.get("objective_value"))
        classification = str(obs.get("classification") or "")
        claims_match = bool(obs.get("adapter_row_verdict")) or "match" in classification.lower()
        # Record the failure-bearing surface before any verdict branch runs: a row that is accepted
        # as a declared synthetic failure still has to say *what* failed, and the coverage this
        # check reports must not silently exclude the rows that took the trap path (§4.3.5).
        row["e_r_failure_kind"] = obs.get("failure_kind")
        row["e_r_failure_stage"] = obs.get("failure_stage")
        row["failure_kind_declared"] = obs.get("failure_kind") is not None

        # 1. identity of the thing evaluated: the adapter must not have swapped candidates
        if obs.get("canonical_digest") and table.get("canonical_digest"):
            if obs["canonical_digest"] != table["canonical_digest"]:
                row["verdict"] = MISMATCH_DIGEST
                row["notes"].append(
                    f"canonical_digest {obs['canonical_digest']} != E*'s {table['canonical_digest']} "
                    "(a different file was evaluated, or stale state was reused)"
                )
        if obs.get("source_sha256") and table.get("source_sha256"):
            if obs["source_sha256"] != table["source_sha256"]:
                row["verdict"] = MISMATCH_DIGEST
                row["notes"].append("reported candidate source sha256 does not match C*")

        # 2. the two named false-green traps (plan:551-552)
        declared_synthetic = ev_status == "synthesized_failure" or "synthetic" in classification.lower()
        if ev_status in NON_FRESH_EVIDENCE or ev_status == "synthesized_failure":
            if (
                ev_status == "synthesized_failure"
                and expected_value is None
                and declared_synthetic
                and not claims_match
                and str(obs.get("status") or "") not in ("ok",)
            ):
                # the trap was hit, detected and declared: the runtime's 0.0 is synthetic and the
                # adapter does not present it as a measurement of E*. Acceptable, and recorded so
                # that this 0.0 is never compared against c14's genuine near-zero.
                row["verdict"] = SYNTHETIC_DECLARED
                expected_kind = table.get("failure_kind")
                declared_kind = obs.get("failure_kind")
                if declared_kind is not None and expected_kind is not None and declared_kind != expected_kind:
                    # not fatal here -- the trap path is about the *number*, and this row is not
                    # presented as a measurement -- but a wrong kind is still a wrong kind, and the
                    # study's FailureStage counts join on it (adapter_contract.md §4.3.5).
                    row["notes"].append(
                        f"declared failure.kind {declared_kind!r} != E*'s {expected_kind!r} even though this "
                        "row is accepted as a declared synthetic failure"
                    )
                row["notes"].append(
                    f"E* returned {expected_status}/null; the runtime's own lane reported "
                    f"{obs.get('value')!r} as a synthesised failure (declared: {evidence.get('detail')!r})"
                )
                findings.append(
                    {
                        "finding_id": "TRAP-SYNTHETIC-DECLARED",
                        "candidate_id": cid,
                        "verdict": SYNTHETIC_DECLARED,
                        "detail": (
                            "the EvE failure_score(0.0) trap was hit and declared, not hidden: "
                            f"{str(evidence.get('detail'))[:300]}"
                        ),
                        "protocol": "plan:551",
                        "fatal": False,
                    }
                )
            else:
                row["verdict"] = evidence_verdict(ev_status)
                findings.append(
                    {
                        "finding_id": evidence_finding_id(ev_status),
                        "candidate_id": cid,
                        "verdict": row["verdict"],
                        "detail": non_fresh_detail(cid, table, obs, evidence, expected_value),
                        "protocol": "plan:551-552",
                        "fatal": True,
                    }
                )
                findings.extend(cap_findings(cid, evidence, row["verdict"]))
            out_rows.append(row)
            continue

        fg = check_attempt_invariants(cid, obs)
        if fg:
            findings.extend(fg)
            row["verdict"] = fg[0]["verdict"]
            out_rows.append(row)
            continue

        # 2b. the failure-bearing surface (adapter_contract.md §4.3.5): for a candidate E* did not
        # accept, `status` alone is not the verdict -- the kind must agree too, and it is the kind
        # that decides the trace `failure_stage` (and therefore plan:577's counts). Rows whose
        # evidence is a declared non-fresh trap returned above, so a declared synthetic failure is
        # never second-guessed here.
        kind_finding = check_failure_kind(
            row, expected_status, table.get("failure_kind"), obs.get("failure_kind"),
            obs.get("failure_stage"),
        )
        if kind_finding:
            findings.append(kind_finding)

        if row["verdict"] in (MISMATCH_DIGEST, MISMATCH_KIND, MISMATCH_STAGE, UNDECLARED_KIND):
            out_rows.append(row)
            continue

        # 3. the acceptance formula, with the reference side taken from the frozen table
        if expected_value is None:
            # a candidate with no number: the verdict must be compared as a verdict
            if obs.get("value") is not None:
                row["verdict"] = FALSE_GREEN_ZERO if abs(obs["value"]) <= EPSILON else MISMATCH_NULL
                row["notes"].append(
                    f"E* returned {expected_status}/null for this candidate (no number exists); "
                    f"the adapter reported the number {obs['value']!r}"
                )
                findings.append(
                    {
                        "finding_id": "FG-EVE-ZERO" if row["verdict"] == FALSE_GREEN_ZERO else "FG-VALUE-WHERE-NULL",
                        "candidate_id": cid,
                        "verdict": row["verdict"],
                        "fatal": True,
                        "detail": (
                            f"E*(c)={expected_status} with objective=null, adapter reported "
                            f"{obs['value']!r} with status={obs.get('status')!r}; a crash or a rejected "
                            "candidate recorded as a number is indistinguishable from a real measurement "
                            "(plan:551)"
                        ),
                        "protocol": "plan:551-552",
                    }
                )
            elif obs.get("status") not in (None, expected_status):
                row["verdict"] = MISMATCH_STATUS
                row["notes"].append(
                    f"E* status {expected_status!r}, adapter reported {obs.get('status')!r} (both have no number)"
                )
            else:
                row["verdict"] = MATCH_VERDICT
                row["notes"].append(
                    f"no objective on either side; verdict compared: E*={expected_status}, adapter={obs.get('status')!r}"
                )
        else:
            if obs.get("value") is None:
                row["verdict"] = MISMATCH_NULL
                row["notes"].append(
                    f"E* returned the number {expected_value!r} (status {expected_status}); the adapter "
                    "reported no number"
                )
            elif obs.get("status") not in (None, "ok"):
                row["verdict"] = MISMATCH_STATUS
                row["notes"].append(
                    f"E* status {expected_status!r} with objective {expected_value!r}, adapter reported "
                    f"status {obs.get('status')!r}"
                )
            elif abs(obs["value"] - expected_value) <= EPSILON:
                row["verdict"] = MATCH
            else:
                row["verdict"] = MISMATCH_VALUE
                row["notes"].append(
                    f"|{obs['value']!r} - {expected_value!r}| = {abs(obs['value'] - expected_value)!r} "
                    f"> epsilon {EPSILON!r}"
                )
        out_rows.append(row)
    return {"rows": out_rows, "findings": findings, "duplicate_rows": duplicates}


def evidence_verdict(ev_status: str) -> str:
    return {
        "synthesized_failure": FALSE_GREEN_ZERO,
        "timeout": FALSE_GREEN_TIMEOUT,
        "cache_hit": FALSE_GREEN_CACHE,
        "truncated_metrics": FALSE_GREEN_TRUNCATED,
    }.get(ev_status, FALSE_GREEN_ZERO)


def evidence_finding_id(ev_status: str) -> str:
    return {
        "synthesized_failure": "FG-EVE-SYNTH",
        "timeout": "FG-LORELEY-TIMEOUT",
        "cache_hit": "FG-LORELEY-CACHE",
        "truncated_metrics": "FG-LORELEY-TRUNCATED",
        "manifest_mismatch": "FG-MANIFEST-TRIPLE",
        "not_run": "FG-NOT-RUN",
    }.get(ev_status, "FG-UNKNOWN-EVIDENCE")


def non_fresh_detail(cid: str, table: dict, obs: dict, evidence: dict, expected_value) -> str:
    """Phrase the finding so it is obvious which trap fired and why the row cannot pass."""
    ev_status = evidence.get("status")
    detail = evidence.get("detail")
    if ev_status == "synthesized_failure":
        return (
            f"evaluator_evidence.status=synthesized_failure ({detail!r}): the number "
            f"{obs.get('value')!r} is the runtime's failure_score fallback, not a measurement of E* "
            f"(E*(c)={expected_value!r}); audit:1016, workflow/evaluation.py:161-167"
        )
    if ev_status == "timeout":
        return (
            f"evaluator_evidence.status=timeout ({detail!r}): the value {obs.get('value')!r} was synthesised "
            "on a deadline, so it is not evidence that E* ran (core/worker/evaluator.py:2304-2310)"
        )
    if ev_status == "cache_hit":
        return (
            f"evaluator_evidence.status=cache_hit (cached_from_run_id="
            f"{evidence.get('cached_from_run_id')!r}): the value was reused from a previous run, so this row "
            "cannot confirm that the adapter executed E* under the frozen theta_E now (plan:552, config.py:29,561)"
        )
    if ev_status == "truncated_metrics":
        return (
            f"evaluator_evidence.status=truncated_metrics (metrics_dropped={evidence.get('metrics_dropped')!r}): "
            "metrics were dropped at the cap, so the Outcome is not E*'s"
        )
    if ev_status == "manifest_mismatch":
        return (
            f"evaluator_evidence.status=manifest_mismatch ({detail!r}): the granted evaluation class did not "
            "match the commanded one, which counts as an A0.1 failure (plan:538)"
        )
    return f"evaluator_evidence.status={ev_status!r} ({detail!r}): this row is not a fresh measurement"


def cap_findings(cid: str, evidence: dict, verdict: str) -> list:
    """Loreley's 64-metric cap, however the adapter reports it (`plan:552`)."""
    findings = []
    dropped = evidence.get("metrics_dropped")
    count = evidence.get("metrics_count")
    if evidence.get("metrics_truncated") is True or (isinstance(count, int) and count > 64) or (
        isinstance(dropped, int) and dropped > 0
    ):
        findings.append(
            {
                "finding_id": "FG-LORELEY-CAP",
                "candidate_id": cid,
                "verdict": verdict,
                "fatal": True,
                "detail": (
                    f"the 64-metric cap was hit (metrics_dropped={dropped!r}, metrics_count={count!r}, "
                    f"metrics_truncated={evidence.get('metrics_truncated')!r}): the Outcome is not E*'s "
                    "(core/worker/evaluator.py:2304-2310, plan:552)"
                ),
                "protocol": "plan:552",
            }
        )
    return findings


def check_attempt_invariants(cid: str, obs: dict) -> list:
    """Per-attempt invariants that do not depend on evidence freshness.

    * KAPSO's D16 rule: the granted evaluation class must equal the commanded one
      (`plan:532-539`) -- a mismatch makes the round an A0.1 failure.
    * the attempt's `theta_E` must equal the frozen `theta_E` (`plan:518`).
    """
    findings = []
    attempt = obs.get("theta_e_attempt") or {}
    if not attempt:
        return findings
    granted = first_present(attempt, ["granted_class", "granted", "manifest_class"])
    commanded = first_present(attempt, ["commanded_class", "commanded", "told_class"])
    triple = attempt.get("triple") or attempt
    class_mismatch, theta_mismatch = [], []
    if granted and commanded and granted != commanded:
        class_mismatch.append(f"granted_class {granted!r} != commanded_class {commanded!r}")
    for key, want in (("fidelity", THETA_E["fidelity"]), ("fraction", THETA_E["fraction"]), ("seed", THETA_E["seed"])):
        got = triple.get(key)
        if got is not None and got != want:
            theta_mismatch.append(f"attempt {key}={got!r} != theta_E {want!r}")
    if class_mismatch:
        findings.append(
            {
                "finding_id": "FG-MANIFEST-TRIPLE",
                "candidate_id": cid,
                "verdict": FALSE_GREEN_TRIPLE,
                "fatal": True,
                "detail": "; ".join(class_mismatch) + " (plan:532-539: such a round is an A0.1 failure)",
                "protocol": "plan:532-539",
            }
        )
    elif theta_mismatch:
        findings.append(
            {
                "finding_id": "FG-ATTEMPT-THETA-DRIFT",
                "candidate_id": cid,
                "verdict": FALSE_GREEN_TRIPLE,
                "fatal": True,
                "detail": "; ".join(theta_mismatch) + " (theta_E must be identical across wrappers, plan:518)",
                "protocol": "plan:518",
            }
        )
    return findings



def check_adapter_identity(adapter_doc: dict, expected_eid: str, runtime: str) -> list:
    """EID_r must be derived from EID*, and the derivation must be recomputable (plan:517)."""
    checks = []

    def add(check_id, ok, detail, **extra):
        checks.append({"check_id": check_id, "ok": bool(ok), "detail": detail, **extra})

    eid_star = adapter_doc.get("eid_star")
    add(
        "EID-star-verbatim",
        eid_star == expected_eid,
        f"adapter carried eid_star={eid_star!r}; expected {expected_eid!r} (verbatim copy required)"
        if eid_star
        else "adapter output carries no eid_star",
    )

    eid_r = adapter_doc.get("eid_r") or {}
    if not eid_r:
        add("EID-r-declared", False, "adapter output declares no eid_r mapping")
        return checks

    derives = eid_r.get("derives_from_eid_star")
    add(
        "EID-r-derives-from-EID-star",
        derives == expected_eid,
        f"eid_r.derives_from_eid_star={derives!r}",
    )
    add(
        "EID-r-declaration-present",
        bool(eid_r.get("declaration")) and bool(eid_r.get("native_scheme")) and bool(eid_r.get("mapping_mode")),
        f"native_scheme={eid_r.get('native_scheme')!r} mapping_mode={eid_r.get('mapping_mode')!r} "
        f"recomputable={eid_r.get('recomputable')!r}",
    )

    recompute = eid_r.get("recompute_cmd") or eid_r.get("recompute_command")
    if recompute:
        argv = recompute if isinstance(recompute, list) else shlex.split(str(recompute))
        res = run_cmd(argv, cwd=A0, timeout=300)
        recomputed = None
        text = (res["stdout"] or "").strip()
        if res["exit_code"] == 0 and text:
            try:
                payload = json.loads(text)
                recomputed = payload.get("value") if isinstance(payload, dict) else payload
            except json.JSONDecodeError:
                recomputed = text.splitlines()[-1].strip()
        add(
            "EID-r-recomputes",
            res["exit_code"] == 0 and recomputed is not None and recomputed == eid_r.get("value"),
            f"ran {argv}: exit {res['exit_code']}, recomputed={recomputed!r}, declared value={eid_r.get('value')!r}",
            stdout_tail="\n".join((res["stdout"] or "").splitlines()[-10:]),
            stderr_tail="\n".join((res["stderr"] or "").splitlines()[-10:]),
        )
    else:
        recipe = eid_r.get("derivation") or {}
        if isinstance(recipe, dict) and recipe.get("payload_canonical") and recipe.get("domain"):
            payload = recipe["payload_canonical"].encode("ascii")
            digest = hashlib.sha256(recipe["domain"].encode("ascii") + b"\x00" + payload).hexdigest()
            add(
                "EID-r-recomputes",
                digest == eid_r.get("value"),
                f"recomputed {recipe['domain']} digest = {digest}; declared value = {eid_r.get('value')!r}",
            )
        elif eid_r.get("mapping_mode") == "adapter_declared_injection":
            declaration = str(eid_r.get("declaration") or "")
            names_inputs = any(word in declaration for word in ("sha256", "digest", "hash", "EID*"))
            verbatim = eid_r.get("declarations_verbatim_from") == expected_eid or eid_r.get("value") == expected_eid
            add(
                "EID-r-recomputes",
                bool(declaration) and (verbatim or names_inputs),
                (
                    "adapter_declared_injection: the adapter pins EID* itself and states the derivation in prose "
                    f"({declaration[:200]!r}); the runner could NOT recompute the value (no recompute_cmd, no "
                    "canonical recipe), so `recomputable: true` remains the adapter's declaration, backed by a "
                    "named recipe rather than by an executed check"
                )
                if not verbatim
                else "adapter_declared_injection: EID_r is EID* itself, copied verbatim",
                recompute_mode="declared_prose" if not verbatim else "verbatim",
            )
        elif eid_r.get("mapping_mode") == "native":
            # A native scheme (KAPSO's manifest fingerprint) needs no recipe to be *cross-checked*:
            # the identity the adapter declares once must be the identity recorded on every attempt.
            declared = str(eid_r.get("value") or "")
            tail = declared.split(":", 1)[-1]
            echoes = {
                str(row.get("identity_echo"))
                for row in adapter_doc["rows"]
                if row.get("identity_echo")
            }
            consistent = bool(echoes) and all(echo == tail or echo == declared for echo in echoes)
            add(
                "EID-r-recomputes",
                consistent,
                (
                    f"native scheme {eid_r.get('native_scheme')!r}: the declared EID_r {declared!r} matches the "
                    f"evaluator identity recorded on all {len(adapter_doc['rows'])} rows "
                    f"({len(echoes)} distinct value(s), e.g. {sorted(echoes)[:1]}); the runner did NOT recompute "
                    "the fingerprint itself (no recompute_cmd), it cross-checked it against the attempt records"
                    if consistent
                    else f"native scheme {eid_r.get('native_scheme')!r} with declared EID_r {declared!r}, but the "
                    f"per-row evaluator identities {sorted(echoes) or 'are not recorded'}, so the mapping cannot "
                    "be tied to what actually ran (plan:517)"
                ),
                recompute_mode="cross_checked_against_attempts" if consistent else "absent",
            )
        else:
            add(
                "EID-r-recomputes",
                False,
                "no recompute_cmd and no canonical derivation recipe: a third party cannot recompute EID_r, "
                "so the declaration cannot be backed (plan:517)",
                recompute_mode="absent",
            )
    for check in checks:
        if check["check_id"] == "EID-r-recomputes" and "recompute_mode" not in check:
            check["recompute_mode"] = "executed"
    return checks


def manifest_echoes(node, _depth=0) -> list:
    """Collect every `E_STAR_MANIFEST {...}` line an adapter's own evidence text carries.

    This is the strongest thing an adapter can hand over without being trusted: E*'s own
    manifest, echoed from inside the runtime, names the evaluator source digest, the theta_E it
    ran at and the candidate's canonical digest. Some adapters nest that text several JSON
    escaping layers deep, so each string is retried after decoding and unescaping.
    """
    found = []

    def scan_text(text: str):
        for variant in (text, text.replace('\\"', '"')):
            idx = variant.find("E_STAR_MANIFEST ")
            while idx >= 0:
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(variant[idx + len("E_STAR_MANIFEST ") :].lstrip())
                    if isinstance(parsed, dict) and str(parsed.get("schema", "")).startswith("e_star.manifest"):
                        found.append(dict(parsed, echo_form="manifest_line"))
                except ValueError:
                    pass
                idx = variant.find("E_STAR_MANIFEST ", idx + 1)

    def walk(value, depth):
        if depth > 8:
            return
        if isinstance(value, str):
            scan_text(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(node, _depth)
    return found


def field_echoes(node, _depth=0) -> list:
    """Manifest echoes from an adapter that publishes `E*`'s *fields* instead of the manifest line.

    KAPSO records what `E*` returned under `registered_channel.manifest` as
    `e_star_canonical_digest`, `e_star_evaluator_source_sha256`, `e_star_status`, `e_star_exit_code`
    plus the `(seed, fidelity, fraction)` it ran at, rather than echoing the raw
    `E_STAR_MANIFEST {...}` text. Those are the same facts in a different spelling, so they are
    read as an echo too -- otherwise a runtime that hands over *more* structured evidence than the
    others is reported as having none (audit F2).
    """
    found = []

    def build(block: dict) -> dict:
        echo = {"schema": "e_star.manifest/v1 (fields)", "echo_form": "fields"}
        for key, mapped in FIELD_ECHO_MAP.items():
            for spelling, value in block.items():
                if spelling.lower() == key:
                    echo[mapped] = value
        for key in ("seed", "fidelity", "fraction"):
            if block.get(key) is not None:
                echo[key] = block[key]
        return echo

    def walk(value, depth):
        if depth > 8:
            return
        if isinstance(value, dict):
            keys = {k.lower() for k in value}
            identified = keys & set(FIELD_ECHO_MAP)
            if identified & {"e_star_canonical_digest", "e_star_evaluator_source_sha256"}:
                found.append(build(value))
                return  # the enclosing block is the record; do not also read its children
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(node, _depth)
    return found


def check_manifest_echoes(echo_by_candidate: dict, ref_table: dict) -> dict:
    """Verify the `E*` manifest a runtime echoed back: same frozen evaluator, same outcome."""
    table_by_id = {c["candidate_id"]: c for c in ref_table["candidates"]}
    table = load_json(E_STAR_TABLE)
    frozen_source = (table.get("evaluator") or {}).get("evaluator_source_sha256")
    mismatches, checked = [], 0
    for cid, echoes in echo_by_candidate.items():
        expect = table_by_id.get(cid, {})
        for echo in echoes:
            checked += 1
            if frozen_source and echo.get("evaluator_source_sha256") != frozen_source:
                mismatches.append(
                    f"{cid}: echoed evaluator_source_sha256={echo.get('evaluator_source_sha256')!r} != the frozen "
                    f"E* source digest {frozen_source!r}"
                )
            if expect.get("canonical_digest") and echo.get("canonical_digest") != expect["canonical_digest"]:
                mismatches.append(
                    f"{cid}: echoed canonical_digest={echo.get('canonical_digest')!r} != E_STAR.json's "
                    f"{expect['canonical_digest']!r}"
                )
            if any(echo.get(key) is not None for key in ("seed", "fidelity", "fraction")) and (
                echo.get("seed"), echo.get("fidelity"), echo.get("fraction")
            ) != (
                THETA_E["seed"], THETA_E["fidelity"], THETA_E["fraction"]
            ):
                mismatches.append(
                    f"{cid}: echoed theta=({echo.get('seed')!r},{echo.get('fidelity')!r},{echo.get('fraction')!r}) "
                    f"!= frozen ({THETA_E['seed']!r},{THETA_E['fidelity']!r},{THETA_E['fraction']!r})"
                )
    return {
        "check_id": "E-star-manifest-echo",
        "ok": not mismatches,
        "detail": (
            f"{checked} E* manifest echo(es) across {len(echo_by_candidate)} candidate(s) verify the frozen "
            f"evaluator source digest, the per-candidate canonical digest and theta_E"
            if checked and not mismatches
            else "; ".join(mismatches)[:600]
            if mismatches
            else "no E* manifest echo found in the adapter's own evidence, so this independent confirmation is "
            "unavailable (not a failure: it is a bonus channel)"
        ),
        "echoes_checked": checked,
        "echo_forms": sorted({
            echo.get("echo_form") or "manifest_line"
            for echoes in echo_by_candidate.values() for echo in echoes
        }),
        "candidates_with_echo": sorted(echo_by_candidate),
    }


def evaluate_runtime(runtime: str, adapter_doc: dict, ref_rows: list, ref_table: dict, eid_star: str,
                     epsilon: float, source_note: str, trace_doc_paths=None, strict_duplicates=True) -> dict:
    checks = []
    checks.extend(check_adapter_identity(adapter_doc, eid_star, runtime))

    theta = adapter_doc.get("theta_e") or {}
    theta_extra = theta.get("extra") if isinstance(theta.get("extra"), dict) else {}
    missing_defaults = {}
    ok_theta = True
    theta_keys_present = 0
    for key, want in THETA_E.items():
        got = theta.get(key)
        if got is None:
            got = theta_extra.get(key)
        if got is None:
            defaults = (theta.get("defaults_applied") or {})
            if key in defaults:
                missing_defaults[key] = defaults[key]
            elif key in ("seed", "fidelity", "fraction"):
                ok_theta = False
        else:
            theta_keys_present += 1
            if got != want:
                ok_theta = False

    # An adapter that does not declare theta_E can still be *shown* to have run at it: E*'s own
    # manifest, echoed by the runtime, carries (seed, fidelity, fraction) and the evaluator source
    # digest. `plan:518` wants the declaration; the echo is the next best evidence, and a
    # per-candidate disagreement in the echoes is exactly the KAPSO D16 drift.
    echo_by_candidate = {}
    for obs in adapter_doc["rows"]:
        # the manifest line first (it is E*'s own text); an adapter that publishes E*'s fields
        # instead (KAPSO) is credited through the same check rather than reported as silent (F2).
        echoes = manifest_echoes(obs.get("raw")) or field_echoes(obs.get("raw"))
        if echoes:
            echo_by_candidate[obs["candidate_id"]] = echoes
    observed_theta_tuples = {
        (echo.get("seed"), echo.get("fidelity"), echo.get("fraction"))
        for echoes in echo_by_candidate.values()
        for echo in echoes
        if any(echo.get(key) is not None for key in ("seed", "fidelity", "fraction"))
    }
    want_tuple = (THETA_E["seed"], THETA_E["fidelity"], THETA_E["fraction"])
    theta_observed_ok = bool(observed_theta_tuples) and observed_theta_tuples == {want_tuple}
    if not theta_keys_present and theta_observed_ok:
        ok_theta = True
    checks.append(
        {
            "check_id": "theta-E-identical",
            "ok": ok_theta,
            "detail": (
                f"adapter declares theta_E = {json.dumps(theta, sort_keys=True)}"
                if theta_keys_present
                else (
                    "the adapter does not declare theta_E at the top level (plan:518 asks for it); "
                    f"the runner recovered the theta_E that E* actually ran at from E*'s own manifest echoed "
                    f"inside {len(echo_by_candidate)} of {len(adapter_doc['rows'])} rows: "
                    f"{sorted(observed_theta_tuples)} (expected {{{want_tuple}}}). The adapter should declare "
                    "theta_E explicitly."
                    if theta_observed_ok
                    else "the adapter does not declare theta_E and no consistent theta_E could be recovered from "
                    f"E*'s manifest echoes (observed tuples: {sorted(observed_theta_tuples) or 'none'})"
                )
            )
            + (
                ""
                if theta_keys_present
                else ""
            ),
            "frozen_theta_E": THETA_E,
            "declared": bool(theta_keys_present),
            "observed_from_manifest_echo": sorted(observed_theta_tuples),
            "defaults_applied": missing_defaults,
        }
    )

    echo_check = check_manifest_echoes(echo_by_candidate, ref_table)
    checks.append(echo_check)

    fr = adapter_doc.get("declared_fr") or {}
    fr_hash = fr.get("spec_hash") if isinstance(fr, dict) else None
    checks.append(
        {
            "check_id": "F-r-frozen",
            "ok": fr_hash == BINDING_FR_SPEC_HASH or fr_hash is None,
            "detail": (
                f"adapter declares F_r spec_hash={fr_hash!r}; frozen first-round F_r hash is "
                f"{BINDING_FR_SPEC_HASH!r} (plan:528)"
                if fr_hash
                else "adapter did not declare F_r; the runner assumes the frozen F_r = scalar(E*) "
                "(no fr.spec_hash to compare, so this is not counted as a failure)"
            ),
        }
    )

    cmp_result = evaluate_runtime_rows(runtime, adapter_doc["rows"], ref_rows, ref_table, eid_star)
    rows = cmp_result["rows"]
    findings = cmp_result["findings"]

    expected_ids = [c["candidate_id"] for c in ref_table["candidates"]]
    covered = [r["candidate_id"] for r in rows if r["verdict"] != MISSING]
    coverage_ok = covered == expected_ids
    checks.append(
        {
            "check_id": "candidate-coverage",
            "ok": coverage_ok,
            "detail": f"adapter produced usable rows for {len(covered)}/{len(expected_ids)} members of C*"
            + ("" if coverage_ok else f"; first missing: {next(i for i in expected_ids if i not in covered)}"),
        }
    )

    bad = [r for r in rows if r["verdict"] not in ACCEPTING_VERDICTS]
    checks.append(
        {
            "check_id": "E-r-equals-E-star",
            "ok": not bad,
            "detail": f"{len(rows) - len(bad)}/{len(rows)} candidates agree with E*(c) within epsilon={epsilon:g} "
            f"(or compare equal as verdicts); disagreeing: "
            f"{', '.join(r['candidate_id'] + ':' + r['verdict'] for r in bad) or 'none'}",
        }
    )

    # adapter_contract.md §4.3.5 / §5.3: a candidate E* did not accept is compared on (verdict,
    # failure.kind). This check exists because a truthful `status` with a wrong `failure.kind` -- or
    # with no `failure.kind` at all -- is a false PASS on the *staging* half of A0.1, and it is what
    # plan:577's FailureStage counts join on. An omission is its own non-conformance
    # (`FG-FAILURE-KIND-UNDECLARED`), reported here for every row that took any path, including the
    # rows accepted as declared synthetic failures.
    non_ok_rows = [r for r in rows if r.get("e_star_failure_kind") or r.get("e_star_status") not in (None, "ok")]
    kind_bad = [r for r in rows if r["verdict"] in (MISMATCH_KIND, MISMATCH_STAGE)]
    kind_declared = [r for r in non_ok_rows if r.get("failure_kind_declared")]
    kind_undeclared = [r for r in non_ok_rows if not r.get("failure_kind_declared")]
    for row in kind_undeclared:
        findings.append(
            {
                "finding_id": FALSE_GREEN_KIND_UNDECLARED,
                "candidate_id": row["candidate_id"],
                "verdict": row["verdict"],
                "fatal": True,
                "detail": (
                    f"E* verdict {row.get('e_star_status')!r} / failure.kind "
                    f"{row.get('e_star_failure_kind')!r}, but the adapter's row declares no failure.kind, so "
                    "the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares is absent"
                ),
                "protocol": "adapter_contract.md:259 (§4.3.5), plan:577",
            }
        )
    checks.append(
        {
            "check_id": "E-r-failure-kind",
            "ok": not kind_bad and not kind_undeclared,
            "detail": (
                f"{len(kind_declared)}/{len(non_ok_rows)} candidate(s) whose E* verdict is not `ok` declare a "
                "failure.kind, and every declared kind matches E*'s"
                if not kind_bad and not kind_undeclared
                else (
                    "; ".join(
                        part for part in (
                            "failure-bearing field disagrees with E*: "
                            + ", ".join(f"{r['candidate_id']}:{r['verdict']} "
                                        f"(declared {r.get('e_r_failure_kind')!r}, "
                                        f"E* {r.get('e_star_failure_kind')!r})"
                                        for r in kind_bad)
                            if kind_bad else "",
                            f"{len(kind_undeclared)}/{len(non_ok_rows)} non-ok candidate(s) declare no "
                            f"failure.kind at all ({', '.join(r['candidate_id'] for r in kind_undeclared)}), so "
                            "their rows do not carry the surface §4.3.5 compares"
                            if kind_undeclared else "",
                        )
                        if part
                    )
                )
            ),
            "non_ok_candidates": [r["candidate_id"] for r in non_ok_rows],
            "kind_declared_for": [r["candidate_id"] for r in kind_declared],
            "kind_undeclared_for": [r["candidate_id"] for r in kind_undeclared],
        }
    )

    if cmp_result["duplicate_rows"]:
        dupes = sorted(set(cmp_result["duplicate_rows"]))
        checks.append(
            {
                "check_id": "no-duplicate-candidates",
                "ok": not strict_duplicates,
                "detail": (
                    f"adapter reported more than one row for {dupes}; the last one was kept (a duplicate row "
                    "makes the comparison ambiguous)"
                    if strict_duplicates
                    else f"the score trace carries repeated evaluations for {dupes}; the last event per "
                    "candidate was used (normal for a search run's trace, not a defect)"
                ),
            }
        )

    fatal_non_fresh = [f for f in findings if f.get("fatal") and f["finding_id"] != "TRAP-SYNTHETIC-DECLARED"]
    synthetic_declared = [r["candidate_id"] for r in rows if r["verdict"] == SYNTHETIC_DECLARED]
    undeclared_rows = [
        r for r in rows
        if r.get("evaluator_evidence_status") in NON_FRESH_EVIDENCE and r["verdict"] != SYNTHETIC_DECLARED
    ]
    evidence_declared = any(r.get("evaluator_evidence_status") for r in rows)
    checks.append(
        {
            "check_id": "evidence-fresh-or-declared",
            "ok": not undeclared_rows,
            "detail": (
                f"{len(synthetic_declared)} row(s) carry a declared synthesised failure "
                f"({', '.join(synthetic_declared)}); no row hides a non-fresh number"
                if undeclared_rows == [] and synthetic_declared
                else "every compared row is a fresh measurement (evaluator_evidence.status == ok)"
                if undeclared_rows == []
                else f"{len(undeclared_rows)} row(s) report a non-fresh number without declaring it as such: "
                + ", ".join(f"{r['candidate_id']}={r['evaluator_evidence_status']}" for r in undeclared_rows)
            )
            + (
                ""
                if evidence_declared
                else "; NOTE: no row declares evaluator_evidence.status, so freshness cannot be attested from "
                "the adapter's output and the traps would be invisible here"
            ),
            "evidence_declared_by_adapter": evidence_declared,
            "synthetic_declared_candidates": synthetic_declared,
        }
    )

    state = PASS
    reason = None
    if bad or fatal_non_fresh or not coverage_ok:
        state = FAIL
        if fatal_non_fresh:
            reason = "false-green finding(s): " + ", ".join(sorted({f["finding_id"] for f in fatal_non_fresh}))
        elif not coverage_ok:
            reason = "incomplete coverage of C*"
        else:
            reason = "E_r(c) disagrees with E*(c)"
    elif not all(c["ok"] for c in checks):
        state = FAIL
        reason = "adapter check(s) failed: " + ", ".join(c["check_id"] for c in checks if not c["ok"])

    return {
        "state": state,
        "reason": reason,
        "checks": checks,
        "rows": rows,
        "false_green_findings": findings,
        "synthetic_declared_candidates": synthetic_declared,
        "evidence_source": source_note,
        "traces": adapter_doc.get("traces") or trace_doc_paths,
        "adapter_run_dir": adapter_doc.get("run_dir"),
        "failure_stage_counts": adapter_doc.get("failure_stage_counts"),
        "adapter_declared_verdict": adapter_doc.get("adapter_verdict"),
        "adapter_schema": adapter_doc.get("schema"),
        "adapter_rows_section": adapter_doc.get("section_key") or "top level",
        "adapter_unverified_notes": adapter_doc.get("unverified"),
        "adapter_seams": adapter_doc.get("seams"),
        "a0_2": None,
        "a0_2_note": "owned by the A0.2 workstream (a0/acceptance); this runner does not judge selection semantics",
    }


# --------------------------------------------------------------------------------------
# the run subcommand


def force_rmtree(path: Path) -> None:
    """Remove a tree even if a runtime made files read-only (EvE's solver workspaces do)."""
    try:
        shutil.rmtree(path)
        return
    except OSError:
        pass
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files + dirs:
            try:
                os.chmod(Path(root) / name, 0o700)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)


def prune_run_dirs() -> int:
    """Keep only the newest run directory per (runtime, purpose) so the tree stays readable."""
    root = HERE / "out" / "runs"
    if not root.is_dir():
        return 0
    removed = 0
    groups = {}
    for path in root.iterdir():
        if not path.is_dir():
            continue
        stem = re.sub(r"-\d{8}T\d{6}$", "", path.name)
        groups.setdefault(stem, []).append(path)
    for stem, paths in groups.items():
        for stale in sorted(paths, key=lambda p: p.name)[:-1]:
            force_rmtree(stale)
            removed += 1
    return removed


def cmd_run(args) -> int:
    apply_manifest_override(args)
    started = time.time()
    runtimes = args.runtimes.split(",") if args.runtimes else RUNTIMES
    if args.out is None and sorted(runtimes) != sorted(RUNTIMES):
        # `report.json` is the four-runtime deliverable, and a bare `--runtimes <one>` used to replace
        # it with a one-runtime report (observed three times during this study, each time destroying
        # the aggregate every other workstream reads). A subset run now gets its own file unless the
        # caller asks for report.json explicitly.
        args.out = str(HERE / f"report.{'-'.join(runtimes)}.json")
        print(
            f"NOTE: --runtimes {args.runtimes} with no --out writes {args.out} instead of report.json "
            "(pass --out to choose; report.json is the four-runtime report)"
        )
    adapter_root = Path(args.adapter_root) if args.adapter_root else ADAPTER_ROOT
    # F6: the control rows are fixtures, and a fixture must not leave directories in the study tree.
    # `fixtures/adapters/fixture_common.py` writes only under `$A0_FIXTURE_RUN_ROOT` (or a system
    # temp directory); here the runner owns that root and removes it when the run is over. A caller
    # that sets the variable itself (selftest.py does) keeps control of it.
    fixture_root = os.environ.get(FIXTURE_RUN_ROOT_ENV)
    fixture_root_owned = fixture_root is None
    if fixture_root_owned:
        fixture_root = tempfile.mkdtemp(prefix="a0-conformance-controls-")
        os.environ[FIXTURE_RUN_ROOT_ENV] = fixture_root
        atexit.register(shutil.rmtree, fixture_root, ignore_errors=True)
    overrides = {}
    for item in args.adapter or []:
        name, _, cmd = item.partition("=")
        overrides[name.strip()] = shlex.split(cmd)
    registry_error = adapter_registry().get("_error") if isinstance(adapter_registry(), dict) else None

    cset = load_candidate_set()
    integrity = check_integrity(cset)
    eid_checks = check_eid(getattr(args, "eid_document", None))
    fr = check_fr()
    expected_eid = eid_checks.get("eid_star") or BINDING_EID_STAR
    supplied_document = eid_checks.get("eid_document_supplied") or describe_eid_document(
        EID_DOCUMENT_CHOICES[EID_DOCUMENT_DEFAULT]
    )

    report = {
        "schema": "a0.conformance.report/v1",
        "generated_at": now_iso(),
        "generated_by": "a0/conformance/conformance.py run",
        "step": "A0.1 evaluator integration conformance",
        "protocol": {
            "formula": "for every r in R and every c in C*: E_r(c; theta_E) = E*(c; theta_E) +- epsilon, and EID_r derived from EID* (plan:513-519)",
            "screen": "A0 is a candidate screen, not a collective gate: R_1 = {r : A0.1_r and A0.2_r}, |R_1| >= 1 to continue (plan:490)",
            "f_r": "round one freezes F_r(E*) = scalar(E*) (plan:528)",
            "false_green": "plan:551-552",
        },
        "frozen": {
            "eid_star": expected_eid,
            "eid_star_binding": BINDING_EID_STAR,
            "eid_document": eid_checks.get("eid_document"),
            "eid_document_name": supplied_document.get("label"),
            "eid_document_requested": eid_checks.get("requested"),
            "eid_document_sha256": supplied_document.get("sha256"),
            "eid_document_supplied_to_adapters": supplied_document,
            "candidate_set": cset["manifest_path"],
            "candidate_set_sha256": cset["manifest_sha256"],
            "candidate_ids": cset["ids"],
            "reference_table": str(E_STAR_TABLE),
            "reference_table_sha256": sha256_file(E_STAR_TABLE),
            "epsilon": EPSILON,
            "primary_field": PRIMARY_FIELD,
            "direction": DIRECTION,
            "theta_e": THETA_E,
            "f_star": fr,
            "evaluator": {
                "script": str(E_STAR_SCRIPT.relative_to(A0)),
                "interpreter": str(E_STAR_PYTHON.relative_to(A0)),
                "argv_template": (
                    f"{E_STAR_PYTHON.relative_to(A0)} {E_STAR_SCRIPT.relative_to(A0)} evaluate "
                    "--candidate <C_STAR/<id>> --seed 1337 --fidelity full --fraction 1.0 --n 26 --runs 5 "
                    "--runtime-budget-ms 250.0 --timeout-s 120.0 --out <out.json> --state-dir <state>"
                ),
            },
        },
        "eid": eid_checks,
        "integrity": integrity,
        "runtimes": {},
        "controls": {},
        "env": {
            "cwd": str(Path.cwd()),
            "argv": sys.argv,
            "python": sys.version.split()[0],
            "fixture_run_root": fixture_root if args.controls else None,
            "fixture_run_root_source": (
                "pre-set by the caller" if not fixture_root_owned
                else "created by the runner for the control rows and removed at exit"
            ) if args.controls else None,
        },
        "runtimes_requested": runtimes,
    }
    if sorted(runtimes) != sorted(RUNTIMES):
        report["note"] = (
            f"this report covers {runtimes}, not the study's four runtimes {RUNTIMES}; rows are still "
            "compared against the frozen E_STAR.json table"
        )

    if not integrity["ok"]:
        report_path = Path(args.out) if args.out else HERE / "report.json"
        write_json(report_path, report)
        write_table(report, report_path.with_suffix(".md"))
        print(
            "ABORT: candidate-set integrity failure (adapter_contract.md exit code 4): "
            + json.dumps(integrity["problems"], indent=2),
            file=sys.stderr,
        )
        return EXIT_RUNNER["integrity"]

    ref_doc = load_reference_document(args, report)
    ref_rows = ref_doc["fresh_sweep"]["rows"] if ref_doc else []
    ref_table = load_json(E_STAR_TABLE)
    report["reference"] = {
        "document": ref_doc.get("path") if ref_doc else None,
        "source": "a0/conformance/reference.json (fresh E* sweep) cross-checked against E_STAR.json",
        "agreement_with_frozen_table": (ref_doc or {}).get("agreement_with_frozen_table"),
        "c_star_unchanged_after_sweep": (ref_doc or {}).get("c_star_unchanged_after_sweep"),
        "theta_e": (ref_doc or {}).get("theta_e"),
        "rows": [
            {k: r[k] for k in ("candidate_id", "exit_code", "status", "objective_value", "failure_kind", "canonical_digest")}
            for r in ref_rows
        ],
    }
    if not ref_doc or not (ref_doc.get("agreement_with_frozen_table") or {}).get("reproduces_frozen_table"):
        report["reference"]["warning"] = (
            "the fresh E* sweep did not reproduce E_STAR.json exactly; the frozen reference table is still the "
            "comparison basis, but this must be resolved before any runtime verdict is trusted"
        )

    eid_document = eid_checks.get("eid_document") or str(EID_DOCUMENT_CHOICES[EID_DOCUMENT_DEFAULT])
    for runtime in runtimes:
        print(f"--- {runtime} ---")
        try:
            entry = run_one_runtime(
                runtime, adapter_root, overrides, registry_error, ref_rows, ref_table, expected_eid, eid_document, args
            )
        except Exception as exc:  # noqa: BLE001  -- one runtime must never abort the others
            import traceback

            entry = {
                "state": FAIL,
                "reason": f"runner exception while driving {runtime}: {type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "checks": [],
                "rows": [],
                "false_green_findings": [],
            }
        report["runtimes"][runtime] = entry
        entry.setdefault("eid_document_supplied", supplied_document)
        print(f"    {entry['state']}: {entry.get('reason') or 'all checks passed'}")

    if args.controls:
        print("--- controls (fixture adapters, not runtimes) ---")
        for name, (rel_cmd, why) in CONTROL_ADAPTERS.items():
            parts = [str(HERE / part) if part.endswith(".py") else part for part in shlex.split(rel_cmd)]
            cmd = [sys.executable] + parts
            try:
                entry = run_one_runtime(
                    name, adapter_root, {name: cmd}, None, ref_rows, ref_table, expected_eid, eid_document, args
                )
            except Exception as exc:  # noqa: BLE001
                import traceback

                entry = {"state": FAIL, "reason": f"runner exception on control {name}: {exc}",
                         "traceback": traceback.format_exc(), "checks": [], "rows": [],
                         "false_green_findings": []}
            entry["control_purpose"] = why
            entry["expectation"] = ("PASS" if "must PASS" in why else "FAIL")
            entry["behaved_as_expected"] = entry["state"] == entry["expectation"]
            entry.setdefault("eid_document_supplied", supplied_document)
            report["controls"][name] = entry
            print(f"    {name}: {entry['state']} (expected {entry['expectation']})")

    states = [e["state"] for e in report["runtimes"].values()]
    report["verdicts"] = {
        "a0_1": {r: e["state"] for r, e in report["runtimes"].items()},
        "n_pass": states.count(PASS),
        "n_fail": states.count(FAIL),
        "n_pending": states.count(PENDING),
        "n_blocked": states.count(BLOCKED),
        "r_1_a0_1_only": [r for r, s in report["runtimes"].items() if s.get("state") == PASS],
        "gate": "|R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2",
        "screen_semantics": "each runtime is evaluated independently; no runtime's failure aborted another's run",
    }
    report["exit_code"] = (
        EXIT_RUNNER["fail"]
        if FAIL in states
        else (EXIT_RUNNER["pending"] if any(s in (PENDING, BLOCKED) for s in states) else EXIT_RUNNER["pass"])
    )
    report["duration_sec"] = round(time.time() - started, 3)
    report_path = Path(args.out) if args.out else HERE / "report.json"
    table_path = report_path.with_suffix(".md")
    report["report_path"] = str(report_path)
    report["table_path"] = str(table_path)
    report["tools"] = {
        "runner": str(Path(__file__).resolve()),
        "selftest": str(HERE / "selftest.py"),
        "reference": str(HERE / "reference.json"),
        "frozen_toolchain": check_frozen_toolchain(),
    }
    write_json(report_path, report)
    write_table(report, table_path)
    pruned = prune_run_dirs()
    if pruned:
        print(f"pruned {pruned} superseded run director{'y' if pruned == 1 else 'ies'}")
    print(f"written: {report_path}")
    print(f"written: {table_path}")
    print(f"verdicts (A0.1 only): {json.dumps(report['verdicts']['a0_1'], ensure_ascii=False)}")
    return report["exit_code"]


def load_reference_document(args, report):
    path = Path(args.reference) if args.reference else HERE / "reference.json"
    if not path.exists() or args.refresh_reference:
        theta = dict(THETA_E)
        before = c_star_digest()
        rows = reference_rows(theta, HERE / "out", args.reference_timeout)
        after = c_star_digest()
        doc = {
            "schema": "a0.conformance.reference/v1",
            "generated_at": now_iso(),
            "generated_by": "a0/conformance/conformance.py run (inline refresh)",
            "theta_e": theta,
            "fresh_sweep": {"state_root": str(HERE / "out"), "rows": rows},
            "agreement_with_frozen_table": compare_to_table(rows, load_json(E_STAR_TABLE)),
            "c_star_unchanged_after_sweep": {"before": before, "after": after, "unchanged": before == after},
            "frozen_evaluator": {"eid_star": BINDING_EID_STAR},
        }
        write_json(path, doc)
    else:
        doc = load_json(path)
    doc["path"] = str(path)
    return doc


def run_one_runtime(runtime, adapter_root, overrides, registry_error, ref_rows, ref_table,
                    expected_eid, eid_document, args) -> dict:
    rerun = (
        f"cd {HERE} && python3 conformance.py run --runtimes {runtime} --out report.{runtime}.json"
    )
    base, info = discover_adapter(runtime, adapter_root, overrides, registry_error)
    supplied = describe_eid_document(eid_document)
    revision_before = adapter_revision(info.get("runtime_dir") or (adapter_root / runtime))
    entry = {
        "state": PENDING,
        "reason": None,
        "adapter": info,
        "adapter_revision": revision_before,
        "rerun": rerun,
        "eid_document_supplied": supplied,
        "checks": [],
        "rows": [],
        "false_green_findings": [],
        "a0_2": None,
    }
    if base is None:
        entry["reason"] = (
            f"adapter not runnable yet: {info.get('reason', 'unknown')}; nothing was run for this runtime, "
            "so it is neither passing nor failing"
        )
        return entry

    out_dir = HERE / "out" / "adapters"
    out_dir.mkdir(parents=True, exist_ok=True)
    conformance_out = out_dir / f"{runtime}.conformance.json"
    if conformance_out.exists():
        conformance_out.unlink()
    run_id = f"a01-{runtime}-{time.strftime('%Y%m%dT%H%M%S')}"
    run_dir = HERE / "out" / "runs" / run_id
    # keep the artifact tree tidy: this is a re-runnable command, not an append-only log
    runs_root = HERE / "out" / "runs"
    if runs_root.is_dir():
        for stale in sorted(runs_root.glob(f"a01-{runtime}-*")):
            if stale != run_dir:
                shutil.rmtree(stale, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Launch with cwd = the adapter directory and that directory on PYTHONPATH, mirroring what
    # `uv run --project <adapter_dir>` does for a package entry point. Every path we pass is
    # absolute, so the adapter still must not depend on cwd (hard constraint 1, plan:544).
    adir = adapter_root / runtime
    if adir.is_dir():
        cwd = adir
        path_root = info.get("pythonpath") or str(adir)
        existing = os.environ.get("PYTHONPATH", "")
        env = {"PYTHONPATH": f"{path_root}{os.pathsep}{existing}" if existing else str(path_root)}
    else:
        cwd, env = HERE, None
    entry["launch"] = {"cwd": str(cwd), "pythonpath": (env or {}).get("PYTHONPATH")}

    conformance_cmd = base + [
        "conformance",
        "--runtime", runtime,
        "--candidate-set", str(C_STAR_MANIFEST),
        "--eid", str(eid_document),
        "--theta", theta_to_flag(THETA_E),
        "--epsilon", repr(EPSILON),
        "--out", str(conformance_out),
    ]
    res = run_cmd(conformance_cmd, cwd=cwd, timeout=args.adapter_timeout, env=env)
    entry["conformance_invocation"] = summarise_proc(res, conformance_out)
    entry["raw"] = save_raw(runtime, res, conformance_out, ".conformance")

    doc = None
    read_error = None
    if conformance_out.exists():
        doc, read_error = parse_output_file(conformance_out)
    source_note = "adapter conformance subcommand"
    if doc is None and not conformance_out.exists():
        # fall back to stdout (some adapters only print) then to the `run` + score trace path
        text = (res["stdout"] or "").strip()
        brace = text.find("{")
        if brace >= 0:
            try:
                doc = json.loads(text[brace:])
                source_note = "adapter conformance stdout (no --out file)"
            except json.JSONDecodeError:
                doc = None

    if doc is None:
        trace_rows, trace_problems = (None, None)
        run_cmdline = base + [
            "run",
            "--runtime", runtime,
            "--task", "circle-packing",
            "--candidate-set", str(C_STAR_MANIFEST),
            "--eid", str(eid_document),
            "--theta", theta_to_flag(THETA_E),
            "--fr", str(FR_DECLARATION),
            "--run-id", run_id,
            "--run-dir", str(run_dir),
            "--budget", BUDGET,
            "--traces", TRACES,
        ]
        res2 = run_cmd(run_cmdline, cwd=cwd, timeout=args.adapter_timeout, env=env)
        entry["run_invocation"] = summarise_proc(res2, None)
        entry["raw"]["run"] = save_raw(runtime, res2, Path("/nonexistent"), ".run")

        # Where did this adapter put its A0.1 answer? Three possibilities, best first.
        harvested = harvest_run_json_traces(run_dir, runtime)
        nested_doc, nested_path = find_nested_conformance_doc(run_dir, runtime)
        recursive_traces = discover_traces_anywhere(run_dir, runtime)
        if nested_doc is not None:
            doc = nested_doc
            source_note = (
                f"the adapter's own run output at {nested_path} (its `conformance` subcommand wrote nothing "
                f"usable to --out: exit {res['exit_code']})"
            )
            doc.setdefault("traces", {}) if isinstance(doc.get("traces"), dict) else None
            if not doc.get("traces"):
                doc["traces"] = harvested or recursive_traces or None
        else:
            trace = resolve_reported_path((harvested or recursive_traces).get("score")) if (
                harvested or recursive_traces
            ) else None
            if trace is None:
                trace = run_dir / "traces" / f"{runtime}.{run_id}.score.jsonl"
            trace_rows, trace_problems = score_trace_rows(trace, PRIMARY_FIELD)
            if trace_rows:
                doc = {
                    "schema": "derived-from-score-trace",
                    "runtime": runtime,
                    "eid_star": expected_eid,
                    "epsilon": EPSILON,
                    "primary_field": PRIMARY_FIELD,
                    "candidates": trace_rows,
                    "traces": harvested or recursive_traces or discover_traces(run_dir, runtime, run_id),
                    "note": "no conformance document was produced; rows were read from the score trace (weaker: "
                            "the trace does not carry E*'s ok/invalid/error verdict or the exit code)",
                }
                source_note = f"score trace fallback: {trace}"
        if doc is None:
            entry["state"] = PENDING
            entry["reason"] = (
                f"adapter is present but produced no usable A0.1 output: conformance exit {res['exit_code']}"
                + (f" ({read_error})" if read_error else "")
                + (f"; run exit {res2['exit_code']}" if res2 else "")
                + f"; stderr tail: {(res['stderr'] or '').strip().splitlines()[-1:] or ['<empty>']}"
                + (
                    f"; entry point was a guess ({info.get('source')}) with files seen {info.get('files_seen')}"
                    if info.get("guessed_entry_point")
                    else ""
                )
                + (
                    "; the adapter reported its own internal error (contract exit 10), so nothing about this "
                    "runtime's conformance was measured -- this is a bug in the adapter, not a runtime verdict"
                    if res["exit_code"] == ADAPTER_EXIT_INTERNAL
                    else ""
                )
            )
            entry["detail"] = {
                "conformance_exit": res["exit_code"],
                "run_exit": res2["exit_code"],
                "read_error": read_error,
                "nested_document": str(nested_path) if nested_path else None,
                "score_trace": str(trace) if trace is not None else None,
                "traces_found_by_recursive_search": recursive_traces or None,
                "traces_named_by_run_json": harvested or None,
            }
            entry["exit_code_semantics"] = explain_exit(res["exit_code"])
            return entry

    adapter_doc = normalise_adapter_output(doc, runtime)
    fallback = str(adapter_doc.get("schema") or "").startswith("derived-from-score-trace")
    entry["adapter_declared"] = {
        "schema": adapter_doc["schema"],
        "state": adapter_doc["declared_state"],
        "blocked_reason": adapter_doc["blocked_reason"],
        "verdict": adapter_doc["adapter_verdict"],
        "row_count": len(adapter_doc["rows"]),
    }
    if adapter_doc["declared_state"] in ("blocked", BLOCKED):
        entry["state"] = BLOCKED
        entry["reason"] = (
            "adapter declared itself blocked: " + str(adapter_doc["blocked_reason"] or "no reason given")
        )
        return entry

    result = evaluate_runtime(
        runtime, adapter_doc, ref_rows, ref_table, expected_eid, EPSILON, source_note,
        trace_doc_paths=discover_traces(run_dir, runtime, run_id), strict_duplicates=not fallback,
    )
    if fallback:
        result["fallback"] = {
            "why": (
                "the adapter's `conformance` subcommand produced no usable document, so the rows were read "
                "from the score trace of a `run` invocation instead"
            ),
            "conformance_exit_code": res["exit_code"],
            "conformance_stderr_tail": (res["stderr"] or "").strip().splitlines()[-6:],
            "limitation": (
                "a score trace carries neither eid_r nor theta_E nor E*'s ok/invalid/error verdict, so this "
                "path cannot establish the identity half of A0.1 (plan:517-519)"
            ),
        }
        if result["state"] == FAIL:
            result["reason"] = (
                "A0.1 not established: the numbers agree (14/14 where comparable) but the adapter's "
                "`conformance` subcommand failed (exit "
                f"{res['exit_code']}), so EID_r / theta_E could not be verified from the run's score trace; "
                f"last stderr line: {(res['stderr'] or '').strip().splitlines()[-1:] or ['<none>']}"
            )
    if not result.get("traces"):
        found = discover_traces_anywhere(adapter_doc.get("run_dir"), runtime)
        if found:
            result["traces"] = found
            result["traces_source"] = f"found under the adapter's own run_dir {adapter_doc.get('run_dir')}"
        else:
            searched = search_adapter_tree_for_traces(adapter_root / runtime, runtime)
            if searched:
                result["traces"] = searched
                result["traces_source"] = (
                    "NOT declared by the adapter's conformance output; found by searching the adapter "
                    "directory (these may be a smoke run's traces, e.g. an A0.2 run, not the A0.1 run's)"
                )
    else:
        result["traces_source"] = "reported by the adapter"
    if result.get("failure_stage_counts") is None and result.get("traces"):
        result["failure_stage_counts"] = count_failure_stages(result["traces"])
        if result["failure_stage_counts"]:
            result["failure_stage_counts"]["note"] = (
                "counted by the runner from the adapter's own score trace, since the adapter did not report "
                "counters (plan:577)"
            )
    result["failure_stage_accounting"] = failure_stage_accounting(
        result.get("rows") or [], result.get("failure_stage_counts")
    )
    revision_after = adapter_revision(info.get("runtime_dir") or (adapter_root / runtime))
    result["adapter_revision"] = dict(
        revision_after or revision_before or {},
        **adapter_revision_diff(revision_before, revision_after),
        snapshot_timing="before and after the adapter invocation",
    )
    if not result["adapter_revision"].get("unchanged_during_run", True):
        result["adapter_revision"]["warning"] = (
            "the adapter's source changed while this runtime was being driven, so this verdict may straddle "
            "two revisions; re-run this runtime alone before quoting it"
        )
        print(f"    NOTE: {runtime} source changed during the run: "
              f"{', '.join(result['adapter_revision'].get('changed_files') or [])}")
    result["adapter"] = info
    result["rerun"] = rerun
    result["conformance_invocation"] = entry.get("conformance_invocation")
    result["run_invocation"] = entry.get("run_invocation")
    result["raw"] = entry.get("raw")
    result["adapter_declared"] = entry["adapter_declared"]
    result["exit_code_semantics"] = explain_exit(res["exit_code"])
    return result


def discover_traces(run_dir: Path, runtime: str, run_id: str):
    base = run_dir / "traces" / f"{runtime}.{run_id}"
    found = {}
    for kind in ("score", "selection", "resource"):
        path = Path(f"{base}.{kind}.jsonl")
        if path.exists():
            found[kind] = str(path)
    return found or None


def resolve_reported_path(value):
    """Adapters report paths relative to a0/ (or absolutely); resolve both against the tree."""
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    for base in (A0, A0.parent, HERE):
        candidate = base / path
        if candidate.exists():
            return candidate
    return A0 / path


def discover_traces_anywhere(run_dir, runtime: str) -> dict:
    """Find an adapter's three traces under a `run_dir` it reported itself.

    The runner prefers the traces the adapter names. When it names only a run directory (EvE's
    `run_dir`), this finds `<run_dir>/**/traces/*.{score,selection,resource}.jsonl`, preferring
    files whose names start with the runtime.
    """
    if not run_dir:
        return {}
    root = resolve_reported_path(run_dir)
    if root is None or not root.is_dir():
        return {}
    found = {}
    for kind in ("score", "selection", "resource"):
        candidates = sorted(root.glob(f"traces/*.{kind}.jsonl")) + sorted(root.glob(f"**/traces/*.{kind}.jsonl"))
        if not candidates:
            continue
        preferred = [p for p in candidates if p.name.startswith(runtime)] or candidates
        found[kind] = str(preferred[0])
    return found


def search_adapter_tree_for_traces(adapter_dir, runtime: str) -> dict:
    """Last resort for the study's trace pointers: look for any trace set under the adapter.

    Clearly labelled as a search result, not as a pointer the adapter declared -- an adapter's own
    smoke-run traces are not the A0.1 run's traces.
    """
    if not adapter_dir or not Path(adapter_dir).is_dir():
        return {}
    root = Path(adapter_dir)
    found = {}
    for kind in ("score", "selection", "resource"):
        candidates = [
            p for p in root.glob(f"**/traces/*.{kind}.jsonl")
            if ".venv" not in p.parts and ".uvcache" not in p.parts
        ]
        if not candidates:
            continue
        preferred = [p for p in candidates if p.name.startswith(runtime)] or candidates
        found[kind] = str(max(preferred, key=lambda p: p.stat().st_mtime))
    return found


def failure_stage_accounting(rows: list, counts) -> dict:
    """Compare the FailureStage counts an adapter declares with the frozen §5.3 mapping over C*.

    Recorded, never a verdict. The counts are one unit per (run_id, iteration, candidate_id)
    (`plan:577`, `plan:628`), so they are only comparable to `C*`'s 14 verdicts when the adapter
    published exactly one unit per candidate; when the total says otherwise the counts describe a
    different run and `matches_frozen_map` stays `null` rather than inventing a disagreement. A
    mismatch that *is* comparable matters because every per-runtime FailureStage total in the study
    is meant to be joinable on this table.
    """
    expected = {}
    for row in rows:
        stage = row.get("e_star_failure_stage")
        if stage:
            expected[stage] = expected.get(stage, 0) + 1
    block = counts.get("counts") if isinstance(counts, dict) and isinstance(counts.get("counts"), dict) else counts
    declared = {}
    if isinstance(block, dict):
        declared = {k: v for k, v in block.items() if isinstance(v, int) and not isinstance(v, bool)}
    total = sum(declared.values())
    comparable = bool(declared) and total == len(rows)
    if not declared:
        note = "the adapter declared no FailureStage counts, so nothing could be compared"
    elif not comparable:
        note = (
            f"the declared counts total {total} unit(s) for {len(rows)} candidate(s), so they describe a "
            "different run's units and are not compared against the frozen mapping"
        )
    elif declared == expected:
        note = "the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts"
    else:
        note = (
            "the declared counts do NOT equal the frozen §5.3 mapping applied to C*'s E* verdicts; these "
            "counts are not joinable with the other runtimes' (recorded, not a verdict: A0.1 does not "
            "require the adapter to re-stage E*'s failures)"
        )
    return {
        "declared_counts": declared or None,
        "declared_units": total or None,
        "expected_from_frozen_map": expected,
        "comparable_to_C*": comparable,
        "matches_frozen_map": (declared == expected) if comparable else None,
        "note": note,
    }


def count_failure_stages(trace_paths) -> dict:
    """FailureStage counts straight from the adapter's own traces (`plan:577`, `plan:628`).

    Read rather than trusted: the count is taken from the score trace's `failure_stage` fields,
    keyed by (run_id, candidate_id, iteration) so a failure reported on two traces is not double
    counted.
    """
    if not isinstance(trace_paths, dict) or not trace_paths.get("score"):
        return None
    path = resolve_reported_path(trace_paths["score"])
    if path is None or not path.exists():
        return None
    counts, units = {}, set()
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("trace") != "score":
                continue
            stage = event.get("failure_stage") or "none"
            unit = (event.get("run_id"), event.get("candidate_id"), event.get("iteration"))
            if stage != "none" and unit in units:
                continue
            units.add(unit)
            counts[stage] = counts.get(stage, 0) + 1
    except OSError:
        return None
    return {"source": str(path), "counts": counts}


EXIT_EXPLAIN = {
    0: "run completed within budget; all three traces written",
    2: "usage / configuration error",
    3: "contract mismatch: EID*.json does not describe the evaluator actually wired",
    4: "candidate-set integrity failure",
    5: "A0.1 conformance failure reported by the adapter itself",
    6: "closure violation (autonomous external acquisition observed)",
    7: "budget exhausted",
    8: "no evaluable candidate produced",
    10: "internal adapter error",
}


def explain_exit(code):
    if code is None:
        return {"exit_code": None, "meaning": "adapter did not exit normally (timeout or spawn failure)"}
    return {"exit_code": code, "meaning": EXIT_EXPLAIN.get(code, "unrecognised exit code")}


# --------------------------------------------------------------------------------------
# readable table


def fmt_value(value):
    if value is None:
        return "null"
    return repr(value)


def write_table(report: dict, path: Path) -> None:
    cids = report["frozen"]["candidate_ids"]
    lines = []
    lines.append("# A0.1 cross-adapter conformance report")
    lines.append("")
    lines.append(f"Generated {report['generated_at']} by `a0/conformance/conformance.py run`.")
    lines.append("")
    lines.append(
        "Frozen coordinates: "
        f"`E* = {report['frozen']['evaluator'].get('script', 'a0/tasks/circle-packing/e_star.py')}` "
        f"(`EID* = {report['frozen']['eid_star']}`), "
        f"`EID* document = {report['frozen'].get('eid_document')} "
        f"[{report['frozen'].get('eid_document_name')}]` "
        f"(sha256 `{str(report['frozen'].get('eid_document_sha256'))[:16]}...`), "
        f"`C* = {report['frozen']['candidate_set']}` "
        f"(sha256 `{report['frozen']['candidate_set_sha256'][:16]}...`), "
        f"`theta_E = {json.dumps(report['frozen']['theta_e'])}`, "
        f"`epsilon = {report['frozen']['epsilon']:g}`, "
        f"`F_r: {report['frozen']['f_star']['rule']}`."
    )
    lines.append("")
    lines.append(
        "Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), "
        "`plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the "
        "frozen table `E_STAR.json` itself; an adapter's own verdict is recorded but never trusted."
    )
    lines.append("")
    lines.append("## Verdicts")
    lines.append("")
    lines.append("| runtime | A0.1 | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |")
    lines.append("|---|---|---|---|---|---|")
    for runtime, entry in report["runtimes"].items():
        rows = entry.get("rows") or []
        accept = sum(1 for r in rows if r["verdict"] in ACCEPTING_VERDICTS)
        total = len(report["frozen"]["candidate_ids"])
        breakdown = {}
        for row in rows:
            breakdown[row["verdict"]] = breakdown.get(row["verdict"], 0) + 1
        detail = ", ".join(
            f"{count} {verdict}" for verdict, count in sorted(breakdown.items()) if verdict not in (MATCH, MATCH_VERDICT)
        )
        fg = sorted({f["finding_id"] for f in entry.get("false_green_findings") or []})
        reason = (entry.get("reason") or "all checks passed").replace("|", "/")
        if len(reason) > 160:
            reason = reason[:157] + "..."
        lines.append(
            f"| {runtime} | {entry['state']} | {accept}/{total}{f' ({detail})' if detail else ''} | "
            f"{', '.join(fg) or '-'} | not judged here | {reason} |"
        )
    lines.append("")
    v = report.get("verdicts", {})
    lines.append(
        f"A0.1-only set: `R_1(A0.1) = {v.get('r_1_a0_1_only')}` (n_pass={v.get('n_pass')}, n_fail={v.get('n_fail')}, "
        f"n_pending={v.get('n_pending')}, n_blocked={v.get('n_blocked')}). {v.get('gate','')}"
    )
    lines.append("")

    lines.append("## Reference table reproducibility")
    lines.append("")
    ref = report.get("reference") or {}
    agree = ref.get("agreement_with_frozen_table") or {}
    lines.append(
        f"Fresh sweep of `E*` over `C*` with the frozen invocation reproduces `E_STAR.json` exactly: "
        f"**{agree.get('reproduces_frozen_table')}**; `C*` unchanged by the sweep: "
        f"**{(ref.get('c_star_unchanged_after_sweep') or {}).get('unchanged')}**."
    )
    if ref.get("warning"):
        lines.append("")
        lines.append(f"> WARNING: {ref['warning']}")
    lines.append("")
    lines.append("| candidate | role | E*(c) status | E*(c) value | failure kind | exit |")
    lines.append("|---|---|---|---|---|---|")
    roles = candidate_roles()
    for row in ref.get("rows") or []:
        role = roles.get(row["candidate_id"], "")
        lines.append(
            f"| {row['candidate_id']} | {role} | {row['status']} | {fmt_value(row['objective_value'])} | "
            f"{row['failure_kind'] or '-'} | {row['exit_code']} |"
        )
    lines.append("")

    lines.append("## Per-runtime detail")
    lines.append("")
    lines.append(
        "Row verdicts: `MATCH` (number agrees within epsilon), `MATCH_VERDICT` (no number on either side, "
        "verdicts compared), `SYNTHETIC_DECLARED` (the runtime's lane returned a declared synthetic failure "
        "where E* has no number -- acceptable, but its 0.0 is never a measurement), `FALSE_GREEN_*` "
        "(a number where none exists, or a non-fresh number), `MISMATCH_*`, `MISSING`."
    )
    lines.append("")
    for runtime, entry in report["runtimes"].items():
        lines.append(f"### {runtime} — {entry['state']}")
        lines.append("")
        if entry.get("reason"):
            lines.append(f"Reason: {entry['reason']}")
            lines.append("")
        if entry.get("rerun"):
            lines.append(f"Re-run this runtime with: `{entry['rerun']}`")
            lines.append("")
        if entry.get("adapter_schema"):
            lines.append(
                f"Adapter output: schema `{entry['adapter_schema']}`, rows from "
                f"`{entry.get('adapter_rows_section')}`, adapter's own verdict "
                f"`{entry.get('adapter_declared_verdict')}` (recorded, never trusted), numbers read from "
                f"`{entry.get('evidence_source')}`."
            )
            lines.append("")
        for check in entry.get("checks") or []:
            lines.append(f"- `{'PASS' if check['ok'] else 'FAIL'}` {check['check_id']}: {check['detail']}")
        if entry.get("checks"):
            lines.append("")
        rows = entry.get("rows") or []
        if not rows:
            pending = entry["state"] == PENDING
            lines.append(
                "No rows: the adapter was not driven (nothing was run for this runtime)."
                if pending
                else "No rows were produced."
            )
            lines.append("")
            continue
        lines.append("| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for row in rows:
            lines.append(
                f"| {row['candidate_id']} | {fmt_value(row.get('e_star_value'))} | {fmt_value(row.get('e_r_value'))} | "
                f"{'-' if row.get('delta') is None else format(row['delta'], '.3e')} | {row.get('e_star_status')} | "
                f"{row.get('e_star_failure_kind') or '-'} | {row.get('e_r_failure_kind') or '-'} | "
                f"{row.get('e_r_status')} | {row.get('evaluator_evidence_status') or '-'} | {row['verdict']} | "
                f"{'; '.join(row.get('notes') or []) or '-'} |"
            )
        lines.append("")
        if entry.get("false_green_findings"):
            lines.append("Findings (false-green traps and attempt invariants):")
            lines.append("")
            grouped = {}
            for finding in entry["false_green_findings"]:
                grouped.setdefault(finding["finding_id"], []).append(finding)
            for finding_id, members in grouped.items():
                severity = "**fatal**" if members[0].get("fatal", True) else "declared, non-fatal"
                ids = [m["candidate_id"] for m in members]
                where = (
                    f"{len(ids)} candidates ({', '.join(ids)})" if len(ids) > 3 else ", ".join(ids)
                )
                lines.append(
                    f"- `{finding_id}` on {where} ({severity}): {members[0]['detail']} "
                    f"(protocol {members[0].get('protocol','-')})"
                )
            lines.append("")

        # handoff block: what the study's final report needs per runtime
        eid_r_check = next(
            (c for c in entry.get("checks") or [] if c["check_id"] == "EID-r-derives-from-EID-star"), None
        )
        lines.append("Handoff:")
        lines.append("")
        lines.append(f"- A0.1 verdict: **{entry['state']}**" + (f" ({entry['reason']})" if entry.get("reason") else ""))
        lines.append(
            "- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the "
            "adapter can carry the identity and the numbers"
        )
        lines.append(f"- EID_r -> EID* : {eid_r_check['detail'] if eid_r_check else 'not declared'}")
        lines.append(f"- traces: {json.dumps(entry.get('traces')) if entry.get('traces') else 'none reported'}"
                     + (f" ({entry.get('traces_source')})" if entry.get("traces_source") else ""))
        counts = entry.get("failure_stage_counts")
        lines.append(f"- FailureStage counts: {json.dumps(counts) if counts else 'none reported'}")
        revision = entry.get("adapter_revision")
        if revision:
            lines.append(
                f"- adapter revision covered by this verdict: digest `{revision.get('digest')}` over "
                f"{revision.get('file_count')} source file(s), newest mtime {revision.get('newest_mtime')}, "
                f"unchanged during the run: {revision.get('unchanged_during_run')}"
                + (f" (changed: {', '.join(revision.get('changed_files') or [])})"
                   if revision.get("changed_files") else "")
            )
        accounting = entry.get("failure_stage_accounting")
        if accounting:
            lines.append(
                f"- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: "
                f"declared {json.dumps(accounting.get('declared_counts'))} "
                f"(comparable={accounting.get('comparable_to_C*')}, "
                f"matches_frozen_map={accounting.get('matches_frozen_map')}); "
                f"expected {json.dumps(accounting.get('expected_from_frozen_map'))}. {accounting.get('note')}"
            )
        if entry.get("synthetic_declared_candidates"):
            lines.append(
                f"- declared synthetic failures (never a measurement): "
                f"{', '.join(entry['synthetic_declared_candidates'])}"
            )
        if entry.get("adapter_unverified_notes"):
            lines.append(f"- adapter's own UNVERIFIED note: {entry['adapter_unverified_notes']}")
        if entry.get("fallback"):
            lines.append(
                f"- **fallback used**: {entry['fallback']['why']}; conformance exit "
                f"`{entry['fallback']['conformance_exit_code']}`; last stderr lines: "
                f"`{entry['fallback']['conformance_stderr_tail']}`. {entry['fallback']['limitation']}"
            )
        if entry.get("adapter_seams"):
            seams = entry["adapter_seams"]
            lines.append(
                "- seams the adapter declares: "
                + "; ".join(
                    f"{s.get('seam')}: {s.get('what')} ({s.get('where')})" if isinstance(s, dict) else str(s)
                    for s in seams
                )
            )
        lines.append("")

    lines.append("## Controls")
    lines.append("")
    controls = report.get("controls") or {}
    if not controls:
        lines.append(
            "No control row in this report. Run `python3 selftest.py` to exercise the checker against "
            "deliberately deviant adapters (see `selftest_report.json`)."
        )
    else:
        lines.append("| control | state | rows | reason |")
        lines.append("|---|---|---|---|")
        for name, entry in controls.items():
            lines.append(f"| {name} | {entry['state']} | {len(entry.get('rows') or [])} | {entry.get('reason') or ''} |")
    lines.append("")
    lines.append("## EID* checks")
    lines.append("")
    frozen = report.get("frozen") or {}
    supplied = frozen.get("eid_document_supplied_to_adapters") or {}
    lines.append(
        f"Handed to every adapter: `{frozen.get('eid_document')}` "
        f"(label `{frozen.get('eid_document_name')}`, requested `{frozen.get('eid_document_requested')}`, "
        f"sha256 `{str(frozen.get('eid_document_sha256'))[:16]}...`)."
    )
    lines.append("")
    if not supplied.get("matches_binding", True):
        lines.append(
            f"WARNING: the supplied document does not carry the binding EID* "
            f"({supplied.get('eid_star')!r}) -- no verdict in this report is trustworthy."
        )
        lines.append("")
    for check in (report.get("eid") or {}).get("checks", []):
        lines.append(f"- `{'PASS' if check['ok'] else 'FAIL'}` {check['check_id']}: {check['detail']}")
    lines.append("")
    lines.append("## Candidate-set integrity")
    lines.append("")
    lines.append(
        f"{report['integrity']['checked']} candidates checked against `manifest.json`; "
        f"integrity ok = **{report['integrity']['ok']}**."
    )
    lines.append("")
    path.write_text("\n".join(lines) + "\n")


def cmd_show(args) -> int:
    path = Path(args.report) if args.report else HERE / "report.json"
    report = load_json(path)
    write_table(report, HERE / "report.md")
    print((HERE / "report.md").read_text())
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="conformance.py", description="A0.1 cross-adapter conformance runner")
    sub = parser.add_subparsers(dest="command", required=True)

    ref = sub.add_parser("reference", help="fresh E* sweep over C*, cross-checked against E_STAR.json")
    ref.add_argument("--out", default=None)
    ref.add_argument("--state-root", default=None)
    ref.add_argument("--fidelity", choices=("full", "fast"), default=None)
    ref.add_argument("--timeout", type=float, default=300.0)
    ref.add_argument("--manifest", default=None, help="override the C* manifest (integrity-abort tests)")
    ref.set_defaults(func=cmd_reference)

    run = sub.add_parser("run", help="drive every adapter and write report.json + report.md")
    run.add_argument("--runtimes", default=None, help=f"comma-separated subset of {RUNTIMES}")
    run.add_argument("--adapter-root", default=None)
    run.add_argument("--adapter", action="append", default=None, metavar="NAME=CMD", help="override an adapter command")
    run.add_argument("--reference", default=None)
    run.add_argument("--refresh-reference", action="store_true")
    run.add_argument("--reference-timeout", type=float, default=300.0)
    run.add_argument("--adapter-timeout", type=float, default=ADAPTER_TIMEOUT_SEC)
    run.add_argument("--out", default=None, help="report path (default a0/conformance/report.json)")
    run.add_argument("--controls", dest="controls", action="store_true", default=True,
                     help="also drive the fixture adapters as control rows (default on)")
    run.add_argument("--no-controls", dest="controls", action="store_false")
    run.add_argument("--manifest", default=None, help="override the C* manifest (integrity-abort tests)")
    run.add_argument(
        "--eid-document", default=EID_DOCUMENT_DEFAULT, metavar="LABEL|PATH",
        help="which EID* document to hand the adapters: 'canonical' (default) = "
             "a0/contract/out/plumbing.EID.json, the contract-owned document; 'proposed' = "
             "a0/tasks/circle-packing/plumbing.EID.proposed.json, the pre-repoint default; or a path",
    )
    run.set_defaults(func=cmd_run)

    show = sub.add_parser("show", help="re-render report.md from report.json")
    show.add_argument("--report", default=None)
    show.set_defaults(func=cmd_show)

    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
