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

## D-T1-3 — §4's `<entry>` is realized as `<interpreter> <entry>`, never as `execve` on the file

**Clause.** §4: `argv: <entry> --graph <abs graph.json> --out <abs partition.json> --seed <int>`.

**What was done.** `<entry>` is the candidate's program file. The harness
prepends an absolute launcher — its own `sys.executable`, or the list declared as
`exec` in the candidate's optional `candidate.json` — so the candidate's own
argument vector is precisely §4's list. A candidate that really is a
self-executing program declares `"exec": []` and is then `execve`'d directly.

**Why this is consistent with §4's literal text, not just a convenience.**

1. §4 mandates `PYTHONDONTWRITEBYTECODE=1` in the candidate's environment — a
   variable only a CPython process reads. §4 therefore presupposes the harness
   supplies the interpreter. Under `execve` of a `#!/usr/bin/env python3` script
   the harness supplies nothing; the *shebang* does, and it does so through PATH.
2. §4 forbids candidates depending on PATH, and §4 sets `PATH` to a minimal set.
   Reading (a) makes the harness's own ability to launch a candidate depend on
   that PATH (`env python3` must resolve), i.e. it puts PATH in the trust path of
   a clause that exists to take PATH out of it.
3. What the candidate sees in `sys.argv` under this reading is exactly
   `<entry> --graph … --out … --seed …` — §4 verbatim. The OS-level `argv[0]`
   is the launcher; the interface writes the *candidate's* argv, which is what
   the candidate can observe.

**Note.** Every invocation's full OS-level argv is recorded in
`<state>/invocations/**/invocation.json` and in the resources sidecar, so the
realization is auditable rather than implied. See D-T1-10 for why inferring
direct execution from a mode bit was not merely a stylistic choice but a defect.

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

## D-T1-10 — the launch was inferred from the entry's mode bit; it is now a function of bytes alone

**What was wrong.** `resolve_candidate` chose the launch by inspecting the entry's
mode and `#!` line:

```python
elif os.access(entry_path, os.X_OK) and entry_path.read_bytes()[:2] == b"#!":
    exec_prefix = []          # execve the file directly
else:
    exec_prefix = [sys.executable]
```

but `stage_candidate` runs a copy of the candidate that carries **content only**
(`{path, bytes, sha256}`), created with `write_bytes` and therefore mode `0644`.
So the decision was taken on one file and the execution performed on another. The
`X_OK` branch could therefore never succeed: it always produced

```
failure=candidate_entry_failed: PermissionError: [Errno 13] Permission denied:
  <state>/candidates/6bfd919ed73c49db/solution.py
```

**Why it is a real defect, not a rough edge.** The mode bit is not part of the
candidate's identity: §2 makes the *file's sha256* the data identity, and
`candidate_source_sha256` digests content only. A byte-identical candidate could
therefore be `ok` or `error` according to a bit no digest covers, and both
Outcomes would carry the *same* `candidate_source_sha256`. That is precisely the
class of silent, unreproducible disagreement (i)/(ii) exist to prevent.
`positive_control/{baseline,pc}/solution.py` were `chmod +x`ed after the gate ran
and E* stopped being able to measure the frozen candidates at all
(`redesign/DEVIATIONS.md` D-RD-1).

**What was done.**

* The inferred branch is **gone**. The default launch is
  `[sys.executable, <staged entry>, …]` — D-T1-3 — for every candidate,
  regardless of its mode or its first two bytes.
* `"exec": []` in `candidate.json` remains as an *explicit* opt-in for a
  candidate that really is a self-executing program. `stage_candidate` then
  copies the source file modes into the staged copy and checks the staged entry's
  executable bit, so a declared direct execution is either honoured or reported
  precisely, never as a bare `PermissionError`.

**Which reading of §4 this picks, and why.** Reading (b), "the harness supplies
the interpreter", for the three reasons in D-T1-3. Decisive additional evidence:
the gate's own recorded invocation, from the run whose verdict it froze, shows
the gate used exactly this path —

```
gates/e-star-state/dev-s3-baseline/resources.json:
  argv[0] = "/usr/bin/python3"
  argv[1] = ".../dev-s3-baseline/candidates/6bfd919ed73c49db/solution.py"
```

— and the gate's staged copy of that candidate is mode `0644` (mtime 17:03, i.e.
before the 17:08 `chmod`). The frozen verdicts were therefore produced by (b), so
(b) is the only choice that *restores* reproducibility; preserving the mode and
execve-ing (reading (a)) would have silently changed what is launched relative to
the frozen table, and would make a byte-identical candidate's verdict depend on an
untracked bit.

**Blast radius: none.** `conformance.expected.json` is byte-identical before and
after the fix — all 21 C\*(T1) verdicts are unchanged, because every member of
C\*(T1) is mode `0644` and never entered the broken branch. All 48 gate rows
(2 candidates × 24 dev graphs) reproduce exactly (`status`, `cut_edges`,
`candidate_source_sha256`), and a forced re-run of the gate in a `/tmp` sandbox
reproduces `verdict = NOT_ADMISSIBLE` with zero differing row fields — both with
`--pc positive_control/pc`, the control in force at the time.

**Corrected 2026-09-23 — which control that re-run measures.** The default re-run
no longer returns `NOT_ADMISSIBLE`. On 2026-09-23 the contract adopted
`positive_control/variants/pc_exchange_k10/` as the positive control
(`gates/gate_runner.py:73`, `positive_control/PC-REVISION.md`), and the default
run now writes `verdict = ADMISSIBLE`, exit 0, to
`gates/verdict.dev.pc_exchange_k10.json`. The `NOT_ADMISSIBLE` result above, and
the row-for-row agreement with the table that was released, belong to the
superseded control `positive_control/pc` alone. That control is still reachable,
and its table is still reproducible, with

```
python3 gates/gate_runner.py --set dev --pc positive_control/pc
```

whose verdict file is `gates/verdict.dev.json` (`NOT_ADMISSIBLE`, exit 1). The
staging defect and its fix are unchanged by this; only the control that fills the
`p_i` column of the table changed.

**Regression test.** `test_candidate_staging.py` (also wired in as conformance
probe `p7_candidate_staging`). It fails on the pre-fix evaluator, and its failure
is the defect in one line: the two byte-identical fixtures report the same
`candidate_source_sha256` while their `cut_edges` are `136` and `null`.

## D-T1-11 — `gates/values/*.json` was rewritten once, by accident, and restored

Not an interface deviation: a footprint to declare. To test the coordinator's
question about `gate_runner.py --force` I ran the gate in a `/tmp` sandbox whose
`gates/values/` was a **symlink** to the real one. `gate_runner.emit_values`
writes `HERE/values/<set>.<role>.json`, so the sandbox's run wrote through the
symlink into `a0/tasks/maxcut/gates/values/{dev.baseline,dev.positive-control}.json`.

* Content impact: none. `git diff` showed the only differing fields are
  `canonical_digest` and `evaluator_source_sha256`, which necessarily change when
  `e_star.py` is edited; all 24 rows' `cut_edges` and `candidate_source_sha256`
  were identical.
* Remediation: both files were restored with `git checkout --`, and `git status
  a0/tasks/maxcut/gates` is clean. Their content is byte-identical to what the
  gate owner committed; their **mtime is newer** (the restore rewrote them), which
  is the only residue.
* Re-done properly: the sandbox now holds a real *copy* of `values/`, and a second
  forced run touched nothing outside `/tmp`.

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
