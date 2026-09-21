#!/usr/bin/env python3
"""Capture harness for the A0 execution/load attestation.

This file is a *sensor*, not a serializer: it runs one real E* invocation inside
the process whose behaviour we want to attest, records what the interpreter
actually loaded and executed, and dumps the raw observations as JSON.  All
canonicalization and hashing of the attestation document happens in
`attest.py`, so no part of the identity scheme lives here.

Two capture modes:

  run          import the frozen evaluator as a module and call its `main()`
               with the argv the adapter would have passed to the CLI.  Every
               module the evaluator imports, every code object the interpreter
               executes, every file opened and every child process spawned is
               recorded.
  probe-import install the captured child environment (`PATH=""`, private
               HOME/TMPDIR/cwd -- exactly what E* hands to `e_star_child.py`)
               and import `e_star_child.py` as a module, so the *child* side of
               the evaluator is attested too.

Why an audit hook rather than a loader wrapper: `sys.addaudithook` observes the
interpreter's own events, and the `exec` event carries the code object that is
about to run.  That is the only artifact that is authoritative about what
executed -- a file hash on disk is not.  A stale `__pycache__`, a module earlier
on `sys.path` shadowing a stdlib name, or a different file loaded under the same
name all leave the on-disk hash of the declared source untouched.

`code_sha256` is `sha256(marshal.dumps(code_object))`.  Marshal output for
identically compiled source is stable within one interpreter build, and the
interpreter build is recorded in the attestation, so cross-build comparison is
guarded rather than silently invalid.

Namespace hygiene: the harness must not pre-bind the names the evaluator
imports, or a shadowing module could not be observed.  The harness therefore
loads its own `hashlib` and `argparse` from `sys.base_prefix` under private
aliases, and writes the capture document with a local JSON writer instead of
importing `json`.  Whatever the evaluator imports is imported by the evaluator,
and `pre_existing_modules` records exactly which modules the harness itself had
already caused to load.
"""

from __future__ import annotations

import importlib.util
import marshal
import os
import sys
import time

# Environment variables that can change what an interpreter runs.  The set is a
# fixed allowlist on purpose: dumping the whole environ would put unrelated
# secrets into an attestation document, and no unfixed name may influence the
# identity.
ENV_NAMES = (
    "PATH",
    "HOME",
    "TMPDIR",
    "TEMP",
    "TMP",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONHASHSEED",
    "PYTHONNOUSERSITE",
    "PYTHONUSERBASE",
    "PYTHONOPTIMIZE",
    "PYTHONWARNINGS",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONPYCACHEPREFIX",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
    "PYTHONMALLOC",
    "PYTHONDEVMODE",
    "PYTHONFAULTHANDLER",
    "PYTHONINSPECT",
    "PYTHONCASEOK",
    "PYTHONEXECUTABLE",
    "PYTHONSAFEPATH",
    "PYTHON_GIL",
    "PYTHONNODEBUGRANGES",
    "VIRTUAL_ENV",
    "LC_ALL",
    "LANG",
    "TZ",
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "SOURCE_DATE_EPOCH",
)

_REDACT_TOKENS = ("sk-", "ghp_", "gho_", "AIza", "xoxb-", "Bearer ")

_MAX_OPEN_EVENTS = 20000
_MAX_IMPORT_EVENTS = 20000


# --------------------------------------------------------------------------- #
# private imports (names the evaluator imports stay unbound here)
# --------------------------------------------------------------------------- #

def _privload(name: str, path: str, package_dir: str | None = None):
    locations = [package_dir] if package_dir else None
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=locations)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stdlib(name: str) -> str:
    return os.path.join(sys.base_prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", name)


_HASHLIB = _privload("_attest_hashlib", _stdlib("hashlib.py"))
_ARGPARSE = _privload("_attest_argparse", _stdlib("argparse.py"))


# --------------------------------------------------------------------------- #
# local JSON writer (keeps the name `json` free for the evaluator)
# --------------------------------------------------------------------------- #

_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


def _json_string(value: str) -> str:
    out = ['"']
    for char in value:
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif char < " " or 0xD800 <= ord(char) <= 0xDFFF:
            out.append("\\u%04x" % ord(char))
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _json_text(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _json_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return "null"
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_json_text(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            _json_string(str(k)) + ":" + _json_text(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        ) + "}"
    return _json_string(repr(value))


# --------------------------------------------------------------------------- #
# capture
# --------------------------------------------------------------------------- #

def _redact(value: str) -> str:
    for token in _REDACT_TOKENS:
        if token in value:
            return "<redacted:secret-shaped>"
    return value


def _sha256_bytes(data: bytes) -> str:
    return _HASHLIB.sha256(data).hexdigest()


def _sha256_file(path: str) -> dict | None:
    try:
        digest = _HASHLIB.sha256()
        size = 0
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
        return {"sha256": digest.hexdigest(), "size": size}
    except OSError:
        return None


def _classify_origin(origin, loader_name: str) -> str:
    if origin is None:
        return "namespace"
    if origin == "built-in":
        return "builtin"
    if origin == "frozen":
        return "frozen"
    suffix = os.path.splitext(origin)[1]
    if suffix in (".py", ".pyw"):
        return "source"
    if suffix in (".pyc", ".pyo"):
        return "bytecode"
    if suffix in (".so", ".pyd", ".dylib"):
        return "extension"
    if loader_name == "ExtensionFileLoader":
        return "extension"
    return "other"


class Capture:
    def __init__(self) -> None:
        self.pre_existing = sorted(sys.modules)
        self.import_events: list[str] = []
        self.exec_events: list[dict] = []
        self.open_events: list[dict] = []
        self.popen_events: list[dict] = []
        self.socket_events: list[dict] = []
        self.truncated = {"open_events": False, "import_events": False, "exec_events": False}
        self._open_seen: set[tuple] = set()
        self._import_seen: set[str] = set()
        self._socket_seen: set[tuple] = set()

    def hook(self, event: str, args: tuple) -> None:
        try:
            if event == "exec":
                self._on_exec(args)
            elif event == "import":
                self._on_import(args)
            elif event == "open":
                self._on_open(args)
            elif event == "subprocess.Popen":
                self._on_popen(args)
            elif event in ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname"):
                self._on_socket(event, args)
        except Exception:  # noqa: BLE001 - an audit hook may never raise
            pass

    def _on_exec(self, args: tuple) -> None:
        code = args[0] if args else None
        if not hasattr(code, "co_filename"):
            return
        if len(self.exec_events) >= _MAX_IMPORT_EVENTS:
            self.truncated["exec_events"] = True
            return
        self.exec_events.append(
            {
                "co_filename": code.co_filename,
                "co_name": code.co_name,
                "co_firstlineno": code.co_firstlineno,
                "co_argcount": code.co_argcount,
                "code_sha256": _sha256_bytes(marshal.dumps(code)),
            }
        )

    def _on_import(self, args: tuple) -> None:
        name = args[0] if args else None
        if not isinstance(name, str) or name in self._import_seen:
            return
        if len(self.import_events) >= _MAX_IMPORT_EVENTS:
            self.truncated["import_events"] = True
            return
        self._import_seen.add(name)
        self.import_events.append(name)

    def _on_open(self, args: tuple) -> None:
        path = args[0] if args else None
        if not isinstance(path, str):
            return
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else None
        key = (path, mode)
        if key in self._open_seen:
            return
        if len(self.open_events) >= _MAX_OPEN_EVENTS:
            self.truncated["open_events"] = True
            return
        self._open_seen.add(key)
        self.open_events.append({"path": path, "mode": mode})

    def _on_popen(self, args: tuple) -> None:
        executable = args[0] if args else None
        argv = args[1] if len(args) > 1 else None
        cwd = args[2] if len(args) > 2 else None
        env = args[3] if len(args) > 3 else None
        self.popen_events.append(
            {
                "executable": executable if isinstance(executable, str) else repr(executable),
                "argv": [str(item) for item in argv] if isinstance(argv, (list, tuple)) else repr(argv),
                "cwd": cwd if isinstance(cwd, str) else None,
                "env": {k: _redact(str(v)) for k, v in sorted(env.items())} if isinstance(env, dict) else None,
            }
        )

    def _on_socket(self, event: str, args: tuple) -> None:
        key = (event, repr(args)[:200])
        if key in self._socket_seen:
            return
        self._socket_seen.add(key)
        self.socket_events.append({"event": event, "args": repr(args)[:400]})

    def module_records(self) -> list[dict]:
        records = []
        for name in sorted(sys.modules):
            module = sys.modules.get(name)
            if module is None:
                continue
            try:
                spec = getattr(module, "__spec__", None)
                origin = getattr(spec, "origin", None) or getattr(module, "__file__", None)
                cached = getattr(spec, "cached", None)
                loader = getattr(spec, "loader", None)
                loader_name = type(loader).__name__ if loader is not None else "namespace/None"
            except Exception:  # noqa: BLE001
                origin, cached, loader_name = None, None, "unreadable"
            entry = {
                "name": name,
                "origin": origin,
                "origin_kind": _classify_origin(origin, loader_name),
                "loader": loader_name,
                "cached": cached,
                "pre_existing": name in self.pre_existing,
            }
            if origin and origin not in ("built-in", "frozen") and os.path.isfile(origin):
                entry.update(_sha256_file(origin) or {})
                if cached and os.path.isfile(cached):
                    cached_stat = _sha256_file(cached)
                    if cached_stat:
                        entry["cached_sha256"] = cached_stat["sha256"]
            records.append(entry)
        return records


def _runtime_identity() -> dict:
    import importlib.util as _importlib_util

    executable = sys.executable
    real = os.path.realpath(executable)
    stat = _sha256_file(real) or {}
    try:
        uname = list(os.uname())
    except Exception:  # noqa: BLE001
        uname = None
    return {
        "executable": executable,
        "executable_realpath": real,
        "executable_sha256": stat.get("sha256"),
        "executable_size": stat.get("size"),
        "version": "%d.%d.%d" % sys.version_info[:3],
        "version_full": sys.version,
        "implementation": sys.implementation.name,
        "cache_tag": getattr(sys.implementation, "cache_tag", None),
        "bytecode_magic_hex": _importlib_util.MAGIC_NUMBER.hex(),
        "hexversion": sys.hexversion,
        "api_version": sys.api_version,
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "sys_exec_prefix": sys.exec_prefix,
        "sys_base_exec_prefix": sys.base_exec_prefix,
        "platform": {
            "sysname": uname[0] if uname else None,
            "nodename": None,  # hostname is deliberately not captured
            "release": uname[2] if uname else None,
            "machine": uname[4] if uname else None,
        },
        "flags": {
            "optimize": sys.flags.optimize,
            "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
            "no_user_site": bool(sys.flags.no_user_site),
            "no_site": bool(sys.flags.no_site),
            "ignore_environment": bool(sys.flags.ignore_environment),
            "isolated": bool(sys.flags.isolated),
            "safe_path": bool(getattr(sys.flags, "safe_path", False)),
            "utf8_mode": bool(sys.flags.utf8_mode),
            "hash_randomization": sys.flags.hash_randomization,
            "dev_mode": bool(getattr(sys.flags, "dev_mode", False)),
            "bytes_warning": sys.flags.bytes_warning,
            "verbose": sys.flags.verbose,
        },
        "sys_path": list(sys.path),
    }


def _environment_snapshot() -> dict:
    out = {}
    for name in ENV_NAMES:
        if name in os.environ:
            out[name] = {"set": True, "value": _redact(os.environ[name])}
        else:
            out[name] = {"set": False, "value": None}
    return out


def _capture_document(mode: str, started: float, capture: Capture, extra: dict) -> dict:
    harness = getattr(sys, "_a0_harness", {})
    return {
        "schema": "a0.attestation.capture/v1",
        "mode": mode,
        "wall_seconds": time.time() - started,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "sys_argv": list(sys.argv),
        "harness": {
            "path": os.path.abspath(__file__),
            "sha256": _sha256_file(os.path.abspath(__file__)).get("sha256"),
            "own_directory_removed_from_sys_path": harness.get("sys_path_removed", []),
        },
        "runtime": _runtime_identity(),
        "environment": _environment_snapshot(),
        "pre_existing_modules": capture.pre_existing,
        "import_events": capture.import_events,
        "exec_events": capture.exec_events,
        "open_events": capture.open_events,
        "popen_events": capture.popen_events,
        "socket_events": capture.socket_events,
        "truncated": capture.truncated,
        "modules": capture.module_records(),
        **extra,
    }


def _write_capture(path: str, document: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(_json_text(document))
    os.replace(tmp, path)


def _load_module_from_path(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def _read_env_file(path: str) -> dict:
    """Read the `KEY=VALUE` environment file written by the parent.

    Values are one line each by construction (E*'s child environment contains
    only paths and single tokens), which keeps this sensor free of a JSON
    dependency.
    """
    out = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle.read().split("\n"):
            if not line:
                continue
            key, _, value = line.partition("=")
            out[key] = value
    return out


def _cmd_run(args) -> int:
    evaluator = os.path.abspath(args.evaluator)
    argv = list(args.evaluator_argv)
    started = time.time()
    directory = os.path.dirname(evaluator)
    name = os.path.splitext(os.path.basename(evaluator))[0]
    sys.path.insert(0, directory)

    capture = Capture()
    sys.addaudithook(capture.hook)
    sys.argv = [evaluator] + list(argv)

    exit_code = None
    error = None
    traceback_text = None
    try:
        module = _load_module_from_path(evaluator, name)
        try:
            exit_code = int(module.main(argv))
        except SystemExit as exc:
            exit_code = int(exc.code) if isinstance(exc.code, int) else 1
    except BaseException as exc:  # noqa: BLE001 - a capture must still be emitted
        import traceback as _tb

        error = f"{type(exc).__name__}: {exc}"
        traceback_text = _tb.format_exc()
        exit_code = 70

    document = _capture_document(
        "run",
        started,
        capture,
        {
            "evaluator_path": evaluator,
            "evaluator_module_name": name,
            "evaluator_argv": list(argv),
            "exit_code": exit_code,
            "error": error,
            "traceback": traceback_text,
        },
    )
    _write_capture(args.capture, document)
    return 0


def _cmd_probe_import(args) -> int:
    path = os.path.abspath(args.module_path)
    started = time.time()
    override = _read_env_file(args.env_file) if args.env_file else None
    if override is not None:
        os.environ.clear()
        os.environ.update({k: str(v) for k, v in override.items()})
    if args.cwd:
        os.makedirs(args.cwd, exist_ok=True)
        os.chdir(args.cwd)

    directory = os.path.dirname(path)
    name = os.path.splitext(os.path.basename(path))[0]
    sys.path.insert(0, directory)

    capture = Capture()
    sys.addaudithook(capture.hook)

    error = None
    traceback_text = None
    try:
        _load_module_from_path(path, name)
    except BaseException as exc:  # noqa: BLE001
        import traceback as _tb

        error = f"{type(exc).__name__}: {exc}"
        traceback_text = _tb.format_exc()

    document = _capture_document(
        "probe-import",
        started,
        capture,
        {
            "module_path": path,
            "module_name": name,
            "error": error,
            "traceback": traceback_text,
            "environment_override_applied": override is not None,
        },
    )
    _write_capture(args.capture, document)
    return 0


def build_parser():
    parser = _ARGPARSE.ArgumentParser(prog="_bootstrap.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="import the evaluator and call its CLI entry point")
    run.add_argument("--evaluator", required=True)
    run.add_argument("--capture", required=True)
    run.add_argument("evaluator_argv", nargs=_ARGPARSE.REMAINDER, help="E* CLI arguments")
    run.set_defaults(func=_cmd_run)

    probe = sub.add_parser("probe-import", help="import one module under a captured environment")
    probe.add_argument("--module-path", required=True)
    probe.add_argument("--env-file", default=None, help="KEY=VALUE file to install as the environment")
    probe.add_argument("--cwd", default=None)
    probe.add_argument("--capture", required=True)
    probe.set_defaults(func=_cmd_probe_import)
    return parser


def main(argv=None) -> int:
    harness_dir = os.path.dirname(os.path.abspath(__file__))
    removed = []
    while harness_dir in sys.path:
        sys.path.remove(harness_dir)
        removed.append(harness_dir)
    sys._a0_harness = {"dir": harness_dir, "sys_path_removed": removed}
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
