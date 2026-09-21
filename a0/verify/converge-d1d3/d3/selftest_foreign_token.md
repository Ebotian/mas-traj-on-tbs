# A0.1 cross-adapter conformance report

Generated 2026-09-21T17:28:07+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own claim about its A0.1 outcome is recorded only under a key named `__untrusted` (see `adapter_claim__untrusted` / `adapter_self_declaration__untrusted`), so it can never be read as a verdict.

## Verdicts

| runtime | A0.1 | measured / 14 | adapted (declared, NOT measured) | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|---|---|
| selftest_foreign_token | FAIL | 14/14 | 0/14 | 0/14 (14 MISMATCH_ATTESTATION) | MISMATCH_ATTESTATION | not judged here | not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the byte... |

A0.1-only screen: `r_1_a0_1_only = []` (n_pass=0, n_partial=0, n_fail=1, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

PARTIAL A0.1 (every row agrees, but at least one only on adapter-supplied semantics), deliberately excluded from the screen set: `r_1_a0_1_partial = []`.

`|R_1| >= 1` is a CANDIDATE SCREEN over runtimes and is a different object from per-runtime qualification. The screen asks whether the study may continue (at least one substrate survives A0); qualification asks whether a given runtime's A0.1 answer is measured or merely adapted. `r_1_a0_1_only` lists runtimes whose A0.1 is PASS (every row measured) and `r_1_a0_1_partial` lists runtimes whose A0.1 is PARTIAL (some rows accepted only on adapter-supplied semantics). A PARTIAL runtime is deliberately NOT in `r_1_a0_1_only`, so a partial result can never be diluted by siblings that passed. Per-runtime eligibility for A1 is declared separately and explicitly by the `Eligible(r)` predicate in `a0/qualification/qualification.json` (see `a0/qualification/QUALIFICATION.md`); the screen can pass while no runtime is Eligible().

## Measurement envelope (D3) and declared execution set (D1)

Envelope mode **required** (required = True): the harness issues one OID-style measurement token per member of C* from its own E* sweep, and every adapter row must echo it and attest the evaluator bytes, candidate bytes and behaviour digest it used; a row that omits them is non-accepting (external review D3)

The harness issued `14` measurement tokens into its own state root `/home/ebt/rsi-dev/a0/conformance/out/envelope/measurement_tokens.a01-reference-20260921T171439.json` (sha256 `acb67873838a78b3...`, nonce `d993b2924eba1a6fe1b610d506a54ff9`, run `a01-reference-20260921T171439`), handed to every adapter as `{"env": "A0_ENVELOPE=<path>", "cli_flag": "--envelope (optional)"}`.

The harness's own sweep ran under {"implementation": "cpython", "version": "3.12.11"} (classification `PINNED` against the declared set).

Declared allowed execution set: pinned `{"implementation": "cpython", "version": "3.12.11", "interpreter_path": "a0/tasks/circle-packing/.venv/bin/python", "source": "a0/tasks/circle-packing/E_STAR.json:evaluator.interpreter (the environment the frozen table was measured under)", "meaning": "PINNED = the execution environment E_STAR.json's per-candidate canonical_digest values are bound to. The reference sweep and the measurement tokens are issued under it."}`, sanctioned `[{"implementation": "cpython", "version": "3.12.11"}, {"implementation": "cpython", "version": "3.14.7"}]` (`/home/ebt/rsi-dev/a0/envelope/execution-set.json`).

> UNDECIDED and documented, not decided: folding this allowed execution set into EID*'s Config would make broadening it a re-freeze of EID* = 664115e0...9328. See a0/envelope/execution-set.json:coupling_question_UNDECIDED and a0/envelope/README.md.

| runtime | attestation required | rows attesting | MISSING_ATTESTATION | MISSING_IDENTITY | MISMATCH_ATTESTATION | EXECUTION_ENV_DRIFT | MISMATCH_EXECUTION_ENV |
|---|---|---|---|---|---|---|---|
| selftest_foreign_token | True | 0 | 0 | 0 | 14 | 0 | 0 |

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
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '49addc23aa7faced3d734ce457e0b5492ba42ff25842234b59d8b4652b70c1ee', which is not the token the harness issued for c01_good_hex ('4eff82345db02191ce5a85c73fda96b168940aa10ee70641c3285ab300f0ae1b'): a foreign, stale or invented measurement id |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '1b4becb1db5079812071a1169a1c28540dc56bf36c43c5b7508059d9869dd7b7', which is not the token the harness issued for c02_baseline_upstream ('c1cf69e267642fca58b2aef5365bcf523e565df5229afb513658f9483688971b'): a foreign, stale or invented measurement id |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID 'fc5ee1f1ae885e6a61fef75b76e441209e1d431185138fb337d2504af8080d7a', which is not the token the harness issued for c03_mirror ('84dd00145eeb67f0348e1fb483b4adab08178b9461b609b54d80f073aa7898e3'): a foreign, stale or invented measurement id |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '696f9102d781d651ff695d2522df6b65c0c567b6cad9f8d87a6601f9df13fe64', which is not the token the harness issued for c04_near_tie ('d9a8a21a8de970d6a943034992e4027672068e074ba58dd58612137f19370e3c'): a foreign, stale or invented measurement id |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID 'b44e6aa6960502dba76a6180b306f12e45a1df1b293fc764ff721fe2bb99cbe9', which is not the token the harness issued for c05_overlapping ('95bfa21ab01ea0b0c1eecce15ef0eaabab8c4cadc7a6017e35dce3d4322f2595'): a foreign, stale or invented measurement id |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID 'c360614456cc3e584d27645fb56a4d07a7abce43b74f8b2ae53f3a8f78349df5', which is not the token the harness issued for c06_empty ('0e86e49b53db1cbfa6aa100fda0162c59b9066dd100e38130acaadf8b0b9421f'): a foreign, stale or invented measurement id |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID 'bde1537af90ea268bb7c056885efdba39d77718195db0e6e85885c7d324b950c', which is not the token the harness issued for c07_single ('e3bfb9f60186115f22fbf158c1510d36ebb3e40e1424722406a5aa7a02b12550'): a foreign, stale or invented measurement id |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=invalid, adapter='invalid'; the row's numbers agree but the row echoes OID 'b51cd693d24d77810042ee4745b487819b8a1f00424b93ef7bde69289d52734d', which is not the token the harness issued for c08_out_of_bounds ('04721256d59d1865b4dcf193e923d7164bec953afb50cd9c0b741feddbe71d58'): a foreign, stale or invented measurement id |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '27e44cce997d9ea88fb3da7760e74d62a47df220c3754fe4ac1114937e61cb79', which is not the token the harness issued for c09_malformed_import ('77923d0618a420c4e3c78c51104b4f5fa5e646e041d7cf9d3cea69be808109d2'): a foreign, stale or invented measurement id |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '75978b0dfbd140ab0697f6c0aa8aa52b81c5ed6c76ecd5296de5191b54ea8783', which is not the token the harness issued for c10_raises ('168a648d8758cd6ea21ade7f508657b1abdf5aa35e876a761d40444eedcfe0b8'): a foreign, stale or invented measurement id |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '59cd617f325cbdd9a6399c21f41be8b4817264d1778f2ea5265300a6844624ac', which is not the token the harness issued for c11_non_deterministic ('7057c6d38e77e4b6a5eb6f3d64701498d6ae16c89b444898e11f23bfb429453c'): a foreign, stale or invented measurement id |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID 'd3022aa49f600a470e5ec0b6f0265146c2adae6af725653a7c430da687f92a61', which is not the token the harness issued for c12_exit_without_artifacts ('4c1fb1269e8ae38ce209dbffa0a0272f4b5ca0269a1888275746c63c579fbb48'): a foreign, stale or invented measurement id |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | no objective on either side; verdict compared: E*=error, adapter='error'; the row's numbers agree but the row echoes OID '49e3c24629b0493b1f58cddc7402f8c91bc2b589e67b8fd39ed522dacd5a32a8', which is not the token the harness issued for c13_slow ('0f3d7fc473519bfb09b20cf8a467d2bf8d12b7280f104bf2d2e50db40d399a5e'): a foreign, stale or invented measurement id |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | agrees (interpreter_substitution) | PINNED {"implementation": "cpython", "version": "3.12.11"} | MISMATCH_ATTESTATION | MISMATCH_ATTESTATION | the row's numbers agree but the row echoes OID '9791ec7e2545fdcbe913d01d4a6db3ed179b4055d7ec74b4ba8c4cb06c846d4d', which is not the token the harness issued for c14_near_zero ('2d41f79d82fef9eeb3741f12afef557c6c4275722ca1109842d7c324070a4244'): a foreign, stale or invented measurement id |

Findings (false-green traps and attempt invariants):

- `MISMATCH_ATTESTATION` on 14 candidates (c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero) (**fatal**): the row echoes OID '49addc23aa7faced3d734ce457e0b5492ba42ff25842234b59d8b4652b70c1ee', which is not the token the harness issued for c01_good_hex ('4eff82345db02191ce5a85c73fda96b168940aa10ee70641c3285ab300f0ae1b'): a foreign, stale or invented measurement id (protocol external review D3 (measurement token, fail-closed on omission))

Handoff:

- A0.1 verdict: **FAIL** (not accepting: 14 x MISMATCH_ATTESTATION -- the numbers agree on 14/14 rows, but an A0.1 row must also echo the harness measurement token and attest the bytes it executed (external review D3, fail-closed on omission))
- A0.1 qualification: state `FAIL`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
- A0.2 verdict: not judged here (owned by `a0/acceptance`); this runner only reports whether the adapter can carry the identity and the numbers
- EID_r -> EID* : eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- traces: none reported
- FailureStage counts: none reported
- adapter revision covered by this verdict: digest `None` over None source file(s), newest mtime None, unchanged during the run: True
- FailureStage accounting vs the frozen `adapter_contract.md` §5.3 map over C*: declared null (comparable=False, matches_frozen_map=None); expected {"none": 5, "verify_failed": 5, "resolve_failed": 1, "evaluator_failed": 2, "timeout": 1}. the adapter declared no FailureStage counts, so nothing could be compared

## Controls

No control row in this report. Run `python3 selftest.py` to exercise the checker against deliberately deviant adapters (see `selftest_report.json`).

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

