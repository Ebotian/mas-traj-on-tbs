# `gates/REVISION-PROPOSAL.md` — replacing `PC_i`, for the contract author to decide

**Status: DECIDED — `k = 10` ADOPTED on 2026-09-23. The proposal below is kept
as the pre-decision record.**
The contract's positive control is now `positive_control/variants/pc_exchange_k10`
(the pinned `one_exchange`, stopped after 10 accepted improving swaps), and the
gate reads it by default. The gate as revised returns **`ADMISSIBLE` on dev and
on eval**, both bars cleared by ≥ 2× in 4/4 families:

| set | verdict | Δ mean | ρ median | families (Δ / ρ) | artifact |
|---|---|---|---|---|---|
| dev | **`ADMISSIBLE`** | `0.116584858` | `0.615639328` | 4/4 / 4/4 | `verdict.dev.pc_exchange_k10.json` |
| eval | **`ADMISSIBLE`** | `0.116426731` | `0.600847458` | 4/4 / 4/4 | `verdict.eval.pc_exchange_k10.json` |

The unbounded local-optimum control is kept as labelled history at
`positive_control/pc/`; its verdicts `verdict.dev.json` / `verdict.eval.json`
still read `NOT_ADMISSIBLE` and are unchanged. See
`../positive_control/PC-REVISION.md` for the revision record and
`../positive_control/HISTORY.md` for the index. **No threshold, no suite graph
and no line of `E*` was changed by the adoption**; the revision moved the
identity of the artifact and nothing else (`§8.0`).

Owner: the gate/positive-control workstream. Authority: `../INTERFACE.md` (v1.1).
Sections 1–7 are the measured curve and the declaration that were put in front
of the person who owns the contract, kept verbatim as the record of what was
decided and on what evidence. Section 6 is the section that names `k = 10`; the
decision has been taken there and is restated here.

---

## 1. The problem, in numbers

The pre-registered gate asks two things of a task. Measured on the frozen dev
suite with the contract's positive control,
`PC_i = one_exchange(G_i, initial_cut=b_i, seed=s_i)` run to a local optimum:

| gate | required | measured | |
|---|---|---|---|
| Δ — the artifact must demonstrably improve the baseline | mean ≥ 0.03, ≥ 0.02 in ≥ 3 of 4 families | `0.247943`, 4/4 | **PASS**, 8.3× the bar |
| ρ — enough headroom must remain afterwards | median ≥ 0.30, ≥ 0.30 in ≥ 3 of 4 families | `0.158820`, 0/4 | **FAIL**, 0.53× the bar |

The artifact is *too effective*: it reaches 94.3 % of the reference target and
closes 82.6 % of the baseline→target gap, so a substrate injected after it has
almost nothing left to earn. The failure is structural — it holds on dev and on
eval, in every family, at every seed tried (`DEVIATIONS.md` D-GATE-6,
`seed_sensitivity.dev.json`).

The brief for this round names one lever that works and two that do not:
`redesign/LEVERS.md` measured that raising `n` does not restore headroom
(`ER:p080`: ρ flat, `0.1768 → 0.1338` over `n = 128 → 1024`) and that a published
**greedy** construction does not either (ρ `0.2399`, still below the bar, because
it is nearly as strong as one exchange). What does work is applying the *same
published procedure* with a smaller budget:

| positive control | Δ mean (bar 0.03) | ρ median (bar 0.30) | Δ families | ρ families | task verdict |
|---|---|---|---|---|---|
| `one_exchange` to a local optimum (contract `PC_i`) | `0.247943` (8.26×) | `0.158820` (0.53×) | 4/4 | 0/4 | `NOT_ADMISSIBLE` |
| truncated after 25 improving swaps | `0.204898` (6.83×) | `0.325903` (1.09×) | 4/4 | 3/4 | `ADMISSIBLE` (dev) |
| truncated after 10 | `0.116585` (3.89×) | `0.615639` (2.05×) | 4/4 | 4/4 | `ADMISSIBLE` |
| truncated after 5 | `0.069658` (2.32×) | `0.775149` (2.58×) | 4/4 | 4/4 | `ADMISSIBLE` |
| truncated after 2 | `0.032882` (1.10×) | `0.895644` (2.99×) | 4/4 | 4/4 | `ADMISSIBLE` |
| truncated after 1 | `0.018221` (**0.61×**) | `0.940123` (3.13×) | **1/4** | 4/4 | `NOT_ADMISSIBLE` |

(dev; the full two-set, per-family table is §3. Every row was produced by
`gate_runner.py` through E*, from frozen §4 candidates in this repository, and is
reproducible with the commands in §9.)

---

## 2. Declaration: this is a posterior degree of freedom

**We measured ρ for the contract's `PC_i`, saw it fail, and only then went
looking for a weaker artifact.** `k` is therefore chosen with knowledge of the
outcome it is supposed to produce. That is exactly the kind of freedom
pre-registration exists to remove, and it must be declared rather than spent
quietly. Concretely:

* **What was *not* free.** The thresholds (`Δ ≥ 0.03`, `ρ ≥ 0.30`, 3-of-4
  families, the saturation veto) were frozen before any of this was measured, and
  `INTERFACE.md` §12 forbids relaxing them. Nothing in this proposal changes
  them, and nothing may. `gate_config.json` is unmodified: its digest is stamped
  into every verdict so a later edit is visible.
* **What *was* free.** The strength of the artifact the contract calls "a
  known-effective external artifact". §1 of this document is a statement about
  the *pair* (artifact strength, ρ threshold). With the threshold fixed, the only
  remaining axis is the artifact — which is a **task-design** decision, not a
  result. It has a real cost that the Δ column shows: weakening the artifact
  weakens the very claim the task exists to make.
* **The choice rule is pre-registered here, not eyeballed.** §6 states the
  criterion before naming a number, so the recommendation is reproducible from
  §3 by anyone who disagrees with it, and so that re-running the gate at a
  different `k` is a decision, not a search.
* **The safe default is `k = ∞`.** If the coordinator does not want to spend this
  degree of freedom, the correct outcome is the one already recorded:
  `NOT_ADMISSIBLE`. The task is then not run. That is a legitimate answer and
  needs no declaration at all.
* **Adopting a `k` re-registers the gate.** The new PC must be frozen as a
  candidate, the gate re-run on dev *and* eval, and the resulting verdicts
  re-frozen (the artifacts and the checklist are in §8). Re-running the gate and
  reporting the new numbers is not optional bookkeeping; without it, the old
  verdicts would be verdicts about a different artifact.

Why this is not simply "moving the goalposts": the goalposts are the thresholds,
and they do not move. What moves is *how hard the task is*, in a direction that
costs the task some of its own claim (Δ falls by 2.1× at `k = 10`, by 3.6× at
`k = 5`), and that is the trade the coordinator is being asked to accept
explicitly.

---

## 3. The measured curve

All numbers are exact-rational reductions of E* `cut_edges` on the frozen suite;
decimals are display fields. Machine-readable: `strength_table.json`. Each
candidate is a frozen §4 candidate with its own bytes and `source_sha256`
(`../positive_control/manifest.json`).

### 3.1 dev (the gate's deciding set)

| positive control | k | Δ mean | Δ families | Δ gate | ρ median | ρ families | ρ gate | task |
|---|---|---|---|---|---|---|---|---|
| `pc` | ∞ | 0.247943 | 4/4 | PASS | 0.158820 | 0/4 | FAIL | `NOT_ADMISSIBLE` |
| `pc_exchange_k25` | 25 | 0.204898 | 4/4 | PASS | 0.325903 | 3/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k10` | 10 | 0.116585 | 4/4 | PASS | 0.615639 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k05` | 5 | 0.069658 | 4/4 | PASS | 0.775149 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k02` | 2 | 0.032882 | 4/4 | PASS | 0.895644 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k01` | 1 | 0.018221 | 1/4 | **FAIL** | 0.940123 | 4/4 | PASS | `NOT_ADMISSIBLE` |

### 3.2 eval (unseen instances — diagnostic, decides nothing, and exactly why it matters)

| positive control | k | Δ mean | Δ families | Δ gate | ρ median | ρ families | ρ gate | task |
|---|---|---|---|---|---|---|---|---|
| `pc` | ∞ | 0.238448 | 4/4 | PASS | 0.178716 | 0/4 | FAIL | `NOT_ADMISSIBLE` |
| `pc_exchange_k25` | 25 | 0.202023 | 4/4 | PASS | 0.301163 | **2/4** | **FAIL** | **`NOT_ADMISSIBLE`** |
| `pc_exchange_k10` | 10 | 0.116427 | 4/4 | PASS | 0.600847 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k05` | 5 | 0.070200 | 4/4 | PASS | 0.762308 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k02` | 2 | 0.033074 | 4/4 | PASS | 0.894196 | 4/4 | PASS | `ADMISSIBLE` |
| `pc_exchange_k01` | 1 | 0.017983 | 1/4 | **FAIL** | 0.942883 | 4/4 | PASS | `NOT_ADMISSIBLE` |

**`k = 25` passes on dev and fails on eval.** Its dev pass comes entirely from
the 3-of-4 family rule (`BA` at ρ `0.2631`); on the unseen set a *different*
family fails (`ER` at `0.2821`), the global median sits at `1.00×` the bar
(`0.3012`), and only `2/4` families clear it. Any recommendation of `k = 25` on
the strength of the dev table alone is a dev-tuned recommendation, and this table
is the evidence that the 3-of-4 rule is not a safety net. This is a new finding
of this round: `redesign/LEVERS.md` measured dev only.

### 3.3 per family (mean Δ / median ρ)

| positive control | set | ER | RR | BA | Planted |
|---|---|---|---|---|---|
| `pc` | dev | 0.2243 / 0.2051 | 0.3043 / 0.1436 | 0.2429 / 0.1518 | 0.2203 / 0.1526 |
| `pc` | eval | 0.2177 / 0.1781 | 0.2889 / 0.1948 | 0.2414 / 0.1692 | 0.2058 / 0.1806 |
| `pc_exchange_k25` | dev | 0.1904 / 0.3275 | 0.2441 / 0.3476 | 0.2085 / **0.2631** | 0.1765 / 0.3224 |
| `pc_exchange_k25` | eval | 0.1941 / **0.2821** | 0.2332 / 0.3481 | 0.2082 / 0.2866 | 0.1725 / 0.3228 |
| `pc_exchange_k10` | dev | 0.1068 / 0.6219 | 0.1313 / 0.6345 | 0.1263 / 0.5704 | 0.1020 / 0.6051 |
| `pc_exchange_k10` | eval | 0.1113 / 0.5839 | 0.1297 / 0.6280 | 0.1250 / 0.5589 | 0.0997 / 0.6060 |
| `pc_exchange_k05` | dev | 0.0616 / 0.7807 | 0.0755 / 0.8060 | 0.0813 / 0.7417 | 0.0603 / 0.7687 |
| `pc_exchange_k05` | eval | 0.0642 / 0.7631 | 0.0768 / 0.7817 | 0.0800 / 0.7287 | 0.0598 / 0.7635 |
| `pc_exchange_k02` | dev | 0.0289 / 0.8956 | 0.0312 / 0.9160 | 0.0446 / 0.8574 | 0.0267 / 0.8951 |
| `pc_exchange_k02` | eval | 0.0304 / 0.8954 | 0.0312 / 0.9101 | 0.0427 / 0.8622 | 0.0280 / 0.8907 |
| `pc_exchange_k01` | dev | **0.0164** / 0.9401 | **0.0156** / 0.9580 | 0.0261 / 0.9124 | **0.0147** / 0.9432 |
| `pc_exchange_k01` | eval | **0.0166** / 0.9416 | **0.0156** / 0.9551 | 0.0243 / 0.9143 | **0.0154** / 0.9431 |

Bold = below a threshold. Note that `k = 2` clears its Δ bar by `0.0029`
absolute, in all four families by a small margin; `k = 1` fails Δ in three of
four families on both sets.

### 3.4 where a truncation falls inside the descent

The untruncated descent accepts a **median of 38** improving swaps on dev
(range 26–54; 38 on eval, 25–46). So `k = 1` is ~3 % of a descent, `k = 2` ~5 %,
`k = 5` ~13 %, `k = 10` ~26 %, `k = 25` ~66 %.

---

## 4. What each choice means

Truncating `one_exchange` after `k` accepted improving swaps does two things at
once, and the trade is monotone:

* **The artifact gets weaker as a demonstration.** Δ falls monotonically with
  `k`: `0.248 (k=∞) → 0.205 (25) → 0.117 (10) → 0.070 (5) → 0.033 (2) → 0.018 (1)`.
  The task's claim is "a known-effective external artifact improves the frozen
  baseline"; at `k = 2` that improvement is `1.10×` its bar and at `k = 1` it
  fails outright. **`k = 1` is the measured lower bound of admissibility** — the
  smallest truncation for which Δ still passes. It is not recommended (1/4
  families), but it bounds the interval.
* **The substrate gets more room as `k` falls.** ρ rises monotonically:
  `0.159 (∞) → 0.326 (25) → 0.616 (10) → 0.775 (5) → 0.896 (2) → 0.940 (1)`.
  Equivalently, the fraction of the baseline→target gap left for a substrate is
  `15.9 % (∞) → 32.6 % (25) → 61.6 % (10) → 77.5 % (5) → 89.6 % (2) → 94.0 % (1)`.

A truncated `one_exchange` is **still the published procedure** — the same pin,
the same shuffle stream, the same first-maximiser tie-break — stopped by a budget
rather than by optimality. What is *not* true is the tempting generalisation
"any weaker published heuristic would work": the published **greedy**
construction measured ρ `0.2399` (dev) and fails, because it is nearly as strong
as one exchange. The lever works only in the direction and in the amount
measured here.

---

## 5. Re-verification of `redesign/`'s numbers: **已复核 (re-verified)**

The `k = 10` / `k = 25` numbers in `redesign/LEVERS.md` came from that
workstream's byte-identical *mirrors* of this directory's candidates. This round
built the truncations as first-class frozen candidates in
`positive_control/variants/` and re-measured. `strength_table.py` compares the
two sets field by field — 6 variants × 10 fields (mean Δ, median ρ, and both for
each of the four families), plus the four gate counts:

| | result |
|---|---|
| variants compared | 6 (`exchange_opt`/`pc`, `k1`, `k2`, `k5`, `k10`, `k25`) |
| fields compared | 60 |
| largest absolute difference, any field | `4.98e-10` |
| gate-count mismatches | 0 |
| verdict | **agree** |

The residual `5e-10` is the float rendering of exact rationals on one side versus
`Fraction` arithmetic on the other, not a disagreement. Every `Δ` and every `ρ`
is the same number. Reproduce with `python3 gates/strength_table.py`.

---

## 6. Recommendation

**Criterion, stated before the answer.** A replacement PC should

1. pass **both** gates on dev **and** on eval, with **all four families** clear of
   each bar — not on the 3-of-4 rule, which §3.2 shows is not a safety net;
2. clear both bars by at least **2×** on both sets, so that the ~0.10
   instance-to-instance swing in ρ that `redesign/LEVERS.md` §3.2 measured cannot
   cross a bar;
3. and among those, be the **strongest** — the strongest artifact is the most
   honest reading of "known-effective", and it leaves the substrate the most
   meaningful thing to exploit.

Applying it to §3:

| k | (1) 4/4 on both sets | (2) min margin ≥ 2× | (3) strongest |
|---|---|---|---|
| 1 | no (Δ 1/4) | no (0.61×) | — |
| 2 | yes | **no** (Δ 1.10×) | — |
| **10** | **yes** | **yes** (min `2.00×`, eval ρ) | **the strongest that qualifies** |
| 5 | yes | yes (min `2.32×`) | weaker than 10 |
| 25 | **no** (eval ρ 2/4) | no (1.00×) | — |

**I recommend `k = 10`.** It is the only strength that satisfies both of the
first two conditions and is the strongest such; it is also the value this
workstream's counterpart arrived at independently, by a different argument
(`redesign/LEVERS.md` §6).

**The honest counter-case, so it is a choice and not a default.** `k = 5` has the
larger *minimum* margin (`2.32×` vs `2.00×`) and gives the substrate 22.5 % of
the gap closed rather than 38.4 % — more room to measure. If the B0+ round cares
more about the *size of the measurable space* than about the *strength of the
injected artifact*, `k = 5` is the better pick and nothing in this table argues
against it. If the round cares about the artifact being a real local search
rather than a three-quarters-of-nothing one, `k = 10` is. **I would not pick
`k = 2`** (Δ margin `0.0029` absolute is thinner than the suite's own
instance-to-instance variation) **and would not pick `k = 25`** (it fails the
gate on unseen instances).

### 6.1 Decision: `k = 10` is ADOPTED — 2026-09-23

The coordinator adopted `k = 10`. The recommendation above is now the decision,
and the re-freeze checklist in §8 has been discharged.

| item | value |
|---|---|
| adopted control | `positive_control/variants/pc_exchange_k10/` (`pc_exchange_k10`) |
| `source_sha256` | `ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da` |
| gate default | `../gates/gate_runner.py` → `DEFAULT_PC` names that directory |
| dev verdict | **`ADMISSIBLE`** — Δ `0.116584858`, ρ median `0.615639328`, 4/4 families both gates; `verdict.dev.pc_exchange_k10.json` |
| eval verdict | **`ADMISSIBLE`** — Δ `0.116426731`, ρ median `0.600847458`, 4/4 families both gates; `verdict.eval.pc_exchange_k10.json` |
| revision record | `../positive_control/PC-REVISION.md` |
| old control | kept as labelled history at `positive_control/pc/` (`HISTORY.md`) |

**The other rows of §6 stay as history, not as live options.** Each was a
measured candidate for the same decision; none is adopted.

| k | status after 2026-09-23 |
|---|---|
| 1 | history — rejected (Δ fails 3/4 families on both sets) |
| 2 | history — rejected (Δ margin 1.10×, thinner than the suite's own swing) |
| **10** | **ADOPTED** |
| 5 | history — the runner-up; kept in case a later round wants more measurable room (§6 counter-case) |
| 25 | history — rejected (ρ fails 2/4 families on the unseen set) |
| ∞ (`pc`) | history — superseded contract control, evaluated at `positive_control/pc/` |

---

## 7. What this implies for B0 and B1

* **The PC's strength is the knob on the measurable space.** B0+ injects a
  "known-effective but non-optimal" artifact, and the substrate's room is exactly
  ρ: `15.9 %` of the baseline→target gap at the contract PC, `61.6 %` at `k = 10`,
  `77.5 %` at `k = 5`, `89.6 %` at `k = 2`. Choosing `k` is choosing how much of
  the experiment is measurable at all. At `k = ∞` the round would be measuring
  within a 15.9 % sliver, with a reference target that is itself a lower bound
  for 18 of the 60 graphs — that is the regime the gate rejects.
* **A truncated artifact is not a local optimum, and that is a confound to
  handle, not ignore.** The cheapest way for a substrate to "exploit the
  injected artifact" is to *continue the same descent* — the PC's output is `k`
  swaps into a procedure whose model accepts ~38. B0+ must therefore be able to
  distinguish "the substrate found a general local-search capability" from "the
  substrate continued the artifact's own trajectory". The existing rule that the
  PC's source is never given to a searching agent is necessary but not
  sufficient; the coordinator should decide whether the injected object is the
  artifact's **outcome** (a partition) or its **procedure**, and whether the
  audit trail separates the two.
* **Every recorded Δ/ρ in the repository is relative to a named PC.**
  `redesign/`'s lever tables carry numbers computed against `PC_∞`, and they are
  the only one of the artifacts this bullet first named that does: earlier it
  also named `a1`'s registered T1 tree, which carries no positive-control number
  at all (**corrected 2026-09-23** — `a1/T1-EID.json` and `a1/T1.contract.json`
  do not mention `positive_control`, and neither do the files under
  `a1/kapso_t1/`). If a `k` is adopted, those numbers must either be re-run or be
  explicitly labelled as `PC_∞` numbers. They do not become wrong; they become
  numbers about a different artifact.
* **A cheaper artifact slightly relaxes the time budget.** On the calibration set
  the pooled p99 is `133–136 ms` and `PC_i`'s own p99 is `140–142 ms`; a
  truncation is faster (p50 `40 ms` at `k = 10` vs `97 ms` at `∞`,
  `tau_calibration.json`). `τ = 10 s` (see `DEVIATIONS.md` D-GATE-4, now closed)
  is unaffected by the choice — the §7 floor binds at every `k`.
* **A stronger (better) reference target makes ρ *larger*, not smaller** — ρ is
  increasing in `T_i` — so the references workstream improving `R_i` or certifying
  more optima moves the gate in the safe direction and cannot invalidate a
  `k = 10` choice made here.

---

## 8. If a `k` is adopted: the re-freeze checklist

### 8.0 Discharge status — 2026-09-23, `k = 10`

| item | status |
|---|---|
| 1. `INTERFACE.md`'s `PC_i` sentence | **open — owned by the coordinator.** The exact before/after text is in `../positive_control/PC-REVISION.md` §7 and was reported, not edited. |
| 2. the adopted candidate's frozen bytes | **done.** The candidate stays at `positive_control/variants/pc_exchange_k10/` and the *gate default* was re-pointed at it. This proposal suggested moving it to `positive_control/pc/`; the adoption deliberately did **not**, because the candidate directory's *name* keys the Outcome and verdict file paths and moving it would have rewritten every stored record for the contract PC — a decision change, where the requirement is identity-only. Keeping the bytes where they are makes the adopted verdict (`verdict.*.pc_exchange_k10.json`) *the* verdict already measured, byte for byte. |
| 3. the gate's verdicts | **done.** `gate_runner.py` re-run on dev and eval; both `ADMISSIBLE`; `values/*.pc_exchange_k10.json` re-emitted; no stored decision field moved. |
| 4. downstream artifacts computed against `PC_∞` | **out of this directory's ownership, and narrower than first written (corrected 2026-09-23).** Only `redesign/`'s lever tables were computed against `PC_∞`; the gate's own `verdict.{dev,eval}.json` and `values/{dev,eval}.positive-control.json` are the old control's files, and a few scripts carry its label (`tau_calibration.py`'s `"PC_i"` key, `seed_sensitivity.dev.json`). This row first also named `a1`'s registered T1 tree and the `C*(T1)` rows `c04_tie_a_pc_optimum` / `c05_tie_b_pc_complement`; that was false — `a1` mentions no positive control, and `c04`/`c05` are `c01_ok_high_pc`'s partition and its complement (`cut_edges` `207`, not the control's `212`), so they need no re-run. |
| 5. τ calibration | **unchanged and still valid.** `τ = 10 s` is the §7 floor, and a truncation is faster than the untruncated control (`p50 40 ms` at `k = 10` vs `97 ms` at `∞`), so the floor binds under either control. |

**Must be re-frozen** (all of it is mechanical; none of it changes a threshold):

1. `INTERFACE.md`'s statement of `PC_i` — the contract text, by its owner, not by
   this workstream. This is a **contract revision**, which is why it needs an
   explicit decision.
2. The PC candidate's frozen bytes and digests: `positive_control/variants/pc_exchange_k<K>/`
   already exists as a §4 candidate with `solution.py` + `candidate.json`, frozen
   in `positive_control/manifest.json`; promoting it means naming it as *the* PC
   (e.g. moving it to `positive_control/pc/`) and re-freezing that identity.
3. The gate's verdicts: re-run `gate_runner.py` on **dev and eval** with the new
   `--pc`, and re-freeze `verdict.*.json` / `values/*.json`. Both new verdicts
   must read `ADMISSIBLE`; a `k` that passes only on dev must be rejected, as
   §3.2 does for `k = 25`.
4. Any downstream artifact computed against `PC_∞`: `redesign/`'s lever tables
   (**corrected 2026-09-23** — this item first also named `a1`'s registered T1
   tree and the `C*(T1)` rows `c04_tie_a_pc_optimum` / `c05_tie_b_pc_complement`;
   neither carries a control number, and `c04`/`c05` are `c01_ok_high_pc`'s
   partition and its complement — see §8.0 row 4).
5. The τ calibration, re-run under the adopted PC (`python3 gates/tau_calibration.py`,
   seconds).

**Must not be changed** — by this proposal or by the adoption of it:

* `Δ` thresholds (`0.03` overall / `0.02` per family / 3-of-4),
* `ρ` thresholds (`0.30` global median / `0.30` per family median / 3-of-4),
* the saturation veto (`1/20`),
* the baseline `b_i`, the suite, `references/targets.json`, `E*`.

`INTERFACE.md` §12 forbids relaxing any pre-registered gate. This proposal keeps
every threshold exactly where it was and moves only what §12 does not protect:
the identity of the artifact.

---

## 9. Reproduce

```bash
cd a0/tasks/maxcut

# the two-set, per-family strength curve and the redesign cross-check
python3 gates/strength_table.py

# the adopted control, which the runner now uses by default — must read ADMISSIBLE
python3 gates/gate_runner.py --set dev
python3 gates/gate_runner.py --set eval

# an explicit row still names its own artifact, e.g. the runner-up
python3 gates/gate_runner.py --set dev --pc positive_control/variants/pc_exchange_k05

# the superseded local-optimum control, unchanged, for comparison — still NOT_ADMISSIBLE
python3 gates/gate_runner.py --set dev --pc positive_control/pc

# the variants are the frozen PC with one line changed; verified, not asserted
python3 positive_control/make_variants.py --check
diff positive_control/variants/pc_exchange_k10/solution.py positive_control/pc/solution.py
```

---

## 10. Residual risks, and what this proposal does not do

* **It spends a posterior degree of freedom.** §2 declares it; declaring it does
  not make it free. A reviewer who considers the freedom unspendable should
  return `NOT_ADMISSIBLE` and re-draw the suite instead — with the caveat that
  `redesign/LEVERS.md` measured the size lever as ineffective and the assignment
  that commissioned this round ruled it out.
* **It does not make the artifact more published, only weaker.** A truncation is
  a budget applied to the same pin. If the contract wants a *different published
  artifact*, that is a different proposal and no measurement here supports a
  specific one — the only other published construction measured, greedy, fails ρ.
* **The measured margins are instance-level sample estimates.** 6 graphs per
  family. The `k = 10` margin (`0.31` of ρ above the bar, on both sets, 4/4
  families on both) is far outside the ~0.10 swing the redesign measured between
  two independent draws of the same stratum; the `k = 25` margin (`0.002` above
  the bar on eval) is far inside it. That gap is the whole argument for `k = 10`
  over `k = 25`, and it is a sample statement, honestly labelled.
* **B1 and the later rounds are not designed here.** This document fixes the
  artifact-strength question and the headroom it implies; what the substrate is
  allowed to do with the artifact is the coordinator's, and §7 names the one
  confound that decision has to handle.
