# Closure verification — verdicts, evidence, findings

Scope: `open_world_plan_review.typ` §4.3 line 569 (*"必须用探测证明所选 runtime 没有自主外部获取，
而不是只在配置里关"*), read with `open_world_plan_independent_review.typ` D15 (line 320).
Auditor: closure-verification workstream. First pass 2026-09-20 17:12–17:30; **re-run 18:05–18:30
with the model lanes restored** (the dead `127.0.0.1:15722` listener was CC Switch's local proxy:
`cc-switch -a codex proxy enable && cc-switch daemon start --detach`), which turned the
seam-only probes for KAPSO's lane and SimpleLoop into genuine end-to-end measurements and
settled F4.

Everything below is **executed**. Raw output is in `evidence/`, machine-readable per-runtime
records in `closure.<runtime>.json`. Reproduce with `./run_probes.sh`.

---

## 1. Verdict per runtime

| Runtime | Verdict | Mechanism that achieves closure | What is proven by execution | Blocked / unverified |
|---|---|---|---|---|
| **EvE** | **CONDITIONAL** | `codex_tmux` driver only: `-s workspace-write -a never -c web_search="disabled"` (config). The **shipped full-run path is not closable at all** — see F1. | end-to-end: real codex turn + shell tool at `-s workspace-write` → canary `egress=BLOCKED`; same prompt unsandboxed → `egress=OPEN` | no EvE campaign launched; sub-agent `.codex/agents/*.toml` sandbox overrides unprobed |
| **KAPSO** | **CONDITIONAL** | codex lane: **one config key is enough** — `agent_specific.sandbox=workspace-write` (+ `web_search=false`), measured end to end: the shell network is closed while the model call still completes. claude lane: no CLI sandbox; the config-level alternative (banning Bash) closes the lane by deleting the capability it exists to use, so it needs an external cut or a lane switch. | lane argv from KAPSO's own adapter, executed with a real model turn: closed posture `rc=0`, in-lane canary `egress=BLOCKED` (34.8 s); shipped default (`--search --sandbox danger-full-access`) `rc=0`, `egress=OPEN` (102 s) | no KAPSO campaign run (worktrees/inbox/registered-eval trigger not exercised); claude lane not driven |
| **Loreley** | **CONDITIONAL** | default path: none. Closure requires changing the worker backend to `codex_cli:codex_coding_backend` (`-a never --sandbox workspace-write`) or an external cut. | backend argv built by Loreley's own code: default `kilo run --auto` (no sandbox/network/search field at all); codex backend `--sandbox workspace-write` / planning `read-only`; `shutil.which('kilo') is None` | default lane cannot even start here (`kilo` not installed) → recorded as BLOCKED, not a pass |
| **SimpleLoop** | **CLOSED** | its shipped solver lane already selects the Codex CLI sandbox: `CliSolver._command` → `codex exec --sandbox workspace-write`. Bounded by the CLI choice (the `claude` branch of the same driver has no sandbox). | real model turn on the driver's own unmodified argv: `rc=0` (model call completed) and the in-lane shell tool persisted `egress=BLOCKED` (68.6 s); positive control through the same machinery (sandbox token `danger-full-access`) → `rc=0`, `egress=OPEN` | full SimpleLoop iteration (proposal → `E*` → selection → traces) not run by this workstream; the SimpleLoop workstream owns run-level evidence |

Reading the table:

* **SimpleLoop is CLOSED as shipped** — the one substrate that needs no change, because its
  solver lane already launches `codex exec --sandbox workspace-write` and that posture is
  measured closed with a live model turn (`17_simpleloop_lane_closed.json`).
* **KAPSO is one config key away** on its default-usable *codex* lane, measured end to end; its
  `claude_code` default lane is the blocker (external cut or lane switch).
* **EvE and Loreley need a driver/backend switch**, not a flag inside their shipped path.
* **One posture is unconditionally OPEN**: EvE's shipped `codex_exec` full-run driver.
* §4.3 requires a *probe*, not a flag — and every "closed" above is a probe result with a
  positive control, not a config read. The mechanisms happen to be CLI-config-driven (the Codex
  CLI's own sandbox), which is exactly why the positive control matters: `workspace-write` could
  have closed the network by breaking it, and `local=ok` in every blocked case shows it did not.

---

## 2. The evidence, per mechanism

### 2.1 Codex CLI `workspace-write` really does block egress (the linchpin)

`a0/closure/evidence/03_cli_sandbox.log` — same canary, four postures:

```
host, no sandbox                                  dns=ok   tcp=ok  https=ok   local=ok  egress=OPEN
codex sandbox -c sandbox_mode="workspace-write"   dns=fail tcp=fail https=fail local=ok  egress=BLOCKED
codex sandbox -c sandbox_mode="danger-full-access" dns=ok  tcp=ok  https=ok   local=ok  egress=OPEN
workspace-write + sandbox_workspace_write.network_access=true
                                                  dns=ok   tcp=ok  https=ok   local=ok  egress=OPEN
```

`local=ok` in the blocked case proves the barrier is selective (a sandbox, not broken
networking); the `danger-full-access` case is the positive control; the last case shows the
`network_access` knob actually re-opens the door, i.e. the default is what closes it.

### 2.2 End-to-end on the real model lane

Mid-audit the `127.0.0.1:15722` codex relay came back (a parallel workstream restored it), so
the probes were re-run **with a real model turn** driving the shell tool
(`evidence/07_model_lane_blocked.log` records the transition):

| Posture | Evidence | Canary result |
|---|---|---|
| `codex exec -s workspace-write`, `-c web_search="disabled"` | `08_e2e_codex_workspace_write.jsonl` | `dns=fail tcp=fail https=fail local=ok egress=BLOCKED`, `exit_code: 0` |
| `codex exec --dangerously-bypass-approvals-and-sandbox` (= **EvE's codex_exec posture**) | `09_e2e_codex_bypass.jsonl` | `dns=ok tcp=ok https=ok local=ok egress=OPEN` |

This is the strongest form of the required evidence: not a seam, not a config read — a model
turn, a tool call, and the network outcome on both sides of the control.

### 2.3 External network isolation, same command both sides

`evidence/01_external_isolation.log` (canary identical in both lines):

```
mechanism=host        ... tcpvia=example.com:443 https=ok    egress=OPEN     -> CONFIRMED
mechanism=unshare-rn  ... dns=fail tcp=fail https=fail local=ok egress=BLOCKED -> CONFIRMED
```

`evidence/00_self_test.log` re-confirms all five mechanisms of
`a0/env/checks/probe_egress.sh` (host / docker-bridge / docker-internal / docker-none /
unshare-rn), each with both controls: `SELF-TEST: PASS`.

### 2.4 Lane argv, from each runtime's own code (no model needed)

* `evidence/04_seam_eve.log` — EvE imports at `/tmp/eve/src` (HEAD `979065fd`):
  * `codex_tmux`: `codex --no-alt-screen -a never -s workspace-write -C <wt> -m gpt-5.4-mini -c model_reasoning_effort="low" -c web_search="disabled" PROMPT`
  * `codex_exec`: `codex exec PROMPT --dangerously-bypass-approvals-and-sandbox --json -C <wt> -m … -c web_search="live"`
* `evidence/04_seam_kapso.log` — KAPSO at `/home/ebt/kapso_ck/kapso` (HEAD `7d99b15`):
  * codex lane: `codex --search exec --sandbox danger-full-access …`
  * codex lane after the one-key change: `codex exec --sandbox workspace-write …`
  * claude lane: `claude -p --dangerously-skip-permissions --allowedTools Edit,Read,Write,Bash …`, `capabilities = {… 'sandbox': False …}`
* `evidence/04_seam_loreley.log` — Loreley at `4c375920`:
  * defaults: `worker_{planning,coding,seed_portfolio}_backend = …kilocode_cli:…`
  * `kilo run --auto --title t PROMPT`; codex coding `codex -a never --sandbox workspace-write exec --ephemeral --color never --json`; planning `--sandbox read-only`; `which('kilo') = None`

### 2.5 End-to-end lane probes (the runtime's own lane command, real model turn)

`probes/lane_e2e_probe.py` builds the lane argv with each runtime's **own** code
(KAPSO's `CodexCodingAgent._exec_command`, SimpleLoop's `CliSolver._command`), runs it for real,
and asks the model to run the shared canary through its shell tool and to **persist** the
canary's stdout to a file. The persisted file — not the model's prose — is the evidence, so a
model that merely claims success cannot fake a result.

| Runtime | Posture | Model call | Tool ran | Canary | Verdict | Evidence |
|---|---|---|---|---|---|---|
| KAPSO | `agent_specific.sandbox=workspace-write`, `web_search=false` | rc=0 (completed) | yes | `egress=BLOCKED` | **closed** | `11_kapso_lane_closed.json`, suite re-run `17_kapso_lane_closed.json` |
| KAPSO | shipped default (`--search`, `--sandbox danger-full-access`) | rc=0 | yes | `egress=OPEN` | egress_detected | `11b_kapso_lane_open.json`, `17_kapso_lane_open.json` |
| SimpleLoop | shipped `CliSolver` argv (`codex exec --sandbox workspace-write`) | rc=0 | yes | `egress=BLOCKED` | **closed** | `13_simpleloop_lane_closed.json`, `17_simpleloop_lane_closed.json` |
| SimpleLoop | control: same machinery, sandbox token `danger-full-access` | rc=0 | yes | `egress=OPEN` | egress_detected | `13b_simpleloop_lane_open.json`, `17_simpleloop_lane_open.json` |

The full suite re-run on the restored model lane finishes green: `run_probes.sh` → sections 0–7
all `CONFIRMED`, `ALL EXECUTED PROBES MATCHED THEIR LABELS (fails=0)`, exit 0.

This settles the two open questions from the previous pass: KAPSO's codex lane closes with **one
config key while the model lane keeps working**, and SimpleLoop's real solver lane is closed as
shipped. It also replaces the KAPSO workstream's `codex_workspace_write` probe, which timed out
(rc=124, `command_ran=false`) and therefore observed nothing.

### 2.6 Sharp edges

`evidence/02_host_loopback_cut.log` (decisive for how closure can be implemented):

```
host, no barrier                HOST_RELAY_HTTP=200      (codex's model relay answers)
inside unshare -rn              NETNS_RELAY_HTTP=000     (unreachable)
docker --internal + host-gateway  INTERNAL_HOSTGW_RELAY=fail ; INTERNAL_EGRESS=blocked
```

1. **Every external cut also severs host loopback.** A runtime whose model endpoint is a
   host-local relay cannot be wrapped in `unshare -rn` or `docker --internal` — the cut kills
   its model lane. Only the CLI's *own* sandbox separates "model lane" from "tool lane", which
   is why the codex `workspace-write` route is the only config-expressible closure on this host.
2. **Only the candidate-execution channel may be wrapped**; the orchestrator (model I/O,
   campaign inbox, `E*` invocation, Postgres/Redis) must stay outside, or its services must be
   siblings inside the same internal network.
3. **The sandbox does not cover provider-side tools.** `codex --help` describes `--search` as
   making "the native Responses `web_search` tool … available to the model" — it runs at the
   provider, not in the sandboxed shell. Closure therefore needs the sandbox **and**
   `web_search` disabled.
4. **A blocked channel can still have other tool surfaces.** `codex features list`
   (`evidence/05_codex_surface.log`) reports `browser_use=true`, `browser_use_external=true`,
   `browser_use_full_cdp_access=true`, `in_app_browser=true`, `computer_use=true` (all
   "stable"); `web_search_request`/`web_search_cached` are deprecated-false and the live knob
   is the `web_search` config. A closure claim must name the *whole* tool list, not just the
   shell.
5. **Config-only closure can be a silent no-op** (F1) — the value is accepted and never used.

---

### 2.7 Probe defects found and fixed while re-running

* `probe_egress.sh --cmd` misclassification — **fixed** (see F4).
* `probes/lane_e2e_probe.py` crashed instead of degrading when a model turn exceeded the
  timeout: `subprocess.TimeoutExpired.stdout` is bytes even in text mode, so the JSON writer
  raised `TypeError` and the case was lost (`evidence/17_simpleloop_lane_open.log`, first
  suite run). Fixed by coercing the timeout payload to text and raising the default timeout to
  420 s; a slow turn now yields `inconclusive`, which the study must read as *not closed*.
  Found only because the suite was re-run end to end — a probe that crashes is a probe that
  proves nothing, the same failure mode as a probe that only ever shows "blocked".

## 3. Findings for the protocol (report as findings, not work-arounds)

**F1 — EvE's default full-run path cannot be closed by configuration; the §4.3 recipe is
wrong for it.** The recipe (`sandbox_mode: workspace-write` + `allow_network: false` +
`web_search: disabled`) applies to the `codex_tmux` driver. But the shipped full-run preset is
`configs/eve/driver/codex_max.yaml` (`driver: codex_exec`, `web_search: live`), which is the
default of `configs/eve/circle_packing.yaml` (`defaults: - driver: codex_max`). The
`codex_exec` driver has **no sandbox parameter** and its argv hardcodes
`--dangerously-bypass-approvals-and-sandbox` (`codex_exec.py:419-436`). Evidence:
`04_seam_eve.log` (executed argv), `09_e2e_codex_bypass.jsonl` (that posture really reaches the
network), and the false-green test: feeding `driver.sandbox_mode=workspace-write` to
`_build_codex_exec_driver` is **silently ignored** — the built driver has no `sandbox_mode`
attribute and still emits the bypass flag. Consequence for A0/A1: EvE is CONDITIONAL on
switching to `codex_tmux`, and any A1 arm that runs EvE must record which driver was used,
because the two postures are not the same experiment.

**F2 — "KAPSO has no lane-level sandbox parameter" is not accurate.** The parameter exists at
the adapter level (`codex_agent.py:117`, `agent_specific.sandbox`, default
`danger-full-access`) and the same tree already uses it (`learning/graders/frame.py:72`;
`learning/codify_run.py:249,273`; `learning/behavior.py:122` set
`agent_specific["sandbox"] = "workspace-write"`). What is true is that the **GENERIC search
strategy never passes it** (`implementation.py:212-231` passes env/mcp/`web_search`/timeout but
no sandbox). Measured end to end: with `sandbox: workspace-write` the lane's shell network is
closed **while the model call still completes** (`11_kapso_lane_closed.json`). So the correct
statement is not "needs a code change" but "needs one config key on the codex lane, and an
external cut or a lane switch for the claude lane". (The previous pass could only verify this at
argv level; the running model lane made the end-to-end measurement possible.)

**F3 — the web-search front door is provider-dependent, and on this machine it is shut by the
provider, not by configuration.** With `-c web_search="live"` a real model turn answered
`NO_WEB_SEARCH_TOOL` (`10b_e2e_websearch_live.jsonl`). Useful, but it is *not* a closure
guarantee: it must be re-probed whenever the model provider/relay changes, and it must never
be written into the record as "closed in config". (`codex exec --search` is also rejected by
the CLI — the flag belongs before `exec`, as KAPSO correctly emits it.)

**F4 — the shared probe misclassified `--cmd` runs. FIXED (authorized patch).** `a0/env/checks/probe_egress.sh check --mechanism M --cmd C` classified by scanning *all* `egress=` occurrences in the output. A command that prints its own `egress=` marker (exactly what a runtime's own network probe does) therefore turned an **unblocked** run into a false `MISMATCH`. Patch: classify from the first line only — the mechanism canary's `EVIDENCE` line — and added a regression case to `self-test` that runs a command printing `egress=BLOCKED` on the host and requires `CONFIRMED`. Before/after, byte-identical except for the one reverted line: `evidence/12_f4_regression.log` (`MISMATCH` before → `CONFIRMED` after). `run_probes.sh` still reads the `EVIDENCE` line and keeps raw output, so its behaviour is unchanged.

---

## 4. What the other workstreams must know

1. **Attach a closure record to every run.** Even now that SimpleLoop is CLOSED and the other
   three are one switch away, the claim must be per-run: which driver/backend/CLI, which sandbox
   mode, which web-search setting, which barrier. Roll these into `adapter.md` and the `resource`
   trace (`a0/contract/trace_schema.md`); a run with an unrecorded posture is not interpretable,
   and the provider can change under the study (it changed mid-audit).
2. **Do not let different runtimes run under different access policies.** `plan:591-603`
   requires SimpleLoop to share M/P/T/E **and the sandbox/access policy** with the complex
   runtimes; if KAPSO's claude lane or Loreley's kilocode lane runs open while another runs
   sandboxed, A1 compares access policies, not search machinery.
3. **Adapter `closure-probe` subcommand** (`adapter_contract.md` §7) should implement exactly
   the two-control pattern demonstrated here; `mechanism` must name the real mechanism
   (`config` / `external_network_isolation` / `code_change`), and `inconclusive` must never be
   reported as closed. The EvE and KAPSO records here show the failure mode to avoid: a config
   key that is accepted but never applied.
4. **`|R_1| >= 1` is comfortably satisfied, and the substrates can now be matched.** SimpleLoop's
   shipped solver lane is measured CLOSED (`13`, `13b`); KAPSO's codex lane closes with one
   `agent_specific` key while its model call keeps working (`11`); EvE closes by switching to
   `codex_tmux`; Loreley closes by switching to its codex backend. All four can therefore run
   under `workspace-write` + web-search-disabled, which is the access-policy parity `plan:591-603`
   requires — do not let one substrate run sandboxed and another open, or A1 compares access
   policies instead of search machinery. Any Adapter `closure-probe` must re-measure per run and
   record the posture; a config key that was set once is not evidence.
5. **Reuse, don't reinvent**: `probes/lane_net_probe.py` is the canary to embed in the
   adapters' closure probes, and `probes/cli_sandbox_probe.sh` is the model-free way to test any
   codex-driven lane.

---

## 5. Reconciliation with the other workstreams' records

Full matrix: `closure.reconciliation.json`. Authority rule applied: a record is authoritative
for a channel only if it contains an **executed, two-control observation** of that channel; a
timed-out probe or a probe that only shows a tool *absent* establishes nothing.

| Runtime | Their record | Their verdict | Agreement | Contradiction, and which record wins |
|---|---|---|---|---|
| KAPSO | `runtimes/kapso/runs/closure-01/closure.json` | `closed` / `config` | Their `channel_detail.codex_lane.note` states the same fact as F2 (lane-level sandbox exists, default `danger-full-access`; claude lane has none). Barrier results agree. | **Codex lane closed posture**: their probe timed out (rc=124, `command_ran=false`) yet `verdict_by_channel.llm_agent_lane=closed_by_config`. **This workstream wins** (executed: rc=0, canary BLOCKED) — their claim is upgraded from inference to evidence. **Claude lane**: their `lane_closure_by` = "disallowed_tools removes Bash". Their own probe shows an *absent* tool, never a denied attempt, and a Bash-less coding lane cannot run the registered evaluation — **this workstream wins** for the study verdict (CONDITIONAL); theirs stands only as "with Bash banned, this lane runs no shell commands". |
| EvE | `runtimes/eve/out/run001/closure.json` | `egress_detected` / external isolation | Full agreement with F1: shipped `codex_exec` open (their HTTP 200), `codex_tmux`/workspace-write blocked (their curl exit 7). | **Scope, not conflict**: their verdict describes EvE *as shipped*, ours the *posture*; quote both (EvE = CONDITIONAL, shipped default OPEN). **Their reachability evidence** is `rc=124` yet concludes "the agent lane is reachable" — ours (`07`, `08`, `…` rc=0) is authoritative for that claim. Their note that the shipped driver pins `gpt-5.6-sol` while the provider answered `gpt-5.6-terra` is relayed to the EvE workstream. |
| Loreley | `runtimes/loreley/out/closure.json` | `closed` / external isolation | External isolation is the mechanism; `--internal` keeps siblings while killing egress, and it cuts host loopback — both records agree. | Their `caveats` state the LLM lane "could not be exercised" and that only the evaluator/candidate lane was probed → their `closed` **does not cover the agent lane**. That caveat is now obsolete: the codex backend's `--sandbox workspace-write` posture is proven closed with a live model turn (`08`, `13`). **Theirs wins for the candidate/evaluator channel; ours for the LLM lane and the default-backend verdict** (default `kilo run --auto`, no switch, binary absent → OPEN/UNPROBEABLE). |
| SimpleLoop | `runtimes/simpleloop/out/closure.json` | `closed` / external isolation (`solver_lane: injected`) | No conflict: their record explicitly leaves the CLI lane uncovered and says a closed deployment must use `--solver injected` or run the lane inside the barrier. | **Channel now measured by this workstream**: the shipped CLI lane is closed end to end (`13`). **Ours wins for the CLI lane**; theirs stands for the injected lane. Net effect: SimpleLoop's study verdict moves from CONDITIONAL to CLOSED for its shipped argv. |

Cross-runtime consequence: all four substrates can now run under the **same** access policy on
this host (codex `workspace-write`, web search disabled) — KAPSO by one `agent_specific` key,
SimpleLoop by its shipped argv, EvE by driver switch, Loreley by backend switch. That is what
`plan:591-603` demands of the A1 comparison. EvE's shipped default stays the outlier: any EvE
arm must state which driver it ran, because `codex_exec` (open) and `codex_tmux` (closed) are
not the same experiment.

## 6. BLOCKED / UNVERIFIED, stated plainly

* **EvE end-to-end as a runtime**: no EvE campaign was launched. What is proven end to end is
  the *posture* (real codex turn + shell tool) that its `codex_tmux`/`codex_exec` drivers
  select.
* **Sub-agent sandbox overrides**: `configs/eve/optimizer/icon/immutable/.codex/agents/check-runner.toml:5`
  sets `sandbox_mode = "danger-full-access"` for a sub-agent, proving the mechanism exists. For
  circle packing the corresponding file sets no sandbox_mode. Whether a sub-agent inherits the
  parent's sandbox, and whether the agent can write such a file into its own workspace before a
  sub-agent launch, needs a live multi-agent session → UNVERIFIED.
* **KAPSO campaign machinery**: the lane command itself is now measured end to end
  (`11`, `11b`), but KAPSO's worktrees, campaign inbox and registered-evaluation trigger were
  not exercised by this workstream; the **claude** lane was not driven (its configured model id
  is reported expired by the CLI, which does not change its closure verdict).
* **Loreley default lane**: cannot run (`kilo` not installed); no Postgres/Redis started by this
  workstream; verdict for the default path is OPEN-by-construction, recorded as `inconclusive`,
  never as a pass. The candidate/evaluator lane is covered by the Loreley workstream's record.
* **SimpleLoop run level**: closure of its solver lane is settled (`13`, `13b`); a full iteration
  (proposal → `E*` → selection → traces) was not run by this workstream.
* **Provider-side tool surface** (`browser_use`, `computer_use`, `web_search`): observed only as
  CLI/provider state, not as request-level proof of what the model is offered. The provider also
  changed mid-audit (the codex relay was restored), which is exactly why the web-search front
  door must be re-probed per run rather than declared closed.
