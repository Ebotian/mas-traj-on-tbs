# `a0/verify/a1-final/DEVIATIONS.md` — how this verification departed from the brief, and why

Owner of `a0/verify/a1-final/**`. Nothing in this directory fixes anything; it verifies,
reports, and names what it could not reach. The findings are in `REPORT.md`, the verdict
table in §1 there. This file records the departures, the interpretations I had to make, and
the two things a reader should not mistake for the artifact's own claims.

---

## D-VF-1 — the working tree moved while I was verifying it

The brief described a committed, frozen tree. It was, and then it was not entirely: at
21:36–21:41, *during* this pass, a sibling workstream edited
`a0/a1/probes/hostile_candidate.py` and `a0/tasks/maxcut/generators/DEVIATIONS.md` in the
shared working tree and committed them as **`8057c1ce`** (it pins the hostile probe's
"before" side to `75403e8c`, closing the 9/13 that `a0/a1/DEVIATIONS.md` D-A1-13 had left
open). `HEAD` therefore went `3bff97b6 → 8057c1ce` between two of my commands.

**What I did.** Ran the identity chain and `a0/a1/verify.py` again at `8057c1ce`
(14/14 and 6/6, `out_v1_identity.txt` / `out_v1_verify.txt`), re-ran the superseded-digest
scan there (897 files, the count in `REPORT.md`), and reported both revisions in the
header. Neither edited file is in the identity chain, in `a0/a1/verify.py`'s steps, in
`T1.contract.json`/`T1-EID.json`, or in the calibration evidence, so no verdict below
depends on which of the two revisions a command saw. I did **not** commit the sibling's
edits and did not touch those files.

**Why it matters to a reader.** A "frozen tree" claim is a claim about a commit. Two of my
probes (`v1_identity`, `v4_bhard`, `v6_labels`) ran at `3bff97b6` and were re-run at
`8057c1ce`; the rest ran at `3bff97b6` and their inputs are byte-identical at both. The
`sandbox_receipt` / state roots under `/tmp/a1final-closures/` are from the earlier
revision's `E*`, which is the same `E*` as `8057c1ce`'s.

---

## D-VF-2 — I treat `a0/a1/kapso_t1/**` as in scope, and say so rather than assume it

The brief names the A1 testbed and lists what is frozen; `kapso_t1/` is not in that list,
but it is inside `a0/a1/`, it is pinned into `AID_r` by
`a0/a1/declarations/causal_audit.json`, and `a0/a1/DEVIATIONS.md` D-A1-2/D-A1-6 treat it as
part of this testbed. So I verified it, found it red (`REPORT.md` §2a), and reported it as
a defect **with the scoping reading named** — it is also defensible that it is another
workstream's pinned deliverable awaiting a re-freeze decision. I did not choose between the
two readings, and I did not rebuild the tree.

---

## D-VF-3 — I ran other workstreams' entry points, four of them

`a0/a1/verify.py`, `a0/a1/kapso_t1/verify.py`, `a0/a1/calibration/verify.py` and
`a0/a1/probes/hostile_candidate.py` are the artifacts' own re-runnable claims; a
verification that refuses to invoke them verifies nothing about them.

* All four are **model-free**. `kapso_t1/verify.py` runs its rehearsal, which skips the
  model call by its own flag; the paid arms are separate commands and were not run.
* All four are **read-only on the tree**, measured: after `sh a0/verify/a1-final/run_all.sh`,
  `git status --porcelain` holds only `?? a0/verify/a1-final/`. The earlier verifier had
  measured `a0/a1/declarations/CID.json` being rewritten by `verify.py`; on this revision
  the rebuild is byte-identical and the file does not move.
* The one file I wrote inside another workstream's directory tree: none.

---

## D-VF-4 — the provider key was tested for *reachability*, never read

`~/gptapi.md` appears in my probes as two named paths
(`Path.home()/…` and the literal `/home/ebt/gptapi.md`), and the probe records only whether
`open()` succeeded and the file's size. No byte of it is read into a variable, printed,
copied, or committed — `out_v2_closures.json` contains `"bytes": 591` and nothing else.
The same rule for `/proc/*/environ`: only variable **names** are recorded, and only whether
a name matches a key-shaped pattern. `/home/ebt/gptapi.md` was never read by me in any lane
other than as this readability probe.

---

## D-VF-5 — scans are scoped, and a miss depends on the scope

* `v1b_superseded.py` scans every **tracked** file (via `git ls-files`), excluding
  `__pycache__`, this directory and `a0/verify/a1-testbed/` — both are reports quoting
  digests as history, which is what a report is for. A hit does not depend on the exclusion.
* `v6_labels.py`'s broad surface is `a0/tasks/maxcut` + `a0/a1` (20 417 files), not the
  whole repository. Stated in the report; a hit would not depend on the scope, a miss does.
* `v2_closures.py`'s partition sweep covers `/tmp`, the task tree and `a0`; the answer stores
  that `fs_policy.json` names outside the repository are probed **by name** as well, so the
  sweep's scope does not carry the negative result.

---

## D-VF-6 — one check uses a corpus outside the repository

`suite/README.md` §5.2 quotes `seal_witnesses.py verify --corpus <retained corpus>`, and the
corpus is not committed. I found a retained copy on this machine at `/tmp/vfix/corpus`
(1968 partition files) and ran the check against it — it verifies all 1968. I named the path
in the report and did not copy any part of it into the repository. The
`--corpus`-free half of that check needs no corpus and is reproducible from `commitments.json`
alone.

---

## D-VF-7 — my probes write to `/tmp`, not to the repository

`v2_closures.py` and the sandbox probes write their state roots under
`/tmp/a1final-closures/`; `v7_staging.py` and `v8_consequences.py` use `tempfile` and clean
up. The paths recorded in `out_v2_closures.json` therefore point at `/tmp` and are not
reproducible byte-for-byte later; what is reproducible is the *command*, which `run_all.sh`
re-runs. The one-shot canary test in §3 of the report used `/tmp/a1final-canary/` (a
128-element all-zero `partition.json`, not an answer) and `/tmp/a1final-probe/`; both were
removed after the measurement.

---

## D-VF-8 — what I did not do, on purpose

* No fix, no threshold change, no gate re-run, no `B_hard` rewrite, no `T1-EID.json`
  re-freeze, no rebuild of `kapso_t1/tree`. Every one of those is a write into a frozen
  artifact or another workstream's directory, and the brief says report.
* No campaign, no paid probe, no model call, no network request beyond the TCP connects my
  hostile candidate makes and the harness's own invocations.
* I did not touch `/home/ebt/kapso_ck/`, `/tmp/eve/`, the `adapdc-catalog-postgres-1`
  container, or any upstream runtime.
* I committed **only** `a0/verify/a1-final/**`.
