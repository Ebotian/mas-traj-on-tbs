# Claude CLI 2.1.278 backed by DeepSeek — re-verification of the KAPSO recipe

Owner: `a0/notes/exit-closed/claude-deepseek-2.1.278/**`. Measured 2026-09-21 (CST, UTC+8).

**Version actually tested: `2.1.278 (Claude Code)`** — `/usr/bin/claude --version` → `2.1.278 (Claude Code)`.
Baseline being re-tested: the 2.1.260 results in `../claude-deepseek/REPORT.md`.

Method: execution only. Every verdict is **verified by running it** unless labelled *read from source*
or *inferred*. The prior audit's conclusions were not re-derived from scratch — only the
version-sensitive parts were re-run. No package installed. No global config modified. Key passed
only as an env var in the same shell command that used it; no artefact here contains it (§7).

---

## 1. Verdict

**Yes — the KAPSO recipe still holds verbatim on 2.1.278.** All four behaviours it rests on
reproduce identically, the credential-header mapping is unchanged, and a real agentic run on
`deepseek-flash` completes with tools, streaming and non-zero cache reads.

The recipe is unchanged: **`CLAUDE_CONFIG_DIR` isolation + explicit `type:` on the config block +
pinning `deepseek-flash`.** No amendment is required, and no delta found below touches it.

The one substantive CLI-level behaviour change on this upgrade is **the `TaskOutput` tool is gone**
(22 → 21 tools). It does not appear in any code path KAPSO's claude lanes depend on.

---

## 2. Credential header mapping — unchanged (zero model spend)

Re-ran the prior capture-only mock (`evidence/mock_anthropic.py`, port 8788; sha256-fingerprints
auth headers, never stores values) with three single-variable probes.

| Probe | Process env | Headers observed at the mock | 2.1.260 | Verdict |
|---|---|---|---|---|
| A | `ANTHROPIC_API_KEY` only | `x-api-key` present, **no** `authorization` | same | **confirmed** |
| B | `ANTHROPIC_AUTH_TOKEN` only | `authorization` present, **no** `x-api-key` | same | **confirmed** |
| C | both | **both** headers on every request | same | **confirmed** |

`ANTHROPIC_API_KEY` → `x-api-key`; `ANTHROPIC_AUTH_TOKEN` → `Authorization: Bearer <token>`
(len = 7 + token length, i.e. a literal `Bearer ` prefix). KAPSO's `oss_claude_code` adapter sets
`ANTHROPIC_AUTH_TOKEN` (`.../adapters/oss_claude_code_agent.py:108-109`, re-read at commit
`7d99b15`, unchanged), so the Bearer path is the one that matters — still correct.

---

## 3. Precedence — all four behaviours reproduce

| # | Behaviour the recipe rests on | Probe | Observed on 2.1.278 | vs 2.1.260 |
|---|---|---|---|---|
| 1 | config-home `settings.json` outranks process env for **endpoint and model** | E | mock was hit although process-env `ANTHROPIC_BASE_URL=http://127.0.0.1:1` was unreachable, and the request carried the **settings-file model**, not `ANTHROPIC_MODEL` | same |
| 2 | …and for the **global** `~/.claude/settings.json` specifically | D | mock request count **13 → 13 (zero)**; the call went to `api.deepseek.com` with the settings-file model | same |
| 3 | argv `--model` outranks the settings file | F | body `model=deepseek-v4-pro` although settings said `SETTINGS_MODEL_WINS` | same |
| 4 | `CLAUDE_CONFIG_DIR` relocates settings+state; a fresh empty dir needs no onboarding/trust prompt | G | fresh dir, exit 0, answered against the mock, **no** prompt; wrote `.claude.json` with `firstStartVersion: "2.1.278"` | same |

Exact observations:

* **Probe E** (`home/precedence/settings.json` → mock; process env → `127.0.0.1:1`,
  `ANTHROPIC_MODEL=ENV_MODEL_LOSES`, `ANTHROPIC_API_KEY=sk-probe-…`):
  mock requests #8/#9 show `BODY model=SETTINGS_MODEL_WINS`, `authorization` = the **settings-file**
  token, and `x-api-key` = the **process-env** key on the same request. So the settings file wins the
  endpoint *and* the model, while the ambient `ANTHROPIC_API_KEY` still rides along — two conflicting
  credentials on one request, exactly as in 2.1.260.
* **Probe D** (real `HOME=~`, i.e. the real `~/.claude/settings.json`; process env → mock):
  `grep -c '=== request'` was 13 before and 13 after. Mock got **nothing**. `modelUsage` key was
  `deepseek-v4.1-flash-expires-on-0910` (the settings-file model), not `ENV_MODEL_LOSES`.
* **Probe F**: `--model deepseek-v4-pro` on argv beat the settings-file model. KAPSO's argv pin
  (`claude_code_agent.py`, `config.model` → `--model`) remains authoritative.
* **Probe G** (`home/fresh_empty_new/`, created empty): first call succeeded with the env-only
  endpoint; `grep -riE 'trust|onboard|login|setup|theme'` over all probe outputs → **no matches**.

Verified precedence on 2.1.278, unchanged from 2.1.260:

1. `--model` argv flag
2. `<CLAUDE_CONFIG_DIR>/settings.json` (`model` and `env` block) — **overrides the process environment**
3. process environment

`CLAUDE_CONFIG_DIR` isolation is intact: state lands under the pointed-at directory
(`.claude.json`, `backups/`, `projects/`, `session-env/`, `sessions/`, `shell-snapshots/`) and
**no `settings.json` is auto-created** there — only the two I wrote by hand exist.

---

## 4. Real runs on `deepseek-flash`

### 4.1 Agentic run (`scratch/run1/`, cwd = that directory)

Env: `CLAUDE_CONFIG_DIR=<here>/home/run1`, `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`,
`ANTHROPIC_AUTH_TOKEN=$DS_KEY`, all five model-slot vars = `deepseek-flash`,
`CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000`, `claude -p … --output-format stream-json --verbose
--dangerously-skip-permissions`, prompt instructing: write `hello.py`, run `python3 hello.py`, put
stdout in `result.txt`.

**Filesystem verification (independent of the model's claim):**

```
scratch/run1/hello.py   → print("CLAUDE_DEEPSEEK_OK")
scratch/run1/result.txt → CLAUDE_DEEPSEEK_OK
```

Tool calls in the stream (real `tool_use` blocks, absolute paths):

```
Write …/scratch/run1/hello.py
Bash  python3 hello.py
Write …/scratch/run1/result.txt
```

Result event: `subtype=success`, `is_error=false`, `num_turns=4`, `terminal_reason=completed`,
exit 0, `duration_ms=5342`, `ttft_ms=1657`, **`ttft_stream_ms=527`** (streaming path used).

**Served model:** request `model=deepseek-flash` → `modelUsage` key `deepseek-flash`,
`canonicalModel: "deepseek-flash"`, `provider: "firstParty"`, `contextWindow: 128000` (the
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` override was honoured), `maxOutputTokens: 32000`.

**Streaming / cache fields:** `cache_read_input_tokens = 53504` (non-zero; per-turn
17664 / 17792 / 18048), **`cache_creation_input_tokens = 0`** — both exactly as in 2.1.260. The
`ephemeral_1h/5m` sub-counters are also 0. Do not build cost logic on a non-zero creation count.

### 4.2 Session resume (`scratch/run2/`, `home/run2`)

```
call1  --session-id 74171a9e-…  result 'OK'      cache_read=0
call2  --resume   74171a9e-…    result 'MARLIN7' cache_read=17536
```

Both exit 0, `session_id` identical across both processes, and the second call recalled the
codeword from the first — conversation state and the prompt cache both survive a resume. KAPSO's
`--session-id` / `--resume` argv is unaffected by the upgrade.

### 4.3 Endpoint, directly (curl, ~300 tokens)

* `GET https://api.deepseek.com/models` → exactly `deepseek-flash`, `deepseek-v4-pro`.
* `POST /anthropic/v1/messages` with `stream:true` + a `tools` array → well-formed SSE:
  `message_start`, `ping`, 2× `content_block_start`, 13× `content_block_delta`, 2×
  `content_block_stop`, `message_delta`, `message_stop`; a real
  `{"type":"tool_use","name":"get_time"}` block and `"stop_reason":"tool_use"`.
* Stream `usage` again shows `cache_creation_input_tokens: 0`.
* The endpoint still returns a leading `thinking` block by default; the CLI asks for
  `thinking:{type:"adaptive",display:"omitted"}` and reports `thinking_tokens: 0`.

---

## 5. Delta vs 2.1.260 (explicit)

Apples-to-apples capture: same mock probe with **no** model override in both versions, so the only
variable is the CLI.

| Item | 2.1.260 | 2.1.278 | Load-bearing? |
|---|---|---|---|
| `user-agent` | `claude-cli/2.1.260 (external, sdk-cli)` | `claude-cli/2.1.278 (external, sdk-cli)` | no |
| Tool schemas | **22** | **21** — `TaskOutput` **removed**, none added | no |
| System prompt size | 10337 chars, 3 blocks (2 with `cache_control`) | 9240 chars, 3 blocks (2 with `cache_control`) | no |
| Default model when none set | `claude-opus-5` | `claude-opus-5` (unchanged) | no |
| `max_tokens` | 64000 with the default opus-5 model | **64000** likewise; **32000 for `deepseek-flash`** | no |
| `anthropic-beta` list | 9 (incl. `context-1m-2025-08-07`, `fallback-credit-2026-06-01`) | 10 for the default model — adds `mid-conversation-tool-changes-2026-07-01`; **with a non-`claude-*` id (`deepseek-flash`) the CLI drops `context-1m-2025-08-07` and `fallback-credit-2026-06-01`** → 8 | no |
| First user-message text blocks | 2 | 3 | no |
| Path / method / auth headers | `POST /v1/messages?beta=true`, x-api-key vs Bearer | identical | no |
| `request` body keys | `context_management,max_tokens,messages,metadata,model,output_config,stream,system,thinking,tools` | identical | no |
| `unrecognized_model` warning | present (`query_source: generate_session_title`) | **still present** (`query_source: "sdk"`); non-fatal | no |

No delta in: auth-var mapping, settings-vs-env precedence, `--model` precedence, `CLAUDE_CONFIG_DIR`
relocation and fresh-dir behaviour, `cache_read` / `cache_creation` semantics, the four tools KAPSO's
score-of-record path uses (`Write`, `Bash`, `Read`, `Edit`).

*Correction to the prior report, found while diffing:* `../claude-deepseek/REPORT.md` §5 states
"`max_tokens=64000` (the CLI's default)". That 64000 came from the default-model capture, not from a
DeepSeek request — with a DeepSeek id the CLI sends **32000**, on **both** versions (the prior
`logs/mock_bodies.json` first entry, `model=deepseek-v4-pro`, also shows `max_tokens=32000`). No
behaviour change, but the recipe's output ceiling is 32k per turn, not 64k.

---

## 6. Does the KAPSO recipe still hold verbatim?

**Yes — all three elements, unchanged, no amendment.**

1. **`CLAUDE_CONFIG_DIR` isolation is still mandatory and still works.** Probe D proves the
   user-global `~/.claude/settings.json` still silently outranks the process environment for both
   endpoint and model on 2.1.278 (mock received zero requests). KAPSO still never sets this variable
   — `grep -rn "CLAUDE_CONFIG_DIR" src/` over the KAPSO tree returns **no occurrences**, and
   `_get_effective_env` still does `os.environ.copy()` (`claude_code_agent.py:329-333`). So the
   child `claude` still reads the real `~/.claude/settings.json` unless the launcher exports the
   variable. Unchanged and still the sharpest hazard on this path.
2. **The explicit `type:` requirement is unchanged** (KAPSO source, *read from source*, commit
   `7d99b15`): `core/preflight.py:222` still ends `return "claude_code" if model_name.startswith("claude") else "codex"`.
   A block naming `model: deepseek-flash` with no `type:`/`cli:` still resolves to the **retired
   codex CLI**. This is a KAPSO-side fact, untouched by the CLI upgrade.
3. **Pinning `deepseek-flash` still works**: env pin honoured (probe G) and argv `--model` still
   outranks the settings file (probe F); served `canonicalModel: deepseek-flash`; `--model` arg
   remains authoritative over both.

Recipe text as it should be recorded:

> Launch KAPSO with `CLAUDE_CONFIG_DIR=<project-local dir>` exported; point the lane at
> `https://api.deepseek.com/anthropic` with `ANTHROPIC_AUTH_TOKEN`; pin all model slots to
> `deepseek-flash`; set `type: claude_code` (or `oss_claude_code`) explicitly on every block whose
> model is a DeepSeek id.

**Two things to carry forward, neither invalidating:** `TaskOutput` no longer exists as a CLI tool
(only matters if a prompt names it explicitly); and per-turn `max_tokens` for DeepSeek ids is 32000.

---

## 7. Cost, and what was spent

Peak window on 2026-09-21 (Monday, 06:56 UTC = within DeepSeek's 06:00–10:00 UTC peak). Estimated at
the same rate basis the 2.1.260 report used (flash peak ≈ $0.30/M cache-miss input, ≈ $0.006/M cache
hit, ≈ $1.20/M output).

| Activity | model | input | cache_read | output | est. real cost |
|---|---|---|---|---|---|
| probe D (global settings vs env; real endpoint) | alias `…expires-on-0910` | 19 881 | 0 | 3 | $0.0060 |
| run1, attempt 1 (my cwd mistake) | flash | 18 168 | 53 760 | 365 | $0.0062 |
| run1, attempt 2 (my cwd mistake; log overwritten) | flash | ~18 200 | ~53 500 | ~300 | **≈$0.006 (estimate — unmeasured)** |
| run1, final (in `scratch/run1`) | flash | 18 274 | 53 504 | 313 | $0.0062 |
| run2 call1 (`--session-id`) | flash | 17 652 | 0 | 2 | $0.0053 |
| run2 call2 (`--resume`) | flash | 164 | 17 536 | 4 | $0.0002 |
| curl SSE + `/models` probe | flash | 299 | 0 | 41 | $0.0001 |
| probes A/B/C/E/F/G/delta (mock) | — | — | — | — | $0.00 |
| **total** | | | | | **≈ $0.030** |

Two agentic runs were wasted by launching `claude` with the wrong working directory (produced files
in the report directory, since deleted); one of them overwrote a stream log. That is the source of
the estimate row above. Everything else was a real, verified measurement. Total ≈ 3 US cents, well
inside budget.

**The CLI's own `total_cost_usd` remains garbage** — it reported $0.125947 for run1 (real ≈ $0.0062)
and still emits `"costBasis":"unknown"`. Do not use it for the study's cost trace; price from the
token counts in `usage`.

---

## 8. Machine state and hygiene

* **Mock started and stopped.** Port 8788, bound to loopback; killed by pid taken from `ss -ltnp`.
  Verified stopped: `curl` → `000`, `ss -ltn` shows no listener. Ports 8788/8799 free.
  *(An oddity worth recording: the `.mock.pid` file I wrote disappeared mid-session with no
  explanation — I stopped the mock by looking up the pid in `ss` instead. No other effect.)*
* **`~/.claude/settings.json` untouched and unchanged on its own:** 555 bytes, mtime
  2026-09-09 10:20 — byte-identical owner/mtime to the prior audit's reading. Its contents are the
  same shape as before: `env{ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic,
  ANTHROPIC_AUTH_TOKEN=<the same key as ~/gptapi.md, sha256[:8]=b194aef5>, 4 model slots +
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=1000000 all set to the stale alias
  deepseek-v4.1-flash-expires-on-0910}, model=deepseek-v4.1-flash-expires-on-0910, theme=dark`.
  **Reported, not modified.** The alias still routes (HTTP 200) — probe D used it successfully.
* `~/.claude.json` unchanged (45693 bytes, mtime 2026-09-10).
* **Key hygiene verified:** the real key's value appears in **no** file under this directory
  (`grep -rlF "$DS_KEY" .` → none), nor the settings-file token. Only the fake placeholder
  `sk-fake-SETTINGS-token-CCCC` and the `sk-probe-…` values were written. Key length 35, passed as
  an env var only, never echoed.
* Probe D necessarily used the real config home, so Claude Code wrote a transcript under
  `~/.claude/projects/-home-ebt-rsi-dev-a0-notes-exit-closed-claude-deepseek-2-1-278/` — safe to
  delete. Every other run used `CLAUDE_CONFIG_DIR`.
* No packages installed. No long-running service left behind.

---

## 9. Evidence index

| Artefact | Contents |
|---|---|
| `evidence/mock_anthropic.py` | capture-only mock (copy of the 2.1.260 one); sha256-fingerprints auth headers |
| `logs/mock_headers.log` | header captures: probes A/B/C (#2–#7), E (#8–#9), F (#10–#11), G (#12–#13) |
| `logs/mock_headers_delta.log`, `logs/mock_bodies_delta.json` | the apples-to-apples no-model-override capture used for §5 |
| `logs/mock_bodies.json` | bodies for the 2.1.278 probes |
| `logs/probe_apikey_only.out`, `…authtoken_only.out`, `…both_set.out` | auth-var probes |
| `logs/probe_precedence.out` | probe E — settings beat unreachable env base_url **and** env model |
| `logs/probe_global_precedence.out` | probe D — real global settings won; model `…expires-on-0910`; mock got 0 requests |
| `logs/probe_flag.out` | probe F — `--model deepseek-v4-pro` beat the settings file |
| `logs/probe_fresh_dir.out` | probe G — fresh config dir, no onboarding/trust prompt |
| `logs/run1.stream.jsonl`, `logs/run1.stderr.log`, `scratch/run1/{hello.py,result.txt}` | §4.1 agentic run, filesystem-verified |
| `logs/run1_cwdroot.stream.jsonl` | the first run (wrong cwd), kept for the token-usage record |
| `logs/run2_call1.json`, `logs/run2_call2.json` | §4.2 resume with codeword recall and cache reuse |
| `logs/sse_tooluse.txt` | raw SSE from DeepSeek with a real `tool_use` and `stop_reason:"tool_use"` |
| `logs/claude-help.txt` | `claude --help` for 2.1.278 (302 lines) |
| `home/<probe>/` | isolated `CLAUDE_CONFIG_DIR`s, showing what the CLI writes where |
| `scratch/run1`, `scratch/run2` | run working directories |
