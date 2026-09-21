# Independent verification — D2, D5, small items, fixture bookkeeping

Verifier: converge-d2d5. Date 2026-09-21. Repo `/home/ebt/rsi-dev` @ worktree HEAD `463e82df`
(working tree carries the authors' uncommitted convergence work; `git tag -l` = `a0-audited` only).

Read-only on everything verified. All writes confined to `a0/verify/converge-d2d5/` and ephemeral
`/tmp` scratch (removed). One model call total (see §D5.4). No DeepSeek call.

Tags: `[ran]` = executed here; `[src]` = read from source; `[inf]` = inferred.

---

## D2 — qualification predicate + freeze

### Tools (all `[ran]`)

| command | result |
|---|---|
| `python3 eligibility.py --self-test` | `predicate a0.eligibility/v2, 18 cases x 2 threshold vectors, 8 rules` / `self-test: ok`, exit 0 |
| `python3 eligibility.py --main-arm` | `R_A1^main = ['simpleloop']`; kapso out(R3,R6), eve out(R1,R3,R5,R6), loreley out(R3,R5,R6) |
| `python3 eligibility.py` (both vectors) | T_A1 \|Eligible\|=1 [simpleloop]; T_exploratory \|Eligible\|=1 [simpleloop]; the three excluded under T_exploratory by R3 only |
| `python3 build_qualification.py --check` | `qualification.json: matches its evidence`, exit 0 |
| `python3 build_qualification.py --self-test` | `attestation resolution self-test: 15 cases over 5 declared sources` / ok |
| `python3 verify_qualification.py` | `26/26 checks pass`, exit 0 |
| `python3 freeze.py self-test` | `a0.freeze/v1: 48 artifacts, 28 components` / ok |
| `python3 freeze.py check` | `MATCHES_ARMED` (document ALREADY armed, state `ARMED_NOT_FROZEN`) |
| `python3 freeze.py gates` | 6/8 pass; red: G5 (measurement), G6 (decision). exit 1 |

### Re-derived from primary evidence `[ran]`

`a0/conformance/report.json`, per runtime, from row fields:

- `verdict_before_attestation` → measurement axis. simpleloop 14×(MATCH/MATCH_VERDICT);
  kapso 14×; eve 5×MATCH + 9×SYNTHETIC_DECLARED; loreley 14×.
- `attestation_verdict` → acceptance axis. simpleloop 14×OK (ATTESTATION_OK); kapso/eve/loreley
  14×MISSING_ATTESTATION.
- `E-r-equals-E-star.measurement_agreeing` = 14 and `measurement_disagreeing_candidates` = [] for
  **all four**; the `measurement-attestation` check is `ok=false, required=true` for the three.

So the claim "kapso/eve/loreley are now non-accepting with `MISSING_ATTESTATION` while their numbers
still agree 14/14" is **true from the machine-readable output**. Runner's folded `state`:
simpleloop PASS, others FAIL — and the kapso `reason` says the numbers agree but the token is
missing. The measurement/acceptance split the author describes is genuinely present in the fixed
report.

Closure component vs primary records: simpleloop CLOSED (closure.simpleloop.json verdict=closed,
study_verdict=CLOSED); kapso CONDITIONAL (inconclusive/CONDITIONAL); eve CONDITIONAL
(closed/CONDITIONAL); loreley CONDITIONAL (inconclusive/CONDITIONAL). `build_qualification.py`
reads `a0/closure/closure.<r>.json` (line 683) plus the reconciliation file. Match confirmed.

No freeze tag: `git tag -l` → `a0-audited` only; no `a0-frozen*`; only `A0.freeze.candidate.json`
exists (`ARMED_NOT_FROZEN`). `freeze freeze --no-tag` on the tree exits **2** and writes no
`A0.freeze.json` `[ran, in a copy]`. G5 red is genuine (evidence: the three `MISSING_ATTESTATION`
lanes); G6 is correctly typed `kind=decision`.

### Falsification attempts

- FA1 `[ran]`: injected `FAIL` into `T_exploratory.attested_allowed` in memory; the author's guard
  fires (`T_exploratory.attested_allowed admits FAIL`), self-test returns 1. The claim holds.
- FA2 `[ran]`: setting `a0_1_attested/mechanism/bridge/closure/mrc .value = "FAIL"` is rejected by
  T_A1 **and** T_exploratory; `a0_1_measured.state="FAIL"` is rejected. Confirmed "no vector softens
  a FAIL".
- **F1/F2 (new, found)** `[ran]`: the predicate accepts structurally-malformed vectors that the doc's
  "fails closed: a component that is absent, empty, or **outside its declared domain** makes its rule
  false" implies it should reject:
  - `a0_1_measured = {value:"FAIL", measured:14, total:14, state:"PASS"}` → **eligible under T_A1**
    (`value` is display-only; the rejection carrier is `state`, which no rule cross-checks against
    `value`).
  - `a0_1_adapted = {value:"9/14", total:14}` with no `adapted` field → **eligible under T_A1**
    (`int_of` defaults a missing `adapted` to 0, so R0/R2 read it as "no adapted rows").
  Not reachable through `build_qualification.py` (it always emits consistent fields), so `R_A1^main`
  is unaffected today, but the six `*_DOMAIN` constants are defined and **never used as guards**
  (dead code), and the "out-of-domain ⇒ false" statement is not literally implemented for these two
  components.

### Overstatement found

- `E-r-equals-E-star.ok` **is still folded**: for kapso/eve/loreley it is `false` although
  `measurement_agreeing=14` / `disagreeing=[]`. The check's `detail` string separates the axes
  correctly and the consumer (`build_qualification.py`) uses `measurement_agreeing`, not `ok` — so
  the exposure is mitigated — but the check keeps a name that says "E_r equals E*" while its `ok`
  flag answers the acceptance question. Any future consumer keying on `check.ok` by id re-introduces
  exactly the conflation the author reports fixing.
- `G1_d1_landed` is typed `kind=measurement` with a behavioural description, but its implementation
  is a substring test for `"EXECUTION_ENV_DRIFT"` in `conformance.py` — a presence check, not a
  behavioural measurement.

---

## D5 — cleanup and hygiene

### Teardown `[ran]`

`docker ps -a` / `docker network ls` / `docker volume ls`:

- **No** `a0pc-*`, `a0tl-*`, `a0-loreley-*` containers; none of the five networks
  (`a0pc-internal`, `a0tl-internal`, `a0-egress-internal`, `a0-loreley-internal`, `a0-loreley-net`).
- `adapdc-catalog-postgres-1` untouched and up:
  `ID=ec2bbaf149c24317e300ea614110d0b7105daa329e95707148766933ca860a25`,
  `StartedAt=2026-09-21T01:11:40.508456929Z`, `RestartCount=0`, `Health=healthy`,
  network `adapdc_temporal-network` only — byte-identical to the recorded baseline.
- Removed probe volumes `eaef1648…c3bad` and `badcca77…d480dc` are absent; the 23 remaining volumes
  match the author's retained list exactly. The 4 unattributed study-era volumes are still present
  (reported, not deleted), as claimed.

### Config change `[ran]`

- Backups exist, mode 600, digests match the report exactly:
  `b38d6588…cab6` (config.toml), `6bbf3e32…43a4` (settings.json), `c8e52ceb…8e82` (auth.json).
- `diff backup current` = **exactly one line**: `base_url "https://zjapi.com"` → `"…/v1"`.
- `~/.kimi-code/config.toml:21` carries `http://127.0.0.1:15722/v1`; `ss -ltnp` shows no listener on
  15721/15722. The brief's premise correction is accurate.
- Endpoint probe (no auth): `POST https://zjapi.com/responses` → **404 `Invalid URL (POST /responses)`**;
  `POST https://zjapi.com/v1/responses` → **401 `Invalid token`**. The bug and the fix are confirmed
  at the HTTP level without a model call.
- **One real model call**: `codex exec … "Reply with exactly the two characters: OK"` →
  `codex / OK / tokens used 14,693`, exit 0. (Author recorded 14,425; the count varies, so
  "14,425 tokens each" is not deterministic — cosmetic only.) **Spend: ~14.7k tokens, zjapi/gpt-5.6-terra.**

### Key hygiene `[ran]` — non-vacuous

Read the four values from `~/gptapi.md` into variables (never printed); `grep -rIl -F` over the
working tree, `git grep` over every commit, `zstd -dc | grep` over the archive trees; positive
control `EID*`:

| key | tree | history | archive trees |
|---|---|---|---|
| chagpt / deepseek / openrouter / gmi-cloud | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 (all 6 tars) |
| **control EID\*** | **993 files** | **759,646 path-hits** | **50,635–50,636 hits** |

Vacuity check: grepping the **compressed** `.tar.zst` directly returns **0 even for `EID*`** — so the
author's decompression step was necessary and they did it. Fingerprint
`sha256(deepseek key)[:8] = b194aef5` reproduces the value recorded in
`a0/notes/exit-closed/claude-deepseek-2.1.278/REPORT.md:243`.
Archive **bundles** (section D of the report) were *not* independently re-run (mirror-cloning 6
repos is expensive); the tree sweep is the load-bearing surface and is confirmed non-vacuous.

### Overstatement found

- Report §1.3 says "the four pre-existing `adapdc-*` exited containers" — the evidence (`03_after.txt`)
  and the live host show **five** (`postgresql`, `temporal`, `temporal-admin-tools`,
  `temporal-create-namespace`, `temporal-ui`). The count in prose is wrong; the transcript is right.

---

## Small items

### (a) MRC enumeration `[ran]`

`git ls-files` split at each declared preimage root reproduces the table exactly:
kapso 11/3344, eve 12/1167, loreley 14/5278, simpleloop 14/5463. The "instrument-shaped outside the
preimage" lists match (`config/`, `contract/`, `bin/`… for kapso; `tools/`, `steps/`, `selection/`
for eve; 3 plugin modules + 21 `llm-round/` files for loreley; `policy/`, `solvers/`, `tools/`,
`tests/` for simpleloop). `mrc.py validate` passes for all four; `verify_adapter_preimage.py`
reproduces all seven adapter digests. The load-bearing claim — the evaluator step / plugin / policy
files decide scores while sitting outside every frozen digest — holds: `EID*.EvaluatorSource` covers
only `{e_star.py, e_star_child.py}`, and each `adapter_source_sha256` preimage is the adapter
*package* only, so none of those files is inside either digest.

### (b) Path independence `[ran]`

Copied `a0` to `/tmp`, ran from the copy:
- All four adapters resolve to the **copy**: simpleloop `DEFAULT_WORK_ROOT=/tmp/…/copy`,
  kapso `a0_root=/tmp/…/copy/a0` (state_root under the copy), loreley/eve `A0_ROOT=/tmp/…/copy/a0`.
- `loreley eidr-recompute` exit 0; `simpleloop -m a0_adapter conformance` exit 0, 14 candidates,
  `failed=[]`.
- Control: hiding the copy's `plumbing.EID.proposed.json` fails with the **copy's** path (exit 3).
- **Nothing landed in the original**: `find a0/runtimes|a0/contract -newer marker` = 0/0 (and a
  whole-`a0` scan excluding `__pycache__` = 0).
- Manifests: only **kapso and loreley** ship a top-level `adapter.json`; both use relative
  `cmd`/`pythonpath`/`interpreter`. Copy-side runner discovery returns copy-local argv for all four.

### (c) EvE RNG `[ran]`

`/tmp/eve` @ `979065fd…`, `git status` clean after the probe. `probe_rng_injection.py` exit 0.
`grep seed|rng|random` over `configs/` returns only `seed_solver_score`/`seed_solver_skip_evaluation`
(not RNG seeds). The `path:line` anchors all resolve: `uniform.py:19-25` (`**_ignored_kwargs`),
`uniform.py:32,35` (call-time `rng or random.Random()`), `base.py:33,40`,
`solver_workspace.py:61,91`, `factory.py:296-297/308-314/321-328` (no `rng=` passed),
`phase2.py:566,633` (call sites pass the population `_rng`). `rank_softmax` `__init__` likewise
swallows kwargs. Conclusion (replication, not seed-fixing) follows from D4's no-patch constraint,
and the report tags the A1-estimand argument `[inferred]` honestly.

---

## Fixture bookkeeping

### Pin chain `[ran]`

`sha256(a0/conformance/conformance.py) = e40d008d9ad0874b0241143c7b436df7640f1e9a7e4af55b443d88469f0978ce`
= pin 3 in `REPORT.md` §6. **Coherent.** Pin 2 `f33659f6…b50c` is a real committed blob
(commits `f4aa6154`…`463e82df`). **Caveat:** pin 1 `45cc4e90…6edf` does **not** appear in git history
(it was a working-tree-only revision) — that link rests solely on the retained report copy in
`out/conformance.pin45cc4e90/`, i.e. it is not independently recoverable.

### Claims `[ran]`

- "only `eplus_control_py314` changes **state** with `--envelope off`": true —
  `reprocheck.off-vs-pin.json` shows the only state flip is `eplus_control_py314: FAIL→PASS`
  (14× `EXECUTION_ENV_DRIFT`).
- Disclosed wording deviation: `eplus_mut_own` changes only its `reason` string and per-row `notes`
  (`… NO interpreter in the declared allowed execution set` vs `a different file was evaluated …`);
  verdict stays `MISMATCH_DIGEST`, `delta=0.0`, status/value/failure_kind unchanged. **Wording only,
  not a verdict — the disclosure is accurate** (and the author even quantifies it as "five rows
  exactly").
- Headline D3 claim verified from the attested artifacts: `eplus_d3_control` PASS;
  `eplus_d3_claim_measured`/`twin_measured`/`fulltheta_measured` **FAIL 14× `MISMATCH_ATTESTATION`**;
  `eplus_d3_claim_copy` and `eplus_d3_fulltheta_copy` **PASS 14/14** (adapter `--attestation copy`
  copies the token's own `evaluator_source_sha256`/`candidate_sha256`/`behaviour_digest`/
  `canonical_digest` verbatim while running `E'`/`E''`). So D3 raises the cost from free omission to
  active forgery, and the token-copy lane still passes — as stated.
- `reprocheck.pin1-vs-pin2.json` `identical: True`; `reprocheck.e40-required.json` `identical: False`.

### Cross-item falsification (new) `[ran]`

Does the A0 freeze cover the unfrozen instruments the MRC report names? In a copy, a 1-byte append to
`a0/runtimes/eve/steps/eve_evaluator_step.sh.tmpl` left `freeze.py check` at **`MATCHES_ARMED`**,
while appending to a *listed* artifact (`a0/runtimes/eve/selection/eve.selection.json`) produced
`DRIFTED_FROM_ARMED / artifact changed`. This corroborates the MRC finding and extends it: the
evaluator step, the Loreley plugin, the KAPSO mode config and the SimpleLoop policy are outside the
**A0 freeze's own 48 artifacts** too, not just outside `adapter_source_sha256`. The freeze's doc is
scoped to its artifact list, so this is a residual gap (matching MRC §7's open item), not a false
claim — but it means "any artifact byte unfreezes" is only true for the listed 48.

### Overstatement found

- README headline: "the four passes become `MISSING_ATTESTATION` failures, and **only** the row that
  was already failing on behaviour (`eplus_mut_own`) keeps its verdict." `eplus_mut_echo` and
  `eplus_control_py314` also keep a `FAIL` state (their reasons change). The table below it is
  precise; the headline sentence is shorthand that reads as if only one row kept `FAIL`.
- REPORT's citation "the worker-evaluator plugin … (`WORKER_EVALUATOR_PLUGIN`), `runtime.py:37`" is
  off by a line: `runtime.py:37` defines `PLUGIN_SOURCE`; `WORKER_EVALUATOR_PLUGIN` is assigned at
  line 79. Substance correct.

---

## Verdicts

| item | verdict |
|---|---|
| D2 predicate, T_A1 / T_exploratory, R_A1^main / R_exploratory | **ACCEPTED** (with two robustness caveats: malformed-vector acceptance; `E-r-equals-E-star.ok` still folded) |
| D2 freeze mechanism, no tag, red gates | **ACCEPTED** (G1 gate is a substring check labelled "measurement") |
| D5 teardown + adapdc untouched | **ACCEPTED** |
| D5 config fix (codex `/v1`) + backup | **ACCEPTED** |
| D5 key hygiene | **ACCEPTED** (non-vacuous; bundles section not re-run) |
| small (a) MRC enumeration + frozen-digest gap | **ACCEPTED** |
| small (b) path independence + manifests | **ACCEPTED** |
| small (c) EvE RNG | **ACCEPTED** |
| fixture pin chain + off-vs-pin + D3 headline | **ACCEPTED** (pin 1 not git-recoverable) |
