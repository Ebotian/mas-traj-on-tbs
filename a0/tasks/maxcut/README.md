# T1 — frozen max-cut evaluator (`E*`) and its fixed candidate set (`C*(T1)`)

`INTERFACE.md` in this directory is the binding authority; this README says what
was built against it, how to re-run it, and what the run produced.
`DEVIATIONS.md` records every place the implementation had to interpret or
extend the interface, with the justification.

## What is here

| path | what it is |
|---|---|
| `e_star.py` | **E\***: the harness-owned evaluator. `evaluate` / `aggregate` / `digest` |
| `e_star_child.py` | the candidate subprocess loader: §4's argv/cwd/env, §7's process-group `SIGKILL` at tau, §4's exit-code table |
| `candidates/` | **C\*(T1)**: 21 fixed candidates with frozen bytes and sha256 (`candidates/manifest.json`) |
| `build_candidates.py` | writes/verifies the C\*(T1) tree from its frozen sources |
| `conformance.py` | runs all of C\*(T1) through E\*, freezes the verdict table, and executes the six proofs plus the standing checks |
| `test_candidate_staging.py` | regression test for D-T1-10 (the launch must be a function of the candidate's bytes alone); also reached as conformance probe `p7_candidate_staging` |
| `conformance.expected.json` | the frozen table: `(status, cut_edges, failure.kind)` per candidate |
| `conformance.report.json` | the most recent full run, with all probe evidence |
| `graphs_tmp/` | task-owned **temporary** graphs (stand-ins generated before `suite/` landed) and the exact-aggregation demonstration sets |
| `suite/` | **owned by another worker** — never written to by anything here |

## The measurement, in one paragraph

A candidate is a subprocess. It is handed `--graph <abs> --out <abs> --seed <int>`
and must write a `partition.json` (§3). The harness runs it **twice** with the
same candidate bytes, graph bytes and seed, from a **private, content-addressed
copy** of the candidate and a fresh scratch directory each time. §6's frozen
rules then reduce those two runs to one of four statuses. `cut_edges` is
recomputed by E* from its own pre-run copy of the graph; a candidate never
reports a score. `invalid`, `error` and `timeout` all carry `cut_edges: null` —
never `0`. Aggregation is `fractions.Fraction` arithmetic over integers;
`cut_fraction` is a display string rendered from those integers and read by no
decision.

## Run it

```bash
cd a0/tasks/maxcut

# identity of the evaluator
python3 e_star.py digest

# one graph
python3 e_star.py evaluate --candidate candidates/c01_ok_high_pc \
    --graph suite/dev/G_dev_0001.json --seed 1337 --timeout 10 \
    --out /tmp/outcome.json --emit-resources /tmp/resources.json

# a whole set (verifies every graph's sha256 against suite/manifest.json)
python3 e_star.py aggregate --candidate candidates/c01_ok_high_pc \
    --graph-set dev --out /tmp/aggregate.json

# the frozen verdict table
python3 build_candidates.py --check
python3 conformance.py --check

# the launch-integrity regression on its own (D-T1-10)
python3 test_candidate_staging.py
```

`--check` exits 0 when every row still reproduces and all probes pass. `--freeze`
regenerates the table; only do that when the change is intended.

`test_candidate_staging.py --e-star <path>` runs the same regression against a
*different* evaluator, which is how the defect was shown to be caught: pointed at
the pre-fix bytes (`git show <rev>:a0/tasks/maxcut/{e_star,e_star_child}.py`) it
fails, pointed at the working tree it passes.

## What the run produced

Measured on the frozen suite, `suite/dev/G_dev_0001.json`
(sha256 `94c713897fc1c5d4fba63e2212a5746c50e4726f67a8452e0a3ee5b0249063d6`),
seed 1337, tau 10 s — `conformance.report.json`:

| status | count | candidates (`cut_edges` when scored) |
|---|---|---|
| `ok` | 8 | c01 (207), c02 (132), c03 (**0**), c04 (207), c05 (207), c18 (136), c20 (136), c21 (136) |
| `invalid` | 5 | c06, c07, c08, c09, c10 — all `cut_edges: null` |
| `error` | 7 | c11, c12, c13, c14, c15, c16, c17 — all `cut_edges: null` |
| `timeout` | 1 | c19 — `cut_edges: null` |

21 rows in total; `conformance.expected.json` is the record.

The six required proofs, all `PASS`:

| proof | evidence |
|---|---|
| cwd/PATH independence | two different cwds, `PATH=/nonexistent-poison:/also/missing`, hostile `env` — outcome files byte-identical (`a9fb9af3e3138db1…`, 1158 bytes each) |
| determinism | c01's `partition.json` canonical sha256 identical across two full evaluations; c13's differs and is recorded `non_deterministic` |
| failure semantics | no non-`ok` row carries a number, and none carries `0`; `c03` is the control: a *legitimate* 0 is reported as 0 |
| network independence | `unshare -rn` run of c01 still `ok` (same cut as open topology); c15 cannot reach the network and refuses |
| child environment | the child's own dump of `os.environ` is exactly `{PATH, PYTHONDONTWRITEBYTECODE, HOME, LANG}` — no proxy name, no credential-like name, none of the seven decoys the parent was given |
| exact aggregation | two graph sets whose exact scores are both `10/21` are reported **equal**, while float summation over the same edges gives `0.4761904761904762` vs `0.47619047619047616` and would rank one strictly higher |

Plus, beyond the list: `c19`'s forked grandchild keeps a heartbeat file growing
until tau and never beats again afterwards (the *process group* was killed);
`c17`'s input tampering is reported as `input_tampered` with no number; `c18`
inflates its input to 272 and is measured at the true 136; and
`p7_candidate_staging` pins the launch invariant of D-T1-10.

## The frozen positive-control candidates

Read 2026-09-23: `positive_control/pc/` is the **superseded** control. The contract's
`PC_i` since that date is `positive_control/variants/pc_exchange_k10/`
(`candidate_source_sha256 = ee49eba0…`), defined in `INTERFACE.md` §13. This section
stays as written because it records the D-T1-10 fix, which is what it measured; the
digest cell and the verdict sentence below carry the two corrections that reading needs.

`positive_control/{baseline,pc}/solution.py` are mode `0755` with a `#!` line.
Until D-T1-10 was fixed they could not be evaluated at all — but with the fix they
evaluate, and their numbers land exactly on the gate's recorded ones:

| candidate | launched as | status | `cut_edges` on `G_dev_0001` | `candidate_source_sha256` | gate recorded |
|---|---|---|---|---|---|
| `positive_control/baseline` | `/usr/bin/python3 <staged>/solution.py …` | `ok` | 132 | `6bfd919e…` | 132 / `6bfd919e…` |
| `positive_control/pc` | `/usr/bin/python3 <staged>/solution.py …` | `ok` | 212 | `25de3e5d…` | 212 / `25de3e5d…` |

The digest in the last column read `d3c12b54…` when this table was written. The D-PC-7
edit of 2026-09-22 changed `pc/`'s bytes, so the current value — and the one every stored
record carries — is `25de3e5d…` (`positive_control/DEVIATIONS.md` keeps that change).

The byte-identical mirrors under `redesign/frozen_mirror/` give the same
`status`, the same `cut_edges` and the same `candidate_source_sha256`, so the
mirror and the frozen original are now interchangeable — which is what makes the
mirror redundant rather than wrong (it is **not** deleted here; it is another
workstream's directory).

Over the whole grid (2 candidates × 24 dev graphs, seed 1337, tau 30 s), **48/48**
of the gate's recorded rows reproduce exactly on `(status, cut_edges,
candidate_source_sha256)`, and a forced re-run of `gates/gate_runner.py` itself —
in a `/tmp` sandbox, so nothing under `gates/` is written — reproduces
`gates/verdict.dev.json` with `delta_gate`, `rho_gate`, `saturation_no_go` and
`counts` all identical and **zero** differing row fields. That file records the unbounded
control, so the re-run reaches it with `--pc positive_control/pc`; the default re-run
writes `gates/verdict.dev.pc_exchange_k10.json` and returns `ADMISSIBLE`. Either exit
code is the gate's own return, not an error: `gate_runner.main` returns
`{"ADMISSIBLE": 0, "PENDING": 2}.get(overall, 1)`.

## C\*(T1) coverage of §10

| §10 row | candidate(s) |
|---|---|
| `ok` but low | `c02_ok_low_baseline` |
| `ok` and high (PC) | `c01_ok_high_pc` |
| byte-different numerical tie pair | `c04_tie_a_pc_optimum`, `c05_tie_b_pc_complement` |
| `invalid` — wrong length | `c06_invalid_length` |
| `invalid` — element not 0/1 | `c07_invalid_element`, `c10_invalid_json_true` (JSON `true`; in Python `bool` subclasses `int`) |
| `invalid` — corrupt JSON | `c08_invalid_json` |
| `error` — raises | `c11_error_raises` (uncaught) and `c12_error_exit30` (§4's code 30) |
| `error` — non-determinism | `c13_error_non_deterministic` |
| `error` — writes no file | `c09_invalid_missing_file` (exit 0 → `invalid`, §6 rule 2) and `c14_error_no_file_nonzero` (exit 1 → `error`) — see DEVIATIONS D-T1-2 |
| `timeout` | `c19_timeout_process_group` |
| `error` — attempts the network | `c15_error_network_attempt` |
| beyond §10 | `c03` (legitimate zero), `c16` (§4's code 40, unconditional), `c17`/`c18` (input tampering), `c20` (environment probe), `c21` (arithmetic probe) |

**Note on "PC".** No definition of `PC` exists anywhere in this repository
(searched). `c01_ok_high_pc` is therefore a deterministic multi-start 1-flip
local search — the strongest fixed heuristic the frozen set could carry without
a definition to conform to. If `PC` names something specific, this candidate is
the thing to replace.

## Temporary graphs vs the frozen suite

`graphs_tmp/` holds task-owned temporary graphs used before `suite/` existed.
Every result in this file was re-run against the frozen suite once it appeared;
`conformance.py --suite-root graphs_tmp/tmp_suite --report <path>` reproduces the
temporary-graph run, and the report there records `graph_source: temporary` and
declines to compare rows against a table frozen for a different graph.
`graphs_tmp/float_tie_{A,B}/` are not a suite at all: they are the two
hand-constructed demonstration sets behind proof #6, laid out as `dev/` so the
frozen `aggregate` CLI addresses them unchanged.

## Reusing the existing instrument

* **D1 behaviour/environment split** (`a0/envelope/`): the Outcome keeps
  `interpreter` and `canonical_digest` as the two non-behaviour keys, so
  `behaviour_digest` applies to it unchanged. T1 adds no key the projection has
  to know about; the environment quantity it *would* have carried (`wall_ms`)
  is out of the canonical Outcome by D-T1-1.
* **D3 harness-owned outcome token**: T1's Outcome is the injected object; its
  `candidate_source_sha256`, `graph_sha256`, `theta` and
  `evaluator_source_sha256` are the join keys `a0/envelope/` binds.
* **Failure-stage table**: T1's `failure.kind` values map onto
  `a0/contract/selection/simpleloop.selection.json` by an explicit extension
  (D-T1-8), published by `e_star.py digest`.
* **Metering topology** (`a0/closure/…`, `a0/meter/`): untouched. This round is
  local computation with no model calls, so §8 never comes into play; the half of
  §4 that T1 does assert in that neighbourhood — no proxy variable and no
  credential reaches the candidate — is proven by `p5_child_environment`.
