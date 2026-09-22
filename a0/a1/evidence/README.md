# `a0/a1/evidence/` — what is recorded, what it is from, and what may be concluded

Every file here is the verbatim output of a probe, produced on **2026-09-22** on
this machine, with the code at the commit that ships it. `python3 a0/a1/verify.py
--evidence` prints a sha256 for each, so a copy that has been edited is
detectable.

**Reproducibility.** Re-running the model-free probes from the committed state
reproduces every `verdict` and every individual check byte-for-byte; the files as
a whole differ only in per-run identifiers (the harness's nonce, the measurement
OIDs, the ledger sequence rows, `elapsed_sec` and `merged_stream_sha256`). Those
are per-run by construction — a nonce that repeated would be the defect.

## Pre-fix or refreshed, file by file

This revision re-froze T1's `EID*` (see `DEVIATIONS.md` D-A1-7) and re-ran every
artifact that described the pre-fix evaluator. The pre-fix versions are **not**
duplicated here; they are the committed bytes at `4b94503e`, retrievable with
`git show 4b94503e:a0/a1/evidence/<file>`.

| file | status | why |
|---|---|---|
| `wiring_simpleloop.json` | **refreshed** | carried `evaluator_source_sha256 08281d21…` (the pre-fix `E*`); now records the current evaluator, and has one new check for the labelled override |
| `live_simpleloop.json` | **refreshed** (paid) | same, on a real campaign |
| `live_kapso.json` | **refreshed** (paid) | re-run so that every artifact in the directory is from one revision |
| `live_controls.json` | **refreshed** (free) | re-run with the rest |
| `wiring_kapso.json` | **refreshed** (free) | carried no pre-fix digest, re-produced for the same reason |
| `skeleton_dryrun.json` | **refreshed** (free) | as above; also records the new preflight check `iv.candidate_lane_is_closed` |
| `score_bound.json` | **new** | the plausibility bound (D-A1-10) |
| `hostile_candidate.json` | **new** | the candidate-lane closure (D-A1-8, D-A1-9) |

| file | produced by | checks | cost |
|---|---|---|---|
| `wiring_simpleloop.json` | `python3 a0/a1/probes/wiring_simpleloop.py` | 9/9 | none |
| `wiring_kapso.json` | `a0/runtimes/kapso/.venv/bin/python a0/a1/probes/wiring_kapso.py` | 7/7 | none |
| `skeleton_dryrun.json` | `python3 a0/a1/probes/skeleton_dryrun.py` | 25/25 | none |
| `score_bound.json` | `python3 a0/a1/probes/score_bound.py` | 7/7 | none |
| `hostile_candidate.json` | `python3 a0/a1/probes/hostile_candidate.py` | 13/13 | none (TCP connect attempts and one byte of a file, no model call) |
| `live_controls.json` | `python3 a0/a1/probes/live_probe.py controls` | 6/6 | none (refusals and one 400) |
| `live_simpleloop.json` | `python3 a0/a1/probes/live_probe.py arm --arm simpleloop` | 9/9 | 1 model call |
| `live_kapso.json` | `python3 a0/a1/probes/live_probe.py arm --arm kapso` | 11/11 | 1 model call |

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
runtime's self-report is diagnostic only). Both live arms ran with the harness in
its sandboxed candidate lane (`candidate_isolation.mechanism =
"unshare -rmnpf --mount-proc"`, recorded in each artifact's
`harness/harness_identity.json`).

| ledger | rows | unmetered | tokens (hit / miss / completion) | `CEq` |
|---|---|---|---|---|
| `live_simpleloop` meter | 1 | 0 | 1024 / 168 / 2048 | 8380 |
| `live_kapso` meter | 1 | 0 | 0 / 80 / 256 | 1104 |
| live controls | 2 | 2 | 0 / 0 / 0 | 0 |
| induced-unmetered case | 1 | 1 | 0 / 0 / 0 | 0 |
| **total for this revision's refresh** | | | **1024 hit / 248 miss / 2304 completion** | **9484** |

`CEq = miss + floor(hit·2/100) + 4·completion` (`INTERFACE.md` §8), which the
meter's own `verify_ledger.py` re-derives from each row's usage (recorded in every
live artifact as `meter_verify_ledger`).

Earlier rounds of this workstream spent more than the table above: the first live
round on the pre-fix meter (SimpleLoop attempts at `CEq` 8310, 9382, 3600; KAPSO
attempts at 1104 and 1104), the model-free calls that found the framing defect
(69, 14), and the previous round's refreshes (8380 + 1104, now superseded). The
session's whole-model total is **≈42,600 `CEq`** — a few cents at any flash-tier
price. No price is asserted here, because none was measured.

**No claim about model quality.** One call per arm is not a search. What the two
live files establish is the *measurement chain*: who produced the number, that it
reached the selection, that the session could not overwrite it, and that the spend
is a number the runtime could not have lied about.
