# `a0/envelope` — the behaviour/execution-environment split (D1) and the measurement token (D3)

Owner: the D1+D3 workstream. Files: `envelope.py` (the library, standard library only),
`execution-set.json` (the declared allowed execution set), `selftest.py` (executed proof),
`out/` (its own artifacts: `out/selftest_report.json`, `out/attested/<runtime>/<run>.json`).

Two mechanisms, one place, because the harness (`a0/conformance/conformance.py`) and a runtime
adapter must compute the same numbers and neither may drift from the other.

## 1. Why this directory exists

`E*`'s own `canonical_digest` (`a0/tasks/circle-packing/e_star.py:654`) hashes the whole Outcome
payload **including `interpreter`**. That single digest was doing two jobs, and conflating them
produced two measured defects:

* **too strong** — a byte-identical `E*` run under `python3.14` instead of the pinned
  `python3.12.11` was reported as `MISMATCH_DIGEST`, i.e. "the evaluator's behaviour disagrees",
  with `delta = 0.0` on every row. Two independent verifiers reproduced it
  (`a0/verify/sprint-evidence/VERDICT.md` §"the python3.14 false red";
  `a0/fixtures/observational-equivalence/REPORT.md` §2.3).
* **too weak** — the field is optional and self-reported, so an adapter that omitted it was silently
  waived and one that asserted the frozen value while running something else was accepted.

D1 answers the first, D3 the second. Neither edits `e_star.py`, `EID*`, or any adapter's evaluator.

## 2. The projection (D1)

`canonical_digest` covers `|payload|`; the projection splits that payload:

```
behaviour_payload(outcome)  = outcome minus {"canonical_digest", "interpreter"}
behaviour_digest(outcome)   = sha256("a0.envelope.behaviour/v1" ‖ 0x00 ‖ canonical_json(behaviour_payload))
interpreter                 = outcome["interpreter"]                 -> compared separately
```

Domain-separated, so a behaviour digest can never be mistaken for a `canonical_digest`. The
canonicalisation is **`E*`'s own** (`json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True)`
plus a trailing newline, `e_star.py:109`) — `selftest.py` proves it reproduces the frozen table's
`canonical_digest` for all 14 members of `C*` *before* anything relies on it.

Verdicts (`conformance.py` maps these onto rows):

| situation | verdict | accepting? |
|---|---|---|
| behaviour agrees, interpreter is the pinned one | `PINNED` (the row keeps its ordinary verdict) | yes |
| behaviour agrees, interpreter is in the declared allowed set but not pinned | `EXECUTION_ENV_DRIFT` | **yes** — an environment difference, never "behaviour disagrees" |
| behaviour agrees, interpreter outside the declared allowed set | `MISMATCH_EXECUTION_ENV` | no |
| the behaviour payload itself differs | `MISMATCH_DIGEST` | no |

Two routes into the comparison, so every adapter written before this change is still measurable:

1. **payload** — the row submits the Outcome it produced (`e_star_outcome`, schema
   `e_star.outcome/v1`). The checker projects it with this module's own code.
2. **interpreter substitution** — the row submits only a `canonical_digest` (all pre-existing
   adapters). `digest_with_interpreter(frozen_outcome, X)` re-applies `E*`'s own digest scheme to
   the *frozen* payload with interpreter block `X` substituted; a match proves the payload differs
   from the frozen one in the interpreter block and nowhere else. `X` is tried for every interpreter
   in the declared set, plus whatever the row itself declares.

### The projection does not rescue a different evaluator (both directions, executed)

`python3 a0/envelope/selftest.py` runs, for every member of `C*`: the frozen `E*` under the pinned
interpreter, the frozen `E*` under `/usr/bin/python3.14`, and the mutant `E'` from
`a0/fixtures/observational-equivalence/e_prime`. Result (`out/selftest_report.json`):

| | pinned | 3.14.7 | mutant `E'` |
|---|---|---|---|
| behaviour digest vs the frozen one | equal 14/14 | equal 14/14 | **differs 14/14** |
| `canonical_digest` vs the frozen one | equal 14/14 | differs 14/14 | differs 14/14 |
| verdict | `PINNED` | `EXECUTION_ENV_DRIFT` | `MISMATCH_DIGEST` |
| objective float bits | identical | identical | **identical** |

The last row is the point: `E'` is bit-identical on the objective, on `status` and on
`failure.kind`, and the projection still rejects it, because its Outcome payload is not `E*`'s (its
`evaluator_source_sha256` is its own). `E*`'s `evaluator_source_sha256` is inside the behaviour
payload on purpose: A0.1 measures "ran these bytes", not "computes this function" (the fixture's R6).
The same conclusion through the checker, with the fixture's own adapter:
`eplus_mut_own` = `MISMATCH_DIGEST` on 14/14.

## 3. The declared allowed execution set (D1) — and the question it leaves open

`execution-set.json` declares the **pinned** interpreter (`cpython 3.12.11`, the environment
`E_STAR.json` was measured under) and the **sanctioned** set (that one plus `cpython 3.14.7`,
re-measured equivalent on all of `C*` — behaviour payload byte-identical 14/14, and `E*`'s own
digest recomputed under the 3.14.7 interpreter block reproduces the digest the 3.14.7 run emitted,
14/14). Membership is a *measurement*, not a claim; the residual risk is recorded there too (3.11
and earlier are plausible-but-unmeasured sources of numeric drift and are deliberately **not**
sanctioned).

**The coupling question is documented and left undecided** (external review D1:
"document it, do not decide it"). If this set were folded into `EID*`'s `Config`, then *broadening*
it would change `Config`'s digest and therefore `EID* = 664115e0…9328`: a re-freeze of every frozen
document, the reference table, and every adapter's `EID_r` derivation. It would also make the
sanctioned set self-referential, since the equivalence measurement for a new interpreter has to run
*under* some interpreter. Three options are listed in
`execution-set.json:coupling_question_UNDECIDED` (`status: "documented, NOT decided"`); none is
chosen here. The report carries the same note at `report.json:execution_set.coupling_question`.

## 4. The measurement token (D3)

```
OID       = sha256("a0.envelope.measurement_token/v1" ‖ 0x00 ‖ compact_canonical_json(binding))
binding   = {candidate_id, candidate_sha256, eid_star, theta_e, behaviour_digest,
             canonical_digest, interpreter, evaluator_source_sha256, harness_run_id, nonce}
```

The harness issues one token per member of `C*` from **its own** `E*` sweep, into its own state root
(`a0/conformance/out/envelope/measurement_tokens.<run>.json`, one immutable file per sweep,
`issue_envelope`). Every adapter row must
carry the token for its candidate **and** attest the bytes it used:

```jsonc
"measurement": {
  "schema": "a0.envelope.measurement_attestation/v1",
  "oid": "<the harness token for THIS candidate>",
  "harness_run_id": "a01-reference-…", "nonce": "…",
  "eid_star": "664115e0…",
  "evaluator_source_sha256": "<measured from the files this lane executed>",
  "candidate_sha256": "<the candidate bytes this lane read>",
  "behaviour_digest": "<behaviour_digest of the Outcome it produced>",
  "interpreter": {"implementation": "cpython", "version": "3.12.11"},
  "theta_e": {"seed": 1337, "fidelity": "full", "fraction": 1.0, …}
}
```

The runner hands the path over as **`A0_ENVELOPE`**; `--envelope <path>` is accepted by adapters
that declare the flag. The environment variable is the mechanism, for a measured reason: an
adapter whose subcommand parser rejects an unknown flag would fail to launch, and "the runner broke
it" is a different finding from "this runtime is not wired".

Checked by `conformance.py` against **harness-owned** facts (the token's binding, the frozen
`E_STAR.json:evaluator.evaluator_source_sha256`, the `C*` manifest's candidate bytes):

| row | verdict |
|---|---|
| no token | `MISSING_ATTESTATION` |
| a token the harness did not issue for this candidate (foreign, stale, invented) | `MISMATCH_ATTESTATION` |
| token present, no evaluator/candidate/behaviour identity | `MISSING_IDENTITY` |
| identity contradicts the harness's own measurement | `MISMATCH_ATTESTATION` |

All four are **non-accepting even when every number agrees** — the fail-closed rule D3 asks for. The
token requirement is on by default; `--envelope off` turns it off and the report says so
(`envelope.required = false`), because a run that did not require the token has established
nothing about identity and must not be quoted as though it had.

`selftest.py` proves the binding: an OID recomputes, tokens differ per candidate, and changing the
candidate bytes, the behaviour digest, EID*, theta or the nonce each changes the OID — so a row
cannot borrow another measurement's token.

Per runtime, the outcome is also written as a standalone record at
`a0/envelope/out/attested/<runtime>/<run>.json`, pinned to the sha256 of the
`a0/conformance/report.json` it describes (the shape `a0/qualification/attested-a0-1.contract.json`
declares for the D2 consumer; a record stops being evidence the moment the report is regenerated).

## 5. What this does *not* establish

* **Not proof that the attested bytes ran.** The attestation is submitted by the runtime's own lane
  and compared by the harness: it establishes that the row *joins* the harness's measurement and
  that the identity it names is *the frozen one*, not that the named bytes were executed. A lying
  producer can still lie consistently — the fixture's R5, and the `a0/attestation/` workstream's
  self-attestation limit. The next step is producing that attestation **inside** each runtime's own
  session (for KAPSO: inside the session that runs `kapso_evaluation/kapso_eval.py`, because that is
  where its score of record is produced). The conformance-side wiring cost per runtime is a table in
  `a0/conformance/README.md`.
* **Not a replacement for the runtime's evaluation path.** The runtime still evaluates; the harness
  supplies the reference value and the token. No adapter was changed into a subprocess wrapper.
* **Not a decision about the allowed execution set's coupling to `EID*`** — see §3.
* **Not a claim that a behaviour-digest match is implementation identity** — it is a *behaviour*
  match, which is exactly why D3 exists alongside it.

## 6. Using the library

```python
import sys; sys.path.insert(0, "a0/envelope")
import envelope as env

env.behaviour_digest(outcome)                       # D1 projection
env.digest_with_interpreter(outcome, {"implementation": "cpython", "version": "3.14.7"})
env.evaluator_source_digest("a0/tasks/circle-packing")   # E*'s own scheme, recomputed from bytes
env.load_execution_set(); env.classify_interpreter(block, execution_set)
env.load_envelope(path); env.token_for(envelope, candidate_id); env.token_oid(binding)
```

Both the checker and SimpleLoop's adapter import this module by path rather than reimplementing the
formulas, so the comparison cannot drift. Verification:

```bash
python3 a0/envelope/selftest.py        # all checks executed; writes out/selftest_report.json
python3 a0/envelope/selftest.py --quick   # canonicalisation + token only (skips the E* / E' runs)
```
