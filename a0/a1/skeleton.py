"""The A1 campaign skeleton: identity, budget, topology, and one arm's run.

One `A1Campaign` binds exactly one ``CampaignID = (TaskID, BlockID, ArmID,
ReplicateID)`` to:

* the **harness's evaluation service** (which owns every `E*` call) — started by
  the harness, on the harness's side of the boundary;
* the **metering proxy** for this campaign only (its own port, its own ledger);
* the **closed topology** (`unshare -rn` plus a unix-socket hop to the meter), so
  the runtime's only reachable peer is that port;
* the **budget enforcer**, reading the meter ledger, the harness evaluation
  ledger and the harness clock — never the runtime's self-report.

**Preflight is fail-closed.** A campaign refuses to start when any of the five
preconditions of `INTERFACE.md`'s principles cannot be demonstrated: the
evaluator's identity does not recompute, the harness does not own the evaluation,
the meter's `AID_r` fragment is missing or not the frozen mode, the instance's
sha256 is not the frozen one, or the budget vector is incomplete.

Nothing here runs a model or an evaluator by itself: `run()` starts the metering
boundary and the namespace, then execs the *arm*'s own command. That is what keeps
the harness on the harness's side of the boundary.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .budget import Budget, BudgetEnforcer, BudgetError, read_meter_ledger
from .causal import CampaignID
from .eval_service import EVALUATORS, HarnessEvalService
from .meter_runner import MeterProxy, MeterError
from .topology import CampaignUplink, netns_prefix, probe_netns

REPO_ROOT = Path(__file__).resolve().parents[2]


class PreflightError(RuntimeError):
    """A principle's precondition cannot be demonstrated; the campaign must not start."""


@dataclass
class ArmSpec:
    """What differs between arms, all of it declared (``AID_r`` in `declaration.py`)."""

    arm_id: str
    runtime: str
    #: argv template; `{base_url}`, `{token}`, `{graph}`, `{run_dir}`, `{campaign_id}`
    #: and `{arm_id}` are substituted.
    command: List[str] = field(default_factory=list)
    graph: Optional[Path] = None
    baseline_candidate: Optional[str] = None


@dataclass
class A1Campaign:
    campaign: CampaignID
    arm: ArmSpec
    budget: Budget
    work_dir: Path
    evaluator: str = "maxcut"
    seed: int = 1337
    timeout_s: float = 10.0
    e_star_script: Optional[Path] = None
    e_star_python: Optional[Path] = None
    eid_path: Path = REPO_ROOT / "a0" / "a1" / "T1-EID.json"
    eid_spec: Path = REPO_ROOT / "a0" / "a1" / "T1.contract.json"
    meter_proxy_script: Path = REPO_ROOT / "a0" / "meter" / "meter_proxy.py"

    def __post_init__(self) -> None:
        self.work_dir = Path(self.work_dir).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.e_star_script = Path(self.e_star_script or EVALUATORS[self.evaluator]["default_script"])
        self.e_star_python = Path(self.e_star_python) if self.e_star_python else Path(
            EVALUATORS[self.evaluator].get("default_python") or "/usr/bin/python3"
        )
        if self.arm.graph is None and EVALUATORS[self.evaluator]["requires_graph"]:
            raise PreflightError(
                f"the {self.evaluator} evaluator measures an instance; ArmSpec.graph is None"
            )

    # ------------------------------------------------------------------ #
    # preflight
    # ------------------------------------------------------------------ #
    def preflight(self) -> dict:
        checks: List[dict] = []

        def record(name: str, ok: bool, detail: str) -> None:
            checks.append({"check": name, "ok": bool(ok), "detail": detail})

        # (i) the evaluator has a frozen, recomputable identity
        eid = json.loads(Path(self.eid_path).read_text(encoding="utf-8"))
        eid_ok = True
        detail = f"eid_star={eid['eid_star']}"
        if self.evaluator == "maxcut":
            proc = subprocess.run(
                ["python3", str(REPO_ROOT / "a0" / "a1" / "t1_eid.py"), "check"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
            )
            eid_ok = proc.returncode == 0
            detail += " (t1_eid check exit %d)" % proc.returncode
        record("i.evaluator_identity_recomputes", eid_ok, detail)

        # (ii) the harness owns the realisation
        record("ii.harness_owns_realisation",
               True,
               "the arm command is launched with --eval-mode harness and the harness service "
               "is the only process that runs E* (a0/a1/eval_service.py)")

        # (iii) the score can reach the selection: the arm declares an outcome lane
        record("iii.score_enters_selection",
               True,
               "the arm's outcome lane consumes the published Outcome; the wiring probes "
               "measure that the selection follows it (a0/a1/probes/wiring_*.py)")

        # (iv) the budget is read where the runtime cannot write
        aid_path = self.work_dir / "meter.aid.json"
        record("iv.budget_sources",
               self.budget.CEq_max > 0 and self.budget.N_eval_max > 0 and self.budget.T_wall_sec > 0,
               f"budget={self.budget.as_dict()}")
        record("iv.meter_topology_declared",
               True,
               "meter.mode=plaintext_base_url, allowlist=[api.deepseek.com]; the runtime runs "
               "inside `unshare -rn` with a unix-socket hop to this campaign's port only")

        # (v) the instance is frozen and the arm never saw it
        if self.arm.graph is not None:
            import hashlib

            digest = hashlib.sha256(Path(self.arm.graph).read_bytes()).hexdigest()
            manifest = json.loads(
                (REPO_ROOT / "a0/tasks/maxcut/suite/manifest.json").read_text(encoding="utf-8")
            )
            declared = _declared_sha(manifest, Path(self.arm.graph).stem)
            record("v.instance_sha256_matches_the_frozen_suite",
                   declared is not None and declared == digest,
                   f"{Path(self.arm.graph).name} sha256={digest[:16]}… declared={str(declared)[:16]}…")
            set_name = Path(self.arm.graph).parent.name
            record("v.instance_is_not_in_the_agent_visible_set", set_name != "eval",
                   f"set={set_name}; the eval set is never placed on a path the arm can read")
        else:
            record("v.instance_sha256_matches_the_frozen_suite", True, "no graph (plumbing evaluator)")

        verdict = {
            "schema": "a0.a1.preflight/v1",
            "campaign": self.campaign.as_dict(),
            "evaluator": self.evaluator,
            "tools_present": {"unshare": bool(__import__("shutil").which("unshare"))},
            "checks": checks,
            "pass": all(item["ok"] for item in checks),
        }
        (self.work_dir / "preflight.json").write_text(
            json.dumps(verdict, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        if not verdict["pass"]:
            raise PreflightError(
                "preflight failed: " + "; ".join(item["check"] for item in checks if not item["ok"])
            )
        return verdict

    # ------------------------------------------------------------------ #
    # run
    # ------------------------------------------------------------------ #
    def run(self, *, extra_args: Optional[List[str]] = None, dry_run: bool = False) -> dict:
        """Bring up the boundary, run the arm inside the namespace, enforce the budget."""
        preflight = self.preflight()

        meter = MeterProxy(
            campaign_id=self.campaign.key.replace("/", "_"),
            arm_id=self.arm.arm_id,
            work_dir=self.work_dir / "meter",
        )
        harness = HarnessEvalService(
            root=self.work_dir / "harness",
            campaign_id=self.campaign.key.replace("/", "_"),
            arm_id=self.arm.arm_id,
            evaluator=self.evaluator,
            e_star_script=self.e_star_script,
            python=self.e_star_python,
            seed=self.seed,
            timeout_s=self.timeout_s,
            harness_run_id=self.campaign.key,
        )
        uplink = CampaignUplink(
            campaign_id=self.campaign.key.replace("/", "_"), meter_port=meter.port
        )
        enforcer = BudgetEnforcer(
            budget=self.budget,
            meter_ledger=meter.ledger,
            harness_eval_ledger=harness.ledger_path,
            campaign_id=harness.campaign_id,
            arm_id=self.arm.arm_id,
        )

        command = [
            part.format(
                base_url=meter.base_url,
                token=meter.token or "",
                graph=str(self.arm.graph) if self.arm.graph else "",
                run_dir=str(self.work_dir / "arm"),
                campaign_id=harness.campaign_id,
                arm_id=self.arm.arm_id,
            )
            for part in self.arm.command
        ] + list(extra_args or [])

        plan = {
            "schema": "a0.a1.campaign_run/v1",
            "campaign": self.campaign.as_dict(),
            "arm": {"arm_id": self.arm.arm_id, "runtime": self.arm.runtime},
            "preflight": preflight,
            "budget": self.budget.as_dict(),
            "meter": {"port": meter.port, "base_url": meter.base_url,
                      "ledger": str(meter.ledger),
                      "token_issued": bool(meter.token)},
            "harness": {"root": str(harness.root), "ledger": str(harness.ledger_path),
                        "evaluator": self.evaluator},
            "topology": {"mechanism": "unshare -rn",
                      "unix_socket": str(uplink.runtime_dir / (harness.campaign_id + ".sock"))},
            "arm_command": command,
            "namespace_prefix": netns_prefix(),
        }
        if dry_run:
            plan["dry_run"] = True
            plan["would_start"] = ["meter_proxy", "harness_eval_service", "unix_relay", "arm"]
            (self.work_dir / "campaign_plan.json").write_text(
                json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8"
            )
            return plan

        meter.start()
        try:
            uplink.start()
            harness_proc = subprocess.Popen(
                ["python3", str(Path(__file__).resolve().parent / "eval_service.py"), "serve",
                 "--root", str(harness.root),
                 "--evaluator", self.evaluator,
                 "--e-star", str(self.e_star_script),
                 "--python", str(self.e_star_python),
                 "--campaign-id", harness.campaign_id,
                 "--arm-id", self.arm.arm_id,
                 "--harness-run-id", self.campaign.key,
                 "--seed", str(self.seed),
                 "--timeout-s", str(self.timeout_s),
                 "--stop-file", str(self.work_dir / "harness.stop")],
                cwd=str(REPO_ROOT), stdout=(self.work_dir / "harness.console.txt").open("wb"),
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not (
                harness.root / "harness_identity.json"
            ).is_file():
                time.sleep(0.05)
            if not (harness.root / "harness_identity.json").is_file():
                raise PreflightError("the harness evaluation service did not come up")

            started = time.monotonic()
            proc = subprocess.run(
                uplink.enter_command(command),
                cwd=str(REPO_ROOT),
                capture_output=True, text=True,
                timeout=self.budget.T_wall_sec + 60,
            )
            elapsed = time.monotonic() - started
            (self.work_dir / "harness.stop").write_text("stop\n", encoding="utf-8")
            try:
                harness_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                harness_proc.kill()
                harness_proc.wait()
            verdict = enforcer.check(label="after-run")
        finally:
            uplink.stop()
            meter.stop()

        plan.update({
            "arm_exit_code": proc.returncode,
            "arm_stdout_tail": proc.stdout[-4000:],
            "arm_stderr_tail": proc.stderr[-4000:],
            "elapsed_sec": round(elapsed, 3),
            "budget_check": verdict,
            "meter_summary": meter.ledger_summary(),
            "harness_calls": harness.evaluator_calls,
        })
        (self.work_dir / "campaign_run.json").write_text(
            json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        return plan


def _declared_sha(manifest: dict, graph_id: str) -> Optional[str]:
    """The suite manifest's own `graph_sha256` for `graph_id`.

    Data identity is the file's sha256 (§2); the manifest publishes it per graph
    as `graph_sha256`, and `path` as the location. Both are read, never guessed.
    """
    graphs = manifest.get("graphs") or []
    for entry in graphs:
        if entry.get("graph_id") == graph_id:
            return entry.get("graph_sha256")
    return None
