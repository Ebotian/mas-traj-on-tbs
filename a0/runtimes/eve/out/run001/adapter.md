# EvE adapter run record

* run_id: `eve-a0-run001`
* run_dir: `/home/ebt/rsi-dev/a0/runtimes/eve/out/run001`
* EvE checkout: `/tmp/eve` @ `979065fd2cf1b3be9caf70596478fe27df7815ad` (pinned)
* EID*: `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`
* EID_r: `sha256:0b738a2c16e6c4b97072dff3469ec12a4ca8504fd3fd5aa125f01966d9b0e20b` (native_scheme `none`, mapping_mode `adapter_declared_injection`)
* EID_r derivation: EvE has no native evaluator identity. The adapter pins EID* by (a) declaring the seed repository as the (github_url, commit) pair of application.circle_packing, (b) replacing the evaluation plan's single step with the adapter-generated shell step that invokes the frozen E* by absolute path, and (c) writing EID* into the score payload the step emits and into every trace event. EID_r.value is the sha256 of the generated evaluation step, so it is recomputable from the run directory alone.
* generated evaluation step: `/home/ebt/rsi-dev/a0/runtimes/eve/out/run001/evaluator/eve_evaluator_step.sh` sha256 `0b738a2c16e6c4b97072dff3469ec12a4ca8504fd3fd5aa125f01966d9b0e20b`
* template: `/home/ebt/rsi-dev/a0/runtimes/eve/steps/eve_evaluator_step.sh.tmpl`
* theta_E: `{"defaults_applied": {"seed": {"source": "EvE passes no seed to the evaluation step; the fixed equivalent used is the frozen E* theta_E.seed=1337, which full-fidelity evaluation does not consume (e_star.py: '--fidelity full audits every item, so the seed is inert there')", "value": 1337}}, "extra": {"n": 26, "runs": 5, "source": "adapter CLI --theta"}, "fidelity": "full", "fraction": 1.0, "seed": null}`
* F_r: `{"applies": "scalar", "declared_in": "a0/contract/fr/scalar.json", "name": "F_r = scalar(E*)", "spec_hash": "1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0", "version": "v1"}` (spec_hash = canonical_file_digest of the declaration)
* evalcontract verify: rc=0
* budget_hard: `{"N_evaluatorCalls": 512, "T_wall_sec": 7200.0, "concurrency_cap": 1}`
* wall clock for the whole adapter run: 70.1s

## Declarations (adapter_contract.md §2, §5)

* seed repo: `(github_url, commit)` = `(https://github.com/scaling-group/evolve-testbed, 6ac22c440e241b7e19d89fff91cc4f9841cc951d)`; a missing half is an error (`RepoTaskProblem._application_source`, problem/repo.py:44-58).
* editable: `files=['candidate.py']`, `folders=[]` (`configs/eve/application/circle_packing.yaml:7-10`).
* the candidate overlay is `solution.py` only; the seed snapshot supplies the rest of the task repo. Declared here because it is a deviation from the repo's own `candidate.py` editable list, forced by `C*`'s layout (`C_STAR/manifest.json`).
* reference evaluator: `/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python /home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py evaluate ...` (binding decision 2).
* `E*` is never scalarized by the runtime: the step writes E*'s full `fields` map into `score.yaml` and sets `score = fields.sum_radii`; `F_r = scalar(E*)` is declared in `a0/contract/fr/scalar.json` and hashed into every trace event.

## A0.1

* verdict: **PASS**
* counters: `{"candidates": 14, "evaluator_failed": 0, "match": 5, "mismatch": 0, "reference_non_ok": 9, "reference_ok": 5, "resolve_failed": 0, "synthesized_failure": 9}`
* epsilon: 1e-09
* per-candidate reference/runtime values: see `conformance.json` → `a01.candidates`

## A0.2

* iterations total: 12200
* frozen sampling config: `{"n_solver_examples_phase2": 4, "n_workers_phase2": 2, "rng_seed": null, "rng_seed_note": "populations/base.py:40 -> random.Random() with no seed; no seed key exists in the config tree", "solver_examples._target_": "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax.RankExponentialSumSampler", "solver_examples.features.score.temperature": 1.0, "solver_examples.features.score.weight": 1.0, "solver_examples.replacement_mode": "no_replacement", "solver_prefill._target_": "scaling_evolve.algorithms.eve.populations.samplers.uniform.UniformSampler", "working_optimizer._target_": "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax.RankSoftmaxSampler"}`
* `A02-E1/E5_solver_examples_order_N2`: n=2000 (effective 2000), p̂=0.754000, H0 p=0.7310585786, p-value=0.0204, reject=True
* `A02-control_solver_examples_order_N2_injected_swap`: n=2000 (effective 2000), p̂=0.263000, H0 p=0.2689414214, p-value=0.562, reject=False
* `A02-E6_solver_prefill_uniform_control_N2`: n=200 (effective 200), p̂=0.495000, H0 p=0.5000000000, p-value=0.944, reject=False
* `A02-E7_solver_examples_order_N4`: n=2000 (effective 2000), p̂=0.647000, H0 p=0.6439142599, p-value=0.779, reject=False
* `A02-E8_solver_examples_second_draw_not_reranked_N4`: n=6000 (effective 1420), p̂=0.853521, H0 p=0.8437947345, p-value=0.324, reject=False
* score→selection contrast: `{"conclusion": "the only input changed between the two cases is the externally supplied score payload; the position-0 frequency of the same candidate moved accordingly", "difference": 0.491, "position0_frequency_with_reference_scores": 0.754, "position0_frequency_with_swapped_scores": 0.263, "same_candidate": "c01_good_hex", "two_proportion_z": 31.05805483607413, "two_sided_p": 0.0}`

## False-green trap (plan:551-552)

* detected: True
* candidates with a synthetic score: `["c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import", "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow"]`
* shipped-step reproduction: `{"R1_adapter_step_propagates_e_star_exit": {"candidates": ["c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import", "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow"], "see": "a01.candidates[*] where reference_status != 'ok'"}, "R2_shipped_step_evaluator_exits_nonzero": {"candidate_id": "c06_empty", "conclusion": "a failed evaluation yields a numeric 0.0 that EvE accepts as a population score; the numeric value carries no information about the failure. Which auxiliary signal survives depends on the route: the step status/error.txt`

## UNVERIFIED

* the agent lane: `codex` cannot complete a model call on this host, so no full EvE iteration has been run end to end. A0.2 exercises the runtime's *sampling and selection machinery* through the real sampler classes and the real call site; the LLM-driven path stays UNVERIFIED.
* closure: see `closure.json` — the agent lane cannot be probed today.

