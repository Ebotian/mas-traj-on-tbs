# `a0/tasks/maxcut/references/` — reference targets `R_i`, `OPT_i`, `U_i`

Owner: the references workstream. Authority for every interface here is
`../INTERFACE.md`; this directory is the answer to its §9 requirement that each
frozen graph carry a **reference target**, and to the audit item
`a0/A1-CONTRACT-AUDIT.md` **B3** ("freeze a per-graph reference ceiling,
explicitly labelled as a reference value and not a proven optimum").

## 1. What is here

| path | what it is |
|---|---|
| `targets.json` | **the deliverable.** Per graph: `R`, its source `(heuristic, seed)`, all ties, `OPT`/`opt_certified`, `U` and the individual bounds behind it |
| `coverage.json` | **the budget ledger.** Per graph: which runs were scheduled, at what time limit, how many succeeded, plus the SCIP and upper-bound budgets. Derived from the artifacts, not asserted |
| `logs/runs/*.json` | one record per (graph, heuristic, seed): recomputed integer cut, partition sha256, wall time, MQLib's own reported value, exit code |
| `witnesses/commitments.json` | **what remains of the witnesses**: per witness the graph id, run id, sha256 of the file bytes, sha256 of the canonical bytes and the recomputed cut. The vectors themselves are not in this repository — see §7 |
| `witnesses/fs_policy.json` | answer stores outside this repository that the evaluator masks from a candidate; found by `leak-proof/run_leak_probe.py` |
| `leak-proof/` | the hostile candidate, the probe that runs it in three environments, and its recorded output |
| `logs_topup/*` | the same per-run records for the 300 s top-up pass on the graphs SCIP did not certify (`tools/resume.sh` step 4) |
| `ub/*.json` | the rigorous upper-bound computation per graph: spectral, SDP dual, Burer–Monteiro certificate, and the parameters they were run at |
| `scip/*.json`, `scip/*.scip.log`, `scip/*.lp` | the exact-certification attempt (SCIP) and its MIP model |
| `recompute_rho.py` | computes `rho_i = (T_i - p_i)/(T_i - b_i)` exactly, from a baseline and a positive-control value |
| `build/PROVENANCE.json`, `build/build_mqlib.sh` | clone URL, commit pin, build command, patches, binary/source digests |
| `tools/` | the generator, driver, independent evaluator, upper bounds, coverage builder, the targets builder, and `seal_witnesses.py` |
| `tools/resume.sh` | the interrupt-safe driver: reruns only what is missing (see §6) |
| `smoke/` | five self-generated canonical graphs used to validate the pipeline before the suite existed |

## 2. The three numbers, and what they are allowed to mean

* `R_i` — the best **feasible** cut found by the ensemble. It is a **lower bound
  on the optimum**. It is never an upper bound, and it is never called optimal
  unless §4 below certifies it.
* `OPT_i` — the value of `R_i`, but only when an upper bound closes the gap
  (`U_i == R_i`). Otherwise `null`. `targets.json` carries `opt_certified` so a
  consumer cannot accidentally read an uncertified value as optimal.
* `U_i` — the smallest of the rigorous upper bounds actually computed:
  the spectral (eigenvalue) bound, a Delorme–Poljak / Goerdel dual bound from a
  Polyak subgradient run, and a Burer–Monteiro dual certificate. Each is valid
  for *every* diagonal vector `y` after the shift `c = max(0, -lambda_min(A + Diag(y)))`,
  so the only numerical exposure is the eigen-decomposition itself; a safety
  margin is added and `U_i >= R_i` is checked for every graph (a violation is
  reported as `U_consistent_with_R: false` rather than hidden).

**The candidate never reports its own score.** MQLib prints an objective; that
number is recorded as `mqlib_reported_objective` for cross-checking only. The
authoritative integer is recomputed from `graph.json` + `partition.json` by
`tools/verify_partition.py`, independently of MQLib. All comparisons and the
`R_i` maximum are integer operations; `cut_fraction` is a display field.

## 3. The ensemble

Six MQLib Max-Cut heuristics × five seeds × 30 s per run:

```
BURER2002  FESTA2002GPR  FESTA2002VNSPR  DUARTE2005  LAGUNA2009HCE  DESOUSA2013
seeds = 1337, 2718, 31415, 4242, 65521
```

All six names are the registry names in MQLib's own `HeuristicFactory`
(`src/heuristics/heuristic_factory.cpp`), verified with `MQLib -l`.
Runs are executed 11-way parallel (`--jobs 11` on a 12-thread box) and every
run is written to disk before it counts, so the driver is resumable: rerunning
skips any triple whose record already exists with `status: ok`.

**Nothing was reduced.** All 60 graphs (the 48 dev+eval the assignment requires,
plus the 12 calibration graphs) got the full `6 x 5 x 30 s = 30 runs`. The
12 calibration graphs are carried for completeness only; they are never used for
any selection (`INTERFACE.md` §9), and `targets.json` labels every entry with its
`role` so a consumer can filter them out in one line.

**Top-up pass.** The 18 graphs whose optimality SCIP did not certify additionally
received 6 runs of **120 s** each — a 4x budget, from the three heuristics that
reach `R_i` on every graph, two seeds (`tools/resume.sh` step 4). Those records
live in `logs_topup/`, never overwriting the 30 s records in `logs/`, and
`targets.json` folds them into the same `R_i` maximum while recording
`budgets_applied_s`, `largest_budget_that_reached_R_s` and `R_from_topup` per
graph. The purpose is not to raise `R_i` — it is to test the 30 s result.

**Measured outcome: no improvement on any of the 18 graphs.** The top-up's best
value equalled `R_i` exactly on all 18, and never exceeded it. On several graphs
the 120 s run produced a *byte-identical* partition to the 30 s run (same
`partition_sha256`, e.g. `G_dev_0005`), i.e. MQLib had already converged well
inside 30 s and the extra budget changed nothing but the wall clock. That is the
strongest statement available for those graphs short of a certificate: 31 runs
reach `R_i` (25 of the 30 short runs, from 5 distinct heuristics, plus all 6 of
the long ones) and not one run in either budget regime beats it.

`DESOUSA2013` never reaches `R_i` on any of the 60 graphs — it is systematically
the weakest of the six (e.g. 300 vs. `R_i = 338` on `G_dev_0003`, a certified
optimum). That is a property of the heuristic, not a harness bug: its runs are
`ok` and recomputed, its own reported objective always matches the recomputation
(`mqlib_reported_matches_recomputed: true`), and a weak member of a
maximum-taking ensemble is harmless. It is called out here because the constant
`5/6 heuristics reach R_i` pattern would otherwise look suspicious.

## 4. Certification status — read this before using `OPT_i`

`OPT_i` is non-null only where it was actually certified. Certification used
**SCIP 10.0.3 / SoPlex 8.0.3**, already installed offline at `/usr/bin/scip`,
with the standard edge MIP plus the triangle odd-cycle inequalities
`y_uv + y_vw + y_wu <= 2`, 120 s per graph.

**Measured outcome (60/60 graphs attempted, no graph skipped):**

| | certified `OPT_i` | not certified (`OPT_i = null`) |
|---|---|---|
| dev (24) | 16 | 8 |
| eval (24) | 17 | 7 |
| calibration (12) | 9 | 3 |
| **total (60)** | **42** | **18** |

On the 18 uncertified graphs the remaining gap `U_i - R_i` is 10–26 edges
(3–8 % of `R_i`); see `targets.json` per graph and `coverage.json` for the
budget each received.

**Why more SCIP time is not the fix — measured, not assumed.** On those 18
graphs SCIP's own best feasible solution never beat `R_i`, and on 7 of them
(`C_0003`, `G_dev_0005`, `G_dev_0006`, `G_dev_0024`, `G_eval_0005`,
`G_eval_0006`, `G_eval_0017`) it was strictly *worse* (`G_dev_0005`: SCIP 490
vs. `R_i` 499). The residual gap is therefore entirely a weak **dual** bound,
not a missing primal solution, so feeding SCIP a warm start or more time on this
formulation cannot close it. Closing it would need a stronger relaxation (cut
generation beyond triangles, or an SDP-based branch and bound), which is out of
scope for a reference table. `OPT_i` is accordingly `null` on those 18 and
`opt_certified` is `false`.

Two failure modes are reported separately and never conflated:

* `opt_certified: false, OPT: null, U: <number>` — the graph is **not** certified;
  `R_i` is a feasible value and a lower bound on the optimum, and
  `U_i - R_i` is the verified remaining gap.
* `opt_certified: false, U: null, U_consistent_with_R: false` — the bound
  computation itself failed; this is a bug report, not a result. **This case does
  not occur in the current `targets.json`**: every one of the 60 graphs has a
  numeric `U_i` with `U_i >= R_i` (checked for all 60, zero violations).

An uncertified `R_i` is still fit for purpose as the `rho_i` denominator, but
`rho_i` is then an estimate, and its **bias direction is decidable**. With
`f(T) = (T-p)/(T-b)` we have `f'(T) = (p-b)/(T-b)^2`, so substituting `R_i` for
the true `T_i` makes the reported `rho_i` a **lower bound** on the true value
exactly when `p_i > b_i` (the positive control beats the baseline — the normal
case), and an **upper bound** when `p_i < b_i`. `recompute_rho.py` decides this
per graph and emits `rho_bias_direction`; it never leaves the reader guessing.

Because `U_i` brackets the optimum too, the true `rho_i` is bracketed as well:
`recompute_rho.py` emits `rho_interval_from_U` (`[f(R_i), f(U_i)]`, sorted) on
every uncertified graph, so a consumer can see how much the missing certificate
could move the number instead of being told to assume it does not move at all.
Consumers must also read `T_is_lower_bound_on_opt`, emitted per graph.

## 5. Computing `rho`

```
rho_i = (T_i - p_i) / (T_i - b_i)
```

`b_i` = baseline value, `p_i` = positive-control value. Because all three are
integers the ratio is exact; `recompute_rho.py` uses `fractions.Fraction`
throughout and prints a decimal only as a display field.

```
python3 recompute_rho.py --targets targets.json \
    --baseline  <baseline.json>  --positive-control <pc.json>  --out rho.json
```

`--baseline` and `--positive-control` accept a plain `{graph_id: cut_edges}`
map, an `{"outcomes": [...]}` document in the `a0.maxcut.outcome/v1` shape of
`INTERFACE.md` §5, or a bare list of such outcomes. A record whose `status` is
not `ok` is treated as **unscored, never as 0** (§6 rule 5), and a graph where
`T_i == b_i` is reported as saturated-at-baseline rather than as a divide by
zero.

## 6. Reproducing this directory

Everything below is local computation. No model calls, no spend, no network
except the one clone in step 1.

**Resume after an interruption** — the one command to use if anything below was
cut short. Every stage skips what is already on disk, so re-running is cheap and
never restarts finished work:

```bash
cd a0/tasks/maxcut/references
bash tools/resume.sh /tmp/mcwork        # tops up ensemble, top-up, SCIP, bounds, table
```

Full rebuild from nothing:

```bash
cd a0/tasks/maxcut/references
bash tools/reproduce.sh            # build -> ensemble -> SCIP -> targets.json
```

Step by step, if you want to run them yourself:

```bash
# 1. build MQLib at the pin (clone URL and commit in build/PROVENANCE.json)
bash build/build_mqlib.sh /tmp/mcwork
sha256sum /tmp/mcwork/MQLib/bin/MQLib     # expect f761c326b68decc7...

# 2. the ensemble over every graph of the frozen suite
python3 tools/run_ensemble.py --binary /tmp/mcwork/MQLib/bin/MQLib \
    --manifest ../suite/manifest.json --roles dev eval calibration \
    --outdir logs --scratch /tmp/mcwork/inputs --jobs 11 --time-limit 30

# 3. the certification attempt
python3 tools/scip_maxcut.py --manifest ../suite/manifest.json \
    --roles dev eval calibration --out scip --limit 120 --jobs 11

# 4. rigorous upper bounds, in parallel, cached per graph
python3 tools/ub_parallel.py --manifest ../suite/manifest.json \
    --targets targets.json --out ub --jobs 11 --iters 4000

# 5. the reference table
python3 tools/build_targets.py --logs logs --manifest ../suite/manifest.json \
    --out targets.json --ub-cache ub

# 6. the budget ledger
python3 tools/build_coverage.py --manifest ../suite/manifest.json --out coverage.json
```

To re-verify a single `R_i` from scratch, without trusting the driver, you need
that witness's bytes. They are not in this repository (§7); the check that *is*
available from the repository alone is the commitment check, and it is part of
`tools/verify_targets.py`. With a retained copy of the removed tree:

```bash
python3 tools/verify_targets.py --witnesses /path/to/retained-copy   # full recomputation
python3 tools/seal_witnesses.py verify --corpus /path/to/retained-copy
```

## 7. Handling warning — and what was done about it

`logs/partitions/**`, `logs/raw/**` and `scip/*` contained **near-optimal
partitions of eval graphs**: the answer to the hold-out, one file per graph, at a
predictable path. Keeping them was a deliberate choice (a reference value that
cannot be re-verified is not evidence) and it was wrong: the independent verifier
scored exactly `R = OPT = 217` on `G_eval_0001` by copying
`logs/partitions/G_eval_0001__*.partition.json`, through `e_star.py` *and*
through `a0/a1/eval_service.py` (`a0/verify/a1-testbed/REPORT.md` §2c).

The vectors were therefore removed from the repository and replaced by
commitments (`tools/seal_witnesses.py`, `DEVIATIONS.md` D9):

* `witnesses/commitments.json` — per witness: graph id, run id, file sha256,
  canonical-bytes sha256, recomputed cut, `|E|`;
* the per-run records under `logs/runs/**` and `logs_topup/runs/**` still commit
  to each run's `partition_sha256`, `raw_stdout_sha256` and recomputed
  `cut_edges`, so `R = max over run records` is still checkable from the repo;
* `tools/verify_targets.py` re-verifies from bytes when a corpus is supplied, and
  otherwise checks every witness against its commitment.

Two residuals, stated in numbers rather than adjectives:

1. **Git history.** The bytes were committed before the removal, so
   `git show <rev>:<path_removed>` returns them until the history is rewritten
   (`git filter-repo`, a coordinator decision). The evaluator masks `.git` and
   this directory from the candidate for exactly that reason (D-T1-12 in
   `../DEVIATIONS.md`), and `leak-proof/run_leak_probe.py` measures the attempt.
2. **Copies outside this directory.** `witnesses/fs_policy.json` lists the ones
   the leak probe found — `/tmp/mcwork/scip_test2/G_dev_0001.partition.json`
   scores 224 = R = OPT, and `det_*.txt` there carries MQLib `Solution:` lines
   for `G_dev_0003` — plus the fact that the credential file `~/gptapi.md` is
   readable by the same uid (that one is the model-budget lane's, not this
   directory's). `e_star.py` masks every path in that file; deleting them is
   better than masking them.

## 8. Headline numbers to compare against

From the current `targets.json` (60 graphs, all `n = 128`, 15 per family):

| quantity | value |
|---|---|
| ensemble runs recorded `ok` | **1800 / 1800** (60 graphs x 30) |
| aggregate `R` | `sum R_i = 18495` over `sum |E_i| = 23868`, i.e. **685/884** |
| dev subset | 24 graphs, `sum R = 7472` over `sum |E| = 9654` (3736/4827) |
| eval subset | 24 graphs, `sum R = 7406` over `sum |E| = 9563` |
| certified `OPT_i` | **42 / 60** (dev 16/24, eval 17/24, calibration 9/12) |
| uncertified graphs, remaining gap `U_i - R_i` | min 10, max 26, mean 19.7 edges (3-8 %) |
| graphs where `U_i < R_i` (a bound bug) | **0** |
| graphs missing a `U_i` | **0** |
| re-verification of `R_i` | **60/60 PASS**, 1499 tie-witness partitions recomputed from bytes before the seal (`tools/verify_targets.py`); the seal keeps the commitments, see §7 |
| `R_i` source heuristic | `BURER2002` on all 60 (25 of 30 runs per graph tie at `R_i`) |
| top-up runs at 4x budget that beat `R_i` | **0 / 108** |

`DESOUSA2013` contributes to none of the 60 maxima (see §3); the other five
heuristics each reach `R_i` on all 18 uncertified graphs.

The one command that decides whether to believe the table:

```bash
python3 tools/verify_targets.py --quiet    # -> PASS, exit 0
```

It prints how many witnesses were recomputed from bytes and how many were checked
against their sealed commitment, so the two are not confused (§7).

To see what a candidate can reach from inside its sandbox, and what it gets if it
can reach the answer store, run the probe (it does not spend anything):

```bash
python3 leak-proof/run_leak_probe.py --modes prefix,open,fixed
```
