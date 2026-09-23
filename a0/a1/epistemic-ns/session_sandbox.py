"""The agent lane's epistemic namespace: a long-lived CLI session with the repo hidden.

**Why this exists.**  `a0/a1/candidate_sandbox.py` closes the *candidate* lane: the
program under test runs in `unshare -rmnpf` with `/home`, `/tmp`, `/var/tmp` and
`/run/user` covered by fresh tmpfs, so it can read neither the stored answers nor
the provider key.  It does **not** close the *agent* lane — the CLI session that
*writes* the candidate.  Measured (`a0/EPISTEMIC-REVIEW.md` §3.1): under the T1
config's `coding_agent.agent_specific.sandbox = danger-full-access`, `codex sandbox
-c sandbox_mode='"workspace-write"'` still reads `references/targets.json` (R/OPT/U/
R_source/role) and the held-out graph `suite/eval/G_eval_0001.json`.  `workspace-write`
is a write-and-network restriction, not a read jail; only a mount namespace hides
files from a process, and the agent processes had never been put in one.

**What it does.**  One process stack per CLI session:

```
   unshare -rmnpf --mount-proc        user + mount + net + PID namespace
     ├─ mount --make-rprivate /       nothing propagates back to the host
     ├─ ip link set lo up             the fresh netns' own loopback
     ├─ stage the allow-list          bind the session's own inputs aside
     ├─ hide the roots                a fresh tmpfs over each of /home, /tmp,
     │                                /var/tmp, /run/user (same code the candidate
     │                                lane uses — imported, not re-implemented)
     ├─ restore the allow-list        bind them back at their real paths
     ├─ start the meter forwarder     TCP 127.0.0.1:<port> -> unix socket
     └─ run the CLI                   `codex exec …` / `claude -p …`, as a child
```

The mount half is `a0/a1/candidate_sandbox.py`'s, imported whole: the same
unconditional tmpfs-over-the-root, the same "the covering mount must be a tmpfs of
*this* namespace with a new mount id, the device changed, and the root empty" check
(that check is the repair for the host's own tmpfs `/tmp`, which an earlier revision
mistook for "already hidden").  What this module adds is the session concerns the
candidate lane never had:

* **network** — the candidate lane is *fully* air-gapped; an agent lane is not.  A
  CLI session must reach exactly one peer, its campaign's meter, and nothing else.
  A fresh netns has its own loopback, so a host TCP listener is unreachable — but a
  **unix domain socket is a filesystem object**, so the session reaches the meter
  over a socket the filesystem carries, exposed on loopback by an in-namespace
  forwarder.  This is `a0/a1/topology.py`'s shape, folded into the same PID-1
  supervisor instead of a second process (the second `python -m` would have to be
  re-imported *after* `/home` is hidden, and the repo is under `/home`).
* **its own `HOME` and config** — `CODEX_HOME` / `CLAUDE_CONFIG_DIR` point at a
  session directory the harness owns, bind-mounted back, so the CLI can write its
  sessions, rollouts and logs while `$HOME/.codex` and `$HOME/.claude` stay hidden.
* **a writable workspace** — the directory the agent edits, bound back at its real
  path.

**Fail-closed, as the candidate lane is.**  If `unshare` is missing, if a mount
fails, if the lane's mount table cannot be read, if a hidden root is not a fresh
tmpfs of this lane's own, if the network is reachable, if there is no PID namespace,
or if the meter forwarder is not actually reachable from inside, the sandbox exits
non-zero and the harness must not measure.  The self-check is written to a receipt
*before* the CLI runs.

**The residual, stated rather than implied.**  This is a mount/PID/network namespace
boundary, not a VM: the session shares the kernel and the host's `/usr`, `/lib`,
`/etc`, `/opt` and `/dev`, and keeps the harness's uid.  It hides *files under the
hidden roots*; it does not defend against a kernel exploit.  Its enforcement is the
launch: a session started through `prefix()` cannot leave the mount namespace
(no other namespace is reachable through the fresh `/proc`), but a session the
driver starts *without* `prefix()` is unconstrained.  That is a property of the
harness's launch site, and the report says so where it matters.

**Use.**

```python
from a0.a1.epistemic_ns.session_sandbox import prefix
argv = prefix(["/usr/bin/codex", "exec", "--skip-git-repo-check", "-"],
              allow=[workspace, session_home],
              meter_port=8801, relay_sock=Path("/run/a0a1/c.sock"),
              receipt=run_dir / "session_receipt.json")
subprocess.run(argv, env=cli_env, ...)
```
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
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The mount boundary is the candidate lane's, imported whole.  Import-time only:
# this module is already in memory before `_hide` covers `/home`.
from a0.a1.candidate_sandbox import (  # noqa: E402
    DEFAULT_HIDDEN_ROOTS,
    EXIT_SANDBOX_REFUSED,
    SandboxError,
    _hide,
    _pid_namespace_state,
    _restore,
    _self_check,
    _stage_allow,
    _stage_dir,
    _write_receipt,
    available,
    interpreter_roots,
    mount,
    MS_PRIVATE,
    MS_REC,
)

SCHEMA_RECEIPT = "a0.a1.session_sandbox/v1"
UNSHARE = shutil.which("unshare")


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


def _bring_up_loopback() -> Dict[str, Any]:
    """A fresh netns' loopback is DOWN; the forwarder cannot bind 127.0.0.1 until it is up."""
    ip = shutil.which("ip")
    if ip is None:
        return {"ok": False, "reason": "`ip` not on PATH"}
    proc = subprocess.run([ip, "link", "set", "lo", "up"], capture_output=True, text=True)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "stderr": (proc.stderr or "").strip()}


def _start_forwarder(port: int, sock_path: str) -> socket.socket:
    """Expose the campaign's meter on this namespace's loopback.

    The bytes go: CLI -> 127.0.0.1:<port> (this socket) -> the unix socket the host
    relay listens on -> the host's metering proxy.  The relay and the forwarder are
    byte pumps; every policy decision stays in the proxy on the host side.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", int(port)))
    server.listen(64)
    server.settimeout(0.2)

    def loop() -> None:
        while True:
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                upstream.connect(sock_path)
            except OSError:
                client.close()
                continue
            threading.Thread(target=_splice, args=(client, upstream), daemon=True).start()
            threading.Thread(target=_splice, args=(upstream, client), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return server


def _meter_reachable(port: int, *, timeout: float = 3.0) -> Dict[str, Any]:
    """Can a process inside this namespace open the forwarder's loopback port?

    This proves the *forwarder* is listening; the end-to-end path (through the unix
    relay to the metering proxy and back) is a separate probe in the harness, because
    a reachable port with a dead relay would still be a lane that cannot spend.
    """
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=timeout).close()
        return {"port": int(port), "reachable": True}
    except OSError as exc:
        return {"port": int(port), "reachable": False, "error": type(exc).__name__}


def prefix(command: Sequence[str], *, allow: Sequence[Optional[Path]] = (),
           hidden_roots: Sequence[str] = DEFAULT_HIDDEN_ROOTS,
           meter_port: Optional[int] = None, relay_sock: Optional[Path] = None,
           receipt: Optional[Path] = None, python: Optional[Path] = None) -> List[str]:
    """The argv that runs `command` inside the agent lane.

    `allow` is the *whole* of what the session may see at its real path: its workspace,
    its `HOME`/config directory, and its scratch/state directory.  The interpreter's
    own installation directories are added automatically; the system directories
    (`/usr`, `/lib`, `/etc`, `/opt`, `/dev`) are not hidden and need no entry.  The
    relay socket's directory is bound back only when it sits under a hidden root.
    """
    if not available():
        raise SandboxError(
            "`unshare` is not on PATH; the agent lane cannot be closed and the harness "
            "must not measure in an open topology"
        )
    interpreter = Path(python or sys.executable)
    entries: List[Path] = []
    for path in [*[Path(item) for item in allow if item is not None], *interpreter_roots(interpreter)]:
        if path not in entries:
            entries.append(path)
    if relay_sock is not None:
        relay_parent = Path(relay_sock).parent
        if relay_parent.is_dir() and relay_parent not in entries:
            entries.append(relay_parent)
    inner = [str(interpreter), str(Path(__file__).resolve()), "enter"]
    for root in hidden_roots:
        inner += ["--hide", str(root)]
    for path in entries:
        inner += ["--allow", str(path)]
    if meter_port is not None:
        inner += ["--meter-port", str(int(meter_port))]
    if relay_sock is not None:
        inner += ["--relay-sock", str(relay_sock)]
    if receipt is not None:
        inner += ["--receipt", str(receipt)]
    inner += ["--", *[str(part) for part in command]]
    return [str(UNSHARE), "-rmnpf", "--mount-proc", *inner]


def enter(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="session_sandbox enter")
    parser.add_argument("--hide", action="append", default=[])
    parser.add_argument("--allow", action="append", default=[])
    parser.add_argument("--meter-port", type=int, default=None)
    parser.add_argument("--relay-sock", default=None)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = [part for part in args.command if part != "--"]
    if not command:
        parser.error("no command given")

    hidden = [Path(root) for root in args.hide]
    allow = [Path(path) for path in args.allow]
    receipt: Dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "pid": os.getpid(),
        "uid": os.getuid(),
        "hidden_roots_requested": [str(root) for root in hidden],
        "allow_requested": [str(path) for path in allow],
        "meter_port": args.meter_port,
        "relay_sock": args.relay_sock,
        "command": command,
        "pass": False,
    }
    try:
        mount("none", "/", None, MS_REC | MS_PRIVATE, None)
        receipt["loopback"] = _bring_up_loopback()
        staged = _stage_allow(_stage_dir(), allow)
        hiding = _hide(hidden)
        hidden_now = [Path(entry["root"]) for entry in hiding]
        restored = _restore(staged, hidden_now)
        receipt["staged"] = staged
        receipt["hidden_roots"] = [str(root) for root in hidden_now]
        receipt["hiding"] = hiding
        receipt["restored"] = restored

        self_check = _self_check(hiding)
        meter: Optional[Dict[str, Any]] = None
        if args.meter_port is not None and args.relay_sock:
            try:
                _start_forwarder(args.meter_port, args.relay_sock)
            except OSError as exc:
                raise SandboxError(
                    f"cannot expose the meter on this lane's loopback (127.0.0.1:"
                    f"{args.meter_port}): {exc}.  The netns' loopback may be down "
                    f"(loopback step: {receipt.get('loopback')})"
                ) from exc
            meter = _meter_reachable(args.meter_port)
        receipt["self_check"] = self_check
        receipt["meter"] = meter
        if not (self_check["hidden_roots_are_tmpfs"]
                and self_check["hidden_roots_are_the_filesystems_this_lane_made"]
                and self_check["egress_is_blocked"]
                and self_check["pid_namespace_is_private"]):
            raise SandboxError(f"the lane's self-check failed: {self_check}")
        if args.meter_port is not None and args.relay_sock:
            if not meter or not meter.get("reachable"):
                raise SandboxError(f"the meter forwarder is not reachable inside the lane: {meter}")
    except SandboxError as exc:
        receipt["error"] = str(exc)
        _write_receipt(args.receipt, receipt)
        print(f"session_sandbox: refusing to run: {exc}", file=sys.stderr)
        return EXIT_SANDBOX_REFUSED

    receipt["pass"] = True
    _write_receipt(args.receipt, receipt)
    # The supervisor is PID 1: it must stay alive for the forwarder thread, so the
    # CLI is a child rather than an exec.  Its exit code is the lane's exit code.
    try:
        completed = subprocess.run(command)
    except FileNotFoundError as exc:
        print(f"session_sandbox: command not found: {exc}", file=sys.stderr)
        return 127
    return completed.returncode


def shim(argv: List[str]) -> int:
    """The `codex` PATH shim's body: re-launch the real CLI inside the lane.

    This is the enforcement-point half of the *proposal* (never applied to the T1
    config): a harness that puts a shim named `codex` first on the child's `PATH`
    makes every codex the driver launches go through `prefix()`, with no edit to the
    upstream adapter.  The contract is the environment the driver sets:

    ===============================  =========================================
    ``A0_EPISTEMIC_NS_REAL_CODEX``   absolute path of the real CLI (so the shim
                                     cannot recurse; default ``/usr/bin/codex``)
    ``A0_EPISTEMIC_NS_PORT``         the campaign's metered port (omitted => no meter)
    ``A0_EPISTEMIC_NS_SOCK``         the host relay's unix socket
    ``A0_EPISTEMIC_NS_RECEIPT``      where to write the boundary receipt
    ``HOME`` / ``CODEX_HOME``        bound back; ``$PWD`` is the workspace
    ===============================  =========================================
    """
    real = os.environ.get("A0_EPISTEMIC_NS_REAL_CODEX", "/usr/bin/codex")
    port = os.environ.get("A0_EPISTEMIC_NS_PORT")
    sock = os.environ.get("A0_EPISTEMIC_NS_SOCK")
    receipt = os.environ.get("A0_EPISTEMIC_NS_RECEIPT")
    workspace = Path.cwd()
    allow: List[Path] = [workspace]
    home = os.environ.get("HOME")
    if home and Path(home).is_dir():
        allow.append(Path(home))
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home and Path(codex_home).is_dir():
        allow.append(Path(codex_home))
    argv_out = prefix([real, *argv], allow=allow,
                      meter_port=int(port) if port else None,
                      relay_sock=Path(sock) if sock else None,
                      receipt=Path(receipt) if receipt else None)
    os.execv(argv_out[0], argv_out)
    return 0  # unreachable


def describe() -> Dict[str, Any]:
    return {
        "schema": SCHEMA_RECEIPT,
        "available": available(),
        "unshare": UNSHARE,
        "hidden_roots": list(DEFAULT_HIDDEN_ROOTS),
        "namespaces": ["user", "mount", "network", "pid"],
        "mount_boundary_imported_from": "a0/a1/candidate_sandbox.py",
        "meter_path": "TCP 127.0.0.1:<port> -> unix socket -> host relay -> metering proxy",
        "refuses_to_run_when": [
            "`unshare` is not on PATH",
            "a mount fails",
            "this namespace's own mount table cannot be read (no topology)",
            "a hidden root's filesystem is not a fresh tmpfs of this lane's own",
            "the network is reachable from inside the lane",
            "there is no PID namespace",
            "the meter forwarder is not reachable on this lane's loopback",
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "enter":
        return enter(argv[1:])
    if argv and argv[0] == "shim":
        return shim([part for part in argv[1:] if part != "--"])
    parser = argparse.ArgumentParser(
        prog="a0.a1.epistemic_ns.session_sandbox",
        description="the agent lane's namespace boundary (see the module docstring)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="print the boundary this module establishes")
    parser.parse_args(argv)
    print(json.dumps(describe(), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
