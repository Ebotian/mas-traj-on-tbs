"""Model-free invariants of the calibration pilot (`a0/a1/calibration/`).

Nothing here spends money or needs the network: the mapping `f`, the estimator, the
published reduction and the freeze ordering are all pure functions of files.
"""

from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "a0"))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("calibration_pilot", HERE / "pilot.py")
pilot = importlib.util.module_from_spec(spec)
sys.modules["calibration_pilot"] = pilot
spec.loader.exec_module(pilot)


def telemetry(*, ceq: int, ne: int, seconds: float, arm: str = "A_simpleloop") -> dict:
    return {
        "arm": arm,
        "T_r_micros": int(round(seconds * 1_000_000)),
        "T_r_sec": seconds,
        "CEq_r": ceq,
        "N_E_r": ne,
        "unmetered_rows": 0,
        "units_completed": 24,
        "workload_complete": True,
        "variance": {"per_unit": {"rates": {"CEq": {"n": 24}, "N_E": {"n": 24},
                                            "T_sec": {"n": 24}}},
                     "per_window": {"CEq": {"n_full": 5}, "N_E": {"n_full": 5}}},
        "ceq_per_call": {"summary": {"n": ceq and 1 or 0}, "completion_tokens": []},
        "cost_sec": {},
        "tau_cross_check": {},
        "report": {},
    }


# --------------------------------------------------------------------------- #
# f
# --------------------------------------------------------------------------- #
def test_rates_are_exact_rationals():
    entry = telemetry(ceq=1000, ne=60, seconds=60.0)
    rate = pilot.arm_rates(entry)
    assert rate["q_r"] == Fraction(1000)
    assert rate["e_r"] == Fraction(60)


def test_f_matches_the_frozen_formula():
    procedure = pilot.load_procedure()
    entry = telemetry(ceq=1000, ne=60, seconds=60.0)
    result = pilot.apply_f({"A_simpleloop": entry}, procedure)
    # 1.25 * 30 * 1000 = 37500 ; 1.25 * 30 * 60 = 2250
    assert result["vector"]["CEq_max"] == 37500
    assert result["vector"]["N_evaluatorCalls"] == 2250
    assert result["vector"]["T_wall_sec"] == 1800.0
    assert result["vector"]["P_concurrency"] == 1
    assert result["clamped"] == {"CEq_max": False, "N_evaluatorCalls": False}


def test_f_takes_the_max_over_the_arms():
    procedure = pilot.load_procedure()
    slow = telemetry(ceq=1000, ne=60, seconds=60.0, arm="A_simpleloop")
    fast = telemetry(ceq=100, ne=6, seconds=60.0, arm="A_kapso")
    result = pilot.apply_f({"A_simpleloop": slow, "A_kapso": fast}, procedure)
    assert result["driving_arm"]["CEq_max"] == "A_simpleloop"
    assert result["vector"]["CEq_max"] == 37500


def test_f_is_monotone_and_bounded_on_the_measured_rates():
    procedure = pilot.load_procedure()
    entries = {"A_simpleloop": telemetry(ceq=8380, ne=72, seconds=300.0),
               "A_kapso": telemetry(ceq=1116, ne=48, seconds=300.0, arm="A_kapso")}
    result = pilot.apply_f(entries, procedure)
    properties = pilot.check_f_properties(entries, procedure, result)
    assert properties["monotone"] is True
    assert properties["bounded"] is True
    assert properties["total"] is True
    scales = [row["scale"] for row in properties["monotone_detail"]]
    assert scales == [0.5, 1.0, 2.0, 4.0]


def test_f_clamps_a_pathological_rate():
    procedure = pilot.load_procedure()
    huge = telemetry(ceq=10 ** 12, ne=10 ** 6, seconds=60.0)
    result = pilot.apply_f({"A_simpleloop": huge}, procedure)
    assert result["vector"]["CEq_max"] == procedure["mapping"]["CEQ_CEILING"]
    assert result["vector"]["N_evaluatorCalls"] == procedure["mapping"]["N_E_CEILING"]
    assert result["clamped"] == {"CEq_max": True, "N_evaluatorCalls": True}
    assert result["vector"]["unclamped"]["CEq_max"] > procedure["mapping"]["CEQ_CEILING"]


def test_f_rejects_a_zero_interval():
    procedure = pilot.load_procedure()
    with pytest.raises(pilot.PilotError):
        pilot.apply_f({"A_simpleloop": telemetry(ceq=1, ne=1, seconds=0.0)}, procedure)


def test_diagnostics_name_the_margin_and_the_spike_check():
    procedure = pilot.load_procedure()
    entry = telemetry(ceq=1000, ne=60, seconds=60.0)
    entry["variance"]["per_window"] = {
        "CEq": {"n_full": 1, "mean_full_rate": 1000.0, "max_full_rate": 9000.0},
        "N_E": {"n_full": 1, "mean_full_rate": 60.0, "max_full_rate": 60.0},
    }
    result = pilot.apply_f({"A_simpleloop": entry}, procedure)
    diag = pilot.diagnostics({"A_simpleloop": entry}, procedure, result)
    arm = diag["per_arm"]["A_simpleloop"]
    assert arm["D1_margin_CEq_minutes"] == pytest.approx(37.5)
    assert arm["D3_ceq_worst_window_ratio"] == pytest.approx(9.0)
    assert "CEq_spike_window" in arm["guardrails_would_bind_before_T_wall"]


# --------------------------------------------------------------------------- #
# the freeze
# --------------------------------------------------------------------------- #
def test_the_procedure_document_is_the_frozen_one():
    procedure = pilot.load_procedure()
    assert pilot.sha256_file(pilot.PROC_MD) == procedure["procedure"]["document_sha256"]


def test_load_procedure_refuses_a_changed_document(tmp_path, monkeypatch):
    procedure = json.loads(pilot.PROC_JSON.read_text(encoding="utf-8"))
    tampered = tmp_path / "pilot_procedure.json"
    procedure["procedure"]["document_sha256"] = "0" * 64
    tampered.write_text(json.dumps(procedure), encoding="utf-8")
    monkeypatch.setattr(pilot, "PROC_JSON", tampered)
    with pytest.raises(pilot.PilotError):
        pilot.load_procedure()


def test_the_calibration_units_are_the_manifest_s():
    units = pilot.calibration_units()
    manifest = json.loads(pilot.MANIFEST.read_text(encoding="utf-8"))
    declared = {g["graph_id"]: g["graph_sha256"] for g in manifest["graphs"]
                if g["path"].startswith("calibration/")}
    assert len(units) == 12
    assert [unit["graph_id"] for unit in units] == sorted(declared)
    assert {unit["graph_id"]: unit["graph_sha256"] for unit in units} == declared
    assert all(unit["path"].endswith(".json") for unit in units)


# --------------------------------------------------------------------------- #
# the estimator
# --------------------------------------------------------------------------- #
def test_percentile_is_nearest_rank():
    values = [float(v) for v in range(1, 101)]
    assert pilot.percentile_nearest_rank(values, 0.99) == 99.0
    assert pilot.percentile_nearest_rank(values, 0.50) == 50.0
    assert pilot.percentile_nearest_rank([], 0.99) is None


def test_summary_uses_the_sample_standard_deviation():
    stats = summary = pilot.summary([1.0, 2.0, 3.0, 4.0])
    assert stats["n"] == 4
    assert stats["mean"] == 2.5
    assert stats["sd"] == pytest.approx(math.sqrt(5.0 / 3.0))
    assert summary["min"] == 1.0 and summary["max"] == 4.0
    assert summary["median"] == 2.5


# --------------------------------------------------------------------------- #
# the published reduction
# --------------------------------------------------------------------------- #
def test_the_reduction_drops_the_objective_value():
    row = {"seq": 0, "ts": "t", "true_value": 132, "handed_value": 132, "status": "ok"}
    reduced = pilot.reduce_harness_row(row)
    assert "true_value" not in reduced and "handed_value" not in reduced
    assert reduced["status"] == "ok" and reduced["seq"] == 0
    outcome = {"status": "ok", "cut_edges": 317, "cut_fraction": "0.6",
               "interpreted": {"wall_ms": 41}}
    reduced_outcome = pilot.reduce_outcome(outcome)
    assert "cut_edges" not in reduced_outcome and "cut_fraction" not in reduced_outcome
    assert reduced_outcome["interpreted"]["wall_ms"] == 41


def _committed_evidence() -> Path:
    return HERE / "evidence"


def test_apply_refuses_a_rehearsal_record(tmp_path):
    for short in ("simpleloop", "kapso"):
        target = tmp_path / short
        target.mkdir(parents=True)
        (target / "pilot_arm.json").write_text(
            json.dumps({"mode": "rehearsal", "telemetry": {}}), encoding="utf-8")
    with pytest.raises(pilot.PilotError):
        pilot.load_published_telemetry(tmp_path)


# --------------------------------------------------------------------------- #
# validity
# --------------------------------------------------------------------------- #
def _published_telemetry(entry_overrides: dict) -> dict:
    entry = telemetry(ceq=1000, ne=60, seconds=300.0)
    entry.update({
        "CEq_r_ledger": 1000, "N_E_r_ledger": 60, "unmetered_rows_ledger": 0,
        "CEq_r_telemetry": 1000, "N_E_r_telemetry": 60,
        "ledger_agrees_with_telemetry": True,
        "models_reported": ["deepseek-flash"],
        "harness_graph_shas": [unit["graph_sha256"] for unit in pilot.calibration_units()],
        "T_r_sec": 300.0, "T_r_micros": 300_000_000, "units_completed": 24,
    })
    entry.update(entry_overrides)
    entry["report"] = {
        "campaign_id": "C_calib_A_simpleloop", "arm_id": "A_simpleloop", "mode": "pilot",
        "stop_reason": "workload_complete", "units_completed": 24,
        "workload_complete": True,
        "graphs": [{"graph_id": unit["graph_id"], "sha256": unit["graph_sha256"]}
                   for unit in pilot.calibration_units()],
        "caps": {}, "checks": {},
    }
    return {"A_simpleloop": entry, "A_kapso": dict(entry, report=dict(
        entry["report"], campaign_id="C_calib_A_kapso", arm_id="A_kapso"))}


def test_validity_holds_for_a_well_formed_record():
    procedure = pilot.load_procedure()
    assert pilot.validity_failures(procedure, _published_telemetry({})) == []


@pytest.mark.parametrize("override,expected", [
    ({"unmetered_rows_ledger": 1}, "V3"),
    ({"T_r_sec": 60.0, "T_r_micros": 60_000_000}, "V4"),
    ({"units_completed": 6}, "V4"),
    ({"models_reported": ["deepseek-chat"]}, "V5"),
    ({"harness_graph_shas": ["0" * 64]}, "V6"),
    ({"ledger_agrees_with_telemetry": False}, "V3"),
])
def test_validity_failures_are_named(override, expected):
    procedure = pilot.load_procedure()
    failures = pilot.validity_failures(procedure, _published_telemetry(override))
    assert any(failure.startswith(expected) for failure in failures), failures


# --------------------------------------------------------------------------- #
# the frozen artifact, once it exists
# --------------------------------------------------------------------------- #
def test_b_hard_loads_into_the_skeleton_budget():
    path = HERE / "B_hard.json"
    if not path.is_file():
        pytest.skip("B_hard.json not frozen yet")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["refused"] is False
    vector = document["vector"]
    from a0.a1.budget import Budget

    budget = Budget(T_wall_sec=vector["T_wall_sec"], N_eval_max=vector["N_evaluatorCalls"],
                    CEq_max=vector["CEq_max"], P_concurrency=vector["P_concurrency"])
    assert budget.as_dict()["T_wall_sec"] == 1800.0
    assert budget.CEq_max == vector["CEq_max"]
    assert document["mapping"]["properties"]["monotone"] is True
    assert document["mapping"]["properties"]["bounded"] is True
    assert document["mapping"]["properties"]["variance_reported"] is True


def test_the_committed_evidence_carries_no_objective_value():
    evidence = _committed_evidence()
    if not evidence.is_dir():
        pytest.skip("no committed evidence yet")
    forbidden = ("cut_edges", "cut_fraction", "true_value", "handed_value")
    offenders = []
    for path in sorted(evidence.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".jsonl":
            documents = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif path.suffix == ".json":
            documents = [json.loads(text)]
        else:
            continue
        for index, document in enumerate(documents):
            for found in pilot.objective_key_paths(document, forbidden):
                offenders.append((str(path.relative_to(evidence)), index, found))
    assert offenders == []


def test_objective_key_paths_ignores_the_reductions_own_documentation():
    document = {"reduction": {"outcome_keys_removed": ["cut_edges", "cut_fraction"]},
                "interpreted": {"wall_ms": 41}}
    assert pilot.objective_key_paths(document, ("cut_edges", "cut_fraction")) == []
    assert pilot.objective_key_paths({"cut_edges": 3}, ("cut_edges",)) == ["cut_edges"]
