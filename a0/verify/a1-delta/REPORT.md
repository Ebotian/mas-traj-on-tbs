# Adversarial re-verification of the A1 fixes — the delta pass

Owner: `a0/verify/a1-delta/**`. **Nothing was fixed.** Every finding is reported with a
minimal reproduction; the only writes outside this directory are two artifacts that two
of the entry points rewrite, both restored with `git checkout --` and both reported in §5.

This pass re-derives the **fixes** the previous pass could not see — they landed after
`a0/verify/a1-final/REPORT.md` was written — rather than repeating that report:

| fix (all committed) | commit | what I re-derived |
|---|---|---|
| `a0/a1/kapso_t1/**` identity drift (the previous pass's REJECTED item) | `f8f8b386`, `08bc5beb` | §1 |
| the task gate's identity stamps (576 Outcomes, 14 `values/`, 12 verdicts) | `afc145a0`, `5091e501` | §3 |
| the candidate sandbox's `/tmp` hiding | `7a1c0c16` | §4 |
| A1 documents refreshed | — | §2, §5 (partially rejected) |

Revision verified: `08bc5bebc3fba8ab12e982ec0b3478801a127a70`. **Zero model spend**: no
paid probe was re-run, no campaign was run, no CEq was spent; the paid artifacts
(`a0/a1/kapso_t1/evidence/live_t1.json`, `a0/a1/evidence/live_*.json`, the calibration
pilot) are verified by recomputing their arithmetic from their own recorded `usage`.

```console
$ sh a0/verify/a1-delta/run_all.sh          # everything below, ~8 minutes, model-free
$ git status --porcelain                    # only "?? a0/verify/a1-delta/"
```

---

## 1. Verdict table

| # | claim under test | verdict | evidence (my command, my output) |
|---|---|---|---|
| 1a | `EID*` recomputes to `7ce9e72f…` from `a0/a1/t1_eid.py`'s own material | **ACCEPTED** | `d1_kapso_identity.py` 26/26: five component digests recomputed from the recorded records with a re-implemented canonical-JSON/domain-digest recipe, `EID* = 7ce9e72f36a0d154…`, `payload_canonical` matches |
| 1b | the registered tree's `EID_r` and per-file digests match the **committed tree bytes** | **ACCEPTED** | same: `sha256` of `tree/kapso_eval.py` (`6759ef05…`) and `tree/a0_locator.json` (`1e3b3a75…`) → `json.dumps(sort_keys, separators)` → `63a9a83c071d82f3…`; `binding.json`, `tree_record.json`, `AID_r`'s two factors all equal it |
| 1c | `python3 a0/a1/kapso_t1/verify.py` is green | **ACCEPTED** | `out_d1_kapso_t1_verify.txt` / `out_d5_kapso_t1_verify.txt`: `{"verdict": "pass", tree/binding/dryrun/rehearse/tests all true}`, rc=0, tree left clean |
| 1d | the live probe's `CEq` recomputes from its own `usage` | **ACCEPTED** | `d1`: `92 + ⌊0·2/100⌋ + 4·256 = 1116` from both the meter ledger row and `arm_state.model_calls[0].usage`; `meter_summary.ceq == 1116`; 16/16 checks |
| 1e | nothing in `kapso_t1` asserts a superseded digest unlabelled | **ACCEPTED** | `d1`: every hit is in `evidence/history/superseded-eid-cddfa64e/` (a directory named for it, with an `INDEX.json` naming both value sets) or on a before/after line (`DEVIATIONS.md` D-KT1-8's table, `README.md`:18 "the previous revision's …") |
| 2a | `registered_tree()`'s two factors recompute to what `AID_r.A_kapso.json` and `CID.json` contain, and the two agree | **ACCEPTED** | `d2_declaration.py`: file map, fingerprint, `eid_r`; `AID_r`'s identity and files factors equal them; `CID.task.eid_star` equals the reconputed `EID*`; **the tree's own locator also pins that EID*** — a cross-check the audit does not make |
| 2b | `declaration.py build` reproduces the committed declarations and the causal audit passes | **ACCEPTED** | `d2`: rebuilt into a scratch dir, all four documents byte-identical to the committed ones; `causal_audit.json` `verdict pass`, `problems []` |
| 2c | the *causal audit* would catch a recurrence of the `CID`-vs-`AID_r` disagreement | **REJECTED** | `d2`: with the pre-rebuild tree (`7bf8a14b`) and a binding re-stamped to match it, `AID_r` names `manifest:6b1d6fcc…` while `CID` names `EID* 7ce9e72f…`, and the audit still says **pass**. `kapso_t1/build_tree.py check` does catch it (locator bytes do not rebuild). §2 |
| 3a | every leaf that moved in the re-stamp is an identity leaf, and no decision leaf moved | **ACCEPTED** | `d3_gate_restamp.py` 16/16 over all 576 Outcomes + 14 `values/` + 12 verdicts vs `7bf8a14b`: leaves moved are exactly the six identity fields (576×6 Outcomes, 336×6 `values/` leaves, 12×1 verdicts), 0 non-identity leaves |
| 3b | no threshold was softened | **ACCEPTED** | `d3`: `gate_config.json` byte-identical to `7bf8a14b`; Δ ≥ 3/100 overall, ≥ 2/100 in ≥3/4 families; ρ median ≥ 3/10 globally and per family in ≥3/4; saturation veto at headroom median ≥ 1/20 and `T_i == b_i`. Every verdict keeps its decision fields; dev and eval stay `NOT_ADMISSIBLE`, failing on ρ |
| 3c | the gate's own re-stamp check reports CLEAN | **ACCEPTED with a caveat** | `restamp_evidence.py --before 7bf8a14b` → CLEAN, 924/924 stamps current, 0 decision leaves, and byte-identical to the committed `restamp.evidence.json`. Its **documented** invocation (`--before HEAD`, the default) reports 0/576 and 0/12 — vacuous after the re-stamp — and rewrites the committed evidence. §3 |
| 4a | the lane's `/tmp` (and `/var/tmp`, `/home`, `/run/user`) is its own | **ACCEPTED** | `d4_canary.py` 11/11 with **my own** canaries: unreadable in all four roots, while the allowed control under `/tmp` and `/var/tmp` *is* readable; `/tmp` shows 332 host entries → 0 in the lane |
| 4b | the fix changed behaviour (it is not a description of what was already true) | **ACCEPTED** | `d4`: the pre-fix module (`7a1c0c16^`) run on the same canaries returns `/tmp` canary **readable, 333 entries**, while its receipt still lists `/tmp` as hidden |
| 4c | the fail-closed branch refuses to measure with no mount topology | **ACCEPTED** | `d4`: `prefix(hidden_roots=("/proc",))` → exit 3, receipt `pass: false`, `error: cannot read this namespace's own mount table … the lane's topology is unknown, so the harness must not measure` |
| 5a | the five entry points are green at this revision | **ACCEPTED** | §5a: `a0/a1/verify.py` pass (6/6), `kapso_t1/verify.py` pass (5/5), `restamp_evidence.py` CLEAN, `conformance.py --check` PASS, `calibration/verify.py --with-rehearsal` pass (0 CEq) |
| 5b | no committed artifact asserts a superseded digest as current | **REJECTED** | `d6_superseded.py`: 37208 files scanned, 299 carry a superseded digest (518 lines), **286 files have an unlabelled line** — 276 under `a0/tasks/maxcut/redesign/out/**` (the previous pass's §2c, untouched) and 10 others, **4 of them newly stale because the KAPSO re-freeze moved `EID_r`**. §5b |
| + | the hostile probe's 13/13 still reproduces and its evidence is self-consistent | **ACCEPTED with a caveat** | re-run into `/tmp` reproduces 13/13 with identical `checks`; but the committed evidence cites `differs_from.revision_full = 654d5da2…`, a commit **not reachable from any ref** (it is the pre-amend version of `7a1c0c16`). §5 |

Two rows are rejections: 2c and 5b. Neither is a regression the fixes introduced; both are
things the fixes did not reach.

---

## 2. `CID` and `AID_r` agree today — but nothing makes them agree

The defect the previous pass found was that `CID` named `EID* 7ce9e72f…` while `AID_r`
named a tree built from `cddfa64e…`. The rebuild fixed the *state*. It did not add the
*check*:

* `declaration.registered_tree()` hashes the tree's two files and fingerprints them. It
  never reads `tree/a0_locator.json`, so it cannot see that the locator pins an `EID*`.
* `registered_tree_checks()` compares the tree against `binding.json` — tree ↔ binding,
  never tree ↔ `CID`. A binding re-derived from a stale tree agrees with it.
* `audit()`'s two failure modes are "an object named nowhere" and "a `CID` factor whose
  observed hash differs across arms". A tree whose *contents* disagree with `CID` is
  neither.

**Falsification.** I offered the audit the pre-rebuild tree from git plus a binding
re-stamped to those bytes (so tree and binding agree, exactly as they do now):

```console
$ python3 a0/verify/a1-delta/d2_declaration.py
   stale tree locator pins EID* cddfa64ead571bbb…
   AID_r names EID_r manifest:6b1d6fccf78d1b94f0bb2fa3e…
   CID   names EID* 7ce9e72f36a0d154…
[FAIL] the declaration audit CATCHES a tree built from a superseded EID*  — verdict=pass problems=[]
[ok ] ...and the two declarations really do disagree in that state
```

**What would have to move** for the defect to recur: `tree/a0_locator.json` (its
`eid_star` / `e_star.source_records` / `eid_star_components`) and `binding.json` kept
consistent with it — i.e. someone rebuilding the registered tree from a stale
`T1-EID.json`, or hand-editing the locator, and re-deriving the binding. That is a
plausible operation for exactly the reason the previous pass hit it: `T1-EID.json` is
another workstream's file and it has moved twice.

**What catches it today** (both measured in `d2`, and neither is the declaration audit):

1. `a0/a1/kapso_t1/build_tree.py check` rebuilds the locator from `T1-EID.json` + C\*(T1)
   and compares **bytes** with the committed tree → `{"locator_rebuild_matches_committed":
   false, "pass": false}`, rc 5. This is a step of `kapso_t1/verify.py`, so the
   workstream's own one-command check is the real guard.
2. The registered stub `tree/kapso_eval.py` re-hashes `e_star.py`/`e_star_child.py` on
   every invocation → exit 3, no `KAPSO_EVAL_MANIFEST` line — the consequence of the
   staleness (and only when the tree actually runs).

So: the declaration's `registered_tree_checks()` is necessary and not sufficient, and the
audit's `pass` says nothing about `CID`-vs-tree content agreement. A one-line addition to
`registered_tree_checks()` (read the locator, compare its `eid_star` to `cid`'s
`task.eid_star`) would close it; that is a change to another workstream's file and not
mine to make.

---

## 3. The gate re-stamp: identity, not decision

`d3_gate_restamp.py` walks all 602 stored documents (`576` Outcomes, `14` `values/`,
`12` verdicts) against `7bf8a14b` with my own leaf walker, so the diff does not come from
the artifact it is testing. Result 16/16:

```
outcomes: 576/576 differ; leaves moved {candidate_graph_bytes, candidate_graph_keys,
          candidate_graph_schema, candidate_graph_sha256, canonical_digest,
          evaluator_source_sha256} × 576; non-identity leaves 0
values:   14/14 differ;  six identity leaves × 336;                     non-identity 0
verdicts: 12/12 differ;  {evaluator_source_sha256: 12};                 non-identity 0
```

Thresholds: `gate_config.json` is byte-identical to `7bf8a14b`'s and carries the
pre-registered numbers (Δ `3/100` overall, `2/100` per family, 3 of 4; ρ `3/10` globally
and per family, 3 of 4; the saturation veto at `1/20` plus the `T_i == b_i` clause). Every
verdict keeps its top-level decision fields; dev stays `NOT_ADMISSIBLE` on the ρ gate
(global median `479/3016 = 0.1588` < `0.30`, 0/4 families), Δ passes, saturation does not
fire. The five `pc_exchange_k*` variants keep their own verdicts (`k02/k05/k10`
ADMISSIBLE on dev) — unchanged, and **not mine to touch**; I record them because the
pending contract revision turns on them and I did not pre-empt it.

`restamp_evidence.py` itself:

```console
$ python3 a0/tasks/maxcut/gates/restamp_evidence.py --before 7bf8a14b --out <my dir>
E* now: dc6969ec9934ab66…
stamped records: 924 in 602 documents, 924 current, 0 stale
history 08281d21… 5 mention(s), 5 labelled · history 4afff01f… 9 mention(s), 9 labelled
outcomes: 576/576 differ; decision leaves 0 · verdicts: 12/12 differ; decision leaves 0
re-stamp verdict: CLEAN
```

and its output is **byte-identical** to the committed `restamp.evidence.json`.

**The caveat.** The tool's own docstring and its default say `--before HEAD`. After
`afc145a0` re-stamped the records *at* `HEAD`, that invocation compares the re-stamped
records with themselves:

```console
$ python3 a0/tasks/maxcut/gates/restamp_evidence.py          # documented invocation
outcomes: 0/576 differ; leaves moved {}; decision leaves 0
verdicts: 0/12 differ;  leaves moved {}; decision leaves 0
re-stamp verdict: CLEAN
wrote /home/ebt/rsi-dev/a0/tasks/maxcut/gates/restamp.evidence.json
```

So: (a) the documented command proves nothing about whether the re-stamp moved a number —
only `--before 7bf8a14b` does, and the committed evidence records that revision, so the
proof exists; (b) the documented command **rewrites a committed artifact** (it makes
`before_revision: HEAD` and empties the diffs). I restored it:
`git checkout -- a0/tasks/maxcut/gates/restamp.evidence.json`, verified byte-identical to
the pre-run copy. A reader following the docstring would commit a weaker evidence file
without noticing.

---

## 4. The candidate lane's `/tmp`, measured with my own canaries

`d4_canary.py` writes `A1DELTA-CANARY-0f3a91` into `/tmp`, `/var/tmp`, `/home/<user>` and
`/run/user/<uid>`, plus a **positive control** under `/tmp` and `/var/tmp` that *is* passed
through the allow-list, then runs a trivial reader inside the lane via
`candidate_sandbox.prefix`.

| root | host | lane, committed module | lane, pre-fix module (`7a1c0c16^`) |
|---|---|---|---|
| `/tmp` | readable, 332 entries | **not readable**, 1 entry (the allowed control), `tmpfs` | **readable**, 333 entries |
| `/var/tmp` | readable, 8 entries | not readable, 1 entry (the allowed control), `tmpfs` | not readable, 1 entry |
| `/home` | readable | not readable, 0 entries, `tmpfs` | not readable |
| `/run/user` | readable | not readable, 0 entries, `tmpfs` | not readable |
| positive control under `/tmp`, `/var/tmp` | — | **readable and byte-equal** | — |

The receipt records the measurement per root: `/tmp` `host_mounted=True before=tmpfs(id
469) → after=tmpfs(id 479), dev 35→86, entries 332→0`; `/home` `dev 66307→85`,
`/var/tmp` `66307→88`, `/run/user` `28→89`. So the root the old `_hide` skipped is exactly
the root replaced now, and the "already a tmpfs" reading is gone.

Fail-closed, through the module's own entry point: with `/proc` as a hidden root the fresh
tmpfs replaces the namespace's mount table, and the next read of it fails —

```console
$ python3 -c "... prefix(['/bin/true'], hidden_roots=('/proc',)) ..."
exit 3: candidate_sandbox: refusing to run: cannot read this namespace's own mount table
        ([Errno 2] No such file or directory: '/proc/self/mountinfo'); the lane's topology
        is unknown, so the harness must not measure
receipt: pass=false, same error
```

Non-vacuity is carried by three controls: the host reads every canary; the allowed control
is readable *inside* the lane; and the pre-fix module reads the same canaries, so a
"not readable" cannot come from a broken probe.

**Not established by me:** the mount code beyond `_hide`/`_self_check` (e.g. the
`_restore` ordering), and whether a candidate can defeat the boundary by other means
(kernel exploits, resource exhaustion — named as a residual in the module docstring).

---

## 5. One-revision agreement, and what still asserts a superseded digest

### 5a. The five entry points

```console
$ sh a0/verify/a1-delta/d5_entrypoints.sh
```

| entry point | verdict | note |
|---|---|---|
| `python3 a0/a1/verify.py` | `pass` 6/6, rc 0 | tree stays clean |
| `python3 a0/a1/kapso_t1/verify.py` | `pass` 5/5, rc 0 | tree, binding, dry run 26/26, rehearsal, tests |
| `python3 a0/tasks/maxcut/gates/restamp_evidence.py --before 7bf8a14b` | `CLEAN`, rc 0 | see §3 for the default-invocation caveat |
| `python3 a0/tasks/maxcut/conformance.py --check` | `PASS`, rc 0 | **rewrites** `conformance.report.json`; restored (§5c) |
| `python3 a0/a1/calibration/verify.py --with-rehearsal` | `verdict: pass`, rc 0 | 8 evaluations, 0 CEq; `B_hard` byte-identical |

### 5b. The superseded-digest scan

`d6_superseded.py` — my own list of thirteen once-current digests (including the two the
KAPSO rebuild moved, `5a0c99ff`/`6b1d6fcc`, and the sandbox module's `fd234f69`), over
every tracked file, with *structural* labelling for JSON (a digest inside a `before_side`
block is labelled even when the marker is hundreds of lines away) and *line-scoped*
labelling for prose (a window is too loose — it labels a present-tense claim because an
unrelated row nearby names the current value).

```
scanned 37208 tracked files; 299 carry a superseded digest (518 lines);
286 files have an unlabelled line: 276 under a0/tasks/maxcut/redesign/out/**, 10 others
```

**Labelled and fine:** `a0/a1/kapso_t1/evidence/history/**` (45+18 lines, a directory
named for it), `kapso_t1/DEVIATIONS.md` (D-KT1-8's before/after table),
`kapso_t1/README.md`, `gates/DEVIATIONS.md`, `gates/README.md`, `gates/refreeze.evidence.json`,
`gates/restamp.evidence.json`, `gates/restamp_evidence.py`, `calibration/history/**`,
`a0/a1/causal.py:175` (an illustrative docstring), and `a0/a1/DEVIATIONS.md`'s
D-A1-11/12/13 prose (which carries both values).

**Unlabelled and presented as current — new, caused by the KAPSO re-freeze.** `63a9a83c`
(the rebuilt tree's `EID_r`) appears **nowhere** in `a0/a1`'s prose or in
`a0/A1-INTERIM.md`. The four documents below still name `manifest:6b1d6fcc…` as the
registered tree:

| file:line | text | why it is not history |
|---|---|---|
| `a0/a1/WIRING-REPORT.md:46` | verdict **5b CONFIRMED**: `runtime.registered_evaluation_tree` = `manifest:6b1d6fcc…` | a verdict row in the present tense; the artifact says `63a9a83c…`. The row is a *claim about the committed declaration* and it is false |
| `a0/a1/WIRING-REPORT.md:200`, `:222` | the "AID_r for the KAPSO arm" table: `eid_r: manifest:6b1d6fcc…`, `a0_locator.json: 5a0c99ff…` | the committed `AID_r` carries `63a9a83c…` / `1e3b3a75…` |
| `a0/a1/DEVIATIONS.md:55`, `:68`, `:241`, `:260` | `a0/a1/kapso_t1/` "delivers … the tree with `EID_r = manifest:6b1d6fcc…`", and the evidence-mapping table | present tense in D-A1-2 and D-A1-6 |
| `a0/a1/evidence/README.md:83` | "the tree whose `EID_r` = `manifest:6b1d6fcc…` **that `AID_r.A_kapso.json` now pins**" | directly contradicts the committed declaration |
| `a0/a1/calibration/pilot_procedure.json:69` | `"tree": "a0/a1/kapso_t1/tree (EID_r = manifest:6b1d6fcc…)"` | a frozen pre-registration naming a superseded identity; not edited since |

and, unchanged from the previous pass's §2c:

* **`a0/A1-INTERIM.md:18`** — the coordinator's status table still reads
  `` `EID* = cddfa64e…` ``. No commit since `bfbe74c2` has touched the file.
* **`a0/tasks/maxcut/redesign/out/**`** — 276 tracked Outcome files carry
  `evaluator_source_sha256 = 08281d21…` (superseded twice), and `redesign/DEVIATIONS.md`
  and `redesign/README.md` never mention the digest.

Two further unlabelled hits I judge **labelled by context**, and say so rather than claim
a clean scan:

* `a0/a1/calibration/evidence/{simpleloop,kapso}/pilot_arm.json:132` — `module_sha256:
  fd234f69…` (the pre-fix sandbox module). Nothing inside the file labels it; the label is
  `a0/a1/DEVIATIONS.md` D-A1-14 §1, which names the file, the digest and the reason ("the
  recorded digest is now history"). It is the weakest label in the set: a reader of the
  file alone sees a present-tense module hash.
* `a0/a1/evidence/hostile_candidate.json` — 23 hits, all inside the pre-fix comparison:
  `before_side`, `evaluator_used_for_the_comparison` (which names revision `75403e8c` and
  prints both file digests and `differs_from` the current ones), and the
  `service_sandbox` / `service_net_isolate_only` lanes that deliberately ran the pinned
  pre-fix evaluator. The individual `response`/`ledger_row` leaves are not self-labelling,
  but the enclosing record is.
* `a0/a1/kapso_t1/DEVIATIONS.md:159` — the continuation of a sentence that names the
  superseded value in D-KT1-8; labelled by its sentence and section.

**Gitignored raw run state, a residual I do not consider closed.** `a0/tasks/maxcut/positive_control/e-star-state/`
is untracked-but-present run state (440 files) holding **48 Outcome files stamped
`08281d21…`**. It is not committed, so it is outside the "committed artifact" claim; but
it is on disk, it is what the positive-control runs produced, and nothing labels it. (The
gate's own state root, `a0/tasks/maxcut/gates/e-star-state/`, 17 030 files, carries **no**
superseded digest — it was rewritten by the re-stamp.)

### 5c. Artifacts the entry points rewrote, restored

| artifact | what happened | restoration |
|---|---|---|
| `a0/tasks/maxcut/conformance.report.json` | `conformance.py --check` rewrites it on every run; it is in `WATCHED` in `d5_entrypoints.sh`, which restores it and prints the fact | `git checkout -- a0/tasks/maxcut/conformance.report.json`; `git status --porcelain` empty afterwards |
| `a0/tasks/maxcut/gates/restamp.evidence.json` | the *documented* default invocation (`--before HEAD`) rewrites it (`before_revision: HEAD`, empty diffs). In the scripted run I pass `--out` into this directory instead, so the committed file is untouched there | `git checkout -- a0/tasks/maxcut/gates/restamp.evidence.json`; compared to the pre-run copy, byte-identical |

`git status --porcelain` is clean apart from `?? a0/verify/a1-delta/` after `run_all.sh`.

**What the conformance rewrite shows** (an observation, not part of the four fixes): the
committed report is the pre-`baf13884` state — its `p1` runs are 1158-byte Outcomes with
`graph.json` handed to the candidate, the re-run produces 1401-byte Outcomes with
`candidate_graph.json`, and every `outcome_digest` differs, while `verdict: PASS`,
`drift: []` and every `cut_edges` are identical. The report carries no
`evaluator_source_sha256`, so it is not a *digest* claim; it is a measurement report whose
per-Outcome digests no longer reproduce. Unlike the gate, nothing re-stamped it.

### 5d. The hostile probe

Re-running `python3 a0/a1/probes/hostile_candidate.py --out-dir /tmp/a1delta-hostile`
(model-free: the hostile candidate's TCP connects, no model call, no CEq; the repository is
untouched) reproduces `verdict: pass`, **13/13**, with `checks` byte-equal to the committed
file, `service_sandbox` booking 0 and `raw_pre_fix` booking 224 = `R = OPT`, and
`lane_visibility` now `/home/ebt: hidden · /tmp: hidden · /var/tmp: hidden`.

The caveat: the committed `a0/a1/evidence/hostile_candidate.json` records
`evaluator_used_for_the_comparison.differs_from.revision_full = 654d5da255a12dc40763b1a511d7247a832a3d99`.
That commit **is not reachable from any ref** — it is the pre-amend version of `7a1c0c16`
(visible in `git reflog`: `HEAD@{3}: commit`, then two `commit (amend)` entries). A fresh
run records `08bc5beb…` instead. The content claim ("HEAD's `e_star.py` is `f67ecd41…`,
differing from `75403e8c`'s `fa0932b4…`") is true and the digests are unchanged; only the
revision citation is dangling, so a third party cannot check out the revision the probe
compared against. The tree difference is real: the amended commit differs from the
dangling one in `CID.json`, `evidence/README.md` and `hostile_candidate.json` itself.

---

## 6. What I could not verify

* **The paid probes and the pilot.** `a0/a1/kapso_t1/evidence/live_t1.json`,
  `a0/a1/evidence/live_*.json` and `a0/a1/calibration/evidence/**` were verified by
  arithmetic (their own `usage`) and by digest, not by re-running them. No CEq was spent.
* **The contract revision awaiting the user's decision.** The `pc_exchange_k*` variants and
  the bounded-round positive control are recorded, not evaluated. I did not pre-empt the
  decision and did not touch a threshold.
* **The `NOT_ADMISSIBLE` verdict's substance.** I re-derived that the numbers are
  unchanged and that they fail the pre-registered ρ demand; I did not re-run the gate (it
  would have rewritten `gates/**` a second time) or question the design.
* **A campaign end-to-end.** There is none: the task is `NOT_ADMISSIBLE`.
* **KAPSO's internals** (`/home/ebt/kapso_ck/`, `/tmp/eve/` — upstream runtimes, read-only
  by rule). I reproduced the consequence of a stale tree (stub exit 3), not the code path.
* **The `EID_r`→`EID*` mapping under a real KAPSO session.** The mapping document is
  verified as bytes; that KAPSO's `EvaluationMaintainer` produces the same fingerprint for
  these bytes is taken from `tree.py`'s imported-function path, which I did not run under
  the adapter's interpreter.
* **`a0/meter`'s framing/budget internals** beyond the calibration verifier's own checks.

## 7. Deviations from this brief

* **I ran other workstreams' entry points and one probe**, as instructed, and two of them
  rewrote a committed artifact; both were restored (§5c) and the restoration is reported.
  `a0/a1/probes/hostile_candidate.py` was run with `--out-dir /tmp/...`; the repository was
  untouched by it (verified with `git status`).
* **I wrote outside this directory twice, transiently**: four canary files under `/tmp`,
  `/var/tmp`, `/home/<user>`, `/run/user/<uid>` (§4), all removed at the end of the probe
  and listed in its output. No byte of any file that is not one of my own canaries was
  read; `/home/<user>` was touched only to place and remove the canary, and the provider
  key was never opened.
* **`d2_declaration.py` monkeypatches `declaration.KAPSO_T1_TREE`/`KAPSO_T1_BINDING`** to
  point at a scratch tree, in-process, to construct the disagreement case. The module's own
  `_rel` fallback documents this use; nothing on disk changes.
* **`d4_canary.py` imports the pre-fix module from `git show 7a1c0c16^:…`** into a temp
  directory and runs it, to show the fix is a real change. That is a read of git history.
* **`d6_superseded.py` is a heuristic**, and its judgement is printed per line so it can be
  overridden by reading: line-scoped markers for prose, structural paths for JSON. The
  three items I judged labelled by context despite the heuristic flagging them are named in
  §5b.
* **Scans are scoped.** `d6` covers every tracked file; the gitignored-state check covers
  `a0/tasks/maxcut/**` only (§5b). A miss would depend on that scope; a hit does not.
