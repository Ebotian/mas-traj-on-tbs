# Positive-control history

This file labels the positive controls this directory has owned, and which of
them the gate reads. It is the index for the superseded item; the revision
record itself is `PC-REVISION.md`.

| status | control | path | `source_sha256` | since |
|---|---|---|---|---|
| **ADOPTED** | bounded round, `k = 10` accepted improving swaps | `variants/pc_exchange_k10/` | `ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da` | 2026-09-23 |
| **history — superseded, kept** | unbounded `one_exchange` to a local optimum | `pc/` | `25de3e5d496198d74c7427de0d4504a0f3e49e8056c154d8eb8197648bcfb901` | 2026-09-22 → 2026-09-23 |

The superseded control at `pc/` is **not deleted**: its bytes, its pinned
NetworkX vendoring, its `pc_identity_report.json` evidence and its verdicts
(`../gates/verdict.dev.json`, `../gates/verdict.eval.json`) are all unchanged. It
failed the pre-registered ρ half of the gate (`0.158820` dev / `0.178716` eval
against a `0.30` bar) because it closed 82.6 % of the baseline→target gap and
left no measurable room. It is still reachable with
`python3 ../gates/gate_runner.py --set dev --pc positive_control/pc`.

Why the control changed, the criterion that was frozen before the choice, the
measured curve, the posterior-freedom caveat and the `instrumentation` evidence
scope are in `PC-REVISION.md`.
