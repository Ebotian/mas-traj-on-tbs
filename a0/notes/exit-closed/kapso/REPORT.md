# KAPSO exit-closed audit — which lanes are open source, and can it run with zero closed-source CLIs?

Owner: `a0/notes/exit-closed/kapso/`. Audit date 2026-09-21. Source audited:
`/home/ebt/kapso_ck/kapso` @ `7d99b152` (read-only, never modified). No model call, no install,
no process started; every fact below is from source (`path:line`) or from an in-process
construction probe (`probe_lane_construct.py`, log in `logs/lane_construct.log`).

Protocol context read-only: `open_world_plan_review.typ` §3.3 (KAPSO row) and §4.0 (toolchain).

---

## 1. Answer

**No lane lets KAPSO's study-relevant path — `GenericSearch` evolve with a registered
evaluation — run with zero closed-source CLIs.** Four lanes invoke no closed binary at all
(`aider`, `gemini`, `openhands`, `openai_compatible`), but none of them can be selected for the
two phases that matter (ideation, implementation) and none of them can produce the score of
record. The cap is not in the lane registry; it is in the strategy code, which hardcodes
`claude_code` (and `codex` for one ensemble member and the research role) at every mandatory
site, and validates `implementation_cli` to `{claude_code, codex}` only.

What *can* be removed by config alone: the **inference layer**. Set
`inference.default.cli: openai_compatible` with a loopback `base_url` +
`allow_missing_api_key: true` and every text-only completion role (rerank, KG navigate,
repo memory, commit message, benchmark utility) runs with no closed CLI and no hosted API.
Upstream states the same limit itself: *"Setting the default to `openai_compatible` does not
replace `GENERIC` ideation or implementation: those sessions still use their separately
configured Claude Code/Codex backends"* — `docs/evolve/coding-agents.mdx:221-223`.

The cheapest correct answer to "can it run with zero closed-source CLIs" is therefore:
**only after source patches at ~10 sites, plus losing the in-session evaluation channel** —
see §6.

---

## 2. Lane inventory

Registry source: `execution/coding_agents/agents.yaml`; loader
`execution/coding_agents/factory.py:283-320` (`_register_from_yaml`, `register`,
`_default_agent = config["default_agent"]`), manifest validator
`core/agent_manifest.py:15-27`.

| lane (yaml line) | external binary / service it actually invokes | that dependency's licence | model-side requirements | config switch that selects it | arbitrary OpenAI-compatible endpoint? |
|---|---|---|---|---|---|
| `claude_code` (:74) | `claude` CLI binary — `_verify_cli` `claude_code_agent.py:245`, argv `claude -p --dangerously-skip-permissions …` `:1179-1198` | **closed source** (Anthropic Claude Code, `npm install -g @anthropic-ai/claude-code`, yaml `:83`) — the CLI is proprietary; verified from the invocation, not from a licence file | Anthropic Messages API, tool use (Edit/Read/Write/Bash), `--output-format stream-json`, server-side WebSearch/WebFetch | `coding_agent.type` / `feedback_generator.type` / `evaluation_maintainer.type` in a mode config (e.g. `config.yaml:142,150,204,212`); default `agents.yaml:28` | no — Anthropic protocol only |
| `codex` (:172) | `codex` CLI binary — `shutil.which("codex")` `codex_agent.py:146`, argv `codex [--search] exec --sandbox … --output-last-message …` `:183-208` | **closed source** (OpenAI Codex CLI, `npm install -g @openai/codex`, yaml `:182`) — verified from the invocation | OpenAI **Responses** API (`POST /responses`, per the recorded 404 in `a0/env/cli/CLI_REPORT.md` §3.1), shell/apply_patch tools, native web search, thread ids for resume | `implementation_cli: codex` (`strategy.py:345-347`), `inference.default.cli: codex` (`config.yaml:31`) | no — Responses API + ChatGPT/auth path |
| `oss_claude_code` (:102) | **the same `claude` CLI binary** — inherits `ClaudeCodeCodingAgent` (`oss_claude_code_agent.py:55`), `shutil.which("claude")` `:83` | **closed source** (identical npm package, yaml `:112`). Only the *endpoint* is open/other | Anthropic-compatible endpoint only; `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` (`:108-109`); no WebSearch (server-side tool) | `coding_agent.type: oss_claude_code` + `agent_specific.base_url` + `auth_token_env` | no — Anthropic-compatible, **not** OpenAI-compatible |
| `aider` (:34) | **no binary** — `from aider.coders import Coder` (`aider_agent.py:14`), in-process | open source (aider, Apache-2.0) — **not verifiable on this host**: `aider-chat` is not installed (`ModuleNotFoundError`, `logs/lane_construct.log`) and PyPI is unreachable from here | whatever litellm/Aider speaks to the model; diff/whole/udiff edit formats, auto-commit | `coding_agent.type: aider` (but the lane is **not registered** without the extra — `factory.py:315-320` swallows the ImportError; `--list-agents` shows five) | *not from KAPSO config*: the adapter does only `Model(self.config.model)` (`aider_agent.py:100,115`) and reads no base_url. Aider honours ambient `OPENAI_API_BASE`; **guess, unverified** (not installed) |
| `gemini` (:54) | Google GenAI SDK → Google's hosted Gemini API — `genai.Client(api_key=...)`, `client.models.generate_content(...)` (`gemini_agent.py:61-67,123-132`) | client lib open source (google-genai, Apache-2.0); **the service is proprietary**. Neither verifiable here (not installed) | single `generate_content` call, no tools; output parsed for code fences and written to files (`:179-236`) | `coding_agent.type: gemini` | no plumbing: `GOOGLE_API_KEY` + api_key only; KAPSO never sets an endpoint. (The SDK may honour its own base-url env vars — **guess, unverified**) |
| `openhands` (:127) | OpenHands SDK → litellm → provider API — `from openhands.llm import LLM`, `llm.completion(messages=...)` (`openhands_agent.py:63-69,140-152`) | open source (OpenHands / `openhands-ai`, MIT; litellm MIT — litellm 1.75.0 MIT **verified locally** from installed dist metadata). OpenHands itself not installed here | one chat completion, no tools, no sandbox; output parsed for code fences and written to files (`:178-233`) | `coding_agent.type: openhands` | no KAPSO plumbing; litellm may read ambient `OPENAI_API_BASE`/`OPENAI_BASE_URL` — **guess, unverified** |
| `openai_compatible` (:149) | **no binary, no service of its own** — `openai` SDK to any configured endpoint (`openai_compatible_agent.py:73-75,116`) | open source on both sides: `openai` Python SDK Apache-2.0 **verified locally** (3.16.2 dist metadata) + any Chat-Completions server (vLLM Apache-2.0 / llama.cpp MIT / Ollama MIT) | **Chat Completions only** (`.chat.completions.create`, `:116`); **tools impossible by construction** (`tools`/`tool_choice`/`functions` are reserved and rejected, `:39-59`; any `tool_calls` response is an error, `:131-134`); no streaming | `inference.default.cli` / `inference.roles.<role>.cli` (`config.yaml:31`, `cli_inference.py:111-125`); `inference_only: true` (`agents.yaml:154`) | **yes, this is the lane for it**: `base_url` (config-only, HTTPS unless literal loopback — `core/api_endpoint.py:16-44`), `api_key_env` (a var *name*), `allow_missing_api_key: true` for an unauthenticated local server |

Note on the assignment's wording: `openai_compatible_agent.py` reads `spec["base_url"]`,
`spec["api_key_env"]`, `spec["allow_missing_api_key"]`, `max_output_tokens`, `temperature`,
`timeout`, `request_options` — it does **not** read `spec["model"]`. The model comes from
`CodingAgentConfig.model` (`:91`), i.e. the config's `model:` key (yaml default
`gpt-4o-mini`); an `agent_specific.model` would be silently ignored.

Registry presence ≠ runnable: in the A0 venv `aider` fails to import and `gemini`/`openhands`
build only if their SDKs are installed; `claude_code`, `codex`, `oss_claude_code`,
`openai_compatible` construct (the last two given dummy credentials). Log:
`logs/lane_construct.log`.

Two doc-vs-code defects found while reading (not blockers, but they mislead a swap decision):

* `agents.yaml:180` says *"OPENAI_API_KEY is deliberately stripped from the child
  environment"* — true of the ideation runner (`codex_ideation.py:117`), **false of the
  adapter**: `CodexCodingAgent._run_session` starts from `os.environ.copy()` and only strips
  names in `env_strip` (`codex_agent.py:230-241`).
* `agents.yaml:128` / `docs/evolve/coding-agents.mdx:153` advertise OpenHands as a
  "sandboxed execution environment". The adapter is a bare `LLM.completion` call and reports
  `"sandbox": False  # Simplified version without Docker` (`openhands_agent.py:281`);
  `agent_name` / `max_iterations` from the yaml are never read.

## 3. What `oss_claude_code` actually is (do not guess from the name)

It is the **closed-source Claude Code CLI run against an Anthropic-compatible endpoint** —
open *model*, closed *CLI*. `OssClaudeCodeCodingAgent` subclasses `ClaudeCodeCodingAgent` and
changes only authentication (`oss_claude_code_agent.py:1-6,55-116`): it still requires
`shutil.which("claude")` (`:83`), still launches `claude -p --dangerously-skip-permissions …`,
still has no sandbox. `core/preflight.py:52-57` maps `oss_claude_code → "claude"`, i.e. KAPSO
itself treats it as the same binary requirement.

So: choosing `oss_claude_code` removes the **Anthropic account/serving dependency**, not the
**closed-CLI dependency**. For this audit's question it is a non-answer. (It also cannot serve
`WebSearch`: the ideation ensemble drops that tool for oss members,
`search_strategies/generic/ideation.py:527-535`.)

## 4. Mandatory paths — where a closed CLI is hardcoded

Verified by reading; each row is a site that no config key can redirect.

| site | what is fixed |
|---|---|
| `agents.yaml:28` | `default_agent: claude_code` — what `build_config()` picks when no agent is named (`factory.py:173`) |
| `config.yaml:73-74`, `:141-152`, `:203-214` | packaged `deployment.coding_agent`, and both shipped modes' `coding_agent` + `feedback_generator` are `claude_code` |
| `config.yaml:31` | `inference.default.cli: codex` |
| `strategy.py:345-352` | `implementation_cli` **validated** to be `claude_code` or `codex` — raises otherwise |
| `implementation.py:207,236` | implementation builds only `codex` or `claude_code` configs; the non-codex branch hard-instantiates `ClaudeCodeCodingAgent` (`:298`) |
| `ideation.py:320`, `:557`, `:108` + `codex_ideation.py:63` | single-session ideation is `claude_code`; ensemble members are limited to `{claude_code, codex, oss_claude_code}` and the codex member runs `codex` directly |
| `lens_planning.py:220` | lens/design-axes planner is `claude_code` |
| `difficulties_generator.py:60` | technical-difficulties fallback session is `claude_code` |
| `feedback_generator.py:95-102` | the judge defaults to `claude_code` when no config block is given |
| `knowledge_merger.py:445`, `repo_ingestor/__init__.py:193`, `research_ingestor/base.py:127` | the whole `learn()` knowledge pipeline is `claude_code` |
| `researcher/researcher.py:73` + `config.yaml:38` | web research runs through `CliInference` role `research`; `cli_inference.py:116-121` **refuses** `openai_compatible` for any web-search role |
| `experiment_session.py:204` | the repo-memory MCP gate is mounted only for `agent_type == "claude_code"` |
| `orchestrator.py:397-409,446,459,465,588` | fallback defaults `claude_code` / `aider` when a config block is absent |
| `preflight.py:211-222` (`resolve_cli`) | when a config block names no `cli`/`type`, the CLI is resolved from the **model name prefix** — `claude-*` → `claude_code`, everything else → `codex`. So `config.yaml:168,176,226,234` (learner ingestor/merger `model: "claude-opus-5"`) resolve to the closed CLI by name alone |

Config-selectable (no source change): `feedback_generator.type`,
`evaluation_maintainer.type` (`orchestrator.py:585-590`), `coding_agent.type`
(`orchestrator.py:459-472`), `inference.default.cli` + per-role `cli`, and the ideation
ensemble member `cli`. Everything in the table above is not.

## 5. Parity risk — what a swap silently changes

The lanes are not equivalent; KAPSO's own code depends on the following, and only
`claude_code`/`codex` provide them.

| capability KAPSO relies on | claude_code | codex | the four "open" lanes |
|---|---|---|---|
| **patch/apply semantics** | Edit/Write tools | apply_patch in sandbox | gemini/openhands **parse ```filename fences from model text and overwrite whole files** (`gemini_agent.py:179-236`, `openhands_agent.py:178-233`); `openai_compatible` edits nothing ever (`:86,142-145`) |
| **shell/Bash tool** | yes (gates, evaluations) | yes | **none** |
| **sandbox / egress control** | none (`capabilities.sandbox=False`, `claude_code_agent.py:1331`) | `agent_specific.sandbox`, default `danger-full-access` (`codex_agent.py:117`) — the only lane with a real closure knob (closure workstream measured it) | none; `openai_compatible` is closed only because it has no tools at all |
| **session resume / inbox continuation** | `--resume` / `--session-id` (`:1179-1190`) | `exec resume <thread>` + `--json` thread capture (`codex_agent.py:166-181,206-207`) | `CodingAgentInterface.resume` raises `NotImplementedError` (`base.py:145-168`), and `implementation.py:307` calls it whenever a suspended node is continued |
| **prompt delivery** | stdin (`claude_code_agent.py:613-615`) | stdin (`codex_agent.py:275`) | in-process argument |
| **registered evaluation (score of record)** | the session runs `python kapso_evaluation/kapso_eval.py --fidelity … --fraction … --seed …` and prints `KAPSO_EVAL_MANIFEST`; KAPSO reads **the session's own output** (`registered_evaluation.py:72`, `evaluation_instructions` `:296-320`, `strategy.py:624,657`) | same | **impossible**: no shell, so no in-session manifest. Only KAPSO's own frame runs (`execute_registered_evaluation`, `:162-285`) could score a node — and those fire only for VALIDATE/bridge grants, i.e. not at all under the frozen `budget.fidelity.mode: off` |
| **MCP gates** (research, repo_memory, leeroopedia) | yes (23 refs in the adapter) | yes, translated to `-c mcp_servers.*` (`codex_agent.py:48-72`) | **zero MCP support in all four** (`grep -c mcp`: 0 in each) |
| **live web** (research role) | yes (WebSearch/WebFetch) | yes (`--search`) | none; `openai_compatible` is refused outright for web roles |
| **cost telemetry** | estimated from output length (`:1295`) | always 0 (`codex_agent.py:358`) | gemini/openhands estimate; openai_compatible returns real usage tokens but `cost_tracking: False` |

Concretely: swapping implementation to any open lane would (a) stop evaluating candidates —
no manifest line means `manifest_of_record` returns `None` and `node.score` stays `None`, so
nothing is ever selectable; (b) overwrite whole files from regex-parsed fences instead of
patching; (c) break the inbox continuation; (d) silently drop the repo-memory gate. A swap of
the *judge* to `gemini`/`openhands` is additionally hazardous: those adapters write any fenced
block in the model's answer into the workspace they are initialized with
(`feedback_generator.py:155` initializes the agent at `workspace_dir`), so a judge can mutate
the candidate it is judging.

## 6. Recommended paths and their cost

**Path A — config-only, one closed CLI remains (cost: one config block, no source edits).**
Point the text-only inference roles at `openai_compatible` with a loopback server:

```yaml
inference:
  default:   # or per-role overrides
    cli: openai_compatible
    model: <your local model id>
    agent_specific:
      base_url: http://127.0.0.1:8000/v1
      api_key_env: LOCAL_KEY
      allow_missing_api_key: true
```
Keep `research` on a web-capable CLI (the code refuses otherwise). Verified against
`cli_inference.py:89-135` and `core/preflight.py:340-362`. This removes `codex` from the
*inference* layer but leaves ideation/implementation/judge on `claude_code` — so it does not
answer the user's question, it only shrinks the footprint.

**Path B — zero closed CLI (cost: source patches + a lost channel).**
1. Patch the hardcoded sites in §4 (realistically: replace the `agent_type=` literals with
   config lookups, extend `strategy.py:348`'s whitelist, and give the feedback/maintainer
   blocks a lane).
2. Add at least one shell-capable open lane, otherwise no candidate is ever evaluated under
   `fidelity.mode: off`. Nothing in the registry today qualifies: `gemini`/`openhands`/
   `openai_compatible` have no tools; `aider` has no shell tool in KAPSO's adapter and is not
   even installable on the 3.13+ default. A new adapter must supply, at minimum:
   prompt-on-stdin, a deadline kill that spares the evaluation's children (the pattern in
   `codex_agent.py:312-322`), a stream artifact, patch semantics, and a way to run
   `python kapso_evaluation/kapso_eval.py …` from inside the session.
3. Accept the losses: session resume/inbox (raises), MCP gates, native web search, and the
   closure knob (no open lane has a sandbox parameter).
   Expected extra work: one new adapter (the template, `adapters/TEMPLATE.py`, is 308 lines
   and the interface is 5 methods) plus ~10 small site edits.

**Not recommended:** `oss_claude_code` as a substitute — it keeps the closed CLI (§3).

## 7. Blockers, uncertainty, and what would invalidate the conclusion

* **Could not verify**: the licences of `aider-chat`, `openhands-ai` and `google-genai`
  (not installed on this host; PyPI fetch refused from this environment). Only `openai` and
  `litellm` licences are host-verified. Treat the open-source claim for those three as
  unverified-by-execution.
* **Could not verify**: whether `aider`/`openhands`/`gemini` can be aimed at a self-hosted
  OpenAI-compatible endpoint. KAPSO passes no endpoint for them; any such ability would come
  from ambient env vars read by litellm/genai, which I could not test without installing.
* **Not exercised**: no KAPSO campaign was run (no model calls allowed), so the parity claims
  in §5 are source-level, not observed. The closure workstream reached the same conclusion by
  execution for the codex/claude lanes (`a0/closure/VERDICTS.md` §1).
* **Would invalidate §4** if the runtime is configured with a *different* search strategy
  (`kg_graph_search`, `kg_llm_navigation` in `config.yaml:161-234` were not audited for their
  own agent sites beyond the shared knowledge-base ingestors), or if a future KAPSO version
  makes `implementation_cli` free-form.
* The plan's §3.3 row for KAPSO ("E2E example depends on codex and claude CLI") is confirmed
  and sharpened: the dependency is not only in the example script — it is in the strategy,
  the judge, the maintainer, the knowledge pipeline and the researcher role.

## 8. Verification log

```
# registry + construction probe (no model call, no file edits)
cd /home/ebt/rsi-dev/a0/runtimes/kapso
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/ebt/kapso_ck/kapso/src:. \
  A0_PROBE_TOKEN=dummy OPENAI_API_KEY=dummy .venv/bin/python \
  /home/ebt/rsi-dev/a0/notes/exit-closed/kapso/probe_lane_construct.py
```
→ `logs/lane_construct.log`: registry `['claude_code','codex','gemini','openai_compatible',
'openhands','oss_claude_code']` (no `aider`), `default = claude_code`; `claude_code`,
`codex`, `oss_claude_code`, `openai_compatible` construct; `aider`/`gemini`/`openhands` fail
for missing packages.

Reading evidence is cited inline as `path:line` (paths are relative to
`/home/ebt/kapso_ck/kapso/src/kapso` unless they name a file in this repo).
