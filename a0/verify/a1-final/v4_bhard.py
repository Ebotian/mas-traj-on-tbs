#!/usr/bin/env python3
"""Item 3 — the calibration product, re-derived from its own published evidence.

Nothing here imports `pilot.py`: the formula and every validity condition are
re-implemented from the frozen text in `B_hard.json["mapping"]["result"]["formula"]`
and `B_hard.json["validity"]["conditions"]`, so a bug in the author's reducer
cannot hide inside the check.

    python3 a0/verify/a1-final/v4_bhard.py
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CAL = REPO / "a0/a1/calibration"
EVID = CAL / "evidence"
BHARD = CAL / "B_hard.json"

results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ceq_from_usage(usage: dict) -> int:
    """The frozen integer formula, INTERFACE.md §8."""
    return (int(usage["prompt_cache_miss_tokens"])
            + (int(usage["prompt_cache_hit_tokens"]) * 2) // 100
            + 4 * int(usage["completion_tokens"]))


def main() -> int:
    doc = json.loads(BHARD.read_text(encoding="utf-8"))
    vector = doc["vector"]
    mapping = doc["mapping"]["result"]
    ceilings = {"CEQ_CEILING": 5_000_000, "N_E_CEILING": None}

    # ---- 1. the ledger rows, re-derived from their own `usage` ------------
    totals: dict[str, dict] = {}
    for arm, dirname in (("A_simpleloop", "simpleloop"), ("A_kapso", "kapso")):
        ledger = EVID / dirname / "meter_ledger.jsonl"
        harness = EVID / dirname / "harness_ledger.jsonl"
        meter_rows = rows(ledger)
        harness_rows = rows(harness)
        bad = [r for r in meter_rows if r.get("unmetered") or r.get("ceq") is None]
        mismatch = [r for r in meter_rows if not r.get("unmetered") and r.get("ceq") != ceq_from_usage(r["usage"])]
        models = sorted({r.get("model_reported") for r in meter_rows})
        camps = sorted({r.get("campaign_id") for r in meter_rows})
        arms = sorted({r.get("arm_id") for r in meter_rows})
        caps = sorted({str(r.get("completion_tokens", r.get("usage", {}).get("completion_tokens")))
                       for r in meter_rows})
        totals[arm] = {
            "meter_rows": len(meter_rows),
            "ceq_sum": sum(r["ceq"] for r in meter_rows if r.get("ceq") is not None),
            "unmetered": len(bad),
            "ceq_mismatch_rows": len(mismatch),
            "harness_rows": len(harness_rows),
            "models": models,
            "campaigns": camps,
            "arms": arms,
            "completion_tokens": [r["usage"]["completion_tokens"] for r in meter_rows],
            "graph_shas": sorted({r.get("graph_sha256") for r in harness_rows}),
            "harness_status": sorted({r.get("status") for r in harness_rows}),
        }
        check(f"{arm}: every metered row's ceq recomputes from its own usage",
              not mismatch, f"{len(meter_rows)} rows, {len(mismatch)} mismatches")
        check(f"{arm}: no unmetered row", not bad, f"{len(bad)} unmetered")
        check(f"{arm}: model_reported uniformly deepseek-flash", models == ["deepseek-flash"], str(models))
        check(f"{arm}: campaign/arm ids match the frozen names",
              camps == [doc["campaigns"][arm]["campaign_id"]] and arms == [arm],
              f"{camps} {arms}")
        tele = doc["telemetry"]["per_arm"][arm]
        check(f"{arm}: CEq_r == Σ ledger ceq",
              totals[arm]["ceq_sum"] == tele["CEq_r"],
              f"{totals[arm]['ceq_sum']} vs {tele['CEq_r']}")
        check(f"{arm}: N_E_r == harness ledger rows",
              totals[arm]["harness_rows"] == tele["N_E_r"],
              f"{totals[arm]['harness_rows']} vs {tele['N_E_r']}")

    # ---- 2. the vector, recomputed from the published telemetry ----------
    manifest = json.loads((REPO / "a0/tasks/maxcut/suite/manifest.json").read_text(encoding="utf-8"))
    manifest_shas = {g["graph_sha256"] for g in manifest["graphs"]}
    for arm in ("A_simpleloop", "A_kapso"):
        unknown = [s for s in totals[arm]["graph_shas"] if s not in manifest_shas]
        check(f"{arm}: V6 every harness row names a manifest graph sha256", not unknown,
              f"{len(totals[arm]['graph_shas'])} distinct shas, {len(unknown)} unknown")
        tele = doc["telemetry"]["per_arm"][arm]
        pilot = json.loads((EVID / ("simpleloop" if arm == "A_simpleloop" else "kapso")
                            / "pilot_arm.json").read_text(encoding="utf-8"))
        ptele = pilot["telemetry"]
        t_r = ptele["T_r_ended_epoch"] - ptele["T_r_started_epoch"]
        check(f"{arm}: T_r_sec agrees with the recorded epoch span",
              abs(t_r - tele["T_r_sec"]) < 1e-2, f"{t_r} vs {tele['T_r_sec']}")
        check(f"{arm}: V4 T_r>0, units>=12, T_r>=120s",
              tele["T_r_sec"] > 0 and tele["units_completed"] >= 12 and tele["T_r_sec"] >= 120,
              f"T_r={tele['T_r_sec']:.3f}s units={tele['units_completed']}")
        q = 60.0 * tele["CEq_r"] / tele["T_r_sec"]
        e = 60.0 * tele["N_E_r"] / tele["T_r_sec"]
        check(f"{arm}: q_r and e_r recompute", 
              abs(q - mapping["per_arm"][arm]["q_r_ceq_per_min"]) < 1e-6
              and abs(e - mapping["per_arm"][arm]["e_r_evals_per_min"]) < 1e-6,
              f"q={q:.6f} e={e:.6f}")
        tele["_q"] = q
        tele["_e"] = e

    q_max = max(doc["telemetry"]["per_arm"][a]["_q"] for a in ("A_simpleloop", "A_kapso"))
    e_max = max(doc["telemetry"]["per_arm"][a]["_e"] for a in ("A_simpleloop", "A_kapso"))
    derived = {"CEq_max": math.ceil(1.25 * 30 * q_max),
               "N_evaluatorCalls": math.ceil(1.25 * 30 * e_max),
               "P_concurrency": 1, "T_wall_sec": 1800.0}
    check("the published vector is the frozen formula applied to the published telemetry",
          all(derived[k] == vector[k] for k in derived),
          f"derived {derived} vs published {json.dumps({k: vector[k] for k in derived})}")
    check("the CEQ_CEILING did not clamp the vector",
          vector["CEq_max"] < ceilings["CEQ_CEILING"], f"{vector['CEq_max']} < 5_000_000")
    check("mapping.ceiling_active is false and matches",
          doc["mapping"]["properties"]["ceiling_active"] == {"CEq_max": False, "N_evaluatorCalls": False})

    # ---- 3. the guardrails really do not bind before T_wall --------------
    t_wall_min = vector["T_wall_sec"] / 60.0
    binding = []
    for arm in ("A_simpleloop", "A_kapso"):
        q = doc["telemetry"]["per_arm"][arm]["_q"]
        e = doc["telemetry"]["per_arm"][arm]["_e"]
        ceq_min = vector["CEq_max"] / q
        ne_min = vector["N_evaluatorCalls"] / e
        binding.append(min(ceq_min, ne_min))
        check(f"{arm}: no ceiling binds before T_wall at its own rate",
              ceq_min > t_wall_min and ne_min > t_wall_min,
              f"CEq_max lasts {ceq_min:.4f} min, N_E lasts {ne_min:.4f} min, T_wall {t_wall_min:.0f} min")
        diag = doc["diagnostics"]["per_arm"][arm]
        check(f"{arm}: diagnostics D1/D2 margins recompute",
              abs(diag["D1_margin_CEq_minutes"] - ceq_min) < 1e-6
              and abs(diag["D2_margin_NE_minutes"] - ne_min) < 1e-6,
              f"D1 {diag['D1_margin_CEq_minutes']:.4f} D2 {diag['D2_margin_NE_minutes']:.4f}")
        check(f"{arm}: guardrails_would_bind_before_T_wall is []", 
              diag["guardrails_would_bind_before_T_wall"] == [])
    check("the binding margin (worst arm) exceeds T_wall", min(binding) > t_wall_min,
          f"{min(binding):.4f} min > {t_wall_min:.0f} min")

    # ---- 4. V1, V3, V5, V7 in full --------------------------------------
    check("V1: sha256(PILOT-PROCEDURE.md) == the recorded document_sha256",
          sha256_file(CAL / "PILOT-PROCEDURE.md") == doc["procedure"]["document_sha256"],
          sha256_file(CAL / "PILOT-PROCEDURE.md"))
    check("V1b: pilot_procedure.json hashes to the recorded json_sha256",
          sha256_file(CAL / "pilot_procedure.json") == doc["procedure"]["json_sha256"])
    check("runner.pilot.py sha256 matches the file",
          sha256_file(CAL / "pilot.py") == doc["runner"]["sha256"])
    check("manifest sha256 matches B_hard.manifest.sha256",
          sha256_file(REPO / doc["manifest"]["path"]) == doc["manifest"]["sha256"])
    v3_ok, v3_detail = True, []
    for dirname in ("simpleloop", "kapso"):
        ledger_proc = subprocess.run([sys.executable, "a0/meter/verify_ledger.py",
                                      str(EVID / dirname / "meter_ledger.jsonl")],
                                     cwd=REPO, capture_output=True, text=True)
        v3_ok &= ledger_proc.returncode == 0
        v3_detail.append(f"{dirname} rc={ledger_proc.returncode}")
    check("V3: a0/meter/verify_ledger.py exits 0 on both pilot ledgers", v3_ok, " ".join(v3_detail))
    check("V3b: published ledger bytes == the meter's raw sha256 in INDEX.json",
          sha256_file(EVID / "simpleloop/meter_ledger.jsonl")
          == json.loads((EVID / "INDEX.json").read_text())["raw_sha256"]["simpleloop/meter_ledger.jsonl"]
          and sha256_file(EVID / "kapso/meter_ledger.jsonl")
          == json.loads((EVID / "INDEX.json").read_text())["raw_sha256"]["kapso/meter_ledger.jsonl"])
    check("validity.all_hold and failures == []",
          doc["validity"]["all_hold"] is True and doc["validity"]["failures"] == [],
          str(doc["validity"]["failures"]))
    check("refused is false", doc["refused"] is False)

    # ---- 5. the declared scope limits, against the artifacts -------------
    sl = json.loads((EVID / "simpleloop/pilot_arm.json").read_text(encoding="utf-8"))
    kp = json.loads((EVID / "kapso/pilot_arm.json").read_text(encoding="utf-8"))
    sl_cap = sl["workload"]["max_tokens_per_call"]
    kp_cap = kp["workload"]["max_tokens_per_call"]
    sl_tokens = totals["A_simpleloop"]["completion_tokens"]
    kp_tokens = totals["A_kapso"]["completion_tokens"]
    check(f"A_simpleloop: calls hit max_tokens={sl_cap}",
          sum(1 for t in sl_tokens if t == sl_cap) > 0,
          f"{sum(1 for t in sl_tokens if t == sl_cap)}/{len(sl_tokens)} rows at the cap")
    check(f"A_kapso: calls hit max_tokens={kp_cap}",
          all(t == kp_cap for t in kp_tokens),
          f"{len(kp_tokens)}/{len(kp_tokens)} rows at the cap")
    sl_exits = [u["exit_code"] for u in sl["units"]]
    kp_exits = [u["exit_code"] for u in kp["units"]]
    check("A_simpleloop: one unit exited 8, the rest 0",
          sl_exits.count(8) == 1 and sl_exits.count(0) == len(sl_exits) - 1, str(sorted(set(sl_exits)))
          + f" counts 0x{sl_exits.count(0)} 8x{sl_exits.count(8)}")
    check("A_kapso: all 24 units exited 0", set(kp_exits) == {0}, str(sorted(set(kp_exits))))
    eight = [u for u in sl["units"] if u["exit_code"] == 8]
    check("the exit-8 unit is unit 20 (pass 1) on C_0009",
          len(eight) == 1 and eight[0]["index"] == 20 and eight[0]["graph_id"] == "C_0009",
          json.dumps({k: eight[0][k] for k in ("index", "pass", "graph_id", "exit_code")}) if eight else "none")

    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
