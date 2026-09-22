# Harness-owned evaluation in KAPSO: can an external Outcome become the score of record?

**Question.** The measurement study is moving to *harness-owned evaluation*: the harness runs a
frozen evaluator `E*`, produces an `Outcome`, and each runtime must **consume** it as its score of
record — the runtime is not the authority on what a candidate scored. Can our adapter land such an
outcome as KAPSO's score of record with **no upstream edit**, and if so, exactly where?

**Scope.** KAPSO `/home/ebt/kapso_ck/kapso` @ `7d99b152` (read-only; `git status` clean before and
after this work). All probe code lives in `runs/harness-owned-probe/`; the only adapter change is
`a0_adapter/seams.py` (an opt-in `harness_outcome=` field on the adapter's own `_Plan`).
**Zero model calls** were made (see §5).

---

## 1. Verdict

**Landable without any upstream edit — the landing site is `node.score`, reached through two
channels that upstream already reads. Two caveats are attached, and one part of the
harness-owned requirement is *not* satisfiable.**

* **Landing site.** `node.score`, assigned by upstream at exactly three places and consumed by
  everything downstream (§2). The adapter can put the harness's outcome there without touching
  `/home/ebt/kapso_ck/kapso`, because both channels that write `node.score` outside the agent's
  own `<score>` tag are *input* channels KAPSO was designed to read:
  1. **the manifest-of-record line** inside `node.evaluation_output`
     (`registered_evaluation.py:52-102` → `feedback_flow.py:76-93`), and
  2. **the feedback-judge slot** (`feedback_flow.py:66-72`), which our adapter already supplies
     (`runtime.py:196`, `seams.py:62-104`).
* **No gate rejects an externally produced score.** KAPSO's integrity machinery is a *file-hash*
  check on the candidate's evaluator tree (`base.py:740-794`, `evaluation_integrity.py:71-174`).
  It never inspects `node.score`, `evaluation_output`, or where a manifest line came from. A node
  scored by the harness is `evaluation_valid=True`, gets an `EvaluationAttempt` under the
  registered evaluator id at `full` fidelity, and is selectable as parent, best, and deliverable
  (§4, checks HOE-K1/K3/K4/K5/K17/K18).
* **Caveat 1 — the harness must speak KAPSO's contract.** The outcome is only adopted if it is
  labelled with the *granted class triple*: the `KAPSO_EVAL_MANIFEST` line must carry
  `fidelity`/`fraction`/`seed` equal to the granted decision and the registered subsample seed
  (`registered_evaluation.py:87-99`), plus the item-count keys
  (`maintainer.py:70-79`). A bare number is discarded as "not this node's canonical measurement"
  (silently `None`, HOE-K12) or raises (HOE-K12 evidence). Both values are readable from our own
  adapter (`strategy.fidelity_decision`, `strategy.registered_subsample_seed`).
* **Caveat 2 — attribution is a lie that KAPSO cannot detect.** Once landed, the number is recorded
  as a registered-evaluator, `full`-fidelity, seed-1337 `EvaluationAttempt`
  (`registered_evaluation.py:124-159`) — the same ledger that feeds evidence tiers
  (`fidelity.py:156-171`), `select_committed_candidate` (`fidelity.py:184-213`),
  `get_deliverable_score` (`strategy.py:1455-1477`) and the MCP-visible experiment memory
  (`store.py:205-221`, `ideation.py:683-689`). KAPSO will report the harness's number as *its own
  evaluator's* measurement, and nothing in the runtime can tell the difference (HOE-K6/K16).
* **Not satisfiable: "the runtime is no longer the authority."** KAPSO has no first-class external
  *Outcome* intake. The one designed caller-owned-evaluation hook, `iteration_evaluator`
  (`orchestrator.py:151`, `1055-1116`), writes only `node.metrics` / `primary_metric` /
  `external_evaluation_metadata` and is documented as "do not participate in search, stopping, or
  best-candidate selection" (`base.py:85-89`). Grepping `\.metrics` across
  `execution/*.py` and `execution/search_strategies/` finds only the writers
  (`orchestrator.py:1090`, `:1105`) plus `EvaluationAttempt.to_dict`'s own unrelated field
  (`fidelity.py:113`) — no selector reads `node.metrics`. It is
  therefore **not** a score-of-record landing site. In KAPSO's registered regime a score *is* "the
  manifest line the session printed"; whoever supplies that line is the authority, and the harness
  must supply it. There is also no authentication: a candidate session can print the same line
  (only the class triple is checked), so an in-session injection is indistinguishable from a
  harness one. For a measurement study that needs the harness to be the sole author, the injection
  should happen **after** the session ends (our own driver code, between rounds) — see §6.

**Alternative with no fabrication at all:** make `E*` the registered evaluator (which our adapter
already does — `registered_tree.py:124-164`, `runtime.py:301-344`). Then the score of record *is*
produced by the harness's frozen evaluator, bound by `EID_r`, and KAPSO merely consumes its line.
What that does not give is harness **invocation** (the command still runs inside the session,
`registered_evaluation.py:296-377`) nor a route for an outcome the harness computed itself.

---

## 2. Where the score enters KAPSO's state

Assignment sites (only three, all in upstream):

| # | site | what it writes |
|---|---|---|
| 1 | `strategy.py:624-627` (`_absorb_implementation`, step 3) | `node.evaluation_output` = the agent's `<evaluation_output>` tag; `node.score` = the agent's `<score>` tag **if non-null** (`extract_agent_result`, `feedback_flow.py:146-159`) |
| 2 | `feedback_flow.py:66-72` | `node.feedback`, `node.evaluation_valid` = the judge's verdict; `node.score = feedback_result.score if evaluation_valid else None` — **this overwrites #1 unconditionally** |
| 3 | `feedback_flow.py:76-93` | `node.score = manifest_score` when a class-matching manifest-of-record exists **and** `evaluation_valid` |

The manifest of record itself:

* `registered_evaluation.py:52-102` `manifest_of_record` — scans `node.evaluation_output` for the
  **last** line starting with `KAPSO_EVAL_MANIFEST`; returns `None` if there is no registered
  command (`:70-71`) or no line (`:77-78`); enforces the granted class triple (`:87-99`, printing
  "Manifest class mismatch … no mechanical score of record"); requires a `score` key (`:100-102`).
* `strategy.py:1117-1126` `_manifest_of_record` (the strategy-side wrapper; returns `None` when
  `registered_evaluation_command` is empty, `:1119-1120`), `strategy.py:1128-1137` the score variant.
* `maintainer.py:49` `MANIFEST_MARKER`, `:56-61` `evaluation_command` (the
  `python kapso_evaluation/kapso_eval.py --fidelity … --fraction … --seed …` contract),
  `:64-83` `parse_manifest_line` (required keys `fidelity, fraction, seed, items, total_items`;
  positive item counts; **raises** otherwise).
* Grant side: `fidelity.py:304-324` `FidelityDecision` + `FULL_PASSTHROUGH` (`eval_fidelity="full"`,
  `eval_fraction=1.0`); `fidelity.py:241-301` `FidelitySpec`; `budget.fidelity.mode ∈ {off,on,auto}`
  (`fidelity.py:224`). Our adapter takes the `off` path (`runtime.py:346-350`).

Integrity gate (the only thing that can veto a node):

* `base.py:740-794` `enforce_evaluation_integrity` — materializes the candidate branch, runs
  `verify_evaluation_tree(kapso_evaluation/, enforced_manifest)` and `verify_data_manifest`; on
  error sets `evaluation_valid=False`, `score=None`, `should_stop=False` (`:788-793`). Registered
  manifest wins over provided (`:751-752`); `AGENT_GENERATED` provenance skips the check entirely
  (`:753-754`). Called **before** feedback in `_finalize_nodes` (`strategy.py:809-822`) — a node
  that fails it is never judged.
* `evaluation_integrity.py:71-174` — `build_evaluation_manifest` (`:71-109`) /
  `manifest_fingerprint` (`:112-119`) / `verify_evaluation_tree` (`:122-174`): symlink refusal, file
  digests, missing/changed/added files, protected suffixes, executable bits. **Nothing about
  scores.**

Consumption by selection (all upstream, untouched by our seams):

* `strategy.py:1420-1434` `get_best_experiment` — max over `not had_error and evaluation_valid and
  score is not None`.
* `strategy.py:1373-1405` `_select_parent` (`parent_policy="best"`) — `get_best_experiment()`
  (`:1378-1383`); when no scored node exists, the *committed-but-unevaluated* fallback
  (`:1390-1404`) which excludes `evaluation_integrity_error` nodes.
* `strategy.py:1436-1453` `get_deliverable_experiment` → `select_committed_candidate`
  (`fidelity.py:184-213`, needs `evidence_tier > TIER_PROBE`); `strategy.py:1455-1477`
  `get_deliverable_score` → `project_score` (`fidelity.py:142-150`) over the
  `(evaluator_id, "full", 1.0, seed)` comparability class.
* `strategy.py:1236-1245` `refresh_score_projections` re-projects `node.score` from
  `evaluation_attempts` on an evaluator transition (so attempt contents and score stay consistent;
  not exercised here).

---

## 3. The integrity gates, against harness-supplied scores

* The gate keys on **evaluator identity**, not score provenance: a candidate that alters
  `kapso_evaluation/` is voided (`base.py:786-793`, HOE-K11: harness score 42.0 on a doctored tree →
  `evaluation_valid=False`, `score=None`, "Provided evaluation integrity check failed
  (changed: kapso_eval.py)"). A candidate with an **intact** tree and a harness score is valid
  (HOE-K3).
* The only other filter is the manifest **class** triple (`registered_evaluation.py:87-99`), which
  checks labels the harness itself supplies. Wrong class/seed → `None` (HOE-K12), not invalid.
* There is no per-run archive check, run-id, signature, or process-identity check anywhere in the
  score path. `await_registered_evaluation` (`registered_evaluation.py:380-463`) is a *teardown*
  recovery that reads `manifest.txt` from the evaluator's durable archive only when the session
  printed no manifest line.
* Consequence: **a node whose score was not produced by the session's own registered evaluation is
  valid and selectable.** No gate marks it invalid, and none can.

---

## 4. Injection points available to *our* code

Every point below is in our adapter or our run code; **none requires an upstream edit.**

| # | injection point | path:line | whose code | exercised |
|---|---|---|---|---|
| 1 | agent-output `<score>` tag → `node.score` | `a0_adapter/seams.py:275-286` writes it; upstream consumes at `strategy.py:626-627` | ours | yes — and **destroyed**: the tag (1.0) does not survive feedback/manifest (HOE-K2, HOE-K8) |
| 2 | **manifest line in `node.evaluation_output`** → `manifest_of_record` → `node.score` | `a0_adapter/seams.py:224-241` (emitted); upstream `registered_evaluation.py:52-102`, `feedback_flow.py:93` | ours (bytes), upstream (parse) | **yes — this is the landing site** (HOE-K1/K3/K4/K5/K17/K18) |
| 3 | feedback-judge slot (`generate_feedback` → `feedback_generator.generate`) | `runtime.py:196` + `seams.py:62-104`; upstream `feedback_flow.py:48-72` | ours (the judge object) | yes — lands with **no manifest at all** (HOE-K15/K16) |
| 4 | registration switch: `set_registered_evaluation(command=…)` | `runtime.py:338-344`; upstream `base.py:724-738`, gate at `strategy.py:1119-1120` | ours | yes — `command=""` turns the entire manifest path off and makes the judge the sole author (HOE-K13) |
| 5 | out-of-band write to `node.score` / `node.evaluation_output` from our round driver, after the session ends | our driver only | ours | no (available; recommended for a "harness is the only author" design — §6) |
| 6 | runtime monkeypatch of upstream module attributes (the pattern `install_seams` already uses) | `seams.py:107-139` (`strategy_module.generate_solution = …` at `:127`) | ours | no (available; e.g. patching `manifest_of_record` itself) |
| 7 | `iteration_evaluator=` on the `Orchestrator` facade | upstream `orchestrator.py:151`, `1055-1116` | upstream API, our callback | **no — and it cannot work**: writes only `metrics`/`primary_metric`/`external_evaluation_metadata` (`orchestrator.py:1090-1092`), documented observational (`base.py:85-89`), read by no selector. Also unreachable from our current driver, which constructs `GenericSearch` directly (`runtime.py:172-205`). |

---

## 5. Model-free probe — executed

`runs/harness-owned-probe/probe.py` (run with the adapter's own interpreter:
`.venv/bin/python runs/harness-owned-probe/probe.py`). Six scenarios, **18/18 checks pass**
(`runs/harness-owned-probe/probe.json`), ~1 min wall clock, **no model call**: the adapter's seams
replace all three model phases (`seams.py:107-139`), the judge is `SeamFeedbackJudge`
(`runtime.py:196`), and the run directories contain **no session transcripts** (`sessions/` empty
in every scenario). Only local CPU (KAPSO's own maintainer calibration + the independent `E*`
reference run).

What the scenarios do:

* `s1_harness_outcome` — three rounds; **the registered evaluation is never executed**. The harness
  hands in `42.0`, `7.0`, `3.0` (values `E*` cannot produce: `sum_radii` here is ≈0.25–2.45), and
  the `<score>` tag on round 1 is deliberately set to `1.0`.
* `s2_no_manifest` — no manifest line, `<score>` tag only.
* `s3_tamper` — harness outcome *plus* a doctored `kapso_evaluation/` tree.
* `s4_gates` — direct calls on the manifest parser and the config surface.
* `s5_judge_slot` — external score delivered through the judge object, no manifest, no run.
* `s6_restored` — KAPSO's own checkpoint round trip.

**Evidence (from KAPSO's own recorded state).**

* Score of record = harness value, with the session's evaluation never run: node 0 `score=42.0`,
  node 1 `7.0`, node 2 `3.0`; the adapter's seam record for each round carries
  `command=null`, `exit_code=null` (HOE-K1).
* The `<score>` tag is *not* authoritative: tag `1.0` vs recorded `42.0` (HOE-K2); with no manifest
  at all the tag value `5.0` is destroyed and the node ends scoreless (HOE-K8).
* Valid and selectable: `evaluation_valid=True`, `evaluation_integrity_error=""` for all three
  harness-scored nodes (HOE-K3).
* Next round's parent derives from the harness score: round 2's node has `parent_node_id=0`
  (only one finished node), and **round 3 chooses node 0 (`42.0`) over node 1 (`7.0`)** —
  `parent_node_id=0`, `parent_branch_name=generic_exp_0` (HOE-K4). `get_best_experiment` and
  `get_deliverable_experiment` both return node 0, `get_deliverable_score()=42.0` (HOE-K5).
* The runtime did **not** produce that score: an independent `E*` run on node 0's candidate bytes
  (`c02_baseline_upstream`) reports `objective=0.25` (status `ok`), while the score of record is
  `42.0` (HOE-K7). The search therefore follows the harness's ranking, which *inverts* the true
  one.
* Attribution caveat, observed: node 0's ledger holds one attempt —
  `{evaluator_id: 8128cf91…, fidelity: full, fraction: 1.0, seed: 1337, score: 42.0}`, i.e. the
  registered evaluator id (HOE-K6); with **no manifest anywhere** the same thing happens with the
  judge-supplied `99.0` (HOE-K16) — `record_evaluation_attempt` (`registered_evaluation.py:124-159`)
  never consults the manifest.
* KAPSO's own durable state agrees: `s1_harness_outcome/kapso-run-checkpoint.json` is written
  through KAPSO's `RunCheckpoint.create(…strategy_state=strategy.dump_state())` (what
  `orchestrator.py:937-951` persists) and read back through `RunCheckpoint.from_dict`; the recorded
  node history carries `score=42.0` / `7.0` / `3.0` with the attempt ledger (HOE-K17). Restoring
  that payload into a fresh strategy the way `orchestrator.py:308-311` does
  (`load_state`) and then calling KAPSO's own `_select_parent` returns node 0
  (`generic_exp_0`) with `get_deliverable_score()=42.0` (HOE-K18).
* The gate that does fire: tampering (HOE-K11) — `evaluation_valid=False`, `score=None`,
  `evaluation_integrity_error="Provided evaluation integrity check failed (changed:
  kapso_eval.py)"`, no best/deliverable.
* Manifest-class gate, direct calls (HOE-K12): line with the granted triple → adopted
  (`score=42.0`); `fast/0.15/1337` → `None`; `full/1.0/seed+1` → `None`; a line missing `items` →
  `EvaluationMaintainerError: Evaluation manifest line is missing 'items'`.
* Registration gate (HOE-K13): with `registered_evaluation_command=""` a perfectly good manifest
  line yields `None` — downstream, `node.score` would then be the judge's number alone.

---

## 6. Can the session be configured to skip its own evaluation?

**No documented switch does that, and no config makes a missing manifest harmless.**

* `budget.fidelity.mode ∈ {off, on, auto}` (`fidelity.py:224`, `FidelitySpec` `:241-301`) only
  selects *which fidelity class* an iteration is granted; the registered command is still the
  iteration's evaluation and its manifest is still the score of record. Our config uses `off` →
  `FULL_PASSTHROUGH` (`fidelity.py:318-324`), so the granted class is exactly `("full", 1.0)` +
  seed `1337` — the triple the harness must label its outcome with.
* The `evaluation_maintainer` block accepts exactly
  `{type, model, debug_model, agent_specific, subsample_seed, calibration_fraction,
  calibration_timeout_seconds, fast_variant_threshold_minutes, overhead_factor,
  max_change_requests, transition_freeze_fraction, protected_data_paths}`
  (`orchestrator.py:88-101`, confirmed at runtime in HOE-K14). There is **no skip/no-eval key**;
  the block is what *provides and registers* the evaluator. `max_change_requests`
  (`orchestrator.py:848-882`) only caps how many `<evaluation_change_request>` tags are routed to
  the maintainer (a re-registration would move `EID_r`); our config sets `0`.
* The registered command is always rendered into the implementor prompt
  (`registered_evaluation.py:296-377`) and the prompt states there is no sanctioned bypass.

**What happens when no manifest exists** (HOE-K8/K9/K10):

* `manifest_of_record` → `None`; `node.score` is whatever the judge returned
  (`feedback_flow.py:66-72`), i.e. the *runtime's* judge — the LLM's extracted `<score>` — becomes
  the author. KAPSO does not fail, does not mark the node invalid.
* With a judge that has nothing to extract (our seam judge, and any real judge that returns no
  score) the node ends `score=None`, `evaluation_valid=True`: **valid but unscored**, excluded from
  `get_best_experiment`/deliverable (HOE-K9), and still usable as the lineage fallback parent
  (`strategy.py:1390-1404`; HOE-K10 shows round 2 parenting on the scoreless node 0).
* `finalize_run_selection` is skipped (it is only called with a manifest, `feedback_flow.py:94-105`)
  but `_record_evaluation_attempt` still runs if a score exists (`strategy.py:817`).
* A malformed harness line raises out of `parse_manifest_line` into `generate_feedback`'s
  try/except (`feedback_flow.py:117-120`), leaving the judge's score and verdict in place
  (*inferred from code* — the raise itself is executed in HOE-K12; the swallowing was not
  exercised end-to-end).

---

## 7. Remaining work, if "landable" is accepted

1. **Choose the channel and make it the contract.** Recommended: option 2 (the manifest line), with
   the harness writing it from *outside* the session — i.e. after the implementation phase has
   produced its artifact and before `_finalize_nodes` reads it, by setting `node.evaluation_output`
   (the field `registered_evaluation.py:72` reads; the whole scan is O(1)). Two ways, both
   adapter-only: (a) with the implementation phase seamed (as in the probe and in A0.1/A0.2), the
   seam composes the line into the returned agent output — `seams.py:224-241`; (b) with a *real*
   coding-agent lane, our adapter wraps the upstream call site from our side (the `install_seams`
   pattern at `seams.py:126-128`: patch `_absorb_implementation`, or `_finalize_nodes`, so the
   harness line replaces whatever the session printed before feedback runs). Neither edits an
   upstream file; (b) is the variant not exercised here (see item 5).
2. **Derive the class label from the runtime, not by guessing**: read
   `strategy.fidelity_decision.eval_fidelity/eval_fraction` and
   `strategy.registered_subsample_seed` (our process) and emit them in the line; anything else is
   discarded (HOE-K12).
3. **Record the honesty caveat wherever the study publishes scores.** With this design KAPSO's
   `evaluation_attempts`, evidence tiers, `get_deliverable_score`, and MCP experiment memory will
   attribute the harness's number to the registered evaluator. If the study needs the kernel to be
   able to tell harness outcomes from runtime measurements, that has to be carried in our own
   artifacts (as `harness_supplied: true` is, in the probe's line) — KAPSO itself cannot.
4. **Decide what to do about `E*`-in-session.** If `E*` stays the registered evaluator, KAPSO still
   invokes it inside the session (its own frame-run path is `registered_evaluation.py:162-285`).
   A harness that wants to run `E*` itself must therefore use the injection above and accept that
   the in-session run is redundant (or leave the registered tree intact and simply not rely on its
   output).
5. **Not verified here, and requiring a live session (model spend):** variant (b) of item 1 — a
   *real* coding-agent session (codex/claude) must produce an artifact our wrapper can then label
   with the harness line, and the real judge's behaviour when `KAPSO_EVAL_MANIFEST` is absent (the
   LLM-extracted `<score>` becoming the score of record) is not exercised. Neither is needed for
   the seam-driven design the probe verifies (variant (a)): that path is fully exercised, and the
   only session-dependent part it adds is where the wrapper sits.

**Artifacts.** `runs/harness-owned-probe/probe.py` (harness), `probe.json` (18/18 checks, all
recorded values), `s1_harness_outcome/kapso-run-checkpoint.json` (KAPSO's own serialized state),
`s1_harness_outcome/reference/…` (the independent `E*` outcome). Adapter change:
`a0_adapter/seams.py` (opt-in `harness_outcome=` / `score_tag_value=` on `_Plan.push`, plus the
`SEAM_HARNESS_OUTCOME` declaration). Upstream KAPSO is untouched.
