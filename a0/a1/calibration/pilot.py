#!/usr/bin/env python3
"""The A1 calibration pilot: one bounded, metered campaign per arm over the calibration graphs.

`a0/a1/calibration/PILOT-PROCEDURE.md` is the frozen procedure and
`pilot_procedure.json` its machine-readable copy.  This file is the runner.  It
measures **resource rates** and nothing else: `CEq`/min, harness `E*` evaluations/min,
and the candidate latency distribution.  The pilot's algorithmic results are discarded:
they are not used for any selection, and the published evidence is a reduction in which
the score-bearing fields are removed (see the procedure's §0 and §8).

The ordering the procedure requires: the procedure document is committed and its sha256
recorded **before** any `suite/calibration/**` byte is read.  `freeze-check` and every
run verify that ordering mechanically.

    python3 a0/a1/calibration/pilot.py freeze-check
    python3 a0/a1/calibration/pilot.py rehearsal --out-dir /tmp/a1cal/rehearse   # free
    python3 a0/a1/calibration/pilot.py all       --out-dir /tmp/a1cal/pilot      # paid
    python3 a0/a1/calibration/pilot.py publish   --out-dir /tmp/a1cal/pilot      # free
    python3 a0/a1/calibration/pilot.py apply     --out-dir /tmp/a1cal/pilot/published
    python3 a0/a1/calibration/pilot.py unmetered --out-dir /tmp/a1cal/pilot      # ~free

The DeepSeek key is read from ``$DEEPSEEK_API_KEY`` (exported by the caller from
``~/gptapi.md`` in the same command) and reaches the children only through their
environment; it is never written to an artifact, a log or an argv.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from a0.a1.budget import Budget, BudgetEnforcer, BudgetError  # noqa: E402
from a0.a1.eval_service import HarnessEvalService  # noqa: E402
from a0.a1.meter_runner import MeterProxy, chat_completion  # noqa: E402
from a0.a1.topology import CampaignUplink, netns_prefix  # noqa: E402

PROC_MD = HERE / "PILOT-PROCEDURE.md"
PROC_JSON = HERE / "pilot_procedure.json"
SUITE = REPO_ROOT / "a0/tasks/maxcut/suite"
MANIFEST = SUITE / "manifest.json"
E_STAR = REPO_ROOT / "a0/tasks/maxcut/e_star.py"
E_STAR_PYTHON = Path("/usr/bin/python3")
SIMPLELOOP_PY = REPO_ROOT / "a0/runtimes/simpleloop/.venv/bin/python"
KAPSO_PY = REPO_ROOT / "a0/runtimes/kapso/.venv/bin/python"
KAPSO_DIR = REPO_ROOT / "a0/runtimes/kapso"
KAPSO_T1 = REPO_ROOT / "a0/a1/kapso_t1"
MODEL = "deepseek-flash"
MODEL_TIMEOUT = 180.0
BASELINE_CANDIDATE = "c02_ok_low_baseline"
MICRO = 10 ** 6
SHORT = {"A_simpleloop": "simpleloop", "A_kapso": "kapso"}

#: fields removed from every published file: they are the objective's value on a
#: calibration graph, and the procedure says the pilot's algorithmic results are not
#: published (see PILOT-PROCEDURE.md §0 and §8).
HARNESS_ROW_REDACT = ("true_value", "handed_value")
OUTCOME_REDACT = ("cut_edges", "cut_fraction")


class PilotError(RuntimeError):
    """The pilot cannot be established as the procedure defines it."""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_text(text)


def read_rows(path: Path) -> List[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def parse_ts(value: str) -> float:
    """ISO-8601 with either offset form (`+08:00` from the meter, `+0800` here)."""
    return datetime.fromisoformat(value).timestamp()


def quantised(value: float) -> int:
    """Microseconds.  `T_r` is quantised so the exact rational is a function of the record."""
    return int(round(float(value) * MICRO))


def frac(num: int, den: int) -> Fraction:
    return Fraction(int(num), int(den))


def to_sec_fraction(micros: int) -> Fraction:
    return Fraction(int(micros), MICRO)


def percentile_nearest_rank(values: List[float], p: float) -> Optional[float]:
    """`ceil(p*n)`-th smallest — the gate workstream's `tau_calibration.py` definition."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(1, math.ceil(p * len(ordered)))
    return ordered[min(index, len(ordered)) - 1]


def summary(values: List[float]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    n = len(ordered)
    mean = sum(ordered) / n
    if n > 1:
        sd = math.sqrt(sum((v - mean) ** 2 for v in ordered) / (n - 1))
    else:
        sd = 0.0
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "cv": (sd / mean) if mean else None,
        "min": ordered[0],
        "median": (
            ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        ),
        "max": ordered[-1],
        "p50": percentile_nearest_rank(ordered, 0.50),
        "p95": percentile_nearest_rank(ordered, 0.95),
        "p99": percentile_nearest_rank(ordered, 0.99),
    }


def reduce_harness_row(row: dict) -> dict:
    """The published form of a harness evaluation ledger row (score fields removed)."""
    return {key: value for key, value in row.items() if key not in HARNESS_ROW_REDACT}


def reduce_outcome(document: dict) -> dict:
    """The published form of a harness-authored Outcome (score fields removed)."""
    return {key: value for key, value in document.items() if key not in OUTCOME_REDACT}


def objective_key_paths(document: Any, forbidden, prefix: str = "") -> List[str]:
    """Where `document` *uses* a forbidden name as a key (naming it is not using it).

    The published reduction documents itself ("these keys were removed"), so a substring
    search would flag the documentation. Structural walk: only a dict key counts.
    """
    found: List[str] = []
    if isinstance(document, dict):
        for key, value in document.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(objective_key_paths(value, forbidden, path))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            found.extend(objective_key_paths(value, forbidden, f"{prefix}[{index}]"))
    return found


# --------------------------------------------------------------------------- #
# the frozen procedure
# --------------------------------------------------------------------------- #
def load_procedure() -> Dict[str, Any]:
    """Load the procedure, fail-closed on a document/JSON mismatch."""
    procedure = json.loads(PROC_JSON.read_text(encoding="utf-8"))
    declared = procedure["procedure"]["document_sha256"]
    actual = sha256_file(PROC_MD)
    if declared != actual:
        raise PilotError(
            "the frozen procedure document changed: PILOT-PROCEDURE.md hashes to "
            f"{actual}, pilot_procedure.json declares {declared}. A pilot run under a "
            "procedure that is not the frozen one is not this pilot."
        )
    return procedure


def manifest_graphs(role: str) -> List[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [g for g in manifest.get("graphs", [])
               if str(g.get("path", "")).startswith(f"{role}/")]
    entries.sort(key=lambda g: g["graph_id"])
    units = []
    for entry in entries:
        path = (SUITE / entry["path"]).resolve()
        digest = sha256_file(path)
        if digest != entry["graph_sha256"]:
            raise PilotError(
                f"{entry['graph_id']}: file sha256 {digest} != manifest {entry['graph_sha256']}"
            )
        units.append({"graph_id": entry["graph_id"], "path": str(path),
                      "graph_sha256": digest, "family": entry.get("family"),
                      "n": entry.get("n"), "edges": entry.get("edges")})
    return units


def calibration_units() -> List[dict]:
    """The 12 calibration graphs, in manifest order, each verified against the manifest."""
    units = manifest_graphs("calibration")
    if len(units) != 12:
        raise PilotError(f"the manifest lists {len(units)} calibration graphs, not 12")
    return units


def rehearsal_units() -> List[dict]:
    """One dev graph, for the free rehearsal only.  Never an input to `f`."""
    units = manifest_graphs("dev")
    return [unit for unit in units if unit["graph_id"] == "G_dev_0001"][:1]


# --------------------------------------------------------------------------- #
# the mapping f
# --------------------------------------------------------------------------- #
def arm_rates(telemetry: dict) -> Dict[str, Fraction]:
    T = to_sec_fraction(telemetry["T_r_micros"])
    if T <= 0:
        raise PilotError("T_r is not positive; no rate is established")
    ceq = int(telemetry["CEq_r"])
    ne = int(telemetry["N_E_r"])
    return {"q_r": Fraction(60 * ceq) / T, "e_r": Fraction(60 * ne) / T}


def apply_f(per_arm: Dict[str, dict], procedure: Dict[str, Any]) -> dict:
    """`f(telemetry) -> B_hard`, mechanically.  See procedure §4."""
    mapping = procedure["mapping"]
    factor = frac(mapping["factor"]["numerator"], mapping["factor"]["denominator"])
    window = Fraction(int(mapping["window_minutes"]))
    ceq_ceiling = int(mapping["CEQ_CEILING"])
    ne_ceiling = int(mapping["N_E_CEILING"])

    rates: Dict[str, Dict[str, Fraction]] = {}
    rows = {}
    for arm, telemetry in sorted(per_arm.items()):
        rate = arm_rates(telemetry)
        rates[arm] = rate
        rows[arm] = {
            "q_r_ceq_per_min": float(rate["q_r"]),
            "e_r_evals_per_min": float(rate["e_r"]),
            "C_r_ceq_per_30min": float(window * rate["q_r"]),
            "E_r_evals_per_30min": float(window * rate["e_r"]),
            "q_r_exact": f"{rate['q_r'].numerator}/{rate['q_r'].denominator}",
            "e_r_exact": f"{rate['e_r'].numerator}/{rate['e_r'].denominator}",
        }

    target_ceq = factor * window * max(rate["q_r"] for rate in rates.values())
    target_ne = factor * window * max(rate["e_r"] for rate in rates.values())
    ceq_max = int(math.ceil(target_ceq))
    ne_max = int(math.ceil(target_ne))
    clamped = {"CEq_max": ceq_max > ceq_ceiling, "N_evaluatorCalls": ne_max > ne_ceiling}
    vector = {
        "T_wall_sec": float(mapping["T_wall_sec"]),
        "N_evaluatorCalls": min(ne_max, ne_ceiling),
        "CEq_max": min(ceq_max, ceq_ceiling),
        "P_concurrency": int(mapping["P_concurrency"]),
        "unclamped": {"CEq_max": ceq_max, "N_evaluatorCalls": ne_max},
    }
    return {
        "vector": vector,
        "per_arm": rows,
        "driving_arm": {
            "CEq_max": max(rates, key=lambda a: rates[a]["q_r"]),
            "N_evaluatorCalls": max(rates, key=lambda a: rates[a]["e_r"]),
        },
        "clamped": clamped,
        "formula": mapping["formula"],
    }


def check_f_properties(per_arm: Dict[str, dict], procedure: Dict[str, Any],
                       result: dict) -> dict:
    """`f`'s required properties (procedure §4), checked on the measured rates."""
    mapping = procedure["mapping"]
    baseline = {arm: arm_rates(telemetry) for arm, telemetry in per_arm.items()}
    monotone = True
    detail: List[dict] = []
    previous = None
    for scale in (Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)):
        scaled = {}
        for arm, telemetry in per_arm.items():
            T = to_sec_fraction(telemetry["T_r_micros"])
            scaled[arm] = {
                "T_r_micros": telemetry["T_r_micros"],
                "CEq_r": int(round(float(baseline[arm]["q_r"] * scale * T / 60))),
                "N_E_r": int(round(float(baseline[arm]["e_r"] * scale * T / 60))),
            }
        vector = apply_f(scaled, procedure)["vector"]
        entry = {"scale": float(scale), "CEq_max": vector["CEq_max"],
                 "N_evaluatorCalls": vector["N_evaluatorCalls"]}
        detail.append(entry)
        if previous is not None and (
            entry["CEq_max"] < previous["CEq_max"]
            or entry["N_evaluatorCalls"] < previous["N_evaluatorCalls"]
        ):
            monotone = False
        previous = entry
    vector = result["vector"]
    bounded = (
        vector["T_wall_sec"] == float(mapping["T_wall_sec"])
        and 0 < vector["CEq_max"] <= int(mapping["CEQ_CEILING"])
        and 0 < vector["N_evaluatorCalls"] <= int(mapping["N_E_CEILING"])
        and vector["P_concurrency"] == int(mapping["P_concurrency"])
    )
    variance_reported = all(
        telemetry.get("variance", {}).get("per_unit", {}).get("rates", {})
        .get("CEq", {}).get("n", 0) > 0
        and telemetry.get("variance", {}).get("per_window", {}).get("CEq", {})
        .get("n_full", 0) > 0
        for telemetry in per_arm.values()
    )
    return {
        "monotone": monotone,
        "monotone_detail": detail,
        "bounded": bounded,
        "variance_reported": variance_reported,
        "total": bool(per_arm) and all(
            telemetry["T_r_micros"] > 0 for telemetry in per_arm.values()
        ),
        "ceiling_active": result["clamped"],
    }


def diagnostics(per_arm: Dict[str, dict], procedure: Dict[str, Any], result: dict) -> dict:
    """Procedure §7's D1–D5, per arm, from the measured telemetry."""
    mapping = procedure["mapping"]
    t_wall_min = float(mapping["T_wall_sec"]) / 60.0
    factor = float(frac(mapping["factor"]["numerator"], mapping["factor"]["denominator"]))
    out = {"T_wall_min": t_wall_min, "factor": factor, "per_arm": {}}
    for arm, telemetry in sorted(per_arm.items()):
        rate = arm_rates(telemetry)
        q = float(rate["q_r"])
        e = float(rate["e_r"])
        windows = telemetry["variance"]["per_window"]
        ceq_max_window = windows["CEq"].get("max_full_rate") or 0.0
        ne_max_window = windows["N_E"].get("max_full_rate") or 0.0
        ceq_mean_window = windows["CEq"].get("mean_full_rate") or 0.0
        ne_mean_window = windows["N_E"].get("mean_full_rate") or 0.0
        entry = {
            "q_r_ceq_per_min": q,
            "e_r_evals_per_min": e,
            "D1_margin_CEq_minutes": (result["vector"]["CEq_max"] / q) if q else None,
            "D2_margin_NE_minutes": (result["vector"]["N_evaluatorCalls"] / e) if e else None,
            "D3_ceq_worst_window_ratio": (ceq_max_window / ceq_mean_window)
            if ceq_mean_window else None,
            "D3_ne_worst_window_ratio": (ne_max_window / ne_mean_window)
            if ne_mean_window else None,
            "D3_threshold": factor,
            "D5_ceq_per_call": telemetry.get("ceq_per_call", {}).get("summary", {}),
            "D5_completion_tokens": telemetry.get("ceq_per_call", {}).get("completion_tokens"),
            "D4_tau_cross_check": telemetry.get("tau_cross_check", {}),
            "variance": {
                "per_unit_ceq": telemetry["variance"]["per_unit"]["rates"].get("CEq", {}),
                "per_unit_ne": telemetry["variance"]["per_unit"]["rates"].get("N_E", {}),
                "per_unit_seconds": telemetry["variance"]["per_unit"]["rates"].get("T_sec", {}),
                "per_window_ceq": {k: v for k, v in windows["CEq"].items()
                                   if k != "full_windows"},
                "per_window_ne": {k: v for k, v in windows["N_E"].items()
                                  if k != "full_windows"},
            },
        }
        early = []
        for name, margin in (("CEq_max", entry["D1_margin_CEq_minutes"]),
                             ("N_evaluatorCalls", entry["D2_margin_NE_minutes"])):
            if margin is not None and margin < t_wall_min:
                early.append(name)
        if (entry["D3_ceq_worst_window_ratio"] or 0) > factor:
            early.append("CEq_spike_window")
        if (entry["D3_ne_worst_window_ratio"] or 0) > factor:
            early.append("N_E_spike_window")
        entry["guardrails_would_bind_before_T_wall"] = early
        out["per_arm"][arm] = entry
    return out


def frozen_identity_status() -> dict:
    """Is the T1 frozen evaluator identity still the identity of the bytes on disk?

    `a0/a1/T1.contract.json` and `a0/a1/T1-EID.json` freeze `EID*` (and the two
    `EvaluatorSource` digests) at a revision of `a0/tasks/maxcut/e_star.py`.  Both arms
    verify that before they will run, and the SimpleLoop adapter's check and KAPSO's
    registration are independent of each other.  A pilot whose arms refuse at that
    precondition has no rates to measure, so it is checked *before* anything else runs.
    """
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "a0" / "a1" / "t1_eid.py"), "check"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=180,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"pass": False, "reason": "t1_eid.py check produced no JSON",
                   "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    payload["exit_code"] = proc.returncode
    payload["consistent"] = bool(proc.returncode == 0 and payload.get("pass") is True)
    payload["command"] = "python3 a0/a1/t1_eid.py check"
    if not payload["consistent"]:
        payload["what_this_blocks"] = (
            "both A1 arms refuse at their frozen-identity precondition: the SimpleLoop "
            "adapter exits 3 (`evalcontract.py verify` drift against T1.contract.json) and "
            "KAPSO's EvaluationMaintainer raises before the session starts (`E* source "
            "drifted … recorded in EID*`). A resource pilot cannot measure a rate through "
            "an arm that will not start."
        )
        payload["what_would_unblock_it"] = (
            "the owner of a0/a1/T1-EID.json + T1.contract.json re-freezes the evaluator "
            "identity against the current E* bytes (`python3 a0/a1/t1_eid.py build`, then "
            "re-declare CID's `task.eid_star`), or a0/tasks/maxcut/e_star.py is returned to "
            "the revision the frozen EID* names. This workstream owns neither file and did "
            "not change either of them."
        )
    return payload


def require_frozen_identity() -> dict:
    status = frozen_identity_status()
    if not status["consistent"]:
        raise PilotError(
            "the arms cannot start: the frozen evaluator identity does not match the E* "
            f"bytes on disk ({status.get('reason')}: {status.get('on_disk')} -> "
            f"{status.get('recomputed')}). See the blocker artifact for the remedy."
        )
    return status


# --------------------------------------------------------------------------- #
# the campaign
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class Unit:
    index: int
    pass_index: int
    graph_id: str
    graph_path: str
    graph_sha256: str
    started_epoch: float
    started_micros: int
    ended_epoch: float
    ended_micros: int
    exit_code: int
    stdout: str
    stderr: str

    @property
    def elapsed_micros(self) -> int:
        return self.ended_micros - self.started_micros

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "pass": self.pass_index,
            "graph_id": self.graph_id,
            "graph_sha256": self.graph_sha256,
            "started_epoch": self.started_epoch,
            "ended_epoch": self.ended_epoch,
            "elapsed_sec": self.elapsed_micros / MICRO,
            "exit_code": self.exit_code,
            "stdout_tail": self.stdout[-2000:],
            "stderr_tail": self.stderr[-2000:],
        }

    def published(self) -> dict:
        """The unit row as published: console output by digest, never by content."""
        return published_unit(self.as_dict())


def published_unit(unit: dict) -> dict:
    """The published form of a per-unit row (see PILOT-PROCEDURE.md §8)."""
    stdout = unit.get("stdout_tail") or ""
    stderr = unit.get("stderr_tail") or ""
    return {
        "index": unit["index"],
        "pass": unit["pass"],
        "graph_id": unit["graph_id"],
        "graph_sha256": unit["graph_sha256"],
        "started_epoch": unit["started_epoch"],
        "ended_epoch": unit["ended_epoch"],
        "elapsed_sec": unit["elapsed_sec"],
        "exit_code": unit["exit_code"],
        "stdout_sha256": sha256_text(stdout),
        "stdout_bytes": len(stdout),
        "stderr_sha256": sha256_text(stderr),
        "stderr_bytes": len(stderr),
    }


class PilotCampaign:
    """One arm, one bounded campaign, inside the closed topology."""

    def __init__(self, *, arm: str, out_dir: Path, procedure: Dict[str, Any],
                 procedure_sha: str, rehearsal: bool = False,
                 units: Optional[List[dict]] = None, passes_max: Optional[int] = None) -> None:
        self.arm = arm
        self.procedure = procedure
        self.procedure_sha = procedure_sha
        self.rehearsal = rehearsal
        self.mode = "rehearsal" if rehearsal else "pilot"
        self.short = SHORT[arm]
        self.out_dir = Path(out_dir).resolve()
        self.work = self.out_dir / self.short
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)
        self.units = units or calibration_units()
        spec = procedure["arms"][arm]
        self.loop_depth = int(spec["loop"].get("max_iterations")
                              or spec["loop"].get("rounds"))
        self.model_calls_per_unit = int(spec["model_calls_per_unit"])
        self.evals_per_unit = int(spec["evals_per_unit"])
        self.max_tokens = int(spec["max_tokens_per_call"])
        self.passes_max = int(passes_max if passes_max is not None
                              else procedure["graph_set"]["passes_max"])
        caps = procedure["caps"][arm]
        self.caps = {
            "T_wall_sec": float(caps["T_wall_sec"]),
            "CEq_max": int(caps["CEq_max"]) if not rehearsal else 10 ** 9,
            "N_E_max": int(caps["N_E_max"]) if not rehearsal else 10 ** 6,
        }
        self.campaign_id = (f"C_rehearsal_A_{self.short}" if rehearsal
                            else procedure["campaign_ids"][arm])
        self.arm_id = arm
        seed = int(procedure["theta"]["seed"])
        timeout_s = float(procedure["theta"]["timeout_s"])
        self.meter = MeterProxy(campaign_id=self.campaign_id, arm_id=self.arm_id,
                                work_dir=self.work / "meter")
        self.uplink = CampaignUplink(campaign_id=self.campaign_id,
                                     meter_port=self.meter.port)
        self.harness = HarnessEvalService(
            root=self.work / "harness", campaign_id=self.campaign_id, arm_id=self.arm_id,
            evaluator="maxcut", e_star_script=E_STAR, python=E_STAR_PYTHON,
            seed=seed, timeout_s=timeout_s, harness_run_id=f"calib-{self.short}",
        )
        self.enforcer = BudgetEnforcer(
            budget=Budget(T_wall_sec=self.caps["T_wall_sec"],
                          N_eval_max=self.caps["N_E_max"], CEq_max=self.caps["CEq_max"]),
            meter_ledger=self.meter.ledger,
            harness_eval_ledger=self.harness.ledger_path,
            campaign_id=self.campaign_id, arm_id=self.arm_id,
        )
        self.harness_process: Optional[subprocess.Popen] = None
        self.units_run: List[Unit] = []
        self.stop_reason: Optional[str] = None
        self.launch_epoch: Optional[float] = None
        self.end_epoch: Optional[float] = None
        self.launch_micros: Optional[int] = None
        self.end_micros: Optional[int] = None
        self.topology_probe: dict = {}

    # ---------------------------------------------------------------- #
    def _safe_check(self, label: str) -> dict:
        """`BudgetEnforcer.check`, with the not-yet-booked case named rather than raised.

        A campaign whose ledger has no rows yet has spent nothing; anything else that makes
        the ledgers unreadable is a stop condition, not a zero.
        """
        try:
            return self.enforcer.check(label=label)
        except BudgetError as exc:
            if not self.units_run:
                return {
                    "within": True,
                    "stopped_because": None,
                    "detail": f"nothing booked yet; the ledger is empty: {exc}",
                    "observed": {"CEq": 0, "N_evaluatorCalls": 0, "T_wall_sec": 0.0,
                                 "unmetered_rows": 0},
                }
            return {"within": False, "stopped_because": "budget_unreadable",
                    "detail": str(exc), "observed": {}}

    def _arm_command(self, unit: dict, run_dir: Path, remaining_wall: float,
                     remaining_evals: int) -> List[str]:
        common = [
            "--work-root", str(REPO_ROOT),
            "--runtime", "simpleloop",
            "--task", "maxcut",
            "--candidate-set", "a0/tasks/maxcut/candidates/manifest.json",
            "--eid", "a0/a1/T1-EID.json",
            "--eid-spec", "a0/a1/T1.contract.json",
            "--eval-mode", "harness",
            "--harness-root", str(self.harness.root),
            "--campaign-id", self.campaign_id,
            "--arm-id", self.arm_id,
            "--graph", str(Path(unit["path"])),
            "--baseline-candidate", BASELINE_CANDIDATE,
            "--policy", "a0/runtimes/simpleloop/policy/simpleloop.maxcut.policy.json",
            "--theta", "seed=1337,fidelity=none,fraction=none,timeout_s=10",
            "--e-star", "a0/tasks/maxcut/e_star.py",
            "--budget", f"T_wall_sec={max(int(remaining_wall), 1)},"
                        f"N_evaluatorCalls={max(int(remaining_evals), 1)},concurrency=1",
            "--max-iterations", str(self.loop_depth),
            "--run-dir", str(run_dir),
        ]
        if self.rehearsal:
            return [str(SIMPLELOOP_PY), "-m", "a0_adapter", "run", *common,
                    "--solver", "injected",
                    "--solver-script", str(self._rehearsal_script())]
        return [str(SIMPLELOOP_PY), "-m", "a0_adapter", "run", *common,
                "--solver", "deepseek",
                "--model-base-url", self.meter.base_url,
                "--model-name", MODEL,
                "--model-max-tokens", str(self.max_tokens),
                "--model-timeout-s", str(MODEL_TIMEOUT),
                *(["--meter-token=" + self.meter.token] if self.meter.token else [])]

    def _kapso_command(self, unit: dict, run_dir: Path) -> List[str]:
        return [
            str(KAPSO_PY), str(Path(__file__).resolve()), "kapso-inner",
            "--out-dir", str(self.work / "kapso"),
            "--base-url", self.meter.base_url,
            "--graph", str(Path(unit["path"])),
            "--rounds", str(self.loop_depth),
            "--run-dir", str(run_dir),
            "--state-root", str(self.work / "kapso-state"),
            "--campaign-id", self.campaign_id,
            "--arm-id", self.arm_id,
            "--harness-root", str(self.harness.root),
            "--max-tokens", str(self.max_tokens),
            *(["--meter-token=" + self.meter.token] if self.meter.token else []),
            *(["--no-model"] if self.rehearsal else []),
        ]

    def _rehearsal_script(self) -> Path:
        path = self.work / "solver_script.json"
        if not path.is_file():
            members = [BASELINE_CANDIDATE, "c01_ok_high_pc", "c03_ok_zero"]
            write_json(path, {
                "schema": "a0.simpleloop.solver_script/v1",
                "proposals": [
                    {"iteration": index, "kind": "c_star_member", "candidate_id": candidate}
                    for index, candidate in enumerate(members[: max(self.loop_depth, 1)])
                ],
            })
        return path

    def _probe_with_relay(self) -> dict:
        script = (
            "import json, socket\n"
            "report = {}\n"
            "for host in ('123.148.116.184', '1.1.1.1', '8.8.8.8'):\n"
            "    try:\n"
            "        socket.create_connection((host, 443), timeout=4).close()\n"
            "        report[host] = 'REACHED'\n"
            "    except OSError as exc:\n"
            "        report[host] = 'BLOCKED:' + type(exc).__name__\n"
            "try:\n"
            "    socket.create_connection(('127.0.0.1', PORT), timeout=4).close()\n"
            "    report['meter_loopback'] = 'REACHED'\n"
            "except OSError as exc:\n"
            "    report['meter_loopback'] = 'BLOCKED:' + type(exc).__name__\n"
            "print(json.dumps(report))\n"
        ).replace("PORT", str(self.meter.port))
        inner = self.uplink.enter_command([sys.executable, "-c", script])
        proc = subprocess.run(netns_prefix() + inner, cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=120,
                              env={**os.environ, "PYTHONPATH": self._pythonpath()})
        lines = [line for line in (proc.stdout or "").splitlines()
                 if line.strip().startswith("{")]
        report = json.loads(lines[-1]) if lines else {"error": (proc.stderr or "")[-400:]}
        negatives = [key for key in ("123.148.116.184", "1.1.1.1", "8.8.8.8") if key in report]
        report["_negative_controls_blocked"] = bool(negatives) and all(
            str(report[key]).startswith("BLOCKED") for key in negatives
        )
        report["_meter_reachable"] = report.get("meter_loopback") == "REACHED"
        return report

    def _pythonpath(self) -> str:
        """Arm-specific: `a0_adapter` resolves to *this* arm's adapter package.

        `a0/runtimes/simpleloop/a0_adapter` and `a0/runtimes/kapso/a0_adapter` are two
        different packages with the same name, so the order of this list decides which one
        a bare `import a0_adapter` gets (measured: a shared list made the KAPSO inner
        import the SimpleLoop adapter and fail with `No module named 'a0_adapter.common'`).
        """
        if self.short == "kapso":
            return os.pathsep.join([str(REPO_ROOT), str(KAPSO_DIR), str(KAPSO_T1)])
        return os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "a0/runtimes/simpleloop")])

    # ---------------------------------------------------------------- #
    def run(self) -> dict:
        if not self.rehearsal and not os.environ.get("DEEPSEEK_API_KEY"):
            raise PilotError("export DEEPSEEK_API_KEY (read from ~/gptapi.md) in this command")
        graph_shas = {unit["graph_sha256"] for unit in self.units}
        report: Dict[str, Any] = {
            "schema": "a0.a1.calibration.pilot_arm/v1",
            "mode": self.mode,
            "not_used_for_selection": True,
            "discarded_sentence": "The pilot's algorithmic results are discarded.",
            "procedure": {
                "document": "a0/a1/calibration/PILOT-PROCEDURE.md",
                "document_sha256": self.procedure_sha,
                "json": "a0/a1/calibration/pilot_procedure.json",
                "json_sha256": sha256_file(PROC_JSON),
            },
            "runner": {"path": "a0/a1/calibration/pilot.py",
                       "sha256": sha256_file(Path(__file__).resolve())},
            "arm": self.arm,
            "runtime": self.procedure["arms"][self.arm]["runtime"],
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "model_requested": MODEL,
            "theta": self.procedure["theta"],
            "caps": dict(self.caps),
            "workload": {
                "graph_role": "calibration" if not self.rehearsal else "dev (rehearsal)",
                "passes_max": self.passes_max,
                "units_per_pass": len(self.units),
                "loop_depth": self.loop_depth,
                "model_calls_per_unit_expected": self.model_calls_per_unit,
                "evals_per_unit_expected": self.evals_per_unit,
                "max_tokens_per_call": self.max_tokens,
            },
            "graphs": [{"graph_id": unit["graph_id"], "sha256": unit["graph_sha256"]}
                       for unit in self.units],
            "graph_set_sha256": sha256_text(json.dumps(sorted(graph_shas), sort_keys=True)),
            "frozen_identity": frozen_identity_status(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        self.meter.start()
        try:
            self.uplink.start()
            report["meter"] = {"port": self.meter.port, "base_url": self.meter.base_url,
                               "ledger": str(self.meter.ledger), "aid": self.meter.aid(),
                               "token_issued": bool(self.meter.token)}
            self.harness_process = subprocess.Popen(
                [sys.executable, str(HERE.parent / "eval_service.py"), "serve",
                 "--root", str(self.harness.root), "--evaluator", "maxcut",
                 "--e-star", str(E_STAR), "--python", str(E_STAR_PYTHON),
                 "--campaign-id", self.campaign_id, "--arm-id", self.arm_id,
                 "--harness-run-id", f"calib-{self.short}",
                 "--seed", str(self.procedure["theta"]["seed"]),
                 "--timeout-s", str(self.procedure["theta"]["timeout_s"]),
                 "--stop-file", str(self.work / "harness.stop")],
                cwd=str(REPO_ROOT),
                stdout=(self.work / "harness.console.txt").open("wb"),
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not (
                self.harness.root / "harness_identity.json"
            ).is_file():
                time.sleep(0.05)
            if not (self.harness.root / "harness_identity.json").is_file():
                raise PilotError("the harness evaluation service did not come up")
            report["harness"] = {
                "root": str(self.harness.root),
                "ledger": str(self.harness.ledger_path),
                "identity": json.loads(
                    (self.harness.root / "harness_identity.json").read_text(encoding="utf-8")
                ),
            }
            self.topology_probe = self._probe_with_relay()
            report["topology_probe"] = self.topology_probe
            self._run_units()
        finally:
            (self.work / "harness.stop").write_text("stop\n", encoding="utf-8")
            if self.harness_process is not None:
                try:
                    self.harness_process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    self.harness_process.kill()
                    self.harness_process.wait()
            self.uplink.stop()
            self.meter.stop()

        report["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        report["units"] = [unit.as_dict() for unit in self.units_run]
        report["stop_reason"] = self.stop_reason
        report["ledger"] = self._ledger_view()
        report["telemetry"] = self._telemetry(report)
        report["checks"] = self._checks(report)
        report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
        write_json(self.work / "pilot_arm.json", report)
        return report

    # ---------------------------------------------------------------- #
    def _run_units(self) -> None:
        self.launch_epoch = time.time()
        self.launch_micros = quantised(self.launch_epoch)
        started_monotonic = time.monotonic()
        index = 0
        for pass_index in range(self.passes_max):
            for unit in self.units:
                elapsed = time.monotonic() - started_monotonic
                if elapsed > self.caps["T_wall_sec"]:
                    self.stop_reason = "T_wall_sec"
                    self.end_epoch, self.end_micros = time.time(), quantised(time.time())
                    return
                verdict = self._safe_check(label=f"before-unit-{index}")
                if not verdict["within"]:
                    self.stop_reason = str(verdict["stopped_because"])
                    self.end_epoch, self.end_micros = time.time(), quantised(time.time())
                    return
                observed = verdict["observed"]
                remaining_wall = self.caps["T_wall_sec"] - elapsed
                remaining_evals = max(
                    self.caps["N_E_max"] - int(observed.get("N_evaluatorCalls") or 0), 1
                )
                run_dir = self.work / "runs" / f"p{pass_index}_{unit['graph_id']}"
                run_dir.mkdir(parents=True, exist_ok=True)
                if self.short == "simpleloop":
                    command = self._arm_command(unit, run_dir, remaining_wall, remaining_evals)
                else:
                    command = self._kapso_command(unit, run_dir)
                started_epoch = time.time()
                started_micros = quantised(started_epoch)
                timeout = max(min(remaining_wall, 600.0) + 60.0, 60.0)
                try:
                    proc = subprocess.run(
                        self.uplink.enter_command(command), cwd=str(REPO_ROOT),
                        capture_output=True, text=True, timeout=timeout,
                        env={**os.environ, "PYTHONPATH": self._pythonpath()},
                    )
                    exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
                except subprocess.TimeoutExpired as exc:
                    exit_code = 124
                    out = exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                    err = exc.stderr if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                    stdout = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
                    stderr = (err.decode("utf-8", "replace") if isinstance(err, bytes) else err)
                    stderr += "\nthe driver timed out this unit"
                ended_epoch = time.time()
                self.units_run.append(Unit(
                    index=index, pass_index=pass_index, graph_id=unit["graph_id"],
                    graph_path=unit["path"], graph_sha256=unit["graph_sha256"],
                    started_epoch=started_epoch, started_micros=started_micros,
                    ended_epoch=ended_epoch, ended_micros=quantised(ended_epoch),
                    exit_code=exit_code, stdout=stdout or "", stderr=stderr or "",
                ))
                index += 1
            if pass_index + 1 >= self.passes_max:
                self.stop_reason = "workload_complete"
                break
        self.end_epoch, self.end_micros = time.time(), quantised(time.time())

    # ---------------------------------------------------------------- #
    def _ledger_view(self) -> dict:
        meter_rows = [row for row in read_rows(self.meter.ledger)
                      if row.get("campaign_id") == self.campaign_id]
        harness_rows = [row for row in read_rows(self.harness.ledger_path)
                        if row.get("campaign_id") == self.campaign_id]
        return {
            "meter_rows": meter_rows,
            "harness_rows": harness_rows,
            "meter_ledger": str(self.meter.ledger),
            "meter_ledger_sha256": (sha256_file(self.meter.ledger)
                                    if self.meter.ledger.is_file() else None),
            "harness_ledger": str(self.harness.ledger_path),
            "harness_ledger_sha256": (sha256_file(self.harness.ledger_path)
                                      if self.harness.ledger_path.is_file() else None),
            "meter_verify": self.meter.verify_ledger(),
        }

    # ---------------------------------------------------------------- #
    def _arm_unit_state(self, unit: Unit) -> dict:
        """Per-unit resource state, with every algorithmic value left out."""
        run_dir = self.work / "runs" / f"p{unit.pass_index}_{unit.graph_id}"
        if self.short == "simpleloop":
            meta_path = run_dir / "run_meta.json"
            if not meta_path.is_file():
                return {"kind": "simpleloop", "present": False}
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            history = meta.get("history") or []
            return {
                "kind": "simpleloop",
                "present": True,
                "exit_code": meta.get("exit_code"),
                "stopped_because": meta.get("stopped_because"),
                "iterations": len(history),
                "model_proposals": sum(1 for row in history
                                       if str(row.get("proposal_source", "")).startswith("model:")),
                "e_star_statuses": [row.get("e_star_status") for row in history],
                "scores_omitted": "the pilot does not publish objectives on calibration graphs",
            }
        state_path = run_dir / "unit_state.json"
        if not state_path.is_file():
            return {"kind": "kapso", "present": False}
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return {
            "kind": "kapso",
            "present": True,
            "rounds": state.get("rounds"),
            "nodes": len(state.get("nodes") or []),
            "harness_calls": state.get("harness_calls"),
            "model_calls": len(state.get("model_calls") or []),
            "model_usage": [row.get("usage") for row in (state.get("model_calls") or [])],
            "model_latency_sec": [row.get("latency_sec") for row in
                                  (state.get("model_calls") or [])],
            "eid_star": state.get("eid_star"),
            "eid_r": state.get("eid_r"),
            "eid_r_matches_the_t1_tree_record": state.get("eid_r_matches_the_t1_tree_record"),
            "granted_class": state.get("granted_class"),
            "holdout_bytes_in_workspace": state.get("holdout_bytes_in_workspace"),
            "model_call_skipped": state.get("model_call_skipped"),
            "scores_omitted": "the pilot does not publish objectives on calibration graphs",
        }

    # ---------------------------------------------------------------- #
    def _telemetry(self, report: dict) -> dict:
        meter_rows = report["ledger"]["meter_rows"]
        harness_rows = report["ledger"]["harness_rows"]
        metered = [row for row in meter_rows if not row.get("unmetered")]
        ceq_total = sum(int(row["ceq"]) for row in metered if isinstance(row.get("ceq"), int))
        t0 = self.launch_micros if self.launch_micros is not None else quantised(time.time())
        t1 = self.end_micros if self.end_micros is not None else quantised(time.time())

        per_unit = {"CEq": [], "N_E": [], "T_sec": []}
        unit_rows: List[dict] = []
        attributed_ceq = 0
        attributed_evals = 0
        for unit in self.units_run:
            ceq_u = sum(int(row["ceq"]) for row in metered
                        if isinstance(row.get("ceq"), int)
                        and unit.started_epoch <= parse_ts(row["ts"]) <= unit.ended_epoch)
            rows_u = [row for row in harness_rows
                      if unit.started_epoch <= parse_ts(row["ts"]) <= unit.ended_epoch]
            attributed_ceq += ceq_u
            attributed_evals += len(rows_u)
            seconds = unit.elapsed_micros / MICRO
            unit_rows.append({
                "unit": unit.index, "pass": unit.pass_index, "graph_id": unit.graph_id,
                "elapsed_sec": seconds, "CEq": ceq_u, "N_E": len(rows_u),
                "exit_code": unit.exit_code,
                "statuses": [row.get("status") for row in rows_u],
                "arm_state": self._arm_unit_state(unit),
            })
            if seconds > 0:
                per_unit["CEq"].append(60.0 * ceq_u / seconds)
                per_unit["N_E"].append(60.0 * len(rows_u) / seconds)
                per_unit["T_sec"].append(seconds)

        windows = self._windows(meter_rows, harness_rows, t0, t1)

        candidate_ms: List[float] = []
        e_star_sec: List[float] = []
        outcome_dir = self.work / "outcomes"
        outcome_dir.mkdir(parents=True, exist_ok=True)
        for row in harness_rows:
            request_id = str(row.get("request_id") or "")
            outcome_path = self.harness.root / "state" / request_id / "outcome.json"
            if outcome_path.is_file():
                document = json.loads(outcome_path.read_text(encoding="utf-8"))
                shutil.copyfile(outcome_path, outcome_dir / f"{row.get('seq')}_{request_id}.json")
                wall_ms = (document.get("interpreted") or {}).get("wall_ms")
                if isinstance(wall_ms, (int, float)):
                    candidate_ms.append(float(wall_ms))
            if isinstance(row.get("wall_sec"), (int, float)):
                e_star_sec.append(float(row["wall_sec"]))

        tau = float(self.procedure["theta"]["timeout_s"])
        p99_candidate = percentile_nearest_rank(candidate_ms, 0.99)
        ceq_per_call = [int(row["ceq"]) for row in metered if isinstance(row.get("ceq"), int)]
        completions = [(row.get("usage") or {}).get("completion_tokens") for row in metered]
        return {
            "schema": "a0.a1.calibration.telemetry/v1",
            "arm": self.arm,
            "mode": self.mode,
            "not_used_for_selection": True,
            "discarded_sentence": "The pilot's algorithmic results are discarded.",
            "procedure_sha256": self.procedure_sha,
            "runner_sha256": sha256_file(Path(__file__).resolve()),
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "T_r_sec": (t1 - t0) / MICRO,
            "T_r_micros": t1 - t0,
            "T_r_started_epoch": t0 / MICRO,
            "T_r_ended_epoch": t1 / MICRO,
            "CEq_r": ceq_total,
            "N_E_r": attributed_evals,
            "N_E_r_ledger_rows": len(harness_rows),
            "meter_rows": len(meter_rows),
            "unmetered_rows": len(meter_rows) - len(metered),
            "units_completed": len(self.units_run),
            "units_per_pass": len(self.units),
            "workload_complete": self.stop_reason == "workload_complete",
            "stop_reason": self.stop_reason,
            "attribution": {
                "CEq_attributed_to_units": attributed_ceq,
                "CEq_total": ceq_total,
                "N_E_attributed_to_units": attributed_evals,
                "N_E_ledger_rows": len(harness_rows),
                "exhaustive": attributed_ceq == ceq_total
                and attributed_evals == len(harness_rows),
            },
            "per_unit": unit_rows,
            "variance": {
                "per_unit": {
                    "rates": {name: summary(values) for name, values in per_unit.items()},
                    "expected_per_unit": {
                        "model_calls": self.model_calls_per_unit,
                        "evals": self.evals_per_unit,
                        "loop_depth": self.loop_depth,
                    },
                },
                "per_window": windows,
            },
            "cost_sec": {
                "candidate_wall_ms": summary(candidate_ms),
                "e_star_wall_sec": summary(e_star_sec),
            },
            "ceq_per_call": {
                "values": ceq_per_call,
                "summary": summary([float(value) for value in ceq_per_call]),
                "completion_tokens": completions,
                "max_tokens_declared": self.max_tokens,
            },
            "tau_cross_check": {
                "tau_frozen_s": tau,
                "candidate_p99_ms": p99_candidate,
                "ten_times_p99_s": (10.0 * p99_candidate / 1000.0)
                if p99_candidate is not None else None,
                "floor_binds": ((10.0 * p99_candidate / 1000.0) < tau)
                if p99_candidate is not None else None,
                "note": "reported, never changed: the frozen tau is the gate workstream's",
            },
            "graphs": [{"graph_id": unit["graph_id"], "sha256": unit["graph_sha256"]}
                       for unit in self.units],
            "graph_shas_used": sorted({row.get("graph_sha256") for row in harness_rows}),
        }

    def _windows(self, meter_rows: List[dict], harness_rows: List[dict],
                 t0: int, t1: int) -> dict:
        window = 60.0
        span = (t1 - t0) / MICRO
        count = int(span // window)
        metered = [row for row in meter_rows if not row.get("unmetered")]
        out: Dict[str, Any] = {"window_sec": window, "windows_total": count,
                               "anchor_epoch": t0 / MICRO}
        for name in ("CEq", "N_E"):
            out[name] = {"full_windows": [], "full_rates": [], "partial": None}
        for index in range(count):
            lo = t0 / MICRO + index * window
            hi = lo + window
            ceq = sum(int(row["ceq"]) for row in metered
                      if isinstance(row.get("ceq"), int) and lo <= parse_ts(row["ts"]) < hi)
            ne = sum(1 for row in harness_rows if lo <= parse_ts(row["ts"]) < hi)
            out["CEq"]["full_windows"].append(ceq)
            out["CEq"]["full_rates"].append(60.0 * ceq / window)
            out["N_E"]["full_windows"].append(ne)
            out["N_E"]["full_rates"].append(60.0 * ne / window)
        tail_lo = t0 / MICRO + count * window
        if tail_lo < t1 / MICRO:
            ceq = sum(int(row["ceq"]) for row in metered
                      if isinstance(row.get("ceq"), int) and tail_lo <= parse_ts(row["ts"]))
            ne = sum(1 for row in harness_rows if tail_lo <= parse_ts(row["ts"]))
            out["CEq"]["partial"] = {"start_epoch": tail_lo,
                                     "span_sec": t1 / MICRO - tail_lo, "CEq": ceq}
            out["N_E"]["partial"] = {"start_epoch": tail_lo,
                                     "span_sec": t1 / MICRO - tail_lo, "N_E": ne}
        for name in ("CEq", "N_E"):
            rates = out[name]["full_rates"]
            out[name]["n_full"] = len(rates)
            out[name]["sum_full"] = sum(out[name]["full_windows"])
            out[name]["mean_full_rate"] = (sum(rates) / len(rates)) if rates else None
            out[name]["max_full_rate"] = max(rates) if rates else None
            out[name]["min_full_rate"] = min(rates) if rates else None
        return out

    # ---------------------------------------------------------------- #
    def _checks(self, report: dict) -> Dict[str, bool]:
        telemetry = report["telemetry"]
        probe = report.get("topology_probe") or {}
        meter_rows = report["ledger"]["meter_rows"]
        metered = [row for row in meter_rows if not row.get("unmetered")]
        harness_rows = report["ledger"]["harness_rows"]
        rederived = 0
        for row in metered:
            usage = row.get("usage") or {}
            miss = int(usage.get("prompt_cache_miss_tokens", -1))
            hit = int(usage.get("prompt_cache_hit_tokens", -1))
            completion = int(usage.get("completion_tokens", -1))
            if row.get("ceq") == miss + (hit * 2) // 100 + 4 * completion:
                rederived += 1
        graph_shas = {unit["graph_sha256"] for unit in self.units}
        return {
            "the_procedure_document_is_the_frozen_one": (
                report["procedure"]["document_sha256"] == sha256_file(PROC_MD)
            ),
            "the_topology_blocks_direct_egress": (
                probe.get("_negative_controls_blocked") is True
                and probe.get("_meter_reachable") is True
            ),
            "the_harness_identity_declares_ownership": bool(
                report["harness"]["identity"].get("owns_evaluation")
            ),
            "every_harness_row_names_a_workload_graph": (
                True if self.rehearsal
                else all(row.get("graph_sha256") in graph_shas for row in harness_rows)
            ),
            "no_unmetered_row_in_the_campaign": telemetry["unmetered_rows"] == 0,
            # The point of the whole exercise: an arm that never reaches the harness has
            # produced no rate, however green the other checks look.  This is not vacuous
            # in either mode — the rehearsal skips the *model* call, not the evaluations.
            "the_arm_reached_the_harness": bool(harness_rows),
            "every_metered_row_re_derives_its_ceq": (
                (bool(metered) and rederived == len(metered)) if meter_rows else self.rehearsal
            ),
            "the_meters_own_verifier_re_derives_the_ledger": (
                (report["ledger"]["meter_verify"] or {}).get("returncode") == 0
            ),
            "the_model_family_is_deepseek_flash": (
                all(row.get("model_reported") == MODEL for row in metered)
                if metered else self.rehearsal
            ),
            "unit_attribution_is_exhaustive": (
                telemetry["attribution"]["exhaustive"] or self.rehearsal
            ),
            "the_runner_is_the_committed_one": (
                report["runner"]["sha256"] == sha256_file(Path(__file__).resolve())
            ),
        }


# --------------------------------------------------------------------------- #
# the KAPSO arm, run inside the namespace
# --------------------------------------------------------------------------- #
def kapso_inner(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="pilot kapso-inner")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--rounds", type=int, required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--harness-root", required=True)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--meter-token", default=None)
    parser.add_argument("--no-model", action="store_true")
    args = parser.parse_args(argv)

    for path in (str(KAPSO_T1), str(KAPSO_DIR), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import runtime_t1
    import task as t1_task
    from a0_adapter.harness_manifest import class_triple

    out_dir = Path(args.out_dir).resolve()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    state_root = Path(args.state_root).resolve()
    graph = Path(args.graph).resolve()

    # The adapter's own `state_root` would write into the T1 workstream's directory;
    # the pilot rebases it into its own work tree.
    config = dataclasses.replace(runtime_t1.load_config(), state_root=state_root)
    runtime = runtime_t1.build_runtime(run_dir=run_dir, state_root=state_root, config=config)
    binding = runtime_t1.prepare(runtime)

    plan = runtime.seams["plan"]
    candidates = [c.candidate_id for c in runtime.candidates
                  if c.candidate_id != binding["baseline_candidate"]]
    for index in range(args.rounds):
        plan.push(candidates[index % len(candidates)], run_evaluation=True)

    model_calls: List[dict] = []
    original_next = plan.next_solution

    def ideation_with_a_real_model_call():
        if args.no_model:
            return original_next()
        prompt = (
            "You are the ideation phase of a search over max-cut heuristics for 128-node "
            "graphs. In one short paragraph, name one concrete change to a multi-start "
            "1-flip local search that you expect to raise the number of edges cut."
        )
        started = time.monotonic()
        result = chat_completion(
            base_url=args.base_url, api_key=os.environ["DEEPSEEK_API_KEY"], model=MODEL,
            messages=[{"role": "user", "content": prompt}], token=args.meter_token,
            max_tokens=args.max_tokens, timeout=MODEL_TIMEOUT,
        )
        latency = time.monotonic() - started
        body = result.get("body") or {}
        model_calls.append({"usage": body.get("usage") or {},
                            "model_reported": body.get("model"),
                            "latency_sec": latency})
        return original_next()

    plan.next_solution = ideation_with_a_real_model_call

    client = runtime_t1.harness_client(
        harness_root=Path(args.harness_root), campaign_id=args.campaign_id,
        arm_id=args.arm_id, seed=int(runtime.maintainer.subsample_seed),
        label_resolver=runtime_t1.plan_label_resolver(runtime),
    )
    client.identity()
    injector = runtime_t1.post_session_injector(
        runtime=runtime, client=client, graph_path=graph,
        resolver=runtime_t1.plan_resolver(runtime), run_id=f"calib-{args.campaign_id}",
    )
    injector.install()

    from kapso.execution.fidelity import FULL_PASSTHROUGH

    runtime.strategy.observe_fidelity(FULL_PASSTHROUGH)
    for _ in range(args.rounds):
        runtime.strategy.run(t1_task.T1_PROBLEM)

    nodes = list(runtime.strategy.node_history)
    state = {
        "schema": "a0.a1.calibration.kapso_unit/v1",
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "campaign_id": args.campaign_id,
        "arm_id": args.arm_id,
        "graph": {"path": str(graph), "sha256": sha256_file(graph)},
        "rounds": args.rounds,
        "eid_star": runtime.eid.eid_star,
        "eid_r": runtime.tree_record["manifest_fingerprint"],
        "registered_evaluator_id": runtime.registration.evaluator_id,
        "eid_r_matches_the_t1_tree_record": binding["eid_r_matches_the_t1_tree_record"],
        "granted_class": class_triple(runtime.strategy),
        "harness_calls": client.calls,
        "model_calls": model_calls,
        "model_call_skipped": bool(args.no_model),
        "nodes": [{"node_id": node.node_id, "evaluation_valid": node.evaluation_valid}
                  for node in nodes],
        "holdout_bytes_in_workspace": runtime.holdout_bytes_in_workspace,
    }
    write_json(run_dir / "unit_state.json", state)
    print(json.dumps({"harness_calls": client.calls, "nodes": len(nodes)}))
    return 0


# --------------------------------------------------------------------------- #
# publish: the reduction the procedure requires
# --------------------------------------------------------------------------- #
def publish(out_dir: Path, published_dir: Path) -> dict:
    out_dir = Path(out_dir).resolve()
    published = Path(published_dir).resolve()
    if published.exists():
        shutil.rmtree(published)
    index: Dict[str, Any] = {
        "schema": "a0.a1.calibration.published_index/v1",
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "reduction": {
            "why": ("the pilot's algorithmic results are not published (PILOT-PROCEDURE.md "
                    "§0/§8): the objective's value on a calibration graph must not be "
                    "available to a later reader who might tune the budget by it"),
            "harness_row_keys_removed": list(HARNESS_ROW_REDACT),
            "outcome_keys_removed": list(OUTCOME_REDACT),
            "kept": ["ts", "campaign_id", "arm_id", "candidate_source_sha256",
                     "graph_sha256", "status", "wall_sec", "interpreted.wall_ms"],
        },
        "files": {},
        "raw_sha256": {},
    }
    meter_rows_all: List[dict] = []
    for arm, short in SHORT.items():
        raw_report = out_dir / short / "pilot_arm.json"
        if not raw_report.is_file():
            continue
        report = json.loads(raw_report.read_text(encoding="utf-8"))
        target = published / short
        target.mkdir(parents=True, exist_ok=True)

        published_report = json.loads(json.dumps(report, default=str))
        published_report["units"] = [published_unit(unit) for unit in report["units"]]
        published_report["ledger"]["harness_rows"] = [
            reduce_harness_row(row) for row in report["ledger"]["harness_rows"]
        ]
        published_report["reduction"] = index["reduction"]
        index["raw_sha256"][f"{short}/harness_ledger.jsonl"] = report["ledger"][
            "harness_ledger_sha256"]
        index["raw_sha256"][f"{short}/meter_ledger.jsonl"] = report["ledger"][
            "meter_ledger_sha256"]
        index["files"][f"{short}/pilot_arm.json"] = write_json(
            target / "pilot_arm.json", published_report)

        meter_rows = report["ledger"]["meter_rows"]
        meter_rows_all.extend(meter_rows)
        # The published ledger is the campaign's own meter file, copied verbatim: a
        # re-serialized copy carries the keys in a different order, which the meter's
        # verifier pins (`a0/meter/verify_ledger.py`, `ROW_KEY_ORDER`) and rejects row by
        # row.  Fail loudly rather than publish a ledger the meter cannot re-derive.
        raw_meter = Path(report["ledger"]["meter_ledger"])
        if not raw_meter.is_file() or (sha256_file(raw_meter)
                                       != report["ledger"]["meter_ledger_sha256"]):
            raise PilotError(f"the campaign's meter ledger is not the recorded one: "
                             f"{raw_meter}")
        shutil.copyfile(raw_meter, target / "meter_ledger.jsonl")
        index["files"][f"{short}/meter_ledger.jsonl"] = sha256_file(target / "meter_ledger.jsonl")

        (target / "harness_ledger.jsonl").write_text(
            "".join(json.dumps(reduce_harness_row(row), sort_keys=True, separators=(",", ":"))
                    + "\n" for row in report["ledger"]["harness_rows"]), encoding="utf-8")
        index["files"][f"{short}/harness_ledger.jsonl"] = sha256_file(
            target / "harness_ledger.jsonl")

        outcomes = out_dir / short / "outcomes"
        if outcomes.is_dir():
            (target / "outcomes").mkdir(parents=True, exist_ok=True)
            for path in sorted(outcomes.glob("*.json")):
                document = json.loads(path.read_text(encoding="utf-8"))
                write_json(target / "outcomes" / path.name, reduce_outcome(document))
            index["files"][f"{short}/outcomes"] = {
                "count": len(list((target / "outcomes").glob("*.json"))),
                "note": "reduced: interpreted.wall_ms, status, graph_sha256 kept",
            }

    if len(meter_rows_all) > 1:
        meter_rows_all.sort(key=lambda row: row["ts"])
    (published / "ledger.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in meter_rows_all), encoding="utf-8")
    index["files"]["ledger.jsonl"] = sha256_file(published / "ledger.jsonl")

    for name in ("rehearsal.json", "BLOCKED.json", "meter-proof/meter_proof.json",
                 "unmetered/unmetered_counterexample.json"):
        source = out_dir / name
        if source.is_file():
            destination = published / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            index["files"][name] = sha256_file(destination)
    # the two probe campaigns' own ledgers, verbatim: the meter's verifier can re-derive
    # them, and they are where the real `ceq` row and the `unmetered` counter-example live.
    for name, ledger in (("meter-proof", out_dir / "meter-proof" / "meter" / "ledger.jsonl"),
                         ("unmetered", out_dir / "unmetered" / "meter" / "ledger.jsonl")):
        if ledger.is_file():
            destination = published / name / "meter_ledger.jsonl"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ledger, destination)
            index["files"][f"{name}/meter_ledger.jsonl"] = sha256_file(destination)
    write_json(published / "INDEX.json", index)
    return index


# --------------------------------------------------------------------------- #
# apply: f over the published evidence
# --------------------------------------------------------------------------- #
def load_published_telemetry(published: Path) -> Dict[str, dict]:
    """Re-derive the telemetry `f` consumes from the published evidence files."""
    published = Path(published).resolve()
    telemetry: Dict[str, dict] = {}
    for arm, short in SHORT.items():
        report_path = published / short / "pilot_arm.json"
        if not report_path.is_file():
            raise PilotError(f"no published pilot record for {arm} at {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("mode") != "pilot":
            raise PilotError(f"{report_path} is a {report.get('mode')!r} run; "
                             "f takes pilot telemetry only")
        entry = dict(report["telemetry"])
        meter_rows = read_rows(published / short / "meter_ledger.jsonl")
        harness_rows = read_rows(published / short / "harness_ledger.jsonl")
        metered = [row for row in meter_rows if not row.get("unmetered")]
        ceq = sum(int(row["ceq"]) for row in metered if isinstance(row.get("ceq"), int))
        entry["CEq_r_ledger"] = ceq
        entry["N_E_r_ledger"] = len(harness_rows)
        entry["unmetered_rows_ledger"] = len(meter_rows) - len(metered)
        entry["CEq_r_telemetry"] = int(entry["CEq_r"])
        entry["N_E_r_telemetry"] = int(entry["N_E_r"])
        entry["CEq_r"] = ceq
        entry["N_E_r"] = len(harness_rows)
        entry["ledger_agrees_with_telemetry"] = (
            ceq == entry["CEq_r_telemetry"] and len(harness_rows) == entry["N_E_r_telemetry"]
            and entry["unmetered_rows_ledger"] == int(entry["unmetered_rows"])
        )
        entry["models_reported"] = sorted({str(row.get("model_reported")) for row in metered})
        entry["harness_graph_shas"] = sorted({str(row.get("graph_sha256"))
                                              for row in harness_rows})
        entry["report"] = {
            "campaign_id": report["campaign_id"],
            "arm_id": report["arm_id"],
            "mode": report["mode"],
            "stop_reason": report["stop_reason"],
            "units_completed": report["telemetry"]["units_completed"],
            "workload_complete": report["telemetry"]["workload_complete"],
            "graphs": report["graphs"],
            "caps": report["caps"],
            "checks": report.get("checks", {}),
        }
        telemetry[arm] = entry
    return telemetry


def apply_b_hard(published: Path, procedure: Optional[Dict[str, Any]] = None) -> dict:
    procedure = procedure or load_procedure()
    telemetry = load_published_telemetry(published)
    failures = validity_failures(procedure, telemetry)
    per_arm = {arm: {key: value for key, value in entry.items()
                     if key not in ("report", "CEq_r_ledger", "N_E_r_ledger",
                                    "unmetered_rows_ledger", "CEq_r_telemetry",
                                    "N_E_r_telemetry", "ledger_agrees_with_telemetry")}
               for arm, entry in telemetry.items()}
    result = apply_f(per_arm, procedure)
    properties = check_f_properties(per_arm, procedure, result)
    diag = diagnostics(per_arm, procedure, result)
    payload: Dict[str, Any] = {
        "schema": "a0.a1.calibration.b_hard/v1",
        "frozen_on": procedure.get("frozen_on"),
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "procedure": {
            "document": "a0/a1/calibration/PILOT-PROCEDURE.md",
            "document_sha256": sha256_file(PROC_MD),
            "json": "a0/a1/calibration/pilot_procedure.json",
            "json_sha256": sha256_file(PROC_JSON),
        },
        "runner": {"path": "a0/a1/calibration/pilot.py",
                   "sha256": sha256_file(Path(__file__).resolve())},
        "manifest": {"path": "a0/tasks/maxcut/suite/manifest.json",
                     "sha256": sha256_file(MANIFEST)},
        "calibration_graphs": telemetry["A_simpleloop"]["report"]["graphs"],
        "campaigns": {arm: {"campaign_id": entry["report"]["campaign_id"],
                            "arm_id": entry["report"]["arm_id"],
                            "mode": entry["report"]["mode"],
                            "stop_reason": entry["report"]["stop_reason"],
                            "workload_complete": entry["report"]["workload_complete"],
                            "units_completed": entry["report"]["units_completed"],
                            "caps": entry["report"]["caps"]}
                      for arm, entry in sorted(telemetry.items())},
        "telemetry": {"per_arm": {
            arm: {
                "T_r_sec": entry["T_r_sec"],
                "T_r_micros": entry["T_r_micros"],
                "CEq_r": entry["CEq_r"],
                "N_E_r": entry["N_E_r"],
                "unmetered_rows": entry["unmetered_rows"],
                "units_completed": entry["units_completed"],
                "workload_complete": entry["workload_complete"],
                "stop_reason": entry["stop_reason"],
                "ledger_agrees_with_telemetry": entry["ledger_agrees_with_telemetry"],
                "variance": entry["variance"],
                "cost_sec": entry["cost_sec"],
                "ceq_per_call": entry["ceq_per_call"]["summary"],
                "completion_tokens": entry["ceq_per_call"]["completion_tokens"],
                "tau_cross_check": entry["tau_cross_check"],
                "attribution": entry["attribution"],
            }
            for arm, entry in sorted(telemetry.items())
        }},
        "validity": {"conditions": procedure["validity_conditions"],
                     "failures": failures, "all_hold": not failures},
        "mapping": {"name": "f", "result": result, "properties": properties},
        "vector": result["vector"],
        "diagnostics": diag,
        "scope_limits": [
            "resource rates only: B_hard bounds consumption, never quality",
            "the KAPSO rate is the rate of the arm's declared T1 configuration (the frozen "
            "C*(T1) implementation seam with one metered ideation call per round); a "
            "configuration with real implementation sessions would consume more per round",
            "the SimpleLoop rate is the rate of the adapter's declared deepseek lane with "
            "the adapter's default --model-max-tokens",
            "the calibration graphs are used for these rates only; no score on them was "
            "used, reported or published",
        ],
    }
    if failures:
        payload["refused"] = True
        payload["vector_note"] = (
            "REFUSED: this vector comes from a telemetry without a measured interval and "
            "is NOT a budget. It is recorded so the refusal's arithmetic is visible; the "
            "campaigns must not read it as B_hard."
        )
    else:
        payload["refused"] = False
    return payload


def validity_failures(procedure: Dict[str, Any], telemetry: Dict[str, dict]) -> List[str]:
    failures: List[str] = []
    if sha256_file(PROC_MD) != procedure["procedure"]["document_sha256"]:
        failures.append("V1: the procedure document does not hash to the frozen value")
    manifest_shas = {unit["graph_sha256"] for unit in calibration_units()}
    for arm, entry in sorted(telemetry.items()):
        report = entry["report"]
        if not entry.get("ledger_agrees_with_telemetry", True):
            failures.append(f"V3: {arm}: the published ledgers and the telemetry disagree")
        if int(entry.get("unmetered_rows_ledger", entry.get("unmetered_rows", 0))) > 0:
            failures.append(f"V3: {arm} has unmetered rows: the campaign's CEq is not "
                            "established")
        report_shas = {unit["sha256"] for unit in report["graphs"]}
        if report_shas != manifest_shas:
            failures.append(f"V2: {arm}'s graph set is not the current manifest's calibration set")
        if not (entry["T_r_micros"] > 0 and float(entry["T_r_sec"]) >= 120
                and int(entry["units_completed"]) >= 12):
            failures.append(
                f"V4: {arm} has no measured interval (T_r={entry['T_r_sec']}s, "
                f"units={entry['units_completed']})")
        models = set(entry.get("models_reported") or [])
        if models and models != {procedure["model"]["requested"]}:
            failures.append(f"V5: {arm} metered rows report models {sorted(models)}")
        harness_shas = set(entry.get("harness_graph_shas") or [])
        if not harness_shas or not harness_shas <= manifest_shas:
            failures.append(f"V6: {arm}'s harness evaluations are not all calibration graphs")
        if report["campaign_id"] != procedure["campaign_ids"][arm] or report["arm_id"] != arm:
            failures.append(f"V7: {arm} campaign/arm id mismatch")
    return failures


# --------------------------------------------------------------------------- #
# the metering proof: a real, tiny, in-namespace metered call
# --------------------------------------------------------------------------- #
def meter_proof(out_dir: Path, procedure_sha: str) -> dict:
    """Prove the pilot's own metering chain end to end, for the price of a few dozen CEq.

    Everything here is the pilot's own boundary — the same `MeterProxy` on the same kind
    of campaign port, the same `CampaignUplink` and `unshare -rn` namespace — with one
    real, tiny model call issued **from inside the namespace** over the unix socket.  It
    is deliberately not an arm: it exists so that a blocked pilot can still show a real
    `ceq` row, the proxy's own re-derivation, and a refusal that is booked rather than
    lost.  Its campaign id is its own; the pilot's totals stay clean.
    """
    root = Path(out_dir).resolve() / "meter-proof"
    root.mkdir(parents=True, exist_ok=True)
    campaign_id, arm_id = "C_calib_meter_proof", "A_calib_proof"
    meter = MeterProxy(campaign_id=campaign_id, arm_id=arm_id, work_dir=root / "meter")
    uplink = CampaignUplink(campaign_id=campaign_id, meter_port=meter.port)
    report: Dict[str, Any] = {
        "schema": "a0.a1.calibration.meter_proof/v1",
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "procedure_sha256": procedure_sha,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "campaign_id": campaign_id,
        "arm_id": arm_id,
        "why": ("the arms are blocked before their first session (see the blocker "
                "artifact); this proves the pilot's own metering chain — meter, namespace, "
                "unix-socket hop, one real upstream call — independently of them"),
        "model_requested": MODEL,
    }
    meter.start()
    try:
        uplink.start()
        report["meter"] = {"port": meter.port, "base_url": meter.base_url,
                           "ledger": str(meter.ledger), "token_issued": bool(meter.token)}
        script = (
            "import json, os, sys\n"
            "sys.path.insert(0, %r)\n"
            "from a0.a1.meter_runner import chat_completion\n"
            "result = chat_completion(base_url=%r, api_key=os.environ['DEEPSEEK_API_KEY'],\n"
            "    model=%r, messages=[{'role': 'user', 'content': 'reply with the single "
            "word ok'}],\n"
            "    token=%r, max_tokens=8, timeout=120)\n"
            "body = result.get('body') or {}\n"
            "print(json.dumps({'usage': body.get('usage'), 'model': body.get('model'),\n"
            "                  'status': result.get('status')}))\n"
        ) % (str(REPO_ROOT), meter.base_url, MODEL, meter.token or "")
        proc = subprocess.run(
            uplink.enter_command([sys.executable, "-c", script]), cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=240,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO_ROOT)])},
        )
        report["in_namespace_call"] = {
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-1500:],
            "stderr_tail": (proc.stderr or "")[-1500:],
        }
        report["direct_egress_from_inside_the_namespace"] = _direct_egress_probe(uplink)
    finally:
        uplink.stop()
        meter.stop()
    rows = read_rows(meter.ledger)
    report["ledger_rows"] = rows
    report["meter_verify"] = meter.verify_ledger()
    report["checks"] = {
        "the_call_was_made_from_inside_the_namespace": (
            report["in_namespace_call"]["exit_code"] == 0
        ),
        "the_topology_blocks_direct_egress": bool(
            report["direct_egress_from_inside_the_namespace"].get(
                "_negative_controls_blocked")
        ),
        "exactly_one_row_was_booked": len(rows) == 1,
        "the_row_carries_a_real_ceq": bool(
            rows and isinstance(rows[0].get("ceq"), int) and rows[0]["ceq"] > 0
            and rows[0].get("unmetered") is False
        ),
        "the_proxy_s_own_verifier_re_derives_it": (
            (report["meter_verify"] or {}).get("returncode") == 0
        ),
    }
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
    write_json(root / "meter_proof.json", report)
    return report


def _direct_egress_probe(uplink: CampaignUplink) -> dict:
    script = (
        "import json, socket\n"
        "report = {}\n"
        "for host in ('123.148.116.184', '1.1.1.1', '8.8.8.8'):\n"
        "    try:\n"
        "        socket.create_connection((host, 443), timeout=4).close()\n"
        "        report[host] = 'REACHED'\n"
        "    except OSError as exc:\n"
        "        report[host] = 'BLOCKED:' + type(exc).__name__\n"
        "print(json.dumps(report))\n"
    )
    proc = subprocess.run(
        uplink.enter_command([sys.executable, "-c", script]), cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )
    lines = [line for line in (proc.stdout or "").splitlines()
             if line.strip().startswith("{")]
    report = json.loads(lines[-1]) if lines else {"error": (proc.stderr or "")[-400:]}
    hosts = [key for key in ("123.148.116.184", "1.1.1.1", "8.8.8.8") if key in report]
    report["_negative_controls_blocked"] = bool(hosts) and all(
        str(report[key]).startswith("BLOCKED") for key in hosts
    )
    return report


# --------------------------------------------------------------------------- #
# the induced missing-usage counter-example
# --------------------------------------------------------------------------- #
def unmetered_probe(out_dir: Path, procedure_sha: str) -> dict:
    """A real response with no `usage` -> the `unmetered` row, and the enforcer's stop.

    Asking for a model that does not exist returns a 4xx carrying no `usage` field, which
    is exactly the gap `a0/meter/README.md` §2 puts in the unmetered bucket. A separate
    campaign id keeps it out of the pilot's totals.
    """
    root = Path(out_dir).resolve() / "unmetered"
    root.mkdir(parents=True, exist_ok=True)
    meter = MeterProxy(campaign_id="C_calib_unmetered_probe", arm_id="A_calib_probe",
                       work_dir=root / "meter")
    meter.start()
    report: Dict[str, Any] = {
        "schema": "a0.a1.calibration.unmetered_counterexample/v1",
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "procedure_sha256": procedure_sha,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "campaign_id": "C_calib_unmetered_probe",
        "why": ("a 4xx with no `usage` field is a *gap*: a call that reached the model "
                "whose usage was not observable. a0/meter books it `unmetered` with "
                "`ceq: null`, and a0/a1/budget.py stops the campaign rather than estimating"),
        "row": None,
    }
    try:
        try:
            chat_completion(
                base_url=meter.base_url,
                api_key=os.environ.get("DEEPSEEK_API_KEY", "not-a-key"),
                model="deepseek-does-not-exist-a0-calibration",
                messages=[{"role": "user", "content": "hi"}], token=meter.token,
                max_tokens=8, timeout=60,
            )
            report["response"] = "accepted (unexpected)"
        except Exception as exc:  # noqa: BLE001
            report["response"] = f"{type(exc).__name__}: {exc}"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not read_rows(meter.ledger):
            time.sleep(0.1)
        rows = read_rows(meter.ledger)
        report["row"] = rows[-1] if rows else None
        report["call_events"] = [event for event in meter.call_events()
                                 if event.get("kind") == "call"]
    finally:
        meter.stop()
    enforcer = BudgetEnforcer(
        budget=Budget(T_wall_sec=60.0, N_eval_max=10, CEq_max=1000),
        meter_ledger=meter.ledger, harness_eval_ledger=root / "no-harness-ledger.jsonl",
        campaign_id="C_calib_unmetered_probe", arm_id="A_calib_probe",
    )
    verdict = enforcer.check(label="induced-unmetered")
    report["budget_check"] = verdict
    report["checks"] = {
        "the_row_is_unmetered_with_a_null_ceq": bool(
            report["row"] and report["row"].get("unmetered") is True
            and report["row"].get("ceq") is None),
        "the_row_carries_a_reason": bool(report["row"] and report["row"].get("reason")),
        "the_enforcer_stops_the_campaign": verdict["stopped_because"]
        == "budget_exhausted:unmetered_model_call",
    }
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
    write_json(root / "unmetered_counterexample.json", report)
    return report


# --------------------------------------------------------------------------- #
# rehearsal
# --------------------------------------------------------------------------- #
def rehearsal(out_dir: Path) -> dict:
    procedure = load_procedure()
    procedure_sha = sha256_file(PROC_MD)
    units = rehearsal_units() * 2
    reports = {}
    identities = {}
    for arm in SHORT:
        campaign = PilotCampaign(arm=arm, out_dir=Path(out_dir) / "rehearsal",
                                 procedure=procedure, procedure_sha=procedure_sha,
                                 rehearsal=True, units=units, passes_max=1)
        report = campaign.run()
        identities[arm] = report["frozen_identity"]
        reports[arm] = {
            "arm": arm,
            "mode": "rehearsal",
            "not_used_for_selection": True,
            "discarded_sentence": "The pilot's algorithmic results are discarded.",
            "verdict": report["verdict"],
            "checks": report["checks"],
            "stop_reason": report["stop_reason"],
            "units_completed": report["telemetry"]["units_completed"],
            "N_E_r": report["telemetry"]["N_E_r"],
            "CEq_r": report["telemetry"]["CEq_r"],
            "unmetered_rows": report["telemetry"]["unmetered_rows"],
            "meter_rows": len(report["ledger"]["meter_rows"]),
            "harness_rows": [{"seq": row.get("seq"), "status": row.get("status"),
                              "graph_sha256": row.get("graph_sha256"),
                              "wall_sec": row.get("wall_sec")}
                             for row in report["ledger"]["harness_rows"]],
            "topology_probe": report["topology_probe"],
            "unit_refusals": [{"unit": unit["index"], "graph_id": unit["graph_id"],
                               "exit_code": unit["exit_code"],
                               "stderr_tail": unit["stderr_tail"]}
                              for unit in report["units"]],
            "arm_reached_the_harness": report["telemetry"]["N_E_r"] > 0,
        }
    payload = {
        "schema": "a0.a1.calibration.rehearsal/v1",
        "mode": "rehearsal",
        "not_used_for_selection": True,
        "discarded_sentence": "The pilot's algorithmic results are discarded.",
        "why": ("the same runner, the same closed topology, the same harness, on a dev "
                "graph with the model call skipped: plumbing only, zero spend, and never "
                "an input to f"),
        "procedure_sha256": procedure_sha,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "arms": reports,
        "frozen_identity": identities,
        "verdict": "pass" if all(r["verdict"] == "pass" for r in reports.values()) else "fail",
    }
    write_json(Path(out_dir).resolve() / "rehearsal.json", payload)
    return payload


# --------------------------------------------------------------------------- #
def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "kapso-inner":
        return kapso_inner(argv=argv[1:])
    parser = argparse.ArgumentParser(prog="a0.a1.calibration.pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze-check", help="verify the procedure freeze ordering")
    p_arm = sub.add_parser("arm", help="one bounded pilot campaign (paid)")
    p_arm.add_argument("--arm", required=True, choices=["simpleloop", "kapso"])
    p_arm.add_argument("--out-dir", required=True)
    p_all = sub.add_parser("all", help="both arms, one bounded campaign each (paid)")
    p_all.add_argument("--out-dir", required=True)
    p_reh = sub.add_parser("rehearsal", help="model-free plumbing rehearsal (free)")
    p_reh.add_argument("--out-dir", required=True)
    p_pub = sub.add_parser("publish", help="reduce the run into the published evidence")
    p_pub.add_argument("--out-dir", required=True)
    p_pub.add_argument("--published-dir", required=True)
    p_app = sub.add_parser("apply", help="apply f to the published evidence")
    p_app.add_argument("--out-dir", required=True)
    p_app.add_argument("--b-hard", default=None,
                       help="where to write B_hard.json (default: <out-dir>/B_hard.json)")
    p_un = sub.add_parser("unmetered", help="induce the unmetered counter-example")
    p_un.add_argument("--out-dir", required=True)
    p_proof = sub.add_parser("meter-proof", help="one real, tiny, in-namespace metered call")
    p_proof.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    if args.command == "freeze-check":
        procedure = load_procedure()
        units = calibration_units()
        print(json.dumps({
            "procedure_sha256": sha256_file(PROC_MD),
            "declared": procedure["procedure"]["document_sha256"],
            "calibration_graphs": [{"graph_id": unit["graph_id"], "sha256": unit["graph_sha256"]}
                                   for unit in units],
            "passes_max": procedure["graph_set"]["passes_max"],
            "caps": procedure["caps"],
            "verdict": "frozen and consistent",
        }, indent=1))
        return 0
    if args.command == "rehearsal":
        payload = rehearsal(Path(args.out_dir))
        print(json.dumps({"verdict": payload["verdict"],
                          "arms": {arm: {"verdict": r["verdict"],
                                         "units": r["units_completed"],
                                         "N_E": r["N_E_r"], "meter_rows": r["meter_rows"],
                                         "failed": [k for k, v in r["checks"].items() if not v]}
                                   for arm, r in payload["arms"].items()}}, indent=1))
        return 0 if payload["verdict"] == "pass" else 5
    if args.command in ("arm", "all"):
        procedure = load_procedure()
        procedure_sha = sha256_file(PROC_MD)
        identity = frozen_identity_status()
        shorts = list(SHORT) if args.command == "all" else [
            "A_simpleloop" if args.arm == "simpleloop" else "A_kapso"]
        out: Dict[str, Any] = {}
        for arm in shorts:
            campaign = PilotCampaign(arm=arm, out_dir=Path(args.out_dir),
                                     procedure=procedure, procedure_sha=procedure_sha)
            report = campaign.run()
            out[arm] = {"verdict": report["verdict"], "stop_reason": report["stop_reason"],
                        "units": report["telemetry"]["units_completed"],
                        "CEq_r": report["telemetry"]["CEq_r"],
                        "N_E_r": report["telemetry"]["N_E_r"],
                        "T_r_sec": report["telemetry"]["T_r_sec"],
                        "failed": [k for k, v in report["checks"].items() if not v],
                        "variance": report["telemetry"]["variance"]["per_unit"]["rates"]}
        blocked = None
        if not identity["consistent"] or all(
            data["N_E_r"] == 0 for data in out.values()
        ):
            blocked = {
                "schema": "a0.a1.calibration.blocked/v1",
                "not_used_for_selection": True,
                "discarded_sentence": "The pilot's algorithmic results are discarded.",
                "procedure_sha256": procedure_sha,
                "runner_sha256": sha256_file(Path(__file__).resolve()),
                "blocked": True,
                "reason": "the arms refuse at their frozen-identity precondition, so no "
                          "rate was measurable",
                "frozen_identity": identity,
                "arms": {arm: {"verdict": data["verdict"], "N_E_r": data["N_E_r"],
                               "CEq_r": data["CEq_r"], "units": data["units"],
                               "refusals": [{"unit": unit["index"],
                                             "exit_code": unit["exit_code"],
                                             "stderr_tail": unit["stderr_tail"]}
                                            for unit in json.loads(
                                                (Path(args.out_dir) / SHORT[arm]
                                                 / "pilot_arm.json").read_text(
                                                     encoding="utf-8"))["units"]]}
                         for arm, data in out.items()},
                "what_the_pilot_needs": identity.get("what_would_unblock_it"),
                "then_run": ("python3 a0/a1/calibration/pilot.py all --out-dir <dir> && "
                             "python3 a0/a1/calibration/pilot.py publish --out-dir <dir> "
                             "--published-dir <dir>/published && "
                             "python3 a0/a1/calibration/pilot.py apply --out-dir "
                             "<dir>/published"),
            }
            write_json(Path(args.out_dir) / "BLOCKED.json", blocked)
        print(json.dumps({"blocked": bool(blocked), "frozen_identity_consistent":
                          identity["consistent"], "arms": out}, indent=1))
        return 0 if not blocked else 6
    if args.command == "meter-proof":
        procedure = load_procedure()
        payload = meter_proof(Path(args.out_dir), sha256_file(PROC_MD))
        print(json.dumps({"verdict": payload["verdict"], "checks": payload["checks"],
                          "rows": payload["ledger_rows"],
                          "meter_verify": payload["meter_verify"]}, indent=1))
        return 0 if payload["verdict"] == "pass" else 5
    if args.command == "publish":
        index = publish(Path(args.out_dir), Path(args.published_dir))
        print(json.dumps({"files": index["files"], "raw_sha256": index["raw_sha256"]},
                         indent=1))
        return 0
    if args.command == "apply":
        payload = apply_b_hard(Path(args.out_dir))
        if args.b_hard:
            target = Path(args.b_hard)
        else:
            name = "B_hard_REFUSED.json" if payload["refused"] else "B_hard.json"
            target = Path(args.out_dir) / name
        write_json(target, payload)
        print(json.dumps({"refused": payload["refused"], "written": str(target),
                          "validity_failures": payload["validity"]["failures"],
                          "vector": payload["vector"],
                          "properties": payload["mapping"]["properties"],
                          "diagnostics": payload["diagnostics"]}, indent=1))
        return 0 if not payload["refused"] else 5
    if args.command == "unmetered":
        procedure = load_procedure()
        payload = unmetered_probe(Path(args.out_dir), sha256_file(PROC_MD))
        print(json.dumps({"verdict": payload["verdict"], "checks": payload["checks"],
                          "row": payload["row"]}, indent=1))
        return 0 if payload["verdict"] == "pass" else 5
    return 2


if __name__ == "__main__":
    sys.exit(main())
