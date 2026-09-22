# Trace specification (score / selection / resource)

Machine-readable schema: `trace_schema.json` (JSON Schema 2020-12). Validator:
`trace_validate.py`. Fixture: `fixtures/traces/good.jsonl`.

The protocol names the three traces it expects us to author (`plan:469`: "trace 规格（score
trace／selection trace／resource trace）") but does not define their fields. This document fixes
them. **Every field below is part of the frozen A0 contract** — an adapter that omits one is
non-conformant, and a reader that cannot join three runtimes' traces is a failure of the
contract, not of the reader.

---

## 1. File format and location

* **jsonl**, one JSON object per line, UTF-8, file ends with a newline. A blank line is
  ignored; a truncated final line is reported as an error.
* One file per (run, trace kind):

  ```
  <run_dir>/traces/<runtime>.<run_id>.score.jsonl
  <run_dir>/traces/<runtime>.<run_id>.selection.jsonl
  <run_dir>/traces/<runtime>.<run_id>.resource.jsonl
  ```

  `<runtime>` ∈ `{kapso, eve, loreley, simpleloop}` (must equal the `runtime` field on every
  line). The three files **partition** the run: a per-kind file carries only events of its own
  `trace` kind.
* **The run's merged stream is the validation unit** (`README.md` §8):

  ```
  <run_dir>/traces/<runtime>.<run_id>.all.jsonl
  ```

  every event of the run in `event_seq` order, with the same envelope. Adapters should write it;
  it is **required** whenever a selection event carries `source_score_event_id`, because that
  reference points across per-kind files and cannot be resolved inside one of them. Validation:

  ```
  trace_validate.py validate-run --run-dir <run_dir>
  trace_validate.py validate     --trace <run_dir>/traces/<runtime>.<run_id>.all.jsonl
  ```

  `validate-run` validates each run as one stream, using the merged file when present and
  otherwise composing the same stream from the three per-kind files in `event_seq` order, and
  additionally checks each per-kind file for event-level validity and kind purity.

  Both commands (and `stats`) also take `--metric <path>` — the metric definition file the run's
  contract lists under `MetricDefinition` — which bounds every published score by the metric's
  declared `range` (§5, §8).

* `<run_dir>` **must be outside any candidate worktree or any directory that a
  `git checkout` / archive extraction can restore** (protocol hard constraint 2, `plan:547`).
  KAPSO's `kapso_evaluation/` is exactly such a directory — do not put traces there.
* Events are appended as they happen. `event_seq` is a per-`run_id` monotonic counter; readers
  order by it and must not rely on `ts` (clock values are not comparable across hosts).

### 1.1 Why the unit is the run and not the file

§6 makes a selection event name the score event that drove it, and §2 makes `event_id` unique
*within the stream*. Both are properties of the run. When the traces were three independent
files, the reference could not be resolved (so every selection event in a per-kind file reported
`has no score event in this stream`) and two events of the run that shared an `event_id` in
different files went unnoticed. Merging fixes both, and it is also what makes the failure counters
of §7 correct across kinds. Per-kind files remain the reading interface — a reader that wants only
selection events reads only that file — but they are checked as components of the run, and their
union must equal the merged stream exactly once.

## 2. Join keys

Three readers must be able to answer, without ambiguity:

| Question | Key |
|---|---|
| Which run / candidate is this? | `run_id` + `runtime` + `iteration` + `candidate_id` (+ `parent_id`) |
| Under which evaluator identity? | `eid_star` (the only admissible cross-runtime identity) |
| What did this runtime call its evaluator, and how does that derive from `EID*`? | `eid_r.*` |
| With which evaluator parameters? | `theta_E` |
| What did `E*` return, before any scalarization? | `outcome.fields` |
| What did the runtime actually optimize? | `fr` + `search_signal` |
| What decision did the runtime actually make? | `selection` |
| What did it cost? | `T_wall`, `N_evaluatorCalls`, `concurrency`, `secondary` |
| Where in the trajectory did it fail? | `failure_stage` (+ `failure_detail`) |

`eid_star` must be a 64-hex sha256. The validator rejects a stream in which one `run_id` carries
two different `eid_star` values: `EID*` is frozen for the whole run.

## 3. Common envelope (all three traces)

| Field | Type | Required | Meaning |
|---|---|---|---|
| `trace` | `"score" \| "selection" \| "resource"` | yes | discriminator |
| `event_id` | string `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` | yes | unique within the stream |
| `event_seq` | int ≥ 0 | yes | monotonic within `run_id` |
| `ts` | string (RFC 3339) | no | wall clock, informational only |
| `run_id` | string | yes | one run of one runtime |
| `task` | string | yes | task identifier (`circle-packing` for the plumbing task) |
| `runtime` | `"kapso" \| "eve" \| "loreley" \| "simpleloop"` | yes | which runtime produced the event |
| `iteration` | int ≥ 0 | yes | search iteration |
| `candidate_id` | string | yes | the candidate this event is about |
| `parent_id` | string \| null | no | the parent candidate, if any |
| `eid_star` | 64-hex | yes | the frozen canonical evaluator identity in force |
| `eid_r` | object | yes | see §3.1 |
| `theta_E` | object | yes | see §3.2 |
| `failure_stage` | enum | yes | see §4 |
| `failure_detail` | string \| null | required iff `failure_stage != "none"` | human-readable cause |

Unknown top-level fields are **rejected** (`unevaluatedProperties: false`): the schema is closed
so that adapters cannot smuggle unvalidated state into the record. New fields go through a
schema version bump.

### 3.1 `eid_r` — the runtime's own identity and its mapping to `EID*`

```json
{"value": "manifest:3f786850...", "native_scheme": "manifest_fingerprint",
 "mapping_mode": "native", "derives_from_eid_star": "22c643f8...",
 "declaration": "the registered-evaluation manifest is generated from the adapter-pinned EID* inputs; ...",
 "recomputable": true}
```

| Field | Values | Meaning |
|---|---|---|
| `value` | non-empty string | the runtime's own identity representation, verbatim |
| `native_scheme` | `manifest_fingerprint` (KAPSO) \| `evaluator_name_version_campaign_program_hash` (Loreley) \| `none` (EvE, SimpleLoop) | what kind of thing `value` is |
| `mapping_mode` | `native` \| `adapter_declared_injection` | `native` = the runtime computes it itself; `adapter_declared_injection` = it has no concept and the adapter pins `EID*` |
| `derives_from_eid_star` | 64-hex | the validator requires this to equal `eid_star`; this is the machine-checkable form of "`EID_r` 由 `EID*` 派生" (`plan:517`) |
| `declaration` | non-empty string | prose statement of *how* the derivation works |
| `recomputable` | bool | whether a third party can recompute `value` from the contract's inputs |

Note that `EID_r` values are **not** compared across runtimes (`plan:513`: the test is *not*
`EID_K = EID_E = EID_L`).

### 3.2 `theta_E`

```json
{"seed": 1337, "fidelity": "fast", "fraction": 0.15, "defaults_applied": {}, "extra": {...}}
```

* `seed` (int \| null), `fidelity` (string \| null), `fraction` (number 0..1 \| null).
* `defaults_applied`: map from parameter name to `{"value": <the fixed equivalent actually
  used>, "source": <why>}`. **A parameter that is `null` must appear here.** This is the
  machine-checkable form of "缺失参数取等价的固定值" (`plan:518`) — e.g. EvE and Loreley receive
  no seed at all, so their events carry `seed: null` plus
  `defaults_applied.seed = {"value": "evaluator-internal-unseeded", "source": "EvE injects no seed..."}`,
  and KAPSO's `1337` is recorded as a real value because its registered contract makes the seed
  an evaluator input (`plan:530`).
* `extra`: free-form, for adapter-specific evaluator wiring (e.g. `EVE_EVAL_LOG_ROOT`,
  `fidelity_mode`). Absolute paths must not appear here if the trace is to be shareable; the
  validator does not enforce that, but `adapter_contract.md` §5 requires stripping them.

---

## 4. `failure_stage` enum and the required counters

Values, cut along the protocol's trajectory strata `Search -> Found -> Resolved -> Verified ->
Injected -> Used -> Improved` (`plan:628`) plus evaluator-side failures:

```
none  evaluator_failed  search_failed  resolve_failed  verify_failed
comprehension_failed  mechanism_mismatch  injection_failed  used_not_improved
timeout  boundary_violation  budget_exhausted
```

Mapping to the required counters (`plan:577`, `plan:651`):

| Counter | `failure_stage` value | Meaning |
|---|---|---|
| search failure rate | `search_failed` | nothing was found |
| `resolve_failed` | `resolve_failed` | found but not resolvable into a runnable artifact |
| `comprehension_failed` | `comprehension_failed` | the repository/artifact was not understood |
| `mechanism_mismatch` | `mechanism_mismatch` | the mechanism is not transferable |
| (evaluator) | `evaluator_failed` | A0.1 conformance failure: `E_r ≠ E* ± epsilon`, or a KAPSO manifest-triple mismatch |

`python trace_validate.py stats --trace <file>` prints these counts. **Counting is by
`(run_id, iteration, candidate_id)` unit, not by log line** — a failure is normally reported on
both the score event and the resource event of the same unit, and counting lines would double it.

---

## 5. Trace 1 — score

One evaluation of one candidate by `E*` as executed by runtime r, plus the search signal derived
from it.

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `{"fields": {name: value, ...}, "cardinality": int}` | the **raw** Outcome of `E*`. Multi-field by construction. |
| `fr` | object, see below | the `F_r` in force for this event |
| `search_signal` | any JSON | the runtime's internal signal after `F_r` (scalar, PyTree, or archive descriptor) |
| `evaluator_evidence` | object, see below | guards the two false-green traps |

**`outcome` must not contain a scalarized field.** Keys `scalar`, `scalarized`, `search_signal`,
`score_scalar` inside `outcome.fields` are rejected: scalarization is `F_r`'s job, not `E*`'s
(hard constraint 3, `plan:549`). If `cardinality` is present it must equal the number of fields.

**`fr`** (declared and frozen before running, `plan:528`):

```json
{"name": "F_r = scalar(E*)", "version": "v1", "applies": "scalar",
 "spec_hash": "0123...", "declared_in": "a0/contract/adapter_contract.md#default-first-round-rule"}
```

`applies` ∈ `{scalar, pytree, multiobjective}`. `spec_hash` is the sha256 of the frozen `F_r`
declaration, so two events claiming the same `fr.name` can be compared field-by-field.

**The score is bounded by the metric's declared range** (finding D-A1-10). `search_signal` is the
value the runtime optimizes, and when the metric in force declares a `range` that value must lie
inside it — the range was previously compared against nothing, so a stream whose every score was
`9999` validated cleanly although its metric declares `[0.0, 0.785...]`. `--metric <path>` names
the definition (the file the run's contract lists under `MetricDefinition`, e.g.
`fixtures/sample/metric.json`) and both published numbers are checked: the Outcome's own field
named by the metric and the scalar `search_signal`. Two deliberate limits: a metric that declares
no `range` is **not** bounded, and a definition that names a `task` other than the event's is not
in force for it — the validator never invents a bound. A non-scalar `search_signal` (a PyTree or an
archive descriptor, and not a score) is left alone.

**`evaluator_evidence`** — the two false-green traps (`plan:551-552`) become machine-detectable:

| `status` | When | Extra requirement |
|---|---|---|
| `ok` | a real measurement | — |
| `synthesized_failure` | the runtime mapped an evaluator exception to `failure_score(0.0)` (EvE) | `detail` required; the 0.0 in `outcome` is then known to be synthetic |
| `timeout` | the runtime synthesized a failure on evaluation timeout (Loreley) | `detail` required |
| `cache_hit` | a persistent cache supplied a previous result (Loreley) | `cached_from_run_id` required |
| `truncated_metrics` | metrics beyond the cap were dropped (Loreley, cap 64) | `metrics_dropped` records how many |
| `manifest_mismatch` | the KAPSO manifest triple did not match the granted class | `detail` required; the round is an A0.1 failure (`plan:538`) |
| `not_run` | evaluation was skipped | `detail` required |

A reader must never compare two `outcome` values without first checking `evaluator_evidence.status`.

---

## 6. Trace 2 — selection

The decision the runtime actually made, and the signals it was made from. This is where A0.2
lives: the protocol's checks are all assertions about behaviour observable in this trace.

```json
{"selection": {"policy": "argmax_{i<=t} E(c_i)", "chosen_candidate_id": "c1",
   "considered": [{"candidate_id": "c1", "search_signal": 0.56},
                  {"candidate_id": "c2", "search_signal": 0.41}],
   "reason": "c1 has the larger scalar search signal", "tie_break": null,
   "source_score_event_id": "sl-run001-s-i0-c2",
   "check_point": "SimpleLoop champion selection"}}
```

* `chosen_candidate_id` must appear in `considered`, or be `null` (no selection).
* `source_score_event_id` must name a score event present in **the run's stream** (§1). Score
  events live in the score file, so this reference is cross-file by construction and is resolved
  when the run is validated as one stream (`validate-run`, or `validate` on the merged
  `<runtime>.<run_id>.all.jsonl`). This is what makes "the decision was actually driven by the
  score" checkable rather than asserted: `chosen_candidate_id` may be compared against the
  `outcome.fields` of the named event, and the two must be consistent with the frozen selection
  rule (`contract/selection/<runtime>.selection.json`).
* `check_point` names which A0.2 executable check the decision corresponds to (`plan:559-567`),
  e.g. `"A0.2 EvE: RankSoftmaxSampler frequency test, k=2, T=1"`.
* A trace with no `selection` event for an iteration is evidence that no decision was recorded;
  it is not evidence that no decision was made.

---

## 7. Trace 3 — resource

Budget counters. Hard-enforceable quantities only (`plan:605-612`); tokens are *not* hard
constraints in round one because the three systems' self-reported numbers are not comparable.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `T_wall` | `{"value_sec": number ≥0, "clock": "monotonic"\|"wall", "scope": "iteration"\|"run"\|"delta"}` | yes | wall-clock |
| `N_evaluatorCalls` | int ≥ 0 | yes | evaluator invocations, counted by the adapter |
| `concurrency` | `{"cap": int ≥1, "observed_max": int ≥0}` | yes | `observed_max > cap` is rejected |
| `secondary` | `{"N_modelCalls", "T_in", "T_out", "C_usd"}` (each number \| null) | no | best-effort telemetry |
| `budget_hard` | `{"T_wall_sec", "N_evaluatorCalls", "concurrency_cap"}` \| null | no | the run's declared budget; exceeding it on a `scope: "run"` line is rejected |

`clock: "monotonic"` is preferred; a wall clock is acceptable only for cross-run reporting.
Adapter-side evaluation **must** be counted in `N_evaluatorCalls` even when the evaluator is
served from a cache, with `evaluator_evidence.status = "cache_hit"` on the corresponding score
event, so that cached and fresh work are separable (`plan:612` on Loreley's
`evaluation_attempts`).

---

## 8. Validation

```bash
./.venv/bin/python trace_validate.py validate --trace fixtures/traces/good.jsonl
./.venv/bin/python trace_validate.py stats    --trace fixtures/traces/good.jsonl
# with the metric definition in force, the published scores are bounded by its range
./.venv/bin/python trace_validate.py validate --trace fixtures/traces/good.jsonl \
    --metric fixtures/sample/metric.json
```

Exit codes: `0` clean, `1` invalid (each problem printed as `INVALID line N: …`), `2` the file
could not be read — or the metric definition named by `--metric` could not be (absent, not JSON, no
metric object, or a `range` that is not `[low, high]`).

Rejected beyond the JSON Schema: `eid_r.derives_from_eid_star ≠ eid_star`; a `null` `theta_E`
parameter with no declared default; a scalarized `outcome`; `synthesized_failure`/`timeout`
without `detail`; `cache_hit` without `cached_from_run_id`; a chosen candidate that was not
`considered`; `concurrency.observed_max > cap`; a stage outside the enum; a `failure_stage`
without `failure_detail`; duplicate `event_id`; a selection referencing a score event that is not
in the stream; one `run_id` carrying two different `eid_star` values; malformed JSON on a line; a
file whose last line has no trailing newline; and, when `--metric` names a definition that declares
a `range`, a published score for that metric outside it — `fixtures/traces/out_of_range.jsonl` is
the regression fixture (every score `9999`), rejected by 14 messages once the metric is named and
still valid without one.
