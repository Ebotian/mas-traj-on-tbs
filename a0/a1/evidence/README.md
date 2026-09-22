# `a0/a1/evidence/` — what is recorded, and what may be concluded from it

Every file here is the verbatim output of a probe, produced on **2026-09-22** on
this machine, with the code at the commit that ships it. The `verify.py` report
prints a sha256 for each, so a copy that has been edited is detectable.

**Reproducibility of these files.** Re-running the three model-free probes from
the committed state reproduces every `verdict` and every individual check
byte-for-byte; the files as a whole differ only in per-run identifiers (the
harness's nonce, the measurement OIDs, the ledger sequence rows, `elapsed_sec` and
`merged_stream_sha256`). Those are per-run by construction — a nonce that repeated
would be the defect.

**Which round these are.** The `live_*` files are from the **second** round, run
after `a0/meter` fixed its request framing (`86987235`) and after this directory
deleted the compensating repair hop (D-A1-3). The first round's files recorded
`repair_records` and one more `CID` factor; they are superseded and not kept,
because a record of a topology that no longer exists is not evidence for the code
that ships.

| file | produced by | cost |
|---|---|---|
| `wiring_simpleloop.json` | `python3 a0/a1/probes/wiring_simpleloop.py` (8/8) | none |
| `wiring_kapso.json` | `a0/runtimes/kapso/.venv/bin/python a0/a1/probes/wiring_kapso.py` (7/7) | none |
| `skeleton_dryrun.json` | `python3 a0/a1/probes/skeleton_dryrun.py` (25/25) | none |
| `live_controls.json` | `python3 a0/a1/probes/live_probe.py controls` (6/6) | none (refusals and one 400) |
| `live_simpleloop.json` | `python3 a0/a1/probes/live_probe.py arm --arm simpleloop` (9/9) | 1 model call |
| `live_kapso.json` | `python3 a0/a1/probes/live_probe.py arm --arm kapso` (11/11) | 1 model call |

## Which configuration each live file describes

| file | task | registered tree in play | `AID_r` |
|---|---|---|---|
| `live_simpleloop.json` | T1 max-cut | none — SimpleLoop has no registration surface | `AID_r.A_simpleloop.json` |
| `live_kapso.json` | plumbing (circle-packing), per D-A1-2 | the *plumbing* tree `8128cf91…`, **not** the T1 tree | `AID_r.A_kapso.json` pins the **T1** tree |

So the KAPSO arm's **T1** live evidence is not here: it is
`a0/a1/kapso_t1/evidence/live_t1.json` (another workstream, 15/15), which drives
the same `a0/runtimes/kapso/a0_adapter/harness_manifest.py` this directory wrote,
against the tree whose `EID_r` = `manifest:6b1d6fcc…` that `AID_r.A_kapso.json`
now pins. The plumbing run is kept because it is *this* probe's own record and it
is what a re-run of the committed code reproduces; it is not offered as T1
evidence for that arm.

## Spend

Model `deepseek-flash`, temperature 0, reported from the **meter ledger** (the
runtime's self-report is diagnostic only).

| ledger | rows | unmetered | tokens (hit / miss / completion) | `CEq` |
|---|---|---|---|---|
| `live_simpleloop` meter | 1 | 0 | 1024 / 168 / 2048 | 8380 |
| `live_kapso` meter | 1 | 0 | 0 / 80 / 256 | 1104 |
| live controls | 2 | 2 | 0 / 0 / 0 | 0 |
| induced-unmetered case | 1 | 1 | 0 / 0 / 0 | 0 |
| **committed total** | | | **1024 hit / 248 miss / 2304 completion** | **9484** |

`CEq = miss + floor(hit·2/100) + 4·completion` (`INTERFACE.md` §8), which the
meter's own `verify_ledger.py` re-derives from each row's usage (recorded in every
live artifact as `meter_verify_ledger`).

Earlier rounds of this workstream spent more than the table above: the first live
round on the pre-fix meter (SimpleLoop attempts at `CEq` 8310, 9382, 3600; KAPSO
attempts at 1104 and 1104) and the model-free calls that found the framing defect
(69, 14). The session's whole-model total is **≈33,100 `CEq`** — still a few cents
at any flash-tier price. No price is asserted here, because none was measured.

**No claim about model quality.** One call per arm is not a search. What the two
live files establish is the *measurement chain*: who produced the number, that it
reached the selection, that the session could not overwrite it, and that the spend
is a number the runtime could not have lied about.
