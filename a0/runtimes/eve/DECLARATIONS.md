# EvE adapter — declarations

The declarations `a0/contract/adapter_contract.md` requires of the EvE adapter *before* a
run. The per-run copy, with the values actually used, is written by the adapter to
`<run_dir>/adapter.md`.

## 1. EID_r → EID* mapping (adapter_contract.md §5.2, plan:517)

| field | value |
| --- | --- |
| `native_scheme` | `none` |
| `mapping_mode` | `adapter_declared_injection` |
| `value` | `'sha256:' + sha256("a0/eve/eid_r/v1" ‖ 0x00 ‖ canonical_json(payload))` |
| `payload` | `{schema, eid_star, native_scheme, mapping_mode, evaluator_source{digest,files}, fr_spec_hash}` |
| `derives_from_eid_star` | the `EID*` in force, copied verbatim |
| `recomputable` | `true` — `tools/recompute-eid-r` recomputes it from published files alone, importing nothing from this adapter |

`EID*` is an **argument of the hash**, not a neighbouring field: change `eid_star` and the value
changes necessarily. The payload also carries `EID*`'s `EvaluatorSource` component — its records
re-hashed from `tasks/circle-packing/{e_star.py,e_star_child.py}`, so a mutated evaluator cannot
be hashed under a stale identity (the adapter aborts with exit 3) — and `fr_spec_hash`, the frozen
`F_r` declaration digest. The payload is deliberately **run-invariant**; the rendered step script
is reported next to `EID_r` (`eid_r.injected_step`) rather than hashed into it, because it embeds
the run's absolute state-dir path and would otherwise make `EID_r` a per-directory value instead
of an evaluator identity.

**R3, fixed 2026-09-20.** An earlier revision set `EID_r.value` to the sha256 of the step script
the adapter itself had generated. It recomputed, but nothing *forced* the value to depend on
`EID*` — a step that ignored `EID*` would have recomputed equally well (`verify/VERDICT.md` R3).
The derivation above replaces it; `tools/eid_r_mutation_check.py` executes the four cases that
make the difference checkable:

```
M1 the published EID* recomputes to the declared value (standalone tool)      PASS
M2 mutating one nibble of eid_star changes EID_r                              PASS
M3 mutating one byte of e_star.py is refused (exit 3), not hashed             PASS
M4 the adapter refuses a mutated EID* document outright (exit 3, verify)      PASS
```

EvE has no native evaluator identity: the evaluator is whatever shell steps
`evaluation.steps` names (`workflow/evaluation.py:759-798`). The adapter therefore *pins*
`EID*` in three ways, each checkable from the run directory alone:

1. it composes the shipped run config (`configs/eve/circle_packing.yaml`) and overrides
   exactly one key, `evaluation.steps`, with the generated step;
2. the generated step invokes the frozen `E*` by absolute path with the frozen `theta_E`
   baked in (no `PATH`, no `cwd` dependence) and consumes exactly the four variables EvE
   injects — `EVE_WORKSPACE_ROOT`, `EVE_SOLVER_ROOT`, `EVE_EVAL_LOG_ROOT`,
   `PYTHONDONTWRITEBYTECODE` (`workflow/evaluation.py:290-318`);
3. every trace event carries `eid_star`, and the score payload written to the eval-log root
   (`$EVE_EVAL_LOG_ROOT/score.yaml`) carries `eid_star` too.

Declared in: `a0_adapter/eidmap.py` (`EID_R_DECLARATION`, `derive_eid_r`),
`a0_adapter/eve_runtime.py` (`eid_r_payload`, `eid_r_enrichment`, `render_step_script`),
template `steps/eve_evaluator_step.sh.tmpl`, recompute tool `tools/recompute-eid-r`.

## 2. Seed repository

`(github_url, commit)` = `(https://github.com/scaling-group/evolve-testbed,
6ac22c440e241b7e19d89fff91cc4f9841cc951d)`, taken from
`configs/eve/application/circle_packing.yaml:5-6`. **A missing half is an error**: the
adapter refuses to run unless both are present (`_application_source`,
`problem/repo.py:44-58`, reached through `RepoTaskProblem.from_config`), so there is no
silent local-path fallback. Reachability checked with `git ls-remote` before the run; the
clone and the `git archive` snapshot both come from the pinned commit.

`editable.files = ["candidate.py"]`, `editable.folders = []`
(`configs/eve/application/circle_packing.yaml:7-10`).

**Declared deviation.** `C*`'s members are `solution.py` directories
(`a0/tasks/circle-packing/C_STAR/manifest.json`), so the candidate overlay the adapter
hands to `SolverEvaluator.evaluate` is `{"solution.py": <candidate source>}`, not
`candidate.py`. The seed snapshot still supplies the rest of the task repo, and the
`solution_sha256` from `C*` is verified before any evaluation. Without this translation
`solution.py` would be absent from the eval workspace and every score would be a
synthesized failure.

## 3. Evaluator wiring (binding decision 2)

The generated step runs exactly:

```
a0/tasks/circle-packing/.venv/bin/python a0/tasks/circle-packing/e_star.py evaluate \
  --candidate "$EVE_SOLVER_ROOT" --seed 1337 --fidelity full --fraction 1.0 \
  --n 26 --runs 5 --timeout-s 120.0 \
  --out "$EVE_EVAL_LOG_ROOT/e_star/outcome.json" --state-dir <run_dir>/e-star-state \
  --emit-resources "$EVE_EVAL_LOG_ROOT/e_star/resources.json"
```

`theta_E.seed` is recorded as `null` with
`defaults_applied.seed = {value: 1337, source: ...}` because EvE injects no seed into an
evaluation step (`workflow/evaluation.py:290-318` names exactly four variables). The seed
is a real `E*` input for `--fidelity fast`; under the frozen `full`/`fraction 1.0` the
audit is exhaustive and the seed is inert (`e_star.py:31-36`).

## 4. F_r

`F_r = scalar(E*)`, declared and frozen in `a0/contract/fr/scalar.json`
(`fr.spec_hash = 1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0`).
The step writes E*'s whole `fields` map into `score.yaml` and sets
`score = fields.sum_radii`; EvE's `scalar()` reads the `score` key
(`populations/score.py:11-33`). `E*` itself is never scalarized by the runtime.

### 4.1 What the A0.1 verdict covers — 5 measured rows, 9 declared synthesised zeros

The formula A0.1 checks is `E_r(c) = E*(c) ± ε`. For EvE it is checked on the **five** candidates
`E*` measured with `status == "ok"`; agreement there is bit-exact. On the other **nine** it does
not hold, and EvE cannot make it hold: EvE's lane returns
`{score: 0.0, summary: "evaluation failed"}` for every non-measurable candidate
(`workflow/evaluation.py:161-165` swallowing the step's exception, into
`evaluation.failure_score` from `configs/eve/evaluation/circle_packing.yaml:8-10`) and has **no
way to express `invalid` or `error` at all**. Those rows are a declaration about what EvE could
not produce, not a comparison of verdicts; the conformance runner labels them
`SYNTHETIC_DECLARED` and the adapter marks them `evaluator_evidence.status = "synthesized_failure"`.

So EvE's A0.1 result is **5/14 measured**, never "14/14 agree" (audit F5). The accounting is
machine-readable in `conformance.json` → `a01.agreement_scope` and top-level `a0_1_scope`, and it
is the study's central false-green trap: a runtime that substituted `0.0` for unmeasurable
candidates *without* declaring it would pass the same arithmetic test.

### 4.2 FailureStage staging — the frozen A0-wide table, adopted and digest-checked

`adapter_contract.md` §4.5/§5.3 make the `failure_stage_mapping` table A0-wide, because it is the
only thing that makes `plan:577`'s per-runtime `FailureStage` counts summable. EvE adopts it:

| where | what |
| --- | --- |
| `a0/contract/selection/simpleloop.selection.json` | the contract's canonical copy (`failure_stage_mapping` digest `201fed78…`, `scalarization` `d59f0930…`) |
| `a0/runtimes/eve/selection/eve.selection.json` | EvE's runtime-side declaration; both shared blocks byte-equal after canonicalization |
| `a0_adapter/selectionmap.py` | re-derives both digests at run time and **refuses the run (exit 3)** if the contract's block, the frozen digest and EvE's copy do not all agree |
| `conformance.json` → `failure_stage_accounting_basis` | the adopted table, both digests, the adoption check, and the staging rule |

The stage is `table(E* status, E* failure.kind)` — `invalid` → `verify_failed`, and for `error`
the kind's entry in the adopted table (`candidate_import_failed` → `resolve_failed`,
`non_deterministic` → `verify_failed`, `runtime_budget_exceeded` → `timeout`,
`candidate_call_raised` / `child_terminated_early` / other → `evaluator_failed`). The same value
is written to the trace event and to the row, so §4.5 checks (b) and (c) cannot drift. Declared
counts over `C*`: `{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}`
— the runner reports `failure_stage_accounting.matches_frozen_map: true`.

**The one declared extension — 0 rows in this run, raised with the contract owner.** A row whose
`E*` verdict is `ok` but whose runtime attempt failed anyway (`mismatch`, or
`runtime_synthesized_failure_for_a_measurable_candidate`) is not describable by a table that maps
`E*` verdicts: E* assigned `none`. Staging it `none` would erase a real runtime failure, so those
rows are staged `evaluator_failed` and counted in `a01.failure_stage_extension` (with
`a01.failure_stage_basis = adapter_extension_runtime_failed_a_measurable_candidate`). **Consequence
for joining counts:** if such a row ever fires, EvE's declared counts will deliberately *not* equal
`expected_from_frozen_map` for that run, because `expected_from_frozen_map` is computed from `E*`'s
verdicts alone. The difference is the finding — reported, never re-mapped away — and the question
for the contract owner is which stage (if any) the table assigns to a runtime failure on a
candidate `E*` measured `ok`. **No row in this run needs the extension.**

## 5. Traces

`<run-dir>/traces/eve.<run_id>.{score,selection,resource}.jsonl` plus the merged
`eve.<run_id>.all.jsonl`, validated with `a0/contract/trace_validate.py`. Both subcommands write
the traces themselves and declare their paths in the conformance document
(`traces: {score, selection, resource, all}`, `traces_source: "written by this … invocation"`),
so `a0/conformance` reads them instead of searching for them. `cmd_conformance` (A0.1 only)
writes an empty selection trace on purpose: A0.1 makes no selection decision, and the
contract asks for an event per *actual* decision, not for a fabricated one.

The three per-kind files **partition** the run: every event is appended to exactly one per-kind
file and, in the same `emit`, to the merged stream (`a0_adapter/traces.py`). A `selection`
event's `source_score_event_id` is resolved against the score events of the **run's stream**
(`trace_validate.py:198-206`, which is why the merged file is required here and why validation
is run-level), so `validate --trace <selection.jsonl>` alone is *not* a valid way to check this
run.

Fixed 2026-09-20: the first version of the writer copied each cited score event into the
selection file to make the old per-file rule pass. Run-level validation showed those 14 copies
were score events in the selection file with duplicate `event_id`s — 14 duplicate-`event_id` plus
14 kind-purity errors once the run was merged, while each file validated clean on its own. The
copies are removed and the run now validates as one stream.

## 5.1 theta_E and the harness

The conformance document declares `theta_e` flat — `seed`, `fidelity`, `fraction`, `n`,
`runs`, `runtime_budget_ms`, `timeout_s`, `defaults_applied`, `extra` — and every row carries
`theta_e_attempt` plus `raw` = the `E_STAR_MANIFEST` line E\* printed inside the runtime's own
evaluation lane. `theta_E.seed = 1337` is what `E*` actually ran at; the honest qualification
is recorded in `theta_e.extra.seed_delivery`: EvE hands an evaluation step no evaluator
parameters at all (`workflow/evaluation.py:290-318`), so the adapter pins the seed. An
invocation that passes `--theta seed=none` instead records `seed: null` plus
`defaults_applied.seed`.

## 5.2 The agent lane's Codex provider

An EvE run with the real agent lane needs `driver.model_provider` and
`driver.model_providers.*` (`tools/run_one_eve_iteration.py --inject-codex-provider`), because
EvE's isolated Codex HOME carries a thin `config.toml` with no provider block
(`providers/agent/codex_isolation.py:42-66`). Without it the agent leaves the local relay and
calls `api.openai.com` with a placeholder key, failing with 401.

## 6. Closure mechanism

Truthful statement of what is and is not closed — see `out/closure.json` for the evidence:

* the shipped full-run driver is `codex_exec` (`configs/eve/driver/codex_max.yaml:6,12`,
  `web_search: live`). `codex_exec` has **no sandbox parameter at all** and its argv always
  carries `--dangerously-bypass-approvals-and-sandbox`
  (`providers/agent/drivers/codex_exec.py:421-447`, flag at `:434`). Closure by
  configuration is therefore impossible on the shipped path; only `web_search` can be
  turned off there.
* `allow_network` **does exist** in EvE, contrary to `ACCEPTANCE.md` T7 ("no `allow_network`
  parameter in EvE at all"): it is a driver-level *sandbox-mode selector*
  (`runtime/driver.py:380-387`: `true` → `danger-full-access`, else `workspace-write`) and a
  `benchmark_safe` policy flag that only hardens the workspace-local Python wrapper
  (`providers/agent/config.py:24-32,86`; `providers/agent/python_runtime.py:20,332`). The
  acceptance work's *conclusion* stands: it cannot close the shipped path.
* the protocol's recipe is realisable only on the `codex_tmux` driver, whose argv carries
  `-s workspace-write` and `-c web_search="disabled"` (`drivers/codex_tmux.py:555-570,584`);
  the guarantee then rests on Codex CLI's `workspace-write` network default, which cannot be
  exercised without a working model backend.
* the evaluator lane (this adapter's step) *is* closed under external isolation
  (`probe_egress.sh check --mechanism unshare-rn`), which is verified by probe and recorded
  in `closure.json`.
* **scope, versus `a0/closure/`.** `out/run001/closure.json` is authoritative for *EvE as
  shipped* (driver selected, argv EvE builds, closable-by-configuration); the per-posture lane
  breakdown is `a0/closure/closure.eve.json` + `VERDICTS.md`, whose executed `rc=0` observations
  are authoritative for the postures and for "the agent lane is reachable". The split is
  recorded in `closure.json` → `scope`; both records agree on `egress_detected`.

Verdict vocabulary from the contract: `closed` → exit 0, `egress_detected` → exit 6,
`inconclusive` → exit 3 (treated as not closed).
