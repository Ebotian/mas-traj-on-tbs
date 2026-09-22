# A1 wiring report — the harness owns the evaluation, the runtimes consume it

Scope: the two A1 arms (SimpleLoop and KAPSO), the harness that measures them, the
budget that bounds them and the block design that replicates them. The binding
authority is `a0/tasks/maxcut/INTERFACE.md`; interpretations and deviations are in
`DEVIATIONS.md`.

Everything below is **evidence from an execution**, not a description of intent.
The re-runnable entry point is `python3 a0/a1/verify.py`; the paid runs are
`a0/a1/probes/live_probe.py` and their recorded output is committed under
`a0/a1/evidence/`.

**This revision.** Four defects reported by `a0/verify/a1-testbed/REPORT.md` are
addressed: T1's `EID*` was re-frozen against the current evaluator bytes
(§1 row 0, `DEVIATIONS.md` D-A1-7), every recorded artifact was re-run against
those bytes (D-A1-11, `a0/a1/evidence/README.md`), the *candidate* lane is now
closed by the harness in a namespace and measured by a hostile candidate (§7,
D-A1-8/D-A1-9), and a harness-supplied score is bounded by the task (§8,
D-A1-10). Two of those touch an interface; the proposed `INTERFACE.md` sentences
are named in D-A1-8 and D-A1-10 rather than assumed.

---

## 1. Verdicts

| # | claim | verdict | evidence |
|---|---|---|---|
| 0 | T1's frozen evaluator identity `EID*` recomputes from the bytes on disk | **CONFIRMED** | `python3 a0/a1/t1_eid.py check` → `eccd859c…`; the re-freeze, both values and the reason are in `DEVIATIONS.md` D-A1-7 |
| 1 | SimpleLoop no longer evaluates: it consumes a harness-authored Outcome, and the same candidate bytes yield the same Outcome and the same selection | **CONFIRMED** | `evidence/wiring_simpleloop.json` (9/9 checks) |
| 2 | When the harness supplies a deliberately wrong number, the runtime's selection follows the **harness's** number | **CONFIRMED** | same file: the override inverts the true ranking (true best `proposal_i1` 207 → handed 1; true worst `proposal_i2` 0 → handed 9999) and the champion is `proposal_i2` |
| 3 | The runtime cannot substitute its own number | **CONFIRMED** | same file, two checks: with no harness identity the adapter exits 3 without running; with the service stopped mid-run every candidate is `error/harness_outcome_missing`, `search_signal: null`, champion `null`, exit 8 |
| 4 | KAPSO's score of record is the harness's number, written **after** the session | **CONFIRMED** | `evidence/wiring_kapso.json` (7/7) and `evidence/live_kapso.json` (10/10): node.score = 2.4519205208433132 = the harness's value, while the session printed its own line claiming 9.75 |
| 5 | KAPSO's class triple is derived from the runtime, not hardcoded | **CONFIRMED** | under a `fast/0.15` grant the derived line is adopted and a hardcoded `full/1.0/1337` line returns `None` (silently discarded, `registered_evaluation.py:87-99`) |
| 5b | The T1 registered evaluation tree is an `AID_r` factor at full resolution | **CONFIRMED** | `declarations/AID_r.A_kapso.json`: `runtime.registered_evaluation_tree` = `manifest:6b1d6fcc…` recomputed from the tree's bytes and cross-checked against `a0/a1/kapso_t1/binding.json` (D-A1-6) |
| 6 | One real campaign per arm ran through the meter, inside the closed topology | **CONFIRMED** | `evidence/live_simpleloop.json`, `evidence/live_kapso.json` |
| 7 | Every upstream call has a ledger row with a real `CEq`; a missing-usage response is `unmetered` | **CONFIRMED** | `evidence/live_controls.json` (6/6) and both live arms; rows cross-checked against the proxy's per-call sidecar and re-derived by `a0/meter/verify_ledger.py` |
| 8 | No unmetered model call is possible | **CONFIRMED** | same file: direct egress blocked from inside `unshare -rn`; non-allowlisted destination 403'd; a call without the campaign token 403'd and booked against that campaign; an induced upstream response without usage booked `unmetered` and stops the campaign |
| 9 | The A1 skeleton exists and its decisions are executable | **CONFIRMED** | `evidence/skeleton_dryrun.json` (25/25 checks) |
| 10 | The two arms can be compared on T1's `Δ` today | **MOSTLY** | the KAPSO T1 retarget exists — `a0/a1/kapso_t1/` (another workstream) delivers the T1 registered tree, the max-cut `EidStar` binding and the T1 arm, with its own live evidence (15/15), and this directory now pins that tree in `AID_r.A_kapso.json` (D-A1-6). What is still missing for a *campaign* is the calibration pilot and the frozen `B_hard` (`INTERFACE.md` §9). See D-A1-2 for which live evidence belongs to which configuration |
| 11 | A **hostile** candidate cannot reach the network, read the stored reference partitions or the key, or read another process's environment | **CONFIRMED** | `evidence/hostile_candidate.json` (13/13): the same candidate scores **224 = R = OPT** by copying a stored witness in the pre-fix lane and through a `--net-isolate`-only lane, and scores **0** in the sandboxed lane, where every attack fails |
| 12 | `--net-isolate` alone is **not** sufficient for the candidate lane | **CONFIRMED** | same file, lane `service_net_isolate_only`: network `BLOCKED:gaierror`, `~/gptapi.md` readable, 30 witnesses read, harness score 224 |
| 13 | A harness-supplied score is bounded by the task, and an out-of-bound one is refused by default | **CONFIRMED** | `evidence/score_bound.json` (7/7): `9999` and `-5` refused (`value: null`, `failure.kind: implausible_override`, booked `override_rejected`), `200` published, and `9999` published **labelled** only under `--override-mode labelled_implausible` |
| 14 | The harness is not launched with, and does not hand down, a provider credential | **CONFIRMED** | `eval_service.py:_evaluator_environment` (four keys) and the sanitized launch in `probes/live_probe.py`/`skeleton.py`; the hostile probe finds the canary in an ancestor's environment in the unconfined lane and finds nothing in the sandboxed one |
| 15 | Every recorded artifact describes the current evaluator bytes | **CONFIRMED** | `evidence/README.md`'s pre-fix/refreshed table; `python3 a0/a1/verify.py` 6/6 |

---

## 2. SimpleLoop: consumption instead of measurement

**What changed.** `a0/runtimes/simpleloop/a0_adapter/harnesseval.py` is new: a
lane with the same surface as `EStarEvaluator` (`evaluate(candidate,
iteration=) -> EStarResult`) that has **no path which runs an evaluator**. It
writes a request into the harness ABI directory, waits for the response the
harness publishes, and returns it. `runner.build_evaluator` selects the lane from
`--eval-mode {estareval,harness}`; `loop.py`, the three traces and the frozen
selection semantics are untouched.

Wiring kept identical on purpose: the same `F_r` fold, the same tie-break, the
same failure-stage table (extended only for T1's `exit 4 = timeout`, D-A1-5). What
changed is *who realises the measurement*.

**Evidence (`evidence/wiring_simpleloop.json`, all 9 checks pass).**

```
same_candidate_bytes_same_consumed_outcome          true   (canonical per-candidate Outcome digests equal across a replay)
same_consumed_outcome_same_selection                true   (champion proposal_i1/207 both runs)
honest_ledger_true_equals_handed                    true
the_override_inverts_the_true_ranking               true   true={c02:132, i1:207, i2:0}  handed={c02:132, i1:1, i2:9999}
runtime_selection_follows_the_harness_number        true   champion=proposal_i2 scalar=9999
the_implausible_number_is_published_labelled_not_silently  true   (9999 > |E| = 265, labelled mode; the default refuses it — §8)
the_score_of_record_is_the_harness_s_in_the_trace   true   every score event carries `harness_supplied … oid=… seq=…`
absent_harness_refuses_instead_of_evaluating        true   adapter exit 3, no run_meta written
stopped_service_scores_nothing_and_exits_8          true   status=error kind=harness_outcome_missing, signal null, champion null
```

The false-green trap this closes is `INTERFACE.md` §12's "用候选自报的分数":
before this change the adapter's own subprocess produced the number. Now the
number arrives from outside, carries the harness's `a0/envelope` OID token in
`evaluator_evidence.detail`, and — in run 2 — is a number `E*` could not have
produced (9999 > |E| = 265), which the runtime uses anyway. That is the property:
the runtime consumes, it does not measure.

---

## 3. KAPSO: the score is written after the session

**What changed.** `a0/runtimes/kapso/a0_adapter/harness_manifest.py` is new. It
implements the three conditions `HARNESS-OWNED-EVAL.md` §7 left open, and its
docstring carries the attribution caveat:

1. `class_triple(strategy)` reads `strategy.fidelity_decision.eval_fidelity`,
   `.eval_fraction` and `strategy.registered_subsample_seed`, and **refuses** to
   build a line when any of them cannot be read. `manifest_line()` includes
   positive `items`/`total_items` (`parse_manifest_line` raises without them).
2. `PostSessionManifest.install()` patches `GenericSearch._absorb_implementation`
   — adapter side, no upstream edit — and `amend()` runs **after** the original
   returns, so the session's output is already fixed and the harness's line is
   the file's **last** manifest line. `manifest_of_record` keeps the last one
   (`registered_evaluation.py:72-78`); appending is the whole mechanism.
3. Every line carries `harness_supplied: true`, the harness run id, the request
   id, the ledger sequence and the measurement OID; `ATTRIBUTION_CAVEAT` is
   written into the probe's artifact.

**Evidence (`evidence/wiring_kapso.json`, 7/7).** The session printed **three**
manifest lines: the registered evaluation's own (2.4519205208433132), the
session's claimed one (9.75), and the harness's. The recorded score of record is
the harness's; the session's claim never lands. Under a `fast/0.15` grant, the
line built by `class_triple` is adopted (score 2.0) and a hardcoded
`full/1.0/1337` line returns `None` — i.e. the failure mode the requirement named
("silently discarded") is reproduced and then removed.

**The caveat, stated where it belongs.** KAPSO files this number as a
`full`-fidelity attempt under the **registered evaluator's id**
(`record_evaluation_attempt`, `registered_evaluation.py:124-159`, which never
consults the manifest). Measured: `evaluation_attempts[0].evaluator_id` ==
`registered_evaluator_id` == `8128cf91…`, with no trace of the harness. So:

> **KAPSO's ledger is not evaluator-realisation evidence.** A1 must read the
> harness's own ledger (`a0/a1/eval_service.py`, one row per `E*` invocation,
> with the handed and the true value) and the `a0/envelope` measurement token.
> KAPSO's `evaluation_attempts`, evidence tiers, `get_deliverable_score` and MCP
> experiment memory will all attribute the harness's number to the registered
> evaluator, and nothing in KAPSO can tell the difference.

This is not a defect we can fix from outside the runtime; it is a boundary
condition on what KAPSO-based numbers may be used as evidence for.

---

## 4. The live-session probe

Topology: `runtime ─plaintext─▶ meter_proxy (campaign port) ─TLS─▶ api.deepseek.com`,
with the runtime inside `unshare -rn` reaching the meter only over a unix socket
that the filesystem — not the network — carries. (A compensating framing hop sat
between the meter and the provider for the first round of this work; `a0/meter`
commit `86987235` fixed the proxy, the hop was deleted, and D-A1-3 records both.) Model `deepseek-flash`,
temperature 0.

| | SimpleLoop (T1 max-cut) | KAPSO (plumbing; D-A1-2) |
|---|---|---|
| campaign id | `C_live_simpleloop` | `C_live_kapso` |
| model calls (meter rows) | 1 | 1 |
| tokens (meter, authoritative) | hit 1024, miss 168, completion 2048 | miss 80, hit 0, completion 256 |
| `CEq` | 8380 | 1104 |
| harness `E*` calls | 2 (baseline 132; `ds_i001` 0) | 1 (node0 2.4519205208433132) |
| score of record | 132, `score_source=harness` | 2.4519205208433132, `score_source=harness` |
| session's own claim | n/a | 9.75 (printed by the session, **not** recorded) |
| checks | 9/9 pass | 11/11 pass |

**(a)** the score of record equals the harness's handed value in both arms.
**(b)** ordering: KAPSO's node carries three manifest lines and the harness's is
last (`last_line_is_the_harness_s = true`); the session's claim of 9.75 is
recorded in the artifact and is *not* the score.
**(c)** one row per upstream call, each with an integer `CEq > 0`. The row count is
cross-checked against the proxy's own per-call sidecar (an independent count of
the calls it handled: 1 == 1 in both arms) and every metered row is re-derived by
the meter's own `verify_ledger.py` (exit 0 in both arms), so the ledger is checked
by something other than its consumer.
**(d)** see §5.

---

## 5. The controls, and what "no unmetered call" means here

`evidence/live_controls.json`, 6/6, and nothing above cost a token:

| control | observed |
|---|---|
| direct egress from inside `unshare -rn` | `1.1.1.1`, `8.8.8.8`, `123.148.116.184` all `Network is unreachable`; the campaign's metered port over the unix socket `REACHED` |
| a destination the meter does not allow | `403`, booked `unmetered` with reason `host_header_not_allowlisted:evil.example` |
| a call without the campaign's token | `403`, booked `unmetered` with reason `attribution_token_mismatch`, **against this campaign** |
| an induced upstream response with no `usage` | a real DeepSeek response (HTTP 400 for a nonexistent model id) booked `unmetered` with reason `upstream_http_400_no_usage` |
| … and the budget's reaction | `stopped_because = budget_exhausted:unmetered_model_call` — a campaign whose spend is not established is stopped, not extrapolated |

---

## 6. The A1 orchestration skeleton

`evidence/skeleton_dryrun.json`, 25/25. No campaign was started.

* **Identity.** `CampaignID = (TaskID, BlockID, ArmID, ReplicateID)`; changing any
  one component changes the key.
* **The causal-role rule.** `a0/a1/declaration.py` builds `CID` (13 factors: T1's
  `EID*`, `e_star.py`, `e_star_child.py`, the suite and candidate-set manifests,
  the harness service, the ABI, the token issuer, the topology, the meter mode,
  the failure semantics, the model route, the measurement protocol) and one
  `AID_r` per arm. The KAPSO arm's declares the **T1 registered evaluation tree**
  (`runtime.registered_evaluation_tree` = `manifest:6b1d6fcc…`, plus its exact
  per-file map), adopted per D-A1-6; the SimpleLoop arm's declares the same factor
  as "no registration mechanism", so the mechanism difference is explicit rather
  than an asymmetry in the paperwork. The audit passes on the real declaration, fails on an
  object named nowhere, and fails on a `CID` factor that drifted.
* **Budget.** All four stop conditions fire as designed (wall clock, `CEq`,
  evaluator calls, and an unobservable usage gap); a policy refusal is counted but
  does not stop the campaign; another campaign's rows are not counted; an absent
  ledger is a refusal, not a zero.
* **Blocks.** The plan is reproducible from the seed, each block contains every
  arm once, block orders are not all equal, an outage invalidates the **whole**
  block (including a campaign that had already completed in it), an invalidated
  block cannot be completed, and it is replaced by a new block.
* **Preflight.** The campaign skeleton passes on the real artifacts and refuses to
  construct when the instance is missing rather than defaulting.

### The `AID_r` for the KAPSO arm (what changed in this revision)

Adopted per D-A1-6, from `a0/a1/kapso_t1`'s D-KT1-7:

| factor | identity |
|---|---|
| `runtime.registered_evaluation_tree` | `value:{eid_r: manifest:6b1d6fccf78d1b94f0bb2fa3e200e5ff224aa4b8575148914499a2f083bc5301, native_scheme: manifest_fingerprint, fingerprint_rule: KAPSO's own, tree: a0/a1/kapso_t1/tree, binding: a0/a1/kapso_t1/binding.json}` |
| `runtime.registered_evaluation_tree_files` | `value:{"a0_locator.json": "5a0c99ff…", "kapso_eval.py": "6759ef05…"}` |

A byte in either file changes the factor; the fingerprint is recomputed here and
disagreement with that directory's `binding.json` fails the audit
(`registered_tree_disagreement`). `A_simpleloop` declares the same factor name with
`{mechanism: "none"}`, so the arm-varying set is
`{runtime.grant_triple, runtime.outcome_lane, runtime.registered_evaluation_tree,
runtime.substrate}` and the mechanism difference between the arms is on the face of
the declaration instead of being an absence.

---

## 7. The candidate lane: who closes it, and the hostile probe that measures it

A campaign's number may be called "the substrate improved the algorithm" only if
the budget is enforceable where the runtime cannot lie (principle iv) and the
improvement holds on instances the agent has never seen (principle v). Both fail
if a *candidate* can reach the provider or read the answers, and that is what the
verifier measured: `eval_service.py`'s frozen `maxcut` argv never passed
`--net-isolate`, and nothing stopped a candidate from reading
`a0/tasks/maxcut/references/` and copying a stored partition — `217 = R = OPT` on
the graph the verifier used, through this service.

**Two closures, both on the harness side** (`DEVIATIONS.md` D-A1-8):

* `--net-isolate` is now inside the frozen `maxcut` argv, so the candidate gets its
  own route-less network namespace because the *harness* says so;
* `E*` itself now runs inside `a0/a1/candidate_sandbox.py`: `unshare -rmnpf
  --mount-proc` (user + mount + network + PID namespace), `/home`, `/tmp`,
  `/var/tmp` and `/run/user` replaced by empty tmpfs mounts, and the invocation's
  own inputs bound back — the evaluator's two files, the interpreter's
  installations, the one graph the request names, the candidate's bytes, and the
  state/out directory. The lane's self-check runs before `E*` is exec'd and
  refuses to measure otherwise; its receipt is written to
  `<out>/sandbox_receipt.json` and quoted in the evidence.

**Is `--net-isolate` enough? No.** `evidence/hostile_candidate.json` (13/13) runs
one hostile candidate — it tries the network, `~/gptapi.md`, every readable
`/proc/*/environ`, and the stored witnesses, and *uses* the best witness it can
read as its answer — through four lanes. The number in the last column is the
harness's own, not the candidate's story:

| lane | network | `~/gptapi.md` | witnesses | key in `/proc` | harness score |
|---|---|---|---|---|---|
| `raw_pre_fix` (`E*` at `HEAD`, no flags) | **REACHED** | readable | **30 read, best used** | **found** | **224 = R = OPT** |
| `service_net_isolate_only` (`--candidate-isolation none`) | BLOCKED | **readable** | **30 read, best used** | — | **224** |
| `service_sandbox` (the default) | BLOCKED | not readable | 0 visible | not found | 0 (its honest fallback) |
| working-tree `E*` inside the sandbox | BLOCKED | not readable | 0 visible | not found | 0 |

The third row is the claim: every attack fails **and the lane still measures**
(status `ok`, a real Outcome, `cut_edges = 0` for the all-zeros fallback). The
fourth row is not part of the comparison — another workstream is closing the same
door inside `E*` at the same time (D-A1-12), and the two mechanisms compose.

`--candidate-isolation none` exists only for a labelled control run: it writes
`labelled_unsafe: true` and `candidate_can_reach_the_network: true` into
`harness_identity.json` and puts `candidate_isolation: "none"` on the response and
on every ledger row, so no artifact can be mistaken for a sandboxed one.

## 8. The bound on a harness-supplied score

`--override` is deliberate — it is how "the runtime consumes, it does not measure"
becomes observable — and the verifier's finding was not that it exists but that
nothing bounded it: the service published `9999` beside `true_value 132` for a
graph with `|E| = 265`, and no check anywhere objected.

**What is enforced now** (`DEVIATIONS.md` D-A1-10): for `maxcut`, every published
value must satisfy `0 <= cut_edges <= edges_total`, where `edges_total` is the
**Outcome's own** number. The check is at the boundary where the service
publishes:

* an override outside the bound is **refused** in the default mode
  (`--override-mode bounded`): `value: null`, `status: error`,
  `failure.kind: implausible_override`, `measurement: null`, and the attempt is
  booked with `override_rejected: true` and no handed value — so the E* call is
  still counted by the budget and the refusal is visible;
* `--override-mode labelled_implausible` publishes the lie **with its label**
  (`plausibility.within_bound: false`,
  `verdict: accepted_labelled_out_of_bound`) on the response, in the handed
  Outcome, and on the ledger row;
* `E*`'s own number is checked too: an Outcome outside the bound is refused as
  `implausible_outcome` (a harness-side integrity failure);
* the plumbing evaluator declares no bound (`score_bound: null`): its Outcome has
  no `|E|`-like denominator, and the service records "unbounded" rather than
  inventing a constant.

`evidence/score_bound.json` (7/7) runs five cases through the service's ABI:
`honest` (132, `within_bound`), `in_bound_override` (200, published),
`above_the_bound` (9999, refused), `below_the_bound` (−5, refused),
`labelled_lie` (9999, published and labelled). `wiring_simpleloop.json`'s lying
run is the labelled case, which is why that probe passes `--override-mode
labelled_implausible` and has a check that the number was labelled.

**Still not enforced, in another workstream's directory:** `a0/contract`'s
run-level trace validator compares nothing against a metric's declared `range`,
although the sample metric declares one. The minimal diff is in D-A1-10.
