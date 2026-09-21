# kilo + DeepSeek — the Loreley path, verified by running it

Owner: `a0/notes/exit-closed/kilo-deepseek/`. Date: 2026-09-21 (CST).
Host: `kilo` 7.7.5 (`/usr/bin/kilo` → `/usr/lib/kilo/kilo`, 162 MB Bun-compiled standalone ELF).
Method: **executed** kilo directly (never through Loreley), plus targeted binary inspection and
Loreley's own pricing code. Every claim below is tagged **[ran]**, **[read]** or **[inferred]**.
Loreley's source was **not modified** — checkout clean at `4c37592` (`git status --porcelain` empty).

---

## 1. Verdicts

| # | Question | Verdict | Basis |
|---|---|---|---|
| 1 | Custom OpenAI-compatible provider at DeepSeek, **no interactive login**, **no key literal in any file** | **Yes** | **[ran]** `kilo debug config` shows `{env:DEEPSEEK_API_KEY}` / `{env:DEEPSEEK_BASE_URL}` resolved from the process env; kilo's `credential` table is **0 rows**; isolated `XDG_CONFIG_HOME` holds no auth file |
| 2 | Small agentic task completes non-interactively (file + shell command) | **Yes** | **[ran]** two real runs, exit 0; `write`, `bash`, `read` tool calls executed; files on disk correct |
| 3 | Does `npm: @ai-sdk/openai-compatible` need network at first use? | **No — bundled** | **[ran]** full agent loop completed in a netns with *zero* egress (DNS fails, no route) + **[read]** static specifier→bundled-module map in the binary |
| 4 | `base_url` override survives resolution? | **Yes** | **[ran]** resolved config shows `baseURL: https://api.deepseek.com/v1` |
| L1 | Seed-portfolio `gpt-5.6-sol` pin — minimal change | Patch proposed (2 sites, not 1) | **[read]** + **[ran]** patch drafted, not applied → `proposed-patch.md` |
| L2 | Usage/cost for an unlisted DeepSeek model | **`unpriced` — and `LLM_USAGE_PRICING_JSON` cannot fix it** | **[ran]** Loreley's own `price_usage_event` on a real-shaped kilo event |

**One-line verdict for this lane:** *kilo 7.7.5 + DeepSeek OpenAI-compatible is a working,
login-free, npm-egress-free agent backend whose tool loop and token accounting both work — but
its spend will record as `unpriced`, and the seed-portfolio lane needs a 15-line two-site patch.*

---

## 2. Exact commands and observed results

### 2.1 Config resolved, key never in a file — `[ran]`

Config content built exactly as `kilocode_cli.py:1119-1160` builds it (`config` mode), with the
`npm: "@ai-sdk/openai-compatible"` provider and **env-var references**:

```json
{"provider":{"loreley-openai-compatible":{"name":"Loreley OpenAI-compatible gateway",
 "npm":"@ai-sdk/openai-compatible",
 "options":{"apiKey":"{env:DEEPSEEK_API_KEY}","baseURL":"{env:DEEPSEEK_BASE_URL}"},
 "models":{"deepseek-v4-pro":{"name":"deepseek-v4-pro"}}}},
 "model":"loreley-openai-compatible/deepseek-v4-pro"}
```

```console
$ . evidence/env.sh && kilo debug config        # key only ever in this shell's env
  ... "provider": { "loreley-openai-compatible": {
        "npm": "@ai-sdk/openai-compatible",
        "options": { "apiKey": "<REDACTED-by-env-ref>",
                     "baseURL": "https://api.deepseek.com/v1" }}}
```

**[ran]** Both `{env:…}` references resolved correctly. Redacted copy: `evidence/01_debug_config_redacted.json`.
Full list of env knobs and the exact probe config: `evidence/env.sh`.

> **Hazard (new):** `kilo debug config` **prints the resolved secret in cleartext** to stdout.
> Loreley's backend redacts provider values from stdout and from its SQLite
> (`kilocode_cli.py:338`, `:637-638`, `:662`), so it is covered *if* that redaction list includes the key — but
> anyone running `kilo debug config` by hand leaks the key. Worth an explicit redaction test.

**[ran]** `kilo models` lists `loreley-openai-compatible/deepseek-v4-pro` as line 317 → the
custom provider **and its explicitly registered model id** are accepted by kilo's catalog
validation, which is what `_kilo_provider_model_id` (`kilocode_cli.py:1220-1229`) exists to satisfy.

### 2.2 Real agentic run — `[ran]`

```console
$ kilo run --auto --pure --dir /tmp/kiloDS-wt2 --format json --title kilo-ds-direct \
    --agent loreley-headless -m loreley-openai-compatible/deepseek-v4-pro \
    "Create result.txt containing direct-ok; run 'date +%Y' and put its output in year.txt"
EXIT=0
```

Observed tool loop (3 steps, `evidence/02_real_run2_events.jsonl`):

| step | tool | detail |
|---|---|---|
| 1 | `write` | `{"filePath":"…/result.txt","content":"direct-ok"}` — `finish_reason: tool-calls` |
| 1 | `bash` | `{"command":"date +%Y > …/year.txt"}` |
| 2 | `read` | read back `year.txt` |
| 3 | *(text)* | `"Done."` — `finish_reason: stop` |

On disk: `result.txt` = `direct-ok`, `year.txt` = `2026`. **Both file creation and shell
execution verified.** Model actually served: **`deepseek-v4-pro`** (echoed by the provider in
the response `model` field and persisted by kilo as
`{"id":"deepseek-v4-pro","providerID":"loreley-openai-compatible"}`).

### 2.3 Token usage — `[ran]`

kilo reports usage for a custom provider **per step** and aggregates it in its own SQLite
(which is exactly where Loreley reads, `kilocode_cli.py:774-900`):

| Run | step | input | output | reasoning | cache read |
|---|---|---|---|---|---|
| smoke | 1 / 2 | 11016 / 108 | 75 / 3 | 9 / 0 | 0 / 11008 |
| direct | 1 / 2 / 3 | 8226 / 98 / 77 | 136 / 53 / 3 | 30 / 0 / 0 | 2816 / 11136 / 11264 |

`kilo stats` (`evidence/06_kilo_stats.out`):

```console
│Total Cost                                        $0.00 │
│Input                                             19.5K │
│Output                                              270 │
│Cache Read                                        36.2K │
│ write              ████████████████████   2 (50.0%)    │
│ bash               ██████████             1 (25.0%)    │
│ read               ██████████             1 (25.0%)    │
```

### 2.4 Cost — `[ran]`, and it is the problem

The session row kilo persists (the field Loreley reads) is
`cost: 0.0`, `tokens_input: 8401`, `tokens_output: 192`, `tokens_cache_read: 25216`.

**`[ran]`** The provider itself returns **no dollar cost** — a direct comparison call returns a
`usage` block with `prompt_tokens` / `completion_tokens` / `prompt_cache_hit_tokens` and
**no cost field**. So kilo has nothing to pass through, and because
`loreley-openai-compatible/deepseek-v4-pro` is absent from kilo's price catalog it writes `0`.

**Spend bound:** ~19.5 K input + 270 output + 36.2 K cache-read across 3 paid calls. Even at an
illustrative $0.28 / $0.42 per-1M-D-token pair this is ≈ **$0.006** — far under the $0.30 budget.
No dollar figure is *verifiable* for this model id: neither the provider nor kilo reports one, and
I did not accept any published price as authoritative **[inferred]**.

---

## 3. Question 3 in detail — the npm question, answered twice

The audit flagged this as unverified and closure-relevant. **Both lines of evidence say bundled.**

**`[ran]` Runtime proof (strongest).** `evidence/offline_probe.sh` runs the *entire* agent loop
inside a fresh user+mount+net namespace: loopback only, no route, egress unreachable, and
`registry.npmjs.org` unresolvable.

```console
== netns interfaces ==            lo  UNKNOWN  127.0.0.1/8
== netns routes (expect empty) == (end route table)
egress BLOCKED: network unreachable
DNS for registry.npmjs.org FAILS
KILO_EXIT=0
```

The local fake endpoint received two real requests — `POST /v1/chat/completions`, `model:
deepseek-v4-pro`, `stream: true` — kilo ran the `write` tool and produced the file with the
correct content, and wrote the session row (`cost 0.0`, `tokens_input 1050`). **With no network
whatsoever, the provider resolved, the request was built, streamed, parsed, and the tool loop
executed.** A runtime npm fetch is therefore impossible on this path.

**`[read]` Structural proof.** The 162 MB binary is a Bun bundle whose provider registry is a
**static specifier → bundled-module map**, no install step:

```
"@ai-sdk/openai-compatible":()=>Promise.resolve().then(() => (a3H()
"@ai-sdk/openai-compatible":()=>Promise.resolve().then(() => (ifA()
```

21 AI-SDK providers are bundled this way (`evidence/04_bundled_provider_map.txt`), and **both**
specifiers Loreley can emit are in it: `@ai-sdk/openai` (responses mode) and
`@ai-sdk/openai-compatible` (config mode) — see `_kilo_provider_npm`, `kilocode_cli.py:1214-1217`.
The full openai-compatible provider implementation (v3, `providerOptionsName`,
`transformRequestBody`) is present in the binary's own code, not just the string.

Also `[ran]`: no `node_modules`, no `*.tgz`, no lockfile was created anywhere in the isolated
XDG tree during any probe, and kilo's logs contain no `registry.npmjs.org` / install activity.
(The binary *does* embed npm's arborist — but for **plugin** installs
(`"Failed to install plugin …"`), a path the provider config never touches.)

**Conclusion:** a `config`-mode provider whose `npm` is a bundled specifier resolves **offline**.
Only an `npm` value outside the bundled 21 would plausibly reach an install path — `[inferred]`,
untested, and irrelevant to Loreley, which emits only bundled specifiers.

---

## 4. Blockers

### B1 — kilo does **not** fail fast on an unreachable endpoint (operational) `[ran]`

Pointing `baseURL` at a dead port: kilo logged, every ~5 s, indefinitely —

```console
WARN service=session.network message=Cannot connect to API: Unable to connect... waiting for network
```

and **did not exit within 150 s** (`EXIT=124`, zero stdout). In a sealed environment a wrong or
unreachable `baseURL` therefore presents as a **hang, not an error**. Loreley's own per-invocation
timeout is what would bound it; the study should not rely on kilo returning an error.

### B2 — seed-portfolio model pin, **two** sites, not one `[read]`

`preflight.py:397` is the one the audit found. There is a **second, harder** one:
`loreley/scheduler/seed_portfolios.py:147` raises `SeedPortfolioStateError` on the *request-build*
path. Patching preflight alone lets a campaign start and then die inside the scheduler.
Full minimal patch (both sites + the settings field + the fingerprint dump): **`proposed-patch.md`**.

### B3 — cost accounting: `LLM_USAGE_PRICING_JSON` **cannot** price the kilo lane `[ran]`

`price_usage_event` short-circuits **before** the pricing table is consulted
(`pricing.py:64-74`):

```python
if event.source == "kilo_cli" or event.api_surface == "kilo_run":
    if event.cost_usd == Decimal("0") and event.total_tokens > 0:
        return _unpriced_zero_cost_placeholder(event)
    return event          # <-- returns before load_pricing_table()
```

kilo's events are tagged exactly that way on the **success** path too
(`normalizers.py` `kilo_usage_event_from_messages`, `defaults={"source":"kilo_cli",
"api_surface":"kilo_run"}` → `price_usage_event(...)`), and `has_catalog_cost` is
`cost_seen and cost_usd > 0` — false when kilo writes `0` — so `cost_usd` stays `None`.

**This corrects the Loreley report.** Its §3.5 / §4 caveat says a self-hosted model "will land as
`unpriced` **unless a pricing JSON is supplied**". Supplying one does **not** help. Demonstrated
with Loreley's own code (`evidence/05_pricing_probe.out`, `evidence/pricing_probe.py`):

```
pricing table loaded: deepseek-probe rules: 2
input  event: 0 unpriced
after price_usage_event: None | unpriced | ''
Does a matching rule EXIST in the table? -> PriceRule(provider='loreley-openai-compatible',
  model='deepseek-v4-pro', api_surface='kilo_run', input_usd_per_1m=Decimal('0.28'), ...)
CONTROL (source=openai_compat): 0.00078669 | estimated | 'deepseek-probe'
```

A **perfectly matching** DeepSeek rule is present and still does not price the kilo event; the
identical counters through a non-kilo `source`/`api_surface` price fine. So the block is the
`kilo_cli` branch, not a missing rule.

**What a DeepSeek entry needs to look like** (necessary shape, for the record — it will not take
effect on the kilo lane as written):

```json
{"version":"deepseek-2026-09",
 "prices":[{"provider":"loreley-openai-compatible","model":"deepseek-v4-pro",
            "api_surface":"kilo_run",
            "input_usd_per_1m":"0.28","cached_input_usd_per_1m":"0.028",
            "output_usd_per_1m":"0.42"}]}
```

`provider`/`model` must match the event verbatim (kilo persists provider
`loreley-openai-compatible`, model `deepseek-v4-pro`); `api_surface` must be `kilo_run` or omitted;
`match_price_rule` is exact-match only — **no globs, no prefixes** (`pricing.py:100-120`).
Note `_cache_reads_are_separate_input_counter` is `True` for kilo events, so kilo's
`cache_read` is **not** subtracted from `input_tokens` — a price entry must not double-count it.

**Does kilo report usage at all for a custom provider?** **Yes** — tokens, per step, in events
and in its SQLite; cost is the only gap. A study that needs dollars must either fix the
`kilo_cli` early return, or price these events downstream from `tokens_*` columns.

---

## 5. Machine state, cleanup, and side effects

* **Nothing started that stays running.** The netns probes and the fake endpoint are dead;
  `pgrep -af kilo` and `pgrep -af fake_openai_server` are empty. One stray fake server survived an
  interrupted first attempt and was killed explicitly.
* **No Loreley source change.** `git status --porcelain` in the checkout is empty (`4c37592`).
  The patch is a proposal document only.
* **No key written anywhere.** `grep -rl "$DEEPSEEK_API_KEY" evidence/` → clean. Auth was
  env-var only; kilo's `credential`/`account` tables are **0 rows**. No `kilo auth` was run.
* **Global config untouched except trivial empty directories.** All probes used
  `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_CACHE_HOME`/`XDG_STATE_HOME` under `/tmp`.
  Non-authoritative note: empty `~/.config/kilo`, `~/.local/share/kilo`, `~/.cache/kilo`
  (10:32:44, before my first command — likely a sibling worker) and empty `~/.local/state/kilo`
  (10:34:19, possibly my unscoped `kilo --version` probe) exist. All contain **no files** and
  are safe to remove: `rm -rf ~/.config/kilo ~/.local/share/kilo ~/.local/state/kilo ~/.cache/kilo`.
* **Ambient proxy is a live hazard.** `http_proxy`/`https_proxy=http://127.0.0.1:7890` were set
  in the environment; the first offline attempt failed *because* of it, and the successful real
  run at §2.2 was re-run with the proxy unset (`remote_ip=101.71.73.135`, direct, HTTP 200).
  Any sealed-environment test must clear these.
* **`adapdc-catalog-postgres-1` was never touched.** No Postgres, Redis, or Loreley worker round
  was run. No packages installed (a pre-existing env at
  `a0/runtimes/loreley/checkout/.venv` was reused to execute Loreley's pricing code).
* Remove probe scratch: `rm -rf /tmp/kiloDS /tmp/kiloDS-wt /tmp/kiloDS-wt2 /tmp/kilo-offline /tmp/kilo-offline-wt /tmp/kiloBad /tmp/kiloDead`.

---

## 6. What would invalidate this

1. A `config`-mode provider whose `npm` is **not** in the bundled 21 (untested — would exercise a
   possible install path). Does not affect Loreley.
2. A kilo upgrade: the bundled-map finding is pinned to **7.7.5**; Loreley's own compatibility
   doc validated against 7.3.16, a 4-minor drift already noted by the earlier audit.
3. Any claim of *dollar* cost for this lane — until B3 is fixed, `unpriced` is the correct answer.
4. Loreley-side equivalence: the patch in `proposed-patch.md` removes a *technical* blocker for a
   DeepSeek seed-portfolio planner; it does **not** make that planner comparable to the
   `gpt-5.6-sol` treatment baseline.

---

## 7. Evidence index

| Artefact | Contents |
|---|---|
| `evidence/env.sh` | env-only credential load + Loreley-shaped `KILO_CONFIG_CONTENT` builder |
| `evidence/01_debug_config_redacted.json` | resolved config, key redacted (env-ref resolution survived) |
| `evidence/02_real_run1_events.jsonl`, `02_real_run2_events.jsonl` | real DeepSeek runs: tool calls, per-step tokens |
| `evidence/03_offline_probe.log`, `03_offline_requests.jsonl`, `03_offline_run_events.jsonl` | zero-egress full-loop proof |
| `evidence/offline_probe.sh`, `evidence/fake_openai_server.py` | the reproducible netns probe and its fake endpoint |
| `evidence/04_bundled_provider_map.txt` | the 21 bundled provider specifiers |
| `evidence/05_pricing_probe.out`, `evidence/pricing_probe.py` | `price_usage_event` on a kilo event vs a control |
| `evidence/06_kilo_stats.out`, `evidence/00_versions.txt` | kilo's own cost/token/tool report; versions |
| `proposed-patch.md` | the two-site seed-portfolio pin fix (proposal, not applied) |
| source anchors | `kilocode_cli.py:322-424, 608-662, 958-988, 1042-1060, 1119-1230, 774-900`; `model_routes.py:105-120`; `normalizers.py:243-293`; `pricing.py:23-42, 64-91, 100-120, 164-165, 168-188`; `preflight.py:397-405`; `scheduler/seed_portfolios.py:145-152`; `config.py:425-428, 1191-1206` |
