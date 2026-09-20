# Handoff to the `a0/contract` owner (worker #5)

Three things the SimpleLoop workstream had to decide in order to execute A0.2, plus one
contract-level defect found by executing the validator. Nothing here is a request to weaken the
contract; the first two close gaps `a0/acceptance/DERIVATIONS.md` §4 already flagged as
"must be closed in `a0/contract` before A0.2 means anything".

Everything below is **implemented and executed** in this directory; the authoritative file is
`policy/simpleloop.policy.json`, and every claim has a real command behind it in `A0_REPORT.md`.
`policy/proposed.a0.contract.simpleloop.selection.json` is a ready-to-copy
`a0/contract/selection/simpleloop.selection.json` whose `scalarization` and `selection` blocks are
copied verbatim from that authoritative file, so the proposal cannot drift from what was executed.

**Status after the follow-up round.** The two blocks to be copied are **unchanged** and still match
both the implementation and the executed runs — verified mechanically rather than by reading:
`tests/test_policy.py::test_declared_rule_and_implementation_are_the_same_rule` asserts that the
proposal's `scalarization` and `selection` blocks are identical to the authoritative policy, that
the declared "byte-wise UTF-8" tie-break coincides with the implementation's comparison order
(checked over a non-ASCII stress set), that a 3-way tie resolves to the same id under **every**
permutation, and that `choose()` has no epsilon parameter that could absorb a score gap. Canonical
digests for pinning:

| what | canonical digest |
|---|---|
| `policy/simpleloop.policy.json` | `0ceb5f6c1d8afe8730e945fa1469484afc74f304be4bef708a6794a9d10dfebf` |
| `policy/proposed.a0.contract.simpleloop.selection.json` | `333a62a16ee9405bef3f5a0f742356c325e020db88cbc35fc77650283c7d3271` |
| the `scalarization` block | `d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c` |
| the `selection` block | `d47f9cea54d5984ef1370a527f6542fbe4a2a46a354b93859346352c13d473f2` |

One thing outside those blocks did change and is worth knowing if any document quotes it:
SimpleLoop's `EID_r` construction is now domain-separated, bare 64-hex and independently
recomputable (`EID_r = 5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e`, see
`A0_REPORT.md` §0). Nothing in `a0/contract/` depends on that value.

---

## 1. Gap A — the fold from E*'s multi-field Outcome to the scalar is undefined

`a0/contract/fr/scalar.json` says `F_r(E*) = scalar(E*)`, `input =
outcome.fields.sum_radii`, `direction = maximize`. It does not say what happens when
`outcome.status != "ok"`, and E* returns `sum_radii: null` with `scored: false` for 9 of the 14
members of `C*` (4 `invalid`, 5 `error`).

**Proposed frozen text (add to `fr/scalar.json`, or land as
`a0/contract/selection/<runtime>.selection.json`):**

```json
"scalarization": {
  "applies": "scalar",
  "input": "outcome.fields.sum_radii",
  "direction": "maximize",
  "status_gate": "scalar is defined iff outcome.status == \"ok\"; when status is invalid or error the scalar is null",
  "null_is_not_zero": "a null scalar is never coerced to 0.0 or to -inf; an unscored candidate is recorded as unscored and is excluded from the argmax; E* exit 2 / exit 3 propagate as failure_stage values with failure_detail, not as a number",
  "nonfinite": "a non-finite scalar is rejected as a measurement error, not compared",
  "identity_check": "when status == ok the adapter asserts objective.value == fields.sum_radii"
}
```

Why it matters: `-inf` and `0.0` are both *comparisons*. `0.0` is the false green the protocol
already names for EvE (`failure_score(0.0)` — `plan:551`), and `-inf` would let `argmax` silently
absorb an invalid candidate. `null` removes the candidate from the comparison entirely, which is
the only one of the three that cannot be mistaken for a measurement.

Executed evidence: `out/a02/a02_checks.json` →
`checks.null_never_wins`. `c05_overlapping` has `structure.sum_radii = 2.4519205208433132` — the
**highest nominal value in `C*`, equal to `c01`'s** — but E* returns `exit 2 / status invalid`,
the substrate records `search_signal = null`, and `c05` is never champion in either proposal
order.

## 2. Gap B — `argmax` on a tie is undefined

**Proposed frozen rule:**

```
c*_t = argmax over { c_i : i <= t and scalar(c_i) is not null } of scalar(c_i)
tie_break = smallest candidate_id by byte-wise comparison of its UTF-8 encoding
comparison = exact binary64; the A0.1 epsilon is NOT applied to selection
```

**The rejected alternative, and why.** `max()` over an insertion-ordered sequence keeps the first
maximum, so "earliest evaluation index" is the natural lazy choice — and it is wrong here, because
it makes `c*_t` a function of the order in which candidates happened to be *proposed*, while
`plan:490`/A0.2 requires the selection to be a property of the runtime's semantics. The
lexicographic rule is a function of the *set* of `(candidate_id, scalar)` pairs.

Executed evidence that this is not a cosmetic choice: with `C*`'s deliberate tie pair
`c01_good_hex` / `c03_mirror` (bit-identical metrics, different `solution.py` bytes), the frozen
rule returns `c01_good_hex` in **both** proposal orders, while the rejected rule returns
`c01_good_hex` in the forward order and `c03_mirror` in the reversed order
(`out/a02/a02_checks.json` → `checks.tie_break_observable.evidence`).

Also frozen: the comparison is exact binary64 and epsilon plays no part
(`checks.near_tie_not_absorbed`: `c01` − `c04` = `1.0000000000021103e-04` = 1.0e5 × epsilon, so no
tolerance window and no rank transform can reorder them).

**Suggested generalization.** The same two decisions exist for every runtime, and Loreley's
"same cell" condition is the same kind of missing tie-break statement. A
`a0/contract/selection/<runtime>.selection.json` convention (`schema: a0.selection/v1`,
fields `scalarization`, `selection`) would let the four adapters declare these in one place with
one digest, and would let the trace's `selection.tie_break` field be checked against a frozen
value instead of an adapter-local string.

## 3. `failure_stage` for an E* verdict is not specified per stratum

The trace schema fixes the enum but not which stage an `invalid` or `error` candidate lands in.
SimpleLoop freezes this mapping and reports it so the four runtimes can share one:

| E* verdict (`failure.kind`) | `failure_stage` |
|---|---|
| exit 0 `ok` | `none` |
| exit 2 `invalid` (`invalid_configuration`) | `verify_failed` |
| exit 3 `candidate_import_failed` | `resolve_failed` |
| exit 3 `non_deterministic` | `verify_failed` |
| exit 3 `runtime_budget_exceeded` | `timeout` |
| exit 3 `candidate_call_raised`, `child_terminated_early`, other | `evaluator_failed` |

Without a shared mapping, the per-runtime `FailureStage` counts that `plan:577`/`plan:628` require
in the final report are not comparable across runtimes — the same candidate would inflate a
different counter in each.

---

## 4. Defect — `selection.source_score_event_id` cannot be satisfied in a per-kind trace file

`trace_schema.md` §1 mandates three files per run
(`<runtime>.<run_id>.{score,selection,resource}.jsonl`); `trace_schema.md` §6 and
`adapter_contract.md` §6.3 require `source_score_event_id` to name a score event *in the stream*;
`trace_validate.py:186-192` resolves that reference **within one file**. A conformant adapter that
writes the three files separately therefore cannot exit 0 on the selection file. Measured, on a
real run of this adapter:

```
$ python a0/contract/trace_validate.py validate --trace <run>/traces/simpleloop.a02-forward.selection.jsonl
INVALID line 1: selection.source_score_event_id 'a02-forward.s0.i0.c02_baseline_upstream' has no score event in this stream
...
6 error(s) in 6 event(s)   (exit 1)
```

while the other two files validate clean (`valid: 6 event(s)` / `valid: 7 event(s)`), and the same
run's events in `event_seq` order in one stream validate clean (`valid: 19 event(s)`).

Three ways to close it; the workstream's preference is (b):

* (a) relax `trace_validate.py` so the check runs over a run's merged stream, or accept
  `source_score_event_id: null` for split files;
* (b) **mandate the merged stream as the validation unit** — keep the three per-kind files as the
  reading interface, and require
  `<run_dir>/traces/<runtime>.<run_id>.all.jsonl` (all events in `event_seq` order) as what
  `trace_validate.py` is pointed at. This preserves the field, preserves the three-file layout,
  and needs only a doc change plus one line in `adapter_contract.md` §6.3.
* (c) drop the field from the schema and rely only on `selection.considered`.

This adapter already writes the merged stream
(`out/a01/traces/simpleloop.a01.all.jsonl`, `out/a02/runs/*/traces/*.all.jsonl`) and reports the
per-file verdicts truthfully, so nothing is hidden either way — but until the contract says which
file is the validation unit, "exit 0 for all three files" is unsatisfiable for any runtime whose
selection events are traceable.

**Resolved during this round.** The contract owner landed option (b):
`trace_schema.md:29-44` makes the run's merged stream the validation unit and
`trace_validate.py` gained `validate-run --run-dir <run_dir>` (`adapter_contract.md:403`). Verified
against this adapter with no change to any trace:

```
$ python a0/contract/trace_validate.py validate-run --run-dir out/main
[ok ] simpleloop.main  events=22  [score=7 resource=8 selection=7]  merged simpleloop.main.all.jsonl
valid: 1 run(s), 22 event(s)
```

All seven runs here validate clean under that unit. The adapter now reports the run-unit verdict
separately from the per-file one (`a0_adapter/runner.py::validate_run_dir`) and only warns when the
frozen unit fails.

---

## 5. What the contract owner may want to know about EID*

Binding decision 1 is confirmed by execution: the authoritative `EID*` is
`664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`, from
`a0/tasks/circle-packing/plumbing.EID.proposed.json` +
`plumbing.contract.proposed.json`, and

```
$ a0/contract/.venv/bin/python a0/contract/evalcontract.py verify \
    --eid-file a0/tasks/circle-packing/plumbing.EID.proposed.json \
    --spec     a0/tasks/circle-packing/plumbing.contract.proposed.json
clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328   (exit 0)
```

**Corrected — there is nothing to fix in the contract (verifier finding R2).** An earlier revision of
this handoff claimed that `a0/contract/out/plumbing.EID.json` "still carries `fac50fc4…` over the
wrong file" and that `contract/README.md` §2's printed value and `adapter_contract.md` §1's
`EID* = fac50fc4…` were "the stale ones". That was already false when this file was written at
18:25: the contract was repaired at 16:57 and has carried `664115e0…` ever since. Verified by
execution on the current tree:

```
$ python -c "import json; d=json.load(open('a0/contract/out/plumbing.EID.json')); \
             print(d['eid_star']); print([r['path'] for r in d['components']['EvaluatorSource']['records']])"
664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
['e_star.py', 'e_star_child.py']            # mtime 2026-09-20 16:57:51

$ grep -n 'EID\* = 664115e0' a0/contract/adapter_contract.md a0/contract/README.md
a0/contract/adapter_contract.md:48:EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
a0/contract/README.md:61:EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
a0/contract/README.md:136:clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
a0/contract/README.md:323:   `EID* = 664115e0…`, matching `a0/tasks/circle-packing/plumbing.EID.proposed.json`. The full
```

The `EvaluatorSource` selects exactly `{e_star.py, e_star_child.py}` rooted at `tasks/circle-packing/`
— not `local_eval.py`. `local_eval.py` survives inside the same document only as hashed provenance
*data* under `components.DataManifest` (`records[33,37].data`, `declared.files[30,37]`) and in
`MetricDefinition`'s one-ULP note, which is correct: it is data the study reasons about, not the
evaluator. Every `fac50fc4…` that remains in `a0/contract/` is inside a revision note that labels it
wrong (`adapter_contract.md:12,59`; `README.md:104-109,322-324`); the only other live occurrence in
the tree is the conformance harness's deliberate negative fixture
(`conformance/fixtures/adapters/deviant.py::STALE_EID`, whose rendered reports are
`conformance/out/adapters/selftest_stale_eid.*`). No action is requested from the contract owner
here; the caution that still holds is the generic one — a third party must wire
`664115e0…`, and anything keyed to `fac50fc4…` is keyed to a document that no longer exists.

---

## 6. Adoption confirmed — the proposal landed, and the executed policy still matches it

The contract owner landed the proposal as `a0/contract/selection/simpleloop.selection.json`
(`schema a0.selection/v1`, `status frozen-a0-contract`, canonical digest
`ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd`) and declared in
`adapter_contract.md` §5.3 that the `scalarization` block and the `E*` verdict → `failure_stage`
table are **A0-wide** — all four runtimes must declare them, otherwise the per-runtime
`FailureStage` counts of `plan:577`/`plan:628` are not comparable. That closes Gaps A, B and §3
above; §4 was closed by the merged-run validation unit earlier.

Re-verified after adoption, by execution and not by reading. `tools/check-frozen-conventions`
(`a0/runtimes/simpleloop/tools/check-frozen-conventions`, output kept at
`out/conventions-recheck.json`) reports **PASS** on 11 checks, of which the load-bearing ones are:

| check | result |
|---|---|
| frozen digest = `ca995f95…` | PASS |
| frozen `scalarization` / `selection` byte-equal to `policy/simpleloop.policy.json` and to the proposal | PASS (both blocks, both directions) |
| 8/8 verdict rows of the frozen `failure_stage` table reproduced by `traces.failure_stage_for`, incl. the `other` fallback | PASS, mismatches: none |
| `solver_lane_produced_no_proposal` → `search_failed` | PASS — the frozen copy's one row this runtime does not put in `traces.py`; it is emitted at the loop's no-proposal site (`a0_adapter/loop.py:305`) |
| null gate + non-finite rejection in `policy.scalar_of` | PASS (`status != ok` → `None`, never `0.0`/`-inf`; `nan` rejected) |
| tie-break order-invariance over `C*`'s tie pair | PASS (frozen rule → `c01_good_hex` in both proposal orders; the rejected earliest-index rule flips to `c03_mirror`) |
| recomputed `EID_r` equals the handoff value | PASS (`5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e`; the conformance runner reports the same, `a0/conformance/report.md`) |

The one asymmetry worth knowing: the frozen `failure_stage_mapping` carries an extra
row (`solver_lane_produced_no_proposal`) that this runtime's policy file does not, because the
runtime implements that case at its call site rather than in the verdict table. The row still
matches what executes; a runtime adopting the frozen table verbatim should implement it in the same
place it decides that the solver produced no proposal.

Cross-runtime status after the refresh: `python3 conformance.py run --runtimes simpleloop`
→ `verdicts (A0.1 only): {"simpleloop": "PASS"}`, 14/14 rows with fresh `evaluator_evidence`
(`status: ok`), no NOTE; all 14 runs in `out/` validate clean under
`python a0/contract/trace_validate.py validate-run --run-dir <run_dir>`.
