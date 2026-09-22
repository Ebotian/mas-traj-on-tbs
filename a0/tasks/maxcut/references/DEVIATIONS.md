# Deviations from `../INTERFACE.md`

Owner: the references workstream (`a0/tasks/maxcut/references/`).

Nothing below relaxes a gate, changes a frozen identity, or alters a number that
another workstream depends on. Each item is a place where the implementation is
*not literally* what the interface document says, stated so that a reader does
not have to discover it.

---

## D1 — where this file lives (filing location only)

`INTERFACE.md` (header) requires any deviation to be recorded in
`a0/A1-DEVIATIONS.md`. My assignment for this round requires me to record it in
`DEVIATIONS.md` **inside my own directory** and forbids writing outside that
directory. I followed the assignment, so this file is `references/DEVIATIONS.md`
rather than a section of `a0/A1-DEVIATIONS.md`.

**Effect on the interface: none.** Same content, different path. If the
coordinator wants it merged, the text is deliberately self-contained and can be
copied verbatim.

## D2 — a reference run is verifiable but its stdout is not byte-reproducible

`INTERFACE.md` §6 rule 4 freezes: the same (candidate bytes, graph bytes, seed)
run twice must produce byte-identical `partition.json`, otherwise the outcome is
`non_deterministic`. §7 fixes `tau`, and the ABI fixes the timeout semantics.

The reference ensemble is driven through MQLib's CLI, whose only termination
control is `-r <seconds>` — a **wall-clock** limit. MQLib stops when its clock
passes the limit, so the iteration count differs between two runs of the same
triple and the process's stdout is **not** byte-identical. Measured, at 30 s,
seed 1337, `G_dev_0003` (`build/determinism.txt`):

```
BURER2002      seed=1337 limit=30s  objective 338/338  stdout=DIFFERS  solution_line=IDENTICAL
FESTA2002GPR   seed=1337 limit=30s  objective 338/338  stdout=DIFFERS  solution_line=IDENTICAL
DESOUSA2013    seed=1337 limit=30s  objective 300/300  stdout=DIFFERS  solution_line=IDENTICAL
```

The only bytes that differ are inside MQLib's history field, which records the
wall-clock second at which each incumbent was found. **The solution line — the
thing that becomes `partition.json` — was byte-identical in all three cases**,
and the objective was identical in all three.

**Why this is not a relaxation of §6 rule 4.** That rule binds the T1 candidate
ABI, where the *harness* owns the realisation and can require byte equality of
the artifact. `R_i` is not a candidate outcome: it is a maximum over runs, and
each contributing run is stored as a canonical `partition.json` with its
sha256. So `R_i` is **re-verifiable** by a third party (recompute the cut from
`graph.json` + `partition.json`) even though it is not **regenerable**
bit-identically.

**What a consumer must not assume.** Re-running the ensemble will reproduce
`R_i` in practice — MQLib saturates these instances long before 30 s, so the
incumbents are already stable — but it is not guaranteed by construction. The
guarantee this directory offers is the partitions and their hashes, not the
driver's output.

**Cheaper fix that was considered and rejected for this round.** Iteration-count
termination would make runs exactly reproducible, but MQLib supports it only for
its `BASELINE` heuristic; the six required heuristics accept seconds only. Using
`BASELINE` instead would have changed the ensemble, which the assignment fixes.

## D3 — additive artifacts under `references/`

`INTERFACE.md` §1 describes `references/` as "reference targets `R_i` /
`OPT_i` / `U_i` + build logs". This directory additionally contains:

* `smoke/` — five self-generated canonical graphs (ER, RR, BA, Planted) used to
  validate the pipeline before the frozen suite appeared. They are **not** part
  of the suite and are never referenced by `targets.json`.
* `tools/` — the generator, driver, independent evaluator, upper-bound code and
  the targets builder, plus `reproduce.sh` / `check_determinism.sh`.
* `scip/` — the exact-certification attempt (MIP models, SCIP logs, verdicts).

All three are additive; no interface field is repurposed and no suite file is
touched. `tools/make_smoke_graphs.py` writes only into `references/smoke/` and
never into `../suite/`.

## D4 — `OPT_i` is null far more often than not, and that is the honest answer

`INTERFACE.md` §9 describes a reference target but does not require optimality.
Where optimality is not certified, `targets.json` reports `OPT: null` and
`opt_certified: false` rather than promoting the feasible reference. This is
strictly more conservative than the interface requires, and it is the point of
the distinction the assignment makes: a feasible value is a lower bound on the
optimum, never an upper bound.

## D5 — `U_i` includes SCIP's dual bound, which is a floating-point quantity

`U_i` is the minimum over the bounds actually computed, and for the 42 certified
graphs that minimum **is** SCIP's dual bound (the reported upper bound that
equals `R_i`). SCIP's bound is a floating-point number from a MIP solver, not an
exact rational like the rest of this table. It is floored to an integer before
being used, which is the conservative direction, but a reader who treats `U_i`
as exact-arithmetic rigor should know that one of its contributors is not.

The three bounds computed in `tools/upper_bounds.py` (spectral, SDP/Delorme–
Poljak dual, Burer–Monteiro certificate) rest on a numeric eigendecomposition
with an added safety margin, for the same reason; the module's docstring states
this and every `U_i >= R_i` is checked (60/60 hold). Nothing here is used to
certify optimality except by closing a gap, and a badly wrong `U_i` would show
up as `U_consistent_with_R: false` rather than silently.

## D6 — `targets.json` carries the 12 calibration graphs as well as the 48 dev+eval

The assignment names 48 graphs (24 dev + 24 eval). `targets.json` also contains
the 12 calibration graphs, because they are part of the same frozen suite and a
reference table that silently omitted them would invite a consumer to recompute
them independently. They are labelled `role: "calibration"` and, per
`INTERFACE.md` §9, **must not take part in any selection**; the ensemble budget
they received is identical to the others and is recorded in `coverage.json`.
A consumer that wants exactly the required 48 filters on `role`.

## D7 — the top-up pass gives 18 graphs a *larger* budget than the other 42

`R_i` is a maximum over feasible solutions, so a larger budget can only raise it;
this is monotone and cannot corrupt a comparison. It does make the per-graph
budget heterogeneous, so the difference is stated rather than left implicit:
`coverage.json` records the exact runs each graph received, and `targets.json`
records `budgets_applied_s` and `R_from_topup` per graph. On the graphs where
the top-up found nothing new, the added budget is evidence *about* `R_i`
(it resists a 4x budget) rather than a change to it.

## D8 — `R_i` is a maximum, so it is not bit-reproducible in the §6 rule-4 sense

See D2. Restated here in one line because it is the single most likely thing for
a consumer to assume wrongly: this table guarantees that every `R_i` can be
**re-verified** (recompute the cut from the stored `graph.json` +
`partition.json`, independently of MQLib), not that re-running the driver
reproduces the same bytes.

## D9 — the witness partitions are removed from this repository; only commitments remain

**What changed.** `logs/partitions/**`, `logs_topup/partitions/**`,
`scip/*.partition.json` and the MQLib stdout transcripts in `logs/raw/**` and
`logs_topup/raw/**` are gone from the working tree. `witnesses/commitments.json`
records, for each of the 1968 witnesses and 1908 transcripts, the graph id, the
run id, the sha256 of the file bytes, the sha256 of the canonical bytes and the
recomputed cut; `targets.json`, `coverage.json` and the per-run records under
`logs/runs/**` and `logs_topup/runs/**` are unchanged.

**Why.** `INTERFACE.md` §12 forbids eval from entering "any path a candidate can
read", and §7 of this directory's README treats the stored partitions as
dangerous but keeps them. The independent verifier measured what that costs
(`a0/verify/a1-testbed/REPORT.md` §2c): a candidate that copies
`references/logs/partitions/G_eval_0001__*.partition.json` scores exactly
`R = OPT = 217` on the hold-out, through `e_star.py` and through
`a0/a1/eval_service.py`. Permissions cannot be the control here — every process
runs as one uid without root — so the only non-obscurity control is for the
vector not to exist.

**What is lost, stated plainly.** `R_i` can no longer be recomputed *from this
repository alone*; a third party re-verifies the values and the commitments
(`tools/verify_targets.py`), and re-verifies witnesses from bytes only if they
are handed a retained copy (`tools/verify_targets.py --witnesses <dir>`,
`tools/seal_witnesses.py verify --corpus <dir>`). This is a real reduction in
re-computability, accepted because the alternative is a hold-out whose answers
are on disk. Two consequences a consumer must know:

1. **The bytes are still in git history.** They were committed before this
   change, so `git show <rev>:<path_removed>` returns them until the history is
   rewritten. Removing them from the *tree* is not removing them from the
   *repository*, and only the coordinator can authorise a `git filter-repo`.
   `e_star.py` masks `.git` and this directory from the candidate for exactly
   that reason (D-T1-12 in `../DEVIATIONS.md`).
2. **Copies outside this directory are outside this directory's control.**
   `witnesses/fs_policy.json` lists the ones the leak probe found (`/tmp/mcwork`:
   `scip_test2/G_dev_0001.partition.json` scores 224 = R = OPT, plus MQLib stdout
   with `Solution:` lines); `e_star.py` masks each of them.

**Procedure.** `tools/seal_witnesses.py audit` recomputes every witness and
cross-checks it against the run records, the SCIP records and `targets.json`
(60/60 graphs: per-graph maximum == `R`, every file sha256 == the value its run
record commits to). `seal --apply` writes the commitments and deletes the files;
it refuses to run while any cross-check fails.

## D10 — the "one command to believe the table" now has two modes

`tools/verify_targets.py` used to read `logs/partitions/**` unconditionally. It
now checks each witness against its sealed commitment when the vector is absent,
and recomputes from bytes when it is present (the default before the seal) or
when `--witnesses <dir>` names a retained copy. The check that `R` is the maximum
over the per-run records stays in both modes, and so do the `U >= R` and
`OPT ⇔ certified` checks. The printed summary says which mode ran and how many
witnesses were recomputed from bytes, so a reader cannot mistake a
commitment-check for a recomputation.
