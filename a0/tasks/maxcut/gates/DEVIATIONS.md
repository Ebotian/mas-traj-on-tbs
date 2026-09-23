# `gates/` deviations and interpretation notes

Owner: the gate workstream of `a0/tasks/maxcut/`. Authority: `../INTERFACE.md`
(v1.1) and the task assignment that named this directory. Each entry names what
was left open, what was chosen, and why. `../INTERFACE.md` was not edited; the
threshold *numbers* were not touched.

---

## D-GATE-1 — the scale of Δ (the only substantive reading this directory had to choose)

**Clause.** The assignment pre-registers "Δ gate: overall mean Δ_PC ≥ 0.03, and
Δ ≥ 0.02 in ≥ 3 of 4 families" but never defines Δ. Two readings are defensible:

| reading | definition | needs `T_i`? |
|---|---|---|
| **A (chosen)** | `Δ_i = (p_i − b_i)/|E_i|` — edges gained, as a fraction of the instance's edges | no |
| B | `Δ_i = (p_i − b_i)/(T_i − b_i)` — fraction of the baseline→target gap closed | yes |

**What was done.** A is primary and is what `gate_config.quantities.delta_i`
freezes. Reading B is reported beside it in every row as `headroom_closed`
(exact + display), and the human table states the fact that identifies B as the
complement of ρ (`Δ + ρ = 1`), so nothing about the other reading is lost.

**Why A.** (i) It is the improvement *in the objective*, normalised by the
instance's own size — the same denominator §5's `cut_fraction` uses — so it is
comparable across graphs and is exactly what "the substrate improved the
algorithm" means. (ii) Decisively, A does not depend on `T_i`, and the assignment
requires the Δ half to be *implementable and reportable before
`references/targets.json` exists*: "Implement and run what does not depend on it
(baseline, PC, the Δ gate) and mark the ρ half PENDING". A definition that needs
`T_i` cannot satisfy that sentence.

**Bearing on the verdict.** None. Under reading A the Δ gate passes with
`0.248 ≫ 0.03`; under reading B the mean is `0.826 ≫ 0.03`, so the gate passes
either way and the failing path is ρ regardless. The choice is recorded because
it changes what the number *means*, not because it changes the answer.
(**2026-09-23:** the two mean numbers, and "the failing path is ρ", belong to the
superseded unbounded control (`PC_∞`, `positive_control/pc`). Under the adopted
`k = 10` control the Δ half still passes and the ρ half now passes, so the verdict
is `ADMISSIBLE` — D-GATE-18. Reading A still changes what the number means, not
the answer.)

---

## D-GATE-2 — the median of an even number of exact rationals

`gate_config.gates.rho_gate.median_definition` freezes it: the exact midpoint of
the two central order statistics. (The assignment says "global median"; with
`n = 24` graphs there is no single central value.) Ordering and averaging are on
`Fraction`s, never on floats. For the dev set the two candidates differ by
`|0.1588 − 0.1638|`, and both are far below `0.30`, so the verdict is insensitive
to this choice — but it is stated so a re-implementation matches to the digit.
(**2026-09-23:** those two medians, and that verdict, are the superseded `PC_∞`
control's. The adopted `k = 10` control's dev ρ median is `0.615639328`, which is
also far from the `0.30` bar, so this choice remains insensitive — D-GATE-18.)

---

## D-GATE-3 — how "saturation NO-GO" is made executable

**Clause.** "Saturation NO-GO: if the baseline is already at/near the reference,
fail the task." No threshold is given for "at/near".

**Frozen operationalisation** (`gate_config.gates.saturation_no_go`): NO-GO if
the median of `(T_i − b_i)/T_i` over the set is below `1/20`, **or** if any graph
has `T_i == b_i` (the baseline attains the reference). `min`, `median` and the
list of zero-headroom graphs are all reported, so a different reading of "near"
is a one-line edit to `gate_config.json` followed by a re-run — and the verdict
records that config's sha256, so the edit would be visible.

**Result.** Not triggered: median `0.384381172`, min `0.257847534` on dev. The
baseline is far from the reference, so the failure cannot be blamed on a suite
that is already solved at the baseline. (**2026-09-23:** "the failure" is the
superseded `PC_∞` control's ρ failure; the median and min above are functions of
the baseline and the targets only, so they hold for either control, and the veto
is not triggered — D-GATE-18.)

---

## D-GATE-4 — `τ`: was the band maximum, now **CLOSED** by derivation (2026-09-22)

**Original entry.** §7 wants `τ = min(30 s, max(10 s, 10 × p99))` with `p99` from
the §9 calibration set. The calibration set exists (`suite/calibration/`,
12 graphs) but no `p99` and no frozen `τ` were published anywhere in the
repository — searched for `p99`/`timeout_s`: the only hits were §7's formula and
the evaluator's own defaults (`defaults.timeout_s = 30.0`, band `10…30`). So the
gate used the band maximum, `30 s`, and this entry recorded that as a guess.

**Resolution.** `tau_calibration.py` measures the distribution §9 asks for and
applies §7's formula. Population: the candidates the task actually runs — the
frozen baseline `b_i`, `PC_i`, its five truncations, and `C*(T1)`'s `ok` rows —
run through E* on the 12 calibration graphs, 2 invocations each (360 timings).
`C*(T1)`'s deliberately-sleeping `timeout` candidate is excluded: it exists to
*exceed* τ, so including it would make the percentile meaningless. Timings are
E*'s own `resources.runs[].wall_ms`; the percentile is the nearest-rank order
statistic, stated in the output.

| | |
|---|---|
| pooled p50 / p95 / p99 / max | `23–24 ms` / `87–88 ms` / **`133–136 ms`** / `140–142 ms` |
| slowest single candidate (`PC_i`, p99) | `140–142 ms` |
| `10 × p99` | `1.33–1.36 s` |
| `τ = min(30 s, max(10 s, 1.33 s))` | **`10 s`** — the 10 s floor binds |

(two runs; the ranges are the run-to-run variation.)

**2026-09-23 label note.** `PC_i` in the population sentence and in the table is
the unbounded control, now labelled `PC_∞` (`positive_control/pc`); the same key
in `tau_calibration.json` and in `tau_calibration.py`'s candidate map reads the
same way. The adopted contract `PC_i` is the variant `pc_exchange_k10` (D-GATE-18).
`τ` itself does not change: the stored re-measurement gives pooled p99 `146 ms`,
so `10 × p99 = 1.46 s` and the 10 s floor still binds.

`gate_config.theta.timeout_s` is now `10.0`, with the derivation and the evidence
file named in the config itself. The floor binding makes the value insensitive to
the percentile estimate: any pooled p99 below 1 s yields `τ = 10 s`.

**Bearing on the verdict.** None — and that was checked, not assumed, by
re-running both sets: the field-level diff between the verdicts at `τ = 30 s` and
at `τ = 10 s` is the identity fields only (`DEVIATIONS.md` D-GATE-11). The
longest invocation ever observed for any candidate under the gate is `472 ms`,
and there are `0` timeouts.

**One caveat, for whoever owns the task-level θ.** `θ` is recorded inside every
Outcome and inside its `canonical_digest` (§5), so adopting `τ = 10 s` for runs
beyond this gate means re-running anything that stored Outcomes at
`θ = (1337, 30)` — `a1`'s registered T1 tree and `redesign/`'s lever tables.
Their *decisions* would not change (nothing is anywhere near either τ), but their
recorded digests would. That call belongs to the contract owner; this directory
has made it only for its own runs and says so in every verdict's `theta` field.

---

## D-GATE-5 — dev decides; eval is written to a *separate* file

The gate is decided on `dev`. The eval numbers are computed (the assignment asks
for them "if cheap") and written to a separate eval verdict file
(`verdict.eval.pc_exchange_k10.json` / `.md` for the adopted control, and
`verdict.eval.json` / `.md` for the superseded `PC_∞` one — D-GATE-18) — never
merged into the dev verdict — so that §12's "let no eval instance enter the
agent's workspace, context or any visible path" is not weakened. Nothing in the
gate's decision path reads an eval number; `gate_config.sets` freezes which set
is `gate` and which is `diagnostic`.

Both sets fail ρ and pass Δ under the superseded `PC_∞` control, which is
corroboration rather than a second chance: no threshold was evaluated against
eval. (**2026-09-23:** under the adopted `k = 10` control both sets pass both
halves; this paragraph records the earlier round, in which the contract's control
failed the ρ half — D-GATE-18.)

---

## D-GATE-6 — multi-seed and cross-implementation runs are diagnostics and decide nothing

`seed_sensitivity.py` re-runs the same measurement at four additional seeds. It
writes to `outcomes/<set>/s<seed>/`, leaving the pre-registered outcomes
untouched, and it reuses `gate_runner`'s own `delta_gate`/`rho_gate` functions
rather than re-implementing them, so a bug in the gate would not be hidden by the
diagnostic. The decision remains the single pre-registered seed (`1337`), because
"best of five seeds" is exactly the kind of relaxation §12 forbids.

`rho_crosscheck.dev.json` is `../references/recompute_rho.py`'s independent ρ
over the same E* Outcomes, fed through `values/dev.*.json`. Agreement is
evidence; the verdict comes from this directory's own arithmetic.

---

## D-GATE-7 — the gate's thresholds are data, not code, and their digest is in the verdict

`gate_config.json` carries the thresholds, `θ`, the set roles and the quantity
definitions; it is stamped `"status": "PRE-REGISTERED"` and its sha256 is copied
into every verdict document. A later edit to the config is therefore visible as a
digest mismatch against any verdict already issued. This is how "the gate was not
relaxed after a failure" is made checkable rather than promised.

---

## D-GATE-8 — the calibration set is deliberately untouched

§9 forbids using `suite/calibration/**` for anything but resource rates. A gate is
selection-adjacent, so `gate_runner.py` and `seed_sensitivity.py` address only
`dev` and `eval`. `tau_calibration.py` *does* use the calibration set, and is the
one place that legitimately may: §9 names "candidate latency distribution
(giving p99 → τ)" as one of the things the calibration set is for. It measures
latency and nothing else, and it takes no part in any choice between candidates.

---

## D-GATE-9 — the ρ half was *not* PENDING after all

The assignment anticipated that `references/targets.json` might not exist yet and
asked for the Δ half plus a PENDING marker and the exact completing command. In
fact the file landed while this work was in progress (sha256 `cd802eb8…`,
`generated_utc 2026-09-22T09:01:00Z`, 60 graphs, 42 of them SCIP-certified), so
both halves ran and the verdict is a decision rather than a promise. The PENDING
path is still implemented and exercised: `rho_gate` returns
`PENDING` with a reason when no graph carries a usable `T_i`, the top-level
verdict then becomes `PENDING` (never `PASS`), and `pending_command` carries the
exact command that would complete it. Removing `--targets`' default file is
enough to see that behaviour.

---

## D-GATE-10 — re-freeze #1: a *dependency* changed (the E* D-T1-10 fix), not a drift

`e_star.py` / `e_star_child.py` were fixed on 2026-09-22 (commit `6dd717c2`): the
candidate launch no longer depends on the entry's mode bit, because
`stage_candidate` runs a content-only copy and the `X_OK` branch could never
succeed. `evaluator_source_sha256` moved `08281d21… → 4afff01f…`, and because
that digest is inside every Outcome, every stored `canonical_digest` moved with
it.

**What was done.** Both sets were re-run through E* (`--force`) and the Outcomes,
value files and verdicts re-frozen. The field-level diff at that moment was:
**2 differing leaf fields, 0 of them decision fields** —
`artifacts.evaluator_source_sha256` and `targets.sha256`, the second of which is
not this workstream's change at all (D-GATE-12). Every row, every family and
stratum reduction, and the verdict itself were identical.

`4afff01f…` is itself history now — `baf13884` superseded it, see D-GATE-15.

This is a re-freeze, and calling it anything else — a "drift", or worse, keeping
the old numbers and their now-wrong digests — would misrepresent what happened:
the frozen artifacts are no longer the artifacts that produced the earlier
digests, even though every digit of every decision is the same. `--force`
re-running from scratch is also the only honest way to show that *nothing else*
was affected, because the alternative (reusing the old Outcomes) would have
carried the pre-fix digest forward.

---

## D-GATE-11 — re-freeze #2: `θ` changed (`τ = 30 s → 10 s`), verdict unchanged

Changing `gate_config.theta.timeout_s` invalidates every stored Outcome for the
same reason as D-GATE-10: `θ` is in the Outcome and in its digest. Both sets were
re-run at the new `θ`.

**The record is the combined diff, and it is machine-checked.**
`gates/refreeze_evidence.py --before 7bf8a14b` compares each verdict as committed
against the verdict on disk now, classifies every differing leaf field as
identity or decision, and refuses to be quiet about a decision field that moved:

| verdict | differing leaf fields | identity | decision | verdict value |
|---|---|---|---|---|
| `verdict.dev.json` | 5 | 5 | **0** | `NOT_ADMISSIBLE → NOT_ADMISSIBLE` |
| `verdict.eval.json` | 5 | 5 | **0** | `NOT_ADMISSIBLE → NOT_ADMISSIBLE` |
| overall | | | | **CLEAN** |

The five identity fields are `evaluator_source_sha256` (D-GATE-10),
`pc_source_sha256` (D-PC-7's `MAX_SWAPS` line), `gate_config_sha256` and
`theta.timeout_s` (this entry), and `targets.sha256` (D-GATE-12). `--before HEAD`
means the comparison covers all four changes at once; the intermediate
two-field state after D-GATE-10 alone was measured at the time and is
reproducible by setting `θ` back to `30 s`, re-running, and reading the same
table — the script is the permanent instrument, not this paragraph.

Both re-freezes are recorded separately so that each change has evidence that it
moved no number, and the combined evidence is regenerable by anyone with the
commit.

---

## D-GATE-12 — `references/targets.json` was revised by its owner mid-round

The target file was re-frozen under this workstream (`cd802eb8… → 0919d7a4…`,
`generated_utc 09:01:00Z → 09:19:40Z`, its owner's commit `623395d8`, "4× top-up
finds nothing"). It is read-only here, and no target moved: for all 48 dev+eval
graphs the recorded `T_i` is identical before and after, which is why the
verdicts differ only in the digest they record. Every verdict carries the
`targets.sha256` it used, so a reader can tell which revision produced which
number. `redesign/`'s L1 top-up independently reports the same finding ("the 4×
top-up barely moves `R`: 2 graphs, by 2 and 3 edges").

---

## D-GATE-13 — the Outcome cache now validates `(θ, E* digest, candidate digest)`

Before this round the cache was keyed on the path alone, so a stored Outcome
looked valid after the evaluator moved underneath it — which is exactly how the
committed verdicts became stale after the D-T1-10 fix, and why the coordinator had
to ask for a re-run. `cache_is_current` now checks that a cached Outcome carries
this run's `seed` and `timeout_s`, this E*'s `evaluator_source_sha256`, and the
live `candidate_source_sha256` of the candidate directory (via E*'s own
`resolve_candidate`, not a re-derivation). A stale record is re-run and the fact
is printed to stderr rather than swallowed.

**Verified by execution, twice.** The `τ` change re-ran all 96 cached Outcomes at
`τ = 10 s`; editing the variants' `candidate.json` re-ran all 240 variant Outcomes
(`stale=24` per candidate per set, 10 runs). `--force` still exists and still
overrides everything.

---

## D-GATE-14 — `--pc`: the runner now evaluates any candidate as the positive control

`gate_runner.py` takes `--pc <dir>`. It defaulted to `positive_control/pc` until
2026-09-23, when the contract adopted `k = 10` and the default moved to
`positive_control/variants/pc_exchange_k10` (D-GATE-18). The candidate's
directory name selects its Outcome directory and its verdict file names, so:

* a run reuses the baseline's Outcomes instead of recomputing them — and cannot
  accidentally pair one PC's value with another baseline's;
* each PC keeps its own frozen file names, so no PC's published verdicts are
  overwritten by another's (the superseded `verdict.dev.json`,
  `values/dev.positive-control.json` are still on disk, for the `PC_∞` control);
* `verdict.dev.pc_exchange_k10.json` / `values/dev.pc_exchange_k10.json` are the
  adopted contract PC's files today — that name is what path stability required
  when the default was re-pointed (D-GATE-18).

This was additive to the runner's logic: `--pc` changes only which directory is
resolved and which file names follow, which the field-level diff in D-GATE-11
confirms.

---

## D-GATE-15 — re-freeze #3: `E*` moved again (`4afff01f… → dc6969ec…`), and the stamps catch up

**What triggered it.** The evaluator was re-frozen a third time for reasons
outside this directory: `baf13884` ("close the answer leaks") changed
`e_star.py`/`e_star_child.py` so the candidate is handed a redacted
`candidate_graph.json` (`candidate_graph_sha256`/`bytes`/`keys`/`schema`) instead
of the raw graph file. `e_star.py`'s own `digest --value-only`, run on each
revision's two files, gives the full lineage:

| `evaluator_source_sha256` | revision | status |
|---|---|---|
| `08281d21e6e84a79dfebd895d7653b517c1e08e7ea8784fe485532dd5db59c4d` | `11f55bf0` | **history** |
| `4afff01f8a73479b2cb548686b4ae31c50100699057d3fad512f7a6aabb4a23a` | `6dd717c2` (D-T1-10) | **history** |
| `dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00` | `baf13884` | **current** |

Independent verification (`a0/verify/a1-final/REPORT.md`) found that this
directory's committed artifacts had not followed: 924 stamped records (576 stored
Outcomes, the 14 `values/` documents built from them, and all 12 verdicts) still
named the superseded `4afff01f…`, and `README.md` stated it in the present tense.
The record was stale while every *decision* it carried was still correct.

**What was done.** The whole measurement was re-run against the current `E*` —
both sets at the frozen `θ`, all five truncation variants on both sets, and the
seed-sensitivity seeds — which rewrote all 576 Outcomes, the 14 `values/`
documents and the 12 verdicts. No `--force` was needed: `cache_is_current`
(D-GATE-13) detects that the cached Outcome names a different evaluator and re-runs
it, printing the fact to stderr. 576 of 576 Outcomes were re-measured.

**Identity moved; nothing else did.** `restamp_evidence.py` (new, and the
instrument for this question) diffs every stored record against the previous
freeze at leaf level and asks `e_star.py digest` — rather than assuming — what the
current evaluator is:

| record set | records | differing | leaves that moved | decision leaves |
|---|---|---|---|---|
| stored Outcomes | 576/576 | 6 leaves each | `evaluator_source_sha256`, `canonical_digest`, `candidate_graph_bytes`, `candidate_graph_keys`, `candidate_graph_schema`, `candidate_graph_sha256` | **0** |
| verdicts | 12/12 | 1 leaf each | `artifacts.evaluator_source_sha256` | **0** |
| stamped records, all 602 documents | 924 | — | 924 name the current `E*`; **0 stale** | — |

`refreeze.evidence.py` now covers all 12 verdicts, not the 3 it named before: the
sixth positive control's verdicts (`pc_exchange_k01/k02/k05/k25`) were outside the
diff, which is the one place a stale digest could have hidden unchecked. Every
verdict — `NOT_ADMISSIBLE` for `dev`/`eval`, `ADMISSIBLE` for the variants that
pass, `NOT_ADMISSIBLE` for `eval` at `k25` — is unchanged, and every rendered
`.md` table and `strength_table.{json,md}`/`seed_sensitivity.dev.json`/
`rho_crosscheck.dev.json` came out byte-identical, so no decision number moved.
(**2026-09-23:** the `dev`/`eval` verdicts named here are the superseded `PC_∞`
control's, `verdict.{dev,eval}.json`. The adopted `k = 10` control's verdicts are
`verdict.{dev,eval}.pc_exchange_k10.json` and read `ADMISSIBLE` — D-GATE-18. Also:
one byte-identity reading above no longer holds for a later reader. A dated label note
was appended to `seed_sensitivity.dev.json`'s `note` string on 2026-09-23; its `rows`
are unchanged, so the reading this entry makes — that no decision number moved — still
stands.)

**One number that did move, and it is not a decision.** `tau_calibration.json` is
re-measured from scratch, and the percentiles came out higher than at the first
measurement: pooled p50 `23–24 → 34–35 ms` and pooled p99 `133–136 → 146–147 ms`
over two re-stamp runs. Whether that is a slower host, a noisier one, or both is
not measured here. What *is* measured is that the derivation's output does not
depend on it: `10 × p99 ≤ 1.47 s` still sits under the 10 s band minimum, so
`τ = 10 s` is unchanged and the floor still binds with 6.8× margin. Recorded here
because a reader diffing the file would otherwise see timings move without an
explanation; `wall_ms` is a diagnostic, never an input to Δ, ρ or the veto.

**A fabricated stamp, corrected.** `README.md` §2 named `79a27789…` as the current
`gate_config.json` digest. No revision of that file ever had it — measured:
`1ff12031…` at `f9054e56` and `171c23d8…` at `b9dfb859`, which is what all 12
verdicts record. The paragraph now names the right digests and says what was
corrected.

**What the history rule now is, and how it is enforced.** No artifact from a
superseded revision is kept; the only surviving mentions of a superseded digest
are prose sentences in `README.md` and this file, each of which names the revision
it belongs to. `restamp_evidence.py` enforces exactly that: it fails with `DRIFT`
if a stamped record names anything but the live `E*`, if a decision leaf moves, or
if a superseded digest appears on a line that does not say it is history. Its
first run reported the `README.md` line above as unlabelled — that is the check
working, and it is why the line no longer reads as present tense.

**Verified by execution.** `python3 gates/restamp_evidence.py --before 7bf8a14b`
→ `CLEAN`, rc `0` (`7bf8a14b` is the freeze this re-stamp moved off, so the command
reproduces the transition itself, not just the end state — that is the command a
reviewer should re-run); `python3 gates/refreeze_evidence.py --before 7bf8a14b`
→ `CLEAN`, 12 verdicts, 0 decision leaves;
`python3 gates/gate_runner.py` → `NOT_ADMISSIBLE`, exit 1. Zero model spend: no
`a0/meter/` call was made for any of this. (**2026-09-23:** that default-control
result was correct at the re-stamp. The runner's default is now
`pc_exchange_k10` (D-GATE-18), so `python3 gates/gate_runner.py` today returns
`ADMISSIBLE`, exit 0; the `NOT_ADMISSIBLE`/exit-1 path needs
`--pc positive_control/pc`.)

---

## Deliberately *not* done this round

* **No `k` was adopted *in that round*.** `REVISION-PROPOSAL.md` supplied the
  curve and a recommendation; choosing the artifact the contract calls `PC_i` was
  a contract revision and belonged to the contract author. It was taken on
  2026-09-23 — see D-GATE-18 — so this bullet is history: the gate's verdict for
  the contract PC is now `ADMISSIBLE` and that is what a caller gets by default.
* **No threshold was touched.** `Δ` (`0.03` / `0.02` / 3-of-4), `ρ`
  (`0.30` / `0.30` / 3-of-4) and the saturation veto are byte-identical to the
  pre-registered values; `gate_config.json`'s only change is `θ` and the comment
  that documents it. Re-confirmed at the re-stamp (D-GATE-15) by
  `gate_config_sha256 171c23d8…` in all 12 verdicts and by
  `restamp_evidence.py` finding 0 decision leaves moved — the thresholds were not
  re-typed, and the digest the pre-registration was frozen under is the digest the
  verdicts record.
* **The suite, `references/targets.json`, `C*(T1)`, `E*` and every upstream
  runtime are read-only here.** No file outside `positive_control/` and `gates/`
  was written.

---

## D-GATE-16 — the re-freeze instruments no longer default to a vacuous window

**The defect.** Both instruments documented `--before HEAD`. Once the re-stamp had
landed, that invoked each one against itself: `restamp_evidence.py` reported
`0/576` and `0/12` and `CLEAN`, `refreeze_evidence.py` reported 0 differing leaf
fields for all 12 verdicts and `CLEAN` — and either run **rewrote its own committed
evidence file** (`before_revision: HEAD`, empty diffs), so a reader following the
documentation would commit a strictly weaker record without noticing. Measured
before the change:

```
outcomes: 0/576 differ; leaves moved {}; decision leaves 0
verdicts: 0/12 differ;  leaves moved {}; decision leaves 0
re-stamp verdict: CLEAN
```

**What changed.** `--before` now defaults to the revision the instrument's own
committed evidence records (`7bf8a14b`, the freeze the re-stamp moved off), the
revision is resolved with `git rev-parse --verify` (an unknown revision refuses
with exit 2), and a run whose comparison window is empty — 0 Outcomes or 0 verdicts
differing — **refuses with exit 2 and writes nothing**. An explicit `--before` is
still honoured, so the meaningful comparison and any later re-freeze both work;
only the self-comparison is refused. `refreeze_evidence.py` grew the same guard and
the two share the resolution helpers rather than keeping a second copy.

**Verified by execution.** `python3 gates/restamp_evidence.py` and
`python3 gates/refreeze_evidence.py` (no `--before`) → `CLEAN`, `576/576`+`12/12`
and `12/12` respectively, rc 0. `--before HEAD` on either → `REFUSED`, rc 2, and no
file written. `refreeze.evidence.json` is byte-identical to its committed copy after
the default run; `restamp.evidence.json` was regenerated because this file's and
`restamp_evidence.py`'s own line numbers moved, which is the only field that
changed.

**The extension beyond the reported finding.** The verifier's caveat named
`restamp_evidence.py`. `refreeze_evidence.py` measured vacuous in exactly the same
way (0/12, `CLEAN`) and its documented command was the one `README.md` recommended,
so the same rule was applied to both rather than closing half of a shared failure
mode. No threshold, the suite, `E*` and the pending contract revision were touched.

## D-GATE-17 — the causal audit cross-checks the registered tree (`a0/a1/declaration.py`)

Recorded here rather than in `a0/a1/DEVIATIONS.md` because another workstream has
uncommitted edits in that file in this shared tree; the change itself is in
`a0/a1/declaration.py`, one of this pass's owned files.

**The gap.** The audit gating `CID`/`AID_r` compared the registered tree only
against `binding.json` (tree ↔ binding), never against `CID`. A tree rebuilt from a
superseded `T1-EID.json`, with a binding re-derived from *its* bytes so the two
agreed, made `AID_r` name `manifest:6b1d6fcc…` while `CID` named
`EID* 7ce9e72f…`, and the audit still said `pass` (verifier finding 2c, REJECTED).

**What changed.** `registered_tree_checks(cid)` now also reads the tree's own
`tree/a0_locator.json` and fails with the named problem
`registered_tree_eid_mismatch` when the locator does not pin the `CID`'s
`task.eid_star` or its `E*` source digests; a new
`registered_tree_factor_checks()` re-reads the written `AID_r` and fails with
`registered_tree_factor_mismatch` when its tree factors do not equal a fresh
recomputation of the tree's bytes. `write()` appends both to the audit's
`problems`, so the verdict is `fail` and the CLI exits 5. On the honest tree the
committed `declarations/**` are still reproduced byte for byte — no declaration
digest moved.

**Verified by execution.** `python3 a0/a1/declaration.py selftest` offers the
pre-rebuild tree (`7bf8a14b`) plus a binding re-stamped to its bytes: the audit
fails with `registered_tree_eid_mismatch`, while the honest tree passes. The full
A1 entry point (`a0/a1/verify.py`) stays green.

## D-GATE-18 — the contract adopted `k = 10`: the gate's default control moved

**The decision.** On 2026-09-23 the coordinator adopted the bounded-round variant
`pc_exchange_k10` as the contract's `PC_i`, on the evidence and under the
criterion in `REVISION-PROPOSAL.md` §2/§3/§6 (now §6.1, ADOPTED). The revision
record is `../positive_control/PC-REVISION.md`. Nothing about the gate itself
moved: no threshold in `gate_config.json`, no suite graph, no line of `E*`, no
target reference.

**What changed, and only this.** `gate_runner.py`'s `DEFAULT_PC` was re-pointed
from `positive_control/pc` to `positive_control/variants/pc_exchange_k10`.

**Why the candidate's *location* was not changed.** `REVISION-PROPOSAL.md` §8.2
had suggested promoting the variant by moving it into `positive_control/pc/`.
That was measured to be the wrong move: the candidate directory's *name* keys the
Outcome paths and the verdict file names, so moving it would have rewritten every
stored record for the contract PC — `cut_edges`, `Δ`, `ρ`, the two verdicts — a
*decision* change. Re-pointing the default instead leaves every stored decision
where it was and makes the already-measured `verdict.*.pc_exchange_k10.*` the
adopted verdict, byte for byte.

**Verified by execution.** With the new default,

```
$ python3 gates/gate_runner.py --set dev    # → ADMISSIBLE, Δ 0.116584858, ρ 0.615639328, 4/4 families
$ python3 gates/gate_runner.py --set eval   # → ADMISSIBLE, Δ 0.116426731, ρ 0.600847458, 4/4 families
$ git status --short -- a0/tasks/maxcut/gates a0/tasks/maxcut/positive_control
 M a0/tasks/maxcut/gates/gate_runner.py
```

i.e. the re-run rewrote no Outcome and no verdict. The identity instruments
agree: `restamp_evidence.py` → `576/576` Outcomes and `12/12` verdicts differ
from `7bf8a14b` in identity leaves only, **0 decision leaves**, `CLEAN`;
`refreeze_evidence.py` → `12/12`, one identity leaf each, `0` decision leaves,
`CLEAN`.

**The superseded control is kept.** `positive_control/pc/`, its bytes, its
`pc_identity_report.json` and its verdicts `verdict.{dev,eval}.json` (still
`NOT_ADMISSIBLE`) are untouched, and
`python3 gates/gate_runner.py --set dev --pc positive_control/pc` reproduces
them. `../positive_control/HISTORY.md` is the index.

**Reported, not applied.** `INTERFACE.md` — the contract's interface authority —
does not define `PC_i` at all (`grep -n "PC_i\|one_exchange\|positive_control"
INTERFACE.md` returns nothing), so the adoption creates a contract gap that only
its owner can close. The exact before/after text is in
`../positive_control/PC-REVISION.md` §7.

**Two stored diagnostics still carry the superseded control's numbers. Not
regenerated here, and deliberately named.** Both read the PC through
`gate_runner.DEFAULT_PC`, so the default they were measured against has moved
underneath them:

* `seed_sensitivity.dev.json` — its rows are the `PC_∞` control's
  (`Δ 0.247942608`, `ρ 0.158819629` at the frozen seed), while its own note
  points a reader at "the single frozen seed's verdict in `verdict.<set>.json`",
  which is the superseded control's file — the adopted one is
  `verdict.<set>.pc_exchange_k10.json`. Regenerating it would add ~192 tagged Outcome
  files (`outcomes/dev/s{0,1,2,3}/pc_exchange_k10/…`) that this revision has no
  need for, so the file is left as the `PC_∞` diagnostic it is — **read its rows
  as `PC_∞` rows.**
* `tau_calibration.json` — its candidate map labels `"PC_i"` →
  `positive_control/pc`. The derivation is unaffected: the pooled p99 is
  `133–136 ms`, so `10 × p99` is below the §7 floor and `τ = 10 s` binds at every
  `k` (`REVISION-PROPOSAL.md` §7). **Read its `"PC_i"` key as `PC_∞`.**

Neither is a gate input: `gate_config.json` carries `τ`, not these files. Both
are listed here so that the label drift is visible rather than latent. Re-running
either under the adopted control is a follow-up, not part of this revision.
