"""E' -- MUTANT evaluator: the observational-equivalence fixture's E-prime.

This file is a copy of the frozen `E*` (`a0/tasks/circle-packing/e_star.py`,
sha256 `2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567`) with
three deliberate semantic deviations.  It exists to demonstrate the limit of the
*behavioural* half of A0.1: E' is a different evaluator that nonetheless agrees
with E* on every member of C* at the frozen theta_E (fidelity=full), so any
check that compares only `(status, objective, failure.kind)` over C* accepts it.
See `../README.md` and `../REPORT.md`.

The three deviations (each invisible at theta_E = full / fraction 1.0 / seed
1337):

  M1  `audit_sample` ignores the seed and audits the first `size` items in index
      order instead of E*'s seed-keyed decimation.  Inert at `fidelity=full`
      (the sample is every item); at `fidelity=fast` it disagrees with E* on
      C* itself -- measured in `../out/e_prime_vs_e_star.fast.json`.
  M2  the geometry tolerances are the strict ones: `in_bounds` drops the EPS
      slack and `overlap_check` calls a pair overlapping when `gap < 0.0`
      instead of `gap < -EPS`.  E* and E' therefore disagree about every
      geometry inside the 1e-9 band; no member of C* is inside it.
  M3  `min_boundary_margin` is computed over *every* circle instead of over the
      audited subset -- an audit-scope field, likewise inert at full fidelity.

Everything else -- the CLI, the exit codes, the child runner, the objective
formula, the outcome schema -- is E*'s, byte for byte.

--- original E* docstring follows ---

E* -- the frozen reference evaluator for the circle-packing plumbing task.

E* is `Candidate -> Outcome` for the study's A0.1 evaluator-integration
conformance check.  It is frozen *outside* the runtimes under test: no runtime's
own provenance schema, cache, or log directory is part of this file's contract.

Objective (upstream definition, unchanged):

    sum_radii = sum of the radii of the circles returned by pack_circles(n)

`sum_radii` is the primary metric named by the upstream task itself
(`circle-packing/loreley.program.md:8-10`; objective in
`circle-packing/README.md:19-27`) and computed by Loreley's evaluator plugin
(`circle_packing_env/evaluate.py:133-145`).  E* keeps the formula bit-for-bit:
the sum runs over every returned circle in the order the candidate returned
them.  E* does not collapse it to a scalar -- the Outcome carries the objective
plus validity and structural fields; turning that into a search signal is the
adapter's job (`F_r`).

Three hard constraints from the study protocol (§4.2.2) and how they are met:

1. No dependence on cwd or PATH.  Candidate code runs in a child process whose
   environment is fully specified by E* (`PATH` empty, no `PYTHONPATH`, private
   HOME/TMPDIR/cwd under E*'s state root) on a private copy of the candidate
   bytes.  E* itself never reads the environment into the Outcome.
2. No counting or logging into a directory that can be reverted.  Every byte E*
   writes goes below its own state root (`--state-dir`, default under the system
   temp directory) -- never into the caller's tree, never into a candidate
   worktree -- so `git checkout` / `git clean` in a candidate cannot revert E*'s
   records, and E* cannot pollute a candidate's tree.
3. Multi-field output.  The Outcome reports `status`, the objective, structural
   fields (overlap count, min gap, boundary margin, packing density) and the
   audit accounting instead of a single score.

Randomness: there is none beyond the explicit `--seed`, which draws the audit
subsample (decimation) for `--fidelity fast`.  `--fidelity full` audits every
item, so the seed is inert there by construction; for candidates whose only
defect sits in a decimated-away pair the seed flips the verdict, which is the
point: the seed is an evaluator input, not a label.

CLI:

    e_star.py evaluate --candidate <path> --seed <S> [--fidelity full|fast]
                       [--fraction F] --out <json> [--state-dir DIR]

Exit codes: 0 = ok, 2 = invalid (measured and rejected), 3 = error (no
measurement could be taken).  E* never emits 0.0 or any other number in place of
a failure, so an adapter cannot silently turn "could not evaluate" into a score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

E_STAR_VERSION = "1.0.0"
SCHEMA = "e_star.outcome/v1"

HERE = Path(__file__).resolve().parent
CHILD_PATH = HERE / "e_star_child.py"
SOURCE_FILES = ("e_star.py", "e_star_child.py")

# Upstream constants (circle_packing_env/evaluate.py).
EPS = 1e-9  # evaluate.py:23
DEFAULT_NUM_CIRCLES = 26  # evaluate.py:26
DEFAULT_RUNTIME_RUNS = 5  # evaluate.py:27
DEFAULT_RUNTIME_BUDGET_MS = 250.0  # evaluate.py:28
UNIT_SQUARE_MIN = 0.0
UNIT_SQUARE_MAX = 1.0

# Protocol constants (§4.2.2): KAPSO's registered fast-tier defaults.
DEFAULT_SEED = 1337  # kapso: evaluation_maintainer.subsample_seed
DEFAULT_FAST_FRACTION = 0.15  # kapso: FidelitySpec.eval_fast_fraction (fidelity.py:247)
DEFAULT_TIMEOUT_S = 120.0

STATUS_OK = "ok"
STATUS_INVALID = "invalid"
STATUS_ERROR = "error"
EXIT_CODES = {STATUS_OK: 0, STATUS_INVALID: 2, STATUS_ERROR: 3}

OBJECTIVE_NAME = "sum_radii"
OBJECTIVE_UNIT = "radius_sum"
OBJECTIVE_DIRECTION = "max"

# Check names follow upstream's `tests_executed` list (evaluate.py:322-329) so
# that an adapter can diff its own test report against E*'s; the audited scope of
# the decimated checks is recorded separately in `validity.audit`.
VALIDITY_CHECKS = (
    "count_equals_n",
    "radius_positive_check",
    "bounds_check",
    "overlap_check",
)


# --------------------------------------------------------------------------- #
# canonical serialisation
# --------------------------------------------------------------------------- #

def canonical_json(payload: object) -> str:
    """The single canonical byte form of any E* payload."""
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def evaluator_source_digest() -> str:
    """Content digest of E*'s own source files (order- and path-independent)."""
    entries = []
    for name in SOURCE_FILES:
        data = (HERE / name).read_bytes()
        entries.append({"name": name, "sha256": sha256_bytes(data), "bytes": len(data)})
    return sha256_text(canonical_json(entries))


def source_file_digests() -> list[dict[str, Any]]:
    out = []
    for name in SOURCE_FILES:
        data = (HERE / name).read_bytes()
        out.append({"name": name, "bytes": len(data), "sha256": sha256_bytes(data)})
    return out


# --------------------------------------------------------------------------- #
# theta_E and the audit subsample
# --------------------------------------------------------------------------- #

def audit_sample(n: int, size: int, seed: int) -> list[int]:
    """MUTANT M1 -- deterministic decimation that ignores `seed`.

    The first `size` items in index order are audited instead of E*'s
    seed-keyed decimation.  `size >= n` still returns every item, so the
    deviation is invisible at `fidelity=full`.
    """
    if size >= n:
        return list(range(n))
    if size <= 0:
        return []
    return list(range(min(size, n)))


def resolve_theta(args: argparse.Namespace) -> dict[str, Any]:
    fidelity = args.fidelity
    if args.fraction is None:
        fraction = 1.0 if fidelity == "full" else DEFAULT_FAST_FRACTION
    else:
        fraction = float(args.fraction)
    if not 0.0 < fraction <= 1.0:
        raise ValueError(f"--fraction must be in (0, 1], got {fraction!r}")
    if fidelity == "full" and fraction != 1.0:
        raise ValueError(
            "--fidelity full evaluates every item; pass --fraction 1.0 "
            f"(or use --fidelity fast) instead of {fraction!r}"
        )
    if int(args.n) <= 0:
        raise ValueError(f"--n must be positive, got {args.n!r}")
    if int(args.runs) <= 0:
        raise ValueError(f"--runs must be positive, got {args.runs!r}")
    return {
        "seed": int(args.seed),
        "fidelity": fidelity,
        "fraction": float(fraction),
        "n": int(args.n),
        "runs": int(args.runs),
        "runtime_budget_ms": float(args.runtime_budget_ms),
        "timeout_s": float(args.timeout_s),
    }


def audited_item_count(theta: Mapping[str, Any]) -> int:
    n = int(theta["n"])
    if theta["fidelity"] == "full":
        return n
    return max(1, min(n, int(round(float(theta["fraction"]) * n))))


def theta_digest(theta: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(dict(theta)))[:16]


# --------------------------------------------------------------------------- #
# candidate resolution and state root
# --------------------------------------------------------------------------- #

def resolve_candidate(path_str: str) -> tuple[Path, bytes]:
    """Return the candidate source file and its exact bytes.

    `path` may be a `solution.py`-style file or a directory containing one.
    """
    path = Path(path_str).expanduser()
    if path.is_dir():
        path = path / "solution.py"
    if not path.is_file():
        raise FileNotFoundError(
            f"candidate not found: {path} (expected a solution.py file or a "
            "directory containing one)"
        )
    return path, path.read_bytes()


def default_state_root() -> Path:
    return Path(tempfile.gettempdir()) / "e-star-state"


def state_dir_for(root: Path, candidate_sha256: str, theta: Mapping[str, Any]) -> Path:
    """State is keyed by candidate *content* and theta_E, never by path."""
    return root / f"{candidate_sha256[:16]}-{theta_digest(theta)}"


# --------------------------------------------------------------------------- #
# isolated execution
# --------------------------------------------------------------------------- #

def child_environment(state_dir: Path) -> dict[str, str]:
    """A fully specified environment: nothing of the caller's can leak in."""
    for sub in ("home", "tmp", "cwd"):
        (state_dir / sub).mkdir(parents=True, exist_ok=True)
    return {
        "PATH": "",
        "PYTHONPATH": "",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "C",
        "LANG": "C",
        "HOME": str(state_dir / "home"),
        "TMPDIR": str(state_dir / "tmp"),
    }


def run_child(
    *,
    solution_copy: Path,
    run_dir: Path,
    theta: Mapping[str, Any],
    state_dir: Path,
) -> dict[str, Any]:
    """Execute the candidate in a child process; return the raw artifacts.

    This process never imports candidate code.  The child writes one artifact
    file per call plus a done marker; a missing marker means the candidate
    terminated the runner, which is reported as an error rather than a score.
    The run directory is emptied first so that no leftover state from an earlier
    invocation can be mistaken for a measurement.
    """
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(CHILD_PATH),
        "--solution",
        str(solution_copy),
        "--n",
        str(int(theta["n"])),
        "--runs",
        str(int(theta["runs"])),
        "--run-dir",
        str(run_dir),
    ]
    info: dict[str, Any] = {
        "command": command,
        "returncode": None,
        "timed_out": False,
        "stdout": "",
        "stderr": "",
        "runs": [],
        "done": None,
    }
    try:
        completed = subprocess.run(
            command,
            cwd=str(state_dir / "cwd"),
            env=child_environment(state_dir),
            capture_output=True,
            timeout=float(theta["timeout_s"]),
            check=False,
        )
        info["returncode"] = completed.returncode
        info["stdout"] = completed.stdout.decode("utf-8", "replace")[-4000:]
        info["stderr"] = completed.stderr.decode("utf-8", "replace")[-4000:]
    except subprocess.TimeoutExpired as exc:
        info["timed_out"] = True
        info["stdout"] = (exc.stdout or b"").decode("utf-8", "replace")[-4000:]
        info["stderr"] = (exc.stderr or b"").decode("utf-8", "replace")[-4000:]

    done_path = run_dir / "child_done.json"
    if done_path.is_file():
        try:
            info["done"] = json.loads(done_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            info["done_error"] = f"unreadable done marker: {exc}"
    for index in range(int(theta["runs"])):
        run_path = run_dir / f"run_{index:02d}.json"
        if run_path.is_file():
            try:
                info["runs"].append(json.loads(run_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                info["runs"].append({"run": index, "error": f"unreadable artifact: {exc}"})
    return info


# --------------------------------------------------------------------------- #
# scoring (parent side, on artifacts only)
# --------------------------------------------------------------------------- #

def coerce_circles(entries: object) -> tuple[list[tuple[float, float, float]] | None, str | None]:
    """Mirror upstream `_coerce_circle` / `_coerce_circles` (evaluate.py:75-97)."""
    if not isinstance(entries, list):
        return None, "the return value is not an iterable of circle entries"
    circles: list[tuple[float, float, float]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, list) or len(entry) != 3:
            return None, f"circle #{index} is not an iterable of length 3: {entry!r}"
        try:
            x, y, r = float(entry[0]), float(entry[1]), float(entry[2])
        except (TypeError, ValueError):
            return None, f"circle #{index} contains non-numeric values: {entry!r}"
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(r)):
            return None, f"circle #{index} contains non-finite values: {entry!r}"
        circles.append((x, y, r))
    return circles, None


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(float(item) for item in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(0.0, min(1.0, float(percentile))) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(len(ordered) - 1, lower + 1)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def p50_ms(durations_s: Sequence[float]) -> float:
    if not durations_s:
        return 0.0
    return _percentile([float(item) * 1000.0 for item in durations_s], 0.5)


def in_bounds(circle: tuple[float, float, float]) -> bool:
    # MUTANT M2a: strict bounds, no EPS slack (E* allows a 1e-9 excursion).
    x, y, r = circle
    return (
        x - r >= UNIT_SQUARE_MIN
        and x + r <= UNIT_SQUARE_MAX
        and y - r >= UNIT_SQUARE_MIN
        and y + r <= UNIT_SQUARE_MAX
    )


def structure_fields(
    circles: Sequence[tuple[float, float, float]], sample: Sequence[int], n: int
) -> dict[str, Any]:
    """Structural fields computed over the audited subset of the item set.

    `sum_radii` and `packing_density` follow upstream `_compute_metrics`
    (evaluate.py:133-145) and always cover *every* returned circle;
    `overlap_count`, `min_gap` and `min_boundary_margin` are audit-scoped.
    """
    sampled = [circles[i] for i in sample if 0 <= i < len(circles)]

    # Bit-for-bit upstream `_compute_metrics` (evaluate.py:137-140): the same
    # `sum(...)` expressions, deliberately, because CPython >= 3.12 sums floats
    # with compensated summation while an explicit accumulator loop does not.
    # Mirroring the expression makes E* bit-identical to the plugin on whatever
    # interpreter the study pins, instead of merely close.
    total_area = sum(math.pi * (r**2) for _, _, r in circles)
    sum_radii = sum(r for _, _, r in circles)

    min_boundary_margin: float | None = None
    # MUTANT M3: the margin is taken over every returned circle, not over the
    # audited subset (E* scopes it to `sampled`).  Inert at full fidelity.
    for x, y, r in circles:
        value = min(x - r, y - r, UNIT_SQUARE_MAX - (x + r), UNIT_SQUARE_MAX - (y + r))
        min_boundary_margin = value if min_boundary_margin is None else min(min_boundary_margin, value)

    overlap_count = 0
    min_gap: float | None = None
    pairs_audited = 0
    for a in range(len(sampled)):
        x1, y1, r1 = sampled[a]
        for b in range(a + 1, len(sampled)):
            x2, y2, r2 = sampled[b]
            gap = math.hypot(x2 - x1, y2 - y1) - (r1 + r2)
            pairs_audited += 1
            min_gap = gap if min_gap is None else min(min_gap, gap)
            if gap < 0.0:  # MUTANT M2b: strict overlap test, E* uses gap < -EPS
                overlap_count += 1

    return {
        "num_circles": len(circles),
        "num_circles_expected": n,
        "sum_radii": sum_radii,
        "packing_density": total_area,  # container area is 1.0
        "overlap_count": overlap_count,
        "min_gap": min_gap,
        "min_boundary_margin": min_boundary_margin,
        "pairs_audited": pairs_audited,
    }


def build_outcome(
    *,
    theta: Mapping[str, Any],
    candidate_sha256: str,
    candidate_bytes: int,
    source_digest: str,
    child: Mapping[str, Any],
) -> dict[str, Any]:
    n = int(theta["n"])
    sample = audit_sample(n, audited_item_count(theta), int(theta["seed"]))
    total_pairs = n * (n - 1) // 2

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> bool:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        return bool(passed)

    status = STATUS_ERROR
    failure: dict[str, str] | None = None
    objective: dict[str, Any] | None = None
    structure: dict[str, Any] | None = None
    runs = list(child.get("runs", []))
    durations = [float(run.get("duration_s", 0.0)) for run in runs]

    done = child.get("done")
    artifacts_ok = check(
        "child_artifacts_complete",
        done is not None,
        {
            "runs_requested": int(theta["runs"]),
            "runs_written": None if done is None else done.get("runs_written"),
            "returncode": child.get("returncode"),
            "timed_out": bool(child.get("timed_out")),
        },
    )

    if not artifacts_ok:
        failure = {
            "kind": "timeout" if child.get("timed_out") else "child_terminated_early",
            "message": (
                f"candidate exceeded the {theta['timeout_s']} s wall-clock budget"
                if child.get("timed_out")
                else "the isolated runner did not write its done marker; no measurement exists"
            ),
        }
    elif done.get("import_error"):
        check("candidate_module_imports", False, done["import_error"])
        failure = {"kind": "candidate_import_failed", "message": str(done["import_error"])}
    elif done.get("entry_error"):
        check("candidate_module_imports", True, None)
        check("candidate_defines_entrypoint", False, done["entry_error"])
        failure = {"kind": "candidate_entrypoint_missing", "message": str(done["entry_error"])}
    else:
        check("candidate_module_imports", True, None)
        check("candidate_defines_entrypoint", True, done.get("entry_type"))
        runs_ok = check(
            "all_runs_recorded", len(runs) == int(theta["runs"]),
            {"recorded": len(runs), "expected": int(theta["runs"])},
        )
        if not runs_ok:
            failure = {"kind": "child_terminated_early", "message": "artifact set is incomplete"}
        else:
            call_errors = [run.get("error") for run in runs if run.get("error")]
            call_ok = check("candidate_call_succeeds", not call_errors, call_errors[0] if call_errors else None)
            if not call_ok:
                failure = {"kind": "candidate_call_raised", "message": str(call_errors[0])}
            else:
                per_run: list[list[tuple[float, float, float]] | None] = []
                parse_error: str | None = None
                for index, run in enumerate(runs):
                    circles_i, error_i = coerce_circles(run.get("value"))
                    per_run.append(circles_i)
                    if error_i is not None and parse_error is None:
                        parse_error = f"run {index}: {error_i}"
                circles = per_run[0]
                parse_ok = check("output_parses_as_triples", parse_error is None, parse_error)
                if not parse_ok or circles is None:
                    failure = {"kind": "malformed_output", "message": str(parse_error)}
                else:
                    structure = structure_fields(circles, sample, n)
                    sampled_radii = [circles[i][2] for i in sample if i < len(circles)]
                    count_ok = check(
                        "count_equals_n",
                        len(circles) == n,
                        {"num_circles": len(circles), "expected": n},
                    )
                    positive_ok = check(
                        "radius_positive_check",
                        all(r > 0.0 for r in sampled_radii),
                        {"items_audited": len(sampled_radii), "min_radius": min(sampled_radii) if sampled_radii else None},
                    )
                    bounds_ok = check(
                        "bounds_check",
                        all(in_bounds(circles[i]) for i in sample if i < len(circles)),
                        {"items_audited": len(sampled_radii), "min_boundary_margin": structure["min_boundary_margin"]},
                    )
                    overlap_ok = check(
                        "overlap_check",
                        structure["overlap_count"] == 0,
                        {
                            "pairs_audited": structure["pairs_audited"],
                            "overlap_count": structure["overlap_count"],
                            "min_gap": structure["min_gap"],
                        },
                    )
                    deterministic_ok = check(
                        "determinism_check",
                        _deterministic(per_run),
                        {"runs": len(per_run), "checked": len(per_run) > 1},
                    )
                    budget_enabled = float(theta["runtime_budget_ms"]) > 0.0
                    budget_ok = check(
                        "runtime_budget_check",
                        p50_ms(durations) <= float(theta["runtime_budget_ms"]) if budget_enabled else True,
                        {
                            "enabled": budget_enabled,
                            "budget_ms": float(theta["runtime_budget_ms"]),
                            "runs": len(runs),
                            # The measured p50 itself is wall-clock dependent and
                            # therefore lives in the state root (resources.json),
                            # never in the canonical Outcome.
                            "measurement": "resources.json",
                        },
                    )
                    mandatory_ok = count_ok and positive_ok and bounds_ok and overlap_ok
                    if not mandatory_ok:
                        status = STATUS_INVALID
                        failure = {"kind": "invalid_configuration", "message": _first_failure(checks)}
                    elif not deterministic_ok:
                        status = STATUS_ERROR
                        failure = {
                            "kind": "non_deterministic",
                            "message": "repeated calls returned different circle sets",
                        }
                    elif not budget_ok:
                        status = STATUS_ERROR
                        failure = {
                            "kind": "runtime_budget_exceeded",
                            "message": (
                                "measured p50 runtime exceeds the "
                                f"{float(theta['runtime_budget_ms']):.3f} ms budget "
                                "(measurement in resources.json)"
                            ),
                        }
                    else:
                        status = STATUS_OK
                        objective = {
                            "name": OBJECTIVE_NAME,
                            "value": structure["sum_radii"],
                            "unit": OBJECTIVE_UNIT,
                            "direction": OBJECTIVE_DIRECTION,
                        }

    # Flat, scalar-izable projection of the outcome for the adapter's
    # F_r(E*) = scalar(E*) declaration (a0/contract/fr/scalar.json reads
    # `outcome.fields.sum_radii`).  This is the score-facing surface, so every
    # metric here is null unless status == "ok" -- never 0.0, and never the sum
    # of a rejected configuration, so no adapter can read a score out of a
    # failure by accident.  Diagnostics for a rejected configuration are kept in
    # `structure`, which is not a score surface.
    fields_ok = structure is not None and status == STATUS_OK
    outcome: dict[str, Any] = {
        "schema": SCHEMA,
        "e_star_version": E_STAR_VERSION,
        "evaluator_source_sha256": source_digest,
        "interpreter": {
            "implementation": sys.implementation.name,
            "version": "{}.{}.{}".format(*sys.version_info[:3]),
        },
        "theta_e": {
            "seed": int(theta["seed"]),
            "fidelity": theta["fidelity"],
            "fraction": float(theta["fraction"]),
            "n": n,
            "runs": int(theta["runs"]),
            "runtime_budget_ms": float(theta["runtime_budget_ms"]),
            "timeout_s": float(theta["timeout_s"]),
        },
        "candidate": {
            "entry": "pack_circles",
            "source_sha256": candidate_sha256,
            "source_bytes": int(candidate_bytes),
        },
        "status": status,
        "scored": status == STATUS_OK,
        "failure": failure,
        "objective": objective,
        "structure": structure,
        "fields": {
            "sum_radii": structure["sum_radii"] if fields_ok else None,
            "packing_density": structure["packing_density"] if fields_ok else None,
            "num_circles": structure["num_circles"] if fields_ok else None,
            "overlap_count": structure["overlap_count"] if fields_ok else None,
            "min_gap": structure["min_gap"] if fields_ok else None,
            "min_boundary_margin": structure["min_boundary_margin"] if fields_ok else None,
            "items_audited": len(sample),
            "pairs_audited": len(sample) * (len(sample) - 1) // 2,
            "audit_coverage": (
                (len(sample) * (len(sample) - 1) // 2) / total_pairs if total_pairs else 1.0
            ),
        },
        "validity": {
            "ok": status == STATUS_OK,
            "checks": checks,
            "audit": {
                "items_total": n,
                "items_audited": len(sample),
                "pairs_total": total_pairs,
                "pairs_audited": len(sample) * (len(sample) - 1) // 2,
                "coverage": (len(sample) * (len(sample) - 1) // 2) / total_pairs if total_pairs else 1.0,
                "sample": sample,
                "sample_sha256": sha256_text(canonical_json(sample)),
                "seed": int(theta["seed"]),
                "fidelity": theta["fidelity"],
            },
        },
        # Timings are environment-dependent, so they are deliberately excluded
        # from the canonical Outcome: this key is always null here and the
        # measurements live in the state directory (resources.json) and in the
        # optional --emit-resources sidecar.
        "resources": None,
    }
    outcome["canonical_digest"] = canonical_digest(outcome)
    return outcome


def canonical_digest(outcome: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in outcome.items() if key != "canonical_digest"}
    return sha256_text(canonical_json(payload))


def _deterministic(per_run: Sequence[Sequence[tuple[float, float, float]] | None]) -> bool:
    baseline = per_run[0]
    return all(item == baseline for item in per_run)


def _first_failure(checks: Sequence[Mapping[str, Any]]) -> str:
    for entry in checks:
        if not entry["passed"] and entry["name"] in VALIDITY_CHECKS:
            return f"{entry['name']} failed: {entry['detail']}"
    return "configuration is not valid"


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_evaluate(args: argparse.Namespace) -> int:
    source_digest = evaluator_source_digest()
    theta = resolve_theta(args)

    try:
        _, candidate_raw = resolve_candidate(args.candidate)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EXIT_CODES[STATUS_ERROR]

    candidate_sha256 = sha256_bytes(candidate_raw)
    state_root = Path(args.state_dir) if args.state_dir else default_state_root()
    state_dir = state_dir_for(state_root, candidate_sha256, theta)
    state_dir.mkdir(parents=True, exist_ok=True)

    # Execute a private copy below the state root: the caller's tree is never
    # imported, so nothing the caller does to it (git checkout, git clean) can
    # change the measurement, and nothing E* does can appear in it.
    solution_dir = state_dir / "candidate"
    solution_dir.mkdir(parents=True, exist_ok=True)
    solution_copy = solution_dir / "solution.py"
    if not solution_copy.is_file() or solution_copy.read_bytes() != candidate_raw:
        solution_copy.write_bytes(candidate_raw)

    run_dir = state_dir / "invocations" / f"pid{os.getpid()}"
    child = run_child(solution_copy=solution_copy, run_dir=run_dir, theta=theta, state_dir=state_dir)
    (state_dir / "child_stdout.txt").write_text(child.get("stdout", ""), encoding="utf-8")
    (state_dir / "child_stderr.txt").write_text(child.get("stderr", ""), encoding="utf-8")

    outcome = build_outcome(
        theta=theta,
        candidate_sha256=candidate_sha256,
        candidate_bytes=len(candidate_raw),
        source_digest=source_digest,
        child=child,
    )

    canonical = canonical_json(outcome)
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(canonical.encode("utf-8"))

    resources = {
        "candidate_source_sha256": candidate_sha256,
        "theta_e": outcome["theta_e"],
        "runtime_ms_p50": p50_ms([float(run.get("duration_s", 0.0)) for run in child.get("runs", [])]),
        "runtime_ms_all": [float(run.get("duration_s", 0.0)) * 1000.0 for run in child.get("runs", [])],
        "runs_recorded": len(child.get("runs", [])),
        "child_returncode": child.get("returncode"),
        "timed_out": bool(child.get("timed_out")),
        "invocation_dir": str(run_dir),
    }
    resources_text = canonical_json(resources)
    (state_dir / "resources.json").write_bytes(resources_text.encode("utf-8"))
    if args.emit_resources:
        resources_path = Path(args.emit_resources).expanduser()
        resources_path.parent.mkdir(parents=True, exist_ok=True)
        resources_path.write_bytes(resources_text.encode("utf-8"))

    manifest = {
        "schema": "e_star.manifest/v1",
        "e_star_version": E_STAR_VERSION,
        "evaluator_source_sha256": source_digest,
        "candidate_source_sha256": candidate_sha256,
        "seed": outcome["theta_e"]["seed"],
        "fidelity": outcome["theta_e"]["fidelity"],
        "fraction": outcome["theta_e"]["fraction"],
        "items": outcome["validity"]["audit"]["items_audited"],
        "total_items": outcome["theta_e"]["n"],
        "status": outcome["status"],
        "objective": outcome["objective"],
        "canonical_digest": outcome["canonical_digest"],
    }
    print(f"E_STAR_MANIFEST {json.dumps(manifest, ensure_ascii=False, sort_keys=True)}")
    print(
        f"e_star: status={outcome['status']} state_dir={state_dir} out={out_path}",
        file=sys.stderr,
    )
    if outcome["failure"]:
        print(
            f"e_star: failure={outcome['failure']['kind']}: {outcome['failure']['message']}",
            file=sys.stderr,
        )
    return EXIT_CODES[outcome["status"]]


def cmd_digest(args: argparse.Namespace) -> int:
    payload = {
        "schema": SCHEMA,
        "e_star_version": E_STAR_VERSION,
        "source_files": source_file_digests(),
        "evaluator_source_sha256": evaluator_source_digest(),
        "defaults": {
            "seed": DEFAULT_SEED,
            "fidelity": "full",
            "fraction": 1.0,
            "fast_fraction": DEFAULT_FAST_FRACTION,
            "n": DEFAULT_NUM_CIRCLES,
            "runs": DEFAULT_RUNTIME_RUNS,
            "runtime_budget_ms": DEFAULT_RUNTIME_BUDGET_MS,
            "timeout_s": DEFAULT_TIMEOUT_S,
        },
        "objective": {
            "name": OBJECTIVE_NAME,
            "unit": OBJECTIVE_UNIT,
            "direction": OBJECTIVE_DIRECTION,
            "upstream": [
                "circle-packing/loreley.program.md:8-10",
                "circle-packing/README.md:19-27",
                "circle_packing_env/evaluate.py:133-145",
            ],
        },
        "validity_checks": list(VALIDITY_CHECKS),
    }
    print(canonical_json(payload), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="e_star.py",
        description="E*: frozen reference evaluator for the circle-packing plumbing task.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="evaluate one candidate")
    evaluate.add_argument("--candidate", required=True, help="solution.py or a directory containing it")
    evaluate.add_argument("--seed", type=int, default=DEFAULT_SEED, help="evaluator seed (theta_E)")
    evaluate.add_argument("--fidelity", choices=("full", "fast"), default="full")
    evaluate.add_argument("--fraction", type=float, default=None, help="fast-tier audit fraction in (0, 1]")
    evaluate.add_argument("--n", type=int, default=DEFAULT_NUM_CIRCLES, help="circles requested from the candidate")
    evaluate.add_argument("--runs", type=int, default=DEFAULT_RUNTIME_RUNS, help="repeated calls per evaluation")
    evaluate.add_argument(
        "--runtime-budget-ms",
        type=float,
        default=DEFAULT_RUNTIME_BUDGET_MS,
        help="p50 runtime budget in ms; <= 0 disables the check",
    )
    evaluate.add_argument(
        "--timeout-s", type=float, default=DEFAULT_TIMEOUT_S, help="wall-clock budget for the child process"
    )
    evaluate.add_argument("--out", required=True, help="path of the canonical Outcome JSON to write")
    evaluate.add_argument(
        "--emit-resources",
        default=None,
        help="optional path for the timing sidecar (timings never enter the canonical Outcome)",
    )
    evaluate.add_argument(
        "--state-dir",
        default=None,
        help="state root for run records (default: <tmp>/e-star-state); never written inside a candidate tree",
    )
    evaluate.set_defaults(func=cmd_evaluate)

    digest = sub.add_parser("digest", help="print E* identity material (source digests, defaults)")
    digest.set_defaults(func=cmd_digest)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"e_star: {exc}", file=sys.stderr)
        return EXIT_CODES[STATUS_ERROR]


if __name__ == "__main__":
    raise SystemExit(main())
