# Verification record — Loreley adapter (A0.1 / A0.2 / traps / closure)

Every verdict below is backed by a command that was actually run in this
repository and by the artefact it wrote. Commands are reproducible from
`README.md`. Paths are relative to `a0/runtimes/loreley/` unless absolute.

Environment at the time of the run: Linux, `docker` 29.8.0, uv-managed CPython
3.12.11 for both the Loreley checkout and `E*`, PostgreSQL 18 on
`127.0.0.1:5432`, Redis 8 on `127.0.0.1:6379`, both on `a0-loreley-net` and
`a0-loreley-internal`.

---

## A−1 inputs consumed

```
$ PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter plan
{
 "eid_star": "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328",
 "primary_field": "sum_radii",
 "epsilon": 1e-09,
 "base_declared": "..",
 "verify": "clean"
}
```

`verify: clean` is `a0/contract/evalcontract.py verify --eid-file
a0/contract/out/plumbing.EID.json --base /home/ebt/rsi-dev/a0` reporting that all
five recorded inputs re-hash to their recorded digests. Every adapter command runs
that check first (exit 3 on drift) unless `--no-verify` is passed, which the
records then show.

## `EID_r → EID*`

Reconstructed independently — not by hand this time, but by a tool that shares no
code with the adapter:

```
$ ./checkout/.venv/bin/python tools/verify_eidr.py \
      --eid /home/ebt/rsi-dev/a0/tasks/circle-packing/plumbing.EID.proposed.json \
      --program out/eidr/loreley.program.md \
      --plugin-source src/loreley_a0_plugin.py \
      --mapping out/eidr/eidr.mapping.json
{
  "checks": {"component_digests_match_record": true,
             "eid_star_matches": true,
             "every_component_digest_reaches_the_hashed_program": true},
  "derivation_matches_declared": true,
  "value_matches_declared": true,
  "reconstruction_ok": true,
  "eid_star": "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328",
  "value": "loreley:v1:loreley_a0_plugin:plugin@source-sha256:53e6cfe804d0d1e53414ed1d8694435d085404b88322889ecdcc73280affd9ad#b18efabb4f6a859b71f489ebca799fcbb9339133dcde51f862232bbb60d88fa1"
}
```

`tools/verify_eidr.py` imports **nothing** from `a0_adapter`. What it does, and why
each step is independent:

1. recomputes the five component digests and `EID*` from the recorded inputs alone,
   with the **contract owner's own** `evalcontract.py::recompute_from_records` — the
   authority's scheme, not a scheme of mine;
2. hashes the plugin source file and the rendered `loreley.program.md` **as bytes on
   disk**, without re-rendering either;
3. rebuilds `EID_r.value` from the native scheme's declared string shape and
   recomputes `eidr_derivation`;
4. checks the structural property: **every one of the five component digests appears
   verbatim in the hashed program bytes** (`structural_containment`).

Step 4 is the answer to the auditor's EvE finding. `EID_r` here is not a hash of a
generated script that the inputs do not reach: its two hash inputs are (a) the
plugin source — the code that will actually run — and (b) the rendered program, whose
bytes now carry all five `EID*` component digests in a `## Provenance` section. The
dynamic side of the same claim is measured too, in `./bin/a0-loreley eidr`:

```
$ ./bin/a0-loreley eidr --run-dir out/eidr
  baseline self-check: recomputed five digests == recorded, EID* == 664115e0…
  EvaluatorSource    digest a3d6534b4e -> 977ff97115  EID* cef56070e0  EID_r changed
  DependencyLock     digest 7b02f1a712 -> a25c617b0a  EID* aa8fd67e36  EID_r changed
  DataManifest       digest b21c975a51 -> 6e5eb1b149  EID* 4577a87ddc  EID_r changed
  Config             digest 550ca3cdd8 -> 3c9db3295f  EID* 224e6bacbb  EID_r changed
  MetricDefinition   digest 420ab0acf2 -> efd0e8657c  EID* 545104b8a6  EID_r changed
  all_five_components_change_eid_star: true
  all_five_components_change_eid_r:    true
```

Each component is perturbed in turn, `evalcontract.recompute_from_records` recomputes
its digest and `EID*`, the program is re-rendered from the perturbed document, and
`EID_r` is re-derived. **All five change it**, so the derivation is a function of the
whole of `EID*` rather than of the subset its prose happens to quote.

`recompute_cmd` in the conformance document points at this independent tool, so the
check the external runner executes is the reconstruction rather than the adapter's
own `derive_eidr`:

```
eid_r.recompute_cmd  = [<venv python>, tools/verify_eidr.py, --eid …, --program …,
                        --plugin-source …, --plugin-ref …, --mapping …]
recompute_cmd_is_adapter_independent = true
```

Artefacts: `out/eidr/eidr.mapping.json`, `out/eidr/loreley.program.md`,
`out/eidr/eidr.recompute.json`, `out/eidr.out`. The mapping document carries
`native_components.evaluator_name`, `.plugin_source_sha256` and
`.campaign_program_sha256`, plus `eidr_derivation`
(`15c5b4374c5b9c7b6011e0a2f4c26d0bac6e093c86dda9c71d72186f08e994e8`).

## A0.1 — conformance

### Driven by the external harness (`a0/conformance`)

```
$ cd /home/ebt/rsi-dev/a0/conformance
$ python3 conformance.py run --runtimes loreley --out report.loreley.json
--- loreley ---
    PASS: all checks passed
--- controls (fixture adapters, not runtimes) ---
    control_honest: PASS (expected PASS)
    control_zero_on_error: FAIL (expected FAIL)
    control_cache_hit: FAIL (expected FAIL)
verdicts (A0.1 only): {"loreley": "PASS"}
exit code 0
```

`report.loreley.json` → `runtimes.loreley`: `state: "PASS"`, `reason: null`, all ten
checks `ok`, `false_green_findings: []`, 14 rows, conformance exit 0 in 8.6 s.

| check | result | evidence |
|---|---|---|
| `EID-star-verbatim` | ok | `664115e0…` carried verbatim |
| `EID-r-derives-from-EID-star` | ok | `eid_r.derives_from_eid_star == EID*` |
| `EID-r-declaration-present` | ok | `evaluator_name_version_campaign_program_hash` / `native` / recomputable |
| `EID-r-recomputes` | ok, **`recompute_mode: "executed"`** | the runner ran the emitted `recompute_cmd`, which points at `tools/verify_eidr.py` — an **adapter-independent** reconstruction (it imports nothing from `a0_adapter`) — and its stdout `value` equals the declared `eid_r.value` |
| `theta-E-identical` | ok | seed 1337, fidelity full, fraction 1.0, n 26, runs 5, runtime_budget_ms 250.0, timeout_s 120.0, all typed |
| `E-star-manifest-echo` | ok | **28 echoes across 14 candidates** verify `evaluator_source_sha256`, the per-candidate canonical digest and `theta_E` |
| `F-r-frozen` | ok | `spec_hash 1fa6f941…` equals the pinned first-round `F_r` |
| `candidate-coverage` | ok | 14/14 members of `C*` |
| `E-r-equals-E-star` | ok | 14/14 agree; disagreeing: none |
| `E-r-failure-kind` | ok | **9/9** non-`ok` rows declare `E*`'s `failure.kind`, and the stage derived from it by the frozen table agrees with `E*`'s |
| `evidence-fresh-or-declared` | ok | every compared row is `evaluator_evidence.status == ok` |

### `FailureStage` accounting (§4.5 / §5.3)

```
declared_counts          {none: 5, verify_failed: 5, resolve_failed: 1,
                          evaluator_failed: 2, timeout: 1}
declared_units           14
expected_from_frozen_map {none: 5, verify_failed: 5, resolve_failed: 1,
                          evaluator_failed: 2, timeout: 1}
comparable_to_C*         true
matches_frozen_map       true
note: "the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts"
```

Per candidate, `status` → `failure.kind` → derived `failure_stage`, all read from the
adapter's own document and compared against `E*`:

```
c01..c04, c14  ok                             --            none
c05..c08       invalid  invalid_configuration  verify_failed
c09            error    candidate_import_failed resolve_failed
c10            error    candidate_call_raised   evaluator_failed
c11            error    non_deterministic       verify_failed
c12            error    child_terminated_early  evaluator_failed
c13            error    runtime_budget_exceeded timeout
```

**What changed and why the previous numbers were unjoinable.** Two independent
defects, both fixed:

1. the staging was the adapter's own invention: `candidate_call_raised` and
   `non_deterministic` were folded into `resolve_failed` and
   `runtime_budget_exceeded` into nothing at all, giving `{none:6, resolve_failed:5,
   verify_failed:4}`. The frozen table sends them to `evaluator_failed`,
   `verify_failed` and `timeout` respectively.
2. the unit basis was "every event in every trace": the run-level resource row
   (`candidate_id: "__run__"`) added a 15th unit for 14 candidates. The counts are
   now read from the **score trace** by `(run_id, iteration, candidate_id)` — exactly
   the runner's own rule in `conformance.py::count_failure_stages` — so adapter-level
   events that are not candidates are not units. `failure_stage_counts_basis` in the
   document states this, and `failure_stage_counts_basis.one_unit_per_member` is
   `true`.

The adopted table is `a0/runtimes/loreley/policy/loreley.selection.json`
(`policy_id: loreley-selection-v1`), whose `scalarization` and
`failure_stage_mapping` blocks are byte-identical to both
`a0/contract/selection/simpleloop.selection.json` and
`a0/contract/selection/kapso.selection.json`. `a0_adapter.failure_stage.adopt()`
recomputes both canonical digests on every run and refuses the run if either has
drifted; the result is recorded as `failure_stage_mapping_adoption` in every
conformance document:

```
failure_stage_mapping_digest          201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f
failure_stage_mapping_digest_expected 201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f
scalarization_digest                  d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c
verified                              true
```

The `run` command declares the same counts from its own score trace
(`out/run-a0/run.summary.json` → `failure_stage_counts`, `.units = 14`, `.match = true`).

Per-row verdicts, including the verdict-only candidates:

```
c01_good_hex              MATCH          E*=2.4519205208433132  E_r=2.4519205208433132
c02_baseline_upstream     MATCH          E*=0.25                E_r=0.25
c03_mirror                MATCH          E*=2.4519205208433132  E_r=2.4519205208433132
c04_near_tie              MATCH          E*=2.451820520843313  E_r=2.451820520843313
c05_overlapping           MATCH_VERDICT  E*=null                E_r=null
c06_empty                 MATCH_VERDICT  E*=null                E_r=null
c07_single                MATCH_VERDICT  E*=null                E_r=null
c08_out_of_bounds         MATCH_VERDICT  E*=null                E_r=null
c09_malformed_import      MATCH_VERDICT  E*=null                E_r=null
c10_raises                MATCH_VERDICT  E*=null                E_r=null
c11_non_deterministic     MATCH_VERDICT  E*=null                E_r=null
c12_exit_without_artifacts MATCH_VERDICT E*=null                E_r=null
c13_slow                  MATCH_VERDICT  E*=null                E_r=null
c14_near_zero             MATCH          E*=2.6e-05             E_r=2.6e-05
```

The `conformance` run writes the three traces itself (non-empty, all valid —
`valid: 14 / 15 / 15 event(s)` plus `valid: 44` for the combined stream) and names
them in its document, so the A0.1 number and the A0.1 evidence come from one
execution.

### Driven directly

```
$ ./bin/a0-loreley conformance --runtime loreley \
      --run-dir out/conformance-run --out out/conformance.json
{
 "verdict": "pass",
 "failure_count": 0,
 "failed_candidates": [],
 "epsilon": 1e-09,
 "candidates": 14,
 "out": "out/conformance.json"
}
```

`out/conformance.json`, per candidate (`E*` = reference run outside the runtime,
`E_r` = the metric the runtime's evaluator process actually returned):

| candidate | E\* status | E* `sum_radii` | E_r outcome | E_r `sum_radii` | verdict |
|---|---|---|---|---|---|
| c01_good_hex | ok | 2.4519205208433132 | passed | 2.4519205208433132 | pass |
| c02_baseline_upstream | ok | 0.25 | passed | 0.25 | pass |
| c03_mirror | ok | 2.4519205208433132 | passed | 2.4519205208433132 | pass |
| c04_near_tie | ok | 2.451820520843313 | passed | 2.451820520843313 | pass |
| c05_overlapping | invalid | null | candidate_failed | (absent) | pass |
| c06_empty | invalid | null | candidate_failed | (absent) | pass |
| c07_single | invalid | null | candidate_failed | (absent) | pass |
| c08_out_of_bounds | invalid | null | candidate_failed | (absent) | pass |
| c09_malformed_import | error | null | candidate_failed | (absent) | pass |
| c10_raises | error | null | candidate_failed | (absent) | pass |
| c11_non_deterministic | error | null | candidate_failed | (absent) | pass |
| c12_exit_without_artifacts | error | null | candidate_failed | (absent) | pass |
| c13_slow | error | null | candidate_failed | (absent) | pass |
| c14_near_zero | ok | 2.6e-05 | passed | 2.6e-05 | pass |

Supporting assertions in the same document:

* `repeats`: 3 fresh evaluations of `c01_good_hex` on each side; `spread = 0.0`,
  `stdev = 0.0`, `epsilon_covers_observed_spread: true`. `E*` is deterministic, so
  the frozen `1e-9` over-covers the observed spread (acceptance A01.3).
* `hard_constraint_1_cwd_independence`: `E*` re-run with `cwd=/` and `PATH=""`;
  `third_path_primary == in_run_reference_primary` and
  `third_path_canonical_digest == in_run_canonical_digest`
  (`1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8`).
* `hard_constraint_3_multi_field`: the runtime's metric vector keeps all six
  declared `E*` fields (`sum_radii`, `packing_density`, `num_circles`,
  `overlap_count`, `min_gap`, `min_boundary_margin`) and the declared `F_r` adds
  exactly one projection metric (`composite_score = 2.4519205208433132`).
  Non-scoring candidates produce **no** metric at all rather than a `0.0`.

## A0.2 — archive replacement, negative control, report branch

```
$ PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter a02 --runtime loreley \
      --run-dir out/a02-run --out out/a02.json
{
 "verdict": "pass", "failed_checks": [],
 "meaningful_control_config": "config-m-multi-objective",
 "checks": [A02-L1 pass, A02-L3 pass, A02-L5 pass, A02-L8 pass,
            A02-L3-M pass, A02-L7 pass, A02-L5-M pass]
}
```

**Positive, same cell (A02-L1).** Identical `measures = (0.25, 0.25)` →
`cell_index = 68` for both; scores are the *real* evaluated values
(`c01_good_hex` 2.4519205208433132, `c02_baseline_upstream` 0.25, gap
2.2019205208433132 > epsilon 1e-9). Added one at a time:

```
add c02_baseline_upstream -> retained=true,  removed_commit_hashes=[]
add c01_good_hex         -> retained=true,  removed_commit_hashes=["c02_baseline_upstream"]
front(cell 68) = ["c01_good_hex"]        archive members = ["c01_good_hex"]
```

**Negative control, cross cell (A02-L3, A02-L3-M).** With `c1` strictly higher on
the primary objective but `measures = (0.75, 0.25)` (cell 196):

```
config-s: add c1 -> retained=true, removed=[]; front(cell 68) = ["c02_baseline_upstream"]
config-m: c1 objective (3.0, 9.0) vs c2 (2.0, 1.0) -> retained=true, removed=[],
          front(cell 68) = ["c2"], members = ["c2", "c1"]
```

**Which configuration makes this control meaningful (A02-L8).** The same
same-cell pair, evaluated under both contracts:

```
single objective (composite_score max): front = ["c1"]           # per-cell argmax: c2 evicted
two objectives   (sum_radii max + runtime_p50_ms min): front = ["c1", "c2"]   # non-dominated
```

Under one objective the archive *is* the per-cell argmax and the report is the
global argmax over retained members, so the protocol's "no global-argmax
guarantee" is false there and a "higher score must not evict" test cannot
discriminate. Under two objectives (`examples/evol_circle_packing.py:80-84`) a
strictly worse primary can be retained alongside a better one, which is the
behaviour the negative control is supposed to detect. So the run is in the
**single-objective regime** and the cross-cell control is reported as meaningful in
the **multi-objective** configuration.

**Report branch (A02-L5, A02-L5-M).** Rows written to PostgreSQL, then the
runtime's own query run:

```
EvolutionScheduler._resolve_best_primary_commit() -> "c01_good_hex"
  meta: {island_id: circle_packing_alpha, primary_metric_name: composite_score,
         primary_metric_value: 2.4519205208433132, root_commit_hash: null}
three members, two cells, one at value 9.0 -> "c_high"
```

The method body, the ORM models, the SQL and the session factory are the pinned
checkout's. The one seam is object construction: `EvolutionScheduler.__init__`
demands a writable git repository, so the instance is allocated with `__new__` and
the two attributes the method reads (`settings`, `_root_commit_hash`) are set
directly - `scheduler/main.py:876-931` is executed unmodified.

**Sampling (A02-L7).** 4000 draws from a two-cell archive holding values 1.0 and
99.0, fixed `random.Random(20260920)`: per-cell frequency `0.5 / 0.5`. The pick
does not depend on score.

## False-green traps

```
$ PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter traps --runtime loreley \
      --run-dir out/traps-run --out out/traps.json --t2-timeout 1
{"verdict": "pass", "T2": true, "T3": true, "T4": true}
```

* **T2 timeout.** `WORKER_EVALUATOR_TIMEOUT_SECONDS=1` against `c13_slow`:
  `Evaluator._execute_with_timeout` raises on the deadline
  (`evaluator.py:1859-1912`) and `evaluate_outcome` synthesizes an outcome
  (`:1513-1520`). Observed: `outcome_kind=infrastructure_failed`,
  `E_r metrics = 0`, `failure_summary = "Evaluation plugin timed out after 1s."`,
  plugin evidence file absent. Adapter label:
  `{"status": "timeout", "detail": "the runtime synthesized a candidate failure on
  timeout: Evaluation plugin timed out after 1s."}` with the score event recording
  `outcome.fields = {"sum_radii": null}`. A real score carries `status: "ok"` and a
  number; there is no `0.0` anywhere, so the two cannot be confused.
* **T3 truncation.** Two payload shapes, one real runtime branch:

  | plugin payload | emitted | returned | truncation applied |
  |---|---|---|---|
  | `EvalPass` (the A0 plugin's shape) | 77 | **77** | no |
  | `Mapping` (`examples/circle_packing_env/evaluate.py`'s shape) | 77 | **64** | yes |

  The `Mapping` run prints the runtime's own warning
  `loreley.core.worker.evaluator:_coerce_result:2305 - Truncating evaluator metrics
  from 77 to 64` and the adapter labels it `truncated_metrics` with
  `metrics_dropped = 13`. The `EvalPass` run shows a real gap in the runtime:
  `_coerce_outcome` returns `payload.to_result()` verbatim
  (`evaluator.py:2029-2037`) and never reaches the cap. The adapter therefore never
  infers truncation from a count - it compares the plugin's reported emission with
  what the runtime returned - and the frozen `E*` emits 6 fields (7 with `F_r`),
  far below the cap of 64, so no A0 result is affected either way.
* **T4 persistent cache.** Against the real PostgreSQL-backed
  `EvolutionJobStore.find_reusable_evaluation` (`job_store.py:519-600`), with a
  stored passed evaluation for the same source-tree hash and evaluator contract:

  ```
  reuse with matching evaluator identity : True   (metrics: composite_score 2.4519205208433132)
  reuse with a different evaluator_version: False  (the cache key includes the identity)
  adapter label when reused               : {"status": "cache_hit",
                                             "cached_from_run_id": "ad37641d-..."}
  ```

  So the reuse really happens, the cache key really does include the evaluator
  identity, and a reused observation is never counted as fresh.

## Traces

`out/run-a0/traces/` — produced by

```
$ PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter run --runtime loreley \
    --run-id lor-a0 --run-dir out/run-a0 \
    --candidate-set /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json \
    --budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1 --traces score,selection,resource
```

```
trace_validate.py validate --trace loreley.lor-a0.score.jsonl      -> valid: 14 event(s)
trace_validate.py validate --trace loreley.lor-a0.selection.jsonl  -> valid: 15 event(s)
trace_validate.py validate --trace loreley.lor-a0.resource.jsonl   -> valid: 15 event(s)
trace_validate.py validate --trace loreley.lor-a0.all.jsonl        -> valid: 44 event(s)
```

`<run_dir>/run.summary.json` records `failure_stage_counts`
(`resolve_failed 5`, `other_failures 4`, all four named counters otherwise 0), the
full `failure_stage_histogram` (`none 6`, `verify_failed 4`, `resolve_failed 5`),
`evaluator_evidence_counts` (`ok 14`), the archive admissions, the report-branch
result and the external-score control.

### The subtlety the validator forces

`trace_validate.py:169-192` resolves `selection.source_score_event_id` only
against score events **in the same file**. A per-kind selection file contains
none, so a non-null reference there is always invalid. The writer therefore emits:

* the three mandated per-kind files, with `source_score_event_id: null` and the
  join available through `(iteration, candidate_id)` - the keys
  `trace_schema.md` §2 prescribes; and
* a combined `loreley.lor-a0.all.jsonl` that keeps the real reference
  (`lor-lor-a0-s-i0-c01_good_hex`), so "the decision was driven by the score" is
  machine-checkable. All four files validate.

## Externally supplied score changed the selection

`run.summary.json → externally_supplied_score_changed_the_selection`:

```
design: two candidates in one cell, differing only in the primary score,
        supplied first as 'external_high' and then as 'external_low'
run_a: survivor ["external_high"], removed ["external_low"]
run_b: survivor ["external_low"],  removed ["external_high"]
score_decides: true
```

The same property on real `C*` members is A02-L1 above: swapping which of
`c01`/`c02` carries the higher value swaps which one survives the cell.

## Closure

```
$ PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter closure-probe --runtime loreley \
      --run-dir out/closure-run --out out/closure.json
verdict = "closed"
```

| observation | expectation | observed | canary line |
|---|---|---|---|
| `probe_egress:host` | open | OPEN | `dns=ok tcp=ok tcpvia=example.com:443 https=ok` |
| `probe_egress:docker-bridge` | open | OPEN | `dns=ok tcp=ok tcpvia=example.com:443 https=ok` |
| `probe_egress:docker-internal` | blocked | BLOCKED | `dns=fail tcp=fail https=fail local=ok` |
| `candidate_channel:bridge` (real lane) | open | OPEN | candidate-side probe: dns/https/tcp all `ok` |
| `candidate_channel:internal` (real lane) | blocked | BLOCKED | `dns_example_com: fail:gaierror`, `tcp_1_1_1_1_53: fail:OSError:[Errno 101] Network is unreachable`, `https_example_com: fail:URLError` |

`mechanism: external_network_isolation`. The protocol says Loreley's default path
has no network switch (`plan:569`), and the checkout confirms it - there is no
allow-network / web-search setting to flip - so isolation, not configuration, is
what closes it. `local=ok` on the internal run (the canary still reaches
`a0-loreley-postgres:5432` and `a0-loreley-redis:6379`) shows the barrier is
selective rather than broken networking.

### The network flip, measured

`infra/net.sh close` takes the services off `a0-loreley-net` and leaves them only
on `a0-loreley-internal`:

```
container a0-loreley-postgres  Up 34 minutes  5432/tcp          # host publishing gone
networks[a0-loreley-postgres] a0-loreley-internal
127.0.0.1:5432 NOT reachable from host: ConnectionRefusedError
127.0.0.1:6379 NOT reachable from host: ConnectionRefusedError
docker exec a0-loreley-postgres pg_isready -U loreley -d loreley
  -> /var/run/postgresql:5432 - accepting connections        # still alive inside
```

`infra/net.sh open` restores `a0-loreley-net` and `127.0.0.1:5432`,
`127.0.0.1:6379` become reachable again. In both states
`adapdc-catalog-postgres-1` on 5433 is untouched.

Recorded caveats, from `out/closure.json`:

* `docker --internal` also removes the container's route to the host, so the
  barrier cuts **host loopback** as well as external egress. The orchestrator
  process therefore cannot sit behind it, and was not placed behind it.
* The probed lane is the evaluator/candidate lane. Loreley's LLM-driven lane
  (planning/coding agents) could not be run at all - see below.

## BLOCKED / UNVERIFIED

| item | status | why |
|---|---|---|
| **Planning lane (real codex, inside Loreley's worker)** | **verified on real runtime code** | one bounded round (`llm-round/RESULT.md`): the worker checked out `b91c0906…`, called `codex_planning_backend()` and produced a plan in **144.1 s**. Requires `WORKER_PLANNING_EXTRA_ENV={"CODEX_HOME":"~/.codex"}` — the backend's home isolation otherwise discards `[model_providers.custom]` and returns 401 (`codex_cli.py:243-270`). |
| **Coding lane** | **reached, did not complete** | `codex exec timed out after 480s` on the first coding attempt; the round's watchdog stopped it at 13 m 28 s with the job still `RUNNING`. 0 `evaluation_attempts`, 0 `candidate_commits`, 0 archive rows, so `E*` was never invoked inside a worker round. Missing quantity is wall clock, not capability (the checkout's own coding budget is 1800 s). |
| A full round to a committed candidate + archived elite | **UNVERIFIED** | follows from the coding timeout above |
| The native behaviour descriptor (repository snapshot → file embeddings → PCA → `measures`) | **UNVERIFIED in the A0 run; wired in the bounded round** | The A0 arm (out/a0.json, out/run-a0) freezes the descriptor condition and declares its measure function — the adapter's own descriptor, *not* the native pipeline. The bounded LLM round does run the native local-hash descriptor (`MAPELITES_CODE_EMBEDDING_MODEL=local-hash-v1`, `MAPELITES_DIMENSIONALITY_TARGET_DIMS=2`) but never reached ingestion, so no archive cell was written. |
| The phased measurement cache end to end (`evolution.py:1640-1665`, `:1741-1766`) | **partially verified** | The reuse **decision** is the runtime's own (`EvolutionJobStore.find_reusable_evaluation` against real PostgreSQL), and the adapter labels a reused outcome `cache_hit`. The worker run above used the one-shot path, so the phased cache through the worker remains UNVERIFIED. |
| `MAPELITES_ADMISSION_POLICY=fresh_comparison` | not exercised | out of scope for A0.2; the frozen condition is `pareto` |
| Candidate set `C*` | integrity-verified | every command recomputes each `solution.py` sha256 against `manifest.json` (exit 4 on mismatch); `--no-integrity` exists only for debugging |

The LLM round's raw evidence: `llm-round/bounded_round.log`, `llm-round/logs/worker.log`,
`llm-round/RESULT.md`, the `loreley_llm` database on the same Postgres container.

## The bounded codex round

```
$ timeout 1200 ./llm-round/run_bounded_round.sh
18:24:45  Checked out base commit b91c0906c9f676eb661990d881144909d99f2d72
18:27:09  Planning agent generated plan in 144.1s (attempt 1/2)
18:35:09  Coding attempt 1 failed: codex exec timed out after 480s.
18:37:48  round watchdog: worker stopped (t+782s of a 1200s cap)
final: evolution_jobs 1 row status=RUNNING; evaluation_attempts 0; archive cells 0
```

Full detail, including the `CODEX_HOME` finding that gates the lane, is in
`llm-round/RESULT.md`.

## What changed in this revision

1. **Adopted the frozen `failure_stage_mapping`** (`201fed78…`) in
   `policy/loreley.selection.json`, with the digest recomputed on every run. The
   staging now follows the table for all five `E*` verdict shapes.
2. **Fixed the unit basis**: `failure_stage_counts` is now one unit per `C*` member
   read from the score trace, not every event in every trace. Previously the
   run-level resource row (`candidate_id: "__run__"`) made 15 units for 14
   candidates, which is why the runner could not compare. The basis is declared in
   the document (`failure_stage_counts_basis`) with
   `one_unit_per_member: true`.
3. **Rows now carry `failure_stage`** alongside `status` and `failure.kind`, and all
   three agree with `E*` on all 14 candidates.
4. **`EID_r` is now reconstructed by an independent tool** (`tools/verify_eidr.py`)
   that shares no code with the adapter, and that tool is what `recompute_cmd`
   points at; the campaign program gained a `## Provenance` section carrying all five
   component digests, so the derivation is a function of the whole of `EID*`,
   demonstrated by a five-way mutation test.
5. Infrastructure unchanged and still running (`./infra/net.sh status`).

## What other workstreams need to know

1. **`E*` is deterministic** on this host: three repeats of `c01_good_hex` gave an
   identical `sum_radii` and an identical canonical digest, so `epsilon = 1e-9`
   is not the binding constraint — but a runtime that folds `E*`'s fields through
   a *timing* metric (as the circle-packing example does with `runtime_p50_ms`)
   introduces nondeterminism that A0.1 must not be judged on.
2. **A runtime metric vector that is not `E*`'s fields must be declared.** The
   adapter adds exactly one `F_r` metric (`composite_score`) and, for the
   multi-objective arm only, one timing metric sourced from `E*`'s
   `--emit-resources` sidecar — which is explicitly *not* part of the canonical
   Outcome.
3. **Loreley's `EvalPass` payload bypasses `worker_evaluator_max_metrics`.** Any
   adapter that returns `EvalPass` can hand the runtime more than 64 metrics.
   A study that compares metric vectors across runtimes must state which payload
   shape each adapter uses.
4. **`ObjectiveContract.resolve` rejects a metric mapping without an explicit
   `higher_is_better`** (`objectives.py:238`); a plugin that emits bare
   name/value pairs fails at the objective gate, not at the archive.
5. **A0.2's cross-cell control is only discriminating under ≥2 objectives.** The
   single-objective regime is per-cell argmax; a conclusion drawn from the
   negative control must name the configuration it was run in.
