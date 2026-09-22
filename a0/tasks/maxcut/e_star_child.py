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
import shutil
import signal
import subprocess
import sys
import tempfile
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

#: Filesystem isolation (§4's "不依赖外部文件" taken to its enforceable form).
#:
#: The ABI says a candidate may not depend on cwd, PATH or external files.  The
#: reason the testbed cares is stronger than portability: the reference
#: solutions, the frozen suite's generator blocks and the git objects all live in
#: the repository the candidate runs beside, under the same uid.  A mount
#: namespace built before the candidate is started takes them away from it, which
#: is enforcement rather than obscurity -- and, unlike a permission bit, it covers
#: `git` history, `logs/raw` stdout transcripts and any other copy of an answer
#: that happens to sit in the repository.
#:
#: The child's own realm (its staged entry, its run directory holding the graph
#: and the artifact path) is bound back in, so nothing the ABI promises is lost.
FS_ISOLATE_DEFAULT = True

#: The wrapper's own exit code.  It is produced by `fs_isolation_wrapper` and by
#: nothing else; a candidate that happens to exit 70 is told apart by the marker
#: file the wrapper touches immediately before `exec`.
FS_FAILURE_EXIT = 70

#: Where the wrapper stages the paths it must bind back after masking.  It must
#: live outside every mask -- in particular outside `/tmp`, which is masked as a
#: whole (see `isolation_policy`) -- and it is private to the mount namespace, so
#: two concurrent loaders cannot collide.
KEEP_CANDIDATES = ("/dev/shm", "/run/shm", "/run/user")

#: Filesystem roots that are temporarily masked to the candidate as a whole, then
#: given back empty: the world-writable scratch filesystems.  Another harness's
#: state root is an answer store (`<state>/invocations/<delta>/<graph_id>/run1/
#: partition.json` is a previous candidate's partition for one of these graphs),
#: and E* cannot enumerate the state roots of harness runs it did not start -- nor
#: the copies of them left behind by earlier ones.  A fresh tmpfs over `/tmp` and
#: `/var/tmp` hides all of them and leaves the candidate a writable scratch, which
#: is what §4 promises it (`HOME=<scratch>` plus a `/tmp` it may use).
TMP_ROOTS = ("/tmp", "/var/tmp")

#: Marker the wrapper drops in the scratch directory once the masking is up and
#: verified.  Its absence is what turns a non-zero exit into "the isolation
#: wrapper never reached the candidate" instead of a candidate failure.
ISOLATION_MARKER = ".e_star_isolation_ok"

#: E*'s default state root (`e_star.py`).  It holds artifacts produced by
#: *previous* candidates, so it is masked like any other answer store: one run
#: must not be able to read a sibling candidate's partition for the same graph.
DEFAULT_STATE_ROOT = Path(tempfile.gettempdir()) / "maxcut-e-star-state"

#: Paths too broad to be mask roots: masking one of these would take away the
#: interpreter, `/tmp` itself or a home directory.  A mask must be a directory
#: *inside* the tree, not a filesystem root.
UNMASKABLE = frozenset({
    "/", "/tmp", "/home", "/root", "/usr", "/etc", "/var", "/opt", "/srv",
    "/proc", "/sys", "/dev", "/run", "/boot", "/mnt", "/media",
})


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
# filesystem isolation
# --------------------------------------------------------------------------- #

def _quote(text: str) -> str:
    """Single-quote a path for the wrapper's `sh`.  No expansion, ever."""
    return "'" + str(text).replace("'", "'\\''") + "'"


def _git_metadata_dir(start: Path) -> Path | None:
    """The `.git` entry of the repository `start` lives in, if there is one."""
    for parent in (start, *start.parents):
        entry = parent / ".git"
        if entry.exists():
            return entry
    return None


def keep_root() -> Path | None:
    """A writable filesystem outside every mask, for the exemption staging."""
    for base in KEEP_CANDIDATES:
        directory = Path(base)
        if directory.is_dir() and os.access(directory, os.W_OK):
            return directory
    return None


def _maskable(path: Path, *, allow_tmp_root: bool = False) -> bool:
    if not path.is_absolute() or path == Path("/"):
        return False
    if str(path) in UNMASKABLE:
        # `/tmp` and `/var/tmp` are maskable *only* through the dedicated
        # whole-filesystem rule below, and only when the staging directory lives
        # outside them: masking them with the staging area inside would hide the
        # very handles the exemptions need.
        return allow_tmp_root and str(path) in TMP_ROOTS
    return True


def isolation_policy(
    *,
    spec: Mapping[str, Any],
    graph_path: Path,
    out_path: Path,
    scratch: Path,
    state_dir: Path | None = None,
    extra_mask: Sequence[str | os.PathLike[str]] = (),
) -> dict[str, list[str]]:
    """Decide, in one place, what the candidate may see and what it must not.

    **Masked** (taken away from the child):

    * the task directory that owns this loader -- `suite/` (whose `generator`
      blocks reproduce the Planted partitions), `references/` (the witness
      store), `generators/`, every `e-star-state` tree under it;
    * the repository's `.git` -- `git show` is otherwise a complete bypass;
    * the state roots: `--state-dir` and E*'s default `--state-dir`, because
      they hold other candidates' artifacts for the same graphs;
    * the directory the input graph was read from, so a candidate cannot go back
      to the unreduced file behind the candidate-facing view;
    * the world-writable scratch filesystems (`/tmp`, `/var/tmp`) as a whole, when
      the exemption staging can live outside them.  Another harness's state root
      is an answer store -- `<state>/invocations/<delta>/<graph_id>/run1/
      partition.json` is a previous candidate's partition for one of these graphs
      -- and E* can neither enumerate the state roots of runs it did not start nor
      the copies those runs left behind.  A fresh tmpfs over each hides all of
      them and still leaves the candidate a writable scratch.

    **Bound back in** (the child's own realm): the staged entry and its directory,
    the interpreter that launches it, the run directory that holds its graph and
    the path it must write its artifact to, and its scratch directory.  The input
    graph is bound back as a *single file*, never with its directory: handing a
    candidate `suite/eval/G_eval_0007.json` must not also hand it
    `suite/eval/G_eval_0001.json`.

    A mask that does not exist is skipped and reported (`skipped_masks`): a
    path that is not there cannot leak.  A mask that *exists* is verified by the
    wrapper -- every witness path captured below must be gone, and the mask root
    must really be a mount point -- before the candidate starts, so a failed
    mount is a refusal, never a silent unmasked run.
    """
    here = Path(__file__).resolve().parent
    mask_needs: list[Path | None] = [
        here,
        _git_metadata_dir(here),
        DEFAULT_STATE_ROOT if DEFAULT_STATE_ROOT.is_dir() else None,
        Path(state_dir).resolve() if state_dir else None,
        Path(graph_path).resolve().parent,
    ]
    mask_needs += [Path(item).resolve() for item in extra_mask]
    stage = keep_root()
    tmp_roots: list[Path] = []
    if stage is not None:
        for base in TMP_ROOTS:
            root = Path(base)
            if not root.is_dir() or root == stage or stage in root.parents:
                continue
            if any(root == Path(item).resolve() for item in extra_mask):
                continue
            tmp_roots.append(root)
    mask_needs = [*mask_needs, *tmp_roots]

    # (path, is_directory): the graph is a file so that masking its directory
    # does not turn into re-exposing that directory.
    exempt_needs: list[tuple[Path, bool]] = [
        (Path(str(spec["entry_path"])).resolve().parent, True),
        (Path(out_path).resolve().parent, True),
        (Path(scratch).resolve(), True),
        (Path(graph_path).resolve(), False),
    ]
    exec_prefix = [str(part) for part in spec.get("exec_prefix") or ()]
    if exec_prefix and Path(exec_prefix[0]).is_absolute():
        exempt_needs.append((Path(exec_prefix[0]).resolve().parent, True))

    masks: list[Path] = []
    skipped: list[str] = []
    for need in mask_needs:
        if need is None:
            continue
        if not need.is_dir() or not _maskable(need, allow_tmp_root=bool(tmp_roots)):
            if need is not None and not need.is_dir():
                skipped.append(str(need))
            continue
        if need in masks:
            continue
        if any(need != other and other in need.parents for other in masks) or \
           any(other != need and need in other.parents for other in masks):
            # Keep only the outermost mask: a tmpfs over an ancestor already
            # covers the descendant, and the descendant's exemption is bound
            # back at its own path anyway.
            if any(other in need.parents for other in masks):
                continue
            masks = [other for other in masks if need not in other.parents]
        masks.append(need)

    exempt_dirs: list[Path] = []
    exempt_files: list[Path] = []
    for need, is_dir in exempt_needs:
        if not need.exists():
            continue
        if is_dir:
            if any(need == other or other in need.parents for other in exempt_dirs):
                continue
            exempt_dirs = [other for other in exempt_dirs if need not in other.parents]
            exempt_dirs.append(need)
        elif need not in exempt_files:
            exempt_files.append(need)
    # A file inside a directory that is already bound back needs no exemption of
    # its own -- and restoring one would write *through* the restored directory
    # into the real file, which is how an earlier revision emptied the view.
    exempt_files = [
        item for item in exempt_files
        if not any(other == item.parent or other in item.parents for other in exempt_dirs)
    ]
    exempts: list[tuple[Path, bool]] = (
        [(path, True) for path in exempt_dirs] + [(path, False) for path in exempt_files]
    )

    if stage is None and any(str(item) in TMP_ROOTS for item in extra_mask):
        skipped.append("a /tmp-style mask was requested but no staging directory outside it exists")
    masks = [mask for mask in masks if all(mask != path for path, _ in exempts)]
    exempts = [
        (path, is_dir) for path, is_dir in exempts
        if any(mask in path.parents for mask in masks)
    ]
    exempts.sort(key=lambda item: (not item[1], len(item[0].parts), str(item[0])))

    # One *witness path* per mask: something that is there now and must be gone
    # after the mask is up.  `ls -A` on the mask root is not usable for this,
    # because an exempt path restored inside it is legitimately visible again.
    witnesses: dict[str, list[str]] = {}
    for mask in masks:
        chosen: list[str] = []
        try:
            entries = sorted(mask.iterdir())
        except OSError:
            entries = []
        for entry in entries:
            if any(entry == path or path in entry.parents or entry in path.parents
                   for path, _ in exempts):
                continue
            chosen.append(str(entry))
            if len(chosen) == 3:
                break
        witnesses[str(mask)] = chosen
    return {
        "mask": [str(item) for item in sorted(masks, key=lambda p: (len(p.parts), str(p)))],
        "exempt": [{"path": str(path), "directory": bool(is_dir)} for path, is_dir in exempts],
        "mask_witnesses": witnesses,
        "skipped_masks": skipped,
    }


def fs_isolation_wrapper(policy: Mapping[str, Any], marker: Path, environment: Mapping[str, str]) -> str:
    """The `sh` program that installs the masks, then hands over to the candidate.

    Every step is checked and the program refuses (exit `FS_FAILURE_EXIT`) rather
    than continuing with a topology it could not build: a mount that did not
    happen is a refusal to measure, never a silent unmasked run.  The last acts
    before `exec` are to drop every capability -- so the candidate cannot undo a
    mask it can see -- and to re-establish §4's environment with `env -i`, so the
    wrapper's own `sh` cannot add `SHLVL`/`PWD` to the four keys §4 names.
    """
    masks = [str(item) for item in policy.get("mask") or ()]
    exempts = [
        (str(item["path"]), bool(item.get("directory")))
        for item in policy.get("exempt") or ()
    ]
    witnesses = policy.get("mask_witnesses") or {}
    stage = keep_root()
    if stage is None:
        raise RuntimeError("no writable staging directory outside the masks is available")  # pragma: no cover
    mount_tool = tool_path("mount") or "mount"
    mountpoint_tool = tool_path("mountpoint") or "mountpoint"
    setpriv_tool = tool_path("setpriv") or "setpriv"
    env_tool = tool_path("env") or "env"
    lines = [
        "set -eu",
        "fail() { echo \"E_STAR_ISOLATION_FAILURE: $1\" >&2; exit %d; }" % FS_FAILURE_EXIT,
        "umask 077",
        "KEEP=%s" % _quote(str(stage / ".e-star-keep")),
        'mkdir -p "$KEEP" || fail keep-mkdir',
        '%s -t tmpfs none "$KEEP" || fail keep-mount' % _quote(mount_tool),
    ]
    for index, (path, is_dir) in enumerate(exempts):
        if is_dir:
            lines.append('mkdir -p "$KEEP/e%d" || fail stage-mkdir%d' % (index, index))
        else:
            lines.append(': > "$KEEP/e%d" || fail stage-mkdir%d' % (index, index))
        lines.append('%s --bind %s "$KEEP/e%d" || fail stage-bind%d'
                     % (_quote(mount_tool), _quote(path), index, index))
    for index, path in enumerate(masks):
        lines.append('%s -t tmpfs none %s || fail mask%d' % (_quote(mount_tool), _quote(path), index))
    for index, (path, is_dir) in enumerate(exempts):
        parent = Path(path).parent
        lines.append('mkdir -p %s || fail restore-mkdir%d' % (_quote(str(parent)), index))
        if is_dir:
            lines.append('mkdir -p %s || fail restore-mkdir%d' % (_quote(path), index))
        else:
            lines.append(': > %s || fail restore-touch%d' % (_quote(path), index))
        lines.append('%s --bind "$KEEP/e%d" %s || fail restore-bind%d'
                     % (_quote(mount_tool), index, _quote(path), index))
    for index, path in enumerate(masks):
        for probe in witnesses.get(path) or ():
            lines.append('[ ! -e %s ] || fail mask-verify%d' % (_quote(probe), index))
        lines.append('%s -q %s || fail mask-not-a-mount%d'
                     % (_quote(mountpoint_tool), _quote(path), index))
    for index, (path, _is_dir) in enumerate(exempts):
        lines.append('[ -e %s ] || fail exempt-verify%d' % (_quote(path), index))
    lines.append('rm -f %s || fail marker-remove' % _quote(str(marker)))
    lines.append(': > %s || fail marker' % _quote(str(marker)))
    environment_argv = " ".join(
        "%s=%s" % (name, _quote(value)) for name, value in sorted(environment.items())
    )
    lines.append(
        'exec %s --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs '
        '%s -i %s "$@"' % (_quote(setpriv_tool), _quote(env_tool), environment_argv)
    )
    return "\n".join(lines)


def tool_path(name: str) -> str | None:
    """Locate a tool by absolute path first, PATH second.

    Never only PATH: the conformance probes deliberately hand E* a poisoned PATH
    to show the measurement does not depend on it, and a sandbox that silently
    disappears under a poisoned PATH would be worse than no sandbox.
    """
    for directory in ("/usr/bin", "/bin", "/usr/sbin", "/sbin"):
        candidate = Path(directory) / name
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def isolation_available() -> tuple[bool, str]:
    """Whether the enforceable form can be reached at all."""
    missing = [tool for tool in ("unshare", "setpriv") if tool_path(tool) is None]
    if missing:
        return False, "not installed at an absolute path or on PATH: " + ", ".join(missing)
    return True, ""


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
    fs_isolate: bool = False,
    state_dir: Path | None = None,
    extra_mask: Sequence[str] = (),
) -> dict[str, Any]:
    """Run one candidate subprocess to completion, to its own exit, or to tau.

    `fs_isolate` is additive to §4/§7 and independent of `net_isolate`.  When it
    is on, the candidate is started inside a private user+mount+PID namespace with
    the answer stores masked and its capabilities dropped, and `observation.argv`
    still records §4's own list -- the argv the *candidate* sees -- while
    `observation.spawn_argv` records what was actually executed.
    """
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    candidate_argv = [
        *[str(part) for part in spec["exec_prefix"]],
        str(spec["entry_path"]),
        "--graph", str(Path(graph_path).resolve()),
        "--out", str(out_path.resolve()),
        "--seed", str(int(seed)),
    ]
    marker = scratch / ISOLATION_MARKER
    policy: dict[str, Any] = {"mask": [], "exempt": [], "skipped_masks": []}
    isolation_prefix: list[str] = []
    isolation_error: str | None = None
    if fs_isolate:
        available, why = isolation_available()
        if not available:
            isolation_error = f"filesystem isolation was requested but `{why}`"
        elif keep_root() is None:
            isolation_error = ("filesystem isolation is on but no writable staging directory outside "
                               + ", ".join(TMP_ROOTS) + " exists, so the exemptions cannot be bound "
                               "back after masking")
        else:
            policy = isolation_policy(
                spec=spec, graph_path=Path(graph_path), out_path=out_path, scratch=scratch,
                state_dir=state_dir, extra_mask=extra_mask,
            )
            isolation_prefix = [
                tool_path("unshare") or "unshare",
                "-r", "-m", "-p", "-f", "--mount-proc",
                "--propagation", "private",
                *(["-n"] if net_isolate else []),
                "/bin/sh", "-c",
                fs_isolation_wrapper(policy, marker, candidate_environment(scratch)),
                "sh",
            ]
    elif net_isolate:
        isolation_prefix = [tool_path("unshare") or "unshare", "-rn"]
    spawn_argv = [*isolation_prefix, *candidate_argv]

    observation: dict[str, Any] = {
        "schema": SCHEMA_OBSERVATION,
        "argv": candidate_argv,
        "spawn_argv": spawn_argv,
        "net_isolate": bool(net_isolate),
        "fs_isolate": bool(fs_isolate),
        "isolation": policy,
        "isolation_error": isolation_error,
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
    if isolation_error is not None:
        observation["wall_ms"] = 0
        return observation

    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            spawn_argv,
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
    if isolation_prefix and not marker.exists() and not observation["timed_out"]:
        # The wrapper touches the marker on its last line before `exec`.  No
        # marker means the candidate was never reached -- the harness could not
        # build the topology it promised, so this is a harness failure and must
        # not be charged to the candidate (nor scored).
        observation["isolation_error"] = (
            "the filesystem-isolation wrapper did not reach the candidate "
            f"(exit {process.returncode}); stderr tail: {observation['stderr_tail'][-300:]!r}"
        )
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
    parser.add_argument(
        "--no-fs-isolate", dest="fs_isolate", action="store_false", default=FS_ISOLATE_DEFAULT,
        help="do NOT mask the answer stores (repository, .git, state roots) from the candidate; "
             "the default is to mask them, fail-closed",
    )
    parser.add_argument("--state-dir", default=None, help="state root of the calling evaluator, masked from the child")
    parser.add_argument(
        "--mask", action="append", default=[], metavar="PATH",
        help="mask one more path from the candidate (repeatable)",
    )
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
        fs_isolate=bool(args.fs_isolate),
        state_dir=Path(args.state_dir) if args.state_dir else None,
        extra_mask=list(args.mask),
    )
    print(json.dumps(observation, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
