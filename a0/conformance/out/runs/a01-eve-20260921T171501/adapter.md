# EvE adapter run record

* run_id: `a01-eve-20260921T171501`
* run_dir: `/home/ebt/rsi-dev/a0/conformance/out/runs/a01-eve-20260921T171501`
* EvE checkout: `/tmp/eve` @ `979065fd2cf1b3be9caf70596478fe27df7815ad` (pinned)
* EID*: `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`
* EID_r: `sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a` (native_scheme `none`, mapping_mode `adapter_declared_injection`)
* EID_r derivation: `value = 'sha256:' + sha256("a0/eve/eid_r/v1" || 0x00 || canonical_json(payload)); canonical_json = json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) encoded ascii (a0/contract/evalcontract.py::canonical_json)`
  * domain: `a0/eve/eid_r/v1`
  * payload (published, so a third party can recompute without this adapter): `{"eid_star":"664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328","evaluator_source":{"digest":"a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29","files":[{"path":"tasks/circle-packing/e_star.py","sha256":"2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567"},{"path":"tasks/circle-packing/e_star_child.py","sha256":"e189c020ddcd2a598dadb797af0f6b06d5a30b2be4c68e226c775d2217bdf9ca"}]},"fr_spec_hash":"1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0","mapping_mode":"adapter_declared_injection","native_scheme":"none","schema":"a0/eve/eid_r/v1"}`
  * recompute: `/home/ebt/rsi-dev/a0/runtimes/eve/.venv/bin/python /home/ebt/rsi-dev/a0/runtimes/eve/tools/recompute-eid-r --eid /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json --fr /home/ebt/rsi-dev/a0/contract/fr/scalar.json --a0-root /home/ebt/rsi-dev/a0`
  * `eid_star` is an argument of the hash: a different `EID*` necessarily gives a different `EID_r` (`tools/recompute-eid-r --eid <mutated EID document>`).
* injected step (provenance, deliberately NOT hashed into `EID_r`): `/home/ebt/rsi-dev/a0/conformance/out/runs/a01-eve-20260921T171501/evaluator/eve_evaluator_step.sh` sha256 `fc857156a8bf3594460d9381ad20f73b8a28538049f980155b51459ec8eecf44`, from template `/home/ebt/rsi-dev/a0/runtimes/eve/steps/eve_evaluator_step.sh.tmpl` sha256 `eb9bcf8c355bcc925e682a1831c08fe536653eb7c144c8610c210f0bebb3036d`
* template: `/home/ebt/rsi-dev/a0/runtimes/eve/steps/eve_evaluator_step.sh.tmpl`
* theta_E: `{"defaults_applied": {}, "extra": {"n": 26, "runs": 5, "runtime_budget_ms": 250.0, "source": "adapter CLI --theta", "timeout_s": 120.0}, "fidelity": "full", "fraction": 1.0, "seed": 1337}`
* F_r: `{"applies": "scalar", "declared_in": "a0/contract/fr/scalar.json", "name": "F_r = scalar(E*)", "spec_hash": "1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0", "version": "v1"}` (spec_hash = canonical_file_digest of the declaration)
* evalcontract verify: rc=0
* budget_hard: `{"N_evaluatorCalls": 200, "T_wall_sec": 3600.0, "concurrency_cap": 1}`
* wall clock for the whole adapter run: 22.2s

## Declarations (adapter_contract.md §2, §5)

* seed repo: `(github_url, commit)` = `(https://github.com/scaling-group/evolve-testbed, 6ac22c440e241b7e19d89fff91cc4f9841cc951d)`; a missing half is an error (`RepoTaskProblem._application_source`, problem/repo.py:44-58).
* editable: `files=['candidate.py']`, `folders=[]` (`configs/eve/application/circle_packing.yaml:7-10`).
* the candidate overlay is `solution.py` only; the seed snapshot supplies the rest of the task repo. Declared here because it is a deviation from the repo's own `candidate.py` editable list, forced by `C*`'s layout (`C_STAR/manifest.json`).
* reference evaluator: `/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python /home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py evaluate ...` (binding decision 2).
* `E*` is never scalarized by the runtime: the step writes E*'s full `fields` map into `score.yaml` and sets `score = fields.sum_radii`; `F_r = scalar(E*)` is declared in `a0/contract/fr/scalar.json` and hashed into every trace event.

## A0.1

* verdict: **PASS**
* counters: `{"candidates": 14, "match": 5, "mismatch": 0, "reference_non_ok": 9, "reference_ok": 5, "runtime_failed_a_measurable_candidate": 0, "runtime_reported_ok_where_e_star_did_not": 0, "synthesized_failure": 9, "value_mismatch": 0}`
* FailureStage counts over `C*` (joinable across runtimes, adopted frozen table `201fed78b725…`): `{"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}`
* staging basis: `{"cases": ["mismatch", "runtime_synthesized_failure_for_a_measurable_candidate"], "consequence_for_joining_counts": "these rows are the only way this adapter's declared counts can differ from expected_from_frozen_map; when one fires, the difference IS the finding and is raised with the contract owner (DECLARATIONS.md \u00a74.2) rather than re-mapped away", "count": 0, "rows": [], "staged_as": "evaluator_failed"}`
* epsilon: 1e-09
* **scope of that verdict — EvE's A0.1 result is 5 measured row(s) + 9 declared synthesised zero(s), NOT 14 reproduced verdicts. On the 5 measured rows agreement is bit-exact; on the 9 others there is no E_r value to compare, because EvE's lane has no way to report E*'s invalid/error verdict — it substitutes evaluation.failure_score 0.0 (workflow/evaluation.py:161-165). A consumer must read this as 5/14 measured.**
* per-candidate reference/runtime values: see `conformance.json` → `a01.candidates`

## A0.2

* iterations total: 12200
* frozen sampling config: `{"n_solver_examples_phase2": 4, "n_workers_phase2": 2, "rng_seed": null, "rng_seed_note": "populations/base.py:40 -> random.Random() with no seed; no seed key exists in the config tree", "solver_examples._target_": "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax.RankExponentialSumSampler", "solver_examples.features.score.temperature": 1.0, "solver_examples.features.score.weight": 1.0, "solver_examples.replacement_mode": "no_replacement", "solver_prefill._target_": "scaling_evolve.algorithms.eve.populations.samplers.uniform.UniformSampler", "working_optimizer._target_": "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax.RankSoftmaxSampler"}`
* `A02-E1/E5_solver_examples_order_N2`: n=2000 (effective 2000), p̂=0.738000, H0 p=0.7310585786, p-value=0.496, reject=False
* `A02-control_solver_examples_order_N2_injected_swap`: n=2000 (effective 2000), p̂=0.264000, H0 p=0.2689414214, p-value=0.632, reject=False
* `A02-E6_solver_prefill_uniform_control_N2`: n=200 (effective 200), p̂=0.515000, H0 p=0.5000000000, p-value=0.724, reject=False
* `A02-E7_solver_examples_order_N4`: n=2000 (effective 2000), p̂=0.660000, H0 p=0.6439142599, p-value=0.135, reject=False
* `A02-E8_solver_examples_second_draw_not_reranked_N4`: n=6000 (effective 1426), p̂=0.860449, H0 p=0.8437947345, p-value=0.0864, reject=False
* score→selection contrast: `{"conclusion": "the only input changed between the two cases is the externally supplied score payload; the position-0 frequency of the same candidate moved accordingly", "difference": 0.474, "position0_frequency_with_reference_scores": 0.738, "position0_frequency_with_swapped_scores": 0.264, "same_candidate": "c01_good_hex", "two_proportion_z": 29.97845217536054, "two_sided_p": 0.0}`

## False-green trap (plan:551-552)

* detected: True
* candidates with a synthetic score: `["c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import", "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow"]`
* shipped-step reproduction: `{"R1_adapter_step_propagates_e_star_exit": {"candidates": ["c05_overlapping", "c06_empty", "c07_single", "c08_out_of_bounds", "c09_malformed_import", "c10_raises", "c11_non_deterministic", "c12_exit_without_artifacts", "c13_slow"], "see": "a01.candidates[*] where reference_status != 'ok'"}, "R2_shipped_step_evaluator_exits_nonzero": {"candidate_id": "c06_empty", "conclusion": "a failed evaluation yields a numeric 0.0 that EvE accepts as a population score; the numeric value carries no information about the failure. Which auxiliary signal survives depends on the route: the step status/error.txt`

## UNVERIFIED

* the agent lane: `codex` cannot complete a model call on this host, so no full EvE iteration has been run end to end. A0.2 exercises the runtime's *sampling and selection machinery* through the real sampler classes and the real call site; the LLM-driven path stays UNVERIFIED.
* closure: see `closure.json` — the agent lane cannot be probed today.

