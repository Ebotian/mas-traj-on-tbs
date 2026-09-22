# `a0/a1/calibration/PILOT-PROCEDURE.md` — the frozen calibration pilot and the mapping `f`

**Authority.** `a0/tasks/maxcut/INTERFACE.md` §9 (calibration and the pre-registered
mapping) and §7 (`τ`). This document is the A1 plan's item 7: *run the calibration
pilot and freeze `B_hard`*.

**Frozen before the calibration suite was touched.** Everything below — the workload,
the caps, the telemetry definitions, the estimator, the mapping `f`, the clamps and the
stopping rule — was written and committed **before** any process read a
`suite/calibration/**` byte. The order is auditable three ways:

1. the pilot's git commit is a descendant of this file's commit (`git log --follow`);
2. the sha256 of *this* document is recorded in `pilot_procedure.json`
   (`procedure.document_sha256`) and in **every** output the pilot writes, so an output
   that claims to be a pilot run of a different procedure is detectable by hashing the
   document it names;
3. the runner refuses to start a pilot when the sha256 of this file differs from the
   frozen value (`pilot.py freeze-check`, and again inside `pilot.py arm`).

The freeze exists so that the budget cannot be tuned by eyeballing results: `f` is a
function of *rates*, and the rates are only observed after `f` is fixed.

---

## 0. What the pilot is, and what it is not

* It measures **resource rates**: `CEq` per minute, harness `E*` evaluations per minute,
  and the candidate latency distribution. Nothing else.
* It uses the **calibration graph set** (`suite/calibration/**`, 12 graphs), which
  `suite/manifest.json` declares as *"resource-rate calibration only (INTERFACE.md §9);
  MUST NOT be used for any algorithmic selection"*.
* **The pilot's algorithmic results are discarded.** No score, ranking, arm comparison,
  policy, candidate or threshold anywhere in this repository is derived from a pilot
  outcome. The pilot compares the two arms only through *rate* — the two arms' scores on
  the calibration set are not used, not reported and **not published**: the committed
  evidence is a *reduction* of the run, with the score-bearing fields removed (§8), so
  that no later reader of this directory can be tempted to eyeball a calibration score
  and tune the budget by it. This sentence is repeated verbatim in every artifact the
  pilot writes (`"not_used_for_selection": true`, `"discarded_sentence"`).
* It does **not** decide admissibility, does **not** touch the task-admissibility gates,
  and does **not** relax any gate. The gate's verdict (`NOT_ADMISSIBLE`) is irrelevant
  here: `B_hard` is a resource vector and is a function of `CEq`/evaluations/seconds.
* `τ = 10 s` (the §7 floor, derived by the gate workstream's `tau_calibration.py`) is the
  value the pilot runs with. The pilot re-measures the candidate-latency distribution and
  reports whether the frozen `τ` still satisfies §7; it does not change `τ`.

---

## 1. The pilot workload

### 1.1 Units

A **unit** is one arm session on **one** calibration graph. The unit sequence is the
calculation set in the manifest's own order — the 12 `calibration/**` entries sorted by
`graph_id` (`C_0001 … C_0012`) — repeated for `passes_max = 2` passes. A pass is
complete when all 12 units of that pass have run.

Before the pilot starts, and again per unit, the driver checks the graph file's sha256
against the manifest's own `graphs[i].graph_sha256` and refuses to run on a mismatch
(`suite/manifest.json` is the identity source; the generator seed is not an identity).

### 1.2 Per-arm session parameters (the arms' own frozen configuration)

| | `A_simpleloop` | `A_kapso` |
|---|---|---|
| entry | `a0/runtimes/simpleloop/.venv/bin/python -m a0_adapter run` | `a0/runtimes/kapso/.venv/bin/python a0/a1/calibration/pilot.py kapso-inner` |
| loop depth per graph | `--max-iterations 3` | `rounds = 2` |
| model calls per unit | **2** (iterations 1 and 2; iteration 0 is the frozen `C*` baseline `c02_ok_low_baseline` and makes no call) | **2** (one ideation call per round) |
| harness `E*` evaluations per unit | **3** (1 baseline + 2 proposals) | **2** |
| model lane | the adapter's `--solver deepseek` (`ModelSolver`, the arm's declared lane) | the run's ideation seam (`chat_completion`, `a0/a1/meter_runner.py`) |
| declared token ceiling per call | the adapter's default `--model-max-tokens 2048` | `max_tokens = 256` (the T1 arm's frozen probe configuration) |
| `θ_E` | `seed=1337, timeout_s=10, fidelity=none, fraction=none` | same (`seed=1337, timeout_s=10`) |
| model | `deepseek-flash`, `temperature=0` | `deepseek-flash`, `temperature=0` |

Both arms' loop depth is a *workload* parameter of the pilot (neither arm's frozen policy
declares an iteration count). It is fixed here, before the run, at the smallest depth
that yields two model calls and two-to-three evaluations per unit; the value is not
revisited after the rates are seen.

The KAPSO unit is one process per graph (one `build_runtime` + `prepare` per unit), the
same shape as `a0/a1/kapso_t1/probes/live_t1.py`; the difference is that the pilot binds
the harness's `graph_path` to a calibration graph, rebases the adapter's `state_root`
into the pilot's own work directory (so no sibling workstream's directory is written),
and does **not** memoise the second round's model call (the probe memoised it to save
cents; a rate measurement must observe the arm's actual call pattern).

### 1.3 What the model actually does

`A_simpleloop` runs its real lane: the graph's edge list is part of the prompt and the
model's answer becomes the proposed partition, which the **harness** evaluates. The
harness, not the arm, runs `E*` in both arms (`--eval-mode harness` / `HarnessEvalClient`),
and the arm consumes the published Outcome.
`A_kapso` runs the T1 configuration of `a0/a1/kapso_t1/`: the implementation seam writes
a frozen `C*(T1)` member (no coding-agent session), while the ideation seam makes the real
metered model call. The measured KAPSO rate is therefore the rate of **that declared
configuration**; a configuration with real implementation sessions would consume more per
round. This is stated again in `B_hard.json` and `README.md` as a scope limit.

---

## 2. Hard caps (pilot-enforced, declared before the run)

| cap | `A_simpleloop` | `A_kapso` | why this number |
|---|---|---|---|
| `T_pilot,wall` | **900 s** | **900 s** | the assignment's ≤ 15 min per arm |
| `CEq_pilot_max` | **1,200,000** | **300,000** | a-priori bound on the planned workload × 2: `A_simpleloop`'s `--model-max-tokens 2048` bounds one call at `4·2048 = 8192` completion-`CEq` plus a prompt bounded by the graph's edge list (≤ 636 edges ≈ 8 k characters ≈ 3 k tokens, the template is fixed) → `≤ 12,000` per call × 48 planned calls ≈ 576,000; `A_kapso`'s `max_tokens 256` bounds one call at `1024 + miss ≤ ~5,000` × 48 planned calls ≈ 240,000. The caps are ~2× and ~1.25× those a-priori bounds: they are safety ceilings, not budgets to spend. |
| `N_E,pilot_max` | **288** | **192** | 4× the planned 72 / 48 evaluations: a runaway on the evaluation lane is caught even if `CEq` stays low |
| `P_concurrency` | 1 | 1 | the closed topology runs one arm, one in-flight evaluation |

Every cap is read from the **harness's own sources** before each unit
(`a0/a1/budget.py::BudgetEnforcer`): `CEq` from the `a0/meter` ledger, `N_E` from the
harness evaluation ledger, wall time from the harness's monotonic clock. The runtime's
self-report is diagnostic only. The first check that fails stops the workload
(fail-closed), and the stop reason is recorded. The driver additionally passes the arm's
own `--budget` (a runtime-side self-check) a value below the remaining harness cap so a
well-behaved arm exits by itself.

---

## 3. Telemetry (measured, per arm `r`)

Let `T_r` be the harness's monotonic wall time from the launch of the arm's first unit
to the exit of its last unit (seconds), `CEq_r` the sum of `ceq` over the rows of the
`a0/meter` ledger whose `campaign_id` is this arm's pilot campaign and `unmetered` is
false, and `N_E,r` the number of rows in the harness evaluation ledger for that campaign.
`T_r` is quantised to microseconds (`round(T·10^6)/10^6`) so that the exact rational
`q_r` is a function of the recorded decimal and not of a float's binary expansion; `q_r`
and `e_r` are exact `Fraction`s and the only rounding anywhere in `f` is the single
`ceil` at the end of each coordinate (§4).

| symbol | definition | unit |
|---|---|---|
| `T_r` | harness monotonic wall of the workload | s |
| `CEq_r` | Σ `ceq` over metered rows (meter ledger, campaign-scoped) | CEq |
| `N_E,r` | harness `E*` evaluator calls (harness eval ledger) | count |
| `q_r` | `60 · CEq_r / T_r` | CEq/min |
| `e_r` | `60 · N_E,r / T_r` | evals/min |

### 3.1 Variance (required by §9: "must report the pilot's own variance")

Two estimators, both frozen here, both reported for both arms:

* **per-unit** — for each unit `u` (one arm session on one graph): `T_u` (harness
  monotonic, around the unit), `CEq_u` and `N_E,u` by ledger-row timestamp attribution
  (a row belongs to the unit whose `[start, end]` wall interval contains its `ts`), and
  `q_u = 60·CEq_u/T_u`, `e_u = 60·N_E,u/T_u`. Report `n`, mean, **sample** standard
  deviation (`n−1`), `cv = sd/mean`, min, median, max. Attribution is asserted
  exhaustive: every ledger row of the campaign is attributed to exactly one unit, and the
  per-unit model-call/evaluation counts are compared against §1.2's expectation as a
  diagnostic.
* **per-window** — non-overlapping 60 s windows anchored at the arm's launch epoch;
  per window the `CEq` and evaluation counts of the rows whose `ts` falls in the window.
  Only **full** windows (entirely inside the workload interval) participate in
  `max_window_rate` and `mean_window_rate`; a trailing partial window is reported but
  excluded from those two statistics.

### 3.2 Latency

For every evaluation in the campaign: the **candidate** wall time
(`interpreted.wall_ms` of the Outcome the harness authored) and the harness-side `E*`
call wall time (`wall_sec` of the harness ledger row). Report `n`, min, p50, p95, p99,
max with the **nearest-rank** percentile definition
(`ceil(p·n)`-th smallest), the same definition the gate's `tau_calibration.py` uses.
The §7 cross-check is `τ_frozen = 10 s` vs `10·p99_candidate`: if `10·p99 < 10 s` the
floor binds and the frozen `τ` remains the §7 value. Reported, never changed here.

---

## 4. The mapping `f(telemetry) → B_hard` (frozen)

`B_hard = (T_wall_sec, CEq_max, N_evaluatorCalls, P_concurrency)`, exactly the vector
`a0/a1/budget.py::Budget` enforces.

```
T_wall_sec      = 1800                     # §9's design constant: the primary constraint
q_r             = 60 · CEq_r / T_r          # CEq/min, exact rational
e_r             = 60 · N_E,r / T_r          # evals/min, exact rational
C_r             = 30 · q_r                  # CEq a 30-minute campaign consumes at this rate
E_r             = 30 · e_r                  # evaluations a 30-minute campaign makes at this rate
CEq_max         = min( ceil( (5/4) · max_r C_r ),  CEQ_CEILING   = 5_000_000 )
N_evaluatorCalls= min( ceil( (5/4) · max_r E_r ),  N_E_CEILING   = 5_000     )
P_concurrency   = 1
```

`max_r` is over the two arms. The `5/4 = 1.25` factor and the 30-minute window are §9's
declared defaults ("`CEq_max = 1.25 ×` the normal 30-minute consumption,
`N_E,max = 1.25 ×` the observed suite evaluations"); the primary constraint `T_wall` is
the designed 30 minutes and is **not** measured — a pilot cannot measure a constant it
is given.

**Ceilings (frozen constants, not measurements).** `CEQ_CEILING = 5,000,000` and
`N_E_CEILING = 5,000` bound the vector so that a pathological pilot rate cannot freeze an
unbounded budget: 5 M `CEq` is ~0.6 M completion tokens (cents at `deepseek-flash`
prices, and a spend beyond "cents" for one campaign would be a different design), and
5,000 evaluations of `E*` at the measured per-evaluation cost would already consume more
than `T_wall` on the evaluation lane alone. If either clamp is active, the artifact says
so and reports which arm's rate drove it.

**Required properties, mechanically checked by `pilot.py apply` and by `verify.py`:**

1. **Monotone** — `f` is non-decreasing in every `q_r` and `e_r`; the clamp is a `min`
   with a constant, which preserves monotonicity. Checked by evaluating `f` at rates
   scaled by `0.5×, 1×, 2×, 4×` and asserting no coordinate ever decreases.
2. **Bounded** — `T_wall_sec = 1800`, `CEq_max ≤ CEQ_CEILING`,
   `N_evaluatorCalls ≤ N_E_CEILING`, `P_concurrency = 1`, all positive integers.
3. **Variance reported** — `B_hard.json` embeds §3.1's per-unit and per-window statistics
   for both arms; `apply` refuses to write a `B_hard` whose telemetry lacks them.
4. **Total and provenance-carrying** — defined for any finite telemetry with `T_r > 0`;
   `B_hard.json` records the procedure document's sha256, the runner's sha256, the
   manifest sha256, the calibration graph set's `(graph_id, sha256)` list, both
   campaigns' ledger sha256, and the per-arm raw telemetry hashes, so `B_hard` is
   re-derivable from the inputs it names (`verify.py` re-derives it and compares).

`f` is applied **mechanically**: `pilot.py apply` reads only the committed telemetry and
ledgers, computes the formula above, and writes `B_hard.json`. No human or model edits a
number in between; re-running `apply` on the same inputs must reproduce the same file
byte for byte.

---

## 5. The pilot's own stopping rule (frozen)

The workload stops at the **first** of:

1. `passes_max = 2` complete passes over the 12 calibration graphs (the planned workload);
2. `T_pilot,wall = 900 s` of harness monotonic time;
3. the arm's `CEq_pilot_max` (or `N_E,pilot_max`) being exceeded, as read by the
   `BudgetEnforcer` **before** launching the next unit;
4. a unit failing in a way that makes the workload meaningless (the arm cannot run at
   all inside the closed topology).

Stop reason 1 is `workload_complete: true`; reasons 2–3 are recorded with the unit index
and the observed `CEq`/`N_E`/wall at the stop, and the telemetry remains valid for a rate
estimate as long as §6's validity conditions hold.

---

## 6. Validity conditions — when no `B_hard` may be frozen

`pilot.py apply` refuses to emit a `B_hard` (exit non-zero, and a
`B_hard_REFUSED.json` naming the reason) unless **all** of these hold for both arms:

| # | condition | why |
|---|---|---|
| V1 | `sha256(PILOT-PROCEDURE.md) == pilot_procedure.json.procedure.document_sha256` | the freeze ordering |
| V2 | every graph used matched the manifest's `graph_sha256` | the workload is the calibration set, by data identity |
| V3 | zero **gap** `unmetered` rows in the pilot campaigns' meter rows (`a0/meter/verify_ledger.py` exits 0 on the ledger) | §8: without usage the campaign's `CEq` is not established; never estimated |
| V4 | `T_r > 0` and at least 12 units completed per arm (one full pass) and `T_r ≥ 120 s` | a rate needs a measured interval |
| V5 | every metered row reports `model_reported == "deepseek-flash"` | the model family is a `CID` factor; a different model is a confound, not a rate |
| V6 | the harness evaluation ledger's rows all name a calibration graph sha256 | the evaluations are the workload's |
| V7 | the campaign ids and arm ids match the pilot's frozen names | attribution cannot be smeared across campaigns |

A **low** rate is not an invalidity and never triggers a refusal: validity is about the
measurement being established, not about its magnitude. `B_hard` may therefore come out
large; if it does, the report says so, with the margins of §7.

---

## 7. Diagnostics the report must state (§9's "are the guardrails sensible?")

| id | quantity | meaning |
|---|---|---|
| D1 | `margin_CEq_minutes = CEq_max / q_r` | how long a campaign may run at the measured rate before the `CEq` guardrail binds. By construction this is `37.5 min` unless a clamp is active; it must be compared against `T_wall = 30 min` |
| D2 | `margin_NE_minutes = N_E,max / e_r` | the same for the evaluation guardrail |
| D3 | `worst_window_ratio = max_window_rate / q_r` (and the same for `e_r`) | if `worst_window_ratio > 1.25`, a rate spike of the size the pilot itself observed, sustained, would bind the guardrail before `T_wall` — i.e. the guardrail could manufacture a false negative. Reported per arm, per quantity |
| D4 | the §3.2 `τ` cross-check | whether the frozen 10 s still satisfies §7's formula on the arm's own candidates |
| D5 | the per-arm `CEq` per model call (min/median/max) and the completion-token distribution | the rate's composition, so a reader can see whether `q_r` is driven by prompt or by completion |

If D1 or D2 is below `30 min`, or D3 exceeds `1.25`, the report must say so **plainly**
and must not freeze a budget that manufactures a false negative; if the guardrails would
bind in the first minutes, that is the headline, not a footnote.

---

## 8. Outputs

| path | what |
|---|---|
| `pilot_procedure.json` | the machine-readable copy of this document's numbers, with `procedure.document_sha256` |
| `evidence/<arm>/pilot_arm.json` | one pilot campaign's published record: workload, caps, per-unit rows, ledger attribution, variance, latency, checks, verdict |
| `evidence/<arm>/outcomes/<seq>_<request_id>.json` | the harness-authored Outcome of every pilot evaluation, **reduced** (the latency source) |
| `evidence/<arm>/harness_ledger.jsonl` | the harness evaluation ledger of that campaign, **reduced** |
| `evidence/<arm>/meter_ledger.jsonl` | that campaign's `a0/meter` ledger, **verbatim** — it is the spend record and carries no score |
| `ledger.jsonl` | the pilot's `a0/meter` ledger at the root: the two campaigns' rows concatenated in time order (real `ceq`, `unmetered: false`) |
| `evidence/rehearsal.json` | the model-free plumbing rehearsal (dev graph, zero spend, `mode: "rehearsal"`, never an input to `f`) |
| `evidence/unmetered_counterexample.json` | an induced missing-usage response, its `unmetered` row, and the enforcer's `budget_exhausted:unmetered_model_call` verdict (a separate probe campaign, not part of the pilot's totals) |
| `B_hard.json` | the frozen vector, the telemetry it came from, `f`'s properties, and §7's diagnostics |
| `README.md` | the report: verdicts, evidence, spend, scope limits |

**The reduction (§0's "not published").** The harness ledger and the Outcomes carry the
objective's value on the calibration graphs (`true_value`, `handed_value`, `cut_edges`,
`cut_fraction`). Those fields are removed from every published file; each published
artifact names the removed keys, and the raw files' sha256 (taken before the reduction, in
the run directory) are recorded next to the reduced ones, so the reduction is auditable
where the raw bytes live. Nothing `f` needs is removed: `ts`, `campaign_id`, `arm_id`,
`candidate_source_sha256`, `graph_sha256`, `status`, `wall_sec` and the Outcome's
`interpreted.wall_ms` all survive, so every rate, every unit attribution and every latency
percentile is still re-derivable from the published evidence alone. Arm stdout/stderr are
not published either; they are recorded as `sha256` plus byte length and `exit_code`.

Every published artifact carries `"procedure_sha256"`, `"runner_sha256"` and
`"not_used_for_selection": true`.

**`apply` reads only published evidence.** It re-derives `CEq_r` from
`evidence/<arm>/meter_ledger.jsonl` and `N_E,r` from
`evidence/<arm>/harness_ledger.jsonl` (counting rows, not trusting the telemetry), checks
them against the telemetry the runner recorded, and refuses on any disagreement. So
`B_hard.json` is a function of the committed evidence files and nothing else, and
re-running `apply` over the committed evidence must reproduce it byte for byte.

---

## 9. Non-goals

* No score, ranking or comparison of the arms on the calibration set.
* No change to `τ`, to any threshold, or to any gate; no use of the `dev` or `eval` sets
  in the pilot's workload (`eval` is additionally never materialised anywhere the arms
  can read: the pilot's graphs are `calibration/**` and the harness reads them; the arms
  are only handed the path they are asked to partition).
* No modification of upstream runtimes or of another workstream's files.
* No claim beyond resource rates: `B_hard` bounds *consumption*, not *quality*.
