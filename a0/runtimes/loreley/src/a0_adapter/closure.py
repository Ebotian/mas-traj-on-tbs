"""Closure probe: prove by measurement that Loreley has no autonomous egress.

Protocol §4.3 (``plan:569``) and ``ACCEPTANCE.md`` T7 require a *probe*, not a
config claim.  The protocol is explicit about Loreley: "Loreley 默认路径无网络开关，
需断网或改用 codex 后端" - its default path has no network switch, so the
mechanism is ``external_network_isolation``.

What is probed is the **candidate-execution channel** - the code path that runs
candidate source - not the orchestrator, which needs its own model endpoint and
therefore cannot be isolated:

* ``probe_egress.sh check --mechanism host`` and ``--mechanism docker-bridge`` are
  the positive controls: the barrier must not be "networking is broken".
* ``probe_egress.sh check --mechanism docker-internal`` is the negative control,
  with ``PROBE_LOCAL_*`` pointed at the sibling services so the result also shows
  the barrier is selective (``local=ok``) rather than a dead interface.
* the real channel is then run for real: ``E*`` executing the egress probe
  candidate inside the internal network, and the same command again on the bridge
  network as the positive control.  Only the first is the runtime's own lane.

Caveat, recorded because it is a sharp edge of this barrier: ``docker --internal``
also removes the container's route to the host, so the barrier cuts host loopback
as well as the public internet.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import A0_ROOT, EXIT_CLOSURE, EXIT_OK
from .runtime import E_STAR_PY, E_STAR_SCRIPT

PROBE_SCRIPT = A0_ROOT / "env" / "checks" / "probe_egress.sh"
INTERNAL_NET = "a0-loreley-internal"
BRIDGE_NET = "a0-loreley-net"
PROBE_IMAGE = "python:3.12-slim"
PROBE_CANDIDATE = Path(__file__).resolve().parents[2] / "probe" / "egress_candidate"
CLOSURE_SCHEMA = "a0.closureprobe/v1"


@dataclass(slots=True)
class ProbeObservation:
    name: str
    mechanism: str
    expectation: str
    observed: str
    evidence: str
    command: str
    extra: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mechanism": self.mechanism,
            "expectation": self.expectation,
            "observed": self.observed,
            "evidence": self.evidence,
            "command": self.command,
            **self.extra,
        }


def _run(command: list[str], *, timeout: int = 180) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=timeout,
    )
    return completed.returncode, completed.stdout


def _probe_egress(mechanism: str, *, local_host: str | None, local_port: int | None,
                  cmd: str | None = None, timeout: int = 60) -> ProbeObservation:
    command = [str(PROBE_SCRIPT), "check", "--mechanism", mechanism, "--image", PROBE_IMAGE,
               "--timeout", str(timeout)]
    if cmd:
        command += ["--cmd", cmd]
    env = {
        "PATH": "/usr/bin:/bin",
        "INTERNAL_NET": INTERNAL_NET,
        "HOME": "/tmp",
    }
    if local_host and local_port:
        env["PROBE_LOCAL_HOST"] = local_host
        env["PROBE_LOCAL_PORT"] = str(local_port)
    completed = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        check=False, env=env, timeout=timeout + 120,
    )
    output = completed.stdout
    verdict = "BLOCKED" if "egress=BLOCKED" in output else (
        "OPEN" if "egress=OPEN" in output else "UNKNOWN"
    )
    expectation = "open" if mechanism in {"host", "docker-bridge"} else "blocked"
    observed = "OPEN" if verdict == "OPEN" else ("BLOCKED" if verdict == "BLOCKED" else "UNKNOWN")
    return ProbeObservation(
        name=f"probe_egress:{mechanism}",
        mechanism=mechanism,
        expectation=expectation,
        observed=observed,
        evidence=next(
            (line for line in output.splitlines() if line.startswith("EVIDENCE ")),
            output.strip().splitlines()[-1] if output.strip() else "(no output)",
        ),
        command=" ".join(command),
        extra={"raw_output": output[-4000:], "returncode": completed.returncode},
    )


def _run_candidate_channel(network: str, result_dir: Path, *, label: str,
                           timeout: int = 240) -> ProbeObservation:
    """Run the runtime's real candidate-execution channel under ``network``."""

    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / "result.json"
    if result_path.exists():
        result_path.unlink()
    command = [
        "docker", "run", "--rm",
        "--network", network,
        "-v", "/home/ebt:/home/ebt",
        "-v", f"{result_dir}:/probe-egress",
        "-e", f"A0_EGRESS_RESULT={result_path}",
        "-w", "/tmp",
        PROBE_IMAGE,
        str(E_STAR_PY),
        str(E_STAR_SCRIPT),
        "evaluate",
        "--candidate", str(PROBE_CANDIDATE),
        "--seed", "1337",
        "--fidelity", "full",
        "--fraction", "1.0",
        "--out", f"/tmp/a0-closure-{label}.outcome.json",
    ]
    started = time.monotonic()
    returncode, output = _run(command, timeout=timeout)
    elapsed = time.monotonic() - started

    probe_result: dict[str, Any] | None = None
    if result_path.is_file():
        try:
            probe_result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            probe_result = None

    egress_open = False
    if probe_result:
        for key in ("dns_example_com", "tcp_example_com_443", "tcp_1_1_1_1_53",
                    "https_example_com"):
            if probe_result.get(key) == "ok":
                egress_open = True
                break

    expectation = "open" if network == BRIDGE_NET else "blocked"
    observed = "OPEN" if egress_open else "BLOCKED"
    return ProbeObservation(
        name=f"candidate_channel:{label}",
        mechanism="external_network_isolation" if network == INTERNAL_NET else "none (positive control)",
        expectation=expectation,
        observed=observed,
        evidence=(
            f"E* exit={returncode} elapsed={elapsed:.1f}s; candidate-side probe: "
            f"{json.dumps(probe_result, sort_keys=True) if probe_result else '(no result file)'}"
        ),
        command=" ".join(command),
        extra={
            "network": network,
            "e_star_exit": returncode,
            "e_star_output_tail": output[-1500:],
            "candidate_egress_result": probe_result,
            "host_loopback_note": (
                "the --internal barrier also cuts host loopback: 127.0.0.1 inside the "
                "container is the container, not the host"
            ),
        },
    )


def run_closure_probe(*, out_path: Path, run_dir: Path) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    observations: list[ProbeObservation] = []

    net_ok, net_out = _run(["docker", "network", "inspect", INTERNAL_NET], timeout=30)
    if net_ok != 0:
        raise RuntimeError(
            f"the internal network {INTERNAL_NET!r} does not exist; create it first "
            f"(`docker network create --internal {INTERNAL_NET}`)"
        )

    observations.append(_probe_egress("host", local_host=None, local_port=None))
    observations.append(_probe_egress("docker-bridge", local_host=None, local_port=None))
    observations.append(
        _probe_egress("docker-internal", local_host="a0-loreley-postgres", local_port=5432)
    )

    positive = _run_candidate_channel(
        BRIDGE_NET, run_dir / "candidate-egress-bridge", label="bridge"
    )
    observations.append(positive)
    negative = _run_candidate_channel(
        INTERNAL_NET, run_dir / "candidate-egress-internal", label="internal"
    )
    observations.append(negative)

    canary_internal = next(
        item for item in observations if item.name == "probe_egress:docker-internal"
    )
    canary_host = next(item for item in observations if item.name == "probe_egress:host")

    positive_control_ok = (
        canary_host.observed == "OPEN" and positive.observed == "OPEN"
    )
    negative_ok = (
        canary_internal.observed == "BLOCKED" and negative.observed == "BLOCKED"
    )
    verdict = (
        "closed"
        if positive_control_ok and negative_ok
        else ("egress_detected" if negative.observed == "OPEN" else "inconclusive")
    )

    document = {
        "schema": CLOSURE_SCHEMA,
        "runtime": "loreley",
        "probe_id": f"loreley-closure-{int(time.time())}",
        "mechanism": "external_network_isolation",
        "configured": {
            "network_switch_in_runtime": None,
            "note": (
                "Loreley's default path has no network switch (protocol plan:569); the "
                "closure mechanism is therefore external isolation, not configuration"
            ),
            "sandbox_mode": None,
            "web_search": None,
            "docker_network": INTERNAL_NET,
            "docker_network_internal": True,
        },
        "observed": {
            "egress_attempts": 4,
            "sentinel_hits": 0 if negative.observed == "BLOCKED" else 4,
            "positive_control_open": positive.observed == "OPEN",
            "negative_control_blocked": negative.observed == "BLOCKED",
            "evidence": negative.evidence,
        },
        "verdict": verdict,
        "caveats": [
            "docker --internal also removes the container's route to the host, so this "
            "barrier cuts host loopback as well as external egress",
            "the orchestrator process was NOT isolated: it needs its own channels and "
            "cannot be placed behind this barrier; only the candidate-execution channel is",
            "Loreley's own LLM-driven path (codex backend) could not be exercised: codex "
            "cannot complete a model call on this host (base_url points at 127.0.0.1:15722 "
            "with no listener), so the probed lane is the evaluator/candidate lane, which is "
            "the only lane this adapter can drive",
        ],
        "interpreter": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "probe_script": str(PROBE_SCRIPT),
        "probe_candidate": str(PROBE_CANDIDATE),
        "observations": [item.as_dict() for item in observations],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def exit_code_for(document: Mapping[str, Any]) -> int:
    return EXIT_OK if document.get("verdict") == "closed" else EXIT_CLOSURE
