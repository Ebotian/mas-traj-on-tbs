#!/usr/bin/env python3
"""In-lane closure probe: the four things the review asks the worker to attempt.

Run INSIDE the worker container by the agent's own shell tool, so every result
below is produced by the worker (not inferred from outside), from the worker's
own namespace:

  P1 shell       -- run a shell command, write and read back a file
  P2 dns         -- resolve the model host, a non-allowlisted host, the proxy
  P3 http        -- direct connect + direct HTTP to a non-allowlisted host, and
                    the same request through the proxy (the enforcement point
                    should record the denial)
  P4 candidate   -- spawn a child process running candidate code, and run the
                    frozen evaluator E* (which spawns its own candidate child)

Every probe is recorded, including the ones that fail: a refusal is the result.
Exit status is always 0; the JSON is the finding.

    python3 inlane_probe.py --out /work/wd/inlane_probe.json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROXY = os.environ.get("A0TL_PROXY", "http://a0tl-proxy:8787")
MODEL_HOST = "api.deepseek.com"
BLOCKED_HOST = "example.com"
BLOCKED_LITERAL = "93.184.216.34"  # example.com, as an IP literal so DNS cannot mask the result
WORK_ROOT = Path(os.environ.get("A0TL_WORK_ROOT", "/home/ebt/rsi-dev"))


def sh(cmd: list[str], timeout: float = 60.0) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"command": cmd, "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip()[:2000],
                "stderr": (proc.stderr or "").strip()[:2000]}
    except Exception as exc:  # noqa: BLE001 - a refused spawn is a result
        return {"command": cmd, "returncode": None, "error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------- P1 shell ---
def probe_shell(work: Path) -> dict:
    marker = work / "inlane_shell_marker.txt"
    text = "written-by-inlane-probe pid=%d" % os.getpid()
    write = "ok"
    try:
        marker.write_text(text, encoding="utf-8")
    except OSError as exc:
        write = f"{type(exc).__name__}: {exc}"
    read_back = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
    return {
        "file_written": str(marker),
        "file_write": write,
        "file_read_back_matches": read_back == text,
        "uname": " ".join(os.uname()),
        "pwd": os.getcwd(),
        "id": sh(["id"]),
        "sh_echo": sh(["sh", "-c", "echo INLANE-SHELL-OK"]),
        "hostname": socket.gethostname(),
        "python": sys.version.split()[0],
    }


# ----------------------------------------------------------------- P2 dns ---
def resolve(name: str) -> dict:
    started = time.monotonic()
    try:
        infos = socket.getaddrinfo(name, None)
        addrs = sorted({i[4][0] for i in infos})
        return {"name": name, "ok": True, "addresses": addrs,
                "sec": round(time.monotonic() - started, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "sec": round(time.monotonic() - started, 3)}


def probe_dns() -> dict:
    resolv = Path("/etc/resolv.conf")
    nameservers = []
    if resolv.is_file():
        for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("nameserver"):
                nameservers.append(line.split()[1])
    return {
        "resolv_conf_nameservers": nameservers,
        "proxy_by_container_name": resolve("a0tl-proxy"),
        "model_host": resolve(MODEL_HOST),
        "blocked_host": resolve(BLOCKED_HOST),
        "getent_blocked_host": sh(["getent", "hosts", BLOCKED_HOST]),
        "getent_proxy": sh(["getent", "hosts", "a0tl-proxy"]),
    }


# ---------------------------------------------------------------- P3 http ---
def tcp(host: str, port: int, timeout: float = 5.0) -> dict:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return {"target": f"{host}:{port}", "ok": True, "sec": round(time.monotonic() - started, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"target": f"{host}:{port}", "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "sec": round(time.monotonic() - started, 3)}


def http(url: str, proxy: str | None, timeout: float = 20.0) -> dict:
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})]
    opener = urllib.request.build_opener(*handlers)
    started = time.monotonic()
    try:
        with opener.open(url, timeout=timeout) as resp:
            body = resp.read(300).decode("utf-8", "replace")
            return {"url": url, "via_proxy": proxy, "status": resp.status,
                    "body_head": body.strip()[:200],
                    "sec": round(time.monotonic() - started, 3)}
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode("utf-8", "replace")
        return {"url": url, "via_proxy": proxy, "status": exc.code,
                "body_head": body.strip()[:200], "error": f"HTTPError: {exc}",
                "sec": round(time.monotonic() - started, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "via_proxy": proxy, "status": None,
                "error": f"{type(exc).__name__}: {exc}",
                "sec": round(time.monotonic() - started, 3)}


def probe_http() -> dict:
    probes = {
        "direct_tcp_literal_443": tcp(BLOCKED_LITERAL, 443),
        "direct_tcp_1.1.1.1_443": tcp("1.1.1.1", 443),
        "direct_tcp_proxy_8787": tcp("a0tl-proxy", 8787),
        "direct_http_blocked_host": http(f"http://{BLOCKED_LITERAL}/", None),
        "proxy_connect_blocked_host": http(f"https://{BLOCKED_HOST}/", PROXY),
        "proxy_connect_allowlisted_host": http(f"https://{MODEL_HOST}/", PROXY),
        "proxy_origin_form_open_relay": http(f"{PROXY}/https://{BLOCKED_HOST}/", None),
        "proxy_origin_form_model_path_no_key": http(f"{PROXY}/v1/models", None),
    }
    # Lateral-move control: the proxy's OTHER (bridge-side) address is the one
    # interface on this host that has an uplink. If the worker can reach it, the
    # allowlist is decorative.
    bridge_ip = os.environ.get("A0TL_BRIDGE_PROXY_IP")
    if bridge_ip:
        probes["lateral_tcp_proxy_bridge_side_8787"] = tcp(bridge_ip, 8787)
        probes["lateral_tcp_docker_bridge_gateway_443"] = tcp("172.17.0.1", 443)
    return probes


# ----------------------------------------------------------- P4 candidate ---
def probe_candidate(work: Path) -> dict:
    """Spawn a child process that runs candidate code, then run E* itself.

    E* is the frozen evaluator; it executes the candidate in a *child* process
    of its own (`e_star_child.py`), so this is the candidate-subprocess path the
    study actually depends on, not a stand-in.
    """
    cstar = WORK_ROOT / "a0/tasks/circle-packing/C_STAR/c02_baseline_upstream"
    cand = work / "cand_c02"
    cand.mkdir(parents=True, exist_ok=True)
    source = cstar / "solution.py"
    if not source.is_file():
        return {"candidate_dir": str(cand), "source": str(source),
                "error": "the C* candidate source is not mounted in this container"}
    for name in ("solution.py",):
        (cand / name).write_bytes(source.read_bytes())

    child = sh([sys.executable, "-c",
                "import sys; sys.path.insert(0, %r); import solution; "
                "print('CANDIDATE-CHILD-OK', sum(r for _, _, r in solution.pack_circles(26)))"
                % str(cand)])
    e_star_python = WORK_ROOT / "a0/tasks/circle-packing/.venv/bin/python"
    e_star_script = WORK_ROOT / "a0/tasks/circle-packing/e_star.py"
    out_json = work / "cand_c02.outcome.json"
    e_star_py = str(e_star_python) if e_star_python.is_file() else sys.executable
    evaluate = sh([e_star_py, str(e_star_script), "evaluate",
                   "--candidate", str(cand), "--seed", "1337", "--fidelity", "full",
                   "--fraction", "1.0", "--n", "26", "--runs", "5",
                   "--out", str(out_json)])
    outcome = None
    if out_json.is_file():
        try:
            outcome = json.loads(out_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            outcome = {"unreadable": str(exc)}
    return {
        "candidate_dir": str(cand),
        "child_process": child,
        "e_star_python": e_star_py,
        "e_star": evaluate,
        "outcome_status": (outcome or {}).get("status"),
        "outcome_fields": (outcome or {}).get("fields"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="/work/wd/inlane_probe.json")
    parser.add_argument("--work", default=None,
                        help="scratch directory for the shell/candidate probes "
                             "(default: the directory holding --out)")
    args = parser.parse_args()

    work = Path(args.work) if args.work else Path(args.out).parent
    work.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "a0.ttoolloop.inlane_probe/v1",
        "when": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "container_hostname": socket.gethostname(),
        "proxy_url": PROXY,
        "p1_shell": probe_shell(work),
        "p2_dns": probe_dns(),
        "p3_http": probe_http(),
        "p4_candidate": probe_candidate(work),
    }
    text = json.dumps(result, indent=1, sort_keys=True)
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
