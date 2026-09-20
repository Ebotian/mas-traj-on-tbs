# out/ — produced artefacts

| file | produced by | content |
| --- | --- | --- |
| `eidr.out`, `eidr/eidr.mapping.json`, `eidr/loreley.program*.md` | `a0_adapter eidr` | the `EID_r → EID*` mapping, its recomputation and the mutation test |
| `conformance.out`, `conformance.json` | `a0_adapter conformance` | A0.1, per candidate |
| `a02.out`, `a02.json` | `a0_adapter a02` | A0.2 checks |
| `traps.out`, `traps.json` | `a0_adapter traps` | T2 / T3 / T4 |
| `closure.json` (+ `closure-run/`) | `a0_adapter closure-probe` | closure verdict and raw canary output |
| `run-a0/` | `a0_adapter run` | the three traces, `run.summary.json`, `adapter.md`, `env.frozen.json`, `eidr.mapping.json`, the A0.1 reference runs and the plugin evidence records |
| `conformance/` | `a0_adapter conformance` | the frozen `a0.adapter.conformance/v1` document plus the traces that run wrote |
| `FINAL_SWEEP.txt` | the loop in `VERIFICATION.md` | `plan`, `eidr`, `eidr-recompute`, `conformance`, `a02`, `traps`, `run`, `closure-probe` in one run; every step `EXIT=0` |
| `eidr/eidr.recompute.json` | `a0-loreley eidr-recompute` | the reconstructed `EID_r`, also printed by `tools/verify_eidr.py` |

The external runner's copy of the conformance document lives at
`a0/conformance/out/adapters/loreley.conformance.json`; its verdict is in
`a0/conformance/report.loreley.json`.

`.out` files are the verbatim stdout+stderr of the corresponding command, so a
reader can see the runtime's own log lines (including the T3 truncation warning)
next to the machine-readable result.

`../VERIFICATION.md` quotes the verdicts and the evidence behind them.
