# `a0/conformance` — A0.1 cross-adapter conformance runner

Answers A0.1 for the whole study: *if every runtime adapter is pointed at the same frozen
evaluator `E*` and the same fixed candidate set `C*`, does it produce the same numbers — and the
same verdicts for the candidates that have no number?*

Protocol: `plan:513-519` (the acceptance formula; `EID_r` derived from `EID*`; `theta_E` identical
across wrappers), `plan:490` (A0 is a candidate screen: `|R_1| >= 1` to continue), `plan:528`
(`F_r(E*) = scalar(E*)` in round one), `plan:551-552` (the two false-green traps). Frozen
coordinates come from the binding decisions in `a0/tasks/circle-packing/README.md` and
`EID_INPUTS.json`.

## Files

| file | what it is |
|---|---|
| `conformance.py` | the runner: `reference`, `run`, `show`. Standard library only |
| `report.json` | **the deliverable**: per-runtime A0.1 verdict, the runtime × candidate table, findings, EID\* checks, integrity, and the per-runtime handoff block |
| `report.md` | the same report as a readable table |
| `reference.json` | the runner's own fresh `E*` sweep over `C*`, cross-checked against `E_STAR.json` |
| `selftest.py` | fault injection: drives 20 fixture adapters (19 injected faults + the honest control) and asserts the verdict each must get, plus the integrity-abort path |
| `selftest_report.json` | the self-test result (fixture, injected fault, expected vs actual verdict) |
| `selftest_runner_report.json` / `.md` | the full runner report of the self-test run |
| `fixtures/adapters/reference_adapter.py` | an honest fixture: really executes `E*` on all 14 members of `C*`. The template an adapter should follow. **Not** a runtime |
| `fixtures/adapters/deviant.py` | one named fault per `--mode` |
| `adapters.json` | optional entry-point registry, for an adapter layout discovery does not recognise |
| `out/envelope/measurement_tokens.<run>.json` | **the measurement envelope** the runner issues from its own `E*` sweep: one OID measurement token per member of `C*` (external review D3). One immutable file per sweep (the newest 3 are kept), so a later sweep can never replace the file an existing report names |
| `a0/envelope/` (sibling) | the projection (behaviour vs execution environment, D1) and the token scheme (D3), plus the declared allowed execution set and their self-test |
| `out/evidence-d1d3/` | the executed acceptance evidence for D1/D3: `index.json` (each entry names its command), the fixture-row reports, and the `reference --python python3.14` sweep |
| `out/` | raw adapter stdout/stderr/exit codes, the `E*` outcome files, per-run dirs (pruned to the latest per runtime) |

## Running it

```bash
cd /home/ebt/rsi-dev/a0/conformance
python3 conformance.py reference                                          # fresh E* sweep vs the frozen table
python3 conformance.py reference --python /usr/bin/python3.14 --out /tmp/reference.py314.json   # D1: the same E* under another interpreter
python3 conformance.py run --envelope off                                 # D3 off: exploratory run, marked as such in the report
python3 conformance.py run                                                # all four runtimes + controls
python3 conformance.py run --runtimes kapso --out report.kapso.json       # one runtime (subset runs are auto-redirected away from report.json)
python3 conformance.py run --eid-document proposed --out report.proposed.json   # old EID* document
python3 conformance.py run --runtimes simpleloop --out report.simpleloop.json
python3 selftest.py                                                       # prove the checker rejects each fault
```

Exit codes: `0` = no FAIL (runtimes may be `PASS` or `PARTIAL`); `2` = no FAIL but at least one
PENDING/BLOCKED; `3` = at least one FAIL; `4` = candidate-set integrity abort; `10` = runner bug.
A `PARTIAL` runtime is a qualification, not a failure, so it does not change the exit code.

## What the runner does

1. **Integrity first** (`adapter_contract.md` §2.2). Recomputes `sha256(solution.py)` for all 14
   members of `C*` against `manifest.json` and **aborts with exit 4 before evaluating anything**
   on a mismatch. Verified by execution: `selftest.py` builds a tampered manifest off to the side,
   the runner exits 4 and names `c04_near_tie`.
2. **`E*` reference sweep.** Runs the frozen invocation (`.venv/bin/python e_star.py evaluate
   --candidate C_STAR/<id> --seed 1337 --fidelity full --fraction 1.0 --n 26 --runs 5
   --runtime-budget-ms 250.0 --timeout-s 120.0 --out … --state-dir …`) over every member and
   checks the result against the frozen table `E_STAR.json`: exit code, status, `canonical_digest`,
   objective **bit-for-bit**, and `failure.kind`. It also digests the whole `C*` tree before and
   after, so "`E*` never writes inside a candidate worktree" is measured rather than asserted.
3. **EID\* checks.** `evalcontract.py recompute` (filesystem-free), `evalcontract.py verify`
   (`--base a0/`), and a check that every EID document on disk carries the binding `EID*`.
4. **Issues the measurement envelope.** From the same sweep it writes, into its own state root, one
   OID measurement token per member of `C*`, binding `(candidate_sha256, EID*, theta_E, behaviour
   digest, run nonce)` and the evaluator source digest the harness measured. It hands the path to
   every adapter as `A0_ENVELOPE` (`--envelope <path>` is accepted by adapters that declare the
   flag; the environment variable is the mechanism because a subcommand parser that rejects an
   unknown flag would make "the runner broke it" indistinguishable from "this runtime is not
   wired"). `--envelope off` turns the requirement off and is recorded in the report as an
   exploratory run (`envelope.required = false`), never as an attested one.
5. **Drives each adapter** through the frozen CLI, then compares the adapter's numbers against
   `E_STAR.json` **itself**. Everything the adapter says about itself is recorded under a key whose
   name states it is untrusted — `adapter_claim__untrusted` (its own A0.1 "verdict" string) and
   `adapter_self_declaration__untrusted` (its declared outcome, blocked reason, row count) — and is
   never the runner's verdict. The `__untrusted` suffix is deliberate: an adapter's self-claim must
   not be mistakable for a verdict in the machine-readable document, so no key that carries a bare
   `PASS`/`FAIL` under a verdict-shaped name belongs to the adapter. An adapter that reports
   "A0.1 ok" for a crash recorded as `0.0`
   fails on the comparison. For a candidate `E*` did not accept, the compared surface is the
   **verdict and `failure.kind`** (`adapter_contract.md` §4.3.5), so a runtime cannot pass by
   repeating `invalid`/`error` truthfully while lying about *why* it failed.
6. **Per-runtime PASS / PARTIAL / FAIL / PENDING / BLOCKED**, each runtime in its own try/except and
   its own subprocess: one runtime's failure can never abort another's run (`plan:490`). A runtime
   that was never driven is `PENDING`, never "passing"; a runtime whose rows agree only on
   adapter-supplied semantics is `PARTIAL`, never "passing".

### The adapter invocation (exactly what the runner sends)

```bash
<adapter cmd> conformance \
  --runtime <r> \
  --candidate-set /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/manifest.json \
  --eid /home/ebt/rsi-dev/a0/contract/out/plumbing.EID.json \
  --theta seed=1337,fidelity=full,fraction=1.0,n=26,runs=5,runtime_budget_ms=250.0,timeout_s=120.0 \
  --epsilon 1e-09 \
  --out /home/ebt/rsi-dev/a0/conformance/out/adapters/<r>.conformance.json
```

`--eid` is the **canonical, contract-owned** document `a0/contract/out/plumbing.EID.json`
(same `EID* = 664115e0…`, and the only document `evalcontract.py verify --spec
a0/contract/plumbing.contract.json` resolves without a path override). `--eid-document proposed`
selects the task-side copy `a0/tasks/circle-packing/plumbing.EID.proposed.json` instead — the
pre-repoint default, kept for comparability with older reports; a path is accepted too. The
runner records which document it handed over (`frozen.eid_document_name`,
`frozen.eid_document_sha256`, and per runtime `runtimes.<r>.eid_document_supplied`) and fails the
`EID-document-as-requested` check if the requested document could not be used.

If that produces no usable document, the runner falls back to `<adapter cmd> run …` (the §3 `run`
form, with `--fr a0/contract/fr/scalar.json`,
`--budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1`, `--traces score,selection,resource`)
and reads `outcome.fields.sum_radii` plus `evaluator_evidence` from the score trace. That path is
**weaker and cannot pass A0.1 on its own**: a score trace carries neither `eid_r`, nor `theta_E`,
nor `E*`'s `ok|invalid|error` verdict, so the identity half of A0.1 stays unestablished
(`plan:517-519`). The report says so (`evidence_source`, `fallback`).

`<adapter cmd>` is discovered (override with `--adapter <r>="<cmd>"`, or an entry in
`adapters.json`):

1. `<adapter_dir>/adapter.json` (or `config/adapter.json`) → `{"cmd": [...], "pythonpath": "..."}`
   — the recommended, unambiguous way
2. `<adapter_dir>/{a0_adapter,adapter,main,cli}.py`, or an executable in `<adapter_dir>/bin/`
3. a package `a0_adapter` or `adapter` (with `__init__.py`) under `<adapter_dir>` or
   `<adapter_dir>/src`, using `__main__.py` → `python -m <pkg>`, else `cli.py`/`main.py` →
   `python -m <pkg>.<mod>`
4. otherwise `python -m a0_adapter` with the adapter's own venv, reported as a *guess*

The runner launches with `cwd = <adapter_dir>` and `<pythonpath or adapter_dir>` prepended to
`PYTHONPATH` — mirroring `uv run --project <adapter_dir>` — and passes only absolute paths, so the
adapter still must not depend on cwd or PATH (`plan:544`). Every launch, exit code and stderr tail
is in `report.json` under `runtimes.<r>.conformance_invocation` / `.adapter`; the raw bytes are in
`out/adapters/`. When discovery finds nothing runnable it reports `PENDING` and names the entry
points it looked for.

## What the adapter must report

The frozen shape is `a0.adapter.conformance/v1`; the README of each adapter should say what it
emits. The reader is deliberately alias-tolerant, because the two adapters that exist now each
published their own spelling, and a partly finished adapter must stay *measurable* rather than be
silently skipped. Accepted today:

* rows at the top level under `candidates` / `results`, **or** inside a section object
  (`a01`, `conformance`, …) — `adapter_rows_section` records which;
* the runtime-side number as `substrate.scalar` (simpleloop), `runtime_scalar` (eve), or
  `objective.value` / `objective_value` / `e_r` / `value` / `score` / `scalar`;
* the runtime-side verdict as `substrate.status` / `runtime_status` / `status`;
* `theta_E` or `theta_e`, with `n`/`runs`/… allowed under `extra`;
* evidence as `evaluator_evidence`, or as the flat `runtime_evidence_status` +
  `runtime_evidence_detail` pair;
* the candidate's identity as `substrate.candidate_source_sha256` / `solution_sha256` /
  `score.e_star_candidate_source_sha256`, and `substrate.canonical_digest` /
  `score.e_star_canonical_digest`.

Aliases never relax the comparison: the numbers are still checked against `E_STAR.json`, and the
adapter's own verdict is recorded only as `adapter_claim__untrusted` — never used as the runner's,
and never under a name a consumer could join on as a verdict.

```jsonc
{
  "schema": "a0.adapter.conformance/v1",
  "runtime": "eve",
  "eid_star": "<64-hex>",                      // EID* verbatim (plan:509)
  "eid_r": {                                   // the EID_r -> EID* mapping (plan:517)
    "value": "<64-hex>",
    "native_scheme": "none" | "manifest_fingerprint" | "evaluator_name_version_campaign_program_hash",
    "mapping_mode": "native" | "adapter_declared_injection",
    "derives_from_eid_star": "<64-hex>",
    "declaration": "how the identity is pinned, in words",
    "recomputable": true,
    "recompute_cmd": ["...", "..."]            // preferred: the runner executes it and compares.
  },                                           // OR "derivation": {"domain": "...", "payload_canonical": "..."}
  "theta_e": {"seed": 1337, "fidelity": "full", "fraction": 1.0, "n": 26, "runs": 5,
              "runtime_budget_ms": 250.0, "timeout_s": 120.0,
              "defaults_applied": {}},         // required for any null parameter (plan:518)
  "epsilon": 1e-09,
  "primary_field": "sum_radii",
  "fr": {"name": "F_r = scalar(E*)", "spec_hash": "1fa6f941…"},   // a0/contract/fr/scalar.json
  "candidates": [                              // one row per member of C*, no skipping
    {
      "candidate_id": "c07_single",            // exactly the manifest's join key
      "source_sha256": "…",
      "canonical_digest": "…",
      "status": "ok" | "invalid" | "error",    // E*'s verdict, not the runtime's own
      "objective": {"name": "sum_radii", "value": null, "direction": "max"},
      "exit_code": 2,
      "failure_kind": "invalid_configuration",
      "evaluator_evidence": {"status": "ok", "detail": "fresh E* subprocess run"},
      "theta_e_attempt": {"evaluator": "E*", "fidelity": "full", "fraction": 1.0, "seed": 1337,
                          "granted_class": "full", "commanded_class": "full"}
    }
  ],
  "traces": {"score": "…", "selection": "…", "resource": "…"},
  "failure_stage_counts": {"…": 0}
}
```

**If your `eid_r` carries a `recompute_cmd` (or a canonical recipe), the runner executes it and the
check becomes `executed` instead of the weaker `declared_prose`.** Both existing adapters use
`declared_prose`, which the report marks as such: `recomputable: true` there is the adapter's
declaration, backed by a named recipe, not by an executed check.

## Verdicts and findings

Per candidate:

| condition | verdict |
|---|---|
| `E*` has a number and \|`E_r − E*`\| ≤ `epsilon` | `MATCH` |
| `E*` has no number and the adapter reports the same non-ok verdict, no number, **and the same `failure.kind`** | `MATCH_VERDICT` |
| `E*` has no number, the runtime's lane returned a **declared** synthetic failure (EvE's `failure_score(0.0)`), and the row is not presented as a match | `SYNTHETIC_DECLARED` — acceptable, but its `0.0` is never a measurement |
| \|Δ\| > epsilon | `MISMATCH_VALUE` |
| a number where `E*` reports `null` | `FALSE_GREEN_SYNTHETIC_ZERO` (0.0) or `MISMATCH_NULL` |
| the row's **behaviour** differs from `E*`'s (the Outcome minus `canonical_digest` and `interpreter`) | `MISMATCH_DIGEST` |
| the row's `canonical_digest` differs from `E*`'s **only** in the `interpreter` block, and that interpreter is in the declared allowed execution set | `EXECUTION_ENV_DRIFT` — **accepting**: an environment difference, never "the evaluator's behaviour disagrees" |
| the same, with an interpreter outside the declared allowed execution set | `MISMATCH_EXECUTION_ENV` — non-accepting |
| reported `source_sha256` differs from `C*`'s | `MISMATCH_DIGEST` |
| the row carries no harness measurement token | `MISSING_ATTESTATION` — fail-closed, non-accepting |
| the row echoes a token the harness did not issue for this candidate | `MISMATCH_ATTESTATION` |
| the row echoes the token but attests no evaluator bytes / candidate bytes / behaviour digest | `MISSING_IDENTITY` — non-accepting |
| the attested identity contradicts the harness's own measurement | `MISMATCH_ATTESTATION` — non-accepting |
| truthful `status` but a different `failure.kind` | `MISMATCH_FAILURE_KIND` (`E*` verdict and kind are one surface: `adapter_contract.md` §4.3.5) |
| a non-ok candidate with **no** `failure.kind` declared at all | `UNDECLARED_FAILURE_KIND` — the surface §4.3.5 compares is absent, so the row cannot "agree" |
| the row declares a `failure_stage` that is not the one the frozen §5.3 table maps `E*`'s kind to | `MISMATCH_FAILURE_STAGE` |
| no row for a member of `C*` | `MISSING` → coverage FAIL |

Only `MATCH`, `MATCH_VERDICT`, `SYNTHETIC_DECLARED` and `EXECUTION_ENV_DRIFT` count as agreeing.
But *agreeing* is not the same as *measuring*, so the runtime state is a qualification, not a
boolean:

| state | condition |
|---|---|
| `PASS` | every candidate agrees **and** every check passes **and** every row was measured by the runtime's own evaluator interface (`evaluator_evidence.status` is fresh) |
| `PARTIAL` | every candidate agrees and every check passes, but at least one row agrees only on semantics the **adapter supplied** (`SYNTHETIC_DECLARED`: a declared synthetic failure where `E*` has no number) — that row was not measured |
| `FAIL` | a candidate disagrees, coverage of `C*` is incomplete, a check fails, or a row is not harness-attested (`MISSING_*` / `MISMATCH_ATTESTATION` / `MISMATCH_EXECUTION_ENV`) |
| `PENDING` / `BLOCKED` | nothing was run / the adapter declared itself unable to run |

`PARTIAL` exists because a single global `PASS` is the wrong output: EvE's lane maps every
evaluation exception to `failure_score(0.0)` and cannot represent `invalid`/`error` at all, so its
`A0.1` is `5/14 measured` and must never be reported as a bare `PASS`. The runner therefore labels
every runtime with the measured split and records it machine-readably:

```
verdicts.a0_1                  {"simpleloop": "PASS (14/14 measured)", ..., "eve": "PARTIAL (5/14 measured)"}
verdicts.a0_1_state            {"eve": "PARTIAL"}                  # the enum
verdicts.a0_1_measured         {"eve": 5}                          # rows measured natively
verdicts.a0_1_adapted          {"eve": 9}                          # rows accepted on adapter-supplied semantics
verdicts.a0_1_qualification    {"eve": {"measured": 5, "adapted": 9, "total": 14,
                                        "measured_candidates": [...], "adapted_candidates": [...]}}
verdicts.r_1_a0_1_only         runtimes whose A0.1 is PASS          -> the A0.1 half of the SCREEN
verdicts.r_1_a0_1_partial      runtimes whose A0.1 is PARTIAL       -> deliberately excluded from it
```

A partial runtime is deliberately **not** in `r_1_a0_1_only`, so a sibling's full `PASS` cannot
dilute it. `|R_1| >= 1` is a *candidate screen* ("may the study continue?"); per-runtime
qualification is a different object, declared explicitly by the `Eligible(r)` predicate in
`a0/qualification/qualification.json` (see `a0/qualification/QUALIFICATION.md`). The screen can
pass while no runtime is `Eligible()`.

The distinction behind `qualified` vs `adapted` is `C_measure` vs `C_adapt`: whether the
**runtime's evaluator interface** can faithfully represent `E*`'s outcome algebra, versus whether
the **adapter** can supply the missing semantics. It is a semantic gap in the runtime's interface,
*not* a statement about whether an adapter is in the loop — all four runtimes run through an
adapter. An adapted row is evidence for `C_adapt` and never for `C_measure`.

Findings (`plan:551-552`; `fatal: false` findings inform, they do not fail a runtime):

| finding | fatal | trigger |
|---|---|---|
| `TRAP-SYNTHETIC-DECLARED` | no | the EvE trap was hit, detected and declared (this is the *good* outcome: the 0.0 is distinguishable from `c14`'s genuine near-zero) |
| `FG-EVE-SYNTH` | yes | `synthesized_failure` reported on a row that still claims a match, or where `E*` has a real number |
| `FG-EVE-ZERO` | yes | a `0.0` (or a value within epsilon of it) where `E*` returned `null`, undeclared |
| `FG-LORELEY-CACHE` | yes | `cache_hit` (must name `cached_from_run_id`) — a reused number is not evidence that `E*` ran |
| `FG-LORELEY-TIMEOUT` | yes | `timeout` — a timeout-synthesised failure |
| `FG-LORELEY-TRUNCATED`, `FG-LORELEY-CAP` | yes | `truncated_metrics`, `metrics_truncated`, `metrics_dropped > 0` or `metrics_count > 64` |
| `FG-MANIFEST-TRIPLE` | yes | `granted_class != commanded_class` (`plan:532-539`, KAPSO D16) |
| `FG-ATTEMPT-THETA-DRIFT` | yes | the per-attempt `(fidelity, fraction, seed)` differs from the frozen `theta_E` (`plan:518`) |
| `FG-FAILURE-KIND` | yes | a non-ok candidate whose declared `failure.kind` is not `E*`'s — a truthful `status` with a lying `why` is a false PASS on the staging half of A0.1 (audit R1) |
| `FG-FAILURE-KIND-UNDECLARED` | yes | a non-ok candidate that declares **no** `failure.kind`, so the (verdict, `failure.kind`) surface `adapter_contract.md` §4.3.5 compares is absent — passing vacuously was the hole the auditor found |
| `FG-FAILURE-STAGE` | yes | a declared `failure_stage` that contradicts the frozen §5.3 mapping of `E*`'s kind |

Runtime checks: `EID-star-verbatim`, `EID-r-derives-from-EID-star`, `EID-r-declaration-present`,
`EID-r-recomputes` (+ `recompute_mode`: `executed` / `verbatim` / `declared_prose` / `absent`),
`theta-E-identical`, `E-star-manifest-echo`, `F-r-frozen`, `candidate-coverage`,
`E-r-equals-E-star`, `E-r-failure-kind`, `evidence-fresh-or-declared`, `no-duplicate-candidates`.

Two checks deserve a note:

* **`E-star-manifest-echo`** — many adapters leave `E*`'s own `E_STAR_MANIFEST` line in their
  evidence (e.g. inside a step's error text). The runner parses it out — through however many JSON
  escaping layers — and checks the echoed `evaluator_source_sha256` against `E_STAR.json`'s, the
  echoed `canonical_digest` against the per-candidate reference, and the echoed
  `(seed, fidelity, fraction)` against `theta_E`. EvE's report carries 56 such echoes. KAPSO does
  not keep the line, but publishes the same facts as fields (`registered_channel.manifest`:
  `e_star_canonical_digest`, `e_star_evaluator_source_sha256`, `seed`/`fidelity`/`fraction`), which
  the runner reads as an echo of the `fields` form (`echo_forms` records which form was used).
  Either way this is the closest thing to proof that the *frozen evaluator bytes* ran inside the
  runtime.
* **`E-r-failure-kind`** — for a candidate `E*` did not accept, the contract compares **verdict and
  `failure.kind`**, not just `status` (`adapter_contract.md` §4.3.5). The check reports how many
  non-ok candidates declared a kind at all (`kind_declared_for`), fails the runtime when a declared
  kind disagrees, and fails it too when a non-ok candidate declares **no** kind at all: a row
  without the field cannot "agree", and treating an omission as silence was the residual hole in
  this checker (`UNDECLARED_FAILURE_KIND`, `FG-FAILURE-KIND-UNDECLARED`). Each runtime also carries
  `failure_stage_accounting`: its declared `FailureStage` counts compared against the frozen §5.3
  map applied to `C*` — **recorded, never a verdict**, because the counts may describe a different
  run's units (`matches_frozen_map` is `null` unless the units total 14).
* **`theta-E-identical`** — if an adapter does not declare `theta_E` at all, the runner recovers
  the theta `E*` actually ran at from those echoes and says so, rather than claiming the adapter
  declared it. Several independent echoes that disagree with each other would fail the check: that
  is exactly KAPSO's D16 drift.

## Behaviour is not the execution environment (D1)

`E*`'s own `canonical_digest` (`a0/tasks/circle-packing/e_star.py:654`) hashes the whole Outcome
payload, `interpreter` included. So a byte-identical `E*` under `python3.14` produced a different
digest with `delta = 0.0` on every row, and the checker reported it as `MISMATCH_DIGEST` — "the
evaluator's behaviour disagrees", which was false (two independent verifiers reproduced it). The
checker now splits the two surfaces it conflated, **checker-side**: `e_star.py` and `EID*` are
untouched.

* **Behaviour** = the Outcome payload minus `canonical_digest` and minus `interpreter`. Compared as
  `a0/envelope/envelope.py:behaviour_digest`. The projection never rescues a different evaluator:
  the mutant `E'` of `a0/fixtures/observational-equivalence/` has a different behaviour digest on all
  14 candidates while its objectives are **bit-identical**, and it still fails.
* **Execution environment** = the `interpreter` block, compared separately against the declared
  **allowed execution set** in `a0/envelope/execution-set.json`: pinned `cpython 3.12.11` (the
  environment `E_STAR.json` was measured in) and sanctioned `cpython 3.14.7` (re-measured
  equivalent on all of `C*`). Inside the set → `EXECUTION_ENV_DRIFT`, which is **accepting** and
  reported loudly; outside it → `MISMATCH_EXECUTION_ENV`, non-accepting.
* A row that carries only a `canonical_digest` — every adapter written before this change — is still
  measurable: the checker re-applies `E*`'s own digest scheme to the frozen payload with each
  declared interpreter block substituted (`digest_with_interpreter`), and a match proves the payload
  differs in the interpreter block and nowhere else. A row that submits its Outcome payload
  (`e_star_outcome`) is projected directly.

**Open and undecided, recorded rather than decided:** if the allowed execution set were folded into
`EID*`'s `Config`, then *broadening* it would change `Config`'s digest and therefore `EID* =
664115e0…9328` — a re-freeze of every frozen document, the reference table and every adapter's
`EID_r` derivation. `a0/envelope/execution-set.json:coupling_question_UNDECIDED` states the three
options and chooses none; the user has not decided. Until then the set is a checker-side
declaration, and the report says so (`report.json:execution_set`, and
`runtimes.<r>.checks[behaviour-vs-execution-env]`).

## The measurement token (D3)

Behavioural testing cannot prove implementation identity: a constructed `E'` agrees with `E*`
bit-for-bit on `C*` and was accepted by this checker in three modes (`claim`, `omit`, `twin`).
Identity therefore becomes a **harness measurement**:

1. From its own `E*` sweep the harness issues one **OID measurement token** per member of `C*` into
   its own state root (`out/envelope/measurement_tokens.<run>.json`), binding at least
   `(candidate_sha256, EID*, theta_E, behaviour digest, run nonce)` plus the evaluator source digest
   it measured. The OID is opaque: `sha256("a0.envelope.measurement_token/v1" ‖ canonical_json(binding))`.
2. Every adapter row must **echo that token** and **attest the bytes it used** — evaluator source
   digest, candidate bytes, behaviour digest, interpreter, theta — in a `measurement` (or
   `attestation`/`identity`) block. The runner hands the envelope path over as `A0_ENVELOPE`.
3. The checker compares the attestation against **its own** measurement and the frozen identity
   (`E_STAR.json:evaluator.evaluator_source_sha256`, the `C*` manifest's candidate bytes), and fails
   closed: `MISSING_ATTESTATION` / `MISSING_IDENTITY` / `MISMATCH_ATTESTATION` are all
   non-accepting, even when every number agrees. The runtime's own evaluation path is *not*
   replaced — the runtime still evaluates, the harness supplies the reference and the token.
4. Per runtime the result is also written as a standalone record at
   `a0/envelope/out/attested/<runtime>/<run>.json`, in the shape the D2 consumer contract
   (`a0/qualification/attested-a0-1.contract.json`) declares, pinned to the sha256 of the report it
   describes.

**Limit, stated because it is not closed by this:** the attestation is *submitted by the runtime's
lane*. It establishes that the row joins the harness's measurement and names the bytes it executed;
it is not proof that those bytes were executed (a lying producer). The `a0/attestation/` workstream's
producer, run **inside** the runtime's session, is the step that would close it — for KAPSO
especially, whose score of record must be produced by the session running its own evaluator.

### Evidence, by running it

```bash
# (a) the same E* under 3.14: an environment verdict, not a behaviour mismatch
python3 conformance.py reference --python /usr/bin/python3.14 --out /tmp/reference.py314.json
#   reference table reproduced exactly: True   behaviour reproduced: True
#   execution environment: EXECUTION_ENV_DRIFT (observed cpython 3.14.7, pinned cpython 3.12.11)
#   every per-candidate record: behaviour_reproduced true, canonical_digest_matches false

# (a') through an adapter, with the fixture's own adapter and command shape
FX=/home/ebt/rsi-dev/a0/fixtures/observational-equivalence
python3 conformance.py run --runtimes eplus_control_py314 --envelope off --no-controls \
  --adapter "eplus_control_py314=python3 $FX/adapters/e_plus_adapter.py \
  --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --identity own --python /usr/bin/python3.14" \
  --out /tmp/eplus_control_py314.json
#   eplus_control_py314  PASS (14/14 measured)  rows: 14 x EXECUTION_ENV_DRIFT   (was 14 x MISMATCH_DIGEST)

# (b) the mutant's previously-passing modes now FAIL -- default, envelope required
#   eplus_mut_claim  FAIL  false-green finding(s): MISSING_ATTESTATION
#   eplus_mut_omit   FAIL  false-green finding(s): MISSING_ATTESTATION
#   eplus_mut_twin   FAIL  false-green finding(s): MISSING_ATTESTATION
#   (the same command with --envelope off leaves them PASS: the D1 projection does not close the
#    claim class, which is exactly why D3's token is the mechanism that does)

# (c) no false red: the honest control still passes, and so does SimpleLoop end to end
python3 conformance.py run --runtimes eplus_control --envelope off --no-controls \
  --adapter "eplus_control=python3 $FX/adapters/e_plus_adapter.py --evaluator-dir /home/ebt/rsi-dev/a0/tasks/circle-packing --identity own" \
  --out /tmp/eplus_control.json                      # PASS (14/14 measured)
python3 conformance.py run --runtimes simpleloop --out report.simpleloop.json
#   simpleloop PASS (14/14 measured); measurement-attestation: 14/14 rows echo the harness token

# (d) the four runtimes
python3 conformance.py run
#   simpleloop PASS (14/14 measured)
#   kapso/eve/loreley  FAIL -- not accepting: 14 x MISSING_ATTESTATION (the numbers agree 14/14)
#   controls: control_honest PASS, control_zero_on_error FAIL, control_cache_hit FAIL (as expected)
```

The Python-level proof of both directions of the projection — pinned vs 3.14.7 vs the mutant `E'`
on all 14 candidates, with `E'`'s objectives bit-identical — is `python3 a0/envelope/selftest.py`
(`a0/envelope/out/selftest_report.json`).

### Wiring cost for the three runtimes that are not wired yet

`simpleloop` is wired (`a0/runtimes/simpleloop/a0_adapter/`): `cli.py` gains `--envelope` /
`A0_ENVELOPE`, the envelope is read in `conformance.py:load_envelope`, and each row carries
`measurement` + `e_star_outcome`. The other three are **not** wired, and their rows are reported
non-accepting rather than faked. The seam each would use:

| runtime | seam (path:line) | what it must do |
|---|---|---|
| KAPSO | `a0/runtimes/kapso/a0_adapter/channels.py:152` (`run_registered_channel`, the subprocess that runs the registered command, with the `env_overrides` hook at `:158-165`) and `a0/runtimes/kapso/a0_adapter/a01.py:148` (`runtime.registered_channel_for_branch`) | pass `A0_ENVELOPE` into that session's environment, and produce the attestation **inside the session that runs `kapso_evaluation/kapso_eval.py`** (the registered command) — its score of record must come from that session, so the digest of the bytes it executed has to be measured there and carried out, not recomputed by the adapter afterwards |
| EvE | `a0/runtimes/eve/a0_adapter/eve_runtime.py:76` (`render_step_script`, where EvE's `evaluation.steps` script is generated) and `:496` (`evaluate_candidate_through_eve`), reached from `a01.py:268` (`run_conformance`) | the step script is executed by EvE's own runtime, not by the adapter: the attestation has to be emitted by that execution (the wrapper EvE runs) and echoed onto the row |
| Loreley | `a0/runtimes/loreley/src/a0_adapter/runtime.py:79` (`WORKER_EVALUATOR_PLUGIN` in the worker environment) and `a0/runtimes/loreley/src/loreley_a0_plugin.py:373` (`plugin(...)`, the entry point Loreley's worker calls) and `:253` (`_run_e_star`, where that plugin invokes `E*`) | the plugin is called by Loreley's worker, so the attestation belongs inside the plugin call next to `_run_e_star`, where the executed bytes are known |

Each needs the same three things: read `A0_ENVELOPE`, hash the evaluator + candidate bytes it really
executed, and put the token + identity on every row. Until then their A0.1 is `FAIL` with
`MISSING_ATTESTATION` — evidence-missing, not a verdict on the runtime, and the numbers themselves
still agree 14/14.

## Controls and self-test

`report.json` also carries `controls`: fixture adapters driven through exactly the same checker —
`control_honest` (really executes `E*` on all of `C*`; must PASS), `control_zero_on_error` and
`control_cache_hit` (the two named traps; must FAIL). If a control comes back wrong, the runtime
verdicts in the same report are not trustworthy.

`selftest.py` runs 29 fixtures (28 injected faults + the honest control) covering: an honest
adapter, a no-fault adapter, undeclared
synthetic zero, declared synthetic zero (must be `PARTIAL (5/14 measured)`, never `PASS`),
a mislabeled synthetic zero (must FAIL),
cache reuse, timeout synthesis, metric truncation, a value drift just above epsilon and just below,
the 1e-4 near-tie swap, a digest swap, partial coverage, a manifest-class mismatch, an attempt
theta drift, a stale `EID*`, an undeclared native `theta_E`, a truthful `status` with a lying
`failure.kind` (must FAIL — audit R1), a truthful kind with a mis-staged `failure_stage` (must
FAIL), and the honest fixture with `failure.kind` omitted altogether (must FAIL — the second half of
R1: a vacuous PASS is a hole); and for D1/D3: a sanctioned interpreter drift (must PASS, rows
`EXECUTION_ENV_DRIFT`), an unsanctioned one (must FAIL), no token (must FAIL),
a foreign token (must FAIL), a token with no identity (must FAIL), the `claim` attack with the
mutant's real evaluator digest (must FAIL), the value-identical twin swap (must FAIL), and an
attestation of another candidate's real measurement (must FAIL) — plus the candidate-set integrity
abort (exit 4). The two `PASS`
fixtures also pin the split (`qualification.measured == 14`, `adapted == 0`) and the label
(`PASS (14/14 measured)`), so the measured/adapted accounting cannot silently regress. All of it is
run `python3 selftest.py` in ~10 s.

**Fixtures never write into the study tree.** A fixture is a test double: `fixture_common.
scratch_root()` sends its run artifacts to `$A0_FIXTURE_RUN_ROOT`, which `selftest.py` sets to a
system temp directory it removes afterwards (`--keep-fixture-runs` keeps it) and the runner sets for
its control rows to a temp directory it removes at exit. Before this, the honest fixture defaulted
its run dir to `a0/conformance/out/fixture-runs/`, so every selftest quietly added 30+ MB of
directories to the deliverable's artifact area (audit F6). Verify with
`python3 selftest.py` and `find a0/conformance -name fixture-runs` (empty), or
`--keep-fixture-runs` to inspect the paths the run used.

## Handoff fields for the study's final report

Per runtime, `report.json` → `runtimes.<r>` carries: `state` (A0.1: `PASS` / `PARTIAL` / `FAIL` /
`PENDING` / `BLOCKED`), `qualification.a0_1` (the machine-readable measured/adapted split with the
candidate ids on each side and the `C_measure` / `C_adapt` framing), `checks`, `rows`
(runtime × candidate with `e_star_value`, `e_r_value`, `delta`, both statuses, both
`failure.kind`s, the E\* `failure_stage`, evidence and verdict), `false_green_findings`,
`synthetic_declared_candidates`, `eid_r` (via
`EID-r-derives-from-EID-star` and `EID-r-recomputes`), `traces` + `traces_source`,
`failure_stage_counts` (the adapter's own counters, or counted by the runner from its score trace),
`failure_stage_accounting` (those counts vs the frozen §5.3 map over `C*`),
`eid_document_supplied` (which `EID*` document this runtime was handed, with its digest),
`adapter_revision` (digest, per-file sha256 + mtime, newest mtime, and whether the source changed
while the runtime was being driven — so a stored verdict names the revision it covers),
`adapter_unverified_notes` (the adapter's own UNVERIFIED statement) and `adapter_seams` (the
injection seams it declares, with `path:line`). `report.md` prints the same as a "Handoff" block.

**Adapter self-claims are namespaced `__untrusted`.** A runtime's own assertion about its A0.1
outcome is never a verdict and never appears under a verdict-shaped name. It is recorded in
`adapter_claim__untrusted` (the raw string the adapter declared) and, with its surrounding metadata,
in `adapter_self_declaration__untrusted` (`schema`, `declared_outcome`, `blocked_reason`,
`claim__untrusted`, `row_count`). The authoritative verdict keys are only `state`,
`qualification.a0_1`, and the top-level `verdicts` block; a consumer that joins on any of those
cannot reach an adapter claim. Verify with the grep in "Current state" below — no key containing
`verdict` in `report.json` may hold an adapter's self-declared string.

`a0_2` is deliberately `null`: A0.2 (selection semantics) is owned by the A0.2 workstream
(`a0/acceptance`), and this runner does not judge it. The study's `R_1` needs both.

## Current state

See `report.json` → `runtimes.<r>` for the verdict and `.rerun` for the exact command to re-run
one runtime alone. `PENDING` means **not driven** — neither passing nor failing — and always comes
with the reason and the raw stderr. `BLOCKED` is reserved for an adapter that declares itself
unable to run (e.g. a missing model backend). `PARTIAL` means the runtime was driven and every row
agrees, but some rows agree only on semantics the adapter supplied, so they are not measurements:
read `qualification.a0_1.measured` / `.adapted` alongside the state, and never quote a `PARTIAL`
runtime's number for a statistic that has to distinguish `invalid`/`error` from a genuine zero.

`report.json` is a single shared artifact written by whatever `run` invocation ran last, so a
per-runtime re-run **must** use `--out report.<runtime>.json`; a bare `--runtimes <r>` no longer
writes `report.json` at all — it is redirected to `report.<r>.json` with a printed notice, because
three times during this study such a run silently replaced the four-runtime report that every other
workstream reads. `report.json` records the `EID*`
document it handed to each adapter (`frozen.eid_document_name` / `eid_document_sha256`,
`runtimes.<r>.eid_document_supplied`) so a reader can tell whether two reports measured the same
inputs. The adapters were still changing during the last full re-run; check each adapter's source
mtimes against `report.json` → `generated_at` before quoting a number.

**The four-runtime state after D1 + D3 (the honest current picture).** `simpleloop` is
`PASS (14/14 measured)`; `kapso`, `eve` and `loreley` are `FAIL` with
`14 x MISSING_ATTESTATION` — their numbers still agree 14/14, and their rows do not carry the
harness measurement token (the wiring cost is in the table above). EvE's own measurement split is
unchanged (`PARTIAL`, 5/14 measured) and is still reported per row; what changed is that A0.1 is
now non-accepting without an attestation, for every runtime. `verdicts.r_1_a0_1_only` is therefore
`["simpleloop"]`, not the four-runtime set earlier reports showed.

**Confirm no bare `PASS` for EvE survives in the machine-readable output** (any bare `PASS` in
`report.json` must belong to a runtime whose authoritative `state` is `PASS`, or to the honest
control; an adapter self-claim never does):

```bash
cd /home/ebt/rsi-dev/a0/conformance
python3 -c "
import json
d = json.load(open('report.json'))
def leaves(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, p+'.'+k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, p+'[%d]'%i)
    else: yield p, o
rows = list(leaves(d))
auth = {p: v for p, v in rows if p in ('.runtimes.eve.state', '.runtimes.eve.qualification.a0_1.state', '.verdicts.a0_1_state.eve')}
# A0.1 is FAIL while the rows are unattested; the measurement split (5/14 measured) is a separate
# axis and stays visible in qualification.a0_1. What must never appear is a bare PASS.
assert auth == {'.runtimes.eve.state': 'FAIL', '.runtimes.eve.qualification.a0_1.state': 'FAIL', '.verdicts.a0_1_state.eve': 'FAIL'}, auth
passes = [(p, v) for p, v in rows if isinstance(v, str) and v.strip() == 'PASS']
adapter_claims = [p for p, _ in passes if '__untrusted' in p]
runner_own = [(p, v) for p, v in passes if '__untrusted' not in p]
# A bare PASS is legitimate only as the runner's own state/label for a runtime it attested
# (simpleloop), or for a control row; an adapter's self-claim is never legitimate.
assert all(('simpleloop' in p) or p.startswith('.controls.') for p, _ in runner_own), runner_own
print('authoritative eve keys        :', auth)
print('eve measurement split         :', json.load(open('report.json'))['runtimes']['eve']['qualification']['a0_1'])
print('runner-own bare PASS keys     :', [p for p, _ in runner_own])
print('adapter PASS claims (untrusted):', adapter_claims)
print('NO BARE PASS OUTSIDE THE RUNNER OWNING IT: ok')
"
```

