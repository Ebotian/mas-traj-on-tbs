# T1 deviations from `INTERFACE.md`

`INTERFACE.md` is the binding authority and was not edited. Everything below is
either (a) a place where the implementation had to choose a reading the
interface leaves open, (b) an additive extension, or (c) an explicit
reconciliation of two clauses that cannot both be satisfied literally. Nothing
here is silent: each entry names the clause, what was done, and why.

Owner: the T1 workstream. Files affected: `e_star.py`, `e_star_child.py`,
`candidates/`, `conformance.py`.

---

## D-T1-1 — `interpreted.wall_ms` is `null` in the canonical Outcome

**Clause.** §5's example Outcome contains `"interpreted": {"exit_code": 0, "wall_ms": 41}`.

**What was done.** The key is present, with the value `null`. The measured wall
clock is written to the resources sidecar (`--emit-resources`, and
`<state>/resources.json`), per run, as `resources.runs[].wall_ms`.

**Why.** §5 also freezes the canonical form and the Outcome is required to be a
*measurement record*. A wall-clock millisecond count is an execution-environment
quantity: it changes with machine load, with the interpreter build, and between
two runs of the same deterministic candidate. Keeping it in the canonical
Outcome makes byte-identical Outcomes impossible, which breaks the T1 brief's
proof #1 (cwd/PATH independence, compared as outcome bytes) and weakens §11's
reuse of `a0/envelope/`'s behaviour projection — `behaviour_digest` excludes the
execution environment (`interpreter`), and wall clock is the same kind of thing.

The proven plumbing evaluator takes exactly this route: it carries
`"resources": null` in its canonical Outcome and puts timings in a sidecar
(`a0/tasks/circle-packing/e_star.py:644-648`). T1 follows the template.

**Bearing on first principles.** None of (i)–(v) depends on `wall_ms`; §7 states
independently that candidate wall clock is diagnostics and "不进算法分".

---

## D-T1-2 — §6 rule 2 vs §10's "error (writes no file)"

**Clauses.** §6 rule 2: "`partition.json` 不存在 / JSON 非法 / schema 不符 / 长度不符 /
元素非 0/1 → `invalid`". §10's required coverage list includes an `error` flavour
described as "不写文件".

These cannot both hold for one candidate. §6 is the *frozen decision rule*; §10
is a coverage list ("至少覆盖").

**What was done.** Both readings are covered by two distinct candidates, so no
coverage intent is lost:

| candidate | behaviour | status | `failure.kind` | authority |
|---|---|---|---|---|
| `c09_invalid_missing_file` | exits 0, writes nothing | `invalid` | `missing_partition` | §6 rule 2 |
| `c14_error_no_file_nonzero` | exits 1, writes nothing | `error` | `candidate_crashed` | §4's "其他非零 → error" |

**Why.** A candidate that exits 0 while claiming success and produces no artifact
has produced a *format* violation, exactly as the frozen rule says; a candidate
that fails and produces no artifact has failed to execute, which §4 classifies
before §6 rule 2 is ever consulted. Rule 5 holds in both cases: neither
contributes a number.

---

## D-T1-3 — §4's `<entry>` is realized with the evaluator's own interpreter as a prefix

**Clause.** §4: `argv: <entry> --graph <abs graph.json> --out <abs partition.json> --seed <int>`.

**What was done.** `<entry>` is the candidate's program file. For a program that
is not a `#!`-executable, the harness prepends an absolute interpreter (its own
`sys.executable`, or a list declared as `exec` in the candidate's optional
`candidate.json`), so the candidate's `argv[1:]` is precisely §4's list. A file
that is executable *and* starts with `#!` is executed directly, with no prefix.

**Why.** `execve` on a bare `.py` file without a shebang fails. A shebang
(`#!/usr/bin/env python3`) would introduce a PATH dependency in the very ABI
whose §4 forbids depending on PATH, and an absolute-path shebang would not be
portable. Prepending the harness's own interpreter keeps the invocation
deterministic and PATH-independent, and it keeps the *frozen* part of the ABI —
the argument vector the candidate sees — exactly as written.

**Note.** This is why the observed child `argv[0]` is an interpreter path and
`argv[1]` is the candidate program. Recorded, not hidden: every invocation's
full argv is in `<state>/invocations/**/invocation.json` and in the resources
sidecar.

---

## D-T1-4 — E*'s own process exit codes add `4` for **timeout**

**Clause.** §4 freezes the *candidate's* exit-code table (0/20/30/40/other), and
§7 says a timeout is not an exit code. Neither clause fixes the *evaluator's* own
exit status.

**What was done.** `e_star.py` exits `0` = ok, `2` = invalid, `3` = error,
`4` = timeout. This is the plumbing evaluator's `0/2/3` shape with one value
appended for T1's fourth status. `digest` publishes the table so a caller never
has to read the source.

**Why.** Colouring a timeout as `3` (error) would make the evaluator's exit code
unable to distinguish "the candidate failed" from "the budget was enforced" —
the distinction §7 exists to make. The candidate-side table is untouched.

---

## D-T1-5 — additive CLI flags

Frozen CLI, implemented verbatim:

```
e_star.py evaluate --candidate <dir> --graph <graph.json> --seed <int> --timeout <s> --out <outcome.json> [--emit-resources <path>]
e_star.py aggregate --candidate <dir> --graph-set <dev|eval|calibration> --out <aggregate.json>
e_star.py digest
```

Optional additions, all defaulting to the frozen behaviour:

| flag | command | why it exists |
|---|---|---|
| `--state-dir` | both | the plumbing evaluator has it; run records must never be written inside a candidate tree |
| `--net-isolate` | `evaluate` | §4's "不注入网络" taken to its enforceable form: the candidate runs inside `unshare -rn`. Fail-closed if `unshare` is missing. Used to make the network row of C*(T1) topology-independent instead of host-dependent |
| `--suite-root` | `aggregate` | lets the same frozen CLI address the temporary graphs before `suite/` existed, and the demonstration sets under `graphs_tmp/` |
| `--emit-resources` | `aggregate` | symmetry with `evaluate` |
| `--value-only` | `digest` | prints just `evaluator_source_sha256`, for shell use |

`e_star_child.py` also has a standalone CLI (`--candidate --graph --out --seed
--timeout [--net-isolate] [--scratch]`) that performs one raw invocation and
prints the observation. It is an instrument for the probes, not part of the
evaluator's contract.

---

## D-T1-6 — additive keys in the Outcome and the aggregate

§5 lists required keys; it does not forbid more. Added, all derived from the
frozen inputs so the document stays recomputable:

* Outcome: `e_star_version`, `graph_family`, `determinism` (the §6 rule 4
  comparison, with both canonical hashes), `interpreted.exit_label`,
  `interpreted.exit_codes`, `interpreted.timed_out`,
  `interpreted.process_group_killed`.
* Aggregate: `evaluator_source_sha256`, `theta`, `graphs` (id/family/n/edges/
  sha256/manifest_match per graph), `scored_graphs`, `edges_total_scored`,
  `cut_edges_total`.

`score_exact` and `per_family_exact` use exactly §5's
`{"numerator","denominator"}` shape. When nothing was scored they are
`{"numerator": 0, "denominator": 0}` — *undefined*, deliberately not `0/1`,
because §6 rule 5 forbids representing a failure as a score of zero.

---

## D-T1-7 — nondeterminism is compared on canonical bytes, raw bytes only as a diagnostic

**Clause.** §6 rule 4: "`partition.json` 的规范字节必须逐字节相同".

**What was done.** The comparison is on the canonical bytes of the *parsed*
partition (§3's canonical form). Whether the raw files were also byte-identical
is recorded as `determinism.raw_bytes_identical`.

**Why.** The clause names the canonical bytes. A candidate that writes the same
assignment with different whitespace has produced the same measurement, and §6's
own validity list (rule 2) checks schema/length/elements, not byte-for-byte
canonicality. Comparing raw bytes would fail such a candidate for a defect §6
does not name. `c13_error_non_deterministic` is caught either way, since its
assignments genuinely differ.

---

## D-T1-8 — T1's `failure.kind` → failure-stage mapping is a declared extension

**Clause.** §11 requires a new `failure.kind` to map to
`a0/contract/selection/simpleloop.selection.json`'s frozen table or to be
declared an extension.

**What was done.** Declared, in `e_star.py`'s `FAILURE_STAGE_MAPPING` and
published by `digest`:

| T1 `failure.kind` | frozen `failure_stage` |
|---|---|
| `invalid_configuration` | `verify_failed` |
| `malformed_partition` | `verify_failed` |
| `missing_partition` | `verify_failed` |
| `candidate_entry_failed` | `resolve_failed` |
| `candidate_call_raised` | `evaluator_failed` |
| `candidate_crashed` | `evaluator_failed` |
| `candidate_refused` | `evaluator_failed` |
| `non_deterministic` | `verify_failed` |
| `runtime_budget_exceeded` | `timeout` |
| `input_tampered` | `evaluator_failed` |
| `graph_invalid` | `resolve_failed` |
| `harness_error` | `evaluator_failed` |

**Why an extension is needed.** The frozen table is keyed by the plumbing
evaluator's exit codes (`exit_2_invalid`, `exit_3_error_*`). T1's candidate exit
table is different (0/20/30/40/other) and T1 has a fourth status, so the keys
cannot be reused literally. The *values* are the frozen enum, unchanged.

---

## D-T1-9 — E* exits nonzero from `aggregate` when not every graph scored

**Clause.** Not addressed by `INTERFACE.md`.

**What was done.** `aggregate` exits with the most severe status it saw
(timeout > error > invalid > ok), using the same table as `evaluate`. The
aggregate document is written either way, with `counts` recording the truth.

**Why.** A uniform exit table means one shell idiom works for both commands. The
document, not the exit code, is the record.

---

## Considered and deliberately **not** changed

* **`PYTHONHASHSEED` is not set in the child environment.** §4's list is
  explicit and closed ("最小集"), and adding a variable would change the frozen
  environment. A candidate whose output depends on Python's per-process string
  hash randomization is non-deterministic by §6 rule 4 and *should* be caught,
  not accommodated. No member of C*(T1) depends on hash order.
* **`TMPDIR` / `LC_ALL` are not set.** Same reason. `LANG=C.UTF-8` is §4's, and
  it is what fixes the child's default text encoding.
* **`HTTPS_PROXY` / `CONNECT` metering topology (§8, `a0/meter/`) is out of
  scope for T1.** §8 governs the CEq ledger for the model lane; T1's round is
  local computation with no model calls, so nothing in `e_star.py` touches it.
  What T1 does assert in that neighbourhood is the *other* half of §4: no proxy
  variable reaches the candidate, proven by `p5_child_environment`.

---

## Known limitations (stated, not papered over)

1. **The child is not a security sandbox.** §4 specifies a subprocess with a
   fixed cwd and environment, not a container. A hostile candidate running as the
   same uid could, in principle, read `/proc/<ppid>/environ`, walk the harness's
   state root, or write outside its scratch directory. What §4 does guarantee —
   and what C*(T1) proves — is that *nothing is handed to it*: no proxy variable,
   no credential, no inherited environment. Isolation of network reachability is
   available by asking (`--net-isolate`, D-T1-5); general hostile-code isolation
   is not claimed here and would need the container/namespace work in
   `a0/closure/`.
2. **Attack on the *input* is detected, not prevented.** `c17_error_input_tampered`
   is reported as `input_tampered`; the score itself is never affected, because
   §6's recomputation always reads the harness's own frozen copy of the graph
   taken before the run. Preventing the write would need a read-only bind mount.
3. **`suite/manifest.json` is read defensively.** It is verified when present
   (each graph's `sha256`/`graph_sha256` must match), and E* refuses to aggregate
   when a manifest exists but carries no recognisable graph entries. If the suite
   owner changes the manifest's shape, that refusal is the thing to look at.
4. **The `--net-isolate` fail-closed path is exercised only by reading.** On this
   host `unshare` exists, so the "`unshare` absent → refuse" branch was verified by
   inspection, not by execution.
