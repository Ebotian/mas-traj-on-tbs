#!/usr/bin/env python3
"""T1's candidate loader: one subprocess invocation of one candidate on one graph.

`INTERFACE.md` §1 gives this file exactly one job — *candidate subprocess loader
(sandbox, timeout, four states)* — and that is all it does.  It runs a candidate,
records what the operating system observed (exit code, wall clock, whether the
process group had to be killed), and reads back the artifact the candidate
wrote.  It never decides whether the candidate succeeded and never computes a
score: those are `e_star.py`'s (§6), which is what keeps the measured quantity
out of the runtime's reach.

Everything here is dictated by §4 and §7:

* `argv` is ``<entry> --graph <abs graph.json> --out <abs partition.json> --seed <int>``;
* `cwd` is a private scratch directory the harness creates;
* `env` is built from nothing (the parent's environment is *not* inherited), so
  no proxy variable and no credential can appear in it;
* the exit-code table (0 / 20 / 30 / 40 / other) is frozen here as constants;
* a timeout is **not** an exit code.  At `tau` the whole **process group** gets
  `SIGKILL`, and the invocation reports ``timed_out``.  Everything the candidate
  spawned dies with it, so no orphan can keep writing into the artifact path
  after the verdict has been taken.

Run this file directly to perform a single raw invocation and see the
observation (used by the conformance probes):

    python3 e_star_child.py --candidate candidates/c01_ok_high_pc \
        --graph graphs_tmp/tmp_suite/G_tmp_0001.json --out /tmp/p.json --seed 1337
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_OBSERVATION = "a0.maxcut.invocation/v1"
SCHEMA_CANDIDATE = "a0.maxcut.candidate/v1"

# --------------------------------------------------------------------------- #
# frozen §4 constants
# --------------------------------------------------------------------------- #

EXIT_OK = 0
EXIT_DECLARED_INVALID = 20
EXIT_INTERNAL_ERROR = 30
EXIT_REFUSED = 40

#: §4's code -> the label this loader records.  The mapping is total: anything
#: not named here is `other` and keeps its raw code, exactly as §4 requires.
EXIT_LABELS: dict[int, str] = {
    EXIT_OK: "ok",
    EXIT_DECLARED_INVALID: "declared_invalid",
    EXIT_INTERNAL_ERROR: "internal_error",
    EXIT_REFUSED: "refused",
}
OTHER_EXIT_LABEL = "other"

#: §4: "PATH 最小集".  The entry is launched through an absolute interpreter, so
#: PATH only matters if the candidate itself spawns something; a candidate that
#: needs more PATH than this is outside the ABI.
MINIMAL_PATH = "/usr/bin:/bin"

#: §4: "清空 http_proxy/https_proxy/no_proxy".  Cleared by absence (the child
#: environment is built from scratch), and named here so the conformance probe
#: can assert their absence explicitly.  Every case variant is listed because
#: libcurl and `requests` read lower and upper case differently.
PROXY_VARIABLES = (
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
)

#: §7's band.  tau = min(30, max(10, 10 x p99)) once calibration exists; until
#: then it is the band's upper edge, and any caller may pass a smaller value for
#: a bounded test.
TAU_MIN_S = 10.0
TAU_MAX_S = 30.0
DEFAULT_TIMEOUT_S = TAU_MAX_S

#: How long a SIGKILLed process group is given to actually disappear before the
#: loader stops waiting for its pipes.  A candidate cannot be permitted to hold
#: the harness open after tau.
REAP_TIMEOUT_S = 5.0

STREAM_TAIL_CHARS = 4000


class CandidateResolutionError(Exception):
    """The candidate directory does not describe a runnable candidate."""


# --------------------------------------------------------------------------- #
# candidate resolution
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(payload: object) -> str:
    """§2/§3's canonical form: sorted keys, compact separators, ASCII, one trailing newline."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def candidate_files(candidate_dir: Path) -> list[dict[str, Any]]:
    """Every byte that *is* the candidate, keyed by content and relpath.

    Directories the interpreter may create are excluded (`__pycache__`), because
    including them would make `candidate_source_sha256` a function of which
    interpreter happened to run first.
    """
    entries: list[dict[str, Any]] = []
    for path in sorted(candidate_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(candidate_dir)
        if any(part == "__pycache__" or part.startswith(".") for part in relative.parts):
            continue
        data = path.read_bytes()
        entries.append({"path": relative.as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)})
    return entries


def candidate_source_digest(files: Sequence[Mapping[str, Any]]) -> str:
    """Content digest of the whole candidate, independent of where it lives."""
    return sha256_bytes(canonical_json(list(files)).encode("utf-8"))


def resolve_candidate(candidate: str | os.PathLike[str]) -> dict[str, Any]:
    """Turn a candidate directory (or a bare program file) into a runnable spec.

    `candidate.json` is optional.  When present it may declare `candidate_id`
    and `exec` (the argv prefix that runs the entry).  The default prefix is the
    evaluator's *own* interpreter as an absolute path, which is what makes the
    invocation independent of the caller's PATH — the realization detail of §4's
    `<entry>` line, recorded in DEVIATIONS.md (D-T1-3).
    """
    path = Path(candidate).expanduser().resolve()
    if path.is_file():
        directory, entry_name = path.parent, path.name
    elif path.is_dir():
        directory = path
        metadata_path = directory / "candidate.json"
        declared_entry = None
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CandidateResolutionError(f"candidate.json is not valid JSON: {exc}") from exc
            if not isinstance(metadata, dict):
                raise CandidateResolutionError("candidate.json must be a JSON object")
            declared_entry = metadata.get("entry")
        else:
            metadata = {}
        entry_name = str(declared_entry) if declared_entry else "solution.py"
        if not (directory / entry_name).is_file() and declared_entry is None:
            alternatives = sorted(p.name for p in directory.glob("*.py") if p.name != "candidate.json")
            if len(alternatives) == 1:
                entry_name = alternatives[0]
    else:
        raise CandidateResolutionError(f"candidate not found: {path}")

    entry_path = (directory / entry_name).resolve()
    if not entry_path.is_file():
        raise CandidateResolutionError(f"candidate entry not found: {entry_path}")

    metadata = {}
    metadata_path = directory / "candidate.json"
    if metadata_path.is_file():
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                metadata = loaded
        except json.JSONDecodeError:
            metadata = {}

    declared_exec = metadata.get("exec")
    if declared_exec is not None:
        if not isinstance(declared_exec, list) or not all(isinstance(part, str) for part in declared_exec):
            raise CandidateResolutionError("candidate.json `exec` must be a list of strings")
        exec_prefix = list(declared_exec)
        exec_mode = "declared"
    else:
        # §4's `<entry>` is realized as `<interpreter> <entry>`, never as execve
        # on the file.  Two reasons, one textual and one structural.
        #
        # Textual: §4 mandates `PYTHONDONTWRITEBYTECODE=1` in the candidate's
        # environment, a variable only a CPython process reads.  §4 therefore
        # presupposes the harness supplies the interpreter, and the candidate's
        # own argv (what it reads in `sys.argv`) is exactly `<entry> --graph ...
        # --out ... --seed ...`, which is what §4 writes.
        #
        # Structural: inferring "run it directly" from the entry's mode bit made
        # the *launch* depend on something the candidate's identity does not
        # cover.  §2 makes the file's sha256 the data identity; a mode bit is not
        # in it, and it is not carried into the staged copy that is actually
        # executed (`e_star.stage_candidate`).  So two byte-identical candidates
        # could be `ok` and `error` respectively while both Outcomes carried the
        # same `candidate_source_sha256` -- the failure DEVIATIONS.md D-T1-10
        # records.  `exec: []` remains available for a candidate that really is a
        # self-executing program, but it must be *declared*, in which case the
        # mode is preserved into the staged copy and checked there.
        exec_prefix = [sys.executable]
        exec_mode = "interpreter"

    files = candidate_files(directory)
    return {
        "candidate_dir": str(directory),
        "candidate_id": str(metadata.get("candidate_id") or directory.name),
        "entry": entry_name,
        "entry_path": str(entry_path),
        "entry_sha256": sha256_bytes(entry_path.read_bytes()),
        "exec_prefix": exec_prefix,
        "exec_mode": exec_mode,
        "source_files": files,
        "source_sha256": candidate_source_digest(files),
        "metadata": metadata,
    }


# --------------------------------------------------------------------------- #
# the environment (§4)
# --------------------------------------------------------------------------- #

def candidate_environment(scratch: Path) -> dict[str, str]:
    """§4's environment, built from nothing.

    Nothing of the caller's environment is inherited, so "clear the proxies" and
    "inject no credentials" are structural properties of this function rather
    than a list of things someone remembered to delete.  The named proxy
    variables are removed explicitly anyway, so the conformance probe's
    assertion reads as the interface writes it.
    """
    scratch = scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": MINIMAL_PATH,
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(scratch),
        "LANG": "C.UTF-8",
    }
    for name in PROXY_VARIABLES:
        environment.pop(name, None)
    return environment


# --------------------------------------------------------------------------- #
# one invocation
# --------------------------------------------------------------------------- #

def _drain(stream) -> str:
    if stream is None:
        return ""
    return stream.decode("utf-8", "replace")[-STREAM_TAIL_CHARS:]


def run_invocation(
    *,
    spec: Mapping[str, Any],
    graph_path: Path,
    out_path: Path,
    seed: int,
    timeout_s: float,
    scratch: Path,
    net_isolate: bool = False,
) -> dict[str, Any]:
    """Run one candidate subprocess to completion, to its own exit, or to tau."""
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    isolation_prefix = ["unshare", "-rn"] if net_isolate else []
    argv = [
        *isolation_prefix,
        *[str(part) for part in spec["exec_prefix"]],
        str(spec["entry_path"]),
        "--graph", str(Path(graph_path).resolve()),
        "--out", str(out_path.resolve()),
        "--seed", str(int(seed)),
    ]

    observation: dict[str, Any] = {
        "schema": SCHEMA_OBSERVATION,
        "argv": argv,
        "net_isolate": bool(net_isolate),
        "cwd": str(scratch),
        "env": candidate_environment(scratch),
        "seed": int(seed),
        "timeout_s": float(timeout_s),
        "out_path": str(out_path.resolve()),
        "graph_path": str(Path(graph_path).resolve()),
        "exit_code": None,
        "exit_label": None,
        "timed_out": False,
        "process_group_killed": False,
        "wall_ms": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "spawn_error": None,
    }

    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(scratch),
            env=candidate_environment(scratch),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # its own process group: §7's SIGKILL target
        )
    except OSError as exc:
        observation["spawn_error"] = f"{type(exc).__name__}: {exc}"
        observation["wall_ms"] = int(round((time.perf_counter() - started) * 1000.0))
        return observation

    stdout = stderr = b""
    try:
        stdout, stderr = process.communicate(timeout=float(timeout_s))
    except subprocess.TimeoutExpired:
        observation["timed_out"] = True
        _kill_process_group(process, observation)
        try:
            stdout, stderr = process.communicate(timeout=REAP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            # A descendant held the pipes open past REAP_TIMEOUT_S.  The group
            # was already killed; stop waiting rather than let tau be defeated.
            _kill_process_group(process, observation)
            stdout, stderr = b"", b""
            try:
                process.wait(timeout=REAP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                pass

    observation["wall_ms"] = int(round((time.perf_counter() - started) * 1000.0))
    observation["exit_code"] = process.returncode
    observation["exit_label"] = (
        OTHER_EXIT_LABEL if process.returncode not in EXIT_LABELS else EXIT_LABELS[process.returncode]
    )
    observation["stdout_tail"] = _drain(stdout)
    observation["stderr_tail"] = _drain(stderr)
    return observation


def _kill_process_group(process: subprocess.Popen, observation: dict[str, Any]) -> None:
    """§7: SIGKILL the whole group at tau, never an exit code."""
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        observation["process_group_killed"] = True
    except (ProcessLookupError, PermissionError):
        try:
            process.kill()
            observation["process_group_killed"] = True
        except ProcessLookupError:
            pass


# --------------------------------------------------------------------------- #
# CLI: one raw invocation, for probes and conformance
# --------------------------------------------------------------------------- #

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one T1 candidate invocation and report the observation.")
    parser.add_argument("--candidate", required=True, help="candidate directory or program file")
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True, help="absolute path the candidate must write partition.json to")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--net-isolate", action="store_true", help="run the candidate in a new, route-less netns")
    parser.add_argument("--scratch", default=None, help="private scratch dir (default: a temp dir)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    spec = resolve_candidate(args.candidate)
    scratch = Path(args.scratch) if args.scratch else Path(
        subprocess.run(["mktemp", "-d"], capture_output=True, check=True).stdout.decode().strip()
    )
    observation = run_invocation(
        spec=spec,
        graph_path=Path(args.graph),
        out_path=Path(args.out),
        seed=args.seed,
        timeout_s=args.timeout,
        scratch=scratch,
        net_isolate=bool(args.net_isolate),
    )
    print(json.dumps(observation, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
