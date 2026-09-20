# `a0/tasks/circle-packing` — the frozen ground-truth evaluator `E*` and the candidate set `C*`

This directory is the study's plumbing-task truth, frozen *outside* the four runtimes
(KAPSO, EvE, Loreley, `SimpleLoop`). It owns these artifacts:

| Path | What it is |
|---|---|
| `e_star.py` (`+ e_star_child.py`) | `E*`: `Candidate -> Outcome`, the reference evaluator the A0.1 conformance check compares every runtime's `E_r` against |
| `C_STAR/` + `C_STAR/manifest.json` | `C* = {c01 … c14}`, the fixed candidate set, each member a self-contained directory with `solution.py` |
| `E_STAR.json` | `E*` applied to every member of `C*`, full multi-field Outcome per candidate, seed, and the exact command |
| `EID_INPUTS.json` | the five canonical inputs for `EID* = H(EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition)` |
| `upstream/loreley`, `upstream/circle-packing` | the two upstream repositories, pinned |

Nothing here writes outside this directory. State written by `E*` at runtime goes to its own
state root (default `<tmp>/e-star-state`, overridable with `--state-dir`), never into a candidate
tree and never into the caller's working directory.

---

## 1. The frozen objective, and where it comes from upstream

```
objective(c) = sum_radii(c) = sum of the radii returned by c.pack_circles(26)
```

* Upstream task statement: `circle-packing/loreley.program.md:7-10` ("Primary metric / name:
  sum_radii / direction: higher_is_better / unit: radius_sum") and
  `circle-packing/README.md:19-27` ("**Objective**: … maximise the sum of radii").
* Upstream computation: `examples/circle_packing_env/evaluate.py:133-145`
  (`_compute_metrics`: `sum_radii = sum(r for _, _, r in circles)`,
  `packing_density = sum(pi * (r**2) …)` with container area 1.0). `evaluate.py` is the plugin
  Loreley's worker actually loads (`examples/evol_circle_packing.py:86-87`,
  `WORKER_EVALUATOR_PLUGIN = "evaluate:plugin"`).
* The gates E\* enforces are the ones that same file enforces: length-3 finite triples,
  `r > 0`, inside the unit square, pairwise non-overlap at `EPS = 1e-9` (`evaluate.py:23`),
  exactly `n` circles, determinism across repeated calls, p50 runtime ≤ 250 ms
  (`evaluate.py:20-28`, `:231-279`).

`E*` keeps that formula bit-for-bit, including the *expression*: it uses
`sum(r for _, _, r in circles)`, because CPython ≥ 3.12 sums floats with compensated summation
while an explicit accumulator loop does not. That detail is not cosmetic — the two upstream
evaluator files disagree in the last bit on the same candidate:

```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python upstream/circle-packing/scripts/local_eval.py \
    --repo-root C_STAR/c01_good_hex --runs 5 --target-n 26 --json \
  | .venv/bin/python -c "import json,sys;print(repr(json.load(sys.stdin)['target_metrics']['sum_radii']))"
2.4519205208433137                                 # local_eval's naive accumulator loop
$ .venv/bin/python -c "import json;print(repr(json.load(open('E_STAR.json'))['candidates'][0]['outcome']['objective']['value']))"
2.4519205208433132                                 # E*, i.e. evaluate.py's sum()
```

`E*` mirrors `evaluate.py` (the plugin wired into the worker), not `local_eval.py`, and
`tools/crosscheck_upstream.py` proves it is bit-identical to that plugin on all 14 candidates.
`min_gap` and `min_boundary_margin` follow `scripts/local_eval.py:104-131` (upstream's plugin
does not report them); they are audit-scoped structural fields, not part of the objective.

**E\* does not scalarize.** The Outcome carries `objective`, `structure`, `validity` and a flat
`fields` map; collapsing to one number is the adapter's `F_r`.

---

## 2. Setup (pinned interpreter)

System python is 3.14.7; the study pins 3.11/3.12, so `E*` runs under its own 3.12 venv with no
third-party packages:

```console
$ cd /home/ebt/rsi-dev/a0/tasks/circle-packing
$ uv venv --python 3.12 .venv
Using CPython 3.12.11
Creating virtual environment at: .venv
$ .venv/bin/python -V
Python 3.12.11
$ uv pip freeze --python .venv
   (no output: no third-party packages at all)
```

A separate, *tool-only* venv `.venv-tools` (numpy, loguru, rich) exists for
`tools/make_good_packing.py` and `tools/crosscheck_upstream.py`. It is not part of `E*`'s identity.

---

## 3. The CLI a downstream adapter must call

```bash
a0/tasks/circle-packing/.venv/bin/python a0/tasks/circle-packing/e_star.py evaluate \
  --candidate <path to a directory containing solution.py> \
  --seed 1337 --fidelity full --fraction 1.0 \
  --out <path for the canonical Outcome JSON> \
  [--state-dir <state root>] [--emit-resources <timing sidecar>]
```

`--candidate` accepts either a directory (containing `solution.py`) or the file itself.
`--seed` defaults to `1337`; `--fidelity` defaults to `full`; `--fraction` defaults to `1.0`
(`full`) or `0.15` (`fast`); `--n` 26, `--runs` 5, `--runtime-budget-ms` 250, `--timeout-s` 120.

Exit codes: **0 = ok, 2 = invalid, 3 = error**. Stdout is exactly one `E_STAR_MANIFEST {...}`
line (deterministic — the state directory path is printed on stderr instead). Example:

```console
$ .venv/bin/python e_star.py evaluate --candidate C_STAR/c01_good_hex --seed 1337 --fidelity full --out /tmp/demo/c01.json --state-dir /tmp/demo/state
e_star: status=ok state_dir=/tmp/demo/state/bca4286ed3b15035-8c9da155eb13c73b out=/tmp/demo/c01.json
E_STAR_MANIFEST {"candidate_source_sha256": "bca4286ed3b15035675f3f2bb2ed0ac8b9e53649f370bf3e5768b5105e3f4a6d", "canonical_digest": "1144adc6b553870800e15131dc2ca1d9e821cc92f49b07f740127ea7416874f8", "e_star_version": "1.0.0", "evaluator_source_sha256": "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532", "fidelity": "full", "fraction": 1.0, "items": 26, "objective": {"direction": "max", "name": "sum_radii", "unit": "radius_sum", "value": 2.4519205208433132}, "schema": "e_star.manifest/v1", "seed": 1337, "status": "ok", "total_items": 26}
```

The Outcome itself (`--out`) has these fields:

| Field | Meaning |
|---|---|
| `schema`, `e_star_version`, `evaluator_source_sha256`, `interpreter` | provenance of the measurement (content digests, not paths) |
| `theta_e` | `{seed, fidelity, fraction, n, runs, runtime_budget_ms, timeout_s}` — the evaluator inputs |
| `candidate` | `{entry, source_sha256, source_bytes}` — **content**, never a path |
| `status`, `scored`, `failure` | `ok` / `invalid` / `error`, plus `failure.kind` + message |
| `objective` | `{name: sum_radii, value, unit, direction}` or `null` |
| `structure` | diagnostics over the audited set: `num_circles`, `overlap_count`, `min_gap`, `min_boundary_margin`, `packing_density`, `sum_radii` (reported even for rejected configurations) |
| `fields` | flat **score-facing** projection (`sum_radii`, `packing_density`, `num_circles`, `overlap_count`, `min_gap`, `min_boundary_margin`, `items_audited`, `pairs_audited`, `audit_coverage`). Every metric is `null` unless `status == "ok"` — this is the path `a0/contract/fr/scalar.json` reads (`outcome.fields.sum_radii`) |
| `validity` | `{ok, checks[], audit{items_total, items_audited, pairs_total, pairs_audited, coverage, sample, sample_sha256, seed, fidelity}}` |
| `resources` | always `null`: timings are environment-dependent and live in the state root (`resources.json`), never in the canonical bytes |
| `canonical_digest` | sha256 of the canonical JSON of everything above except this field |

Check names mirror upstream's `tests_executed` list (`evaluate.py:322-329`):
`count_equals_n`, `radius_positive_check`, `bounds_check`, `overlap_check`,
`determinism_check`, `runtime_budget_check`, plus the process-level ones
(`child_artifacts_complete`, `candidate_module_imports`, `candidate_defines_entrypoint`,
`all_runs_recorded`, `candidate_call_succeeds`, `output_parses_as_triples`).

A failure never produces a number:

```console
$ .venv/bin/python e_star.py evaluate --candidate C_STAR/c12_exit_without_artifacts --seed 1337 --out /tmp/demo/c12.json --state-dir /tmp/demo/state
e_star: status=error state_dir=/tmp/demo/state/f8dcd5c14eafc57a-8c9da155eb13c73b out=/tmp/demo/c12.json
e_star: failure=child_terminated_early: the isolated runner did not write its done marker; no measurement exists
E_STAR_MANIFEST {"candidate_source_sha256": "f8dcd5c14eafc57a9b7e82e23cab78583f8e8d4be8d72f90931cb511334ecc6d", "canonical_digest": "cb4d9bcc4712dcc4e670f7feea3ccb72a60aa7fb5c09d2a3382b699a894f9a64", "e_star_version": "1.0.0", "evaluator_source_sha256": "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532", "fidelity": "full", "fraction": 1.0, "items": 26, "objective": null, "schema": "e_star.manifest/v1", "seed": 1337, "status": "error", "total_items": 26}
$ echo $?
3
```

---

## 4. `C*`, and why each member exists

`C* = {c01 … c14}`; the full justification is in `C_STAR/README.md`, and `C_STAR/manifest.json`
follows `a0.candidateset/v1` (the shape `a0/contract/adapter_contract.md` §2 consumes) with
`role` ∈ {good, baseline, tie, bad} and this workstream's provenance keys on top.

| id | role | `E*` objective | `E*` status (exit) | why it is in `C*` |
|---|---|---|---|---|
| `c01_good_hex` | good | 2.4519205208433132 | ok (0) | high end of the required ordered pair; jammed 26-circle packing from `tools/make_good_packing.py` |
| `c02_baseline_upstream` | baseline | 0.25 | ok (0) | low end of that pair; upstream `solution.py`@`b91c090` verbatim, i.e. `c_0` |
| `c03_mirror` | tie | 2.4519205208433132 | ok (0) | exact tie with `c01`, *identical structure, different content* |
| `c04_near_tie` | tie | 2.4518205208433135 | ok (0) | near-tie with `c01`, Δ = 1.0000000000021e-04 |
| `c05_overlapping` | bad | `null` | invalid (2) | one fully overlapping pair; `overlap_count=1`; diagnostics present, no score |
| `c06_empty` | bad | `null` | invalid (2) | returns `[]` |
| `c07_single` | bad | `null` | invalid (2) | returns one valid circle |
| `c08_out_of_bounds` | bad | `null` | invalid (2) | whole packing translated out of the square (bounds gate only) |
| `c09_malformed_import` | bad | `null` | error (3) | `solution.py` does not parse |
| `c10_raises` | bad | `null` | error (3) | `pack_circles` raises |
| `c11_non_deterministic` | bad | `null` | error (3) | valid geometry, different radii per call |
| `c12_exit_without_artifacts` | bad | `null` | error (3) | `os._exit(0)`: kills the runner, exit code 0, no artifact |
| `c13_slow` | bad | `null` | error (3) | valid geometry behind a 0.3 s sleep (p50 > 250 ms) |
| `c14_near_zero` | bad | 2.600000000000001e-05 | ok (0) | a *genuine* near-zero score, so `null` and `0.0` cannot be conflated |

Answers to the questions the protocol asks of this set:

* **Ordered pair with a decidable margin**: `E*(c01) − E*(c02) = 2.2019205208433132`, which is
  4 958 284 218 584 697 ULP at that magnitude (`math.ulp(2.4519205208433132) = 4.440892098500626e-16`)
  — no epsilon, rounding, rank transform or softmax can absorb it.
* **Tied/near-tied pair**: `c01`/`c03` are exactly tied; `c01`/`c04` differ by 1e-4.
* **Identical structure, different content**: yes — `c01`/`c03` (reflected packing; every metric
  field bit-identical, `solution.py` sha256 `bca4286e…` vs `893d0aa4…`).
* **Candidates expected to make `E*` fail rather than return a measurement**: `c09`–`c13`
  (`status="error"`, exit 3, `objective=null`). `E*` never raises an uncaught exception for any
  member: it always writes the Outcome and signals via the exit code. Only an unreadable
  candidate path makes it exit 3 *without* writing `--out`; it never writes a partial or
  zero-valued Outcome.

---

## 5. `E_STAR.json`, and the stability demonstration

```console
$ .venv/bin/python tools/build_table.py --write
wrote /home/ebt/rsi-dev/a0/tasks/circle-packing/E_STAR.json (160818 bytes)
candidate                        exit   status              objective  fast
c01_good_hex                        0       ok         2.451920520843  ok/4items
c02_baseline_upstream               0       ok         0.250000000000  ok/4items
c03_mirror                          0       ok         2.451920520843  ok/4items
c04_near_tie                        0       ok         2.451820520843  ok/4items
c05_overlapping                     2  invalid                   null  ok/4items
c06_empty                           2  invalid                   null  invalid/4items
c07_single                          2  invalid                   null  invalid/4items
c08_out_of_bounds                   2  invalid                   null  invalid/4items
c09_malformed_import                3    error                   null  error/4items
c10_raises                          3    error                   null  error/4items
c11_non_deterministic               3    error                   null  error/4items
c12_exit_without_artifacts          3    error                   null  error/4items
c13_slow                            3    error                   null  error/4items
c14_near_zero                       0       ok         0.000026000000  ok/4items
```

The tool invokes the real CLI once per candidate (no imports of `e_star.py` internals) and records
the exit code, the manifest line and the canonical Outcome verbatim. Stability, by rerunning every
candidate and comparing bytes:

```console
$ .venv/bin/python tools/build_table.py --check
E_STAR.json is stable: rerun produced byte-identical output
```

The table contains **two** thetas. `canonical_theta_e = {seed 1337, fidelity full, fraction 1.0,
n 26, runs 5, budget 250 ms}` holds each candidate's complete Outcome; `fast_theta_e = {seed 1337,
fidelity fast, fraction 0.15, …}` holds the complete fast-tier Outcome plus a summary row
(`status`, `objective_value`, `items_audited`, `coverage`, `canonical_digest`) — the second one is
there because `adapter_contract.md` §3's example theta is exactly `seed=1337,fidelity=fast,fraction=0.15`.

Timings are deliberately excluded: they vary run to run (in `resources.json` only).

---

## 6. The three hard constraints of §4.2.2, with evidence

`tools/check_invariance.py` runs the real CLI and compares real bytes:

```console
$ .venv/bin/python tools/check_invariance.py
[PASS] cwd: identical --out bytes and stdout from repo-root, slash, tmp (sha256 65e223ec2e7eee4b, exit 0)
[PASS] path: PATH=/tmp/e-star-invariance/path/poison-bin:/nonexistent gave identical --out bytes (sha256 65e223ec2e7eee4b)
[PASS] env: hostile EVE_*/PYTHONPATH/CIRCLE_PACKING_* environment gave identical --out bytes
[PASS] relocate: the same bytes under three different paths/names gave identical outcomes (sha256 65e223ec2e7eee4b)
[PASS] tree: candidate tree byte-identical after evaluation, files=['candidate.json', 'solution.py']
[PASS] revert: state root and --out survived `git checkout . && git clean -xfd`; rerun is byte-identical (worktree left clean: '')
[PASS] seedful: full: 1 distinct measurement(s) for c05 and 1 for c01 over 12 seeds, samples audited=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25)]; fast(0.15) statuses=['invalid', 'ok']; seed 0 -> ok [1, 12, 14, 22] overlap_count=0; seed 1 -> ok [4, 11, 19, 22] overlap_count=0; seed 2 -> ok [0, 4, 12, 22] overlap_count=0; seed 3 -> ok [0, 7, 16, 23] overlap_count=0
[PASS] sideeffect: candidate's own writes never touched its tree (files=['solution.py']); they landed under the state root as ['5b97f19193501e23-8c9da155eb13c73b/candidate/candidate_wrote_here.txt', '5b97f19193501e23-8c9da155eb13c73b/cwd/cwd_write.txt']

8/8 checks passed
```

**1 — no dependence on cwd or PATH.** Three working directories (the repo root, `/`, a temp dir),
each with its *own* state dir, produced byte-identical `--out` files *and* byte-identical stdout.
With a poisoned `PATH` (fake `python`, `python3`, `git`, `gcc`, `cc`, `sh` that exit 111, prepended
before `/nonexistent`) the bytes are unchanged; `E*` spawns its child with `sys.executable` (an
absolute path) and a fully specified child environment (`PATH=""`, `PYTHONPATH=""`,
`PYTHONHASHSEED=0`, `PYTHONNOUSERSITE=1`, `PYTHONDONTWRITEBYTECODE=1`, private `HOME`/`TMPDIR`/cwd).
Hostile caller environment (`EVE_WORKSPACE_ROOT`, `EVE_SOLVER_ROOT`, `EVE_EVAL_LOG_ROOT`,
`PYTHONPATH=/evil/site`, `CIRCLE_PACKING_RUNTIME_BUDGET_MS=1`, `CIRCLE_PACKING_RUNTIME_RUNS=3`,
`HOME=/evil/home`, `TMPDIR=/evil/tmp`) also leaves the bytes unchanged — note that upstream's own
plugin *does* read those two `CIRCLE_PACKING_*` variables (`evaluate.py:190-209`); `E*` does not.
The same candidate bytes relocated to two unrelated paths/names give identical outcomes, so the
score is a function of content, not location.

**2 — no counting or logging where a `git checkout` can revert it.** Everything `E*` writes goes
below its state root, keyed by `sha256(candidate content)` + `theta_E` digest: the private copy of
the candidate, the per-run artifacts, the child's stdout/stderr, `resources.json`. Nothing is ever
written into the caller's tree or a candidate worktree. The `revert` check builds a real git
worktree, evaluates it, then runs `git checkout -- . && git clean -xfd`: the state root and `--out`
survive untouched and a rerun is byte-identical, with the worktree left clean. The `tree` check
hashes the candidate directory before and after evaluation; the `sideeffect` check runs a candidate
that deliberately writes `Path(__file__).parent / …` and `./cwd_write.txt` — both land under the
state root, because `E*` executes a *copy* of the candidate bytes
(`<state>/candidate/solution.py`) with cwd `<state>/cwd`, never the caller's file.

**3 — multi-field output.** See §3: `objective` + `structure` + `validity` + `fields`; the
`rejected`/`error` cases keep their diagnostics while `objective` and every score-facing field
stay `null`.

---

## 7. Seed semantics

`theta_E = (seed, fidelity, fraction, n, runs, runtime_budget_ms, timeout_s)`. The seed's only role
is to draw the **audit subsample**: the items `E*` audits (`radius_positive_check`,
`bounds_check`) and, derived from them, the pairs it checks for overlap. The draw is
`sha256("e_star/v1|seed=<s>|n=<n>|index=<i>")`-ordered, so it is reproducible on any Python
version or platform, unlike `random.Random.sample`. The audit is recorded in
`validity.audit` (`items_audited`, `pairs_audited`, `coverage`, `sample`, `sample_sha256`).

* `--fidelity full` audits every item; the subsample is the whole set by construction, so the seed
  cannot change the *measurement* (it still appears in the recorded `theta_e`). Evidence: 12 seeds
  give 1 distinct measurement for `c05` and for `c01`, with the audited sample always the full
  26-item set.
* `--fidelity fast --fraction 0.15` audits a seeded decimation (`round(0.15 × 26) = 4` items → 6 of
  325 pairs, coverage 0.018 of pairs). Here the seed genuinely bites: over 12 seeds `c05`
  (overlapping pair at indices 0–1) is reported `ok` for some seeds and `invalid` for others,
  because the sampled items differ (`seed 0 -> [1, 12, 14, 22]`, `seed 1 -> [4, 11, 19, 22]`, …).
  This is the declared cost/accuracy trade of the fast tier, and the reason the protocol requires
  the `(fidelity, fraction, seed)` triple to be recorded per attempt: a fast-tier `ok` is an
  approximation, and `audit.coverage` makes that visible in the Outcome. Every A0.1/A0.2 comparison
  in `E_STAR.json`'s canonical table is at `fidelity=full`.

The default seed `1337` and the default fast fraction `0.15` are KAPSO's registered values
(`evaluation_maintainer.subsample_seed`; `FidelitySpec.eval_fast_fraction = 0.15`,
`src/kapso/execution/fidelity.py:247`), so a runtime whose interface cannot carry a seed can be
driven with the protocol's fixed equivalent value rather than an invented one.

---

## 8. Faithfulness cross-check against upstream's own evaluator

`tools/crosscheck_upstream.py` runs upstream's plugin
(`upstream/loreley/examples/circle_packing_env/evaluate.py::plugin`) on every member of `C*`, each
in a subprocess, and compares with `E_STAR.json`:

```console
$ .venv/bin/python tools/crosscheck_upstream.py
candidate                   E* status            E* objective  upstream
c01_good_hex                       ok          2.451920520843  returned sum_radii=2.4519205208433132
c02_baseline_upstream              ok          0.250000000000  returned sum_radii=0.25
c03_mirror                         ok          2.451920520843  returned sum_radii=2.4519205208433132
c04_near_tie                       ok          2.451820520843  returned sum_radii=2.451820520843313
c05_overlapping               invalid                    null  raised ValueError
c06_empty                     invalid                    null  raised ValueError
c07_single                    invalid                    null  raised ValueError
c08_out_of_bounds             invalid                    null  raised ValueError
c09_malformed_import            error                    null  raised SyntaxError
c10_raises                      error                    null  raised RuntimeError
c11_non_deterministic           error                    null  raised ValueError
c12_exit_without_artifacts      error                    null  no_report rc=0
c13_slow                        error                    null  raised ValueError
c14_near_zero                      ok          0.000026000000  returned sum_radii=2.6e-05

all 14 candidates agree with upstream's evaluator
```

``==`` is exact (binary64 equality) for `sum_radii`, `packing_density`, `num_circles` and the
ok/raise verdict. `c12` is the one deliberate difference: upstream's plugin is called in-process,
so a candidate that calls `os._exit(0)` leaves its caller a clean exit code 0 and no verdict at
all; `E*` detects the missing artifact (`child_terminated_early`) and refuses to report a score.

---

## 9. `EID_INPUTS.json` and `EID*`

The hashing scheme is owned by a parallel workstream (`a0/contract/evalcontract.py`). `EID_INPUTS.json`
therefore *imports that module* and feeds it this task's five inputs, then records the canonical
material each component hashes plus the resulting digests. The spec it embeds is a drop-in
replacement for `a0/contract/plumbing.contract.json` (also written to
`plumbing.contract.proposed.json`), with:

* **EvaluatorSource** — `e_star.py` + `e_star_child.py` (the frozen evaluator itself), i.e. the
  files whose sha256 are recorded above.
* **DependencyLock** — `requirements.lock` (raw) plus an inline entry `{"python": "3.12.11",
  "implementation": "CPython", "third_party_packages": []}`; `E*` and every candidate use the
  standard library only.
* **DataManifest** — 39 files (the 29 machine-readable `C_STAR/` files — 14 `solution.py`, 14
  `candidate.json`, `manifest.json` — plus 9 pinned upstream reference files and
  `tools/good_packing_26.json`; prose is excluded so editing docs does not move `EID*`), plus four
  inline records for the two pinned upstream commits:
  `github.com/NeapolitanIcecream/loreley @ 4c3759208e6b908f90716488ac3eec3dceaaf397` and
  `github.com/NeapolitanIcecream/circle-packing @ b91c0906c9f676eb661990d881144909d99f2d72`.
  `E_STAR.json` is deliberately *not* hashed into `EID*` (it is a derived artifact, recorded as an
  inline note instead).
* **Config** — `theta_E` canonical + fast values, evaluator constants (EPS 1e-9, runs 5, 250 ms,
  unit square), environment policy, cwd-independence and revert-safety requirements.
* **MetricDefinition** — `sum_radii`, direction `maximize`, unit `radius_sum`, the four outcome
  fields, the validity gates, the failure semantics (`status != ok ⇒ objective null, never 0.0`),
  and the provenance list above.

```console
$ .venv/bin/python tools/build_eid_inputs.py --write
wrote /home/ebt/rsi-dev/a0/tasks/circle-packing/EID_INPUTS.json (30897 bytes)
EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
verify: rc=0 clean: all recorded inputs match; EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328

$ .venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py recompute --eid-file plumbing.EID.proposed.json
  [ok ] EvaluatorSource    recorded=a3d6534b4e3bc78f recomputed=a3d6534b4e3bc78f
  [ok ] DependencyLock     recorded=7b02f1a71288335f recomputed=7b02f1a71288335f
  [ok ] DataManifest       recorded=b21c975a51ef24cd recomputed=b21c975a51ef24cd
  [ok ] Config             recorded=550ca3cdd8af04ec recomputed=550ca3cdd8af04ec
  [ok ] MetricDefinition   recorded=420ab0acf24e1c73 recomputed=420ab0acf24e1c73
  [ok ] EID*               recorded=664115e0d63ad2e1 recomputed=664115e0d63ad2e1
```

(`recompute` touches no filesystem, so it succeeds identically on any machine holding the EID
document.)

`EID_INPUTS.json` also records five `recommendations_for_contract_owner` items where this workstream's
artifacts and the frozen `a0/contract` documents currently disagree:

1. `plumbing.contract.json` points `EvaluatorSource` at upstream's `scripts/` (i.e. `local_eval.py`);
   the frozen evaluator is `e_star.py` + `e_star_child.py`.
2. its `Config` says the seed is inapplicable and the fraction is fixed at 1.0; protocol
   `plan:513-523` makes the seed an evaluator input (`theta_E = seed, fidelity, fraction`) whose
   triple must be recorded per attempt, so the seed is applicable, defaulting to 1337.
3. `adapter_contract.md` §4 parses `target_metrics[sum_radii]` from `local_eval.py`'s stdout;
   `E*`'s contract is `--out <json>` with `objective.value`, `status`, exit codes 0/2/3 and
   `objective = null` on failure. `local_eval.py` cannot express invalid/error, the audit fields,
   or the seed, and it is the file that differs from the plugin by one ULP.
4. `adapter_contract.md` §3 points `--candidate-set` at `candidates/manifest.json`; this
   workstream's directory is `C_STAR/`, so the flag value is
   `a0/tasks/circle-packing/C_STAR/manifest.json` (`C_STAR/manifest.json` already follows
   `a0.candidateset/v1`).
5. the `{"candidate_set": "C*", "status": "pending"}` placeholder in `DataManifest` can move to
   published — the files are hashed in `EID_INPUTS.json`.

---

## 10. Reproducing everything from scratch

```bash
cd /home/ebt/rsi-dev/a0/tasks/circle-packing

# 0. pinned interpreter (CPython 3.12.11) and the tool-only venv
uv venv --python 3.12 .venv
uv venv --python 3.12 .venv-tools && uv pip install --python .venv-tools/bin/python numpy loguru rich

# 1. upstream pins (already present): a real git checkout each, at the pinned commit
git -C upstream/loreley rev-parse HEAD          # 4c3759208e6b908f90716488ac3eec3dceaaf397
git -C upstream/loreley status --short          # empty: the tree matches the commit
git -C upstream/circle-packing rev-parse HEAD   # b91c0906c9f676eb661990d881144909d99f2d72

# 2. C* matches its builder; E_STAR.json is byte-stable; the invariants hold; upstream agrees
.venv/bin/python tools/build_c_star.py --check
.venv/bin/python tools/build_table.py --check
.venv/bin/python tools/check_invariance.py
.venv/bin/python tools/crosscheck_upstream.py

# 3. EID inputs and the identity check through the contract owner's own CLI
.venv/bin/python tools/build_eid_inputs.py --check
.venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py verify \
  --eid-file plumbing.EID.proposed.json --spec plumbing.contract.proposed.json

# 4. (optional, ~5 min) regenerate the frozen good-packing geometry, then rebuild C* and the table
.venv-tools/bin/python tools/make_good_packing.py --n 26 --seed 0 --trials 5 --iters 40 \
  --budgets 200,2000,20000 --shrink-budgets 100,1000,6000 --hi-side 12.0 --lo-side 9.0 \
  --json /tmp/good_packing_26.json
.venv/bin/python tools/build_c_star.py --write && .venv/bin/python tools/build_table.py --write
```

Step 4 was verified once, end to end: rerunning the generator with those exact flags reproduced
`tools/good_packing_26.json` byte for byte, so the frozen geometry is reproducible from the
recorded invocation:

```console
$ .venv-tools/bin/python tools/make_good_packing.py --n 26 --seed 0 --trials 5 --iters 40 \
    --budgets 200,2000,20000 --shrink-budgets 100,1000,6000 --hi-side 12.0 --lo-side 9.0 \
    --json /tmp/good_rerun.json            # ~3.5 minutes
$ .venv/bin/python -c "import json;print(json.load(open('tools/good_packing_26.json'))==json.load(open('/tmp/good_rerun.json')))"
True
```

`tools/` is not part of `E*`'s identity; `E*` itself is `e_star.py` + `e_star_child.py` only.

---

## 11. Limitations, guesses, and what is *not* verified

* **`a0/contract/plumbing.contract.json` was not edited** (another workstream owns it). It still
  points at `local_eval.py` and its `EID*` (`fac50fc4…`) is therefore not the identity of this
  evaluator. `EID_INPUTS.json` + `plumbing.contract.proposed.json` carry the corrected inputs
  (`EID* = 664115e0…`); adopting them is the contract owner's call.
* **Multi-`n` sampling is not implemented.** Upstream's `local_eval.py` also samples `n ∈ {1,2,5,26}`;
  `E*` evaluates one `n` per invocation (`--n`, default 26), which is what `theta_E` records. A
  runtime that wants the `n`-sweep can invoke `E*` once per `n`; those invocations are separate
  thetas, so they must not be pooled with the `n=26` comparison. The `c` members marked *bad* keep
  their designed behaviour at every `n` (`c06` still returns `[]`, `c07` one circle, `c09`–`c13`
  still fail), while the good/baseline/tie members fall back to the upstream diagonal construction
  for `n ≠ 26`, so upstream's `local_eval.py` also runs on those unchanged.
* **`c01_good_hex` is good, not optimal.** Its radius `0.0943046354170505` (26 equal circles,
  packing density 0.7264) is a locally jammed max-min packing from a seeded heuristic. It is 5.7%
  below the provable reference point next door — 25 circles fit at exactly `r = 0.1` (a 5×5 grid),
  and no arrangement of 26 can reach it — but it is *not* a certified optimum, and leaving headroom
  is deliberate for a measurement study (B0/A1 need somewhere to improve).
* **Clock-based gates are clock-based.** `runtime_budget_check` and `--timeout-s` depend on
  wall-clock time; their verdicts cannot be byte-stable in principle. For every member of `C*` the
  margin is enormous (valid candidates take ~0.006 ms per call against a 250 ms budget; `c13_slow`
  sleeps 0.3 s), so the verdicts are robust — but they are the one part of the Outcome that is not
  a pure function of content.
* **In-process sabotage by a candidate is not fully preventable.** `E*` never imports candidate
  code into the scoring process, and the scoring process re-derives every metric from the raw
  artifact, but candidate code *does* run inside the child that writes the artifacts, so a
  deliberately malicious candidate could in principle forge artifact JSON (it can read its own
  `sys.argv`, which carries the run directory). `C*` contains no such candidate. Real defence would
  need OS-level isolation (namespaces/seccomp), which the protocol does not require at this stage.
* **`.venv-tools` is a tool dependency.** `tools/make_good_packing.py` (numpy) and
  `tools/crosscheck_upstream.py` (loguru, rich, because upstream's plugin imports them at module
  level) need it. Neither is part of `E*`.
* **Two paths in the recorded commands are machine-specific**: `state_root`
  (`/tmp/e-star-state-table`) and the absolute interpreter path in `plumbing.contract.proposed.json`'s
  documented commands. The Outcomes themselves contain no paths at all.
* A tool of *mine* (the upstream cross-check oracle) initially left `__pycache__` inside `C_STAR/`
  because it imports candidate code in-process; the `tree` check caught it and the oracle now sets
  `PYTHONDONTWRITEBYTECODE=1`. Worth remembering when wiring adapters: only `E*` executes a private
  copy, everyone else must be told not to import candidate code in place.
