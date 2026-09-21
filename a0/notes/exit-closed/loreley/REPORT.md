# Loreley — which backends are open, and what an OpenAI-compatible backend would cost

Owner: `a0/notes/exit-closed/loreley/`. Date: 2026-09-21 (CST).
Source audited: `a0/tasks/circle-packing/upstream/loreley` @`4c375920` (identical to the installed copy,
verified by `diff -rq` — `evidence/recheck.out`). Reproduce with `bash evidence/recheck.sh`.
Method: read source, inspect the host, fetch upstream licence metadata. **No model calls, no installs,
no edits outside this directory.** Where a claim is not measured on this host it is labelled *inference*.

---

## 1. Verdicts

| Question | Verdict | Evidence |
|---|---|---|
| How many agent backends does Loreley have? | **Three**, enumerated from the directory, not from `__init__`: `codex_cli.py`, `cursor_cli.py`, `kilocode_cli.py` | `backends/__init__.py:3-22`; `ls backends/` → `__init__.py codex_cli.py cursor_cli.py kilocode_cli.py` |
| Default planning/coding/seed backend | `kilocode_cli:*` — i.e. **the default lane is already an open-source (MIT) CLI** | `config.py:467-473`, `config.py:418-421`; seam probe: `a0/closure/evidence/04_seam_loreley.log:4-6` |
| Is that default usable here? | **No.** `kilo` is not installed → the shipped default cannot start on this host | `shutil.which('kilo') -> None` (`recheck.out`); closure already recorded it `inconclusive`, never a pass (`a0/closure/VERDICTS.md` §1, §6) |
| Which installed backend is open and usable **with no new code**? | **The codex backend** — `codex` is installed and its CLI is Apache-2.0 upstream. What stays closed on that path is the **model service/auth**, not the binary | `which codex` → `/usr/bin/codex`; `openai/codex` GitHub licence `Apache-2.0`, npm `@openai/codex` licence `Apache-2.0` (`recheck.out`); embedded Apache/MIT notices in the installed binary |
| Which backend is genuinely closed-source? | **`cursor_cli` only** — Cursor's `cursor-agent`; proprietary, and also not installed, and never exercised by A0 | npm `cursor-agent` is an unrelated package (`zalab-inc/cursor_agent`) — Cursor's CLI is not distributed there; `which cursor-agent` → `None` |
| Does Loreley use `claude` at all? | **No.** There is no claude backend; `claude` is installed but irrelevant to this lane | `grep -rn claude loreley/core/worker/agent/` → nothing; CLI_REPORT's KAPSO/EvE gating does not cover Loreley (`a0/env/cli/CLI_REPORT.md:§6`) |
| Can the closed CLIs be dropped with **no new code and no install**? | **No.** Default (kilo) is absent; the only installed backend is codex | table above |
| Can they be dropped with **no new code, one install**? | **Yes — install `kilo` (MIT) and point it at any OpenAI-compatible endpoint.** Loreley already ships that wiring | `kilocode_cli.py:958-988`, `:1042-1060`, `:1119-1160`, `:1214-1217`; `model_routes.py:105-120` |
| Does a written OpenAI-compatible backend avoid the `CODEX_HOME` class of bug? | **Yes, entirely — by construction** | §5 |

**The framing correction that matters most:** the codex *CLI* is open source (Apache-2.0); our
closure work already recommends it (`a0/closure/VERDICTS.md` §1 "Loreley closes by switching to its
codex backend"). So for Loreley, "remove the closed-source CLI" is nearly moot — the exposure is the
**provider credential/service behind the CLI** (on this host: CC Switch relay → `zjapi.com`,
`a0/env/cli/CLI_REPORT.md` §2). Only `cursor_cli` is a closed-source *CLI* dependency, and nothing in
A0 uses it.

---

## 2. Backend inventory

Each row's "switch" is the env var that selects it; selection is pure configuration, no code change
(`config.py:467-473`).

| Backend | External binary / service | Licence (evidence) | Config switch | Command shape | Sandbox/closure posture | Usage source |
|---|---|---|---|---|---|---|
| `codex_cli.CodexCliBackend` | `codex` (default bin `codex`), talks to OpenAI-compatible/ChatGPT provider | CLI **Apache-2.0** (`openai/codex`, npm `@openai/codex`); service closed | `WORKER_{PLANNING,CODING}_BACKEND=…codex_cli:codex_{planning,coding}_backend` | `codex [-m …] [-p …] -a never --sandbox <mode> exec --ephemeral --color never --json [--output-last-message …]`, prompt on stdin | **`read-only` (planning)** / **`workspace-write` (coding)** — the only measured-closed lane | parses `--json` JSONL `token_count` (`codex_cli.py:191-221`) |
| `cursor_cli.CursorCliBackend` | `cursor-agent` (Cursor's proprietary CLI) | **closed** — no licence grant found | `…cursor_cli:cursor_{planning,coding}_backend`; `WORKER_CURSOR_MODEL`, `WORKER_CURSOR_FORCE` | `cursor-agent -p <prompt> --model … --output-format text --force` (prompt in argv) | none exposed; `--force` is the opposite of a sandbox | **none** — `usage_events` empty (`cursor_cli.py:120-126`) |
| `kilocode_cli.KilocodeCliBackend` | `kilo` (default bin `kilo`) — opencode-derived agent CLI; npm `@kilocode/cli`, per-platform binaries | **MIT** (`Kilo-Org/kilocode` LICENSE: "Copyright (c) 2026 Kilo Code / 2025 opencode"); *not installed here* | default for all three lanes; `WORKER_KILOCODE_*` | `kilo run --auto [--pure] [--dir <wt>] [--format json] [--agent …] [--model …] [--variant …] [--title …] <prompt>` | **no sandbox/network/search field at all** (`kilocode_cli.py:457-470`; seam log line 11) | reads Kilo's SQLite session/message rows (`kilocode_cli.py:774-900`) |

Facts quoted per requirement:

* config switch lines — `codex_cli.py:280-296, 299-315`; `cursor_cli.py:129-176`; `kilocode_cli.py:1423-1489, 1534-1570`.
* the `-s workspace-write` our closure work measured is built at `codex_cli.py:171-173` with
  `_requested_sandbox()` at `:276-277` (default `read-only` unless `full_auto`, which the coding factory sets).
* the temp-`CODEX_HOME` behaviour (the measured fact to respect) is `codex_cli.py:243-274`:
  copies only `auth.json` (`:259-260`), writes a config containing **only** a trust level
  (`:262-267`), then `env["CODEX_HOME"] = str(isolated_home)` (`:268`).

---

## 3. What a backend must implement (the contract)

There is **no base class** — the contract is a `Protocol` plus structural loading.

* `AgentBackend` Protocol: **one method**, `run(self, task: AgentTask, *, working_dir: Path) -> AgentInvocation` (`contracts.py:36-45`).
* `AgentInvocation` fields: `command`, `stdout`, `stderr`, `duration_seconds`, `usage_events`, `working_directory` (`contracts.py:11-20`).
* Resolution: `load_agent_backend(ref)` accepts an instance, a no-arg class, or a **no-arg factory**
  (`loader.py:46-81`; the no-arg call is `loader.py:69-72`). It only checks `hasattr(x, "run")`.

Factory shape (all zero-arg, returning a configured instance, exercising the phase's error type):

* `codex_planning_backend()` / `codex_coding_backend()` — `codex_cli.py:280-315` (note: the coding
  factory is what sets `full_auto=True` → `workspace-write`).
* `cursor_backend()` / `cursor_planning_backend()` / `cursor_coding_backend()` — `cursor_cli.py:129-176`.
* `kilocode_backend()` / `kilocode_planning_backend()` / `kilocode_coding_backend()` / `kilocode_seed_portfolio_backend()` — `kilocode_cli.py:1423-1570`.
* seed portfolio also has **`build_kilocode_seed_portfolio_backend(settings)`** (`kilocode_cli.py:1491-1525`),
  because the seed lane is campaign-scoped and the loader's no-arg rule cannot pass settings; the
  default ref is special-cased in `seed_portfolio.py:447-460`.

What the worker actually relies on (this is the real interface, not the annotation):

1. **Write-back into a git worktree.** The backend must edit files in `working_dir`; after each attempt
   the worker diffs a content-aware git snapshot and **retries if nothing changed**
   (`coding.py:197-207`, snapshot at `:374-398`). The prompt demands tracked-file changes, no commits,
   no push (`coding.py:318-333`). Planning is text-only in comparison.
2. **Markdown on stdout.** stdout is coerced into an `ExecutionReport` / `PlanDocument`
   (`coding.py:349-367`, `coerce_agent_stdout_text()` in `agent/utils.py`); `##` sections expected.
3. **Errors must be the phase's error class** (`PlanningError` / `CodingError` / `SeedPortfolioPlanningError`)
   or `run_agent_task` will not retry (`runner.py:18-94`); timeouts raise the same. Kilo additionally
   reports an allowlisted `failure_reason_code` (`runner.py:145-149`, `kilocode_cli.py:38-43`).
4. **Usage/cost accounting via `usage_events`.** Events flow `AgentInvocation` → plan/coding response →
   `llm_usage_events` (`job_store.py:1070-1075`, `evolution.py:2385-2408`), deduped by
   `external_usage_id` (`runner.py:129-133`, unique index `db/base.py:82-83`). A new backend should use
   `normalize_openai_usage_event()` (`normalizers.py:146-186`; sets `provider_reported` if
   `usage.cost > 0`, else `unpriced`) and fall back to `unavailable_usage_event()` rather than failing a
   completed run — the shape kilo uses (`kilocode_cli.py:796-815`). Pricing comes from
   `price_usage_event()` (`pricing.py:64-91`) against a table from `LLM_USAGE_PRICING_JSON`/`…_PATH`
   (`pricing.py:168-188`); the builtin table only has two OpenAI models (`pricing.py:23-42`), and kilo's
   zero-cost-with-tokens placeholder is deliberately demoted to `unpriced` (`pricing.py:69-73, 144-154`).
5. **Isolation/hygiene** (kilo only, but the study will want it): per-`(job,run)` HOME/XDG/TMP
   (`kilocode_cli.py:566-588`), provider-value redaction from stdout and its SQLite (`:598-662`).
6. **Sandbox flags** live only in the codex backend (`:171-173`, `:276-277`); kilo exposes none — which is
   exactly why closure had to switch backends (`a0/closure/VERDICTS.md` §1 row "Loreley").

---

## 4. Can Loreley drop the closed CLIs with **no new code**?

**With one install (recommended zero-code route): yes.**

* The default backend is *already* the MIT-licensed `kilo`; nothing to configure to "use an open CLI".
* Loreley also already speaks "OpenAI-compatible gateway" through kilo: `WORKER_KILOCODE_OPENAI_BASE_URL`,
  `WORKER_KILOCODE_OPENAI_API_KEY`, `WORKER_KILOCODE_OPENAI_MODEL`,
  `WORKER_KILOCODE_OPENAI_API_SPEC=chat_completions` (or `responses`), with
  `WORKER_KILOCODE_PROVIDER_CONFIG_MODE=auto|config` building `KILO_CONFIG_CONTENT` whose provider uses
  `npm: "@ai-sdk/openai-compatible"` and `baseURL/apiKey` env references
  (`kilocode_cli.py:958-988`, `:1042-1060`, `:1119-1160`, `:1214-1217`; provider id resolved in
  `model_routes.py:105-120`). Point that at a self-hosted endpoint (vLLM/Ollama/llama.cpp) and both the
  closed CLI *and* the closed model service are gone.
* Costs/caveats of this route (all configuration-level, no code):
  * requires installing `@kilocode/cli` (MIT) + its platform binary — **out of scope for this audit, so unverified here**;
  * seed-portfolio preflight **fails unless the model id ends in `gpt-5.6-sol`** (`preflight.py:397-407`);
  * kilo has no sandbox field, so the §4.3 closure posture stays OPEN unless an external barrier is used —
    and an external barrier also kills host loopback, so it cannot wrap the model lane
    (`a0/closure/VERDICTS.md` §2.6, `evidence/02_host_loopback_cut.log`);
  * usage/cost for a self-hosted model will land as `unpriced` unless a pricing JSON is supplied;
  * the custom-provider `npm` package is *inference-flagged* as requiring network/for a bundled provider
    cache at first use.

**With nothing installed: no.** The only installed candidate is the codex path, whose CLI is
Apache-2.0 but whose provider/auth stays third-party.

---

## 5. If an OpenAI-compatible backend must be written: the concrete cost

### 5.1 Files to add / touch

| File | Change |
|---|---|
| `loreley/core/worker/agent/backends/openai_compat.py` (new) | the backend class + factories. ~150-300 lines if it drives a real agent loop, less if not (see §5.4) |
| `loreley/core/worker/agent/backends/__init__.py:3-22` | add the exports (optional: a ref may point straight at the module) |
| `loreley/config.py` (next to `:467-473`, and the dump at `:1191-1206`) | optional `WORKER_OPENAI_*` fields (base_url/api_key can already be inherited from `OPENAI_BASE_URL` / `OPENAI_API_KEY`) |
| `loreley/core/seed_portfolio.py:447-460` | special-case the new seed factory the way kilo's `build_*` is special-cased, **or** give the new seed factory zero args |
| `tests/core/worker/test_agent_backends.py` | follow the existing fakes (`test_cursor_cli_backend_builds_command`, `test_builtin_codex_agents_*`) + one usage-event assertion |
| `docs/loreley/core/worker/agent.md:28-35`, `docs/loreley/config.md:26-27`, `docs/adr/00XX-…` | house convention (ADR 0020/0034/0035 are the precedents) |
| `loreley/preflight.py:397-407` | only if the seed lane must run a non-`gpt-5.6-sol` model |

### 5.2 Methods to implement (named)

* **Required by the protocol:** `run(self, task: AgentTask, *, working_dir: Path) -> AgentInvocation`.
* Practical private methods, mirroring the existing backends:
  `_build_command`/`_render_messages`, `_client()` (reuse `build_internal_openai_client_kwargs`,
  `core/openai_auth.py:539-548`, plus `openai_retrying`, `core/openai_retry.py`), a
  `_tool_loop(...)` step (read/write/edit/shell) if the coding contract must be satisfied,
  `_usage_events_from_response(response, task)` → `normalize_openai_usage_event(...)`,
  `_usage_external_id(task, phase=…)`, and a timeout path that raises `self.error_cls`.
* Factory functions to export: `openai_planning_backend()`, `openai_coding_backend()`,
  `openai_backend()`, and (seed) `build_openai_seed_portfolio_backend(settings)` or a zero-arg wrapper.

### 5.3 How it reports usage/cost, and how it is registered/selected

* Usage: return `AgentInvocation.usage_events=(event,)` from `normalize_openai_usage_event(response,
  phase=…, model=…, api_surface="chat_completions", job_id=…, run_token=…,
  external_usage_id=…)`; the worker persists it to `llm_usage_events`. If the response carries no usage,
  emit `unavailable_usage_event(...)` with a reason (never drop the run).
* Cost: provider-reported if the endpoint returns `usage.cost`, otherwise priced from
  `LLM_USAGE_PRICING_JSON`; a self-hosted model with no price entry stays `unpriced` (cost `None`) —
  the study's cost trace must record which of the two happened.
* Registration/selection: **no code change** — set `WORKER_PLANNING_BACKEND` /
  `WORKER_CODING_BACKEND` / `WORKER_SEED_PORTFOLIO_BACKEND` to `module:factory` (`config.py:467-473`,
  `:418-421`). Preflight then loads it and, for an unknown class, emits
  `"warn: unknown backend type; skipping binary checks"` unless the object exposes a `bin` attribute
  (`preflight.py:884-895`). `model_routes` degrades to `backend_defined` for non-kilo backends
  (`model_routes.py:286-287`, `:145-159`) — doctor/`effective_routes` stop reporting model/provider, which
  the study's trace should account for.

### 5.4 The cost that is easy to underestimate

An OpenAI-compatible **chat** endpoint is not an agent. Because the worker enforces actual worktree
changes (`coding.py:197-207`) and a Markdown report, "an OpenAI-compatible backend" means *writing the
agent loop yourself*: tool schemas, file edits, shell execution, per-invocation context assembly,
timeouts, usage extraction, and — for the §4.3 closure requirement — **your own sandbox for the tool
lane**, since the codex backend gets `-s workspace-write` for free and a Python loop gets nothing.
An external cut cannot substitute: it also severs host loopback, so it would kill the model call itself
(`a0/closure/VERDICTS.md` §2.6). Practical size: one backend file (~200-300 lines) for a *text* backend
that satisfies planning but not coding; substantially more for a coding-capable loop (the CLI backends
we are replacing are 185-1585 lines each, and the tool sandbox is the part with no local precedent).
Upside: the self-hosted endpoint has no provider-side `web_search` tool at all, which closes a channel
the closure work could only shut by config (`a0/closure/VERDICTS.md` F3).

### 5.5 Does it avoid the `CODEX_HOME` class of problem?

**Yes.** `codex_cli._prepare_isolated_home` (`:243-274`) re-points `CODEX_HOME` at a temp dir that
contains only `auth.json` and a `trust_level` line, so any `[model_providers.*]`, `model_provider` or
`base_url` in the user's real config is invisible to the child; our bounded round only worked by
setting `WORKER_PLANNING_EXTRA_ENV={"CODEX_HOME":"~/.codex"}` (`a0/runtimes/loreley/VERIFICATION.md:500`),
which also disables the isolation the backend wanted (`early return, codex_cli.py:252-253`). An
HTTP backend takes base URL and key from Loreley's own settings (`OPENAI_BASE_URL`/`OPENAI_API_KEY`,
`openai_auth.py:539-548`) and creates no per-invocation config directory at all — the failure mode
cannot occur. The trade is the lost CLI sandbox (§5.4) plus the loss of kilo's per-job state isolation
and output redaction (`kilocode_cli.py:566-588`, `:598-662`), which a new backend would have to
re-implement if the study wants the same hygiene.

---

## 6. Blockers, unverified, and what would invalidate this

1. **Everything about `kilo` here is code-level.** Installing is out of scope, so `kilo --version`,
   `kilo run --help` flag availability, `KILO_CONFIG_CONTENT` provider resolution, and the usage-DB
   schema are **unverified on this host**. The repo's own proposal verified them on 2026-06-02 at
   `@kilocode/cli` 7.3.16 / local 7.3.1 (`docs/proposals/kilo-cli-compatibility-update.md:15-20`); the
   npm `latest` today is 7.7.5 — a 4-minor drift the zero-code route inherits.
2. **Custom-provider packaging is inference.** `provider.<id>.npm = "@ai-sdk/openai-compatible"` is
   built by Loreley (`kilocode_cli.py:1131-1135`, `:1214-1217`); whether the installed binary resolves
   that package offline (the CLI package depends on `@ai-sdk/…`, and the linux binary is 236 MB) is not
   measured. If it needs npm egress at first use, a hermetic/closed-network deployment fails.
3. **`cursor-agent` is inferred proprietary**: no public source, no licence grant, no npm distribution
   of the real CLI (npm's `cursor-agent` is `zalab-inc/cursor_agent`, unrelated). It is also absent
   here, so the claim has no runtime consequence.
4. **`claude`**: Claude Code's repo has no licence (`license: None` via the GitHub API) and the npm
   package says "SEE LICENSE IN README.md" → proprietary terms. Loreley has no claude backend, so this
   only matters to the KAPSO/EvE lanes.
5. **The codex licence finding contradicts the passing premise.** If the study treats codex as
   closed-source, the correct statement is "closed *service*, open *CLI*"; an "open backend" swap
   cannot fix the provider. Pointing codex at an OSS/local provider is possible in principle
   (the installed binary references an `oss` provider and Ollama — `strings /usr/bin/codex`), but not
   through Loreley's codex backend without defeating its `CODEX_HOME` isolation, i.e. it is the same
   problem as §5.5.
6. **Not run by this audit:** no Postgres/Redis, no Loreley worker round, no campaign. The only
   measured Loreley LLM-lane evidence remains `a0/runtimes/loreley/llm-round/RESULT.md`
   (planning 144.1 s; coding timed out — a wall-clock, not capability, result).
7. **What would invalidate the recommendation:** a real `npm i -g @kilocode/cli` + `kilo debug config`
   probe showing the custom OpenAI-compatible provider does not resolve (kills the zero-code route); or
   a written in-process loop failing the coding `post_check` / scope gate (raises the new-code cost
   materially above the estimate in §5.4).

---

## 7. Evidence index

| Artefact | Contents |
|---|---|
| `evidence/recheck.sh` | the re-runnable, read-only evidence script (licences fetched from GitHub/npm, host binary probe, pinned-commit check, checkout diff) |
| `evidence/recheck.out` | its output, 2026-09-21 09:49 |
| source anchors | `contracts.py:11-45`; `loader.py:46-81`; `runner.py:18-149`; `codex_cli.py:155-190, 243-277, 280-315`; `cursor_cli.py:28-60, 120-176`; `kilocode_cli.py:457-470, 566-662, 716-750, 774-900, 958-988, 1042-1160, 1214-1217, 1423-1570`; `coding.py:197-207, 318-367, 374-398`; `normalizers.py:146-186`; `pricing.py:23-42, 64-91, 168-188`; `preflight.py:397-407, 816-895`; `seed_portfolio.py:447-460`; `model_routes.py:105-120, 145-159, 286-287`; `openai_auth.py:539-548`; `config.py:418-421, 467-473` |
| cross-workstream | `a0/closure/VERDICTS.md` (Loreley row, §2.6), `a0/closure/evidence/04_seam_loreley.log:4-11`, `a0/runtimes/loreley/VERIFICATION.md:500`, `a0/env/cli/CLI_REPORT.md` |
