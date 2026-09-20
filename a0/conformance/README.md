# `a0/conformance` — A0.1 cross-adapter conformance runner

Answers A0.1 for the whole study: *if every runtime adapter is pointed at the same frozen
evaluator `E*` and the same fixed candidate set `C*`, does it produce the same numbers — and the
same verdicts for the candidates that have no number?*

Protocol: `plan:513-519` (the acceptance formula; `EID_r` derived from `EID*`; `theta_E` identical
across wrappers), `plan:490` (A0 is a candidate screen: `|R_1| >= 1` to continue), `plan:528`
(`F_r(E*) = scalar(E*)` in round one), `plan:551-552` (the two false-green traps). Frozen
coordinates come from the binding decisions in `a0/tasks/circle-packing/README.md` and
`EID_INPUTS.json`.

## Files

| file | what it is |
|---|---|
| `conformance.py` | the runner: `reference`, `run`, `show`. Standard library only |
| `report.json` | **the deliverable**: per-runtime A0.1 verdict, the runtime × candidate table, findings, EID\* checks, integrity, and the per-runtime handoff block |
| `report.md` | the same report as a readable table |
| `reference.json` | the runner's own fresh `E*` sweep over `C*`, cross-checked against `E_STAR.json` |
| `selftest.py` | fault injection: drives 20 fixture adapters (19 injected faults + the honest control) and asserts the verdict each must get, plus the integrity-abort path |
| `selftest_report.json` | the self-test result (fixture, injected fault, expected vs actual verdict) |
| `selftest_runner_report.json` / `.md` | the full runner report of the self-test run |
| `fixtures/adapters/reference_adapter.py` | an honest fixture: really executes `E*` on all 14 members of `C*`. The template an adapter should follow. **Not** a runtime |
| `fixtures/adapters/deviant.py` | one named fault per `--mode` |
| `adapters.json` | optional entry-point registry, for an adapter layout discovery does not recognise |
| `out/` | raw adapter stdout/stderr/exit codes, the `E*` outcome files, per-run dirs (pruned to the latest per runtime) |

## Running it

```bash
cd /home/ebt/rsi-dev/a0/conformance
python3 conformance.py reference                                          # fresh E* sweep vs the frozen table
python3 conformance.py run                                                # all four runtimes + controls
python3 conformance.py run --runtimes kapso --out report.kapso.json       # one runtime (subset runs are auto-redirected away from report.json)
python3 conformance.py run --eid-document proposed --out report.proposed.json   # old EID* document
python3 selftest.py                                                       # prove the checker rejects each fault
```

Exit codes: `0` = all four runtimes PASS; `2` = no FAIL but at least one PENDING/BLOCKED;
`3` = at least one FAIL; `4` = candidate-set integrity abort; `10` = runner bug.

## What the runner does

1. **Integrity first** (`adapter_contract.md` §2.2). Recomputes `sha256(solution.py)` for all 14
   members of `C*` against `manifest.json` and **aborts with exit 4 before evaluating anything**
   on a mismatch. Verified by execution: `selftest.py` builds a tampered manifest off to the side,
   the runner exits 4 and names `c04_near_tie`.
2. **`E*` reference sweep.** Runs the frozen invocation (`.venv/bin/python e_star.py evaluate
   --candidate C_STAR/<id> --seed 1337 --fidelity full --fraction 1.0 --n 26 --runs 5
   --runtime-budget-ms 250.0 --timeout-s 120.0 --out … --state-dir …`) over every member and
   checks the result against the frozen table `E_STAR.json`: exit code, status, `canonical_digest`,
   objective **bit-for-bit**, and `failure.kind`. It also digests the whole `C*` tree before and
   after, so "`E*` never writes inside a candidate worktree" is measured rather than asserted.
3. **EID\* checks.** `evalcontract.py recompute` (filesystem-free), `evalcontract.py verify`
   (`--base a0/`), and a check that every EID document on disk carries the binding `EID*`.
4. **Drives each adapter** through the frozen CLI, then compares the adapter's numbers against
   `E_STAR.json` **itself**. The adapter's own verdict is recorded (`adapter_declared_verdict`) but
   is never the runner's verdict — an adapter that reports "A0.1 ok" for a crash recorded as `0.0`
   fails on the comparison. For a candidate `E*` did not accept, the compared surface is the
   **verdict and `failure.kind`** (`adapter_contract.md` §4.3.5), so a runtime cannot pass by
   repeating `invalid`/`error` truthfully while lying about *why* it failed.
5. **Per-runtime PASS / FAIL / PENDING / BLOCKED**, each runtime in its own try/except and its own
   subprocess: one runtime's failure can never abort another's run (`plan:490`). A runtime that was
   never driven is `PENDING`, never "passing".

### The adapter invocation (exactly what the runner sends)

```bash
<adapter cmd> conformance \
  --runtime <r> \
  --candidate-set /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json \
  --eid /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json \
  --theta seed=1337,fidelity=full,fraction=1.0,n=26,runs=5,runtime_budget_ms=250.0,timeout_s=120.0 \
  --epsilon 1e-09 \
  --out /home/ebt/rsi-dev/a0/conformance/out/adapters/<r>.conformance.json
```

`--eid` is the **canonical, contract-owned** document `a0/contract/out/plumbing.EID.json`
(same `EID* = 664115e0…`, and the only document `evalcontract.py verify --spec
a0/contract/plumbing.contract.json` resolves without a path override). `--eid-document proposed`
selects the task-side copy `a0/tasks/circle-packing/plumbing.EID.proposed.json` instead — the
pre-repoint default, kept for comparability with older reports; a path is accepted too. The
runner records which document it handed over (`frozen.eid_document_name`,
`frozen.eid_document_sha256`, and per runtime `runtimes.<r>.eid_document_supplied`) and fails the
`EID-document-as-requested` check if the requested document could not be used.

If that produces no usable document, the runner falls back to `<adapter cmd> run …` (the §3 `run`
form, with `--fr a0/contract/fr/scalar.json`,
`--budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1`, `--traces score,selection,resource`)
and reads `outcome.fields.sum_radii` plus `evaluator_evidence` from the score trace. That path is
**weaker and cannot pass A0.1 on its own**: a score trace carries neither `eid_r`, nor `theta_E`,
nor `E*`'s `ok|invalid|error` verdict, so the identity half of A0.1 stays unestablished
(`plan:517-519`). The report says so (`evidence_source`, `fallback`).

`<adapter cmd>` is discovered (override with `--adapter <r>="<cmd>"`, or an entry in
`adapters.json`):

1. `<adapter_dir>/adapter.json` (or `config/adapter.json`) → `{"cmd": [...], "pythonpath": "..."}`
   — the recommended, unambiguous way
2. `<adapter_dir>/{a0_adapter,adapter,main,cli}.py`, or an executable in `<adapter_dir>/bin/`
3. a package `a0_adapter` or `adapter` (with `__init__.py`) under `<adapter_dir>` or
   `<adapter_dir>/src`, using `__main__.py` → `python -m <pkg>`, else `cli.py`/`main.py` →
   `python -m <pkg>.<mod>`
4. otherwise `python -m a0_adapter` with the adapter's own venv, reported as a *guess*

The runner launches with `cwd = <adapter_dir>` and `<pythonpath or adapter_dir>` prepended to
`PYTHONPATH` — mirroring `uv run --project <adapter_dir>` — and passes only absolute paths, so the
adapter still must not depend on cwd or PATH (`plan:544`). Every launch, exit code and stderr tail
is in `report.json` under `runtimes.<r>.conformance_invocation` / `.adapter`; the raw bytes are in
`out/adapters/`. When discovery finds nothing runnable it reports `PENDING` and names the entry
points it looked for.

## What the adapter must report

The frozen shape is `a0.adapter.conformance/v1`; the README of each adapter should say what it
emits. The reader is deliberately alias-tolerant, because the two adapters that exist now each
published their own spelling, and a partly finished adapter must stay *measurable* rather than be
silently skipped. Accepted today:

* rows at the top level under `candidates` / `results`, **or** inside a section object
  (`a01`, `conformance`, …) — `adapter_rows_section` records which;
* the runtime-side number as `substrate.scalar` (simpleloop), `runtime_scalar` (eve), or
  `objective.value` / `objective_value` / `e_r` / `value` / `score` / `scalar`;
* the runtime-side verdict as `substrate.status` / `runtime_status` / `status`;
* `theta_E` or `theta_e`, with `n`/`runs`/… allowed under `extra`;
* evidence as `evaluator_evidence`, or as the flat `runtime_evidence_status` +
  `runtime_evidence_detail` pair;
* the candidate's identity as `substrate.candidate_source_sha256` / `solution_sha256` /
  `score.e_star_candidate_source_sha256`, and `substrate.canonical_digest` /
  `score.e_star_canonical_digest`.

Aliases never relax the comparison: the numbers are still checked against `E_STAR.json`, and the
adapter's own verdict is never used as the runner's.

```jsonc
{
  "schema": "a0.adapter.conformance/v1",
  "runtime": "eve",
  "eid_star": "<64-hex>",                      // EID* verbatim (plan:509)
  "eid_r": {                                   // the EID_r -> EID* mapping (plan:517)
    "value": "<64-hex>",
    "native_scheme": "none" | "manifest_fingerprint" | "evaluator_name_version_campaign_program_hash",
    "mapping_mode": "native" | "adapter_declared_injection",
    "derives_from_eid_star": "<64-hex>",
    "declaration": "how the identity is pinned, in words",
    "recomputable": true,
    "recompute_cmd": ["...", "..."]            // preferred: the runner executes it and compares.
  },                                           // OR "derivation": {"domain": "...", "payload_canonical": "..."}
  "theta_e": {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
              "runtime_budget_ms": 250.0, "timeout_s": 120.0,
              "defaults_applied": {}},         // required for any null parameter (plan:518)
  "epsilon": 1e-09,
  "primary_field": "sum_radii",
  "fr": {"name": "F_r = scalar(E*)", "spec_hash": "1fa6f941…"},   // a0/contract/fr/scalar.json
  "candidates": [                              // one row per member of C*, no skipping
    {
      "candidate_id": "c07_single",            // exactly the manifest's join key
      "source_sha256": "…",
      "canonical_digest": "…",
      "status": "ok" | "invalid" | "error",    // E*'s verdict, not the runtime's own
      "objective": {"name": "sum_radii", "value": null, "direction": "max"},
      "exit_code": 2,
      "failure_kind": "invalid_configuration",
      "evaluator_evidence": {"status": "ok", "detail": "fresh E* subprocess run"},
      "theta_e_attempt": {"evaluator": "E*", "fidelity": "full", "fraction": 1.0, "seed": 1337,
                          "granted_class": "full", "commanded_class": "full"}
    }
  ],
  "traces": {"score": "…", "selection": "…", "resource": "…"},
  "failure_stage_counts": {"…": 0}
}
```

**If your `eid_r` carries a `recompute_cmd` (or a canonical recipe), the runner executes it and the
check becomes `executed` instead of the weaker `declared_prose`.** Both existing adapters use
`declared_prose`, which the report marks as such: `recomputable: true` there is the adapter's
declaration, backed by a named recipe, not by an executed check.

## Verdicts and findings

Per candidate:

| condition | verdict |
|---|---|
| `E*` has a number and \|`E_r − E*`\| ≤ `epsilon` | `MATCH` |
| `E*` has no number and the adapter reports the same non-ok verdict, no number, **and the same `failure.kind`** | `MATCH_VERDICT` |
| `E*` has no number, the runtime's lane returned a **declared** synthetic failure (EvE's `failure_score(0.0)`), and the row is not presented as a match | `SYNTHETIC_DECLARED` — acceptable, but its `0.0` is never a measurement |
| \|Δ\| > epsilon | `MISMATCH_VALUE` |
| a number where `E*` reports `null` | `FALSE_GREEN_SYNTHETIC_ZERO` (0.0) or `MISMATCH_NULL` |
| reported `canonical_digest` / `source_sha256` differs from `E*`'s | `MISMATCH_DIGEST` |
| truthful `status` but a different `failure.kind` | `MISMATCH_FAILURE_KIND` (`E*` verdict and kind are one surface: `adapter_contract.md` §4.3.5) |
| a non-ok candidate with **no** `failure.kind` declared at all | `UNDECLARED_FAILURE_KIND` — the surface §4.3.5 compares is absent, so the row cannot "agree" |
| the row declares a `failure_stage` that is not the one the frozen §5.3 table maps `E*`'s kind to | `MISMATCH_FAILURE_STAGE` |
| no row for a member of `C*` | `MISSING` → coverage FAIL |

Only `MATCH`, `MATCH_VERDICT` and `SYNTHETIC_DECLARED` count as agreeing. A runtime is `PASS`
only when every candidate agrees **and** every check passes.

Findings (`plan:551-552`; `fatal: false` findings inform, they do not fail a runtime):

| finding | fatal | trigger |
|---|---|---|
| `TRAP-SYNTHETIC-DECLARED` | no | the EvE trap was hit, detected and declared (this is the *good* outcome: the 0.0 is distinguishable from `c14`'s genuine near-zero) |
| `FG-EVE-SYNTH` | yes | `synthesized_failure` reported on a row that still claims a match, or where `E*` has a real number |
| `FG-EVE-ZERO` | yes | a `0.0` (or a value within epsilon of it) where `E*` returned `null`, undeclared |
| `FG-LORELEY-CACHE` | yes | `cache_hit` (must name `cached_from_run_id`) — a reused number is not evidence that `E*` ran |
| `FG-LORELEY-TIMEOUT` | yes | `timeout` — a timeout-synthesised failure |
| `FG-LORELEY-TRUNCATED`, `FG-LORELEY-CAP` | yes | `truncated_metrics`, `metrics_truncated`, `metrics_dropped > 0` or `metrics_count > 64` |
| `FG-MANIFEST-TRIPLE` | yes | `granted_class != commanded_class` (`plan:532-539`, KAPSO D16) |
| `FG-ATTEMPT-THETA-DRIFT` | yes | the per-attempt `(fidelity, fraction, seed)` differs from the frozen `theta_E` (`plan:518`) |
| `FG-FAILURE-KIND` | yes | a non-ok candidate whose declared `failure.kind` is not `E*`'s — a truthful `status` with a lying `why` is a false PASS on the staging half of A0.1 (audit R1) |
| `FG-FAILURE-KIND-UNDECLARED` | yes | a non-ok candidate that declares **no** `failure.kind`, so the (verdict, `failure.kind`) surface `adapter_contract.md` §4.3.5 compares is absent — passing vacuously was the hole the auditor found |
| `FG-FAILURE-STAGE` | yes | a declared `failure_stage` that contradicts the frozen §5.3 mapping of `E*`'s kind |

Runtime checks: `EID-star-verbatim`, `EID-r-derives-from-EID-star`, `EID-r-declaration-present`,
`EID-r-recomputes` (+ `recompute_mode`: `executed` / `verbatim` / `declared_prose` / `absent`),
`theta-E-identical`, `E-star-manifest-echo`, `F-r-frozen`, `candidate-coverage`,
`E-r-equals-E-star`, `E-r-failure-kind`, `evidence-fresh-or-declared`, `no-duplicate-candidates`.

Two checks deserve a note:

* **`E-star-manifest-echo`** — many adapters leave `E*`'s own `E_STAR_MANIFEST` line in their
  evidence (e.g. inside a step's error text). The runner parses it out — through however many JSON
  escaping layers — and checks the echoed `evaluator_source_sha256` against `E_STAR.json`'s, the
  echoed `canonical_digest` against the per-candidate reference, and the echoed
  `(seed, fidelity, fraction)` against `theta_E`. EvE's report carries 56 such echoes. KAPSO does
  not keep the line, but publishes the same facts as fields (`registered_channel.manifest`:
  `e_star_canonical_digest`, `e_star_evaluator_source_sha256`, `seed`/`fidelity`/`fraction`), which
  the runner reads as an echo of the `fields` form (`echo_forms` records which form was used).
  Either way this is the closest thing to proof that the *frozen evaluator bytes* ran inside the
  runtime.
* **`E-r-failure-kind`** — for a candidate `E*` did not accept, the contract compares **verdict and
  `failure.kind`**, not just `status` (`adapter_contract.md` §4.3.5). The check reports how many
  non-ok candidates declared a kind at all (`kind_declared_for`), fails the runtime when a declared
  kind disagrees, and fails it too when a non-ok candidate declares **no** kind at all: a row
  without the field cannot "agree", and treating an omission as silence was the residual hole in
  this checker (`UNDECLARED_FAILURE_KIND`, `FG-FAILURE-KIND-UNDECLARED`). Each runtime also carries
  `failure_stage_accounting`: its declared `FailureStage` counts compared against the frozen §5.3
  map applied to `C*` — **recorded, never a verdict**, because the counts may describe a different
  run's units (`matches_frozen_map` is `null` unless the units total 14).
* **`theta-E-identical`** — if an adapter does not declare `theta_E` at all, the runner recovers
  the theta `E*` actually ran at from those echoes and says so, rather than claiming the adapter
  declared it. Several independent echoes that disagree with each other would fail the check: that
  is exactly KAPSO's D16 drift.

## Controls and self-test

`report.json` also carries `controls`: fixture adapters driven through exactly the same checker —
`control_honest` (really executes `E*` on all of `C*`; must PASS), `control_zero_on_error` and
`control_cache_hit` (the two named traps; must FAIL). If a control comes back wrong, the runtime
verdicts in the same report are not trustworthy.

`selftest.py` runs 20 fixtures (19 injected faults + the honest control) covering: an honest
adapter, a no-fault adapter, undeclared
synthetic zero, declared synthetic zero (must PASS), a mislabeled synthetic zero (must FAIL),
cache reuse, timeout synthesis, metric truncation, a value drift just above epsilon and just below,
the 1e-4 near-tie swap, a digest swap, partial coverage, a manifest-class mismatch, an attempt
theta drift, a stale `EID*`, an undeclared native `theta_E`, a truthful `status` with a lying
`failure.kind` (must FAIL — audit R1), a truthful kind with a mis-staged `failure_stage` (must
FAIL), and the honest fixture with `failure.kind` omitted altogether (must FAIL — the second half of
R1: a vacuous PASS is a hole) — plus the candidate-set integrity abort (exit 4). All of it is run
`python3 selftest.py` in ~10 s.

**Fixtures never write into the study tree.** A fixture is a test double: `fixture_common.
scratch_root()` sends its run artifacts to `$A0_FIXTURE_RUN_ROOT`, which `selftest.py` sets to a
system temp directory it removes afterwards (`--keep-fixture-runs` keeps it) and the runner sets for
its control rows to a temp directory it removes at exit. Before this, the honest fixture defaulted
its run dir to `a0/conformance/out/fixture-runs/`, so every selftest quietly added 30+ MB of
directories to the deliverable's artifact area (audit F6). Verify with
`python3 selftest.py` and `find a0/conformance -name fixture-runs` (empty), or
`--keep-fixture-runs` to inspect the paths the run used.

## Handoff fields for the study's final report

Per runtime, `report.json` → `runtimes.<r>` carries: `state` (A0.1), `checks`, `rows`
(runtime × candidate with `e_star_value`, `e_r_value`, `delta`, both statuses, both
`failure.kind`s, the E\* `failure_stage`, evidence and verdict), `false_green_findings`,
`synthetic_declared_candidates`, `eid_r` (via
`EID-r-derives-from-EID-star` and `EID-r-recomputes`), `traces` + `traces_source`,
`failure_stage_counts` (the adapter's own counters, or counted by the runner from its score trace),
`failure_stage_accounting` (those counts vs the frozen §5.3 map over `C*`),
`eid_document_supplied` (which `EID*` document this runtime was handed, with its digest),
`adapter_revision` (digest, per-file sha256 + mtime, newest mtime, and whether the source changed
while the runtime was being driven — so a stored verdict names the revision it covers),
`adapter_unverified_notes` (the adapter's own UNVERIFIED statement) and `adapter_seams` (the
injection seams it declares, with `path:line`). `report.md` prints the same as a "Handoff" block.

`a0_2` is deliberately `null`: A0.2 (selection semantics) is owned by the A0.2 workstream
(`a0/acceptance`), and this runner does not judge it. The study's `R_1` needs both.

## Current state

See `report.json` → `runtimes.<r>` for the verdict and `.rerun` for the exact command to re-run
one runtime alone. `PENDING` means **not driven** — neither passing nor failing — and always comes
with the reason and the raw stderr. `BLOCKED` is reserved for an adapter that declares itself
unable to run (e.g. a missing model backend).

`report.json` is a single shared artifact written by whatever `run` invocation ran last, so a
per-runtime re-run **must** use `--out report.<runtime>.json`; a bare `--runtimes <r>` no longer
writes `report.json` at all — it is redirected to `report.<r>.json` with a printed notice, because
three times during this study such a run silently replaced the four-runtime report that every other
workstream reads. `report.json` records the `EID*`
document it handed to each adapter (`frozen.eid_document_name` / `eid_document_sha256`,
`runtimes.<r>.eid_document_supplied`) so a reader can tell whether two reports measured the same
inputs. The adapters were still changing during the last full re-run; check each adapter's source
mtimes against `report.json` → `generated_at` before quoting a number.
