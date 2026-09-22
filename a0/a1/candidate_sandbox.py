"""The candidate lane's own boundary: what a candidate can reach, and what not.

**Why this exists.**  `INTERFACE.md` principle (iv) says the budget must be
enforceable where the runtime cannot lie, and §4 says a candidate is given *no*
network and no credential.  `--net-isolate` (`a0/tasks/maxcut/e_star_child.py`)
enforces the network half for the candidate.  It does **not** enforce the other
half: the candidate runs under the harness's uid with the whole filesystem
readable, so it can read the stored reference partitions
(`a0/tasks/maxcut/references/`), the provider key (`~/gptapi.md`) or any other
file that is not exactly the graph it was handed.  A candidate that reads a
stored answer is a candidate whose score is not a measurement, and a candidate
that reads a key can spend outside the meter — both are failures of principle
(iv), and the second is a failure of principle (ii) as well.

**What it does.**  The harness runs `E*` (and therefore every candidate `E*`
spawns) inside one unprivileged namespace stack:

```
   unshare -rmnpf --mount-proc        user + mount + net + pid namespace
     ├─ mount --make-rprivate /      nothing propagates back to the host
     ├─ stage the allow-list         bind the invocation's own inputs aside
     ├─ hide the roots               tmpfs over /home, /tmp, /var/tmp, /run/user
     ├─ restore the allow-list       bind the inputs back at their real paths
     └─ exec E*                      which runs the candidate twice
```

Three closures, each of them a separate thing that can be probed:

* **network** — a fresh network namespace with no route but its own (down)
  loopback, so `api.deepseek.com`, `1.1.1.1` and every other destination are
  unreachable.  `E*` is additionally given `--net-isolate`, so the candidate gets
  a namespace of its own *inside* that one.
* **filesystem** — the hidden roots are empty tmpfs mounts.  Everything the
  invocation legitimately needs is bind-mounted back, so a candidate sees
  exactly: its own staged bytes, the one graph it was handed, its scratch, the
  invocation's state directory, and the interpreter.  `graph.json`'s siblings
  (`suite/eval/**`, `references/logs/partitions/**`, the generators) are not
  there to read.
* **processes** — a fresh PID namespace plus a fresh `/proc`, so the candidate
  cannot enumerate the host's processes or read another process's
  `/proc/<pid>/environ`.  That matters because the *runtime* holds the provider
  key in its own environment: without this, a candidate could read the key out
  of `/proc/<arm pid>/environ` and spend outside the meter even with the
  filesystem closed.

**Fail-closed.**  If `unshare` is missing, if a mount fails, or if the
namespace's own self-check finds the network reachable, or a hidden root not
actually hidden, or no PID namespace, the sandbox exits non-zero and the
harness refuses to measure.  The self-check's result is written to a receipt
(`--receipt <path>`) *before* `E*` is exec'd, so "the candidate ran in a closed
lane" is recorded evidence rather than an intention.

**Residual, stated rather than implied.**  This is a mount/PID/network namespace
boundary, not a virtual machine: the candidate still shares the kernel and the
host's `/usr`, `/lib`, `/etc` and `/dev`, and it still has the harness's uid.
It does not defend against a kernel exploit, and it does not make `E*`'s own
process tree immune to a candidate that merely exhausts memory.  What it does
establish is the property A1 needs: a candidate cannot reach the network, cannot
read a file outside the allow-list, and cannot see another process.

**Use.**

```python
from a0.a1.candidate_sandbox import prefix
argv = prefix(["/usr/bin/python3", "e_star.py", "evaluate", ...],
              allow=[graph, candidate, script, out_dir, state_dir],
              receipt=out_dir / "sandbox_receipt.json")
subprocess.run(argv, ...)
```
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCHEMA_RECEIPT = "a0.a1.candidate_sandbox/v1"

#: The roots hidden from the candidate lane.  Each is replaced by an empty
#: tmpfs; the invocation's own inputs are bind-mounted back on top of it.
#: `/home` carries the repository (and the provider key), `/tmp` and `/var/tmp`
#: carry every other run's scratch, `/run/user` carries per-session runtime
#: state.  The system directories the interpreter itself needs (`/usr`,
#: `/lib`, `/etc`, `/dev`) are deliberately *not* hidden: they carry no
#: evaluation material, and hiding them would break the interpreter rather
#: than the attack.  That boundary is a residual, and it is named in the module
#: docstring and in the receipt.
DEFAULT_HIDDEN_ROOTS = ("/home", "/tmp", "/var/tmp", "/run/user")

#: Where the allow-list is staged.  It must be a path that is *not* hidden, so
#: the sources can be bound aside before `/home` and `/tmp` disappear.
STAGE_ROOT = Path("/dev/shm")
STAGE_NAME = ".a0a1-candidate-sandbox"

UNSHARE = shutil.which("unshare")

# linux/mount.h, the only flags this module uses.
MS_NOSUID = 2
MS_NODEV = 4
MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 1 << 18

TEMPORARY_FS_OPTIONS = "mode=1777,size=64m"

#: `prefix()` is called once per evaluation, and the interpreter's roots do not
#: change between calls.
_INTERPRETER_ROOTS_CACHE: Dict[str, List[Path]] = {}

#: Exit code the sandbox uses when it cannot establish the boundary.
EXIT_SANDBOX_REFUSED = 3


class SandboxError(RuntimeError):
    """The boundary could not be established; the harness must not measure."""


def available() -> bool:
    return UNSHARE is not None


# ---------------------------------------------------------------------------
# the mount syscall, without a dependency on /usr/bin/mount
# ---------------------------------------------------------------------------
def _libc() -> ctypes.CDLL:
    libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
    libc.mount.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_char_p
    ]
    libc.mount.restype = ctypes.c_int
    return libc


def _encoded(value: Optional[str]) -> Optional[bytes]:
    return None if value is None else str(value).encode("utf-8")


def mount(source: Optional[str], target: str, fstype: Optional[str] = None,
          flags: int = 0, data: Optional[str] = None) -> None:
    rc = _libc().mount(_encoded(source), _encoded(target), _encoded(fstype),
                       ctypes.c_ulong(flags), _encoded(data))
    if rc != 0:
        err = ctypes.get_errno()
        raise SandboxError(
            f"mount({source!r} -> {target!r}, fstype={fstype!r}, flags={flags}) "
            f"failed: {os.strerror(err)}"
        )


# ---------------------------------------------------------------------------
# what the caller hands in
# ---------------------------------------------------------------------------
def interpreter_roots(python: Path) -> List[Path]:
    """The installation directories of `python`, asked of `python` itself.

    `E*` launches the candidate through its own absolute interpreter
    (`e_star_child.resolve_candidate`), and that interpreter's standard library
    is not necessarily under `/usr`: on this machine the plumbing evaluator's
    virtualenv resolves to a `uv`-managed CPython under `$HOME`. Hiding `$HOME`
    without binding that installation back would hide the lane's own standard
    library (measured: `LookupError: unknown encoding: idna` from the lane's own
    self-check, and `ModuleNotFoundError: No module named 'encodings'` when the
    venv's `pyvenv.cfg` was missing too).

    The roots are queried from the interpreter rather than assumed, and a prefix
    that does not exist is skipped: a path that is not there cannot be hidden.
    """
    key = str(python)
    if key in _INTERPRETER_ROOTS_CACHE:
        return list(_INTERPRETER_ROOTS_CACHE[key])
    script = (
        "import json, sys; print(json.dumps([sys.prefix, sys.base_prefix, "
        "sys.exec_prefix, sys.base_exec_prefix, sys.executable]))"
    )
    roots: List[Path] = [Path(python)]
    try:
        proc = subprocess.run([str(python), "-c", script], capture_output=True, text=True,
                              timeout=60)
        if proc.returncode == 0:
            roots = [Path(item) for item in json.loads(proc.stdout.strip().splitlines()[-1])]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    roots = [path for path in roots if path.is_dir() or path.exists()]
    deduped: List[Path] = []
    for path in roots:
        if path not in deduped:
            deduped.append(path)
    _INTERPRETER_ROOTS_CACHE[key] = list(deduped)
    return deduped


def prefix(command: Sequence[str], *, allow: Sequence[Optional[Path]],
           receipt: Optional[Path] = None,
           hidden_roots: Sequence[str] = DEFAULT_HIDDEN_ROOTS,
           python: Optional[Path] = None) -> List[str]:
    """The argv that runs `command` inside the candidate lane.

    `allow` is the *whole* of what the invocation may see at its real path: the
    evaluator's own files, the graph, the candidate, the scratch/state directory
    and the interpreter.  A path outside the hidden roots needs no entry (it was
    never hidden); a path inside them that is missing from `allow` will not
    exist inside the lane.  The interpreter's own installation directories are
    added by `interpreter_roots`; nothing else is added.
    """
    if not available():
        raise SandboxError(
            "`unshare` is not on PATH; the candidate lane cannot be closed and "
            "the harness must not measure in an open topology"
        )
    interpreter = Path(python or sys.executable)
    entries: List[Path] = []
    for path in [*[Path(item) for item in allow if item is not None], *interpreter_roots(interpreter)]:
        if path in entries:
            continue
        entries.append(path)
    inner = [str(interpreter), str(Path(__file__).resolve()), "enter"]
    for root in hidden_roots:
        inner += ["--hide", str(root)]
    for path in entries:
        inner += ["--allow", str(path)]
    if receipt is not None:
        inner += ["--receipt", str(receipt)]
    inner += ["--", *[str(part) for part in command]]
    # `-r` maps this uid to root inside the new user namespace, which is what
    # makes the mounts legal; `-m -n -p` are the mount, network and PID
    # namespaces; `-f` is required because the command is exec'd (`--mount-proc`
    # mounts the fresh procfs after the fork, so /proc lists only this tree).
    return [str(UNSHARE), "-rmnpf", "--mount-proc", *inner]


# ---------------------------------------------------------------------------
# inside the namespace
# ---------------------------------------------------------------------------
def _under_any(path: Path, roots: Sequence[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _stage_dir() -> Path:
    stage = STAGE_ROOT / STAGE_NAME / f"pid{os.getpid()}"
    stage.mkdir(parents=True, exist_ok=True)
    return stage


def _stage_allow(stage: Path, allow: Sequence[Path]) -> List[Dict[str, Any]]:
    """Bind the allow-list aside, before the roots it lives under disappear."""
    staged: List[Dict[str, Any]] = []
    for index, path in enumerate(allow):
        if not path.exists():
            raise SandboxError(f"allow path does not exist: {path}")
        target = stage / str(index)
        target.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            mount(str(path), str(target), None, MS_BIND)
            held = target
            kind = "dir"
        else:
            held = target / "file"
            held.touch(exist_ok=True)
            mount(str(path), str(held), None, MS_BIND)
            kind = "file"
        staged.append({"path": str(path), "kind": kind, "stage": str(held)})
    return staged


def _mount_table() -> Dict[str, str]:
    """`mount point -> filesystem type`, from this namespace's own mountinfo."""
    table: Dict[str, str] = {}
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        left, _, right = line.partition(" - ")
        fields = left.split()
        if len(fields) < 5 or not right:
            continue
        table[fields[4].replace("\\040", " ")] = right.split()[0]
    return table


def _hide(roots: Sequence[Path]) -> List[str]:
    hidden: List[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        if _mount_table().get(str(root)) == "tmpfs":
            hidden.append(str(root))  # already hidden: idempotent
            continue
        mount("tmpfs", str(root), "tmpfs", MS_NOSUID | MS_NODEV, TEMPORARY_FS_OPTIONS)
        hidden.append(str(root))
    return hidden


def _restore(staged: Sequence[Dict[str, Any]], hidden: Sequence[Path]) -> List[str]:
    """Bind each staged input back at the path the invocation knows it by.

    Shallow paths first: an entry that lives *inside* another entry (a virtualenv's
    `bin/python` inside the virtualenv, a file inside an allowed directory) must
    be mounted **after** its ancestor, or the ancestor's bind would cover it and
    the file-level mount would be lost.  (Measured: with the deep entry first, the
    interpreter path came back as a plain file inside a directory that was then
    covered, and the `exec` of the interpreter failed with `ENOENT`.)
    """
    ordered = sorted(staged, key=lambda entry: (len(Path(entry["path"]).parts), entry["path"]))
    restored: List[str] = []
    for entry in ordered:
        path = Path(entry["path"])
        if not _under_any(path, hidden):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if entry["kind"] == "dir":
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            path.touch()
        mount(str(entry["stage"]), str(path), None, MS_BIND)
        restored.append(str(path))
    return restored


def _pid_namespace_state() -> Dict[str, Any]:
    """How many processes this namespace can see, and which pid we are in it.

    `NSpid` in `/proc/self/status` is *not* the test: the lane's `/proc` is
    mounted for the lane's own PID namespace, so it reports a single column even
    though the namespace is new (measured).  What is decisive is that this
    process is PID 1 of the namespace it is running in -- impossible in the
    host's namespace -- and that `/proc` lists only this tree.
    """
    visible: List[int] = []
    try:
        visible = sorted(int(name) for name in os.listdir("/proc") if name.isdigit())
    except OSError:
        pass
    levels = 0
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("NSpid:"):
                levels = len(line.split(":", 1)[1].split())
    except OSError:
        pass
    return {
        "self_pid": os.getpid(),
        "visible_pid_count": len(visible),
        "visible_pids": visible[:8],
        "nspid_columns": levels,
        "is_private": os.getpid() == 1 and len(visible) <= 8,
    }


def _self_check(hidden: Sequence[Path], *, probe_host: str = "api.deepseek.com") -> Dict[str, Any]:
    """Probe the boundary from inside it, before `E*` is allowed to run."""
    table = _mount_table()
    not_hidden = [str(root) for root in hidden if table.get(str(root)) != "tmpfs"]
    try:
        socket.create_connection((probe_host, 443), timeout=2).close()
        egress = "REACHED"
    except OSError as exc:
        egress = "BLOCKED:" + type(exc).__name__
    pid = _pid_namespace_state()
    return {
        "hidden_roots_are_tmpfs": not not_hidden,
        "not_hidden": not_hidden,
        "egress": egress,
        "egress_is_blocked": egress.startswith("BLOCKED"),
        "pid_namespace": pid,
        "pid_namespace_is_private": bool(pid["is_private"]),
    }


def _write_receipt(path: Optional[str], payload: Dict[str, Any]) -> None:
    if not path:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:  # a receipt that cannot be written is not a boundary
        print(f"candidate_sandbox: could not write the receipt: {exc}", file=sys.stderr)


def enter(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="candidate_sandbox enter")
    parser.add_argument("--hide", action="append", default=[])
    parser.add_argument("--allow", action="append", default=[])
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
        "command": command,
        "pass": False,
    }
    try:
        # Nothing this namespace does may propagate back to the host's mount
        # table, and the new mount namespace must not be shared with anything
        # that already exists.
        mount("none", "/", None, MS_REC | MS_PRIVATE, None)
        staged = _stage_allow(_stage_dir(), allow)
        hidden_now = _hide(hidden)
        restored = _restore(staged, hidden)
        receipt["staged"] = staged
        receipt["hidden_roots"] = hidden_now
        receipt["restored"] = restored
        self_check = _self_check([Path(root) for root in hidden_now])
        receipt["self_check"] = self_check
        if not (self_check["hidden_roots_are_tmpfs"]
                and self_check["egress_is_blocked"]
                and self_check["pid_namespace_is_private"]):
            raise SandboxError(f"the lane's self-check failed: {self_check}")
    except SandboxError as exc:
        receipt["error"] = str(exc)
        _write_receipt(args.receipt, receipt)
        print(f"candidate_sandbox: refusing to run: {exc}", file=sys.stderr)
        return EXIT_SANDBOX_REFUSED

    receipt["pass"] = True
    _write_receipt(args.receipt, receipt)
    os.execv(command[0], command)  # never returns
    return 0  # unreachable


def describe() -> Dict[str, Any]:
    return {
        "schema": SCHEMA_RECEIPT,
        "available": available(),
        "unshare": UNSHARE,
        "hidden_roots": list(DEFAULT_HIDDEN_ROOTS),
        "namespaces": ["user", "mount", "network", "pid"],
        "stage_root": str(STAGE_ROOT / STAGE_NAME),
        "refuses_to_run_when": [
            "`unshare` is not on PATH",
            "a mount fails",
            "a hidden root is not actually a tmpfs inside the lane",
            "the network is reachable from inside the lane",
            "there is no PID namespace",
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "enter":
        return enter(argv[1:])
    parser = argparse.ArgumentParser(
        prog="a0.a1.candidate_sandbox",
        description="the candidate lane's namespace boundary (see the module docstring)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="print the boundary this module establishes")
    parser.parse_args(argv)
    print(json.dumps(describe(), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
