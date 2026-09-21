# A0.1 cross-adapter conformance report

Generated 2026-09-21T15:15:56+0800 by `a0/conformance/conformance.py run`.

Frozen coordinates: `E* = tasks/circle-packing/e_star.py` (`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`), `EID* document = /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json [canonical]` (sha256 `50af0aeb42dbc5a7...`), `C* = /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json` (sha256 `8d9b953877beb1b0...`), `theta_E = {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5, "runtime_budget_ms": 250.0, "timeout_s": 120.0}`, `epsilon = 1e-09`, `F_r: F_r(E*) = scalar(E*) = outcome.objective.sum_radii, maximize (plan:528)`.

Protocol: `plan:513-519` (the acceptance formula), `plan:490` (candidate screen, `|R_1| >= 1`), `plan:551-552` (the two false-green traps). The runner compares the adapter's numbers against the frozen table `E_STAR.json` itself; an adapter's own verdict is recorded but never trusted.

## Verdicts

| runtime | A0.1 | measured / 14 | adapted (declared, NOT measured) | acceptable / 14 | false-green findings | A0.2 (other workstream) | reason |
|---|---|---|---|---|---|---|---|
| eplus_mut_echo | PENDING | - | - | 0/14 | - | not judged here | adapter is present but produced no usable A0.1 output: conformance exit 2; run exit 2; stderr tail: ["python3: can't open file '/home/ebt/rsi-dev/a0/conforma... |

A0.1-only screen: `r_1_a0_1_only = []` (n_pass=0, n_partial=0, n_fail=0, n_pending=1, n_blocked=0). |R_1| >= 1 suffices to continue (plan:490); a0_1_only is not R_1, which also needs A0.2

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

### eplus_mut_echo — PENDING

Reason: adapter is present but produced no usable A0.1 output: conformance exit 2; run exit 2; stderr tail: ["python3: can't open file '/home/ebt/rsi-dev/a0/conformance/adapters/e_plus_adapter.py': [Errno 2] No such file or directory"]

Re-run this runtime with: `cd /home/ebt/rsi-dev/a0/conformance && python3 conformance.py run --runtimes eplus_mut_echo --out report.eplus_mut_echo.json`

No rows: the adapter was not driven (nothing was run for this runtime).

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

