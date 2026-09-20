# adapter.md — SimpleLoop, run simpleloop-a02

Written by the adapter into --run-dir (adapter_contract.md §5.2).

## Evaluator identity

* `EID*` = `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328` (from `a0/tasks/circle-packing/plumbing.EID.proposed.json`)
* `verify` (spec `a0/tasks/circle-packing/plumbing.contract.proposed.json`): exit 0 — clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
* `recompute`: exit 0 —   [ok ] EID*               recorded=664115e0d63ad2e1 recomputed=664115e0d63ad2e1
* E* script: `a0/tasks/circle-packing/e_star.py` (sha256 recomputed and compared with the EID* records: True)
* E* interpreter: `/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python` (3.12.11)
* E* self-reported evaluator_source_sha256: `5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532`

## `EID_r -> EID*` mapping

* `native_scheme` = `none`, `mapping_mode` = `adapter_declared_injection`.
* declaration: SimpleLoop has no native evaluator identity (adapter_contract.md §5.2: native_scheme=none). The adapter pins EID* and is the sole source of the identity. EID_r.value is sha256("a0/simpleloop/eid_r/v1" + 0x00 + canonical_json(payload)) with payload = {schema, eid_star, evaluator_source_records, policy_digest} — the same domain-separated construction a0/contract/evalcontract.py uses for its own components. A third party recomputes it from EID*.json, a0/tasks/circle-packing/{e_star.py,e_star_child.py} and a0/runtimes/simpleloop/policy/simpleloop.policy.json alone, without running this adapter: a0/runtimes/simpleloop/tools/recompute-eid-r prints the payload and the digest, and the adapter publishes the same (domain, payload_canonical) pair in its conformance document. It changes iff EID*, the evaluator bytes, or the frozen selection/scalarization policy changes.
* `EID_r.value` = `sha256:5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e`
* recompute it with: `python -m a0_adapter eidr --eid plumbing.EID.proposed.json --eid-spec plumbing.contract.proposed.json`

## Frozen policy

* policy file: `a0/runtimes/simpleloop/policy/simpleloop.policy.json`
* canonical policy digest: `0ceb5f6c1d8afe8730e945fa1469484afc74f304be4bef708a6794a9d10dfebf`
* frozen `F_r` declaration `a0/contract/fr/scalar.json` canonical digest: `1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0`
* selection: `argmax_{i<=t} E(c_i)`, tie-break `smallest candidate_id by byte-wise comparison of the UTF-8 encoding of candidate_id`
* selection comparison is exact binary64; the A0.1 epsilon (1e-09) is not used in selection

## Run

* solver lane: `injected`
* theta_E: `{"seed": 1337, "fidelity": "full", "fraction": 1.0}`
* theta_E.extra: `{"candidate_set_sha256": "8d9b953877beb1b09a240302ec4e3ab51590107e715f86a63963cff9255572f2", "e_star_script_sha256": "2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567", "evaluator_lane": "subprocess: e_star.py evaluate (frozen CLI)", "inject_scores_sha256": "b5757ead0c9b9d9e58b04bc183193f0ef07d4e08105115441c44f74537920d7d", "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "solver_lane": "injected", "timeout_s": 120.0}`
* budget: `{"N_evaluatorCalls": 200, "T_wall_sec": 3600.0, "concurrency_cap": 1}`
* iterations: 6; evaluator calls: 6
* champion: `c02_baseline_upstream` scalar `99.0`
* stopped because: solver_exhausted
* failure_stage counts: `{"resolve_failed": 1, "verify_failed": 1}`
* adapter exit code: 0 — run completed within budget; all three traces written

## Traces
* combined: `a0/verify/out/runs/a02-injected/traces/simpleloop.a02-injected.all.jsonl`
* resource: `a0/verify/out/runs/a02-injected/traces/simpleloop.a02-injected.resource.jsonl`
* score: `a0/verify/out/runs/a02-injected/traces/simpleloop.a02-injected.score.jsonl`
* selection: `a0/verify/out/runs/a02-injected/traces/simpleloop.a02-injected.selection.jsonl`
