# `redesign/` deviations and interpretation notes

Owner: the redesign/measurement workstream of `a0/tasks/maxcut/`. Authority:
`../INTERFACE.md` (v1.1) and the assignment that named this directory.  Each
entry names what was left open or had to be worked around, what was chosen, and
why.  No upstream runtime, no frozen artifact and no other workstream's file was
modified.  Nothing here changes the suite, the gate thresholds, or any target.

---

## D-RD-1 — the frozen candidates are currently un-evaluable by E*; a byte-identical mirror is used

**What is wrong.** `positive_control/{baseline,pc}/solution.py` are mode `0755`
and start with `#!` — but they were chmod'ed **after** the gate ran.  Evidence:

```
$ stat -c '%n mode=%a ctime=%z' positive_control/pc/solution.py
positive_control/pc/solution.py mode=755 ctime=2026-09-22 17:08:08
$ stat -c '%n ctime=%z' gates/outcomes/dev/pc/G_dev_0001.outcome.json
gates/outcomes/dev/pc/G_dev_0001.outcome.json ctime=2026-09-22 17:03:07
```

`e_star_child.resolve_candidate` (lines 188-192) then selects `exec_prefix = []`
("run the entry directly, it is executable and has a shebang"), while
`e_star.stage_candidate` copies the staged entry with `Path.write_bytes`, which
does **not** preserve the executable bit.  The spawn fails:

```
$ python3 e_star.py evaluate --candidate positive_control/baseline \
      --graph suite/dev/G_dev_0001.json --seed 1337 --timeout 30 --out /tmp/o.json
e_star: status=error failure=candidate_entry_failed:
  PermissionError: [Errno 13] Permission denied: .../candidates/6bfd919ed73c49db/solution.py
```

So today `gates/gate_runner.py --force` cannot reproduce its own verdict, and no
workstream can evaluate the two frozen candidates through E* as they stand.

**What was done.** `gen/make_frozen_mirror.py` copies both candidate directories
into `redesign/frozen_mirror/{baseline,pc}/` with **byte-identical contents** and
mode `0644`.  Content is the identity (`INTERFACE.md` §2 is sha256 of the bytes;
the file mode is not part of it), and the script asserts the mirror's
`candidate_source_sha256` equals the digest recorded in the gate's own Outcomes:

```
baseline: 6bfd919ed73c49dbb27fd2eb8f1f7224fac131773d7c8e1aa1f8b6ed09b24d97  (== frozen)
pc:       d3c12b54999415a199bdcd1c9bfed715a8e28147014a14083fe0bd502be3987f  (== frozen)
```

Every Outcome produced here from the mirror therefore carries the same
`candidate_source_sha256` as the gate's, and is directly comparable.  The frozen
files themselves were not touched, and the mirror is not a fix to E* — it is a
workaround recorded so the coordinator can decide whether to revert the chmod or
to make `stage_candidate` preserve the mode.

**Not done, deliberately:** no change to `e_star_child.py`, `e_star.py`, or the
frozen candidate files.  This is another workstream's artifact.

**Status update, 2026-09-23 — the finding above is not rewritten.** Commit
`6dd717c2` ("the candidate launch must be a function of the candidate's bytes
alone") removed the mode-bit inference.  `e_star_child.resolve_candidate` now
launches every candidate as `[sys.executable, <staged entry>, …]` unless the
candidate declares `exec`, and `stage_candidate` copies source file modes only for
a declared `exec: []`.  The two frozen candidates declare no `exec`, so the
`PermissionError` above no longer occurs: `python3 e_star.py evaluate --candidate
positive_control/pc --graph suite/dev/G_dev_0001.json --seed 1337 --timeout 30
--out /tmp/o.json` returns `status=ok`, exit 0 (checked 2026-09-23 against `E*` at
`dc6969ec…`).  The words "today" and "as they stand" above describe the state when
this entry was written.  The mirror workaround was necessary then, and its
Outcomes stay as measured.

---

## D-RD-2 — `p_i` at large `n` uses an efficient *equivalent* transliteration of the pinned `one_exchange`

The pinned `one_exchange` recomputes `cut_size` over **all** edges for **every**
candidate swap in **every** round, i.e. `O(rounds · n · m)`.  Measured through E*
at the frozen `θ = (seed 1337, τ = 30 s)` on the L1 sample:

| graph | n | \|E\| | pinned PC status |
|---|---|---|---|
| `L1_ERp080_n256_r0` | 256 | 2540 | `ok` |
| `L1_RRd4_n512_r0` | 512 | 1024 | `ok` |
| `L1_ERp080_n512_r0` (×4) | 512 | 10451 | **`timeout`** |
| `L1_RRd4_n1024_r0/r1/r2` | 1024 | 2048 | **`timeout`** (r3 `ok`) |
| `L1_ERp080_n1024_r0…r3` | 1024 | ~41800 | **`timeout`** |

So beyond `n = 512` on the denser stratum, and mostly at `n = 1024` on the
sparser one, the superseded control does not finish inside the frozen budget, and
`INTERFACE.md` §6 rule 5 forbids folding a `timeout` in as anything.  The value
`p_i` in `out/l1_values.json` is therefore the local optimum of the **same
algorithm**, obtained from `redesign/candidates/exchange_opt/solution.py`, which
computes each node's swap gain from the adjacency list in `O(m)` per round
instead of `O(n·m)`.  It is the *same map* on (graph, seed):

* same starting partition `b_i = splitmix64(seed ^ 0xA5A5A5A5A5A5A5A5)`;
* same `random.Random(seed)` shuffle order (so the same first maximiser
  tie-break);
* same accept-only-if-improving loop.

Equality is asserted, not assumed: `gen/run_l2.py` requires `exchange_opt` to
reproduce the superseded control's `cut_edges` on **all 24 dev graphs** (0
differences), and `gen/l1_eval.py` asserts equality on every L1 graph where the
pin completes.

**Budget, labelled.**  The transliteration is given `τ = 900 s` (recorded in each
Outcome's `theta.timeout_s`), because the question is the value of the converged
1-exchange descent, not the value reachable in 30 s.  A *larger* `p` only makes
`ρ = (T−p)/(T−b)` *smaller*, so this choice is conservative for the headroom
measurement.  The pinned PC's own `wall_ms`/timeout is reported alongside so the
cost difference is visible rather than hidden.

---

## D-RD-3 — what the "published greedy construction" (L2c) is

The assignment defines it parenthetically: "assign each node to maximise the cut
incrementally".  Implemented as the classic greedy: nodes are visited in a
seeded `random.Random(seed)` order, and each node joins the side that maximises
its cut contribution against already-placed neighbours (ties → side 0).  `O(n+m)`,
deterministic given (graph, seed).  It is the textbook greedy Max-Cut
construction (Sahni & Gonzalez 1976 and every approximation-algorithms text that
repeats it); it is *not* taken from NetworkX, which ships no plain greedy.

`randomized_partitioning` (L2d) is the pinned NetworkX function transcribed from
`positive_control/pc/pinned/networkx_maxcut_b69beb2c.py`: an i.i.d. `p = 1/2`
side per node, no search.  It is the floor that should fail Δ.

---

## D-RD-4 — the L1 target at larger `n` is an uncertified heuristic incumbent, and `ρ` is bracketed

The reference recipe is the project's own (`references/README.md` §3: six MQLib
heuristics × five seeds × 30 s, `R_i` = max recomputed cut; SCIP 120 s where it
certifies).  At `n ≥ 256` SCIP does not certify, so `T_i = R_i` is a feasible
value and a **lower bound** on the optimum, `U_i` is the rigorous upper bound
that brackets it, and `OPT_i` is `null`.  `targets.json` in this directory is
built by the project's `references/tools/build_targets.py` (`--skip-ub`) and the
`U_i` records from `gen/l1_ub.py` are merged exactly as `build_targets.read_ub`
and its OPT determination do (certified iff `U_i == R_i`).

Because `ρ(T) = (T−p)/(T−b)` has `∂ρ/∂T = (p−b)/(T−b)²`, with `p > b` (always
true here) an uncertified `R_i ≤ OPT ≤ U_i` makes the reported `ρ(R)` a **lower
bound** on the true headroom and `ρ(U)` an upper bound.  Both are reported per
graph as `rho_R` / `rho_hi`, plus `T_is_lower_bound_on_opt`.  The verdict for L1
is read off `rho_R` (the gate's own definition, `T_i = OPT_i if certified else
R_i`), with the bracket shown beside it.

---

## D-RD-5 — the L1 sample is generated, not part of the frozen suite

The frozen suite has no size variance (60 graphs, all `n = 128`).  `gen/
gen_l1_instances.py` draws the two strata `RR:d4` and `ER:p080` at
`n ∈ {128,256,512,1024}` — 2 graphs per cell at `n = 128` (matching the frozen
suite's own 2-per-stratum density) and 4 per cell at `n ≥ 256`, 28 graphs in
all — by importing the frozen generator
module **read-only** (`generators/maxcut_suite.py`: same SplitMix64 stream, same
generators, same canonical writer, `INTERFACE.md` §2).  A distinct generation
role (`redesign-L1`) and distinct graph ids (`L1_*`) keep the streams disjoint
from the frozen suite's, so no L1 graph can collide with a frozen one.  The
instances live only under `redesign/instances/`.  `verify`-style regeneration is
exposed as `gen_l1_instances.py --check` (re-derives every graph and the manifest
and requires byte-identical output).

---

## D-RD-6 — the upper-bound budget is tiered by `n`, and a tier is a label, not a claim

`U_i` needs the project's spectral + SDP-dual + Burer–Monteiro bounds.  One
SDP-dual iteration costs one `n×n` eigendecomposition (`references/tools/
upper_bounds.py`), so the project's `iters = 4000` is affordable at `n ≤ 256` but
not at `n = 1024` (measured: `eigvalsh` 0.28 s at `n = 1024` → ~19 min/graph).
`gen/l1_ub.py` therefore uses:

| n | iters | bm_iters | label |
|---|---|---|---|
| ≤ 256 | 4000 | 3000 | project recipe |
| 512 | 1500 | 1500 | capped |
| 1024 | 400 | 600 | capped |

Every iterate of the subgradient is a *valid* bound, so a reduced count only
weakened the bracket; it did not make it wrong.  The per-graph parameters are
recorded in `instances/ub/<graph_id>.json` and copied into `targets.json`.

---

## D-RD-7 — L2's reference row is measured, not copied

L2(a) (the superseded control, for reference) is measured by running
`redesign/candidates/exchange_opt` through E* like every other variant, rather
than reading `gates/values/dev.positive-control.json` — the frozen value file of
the superseded control, `positive_control/pc/`.  `gen/run_l2.py` then **asserts**
that this reproduces that control's `cut_edges` on all 24 dev graphs
(0 differences), and the headline numbers it produces (mean Δ `0.247942608`,
median ρ `0.158819629`) are digit-identical to that control's verdict,
`gates/verdict.dev.md`.  So the L2
comparison shares one instrument with the gate, and that is checked rather than
claimed.

---

## D-RD-8 — no model spend

The whole directory is local CPU.  No `deepseek-flash` call, no meter ledger
entry, no network.  The L1 reference pipeline reuses the already-built MQLib
binary at the pin (`/tmp/mcwork/MQLib/bin/MQLib`, sha256 `f761c326…`, the same
binary `references/build/PROVENANCE.json` names); it was not rebuilt and nothing
under `references/` was written.

---

## D-RD-9 — every artifact under `out/` is stamped with a **superseded** `E*` digest, and is labelled as history rather than re-measured

**What is wrong with the artifacts as they stand.** All 276 Outcomes under
`out/**` carry `evaluator_source_sha256 = 08281d21…`. That is `E*`'s composite
source digest at **`11f55bf0`**, not at `HEAD` — it was superseded twice since
(`6dd717c2` → `4afff01f…`, `baf13884` → `dc6969ec…`). Nothing in this directory
said so, so a reader (or a scan) could take `08281d21…` for the current evaluator.
This entry, `HISTORY.md` and the machine-readable `out/HISTORY.json` are the label.

**Why the artifacts were not re-stamped.** The levers were measured against the
revision current at the time, and their *conclusions* do not depend on the digest:
the gate thresholds, the exact-rational `Δ`/`ρ` reductions, the reference recipe
and every stored `cut_edges` are functions of the graphs and the candidates. An
Outcome's `canonical_digest` is a self-digest over its own bytes and
`INTERFACE.md` §5/§6 make the harness its author, so editing one to carry a new
`evaluator_source_sha256` would falsify the measurement *and* break its
self-digest. Re-deriving the digests means re-running `gen/l1_eval.py` and
`gen/run_l2.py` — i.e. re-running the lever study — which the assignment forbids
and which would move no conclusion. So: **the digests stay as measured, and the
directory says which revision they belong to** (`HISTORY.md` §1–§3).

**What was added.**
* `HISTORY.md` — the labelled record: the superseded digest, the revision
  (`11f55bf0`, `E*` = `e_star.py 670f02ee…` + `e_star_child.py 013f3e33…`), the
  window in which the whole directory was produced, why re-deriving is a re-run,
  and where the current value (`dc6969ec…`) is.
* `out/HISTORY.json` (`"schema": "a0.maxcut.redesign.history/v1"`) — the
  machine-readable marker an automated scan can read: the superseded digest list,
  `measured_against`, the current digest, the per-directory counts and all 276
  paths with their own `canonical_digest`. Its file list is exhaustive and
  anchored by `files_sha256`.

**Not claimed.** That the numbers here are measurements of the current `E*` (they
are the measurements that were made), nor that the digest is recoverable from the
repository (`E*` writes it). `out/e-star-state/` is untracked raw run state,
excluded by the repository's `.gitignore`; it carries no `evaluator_source_sha256`
and is left untouched.

---

## D-RD-10 — `PC_i` is the bounded variant since 2026-09-23, and this file's "PC" labels name the superseded control

**What changed upstream, not here.** On 2026-09-23 the contract's positive
control `PC_i` became `positive_control/variants/pc_exchange_k10/` — the same
pinned `one_exchange(G_i, initial_cut=b_i, seed=s_i)`, stopped after 10 accepted
improving swaps — on the strength curve this directory measured (L2, `LEVERS.md`
§2; the criterion is frozen in `gates/REVISION-PROPOSAL.md`, the decision in
`positive_control/PC-REVISION.md`).  `gates/gate_runner.py` `DEFAULT_PC` now points
at that directory, the adopted verdicts are
`gates/verdict.{dev,eval}.pc_exchange_k10.json` (`ADMISSIBLE`), and
`positive_control/pc/` is kept as history with its verdicts
`gates/verdict.{dev,eval}.json` (`NOT_ADMISSIBLE`).

**What it means for this file.** The unbounded local optimum at
`positive_control/pc/` — the reference row that D-RD-2 and D-RD-7 measured, and
that this file called "the current PC" or "the frozen PC" — is the **superseded**
control.  Every number in this directory is unchanged and correct for the control
it measured; none was recomputed.  D-RD-2 and D-RD-7 now name that control, and
D-RD-1 carries the 2026-09-23 status update on the `E*` launch fix (`6dd717c2`).

**Not changed by this entry.** No threshold, no suite byte, no `E*` byte and no
`gate_config.json` value.  Labels only.

