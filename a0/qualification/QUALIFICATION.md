# Per-runtime qualification `Q_r`, the `Eligible(r)` predicate, and the A0 freeze

Workstream: `a0/qualification/**`. This directory owns three things:

1. the per-runtime qualification vector `Q_r` and the predicate `Eligible(r; T)` over it
   (external review points 2 and 8, redefined by decision **D2**);
2. the consumer side of the **harness attestation** of A0.1 (decision **D3**) — the interface, and
   the fail-closed rule for reading it;
3. the **freeze mechanism** for stage A0: a frozen vector with per-artifact digests and a checker
   that says whether the current tree still matches it.

| file | what it is |
|---|---|
| `qualification.json` | the deliverable: `Q_r` for all four runtimes, the declared predicate, its evaluation under both threshold vectors, `R_A1^main`, the screen block, the `unproven` and `rejected` blocks |
| `eligibility.py` | the predicate `Eligible(r; T)` with the rules and the threshold vectors as data, plus a self-test (`--self-test`) |
| `build_qualification.py` | derives `Q_r` from existing evidence and writes the JSON; `--check` re-derives and diffs it; `--self-test` exercises the D3 resolution |
| `verify_qualification.py` | independent consistency check over the JSON, the report and the contract (26 assertions) |
| `freeze.py` | `fingerprint` / `arm` / `gates` / `check` / `freeze` / `self-test` — the freeze mechanism |
| `attested-a0-1.contract.json` | the D3 interface: where an attestation is read from, which fields it must carry, what fails closed |
| `A0.freeze.candidate.json` | the armed baseline (`ARMED_NOT_FROZEN`) that `freeze.py check` diffs against. It is **not** a freeze |
| `QUALIFICATION.md` | this document |

Nothing here re-runs an experiment. Every component is read out of evidence another workstream
produced, names the path it came from, and is tagged **verified by running**, **read from source**
or **inferred**. The single exceptions are `mrc` (validated by running `a0/mrc/mrc.py validate`,
read-only and offline) and the two self-tests of this directory's own code.

## 0. State of play after D3 landed

D1, D2 and D3 have all landed; the A0.1 report on record is the D3 re-run with the measurement
envelope **required**. What that changed here:

| previously reported | now | why |
|---|---|---|
| `R_A1^main = {}` (empty) | **`R_A1^main = ['simpleloop']`** | SimpleLoop's lane echoes the harness measurement token and attests the bytes it executed for 14/14 rows, so `a0_1_attested = PASS` and every other `T_A1` clause already held |
| `R_exploratory = [eve, kapso, loreley, simpleloop]` | **`R_exploratory = ['simpleloop']`** | the other three are not `UNPROVEN` any more, they are `FAIL`: the A0.1 run asked for the token and the rows did not answer. `T_exploratory` tolerates *absent* evidence, never *rejected* evidence |
| `a0_1_measured.state` = the runner's `state` | **the measurement axis**, with the runner's folded acceptance state carried separately as `runner_acceptance_state` | D3 made the runner fold two axes into one state. See §1.1 — this is the correction that matters most |
| `a0_1_attested` read from `/unproven` | `a0_1_attested` **decided** for all four runtimes | the predicted wiring was right: `runtimes.<r>.checks[check_id=measurement-attestation]`, exactly as read from `conformance.py` before the output existed. No change to the contract's `record_sources` paths was needed |

## 1. The vector `Q_r`

`Q_r = (a0_1_measured, a0_1_adapted, a0_1_attested, a0_2_mechanism, a0_2_bridge, closure, mrc)`.

| runtime | A0.1 measured | A0.1 adapted | A0.1 attested | A0.2 mechanism | A0.2 bridge | Closure | MRC | `T_A1` | `T_exploratory` |
|---|---|---|---|---|---|---|---|---|---|
| **SimpleLoop** | `14/14` | `0/14` | **PASS** (`ATTESTATION_OK`, 14/14 rows) | PASS | PASS | CLOSED | FROZEN | **eligible** | eligible |
| KAPSO | `14/14` | `0/14` | **FAIL** (`MISSING_ATTESTATION`) | PASS | PASS | CONDITIONAL | FROZEN | out (`R3`, `R6`) | out (`R3`) |
| EvE | **`5/14`** | `9/14` | **FAIL** (`MISSING_ATTESTATION`) | PASS | ATTEMPTED | CONDITIONAL | FROZEN | out (`R1`, `R3`, `R5`, `R6`) | out (`R3`) |
| Loreley | `14/14` | `0/14` | **FAIL** (`MISSING_ATTESTATION`) | PASS | ATTEMPTED | CONDITIONAL | FROZEN | out (`R3`, `R5`, `R6`) | out (`R3`) |

```
R_A1^main     = ['simpleloop']
R_exploratory = ['simpleloop']
```

### 1.1 The two axes must not be merged (the D3 correction)

Since D3 the conformance runner keeps two things apart, and says so in
`runtimes.<r>.qualification.a0_1.basis`:

* **MEASUREMENT** — `row.verdict_before_attestation` + `row.evaluator_evidence_status`: did the
  runtime's **own evaluator interface** produce a fresh verdict that the runner compared against
  `E*`?
* **ACCEPTANCE** — `row.attestation_verdict`: did the row echo the harness's measurement token and
  attest the bytes it executed, so that it is **acceptable evidence**?

The runner's folded `state`/`label` are the acceptance state. After the D3 re-run KAPSO's report
says `state: FAIL` while its own `reason` says *"the numbers agree on 14/14 rows, but an A0.1 row
must also echo the harness measurement token"*. Reading that `FAIL` into `a0_1_measured` would
report **"this runtime's measurement is wrong"** when the truth is **"this runtime's evidence is
missing"** — two findings with different remedies. So:

* `a0_1_measured.state` is derived here from `rows[].verdict_before_attestation` against the
  runner's own accepting set, and corroborated by the `E-r-equals-E-star` check's
  `measurement_agreeing` / `measurement_disagreeing_candidates`. The runner's folded state is
  carried on the same component as `runner_acceptance_state`.
* `a0_1_attested` carries the acceptance verdict.

The result is visible in `Q_r` and asserted by `verify_qualification.py`
(`measurement_state_is_not_the_folded_acceptance_state`, `two_axes_present_at_the_source`):

| runtime | measurement axis | runner's folded (acceptance) state | attestation verdict |
|---|---|---|---|
| SimpleLoop | PASS (14/14 agreeing) | PASS | `ATTESTATION_OK` |
| KAPSO | PASS (14/14 agreeing) | FAIL | `MISSING_ATTESTATION` |
| EvE | PARTIAL (14/14 agreeing, 9 synthesized) | FAIL | `MISSING_ATTESTATION` |
| Loreley | PASS (14/14 agreeing) | FAIL | `MISSING_ATTESTATION` |

Three of the four runtimes are therefore excluded from the main arm **because a token is missing,
not because a number is wrong**. `qualification.json` reports that as a separate top-level block,
`rejected`, alongside `unproven`:

* `unproven` — the evidence has not been produced yet (e.g. the ATTEMPTED bridges, the
  unreconciled closure records, the open route choice).
* `rejected` — an axis was decided **against** the runtime: `kapso`, `eve`, `loreley` on
  `a0_1_attested`, each with `identity_verdict = MISSING_ATTESTATION`.

`eligibility.py`'s self-test also enforces the asymmetry in data: no threshold vector may list
`FAIL` in any `*_allowed` set.

### 1.2 What each component means and where it comes from

**`a0_1_measured` / `a0_1_adapted`** — `a0/conformance/report.json`,
`runtimes.<r>.qualification.a0_1` plus the rows. `measured` is the count the runner reports for the
measurement axis; `adapted` is the subset that agrees only because the **adapter supplied**
semantics the interface cannot represent (`SYNTHETIC_DECLARED`). EvE is `5/14` measured: its lane
maps every evaluation exception to `failure_score(0.0)` and cannot express `invalid`/`error`, so the
9 non-`ok` rows of `C*` were reconstructed from side channels by the adapter — evidence for
`C_adapt`, never for `C_measure`.

**`a0_1_attested`** — the acceptance axis, read from the D3 runner's own per-runtime check
`runtimes.<r>.checks[check_id=measurement-attestation]` (see §3). SimpleLoop: `ok=true`,
`required=true`, 14 rows echo the token, `executed_identity` recorded, harness run
`a01-reference-20260921T171439`. The other three: `ok=false`, `required=true`, 14 rows
`MISSING_ATTESTATION`.

**`a0_2_mechanism`** — does the runtime consume scores per its claimed selection semantics?
SimpleLoop `a0/runtimes/simpleloop/out/a02/a02_checks.json` (9/9); KAPSO
`a0/runtimes/kapso/runs/a0-01/a02/a02.json` (14/14 over 5 scenarios, through real KAPSO selection
code); EvE the sampled-selection frequency test with the auditor's own 3000-draw replication
(`a0/verify/out/eve_a02_replication.json`); Loreley `a0/runtimes/loreley/out/a02.json` (7/7). All four
independently `ACCEPTED` as claims C4.4 / C4.1 / C4.2 / C4.3. Two carry caveats (KAPSO's tie-break
divergence, EvE's sampler-only scope).

**`a0_2_bridge`** — the same path inside the runtime's **own real campaign**. KAPSO
`runs/bridge-2round/real/verification.json` → `bridge_verified` (`E*` → `node.score` →
`node_history` → `_select_parent` → `parent_branch`, resumed from a checkpoint in a new process;
C7.1); SimpleLoop `out/cli-lane/codex-live{3,4}/run_meta.json` (agent-authored candidates that `E*`
scored 2.6251746109048 and 2.5414213562373096, and the champion changed on that score; C7.2); EvE
three real codex-backed rounds that reached iteration-complete but never wrote back an agent-authored
`solution.py` → `ATTEMPTED`; Loreley a real planning call (144.1 s) with the coding call over budget
→ `ATTEMPTED`.

**`closure`** — the `a0/closure/*.json` record, reconciled by `closure.reconciliation.json`.
`CLOSED` only where the top-level verdict *and* study verdict are both closed (SimpleLoop's shipped
codex `workspace-write` argv). Where a mechanism is probe-proven closed but the shipped default is
not, the value is `CONDITIONAL` with the mechanism lists attached (KAPSO, EvE, Loreley).

**`mrc`** — D2 clause 6. Each runtime must be covered by a declaration under `a0/mrc/declarations/`
that **validates** against `a0/mrc/frozen_routes.json`; validation is re-derived at build time by
`python3 a0/mrc/mrc.py validate` (exit 0). All four are covered and frozen. Where more than one
covering route validates — everything except SimpleLoop — the component carries an open caveat: the
A1 route *choice* among them is not frozen here.

## 2. The predicate, as data

`RULES` and `THRESHOLD_VECTORS` in `eligibility.py` are the single source of truth;
`qualification.json` carries a byte-identical copy and `verify_qualification.py` asserts the two agree.

```
Eligible(r; T) = R0 and R1 and R2 and R3 and R4 and R5 and R6 and R7

R0_coverage          total > 0  and  measured + adapted == total  and  state in {PASS, PARTIAL}
R1_measure_floor     measured >= required_measured(T, total)
R2_adapted_declared  adapted == 0  or  a0_1_adapted.all_declared_synthetic
R3_a0_1_attested     a0_1_attested.value in T.attested_allowed
R4_a0_2_mechanism    a0_2_mechanism.value in T.mechanism_allowed
R5_a0_2_bridge       a0_2_bridge.value in T.bridge_allowed
R6_closure           closure.value in T.closure_allowed
R7_mrc               mrc.value in T.mrc_allowed

required_measured(T, total) = T.measured_floor.value                if kind == "rows"
                            = ceil(T.measured_floor.value * total)  if kind == "fraction"
```

Every rule is a total function of `Q_r` × thresholds and **fails closed**: an absent, empty or
out-of-domain component makes its rule false. Nothing is averaged or weighted, and no rule defaults
to true.

| vector | role | measured floor | attested | mechanism | bridge | closure | mrc |
|---|---|---|---|---|---|---|---|
| **`T_A1`** (default) | main arm | all 14 rows (`fraction 1.0`) | `PASS` | `PASS` | `PASS` | `CLOSED` | `FROZEN` |
| `T_exploratory` | integration / pilot / debug | ≥ 1 row (`rows 1`) | `PASS`, `UNPROVEN` | `PASS` | `PASS`, `ATTEMPTED` | `CLOSED`, `CONDITIONAL` | `FROZEN`, `PRESENT_UNFROZEN` |

**Leniency is about missing evidence, never about rejected evidence** — `UNPROVEN` is tolerated by
`T_exploratory`, `FAIL` is not, under any vector. That is why the exploratory set is not larger than
the main set today: the three other runtimes moved from *unproven* to *rejected*, and a rejection is
not softened by being called exploratory.

`T_exploratory` also carries, in data, `may_be_used_for: [pilot, integration, debug]` and
`must_not_be_used_for: [a1_main_arm, a0_freeze, …]`, and `eligibility.py` fails its own self-test if
the default vector is ever anything but `T_A1`.

### The screen is a different object

`|R_1| >= 1` (`plan:490`) is a **candidate screen**: *may the study continue at all?* It uses the
runner's **acceptance** state, so a runtime that measured every row but did not attest it is not in
it. `Eligible(r)` asks *may **this** runtime's numbers be used in an A1 statistic?*

```
verdicts.a0_1            = {simpleloop: "PASS (14/14 measured)", kapso: FAIL, eve: FAIL, loreley: FAIL}
verdicts.n_pass/n_partial/n_fail = 1 / 0 / 3
r_1_a0_1_only            = ['simpleloop']
screen passes            = true
R_A1^main                = ['simpleloop']
```

The `screen.r_1_derived_if_a0_2_mechanism_counts` field is deliberately computed from the
**measurement** axis instead, and says so: it is an upper bound showing what the screen would be if
it ignored acceptance. The two must not be silently swapped.

## 3. `a0_1_attested`: the D3 interface

The observational-equivalence fixture (`a0/fixtures/observational-equivalence/`) constructs an `E'`
that agrees with `E*` **bit-for-bit on all 14 members of `C*`** and was accepted by the behavioural
checker, including when it omitted the identity fields. No in-band behavioural evidence closes that
class, because the thing calling `E*` is the adapter and its reported identity is a *statement*, not
a *measurement*. So the identity became a harness measurement.

**The wiring is now confirmed by real output, not by reading the source.** The prediction made
before D3 produced its report was `runtimes.<r>.checks[check_id=measurement-attestation]`, read from
`conformance.py`'s `evaluate_runtime`. That is exactly where the report now carries it, with the
fields the contract names (`required`, `ok`, `envelope{path,sha256,nonce,harness_run_id,tokens}`,
`attested_candidates`, `missing_attestation_candidates`, `missing_identity_candidates`,
`mismatch_attestation_candidates`, `rows_with_oid`). **No change to `record_sources` was needed.**
The runner also publishes the same verdict a second time at
`runtimes.<r>.qualification.a0_1.attestation.identity_verdict` (`ATTESTATION_OK` /
`MISSING_ATTESTATION`); the consumer takes the **decision** from the check and the **name** from the
qualification block, so `Q_r` reports the runner's own vocabulary.

Sources are tried in the order declared in `attested-a0-1.contract.json`; the first that *decides*
wins, and a source that is present but inconclusive is recorded as rejected and the next is tried:

1. *(preferred)* the runner's per-runtime `measurement-attestation` check;
2. `runtimes.<r>.qualification.a0_1.attestation`;
3. standalone files under `a0/conformance/attested/<r>/`, `a0/envelope/out/attested/<r>/`, and this
   directory's own drop box `a0/qualification/evidence/a0_1_attested/<r>/` — a file record must pin
   the current `report.json` sha256, so a re-run invalidates stale attestations.

Domain: **`PASS`** (positive verdict, `required=true`, and the executed-bytes identity / OID
material present), **`FAIL`** (a negative verdict — `NOT_SUBMITTED`, `MISSING_ATTESTATION`,
`MISSING_IDENTITY`, `MISMATCH_ATTESTATION`: being asked and not answering to the standard is a FAIL,
not an UNPROVEN), **`UNPROVEN`** (no source decided, including a run made with the requirement off).
Forbidden: inferring identity from behavioural agreement on `C*`; an adapter self-report with no
harness reference or OID; treating a missing attestation as "fine"; treating a `required=false` run
as attested; and replacing the runtime's own evaluation path with a harness subprocess (all four
runtimes invoke the evaluator themselves).

`build_qualification.py --self-test` exercises the resolution on synthetic payloads — 15 cases across
a positive verdict with and without identity/OID material, a contradiction, `NOT_SUBMITTED`,
omission, an out-of-domain verdict, all four states of the runner's own check (passing, failing on a
missing token, `required=false`, `ok` with no harness run), and, in a real temp tree through
`a01_attested`, a standalone record that is stale, fresh, contradictory and OID-less.

## 4. The freeze mechanism

`freeze.py`. A frozen vector records, per runtime, each component's value **and its own sha256**,
plus the sha256 of **every artifact** the component was derived from — 48 of them: this directory's
own code and contract, the conformance runner and its fixture runner, the D3 envelope module and its
declared execution set, the measurement envelope document the tokens were issued from, the frozen
evaluator and its two companions, the frozen reference table and candidate manifest, the MRC
registry, the closure records, and every evidence file the components cite. Plus the digest of the
predicate module and of the rules/threshold data.

`check` recomputes all of it and reports `FROZEN`(=`MATCHES_ARMED` for an armed document) or the
drift, naming what changed. **Any component change, any artifact byte, any rules change unfreezes.
There is no partial credit.** This is mechanical because a revision pin in this repository was
already broken once by a field rename.

`freeze_id` is a digest over the *state* (`schema`, `stage`, `eid_star`, `predicate`, `components`,
`artifacts`, `artifacts_missing_at_build`, `key_metrics`, `excluded_runtimes`) and deliberately not
over `gates`, `frozen_at`, `reason` or `git_dirty` — a gate detail carries a timestamp, and folding
that in would move the id while the frozen state stood still.

```bash
cd /home/ebt/rsi-dev/a0/qualification
python3 freeze.py fingerprint      # print the fingerprint; writes nothing
python3 freeze.py arm              # record the current tree as A0.freeze.candidate.json (NOT a freeze)
python3 freeze.py gates            # the freeze-readiness gates alone (exit 1 if any is red)
python3 freeze.py check            # does the tree still match the frozen/armed document?
python3 freeze.py self-test        # prove the drift detection mechanically, in a real temp tree
```

`self-test` copies all 48 artifacts into a temp tree and proves, by real byte mutation, that a
one-byte artifact edit is named as `artifact_changed`, that the same edit to the predicate module is
additionally named as `predicate_changed`, that a component value change is named as
`component_changed`, that a deleted artifact is named as `artifact_missing`, and that a tampered
document trips `freeze_id_mismatch`.

### The readiness gates (8, each with an owner)

| gate | kind | owner of the fix | now |
|---|---|---|---|
| `G1_d1_landed` | measurement | D1 workstream | **PASS** |
| `G2_predicate_self_test` | measurement | this directory | **PASS** |
| `G2b_attestation_fails_closed` | measurement | this directory | **PASS** |
| `G3_qualification_matches_evidence` | measurement | this directory | **PASS** |
| `G4_a0_1_rerun_with_attestation_required` | measurement | D3 + `a0/conformance` | **PASS** — the report is the D3 re-run, `envelope.mode=required`, 14 tokens |
| `G5_a0_1_attested` | measurement | the runtime adapters | **FAIL** — KAPSO/EvE/Loreley `MISSING_ATTESTATION` |
| `G6_runtimes_wired_or_excluded` | **decision** | **the coordinator / user** | **DECIDE** |
| `G7_mrc_frozen` | measurement | `a0/mrc` | **PASS** |

6 of 8 pass. `G5` is the evidence statement; `G6` is the human answer to it. Excluding the three
runtimes with a written reason satisfies both; so does wiring their adapters and re-running A0.1.
**This directory does not choose between those.**

### The one command that freezes, and what must be true first

```bash
cd /home/ebt/rsi-dev && python3 a0/qualification/freeze.py freeze \
    --reason "A0 measurement chain frozen for A1 design"
```

Preconditions, all mechanical:

1. D1 landed — done.
2. D3 landed and A0.1 re-run with the envelope required — done (`G4`).
3. Every runtime either wired (its lane echoes the measurement token and attests the bytes it
   executed, then A0.1 re-run) or explicitly excluded with a reason. **Open — `G5`/`G6`.**

`freeze` **refuses** (exit 2) while any gate is red, listing them with their owners, and never falls
back to a partial freeze. `--force` exists and records the red gates in the document. If
`R_A1^main` is empty the command requires a non-empty `--reason` and prints a warning. It writes
`A0.freeze.json`, commits it and creates the annotated tag (default `a0-frozen`; `--no-tag` prints
the three git commands instead). **This workstream has not cut the tag.**

## 5. `C_measure` vs `C_adapt`

* **`C_measure`** — can the *runtime's* evaluator interface faithfully represent `E*`'s outcome
  algebra, i.e. distinguish `ok` / `invalid` / `error` and carry the failure kind?
* **`C_adapt`** — can the *adapter* supply the semantics that interface cannot represent?

A semantic gap in the runtime's interface, not a statement about whether an adapter is in the loop.
A row the adapter had to reconstruct is evidence for `C_adapt` and **never** for `C_measure`, which
is why the two are separate components rather than one number. EvE is the only runtime where they
diverge: its native lane returns `{"score": 0.0, "summary": "evaluation failed"}` verbatim for any
swallowed exception, so on 9 of the 14 members of `C*` there is no native measurement at all.

**Operational consequence for A1** (`c_measure_vs_c_adapt.a1_consequence`): EvE's native numbers must
not be used in any statistic that needs to distinguish `invalid`/`error` from a genuine zero.
`c14_near_zero` is a *genuine* `2.6e-05`, and conflating the two is the false green the trap exists
to catch.

## 6. UNPROVEN and rejected, and what would settle each

`qualification.json` → `unproven` (evidence not yet produced) and `rejected` (an axis decided
against the runtime). Nothing is hidden inside a passing component.

| what | status | how to settle it |
|---|---|---|
| **KAPSO / EvE / Loreley A0.1 acceptance** | **REJECTED** — `MISSING_ATTESTATION` on 14/14 rows, with the token requirement ON | wire the lane: echo the harness OID and attest the evaluator bytes, candidate bytes and behaviour digest (see `a0/attested-a0-1.contract.json`, `a0/envelope/README.md`), then re-run A0.1. **Or** exclude the runtime with a written reason. This is open decision `G6` |
| EvE completes a real campaign round (bridge) | **ATTEMPTED** — 3 attempts, none wrote back | `a0/runtimes/eve/tools/run_one_eve_iteration.py --run-dir a0/runtimes/eve/out/run006 --turns 14 --turn-timeout 660 --max-seconds 1080`, then require a post-round solver whose `e_star_candidate_source_sha256` is not `18bacee4…` |
| Loreley completes a real campaign round (bridge) | **ATTEMPTED** — planning real, coding over budget | `cd a0/runtimes/loreley && timeout 1200 ./llm-round/run_bounded_round.sh` with a coding budget that fits the cap |
| KAPSO applies the A0-wide **frozen tie-break** | **UNPROVEN** (and measured false under reordering) | already measured in both proposal orders (`runs/tie-order-probe/outcome.json`); what remains is a *contract* decision on whether the frozen tie-break is required of KAPSO at all |
| the A1 route *choice* among covering MRC routes | **OPEN** (KAPSO, EvE, Loreley each have two) | record the chosen lane per runtime in the freeze document |
| the closure verdicts reflect the 2026-09-21 proxy topology | **NOT RECONCILED** — `a0/closure/*.json` are dated 2026-09-20 | re-run the per-runtime closure verdicts against the `docker --internal` + allowlist-proxy topology |

## 7. Re-running this

```bash
cd /home/ebt/rsi-dev/a0/qualification

python3 eligibility.py --self-test          # the predicate on hand-built vectors (18 cases x 2 vectors)
python3 eligibility.py --main-arm           # R_A1^main and, per runtime, which clauses block it
python3 build_qualification.py              # regenerate qualification.json from the evidence
python3 build_qualification.py --check      # re-derive and diff; exit 1 on drift
python3 build_qualification.py --self-test  # the D3 attestation resolution fails closed
python3 verify_qualification.py             # independent consistency check: 26 assertions
python3 freeze.py self-test                 # mechanical drift detection, in a temp tree
python3 freeze.py gates                     # freeze readiness, with the owner of each red gate
python3 freeze.py check                     # current tree vs the frozen/armed document
```

**Live inputs owned by other workstreams.** `qualification.json` is derived from
`a0/conformance/report.json`, `a0/mrc/declarations/*.mrc.json`, `a0/closure/*.json` and
`a0/verify/verdicts.json`. During this session the MRC declarations were regenerated mid-flight and
the check went red until they were re-derived — which is the mechanism working, not a defect. After
any of those move: `python3 build_qualification.py && python3 build_qualification.py --check`, then
`python3 freeze.py arm` to re-baseline.
