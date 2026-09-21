# The execution/load attestation — field specification

`a0/attestation/` · owner: execution/load attestation workstream · schema `a0.attestation/v1`

## 1. What problem this solves

`EID*` freezes the **intended** evaluator identity: five digests over the declared
source tree, dependency lock, data manifest, config and metric definition. It says
nothing about what a given run *executed*. Four concrete ways the two can come
apart, none of which change a single byte on disk:

| # | mechanism | why `EID*` cannot see it |
|---|---|---|
| 1 | the runtime imports a different module under the evaluator's name | `EID*` hashes a path, not a resolution |
| 2 | a stale/forged `__pycache__` entry the interpreter accepts | `evalcontract.py`'s `DEFAULT_EXCLUDES` skips `**/__pycache__/**` and `**/*.pyc` |
| 3 | a different native dependency (extension module, interpreter build) | the declared lock records package names, never loaded binaries |
| 4 | an environment variable changes behaviour | the contract specifies only the *child* environment, not the evaluator's own process |

`a0/STATUS.md` §8.2 records that this is not hypothetical: an earlier freeze picked
`scripts/local_eval.py` as "the evaluator" while the runtime actually loaded
`circle_packing_env/evaluate.py`, one ULP away.

The review's prescription — split the identity and produce an execution attestation per
real run — is what this directory implements.

## 2. The two identities and the third condition

```
EID_semantic   the frozen five-component EID* (664115e0…), recomputed at run time
               from the inputs actually present on disk
EID_execution  = H_domain("a0/attestation/v1/EID_execution", canonical_json(payload))
```

`payload` is the identity-bearing part of the attestation. Volatile facts — timings,
process ids, temporary directory names, audit event counts — are kept in
`observations`, **outside** the payload, so that two identical clean runs at the same
paths produce the *same* `EID_execution`. Verified: three runs of the same candidate
produced `bf2ba2ef7a0c2702fedfbf7f194eb49d4009d74a1c7e10cb7098bdb5de755005` with
byte-identical payloads (§7, command 6). An identity that changes per run would be a
run id, not an identity.

### Reconciliation with the review's split, and the coordinator's correction

The review wrote `EID_semantic = H(Source, Data, Config, Metric)` (four components) and
`EID_execution = H(EID_semantic, Dependencies, Runtime, LoadedArtifacts)`. This
implementation keeps the study's frozen five-component identity as `EID_semantic`,
because `DependencyLock` **as declared** is a frozen declaration like the other four;
what moves to the execution side is the dependency environment *as observed*. The
review's literal four-component digest is still carried, for traceability only, in
`payload.review_formula_semantic_4c`, computed with the contract's own
`component_digest` over `{EvaluatorSource, DataManifest, Config, MetricDefinition}`.
It is not the identity; the frozen `EID*` is.

The review's condition `EID_execution ⊨ EID_semantic` is not implementable as written:
the entailment symbol names a relation between two hashes, and no procedure can decide
it. The coordinator's correction is what this workstream implements, as three
separately reported verdicts:

- **Q1** — recomputing the attestation yields the declared `EID_execution`;
- **Q2** — its `EID_semantic` component equals the frozen value;
- **Q3** — *the declared identity is realized by this execution*: the declared source
  files are the artifacts that ran, nothing was loaded from outside the declared set,
  and the two invocation routes agree.

Q1 ∧ Q2 are **not** sufficient, and the demonstrations in §6 are the proof: all three
malicious attestations in `out/demo/` return `RECOMPUTES` and `SEMANTIC_MATCH` and are
caught only by Q3. That is the residual the review's `⊨` was reaching for, made
executable.

## 3. Field table

Every entry below is justified by what it makes observable and by what it would have to
change for the identity to change. "Obtainable here" means: measured on this host by the
code in this directory, not inferred.

### 3.1 Top level

| field | value | why it is there |
|---|---|---|
| `schema` | `a0.attestation/v1` | the document must be versioned before it is hashed into anything |
| `task` | `circle-packing-plumbing` | one attestation schema will serve other tasks later; the task id is not derivable from `EID*` alone |
| `eid_execution` | 64 hex | the per-run identity; the answer to Q1 |
| `eid_semantic`, `eid_semantic_components` | 64 hex ×6 | copied out of the payload so Q2 is answerable without parsing it; the verifier checks that the copy is the digest of the payload's components, so this is not a second source of truth |
| `declared_eid_star`, `frozen_eid_star` | `664115e0…` | the declared and the repo-pinned value, recorded so a mismatch between the two is visible rather than silently resolved |
| `payload` | object | the hashed identity material (§3.2–§3.9) |
| `observations` | object | everything true of this run but not part of its identity (§3.10) |

### 3.2 `payload.invocation` — what was asked for

| field | why |
|---|---|
| `mode` | `authoritative-script + capture-import`: two routes were used, and which one each number came from matters (§3.3) |
| `adapter_id` | null until an adapter is wired in (rest of §8); the whole point of per-run attestation is to attribute a run to a runtime |
| `evaluator_entry` | the file the caller named, repo-relative. **This is a declared input to the identity**: pointing at a different file must change `EID_execution`, and it does |
| `evaluator_entry_sha256` | that file's bytes at run time |
| `theta_e` | `seed, fidelity, fraction, n, runs, runtime_budget_ms, timeout_s` — the evaluator inputs. `EID*`'s `Config` freezes the *policy*; the per-run values are part of what was executed |
| `candidate_id` | which member of `C*` |
| `cwd` | repo-relative. `E*` claims cwd-independence; recording it lets a reviewer check the claim against a run instead of trusting the docstring |
| `env_overrides_for_the_evaluator` | env vars this wrapper set for the evaluator subprocesses (empty in the baseline). Configuration that changes behaviour must change the identity |

### 3.3 `payload.evaluator_execution` — what the two routes produced

| field | why |
|---|---|
| `routes_agree` | `false` when the authoritative CLI route (`python e_star.py evaluate …`, exactly what the adapters and the conformance runner invoke) and the capture route disagree. This is the alarm for "the imported module is not the script" — it fires for the stale-bytecode demonstration |
| `authoritative_route`, `capture_route` | `{returncode, status, objective_value, outcome_canonical_digest}` for each route, so a reader can see *which* route produced a number |
| `self_reported_evaluator_source_sha256` | what `E*` prints about itself (`5ae97ad9…` when honest). Recorded as evidence, never trusted: the verifier recomputes it from the declared file hashes |
| `self_reported_interpreter` | `E*`'s own version claim; independent of the captured runtime identity |
| `reference_comparison_applicable` / `_matches`, `reference_table_row_expected_{status,digest}` | the outcome compared against the frozen `E_STAR.json` row for this candidate and `theta_E`. Catches "the numbers are wrong" even when the source looks right |

`reference_comparison_applicable` is `false` for any `theta_E` other than the canonical
one, so a fast-tier run is not falsely flagged against the full-tier table.

### 3.4 `payload.candidate` — the candidate hash actually evaluated

| field | why |
|---|---|
| `id`, `solution_path`, `is_member_of_C_STAR` | which candidate, and whether it is under the study's control |
| `declared` | `{source: EID_INPUTS.DataManifest, sha256, size}` — the frozen record |
| `disk_sha256`, `disk_size` | the bytes at the path that was named |
| `executed_copy_sha256`, `executed_copy_path` | `E*` executes a private copy below its state root; this is the hash of *that* file, read back after the run. Without it, "the candidate that was evaluated" is an inference |
| `outcome_source_sha256` | the hash `E*` itself put in the Outcome |
| `checks` | `declared_equals_disk`, `declared_equals_outcome`, `disk_equals_executed_copy` — the three-way agreement, as booleans |
| `files[]` | every file of the candidate directory: `{path, sha256, size, declared_sha256, declared_match, opened_by_evaluator}`. `opened_by_evaluator` comes from the audit hook, so "which data files were actually read" is measured, not assumed: `solution.py` is `true`, `candidate.json` is `false` |

### 3.5 `payload.loaded_artifacts` — the core of the load attestation

`evaluator_sources[]` / `evaluator_child_sources[]` — one record per loaded module that
is, or stands in for, a declared evaluator source file (parent side and child side,
probed separately with the environment `E*` itself hands the child):

| field | why |
|---|---|
| `name`, `loader`, `origin_kind` | module name, the loader class that provided it, and whether the artifact is source / bytecode / extension / builtin / frozen |
| `origin`, `origin_absolute` | the path the import system actually resolved. Absolute because that *is* the evidence: the identity is host-relative by design, and demo 1 is precisely a case where the path is not the declared one |
| `file_sha256`, `file_size` | the bytes at that path, hashed now |
| `loaded_code_sha256` | `sha256(marshal.dumps(code_object))` of the code object the interpreter was about to execute, taken from the `exec` audit event. **This is the only artifact that is authoritative about what ran** — every other hash here is about what is on disk |
| `fresh_compile_sha256` | the same digest for compiling the current bytes at `origin` in this interpreter |
| `bytecode_matches_source` | `loaded_code_sha256 == fresh_compile_sha256`; `null` when the two interpreters differ and the comparison would be meaningless. `false` is the stale-bytecode alarm |
| `pyc_path`, `pyc_sha256`, `loaded_from_cache_path` | the `__pycache__` entry the loader reported, if any. Recorded even when the bytecode matches, because it is the artifact that *would* have to be forged |
| `declared_path`, `declared_sha256`, `declared_match` | the declared record for a file of this name, and whether the bytes agree |
| `is_entry`, `entry_is_the_declared_entry` | whether this module is the one the caller named, and whether it is also the declared file |
| `loaded_by_harness_before_hook` | whether the module was already imported when the audit hook was installed (a disclosure of the harness's own floor, see §5) |

`foreign_modules[]` — every loaded module whose `origin` is neither under the runtime's
own prefixes nor exactly a declared source file, as
`{name, origin, origin_kind, sha256, size, loaded_by_harness_before_hook}`. **No
directory is exempt, deliberately**: `a0/tasks/circle-packing/` is the evaluator's own
directory and is also full of `.venv/`, so a prefix rule would both hide a module
dropped next to `e_star.py` (found first on `sys.path`) and flood the table with
site-packages noise. Membership of `evaluator_sources` is likewise decided by the exact
declared file set, never by a directory. Empty in the baseline; `hashlib` in demo 1.

`shadowing_hazards[]` — a `sys.path` scan, independent of import order: any entry ahead
of the runtime's stdlib that holds a top-level module or package whose name collides
with a stdlib top-level name. This fires for demo 1 even if nothing had been imported
yet. Reported whether or not this run happened to use the shadowed name.

`declared_source_paths`, `declared_evaluator_entry` | the declared file set the two
lists above are checked against, carried so the verifier does not have to re-derive it.

`opens_by_category`, `opens_outside_all_known_roots` — every `open` event bucketed into
`runtime / evaluator_root / repo / candidate_set / state_dir / system_or_tmp / other`,
plus the literal paths that fall outside all known roots. This is the "loaded from
outside the declared source set" reading for *data*, complementing the module reading.

`child_argv_normalized` — the exact command `E*` spawns for its child, with the
`pid`-bearing run directory masked to `/pid<pid>`. The child's environment is captured
from the same `subprocess.Popen` audit event (see §3.7) rather than copied from
`e_star.py`'s source.

`harness_modules[]` — the capture harness's own files, named rather than silently
excluded.

### 3.6 `payload.runtime` — the interpreter that ran

| field | why |
|---|---|
| `executable`, `executable_realpath`, `executable_sha256`, `executable_size` | the interpreter binary, hashed. On this build it is 33,015,520 bytes and *is* the native dependency: `lib-dynload/` contains exactly one extension module (`_crypt`), which `E*` never loads (§5) |
| `version`, `version_full`, `implementation`, `hexversion`, `api_version` | 3.12.11 / CPython. `version_full` is kept because the *build* string carries the compiler (`Clang 20.1.4`) that decides float behaviour |
| `cache_tag`, `bytecode_magic_hex` | `cpython-312` / `cb0d0d0a`. A `.pyc` is only loadable by a matching magic; recording it makes cross-build bytecode comparison a check rather than a guess |
| `sys_prefix`, `sys_base_prefix` | the venv and the uv-managed base interpreter. Also the allowlist that defines "the runtime's own trees" in §3.5 |
| `flags` | `optimize`, `dont_write_bytecode`, `no_user_site`, `no_site`, `ignore_environment`, `isolated`, `safe_path`, `utf8_mode`, `hash_randomization`, `dev_mode`, `bytes_warning`, `verbose`. `-O` drops assertions; `-B` changes whether bytecode is written at all; these are per-process and invisible to `EID*` |
| `sys_path` | the resolved search order. It is the input to the shadowing question and to any "why did this module come from there" |
| `platform` | `sysname`, `release`, `machine`. `nodename` is deliberately `null`: the hostname identifies a machine without adding anything an attestation needs |

### 3.7 `payload.dependencies` — the dependency environment, as recomputable here

| field | why |
|---|---|
| `kind` | `host_venv`: the honest statement that `E*` runs on the host, under a pinned venv |
| `container_image` | `null`, with the reason carried in the document. **No container-image digest exists for this invocation and none is fabricated**: the adapters and the conformance runner invoke `E*` on the host, and the closure network (`a0pc-internal`, `a0pc-proxy`) exists to confine *agent* traffic, not the evaluator. A containerized invocation must pass the image id in |
| `interpreter_sha256`, `interpreter_size` | the binary again, here because it is the dependency that dominates |
| `pyvenv_cfg`, `pyvenv_cfg_content` | the venv's `pyvenv.cfg`, hashed and parsed (`home`, `implementation`, `uv`, `version_info`, `include-system-site-packages=false`). This is what makes the *interpreter selection* recomputable from the document |
| `distributions[]` | `*.dist-info` directories under the runtime's site-packages, with the `METADATA` hash and the site-packages path. Read as files, never imported, so this reflects the evaluator's environment rather than the tool's. Baseline: `pip-24.3.1`. Declared `DependencyLock` records `third_party_packages: []` — the observed set is not empty, but `pip` appears in no loaded-module record, so it cannot have affected the result. Recorded as a benign declared-vs-observed difference rather than smoothed over |
| `declared_lock` | the declared lock file with `declared_sha256`, `live_sha256`, `matches` — the declared dependency identity checked against the bytes on disk |
| `native_dependencies[]`, `native_dependency_digest` | every loaded module whose `origin_kind` is `extension`, with its `.so` path, hash and size. **Empty on this host, and that is a measurement, not a placeholder**: this CPython build is statically linked except for `_crypt`, which `E*` does not import. The counterexample "a different native dependency" therefore has almost no surface here — the native dependency is the interpreter binary, which is hashed in full |
| `environment_digest` | `H_domain` over `{interpreter_sha256, version, bytecode_magic, pyvenv_cfg, pyvenv_cfg_content, native_dependency_digest, container_image}`. This is the "environment digest that is actually recomputable here": every input is either a file hash in the document or a parsed config, so a third party can recompute it on this host without any registry or image |

### 3.8 `payload.environment` — the variables that can change behaviour

| field | why |
|---|---|
| `allowlist` | the 34 names that can influence an interpreter's behaviour, recorded as a fixed list. The full `environ` is **not** dumped: it would put unrelated secrets into a document that is meant to be published alongside results. A defensive redaction (`sk-`, `ghp_`, `AIza`, `xoxb-`, `Bearer `) is applied to every captured value |
| `values` | for each name, its value or an explicit `null` — "unset" and "empty" must be distinguishable, because `PYTHONHASHSEED=""` and an unset `PYTHONHASHSEED` are different requests. Baseline: only `HOME` and `PATH` are set |
| `behaviour_affecting_set` | the subset that is set to something non-empty *and* is interpreter-relevant. This is the honest statement of exposure: in the baseline, the evaluator's own process sees a host `PATH` and `HOME` that the contract does not specify |
| `unspecified_by_contract` | a sentence making it explicit that `E*`'s **own** environment is unspecified by the frozen `Config`, which constrains only the child. Without this field a reader would reasonably assume the whole environment was declared |
| `child_environment` | the environment `E*` hands to its child, captured from the `subprocess.Popen` audit event (`PATH=""`, `PYTHONPATH=""`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, private `HOME`/`TMPDIR`). Captured, not transcribed from the evaluator's source, so a drift between the contract's policy and `e_star.py`'s code would show up here |
| `child_policy_checks`, `child_policy_ok` | each declared policy value compared against the captured one |
| `child_probe` | which module the child-side capture imported, and that the override was applied |

### 3.9 `payload.semantic` fields

`eid_semantic`, `eid_semantic_components`, `declared_component_digests`,
`eid_semantic_declared`, `eid_semantic_matches_declared`, `declared_eid_star_frozen`,
`review_formula_semantic_4c` — the semantic identity recomputed at run time by the
contract owner's own `a0/contract/evalcontract.py`, plus the declared values it is
compared against. Both the live and the declared digests are carried so that a
disagreement is visible in the document itself, not only in the verifier's report.

### 3.10 `observations` — true of this run, outside the identity

`generated_at_utc`, `generated_by`, `attestation_tool_interpreter` and whether it
matches the captured interpreter, `scratch_dir`, `state_root`, the two route records
with their stdout/stderr, the child probe document, `module_count`,
`module_index_digest` (all loaded modules — deliberately *not* in the identity: the
lazy import set is an interpreter implementation detail), 
`modules_loaded_by_the_evaluator` (the 34 modules this run pulled in),
`exec_event_count`, `open_event_count`, `import_event_count`, `socket_events`,
`truncated`, and the declared/live component digests with
`components_match_declared`.

`socket_events` is empty in every baseline and demonstration run: no network during
evaluation. The verifier gates on it.

## 4. Fields that are deliberately *not* included

| candidate field | why not |
|---|---|
| hostname, boot id, MAC addresses | identify a machine without constraining an execution; `nodename` is explicitly `null` |
| kernel version, `/proc/cpuinfo`, GPU state | no mechanism was found by which they change `E*`'s verdict for `C*`; if one is found, it belongs here with a demonstration |
| timestamps of the run inside the payload | makes `EID_execution` a run id (see §2) |
| the full environment | secrets; the allowlist is the defensible unit |
| per-`import` counts, per-`open` counts | interpreter-version and laziness dependent; they live in `observations` |
| a container image digest | not obtainable for this invocation (see §3.7). Stated, not fabricated |

## 5. What this attestation cannot catch

Written as limits, not caveats:

1. **The harness is trusted software.** `_bootstrap.py` installs the audit hook and
   writes the capture. A hostile evaluator that installs its own hook first, or that
   forks before the hook is installed, is outside what this can see. The mitigation
   that would close this — running the attestation from outside as a debugger or an
   `LD_PRELOAD` shim — is not implemented here.
2. **Namespace hygiene is partial.** The harness keeps `hashlib`, `argparse` and `json`
   unbound until the evaluator imports them, and loads its own copies from
   `sys.base_prefix` under private names. It still imports `importlib.util`,
   `marshal`, `os`, `sys` and `time` itself, so those names are pre-bound; a shadow of
   one of them would be reported as a `shadowing_hazard` (configuration) rather than as
   a `foreign_module` (fact). The `harness_floor` count and
   `loaded_by_harness_before_hook` flags disclose exactly which modules are affected.
3. **`bytecode_matches_source` is `null` when the comparison would be meaningless.**
   `fresh_compile_sha256` is computed by the tool's interpreter; if someone runs the
   tool with a different build than the evaluator used, the field degrades to `null`
   and the verifier says `??`, not `ok`. That case is not exercised here because the
   tool always launches the evaluator with its own `sys.executable`.
4. **Timing-sensitive verdicts can make the two routes disagree legitimately.** `E*`
   has a p50 runtime-budget check; a candidate near the 250 ms boundary could produce
   different outcomes on the two routes for reasons that are not an attack. The
   verifier reports `routes_agree == false` as a failure either way, which is the safe
   direction but is a false-positive source.
5. **`EID_execution` is host-relative.** Absolute paths in `origin_absolute`, the
   interpreter path and the `sys_path` are part of the payload on purpose — the
   question "which artifact ran" has no path-free answer — so the same logical
   execution on another machine yields a different `EID_execution`. Reproducibility is
   guaranteed across runs at the same paths (verified), not across hosts.
6. **One candidate per attestation.** `EID_execution` covers one `E*` invocation. A
   batch of 14 candidates yields 14 execution identities; nothing here aggregates them,
   and no claim is made about the ordering or completeness of a batch.
7. **`E*` is not modified, so the child process is attested by a probe, not by
   observation.** The child side (`e_star_child.py`) is captured by importing it under
   the environment `E*` itself hands the child — captured from the `Popen` audit event.
   The actual child process is *not* instrumented; if it loaded something different
   from the probe (for example because it runs with a different `cwd`), this would not
   be seen. The probe's `cwd` is set from the captured `Popen` event to reduce that gap,
   but it is a probe.
8. **This is self-attestation, not third-party attestation.** The producer runs in the
   same lane as the evaluator, so a producer that is itself compromised can emit a
   consistent lie: a payload whose `foreign_modules` is empty while the process that
   produced the numbers loaded something else. What the verifier independently
   recomputes — `EID_semantic` from the live tree, `E*`'s self-reported digest from the
   declared file hashes, the outcome against the frozen reference row — narrows the
   lie's room but does not eliminate it. The structural fix is to move production out
   of the lane: the conformance runner (or an outside observer) should run the
   capture, and the lane should be unable to write to the attestation it is judged by.
   That is a wiring decision, not something this directory can enforce against itself.

## 6. The demonstrations

Built and run by `demo.py`; evidence in `out/demo/EVIDENCE.json` and the per-demo
`attestation.*.json` / `verdict.*.json`. The candidate is `c05_overlapping` in every
case: declared `invalid` because of one real overlap, with a nominal `sum_radii` of
2.4519205208433132 — exactly equal to the best valid candidate, which is why it is in
`C*` as the "nominal value" trap.

The declared `E*` source (`a0/tasks/circle-packing/e_star.py`) was hashed before and
after the whole demonstration run: **unchanged**, `2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567`.

| | d0 baseline | d1 shadow module | d2 stale bytecode | d3 other file |
|---|---|---|---|---|
| mechanism | none | `PYTHONPATH` shadows `hashlib` | forged `__pycache__` accepted by the timestamp check | a patched `e_star.py` executed under the same name |
| declared source on disk | unchanged | **unchanged** | **unchanged** (byte-identical copy) | **unchanged** |
| `E*` self-reported source hash | frozen `5ae97ad9…` | **falsified**, matches the demo's own prediction | frozen `5ae97ad9…` | different |
| code object actually executed | = source | = source | **≠ source** (predicted hash matched) | = the patched source (predicted hash matched) |
| `Q1` recomputes | yes | yes | yes | yes |
| `Q2` semantic match | yes | yes | yes | yes |
| `Q3` realization | **REALIZED** | **NOT_REALIZED** | **NOT_REALIZED** | **NOT_REALIZED** |
| authoritative route verdict | `invalid` | `invalid` | `invalid` | **`ok`** |
| capture route verdict | `invalid` | `invalid` | **`ok` 2.4519205208433132** | **`ok` 2.4519205208433132** |
| detectors that fired | — | foreign module, shadowing hazard, self-report mismatch, reference mismatch | routes disagree, foreign module, bytecode ≠ source, self-report contradicted | foreign module, source hash ≠ declared, self-report ≠ frozen, reference mismatch |

The last three rows are the point: on the route that executed the substituted artifact,
d2 and d3 report a candidate the study classifies as `invalid` as `ok` with the best
nominal score — the false green this study exists to detect — while `EID*` is bit-identical
in all four columns. (d2's *authoritative* route, which runs the real frozen source as a
script, still says `invalid`; the disagreement between the two routes is itself one of the
detectors, and the warning is that an integration which imports the evaluator rather than
executing it would see only the `ok`.)

Each demo also *predicts* the digest it will produce and the evidence records whether
the prediction held (`prediction_checks` in `EVIDENCE.json`): for d2, the code object's
marshal digest was computed from the patched source before the run and matched the
`loaded_code_sha256` the capture recorded. The demonstrations are therefore
"the forgery produced exactly this artifact", not "something failed".

The native-dependency counterexample (3) is **not** demonstrated, for a measured reason:
no extension module is loaded at all on this build, so there is no native artifact to
swap. `native_dependencies` is recorded empty with its digest, and the interpreter
binary (33 MB) is hashed in full.

## 7. Commands a third party can run

All commands are run from the repository root, with the study's pinned interpreter.

```sh
PY=a0/tasks/circle-packing/.venv/bin/python

# 1. produce an attestation for a real E* invocation (→ out/attestation.<id>.full.json)
$PY a0/attestation/attest.py --candidate a0/tasks/circle-packing/C_STAR/c01_good_hex

# 2. verify it: Q1 / Q2 / Q3, with independent recomputation of EID_semantic
$PY a0/attestation/verify_attestation.py \
    --attestation a0/attestation/out/attestation.c01_good_hex.full.json \
    --repo-root . --json-out a0/attestation/out/verdict.c01_good_hex.json

# 3. the self-test: canonicalizer agreement, the verifier's independent
#    reimplementation of E*'s self-report and of the EID* combination step, and
#    four injected faults that must each be rejected
$PY a0/attestation/selftest.py

# 4. build and run all four demonstrations, then verify each
$PY a0/attestation/demo.py

# 5. a clean run against a *different* candidate (the other baseline)
$PY a0/attestation/attest.py --candidate a0/tasks/circle-packing/C_STAR/c05_overlapping
$PY a0/attestation/verify_attestation.py \
    --attestation a0/attestation/out/attestation.c05_overlapping.full.json --repo-root .

# 6. determinism: the same run twice must yield the same EID_execution
$PY a0/attestation/attest.py --candidate a0/tasks/circle-packing/C_STAR/c01_good_hex \
    --attestation-out a0/attestation/out/determinism.a.json
$PY a0/attestation/attest.py --candidate a0/tasks/circle-packing/C_STAR/c01_good_hex \
    --attestation-out a0/attestation/out/determinism.b.json
$PY -c "import json;a=json.load(open('a0/attestation/out/determinism.a.json'));\
b=json.load(open('a0/attestation/out/determinism.b.json'));\
print(a['eid_execution']);print(b['eid_execution']);print(a['payload']==b['payload'])"
```

Verifier exit codes: `0` all three verdicts good, `1` does not recompute, `2` semantic
mismatch, `3` not realized, `4` malformed attestation.

## 8. What wiring remains for every run to emit an attestation

The four adapters call `E*` directly; nothing forces them through `attest.py`. This is a
**proposal**, not a change made here — `a0/runtimes/**` belongs to other workstreams and
was not touched. The call sites are named below as read from source (not executed in
this session), so the cost estimate is grounded rather than guessed.

### Which mechanisms are live today

All four invoke `E*` as a **script** (`<python> e_star.py evaluate …`), never as an
import, and the invocation environments differ:

| adapter | `E*` call site | environment passed to `E*` | `PYTHONPATH` reaches `E*`? | stale `.pyc` loadable? |
|---|---|---|---|---|
| SimpleLoop | `a0/runtimes/simpleloop/a0_adapter/estareval.py:219` (`subprocess.run` at 246/251) | constructed minimal env (`PATH=/usr/bin:/bin`, `HOME`, `LANG`, `LC_ALL`, `TMPDIR`, `PYTHONDONTWRITEBYTECODE=1`) | no | no (script route) |
| KAPSO | `a0/runtimes/kapso/a0_adapter/channels.py:113` | `dict(os.environ)` + `PYTHONDONTWRITEBYTECODE=1` | **yes** | no (script route) |
| EvE | `a0/runtimes/eve/a0_adapter/common.py:419` (`subprocess.run` at 444, no `env=` argument) | inherited, i.e. the adapter's whole environment | **yes** | no (script route) |
| Loreley | `a0/runtimes/loreley/src/a0_adapter/runtime.py:325` (`subprocess.run` at 342) | `{PATH: "", HOME, TMPDIR, PYTHONDONTWRITEBYTECODE}` | no | no (script route) |

Two consequences worth stating plainly rather than leaving to inference:

- **Demonstration d1 is live for KAPSO and EvE today.** A `PYTHONPATH` in the
  adapter's own environment propagates into `E*`'s process, where a module named after
  a stdlib module shadows the real one — and `E*`'s self-reported identity hash becomes
  whatever that module says. Both already set `PYTHONDONTWRITEBYTECODE`, which is why
  the route is closed for d2/d3 but not for d1.
- **Demonstration d2 is not live for any of the four adapters**, because running a
  script never consults `__pycache__`. It becomes live the moment any integration
  imports the evaluator or runs it with `-m` — which is exactly what this wrapper's
  capture route does. d3 (a different file under the same name, or a copy in another
  directory) needs no misconfiguration beyond a wrong path, and is the incident that
  motivated this workstream.

### Cost of wiring

1. **Wrap the call site, not the evaluator.** Each site above becomes a call to
   `attest.py --candidate … --seed … --fidelity … --fraction … --adapter <id>
   --attestation-out <run-dir>/…`. The wrapper keeps the same CLI surface and writes
   the same Outcome, so the adapter's parsing does not change. One option change per
   site; the two adapters that pass an explicit env must forward it with `--env` so the
   attestation records what it actually is.
2. **One attestation per evaluation, named by candidate and theta.** `EID_execution` is
   per invocation. The trace schema needs a place for it: an optional `attestation`
   object on the per-run record in `a0/contract/trace_schema.*`, carrying
   `{eid_execution, eid_semantic, attestation_path, verdict}`. That is a contract
   change and belongs to the contract owner.
3. **A run register.** `--declared-eid-execution` exists so a verifier can compare
   against a previously admitted value; nothing currently stores those values. A
   per-lane `runs.jsonl` would turn "recomputes" into "recomputes to the value we
   admitted".
4. **Fail-closed at the conformance layer.** `a0/conformance/conformance.py` should
   treat `Q3 != REALIZED` the way it treats a candidate-identity mismatch: the row is
   not compared, it is failed. With `--adapter` supplied by the runner, a missing or
   forged attestation cannot pass by omission.
5. **Budget.** One attestation costs three interpreter launches (the authoritative CLI,
   the capture import, the child probe) plus hashing ~110 modules and one 33 MB binary;
   wall clock is dominated by the two full evaluations of the candidate. A
   `--no-authority-route` mode would halve it at the cost of the cross-route check, and
   would have to record that it did so.
6. **Not needed:** changes to `e_star.py`, `e_star_child.py` or anything under
   `a0/tasks/`. The wrapper observes through the audit hook only.

## 9. Side effects and disclosures

- **`a0/tasks/circle-packing/__pycache__/` was created by this workstream's runs**
  (`e_star.cpython-312.pyc` at 15:14, `e_star_child.cpython-312.pyc` at 15:17). The
  capture route imports the evaluator as a module, which is what makes stale-bytecode
  hazards visible at all; CPython then caches bytecode there. The directory is
  gitignored, the study's own pipeline executes `E*` as a script (which neither writes
  nor reads it, and the frozen `E*` sets `PYTHONDONTWRITEBYTECODE=1` for its child), and
  the entries were verified to match their sources
  (`bytecode_matches_source: true`). They were left in place rather than deleted
  because deleting another workstream's cache is a bigger intervention than disclosing
  it; a future import-style invocation would silently use them, which is precisely the
  hazard d2 demonstrates.
- No container was started, stopped or inspected. `adapdc-catalog-postgres-1` and the
  `a0pc-*` closure containers were not touched.
- Nothing outside `a0/attestation/**` was written. `a0/STATUS.md` was not edited.
- One model-free process only: no model calls, so spend for this workstream is $0.
  The DeepSeek key was never read, printed or written.
