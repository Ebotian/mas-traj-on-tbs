#!/usr/bin/env python3
"""What a CLI session can see from *inside* the agent lane.  Runs under `session_sandbox`.

Prints one JSON object.  Every "hidden" verdict is paired with a read attempt, because
"the path does not exist" is only a boundary if the path *does* exist on the host — the
outer probe records that control.  Nothing here prints file contents; the answer stores
are only opened, never read.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def _readable(path: str) -> dict:
    """Does a process at this path resolve it, and can it open it?"""
    entry = {"path": path, "exists": False, "opened": False}
    try:
        entry["exists"] = os.path.exists(path)
    except OSError as exc:
        entry["exists_error"] = type(exc).__name__
    try:
        with open(path, "rb") as handle:
            handle.read(1)
        entry["opened"] = True
    except OSError as exc:
        entry["open_error"] = type(exc).__name__
    except Exception as exc:  # noqa: BLE001
        entry["open_error"] = type(exc).__name__
    return entry


def _listing(path: str) -> dict:
    entry = {"path": path, "exists": False, "entries": None}
    try:
        entry["exists"] = os.path.isdir(path)
        if entry["exists"]:
            entry["entries"] = sorted(os.listdir(path))[:12]
    except OSError as exc:
        entry["error"] = type(exc).__name__
    return entry


def _version(binary: str) -> dict:
    found = shutil.which(binary) or binary
    try:
        proc = subprocess.run([found, "--version"], capture_output=True, text=True, timeout=60)
        return {"binary": binary, "resolved": found, "returncode": proc.returncode,
                "stdout": proc.stdout.strip()[:200], "stderr": proc.stderr.strip()[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"binary": binary, "resolved": found, "error": type(exc).__name__ + ":" + str(exc)[:200]}


def _egress(hosts=("1.1.1.1", "8.8.8.8", "123.148.116.184"), port: int = 443) -> dict:
    report = {}
    for host in hosts:
        try:
            socket.create_connection((host, port), timeout=3).close()
            report[host] = "REACHED"
        except OSError as exc:
            report[host] = "BLOCKED:" + type(exc).__name__
    try:
        socket.getaddrinfo("api.deepseek.com", 443)
        report["dns:api.deepseek.com"] = "resolved"
    except OSError as exc:
        report["dns:api.deepseek.com"] = "BLOCKED:" + type(exc).__name__
    return report


def _meter(port: int) -> dict:
    """End-to-end: an HTTP GET through the loopback forwarder must reach the metering proxy.

    A bare `connect()` would only prove the *forwarder* is listening; the request must
    come back from the proxy (which routes `/v1/models` and books it unmetered by design)
    for the lane to be one that can actually spend.
    """
    import http.client
    out = {"port": int(port)}
    try:
        conn = http.client.HTTPConnection("127.0.0.1", int(port), timeout=8)
        conn.request("GET", "/v1/models")
        resp = conn.getresponse()
        body = resp.read(64)
        out.update({"reachable": True, "status": resp.status, "body_prefix": body[:32].decode("utf-8", "replace")})
        conn.close()
    except OSError as exc:
        out.update({"reachable": False, "error": type(exc).__name__ + ":" + str(exc)[:120]})
    return out


def _git_route(repo: str) -> dict:
    """The git-objects route: a reader with repo access can `git cat-file` a sealed blob."""
    out = {"repo": repo, "executed": False}
    if not os.path.isdir(repo):
        out["reason"] = "repo path is not present inside the lane"
        return out
    try:
        proc = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30)
        out["executed"] = True
        out["returncode"] = proc.returncode
        out["stderr"] = proc.stderr.strip()[:200]
    except Exception as exc:  # noqa: BLE001
        out["error"] = type(exc).__name__
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="probe_inside")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--meter-port", type=int, default=None)
    parser.add_argument("--session-home", default=None)
    parser.add_argument("--workspace", default=None)
    args = parser.parse_args(argv)

    repo = args.repo_root
    forbidden = [
        repo,
        os.path.join(repo, ".git"),
        os.path.join(repo, "a0", "tasks", "maxcut", "references", "targets.json"),
        os.path.join(repo, "a0", "tasks", "maxcut", "suite", "eval", "G_eval_0001.json"),
        os.path.join(repo, "a0", "tasks", "maxcut", "references", "witnesses", "commitments.json"),
        os.path.join(os.path.dirname(repo), "gptapi.md"),
        os.path.join(os.path.dirname(repo), ".codex"),
        os.path.join(os.path.dirname(repo), ".claude"),
        "/tmp/maxcut",
    ]
    report = {
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "home_env": os.environ.get("HOME"),
        "uid": os.getuid(),
        "nproc_visible": os.cpu_count(),
        "forbidden": {path: {"read": _readable(path)} for path in forbidden},
        "listings": {
            "/home": _listing("/home"),
            "/home/ebt": _listing(os.path.dirname(repo)),
            "/tmp": _listing("/tmp"),
            os.path.dirname(repo): _listing(os.path.dirname(repo)),
        },
        "binaries": {"codex": _version("codex"), "claude": _version("claude")},
        "egress": _egress(),
        "git_route": _git_route(repo),
        "can_write_home": None,
        "can_write_workspace": None,
    }
    if args.session_home:
        try:
            probe = Path(args.session_home) / ".session_probe"
            probe.write_text("ok", encoding="utf-8")
            report["can_write_home"] = probe.read_text(encoding="utf-8") == "ok"
            probe.unlink()
        except OSError as exc:
            report["can_write_home"] = False
            report["session_home_error"] = type(exc).__name__
    if args.workspace:
        try:
            probe = Path(args.workspace) / ".session_probe"
            probe.write_text("ok", encoding="utf-8")
            report["can_write_workspace"] = probe.read_text(encoding="utf-8") == "ok"
            probe.unlink()
        except OSError as exc:
            report["can_write_workspace"] = False
            report["workspace_error"] = type(exc).__name__
    if args.meter_port:
        report["meter"] = _meter(args.meter_port)

    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
