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

## D-GATE-4 — `τ = 30 s` because no calibration `p99` is frozen in this repository

§7 wants `τ = min(30 s, max(10 s, 10 × p99))` with `p99` from the §9 calibration
set. The calibration set exists (`suite/calibration/`, 12 graphs) but no `p99`
and no frozen `τ` are published anywhere in the repository yet — searched for
`p99`/`timeout_s`: the only hits are §7's formula and the evaluator's own
defaults (`defaults.timeout_s = 30.0`, band `10…30`). So the gate uses the band
maximum, `30 s`, which is also `e_star.py`'s default and §5's example value.

**Bearing on the verdict.** None measurable: the longest PC invocation observed
was `472 ms` and there were `0` timeouts at `30 s` on either set.

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
`dev` and `eval`. The consequence is that D-GATE-4's `τ` could not be re-derived
here even though the data to do so may exist.

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
