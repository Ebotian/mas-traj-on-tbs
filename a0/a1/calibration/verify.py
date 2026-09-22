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
class SkipStep(Exception):
    """A claim this directory does not make yet (no budget was frozen), named as such."""
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


def step_budget() -> str:
    """`B_hard` re-derivation, or — when the pilot could not measure — the refusal.

    Both are claims about the committed evidence, and both must be reproducible byte for
    byte: either the frozen vector follows from the published telemetry, or the pilot
    refused to freeze one for named reasons.
    """
    frozen = HERE / "B_hard.json"
    refused = HERE / "B_hard_REFUSED.json"
    if not frozen.is_file() and not refused.is_file():
        raise AssertionError("neither B_hard.json nor B_hard_REFUSED.json is committed")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.json"
        code, out = run([sys.executable, "a0/a1/calibration/pilot.py", "apply",
                         "--out-dir", str(EVIDENCE), "--b-hard", str(target)])
        produced = json.loads(target.read_text(encoding="utf-8"))
        derived = target.read_bytes()
    if frozen.is_file():
        if produced["refused"]:
            raise AssertionError("the committed B_hard.json exists but apply now refuses: "
                                 f"{produced['validity']['failures']}")
        if derived != frozen.read_bytes():
            raise AssertionError(
                "the committed B_hard.json is not reproducible from the committed evidence "
                "(re-run `pilot.py publish` + `apply`, or record why the runner changed)")
        document = produced
        return (f"byte-identical from the evidence · vector CEq_max={document['vector']['CEq_max']} "
                f"N_E,max={document['vector']['N_evaluatorCalls']} "
                f"T_wall={document['vector']['T_wall_sec']:.0f}s")
    if not produced["refused"]:
        raise AssertionError("no B_hard.json is committed, but apply froze a vector: "
                             f"{produced['vector']}")
    if derived != refused.read_bytes():
        raise AssertionError("the committed B_hard_REFUSED.json is not reproducible from "
                             "the committed evidence")
    failures = produced["validity"]["failures"]
    if not failures:
        raise AssertionError("a refusal with no named validity failure")
    return ("NO budget frozen, reproducibly refused: " + " · ".join(failures))


def step_budget_loads() -> str:
    from a0.a1.budget import Budget

    frozen = HERE / "B_hard.json"
    if not frozen.is_file():
        raise SkipStep(
            "no vector is frozen (B_hard_REFUSED.json: the pilot measured no rate), so "
            "there is nothing for a0/a1/budget.Budget to load — re-established when the "
            "pilot can run")
    document = json.loads(frozen.read_text(encoding="utf-8"))
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
    procedure = pilot.load_procedure()
    telemetry = pilot.load_published_telemetry(EVIDENCE)
    failures = pilot.validity_failures(procedure, telemetry)
    refused = json.loads((HERE / "B_hard_REFUSED.json").read_text(encoding="utf-8")) \
        if (HERE / "B_hard_REFUSED.json").is_file() else None
    if refused is not None:
        if not failures:
            raise AssertionError("B_hard_REFUSED.json is committed but V1–V7 now hold")
        if sorted(failures) != sorted(refused["validity"]["failures"]):
            raise AssertionError("the refusal's validity failures changed")
        if (HERE / "B_hard.json").is_file():
            raise AssertionError("both a refusal and a frozen budget are committed")
        return ("V1–V7 fail exactly as recorded, so no budget was frozen: "
                + " · ".join(failures)
                + " — the vector-dependent properties (monotonicity, boundedness, "
                  "reported variance of a *measured* rate) are not established")
    if failures:
        raise AssertionError(f"validity failures: {failures}")
    per_arm = {arm: {key: value for key, value in entry.items()
                     if key not in ("report", "CEq_r_ledger", "N_E_r_ledger",
                                    "unmetered_rows_ledger", "CEq_r_telemetry",
                                    "N_E_r_telemetry", "ledger_agrees_with_telemetry",
                                    "models_reported", "harness_graph_shas")}
               for arm, entry in telemetry.items()}
    result = pilot.apply_f(per_arm, procedure)
    properties = pilot.check_f_properties(per_arm, procedure, result)
    for name in ("monotone", "bounded", "variance_reported", "total"):
        if properties[name] is not True:
            raise AssertionError(f"f's required property {name} is {properties[name]!r}")
    document = json.loads((HERE / "B_hard.json").read_text(encoding="utf-8"))
    if result["vector"] != {key: document["vector"][key] for key in result["vector"]}:
        raise AssertionError("re-applying f gives a different vector")
    notes = []
    for arm, entry in sorted(document["diagnostics"]["per_arm"].items()):
        notes.append(f"{arm}: margins {entry['D1_margin_CEq_minutes']:.1f}/"
                     f"{entry['D2_margin_NE_minutes']:.1f} min"
                     + (f", would bind early on {entry['guardrails_would_bind_before_T_wall']}"
                        if entry["guardrails_would_bind_before_T_wall"] else ""))
    return ("V1–V7 hold · monotone+bounded+variance reported+total · " + " · ".join(notes))


def step_meter_evidence() -> str:
    """The two probe campaigns: one real `ceq` row, and one `unmetered` counter-example."""
    notes = []
    proof = EVIDENCE / "meter-proof" / "meter_proof.json"
    if proof.is_file():
        document = json.loads(proof.read_text(encoding="utf-8"))
        rows = document.get("ledger_rows") or []
        if document.get("verdict") != "pass" or len(rows) != 1:
            raise AssertionError(f"the metering proof is not a pass with one row: {document}")
        if not isinstance(rows[0].get("ceq"), int) or rows[0].get("unmetered"):
            raise AssertionError("the metering proof's row carries no real ceq")
        code, out = run([sys.executable, "a0/meter/verify_ledger.py",
                         str(EVIDENCE / "meter-proof" / "meter_ledger.jsonl"), "--json"])
        if code != 0:
            raise AssertionError(f"the meter's verifier failed on the proof ledger: {out}")
        notes.append(f"in-namespace metered call: ceq={rows[0]['ceq']} "
                     f"(usage {rows[0]['usage']}), re-derived by a0/meter/verify_ledger.py")
    counter = EVIDENCE / "unmetered" / "unmetered_counterexample.json"
    if counter.is_file():
        document = json.loads(counter.read_text(encoding="utf-8"))
        row = document.get("row") or {}
        if not (document.get("verdict") == "pass" and row.get("unmetered") is True
                and row.get("ceq") is None and row.get("reason")):
            raise AssertionError(f"the unmetered counter-example is not the expected row: {row}")
        stopped = (document.get("budget_check") or {}).get("stopped_because")
        if stopped != "budget_exhausted:unmetered_model_call":
            raise AssertionError(f"the enforcer did not stop on the unmetered row: {stopped}")
        code, out = run([sys.executable, "a0/meter/verify_ledger.py",
                         str(EVIDENCE / "unmetered" / "meter_ledger.jsonl"), "--json"])
        if code != 0:
            raise AssertionError(f"the meter's verifier failed on the counter-example: {out}")
        notes.append(f"counter-example: unmetered row, reason={row['reason']}, "
                     f"ceq=null, budget stopped ({stopped})")
    if not notes:
        raise AssertionError("no metering evidence is committed")
    return " · ".join(notes)


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
        campaign = (rows[0]["campaign_id"] if rows
                    else json.loads((EVIDENCE / short / "pilot_arm.json").read_text(
                        encoding="utf-8"))["campaign_id"])
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
        if path.suffix == ".jsonl":
            documents = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif path.suffix == ".json":
            documents = [json.loads(text)]
        else:
            continue
        for index, document in enumerate(documents):
            paths = pilot.objective_key_paths(document, FORBIDDEN_KEYS)
            if paths:
                raise AssertionError(
                    f"{path.relative_to(HERE)}[{index}] uses {paths[:3]} — the pilot's "
                    "objective values must not be published")
    return f"{files} published files, none uses an objective value on a calibration graph as data"




def step_rehearsal() -> str:
    """The free closed-topology rehearsal: either the arms run, or they refuse — measured.

    The rehearsal's claim is not "it passed"; it is "the runner, the namespace hop, the
    metered port and the harness behave as the procedure says".  When an arm refuses at
    its frozen-identity precondition, that refusal *is* the observation, and it must be
    recorded as one rather than papered over.
    """
    with tempfile.TemporaryDirectory() as tmp:
        code, out = run([sys.executable, "a0/a1/calibration/pilot.py", "rehearsal",
                         "--out-dir", tmp])
        document = json.loads((Path(tmp) / "rehearsal.json").read_text(encoding="utf-8"))
    arms = document["arms"]
    topology = [name for name, entry in arms.items()
                if entry["topology_probe"].get("_negative_controls_blocked") is True
                and entry["topology_probe"].get("_meter_reachable") is True]
    if len(topology) != len(arms):
        raise AssertionError(f"the closed topology was not established for {arms.keys()}"
                             f" (established for {topology})")
    reached = [name for name, entry in arms.items() if entry["arm_reached_the_harness"]]
    if len(reached) == len(arms):
        if document["verdict"] != "pass":
            raise AssertionError(f"both arms reached the harness but the rehearsal is "
                                 f"{document['verdict']}: "
                                 f"{[k for k, v in arms['A_simpleloop']['checks'].items() if not v]}")
        return (f"both arms reached the harness through the closed topology, model calls "
                f"skipped: {sum(e['N_E_r'] for e in arms.values())} evaluations, "
                f"{sum(e['CEq_r'] for e in arms.values())} CEq")
    if document["verdict"] != "fail":
        raise AssertionError("a rehearsal where no arm reached the harness must not pass")
    codes = {name: sorted({unit["exit_code"] for unit in entry["unit_refusals"]})
             for name, entry in arms.items()}
    if any(0 in value for value in codes.values()):
        raise AssertionError(f"an arm exited 0 without reaching the harness: {codes}")
    return ("closed topology up (direct egress BLOCKED from inside `unshare -rn`, the "
            f"campaign port reachable) and both arms refuse before their first session "
            f"(exit codes {codes}); see evidence/BLOCKED.json")


STEPS = [
    ("freeze", "the procedure document hashes to the frozen value and the calibration "
               "graphs match the manifest", step_freeze, True),
    ("tests", "the model-free invariants of the mapping, the estimator and the reduction",
     step_tests, True),
    ("budget", "f re-applied to the committed evidence reproduces the committed budget — "
               "or reproduces the refusal, when no rate was measurable",
     step_budget, True),
    ("ledgers", "the meter's own verifier re-derives every published pilot row; none is "
                "unmetered", step_ledgers, True),
    ("meter-evidence", "the in-namespace metered call (a real ceq) and the induced "
                       "unmetered counter-example, both re-derived by the meter's own "
                       "verifier", step_meter_evidence, True),
    ("reduction", "no published file carries an objective value on a calibration graph",
     step_reduction, True),
    ("budget-loads", "the frozen B_hard is loadable by the skeleton's own Budget",
     step_budget_loads, True),
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
        except SkipStep as exc:
            print(f"SKIP {name:20s} {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {name:20s} {description}\n     {exc}")
        else:
            print(f"PASS {name:20s} {detail}")
    print("verdict:", "pass" if not failures else f"fail ({failures} step(s))")
    return 0 if not failures else 5


if __name__ == "__main__":
    sys.exit(main())
