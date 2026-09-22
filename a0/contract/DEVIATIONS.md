# `a0/contract` deviations — the metric-range bound (finding D-A1-10)

The authority for this directory is `trace_schema.md` (semantics) plus `trace_schema.json` (shape).
Nothing below changes a clause either of them already stated: the work is additive, and each entry
names the reading it takes and why. Files affected: `trace_validate.py`,
`fixtures/traces/out_of_range.jsonl` (new), `tests/test_trace_schema.py`, `trace_schema.md`,
`README.md`. `selection/`, `fr/`, `evalcontract.py` and the `out/*.EID.json` records are untouched.

---

## D-C-1 — the bound is opt-in: the caller names the metric definition

**Clause.** D-A1-10's minimal diff: take the metric definition in force — "the file the run's
contract names" — and, when it declares `range`, refuse a `search_signal` outside it.

**What was done.** `--metric <path>` (repeatable) on `validate`, `validate-run` and `stats`, and a
`metric_definitions=` keyword on `validate_event`, `semantic_errors`, `validate_stream`,
`validate_composed`, `validate_events_only` and `validate_run_dir`. With no `--metric`, nothing is
bounded: that path is byte-for-byte the old behaviour.

**Why the caller has to supply it.** A trace event carries `task`, never a metric range, so a stream
alone cannot tell the validator that `coverage ∈ [0.0, 0.7853981633974483]`. The file that says so is
`components.MetricDefinition` in the run's contract — `fixtures/sample/contract.json` names
`metric.json`. The loader accepts either shape that file can arrive in: a `metric.json` (definition
under `metric`) or an `EID*` record (the same file nested under its own path) — any object carrying
`name` and `direction`.

**Bearing.** No existing caller changes verdict: `a0/runtimes/eve/a0_adapter/traces.py` shells out to
`validate-run` / `validate` / `stats` without `--metric`. The limit is named rather than hidden — a
caller that does not name the definition gets no bound, and `--metric`'s help text says so.

---

## D-C-2 — the Outcome's own field is bounded as well as `search_signal`

**Clause.** The recorded minimal diff names `search_signal` only.

**What was done.** Both numbers a score event publishes for the metric are checked:
`outcome.fields[<metric name>]` and the scalar `search_signal`. Each offence is a separate message
carrying the value, the declared range, the metric name and the file the definition came from.

**Why.** With only the signal checked, `{"coverage": 9999, "search_signal": 0.56}` would validate —
the same defect one field over. The harness-side closure of the same finding (`a0/a1/DEVIATIONS.md`
D-A1-10) checks `E*`'s own number too (`failure.kind: implausible_outcome`), so the trace level
matching it is the point; a single-value check would leave the pair disagreeing.

---

## D-C-3 — "in force" is a `task` match, and a metric with no range is not bounded

**What was done.** A definition that declares a `task` bounds only events carrying that `task`; one
that declares no `task` bounds every score event being validated; one that declares no `range` bounds
nothing. A non-numeric `search_signal` (a PyTree, or Loreley's archive descriptor) is not a scalar
score and is skipped.

**Why.** "Do not invent a bound where none is declared" is the assignment's own rule, and `task` is
the only tie between a definition and an event that the trace actually carries. The consequence is
named: a definition whose `task` does not match the run is silently not in force.

---

## D-C-4 — `trace_schema.json` was not edited

The schema promises nothing the check changes: `search_signal` is declared as `{}` (any JSON), and a
per-metric range cannot be expressed there anyway — the range lives in the run's contract, not in the
event. The rule is therefore documented where the semantics live (`trace_schema.md` §5 and §8,
`README.md` §5 and §6) and the schema file keeps its bytes; no file in the tree records its sha256
(searched for `9f889748181a83a33c2cfc232f1b8995f5b1b91efef4cd4822c910ef48c213c8`, no hits).
