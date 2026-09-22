#!/usr/bin/env python3
"""E* -- T1's harness-owned evaluator for the frozen max-cut heuristic search.

E* is ``Candidate -> Outcome`` for the study's A0/T1 evaluator-integration
conformance check.  It is frozen *outside* the runtime under test: no runtime's
provenance schema, cache or log directory is any part of this file's contract.
The objective is the unweighted max-cut edge count.

How this file serves the five first-principles constraints (`INTERFACE.md` §0):

(i)  **Frozen, recomputable identity.**  ``evaluator_source_sha256`` digests this
     file's and `e_star_child.py`'s bytes; ``graph_sha256`` is the graph file's
     sha256.  Both appear in every Outcome, so any number can be re-derived from
     the artifacts alone.
(ii) **The harness owns the realization.**  The candidate writes an *assignment*
     and nothing else.  The cut is recomputed here, from the harness's own
     in-memory copy of `graph.json` plus the candidate's `partition.json`.  A
     candidate's own report of its score is never read -- there is no field for
     it in §3's artifact, and a candidate that writes one is ignored.
(iii) **The score observably enters selection.**  The Outcome carries the
     objective together with join keys (candidate id, graph id, both hashes,
     theta) so an adapter can bind this measurement to a selection event.
(iv) **The budget is enforceable where the runtime cannot lie.**  Wall clock is
     measured by the parent around the child's whole lifetime; at tau the
     *process group* is SIGKILLed (§7).  A candidate cannot report its own
     runtime, and cannot survive tau.
(v)  **Improvement must hold on unseen instances.**  dev/eval are separate
     graph sets and `eval` is only ever aggregated on demand; nothing here
     selects on eval.

Two consequences the brief calls out explicitly, and where they are enforced:

* **The candidate never reports its own score.**  `recompute_cut_edges` is the
  only source of `cut_edges`; it reads the frozen graph bytes and the validated
  assignment.
* **The winner is decided on integers.**  `cut_edges` is an `int` and every
  comparison, threshold and aggregate below is integer or `fractions.Fraction`
  arithmetic.  `cut_fraction` is a *display* string rendered from the integers
  with exact decimal arithmetic; §5 forbids any decision from reading it, and
  nothing in this file does.

CLI:

    e_star.py evaluate --candidate <dir> --graph <graph.json> --seed <int>
                       --timeout <s> --out <outcome.json> [--emit-resources <path>]
    e_star.py aggregate --candidate <dir> --graph-set <dev|eval|calibration> --out <aggregate.json>
    e_star.py digest

E*'s own exit codes: 0 = ok, 2 = invalid, 3 = error, 4 = timeout.  E* never
emits a number in place of a failure: `cut_edges` is null for every status other
than `ok`, and null is never coerced to 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

# Resolve the loader by *location*, not by whatever the caller's sys.path says,
# so `evaluate` behaves the same from every working directory (§4 asks the same
# of candidates; E* holds itself to it too).
sys.path.insert(0, str(Path(__file__).resolve().parent))

import e_star_child as child  # noqa: E402

E_STAR_VERSION = "1.0.0"
SCHEMA_OUTCOME = "a0.maxcut.outcome/v1"
SCHEMA_AGGREGATE = "a0.maxcut.aggregate/v1"
SCHEMA_MANIFEST = "a0.maxcut.manifest/v1"
SCHEMA_GRAPH = "a0.maxcut.graph/v1"
SCHEMA_PARTITION = "a0.maxcut.partition/v1"

HERE = Path(__file__).resolve().parent
SOURCE_FILES = ("e_star.py", "e_star_child.py")
DEFAULT_SUITE_ROOT = HERE / "suite"
GRAPH_SETS = ("dev", "eval", "calibration")
FAMILIES = ("ER", "RR", "BA", "Planted")

STATUS_OK = "ok"
STATUS_INVALID = "invalid"
STATUS_ERROR = "error"
STATUS_TIMEOUT = "timeout"
STATUSES = (STATUS_OK, STATUS_INVALID, STATUS_ERROR, STATUS_TIMEOUT)

#: E*'s own process exit code per status.  Kept in the plumbing evaluator's
#: 0/2/3 shape with 4 added for §7's timeout status (DEVIATIONS.md D-T1-4).
EVALUATOR_EXIT_CODES = {
    STATUS_OK: 0,
    STATUS_INVALID: 2,
    STATUS_ERROR: 3,
    STATUS_TIMEOUT: 4,
}

#: Severity order for a multi-graph verdict: the aggregate's own exit code is
#: the worst status it saw, so `aggregate` and `evaluate` use one table.
STATUS_SEVERITY = (STATUS_TIMEOUT, STATUS_ERROR, STATUS_INVALID, STATUS_OK)

DEFAULT_SEED = 1337
DEFAULT_TIMEOUT_S = child.DEFAULT_TIMEOUT_S

#: How many places `cut_fraction` is rendered to.  §5's example
#: (`0.6191406250000000000` for 317/512) is exactly this width.
CUT_FRACTION_PLACES = 19

#: §11: T1's new `failure.kind` values mapped onto the frozen table in
#: `a0/contract/selection/simpleloop.selection.json`.  This is the explicit
#: extension §11 permits; it is also emitted by `digest` so a consumer can read
#: it without importing this module.
FAILURE_STAGE_MAPPING: dict[str, str] = {
    "invalid_configuration": "verify_failed",
    "malformed_partition": "verify_failed",
    "missing_partition": "verify_failed",
    "candidate_entry_failed": "resolve_failed",
    "candidate_call_raised": "evaluator_failed",
    "candidate_crashed": "evaluator_failed",
    "candidate_refused": "evaluator_failed",
    "non_deterministic": "verify_failed",
    "runtime_budget_exceeded": "timeout",
    "input_tampered": "evaluator_failed",
    "graph_invalid": "resolve_failed",
    "harness_error": "evaluator_failed",
}

#: failure.kind is a function of status, and §5 requires them to agree.
KINDS_BY_STATUS: dict[str, tuple[str, ...]] = {
    STATUS_OK: (),
    STATUS_INVALID: ("invalid_configuration", "malformed_partition", "missing_partition"),
    STATUS_ERROR: (
        "candidate_entry_failed", "candidate_call_raised", "candidate_crashed",
        "candidate_refused", "non_deterministic", "input_tampered", "harness_error",
    ),
    STATUS_TIMEOUT: ("runtime_budget_exceeded",),
}


class GraphInvalid(Exception):
    """The graph file is not a valid §2 graph: a harness input problem."""


# --------------------------------------------------------------------------- #
# canonical serialisation (§2, §3)
# --------------------------------------------------------------------------- #

def canonical_json(payload: object) -> str:
    """The one canonical byte form of any E* payload: sorted keys, compact
    separators, ASCII, a single trailing newline."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def source_file_digests() -> list[dict[str, Any]]:
    return [
        {"name": name, "bytes": (HERE / name).stat().st_size, "sha256": sha256_bytes((HERE / name).read_bytes())}
        for name in SOURCE_FILES
    ]


def evaluator_source_digest() -> str:
    """Content digest of E*'s own sources, independent of where they live."""
    return sha256_text(canonical_json(source_file_digests()))


def canonical_digest(outcome: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in outcome.items() if key != "canonical_digest"}
    return sha256_text(canonical_json(payload))


# --------------------------------------------------------------------------- #
# exact display rendering (never a decision input)
# --------------------------------------------------------------------------- #

def decimal_string(numerator: int, denominator: int, places: int = CUT_FRACTION_PLACES) -> str | None:
    """Render `numerator/denominator` as a fixed-point decimal string, using
    integers only (round-half-up).

    Deliberately *not* `f"{numerator / denominator:.19f}"`: §5 makes
    `cut_fraction` a display field derived from the integers by a deterministic
    rule, and doing the rounding in exact arithmetic means the string is a
    function of the two integers alone -- not of the platform's float
    formatting, and not of which interpreter rendered it.
    """
    if denominator == 0:
        return None
    scale = 10 ** places
    scaled = (2 * numerator * scale + denominator) // (2 * denominator)
    whole, fraction = divmod(scaled, scale)
    return f"{whole}.{fraction:0{places}d}"


# --------------------------------------------------------------------------- #
# the graph (§2)
# --------------------------------------------------------------------------- #

def read_graph(graph_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and fully validate a §2 graph, freezing its bytes for recomputation.

    The returned `raw` is the harness's own copy: `cut_edges` is always computed
    from these bytes, never from a re-read of the path, so a candidate that
    rewrites `graph.json` mid-run cannot inflate its own score.  The on-disk
    bytes are compared against this copy afterwards so the tampering is reported
    rather than silently ignored.
    """
    path = Path(graph_path).expanduser().resolve()
    if not path.is_file():
        raise GraphInvalid(f"graph not found: {path}")
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GraphInvalid(f"graph is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise GraphInvalid("graph must be a JSON object")
    if document.get("schema") != SCHEMA_GRAPH:
        raise GraphInvalid(f"graph schema must be {SCHEMA_GRAPH!r}, got {document.get('schema')!r}")
    graph_id = document.get("graph_id")
    if not isinstance(graph_id, str) or not graph_id:
        raise GraphInvalid("graph_id must be a non-empty string")
    family = document.get("family")
    if family not in FAMILIES:
        raise GraphInvalid(f"family must be one of {FAMILIES}, got {family!r}")
    n = document.get("n")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise GraphInvalid(f"n must be a positive integer, got {n!r}")
    edges_raw = document.get("edges")
    if not isinstance(edges_raw, list):
        raise GraphInvalid("edges must be a list")
    if "weight" in document:
        raise GraphInvalid("weighted graphs are outside §2: the file must not carry a weight field")

    edges: list[tuple[int, int]] = []
    for index, edge in enumerate(edges_raw):
        if not isinstance(edge, list) or len(edge) != 2:
            raise GraphInvalid(f"edge #{index} must be a 2-element list, got {edge!r}")
        u, v = edge
        for value in (u, v):
            if not isinstance(value, int) or isinstance(value, bool):
                raise GraphInvalid(f"edge #{index} has a non-integer endpoint: {edge!r}")
        if not (0 <= u < n and 0 <= v < n):
            raise GraphInvalid(f"edge #{index} is out of range for n={n}: {edge!r}")
        if u == v:
            raise GraphInvalid(f"edge #{index} is a self-loop: {edge!r}")
        if u > v:
            raise GraphInvalid(f"edge #{index} must be written [u, v] with u < v: {edge!r}")
        edges.append((u, v))
    if edges != sorted(edges):
        raise GraphInvalid("edges must be sorted in ascending lexicographic order")
    if len(set(edges)) != len(edges):
        raise GraphInvalid("the graph has duplicate edges")

    canonical = raw == canonical_json(document).encode("ascii")
    return {
        "path": str(path),
        "graph_id": graph_id,
        "family": family,
        "n": n,
        "edges": edges,
        "edges_total": len(edges),
        "sha256": sha256_bytes(raw),
        "bytes_len": len(raw),
        "raw": raw,
        "canonical_form": canonical,
        "isolated_vertices": n - len({node for edge in edges for node in edge}),
        "generator": document.get("generator"),
    }


def recompute_cut_edges(edges: Sequence[tuple[int, int]], assignment: Sequence[int]) -> int:
    """The authoritative integer.  One comparison per edge, in the graph's own
    canonical edge order, so the value cannot depend on iteration order,
    interpreter or machine."""
    return sum(1 for u, v in edges if assignment[u] != assignment[v])


# --------------------------------------------------------------------------- #
# the candidate-facing view of the graph (§2 distribution provenance is not input)
# --------------------------------------------------------------------------- #

#: §2's `generator` block carries *distribution* parameters -- and, for the
#: Planted family, the seed that reproduces the planted partition exactly.  The
#: block is provenance for the harness (it is what makes regeneration a check),
#: never an input: §2 itself says `generator.seed` "不得被任何判定引用".
#:
#: A candidate is therefore handed the graph *without* it.  The frozen suite files
#: stay byte-identical (their sha256 is the data identity, and every hash-keyed
#: artifact -- `suite/manifest.json`, `references/targets.json`, the gate,
#: C*(T1)'s table -- keeps its value), and the Outcome records both digests: the
#: suite bytes and the bytes actually handed over.
CANDIDATE_GRAPH_KEYS = ("schema", "graph_id", "family", "n", "edges")


def candidate_graph_document(graph: Mapping[str, Any]) -> dict[str, Any]:
    """The one document a candidate is given: identity, shape and the edge list."""
    return {
        "schema": SCHEMA_GRAPH,
        "graph_id": str(graph["graph_id"]),
        "family": str(graph["family"]),
        "n": int(graph["n"]),
        "edges": [[int(u), int(v)] for u, v in graph["edges"]],
    }


def write_candidate_view(graph: Mapping[str, Any], directory: Path) -> dict[str, Any]:
    """Write the candidate-facing view beside the run it belongs to.

    The view lives in the private run directory, not next to the suite file: the
    loader masks the suite from the candidate, so the view is the *only* graph a
    candidate can read, and its bytes are what `candidate_graph_sha256` digests.
    """
    document = candidate_graph_document(graph)
    payload = canonical_json(document).encode("ascii")
    path = Path(directory) / "candidate_graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": str(path),
        "sha256": sha256_bytes(payload),
        "bytes_len": len(payload),
        "keys": sorted(document),
    }


# --------------------------------------------------------------------------- #
# the candidate artifact (§3) and §6's decision rules
# --------------------------------------------------------------------------- #

def parse_partition(raw_bytes: bytes | None, graph: Mapping[str, Any]) -> dict[str, Any]:
    """§3 + §6 rule 2.  Returns `{"assignment": [...]}` or `{"kind","detail"}`.

    `kind` is one of `missing_partition` / `malformed_partition`; both are
    `invalid`, never `error`, because §3 calls every one of these cases a
    format violation.
    """
    if raw_bytes is None:
        return {"kind": "missing_partition", "detail": "the candidate wrote no partition.json"}
    try:
        document = json.loads(raw_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"kind": "malformed_partition", "detail": f"partition.json is not valid JSON: {exc}"}
    if not isinstance(document, dict):
        return {"kind": "malformed_partition", "detail": "partition.json must be a JSON object"}
    if document.get("schema") != SCHEMA_PARTITION:
        return {
            "kind": "malformed_partition",
            "detail": f"schema must be {SCHEMA_PARTITION!r}, got {document.get('schema')!r}",
        }
    if document.get("graph_id") != graph["graph_id"]:
        return {
            "kind": "malformed_partition",
            "detail": f"graph_id must be {graph['graph_id']!r}, got {document.get('graph_id')!r}",
        }
    assignment = document.get("assignment")
    if not isinstance(assignment, list):
        return {"kind": "malformed_partition", "detail": "assignment must be a list"}
    if len(assignment) != int(graph["n"]):
        return {
            "kind": "malformed_partition",
            "detail": f"assignment length {len(assignment)} != graph n {graph['n']}",
        }
    for index, value in enumerate(assignment):
        # `bool` is a subclass of `int` in Python, so `True` would otherwise pass
        # as the integer 1; §3 requires integer 0/1 and JSON `true` is not that.
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            return {
                "kind": "malformed_partition",
                "detail": f"assignment[{index}] = {value!r} is not the integer 0 or 1",
            }
    return {"assignment": assignment, "canonical_bytes": canonical_json(document).encode("ascii")}


# --------------------------------------------------------------------------- #
# one graph, start to finish
# --------------------------------------------------------------------------- #

def evaluate_graph(
    *,
    graph: Mapping[str, Any],
    spec: Mapping[str, Any],
    seed: int,
    timeout_s: float,
    state_dir: Path,
    source_digest: str,
    delta: str,
    net_isolate: bool = False,
    fs_isolate: bool = False,
    extra_mask: Sequence[str] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one candidate twice on one graph and decide the §6 verdict.

    Two invocations, not one: §6 rule 4 freezes determinism *per (candidate
    bytes, graph bytes, seed)*, so a single run cannot establish it.  The two
    runs get different scratch directories on purpose -- that way a candidate
    that quietly depends on its own cwd, or on residue from a previous run, is
    caught by the same check.

    Determinism is compared on the **canonical bytes** of the parsed partition
    (§3's own canonical form), which is what §6 rule 4 names.  The raw-bytes
    comparison is recorded as a diagnostic only.

    What the candidate is handed is `write_candidate_view`'s bytes -- §2's five
    keys, no `generator` block -- while `cut_edges` is always recomputed from the
    harness's own frozen copy of the *suite* bytes.
    """
    graph_id = str(graph["graph_id"])
    base = Path(state_dir) / "invocations" / delta / graph_id
    parsed: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    raw_partitions: list[bytes | None] = []
    views: list[dict[str, Any]] = []

    for index in (1, 2):
        run_dir = base / f"run{index}"
        out_path = run_dir / "partition.json"
        run_dir.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            out_path.unlink()
        view = write_candidate_view(graph, run_dir)
        views.append(view)
        observation = child.run_invocation(
            spec=spec,
            graph_path=Path(view["path"]),
            out_path=out_path,
            seed=seed,
            timeout_s=timeout_s,
            scratch=run_dir / "scratch",
            net_isolate=net_isolate,
            fs_isolate=fs_isolate,
            state_dir=Path(state_dir),
            extra_mask=extra_mask,
        )
        observations.append(observation)
        (run_dir / "stdout.txt").write_text(observation["stdout_tail"], encoding="utf-8")
        (run_dir / "stderr.txt").write_text(observation["stderr_tail"], encoding="utf-8")
        (run_dir / "invocation.json").write_bytes(canonical_json(observation).encode("utf-8"))
        raw = out_path.read_bytes() if out_path.is_file() else None
        raw_partitions.append(raw)
        parsed.append(parse_partition(raw, graph))

    status, failure = _decide(graph=graph, observations=observations, parsed=parsed, raw=raw_partitions)

    cut: int | None = None
    if status == STATUS_OK:
        cut = recompute_cut_edges(graph["edges"], parsed[0]["assignment"])

    # Input integrity, on both files: the suite bytes the number is computed from,
    # and the bytes actually handed to the candidate.
    suite_tampered = sha256_bytes(Path(graph["path"]).read_bytes()) != graph["sha256"]
    handed_tampered = any(
        Path(view["path"]).is_file() and sha256_bytes(Path(view["path"]).read_bytes()) != view["sha256"]
        for view in views
    )
    if suite_tampered or handed_tampered:
        status = STATUS_ERROR
        cut = None
        which = "graph.json" if suite_tampered else "the candidate-facing graph view"
        failure = {
            "kind": "input_tampered",
            "detail": f"{which} changed while the candidate ran; the frozen copy was used for "
                      "recomputation",
        }

    canonical_partitions = [p.get("canonical_bytes") for p in parsed]
    determinism_identical = (
        all(item is not None for item in canonical_partitions)
        and canonical_partitions[0] == canonical_partitions[1]
    )
    outcome: dict[str, Any] = {
        "schema": SCHEMA_OUTCOME,
        "e_star_version": E_STAR_VERSION,
        "evaluator_source_sha256": source_digest,
        "graph_id": graph_id,
        "graph_sha256": graph["sha256"],
        "graph_family": graph["family"],
        "candidate_id": spec["candidate_id"],
        "candidate_source_sha256": spec["source_sha256"],
        "status": status,
        "cut_edges": cut,
        "cut_fraction": None if cut is None else decimal_string(cut, int(graph["edges_total"])),
        "edges_total": int(graph["edges_total"]),
        "failure": failure,
        # §5's `interpreted` block, minus `wall_ms`, which is an execution-
        # environment quantity: it is measured and reported in the resources
        # sidecar, never in the canonical Outcome (DEVIATIONS.md D-T1-1).
        "interpreted": {
            "exit_code": None if status == STATUS_TIMEOUT else observations[0]["exit_code"],
            "wall_ms": None,
            # §4 labels an *exit code*; a SIGKILLed process never had one, so the
            # label is null for a timeout rather than a misleading "other".
            "exit_label": None if status == STATUS_TIMEOUT else observations[0]["exit_label"],
            "timed_out": status == STATUS_TIMEOUT,
            "process_group_killed": observations[0]["process_group_killed"],
            "exit_codes": [observation["exit_code"] for observation in observations],
        },
        "interpreter": {
            "implementation": sys.implementation.name,
            "version": "{}.{}.{}".format(*sys.version_info[:3]),
            "executable": sys.executable,
        },
        "theta": {"seed": int(seed), "timeout_s": float(timeout_s)},
        # The two identities of the input: the frozen suite file the number is
        # recomputed from, and the bytes the candidate was actually handed
        # (`graph_sha256` is the former; this block is the latter).
        "candidate_graph_sha256": views[0]["sha256"],
        "candidate_graph_bytes": views[0]["bytes_len"],
        "candidate_graph_keys": views[0]["keys"],
        "candidate_graph_schema": "a0.maxcut.candidate_graph/v1",
        "determinism": {
            "runs": 2,
            "compared": "canonical bytes of partition.json (§6 rule 4)",
            "canonical_sha256": [
                None if item is None else sha256_bytes(item) for item in canonical_partitions
            ],
            "identical": determinism_identical,
            "raw_bytes_identical": (
                raw_partitions[0] is not None and raw_partitions[0] == raw_partitions[1]
            ),
        },
        # Timings are environment-dependent and deliberately excluded from the
        # canonical Outcome (the plumbing evaluator does the same).  The
        # measurements live in `resources.json` and in `--emit-resources`.
        "resources": None,
    }
    outcome["canonical_digest"] = canonical_digest(outcome)
    resources = {
        "schema": "a0.maxcut.resources/v1",
        "graph_id": graph_id,
        "candidate_id": spec["candidate_id"],
        "candidate_source_sha256": spec["source_sha256"],
        "graph_sha256": graph["sha256"],
        "candidate_graph_sha256": views[0]["sha256"],
        "fs_isolate": bool(fs_isolate),
        "theta": {"seed": int(seed), "timeout_s": float(timeout_s)},
        "runs": [
            {
                "index": index + 1,
                "wall_ms": observation["wall_ms"],
                "exit_code": observation["exit_code"],
                "exit_label": observation["exit_label"],
                "timed_out": observation["timed_out"],
                "process_group_killed": observation["process_group_killed"],
                "spawn_error": observation["spawn_error"],
                "isolation_error": observation.get("isolation_error"),
                "scratch": observation["cwd"],
                "env": observation["env"],
                "argv": observation["argv"],
                "graph_path": observation["graph_path"],
                "isolation": observation.get("isolation"),
            }
            for index, observation in enumerate(observations)
        ],
        "wall_ms_max": max(int(observation["wall_ms"] or 0) for observation in observations),
        "status": status,
        "failure_kind": None if failure is None else failure["kind"],
    }
    return outcome, resources


def _decide(
    *,
    graph: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    parsed: Sequence[Mapping[str, Any]],
    raw: Sequence[bytes | None],
) -> tuple[str, dict[str, Any] | None]:
    """§6's frozen rules, plus the precedence among them this file declares.

    Precedence (documented in README.md, and the only degree of freedom §6
    leaves): the harness's own timeout first, because at tau there is no
    artifact to judge; then a genuine candidate failure (spawn failure, exit 30,
    exit 40, any other non-zero); then the candidate's own declaration `invalid`
    (exit 20); then artifact validation; then determinism.  A run that failed is
    never converted into a number at any step.
    """
    for observation in observations:
        if observation["timed_out"]:
            return STATUS_TIMEOUT, {
                "kind": "runtime_budget_exceeded",
                "detail": (
                    f"tau = {observation['timeout_s']} s reached; the process group was SIGKILLed "
                    "(§7: a timeout is not an exit code)"
                ),
            }
    for observation in observations:
        if observation.get("isolation_error"):
            # The harness could not build the topology it promised.  That is a
            # harness failure: it is neither the candidate's fault nor a number,
            # and §6 rule 5 forbids turning it into one.
            return STATUS_ERROR, {"kind": "harness_error", "detail": str(observation["isolation_error"])}
    for observation in observations:
        if observation["spawn_error"]:
            return STATUS_ERROR, {"kind": "candidate_entry_failed", "detail": str(observation["spawn_error"])}
    ordered_codes = [observation["exit_label"] for observation in observations]
    for label, kind in (
        ("internal_error", "candidate_call_raised"),
        ("refused", "candidate_refused"),
        ("other", "candidate_crashed"),
    ):
        if label in ordered_codes:
            index = ordered_codes.index(label)
            return STATUS_ERROR, {
                "kind": kind,
                "detail": f"candidate exited {observations[index]['exit_code']} "
                          f"(§4 label {label!r}) on invocation {index + 1}",
            }
    if "declared_invalid" in ordered_codes:
        index = ordered_codes.index("declared_invalid")
        return STATUS_INVALID, {
            "kind": "invalid_configuration",
            "detail": f"candidate declared its own output invalid (exit 20) on invocation {index + 1}",
        }
    for index, item in enumerate(parsed):
        if "assignment" not in item:
            return STATUS_INVALID, {"kind": item["kind"], "detail": f"invocation {index + 1}: {item['detail']}"}
    if parsed[0]["canonical_bytes"] != parsed[1]["canonical_bytes"]:
        return STATUS_ERROR, {
            "kind": "non_deterministic",
            "detail": (
                "two invocations with identical (candidate bytes, graph bytes, seed) produced different "
                "partition.json canonical bytes"
            ),
        }
    return STATUS_OK, None


# --------------------------------------------------------------------------- #
# aggregation (§5) -- exact rational arithmetic
# --------------------------------------------------------------------------- #

def exact_score(pairs: Sequence[tuple[int, int]]) -> Fraction | None:
    """`(sum of cut_edges) / (sum of edges_total)` over the contributing graphs.

    `Fraction` reduces, so the result is the reduced fraction §5 asks for.  The
    denominator is a sum of `edges_total`, which is what makes this the
    edge-weighted rate over the whole set rather than a mean of per-graph rates;
    the two agree only when every graph in the set has the same `edges_total`.
    `None` means nothing was scored -- an undefined rate, which is not zero.
    """
    numerator = sum(cut for cut, _ in pairs)
    denominator = sum(edges for _, edges in pairs)
    if denominator == 0:
        return None
    return Fraction(numerator, denominator)


def fraction_payload(value: Fraction | None) -> dict[str, int]:
    """§5's `{"numerator","denominator"}`.

    `{"numerator": 0, "denominator": 0}` means *undefined*: no graph in the set
    was scored, so no rate exists.  It is deliberately not `0/1`, because §6
    rule 5 forbids reporting a failure as a score of zero.
    """
    if value is None:
        return {"numerator": 0, "denominator": 0}
    return {"numerator": value.numerator, "denominator": value.denominator}


def discover_graphs(graph_set: str, suite_root: Path) -> list[dict[str, Any]]:
    """§5's `--graph-set`, resolved under the suite root.

    When `manifest.json` exists its recorded sha256 for each graph is verified:
    §2 makes the file's sha256 the *data identity*, so a suite that does not
    match its own manifest must not silently produce a score.
    """
    directory = (suite_root / graph_set).resolve()
    if not directory.is_dir():
        raise GraphInvalid(f"graph set not found: {directory}")
    manifest_path = suite_root / "manifest.json"
    recorded: dict[str, str] = {}
    order: list[str] = []
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GraphInvalid(f"{manifest_path} is not valid JSON: {exc}") from exc
        entries = manifest.get("graphs") if isinstance(manifest, dict) else None
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("graph_id"):
                    recorded[str(entry["graph_id"])] = str(
                        entry.get("sha256") or entry.get("graph_sha256") or ""
                    )
        elif isinstance(entries, dict):
            for key, entry in entries.items():
                if isinstance(entry, dict):
                    recorded[str(entry.get("graph_id") or key)] = str(
                        entry.get("sha256") or entry.get("graph_sha256") or ""
                    )
        if not recorded:
            raise GraphInvalid(
                f"{manifest_path} exists but carries no recognisable graph entries; refusing to "
                "aggregate without verifying §2's data identity"
            )

    paths: list[Path] = []
    for candidate_path in sorted(directory.glob("*.json")):
        if candidate_path.name == "manifest.json":
            continue
        paths.append(candidate_path)

    graphs: list[dict[str, Any]] = []
    for path in paths:
        graph = read_graph(path)
        expected = recorded.get(graph["graph_id"])
        graph["manifest_sha256"] = expected
        graph["manifest_match"] = None if not expected else (expected == graph["sha256"])
        if expected and expected != graph["sha256"]:
            raise GraphInvalid(
                f"{path} sha256 {graph['sha256']} does not match manifest entry {expected}"
            )
        graphs.append(graph)
    if not graphs:
        raise GraphInvalid(f"graph set {directory} contains no graphs")
    return graphs


def aggregate_outcomes(
    *,
    candidate_id: str,
    graph_set: str,
    outcomes: Sequence[Mapping[str, Any]],
    graphs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """§5's aggregate document.  Every rate here comes from `exact_score`."""
    counts = {status: 0 for status in STATUSES}
    scored: list[tuple[int, int]] = []
    per_family: dict[str, list[tuple[int, int]]] = {family: [] for family in FAMILIES}
    for outcome, graph in zip(outcomes, graphs):
        status = str(outcome["status"])
        counts[status] = counts.get(status, 0) + 1
        if status != STATUS_OK:
            # §6 rule 5: a non-ok outcome contributes nothing -- not a zero.
            continue
        cut = outcome["cut_edges"]
        if not isinstance(cut, int) or isinstance(cut, bool):
            raise ValueError(f"ok outcome for {outcome['graph_id']} has a non-integer cut_edges")
        scored.append((cut, int(graph["edges_total"])))
        per_family.setdefault(str(graph["family"]), []).append((cut, int(graph["edges_total"])))

    return {
        "schema": SCHEMA_AGGREGATE,
        "candidate_id": candidate_id,
        "graph_set": graph_set,
        "counts": counts,
        "score_exact": fraction_payload(exact_score(scored)),
        "per_family_exact": {
            family: fraction_payload(exact_score(pairs)) for family, pairs in sorted(per_family.items())
        },
        "outcome_digests": [str(outcome["canonical_digest"]) for outcome in outcomes],
        # Additive provenance (§5's schema is a floor, not a ceiling); no
        # decision reads it, but it is what makes the aggregate recomputable.
        "evaluator_source_sha256": evaluator_source_digest(),
        "theta": dict(outcomes[0]["theta"]) if outcomes else None,
        "graphs": [
            {
                "graph_id": graph["graph_id"],
                "family": graph["family"],
                "n": graph["n"],
                "edges_total": graph["edges_total"],
                "sha256": graph["sha256"],
                "manifest_match": graph.get("manifest_match"),
            }
            for graph in graphs
        ],
        "scored_graphs": len(scored),
        "edges_total_scored": sum(edges for _, edges in scored),
        "cut_edges_total": sum(cut for cut, _ in scored),
    }


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def _state_root(args: argparse.Namespace) -> Path:
    root = Path(args.state_dir) if getattr(args, "state_dir", None) else Path(tempfile.gettempdir()) / "maxcut-e-star-state"
    root.mkdir(parents=True, exist_ok=True)
    return root


#: Optional, task-owned list of *additional* paths to mask from a candidate.  It
#: exists because the answer stores are not all inside this repository: a rebuild
#: scratch tree, an exported corpus or a copied state directory is still readable
#: by the candidate, and neither E* nor the A1 harness can enumerate those from
#: first principles.  `references/leak-proof/run_leak_probe.py` scans for them and
#: writes what it finds here; a missing file means "no extras", a malformed one is
#: a hard error (the policy must never be silently ignored).
FS_POLICY_PATH = HERE / "references" / "witnesses" / "fs_policy.json"


def extra_mask_paths() -> list[str]:
    path = FS_POLICY_PATH
    if not path.is_file():
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphInvalid(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("extra_masks", []), list):
        raise GraphInvalid(f"{path} must be an object with a list `extra_masks`")
    return [str(item) for item in document.get("extra_masks", [])]


def _delta_tag(spec: Mapping[str, Any], seed: int, timeout_s: float) -> str:
    payload = {
        "candidate_source_sha256": spec["source_sha256"],
        "seed": int(seed),
        "timeout_s": float(timeout_s),
    }
    return sha256_text(canonical_json(payload))[:16]


def stage_candidate(spec: Mapping[str, Any], state_dir: Path) -> dict[str, Any]:
    """Copy the candidate below the state root and run *that* copy.

    The plumbing evaluator does this for the same reason it applies here: the
    candidate directory belongs to the caller, so anything that writes to it
    between E*'s two invocations -- a checkout, a rebuild, a `git clean` -- would
    otherwise be indistinguishable from the candidate being non-deterministic,
    and a candidate could be swapped underneath a frozen measurement.  The copy
    is content-addressed by `candidate_source_sha256`, and the copy's own digest
    is re-derived and compared before anything is measured.

    Content is the *only* thing carried across by default.  The one exception is
    a candidate that declared `exec: []` in its `candidate.json`, i.e. asked to
    be executed directly rather than through an interpreter (D-T1-10): for those,
    the source file modes are copied too and the staged entry's executable bit is
    checked here, so the declared launch is either honoured or reported as a
    precise error instead of surfacing as a bare `PermissionError` at spawn time.
    """
    source = Path(str(spec["candidate_dir"]))
    target = Path(state_dir) / "candidates" / str(spec["source_sha256"])[:16]
    target.mkdir(parents=True, exist_ok=True)
    preserve_mode = not spec["exec_prefix"]
    for item in spec["source_files"]:  # type: ignore[index]
        data = (source / str(item["path"])).read_bytes()
        if sha256_bytes(data) != item["sha256"]:
            raise ValueError(f"candidate file changed between hashing and staging: {item['path']}")
        destination = target / str(item["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.read_bytes() != data:
            destination.write_bytes(data)
        if preserve_mode:
            os.chmod(destination, stat.S_IMODE((source / str(item["path"])).stat().st_mode))
    staged = dict(spec)
    staged["candidate_dir"] = str(target)
    staged["entry_path"] = str((target / str(spec["entry"])).resolve())
    staged["source_files"] = child.candidate_files(target)
    if child.candidate_source_digest(staged["source_files"]) != spec["source_sha256"]:
        raise ValueError("the staged candidate's digest does not match the measured candidate's digest")
    if preserve_mode and not os.access(staged["entry_path"], os.X_OK):
        raise ValueError(
            f"{spec['candidate_id']} declares direct execution (`exec: []`) but the staged entry "
            f"{staged['entry_path']} is not executable"
        )
    return staged


def cmd_evaluate(args: argparse.Namespace) -> int:
    source_digest = evaluator_source_digest()
    try:
        graph = read_graph(args.graph)
    except GraphInvalid as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    try:
        spec = child.resolve_candidate(args.candidate)
    except child.CandidateResolutionError as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]

    state_dir = _state_root(args)
    if args.net_isolate and child.tool_path("unshare") is None:
        print("e_star: --net-isolate was requested but `unshare` is not installed; refusing to measure "
              "in an open topology", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    if args.fs_isolate:
        available, why = child.isolation_available()
        if not available:
            print(f"e_star: filesystem isolation is on by default but {why}; pass --no-fs-isolate only "
                  "with a documented reason -- without it a candidate can read the reference solutions, "
                  "the suite's generator blocks and the git objects", file=sys.stderr)
            return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    try:
        spec = stage_candidate(spec, state_dir)
    except ValueError as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    delta = f"pid{os.getpid()}-{_delta_tag(spec, args.seed, args.timeout)}"
    try:
        masks = list(args.fs_mask) + extra_mask_paths()
    except GraphInvalid as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    outcome, resources = evaluate_graph(
        graph=graph, spec=spec, seed=int(args.seed), timeout_s=float(args.timeout),
        state_dir=state_dir, source_digest=source_digest, delta=delta,
        net_isolate=bool(args.net_isolate),
        fs_isolate=bool(args.fs_isolate),
        extra_mask=masks,
    )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(canonical_json(outcome).encode("utf-8"))

    resources["graph_sha256"] = graph["sha256"]
    resources_text = canonical_json(resources)
    (state_dir / "resources.json").write_bytes(resources_text.encode("utf-8"))
    if args.emit_resources:
        resources_path = Path(args.emit_resources).expanduser()
        resources_path.parent.mkdir(parents=True, exist_ok=True)
        resources_path.write_bytes(resources_text.encode("utf-8"))

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "e_star_version": E_STAR_VERSION,
        "evaluator_source_sha256": source_digest,
        "candidate_id": spec["candidate_id"],
        "candidate_source_sha256": spec["source_sha256"],
        "graph_id": graph["graph_id"],
        "graph_sha256": graph["sha256"],
        "seed": int(args.seed),
        "timeout_s": float(args.timeout),
        "status": outcome["status"],
        "cut_edges": outcome["cut_edges"],
        "edges_total": outcome["edges_total"],
        "candidate_graph_sha256": outcome["candidate_graph_sha256"],
        "fs_isolate": bool(args.fs_isolate),
        "failure_kind": None if outcome["failure"] is None else outcome["failure"]["kind"],
        "canonical_digest": outcome["canonical_digest"],
    }
    print(f"E_STAR_MANIFEST {json.dumps(manifest, ensure_ascii=False, sort_keys=True)}")
    print(f"e_star: status={outcome['status']} out={out_path}", file=sys.stderr)
    if outcome["failure"]:
        print(f"e_star: failure={outcome['failure']['kind']}: {outcome['failure']['detail']}", file=sys.stderr)
    return EVALUATOR_EXIT_CODES[outcome["status"]]


def cmd_aggregate(args: argparse.Namespace) -> int:
    source_digest = evaluator_source_digest()
    suite_root = Path(args.suite_root).expanduser().resolve() if args.suite_root else DEFAULT_SUITE_ROOT
    try:
        graphs = discover_graphs(args.graph_set, suite_root)
    except GraphInvalid as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    try:
        spec = child.resolve_candidate(args.candidate)
    except child.CandidateResolutionError as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]

    state_dir = _state_root(args)
    if args.fs_isolate:
        available, why = child.isolation_available()
        if not available:
            print(f"e_star: filesystem isolation is on by default but {why}; pass --no-fs-isolate only "
                  "with a documented reason", file=sys.stderr)
            return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    try:
        spec = stage_candidate(spec, state_dir)
    except ValueError as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    try:
        masks = list(args.fs_mask) + extra_mask_paths()
    except GraphInvalid as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]
    delta = f"agg-pid{os.getpid()}-{_delta_tag(spec, args.seed, args.timeout)}"
    outcomes: list[dict[str, Any]] = []
    per_graph_resources: list[dict[str, Any]] = []
    for graph in graphs:
        outcome, resources = evaluate_graph(
            graph=graph, spec=spec, seed=int(args.seed), timeout_s=float(args.timeout),
            state_dir=state_dir, source_digest=source_digest, delta=delta,
            net_isolate=bool(args.net_isolate),
            fs_isolate=bool(args.fs_isolate),
            extra_mask=masks,
        )
        outcomes.append(outcome)
        per_graph_resources.append(resources)
        outcome_path = state_dir / "aggregate" / delta / f"{graph['graph_id']}.outcome.json"
        outcome_path.parent.mkdir(parents=True, exist_ok=True)
        outcome_path.write_bytes(canonical_json(outcome).encode("utf-8"))

    aggregate = aggregate_outcomes(
        candidate_id=spec["candidate_id"], graph_set=args.graph_set, outcomes=outcomes, graphs=graphs,
    )
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(canonical_json(aggregate).encode("utf-8"))
    (state_dir / "aggregate" / delta / "resources.json").write_bytes(
        canonical_json({
            "schema": "a0.maxcut.aggregate.resources/v1",
            "graph_set": args.graph_set,
            "runs": per_graph_resources,
        }).encode("utf-8")
    )
    if args.emit_resources:
        resources_path = Path(args.emit_resources).expanduser()
        resources_path.parent.mkdir(parents=True, exist_ok=True)
        resources_path.write_bytes(
            canonical_json({
                "schema": "a0.maxcut.aggregate.resources/v1",
                "graph_set": args.graph_set,
                "runs": per_graph_resources,
            }).encode("utf-8")
        )

    score = aggregate["score_exact"]
    print(f"E_STAR_AGGREGATE {json.dumps({
        'candidate_id': aggregate['candidate_id'],
        'graph_set': aggregate['graph_set'],
        'counts': aggregate['counts'],
        'score_exact': score,
        'edges_total_scored': aggregate['edges_total_scored'],
        'cut_edges_total': aggregate['cut_edges_total'],
    }, ensure_ascii=False, sort_keys=True)}")
    print(f"e_star: aggregate out={out_path} counts={aggregate['counts']}", file=sys.stderr)
    exit_code = EVALUATOR_EXIT_CODES[
        next(status for status in STATUS_SEVERITY if aggregate["counts"][status] > 0)
    ]
    return exit_code


def cmd_digest(args: argparse.Namespace) -> int:
    payload = {
        "schema": SCHEMA_OUTCOME,
        "e_star_version": E_STAR_VERSION,
        "source_files": source_file_digests(),
        "evaluator_source_sha256": evaluator_source_digest(),
        "defaults": {
            "seed": DEFAULT_SEED,
            "timeout_s": DEFAULT_TIMEOUT_S,
            "tau_band_s": {"min": child.TAU_MIN_S, "max": child.TAU_MAX_S},
            "cut_fraction_places": CUT_FRACTION_PLACES,
        },
        "objective": {"name": "cut_edges", "unit": "edges", "direction": "max", "weighted": False},
        "statuses": list(STATUSES),
        "evaluator_exit_codes": EVALUATOR_EXIT_CODES,
        "candidate_exit_labels": {
            "0": "ok", "20": "declared_invalid", "30": "internal_error", "40": "refused", "other": "other",
        },
        "failure_kinds_by_status": KINDS_BY_STATUS,
        "failure_stage_mapping": FAILURE_STAGE_MAPPING,
        "failure_stage_mapping_source": "a0/contract/selection/simpleloop.selection.json",
        "determinism_rule": "§6 rule 4: canonical bytes of partition.json over two invocations",
        "aggregate_arithmetic": "fractions.Fraction; cut_edges integers authoritative; cut_fraction display only",
        "candidate_input": {
            "view": "the candidate is handed `candidate_graph.json`, written into its private run "
                    "directory: §2's keys minus `generator` and `notes`",
            "view_keys": list(CANDIDATE_GRAPH_KEYS),
            "suite_identity": "graph_sha256 (sha256 of the frozen suite file; the bytes `cut_edges` is "
                              "recomputed from)",
            "handed_identity": "candidate_graph_sha256 (sha256 of the bytes actually handed over)",
            "fs_isolate_default": child.FS_ISOLATE_DEFAULT,
            "fs_isolate_mechanism": "unshare --user --map-root-user --mount --pid --fork --mount-proc "
                                    "with a tmpfs over every answer store, then setpriv to drop the "
                                    "whole capability set before exec; fail-closed",
            "fs_mask_policy": "the task directory (suite/references/generators and every e-star-state "
                              "under it), the repository's .git, the state roots, and the directory the "
                              "input graph was read from; the child's own run directory and interpreter "
                              "are bound back in",
        },
    }
    if getattr(args, "value_only", False):
        print(payload["evaluator_source_sha256"])
    else:
        print(canonical_json(payload), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="e_star.py",
        description="E*: the frozen harness-owned evaluator for the max-cut search task.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="evaluate one candidate on one graph")
    evaluate.add_argument("--candidate", required=True, help="candidate directory (or a bare program file)")
    evaluate.add_argument("--graph", required=True, help="path of the §2 graph.json")
    evaluate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    evaluate.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="tau in seconds (§7)")
    evaluate.add_argument("--out", required=True, help="path of the canonical Outcome JSON to write")
    evaluate.add_argument("--emit-resources", default=None, help="optional path for the timing sidecar")
    evaluate.add_argument(
        "--net-isolate", action="store_true",
        help="§4's 'inject no network' taken to its enforceable form: run the candidate inside a new "
             "route-less network namespace (`unshare -rn`). Fail-closed if `unshare` is unavailable. "
             "Additive flag; see DEVIATIONS.md D-T1-5.",
    )
    evaluate.add_argument(
        "--no-fs-isolate", dest="fs_isolate", action="store_false", default=child.FS_ISOLATE_DEFAULT,
        help="do NOT take the answer stores away from the candidate.  On by default: the candidate is "
             "started in a private user+mount+PID namespace with the repository, its `.git` and the "
             "state roots masked, and with every capability dropped.  Fail-closed if the topology "
             "cannot be built.  See DEVIATIONS.md D-T1-12.",
    )
    evaluate.add_argument(
        "--fs-mask", action="append", default=[], metavar="PATH",
        help="mask one more path from the candidate (repeatable); additive to the default policy",
    )
    evaluate.add_argument(
        "--state-dir", default=None,
        help="state root for run records (default: <tmp>/maxcut-e-star-state); never inside a candidate",
    )
    evaluate.set_defaults(func=cmd_evaluate)

    aggregate = sub.add_parser("aggregate", help="evaluate one candidate over a whole graph set")
    aggregate.add_argument("--candidate", required=True)
    aggregate.add_argument("--graph-set", required=True, choices=GRAPH_SETS)
    aggregate.add_argument("--out", required=True)
    aggregate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    aggregate.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    aggregate.add_argument("--emit-resources", default=None)
    aggregate.add_argument("--state-dir", default=None)
    aggregate.add_argument(
        "--suite-root", default=None,
        help=f"root holding <graph-set>/ (default: {DEFAULT_SUITE_ROOT}); additive flag, see DEVIATIONS.md",
    )
    aggregate.add_argument(
        "--net-isolate", action="store_true",
        help="as for `evaluate`: run every invocation in a route-less network namespace",
    )
    aggregate.add_argument(
        "--no-fs-isolate", dest="fs_isolate", action="store_false", default=child.FS_ISOLATE_DEFAULT,
        help="as for `evaluate`: do NOT mask the answer stores from the candidate",
    )
    aggregate.add_argument(
        "--fs-mask", action="append", default=[], metavar="PATH",
        help="mask one more path from the candidate (repeatable)",
    )
    aggregate.set_defaults(func=cmd_aggregate)

    digest = sub.add_parser("digest", help="print E*'s identity material (source digests, frozen tables)")
    digest.add_argument("--value-only", action="store_true", help="print only evaluator_source_sha256")
    digest.set_defaults(func=cmd_digest)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except GraphInvalid as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EVALUATOR_EXIT_CODES[STATUS_ERROR]


if __name__ == "__main__":
    raise SystemExit(main())
