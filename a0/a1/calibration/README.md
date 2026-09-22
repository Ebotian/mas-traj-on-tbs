# `a0/a1/calibration/` — the A1 calibration pilot: procedure frozen, the pilot blocked by a repo-level identity drift

This directory is the A1 plan's item 7 ("run the calibration pilot and freeze `B_hard`").
`a0/tasks/maxcut/INTERFACE.md` §9 is the binding authority; `PILOT-PROCEDURE.md` is the
frozen procedure and `pilot_procedure.json` its machine-readable copy.

## 0. Bottom line, in the order the assignment asked for it

| # | step | verdict | evidence |
|---|---|---|---|
| 1 | **freeze the procedure and the mapping `f` before the calibration suite is touched** | **DONE** | `PILOT-PROCEDURE.md` (sha256 `68af1321…`), `pilot_procedure.json`, committed as `3e62d588` **before** any `suite/calibration/**` byte was read; `pilot.py freeze-check` re-verifies the ordering |
| 2 | **run the pilot** (one bounded campaign per arm, closed topology, calibration graphs, hard caps) | **RAN, BLOCKED** — 24 units per arm, all refused at the arms' frozen-identity precondition | `evidence/BLOCKED.json`, `evidence/<arm>/pilot_arm.json`, `evidence/rehearsal.json` |
| 3 | **apply `f` mechanically and freeze `B_hard`** | **REFUSED — no budget frozen** (a rate was never measured, so freezing one would be a fabricated number) | `B_hard_REFUSED.json` (V4/V6 named per arm); `apply` is re-run and compared byte-for-byte by `verify.py` |
| 4 | **the real ledger rows** | one real metered row (`ceq 68`), one induced `unmetered` counter-example (`ceq: null`), pilot campaigns: **0 rows** (the arms never reached the meter) | `evidence/meter-proof/meter_ledger.jsonl`, `evidence/unmetered/meter_ledger.jsonl`, `ledger.jsonl` |
| — | **spend** | **68 CEq** total, from the ledger (`a0/meter`), `deepseek-flash` | §7 below |

**What is missing is a rate, not a decision.** The procedure, the runner, the estimator,
the reduction and the verifier are all in place and green; the moment the evaluator
identity is consistent again, three commands produce `B_hard.json` with no design work
(§6).

## 1. What is here

| path | what it is |
|---|---|
| `PILOT-PROCEDURE.md` | the frozen procedure: workload, caps, telemetry definitions, variance estimators, `f`, its required properties, the stopping rule, the validity conditions V1–V7, the required diagnostics D1–D5 |
| `pilot_procedure.json` | the machine-readable copy, with the document's own sha256 (the runner refuses to run when it does not match) |
| `pilot.py` | the runner: the two campaigns, the arm commands, the KAPSO inner driver, `publish` (the reduction), `apply` (`f`), the metering proof, the unmetered counter-example |
| `verify.py` | **the one command**: everything model-free, re-established (see §8) |
| `tests/test_pilot.py` | the invariants: `f`'s formula, monotonicity, boundedness and clamp, validity V1–V7, percentile/`sd` definitions, the reduction |
| `evidence/` | the published run: `pilot_arm.json` + reduced harness ledger + reduced Outcomes + the meter ledger per arm, `rehearsal.json`, `BLOCKED.json`, the metering proof and the counter-example, `INDEX.json` |
| `ledger.jsonl` | the pilot campaigns' `a0/meter` rows, concatenated in time order (**0 rows**: no upstream call was made) |
| `B_hard_REFUSED.json` | **not a budget**: the refusal, the named validity failures, the telemetry, and the zero vector marked as unusable |

`B_hard.json` deliberately does not exist. `apply` writes it only when V1–V7 hold; when
they do not it writes `B_hard_REFUSED.json` instead and exits non-zero.

## 2. The freeze, and why the ordering is auditable

`PILOT-PROCEDURE.md` was written, its sha256 recorded in `pilot_procedure.json`, and both
committed (`3e62d588`, "…freeze the pilot procedure, the mapping f and B_hard's caps
before the calibration set is touched") **before** anything in this directory read a
`suite/calibration/**` byte. The first read of a calibration graph was `freeze-check`,
which hashes the 12 graphs against the manifest — after the sha was recorded. Three
mechanisms keep it auditable:

* the runner refuses to start when the document does not hash to
  `pilot_procedure.json.procedure.document_sha256` (`load_procedure`, and the
  `the_procedure_document_is_the_frozen_one` check on every run);
* every artifact carries `procedure.document_sha256` and `runner.sha256`;
* `verify.py`'s `budget` step re-derives the outcome from the published evidence, so a
  budget that did not come from this procedure cannot pass.

What the freeze covers, and nothing more: the workload (12 calibration graphs in manifest
order, 2 passes, `--max-iterations 3` / `rounds 2`), the caps (900 s and 1,200,000 CEq /
300,000 CEq), the estimators, `f` (`T_wall = 1800`; `CEq_max = min(ceil(1.25·30·max_r q_r),
5,000,000)`; `N_E,max = min(ceil(1.25·30·max_r e_r), 5,000)`; `P_concurrency = 1`), the
stopping rule and the validity conditions. No number in it was informed by a calibration
measurement: `τ = 10 s` is the gate workstream's frozen derivation, cited as the value the
pilot would run with.

## 3. The pilot attempt: what ran, and where it stopped

Both campaigns ran their full workload of 24 units (2 passes × 12 calibration graphs)
inside `unshare -rn`, with the campaign's metering proxy, the harness evaluation service,
and the unix-socket hop — the same boundary the paid arms use. Every unit refused
**before its first session**, with the same root cause reached from two independent code
paths:

| arm | campaign | units | exit codes | `CEq_r` | `N_E,r` | what the arm said |
|---|---|---|---|---|---|---|
| `A_simpleloop` | `C_calib_A_simpleloop` | 24/24 | `3` (×24) | **0** | **0** | `adapter: contract mismatch: evalcontract.py verify reported drift against T1.contract.json: DRIFT EvaluatorSource: digest changed c095f0c63430 -> a5636ab9f394 \| DRIFT EvaluatorSource: content changed a0/tasks/maxcut/e_star.py \| … \| DRIFT EID* changed cddfa64ead571bbb -> 6682ff6a85088cbb` |
| `A_kapso` | `C_calib_A_kapso` | 24/24 | `1` (×24) | **0** | **0** | `EvaluationMaintainerError: Calibration run failed (exit 3): kapso_eval_t1: E* source drifted: e_star.py sha256 fa0932b4… != 670f02ee… recorded in EID* (cddfa64e…)` |

The driver's own checks agree: `the_arm_reached_the_harness: false`,
`the_model_family_is_deepseek_flash: false` (there was no call to attribute),
`every_metered_row_re_derives_its_ceq: false` (there was no row). The topology checks are
green in both campaigns: direct egress to three bare IP literals is `BLOCKED` from inside
the namespace while the campaign's metered port is reachable over the unix socket.

**The root cause is outside this directory, and it is repo-wide.** `EID*` was frozen at
`a0/a1/T1-EID.json` on 2026-09-22 17:02 (commit `9e836f36`) against `e_star.py`'s then-current
bytes. The maxcut workstream then fixed a real defect in `E*` ("the candidate launch must
be a function of the candidate's bytes alone", commit `6dd717c2`, 19:08; file mtime 19:03),
whose own conformance suite is green (`python3 a0/tasks/maxcut/conformance.py --check` →
`VERDICT: PASS`). The A1 evaluator identity was not re-frozen, so:

```
$ python3 a0/a1/t1_eid.py check
{"on_disk": "cddfa64ead571bbb…", "pass": false, "reason": "eid_star drifted",
 "recomputed": "6682ff6a85088cbb…"}                      # exit 5
$ python3 a0/a1/verify.py
{"verdict": "fail", "steps": {"t1-eid": false, "declarations": true,
 "wiring-simpleloop": false, "wiring-kapso": true, "skeleton-dryrun": false,
 "tests": true}}                                          # exit 5
```

So this is not a pilot-specific refusal: the A1 harness's own verifier is red in the
current tree, for the same reason, and the A1 testbed commit `bfbe74c2` ("built and
verified") predates nothing — it was made at 19:21, after `E*` changed. The arms are
correctly fail-closed; the identity document is simply stale.

**None of the calibration set was evaluated.** No `E*` ran, no Outcome exists
(`evidence/<arm>/outcomes/` has 0 files), no harness ledger row was booked, and no
algorithmic quantity of any kind was computed. The arms stopped at their identity
precondition, before reading the graph they were handed — measured, not assumed: run with
a **non-existent** graph path (`--graph /nonexistent/NO_SUCH_GRAPH.json`) the SimpleLoop
adapter fails with the *same* drift error and never reports a missing file, and the unit
run directories are empty (no `run_meta.json`, no traces, `arm_state.present: false` in
the published telemetry). The 12 calibration graphs were only *hashed* (identity against
the manifest) and *named* in the arm command lines; the pilot's `graph_shas_used` lists
are empty in both campaigns.

## 4. Where the calibration set was used, and where it was not

* **Not evaluated, not scored, not ranked.** No score on any calibration graph exists in
  this directory, and none was computed (§3).
* **Not used for any selection.** No candidate, arm, policy or threshold anywhere in this
  repository was chosen from a pilot result; there is no pilot result.
* **Published evidence is a reduction.** The pilot's artifacts would carry the objective's
  value on calibration graphs (`true_value`, `handed_value` in the harness ledger;
  `cut_edges`, `cut_fraction` in the Outcome). `publish` removes them, records which keys
  were removed and why, and keeps every field a rate needs (`ts`, `campaign_id`, `arm_id`,
  `candidate_source_sha256`, `graph_sha256`, `status`, `wall_sec`,
  `interpreted.wall_ms`); arm stdout/stderr are published as sha256 plus byte length.
  `verify.py` re-checks this structurally (a dict key, not a substring) over every
  published file. In this run the redaction is vacuous — there was nothing to redact — but
  the mechanism is exercised by the test suite and is part of the freeze.

## 5. Ledger excerpts (real, from `a0/meter`)

The pilot campaigns booked nothing, so the ledger evidence comes from two probe campaigns
that are **not** part of the pilot's totals. Both rows are verbatim below.

**One real metered upstream call, issued from inside the namespace** (`evidence/meter-proof/`):

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_meter_proof","arm_id":"A_calib_proof",
 "ts":"2026-09-22T19:41:5x+08:00","provider":"deepseek",
 "endpoint":"https://api.deepseek.com/v1/chat/completions",
 "model_requested":"deepseek-flash","model_reported":"deepseek-flash",
 "provider_request_id":"…","stream":false,
 "usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":36,"completion_tokens":8},
 "ceq":68,"unmetered":false,"reason":null}
```

`ceq = 36 + floor(0·2/100) + 4·8 = 68`, re-derived by `a0/meter/verify_ledger.py` (exit 0),
and direct egress from the same namespace is `BLOCKED` for `1.1.1.1`, `8.8.8.8` and
`123.148.116.184`.

**The induced missing-usage counter-example** (`evidence/unmetered/`): a request for a
model that does not exist gets a 4xx with no `usage` field — a *gap*, not a refusal:

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_unmetered_probe","arm_id":"A_calib_probe",
 "provider":"deepseek","model_requested":"deepseek-does-not-exist-a0-calibration",
 "model_reported":null,"provider_request_id":null,"stream":false,
 "usage":null,"ceq":null,"unmetered":true,"reason":"upstream_http_400_no_usage"}
```

and `a0/a1/budget.py::BudgetEnforcer` stops the campaign on it —
`stopped_because: "budget_exhausted:unmetered_model_call"` — rather than estimating the
spend (`INTERFACE.md` §8).

**Per-arm totals for the pilot itself:** `C_calib_A_simpleloop` 0 rows / 0 CEq,
`C_calib_A_kapso` 0 rows / 0 CEq. **No pilot row is `unmetered`** (there are no rows to be
unmetered, and the two probe rows above are on their own campaigns, outside
`ledger.jsonl`).

## 6. Why no `B_hard`, and what would unblock it

`apply` ran `f` over the published telemetry and refused, naming the validity conditions
(procedure §6, `B_hard_REFUSED.json`):

```
V4: A_simpleloop has no measured interval (T_r=51.430327s, units=24)
V6: A_simpleloop's harness evaluations are not all calibration graphs
V4: A_kapso has no measured interval (T_r=32.368727s, units=24)
V6: A_kapso's harness evaluations are not all calibration graphs
```

The `T_r` values there are launch intervals of a workload that evaluated nothing, not
measured work intervals — which is exactly why V4 exists. The document also carries a
`vector_note` marking its zero vector as **not a budget**, so no consumer can mistake it
for one. The report required by §9 (variance, per-call `CEq`, margins, the "would the
guardrails bind early?" test) **cannot be produced**, because every one of those numbers is
a function of a rate that does not exist. Freezing a budget from this run would have been
the fabricated number the freeze exists to prevent.

**What the pilot needs** (one change, outside this directory):

1. the owner of `a0/a1/T1-EID.json` + `a0/a1/T1.contract.json` re-freezes the evaluator
   identity against the current `E*` bytes — `python3 a0/a1/t1_eid.py build` — and
   re-declares `CID`'s `task.eid_star`; **or** `a0/tasks/maxcut/e_star.py` is returned to
   the revision the frozen `EID*` names (`670f02ee…`, `git show 11f55bf0:a0/tasks/maxcut/e_star.py`).
   Either way the two files must agree; nothing in this directory can decide which.
2. then, with no design work:

```bash
DEEPSEEK_API_KEY=$(python3 -c "...") python3 a0/a1/calibration/pilot.py all --out-dir /tmp/a1cal/pilot
python3 a0/a1/calibration/pilot.py publish --out-dir /tmp/a1cal/pilot --published-dir /tmp/a1cal/pilot/published
python3 a0/a1/calibration/pilot.py apply  --out-dir /tmp/a1cal/pilot/published
```

The caps bound that run at 900 s wall and 1,200,000 / 300,000 CEq per arm; the a-priori
expectation in `pilot_procedure.json` is ~48 model calls per arm.

## 7. Spend (from the ledger, not self-reported)

| campaign | rows | unmetered | `CEq` |
|---|---|---|---|
| `C_calib_meter_proof` (one tiny in-namespace call) | 1 | 0 | **68** |
| `C_calib_A_simpleloop` (pilot, blocked) | 0 | 0 | **0** |
| `C_calib_A_kapso` (pilot, blocked) | 0 | 0 | **0** |
| `C_calib_A_simpleloop` / `C_calib_A_kapso` (rehearsals, `--no-model` / injected solver) | 0 | 0 | **0** |
| `C_calib_unmetered_probe` (induced 4xx) | 1 | 1 | `null` (not estimable by design) |
| **total for this workstream** | | | **68 CEq** |

Model `deepseek-flash`, temperature 0, everything through `a0/meter`. The key was read
into the environment in the same command that used it and was never printed, logged or
written to an artifact.

## 8. The one command a third party reruns

```bash
python3 a0/a1/calibration/verify.py --with-rehearsal     # exit 0 = every claim re-established
```

It re-establishes, in order: the freeze ordering (the document's sha256 and the 12
manifest-verified calibration graphs); the model-free invariants (23 tests); that
`B_hard_REFUSED.json` is *reproducible* from the published evidence and that V1–V7 fail
exactly as recorded (or, in the unblocked case, that `B_hard.json` is byte-reproducible
and V1–V7 hold); that the meter's own verifier re-derives every published pilot ledger and
that none is `unmetered`; that the in-namespace metered row and the induced `unmetered`
counter-example are what they claim to be; that no published file uses an objective value
on a calibration graph as data; that the reduction, the estimators and the validity
predicates hold; and — with `--with-rehearsal` — the closed topology, measured. Note that
it does **not** re-run the paid campaigns (they spend money), and that any edit to
`pilot.py` invalidates the committed evidence chain, because every artifact records
`runner.sha256`; `verify.py` says so explicitly rather than papering over it.

## 9. Deviations (none of them a relaxation)

| id | what | why |
|---|---|---|
| D-CAL-1 | the KAPSO unit driver is **mine** (`pilot.py kapso-inner`), built on `a0/a1/kapso_t1/`'s `runtime_t1`, because that workstream's probe hardcodes `GRAPH_ID = G_dev_0001` and offers no graph argument (its README calls the per-node graph "the probe's choice, not a campaign policy") | §9 requires the pilot to run on the calibration graphs; I own only my directory, so the driver lives here and reads theirs unchanged |
| D-CAL-2 | the KAPSO unit **rebases the adapter's `state_root`** into the pilot's work directory (`dataclasses.replace(config, state_root=…)`) | the adapter would otherwise install the registered tree under `a0/a1/kapso_t1/state/`, i.e. write inside another workstream's directory |
| D-CAL-3 | the KAPSO inner does **not** memoise the second round's model call (the `kapso_t1` probe does, to spend one call instead of two) | a rate measurement must observe the arm's actual call pattern; memoising would understate `q_r` |
| D-CAL-4 | the published evidence is a **reduction** (score-bearing keys removed, console output by digest) | procedure §0: the pilot's algorithmic results are not used, reported *or published*, so that no later reader can tune the budget by eyeballing a calibration score |
| D-CAL-5 | the pilot runs **without a harness-owned preflight for the arms' identity** (my driver reproduces the arms' checks by running `t1_eid.py check` and records the result per campaign) | the `a0/a1/skeleton.py` preflight checks *one* instance's sha and the CID factors, not the arms' evaluator-identity agreement; adding the check to the skeleton is another directory's change (reported, not made) |
| D-CAL-6 | `a0/a1/calibration/pilot.py meter-proof` makes **one real, tiny upstream call** (~68 CEq) that is not part of the pilot workload | with both arms blocked, the assignment's requirement to report real ledger rows would otherwise have no row at all; it is labelled, capped (`max_tokens 8`), and on its own campaign id |
| D-CAL-7 | the assignment's item 7 says "freeze `B_hard`", and no `B_hard` is frozen | `INTERFACE.md` §9 requires the mapping to report the pilot's variance and §6 of the procedure requires a measured interval; with no rate, freezing a vector would be a false negative manufactured by the pilot — the thing the assignment told me not to do |

## 10. What I could not verify (stated plainly)

1. **No rate exists** — `q_r`, `e_r`, the candidate-latency distribution, the per-arm
   variance and the §7 `τ` cross-check are all unmeasured, because the arms never ran a
   session. Nothing in this directory should be read as a rate estimate.
2. **The arms' post-preflight plumbing is unexercised here**: the model call through the
   campaign's meter *by an arm*, the harness `E*` invocation for an arm's candidate, and
   the per-unit ledger attribution are all written and unit-tested but have not run
   end-to-end in this pilot. (The topology and the metered path themselves are proven —
   `evidence/meter-proof/` — and the same arms ran live earlier today under the *previous*
   `E*` bytes, `a0/a1/evidence/live_simpleloop.json`, `a0/a1/kapso_t1/evidence/live_t1.json`.)
3. **The KAPSO arm's declared configuration is what would be measured**, not a
   configuration with real coding-agent implementation sessions (the `a0_kapso` adapter's
   `real_implementation=False` default, as in `kapso_t1`'s own live arm): its per-round
   consumption would be higher than any number this pilot could have produced. Recorded as
   a scope limit in `B_hard_REFUSED.json` so it cannot be lost when the pilot runs.
4. **The block is a snapshot**: `t1_eid.py check` failed at 19:31 and again at 19:45; if the
   identity is re-frozen after this commit, re-running `verify.py` will report the arms as
   reachable instead, and the pilot can be run.

## 11. A repo-level finding, for whoever owns it

`python3 a0/a1/verify.py` — the A1 harness's own re-runnable verifier — currently exits 5
with `t1-eid: false`, `wiring-simpleloop: false`, `skeleton-dryrun: false`, i.e. the harness
is red in the committed tree for the reason in §3, and the committed evidence under
`a0/a1/evidence/` was produced under `E*` bytes that no longer exist on disk. That is a
decision for the A1 workstream (re-freeze `EID*`, re-run its paid probes, or pin `E*` back);
this directory only reports it. I did not modify `a0/a1/T1-EID.json`,
`a0/a1/T1.contract.json`, `a0/tasks/maxcut/e_star.py` or any other workstream's file.
