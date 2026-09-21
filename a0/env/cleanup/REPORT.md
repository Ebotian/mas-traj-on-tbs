# D5 — teardown, local configuration hygiene, key hygiene, rotation checklist

Worker: D5 (owns `a0/env/cleanup/**`). Date: 2026-09-21. Repo `/home/ebt/rsi-dev`, base commit
`f4aa6154` (working tree clean before and after; nothing in this workstream is committed).

Every claim below is `verified by running it` unless marked `read from source` or `inferred`.
Raw transcripts: `a0/env/cleanup/evidence/01..07`.

---

## 0. Verdict summary

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | a0 probe containers/networks removed | **DONE** | `evidence/01_before.txt`, `02_teardown.txt`, `03_after.txt` |
| 2 | `adapdc-catalog-postgres-1` untouched | **DONE** — same container ID, same `StartedAt`, `RestartCount=0`, healthy | `01_before.txt` vs `03_after.txt` |
| 3 | Recorded `teardown.sh` scripts still recreate what they removed | **DONE** (both were executed as the teardown and reported success) | `02_teardown.txt` |
| 4 | Local config hygiene | **PARTIAL** — one change applied (codex), two proposals left to the user | `05_config_hygiene.txt`, `07_codex_probe.txt` |
| 5 | Key hygiene (repo + archive) | **CLEAN** — 0 literal hits for all 4 keys, with positive controls | `06_key_hygiene.txt` |
| 6 | Rotation checklist | **DELIVERED** (§4) — the user must rotate on the provider side | §4 |

One correction to the brief's premise is recorded in §2.2 and §3.1: `~/.codex/config.toml` did
**not** point at `http://127.0.0.1:15722/v1`. It pointed at `https://zjapi.com` (no `/v1`), which
fails for a different reason. The `127.0.0.1:15722/v1` relay reference exists, but in
`~/.kimi-code/config.toml`.

---

## 1. Containers, networks, volumes

### 1.1 Before (2026-09-21T16:45:39+08:00, `evidence/01_before.txt`)

Containers: `a0pc-{proxy,cli,pg,redis}` (Up 6 h), `a0tl-{proxy,cli}` (Up 25 min),
`a0-loreley-{postgres,redis}` (Exited (0) 20 h), `adapdc-catalog-postgres-1` (Up, healthy).
Networks: `a0pc-internal`, `a0tl-internal`, `a0-egress-internal`, `a0-loreley-internal`,
`a0-loreley-net`.
`adapdc-catalog-postgres-1` baseline pinned as
`ID=ec2bbaf149c24317e300ea614110d0b7105daa329e95707148766933ca860a25`,
`StartedAt=2026-09-21T01:11:40.508456929Z`, `RESTARTS=0`, on `adapdc_temporal-network` only.

### 1.2 Exact commands run (`evidence/02_teardown.txt`)

```bash
docker stop a0pc-cli a0pc-pg a0pc-proxy a0pc-redis a0tl-cli a0tl-proxy
bash a0/closure/tool-loop/teardown.sh            # a0tl-*  (recorded script)
bash a0/notes/exit-closed/proxy-closure/teardown.sh   # a0pc-*  (recorded script)
bash a0/runtimes/loreley/infra/net.sh down --networks  # a0-loreley-* + its 2 networks
docker network rm a0-egress-internal             # no teardown script exists for it
docker volume rm eaef1648…c3bad badcca77…d480dc  # the two probe data volumes
```

I used the recorded scripts rather than hand-rolled `docker rm` on purpose: that both performs the
teardown and proves the scripts still do what they claim. `tool-loop/teardown.sh` was run first so
that its "untouched neighbours" check (`a0pc-*` + adapdc) was still meaningful.

### 1.3 After (`evidence/03_after.txt`)

Remaining containers: only `adapdc-catalog-postgres-1` (Up, healthy) and the four
pre-existing `adapdc-*` exited containers. Remaining networks: only `adapdc_temporal-network`,
`bridge`, `host`, `none`. `grep '^a0'` over both container names and network names returns nothing.

`adapdc-catalog-postgres-1` after: **same ID, same `StartedAt`, `RESTARTS=0`, healthy, still only
on `adapdc_temporal-network`** — byte-for-byte the same identity fields as the baseline. It was
never stopped, never connected to an a0 network.

### 1.4 Volumes: what I removed and what I deliberately did not

`docker rm -f` (what both recorded `teardown.sh` scripts use) does **not** remove volumes, so four
anonymous volumes would have survived. I removed only the two whose ownership is unambiguous
because a probe container had them mounted:

| volume | mounted by | created | action |
|---|---|---|---|
| `eaef1648839d…c3bad` | `a0pc-pg` (`/var/lib/postgresql/data`) | 2026-09-21 10:46:37 | **removed** |
| `badcca7739aa…d480dc` | `a0-loreley-postgres` (`/var/lib/postgresql`) | 2026-09-20 17:03:09 | **removed** |

Left in place and **reported rather than deleted** (no owner label, no container reference, so
ownership is not provable — `evidence/04_volumes.txt`):

- `e0fd964a…bc581c` (2026-09-20 15:51) — study-era, unattributed.
- `43afd7c5…6be008` (2026-09-21 10:42), `25e66563…fb9150` (10:44), `c549b58c…7ed7a2` (10:46) —
  study-era, unattributed; these timestamps sit inside the proxy-closure probe window.
- 17 pre-study volumes (2026-09-10/11) and `adapdc_catalog-pg-data` / `adapdc_temporal-pg-data` —
  not this study's. Not touched.

`inferred`: the four study-era volumes above are almost certainly earlier throwaway probes, but I
could not prove it from any label, container reference, or log, so per instruction they stay.

### 1.5 Recreation is still described (verified by reading, not by recreating)

I did **not** recreate anything. Pointers that a third party can follow:

| removed | recreate with | note |
|---|---|---|
| `a0pc-*` containers + `a0pc-internal` | `a0/notes/exit-closed/proxy-closure/setup.sh` | creates network + proxy; `WITH_CLI_CTR`/`WITH_SERVICES` re-create `a0pc-cli`/`a0pc-pg`/`a0pc-redis` (the latter also re-creates the pg data volume fresh) |
| `a0tl-*` containers + `a0tl-internal` | `a0/closure/tool-loop/setup.sh` | idempotent rebuild of proxy + worker |
| `a0-loreley-postgres`/`-redis` + `a0-loreley-{net,internal}` | `a0/runtimes/loreley/infra/net.sh up` | its `down --networks` is exactly what I ran |
| `a0-egress-internal` | `a0/env/checks/probe_egress.sh` | creates it on demand (`probe_egress.sh:233-236`); `a0/env/checks/ENV_REPORT.md:391-392` already records this convention |

`read from source`: each of those scripts contains the corresponding `docker network create` /
`docker run` lines; none of them was edited by me.

### 1.6 Not study leftovers (checked, not removed)

`adapdc-*` containers and `adapdc_temporal-network` (+ `adapdc_catalog-pg-data`,
`adapdc_temporal-pg-data`) belong to a different project. `/tmp` holds EvE-workstream artifacts
(`/tmp/eve/`, `new.eve.json`, `pre-change.simpleloop-eve.json`, `final_eve.log`,
`codex-bwrap-synthetic-mount-targets-1000`) — another workstream's scope and `/tmp/eve/` is
explicitly off-limits, so they are reported, not deleted. Host model-lane sockets are gone:
nothing is listening on 15721/15722.

---

## 2. Local configuration hygiene

Backups (outside the repo — a backup of `settings.json` must never land inside the repository,
since that would put a cleartext key into the repo):

```
~/.codex/config.toml.a0d5-bak-20260921T165606   sha256 b38d65888b66193f1d4935507ff1ee1cd7696ef9179dd3bb374fe7fde425cab6
~/.claude/settings.json.a0d5-bak-20260921T165606 sha256 6bbf3e3274dcc8e5d0c9f08c7731df9a4d229f0610e073a3f657867aff0843a4
~/.codex/auth.json.a0d5-bak-20260921T165606     sha256 c8e52cebd958b107061ed47fa8d03f764e388f13cb87084a1b5afa88d32b8e82
```

All three backups are mode `600`.

### 2.1 APPLIED — `~/.codex/config.toml` (one line)

```diff
--- ~/.codex/config.toml.a0d5-bak-20260921T165606
+++ ~/.codex/config.toml
@@ -7,7 +7,7 @@
 name = "zjapi"
 wire_api = "responses"
 requires_openai_auth = true
-base_url = "https://zjapi.com"
+base_url = "https://zjapi.com/v1"
```

Why this is safe and reversible: it changes no provider, no model, no billing destination — it
repairs the URL path of the provider the user already selected. Revert with
`cp ~/.codex/config.toml.a0d5-bak-20260921T165606 ~/.codex/config.toml`.

Verified end to end (`evidence/07_codex_probe.txt`):

- before: `codex exec …` → `ERROR: unexpected status 404 Not Found: Invalid URL (POST /responses),
  url: https://zjapi.com/responses`, exit 1.
- after: same command → `OK`, `tokens used 14,425`, exit 0.
- the same fix was first proven with a command-line override only
  (`-c model_providers.custom.base_url='"https://zjapi.com/v1"'`), so the claim does not depend on
  having edited the file.

### 2.2 CORRECTION to the brief — the failing URL was not the local relay

`~/.codex/config.toml` (mtime 2026-09-21 09:34) contained `base_url = "https://zjapi.com"` — no
`127.0.0.1:15722`, no `/v1`. Its `custom` provider is the third-party aggregator `zjapi`, not
cc-switch's relay. Plain `codex` did fail, but from the missing `/v1` path segment.

Where `127.0.0.1:15722/v1` actually lives today:

- `~/.kimi-code/config.toml`, provider `[providers.ccswitch-codex]`
  (`base_url = "http://127.0.0.1:15722/v1"`, `type = "openai_responses"`) — dead relay, nothing
  listening. It is **not** the default model (`default_model = "deepseek/deepseek-v4-flash-vision-exp"`),
  so it breaks nothing until selected.
- The study's own scripts/comments (`a0/closure/run_probes.sh:97` `RELAY_PORT=15722`,
  `a0/closure/VERDICTS.md:6`, `a0/closure/README.md:20`).
- cc-switch's own DB has `proxy_config` for `codex` at `listen_port=15721`, `proxy_enabled=1`,
  `enabled=0` — i.e. cc-switch's relay port is 15721 and its proxy mode is currently off
  (`read from source`: `~/.cc-switch/cc-switch.db`).

Its July backup `~/.codex/config.toml.bak` shows the relay form of the same file
(`base_url = "http://127.0.0.1:15721/v1"`), which is the shape the brief was describing — stale by
one cc-switch rewrite (2026-09-21 09:34), which is when cc-switch wrote the direct form.
`inferred`: cc-switch's "direct" template emits `base_url` without `/v1` while its relay form emits
`/v1`, and its July log shows the relay forwarding to `https://zjapi.com/v1/responses` — the
`/v1`-less direct form is a latent defect in that tool.

### 2.3 A false green worth recording: `codex doctor` reachability

Before the fix, `codex doctor` reported
`custom API inference URL https://zjapi.com/responses reachable (HTTP 200)` and
`18 ok · 0 fail`, while the same config failed every real call with 404. After the fix it still
prints `✓ reachability … reachable (HTTP 404)`. The check accepts any HTTP status, so its
label carries no information. Anyone re-deriving "the codex endpoint is fine" from `codex doctor`
will reach the wrong conclusion — use a real `codex exec` (as in `evidence/07`) instead.

### 2.4 PROPOSED, NOT APPLIED — repoint codex at DeepSeek (`/v1`, `wire_api="responses"`)

Left to the user: it changes which account and model bill a plain `codex` invocation. The shape
below is the one the study already verified in
`a0/runtimes/kapso/runs/bridge-2round/codex-home/config.toml` and
`a0/closure/tool-loop/run/run_codex_lane.sh:69-72`, and it matches the user decision already
encoded in `a0/SPRINT-2026-09-21.md:52` (`primary=deepseek-flash`).

```diff
--- ~/.codex/config.toml
+++ ~/.codex/config.toml
@@ -1,10 +1,11 @@
-model_provider = "custom"
-model = "gpt-5.6-terra"
+model_provider = "ds"
+model = "deepseek-flash"
 model_reasoning_effort = "high"
 disable_response_storage = true
 
-[model_providers.custom]
-name = "zjapi"
+[model_providers.ds]
+name = "DeepSeek"
 wire_api = "responses"
-requires_openai_auth = true
-base_url = "https://zjapi.com/v1"
+env_key = "DEEPSEEK_API_KEY"
+base_url = "https://api.deepseek.com/v1"
```

Notes if it is applied: `requires_openai_auth = true` must go — with it codex uses the stored
OpenAI-style credential in `~/.codex/auth.json` rather than `env_key`. The key would then have to be
exported by the invoking shell (the study reads it from `~/gptapi.md`; see §4). I did **not** apply
this, so it is unverified end to end in this workstream — only the two ingredients are measured
(`https://api.deepseek.com/v1/responses` answered 200 in a prior workstream; the `[model_providers.ds]`
shape is in use in the study's own lanes).

### 2.5 PROPOSED, NOT APPLIED — `~/.claude/settings.json` (left byte-identical to its backup)

`diff` against the backup is empty; I changed nothing. Two items, both needing a user decision:

1. **Stale-looking model alias.** All five model slots and the top-level `model` are
   `deepseek-v4.1-flash-expires-on-0910`. Measured today: it **still works** —
   `POST https://api.deepseek.com/anthropic/v1/messages` with that id → `HTTP 200`, response
   `model: "deepseek-v4.1-flash-expires-on-0910"`. So this is a misleading *name*, not a broken
   setting; renaming it changes the user's default model behaviour for no measured benefit.
2. **Cleartext key.** `ANTHROPIC_AUTH_TOKEN` holds the DeepSeek key in plaintext. Explicitly out of
   scope to remove, and removing it would break the claude lane, which
   `a0/STATUS.md:172` records as depending on this file (the file outranks the process environment).

If the user wants the alias refreshed, the minimal diff is a pure rename in 6 places:

```diff
-    "ANTHROPIC_MODEL": "deepseek-v4.1-flash-expires-on-0910",
-    ... (SMALL_FAST / DEFAULT_SONNET / DEFAULT_HAIKU, and "model") ...
+    "ANTHROPIC_MODEL": "deepseek-v4-flash",
```

`deepseek-v4-flash` was measured to work on the same endpoint (HTTP 200). `deepseek-flash` is the
id in DeepSeek's own `/models` list; the anthropic endpoint echoed both.

### 2.6 PROPOSED, NOT APPLIED — `~/.kimi-code/config.toml` (the real dead-relay leftover)

```diff
-[providers.ccswitch-codex]
-type = "openai_responses"
-api_key = "11"
-base_url = "http://127.0.0.1:15722/v1"
-
-[providers.ccswitch-codex.source]
-kind = "apiJson"
-url = "http://127.0.0.1:8765/api.json"
-apiKey = "11"
```

Not applied: it is this CLI's own config, and deleting the provider removes a (currently dead)
option from the user's menu — their call. The same file also carries cleartext keys for
`deepseek`, `302ai`, `openrouter` and `gmicloud` (see §4); I did not touch any of them.

---

## 3. Key hygiene — do the four credentials appear in the repo or the archives?

Search target: the four values in `~/gptapi.md` — `chagpt` (164 chars), `deepseek` (35),
`openrouter_openai_compatible` (73), `gmi-cloud-key` (252). Values were read into shell variables
and never printed or written into the repo. Full output: `evidence/06_key_hygiene.txt`.

| surface searched | method | result |
|---|---|---|
| repo working tree (tracked + untracked, incl. `.gitignore`d) | `grep -rIl -F` over the literal value | **0 files** for all 4 |
| repo git history | `git grep -F` over all 16 commits of `rev-list --all`, plus raw `grep -aF` over both packfiles | **0** for all 4 |
| `/home/ebt/rsi-archive` (loose files) | `grep -rIl -F` | **0** (but this is *vacuous* — see below) |
| `/home/ebt/rsi-archive/trees/*.tar.zst` | `zstd -dc` then `grep -aF` on the stream | **0** for all 4 |
| `/home/ebt/rsi-archive/bundles/*.bundle.zst` | `git clone --mirror` each decompressed bundle, then `git grep -F` over **every** commit of every bundle (circle-packing 17, eve 58, kapso 1987, loreley 644, rsi-dev-a0-audited 12, rsi-dev-head 15) | **0** for all 4 |

**Positive controls (so the zeros mean something):** the same commands with the `EID*` value
`664115e0…9328` return 809 files in the working tree, 3687 path-hits across the 16 commits, and
1762/3053 path-hits in the rsi-dev bundles. The archive method in particular was *vacuous until
fixed*: grepping the compressed `.zst` files directly returns 0 even for `EID*`, because the
bundles are packfiles (zlib) and the trees are zstd. Decompressing first is what makes the archive
sweep a real test.

**Conclusion:** no credential value is present anywhere in the repository (working tree or history)
or in the archived bundles/trees. The repo does contain one credential *fingerprint* —
`a0/notes/exit-closed/claude-deepseek-2.1.278/REPORT.md:243` records
`sha256[:8]=b194aef5` of the DeepSeek key, which I confirmed matches
`sha256(deepseek key)[:8]`. Eight hex characters let someone confirm a guessed key offline; it does
not reveal the key. Worth knowing, not worth "fixing" (rotation makes it moot).

**Where the values do live** (all outside the repo, `verified by search`): `~/gptapi.md`,
`~/.claude/settings.json`, `~/.kimi-code/config.toml`, `~/.pi/agent/auth.json`,
`~/.cc-switch/cc-switch.db`, `~/openevolve/.env`, `~/.zotero/zotero/cguira9f.default/prefs.js`,
plus session/rollout records (`~/.kimi-code/sessions/**/wire.jsonl`, `~/.claude/file-history/**`,
`~/.claude/projects/**.jsonl`, `~/.codex/sessions/**.jsonl`, `~/.pi/agent/sessions/**.jsonl`) —
the four keys have indeed been exposed in session records, as the brief states.
Per-key file inventory: `evidence/08_credential_files.txt`.

---

## 4. Rotation checklist (provider side — the user's action)

### 4.1 What is compromised

| credential | where it leaked | severity |
|---|---|---|
| **deepseek** (`~/gptapi.md` line 3) | the whole study reads it; present in cleartext in ≥8 config/state files and in session records | **highest** — the study depends on it and it is the most widely copied |
| **chagpt** (line 1, OpenAI-compatible) | session records (`~/.codex/sessions`, kimi-code / pi session logs) | high |
| **openrouter_openai_compatible** (line 5) | `~/.kimi-code/config.toml`, session records | high (note: `excluded_providers=[openrouter]` in the study's own policy) |
| **gmi-cloud-key** (line 7, a JWT) | `~/.kimi-code/config.toml`, session records | high — it is a bearer JWT, so it is replayable until it expires |
| `zjapi` OpenAI-style key | `~/.codex/auth.json`, `~/.cc-switch/cc-switch.db` | medium — not in `~/gptapi.md`, not read by the study; rotate with the others since it is the same class of exposure |

### 4.2 What to rotate

Rotate all four in `~/gptapi.md` plus the `zjapi` key. `~/gptapi.md` is a one-line-per-provider
file — replace the value after the colon, keep the `name:` prefix and the exact line order; the
repo's readers are line/prefix-anchored (see 4.3), so the format is part of the contract.

### 4.3 What reads the DeepSeek key, and how (so the study keeps working after rotation)

Rotation is low-friction because **no study artifact stores the value**; everything reads
`~/gptapi.md` at runtime. `verified by reading the files`:

*Runtime readers (3, executable code):*

| file:line | idiom | reads |
|---|---|---|
| `a0/notes/exit-closed/opencode-deepseek/env.sh:5` | `awk -F: '/^deepseek:/{print $2; exit}' "$HOME/gptapi.md"` | deepseek |
| `a0/notes/exit-closed/opencode-deepseek/parallel_probe.sh:7` | same awk idiom | deepseek |
| `a0/notes/exit-closed/kilo-deepseek/evidence/env.sh:4` | `awk -F: -v n="$1" '$1==n{ sub(/^[^:]*:/, ""); print; exit }' "$HOME/gptapi.md"` | **any** of the four, selected by name |

*Documented invocations (comments / READMEs / `reproduce` strings — executed only when a human
pastes them):* `a0/notes/exit-closed/proxy-closure/run_cli_through_proxy.sh:21` and
`probe_closure.sh:72`; `a0/closure/tool-loop/run/{run_codex_lane.sh:25,
run_simpleloop_lane_probe.sh:13, run_simpleloop_adapter.sh:16}`; `a0/closure/tool-loop/README.md`;
`a0/mrc/make_declarations.py:176` (emits the `reproduce` string) and the `reproduce` fields of the
`a0/mrc/**` and `a0/verify/sprint-contract/mrc-falsify/**` JSON fixtures — all use
`sed -n 's/^deepseek://p' ~/gptapi.md|head -1`.

Everything else that needs the key receives it as an inherited environment variable from a shell
that performed one of those reads; nothing re-reads `~/gptapi.md` mid-run. `inferred`: because the
read happens per invocation, a rotated file takes effect on the next run with no rebuild.

### 4.4 Also update after rotation (otherwise something silently breaks)

These hold the **old value** in cleartext and are not derived from `~/gptapi.md`:

1. `~/.claude/settings.json` → `env.ANTHROPIC_AUTH_TOKEN` (the claude lane). Priority note from
   `a0/STATUS.md:172`: this file **outranks** the process environment, so exporting a new key does
   not help while the old one sits here.
2. `~/.kimi-code/config.toml` → `[providers.deepseek].api_key` (and `.openrouter`, `.gmicloud` for
   their keys). This is this CLI's own config; the running CLI may cache it in memory, so restart
   the CLI after editing.
3. `~/.pi/agent/auth.json` (deepseek).
4. `~/.cc-switch/cc-switch.db` → provider `default` (`app_type=claude`) and provider `zjapi`
   (`app_type=codex`) `settings_config` blobs. `cc-switch` rewrites `~/.codex/config.toml` and
   `~/.claude/settings.json` from this DB, so **editing the DB beats editing the files** if
   cc-switch is ever run again — otherwise the old key comes back.
5. `~/openevolve/.env` (deepseek).
6. `~/.zotero/zotero/cguira9f.default/prefs.js` (deepseek) — unexpected, but measured.
7. `~/.codex/auth.json` → `OPENAI_API_KEY` (the `zjapi` key) if that is rotated too.
8. `~/.codex/config.toml` needs **no** change for a DeepSeek rotation (it holds no key; the key
   lives in `auth.json`, or in `env_key`'s environment variable if proposal §2.4 is applied).

Old values will also remain in session/rollout logs and `~/.claude/file-history/`. Those are
historical records, not live config; deleting them is optional and out of this workstream's scope.

### 4.5 Verify after rotation

```bash
# 1. new value is in place and the four lines still parse
sed -n 's/^deepseek://p' ~/gptapi.md | head -1 | wc -c     # expect 36 (35 + newline)

# 2. DeepSeek accepts it (replaces the mrc-falsify reproduce probe)
DS_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
curl -s --noproxy '*' https://api.deepseek.com/anthropic/v1/messages \
  -H "x-api-key: $DS_KEY" -H 'anthropic-version: 2023-06-01' -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","max_tokens":4,"messages":[{"role":"user","content":"hi"}]}' \
  -o /tmp/rot.json -w 'http=%{http_code}\n'      # expect http=200

# 3. the claude lane still starts
claude --version && echo 'ok'

# 4. codex (only if §2.4 was applied; otherwise `codex exec` uses zjapi and needs no DeepSeek key)
DEEPSEEK_API_KEY=$DS_KEY codex exec --skip-git-repo-check --sandbox read-only \
  -c model_reasoning_effort='"low"' "Reply with exactly: OK"

# 5. re-run the key-hygiene sweep from §3 and confirm the NEW value is also absent from the repo
```

`note`: step 2 costs ~4 output tokens. `note`: if `~/.claude/settings.json` still holds the **old**
key, step 3 can appear to work while actually using the stale credential — check with
`grep -c "$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)" ~/.claude/settings.json` (expect `1`).

---

## 5. What changed relative to what was previously reported

- `a0/SPRINT-2026-09-21.md:103` ("D5（清理与轮换）") said `a0pc-*`/`a0tl-*` containers and two
  internal networks were still running and listed only two networks. Measured before-state had
  **five** a0 networks (`a0pc-internal`, `a0tl-internal`, `a0-egress-internal`,
  `a0-loreley-internal`, `a0-loreley-net`) and **eight** a0 containers, including the two
  `a0-loreley-*` ones. All eight containers and all five networks are now gone (§1).
- That line described the codex problem as a dead `127.0.0.1:15722` relay. Corrected in §2.2: the
  relay path is in `~/.kimi-code/config.toml`, while `~/.codex/config.toml` was failing on a
  missing `/v1` against `zjapi.com`.
- `a0/notes/exit-closed/local-model/REPORT.md` §2.1 called the direct form "the failing direct
  form" and inferred that codex "cannot complete a call". That inference is now **confirmed by an
  actual call** (404, exit 1) and the cause is identified (`/v1`), which that report did not
  establish. Its §6 blocker 5 ("codex is currently broken again") is now **resolved** by §2.1 here.
- `a0/env/checks/ENV_REPORT.md:391-392` already claimed `a0-egress-internal` was "removed";
  it was in fact still present today. It is now actually removed.

## 6. Open / not done

1. `~/.claude/settings.json`, `~/.kimi-code/config.toml` and `~/.codex/auth.json` still contain
   cleartext credentials. I was instructed not to remove them; they are a user decision (§2.5, §2.6).
2. Proposal §2.4 (codex → DeepSeek) is unapplied and therefore **not verified end to end** in this
   workstream; only its two ingredients are measured.
3. Four unowned study-era Docker volumes were left in place (§1.4) — reported, not deleted.
4. The five `cc-switch` `proxy_config` rows still have `proxy_enabled=1` (port 15721). If anyone runs
   `cc-switch -a codex proxy enable` without also starting the daemon, codex will point at a dead
   relay again — the exact failure `a0/closure/VERDICTS.md:6` records.
5. `codex doctor`'s reachability check is misleading (§2.3). Worth a line in the environment report;
   `a0/STATUS.md` and `a0/env/checks/ENV_REPORT.md` are owned by other workstreams, so I did not
   edit them.
6. Session/rollout logs still contain the pre-rotation keys (§4.4). Cleanup is optional and outside
   this directory.
