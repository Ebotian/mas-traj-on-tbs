#!/usr/bin/env python3
"""One command that re-establishes every claim this directory makes, model-free.

    python3 a0/a1/calibration/verify.py                 # everything that costs nothing
    python3 a0/a1/calibration/verify.py --list          # what it runs
    python3 a0/a1/calibration/verify.py --with-rehearsal  # also the free topology rehearsal

What it re-establishes:

1. the freeze ordering — `PILOT-PROCEDURE.md` hashes to the value its JSON declares;
2. the model-free invariants (`tests/`, the mapping's monotonicity/boundedness, the
   reduction, the validity predicates);
3. **`B_hard` is re-derivable**: `apply` is re-run over the committed evidence and its
   output must equal the committed `B_hard.json` byte for byte;
4. the ledgers: each published `a0/meter` ledger re-derives under the meter's own
   `verify_ledger.py` (a program the pilot did not write), no pilot row is `unmetered`,
   and `ledger.jsonl` equals the two published ledgers concatenated in time order;
5. the published reduction: no objective value on a calibration graph appears anywhere in
   the published evidence;
6. `B_hard` is loadable by the skeleton's own `a0/a1/budget.py::Budget`.

The paid campaigns are **not** re-run (they spend money); their recorded output is
committed under `evidence/`.  Exit code 0 means every step passed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("calibration_pilot_verify", HERE / "pilot.py")
pilot = importlib.util.module_from_spec(spec)
sys.modules["calibration_pilot_verify"] = pilot
spec.loader.exec_module(pilot)

EVIDENCE = HERE / "evidence"
FORBIDDEN_KEYS = ("cut_edges", "cut_fraction", "true_value", "handed_value")


def run(argv: List[str]) -> Tuple[int, str]:
    proc = subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def step_freeze() -> str:
    procedure = pilot.load_procedure()
    units = pilot.calibration_units()
    return (f"procedure {pilot.sha256_file(pilot.PROC_MD)[:16]}… · "
            f"{len(units)} calibration graphs verified against the manifest · "
            f"caps {procedure['caps']['A_simpleloop']['CEq_max']}/"
            f"{procedure['caps']['A_kapso']['CEq_max']} CEq")


def step_tests() -> str:
    code, out = run([sys.executable, "-m", "pytest", "a0/a1/calibration/tests", "-q"])
    if code != 0:
        raise AssertionError(out.strip()[-1200:])
    return out.strip().splitlines()[-1]


def step_b_hard_rederived() -> str:
    committed = HERE / "B_hard.json"
    if not committed.is_file():
        raise AssertionError("no committed B_hard.json")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "B_hard.json"
        code, out = run([sys.executable, "a0/a1/calibration/pilot.py", "apply",
                         "--out-dir", str(EVIDENCE), "--b-hard", str(target)])
        if code != 0:
            raise AssertionError(f"apply exited {code}: {out.strip()[-800:]}")
        derived = target.read_bytes()
    frozen = committed.read_bytes()
    if derived != frozen:
        raise AssertionError(
            "the committed B_hard.json is not reproducible from the committed evidence "
            "(re-run `pilot.py publish` + `apply`, or record why the runner changed)")
    document = json.loads(frozen)
    return (f"byte-identical · vector CEq_max={document['vector']['CEq_max']} "
            f"N_E,max={document['vector']['N_evaluatorCalls']} "
            f"T_wall={document['vector']['T_wall_sec']:.0f}s")


def step_ledgers() -> str:
    totals = []
    concatenated: List[dict] = []
    for arm, short in pilot.SHORT.items():
        path = EVIDENCE / short / "meter_ledger.jsonl"
        if not path.is_file():
            raise AssertionError(f"no published meter ledger for {arm} at {path}")
        code, out = run([sys.executable, "a0/meter/verify_ledger.py", str(path), "--json"])
        if code != 0:
            raise AssertionError(f"{path}: the meter's own verifier failed:\n{out[-800:]}")
        summary = json.loads(out)
        if summary["unmetered"]:
            raise AssertionError(f"{path}: {summary['unmetered']} unmetered row(s)")
        rows = pilot.read_rows(path)
        campaign = rows[0]["campaign_id"] if rows else "?"
        concatenated.extend(rows)
        totals.append(f"{campaign}: {summary['rows']} rows, ceq {summary['ceq_total']}")
    concatenated.sort(key=lambda row: row["ts"])
    combined = HERE / "ledger.jsonl"
    if not combined.is_file():
        raise AssertionError("no ledger.jsonl at the directory root")
    expected = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                       for row in concatenated)
    if combined.read_text(encoding="utf-8") != expected:
        raise AssertionError("ledger.jsonl is not the two published ledgers concatenated "
                             "in time order")
    return " · ".join(totals) + f" · root ledger.jsonl == concat ({len(concatenated)} rows)"


def step_reduction() -> str:
    files = 0
    for path in sorted(EVIDENCE.rglob("*")):
        if not path.is_file():
            continue
        files += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for key in FORBIDDEN_KEYS:
            if f'"{key}"' in text:
                raise AssertionError(f"{path.relative_to(HERE)} publishes {key!r}")
    return f"{files} published files, none carries an objective value on a calibration graph"


def step_budget_loads() -> str:
    from a0.a1.budget import Budget

    document = json.loads((HERE / "B_hard.json").read_text(encoding="utf-8"))
    vector = document["vector"]
    budget = Budget(T_wall_sec=vector["T_wall_sec"], N_eval_max=vector["N_evaluatorCalls"],
                    CEq_max=vector["CEq_max"], P_concurrency=vector["P_concurrency"])
    as_dict = budget.as_dict()
    if as_dict["T_wall_sec"] != 1800.0 or as_dict["CEq_max"] != vector["CEq_max"]:
        raise AssertionError(f"the skeleton's Budget does not reproduce the vector: {as_dict}")
    return (f"a0/a1/budget.Budget(T_wall_sec={as_dict['T_wall_sec']}, "
            f"N_eval_max={as_dict['N_evaluatorCalls']}, CEq_max={as_dict['CEq_max']}, "
            f"P={as_dict['P_concurrency']})")


def step_properties() -> str:
    document = json.loads((HERE / "B_hard.json").read_text(encoding="utf-8"))
    procedure = pilot.load_procedure()
    telemetry = pilot.load_published_telemetry(EVIDENCE)
    per_arm = {arm: {key: value for key, value in entry.items()
                     if key not in ("report", "CEq_r_ledger", "N_E_r_ledger",
                                    "unmetered_rows_ledger", "CEq_r_telemetry",
                                    "N_E_r_telemetry", "ledger_agrees_with_telemetry",
                                    "models_reported", "harness_graph_shas")}
               for arm, entry in telemetry.items()}
    result = pilot.apply_f(per_arm, procedure)
    properties = pilot.check_f_properties(per_arm, procedure, result)
    failures = pilot.validity_failures(procedure, telemetry)
    if failures:
        raise AssertionError(f"validity failures: {failures}")
    for name, value in (("monotone", properties["monotone"]),
                        ("bounded", properties["bounded"]),
                        ("variance_reported", properties["variance_reported"]),
                        ("total", properties["total"])):
        if value is not True:
            raise AssertionError(f"f's required property {name} is {value!r}")
    if result["vector"] != {key: document["vector"][key] for key in result["vector"]}:
        raise AssertionError("re-applying f gives a different vector")
    diag = document["diagnostics"]["per_arm"]
    notes = []
    for arm in sorted(diag):
        d1 = diag[arm]["D1_margin_CEq_minutes"]
        d2 = diag[arm]["D2_margin_NE_minutes"]
        early = diag[arm]["guardrails_would_bind_before_T_wall"]
        notes.append(f"{arm}: margins {d1:.1f}/{d2:.1f} min"
                     + (f", would bind early on {early}" if early else ""))
    return ("monotone+bounded+variance reported+total · V1–V7 hold · " + " · ".join(notes))


def step_rehearsal() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        code, out = run([sys.executable, "a0/a1/calibration/pilot.py", "rehearsal",
                         "--out-dir", tmp])
        if code != 0:
            raise AssertionError(out.strip()[-1200:])
    return "the same runner and closed topology, model call skipped, both arms green"


STEPS = [
    ("freeze", "the procedure document hashes to the frozen value and the calibration "
               "graphs match the manifest", step_freeze, True),
    ("tests", "the model-free invariants of the mapping, the estimator and the reduction",
     step_tests, True),
    ("b-hard-re-derived", "f re-applied to the committed evidence equals the committed "
                          "B_hard.json", step_b_hard_rederived, True),
    ("ledgers", "the meter's own verifier re-derives every published row; no unmetered row",
     step_ledgers, True),
    ("reduction", "no published file carries an objective value on a calibration graph",
     step_reduction, True),
    ("budget-loads", "B_hard is loadable by the skeleton's own Budget", step_budget_loads,
     True),
    ("f-properties", "monotonicity, boundedness, reported variance and validity V1–V7",
     step_properties, True),
    ("rehearsal", "the free closed-topology rehearsal (opt in with --with-rehearsal)",
     step_rehearsal, False),
]


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.calibration.verify")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--with-rehearsal", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        for name, description, _, required in STEPS:
            suffix = "" if required else " [optional]"
            print(f"{name:20s} {description}{suffix}")
        return 0

    failures = 0
    for name, description, function, required in STEPS:
        if not required and not args.with_rehearsal:
            print(f"SKIP {name:20s} {description}")
            continue
        try:
            detail = function()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {name:20s} {description}\n     {exc}")
        else:
            print(f"PASS {name:20s} {detail}")
    print("verdict:", "pass" if not failures else f"fail ({failures} step(s))")
    return 0 if not failures else 5


if __name__ == "__main__":
    sys.exit(main())
