# a0/acceptance — A0.2 pre-registered expectations

Independently derived expected values and acceptance criteria for step A0.2
("does each runtime consume evaluation scores according to the selection semantics it
claims"). Derived from runtime source **before** any experiment was run, so the tests have a
pre-registered expectation that was not written by the adapter implementer.

## Files

| file | what it is |
| --- | --- |
| `DERIVATIONS.md` | the derivations, with `path:line` citations for every claim, the findings where the protocol or the source is suspect (§5), and the unresolved items (§7) |
| `expected_values.json` | machine-readable expected values. **Generated** by `simulate.py --emit-json`; do not hand-edit |
| `simulate.py` | the numerical cross-check. Executes the real EvE sampler classes and the real Loreley archive; runs the power analysis |
| `run_output.txt` | the exact stdout pasted into `DERIVATIONS.md` §6 |
| `ACCEPTANCE.md` | the A−1 / A0.1 / A0.2 pass checklist and the false-green traps |

## Requirements

Python 3 with `numpy`, `scipy`, `PyYAML`. Verified on Python 3.14.7 with numpy 2.5.3,
scipy 1.18.1, PyYAML 6.0.3. `optree` is **not** needed: `simulate.py` installs a stub for
it (EvE's samplers only need it on the rank-exponential path, and the stub is validated by
the `RankExponentialSumSampler` ⇄ `RankSoftmaxSampler` equivalence checks — see
`DERIVATIONS.md` §6.0).

Nothing is installed and nothing is mutated: the runtime sources are opened read-only.

## Rerun the simulation

```bash
cd a0/acceptance
python3 simulate.py                      # ~2 min at the default 10^6 draws per case
python3 simulate.py --draws 200000       # quicker, looser tolerance check
python3 simulate.py --emit-json          # also rewrite expected_values.json
```

Exit codes: `0` = every closed form agreed with its simulation; `2` = at least one
`DISAGREEMENT` was printed (the script never papers one over). To watch the failure path
work, run `python3 simulate.py --draws 50` — Monte-Carlo noise then exceeds the tolerance
and the script prints a `DISAGREEMENT` block and exits `2`.

**Reproducibility.** The simulation is bit-for-bit reproducible: every Monte-Carlo driver
passes an explicit `random.Random(<fixed seed>)`. Those seeds belong to the *simulation*,
not to the runtime — EvE's own RNG is unseeded (`populations/base.py:40`), which is why
A0.2 needs a frequency test rather than a seeded replay. `run_output.txt` is therefore the
current output, not a snapshot. The only nondeterminism in the script is the state of the
source trees it reads.

## Source locations the scripts read

| runtime | path the script uses | override |
| --- | --- | --- |
| EvE | `/tmp/eve` (pinned `979065fd`) | edit `EVE_ROOT` / `EVE_COMMIT` at the top of `simulate.py` |
| Loreley | `/tmp/lor` | edit `LOR_ROOT` / `LOR_NOTE`; the copy is verified blob-identical to pin `4c375920`, whose checkout is `a0/tasks/circle-packing/upstream/loreley` (`DERIVATIONS.md` §0.1) |
| KAPSO | not read at runtime; the selection rules are transcribed in `simulate.py` with the source lines quoted in the function docstrings | — |

The current `/tmp/lor` copy is already verified blob-identical to the pin `4c375920`
(591/592 entries; the one difference is a submodule gitlink): a pinned checkout now exists at
`a0/tasks/circle-packing/upstream/loreley`, and `DERIVATIONS.md` §0.1 gives the exact blob
comparison, which is a few lines to re-run if either tree moves. `LOR_ROOT` deliberately
stays on `/tmp/lor` so `simulate.py` does not depend on another workstream's directory; point
it at the pinned checkout to reproduce from the git-verified tree.

## Rerun a derivation by hand

1. **EvE.** Read `configs/eve/loop/default.yaml` for the frozen samplers and draw counts,
   then `src/scaling_evolve/algorithms/eve/populations/samplers/{base,rank_softmax,uniform}.py`
   for the algorithm. The weight vector is `exp(-rank/T)`; the no-replacement path never
   recomputes weights, so it is Plackett–Luce.
2. **KAPSO.** Read `src/kapso/execution/search_strategies/generic/strategy.py` lines
   211-212 (default `parent_policy`), 1374-1403 (`_select_parent`), 1424-1434
   (`get_best_experiment`), 1436-1453 + `execution/fidelity.py:184-213`
   (`select_committed_candidate`), and `registered_evaluation.py:87-99` (the granted-class
   gate).
3. **Loreley.** Read `loreley/core/map_elites/pareto_archive.py` (`index_of`,
   `_merge_affected_cells`, `_select_front`, `_dominates`, `_crowding_distances`, `sample`),
   `config.py:904-956` for the frozen defaults, and `scheduler/main.py:876-931` for the
   report query.
4. **SimpleLoop.** No upstream implementation exists; the specification is protocol §4.4
   (line ~608) plus `DERIVATIONS.md` §4.

## Using `expected_values.json`

Keys: `provenance`, `eve`, `loreley`, `kapso`, `simpleloop`, `power`, `mc_resolution`.
Each entry in `eve` / `loreley` carries the closed form, the simulated value, the absolute
difference and (for the probabilistic ones) a `decision_rule` or `note`. The `power` block
holds, per alternative, the two-sided and one-sided normal-approximation counts and the
exact binomial count at `alpha = 0.05`, power = 0.90 — these are the numbers to quote in the
pre-registration, and `ACCEPTANCE.md` §3.4 states which one is binding.

## Constraints this directory honours

- Everything here is expectation and criteria only: no adapter is implemented and no runtime
  is executed (only the sampler/archive library code, in-process, read-only).
- `a0/contract/**`, `a0/tasks/circle-packing/**` and the runtime adapters are owned by other
  agents and were not touched.
- The protocol `.typ` files were read only and never edited.
