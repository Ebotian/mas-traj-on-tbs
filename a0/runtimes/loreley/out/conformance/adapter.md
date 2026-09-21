# Loreley adapter declaration (A0)

* adapter version: 1.0.0
* runtime: loreley, pinned checkout `4c3759208e6b908f90716488ac3eec3dceaaf397`
  (`a0/runtimes/loreley/checkout`)
* interpreter: CPython 3.12.11

## EID* -> EID_r mapping

* `EID*` = `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328` (from `/home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json`; `evalcontract.py verify` run
  before every command unless `--no-verify` is passed).
* native scheme: `evaluator_name_version_campaign_program_hash`, mapping mode `native`.
* `EID_r.value` = `loreley:v1:loreley_a0_plugin:plugin@source-sha256:53e6cfe804d0d1e53414ed1d8694435d085404b88322889ecdcc73280affd9ad#b18efabb4f6a859b71f489ebca799fcbb9339133dcde51f862232bbb60d88fa1`
* recomputable: yes - `a0_adapter eidr` recomputes `value` and `eidr_derivation` from
  the plugin source file, the campaign program file and `EID*`, and reports
  `recomputed: true` with an empty `problems` list.
* `eidr_derivation` = `15c5b4374c5b9c7b6011e0a2f4c26d0bac6e093c86dda9c71d72186f08e994e8`

## F_r

* declaration: `F_r = scalar(E*)` (`1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0`), applies `scalar`.
* realised as one extra metric (`A0_FR_METRIC_NAME`) appended to E*'s own field set;
  E*'s multi-field Outcome is never reduced (hard constraint 3, plan:549).

## FailureStage (adapter_contract.md 5.3)

* adopted table: `201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f` from
  `a0/contract/selection/simpleloop.selection.json`; the adapter's copy is
  `a0/runtimes/loreley/policy/loreley.selection.json` and both blocks' canonical
  digests are recomputed on every run (`a0_adapter.failure_stage.adopt`), refusing
  the run if either has drifted.
* unit basis: one unit per member of `C*`, read from the score trace by
  `(run_id, iteration, candidate_id)` - adapter-level events that are not candidates
  (the run-level resource row, the report-branch selection row) are not units, so the
  counts stay joinable with the other runtimes'.
* `status` + `failure.kind` + the stage derived from them are on every row of the
  conformance document.

## EID_r recomputation

`recompute_cmd` in the conformance document points at `tools/verify_eidr.py`, which
imports **nothing** from this adapter: it recomputes the five component digests and
`EID*` with the contract owner's own scheme, hashes the plugin source and the rendered
program as bytes on disk, and checks that all five component digests appear verbatim
in the hashed program bytes.

## Evaluator wiring

* `WORKER_EVALUATOR_PLUGIN=loreley_a0_plugin:plugin`
* `WORKER_EVALUATOR_PYTHON_PATHS=['/home/ebt/rsi-dev/a0/runtimes/loreley/src']`
* `A0_E_STAR_PY=/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python`
* `A0_E_STAR_SCRIPT=/home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py`
* theta_E: seed=1337 fidelity=full
  fraction=1.0 (defaults applied:
  {})
* objectives: `[{"name": "composite_score", "direction": "max"}]`
* `MAPELITES_EXPERIMENT_ROOT_COMMIT=b91c0906c9f676eb661990d881144909d99f2d72`

## Measurements

measures are the adapter's declared, frozen behavior descriptor for the A0 plumbing round: (clip(sum_radii/3.0), clip(runtime_p50_ms/50.0)) into the [0,1]^2 feature box the archive is built with. Loreley's native descriptor (repository snapshot -> file embeddings -> dimension reduction, map_elites/manager.py) is NOT exercised in A0 and is recorded as such.

## What is not exercised

Loreley's LLM-driven path (planning/coding agents, codex backend) is not exercised:
`codex` cannot complete a model call on this host. The lanes exercised here are the
evaluator spawn, the plugin protocol, the metric/objective resolution, the QD archive
and the report query.
