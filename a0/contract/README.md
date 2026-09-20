# `a0/contract` — A−1 frozen evaluation contract + trace specification

Everything a downstream workstream needs in order to run KAPSO / EvE / Loreley / SimpleLoop
against one shared, frozen evaluator identity.

| File | Purpose |
|---|---|
| `SPEC.md` | the frozen requirements extracted from protocol §4.0–§4.3, quoted verbatim with `file:line` pointers |
| `evalcontract.py` | the implementation of `EID* = H(EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition)` plus its CLI |
| `plumbing.contract.json` | the EID* spec for the plumbing task (circle-packing); `EvaluatorSource` is the frozen evaluator `e_star.py` + `e_star_child.py` |
| `fixtures/sample/contract.json` | a self-contained stand-in spec used by the tests |
| `fr/scalar.json` | the frozen first-round `F_r(E*) = scalar(E*)` declaration (`plan:528`) |
| `selection/simpleloop.selection.json` | the frozen `argmax` tie-break and `status != ok` fold, plus the A0-wide `E*` verdict → `failure_stage` table |
| `selection/kapso.selection.json` | KAPSO's adopted declaration, frozen here byte-for-byte; its runtime tie-break **diverges** from the A0-wide rule and the divergence is recorded in `adapter_contract.md` §5.3.1 |
| `selection/eve.selection.json` | EvE's adopted declaration, frozen byte-for-byte from `runtimes/eve/selection/eve.selection.json`; EvE's adapter refuses the run (exit 3) if either shared block drifts |
| `selection/loreley.selection.json` | Loreley's adopted declaration, frozen byte-for-byte from `runtimes/loreley/`**`policy/`**`loreley.selection.json` — note the directory, it is not a `selection/` path |
| `trace_schema.json` | machine-readable schema for the three traces (JSON Schema 2020-12) |
| `trace_schema.md` | the trace specification: fields, joins, failure stages, false-green handling |
| `trace_validate.py` | schema + semantic validator, run-level validator, and failure-stage counter |
| `adapter_contract.md` | the frozen interface each runtime adapter implements (CLI, exit codes, score source, `C*`, closure probe) |
| `fixtures/traces/good.jsonl` | a valid 11-event stream covering all three traces and all four runtimes |
| `tests/` | 84 tests: recomputability, single-input sensitivity, malformed-input rejection, the pinned plumbing `EID*`, run-level trace validation |
| `out/plumbing.EID.json`, `out/sample.EID.json` | generated EID* documents |

Nothing here imports KAPSO, EvE or Loreley; `evalcontract.py` uses the standard library only
(`tests/test_evalcontract.py::test_no_runtime_specific_imports` enforces both points).

---

## 1. Setup

```bash
cd /home/ebt/rsi-dev/a0/contract
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python pytest jsonschema
```

Observed:

```
Using CPython 3.12.11
Creating virtual environment at: .venv
 + jsonschema-specifications==2025.9.1
 + pluggy==1.6.0
 + pytest==9.1.1
 + referencing==0.37.0
 + rpds-py==2026.6.3
 + typing-extensions==4.16.0
```

`jsonschema` is needed only by `trace_validate.py`; `evalcontract.py` has no dependencies.

---

## 2. The frozen `EID*` for the plumbing task

```bash
./.venv/bin/python evalcontract.py compute --spec plumbing.contract.json --out out/plumbing.EID.json
```

Observed (2026-09-20, after the identity arbitration):

```
EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
  EvaluatorSource    a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  DependencyLock     7b02f1a71288335ff92fe68da8804349e416ba4ae9e95f8cd0c6a3b5bc372a75
  DataManifest       b21c975a51ef24cdfb2078957f0e0e4b2fb194e7c55b3a8058febb019d214a21
  Config             550ca3cdd8af04ec0895a2515bbee40a9627b805d5477611995f4cef0f4043ac
  MetricDefinition   420ab0acf24e1c7325b089e2ec4bc6c3d074119c4f3ac8aac8ed3cfa1c45bfc0
written: out/plumbing.EID.json
```

The spec is `plumbing.contract.json` with `base = ".."` (= `a0/`), so every declared path is
`a0`-relative. `base` and `spec` are recorded but **not hashed**, so relocating the spec without
changing the declared inputs leaves `EID*` unchanged; that is why the same five component digests
appear in `a0/tasks/circle-packing/plumbing.EID.proposed.json`, whose spec sits elsewhere with a
different `base` string.

What that hashes:

* `EvaluatorSource` — **the frozen evaluator itself**: `tasks/circle-packing/e_star.py` +
  `tasks/circle-packing/e_star_child.py` (root `tasks/circle-packing`, nothing else included).
* `DependencyLock` — `tasks/circle-packing/requirements.lock` raw hash plus an inline entry
  declaring CPython 3.12.11 and no third-party packages (E* and every member of C* import the
  standard library only).
* `DataManifest` — the two pinned upstream checkouts' identity (Loreley `4c375920…`, circle-packing
  `b91c0906…`), the task statement and objective files, the evaluator plugin the worker loads
  (`upstream/loreley/examples/circle_packing_env/evaluate.py`), the reference solution, the
  generated good packing, and **all 28 files of `C_STAR/`** including `manifest.json`. `C*` is
  *published*: it is hashed into `EID*`, so a change to any candidate changes the identity
  (`plan:509`). `E_STAR.json` (E* applied to C*) is deliberately **not** hashed — it is a derived
  artifact; hash it separately for provenance.
* `Config` — the `theta_E` semantics (`seed`/`fidelity`/`fraction` with their defaults and the
  statement that **the seed is a genuine evaluator input**), the canonical and fast thetas, the
  conformance `epsilon = 1e-9` (absolute, `sum_radii` units), the evaluator constants, the child
  environment policy (`PATH=""`, `PYTHONPATH=""`, `PYTHONNOUSERSITE=1`,
  `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`, private `HOME`/`TMPDIR`/cwd), the exit-code
  map, `cwd_independence.required = true`, `revert_safety.required = true` and
  `allow_network = false`.
* `MetricDefinition` — `name = sum_radii`, `direction = maximize`, the six-field Outcome
  (`sum_radii`, `packing_density`, `num_circles`, `overlap_count`, `min_gap`,
  `min_boundary_margin`), the failure semantics (**objective is `null`, never `0.0`, when
  `status != ok`**), the six validity gates, the `F_r`-owns-scalarization rule, and the recorded
  one-ULP discrepancy between upstream's `evaluate.py` and `scripts/local_eval.py`.

> **What changed and why.** The previous value was
> `EID* = fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d`, over upstream
> `scripts/local_eval.py`. That identified the **wrong artifact**: the frozen evaluator is
> `e_star.py`, and `local_eval.py` is not merely a different file but a different function — it
> accumulates `sum_radii` in a loop while the plugin the worker actually loads uses `sum()` (a
> one-ULP difference), and it can express neither `invalid`/`error` verdicts nor the audit fields
> nor the seed. Any trace keyed to `fac50fc4…` is keyed to a document that no longer exists.

### Recomputing it without the filesystem

```bash
./.venv/bin/python evalcontract.py recompute --eid-file out/plumbing.EID.json
```

```
  [ok ] EvaluatorSource    recorded=a3d6534b4e3bc78f recomputed=a3d6534b4e3bc78f
  [ok ] DependencyLock     recorded=7b02f1a71288335f recomputed=7b02f1a71288335f
  [ok ] DataManifest       recorded=b21c975a51ef24cd recomputed=b21c975a51ef24cd
  [ok ] Config             recorded=550ca3cdd8af04ec recomputed=550ca3cdd8af04ec
  [ok ] MetricDefinition   recorded=420ab0acf24e1c73 recomputed=420ab0acf24e1c73
  [ok ] EID*               recorded=664115e0d63ad2e1 recomputed=664115e0d63ad2e1
```

`recompute` reads only the `EID*.json` document — no files, no cwd dependence — which is the A−1
requirement that each of the five hashes be independently recomputable (`plan:509`).

### Detecting drift against the working tree

```bash
./.venv/bin/python evalcontract.py verify --eid-file out/plumbing.EID.json --spec plumbing.contract.json
```

```
clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
```

Demonstration of a failing verify (edit one byte in the stand-in `E*`, then re-verify):

```
-- edited evaluator/evaluator.py --
DRIFT EvaluatorSource: digest changed 790cee944d78 -> aa3c73e0788f
DRIFT EvaluatorSource: content changed evaluator/evaluator.py
DRIFT EID* changed 22c643f821b5bcb7 -> b26c5518d4995061
```

---

## 3. What is hashed, exactly

`H` is **not** specified by the protocol, so this contract fixes it:

* **Canonical form**: `sha256` over `json.dumps(value, sort_keys=True, separators=(",",":"),
  ensure_ascii=True, allow_nan=False)` encoded as ASCII, with keys recursively stringified.
  NaN/Infinity, non-JSON values and absolute paths are rejected rather than hashed.
* **Domain separation**: each component digest is
  `sha256("a0/evalcontract/v1/<Component>" + 0x00 + canonical_json(input))`; `EID*` itself is
  `sha256("a0/evalcontract/v1/EID*" + 0x00 + canonical_json({component: digest}))`. Two different
  kinds of object can therefore never collide.
* **Paths** are root-relative, POSIX, `..`-free. Symlinks pointing outside the root are rejected
  outright. The declared `root` is itself part of `EvaluatorSource`'s payload, so moving an
  evaluator tree to a different *relative* location is a different identity, while moving it to a
  different absolute directory is not.
* **Excluded**: absolute paths, mtimes, ownership, permissions, hostname, pid, traversal order,
  `.git/`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`.
* **Dependency locks** are normalized to `name==version` entries (`uv.lock`, `requirements*.txt`,
  `pyproject.toml`, `package-lock.json`; anything else falls back to a raw content hash). A lock
  that resolves to zero entries is an error — the contract refuses to hash "nothing".
* **`fr.spec_hash`** is the digest of a declaration's canonical form, not its bytes:
  `canonical_file_digest("fr/scalar.json") = 1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0`.

A test asserts the EID* document contains no absolute path
(`test_document_contains_no_absolute_paths`), and another asserts the fixture's `EID*` equals a
pinned constant so that any accidental change to what is hashed breaks the build instead of
silently redefining the identity (`test_fixture_eid_star_is_frozen`).

---

## 4. Tests — real output

```bash
./.venv/bin/python -m pytest tests/ -q
```

```
..............................................................           [100%]
83 passed, 1 skipped in 0.46s
```

The acceptance-critical tests, run verbosely:

```
tests/test_evalcontract.py::test_components_and_eid_are_recomputable_from_recorded_inputs PASSED
tests/test_evalcontract.py::test_recompute_needs_no_filesystem PASSED
tests/test_evalcontract.py::test_same_logical_input_same_digest_across_paths_and_times PASSED
tests/test_evalcontract.py::test_single_file_input_changes_only_its_component[EvaluatorSource] PASSED
tests/test_evalcontract.py::test_single_file_input_changes_only_its_component[DependencyLock] PASSED
tests/test_evalcontract.py::test_single_file_input_changes_only_its_component[DataManifest] PASSED
tests/test_evalcontract.py::test_single_file_input_changes_only_its_component[MetricDefinition] PASSED
tests/test_evalcontract.py::test_config_value_change_changes_only_config PASSED
tests/test_evalcontract.py::test_eid_star_covers_all_five_positions PASSED
```

Single-input sensitivity, measured directly (baseline `EID*` `22c643f821b5…`):

```
edit evaluator/evaluator.py   -> changed=['EvaluatorSource']  EID* 22c643f821b5 -> efb0be41c307
edit requirements.txt         -> changed=['DependencyLock']  EID* 22c643f821b5 -> bd0380f7f849
edit data/candidates.json     -> changed=['DataManifest']     EID* 22c643f821b5 -> a36f42fba847
edit metric.json              -> changed=['MetricDefinition'] EID* 22c643f821b5 -> 652eb3ddf04e
edit Config.value.seed=1338   -> changed=['Config']           EID* 22c643f821b5 -> 7020eadb66cf
```

Each edit changed exactly the expected component and the combined identity; the five `EID*`
values are pairwise distinct, so `EID*` covers all five positions
(`test_eid_star_covers_all_five_positions` also checks that permuting two component digests
changes `EID*`).

Also verified: absolute paths in `Config`/`MetricDefinition` are rejected; a symlink escaping the
declared root is rejected; a missing declared input is rejected; a spec omitting a component is
rejected; NaN/Infinity are rejected; `verify` exits 1 with `DRIFT` lines after a real edit;
a missing spec exits 2.

---

## 5. Traces

```bash
./.venv/bin/python trace_validate.py validate --trace fixtures/traces/good.jsonl
```

```
valid: 11 event(s)
```

```bash
./.venv/bin/python trace_validate.py stats --trace fixtures/traces/good.jsonl
```

```
events              11
schema/semantic errors 0
  search_failed          0
  resolve_failed         1
  comprehension_failed   1
  mechanism_mismatch     0
  other_failures         0
  events[eve] 2
  events[kapso] 3
  events[loreley] 2
  events[simpleloop] 4
```

The fixture exercises all three traces, all four runtimes, a `cache_hit`, a `synthesized_failure`
(EvE's silent `failure_score(0.0)` trap), a KAPSO manifest-era `resolve_failed`, and Loreley's
same-cell replacement. Counters are per `(run, iteration, candidate)` unit, not per line: the
`resolve_failed` failure is reported on both the score and the resource event of the same unit
and counts once.

Rejected cases, each with a dedicated test
(`tests/test_trace_schema.py::test_malformed_event_rejected[…]`): `missing_eid_star`,
`bad_eid_star_hex`, `eid_r_not_derived_from_eid_star`, `undeclared_theta_default`,
`outcome_scalarized_by_e_star`, `synthesized_failure_without_detail`, `cache_hit_without_source`,
`failure_without_detail`, `unknown_failure_stage`, `unknown_runtime`,
`selection_chooses_unconsidered_candidate`, `concurrency_over_cap`, `negative_evaluator_calls`,
`unknown_extra_field`, plus stream-level checks (malformed JSON line, truncated last line,
duplicate `event_id`, a selection referencing a missing score event, one run carrying two
different `EID*` values).

---

## 6. Invocation downstream adapters must use

Contract checks (from any directory):

```bash
python /home/ebt/rsi-dev/a0/contract/evalcontract.py compute --spec <spec.json> --out <EID.json>
python /home/ebt/rsi-dev/a0/contract/evalcontract.py verify   --eid-file <EID.json> --spec <spec.json>
python /home/ebt/rsi-dev/a0/contract/evalcontract.py recompute --eid-file <EID.json>
```

Trace validation (**the run is the unit**, see §8):

```bash
python /home/ebt/rsi-dev/a0/contract/trace_validate.py validate-run --run-dir <run_dir>
python /home/ebt/rsi-dev/a0/contract/trace_validate.py validate --trace <run_dir>/traces/<runtime>.<run_id>.all.jsonl
python /home/ebt/rsi-dev/a0/contract/trace_validate.py stats    --trace <merged stream>
```

Adapter run command and its exit-code table: `adapter_contract.md` §3.
Closure probe: `adapter_contract.md` §7.

---

## 7. Dependencies on the other workstreams

* **`a0/tasks/circle-packing/**`** — the frozen evaluator `E*`
  (`e_star.py` + `e_star_child.py`) and the published candidate set `C*`
  (`C_STAR/manifest.json`, 14 members). Both are hashed into `EID*`; `verify` reports drift if
  either moves, and that is the intended behaviour (`plan:509`). `EID*`'s C* content was
  independently reproduced by the producing workstream as
  `a0/tasks/circle-packing/plumbing.EID.proposed.json` — the same five component digests, computed
  from a spec at a different relative location.
* **`a0/acceptance/**`** — independent expected-value derivations for A0.2
  (`DERIVATIONS.md`, `expected_values.json`, `simulate.py`). `SPEC.md` §9 corrects three of its
  findings in the light of the runtime source; the corrections do not change any derived
  expectation, only the *reason* recorded for it.
* **`a0/runtimes/{simpleloop,kapso,eve,loreley}/**`** — the adapters and their traces. All four
  declarations are frozen under `contract/selection/` and all four reproduce block digests
  `d59f0930…` and `201fed78…`, so the two A0-wide tables are uniform.
  **Still outstanding**: EvE's and Loreley's *declared counts* over `C*` were reported as
  mismatching the frozen map before adoption (§5.3.2 records the numbers) — re-running the sweep
  with the adopted table closes that; and EvE owes an `eve_specific_stages` block declaring its
  extension case (§5.3.4 Rule 7), plus a `failure_stage_counts()` that excludes extension rows
  (0 rows today, so it changes no number yet). KAPSO's `tie_break_divergence` is recorded in §5.3.1
  and must not be assumed away; the condition under which a runtime-specific stage keeps counts
  joinable is §5.3.3, as amended.

---

## 8. The 2026-09-20 arbitration: what changed

Nine defects were found by execution and fixed. Anything a downstream workstream recorded against
the old text is invalid.

1. **`EID*` identified the wrong evaluator.** `plumbing.contract.json` pointed `EvaluatorSource`
   at upstream `scripts/local_eval.py` → `EID* = fac50fc4…`. Re-pointed at the frozen evaluator →
   `EID* = 664115e0…`, matching `a0/tasks/circle-packing/plumbing.EID.proposed.json`. The full
   reasoning is in `adapter_contract.md` §1. **Any trace keyed to `fac50fc4…` must be re-run.**
2. **`Config` said the seed was inapplicable.** It is a genuine evaluator input (`plan:530`,
   `plan:513-519`): at `fidelity=fast` it draws the audited subsample. Measured on
   `C_STAR/c01_good_hex`: `seed=1337 → sample [0, 3, 12, 22]`, `seed=1338 → sample [0, 14, 18,
   24]`, 4 of 26 items audited either way. `Config.value.theta_e_semantics.seed` now says so, and
   `theta_e_canonical` records `seed=1337, fidelity=full, fraction=1.0`.
3. **`selection.source_score_event_id` was unsatisfiable.** `trace_schema.md` §1 mandated three
   per-kind files, §6 required the selection event to name a score event, and
   `trace_validate.py:validate_stream` resolved the reference within one file — so *every*
   selection event in a per-kind file reported an error. Resolved by making the **run** the
   validation unit: `trace_validate.py validate-run --run-dir <dir>` validates each run as one
   stream, using the merged `<runtime>.<run_id>.all.jsonl` when the adapter wrote it and otherwise
   composing the same stream from the three per-kind files in `event_seq` order, plus a per-file
   event-level and kind-purity check.
4. **A0.1 could return a false PASS on a mis-staged failure.** `adapter_contract.md` §4.3 required
   non-`ok` candidates to be compared on "verdict **and** `failure.kind`", but the conformance
   runner compared only the coarse `status`, so an adapter reporting a truthful status with a wrong
   `failure.kind` on all nine non-`ok` members of `C*` passed with exit 0 (auditor's rejection
   **R1**, `a0/verify/VERDICT.md`). The requirement is now stated where it is checkable:
   **§4.5** makes `status` + `failure.kind` + the derived `failure_stage` all conformance, with
   the nine expected pairs tabulated, and **§6.3** states the trace-side form (a run whose non-`ok`
   stage disagrees with the frozen table is not a valid run). Exit code 5 now names all four ways
   an A0.1 row can fail. The checker fix is the conformance workstream's.
5. **KAPSO's runtime tie-break is not the A0-wide tie-break, and the divergence is demonstrated
   in both proposal orders.** Recorded in §5.3.1: `max()` over `node_history` returns the
   first-inserted maximum (a function of proposal order), while the frozen rule is the byte-wise
   smallest `candidate_id` (a function of the candidate set). With `c01_good_hex` proposed first
   the two agree; with `c03_mirror` proposed first KAPSO selects `c03_mirror` for parent,
   deliverable and next-round parent while the frozen rule still returns `c01_good_hex`
   (`runtimes/kapso/runs/tie-order-probe/outcome.json`, `diverges_from_frozen_tie_break: true`).
   **This corrects an earlier revision of this section**, which claimed `C*` could not
   discriminate the two rules: it can, and the shipped A0.2 scenario simply never exercises the
   discriminating order — so the A0.2 `tie_break` assertion, as run, does **not** establish the
   frozen tie-break for KAPSO and must not be cited as if it did.
6. **KAPSO's declaration was re-adopted (`143bfc94…` → `c1a99365…`).** The first freeze went stale
   within the hour: KAPSO corrected its `selection` block at 19:23 (its tie-order probe turned
   "would diverge" into "demonstrated in both orders", plus a `tie_break_divergence_evidence`
   block), so `a0/contract/selection/kapso.selection.json` at `143bfc94…` no longer described the
   thing it froze. Re-copied byte-for-byte, digest recomputed independently as
   `c1a993650b4edc4e7a0a799d12d2f6f74e7927b364021dd454454b6e22fc4d6c`; only the `selection` block
   moved (`differing_top_level_keys: ["selection"]`), and both shared blocks still reproduce
   `d59f0930…` / `201fed78…`. §5.3 now states plainly that a freeze here is a **snapshot, not a
   handshake**: the runtime-side file is frozen at the digest pinned in the contract, and any later
   change to it must come back as a re-adoption request.
7. **The failure-stage requirement is per row, and EvE/Loreley currently mismatch by count.**
   §5.3.2 answers the question the runner's counts raise: per-row conformance (§4.5) is the
   requirement, the aggregate over `C*` is *derived* (a mismatch is a guaranteed failure, a match
   proves nothing), and the frozen counts are
   `{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}` over 14 units.
   At the time of writing EvE declares `{none: 5, resolve_failed: 9}` and Loreley declares
   `{none: 6, resolve_failed: 5, verify_failed: 4}` (**15 units for 14 candidates** — a
   unit-definition defect that has to be resolved before its counts mean anything). §5.3.3 states
   the condition under which a runtime-specific stage such as KAPSO's `boundary_violation` keeps
   the cross-runtime counts joinable, and why such a row is not an `E*`-comparable measurement.
8. **EvE's and Loreley's declarations are frozen too.** Copied byte-for-byte, digests recomputed
   independently: EvE `1d4a30d5…` (from `runtimes/eve/selection/eve.selection.json`), Loreley
   `94d7139d…` (from `runtimes/loreley/`**`policy/`**`loreley.selection.json` — a `policy/`
   directory, so a reader globbing `**/selection/*.selection.json` finds only three of the four;
   §5.3 now tables the source paths). All four frozen copies reproduce both block digests, and
   EvE's own `check_adoption()` reports `agrees: True` after re-deriving them at run time.
9. **The staging question EvE raised is answered in §5.3.4.** A row can fail while `E*`'s verdict is
   `ok` (the runtime disagreed, or produced no measurement), and the frozen table — which maps
   `E*` verdicts — has no entry for it. The rule: `none` on a failed row is forbidden (it is the
   success counter); a disagreeing measurement is `mechanism_mismatch`, a missing measurement is
   `evaluator_failed`, a row with no `E*` verdict takes the runtime's declared stage
   (`timeout`, `boundary_violation`), and a never-attempted row is not emitted as a `C*` row at all.
   **Such a row cannot pass A0.1 for that candidate** — `E_r(c)` does not exist, and counting the
   row as a pass would compare `E*` against itself. `A0.1_r` is therefore reported
   `passed / measured / total` with the not-measured candidates named, never a bare boolean, and
   the shared `FailureStage` counter excludes extension rows so the counts stay joinable. The rule
   is A0-wide, and §5.3.3's third condition was amended because of it: a shared stage name may
   carry a second meaning (Loreley's `timeout`) only when those rows are basis-labelled and counted
   outside the shared counter — renaming is impossible, since the enum is closed.

Re-validation over every A0 trace directory under `a0/runtimes/*/**/traces/` (17 run
directories at the time of writing), per-file rule (`validate`) before, run rule
(`validate-run`) after:

| | before | after |
|---|---|---|
| events reporting `has no score event in this stream` | 33, across 8 SimpleLoop run directories | **0** |
| run directories whose traces validate clean | 9 of 17 | 16 of 17 |
| total reported errors | 33 | 28, all in one run |

The 33 errors were one per selection event in those 8 runs — i.e. **every** selection event in a
runtime that correctly records `source_score_event_id` was reported as an error, which is what
made the defect unsatisfiable rather than merely inconvenient.

The one remaining failure is a **newly visible, pre-existing EvE defect**, not a regression from
the change (before, EvE's three files each validated clean — the defect was invisible because
nothing was ever compared across them): `eve.eve-a0-run001.selection.jsonl` contains 14 events whose own `trace` field is
`"score"` — copies of score events that are also in the score file. Merged into one run stream
those 14 collide on `event_id` (`duplicate event_id … (first seen at position 16)`), and
`validate-run` additionally reports
`per-kind file for 'selection' carries a trace='score' event` for each. The three per-kind files
must partition the run. EvE's adapter (worker-owned, `a0/runtimes/eve/**`) needs either to stop
copying score events into the selection file or to namespace the `event_id`s; the contract cannot
fix it from here. All other runtimes — KAPSO (2 runs), Loreley (1), SimpleLoop (10) — validate
clean under the stricter rule.
* **`a0/env/upstream/loreley`** — treated as possibly incomplete and not depended upon anywhere.
