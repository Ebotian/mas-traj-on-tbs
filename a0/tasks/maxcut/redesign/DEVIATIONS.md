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

---

## D-RD-2 — `p_i` at large `n` uses an efficient *equivalent* transliteration of the pinned `one_exchange`

The pinned `one_exchange` recomputes `cut_size` over **all** edges for **every**
candidate swap in **every** round, i.e. `O(rounds · n · m)`.  Measured through E*
at the frozen `θ = (seed 1337, τ = 30 s)` on the L1 sample:

| graph | n | \|E\| | pinned PC status |
|---|---|---|---|
| `L1_ERp080_n256_r0` | 256 | 2540 | `ok` |
| `L1_ERp080_n512_r0` | 512 | 10451 | **`timeout`** |

So at `n ≥ 512` the frozen PC does not finish inside the frozen budget, and
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
reproduce the frozen PC's `cut_edges` on **all 24 dev graphs** (0 differences),
and `gen/l1_eval.py` asserts equality on every L1 graph where the pin completes.

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
`n ∈ {128,256,512,1024}`, 2 graphs per cell, by importing the frozen generator
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

L2(a) (the current PC, for reference) is measured by running
`redesign/candidates/exchange_opt` through E* like every other variant, rather
than reading `gates/values/dev.positive-control.json`.  `gen/run_l2.py` then
**asserts** that this reproduces the frozen PC's `cut_edges` on all 24 dev graphs
(0 differences), and the headline numbers it produces (mean Δ `0.247942608`,
median ρ `0.158819629`) are digit-identical to `gates/verdict.dev.md`.  So the L2
comparison shares one instrument with the gate, and that is checked rather than
claimed.

---

## D-RD-8 — no model spend

The whole directory is local CPU.  No `deepseek-flash` call, no meter ledger
entry, no network.  The L1 reference pipeline reuses the already-built MQLib
binary at the pin (`/tmp/mcwork/MQLib/bin/MQLib`, sha256 `f761c326…`, the same
binary `references/build/PROVENANCE.json` names); it was not rebuilt and nothing
under `references/` was written.
