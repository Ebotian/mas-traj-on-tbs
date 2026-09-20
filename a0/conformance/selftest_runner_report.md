# A0.1 cross-adapter conformance report

Generated 2026-09-20T19:52:00+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own verdict is recorded but never trusted.

## Verdicts

| runtime | A0.1 | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|
| selftest_honest | PASS | 14/14 | - | not judged here | all checks passed |
| selftest_clean | PASS | 14/14 | - | not judged here | all checks passed |
| selftest_zero_on_error | FAIL | 5/14 (9 FALSE_GREEN_SYNTHETIC_ZERO) | FG-EVE-SYNTH | not judged here | false-green finding(s): FG-EVE-SYNTH |
| selftest_cache_hit | FAIL | 0/14 (14 FALSE_GREEN_CACHE_REUSE) | FG-LORELEY-CACHE | not judged here | false-green finding(s): FG-LORELEY-CACHE |
| selftest_timeout | FAIL | 0/14 (14 FALSE_GREEN_TIMEOUT_SYNTHESIS) | FG-LORELEY-TIMEOUT | not judged here | false-green finding(s): FG-LORELEY-TIMEOUT |
| selftest_truncated | FAIL | 0/14 (14 FALSE_GREEN_TRUNCATED_METRICS) | FG-LORELEY-CAP, FG-LORELEY-TRUNCATED | not judged here | false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED |
| selftest_drift_1e_6 | FAIL | 9/14 (5 MISMATCH_VALUE) | - | not judged here | E_r(c) disagrees with E*(c) |
| selftest_drift_1e_10 | PASS | 14/14 | - | not judged here | all checks passed |
| selftest_swap_near_tie | FAIL | 13/14 (1 MISMATCH_VALUE) | - | not judged here | E_r(c) disagrees with E*(c) |
| selftest_digest_swap | FAIL | 13/14 (1 MISMATCH_DIGEST) | - | not judged here | E_r(c) disagrees with E*(c) |
| selftest_partial | FAIL | 5/14 (9 MISSING) | FG-FAILURE-KIND-UNDECLARED | not judged here | false-green finding(s): FG-FAILURE-KIND-UNDECLARED |
| selftest_manifest_triple | FAIL | 0/14 (14 FALSE_GREEN_MANIFEST_TRIPLE) | FG-MANIFEST-TRIPLE | not judged here | false-green finding(s): FG-MANIFEST-TRIPLE |
| selftest_attempt_theta_drift | FAIL | 0/14 (14 FALSE_GREEN_MANIFEST_TRIPLE) | FG-ATTEMPT-THETA-DRIFT | not judged here | false-green finding(s): FG-ATTEMPT-THETA-DRIFT |
| selftest_stale_eid | FAIL | 14/14 | - | not judged here | adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star |
| selftest_native_theta | FAIL | 14/14 | - | not judged here | adapter check(s) failed: theta-E-identical |
| selftest_synthetic_declared | PASS | 14/14 (9 SYNTHETIC_DECLARED) | TRAP-SYNTHETIC-DECLARED | not judged here | all checks passed |
| selftest_synthetic_mislabeled | FAIL | 5/14 (9 FALSE_GREEN_SYNTHETIC_ZERO) | FG-EVE-SYNTH | not judged here | false-green finding(s): FG-EVE-SYNTH |
| selftest_wrong_failure_kind | FAIL | 5/14 (9 MISMATCH_FAILURE_KIND) | FG-FAILURE-KIND | not judged here | false-green finding(s): FG-FAILURE-KIND |
| selftest_wrong_failure_stage | FAIL | 5/14 (9 MISMATCH_FAILURE_STAGE) | FG-FAILURE-STAGE | not judged here | false-green finding(s): FG-FAILURE-STAGE |
| selftest_omit_failure_kind | FAIL | 5/14 (9 UNDECLARED_FAILURE_KIND) | FG-FAILURE-KIND-UNDECLARED | not judged here | false-green finding(s): FG-FAILURE-KIND-UNDECLARED |

A0.1-only set: `R_1(A0.1) = ['selftest_honest', 'selftest_clean', 'selftest_drift_1e_10', 'selftest_synthetic_declared']` (n_pass=4, n_fail=16, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

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

### selftest_honest — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_honest --out report.selftest_honest.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/reference_adapter/v1/EID_r digest = ec55edeefc784e0f0da5d74f245a3be22d929e6f4d9b8535dcb4030de166df41; declared value = 'ec55edeefc784e0f0da5d74f245a3be22d929e6f4d9b8535dcb4030de166df41'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
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
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_clean — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_clean --out report.selftest_clean.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/pass/v1/EID_r digest = 93685028199afb59ac51320ce75b7ca1ea5815d097277ed8e4d0e3cb42089e38; declared value = '93685028199afb59ac51320ce75b7ca1ea5815d097277ed8e4d0e3cb42089e38'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
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
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_zero_on_error — FAIL

Reason: false-green finding(s): FG-EVE-SYNTH

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_zero_on_error --out report.selftest_zero_on_error.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/zero_on_error/v1/EID_r digest = e432ec4367fe207e33989ccba167bee9e377417b0e7d18d5ba1fb2f56fb83d48; declared value = 'e432ec4367fe207e33989ccba167bee9e377417b0e7d18d5ba1fb2f56fb83d48'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c05_overlapping:FALSE_GREEN_SYNTHETIC_ZERO, c06_empty:FALSE_GREEN_SYNTHETIC_ZERO, c07_single:FALSE_GREEN_SYNTHETIC_ZERO, c08_out_of_bounds:FALSE_GREEN_SYNTHETIC_ZERO, c09_malformed_import:FALSE_GREEN_SYNTHETIC_ZERO, c10_raises:FALSE_GREEN_SYNTHETIC_ZERO, c11_non_deterministic:FALSE_GREEN_SYNTHETIC_ZERO, c12_exit_without_artifacts:FALSE_GREEN_SYNTHETIC_ZERO, c13_slow:FALSE_GREEN_SYNTHETIC_ZERO
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 9 row(s) report a non-fresh number without declaring it as such: c05_overlapping=synthesized_failure, c06_empty=synthesized_failure, c07_single=synthesized_failure, c08_out_of_bounds=synthesized_failure, c09_malformed_import=synthesized_failure, c10_raises=synthesized_failure, c11_non_deterministic=synthesized_failure, c12_exit_without_artifacts=synthesized_failure, c13_slow=synthesized_failure

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | ok | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-EVE-SYNTH` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): evaluator_evidence.status=synthesized_failure ('evaluation exception mapped to failure_score(0.0) -- the EvE trap'): the number 0.0 is the runtime's failure_score fallback, not a measurement of E* (E*(c)=None); audit:1016, workflow/evaluation.py:161-167 (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-EVE-SYNTH)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_cache_hit — FAIL

Reason: false-green finding(s): FG-LORELEY-CACHE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_cache_hit --out report.selftest_cache_hit.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/cache_hit/v1/EID_r digest = e84dd4e9202e80ed35d5d7965083992bc340fe13cc6396151e05acf95b6f62da; declared value = 'e84dd4e9202e80ed35d5d7965083992bc340fe13cc6396151e05acf95b6f62da'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:FALSE_GREEN_CACHE_REUSE, c02_baseline_upstream:FALSE_GREEN_CACHE_REUSE, c03_mirror:FALSE_GREEN_CACHE_REUSE, c04_near_tie:FALSE_GREEN_CACHE_REUSE, c05_overlapping:FALSE_GREEN_CACHE_REUSE, c06_empty:FALSE_GREEN_CACHE_REUSE, c07_single:FALSE_GREEN_CACHE_REUSE, c08_out_of_bounds:FALSE_GREEN_CACHE_REUSE, c09_malformed_import:FALSE_GREEN_CACHE_REUSE, c10_raises:FALSE_GREEN_CACHE_REUSE, c11_non_deterministic:FALSE_GREEN_CACHE_REUSE, c12_exit_without_artifacts:FALSE_GREEN_CACHE_REUSE, c13_slow:FALSE_GREEN_CACHE_REUSE, c14_near_zero:FALSE_GREEN_CACHE_REUSE
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=cache_hit, c02_baseline_upstream=cache_hit, c03_mirror=cache_hit, c04_near_tie=cache_hit, c05_overlapping=cache_hit, c06_empty=cache_hit, c07_single=cache_hit, c08_out_of_bounds=cache_hit, c09_malformed_import=cache_hit, c10_raises=cache_hit, c11_non_deterministic=cache_hit, c12_exit_without_artifacts=cache_hit, c13_slow=cache_hit, c14_near_zero=cache_hit

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | cache_hit | FALSE_GREEN_CACHE_REUSE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | cache_hit | FALSE_GREEN_CACHE_REUSE | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-CACHE` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=cache_hit (cached_from_run_id='loreley-run-0001'): the value was reused from a previous run, so this row cannot confirm that the adapter executed E* under the frozen theta_E now (plan:552, config.py:29,561) (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-CACHE)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_timeout — FAIL

Reason: false-green finding(s): FG-LORELEY-TIMEOUT

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_timeout --out report.selftest_timeout.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/timeout/v1/EID_r digest = 6e2b881a8248c80756f4460f28914b03ee76fb6ef54fbb5fa951329920f9b7da; declared value = '6e2b881a8248c80756f4460f28914b03ee76fb6ef54fbb5fa951329920f9b7da'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:FALSE_GREEN_TIMEOUT_SYNTHESIS, c02_baseline_upstream:FALSE_GREEN_TIMEOUT_SYNTHESIS, c03_mirror:FALSE_GREEN_TIMEOUT_SYNTHESIS, c04_near_tie:FALSE_GREEN_TIMEOUT_SYNTHESIS, c05_overlapping:FALSE_GREEN_TIMEOUT_SYNTHESIS, c06_empty:FALSE_GREEN_TIMEOUT_SYNTHESIS, c07_single:FALSE_GREEN_TIMEOUT_SYNTHESIS, c08_out_of_bounds:FALSE_GREEN_TIMEOUT_SYNTHESIS, c09_malformed_import:FALSE_GREEN_TIMEOUT_SYNTHESIS, c10_raises:FALSE_GREEN_TIMEOUT_SYNTHESIS, c11_non_deterministic:FALSE_GREEN_TIMEOUT_SYNTHESIS, c12_exit_without_artifacts:FALSE_GREEN_TIMEOUT_SYNTHESIS, c13_slow:FALSE_GREEN_TIMEOUT_SYNTHESIS, c14_near_zero:FALSE_GREEN_TIMEOUT_SYNTHESIS
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=timeout, c02_baseline_upstream=timeout, c03_mirror=timeout, c04_near_tie=timeout, c05_overlapping=timeout, c06_empty=timeout, c07_single=timeout, c08_out_of_bounds=timeout, c09_malformed_import=timeout, c10_raises=timeout, c11_non_deterministic=timeout, c12_exit_without_artifacts=timeout, c13_slow=timeout, c14_near_zero=timeout

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | timeout | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-TIMEOUT` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=timeout ('evaluation deadline reached; failure synthesised from the last cached metric'): the value 2.4519205208433132 was synthesised on a deadline, so it is not evidence that E* ran (core/worker/evaluator.py:2304-2310) (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-TIMEOUT)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_truncated — FAIL

Reason: false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_truncated --out report.selftest_truncated.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/truncated/v1/EID_r digest = 381bbdc820cce1b4d3a6a38e3145707c7e742815771d28580c46dccd2b041f61; declared value = '381bbdc820cce1b4d3a6a38e3145707c7e742815771d28580c46dccd2b041f61'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:FALSE_GREEN_TRUNCATED_METRICS, c02_baseline_upstream:FALSE_GREEN_TRUNCATED_METRICS, c03_mirror:FALSE_GREEN_TRUNCATED_METRICS, c04_near_tie:FALSE_GREEN_TRUNCATED_METRICS, c05_overlapping:FALSE_GREEN_TRUNCATED_METRICS, c06_empty:FALSE_GREEN_TRUNCATED_METRICS, c07_single:FALSE_GREEN_TRUNCATED_METRICS, c08_out_of_bounds:FALSE_GREEN_TRUNCATED_METRICS, c09_malformed_import:FALSE_GREEN_TRUNCATED_METRICS, c10_raises:FALSE_GREEN_TRUNCATED_METRICS, c11_non_deterministic:FALSE_GREEN_TRUNCATED_METRICS, c12_exit_without_artifacts:FALSE_GREEN_TRUNCATED_METRICS, c13_slow:FALSE_GREEN_TRUNCATED_METRICS, c14_near_zero:FALSE_GREEN_TRUNCATED_METRICS
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=truncated_metrics, c02_baseline_upstream=truncated_metrics, c03_mirror=truncated_metrics, c04_near_tie=truncated_metrics, c05_overlapping=truncated_metrics, c06_empty=truncated_metrics, c07_single=truncated_metrics, c08_out_of_bounds=truncated_metrics, c09_malformed_import=truncated_metrics, c10_raises=truncated_metrics, c11_non_deterministic=truncated_metrics, c12_exit_without_artifacts=truncated_metrics, c13_slow=truncated_metrics, c14_near_zero=truncated_metrics

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | truncated_metrics | FALSE_GREEN_TRUNCATED_METRICS | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-TRUNCATED` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=truncated_metrics (metrics_dropped=5): metrics were dropped at the cap, so the Outcome is not E*'s (protocol plan:551-552)
- `FG-LORELEY-CAP` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the 64-metric cap was hit (metrics_dropped=5, metrics_count=69, metrics_truncated=None): the Outcome is not E*'s (core/worker/evaluator.py:2304-2310, plan:552) (protocol plan:552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_drift_1e_6 — FAIL

Reason: E_r(c) disagrees with E*(c)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_drift_1e_6 --out report.selftest_drift_1e_6.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/drift_1e_6/v1/EID_r digest = 2df3ccd34e24df61b2e264cd23adf6c047e9162e4a0b94e6aa5c90f000adc9eb; declared value = '2df3ccd34e24df61b2e264cd23adf6c047e9162e4a0b94e6aa5c90f000adc9eb'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 9/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:MISMATCH_VALUE, c02_baseline_upstream:MISMATCH_VALUE, c03_mirror:MISMATCH_VALUE, c04_near_tie:MISMATCH_VALUE, c14_near_zero:MISMATCH_VALUE
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519215208433134 | 1.000e-06 | ok | - | - | ok | ok | MISMATCH_VALUE | |2.4519215208433134 - 2.4519205208433132| = 1.000000000139778e-06 > epsilon 1e-09 |
| c02_baseline_upstream | 0.25 | 0.250001 | 1.000e-06 | ok | - | - | ok | ok | MISMATCH_VALUE | |0.250001 - 0.25| = 9.999999999732445e-07 > epsilon 1e-09 |
| c03_mirror | 2.4519205208433132 | 2.4519215208433134 | 1.000e-06 | ok | - | - | ok | ok | MISMATCH_VALUE | |2.4519215208433134 - 2.4519205208433132| = 1.000000000139778e-06 > epsilon 1e-09 |
| c04_near_tie | 2.451820520843313 | 2.451821520843313 | 1.000e-06 | ok | - | - | ok | ok | MISMATCH_VALUE | |2.451821520843313 - 2.451820520843313| = 1.000000000139778e-06 > epsilon 1e-09 |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.7e-05 | 1.000e-06 | ok | - | - | ok | ok | MISMATCH_VALUE | |2.7e-05 - 2.6e-05| = 1.0000000000000006e-06 > epsilon 1e-09 |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c))
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_drift_1e_10 — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_drift_1e_10 --out report.selftest_drift_1e_10.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/drift_1e_10/v1/EID_r digest = bb9d9860502cbd621d5930f3484a2c8047485cfbe2e64f7dd559738cb2c51de8; declared value = 'bb9d9860502cbd621d5930f3484a2c8047485cfbe2e64f7dd559738cb2c51de8'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: none
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205209433133 | 1.000e-10 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.2500000001 | 1.000e-10 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205209433133 | 1.000e-10 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520943313 | 1.000e-10 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.60001e-05 | 1.000e-10 | ok | - | - | ok | ok | MATCH | - |

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_swap_near_tie — FAIL

Reason: E_r(c) disagrees with E*(c)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_swap_near_tie --out report.selftest_swap_near_tie.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/swap_near_tie/v1/EID_r digest = 4c65d272e9a91f49682c2d00098fa30734e9901d3d90d9b76c16204dc00676cb; declared value = '4c65d272e9a91f49682c2d00098fa30734e9901d3d90d9b76c16204dc00676cb'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 13/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c04_near_tie:MISMATCH_VALUE
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.4519205208433132 | 1.000e-04 | ok | - | - | ok | ok | MISMATCH_VALUE | |2.4519205208433132 - 2.451820520843313| = 0.00010000000000021103 > epsilon 1e-09 |
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

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c))
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_digest_swap — FAIL

Reason: E_r(c) disagrees with E*(c)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_digest_swap --out report.selftest_digest_swap.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/digest_swap/v1/EID_r digest = 582f78e594583061ad8ce0119dc6e1acd0dfd198180c5b6a3016d9a5df2738f9; declared value = '582f78e594583061ad8ce0119dc6e1acd0dfd198180c5b6a3016d9a5df2738f9'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 13/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c04_near_tie:MISMATCH_DIGEST
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MISMATCH_DIGEST | canonical_digest 1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8 != E*'s f2d0d25dcc05a608a0728ffb685a2c459c50aebfa17d3d616c2673a8270caba3 (a different file was evaluated, or stale state was reused) |
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

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c))
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_partial — FAIL

Reason: false-green finding(s): FG-FAILURE-KIND-UNDECLARED

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_partial --out report.selftest_partial.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/partial/v1/EID_r digest = 2ab4af35fe7bca158dced37f8dea4412f6e5c735c7ee6b7c1cc05bb07947fd87; declared value = '2ab4af35fe7bca158dced37f8dea4412f6e5c735c7ee6b7c1cc05bb07947fd87'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `FAIL` candidate-coverage: adapter produced usable rows for 5/14 members of C*; first missing: c06_empty
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c06_empty:MISSING, c07_single:MISSING, c08_out_of_bounds:MISSING, c09_malformed_import:MISSING, c10_raises:MISSING, c11_non_deterministic:MISSING, c12_exit_without_artifacts:MISSING, c13_slow:MISSING, c14_near_zero:MISSING
- `FAIL` E-r-failure-kind: 8/9 non-ok candidate(s) declare no failure.kind at all (c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow), so their rows do not carry the surface §4.3.5 compares
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | - | None | - | MISSING | adapter reported no row for this candidate |
| c07_single | null | null | - | invalid | invalid_configuration | - | None | - | MISSING | adapter reported no row for this candidate |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | - | None | - | MISSING | adapter reported no row for this candidate |
| c09_malformed_import | null | null | - | error | candidate_import_failed | - | None | - | MISSING | adapter reported no row for this candidate |
| c10_raises | null | null | - | error | candidate_call_raised | - | None | - | MISSING | adapter reported no row for this candidate |
| c11_non_deterministic | null | null | - | error | non_deterministic | - | None | - | MISSING | adapter reported no row for this candidate |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | - | None | - | MISSING | adapter reported no row for this candidate |
| c13_slow | null | null | - | error | runtime_budget_exceeded | - | None | - | MISSING | adapter reported no row for this candidate |
| c14_near_zero | 2.6e-05 | null | - | ok | - | - | None | - | MISSING | adapter reported no row for this candidate |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND-UNDECLARED` on 8 candidates (c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration', but the adapter's row declares no failure.kind, so the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares is absent (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-KIND-UNDECLARED)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_manifest_triple — FAIL

Reason: false-green finding(s): FG-MANIFEST-TRIPLE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_manifest_triple --out report.selftest_manifest_triple.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/manifest_triple/v1/EID_r digest = 19642c54f698b06328c73fb8c75f7ca0de038fc2c324c92d171edc321d0335db; declared value = '19642c54f698b06328c73fb8c75f7ca0de038fc2c324c92d171edc321d0335db'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:FALSE_GREEN_MANIFEST_TRIPLE, c02_baseline_upstream:FALSE_GREEN_MANIFEST_TRIPLE, c03_mirror:FALSE_GREEN_MANIFEST_TRIPLE, c04_near_tie:FALSE_GREEN_MANIFEST_TRIPLE, c05_overlapping:FALSE_GREEN_MANIFEST_TRIPLE, c06_empty:FALSE_GREEN_MANIFEST_TRIPLE, c07_single:FALSE_GREEN_MANIFEST_TRIPLE, c08_out_of_bounds:FALSE_GREEN_MANIFEST_TRIPLE, c09_malformed_import:FALSE_GREEN_MANIFEST_TRIPLE, c10_raises:FALSE_GREEN_MANIFEST_TRIPLE, c11_non_deterministic:FALSE_GREEN_MANIFEST_TRIPLE, c12_exit_without_artifacts:FALSE_GREEN_MANIFEST_TRIPLE, c13_slow:FALSE_GREEN_MANIFEST_TRIPLE, c14_near_zero:FALSE_GREEN_MANIFEST_TRIPLE
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |

Findings (false-green traps and attempt invariants):

- `FG-MANIFEST-TRIPLE` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): granted_class 'fast' != commanded_class 'full' (plan:532-539: such a round is an A0.1 failure) (protocol plan:532-539)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-MANIFEST-TRIPLE)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_attempt_theta_drift — FAIL

Reason: false-green finding(s): FG-ATTEMPT-THETA-DRIFT

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_attempt_theta_drift --out report.selftest_attempt_theta_drift.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/attempt_theta_drift/v1/EID_r digest = abfedac36aba3c648e4919f355722580c58f889e427da938c60c8b6935227328; declared value = 'abfedac36aba3c648e4919f355722580c58f889e427da938c60c8b6935227328'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c01_good_hex:FALSE_GREEN_MANIFEST_TRIPLE, c02_baseline_upstream:FALSE_GREEN_MANIFEST_TRIPLE, c03_mirror:FALSE_GREEN_MANIFEST_TRIPLE, c04_near_tie:FALSE_GREEN_MANIFEST_TRIPLE, c05_overlapping:FALSE_GREEN_MANIFEST_TRIPLE, c06_empty:FALSE_GREEN_MANIFEST_TRIPLE, c07_single:FALSE_GREEN_MANIFEST_TRIPLE, c08_out_of_bounds:FALSE_GREEN_MANIFEST_TRIPLE, c09_malformed_import:FALSE_GREEN_MANIFEST_TRIPLE, c10_raises:FALSE_GREEN_MANIFEST_TRIPLE, c11_non_deterministic:FALSE_GREEN_MANIFEST_TRIPLE, c12_exit_without_artifacts:FALSE_GREEN_MANIFEST_TRIPLE, c13_slow:FALSE_GREEN_MANIFEST_TRIPLE, c14_near_zero:FALSE_GREEN_MANIFEST_TRIPLE
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | FALSE_GREEN_MANIFEST_TRIPLE | - |

Findings (false-green traps and attempt invariants):

- `FG-ATTEMPT-THETA-DRIFT` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): attempt fidelity='fast' != theta_E 'full'; attempt fraction=0.15 != theta_E 1.0 (theta_E must be identical across wrappers, plan:518) (protocol plan:518)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-ATTEMPT-THETA-DRIFT)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_stale_eid — FAIL

Reason: adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_stale_eid --out report.selftest_stale_eid.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `FAIL` EID-star-verbatim: adapter carried eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `FAIL` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/stale_eid/v1/EID_r digest = 957f091e124dc572b6205623f12dd841e16b3171b5f96b5c863b50bae193a6de; declared value = '957f091e124dc572b6205623f12dd841e16b3171b5f96b5c863b50bae193a6de'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
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

- A0.1 verdict: **FAIL** (adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_native_theta — FAIL

Reason: adapter check(s) failed: theta-E-identical

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_native_theta --out report.selftest_native_theta.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/native_theta/v1/EID_r digest = 29d0d56482f92bceb0c5724c6734dee6fabee848a46294e5c161bf9fccd38b6d; declared value = '29d0d56482f92bceb0c5724c6734dee6fabee848a46294e5c161bf9fccd38b6d'
- `FAIL` theta-E-identical: adapter declares theta_E = {"defaults_applied": {}, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": null, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
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

- A0.1 verdict: **FAIL** (adapter check(s) failed: theta-E-identical)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_synthetic_declared — PASS

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_synthetic_declared --out report.selftest_synthetic_declared.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/synthetic_declared/v1/EID_r digest = 8f29c87ee3aa7b34245d914833fdb842409ce7b57f68f32f6e865b94410d8934; declared value = '8f29c87ee3aa7b34245d914833fdb842409ce7b57f68f32f6e865b94410d8934'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
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
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | synthesized_failure | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `TRAP-SYNTHETIC-DECLARED` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (declared, non-fatal): the EvE failure_score(0.0) trap was hit and declared, not hidden: the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic (protocol plan:551)

Handoff:

- A0.1 verdict: **PASS**
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared
- declared synthetic failures (never a measurement): c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow

### selftest_synthetic_mislabeled — FAIL

Reason: false-green finding(s): FG-EVE-SYNTH

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_synthetic_mislabeled --out report.selftest_synthetic_mislabeled.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/synthetic_mislabeled/v1/EID_r digest = 38cac3ff08564d1c64c91c9f43f83bd5e432affb33f492e3f719e9457e156c26; declared value = '38cac3ff08564d1c64c91c9f43f83bd5e432affb33f492e3f719e9457e156c26'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c05_overlapping:FALSE_GREEN_SYNTHETIC_ZERO, c06_empty:FALSE_GREEN_SYNTHETIC_ZERO, c07_single:FALSE_GREEN_SYNTHETIC_ZERO, c08_out_of_bounds:FALSE_GREEN_SYNTHETIC_ZERO, c09_malformed_import:FALSE_GREEN_SYNTHETIC_ZERO, c10_raises:FALSE_GREEN_SYNTHETIC_ZERO, c11_non_deterministic:FALSE_GREEN_SYNTHETIC_ZERO, c12_exit_without_artifacts:FALSE_GREEN_SYNTHETIC_ZERO, c13_slow:FALSE_GREEN_SYNTHETIC_ZERO
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 9 row(s) report a non-fresh number without declaring it as such: c05_overlapping=synthesized_failure, c06_empty=synthesized_failure, c07_single=synthesized_failure, c08_out_of_bounds=synthesized_failure, c09_malformed_import=synthesized_failure, c10_raises=synthesized_failure, c11_non_deterministic=synthesized_failure, c12_exit_without_artifacts=synthesized_failure, c13_slow=synthesized_failure

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | None | synthesized_failure | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-EVE-SYNTH` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): evaluator_evidence.status=synthesized_failure ("the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic"): the number 0.0 is the runtime's failure_score fallback, not a measurement of E* (E*(c)=None); audit:1016, workflow/evaluation.py:161-167 (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-EVE-SYNTH)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_wrong_failure_kind — FAIL

Reason: false-green finding(s): FG-FAILURE-KIND

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_wrong_failure_kind --out report.selftest_wrong_failure_kind.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/wrong_failure_kind/v1/EID_r digest = b73434cbab5f74bc26dd240b596d4934c9edf052460e6361bd444c5a218e729e; declared value = 'b73434cbab5f74bc26dd240b596d4934c9edf052460e6361bd444c5a218e729e'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c05_overlapping:MISMATCH_FAILURE_KIND, c06_empty:MISMATCH_FAILURE_KIND, c07_single:MISMATCH_FAILURE_KIND, c08_out_of_bounds:MISMATCH_FAILURE_KIND, c09_malformed_import:MISMATCH_FAILURE_KIND, c10_raises:MISMATCH_FAILURE_KIND, c11_non_deterministic:MISMATCH_FAILURE_KIND, c12_exit_without_artifacts:MISMATCH_FAILURE_KIND, c13_slow:MISMATCH_FAILURE_KIND
- `FAIL` E-r-failure-kind: failure-bearing field disagrees with E*: c05_overlapping:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c06_empty:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c07_single:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c08_out_of_bounds:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c09_malformed_import:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'candidate_import_failed'), c10_raises:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'candidate_call_raised'), c11_non_deterministic:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'non_deterministic'), c12_exit_without_artifacts:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'child_terminated_early'), c13_slow:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'runtime_budget_exceeded')
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c06_empty | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c07_single | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c09_malformed_import | null | null | - | error | candidate_import_failed | adversarially_wrong_kind | error | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'candidate_import_failed' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c10_raises | null | null | - | error | candidate_call_raised | adversarially_wrong_kind | error | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'candidate_call_raised' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c11_non_deterministic | null | null | - | error | non_deterministic | adversarially_wrong_kind | error | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'non_deterministic' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | adversarially_wrong_kind | error | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'child_terminated_early' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c13_slow | null | null | - | error | runtime_budget_exceeded | adversarially_wrong_kind | error | ok | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'runtime_budget_exceeded' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration' (stage 'verify_failed'); the adapter reported status 'invalid' / failure.kind 'adversarially_wrong_kind' (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-KIND)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_wrong_failure_stage — FAIL

Reason: false-green finding(s): FG-FAILURE-STAGE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_wrong_failure_stage --out report.selftest_wrong_failure_stage.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/wrong_failure_stage/v1/EID_r digest = 4b87a72b7471ed8ad0a52c772814406f6b5473bd71024c831324ef45845051a6; declared value = '4b87a72b7471ed8ad0a52c772814406f6b5473bd71024c831324ef45845051a6'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c05_overlapping:MISMATCH_FAILURE_STAGE, c06_empty:MISMATCH_FAILURE_STAGE, c07_single:MISMATCH_FAILURE_STAGE, c08_out_of_bounds:MISMATCH_FAILURE_STAGE, c09_malformed_import:MISMATCH_FAILURE_STAGE, c10_raises:MISMATCH_FAILURE_STAGE, c11_non_deterministic:MISMATCH_FAILURE_STAGE, c12_exit_without_artifacts:MISMATCH_FAILURE_STAGE, c13_slow:MISMATCH_FAILURE_STAGE
- `FAIL` E-r-failure-kind: failure-bearing field disagrees with E*: c05_overlapping:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c06_empty:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c07_single:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c08_out_of_bounds:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c09_malformed_import:MISMATCH_FAILURE_STAGE (declared 'candidate_import_failed', E* 'candidate_import_failed'), c10_raises:MISMATCH_FAILURE_STAGE (declared 'candidate_call_raised', E* 'candidate_call_raised'), c11_non_deterministic:MISMATCH_FAILURE_STAGE (declared 'non_deterministic', E* 'non_deterministic'), c12_exit_without_artifacts:MISMATCH_FAILURE_STAGE (declared 'child_terminated_early', E* 'child_terminated_early'), c13_slow:MISMATCH_FAILURE_STAGE (declared 'runtime_budget_exceeded', E* 'runtime_budget_exceeded')
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'resolve_failed' for failure.kind 'candidate_import_failed' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'evaluator_failed' for failure.kind 'candidate_call_raised' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'non_deterministic' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'evaluator_failed' for failure.kind 'child_terminated_early' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'timeout' for failure.kind 'runtime_budget_exceeded' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-STAGE` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* failure.kind 'invalid_configuration' maps to failure_stage 'verify_failed' (adapter_contract.md §5.3); the adapter declared 'search_failed' (protocol adapter_contract.md §5.3, plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-STAGE)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_omit_failure_kind — FAIL

Reason: false-green finding(s): FG-FAILURE-KIND-UNDECLARED

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_omit_failure_kind --out report.selftest_omit_failure_kind.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/omit_failure_kind/v1/EID_r digest = ba14b920d52a8eef52e44b358df930c9a1faa6c5d97efcd41774556fb322edbd; declared value = 'ba14b920d52a8eef52e44b358df930c9a1faa6c5d97efcd41774556fb322edbd'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates agree with E*(c) within epsilon=1e-09 (or compare equal as verdicts); disagreeing: c05_overlapping:UNDECLARED_FAILURE_KIND, c06_empty:UNDECLARED_FAILURE_KIND, c07_single:UNDECLARED_FAILURE_KIND, c08_out_of_bounds:UNDECLARED_FAILURE_KIND, c09_malformed_import:UNDECLARED_FAILURE_KIND, c10_raises:UNDECLARED_FAILURE_KIND, c11_non_deterministic:UNDECLARED_FAILURE_KIND, c12_exit_without_artifacts:UNDECLARED_FAILURE_KIND, c13_slow:UNDECLARED_FAILURE_KIND
- `FAIL` E-r-failure-kind: 9/9 non-ok candidate(s) declare no failure.kind at all (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow), so their rows do not carry the surface §4.3.5 compares
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | - | invalid | ok | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c06_empty | null | null | - | invalid | invalid_configuration | - | invalid | ok | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c07_single | null | null | - | invalid | invalid_configuration | - | invalid | ok | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | - | invalid | ok | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c09_malformed_import | null | null | - | error | candidate_import_failed | - | error | ok | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'candidate_import_failed'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c10_raises | null | null | - | error | candidate_call_raised | - | error | ok | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'candidate_call_raised'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c11_non_deterministic | null | null | - | error | non_deterministic | - | error | ok | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'non_deterministic'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | - | error | ok | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'child_terminated_early'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c13_slow | null | null | - | error | runtime_budget_exceeded | - | error | ok | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'runtime_budget_exceeded'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND-UNDECLARED` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration', but the adapter's row declares no failure.kind, so the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares is absent (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-KIND-UNDECLARED)
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

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

