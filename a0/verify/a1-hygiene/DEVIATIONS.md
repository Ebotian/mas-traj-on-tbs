# `a0/verify/a1-hygiene/DEVIATIONS.md` — what this pass departed from, and why

Owner: the hygiene pass that closes the three findings `a0/verify/a1-delta/REPORT.md`
left open — §5b (286 files carrying a superseded digest with no label, 276 of them
under `a0/tasks/maxcut/redesign/out/**`, plus ten in `a0/a1` prose) and §5d (the
hostile probe's evidence citing a commit no ref reaches). **No decision moved**: no
threshold, no gate verdict, no `B_hard` cap, no `EID*`, no `EID_r`, and no stored
`cut_edges`. Zero model spend: nothing here made a model call or spent `CEq`, and
no `E*` measurement was re-run.

The owned paths are the ones the assignment named: `a0/tasks/maxcut/redesign/**`,
the named prose lines in `a0/a1/**`, and `a0/a1/probes/hostile_candidate.py`'s
revision citation. `a0/A1-INTERIM.md` and
`a0/tasks/maxcut/positive_control/e-star-state/**` were not touched.

---

## D-HYG-1 — this directory is the record; the pass had no directory of its own

The assignment says to record deviations in "your own `DEVIATIONS.md`". No
workstream directory existed for this pass, so one was created
(`a0/verify/a1-hygiene/`) rather than writing into another workstream's log
(`a0/verify/a1-delta/**`, `a0/verify/a1-final/**` are other passes' records and
were left byte-intact). The four files written outside it are exactly the ones the
assignment named, plus the two new labelling files under `redesign/`: see D-HYG-6.

## D-HYG-2 — the 276 redesign Outcomes are labelled as history, not re-measured

`a0/tasks/maxcut/redesign/out/**`'s 276 Outcomes carry
`evaluator_source_sha256 = 08281d21…`, which is `E*` at **`11f55bf0`** — superseded
twice since (`6dd717c2` → `4afff01f…`, `baf13884` → `dc6969ec…`). They were left
byte-identical. The label is `redesign/HISTORY.md` (the record: which revision the
whole `out/**` tree was measured at, and why re-deriving is a re-run),
`redesign/out/HISTORY.json` (the machine-readable marker: superseded and current
digests, the revision, the per-directory counts, all 276 paths) and
`redesign/DEVIATIONS.md` D-RD-9.

**Why not re-stamp them.** An Outcome's `canonical_digest` is a self-digest over its
own bytes, and `a0/tasks/maxcut/INTERFACE.md` §5/§6 make the harness its author, so
editing one to carry a new `evaluator_source_sha256` would falsify the measurement
*and* break its self-digest. The levers were measured against the revision current
at the time and their conclusions do not depend on the digest; re-deriving the
digests means re-running `gen/l1_eval.py` and `gen/run_l2.py` — the lever study
itself — which the assignment forbids and which would move no conclusion.

## D-HYG-3 — `calibration/pilot_procedure.json:69` was **not** edited, on purpose

That file's line 69 records the KAPSO arm's tree as
`"a0/a1/kapso_t1/tree (EID_r = manifest:6b1d6fcc…)"` — the pre-rebuild value. It is
left byte-frozen because its freeze is a hash: `a0/a1/calibration/B_hard.json` pins
`procedure.json_sha256 = 8fcc8795e8f5c044771c6adc29c7fecdbbe730d5fe74bd2d51d4b6ca425cd3eb`
(the file's sha256) and `a0/verify/a1-final/v4_bhard.py`'s V1b check asserts it.
Editing one character would break that check and leave a frozen `B_hard` describing
bytes that no longer exist — a re-freeze of the pilot pre-registration, which is not
a documentation pass's to make and which no threshold may be touched for.

**The honest alternative, taken:** the line stays frozen and its staleness is
recorded where a reader meets it — `a0/a1/DEVIATIONS.md` D-A1-15 (new, see D-HYG-6)
names the stale value, the current one and the freeze that forbids the edit. The
two mechanical options, stated for whoever owns `B_hard`: correct line 69 **and**
re-derive `procedure.json_sha256` in the same commit, or leave it and keep the
label. **No pilot number depends on the line** (it is a label; `f(telemetry) →
B_hard` was applied to the measured ledger rows), and
`calibration/verify.py --with-rehearsal` is not affected.

## D-HYG-4 — the hostile probe was re-run, and its committed evidence was replaced

Its evidence cited `after_side.revision_full = 654d5da2…`,
`before_side.evaluator.differs_from.revision_full = 654d5da2…` and
`evaluator_used_for_the_comparison.differs_from.revision_full = 654d5da2…`. That
commit resolves but **no ref reaches it** — it is the pre-amend version of
`7a1c0c16`. `before_side.revision_full` (`75403e8c…`) and the pinned evaluator's own
citation were already reachable.

`python3 a0/a1/probes/hostile_candidate.py` (model-free: the hostile candidate's
TCP connects, no model call, no `CEq`) was re-run at `--out-dir /tmp/a1/hostile`
(the path the committed artifact records) and its output installed as
`a0/a1/evidence/hostile_candidate.json`. **What moved, enumerated by a structural
diff of the two JSON documents:**
* the three revision fields above → `d069766f…`, the `HEAD` of the run (reachable,
  and an ancestor of every later commit);
* 96 leaves under `runs/**` that are per-run identifiers by construction: the
  harness nonce, `measurement.oid`, `behaviour_digest`, `canonical_digest`,
  `started_at`, ledger `ts`/`wall_sec`/`measurement_oid`, the before-side store's
  `/var/tmp/a0-a1-hostile-<pid>` path, sandbox mount ids/devices/entry counts, the
  `/proc` visible-pid count and key-variable pid, and the repository's git-object
  sample;
* `candidate_source_sha256` — the probe bakes the before-side store's absolute path
  (which contains a pid) into the candidate it generates, so the generated
  candidate's bytes change per run. That is the probe's own design, not drift in a
  measured artifact;
* `verdict`, `checks` (all 13), `graph`, `lane_visibility`, `candidate` and the
  harness scores are **unchanged** (`pass`, 13/13, `service_sandbox` 0,
  `raw_pre_fix` 224 = `R` = OPT, `lane_visibility` `/tmp: hidden`).
The claim the artifact exists for is therefore re-measured at a reachable revision,
not re-labelled.

## D-HYG-5 — `--check-citations` was added to a file the assignment licensed only at its citation

`a0/a1/probes/hostile_candidate.py` is mine "for its revision citation", and the
citation defect cannot be caught at run time (a run records `HEAD`, which is
reachable by construction; only a later amend orphans it). So the file gained a
read-only mode that re-checks a committed report:

```console
$ python3 a0/a1/probes/hostile_candidate.py --check-citations a0/a1/evidence/hostile_candidate.json
```

It resolves every cited field (`before_side(.evaluator(.differs_from))`,
`after_side`, `evaluator_used_for_the_comparison(.differs_from)`) and requires each
to resolve **and** be an ancestor of the current `HEAD`; a dangling one exits 5 and
is printed. Against the *previous* evidence it exits 5 with exactly the three
dangling citations above — i.e. it detects the defect it was written for — and
against the new evidence it exits 0 with `citations_checked: 6, dangling: []`. The
probe's own measurement path and its 13 checks are untouched; the addition is a
`git`-only query that measures nothing.

## D-HYG-6 — edits past the named lines, and why each was needed

| file | beyond the named line | why |
|---|---|---|
| `a0/a1/DEVIATIONS.md` | new closing entry **D-A1-15** (the `pilot_procedure.json` freeze, D-HYG-3), and a labelled blockquote under D-A1-2's evidence table and D-A1-6's factor table | the task's requirement is that a reader can never take a superseded digest for the current one; the two tables are where the reader meets `6b1d6fcc…`, and the frozen-procedure residual needs a home in `a0/a1` or a reader of `a0/a1` will not see it |
| `a0/a1/evidence/README.md` | one paragraph and one table-row clause | the file *is* the evidence inventory; after D-HYG-4 the `hostile_candidate.json` row had to say why that file was re-run a second time, and the row's own subject moved |
| `a0/tasks/maxcut/redesign/LEVERS.md` | two rows in §7's artifact table and a short "read this before you compare digests" paragraph | it is the directory's entry document, and D-HYG-2's digest is the one thing in it a reader can trip over |

Nothing else in those files was touched. The named lines themselves were corrected
in place (`WIRING-REPORT.md` 46/200/222 + 223's `a0_locator.json` value,
`DEVIATIONS.md` 55/68/241/260, `evidence/README.md` 83): each now names the current
value (`EID_r = manifest:63a9a83c…`, `a0_locator.json = 1e3b3a75…`), and the old
value appears only inside a sentence that says it is the pre-rebuild one.

## D-HYG-7 — another workstream's in-flight edits were left alone, and not committed

While this pass ran, `git status` also showed `a0/a1/declaration.py` and
`a0/tasks/maxcut/gates/{DEVIATIONS.md,README.md,refreeze_evidence.py,restamp_evidence.py}`
modified — that workstream was landing finding 2c's `CID`-vs-tree cross-check and
finding 3c's non-vacuous re-stamp (they committed as `5c9cd0c8` while this pass was
in progress). They were **not** staged, **not** reverted and **not** touched; this
pass's commit contains only the paths listed in D-HYG-6 plus the four `a0/a1` files
named by the assignment, and `a1-hygiene/`. Nothing of mine needed restoring: no
entry point rewrote an artifact I own, because the only entry point run against this
tree was the probe (out-dir `/tmp`) and the redesign's three reductions — all
byte-identical, and re-checked after `5c9cd0c8` landed.

## D-HYG-8 — gitignored raw run state: reported, not touched

* `a0/tasks/maxcut/positive_control/e-star-state/**` — 440 files, **48 Outcomes
  stamped `08281d21…`**, untracked and `.gitignore`d (`.gitignore:11`). The
  assignment excludes it from this pass; it is left as it is and named here as a
  residual: the same class of stale digest as D-HYG-2, but not a committed artifact,
  so no reader of the repository meets it. Closing it would mean either a label file
  inside a gitignored directory (invisible to every consumer) or deleting run state
  this pass does not own.
* `a0/tasks/maxcut/redesign/out/e-star-state/**` — 2243 files, also `.gitignore`d,
  and it carries **no** `evaluator_source_sha256` at all, so it is not a
  stale-digest artifact. Left untouched.

## D-HYG-9 — two residuals this pass could not close

1. `a0/A1-INTERIM.md:18` still reads `EID* = cddfa64e…` (superseded twice; the
   coordinator owns the file and the brief forbids editing it). It is the last
   present-tense superseded identity in the tree that a reader can hit.
2. `a0/a1/evidence/hostile_candidate.json`'s per-lane leaves still carry
   `evaluator_source_sha256 = 4afff01f…` — the **pinned pre-fix** evaluator's own
   digest (`75403e8c`), written by that evaluator when it ran. The enclosing record
   labels it (`before_side.claim`, `evaluator_used_for_the_comparison.revision =
   75403e8c`, `differs_from`), which is the same judgement
   `a0/verify/a1-delta/REPORT.md` §5b made; the alternative — deleting the leaves —
   would remove the evidence that the before-side comparison ran the pinned bytes.

## D-HYG-10 — verification was by execution, and it re-ran nothing of the study

See `REPORT.md` for the commands and their output. `gen/run_l2.py` (no `--force`)
reuses the stored Outcomes rather than re-invoking `E*`, and both reductions were
confirmed byte-identical to the committed files, so the diagnosis that the
conclusions survive the superseded digest is measured rather than asserted.

## D-HYG-11 — the checker was itself wrong once, and the commit is what caught it

`h1_history.py`'s scan runs over `git ls-files`, so before this pass committed, the
two label files it added (`redesign/HISTORY.md`, `redesign/out/HISTORY.json`) were
untracked and invisible to it — it reported `pass` while the files it exists to
justify were outside its scan, and while `run_all.sh`'s step 1 was therefore
passing for an incomplete reason. Committing made them tracked, the very next run
of `run_all.sh` failed with both of them listed as `UNLABELLED`, and the fix was to
classify a *name* as a label: `HISTORY.md` / `HISTORY.json`, or any path under a
`.../history/` directory, is a history record by construction. That also generalises
the rule the `kapso_t1` directory already relied on.

Two smaller notes from the same episode. The check now also runs post-commit (the
committed hash is re-verified, not just the working tree), and `a0/verify/**` is
deliberately outside the scan scope: a checker has to *name* the digests to have a
list, so it cannot label itself by line-scoped wording, and its own raw output
echoes the findings — an infinite regress that would make the scan useless. That is
stated in the script, not hidden.

**No artifact was affected by this**: the fix is in the checker and the label
files, both of which this pass owns, and it was found by re-running the check after
committing rather than by reading it.

