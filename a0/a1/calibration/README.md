# `a0/a1/calibration/` — the A1 calibration pilot: `B_hard` frozen from measured rates

This directory is the A1 plan's item 7 ("run the calibration pilot and freeze `B_hard`").
`a0/tasks/maxcut/INTERFACE.md` §9 is the binding authority; `PILOT-PROCEDURE.md` is the
frozen procedure and `pilot_procedure.json` its machine-readable copy. Departures are
recorded one by one in `DEVIATIONS.md` (this directory's own).

## 0. Bottom line, in the order the assignment asked for it

| # | step | verdict | evidence |
|---|---|---|---|
| 1 | **use the frozen procedure unchanged** | **DONE** — used unchanged; `PILOT-PROCEDURE.md` still hashes to `68af1321…`, re-checked on every run | `pilot.py freeze-check`, `calibration/verify.py` step `freeze` |
| 2 | **one bounded campaign per arm**, closed topology, calibration graphs only | **PASS** — 24/24 units each, `stop_reason: workload_complete`, every campaign check `true` | `evidence/<arm>/pilot_arm.json`, `evidence/<arm>/meter_ledger.jsonl`, `evidence/<arm>/harness_ledger.jsonl` |
| 3 | **apply `f` mechanically and freeze `B_hard`** | **FROZEN** — `B_hard.json` (sha256 `fd15d9ec…`), V1–V7 hold, `f`'s four required properties hold, no clamp active | `B_hard.json` §6 below |
| 4 | **the real ledger rows** | 95 rows, 0 `unmetered`; per-arm totals 370 881 / 52 992 `CEq`; one induced `unmetered` counter-example | `ledger.jsonl`, `evidence/<arm>/meter_ledger.jsonl`, `evidence/unmetered/` |
| 5 | **scope limits stated** | 4 in `B_hard.json`, 4 more below | §9 |
| — | **spend** | **423 941 CEq** total, from the ledger (`a0/meter`), `deepseek-flash` | §7 |

**The frozen vector.**

```
B_hard = (T_wall_sec = 1800,          # §9's designed primary constraint, not measured
          CEq_max = 1_966_519,        # = ceil(1.25 x 30 x max_r q_r);  A_simpleloop drives it
          N_evaluatorCalls = 725,     # = ceil(1.25 x 30 x max_r e_r);  A_kapso drives it
          P_concurrency = 1)
```

## 1. What is here

| path | what it is |
|---|---|
| `PILOT-PROCEDURE.md` | the frozen procedure: workload, caps, telemetry definitions, variance estimators, `f`, its required properties, the stopping rule, validity V1–V7, diagnostics D1–D5 |
| `pilot_procedure.json` | the machine-readable copy, carrying the document's own sha256 (the runner refuses to run when it does not match) |
| `pilot.py` | the runner: the two campaigns, the arm commands, the KAPSO inner driver, `publish` (the reduction), `apply` (`f`), the metering proof, the unmetered counter-example |
| `verify.py` | **the one command**: everything model-free, re-established (§8) |
| `tests/test_pilot.py` | 24 invariants: `f`'s formula, monotonicity, boundedness, clamp, V1–V7, percentile/`sd` definitions, the reduction |
| `B_hard.json` | **the frozen vector**, its `f` arithmetic, `f`'s properties, the variance, §7's diagnostics, the scope limits, and the digests of everything it came from |
| `ledger.jsonl` | the two pilot campaigns' `a0/meter` rows, concatenated in time order (95 rows) |
| `evidence/` | the published run: per-arm `pilot_arm.json` + verbatim meter ledger + reduced harness ledger + reduced Outcomes (70 + 48), `rehearsal.json`, the metering proof, the unmetered counter-example, `INDEX.json` — 131 files |
| `tau_cross_check.json` | the §7 `τ` cross-check, read from the resources sidecar because the frozen clause's field is null by design (**D-CAL-7**); labelled, not part of the re-derivable evidence set, not an input to `f` |
| `history/attempt1-blocked-identity-drift/` | the previous attempt, archived (**D-CAL-9**) |
| `DEVIATIONS.md` | every departure from a frozen document, with its reason |

## 2. The freeze, and why the ordering is auditable

`PILOT-PROCEDURE.md` was written, its sha256 recorded in `pilot_procedure.json`, and both
committed (`3e62d588`) **before** anything in this directory read a `suite/calibration/**`
byte. Three mechanisms keep that auditable:

* the runner refuses to start when the document does not hash to
  `pilot_procedure.json.procedure.document_sha256` (`freeze-check`, and again inside
  `arm`); the check re-ran on this run and reports `the_procedure_document_is_the_frozen_one: true`
  for both campaigns;
* every artifact carries `procedure.document_sha256` and `runner.sha256`;
* `verify.py`'s `budget` step re-derives `B_hard.json` from the published evidence and
  requires byte-identical output.

The document was **not edited** for this run (sha256 `68af13211ab88aad1fe4b3ca40d29cf00e73f2139d78ae5b26fe8fc47a0e3fa2`
before and after). The one clause that cannot be applied to the current tree is named in
**D-CAL-7** and reported as a supplement rather than by amending the freeze.

## 3. The pilot: what ran

Both campaigns ran inside `unshare -rn`, with the campaign's own metering proxy, the
harness evaluation service and the unix-socket hop — the same boundary the paid arms use.
Each ran its **full workload of 24 units** (2 passes × 12 calibration graphs, in manifest
order `C_0001 … C_0012`), every graph's sha256 checked against `suite/manifest.json` before
it was handed to the arm.

| | `A_simpleloop` | `A_kapso` |
|---|---|---|
| campaign id | `C_calib_A_simpleloop` | `C_calib_A_kapso` |
| verdict / stop reason | `pass` / `workload_complete` | `pass` / `workload_complete` |
| units completed | 24 / 24 | 24 / 24 |
| exit codes | 23 × `0`, 1 × `8` (fail-closed, see below) | 24 × `0` |
| model calls / evaluations | 47 / 70 | 48 / 48 |
| `T_r` (wall of the workload) | **424.34501 s** | **149.108791 s** |
| `CEq_r` | **370 881** | **52 992** |
| `N_E,r` | **70** | **48** |
| failed campaign checks | none | none |

Topology, measured from inside each campaign's namespace: direct egress to `1.1.1.1`,
`8.8.8.8` and `123.148.116.184` is `BLOCKED:OSError`, the campaign's metered port is
`REACHED` over the unix socket. Both arms reached the harness; both report
`frozen_identity.consistent: true` with `EID* = 7ce9e72f…` and
`evaluator_source_sha256 = dc6969ec…` on every ledger row and Outcome.

**The one `exit 8` unit.** `A_simpleloop`, unit 20 (pass 1, `C_0009`), exited `8` — the
adapter's fail-closed code — with `search_failed 1` in its traces; the unit made 1 model
call and 1 evaluation instead of 2 and 3. It is a genuine observation about the arm's
behaviour, not a harness or identity fault: the campaign continued, all 24 units are
present, and the per-unit variance below includes it. It is the reason `A_simpleloop`'s
counts are 47/70 rather than 48/72.

## 4. Where the calibration set was used, and where it was not

* **Used for resource rates only** — `CEq`/min, evaluations/min, the candidate latency
  distribution.
* **Not evaluated for quality, not ranked, not scored for any decision.** No candidate,
  arm, policy or threshold anywhere in this repository was chosen from a pilot result.
* **Published evidence is a reduction.** The harness ledger and the Outcomes carry the
  objective's value on the calibration graphs (`true_value`, `handed_value`, `cut_edges`,
  `cut_fraction`); `publish` removes them, records which keys were removed and why, and
  keeps every field a rate needs (`ts`, `campaign_id`, `arm_id`,
  `candidate_source_sha256`, `graph_sha256`, `status`, `wall_sec`). Arm stdout/stderr are
  published as sha256 + byte length + exit code. `verify.py` re-checks this structurally
  over every published file: **131 files, 0 findings**.
* The reduction is auditable where the raw bytes live: `evidence/INDEX.json` records each
  raw file's sha256 next to the reduced file's.

## 5. Ledger excerpts (real, from `a0/meter`)

One row per upstream call, 95 rows across the two campaigns, **no row `unmetered`**, every
row re-derived by `a0/meter/verify_ledger.py` (`ceq = miss + floor(hit×2/100) + 4×completion`).

`A_simpleloop` — first and last rows of `evidence/simpleloop/meter_ledger.jsonl` (47 rows,
`ceq` total **370 881**):

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_A_simpleloop","arm_id":"A_simpleloop","ts":"2026-09-22T21:05:56.712117+08:00","provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-flash","model_reported":"deepseek-flash","provider_request_id":"538d25c2-b511-4f36-9583-5ffe820064cd","stream":false,"usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":1112,"completion_tokens":2048},"ceq":9304,"unmetered":false,"reason":null}
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_A_simpleloop","arm_id":"A_simpleloop","ts":"2026-09-22T21:12:50.031501+08:00","provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-flash","model_reported":"deepseek-flash","provider_request_id":"4d8f6803-b6bb-42a4-813e-6d7b0473bbc2","stream":false,"usage":{"prompt_cache_hit_tokens":2048,"prompt_cache_miss_tokens":152,"completion_tokens":1098},"ceq":4584,"unmetered":false,"reason":null}
```

`A_kapso` — first and last rows of `evidence/kapso/meter_ledger.jsonl` (48 rows, `ceq`
total **52 992**):

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_A_kapso","arm_id":"A_kapso","ts":"2026-09-22T21:12:54.398495+08:00","provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-flash","model_reported":"deepseek-flash","provider_request_id":"799e62c8-efa5-401e-9931-81971c69b7db","stream":false,"usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":80,"completion_tokens":256},"ceq":1104,"unmetered":false,"reason":null}
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_A_kapso","arm_id":"A_kapso","ts":"2026-09-22T21:15:20.042559+08:00","provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-flash","model_reported":"deepseek-flash","provider_request_id":"26608d53-b2da-410a-94e6-fd61fc5dc64a","stream":false,"usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":80,"completion_tokens":256},"ceq":1104,"unmetered":false,"reason":null}
```

Every row reports `model_reported: "deepseek-flash"` and `provider: "deepseek"`
(47/47 and 48/48). The published ledger files are **byte-identical to the meter's own
files** (raw sha256 `0c847c46…` / `3a7b1fb6…`, recorded for both in `INDEX.json` under
`raw_sha256` and `files`) — **D-CAL-8** explains why that took a runner fix.

**One separately labelled proof call** (`evidence/meter-proof/`, campaign
`C_calib_meter_proof`, not part of any pilot total): a real in-namespace call,
`ceq = 36 + floor(0×2/100) + 4×8 = 68`, re-derived by the meter's verifier with direct
egress `BLOCKED` from the same namespace.

**The induced missing-usage counter-example** (`evidence/unmetered/`, campaign
`C_calib_unmetered_probe`): a request for a model that does not exist returns 4xx with no
`usage` field — a *gap*, not a refusal:

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_unmetered_probe","arm_id":"A_calib_probe","ts":"2026-09-22T21:18:04.891121+08:00","provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-does-not-exist-a0-calibration","model_reported":null,"provider_request_id":null,"stream":false,"usage":null,"ceq":null,"unmetered":true,"reason":"upstream_http_401_no_usage"}
```

and `a0/a1/budget.py::BudgetEnforcer` stops the campaign on it —
`stopped_because: "budget_exhausted:unmetered_model_call"` — rather than estimating the
spend (§8).

## 6. `B_hard`: the rates, the arithmetic, the variance, the guardrails

**Rates** (exact rationals; `q_r = 60·CEq_r/T_r`, `e_r = 60·N_E,r/T_r`):

| arm | `T_r` (s) | `CEq_r` | `N_E,r` | `q_r` (CEq/min) | `e_r` (evals/min) |
|---|---|---|---|---|---|
| `A_simpleloop` | 424.34501 | 370 881 | 70 | **52 440.489** | **9.898** |
| `A_kapso` | 149.108791 | 52 992 | 48 | **21 323.491** | **19.315** |

**`f` applied mechanically** (procedure §4; no number was edited by hand):

```
CEq_max          = ceil(1.25 × 30 × max_r q_r) = ceil(1.25 × 30 × 52440.48940271502) = 1_966_519   [A_simpleloop]
N_evaluatorCalls = ceil(1.25 × 30 × max_r e_r) = ceil(1.25 × 30 × 19.314756565895568) =    725   [A_kapso]
T_wall_sec       = 1800                                                              (the design constant)
P_concurrency    = 1
```

Neither ceiling clamp (`5 000 000`, `5 000`) is active. `f`'s required properties are all
`true`: **monotone** (evaluated at rates × 0.5/1/2/4 → `983 257 / 1 966 519 / 3 933 037 /
5 000 000`, never decreasing), **bounded**, **variance reported**, **total**. V1–V7 hold
with no failures, and `a0/a1/budget.py::Budget` loads the vector unchanged.

**Variance** (procedure §3.1; sample `sd`, `n−1`; nearest-rank percentiles):

| | `A_simpleloop` | `A_kapso` |
|---|---|---|
| per-unit `CEq` rate (CEq/min): mean / sd / **cv** | 52 567.2 / 5 869.5 / **0.112** | 21 503.3 / 1 885.4 / **0.088** |
| per-unit `CEq` rate: min / median / max | 42 651.3 / 51 199.4 / 64 971.5 | 16 326.5 / 21 684.5 / 24 179.7 |
| per-unit `N_E` rate (evals/min): mean / sd / cv | 10.124 / 2.197 / **0.217** | 19.478 / 1.708 / **0.088** |
| per-unit seconds: mean / sd / cv / max | 17.681 / 3.323 / 0.188 / 23.765 | 6.212 / 0.619 / 0.100 / 8.114 |
| 60 s windows: full / max / mean (CEq rate) | 7 / 59 216 / 52 328.1 | 2 / 20 976 / 20 976 |
| 60 s windows: full / max / mean (`N_E` rate) | 7 / 11 / 9.857 | 2 / 19 / 19 |
| attribution exhaustive | `true` (370 881 CEq, 70 rows) | `true` (52 992 CEq, 48 rows) |

Both arms are reasonably tight: `cv ≈ 0.09–0.11` on the `CEq` rate, `0.22` on
`A_simpleloop`'s `N_E` rate (the one fail-closed unit is the bulk of that spread). The
per-unit model-call/evaluation counts match §1.2's expectation everywhere except unit 20.

**D5 — what the rate is made of.** `A_simpleloop`: 7 891 `CEq`/call mean, median 8 437,
min 2 505, max 10 868; **33 of 47 calls hit the declared `--model-max-tokens 2048`**, the
rest 565–2 030. `A_kapso`: **1 104 `CEq`/call, all 48 calls identical** (completion always
exactly 256 = its `max_tokens`, 80 miss tokens, no cache hits). So both rates are driven by
the arm's *declared token ceiling*, not by the graph or by the task's difficulty.

**D1/D2/D3 — are the guardrails sensible?** Yes, by the procedure's own test:

| | `A_simpleloop` | `A_kapso` |
|---|---|---|
| D1 `CEq_max / q_r` | 37.50 min | 92.22 min |
| D2 `N_E,max / e_r` | 73.25 min | 37.54 min |
| D3 worst observed 60 s window / mean (`CEq`, `N_E`) | 1.132 / 1.116 | 1.000 / 1.000 |

Every margin exceeds `T_wall = 30 min`, so **no guardrail binds before the wall-clock
constraint** — the intended design — and the largest rate spike the pilot itself observed,
sustained for a whole campaign, stays under the 1.25 bound (D3 ≤ 1.132 < 1.25). The
guardrails would therefore not manufacture a false negative. Note that the two coordinates
are driven by **different arms**: `CEq_max` by `A_simpleloop` (it spends 7.1× more per
minute) and `N_E,max` by `A_kapso` (its units are ~3× faster, so it makes evaluations
faster).

**D4 — the `τ` cross-check.** Reported as `null` by the frozen procedure, because the field
it names is null in the frozen `E*`: **D-CAL-7**. Measured from the resources sidecar and
published in `tau_cross_check.json`: candidate wall time n/min/p50/p95/p99/max =
140/31/33/34/**36**/37 ms (`A_simpleloop`) and 96/31/33/35/**38**/38 ms (`A_kapso`), so
`10·p99 = 0.36 s` / `0.38 s` — **below the 10 s floor**, i.e.
`τ = min(30 s, max(10 s, 10·p99)) = 10 s`, unchanged and in agreement with the gate
workstream's frozen value. Reported, never changed.

**The size of `CEq_max`, stated plainly.** 1 966 519 `CEq` is a *30-minute extrapolation* of
a 7.07-minute measurement — ~5.3× what `A_simpleloop` actually consumed in the pilot and
~37× KAPSO's. That is what §9's frozen formula produces and it was frozen before any
calibration byte was read; the margins above are the check on it, and they pass. The
*pilot's* own caps were much smaller and did not bind: 1 200 000 / 300 000 `CEq` and
288 / 192 evaluations against actual 370 881 / 52 992 and 70 / 48. Recorded as **D-CAL-10**.
No gate threshold was touched.

## 7. Spend (from the ledger, not self-reported)

| campaign | rows | unmetered | `CEq` |
|---|---|---|---|
| `C_calib_A_simpleloop` (pilot) | 47 | 0 | **370 881** |
| `C_calib_A_kapso` (pilot) | 48 | 0 | **52 992** |
| `C_calib_meter_proof` (one tiny in-namespace call) | 1 | 0 | **68** |
| `C_calib_unmetered_probe` (induced 4xx) | 1 | 1 | `null` (not estimable by design) |
| rehearsals (`--no-model` / injected solver) | 0 | 0 | **0** |
| **total for this workstream** | | | **423 941 CEq** |

Model `deepseek-flash`, temperature 0, everything through `a0/meter`. The key was read into
the environment in the same command that used it and was never printed, logged or written
to an artifact.

## 8. The one command a third party reruns

```bash
python3 a0/a1/calibration/verify.py --with-rehearsal     # exit 0 = every claim re-established
```

Last run, exit 0, every step `PASS`:

```
PASS freeze        procedure 68af13211ab88aad… · 12 calibration graphs verified against the manifest · caps 1200000/300000 CEq
PASS tests         24 passed in 0.05s
PASS budget        byte-identical from the evidence · vector CEq_max=1966519 N_E,max=725 T_wall=1800s
PASS ledgers       C_calib_A_simpleloop: 47 rows, ceq 370881 · C_calib_A_kapso: 48 rows, ceq 52992 · root ledger.jsonl == concat (95 rows)
PASS meter-evidence in-namespace metered call: ceq=68 (…) · counter-example: unmetered row, reason=upstream_http_401_no_usage, ceq=null, budget stopped
PASS reduction     131 published files, none uses an objective value on a calibration graph as data
PASS budget-loads  a0/a1/budget.Budget(T_wall_sec=1800.0, N_eval_max=725, CEq_max=1966519, P=1)
PASS f-properties  V1–V7 hold · monotone+bounded+variance reported+total · A_kapso: margins 92.2/37.5 min · A_simpleloop: margins 37.5/73.3 min
PASS rehearsal     both arms reached the harness through the closed topology, model calls skipped: 8 evaluations, 0 CEq
verdict: pass
```

It re-establishes, in order: the freeze ordering; the 24 model-free invariants; that
`B_hard.json` is **reproducible byte-for-byte** from the committed evidence; that the
meter's own verifier re-derives every published row and that none is `unmetered`; that the
metered proof call and the induced `unmetered` counter-example are what they claim; that no
published file uses an objective value on a calibration graph as data; that the skeleton's
`Budget` loads the vector; that V1–V7 and `f`'s properties hold; and — with
`--with-rehearsal` — the closed topology, measured. The paid campaigns are **not** re-run
(they spend money).

The precondition this run waited for is the A1 harness's own verifier:

```bash
python3 a0/a1/verify.py            # exit 0, {"verdict":"pass"}, all six steps true
```

## 9. Scope limits

Stated in `B_hard.json.scope_limits`, plus four this run made visible:

1. **Resource rates only.** `B_hard` bounds *consumption*, never *quality*.
2. **The KAPSO rate is the rate of its declared T1 configuration** — the frozen `C*(T1)`
   implementation seam with one metered ideation call per round, no coding-agent session.
   A configuration with real implementation sessions would consume more per round.
3. **Both rates are set by the arms' declared token ceilings, not by the task.** 33/47
   `A_simpleloop` calls and 48/48 `A_kapso` calls hit their `max_tokens` exactly (2 048 and
   256). Scaling either declared ceiling scales `q_r` linearly.
4. **The calibration graphs are used for rates only**; no score on them was used, reported
   or published.
5. **`q_r` is measured at 128 nodes / ≤636 edges.** The SimpleLoop prompt carries the edge
   list, so a larger graph set would raise the prompt side of `q_r`; the completion side is
   already pinned at the ceiling and would not grow.
6. **`e_r` couples evaluations to the arm's loop shape**, not to a pure evaluation cost:
   `A_simpleloop`'s 3 evaluations per unit include a baseline (iteration 0) that makes no
   model call, while `A_kapso`'s 2 are both proposal evaluations.
7. **One unit failed closed** in `A_simpleloop` (unit 20, exit `8`, `search_failed`). The
   rate is the rate of the arm *including* its failure path, not of a hypothetical
   always-succeeding arm.
8. **`A_simpleloop`'s workload is not the workload the gate exercised.** The procedure fixes
   `--max-iterations 3` as a *pilot* workload parameter ("neither arm's frozen policy
   declares an iteration count"); a campaign at a different depth would have a different
   `q_r` per unit but roughly the same per-call cost.

## 10. What I could not verify (stated plainly)

1. **The A1 contract revision is not mine to make.** Whether to adopt a bounded-round
   positive control so the headroom gate can pass is the user's decision; nothing here
   touches it. The gate's verdict (`NOT_ADMISSIBLE` at this run; `ADMISSIBLE` since the
   2026-09-23 revision of the positive control) was not read as a target and no
   threshold was moved.
2. **D4 is not re-derivable from the committed evidence** (D-CAL-7): the `τ` cross-check
   reads the resources sidecar, which the reduction does not publish. `tau_cross_check.json`
   carries the numbers and their provenance; `verify.py` does not claim to re-derive them.
3. **The campaign-time runner is not the current runner.** The published
   `pilot_arm.json` files record `runner.sha256 = 5034b91e…` (the revision that ran the
   campaigns, including its own `the_runner_is_the_committed_one: true` check, which was
   true at campaign time), while `B_hard.json` records `b6c69e43…` (the revision that
   reduced the evidence and applied `f`). The delta is exactly the `publish()` ledger fix
   in D-CAL-8; the campaign code path is untouched and the campaigns were not re-run.
4. **One measurement, one tree.** The rates describe `deepseek-flash` at temperature 0 on
   2026-09-22 with these interpreter and runtime revisions. A provider-side change
   (pricing, caching behaviour, a different model behind the alias) would move `q_r`; the
   ledger's `model_requested`/`model_reported` pair is the only alias check available.

## 11. A note on what changed since the previous attempt

The previous commit in this directory (`6602d943`) reported that the pilot was **blocked**:
both arms refused at their frozen-identity precondition because `EID*` named an `E*`
revision whose bytes were no longer on disk, so no rate existed and `apply` refused to
freeze a budget (`B_hard_REFUSED.json`). The A1 workstream re-froze `EID*` to
`7ce9e72f…`; `python3 a0/a1/verify.py` exits `0` in the current tree (checked before the
pilot started, at 21:04:50, and again after it finished). The refusal, with the blocked
run's evidence, is archived under `history/attempt1-blocked-identity-drift/` — it is the
record of a real state and of the arms being correctly fail-closed (**D-CAL-9**). Nothing
in it was used for this run.
