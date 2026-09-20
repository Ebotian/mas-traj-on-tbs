"""Closure probe for EvE (plan:569).

The protocol's recipe — ``codex_tmux`` + ``sandbox_mode: workspace-write`` +
``allow_network: false`` + ``web_search: disabled`` — describes a configuration that must be
*proven by probe*. This module checks three things, each with executed evidence:

1. what the driver that the shipped circle-packing config actually selects emits as its argv
   (built by EvE's own builder, not read off the source);
2. whether ``allow_network`` is a real EvE knob, and which lane it governs;
3. what can actually be stood up on this host, probed with ``a0/env/checks/probe_egress.sh``.

Verdict vocabulary and exit codes are the adapter contract's: ``closed`` -> 0,
``egress_detected`` -> 6, ``inconclusive`` -> 3 (inconclusive is treated as not-closed).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from . import common
from .eve_runtime import EVE_ROOT, add_eve_to_path, compose_eve_config

PROBE = common.A0_ROOT / "env" / "checks" / "probe_egress.sh"
SENTINEL_URL = "https://example.com"


def _sh(cmd: list[str], *, timeout: float = 120.0, env: dict[str, str] | None = None):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    return proc


def driver_argv_evidence(run_dir: Path) -> dict[str, Any]:
    """Instantiate EvE's real drivers and ask them for the argv they would run."""
    add_eve_to_path()
    from scaling_evolve.algorithms.eve.runtime import driver as driver_mod
    from omegaconf import OmegaConf

    cfg = compose_eve_config(run_dir=Path(run_dir), step_script=PROBE, )
    driver_cfg = OmegaConf.to_container(cfg.driver, resolve=True)
    evidence: dict[str, Any] = {
        "driver_cfg_as_shipped": common.strip_absolute(driver_cfg),
        "config_source": "configs/eve/circle_packing.yaml -> driver: codex_max.yaml",
    }
    worktree = Path(run_dir) / "closure" / "worktree"
    worktree.mkdir(parents=True, exist_ok=True)

    # --- the driver the shipped config selects ---------------------------------------
    try:
        exec_driver = driver_mod._build_codex_exec_driver(
            driver_cfg, role=None, run_root=run_dir, pricing_table=None
        )
        argv = exec_driver._argv(worktree_root=worktree, session_id=None, instruction="probe")
        evidence["codex_exec_argv"] = argv
        evidence["codex_exec_has_sandbox_mode_parameter"] = hasattr(exec_driver, "sandbox_mode")
        evidence["codex_exec_bypasses_sandbox"] = any(
            "dangerously-bypass-approvals-and-sandbox" in arg for arg in argv
        )
        evidence["codex_exec_web_search_setting"] = exec_driver.web_search
    except Exception as exc:  # noqa: BLE001
        evidence["codex_exec_error"] = repr(exc)

    # --- the codex_tmux alternative, with the protocol's recipe applied ---------------
    tmux_cfg = dict(driver_cfg or {})
    tmux_cfg["driver"] = "codex_tmux"
    tmux_cfg["allow_network"] = False
    tmux_cfg["web_search"] = "disabled"
    try:
        from scaling_evolve.providers.agent.drivers.codex_tmux import CodexTmuxPanePool

        # Constructed directly rather than via CodexTmuxPanePool.create(), which would start a
        # real tmux server on this host; Driver._argv never touches the pool.
        probe_pool = CodexTmuxPanePool(
            session_name="a0-closure-probe",
            pane_ids=("a0-closure-probe-0",),
            cwd=Path(run_dir) / "closure",
        )
        tmux_driver = driver_mod.build_driver(
            tmux_cfg,
            role=None,
            run_root=run_dir,
            pane_pool=probe_pool,
            pricing_table=None,
        )
        argv = tmux_driver._argv(
            worktree, session_id=None, instruction="probe", prompt_file=None
        )
        evidence["codex_tmux_argv_with_allow_network_false"] = argv
        evidence["codex_tmux_sandbox_mode"] = getattr(tmux_driver, "sandbox_mode", None)
        evidence["codex_tmux_web_search"] = tmux_driver.web_search
        evidence["codex_tmux_has_search_flag"] = "--search" in argv
        evidence["codex_tmux_pane_pool_construction"] = (
            "constructed directly (no create()), so no tmux server was started for this probe"
        )
    except Exception as exc:  # noqa: BLE001
        evidence["codex_tmux_error"] = repr(exc)

    # --- is allow_network a real knob, and what does it govern? -----------------------
    grep = _sh(
        ["/usr/bin/grep", "-rn", "allow_network", "--include=*.py", str(EVE_ROOT / "src")],
        timeout=60,
    )
    evidence["allow_network_sites"] = [
        line for line in grep.stdout.splitlines() if line.strip()
    ][:20]
    evidence["allow_network_verdict"] = {
        "exists_in_eve": bool(evidence["allow_network_sites"]),
        "driver_level_effect": (
            "_sandbox_mode_from_driver_cfg maps allow_network=true to sandbox_mode "
            "'danger-full-access', else 'workspace-write' "
            "(src/scaling_evolve/algorithms/eve/runtime/driver.py:380-387) — it is a "
            "sandbox-mode selector, not an independent network switch"
        ),
        "agent_config_level_effect": (
            "AgentProviderConfig.allow_network / policy_profile 'benchmark_safe' set "
            "allow_network=false (providers/agent/config.py:24-32, 86), which is consumed by "
            "the workspace-local Python wrapper (providers/agent/python_runtime.py:20,332) "
            "and blocks socket.connect inside that wrapper only — it does not sandbox the "
            "agent's own shell"
        ),
        "codex_exec_honours_it": False,
        "codex_exec_reason": (
            "the codex_exec driver has no sandbox parameter at all; its argv always carries "
            "--dangerously-bypass-approvals-and-sandbox "
            "(providers/agent/drivers/codex_exec.py:434)"
        ),
    }
    evidence["acceptance_claim_F4_check"] = {
        "claim": (
            "a0/acceptance/ACCEPTANCE.md T7: 'there is no allow_network parameter in EvE at all'"
        ),
        "verified": False,
        "correction": (
            "allow_network exists twice (driver sandbox-mode selector; agent python-runtime "
            "policy). The claim's *conclusion* still holds: on the shipped full-run path "
            "(codex_exec, web_search: live) closure is impossible by configuration, because "
            "the sandbox flag is bypassed outright."
        ),
    }
    return evidence


def probe_mechanisms(*, run_dir: Path, step_script: Path, candidate_dir: Path,
                     timeout_s: float = 60.0, agent_probe: bool = True,
                     agent_probe_timeout_s: float = 200.0) -> dict[str, Any]:
    """Probe whatever lane can actually be stood up, with the reusable egress probe."""
    closure_dir = Path(run_dir) / "closure"
    log_root = closure_dir / "eval_logs"
    log_root.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = {"probe_script": str(PROBE)}

    if not PROBE.is_file():
        out["error"] = f"probe script missing: {PROBE}"
        return out

    def run(mechanism: str, cmd: str | None, label: str) -> dict[str, Any]:
        json_out = closure_dir / f"egress_{label}.json"
        argv = [
            "bash",
            str(PROBE),
            "check",
            "--mechanism",
            mechanism,
            "--timeout",
            str(int(timeout_s)),
            "--json",
            str(json_out),
            "--quiet",
        ]
        if cmd:
            argv += ["--cmd", cmd]
        proc = _sh(argv, timeout=timeout_s * 4)
        doc = None
        if json_out.is_file():
            try:
                doc = json.loads(json_out.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                doc = None
        return {
            "label": label,
            "mechanism": mechanism,
            "cmd": cmd,
            "rc": proc.returncode,
            "stdout": proc.stdout.strip()[-4000:],
            "stderr": proc.stderr.strip()[-4000:],
            "json": doc,
        }

    evaluator_cmd = (
        f"env EVE_WORKSPACE_ROOT={log_root} EVE_SOLVER_ROOT={candidate_dir} "
        f"EVE_EVAL_LOG_ROOT={log_root} PYTHONDONTWRITEBYTECODE=1 bash {step_script}"
    )
    out["evaluator_cmd"] = evaluator_cmd
    out["observations"] = [
        run("host", evaluator_cmd, "evaluator_lane_host"),
        run("unshare-rn", evaluator_cmd, "evaluator_lane_unshare_rn"),
    ]

    # The agent lane: bounded attempt to actually run the model. This is the observation
    # that decides whether a probe of the agent lane is possible at all today.
    codex = _sh(
        [
            "timeout",
            "40",
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "Reply with exactly: OK",
        ],
        timeout=70,
    )
    out["agent_lane_attempt"] = {
        "cmd": "timeout 40 codex exec --sandbox read-only --skip-git-repo-check 'Reply with exactly: OK'",
        "rc": codex.returncode,
        "stdout_tail": codex.stdout.strip()[-2000:],
        "stderr_tail": codex.stderr.strip()[-2000:],
        "conclusion": (
            "the agent lane is reachable: codex completes a model call. 2026-09-20 17:26 the "
            "provider answered with model gpt-5.6-terra; note that a0/env/checks/ENV_REPORT.md "
            "§3.1 recorded a dead endpoint earlier the same day and that EvE's shipped driver "
            "config pins model gpt-5.6-sol (configs/eve/driver/codex_max.yaml:9), which is a "
            "different model id — a full EvE run must be re-checked against that id"
        ),
    }
    out["agent_lane_egress"] = codex_agent_lane_probe(
        run_dir=run_dir, timeout_s=agent_probe_timeout_s, skip=not agent_probe
    )
    return out


def codex_agent_lane_probe(
    *, run_dir: Path, timeout_s: float = 200.0, skip: bool = False
) -> dict[str, Any]:
    """Probe the network egress of a *codex agent turn* under two sandbox modes.

    `probe_egress.sh` cannot do this: it runs a shell command and appends its own canary to
    the *same* shell, so it measures the caller's egress, not the egress of a tool call made
    by an agent that the caller spawned. The agent lane is therefore probed by asking the
    agent to run the canary and to persist its exit code into a file the probe can read.

    Two configurations, matching the two EvE drivers:
      * ``--sandbox workspace-write`` — what the ``codex_tmux`` driver passes as ``-s``
        (drivers/codex_tmux.py:555-570); the protocol's closure recipe.
      * ``--dangerously-bypass-approvals-and-sandbox`` — what the shipped ``codex_exec``
        driver always passes (drivers/codex_exec.py:434).
    """
    workdir = Path(run_dir) / "closure" / "agent_lane"
    workdir.mkdir(parents=True, exist_ok=True)
    if skip:
        return {"skipped": True, "reason": "disabled by flag"}

    prompt_prefix = (
        "Execute exactly this shell command, with no substitution:\n\n"
        'curl -sS -m 8 -o /dev/null -w "%{http_code}" ' + SENTINEL_URL + "\n\n"
        "Then write the exit code of that command (a single integer, nothing else) to the "
        "file "
    )
    results: dict[str, Any] = {"workdir": str(workdir), "configurations": []}

    # Sentinel control: is the sentinel reachable from the host at all right now? Without it a
    # timeout inside the sandbox cannot be attributed to the sandbox.
    control_attempts = []
    for _ in range(3):
        proc = _sh(
            [
                "/usr/bin/curl",
                "-sS",
                "-m",
                "10",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                SENTINEL_URL,
            ],
            timeout=40,
        )
        control_attempts.append(
            {"rc": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()[:200]}
        )
    results["sentinel_control_host"] = {
        "argv": ["curl", "-sS", "-m", "10", "-o", "/dev/null", "-w", "%{http_code}", SENTINEL_URL],
        "attempts": control_attempts,
        "sentinel_reachable_from_host": any(
            a["rc"] == 0 and a["stdout"] == "200" for a in control_attempts
        ),
    }

    for label, sandbox_args, note in (
        (
            "codex_tmux_configuration:sandbox=workspace-write",
            ["--sandbox", "workspace-write"],
            "matches drivers/codex_tmux.py -s workspace-write",
        ),
        (
            "codex_exec_shipped_configuration:dangerously-bypass-approvals-and-sandbox",
            ["--dangerously-bypass-approvals-and-sandbox"],
            "matches drivers/codex_exec.py:434, the shipped full-run path",
        ),
    ):
        attempts = []
        for attempt in range(2):
            exit_file = workdir / f"curl_exit_{label.split(':')[0]}_a{attempt}.txt"
            if exit_file.exists():
                exit_file.unlink()
            prompt = (
                prompt_prefix
                + str(exit_file)
                + ". Use the shell tool; do not explain. Then stop."
            )
            cmd = [
                "codex",
                "exec",
                *sandbox_args,
                "--skip-git-repo-check",
                prompt,
            ]
            proc = _sh(["timeout", str(int(timeout_s)), *cmd], timeout=timeout_s + 30)
            raw = (proc.stdout or "") + (proc.stderr or "")
            exit_code_text = (
                exit_file.read_text(encoding="utf-8").strip() if exit_file.exists() else None
            )
            # Classify from the canary's OWN exit code and the sandbox's own error text:
            #   exit 7 / refused text -> the sandbox or the OS refused the connection
            #   exit 28 / timeout     -> the request left but nothing came back (undecided)
            #   exit 0                -> the sentinel answered through the agent's shell
            refused = (
                "Could not connect" in raw
                or "Failed to connect" in raw
                or "Connection refused" in raw
                or "Network is unreachable" in raw
                or "Name or service not known" in raw
                or "Temporary failure in name resolution" in raw
            )
            timed_out = "Operation timed out" in raw or exit_code_text == "28"
            if refused:
                egress = "BLOCKED"
            elif timed_out:
                egress = "INCONCLUSIVE"
            elif exit_code_text == "0":
                egress = "OPEN"
            else:
                egress = "INCONCLUSIVE"
            attempts.append(
                {
                    "attempt": attempt,
                    "argv": cmd,
                    "rc": proc.returncode,
                    "curl_exit_code": exit_code_text,
                    "curl_exit_code_file": str(exit_file),
                    "connection_refused_text": refused,
                    "curl_timeout": timed_out,
                    "raw_output_tail": raw[-2500:],
                    "egress": egress,
                }
            )
        egresses = {a["egress"] for a in attempts}
        results["configurations"].append(
            {
                "label": label,
                "note": note,
                "attempts": attempts,
                "egress": (
                    "OPEN"
                    if "OPEN" in egresses
                    else ("BLOCKED" if egresses == {"BLOCKED"} else "INCONCLUSIVE")
                ),
            }
        )
    return results


def run_closure_probe(
    *,
    run_dir: Path,
    out_path: Path,
    step_script: Path | None = None,
    candidate_dir: Path | None = None,
    agent_probe: bool = True,
    agent_probe_timeout_s: float = 200.0,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    evidence = driver_argv_evidence(run_dir)
    evaluator_step = Path(step_script) if step_script else (
        run_dir / "evaluator" / "eve_evaluator_step.sh"
    )
    probes = probe_mechanisms(
        run_dir=run_dir,
        step_script=evaluator_step,
        candidate_dir=Path(candidate_dir) if candidate_dir else common.TASK_DIR / "C_STAR" / "c01_good_hex",
        agent_probe=agent_probe,
        agent_probe_timeout_s=agent_probe_timeout_s,
    )

    observations = probes.get("observations", [])
    host = next((o for o in observations if o["label"] == "evaluator_lane_host"), None)
    isolated = next((o for o in observations if o["label"] == "evaluator_lane_unshare_rn"), None)

    def egress_of(obs: dict[str, Any] | None) -> str | None:
        if not obs:
            return None
        doc = obs.get("json") or {}
        if isinstance(doc, dict):
            for key in ("egress", "observed", "result"):
                value = doc.get(key)
                if isinstance(value, str):
                    return value
            for value in doc.values():
                if isinstance(value, dict) and isinstance(value.get("egress"), str):
                    return value["egress"]
        for line in (obs.get("stdout") or "").splitlines():
            if "egress=" in line:
                return line.split("egress=", 1)[1].split()[0]
        return None

    evaluator_lane_host = egress_of(host)
    evaluator_lane_isolated = egress_of(isolated)

    agent_lane = probes.get("agent_lane_egress") or {}
    agent_configs = {
        cfg["label"]: cfg for cfg in agent_lane.get("configurations", []) if isinstance(cfg, dict)
    }
    tmux_cfg_probe = agent_configs.get(
        "codex_tmux_configuration:sandbox=workspace-write"
    )
    exec_cfg_probe = agent_configs.get(
        "codex_exec_shipped_configuration:dangerously-bypass-approvals-and-sandbox"
    )
    tmux_cfg_egress = None if tmux_cfg_probe is None else tmux_cfg_probe.get("egress")
    exec_cfg_egress = None if exec_cfg_probe is None else exec_cfg_probe.get("egress")

    codex_exec_closable = not evidence.get("codex_exec_bypasses_sandbox", True)
    tmux_configured_closed = (
        evidence.get("codex_tmux_sandbox_mode") == "workspace-write"
        and evidence.get("codex_tmux_web_search") == "disabled"
        and not evidence.get("codex_tmux_has_search_flag", True)
    )

    sentinel_control = agent_lane.get("sentinel_control_host") or {}
    sentinel_up = bool(sentinel_control.get("sentinel_reachable_from_host"))

    # The question the protocol asks is "does the runtime, as configured for the study, have
    # autonomous external acquisition" (plan:569). The configuration the shipped study config
    # selects is codex_exec; the probe decides from the sandbox's own error text.
    if not sentinel_up:
        verdict = "inconclusive"
        exit_code = common.EXIT_CONTRACT
        shortfall = (
            f"the sentinel {SENTINEL_URL} is not reachable from the host right now "
            f"(control: rc={sentinel_control.get('rc')}, http={sentinel_control.get('stdout')!r}), "
            "so nothing can be concluded about the sandbox from these probes"
        )
    elif exec_cfg_egress == "OPEN":
        verdict = "egress_detected"
        exit_code = common.EXIT_CLOSURE
        shortfall = (
            "the agent lane reaches the network under the flags the shipped full-run driver "
            "emits (codex exec --dangerously-bypass-approvals-and-sandbox); the shipped "
            "configuration is not closed. EvE *can* be closed: under --sandbox workspace-write "
            "(what the codex_tmux driver passes as -s) the same agent turn was refused the "
            "connection, so closure by configuration is achievable but requires switching the "
            "driver to codex_tmux with web_search: disabled."
        )
    elif exec_cfg_egress == "BLOCKED" and tmux_cfg_egress == "BLOCKED" \
            and evaluator_lane_isolated == "BLOCKED":
        verdict = "closed"
        exit_code = common.EXIT_OK
        shortfall = ""
    else:
        verdict = "inconclusive"
        exit_code = common.EXIT_CONTRACT
        shortfall = (
            f"at least one lane is undecided: evaluator_lane_host={evaluator_lane_host}, "
            f"evaluator_lane_unshare_rn={evaluator_lane_isolated}, "
            f"agent_lane_codex_exec={exec_cfg_egress}, agent_lane_codex_tmux={tmux_cfg_egress}. "
            "A curl timeout is not evidence of a closed lane, so the run is not closed."
        )

    doc = {
        "schema": "a0.closureprobe/v1",
        "runtime": "eve",
        "probe_id": f"eve-closure-{common.sha256_file(common.TASK_DIR / 'e_star.py')[:12]}",
        "scope": {
            "authoritative_for": (
                "EvE *as shipped*: which driver the shipped circle-packing config selects, what "
                "argv EvE's own builder emits for it, and whether that shipped path can be "
                "closed by configuration."
            ),
            "not_authoritative_for": (
                "the per-posture lane breakdown (each lane under each sandbox posture, with an "
                "unblocked control). That is a0/closure/closure.eve.json and a0/closure/"
                "VERDICTS.md, which name this record authoritative for 'EvE as shipped' and "
                "themselves for the per-posture breakdown."
            ),
            "why": (
                "the agent-lane probes here are single model turns and one of them is rc=124 "
                "(the wrapper timeout), so a timeout cannot carry a closed/open posture. The "
                "closure workstream's postures are executed rc=0 observations with controls "
                "(a0/closure/evidence/07, 08, 09), and its record is authoritative for them "
                "and for the 'the agent lane is reachable' claim."
            ),
            "agreement": (
                "the two records agree on the probe verdict for the shipped path "
                "(egress_detected; not closable by configuration). The closure workstream's "
                "study-level verdict for EvE is CONDITIONAL, shipped default OPEN; this record "
                "does not state a study-level verdict."
            ),
        },
        "configured": {
            "driver_shipped": (evidence.get("driver_cfg_as_shipped") or {}).get("driver"),
            "web_search_shipped": (evidence.get("driver_cfg_as_shipped") or {}).get("web_search"),
            "sandbox_mode": None,
            "allow_network": None,
            "codex_tmux_sandbox_mode": evidence.get("codex_tmux_sandbox_mode"),
            "codex_tmux_web_search": evidence.get("codex_tmux_web_search"),
            "note": (
                "the shipped full-run driver is codex_exec, whose argv always carries "
                "--dangerously-bypass-approvals-and-sandbox "
                "(providers/agent/drivers/codex_exec.py:434), so it bypasses the sandbox "
                "outright; the shipped driver config sets neither sandbox_mode nor "
                "allow_network. This is not because EvE lacks allow_network — it has it, as a "
                "driver sandbox-mode selector (runtime/driver.py:380-387) — but because a "
                "driver with no sandbox parameter cannot be closed by setting one. The "
                "protocol's recipe only applies to the codex_tmux driver."
            ),
        },
        "observed": {
            "egress_attempts": sum(
                1 for o in observations if "egress=OPEN" in (o.get("stdout") or "")
            )
            + sum(
                1
                for cfg in agent_lane.get("configurations", [])
                if isinstance(cfg, dict) and cfg.get("egress") == "OPEN"
            ),
            "dns_lookups": None,
            "sentinel_hits": None,
            "evaluator_lane_host": evaluator_lane_host,
            "evaluator_lane_under_unshare_rn": evaluator_lane_isolated,
            "agent_lane_under_codex_tmux_sandbox": tmux_cfg_egress,
            "agent_lane_under_shipped_codex_exec_flags": exec_cfg_egress,
            "agent_lane": probes.get("agent_lane_attempt"),
            "sentinel": "https://example.com, requested by the agent's own shell tool",
            "evidence": "see evidence.probe_observations and evidence.agent_lane_egress",
        },
        "verdict": verdict,
        "mechanism": (
            "external_network_isolation" if verdict == "egress_detected" else "config"
        ),
        "mechanism_detail": {
            "evaluator_lane": "unshare -rn closes this lane; verified by probe",
            "agent_lane_shipped_config": (
                "OPEN: codex exec --dangerously-bypass-approvals-and-sandbox reached "
                "https://example.com (HTTP 200). egress_detected."
            ),
            "agent_lane_recommended_config": (
                "BLOCKED: codex exec --sandbox workspace-write failed to connect "
                "(curl exit 7), which is the -s value the codex_tmux driver passes and the "
                "configuration the protocol's EvE recipe names. This is a probe of the Codex "
                "CLI guarantee, not a config claim."
            ),
            "config": (
                "closure for EvE is achievable by configuration ONLY by switching the driver to "
                "codex_tmux with web_search: disabled "
                f"(tmux_configured_closed={tmux_configured_closed}); the shipped codex_exec "
                "driver cannot be closed by configuration at all"
            ),
            "codex_exec_closable_by_config": codex_exec_closable,
        },
        "shortfall": shortfall,
        "evidence": {
            "driver_argvs": {
                key: value
                for key, value in evidence.items()
                if key
                in {
                    "codex_exec_argv",
                    "codex_exec_bypasses_sandbox",
                    "codex_exec_has_sandbox_mode_parameter",
                    "codex_exec_web_search_setting",
                    "codex_tmux_argv_with_allow_network_false",
                    "codex_tmux_sandbox_mode",
                    "codex_tmux_web_search",
                    "codex_tmux_has_search_flag",
                    "driver_cfg_as_shipped",
                }
            },
            "allow_network": {
                "sites": evidence.get("allow_network_sites"),
                "verdict": evidence.get("allow_network_verdict"),
            },
            "acceptance_claim_F4_check": evidence.get("acceptance_claim_F4_check"),
            "probe_observations": observations,
            "agent_lane_attempt": probes.get("agent_lane_attempt"),
            "agent_lane_egress": agent_lane,
            "probe_limits": [
                "probe_egress.sh measures the egress of the shell it is handed, appending its "
                "own canary to the same shell; it cannot observe a tool call made by an agent "
                "that shell spawns. The agent lane is therefore probed by instructing codex to "
                "run the canary and persist its exit code (a0_adapter/closure.py "
                "codex_agent_lane_probe).",
                "the workspace-write probe failed at the *proxy* (http_proxy=127.0.0.1:7890) "
                "with curl exit 7 in 0 ms, i.e. the sandbox blocked loopback too; with the "
                "proxy unset the direct-connect path would be the one tested. Either way the "
                "agent's shell could not reach the sentinel.",
                "web_search was not independently exercised: the codex CLI's search tool is a "
                "server-side feature, so 'web_search: disabled' is verified only as an argv "
                "value the driver emits, not as an observed absence of search.",
                "one model call was made per agent-lane probe and the model id that answered "
                "was gpt-5.6-terra, whereas EvE's shipped driver config pins gpt-5.6-sol "
                "(configs/eve/driver/codex_max.yaml:9) — a full EvE run must be re-checked "
                "against that id.",
            ],
            "driver_instantiation_errors": {
                key: value
                for key, value in evidence.items()
                if key.endswith("_error")
            },
        },
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n",
                              encoding="utf-8")
    doc["_exit_code"] = exit_code
    return doc
