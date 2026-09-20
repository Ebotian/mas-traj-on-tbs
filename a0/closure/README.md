# Closure verification by probe — `a0/closure/`

Protocol: `open_world_plan_review.typ` §4.3, last paragraph (line 569) — *a runtime's
autonomous external acquisition must be proven absent BY PROBE, not by a config flag*.
Audit history: `open_world_plan_independent_review.typ` D15 (line 320) — the Closed arm of
Stage B may not be closed at all.

This directory owns the closure evidence for all four A0 runtimes. **Verdicts and findings:
[`VERDICTS.md`](VERDICTS.md).** Machine-readable per-runtime records (the
`a0.closureprobe/v1` shape from `a0/contract/adapter_contract.md` §7):
`closure.{eve,kapso,loreley,simpleloop}.json`.

## Run everything

```bash
a0/closure/run_probes.sh            # ~6 min; writes a0/closure/evidence/
```

Sections 0–6 are probe-only (seconds); section 7 makes four real model calls (~35–105 s each),
so it needs a working codex endpoint (`cc-switch -a codex proxy enable && cc-switch daemon
start --detach` provides the one this machine uses).

It exits 0 iff every executed probe matched its label. Nothing outside `a0/closure/` is
written; the pinned checkouts are only read (imports run with `PYTHONDONTWRITEBYTECODE=1`).

## What is measured, and why every mechanism is measured twice

A barrier that blocks *everything* is not a closure mechanism, it is broken networking. So
each probe runs the **same command text** twice:

* **positive control** — on the host, unblocked: the canary must really reach the network;
* **negative case** — inside the barrier: the same canary must fail.

The canary reports `dns`, `tcp`, `tcpvia`, `https`, `local` and `egress=OPEN|BLOCKED`.
`local=ok` proves the channel can still do real work (it is a sandbox, not a corpse).

## Files

| Path | What it is |
|---|---|
| `run_probes.sh` | orchestrator; runs sections 0–7 below and prints a pass/fail summary |
| `probes/lane_net_probe.py` | the canary the lanes execute (no third-party imports) |
| `probes/lane_e2e_probe.py` | **end-to-end lane probe**: builds the lane argv with the runtime's own code, runs a real model turn, and reads the canary from a file the in-lane shell tool persisted |
| `probes/cli_sandbox_probe.sh` | the Codex CLI's own sandbox, executed without a model (`codex sandbox`) |
| `probes/simpleloop_lane_probe.sh` | SimpleLoop's closure posture per candidate solver CLI |
| `probes/seam_eve_argv.py` | builds the exact argv of EvE's `codex_tmux` / `codex_exec` drivers (real EvE code) |
| `probes/seam_kapso_argv.py` | builds the exact argv of KAPSO's codex lane and claude lane (real KAPSO code) |
| `probes/seam_loreley_argv.py` | builds the exact argv of Loreley's kilocode / codex / cursor backends (real Loreley code) |
| `evidence/*.log`, `evidence/*.jsonl`, `evidence/*.json` | raw output of every executed probe, kept verbatim |
| `closure.<runtime>.json` | per-runtime closure record (mechanisms, controls, residuals, verdicts) |
| `closure.reconciliation.json` | this workstream's records vs each runtime workstream's own closure record, with the authoritative one named per channel |

## Probe sections

| # | Section | Mechanism probed |
|---|---|---|
| 0 | `00_self_test.log` | which isolation mechanisms exist at all, each with both controls |
| 1 | `01_external_isolation.log` | external cut: same lane command, host (OPEN) vs `unshare -rn` (BLOCKED) |
| 2 | `02_host_loopback_cut.log` | sharp edge: the cut also severs `127.0.0.1:15722` (the model relay) |
| 3 | `03_cli_sandbox.log`, `.jsonl` | Codex CLI sandbox: `workspace-write` (BLOCKED) vs `danger-full-access` (OPEN) |
| 4 | `04_seam_*.log` | argv of each runtime's own lane commands (no model needed) |
| 5 | `05_codex_surface.log` | CLI capability surface beyond the shell sandbox |
| 6 | `06_simpleloop_*.log` | SimpleLoop postures, each with a positive control |
| 7 | `07_model_lane_blocked.log` | whether a model turn is possible at all (it became possible mid-audit) |
| 8–10 | `08_*`, `09_*`, `10b_*` | END-TO-END: a real codex model turn driving the shell tool, per posture |
| 7 (run_probes) | `17_*.json` | END-TO-END lane probes: KAPSO's and SimpleLoop's own lane argv, closed posture + control |
| 12 | `12_f4_regression.log` | before/after proof of the `probe_egress.sh --cmd` classifier fix |

## Reproducing an individual probe

```bash
a0/closure/probes/cli_sandbox_probe.sh                       # CLI sandbox, both controls
a0/closure/probes/simpleloop_lane_probe.sh --posture codex-workspace-write
a0/env/checks/probe_egress.sh check --mechanism unshare-rn \
  --cmd 'env -u http_proxy -u https_proxy /usr/bin/python3 a0/closure/probes/lane_net_probe.py'

# seams (need a venv with that project's deps; see VERDICTS.md for exact PYTHONPATHs)
PYTHONPATH=/tmp/eve/src a0/runtimes/eve/.venv/bin/python a0/closure/probes/seam_eve_argv.py
PYTHONPATH=/home/ebt/kapso_ck/kapso/src a0/closure/.venv/bin/python a0/closure/probes/seam_kapso_argv.py
cd /tmp && PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=a0/tasks/circle-packing/upstream/loreley \
  a0/runtimes/loreley/checkout/.venv/bin/python a0/closure/probes/seam_loreley_argv.py
```

`a0/closure/.venv` (python 3.12) holds only what the KAPSO seam needs to import KAPSO's real
adapters **without installing KAPSO itself** (which would write build artefacts into the
shared checkout): `mcp`, `pydantic`, `GitPython`, `litellm`, `PyYAML`, `python-dotenv`.

## Canonical egress probe, and the F4 fix

`a0/env/checks/probe_egress.sh` is the canonical probe and it has been **patched** here (the
original owner is inactive; the patch was authorized). `check --mechanism M --cmd C` used to
classify by scanning *all* `egress=` occurrences in the output, so a command that printed its
own `egress=` marker — exactly what a runtime's own network probe does — turned an **unblocked**
run into a false `MISMATCH`. It now classifies from the mechanism canary's `EVIDENCE` line only,
and `self-test` carries a regression case that runs a command printing `egress=BLOCKED` on the
host and requires `CONFIRMED`. Before/after: `evidence/12_f4_regression.log`.

No wrapper is shipped here: a second implementation would be exactly the kind of ambiguity this
study is trying to remove, so the patched shared tool is the single canonical one.
`run_probes.sh` reads the `EVIDENCE` line and keeps raw output regardless, so its behaviour is
identical before and after the patch; `evidence/01_external_isolation.log` preserves the
original mislabelled output from the first pass.
