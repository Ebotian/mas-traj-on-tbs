# The observational-equivalence fixture — report

Scope: the external review's point 6 ("for any finite `C*` there is an `E' ≠ E*` that agrees on
`E*` everywhere on `C*`"), executed as a controlled experiment against the study's own artifacts.
Owned directory: `a0/fixtures/observational-equivalence/**`. Nothing outside it was edited; §6
lists the runner side effects.

Every claim below is either **measured** (command + real output, artifact path), **read** (file and
line), or marked **UNVERIFIED**.

---

## 1. The mutant `E'`

`e_prime/e_star.py` is a copy of the frozen `E*` with three semantic deviations; `e_prime/e_star_child.py`
is byte-identical to `E*`'s. Everything else — CLI, exit codes, outcome schema, objective formula,
child environment policy — is `E*`'s.

| | sha256 | `evaluator_source_sha256` (self-reported) | EID* `EvaluatorSource` component |
|---|---|---|---|
| `E*` (`a0/tasks/circle-packing/e_star.py`, 34860 B) | `2abc6ea1…5567` | `5ae97ad9…5532` | `a3d6534b…dc29` |
| `E'` (`e_prime/e_star.py`) | `cfaa6194…7b8c` | `c42963b0…6796` | `cbb85480…869b` |

The deviations (this is not a rename — each one changes behaviour for some input):

| id | site | `E*` | `E'` |
|---|---|---|---|
| **M1** | `audit_sample()` | seed-keyed decimation: `sha256("e_star/v1\|seed=S\|n=N\|index=i")` ordering, first `size` | ignores the seed, first `size` indices in index order |
| **M2a** | `in_bounds()` | `x - r >= 0 - EPS`, `x + r <= 1 + EPS` | strict, no EPS slack |
| **M2b** | `overlap_check` | overlapping iff `gap < -EPS` | overlapping iff `gap < 0.0` |
| **M3** | `structure_fields()` | `min_boundary_margin` over the audited subset | over every returned circle |

### 1.1 It agrees with `E*` on all of `C*` at the frozen `theta_E` (measured)

```
$ python3 equivalence.py --a out/e_star/sweep.json --b out/e_prime/sweep.json --out out/equivalence.full.json
  c01_good_hex             ok       2.4519205208433132     AGREE      same
  c02_baseline_upstream    ok       0.25                   AGREE      same
  c03_mirror               ok       2.4519205208433132     AGREE      same
  c04_near_tie             ok       2.451820520843313      AGREE      same
  c05_overlapping          invalid  None                   AGREE      same
  (rows c06…c13 elided here; the full 14-row table is in out/equivalence.full.json)
  c14_near_zero            ok       2.6e-05                AGREE      same
e_star vs e_prime: 14/14 candidates agree exactly on ['exit_code', 'status', 'failure_kind', 'objective_value']
EXIT=0
```

Agreement is on the **float bits** (`struct.pack('>d', value).hex()`, printed in
`out/equivalence.full.json`), not on `repr`. `structure` (overlap count, min gap, margin, pairs
audited) is identical on all 14 as well, because M1 is inert at `fidelity=full`, M3 too, and no
member of `C*` reaches M2's band (tightest gaps/margins observed: `min_gap = 2.0e-7` for
c01/c03/c04, `min_boundary_margin = 1.0e-7`, and exactly `0.0` for c02/c07 — which passes M2a's
inclusive strict comparison).

### 1.2 It is genuinely different (measured, on `C*` itself)

Same candidates, same seed, `fidelity=fast`:

```
$ python3 equivalence.py --a out/e_star.fast/sweep.json --b out/e_prime.fast/sweep.json --out out/equivalence.fast.json
  c05_overlapping          ok       2.4519205208433132     DISAGREE   DIFFERS
    !! c05_overlapping: exit_code: A=0 B=2
    !! c05_overlapping: status: A='ok' B='invalid'
    !! c05_overlapping: failure_kind: A=None B='invalid_configuration'
    !! c05_overlapping: objective_value: A=2.4519205208433132 B=None
e_star_fast vs e_prime_fast: 13/14 candidates agree exactly ...
EXIT=3
```

The mechanism is exactly the one `E*`'s own docstring calls out (`e_star.py:35-39`): the audit
sample is an evaluator input, and

```
E*   audit_sample(26, 4, seed=1337) = [0, 3, 12, 22]   -> misses c05's overlapping pair (0,1): returns ok, 2.4519205208433132
E'   audit_sample(26, 4, seed=1337) = [0, 1, 2, 3]     -> sees it: invalid / invalid_configuration
```

(measured: `out/e_star.fast/sweep.json`, `out/e_prime.fast/sweep.json`, and the same expression
evaluated directly against `e_star.audit_sample`).

So `E'` is a different evaluator that is *not* distinguishable by the A0.1 gate, and *is*
distinguishable once the theta grid includes the fast tier. Both facts matter for §5.

---

## 2. Direction 1 — the existing behavioural checker accepts `E'`

The checker is the study's own, unmodified: `a0/conformance/conformance.py run --runtimes … --adapter …`.
The adapter is `adapters/e_plus_adapter.py` (revision `a6cff4b2…bbbd`), which implements the same
protocol as the study's honest fixture (`a0/conformance/fixtures/adapters/reference_adapter.py`):
integrity-check every `C*` member, invoke the evaluator CLI once per candidate at the frozen
`theta_E`, carry `eid_star` verbatim with a recomputable `eid_r`, declare `evaluator_evidence.status = "ok"`.
All seven rows in one command: `./run_conformance_probe.sh` (~5 min), raw output `out/conformance/probe.log`,
per-row reports `out/conformance/eplus_*.json`.

```
=== verdicts ===
eplus_control          PASS     all checks passed                       rows={'MATCH': 5, 'MATCH_VERDICT': 9}
eplus_control_py314    FAIL     E_r(c) disagrees with E*(c)             rows={'MISMATCH_DIGEST': 14}
eplus_mut_claim        PASS     all checks passed                       rows={'MATCH': 5, 'MATCH_VERDICT': 9}
eplus_mut_echo         FAIL     adapter check(s) failed: E-star-manifest-echo
eplus_mut_omit         PASS     all checks passed                       rows={'MATCH': 5, 'MATCH_VERDICT': 9}
eplus_mut_own          FAIL     E_r(c) disagrees with E*(c)             rows={'MISMATCH_DIGEST': 14}
eplus_mut_twin         PASS     all checks passed                       rows={'MATCH': 5, 'MATCH_VERDICT': 9}
```

**Re-run after the checker's field rename (added later, measured).** The table above was first
produced against `conformance.py` `45cc4e90…6edf` and then reproduced **row for row** against the
current revision `f33659f6…b50c`, whose only relevant change was renaming the recorded adapter claim
to `adapter_claim__untrusted` (no verdict logic touched). The comparison is mechanical, not visual:
`python3 compare_probe_reports.py --before out/conformance.pin45cc4e90 --after out/conformance --out
out/conformance/reprocheck.json` → `identical: True`, exit 0, all 7 runtimes, all 14 rows each (see
§6 for the pins and the tool's own negative control). New-revision raw output: `out/conformance/probe.log`.

**The control matters.** `eplus_control` runs the real `E*` through my adapter: `PASS`, 11/11
checks. So the adapter implementation is faithful and the checker can accept an honest adapter —
the mutant rows below are not an artifact of a broken fixture.

### 2.1 The accept (the gap)

`eplus_mut_claim` executes `E'` on all 14 candidates and reports `E*`'s identity material (the
frozen `E_STAR.json` per-candidate `canonical_digest` and the frozen source digest) on every row:

```
$ cd a0/conformance && python3 conformance.py run --runtimes eplus_mut_claim \
    --adapter "eplus_mut_claim=python3 …/e_plus_adapter.py --evaluator-dir …/e_prime --identity claim-e-star" \
    --no-controls --out …/out/conformance/eplus_mut_claim.json
--- eplus_mut_claim ---
    PASS: all checks passed
verdicts (A0.1 only): {"eplus_mut_claim": "PASS (14/14 measured)"}
```

All eleven checks pass, including `E-r-equals-E-star` (`14/14 candidates agree with E*(c) within
epsilon=1e-09`). Nothing in the checker inspects the evaluator that ran; the identity-bearing
fields it does read are strings the adapter wrote.

Three more measured observations from the same table:

- **The honest mutant fails on identity alone, not behaviour.** `eplus_mut_own` reports `E'`'s own
  outcome digests: 14× `MISMATCH_DIGEST`, and the runner's own row records show `delta = 0.0` on
  every candidate with a number (`e_r_value = 2.4519205208433132` = `E*`'s value). The reported
  reason, `E_r(c) disagrees with E*(c)`, is therefore misleading: the numbers do not disagree, the
  digest string does. An adapter that reports its identity truthfully is failed; one that asserts
  `E*`'s identity is passed.
- **Omitting the identity fields is free and silent.** `eplus_mut_omit` reports no
  `canonical_digest` and no `source_sha256`: PASS, with no note and no finding anywhere in the
  report (`E-r-equals-E-star`: "14/14 … disagreeing: none"; the only check naming a digest is
  `EID-r-recomputes`, which is about `EID_r`). The reader at `conformance.py:1617-1628` guards the
  digest comparison with `if obs.get("canonical_digest") and table.get("canonical_digest")`, so
  absence skips verification rather than failing it.
- **A value-identical twin cannot be seen from the numbers.** `eplus_mut_twin` answers c01's row by
  evaluating the c03 directory. c01 and c03 are bit-identical in value
  (`2.4519205208433132`, both) and in every structure field, so the value comparison is blind; with
  the identity fields omitted the checker PASSes. That the row really came from the other file is
  visible only in the output document the adapter kept:
  `out/adapter-runs/twin_probe-20260921T151848/outcomes/c01_good_hex.json` →
  `.candidate.source_sha256 = 893d0aa4…6fcf` = c03's file, not c01's `bca4286e…3a6d`.

### 2.2 The one channel that did catch it — and why it does not count

`eplus_mut_echo` carries the evaluator's own `E_STAR_MANIFEST {...}` stdout line in each row:

```
    FAIL: adapter check(s) failed: E-star-manifest-echo
    c01_good_hex: echoed evaluator_source_sha256='c42963b0…6796' != the frozen E* source digest '5ae97ad9…5532'
```

`check_manifest_echoes` (`conformance.py:2079-2129`) compares an echoed manifest — or, through
`field_echoes` (`conformance.py:2053-2078`), the same facts published as
`e_star_canonical_digest` / `e_star_evaluator_source_sha256` fields, which is how KAPSO spells
them — against the frozen source digest, the frozen per-candidate digest and the frozen theta. But
the channel is **voluntary and self-served**: its no-echo branch reports "no E* manifest echo found
… (not a failure: it is a bonus channel)". The runtime that is the actual worry — one whose
evaluator differs and which does not volunteer — is exactly the runtime with no echo, and that is
recorded as *not a failure*. `eplus_mut_claim` and `eplus_mut_omit` (no echo) demonstrate this: PASS.

Related, and citable: `adapter_contract.md` §4.3 (obligation 3, "The invoked `E*` and the recorded one
must be the same file") *requires* the adapter to record the invoked
evaluator's source digest in `evaluator_evidence` ("a mismatch means the adapter executed something
else"), but neither `evaluator_evidence.source_sha256` nor a plain `evaluator_source_sha256` row key
is among the spellings the checker reads (`ROW_IDENTITY_KEYS`, `conformance.py:1069-1073`; the echo
readers recognize the `E_STAR_MANIFEST` line and the `e_star_*` field names). The obligation exists;
the verification of it does not.

### 2.3 A false red from the same field (finding for the checker's owner)

The real `E*`, executed by `python3.14` instead of the pinned `3.12.11`, and reporting its identity
honestly, is failed:

```
eplus_control_py314    FAIL   E_r(c) disagrees with E*(c)    rows={'MISMATCH_DIGEST': 14}
```

Its values are `delta = 0.0` on all 14 (measured, same report). Diffing the two canonical outcomes
of the same candidate shows the entire difference:

```
same candidate c02_baseline_upstream, frozen E*, two interpreters:
  DIFF /canonical_digest: py3.12='b4ddfc46…92fc'  py3.14='9bb99f39…b058'
  DIFF /interpreter/version: py3.12='3.12.11'  py3.14='3.14.7'
```

`canonical_digest` covers the whole outcome payload, which includes `interpreter.version`, while
the checker never compares the `interpreter` field (grep over `conformance.py`: it appears only at
lines 730/859/964/970/2500, all about launching the reference sweep and the report's frozen
block). So the same field is simultaneously too weak (optional, self-reported, free to omit) and
too strong (fails a byte-identical evaluator on a different interpreter build). The same failure
mode appears in `a0/attestation/` — see §3.1.

---

## 3. Direction 2 — execution attestation rejects `E'`

### 3.1 The `a0/attestation/` workstream's own verifier (third-party tool, measured)

Their producer and verifier are usable now. Control and mutant, both at the frozen interpreter
(`a0/tasks/circle-packing/.venv/bin/python`, 3.12.11), on candidate c02:

```
$ $D/attest.py --candidate .../c02_baseline_upstream --evaluator .../e_star.py        # control
declared EID* 664115e0…9328  (frozen 664115e0…9328) | semantic == declared: True | frozen: True
$ python3 $D/verify_attestation.py --attestation out/attestation_a0/e_star.p312.attestation.json --repo-root /home/ebt/rsi-dev
  [ok  ] the evaluator's self-reported source digest equals E*'s frozen value
  [ok  ] the outcome matches the frozen reference table row for this candidate
Q1_recomputes RECOMPUTES   Q2_semantic SEMANTIC_MATCH   Q3_realization REALIZED        exit=0

$ $D/attest.py --candidate .../c02_baseline_upstream --evaluator .../e_prime/e_star.py  # mutant
$ python3 $D/verify_attestation.py --attestation out/attestation_a0/e_prime.attestation.json --repo-root /home/ebt/rsi-dev
  [FAIL] the evaluator's self-reported source digest equals E*'s frozen value
         {"self_reported": "c42963b0…6796"}
  [FAIL] the outcome matches the frozen reference table row for this candidate
         {"expected": "b4ddfc46…92fc", "observed": "3bf1f7c3…ced3", "observed_status": "ok"}
Q1_recomputes RECOMPUTES   Q2_semantic SEMANTIC_MATCH   Q3_realization NOT_REALIZED   exit=3
```

`Q3` is the leg that catches it, which is what their own module docstring claims it is for. Their
control was **not** clean on the first attempt, for the §2.3 reason: run under `python3.14`, their
producer captures `runtime.executable = /usr/bin/python3.14`, `E*`'s outcome digest becomes
`9bb99f39…`, and their verifier returns `Q3_realization NOT_REALIZED` (exit 3) for the *real* `E*`
(artifact `out/attestation_a0/verdict.e_star.json`). Their own observation block even records
`attestation_tool_interpreter_matches_captured`. Worth passing to that workstream: either pin the
tool's interpreter to the frozen build, or report an interpreter drift as its own verdict instead
of folding it into `NOT_REALIZED`.

### 3.2 This fixture's own attestor (`attest.py`)

Same idea, implemented independently: the harness picks the evaluator files, hashes the bytes it is
about to execute, executes **a staged copy of those bytes**, feeds `C*` itself, hashes each candidate
it feeds, reads the outcome files and re-derives each `canonical_digest` from the file contents, then
compares the measured `EvaluatorSource` records against EID*'s own records. It re-derives EID*'s
component digest with the contract's own builder (`a0/contract/evalcontract.py`, imported read-only).

```
$ python3 attest.py attest --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --out out/attestation/e_star.json
  measured EvaluatorSource component digest : a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  EID* EvaluatorSource component digest     : a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  e_star.py            measured 2abc6ea1…5567  expected 2abc6ea1…5567  MATCH
  outcomes re-hash to their own canonical_digest: True
  VERDICT: ACCEPT: the executed evaluator is the one EID* freezes

$ python3 attest.py attest --evaluator-dir e_prime --out out/attestation/e_prime.json
  measured EvaluatorSource component digest : cbb854800a0fa870fefb757546261202be4e7ccf9be3eec3d400f32ae0b0869b
  EID* EvaluatorSource component digest     : a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  e_star.py            measured cfaa6194…7b8c  expected 2abc6ea1…5567  DIFFER
  VERDICT: REJECT: the executed evaluator's source records are not EID*'s EvaluatorSource
```

`verify` then compares an adapter's own A0.1 answer against that record. With the document the
adapter really produced (`out/adapter-doc/e_plus_claim-e-star.json`, produced by the same command
line the runner uses):

```
$ python3 attest.py verify --record out/attestation/e_prime.json --adapter-doc out/adapter-doc/e_plus_claim-e-star.json --out out/attestation/verdict.claim-e-star.json
  attested evaluator identity is EID*'s: False
  !! the evaluator the harness measured and executed is NOT the one EID* freezes: … cbb85480…869b != a3d6534b…dc29
  !! c01_good_hex: adapter canonical_digest '1144adc6…74f8' != attested '831d818c…3ce0'
  ... one such line per candidate ...
  VERDICT: REJECT                                                          exit=3
$ python3 attest.py verify --record out/attestation/e_star.json --adapter-doc out/adapter-doc/e_plus_control.json --out out/attestation/verdict.control.json
  attested evaluator identity is EID*'s: True
  VERDICT: ACCEPT                                                          exit=0
```

The control is meaningful because the adapter document came from an independent run (different
state root, different process) yet every per-candidate digest matches the attestor's own run — the
identity-bearing part of the outcome is path-independent, which is what makes attestation and
behavioural evidence comparable at all.

### 3.3 TOCTOU: probe with the study's two controls (measured)

`./run_attestation_probe.sh` — an "evil" copy of `E*` (`sum_radii += 1e-3`, version marker) replaces
the evaluator file ~6 s after the attestor hashed it and ~4 s before it runs.

```
CONTROL NEGATIVE (--no-stage): measured e_star.py sha256 = 2abc6ea1…5567 (clean E*)
  outcomes self-report the launched digest: False
  objective of c01 in the attested run: 2.452920520843313 = 2.4519205208433132 + 1e-3
  VERDICT: REJECT: the executed bytes changed under the run
CONTROL POSITIVE (--stage):   measured e_star.py sha256 = 2abc6ea1…5567 (clean E*)
  outcomes self-report the launched digest: True
  objective of c01 in the attested run: 2.4519205208433132
  VERDICT: ACCEPT: the executed evaluator is the one EID* freezes
```

Two lessons, both measured: hash-the-path-then-exec-the-path is a **false green generator** (it
printed a clean identity while `1e-3`-shifted numbers were produced; it was caught only because the
evaluator happens to self-report its source digest inside the outcome, which an arbitrary `E'` need
not do), and staging the hashed bytes removes the window. `E*` already applies this discipline to
*candidate* bytes (`e_star.py:685-700`); its own bytes need the same treatment.

---

## 4. Residual equivalence classes neither mechanism catches

"Neither" = not the A0.1 checker as it stands (measured above), not an execution attestation of the
kind in §3. Each class names the evidence that *would* catch it.

**R1 — Same bytes, different environment.** `E*` executed by 3.12.11 and by 3.14.7 produces
identical statuses, identical `sum_radii` bits and identical audit fields on all 14 (measured,
`out/equivalence.interpreter.json`); the only difference anywhere in the canonical outcome is
`interpreter.version`. EID*'s `EvaluatorSource` is two files and does not name the interpreter,
stdlib or loader, and neither the checker nor an attestor that hashes those files can see the
difference. *Would catch it:* compare the `interpreter` block the outcome already carries (`E*`
emits implementation + version) against the frozen one — a reader change, not new evaluation; and
hash the interpreter binary and stdlib into a sixth EID component if the drift is a real threat.
Note the asymmetry: this class is currently invisible to a *behavioural* reader and a *false red* to
a digest-comparing one (§2.3, §3.1), so today it is caught by accident and misattributed.

**R2 — Value-identical twin / wrong-file substitution.** Measured: `eplus_mut_twin` PASSes; the c01
row was produced from the c03 file, and c01/c03 are bit-identical in value and structure. Nothing in
the numbers distinguishes them; the only in-band evidence is a per-row file digest, which is
optional (R3) and self-reported. *Would catch it:* the harness hashing the candidate bytes it feeds,
per row — i.e. moving `source_sha256` from the adapter's row into the harness's own record (my
`attest.py` already records `candidate_source_sha256_measured`), or making the row carry E*'s own
`candidate.source_sha256` read from the output document by the harness rather than by the adapter.

**R3 — Asserted identity (omission or misstatement).** Measured: omission is silent (no finding), and
misstatement passes. An identity field is only evidence when a party that is not the adapter measures
it. *Would catch it:* fail-closed on required fields + a harness-measured identity (§5).

**R4 — Attested measurement, unattested consumption.** A runtime can evaluate honestly and then
reuse, relabel or cache the number. The study's own cache trap (`control_cache_hit`,
`fixtures/adapters/deviant.py`) is detected only because the fixture *declares*
`evaluator_evidence.status = "cache_hit"` (`conformance.py:1616`) — a runtime that reuses a value
silently, especially one that coincides with the right value (R2), is not visible. Attestation of the
measurement says nothing about the search that later reads it. *Would catch it:* a harness-issued
measurement id carried in the score trace and joined to the selection trace — the study already
contracts `score,selection,resource` traces (`conformance.py:TRACES`); what is missing is the join
key and a requirement that every consumed score name the measurement that produced it.

**R5 — The trust root: who launches.** Today the *adapter* invokes `E*` and reports the result
(`adapter_contract.md` §4.1 fixes the invocation the adapter must run; measured in
`a0/conformance/fixtures/adapters/reference_adapter.py` and in my `e_plus_adapter.py`, both of which
`subprocess.run` the evaluator themselves). Any attestation produced by the adapter is then a
statement, not a measurement; §3 only rejects `E'` because *the harness* chose and executed the
evaluator. So as A0.1 is currently designed, no in-band evidence can close the `E'` class — the fix
is architectural, and the runner is already half-way there: it owns an `E*` invocation path of its
own (`reference_rows` / `e_star_argv`, used to produce `reference.json` and re-exercised with
`--refresh-reference`). Related: nothing attests the attestor; my §3.2 self-tests (reproducing EID*'s
component digest and `E*`'s source digest) are self-checks, not an external audit.

**R6 — Faithful re-implementations.** A refactor, port or vendored copy of `E*` that agrees on every
input is rejected by source-identity attestation while being behaviourally identical. This is the
one class where strict attestation is *deliberately* stricter than behavioural equivalence; the
reviewer should know it, because it means A0.1 as strengthened in §5 measures "ran these bytes", not
"computes this function".

**R7 — Dimensions `C*` cannot test at all.** All 14 members are `n = 26`, and the frozen gate is
`fidelity=full, fraction=1.0, seed=1337`. A mutant that differs only for `n ≠ 26`, only for
`fraction < 1`, or only for a different seed is invisible at the frozen theta — M1 is exactly such a
deviation, which is why §1.2 needed a second theta to expose it. *Would catch it:* a small theta
grid — and the frozen table already carries one, the per-candidate `fast_tier` row (§5.1), so the
oracle costs nothing. But this class is **widened, not closed**, by that: the sibling mutant
`e_prime_fulltheta` agrees with `E*` on both full and fast at the level the checker compares, so a
further theta would be needed for it, and so on. The closure for this class is the identity of the
evaluator, not more of its outputs.

---

## 5. Recommendation

### 5.1 The cheaper check the verifier proposed — verified, and what it does and does not buy

The independent verifier's proposal: `E_STAR.json` freezes a per-candidate `fast_tier` row and the
A0.1 checker never uses it, while `E'` diverges exactly there (c05). I checked the three parts, and
all three hold — evidence `out/fast_tier_check.json`, tool `verify_fast_tier.py`:

1. **The oracle exists.** All 14 candidates carry a `fast_tier` block (`status`, `objective_value`,
   `exit_code`, `failure_kind`, `canonical_digest`, `items_audited`, `pairs_audited`, `coverage`)
   measured at `E_STAR.json.fast_theta_e = {fidelity: fast, fraction: 0.15, n: 26, runs: 5,
   runtime_budget_ms: 250.0, seed: 1337, timeout_s: 120.0}`.
2. **The checker ignores it.** `conformance.py` (revision `f33659f6…b50c`) contains **0**
   occurrences of `fast_tier` and **0** of `fast_theta_e`; the only `fast` it knows is the
   `reference` subcommand's `--fidelity` flag. The fast tier is written by
   `tasks/circle-packing/tools/build_table.py` and read by KAPSO's **A0.2** adapter
   (`runtimes/kapso/a0_adapter/a02.py`) — the A0.1 lane never touches it.
3. **It would catch my mutant, on one row.** `E*`'s own fresh fast sweep reproduces all 14 frozen
   `fast_tier` rows exactly — values *and* `canonical_digest` — so the oracle is usable as it
   stands; and `E'` contradicts it on c05: frozen `ok / 2.4519205208433132 / exit 0` vs `E'`
   `invalid / null / exit 2`. A comparison at the level A0.1 already applies (`exit_code, status,
   failure_kind, objective_value`) would fail `E'` on that row, for one extra evaluator invocation
   per candidate and no new oracle.

**It does not overturn the argument, and the reason is measured, not asserted.** I built the
sibling mutant `e_prime_fulltheta/e_star.py` (`fadb4062…0504`): the primary mutant with **M1
reverted**, keeping only M2 (strict tolerance band) and M3 (audit-scope margin). Against the frozen
fast rows its values are equal on **14/14** — the cheaper check misses it — and comparing its full
canonical outcomes against `E*`'s shows it differs on `C*` at **both** theta classes in exactly two
keys, 14/14 candidates each: `evaluator_source_sha256` and the `canonical_digest` derived from it.
Every behavioural key — status, objective, structure, `min_boundary_margin`, the audit sample,
`min_gap`, the check details — is byte-identical under both full and fast. So the fast tier catches
my *primary* mutant because I chose a sampling deviation (M1), which is exactly the kind of
deviation a second theta class exposes; it is a wider behavioural net, not a closed one. Any mutant
that agrees with `E*` on both frozen thetas and differs only where no candidate probes it — inside
the 1e-9 tolerance band, at `n ≠ 26`, at a `fraction` other than 0.15 — passes both tiers, which is
§4 R7. The one surface on which `E''` is distinguishable from `E*` at all on `C*` is its identity,
and the only in-band carrier of that is a string the adapter writes about itself. A stronger form of
the same idea — comparing `canonical_digest` at the fast tier — does catch `E''` (14/14 digests
differ) but inherits both measured defects of that channel: it is adapter-optional (omission is
silently waived, §2.1) and interpreter-sensitive (a legitimate `E*` under 3.14.7 fails with
`delta = 0.0`, §2.3).

**The independent verifier reached the same c05 divergence from the other side.** Their evidence file
(`a0/verify/sprint-evidence/VERDICT.md`, read-only for me) records the same three-line comparison —
frozen `c05.fast_tier` `ok`/`2.4519205208433132`/`920ebe73…`, `E*` reproducing it, `E'` returning
`invalid` — and concludes a theta grid "does not falsify §5's recommendation as stated" because "a
theta grid is just a larger `C*`". Their note is a reasoning argument; §5.1's sibling mutant is the
measurement that bounds it: the fast tier misses `E''` entirely. (Two notes for the coordinator: their
pin `45cc4e90…6edf` is superseded — the checker's owner renamed the field at 16:24:53 to
`f33659f6…b50c`, and my §2 re-run covers the new revision; the interpreter defect in §2.3 was
independently reproduced by them and is a shared-checker defect, not a fixture artifact.)

**My recommendation therefore gains one item rather than changing:** add the
frozen fast tier to the A0.1 comparison **at the value/verdict level** — cheap, already-oracled, no
false-red cost, and it closes the decimation/sampling sub-class — *in addition to*, not instead of,
the identity change below.

### 5.2 What to change

Grounded in the measurements above, the highest yield per unit of effort is **not** to extend `C*`
(point 6 forbids it) and **not** to tighten the `canonical_digest` comparison (measured too weak —
optional and self-reported, so a misstating adapter passes and an omitting one is silently waived —
and simultaneously too strong — it fails the byte-identical `E*` on a different interpreter build,
`delta = 0.0` on all 14), but to **move the evaluator invocation for the A0.1 rows into the harness
and make the resulting identity a required, harness-measured field**: the runner already owns an
`E*` invocation path (`reference_rows` / `e_star_argv`, which produces `reference.json`) and already
sweeps `C*` with it, so have it emit, per candidate, a measurement token —
domain-separated sha256 over (EID*, candidate source sha256, `theta_E`, a per-run nonce) written
into its own state root — require every adapter row to carry that token plus the identity fields
(fail-closed on omission), and compare the row's *use* of the number against the token rather than
the adapter's *claim* about it; the mutant here is accepted today in three of five modes only
because every identity-bearing field it reports is one it wrote itself, and the sole channel that
did catch it (`E_star-manifest-echo`) is voluntary by the checker's own words, even though
`adapter_contract.md` §4.3 (obligation 3) already obliges the adapter to assert its evaluator's
digest. Cost: the extra
`E*` invocations are the ones the runner already performs, plus roughly a reader/adapter-contract
change; benefit: the `E'` class flips from free to FAIL, the `delta = 0.0`/`MISMATCH_DIGEST` false
red disappears because identity is compared on the measured evaluator source instead of on an
outcome digest that embeds the interpreter build, and R2/R3/R4 acquire a join key. If only an hour
is available, take the three cheap halves first — fail-closed on the missing fields, require the
`interpreter` block to match (or drop it from the digest payload and compare it explicitly), and add
the frozen `fast_tier` rows to the comparison at the value/verdict level (§5.1) — and accept that
they close omission, interpreter drift and the sampling sub-class but not a runtime that simply
asserts `E*`.

---

## 6. What this report does not establish

- **`a0/STATUS.md` was not edited** (coordinator-owned) and no other workstream's files were
  modified. The runner's own artifacts written under `a0/conformance/out/` are listed in
  `README.md`.
- **Revision pins.** The seven checker rows in §2 have now been produced against **two** revisions of
  `a0/conformance/conformance.py`, and are identical under both:

  | revision | sha256 | when | rows |
  |---|---|---|---|
  | before the rename | `45cc4e90b9c65c0a0139c336ed1d23288fa242512ba7a8970190a9f1f72f6edf` | 15:19:04–15:19:19 | §2 table |
  | current | `f33659f605f6a6892e9d0f766961a13eeb55ddc4225776ad34fb974cdecfb50c` | 16:30:03–16:30:19 (file mtime 16:24:53, unchanged before and after) | identical, row for row |

  The rename (`adapter_declared_verdict` → `adapter_claim__untrusted`, so that no machine-readable
  field can be misread as a verdict) touched no verdict logic, and that is now measured rather than
  assumed: `python3 compare_probe_reports.py --before out/conformance.pin45cc4e90 --after out/conformance
  --out out/conformance/reprocheck.json` returns `identical: True` (exit 0) for all 7 runtimes —
  same `state`, same `reason`, same per-check `ok` flags, same 14 row verdicts/values/deltas, same
  finding ids — and reports `adapter_declared_verdict` present only in the old set and
  `adapter_claim__untrusted` only in the new one, with value `null` in both. The tool's own negative
  control: perturbing one earlier row's `e_r_value` by one ULP makes it report that row and exit 3.
  Old-revision reports are kept verbatim in `out/conformance.pin45cc4e90/`.
  Also pinned: mutant `e_prime/e_star.py` `cfaa6194…7b8c`, sibling mutant `e_prime_fulltheta/e_star.py`
  `fadb4062…0504`, adapter `adapters/e_plus_adapter.py` `a6cff4b2…bbbd`, `E_STAR.json`
  (`fast_tier` oracle) and EID* `664115e0…9328`. If any of those move, re-run
  `run_conformance_probe.sh && python3 compare_probe_reports.py …` before quoting these rows.
- **UNVERIFIED:** whether a Python 3.11 interpreter would change `sum_radii` on `C*` (no 3.11 on
  this host); the candidate-side TOCTOU window at runtime (read from `e_star.py:685-700`, not
  raced); whether any real runtime adapter in this study actually misreports its evaluator identity
  — the mutant is a fixture constructed to show the checker cannot tell, not an accusation.
- **`a0/attestation/` is another workstream's, still in flight.** Its producer and verifier were
  usable for the two runs in §3.1; if they change, re-run that block. Its 3.14 control failure is
  reported to that workstream, not adjudicated here.
- **No model spend.** Every command here is local; no API call was made, so there are no token
  counts to report.
