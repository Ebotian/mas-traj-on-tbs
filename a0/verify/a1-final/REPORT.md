# Adversarial re-verification of the A1 testbed, final revision

Owner: `a0/verify/a1-final/**`. **Nothing was fixed.** Every finding is reported with a
minimal reproduction; every probe is read-only on other workstreams' trees, with one
exception named in §7.

Scope: items 1–5 of the assignment, plus two consequences I refused to take on trust
(§4). Zero model spend: no campaign, no paid probe, no network call. Every number below
comes from a command in this directory; the raw output of each is committed beside it
(`out_*.txt`).

**The revision I verified.** `8057c1cecc886c6575a86d8d1d90d57ea1751a77`. `HEAD` moved
*during* this pass: the session started at `3bff97b6`, and at 21:36–21:41 a sibling
workstream edited `a0/a1/probes/hostile_candidate.py` and
`a0/tasks/maxcut/generators/DEVIATIONS.md` in the shared working tree and committed them
as `8057c1ce` (it pins the hostile probe's "before" side to `75403e8c`, closing the 9/13
finding `a0/a1/DEVIATIONS.md` D-A1-13 left open). Neither file is in the identity chain,
in `a0/a1/verify.py`'s steps, in the contract, or in the calibration evidence, so the
findings below hold at both revisions; the identity and `verify.py` steps were re-run at
`8057c1ce` and are green there too.

## How to re-run everything

```console
$ sh a0/verify/a1-final/run_all.sh          # ~3 minutes, model-free
```

It runs, in order: my six probes, `a0/a1/verify.py`, `a0/a1/kapso_t1/verify.py` and
`a0/a1/calibration/verify.py` (the artifacts' own re-runnable claims), and prints
`git status` at the end. The whole transcript is committed as `out_run_all.txt`.

`a0/a1/verify.py` and `a0/a1/calibration/verify.py` are read-only on the tree now: both
were run, and `git status --porcelain` was empty afterwards apart from this directory
(the previous verifier had measured `declarations/CID.json` being rewritten; it is not).

---

## 1. Verdict table

| # | claim | verdict | evidence |
|---|---|---|---|
| 1 | `EID*` recomputes to `7ce9e72f…` from `T1.contract.json`/`T1-EID.json`'s own recorded material | **ACCEPTED** | `out_v1_identity.txt` 14/14: five component digests recomputed from the recorded records, `EID*` = `7ce9e72f36a0d154…`, the document's own `payload_canonical` matches |
| 1 | the `EvaluatorSource` records are the bytes of `e_star.py`/`e_star_child.py` **on disk** | **ACCEPTED** | same: `f67ecd41…`/`fdcf425c…` match, sizes match, exactly two files selected; `e_star.py digest --value-only` = `dc6969ec…` reproduced by hand from E*'s own recipe |
| 1 | `python3 a0/a1/verify.py` is 6/6 / rc=0 | **ACCEPTED** | `out_v1_verify.txt`: `verdict: pass`, all six steps true; re-run green at `8057c1ce`; the tree stays clean |
| 1 | no committed artifact still asserts a superseded digest without labelling it as history | **REJECTED** | `out_v1b_superseded.txt`: 897 tracked files carry one; four groups are unlabelled — `a0/a1/kapso_t1/**` (which *enforces* the old identity), `a0/tasks/maxcut/gates/**`, `a0/A1-INTERIM.md`, `a0/tasks/maxcut/redesign/out/**`. §2 |
| 2a | a candidate spawned by the **service** cannot reach any host | **ACCEPTED** | `out_v2_closures.txt`: `api.deepseek.com:443`, `1.1.1.1:443`, `8.8.8.8:53` all unreachable, DNS `gaierror`, from a candidate E* spawned under the service; non-vacuous — the same candidate on the host reaches all three and resolves DNS |
| 2b | a candidate cannot read a stored reference partition — tree, git, logs, bundle | **ACCEPTED for the candidate lane** | measured: 0 partition files reachable, `git rev-parse`/`show`/`log`/`cat-file` all "not a git repository", `/tmp/mcwork/scip_test2/G_dev_0001.partition.json` (a real `224 = R = OPT`) `FileNotFoundError`. Residual in §3 |
| 2c | the provider key is unreachable from the candidate's environment and from `/proc` | **ACCEPTED** | candidate env is exactly `HOME, LANG, PATH, PYTHONDONTWRITEBYTECODE` with no key-shaped name; 1 visible PID; `/proc/1/environ` not readable; `/home/ebt/gptapi.md` `FileNotFoundError` |
| 2d | the honest path still books a real score | **ACCEPTED** | `c02_ok_low_baseline` through the service: `cut_edges 132`; my own honest fallback: `136` |
| 3 | `B_hard` is re-derivable from the published evidence by the frozen formula | **ACCEPTED** | `out_v4_bhard.txt` 43/43 + `out_v4_calverify.txt`: `CEq_max 1966519`, `N_E,max 725`, `P 1`, `T_wall 1800` recomputed from the raw ledgers' own `usage` and the recorded epoch span; `verify.py budget` reports the committed file **byte-identical** to a fresh `apply` |
| 3 | V1–V7 hold | **ACCEPTED** | same: V1 (procedure sha), V1b (json sha), runner sha, manifest sha, V3 (`verify_ledger.py` rc 0 per ledger; published bytes == `INDEX.json` raw sha), V4 (units 24/24, `T_r` 424.345/149.109 s), V5 (`deepseek-flash` 47/47, 48/48), V6 (every harness row names a manifest graph sha), V7 (campaign/arm ids) |
| 3 | the guardrails do not bind before `T_wall` | **ACCEPTED** | same: `CEq_max` lasts 37.50 min (`A_simpleloop`) / 92.22 min (`A_kapso`), `N_E,max` 73.25 / 37.54 min, all > 30 min; D1/D2 recompute; `guardrails_would_bind_before_T_wall: []` |
| 3 | the declared scope limits are real | **ACCEPTED** | same: `A_simpleloop` 33/47 rows at `max_tokens 2048`, `A_kapso` 48/48 at 256; unit 20 (pass 1, `C_0009`) exited 8 and is the only non-zero of 24; `A_kapso` 24 × 0 |
| 4a | a metric with a declared range rejects an out-of-range score; one without is not given an invented bound | **ACCEPTED** | `out_v5_tracebound.txt` 12/12, both directions, `validate` and `validate-run` |
| 4a | the regression claim: the pre-fix module accepts the fixture | **ACCEPTED** | same: `git show 10686854^:…trace_validate.py` + `trace_schema.json` in its own directory → `valid: 11 event(s)` for both streams; the new module rejects the same file in the identical layout |
| 4b | the suite README's corrected leakage claim is substantiated by the artifact it points to | **ACCEPTED** | `out_v6_labels.txt` 23/23 + `audit_labels.py verify` PASS; the label audit's ground truth re-derived independently (§5) |
| 5a | the executable bit no longer matters | **ACCEPTED** | `out_v7_staging.txt`: one candidate's bytes, modes 0755/0644/0600/0400 → one `candidate_source_sha256`, one `canonical_digest`, **byte-identical** 1411-byte Outcome files, `cut_edges 261` |
| 5b | the candidate-facing view omits the generator block, and the Outcome records both hashes | **ACCEPTED** | same: the handed document's keys are exactly `{schema, graph_id, family, n, edges}`, `edges` equal to the suite file's, while the suite file carries `generator`+`notes`; `graph_sha256` == sha256(suite file), `candidate_graph_sha256` == sha256(handed view), and they differ |
| + | the gate's frozen numbers survive the current `E*` | **ACCEPTED with a caveat** | `out_v8_consequences.txt`: `baseline` 132 and `pc` 212 recompute identically, but six fields move — `evaluator_source_sha256`, `canonical_digest` and the new `candidate_graph_*` keys. §2b |
| + | the harness-side score bound (F3) works in both modes | **ACCEPTED** | same: `bounded` → `refused_out_of_bound`, `status error`, nothing published, `true_value 132` kept; `labelled_implausible` → publishes 9999 with `within_bound: false` and the true value beside it |
| + | the sibling commit's 13/13 claim for the hostile probe | **ACCEPTED** | `out_v1c_hostile_probe.txt`: `verdict pass`, all 13 checks true, `raw_pre_fix` books 224 = `R = OPT` on `G_dev_0001` and `service_sandbox` books 0 |

Two of those rows are **not** acceptance of what a report says, and are called out in §2.

---

## 2. The falsification: superseded digests asserted as current

`v1b_superseded.py` scans every tracked file for the ten digests that were current and are
not any more (`cddfa64e`, `eccd859c`, `08281d21`, `4afff01f`, `670f02ee`, `fa0932b4`,
`83d55e80`, `013f3e33`, `c08f0c36`, `7392915d`) and prints each line. 897 files carry one.
Labelled as history and therefore fine: `a0/a1/DEVIATIONS.md` (D-A1-1/7/11/12/13 carry
both values and the reason), `a0/a1/WIRING-REPORT.md`, `a0/a1/calibration/history/**` (a
directory named for it), `a0/a1/calibration/README.md`, `a0/verify/a1-testbed/**` (the
earlier verifier's report) and `a0/a1/DEVIATIONS.md` §"what is pre-fix and what is not".

### 2a. `a0/a1/kapso_t1/**` asserts **and enforces** the superseded evaluator — REJECTED

This is a fifth defect. The earlier pass did not look here, and the four fixes did not
close it. The KAPSO arm's registered evaluation tree pins the **pre-`6dd717c2`** evaluator:

```console
$ python3 -c "import json;d=json.load(open('a0/a1/kapso_t1/tree/a0_locator.json'));print(d['eid_star']);print(d['e_star']['self_identity']['evaluator_source_sha256']);print([f['sha256'] for f in d['e_star']['source_records']])"
cddfa64ead571bbb09daa458c6b514377fba32e62612f5c2e17a6b49b7a78ab1
08281d21e6e84a79dfebd895d7653b517c1e08e7ea8784fe485532dd5db59c4d
['670f02ee91885c10c9c6df95971a15d5ae0f81ad8bbb723d20e8f7fa0bdebbb0', '013f3e334dbde616c3cb6beb5debf125d5e9ad57d56ae1fa145da5ae4ca76473']
```

On disk now: `EID* = 7ce9e72f…`, `e_star.py f67ecd41… (53 788 B)`,
`e_star_child.py fdcf425c… (35 924 B)`. The tree is not merely stale documentation — it is
enforced, and it is pinned by the declaration:

* `t1_binding.py:260` hard-asserts `eid.eid_star == "cddfa64e…"`;
* `tree/kapso_eval.py` re-hashes both `E*` files on every invocation and aborts with exit 3
  on drift (measured in the test failure below);
* `a0/a1/declarations/causal_audit.json` and `AID_r.A_kapso.json` pin the tree by digest
  (`a0_locator.json 5a0c99ff…`, `eid_r manifest:6b1d6fcc…`) — so `CID` names
  `EID* = 7ce9e72f…` while `AID_r` names a tree built from `cddfa64e…`.

Its own one command is red, 0/5:

```console
$ python3 a0/a1/kapso_t1/verify.py ; echo rc=$?
{"verdict": "fail", "steps": {"tree": false, "binding": false, "dryrun": false, "rehearse": false, "tests": false}, ...}
rc=5
--- tree failed (exit 5) ---  "locator_rebuild_matches_committed": false, "eid_star": "7ce9e72f…"
--- binding failed (exit 5) --- (EID* 7ce9e72f, pass false)
--- tests failed --- AssertionError: assert '7ce9e72f36a0…' == 'cddfa64ead57…'
  E* source drifted: e_star.py sha256 6312cb7b… != 670f02ee… recorded in EID* (cddfa64e…)
```

Two readings, and I do not choose between them for the coordinator:

1. **Defect.** `a0/a1`'s final revision advertises a KAPSO T1 arm whose registered tree
   cannot run against the frozen `E*`, and whose own verifier is red — while
   `a0/a1/README.md` and `WIRING-REPORT.md` present the directory as frozen and green.
   The arm's identity preflight would abort in a campaign.
2. **Scoping decision, not a defect.** `kapso_t1/` is a named workstream's own deliverable
   (D-A1-2) committed at 17:37, before the 20:51/21:14 re-freezes, and D-A1-12's "this
   freeze is a snapshot" caveat is about exactly this class of event. Re-freezing it means
   rebuilding the tree, the binding and the EID_r, and re-recording its evidence — a
   decision and a paid-or-not question that is not mine to make.

Either way the *artifact* is not labelled as history, so item 1's third sub-claim is not
met. The one-line reproduction is above.

### 2b. The gate's artifacts and prose — PARTIALLY ACCEPTED

All 924 gate Outcomes (and the 12 verdicts and the `values/`) carry
`evaluator_source_sha256 4afff01f…`, which `baf13884` superseded with `dc6969ec…`;
`gates/README.md:247` states it in the present tense ("the harness-owned `E*`,
`evaluator_source_sha256 4afff01f…` — with the frozen `θ`"), and `gates/DEVIATIONS.md`
D-GATE-10/11 label only the move *into* `4afff01f…`, never out of it.

I measured what that costs. Re-running the same `(candidate, graph, θ)` with the current
`E*`:

```
baseline  fresh 132 vs frozen 132   pc  fresh 212 vs frozen 212   (|E| = 265, G_dev_0001)
fields differing from the frozen Outcome:
  ['candidate_graph_bytes','candidate_graph_keys','candidate_graph_schema',
   'candidate_graph_sha256','canonical_digest','evaluator_source_sha256']
```

So the **decision fields do not move** and the `NOT_ADMISSIBLE` verdict is not in question,
but the gate's own re-freeze discipline (D-GATE-10: "the frozen artifacts are no longer the
artifacts that produced the earlier digests") is unmet: this is a third re-freeze that has
not been done, and the README's §4 asserts a superseded evaluator as the current one.
I did not re-run the gate and did not touch a threshold.

### 2c. Two smaller ones

* `a0/A1-INTERIM.md:18` — the interim report the coordinator reads quotes
  `EID* = cddfa64e…` as the T1 evidence row, unlabelled and now two re-freezes old.
* `a0/tasks/maxcut/redesign/out/l2_outcomes/**` — 276 Outcome files carry `08281d21…`;
  `redesign/DEVIATIONS.md` never mentions the digest. `a0/a1/causal.py:175` carries
  `670f02ee…` in an illustrative docstring example (harmless).

---

## 3. The closures — what is closed, and what is only masked

`v2_closures.py` runs **my own** hostile candidate (not the suite's, not the authors')
through `a0/a1/eval_service.py` in four lanes: the default `sandbox`, the labelled control
`--candidate-isolation none`, a bare host control, and an honest C\*(T1) candidate. The
candidate reports only *readability*, sizes, and (for a partition-shaped file) the cut it
would score — never a byte of an answer, never a value from `/proc/*/environ`.

| attempt | service (sandbox) | `none` | host control |
|---|---|---|---|
| `api.deepseek.com:443`, `1.1.1.1:443`, `8.8.8.8:53`, DNS | unreachable | unreachable | **reached / resolved** |
| `references/logs/partitions/G_dev_0001__*` | 0 matches | 0 matches | 0 matches (the tree store is empty) |
| `/tmp/mcwork/scip_test2/G_dev_0001.partition.json` | `FileNotFoundError` | `FileNotFoundError` | **readable, `cut_if_copied 224 = R = OPT`** |
| `references/targets.json`, `suite/manifest.json`, `generators/provenance.json` | `FileNotFoundError` | `FileNotFoundError` | **readable (762 KB / 93 KB / 26 KB)** |
| `git rev-parse` / `show HEAD:…` / `log --all` / `cat-file` | "not a git repository" | "not a git repository" | **rc=0, all objects listable** |
| `/home/ebt/gptapi.md` | `FileNotFoundError` | **readable, 591 B** | **readable, 591 B** |
| visible PIDs / `/proc/1/environ` | 1 / not readable | 1 / not readable | **443 / readable** |
| another candidate's partition under the state root | none | none | **the sibling lanes' `partition.json`** |

Four things this establishes, and one it does not:

1. **2a holds and is not vacuous.** The host control reaches the provider and resolves DNS
   with the same script and the same targets; inside the service lane nothing does.
2. **2b holds for the candidate lane.** The answer stores are not merely deleted: a real
   answer (`/tmp/mcwork/scip_test2/G_dev_0001.partition.json`, which `fs_policy.json` names
   and which scores `224 = R = OPT`) is unreadable from the lane, and `git` is not there.
   **Residual, stated rather than hidden:** the answers *do* still exist — 606 `G_eval_*`
   witness blobs are reachable as git objects, and
   `git cat-file blob 9020082d…` returns `G_eval_0001`'s optimal partition (cut `217 = R =
   OPT`). `suite/README.md` §5.2 and `references/witnesses/commitments.json.recoverable_from`
   say so; `E*` masks `.git` and this directory. The claim is "not reachable by a
   candidate", not "not recoverable by anyone with the repository".
3. **2c holds, and it is the *service sandbox* that closes the credential path, not `E*`.**
   In the `none` lane `/home/ebt/gptapi.md` is readable (591 B) although `HOME` points at the
   scratch — only the hidden `/home` root stops it. The lane is labelled unsafe
   (`harness_identity.json`: `labelled_unsafe: true`), so this is by design; it does mean
   `--candidate-isolation none` is a lane in which a candidate can read the key.
   A footnote, not a defect: that identity also asserts
   `candidate_can_reach_the_network: true`, and I measured the network **closed** in that
   lane too (the frozen `maxcut` argv passes `--net-isolate` regardless of the lane), so the
   label over-states the exposure.
4. **2d holds.** `c02_ok_low_baseline → 132`; my own `index % 2` candidate → `136`, both
   `status ok`.
5. Not established by me: the sandbox receipt's own self-check is the only in-lane evidence
   for `mount` masking; I read the receipt (`pass: true`, `hidden_roots` all tmpfs,
   `egress BLOCKED:gaierror`, `visible_pid_count 1`) rather than auditing the mount code.

---

## 4. Two consequences I did not take on trust

* **The gate's numbers survive the evaluator change** (§2b) — they do, and the identity
  fields move.
* **The harness-side score bound** (F3's closure, `--override-mode`): with
  `--override {"cand_bound": 9999}` on a graph with `|E| = 265`, `bounded` refuses
  (`verdict refused_out_of_bound`, `status error`, `value`/`handed_value` null,
  `outcome.cut_edges` null, `true_value 132` preserved), and `labelled_implausible`
  publishes `9999` with `within_bound: false`, `bound.upper 265`, and `true_value 132`
  beside it. Both directions checked; both are what the module's docstring claims.

---

## 5. The label audit, re-derived and then attacked

I did not take the audit's ground truth from the audit. `v6_labels.py` replays each of the
15 Planted graphs' own `generator` block through the frozen generator, checks the replay
reproduces the frozen edge list (15/15), and only then uses the labels it produces:
`provenance.json`'s recorded vectors equal the replayed ones for 15/15. It then builds
**8** spellings per graph (the audit's 6 plus the two complements — the complement is the
same partition, so it is the same leak) and searches three surfaces.

* A — every file under `suite/**`, **any extension** (the audit scans `*.json`): 62 files,
  **0 hits**.
* B — the candidate-facing document for all 60 graphs: **0 hits**, and the key set is
  exactly `{schema, graph_id, family, n, edges}`.
* C — a broad surface of 20 417 files (`a0/tasks/maxcut/**` + `a0/a1/**`): the **only**
  carrier is `generators/provenance.json` — the label store itself, by design, and the file
  the candidate lane masks (measured: unreadable in the service lane, 26 525 bytes in the
  host lane).

Two attempted leaks it does not cover, and what they showed:

* **The method's blind spot, demonstrated.** The audit's needles are JSON *substrings*, so
  they match only a file that spells the vector exactly as `json.dumps` does on one line —
  and `provenance.json` itself is pretty-printed with a wrapped array, which is why the
  literal scan reports **0 carriers** where the whitespace-normalised scan reports the store
  (my control: a reformatted copy of the labels is invisible to the literal scan and found
  by the normalised one). The check is safe for the shipped files because they are canonical
  single-line JSON, but the audit's "0 hits" is weaker than "no leak": a leak that reformats
  is invisible to it. The audit's *other* half — the view assertion — is not
  whitespace-sensitive and is the one that carries the claim.
* **The store the audit does not scan.** `generators/provenance.json` is a carrier by
  design, and it is the *hand-over* route (the evaluator's mask), not the audit, that keeps
  it away from a candidate. I measured that route closed in the service lane (§3).

Also re-run as the README quotes them: `audit_labels.py verify` → PASS (15 graphs, 61 JSON
files, 15 × 6 spellings, 0 hits, 60 views checked); `grep -rn --include='*.json' -E
'"labels"|planted_labels|…' suite/` → no match (rc 1); the `community_sizes` counts match.

One half of §5.2 is **not reproducible from the repository alone**:
`seal_witnesses.py verify --corpus <retained corpus>` needs a corpus that is not committed.
The README writes `<retained corpus>` rather than a path. I found a retained copy on this
machine (`/tmp/vfix/corpus`, 1968 partition files) and it verifies green —
"1968 witnesses recomputed, PASS: every recorded maximum equals targets.json's R" — but a
third party without it can only run the values-only half.

---

## 6. Item 3 in detail (why it is "ACCEPTED" and not "their verify.py said so")

`v4_bhard.py` imports nothing from `pilot.py`; the formula and V1–V7 are re-implemented from
the frozen strings in `B_hard.json`. 43/43 checks, including:

* **the rates are recomputed from the raw artifacts, not from `B_hard.json`'s own telemetry
  block**: `Σ ceq` over each committed `meter_ledger.jsonl` using each row's own `usage`
  equals `CEq_r` (370 881 / 52 992), the row count equals `N_E_r` (70 / 48), and `T_r`
  equals the recorded epoch span (424.345 010 s / 149.108 791 s);
* `q_r = 52440.489403` and `21323.491249` CEq/min, `e_r = 9.897607` / `19.314757` evals/min —
  the numbers the assignment's brief quotes;
* `ceil(1.25 × 30 × max_r q_r) = 1966519`, `ceil(1.25 × 30 × max_r e_r) = 725`, unclamped
  (`< 5 000 000`);
* **the guardrails really do not bind before `T_wall`**: at each arm's own rate,
  `CEq_max` lasts 37.50 / 92.22 min and `N_E,max` 73.25 / 37.54 min against a 30-minute
  wall — the binding margin (37.50 min) is positive, which is what
  `guardrails_would_bind_before_T_wall: []` asserts;
* **no model row is unmetered** (0 of 47 and 0 of 48), every row re-derives from its own
  `usage`, every `model_reported` is `deepseek-flash`, every `campaign_id`/`arm_id` matches;
* the **scope limits are real**: 33/47 `A_simpleloop` calls sit exactly on `max_tokens
  2048` (48/48 for `A_kapso` at 256), and the exit-8 unit is real, unique, and is unit 20
  (pass 1, `C_0009`) — the README's claim, checked in the artifact rather than quoted.

The one part I take from the author's runner: **byte-identity** of `B_hard.json`. `verify.py
budget` re-runs `pilot.py apply --out-dir evidence --b-hard <tmp>` and compares bytes; it
reports byte-identical (`out_v4_calverify.txt`). I re-derived the vector independently; I did
not re-implement the document's serialisation.

---

## 7. What I could not verify

* **The MQLib ensemble behind `R`.** By instruction and by scope I verified only what is
  stored (`targets.json`, the commitments, one git-recovered partition). I did not rebuild
  the ensemble.
* **The paid live probes** (`a0/a1/evidence/live_*.json`, `a0/a1/kapso_t1/evidence/live_t1.json`)
  and the **pilot itself**: re-running them spends money. I verified the ledger arithmetic,
  the artifact digests and the byte-identity of the published ledgers, not the sessions.
* **A campaign end-to-end.** The task is `NOT_ADMISSIBLE`; there is no campaign. The
  task-level verdict is untouched by anything in this report, and I did not run the gate.
* **KAPSO's internals** (an upstream runtime, read-only by rule). I reproduced the
  consequence of the stale registered tree (`exit 3 E* source drift`), not the code path.
* **`kapso_eval.py`'s stub under a rebuilt tree.** I did not rebuild `a0/a1/kapso_t1/tree`
  (that is a write into another workstream's directory and a scoping decision, §2a).
* **The sandbox's mount code.** I read its receipt and measured its effect; I did not audit
  `_hide`/`_restore`.
* **The retained witness corpus from the repository.** It is not committed (§5); I used the
  copy found at `/tmp/vfix/corpus` and said so.

## 8. Deviations from this brief

* I ran three other workstreams' own entry points — `a0/a1/verify.py`,
  `a0/a1/kapso_t1/verify.py`, `a0/a1/calibration/verify.py` — and
  `a0/a1/probes/hostile_candidate.py` (§1). All four are read-only on the tree; measured:
  `git status --porcelain` empty apart from `a0/verify/a1-final/` after the whole run.
  Running `kapso_t1/verify.py` executes its *free* rehearsal (the model call is skipped by
  its own flag), not the paid arm.
* I ran `seal_witnesses.py verify --corpus /tmp/vfix/corpus` — a read-only check against a
  corpus outside the repository (§5).
* My hostile candidate writes a `partition.json` and prints a JSON finding line; it never
  writes, copies or prints the contents of anything it finds, and it records `/proc`
  variable **names** only. The provider key is never read into this report or into any
  committed file.
* The broad leakage surface in `v6_labels.py` is `a0/tasks/maxcut` + `a0/a1` (20 417 files)
  rather than the whole repository. A hit does not depend on the scope; a miss does.
* `v1b_superseded.py` excludes this directory and the earlier verifier's report — both are
  themselves reports quoting digests as history.
* I did not touch `/home/ebt/kapso_ck/`, `/tmp/eve/`, the `adapdc-catalog-postgres-1`
  container, or any upstream runtime; and I committed only `a0/verify/a1-final/**`.
