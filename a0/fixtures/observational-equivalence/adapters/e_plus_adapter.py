#!/usr/bin/env python3
"""Fixture adapter for the observational-equivalence experiment.

It is a copy of the *protocol* of the study's own honest fixture
(`a0/conformance/fixtures/adapters/reference_adapter.py`): hash every member of
C* before evaluating anything, invoke the frozen evaluator CLI once per
candidate with the frozen theta_E, carry `eid_star` verbatim with a recomputable
`eid_r`, and mark every row's `evaluator_evidence.status` as `ok` only for a real
subprocess run.

**It is not a runtime adapter and must never be reported as one.** What it varies
is only what the A0.1 checker does *not* measure for itself:

  --evaluator-dir    which evaluator directory is executed (E*, or the mutant E')
  --identity         what identity material each row declares:
                       own        the executed evaluator's own outcome digest (honest)
                       claim-e-star  the frozen E* material from E_STAR.json, while the
                                  numbers come from --evaluator-dir (the "echo is not
                                  proof" case: what a runtime that has vendored or
                                  modified its evaluator would report)
                       omit       no `canonical_digest` and no `source_sha256` at all
  --twin-swap        evaluate c03's directory for c01's row (c01 and c03 are
                     bit-identical in value, so only a file-identity field can see it)
  --echo-manifest    carry the evaluator's own `E_STAR_MANIFEST {...}` stdout in the row

Modes `own` + the real E* is the control: it must PASS, or the experiment's
"the checker accepts E'" rows mean nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent
A0 = FIXTURE.parents[1]
TASK = A0 / "tasks" / "circle-packing"
E_STAR_SCRIPT = TASK / "e_star.py"
E_STAR_PYTHON = TASK / ".venv" / "bin" / "python"
E_STAR_TABLE = TASK / "E_STAR.json"
FR_DECLARATION = A0 / "contract" / "fr" / "scalar.json"
C_STAR_DEFAULT = TASK / "C_STAR" / "manifest.json"

THETA_KEYS = ("seed", "fidelity", "fraction", "n", "runs", "runtime_budget_ms", "timeout_s")
DEFAULT_THETA = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
                 "runtime_budget_ms": 250.0, "timeout_s": 120.0}
TWIN = {"c01_good_hex": "c03_mirror"}


BOOLEAN_FLAGS = {"twin-swap", "echo-manifest"}


def read_args(argv):
    """Flag/value reader. The runner appends `<subcommand> --flag value ...` to the base argv,
    so a bare boolean flag must not swallow the subcommand that follows it."""
    positional, flags = [], {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("--"):
            name = token[2:]
            if "=" in name:
                name, value = name.split("=", 1)
            elif name in BOOLEAN_FLAGS or i + 1 >= len(argv) or argv[i + 1].startswith("--") \
                    or argv[i + 1] in ("conformance", "run"):
                value = "true"
            else:
                value = argv[i + 1]
                i += 1
            flags[name] = value
        else:
            positional.append(token)
        i += 1
    return positional, flags


def parse_theta(text):
    theta = {}
    for part in (text or "").split(","):
        if not part.strip():
            continue
        key, _, value = part.partition("=")
        key, value = key.strip(), value.strip()
        for cast in (int, float):
            try:
                value = cast(value)
                break
            except ValueError:
                continue
        theta[key] = value
    return theta


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_file_digest(path: Path) -> str:
    return hashlib.sha256(canonical_json(json.loads(Path(path).read_text()))).hexdigest()


def eid_r_declaration(eid_star: str, runtime: str) -> dict:
    domain = f"a0/fixture/e_plus/v1/EID_r"
    payload = {"eid_star": eid_star, "runtime": runtime}
    value = hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json(payload)).hexdigest()
    return {
        "value": value,
        "native_scheme": "none",
        "mapping_mode": "adapter_declared_injection",
        "derives_from_eid_star": eid_star,
        "declarations_verbatim_from": eid_star,
        "declaration": (
            "e_plus fixture has no native evaluator identity; EID_r is a domain-separated digest over "
            "(eid_star, runtime) so that it is a function of EID* alone."
        ),
        "recomputable": True,
        "derivation": {"algorithm": "sha256", "domain": domain,
                       "payload_canonical": canonical_json(payload).decode("ascii")},
    }


def scratch_root(runtime: str) -> Path:
    override = os.environ.get("A0_FIXTURE_RUN_ROOT")
    root = Path(override) if override else FIXTURE / "out" / "adapter-runs"
    root = root / f"{runtime}-{time.strftime('%Y%m%dT%H%M%S')}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def conformance(flags: dict) -> int:
    runtime = flags.get("runtime", "unknown")
    out_path = Path(flags["out"])
    evaluator_dir = Path(flags.get("evaluator-dir") or (FIXTURE / "e_prime")).resolve()
    evaluator_script = evaluator_dir / "e_star.py"
    identity = flags.get("identity", "own")
    interpreter = flags.get("python") or str(E_STAR_PYTHON)
    twin_swap = flags.get("twin-swap", "false") not in ("false", "0")
    echo_manifest = flags.get("echo-manifest", "false") not in ("false", "0")

    theta = dict(DEFAULT_THETA)
    theta.update({k: v for k, v in parse_theta(flags.get("theta", "")).items() if k in THETA_KEYS})
    manifest_path = Path(flags.get("candidate-set") or C_STAR_DEFAULT)
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parent
    eid_doc = json.loads(Path(flags["eid"]).read_text()) if flags.get("eid") else {}
    eid_star = eid_doc.get("eid_star", "")
    frozen = {c["candidate_id"]: c for c in json.loads(E_STAR_TABLE.read_text())["candidates"]}

    run_dir = scratch_root(runtime)
    out_dir = run_dir / "outcomes"
    state_dir = run_dir / "state"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for cand in manifest["candidates"]:
        cid = cand["candidate_id"]
        evaluated_id = TWIN.get(cid, cid) if twin_swap else cid
        cdir = root / evaluated_id
        if not cdir.is_dir():
            cdir = root / (cand.get("path") or cand.get("dir") or cid)
        source = cdir / "solution.py"
        declared_source = cand["solution_sha256"]
        observed = sha256_file(source) if source.exists() else None
        if observed is None:
            return 4  # integrity failure (adapter_contract.md 3.1)
        outcome_path = out_dir / f"{cid}.json"
        if outcome_path.exists():
            outcome_path.unlink()
        argv = [
            interpreter, str(evaluator_script), "evaluate",
            "--candidate", str(cdir),
            "--seed", str(theta["seed"]),
            "--fidelity", str(theta["fidelity"]),
            "--fraction", str(theta["fraction"]),
            "--n", str(theta["n"]),
            "--runs", str(theta["runs"]),
            "--runtime-budget-ms", str(theta["runtime_budget_ms"]),
            "--timeout-s", str(theta["timeout_s"]),
            "--out", str(outcome_path),
            "--state-dir", str(state_dir),
        ]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=float(theta["timeout_s"]) + 60.0, cwd=str(root))
        outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else {}
        objective = outcome.get("objective") or {}
        manifest_line = next(
            (line for line in proc.stdout.splitlines() if line.startswith("E_STAR_MANIFEST ")), None
        )
        row = {
            "candidate_id": cid,
            "status": outcome.get("status"),
            "exit_code": proc.returncode,
            "objective": {"name": objective.get("name"), "value": objective.get("value"),
                          "direction": objective.get("direction")},
            "objective_value": objective.get("value"),
            "failure_kind": (outcome.get("failure") or {}).get("kind"),
            "fields": outcome.get("fields"),
            "evaluator_evidence": {
                "status": "ok",
                "detail": f"fresh subprocess run of {evaluator_script}, exit {proc.returncode}",
            },
            "theta_e_attempt": {
                "evaluator": str(evaluator_script),
                "fidelity": theta["fidelity"], "fraction": theta["fraction"], "seed": theta["seed"],
                "granted_class": theta["fidelity"], "commanded_class": theta["fidelity"],
                "command": " ".join(argv),
            },
        }
        if identity == "own":
            row["source_sha256"] = declared_source
            row["canonical_digest"] = outcome.get("canonical_digest")
            row["evaluator_outcome_sha256"] = outcome.get("evaluator_source_sha256")
        elif identity == "claim-e-star":
            row["source_sha256"] = declared_source
            row["canonical_digest"] = (frozen.get(cid) or {}).get("canonical_digest")
            row["evaluator_source_sha256"] = (
                json.loads(E_STAR_TABLE.read_text()).get("evaluator") or {}
            ).get("evaluator_source_sha256")
        elif identity == "omit":
            pass
        else:
            print(f"e_plus_adapter: unknown --identity {identity!r}", file=sys.stderr)
            return 2
        if echo_manifest and manifest_line:
            row["raw_manifest_line"] = manifest_line
        rows.append(row)

    doc = {
        "schema": "a0.adapter.conformance/v1",
        "runtime": runtime,
        "adapter": "a0/fixtures/observational-equivalence/adapters/e_plus_adapter.py (FIXTURE, not a runtime)",
        "fixture": {
            "evaluator_dir": str(evaluator_dir),
            "evaluator_script_sha256": sha256_file(evaluator_script) if evaluator_script.exists() else None,
            "identity_mode": identity,
            "twin_swap": twin_swap,
            "echo_manifest": echo_manifest,
        },
        "eid_star": eid_star,
        "eid_r": eid_r_declaration(eid_star, runtime),
        "theta_e": theta,
        "epsilon": float(flags.get("epsilon", 1e-9)),
        "primary_field": "sum_radii",
        "fr": {"name": "F_r = scalar(E*)", "version": "v1", "applies": "scalar",
               "spec_hash": canonical_file_digest(FR_DECLARATION),
               "declared_in": "a0/contract/fr/scalar.json"},
        "candidate_set": str(manifest_path),
        "run_dir": str(run_dir),
        "candidates": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return 0


def main(argv) -> int:
    positional, flags = read_args(argv)
    if positional and positional[0] in ("conformance", "run"):
        return conformance(flags)
    print(f"e_plus_adapter: unsupported subcommand {positional!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
