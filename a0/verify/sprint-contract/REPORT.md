# Independent verification — contract-side items (qualification, EvE label, attestation, MRC, archive)

Verifier: independent second verifier, owns `a0/verify/sprint-contract/**`. Read-only everywhere else.
Date of run: 2026-09-21. Host interpreters: `python3` = 3.14.7; frozen E* venv = `a0/tasks/circle-packing/.venv/bin/python` = 3.12.11.

Method: **re-derive, do not re-read.** Every command below was run by this verifier. Where a run
would have written into a directory under verification (the conformance runner, `selftest.py`,
`attest.py`, `demo.py`), it was run inside an isolated copy of the repo at `/tmp/sv/rsi-dev`
(`cp -a`), never in place. The copy was made from the working tree; source hashes were checked.

**Verification-hygiene disclosure (round 2).** Copy-isolation is **not** complete for the conformance
runner: the adapters hardcode the host root (`a0/runtimes/loreley/src/a0_adapter/contracts.py:13`
`A0_ROOT = Path("/home/ebt/rsi-dev/a0")`; `a0/runtimes/simpleloop/a0_adapter/cli.py:34`
`DEFAULT_WORK_ROOT = "/home/ebt/rsi-dev"`), so running the runner from `/tmp/sv3` still wrote run
artifacts into the **original** `a0/runtimes/{simpleloop,eve,loreley}/out/` (confirmed — `/tmp/sv3`
paths appear inside `a0/runtimes/loreley/out/conformance/adapter.md`). No tracked **source** outside
`a0/verify/sprint-contract/` was edited; the affected paths are run outputs under `out/` (one tracked
file, `a0/runtimes/loreley/out/conformance/adapter.md`, shows modified). The tree was already dirty
from the sprint, and the runner regenerates these files on every run, but this verifier's re-runs
contributed to them. It is also a finding in its own right: the adapter is not path-independent,
despite the runner's comment that "the adapter still must not depend on cwd" — it depends on an
absolute hard-coded root instead.

Revision pins checked before trusting any quoted verdict (round 1):

| file | value | matches author's pin? |
|---|---|---|
| `a0/conformance/conformance.py` sha256 (round 1) | `45cc4e90b9c65c0a0139c336ed1d23288fa242512ba7a8970190a9f1f72f6edf` | yes — `a0/fixtures/observational-equivalence/REPORT.md` §6 pins exactly this. **Superseded in round 2**: the file now hashes to `f33659f6…` (edited 16:24:53) — see §2 |

---

## Verdict table

| # | item | verdict |
|---|---|---|
| 1 | `a0/qualification/` `Q_r` + `Eligible(r)` | **PARTIALLY ACCEPTED** — pipeline and re-derivation reproduce; the predicate admits an `UNPROVEN` E2E component under `T_literal` (falsification below) |
| 2 | EvE label fix (`a0/conformance/`) | **ACCEPTED for the claim, with a pin caveat** — authoritative machine fields correct; the round-1 bare-PASS nuance is resolved (field renamed `adapter_claim__untrusted`). But `conformance.py` moved to `f33659f6…` at 16:24:53 after round 1, so the fixture report's §6 pin is stale — see §2 |
| 3 | `a0/attestation/` | **ACCEPTED** for producer/verifier behaviour; the py3.14 false red is **STILL LIVE** and **REPRODUCED in the conformance runner** (the author flagged it, so the report does not overstate) |
| 4 | `a0/mrc/` | **ACCEPTED** (re-verified after the fix) — previously recorded UNPROVEN (`adapter_source_sha256` had no preimage); now reproduced end-to-end by this verifier from `git` bytes with independent code. One scope caveat remains (see §4) |
| 5 | `a0/archive/` + `/home/ebt/rsi-archive/` | **ACCEPTED** |

This report was revised after the MRC workstream shipped a fix for item 4; §4 below is the
re-verification and supersedes the first round's UNPROVEN verdict. Items 1, 2, 3, 5 are from the
first round and unchanged.

---

## 1. `a0/qualification/` — `Q_r` and `Eligible(r)`

### Reproduction (all pass)

```
$ python3 verify_qualification.py        # 15/15 checks pass, exit 0
$ python3 build_qualification.py --check # "matches its evidence (re-derived ...)", exit 0  (writes nothing)
$ python3 eligibility.py --self-test     # "predicate a0.eligibility/v1, 10 cases x 2 threshold vectors / self-test: ok"
```

`build_qualification.py --check`/`--stdout` write nothing (`build_qualification.py:577-603`); the bare
form writes `qualification.json`, so it was deliberately not run.

### Re-derived by hand from the primary artifact (`a0/conformance/report.json`, not the builder's file)

Walking `runtimes.<r>.rows` and counting `verdict ∈ {MATCH, MATCH_VERDICT}` with
`evaluator_evidence_status` fresh:

- **EvE**: 5 rows `MATCH`/`ok` (c01,c02,c03,c04,c14) + 9 rows `SYNTHETIC_DECLARED`/`synthesized_failure`
  → **measured = 5, adapted = 9**. Matches `report.json` and `qualification.json`.
- **KAPSO**: 14 rows accepting, all `evaluator_evidence_status = ok` → **measured = 14, adapted = 0**. Matches.
- This is byte-identical to the runner's own logic (`conformance.py:2374-2383`): `measured_rows =
  verdict in (MATCH, MATCH_VERDICT) and eval_status not in NON_FRESH_EVIDENCE`. The split is derived
  from primary row records, not a summary.
- The 9 EvE "adapted" rows are exactly `C*`'s non-`ok` members; the 5 "measured" are the `ok` members.
  Consistent with QUALIFICATION.md §1.

**Closure component vs primary `a0/closure/*.json` (not a summary).** All four match the raw record's
`verdict`+`study_verdict`, and the `justification` mechanism lists match `closure.<r>.json.mechanisms`:

| runtime | `closure.json` verdict / study_verdict | `Q_r.closure.value` |
|---|---|---|
| simpleloop | closed / CLOSED | CLOSED |
| kapso | inconclusive / CONDITIONAL | CONDITIONAL |
| eve | closed / CONDITIONAL | CONDITIONAL |
| loreley | inconclusive / CONDITIONAL | CONDITIONAL |

**Thresholds are what the report says.** `required_measured(T_strict,14)=14`, `required_measured(T_literal,14)=1`;
`T_strict.e2e_allowed={COMPLETE}`, `T_strict.closure_allowed={CLOSED}`; `T_literal` widens both — exactly
the QUALIFICATION.md §2 table.

### Falsification: the predicate marks a runtime eligible with an `UNPROVEN` component

`E2E_DOMAIN` includes the literal token `UNPROVEN`, which fails R4 under **both** vectors. But the
reported runtimes encode their *unproven* E2E as `ATTEMPTED`/`PLANNING_ONLY`, and their *unproven*
closure as `CONDITIONAL` — both of which `T_literal` accepts:

```
eve     e2e=ATTEMPTED  closure=CONDITIONAL -> T_strict=False T_literal=TRUE
loreley e2e=PLANNING_ONLY closure=CONDITIONAL -> T_strict=False T_literal=TRUE
```

QUALIFICATION.md's own `unproven` table (§5) says "EvE completes a real round end to end" is
**UNPROVEN** and "Loreley completes a real round end to end" is **UNPROVEN**, and the closure records
are flagged **NOT RECONCILED** against the 2026-09-21 topology. So under the declared default
`T_strict` this is contained; but if the coordinator picks `T_literal` (one of the two the report
explicitly offers as "the open decision"), `Eligible(eve)=true` on an E2E component the same report
calls unproven. The predicate cannot distinguish "E2E completed" from "E2E attempted" without the
threshold vector; nothing records the epistemic status as data. Minimal reproduction: the two lines
above via `eligibility.eligible(_q(...), 'T_literal')`.

**Not a defect in the arithmetic** — `T_literal` is honest about what it accepts. It is a scope limit
the report should state in the predicate section, not only in the prose `unproven` table.

---

## 2. The EvE label fix (`a0/conformance/`)

### Reproduction (all pass)

- `conformance.py run` re-run in the isolated copy reproduces the shipped verdicts exactly:
  `simpleloop/kapso/loreley = "PASS (14/14 measured)"`, `eve = "PARTIAL (5/14 measured)"`,
  `n_pass=3, n_partial=1, n_fail=0`, `r_1_a0_1_only=['simpleloop','kapso','loreley']`,
  `r_1_a0_1_partial=['eve']`, `runtimes.eve.state='PARTIAL'`.
- `selftest.py` re-run: **20 fixtures, "all fixtures behaved as expected: True"**; `selftest_synthetic_declared`
  behaves as `PARTIAL` (the corrected expectation). Shipped `selftest_report.json` also records 20 fixtures, `all_fixtures_behaved: true`.
- `report.md` prints the split (`eve | PARTIAL (5/14 measured) | 5/14 | 9/14 (c05…c13) | …`).

### Machine-readable "no bare PASS for EvE"

Walked every JSON scalar in `report.json`. The authoritative fields are all correct:
`verdicts.a0_1.eve = "PARTIAL (5/14 measured)"`, `verdicts.a0_1_state.eve = "PARTIAL"`,
`runtimes.eve.state = "PARTIAL"`, `qualification.a0_1.label = "PARTIAL (5/14 measured)"`.

**However** a literal bare `"PASS"` for EvE was present in the same document, twice, in round 1:
`.runtimes.eve.adapter_declared_verdict = "PASS"` and `.runtimes.eve.adapter_declared.verdict = "PASS"`.
This is the *adapter's own* declared verdict (recorded but "never trusted"), so a consumer that naively
greps the document for `eve`+`PASS` could read it.

**Round-2 status: mitigated.** `a0/conformance/conformance.py` was edited at 16:24:53 (new sha
`f33659f6…`, see below) and the regenerated `report.json` (generated_at 16:25:11) now carries that
adapter claim under field names that say what they are:
`.runtimes.eve.adapter_claim__untrusted = "PASS"` and
`.runtimes.eve.adapter_self_declaration__untrusted.claim__untrusted = "PASS"`;
`adapter_declared_verdict` is now `None` for all four runtimes. The reviewer's requirement
("EvE must never read PASS") is satisfied for both the runner's verdict and the adapter's claim.

### Blast radius / revision pin — MOVED after round 1

In round 1 the fixture report's §6 pin and the file agreed byte-for-byte
(`45cc4e90b9c65c0a0139c336ed1d23288fa242512ba7a8970190a9f1f72f6edf`). **That is no longer true:**
`a0/conformance/conformance.py` was modified at **16:24:53** and now hashes to
`f33659f605f6a6892e9d0f766961a13eeb55ddc4225776ad34fb974cdecfb50c`. So the fixture report's §6 pin is
stale, and its own instruction applies ("If any of those move, re-run `run_conformance_probe.sh` before
quoting these rows"). The fixture report's §2 rows were not re-run here (out of this round's scope).

Against the **new** revision (`f33659f6…`) I re-ran the four-runtime runner in an isolated copy: the
labels reproduce exactly (`eve = "PARTIAL (5/14 measured)"`, `n_pass=3, n_partial=1`,
`r_1_a0_1_only=['simpleloop','kapso','loreley']`), `selftest.py` still reports "all fixtures behaved as
expected: True", and the only exact `"PASS"` strings under an `eve` path are the two `…__untrusted`
adapter-claim fields. The fixture report's §6 pin (`45cc4e90…`) is the outstanding stale reference and
its §2 rows should be re-run under `run_conformance_probe.sh` before being quoted. Boundary check read
from source: `PARTIAL` is only reached after the `FAIL` branches, so a runtime with a failed check and
adapted rows is `FAIL`, never `PARTIAL`.

---

## 3. `a0/attestation/`

### Reproductions

Real E* (`c01_good_hex`), frozen interpreter 3.12.11:
```
Q1_recomputes RECOMPUTES  Q2_semantic SEMANTIC_MATCH  Q3_realization REALIZED   exit=0
```
Adversarially altered evaluator (a copy of E* with `sum_radii += 1e-3`, run at 3.12.11):
```
Q1 RECOMPUTES  Q2 SEMANTIC_MATCH  Q3 NOT_REALIZED   exit=3
```
`selftest.py` (in the copy): **11/11 checks pass**. `demo.py` (in the copy): control + d1 shadow,
d2 stale bytecode, d3 other-file all reproduced; each attack `NOT_REALIZED` (rc=3) with the
predicted catch reasons; "declared E* source unchanged across all demos: True".

### The py3.14 false red — STILL LIVE

`attest.py` runs the subject with `sys.executable` (`attest.py:546`). With the real, byte-identical E*
but the producer invoked under `python3.14`:

```
EID_semantic  664115e0…9328   (frozen, correct)
EID_execution 62e8514c… (differs)
Q1 RECOMPUTES  Q2 SEMANTIC_MATCH  Q3 NOT_REALIZED  exit=3
  [FAIL] the outcome matches the frozen reference table row for this candidate
```

Root cause, measured directly on the same c01 outcome: both runs have `status = ok`, and the **only**
differing keys anywhere in the outcome are `interpreter` and `canonical_digest`:

```
p312 canonical_digest 1144adc6… = frozen expected   interpreter 3.12.11
p314 canonical_digest c45d79ee… != frozen expected  interpreter 3.14.7
```

So a byte-identical evaluator on a different interpreter build is failed. This is not fixed.

### The same root cause in the conformance runner — REPRODUCED

Read from source: `conformance.py` never compares the `interpreter` block
(`grep interpreter`: only launch/report sites, lines 730/863/968-998/2568); it compares
`canonical_digest` (`conformance.py:806`, `:1618`), which embeds `interpreter.version`.

Reproduced end-to-end in the isolated copy: I built a copy of the study's own honest control adapter
(`fixtures/adapters/reference_adapter.py`) with its evaluator python patched to `/usr/bin/python3.14`,
and drove the real runner with it:
```
$ python3 a0/conformance/conformance.py run --runtimes simpleloop \
    --adapter "simpleloop=python3 …/adapters-py314/reference_adapter.py" --no-controls --out false-red.json
    FAIL: E_r(c) disagrees with E*(c)
    row verdicts: Counter({'MISMATCH_DIGEST': 14})
    row0: e_r_value = 2.4519205208433132  e_star_value = 2.4519205208433132  delta = 0.0
```
An honest adapter whose values agree to the last bit is FAILed because `canonical_digest` embeds the
interpreter build. The study's four shipped adapters do **not** trigger this — they all pin
`E_STAR_PYTHON` — so it is latent, but it is real and it is the same defect the fixture report's
§2.3 `eplus_control_py314` row shows. The author's own README/FIELDS report the 3.14 control failure;
this verifier confirms it is still present and adds the conformance-side measurement.

---

## 4. `a0/mrc/`

### Reproduction (all pass)

- `mrc_selftest.py` (run in an isolated copy, `/tmp/sv2`): **44/44 checks passed**, exit 0.
- `verify_adapter_preimage.py`: **every adapter digest is reproduced from its preimage**, exit 0.
- `mrc.py validate` on all four declarations → valid, exit 0, MRC* values match the *current* REPORT.md
  §1 (`0d98045b…`, `f31802ac…`, `e80a3530…`, `046ca78c…`).
- All **14** negative fixtures → exit 1 with the specific codes REPORT.md claims (endpoint/model/surface
  drift, eid drift, echo-as-proof, weights-claim, null-digest, policy primary/OpenRouter, hygiene,
  digest tamper, adapter missing, and the two new adapter-preimage codes).

### Decisions encoded as the user set them

All four declarations carry the identical `model_policy`:
`primary="deepseek-flash"`, `mixed_secondary_allowed=true`, `permitted_secondary=["deepseek-v4-pro"]`,
`excluded_providers=["openrouter"]`. `identity_evidence` is per-surface, not a blanket claim: 15
`observations` rows each name `surface`, `requested_model_id`, `echoed_model_id`, `echo_is_verbatim`,
`proves_weights=false`, plus a `cross_surface_divergence` block. Correct.

## 4. `a0/mrc/` — re-verified after the workstream's fix

### What changed, and what I re-derived (round 2)

First round: the four `RuntimeAdapters[].adapter_source_sha256` values matched no file in the repo
(repo-wide scan of 106,768 files) and were **UNPROVEN**. The workstream replaced the hard-coded
literals with a recomputable preimage rule and shipped `verify_adapter_preimage.py`. **I re-derived
everything with my own code** (`a0/verify/sprint-contract/mrc-recompute.py`, which shares nothing with
`a0/mrc`): read `git ls-tree -r <commit> -- <root>`, hash each blob with `git show`, build
`[[path, sha256], …]` in ascending path order, and apply
`sha256(b"a0/mrc/v1/RuntimeAdapters/adapter_source" + b"\x00" + canonical_json(payload))`; then
recompute `MRC* = sha256(b"a0/mrc/v1/MRC*" + b"\x00" + canonical_json({component: digest}))` from the
declaration's own `component_digests`.

```
[ok ] kapso       n=11  recomputed=3ab3e139569bc49bf0c21e72521d690673c18ac2533d133ce10a344aa66fa3a4  list_matches_repo=True
[ok ] eve         n=12  recomputed=57a5c251416f9b378b90fae078bdf2e57a4c8096410b3beadb349722d7eddb70  list_matches_repo=True
[ok ] loreley     n=14  recomputed=3ab1436fe69cb7cb29b780e4c160b69009fb04403ddd5d90e350e9b048c165df  list_matches_repo=True
[ok ] simpleloop  n=14  recomputed=167fe070911bb7a4767690e387e6fa2d138ec61cf31b3f6c7014814b1d5bcc89  list_matches_repo=True
MRC* codex=0d98045b…ac4e4  claude=f31802ac…fb66  kilo=e80a3530…5773  opencode=046ca78c…f131   (all match)
RESULT: ALL REPRODUCED
```

The author-stated numbers (4 adapter digests, 4 MRC*) reproduce exactly, and the recorded
`adapter_source_files` equal the repo's file set at `261f0c9` for every runtime. `adapter_commit`
resolves to `261f0c91eeef…`; working tree == commit == declaration for all **51/51** preimage files.
`adapter_commit` is the short form `261f0c9`; `git ls-tree`/`show` resolve it correctly.

Independent corroboration: `verify_adapter_preimage.py` → "every adapter digest is reproduced from
its preimage" (exit 0); `mrc_selftest.py` **44/44**; all **14** negative fixtures exit 1 with their
codes, including the two new ones `MRC-ADAPTER-PREIMAGE` (digest with no preimage / non-ascending
order) and `MRC-ADAPTER-DIGEST` (digest not the hash of the listed preimage). `mrc_selftest.py` was
run in a lighter isolated copy (`/tmp/sv2`) because it rewrites `fixtures/negative/*`.

### Falsification of the new rule — it is well-defined

| attempt | effect on the digest |
|---|---|
| change one file's `sha256` in the list | changes (`888d7eb8…`) — not a function of the path list alone |
| **reverse the list order** | **changes** (`97e7e2ce…`) — **order IS significant**; the validator also rejects non-ascending order |
| re-serialize with `indent=2` | changes (`fbc8d55d…`) — serialization is load-bearing |
| use a JSON object instead of `[[path,sha],…]` | changes (`deb32a33…`) |
| drop `/adapter_source` from the domain | changes (`9673fc7b…`) |
| pass a **different commit** with identical blobs (`HEAD`, `a0-audited`) | **unchanged** — the digest is content-addressed, not commit-string-addressed. This is correct design, not a defect; it means the value moves iff the bytes move |

So there is no ordering defect: the digest is domain-separated, order-sensitive, serialization-
sensitive, and content-based.

### Falsification of a frozen field (rebuilt fixtures)

My old `mrc-falsify/**` fixtures embedded the pre-fix digests and were **stale** (they fail with
`MRC-ADAPTER-PREIMAGE`, which is expiry, not a finding). I rebuilt all of them from the **current**
`declarations/codex-deepseek-responses.spec.json` and re-ran:

| perturbation (self-consistently recomputed via `mrc.py compute`) | result |
|---|---|
| `Endpoint.base_url` → openrouter | **FAIL** `MRC-ENDPOINT-DRIFT` (external `frozen_routes.json`) |
| `RequestedModel.requested_model_id` → `deepseek-v4-pro` | **FAIL** `MRC-MODEL-DRIFT` |
| `Tools.tool_choice` `auto`→`none` | **valid** (only MRC* moves: `8ee5ce35…`) |
| `Permissions.sandbox_mode` `read-only`→`danger-full-access` | **valid** (only MRC* moves: `a3779b94…`) |
| naive edit of `Tools`, digests left stale | **FAIL** `MRC-DIGEST-MISMATCH` (Tools + MRC*) |
| listed preimage sha changed, `adapter_source_sha256` kept | **FAIL** `MRC-ADAPTER-DIGEST` |
| preimage removed, digest kept | **FAIL** `MRC-ADAPTER-PREIMAGE` |
| preimage reordered (descending) | **FAIL** `MRC-ADAPTER-PREIMAGE` (`…must be listed in ascending path order`) |

These reproduce the workstream's own §7 measurements byte-for-byte, including the endpoint/model
MRC* values (`d5c9b929…`, `3b4a220e…`) and the tools/perms MRC* values (`8ee5ce35…`, `a3779b94…`).
The Tools/Permissions limitation is now **stated in REPORT.md §4** ("they are protected only by the
MRC* pin"), which closes the round-one documentation gap. A tool/permission change is still not
semantically rejected — that remains true and is now declared.

### Remaining scope caveat — the coverage statement is accurate but not exhaustive

REPORT.md §7 says the preimage is the adapter **package** and lists what it does *not* cover
(`loreley/bin/a0-loreley`, per-runtime `adapter.json`, installed upstream checkouts, `__pycache__`,
`out/`). The **positive** claim is exactly right: I confirmed the digest covers precisely the blobs
under each `adapter_source_root` (`a0/runtimes/<rt>/a0_adapter`, or `…/loreley/src/a0_adapter`). But
the enumerated exclusions are **not exhaustive**, and the omissions are instrument-shaped tracked
files outside the root:

| runtime | covered | notable **tracked** files outside the preimage |
|---|---|---|
| kapso | 11 | `config/` (4: `adapter.json`, 2 mode YAMLs, reqs), `contract/selection/kapso.selection.json`, `bin/` (3) |
| eve | 12 | `tools/` (5), `steps/`, `selection/` |
| loreley | 14 | `src/loreley_a0_plugin*.py` (**3 plugin/metric modules**), `bin/a0-loreley`, `policy/`, `probe/`, `infra/`, `llm-round/` (21), `tools/` |
| simpleloop | 14 | `policy/` (3), `solvers/main_run.json`, `tools/` (2), `tests/` (2), `conftest.py`, `pytest.ini` |

`__pycache__`, `out/`, and the upstream `checkout/` are excluded because they are untracked at
`261f0c9` (not in the commit), which matches the report; but "the adapter package" is narrower than
"the instrument". In particular loreley's metric/plugin modules and simpleloop's `policy/`+`solvers/`
are part of what decides a selection yet sit outside `adapter_source_sha256`'s claim. The report's
sentence "the field's claim is now exactly what it says" is true for the *definition*; the scope
*enumeration* should name these tracked exclusions too, not only the untracked ones.

### Record: previously UNPROVEN → now closed

**Closed by**: `verify_adapter_preimage.py` + `make_declarations.py --verify` + the four per-
declaration `adapter_source_files`/`adapter_source_root`/`adapter_source_rule` fields, and my
independent `mrc-recompute.py`. The first-round finding ("no file in the repo hashes to any of the
four values") is **resolved**: the values are now digests of a named, ordered file manifest taken
from `git ls-tree`, and I reproduced all four plus all four MRC* myself. No trace of the old values
remains in the declarations.

**Still not standing on its own**: the exclusion list in §7 is illustrative rather than complete (see
table above); and Tools/Permissions rest on the MRC* pin rather than on `frozen_routes.json` (now
declared). Neither is a defect in the fix; both are scope facts the next reader should have.

---

## 5. `a0/archive/` + `/home/ebt/rsi-archive/`

### Reproduction (all pass)

- `sha256sum -c SHA256SUMS` from the store root: **12/12 OK**.
- Author's verifier `a0/archive/restore_verify.sh` (offline, writes only to `/tmp`):
  **54 OK, 0 FAIL — "all artifacts restored and verified"**, exit 0. Its log is copied to
  `restore-verify.repro.log`.
- Independent restores by this verifier (manual `zstd | git fetch '<refs/*:refs/archived/*>' |
  git checkout --detach <commit> | git rev-parse HEAD^{tree}`):

| artifact | pinned commit | tree recomputed | provenance tree | match |
|---|---|---|---|---|
| rsi-dev-a0-audited.bundle | `2a61c56b…` | `29302a13…` | `29302a13…` | ✅ |
| kapso.bundle | `7d99b152…` | `281ddc61…` | `281ddc61…` | ✅ |
| loreley.bundle | `4c375920…` | `27702aab…` | `27702aab…` | ✅ |
| eve.bundle | `979065fd…` | `5d42deab…` | `5d42deab…` | ✅ |
| circle-packing.bundle | `b91c0906…` | `83aff89b…` | `83aff89b…` | ✅ |
| rsi-dev-head.bundle | `261f0c91…` | `258705c9…` | `258705c9…` | ✅ |

  `git fsck --full --strict` clean on the restored bundles. The `a0-audited` tar complement, extracted
  with its `rsi-dev-a0-audited/` prefix stripped and rebuilt with `git add -A -f` + `git write-tree`,
  also gives `29302a13…`. (My first tar rebuild mismatched because I did **not** strip the prefix —
  my error, not the archive's; the author's verifier handles the prefix.)

### Note on the `a0-audited` pin (not a discrepancy)

`git rev-parse a0-audited` returns `10fa652e…`, which is the **annotated tag object**; its commit is
`2a61c56b…`, exactly as provenance records. `git bundle list-heads` prints the tag object id, which can
look like a mismatch. Resolved.

### Licenses — read from each repo's own file

| repo | recorded | measured `LICENSE` sha256 | match |
|---|---|---|---|
| kapso | MIT | `84fa98c0…` | ✅ |
| loreley | Apache-2.0 | `c71d239d…` | ✅ |
| eve | Apache-2.0 | `59cde600…` (+ `NOTICE`, NUS) | ✅ |
| circle-packing | NONE_FOUND | no `LICENSE` at root | ✅ |
| rsi-dev (this repo) | NONE_FOUND | no `LICENSE` at HEAD/tag | ✅ |

### Store location / self-reference

- Store `/home/ebt/rsi-archive` is a sibling of the repo; neither contains the other.
- `git remote -v` on the working repo is empty (matches PROVENANCE.md).
- `git ls-tree -r` of the `a0-audited` and `HEAD` bundles contains **no `a0/archive`** path — the
  manifest/store is not inside any bundle (no self-reference).
- The DeepSeek key does not appear in the store (0 matching files; checked without printing it).

---

## Cross-cutting: do claims rest on files that changed since measurement?

- `conformance.py` — **moved after round 1.** Round 1: byte-identical to the fixture report's pin
  (`45cc4e90…`). Round 2: edited at 16:24:53 to `f33659f6…`; I re-ran the runner against it and the
  labels reproduce. The fixture report's §6 pin is now stale.
- `report.json` — my independent re-run reproduces it. ✅
- `a0/closure/*.json` — dated 2026-09-20; the qualification's `Closure` components are read from them,
  and the report **discloses** in `unproven` that they are "NOT RECONCILED" against the newer
  2026-09-21 proxy topology. Disclosed, but the `Closure` component of every `Q_r` therefore rests on
  evidence older than the topology it describes.
- MRC `RuntimeAdapters` — **resolved in round 2**: the digests are now the hash of a named, ordered
  file manifest and I reproduced all four from `git` bytes (see §4).
- `a0/attestation/**` — the fixture report (§6) flags this directory as "still in flight"; the fixture's
  §3.1 attestation quotes may predate the final `attest.py`/`verify_attestation.py` (mtimes 15:21/15:19
  vs fixture REPORT.md 15:24). This verifier re-ran the attestation block itself and it behaves as
  described; the fixture's own quotes were not re-verified here.

---

## Where reports say more than the evidence supports

1. **`a0/mrc/REPORT.md` — RESOLVED (round 2).** Round one: the four `RuntimeAdapters.adapters[].
   adapter_source_sha256` values matched no file in the repo (repo-wide scan of 106,768 files); the
   report's §6 claim that they were "read from the repo" was unsupported. The workstream replaced the
   hard-coded literals with a recomputable preimage and I reproduced all four values and all four
   MRC* myself from `git ls-tree` bytes. See §4.
2. **`a0/mrc/REPORT.md` §4 — RESOLVED (round 2).** The report now states explicitly that
   `Tools`/`Permissions` are protected only by the `MRC*` pin and gives the measurement; I reproduced
   it. The remaining, purely descriptive caveat: the §7 scope sentence names only untracked
   exclusions (`bin/a0-loreley`, `adapter.json`, upstream `checkout/`, `__pycache__`, `out/`) and
   omits tracked instrument files also outside the preimage (loreley's plugin modules, simpleloop
   `policy/`+`solvers/`, kapso `config/`+`contract/`, eve `tools/`+`steps/`+`selection/`). Scope
   enumeration, not a defect in the fix.
3. **`a0/conformance/report.json`** — the runner's verdict is fixed, but `runtimes.eve.adapter_declared_verdict`
   is still a bare `"PASS"`. A naive consumer can read `PASS` for EvE from the same document.
4. **`a0/qualification/QUALIFICATION.md` §2** — the predicate section presents `T_literal` as "the
   reading under which the study's existing wording is already sufficient" without noting that under it
   `Eligible(eve)=Eligible(loreley)=true` on E2E components the same report's `unproven` table calls
   UNPROVEN. The fact is disclosed elsewhere, not in the predicate section a reader would use.
5. **`a0/attestation/README.md`** — reports the py3.14 control failure as a known, passed-to-owner
   item; this verifier confirms it is **still live**, and that the same root cause produces a false red
   in the conformance runner (both measured). No overstatement, but the item is open, not closed.

No claim was found where a quoted number failed to reproduce, in either round. The round-one
provenance gap in `a0/mrc` (`adapter_source_sha256` with no preimage) is now **closed and
independently reproduced**; every remaining item is a scope/enumeration fact, not a fabricated number.
