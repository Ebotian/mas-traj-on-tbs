# codex 0.155.1 — does the retirement verdict still hold?

Owner: `a0/notes/exit-closed/codex-0.155.1/**`. Date of all measurements: 2026-09-21 (CST, UTC+8).
Exact version strings tested: **`codex-cli 0.155.1`** (`/usr/bin/codex`) against **`codex-cli 0.154.0`**
(extracted from the retained pacman package `/var/cache/pacman/pkg/openai-codex-0.154.0-1-x86_64.pkg.tar.zst`).
Method: execution. Every verdict below is labelled **verified by running it**, **read from source**,
or **inferred**. Key material was read into an env var inside the same shell command that used it;
no artefact under this directory contains the key (checked, §7). Global config was never modified —
all config tests used isolated `CODEX_HOME` directories under `scratch/`.

---

## 1. Verdict

**Retirement does not stand. Codex is usable again — against DeepSeek, with no new software.**

But the reason is *not* the one the plan anticipated. **codex did not regain chat-completions
support.** `wire_api = "chat"` is still a hard config-load error in 0.155.1, exactly as in 0.154.0,
and the binary still contains **zero** chat-completions request paths. Nothing on the codex side moved.

What moved is a **premise on the other side of the argument**. The retirement case rested on:

> codex speaks Responses only, *and* both available providers serve Chat Completions (DeepSeek) or
> Anthropic Messages.

The first clause is confirmed. **The second clause is false.** DeepSeek serves a real, fully-formed
**Responses API at `POST https://api.deepseek.com/v1/responses`**, and codex 0.155.1 drives it
end-to-end — streaming, tool use, file patching, shell execution — with exit 0.

So the shape of the answer is: *still Responses-only, but the premise that nothing serves Responses
is wrong, therefore the retirement does not hold.*

**Two further corrections to the record:**

1. **The upgrade is not what invalidated the verdict.** I ran the same live test against the retained
   **0.154.0** binary: it works too. The verdict was **already wrong before the upgrade**. The prior
   verification's error was a gap in endpoint exploration (it probed `/models` and
   `/chat/completions` and concluded "Chat Completions only"), not a version effect.
2. **OpenRouter's exclusion is irrelevant to this lane.** The decision to exclude OpenRouter does not
   bind here, because DeepSeek alone carries codex. DeepSeek is the primary model *and* it serves
   the wire API codex needs.

---

## 2. Static evidence: the codex side did not change

Both binaries are the same build family: Arch `extra/openai-codex`, stripped x86-64 PIE ELF, same
interpreter (`/lib64/ld-linux-x86-64.so.2`), size 244 810 808 → 250 292 704 bytes (+2.2 %), each
with its own BuildID. The pacman log records the single upgrade
**`openai-codex (0.154.0-1 -> 0.155.1-1)`** at `2026-09-21T10:27:26+0800`.

Byte-level counts over each whole binary (identical command, `evidence/05_ab_paths.txt`):

| pattern | 0.154.0 | 0.155.1 |
|---|---|---|
| `/chat/completions` | **0** | **0** |
| `chat/completions` | **0** | **0** |
| `chat.completions` | **0** | **0** |
| `/v1/chat` | **0** | **0** |
| `/completions` | **0** | **0** |
| `/responses` | 41 | 40 |
| `/v1/messages` | 0 | 0 |

The count is stable across `strings -n 4/5/6/8/10` (all give 0 chat paths, 40 responses paths), so
the zero is not a `strings` windowing artefact. The `/responses` 41→40 delta is a string-boundary
shift, not a removal.

The enumerated `wire_api` values are **unchanged and still Responses-only**. The only value-adjacent
tokens are `responses` and the internal transport name `responses_websocket`
(`wanted exactly 1 element…wire_apiresponses_websocketguardian_credits_requested`). There is no
`chat` variant anywhere in the enum.

**The vendor's own removal nag is still present, verbatim, in both builds** — 7 copies each:

```
`wire_api = "chat"` is no longer supported.
How to fix: set `wire_api = "responses"` in your provider config.
`ollama-chat` is no longer supported.
How to fix: replace `ollama-chat` with `ollama` in `model_provider`, `oss_provider`, or `--local-provider`.
```

**`codex --help` is byte-identical between 0.154.0 and 0.155.1** (`diff -u` → empty, for both
`codex --help` and `codex sandbox --help`). Every subcommand, flag and enumerand the lanes use is
present in both with identical text. Notably `-s, --sandbox <SANDBOX_MODE>` still enumerates
`[possible values: read-only, workspace-write, danger-full-access]`, and `--oss` /
`--local-provider <lmstudio|ollama>`, `--search`, `-c/--config`, `--strict-config` all survive.

---

## 3. Config-validation evidence: `wire_api = "chat"` is still rejected — in both versions

Five isolated `CODEX_HOME` directories, each a `[model_providers.ds]` block differing only in
`wire_api`. Validated with `codex debug models`, which loads configuration and makes **no model
call** (`evidence/11_ab_config.txt`, `evidence/12_error_text.txt`, `evidence/13_ab_error_text.txt`):

| `wire_api` value | 0.154.0 | 0.155.1 |
|---|---|---|
| `"chat"` | ✗ config could not be loaded | ✗ config could not be loaded |
| `"responses"` | ✓ config loaded | ✓ config loaded |
| `"responses_websocket"` | — | ✗ config could not be loaded |
| `"bogus"` | ✗ config could not be loaded | ✗ config could not be loaded |
| *(omitted)* | ✓ config loaded (defaults to `responses`) | ✓ config loaded |

The exact rejection text is byte-identical across the two versions:

```console
$ CODEX_HOME=.../scratch/home_chat codex exec "say hi"
Error loading config.toml: `wire_api = "chat"` is no longer supported.
How to fix: set `wire_api = "responses"` in your provider config.
More info: https://github.com/openai/codex/discussions/7782
in `model_providers.ds.wire_api`
```

The same rejection fires through the **`-c` injection seam** EvE uses
(`-c 'model_providers.ds.wire_api="chat"'` → same error), so no lane can smuggle chat in via argv.

**Conclusion of steps 1–2: the codex side is closed for chat, unchanged, in both versions.** The door
that turns out to be open is on the provider side.

---

## 4. The finding that decides it: DeepSeek serves the Responses API

The prior probe surveyed `GET /models` and `POST /v1/chat/completions` and concluded DeepSeek was
Chat-Completions-only. **It never tried `/v1/responses`.** It does exist, it is genuine, and it is
not a permissive catch-all (`evidence/15`–`17_endpoint_probe.txt`):

```console
$ curl -X POST https://api.deepseek.com/v1/responses -H "Authorization: Bearer $DS_KEY" \
       -H 'Content-Type: application/json' -d '{"model":"deepseek-flash","input":"say OK"}'
HTTP/2 200
server: openresty
x-ds-trace-id: c72fef9a7176796956d0372b87746b52
```

```json
{"id":"f4074cfb-…","object":"response","status":"completed","model":"deepseek-flash",
 "output":[{"type":"reasoning","content":[{"type":"reasoning_text","text":"We need answer simply \"OK\"…"}],
            "encrypted_content":"…-0"},
           {"type":"message","role":"assistant","phase":"final_answer",
            "content":[{"type":"output_text","text":"OK"}]}],
 "store":false,"parallel_tool_calls":true,"service_tier":"default"}
```

This is a correct Responses object — `object:"response"`, `status`, `output[]` with
`reasoning`/`message` items, `output_text` content, `encrypted_content`, `store`,
`parallel_tool_calls`, `usage.input_tokens_details.cached_tokens`. Controls rule out a synthetic or
catch-all proxy:

| control | result |
|---|---|
| bogus model id | **400** `The supported API model names are deepseek-flash, deepseek-v4-pro…` |
| no auth header | **401** `Authentication Fails (governor)` |
| bogus path `/v1/responses_bogus` | **404** |
| `stream: true` | **200**, 30 `event:` SSE frames starting `response.created` |
| `deepseek-v4-pro` | **200**, `usage {input 85, output 16, total 101}` |

Both available model ids work over the Responses wire. **That is the clause the retirement argument
was missing.**

---

## 5. The decisive test: codex 0.155.1 against DeepSeek, end to end

Configured with an isolated `CODEX_HOME` and nothing exotic
(`model = "deepseek-flash"`, `[model_providers.ds] base_url = "https://api.deepseek.com/v1"`,
`env_key = "DS_KEY"`, `wire_api = "responses"`).

**5.1 Minimal call** (`evidence` — transcript in `/tmp/live1.out`, reproduced below):

```console
$ CODEX_HOME=scratch/home_live codex exec --skip-git-repo-check --sandbox read-only \
    "Reply with exactly the two characters: OK"
OpenAI Codex v0.155.1
model: deepseek-flash
provider: ds
approval: never
sandbox: read-only
warning: Model metadata for `deepseek-flash` not found. Defaulting to fallback metadata;
         this can degrade performance and cause issues.
codex
OK
tokens used
8,719
[exit 0]
```

**5.2 Full agentic loop — patch, shell, output.** Task: create `hello.py`, run it, capture stdout.
Verified from the filesystem, not from the model's claim:

```console
$ ls scratch/tool-cwd
hello.py  out.txt
$ cat hello.py   →  print('CODEX_DS_OK')
$ cat out.txt    →  CODEX_DS_OK
[exit 0, tokens used 1,553, sandbox: workspace-write]
```

That run exercised `apply_patch` **and** the shell tool through DeepSeek's Responses wire — the
tool-calling path the lanes actually depend on.

**5.3 EvE's provider-injection seam.** With a **completely empty `CODEX_HOME`** (no `config.toml`)
and the provider supplied entirely by `-c`, exactly as `drivers/codex_exec.py` and
`drivers/codex_tmux.py` do:

```console
$ CODEX_HOME=scratch/home_empty codex exec --skip-git-repo-check --sandbox read-only \
    -c model="deepseek-flash" -c model_provider="ds" \
    -c model_providers.ds.name="DeepSeek" \
    -c model_providers.ds.base_url="https://api.deepseek.com/v1" \
    -c model_providers.ds.env_key="DS_KEY" \
    -c model_providers.ds.wire_api="responses" \
    "Reply with exactly: INJECTED"
provider: ds
codex
INJECTED
tokens used
1,081
[exit 0]
```

**5.4 Session resume** — `codex exec resume --last … "Reply with exactly: RESUMEOK"` → exit 0,
506 tokens. *Caveat: the run printed a **new** session id and only the new prompt, so I did **not**
verify that prior-turn context was actually replayed. `resume` completed against DeepSeek; that is
all this proves.* Worth its own probe before a lane relies on KAPSO's inbox continuation.

**5.5 The same test on 0.154.0** — the retained old binary, unchanged config:

```console
$ evidence/bin154/usr/bin/codex exec --skip-git-repo-check --sandbox read-only "Reply with exactly: OLDWORKS"
OpenAI Codex v0.154.0
model: deepseek-flash
provider: ds
codex
OLDWORKS
tokens used
1,498
[exit 0]
```

**This is the version-attribution result: 0.154.0 works too.** The upgrade neither caused nor fixed
this. The retirement verdict was already incorrect at 0.154.0.

---

## 6. The version-sensitive details our closure and lane design references

All four items the assignment named were re-tested. **None moved.** `evidence/18`–`20`.

| Item | 0.154.0 record | 0.155.1 observed |
|---|---|---|
| `--sandbox workspace-write` | blocks even `socket()` | **unchanged** — `permission: Operation not permitted` (errno 1) on `socket.socket()` |
| `--sandbox danger-full-access` | the unconfined posture | **unchanged** — accepted (positive control: `socket() OK`); invalid values rejected with the same 3-value enumeration |
| `--sandbox read-only` | — | also blocks `socket()`, same errno |
| `CODEX_HOME` isolation | the Loreley/SimpleLoop knob | **unchanged** — used for every test here; `codex doctor` reports "CODEX_HOME was resolved without config" and a nonexistent path is a hard error |
| `-c model_providers…` injection (EvE) | the seam | **unchanged** — verified working end-to-end in §5.3 |
| `wire_api` accepted values | `responses` only | **unchanged** — §3 |

Two details worth adding to the closure records, both **unchanged from 0.154.0** (I A/B'd them, so
they are not upgrade regressions):

* **`workspace-write` is not "no filesystem writes" — it is "writes in {workdir, `/tmp`, `$TMPDIR`}"**,
  which the CLI states itself: `sandbox: workspace-write [workdir, /tmp, $TMPDIR]`. Verified: writing
  `probe.txt` in cwd succeeds; writing `/tmp/outside_probe.txt` **succeeds**; writing
  `$HOME/outside_home_probe.txt` fails with `Read-only file system`. This matters here because
  **`/tmp` on this host is a 16 GiB RAM-backed tmpfs**, so a candidate sandboxed as `workspace-write`
  can still touch RAM-backed shared state outside the worktree. The existing closure evidence only
  asserted the socket() result; this is a second, previously unrecorded channel.
* **The new-looking `permission_profile` / `default_permissions` config keys are not new** — they are
  present in 0.154.0 in comparable counts (49/35 strings vs 45/35). `default_permissions` errors with
  ``default_permissions requires a `[permissions]` table``, and `sandbox_mode` remains usable and
  non-conflicting on its own. No lane needs to migrate.

**Nothing else in the records describes 0.154.0 behaviour that has moved.** The only behavioural
difference I could find between the two builds that is relevant to anything in our notes is the
fleet-side model catalog (0.155.1 carries `gpt-6-astra`), which no lane references.

---

## 7. Recipe, cost, and hygiene

**Recipe (verified).** No install, no code change; this is the same shape as the existing EvE
injection, with `wire_api = "responses"` and DeepSeek's `/v1` base URL:

```toml
model = "deepseek-flash"
model_provider = "ds"
[model_providers.ds]
name     = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
env_key  = "DS_KEY"        # name of a var; never the value
wire_api = "responses"     # still the only accepted value
```

or, for lanes that pass no config file (EvE, SimpleLoop): the same keys as `-c` / parent-env
`CODEX_HOME`. `deepseek-v4-pro` works identically by changing `model`.

**One real caveat, printed on every call:** `warning: Model metadata for 'deepseek-flash' not found.
Defaulting to fallback metadata; this can degrade performance and cause issues.` Codex is sizing and
configuring a model it has no catalog entry for. The binary carries a `model_catalog_json`
config key ("model_catalog_json path ...") that is the obvious fix; supplying a correct entry for the
DeepSeek ids is **not tested here** and should be done before a long campaign, because the warning
explicitly names performance degradation.

**Cost.** All model spend, from the counts the tools printed:

| Call | tokens |
|---|---|
| codex 0.155.1 minimal ("OK") | 8,719 |
| codex 0.155.1 tool loop | 1,553 |
| codex 0.155.1 `-c` injection | 1,081 |
| codex 0.155.1 resume | 506 |
| codex 0.154.0 (A/B) | 1,498 |
| codex 0.155.1 recipe re-verification | ~500 |
| **codex total** | **≈13,900** |

Plus a handful of curl probes (`/responses` ×4, one reporting `usage: 85 in / 16 out / 101 total`).
At `deepseek-flash` rates this is **well under one US cent** — far inside the budget.

**Hygiene.** The key was read from `~/gptapi.md` into an env var in the same command that used it.
Grepping every file under this directory for the key's exact value returns **nothing**. No global
config file was read-modified or written: every test ran under its own `CODEX_HOME` under `scratch/`,
and `~/.codex/config.toml` was left untouched. No service, container or daemon was started. The only
network writes were the DeepSeek calls above.

---

## 8. What this invalidates, and what is still open

**Invalidates:**

* The plan step **"retire codex entirely"** as written. Its stated basis (Responses-only *and* no
  available provider serves Responses) is half false.
* The record in `a0/notes/exit-closed/local-model/REPORT.md` §1.1/§2.1 characterizing DeepSeek as
  Chat-Completions-only, and the `kapso/REPORT.md:46` note that codex's lane is
  "no — Responses API + ChatGPT/auth path": with a custom `model_providers` block against DeepSeek,
  the protocol objection is gone.
* Any note implying the codex verdict turned on the 0.154.0→0.155.1 upgrade. It did not.

**Still open (not resolved here, and they are what actually decide the plan now):**

1. **Long-context and long-horizon behaviour.** The lanes send 18–20k-token protocol prompts and run
   thousands of turns. My calls were tiny. DeepSeek's Responses implementation is only proven on
   small requests.
2. **Session-resume context retention** (§5.4) — the KAPSO inbox-continuation path.
3. **`model_catalog_json`** metadata for the DeepSeek ids, to remove the fallback-metadata warning.
4. **Whether the Responses path bills/behaves differently** from `/chat/completions` (cache
   accounting, `store`, reasoning tokens) — the `usage` shape is correct but long-run cost is
   unmeasured.

**Known scope limit of this pass:** step 3 of the brief was to make "one minimal real call … if step 1
or 2 leaves the door open". Steps 1–2 left the *chat* door closed, but the provider-side probe opened
a different one, so I spent a few small calls establishing that codex genuinely drives DeepSeek. I
stopped at five calls rather than characterising the lane further.

---

## 9. Reproducing the 0.154.0 A/B, and evidence index

The 0.154.0 side of every A/B above used the **still-retained pacman package**, extracted rather than
replaced. The 244 MB extracted binary was deleted after the tests (the repo does not ignore this
path); re-create it with:

```bash
cd a0/notes/exit-closed/codex-0.155.1/evidence
mkdir -p bin154 && cd bin154
tar --zstd -xf /var/cache/pacman/pkg/openai-codex-0.154.0-1-x86_64.pkg.tar.zst usr/bin/codex
./usr/bin/codex --version      # → codex-cli 0.154.0
```

Config fixtures for every scenario are preserved under `evidence/setups/`. The codex transcripts in
`evidence/22`–`26` were captured from the live runs; the CODEX_HOME session state behind them was
scratch and has been removed.

| Artefact | Contents |
|---|---|
| `evidence/01_version_identity.txt` | `codex --version`, both binaries' file/BuildID/size, `which -a` |
| `evidence/02`, `03`, `04_strings_*.txt` | path-count scan, `wire_api` nag strings, enum tokens |
| `evidence/05`, `06_ab_*.txt` | byte-level path counts and removal nags, 0.154.0 vs 0.155.1 |
| `evidence/07_help.txt`, `08_subhelp.txt` | `codex --help`, `doctor`/`debug`/`exec` help |
| `evidence/09`, `10_doctor_*.txt` | `codex doctor` across all five `wire_api` homes |
| `evidence/11_ab_config.txt` | the A/B config-acceptance matrix |
| `evidence/12`, `13_ab_error_text.txt` | the exact `wire_api = "chat"` rejection text, both versions |
| `evidence/14_injection_strict.txt` | `-c` injection rejection; `--strict-config` availability |
| `evidence/15`, `16`, `17_ds_responses_*.txt` | DeepSeek `/responses` 200 + full body; 400/401/404 controls |
| `evidence/18_sandbox_retest.txt`, `20_sandbox_forms.txt` | socket() under each sandbox mode; flag parsing |
| `evidence/19_ab_feature_strings.txt` | A/B presence of config/behaviour strings incl. `permission_profile` |
| `evidence/21_endpoint_final.txt` | `/responses` with `deepseek-v4-pro`; SSE stream; usage |
| `evidence/22_live_0.155.1_minimal.txt` | the decisive codex-0.155.1 ↔ DeepSeek call (8,719 tok) |
| `evidence/23_live_0.155.1_toolloop.txt` | apply_patch + shell + file verification (1,553 tok) |
| `evidence/24_live_0.155.1_c_injection.txt` | EvE-style `-c` seam, empty `CODEX_HOME` (1,081 tok) |
| `evidence/25_live_0.155.1_resume.txt` | `exec resume --last` (506 tok; context retention unverified) |
| `evidence/26_live_0.154.0_A-B.txt` | **the old binary also works against DeepSeek** (1,498 tok) |
| `evidence/27_ds_responses_v4pro.json`, `28_ds_responses_stream_sse.txt` | raw Responses objects / SSE frames |
| `evidence/setups/*.config.toml` | every `CODEX_HOME` fixture used |
