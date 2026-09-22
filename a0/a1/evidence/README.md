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

One exception, and it is the reason `hostile_candidate.json` is `fail`: four of
its checks assert that the *open* lanes really can read the answers and the key,
and those assertions depend on what `HEAD` contains, not on this directory. They
were true when the committed bytes were recorded and are false now that the
maxcut worker removed the stored witnesses (D-A1-13). Re-running the probe
reproduces its 9/13 faithfully; what it cannot reproduce is a leak that the tree
no longer contains.

## Refreshed against one revision, file by file

`EID*` moved a **second** time when two further commits to `E*` landed (the
candidate-staging fix, then the candidate-facing redaction); `DEVIATIONS.md`
D-A1-13 records both digests and the reason. Every artifact in this directory was
produced *after* the last of those commits, in one sitting, so the set describes
one revision: `EID*` = `7ce9e72f…`, `evaluator_source_sha256` = `dc6969ec…`.

The older versions are **not** duplicated here. They are the committed bytes at
`4b94503e` (the round that closed the verifier's findings) and at `75403e8c` (the
round that followed the first re-freeze), retrievable with
`git show <commit>:a0/a1/evidence/<file>`.

| file | status | why |
|---|---|---|
| `wiring_simpleloop.json` | **refreshed** | re-produced after the last `E*` edit; records `dc6969ec…` |
| `live_simpleloop.json` | **refreshed** (paid) | same, on a real campaign; records `dc6969ec…` |
| `live_kapso.json` | **refreshed** (paid) | re-run so every artifact is from one revision; records the *plumbing* evaluator (`5ae97ad9…`) because that is the task this arm ran (D-A1-2) |
| `live_controls.json` | **refreshed** (free) | re-run with the rest |
| `wiring_kapso.json` | **refreshed** (free) | as above |
| `skeleton_dryrun.json` | **refreshed** (free) | now records `eid_star=7ce9e72f…` |
| `score_bound.json` | **refreshed** (free) | records `dc6969ec…` |
| `hostile_candidate.json` | **refreshed, verdict changed to 9/13** | the four failing checks are the probe's own positive controls, invalidated by the maxcut worker's witness removal — see D-A1-13. This is the only artifact here whose verdict is not `pass`, and it is reported rather than repaired |

| file | produced by | checks | cost |
|---|---|---|---|
| `wiring_simpleloop.json` | `python3 a0/a1/probes/wiring_simpleloop.py` | 9/9 | none |
| `wiring_kapso.json` | `a0/runtimes/kapso/.venv/bin/python a0/a1/probes/wiring_kapso.py` | 7/7 | none |
| `skeleton_dryrun.json` | `python3 a0/a1/probes/skeleton_dryrun.py` | 25/25 | none |
| `score_bound.json` | `python3 a0/a1/probes/score_bound.py` | 7/7 | none |
| `hostile_candidate.json` | `python3 a0/a1/probes/hostile_candidate.py` | **9/13** | none (TCP connect attempts and one byte of a file, no model call) |
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
live artifact as `meter_verify_ledger`). For this round it re-derived `ceq_total`
8380 and 1104 with `failures: []` and `unmetered: 0` for the two arms.

The token counts of this round are identical to the previous round's refresh —
same prompts, same deterministic decoding — but this is a **second** paid round:
each arm was called once more and these are new ledger rows, not the old ones.

Earlier rounds of this workstream spent more: the first live round on the pre-fix
meter (SimpleLoop attempts at `CEq` 8310, 9382, 3600; KAPSO attempts at 1104 and
1104), the model-free calls that found the framing defect (69, 14), and the
previous round's refreshes (8380 + 1104). Counting this round's 9484, the
session's whole-model total is **≈52,100 `CEq`** — a few cents at any flash-tier
price. No price is asserted here, because none was measured.

**No claim about model quality.** One call per arm is not a search. What the two
live files establish is the *measurement chain*: who produced the number, that it
reached the selection, that the session could not overwrite it, and that the spend
is a number the runtime could not have lied about.
