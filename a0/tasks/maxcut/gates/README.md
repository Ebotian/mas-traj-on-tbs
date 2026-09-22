# `gates/` — the pre-registered admissibility gate for the T1 max-cut task

Owner: the gate workstream of `a0/tasks/maxcut/`. Authority: `../INTERFACE.md`
(v1.1) plus the assignment that named this directory. Every interpretation this
directory had to make is in `DEVIATIONS.md`; the artifacts under test are in
`../positive_control/`.

## 1. The verdict, and the evidence for it

| gate | verdict | dev | eval |
|---|---|---|---|
| **Δ** — did the artifact improve anything? | **PASS** | mean `0.247942608` (need ≥ `0.03`), `4/4` families ≥ `0.02` | mean `0.238448095`, `4/4` |
| **ρ** — is there headroom left afterwards? | **FAIL** | median `0.158819629` (need ≥ `0.30`), `0/4` families | median `0.178715729`, `0/4` |
| **saturation NO-GO** — is the baseline already at the reference? | not triggered | baseline headroom median `0.384381172` (veto below `0.05`), min `0.257847534` | median `0.361056711`, min `0.280269058` |
| **task admissibility** | **`NOT_ADMISSIBLE`** | | |

The failing path is the **ρ gate**, and it fails on both sets, in every family,
and at every seed tried (§5). The Δ gate passes comfortably. In other words: the
positive control *does* improve the baseline — by a lot, `+0.248` of the edge
count on average — and that is exactly the problem. The PC closes **82.6 %** of
the distance from `b_i` to the reference target (mean of `(p_i−b_i)/(T_i−b_i)`,
`8192591197903591608341/9921038743642647741120`, identical to the value the
independent `../references/recompute_rho.py` computes from the same inputs:
`0.8257795790943124`).

Why that is fatal for the task rather than for the artifact: a substrate cannot
earn credit for "improving the algorithm" on instances where an injected
one-flip local search already sits at **94.3 %** of the target (median `p_i/T_i`,
dev; `93.7 %` on eval). The requirement `ρ ≥ 0.30` is equivalent to
`p_i ≤ 0.7·T_i + 0.3·b_i`, i.e. `p_i/T_i ≲ 0.885` at the measured baseline. The
artifact would have to be roughly twice as far from the target as it is.

This is not a measurement accident:

* `24/24` graphs scored `ok` in both candidates on both sets, `0` unscored —
  nothing is being silently dropped and nothing non-`ok` is folded in as `0`
  (§6 rule 5);
* both candidates are `determinism.identical: true` on every graph (§6 rule 4);
* the longest PC invocation observed was `472 ms` against `τ = 10 s`, and there
  were `0` timeouts, so no result is a budget artefact;
* no stratum of the frozen suite reaches a median `ρ` of `0.30`, on either set
  (best: `RR:d4` `0.287` dev / `0.258` eval; `ER:p080` `0.274` dev / `0.137`
  eval), so re-balancing the existing strata cannot rescue the gate (§2 records
  what was measured afterwards: re-drawing the suite does not work either, and a
  weaker positive control does);
* the ρ numbers agree exactly, graph by graph, with
  `../references/recompute_rho.py` run over the same E* Outcomes.

**Re-frozen three times on 2026-09-22, with no number moved.** Each time a
*dependency* changed, never a result: `E*` was fixed (`08281d21… → 4afff01f…`,
`DEVIATIONS.md` D-GATE-10), `θ` was derived instead of guessed (`τ 30 s → 10 s`,
D-GATE-4 / D-GATE-11), `references/targets.json` was revised underneath by its
owner (D-GATE-12), and `E*` moved again — `4afff01f… → dc6969ec…`, whose history
is D-GATE-15. The third re-freeze re-ran all 576 stored Outcomes, the 14 `values/`
documents built from them, and all 12 verdicts against the current evaluator.

**Identity lineage — read no digest out of its revision.** Every digest named
anywhere below is either current or marked **history** with the revision it
belongs to:

| artifact | digest | revision | status |
|---|---|---|---|
| `E*` | `08281d21e6e84a79dfebd895d7653b517c1e08e7ea8784fe485532dd5db59c4d` | `11f55bf0` | **history** — superseded |
| `E*` | `4afff01f8a73479b2cb548686b4ae31c50100699057d3fad512f7a6aabb4a23a` | `6dd717c2` | **history** — superseded |
| `E*` | `dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00` | `baf13884` | **current** |
| `gate_config.json` | `1ff12031562031c879c86e177c2a685a5508632f1ecbf409ff650661223a30a0` | `f9054e56` | **history** — superseded |
| `gate_config.json` | `171c23d89dd59e5c83868acff8526ab42b94e6d7b1fd37a7a3a04246a30c452f` | `b9dfb859` | **current** |
| `references/targets.json` | `0919d7a4b41455ce504678c615d6a266666b5767435a4e6061982c780470d79c` | `b9dfb859` | **current** |

No artifact from a superseded revision is retained. The only places those digests
still appear at all are the history sentences in this file and in `DEVIATIONS.md`,
and each says which revision it is about; `restamp_evidence.py` checks that
mechanically and fails the run if an unlabelled one is found.

Two instruments, one rule — an identity field may move, a decision field may not:

| instrument | records | differing | identity leaves | decision leaves | verdict |
|---|---|---|---|---|---|
| `refreeze.evidence.json` — 12 verdicts | 12/12 | 1 leaf each | `evaluator_source_sha256` | **0** | `CLEAN` |
| `restamp.evidence.json` — 576 Outcomes | 576/576 | 6 leaves each | the six stamps below | **0** | `CLEAN` |

The six are `evaluator_source_sha256`, `canonical_digest`, and the four
`candidate_graph_*` fields of the redacted candidate view `baf13884` introduced.
The earlier two re-freezes' combined diff (5 identity leaves, 0 decision leaves)
is recorded in D-GATE-11. This is the point of calling it a re-freeze rather than
a drift: the artifacts that produced the earlier digits no longer exist, every
digit is the same, and the difference is machine-checked rather than asserted.

**The gate is satisfiable, and the decision it needs is not mine to make.** The
same frozen runner, pointed at a weaker positive control (`--pc
../positive_control/variants/pc_exchange_k10`), returns `ADMISSIBLE` on dev *and*
eval with both bars cleared by ≥ 2×. Whether the contract should call that
artifact `PC_i` is a **contract revision**, and `REVISION-PROPOSAL.md` is the
document that puts the measured curve, the posterior-freedom declaration and the
re-freeze checklist in front of whoever owns it. Nothing is adopted: the default
run still evaluates the contract's `PC_i` and still says `NOT_ADMISSIBLE`.

## 2. The pre-registered branch: what to change, and what that re-freezes

Not relaxing the gate. The three parts of the gate and their thresholds live in
`gate_config.json`, which is frozen *before* execution and whose sha256 is
recorded inside every verdict — so "the gate was not moved" is checkable, not
asserted. (Its current digest is `171c23d8…`; the verdicts issued before the `θ`
revision carry the earlier config `1ff12031…`, and the only difference between
those two config revisions is `θ`, which the same verdicts record. No threshold
changed. This paragraph used to name `79a27789…` as the current digest — no
revision of `gate_config.json` ever had that digest; corrected under D-GATE-15.)

>> **This section is superseded for the *choice of lever*, and kept for the
>> record.** It proposed re-drawing two strata at larger `n`. That lever was then
>> measured by another workstream and **ruled out**: `ρ` is flat in `n` for
>> `ER:p080` (`0.1768 → 0.1338` over `n = 128 → 1024`), `RR:d4` gains only
>> `≈0.03` of `ρ` at 8× the size against an instance-to-instance swing of `≈0.10`,
>> and at `n ≥ 512` the frozen PC itself exceeds `τ` (`redesign/LEVERS.md` §3, §6).
>> The lever that was measured to work is a weaker-but-still-published positive
>> control, and the decision it needs is written up in
>> **`REVISION-PROPOSAL.md`**. The re-freeze checklist at the end of this section
>> still applies, and `REVISION-PROPOSAL.md` §8 supersedes it in detail.

**Which knob is wrong.** Write the gate as a product of two measured factors:

    ρ_i ≥ 0.30   ⟺   (T_i − p_i)/T_i  ≥  0.3 · (T_i − b_i)/T_i
    (the PC's distance from the target)  (how far the baseline is from the target)

`ρ` is *increasing* in `T_i` (`∂ρ/∂T = (p_i−b_i)/(T_i−b_i)² > 0`), so headroom
survives only where a single 1-flip local search from a random start lands far
below a really good feasible solution, *relative to the baseline's own distance
from it*. Both factors are exact rationals already present in
`verdict.dev.json`'s rows (`T`, `p`, `b`), so this is a re-reading of the same
measurement, not a new one. How close the best instances come:

| graph | family:stratum | `(T−p)/T` | `(T−b)/T` | required `(T−p)/T` | |
|---|---|---|---|---|---|
| `G_dev_0010` | `RR:d4` | 0.1273 | 0.4364 | 0.1309 | short by 0.0036 |
| `G_dev_0009` | `RR:d4` | 0.1193 | 0.4220 | 0.1266 | short by 0.0073 |
| `G_dev_0006` | `ER:p080` | 0.0942 | 0.3233 | 0.0970 | short by 0.0028 |
| `G_dev_0014` | `BA:m2` | 0.0957 | 0.4163 | 0.1249 | short by 0.0292 |
| `G_eval_0003` | `ER:p050` | 0.0987 | 0.2993 | 0.0898 | **met** |
| `G_dev_0003` | `ER:p050` | 0.0740 | 0.3935 | 0.1180 | short by 0.0441 |

So the frozen suite is not wildly off — its best dev instances miss by ~0.004 of
`T` — but no dev graph clears the bar, and the *binding* factor is
`(T−p)/T`, the PC's relative distance from the target. That is a statement about
how hard the instance is for a seeded one-flip descent, not about how good the
reference is. (One eval graph, `G_eval_0003`, does clear it; eval numbers are
diagnostic here and decide nothing, so that is a direction to look at, not
evidence that the suite is already sufficient.)

The measured facts that bear on this:

| family:stratum | dev median ρ | eval median ρ |
|---|---|---|
| `RR:d4` | 0.287 | 0.258 |
| `ER:p080` | 0.274 | 0.137 |
| `ER:p050` | 0.205 | 0.235 |
| `ER:p030` | 0.151 | 0.209 |
| `BA:m2` / `BA:m3` / `BA:m5` | 0.176 / 0.141 / 0.152 | 0.194 / 0.181 / 0.107 |
| `RR:d3` / `RR:d5` | 0.139 / 0.136 | 0.132 / 0.145 |
| `Planted:k2sym` / `k3asym` / `k4sym` | 0.184 / 0.112 / 0.133 | 0.158 / 0.197 / 0.196 |

* **Sparser is the wrong direction.** The sparsest strata (`RR:d3`, `RR:d5`) have
  the *lowest* headroom, because sparse random graphs are nearly bipartite: the
  reference almost saturates `|E|` and a 1-flip descent also almost saturates it,
  so `(T−p)/T` is small *and* `(T−b)/T` is large. On dev, `ρ` rises monotonically
  with ER density (`p030` 0.151 → `p050` 0.205 → `p080` 0.274). On eval that
  trend does not hold, so **density is a plausible knob, not an established one.**
* **The suite has no size variance at all.** Every one of the 60 graphs is
  `n = 128`. That is the lever the data cannot speak to but the mechanism does:
  the reference is a 30 s run of a diverse, well-tuned ensemble, the PC is a
  single seeded descent, and a descent's quality relative to such an ensemble
  degrades as `n` grows — which is exactly `(T−p)/T` growing. *Inference, labelled
  as one:* raising `n` (or adding a size stratum) is the change most likely to
  lift `ρ` past `0.30`; it is not demonstrated here, because demonstrating it
  needs new graphs *and* new reference targets.

**Minimal proposed change** (coordinator's call; this directory only proposes):
re-draw **two** of the twelve strata and leave the other ten alone — the two
whose instances already come closest, `RR:d4` (short by 0.0036) and `ER:p080`
(short by 0.0028), and perturb them along the one axis the suite has never
varied: `n`. Concretely, draw those two strata at `n = 512` instead of `n = 128`,
keeping family, generator and density. Rationale: the binding factor is
`(T−p)/T`, the PC's relative distance from the target, and the only untested
lever for it here is instance size; changing density instead is not supported —
`RR` is non-monotone in degree (`d3` 0.139, `d4` 0.287, `d5` 0.136) and the ER
density trend that appears on dev does not reproduce on eval.

**What would have to be re-frozen** if any graph changes:

1. the affected `suite/<set>/*.json` files and `suite/manifest.json` (identity is
   the file's sha256, §2);
2. `references/targets.json` for those graphs — `R_i` must be re-run, and at
   larger `n` SCIP will mostly *not* certify, so `OPT_i` becomes `null` and `T_i`
   becomes a feasible lower bound (that is allowed, but it must be recorded, and
   `ρ` becomes an estimate);
3. the §7 timeout calibration, whose `p99` is derived from the *calibration* set
   — that set would need re-drawing too;
4. `C*(T1)`'s `conformance.expected.json` if `G_dev_0001` changes: rows `c01`,
   `c02`, `c03`, `c04`, `c05`, `c18`, `c20`, `c21` are graph-specific
   (`../conformance.report.json` records `cut_edges` per row for that graph).

**A cheaper design test for whoever drafts the replacement strata**, so this
does not have to be guessed again: `ρ ≥ 0.30` is equivalent to
`T_i ≥ (p_i − 0.3·b_i)/0.7`, and `ρ` is increasing in `T_i`, so *exhibiting any
feasible cut with value `V` that satisfies `(V−p_i)/(V−b_i) ≥ 0.30` certifies the
gate for that graph* whenever the graph's target is a proven optimum (`V ≤ OPT`
holds for every feasible `V`, so `ρ(T)` cannot be below `ρ(V)`). A candidate
stratum can therefore be screened with an ordinary feasible solver — no SCIP run
needed — and screened *before* the expensive reference pipeline is re-run. The
test is one-sided: it can certify a stratum, and it cannot reject one, because a
weak `V` only understates `ρ`.

## 3. Run it

One command, from the repository root, decides the gate and writes everything:

```bash
cd a0/tasks/maxcut && python3 gates/gate_runner.py
```

It prints the human table, writes `verdict.dev.json` (machine-readable, exact
rationals) and `verdict.dev.md`, caches one E* Outcome per (candidate, graph)
under `outcomes/dev/`, and exits `0` for `ADMISSIBLE`, `2` for `PENDING`,
`1` for `NOT_ADMISSIBLE`. Nothing outside this directory and
`../positive_control/` is written; the frozen suite is read-only.

**Any candidate can be the positive control** (`--pc <dir>`, D-GATE-14). Its
directory name selects its Outcome directory and its verdict file names, so the
contract PC's frozen file names are untouched and a variant lands beside them:

```bash
# the recommended truncation, on both sets (proposal only -- nothing is adopted)
python3 gates/gate_runner.py --set dev  --pc positive_control/variants/pc_exchange_k10
python3 gates/gate_runner.py --set eval --pc positive_control/variants/pc_exchange_k10

# the whole strength curve, both sets, per family, plus the redesign cross-check
python3 gates/strength_table.py
```

Full re-verification, including the eval diagnostic and the pin:

```bash
cd a0/tasks/maxcut
python3 positive_control/build.py --check
python3 positive_control/make_variants.py --check
sh positive_control/bootstrap_pin.sh
python3 positive_control/verify_pc_identity.py \
    --reference-python positive_control/.venv-pin/bin/python \
    --report positive_control/pc_identity_report.json
python3 gates/gate_runner.py                 # dev: the gate, exit 1
python3 gates/gate_runner.py --set eval      # diagnostic, separate files
python3 gates/seed_sensitivity.py --set dev  # is the verdict seed luck? no
python3 gates/tau_calibration.py             # derive tau per section 7 (10 s)
python3 gates/strength_table.py              # PC strength -> Delta/rho, both sets
python3 gates/refreeze_evidence.py --before HEAD   # re-freeze moved no decision
python3 gates/restamp_evidence.py --before HEAD    # ... and every stamp is current
python3 references/recompute_rho.py --targets references/targets.json \
    --baseline gates/values/dev.baseline.json \
    --positive-control gates/values/dev.positive-control.json \
    --out gates/rho_crosscheck.dev.json      # the sibling's own ρ implementation
```

`--force` re-runs E* instead of reusing cached Outcomes; without it, a cached
Outcome is re-run automatically when it was produced by a different E*, from
different candidate bytes, or at a different `θ` (D-GATE-13). The gate runner
needs only `python3`; the venv is needed only by the identity verification,
because `../positive_control/pc/solution.py` is self-contained.

## 4. How the measurement is taken

* **The evaluator is the authority.** This runner never computes a cut. For every
  (candidate, graph) it invokes `../e_star.py evaluate` — the harness-owned E*,
  `evaluator_source_sha256 dc6969ec…` — with the frozen
  `θ = (seed 1337, τ 10 s)`, and reads `cut_edges` out of the frozen Outcome. A
  candidate never reports its own score here either (§4, §5).
* **Exact arithmetic only.** `Δ`, `ρ`, the medians and the family means are
  `fractions.Fraction`; every decimal in the reports is a display field. No float
  decides anything, so there is no 1-ULP argument to have.
* **Unscored is not zero.** A graph whose `b_i` or `p_i` is not `ok` is excluded
  from every mean and listed in `unscored` (§6 rule 5). On these runs there were
  none.
* **Where the numbers are.** `verdict.<set>[.<pc>].json` — verdict, gates,
  per-graph rows, per-family and per-stratum reductions, artifact digests, the
  gate-config digest and the targets digest. The matching `.md` is the same as a
  table. `values/<set>.<candidate>.json` — the E* Outcomes in the shape
  `../references/recompute_rho.py` accepts, which is how the sibling
  implementation was used as a cross-check. `strength_table.{json,md}` — the
  curve across all six positive controls.

## 5. Diagnostics that guard the verdict

* **`seed_sensitivity.dev.json`** — the same measurement at seeds
  `1337, 0, 1, 2, 3`. Δ passes `4/4` families at every seed (means
  `0.228…0.253`); ρ fails at every seed (medians `0.152…0.207`). The failure is
  structural, not one seed's luck. The extra runs live in
  `outcomes/dev/s<seed>/` and the *decision* remains the single pre-registered
  seed.
* **`rho_crosscheck.dev.json`** — `../references/recompute_rho.py`, the sibling
  workstream's own implementation of `ρ`, over the same inputs. Every per-graph
  `ρ_exact` and `T_i` agrees; its mean headroom closed `0.8257795790943124`
  matches this runner's exact figure.
* **`tau_calibration.json`** — the §7 derivation of `θ.timeout_s` from the
  calibration set over the candidates the task runs: pooled p99 `133 ms` at the
  first measurement and `146–147 ms` when re-measured for the re-stamp (D-GATE-15
  — a timing on a host that read slower this time, not a decision).
  `10 × p99 ≤ 1.47 s`, so the 10 s floor binds either way and `τ = 10 s`
  (D-GATE-4, closed).
* **`strength_table.json`** — the PC strength curve for both sets with per-family
  detail, and the **re-verification of `redesign/`**: 6 variants, 60 fields,
  largest difference `4.98e-10` (float rendering of exact rationals), 0 gate-count
  mismatches.
* **`refreeze.evidence.json`** — every verdict diffed leaf by leaf against the
  previous freeze, identity fields and decision fields separated. Currently all
  12 verdicts, 1 identity leaf each, **0** decision leaves, `CLEAN`.
* **`restamp.evidence.json`** — the same question asked of the stored Outcomes,
  plus the stamp check the verdicts cannot make on their own: every one of the 924
  stamped records in all 602 documents names *this* `E*` (asked of
  `e_star.py digest`, not assumed); the 576 Outcomes each move 6 identity leaves
  and **0** decision leaves; every remaining mention of a superseded digest
  carries the revision it belongs to. Currently `CLEAN`.
* **`positive_control/pc_identity_report.json`** — the artifact under test really
  is the pinned NetworkX `one_exchange`, not an approximation of it (§1 of that
  README).

## 6. What this gate is not

It is a **task-admissibility pre-gate**, run by us, offline, before any campaign
exists. It is not the B0+ experiment (which asks whether a substrate can exploit
an *injected* artifact and needs the evaluator, budget enforcement and unseen
instances to answer that), it is not an arm of any campaign, and the PC's source
is never given to a searching agent — including the truncation variants, which
are the same NetworkX source with one line changed. No model spend was involved:
the CEq ledger (§8) is untouched because no model call was made.

It is also **not a chooser**. It measures six positive controls and reports which
pass; it does not decide which one the contract should use, and the default run
still evaluates the contract's own `PC_i`. That decision, its posterior-freedom
declaration and its re-freeze checklist are in `REVISION-PROPOSAL.md`.
