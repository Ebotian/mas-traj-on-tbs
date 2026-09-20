# `a0/verify/` — independent adversarial verification of the A−1 / A0.1 / A0.2 claim set

**Auditor.** Independent verification workstream. I own `a0/verify/**`. I did not edit any other
workstream's code or records. Three artifacts I did touch outside my directory across both passes
are disclosed in §5: two fixture-run directories, both removed again, and one regenerated file that
is still outstanding.

**Method.** Every verdict below rests on a command I executed in this session, with its real
output. Machine-readable form: [`verdicts.json`](verdicts.json). Raw outputs: `a0/verify/out/`,
probe scripts: `a0/verify/*.py`.

**Headline.** Of the study's claims: **32 ACCEPTED / FIXED**, **1 STILL REJECTED** (the
failure-bearing surface is not *fully* enforced — R1b), **1 UNPROVEN**. All three pass-1 rejections
are **FIXED** and reproduced by me against the corrected artifacts. The study's core — `EID*` frozen
and recomputable, `C*` intact, `E*` deterministic and environment-invariant, all four adapters
faithfully executing `E*`, all four selection semantics demonstrated, all four false-green trap
families firing, closure measured with real two-control probes — **reproduces when I run it myself**.
Two further auditor-constructed probes (C8.3, C8.4) are REJECTED and are not study claims: the
workstreams' *stored* conformance artifacts are stale relative to their own code.

**Pass 2 (re-verification).** This revision re-checks the three rejections and the two findings
after the workstreams acted, plus the two items that were still in flight. Everything below is
pinned to the digests and mtimes recorded at read time; §5 lists what changed between passes.
Findings now fixed: **R1 FIXED except for the residual below**, **R2 FIXED**, **R3 FIXED**,
**F1 FIXED**, **F2 FIXED**.
Landed in flight: **KAPSO declaration re-adoption**, **EvE + Loreley frozen `failure_stage_mapping`
adoption** (both verified only by re-running the adapters myself — the workstreams' own stored
artifacts still predate their own fixes; see §5).

---

## 1. Dispositions of the pass-1 rejections

### R1 — "The nine non-`ok` candidates are compared as verdicts" (`adapter_contract.md` §4.5)

**Disposition: PARTIALLY FIXED.** The false PASS is gone; a residual hole remains for an adapter
that *omits* `failure.kind` entirely (R1b below).

`conformance.py` compares only the **coarse status**, never `failure.kind`. The contract says:
"Candidates whose `E*` verdict is `invalid` or `error` compare on **verdict and `failure.kind`**,
not on a number."

I built an adapter (a copy of the study's own honest reference fixture, one field patched) that
reports `status` truthfully but `failure_kind: "adversarially_wrong_kind"` on **all nine** non-ok
rows — i.e. misattributes every failure to the wrong stage — and ran the checker against it:

```
$ cd a0/verify/confrun && a0/contract/.venv/bin/python conformance.py run \
      --runtimes kindlier --adapter "kindlier=<venv>/python a0/verify/fixtures/adapters/kindlier_adapter.py" \
      --no-controls --out a0/verify/out/kindlie.report.json
--- kindlier ---
    PASS: all checks passed
verdicts (A0.1 only): {"kindlier": "PASS"}
EXIT=0
```

All ten checks `ok: true`, including `E-r-equals-E-star`. The runner's own rows show what it
ignored:

```
c09_malformed_import   E*_kind=candidate_import_failed   verdict=MATCH_VERDICT
c10_raises             E*_kind=candidate_call_raised      verdict=MATCH_VERDICT
c11_non_deterministic  E*_kind=non_deterministic          verdict=MATCH_VERDICT
c13_slow               E*_kind=runtime_budget_exceeded    verdict=MATCH_VERDICT
c05_overlapping        E*_kind=invalid_configuration      verdict=MATCH_VERDICT
```

`grep -n failure_kind a0/conformance/conformance.py` showed it used only in the `E*` reference
sweep self-check (`:681`); `compare_rows` keyed on `obs['status']` alone. Severity: **high** — the
A0-wide `failure_stage` table exists precisely so per-runtime `FailureStage` counts are joinable
(`plan:577`, `plan:628`), and a runtime that mis-staged every failure passed A0.1.
Owner: conformance workstream. **Original evidence kept: `verify/out/kindlie.report.json`.**

#### R1 fix — reproduced by me (PASS)

`conformance.py` moved from `62e492fb…` (128603 B, 18:59:51) to
**`2d7040750f164d8f44ce1600a68b673856d6dec2de48a2584af61fe47ed88511`** (147927 B, 19:24:10).
New surface: `declared_failure_kind()` (`:1039-1052`), `check_failure_kind()` (`:1071-1110`),
`MISMATCH_FAILURE_KIND` (`:123`), `FALSE_GREEN_KIND = "FG-FAILURE-KIND"` (`:129`), and a new
`E-r-failure-kind` check (`:2177-2202`). I rebuilt my liar adapter from the **current** fixture
(`kindlier_adapter.py`, sha256 `6be8f8ad…`) and re-ran:

```
$ cd a0/verify/confrun && a0/contract/.venv/bin/python conformance.py run \
      --runtimes kindlier --adapter "kindlier=<venv>/python a0/verify/fixtures/adapters/kindlier_adapter.py" \
      --no-controls --out a0/verify/out/kindlie.recheck.json
--- kindlier ---
    FAIL: false-green finding(s): FG-FAILURE-KIND
verdicts (A0.1 only): {"kindlier": "FAIL"}
EXIT=3
```

Row verdicts `{MATCH: 5, MISMATCH_FAILURE_KIND: 9}`, failing checks `E-r-equals-E-star` +
`E-r-failure-kind`, matching the owner's reported numbers exactly. Per-row evidence:

```
c10_raises  e_star_failure_kind=candidate_call_raised  e_r_failure_kind=adversarially_wrong_kind
            e_star_failure_stage=evaluator_failed      verdict=MISMATCH_FAILURE_KIND
```

The fix is self-tested: `selftest.py` now carries `selftest_wrong_failure_kind` →
FAIL `FG-FAILURE-KIND` and `selftest_wrong_failure_stage` → FAIL `FG-FAILURE-STAGE`, and my
re-run of the whole matrix is **19/19 fixtures behaved as expected: True** (was 17/17).

#### R1b — the residual hole (STILL OPEN, judged not to matter for this study)

An adapter can dodge the new check by **omitting** `failure.kind` entirely. `check_failure_kind`
returns `None` without setting a verdict when `declared_kind is None`, so `kind_bad` stays empty
and the check's `ok` flag — `"ok": not kind_bad` (`:2181`) — is **True**. I built
`omitter_adapter.py` (the honest fixture with `"failure_kind": None`, sha256 `981ec7b1…`) and ran it:

```
--- omitter ---
    PASS: all checks passed
verdicts (A0.1 only): {"omitter": "PASS"}
EXIT=0
```

with `E-r-failure-kind.ok = True`, `kind_undeclared_for = [c05…c13]` (all nine), and per-row
`failure_kind_declared: false`. The report *does* disclose the gap in the check's `detail`
("0/9 non-ok candidate(s) declare a failure.kind … the rest declare none, so their staging could
not be compared…") and on every affected row's `notes`, but a reader who reads the check's `ok`
flag — or the runtime's `PASS` — sees green. Evidence: `verify/out/omitter.report.json`.

**My judgement: it does not matter for A0.1 as this study runs it, but the check's `ok`
semantics are wrong and should be fixed.**
* Not live here: all four real runtimes declare **9/9** kinds and every declared kind matches `E*`'s
  (verified in my own four-runtime re-run, `verify/out/recheck.final.json`). No runtime in this
  study can trip the hole.
* It matters as an artifact: the checker is the study's reusable deliverable and `selftest.py`
  exists to prove it rejects faults — but no fixture exercises the omission path, so the hole is
  untested by the very harness that certifies the checker.
* It matters for the *contract*, not the protocol: the A0.1 acceptance formula
  (`plan:513-519`) says nothing about `failure.kind`; `adapter_contract.md` §4.3.5 requires it.
  An omitting adapter is non-conformant with the adapter contract yet still gets PASS.
* Requested fix: make `E-r-failure-kind` `ok: False` (or a distinct non-fatal state) whenever
  `len(kind_declared) < len(non_ok_rows)`, and add an omission fixture to `selftest.py`.
  It is *not* urgent given the current four adapters; it *is* the difference between a checker
  that tests §4.3.5 and one that tests it only when the adapter volunteers.

### R2 — "No document under `a0/` still carries the superseded `fac50fc4…` in a way that could mislead"

**Disposition: FIXED.**

The *true* half held: I enumerated every `*EID*.json` in the tree and none carries `fac50fc4…`
as its identity — `contract/out/plumbing.EID.json`, `tasks/circle-packing/plumbing.EID.proposed.json`
and `EID_INPUTS.json` all carry `664115e0…`; the only other occurrence is a deliberate stale
fixture (`conformance/fixtures/adapters/deviant.py::STALE_EID`). Every prose occurrence in
`contract/README.md` and `contract/adapter_contract.md` is inside a revision note that says the
old value was wrong.

The *false* half — two documents asserting the contract was still stale — has been corrected, each
with an explicit note:

* `runtimes/simpleloop/HANDOFF_to_contract_owner.md` (sha256 `0dae73ef…`, mtime 19:18:36) now
  carries "**Corrected — there is nothing to fix in the contract (verifier finding R2).** … That was
  already false when this file was written at 18:25: the contract was repaired at 16:57".
* `runtimes/simpleloop/A0_REPORT.md` (sha256 `92c41f2b…`, mtime 19:18:50) now carries
  "**Corrected (verifier finding R2).** An earlier revision of this report warned that …".

Both replacements keep the original wrong text quoted and labelled, which is the right way to
retract. Their second sub-claim also checks out, and I verified it independently: **no
machine-readable artifact ever carried it as an identity.** Every `json`/`jsonl` file in the tree
containing `fac50fc4` — outside my own `verify/` — is the negative fixture `selftest_stale_eid`
(its source constant, the self-test expectation, and its deliberately-stale output document); and
`grep -rl fac50fc4 --include=*.jsonl .` over the whole tree returns **nothing**, so no run trace
ever carried it.

### R3 — "EvE's `EID_r` recompute shows `EID_r` derives from `EID*`"

**Disposition: FIXED.** The property I cared about — that a script ignoring `EID*` could not
recompute the value — now holds, and I verified it four ways.

`EID_r` was `sha256` of the evaluation step script **the adapter itself generated**; I recomputed
it (`sha256:60ee4117…`) and it matched, but nothing *forced* the `EID*` dependence. The value is now
`sha256:b903b051c87218a3599609ade2e742565f4244b893a49d9850fb7cd09a79fc0a`, a domain-separated
hash over a payload in which `eid_star` is an **argument**, with a standalone tool that imports
nothing from the adapter.

1. **Standalone recomputation reproduces the declared value.**
   `runtimes/eve/.venv/bin/python runtimes/eve/tools/recompute-eid-r --eid contract/out/plumbing.EID.json`
   → exit 0, value `sha256:b903b051…`, equal to the declared value, over the payload
   `{"eid_star":"664115e0…","evaluator_source":{"digest":"a3d6534b…","files":[…]},…}`.
   The runner now executes this tool: `EID-r-recomputes` mode `executed`, recomputed == declared.
   Tool sha256 `e78ffac5…`.
2. **Mutating `EID*` changes the derived value.** I copied the EID document and flipped one nibble
   of `eid_star` (`f64115e0…`, staged at `verify/out/eve-eidr/eid.mutated-star.json`):
   recomputed value becomes `sha256:9635bba934c350894e3134e77c7e3ebf3166c5717029adc9c83a948c9382ad34`,
   ≠ the original. So `EID*` is a genuine argument, not a hardcoded constant.
3. **A mismatched evaluator source is refused, not hashed.** Two mutations, both exit 3 with a
   named reason: corrupting a recorded `EvaluatorSource` digest
   ("hashes to `2abc6ea1…`, EID* records `000…0` — the document does not describe these bytes"),
   and genuinely appending bytes to a staged copy of `e_star.py`
   ("hashes to `44876e70…`, EID* records `2abc6ea1…`").
4. **The adapter itself refuses a mutated `EID*`.** Running EvE's own conformance subcommand with
   the mutated document at `a0/runtimes/eve`:

   ```
   EXIT=3
   a0_adapter(eve): evalcontract verify failed: DRIFT EID* changed f64115e0d63ad2e1 -> 664115e0d63ad2e1
   ```

   and no output document is produced. This is the part that closes my original objection: the
   adapter is parameterised by the document it is handed rather than declaring a constant.

EvE's own `tools/eid_r_mutation_check.py` (sha256 `92971699…`) reports M1–M4 all PASS; I reproduced
M3 and M4 independently above rather than taking them on trust. One honest limit remains: this
proves the *recomputation* cannot ignore `EID*` and that the adapter refuses a document that does
not match its own inputs. It does not prove the adapter used the passed document at every internal
point — that rests on items 2–4 plus the runner's `EID-star-verbatim` echo, which is what a checker
can reasonably demand.


---

## 2. UNPROVEN

* **"No mock was silently substituted for a runtime."** The only `monkeypatch`/`Mock`/`Stub` hit
  across all four adapters is KAPSO's *declared* `EvaluationMaintainer._run_agent` no-op
  (`runtimes/kapso/a0_adapter/runtime.py:288`), and each adapter publishes a `seams`/`unverified`
  block. My scan was lexical and I did not read every line, so I cannot prove a negative. What I
  *did* establish by execution is stronger for the seamed paths anyway: the A0.1/A0.2 numbers come
  from real `E*` subprocesses and real runtime selection code in all four cases (see §3).

---

## 3. ACCEPTED — the evidence that matters

### `EID*` is frozen, recomputable, and single-input sensitive
I re-implemented the whole hashing scheme from `contract/SPEC.md` §2 alone
(`verify/myEID.py` — it imports nothing from `evalcontract.py`) and reproduced all five component
digests and `EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`
bit-for-bit; their own `evalcontract.py recompute` and `verify` say the same (exit 0).
`EvaluatorSource` selects exactly `{e_star.py, e_star_child.py}` and my re-hash of both matches
the records (`2abc6ea1…`, `e189c020…`).

Five one-input mutations (`verify/mutate_inputs.py`, plus a negative control) each changed **only**
the corresponding component and `EID*`: 5/5 PASS, control PASS. The staged harness reproduced 4 of
the 5 real component digests exactly (only `DataManifest` differs, by design).

### `C*` and `E*`
All 14 `solution_sha256` match `C_STAR/manifest.json` (14/14, exit 0). Every candidate file is older
than `E_STAR.json` (16:03:40 vs 16:06:12). I reproduced **all 14** candidates' `E*` results — exit
code, status, `canonical_digest` and objective bit-for-bit, including the four `invalid` (exit 2,
objective `null`) and five `error` (exit 3, objective `null`) cases; exactly one
`E_STAR_MANIFEST` line per run.

**Hostile-environment invariance holds.** From a cwd full of decoy `solution.py`/`e_star.py`/
`C_STAR/c01_good_hex`, with a `PATH` whose first entry is a shim dir of fake
`python`/`sh`/`bash`/`env`/`git`, the score was identical (`1144adc6…`, `2.4519205208433132`), the
decoy was never used (`source_sha256 = bca4286e…`), no shim ever executed, and the hostile cwd was
left untouched.

*Residual (outside the frozen claim):* with `PYTHONPATH` additionally pointed at the hostile cwd,
the `E*` **parent** interpreter imported the injected `sitecustomize.py` and dropped a `.pyc` in
that cwd. The score was unaffected and `PYTHONPATH` is not part of the "no cwd or PATH dependence"
claim, but the parent process is only as clean as its caller.

### A0.1 conformance reproduces
`conformance.py reference` → "reference table reproduced exactly: **True**". A full `run` at 19:03
(my byte-copy of the runner, `sha256 62e492fb…`, writing only into `verify/`) → **simpleloop PASS,
kapso PASS, eve PASS, loreley PASS**, both deviant controls FAIL as expected, exit 0. The
conformance workstream's own `report.json` (19:07:12) independently agrees. Their `report.json`
at 18:56 covered *only* `simpleloop`; the four-runtime report is newer than that.
**Pass 2:** the same four-runtime re-run against the fixed runner (`2d704075…`, my re-run at 19:38,
`verify/out/recheck.final.json`) again gives **all four PASS, exit 0**, with
`E-r-failure-kind` `ok: true` and 9/9 kinds declared for every runtime.

**False-PASS attacks all fail.** `selftest.py` (my own re-run, pass 1): **17/17** fixtures behaved
as expected, including drift at `1e-6` FAILing while `1e-10` PASSes, `digest_swap` FAIL, `partial`
FAIL, `stale_eid` FAIL, `synthetic_mislabeled` FAIL while `synthetic_declared` PASSes. A tampered
candidate aborts the run at **exit 4** naming exactly `['c04_near_tie']`, before anything is
evaluated. Pass 2 raises this to **19/19** with the two new fixtures `selftest_wrong_failure_kind`
(FAIL `FG-FAILURE-KIND`) and `selftest_wrong_failure_stage` (FAIL `FG-FAILURE-STAGE`); the integrity
abort still exits 4 naming `['c04_near_tie']`. The `kindlier` attack was the exception I found in
pass 1 — a gap in *what* was compared, not in the trap machinery — and it is now caught (§R1),
with the omission variant still open (§R1b).

**Race finding.** My first run (19:00:15) FAILED KAPSO with adapter exit 10, `incomplete coverage
of C*`, 0/14 rows and `FileNotFoundError: …/runtimes/kapso/contract/selection/kapso.selection.json`.
That file was created at **19:01:32** by the KAPSO workstream; the 19:03 re-run PASSes. Both
outcomes are real. The lesson is structural: KAPSO's `conformance` subcommand hard-requires a
declaration file inside its own tree that is not part of `a0/contract`, and its absence turns the
entire A0.1 answer into a crash instead of a diagnosable FAIL. Pass 2 shows the same shape twice
more (F7's EvE `selectionmap.py` window, and the two stale stored artifacts in §5): **the A0.1
verdict for a workstream is only as current as its last re-run.**

### A0.2 — every runtime, re-run by me
* **KAPSO** — my own `run --skip-a01`: `a02_pass: true`, all five scenarios true, 14 checks pass.
  The discriminator is `A02-K2-REVERSED`: with the low scorer (0.25) evaluated **last**, the next
  parent is still the high scorer — score, not recency, decides. `fast_only` shows a fast-tier
  2.4519 winning the *parent* while a full-tier 0.25 wins the *deliverable*, exactly as the frozen
  semantics claim. Real KAPSO strategy code (`get_best_experiment`, `_select_parent`,
  `select_committed_candidate`, `enforce_evaluation_integrity` …) with real `E*` subprocesses; the
  three seams (ideation/implementation/judge) are declared in `seams.py` and the LLM path is
  declared UNVERIFIED.
* **EvE** — my own 3000-draw driver through the real call site
  (`Phase2BatchRunner._sample_solvers`, `phase2.py:597-605`): `p̂ = 0.7357` against the closed form
  `0.7310586`; the score-swap control moves it to `0.2553`; two-proportion `z = 37.2`, `p ≈ 5e-303`.
  My numbers **differ** from theirs (`0.7540`/`0.2630`) — as they must, since `base.py:40` makes the
  population RNG unseeded, which is also why the six replicates in `e1_replication.json` are
  independent draws. I instrumented the sampler: exactly **one** `sample` call per iteration
  (3000/3000), so the count is per iteration, not per worker. Pooled arithmetic reproduces exactly
  (`p̂ 0.7290`, `z −0.6228719532600361`, exact two-sided `p 0.5339723993557` vs their
  `0.5339723993507`). Competing hypotheses rejected (uniform, wrong population, re-ranking).
  Pre-registered `n` (43 normal / 44 exact) met with ~4x margin, and the marginal E1 result is
  honestly disclosed and superseded by the pooled figure. `/tmp/eve` is at the pin `979065fd…`.
* **Loreley** — my own `a02` re-run: 7/7 checks pass. `L1` scores c01/c02 through the real
  `Evaluator` path and then calls the real `ParetoGridArchive.add` twice, showing same-cell
  replacement (c2 removed, `|gap| = 2.2019 ≫ ε`); `L3`/`L3-M` are the cross-cell negative control
  (higher score, different cell, no eviction); `L7` shows sampling is score-independent (4000 draws,
  1970/2030). The archive is the pinned checkout's own class (`checkout` HEAD `4c375920…`), and the
  observation reproduces a real internal quirk (`pareto_archive.py:407`) no mock would emit. The
  single-objective caveat is self-disclosed — under one objective the cell front has one member, so
  the discriminating control only exists in the two-objective config, which is also run.
* **SimpleLoop** — my own `a02-check`: `pass`, 9/9. Order invariance holds in both directions; the
  frozen tie-break is observable and the **rejected** earliest-index rule provably gives a different
  answer in reverse order, so the test discriminates; the near-tie gap is 100000× ε so an
  ε-tolerant comparison cannot absorb it. The clearest direct demonstration of the whole claim set
  is `injected_score_moves_selection`: with `--inject-scores` giving c02 `99.0`, the champion flips
  from c01 to c02 while the logged `E*` Outcome stays real.

### Traps — all four families fire
`selftest_zero_on_error` FAILs with fatal `FG-EVE-SYNTH` on all nine non-ok candidates (a 0.0 where
`E*` has `null` is failed, not passed); Loreley's timeout / cap+truncation / cache trio fires
(`FG-LORELEY-TIMEOUT`, `FG-LORELEY-CAP` + `FG-LORELEY-TRUNCATED`, `FG-LORELEY-CACHE`) and my own
`a0-loreley traps` re-run reports T2/T3/T4 pass — with T3 honestly reporting that the metric cap is
**bypassed** entirely on the `EvalPass` payload path, a genuine upstream gap reported rather than
smoothed away; KAPSO's manifest triple fires (`FG-MANIFEST-TRIPLE`, `FG-ATTEMPT-THETA-DRIFT`, and
KAPSO's own `manifest_class_mismatch` control returns no score of record). The `c05_overlapping`
trap is genuinely closed: its pre-gate `structure.sum_radii = 2.4519205208433132` is **bit-identical
to c01's score** yet `status = invalid`, `objective = null`, `fields.sum_radii = null` — and no
runtime gives it a number (`MATCH_VERDICT` ×3, `SYNTHETIC_DECLARED` with the 0.0 annotated for EvE).

### Closure — measured, with both controls
I re-ran the CLI sandbox probe myself (exit 0, PASS): host `egress=OPEN`; `workspace-write`
`BLOCKED`; `danger-full-access` `OPEN`; and `workspace-write + network_access=true` **OPEN** — so the
record is right that config alone is not proof. The four end-to-end model-lane pairs each show
`returncode 0`, `model_call_completed true`, `tool_ran true` and a canary **persisted by the in-lane
shell tool** (never read from the model's prose): closed postures `egress=BLOCKED`, open postures
`egress=OPEN`. My scan of all four records: **5 mechanisms carry `schema_verdict=closed` and all 5
carry both controls**; nothing closed rests on a timeout, an absent tool, or `inconclusive`.
Top-level verdicts are disciplined — `eve` closed, `simpleloop` closed, `kapso` **inconclusive**,
`loreley` **inconclusive**, each glossed as "treated as NOT closed" with a named reason.

`closure.reconciliation.json`'s authority rule (refuse to credit an absent tool as closure) is
sound, and its claims check out — **but it is now stale**: it cites KAPSO's
`lane_probes.codex_workspace_write` as `{returncode 124, timed_out true, command_ran false}`, while
the file was rewritten at 19:08:02 and now reads `{returncode 0, ran true, network_reached false}`.
The workstream re-ran the probe; the specific defect the reconciliation cites no longer exists there.

### Real-lane evidence
All verified by executing `E*` myself on the producers' artifacts:
* SimpleLoop `codex-live3` `work/iter001/solution.py` → **2.6251746109048** and `codex-live4`
  `work/iter001/solution.py` → **2.5414213562373096**, matching the recorded champions exactly, and
  both beating every member of `C*` (best 2.4519).
* EvE `run004` records its failure as a failure ("driver rollout timeout at 660 s … the produced
  candidate scored `E*` = 0.25 (the untouched baseline)") while its by-product is labelled honestly
  ("adapter transcription of the agent's own artifact, not an agent-authored solution.py") and I
  reproduced its measurement, **2.6168716968517516**, exactly.
* KAPSO `e2e-real` agrees three ways on 2.451820520843313, which I reproduced as `E*`(c04_near_tie);
  `e2e-real2` records a failed round rather than a success.
* Loreley's bounded round states its own negative plainly: planning succeeded (144.1s, real codex
  call), coding timed out at 480s, watchdog stopped the round, `evaluation_attempts = 0 rows`; an
  earlier attempt is recorded as `"ok": false` with the real 401 in the error text.

---

## 4. Findings for the owners — pass-2 dispositions

| # | Disposition | Finding and pass-2 verification |
|---|---|---|
| F1 | **FIXED** | **KAPSO `theta_E` identity keys were ambiguous**, and now are not. Pass 1: `theta_E.extra.evaluator_source_sha256 = 781f54ee…`, which `sha256sum` shows is `kapso_eval.py` — the *adapter wrapper*, not `E*` — while everywhere else that key means `E*`'s `5ae97ad9…`. Now (`conformance/out/adapters/kapso.conformance.json`): `e_star_evaluator_source_sha256 = 5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532` **and** `registered_wrapper_sha256 = 781f54ee7674164d2b71e78d42640f985f3907a76542b8d5a84a3b5220d9e5ba`. Both correct and unambiguously named; I re-ran `sha256sum` on `kapso_eval.py` (`781f54ee…`) to confirm the second. |
| F2 | **FIXED** | **The runner's `E-star-manifest-echo` no longer has a false negative for KAPSO.** Pass 1 it reported "no E* manifest echo found"; now `E-star-manifest-echo` is `ok: true` with `echoes_checked: 14`, `echo_forms: ["fields"]`, and all 14 candidates listed. I did not take the count on trust: my own independent comparison of every row's `registered_channel.manifest.e_star_canonical_digest` against `E_STAR.json` gives **14 matches, 0 mismatches**, with `e_star_evaluator_source_sha256 = 5ae97ad9…` on all 14. SimpleLoop/eve/loreley still report 28/56/28 echoes. |
| F3 | **FIXED** | Stale cross-references in two SimpleLoop documents — corrected, see R2. |
| F4 | still open (info) | `C_STAR/README.md` was written after `E_STAR.json` (16:07:47 vs 16:06:12) but is not in `DataManifest` and does not enter `EID*`. "C* unchanged" is true of the candidate data and manifest, not of the whole directory. No action requested. |
| F5 | still open (info) | EvE's A0.1 "14/14 agree" is, for EvE, **5 measurements + 9 declared synthesised zeros**. Defensible under the "the trap is *silent* mapping, and this mapping is declared" reading, but the literal acceptance formula `E_r(c) = E*(c) ± ε` does not hold on those 9 rows, and EvE's lane structurally cannot express `invalid`/`error` at all. A consumer should read EvE's row as 5/14 measured. EvE's `failure_stage` counts now match the frozen map (see below), which does not change this. |
| F6 | still open (low) | The reference fixture's default run dir resolves from the fixture's own location and escapes the adapter root (`reference_adapter.py:63`); a copy of the fixture placed elsewhere litters the original tree. See §5 for how it bit me twice. |
| F7 | **new, transient (resolved)** | At 19:37 my four-runtime re-run put **EvE at PENDING** with `a0_adapter.selectionmap.SelectionMappingError: … '/home/ebt/rsi-dev/a0/a0/contract/selection/simpleloop.selection.json'` — a doubled `a0/` segment in `selectionmap.py` (written 19:36:32). The file was fixed at 19:37:59 and my re-run at 19:38 gave PASS. Reported as an observed transient, not a standing defect: the A0.1 verdict for a workstream can flip for ~a minute while its own file is mid-write. |

---

## 4b. Items that were in flight — all landed

### KAPSO's corrected selection declaration, re-adopted by the contract owner — LANDED
KAPSO's runtime-side canonical digest moved `143bfc94…` → `c1a99365…` after a sanity check forced a
text fix; the contract owner re-adopted it. Verified by my own computation, not by reading theirs:

* `contract/selection/kapso.selection.json` (sha256 `29ee490a…`, mtime 19:23:25) canonical digest,
  computed with my own `sha256(canonical_json(...))` implementation = **`c1a99365…`**, matching both
  the contract pin (`contract/tests/test_evalcontract.py:240`) and KAPSO's declared value.
* The two A0-wide blocks are byte-identical to the frozen `simpleloop.selection.json` and hash to
  the pinned digests: `scalarization = d59f0930…`, `failure_stage_mapping = 201fed78…` (my
  computation; KAPSO's `shared_blocks.{scalarization,failure_stage_mapping}.identical == true`).
* KAPSO's frozen-copy check now agrees: my fresh run reports
  `selection.frozen_canonical_copy.identical_to_this_declaration = true` with both digests
  `c1a99365…`. The **stored** artifact `conformance/out/adapters/kapso.conformance.json`
  (19:26:42) still records `143bfc94…` / `identical: false` — it was written by a run that began
  before the 19:23:25 re-adoption. **The conformance workstream needs a re-run for its stored
  artifacts to match its own code.**
* `cd a0/contract && ./.venv/bin/python -m pytest -q` → **73 passed** (was 62), including the newly
  pinned per-runtime declaration digests.

### EvE and Loreley adopting the frozen `failure_stage_mapping` — LANDED
Both now declare counts equal to the frozen map over `C*`, and I verified the map itself
independently rather than trusting the advertised numbers: applying
`contract/selection/simpleloop.selection.json`'s `failure_stage_mapping` to `E_STAR.json`'s
(status, `failure.kind`) pairs with my own code gives exactly
**`{none: 5, verify_failed: 5, resolve_failed: 1, evaluator_failed: 2, timeout: 1}`** (c01–c04, c14
→ `none`; c05–c08 → `verify_failed`; c09 → `resolve_failed`; c10, c12 → `evaluator_failed`;
c11 → `verify_failed`; c13 → `timeout`).

My four-runtime re-run (`verify/out/recheck.final.json`, exit 0, all four PASS) reports:

| runtime | `failure_stage_counts` | equals frozen map over C* |
|---|---|---|
| simpleloop | `{none:5, resolve_failed:1, timeout:1, verify_failed:5, evaluator_failed:2}` | yes (nested under `counts`) |
| kapso | same, plus `counts_score_trace_only` | yes (nested under `counts`) |
| eve | `{evaluator_failed:2, none:5, resolve_failed:1, timeout:1, verify_failed:5}` | **yes** |
| loreley | same, and 14/14 rows declare a per-row `failure_stage` | **yes** |

Two caveats a reader should keep. (1) EvE's earlier `{none:5, resolve_failed:9}` is what its stored
artifact and `conformance/report.json` (19:27) still show; the fix landed in
`runtimes/eve/a0_adapter/a01.py` at **19:35:48** and my run at 19:36:10 is the first to exercise
it — same staleness as KAPSO above. (2) EvE declares no *per-row* `failure_stage` (0/14), only
aggregate counts; Loreley declares both.


---

## 5. Snapshot hygiene and side effects

Everything above is pinned to the artifacts I read; sizes and mtimes are in `verdicts.json`.
Other workstreams were **actively writing while I audited**. Pass-2 timeline of the writes that
decided my verdicts — note how many landed *after* the artifacts that claim to record them:

| time | write | consequence |
|---|---|---|
| 19:00:14 | `conformance/reference.json` (mine) | regenerated E\* sweep |
| 19:01:32 | `runtimes/kapso/contract/selection/kapso.selection.json` created | my 19:00 KAPSO conformance run had already crashed on its absence (pass 1) |
| 19:07 / 19:08 | `conformance/report.json`, KAPSO `closure.json` | converged with pass 1 |
| 19:18:36 / 19:18:50 | SimpleLoop `HANDOFF_…md` / `A0_REPORT.md` | R2 corrected |
| 19:22–19:23 | `runtimes/eve/tools/*`, `contract/selection/kapso.selection.json` | R3 tools, F1 rename, KAPSO re-adoption |
| 19:24:10 | `conformance/conformance.py` → `2d704075…` | R1 fix |
| 19:26:42 / 19:27:01 | KAPSO + `report.json` artifacts | **predate** the 19:23:25 re-adoption in the way they report it |
| 19:35:48 | `runtimes/eve/a0_adapter/a01.py` | frozen-map adoption; **stored eve artifact (19:28) predates it** |
| 19:36:32 → 19:37:59 | `runtimes/eve/a0_adapter/selectionmap.py` | EvE briefly PENDING (F7), then fixed |
| 19:38–19:41 | my four-runtime re-run | all four PASS with the frozen map |

The general lesson, which is why I re-ran rather than read: **both workstreams' stored conformance
artifacts describe a code state older than the code on disk.** Two items I was asked to check would
have come back "not landed" from the stored artifacts alone and are in fact landed.
Owner action: re-run `conformance.py run` so `report.json` and `out/adapters/*` are regenerated
against the current adapters.

**Files I wrote or removed outside `a0/verify/`.** Two, both disclosed and now both clean:

1. `a0/conformance/reference.json` (mtime 19:00:14), from running `conformance.py reference` — it
   regenerates the same `E*` sweep the tool always produces. **Still outstanding**: I cannot restore
   the pre-existing bytes, and the file has not been rewritten since. It is the tool's own output
   and semantically identical to a fresh sweep, but the owner should know their copy was regenerated.
2. `a0/conformance/out/fixture-runs/{kindlier,omitter}/**` — created by my R1 probes. Cause: the
   study's own fixture template defaults its run dir to
   `A0 / "conformance" / "out" / "fixture-runs" / runtime` with `A0 = <fixture dir>.parents[2]`
   (`conformance/fixtures/adapters/reference_adapter.py:63`), and the runner passes `--run-dir` only
   on the `run` fallback path, not on the `conformance` path. My copies, placed under
   `a0/verify/fixtures/adapters/`, therefore resolved `A0` back to `a0/`. This bit me **twice** —
   the pass-1 `kindlier` directory, then `kindlier` + `omitter` again in pass 2. Both times a
   snapshot check confirmed every file was mine and none pre-existed, and both times I removed the
   directories (`a0/conformance/out/fixture-runs/` is back to `control_honest` + `selftest_honest`,
   verified by `ls` after the removal). I have now also **patched my own adapter copies** so their
   default run dir resolves under `verify/out/fixture-runs/`, which is where pass-2's runs wrote.
   That closes the mechanism on my side; F6 is the corresponding request to the conformance owner.

I traced everything else with before/after snapshots of the whole tree (`a0/verify/snapshot.py`,
pass-2 pair `verify/out/snap_t2_before.json` / `snap_t2_after.json`): 1876 files added and 962
modified outside `a0/verify/`, essentially all under `a0/runtimes/{eve,loreley,simpleloop}/**` and
`a0/conformance/out/**` — the other workstreams' own concurrent work. Of the **346 files deleted**
outside my tree, **216 are my two fixture-run directories**; I checked the remaining 130 one by one
and they are the loreley/eve workstreams clearing their own `out/conformance-run`,
`out/_eidmap_probe` and similar run directories. Every runtime I drove was given a `--run-dir`
inside `a0/verify/`, and I ran the conformance runner from a byte-copy under `a0/verify/confrun/`
so its report, run dirs and adapter outputs landed in my own tree.

Post-audit re-check, to show the inputs were not disturbed by anything I ran:
`verify/check_cstar.py` → 14/14, 0 bad; `evalcontract.py recompute` → all `[ok]`;
`e_star.py` still `2abc6ea1…`, `C_STAR/manifest.json` still `8d9b9538…`.

---

## 6. What remains BLOCKED / UNVERIFIED

* **`C7.5` "no mock was silently substituted for a runtime" — the one UNPROVEN claim.** The only
  `monkeypatch`/`Mock`/`Stub` hit across all four adapters is KAPSO's *declared*
  `EvaluationMaintainer._run_agent` no-op (`runtimes/kapso/a0_adapter/runtime.py:288`), and each
  adapter publishes a `seams`/`unverified` block. My scan was lexical and I did not read every line,
  so I cannot prove the negative. What I established by execution is stronger for the seamed paths:
  the A0.1/A0.2 numbers come from real `E*` subprocesses and real runtime selection code in all four
  cases.
* **The full LLM-driven KAPSO campaign loop.** Declared UNVERIFIED by the adapter (ideation,
  implementation and judge are seamed). I verified the *selection* semantics on real strategy code
  with real `E*` scores, and separately verified one real `run_implementation` round
  (`runs/e2e-real`). I did not drive an unseamed end-to-end campaign loop.
* **Loreley's full `EvolutionWorker` + phased-measurement-cache orchestration.** Implied by
  `traps.json` T4's own `unverified` field. The reuse *decision* is the runtime's own; the worker
  that consumes it was not run end to end.
* **EvE's provider-side `web_search` tool.** No probe was possible; `closure.eve.json` says so.
  The record `evidence/10b_e2e_websearch_live.jsonl` shows the model replying `NO_WEB_SEARCH_TOOL`
  — an *absent tool*, which is the same evidentiary class the reconciliation correctly refuses to
  count as closure for KAPSO's claude lane. EvE's closed verdict is scoped to the
  candidate-execution (shell) channel and the record says so.
* **R1b (omission of `failure.kind`).** Still open in the checker; judged not to matter for A0.1 as
  this study runs it, because all four runtimes declare 9/9 kinds. The exact command that would
  settle it after a fix: re-run `verify/fixtures/adapters/omitter_adapter.py` through
  `conformance.py run` and require either FAIL or a non-`ok` verdict on `E-r-failure-kind`.
* **EvE's `failure_stage_counts` and KAPSO's `frozen_canonical_copy` in the workstreams' *stored*
  artifacts.** Both are stale relative to the code on disk (see §5). Settled by re-running
  `conformance.py run`; my own re-runs already show the corrected values.
* **`MISMATCH_FAILURE_STAGE`.** The runner has the constant and `selftest_wrong_failure_stage`
  fires, so the mechanism is tested; I did not find a real runtime that trips it, and I did not
  audit every declared stage value for the four runtimes beyond the aggregate counts.

---

## 7. Bottom line — quotable

**ACCEPTED (verified by my own execution, `a0/verify/` reproduces it):**

1. `EID* = 664115e0…` is frozen, single-input sensitive, and independently recomputable — I
   re-implemented the scheme myself and reproduced all five component digests plus `EID*`.
2. `C*` is intact (14/14 hashes) and `E*` is deterministic: all 14 results reproduced bit-for-bit,
   including the `invalid` and `error` candidates.
3. `E*` does not depend on cwd or `PATH` — a hostile cwd and a poisoned `PATH` leave the score
   bit-identical and never touch the decoys.
4. A0.1: all four runtimes now **PASS** my own conformance re-run, and the checker's fault matrix is
   **19/19** — including the two new fixtures for the failure-bearing surface.
5. A0.1's failure-bearing surface: my liar adapter (truthful `status`, false `failure_kind` on all
   nine non-ok rows) now **FAILS with `FG-FAILURE-KIND`**, `{MATCH: 5, MISMATCH_FAILURE_KIND: 9}`.
6. A0.2: all four selection semantics reproduced by me — KAPSO's ordered pair + reversals + tier
   control, EvE's frequency test (my own 3000 draws: 0.7357 vs closed form 0.73106, swap control
   0.2553, one sampler call per iteration), Loreley's same-cell replacement + cross-cell control,
   SimpleLoop's ordering invariance and the injected-score flip.
7. All four false-green trap families fire, and a crash recorded as `0.0` is **failed**, not passed.
8. Closure is measured, not asserted: I re-ran the CLI sandbox probe (host OPEN / workspace-write
   BLOCKED / full-access OPEN / `network_access=true` OPEN) and the four end-to-end model-lane pairs
   show real turns with the canary persisted in-lane; 5/5 `closed` mechanisms carry both controls and
   nothing closed rests on `inconclusive`.
9. Real-lane evidence is real: I reproduced SimpleLoop's 2.6251746109048 / 2.5414213562373096,
   EvE's 2.6168716968517516 and KAPSO's 2.451820520843313 with my own `E*` runs, and failed attempts
   are recorded as failures.
10. EvE's `EID_r` is now a genuine function of `EID*`: mutating `eid_star` changes the value, a
    mutated evaluator source is refused, and the adapter itself refuses a mismatched `EID*`.
11. All four runtimes now declare `failure_stage` counts equal to the frozen map over `C*`
    (`{none:5, verify_failed:5, resolve_failed:1, evaluator_failed:2, timeout:1}`), and KAPSO's
    re-adopted declaration digest `c1a99365…` is confirmed by my own computation.

**REJECTED: none of the pass-1 rejections.** All three (R1's false PASS, R2, R3) are fixed and
reproduced. The one thing I still reject is the *complete* version of R1's claim (R1b below), and
two auditor-constructed probes of the workstreams' own stored artifacts (C8.3, C8.4).

**PARTIALLY FIXED (one residual, recorded as a hole not a rejection):** R1b — an adapter can still
dodge the failure-kind check by *omitting* `failure.kind`; `E-r-failure-kind` reports `ok: true` on
`0/9` declared. Not live for this study (all four runtimes declare 9/9), but the check's `ok`
semantics are wrong and no fixture exercises the path.

**UNPROVEN:** that no mock was silently substituted for a runtime (lexical check only), plus the
scoped gaps above — KAPSO's unseamed campaign loop, Loreley's full `EvolutionWorker` cache
orchestration, and EvE's provider-side `web_search`.

**Worth quoting as a caveat, not a rejection:** EvE's A0.1 "14/14 agree" is 5 real measurements plus
9 *declared* synthesised failures — its lane cannot express `invalid`/`error` at all; and both
workstreams' stored conformance artifacts describe a code state older than the code on disk.

