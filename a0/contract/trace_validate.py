#!/usr/bin/env python3
"""Validation for the three A0 traces (score / selection / resource).

Two layers: the JSON Schema in trace_schema.json checks shape, and the semantic
rules here check the invariants the schema cannot express (EID_r must derive
from the EID* in force, E* must not scalarize, a synthesized failure score must
not be able to masquerade as a real one, and so on).

The validation unit is a *run*, not a file: a selection event names the score
event that drove it, and those two live in different per-kind files
(trace_schema.md sections 1 and 6).  ``validate --trace`` therefore takes the
run's merged stream, and ``validate-run`` takes a run directory, using the
merged ``<runtime>.<run_id>.all.jsonl`` when the adapter wrote it and otherwise
composing the same stream from the three per-kind files in ``event_seq`` order.

``--metric`` names the metric definition file a run's contract lists under
``MetricDefinition``.  When that definition declares a ``range``, every score the
run publishes for the metric -- the Outcome's own field and the scalar
``search_signal`` -- must lie inside it (finding D-A1-10).  A metric that
declares no range is not bounded, because the validator must not invent one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover
    print("trace_validate requires jsonschema (uv pip install jsonschema)", file=sys.stderr)
    raise SystemExit(2)

SCHEMA_PATH = Path(__file__).resolve().parent / "trace_schema.json"

REQUIRED_THETA = ("seed", "fidelity", "fraction")

FAILURE_STAGES = (
    "none",
    "evaluator_failed",
    "search_failed",
    "resolve_failed",
    "verify_failed",
    "comprehension_failed",
    "mechanism_mismatch",
    "injection_failed",
    "used_not_improved",
    "timeout",
    "boundary_violation",
    "budget_exhausted",
)

# Stage counters the protocol singles out (lines 577 and 651).
COUNTED_FAILURES = ("search_failed", "resolve_failed", "comprehension_failed", "mechanism_mismatch")

_FORBIDDEN_OUTCOME_FIELDS = ("scalar", "scalarized", "search_signal", "score_scalar")


def _is_number(value) -> bool:
    """True for a JSON number. ``bool`` is an ``int`` in Python but not a score."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def find_metric_definition(doc):
    """Locate the object that describes a metric inside a definition file.

    ``metric.json`` nests it under ``metric``; an EID* record nests the same file
    under its own path.  Anything carrying both ``name`` and ``direction`` is a
    metric definition, so a recursive search reads either shape.
    """
    if isinstance(doc, dict):
        if "name" in doc and "direction" in doc:
            return doc
        for value in doc.values():
            found = find_metric_definition(value)
            if found is not None:
                return found
    elif isinstance(doc, list):
        for value in doc:
            found = find_metric_definition(value)
            if found is not None:
                return found
    return None


def load_metric_definitions(paths) -> list[dict]:
    """Load the metric definitions a run's contract names (``--metric``).

    Each entry is ``{"name", "task", "range", "source"}``.  ``range`` is ``None``
    when the definition declares none -- the validator never invents a bound, so
    such a metric is checked for nothing.
    """
    definitions: list[dict] = []
    for raw in paths or ():
        path = Path(raw)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"{path}: no such metric definition file") from None
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: not valid JSON ({exc.msg})") from None
        metric = find_metric_definition(doc)
        if metric is None:
            raise ValueError(f"{path}: no metric definition (an object with 'name' and "
                             f"'direction')")
        name = metric.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path}: metric definition has no usable 'name'")
        declared = metric.get("range")
        rng = None
        if declared is not None:
            if (not isinstance(declared, list) or len(declared) != 2
                    or not all(_is_number(v) for v in declared)):
                raise ValueError(f"{path}: metric {name!r} declares a range that is not "
                                 f"[low, high]: {declared!r}")
            if declared[0] > declared[1]:
                raise ValueError(f"{path}: metric {name!r} declares the range "
                                 f"[{declared[0]!r}, {declared[1]!r}] with low > high")
            rng = (declared[0], declared[1])
        task = doc.get("task") if isinstance(doc, dict) else None
        definitions.append({"name": name,
                            "task": task if isinstance(task, str) and task else None,
                            "range": rng,
                            "source": str(path)})
    return definitions


def _metric_is_in_force(definition: dict, event: dict) -> bool:
    """A definition with no task of its own is in force for every event."""
    task = definition["task"]
    return task is None or task == event.get("task")


def metric_range_errors(event: dict, definitions=None) -> list[str]:
    """Bound the score a score event publishes for a metric by the metric's range.

    Finding D-A1-10: the range a metric file declares was compared against
    nothing, so a trace whose every score was ``9999`` validated cleanly although
    the metric is declared over ``[0.0, 0.785...]``.  Two published values carry
    that metric: the Outcome's own field and the scalar ``search_signal`` the
    runtime acts on.  Both are checked here.

    Enforced only when the caller names the definition in force (the file the
    run's contract lists under ``MetricDefinition``), and only when that
    definition actually declares a ``range``: a metric that declares none is not
    given an invented bound.  A ``search_signal`` that is not a number (a PyTree
    or an archive descriptor) is not a scalar score and is left alone.
    """
    if event.get("trace") != "score" or not definitions:
        return []
    outcome = event.get("outcome")
    fields = outcome.get("fields") if isinstance(outcome, dict) else None
    errors: list[str] = []
    for definition in definitions:
        rng = definition["range"]
        if rng is None or not _metric_is_in_force(definition, event):
            continue
        low, high = rng
        name, source = definition["name"], definition["source"]
        bound = f"[{low!r}, {high!r}] declared by metric {name!r} ({source})"
        if isinstance(fields, dict):
            value = fields.get(name)
            if _is_number(value) and not (low <= value <= high):
                errors.append(f"outcome.fields.{name} {value!r} is outside the range {bound}")
        signal = event.get("search_signal")
        if _is_number(signal) and not (low <= signal <= high):
            errors.append(f"search_signal {signal!r} is outside the range {bound}")
    return errors


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_validator(schema: dict | None = None) -> Draft202012Validator:
    return Draft202012Validator(schema or load_schema(),
                                format_checker=Draft202012Validator.FORMAT_CHECKER)


def schema_errors(event: dict, validator: Draft202012Validator | None = None) -> list[str]:
    validator = validator or make_validator()
    return [f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
            for err in sorted(validator.iter_errors(event), key=lambda e: list(e.absolute_path))]


def semantic_errors(event: dict, metric_definitions=None) -> list[str]:
    errs: list[str] = []

    eid_star = event.get("eid_star")
    eid_r = event.get("eid_r")
    if isinstance(eid_r, dict) and eid_r.get("derives_from_eid_star") != eid_star:
        errs.append(f"eid_r.derives_from_eid_star {eid_r.get('derives_from_eid_star')!r} "
                    f"does not match eid_star {eid_star!r}")

    theta = event.get("theta_E")
    if isinstance(theta, dict):
        defaults = theta.get("defaults_applied") or {}
        for param in REQUIRED_THETA:
            if theta.get(param) is None and param not in defaults:
                errs.append(f"theta_E.{param} is null but defaults_applied does not declare "
                            f"the fixed value used instead")

    stage = event.get("failure_stage")
    if stage is not None and stage not in FAILURE_STAGES:
        errs.append(f"failure_stage {stage!r} is not in the frozen enum")
    if stage not in (None, "none") and not event.get("failure_detail"):
        errs.append(f"failure_stage={stage} requires failure_detail")

    if event.get("trace") == "score":
        outcome = event.get("outcome")
        if isinstance(outcome, dict):
            fields = outcome.get("fields") or {}
            for banned in _FORBIDDEN_OUTCOME_FIELDS:
                if banned in fields:
                    errs.append(f"outcome.fields.{banned} present: E* returns the raw Outcome; "
                                f"scalarization is F_r's job")
            if "cardinality" in outcome and outcome["cardinality"] != len(fields):
                errs.append("outcome.cardinality does not match the number of outcome fields")
        evd = event.get("evaluator_evidence")
        if isinstance(evd, dict):
            status = evd.get("status")
            if status in ("synthesized_failure", "timeout", "truncated_metrics",
                          "manifest_mismatch", "not_run") and not evd.get("detail"):
                errs.append(f"evaluator_evidence.status={status} requires detail so that a "
                            f"synthesized score cannot be mistaken for a real one")
            if status == "cache_hit" and not evd.get("cached_from_run_id"):
                errs.append("evaluator_evidence.status=cache_hit requires cached_from_run_id")

    if event.get("trace") == "selection":
        sel = event.get("selection")
        if isinstance(sel, dict):
            chosen = sel.get("chosen_candidate_id")
            considered = [c.get("candidate_id") for c in sel.get("considered", [])
                          if isinstance(c, dict)]
            if chosen is not None and chosen not in considered:
                errs.append(f"selection.chosen_candidate_id {chosen!r} is not among considered "
                            f"{considered}")

    if event.get("trace") == "resource":
        conc = event.get("concurrency")
        if isinstance(conc, dict):
            cap, seen = conc.get("cap"), conc.get("observed_max")
            if isinstance(cap, int) and isinstance(seen, int) and seen > cap:
                errs.append(f"concurrency.observed_max {seen} exceeds cap {cap}")
        budget = event.get("budget_hard")
        t_wall = event.get("T_wall")
        if isinstance(budget, dict) and isinstance(t_wall, dict):
            cap = budget.get("T_wall_sec")
            if isinstance(cap, (int, float)) and isinstance(t_wall.get("value_sec"), (int, float)):
                if t_wall["scope"] == "run" and t_wall["value_sec"] > cap:
                    errs.append(f"T_wall {t_wall['value_sec']} exceeds the hard budget {cap}")
            calls_cap = budget.get("N_evaluatorCalls")
            calls = event.get("N_evaluatorCalls")
            if isinstance(calls_cap, int) and isinstance(calls, int) and calls > calls_cap:
                errs.append(f"N_evaluatorCalls {calls} exceeds the hard budget {calls_cap}")

    errs += metric_range_errors(event, metric_definitions)

    return errs


def validate_event(event: dict, validator: Draft202012Validator | None = None,
                   metric_definitions=None) -> list[str]:
    return (schema_errors(event, validator)
            + semantic_errors(event, metric_definitions))


def load_jsonl(path: Path) -> tuple[list[tuple[int, dict]], list[str]]:
    events: list[tuple[int, dict]] = []
    errors: list[str] = []
    text = Path(path).read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        errors.append("file does not end with a newline; the last line may be truncated")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {lineno}: each jsonl line must be a JSON object")
            continue
        events.append((lineno, event))
    return events, errors


def _event_label(event: dict) -> str:
    """Name an event for a message that survives a merge across files."""
    eid = event.get("event_id")
    seq = event.get("event_seq")
    if isinstance(eid, str):
        return f"event {eid!r} (event_seq {seq})"
    return f"event at event_seq {seq}"


def stream_errors(events: list[dict]) -> list[str]:
    """Checks that only make sense over a whole run stream, not one event."""
    errors: list[str] = []
    seen_ids: dict[str, int] = {}
    score_ids: set[str] = set()
    run_eids: dict[str, set[str]] = {}
    for index, event in enumerate(events):
        eid = event.get("event_id")
        if isinstance(eid, str):
            if eid in seen_ids:
                errors.append(f"{_event_label(event)}: duplicate event_id {eid!r} "
                              f"(first seen at position {seen_ids[eid]})")
            seen_ids.setdefault(eid, index)
        if event.get("trace") == "score" and isinstance(eid, str):
            score_ids.add(eid)
        run = event.get("run_id")
        eid_star = event.get("eid_star")
        if isinstance(run, str) and isinstance(eid_star, str):
            run_eids.setdefault(run, set()).add(eid_star)

    for event in events:
        sel = event.get("selection") if event.get("trace") == "selection" else None
        if isinstance(sel, dict):
            ref = sel.get("source_score_event_id")
            if isinstance(ref, str) and ref not in score_ids:
                errors.append(f"{_event_label(event)}: selection.source_score_event_id {ref!r} "
                              f"has no score event in this stream "
                              f"(validate the run, not one per-kind file: "
                              f"validate-run --run-dir <run_dir>)")
    for run, eids in sorted(run_eids.items()):
        if len(eids) > 1:
            errors.append(f"run {run!r} mixes {len(eids)} distinct EID* values: "
                          f"{sorted(eids)} -- EID* must be frozen for the whole run")
    return errors


def validate_stream(path: Path, metric_definitions=None) -> tuple[list[str], list[dict]]:
    events, errors = load_jsonl(path)
    validator = make_validator()
    for lineno, event in events:
        for err in validate_event(event, validator, metric_definitions):
            errors.append(f"line {lineno}: {err}")
    errors += stream_errors([e for _, e in events])
    return errors, [e for _, e in events]


def validate_composed(paths: list[Path], metric_definitions=None) -> tuple[list[str], list[dict]]:
    """Validate a run assembled from its per-kind files, in ``event_seq`` order.

    Produces the same verdict as validating the merged stream, so a runtime that
    keeps only the three per-kind files is still checkable.
    """
    rows: list[tuple[int, int, int, dict]] = []
    errors: list[str] = []
    for index, path in enumerate(paths):
        loaded, load_errors = load_jsonl(path)
        errors += [f"{path.name}: {err}" for err in load_errors]
        for lineno, event in loaded:
            seq = event.get("event_seq")
            rows.append((seq if isinstance(seq, int) else -1, index, lineno, event))
    rows.sort(key=lambda row: row[:3])

    validator = make_validator()
    for _seq, index, lineno, event in rows:
        for err in validate_event(event, validator, metric_definitions):
            errors.append(f"{paths[index].name}:{lineno}: {err}")
    events = [row[3] for row in rows]
    errors += stream_errors(events)
    return errors, events


def validate_events_only(path: Path, expected_kind: str | None = None,
                         metric_definitions=None) -> tuple[list[str], int]:
    """Event-level checks for one per-kind file, without cross-file resolution.

    ``expected_kind`` enforces that a per-kind file holds only its own kind of
    event: a score line copied into the selection file is a duplicate of the
    score stream, and merging would report it as a colliding ``event_id``.
    """
    loaded, errors = load_jsonl(path)
    validator = make_validator()
    for lineno, event in loaded:
        for err in validate_event(event, validator, metric_definitions):
            errors.append(f"line {lineno}: {err}")
        if expected_kind is not None and event.get("trace") != expected_kind:
            errors.append(f"line {lineno}: per-kind file for {expected_kind!r} carries a "
                          f"trace={event.get('trace')!r} event ({_event_label(event)}); "
                          f"the per-kind files must partition the run")
    return errors, len(loaded)


KINDS = ("score", "selection", "resource")
MERGED_KIND = "all"


def run_components(traces_dir: Path) -> dict[tuple[str, str], dict[str, Path]]:
    """Group ``<runtime>.<run_id>.<kind>.jsonl`` files by ``(runtime, run_id)``."""
    groups: dict[tuple[str, str], dict[str, Path]] = {}
    for path in sorted(traces_dir.glob("*.jsonl")):
        stem = path.name[: -len(".jsonl")]
        rest, _, kind = stem.rpartition(".")
        runtime, _, run_id = rest.partition(".")
        if not runtime or not run_id or kind not in KINDS + (MERGED_KIND,):
            continue
        groups.setdefault((runtime, run_id), {})[kind] = path
    return groups


def validate_run_dir(run_dir: Path, metric_definitions=None) -> int:
    traces_dir = run_dir / "traces" if (run_dir / "traces").is_dir() else run_dir
    groups = run_components(traces_dir)
    if not groups:
        print(f"no <runtime>.<run_id>.<kind>.jsonl traces under {traces_dir}", file=sys.stderr)
        return 2
    total_errors = 0
    total_events = 0
    for (runtime, run_id), files in sorted(groups.items()):
        merged = files.get(MERGED_KIND)
        if merged is not None:
            source, errors, events = (f"merged {merged.name}",
                                      *validate_stream(merged, metric_definitions))
        else:
            parts = [files[kind] for kind in KINDS if kind in files]
            source = "composed from " + "+".join(p.name for p in parts)
            errors, events = validate_composed(parts, metric_definitions)
        per_file: list[str] = []
        for kind in KINDS:
            if kind not in files:
                continue
            file_errors, count = validate_events_only(files[kind], expected_kind=kind,
                                                      metric_definitions=metric_definitions)
            errors += [f"{files[kind].name}: {err}" for err in file_errors]
            per_file.append(f"{kind}={count}" + ("" if not file_errors else "/ERR"))
        total_errors += len(errors)
        total_events += len(events)
        status = "ok " if not errors else "BAD"
        print(f"[{status}] {runtime}.{run_id}  events={len(events)}  "
              f"[{' '.join(per_file)}]  {source}")
        for err in errors:
            print(f"        INVALID {err}")
    verdict = "valid" if total_errors == 0 else f"{total_errors} error(s)"
    print(f"{verdict}: {len(groups)} run(s), {total_events} event(s)")
    return 0 if total_errors == 0 else 1


def count_failure_stages(events) -> dict[str, int]:
    """Count distinct (run, iteration, candidate) units per stage, not log lines.

    A failure is typically reported on both the score event and the resource
    event of the same unit; counting lines would double it.
    """
    counts = {stage: 0 for stage in FAILURE_STAGES}
    seen: set[tuple] = set()
    for event in events:
        stage = event.get("failure_stage", "none")
        unit = (event.get("run_id"), event.get("iteration"), event.get("candidate_id"), stage)
        if unit in seen:
            continue
        seen.add(unit)
        counts[stage] = counts.get(stage, 0) + 1
    return counts


def _cmd_validate(args) -> int:
    errors, events = validate_stream(Path(args.trace), args.metric_definitions)
    if errors:
        for err in errors:
            print(f"INVALID {err}")
        print(f"{len(errors)} error(s) in {len(events)} event(s)")
        return 1
    print(f"valid: {len(events)} event(s)")
    return 0


def _cmd_stats(args) -> int:
    errors, events = validate_stream(Path(args.trace), args.metric_definitions)
    counts = count_failure_stages(events)
    print(f"events              {len(events)}")
    print(f"schema/semantic errors {len(errors)}")
    for stage in COUNTED_FAILURES:
        print(f"  {stage:<22} {counts[stage]}")
    other = sum(v for k, v in counts.items() if k not in COUNTED_FAILURES and k != "none")
    print(f"  {'other_failures':<22} {other}")
    by_runtime: dict[str, int] = {}
    for event in events:
        by_runtime[event.get("runtime", "?")] = by_runtime.get(event.get("runtime", "?"), 0) + 1
    for runtime, n in sorted(by_runtime.items()):
        print(f"  events[{runtime}] {n}")
    return 1 if errors else 0


def _cmd_validate_run(args) -> int:
    return validate_run_dir(Path(args.run_dir), args.metric_definitions)


METRIC_HELP = ("a metric definition file the run's contract names (repeatable). When it "
               "declares a 'range', every score the run publishes for that metric must lie "
               "inside it; a metric that declares none is not bounded")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trace_validate", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate", help="schema + semantic checks over one jsonl trace; "
                                        "for a run's traces point this at the merged .all.jsonl")
    p.add_argument("--trace", required=True)
    p.add_argument("--metric", action="append", metavar="PATH", help=METRIC_HELP)
    p.set_defaults(fn=_cmd_validate)
    p = sub.add_parser("validate-run", help="validate every run under a run directory "
                                            "(or its traces/ directory) as one stream each")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--metric", action="append", metavar="PATH", help=METRIC_HELP)
    p.set_defaults(fn=_cmd_validate_run)
    p = sub.add_parser("stats", help="failure-stage counters and per-runtime event counts")
    p.add_argument("--trace", required=True)
    p.add_argument("--metric", action="append", metavar="PATH", help=METRIC_HELP)
    p.set_defaults(fn=_cmd_stats)
    args = parser.parse_args(argv)
    try:
        args.metric_definitions = load_metric_definitions(args.metric)
    except ValueError as exc:
        print(f"cannot read metric definition: {exc}", file=sys.stderr)
        return 2
    try:
        return args.fn(args)
    except FileNotFoundError as exc:
        print(f"cannot read trace: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
