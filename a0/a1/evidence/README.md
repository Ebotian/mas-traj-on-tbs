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

| file | produced by | cost |
|---|---|---|
| `wiring_simpleloop.json` | `python3 a0/a1/probes/wiring_simpleloop.py` (8/8) | none |
| `wiring_kapso.json` | `a0/runtimes/kapso/.venv/bin/python a0/a1/probes/wiring_kapso.py` (7/7) | none |
| `skeleton_dryrun.json` | `python3 a0/a1/probes/skeleton_dryrun.py` (25/25) | none |
| `live_controls.json` | `python3 a0/a1/probes/live_probe.py controls` (6/6) | none (refusals and one 400) |
| `live_simpleloop.json` | `python3 a0/a1/probes/live_probe.py arm --arm simpleloop` (8/8) | 1 model call |
| `live_kapso.json` | `python3 a0/a1/probes/live_probe.py arm --arm kapso` (10/10) | 1 model call |

## Spend

Model `deepseek-flash`, temperature 0, reported from the **meter ledger** (the
runtime's self-report is diagnostic only).

| ledger | rows | unmetered | tokens (hit / miss / completion) | `CEq` |
|---|---|---|---|---|
| `live_simpleloop` meter | 1 | 0 | 0 / 1192 / 602 | 3600 |
| `live_kapso` meter | 1 | 0 | 0 / 80 / 256 | 1104 |
| live controls | 8 | 8 | 0 / 0 / 0 | 0 |
| induced-unmetered case | 1 | 1 | 0 / 0 / 0 | 0 |
| repair-hop validation (before the arms) | 1 | 0 | 0 / 37 / 8 | 69 |
| **committed total** | | | **1 hit / 1309 miss / 866 completion** | **4773** |

The session also contains **two discarded SimpleLoop attempts whose ledgers were
overwritten by the reruns** — `CEq` 8310 and 9382, i.e. ~17,700 more, plus a
handful of model-free attempts whose purpose was to find the framing defect
(D-A1-3). The session's whole-model total is therefore on the order of
**22,500 `CEq`**, with completion tokens under 3,000. At the interface's own
weights (`miss + 0.02·hit + 4·completion`) that is a few cents at any flash-tier
price; no price is asserted here, because none was measured.

**No claim about model quality.** One call per arm is not a search. What the two
live files establish is the *measurement chain*: who produced the number, that it
reached the selection, that the session could not overwrite it, and that the spend
is a number the runtime could not have lied about.
