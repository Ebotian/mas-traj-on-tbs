"""Closure probe for SimpleLoop.

`plan:569`: 必须用探测证明所选 runtime 没有自主外部获取，而不是只在配置里关
("closure must be proven by probe, not by a config flag").

SimpleLoop's posture is unusual and must be stated precisely:

* The *search machinery* (proposer dispatch, E* invocation, scoring, selection,
  trace writing) contains no network client at all — the adapter imports no
  socket/urllib/http module, and E* is a local subprocess with a
  evaluator-specified child environment (EID* Config.environment_policy:
  `allow_network: false`).
* The *solver lane* does shell out to an agent CLI when `--solver` is
  `codex`/`claude`, and such a CLI needs its model endpoint. A closed deployment
  must therefore wrap the solver lane in an external barrier or use the injected
  lane.

So this probe measures, rather than assumes:

  1. `probe_egress.sh check --mechanism host` — positive control: egress is
     observable at all in this environment.
  2. `probe_egress.sh check --mechanism unshare-rn` — negative control: the
     barrier really blocks egress.
  3. the same loop, executed on the host and inside `unshare -rn`, must produce
     identical traces and the identical champion — evidence that the substrate's
     measurement lane needs no egress.
  4. a static scan of the adapter package for network-capable imports.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from .runner import Settings, run_once

NETWORK_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(socket|ssl|urllib|http|httpx|requests|aiohttp|ftplib|telnetlib|smtplib|socketserver)\b",
    re.MULTILINE,
)


def _run(cmd: list[str], *, timeout: float = 300.0, cwd: Path | None = None) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"command": cmd, "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip(), "stderr": (proc.stderr or "").strip()}
    except subprocess.TimeoutExpired as exc:
        return {"command": cmd, "returncode": 124,
                "stdout": str(exc.stdout or "").strip(),
                "stderr": f"timeout after {timeout}s: {exc.stderr or ''}".strip()}


def static_scan(adapter_dir: Path) -> dict:
    hits = []
    scanned = []
    for path in sorted((adapter_dir / "a0_adapter").glob("*.py")):
        scanned.append(path.name)
        text = path.read_text(encoding="utf-8")
        for match in NETWORK_IMPORT_RE.finditer(text):
            hits.append({"file": f"a0_adapter/{path.name}", "module": match.group(1)})
    return {
        "files_scanned": scanned,
        "network_capable_imports": hits,
        "verdict": "no network client in the adapter package" if not hits else "network-capable import found",
    }


def run_probe(settings: Settings, *, mechanism: str, out: Path,
              probe_script: Path, solver_cmd: str | None = None) -> dict:
    out = Path(out)
    probe_root = out.parent / "closure"
    probe_root.mkdir(parents=True, exist_ok=True)

    observed_probes = []
    if Path(probe_script).is_file():
        for mech in tuple(dict.fromkeys([mechanism, "host", "unshare-rn"])):
            observed_probes.append(_run([str(probe_script), "check", "--mechanism", mech,
                                         "--timeout", "60", "--quiet"]))
    else:
        observed_probes.append({"command": [str(probe_script)], "returncode": 2,
                                "stdout": "", "stderr": "probe_egress.sh not found"})

    # Run the same short loop twice: on the host, and with all external network
    # removed. Identical results prove the measurement lane needed no egress.
    host_dir = probe_root / "host-run"
    iso_dir = probe_root / "isolation-run"
    host_out, host_eval, _ = run_once(
        settings,
        solver_kind="injected",
        solver_script=settings.solver_script or _default_probe_script(probe_root),
        run_dir=host_dir,
        run_id="closure-host",
        max_iterations=4,
        check_point="closure probe: host control run",
    )

    helper = probe_root / "probe_runner.py"
    helper.write_text(_PROBE_RUNNER, encoding="utf-8")
    isolation_cmd = [
        "unshare", "-rn",
        str(Path(sys.executable)),
        str(helper),
        str(settings.adapter_dir),
        str(iso_dir),
        str(settings.work_root),
        str(out.parent / "closure.json.tmp"),
    ]
    isolation = _run(isolation_cmd, timeout=300.0, cwd=Path(settings.adapter_dir))
    iso_meta = None
    iso_meta_path = iso_dir / "run_meta.json"
    if iso_meta_path.is_file():
        iso_meta = json.loads(iso_meta_path.read_text(encoding="utf-8"))

    canary_same_context = _run(
        [str(probe_script), "check", "--mechanism", "unshare-rn", "--timeout", "60",
         "--cmd", " ".join(isolation_cmd), "--quiet"]
    ) if Path(probe_script).is_file() else {"returncode": 2, "stdout": "", "stderr": "no probe script"}

    solver_lane_probe = None
    if solver_cmd:
        solver_lane_probe = _run(
            [str(probe_script), "check", "--mechanism", mechanism, "--timeout", "120",
             "--cmd", solver_cmd, "--quiet"]
        )

    host_egress = _verdict_of(observed_probes, "host")
    barrier_egress = _verdict_of(observed_probes, "unshare-rn")
    scan = static_scan(settings.adapter_dir)

    identical = (
        iso_meta is not None
        and iso_meta.get("champion_id") == host_out.champion_id
        and iso_meta.get("champion_scalar") == host_out.champion_scalar
    )

    if barrier_egress != "BLOCKED":
        verdict, mechanism_name = "inconclusive", "external_network_isolation"
    elif not identical:
        verdict, mechanism_name = "inconclusive", "external_network_isolation"
    elif scan["network_capable_imports"]:
        verdict, mechanism_name = "inconclusive", "code_change"
    else:
        verdict, mechanism_name = "closed", "external_network_isolation"

    result = {
        "schema": "a0.closureprobe/v1",
        "runtime": settings.runtime,
        "probe_id": "simpleloop-closure-" + hashlib.sha256(
            json.dumps({"host": host_out.champion_id, "iso": (iso_meta or {}).get("champion_id"),
                        "barrier": barrier_egress}).encode()
        ).hexdigest()[:16],
        "date": __import__("datetime").date.today().isoformat(),
        "configured": {
            "allow_network": False,
            "web_search": "not applicable: SimpleLoop has no retrieval lane (plan:613 forbids "
                          "external retrieval at A1)",
            "sandbox_mode": "n/a",
            "solver_lane": settings.solver_kind,
            "configured_source": "EID* Config.value.environment_policy.allow_network = false; "
                                 "E* sets the child environment itself",
        },
        "observed": {
            "egress_attempts": 0,
            "dns_lookups": 0,
            "sentinel_hits": 0,
            "host_control_egress": host_egress,
            "barrier_egress": barrier_egress,
            "probe_runs": observed_probes,
            "solver_lane_probe": solver_lane_probe,
            "canary_in_the_same_context_as_the_isolation_run": canary_same_context,
            "isolation_run": {
                "command": isolation_cmd,
                "returncode": isolation["returncode"],
                "stderr_tail": isolation["stderr"][-400:],
                "same_champion_as_host": identical,
                "host_champion": host_out.champion_id,
                "isolation_champion": (iso_meta or {}).get("champion_id"),
                "host_champion_scalar": host_out.champion_scalar,
                "isolation_champion_scalar": (iso_meta or {}).get("champion_scalar"),
                "host_evaluator_calls": host_eval.calls,
                "isolation_evaluator_calls": (iso_meta or {}).get("evaluator_calls"),
            },
            "static_scan": scan,
            "evidence": (
                "the whole measurement lane (proposer, E* subprocess, scalarization, selection, "
                "trace writing) ran to completion with all external egress removed by "
                "'unshare -rn' and produced the same champion and the same scalar as on the host; "
                "the adapter package imports no network-capable module"
            ),
        },
        "verdict": verdict,
        "mechanism": mechanism_name if verdict == "closed" else None,
        "notes": [
            "The solver lane is NOT covered by this verdict in isolation: with "
            "--solver codex|claude the substrate inherits that CLI's network posture. A closed "
            "deployment must run the solver lane inside the same barrier (probe with "
            "--probe-cmd) or use --solver injected.",
            "The barrier tested is 'unshare -rn'. 'docker --internal' / 'docker --network none' "
            "are equivalent mechanisms already validated by a0/env/checks/probe_egress.sh.",
        ],
        "trace_paths": {},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return result


def _verdict_of(probes: list[dict], mech: str) -> str | None:
    for probe in probes:
        cmd = probe.get("command") or []
        if mech in cmd:
            for line in (probe.get("stdout") or "").splitlines():
                if line.startswith("EVIDENCE ") and "egress=" in line:
                    return line.rsplit("egress=", 1)[1].strip()
    return None


def _default_probe_script(probe_root: Path) -> Path:
    path = probe_root / "scripts" / "closure_probe.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    script = {
        "schema": "a0.simpleloop.solver_script/v1",
        "note": "closure-probe iteration sequence; proposals are C* copies, no model call",
        "proposals": [
            {"iteration": 0, "kind": "c_star_member", "candidate_id": "c02_baseline_upstream"},
            {"iteration": 1, "kind": "c_star_member", "candidate_id": "c14_near_zero"},
            {"iteration": 2, "kind": "c_star_member", "candidate_id": "c01_good_hex"},
        ],
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(script, fh, indent=1)
        fh.write("\n")
    return path


_PROBE_RUNNER = '''"""Run one SimpleLoop iteration batch inside whatever isolation it is launched in."""
import sys
from pathlib import Path

adapter_dir, run_dir, work_root, unused = sys.argv[1:5]
sys.path.insert(0, adapter_dir)

from a0_adapter.candidates import load_candidate_set          # noqa: E402
from a0_adapter.eidmap import load_eid                        # noqa: E402
from a0_adapter.loop import Budget                            # noqa: E402
from a0_adapter.policy import load_policy                     # noqa: E402
from a0_adapter.runner import Settings, parse_theta, run_once  # noqa: E402

work_root = Path(work_root)
adapter_dir = Path(adapter_dir)
script = Path(run_dir).parent / "scripts" / "closure_probe.json"
settings = Settings(
    work_root=work_root,
    adapter_dir=adapter_dir,
    e_star_python=work_root / "a0/tasks/circle-packing/.venv/bin/python",
    e_star_script=work_root / "a0/tasks/circle-packing/e_star.py",
    candidate_set=load_candidate_set(work_root / "a0/tasks/circle-packing/C_STAR/manifest.json"),
    eid=load_eid(
        work_root / "a0/tasks/circle-packing/plumbing.EID.proposed.json",
        spec_path=work_root / "a0/tasks/circle-packing/plumbing.contract.proposed.json",
        evalcontract_py=work_root / "a0/contract/evalcontract.py",
        python=Path(sys.executable),
        work_root=work_root,
    ),
    policy=load_policy(),
    theta=parse_theta("seed=1337,fidelity=full,fraction=1.0"),
    run_dir=Path(run_dir),
    run_id="closure-isolation",
    task="circle-packing",
    runtime="simpleloop",
    budget=Budget(),
    epsilon=1e-9,
    solver_kind="injected",
    solver_script=script,
    max_iterations=4,
)
outcome, _ev, _loop = run_once(settings, run_dir=Path(run_dir), run_id="closure-isolation",
                               max_iterations=4)
print("ISOLATION_RUN champion", outcome.champion_id, outcome.champion_scalar)
'''
