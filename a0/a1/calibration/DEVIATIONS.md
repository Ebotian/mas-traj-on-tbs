# `a0/a1/calibration/DEVIATIONS.md` — every place the pilot departed from a frozen document

`a0/tasks/maxcut/INTERFACE.md` is the interface authority and
`a0/a1/calibration/PILOT-PROCEDURE.md` is this directory's own frozen procedure. Nothing
below is silent, and **none of it is a relaxation**: no gate, no threshold, no budget
coordinate and no validity condition V1–V7 was moved. Where a frozen clause could not be
applied as written, it is named here and the measurement is reported as a labelled
supplement — the procedure was not edited, because editing it would break the ordering
that the freeze exists to protect (procedure §0: `f` may not be tuned by eyeballing
results, and every artifact records the procedure's sha256).

Frozen digests this file is written against:

| artifact | sha256 |
|---|---|
| `PILOT-PROCEDURE.md` | `68af13211ab88aad1fe4b3ca40d29cf00e73f2139d78ae5b26fe8fc47a0e3fa2` |
| `pilot_procedure.json` | as recorded in `B_hard.json` |
| `a0/tasks/maxcut/suite/manifest.json` | as recorded in `B_hard.json` |
| `a0/tasks/maxcut/e_star.py` | `f67ecd41bd769e41e57e1812ce60d544b6894071cd7849bccaa83a2163b614f6` |
| `evaluator_source_sha256` (E*) | `dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00` |
| `EID*` (`a0/a1/T1-EID.json`) | `7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec` |

---

## D-CAL-1 — the KAPSO unit driver is authored here

**What.** `pilot.py kapso-inner` drives the KAPSO arm, built on `a0/a1/kapso_t1/`'s
`runtime_t1`, because that workstream's probe hardcodes `GRAPH_ID = G_dev_0001` and offers
no graph argument (its README calls the per-node graph "the probe's choice, not a campaign
policy").

**Why.** `INTERFACE.md` §9 requires the pilot to run on the **calibration** graphs. This
workstream owns only its own directory, so the driver lives here and reads `kapso_t1`
unchanged.

---

## D-CAL-2 — the KAPSO unit rebases the adapter's `state_root`

**What.** `dataclasses.replace(config, state_root=…)` points the adapter's tree at the
pilot's own work directory.

**Why.** The adapter would otherwise install the registered tree under
`a0/a1/kapso_t1/state/`, i.e. write inside another workstream's directory.

---

## D-CAL-3 — the KAPSO inner does not memoise the second round's model call

**What.** The `kapso_t1` probe memoises round 2's ideation call (one call instead of two,
to save cents). The pilot does not.

**Why.** A rate measurement must observe the arm's actual call pattern; memoising would
understate `q_r` by roughly half. The consequence is visible in the ledger: **48 rows for
24 units**, exactly two per unit.

---

## D-CAL-4 — the published evidence is a reduction

**What.** Score-bearing keys (`cut_edges`, `cut_fraction` in the Outcomes;
`true_value`, `handed_value` in the harness ledger) are removed from every published file;
arm stdout/stderr are published as `sha256` + byte length + exit code.

**Why.** Procedure §0/§8: the pilot's algorithmic results are not used, reported **or
published**, so that no later reader can tune the budget by eyeballing a calibration score.
The removal is auditable: `evidence/INDEX.json` records each raw file's sha256 (taken in
the run directory, before the reduction) next to the reduced file's. `calibration/verify.py`
re-checks structurally that no published file uses an objective value as data
(131 files, 0 findings).

---

## D-CAL-5 — the pilot runs without a harness-owned preflight for the arms' identity

**What.** The driver reproduces the arms' identity checks by running `a0/a1/t1_eid.py
check` and records the result per campaign (`frozen_identity.frozen_identity_consistent`).

**Why.** `a0/a1/skeleton.py`'s preflight checks *one* instance's sha and the `CID`
factors, not the arms' evaluator-identity agreement; adding that check to the skeleton is
another directory's change. Reported here, not made. In this run the check is `true` for
both arms and the campaigns reached the harness.

---

## D-CAL-6 — a small, labelled metering proof outside the pilot's workload

**What.** `pilot.py meter-proof` makes one real upstream call (8 completion tokens) from
inside the campaign namespace, on its own campaign id `C_calib_meter_proof`:
`ceq = 36 + floor(0×2/100) + 4×8 = 68`.

**Why.** It is the cheapest end-to-end demonstration that the metered path, the closed
topology and the meter's own verifier all hold — independent of whatever the arms do. It
is **not** part of the pilot's per-arm totals and is listed separately in the spend table.

---

## D-CAL-7 — procedure §3.2 / diagnostic D4 cannot be applied to the frozen `E*`

**The clause that fails.** `PILOT-PROCEDURE.md` §3.2 and `B_hard.json`'s
`diagnostics.per_arm.*.D4_tau_cross_check` define the candidate wall time as
"`interpreted.wall_ms` of the Outcome the harness authored".

**What the tree does instead.** The frozen `E*` revision leaves
`interpreted.wall_ms` **null** by design and writes the measured wall clock to the
per-run **resources sidecar** (`<state>/resources.json`, `runs[].wall_ms`). That is a
documented upstream deviation — `a0/tasks/maxcut/DEVIATIONS.md` **D-T1-1** — made because
the canonical Outcome must be byte-identical for two runs of the same deterministic
candidate, which a wall-clock count cannot be. Measured, on the committed evidence: all
70 `A_simpleloop` and all 48 `A_kapso` Outcomes carry `interpreted.wall_ms: null`, and the
harness ledger rows carry only `wall_sec` (the whole `E*` invocation), not the candidate's
own time.

**What was done.** Nothing was edited. `D4` is reported as `null` exactly as the frozen
procedure computes it, and the same measurement read from the sidecars is published in a
separate, clearly labelled file — `a0/a1/calibration/tau_cross_check.json` — which states
its own provenance and that it is **not** part of the published, re-derivable evidence set
and **not** an input to `f`:

| arm | candidate `wall_ms` n / min / p50 / p95 / p99 / max | `10·p99` | §7 verdict |
|---|---|---|---|
| `A_simpleloop` | 140 / 31 / 33 / 34 / 36 / 37 | **0.36 s** | floor binds → `τ = 10 s` stands |
| `A_kapso` | 96 / 31 / 33 / 35 / 38 / 38 | **0.38 s** | floor binds → `τ = 10 s` stands |

`τ = min(30 s, max(10 s, 10·p99)) = 10 s`, i.e. the gate workstream's frozen `τ` is
unchanged and this cross-check agrees with it. Nothing was changed.

**Why not amend the procedure.** An amendment would be a new frozen revision with both
digests recorded, and every artifact records the procedure's sha256 — amending now would
break `V1` and force a re-run of a measurement that is otherwise complete. The clause's
only consumer is a *reported* diagnostic that `f` never reads, so the budget is unaffected.
If the procedure is revised later, the correct change is to widen §3.2 to
"`interpreted.wall_ms`, or the resources sidecar's `runs[].wall_ms` when the Outcome's key
is null by D-T1-1", and to publish the sidecar's numbers with the evidence.

**Also note.** Because the sidecar is not part of the reduction, D4 is not re-derivable
from the committed evidence alone. `calibration/verify.py` does not claim it is.

---

## D-CAL-8 — `publish` was re-serializing the meter ledger; the runner changed, the campaign did not

**What was wrong.** `pilot.py publish` wrote `<arm>/meter_ledger.jsonl` by re-serializing
each parsed row with `sort_keys=True`. The meter's own verifier pins the row key order
(`a0/meter/verify_ledger.py`, `ROW_KEY_ORDER`; `a0/meter/meter_core.py`), so on a real
(non-empty) ledger that copy fails row by row:

```
$ python3 a0/meter/verify_ledger.py a0/a1/calibration/evidence/simpleloop/meter_ledger.jsonl --json
rc=1  ... 47 rows, "failures": [{"row": 0, "detail": "key order is ['arm_id', 'campaign_id',
      'ceq', 'endpoint', ... 'ts', 'unmetered', 'usage']"}, ...]
```

**Why it had not been seen.** In the previous attempt both campaigns were blocked at their
identity precondition, so every published ledger was **empty** (sha256 `e3b0c442…`) and the
check passed vacuously.

**What was done.** `publish` now copies the campaign's own meter file **verbatim** and
refuses loudly (missing file, or sha256 ≠ the recorded `meter_ledger_sha256`) rather than
publishing a ledger the meter cannot re-derive. This is also what procedure §8 already
says ("that campaign's `a0/meter` ledger, **verbatim**"). After the fix the published file
is byte-identical to the meter's:

| | raw (run dir) | published | `INDEX.raw_sha256` |
|---|---|---|---|
| `simpleloop/meter_ledger.jsonl` | `0c847c46…` | `0c847c46…` | `0c847c46…` |
| `kapso/meter_ledger.jsonl` | `3a7b1fb6…` | `3a7b1fb6…` | `3a7b1fb6…` |

**The provenance point, stated plainly.** The fix is confined to `publish()`; the campaign
code path is untouched, and the paid campaigns were **not** re-run (that would be a second
paid campaign per arm, which the assignment does not allow). Consequently the artifacts
name two runner revisions, each truthfully:

| artifact | `runner.sha256` | what it names |
|---|---|---|
| `evidence/<arm>/pilot_arm.json` | `5034b91e0e4cdcf75d68954a3ca67d15eb2a41b16cc68937a6222dacc89c20a1` | the runner that **ran the campaign** (recorded during the run, from the run directory) |
| `B_hard.json` | `b6c69e43236162b7bb6f70ec1a26eb8738867be6d74464963417999f37190f09` | the runner that **reduced the evidence and applied `f`** (computed at `apply` time) |

Both hashes are recorded here, and the delta between them is exactly the `publish()`
meter-ledger change. Everything else the two revisions do is identical; the invariant test
suite (24 tests) passes on the new revision, and `calibration/verify.py` re-derives
`B_hard.json` byte-for-byte from the committed evidence with the new one.

**One check to read carefully.** The published `pilot_arm.json` carries
`the_runner_is_the_committed_one: true`. That assertion was made **during the campaign**,
against the then-current revision `5034b91e…`, and it was true when it was made; it is a
campaign-time observation, not a claim about the file on disk today. It is the only field
whose reading changes because of this fix, and it is left as recorded rather than
rewritten — rewriting it would be editing a measurement record.

**A consequence worth stating.** A ledger the meter cannot re-derive is exactly the
failure the meter's verifier exists to catch, and it was caught — by `calibration/verify.py`
before the evidence was committed. That step is now green.

---

## D-CAL-9 — the previous attempt's refusal is archived, not deleted

**What.** The blocked run's artifacts (`B_hard_REFUSED.json`, `BLOCKED.json`, the empty
per-arm records and ledgers) and the refusal document were moved to
`history/attempt1-blocked-identity-drift/`.

**Why.** `apply` must write `B_hard.json` **or** `B_hard_REFUSED.json` and
`calibration/verify.py` refuses to accept both being present at the directory root
(`step_properties`). The refusal is a real, reproducible record of a real state — the
`EID*` drift — and discarding it would erase the evidence that the arms were correctly
fail-closed before the identity was re-frozen. It is archived with its own `INDEX.json` so
a reader can reproduce the refusal from it.

---

## D-CAL-10 — the `CEq_max` guardrail is ~1.97 M CEq, i.e. a 30-minute extrapolation

**What.** `f` is designed (`INTERFACE.md` §9, procedure §4) as
`CEq_max = ⌈1.25 × 30 min × max_r q_r⌉`. With the measured
`q_r = 52 440.5 CEq/min` (`A_simpleloop`) that is **1 966 519 CEq** — about 5.3× the
`CEq` the pilot's SimpleLoop campaign actually consumed (370 881) and about 37× KAPSO's
(52 992).

**Why this is recorded rather than corrected.** It is what the frozen mapping produces, and
the mapping was frozen before any calibration byte was read precisely so that a number like
this could not be negotiated after the fact. The margin arithmetic is the check on it and
it passes (`D1 = 37.5 / 92.2 min`, `D2 = 73.3 / 37.5 min`, both above `T_wall = 30 min`;
`D3 ≤ 1.13 < 1.25`), neither ceiling clamp is active, and the `CEq_pilot_max` caps the
*pilot* at 1.2 M / 300 k (actual 370 881 / 52 992 — neither bound). No threshold was
touched, and the pending contract question about a bounded-round positive control is the
user's decision, not this directory's.

---

## Non-deviations worth naming, because they look like ones

* `T_wall_sec = 1800` is **not measured** — §9 calls it the design constant and the primary
  constraint. The pilot measures `q_r`, `e_r` and the latency distribution only.
* A **low** rate is not an invalidity (procedure §6): validity is about the measurement
  being established, not its magnitude. Nothing was refused on magnitude grounds.
* The pilot does not decide admissibility and does not read the gate's verdict. `B_hard`
  bounds *consumption*, never *quality*.
