# `a0/a1/` — the A1 harness: harness-owned evaluation, causal identity, budget, blocks

`a0/tasks/maxcut/INTERFACE.md` is the binding authority for the task, the
evaluator, the budget arithmetic and the traces. This directory is the **harness**
side of A1: it owns the evaluator, the metering boundary and the accounting, and
the two runtimes under test only *consume* what it publishes.

Deviations are in `DEVIATIONS.md`; the wiring report (what changed, where, with
which evidence) is in `WIRING-REPORT.md`.

## The one command

```bash
python3 a0/a1/verify.py            # every model-free claim, re-established; exit 0 = pass
python3 a0/a1/verify.py --list     # what it runs
```

The paid runs are **not** re-run by that command (they spend money). They are
`a0/a1/probes/live_probe.py`, and their recorded output is committed under
`a0/a1/evidence/`.

## What is here

| path | what it is |
|---|---|
| `eval_service.py` | **the harness-owned evaluation service**: the only process that runs `E*`, for `maxcut` or `circle-packing`. Writes the Outcome, binds it to an `a0/envelope` measurement token, books a row, then publishes |
| `t1_eid.py` / `T1-EID.json` / `T1.contract.json` | T1's frozen evaluator identity `EID*` = `cddfa64e…`, built by `a0/contract/evalcontract.py` from a spec (see D-A1-1) |
| `causal.py` | `CampaignID = (TaskID, BlockID, ArmID, ReplicateID)`, `CID` / `AID_r`, and the causal-role rule as an executable audit |
| `declaration.py` / `declarations/` | the CID and the two arms' `AID_r`, rebuilt from the repository, plus the audit verdict |
| `budget.py` | the `B_hard` enforcer: meter ledger + harness eval ledger + wall clock, fail-closed |
| `blocks.py` | the randomised complete block scheduler, with block-level invalidation on outage |
| `topology.py` | the closed topology: `unshare -rn` plus a unix-socket hop to the campaign's metered port |
| `meter_runner.py` | one metering listener per campaign and the model client; the proxy's own ledger verifier and per-call sidecar are read from here |
| `skeleton.py` | the campaign skeleton: identity + boundary + budget + one arm's run |
| `verify.py`, `tests/` | the re-runnable check entry point and the unit invariants |
| `probes/` | the three model-free probes and the paid live probe |
| `evidence/` | the committed output of every probe (probes write to `/tmp`; the committed copy is the evidence) |

## The boundary, in one picture

```
                        HARNESS (this directory)
  ┌──────────────────────────────────────────────────────────────┐
  │ meter_proxy (one port per campaign) ──plaintext/TLS──▶ provider│
  │        ▲                                                      │
  │        │ unix socket                                          │
  │ eval_service: runs E*, authors the Outcome, issues the token   │
  │ budget enforcer: reads the two ledgers + its own clock         │
  └────────┬─────────────────────────────────────────────────────┘
           │  unshare -rn: the only reachable peer is 127.0.0.1:<campaign port>
  ┌────────▼─────────────────────────────────────────────────────┐
  │ the runtime under test: proposes, consumes, selects            │
  └──────────────────────────────────────────────────────────────┘
```

## Reusing the existing instruments

* **`a0/envelope/`** — every response carries an OID measurement token bound to
  the candidate bytes, `EID*`, `theta_E`, the behaviour digest and the harness run
  id, and `behaviour_digest` is that module's projection, not a local copy.
* **`a0/contract/`** — T1's `EID*` is built by the contract owner's
  `evalcontract.py` from a spec; the run-level trace validator is unchanged and
  SimpleLoop's traces keep their frozen shape.
* **`a0/meter/`** — the ledger schema, the `CEq` formula and the one-port-per-
  campaign attribution are used as they are; `a0/a1/budget.py` only reads rows,
  and the probes call the meter's own `verify_ledger.py` so a ledger is checked by
  something other than its consumer.
* **`a0/a1/kapso_t1/`** — another workstream's T1 registered evaluation tree. Its
  identity is adopted into the KAPSO arm's `AID_r` (`runtime
  .registered_evaluation_tree`, `…_files`), recomputed from the tree's bytes here
  and cross-checked against that directory's `binding.json`; see D-A1-6.
