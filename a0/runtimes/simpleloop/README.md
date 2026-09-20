# `a0/runtimes/simpleloop` — the SimpleLoop substrate and its A0.1 / A0.2 checks

SimpleLoop is a member of `R_1` per `open_world_plan_review.typ:490` and the comparison baseline
for A1, so it is subject to `A0.1 ∧ A0.2` exactly like KAPSO / EvE / Loreley. (The handoff that
started this work listed only the three real runtimes; that omission is itself a finding — see
`A0_REPORT.md` §7.)

It implements the same frozen adapter contract as the real runtimes
(`a0/contract/adapter_contract.md`): one CLI, the same flags, the same exit-code table, the same
three traces, the same `EID_r -> EID*` declaration.

## What it is

```
a0_adapter/
  cli.py          the adapter CLI: run / conformance / closure-probe / a02-check / eidr
  runner.py       assembles one run: EID* checks, evaluator, solver, traces, run_meta.json, adapter.md
  eidmap.py       the EID_r -> EID* mapping, evalcontract verify/recompute, source re-hashing
  estareval.py    the evaluator lane: E* executed through its frozen CLI, cwd/PATH-independent
  candidates.py   C* loading + solution_sha256 integrity before any evaluation
  solvers.py      the pluggable solver lane (InjectedSolver = documented seam, CliSolver = codex/claude)
  loop.py         c_0 = baseline; c_{t+1} = Agent(c_t, H_t); c*_t = argmax_{i<=t} E(c_i)
  policy.py       the frozen scalarization fold and tie-break
  traces.py       the three jsonl traces
  conformance.py  A0.1
  a02check.py     A0.2, executed rather than asserted
  closure.py      the closure probe
policy/
  simpleloop.policy.json   FROZEN: scalarization, tie-break, selection rule, failure_stage mapping
  simpleloop.inject.json   FROZEN: the F_r in force only for --inject-scores runs
  proposed.a0.contract.simpleloop.selection.json   the proposal a0/contract adopted verbatim
solvers/main_run.json      the primary run's proposal sequence (seam input)
tools/recompute-eid-r      third-party recomputation of EID_r from declared inputs (no adapter code)
tools/check-frozen-conventions   checks the executed conventions against the frozen A0-wide copy
out/                       every run, trace, conformance and closure artifact produced here
tests/                     19 unit tests
HANDOFF_to_contract_owner.md   the two gaps it proposed (now adopted A0-wide) + one contract defect
A0_REPORT.md               verdicts per requirement, with the commands and outputs behind them
```

Nothing in the search machinery touches the network, and nothing outside `out/` is written.

`EID_r` is
`sha256("a0/simpleloop/eid_r/v1" + 0x00 + canonical_json(payload))` — the same domain-separated
construction `a0/contract/evalcontract.py` uses. The adapter publishes `(domain,
payload_canonical)` in its conformance document, so a third party recomputes the value with their
own sha256; `tools/recompute-eid-r` is a human-readable version of the same check. The A0
conformance runner performs that independent recomputation and reports it as PASS.

## The two things the protocol leaves open, and how they are frozen here

`open_world_plan_review.typ:608-614` fixes `c*_t = argmax_{i<=t} E(c_i)`. It does not say what
`argmax` does on a tie, and `plan:528`'s `F_r(E*) = scalar(E*)` does not say how E*'s multi-field
Outcome folds when `status != "ok"`. `a0/acceptance/DERIVATIONS.md` §4 flags both as gaps. Both are
frozen in `policy/simpleloop.policy.json` — before the runs, with the file's digest recomputable —
as:

```
scalar(c) = outcome.fields.sum_radii   iff outcome.status == "ok", else null
c*_t      = argmax over { c_i : i <= t and scalar(c_i) is not null } of scalar(c_i)
tie-break = smallest candidate_id by byte-wise comparison of its UTF-8 encoding
comparison = exact binary64; the A0.1 epsilon is NOT used in selection
```

`null` rather than `0.0` or `-inf` is deliberate: 9 of the 14 members of `C*` are `invalid` or
`error` and carry `sum_radii: null`, and `0.0` is precisely the false green the protocol already
names for EvE (`plan:551`). See `HANDOFF_to_contract_owner.md` §1-§2 for the proposed contract
text and for why the natural alternative tie-break is *wrong* here rather than merely different.

**Both decisions are now A0-wide, not SimpleLoop-local.** `a0/contract/adapter_contract.md` §5.3
records the frozen copy at `a0/contract/selection/simpleloop.selection.json` (schema
`a0.selection/v1`, status `frozen-a0-contract`, canonical digest
`ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd`) and requires the same
`scalarization` block and the same `E*` verdict → `failure_stage` table from all four runtimes.
The contract owner copied this workstream's blocks verbatim and re-checked them against the policy
the substrate actually executed; `tools/check-frozen-conventions` re-establishes that equivalence
after the fact, by execution rather than by reading:

```bash
.venv/bin/python tools/check-frozen-conventions --out out/conventions-recheck.json   # verdict PASS
```

It confirms the frozen digest, block-level byte equality of `scalarization`/`selection` between the
frozen copy, the authoritative `policy/simpleloop.policy.json` and the proposal, that all 8 verdict
rows of the frozen `failure_stage` table are reproduced by `traces.failure_stage_for` (including the
`other` fallback and `solver_lane_produced_no_proposal` → `search_failed`, the literal the loop
emits at its no-proposal site), the null gate and non-finite rejection in `policy.scalar_of`, the
order-invariance of the tie-break (with the rejected earliest-index rule shown to be
order-sensitive), and that the recomputed `EID_r` is the value the conformance handoff reports.

## Running it

```bash
cd /home/ebt/rsi-dev/a0/runtimes/simpleloop

# A0.1 — every member of C* against the reference table
.venv/bin/python -m a0_adapter conformance --run-dir out/a01

# A0.2 — the score -> search contract checks
.venv/bin/python -m a0_adapter a02-check --out out/a02/a02_checks.json

# one run of the loop (injected solver; see "solver lane" below)
.venv/bin/python -m a0_adapter run --solver injected \
    --solver-script solvers/main_run.json --run-dir out/main

# closure probe
.venv/bin/python -m a0_adapter closure-probe --out out/closure/closure.json

# the EID_r -> EID* mapping, recomputed
.venv/bin/python -m a0_adapter eidr

# does the executed policy still equal the A0-wide frozen copy in a0/contract? (verdict PASS)
.venv/bin/python tools/check-frozen-conventions --out out/conventions-recheck.json

# tests
.venv/bin/python -m pytest tests/ -q
```

Defaults: `--work-root /home/ebt/rsi-dev`, `--candidate-set
a0/tasks/circle-packing/C_STAR/manifest.json`, `--eid
a0/tasks/circle-packing/plumbing.EID.proposed.json` (+ `--eid-spec
plumbing.contract.proposed.json`), `--theta seed=1337,fidelity=full,fraction=1.0`,
`--fr a0/contract/fr/scalar.json`, `--budget T_wall_sec=3600,N_evaluatorCalls=200,concurrency=1`.
Relative `--run-dir` / `--out` / `--solver-script` paths resolve **inside this directory**;
external artifact paths resolve against `--work-root`. Nothing is written outside `out/`.

Exit codes are `a0/contract/adapter_contract.md` §3.1. The one worth knowing: **the adapter does
not exit 0 when the traces are invalid** — `run` prints the validator's real verdict for every
trace file it wrote and warns on stderr, rather than reporting success over an invalid trace.

`--run-id` and `--traces score,selection,resource` are honoured as the contract specifies; with
`--traces` omitted all three are written.

## The solver lane, and why A0.1/A0.2 are executable today

`solvers.py` exposes one interface with two implementations:

* `CliSolver` (`--solver codex|claude`) — the intended production lane: `c_{t+1} =
  Agent(c_t, H_t)` with a real agent CLI, which is the lane that carries the model endpoint and
  therefore the network posture. **VERIFIED end to end with `codex`** on 2026-09-20: the model
  produced a parseable `solution.py`, E* scored it, the loop's argmax selected it as champion,
  the run exited 0 and `validate-run` accepted it — `out/cli-lane/codex-live4/` (exit 0, E* `ok`,
  champion `codex_i001`, `sum_radii 2.5414213562373096` against a 0.25 baseline) and
  `out/cli-lane/codex-live3/` (exit 0, `2.6251746109048`). The a0/closure workstream
  independently measured the lane as shipped: a real model turn through exactly this argv
  returned rc=0 while the in-lane canary persisted `egress=BLOCKED`
  (`a0/closure/evidence/13_simpleloop_lane_closed.json`), with a `--sandbox danger-full-access`
  control on the same lane persisting `egress=OPEN`
  (`a0/closure/evidence/13b_simpleloop_lane_open.json`) — so that probe can tell the two postures
  apart. Two things this lane is *not*: (i) it was not always live — the dead `127.0.0.1:15722`
  was CC Switch's local proxy, and the earlier rounds are still recorded honestly rather than
  deleted (`out/cli-lane/codex/` exit 8 `search_failed` against the dead relay;
  `codex-live`/`codex-live2` cut by the wall-clock cap); (ii) **the `claude` branch remains
  UNVERIFIED** — `claude doctor` reports no active subscription login, the branch is implemented
  and reviewed but has never been observed producing a proposal, and no A0 verdict depends on it.
  The lane is fast to be wrong about and slow to run: a real round costs ~5 minutes of wall clock
  and ~59k tokens for one proposal (the token figure is the CLI's footer in the raw transcript
  `out/cli-lane/codex-live4/work/iter001/solver.stderr.txt`; it is not carried by any trace, and
  the `tokens_total` field the loop now writes on history rows postdates every recorded run), so
  `T_wall` at `scope: "iteration"` measures the whole iteration (proposal + evaluation), not just
  the E* call.
* `InjectedSolver` (`--solver injected --solver-script <json>`) — a **documented seam**:
  the proposal sequence is read from a JSON file instead of from a model. Seam citations:
  `a0_adapter/solvers.py` (`InjectedSolver.propose`) and `a0_adapter/loop.py` (the call site).
  Everything downstream of the proposal — the E* invocation, the `F_r` fold, the argmax, the
  traces — is byte-identical code for both lanes.

The seam is *only* the proposer. A C* member proposed by the seam is a byte copy whose sha256 is
re-checked against the manifest after the copy, so a script cannot smuggle in different bytes under
a C* id; a literal-solution proposal is hashed and evaluated exactly like any other candidate.

## Closure

`out/closure/closure.json`, verdict **closed**, mechanism `external_network_isolation`: the whole
measurement lane ran to completion under `unshare -rn` and produced the same champion and the same
scalar as on the host, while the same barrier was shown by `a0/env/checks/probe_egress.sh` to block
egress (`host` → `egress=OPEN`, `unshare-rn` → `egress=BLOCKED`), and a static scan finds no
network-capable import in `a0_adapter/*.py`. That verdict covers the *search machinery* only: with
`--solver codex|claude` the substrate inherits that CLI's network posture, so a closed deployment
must run the solver lane inside the same barrier (probe it with `--probe-cmd`). The separate
`a0/closure/` workstream probed that lane directly and found `codex exec --sandbox workspace-write`
(no `--search`) — exactly the argv `CliSolver._command` builds (`a0_adapter/solvers.py:281`) — to be
**egress=BLOCKED** by config, with a real model turn completing (rc=0) and an in-lane canary
persisting `egress=BLOCKED`, and with the same lane patched to `--sandbox danger-full-access`
persisting `egress=OPEN` as a control
(`a0/closure/evidence/13_simpleloop_lane_closed.json`, `13b_simpleloop_lane_open.json`). It also
warned that `unshare -rn` cuts a *host-local* model relay, so a barrier around the solver lane
must leave the endpoint reachable. See `A0_REPORT.md` §5.
