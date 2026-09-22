#!/usr/bin/env python3
"""SimpleLoop wiring evidence: the runtime consumes, it does not measure.

Four runs, each recorded, each re-runnable from this one command:

1. **same bytes, same Outcome, same selection** — the same candidate bytes are
   handed to the harness twice (a replay run and its repeat) and the two runs'
   *consumed Outcomes* must be byte-identical and their selection identical.
   This is the determinism half of the claim.
2. **the harness lies, the runtime follows** — a second harness instance is given
   an override map that *inverts* the true ranking (the true-best candidate is
   handed 1, the true-worst is handed 9999). The runtime's champion must be the
   candidate the harness rewarded, and the harness's own ledger must record both
   the handed and the true number.
3. **no fallback** — the adapter is pointed at an ABI root with no identity at
   all. It must refuse to run rather than evaluate locally (adapter exit 3).
4. **fail-closed mid-run** — the identity exists, the service is then stopped,
   and the run must score nothing and exit 8 (never a locally invented number).

    python3 a0/a1/probes/wiring_simpleloop.py --out-dir /tmp/a1/wiring-simpleloop
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_DIR = REPO_ROOT / "a0" / "runtimes" / "simpleloop"
ADAPTER_PYTHON = ADAPTER_DIR / ".venv" / "bin" / "python"
E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"

GRAPH = "a0/tasks/maxcut/suite/dev/G_dev_0001.json"
CANDIDATE_SET = "a0/tasks/maxcut/candidates/manifest.json"
EID = "a0/a1/T1-EID.json"
EID_SPEC = "a0/a1/T1.contract.json"
POLICY = "a0/runtimes/simpleloop/policy/simpleloop.maxcut.policy.json"
E_STAR = "a0/tasks/maxcut/e_star.py"
BASELINE = "c02_ok_low_baseline"
THETA = "seed=1337,fidelity=none,fraction=none,timeout_s=10"

SOLVER_SCRIPT = {
    "schema": "a0.simpleloop.solver_script/v1",
    "proposals": [
        {"iteration": 0, "kind": "c_star_member", "candidate_id": BASELINE},
        {"iteration": 1, "kind": "c_star_member", "candidate_id": "c01_ok_high_pc",
         "as_candidate_id": "proposal_i1"},
        {"iteration": 2, "kind": "c_star_member", "candidate_id": "c03_ok_zero_all_one_side",
         "as_candidate_id": "proposal_i2"},
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(path: Path) -> bytes:
    """The two runs must agree on the *document*, not on its formatting."""
    return json.dumps(
        json.loads(Path(path).read_text(encoding="utf-8")),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")


class Service:
    def __init__(self, root: Path, campaign_id: str, arm_id: str, run_id: str,
                 override: Optional[dict] = None):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root.parent / f"{self.root.name}.stop"
        self.summary = self.root.parent / f"{self.root.name}.summary.json"
        command = [
            str(ADAPTER_PYTHON), str(E_SERVICE), "serve",
            "--root", str(self.root),
            "--evaluator", "maxcut",
            "--campaign-id", campaign_id,
            "--arm-id", arm_id,
            "--harness-run-id", run_id,
            "--stop-file", str(self.stop_file),
            "--summary-out", str(self.summary),
        ]
        if override is not None:
            override_path = self.root / "override.json"
            override_path.write_text(json.dumps(override, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
            command += ["--override", str(override_path)]
        self.command = command
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        if self.stop_file.exists():
            self.stop_file.unlink()
        log = (self.root / "service.log").open("wb")
        self.process = subprocess.Popen(self.command, cwd=str(REPO_ROOT),
                                        stdout=log, stderr=subprocess.STDOUT)
        identity = self.root / "harness_identity.json"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if identity.is_file():
                return
            if self.process.poll() is not None:
                raise SystemExit(f"harness service exited {self.process.returncode}")
            time.sleep(0.05)
        raise SystemExit("harness service did not write its identity")

    def stop(self) -> None:
        if self.process is None:
            return
        self.stop_file.write_text("stop\n", encoding="utf-8")
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def run_adapter(*, harness_root: Path, campaign_id: str, arm_id: str, run_dir: Path,
                graph: str = GRAPH, request_timeout_s: float = 600.0) -> dict:
    if run_dir.exists():
        shutil.rmtree(run_dir)
    command = [
        str(ADAPTER_PYTHON), "-m", "a0_adapter", "run",
        "--work-root", str(REPO_ROOT),
        "--runtime", "simpleloop",
        "--task", "maxcut",
        "--candidate-set", CANDIDATE_SET,
        "--eid", EID,
        "--eid-spec", EID_SPEC,
        "--eval-mode", "harness",
        "--harness-root", str(harness_root),
        "--harness-request-timeout-s", str(request_timeout_s),
        "--campaign-id", campaign_id,
        "--arm-id", arm_id,
        "--graph", graph,
        "--baseline-candidate", BASELINE,
        "--policy", POLICY,
        "--theta", THETA,
        "--e-star", E_STAR,
        "--solver", "injected",
        "--solver-script", str(run_dir.parent / "solver.json"),
        "--max-iterations", "3",
        "--run-dir", str(run_dir),
    ]
    proc = subprocess.run(command, cwd=str(ADAPTER_DIR), capture_output=True, text=True,
                          timeout=900)
    return {"command": command, "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


def responses_of(harness_root: Path) -> dict:
    out = {}
    for path in sorted((harness_root / "responses").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        out[path.stem] = document
    return out


def outcomes_digest(harness_root: Path) -> dict:
    """The consumed Outcomes, keyed by candidate, hashed canonically."""
    digest = {}
    for _name, document in responses_of(harness_root).items():
        outcome = document.get("outcome")
        if outcome is None:
            continue
        payload = json.dumps(outcome, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")
        digest[document["candidate_id"]] = hashlib.sha256(payload).hexdigest()
    return digest


def run_meta(run_dir: Path) -> dict:
    return json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="wiring_simpleloop")
    parser.add_argument("--out-dir", default="/tmp/a1/wiring-simpleloop")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "solver.json").write_text(json.dumps(SOLVER_SCRIPT, indent=1, sort_keys=True) + "\n",
                                        encoding="utf-8")

    report: dict = {
        "schema": "a0.a1.wiring_simpleloop/v1",
        "adapter": "a0/runtimes/simpleloop",
        "task": "maxcut-t1",
        "graph": GRAPH,
        "graph_sha256": sha256_file(REPO_ROOT / GRAPH),
        "config": {
            "eval_mode": "harness",
            "candidate_set": CANDIDATE_SET,
            "candidate_set_sha256": sha256_file(REPO_ROOT / CANDIDATE_SET),
            "eid": EID,
            "eid_sha256": sha256_file(REPO_ROOT / EID),
            "policy": POLICY,
            "theta": THETA,
        },
        "checks": {},
    }

    # -- 1. same bytes, same Outcome, same selection ----------------------
    honest = Service(out_dir / "harness-honest", "C_wiring_honest", "A_simpleloop", "wiring-honest")
    honest.start()
    try:
        first = run_adapter(harness_root=honest.root, campaign_id="C_wiring_honest",
                            arm_id="A_simpleloop", run_dir=out_dir / "run-honest-a")
        first_outcomes = outcomes_digest(honest.root)
        second = run_adapter(harness_root=honest.root, campaign_id="C_wiring_honest",
                             arm_id="A_simpleloop", run_dir=out_dir / "run-honest-b")
        second_outcomes = outcomes_digest(honest.root)
    finally:
        honest.stop()

    meta_a = run_meta(out_dir / "run-honest-a")
    meta_b = run_meta(out_dir / "run-honest-b")
    report["runs"] = {
        "honest_a": {"returncode": first["returncode"], "exit_code": meta_a["exit_code"],
                     "champion": meta_a["champion_id"], "champion_scalar": meta_a["champion_scalar"],
                     "history": [{k: row[k] for k in
                                  ("iteration", "candidate_id", "search_signal", "e_star_status")}
                                 for row in meta_a["history"]]},
        "honest_b": {"returncode": second["returncode"], "exit_code": meta_b["exit_code"],
                     "champion": meta_b["champion_id"], "champion_scalar": meta_b["champion_scalar"],
                     "history": [{k: row[k] for k in
                                  ("iteration", "candidate_id", "search_signal", "e_star_status")}
                                 for row in meta_b["history"]]},
    }
    report["checks"]["same_candidate_bytes_same_consumed_outcome"] = (
        first_outcomes == second_outcomes and bool(first_outcomes)
    )
    report["checks"]["same_consumed_outcome_same_selection"] = (
        meta_a["champion_id"] == meta_b["champion_id"]
        and meta_a["champion_scalar"] == meta_b["champion_scalar"]
        and [(r["candidate_id"], r["search_signal"]) for r in meta_a["history"]]
        == [(r["candidate_id"], r["search_signal"]) for r in meta_b["history"]]
    )
    report["outcome_digests"] = first_outcomes
    report["honest_ledger"] = [
        json.loads(line) for line in (honest.root / "ledger.jsonl").read_text().splitlines() if line
    ]
    report["checks"]["honest_ledger_true_equals_handed"] = all(
        row["true_value"] == row["handed_value"] and not row["override_applied"]
        for row in report["honest_ledger"]
    )

    # -- 2. the harness lies; the runtime follows -------------------------
    lying = Service(out_dir / "harness-lying", "C_wiring_lying", "A_simpleloop", "wiring-lying",
                    override={"proposal_i1": 1, "proposal_i2": 9999})
    lying.start()
    try:
        third = run_adapter(harness_root=lying.root, campaign_id="C_wiring_lying",
                            arm_id="A_simpleloop", run_dir=out_dir / "run-lying")
    finally:
        lying.stop()
    meta_c = run_meta(out_dir / "run-lying")
    lying_ledger = [
        json.loads(line) for line in (lying.root / "ledger.jsonl").read_text().splitlines() if line
    ]
    report["runs"]["lying"] = {
        "returncode": third["returncode"], "exit_code": meta_c["exit_code"],
        "champion": meta_c["champion_id"], "champion_scalar": meta_c["champion_scalar"],
        "history": [{k: row[k] for k in
                     ("iteration", "candidate_id", "search_signal", "e_star_status")}
                    for row in meta_c["history"]],
    }
    report["lying_ledger"] = lying_ledger
    true_by_candidate = {row["candidate_id"]: row["true_value"] for row in lying_ledger}
    handed_by_candidate = {row["candidate_id"]: row["handed_value"] for row in lying_ledger}
    # The lie must actually invert the true ranking, or the test proves nothing.
    report["truth_vs_handed"] = {
        "true_best": max(true_by_candidate, key=lambda k: true_by_candidate[k]),
        "handed_best": max(handed_by_candidate, key=lambda k: handed_by_candidate[k]),
        "true": true_by_candidate,
        "handed": handed_by_candidate,
    }
    report["checks"]["the_override_inverts_the_true_ranking"] = (
        report["truth_vs_handed"]["true_best"] != report["truth_vs_handed"]["handed_best"]
    )
    report["checks"]["runtime_selection_follows_the_harness_number"] = (
        meta_c["champion_id"] == f"proposal_i2"
        and meta_c["champion_scalar"] == 9999
        and meta_c["champion_id"] == report["truth_vs_handed"]["handed_best"]
        and meta_c["champion_id"] != report["truth_vs_handed"]["true_best"]
    )
    report["checks"]["the_score_of_record_is_the_harness_s_in_the_trace"] = all(
        "harness_supplied" in (line and json.loads(line).get("evaluator_evidence", {}).get("detail") or "")
        for line in (out_dir / "run-lying" / "traces" / "simpleloop.run-lying.score.jsonl")
        .read_text().splitlines()
        if line.strip()
    )

    # -- 3. no identity: refuse, do not evaluate locally -------------------
    empty_root = out_dir / "harness-absent"
    empty_root.mkdir(parents=True, exist_ok=True)
    fourth = run_adapter(harness_root=empty_root, campaign_id="C_wiring_absent",
                         arm_id="A_simpleloop", run_dir=out_dir / "run-absent")
    report["runs"]["absent"] = {"returncode": fourth["returncode"],
                                "stderr_tail": fourth["stderr"][-500:]}
    report["checks"]["absent_harness_refuses_instead_of_evaluating"] = (
        fourth["returncode"] == 3
        and "no harness identity" in fourth["stderr"]
        and not (out_dir / "run-absent" / "run_meta.json").exists()
    )

    # -- 4. identity present, service stopped mid-run: nothing is scored ---
    gone = Service(out_dir / "harness-gone", "C_wiring_gone", "A_simpleloop", "wiring-gone")
    gone.start()
    gone.stop()
    fifth = run_adapter(harness_root=gone.root, campaign_id="C_wiring_gone",
                        arm_id="A_simpleloop", run_dir=out_dir / "run-gone",
                        request_timeout_s=5.0)
    meta_e = run_meta(out_dir / "run-gone")
    report["runs"]["service_stopped"] = {
        "returncode": fifth["returncode"], "exit_code": meta_e["exit_code"],
        "champion": meta_e["champion_id"],
        "history": [{k: row[k] for k in
                     ("iteration", "candidate_id", "search_signal", "e_star_status",
                      "e_star_failure_kind")}
                    for row in meta_e["history"]],
    }
    report["checks"]["stopped_service_scores_nothing_and_exits_8"] = (
        meta_e["exit_code"] == 8
        and meta_e["champion_id"] is None
        and all(row["search_signal"] is None for row in meta_e["history"])
        and all(row["e_star_status"] == "error" for row in meta_e["history"])
        and all(row["e_star_failure_kind"] == "harness_outcome_missing"
                for row in meta_e["history"])
    )

    # -- trace-level evidence ---------------------------------------------
    merged = out_dir / "run-honest-a" / "traces" / "simpleloop.run-honest-a.all.jsonl"
    report["merged_stream_sha256"] = sha256_file(merged)
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"
    (out_dir / "wiring_simpleloop.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"],
                      "truth_vs_handed": report["truth_vs_handed"],
                      "champions": {name: run.get("champion") for name, run in report["runs"].items()},
                      "out": str(out_dir / "wiring_simpleloop.json")}, indent=1))
    return 0 if report["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
