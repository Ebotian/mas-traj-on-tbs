# KAPSO runtime adapter (A0.1 + A0.2)

Owner: the KAPSO workstream of `a0/`. Everything here is new work by that
workstream; the pinned KAPSO checkout `/home/ebt/kapso_ck/kapso` @ `7d99b152`
is read-only and is never installed into or written to (it is imported from
`src` through `PYTHONPATH`, with `PYTHONDONTWRITEBYTECODE=1` for every child).

## Verdict

| requirement | verdict | evidence |
|---|---|---|
| A0.1 evaluator conformance | **PASS** — 14/14 candidates | `runs/a0-01/a01/conformance.json` |
| `EID_r -> EID*` mapping | declared, recomputable **and enforced** | `runs/a0-01/a01/eid_mapping.json`, `registered_tree.json` |
| A0.2 score -> search contract | **PASS** — 14/14 checks, 5 scenarios | `runs/a0-01/a02/a02.json` |
| three traces + merged run stream | written; `trace_validate.py validate-run` exit 0 on both runs | `runs/a0-01/a01/traces/*`, `runs/a0-01/a02/traces/*` (incl. `*.all.jsonl`) |
| A0-wide contract tables adopted | `scalarization` + `failure_stage_mapping` byte-identical to the frozen declaration; A0.1 counts match SimpleLoop's | `contract/selection/kapso.selection.json`, `runs/a0-01/a01/conformance.json` |
| closure probe | **CONDITIONAL** — codex lane closed by one config key (executed, with control); default claude lane has no CLI sandbox | `runs/closure-01/closure.json` |
| full LLM-driven path | **VERIFIED for one round** (real codex session executed the registered evaluation; manifest became the score of record) | `runs/e2e-real/e2e_verification.json` |

An **independent** conformance harness (`a0/conformance/`, another workstream)
drove this adapter and reports `kapso PASS 14/14` with FailureStage counts that
now equal the runtime's own declaration.

## How to run

```bash
cd /home/ebt/rsi-dev/a0/runtimes/kapso
export PATH="$PWD/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1

# A0.1 + A0.2 in one run
.venv/bin/python -m a0_adapter run \
  --runtime kapso --task circle-packing \
  --run-id a0-01 --run-dir runs/a0-01 \
  --theta seed=1337,fidelity=full,fraction=1.0 \
  --budget T_wall_sec=3600,N_evaluatorCalls=500,concurrency=1 \
  --traces score,selection,resource

# A0.1 alone
.venv/bin/python -m a0_adapter conformance --runtime kapso \
  --run-id a01-01 --out runs/a01-01/conformance.json

# closure probe
.venv/bin/python -m a0_adapter closure-probe --runtime kapso \
  --run-dir runs/closure-01 --out runs/closure-01/closure.json
```

Exit codes follow `a0/contract/adapter_contract.md` §3.1 (0 ok, 2 usage, 3 EID
drift, 4 candidate integrity, 5 conformance failure, 6 closure, 7 budget, 8
nothing evaluable, 10 adapter bug). Paths and pinned inputs come from
`config/adapter.json`; `--config` overrides it. All run state lives below
`--run-dir` (`<run-dir>/state`), so a caller's invocation is self-contained and
nothing is written into a candidate worktree or into any tree a `git checkout`
can restore.

Dependencies: `uv venv --python 3.12`, KAPSO's core dependencies
(`config/kapso-core-reqs.txt`, extracted from its `pyproject.toml`) and
`jsonschema` for the trace validator. No KAPSO package install, so no build
artifacts land in the snapshot.

## Layout

| path | what it is |
|---|---|
| `ADAPTER.md` | the full run record (this text is copied into every `--run-dir` as `adapter.md`) |
| `a0_adapter/registered/kapso_eval.py` | the KAPSO-side execution of `E*`: identity + candidate gates, one `KAPSO_EVAL_MANIFEST` line, verdict-preserving exit codes |
| `a0_adapter/registered_tree.py` | builds the two-file registered evaluation tree and the `EID_r` fingerprint from `EID*` |
| `a0_adapter/runtime.py` | workspace, `EvaluationMaintainer` registration, candidate branches, frame runs |
| `a0_adapter/channels.py` | the reference (`E*`) and registered (KAPSO) evaluation channels |
| `a0_adapter/seams.py` | the three documented model-lane seams (+ a `patch` selector) |
| `a0_adapter/a01.py`, `a02.py`, `closure.py` | the three A0 checks |
| `a0_adapter/common.py` | `EID*` verification through the contract's own CLI, `C*` integrity, trace writer/validator, `EID_r` payloads, the A0-wide `failure_stage` table |
| `contract/selection/kapso.selection.json` | KAPSO's selection declaration: the A0-wide `scalarization` / `failure_stage_mapping` blocks (verbatim) + KAPSO's own `parent_policy=best` / tier-rule semantics |
| `config/mode.circle-packing.yaml` | KAPSO mode config: `parent_policy=best`, `fidelity.mode=off`, `max_change_requests=0`, front doors closed |
| `config/mode.circle-packing.codex.yaml` | the same settings with codex lanes, for the end-to-end attempt |
| `runs/a0-01/` | the canonical run: `adapter.md`, `a01/conformance.json`, `a02/a02.json`, traces, per-scenario workspaces |
| `runs/closure-01/` | closure report + raw `probe_egress.sh` JSON + lane-probe nonce files |
| `bin/smoke.py`, `bin/e2e_round.py` | build-time smoke test; the real-session end-to-end attempt |
| `runs/e2e-attempts/` | every real-session attempt's transcript + `attempts.json` |
| `runs/e2e-real/` | the completed real round: `e2e_verification.json`, workspace, session transcript |
| `bin/e2e_verify.py` | reconstructs the end-to-end evidence from a completed round |

## Key numbers

* `EID*` = `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`
  (re-verified by the contract's `verify` + `recompute` before every run).
* `EID_r` = `manifest:5495c22416cca0497121b8cfe4ccbcaa8ad9c470027b5fffa16bdaa66eda4639`
  = `manifest_fingerprint({a0_locator.json: 670ee167…, kapso_eval.py: a4be92de…})`.
  Identical in the A0.1 and A0.2 traces of a run and across runs, because the
  tree is generated from `EID*` alone (the per-run state root is an environment
  override, not part of the tree).
* Scores at `theta_E*`: `c01 2.4519205208433132`, `c03 2.4519205208433132`
  (bit-identical tie), `c04 2.451820520843313` (1e-4 below), `c02 0.25`,
  `c14 2.6e-05`; `c05`–`c08` exit 2 (`invalid`), `c09`–`c13` exit 3 (`error`).
* FailureStage, A0.1: `{evaluator_failed: 2, none: 5, resolve_failed: 1,
  timeout: 1, verify_failed: 5}` — the A0-wide table
  (`contract/selection/kapso.selection.json`), identical to SimpleLoop's, so the
  counts join across runtimes. A0.2: `{none: 19, evaluator_failed: 1,
  boundary_violation: 1}` over the merged run stream (the report also carries
  the score-trace-only variant). Before the adoption this adapter folded all
  nine non-`ok` candidates into `verify_failed`, which is what made the counts
  incomparable. `search_failed` / `comprehension_failed` /
  `mechanism_mismatch` are 0 (those strata belong to B0+).
* `selection.source_score_event_id` is populated and resolves in the run's
  merged stream. Selection declaration digest `c1a99365…`; the contract owner's
  frozen copy is still at `143bfc94…` and the only difference is the corrected
  tie-break-divergence wording (`differing_top_level_keys: ["selection"]`), so
  the contract owner needs to re-adopt it — the normative blocks match
  (`shared_blocks.*.identical == true`).
* `theta_E.extra` names two distinct identities: `registered_wrapper_sha256`
  (`781f54ee…`, the adapter's `kapso_eval.py`, the `EID_r` input) and
  `e_star_evaluator_source_sha256` (`5ae97ad9…`, E*'s own source digest as E*
  prints it). Join on the second for evaluator identity — an earlier revision
  published the wrapper digest under the ambiguous name `evaluator_source_sha256`
  (audit finding F1, fixed).

## BLOCKED / UNVERIFIED

* **The full LLM-driven path is verified for one round, not for the A0 suite.**
  The A0 rounds in `runs/a0-01` are seam-driven (ideation, implementation,
  judge). Separately, the real codex lane was driven for one round in
  `runs/e2e-real/`: the session installed frozen candidate `c04_near_tie`,
  executed the registered evaluation itself, and its manifest became the node's
  score of record, matching an independent `E*` run (`e2e_verification.json`,
  `verified_end_to_end`). What is *not* verified: a real **ideation** session
  choosing a change (the adapter supplied the candidate text), a real judge, and
  a long multi-round campaign. Attempts 1–2 (open-ended, first mechanical) were
  killed by the box at ~25 and ~13 min before committing; a repeat of the
  mechanical round (attempt 4, 900 s) died on the codex CLI's own deadline while
  the agent was still planning, so `runs/e2e-real2/e2e.json` is `not_verified`
  with `score: null`. All four transcripts are in `runs/e2e-attempts/`; the
  local codex endpoint is usable but flaky (`ERROR: Reconnecting... 1/5` in both
  real rounds), which is the reason one round landed and one did not.
* **A design leak the real session surfaced:** the registered wrapper honours
  `A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE=1` (used by the closure sentinel). A coding
  agent that reads `kapso_evaluation/kapso_eval.py` can find and set it, and
  attempt 1 did exactly that to measure a local candidate. It cannot affect any
  A0 claim (the study's runs never set it, and the manifest records
  `candidate_identity.in_frozen_set: false`), but the study should decide whether
  the sentinel override belongs in the shipped tree at all.
* **`selection.source_score_event_id` was reported as unsatisfiable and no
  longer is.** The adapter's earlier record (`a02.json.contract_defect`) claimed
  no conformant adapter could populate the field, because the validator resolved
  streams per file. The 2026-09-20 arbitration made the *run* the validation
  unit (`contract/README.md` §8 item 3, `adapter_contract.md` §6.3), and this
  adapter now writes the merged `traces/kapso.<run_id>.all.jsonl` and validates
  with `validate-run`; the field names a real score event of the run.
* **KAPSO defect found while making the adapter harness-drivable:** building a
  `GenericSearch` over a workspace that already has an untracked
  `.kapso/evaluation_registry.json` crashes, because `_initialize_repo_memory`
  stages `.kapso/repo_memory.json` but commits when *any* untracked file exists,
  so git exits 1 with "nothing added to commit but untracked files present"
  (`strategy/base.py:568-572`). It propagates out of the constructor, which is
  why the external harness saw exit 10 on a re-used run dir. The adapter now
  rebuilds `<run-dir>/workspace` before each run and commits only staged
  deltas (`runtime.py:_commit_staged`); the evidence is in
  `conformance.json.adapter_setup_log`. Resume is unaffected (`import_from_checkpoint`
  skips that code), so this hits fresh construction over an existing workspace.
* **Closure is CONDITIONAL, not closed.** The codex lane is closed by one
  config key and that is executed evidence with a positive control; KAPSO's
  *default* lane is `claude_code`, which has no CLI-level sandbox, and the only
  config-level move deletes Bash — closure by tool removal, which also removes
  the ability to run the registered evaluation. So a closed deployment must
  switch to the codex lane or run inside an external network cut. Details,
  including `unprobed_channels` and the two attempts that established nothing
  (a 240 s probe timeout, and a `git worktree` reuse bug on re-run, now fixed):
  `runs/closure-01/closure.json`, ADAPTER.md "Closure (probe result)".
* **`mechanism` is a single enum.** `mechanism_by_channel` carries the split:
  `front_doors`/`codex_lane` = `config`, `claude_lane`/`candidate_execution` =
  `external_network_isolation`.

## Snapshot hygiene

`git -C /home/ebt/kapso_ck/kapso status --porcelain` is empty (no tracked file
changed). The interpreter created gitignored `__pycache__/*.pyc` files under
`src/` (90 `.pyc`, 3.12 and 3.14 flavours, from this and other workstreams);
they are ignored build junk and the adapter adds none of its own.
