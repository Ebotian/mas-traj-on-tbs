# EvE adapter for A0 (evaluator conformance + score→search contract)

Owned by the EvE workstream. Everything here writes inside this directory; the pinned EvE
snapshot `/tmp/eve` @ `979065fd2cf1b3be9caf70596478fe27df7815ad` is read-only and is used
through `PYTHONPATH` (never installed into, so no `.pyc`/egg-info is written by this
adapter — verified: importing through this adapter's pattern leaves no new file under
`/tmp/eve`, see "Tree hygiene" below).

## What is here

| path | what it is |
| --- | --- |
| `a0_adapter/` | the adapter package; entry point `python -m a0_adapter` (`run`, `conformance`, `closure-probe`) |
| `steps/eve_evaluator_step.sh.tmpl` | the template for the generated evaluation step that `evaluation.steps` points at |
| `tools/recompute-eid-r` | recomputes `EID_r` from the published inputs alone, importing nothing from the adapter (the auditor's hand-recompute path) |
| `tools/eid_r_mutation_check.py` | the four cases that show `EID_r` changes with `EID*` and is refused for mutated evaluator bytes |
| `selection/eve.selection.json` | EvE's adoption of the frozen A0-wide `scalarization` + `failure_stage_mapping` blocks (canonical digests `d59f0930…` / `201fed78…`), checked at run time by `a0_adapter/selectionmap.py` |
| `DECLARATIONS.md` | the declarations the contract requires (EID_r mapping, seed repo, editable, closure) |
| `tools/replicate_a02.py` | independent replication of the A0.2 N=2 case (quality check on the marginal result) |
| `out/run001/` | the frozen A0.1+A0.2 run: `conformance.json`, `closure.json`, `adapter.md`, `traces/` |
| `out/run002`, `out/run003`, `out/run004/` | the three real codex-backed EvE attempts, each with `real_round.json`; run004 also carries the agent's `logs/optimize/` search artifacts and E\*'s measurement of the packing it found |
| `out/run005/` | the post-fix verification run: the same A0.1+A0.2 command as `run001`, run on 2026-09-20 first against the corrected trace writer and then against the `EID_r` derivation that depends on `EID*` (its `eid_r.value` equals `run001`'s). Not a substitute for `run001` — the sampler RNG is unseeded, so the frequency numbers differ run to run |
| `tools/run_one_eve_iteration.py` | drives one real EvE iteration (`--inject-codex-provider` re-supplies the local Codex provider block) |
| `out/replication/` | the replication record |
| `.venv/` | CPython 3.12.11 with EvE's locked dependency set (`a0/env/checks/eve/locked-reqs.txt`) |

## Conformance-harness contract (a0/conformance)

`a0/conformance/conformance.py` drives this adapter and needs no recovery step. That is a
hard requirement, so the emitted document declares everything it reads:

| what the runner reads | where this adapter puts it |
| --- | --- |
| `theta_E` / `theta_e` (`n`/`runs` allowed under `extra`) | top-level `theta_e`, flat: `seed, fidelity, fraction, n, runs, runtime_budget_ms, timeout_s, defaults_applied, extra` |
| `traces` + `traces_source` | `traces: {score, selection, resource, all}` with `traces_source: "written by this <subcommand> invocation"` — the files are written by the same invocation that produced the numbers (`all` is the run's merged stream, `trace_validation` holds the run-level verdict) |
| `eid_r` + `recompute_cmd` | `eid_r.recompute_cmd` runs `tools/recompute-eid-r` (the standalone derivation of `EID_r` from `EID*`, the evaluator bytes and `fr_spec_hash`) and prints `eid_r.value`; `eid_r.derivation` publishes the same `(domain, payload_canonical)` pair so a third party can recompute it without our code |
| rows | top-level `candidates[]`, one per member of `C*`, carrying `runtime_scalar`, `solution_sha256`, `canonical_digest`, `exit_code`, `failure_kind`, `objective`, `evaluator_evidence` and `theta_e_attempt` |
| `failure_stage_counts` | counted per `(run_id, iteration, candidate_id)` unit from the score trace this invocation wrote |
| the E\* manifest echo | every row carries `raw` = the `E_STAR_MANIFEST {...}` line captured from **inside the runtime's own evaluation lane** |

Verified by execution:

```
$ cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes eve --out report.eve.json
--- eve ---
    PASS: all checks passed
verdicts (A0.1 only): {"eve": "PASS"}
rc=0
```

with, in `report.eve.json` → `runtimes.eve.checks`:

* `theta-E-identical` — **PASS**, "adapter declares theta_E = {\`seed\`: 1337, \`fidelity\`: full,
  \`fraction\`: 1.0, \`n\`: 26, \`runs\`: 5, \`runtime_budget_ms\`: 250.0, \`timeout_s\`: 120.0}" —
  the previous "recovered from E\*'s manifest echoed inside 9 of 14 rows" step is gone;
* `EID-r-recomputes` — **executed**, not `declared_prose`: the runner ran
  `tools/recompute-eid-r` (exit 0) and `recomputed == declared value`
  (`sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a`), i.e. it
  re-derived `EID_r` **from `EID*`** rather than re-hashing an artefact the adapter produced;
* `E-star-manifest-echo` — **PASS**: "56 E\* manifest echo(es) across 14 candidate(s) verify
  the frozen evaluator source digest, the per-candidate canonical digest and theta_E";
* `traces_source` — `"reported by the adapter"` (previously "found by searching the adapter
  directory (these may be a smoke run's traces)");
* `failure_stage_counts` — `{"none": 5, "verify_failed": 5, "resolve_failed": 1,
  "evaluator_failed": 2, "timeout": 1}`, i.e. `failure_stage_accounting.matches_frozen_map: true`
  (before the §4.5 adoption it was `{"none": 5, "resolve_failed": 9}` — see "FailureStage
  accounting" below);
* `E-r-failure-kind` — **PASS**: "9/9 candidate(s) whose E\* verdict is not `ok` declare a
  failure.kind, and every declared kind matches E\*'s", with each row's `e_r_failure_stage` now
  declared and equal to `e_star_failure_stage` (check (c) of §4.5 executed, not absent).

Note the `raw` echo is *not* a second reference run dressed up as evidence: it is the manifest
line E\* itself printed while EvE's evaluation step executed it, captured from
`<eval_workspace>/logs/evaluate/e_star/e_star.stdout.txt`.

## One real codex-backed EvE round (`out/run002`, `out/run003`, `out/run004`)

`tools/run_one_eve_iteration.py` drives EvE's *own* loop — real `EveFactory`, real
`Phase2BatchRunner`, real codex driver, real boundary check, real lineages — with the
adapter's E\* step as the evaluator and one pre-seeded solver entry holding a real
circle-packing baseline as `solution.py`. Configuration: `loop.max_iterations=1`,
`n_workers_phase2=1`, `n_solver_examples_phase2=1`, `n_optimizer_examples_phase2=1`,
`enable_resume=false`, the shipped `codex_exec` driver (model `gpt-5.6-sol`,
`reasoning_effort=xhigh`, `web_search=live`), agent turns and per-rollout wall time bounded,
whole script under an outer `timeout`. Each attempt writes `real_round.json`.

**Attempt 1 (`out/run002`, 95 s): agent lane failed, evaluator lane verified.**
`codex exec` returned exit 1 with

```
unexpected status 401 Unauthorized: Incorrect API key provided: PROXY_MA*AGED
url: https://api.openai.com/v1/responses
```

**Cause, established by reading the runtime:** EvE isolates the agent's Codex HOME
(`providers/agent/codex_isolation.py:42-66`): it symlinks `auth.json` but writes a *thin*
`config.toml` rendered from `CodexLaunchConfig`, which contains no `model_providers` block.
The agent therefore left the CC Switch relay and called `api.openai.com` directly, where the
placeholder key is rejected. EvE's own driver config supports the fix
(`driver.model_provider` + `driver.model_providers.*` → `-c model_providers.<id>.<key>=...`,
`codex_exec.py:466-485`), so no code change is needed.

**Attempt 2 (`out/run003`, 5 min): agent lane worked; the epoch ran out mid-edit.**
With the relay provider injected the agent ran successful turns — `exit_code: 0` on every
tool call, model `gpt-5.6-sol` — reading `README.md`, `guidance/skills/read-eval`,
`guidance/skills/optimize-from-examples`, `solver/evaluate.py`, `solver/candidate.py`,
`solver/README.md`, `guidance/agents/codex/check-runner.toml`, `solver/solution.py`, the
sampled solver example, and an `rg` sweep of the workspace. The rollout then hit the
driver's per-rollout timeout (`Codex exec timed out`, `timeout_seconds=300`), EvE evaluated
the partial output, and iteration 1 completed:

* produced candidate `solver_430fb9ac7f1c` with score
  `{"score": 0.25, "e_star_status": "ok", "e_star_canonical_digest": "b4ddfc46...",
  "eid_star": "664115e0...", "e_star_fields": {...}}` — i.e. **E\*'s own Outcome, produced by
  the adapter's step inside a real EvE iteration**, entered the solver population;
* `solution_sha256 = 18bacee4…` = the untouched baseline, so the agent produced no edit
  within its budget. This is a time-boxed probe, not a capability test.

**Attempt 3 (`out/run004`, 662 s, `--turns 14 --turn-timeout 660`): the agent optimised, the
epoch ran out before write-back.** The agent worked on the real task: it wrote
`logs/optimize/search_packing.py` (a `scipy.optimize.minimize` search over 26-circle
layouts), iterated several seeds, kept its best per seed
(`best_packing.txt` 2.60506, `best_141421.txt` 2.61505, `best_271828.txt` 2.61393,
`best_161803.txt` **2.616871696851752**, `best_314159.txt` 2.616871696852813 — against the
seed baseline 0.25), and its final messages describe inspecting the 2.61687 contact graph
against the published 2.635 target. The driver then hit its per-rollout timeout
(`agent_error.txt`: `Codex exec timed out. timeout_seconds: 660.0`), EvE evaluated the
partial output, and iteration 1 completed with `solver_fc3655bd06e2` at E\* = 0.25 on the
unchanged baseline (`solution_sha256 = 18bacee4…`, 1441 bytes, written by the prefill at
18:26 and never rewritten).

The agent's artifact was measured separately, because the interesting number is what its
search actually reached:

```
$ e_star.py evaluate --candidate <transcribed logs/optimize/best_161803.txt> --fidelity full
E_STAR_MANIFEST {... "objective": {"name": "sum_radii", "value": 2.6168716968517516}, "status": "ok" ...}
```

E\* says **2.6168716968517516** for the agent's own packing while the agent's file declares
`2.616871696851752` — agreement to ~1e-15, `overlap_count: 0`, `min_gap: -1.17e-14` inside E\*'s
1e-9 overlap tolerance. So the agent's internal objective and the frozen evaluator agree; what
the round lacked was the write-back into `solver/solution.py` before the budget ended. The
transcription is the adapter's, not the agent's, and is labelled as such
(`/tmp/a0-agent-packing`); it measures the agent's artifact, it does not claim the agent
produced `solution.py`.

**What these three attempts establish.** The evaluator lane is verified *inside the loop*:
EvE's own `SolverEvaluator.evaluate` invoked the adapter's step on the loop's candidate and
E\*'s multi-field Outcome entered the solver population. The agent lane is verified up to a
live model conversation through EvE's real `codex_exec` driver with the pinned model
(`gpt-5.6-sol`), including real tool calls and a real optimisation run — and it required
injecting the local provider block (below). Still not observed: an agent completing its edit
inside the budget, so no round shows an *improvement*; the recorded candidate is always the
seed. For a successful A1-style round the preset needs either a larger
`driver.timeout_seconds` or an explicit write-back-before-check instruction; that is a budget
observation, not a defect of the runtime.

## Reproduce

```bash
cd a0/runtimes/eve
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m a0_adapter run \
  --runtime eve --task circle-packing \
  --candidate-set ../../tasks/circle-packing/C_STAR/manifest.json \
  --eid ../../contract/out/plumbing.EID.json --spec ../../contract/plumbing.contract.json \
  --theta seed=none,fidelity=full,fraction=1.0 --fr ../../contract/fr/scalar.json \
  --run-id eve-a0-run001 --run-dir out/run001
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m a0_adapter closure-probe \
  --runtime eve --run-dir out/run001 --out out/run001/closure.json
```

The `EID_r` derivation is checkable without running the adapter at all:

```bash
cd a0/runtimes/eve
.venv/bin/python tools/recompute-eid-r                     # the value, from published inputs
.venv/bin/python tools/eid_r_mutation_check.py             # M1-M4: it tracks EID*, byte for byte
```

Exit codes are the contract's. The full `run` above exits `0`: A0.1 passes on every
measurable candidate, both independent traces and the A0.2 frequency test ran, and the run
recorded the false-green trap rather than being fooled by it.

Cleaning a run directory needs `chmod -R u+w` first: EvE makes the eval workspace's
`solver/` and `logs/optimize/` read-only (`workflow/evaluation.py:734-742`), so a plain
`rm -rf` fails.

## Verdicts

### A−1 wiring

`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`, taken from
`a0/contract/out/plumbing.EID.json`; `evalcontract.py verify` is run before every adapter
invocation and a non-zero exit aborts with code 3 (none did).
`eid_r = {native_scheme: none, mapping_mode: adapter_declared_injection, value: ...}` with

```
EID_r.value = 'sha256:' + sha256("a0/eve/eid_r/v1" ‖ 0x00 ‖ canonical_json(payload))
payload     = {schema, eid_star, native_scheme, mapping_mode,
               evaluator_source{digest,files}, fr_spec_hash}
```

`derives_from_eid_star` is the pinned `EID*` on every one of the run's 24431 events
(`out/run001`; 30 score + 12200 selection + 12201 resource), and `eid_star` is an **argument of
the hash** — see "EID_r is derived from EID*, not asserted next to it" below.
`theta_E.seed` is recorded as `null` with
`defaults_applied.seed` naming the fixed equivalent 1337 (EvE injects no seed:
`workflow/evaluation.py:290-318`).

#### EID_r is derived from EID*, not asserted next to it (audit R3, fixed 2026-09-20)

The first revision made `EID_r.value` the sha256 of the evaluation step script *the adapter
itself generated* (`sha256:60ee4117…` in the conf run). It recomputed, but nothing in that
recomputation forced the value to depend on `EID*`: a step that ignored `EID*` would have
recomputed equally well, which is exactly what `plan:517` ("EID_r derived from EID*") rules out
(`verify/VERDICT.md` R3).

`EID_r.value` is now `sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a`,
a domain-separated hash **over a payload that contains `eid_star`** plus `EID*`'s
`EvaluatorSource` component (its `records` re-hashed from
`tasks/circle-packing/{e_star.py,e_star_child.py}`, so a mutated evaluator cannot be hashed under
a stale identity) and `fr_spec_hash`. Consequences, each verified by execution in
`tools/eid_r_mutation_check.py`:

| case | result |
| --- | --- |
| M1 the published `EID*` recomputes to the declared value, with `tools/recompute-eid-r` (imports nothing from the adapter) | **PASS**, exit 0 |
| M2 one nibble of `eid_star` mutated → `b903b051…` becomes `9635bba9…` | **PASS** |
| M3 one byte of `e_star.py` mutated → the recomputation refuses, exit 3 | **PASS** |
| M4 the adapter refuses a mutated `EID*` document outright (`evalcontract verify`, exit 3) | **PASS** |

The conf run's `EID-r-recomputes` check is `executed` (the runner ran the recompute command and
got exit 0, `recomputed == declared`). The payload is deliberately run-invariant; the rendered
step's own provenance (`injected_step`: path, sha256, template sha256) is published next to
`EID_r` in `conformance.json` and `adapter.md` rather than hashed into it, because the step
embeds the run's absolute state-dir path — hashing it would make `EID_r` a per-directory value
instead of an evaluator identity. `out/run001` and `out/run005` therefore carry the *same*
`EID_r`, although their step scripts differ (`run001`'s was rendered before the
`--runtime-budget-ms` flag was added to the template).

### A0.1 — PASS: **5 measured rows + 9 declared synthesised zeros**, with the false-green trap detected

**This is not 14 reproduced verdicts.** The A0.1 formula `E_r(c) = E*(c) ± ε` is checked on the
five candidates `E*` measured with `status == "ok"`. For the other nine, EvE's lane has no way to
express `E*`'s `invalid`/`error` verdict at all — its step raises, `SolverEvaluator.evaluate`
swallows the exception and EvE substitutes `evaluation.failure_score` `{score: 0.0, summary:
"evaluation failed"}` (`workflow/evaluation.py:161-165`). Those nine rows are a **declaration about
what EvE could not produce**, never a comparison of runtime and reference verdicts; the conformance
runner labels them `SYNTHETIC_DECLARED` and the adapter marks them
`evaluator_evidence.status = "synthesized_failure"`. A reader must take EvE's A0.1 result as
**5/14 measured**. The same accounting is machine-readable in `conformance.json` →
`a01.agreement_scope` and top-level `a0_1_scope`.

All 14 members of `C*` were evaluated twice — the reference `E*` outside any runtime, and
EvE's own `SolverEvaluator.evaluate` path (`workflow/evaluation.py:119-165`) with the
adapter-pinned step — but only the first five rows below are *comparisons*. Results
(`out/run001/conformance.json` → `a01.candidates`):

| candidate | `E*` status | `E*` `failure.kind` | `E*(c)` | `E_r(c)` | classification | `failure_stage` (frozen table) |
| --- | --- | --- | --- | --- | --- | --- |
| c01_good_hex | ok | — | 2.4519205208433132 | 2.4519205208433132 | match | `none` |
| c02_baseline_upstream | ok | — | 0.25 | 0.25 | match | `none` |
| c03_mirror | ok | — | 2.4519205208433132 | 2.4519205208433132 | match | `none` |
| c04_near_tie | ok | — | 2.451820520843313 | 2.451820520843313 | match | `none` |
| c14_near_zero | ok | — | 2.6e-05 | 2.6e-05 | match | `none` |
| c05, c06, c07, c08 | invalid (rc 2) | `invalid_configuration` | none | 0.0 | synthesized failure | `verify_failed` |
| c09_malformed_import | error (rc 3) | `candidate_import_failed` | none | 0.0 | synthesized failure | `resolve_failed` |
| c10_raises | error (rc 3) | `candidate_call_raised` | none | 0.0 | synthesized failure | `evaluator_failed` |
| c11_non_deterministic | error (rc 3) | `non_deterministic` | none | 0.0 | synthesized failure | `verify_failed` |
| c12_exit_without_artifacts | error (rc 3) | `child_terminated_early` | none | 0.0 | synthesized failure | `evaluator_failed` |
| c13_slow | error (rc 3) | `runtime_budget_exceeded` | none | 0.0 | synthesized failure | `timeout` |

Agreement is **bit-exact** (delta 0.0, `epsilon` 1e-9 never needed) on all five measurable
candidates — EvE executes the frozen evaluator faithfully, and the score EvE puts in the
population is `fields.sum_radii`, not a runtime-side recomputation. That is the whole of the
measured evidence: **5 rows**.

The nine non-measurable candidates are the trap, and they are **not** agreement. Their trace
units carry the stage the frozen A0-wide table assigns to `E*`'s own `failure.kind` — never
`none`, and never a stage this adapter picked: no comparable `E_r` value exists, so they are not
a match and not a conformance failure either — they are an observation EvE cannot produce at all
(it cannot report `invalid`/`error`; it reports `0.0`), and the 0.0 sitting in the population is
EvE's `failure_score`. Read the verdict as `A0.1 = PASS on 5/14 measured candidates`, never as
`14/14 agree`.

### The false-green trap — demonstrated on real runtime code, three routes

`out/run001/conformance.json` → `a01.trap` and `trap_reproduction_shipped_step`.

| route | how it arises | returned payload | step status | `error.txt` |
| --- | --- | --- | --- | --- |
| R1 | the adapter step propagates `E*`'s exit 2/3; EvE's `except Exception` swallows it (`workflow/evaluation.py:161-165`) | `{score: 0.0, summary: "evaluation failed"}` | `failed` | present at the eval-log root |
| R2 | the *shipped* `evaluation.sh` runs an evaluator that exits 7; the script writes a failure payload and **exits 0** (`configs/eve/evaluation/circle_packing/evaluation.sh:56-72`) | `{score: 0.0, summary: "evaluation command failed"}` | **ok** | present |
| R3 | the *shipped* step runs the task repo's own `evaluate.py`, which returns a numeric score with `status: "error"` | `{score: 0.0, status: "error", summary: "centers must be ..."}` | **ok** | **absent** |

All three produce a population score of exactly 0.0. `C*`'s smallest genuine measurement is
`2.6e-05`, so **no threshold on the score can separate them** — which is the point: without
the side channel, R1 and R2 are invisible; without reading the payload's own status field,
R3 is invisible even though EvE accepted it (`_validate_score_shape` only checks that the
`score` leaf is numeric, `workflow/evaluation.py:924-935`).

The adapter therefore never lets the number decide: `evaluator_evidence.status` comes from
(a) payload equality with `evaluation.failure_score` / `boundary_failure_score`, (b) the
step's `status.txt` and the eval-log-root `error.txt`, and (c) a failure marker in the
payload's own status vocabulary. The third rule is the adapter's own addition and is
documented as such; it is what caught R3.

### A0.2 — PASS: the runtime consumes scores by the selection semantics it claims

Tested against the runtime's **real** machinery, at three named seams (`out/run001/
conformance.json` → `a02.seams`): the sampler is the class `loop.sampling.solver_examples`
names, instantiated by Hydra from the shipped config (S1); the draw comes from the real call
site `Phase2BatchRunner._sample_solvers` with the population's unseeded RNG (S2); and the
observable is the `{solver_examples_block}` order **read back out of the rendered Phase-2
README** (S3). The observable's own validity is asserted first: on every case the parsed
README order equals the sampler's returned order (`observable_self_check
.order_matches_sampler_return = true`).

12 200 iterations, one draw per iteration (not per worker):

| case | n (effective) | p̂ | expected p | p-value vs expected | competing expectation | p-value | 
| --- | --- | --- | --- | --- | --- | --- |
| E1/E5 `solver_examples`, N=2, `num=min(4,2)` | 2000 (2000) | 0.7540 | 0.7310586 | 0.020 | uniform (0.5) | 2.1e-119 |
| control: same case, injected swapped scores | 2000 (2000) | 0.2630 | 0.2689414 | 0.562 | uniform (0.5) | 1.6e-103 |
| E6 `solver_prefill` `UniformSampler` (must not be used as the score test) | 200 (200) | 0.4950 | 0.5 | 0.944 | rank-softmax 0.731 | 1.9e-12 |
| E7 `solver_examples`, N=4 | 2000 (2000) | 0.6470 | 0.6439143 | 0.779 | 0.731 (wrong population) | 1.6e-16 |
| E8 second draw, N=4, no re-ranking | 6000 (1420 qualified) | 0.8535 | 0.8437947 | 0.324 | re-ranking 0.8807971 | 0.0021 |

Reading:

* the position-0 frequency follows the frozen class's own expectation, and the
  population-size-sensitive alternative is rejected (E7: 0.647, i.e. 0.6439, **not** 0.731);
* the second draw is **not** re-ranked (E8: 0.8535 vs 0.8438, and the re-ranking value
  0.8808 is rejected at p = 0.0021) — this is the `no_replacement` path keeping its original
  weights, `samplers/base.py:41-64`;
* the prefill control behaves exactly as the protocol warns: score-independent, ≈0.5, and it
  cannot be confused with 0.731 once the expectation is stated per class;
* **the externally supplied score decides the selection**: the two control rows differ only
  in the score payload, and the same candidate's position-0 frequency moves from 0.754 to
  0.263 (two-proportion z = 31.1). In the swap case the score was *injected by the adapter*
  and marked `evaluator_evidence.status = "not_run"`, so this is a test of the machinery, not
  a claim about `E*`.

**Honest note on E1.** In this run p̂ = 0.7540 sits just under α = 0.05. A second full run of
the same case gave p̂ = 0.7300 (p = 0.92). `tools/replicate_a02.py` then drew six further
independent replicates of 3000 (`out/replication/e1_replication.json`):
p̂ = 0.7290 pooled over 18 000 draws, z = −0.62, p = 0.53, replicate range 0.7237–0.7380 —
consistent with 0.7310586. The single marginal rejection is sampling noise, and the study
should quote the pooled figure. Iteration counts exceed the pre-registered binding case
(~515) by a factor of ~4.

`p`-value implementation: exact two-sided binomial on the probability-ordering rule,
verified equal to `scipy.stats.binomtest` to 3.4e-14
(`a02.power_table_reproduced._p_value_selftest`). The independent recomputation of the
pre-registered `n` reproduces the normal-approximation counts exactly (43 / 290 / 502) and
gives slightly smaller exact counts (44 / 289 / 496 vs 46 / 295 / 515) because the critical
region is the strict probability-ordering set; both are below the 2000 used, so the binding
requirement is met either way.

### FailureStage accounting — EvE adopts the frozen A0-wide table

`adapter_contract.md` §4.5/§5.3 require every runtime's A0.1 row to agree with `E*` on `status`,
`failure.kind` **and** the `failure_stage` the frozen table derives from them, because that table
is the only thing that makes `plan:577`'s per-runtime `FailureStage` counts summable. EvE's first
revision staged *every* non-measurable candidate `resolve_failed`: the kinds were right on all
nine rows, but `invalid_configuration` → `verify_failed`, `non_deterministic` → `verify_failed`
and `runtime_budget_exceeded` → `timeout` were all collapsed into `resolve_failed`, so the
declared counts were `{none: 5, resolve_failed: 9}` against the frozen map's
`{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}` and the
conformance runner reported `matches_frozen_map: false`. **Fixed**: the staging is now the adopted
table itself.

* `a0/runtimes/eve/selection/eve.selection.json` is the runtime-side declaration; its
  `failure_stage_mapping` and `scalarization` blocks are byte-equal (after canonicalization) to the
  contract's canonical copy `a0/contract/selection/simpleloop.selection.json`.
* `a0_adapter/selectionmap.py` re-derives both blocks' canonical digests at run time, compares
  them with the frozen values (`failure_stage_mapping` = `201fed78…`, `scalarization` =
  `d59f0930…`) and with EvE's copy, and the adapter **refuses the run** (exit 3) if any of the
  three disagrees. The `kind → stage` lookup is derived from the adopted table, not from a second
  hand-written list that could drift.
* the same stage is written to the trace event and to the row, so check (c) of §4.5 cannot drift
  between them; `conformance.json` carries `failure_stage_accounting_basis` with the table, both
  digests and the adoption check.

Declared counts over `C*`, and the runner's verdict:

```
$ cd a0/conformance && python3 conformance.py run --runtimes eve --out report.eve.json
  failure_stage_counts: {"none": 5, "verify_failed": 5, "resolve_failed": 1,
                         "evaluator_failed": 2, "timeout": 1}
  failure_stage_accounting: {"declared_units": 14, "comparable_to_C*": true,
                             "matches_frozen_map": true,
                             "note": "the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts"}
```

**One declared extension, 0 rows in this run** (`a01.failure_stage_extension`, and raised for the
contract owner in `DECLARATIONS.md` §4.2): a candidate whose `E*` verdict is `ok` but whose
runtime attempt failed anyway (`mismatch`, or a synthesised score where `E*` measured) has no
entry in a table that maps `E*` verdicts, and staging it `none` would erase a real runtime
failure. Those rows are staged `evaluator_failed` and counted separately. If one fires, the
declared counts stop equalling `expected_from_frozen_map` *by design* — that difference is the
finding, reported rather than re-mapped away. No row in this run needs it.

`out/run001` is the frozen A0.1+A0.2 record, so its nine non-`ok` units were **restaged in
place** rather than by re-running the run (the sampler RNG is unseeded, so a re-run would not
reproduce its numbers). The restaging was derived from the run's own reference outcome files with
`a01.stage_of`, and `out/run001` and the freshly executed `out/run005` stage all 14 `C*`
candidates identically, detail text included. `conformance.json` → `traces_note` records it.

### FailureStage counts and trace paths

`trace_validate.py stats` on the run's merged stream (`out/run001/traces/`):

```
$ python a0/contract/trace_validate.py stats --trace .../eve.eve-a0-run001.all.jsonl
events              24431
schema/semantic errors 0
  search_failed          0
  resolve_failed         1
  comprehension_failed   0
  mechanism_mismatch     0
  other_failures         8      # verify_failed 5, evaluator_failed 2, timeout 1
  events[eve] 24431
```

| file | events | role |
| --- | --- | --- |
| `eve.eve-a0-run001.score.jsonl` | 30 | the 14 `C*` A0.1 rows + the 2 shipped-step trap-reproduction units + the 14 A0.2 sampling units |
| `eve.eve-a0-run001.selection.jsonl` | 12200 | one decision per A0.2 iteration |
| `eve.eve-a0-run001.resource.jsonl` | 12201 | one per iteration + the run-level unit |
| `eve.eve-a0-run001.all.jsonl` (merged) | 24431 | the run's stream; the only valid validation target |

The `C*` accounting (`conformance.json` → `a01.failure_stage_counts`) is
`{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}` — the frozen
map, as the runner confirms. The run's *own* 30 score units also carry `{none: 21, …}` because the
trap-reproduction and A0.2 units are appended to the same trace
(`conformance.json` → `failure_stage_counts_scope` says which is which).

Only the run-level command is valid. `stats`/`validate` applied to a single per-kind file is the
old per-file rule: the selection file cannot resolve `source_score_event_id` at all, so
`validate --trace <selection.jsonl>` now reports 12200 errors by construction
(`adapter_contract.md` §6.3). Every one of the 12200 selection events cites a
`source_score_event_id`, and all 12200 references resolve in the run's merged stream — the unit
the reference is defined over (`trace_schema.md` §1.1):

```
$ python a0/contract/trace_validate.py validate-run --run-dir a0/runtimes/eve/out/run001
[ok ] eve.eve-a0-run001  events=24431  [score=30 selection=12200 resource=12201]  merged eve.eve-a0-run001.all.jsonl
valid: 1 run(s), 24431 event(s)
rc=0
```

**Defect fixed (2026-09-20).** The first version of this run passed the three per-kind files
to `trace_validate.py validate` one at a time, and that validator resolved
`source_score_event_id` only against score events in the *file being validated*
(`trace_validate.py:198-206`). The adapter therefore re-stated each cited score event inside
the selection file. Under run-level validation those 14 copies are what they always were:
score events sitting in the selection file, duplicating the score file's `event_id`s —
`28 errors = 14 duplicate event_id + 14 kind-purity`. Three files valid separately, one
invalid run. The copies are gone, the three per-kind files now partition the run, and the
merged `.all.jsonl` is written by the same `emit` that writes the per-kind files
(`a0_adapter/traces.py`).

### Closure — `egress_detected` for the shipped configuration; `closed` is reachable only via `codex_tmux`

`out/run001/closure.json` (probe exit 6). The sharp claim to check was whether EvE's default
full-run path is closable by configuration. It is not, and there is now probe evidence rather
than a source reading:

* **Scope of this record.** It is authoritative for **EvE as shipped**: which driver the shipped
  config selects, the argv EvE's own builder emits for it, and whether that shipped path is
  closable by configuration. The *per-posture lane breakdown* (each lane under each sandbox
  posture, with an unblocked control) is `a0/closure/closure.eve.json` + `a0/closure/VERDICTS.md`,
  whose executed `rc=0` observations (`a0/closure/evidence/07`, `08`, `09`) are also authoritative
  for the claim "the agent lane is reachable" — that claim rests on an `rc=124` attempt here.
  `closure.json` → `scope` records the same split. The two records agree on the **probe** verdict
  for the shipped path (`egress_detected`; not closable by configuration) — the closure
  workstream's *study-level* verdict for EvE is `CONDITIONAL`, shipped default OPEN — and they are
  meant to be quoted together.

* `codex_exec` has **no sandbox parameter**, and its argv always contains
  `--dangerously-bypass-approvals-and-sandbox` (built by EvE's own `_argv`,
  `providers/agent/drivers/codex_exec.py:421-447`, flag at `:434`). This is the driver the
  shipped config selects (`configs/eve/driver/codex_max.yaml:6`, `web_search: live` at `:12`).
* **Probe, shipped flags:** `codex exec --dangerously-bypass-approvals-and-sandbox`, asked to
  run the canary from its own shell tool → the sandbox reports `danger-full-access`; one
  attempt returned `curl` exit 0 (the sentinel answered), the repeat did not finish writing
  its exit file within the wrapper timeout. Egress **OPEN** → `verdict = egress_detected`,
  exit 6. The shipped configuration is not closed.
* **Probe, protocol's recipe:** `codex exec --sandbox workspace-write` (the `-s` value the
  `codex_tmux` driver passes, `drivers/codex_tmux.py:555-570`) → **both** attempts `curl`
  exit 7, "Failed to connect to example.com:443 ... Could not connect to server" in **0 ms**.
  Egress **BLOCKED**. That is the Codex-CLI `workspace-write` / `network_access: false`
  guarantee the protocol leans on, now verified on this host instead of assumed — so EvE *is*
  closable, but only by switching the driver to `codex_tmux` with `web_search: disabled`.
* A host-side sentinel control (3 × `curl` → HTTP 200) is recorded so a sandbox timeout
  cannot be blamed on a dead sentinel; a timeout is classified `INCONCLUSIVE`, never
  `BLOCKED`.
* Corrections to the acceptance work: `allow_network` **does exist** in EvE —
  `runtime/driver.py:380-387` maps it to the sandbox mode, and
  `providers/agent/config.py:24-32,86` + `providers/agent/python_runtime.py:20,332` apply it
  to the workspace-local Python wrapper. Its conclusion stands (the shipped path cannot be
  closed), but the stated reason needs fixing.
* Limits, recorded in `closure.json` → `evidence.probe_limits`: `probe_egress.sh` cannot
  observe a *tool call made by an agent it spawns* (it appends its canary to its own shell),
  so the agent lane was probed by instructing codex to run the canary and persist its exit
  code; `web_search: disabled` was verified only as an argv value, not as an observed absence
  of search; the `workspace-write` refusal happened at the host proxy (loopback blocked), so
  the direct-connect path was not separately exercised.
* Also recorded: `codex` **works again** on this host (model `gpt-5.6-terra` answered at
  17:26 on 2026-09-20), contradicting `a0/env/checks/ENV_REPORT.md` §3.1. EvE's shipped
  driver config pins `model: gpt-5.6-sol` (`codex_max.yaml:9`), a different id, so a full EvE
  run must be re-checked against that id before it is claimed to work.

The adapter's `run` does **not** exit 6 on this finding: it never starts an agent, and its
own lane (candidate execution) is closed by `unshare -rn` and probed. The closure verdict is
reported separately, as the contract's separate `closure-probe` command requires.

`N_evaluatorCalls` on the run-scope resource event counts the **runtime-lane** evaluations
(EvE's own `evaluate()` calls: 14 candidates + 1 trap reproduction = 15). The 14 independent
reference runs of `E*` are recorded per candidate in `conformance.json` → `a01.candidates`
(`reference_*`) and are not runtime evaluator calls.

## What is UNVERIFIED

* **The LLM-driven end-to-end path.** No EvE iteration was run with a real optimizer/solver
  agent. A0.1 exercises the evaluator lane through EvE's own `evaluate()`; A0.2 exercises the
  sampling and selection machinery through the real sampler classes and the real call site.
  Nothing here shows an agent improving a candidate.
* The lm-lane closure claim for a *configured* `codex_tmux` run: the two sandbox modes were
  probed, but the full `codex_tmux` driver (tmux pane pool + hooks) was not stood up.
* The `optimizer_examples` and `produced_optimizers` sampling sites, which need the optimizer
  population frozen as well (`a0/acceptance/DERIVATIONS.md` §1.1).

## Cross-workstream notes

1. **`codex` works again on this host, and the pinned model id resolves.** At 17:26 on
   2026-09-20 the relay answered (model `gpt-5.6-terra`), contradicting
   `a0/env/checks/ENV_REPORT.md` §3.1. Because EvE pins `model: gpt-5.6-sol`
   (`configs/eve/driver/codex_max.yaml:9`) and a silent model-id mismatch would change what an
   EvE run means, the pinned id was probed directly:

   ```
   $ codex exec -m gpt-5.6-sol   --sandbox read-only --skip-git-repo-check 'Reply with exactly: MODEL_OK'
   model: gpt-5.6-sol      → MODEL_OK        rc=0   (11 442 tokens)
   $ codex exec -m gpt-5.6-terra ...
   model: gpt-5.6-terra    → MODEL_OK        rc=0   (4 592 tokens)
   ```

   Both ids resolve through the relay, so an EvE run really does use `gpt-5.6-sol`.
2. **EvE's isolated Codex HOME drops the provider block** (see the real-round section). Any
   A0/A1 EvE run that expects the CC Switch relay must inject `driver.model_provider` +
   `driver.model_providers.*`; otherwise the agent silently calls `api.openai.com` and dies
   with 401. This is a *configuration* gap, not a code defect, and it is the reason the
   earlier "codex cannot complete a call" verdict looked like a host outage.
3. **`E*` requires absolute `--state-dir` (and `--out`).** With a relative `--state-dir`,
   every candidate returns `status=error`, `failure.kind=child_terminated_early`,
   `"the isolated runner did not write its done marker"`, exit 3 — reproduced directly:

   ```
   $ a0/tasks/circle-packing/.venv/bin/python .../e_star.py evaluate --candidate .../c01_good_hex \
       --seed 1337 --fidelity full --fraction 1.0 --out /tmp/reltest/c01.json --state-dir relstate
   rc=3   # status=error child_terminated_early
   $ ... --state-dir /tmp/reltest/absstate
   rc=0   # status=ok
   ```

   The adapter now resolves every path before invoking `E*` (`common.run_e_star`). Whoever
   owns `E*` should either accept relative paths or reject them with a clear message; silent
   `status=error` on every candidate is easy to misread as "the runtime cannot evaluate".
4. **The `E*` scalar is bit-stable and reproducible across runtimes**: this adapter measured
   `E_r(c01) = 2.4519205208433132`, byte-identical to `E_STAR.json`, through a completely
   different process chain — and again inside a real EvE iteration (`0.25` for the baseline,
   with the same `canonical_digest` as the reference sweep).
5. **`E_STAR.json`'s `structure.sum_radii` is a trap for adapters**: it is `0` (a genuine
   measured zero-length sum) for candidates where `fields.sum_radii` is `null`. An adapter
   that scalarizes from `structure` reproduces EvE's false green exactly.
6. EvE leaves read-only trees in the run directory; `rm -rf` needs `chmod -R u+w` first.
7. The seed repo `scaling-group/evolve-testbed @ 6ac22c44` is reachable and its HEAD equals
   the pinned commit, so the `(github_url, commit)` path works — the adapter refuses to fall
   back to a local path. `git clone` did fail once transiently (exit 128); the adapter now
   retries the idempotent `RepoTaskProblem` construction 3 times before failing.
8. `/tmp/eve` contains 85 untracked `__pycache__/*.pyc` (81 × 3.12 from A0 tooling, 4 × 3.14
   from the acceptance run). `git status` stays clean because they are ignored; this
   adapter's import pattern writes none (verified). Keep `PYTHONDONTWRITEBYTECODE=1` in front
   of EvE imports.

## Tree hygiene of the pinned snapshot (shared with the other workstreams)

`/tmp/eve` currently contains 85 `__pycache__/*.pyc` files (81 `cpython-312`, 4
`cpython-314`) that are not part of the checkout. `git status --porcelain` in `/tmp/eve` is
**empty** because `__pycache__` is ignored, so the tree still passes a git-level identity
check, but a byte-level comparison against the audit snapshot would now see them. The
`cpython-314` files are from the acceptance workstream (mtime 15:48, system Python 3.14);
the `cpython-312` ones (earliest 17:07) are from A0 tooling importing EvE with
`PYTHONPATH=/tmp/eve/src` and without `PYTHONDONTWRITEBYTECODE` — **not** from this adapter:
verified by running this adapter's exact import pattern with the env var set and observing no
new file (`find /tmp/eve -name '*.pyc' -newer <marker>` → empty). Nothing in `EID*` covers
`/tmp/eve`, so no identity is invalidated; still, concurrent workers should keep
`PYTHONDONTWRITEBYTECODE=1` in front of every EvE import, or the "pinned snapshot" will drift
in files that git does not track.

