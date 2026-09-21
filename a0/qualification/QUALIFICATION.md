# Per-runtime qualification `Q_r` and the `Eligible(r)` predicate

Workstream: `a0/qualification/`. This directory answers two questions the external review raised
and one it only implied:

* **Point 8** — a single global `A0 PASS` is the wrong output. What is needed is a per-runtime
  qualification vector and an explicit eligibility predicate, so a partial result can never be
  diluted by siblings that passed.
* **Point 2** — `A0.1` for EvE is `PARTIAL — 5/14 measured` and must never read `PASS`.
* plus the distinction the review drew between `C_measure` and `C_adapt`.

Files:

| file | what it is |
|---|---|
| `qualification.json` | the deliverable: `Q_r` for all four runtimes, the declared predicate, its evaluation under two threshold vectors, the screen block and the UNPROVEN list |
| `eligibility.py` | the predicate `Eligible(r; T)`, with the rules and thresholds as data, plus a self-test (`--self-test`) |
| `build_qualification.py` | derives `Q_r` from existing evidence and writes the JSON; `--check` re-derives and diffs |
| `verify_qualification.py` | independent consistency check: re-reads the evidence and asserts the labels, the split, the predicate and the fixture set agree |
| `QUALIFICATION.md` | this document |

Nothing here re-runs an experiment: every component is read out of evidence another workstream
produced, and each one names the path it came from and whether it was **verified by running**,
**read from source**, or **inferred**.

## 1. The vector `Q_r`

`Q_r = (A0.1_measured, A0.1_adapted, A0.2_mechanism, A0.2_E2E, Closure)`, one row per runtime:

| runtime | A0.1 measured | A0.1 adapted | A0.2 mechanism | A0.2 E2E | Closure | `Eligible` @ `T_strict` | `Eligible` @ `T_literal` |
|---|---|---|---|---|---|---|---|
| SimpleLoop | `14/14` | `0/14` | PASS | COMPLETE | CLOSED | **eligible** | eligible |
| KAPSO | `14/14` | `0/14` | PASS (tie-break divergence declared) | COMPLETE | CONDITIONAL | not (`R5_closure`) | eligible |
| EvE | **`5/14`** | `9/14` | PASS (sampler only) | ATTEMPTED | CONDITIONAL | not (`R1`, `R4`, `R5`) | eligible |
| Loreley | `14/14` | `0/14` | PASS | PLANNING_ONLY | CONDITIONAL | not (`R4`, `R5`) | eligible |

`|Eligible| = 1` under `T_strict`, `4` under `T_literal`. Which vector the study should use is
**not decided here** — it is exactly external-review point 2 — so both are evaluated and reported.

### What each component means, and where it comes from

**`A0.1_measured` / `A0.1_adapted`** — `a0/conformance/report.json`,
`runtimes.<r>.qualification.a0_1`. A row is *measured* when the runtime's **own evaluator
interface** produced a fresh value/verdict that the runner compared against the frozen `E*` table;
it is *adapted* when the row agrees only because the **adapter supplied** semantics the interface
cannot represent (a declared synthetic failure, i.e. `SYNTHETIC_DECLARED`). The runner computes the
split, so the two numbers always sum to 14. EvE is `5/14` measured: its lane maps every evaluation
exception to `failure_score(0.0)` and cannot express `invalid`/`error`, so the 9 non-`ok` rows of
`C*` were reconstructed from side channels by the adapter.

**`A0.2_mechanism`** — does the runtime consume scores per its claimed selection semantics?
SimpleLoop `a0/runtimes/simpleloop/out/a02/a02_checks.json` (9/9, verdict `pass`); KAPSO
`a0/runtimes/kapso/runs/a0-01/a02/a02.json` (14/14 over 5 scenarios, driven through real KAPSO
selection code); EvE the sampled-selection frequency test, with the auditor's own 3000-draw
replication as the artifact read here (`a0/verify/out/eve_a02_replication.json`); Loreley
`a0/runtimes/loreley/out/a02.json` (7/7). All four are independently `ACCEPTED` by the audit as
claims C4.4 / C4.1 / C4.2 / C4.3. **This is the mechanism level, not end to end.** Each of the four
carries its scope next to the value; two carry caveats (KAPSO's tie-break, EvE's sampler-only
scope).

**`A0.2_E2E`** — a real model-lane round through the runtime's own loop. KAPSO
`runs/e2e-real/e2e_verification.json` → `verified_end_to_end` with a three-way score agreement;
SimpleLoop `out/cli-lane/codex-live{3,4}/run_meta.json` (agent-authored candidates that `E*` scored
2.6251746109048 and 2.5414213562373096, both above the best member of `C*`); EvE three real
codex-backed rounds that each reached iteration-complete but **never wrote back an agent-authored
`solution.py`** (every post-round solver still carries the prefill sha `18bacee4…`) → `ATTEMPTED`;
Loreley a real planning call (144.1 s) followed by a coding call that exceeded its 480 s budget →
`PLANNING_ONLY`.

**`Closure`** — the `a0/closure/*.json` record for the runtime, reconciled by
`a0/closure/closure.reconciliation.json`. `CLOSED` is used only where the record's top-level verdict
*and* study verdict are both closed (SimpleLoop's shipped codex `workspace-write` argv). Where a
mechanism is probe-proven closed but the *shipped default* is not, the value is `CONDITIONAL` and
the component lists which mechanisms are probe-proven and which are not — KAPSO (codex lane closed
by one `agent_specific` key; the default claude lane closed by nothing), EvE (`codex_tmux` closed;
the shipped `codex_exec` preset open), Loreley (codex backend closed; the default `kilo` path open
and not even runnable here).

## 2. The predicate `Eligible(r)`

Implemented in `eligibility.py`, declared in `qualification.json` → `predicate`.

```
Eligible(r; T) = R0 and R1 and R2 and R3 and R4 and R5

R0 coverage          measured + adapted == total  and  state in {PASS, PARTIAL}
R1 measure_floor     measured >= required_measured(T, total)
R2 adapted_declared  adapted == 0  or  adapted_all_declared_synthetic
R3 a0_2_mechanism    a0_2_mechanism.value == "PASS"
R4 a0_2_e2e          a0_2_e2e.value in T.e2e_allowed
R5 closure           closure.value in T.closure_allowed

required_measured(T, total) = T.measured_floor.value                if kind == "rows"
                            = ceil(T.measured_floor.value * total)  if kind == "fraction"
```

Every rule is a total function of `Q_r`; nothing is averaged, and there is no weighting. `R1` is
the rule the review's point 8 asks for: if a runtime could not measure `E*`'s outcome algebra on
some of `C*`, how many rows *were* measured is a threshold, not an afterthought.

Two threshold vectors are declared, both evaluated:

| vector | measured floor | `A0.2_E2E` must be | `Closure` must be | `|Eligible|` |
|---|---|---|---|---|
| `T_strict` (default) | all 14 rows (`fraction 1.0`) | `COMPLETE` | `CLOSED` | 1 — SimpleLoop |
| `T_literal` | ≥ 1 row (`rows 1`) | `COMPLETE`, `PLANNING_ONLY` or `ATTEMPTED` | `CLOSED` or `CONDITIONAL` | 4 — all |

`T_strict` is the default because it is the reading under which the study does not spend its own
stated caveats (`a0/STATUS.md` §3.3: mechanism-level verified vs end-to-end unverified; §5.5:
closure by topology rather than by configuration). `T_literal` is the reading under which the
study's existing wording is already sufficient. **Choosing between them is the open decision**; the
predicate is written so that changing it is a change of one data structure, not a rewrite.

### The screen is a different object

`|R_1| >= 1` (`plan:490`) is a **candidate screen** over runtimes: it answers *may the study
continue at all?* `R_1 = {r : A0.1_r ∧ A0.2_r}` and one surviving substrate is enough.
`Eligible(r)` answers a different question: *may **this** runtime's numbers be used in an A1
statistic?* The two are not the same object, and the screen can pass while not one runtime is
eligible — that is not a contradiction, it is the point.

Concretely, after the label correction:

```
verdicts.r_1_a0_1_only      = ['simpleloop', 'kapso', 'loreley']    (A0.1 fully measured)
verdicts.r_1_a0_1_partial   = ['eve']                                (A0.1 partial: excluded)
screen passes                = true                                  (3 >= 1)
|Eligible| @ T_strict        = 1                                     (simpleloop)
```

EvE is deliberately **not** in `r_1_a0_1_only`. Before this change all four runtimes were in that
list, which is precisely how a partial result gets diluted by its siblings.

## 3. `C_measure` vs `C_adapt`

* **`C_measure`** — can the *runtime's* evaluator interface faithfully represent `E*`'s outcome
  algebra, i.e. can it distinguish `ok` / `invalid` / `error` and carry the failure kind, so that a
  row is *measured*?
* **`C_adapt`** — can the *adapter* supply the semantics that interface cannot represent?

This is a **semantic gap in the runtime's interface**, not a statement about whether an adapter is
in the loop. All four runtimes run through an adapter; that is by construction and says nothing
about `C_measure`. A row that the adapter had to reconstruct is evidence for `C_adapt` and **never**
for `C_measure`, which is why the two are separate components of `Q_r` rather than one number.

EvE is the only runtime where the two diverge: its native lane returns `{"score": 0.0, "summary":
"evaluation failed"}` verbatim for any swallowed exception, so on 9 of the 14 members of `C*` there
is no native measurement at all, and the adapter restores the verdict from side channels
(`step_status`, the eval-log-root `error.txt`).

**Operational consequence for A1** (stated in `qualification.json` →
`c_measure_vs_c_adapt.a1_consequence`, and in `a0/conformance/README.md`): EvE's native numbers must
not be used in any statistic that needs to distinguish `invalid`/`error` from a genuine zero. On
those rows EvE's interface reports a synthetic `0.0`; `c14_near_zero` is a *genuine* `2.6e-05`, and
conflating the two is exactly the false green the trap was built to catch. Any A1 statistic over
EvE must either be restricted to the 5 measured rows or go through the adapter's side-channel
reconstruction — and in the latter case it is measuring the adapter, not EvE.

## 4. The conformance label correction (review point 2)

`a0/conformance/report.json` used to say:

```json
"verdicts": {"a0_1": {"simpleloop": "PASS", "kapso": "PASS", "eve": "PASS", "loreley": "PASS"},
             "n_pass": 4, "r_1_a0_1_only": ["simpleloop", "kapso", "eve", "loreley"]}
```

It now says:

```json
"verdicts": {
  "a0_1":           {"simpleloop": "PASS (14/14 measured)", "kapso": "PASS (14/14 measured)",
                     "eve": "PARTIAL (5/14 measured)", "loreley": "PASS (14/14 measured)"},
  "a0_1_state":     {"eve": "PARTIAL"},
  "a0_1_measured":  {"eve": 5},
  "a0_1_adapted":   {"eve": 9},
  "a0_1_qualification": {"eve": {"state": "PARTIAL", "measured": 5, "adapted": 9, "total": 14,
                                 "measured_candidates": ["c01_good_hex", ..., "c14_near_zero"],
                                 "adapted_candidates": ["c05_overlapping", ..., "c13_slow"],
                                 "c_measure": "...", "c_adapt": "..."}},
  "n_pass": 3, "n_partial": 1,
  "r_1_a0_1_only": ["simpleloop", "kapso", "loreley"],
  "r_1_a0_1_partial": ["eve"],
  "screen_vs_qualification": "..."
}
```

Fields that changed in `report.json` (everything else is byte-identical: `rows`, `checks`,
`false_green_findings`, `failure_stage_counts`, `adapter_revision` are all unchanged, and
`exit_code` stays 0):

| field | before | after |
|---|---|---|
| `runtimes.eve.state` | `PASS` | `PARTIAL` |
| `runtimes.<r>.qualification` (new) | — | `a0_1` split + label + `C_measure`/`C_adapt` framing |
| `verdicts.a0_1.<r>` | bare `PASS` | label carrying the measured split |
| `verdicts.a0_1_state` (new) | — | the enum: `PASS` / `PARTIAL` |
| `verdicts.a0_1_measured`, `a0_1_adapted` (new) | — | per-runtime integers |
| `verdicts.a0_1_qualification` (new) | — | the full split with candidate ids |
| `verdicts.n_partial` (new) | — | `1` |
| `verdicts.r_1_a0_1_only` | all four | three (EvE removed) |
| `verdicts.r_1_a0_1_partial` (new) | — | `["eve"]` |
| `verdicts.screen_vs_qualification` (new) | — | the screen-vs-predicate statement |
| `protocol.qualification` (new) | — | the PASS/PARTIAL/FAIL definition |
| `exit_code` | `0` | `0` (a partial runtime is a qualification, not a failure) |

`report.md` gained a `measured / 14` and an `adapted (declared, NOT measured)` column, prints the
label in the per-runtime heading and Handoff block, and prints the screen set and the partial set
separately.

The runner change is in `a0/conformance/conformance.py`: a new runtime state `PARTIAL`, the
`qualification` block computed in `evaluate_runtime`, the label helper `a0_1_label`, and the
embeddings in `verdicts` and `write_table`. A row is *adapted* iff it is accepted and its
`evaluator_evidence_status` is non-fresh (in practice `SYNTHETIC_DECLARED`); `PARTIAL` is set only
after all FAIL branches, so a runtime with a failed check or an incomplete coverage is `FAIL`,
never `PARTIAL`.

### Self-test

`python3 a0/conformance/selftest.py` still runs **20 fixtures** (19 injected faults + the honest
control) plus the candidate-set integrity abort. **19 of 20 behave exactly as before.** The one
that changed is the fixture whose *correct* answer the review corrected:

| fixture | before expected | after expected | actual |
|---|---|---|---|
| `selftest_synthetic_declared` (adapter hits the EvE trap, declares it, does not claim a match) | `PASS` | `PARTIAL (5/14 measured)` | `PARTIAL`, `measured=5`, `adapted=9` |
| the other 19 (honest, clean, zero-on-error, cache hit, timeout, truncated, drift 1e-6, drift 1e-10, swap, digest swap, partial coverage, manifest triple, attempt-theta drift, stale EID*, native theta, mislabeled synthetic, wrong kind, wrong stage, omitted kind) | unchanged | unchanged | all as expected |

`check_expectation` now also asserts the split and the label text on the three fixtures that declare
them, so the accounting cannot silently regress.

## 5. UNPROVEN, and what would settle it

Recorded in `qualification.json` → `unproven`. Nothing here is hidden inside a passing component.

| what | status | how to settle it |
|---|---|---|
| EvE completes a real round end to end (selection consumed and written back) | **UNPROVEN** — 3 attempts, none wrote back; every post-round solver is the prefill | run the documented driver `a0/runtimes/eve/tools/run_one_eve_iteration.py --run-dir a0/runtimes/eve/out/run006 --turns 14 --turn-timeout 660 --max-seconds 1080` and require a post-round solver whose `e_star_candidate_source_sha256` is not `18bacee4…`. Not executed here (needs the model lane) |
| Loreley completes a real round end to end | **UNPROVEN** — planning real, coding exceeded its 480 s budget | `cd a0/runtimes/loreley && timeout 1200 ./llm-round/run_bounded_round.sh` with a coding budget that fits the cap, or a smaller task. Not executed here |
| KAPSO applies the A0-wide **frozen tie-break** | **UNPROVEN** (and measured false under reordering) | already measured in both proposal orders (`a0/runtimes/kapso/runs/tie-order-probe/outcome.json`: `diverges_from_frozen_tie_break=true`); what remains is a *contract* decision on whether the frozen tie-break is required of KAPSO at all |
| the closure verdicts reflect the 2026-09-21 proxy topology | **NOT RECONCILED** — `a0/closure/*.json` are dated 2026-09-20; the newer `docker --internal` + allowlist-proxy work has no per-runtime closure record | re-run the per-runtime closure verdicts against the new topology and update `a0/closure/*.json` |
| the auditor's probes C8.3 / C8.4 | **REJECTED as written** (the stored report predated a re-adoption; EvE's A0.1 answer was not stable across a mid-write window) | mitigated by regeneration: `report.json` was re-run this round and every runtime carries `adapter_revision.unchanged_during_run`; C8.4 remains a genuine stability question for EvE and would need a repeated-run stability probe |
| A0.2 for KAPSO rests partly on seams | **scope limit, declared** — one real model-lane round exists (C7.1 ACCEPTED) | run a second real KAPSO campaign without seams |

## 6. Re-running this

```bash
# 1. the corrected conformance labels (drives the four adapters; no model calls, ~45 s)
cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run
python3 conformance.py show --report report.json     # re-render report.md only
python3 selftest.py                                  # 20 fixtures, must print "all fixtures behaved as expected: True"

# 2. the qualification vector and the predicate (reads the evidence, runs nothing)
cd /home/ebt/rsi-dev/a0/qualification
python3 build_qualification.py                       # regenerate qualification.json
python3 build_qualification.py --check               # re-derive and diff; exit 1 on drift
python3 eligibility.py                               # the Eligible(r; T) table
python3 eligibility.py --self-test                   # the predicate on hand-built vectors
python3 verify_qualification.py                      # independent consistency check, 15 assertions
```

`verify_qualification.py` is the one to run first if the question is "does this pile of claims
still match the artifacts?": it re-reads `a0/conformance/report.json`,
`a0/conformance/selftest_report.json` and the closure/A0.2 sources, and fails loudly if any label,
number, evidence path or predicate outcome has drifted.
