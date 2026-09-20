# A0 — Agent CLI Restorability (`codex`, `claude`)

Owner: `a0/env/cli/**`. Date of all measurements: 2026-09-20 (CST, UTC+8).
Method: verify by execution. Every verdict below is backed by a real command whose output is in `a0/env/cli/logs/`.

## 1. Verdict

| CLI | Verdict | Blocks |
|---|---|---|
| `codex` 0.154.0 | **RESTORED — verified end-to-end** (real model call, exit 0, `PONG`, 4×) | was blocking KAPSO + EvE |
| `claude` 2.1.260 | **ALREADY WORKING — verified** (real model call, exit 0, `PONG`) | was reported as UNKNOWN; not actually blocking |

Both CLIs can now complete model calls. **No CLI is BLOCKED.**

The single root cause of the codex outage was that **a local relay the config depends on was not running.** It has been found and started.

## 2. Root cause: the relay is CC Switch's local proxy

The relay is **CC Switch** (`cc-switch-cli-bin 5.9.2`, `/usr/bin/cc-switch`) — a provider-routing tool that also runs a local OpenAI/Anthropic-compatible proxy and can "take over" the Codex live config. Prior work stopped at "nothing listens on 127.0.0.1:15722". The relay's identity is established by:

- `/home/ebt/Downloads/emsx/toapi.py:49,58` — the user's own helper script for this setup: *"本脚本主要用于接入 CC Switch 本地路由"* / *"请先在 CC Switch 中开启'本地路由'和'Codex 接管'"*.
- `cc-switch proxy show` reports the exact port codex's config points at, and names `zjapi` as the current codex provider — matching `name = "zjapi"` in `~/.codex/config.toml`.
- `~/.local/state/cc-switch/cc-switchd.log` shows this was the normal mode until 2026-07-31: `[daemon] spawned codex worker pid=1149398`.

Route topology (from `cc-switch proxy show`): Claude 15721, **Codex 15722**, Gemini 15723 — the daemon serves codex on `127.0.0.1:15722`, which is exactly the `base_url` in `~/.codex/config.toml`.

State found (before any action):

```
$ cc-switch proxy show
运行中: 否
活动路由: Claude=关闭, Codex=关闭, Gemini=关闭
- Codex: 关闭, 配置 15722
$ cc-switch daemon status
daemon not reachable: No such file or directory (os error 2)
$ curl --noproxy '*' http://127.0.0.1:15722/v1/models   # rc=7, connection refused
```

Note on a red herring: with the ambient `http_proxy=127.0.0.1:7890` left on, `curl` to 15722 returns **502** even with nothing listening (the proxy answers on behalf of the dead port). Only `--noproxy '*'` reveals the true `connection refused`. Do not read a 502 as "something is listening".

## 3. `codex` — diagnosis, fix, verification

### 3.1 The two independent faults

Fault A (the headline one): **the relay was not running.**
Fault B (revealed only after A was fixed): **`~/.codex/config.toml` had been switched to a direct-upstream form that cannot work**, because the stored upstream base URL for provider `zjapi` omits the `/v1` prefix that the upstream requires.

Evidence for B — a real codex call with no relay, exit 1 (`logs/codex_exec_after_relay.log`):

```
ERROR: unexpected status 404 Not Found: Invalid URL (POST /responses),
       url: https://zjapi.com/responses, cf-ray: ...
```

`https://zjapi.com/v1/responses` is correct and is what the relay has always forwarded to (`~/.cc-switch/logs/cc-switch.log`, 2026-07-31: `>>> 请求目标: https://zjapi.com/v1/responses`). The direct path drops `/v1` → 404. **Going "direct" is not a viable fallback for this provider; the relay is the only working path.**

### 3.2 What I changed

Nothing by hand-editing. I used the tool's own documented interface, which is also what the tool does when the user enables it in the UI:

```
cc-switch -a codex proxy enable          # → 代理路由 codex: 开启
cc-switch daemon start --detach          # → worker[codex] 127.0.0.1:15722 (pid 268112)
```

The daemon then applied **live takeover** to codex (`daemon status` → `takeovers: claude=false, codex=true`) and rewrote the live config itself, preserving a backup:

```
$ grep -E 'base_url|^model ' ~/.codex/config.toml
model = "gpt-5.6-terra"
base_url = "http://127.0.0.1:15722/v1"
```

Before the takeover, cc-switch saved the previous live config. Reading only its non-secret part:

```
$ sqlite3 ~/.cc-switch/cc-switch.db \
  "select json_extract(original_config,'\$.config') from proxy_live_backup where app_type='codex';"
base_url = "https://zjapi.com"
model = "gpt-5.6-terra"
```

So the restore is **reverting to the pre-existing design** (relay URL), not inventing a configuration.

### 3.3 Verification (real calls through the user's own config)

| # | Command | Result | Log |
|---|---|---|---|
| 1 | `codex exec -c 'model_providers.custom.base_url="http://127.0.0.1:15722/v1"' ...` | **exit 0**, `PONG`, 10,541 tok | `logs/codex_exec_via_relay.log` |
| 2 | `codex exec ...` (no override) after takeover | **exit 0**, `PONG` | `logs/codex_exec_restored_full.log` |
| 3 | cold restart: `proxy disable` effect → enable + `daemon start --detach` → `codex exec` | **exit 0**, `PONG` | `logs/codex_exec_coldstart_verified.log` |
| 4 | `codex exec --sandbox workspace-write ...` (the lane KAPSO/EvE use) | **exit 0**, `PONG` | `logs/codex_exec_workspace_write.log` |

Cross-checked in the relay's own request log (`cc-switch.db:proxy_request_logs`), all `status_code=200`:

```
request_id                            model           in_tok out_tok     usd  t
5e723a50-e23a-47db-9a02-3a1e517251be  gpt-5.6-terra    18471       6 0.02841  17:11:30
12aa8c8b-1e48-4881-92f5-7a46070767a1  gpt-5.6-terra    20207       6 0.00971  17:12:51
03f1c71f-9866-4f13-9f24-0221573f9ec1  gpt-5.6-terra    18471       6 0.03763  17:14:16
7b22b97c-6784-4709-a2e0-2400c6beee21  gpt-5.6-terra    20053       6 0.00933  17:15:35
```

**Cost:** ~$0.006–0.038 per trivial codex call (18–20k input tokens at `model_reasoning_effort = "high"`). Budget accordingly for A0.1/A1 loops.

### 3.4 The "false green" is real — and it is still green now

`codex login status` → `Logged in using an API key - ***`. This only asserts that a local auth file exists; it says nothing about the provider being reachable. It was green **while codex could not complete any call**, and it is green now. Do not use it as a liveness check for A0. A liveness check must be an actual model call.

## 4. `claude` — the `loggedIn: true` vs `doctor` "contradiction" is resolved, and claude already works

### 4.1 Diagnosis

`~/.claude/settings.json` (configuration, not the credentials file) points claude at a third-party Anthropic-compatible endpoint:

- `ANTHROPIC_BASE_URL = https://api.deepseek.com/anthropic`
- model `deepseek-v4.1-flash-expires-on-0910` (the id carries an expiry label of 09-10)
- these exact values are the stored settings of cc-switch's **current claude provider `default`** — i.e. cc-switch wrote them. (`~/.claude/settings.json` matches `providers(app_type='claude', is_current=1)` on base URL and model.)

`claude doctor` explains its own output rather than contradicting `auth status`:

```
Managed settings (remote): not fetched — not available with a custom ANTHROPIC_BASE_URL
Remote Control is only available when using Claude via api.anthropic.com. ANTHROPIC_BASE_URL is
set and does not point at api.anthropic.com, so this session is using a custom endpoint
- Not signed in to claude.ai
- Sign-in is missing the user:profile scope
```

So: `auth status`'s `loggedIn: true / oauth_token` reports that a token **exists locally**; `doctor` reports correctly that **no claude.ai account sign-in is usable** because the CLI is deliberately pointed at a third-party endpoint. This is *expected and consistent* for third-party-endpoint use — not a fault, and **not a blocker for `claude -p`**.

### 4.2 Single permitted call (used — this is the only `claude` call I made)

```
$ claude -p "Reply with exactly the word PONG and nothing else." --output-format json
exit 0
{"is_error":false,"subtype":"success","result":"PONG","num_turns":1,
 "total_cost_usd":0.10884,"modelUsage":{"deepseek-v4.1-flash-expires-on-0910":
 {"inputTokens":21753,"outputTokens":3,"costUSD":0.10884,...}}}
[claude-code:unrecognized_model] {"model":"deepseek-v4.1-flash-expires-on-0910","query_source":"generate_session_title"}
```

Raw: `logs/claude_probe_single_call.json`. **Claude works as configured.** The only blemish is a non-fatal warning that Claude Code doesn't have the model id in its known-model table (`unrecognized_model`); the call still succeeded.

**Cost warning:** $0.10884 for a 3-token answer — ~$5/M input tokens, and `cache_read_input_tokens: 0` means no prompt-cache reuse. A `claude`-driven loop is roughly **10× more expensive per call than codex** here. This matters for KAPSO, which needs both CLIs.

### 4.3 What I changed for claude

**Nothing.** It already worked, so per the "do not rewrite global config without strong justification" constraint I left `~/.claude/settings.json` alone.

Optional, not done: claude could be routed through the same relay (`cc-switch proxy show` documents the wiring `ANTHROPIC_BASE_URL=http://127.0.0.1:15721` + `ANTHROPIC_AUTH_TOKEN=proxy-placeholder`, and the claude route is configured but 关闭). That would centralise routing/failover but is **not needed** to unblock the study.

## 5. The single action the user must take

The relay is a tool run manually — there is **no systemd unit** (`systemctl --user list-units` has none) and `~/.cc-switch/settings.json` has `launchOnStartup: false`, so **it will not come back by itself after a reboot or after `cc-switch daemon stop`.** This is the one thing that needs a decision.

To restore/keep codex working, the user must run:

```bash
cc-switch -a codex proxy enable && cc-switch daemon start --detach
```

I verified this exact sequence works from a cold state (daemon stopped, route off): worker came up on `127.0.0.1:15722`, takeover re-applied `base_url = "http://127.0.0.1:15722/v1"`, and a subsequent `codex exec` returned exit 0 / `PONG`.

Two behaviours worth knowing, both measured:

- `cc-switch daemon stop` **reverts** the live config to the direct form (`base_url = "https://zjapi.com"`), which is **broken** (404). So *stopping the relay breaks codex's config*, not just its connectivity.
- `cc-switch daemon start --detach` **alone is not sufficient** after a stop — `daemon stop` also flips the route off (`proxy_config.enabled = 0` for all apps). The route must be re-enabled first. Hence the `&&` form above.

Durable option (not implemented by me): `cc-switch daemon start` is documented as suitable for running under systemd/launchd; a user unit would remove the manual step. Enabling `launchOnStartup` is a GUI-era setting and no GUI binary is currently installed (`/usr/bin/cc-switch` is the CLI-only package).

## 6. Study gating

Per protocol `open_world_plan_review.typ:475` — *"KAPSO 需要 codex 与 claude 两个 CLI 且已登录；EvE 需要 Codex CLI 并登录。登录态无法由审查侧验证，须由执行者确认。"* (also logged as risk `[S85]` at `:914`, and the E2E entry point at `:375`).

| Runtime | CLI dependency | Gate status now |
|---|---|---|
| KAPSO | **codex + claude** | **UNBLOCKED** — codex verified end-to-end; claude verified working (see caveat in §7) |
| EvE | **codex** | **UNBLOCKED** — codex verified incl. the `workspace-write` lane |
| Loreley | none (needs Postgres + Redis) | never gated on CLIs |
| SimpleLoop | shares M/P/T/E with the complex runtimes (`§4.4`), so a model lane | UNBLOCKED via codex |

The protocol's own caveat stands and is now satisfied from the executor side: login state could not be checked by the reviewers, and I have replaced every login-state assertion with an actual completed model call.

What can be executed **without** the CLIs at all: A−1 (`EID*` freezing/recompute), all of A0.1/A0.2 that does not involve a live LLM lane (adapter conformance against `E*`, trace validation, selection-semantics checks driven through each runtime's documented seam), and any Loreley work needing only Postgres/Redis. Only the *LLM-lane* portions of KAPSO and EvE required this repair.

### 6.1 Note for the other workstreams (stale verdicts)

- **`a0/closure` concluded the model lane was BLOCKED, and that verdict is now stale for codex.** Its own `a0/closure/evidence/07_model_lane_blocked.log` (17:15:18) records the relay `LISTEN`ing on 15722 and *"one codex model call → OK … rc=0"* — i.e. it was already running against the relay I had restored minutes earlier. The file's "blocked" framing rests on the claude block in the same log, which quotes `claude doctor`'s claude.ai lines. **Those lines are not evidence of failure** (see §4.1): claude is pointed at a third-party endpoint by design, and `claude -p` completes successfully.
- **Independent corroboration that codex's full agentic lane works, not just text replies.** `a0/closure/evidence/08_e2e_codex_workspace_write.jsonl` shows a real `codex exec --sandbox workspace-write` run emitting `thread.started` → `turn.started` → an `item.completed` **`command_execution`** with `exit_code: 0` — codex actually executed a shell probe. `a0/closure/evidence/06_simpleloop_codex-danger-full-access.log` shows the same for `--dangerously-bypass-approvals-and-sandbox` (`VERDICT codex-sandbox-danger-full-access: CONFIRMED`). Both were produced *through the relay I restored*, so the model lane for the lanes KAPSO/EvE use is verified by a second, independent workstream.
- **Recommendation:** re-run any closure/A0 step that was marked BLOCKED on "no model lane" before treating it as a finding.

## 7. Disclosures, limits, and residual risk

**Honesty items I must not bury:**

1. **I accidentally surfaced a credential fragment.** Dumping the pre-takeover backup (`proxy_live_backup.original_config`) printed a `sk-…` API key prefix in my tool output. That was my error: I should have filtered to the `config` field from the start (which I did immediately after). The value is not repeated here and I will not propagate it. **If this session's transcript is shared or stored anywhere, that codex/zjapi key should be rotated.**
2. **An unattributed change to the user's codex config happened during my run.** At exactly `2026-09-20 16:35:00` — *before* my first mutating command (`cc-switch proxy serve`, 16:37:35) — both `~/.codex/config.toml` and `~/.codex/auth.json` were rewritten (mtime identical to the millisecond) to the direct `https://zjapi.com` form, and `proxy_config(updated_at)` was touched. At my first read (a few minutes earlier) the config still pointed at the relay and carried `model = "gpt-5.6-sol"`. I did not do this and cannot attribute it; it was most likely a `provider use`-style switch performed by the user or another workstream. My takeover later restored the relay URL but kept the newer `model = "gpt-5.6-terra"` — **if `gpt-5.6-sol` was the intended model, that is a loose end I did not resolve.** The agent bus shows no other window claiming these files (`bus busy` → 空闲 for both `~/.codex/config.toml` and `~/.cc-switch/cc-switch.db`; no matching posts). The most plausible author is the concurrently-running `a0/closure` workstream (it was probing codex surfaces and applying sandbox modes in the same window), but I have no direct evidence of that and am not asserting it as fact.
3. **One persisted cc-switch field changed as a side effect.** `proxy_config.proxy_enabled` went `1 → 0` for `claude`, `gemini`, `grokbuild` (it was `1` for all apps before; `codex` is back to `1`). Their routes were already 关闭 before and after, so this is behaviourally inert, but the CLI offers no way to set that field without *activating* a route, so I left it off rather than turning on routes nobody asked for.
4. **Claude's non-interactive lane is only partly verified.** I was limited to one `claude` call and used it on a plain `claude -p`. The flags KAPSO actually uses (permission-bypass / sandboxed invocation) were **not** exercised → **UNVERIFIED**. Only the model+auth+endpoint path is verified.
5. **Runtime-internal invocation is UNVERIFIED.** I drove the CLIs directly. Whether KAPSO/EvE spawn them with an env that still reaches `127.0.0.1:15722` (e.g. their own `PATH`/env probing, or a containerised lane that would break host loopback) is an A0.1 concern for those workstreams, not something this repair proves.
6. **The upstream is not perfectly reliable near-term.** Three transient failures appear in today's relay log at 0 tokens, each retried successfully by codex: 2× `502 proxy request failed: stream terminated before completion`, 1× `504 proxy timeout: error sending request for url (https://zjapi.com/v1/responses)`. `zjapi.com` itself answers direct and via the ambient proxy in ~0.75 s, so this is not a local-proxy or `http_proxy` problem. **Caveat on attribution:** two of the three timestamps (17:14:57, 17:15:20) coincide with the `a0/closure` workstream's concurrent codex probes (`evidence/06_*`, 17:14:48–50), so they may be artifacts of parallel load rather than upstream flakiness. Either way, **relevant to §4.2's false-green warning:** EvE silently maps evaluation exceptions to `failure_score(0.0)`, so a transient model-lane 502 during an EvE run could look like a genuine zero. Recommend retry-count evidence in the A0.2 traces.

## 8. Evidence index (all under `a0/env/cli/logs/`)

| File | Shows |
|---|---|
| `codex_exec_after_relay.log` | direct-upstream 404, exit 1 (the broken state) |
| `codex_exec_via_relay.log` | exit 0 / `PONG` via relay override (10,541 tok) |
| `codex_exec_restored_full.log` | exit 0 / `PONG` with the user's real config after takeover |
| `codex_exec_coldstart_verified.log` | exit 0 / `PONG` after cold `enable && daemon start` |
| `codex_exec_workspace_write.log` | exit 0 / `PONG` in the `workspace-write` lane |
| `claude_probe_single_call.json` | the one claude call: exit 0, `PONG`, $0.10884, `unrecognized_model` warning |
| `proxy_serve_codex.log`, `proxy_serve_codex_15722.log` | foreground relay start; note the default listen port is 15721, codex needs 15722 |

External state referenced (read-only): `~/.cc-switch/logs/cc-switch.log`, `~/.local/state/cc-switch/cc-switchd.log`, `~/.cc-switch/cc-switch.db` (`proxy_config`, `proxy_live_backup`, `proxy_request_logs`), `~/.codex/config.toml`, `~/.claude/settings.json`, `Downloads/emsx/toapi.py`.

Current end state: relay daemon running (`worker[codex] 127.0.0.1:15722`), `takeovers: codex=true`, codex config at the relay URL, claude untouched and working.
