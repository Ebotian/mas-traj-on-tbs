# `a0/fixtures/observational-equivalence/` — behavioural conformance is not enough

The fixture behind the external review's point 6: **for any finite `C*` there is an evaluator
`E' ≠ E*` with `E'(c) = E*(c)` for every `c ∈ C*`**, so no amount of extra candidates can make
A0.1 pin the implementation. This directory builds one such `E'`, runs it through the study's
own A0.1 checker and through execution attestation, and enumerates what neither mechanism sees.

Everything here is a **fixture**, not a runtime. Nothing outside this directory is written
except the disclosed runner side effects listed at the bottom.

## Headline

Three checker revisions have now been measured. Under the **current** one (D1+D3, `e40d008d…78ce`,
`a0/envelope/`), every one of my seven rows changes: the four passes become
`MISSING_ATTESTATION` failures, and only the row that was already failing on behaviour
(`eplus_mut_own`) keeps its verdict. Rows marked † are the ones that used to be *silent* passes.

| row | what ran | checker verdict |
|---|---|---|
| `eplus_control` | real `E*`, identity reported honestly | PASS → **FAIL** 14× `MISSING_ATTESTATION` (D3 is fail-closed on omission) |
| `eplus_mut_own` | mutant `E'`, reports its own identity | FAIL — 14× `MISMATCH_DIGEST`, values `delta = 0.0` (unchanged) |
| † `eplus_mut_claim` | mutant `E'` claiming `E*`'s identity material | PASS → **FAIL** 14× `MISSING_ATTESTATION` |
| † `eplus_mut_omit` | mutant `E'`, no identity fields at all | PASS → **FAIL** 14× `MISSING_ATTESTATION` |
| † `eplus_mut_twin` | mutant `E'`, c01 answered from the c03 file | PASS → **FAIL** 14× `MISSING_ATTESTATION` |
| `eplus_mut_echo` | mutant `E'` claiming `E*` + echoing its own manifest | FAIL → **FAIL** 14× `MISSING_ATTESTATION` |
| `eplus_control_py314` | real `E*` under python 3.14.7 instead of the pinned 3.12.11 | FAIL 14× `MISMATCH_DIGEST` → **PASS** 14× `EXECUTION_ENV_DRIFT` (D1 fixes the false red) → **FAIL** `MISSING_ATTESTATION` with the envelope required |

With the token wired (`--attestation measured`), a lane that echoes the harness token **and attests
what it really executed** is judged properly: the real `E*` PASSes, while `E'` (evaluator dimension),
the sibling `E''` and the c01←c03 twin (candidate dimension) each FAIL 14× `MISMATCH_ATTESTATION`.
What the token does **not** close is a lane that copies the token's own binding values into its own
attestation: `eplus_d3_claim_copy` and `eplus_d3_fulltheta_copy` PASS 14/14 while executing `E'`/`E''`
— the "consistent liar" `a0/envelope/README.md` §5 names, and this fixture's R5. Details and the
per-row matrix: [`REPORT.md`](REPORT.md) §2.4 and §5.1.

Execution attestation, same mutant: `a0/attestation/`'s own verifier returns
`Q3_realization NOT_REALIZED` (exit 3) while its control on the real `E*` returns `REALIZED`
(exit 0). Full detail and the residual classes: [`REPORT.md`](REPORT.md).

Earlier revisions, for the record: the seven rows were reproduced **row for row** across the field
rename (`adapter_declared_verdict` → `adapter_claim__untrusted`, no verdict logic):
`out/conformance/reprocheck.json`, `identical: True`. And the cheaper check the verifier proposed —
`E_STAR.json`'s frozen per-candidate `fast_tier` row, which the checker never reads — *does* catch
`E'` (c05: frozen `ok`/`2.4519205208433132` vs `E'` `invalid`) but not the sibling mutant
`e_prime_fulltheta` (M2+M3 only), which agrees with `E*` on **both** theta classes and differs from
it on `C*` only in its source digest: `out/fast_tier_check.json`, `REPORT.md` §5.1.

## Files

| path | what it is |
|---|---|
| `e_prime/e_star.py` | the mutant `E'` — `E*` with three semantic deviations (M1 seed-blind audit sample, M2 strict geometry tolerances, M3 audit-scope margin). `e_star_child.py` is `E*`'s, unchanged |
| `e_prime_fulltheta/e_star.py` | sibling mutant `E''` — M2+M3 only, M1 reverted. Agrees with `E*` on **both** frozen theta classes (full and fast) and differs on `C*` only in its source digest; used in `REPORT.md` §5.1 |
| `adapters/e_plus_adapter.py` | a protocol-faithful A0.1 adapter (the study's own honest fixture's protocol) whose evaluator, identity claims and D3 attestation are switchable: `--identity {own,claim-e-star,omit}`, `--attestation {none,measured,copy}` |
| `sweep.py`, `equivalence.py` | run one evaluator over all of `C*`; compare two sweeps field by field, including the float bits |
| `verify_fast_tier.py` | checks the frozen `fast_tier` rows, that the checker ignores them, and how each evaluator fares against them |
| `compare_probe_reports.py` | field-by-field comparison of two `conformance.py run` report sets; `--scope rows` separates the row dimension from the check dimension (revisions legitimately add checks) |
| `attest.py` | this fixture's own execution attestor (the `a0/attestation/` workstream was mid-flight when it was written); `attest` + `verify` |
| `run_conformance_probe.sh` | direction 1: the seven checker rows, `[--envelope required\|off]` |
| `run_envelope_probe.sh` | direction 1b: what the D3 token closes and what a binding-copying lane still passes |
| `run_attestation_probe.sh` | direction 2: the TOCTOU probe with its two controls |
| `out/` | every artifact the claims below quote; `out/conformance.pin45cc4e90/` and `out/conformance.pinf33659f6/` keep the earlier revisions' reports verbatim |

## Re-run everything

```bash
cd /home/ebt/rsi-dev/a0/fixtures/observational-equivalence

# 1. E' agrees with E* on all of C* at the frozen theta_E        (14/14, exit 0)
python3 sweep.py       --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --out-root out/e_star --label e_star
python3 sweep.py       --evaluator-dir e_prime --out-root out/e_prime --label e_prime
python3 equivalence.py --a out/e_star/sweep.json --b out/e_prime/sweep.json --out out/equivalence.full.json

# 2. E' is genuinely different: same C*, fast tier, seed 1337     (c05 disagrees, exit 3)
python3 sweep.py       --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --out-root out/e_star.fast --label e_star_fast --fidelity fast
python3 sweep.py       --evaluator-dir e_prime --out-root out/e_prime.fast --label e_prime_fast --fidelity fast
python3 equivalence.py --a out/e_star.fast/sweep.json --b out/e_prime.fast/sweep.json --out out/equivalence.fast.json

# 3. direction 1: the unmodified A0.1 checker                     (~5 min each)
./run_conformance_probe.sh                             # default: --envelope required (D3 on)
./run_conformance_probe.sh --envelope off              # D3 off; writes out/conformance.envelope_off/
#    and compare against the previous checker revision, dimension by dimension:
python3 compare_probe_reports.py --scope rows \
        --before out/conformance.pinf33659f6 --after out/conformance \
        --out out/conformance/reprocheck.e40-required.json      # all seven rows change (exit 3)
python3 compare_probe_reports.py --scope rows \
        --before out/conformance.pinf33659f6 --after out/conformance.envelope_off \
        --out out/conformance.envelope_off/reprocheck.off-vs-pin.json   # only py314 changes state
#    revision-stability of the two earlier revisions is preserved too (pinned copies, since the live
#    out/conformance/ now holds the third revision's reports):
python3 compare_probe_reports.py --scope rows \
        --before out/conformance.pin45cc4e90 --after out/conformance.pinf33659f6 \
        --out out/conformance.pinf33659f6/reprocheck.pin1-vs-pin2.json   # identical: True, exit 0

# 3b. what the D3 token closes, and what a binding-copying lane still passes    (~2 min)
./run_envelope_probe.sh                                 # → out/conformance.envelope_required_attested/

# 3c. the cheaper check the verifier proposed, and the sibling mutant that survives it
python3 sweep.py --evaluator-dir e_prime_fulltheta --out-root out/e_prime_fulltheta --label e_prime_fulltheta_full
python3 sweep.py --evaluator-dir e_prime_fulltheta --out-root out/e_prime_fulltheta.fast --label e_prime_fulltheta_fast --fidelity fast
python3 verify_fast_tier.py --out out/fast_tier_check.json      # E' differs on c05; E'' does not differ at all

# 4. direction 2: attestation                                      (~3 min)
python3 attest.py attest --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --out out/attestation/e_star.json --label e_star_frozen
python3 attest.py attest --evaluator-dir e_prime --out out/attestation/e_prime.json --label e_prime_mutant
./run_attestation_probe.sh

# 5. the a0/attestation workstream's own verifier, both directions
D=/home/ebt/rsi-dev/a0/attestation; PY=/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python
C=/home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/c02_baseline_upstream
$PY $D/attest.py --candidate $C --evaluator /home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py \
    --out-dir out/attestation_a0/control312 --attestation-out out/attestation_a0/e_star.p312.attestation.json
$PY $D/attest.py --candidate $C --evaluator e_prime/e_star.py \
    --out-dir out/attestation_a0/mutant312 --attestation-out out/attestation_a0/e_prime.attestation.json
python3 $D/verify_attestation.py --attestation out/attestation_a0/e_star.p312.attestation.json --repo-root /home/ebt/rsi-dev   # exit 0
python3 $D/verify_attestation.py --attestation out/attestation_a0/e_prime.attestation.json  --repo-root /home/ebt/rsi-dev   # exit 3
```

## Disclosed side effects

Running the unmodified `a0/conformance/conformance.py` (which is the point — an edited copy would
prove less) leaves its per-runtime artifacts in its own tree, all names prefixed `eplus_`:
`a0/conformance/out/adapters/eplus_*.{conformance.json,conformance.out.json,conformance.stdout.txt,conformance.stderr.txt,conformance.exit}`
and `a0/conformance/out/runs/a01-eplus_*-<ts>/` (empty of traces; the runner prunes superseded
directories with the same prefix on its next run of that name). From the D1+D3 revision onward it
also writes its own measurement envelopes to
`a0/conformance/out/envelope/measurement_tokens.<run>.json` (one immutable file per sweep, pruned to
the newest few) — that is the harness's artifact area, and I did not touch it. No file of any other
workstream was modified; `a0/conformance/report*.json`, `E_STAR.json` and `C_STAR/` are untouched.
When the runner drives an adapter it sets `A0_FIXTURE_RUN_ROOT` to a temp directory it deletes at
exit, so the adapter's own scratch never lands in either tree.

## Unverified / undecided

- No Python 3.11 exists on this host, so the interpreter class is measured only for 3.12.11 vs
  3.14.7 (identical values); E*'s own source comment says `sum()` semantics changed at 3.12, so a
  3.11 interpreter is a **plausible but untested** source of numeric drift.
- The candidate-side TOCTOU window (a `solution.py` swapped between E*'s read and its child run) is
  **read from source**, not raced: `e_star.py:685-700` reads the bytes once into a state directory
  keyed by their content hash and the child runs that copy.
- **Three checklist revisions, three pins.** `45cc4e90…6edf` (15:19) and `f33659f6…b50c`
  (16:30:03–16:30:19, after the `adapter_declared_verdict` → `adapter_claim__untrusted` rename) gave
  **identical** seven-row results, compared field by field by `compare_probe_reports.py`
  (`identical: True`); the tool's own negative control — one row's value moved by one ULP — is
  reported as a difference with exit 3. The current `e40d008d…78ce` (D1+D3, re-run 17:19 required /
  17:19:55 `--envelope off` / 17:20:48–17:22:12 with the token wired) is a substantive change and
  every row moves; `REPORT.md` §2.4 carries the matrix and §6 the pins. Other pins: mutant
  `cfaa6194…7b8c`, sibling mutant `fadb4062…0504`, adapter `b1955a45…a1e8` (`a6cff4b2…bbbd` for the
  seven-row runs, whose default path is unchanged), EID* `664115e0…9328`.
- **The D3 token does not close the class against a lane that copies the binding.** Measured:
  `eplus_d3_claim_copy` and `eplus_d3_fulltheta_copy` PASS 14/14, all checks ok, while executing
  `E'`/`E''`. It closes omission and honest divergence — including the sibling mutant the fast tier
  cannot see (`eplus_d3_fulltheta_measured`: 14× `MISMATCH_ATTESTATION`). The remaining step is
  harness-owned measurement (`REPORT.md` §4 R5), which is a decision, not a fixture result. This is
  the same limit `a0/envelope/README.md` §5 records.
- `E'` was chosen to be *detectable* by a wide theta set (it disagrees with E* at `fidelity=fast`).
  The sibling mutant `e_prime_fulltheta` shows the limit of that net: it agrees on both frozen theta
  classes and differs from `E*` on `C*` only in `evaluator_source_sha256`, so no finite theta grid
  over `C*` closes the class — see `REPORT.md` §4 R7 and §5.1.
- The intermediate E* state directories these runs created (private candidate copies, child run
  artifacts, ~9 MB) were removed after the fact; every artifact the claims quote is retained and
  listed above, and the re-run commands regenerate the state.
