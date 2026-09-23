#!/usr/bin/env python3
"""Mechanism C's in-container probe: what exists, what is reachable, from inside.

Runs INSIDE the agent container (nothing outside is imported, so the container
needs only its own python3).  Writes one JSON report, so a claim about the
container's view is a file rather than an assertion.

Two design points that make the "absent" results measurements rather than
defaults:

* **A visibility control.**  Two canary files are planted by ``run.sh``: one in
  the session workspace (mounted into the container) and one on the host at a
  path that is *not* mounted.  The walk must find the first and must not find
  the second.  If it finds neither, the walk is broken and every "absent" below
  is worthless; the report says so explicitly via ``_walk_control_ok``.
* **Named negative and positive controls on the network.**  Egress checks are
  bare IP literals (no DNS to mask the result) and the metering listener is
  probed on the same code path, so "unreachable" and "reachable" are produced by
  one implementation.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# configuration, all from the environment
# ---------------------------------------------------------------------------
VARIANT = os.environ.get("A0EC_VARIANT", "C1")
METER_URL = os.environ.get("A0EC_METER_URL", "http://a0ec-meter:8801")
SCAN_SUBNET = os.environ.get("A0EC_SCAN_SUBNET", "172.31.78")
CANARY_VISIBLE = os.environ.get("A0EC_CANARY_VISIBLE", "a0ec-canary-visible.txt")
CANARY_HOST_ONLY = os.environ.get("A0EC_CANARY_HOST_ONLY", "a0ec-canary-host-only.txt")
WORKSPACE = os.environ.get("A0EC_WORKSPACE", "/workspace")

REPO = "/home/ebt/rsi-dev"

#: Absolute paths that hold, or route to, experimenter-only facts.  Every one of
#: these is opened (not merely stat'ed) below.
LEAK_TARGETS = [
    # the provider key, and the home tree that carries it
    "/home/ebt/gptapi.md",
    "/home/ebt",
    f"{REPO}",
    f"{REPO}/.git",
    # the answer stores
    f"{REPO}/a0/tasks/maxcut/references/targets.json",
    f"{REPO}/a0/tasks/maxcut/references/witnesses/commitments.json",
    f"{REPO}/a0/tasks/maxcut/references/witnesses/fs_policy.json",
    f"{REPO}/a0/tasks/maxcut/suite/eval/G_eval_0001.json",
    f"{REPO}/a0/tasks/maxcut/suite/eval",
    f"{REPO}/a0/tasks/maxcut/suite",
    # the reviewer's own tree, and the harness's other halves
    f"{REPO}/a0/a1/kapso_t1",
    f"{REPO}/a0/meter/meter_proxy.py",
    "/home/ebt/kapso_ck",
    "/tmp/eve",
    "/tmp/a0ec",
    # agent state that would carry a credential or a live session
    "/home/ebt/.codex/auth.json",
    "/home/ebt/.codex/config.toml",
    "/root/.codex",
    # container control planes that would dissolve the boundary
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/run/containerd/containerd.sock",
]

#: Names searched for across the whole visible filesystem.  Finding any of the
#: first group inside the container is a leak; the canaries are the control.
BASENAME_LEAKS = ["targets.json", "commitments.json", "fs_policy.json",
                  "G_eval_0001.json", "benchmarks.json", "R_source.json"]
BASENAME_CONTROLS = [CANARY_VISIBLE, CANARY_HOST_ONLY]
DIRNAME_LEAKS = [".git", "witnesses", "references"]

EGRESS_LITERALS = [("123.148.116.184", 443), ("1.1.1.1", 443), ("8.8.8.8", 53),
                   ("140.82.121.4", 443)]
#: Addresses belonging to networks the agent container is *not* on: the default
#: bridge gateway and the pre-existing containers' network.  Reaching any of
#: them would mean the boundary leaked sideways.
LATERAL = [("172.17.0.1", 443), ("172.17.0.1", 5432), ("172.17.0.2", 5432),
           ("127.0.0.1", 5433), ("127.0.0.1", 2375)]
SCAN_PORTS = [80, 443, 2375, 5432, 5433, 6379, 8801, 8802]

SKIP_DIRS = {"/proc", "/sys", "/dev"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def tcp(host: str, port: int, timeout: float = 3.0) -> str:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return "REACHED"
    except OSError as exc:
        return "BLOCKED:%s" % type(exc).__name__


def dns(name: str) -> str:
    try:
        return "resolved:%s" % (socket.getaddrinfo(name, 443)[0][4][0],)
    except OSError as exc:
        return "BLOCKED:%s" % type(exc).__name__


def http_get(url: str, timeout: float = 8.0) -> dict:
    """A raw HTTP/1.1 GET, so the probe needs no third-party client."""
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    host, port = parts.hostname, parts.port or 80
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        return {"error": "connect:%s" % type(exc).__name__}
    try:
        req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nAccept: */*\r\n"
               "Connection: close\r\n\r\n" % (parts.path or "/", host, port))
        sock.sendall(req.encode())
        raw = b""
        sock.settimeout(timeout)
        while len(raw) < 65536:
            chunk = sock.recv(4096)
            if not chunk:
                break
            raw += chunk
    except OSError as exc:
        return {"error": "io:%s" % type(exc).__name__}
    finally:
        sock.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    status = head.split(b"\r\n", 1)[0].decode("latin-1") if head else ""
    return {"status_line": status, "body_head": body[:200].decode("utf-8", "replace")}


def walk_visible() -> dict:
    """Every path under / except the kernel filesystems, plus name hits."""
    files, dirs = [], []
    hit_files, hit_dirs = [], []
    for root, subdirs, names in os.walk("/", topdown=True, onerror=lambda e: None):
        subdirs[:] = [d for d in subdirs if os.path.join(root, d) not in SKIP_DIRS]
        dirs.append(root)
        for name in names:
            path = os.path.join(root, name)
            files.append(path)
            if name in BASENAME_LEAKS or name in BASENAME_CONTROLS:
                hit_files.append(path)
        for name in list(subdirs):
            if name in DIRNAME_LEAKS:
                hit_dirs.append(os.path.join(root, name))
    return {"n_dirs": len(dirs), "n_files": len(files),
            "name_hits": sorted(hit_files), "dir_hits": sorted(hit_dirs)}


def proc_view() -> dict:
    pids = sorted(int(p) for p in os.listdir("/proc") if p.isdigit())
    cmdlines = {}
    for pid in pids:
        try:
            cmdlines[str(pid)] = Path("/proc/%d/cmdline" % pid).read_bytes().replace(
                b"\0", b" ").decode("utf-8", "replace").strip()[:200]
        except OSError:
            pass
    return {"n_pids": len(pids), "pids": pids[:40], "cmdlines": cmdlines}


def read_file(path: str, limit: int = 4096) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError as exc:
        return "ERR:%s" % exc


def scan_ports() -> dict:
    """Bounded parallel sweep of the campaign subnet for live listeners."""
    targets = []
    if SCAN_SUBNET:
        for last in range(1, 255):
            for port in SCAN_PORTS:
                targets.append(("%s.%d" % (SCAN_SUBNET, last), port))
    for host, port in LATERAL:
        targets.append((host, port))

    found: dict[str, str] = {}
    lock = threading.Lock()
    index = [0]

    def worker() -> None:
        while True:
            with lock:
                if index[0] >= len(targets):
                    return
                host, port = targets[index[0]]
                index[0] += 1
            result = tcp(host, port, timeout=0.7)
            if result == "REACHED":
                with lock:
                    found["%s:%d" % (host, port)] = "REACHED"

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(96)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=180)
    return {"probed": len(targets), "listeners_found": dict(sorted(found.items()))}


def codex_version() -> str:
    for argv in (["codex", "--version"], ["/usr/local/bin/codex", "--version"]):
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
            return (proc.stdout + proc.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
    return "ERR:%s" % last


# ---------------------------------------------------------------------------
def main() -> int:
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path(
        "/workspace/probe.json")
    report: dict = {"variant": VARIANT, "meter_url": METER_URL}

    report["identity"] = {"uid_gid": "%d:%d" % (os.getuid(), os.getgid()),
                          "hostname": socket.gethostname(),
                          "cwd": os.getcwd(),
                          "codex": codex_version()}

    # 1. what is visible
    walk = walk_visible()
    report["walk"] = walk
    visible_hits = [p for p in walk["name_hits"] if CANARY_VISIBLE in p]
    host_hits = [p for p in walk["name_hits"] if CANARY_HOST_ONLY in p]
    leak_hits = [p for p in walk["name_hits"] if Path(p).name in BASENAME_LEAKS]
    report["_walk_control_ok"] = bool(visible_hits) and not host_hits
    report["_leak_basenames_found"] = leak_hits
    report["_leak_dirs_found"] = walk["dir_hits"]

    # 2. open each named leak target (stat is weaker than read)
    attempts = {}
    for path in LEAK_TARGETS:
        entry: dict = {}
        try:
            with open(path, "rb") as handle:
                entry["opened"] = True
                entry["first_bytes"] = handle.read(32).decode("utf-8", "replace")
        except IsADirectoryError:
            entry["opened"] = True
            entry["note"] = "directory_listable:%s" % sorted(os.listdir(path))[:10]
        except OSError as exc:
            entry["opened"] = False
            entry["errno"] = exc.errno
            entry["error"] = "%s: %s" % (type(exc).__name__, exc.strerror)
        entry["exists"] = os.path.exists(path)
        attempts[path] = entry
    report["read_attempts"] = attempts
    report["_opened_count"] = sum(1 for v in attempts.values() if v.get("opened"))

    # 2b. the positive control for the read path: the visible canary must OPEN,
    # not merely be found by the walk.  Without this, "opened=False" everywhere
    # could be a broken open(), not an absent file.
    control_path = os.path.join(WORKSPACE, CANARY_VISIBLE)
    try:
        with open(control_path, "rb") as handle:
            report["_read_control_ok"] = True
            report["_read_control_body"] = handle.read(64).decode("utf-8", "replace")
    except OSError as exc:
        report["_read_control_ok"] = False
        report["_read_control_body"] = "%s: %s" % (type(exc).__name__, exc)

    # 3. the container's own mount table and network view
    report["mounts"] = read_file("/proc/self/mountinfo", 20000)
    report["etc_hosts"] = read_file("/etc/hosts")
    report["resolv_conf"] = read_file("/etc/resolv.conf")
    report["proc_net_route"] = read_file("/proc/net/route")
    report["proc_net_dev"] = read_file("/proc/net/dev")
    report["hosts_seen"] = {"meter_name": dns("a0ec-meter"),
                            "api.deepseek.com": dns("api.deepseek.com"),
                            "example.com": dns("example.com")}

    # 4. processes
    report["proc"] = proc_view()

    # 5. network: negatives, laterals, positive, and the sweep
    report["egress_literals"] = {"%s:%d" % hp: tcp(*hp) for hp in EGRESS_LITERALS}
    report["lateral"] = {"%s:%d" % hp: tcp(*hp, timeout=2.0) for hp in LATERAL}
    report["positive_meter_http"] = http_get(METER_URL + "/v1/models")
    meter_host = os.environ.get("A0EC_METER_HOST", "")
    if meter_host:
        host, _, port = meter_host.partition(":")
        report["positive_meter_tcp"] = tcp(host, int(port), timeout=4.0)
    report["scan"] = scan_ports()

    # 6. escape attempts.  /proc/1/root is the classic route out of a mount
    # namespace that shares a kernel; here PID 1 is the container's own init, so
    # the route must land back inside the same container.
    def ls(path: str) -> list:
        try:
            return sorted(os.listdir(path))[:40]
        except OSError as exc:
            return ["ERR:%s" % type(exc).__name__]

    environ = b""
    try:
        environ = Path("/proc/1/environ").read_bytes()
    except OSError:
        pass
    report["escape_attempts"] = {
        "/proc/1/cmdline": read_file("/proc/1/cmdline").replace("\0", " "),
        "/proc/1/root listing": ls("/proc/1/root"),
        "/proc/1/root/home": ls("/proc/1/root/home"),
        "/proc/1/root/tmp": ls("/proc/1/root/tmp"),
        "/proc/1/root/workspace": ls("/proc/1/root/workspace"),
        "proc1_environ_has_DS_KEY": b"DS_KEY" in environ,
        "/proc/self/cgroup": read_file("/proc/self/cgroup"),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k.startswith("_")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
