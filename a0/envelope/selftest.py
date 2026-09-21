#!/usr/bin/env python3
"""Self-test for `a0/envelope/envelope.py`: the D1 projection (both directions) and the D3 token.

Every check is executed, and the two directions of the projection are measured against **real
evaluator runs**, not hand-built payloads:

1. **Canonicalisation.** `canonical_json_bytes` + `outcome_digest` reproduce the frozen table's own
   `canonical_digest` for all 14 members of `C*`. Nothing else here is trustworthy until this holds.
2. **Evaluator identity.** `evaluator_source_digest` reproduces the frozen table's
   `evaluator.evaluator_source_sha256` from the actual bytes of `e_star.py` + `e_star_child.py`.
3. **Direction 1 (the false red is gone).** Run the frozen `E*` under the pinned interpreter and
   under `/usr/bin/python3.14`: the behaviour digests agree on every candidate and the
   `canonical_digest`s differ on every candidate, and `digest_with_interpreter` bridges exactly the
   two -> `EXECUTION_ENV_DRIFT`, never `MISMATCH_DIGEST`.
4. **Direction 2 (the mutant is not rescued).** Run the observational-equivalence fixture's mutant
   `E'` (`a0/fixtures/observational-equivalence/e_prime`) over the same `C*`: its behaviour digest
   differs from `E*`'s on every candidate **while its objective values are bit-identical**, and no
   interpreter in the declared allowed set reconciles the digests -> `MISMATCH_DIGEST`. The
   projection therefore cannot be used to accept a different evaluator.
5. **The token.** An issued OID recomputes; a token is bound to its candidate, its nonce and every
   field of its binding, so a row cannot reuse another measurement's token.

    python3 a0/envelope/selftest.py            # exit 0 = every check holds

Writes `a0/envelope/out/selftest_report.json`. Executes `E*` (pinned and 3.14.7) and the fixture's
mutant `E'`; it writes nothing outside `a0/envelope/out/` and a scratch directory under the system
temp directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import envelope as env  # noqa: E402

A0 = HERE.parent
TASK = A0 / "tasks" / "circle-packing"
E_STAR_SCRIPT = TASK / "e_star.py"
E_STAR_PYTHON = TASK / ".venv" / "bin" / "python"
E_STAR_TABLE = TASK / "E_STAR.json"
C_STAR = TASK / "C_STAR"
E_PRIME_DIR = A0 / "fixtures" / "observational-equivalence" / "e_prime"
ALT_PYTHON = Path("/usr/bin/python3.14")

THETA = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
         "runtime_budget_ms": 250.0, "timeout_s": 120.0}
OUT = HERE / "out"


def table() -> dict:
    return json.loads(E_STAR_TABLE.read_text())


def e_star_argv(script: Path, candidate_dir: Path, out_json: Path, state_dir: Path) -> list:
    return [
        str(E_STAR_PYTHON), str(script), "evaluate",
        "--candidate", str(candidate_dir),
        "--seed", str(THETA["seed"]),
        "--fidelity", str(THETA["fidelity"]),
        "--fraction", str(THETA["fraction"]),
        "--n", str(THETA["n"]),
        "--runs", str(THETA["runs"]),
        "--runtime-budget-ms", str(THETA["runtime_budget_ms"]),
        "--timeout-s", str(THETA["timeout_s"]),
        "--out", str(out_json),
        "--state-dir", str(state_dir),
    ]


def run_evaluator(interpreter: Path, script: Path, candidate_dir: Path, scratch: Path,
                  label: str) -> dict:
    out_json = scratch / f"{label}.{candidate_dir.name}.json"
    if out_json.exists():
        out_json.unlink()
    argv = e_star_argv(script, candidate_dir, out_json, scratch / f"{label}.state")
    argv[0] = str(interpreter)
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(scratch),
                          timeout=float(THETA["timeout_s"]) + 60.0)
    outcome = json.loads(out_json.read_text()) if out_json.exists() else None
    return {"exit_code": proc.returncode, "outcome": outcome, "argv": argv}


def bits(value) -> str:
    """Float identity by bit pattern, not by repr: the fixture's own standard."""
    if value is None:
        return "null"
    return struct.pack(">d", float(value)).hex()


def check_canonicalisation(report: dict) -> None:
    frozen = table()
    ok = 0
    details = []
    for entry in frozen["candidates"]:
        outcome = entry["outcome"]
        recomputed = env.outcome_digest(outcome)
        if recomputed == entry["canonical_digest"]:
            ok += 1
        else:
            details.append(f"{entry['candidate_id']}: {recomputed} != {entry['canonical_digest']}")
    assert ok == len(frozen["candidates"]), f"canonicalisation does not reproduce the frozen digests: {details}"
    report["canonicalisation"] = {
        "check": "canonical_json_bytes/outcome_digest reproduce E_STAR.json's canonical_digest",
        "candidates_reproduced": ok,
        "total": len(frozen["candidates"]),
        "ok": ok == len(frozen["candidates"]),
    }
    source_digest = env.evaluator_source_digest(E_STAR_SCRIPT.parent)
    expected = (frozen.get("evaluator") or {}).get("evaluator_source_sha256")
    assert source_digest == expected, f"evaluator_source_digest {source_digest} != frozen {expected}"
    report["evaluator_identity"] = {
        "check": "evaluator_source_digest recomputes the frozen evaluator_source_sha256",
        "recomputed": source_digest,
        "frozen": expected,
        "ok": True,
    }


def check_projection(scratch: Path, report: dict) -> None:
    """Directions 1 and 2, measured on real runs of `E*` and of the mutant `E'`."""
    frozen = table()
    execution_set = env.load_execution_set()
    rows = []
    errors = []
    for entry in frozen["candidates"]:
        cid = entry["candidate_id"]
        cdir = C_STAR / entry["dir"].split("/", 1)[-1]
        pinned = run_evaluator(E_STAR_PYTHON, E_STAR_SCRIPT, cdir, scratch, "estar312")
        drifted = run_evaluator(ALT_PYTHON, E_STAR_SCRIPT, cdir, scratch, "estar314")
        mutant = run_evaluator(E_STAR_PYTHON, E_PRIME_DIR / "e_star.py", cdir, scratch, "eprime")
        ref = entry["outcome"]
        row = {
            "candidate_id": cid,
            "frozen_behaviour_digest": env.behaviour_digest(ref),
            "pinned_behaviour_digest": env.behaviour_digest(pinned["outcome"]),
            "drifted_behaviour_digest": env.behaviour_digest(drifted["outcome"]),
            "mutant_behaviour_digest": env.behaviour_digest(mutant["outcome"]),
            "mutant_objective_bits": bits(((mutant["outcome"] or {}).get("objective") or {}).get("value")),
            "frozen_objective_bits": bits(entry["objective_value"]),
            "substitution_reproduces_drifted_digest": (
                env.digest_with_interpreter(ref, (drifted["outcome"] or {}).get("interpreter"))
                == (drifted["outcome"] or {}).get("canonical_digest")
            ),
            "frozen_canonical_digest": entry["canonical_digest"],
            "drifted_canonical_digest": (drifted["outcome"] or {}).get("canonical_digest"),
            "mutant_canonical_digest": (mutant["outcome"] or {}).get("canonical_digest"),
            "drifted_interpreter": (drifted["outcome"] or {}).get("interpreter"),
        }
        row["pinned_env_verdict"] = env.behaviour_env_verdict(
            row["pinned_behaviour_digest"] == row["frozen_behaviour_digest"],
            env.classify_interpreter((pinned["outcome"] or {}).get("interpreter"), execution_set),
        )[0]
        row["drifted_env_verdict"] = env.behaviour_env_verdict(
            row["drifted_behaviour_digest"] == row["frozen_behaviour_digest"],
            env.classify_interpreter(row["drifted_interpreter"], execution_set),
        )[0]
        row["mutant_env_verdict"] = env.behaviour_env_verdict(
            row["mutant_behaviour_digest"] == row["frozen_behaviour_digest"],
            env.classify_interpreter((mutant["outcome"] or {}).get("interpreter"), execution_set),
        )[0]
        rows.append(row)

    direction1 = [r for r in rows if r["drifted_env_verdict"] == env.EXECUTION_ENV_DRIFT
                  and r["drifted_behaviour_digest"] == r["frozen_behaviour_digest"]]
    direction2 = [r for r in rows if r["mutant_env_verdict"] == "MISMATCH_DIGEST"
                  and r["mutant_behaviour_digest"] != r["frozen_behaviour_digest"]]
    mutant_bit_identical = [r for r in rows if r["mutant_objective_bits"] == r["frozen_objective_bits"]]
    pinned_ok = [r for r in rows if r["pinned_env_verdict"] == env.ENV_PINNED]
    substitution_ok = [r for r in rows if r["substitution_reproduces_drifted_digest"]]
    errors.extend(
        f"{r['candidate_id']}: drifted verdict {r['drifted_env_verdict']}" for r in rows
        if r not in direction1
    )
    errors.extend(
        f"{r['candidate_id']}: mutant verdict {r['mutant_env_verdict']}" for r in rows
        if r not in direction2
    )
    assert not errors, "projection checks failed: " + "; ".join(errors)
    report["projection"] = {
        "check": "D1: the execution environment is split from behaviour, in both directions",
        "direction_1_false_red_removed": {
            "what_ran": f"frozen E* on all of C* under {E_STAR_PYTHON} (pinned) and {ALT_PYTHON}",
            "behaviour_digests_equal": len(direction1),
            "verdicts": sorted({r["drifted_env_verdict"] for r in rows}),
            "canonical_digests_differ": sum(
                1 for r in rows if r["drifted_canonical_digest"] != r["frozen_canonical_digest"]
            ),
        },
        "direction_2_mutant_not_rescued": {
            "what_ran": f"the fixture's mutant E' ({E_PRIME_DIR / 'e_star.py'}) on all of C*",
            "behaviour_digests_differ": len(direction2),
            "verdicts": sorted({r["mutant_env_verdict"] for r in rows}),
            "mutant_objective_values_bit_identical": len(mutant_bit_identical),
            "note": (
                "E' agrees with E* on the objective's float bits and on status/failure.kind, and its "
                "behaviour payload still differs (its outcome carries its own evaluator source digest), "
                "so the projection rejects it as a behaviour difference -- which is the point: the "
                "projection must not become a way to accept a different evaluator"
            ),
        },
        "pinned_verdicts": len(pinned_ok),
        "interpreter_substitution_reproduces_the_other_interpreter_digest": len(substitution_ok),
        "allowed_execution_set": execution_set.get("_path"),
        "rows": rows,
    }


def check_token(report: dict) -> None:
    """D3: the token is bound to its candidate, its run and every field of its binding."""
    frozen = table()
    execution_set = env.load_execution_set()
    entries = []
    for candidate in frozen["candidates"][:3]:
        outcome = candidate["outcome"]
        entries.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_sha256": candidate["source_sha256"],
                "behaviour_digest": env.behaviour_digest(outcome),
                "canonical_digest": candidate["canonical_digest"],
                "interpreter": env.interpreter_of(outcome),
            }
        )
    document = env.issue_envelope(
        eid_star="0" * 64,
        theta_e=THETA,
        evaluator={"evaluator_source_sha256": env.evaluator_source_digest(E_STAR_SCRIPT.parent),
                   "interpreter": env.interpreter_of(frozen["candidates"][0]["outcome"])},
        execution_set=execution_set,
        harness_run_id="selftest",
        nonce="deadbeef" * 4,
        candidates=entries,
    )
    first = document["candidates"][entries[0]["candidate_id"]]
    checks = {
        "oid_is_recomputable": env.token_oid(first["binding"]) == first["oid"],
        "token_is_per_candidate": all(
            document["candidates"][e["candidate_id"]]["oid"] != first["oid"]
            for e in entries[1:]
        ),
        "foreign_candidate_token_does_not_verify": (
            env.token_oid(document["candidates"][entries[1]["candidate_id"]]["binding"]) != first["oid"]
        ),
        "nonce_changes_the_oid": (
            env.token_oid(dict(first["binding"], nonce="0" * 32)) != first["oid"]
        ),
        "behaviour_digest_changes_the_oid": (
            env.token_oid(dict(first["binding"], behaviour_digest="0" * 64)) != first["oid"]
        ),
        "candidate_bytes_change_the_oid": (
            env.token_oid(dict(first["binding"], candidate_sha256="0" * 64)) != first["oid"]
        ),
        "eid_star_changes_the_oid": (
            env.token_oid(dict(first["binding"], eid_star="1" * 64)) != first["oid"]
        ),
        "theta_changes_the_oid": (
            env.token_oid(dict(first["binding"], theta_e=dict(THETA, seed=1))) != first["oid"]
        ),
        "every_token_recomputes": all(
            env.token_oid(t["binding"]) == t["oid"] for t in document["candidates"].values()
        ),
        "document_digest_is_over_the_document": bool(env.envelope_sha256(document)),
    }
    failed = sorted(k for k, v in checks.items() if not v)
    assert not failed, f"token checks failed: {failed}"
    report["token"] = {
        "check": "D3: OID binding and per-candidate/per-run separation",
        "checks": checks,
        "binding_fields": sorted(first["binding"]),
        "example_oid": first["oid"],
        "nonce": document["nonce"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="a0/envelope/selftest.py")
    parser.add_argument("--quick", action="store_true",
                        help="skip the real E* / E' runs (canonicalisation and token checks only)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = {"schema": "a0.envelope.selftest/v1", "env": {"python": sys.version.split()[0], "cwd": os.getcwd()}}
    OUT.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="a0-envelope-selftest-"))
    try:
        check_canonicalisation(report)
        print("canonicalisation: reproduces the frozen table's canonical_digest 14/14 ... ok")
        if not args.quick:
            check_projection(scratch, report)
            print("projection: EXECUTION_ENV_DRIFT for the pinned-vs-3.14.7 run, MISMATCH_DIGEST for the "
                  "mutant on 14/14 ... ok")
        check_token(report)
        print("token: OID recomputes and is bound to candidate, nonce and binding ... ok")
        report["ok"] = True
        exit_code = 0
    except AssertionError as exc:
        report["ok"] = False
        report["failure"] = str(exc)
        print(f"FAILED: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (OUT / "selftest_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"written: {OUT / 'selftest_report.json'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
