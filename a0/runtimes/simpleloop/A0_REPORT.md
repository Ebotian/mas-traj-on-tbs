# A0 verdicts — SimpleLoop (`a0/runtimes/simpleloop`)

Every claim below is backed by a command executed in this directory. Where something could not be
verified it says so; nothing is reported as working on the strength of an assumption.

Artifacts: `out/a01/` (A0.1 + traces), `out/a01-repeat/` (determinism re-run), `out/a02/` (A0.2 +
three runs), `out/main/` (the primary run), `out/closure/closure.json`, `out/cli-lane/` (the real
agent-CLI failure), `*.summary.txt` (the exact stdout of each command), `policy/`, `tests/`.

---

## 0. The frozen identity this substrate is wired to

```
$ cd /home/ebt/rsi-dev/a0/tasks/circle-packing
$ /home/ebt/rsi-dev/a0/contract/.venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py verify \
      --eid-file plumbing.EID.proposed.json --spec plumbing.contract.proposed.json
clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328   (exit 0)
```

`EID_r → EID*` for SimpleLoop (`native_scheme = none`, `mapping_mode = adapter_declared_injection`,
adapter_contract.md §5.2):

```
$ cd /home/ebt/rsi-dev/a0/runtimes/simpleloop
$ .venv/bin/python -m a0_adapter eidr | python3 -c "import json,sys;print(json.load(sys.stdin)['value'])"
5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e
$ ./tools/recompute-eid-r | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['value'],d['agrees_with_adapter_module'])"
5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e True
```

The scheme is `sha256("a0/simpleloop/eid_r/v1" + 0x00 + canonical_json(payload))` with
`payload = {schema, eid_star, evaluator_source_records, policy_digest}` — the same
domain-separated construction `a0/contract/evalcontract.py` uses for its own components, and bare
64-hex like `eid_star` itself. The adapter publishes `(domain, payload_canonical)` in its
conformance document, so **a third party recomputes the value with their own sha256 and no code of
ours**; the A0 conformance runner does exactly that and reports
`PASS EID-r-recomputes: recomputed a0/simpleloop/eid_r/v1 digest = 5773dfe1… == declared value`
(`a0/conformance/report.md:51`).

> Two defects were found here by building that recomputation and were fixed rather than
> documented around: the declaration claimed a domain-separated hash while `derive_eid_r` hashed
> the bare payload, and the declared value carried a `sha256:` prefix that no third-party
> recomputation could reproduce. Both are corrected; `tests/test_policy.py` now pins the
> declaration against the implementation.

The wire-up is
checked at run start, not asserted: `estareval.py::verify_wiring` re-hashes the two evaluator
source files against the `EvaluatorSource.records` inside the `EID*` document (drift ⇒ adapter
exit 3), and the E* self-reported identity is recorded on every run
(`evaluator_source_sha256 = 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532`,
`e_star.py` sha256 `2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567`, CPython
3.12.11).

> **Corrected (verifier finding R2).** An earlier revision of this report warned that
> `a0/contract/out/plumbing.EID.json` and the value printed in `adapter_contract.md` §1 "still carry
> `EID* = fac50fc4…`". That was false when written: the contract was repaired at 16:57 and the
> canonical document has carried `664115e0…` ever since — verified on the current tree:
> `contract/out/plumbing.EID.json` (mtime 16:57:51) has `eid_star = 664115e0…` with
> `components.EvaluatorSource.records = ['e_star.py', 'e_star_child.py']`, and
> `adapter_contract.md:48` / `contract/README.md:61` print the same value. `local_eval.py` survives
> in that document only as hashed provenance *data* under `components.DataManifest`
> (`records[33,37].data`, `declared.files[30,37]`) and in `MetricDefinition`'s one-ULP note — not as
> the evaluator, which is correct. The superseded `fac50fc4…` now appears only inside revision notes
> that label it wrong (`adapter_contract.md:12,59`; `contract/README.md:104-109,322-324`) and as the
> harness's deliberate negative fixture (`conformance/fixtures/adapters/deviant.py::STALE_EID`),
> never as an identity. What still holds is only the generic caution: a third party must wire
> `plumbing.EID.proposed.json` / `664115e0…`, which is what this substrate does, and anything keyed
> to `fac50fc4…` is keyed to a document that no longer exists.

---

## 1. A0.1 — Evaluator Integration Conformance: **PASS** (14/14)

```
$ .venv/bin/python -m a0_adapter conformance --run-dir out/a01
verdict = pass, passed = 14, failed = []
→ out/a01/conformance.json
```

Method: the substrate's evaluator lane evaluates every member of `C*` in manifest order with
`theta_E = (seed 1337, fidelity full, fraction 1.0, n 26, runs 5, runtime_budget_ms 250, timeout_s 120)`
— the same `theta_E` as the reference table's `canonical_theta_e`
(`a0/tasks/circle-packing/E_STAR.json`) — from a scratch cwd with a minimal `PATH` (`HOME`,
`PATH=/usr/bin:/bin`, no proxy variables, `PYTHONDONTWRITEBYTECODE=1`), so a pass cannot be an
accident of this shell (protocol hard constraint 1, `plan:544`).

Integrity first: every `solution.py`'s sha256 is recomputed against `C_STAR/manifest.json` before it
is evaluated (14/14 match; a tampered copy raises `CandidateSetError` → adapter exit 4 —
`tests/test_contract_lane.py::test_tampered_candidate_aborts_before_evaluation`).

Per candidate, the comparison is against the independently produced reference table
(`E_STAR.json`, sha256 `f5ac1abfa61872541ea92a6a09fcc6178c244d914234211dcc633bac0ea66f5f`), not
against a re-run of the same code path:

| verdict class | candidates | exit code | `status` | check performed | result |
|---|---|---|---|---|---|
| `ok` | c01, c02, c03, c04, c14 | 0 | `ok` | `\|E_r − E*\| ≤ 1e-9` **and** canonical digest equality | **Δ = 0.0 exactly, digest equal** |
| `invalid` | c05, c06, c07, c08 | 2 | `invalid` | exit code, `status`, `failure.kind`, **and `scalar is null`** | match |
| `error` | c09, c10, c11, c12, c13 | 3 | `error` | exit code, `status`, `failure.kind`, `scalar is null` | match |

The `ok` comparison is stronger than epsilon requires: E* reports its own `canonical_digest` of the
whole Outcome on its manifest line, and all five equal the reference table's digest — the substrate
reproduced the reference **bit for bit**, not merely within 1e-9.

Verdict propagation (`plan:513` compares the evaluator, not the number):

* `c05_overlapping` → exit 2, `failure.kind=invalid_configuration`, `failure_stage=verify_failed`,
  detail `overlap_check failed: {'pairs_audited': 325, 'overlap_count': 1, 'min_gap': -0.188609270834101}`;
  `sum_radii` recorded as `null`, `search_signal` as `null` — never 0.0.
* `c09_malformed_import` → exit 3, `failure.kind=candidate_import_failed`, `failure_stage=resolve_failed`,
  detail `SyntaxError: expected ':' (solution.py, line 6)`; `sum_radii` `null`.
* all nine non-`ok` candidates carry `exit_code != 0`, a named `failure_stage` and a
  `failure_detail`; none carries a scalar.

Determinism (repeat run, `out/a01-repeat/`): identical exit codes **and** identical canonical
digests for all 14 candidates, including the timing-sensitive `c13_slow`
(`runtime_budget_exceeded` at the 250 ms p50 budget) — so the A0.1 verdict is stable on this host,
not a one-off.

**Per-row evaluator evidence.** Every row of `out/a01/conformance.json` carries an
`evaluator_evidence` block — `status: "ok"`, the source (`e_star.py evaluate`, frozen CLI), and the
raw material a third party needs to attest freshness without trusting this adapter: E*'s own
`E_STAR_MANIFEST` line and parsed manifest, the row's `canonical_digest`, both source hashes, the
`theta_E` E* actually ran at, `scored` and E*'s verdict. Confirmed against the A0.1 conformance
runner (`a0/conformance/report.md`), which had previously recorded a NOTE because no row declared
evidence:

```
PASS evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)
PASS E-star-manifest-echo: 28 E* manifest echo(es) across 14 candidate(s) verify the frozen
     evaluator source digest, the per-candidate canonical digest and theta_E
PASS F-r-frozen: adapter declares F_r spec_hash='1fa6f941…' == the frozen first-round hash
```

The per-candidate table in that report now shows `evidence = ok` on all 14 rows (previously `-`),
and the runner no longer has to fall back to counting `FailureStage` from the trace: the adapter
declares `failure_stage_counts` and a `F_r` block in the same document.

**A0.1 verdict: PASS.**

## 2. A0.2 — Score → Search Contract: **PASS** (9/9 checks)

```
$ .venv/bin/python -m a0_adapter a02-check --out out/a02/a02_checks.json
verdict = pass, passed = 9, failed = []
```

The checks, each one designed so that it *fails* if the frozen rule is wrong (full evidence in
`out/a02/a02_checks.json`):

| # | check | result | evidence |
|---|---|---|---|
| 1 | `order_invariance` — the same multiset proposed forward and reversed | pass | forward champion `c01_good_hex` = reverse champion `c01_good_hex`, scalar `2.4519205208433132` both times |
| 2 | `tie_break_observable` — the tie pair decides by the frozen rule, and the **rejected** rule gives a different answer | pass | c01/c03 both `2.4519205208433132`, different sha256 (`bca4286e…`/`893d0aa4…`); frozen rule → `c01_good_hex` in **both** orders; rejected earliest-index rule → `c01_good_hex` forward but **`c03_mirror` reversed** |
| 3 | `near_tie_not_absorbed` | pass | gap `c01−c04 = 1.0000000000021103e-04` = **1.0e5 × epsilon**; value order == rank order |
| 4 | `null_never_wins` | pass | `c05_overlapping` has `structure.sum_radii = 2.4519205208433132` — the **highest nominal value in C*, equal to c01** — and is still never champion, because `status=invalid` ⇒ `scalar=null` |
| 5 | `error_verdicts_propagate` | pass | exit 2 → `verify_failed`; exit 3 (`candidate_import_failed`) → `resolve_failed`; both with `scalar=null` and `failure_detail` |
| 6 | `injected_score_moves_selection` | pass | see §3 |
| 7 | `running_max_monotone` | pass | every recorded decision equals `choose(considered)`; champion trajectory `0.25 → 2.4519 … 2.4519`, never decreasing (7 iterations in `out/main`) |
| 8 | `fr_frozen` | pass | every non-injected score event carries `fr.spec_hash = 1fa6f941…580d0` (canonical digest of `a0/contract/fr/scalar.json`); injection events carry the separate frozen hash of `policy/simpleloop.inject.json` |
| 9 | `argmax_is_a_set_function` | pass | permutations `abc`/`bac`/`cba` all return `a`; all-unscored returns `null` |

Check 2 is the one that matters most: it shows the frozen tie-break is *load-bearing*. Had the
workstream taken the obvious "first maximum wins" rule, A0.2's order-invariance requirement would
have failed on this exact pair — the two orders disagree — and the check would have caught it.

The frozen configuration conditions (`plan:557-567`) are stated in
`policy/simpleloop.policy.json` and recorded on every event: no archive/QD, no evolved harness, no
multi-island, no learned operator selection, no external retrieval, no undeclared prompt; the only
state carried across iterations is the running champion `c*_t` and the raw history `H_t`.

**A0.2 verdict: PASS.**

## 3. Evidence that an externally supplied score actually changed the selection

Required verbatim by the study: *"evidence that an externally supplied score actually changed the
selection"*. Two runs, same proposal script, same `C*` bytes, same `theta_E`; only
`--inject-scores` differs:

```
uninjected champion: c01_good_hex       (its real E* scalar 2.4519205208433132)
injected   champion: c02_baseline_upstream  (real E* scalar 0.25, injected scalar 99.0)
```

`out/a02/a02_checks.json` → `checks.injected_score_moves_selection`; run dirs
`out/a02/runs/a02-forward` and `out/a02/runs/a02-injected`.

Honesty conditions on that evidence, all satisfied:

* the score event still carries E*'s **true** multi-field Outcome (`outcome.fields.sum_radii =
  0.25` for c02) — the injection changes `search_signal`, not the recorded measurement;
* the injected runs declare a **different** `F_r` (`policy/simpleloop.inject.json`,
  `spec_hash != 1fa6f941…`), so an injection event can never be pooled with an
  `F_r = scalar(E*)` event, and `selection.reason` says the signal came from `--inject-scores`;
* the injection is a declared channel (`runner.py`, `theta_E.extra.inject_scores_sha256`), frozen
  before the run, not an adapter-side score override.

This is channel *existence* (B0+), not a claim about improvement: the injected value is arbitrary
by construction and the study must not read it as a result.

## 4. Traces — the three files, and the `FailureStage` counts

Primary run (7 iterations, champion `c01_good_hex`, exit 0):

| trace | path | validator (per file) |
|---|---|---|
| score | `out/main/traces/simpleloop.main.score.jsonl` | `valid: 7 event(s)` |
| selection | `out/main/traces/simpleloop.main.selection.jsonl` | `7 error(s)` — cross-file `source_score_event_id`; not a run failure, see below |
| resource | `out/main/traces/simpleloop.main.resource.jsonl` | `valid: 8 event(s)` |
| merged (all three in `event_seq` order) | `out/main/traces/simpleloop.main.all.jsonl` | `valid: 22 event(s)` |

The per-file column is the *reading interface* only. The frozen validation unit is the run's
merged stream, and the contract owner landed exactly that during this round
(`trace_schema.md:29-44`, `adapter_contract.md:403`):

```
$ python a0/contract/trace_validate.py validate-run --run-dir out/main
[ok ] simpleloop.main  events=22  [score=7 resource=8 selection=7]  merged simpleloop.main.all.jsonl
valid: 1 run(s), 22 event(s)
```

All seven runs produced in this directory validate clean under that unit
(`out/a01`, `out/main`, the three `out/a02/runs/*`, and both agent-lane runs), and `run`'s own
summary reports the run-unit verdict separately from the per-file one. Scope of the trailing
`out/` directory: `out/cli-lane/` is a run, not a defect.

`FailureStage` counts — the number for each row comes from the frozen counter, not from an ad-hoc
tally:

```
$ python a0/contract/trace_validate.py stats --trace out/main/traces/simpleloop.main.score.jsonl
events 7 | schema/semantic errors 0 | resolve_failed 1 | other_failures 1 | search_failed 0 | ...
```

(The counts are per `(run_id, iteration, candidate_id)` unit. Count them from the **score** trace:
re-deriving them from the merged stream by hand is easy to get wrong, because the run-scope summary
resource event repeats the last iteration's `candidate_id` and will overwrite that unit's stage in
a naive tally.)

| run | `verify_failed` | `resolve_failed` | `evaluator_failed` | `timeout` | `search_failed` | `comprehension_failed` | `mechanism_mismatch` |
|---|---|---|---|---|---|---|---|
| A0.1 sweep (`out/a01`, all 14 of C*) | 5 | 1 | 2 | 1 | 0 | 0 | 0 |
| primary run (`out/main`, 7 iterations) | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| A0.2 forward / reverse / injected | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| agent-CLI, dead relay (`out/cli-lane/codex`) | 0 | 0 | 0 | 0 | **1** | 0 | 0 |
| agent-CLI, live relay, cut by the cap (`codex-live`) | 0 | 0 | 0 | 0 | **1** | 0 | 0 |
| agent-CLI, live relay, cut by the cap (`codex-live2`) | 0 | 0 | 0 | 0 | **1** | 0 | 0 |
| agent-CLI, live relay, **completed** (`codex-live3`) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| agent-CLI, live relay, **completed** (`codex-live4`) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The A0.1 sweep's 9 non-`ok` verdicts are `C*`'s deliberately degenerate members: 5
`verify_failed` (4 invalid geometry + c11 non-deterministic), 1 `resolve_failed` (c09 does not
parse), 2 `evaluator_failed` (c10 raises, c12 `os._exit`s), 1 `timeout` (c13 exceeds the p50
runtime budget) — i.e. `other_failures 8` in the `stats` line above, decomposed. These are the counts the study's failure-rate analysis will consume; the mapping
from E* verdict to stage is frozen in `policy/simpleloop.policy.json` and proposed to
`a0/contract` so all four runtimes agree (`HANDOFF_to_contract_owner.md` §3).

The selection trace records `parent_{t+1} = c*_t` for every iteration, the `considered` list with
each candidate's `search_signal` (including `null` for unscored ones), the tie-break actually used,
and `source_score_event_id` pointing at the score event that drove the decision.

## 5. Closure: **closed** (search machinery); the solver lane is a separate, conditional question

```
$ .venv/bin/python -m a0_adapter closure-probe --out out/closure/closure.json
verdict = closed, mechanism = external_network_isolation   (exit 0 → closure satisfied)
```

Measured, not assumed (`out/closure/closure.json`):

* positive control — `probe_egress.sh check --mechanism host`:
  `dns=ok tcp=ok tcpvia=example.com:443 https=ok egress=OPEN`;
* negative control — same probe, `--mechanism unshare-rn`:
  `dns=fail tcp=fail tcpvia=none https=fail egress=BLOCKED`;
* the full measurement lane ran to completion **inside** `unshare -rn` and produced the same
  champion and the same scalar as on the host (`c01_good_hex`, `2.4519205208433132`, 3 evaluator
  calls each) — so the lane needs no egress;
* static scan of all 14 modules in `a0_adapter/`: **no** network-capable import
  (`socket`/`ssl`/`urllib`/`http`/`requests`/…).

Scope limit, stated plainly: this verdict covers the search machinery. With
`--solver codex|claude` the substrate inherits that CLI's network posture, so a closed deployment
must run the solver lane inside the same barrier (probe it with `--probe-cmd`) or use
`--solver injected`. SimpleLoop has no retrieval lane at all, which is what `plan:613` requires of
it at A1.

**Cross-reference to the closure workstream** (`a0/closure/closure.simpleloop.json`, probe run
17:13 today, before this driver existed — it records `solvers/` as empty, which is now stale).
Its lane probes are stronger evidence about the solver lane than anything this workstream can
produce, and they agree with the code here. The later, decisive measurement is of the lane *as
shipped*: `a0/closure/evidence/13_simpleloop_lane_closed.json` records a real model turn through
`CliSolver`'s unpatched argv (`patched: false`, `codex exec --sandbox workspace-write
--skip-git-repo-check <prompt>`) returning rc=0 with the in-lane canary persisted by the in-sandbox
shell tool as `LANE_PROBE dns=fail tcp=fail https=fail local=ok egress=BLOCKED`, while the control
`13b_simpleloop_lane_open.json` — same lane, `--sandbox danger-full-access` — persists
`egress=OPEN`. So the probe distinguishes the postures rather than reporting "blocked" for
everything, and the lane this substrate actually launches is the closed one by its own sandbox:

* `codex-workspace-write` → `LANE_PROBE egress=BLOCKED` with a host positive control at
  `egress=OPEN`, including a real model turn
  (`a0/closure/evidence/08_e2e_codex_workspace_write.jsonl`). `CliSolver._command`
  (`a0_adapter/solvers.py:281`) launches exactly `codex exec --sandbox workspace-write
  --skip-git-repo-check <prompt>` — no `--search` — so the codex lane is the *closed* posture by
  config, and their probe is the measurement of it.
* `unsandboxed-shell` / `claude --dangerously-skip-permissions` → only closed with an external
  cut, and their probe adds a sharp edge this workstream's own probe could not see: `unshare -rn`
  also cuts a **host-local** relay (`NETNS_RELAY_HTTP=000` while the host sees `200`). A closed
  deployment whose model endpoint is a relay on `127.0.0.1` therefore cannot run the CLI lane
  inside `unshare -rn`; the barrier must leave the endpoint reachable (sibling container) or the
  lane cannot run closed on this host. My own isolation run did not test this because the injected
  lane makes no model call.

The live relay used for §6 is exactly such a host-local endpoint (`127.0.0.1:15722`, confirmed:
`ss -ltnp` shows `cc-switch` listening, and a real `codex exec` call returned exit 0). So on this
machine the two halves of the closure story are in tension and the study should record it as a
constraint rather than a contradiction: the codex lane is closed *by its own sandbox*, and the
endpoint it must reach lives on host loopback, so a deployment that also cuts loopback cannot run
this lane. Mechanism: `config` (for the lane) + `external_network_isolation` (for everything else),
with the endpoint on the allowed side of the barrier.

## 6. Verification status of the agent-CLI solver lane

**(a) The real solver lane is now VERIFIED end to end.** `--solver codex` runs the real `codex` CLI
(model `gpt-5.6-terra` through the local relay on `127.0.0.1:15722`); on the third bounded attempt
the model produced a parseable `solution.py`, E* scored it, and the loop's frozen argmax selected
it:

```
$ .venv/bin/python -m a0_adapter run --solver codex --solver-timeout 780 \
      --max-iterations 2 --run-dir out/cli-lane/codex-live4 --run-id codex-live4
exit_code = 0        stopped_because = solver_exhausted     failure_counts = {}
iterations = 2       evaluator_calls = 2                    champion = codex_i001
  iter 0  c02_baseline_upstream  E* ok  sum_radii 0.25                (c_0 = baseline)
  iter 1  codex_i001             E* ok  sum_radii 2.5414213562373096  (cli:codex)
                       proposal 282.30 s, E* 0.057 s, iteration 282.36 s
$ python a0/contract/trace_validate.py validate-run --run-dir out/cli-lane/codex-live4
[ok ] simpleloop.codex-live4  events=7  [score=2 selection=2 resource=3]  merged ...all.jsonl
```

That is the second successful real round; the first (`out/cli-lane/codex-live3`, 840 s cap) produced
`codex_i001` with `sum_radii 2.6251746109048` under the pre-fix accounting described below, so its
resource events under-report the iteration cost. `codex-live4` is the artifact to quote for cost:
`proposal_sec 282.30`, `evaluation_sec 0.057`, `iteration_sec 282.36`, `wall_sec 282.40`, and
59,147 tokens for the model turn. The token figure is the CLI's own footer in the raw transcript
(`out/cli-lane/codex-live4/work/iter001/solver.stderr.txt`: `tokens used` / `59,147`), **not** a
field in any `run_meta.json`: the loop gained `tokens_total` on its history rows at 18:55, one
minute *after* `codex-live4` ran, so every recorded run predates the field and none carries it
(checked: `grep -c tokens_total out/*/run_meta.json` → 0 in all of them). `out/refresh-smoke/` is a
cheap injected-lane run through today's code that shows the field is live (`"tokens_total": null`
on its 7 rows — null is correct for a lane with no CLI footer). The trace's
`secondary.T_in`/`T_out` stay null because the CLI reports a single total and forcing it into one of
those fields would mislabel it.

So the whole lane is exercised with the runtime's own machinery: prompt → live model call →
`solution.py` written inside the sandbox → hash → E* evaluation → `F_r` fold → argmax → champion →
traces. The candidate the agent produced (2.6252) beats both the baseline (0.25) and the best
member of `C*` (c01, 2.4519), and the champion changed because of a score the evaluator produced,
which is independent evidence that the selection consumes real evaluations.

Cost, measured on both successful rounds: 394.45 s and 282.40 s of wall clock for two iterations,
of which the two E* calls were 0.040 s / 0.056 s and 0.043 s / 0.057 s. **The agent call, not the
evaluator, is the cost of a SimpleLoop iteration** (ratio ~5000:1), which is exactly what A1's
`B_hard = (T_wall, N_evaluatorCalls, concurrency)` accounting has to capture — and what a
`T_wall` measured at the wrong scope would have hidden.

**(b) What it took to get there, with the failures reported exactly where they happened.**

| attempt | cap | outcome | where it stopped |
|---|---|---|---|
| `out/cli-lane/codex` (dead relay) | 45 s | exit 8, `search_failed` | `codex` retried against a dead listener and timed out — reproduces `ENV_REPORT.md` §3.1 |
| `out/cli-lane/codex-live` | 600 s | exit 8, `search_failed` | relay live; the model ran real turns in the sandbox (wrote `task_plan.md`, `notes.md`), still in "Phase 2 - searching for a high-sum configuration" when the cap hit |
| `out/cli-lane/codex-live2` | 840 s | exit 8, `search_failed` | same, with the transcript on disk: 868 lines of real model work, `solution.py` never written |
| `out/cli-lane/codex-live3` | 840 s | **exit 0** | model wrote `solution.py` (~6 min in) and E* scored it |

Two genuine lane defects were found by watching those runs and are fixed rather than documented
around:

* the prompt rendered "its score is **unknown**" because the lane looked the seed candidate's score
  up under `scalar` while history rows carry it under `search_signal`. `H_t` is supposed to carry
  `c_t`'s score (`plan:610`), so attempts 1-2 ran with less information than the policy specifies.
  The prompt now reads `its score is 0.25.` (verified in the running command line).
* the child inherited the caller's **stdin**, and `codex exec` announces "Reading additional input
  from stdin..." and waits for EOF before starting; and stdout/stderr were buffered in memory until
  exit, so a ten-minute call was neither observable nor recoverable. Now `stdin=DEVNULL` and both
  streams are written to `<work>/iterNNN/solver.{stdout,stderr}.txt` while the call runs. Attempt 3
  reached the writing stage in ~4 minutes where attempt 2 had not after 14 — consistent with the
  stdin wait having cost attempt 2 time, though that is not established on its own.

A third defect, in the *accounting* rather than the lane, was exposed by the first success:
`T_wall` with `scope: "iteration"` measured only the E* call, so `codex-live3`'s resource events
report 0.056 s for an iteration that really cost ~394 s. Fixed (`loop.py::_evaluate` now times the
whole iteration: proposal + evaluation) and every artifact in `out/` was regenerated afterwards —
including a fresh real round, `out/cli-lane/codex-live4/`, which now carries
`T_wall 282.36 s scope=iteration`. `codex-live3`'s own totals remain honest in its `run_meta.json`
(`wall_sec = 394.45`, per-iteration `proposal_sec` / `evaluation_sec`), which is where to read its
cost.

**(c) `claude` — not attempted.** `a0/env/checks/ENV_REPORT.md` §3.2 finds `claude doctor` reporting
"Not signed in to claude.ai"; a billed call was deliberately not made. The lane is implemented
(`--solver claude`) and remains UNVERIFIED. It is not needed for the A0 verdicts, which rest on the
injected lane plus the codex lane above.

**(d) The A0.1 comparison is against the reference table, not a second independent computation of
`E*`.** That is deliberate (comparing two runs of the same code would be circular), and the
reference table is the `a0/tasks/circle-packing` workstream's artifact. If that table is later
regenerated, the conformance verdict must be recomputed; `conformance.json` records its sha256 so
the dependency is visible.

## 7. Findings the other workstreams need

1. **SimpleLoop was missing from the handoff's `R_1` list.** `plan:490` puts it in
   `R_1 = { r ∈ {SimpleLoop, KAPSO, EvE, Loreley} : A0.1_r ∧ A0.2_r }`, and it is the A1 baseline —
   so it needs the same conformance evidence as the real runtimes. It now has it. Had it been left
   out, A1 would have compared two substrates of which one had never been shown to execute the
   frozen evaluator faithfully.
2. **The trace contract could not be satisfied per file — reported and now fixed.** The frozen
   validator resolved `source_score_event_id` inside a single file (`trace_validate.py:186-192`)
   while `trace_schema.md` §1 mandated three separate files, so every selection file reported one
   error per event while its merged stream was clean. Reported to the contract owner (bus message
   #5, `HANDOFF_to_contract_owner.md` §4) with the measured output and three options; they landed
   option (b) during this round: `trace_schema.md:29-44` now makes the run's merged stream the
   validation unit and adds `trace_validate.py validate-run --run-dir <run_dir>`
   (`adapter_contract.md:403`). This adapter already wrote `<runtime>.<run_id>.all.jsonl`, so it
   became conformant with **no change to the traces** — only to how it reports the verdict.
3. **The `E*` verdict → `failure_stage` mapping is unspecified** and the four runtimes must not each
   invent one, or their `FailureStage` counts will not be comparable. Mapping proposed in
   `HANDOFF_to_contract_owner.md` §3.
4. **`E*`'s exit code 2 vs a zero score.** `c05_overlapping` has the *highest nominal*
   `structure.sum_radii` in `C*` (equal to c01's) while being invalid. Any adapter that reads a
   nominal or structural value instead of the gated objective will rank an invalid candidate first;
   this is a second false-green trap beyond EvE's `failure_score(0.0)`, and `C*` is built to expose
   it.
5. **Only one `EID*` is in circulation for this task: `664115e0…`.** (Corrected, verifier finding
   R2 — this item previously asserted that a second, stale identity was circulating.) Every
   identity document in the tree carries it: `contract/out/plumbing.EID.json`,
   `tasks/circle-packing/plumbing.EID.proposed.json`, `tasks/circle-packing/EID_INPUTS.json`,
   `verify/out/myEID.plumbing.json`. The superseded `fac50fc4…` survives only in revision notes and
   in the harness's deliberate stale-EID fixture, so no consumer can mistake it for a live identity;
   `contract/out/sample.EID.json` carries `22c643f8…`, which is the *sample* task's identity, not a
   competing plumbing one. See §0.

## 8. Follow-up round (same day, later)

Three changes were requested and made; this section records them so the earlier sections can be
read with the right history. Short answer for each: (a) per-row evidence emitted and confirmed by
the harness; (a2) the real solver lane is now verified, with four lane/accounting defects found and
fixed along the way; (b) the two frozen blocks the contract owner is copying are **unchanged** —
only `EID_r` (a value outside those blocks) changed.

**(a) Per-row evaluator evidence.** `out/a01/conformance.json` now emits an `evaluator_evidence`
block on every row, and the A0.1 conformance runner confirms it: the `evidence` column of its
per-candidate table went from `-` to `ok`, the `evidence-fresh-or-declared` check dropped its NOTE,
and two checks that had been unavailable because the material was not published now pass —
`E-star-manifest-echo` (28 verified echoes) and `F-r-frozen` (real hash equality). The runner also
no longer falls back to deriving `FailureStage` from the trace: the adapter declares
`failure_stage_counts`. See §1 and `out/a0-conformance-harness.report.md` (a copy of
`a0/conformance/report.md` as produced by the harness for the `simpleloop` runtime).

**(a2) The agent-CLI lane was retried and is now VERIFIED.** Detail in §6. The relay on
`127.0.0.1:15722` was live (a real `codex exec` call returned exit 0), and two bounded real rounds
produced scored candidates: `out/cli-lane/codex-live3` (`codex_i001`, 2.6252) and
`out/cli-lane/codex-live4` (`codex_i001`, 2.5414, with corrected iteration accounting). Three lane
defects were found by running it and fixed: the prompt lost `c_t`'s score (`scalar` vs
`search_signal`), the child inherited stdin (which `codex exec` waits on), and the transcript was
buffered in memory instead of streamed; a fourth defect — `T_wall` at `scope: "iteration"` timing
only the E* call — was exposed by the first success and fixed. What remains unverified is the
`claude` lane only.

**(b) Two `EID_r` defects found and fixed.** Building the third-party recomputation (`tools/recompute-eid-r`) exposed that the declaration claimed a domain-separated hash while
`derive_eid_r` hashed the bare payload, and that the declared value carried a `sha256:` prefix no
independent recomputation could reproduce. Both are fixed; the construction now matches
`evalcontract.py`'s convention and the harness recomputes the value itself and gets it right:

```
$ cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes simpleloop
PASS EID-r-recomputes: recomputed a0/simpleloop/eid_r/v1 digest = 5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e;
                      declared value = '5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e'
verdicts (A0.1 only): {"simpleloop": "PASS"}
```

Consequence for anything that quoted the old value: `EID_r` is now
`5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e` (bare hex, no prefix). Every
artifact in `out/` was regenerated afterwards, so no file in this directory carries the old value.
The frozen `scalarization` / `selection` blocks are **unchanged** — verified mechanically by
`tests/test_policy.py::test_declared_rule_and_implementation_are_the_same_rule`, which is also the
check the contract owner can run against the copy they land in `a0/contract/`.

## 9. Refresh: the A0-wide conventions landed, and the stale lane records are corrected

Three things were re-checked on this pass; each has a command and its real output behind it.

**(a) The proposal was adopted A0-wide.** `a0/contract/selection/simpleloop.selection.json`
(`status: frozen-a0-contract`) now carries this workstream's `scalarization`, `selection` and
`failure_stage_mapping` blocks, and `adapter_contract.md` §5.3 states that the first and the third
are A0-wide — every runtime must declare the same null policy and the same `E*` verdict →
`failure_stage` table, or `plan:577`'s per-runtime `FailureStage` counts are not comparable. The
frozen file's canonical digest is
`ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd`, as §5.3 prints.

**(b) The executed policy still matches the frozen copy** — checked by execution, not by reading:

```
$ .venv/bin/python tools/check-frozen-conventions --out out/conventions-recheck.json
"verdict": "PASS", "failed": []
```

11 checks, all PASS: frozen digest; `scalarization` and `selection` byte-equal across the frozen
copy, `policy/simpleloop.policy.json` and the proposal; 8/8 verdict rows of the frozen
`failure_stage` table reproduced by `traces.failure_stage_for` including the `other` fallback;
`solver_lane_produced_no_proposal` → `search_failed` matching the literal the loop emits at
`a0_adapter/loop.py:305`; the `null`-gate and `nan` rejection in `policy.scalar_of`; the tie-break
returning `c01_good_hex` under both proposal orders while the rejected earliest-index rule flips to
`c03_mirror`; and the recomputed `EID_r` equal to
`5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e` — the value the conformance
handoff reports.

**(c) Stale lane records corrected.** The module docstring and the `CliSolver` docstring in
`a0_adapter/solvers.py` still asserted the CLI lane was UNVERIFIED because "`codex` has no live
endpoint"; that was true when written (the dead `127.0.0.1:15722` was CC Switch's local proxy) and
is no longer, so both now state the verified status, cite the two exit-0 rounds and the closure
probes, and state precisely what remains unproven: the `claude` branch only. The README's closure
section now cites the shipped-lane probes
(`a0/closure/evidence/13_simpleloop_lane_closed.json` with the `danger-full-access` control
`13b_simpleloop_lane_open.json`) rather than the earlier proxy measurement, and its test count was
corrected from 17 to 19 (`pytest tests/ -q` → `19 passed`).

```
$ cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes simpleloop
--- simpleloop ---
    PASS: all checks passed
verdicts (A0.1 only): {"simpleloop": "PASS"}

$ python a0/contract/trace_validate.py validate-run --run-dir <each run in out/>
runs validated: pass=15 fail=0        # 14 recorded runs + out/refresh-smoke
e.g. [ok ] simpleloop.codex-live4  events=7  [score=2 selection=2 resource=3]
```

The refreshed harness report (`a0/conformance/report.md`) carries fresh `evaluator_evidence`
(`status: ok`) on all 14 rows, no NOTE, and no `adapter_unverified_notes` for this runtime.

**(d) One claim was wrong and is corrected rather than repeated.** §6 said the `codex-live4` token
total is "recorded in `run_meta.json`". No pre-refresh artifact contains it: `grep -c tokens_total`
is 0 in the `run_meta.json` of all 14 runs recorded before the field was added, because the loop
gained `tokens_total` on its history rows at 18:55, one minute after `codex-live4` ran. The 59,147
figure is real but its source is the raw transcript
(`out/cli-lane/codex-live4/work/iter001/solver.stderr.txt`), so §6 and the README now say that. To
show the field is not dead code, `out/refresh-smoke/` is a fresh injected-lane run through today's
code (`--solver injected`, no model call): its 7 history rows each carry `"tokens_total": null`,
which is the correct value for a lane with no CLI footer, and it validates clean under the run unit.
A future real round would populate it with the parsed total.

**(e) A second wrong claim, found by the independent auditor (finding R2), is corrected.** §0's
warning and `HANDOFF_to_contract_owner.md` §5 asserted that the contract documents "still carry
`EID* = fac50fc4…`" and that `a0/contract/out/plumbing.EID.json` hashes
`upstream/circle-packing/scripts/local_eval.py`. Both statements are false and were false when
written: the contract was repaired at 16:57, an hour before those files were written at 18:16-18:25.
Verified on the current tree (commands in §0 and in the handoff): the canonical document carries
`664115e0…` with `EvaluatorSource = {e_star.py, e_star_child.py}`, `adapter_contract.md:48` and
`contract/README.md:61` print `664115e0…`, `local_eval.py` appears in the identity document only as
hashed provenance data under `components.DataManifest` (plus `MetricDefinition`'s one-ULP note), and
`fac50fc4…` appears nowhere as an identity — only in revision notes and in the harness's deliberate
stale-EID fixture. The error direction was conservative (it steered readers away from the *correct*
value) but it told third parties the contract was stale when it was not, so all three places were
rewritten rather than softened: §0 above, §7 item 5, and the handoff's §5 tail.

For the record on the auditor's question about a `contract_note`: this adapter has no such field —
`contract_note` is KAPSO's (`a0/runtimes/kapso/a0_adapter/a02.py:882`). The text this workstream
publishes to the contract owner is the handoff, plus the two places above; no machine-readable
artifact of this runtime (`out/**/*.json`, `out/**/adapter.md`, the three traces) ever carried the
false claim — `grep -rn 'fac50fc4\|local_eval' runtimes/simpleloop/` now returns only this
correction's own prose. Nothing executable changed, so no re-run was required; the checks were
re-run anyway and are clean (§9(b) above).
