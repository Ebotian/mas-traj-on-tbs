# Adapter contract

The frozen interface each runtime adapter (KAPSO / EvE / Loreley / SimpleLoop) implements, so
that a third party can drive all four identically and join their outputs. Protocol references:
`plan:513-528` (A0.1), `plan:557-567` (A0.2), `plan:569` (closure), `plan:591-603` (SimpleLoop's
fixed definition).

Everything here is a contract, not a suggestion: an adapter that deviates is non-conformant, and
its runtime is excluded from `R_1 = { r : A0.1_r ∧ A0.2_r }` (`plan:490`).

> **Revision note (identity arbitration).** An earlier revision of this file described upstream
> `scripts/local_eval.py` as `E*` and printed `EID* = fac50fc4…`. Both were wrong. The frozen
> evaluator is `a0/tasks/circle-packing/e_star.py` (+ `e_star_child.py`) and the frozen identity
> is `664115e0…`; §1 records why, and `README.md` §2 records the digests. Any adapter written
> against the earlier text is wired to the wrong evaluator and must be re-pointed.

---

## 1. The frozen identity every adapter starts from

An adapter must be handed the `EID*.json` document produced by `evalcontract.py` and must:

1. read `eid_star` from it and copy it verbatim onto every trace event;
2. wire its evaluator so that the evaluator's *source, dependency lock, data and config* are
   exactly the ones the document recorded — that is what makes `EID*` true rather than nominal;
3. run `python evalcontract.py verify --eid-file <EID*.json> [--base <workspace root>]` before
   the run and abort if it reports drift. `verify` re-hashes the declared inputs and fails with a
   non-zero exit if any of them changed.

```
compute :  python evalcontract.py compute  --spec <spec.json> [--out <EID.json>]
verify  :  python evalcontract.py verify    --eid-file <EID.json> [--spec <spec.json>] [--base <root>]
recompute: python evalcontract.py recompute --eid-file <EID.json>
```

`recompute` touches no filesystem and is the third-party check that `EID*` follows from the
recorded inputs.

**The frozen evaluator is `E*` = `a0/tasks/circle-packing/e_star.py` (+ its helper
`e_star_child.py`)** — the study's canonical evaluator, not upstream's
`circle-packing/scripts/local_eval.py`. The spec that declares this is
`contract/plumbing.contract.json`, whose `EvaluatorSource` selects exactly
`{e_star.py, e_star_child.py}` rooted at `tasks/circle-packing/`.

For the plumbing task the frozen value is

```
EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
  EvaluatorSource    a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  DependencyLock     7b02f1a71288335ff92fe68da8804349e416ba4ae9e95f8cd0c6a3b5bc372a75
  DataManifest       b21c975a51ef24cdfb2078957f0e0e4b2fb194e7c55b3a8058febb019d214a21
  Config             550ca3cdd8af04ec0895a2515bbee40a9627b805d5477611995f4cef0f4043ac
  MetricDefinition   420ab0acf24e1c7325b089e2ec4bc6c3d074119c4f3ac8aac8ed3cfa1c45bfc0
```

(`contract/out/plumbing.EID.json`; see README for the exact command and its output).

> **Why this value replaces an earlier one.** An earlier revision of this contract hashed
> upstream `scripts/local_eval.py` and printed `EID* = fac50fc4…`. That was wrong twice over:
> hashing a file that is *not* the frozen evaluator makes `EID*` identify the wrong artifact,
> and `local_eval.py` is not even behaviourally equivalent — it accumulates `sum_radii` in a
> loop while the plugin the worker actually loads (`upstream/loreley/examples/
> circle_packing_env/evaluate.py`) uses `sum()`, a one-ULP difference; and it cannot express
> `invalid`/`error` verdicts, the audit fields, or the seed. `E*` mirrors the plugin.
> `local_eval.py` survives in `DataManifest` only as hashed *data* (upstream provenance), which
> is correct: it is an input to the study's reasoning, not the evaluator.

---

## 2. Consuming `C*`

`C* = {c_1, …, c_k}` is the fixed candidate set produced by the circle-packing workstream.

**The published path is `a0/tasks/circle-packing/C_STAR/manifest.json`** (14 members, schema
`a0.candidateset/v1`, `status: published`), not a `<candidates>/manifest.json` directory chosen
by each adapter. Every adapter takes exactly that path. The producing workstream owns the file
and has added fields beyond the required ones (`dir`, `kind`, `expected_status_at_theta_e_star`,
`designed_relations`); an adapter may read them but must not depend on them being present.

Required shape:

```
a0/tasks/circle-packing/C_STAR/manifest.json
{
  "schema": "a0.candidateset/v1",
  "candidate_set_id": "C*",
  "task": "circle-packing",
  "candidates": [
    {"candidate_id": "c01_good_hex", "path": "c01_good_hex", "solution_sha256": "<64-hex>",
     "role": "good" | "baseline" | "bad" | "tie", "note": "..."}
  ]
}
```

Rules the adapter must enforce:

1. `path` is a directory containing `solution.py`, so that `E*`'s `--candidate` can point
   straight at it (`--candidate` accepts either the directory or the `solution.py` file).
2. **Integrity before every evaluation**: recompute `sha256(solution.py)` and abort with exit 4
   if it does not match `solution_sha256`. A silently edited candidate invalidates the whole
   comparison. This is checked per evaluation, not once per run — `E*` itself re-records
   `candidate.source_sha256` in the Outcome and `candidate_source_sha256` in the
   `E_STAR_MANIFEST` line, so the adapter can and must compare the three.
3. **Every candidate of `C*` is evaluated by every runtime.** No skipping, no early stopping,
   no runtime-specific filtering: A0.1 compares `E_r(c; theta_E)` against `E*(c; theta_E)` for
   *each* runtime and *each* candidate (`plan:513`).
4. The candidate set is part of `DataManifest` in `EID*`, and it is **published**: the plumbing
   spec now hashes all 28 files of `C_STAR/` under `DataManifest.files` instead of carrying a
   placeholder. When `C*` changes, `EID*` changes, and that is the intended behaviour
   (`plan:509`).
5. `candidate_id` in the traces is exactly `candidate_id` from the manifest — the join key must
   not be re-derived from a path or a hash.

---

## 3. Adapter CLI

One executable, four runtimes, identical flags:

```bash
uv run --project <adapter_dir> python -m a0_adapter run \
  --runtime {kapso|eve|loreley|simpleloop} \
  --task circle-packing \
  --candidate-set <a0/tasks/circle-packing/C_STAR/manifest.json> \
  --eid <a0/contract/out/plumbing.EID.json> \
  --theta seed=1337,fidelity=fast,fraction=0.15 \
  --fr <a0/contract/fr/scalar.json> \
  --run-id <id> \
  --run-dir <dir outside every candidate worktree> \
  --budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1 \
  --traces score,selection,resource
```

`--theta` values are the ones recorded on every event; a parameter that the runtime cannot
receive is passed as `none` and then *must* be recorded in `theta_E.defaults_applied` with the
fixed equivalent value used instead (`plan:518`). Example: EvE/Loreley receive no seed, so
`--theta seed=none,...` and each event carries
`defaults_applied.seed = {"value": "evaluator-internal-unseeded", "source": "..."}`.

The example above is the **fast** theta, which is what the `E_STAR.json` reference table is
generated for; it is the right choice for a cheap A0.2 selection-semantics run. The **canonical
A0.1 conformance theta** is the one frozen in `EID*`'s `Config.value.theta_e_canonical`:
`seed=1337, fidelity=full, fraction=1.0, n=26, runs=5, runtime_budget_ms=250.0, timeout_s=120.0`.
Both are legitimate; a run must declare which one it used, and `theta_E` on the trace must match
the theta that was handed to `E*` (see §4.2).

Two further subcommands:

```bash
uv run --project <adapter_dir> python -m a0_adapter conformance \
  --runtime <r> --candidate-set <C*> --eid <EID.json> --theta <theta> \
  --epsilon 1e-9 --out <conformance.json>

uv run --project <adapter_dir> python -m a0_adapter closure-probe \
  --runtime <r> --run-dir <dir> --out <closure.json>
```

### 3.1 Exit codes (identical for all four runtimes)

| Code | Meaning |
|---|---|
| 0 | run completed within budget; all three traces written (and, for any runtime whose selection events carry `source_score_event_id`, the merged `.all.jsonl`, §6.3) |
| 2 | usage / configuration error (bad flags, missing file, unreadable `C*`) |
| 3 | contract mismatch: `EID*.json` does not describe the evaluator actually wired, or `verify` reported drift |
| 4 | candidate-set integrity failure (`solution.py` sha256 mismatch, missing candidate, malformed manifest) |
| 5 | A0.1 conformance failure for at least one candidate in `C*`: the score disagrees beyond `epsilon`, **or** the `status` disagrees, **or** the `failure.kind` disagrees, **or** the `failure_stage` derived from them disagrees with the frozen table (§4.5, §5.3) |
| 6 | closure violation: the probe observed autonomous external acquisition |
| 7 | budget exhausted (`B_hard` reached); traces are still written and complete up to the stop |
| 8 | the runtime failed to produce any evaluable candidate (all `C*` attempts failed at an earlier stratum); traces written |
| 10 | internal adapter error (bug); traces written as far as possible |

An adapter **must write partial traces before exiting with 7 or 8** — those exits are results,
not crashes, and the failure counters (`plan:577`) are what makes them interpretable.

---

## 4. Where the numeric score comes from

### 4.1 The frozen invocation

```bash
a0/tasks/circle-packing/.venv/bin/python a0/tasks/circle-packing/e_star.py evaluate \
  --candidate <dir containing solution.py> --seed 1337 --fidelity full --fraction 1.0 \
  --out <outcome.json> [--state-dir <dir>] [--emit-resources <path>]
```

* `--candidate` accepts the directory or the `solution.py` file itself.
* `--fidelity {full,fast}`; `--fraction` is the audit fraction in `(0, 1]` and defaults to `1.0`
  at `fidelity=full` and `0.15` at `fidelity=fast`. `fidelity=full` with any other fraction is
  **rejected**, not silently normalised: `--fidelity full --fraction 0.15` prints
  `e_star: --fidelity full evaluates every item; pass --fraction 1.0 …` and exits **3**.
  Optional: `--n` (default 26), `--runs` (default 5), `--runtime-budget-ms` (default 250.0,
  `<= 0` disables), `--timeout-s` (default 120.0).
* `--out` is the **canonical Outcome** (compact, sorted, ASCII JSON). `--state-dir` is the state
  root for run records; `E*` writes only below `--state-dir` and `--out`, never inside a
  candidate tree.
* `--emit-resources` **takes a path**, it is not a bare flag (an earlier revision of this file
  and of the task brief wrote it as `[--emit-resources]`). It writes the timing sidecar;
  timings never enter the canonical Outcome — `outcome.resources` is always `null`.

### 4.2 Exit codes, stdout, and the score surface

| `E*` exit | `outcome.status` | Meaning |
|---|---|---|
| 0 | `ok` | measured; the objective is defined |
| 2 | `invalid` | the candidate **ran** but the configuration is invalid (overlap, wrong count, out of bounds, …) |
| 3 | `error` | the candidate could not be measured (import failed, raised, non-deterministic, over budget, …) |

* **stdout is exactly one line** — the deterministic manifest line:

  ```
  E_STAR_MANIFEST {"candidate_source_sha256": ..., "canonical_digest": ...,
   "e_star_version": ..., "evaluator_source_sha256": ..., "fidelity": ..., "fraction": ...,
   "items": ..., "objective": {...}, "schema": "e_star.manifest/v1", "seed": ...,
   "status": ..., "total_items": ...}
  ```

  Sorting is `sort_keys=True`, so the line is byte-reproducible. Everything else `E*` prints goes
  to **stderr**. An adapter that parses JSON from stdout will fail; parse the `_MANIFEST` line or
  read `--out`.
* **The score surface is `outcome.fields.sum_radii`**, and it is `null` unless
  `status == "ok"`. It is never `0.0` on failure. `outcome.objective.value` carries the same
  number when `status == "ok"` and is `null` otherwise; the adapter asserts
  `objective.value == fields.sum_radii` whenever `status == "ok"`.
* The **Outcome** recorded on the score trace is the multi-field `outcome.fields` map — never
  pre-scalarized (`plan:549`).
* `outcome.validity.checks` lists the named gates that ran
  (`count_equals_n`, `radius_positive_check`, `bounds_check`, `overlap_check`,
  `determinism_check`, `runtime_budget_check`), and `outcome.failure.kind` names why a
  non-`ok` verdict was reached. Both belong on the score event (`trace_schema.md` §3.3).

### 4.3 What the adapter must do with it

1. **Read `--out` (or the manifest line), never a human rendering.** `E*` emits no
   `target_metrics`/`repo_root` payload; an adapter that expects upstream `local_eval.py`'s JSON
   shape is wired to the wrong evaluator.
2. **Pass `theta_E` through unchanged.** The `seed` is a genuine evaluator input, not a
   comparability label: at `fidelity=fast` it draws the audited subsample, so changing it changes
   which items are checked and therefore which verdicts are reachable
   (`outcome.validity.audit.sample`, `sample_sha256`). Measured on `C_STAR/c01_good_hex`:
   `seed=1337 → sample [0, 3, 12, 22]`, `seed=1338 → sample [0, 14, 18, 24]`
   (`.venv/bin/python e_star.py evaluate --candidate C_STAR/c01_good_hex --seed <S> --fidelity
   fast --fraction 0.15 …`). At `fidelity=full` the seed is inert because every item is audited,
   but it is still recorded. A runtime whose evaluator lane cannot receive a seed must record
   `theta_E.defaults_applied.seed` with the fixed value it used instead (`plan:518`).
3. **The invoked `E*` and the recorded one must be the same file.** `E*` records
   `evaluator_source_sha256` in both the manifest line and the Outcome; the adapter records it in
   `evaluator_evidence` and asserts it is the digest of the `e_star.py` the `EID*` document
   hashed. `EID*`'s `EvaluatorSource` digest covers `e_star.py` + `e_star_child.py`, so a
   mismatch means the adapter executed something else.
4. **No absolute paths in traces.** `E*`'s Outcome deliberately contains no path (it records
   `candidate.source_sha256` and `source_bytes`, not the location), but `--out`, `--state-dir`
   and the `e_star:` status line on stderr do. The adapter must strip or rewrite those before
   writing them into a trace; the trace is a shared artifact and must not leak host layout.
5. **Never take a score from a runtime's own summary.** KAPSO's `node.score` can silently hold a
   judge score (D16), EvE maps evaluator exceptions to `failure_score(0.0)`, and Loreley may
   reuse a cached metric. The adapter reads `E*`'s Outcome, maps the verdict to a
   `failure_stage` with the **frozen table** (§5.3), and records what happened in
   `evaluator_evidence` (`trace_schema.md` §5).

### 4.4 The A0.1 comparison

For each `c ∈ C*`, `|E_r(c) − E*(c)| <= epsilon` with the `epsilon` from the frozen `Config`
(`contract/plumbing.contract.json`: absolute, `1e-9`, in `sum_radii` units). The reference side
`E*(c)` is computed with the same `theta_E` and the same candidate directory, and recorded per
candidate in `conformance.json`.

This comparison has **two halves, and both are conformance**. Nine of the fourteen members of `C*`
are not `ok` (4 `invalid`, 5 `error`), so the non-`ok` half is the larger half of the data:

1. a **number** comparison where `E*` produced a number — `|E_r − E*| <= epsilon`; and
2. a **verdict** comparison everywhere — `status`, **and** `failure.kind`, **and** the
   `failure_stage` that follows from it (§4.5).

### 4.5 A0.1 conformance is owed on the failure stage, not only on the status

**This is a requirement on the adapter, not an artefact of any one checker.**

> **Requirement.** For every candidate `c ∈ C*` and every runtime `r`, the row reported by `r`
> must agree with `E*` on **all three** of: (a) `status`, (b) `failure.kind`, and (c) the
> `failure_stage` derived from (a) and (b) by the frozen A0-wide table (§5.3). **Any disagreement
> on any of the three fails that row, and therefore fails `A0.1_r`**, regardless of whether the
> `status` and the score alone happen to agree.

The rule this replaces, quoted so that citations of the earlier revision still resolve against
something:

> Candidates whose `E*` verdict is `invalid` or `error` compare on **verdict and `failure.kind`**,
> not on a number.

That sentence was always the rule; it was simply not enforced. It is restated above as (a)(b)(c)
because "verdict" was ambiguous enough to be read as the coarse `status` alone — which is exactly
the reading that produced the false PASS in the auditor's R1.

(a) alone is not conformance. An adapter that reports a truthful `status` and a *wrong*
`failure.kind` has mis-attributed the failure: it will emit the wrong `failure_stage`, which is
precisely the quantity the study reports per runtime. `plan:577` and `plan:628` require
`FailureStage` counts and the `resolve_failed` / `comprehension_failed` / `mechanism_mismatch`
breakdowns to be **comparable across runtimes**, and that comparability is the *only* reason the
frozen table exists. A runtime that maps `candidate_import_failed` to `evaluator_failed`, or
`non_deterministic` to `timeout`, produces counts that do not join, and its A0.1 answer is not
evidence about that runtime's evaluation lane.

Concretely, for the nine non-`ok` members of `C*` the expected pairs are:

| candidate | `E*` status | `E*` `failure.kind` | frozen `failure_stage` |
|---|---|---|---|
| `c05_overlapping` | `invalid` | `invalid_configuration` | `verify_failed` |
| `c06_empty` | `invalid` | `invalid_configuration` | `verify_failed` |
| `c07_single` | `invalid` | `invalid_configuration` | `verify_failed` |
| `c08_out_of_bounds` | `invalid` | `invalid_configuration` | `verify_failed` |
| `c09_malformed_import` | `error` | `candidate_import_failed` | `resolve_failed` |
| `c10_raises` | `error` | `candidate_call_raised` | `evaluator_failed` |
| `c11_non_deterministic` | `error` | `non_deterministic` | `verify_failed` |
| `c12_exit_without_artifacts` | `error` | `child_terminated_early` | `evaluator_failed` |
| `c13_slow` | `error` | `runtime_budget_exceeded` | `timeout` |

Two of these rows are the ones a "status-only" comparison is least able to fake and most likely to
mangle: `c13_slow` is the only `timeout`, and `c11_non_deterministic` and `c09_malformed_import`
are the only rows whose stage is not `evaluator_failed`. A runtime that collapses every `error`
into `evaluator_failed` passes a status-only check and produces a `FailureStage` table in which
`timeout` is 0 and `resolve_failed` is 0 — both of which the study reports.

A `failure.kind` that `E*` cannot produce, or a `failure_stage` outside the frozen table, is a
failure of the row by itself; an adapter must not invent a stage for a case the table does not
cover, and must not "repair" a mismatch by re-mapping at report time. A runtime-side stage that is
*not* derived from an `E*` verdict (KAPSO's `boundary_violation`) is admissible only under the
conditions in §5.3.3, and a row carrying one is not an `E*`-comparable measurement.

This is **per row**, not an aggregate test. The counts over `C*` are a derived quantity and a
necessary condition — see §5.3.2, which states why a matching count is not conformance and gives
the frozen expected counts.

**A row that fails while `E*`'s verdict is `ok`** — the runtime disagreed, or produced no
measurement at all — has no entry in the frozen table, so the table cannot stage it. It is **not** a
pass, and it is **never** staged `none`. The assigned stage, the labelling, and the consequence for
`A0.1_r` and for joining counts are in §5.3.4.

---

## 5. Declaring `F_r` and the `EID_r → EID*` mapping

### 5.1 Default first-round rule

> A1 的第一轮固定共同信息，即 `F_r(E*) = scalar(E*)`

`plan:528`. **Every adapter's first round declares `F_r(E*) = scalar(E*)`**, and freezes that
declaration before running. The declaration is a small JSON file referenced from `--fr` and its
sha256 is recorded as `fr.spec_hash` on every score event:

```json
{
  "schema": "a0.fr/v1",
  "name": "F_r = scalar(E*)",
  "version": "v1",
  "applies": "scalar",
  "input": "outcome.fields.<primary_field>",
  "primary_field": "sum_radii",
  "direction": "maximize",
  "frozen_before_run": true
}
```

For the plumbing task `scalar(E*) = outcome.fields.sum_radii`, maximize. A runtime's *native*
`F_r` (KAPSO scalar, EvE PyTree, Loreley multi-objective archive) may be run as a separate
control arm later, but the two may never be mixed in one "runtime comparison" (`plan:528`).
Loreley's QD behaviour is still exercised — through the `selection` trace, whose archive
decisions are what A0.2 checks (`plan:567`).

`fr.spec_hash` is the digest of the declaration's **canonical form**, not of its bytes:
`evalcontract.canonical_file_digest(path) = sha256(canonical_json(json.load(path)))`. Reformatting
or reordering the file must not change the frozen identity; editing any value must. The frozen
first-round declaration in this repository is `fr/scalar.json`, whose hash is

```
fr.spec_hash = 1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0
```

(pinned by `tests/test_evalcontract.py::test_fr_declaration_hash_is_pinned`).

### 5.2 Mapping declaration

The adapter states, in the run's `adapter.md` (a file the adapter writes into `--run-dir`) and on
every event as `eid_r`:

| Runtime | `native_scheme` | `mapping_mode` | `declaration` must say |
|---|---|---|---|
| KAPSO | `manifest_fingerprint` | `native` | how the registered-evaluation manifest is generated from the `EID*` inputs, and that `(fidelity, fraction, seed)` from the manifest equals the granted class (`plan:534-538`). **There is no evaluator field in KAPSO's manifest** — see §5.4 |
| EvE | `none` | `adapter_declared_injection` | that EvE has no native identity, and exactly which environment variables / log root the adapter pins (`EVE_EVAL_LOG_ROOT` etc.) so the frozen evaluator is the one that runs |
| Loreley | `evaluator_name_version_campaign_program_hash` | `native` | how the campaign program hash is computed over the contract-frozen evaluator program |
| SimpleLoop | `none` | `adapter_declared_injection` | that the adapter is the sole source of the evaluator identity |

`recomputable: true` is a claim the adapter must be able to back: a third party must be able to
recompute `value` (or its derivation from `EID*`) from the documented inputs.

### 5.3 The frozen selection / scalarization declaration

`fr/scalar.json` says *what* is read (`outcome.fields.sum_radii`, maximize) but not what happens
when `outcome.status != "ok"`, and `plan:591-603` fixes SimpleLoop's `argmax` without saying what
`argmax` does on a tie. Both were unspecified, and an unspecified tie-break or fold makes A0.2
untestable. **Frozen:**

All four runtimes now have a frozen canonical copy here. **The frozen copies all live in
`contract/selection/`; their runtime-side originals do not follow one path convention** — EvE's is
at `runtimes/eve/selection/eve.selection.json` and KAPSO's at
`runtimes/kapso/contract/selection/kapso.selection.json`, but **Loreley's is at
`runtimes/loreley/policy/loreley.selection.json` (a `policy/` directory, not a `selection/`
one)**. A reader who globs for `**/selection/*.selection.json` will find three of the four; use
this table, not a path convention.

```
a0/contract/selection/simpleloop.selection.json   (status frozen-a0-contract)
  canonical digest = ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd
  runtime-side original: (none — the contract copy is the only one)
a0/contract/selection/kapso.selection.json        (status adopted-by-kapso-workstream)
  canonical digest = c1a993650b4edc4e7a0a799d12d2f6f74e7927b364021dd454454b6e22fc4d6c
  runtime-side original: runtimes/kapso/contract/selection/kapso.selection.json
  re-adopted 2026-09-20 19:24 (source file modified 19:23:25),
  superseding 143bfc949f074079e612041622640afd8321ff7c24dab0b62d0cfda8a4e10d59
a0/contract/selection/eve.selection.json          (status adopted-by-eve-workstream)
  canonical digest = 1d4a30d546ba3224b4ff9dff61bfad1b60a4730669281ba07f4ad8a6207783a0
  runtime-side original: runtimes/eve/selection/eve.selection.json
a0/contract/selection/loreley.selection.json      (status adopted-by-loreley-workstream)
  canonical digest = 94d7139d726b2356d60ff6e32cdb5d8681047c9e84e4fb2a0cd7b2b827864aa1
  runtime-side original: runtimes/loreley/policy/loreley.selection.json   <-- policy/, not selection/
```

**Both copies live in this directory and both are frozen here.** A declaration is frozen by being
*recorded* in this contract with a pinned digest — the file's own `status` string is descriptive
text, not the freeze mechanism. The two copies were frozen differently on purpose:

* SimpleLoop's copy was edited on adoption (`status: proposed-… → frozen-a0-contract`), because no
  other artifact had published a digest for the proposal.
* KAPSO's copy is admitted **byte-for-byte unmodified**, including its
  `status: "adopted-by-kapso-workstream"` and its `status_note`. Editing one byte to relabel it
  would re-digest the file and orphan the digest recorded inside KAPSO's own run artifacts.
  "Not edited" is the freeze.

**A freeze here is a snapshot, not a handshake.** The first KAPSO freeze (`143bfc94…`) was already
stale within the hour: the runtime-side declaration was corrected at 19:23 while this file was
being edited, so `143bfc94…` no longer described it. Re-adoption is the normal repair — the
contract owner re-verifies equality, re-pins the digest, and records the superseded value — and it
is the reason `adapter_contract.md` pins digests rather than trusting a path. A runtime-side
declaration is not frozen merely because the contract copied it once; it is frozen at the digest
pinned here, and any later change to it **must** come back as a re-adoption request. KAPSO's own
self-check reports the condition (`selection.frozen_canonical_copy`)
and correctly reported `identical_to_this_declaration: false` for the stale copy rather than
passing silently; it should now read `true` against `c1a99365…`.

The rows below are the frozen rules of SimpleLoop's declaration, which is the one referenced by
`plan:591-603`. Only `scalarization` and `failure_stage_mapping` are A0-wide; each runtime's
`selection` block is its own (KAPSO's, for instance, describes `parent_policy="best"` over its node
history plus a separate tier rule for the deliverable, and declares its tie-break divergence in
§5.3.1).

| Field | Frozen rule |
|---|---|
| `scalarization.status_gate` | the scalar is defined **iff** `outcome.status == "ok"`; otherwise it is `null` |
| `scalarization.null_is_not_zero` | a null scalar is **never** coerced to `0.0` or `-inf`; the candidate is recorded as unscored and excluded from the `argmax` |
| `selection.rule` | `c*_t = argmax over { c_i : i ≤ t and scalar(c_i) is not null } of scalar(c_i)` |
| `selection.tie_break` | **smallest `candidate_id` by byte-wise comparison of its UTF-8 encoding** |
| `selection.comparison` | exact binary64; the A0.1 `epsilon = 1e-9` is a *conformance* tolerance and is **not** applied in selection |

`null` is the only one of the three possible foldings that cannot be mistaken for a measurement:
`0.0` is precisely the false green the protocol names for EvE (`plan:551`), and `-inf` would let
an `argmax` silently absorb an invalid candidate. The tie-break is a function of the *set*
`{(candidate_id, scalar)}`, which is what A0.2 requires; "earliest evaluation index" is a function
of proposal order and was rejected.

The **same `scalarization` block and the same `failure_stage_mapping` table are A0-wide**: all four
runtimes must declare them, otherwise the per-runtime `FailureStage` counts that `plan:577` and
`plan:628` require are not comparable. The table is:

| `E*` verdict | `failure_stage` |
|---|---|
| exit 0 `ok` | `none` |
| exit 2 `invalid` | `verify_failed` |
| exit 3 `candidate_import_failed` | `resolve_failed` |
| exit 3 `non_deterministic` | `verify_failed` |
| exit 3 `runtime_budget_exceeded` | `timeout` |
| exit 3 `candidate_call_raised`, `child_terminated_early`, other | `evaluator_failed` |
| the agent lane produced no proposal at all | `search_failed` |

The `note` inside `failure_stage_mapping` says "SimpleLoop freezes it here and reports it to the
contract owner". That sentence is inherited by every copy of the block and is **descriptive text
inside the frozen block, not a statement of ownership** — the block is frozen A0-wide, and the
table above is normative. Verify block equality by canonical form, never by eye:

```
sha256(canonical_json(declaration["scalarization"]))          = d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c
sha256(canonical_json(declaration["failure_stage_mapping"]))  = 201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f
```

**All four frozen copies reproduce both digests exactly**, so the two A0-wide tables are now
literally the same bytes' worth of canonical form in every runtime's declaration (checked with the
same `sha256(canonical_json(block))` scheme the KAPSO adapter uses in
`runtimes/kapso/a0_adapter/common.py:408-417`). Two of them enforce it rather than asserting it:
EvE's adapter re-derives both digests at run time and **refuses the run (exit 3)** if the
contract's block, the frozen digest and its own copy do not all agree
(`runtimes/eve/a0_adapter/selectionmap.py`: `check_adoption()`, verified `agrees: True`), and
Loreley recomputes both and refuses a run whose blocks differ.

**EvE and Loreley: the blocks are in, the counts are not yet.** Both now have a frozen declaration
here and both reproduce the two block digests above, so the A0-wide tables are uniform across all
four runtimes. What is still outstanding is the *count* consequence: the conformance runner
reported their declared `FailureStage` counts over `C*` as not matching the frozen map before
adoption (§5.3.2 records the numbers). Re-running the sweep with the adopted table is what closes
it — and the expected shape is now stated exactly: with no extension rows (§5.3.4), the counts must
equal the frozen map; with extension rows, the frozen-map count must equal the frozen map
*restricted to the candidates that were measured*, and the extension rows are reported separately.

#### 5.3.1 KAPSO's runtime tie-break diverges from the A0-wide rule

Recorded because a later step must **not** assume the two rules are the same function:

| | rule | function of |
|---|---|---|
| A0-wide, frozen | smallest `candidate_id` by byte-wise comparison of its UTF-8 encoding | the *set* `{(candidate_id, scalar)}` |
| KAPSO, measured | `max()` over `node_history` keeps the **first** maximum, so the tie goes to whichever tied node was inserted first (`strategy.py:1420-1434`) | proposal **order** |

They are different functions and they are **not** interchangeable, and the divergence is now
**demonstrated in both proposal orders by execution** on `C*`'s own tie pair (`c01_good_hex` /
`c03_mirror`, whose scores are bit-identical at `2.4519205208433132`):

| proposal order | KAPSO selects (parent / deliverable / next-round parent) | A0-wide rule | evidence |
|---|---|---|---|
| `c01_good_hex` first | `c01_good_hex` | `c01_good_hex` | `runtimes/kapso/runs/a0-01/a02/a02.json` → `scenarios.tie_break` |
| `c03_mirror` first | `c03_mirror` | `c01_good_hex` | `runtimes/kapso/runs/tie-order-probe/outcome.json` → `diverges_from_frozen_tie_break: true`, `byte_wise_smallest_candidate_id: c01_good_hex` |

> **Correction to an earlier revision of this section.** It said `C*` "contains no tie pair on
> which the two rules disagree under a counterbalanced proposal order, so nothing in the study
> currently discriminates them". **That was wrong**, and the tie-order probe (the adapter's own A0.2
> machinery with the proposal order reversed) is the counter-example: on the *same* tie pair the two
> rules disagree as soon as `c03_mirror` is proposed first. The rules are discriminated by `C*`
> itself; what the shipped A0.2 scenario fails to do is *exercise* the discriminating order.

Consequences, binding on the A0.2/A1 tests and on how the A0.2 result may be cited:

1. **The A0.2 `tie_break` assertion does not establish the frozen tie-break for KAPSO, and must not
   be cited as if it did.** It passes because `c01_good_hex` is both the byte-wise smallest and the
   one proposed first — a coincidence of the scenario's candidate order, not an implementation of
   the rule. As run, the assertion establishes only that KAPSO's selection follows the *score*
   ordering.
2. The assertion must therefore assert what is actually frozen: that the recorded
   `selection.tie_break` matches **the runtime's own declared rule**, and that the tied candidates
   are both *valid* maxima. It must not assert the byte-wise identity of the winner for a runtime
   whose declaration says a different rule applies. A run that wants to test the frozen rule as a
   rule must exercise the discriminating order (propose the byte-wise *larger* tied candidate first)
   and report both orders.
3. KAPSO is **not** non-conformant for the divergence itself: A0.2 compares a runtime against the
   semantics it claims (`plan:557`, "各 runtime 是否按自己声称的 selection semantics 消费评价"), and
   KAPSO declares the divergence in `selection.tie_break_divergence` with its evidence rather than
   hiding it — and that declaration is the frozen `c1a99365…` above. The A0-wide tie-break is the
   rule for runtimes whose selection is a function of the candidate *set* (SimpleLoop); it is not a
   mandate to reimplement `parent_policy`, and an order-dependent tie-break cannot be repaired
   inside an adapter without changing the runtime.
4. **Consequence for substrate selection (A1).** If a later step needs a substrate whose selection
   is order-invariant, KAPSO is not it, and the difference is not visible in the A0.2 result as
   currently reported. Any cross-runtime statement about tie behaviour must carry this qualification.

#### 5.3.2 The conformance requirement is per *row*; the counts over `C*` are derived

Asked directly here because the two readings give different verdicts, and the answer is the first:

* **The requirement is per row.** For every `c ∈ C*` and every runtime `r`, the row must agree with
  `E*` on `status`, `failure.kind`, and the `failure_stage` derived from them (§4.5). That is
  A0.1 conformance.
* **The aggregate over `C*` is not a separate requirement.** It is implied by the per-row rule, so
  demanding it again would be redundant *and* strictly weaker — a runtime can match the counts by
  permuting stages between candidates. A count mismatch is therefore a **guaranteed** A0.1 failure
  (it proves at least one row disagrees), but a count *match* proves nothing on its own.
* **Both must be reported.** The counts are a cheap triage signal that points at a failing runtime
  without reading 14 rows; the rows are the evidence. Use the counts to find the runtime, the rows
  to state the verdict.

The frozen expected counts follow from `E_STAR.json` and are fixed by this contract:

```
over the 14 units of C*:  none=5  verify_failed=5  resolve_failed=1  evaluator_failed=2  timeout=1
  none              c01_good_hex c02_baseline_upstream c03_mirror c04_near_tie c14_near_zero
  verify_failed     c05_overlapping c06_empty c07_single c08_out_of_bounds   (invalid_configuration)
  verify_failed     c11_non_deterministic                                     (non_deterministic)
  resolve_failed    c09_malformed_import                                      (candidate_import_failed)
  evaluator_failed  c10_raises (candidate_call_raised)  c12_exit_without_artifacts (child_terminated_early)
  timeout           c13_slow                                                  (runtime_budget_exceeded)
```

The unit is **one unit per candidate of `C*` in the conformance run** — `14` for the frozen set —
matching `trace_validate.py:count_failure_stages`, which counts distinct
`(run_id, iteration, candidate_id, stage)` tuples rather than log lines. A runtime that reports a
different number of units has a unit-definition defect: its counts are not comparable to the frozen
map at all and must be reconciled before a count verdict means anything.

These are the counts a runtime must reach **over the candidates it measured**, and reaching them is
necessary but not sufficient (§4.5 is the requirement). A row the frozen table cannot stage — the
runtime failed on a candidate `E*` measured `ok`, or there is no `E*` verdict at all — is removed
from this counter and reported separately, so the number above is never contaminated by a
runtime-side cause; the partition and the check that makes it verifiable are §5.3.4 Rule 6.

**Observed at the time of writing** (2026-09-20, as reported by the conformance runner; expected to
change as the owners land the adoption, and recorded here so their owners have the number):

| runtime | declared counts over `C*` | verdict |
|---|---|---|
| EvE | `{none: 5, resolve_failed: 9}` | every non-`ok` row collapsed into `resolve_failed`; differs from the frozen map → at least one row fails |
| Loreley | `{none: 6, resolve_failed: 5, verify_failed: 4}` = **15 units for 14 candidates** | both a mismatch against the frozen map and a unit-count defect that must be resolved first |

Note what the EvE figure specifically cannot be: `resolve_failed` is the stage for exactly one
candidate (`c09_malformed_import`, `candidate_import_failed`). A runtime reporting nine of them has
either mis-mapped `invalid_configuration` / `non_deterministic` / `runtime_budget_exceeded` /
`candidate_call_raised` into it, or is not reporting `failure.kind` at all. Either way the
`resolve_failed` / `timeout` / `verify_failed` columns the study publishes (`plan:577`, `plan:628`)
would be wrong for that runtime.

#### 5.3.3 Runtime-specific stages, and the condition under which counts still join

The table frozen in §5.3 is **exhaustive for stages derived from an `E*` verdict**. A runtime may
declare additional stages that no `E*` verdict can produce. KAPSO declares one:
`boundary_violation` — `enforce_evaluation_integrity` rejected the measurement because the
candidate's committed evaluation tree differs from the registered head
(`kapso.selection.json` → `kapso_specific_stages`). It is a legal value of the trace schema's
`failure_stage` enum, but it is **not** a statement about `E*`.

A runtime-specific stage is admissible only under all three of these conditions, and the third is
the one that keeps counts joinable:

1. it is **declared** in the runtime's own `contract/selection/<runtime>.selection.json`, with the
   mechanism that produces it (KAPSO's does this);
2. it names a **runtime-side** event, not an `E*` verdict — a runtime must not emit a
   runtime-specific stage for a row where `E*` produced a verdict, and must not use it to absorb a
   row whose `E*` verdict has a frozen stage;
3. **no other runtime uses that stage with a different meaning** — *and, where a name is reused, the
   row is basis-separated so the counts still join.*

> **Amendment to an earlier revision of this condition.** It originally read "every stage name means
> the same thing in every runtime that can emit it", with no escape. That was too strong for the
> closed enum, and Loreley's declaration is the counter-example: it uses the shared name `timeout`
> for **two** causes — (a) the frozen table's own entry, `E*` exit 3 with
> `failure_kind = runtime_budget_exceeded`, and (b) a runtime-level timeout with **no `E*` verdict at
> all**, where the plugin process is killed by `Evaluator._execute_with_timeout` and
> `evaluate_outcome` synthesises a failure (`loreley.selection.json` → `loreley_specific_stages`).
> Renaming case (b) is not possible — the enum is closed and `timeout` is the correct stratum name —
> and forbidding the reuse would forbid a truthful report. What actually protects joinability is the
> **basis**, not the stage name: a row staged by a runtime-side rule is labelled and counted
> separately (§5.3.4), so a reader comparing `timeout` counters across runtimes compares
> frozen-map rows only. The condition is therefore amended to what it was really protecting: *a
> stage name may carry a second meaning only when every row carrying that second meaning is
> basis-labelled and counted outside the shared counter.*

Consequences, binding on how the counts may be presented:

* The cross-runtime `FailureStage` comparison is over **shared-map stages only**. Runtime-specific
  stages are reported **separately**, as their own labelled counters, so they can never be read as a
  difference in how two runtimes consumed `E*`.
* `boundary_violation` is currently KAPSO-only. That is a fact about the code, not a guarantee: if a
  second runtime ever gains the ability to emit it, either the two meanings are shown to be
  identical or the stage must be namespaced (for example `kapso/boundary_violation`, which would
  require a trace-schema change, since the frozen enum is closed). Until then a study-level table
  must label it KAPSO-only rather than placing it in a column that reads as comparable.
* A row carrying a runtime-specific stage carries **no `E*`-comparable measurement**, so it can
  never be counted as a passing A0.1 row: it is reported as a runtime-side integrity finding, with
  the row's `failure_stage` visible so the reader can see it was not an `E*` verdict.

#### 5.3.4 Rows the frozen table cannot express: staging a runtime-side failure

Raised by the EvE workstream as an explicit finding and answered here, because the same shape occurs
in at least three of the four runtimes and the answer must not be invented per adapter.

**The table is total over `E*` verdicts but not over rows.** A row can fail while `E*`'s verdict is
`ok`: the runtime's attempt can disagree with `E*`, or produce no measurement at all. The frozen
table's entry for an `ok` verdict is `none`, so applying it literally would stage a genuine runtime
failure as success. `none` is the study's success counter — the one stage that must never be
assigned to a row that failed.

**Rule 1 — `none` on a failed row is forbidden.** `failure_stage = none` is admissible **iff** the
runtime produced a fresh measurement that reproduced `E*` within `epsilon` for that candidate. A row
where the runtime failed is never staged `none`, whatever `E*` said; a row where the runtime
succeeded is never staged anything else.

**Rule 2 — staging.** `<runtime>` is the runtime, `E*`'s verdict is the reference:

| case | stage | why that stage |
|---|---|---|
| `E*` `ok`, runtime produced a measurement that disagrees beyond `epsilon` | **`mechanism_mismatch`** | the runtime's *evaluation mechanism* disagreed with the frozen evaluator — the protocol's own counted stage for it (`plan:577`), and not a name the frozen map already uses |
| `E*` `ok`, runtime produced **no** measurement (synthesised failure, lane error) | **`evaluator_failed`** | the evaluator stratum produced nothing; this is a statement about the stratum, not about `E*` |
| **no `E*` verdict at all** (runtime-level timeout, integrity rejection) | the runtime's declared stage: `timeout` (Loreley (b)), `boundary_violation` (KAPSO) | the stratum is the runtime's own; §5.3.3 applies |
| the row was **never attempted** (declared seam, unavailable lane) | *none — do not emit a `C*` row* | there is no stratum to name; the candidate is BLOCKED and reported outside the counts, with the seam cited as `path:line` |

**Rule 3 — labelling.** Every such row carries a basis label distinct from
`frozen_table_e_star_verdict`, naming the runtime-side event (EvE's
`adapter_extension_runtime_failed_a_measurable_candidate` is compliant), and a `failure_detail`
naming it on the trace. On the trace the machine-checkable discriminator is
`evaluator_evidence.status != "ok"` on that row's score event — `synthesized_failure`,
`manifest_mismatch`, `timeout`, `not_run` — with `detail` set, which the validator already requires.
**Do not add a new trace field for the basis:** the schema rejects unknown top-level fields (an event
carrying one fails validation), so the basis belongs in the runtime's report plus `failure_detail`,
or in `evaluator_evidence`.

**Rule 4 — can such a row still pass A0.1 for that candidate? No.** A0.1's formula,
`E_r(c; theta_E) = E*(c; theta_E) ± epsilon`, requires `E_r(c)` to exist. Concretely:

* a **disagreeing measurement** is an ordinary A0.1 failure of the number — the row is a *fail*;
* **no measurement** means `E_r(c)` does not exist, so the row is **not measured**: it is not a pass
  and must not be counted as one. Counting it as a pass would compare `E*` with `E*` — the adapter's
  own reference invocation — which is circular, and would let a runtime pass A0.1 with its
  evaluation lane never having run;
* a row **never attempted** is **BLOCKED**, also not a pass.

**Rule 5 — the consequence for `A0.1_r`.** `A0.1_r` is reported as `pass / fail / not-measured` per
candidate, never as a bare boolean:

* **FAIL** if any candidate is a *fail* (a number disagreement, or no measurement where the lane was
  exercised) — a runtime that cannot measure a measurable candidate has not demonstrated A0.1;
* **not established (BLOCKED)** if any candidate is not-measured because a declared lane was never
  driven; the study's own method rule applies, and the row must be marked UNVERIFIED rather than
  quietly passed;
* **PASS** requires all 14 candidates measured and agreeing.

The published row reads `passed / measured / total` with the not-measured candidates named — e.g.
`13/14, 1 not measured (c07)` — never `14/14`.

**Rule 6 — joining the counts.** The shared `FailureStage` counter must contain **only** rows staged
by the frozen table; extension rows are removed from it and reported under their own labelled
counter. So the partition over the 14 units is

```
frozen_map_count  +  extension_count  +  not_attempted_count  =  14
```

and `frozen_map_count` must equal the frozen counts **restricted to the candidates it covers**. The
check that makes this verifiable rather than arithmetic: list the extension rows by `candidate_id`,
so the reader can see exactly which frozen expectation each one removes. If `extension_count == 0`
and nothing is BLOCKED, `frozen_map_count` must equal the frozen counts exactly; only then may a
runtime claim its counts join with the other runtimes'. A difference that is *reported* is a finding;
a difference that is absorbed into the shared counter or re-mapped away is a defect.

> **Owed by EvE, 0 rows affected today.** `a01.failure_stage_counts()` currently counts every
> candidate, so an extension row would land inside the shared counter and make it non-comparable —
> exactly what Rule 6 forbids. With `failure_stage_extension.count == 0` in the current run this
> changes nothing numerically, but the counter must be computed over basis
> `frozen_table_e_star_verdict` rows before one fires. EvE must also declare its extension in its
> declaration file: its `eve.selection.json` has **no `eve_specific_stages` block**, so the rule is
> currently documented only in its report. KAPSO (`kapso_specific_stages`) and Loreley
> (`loreley_specific_stages`) already declare theirs.

**Rule 7 — this is A0-wide, not EvE-specific.** Every runtime must declare its extension cases and
basis labels in its frozen declaration, including the empty set (SimpleLoop's declaration has no
extension block and should say so explicitly rather than leave the absence ambiguous). The three
live instances are EvE's runtime-failed-a-measurable-candidate, Loreley's no-verdict `timeout` and
no-readable-Outcome `resolve_failed`, and KAPSO's integrity rejection `boundary_violation`.

### 5.4 KAPSO's evaluator identity is enforced out of band

`plan:532-539` writes the manifest invariant as `(evaluator, fidelity, fraction, seed)`.
**There is no evaluator field in KAPSO's manifest.** `parse_manifest_line`
(`evaluation_maintainer/maintainer.py:64-83`) requires exactly `fidelity, fraction, seed, items,
total_items` (plus `score`), and the accepted check
(`registered_evaluation.py:87-99`) compares a **triple**: `fidelity`, `fraction` (within `1e-9`),
`seed`. Evaluator identity is enforced by two other mechanisms: the registered head's
`manifest_fingerprint` over `kapso_evaluation/` (`maintainer.py:216-218`,
`evaluation_integrity.py:112-119`), and `sync_registered_evaluation` overwriting the branch's
evaluation tree from the registered head before every frame run
(`registered_evaluation.py:193-200`). The adapter must assert **both** the triple and the
fingerprint; see `a0/acceptance/DERIVATIONS.md` §2.3. A test written from the protocol's wording
would look for a field that does not exist.

---

## 6. Emitting the three traces

File layout, field semantics and validation are in `trace_schema.md`. Adapter obligations. The
obligations below are numbered for citation: **`§6.1` … `§6.6` are the obligations, in order**, and
the A0.2 table is `§6.7`. (Earlier revisions numbered the obligations as a list and called the A0.2
table `§6.1`; nothing downstream depends on that, and existing citations of "§6.3" already mean
obligation 3.)

### 6.1 One file per kind, and the three must partition the run

Write `<run_dir>/traces/<runtime>.<run_id>.{score,selection,resource}.jsonl`, one JSON object per
line, valid against `trace_schema.json`. The three files **partition** the run: a per-kind file
carries only events of its own `trace` kind. (EvE's first run violates this — 14 score events are
copied into the selection file, giving duplicate `event_id`s once the run is merged; see
`contract/README.md` §8.)

### 6.2 The run directory

`<run_dir>` must be **outside every candidate worktree** and outside any directory a
`git checkout` can restore (KAPSO's `kapso_evaluation/` is exactly such a directory — `plan:547`).

### 6.3 The validation unit is the run, not the file

`selection.source_score_event_id` points at a score event, and score events live in a different
per-kind file, so a per-kind file cannot resolve it. Validate with:

   ```bash
   python trace_validate.py validate-run --run-dir <run_dir>          # every run under it
   python trace_validate.py validate --trace <run_dir>/traces/<runtime>.<run_id>.all.jsonl
   ```

`validate-run` takes each run as one stream — using the merged
`<runtime>.<run_id>.all.jsonl` when the adapter wrote it, and otherwise composing the same stream
from the three per-kind files in `event_seq` order — and additionally checks each per-kind file
for event-level validity and kind purity. Adapters **should** write the merged file (SimpleLoop,
KAPSO and Loreley do); it is required whenever a selection event carries
`source_score_event_id`. An adapter that exits 0 with an invalid trace is non-conformant.

**The stage comparison is part of what "the run validates" means.** Because the unit of validation
is the run, a validator reading a run has both `E*`'s verdict for a candidate and the runtime's
emitted `failure_stage` for the same candidate in the same stream, and **must compare them**:
`status` and `failure.kind` from the evaluator side against the `failure_stage` the adapter
derived with the frozen table (§5.3, §4.5). A run in which a non-`ok` row's stage disagrees with
the stage the frozen table assigns to `E*`'s `failure.kind` is **not** a valid run, however
truthfully the `status` and the score were reported. This is the trace-side statement of the §4.5
requirement: A0.1 conformance is owed on the failure stage as well as the status and the score, so
a checker that compares only `status` is checking less than the contract requires and can return a
false PASS.

### 6.4 Emit a selection event for every decision

Emit a `selection` event for **every** decision the runtime actually makes, including ones that
choose nothing (`chosen_candidate_id: null`) — the A0.2 checks are assertions about decisions, and
an unrecorded decision cannot be checked.

### 6.5 Emit a resource event at least once per iteration

With `T_wall`, `N_evaluatorCalls` and `concurrency` filled from the adapter's own counters, not
from the runtime's self-report (`plan:612`: the three systems' self-reported accounting is not
comparable, and Loreley's is the only one that today separates a real run from a cache reuse).

### 6.6 Record the failure stage honestly

Record `failure_stage` at the stratum where the attempt stopped (`plan:628`) and `failure_detail`
for every non-`none` stage. "Honestly" is load-bearing: the stage must be the one the frozen table
(§5.3) assigns to `E*`'s own `failure.kind` for that candidate, not the one that reads best, and
not a re-mapping invented at report time to make a mismatch disappear (§4.5).

### 6.7 A0.2 checks per system

The adapter's `--run-dir` must contain the artifacts the A0.2 checks read, and the `check_point`
field on `selection` events names the check:

| Runtime | Frozen configuration condition | Check the adapter must support |
|---|---|---|
| KAPSO | `parent_policy = "best"` (default, `strategy.py:198, 212`) | with `E(c_1) > E(c_2)`, assert the next round's parent branch is `c_1` and the best-experiment branch returns `c_1` |
| EvE | `working_optimizer`: `RankSoftmaxSampler(temperature=1.0, replacement_mode=auto)`; `solver_examples`: `RankExponentialSumSampler(features.score weight 1.0, temperature=1.0, replacement_mode=no_replacement, n=4)`; `solver_prefill`: score-independent `UniformSampler` | a frequency test over many draws, with the expectation derived **per class** (`P(c_1) = 1/(1+e^{-1}) ≈ 0.731` holds only for `RankSoftmaxSampler`, `k=2`, `T=1`, one draw). The prefill segment may not be used and one run is not enough |
| Loreley | the two candidates share descriptor/measures (same cell); single objective `composite_score` (`direction="max"`), `epsilon=1e-9`, `admission_policy="pareto"`, and a score gap `|Δ| > epsilon` | assert `c_1` replaces `c_2` inside the cell and the report points at `c_1`; across cells, a higher score must **not** evict. **Under this single-objective configuration the protocol's "no global-argmax guarantee" does not hold**: every cell front has exactly one member, so the archive is the per-cell argmax and the report is the argmax over everything evaluated (see §5 of the findings in `SPEC.md`) |
| SimpleLoop | none (`plan:591-603`: `c_{t+1} = Agent(c_t, H_t)`, `c*_t = argmax_{i<=t} E(c_i)`, `parent_{t+1} = c*_t`; no archive/QD, no evolutionary harness, no multi-island, no learned operator selection, no external retrieval in A1, no undeclared special prompt). Tie-break and null-fold frozen in §5.3 | assert the next parent is the argmax-scoring candidate seen so far; on equal scalars, the next parent is the candidate with the byte-wise smallest `candidate_id` (`C*`'s tie pair `c01_good_hex`/`c03_mirror` is the test case, and the assertion must hold in both proposal orders); a candidate whose `E*` verdict is `invalid`/`error` is never parent |

---

## 7. Closure-probe interface

> 必须用探测证明所选 runtime 没有自主外部获取，而不是只在配置里关

`plan:569`. Configuration alone is not evidence. The probe is a separate, repeatable command:

```bash
uv run --project <adapter_dir> python -m a0_adapter closure-probe \
  --runtime <r> --run-dir <dir> --out <closure.json>
```

Required behaviour:

1. Run one short, otherwise ordinary iteration with network egress instrumented — at minimum an
   HTTP/DNS sentinel reachable only from outside the sandbox, plus a check of the runtime's own
   network configuration.
2. Emit `closure.json`:

   ```json
   {"schema": "a0.closureprobe/v1", "runtime": "kapso", "probe_id": "...",
    "configured": {"allow_network": false, "web_search": "disabled", "sandbox_mode": "workspace-write"},
    "observed": {"egress_attempts": 0, "dns_lookups": 0, "sentinel_hits": 0, "evidence": "..."},
    "verdict": "closed" | "egress_detected" | "inconclusive",
    "mechanism": "config | external_network_isolation | code_change"}
   ```

3. Exit 0 iff `verdict == "closed"`. `egress_detected` → exit 6 (adapter `run` must also exit 6
   if a probe during the run observes egress). `inconclusive` must be treated as not-closed.

Per-system expectations, which the probe's `mechanism` field must name truthfully. These are
**corrected against the source**; `SPEC.md` §5 records the citations and where the protocol's own
wording is inaccurate:

* **EvE** — `allow_network` **does** exist (`providers/agent/config.py:26,31,86`,
  `providers/agent/python_runtime.py:20,27,332`, `runtime/driver.py:381-386`), so `codex_tmux`
  with `sandbox_mode: workspace-write` + `allow_network: false` + `web_search: disabled` is a
  real closure. But the **shipped full-run driver is `codex_exec`**, which has no sandbox
  parameter at all and hardcodes `--dangerously-bypass-approvals-and-sandbox`
  (`providers/agent/drivers/codex_exec.py:419-436`); feeding it `sandbox_mode: workspace-write`
  is silently ignored. A config-only closure verdict on the `codex_exec` path is a **false
  green** — the probe must observe egress, and `mechanism` must say `codex_tmux` or
  `external_network_isolation`, never "config" on the default driver.
* **KAPSO** — the front doors (ideation `web_search`, `implementation_web`, the gates,
  `knowledge_search`) can be configured off. The Bash side door has a **lane-level sandbox
  parameter, but it defaults to the most permissive mode**:
  `agent_specific.sandbox` → `codex_agent.py:117` (`default "danger-full-access"`), passed as
  `--sandbox <mode>` (`:192-193`) and defaulting `web_search` on (`:118`). The claude lane
  (`claude_code_agent.py:1182` `--dangerously-skip-permissions`) has no equivalent parameter.
  So KAPSO needs the parameter set explicitly *and*, for the claude lane, external isolation or a
  code change.
* **Loreley** — the default path has no network switch, so it needs isolation or a codex backend.
  Codex CLI's `workspace-write` default `network_access: false` is the one hard CLI-level
  guarantee, but it only applies where the sandbox mode actually reaches the CLI.

---

## 8. What an adapter must never do

* Never re-derive the score from the runtime's own logs or summary fields (D16, false-green
  traps — `plan:534-552`).
* Never change `F_r`, `theta_E`, `epsilon` or the `E*` wiring mid-run; a change produces a new
  `EID*` and a new run (`plan:509`).
* Never write counters or logs into a candidate worktree (`plan:547`).
* Never rely on cwd or `PATH` (hard constraint 1, `plan:544`).
* Never let `E*` scalarize: scalarization is `F_r`'s job (hard constraint 3, `plan:549`).
* Never skip a candidate or a runtime silently; failures go into the traces as
  `failure_stage` values, not into a missing row.
