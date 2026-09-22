# `redesign/HISTORY.md` — the revision every artifact in this directory was measured at

Owner: the redesign/measurement workstream of `a0/tasks/maxcut/`. This file exists
for one reason: the artifacts under `out/` are stamped with an **evaluator digest
that is superseded**, and a reader must never mistake it for the one current at
`HEAD`. It is the labelled history record D-RD-9 points at.

**Nothing here re-measures anything.** The study's *conclusions* do not depend on
the digest — the gate thresholds, the exact-rational `Δ`/`ρ` reductions, the
reference recipe, the L2 comparison and every stored `cut_edges` are functions of
the graphs and the candidates, not of `E*`'s bytes. The levers were therefore
**not** re-run; this is a label, not a repair, and no number moves.

---

## 1. The superseded digest, and the revision it belongs to

All **276** Outcomes under `out/**` carry

```json
"evaluator_source_sha256": "08281d21e6e84a79dfebd895d7653b517c1e08e7ea8784fe485532dd5db59c4d"
```

which is `E*`'s composite source digest (`e_star.py`'s `evaluator_source_digest()`:
`sha256` of the canonical JSON of `[{name, bytes, sha256}]` over `e_star.py` and
`e_star_child.py`). It is the digest of those two files **as committed at
`11f55bf0`**:

| | composite `evaluator_source_sha256` | revision whose `E*` bytes these are | current from → until |
|---|---|---|---|
| **this study** | **`08281d21…`** | `11f55bf0` | `11f55bf0` (15:16:37) → `6dd717c2` (19:08:47) |
| next | `4afff01f…` | `6dd717c2` | `6dd717c2` → `baf13884` |
| current | `dc6969ec…` | `baf13884` | `baf13884` → `HEAD` |

```console
$ git show 11f55bf0:a0/tasks/maxcut/e_star.py       | sha256sum   # 670f02ee91885c10…
$ git show 11f55bf0:a0/tasks/maxcut/e_star_child.py | sha256sum   # 013f3e334dbde616…
$ git show 11f55bf0:a0/tasks/maxcut/e_star.py       | wc -c       # 43410
$ git show 11f55bf0:a0/tasks/maxcut/e_star_child.py | wc -c       # 15128
$ python3 ../e_star.py digest --value-only                        # dc6969ec… today
```

Every file under `out/` was written between **17:25:46 and 19:03:15 on
2026-09-22** — strictly inside the window in which `11f55bf0`'s `E*` bytes were the
current ones. So the whole directory is a measurement against `08281d21…`: the 276
Outcomes, the `l1_*.log` / `l1_scip*.log` / `l1_ub*.log` transcripts,
`l1_results.json`, `l1_values.json`, `l2_results.json`, `l2_candidates.json`,
`frozen_mirror.json`, and the untracked raw run state under `out/e-star-state/`
(excluded by the repository's `.gitignore`; it carries no
`evaluator_source_sha256` at all).

`canonical_digest` on those Outcomes is **not** stale in the same sense: it is each
Outcome's own self-digest over its own bytes, computed when it was written, and all
276 still recompute exactly. It is internally consistent — it merely folds in a
superseded `evaluator_source_sha256`.

## 2. Machine-readable form

`out/HISTORY.json` (`"schema": "a0.maxcut.redesign.history/v1"`) is the same
statement for a script: the superseded digest, the revision and per-file digests it
was measured from, the current digest, the per-directory counts, and all 276 paths
with their own `canonical_digest`. A scanner that finds `08281d21…` in a file under
`out/**` looks it up in `superseded_evaluator_source_sha256` and reads
`measured_against`, instead of comparing it with `e_star.py digest`.

Check the index is complete (every file that carries the digest is listed, and
nothing else is):

```python
import json, hashlib
from pathlib import Path
d = json.loads(Path("out/HISTORY.json").read_text())
sup = set(d["superseded_evaluator_source_sha256"])
found = sorted(str(f.relative_to("out")) for f in Path("out").rglob("*.outcome.json")
               if json.loads(f.read_text()).get("evaluator_source_sha256") in sup)
print("listed", len(d["files"]), "found", len(found),
      "equal", found == sorted(x["path"] for x in d["files"]))
print("path-list digest matches:",
      hashlib.sha256(("\n".join(found) + "\n").encode()).hexdigest() == d["files_sha256"])
```

## 3. Why the digests were not re-stamped, and what re-deriving would take

An Outcome's `canonical_digest` is a function of its own bytes, and `INTERFACE.md`
§5/§6 make the harness its author. *Editing* an Outcome to carry a new
`evaluator_source_sha256` would both falsify the measurement and break that
self-digest, so there is no re-stamp path — re-deriving the digests means
re-running the levers through `E*`:

* `gen/l1_eval.py` (the L1 `b_i`/`p_i` stage) and `gen/run_l2.py` (192 L2
  invocations) produce exactly these 276 files; `gen/run_all.sh` is the one command
  that drives both, plus the MQLib ensemble, the SCIP attempt and the tiered `U_i`
  stages whose results the tables reduce;
* the run is *resumable*, which is what let it be finished in stages — but resuming
  skips finished stages, and `FORCE=1` re-runs every `E*` measurement;
* D-RD-2's `p_i` depends on `candidates/exchange_opt`, because the pinned positive
  control itself `timeout`s at `n ≥ 512`.

**Where the current value is.** `dc6969ec…` (`a0/tasks/maxcut/e_star.py digest
--value-only`), frozen as `EID* = 7ce9e72f…` in `a0/a1/T1-EID.json`. The two later
`E*` revisions are the candidate-launch fix (`6dd717c2`) and the answer-leak
closure (`baf13884`); neither changes the max-cut arithmetic measured here — they
change what a *candidate* can reach, and the `cut_edges` these tables reduce were
already produced by harness-owned evaluation.

## 4. What this does not claim

* It does not claim the numbers here are measurements of the current `E*`. They are
  the measurements that were made, at the revision named above, and the
  gate-facing conclusions drawn from them are unaffected by the later `E*` edits.
* It does not claim the digests are recoverable from the repository. `E*` writes
  them; the only route to a `dc6969ec…` Outcome is another measurement run.
* It does not cover `instances/`, `candidates/`, `frozen_mirror/`, `lever_data.json`
  or `LEVERS.md` — none of them records an `evaluator_source_sha256`, so none of
  them can carry a stale one.
