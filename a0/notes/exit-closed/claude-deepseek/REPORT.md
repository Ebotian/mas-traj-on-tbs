# Claude CLI backed by DeepSeek — the KAPSO default-lane path

Owner: `a0/notes/exit-closed/claude-deepseek/**`. Date of all measurements: 2026-09-21 (CST, UTC+8).
Method: execution only. Every verdict below is **verified by running it** unless labelled
*read from source* or *inferred*. No package was installed. No global config file was modified.
Key material was passed only through environment variables in the same shell command that used it;
no artefact under this directory contains the key (checked, §9).

---

## 1. One-line verdict

**The `claude` CLI drives DeepSeek's Anthropic-compatible endpoint through a complete agentic
loop — tools, streaming, prompt caching, session resume — with no code change and no new
dependency; but the CLI has no config-home isolation, and the user-global
`~/.claude/settings.json` silently overrides the `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`
that KAPSO's adapter sets, so the lane must be launched with `CLAUDE_CONFIG_DIR` pointed at a
project-local directory or its configured endpoint is ignored. Pin `deepseek-flash`.**

---

## 2. Auth: which env var the CLI honors (determined by experiment, zero model spend)

A local capture-only mock (`evidence/mock_anthropic.py`, port 8799) recorded the request headers
the CLI actually sends. It logs presence + a sha256 fingerprint, never a header value.

| Probe | Process env set | Header observed at the mock | Conclusion |
|---|---|---|---|
| A | `ANTHROPIC_API_KEY` only | `x-api-key: <present>` — **no** `authorization` | `ANTHROPIC_API_KEY` → `x-api-key` |
| B | `ANTHROPIC_AUTH_TOKEN` only | `authorization: <present>` — **no** `x-api-key` | `ANTHROPIC_AUTH_TOKEN` → `Authorization: Bearer` |
| C | both | **both** headers on every request | if both are set, both are sent |

Both forms are accepted by DeepSeek (`HTTP 200` with `x-api-key` **and** with
`Authorization: Bearer`), so either variable works. This matters because **KAPSO's
`oss_claude_code` adapter sets `ANTHROPIC_AUTH_TOKEN` and never `ANTHROPIC_API_KEY`**
(`adapters/oss_claude_code_agent.py:110-111`) — that is the variable to use.

No `claude login` / `claude setup-token` was run; `claude auth status` was only read (§7).

---

## 3. The real agentic runs

All runs used `claude -p` non-interactively with an isolated config home, the real endpoint, and a
tiny task. Working directories are under `scratch/`; every claim below was re-checked from the
filesystem after the process exited.

Common env (exact):

```
CLAUDE_CONFIG_DIR=<this dir>/home/<run>          # isolates ~/.claude entirely
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=<value of the deepseek: line of ~/gptapi.md, passed as an env var only>
ANTHROPIC_MODEL / ANTHROPIC_SMALL_FAST_MODEL / ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS}_MODEL = <pinned id>
CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000
claude -p "<task>" --output-format stream-json --verbose --dangerously-skip-permissions
```

### 3.1 Run 1 — tool loop on `deepseek-flash` (`scratch/run1/`)

Task: write `hello.py`, run `python3 hello.py`, capture stdout into `result.txt`.

**Filesystem verification (independent of the model's own claim):**

```
$ ls scratch/run1
hello.py  result.txt
$ cat scratch/run1/hello.py      →  print("CLAUDE_DEEPSEEK_OK")
$ cat scratch/run1/result.txt    →  CLAUDE_DEEPSEEK_OK
```

The stream proves the work was real, not hallucinated — `assistant` events contain actual
`tool_use` blocks:

```
tool_use Write  {"file_path":"…/scratch/run1/hello.py","content":"print(\"CLAUDE_DEEPSEEK_OK\")\n"}
tool_use Bash   {"command":"python3 hello.py","description":"Run hello.py"}
tool_use Write  {"file_path":"…/scratch/run1/result.txt","content":"CLAUDE_DEEPSEEK_OK\n"}
```

Result: `subtype=success`, `num_turns=4`, `duration_ms=5453`, `terminal_reason=completed`,
`permissionMode=bypassPermissions`, exit 0.

### 3.2 Run 2 — KAPSO's score-of-record shape on `deepseek-v4-pro` (`scratch/run2-worktree/`)

This is the decisive KAPSO test. Task: create `kapso_evaluation/kapso_eval.py`, then **execute the
exact command KAPSO's score of record requires** in the worktree:

`python3 kapso_evaluation/kapso_eval.py --fidelity 1 --fraction 0.5 --seed 7`

and write its stdout to `score.txt`.

**Filesystem verification:**

```
$ find scratch/run2-worktree -type f
./kapso_evaluation/kapso_eval.py
./score.txt
$ cat scratch/run2-worktree/score.txt
KAPSO_EVAL_MANIFEST {"fidelity": 1, "fraction": 0.5, "seed": 7, "score": 0.42}
```

Result: `subtype=success`, `num_turns=4`, `duration_ms=12580`, exit 0.
**A `claude` session running on DeepSeek can create a file, run a shell command in a working
directory, and produce the manifest line — the thing `registered_evaluation.py` reads.**

### 3.3 Run 3 — `--session-id` / `--resume` (KAPSO's inbox continuation)

```
call1  --session-id ed6e87eb-…  → result 'OK'      session=ed6e87eb-…  cache_read=0
call2  --resume   ed6e87eb-…    → result 'MARLIN7' session=ed6e87eb-…  cache_read=19712
```

Both exit 0, same session id, and the second call **recalled a codeword given in the first** —
so conversation state and the prompt cache both survive a resume across processes. KAPSO's
`--session-id` / `--resume` argv (`claude_code_agent.py:1179-1190`) works unchanged.

### 3.4 Run 4 — prompt on **stdin** (KAPSO's delivery path)

KAPSO deliberately does not put the prompt in argv (`claude_code_agent.py:1176-1182`, to stop an
agent's own `pkill -f` matching its ancestor). Verified with `printf '…' | claude -p`:

```
$ cat scratch/run4-stdin/stdin_ok.txt   →  STDINOK
result: success  turns: 2  exit 0
```

---

## 4. Model id actually served

| Requested `model` | Response `model` field | HTTP |
|---|---|---|
| `deepseek-flash` | `deepseek-flash` | 200 |
| `deepseek-v4-pro` | `deepseek-v4-pro` | 200 |
| `deepseek-v4.1-flash-expires-on-0910` | `deepseek-v4.1-flash-expires-on-0910` | 200 |
| `definitely-not-a-model` | — | **400** `The supported API model names are deepseek-flash, deepseek-v4-pro` |

The endpoint **strictly validates the model id**: an unknown id is a hard 400, not a silent
fallback. `GET /models` returns exactly `deepseek-flash` and `deepseek-v4-pro`. Note that the
undocumented `deepseek-v4.1-flash-expires-on-0910` is still *routable* despite its name — the
endpoint echoes the requested id rather than a canonical served id, so "what was served" cannot be
read off the response for alias ids. `modelUsage.canonicalModel` in the CLI's own output reported
`deepseek-flash` / `deepseek-v4-pro` / `deepseek-v4.1-flash-expires-on-0910` respectively.

### 4.1 Which id should the lane pin — `deepseek-flash`

Per [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing) (read from source, not
measured): `deepseek-flash` = DeepSeek-V4.1-Flash, `deepseek-v4-pro` = DeepSeek-V4-Pro-0813, both
1M context / 384K max output / tool calls / Anthropic API. Flash costs **4.4× less** on cache miss
($0.15 vs $0.66 per 1M off-peak) and 3.3× less on output.

Measured on this host: **both ids completed the identical 4-turn agentic task**; flash was faster
(5.5 s vs 12.6 s wall, 6.7 s vs 19.3 s API time). Recommend **`deepseek-flash`** as the lane pin.

* Pin the *canonical* id, not an alias: `deepseek-v4-flash` is documented as accepted-but-retired
  and billed at Flash price, and `deepseek-v4.1-flash-expires-on-0910` (the value currently in the
  user's global settings) is undocumented and self-describing as expiring — its billing class is
  **unknown**, since the docs only name `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` as
  legacy-accepted aliases.
* Escalate to `deepseek-v4-pro` only for a specific hard role, per-role, via its own config block.

---

## 5. Streaming, prompt caching, thinking

**Streaming — verified.** `POST /anthropic/v1/messages` with `stream:true` returns a well-formed
Anthropic SSE stream (`evidence/sse_tooluse.txt`):

```
event: message_start / ping / content_block_start ×2 / content_block_delta ×11 / content_block_stop ×2 / message_delta / message_stop
```

and a real tool call comes back in the streamed body:

```
{"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"call_00_I1XR…","name":"get_time","input":{}}}
{"type":"message_delta","delta":{"stop_reason":"tool_use",…}}
```

`stop_reason: "tool_use"` is correct, so Claude Code's loop terminates turns properly. The
endpoint also accepts and ignores the CLI's whole `anthropic-beta` header list (9 betas:
`claude-code-20250219`, `context-1m-2025-08-07`, `prompt-caching-scope-2026-01-05`,
`mid-conversation-system-2026-04-07`, `effort-2025-11-24`, …).

**Prompt caching — works.** Every run reported non-zero `cache_read_input_tokens`
(60 032 / 61 056 / 19 840 / 19 712 across runs) and DeepSeek bills cache hits at $0.003–0.006 per
1M instead of $0.15–0.30. Caveat: `cache_creation_input_tokens` was **0 on every single
response**, even the first call of a session. DeepSeek appears to report only hits, never
creations — do not build cost logic that requires a non-zero creation count. Claude Code's
`cache_control:{type:"ephemeral"}` markers are accepted (2 system blocks carry them).

**Thinking.** The CLI sends `thinking:{"type":"adaptive","display":"omitted"}`,
`output_config:{"effort":"high"}` and `context_management:{"edits":[{"type":"clear_thinking_20251015"}]}`.
DeepSeek accepts all of it (HTTP 200). By default the endpoint **does** return `thinking` blocks,
but the CLI asked for them omitted, and the reported `thinking_tokens` was 0 in every run.
Thinking can be switched off outright — `thinking:{"type":"disabled"}` yields a plain text
response with no thinking block and no wasted output budget (verified by curl). Do this if the
lane's cost profile matters.

**Request shape actually sent** (captured free at the mock, `logs/mock_bodies.json`):
22 tool schemas (`Agent, Bash, Cron*, DesignSync, Edit, Enter/ExitWorktree, ListAgents,
NotebookEdit, Read, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskOutput, TaskStop,
WebFetch, WebSearch, Workflow, Write`), `max_tokens=64000`, ~10.3k characters of system prompt
across 3 blocks, and a `role:"system"` entry **inside the messages array** (the
`mid-conversation-system` beta). DeepSeek accepted that system-role message (HTTP 200) — a real
compatibility risk that did **not** materialise.

---

## 6. Token usage, and why the CLI's cost figure is wrong

| Run | model | input | cache_read | output | claude `total_cost_usd` | **real DeepSeek cost (peak)** |
|---|---|---|---|---|---|---|
| run1 tool loop | flash | 20 515 | 60 032 | 266 | $0.145856 | **$0.006834** |
| run2 KAPSO-shaped | pro | 20 403 | 61 056 | 460 | $0.158198 | **$0.031440** |
| run3 call1 (`--session-id`) | flash | 19 831 | 0 | 2 | $0.104605 | **$0.005952** |
| run3 call2 (`--resume`) | flash | 172 | 19 712 | 4 | $0.010816 | **$0.000175** |
| run4 stdin | flash | 20 018 | 19 840 | 94 | $0.121390 | **$0.006237** |
| probe D (global-config override) | alias | 22 015 | 0 | 2 | $0.110125 | **$0.006607** |
| SSE `tool_use` curl probe | flash | 276 | 0 | 44 | n/a | $0.000136 |
| **total** | | | | | **$0.651** (fictional) | **≈ $0.058**, plus ~15 sub-300-token curl probes (<$0.0005) |

**The bottom line on cost: real spend for this entire audit is ~US$0.058 at peak rates** (and
02:37 UTC Monday is peak — [pricing](https://api-docs.deepseek.com/quick_start/pricing): peak is
01:00–04:00 and 06:00–10:00 UTC Mon–Fri; off-peak is half). Far under the US$0.30 budget.

**Do not trust `total_cost_usd`.** It is ~10× the truth. The model is not in Claude Code's price
table, so the CLI prices it with its own heuristic and flags `"costBasis":"unknown"` in
`modelUsage`; it reported $0.145856 for work DeepSeek billed at $0.0068. KAPSO must **not** use
this field for the study's cost trace. The endpoint exposes the real driver — token counts — in
`usage`, so price from token counts against DeepSeek's published table. (Same failure the prior
CLI report saw: "$5/M input tokens" is Claude Code's estimate, not DeepSeek's price.)

Useful constant observed on this host: **every plain `claude -p` call costs ~20k input tokens**
before any work — 19 831 / 20 018 / 20 403 / 20 515 / 22 015 — i.e. Claude Code's system prompt +
22 tool schemas. Cache reads absorb most of the repeat cost across turns.

---

## 7. Limits observed

| Limit | Observed |
|---|---|
| Context window | DeepSeek documents **1M**; `modelUsage.contextWindow` defaulted to **1 000 000** with no override, and honoured `CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000` when set. `CLAUDE_CODE_MAX_CONTEXT_TOKENS` is the knob that controls auto-compaction. |
| Max output | `max_tokens=64000` (the CLI's default) accepted with HTTP 200; DeepSeek documents 384K max output. |
| Wall-clock | No timeout was hit. run1 5.5 s, run2 12.6 s, run3 call2 0.9 s API. I capped runs at 200–300 s; KAPSO's own per-session timeout was never approached. |
| Model validation | Hard 400 on an unknown model id — no fallback. `--fallback-model` pointed at a non-existent id would therefore break rather than degrade. |
| Model aliases | `claude-*` ids fail (400). All model slots must be pointed at DeepSeek ids; the CLI otherwise routes its internal "small/fast" and subagent calls to Anthropic ids the endpoint rejects. |
| Auth | Both `x-api-key` and `Authorization: Bearer` accepted. |
| Rate/concurrency | Not hit. DeepSeek documents concurrency 2500 (flash) / 500 (pro). |

---

## 8. Config-home handling — the finding that decides the KAPSO question

This is the direct analogue of the `CODEX_HOME` issue the Loreley report found, but **inverted:
`claude` has no isolation at all, and its user-global settings file outranks the process
environment.**

| Probe | What `settings.json` says | What the process env says | What actually happened |
|---|---|---|---|
| D | `~/.claude/settings.json`: base_url = DeepSeek, model = `…expires-on-0910` | base_url = mock, `ANTHROPIC_MODEL=deepseek-flash` | **The mock got zero requests.** The CLI called DeepSeek with the *settings-file* model and the *settings-file* endpoint. Cost: a real $0.0066. |
| E | custom `CLAUDE_CONFIG_DIR` with settings.json base_url = mock | base_url = unreachable `127.0.0.1:1`, `ANTHROPIC_API_KEY` set | The **mock** was hit (settings.json won), and the process-env `ANTHROPIC_API_KEY` was still sent **alongside** the settings-file `AUTH_TOKEN` — two conflicting credentials on one request. |
| F | custom settings.json model = `…expires-on-0910` | argv `--model deepseek-v4-pro` | The CLI requested **`deepseek-v4-pro`** — the argv flag wins. |

Verified precedence, highest first:

1. `--model` argv flag — **wins over everything** (probe F). KAPSO's argv pin
   (`_build_command`, `claude_code_agent.py:1200`) is therefore effective.
2. `<config home>/settings.json` — its `model` and its `env` block **override the process
   environment** (probes D and E).
3. process environment (honoured only for names settings.json does not define).

`CLAUDE_CONFIG_DIR` **does** relocate everything — settings, state, `.claude.json` sessions,
`projects/`, `backups/` — and was verified working in every run (§3): fresh, empty config
directories required no onboarding and no trust prompt with `-p`. It is the isolation knob.

### 8.1 Consequences for KAPSO (read from source, then verified where stated)

* KAPSO's `claude` adapters build the child env from `os.environ.copy()`
  (`claude_code_agent.py:329-333`) and **never set `HOME` or `CLAUDE_CONFIG_DIR`**, so the child
  `claude` reads the real `~/.claude/settings.json`.
* `oss_claude_code` sets `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` in that child env
  (`oss_claude_code_agent.py:108-109`) — **and probe E shows a `settings.json` in the config home
  will silently override them.** Today this is benign only because the user's global
  settings.json points at the *same* `https://api.deepseek.com/anthropic`. It is not benign in
  general: `agent_specific.base_url` can be configured, validated, and then **ignored at runtime**
  with no error.
* The default `claude_code` lane sets **no endpoint at all** and, in the auth mode this host
  resolves to (`oauth_token`, §7/§9), `_get_env` explicitly **pops `ANTHROPIC_API_KEY` and
  `ANTHROPIC_AUTH_TOKEN` from the child environment** (`claude_code_agent.py:1236-1246`). So the
  default lane can only reach DeepSeek if the endpoint + credential live in the CLI's *own*
  config file — i.e. it depends on the global `~/.claude/settings.json`.
* **Zero-code-change way to get both isolation and scoped config:** export
  `CLAUDE_CONFIG_DIR=<project-local dir>` in the environment KAPSO is launched with (the child
  inherits it), and keep the `oss_claude_code` lane config (`base_url` + `auth_token_env`). With
  no `settings.json` in that directory, the adapter's env vars are honoured, the key stays in an
  environment variable, and no global file is touched — verified by probes B/C and every run in §3.
  If the default `claude_code` lane must be used instead, that directory needs its own
  `settings.json`; its `env` block has **no env-var reference syntax**, so the key would have to be
  written literally, unless `apiKeyHelper` is used to shell out for it.

---

## 9. Failure modes (all negative results found, none of them fatal)

1. **`unrecognized_model` warning on every call** — e.g.
   `[claude-code:unrecognized_model] {"model":"deepseek-flash","query_source":"generate_session_title"}`.
   Non-fatal (exit 0), but it is also the signal that the CLI is pricing and sizing the model from
   a table that does not contain it (§6). It means `total_cost_usd` and the reported context/output
   ceilings are unreliable for DeepSeek ids.
2. **`settings.json` silently wins over process env** (§8) — the one that can silently misroute a
   lane.
3. **Both auth headers sent when both vars are present** (probe C, probe E) — an ambiguous
   credential state the CLI does not guard against.
4. **`cache_creation_input_tokens` always 0** — cost accounting must not depend on it.
5. **Strict model-id validation** (400) — no graceful degradation, and `preflight.resolve_cli`
   resolves an unknown model name to **codex**, not claude (§10).
6. **Pre-existing global config carries a stale model id in plain text**
   (`~/.claude/settings.json`: `deepseek-v4.1-flash-expires-on-0910`). It still answers HTTP 200
   today, so it is not currently broken — but it is an undocumented, self-expiring alias in a
   global file, and the same file holds the provider key in cleartext. Flagged, **not modified**
   (mine, not my call to change; §11).
7. **Not tested:** MCP servers (KAPSO mounts `repo_memory` / research gates for this lane), the
   server-side `WebSearch`/`WebFetch` tools (DeepSeek has no such server-side tool, and KAPSO's
   `research` role needs live web — untouched by this audit), subagent spawning, and the
   `--restricted` / `--bare` flags. Also untested: behaviour under KAPSO's real 18–20k-token
   protocol prompts and long campaigns.

---

## 10. What this implies for KAPSO

* **The score-of-record channel is open.** Run 2 is exactly the required shape: the session itself
  ran `python kapso_evaluation/kapso_eval.py --fidelity 1 --fraction 0.5 --seed 7` inside the
  worktree and wrote the `KAPSO_EVAL_MANIFEST` line. The `Bash` tool is present and works in the
  configured working directory; `--dangerously-skip-permissions` auto-approves it.
* **The flags KAPSO uses are all verified**: `-p` with the prompt on **stdin**, `--output-format
  stream-json --verbose`, `--dangerously-skip-permissions`, `--session-id`, `--resume`, `--model`.
  This closes the "non-interactive lane only partly verified / UNVERIFIED" gap in
  `a0/env/cli/CLI_REPORT.md:200`.
* **It is a config swap, not a code change, for KAPSO's claude lane** — so the ~10-site patch in
  `a0/notes/exit-closed/kapso/REPORT.md` §6 is **not** required on account of the claude lane.
  The `claude_code` / `oss_claude_code` lanes survive with a DeepSeek endpoint.
  (`oss_claude_code` is the better seam: `agent_specific: {base_url, auth_token_env}` keeps the key
  in an env var and names the variable rather than embedding a value.)
* **Two workarounds the lane needs, both zero-code:**
  1. Set `CLAUDE_CONFIG_DIR` to a project-local directory when launching KAPSO, or the user-global
     `~/.claude/settings.json` overrides the configured endpoint (§8).
  2. Make sure no config block lets the CLI be resolved from the model name. **`deepseek-flash`
     does not start with `claude`, and `preflight.resolve_cli` falls back to `codex` for any model
     whose name does not** — *read from source*, `core/preflight.py:211-222`:
     `return "claude_code" if model_name.startswith("claude") else "codex"`. So a block with
     `model: deepseek-flash` and no explicit `type:`/`cli:` resolves to the **retired codex CLI**.
     Set `type: claude_code` (or `oss_claude_code`) explicitly on every block whose model is a
     DeepSeek id. This is the sharpest trap on this path.
* **Model pinning works**: `--model` outranks the settings file (probe F), so KAPSO's
  `config.model` → `--model` is authoritative. It must be exactly `deepseek-flash` or
  `deepseek-v4-pro`; anything else is a hard 400.
* **Cost telemetry**: KAPSO estimates cost from output length for this adapter
  (`claude_code_agent.py:1295` per the KAPSO report). For a DeepSeek-backed lane that estimate has
  no relationship to the bill, and neither does the CLI's own `total_cost_usd`. Price from the
  token counts in the `result` event.

---

## 11. Machine state — what I started, how to stop it, what I touched

* **Started and stopped a local mock server** (`evidence/mock_anthropic.py`, port 8799, pid in
  `.mock.pid`). It is **stopped**: port 8799 is free and a curl to it returns `000`. To re-run:
  `python3 evidence/mock_anthropic.py 8799 "$PWD/logs/mock_headers.log" "$PWD/logs/mock_bodies.json" &`
  then `kill <pid>`. It binds loopback only and was used solely for header/body capture; the last
  session used a pidfile after `pkill -f mock_anthropic.py` matched its own shell and killed it.
* **No long-running service, container or daemon is left behind.** `adapdc-catalog-postgres-1` was
  never touched (`Up About an hour (healthy)`).
* **No global config file was modified.** `~/.claude/settings.json` is byte-for-byte unchanged
  (555 bytes, mtime 2026-09-09 10:20) — its stale model id and cleartext key are reported, not
  edited. `~/.claude.json` unchanged (mtime 2026-09-10).
* **One unavoidable global-state side effect:** probe D had to run with the user's real config
  home, so Claude Code wrote a session transcript under
  `~/.claude/projects/-home-ebt-rsi-dev-a0-notes-exit-closed-claude-deepseek/`. Safe to delete;
  nothing else under `~/.claude` was written by this audit. Every later run used
  `CLAUDE_CONFIG_DIR`, so its state landed under `home/<run>/` here instead.
* **Key hygiene:** the real key appears in **no** file under this directory (grepped for its exact
  value — no match). Only fake placeholders (`sk-fake-token-from-settings`, `sk-probe-*`) were
  written. The key was passed only as an env var in the same shell command that used it, and the
  capture mock fingerprints header values with sha256 instead of storing them.
* **No packages installed.**

---

## 12. Verification log

Auth determination (free — mock server on 127.0.0.1:8799):

```
python3 evidence/mock_anthropic.py 8799 "$PWD/logs/mock_headers.log" "$PWD/logs/mock_bodies.json" &
env -i PATH=/usr/bin:/bin HOME=/home/ebt TERM=dumb CLAUDE_CONFIG_DIR="$PWD/home/api_key_only" \
    ANTHROPIC_BASE_URL=http://127.0.0.1:8799 ANTHROPIC_API_KEY=sk-probe-FAKEKEY-AAAA \
    claude -p "reply OK" --output-format json            # → x-api-key
# …and the same with ANTHROPIC_AUTH_TOKEN → authorization …and with both → both headers
```

Real runs (key read from `~/gptapi.md`, used as an env var only):

```
DS_KEY=$(grep '^deepseek:' ~/gptapi.md | cut -d: -f2- | tr -d '[:space:]')
env -i PATH=/usr/bin:/bin HOME=/home/ebt TERM=dumb \
  CLAUDE_CONFIG_DIR=<dir> ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
  ANTHROPIC_AUTH_TOKEN="$DS_KEY" ANTHROPIC_MODEL=deepseek-flash \
  ANTHROPIC_SMALL_FAST_MODEL=deepseek-flash CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000 \
  claude -p "<task>" --output-format stream-json --verbose --dangerously-skip-permissions
```

Endpoint probes (curl, `x-api-key`): `/models`; per-model messages with
`thinking:{"type":"disabled"}`; `stream:true` + a `tools` array (SSE event inventory and
`stop_reason:"tool_use"` in `evidence/sse_tooluse.txt`); `role:"system"` inside `messages`;
the 9-beta header list; `max_tokens=64000`; a bogus model id (400); and the stale alias id (200).

KAPSO source anchors (read-only): `adapters/oss_claude_code_agent.py:36-52,55-116`;
`adapters/claude_code_agent.py:236-270,329-333,1170-1240`;
`core/preflight.py:200-232`.

### Evidence index

| Artefact | Contents |
|---|---|
| `evidence/mock_anthropic.py` | the capture-only mock; sha256-fingerprints auth headers, writes full bodies |
| `evidence/sse_tooluse.txt` | raw SSE stream with a real `tool_use` block and `stop_reason:"tool_use"` |
| `logs/mock_headers_apikey.log`, `logs/mock_headers.log` | header captures for the auth probes |
| `logs/mock_bodies.json` | exact request bodies: model, max_tokens, 22 tools, system-block sizes, `thinking`/`output_config` |
| `logs/probe_apikey_only.out`, `…authtoken_only.out`, `…both_set.out` | the three auth-variable probes |
| `logs/probe_global_precedence.out` | probe D: global settings won; stale model used; real cost $0.110125 (fictional) |
| `logs/probe_precedence.out` | probe E: settings.json beat an unreachable process-env base_url |
| `logs/probe_flag.out` | probe F: `--model` outranked the settings-file model |
| `scratch/run1.stream.jsonl`, `scratch/run1/{hello.py,result.txt}` | run 1: tool loop, filesystem-verified |
| `logs/run2.stream.jsonl`, `scratch/run2-worktree/{kapso_evaluation/kapso_eval.py,score.txt}` | run 2: the KAPSO score-of-record shape |
| `logs/run3_call1.json`, `logs/run3_call2.json` | session id / resume with codeword recall and cache reuse |
| `logs/run4.stream.jsonl`, `scratch/run4-stdin/stdin_ok.txt` | prompt delivered on stdin |
| `home/<run>/` | isolated `CLAUDE_CONFIG_DIR`s, showing what the CLI writes where |
