# A0.1 cross-adapter conformance report

Generated 2026-09-20T19:52:26+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own verdict is recorded but never trusted.

## Verdicts

| runtime | A0.1 | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|
| simpleloop | PASS | 14/14 | - | not judged here | all checks passed |
| kapso | PASS | 14/14 | - | not judged here | all checks passed |
| eve | PASS | 14/14 (9 SYNTHETIC_DECLARED) | TRAP-SYNTHETIC-DECLARED | not judged here | all checks passed |
| loreley | PASS | 14/14 | - | not judged here | all checks passed |

A0.1-only set: `R_1(A0.1) = ['simpleloop', 'kapso', 'eve', 'loreley']` (n_pass=4, n_fail=0, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

## Reference table reproducibility

Fresh sweep of `E*` over `C*` with the frozen invocation reproduces `E_STAR.json` exactly: **True**; `C*` unchanged by the sweep: **True**.

| candidate | role | E*(c) status | E*(c) value | failure kind | exit |
|---|---|---|---|---|---|
| c01_good_hex | good | ok | 2.4519205208433132 | - | 0 |
| c02_baseline_upstream | baseline | ok | 0.25 | - | 0 |
| c03_mirror | tie | ok | 2.4519205208433132 | - | 0 |
| c04_near_tie | tie | ok | 2.451820520843313 | - | 0 |
| c05_overlapping | bad | invalid | null | invalid_configuration | 2 |
| c06_empty | bad | invalid | null | invalid_configuration | 2 |
| c07_single | bad | invalid | null | invalid_configuration | 2 |
| c08_out_of_bounds | bad | invalid | null | invalid_configuration | 2 |
| c09_malformed_import | bad | error | null | candidate_import_failed | 3 |
| c10_raises | bad | error | null | candidate_call_raised | 3 |
| c11_non_deterministic | bad | error | null | non_deterministic | 3 |
| c12_exit_without_artifacts | bad | error | null | child_terminated_early | 3 |
| c13_slow | bad | error | null | runtime_budget_exceeded | 3 |
| c14_near_zero | bad | ok | 2.6e-05 | - | 0 |

## Per-runtime detail

Row verdicts: `MATCH` (number agrees within epsilon), `MATCH_VERDICT` (no number on either side, verdicts compared), `SYNTHETIC_DECLARED` (the runtime's lane returned a declared synthetic failure where E* has no number -- acceptable, but its 0.0 is never a measurement), `FALSE_GREEN_*` (a number where none exists, or a non-fresh number), `MISMATCH_*`, `MISSING`.

### simpleloop — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes simpleloop --out report.simpleloop.json`

Adapter output: schema `a0.simpleloop.conformance/v1`, rows from `top level`, adapter's own verdict `pass` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/simpleloop/eid_r/v1 digest = 5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e; declared value = '5773dfe1e86728df2ee07be92b2166858eda94cfe7c02e3e737a9a091c8ed42e'
- `PASS` theta-E-identical: adapter declares theta_E = {"extra": {"candidate_set_sha256": "8d9b953877beb1b09a240302ec4e3ab51590107e715f86a63963cff9255572f2", "check_point": "A0.1 conformance: E_r(c) vs E*(c) for every c in C* (plan:513)", "e_star_script_sha256": "2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567", "evaluator_lane": "subprocess: e_star.py evaluate (frozen CLI)", "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}, "fidelity": "full", "fraction": 1.0, "seed": 1337}
- `PASS` E-star-manifest-echo: 28 E* manifest echo(es) across 14 candidate(s) verify the frozen evaluator source digest, the per-candidate canonical digest and theta_E
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: none
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: {"resource": "a0/runtimes/simpleloop/out/default-run/traces/simpleloop.default-run.resource.jsonl", "score": "a0/runtimes/simpleloop/out/default-run/traces/simpleloop.default-run.score.jsonl"} (reported by the adapter)
- FailureStage counts: {"counts": {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}, "note": "declared by the adapter from its own score trace, one unit per (run_id, iteration, candidate_id) so a failure reported on two traces is counted once (plan:577, plan:628); identical to trace_validate.py's rule", "source": "a0/runtimes/simpleloop/out/default-run/traces/simpleloop.default-run.score.jsonl"}
- adapter revision covered by this verdict: digest `c0b2fa1fb329ab179d1d97f6a36ebede56f00552194d441edb79a4b0c799dfe8` over 21 source file(s), newest mtime 2026-09-20T18:58:58+0800, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5} (comparable=True, matches_frozen_map=True); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts

### kapso — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes kapso --out report.kapso.json`

Adapter output: schema `a0.kapso.conformance/v1`, rows from `top level`, adapter's own verdict `pass` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='manifest_fingerprint' mapping_mode='native' recomputable=True
- `PASS` EID-r-recomputes: native scheme 'manifest_fingerprint': the declared EID_r 'manifest:1c6cdec3d71c01124249e00a8723c6b4ea7442ed479edcfc249b937d7125e962' matches the evaluator identity recorded on all 14 rows (1 distinct value(s), e.g. ['1c6cdec3d71c01124249e00a8723c6b4ea7442ed479edcfc249b937d7125e962']); the runner did NOT recompute the fingerprint itself (no recompute_cmd), it cross-checked it against the attempt records
- `PASS` theta-E-identical: adapter declares theta_E = {"defaults_applied": {}, "extra": {"e_star_evaluator_source_sha256": "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532", "e_star_version": "1.0.0", "fidelity_mode": "off", "granted_class": {"eval_fidelity": "full", "eval_fraction": 1.0, "profile": "full"}, "max_change_requests": 0, "parent_policy": "best", "registered_command": "python kapso_evaluation/kapso_eval.py --fidelity full --fraction 1.0 --seed 1337", "registered_subsample_seed": 1337, "registered_wrapper_sha256": "781f54ee7674164d2b71e78d42640f985f3907a76542b8d5a84a3b5220d9e5ba"}, "fidelity": "full", "fraction": 1.0, "seed": 1337}
- `PASS` E-star-manifest-echo: 14 E* manifest echo(es) across 14 candidate(s) verify the frozen evaluator source digest, the per-candidate canonical digest and theta_E
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: none
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: {"all": "/home/ebt/rsi-dev/a0/conformance/out/adapters/traces/kapso.kapso-a01-adapters.all.jsonl", "resource": "/home/ebt/rsi-dev/a0/conformance/out/adapters/traces/kapso.kapso-a01-adapters.resource.jsonl", "score": "/home/ebt/rsi-dev/a0/conformance/out/adapters/traces/kapso.kapso-a01-adapters.score.jsonl"} (reported by the adapter)
- FailureStage counts: {"counts": {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}, "counts_score_trace_only": {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}, "note": "declared by the adapter from its own emitted events, one unit per (iteration, candidate_id, stage) so a failure reported on both the score and the resource event of a unit is counted once (plan:577, plan:628, trace_validate.py count_failure_stages). `counts` is over the run's merged stream (the validation unit); `counts_score_trace_only` is the same rule over the score trace alone, which is what a0/conformance/conformance.py counts when an adapter declares nothing. The mapping is the A0-wide table in contract/selection/kapso.selection.json", "source": "/home/ebt/rsi-dev/a0/conformance/out/adapters/traces/kapso.kapso-a01-adapters.score.jsonl"}
- adapter revision covered by this verdict: digest `ef69ae5c3f712ea1fe765c1819479fba149787e405734d8a849674a7ccaffbf6` over 18 source file(s), newest mtime 2026-09-20T19:23:35+0800, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5} (comparable=True, matches_frozen_map=True); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts

### eve — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes eve --out report.eve.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `PASS` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: ran ['/home/ebt/rsi-dev/a0/runtimes/eve/.venv/bin/python', '/home/ebt/rsi-dev/a0/runtimes/eve/tools/recompute-eid-r', '--eid', '/home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json', '--fr', '/home/ebt/rsi-dev/a0/contract/fr/scalar.json', '--a0-root', '/home/ebt/rsi-dev/a0']: exit 0, recomputed='sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a', declared value='sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a'
- `PASS` theta-E-identical: adapter declares theta_E = {"defaults_applied": {}, "extra": {"seed_delivery": "adapter-pinned: EvE injects no seed into an evaluation step", "source": "adapter CLI --theta"}, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: 56 E* manifest echo(es) across 14 candidate(s) verify the frozen evaluator source digest, the per-candidate canonical digest and theta_E
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: none
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: 9 row(s) carry a declared synthesised failure (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow); no row hides a non-fresh number

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | invalid | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'invalid\')') |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | invalid | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'invalid\')') |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | invalid | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'invalid\')') |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | invalid | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'invalid\')') |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'error\')') |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'error\')') |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'error\')') |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'error\')') |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: 'EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate\'s `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status=\'failed\\n\', eval-log-root error.txt present=True, e_star_status=\'error\')') |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `TRAP-SYNTHETIC-DECLARED` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (declared, non-fatal): the EvE failure_score(0.0) trap was hit and declared, not hidden: EvE returned evaluation.failure_score verbatim {"score": 0.0, "summary": "evaluation failed"} because a step exception was swallowed by SolverEvaluator.evaluate's `except Exception` (workflow/evaluation.py:161-165); E* did not measure this candidate (side channel: step_status='failed\n', eval-log-ro (protocol plan:551)

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: {"all": "/home/ebt/rsi-dev/a0/runtimes/eve/out/conf-a0-eve-run001/traces/eve.a0-eve-run001.all.jsonl", "resource": "/home/ebt/rsi-dev/a0/runtimes/eve/out/conf-a0-eve-run001/traces/eve.a0-eve-run001.resource.jsonl", "score": "/home/ebt/rsi-dev/a0/runtimes/eve/out/conf-a0-eve-run001/traces/eve.a0-eve-run001.score.jsonl", "selection": "/home/ebt/rsi-dev/a0/runtimes/eve/out/conf-a0-eve-run001/traces/eve.a0-eve-run001.selection.jsonl"} (reported by the adapter)
- FailureStage counts: {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}
- adapter revision covered by this verdict: digest `41d49211756c1c0dc71fd98ff975fce77cb486126264f8c9c6e8e5da25fcef0f` over 17 source file(s), newest mtime 2026-09-20T19:46:04+0800, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5} (comparable=True, matches_frozen_map=True); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts
- declared synthetic failures (never a measurement): c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- adapter's own UNVERIFIED note: the agent lane is not exercised by this subcommand: A0.1 needs only the evaluator lane, which runs here through EvE's own evaluate() path. The LLM-driven end-to-end EvE round is a separate experiment (see out/run002/ if present).
- seams the adapter declares: E1: SolverEvaluator.evaluate path (real EvE evaluation machinery) (src/scaling_evolve/algorithms/eve/workflow/evaluation.py:119-165); E2: the shell step subprocess with the runtime-injected environment (src/scaling_evolve/algorithms/eve/workflow/evaluation.py:277-347)

### loreley — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes loreley --out report.loreley.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `pass` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='evaluator_name_version_campaign_program_hash' mapping_mode='native' recomputable=True
- `PASS` EID-r-recomputes: ran ['/home/ebt/rsi-dev/a0/runtimes/loreley/checkout/.venv/bin/python', '/home/ebt/rsi-dev/a0/runtimes/loreley/tools/verify_eidr.py', '--eid', '/home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json', '--program', '/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/loreley.program.md', '--plugin-source', '/home/ebt/rsi-dev/a0/runtimes/loreley/src/loreley_a0_plugin.py', '--plugin-ref', 'loreley_a0_plugin:plugin', '--mapping', '/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/eidr.mapping.json']: exit 0, recomputed='loreley:v1:loreley_a0_plugin:plugin@source-sha256:53e6cfe804d0d1e53414ed1d8694435d085404b88322889ecdcc73280affd9ad#b18efabb4f6a859b71f489ebca799fcbb9339133dcde51f862232bbb60d88fa1', declared value='loreley:v1:loreley_a0_plugin:plugin@source-sha256:53e6cfe804d0d1e53414ed1d8694435d085404b88322889ecdcc73280affd9ad#b18efabb4f6a859b71f489ebca799fcbb9339133dcde51f862232bbb60d88fa1'
- `PASS` theta-E-identical: adapter declares theta_E = {"defaults_applied": {}, "extra": {"n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: 28 E* manifest echo(es) across 14 candidate(s) verify the frozen evaluator source digest, the per-candidate canonical digest and theta_E
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: none
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: {"combined": "/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/traces/loreley.lor-a0.all.jsonl", "resource": "/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/traces/loreley.lor-a0.resource.jsonl", "score": "/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/traces/loreley.lor-a0.score.jsonl", "selection": "/home/ebt/rsi-dev/a0/runtimes/loreley/out/conformance/traces/loreley.lor-a0.selection.jsonl"} (reported by the adapter)
- FailureStage counts: {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5}
- adapter revision covered by this verdict: digest `b3ef599150a927ef319747f9bcc6d0fb0a3a5134ccee66e4c7f1319cb1f7b25f` over 22 source file(s), newest mtime 2026-09-20T19:39:26+0800, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared {"evaluator_failed": 2, "none": 5, "resolve_failed": 1, "timeout": 1, "verify_failed": 5} (comparable=True, matches_frozen_map=True); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the declared counts equal the frozen §5.3 mapping applied to C*'s E* verdicts
- adapter's own UNVERIFIED note: ["Loreley's LLM-driven path (planning / coding / evolution worker) was not run: the host has no usable model backend at the time of the A0 run (`codex` could not complete a model call; `claude`'s login state was unknown). No candidate generation, job scheduling or worker-driven archive ingestion happened.", "The native behaviour descriptor (repository snapshot -> file embeddings -> PCA -> measures) was not run: it needs an embedding provider. A0 freezes the descriptor condition ('two candidates with equal measures'); the adapter declares its measure function instead (see run.summary.json -> measure_source).", "The phased measurement cache end to end (evolution.py:1640-1665, :1741-1766) is only partially verified: the reuse DECISION is the runtime's own (EvolutionJobStore.find_reusable_evaluation against real PostgreSQL) and the adapter labels a reused outcome cache_hit, but the worker that consumes that decision was not run.", 'MAPELITES_ADMISSION_POLICY=fresh_comparison was not exercised; the frozen policy is pareto.']
- seams the adapter declares: EvolutionScheduler.__new__ + settings/_root_commit_hash: None (None); plugin payload shape (EvalPass rather than a Mapping): None (None); adapter-declared behaviour descriptor: None (None)

## Controls

| control | state | rows | reason |
|---|---|---|---|
| control_honest | PASS | 14 |  |
| control_zero_on_error | FAIL | 14 | false-green finding(s): FG-EVE-SYNTH |
| control_cache_hit | FAIL | 14 | false-green finding(s): FG-LORELEY-CACHE |

## EID* checks

Handed to every adapter: `/home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json` (label `canonical`, requested `canonical`, sha256 `50af0aeb42dbc5a7...`).

- `PASS` EID-inputs-match-binding: EID_INPUTS.json eid_star == binding 664115e0... : True
- `PASS` EID-document-found: an EID*.json with eid_star == 664115e0... was found
- `PASS` EID-document-as-requested: the document handed to the adapters is the one requested (`--eid-document canonical` -> /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json)
- `PASS` EID-recompute: evalcontract.py recompute is filesystem-free and recomputed EID* matching 664115e0d63ad2e1 (exit 0)
- `PASS` EID-verify-inputs: evalcontract.py verify re-hashed the declared inputs of plumbing.EID.json against /home/ebt/rsi-dev/a0/contract/plumbing.contract.json [the supplied document's own `spec` field (plumbing.EID.json)] (exit 0)
- `PASS` EID-documents-agree: 2 document(s) carry EID* = 664115e0...: ['/home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json', '/home/ebt/rsi-dev/a0/tasks/circle-packing/plumbing.EID.proposed.json']; the runner hands /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json to the adapters (sha256 50af0aeb42dbc5a7217de99ffe619f336d6bb9e9e483e1a50dc3be518d03075b)

## Candidate-set integrity

14 candidates checked against `manifest.json`; integrity ok = **True**.

