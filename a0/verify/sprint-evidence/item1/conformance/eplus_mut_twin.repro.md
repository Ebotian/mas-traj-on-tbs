# A0.1 cross-adapter conformance report

Generated 2026-09-21T16:10:27+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own verdict is recorded but never trusted.

## Verdicts

| runtime | A0.1 | measured / 14 | adapted (declared, NOT measured) | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|---|---|
| eplus_mut_twin | PASS (14/14 measured) | 14/14 | 0/14 | 14/14 | - | not judged here | all checks passed |

A0.1-only screen: `r_1_a0_1_only = ['eplus_mut_twin']` (n_pass=1, n_partial=0, n_fail=0, n_pending=0, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

PARTIAL A0.1 (every row agrees, but at least one only on adapter-supplied semantics), deliberately excluded from the screen set: `r_1_a0_1_partial = []`.

`|R_1| >= 1` is a CANDIDATE SCREEN over runtimes and is a different object from per-runtime qualification. The screen asks whether the study may continue (at least one substrate survives A0); qualification asks whether a given runtime's A0.1 answer is measured or merely adapted. `r_1_a0_1_only` lists runtimes whose A0.1 is PASS (every row measured) and `r_1_a0_1_partial` lists runtimes whose A0.1 is PARTIAL (some rows accepted only on adapter-supplied semantics). A PARTIAL runtime is deliberately NOT in `r_1_a0_1_only`, so a partial result can never be diluted by siblings that passed. Per-runtime eligibility for A1 is declared separately and explicitly by the `Eligible(r)` predicate in `a0/qualification/qualification.json` (see `a0/qualification/QUALIFICATION.md`); the screen can pass while no runtime is Eligible().

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

Row verdicts: `MATCH` (number agrees within epsilon), `MATCH_VERDICT` (no number on either side, verdicts compared), `SYNTHETIC_DECLARED` (the runtime's lane returned a declared synthetic failure where E* has no number -- acceptable, but its 0.0 is never a measurement, and a runtime with such a row is `PARTIAL`, not `PASS`), `FALSE_GREEN_*` (a number where none exists, or a non-fresh number), `MISMATCH_*`, `MISSING`.

### eplus_mut_twin — PASS (14/14 measured)

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes eplus_mut_twin --out report.eplus_mut_twin.json`

Adapter output: schema `a0.adapter.conformance/v1`, rows from `top level`, adapter's own verdict `None` (recorded, never trusted), numbers read from `adapter conformance subcommand`.

- `PASS` EID-star-verbatim: adapter carried eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'; expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328' (verbatim copy required)
- `PASS` EID-r-derives-from-EID-star: eid_r.derives_from_eid_star='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
- `PASS` EID-r-declaration-present: native_scheme='none' mapping_mode='adapter_declared_injection' recomputable=True
- `PASS` EID-r-recomputes: recomputed a0/fixture/e_plus/v1/EID_r digest = 898cd36345fcb383d9b55612d819e9c44fbf2e001fdced43d831c1d67e08a064; declared value = '898cd36345fcb383d9b55612d819e9c44fbf2e001fdced43d831c1d67e08a064'
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

- A0.1 verdict: **PASS (14/14 measured)**
- A0.1 qualification: state `PASS`, measured 14/14 by the runtime's own evaluator interface, adapted 0/14 on adapter-supplied semantics (never used as a measurement): measured=['c01_good_hex', 'c02_baseline_upstream', 'c03_mirror', 'c04_near_tie', 'c05_overlapping', 'c06_empty', 'c07_single', 'c08_out_of_bounds', 'c09_malformed_import', 'c10_raises', 'c11_non_deterministic', 'c12_exit_without_artifacts', 'c13_slow', 'c14_near_zero'], adapted=none
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

