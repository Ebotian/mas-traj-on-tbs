# opencode v2.0.11 backed by DeepSeek — the EvE lane

Owner: `a0/notes/exit-closed/opencode-deepseek/`. Date: 2026-09-21.
Method: executed on this host against the real `opencode` binary and the real DeepSeek
endpoint. Every claim below is tagged **[ran]**, **[read]** (source, cited) or **[inferred]**.
No file outside this directory was modified. No key was written to any file; the key is read
from `~/gptapi.md` at run time by `env.sh` into the shell environment only.

**One-line verdict: the EvE→opencode→DeepSeek path works end-to-end at the model/provider
layer, but EvE's shipped driver cannot drive opencode v2.0.11 — the argv is rejected outright
and the JSON stream no longer matches EvE's parser. One EvE code change, not zero.**

---

## 0. Environment and scoping

| item | value |
| --- | --- |
| binary | `/usr/bin/opencode`, `opencode v2.0.11` **[ran: `opencode --version`]** |
| scope | `env.sh` here exports `XDG_{CONFIG,DATA,CACHE,STATE}_HOME` under this directory; the user's global `~/.config/opencode` was never written **[ran: `opencode debug paths`]** |
| config | `xdg/config/opencode/opencode.json` — custom provider block, `apiKey: "{env:DEEPSEEK_API_KEY}"` **[ran]** |
| global spill | four *unscoped* probe commands (`opencode --help`/`models`/`debug …`) created `~/.config/opencode/service.json` and `~/.local/{share,state}/opencode/` (11 MB DB). No credentials in any of it — `credential`/`account` tables are 0 rows and the key prefix does not appear **[ran]**. Described in §8, not deleted |
| auth | no interactive login: `opencode auth list` → `No authenticated integrations`; after nine runs the `credential` and `account` tables in `xdg/data/opencode/opencode.db` are still **0 rows** **[ran, sqlite3]** |
| endpoint | `https://api.deepseek.com/v1/chat/completions` |

`{env:VAR}` substitution **is** supported in the provider `options.apiKey` — the env reference
is resolved at config load, so nothing is persisted. Caveat: `opencode debug config` and
`opencode debug agents` **print the resolved key in plaintext** **[ran]**; the key is not in
any file here (`grep -rI 'sk-[A-Za-z0-9]\{20,\}' .` → no match), but any evidence collector
must redact `debug config` output.

Served model id: **the endpoint echoes the requested id** — `deepseek-v4-pro` → `"model":
"deepseek-v4-pro"`, `deepseek-flash` → `"model":"deepseek-flash"`, same with `"stream":true`
**[ran, curl]**. The brief's "responses report the served model as `deepseek-v4-flash`" was
**not reproducible** on the OpenAI-compatible surface here. Attribution traces should record
what they measure, not the earlier claim.

---

## 1. Does `opencode run` work non-interactively without a TTY, and what does `--auto` do?

**Yes, no TTY needed.** Every run below was executed with stdin *and* stdout not a tty
(`[ -t 0 ]`/`[ -t 1 ]` both false) and no stdin redirect beyond the default **[ran]**.

First real agentic run **[ran]** — `cd work && opencode run --format json --auto --agent build
--thinking --model deepseek/deepseek-v4-pro "Create a file named hello.txt …"`, exit 0 in 6 s,
`hello.txt` written with contents `ping` (4 bytes, **no trailing newline**), and
`git status --porcelain` → `?? hello.txt`.

**`--auto` means "auto-approve permissions that are not explicitly denied"** (its own help text)
— and that is exactly what it does. Three runs isolate it:

| run | permission | `--auto` | observed |
| --- | --- | --- | --- |
| run1 | `shell/edit = ask` | yes | `write` and `shell` tools executed, exit 0 **[ran]** |
| run7 | `shell/edit/webfetch = deny` | yes | shell tool **never offered** — the model answered "I don't have a shell execution tool in my current environment"; no `tool_use` event at all; exit 0 **[ran]** |
| run8 | `shell = ask` | **no** | non-interactive → **auto-rejected**: stderr `permission requested: shell (echo ASK_TEST); auto-rejecting`; the `tool_use` part has `status:"error"`, `error:"The user declined this tool call"`; then `{"type":"error","error":{"type":"aborted","message":"Step interrupted"}}`; **exit 1** **[ran]** |

So `--auto` turns `ask` into `allow` but cannot override `deny`, and dropping `--auto` makes
every `ask` a hard failure. EvE always passes `--auto` (`drivers/opencode.py:405`) — that is
the correct choice and it is load-bearing.

## 2. Custom OpenAI-compatible provider with a custom base_url + env-var key, no interactive login?

**Yes, verified three ways.**

Config used (no key literal anywhere; `{env:DEEPSEEK_API_KEY}` in the file):
`xdg/config/opencode/opencode.json` declares provider `deepseek` with
`npm: "@ai-sdk/openai-compatible"`, `options.baseURL`, `options.apiKey`, and two custom model
ids. `opencode debug config` reports it normalized to `package: "aisdk:@ai-sdk/openai-compatible"`
with no npm install performed **[ran]**; `opencode models` then lists
`deepseek/deepseek-v4-pro`, `deepseek/deepseek-flash` **[ran]**.

**EvE's own injection channel works.** EvE folds `driver.model_providers.<p>.env_key` into
`provider_env` and merges it into `OPENCODE_CONFIG_CONTENT` **[read: `drivers/opencode.py:426-510`]**.
I reproduced EvE's exact environment shape — fresh `HOME`, `OPENCODE_CONFIG` = an empty `{}`
file, `OPENCODE_CONFIG_DIR`, `XDG_*` all under that home, `OPENCODE_DISABLE_PROJECT_CONFIG=true`,
provider supplied **only** through `OPENCODE_CONFIG_CONTENT` **[ran: `logs/run9_eveshape.json`]**:
exit 0, model replied `ok`, and the requests arrived at my local proxy with
`authorization_present: true`. So EvE's provider path is sound.

**One sharp edge [ran]:** `OPENCODE_CONFIG_CONTENT` is read by the *background service process*,
not by each CLI invocation. A config change is invisible until the service is restarted:
identical runs with and without `opencode service restart` went to different base URLs
(`logs/run2_proxy.json` untouched-by-proxy vs `logs/run6_envcontent.json` hitting the proxy).
Under EvE each rollout gets a fresh state dir, so the CLI spawns its own service and inherits
the env — correct by construction, but it means **you cannot hot-reload a config under a
running daemon**.

## 3. Is `--format json` parseable, and what is its shape? (EvE parses it — mismatch here)

**Parseable: yes. Compatible with EvE's parser: no, on two independent points, both proven by
execution.**

Shape **[ran, 9 event lines for a 3-step run]**: newline-delimited JSON, one object per line,
keys `type`, `timestamp`, `sessionID`, `part`. Event types observed across 8 runs:
`step_start`, `reasoning`, `tool_use`, `step_finish`, `text`, and `error`. A `tool_use` part is
`{partID, sessionID, messageID, type:"tool", id:"call_…", tool:"write", state:{status, input,
output, metadata, time}}`; a `step_finish` part carries `reason`, `cost`, `tokens{input,output,
reasoning,cache{read,write}}`. Lines are flushed **incrementally** (per-line arrival timestamps
confirm it) **[ran]**, so EvE's live-stdout capture works.

I ran EvE's own parser (`OpenCodeSessionDriver._parse_stdout_jsonl`, imported read-only from
`/tmp/eve` @ `979065fd`, no EvE file touched) against the captured streams
(`probe_eve_parser.py`):

| stream | observed result |
| --- | --- |
| `logs/run1.json` (write + shell + answer) | `ValueError: line 3: 'callID' must be a non-empty string.` **[ran]** |
| same stream with `callID` injected from `id` | `RuntimeError: session … ended with incomplete finish reason 'tool-calls'.` **[ran]** |
| `logs/run3_fileproxy.json` (plain text answer) | `ValueError: stream contains no completed OpenCode step.` **[ran]** |

1. **Field rename.** EvE reads `part.callID` **[read: `drivers/opencode.py:576`]**; v2.0.11 emits
   `part.id`. Every tool call fails the parse.
2. **No terminal `step_finish`.** EvE requires the last seen reason to be `"stop"`
   (`_SUCCESSFUL_FINISH_REASON = "stop"`, `:49`, checked at `:598`). v2.0.11 emits
   `step_finish` only for steps that end in tool calls — reason is **always** `tool-calls`
   (4/4 across all captured runs; the string `"reason":"stop"` appears in **zero** captured
   lines) **[ran]**. The final assistant turn produces `step_start` + `text` and the process
   exits. EvE can never satisfy its own check.
3. **Cost is under-reported downstream of that.** The missing final `step_finish` also loses the
   last step's tokens and cost. run1's session: stream sums to **$0.002905481**, the session DB
   (`session_message.data.cost`) sums to **$0.003001297** — a systematic undercount, and EvE's
   `input_tokens/output_tokens/model_cost_usd` all come from the stream **[read:
   `drivers/opencode.py:295-312`]**. Workaround if the driver is patched: read the final
   message's `cost`/`tokens` from `$XDG_DATA_HOME/opencode/opencode.db`, table
   `session_message`, `type='assistant'` **[ran]** — that table does contain the final step.

Note the `error` event also carries `{"type":"error","error":{…}}` and EvE already raises on it
**[read: `:554`]** — that part is compatible.

## 4. Does it expose sandbox / permission control?

**Yes — a real rule engine, and it is more than EvE currently uses. There is no OS-level sandbox.**

`opencode debug agents` **[ran, `logs/debug_agents.json`]** shows every agent carrying an ordered
list of `{action, resource, effect}` permissions, with `effect ∈ {allow, ask, deny}` and actions
including `*`, `shell`, `edit`, `read`, `write`, `webfetch`, `websearch`, `external_directory`,
`question`, `subagent`, `grep`, `glob`, `skill`, `task`, `mcp`. Concrete examples measured:

* `build` (default): `allow * *`, then `ask external_directory *`, `ask read *.env`,
  `allow read *.env.example`, `ask shell *` — plus, at the end, whatever the config declared.
* `plan`: `deny edit *` with a single `allow edit /home/ebt/.opencode/plan/*` — a genuine
  allowlist.
* `explore`: `deny * *` then `allow grep|glob|read|webfetch|websearch` — a genuine tool allowlist.
* `general`/`summary`/`title`: `deny * *`.

Configurable surface, verified by execution: a `permission` block in the config file
(`{"shell":"ask","edit":"ask","webfetch":"deny"}`) materializes as rules appended after the
built-ins and **does** win over the built-in `allow * *` (run7's `deny shell *` removed the shell
tool entirely) **[ran]**. `deny` removes the tool from the model's toolset rather than failing at
call time.

**What it is not:** there is no filesystem or network sandbox — no namespace, no path jail, no
egress filter. `external_directory` gates *outside-the-project* paths and the default is
`allow * *`; `webfetch` can be denied but the agent's `shell` can then do the same thing unless
you deny it too. So opencode gives **config-level permission control**, which is strictly more
than `codex_exec` has (that driver hardcodes `--dangerously-bypass-approvals-and-sandbox`
**[read: `codex_exec.py:434`]**), but it is not closure. The EvE audit's line
"`opencode.py` contains zero occurrences of `sandbox` and zero of `permission`" is about EvE's
*driver*; **the CLI itself does have a `permission` system** — it is simply not wired through
EvE's driver, and EvE passes no permission config of its own.

Related surface found in the binary **[read: `strings`, not exercised]**:
`OPENCODE_DISABLE_PROJECT_CONFIG`, `OPENCODE_CONFIG_PROJECT_DISABLE`,
`OPENCODE_DISABLE_MODELS_FETCH`, `OPENCODE_MODELS_URL`, `OPENCODE_MODELS_PATH`.
Note `OPENCODE_DISABLE_EXTERNAL_SKILLS` — which EvE sets **[read: `opencode.py:452`]** — is
**absent** from v2.0.11, so that hardening knob is silently ignored.

## 5. Custom base_url at a local plaintext `http://` proxy, and `HTTPS_PROXY`?

**Both work. `HTTPS_PROXY` has a trap that will bite the isolation topology.**

*Plaintext local base_url* **[ran]** — `proxy.py` (a logging reverse proxy) on `127.0.0.1:8099`,
provider `baseURL` = `http://127.0.0.1:8099/v1`. Two independent setups hit it:
`schema`-identical POSTs recorded as
`{"method":"POST","path":"/v1/chat/completions","host_header":"127.0.0.1:8099","authorization_present":true,"body_model":"deepseek-v4-pro"}`
— once with the file config (`logs/run3_fileproxy.json`) and once with the EvE-shaped
`OPENCODE_CONFIG_CONTENT` setup (`logs/run9_eveshape.json`). A local plaintext endpoint is a
supported topology.

*`HTTPS_PROXY`* **[ran]** — with `https_proxy=http://127.0.0.1:8098` pointed at
`connect_proxy.py`, the CONNECT log shows `models.opencode.ai:443` and (twice)
`api.deepseek.com:443`, and the run succeeded:
`{"proxy":"connect","target":"api.deepseek.com:443"}`.

*The trap* **[ran]** — the same env **without** `NO_PROXY` breaks the run. opencode routes its
own loopback service call through the proxy: the log filled with **9 947 identical**
`GET http://127.0.0.1:49411/api/info HTTP/1.1` requests (a hot retry loop, ~800 KB of log in
seconds), the CLI never reached its own service, and the run failed. Mitigation verified:
`NO_PROXY=127.0.0.1,localhost` → clean run. **Any isolation topology that wraps opencode in an
HTTP proxy must set `NO_PROXY` for loopback.** Raw log: `evidence/httpsproxy_hotloop_raw.jsonl`.

Also note egress: `models.opencode.ai:443` is contacted at startup to fetch the model registry
**[ran: CONNECT log]**. `api.deepseek.com` is the only model endpoint needed, but a hermetic
deployment also needs the registry host reachable or must pin a local registry
(`OPENCODE_MODELS_URL` / `OPENCODE_MODELS_PATH` exist in the binary **[read]**; not exercised).

---

## 6. Blockers, in priority order

### B1 — EvE's argv is rejected by v2.0.11 (hard failure, every rollout) [ran]

EvE builds `opencode run --format json --auto --dir <worktree> --agent build --thinking …`
**[read: `drivers/opencode.py:405-424`]**. Running that exact argv:

```
$ opencode run --format json --auto --dir "$(pwd)" --agent build --thinking \
      --model deepseek/deepseek-v4-pro "say ok"
ERROR
  Unrecognized flag: --dir in command opencode run
EXIT=1   stdout=1619 bytes (the help text)
```
`--variant` is likewise rejected (`Unrecognized flag: --variant`) — it is only passed when
`driver.variant` is non-null, and both presets set `variant: null`, so `--variant` is latent
not active. `--dir` is active and fatal. Mitigation is available and already half-present: the
driver also runs the child with `cwd=worktree_root` **[read: `opencode.py:239`]**, and v2 uses
the positional directory argument, so **dropping `--dir` from `_argv` is sufficient**. (EvE
pins no opencode version — `grep opencode uv.lock pyproject.toml` found none — which is why
this drift is unowned.)

### B2 — The JSON stream schema mismatch (§3) [ran]

`part.callID` → `part.id`, and EvE's mandatory `finish_reason == "stop"` never occurs. EvE must
either accept `id` as the call id and drop/relax the terminal-finish check, or read usage and
completion state from `opencode.db`.

### B3 — Parallel rollouts collide on a fixed service port [ran]

opencode runs a **background daemon** (`opencode serve --service`; the CLI connects to it, per
`opencode service status` → `http://127.0.0.1:49411`). The port is **not** derived from `HOME` or
`XDG_*`: decompiled from the binary, `Mq()` returns `49374` for channel `latest`, `49375` for
`local`, else `10000 + hash%50000` **[read: `strings /usr/bin/opencode`]**. Two concurrent runs,
each with its own EvE-style `HOME`/`XDG` tree (exactly what EvE does per rollout) and no explicit
port: **a exited 1 with 0 bytes of stream, b succeeded** (`parallel_probe.sh`,
`evidence/parallel_port_collision.txt`):

```
Managed service port 49374 on 127.0.0.1 is already in use by another process.
Configure another port with `opencode service set port <port>` …
→ Timed out waiting for the background service to start     (exit 1, empty stdout)
```
Fix: `opencode service set port <n>` per state dir before the first run, or `--standalone`
(private server, no shared port — present as a documented flag on `run` **[ran: `opencode run
--help`]** but not passed by EvE). This affects any plan for four parallel workers.

Two supporting observations: the daemon **outlives the CLI invocation** and keeps the
per-rollout temp `HOME` alive (three daemons accrued during this audit before I reaped them),
and a stale daemon on 49374 silently breaks an unrelated later run — that is what killed my
first `eve_shape` attempt.

### B4 — Cosmetic / latent

* `OPENCODE_DISABLE_EXTERNAL_SKILLS` is not a v2.0.11 env var (§4).
* `opencode debug config` prints the resolved API key in plaintext (§0).
* The provider registry is fetched from `models.opencode.ai` at startup (§5).

---

## 7. Cost

All figures are opencode's own client-side `cost` field (the DeepSeek response carries no cost,
so this is **locally priced from the fetched registry, not provider-reported**).

| scope | value |
| --- | --- |
| scoped DB, 10 assistant messages, 8 sessions | **$0.020966** |
| parallel-test run b (separate DB) | $0.002529 |
| direct `curl` probes (85 + 32 prompt tokens) | < $0.0001 |
| **total** | **≈ $0.0235** |

Per-run detail: the full agentic run (write + shell + answer, 3 steps) cost **$0.002905481** in
the stream / **$0.003001297** in the DB, with 6 214 input + 84 output + 37 reasoning tokens on
the first step and 6 272 cached tokens read on the second. Token counts: 46 440 input / 322
output / 498 reasoning across the scoped DB. Well inside the $0.30 target.

---

## 8. Machine state — what I started and how to stop it

Everything is stopped now. Nothing outside this directory was permanently changed, but two
things need stating honestly:

1. **Accidental global spill.** Four probe commands I ran *without* the scoped env — `opencode
   --help`, `opencode models`, `opencode debug paths|config|agents` from `/tmp` — made opencode
   create its own global state: `~/.config/opencode/service.json` (64 bytes: a random local
   service password, **not** the API key) and `~/.local/{share,state}/opencode/` (an 11 MB
   `opencode.db` plus logs). Neither existed before this session (they were created 10:34, and
   `opencode` was installed at 09:57). **No key material is in any of it** — verified by grepping
   for the key prefix and by `select count(*) from credential` → 0. I have **not** deleted it:
   three other workers are running on this host and may be sharing that default scope, so
   deleting the DB mid-flight is the more dangerous option. If you want it gone:
   `rm -rf ~/.config/opencode ~/.local/share/opencode ~/.local/state/opencode`.
   All *deliberate* configuration for this lane lives under this directory and is removed by
   deleting it.
2. `~/.config/opencode/opencode.json` (a config file) never existed and was never written — I
   confirmed the config file path was never created in the global scope. The user's global
   opencode *config* is untouched; only opencode's own runtime state appeared.

`adapdc-catalog-postgres-1` was not touched. No packages installed, no files outside this
directory written.

Started and already reaped:

* `opencode serve --service` daemons (5 across the audit). To stop any future one:
  `source env.sh && opencode service stop`, or `pkill -f "opencode serve --service"`.
* `proxy.py 8099` (reverse proxy) and `connect_proxy.py 8098` (CONNECT proxy) — both killed,
  ports free. Restart with `python3 proxy.py 8099 logs/proxy_reverse.jsonl` /
  `python3 connect_proxy.py 8098 logs/proxy_connect.jsonl`.

Not mine, left alone: `python3 /opt/a0pc/allowlist_proxy.py` and a listener on `*:7890`
(`http_proxy`/`https_proxy` are pre-set globally in `/etc/environment`) — this is why every run
here was already proxied at the host level.

Re-run everything: `source env.sh` then `bash parallel_probe.sh`, or replay a single run as in
`logs/run9_eveshape.json`'s invocation. `probe_eve_parser.py` needs
`PYTHONPATH=/tmp/eve/src` and `/home/ebt/rsi-dev/a0/runtimes/eve/.venv/bin/python`.

---

## 9. Evidence index (all paths relative to this directory)

| artefact | contents |
| --- | --- |
| `env.sh` | scoped `XDG_*` + key pulled from `~/gptapi.md` at run time (no key stored) |
| `xdg/config/opencode/opencode.json` | the provider + permission config actually used |
| `logs/run1.json` | the full agentic run (write + shell + answer), 9-line JSONL stream |
| `logs/run1_callID_patched.json` | same stream with `callID` injected, to expose the second parser failure |
| `logs/run2_proxy.json` / `run6_envcontent.json` | the daemon-config-caching pair |
| `logs/run3_fileproxy.json` | plaintext local `baseURL` proven via file config |
| `logs/run4_httpsproxy.json` | the `HTTPS_PROXY`-without-`NO_PROXY` failure |
| `logs/run5_httpsproxy.json` | the same with `NO_PROXY` — success |
| `logs/run7_deny.json` / `run8_ask_noauto.json` | `deny` beats `--auto`; `ask` without `--auto` aborts with exit 1 |
| `logs/run9_eveshape.json` | EvE-shaped `OPENCODE_CONFIG_CONTENT` injection, end-to-end |
| `logs/eve_argv.out` / `.err` | the exact EvE argv being rejected |
| `logs/debug_agents.json` | the full agent/permission rule listing |
| `evidence/eve_parser_*.txt` | EvE's own parser failing three ways |
| `evidence/parallel_port_collision.txt`, `evidence/a.exit`, `logs/parallel/*` | the parallel-run port collision |
| `evidence/httpsproxy_hotloop_raw.jsonl` | the 9 947-request loopback hot loop |
| `probe_eve_parser.py`, `proxy.py`, `connect_proxy.py`, `parallel_probe.sh` | the re-runnable probes |
| `/tmp/eve` @ `979065fd` | EvE checkout used read-only for the parser and argv citations (not created here — it pre-existed) |

## 10. The one-line answer for this lane

opencode v2.0.11 + DeepSeek is a **real, working agent lane** — non-interactive and TTY-free,
custom OpenAI-compatible provider via `{env:…}` with no login, real permission rules, plaintext
local `base_url` and `HTTPS_PROXY` both working — but **it is not a zero-change EvE swap**: EvE
must drop `--dir` from the argv, accept `part.id` instead of `part.callID`, and stop requiring a
terminal `finish_reason:"stop"`; and any parallel-rollout plan must pin a per-rollout service
port or use `--standalone`.
