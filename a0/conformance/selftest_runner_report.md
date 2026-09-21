# A0.1 cross-adapter conformance report

Generated 2026-09-21T17:14:22+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own claim about its A0.1 outcome is recorded only under a key named `__untrusted` (see `adapter_claim__untrusted` / `adapter_self_declaration__untrusted`), so it can never be read as a verdict.

## Verdicts

| runtime | A0.1 | measured / 14 | adapted (declared, NOT measured) | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|---|---|
| selftest_honest | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 | - | not judged here | all checks passed |
| selftest_clean | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 | - | not judged here | all checks passed |
| selftest_zero_on_error | FAIL | 5/14 | 0/14 | 5/14 (9 FALSE_GREEN_SYNTHETIC_ZERO) | FG-EVE-SYNTH | not judged here | false-green finding(s): FG-EVE-SYNTH |
| selftest_cache_hit | FAIL | 0/14 | 0/14 | 0/14 (14 FALSE_GREEN_CACHE_REUSE) | FG-LORELEY-CACHE | not judged here | false-green finding(s): FG-LORELEY-CACHE |
| selftest_timeout | FAIL | 0/14 | 0/14 | 0/14 (14 FALSE_GREEN_TIMEOUT_SYNTHESIS) | FG-LORELEY-TIMEOUT | not judged here | false-green finding(s): FG-LORELEY-TIMEOUT |
| selftest_truncated | FAIL | 0/14 | 0/14 | 0/14 (14 FALSE_GREEN_TRUNCATED_METRICS) | FG-LORELEY-CAP, FG-LORELEY-TRUNCATED | not judged here | false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED |
| selftest_drift_1e_6 | FAIL | 9/14 | 0/14 | 9/14 (5 MISMATCH_VALUE) | - | not judged here | E_r(c) disagrees with E*(c): 5 x MISMATCH_VALUE |
| selftest_drift_1e_10 | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 | - | not judged here | all checks passed |
| selftest_swap_near_tie | FAIL | 13/14 | 0/14 | 13/14 (1 MISMATCH_VALUE) | - | not judged here | E_r(c) disagrees with E*(c): 1 x MISMATCH_VALUE |
| selftest_digest_swap | FAIL | 13/14 | 0/14 | 13/14 (1 MISMATCH_DIGEST) | - | not judged here | E_r(c) disagrees with E*(c): 1 x MISMATCH_DIGEST |
| selftest_partial | FAIL | 5/14 | 0/14 | 5/14 (9 MISSING) | FG-FAILURE-KIND-UNDECLARED | not judged here | incomplete coverage of C* |
| selftest_manifest_triple | FAIL | 0/14 | 0/14 | 0/14 (14 FALSE_GREEN_MANIFEST_TRIPLE) | FG-MANIFEST-TRIPLE | not judged here | false-green finding(s): FG-MANIFEST-TRIPLE |
| selftest_attempt_theta_drift | FAIL | 0/14 | 0/14 | 0/14 (14 FALSE_GREEN_MANIFEST_TRIPLE) | FG-ATTEMPT-THETA-DRIFT | not judged here | false-green finding(s): FG-ATTEMPT-THETA-DRIFT |
| selftest_stale_eid | FAIL | 14/14 | 0/14 | 14/14 | - | not judged here | adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star |
| selftest_native_theta | FAIL | 14/14 | 0/14 | 14/14 | - | not judged here | adapter check(s) failed: theta-E-identical |
| selftest_synthetic_declared | PARTIAL (5/14 measured) | 5/14 | 9/14 (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) | 14/14 (9 SYNTHETIC_DECLARED) | TRAP-SYNTHETIC-DECLARED | not judged here | 5/14 rows measured by the runtime's own evaluator interface; 9/14 accepted only on adapter-supplied semantics (c05_overlapping, c06_empty, c07_single, c08_ou... |
| selftest_synthetic_mislabeled | FAIL | 5/14 | 0/14 | 5/14 (9 FALSE_GREEN_SYNTHETIC_ZERO) | FG-EVE-SYNTH | not judged here | false-green finding(s): FG-EVE-SYNTH |
| selftest_wrong_failure_kind | FAIL | 5/14 | 0/14 | 5/14 (9 MISMATCH_FAILURE_KIND) | FG-FAILURE-KIND | not judged here | false-green finding(s): FG-FAILURE-KIND |
| selftest_wrong_failure_stage | FAIL | 5/14 | 0/14 | 5/14 (9 MISMATCH_FAILURE_STAGE) | FG-FAILURE-STAGE | not judged here | false-green finding(s): FG-FAILURE-STAGE |
| selftest_env_drift | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 (14 EXECUTION_ENV_DRIFT) | - | not judged here | 14/14 rows are EXECUTION_ENV_DRIFT: the behaviour agrees, the interpreter does not match the pinned one (sanctioned set), so this runtime's rows are not meas... |
| selftest_env_drift_unsanctioned | FAIL | 14/14 | 0/14 | 0/14 (14 MISMATCH_EXECUTION_ENV) | - | not judged here | E_r(c) disagrees with E*(c): 14 x MISMATCH_EXECUTION_ENV |
| selftest_measurement_pass | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 | - | not judged here | all checks passed |
| selftest_no_token | FAIL | 14/14 | 0/14 | 0/14 (14 MISSING_ATTESTATION) | MISSING_ATTESTATION | not judged here | not accepting: 14 x MISSING_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes... |
| selftest_foreign_token | FAIL | 14/14 | 0/14 | 0/14 (14 MISMATCH_ATTESTATION) | MISMATCH_ATTESTATION | not judged here | not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the byte... |
| selftest_no_identity | FAIL | 14/14 | 0/14 | 0/14 (14 MISSING_IDENTITY) | MISSING_IDENTITY | not judged here | not accepting: 14 x MISSING_IDENTITY -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it... |
| selftest_mutant_identity | FAIL | 14/14 | 0/14 | 0/14 (14 MISMATCH_ATTESTATION) | MISMATCH_ATTESTATION | not judged here | not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the byte... |
| selftest_other_candidate_bytes | FAIL | 14/14 | 0/14 | 12/14 (2 MISMATCH_ATTESTATION) | MISMATCH_ATTESTATION | not judged here | not accepting: 2 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes... |
| selftest_attest_other_measurement | FAIL | 14/14 | 0/14 | 0/14 (14 MISMATCH_ATTESTATION) | MISMATCH_ATTESTATION | not judged here | not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the byte... |
| selftest_omit_failure_kind | FAIL | 5/14 | 0/14 | 5/14 (9 UNDECLARED_FAILURE_KIND) | FG-FAILURE-KIND-UNDECLARED | not judged here | false-green finding(s): FG-FAILURE-KIND-UNDECLARED |

A0.1-only screen: `r_1_a0_1_only = ['selftest_honest', 'selftest_clean', 'selftest_drift_1e_10', 'selftest_env_drift', 'selftest_measurement_pass']` (n_pass=5, n_partial=1, n_fail=23, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

PARTIAL A0.1 (every row agrees, but at least one only on adapter-supplied semantics), deliberately excluded from the screen set: `r_1_a0_1_partial = ['selftest_synthetic_declared']`.

`|R_1| >= 1` is a CANDIDATE SCREEN over runtimes and is a different object from per-runtime qualification. The screen asks whether the study may continue (at least one substrate survives A0); qualification asks whether a given runtime's A0.1 answer is measured or merely adapted. `r_1_a0_1_only` lists runtimes whose A0.1 is PASS (every row measured) and `r_1_a0_1_partial` lists runtimes whose A0.1 is PARTIAL (some rows accepted only on adapter-supplied semantics). A PARTIAL runtime is deliberately NOT in `r_1_a0_1_only`, so a partial result can never be diluted by siblings that passed. Per-runtime eligibility for A1 is declared separately and explicitly by the `Eligible(r)` predicate in `a0/qualification/qualification.json` (see `a0/qualification/QUALIFICATION.md`); the screen can pass while no runtime is Eligible().

## Measurement envelope (D3) and declared execution set (D1)

Envelope mode **required** (required = True): the harness issues one OID-style measurement token per member of C* from its own E* sweep, and every adapter row must echo it and attest the evaluator bytes, candidate bytes and behaviour digest it used; a row that omits them is non-accepting (external review D3)

The harness issued `14` measurement tokens into its own state root `/home/ebt/rsi-dev/a0/conformance/out/envelope/measurement_tokens.a01-reference-20260921T171004.json` (sha256 `29953a73546ecc20...`, nonce `dc5e66e616ee5a78608f821ccbe709e9`, run `a01-reference-20260921T171004`), handed to every adapter as `{"env": "A0_ENVELOPE=<path>", "cli_flag": "--envelope (optional)"}`.

The harness's own sweep ran under {"implementation": "cpython", "version": "3.12.11"} (classification `PINNED` against the declared set).

Declared allowed execution set: pinned `{"implementation": "cpython", "version": "3.12.11", "interpreter_path": "a0/tasks/circle-packing/.venv/bin/python", "source": "a0/tasks/circle-packing/E_STAR.json:evaluator.interpreter (the environment the frozen table was measured under)", "meaning": "PINNED = the execution environment E_STAR.json's per-candidate canonical_digest values are bound to. The reference sweep and the measurement tokens are issued under it."}`, sanctioned `[{"implementation": "cpython", "version": "3.12.11"}, {"implementation": "cpython", "version": "3.14.7"}]` (`/home/ebt/rsi-dev/a0/envelope/execution-set.json`).

> UNDECIDED and documented, not decided: folding this allowed execution set into EID*'s Config would make broadening it a re-freeze of EID* = 664115e0...9328. See a0/envelope/execution-set.json:coupling_question_UNDECIDED and a0/envelope/README.md.

| runtime | attestation required | rows attesting | MISSING_ATTESTATION | MISSING_IDENTITY | MISMATCH_ATTESTATION | EXECUTION_ENV_DRIFT | MISMATCH_EXECUTION_ENV |
|---|---|---|---|---|---|---|---|
| selftest_honest | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_clean | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_zero_on_error | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_cache_hit | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_timeout | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_truncated | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_drift_1e_6 | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_drift_1e_10 | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_swap_near_tie | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_digest_swap | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_partial | True | 5 | 0 | 0 | 0 | 0 | 0 |
| selftest_manifest_triple | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_attempt_theta_drift | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_stale_eid | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_native_theta | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_synthetic_declared | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_synthetic_mislabeled | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_wrong_failure_kind | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_wrong_failure_stage | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_env_drift | True | 14 | 0 | 0 | 0 | 14 | 0 |
| selftest_env_drift_unsanctioned | True | 14 | 0 | 0 | 0 | 0 | 14 |
| selftest_measurement_pass | True | 14 | 0 | 0 | 0 | 0 | 0 |
| selftest_no_token | True | 0 | 14 | 0 | 0 | 0 | 0 |
| selftest_foreign_token | True | 0 | 0 | 0 | 14 | 0 | 0 |
| selftest_no_identity | True | 0 | 0 | 14 | 0 | 0 | 0 |
| selftest_mutant_identity | True | 0 | 0 | 0 | 14 | 0 | 0 |
| selftest_other_candidate_bytes | True | 12 | 0 | 0 | 2 | 0 | 0 |
| selftest_attest_other_measurement | True | 0 | 0 | 0 | 14 | 0 | 0 |
| selftest_omit_failure_kind | True | 14 | 0 | 0 | 0 | 0 | 0 |

## Reference table reproducibility

Fresh sweep of `E*` over `C*` with the frozen invocation reproduces `E_STAR.json` exactly: **True**; `C*` unchanged by the sweep: **True**.

Execution environment of that sweep: **PINNED** (observed `{"implementation": "cpython", "version": "3.12.11"}`, pinned `{"implementation": "cpython", "version": "3.12.11"}`). A sanctioned interpreter drift reproduces every number and is reported here as an environment verdict, never as a behaviour mismatch (external review D1).

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

Row verdicts: `MATCH` (number agrees within epsilon), `MATCH_VERDICT` (no number on either side, verdicts compared), `SYNTHETIC_DECLARED` (the runtime's lane returned a declared synthetic failure where E* has no number -- acceptable, but its 0.0 is never a measurement, and a runtime with such a row is `PARTIAL`, not `PASS`), `FALSE_GREEN_*` (a number where none exists, or a non-fresh number), `MISMATCH_*`, `MISSING`.

Two further verdicts split out of `MISMATCH_DIGEST` by external review D1 and D3, because folding them into it made two different things look like the same one:

- `EXECUTION_ENV_DRIFT` -- the behaviour payload agrees with `E*`'s (the Outcome minus `canonical_digest` and `interpreter`), and the row ran under an interpreter that is in the declared allowed execution set but is not the pinned one. **Accepting**: this is an environment difference, never "the evaluator's behaviour disagrees". `MISMATCH_EXECUTION_ENV` is the same situation with an interpreter *outside* that set: non-accepting.
- `MISSING_ATTESTATION` / `MISSING_IDENTITY` / `MISMATCH_ATTESTATION` -- the row does not carry the harness's measurement token, or echoes it without attesting the evaluator bytes / candidate bytes / behaviour digest it used, or contradicts what the harness itself measured. Fail-closed: an omission is non-accepting even when every number agrees. The attestation is submitted by the runtime lane, so it establishes what the row *claims and joins*, not that the claimed bytes were executed.

### selftest_honest — PASS (14/14 measured)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_honest --out report.selftest_honest.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/reference_adapter/v1/EID_r digest = ec55edeefc784e0f0da5d74f245a3be22d929e6f4d9b8535dcb4030de166df41; declared value = 'ec55edeefc784e0f0da5d74f245a3be22d929e6f4d9b8535dcb4030de166df41'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (submitted_outcome_payload) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **PASS (14/14 measured)**
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_clean — PASS (14/14 measured)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_clean --out report.selftest_clean.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/pass/v1/EID_r digest = 93685028199afb59ac51320ce75b7ca1ea5815d097277ed8e4d0e3cb42089e38; declared value = '93685028199afb59ac51320ce75b7ca1ea5815d097277ed8e4d0e3cb42089e38'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **PASS (14/14 measured)**
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_zero_on_error — FAIL

Reason: false-green finding(s): FG-EVE-SYNTH

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_zero_on_error --out report.selftest_zero_on_error.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/zero_on_error/v1/EID_r digest = e432ec4367fe207e33989ccba167bee9e377417b0e7d18d5ba1fb2f56fb83d48; declared value = 'e432ec4367fe207e33989ccba167bee9e377417b0e7d18d5ba1fb2f56fb83d48'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c05_overlapping:FALSE_GREEN_SYNTHETIC_ZERO, c06_empty:FALSE_GREEN_SYNTHETIC_ZERO, c07_single:FALSE_GREEN_SYNTHETIC_ZERO, c08_out_of_bounds:FALSE_GREEN_SYNTHETIC_ZERO, c09_malformed_import:FALSE_GREEN_SYNTHETIC_ZERO, c10_raises:FALSE_GREEN_SYNTHETIC_ZERO, c11_non_deterministic:FALSE_GREEN_SYNTHETIC_ZERO, c12_exit_without_artifacts:FALSE_GREEN_SYNTHETIC_ZERO, c13_slow:FALSE_GREEN_SYNTHETIC_ZERO; disagreeing on the measurement surface: c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 9 row(s) report a non-fresh number without declaring it as such: c05_overlapping=synthesized_failure, c06_empty=synthesized_failure, c07_single=synthesized_failure, c08_out_of_bounds=synthesized_failure, c09_malformed_import=synthesized_failure, c10_raises=synthesized_failure, c11_non_deterministic=synthesized_failure, c12_exit_without_artifacts=synthesized_failure, c13_slow=synthesized_failure

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | ok | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-EVE-SYNTH` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): evaluator_evidence.status=synthesized_failure ('evaluation exception mapped to failure_score(0.0) -- the EvE trap'): the number 0.0 is the runtime's failure_score fallback, not a measurement of E* (E*(c)=None); audit:1016, workflow/evaluation.py:161-167 (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-EVE-SYNTH)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_cache_hit — FAIL

Reason: false-green finding(s): FG-LORELEY-CACHE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_cache_hit --out report.selftest_cache_hit.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/cache_hit/v1/EID_r digest = e84dd4e9202e80ed35d5d7965083992bc340fe13cc6396151e05acf95b6f62da; declared value = 'e84dd4e9202e80ed35d5d7965083992bc340fe13cc6396151e05acf95b6f62da'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:FALSE_GREEN_CACHE_REUSE, c02_baseline_upstream:FALSE_GREEN_CACHE_REUSE, c03_mirror:FALSE_GREEN_CACHE_REUSE, c04_near_tie:FALSE_GREEN_CACHE_REUSE, c05_overlapping:FALSE_GREEN_CACHE_REUSE, c06_empty:FALSE_GREEN_CACHE_REUSE, c07_single:FALSE_GREEN_CACHE_REUSE, c08_out_of_bounds:FALSE_GREEN_CACHE_REUSE, c09_malformed_import:FALSE_GREEN_CACHE_REUSE, c10_raises:FALSE_GREEN_CACHE_REUSE, c11_non_deterministic:FALSE_GREEN_CACHE_REUSE, c12_exit_without_artifacts:FALSE_GREEN_CACHE_REUSE, c13_slow:FALSE_GREEN_CACHE_REUSE, c14_near_zero:FALSE_GREEN_CACHE_REUSE; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=cache_hit, c02_baseline_upstream=cache_hit, c03_mirror=cache_hit, c04_near_tie=cache_hit, c05_overlapping=cache_hit, c06_empty=cache_hit, c07_single=cache_hit, c08_out_of_bounds=cache_hit, c09_malformed_import=cache_hit, c10_raises=cache_hit, c11_non_deterministic=cache_hit, c12_exit_without_artifacts=cache_hit, c13_slow=cache_hit, c14_near_zero=cache_hit

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | cache_hit | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_CACHE_REUSE | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-CACHE` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=cache_hit (cached_from_run_id='loreley-run-0001'): the value was reused from a previous run, so this row cannot confirm that the adapter executed E* under the frozen theta_E now (plan:552, config.py:29,561) (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-CACHE)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_timeout — FAIL

Reason: false-green finding(s): FG-LORELEY-TIMEOUT

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_timeout --out report.selftest_timeout.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/timeout/v1/EID_r digest = 6e2b881a8248c80756f4460f28914b03ee76fb6ef54fbb5fa951329920f9b7da; declared value = '6e2b881a8248c80756f4460f28914b03ee76fb6ef54fbb5fa951329920f9b7da'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:FALSE_GREEN_TIMEOUT_SYNTHESIS, c02_baseline_upstream:FALSE_GREEN_TIMEOUT_SYNTHESIS, c03_mirror:FALSE_GREEN_TIMEOUT_SYNTHESIS, c04_near_tie:FALSE_GREEN_TIMEOUT_SYNTHESIS, c05_overlapping:FALSE_GREEN_TIMEOUT_SYNTHESIS, c06_empty:FALSE_GREEN_TIMEOUT_SYNTHESIS, c07_single:FALSE_GREEN_TIMEOUT_SYNTHESIS, c08_out_of_bounds:FALSE_GREEN_TIMEOUT_SYNTHESIS, c09_malformed_import:FALSE_GREEN_TIMEOUT_SYNTHESIS, c10_raises:FALSE_GREEN_TIMEOUT_SYNTHESIS, c11_non_deterministic:FALSE_GREEN_TIMEOUT_SYNTHESIS, c12_exit_without_artifacts:FALSE_GREEN_TIMEOUT_SYNTHESIS, c13_slow:FALSE_GREEN_TIMEOUT_SYNTHESIS, c14_near_zero:FALSE_GREEN_TIMEOUT_SYNTHESIS; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=timeout, c02_baseline_upstream=timeout, c03_mirror=timeout, c04_near_tie=timeout, c05_overlapping=timeout, c06_empty=timeout, c07_single=timeout, c08_out_of_bounds=timeout, c09_malformed_import=timeout, c10_raises=timeout, c11_non_deterministic=timeout, c12_exit_without_artifacts=timeout, c13_slow=timeout, c14_near_zero=timeout

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | timeout | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TIMEOUT_SYNTHESIS | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-TIMEOUT` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=timeout ('evaluation deadline reached; failure synthesised from the last cached metric'): the value 2.4519205208433132 was synthesised on a deadline, so it is not evidence that E* ran (core/worker/evaluator.py:2304-2310) (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-TIMEOUT)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_truncated — FAIL

Reason: false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_truncated --out report.selftest_truncated.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/truncated/v1/EID_r digest = 381bbdc820cce1b4d3a6a38e3145707c7e742815771d28580c46dccd2b041f61; declared value = '381bbdc820cce1b4d3a6a38e3145707c7e742815771d28580c46dccd2b041f61'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:FALSE_GREEN_TRUNCATED_METRICS, c02_baseline_upstream:FALSE_GREEN_TRUNCATED_METRICS, c03_mirror:FALSE_GREEN_TRUNCATED_METRICS, c04_near_tie:FALSE_GREEN_TRUNCATED_METRICS, c05_overlapping:FALSE_GREEN_TRUNCATED_METRICS, c06_empty:FALSE_GREEN_TRUNCATED_METRICS, c07_single:FALSE_GREEN_TRUNCATED_METRICS, c08_out_of_bounds:FALSE_GREEN_TRUNCATED_METRICS, c09_malformed_import:FALSE_GREEN_TRUNCATED_METRICS, c10_raises:FALSE_GREEN_TRUNCATED_METRICS, c11_non_deterministic:FALSE_GREEN_TRUNCATED_METRICS, c12_exit_without_artifacts:FALSE_GREEN_TRUNCATED_METRICS, c13_slow:FALSE_GREEN_TRUNCATED_METRICS, c14_near_zero:FALSE_GREEN_TRUNCATED_METRICS; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 14 row(s) report a non-fresh number without declaring it as such: c01_good_hex=truncated_metrics, c02_baseline_upstream=truncated_metrics, c03_mirror=truncated_metrics, c04_near_tie=truncated_metrics, c05_overlapping=truncated_metrics, c06_empty=truncated_metrics, c07_single=truncated_metrics, c08_out_of_bounds=truncated_metrics, c09_malformed_import=truncated_metrics, c10_raises=truncated_metrics, c11_non_deterministic=truncated_metrics, c12_exit_without_artifacts=truncated_metrics, c13_slow=truncated_metrics, c14_near_zero=truncated_metrics

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | truncated_metrics | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_TRUNCATED_METRICS | - |

Findings (false-green traps and attempt invariants):

- `FG-LORELEY-TRUNCATED` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): evaluator_evidence.status=truncated_metrics (metrics_dropped=5): metrics were dropped at the cap, so the Outcome is not E*'s (protocol plan:551-552)
- `FG-LORELEY-CAP` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the 64-metric cap was hit (metrics_dropped=5, metrics_count=69, metrics_truncated=None): the Outcome is not E*'s (core/worker/evaluator.py:2304-2310, plan:552) (protocol plan:552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-LORELEY-CAP, FG-LORELEY-TRUNCATED)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_drift_1e_6 — FAIL

Reason: E_r(c) disagrees with E*(c): 5 x MISMATCH_VALUE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_drift_1e_6 --out report.selftest_drift_1e_6.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/drift_1e_6/v1/EID_r digest = 2df3ccd34e24df61b2e264cd23adf6c047e9162e4a0b94e6aa5c90f000adc9eb; declared value = '2df3ccd34e24df61b2e264cd23adf6c047e9162e4a0b94e6aa5c90f000adc9eb'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 9/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 9/14. not accepting: c01_good_hex:MISMATCH_VALUE, c02_baseline_upstream:MISMATCH_VALUE, c03_mirror:MISMATCH_VALUE, c04_near_tie:MISMATCH_VALUE, c14_near_zero:MISMATCH_VALUE; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519215208433134 | 1.000e-06 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |2.4519215208433134 - 2.4519205208433132| = 1.000000000139778e-06 > epsilon 1e-09 |
| c02_baseline_upstream | 0.25 | 0.250001 | 1.000e-06 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |0.250001 - 0.25| = 9.999999999732445e-07 > epsilon 1e-09 |
| c03_mirror | 2.4519205208433132 | 2.4519215208433134 | 1.000e-06 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |2.4519215208433134 - 2.4519205208433132| = 1.000000000139778e-06 > epsilon 1e-09 |
| c04_near_tie | 2.451820520843313 | 2.451821520843313 | 1.000e-06 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |2.451821520843313 - 2.451820520843313| = 1.000000000139778e-06 > epsilon 1e-09 |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.7e-05 | 1.000e-06 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |2.7e-05 - 2.6e-05| = 1.0000000000000006e-06 > epsilon 1e-09 |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c): 5 x MISMATCH_VALUE)
- A0.1 qualification: state `FAIL`, measured 9/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_drift_1e_10 — PASS (14/14 measured)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_drift_1e_10 --out report.selftest_drift_1e_10.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/drift_1e_10/v1/EID_r digest = bb9d9860502cbd621d5930f3484a2c8047485cfbe2e64f7dd559738cb2c51de8; declared value = 'bb9d9860502cbd621d5930f3484a2c8047485cfbe2e64f7dd559738cb2c51de8'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205209433133 | 1.000e-10 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.2500000001 | 1.000e-10 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205209433133 | 1.000e-10 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520943313 | 1.000e-10 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.60001e-05 | 1.000e-10 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **PASS (14/14 measured)**
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_swap_near_tie — FAIL

Reason: E_r(c) disagrees with E*(c): 1 x MISMATCH_VALUE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_swap_near_tie --out report.selftest_swap_near_tie.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/swap_near_tie/v1/EID_r digest = 4c65d272e9a91f49682c2d00098fa30734e9901d3d90d9b76c16204dc00676cb; declared value = '4c65d272e9a91f49682c2d00098fa30734e9901d3d90d9b76c16204dc00676cb'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 13/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 13/14. not accepting: c04_near_tie:MISMATCH_VALUE; disagreeing on the measurement surface: c04_near_tie
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.4519205208433132 | 1.000e-04 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_VALUE | |2.4519205208433132 - 2.451820520843313| = 0.00010000000000021103 > epsilon 1e-09 |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c): 1 x MISMATCH_VALUE)
- A0.1 qualification: state `FAIL`, measured 13/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_digest_swap — FAIL

Reason: E_r(c) disagrees with E*(c): 1 x MISMATCH_DIGEST

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_digest_swap --out report.selftest_digest_swap.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/digest_swap/v1/EID_r digest = 582f78e594583061ad8ce0119dc6e1acd0dfd198180c5b6a3016d9a5df2738f9; declared value = '582f78e594583061ad8ce0119dc6e1acd0dfd198180c5b6a3016d9a5df2738f9'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `FAIL` behaviour-vs-execution-env: 13/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter; 1 row(s) disagree on behaviour itself: c04_near_tie
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 13/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 13/14. not accepting: c04_near_tie:MISMATCH_DIGEST; disagreeing on the measurement surface: c04_near_tie
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8 vs E*'s f2d0d25dcc05a608a0728ffb685a2c459c50aebfa17d3d616c2673a8270caba3) |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c): 1 x MISMATCH_DIGEST)
- A0.1 qualification: state `FAIL`, measured 13/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_partial — FAIL

Reason: incomplete coverage of C*

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_partial --out report.selftest_partial.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/partial/v1/EID_r digest = 2ab4af35fe7bca158dced37f8dea4412f6e5c735c7ee6b7c1cc05bb07947fd87; declared value = '2ab4af35fe7bca158dced37f8dea4412f6e5c735c7ee6b7c1cc05bb07947fd87'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 5/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 5/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `FAIL` candidate-coverage: adapter produced usable rows for 5/14 members of C*; first missing: c06_empty
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c06_empty:MISSING, c07_single:MISSING, c08_out_of_bounds:MISSING, c09_malformed_import:MISSING, c10_raises:MISSING, c11_non_deterministic:MISSING, c12_exit_without_artifacts:MISSING, c13_slow:MISSING, c14_near_zero:MISSING; disagreeing on the measurement surface: c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `FAIL` E-r-failure-kind: 8/9 non-ok candidate(s) declare no failure.kind at all (c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow), so their rows do not carry the surface §4.3.5 compares
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c07_single | null | null | - | invalid | invalid_configuration | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c09_malformed_import | null | null | - | error | candidate_import_failed | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c10_raises | null | null | - | error | candidate_call_raised | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c11_non_deterministic | null | null | - | error | non_deterministic | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c13_slow | null | null | - | error | runtime_budget_exceeded | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |
| c14_near_zero | 2.6e-05 | null | - | ok | - | - | None | - | not declared | - | - | MISSING | adapter reported no row for this candidate |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND-UNDECLARED` on 8 candidates (c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration', but the adapter's row declares no failure.kind, so the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares is absent (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (incomplete coverage of C*)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_manifest_triple — FAIL

Reason: false-green finding(s): FG-MANIFEST-TRIPLE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_manifest_triple --out report.selftest_manifest_triple.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/manifest_triple/v1/EID_r digest = 19642c54f698b06328c73fb8c75f7ca0de038fc2c324c92d171edc321d0335db; declared value = '19642c54f698b06328c73fb8c75f7ca0de038fc2c324c92d171edc321d0335db'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:FALSE_GREEN_MANIFEST_TRIPLE, c02_baseline_upstream:FALSE_GREEN_MANIFEST_TRIPLE, c03_mirror:FALSE_GREEN_MANIFEST_TRIPLE, c04_near_tie:FALSE_GREEN_MANIFEST_TRIPLE, c05_overlapping:FALSE_GREEN_MANIFEST_TRIPLE, c06_empty:FALSE_GREEN_MANIFEST_TRIPLE, c07_single:FALSE_GREEN_MANIFEST_TRIPLE, c08_out_of_bounds:FALSE_GREEN_MANIFEST_TRIPLE, c09_malformed_import:FALSE_GREEN_MANIFEST_TRIPLE, c10_raises:FALSE_GREEN_MANIFEST_TRIPLE, c11_non_deterministic:FALSE_GREEN_MANIFEST_TRIPLE, c12_exit_without_artifacts:FALSE_GREEN_MANIFEST_TRIPLE, c13_slow:FALSE_GREEN_MANIFEST_TRIPLE, c14_near_zero:FALSE_GREEN_MANIFEST_TRIPLE; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |

Findings (false-green traps and attempt invariants):

- `FG-MANIFEST-TRIPLE` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): granted_class 'fast' != commanded_class 'full' (plan:532-539: such a round is an A0.1 failure) (protocol plan:532-539)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-MANIFEST-TRIPLE)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_attempt_theta_drift — FAIL

Reason: false-green finding(s): FG-ATTEMPT-THETA-DRIFT

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_attempt_theta_drift --out report.selftest_attempt_theta_drift.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/attempt_theta_drift/v1/EID_r digest = abfedac36aba3c648e4919f355722580c58f889e427da938c60c8b6935227328; declared value = 'abfedac36aba3c648e4919f355722580c58f889e427da938c60c8b6935227328'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:FALSE_GREEN_MANIFEST_TRIPLE, c02_baseline_upstream:FALSE_GREEN_MANIFEST_TRIPLE, c03_mirror:FALSE_GREEN_MANIFEST_TRIPLE, c04_near_tie:FALSE_GREEN_MANIFEST_TRIPLE, c05_overlapping:FALSE_GREEN_MANIFEST_TRIPLE, c06_empty:FALSE_GREEN_MANIFEST_TRIPLE, c07_single:FALSE_GREEN_MANIFEST_TRIPLE, c08_out_of_bounds:FALSE_GREEN_MANIFEST_TRIPLE, c09_malformed_import:FALSE_GREEN_MANIFEST_TRIPLE, c10_raises:FALSE_GREEN_MANIFEST_TRIPLE, c11_non_deterministic:FALSE_GREEN_MANIFEST_TRIPLE, c12_exit_without_artifacts:FALSE_GREEN_MANIFEST_TRIPLE, c13_slow:FALSE_GREEN_MANIFEST_TRIPLE, c14_near_zero:FALSE_GREEN_MANIFEST_TRIPLE; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_MANIFEST_TRIPLE | - |

Findings (false-green traps and attempt invariants):

- `FG-ATTEMPT-THETA-DRIFT` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): attempt fidelity='fast' != theta_E 'full'; attempt fraction=0.15 != theta_E 1.0 (theta_E must be identical across wrappers, plan:518) (protocol plan:518)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-ATTEMPT-THETA-DRIFT)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_stale_eid — FAIL

Reason: adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_stale_eid --out report.selftest_stale_eid.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `FAIL` EID-star-verbatim: adapter carried eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `FAIL` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/stale_eid/v1/EID_r digest = 957f091e124dc572b6205623f12dd841e16b3171b5f96b5c863b50bae193a6de; declared value = '957f091e124dc572b6205623f12dd841e16b3171b5f96b5c863b50bae193a6de'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **FAIL** (adapter check(s) failed: EID-star-verbatim, EID-r-derives-from-EID-star)
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='fac50fc4a5c52556b6d4f35c5a68edbfa076cfde813f336346e1e083ffb24b2d'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_native_theta — FAIL

Reason: adapter check(s) failed: theta-E-identical

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_native_theta --out report.selftest_native_theta.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/native_theta/v1/EID_r digest = 29d0d56482f92bceb0c5724c6734dee6fabee848a46294e5c161bf9fccd38b6d; declared value = '29d0d56482f92bceb0c5724c6734dee6fabee848a46294e5c161bf9fccd38b6d'
- `FAIL` theta-E-identical: adapter declares theta_E = {"defaults_applied": {}, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": null, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **FAIL** (adapter check(s) failed: theta-E-identical)
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_synthetic_declared — PARTIAL (5/14 measured)

Reason: 5/14 rows measured by the runtime's own evaluator interface; 9/14 accepted only on adapter-supplied semantics (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow). No check failed, but this runtime cannot represent E*'s outcome algebra on those rows

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_synthetic_declared --out report.selftest_synthetic_declared.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/synthetic_declared/v1/EID_r digest = 8f29c87ee3aa7b34245d914833fdb842409ce7b57f68f32f6e865b94410d8934; declared value = '8f29c87ee3aa7b34245d914833fdb842409ce7b57f68f32f6e865b94410d8934'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: 9 row(s) carry a declared synthesised failure (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow); no row hides a non-fresh number

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned invalid/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | SYNTHETIC_DECLARED | E* returned error/null; the runtime's own lane reported 0.0 as a synthesised failure (declared: "the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic") |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `TRAP-SYNTHETIC-DECLARED` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (declared, non-fatal): the EvE failure_score(0.0) trap was hit and declared, not hidden: the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic (protocol plan:551)

Handoff:

- A0.1 verdict: **PARTIAL (5/14 measured)** (5/14 rows measured by the runtime's own evaluator interface; 9/14 accepted only on adapter-supplied semantics (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow). No check failed, but this runtime cannot represent E*'s outcome algebra on those rows)
- A0.1 qualification: state `PARTIAL`, measured 5/14 by the runtime's own evaluator interface, adapted 9/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=['c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow']
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

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/synthetic_mislabeled/v1/EID_r digest = 38cac3ff08564d1c64c91c9f43f83bd5e432affb33f492e3f719e9457e156c26; declared value = '38cac3ff08564d1c64c91c9f43f83bd5e432affb33f492e3f719e9457e156c26'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c05_overlapping:FALSE_GREEN_SYNTHETIC_ZERO, c06_empty:FALSE_GREEN_SYNTHETIC_ZERO, c07_single:FALSE_GREEN_SYNTHETIC_ZERO, c08_out_of_bounds:FALSE_GREEN_SYNTHETIC_ZERO, c09_malformed_import:FALSE_GREEN_SYNTHETIC_ZERO, c10_raises:FALSE_GREEN_SYNTHETIC_ZERO, c11_non_deterministic:FALSE_GREEN_SYNTHETIC_ZERO, c12_exit_without_artifacts:FALSE_GREEN_SYNTHETIC_ZERO, c13_slow:FALSE_GREEN_SYNTHETIC_ZERO; disagreeing on the measurement surface: c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `FAIL` evidence-fresh-or-declared: 9 row(s) report a non-fresh number without declaring it as such: c05_overlapping=synthesized_failure, c06_empty=synthesized_failure, c07_single=synthesized_failure, c08_out_of_bounds=synthesized_failure, c09_malformed_import=synthesized_failure, c10_raises=synthesized_failure, c11_non_deterministic=synthesized_failure, c12_exit_without_artifacts=synthesized_failure, c13_slow=synthesized_failure

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c06_empty | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c07_single | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c08_out_of_bounds | null | 0.0 | - | invalid | invalid_configuration | invalid_configuration | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c09_malformed_import | null | 0.0 | - | error | candidate_import_failed | candidate_import_failed | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c10_raises | null | 0.0 | - | error | candidate_call_raised | candidate_call_raised | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c11_non_deterministic | null | 0.0 | - | error | non_deterministic | non_deterministic | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c12_exit_without_artifacts | null | 0.0 | - | error | child_terminated_early | child_terminated_early | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c13_slow | null | 0.0 | - | error | runtime_budget_exceeded | runtime_budget_exceeded | None | synthesized_failure | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | FALSE_GREEN_SYNTHETIC_ZERO | - |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-EVE-SYNTH` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): evaluator_evidence.status=synthesized_failure ("the runtime's lane returned evaluation.failure_score verbatim because a step exception was swallowed; E* itself reported non-ok, so this 0.0 is synthetic"): the number 0.0 is the runtime's failure_score fallback, not a measurement of E* (E*(c)=None); audit:1016, workflow/evaluation.py:161-167 (protocol plan:551-552)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-EVE-SYNTH)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_wrong_failure_kind — FAIL

Reason: false-green finding(s): FG-FAILURE-KIND

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_wrong_failure_kind --out report.selftest_wrong_failure_kind.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/wrong_failure_kind/v1/EID_r digest = b73434cbab5f74bc26dd240b596d4934c9edf052460e6361bd444c5a218e729e; declared value = 'b73434cbab5f74bc26dd240b596d4934c9edf052460e6361bd444c5a218e729e'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c05_overlapping:MISMATCH_FAILURE_KIND, c06_empty:MISMATCH_FAILURE_KIND, c07_single:MISMATCH_FAILURE_KIND, c08_out_of_bounds:MISMATCH_FAILURE_KIND, c09_malformed_import:MISMATCH_FAILURE_KIND, c10_raises:MISMATCH_FAILURE_KIND, c11_non_deterministic:MISMATCH_FAILURE_KIND, c12_exit_without_artifacts:MISMATCH_FAILURE_KIND, c13_slow:MISMATCH_FAILURE_KIND; disagreeing on the measurement surface: c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- `FAIL` E-r-failure-kind: failure-bearing field disagrees with E*: c05_overlapping:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c06_empty:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c07_single:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c08_out_of_bounds:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'invalid_configuration'), c09_malformed_import:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'candidate_import_failed'), c10_raises:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'candidate_call_raised'), c11_non_deterministic:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'non_deterministic'), c12_exit_without_artifacts:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'child_terminated_early'), c13_slow:MISMATCH_FAILURE_KIND (declared 'adversarially_wrong_kind', E* 'runtime_budget_exceeded')
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c06_empty | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c07_single | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | adversarially_wrong_kind | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'invalid_configuration' for a candidate whose E* verdict is 'invalid': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c09_malformed_import | null | null | - | error | candidate_import_failed | adversarially_wrong_kind | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'candidate_import_failed' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c10_raises | null | null | - | error | candidate_call_raised | adversarially_wrong_kind | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'candidate_call_raised' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c11_non_deterministic | null | null | - | error | non_deterministic | adversarially_wrong_kind | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'non_deterministic' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | adversarially_wrong_kind | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'child_terminated_early' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c13_slow | null | null | - | error | runtime_budget_exceeded | adversarially_wrong_kind | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_KIND | failure.kind 'adversarially_wrong_kind' != E*'s 'runtime_budget_exceeded' for a candidate whose E* verdict is 'error': the verdict agrees but the failure does not, which is exactly the mis-staging that makes FailureStage counts non-joinable (adapter_contract.md §4.3.5, §5.3) |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration' (stage 'verify_failed'); the adapter reported status 'invalid' / failure.kind 'adversarially_wrong_kind' (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-KIND)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_wrong_failure_stage — FAIL

Reason: false-green finding(s): FG-FAILURE-STAGE

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_wrong_failure_stage --out report.selftest_wrong_failure_stage.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/wrong_failure_stage/v1/EID_r digest = 4b87a72b7471ed8ad0a52c772814406f6b5473bd71024c831324ef45845051a6; declared value = '4b87a72b7471ed8ad0a52c772814406f6b5473bd71024c831324ef45845051a6'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c05_overlapping:MISMATCH_FAILURE_STAGE, c06_empty:MISMATCH_FAILURE_STAGE, c07_single:MISMATCH_FAILURE_STAGE, c08_out_of_bounds:MISMATCH_FAILURE_STAGE, c09_malformed_import:MISMATCH_FAILURE_STAGE, c10_raises:MISMATCH_FAILURE_STAGE, c11_non_deterministic:MISMATCH_FAILURE_STAGE, c12_exit_without_artifacts:MISMATCH_FAILURE_STAGE, c13_slow:MISMATCH_FAILURE_STAGE; disagreeing on the measurement surface: c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- `FAIL` E-r-failure-kind: failure-bearing field disagrees with E*: c05_overlapping:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c06_empty:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c07_single:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c08_out_of_bounds:MISMATCH_FAILURE_STAGE (declared 'invalid_configuration', E* 'invalid_configuration'), c09_malformed_import:MISMATCH_FAILURE_STAGE (declared 'candidate_import_failed', E* 'candidate_import_failed'), c10_raises:MISMATCH_FAILURE_STAGE (declared 'candidate_call_raised', E* 'candidate_call_raised'), c11_non_deterministic:MISMATCH_FAILURE_STAGE (declared 'non_deterministic', E* 'non_deterministic'), c12_exit_without_artifacts:MISMATCH_FAILURE_STAGE (declared 'child_terminated_early', E* 'child_terminated_early'), c13_slow:MISMATCH_FAILURE_STAGE (declared 'runtime_budget_exceeded', E* 'runtime_budget_exceeded')
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'invalid_configuration' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'resolve_failed' for failure.kind 'candidate_import_failed' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'evaluator_failed' for failure.kind 'candidate_call_raised' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'verify_failed' for failure.kind 'non_deterministic' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'evaluator_failed' for failure.kind 'child_terminated_early' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MISMATCH_FAILURE_STAGE | declared failure_stage 'search_failed' != the frozen §5.3 stage 'timeout' for failure.kind 'runtime_budget_exceeded' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-STAGE` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* failure.kind 'invalid_configuration' maps to failure_stage 'verify_failed' (adapter_contract.md §5.3); the adapter declared 'search_failed' (protocol adapter_contract.md §5.3, plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-STAGE)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_env_drift — PASS (14/14 measured)

Reason: 14/14 rows are EXECUTION_ENV_DRIFT: the behaviour agrees, the interpreter does not match the pinned one (sanctioned set), so this runtime's rows are not measurements in the frozen execution environment

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_env_drift --out report.selftest_env_drift.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/env_drift/v1/EID_r digest = 8465c10780e399874bfff52e97284ac363e6e62cdc823d67b2bcc9c6af41983a; declared value = '8465c10780e399874bfff52e97284ac363e6e62cdc823d67b2bcc9c6af41983a'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: 14 row(s) EXECUTION_ENV_DRIFT (sanctioned, not a behaviour disagreement: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero)
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1) |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1) |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1) |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1) |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1); no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | EXECUTION_ENV_DRIFT {"implementation": "cpython", "version": "3.14.7"} | OK | EXECUTION_ENV_DRIFT | behaviour agrees; the execution environment differs from the pinned interpreter ({'implementation': 'cpython', 'version': '3.14.7'} vs {'implementation': 'cpython', 'version': '3.12.11'}) and is in the declared allowed execution set -> EXECUTION_ENV_DRIFT, not a behaviour disagreement (external review D1) |

Handoff:

- A0.1 verdict: **PASS (14/14 measured)** (14/14 rows are EXECUTION_ENV_DRIFT: the behaviour agrees, the interpreter does not match the pinned one (sanctioned set), so this runtime's rows are not measurements in the frozen execution environment)
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_env_drift_unsanctioned — FAIL

Reason: E_r(c) disagrees with E*(c): 14 x MISMATCH_EXECUTION_ENV

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_env_drift_unsanctioned --out report.selftest_env_drift_unsanctioned.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/env_drift_unsanctioned/v1/EID_r digest = 3e939326e95ca37b4446bfdb4da6f69a8edc950b90eb54bc9ff98a7e6c004321; declared value = '3e939326e95ca37b4446bfdb4da6f69a8edc950b90eb54bc9ff98a7e6c004321'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `FAIL` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter; 14 row(s) MISMATCH_EXECUTION_ENV outside the declared allowed set (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero)
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISMATCH_EXECUTION_ENV, c02_baseline_upstream:MISMATCH_EXECUTION_ENV, c03_mirror:MISMATCH_EXECUTION_ENV, c04_near_tie:MISMATCH_EXECUTION_ENV, c05_overlapping:MISMATCH_EXECUTION_ENV, c06_empty:MISMATCH_EXECUTION_ENV, c07_single:MISMATCH_EXECUTION_ENV, c08_out_of_bounds:MISMATCH_EXECUTION_ENV, c09_malformed_import:MISMATCH_EXECUTION_ENV, c10_raises:MISMATCH_EXECUTION_ENV, c11_non_deterministic:MISMATCH_EXECUTION_ENV, c12_exit_without_artifacts:MISMATCH_EXECUTION_ENV, c13_slow:MISMATCH_EXECUTION_ENV, c14_near_zero:MISMATCH_EXECUTION_ENV
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=error, adapter='error'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=error, adapter='error'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=error, adapter='error'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=error, adapter='error'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | no objective on either side; verdict compared: E*=error, adapter='error'; the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | MISMATCH_EXECUTION_ENV {"implementation": "cpython", "version": "3.13.5"} | OK | MISMATCH_EXECUTION_ENV | the row's behaviour agrees but the interpreter it ran under is outside the declared allowed execution set, so its agreement is not evidence about EID* |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c): 14 x MISMATCH_EXECUTION_ENV)
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_measurement_pass — PASS (14/14 measured)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_measurement_pass --out report.selftest_measurement_pass.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/pass/v1/EID_r digest = 4a72894625eedf7d0b3ce3a77fa49040c426b588df70c743c5feb0e70430d84b; declared value = '4a72894625eedf7d0b3ce3a77fa49040c426b588df70c743c5feb0e70430d84b'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `PASS` E-r-equals-E-star: 14/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. no row disagrees
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Handoff:

- A0.1 verdict: **PASS (14/14 measured)**
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_no_token — FAIL

Reason: not accepting: 14 x MISSING_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_no_token --out report.selftest_no_token.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/no_token/v1/EID_r digest = 392307a0e907c1458ba8ecd46fd5c4ef2376e5cb6ea601c25fef3118e1b16ea5; declared value = '392307a0e907c1458ba8ecd46fd5c4ef2376e5cb6ea601c25fef3118e1b16ea5'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 14/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 0/14 echo a token but attest no identity (MISSING_IDENTITY), 0/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISSING_ATTESTATION, c02_baseline_upstream:MISSING_ATTESTATION, c03_mirror:MISSING_ATTESTATION, c04_near_tie:MISSING_ATTESTATION, c05_overlapping:MISSING_ATTESTATION, c06_empty:MISSING_ATTESTATION, c07_single:MISSING_ATTESTATION, c08_out_of_bounds:MISSING_ATTESTATION, c09_malformed_import:MISSING_ATTESTATION, c10_raises:MISSING_ATTESTATION, c11_non_deterministic:MISSING_ATTESTATION, c12_exit_without_artifacts:MISSING_ATTESTATION, c13_slow:MISSING_ATTESTATION, c14_near_zero:MISSING_ATTESTATION
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_ATTESTATION | MISSING_ATTESTATION | the row's numbers agree but the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) |

Findings (false-green traps and attempt invariants):

- `MISSING_ATTESTATION` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the row echoes no harness measurement token: it declares a number but not that this number came from a run the harness can identify (D3 is fail-closed on omission) (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISSING_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_foreign_token — FAIL

Reason: not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_foreign_token --out report.selftest_foreign_token.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/foreign_token/v1/EID_r digest = f1095fa97d2784b39a0c5754897b1d1ec7106b548f99f1c58dfa0448a8ff5931; declared value = 'f1095fa97d2784b39a0c5754897b1d1ec7106b548f99f1c58dfa0448a8ff5931'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 0/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 0/14 echo a token but attest no identity (MISSING_IDENTITY), 14/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISMATCH_ATTESTATION, c02_baseline_upstream:MISMATCH_ATTESTATION, c03_mirror:MISMATCH_ATTESTATION, c04_near_tie:MISMATCH_ATTESTATION, c05_overlapping:MISMATCH_ATTESTATION, c06_empty:MISMATCH_ATTESTATION, c07_single:MISMATCH_ATTESTATION, c08_out_of_bounds:MISMATCH_ATTESTATION, c09_malformed_import:MISMATCH_ATTESTATION, c10_raises:MISMATCH_ATTESTATION, c11_non_deterministic:MISMATCH_ATTESTATION, c12_exit_without_artifacts:MISMATCH_ATTESTATION, c13_slow:MISMATCH_ATTESTATION, c14_near_zero:MISMATCH_ATTESTATION
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '577d0f9b068fcb10161b40dff41ffa233971d0f2cce749a565711ecfdf7fc39c', which is not the token the harness issued for c01_good_hex ('6db45d69fe9e7ee8ef50538581db4faa469af2abba91a077b87b2afd1b90f0fb'): a foreign, stale or invented measurement id |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '553774e1acb3e848986c21eebaa4f4feae8adbe8676fe650d5afcd0935f43479', which is not the token the harness issued for c02_baseline_upstream ('b9ccf0c0314e189227bcd1ad2cdb15f1b4c076d080769dc91fb506981e06e941'): a foreign, stale or invented measurement id |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '78d9f1ec148b9c4c7aaa1d3a7d623aab69416b5a271b90cc0f81eab9d82fd9a9', which is not the token the harness issued for c03_mirror ('ddaec428a96dd1083a9eb640953bbcf98e1981a6e228d4b68ea34eedcbff4044'): a foreign, stale or invented measurement id |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '1be52bf6bcd5f186a2375b987f3dfff581910810d5a5b25f9eb0068c5021edd5', which is not the token the harness issued for c04_near_tie ('663e0edae90baf3cdb654d02f3364c7694d20042222e39fc0142f2806f9c2f33'): a foreign, stale or invented measurement id |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID '8369c94f9eb1006064374c619847832709090228ced386d14a5873b521ba27aa', which is not the token the harness issued for c05_overlapping ('8e302323f71f3cac0b12276f64216c1b2d7da9ba7c3dd553fb11ae4842f775b6'): a foreign, stale or invented measurement id |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID '8e96284d0728c01d38cacfe66910f09bf19311bef5eb67413eab8cb8d34b3e0e', which is not the token the harness issued for c06_empty ('f01a2c868596dcdbdabee4d7439d4cc526a4de67142fd4c0963ceda2f78266e0'): a foreign, stale or invented measurement id |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID '59200b652f6c3ed53b175532b6a21716519dc87b0732298dde00db655cb73df0', which is not the token the harness issued for c07_single ('f63dbb88cb2e01dbc3054423fab4a742eac52171ee5318e3424f178066f86674'): a foreign, stale or invented measurement id |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID 'afbc7441720313fb9f3bbd43b4b0f04a8954bf8a502b5ce32986db5fa5ec4e1a', which is not the token the harness issued for c08_out_of_bounds ('d47c0fc2b42e912cb944dd6d51545003869767b280c8c55c1be08f8c105e1e73'): a foreign, stale or invented measurement id |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '1c5af6e1e80f933a6e6bdd546cf0bed8aaa1a5b440fdc8265a28a118a7816ed3', which is not the token the harness issued for c09_malformed_import ('a84b61aa7cf76d3f9287cb5943dc0f9855622bb76f6c984f8b22b09780d57117'): a foreign, stale or invented measurement id |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID 'afb28e5bb9e3c12abdadc28d8aaf1916148ab00d6a690998c64a42eddad4c64b', which is not the token the harness issued for c10_raises ('1e958721392c15a2a88fad60d9b04fa3371fdfe25b42b6e3265801ca842eb5c0'): a foreign, stale or invented measurement id |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '6f3312c258fd33c7d113dd69c0d15aaf9616f268a2459d63f5a5d7a1cf37e394', which is not the token the harness issued for c11_non_deterministic ('1f4f8a584d91a3f6abe16292e41900715aa218dd25cf65ef6915d8f25d7c2f6b'): a foreign, stale or invented measurement id |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '963a93d15dfd03729b4ff60f44b0da8fb843243bf05298f215aa3a7b62ba8a4d', which is not the token the harness issued for c12_exit_without_artifacts ('2e0b0e60a2fe52adcdd1dccd0c812da4c66e65845fcbbffa1d52d4d6023e48db'): a foreign, stale or invented measurement id |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID 'a75b98c463a48d1e562521b6d386d6dbb83f5b434b1330b006b855db31a6fc07', which is not the token the harness issued for c13_slow ('547c5f418d0cad32d7356a2eca329f5ce73f71e8e8273832543811160f0e1352'): a foreign, stale or invented measurement id |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '9e060ec75cf6cddc8988c7e6731c33ad4087cb129cc919de1bacd069a9a18348', which is not the token the harness issued for c14_near_zero ('1492cddf6c922a60e69dbf75c7b89f4d1866e75e5e82f653950b76ff761db17c'): a foreign, stale or invented measurement id |

Findings (false-green traps and attempt invariants):

- `MISMATCH_ATTESTATION` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the row echoes OID '577d0f9b068fcb10161b40dff41ffa233971d0f2cce749a565711ecfdf7fc39c', which is not the token the harness issued for c01_good_hex ('6db45d69fe9e7ee8ef50538581db4faa469af2abba91a077b87b2afd1b90f0fb'): a foreign, stale or invented measurement id (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_no_identity — FAIL

Reason: not accepting: 14 x MISSING_IDENTITY -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_no_identity --out report.selftest_no_identity.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/no_identity/v1/EID_r digest = 452bd2c3606e69edf161a6b56f53dc9d41ca39375744648ebc6333226e52322f; declared value = '452bd2c3606e69edf161a6b56f53dc9d41ca39375744648ebc6333226e52322f'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 0/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 14/14 echo a token but attest no identity (MISSING_IDENTITY), 0/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISSING_IDENTITY, c02_baseline_upstream:MISSING_IDENTITY, c03_mirror:MISSING_IDENTITY, c04_near_tie:MISSING_IDENTITY, c05_overlapping:MISSING_IDENTITY, c06_empty:MISSING_IDENTITY, c07_single:MISSING_IDENTITY, c08_out_of_bounds:MISSING_IDENTITY, c09_malformed_import:MISSING_IDENTITY, c10_raises:MISSING_IDENTITY, c11_non_deterministic:MISSING_IDENTITY, c12_exit_without_artifacts:MISSING_IDENTITY, c13_slow:MISSING_IDENTITY, c14_near_zero:MISSING_IDENTITY
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISSING_IDENTITY | MISSING_IDENTITY | the row's numbers agree but the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable |

Findings (false-green traps and attempt invariants):

- `MISSING_IDENTITY` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the row echoes the harness token but attests no evaluator_source_sha256, candidate_sha256, behaviour_digest: the token proves which measurement is claimed, the identity fields are what the runtime says it executed, and omitting them is not acceptable (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISSING_IDENTITY -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_mutant_identity — FAIL

Reason: not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_mutant_identity --out report.selftest_mutant_identity.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/mutant_e_prime_identity/v1/EID_r digest = 4b8ad4e23f83264f0febc93bc62f618d62ea1b26ba81ad89437278bcb2039a62; declared value = '4b8ad4e23f83264f0febc93bc62f618d62ea1b26ba81ad89437278bcb2039a62'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 0/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 0/14 echo a token but attest no identity (MISSING_IDENTITY), 14/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISMATCH_ATTESTATION, c02_baseline_upstream:MISMATCH_ATTESTATION, c03_mirror:MISMATCH_ATTESTATION, c04_near_tie:MISMATCH_ATTESTATION, c05_overlapping:MISMATCH_ATTESTATION, c06_empty:MISMATCH_ATTESTATION, c07_single:MISMATCH_ATTESTATION, c08_out_of_bounds:MISMATCH_ATTESTATION, c09_malformed_import:MISMATCH_ATTESTATION, c10_raises:MISMATCH_ATTESTATION, c11_non_deterministic:MISMATCH_ATTESTATION, c12_exit_without_artifacts:MISMATCH_ATTESTATION, c13_slow:MISMATCH_ATTESTATION, c14_near_zero:MISMATCH_ATTESTATION
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) |

Findings (false-green traps and attempt invariants):

- `MISMATCH_ATTESTATION` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): attested evaluator_source_sha256 c42963b08c46420bd90e6f515322cd3975667f66d5880acdb7260d1820c66796 != the frozen E* 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532: the row asserts a measurement token issued for E* while attesting different evaluator bytes (the 'claim' attack) (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_other_candidate_bytes — FAIL

Reason: not accepting: 2 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_other_candidate_bytes --out report.selftest_other_candidate_bytes.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/other_candidate_bytes/v1/EID_r digest = 24402d318a633695681584cd6b7631e986300322cb5681d1d8e3bd4ea4876bed; declared value = '24402d318a633695681584cd6b7631e986300322cb5681d1d8e3bd4ea4876bed'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 0/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 0/14 echo a token but attest no identity (MISSING_IDENTITY), 2/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 12/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISMATCH_ATTESTATION, c03_mirror:MISMATCH_ATTESTATION
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested candidate_sha256 893d0aa439433d523e2666d62de9b60caacdbab7868134aa83877ee0b03f6fcf != the candidate bytes the harness measured for c01_good_hex (bca4286ed3b15035675f3f2bb2ed0ac8b9e53649f370bf3e5768b5105e3f4a6d): the row was produced from a different file (a swap, or a twin whose value happens to be identical) |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested candidate_sha256 bca4286ed3b15035675f3f2bb2ed0ac8b9e53649f370bf3e5768b5105e3f4a6d != the candidate bytes the harness measured for c03_mirror (893d0aa439433d523e2666d62de9b60caacdbab7868134aa83877ee0b03f6fcf): the row was produced from a different file (a swap, or a twin whose value happens to be identical) |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=invalid, adapter='invalid' |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH_VERDICT | no objective on either side; verdict compared: E*=error, adapter='error' |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `MISMATCH_ATTESTATION` on c01_good_hex, c03_mirror (**fatal**): attested candidate_sha256 893d0aa439433d523e2666d62de9b60caacdbab7868134aa83877ee0b03f6fcf != the candidate bytes the harness measured for c01_good_hex (bca4286ed3b15035675f3f2bb2ed0ac8b9e53649f370bf3e5768b5105e3f4a6d): the row was produced from a different file (a swap, or a twin whose value happens to be identical) (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 2 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_attest_other_measurement — FAIL

Reason: not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_attest_other_measurement --out report.selftest_attest_other_measurement.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/attest_other_measurement/v1/EID_r digest = 007bcaa5a87871457443999fc92c821596af6dc3e6687989fa78f67ee1f3f1f1; declared value = '007bcaa5a87871457443999fc92c821596af6dc3e6687989fa78f67ee1f3f1f1'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `FAIL` measurement-attestation: 0/14 rows carry no harness measurement token (MISSING_ATTESTATION, fail-closed), 0/14 echo a token but attest no identity (MISSING_IDENTITY), 14/14 contradict the harness's own measurement (MISMATCH_ATTESTATION)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 14/14. not accepting: c01_good_hex:MISMATCH_ATTESTATION, c02_baseline_upstream:MISMATCH_ATTESTATION, c03_mirror:MISMATCH_ATTESTATION, c04_near_tie:MISMATCH_ATTESTATION, c05_overlapping:MISMATCH_ATTESTATION, c06_empty:MISMATCH_ATTESTATION, c07_single:MISMATCH_ATTESTATION, c08_out_of_bounds:MISMATCH_ATTESTATION, c09_malformed_import:MISMATCH_ATTESTATION, c10_raises:MISMATCH_ATTESTATION, c11_non_deterministic:MISMATCH_ATTESTATION, c12_exit_without_artifacts:MISMATCH_ATTESTATION, c13_slow:MISMATCH_ATTESTATION, c14_near_zero:MISMATCH_ATTESTATION
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested behaviour_digest f01f10f8229f191da93fe8a74a56c58031576ab402f5b5a8a3c7eb9174129207 != the behaviour digest the harness measured for c01_good_hex (65daffac4768d8d15650baf0827308d7649b1d5cc08513dcccc49f4bb6fef123): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested behaviour_digest 688d4d7e158d052a97b43e766d6faab625031db0313685596bd41b4b3cf1964b != the behaviour digest the harness measured for c02_baseline_upstream (f01f10f8229f191da93fe8a74a56c58031576ab402f5b5a8a3c7eb9174129207): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested behaviour_digest e00d05d50d64675815640a2807aeb1fc14954e7626d9296cdbe542e3845ff7b0 != the behaviour digest the harness measured for c03_mirror (688d4d7e158d052a97b43e766d6faab625031db0313685596bd41b4b3cf1964b): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested behaviour_digest 34fce10674ffe5f2b8b657cc5c713158121fba6f39fddd1053044dcb4c13d547 != the behaviour digest the harness measured for c04_near_tie (e00d05d50d64675815640a2807aeb1fc14954e7626d9296cdbe542e3845ff7b0): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested behaviour_digest f410339c4b28814b4d93a2ba38cd3e4b965fff56efb609201ba2079e80c9f3a9 != the behaviour digest the harness measured for c05_overlapping (34fce10674ffe5f2b8b657cc5c713158121fba6f39fddd1053044dcb4c13d547): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested behaviour_digest 730e177705fc429bb7950a15895930cfb2990f1d038f4775ea629beb9b2ffbf6 != the behaviour digest the harness measured for c06_empty (f410339c4b28814b4d93a2ba38cd3e4b965fff56efb609201ba2079e80c9f3a9): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested behaviour_digest bb939996a2d19e045c397d5555549c46acf0ceddf2d4b4a893e486e1fc045459 != the behaviour digest the harness measured for c07_single (730e177705fc429bb7950a15895930cfb2990f1d038f4775ea629beb9b2ffbf6): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but attested behaviour_digest 97886403db96be5c536ffb43c9bd338dba9e977de370771aa13f74b9c04e639e != the behaviour digest the harness measured for c08_out_of_bounds (bb939996a2d19e045c397d5555549c46acf0ceddf2d4b4a893e486e1fc045459): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested behaviour_digest ba0c067ef8235e3a418f1068deb45f22836b4d558e30e896f0fc96af2741d17c != the behaviour digest the harness measured for c09_malformed_import (97886403db96be5c536ffb43c9bd338dba9e977de370771aa13f74b9c04e639e): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested behaviour_digest 9c8a16d08cbcde7a97212509c60afd1da9251191ff9f7c3303be8f451f193d0e != the behaviour digest the harness measured for c10_raises (ba0c067ef8235e3a418f1068deb45f22836b4d558e30e896f0fc96af2741d17c): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested behaviour_digest 8c03704fadac8a8329f3da135b31edfacb5a04f465e5a7e3aaecc8f01fbc5187 != the behaviour digest the harness measured for c11_non_deterministic (9c8a16d08cbcde7a97212509c60afd1da9251191ff9f7c3303be8f451f193d0e): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested behaviour_digest 442b460585317e9e292888cd3f037a4bd720b46221264f538e8d270be1b06362 != the behaviour digest the harness measured for c12_exit_without_artifacts (8c03704fadac8a8329f3da135b31edfacb5a04f465e5a7e3aaecc8f01fbc5187): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but attested behaviour_digest 3a90f151499cd9e9c4880ed2ae2f34a55319536847a1ff54bd3e9051ff1c00b2 != the behaviour digest the harness measured for c13_slow (442b460585317e9e292888cd3f037a4bd720b46221264f538e8d270be1b06362): the runtime's own measurement does not agree with the reference it claims to have consumed |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but attested behaviour_digest 65daffac4768d8d15650baf0827308d7649b1d5cc08513dcccc49f4bb6fef123 != the behaviour digest the harness measured for c14_near_zero (3a90f151499cd9e9c4880ed2ae2f34a55319536847a1ff54bd3e9051ff1c00b2): the runtime's own measurement does not agree with the reference it claims to have consumed |

Findings (false-green traps and attempt invariants):

- `MISMATCH_ATTESTATION` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): attested behaviour_digest f01f10f8229f191da93fe8a74a56c58031576ab402f5b5a8a3c7eb9174129207 != the behaviour digest the harness measured for c01_good_hex (65daffac4768d8d15650baf0827308d7649b1d5cc08513dcccc49f4bb6fef123): the runtime's own measurement does not agree with the reference it claims to have consumed (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

### selftest_omit_failure_kind — FAIL

Reason: false-green finding(s): FG-FAILURE-KIND-UNDECLARED

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes selftest_omit_failure_kind --out report.selftest_omit_failure_kind.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/deviant/omit_failure_kind/v1/EID_r digest = ba14b920d52a8eef52e44b358df930c9a1faa6c5d97efcd41774556fb322edbd; declared value = 'ba14b920d52a8eef52e44b358df930c9a1faa6c5d97efcd41774556fb322edbd'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `PASS` behaviour-vs-execution-env: 14/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter
- `PASS` measurement-attestation: 14/14 rows echo the harness measurement token and attest the evaluator bytes, candidate bytes and behaviour digest they used (envelope nonce dc5e66e616ee..., run a01-reference-20260921T171004)
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 5/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 5/14. not accepting: c05_overlapping:UNDECLARED_FAILURE_KIND, c06_empty:UNDECLARED_FAILURE_KIND, c07_single:UNDECLARED_FAILURE_KIND, c08_out_of_bounds:UNDECLARED_FAILURE_KIND, c09_malformed_import:UNDECLARED_FAILURE_KIND, c10_raises:UNDECLARED_FAILURE_KIND, c11_non_deterministic:UNDECLARED_FAILURE_KIND, c12_exit_without_artifacts:UNDECLARED_FAILURE_KIND, c13_slow:UNDECLARED_FAILURE_KIND; disagreeing on the measurement surface: c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow
- `FAIL` E-r-failure-kind: 9/9 non-ok candidate(s) declare no failure.kind at all (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow), so their rows do not carry the surface §4.3.5 compares
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |
| c05_overlapping | null | null | - | invalid | invalid_configuration | - | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c06_empty | null | null | - | invalid | invalid_configuration | - | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c07_single | null | null | - | invalid | invalid_configuration | - | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | - | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'invalid' with failure.kind 'invalid_configuration'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c09_malformed_import | null | null | - | error | candidate_import_failed | - | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'candidate_import_failed'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c10_raises | null | null | - | error | candidate_call_raised | - | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'candidate_call_raised'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c11_non_deterministic | null | null | - | error | non_deterministic | - | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'non_deterministic'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | - | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'child_terminated_early'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c13_slow | null | null | - | error | runtime_budget_exceeded | - | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | UNDECLARED_FAILURE_KIND | E* reached 'error' with failure.kind 'runtime_budget_exceeded'; the adapter declared no failure.kind for this candidate, so the row does not carry the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | OK | MATCH | - |

Findings (false-green traps and attempt invariants):

- `FG-FAILURE-KIND-UNDECLARED` on 9 candidates (c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow) (**fatal**): E* verdict 'invalid' / failure.kind 'invalid_configuration', but the adapter's row declares no failure.kind, so the (verdict, failure.kind) surface adapter_contract.md §4.3.5 compares is absent (protocol adapter_contract.md:259 (§4.3.5), plan:577)

Handoff:

- A0.1 verdict: **FAIL** (false-green finding(s): FG-FAILURE-KIND-UNDECLARED)
- A0.1 qualification: state `FAIL`, measured 5/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c14_near_zero'], adapted=none
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

