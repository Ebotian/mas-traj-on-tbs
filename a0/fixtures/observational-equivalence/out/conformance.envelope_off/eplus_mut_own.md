# A0.1 cross-adapter conformance report

Generated 2026-09-21T17:20:01+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own claim about its A0.1 outcome is recorded only under a key named `__untrusted` (see `adapter_claim__untrusted` / `adapter_self_declaration__untrusted`), so it can never be read as a verdict.

## Verdicts

| runtime | A0.1 | measured / 14 | adapted (declared, NOT measured) | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|---|---|
| eplus_mut_own | FAIL | 0/14 | 0/14 | 0/14 (14 MISMATCH_DIGEST) | - | not judged here | E_r(c) disagrees with E*(c): 14 x MISMATCH_DIGEST |

A0.1-only screen: `r_1_a0_1_only = []` (n_pass=0, n_partial=0, n_fail=1, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

PARTIAL A0.1 (every row agrees, but at least one only on adapter-supplied semantics), deliberately excluded from the screen set: `r_1_a0_1_partial = []`.

`|R_1| >= 1` is a CANDIDATE SCREEN over runtimes and is a different object from per-runtime qualification. The screen asks whether the study may continue (at least one substrate survives A0); qualification asks whether a given runtime's A0.1 answer is measured or merely adapted. `r_1_a0_1_only` lists runtimes whose A0.1 is PASS (every row measured) and `r_1_a0_1_partial` lists runtimes whose A0.1 is PARTIAL (some rows accepted only on adapter-supplied semantics). A PARTIAL runtime is deliberately NOT in `r_1_a0_1_only`, so a partial result can never be diluted by siblings that passed. Per-runtime eligibility for A1 is declared separately and explicitly by the `Eligible(r)` predicate in `a0/qualification/qualification.json` (see `a0/qualification/QUALIFICATION.md`); the screen can pass while no runtime is Eligible().

## Measurement envelope (D3) and declared execution set (D1)

Envelope mode **off** (required = False): --envelope off was requested: the token requirement is off, so this run's acceptances are exploratory and do not carry the A0.1 measurement-attestation evidence

The harness issued `0` measurement tokens into its own state root `/home/ebt/rsi-dev/a0/conformance/out/envelope/measurement_tokens.a01-reference-20260921T171439.json` (sha256 `acb67873838a78b3...`, nonce `None`, run `None`), handed to every adapter as `{"env": "A0_ENVELOPE=<path>", "cli_flag": "--envelope (optional)"}`.

The harness's own sweep ran under null (classification `None` against the declared set).

Declared allowed execution set: pinned `{"implementation": "cpython", "version": "3.12.11", "interpreter_path": "a0/tasks/circle-packing/.venv/bin/python", "source": "a0/tasks/circle-packing/E_STAR.json:evaluator.interpreter (the environment the frozen table was measured under)", "meaning": "PINNED = the execution environment E_STAR.json's per-candidate canonical_digest values are bound to. The reference sweep and the measurement tokens are issued under it."}`, sanctioned `[{"implementation": "cpython", "version": "3.12.11"}, {"implementation": "cpython", "version": "3.14.7"}]` (`/home/ebt/rsi-dev/a0/envelope/execution-set.json`).

> UNDECIDED and documented, not decided: folding this allowed execution set into EID*'s Config would make broadening it a re-freeze of EID* = 664115e0...9328. See a0/envelope/execution-set.json:coupling_question_UNDECIDED and a0/envelope/README.md.

| runtime | attestation required | rows attesting | MISSING_ATTESTATION | MISSING_IDENTITY | MISMATCH_ATTESTATION | EXECUTION_ENV_DRIFT | MISMATCH_EXECUTION_ENV |
|---|---|---|---|---|---|---|---|
| eplus_mut_own | False | 0 | 0 | 0 | 0 | 0 | 0 |

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

### eplus_mut_own — FAIL

Reason: E_r(c) disagrees with E*(c): 14 x MISMATCH_DIGEST

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes eplus_mut_own --out report.eplus_mut_own.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own claim `None` (recorded under `adapter_claim__untrusted`, never a verdict, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/e_plus/v1/EID_r digest = bc13e551a99b0e213fa78a64c658d886bb6c16449b179e72c21dcf253b9a6a7b; declared value = 'bc13e551a99b0e213fa78a64c658d886bb6c16449b179e72c21dcf253b9a6a7b'
- `PASS` theta-E-identical: adapter declares theta_E = {"fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "seed": 1337, "timeout_s": 120.0}
- `PASS` E-star-manifest-echo: no E* manifest echo found in the adapter's own evidence, so this independent confirmation is unavailable (not a failure: it is a bonus channel)
- `PASS` F-r-frozen: adapter declares F_r spec_hash='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'; frozen first-round F_r hash is '1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0' (plan:528)
- `FAIL` behaviour-vs-execution-env: 0/14 rows agree with E*'s behaviour payload (the Outcome minus `canonical_digest` and `interpreter`), 14/14 rows declared a digest surface to compare; execution environment: every row ran under the pinned interpreter; 14 row(s) disagree on behaviour itself: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` measurement-attestation: no measurement envelope was issued for this run (--envelope off): the token requirement is off, so this run's acceptances are exploratory -- a row's identity material is still recorded, but nothing required it to be there
- `PASS` candidate-coverage: adapter produced usable rows for 14/14 members of C*
- `FAIL` E-r-equals-E-star: 0/14 candidates are ACCEPTING (their row agrees with E*(c) within epsilon=1e-09 or compares equal as a verdict, AND carries the harness attestation); agreeing on the measurement surface alone: 0/14. not accepting: c01_good_hex:MISMATCH_DIGEST, c02_baseline_upstream:MISMATCH_DIGEST, c03_mirror:MISMATCH_DIGEST, c04_near_tie:MISMATCH_DIGEST, c05_overlapping:MISMATCH_DIGEST, c06_empty:MISMATCH_DIGEST, c07_single:MISMATCH_DIGEST, c08_out_of_bounds:MISMATCH_DIGEST, c09_malformed_import:MISMATCH_DIGEST, c10_raises:MISMATCH_DIGEST, c11_non_deterministic:MISMATCH_DIGEST, c12_exit_without_artifacts:MISMATCH_DIGEST, c13_slow:MISMATCH_DIGEST, c14_near_zero:MISMATCH_DIGEST; disagreeing on the measurement surface: c01_good_hex, c02_baseline_upstream, c03_mirror, c04_near_tie, c05_overlapping, c06_empty, c07_single, c08_out_of_bounds, c09_malformed_import, c10_raises, c11_non_deterministic, c12_exit_without_artifacts, c13_slow, c14_near_zero
- `PASS` E-r-failure-kind: 9/9 candidate(s) whose E* verdict is not `ok` declare a failure.kind, and every declared kind matches E*'s
- `PASS` evidence-fresh-or-declared: every compared row is a fresh measurement (evaluator_evidence.status == ok)

| candidate | E*(c) | E_r(c) | delta | E* verdict | E* failure.kind | E_r failure.kind | E_r status | evidence | behaviour | execution env | attestation | verdict | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_good_hex | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 831d818c891b75257fc91d2a3aa5453b472c26157c6660d9c469e51a2d8d3ce0 vs E*'s 1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8) |
| c02_baseline_upstream | 0.25 | 0.25 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 3bf1f7c311650f46ff0e74622a4484e1eada1522f71f1fba765f51f98516ced3 vs E*'s b4ddfc46f1c745ae11828b80d7c67e460953ee8bd854d94ed4a94ccaea0092fc) |
| c03_mirror | 2.4519205208433132 | 2.4519205208433132 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest ba4155fc9a78d9c3c35e0d89bc8157b4d221caffdbd79ad68288ace911c43eed vs E*'s c0b8113c22d5edb385491972b41f62d914660ae0810a969ff53eb078f3bb78aa) |
| c04_near_tie | 2.451820520843313 | 2.451820520843313 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 6653d66662c749c923e3bb1fee04c70b2e2570fdfa94bb6ad50617bb7db6a1c3 vs E*'s f2d0d25dcc05a608a0728ffb685a2c459c50aebfa17d3d616c2673a8270caba3) |
| c05_overlapping | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 06d41d52c7eb2c8a3412a5e0de2a56e2919ffd61539993eb2c6ee37ce55c6633 vs E*'s 6bcd9a1659598d000b894be368603c66ecee0195964fd489f2ab202b5f9a0573) |
| c06_empty | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 46769871eb044b9417c6f7bf37b6ddcbdae50582f356b226a6aa1bd42c5ce343 vs E*'s 319effe699c1d7e1c789fa2eead12663612fd71b889e30b47d79f92964619fc2) |
| c07_single | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 18bac026844cc866290f9b89192509fc3b37bbd383021ebafb65f526e74cf824 vs E*'s a58c002383f8e1278ca36a10309582ddfd0e911f3ebb7090f0f9c099ca69d743) |
| c08_out_of_bounds | null | null | - | invalid | invalid_configuration | invalid_configuration | invalid | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 21ba5fd0051a42e612f7bc962e539ed35c7c491035072aadc016802ccaaff588 vs E*'s 1e3f26a7c94f1f5332a79d8eb473340952331b3d59d70025ad409a2a93350376) |
| c09_malformed_import | null | null | - | error | candidate_import_failed | candidate_import_failed | error | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest af1a539ccc74ce317dc5c6415ba9bb5ab6914337b3ebb38850754761e856bf83 vs E*'s 98e37580fd92861a30102ebd6bce90fc26c265d6dc42782cf10428e1fea61bb9) |
| c10_raises | null | null | - | error | candidate_call_raised | candidate_call_raised | error | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 530c7a0567d8210f854456c9389e34cc11ba6d8e5edc4dbc22427cae234457cb vs E*'s 0d45d41307b93e9b88806e31564b03991881fa2cb3e00cb13509a55e615565b3) |
| c11_non_deterministic | null | null | - | error | non_deterministic | non_deterministic | error | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest e6633feb08442e9ba158bc76b929c58a5d1490e1701cc5344ee0b98f14a92555 vs E*'s 2800cb425b2cdb04a4a2ed358009eb8c54a68d00102bc96e8a21fca61e515fd8) |
| c12_exit_without_artifacts | null | null | - | error | child_terminated_early | child_terminated_early | error | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 2b29ddf42c9b6bea35db4199da89c40e40cdf35e0f92a885e8821e3384426c35 vs E*'s cb4d9bcc4712dcc4e670f7feea3ccb72a60aa7fb5c09d2a3382b699a894f9a64) |
| c13_slow | null | null | - | error | runtime_budget_exceeded | runtime_budget_exceeded | error | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 44f7eb83d5228fa2bca4a76d5955aa433df439170c4509535c932765b5bdbf62 vs E*'s 710d01d9475cfca4bd33479d4279d61b632b801a7e15e173fde7a2a41e237181) |
| c14_near_zero | 2.6e-05 | 2.6e-05 | 0.000e+00 | ok | - | - | ok | ok | DIFFERS (interpreter_substitution) | MISMATCH_DIGEST | ENVELOPE_NOT_REQUIRED | MISMATCH_DIGEST | behaviour mismatch: the row's canonical_digest matches the frozen payload under NO interpreter in the declared allowed execution set [{'implementation': 'cpython', 'version': '3.12.11'}, {'implementation': 'cpython', 'version': '3.14.7'}]: the behaviour payload itself differs (canonical_digest 882f2b2bd65f9d548410cb611c3ab825b3ab0151c1f0fc3f5622e9a1b3ed1538 vs E*'s cabca3563053dc7d04de0553a8bd62a9980d2ee9fdb0943e64599521d78b9cfe) |

Handoff:

- A0.1 verdict: **FAIL** (E_r(c) disagrees with E*(c): 14 x MISMATCH_DIGEST)
- A0.1 qualification: state `FAIL`, measured 0/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=[], adapted=none
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

