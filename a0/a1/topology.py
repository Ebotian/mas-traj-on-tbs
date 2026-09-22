"""The A1 closed topology: `unshare -rn`, and one metered uplink.

**The shape.**  A1 requires that the runtime under test have no way to reach a
model except through the metering proxy, because the budget claim
(``INTERFACE.md`` principle (iv)) is otherwise unenforceable.

```
   host netns                              │  new netns (unshare -rn)
   ─────────────────────────────────────── │ ─────────────────────────────────────
   meter_proxy  TCP 127.0.0.1:PORT         │  runtime under test
        ▲                                   │        │  base_url =
        │ TCP (loopback, host netns)         │        │  http://127.0.0.1:PORT/v1
   unix_relay  /run/a0a1/<campaign>.sock ───┼────────┘  (TCP 127.0.0.1:PORT)
                                            │  forwarder: TCP -> unix socket
                                            │
                                            │  no route except loopback
```

The fork in that picture is the whole mechanism.  A network namespace has its own
loopback, so a TCP listener on the host is unreachable from inside — but a
**unix domain socket is a filesystem object**, and the filesystem is shared.  The
runtime therefore reaches the meter over the unix socket and nothing else, and
the probe in ``probe_netns`` shows every other destination failing with
``Network is unreachable``.

This is the ``unshare -rn`` arm of the assignment's "closed topology
(``unshare -rn`` or the allowlist network)".  It is preferred over the docker
``--internal`` topology recorded in ``a0/notes/exit-closed/proxy-closure/`` for
one measured reason: the campaign runs against the *host's* interpreter and the
host's virtualenvs, so no image has to reproduce KAPSO's C extensions.  The
closure property is the same one — one reachable peer, chosen by the harness —
and it is probed, not asserted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_RUNTIME_DIR = Path(os.environ.get("A0A1_RUNTIME_DIR", "/tmp/a0a1"))
LOOPBACK_IP_LITERALS = ("123.148.116.184", "1.1.1.1", "8.8.8.8")


def _splice(left: socket.socket, right: socket.socket) -> None:
    try:
        while True:
            data = left.recv(65536)
            if not data:
                break
            right.sendall(data)
    except OSError:
        pass
    finally:
        for sock in (left, right):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# host side: unix socket -> TCP (the metering proxy)
# ---------------------------------------------------------------------------
class UnixRelay:
    """Listen on a unix socket; each connection becomes a connection to `target`.

    The relay is a byte pump and nothing else: it cannot see, alter or meter the
    HTTP.  All policy lives in the metering proxy on the far side.
    """

    def __init__(self, sock_path: Path, target: tuple[str, int]):
        self.sock_path = Path(sock_path)
        self.target = target
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._server: Optional[socket.socket] = None

    def start(self) -> None:
        self.sock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.sock_path.exists():
            self.sock_path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.sock_path))
        os.chmod(self.sock_path, 0o777)
        server.listen(64)
        server.settimeout(0.2)
        self._server = server

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    client, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    upstream = socket.create_connection(self.target, timeout=15)
                except OSError:
                    client.close()
                    continue
                threading.Thread(target=_splice, args=(client, upstream), daemon=True).start()
                threading.Thread(target=_splice, args=(upstream, client), daemon=True).start()

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# namespace side: TCP -> unix socket
# ---------------------------------------------------------------------------
def forwarder_main(argv: Optional[list] = None) -> int:
    """`python -m a0.a1.topology forwarder --port P --sock S` (inside the netns)."""
    parser = argparse.ArgumentParser(prog="a0a1-forwarder")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--sock", required=True)
    parser.add_argument("--ready-file", default=None)
    args = parser.parse_args(argv)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", args.port))
    server.listen(64)
    if args.ready_file:
        Path(args.ready_file).write_text("ready\n", encoding="utf-8")

    while True:
        client, _ = server.accept()
        try:
            upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            upstream.connect(args.sock)
        except OSError:
            client.close()
            continue
        threading.Thread(target=_splice, args=(client, upstream), daemon=True).start()
        threading.Thread(target=_splice, args=(upstream, client), daemon=True).start()


# ---------------------------------------------------------------------------
# running inside the namespace
# ---------------------------------------------------------------------------
def netns_prefix(*, up_lo: bool = True) -> list:
    """The argv prefix that puts a command in a fresh, uplink-free namespace."""
    if shutil.which("unshare") is None:
        raise RuntimeError("`unshare` is not on PATH; the closed topology cannot be entered")
    inner = "ip link set lo up && exec \"$@\"" if up_lo else 'exec "$@"'
    return ["unshare", "-rn", "sh", "-c", inner, "sh"]


def run_in_netns(command: list, *, cwd: Optional[Path] = None, env: Optional[dict] = None,
                 timeout: float = 600.0, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        netns_prefix() + list(command),
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )


PROBE_SCRIPT = r"""
import json, socket, sys
report = {"mechanism": "unshare -rn"}
for host in (__HOSTS__):
    try:
        socket.create_connection((host, 443), timeout=4).close()
        report[host] = "REACHED"
    except OSError as exc:
        report[host] = "BLOCKED:" + type(exc).__name__
try:
    socket.getaddrinfo("api.deepseek.com", 443)
    report["dns:api.deepseek.com"] = "resolved"
except OSError as exc:
    report["dns:api.deepseek.com"] = "BLOCKED:" + type(exc).__name__
print(json.dumps(report))
""".replace("__HOSTS__", ", ".join(repr(host) for host in LOOPBACK_IP_LITERALS))


def probe_netns(*, expected_meter_port: Optional[int] = None,
                timeout: float = 60.0) -> dict:
    """Execute the egress probe inside a fresh namespace and return its report.

    Two controls in one run, so "blocked" is a measurement and not a default:
    the negative controls are the bare IP literals; when `expected_meter_port` is
    given, the positive control is the local forwarder, which must be reached.
    """
    script = PROBE_SCRIPT
    if expected_meter_port:
        script += (
            "\nPORT=" + str(int(expected_meter_port)) + "\n"
            "try:\n"
            "    socket.create_connection(('127.0.0.1', PORT), timeout=4).close()\n"
            "    report['meter_loopback'] = 'REACHED'\n"
            "except OSError as exc:\n"
            "    report['meter_loopback'] = 'BLOCKED:' + type(exc).__name__\n"
            "print(json.dumps(report))\n"
        )
    proc = run_in_netns([sys.executable, "-c", script], timeout=timeout)
    line = (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else "{}"
    report = json.loads(line)
    negative = [k for k in LOOPBACK_IP_LITERALS]
    blocked = all(str(report.get(k, "")).startswith("BLOCKED") for k in negative)
    report["_negative_controls_blocked"] = blocked
    if expected_meter_port:
        report["_meter_reachable"] = report.get("meter_loopback") == "REACHED"
    return report


# ---------------------------------------------------------------------------
# one campaign's uplink
# ---------------------------------------------------------------------------
@dataclass
class CampaignUplink:
    """The host-side half: a unix relay in front of the campaign's meter port."""

    campaign_id: str
    meter_port: int
    runtime_dir: Path = DEFAULT_RUNTIME_DIR
    sock_path: Path = None  # type: ignore[assignment]

    def start(self) -> Path:
        self.sock_path = self.runtime_dir / f"{self.campaign_id}.sock"
        self.relay = UnixRelay(self.sock_path, ("127.0.0.1", self.meter_port))
        self.relay.start()
        return self.sock_path

    def stop(self) -> None:
        if getattr(self, "relay", None) is not None:
            self.relay.stop()

    def forwarder_command(self, *, port: Optional[int] = None) -> list:
        """The argv the runtime's namespace runs to expose the meter on loopback."""
        return [
            sys.executable,
            "-m",
            "a0.a1.topology",
            "forwarder",
            "--port",
            str(port or self.meter_port),
            "--sock",
            str(self.sock_path),
        ]

    def enter_command(self, arm_command: list, *, port: Optional[int] = None) -> list:
        """`unshare -rn` + the loopback forwarder + the arm.

        The arm therefore starts in a namespace whose only reachable peer is the
        campaign's metering port, and its `base_url` is
        ``http://127.0.0.1:<port>/v1``.
        """
        inner = [
            sys.executable,
            "-m",
            "a0.a1.topology",
            "enter",
            "--port",
            str(port or self.meter_port),
            "--sock",
            str(self.sock_path),
            "--",
        ] + list(arm_command)
        return netns_prefix() + inner


def enter_main(argv: Optional[list] = None) -> int:
    """Run a command inside the namespace, with the meter exposed on loopback.

    Called *inside* `unshare -rn`: it starts the TCP->unix forwarder on a thread
    and then `exec`s the arm, so the arm's process tree is the one the probe
    measures.
    """
    parser = argparse.ArgumentParser(prog="a0a1-enter")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--sock", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = [item for item in args.command if item != "--"]
    if not command:
        parser.error("no command given")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", args.port))
    server.listen(64)

    def loop() -> None:
        while True:
            try:
                client, _ = server.accept()
            except OSError:
                return
            try:
                upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                upstream.connect(args.sock)
            except OSError:
                client.close()
                continue
            threading.Thread(target=_splice, args=(client, upstream), daemon=True).start()
            threading.Thread(target=_splice, args=(upstream, client), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    # Not `execvp`: Python sockets are created `CLOEXEC`, so an exec would close
    # the listening socket and the forwarder would vanish with a
    # ConnectionRefused (measured). The command runs as a child and this process
    # waits, which also keeps the process group the same for the probes.
    completed = subprocess.run(command)
    return completed.returncode


def wait_for_port(host: str, port: int, *, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.topology")
    sub = parser.add_subparsers(dest="command", required=True)
    fwd = sub.add_parser("forwarder")
    fwd.add_argument("--port", type=int, required=True)
    fwd.add_argument("--sock", required=True)
    fwd.add_argument("--ready-file", default=None)
    fwd.set_defaults(fn=lambda a: forwarder_main(["--port", str(a.port), "--sock", a.sock]
                                                 + (["--ready-file", a.ready_file] if a.ready_file else [])))
    probe = sub.add_parser("probe")
    probe.add_argument("--meter-port", type=int, default=None)
    probe.set_defaults(fn=lambda a: (print(json.dumps(probe_netns(expected_meter_port=a.meter_port),
                                                      indent=1)), 0)[1])
    ent = sub.add_parser("enter", help="start the loopback forwarder, then exec a command")
    ent.add_argument("--port", type=int, required=True)
    ent.add_argument("--sock", required=True)
    ent.add_argument("command", nargs=argparse.REMAINDER)
    ent.set_defaults(fn=lambda a: enter_main(["--port", str(a.port), "--sock", a.sock, "--"]
                                             + [c for c in a.command if c != "--"]))
    args = parser.parse_args(argv)
    result = args.fn(args)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
