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

---

## D-GATE-2 — the median of an even number of exact rationals

`gate_config.gates.rho_gate.median_definition` freezes it: the exact midpoint of
the two central order statistics. (The assignment says "global median"; with
`n = 24` graphs there is no single central value.) Ordering and averaging are on
`Fraction`s, never on floats. For the dev set the two candidates differ by
`|0.1588 − 0.1638|`, and both are far below `0.30`, so the verdict is insensitive
to this choice — but it is stated so a re-implementation matches to the digit.

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
that is already solved at the baseline.

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
for them "if cheap") and written to `verdict.eval.json` / `verdict.eval.md` —
never merged into the dev verdict — so that §12's "let no eval instance enter the
agent's workspace, context or any visible path" is not weakened. Nothing in the
gate's decision path reads an eval number; `gate_config.sets` freezes which set
is `gate` and which is `diagnostic`.

Both sets fail ρ and pass Δ, which is corroboration rather than a second chance:
no threshold was evaluated against eval.

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
`gates/refreeze_evidence.py --before HEAD` compares each verdict as committed
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

`gate_runner.py` takes `--pc <dir>` (default `positive_control/pc`). The
candidate's directory name selects its Outcome directory and its verdict file
names, so:

* a variant's run reuses the baseline's Outcomes instead of recomputing them —
  and cannot accidentally pair one PC's value with another baseline's;
* the contract PC's frozen file names are unchanged (`verdict.dev.json`,
  `values/dev.positive-control.json`), so nothing already published moved;
* a variant writes `verdict.dev.pc_exchange_k10.json` and
  `values/dev.pc_exchange_k10.json`, side by side with the contract PC's.

This is additive: with no `--pc` the runner behaves exactly as before, which the
field-level diff in D-GATE-11 confirms.

---

## Deliberately *not* done this round

* **No `k` was adopted.** `REVISION-PROPOSAL.md` supplies the curve and a
  recommendation; choosing the artifact the contract calls `PC_i` is a contract
  revision and belongs to the contract author. The gate's verdict for the
  contract PC is still `NOT_ADMISSIBLE` and is still what a caller gets by
  default.
* **No threshold was touched.** `Δ` (`0.03` / `0.02` / 3-of-4), `ρ`
  (`0.30` / `0.30` / 3-of-4) and the saturation veto are byte-identical to the
  pre-registered values; `gate_config.json`'s only change is `θ` and the comment
  that documents it.
* **The suite, `references/targets.json`, `C*(T1)`, `E*` and every upstream
  runtime are read-only here.** No file outside `positive_control/` and `gates/`
  was written.
