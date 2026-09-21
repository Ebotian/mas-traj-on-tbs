# EvE RNG injection surface (review D4)

Owner: `a0/notes/exit-closed/eve-rng/**`. Measured 2026-09-21 on this host against the pinned
EvE checkout at `/tmp/eve` (`979065fd2cf1b3be9caf70596478fe27df7815ad`). The checkout was read
only; nothing under `/tmp/eve` was written or patched.

**Question (D4).** The review decided there will be **no upstream patch**, preferring
config/API injection, and otherwise independent campaign replication. The audit had found the
samplers take `rng: random.Random | None = None` and fall back to `random.Random()`
(`solver_workspace.py:61,91`, `samplers/uniform.py:32`), while the Hydra configs expose no
`rng`/`seed` key. This note determines the *real* surface.

**Verdict.** There is **no config surface** for the rng. Config reaches the sampler **class**
(`_target_`) and its constructor kwargs, but the rng is a **call-time** argument handed in by the
runtime's own call sites, and every one of those call sites passes a fresh unseeded
`random.Random()`. The only injection that works is **Python at the call site** — i.e. an
upstream code change, which D4 forbids. **So for A1 the available answer is independent campaign
replication, not seed-fixing.**

Every claim below is **verified by running it** unless tagged otherwise.

---

## 1. What config can reach

Run:

```bash
a0/runtimes/eve/.venv/bin/python a0/notes/exit-closed/eve-rng/probe_rng_injection.py
```

Raw output: `probe_output.json` (this directory). The three attempts, with real values:

### Attempt A — config injection (`[verified by running it]`)

Take EvE's own `solver_prefill` sampler block and add `seed: 1234` and `rng: 1234`, then build it
the way EvE builds it (`hydra.utils.instantiate`, `factory.py:296-297`):

```json
"config_block_with_injection": {
  "_target_": "...samplers.uniform.UniformSampler",
  "replacement_mode": "no_replacement",
  "rng": 1234,
  "seed": 1234
},
"instance_attributes": ["replacement_mode"],
"instance_has_rng_attribute": false,
"deterministic_within_instance": false,
"deterministic_across_instances": false,
"samples_same_instance_a": [15, 6, 5, 19],
"samples_same_instance_b": [10, 4, 20, 15]
```

The injected keys are **discarded**. `UniformSampler.__init__` is
`(*, replacement_mode, **_ignored_kwargs)` (`samplers/uniform.py:19-25`), so every extra key lands
in `**_ignored_kwargs`. `rng` is not a constructor parameter at all; it is the 4th parameter of
`.sample` (`uniform.py:32`), and `.sample` does `rng = rng or random.Random()` (`uniform.py:35`).
Two calls on the same instance, and two instances built from the same config, give different
samples.

### Attempt B — call-site injection (`[verified by running it]`)

Passing an seeded rng at the call site *is* deterministic:

```json
"seeded_reproduces": true,     // rng=random.Random(1234) twice -> identical
"unseeded_reproduces": false   // no rng -> two different samples
```

That surface lives in the runtime's own code: `workflow/phase2.py:566-633` calls
`self.<pop>_sampler.sample(..., rng=self.<pop>._rng)`, and `<pop>._rng` is set in
`populations/base.py:40` as `rng or random.Random()`. `factory.py:308-314` (the populations) and
`factory.py:321-328` (the `SolverWorkspaceBuilder`, `solver_workspace.py:91`) pass **no** `rng=`.
So reaching this surface means editing upstream Python — the patch D4 rules out.

### Attempt C — Hydra `_target_` override (`[verified by running it]`)

```json
"target_swapped_to": "...rank_softmax.RankSoftmaxSampler",
"class_is_selectable": true,
"rng_reachable_via_target": false
```

`_target_` is a dotted import path; `instantiate` swaps the sampler **class** and forwards the
remaining keys to its `__init__`. It cannot define code, and no nameable sampler reads an rng from
its own construction. `_target_` therefore selects the sampling *policy*, never the *stream*.

---

## 2. Why there is no config key to find (`[read from source]`)

```bash
grep -rn "seed\|rng\|random" /tmp/eve/configs/ --include=*.yaml
```

```
configs/eve/evaluation/math_proof.yaml:29:  seed_solver_score:
configs/eve/evaluation/math_proof.yaml:36:  seed_solver_skip_evaluation: true
configs/eve/evaluation/icon.yaml:10:  seed_solver_score:
configs/eve/evaluation/icon.yaml:34:  seed_solver_skip_evaluation: true
configs/eve/evaluation/circle_packing.yaml:11:  seed_solver_score: null
configs/eve/evaluation/circle_packing.yaml:12:  seed_solver_skip_evaluation: false
configs/eve/evaluation/circle_packing.judge.yaml:42:  seed_solver_score: null
configs/eve/evaluation/circle_packing.judge.yaml:43:  seed_solver_skip_evaluation: false
```

The only matches are `seed_solver_score` / `seed_solver_skip_evaluation` — the bootstrap *solver's*
score and whether to skip evaluating it. Neither is an RNG seed. No `rng`, no `seed`, no `random`
key exists anywhere under `configs/eve/**`.

The rng fallback chain, by `path:line` (all in the pinned checkout):

| what | location |
|---|---|
| samplers built by Hydra `instantiate` | `src/scaling_evolve/algorithms/eve/factory.py:296-297` |
| populations built with no `rng=` | `src/scaling_evolve/algorithms/eve/factory.py:308-314` |
| workspace builder built with no `rng=` | `src/scaling_evolve/algorithms/eve/factory.py:321-328` |
| population rng fallback | `src/scaling_evolve/algorithms/eve/populations/base.py:33,40` |
| builder rng fallback | `src/scaling_evolve/algorithms/eve/workspace/solver_workspace.py:61,91` |
| sampler `__init__` swallows kwargs | `src/scaling_evolve/algorithms/eve/populations/samplers/uniform.py:19-25` |
| sampler rng is call-time | `src/scaling_evolve/algorithms/eve/populations/samplers/uniform.py:32,35` |
| samplers called with population rng | `src/scaling_evolve/algorithms/eve/workflow/phase2.py:566-633` |

`probe_output.json → source_evidence.anchors_resolve` records that every path above exists.

---

## 3. Which of `config injection / campaign replication / patch` is available

- **Config injection — not available.** The class is config-selectable; the rng is not. Demonstrated
  (attempt A swallows the key; attempt C cannot reach it).
- **Patch — available but forbidden by D4,** and it would not buy reproducibility anyway: the rng
  seeds Phase-2 sampler *choices* inside one process, while the campaign's outcome is dominated by
  the model calls the runtime issues (and, per `a0/notes/exit-closed/eve/REPORT.md`, those were not
  driven on this host). A fixed Python seed leaves the model stream unfixed.
- **Campaign replication — the available answer.** Freezing the declared instrument (the adapter
  preimage and the MRC* route) and repeating the campaign is the only honest way to estimate A1's
  estimand here.

## 4. Why replication, not seed-fixing, is right for A1's estimand (`[inferred]`)

A1 asks for the effect of the runtime on an iteration's outcome, under a declared instrument. The
randomness that matters is the runtime's own search and its model calls. Two reasons seed-fixing is
the wrong instrument for that estimand:

1. **It changes the estimand.** Fixing the seed conditions the result on one random stream, so the
   quantity measured becomes "the effect under this stream", not the runtime's expected behaviour.
   A1's `B_hard` record (`a0/mrc/A1_ATTRIBUTION.md`) is about the runtime's distribution of
   outcomes, which only repeated independent campaigns estimate.
2. **It would not make the run reproducible even if it worked.** The EvE rng governs sampler
   choices; the model calls are drawn from a live service and the study itself freezes
   `weights_identity.verifiable: false` (`a0/mrc/REPORT.md` §3). A fixed Python seed would create the
   *appearance* of reproducibility without reproducing the run.

Replication treats the whole runtime (including every unseeded draw) as the instrument, which is
what the frozen MRC* declares — and it also exposes a real risk this probe names: EvE's
`_rng` is unseeded, so two campaigns with the same declared route are genuinely different draws.

## 5. Re-run

```bash
a0/runtimes/eve/.venv/bin/python a0/notes/exit-closed/eve-rng/probe_rng_injection.py
# exit 0; the JSON above (probe_output.json) is the recorded run
```

No key, no network, no write to `/tmp/eve`.
