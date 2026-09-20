# a0/runtimes/loreley — Loreley evaluator adapter + A0.2 archive check

Owner of this directory: the Loreley workstream of A0. Nothing here writes outside
`a0/runtimes/loreley/`. The pinned snapshots (`a0/tasks/circle-packing/upstream/**`),
the contract (`a0/contract/**`) and the other runtimes' directories are read only.

## Layout

| path | what it is |
| --- | --- |
| `adapter.json` | the declared entry point the conformance runner discovers (`cmd`, `pythonpath`, interpreter) |
| `bin/a0-loreley` | absolute entry point: pins `checkout/.venv/bin/python`, resolves its own paths, works from any cwd |
| `checkout/` | mutable copy of the pinned Loreley checkout `4c3759208e6b908f90716488ac3eec3dceaaf397`, plus a 3.12 venv with `pip install -e .` |
| `src/loreley_a0_plugin.py` | **the adapter plugin**: `WORKER_EVALUATOR_PLUGIN=loreley_a0_plugin:plugin`, takes an `EvaluationContext`, returns `EvalPass` / `EvalFail`, runs the frozen `E*` |
| `src/loreley_a0_plugin_metrics_heavy.py`, `src/loreley_a0_plugin_metrics_mapping.py` | declared T3 test doubles only |
| `src/a0_adapter/` | the adapter: CLI, contracts, `EID_r` derivation, evidence classifier, traces, A0.1, A0.2, closure probe, traps |
| `policy/loreley.selection.json` | the runtime-side selection declaration: the frozen `scalarization` and `failure_stage_mapping` blocks copied verbatim, plus Loreley's own QD-archive selection block |
| `tools/verify_eidr.py` | the independent `EID_r` reconstruction (imports nothing from `a0_adapter`) |
| `infra/net.sh` | Postgres 18 on 5432 + Redis 8 on 6379, on a bridge network and an `--internal` one |
| `probe/egress_candidate/` | the candidate-source egress canary (never part of `C*`) |
| `llm-round/` | the codex-lane question: the bounded probes and their results |
| `out/` | every produced artefact, with the real command output next to it |
| `scratch/` | throwaway smoke script |

## Being driven by the external conformance harness

`a0/conformance/conformance.py` discovers `adapter.json` and runs
`bin/a0-loreley`. That matters: the harness launches with whatever interpreter it
finds, and the adapter executes the pinned checkout's own code, which needs that
checkout's dependencies. Two independent fixes are in place, either of which is
sufficient:

* `adapter.json` names `bin/a0-loreley`, which pins `checkout/.venv/bin/python`;
* `a0_adapter.cli.main` re-execs into that interpreter when `loreley` is not
  importable (guarded by `A0_LORELEY_REEXECUTED=1`), so even
  `/usr/bin/python3 -m a0_adapter` works.

```bash
cd a0/conformance
python3 conformance.py run --runtimes loreley --out report.loreley.json
# --- loreley ---
#     PASS: all checks passed
# verdicts (A0.1 only): {"loreley": "PASS"}
```

Eleven of eleven checks pass, 14/14 candidates (5 `MATCH` with numbers, 9
`MATCH_VERDICT` for the verdict-only members), no `false_green_findings`, and
`EID-r-recomputes` runs **executed** rather than `declared_prose`: the runner
executes the `recompute_cmd` this adapter emits and compares its stdout `value`
with the declared `eid_r.value`. `E-star-manifest-echo` verifies 28 of `E*`'s own
manifest lines across the 14 candidates, and `E-r-failure-kind` records that all
nine non-`ok` rows declare `E*`'s `failure.kind` and the stage the frozen table
derives from it.

## FailureStage accounting (§5.3)

The study joins every runtime's `FailureStage` totals on one table, so the adapter
adopts the frozen `failure_stage_mapping` rather than choosing one:

```bash
./bin/a0-loreley conformance --runtime loreley --run-dir out/conformance-run --out out/conformance.json
# failure_stage_counts                  {none: 5, verify_failed: 5, resolve_failed: 1,
#                                        evaluator_failed: 2, timeout: 1}
# failure_stage_expected_from_frozen_map  (identical)
# failure_stage_counts_match_frozen_map   true
# failure_stage_counts_basis.units        14   (one per member of C*)
```

* the table lives in `policy/loreley.selection.json`, copied verbatim; both shared
  blocks' canonical digests (`201fed78…` for the mapping, `d59f0930…` for the
  scalarization) are recomputed on every run by `a0_adapter.failure_stage.adopt`,
  and a run whose blocks have drifted is refused;
* the **unit basis is one unit per `C*` member**, read from the score trace by
  `(run_id, iteration, candidate_id)`. Adapter-level events that are not candidates
  — the run-level resource row and the report-branch selection row — are excluded;
  including them is what previously produced 15 units for 14 candidates and left
  the runner unable to compare;
* every conformance row carries `status`, `failure.kind` and the derived
  `failure_stage`, and each agrees with `E*`.

The `conformance` subcommand also writes the three traces under
`<run_dir>/conformance/traces/` and names them in the document, so the A0.1
number and the A0.1 evidence come from one execution.

## `EID_r → EID*`, at the auditor's standard

The auditor reconstructed EvE's identity independently and found it was a hash of a
*generated script* rather than structurally derived from `EID*`. The Loreley answer
is a tool, not a sentence:

```bash
./checkout/.venv/bin/python tools/verify_eidr.py \
  --eid /home/ebt/rsi-dev/a0/tasks/circle-packing/plumbing.EID.proposed.json \
  --program out/eidr/loreley.program.md \
  --plugin-source src/loreley_a0_plugin.py \
  --mapping out/eidr/eidr.mapping.json
# {"checks": {"component_digests_match_record": true, "eid_star_matches": true,
#             "every_component_digest_reaches_the_hashed_program": true},
#  "derivation_matches_declared": true, "reconstruction_ok": true,
#  "value_matches_declared": true}
```

`tools/verify_eidr.py` imports **nothing** from `a0_adapter`. It uses the contract
owner's own `evalcontract.py` to recompute the five component digests and `EID*`
from the recorded inputs alone, hashes the plugin source and the rendered campaign
program **as bytes on disk**, rebuilds `EID_r.value` from the native scheme's
declared string shape, recomputes `eidr_derivation`, and checks the structural
property that matters: **every one of the five component digests appears verbatim in
the hashed program bytes**. That is what makes `EID_r` a function of all five `EID*`
inputs instead of only of the ones the program's prose mentions.

`recompute_cmd` in the conformance document points at this tool, so the check the
external runner executes is the independent reconstruction, not the adapter's own
`derive_eidr`. A second, dynamic check is in `./bin/a0-loreley eidr`: each of the
five components is perturbed in turn, `evalcontract.recompute_from_records`
recomputes `EID*`, the program is re-rendered and `EID_r` re-derived — all five must
change (see `mutation_test.components` in `out/eidr.out`).

## Reproduce

```bash
cd a0/runtimes/loreley
./infra/net.sh up                     # postgres:5432, redis:6379, internal network

./bin/a0-loreley plan                                                       # frozen contract + verify
./bin/a0-loreley eidr                                                       # EID_r derivation + recompute
./bin/a0-loreley conformance  --runtime loreley                             # A0.1 (+ traces)
./bin/a0-loreley a02          --runtime loreley                             # A0.2
./bin/a0-loreley traps        --runtime loreley                             # T2 / T3 / T4
./bin/a0-loreley run          --runtime loreley --run-id lor-a0 \
     --run-dir out/run-a0 --budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1
./bin/a0-loreley closure-probe --runtime loreley                            # closure verdict
```

(`PYTHONPATH=src ./checkout/.venv/bin/python -m a0_adapter …` is equivalent; the
entry point only exists so a harness does not have to know that.)

The `infra/net.sh close | open` flip was measured: closing removes host
publishing for 5432/6379 (`ConnectionRefusedError` from the host) while the
services stay reachable inside `a0-loreley-internal`
(`docker exec a0-loreley-postgres pg_isready` → accepting connections); opening
restores both. The unrelated `adapdc-catalog-postgres-1` on 5433 is untouched.

**Left running on purpose** (reproducible, and needed by the SQL-dependent checks):

| what | where | teardown |
| --- | --- | --- |
| Postgres 18 | container `a0-loreley-postgres`, `127.0.0.1:5432`, databases `loreley` (A0 evidence) and `loreley_llm` (the bounded round) | `./infra/net.sh down --networks` |
| Redis 8 | container `a0-loreley-redis`, `127.0.0.1:6379`, DBs `0` and `1` | same |
| networks | `a0-loreley-net` (bridge) and `a0-loreley-internal` (`--internal`, the closure mechanism) | same |

`./infra/net.sh status` prints all of it. `adapdc-catalog-postgres-1` on 5433 is
never touched.

## Results (all produced by the commands above; numbers are from the artefacts)

* A0.1 — `out/conformance.json`: **pass**, 14/14 candidates of `C*`, epsilon `1e-9`
  (read from `EID*`, not chosen), observed spread `0.0` over 3 repeats, cwd/PATH
  independence verified with an identical canonical digest.
* A0.2 — `out/a02.json`: **pass**, 7/7 checks. Same-cell replacement on real
  evaluated values (2.4519205208433132 vs 0.25) with `removed_commit_hashes ==
  ("c02_baseline_upstream",)`, cross-cell non-eviction, report branch resolved
  through the real PostgreSQL query, and the regime control that shows which
  configuration makes the cross-cell control meaningful.
* Traps — `out/traps.json`: **pass**, T2/T3/T4 each demonstrated on the runtime's
  own code. One finding: the metric cap is not enforced on the `EvalPass` payload
  path (see `out/traps.json` `T3.finding`).
* Closure — `out/closure.json`: verdict `closed`, `mechanism:
  external_network_isolation` (Loreley's default path has no network switch), with
  both positive controls OPEN, both negative controls BLOCKED, `local=ok` proving
  the barrier is selective, and the recorded caveat that `docker --internal` also
  cuts host loopback.
* Traces — `out/run-a0/traces/loreley.lor-a0.{score,selection,resource}.jsonl`,
  validated by `a0/contract/trace_validate.py` → `valid: 14 / 15 / 15 event(s)`,
  plus a combined `…all.jsonl` (44 events) that carries resolvable
  `source_score_event_id` references. The `conformance` run writes the same three
  traces (validated the same way) and names them in its document.
* External conformance harness — `a0/conformance`: **`loreley: PASS`**, 11/11
  checks, `EID-r-recomputes` **executed** (not declared), 28 `E*` manifest echoes
  verified, 14/14 candidates (5 `MATCH` with numbers, 9 `MATCH_VERDICT`), and
  `failure_stage_accounting.matches_frozen_map: true` over **14 units**.
* `FailureStage` — the frozen `failure_stage_mapping`
  (`201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f`) is adopted
  in `policy/loreley.selection.json`, its digest is recomputed on every run, and the
  counts are one unit per `C*` member:
  `{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}`.
* `EID_r` reconstruction — `tools/verify_eidr.py` rebuilds `EID_r` from the `EID*`
  document, the plugin source bytes and the rendered program bytes without importing
  the adapter; it is what `recompute_cmd` points at, and it is the command the
  conformance runner executes.
* Codex lane — `llm-round/RESULT.md`: one bounded real round. The planning lane
  completed a real codex call (144.1 s); the coding lane timed out at 480 s and the
  round was stopped by its own watchdog at 13 m 28 s with the job still `RUNNING`.
* Every subcommand in one run: `out/FINAL_SWEEP.txt`, each step `EXIT=0`.

`VERIFICATION.md` has the evidence behind each verdict, including the rows of
`out/*.json` that back them, and the list of what is BLOCKED or UNVERIFIED.

## C* integrity

Every command re-checks each candidate's `solution.py` sha256 against
`C_STAR/manifest.json` before evaluating, and aborts with exit 4 on a mismatch.
`--no-integrity` exists for debugging and is recorded in the output.

## Exit codes

`adapter_contract.md` §3.1: 0 ok, 2 usage, 3 contract/EID drift, 4 C* integrity,
5 A0.1 conformance failure, 6 closure violation, 7 budget exhausted, 8 no
evaluable candidate, 10 internal error. This package serves `--runtime loreley`
only and exits 2 for the others rather than pretending to serve them.
