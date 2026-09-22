# A1 wiring report — the harness owns the evaluation, the runtimes consume it

Scope: the two A1 arms (SimpleLoop and KAPSO), the harness that measures them, the
budget that bounds them and the block design that replicates them. The binding
authority is `a0/tasks/maxcut/INTERFACE.md`; interpretations and deviations are in
`DEVIATIONS.md`.

Everything below is **evidence from an execution**, not a description of intent.
The re-runnable entry point is `python3 a0/a1/verify.py`; the paid runs are
`a0/a1/probes/live_probe.py` and their recorded output is committed under
`a0/a1/evidence/`.

---

## 1. Verdicts

| # | claim | verdict | evidence |
|---|---|---|---|
| 1 | SimpleLoop no longer evaluates: it consumes a harness-authored Outcome, and the same candidate bytes yield the same Outcome and the same selection | **CONFIRMED** | `evidence/wiring_simpleloop.json` (8/8 checks) |
| 2 | When the harness supplies a deliberately wrong number, the runtime's selection follows the **harness's** number | **CONFIRMED** | same file: the override inverts the true ranking (true best `proposal_i1` 207 → handed 1; true worst `proposal_i2` 0 → handed 9999) and the champion is `proposal_i2` |
| 3 | The runtime cannot substitute its own number | **CONFIRMED** | same file, two checks: with no harness identity the adapter exits 3 without running; with the service stopped mid-run every candidate is `error/harness_outcome_missing`, `search_signal: null`, champion `null`, exit 8 |
| 4 | KAPSO's score of record is the harness's number, written **after** the session | **CONFIRMED** | `evidence/wiring_kapso.json` (7/7) and `evidence/live_kapso.json` (10/10): node.score = 2.4519205208433132 = the harness's value, while the session printed its own line claiming 9.75 |
| 5 | KAPSO's class triple is derived from the runtime, not hardcoded | **CONFIRMED** | under a `fast/0.15` grant the derived line is adopted and a hardcoded `full/1.0/1337` line returns `None` (silently discarded, `registered_evaluation.py:87-99`) |
| 6 | One real campaign per arm ran through the meter, inside the closed topology | **CONFIRMED** | `evidence/live_simpleloop.json`, `evidence/live_kapso.json` |
| 7 | Every upstream call has a ledger row with a real `CEq`; a missing-usage response is `unmetered` | **CONFIRMED** | `evidence/live_controls.json` (6/6); rows cross-checked against the repair hop's own log |
| 8 | No unmetered model call is possible | **CONFIRMED** | same file: direct egress blocked from inside `unshare -rn`; non-allowlisted destination 403'd; a call without the campaign token 403'd and booked against that campaign; an induced upstream response without usage booked `unmetered` and stops the campaign |
| 9 | The A1 skeleton exists and its decisions are executable | **CONFIRMED** | `evidence/skeleton_dryrun.json` (25/25 checks) |
| 10 | The two arms can be compared on T1's `Δ` today | **NOT SATISFIED** | D-A1-2: KAPSO's adapter is still wired to the plumbing task; the wiring and the ordering rule are task-independent and are verified, the retarget is not done |

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

**Evidence (`evidence/wiring_simpleloop.json`, all 8 checks pass).**

```
same_candidate_bytes_same_consumed_outcome          true   (canonical per-candidate Outcome digests equal across a replay)
same_consumed_outcome_same_selection                true   (champion proposal_i1/207 both runs)
honest_ledger_true_equals_handed                    true
the_override_inverts_the_true_ranking               true   true={c02:132, i1:207, i2:0}  handed={c02:132, i1:1, i2:9999}
runtime_selection_follows_the_harness_number        true   champion=proposal_i2 scalar=9999
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

Topology: `runtime ─plaintext─▶ meter_proxy (campaign port) ─▶ repair hop ─TLS─▶ api.deepseek.com`,
with the runtime inside `unshare -rn` reaching the meter only over a unix socket
that the filesystem — not the network — carries. Model `deepseek-flash`,
temperature 0.

| | SimpleLoop (T1 max-cut) | KAPSO (plumbing; D-A1-2) |
|---|---|---|
| campaign id | `C_live_simpleloop` | `C_live_kapso` |
| model calls (meter rows) | 1 | 1 |
| tokens (meter, authoritative) | miss 1192, hit 0, completion 602 | miss 80, hit 0, completion 256 |
| `CEq` | 3600 | 1104 |
| harness `E*` calls | 2 (baseline 132; `ds_i001` 0) | 1 (node0 2.4519205208433132) |
| score of record | 132, `score_source=harness` | 2.4519205208433132, `score_source=harness` |
| session's own claim | n/a | 9.75 (printed by the session, **not** recorded) |
| checks | 8/8 pass | 10/10 pass |

**(a)** the score of record equals the harness's handed value in both arms.
**(b)** ordering: KAPSO's node carries three manifest lines and the harness's is
last (`last_line_is_the_harness_s = true`); the session's claim of 9.75 is
recorded in the artifact and is *not* the score.
**(c)** one row per upstream call, each with an integer `CEq > 0`, cross-checked
against the repair hop's own log of requests that left the machine (1 == 1, 1 == 1).
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
* **The causal-role rule.** `a0/a1/declaration.py` builds `CID` (14 factors: T1's
  `EID*`, `e_star.py`, `e_star_child.py`, the suite and candidate-set manifests,
  the harness service, the ABI, the token issuer, the topology, the meter mode and
  its repair hop, the failure semantics, the model route, the measurement protocol)
  and one `AID_r` per arm. The audit passes on the real declaration, fails on an
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
