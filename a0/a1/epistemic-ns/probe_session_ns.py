#!/usr/bin/env python3
"""Mechanism A feasibility probe: can a CLI session run with the repo hidden?

Runs, from outside, the whole measurement the assignment asks for and writes raw
evidence under `--out`:

1. **reachability** — `probe_inside.py` under `session_sandbox.prefix`, with a host-side
   control listing the same paths, so "absent inside" means *hidden*, not *never there*.
2. **network** — the meter reaches the session over a unix-socket relay on the session's
   own loopback; every other destination is blocked.
3. **a real metered call** — `codex exec` (Responses route) and `claude -p` (Anthropic
   route), each through `a0/meter/`, each leaving a ledger row.
4. **the lane invocation shapes** — the KAPSO `CodexCodingAgent` argv, imported from the
   pinned checkout, run inside the lane; and the claude argv the KAPSO adapter uses.
5. **cost and fragility** — startup latency, nested namespaces, codex's own sandbox
   inside the lane, canaries for writes that would leak to the host.

The API key is read from `$DEEPSEEK_API_KEY` (set by the caller in the same command) and
only forwarded into the child environment; it is never printed and never written down.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

import session_sandbox as ss  # noqa: E402
from a0.a1.meter_runner import MeterProxy  # noqa: E402
from a0.a1.topology import UnixRelay  # noqa: E402

SESSION_ROOT = Path(os.environ.get("A0A1_EPISTEMIC_NS_DIR", "/dev/shm/a0a1-epistemic"))
MODEL = "deepseek-flash"
KAPSO_VENV_PYTHON = Path("/home/ebt/rsi-dev/a0/runtimes/kapso/.venv/bin/python")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _write(out: Path, name: str, payload: Any) -> str:
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=repr) + "\n",
                        encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    return str(path)


def _run(argv: List[str], *, env: Optional[dict] = None, cwd: Optional[str] = None,
         timeout: float = 300.0, stdin: Optional[str] = None) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, env=env, cwd=cwd, input=stdin, capture_output=True,
                              text=True, errors="replace", timeout=timeout)
        return {"argv": argv, "returncode": proc.returncode, "stdout": _text(proc.stdout),
                "stderr": _text(proc.stderr), "seconds": round(time.monotonic() - started, 3),
                "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"argv": argv, "returncode": None, "stdout": _text(exc.stdout),
                "stderr": _text(exc.stderr), "seconds": round(time.monotonic() - started, 3),
                "timed_out": True}


def _session_dirs(name: str) -> Dict[str, Path]:
    base = SESSION_ROOT / "session" / name
    dirs = {k: base / k for k in ("home", "codex_home", "claude_cfg", "workspace", "relay")}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _codex_config(port: int) -> str:
    return (
        f'model = "{MODEL}"\n'
        'model_provider = "meter"\n'
        '[model_providers.meter]\n'
        'name = "meter"\n'
        f'base_url = "http://127.0.0.1:{port}/v1"\n'
        'wire_api = "responses"\n'
        'env_key = "DEEPSEEK_API_KEY"\n'
    )


def _base_env(dirs: Dict[str, Path], key: str) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(dirs["home"])
    env.pop("XDG_RUNTIME_DIR", None)
    # A host HTTP(S) proxy is a *rerouting* of the CLI's egress: inside the closed
    # netns the proxy is unreachable, so every model request fails ("error sending
    # request", measured) instead of going to the meter.  Strip every proxy name.
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy",
                 "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        env.pop(name, None)
    env["DEEPSEEK_API_KEY"] = key
    return env


def _claude_env(env: dict, dirs: Dict[str, Path], port: int, key: str) -> dict:
    env = dict(env)
    env.update({
        "CLAUDE_CONFIG_DIR": str(dirs["claude_cfg"]),
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_MODEL": MODEL,
        "ANTHROPIC_SMALL_FAST_MODEL": MODEL,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": MODEL,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": MODEL,
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "128000",
    })
    return env


#: Rendered under the KAPSO checkout's own venv, so the argv is the adapter's, not a paraphrase.
_ADAPTER_ARGV_SNIPPET = r"""
import json, sys
sys.path.insert(0, "/home/ebt/kapso_ck/kapso/src")
from kapso.execution.coding_agents.adapters.codex_agent import CodexCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig
spec = {"sandbox": __SANDBOX__, "web_search": False, "timeout": 900, "effort": "low"}
if __JSON__:
    spec["capture_thread_id"] = True
cfg = CodingAgentConfig(agent_type="codex", model="deepseek-flash",
                        debug_model="deepseek-flash", agent_specific=spec)
print(json.dumps(CodexCodingAgent(cfg)._exec_command("deepseek-flash", __LAST__)))
"""


def _codex_lane_argv_from_adapter(sandbox: str = "danger-full-access",
                                  capture_thread_id: bool = False,
                                  last_message: str = "/tmp/kapso_last_message.txt") -> Dict[str, Any]:
    """The true KAPSO codex argv, taken from the pinned adapter, not paraphrased."""
    snippet = (_ADAPTER_ARGV_SNIPPET
               .replace("__SANDBOX__", json.dumps(sandbox))
               .replace("__JSON__", "True" if capture_thread_id else "False")
               .replace("__LAST__", json.dumps(last_message)))
    if KAPSO_VENV_PYTHON.is_file():
        proc = subprocess.run([str(KAPSO_VENV_PYTHON), "-c", snippet],
                              capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            return {"source": "a0/a1/kapso_t1 lane -> kapso codex_agent.py::_exec_command",
                    "argv": json.loads(proc.stdout.strip().splitlines()[-1]),
                    "derived_from_source": False, "rendered_by": str(KAPSO_VENV_PYTHON)}
        error = proc.stderr.strip()[-300:]
    else:
        error = f"venv python absent: {KAPSO_VENV_PYTHON}"
    return {"source": "kapso codex_agent.py::_exec_command (read from source)",
            "argv": ["codex", "exec", "--sandbox", sandbox,
                     "--skip-git-repo-check", "--color", "never",
                     "--output-last-message", last_message,
                     "-m", MODEL, "-c", 'model_reasoning_effort="low"']
                    + (["--json"] if capture_thread_id else []),
            "derived_from_source": True, "render_error": error}


def step_reachability(out: Path, dirs: Dict[str, Path], sock: Optional[Path],
                      port: Optional[int], key: str, names: Dict[str, str]) -> Dict[str, Any]:
    probe = dirs["home"].parent / "probe_inside.py"  # under /dev/shm, never under /home
    shutil.copy(HERE / "probe_inside.py", probe)
    cmd = [sys.executable, str(probe), "--repo-root", str(REPO_ROOT),
           "--session-home", str(dirs["home"]), "--workspace", str(dirs["workspace"])]
    if port:
        cmd += ["--meter-port", str(port)]
    allow = [dirs["home"], dirs["workspace"]]
    receipt = dirs["home"].parent / "receipt.json"
    argv = ss.prefix(cmd, allow=allow, meter_port=port, relay_sock=sock, receipt=receipt)
    env = _base_env(dirs, key)
    result = _run(argv, env=env, cwd=str(REPO_ROOT), timeout=180)
    inside = None
    try:
        inside = json.loads(result["stdout"])
    except Exception:  # noqa: BLE001
        inside = None
    control = {name: {"path": path, "exists_on_host": os.path.exists(path)}
               for name, path in names.items()}
    return {"result": result, "inside": inside, "host_control": control,
            "receipt": json.loads(receipt.read_text()) if receipt.exists() else None,
            "receipt_path": str(receipt), "probe_deployed_at": str(probe)}


def step_latency(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    env = _base_env(dirs, key)
    bare = []
    wrapped = []
    for _ in range(3):
        bare.append(_run([sys.executable, "-c", "pass"], env=env)["seconds"])
        argv = ss.prefix([sys.executable, "-c", "pass"], allow=[dirs["home"], dirs["workspace"]])
        wrapped.append(_run(argv, env=env)["seconds"])
    return {"bare_python_seconds": bare, "in_namespace_seconds": wrapped,
            "median_added_seconds": round(sorted(wrapped)[1] - sorted(bare)[1], 3)}


def step_nested_and_landlock(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    """What breaks when the lane is entered differently, or a sandbox runs inside it."""
    env = _base_env(dirs, key)
    script = r"""
import json, os, subprocess, sys
out = {}
# nested user namespace
p = subprocess.run(["unshare", "-r", "true"], capture_output=True, text=True)
out["nested_userns"] = {"rc": p.returncode, "stderr": p.stderr.strip()[:160]}
# nested mount namespace
p = subprocess.run(["unshare", "-m", "true"], capture_output=True, text=True)
out["nested_mountns"] = {"rc": p.returncode, "stderr": p.stderr.strip()[:160]}
# another mount namespace + hide check: a child that unshares mount ns still sees the hidden /home
p = subprocess.run(["unshare", "-m", "sh", "-c", "ls /home | wc -l"], capture_output=True, text=True)
out["child_mountns_sees_home_entries"] = p.stdout.strip()
# /proc: how many pids, and are they all our own mount namespace?
pids = sorted(int(n) for n in os.listdir("/proc") if n.isdigit())
out["visible_pids"] = pids[:16]
out["visible_pid_count"] = len(pids)
try:
    mine = os.stat("/proc/self/ns/mnt").st_ino
    out["all_visible_share_my_mountns"] = all(
        os.stat(f"/proc/{p}/ns/mnt").st_ino == mine for p in pids)
except OSError as exc:
    out["mountns_check_error"] = type(exc).__name__
# can we see the host root through /proc/1/root ?
try:
    out["proc1_root_lists"] = sorted(os.listdir("/proc/1/root"))[:8]
except OSError as exc:
    out["proc1_root_error"] = type(exc).__name__
print(json.dumps(out))
"""
    argv = ss.prefix([sys.executable, "-c", script], allow=[dirs["home"], dirs["workspace"]])
    result = _run(argv, env=env, timeout=120)
    parsed = None
    try:
        parsed = json.loads(result["stdout"])
    except Exception:  # noqa: BLE001
        parsed = None
    return {"result": result, "parsed": parsed}


def step_codex_sandbox_inside(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    """codex's own `workspace-write` sandbox sets up seccomp/landlock *inside* our lane.

    Expected to fail the call (codex's own sandbox blocks `socket()`, measured in
    `a0/notes/exit-closed/local-model/evidence/codex_and_netns.txt`), which is the point:
    the read jail is the *mount namespace*, not the codex sandbox — the T1 lane's
    `danger-full-access` is what lets it call the model at all.
    """
    env = _base_env(dirs, key)
    (dirs["codex_home"] / "config.toml").write_text(
        'model = "%s"\nmodel_provider = "meter"\n[model_providers.meter]\n'
        'name = "meter"\nbase_url = "http://127.0.0.1:1/v1"\nwire_api = "responses"\n'
        'env_key = "DEEPSEEK_API_KEY"\n' % MODEL)
    env["CODEX_HOME"] = str(dirs["codex_home"])
    lane = _codex_lane_argv_from_adapter(sandbox="workspace-write",
                                         last_message=str(dirs["workspace"] / "ww_last.txt"))
    argv = ss.prefix(lane["argv"], allow=[dirs["home"], dirs["codex_home"], dirs["workspace"]])
    result = _run(argv, env=env, cwd=str(dirs["workspace"]), timeout=40, stdin="say nothing")
    return {"lane_argv": lane, "result": result}


def step_allow_under_hidden_root(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    """A workspace that lives *under a hidden root* must still be bound back.

    The KAPSO live probe puts its run dirs under `/tmp`, which this lane hides.  The
    allow-list is what puts such a path back; this step proves the bind-back works and
    that it does not re-expose the root.
    """
    work = Path("/tmp/a0a1-epistemic-hidden-root/workspace")
    shutil.rmtree(work.parent, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    (work / "marker.txt").write_text("visible", encoding="utf-8")
    # A sibling of the allowed workspace, under the same hidden root, must stay hidden.
    (work.parent / "secret.txt").write_text("secret", encoding="utf-8")
    script = "\n".join([
        "import json, os",
        "ws = " + repr(str(work)),
        "out = {",
        "  'workspace_listing': sorted(os.listdir(ws)),",
        "  'marker': open(os.path.join(ws, 'marker.txt')).read(),",
        "  'tmp_root_listing': sorted(os.listdir('/tmp'))[:8],",
        "  'hidden_sibling_readable': os.path.exists('/tmp/a0a1-epistemic-hidden-root/secret.txt'),",
        "}",
        "print(json.dumps(out))",
    ])
    argv = ss.prefix([sys.executable, "-c", script], allow=[work, dirs["home"]])
    result = _run(argv, env=_base_env(dirs, key), timeout=60)
    parsed = None
    try:
        parsed = json.loads(result["stdout"])
    except Exception:  # noqa: BLE001
        parsed = None
    return {"result": result, "parsed": parsed, "workspace": str(work),
            "workspace_on_host": work.exists()}


def _meter_session(name: str, dirs: Dict[str, Path]) -> Dict[str, Any]:
    work = SESSION_ROOT / "meter" / name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    proxy = MeterProxy(campaign_id=name, arm_id="A_ns", work_dir=work, issue_token=False)
    proxy.start()
    sock = dirs["relay"] / f"{name}.sock"
    relay = UnixRelay(sock, ("127.0.0.1", proxy.port))
    relay.start()
    return {"proxy": proxy, "relay": relay, "sock": sock, "work": work}


def step_real_codex_call(out: Path, dirs: Dict[str, Path], key: str, names: Dict[str, str]) -> Dict[str, Any]:
    m = _meter_session("NS_CODEX", dirs)
    proxy, relay = m["proxy"], m["relay"]
    (dirs["codex_home"] / "config.toml").write_text(_codex_config(proxy.port))
    env = _base_env(dirs, key)
    env["CODEX_HOME"] = str(dirs["codex_home"])
    last = dirs["workspace"] / "codex_last.txt"
    lane = _codex_lane_argv_from_adapter(last_message=str(last))
    lane_argv = lane["argv"]
    argv = ss.prefix(lane_argv, allow=[dirs["home"], dirs["codex_home"], dirs["workspace"]],
                     meter_port=proxy.port, relay_sock=m["sock"],
                     receipt=dirs["home"].parent / "codex_receipt.json")
    result = _run(argv, env=env, cwd=str(dirs["workspace"]), timeout=300,
                  stdin="Reply with the single word OK.")
    summary = proxy.ledger_summary()
    verified = proxy.verify_ledger()
    rows = []
    if proxy.ledger.is_file():
        rows = [json.loads(line) for line in proxy.ledger.read_text().splitlines() if line.strip()]
    proxy.stop(); relay.stop()
    return {"lane_argv": lane, "lane_argv_used": lane_argv, "result": result,
            "last_message": last.read_text()[:200] if last.exists() else None,
            "ledger_summary": summary, "ledger_rows": rows, "verify": verified,
            "receipt": json.loads((dirs["home"].parent / "codex_receipt.json").read_text())
                       if (dirs["home"].parent / "codex_receipt.json").exists() else None}


def step_real_codex_resume(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    """KAPSO's inbox continuation: a fresh `--json` session, then `resume <thread> -`."""
    m = _meter_session("NS_CODEX_RESUME", dirs)
    proxy, relay = m["proxy"], m["relay"]
    (dirs["codex_home"] / "config.toml").write_text(_codex_config(proxy.port))
    env = _base_env(dirs, key)
    env["CODEX_HOME"] = str(dirs["codex_home"])
    last = dirs["workspace"] / "resume_last.txt"
    fresh = _codex_lane_argv_from_adapter(capture_thread_id=True, last_message=str(last))
    first = _run(ss.prefix(fresh["argv"], allow=[dirs["home"], dirs["codex_home"], dirs["workspace"]],
                           meter_port=proxy.port, relay_sock=m["sock"]),
                 env=env, cwd=str(dirs["workspace"]), timeout=300,
                 stdin="Remember the codeword MARLIN7. Reply OK.")
    import re
    match = re.search(r'"type"\s*:\s*"thread\.started".*?"thread_id"\s*:\s*"([^"]+)"', first["stdout"])
    thread = match.group(1) if match else None
    second = None
    if thread:
        resumed = fresh["argv"] + ["resume", thread, "-"]
        second = _run(ss.prefix(resumed, allow=[dirs["home"], dirs["codex_home"], dirs["workspace"]],
                                meter_port=proxy.port, relay_sock=m["sock"]),
                      env=env, cwd=str(dirs["workspace"]), timeout=300,
                      stdin="What was the codeword? Reply with just the word.")
    summary = proxy.ledger_summary()
    proxy.stop(); relay.stop()
    return {"fresh_lane_argv": fresh, "thread_id": thread, "first": first, "second": second,
            "codeword_recalled": bool(second and "MARLIN7" in second["stdout"]),
            "ledger_summary": summary}


def step_real_claude_call(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    m = _meter_session("NS_CLAUDE", dirs)
    proxy, relay = m["proxy"], m["relay"]
    env = _claude_env(_base_env(dirs, key), dirs, proxy.port, key)
    argv = ss.prefix(["/usr/bin/claude", "-p", "Reply with the single word OK.",
                      "--output-format", "json"],
                     allow=[dirs["home"], dirs["claude_cfg"], dirs["workspace"]],
                     meter_port=proxy.port, relay_sock=m["sock"])
    result = _run(argv, env=env, cwd=str(dirs["workspace"]), timeout=300)
    summary = proxy.ledger_summary()
    verified = proxy.verify_ledger()
    proxy.stop(); relay.stop()
    return {"result": result, "ledger_summary": summary, "verify": verified}


def step_canary_leak(dirs: Dict[str, Path], key: str) -> Dict[str, Any]:
    """A write inside the lane must not appear on the host's hidden roots."""
    host_canary = Path("/tmp/.a0a1_epistemic_leak_canary")
    if host_canary.exists():
        host_canary.unlink()
    script = (
        "open('/tmp/.a0a1_epistemic_leak_canary','w').write('escaped');"
        "open('/home/.a0a1_epistemic_leak_canary','w').write('escaped');"
        "print('written')"
    )
    argv = ss.prefix([sys.executable, "-c", script], allow=[dirs["home"], dirs["workspace"]])
    result = _run(argv, env=_base_env(dirs, key))
    return {"result": result,
            "tmp_canary_on_host": Path("/tmp/.a0a1_epistemic_leak_canary").exists(),
            "home_canary_on_host": Path("/home/.a0a1_epistemic_leak_canary").exists(),
            "note": "inside the lane the host's /tmp and /home are fresh tmpfs; a write "
                    "there must not reach the host"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="probe_session_ns")
    parser.add_argument("--out", required=True)
    parser.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--skip-real-calls", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    key = os.environ.get(args.key_env, "")
    if not key and not args.skip_real_calls:
        print(f"${args.key_env} is empty; refusing to attempt a model call", file=sys.stderr)
        return 2

    evidence: Dict[str, Any] = {"schema": "a0.a1.epistemic_ns/probe/v1", "model": MODEL,
                                "repo_root": str(REPO_ROOT), "session_root": str(SESSION_ROOT)}
    names = {
        "repo": str(REPO_ROOT),
        "dot_git": str(REPO_ROOT / ".git"),
        "gptapi_md": str(Path.home() / "gptapi.md"),
        "targets_json": str(REPO_ROOT / "a0/tasks/maxcut/references/targets.json"),
        "commitments_json": str(REPO_ROOT / "a0/tasks/maxcut/references/witnesses/commitments.json"),
        "eval_graph": str(REPO_ROOT / "a0/tasks/maxcut/suite/eval/G_eval_0001.json"),
    }
    dirs = _session_dirs("main")

    # (1) reachability without a meter
    evidence["reachability_no_meter"] = step_reachability(out, dirs, None, None, key, names)
    _write(out, "01_reachability_no_meter.json", evidence["reachability_no_meter"])

    # (2) one metered session carrying both the network and the reachability probe
    m = _meter_session("NS_PROBE", dirs)
    try:
        reach = step_reachability(out, dirs, m["sock"], m["proxy"].port, key, names)
    finally:
        m["proxy"].stop(); m["relay"].stop()
    evidence["reachability_with_meter"] = reach
    _write(out, "02_reachability_with_meter.json", reach)

    # (3) latency
    evidence["latency"] = step_latency(dirs, key)
    _write(out, "03_latency.json", evidence["latency"])

    # (4) nested namespaces / landlock
    evidence["nested_and_proc"] = step_nested_and_landlock(dirs, key)
    _write(out, "04_nested_and_proc.json", evidence["nested_and_proc"])

    # (5) allow-list path under a hidden root must be bound back
    evidence["allow_under_hidden_root"] = step_allow_under_hidden_root(dirs, key)
    _write(out, "05_allow_under_hidden_root.json", evidence["allow_under_hidden_root"])

    # (6) codex's own sandbox inside the lane
    evidence["codex_workspace_write_inside"] = step_codex_sandbox_inside(dirs, key)
    _write(out, "06_codex_workspace_write_inside.json", evidence["codex_workspace_write_inside"])

    # (7) canary leak
    evidence["canary_leak"] = step_canary_leak(dirs, key)
    _write(out, "07_canary_leak.json", evidence["canary_leak"])

    if not args.skip_real_calls:
        evidence["real_codex_call"] = step_real_codex_call(out, dirs, key, names)
        _write(out, "08_real_codex_call.json", evidence["real_codex_call"])
        evidence["real_codex_resume"] = step_real_codex_resume(dirs, key)
        _write(out, "09_real_codex_resume.json", evidence["real_codex_resume"])
        evidence["real_claude_call"] = step_real_claude_call(dirs, key)
        _write(out, "10_real_claude_call.json", evidence["real_claude_call"])

    _write(out, "summary.json", evidence)
    print(json.dumps({
        "out": str(out),
        "codex_ceq": evidence.get("real_codex_call", {}).get("ledger_summary", {}),
        "codex_resume_ceq": evidence.get("real_codex_resume", {}).get("ledger_summary", {}),
        "claude_ceq": evidence.get("real_claude_call", {}).get("ledger_summary", {}),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
