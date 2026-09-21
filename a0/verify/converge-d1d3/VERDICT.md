# Independent verification — D1 (behaviour/execution split), D3 (measurement token), fixture boundary matrix

Verifier directory: `a0/verify/converge-d1d3/` (read-only on everything else).
No model calls were made. All conclusions below are *verified by running* unless marked
*read from source* or *inferred*.

Artifacts:
- `d1/reference.pinned.json`, `d1/reference.py314.json` — the two reference sweeps
- `d1/state.pinned/outcomes/*`, `d1/state.py314/outcomes/*` — raw E* outcome payloads
- `d1/eplus_mut_own.off.json` — mutant under the checker, `--envelope off`
- `fixture/eplus_d3_*.json` — the six-row boundary matrix re-run
- `fixture/eplus_mut_claim.off.json`, `fixture/eplus_control_py314.off.json`
- `d3/selftest_{env_drift,env_drift_unsanctioned,no_identity,foreign_token,no_token}.json`

## D1

| claim | verdict | evidence |
|---|---|---|
| 3.14 run reports `EXECUTION_ENV_DRIFT`, 14/14 behaviour agreement, no behaviour mismatch | ACCEPTED | `reference --python /usr/bin/python3.14`: `behaviour_reproduced true`, `execution_env.verdict EXECUTION_ENV_DRIFT`, every per-candidate `canonical_digest_matches false`, `problems []` |
| pinned run is `PINNED`, reproduces the table | ACCEPTED | `reference --python .../.venv/bin/python`: `reproduces_frozen_table true`, `PINNED` |
| behaviour digest recomputes by hand from a real payload with `canonical_digest`+`interpreter` removed | ACCEPTED | hand sha256 over `"a0.envelope.behaviour/v1"\0 + canon(payload)` matched the tool 14/14 |
| only `canonical_digest` and `interpreter` are excluded; `evaluator_source_sha256` stays in | ACCEPTED | payload keys minus excluded = `{..., evaluator_source_sha256, ...}`; changing it changes the digest, changing `interpreter` does not |
| interpreter-only mutation does not change behaviour digest; behaviour mutation does | ACCEPTED | by hand |
| a payload whose behaviour differs is still a behaviour mismatch | ACCEPTED | mutant `E'` `--envelope off` → FAIL 14× `MISMATCH_DIGEST` |
| sanctioned-set membership (3.14.7 equivalent) is a measurement | ACCEPTED | E*'s digest recomputed on the pinned payload with the 3.14.7 interpreter block == the 3.14.7 run's digest 14/14; behaviour payload bytes identical 14/14 |

## D3

| claim | verdict | evidence |
|---|---|---|
| token is harness-issued, recomputes from its declared binding | ACCEPTED | independent OID recompute matched 14/14; binding `candidate_sha256` == manifest, `evaluator_source_sha256` == E_STAR.json (and recomputed from bytes), `eid_star` == 664115e0…9328 |
| per-candidate, not reusable | ACCEPTED | 14 distinct OIDs |
| `MISSING_ATTESTATION` / `MISMATCH_ATTESTATION` / `MISSING_IDENTITY` / `MISMATCH_EXECUTION_ENV` appear and are non-accepting | ACCEPTED | deviant modes driven through the real runner: `no_token`, `foreign_token`, `no_identity`, `env_drift_unsanctioned` → 14/14 of the named code, 0 accepting rows each; sanctioned `env_drift` → PASS `EXECUTION_ENV_DRIFT` 14/14 |
| SimpleLoop echoes the *harness* token, not one it minted | ACCEPTED | `report.json` simpleloop rows: `oid_echoed` == the envelope's OID 14/14; adapter reads `A0_ENVELOPE`/`--envelope` (`cli.py:92`, `conformance.py:53`) |

## Fixture boundary matrix

| row | verdict (reproduced) |
|---|---|
| `eplus_d3_control` | PASS 14/14, attestation ok |
| `eplus_d3_claim_measured` | FAIL, 14× `MISMATCH_ATTESTATION` (numbers agree 14/14) |
| `eplus_d3_twin_measured` | FAIL, 14× `MISMATCH_ATTESTATION` |
| `eplus_d3_fulltheta_measured` | FAIL, 14× `MISMATCH_ATTESTATION` |
| `eplus_d3_claim_copy` | **PASS 14/14** (executes `E'`) |
| `eplus_d3_fulltheta_copy` | **PASS 14/14** (executes `E''`) |

All six row-for-row identical to the author's `out/conformance.envelope_required_attested/`.

## Four-runtime A0.1 (from `report.json`)

simpleloop PASS (14/14 measured); kapso/eve/loreley FAIL, 14× `MISSING_ATTESTATION`,
`E-r-equals-E-star` detail: "agreeing on the measurement surface alone: 14/14", zero rows with
non-zero delta. EvE `qualification.a0_1 = {state FAIL, measured 5, adapted 9, total 14}`.
`verdicts.r_1_a0_1_only = ["simpleloop"]`.

## Falsification attempts (cheaper closure of the copying lane)

1. **"Withhold the binding from the lane, publish only the OID."** FAILS as a closure: the value
   the checker requires the lane to reproduce is derivable from the *public* frozen table.
   `E_STAR.json:candidates[].outcome` is the full E* payload; its behaviour digest recomputes to
   exactly the envelope binding value. So the copy lane (and any lane) needs the envelope only
   for the per-run OID.
2. **"Hash the evaluator the row says it ran and compare to the digest it attests."** Fails the
   copy lane as constructed (its row names `e_prime/e_star.py`, digest `cfaa6194…`, while attesting
   `5ae97a…`), but is defeated by omitting/forging the path → cost, not closure.
3. **"Require the row's Outcome and recompute the digest."** Forgeable: the lane can submit E*'s
   payload (public in `E_STAR.json`), which is indistinguishable.

Conclusion: no cheaper *robust* check was found; the fixture's framing (residual is harness-owned
measurement) stands.

## Overstatements / defects (not fixed)

1. `conformance.py:row_attestation` docstring claims identity is "read only from an attestation-shaped
   container, never from the row's top level" — the code searches `containers + [rec]`.
   Verified by calling `row_attestation` on a top-level-only row: `oid_present`/`identity_present`
   both True.
2. `run_envelope_probe.sh` runs only 4 of the 6 rows REPORT.md §2.4 quotes (`fulltheta` rows have no
   command in the script); the "Re-run everything" step 3b does not regenerate the matrix it is cited for.
3. The runner reused a cached envelope (nonce `d993b292…`, run `…T171439`) for runs at 17:26 — the
   envelope is per *sweep*, not per invocation.
4. `E-r-equals-E-star` folds the attestation into its `ok`, so it reads `False` for rows whose numbers
   agree 14/14 (only the detail text disambiguates).
