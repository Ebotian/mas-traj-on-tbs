# `a0/verify/a1-hygiene/REPORT.md` — the three evidence-hygiene findings, closed

Owner: `a0/verify/a1-hygiene/**`. This pass labels history; it decides nothing. **No
number moved**: no threshold, no gate verdict, no `B_hard` cap, no `EID*`, no
`EID_r`, and no stored `cut_edges`. **Zero model spend** — no model call, no `CEq`,
and no `E*` measurement re-run. Departures and their justifications are in
[`DEVIATIONS.md`](DEVIATIONS.md).

The findings are the three `a0/verify/a1-delta/REPORT.md` left open in §5b and §5d.
All three are about a reader (or a scan) mistaking a **superseded** digest for the
current one.

```console
$ sh a0/verify/a1-hygiene/run_all.sh      # model-free, ~1 min, 5/5, tree left as it was
```

---

## 1. Verdicts

| # | finding (a1-delta) | verdict | evidence |
|---|---|---|---|
| 1 | §5b: 276 Outcomes under `a0/tasks/maxcut/redesign/out/**` carry a superseded `evaluator_source_sha256` with `redesign/DEVIATIONS.md` silent | **CLOSED — labelled, not re-measured** | `redesign/HISTORY.md` + `redesign/out/HISTORY.json` (`schema a0.maxcut.redesign.history/v1`) + D-RD-9. The marker names the digest (`08281d21…`, `E*` at `11f55bf0`), the revision, the window, the current value (`dc6969ec…`) and all 276 paths. `h1_history.py` A: `listed 276, found 276, exhaustive True, path-list digest True` |
| 2 | §5b: 10 further files present a superseded digest as current — `WIRING-REPORT.md:46/200/222`, `DEVIATIONS.md:55/68/241/260`, `evidence/README.md:83`, `calibration/pilot_procedure.json:69` | **CLOSED — corrected in place, except the one frozen file** | each named line now reads `EID_r = manifest:63a9a83c…` / `a0_locator.json = 1e3b3a75…`, with the old value only inside a sentence saying it is the pre-rebuild one. `h1_history.py` B: `3465 tracked files scanned; 416 digest-carrying lines in 296 files`, no unlabelled line outside four named exceptions |
| 2b | the same finding for `calibration/pilot_procedure.json:69` | **NOT EDITED, by design — see §4** | its bytes are pinned by `B_hard.json` (`procedure.json_sha256 = 8fcc8795…`, asserted by `a0/verify/a1-final/v4_bhard.py` V1b). Labelled in the new `a0/a1/DEVIATIONS.md` **D-A1-15** instead |
| 3 | §5d: the hostile probe's evidence cites `654d5da2…`, a commit no ref reaches | **CLOSED — re-run at a reachable revision** | the probe was re-run (model-free) and its output installed; `after_side.revision_full`, `before_side.evaluator.differs_from.revision_full` and `evaluator_used_for_the_comparison.differs_from.revision_full` are now `d069766f…`. `--check-citations`: `citations checked: 6, dangling: [], verdict: pass` (against the *previous* evidence it exits 5 with exactly those three) |
| 3b | "also check its `before_side`/`after_side` blocks for the same class of unreachable citation" | **CLOSED — checked, and one of the three was in `before_side`** | `before_side.revision_full` (`75403e8c…`) and `before_side.evaluator.revision_full` were already reachable; the dangling value appeared in `after_side.revision_full`, `before_side.evaluator.differs_from` and `evaluator_used_for_the_comparison.differs_from`. All three now resolve and are ancestors of `HEAD` |

## 2. The one command, and what each step proves

```console
$ sh a0/verify/a1-hygiene/run_all.sh
1. every stale digest in a0/a1/** and redesign/** is labelled, or a named exception
   A. … HISTORY.json: listed 276, found 276, exhaustive True, path-list digest True
   verdict: pass                                   # 296 files, 416 digest-carrying lines
2. the L1 instances re-derive byte-identically (read-only)
   OK: 28 graphs re-derived and byte-identical; manifest matches
3. the L2 table re-reduces from the stored Outcomes (no E* re-run)
   exchange_k10   0.116584858 0.615639328     4     4   True   True
   OK: exchange_opt reproduces the frozen PC cut_edges on all 24 dev graphs
   out/l2_results.json: byte-identical
4. the decision table re-reduces from the two results files
   lever_data.json: byte-identical
5. every commit the hostile probe's evidence cites is reachable from HEAD
   citations checked: 6  dangling: []  verdict: pass
a1-hygiene: PASS (5/5) — the tree is left as it was
```

Steps 2–4 are the "re-run the verify equivalent" the brief asked for. There is no
`redesign/verify.py`; the equivalents are `gen/gen_l1_instances.py --check` (the
instance regeneration check `run_all.sh` itself runs), `gen/run_l2.py` **without**
`--force` (it reuses the stored Outcomes and asserts `exchange_opt == the frozen
PC` on all 24 dev graphs) and `gen/make_lever_data.py` (the decision table's
reduction). All three reproduce the committed files **byte-for-byte**, which is the
evidence that the study's conclusions do not depend on the superseded digest — and
none of them re-invokes `E*`.

The command above is run **after** the commit, not only before it, and it is what
found the one defect in this pass's own tooling: `h1_history.py` scans
`git ls-files`, so while the two new label files were still untracked it passed
without seeing them. The committed run flagged both, and the rule was generalised
(a `HISTORY.md` / `HISTORY.json` name, or a `.../history/` directory, is a history
record by construction). See `DEVIATIONS.md` D-HYG-11. `a1/verify.py` was also
re-run at the committed revision: **6/6, rc 0, tree clean afterwards**.

## 3. Every file this pass changed

| path | before → after |
|---|---|
| `a0/a1/WIRING-REPORT.md` | verdict row 5b and §6: `registered_evaluation_tree = manifest:6b1d6fcc…` → `manifest:63a9a83c…` (with the old value marked pre-rebuild at `f8f8b386`); the factor rows: `eid_r: manifest:6b1d6fcc…` → `63a9a83c…`, `a0_locator.json 5a0c99ff…` → `1e3b3a75…` |
| `a0/a1/DEVIATIONS.md` | D-A1-2 line 55 and D-A1-6 line 241: `EID_r = manifest:6b1d6fcc…` → `manifest:63a9a83c…`; D-A1-2's evidence table and D-A1-6's factor table: `6b1d6fcc…`/`5a0c99ff…` → `63a9a83c…`/`1e3b3a75…`, each followed by a labelled note naming the pre-rebuild pair; **new closing entry D-A1-15** (the frozen pilot procedure) |
| `a0/a1/evidence/README.md` | line 83: "the tree whose `EID_r` = `manifest:6b1d6fcc…` that `AID_r…` now pins" → `manifest:63a9a83c…`; one new paragraph on why `hostile_candidate.json` was re-run a second time; one clause on its status row |
| `a0/a1/evidence/hostile_candidate.json` | re-run at `HEAD = d069766f…`: three revision citations `654d5da2…` → `d069766f…`; 96 per-run leaves (nonce, OIDs, wall/`ts`, mount ids, store path, proc counts, git-object sample, `candidate_source_sha256`) moved; `verdict`, `checks` (13/13), `graph`, `lane_visibility` and the harness scores unchanged |
| `a0/a1/probes/hostile_candidate.py` | **new** `--check-citations REPORT` mode (+ docstring paragraph explaining the dangling-citation class). The measurement path and the 13 checks are untouched; the mode only runs `git` |
| `a0/tasks/maxcut/redesign/HISTORY.md` | **new** — the labelled history record: the superseded digest, the revision, the window, why re-deriving is a re-run, and the current value |
| `a0/tasks/maxcut/redesign/out/HISTORY.json` | **new** — the machine-readable marker: superseded + current digests, `measured_against`, per-directory counts, all 276 paths with their `canonical_digest`, `files_sha256` |
| `a0/tasks/maxcut/redesign/DEVIATIONS.md` | **new entry D-RD-9** — why the digests are labelled and not re-stamped |
| `a0/tasks/maxcut/redesign/LEVERS.md` | §7's artifact table gains `HISTORY.md`/`out/HISTORY.json` and `DEVIATIONS.md` → `D-RD-1 … D-RD-9`, plus a short "read this before you compare digests" paragraph |
| `a0/verify/a1-hygiene/{REPORT.md,DEVIATIONS.md,run_all.sh,h1_history.py}` | **new** — this record and the checker. Raw output is written outside the repository (`$A1_HYGIENE_OUT`, default `/tmp/a1-hygiene-out`): step 5's report records `HEAD`, so a committed copy would be rewritten by every run — see D-HYG-12 |

Nothing else was touched. In particular: no Outcome under `redesign/out/**` was
edited (all 276 still recompute their own `canonical_digest`), no threshold file was
opened, no `E*` byte changed, `a0/A1-INTERIM.md` and
`a0/tasks/maxcut/positive_control/e-star-state/**` were left alone, and the files
another workstream had in flight while this pass ran (`a0/a1/declaration.py`,
`a0/tasks/maxcut/gates/**`; committed by them as `5c9cd0c8`) were never staged,
reverted or touched here.

## 4. What could not be closed, and why

* **`a0/a1/calibration/pilot_procedure.json:69` still names `6b1d6fcc…`.** It is the
  frozen pre-registration and its freeze is a hash: `B_hard.json` pins
  `procedure.json_sha256 = 8fcc8795e8f5c044771c6adc29c7fecdbbe730d5fe74bd2d51d4b6ca425cd3eb`
  and `v4_bhard.py`'s V1b check asserts it. Editing one character breaks that check
  and leaves a frozen `B_hard` describing bytes that no longer exist — a re-freeze of
  the pre-registration, which is not this pass's to make and which no threshold may
  be touched for. The honest alternative, taken, is the label: `a0/a1/DEVIATIONS.md`
  **D-A1-15** states the stale value, the current one, and the two mechanical options
  for whoever owns `B_hard`. No pilot number depends on the line.
* **`a0/A1-INTERIM.md:18`** still reads `EID* = cddfa64e…` (superseded twice). The
  coordinator owns the file and the brief forbids editing it. It is the one
  present-tense superseded identity a reader can still hit, and it is named in
  `DEVIATIONS.md` D-HYG-9.
* **`a0/tasks/maxcut/positive_control/e-star-state/**`** — 440 files, **48 Outcomes
  stamped `08281d21…`**, untracked and `.gitignore`d. Same class as finding 1, but
  not a committed artifact; the brief excludes it. Residual, not closed.
  (`redesign/out/e-star-state/**` is also gitignored but carries no evaluator digest
  at all, so it is not a stale-digest artifact.)
* **`a0/a1/calibration/evidence/{simpleloop,kapso}/pilot_arm.json:132`** carry
  `module_sha256 = fd234f69…` (the pre-D-A1-14 sandbox module) with no label inside
  the file. They are paid pilot artifacts and editing them would falsify their own
  record; the label is `a0/a1/DEVIATIONS.md` D-A1-14 §1, which names the file, the
  digest and the reason. This is the weakest label in the set and is listed as a
  named exception in `h1_history.py` rather than silently passed.
* **`a0/a1/evidence/hostile_candidate.json`'s per-lane leaves** carry the *pinned
  pre-fix* evaluator's own digest (`4afff01f…` = `E*` at `75403e8c`), written by
  that evaluator when it ran. The enclosing record names the revision and says it
  differs from `HEAD`; deleting the leaves would delete the evidence that the
  before-side comparison ran the pinned bytes. Named exception, same as `a1-delta`
  judged.
* **The probe's own re-run cannot be made to prove its citation for the future.**
  `--check-citations` catches a citation orphaned by a later amend or rebase, but
  nothing forces a future committer to run it. What is checkable now is checked;
  what is not is that the next person runs the check.

## 5. What this pass does *not* claim

* That the redesign's stored digests are current. They are labelled history, and the
  study was not re-measured — that is the point (D-RD-9).
* That any decision in the testbed changed. None did; the task gate is still
  `NOT_ADMISSIBLE`, `B_hard` is byte-identical, `EID*` still recomputes to
  `7ce9e72f…` and the contract revision awaiting the user's decision was not
  pre-empted — the `pc_exchange_k*` variants were not read for this pass except as
  the L2 table's own rows.
