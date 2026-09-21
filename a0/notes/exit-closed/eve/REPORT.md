# EvE — is there a non-codex agent lane, and what would removing codex cost?

Audit date 2026-09-21. Read-only on every source; writes confined to this directory.
No model calls, no installs. Verdict: **the codex dependency is removable by
configuration — EvE needs no new driver.**

## 0. Provenance (established from evidence, not a guess)

| fact | evidence |
| --- | --- |
| EvE repo = `https://github.com/scaling-group/eve`, Apache-2.0, pin `979065fd` | protocol §3.3.2 (`open_world_plan_review.typ:396`): "EvE（快照 `979065fd`，Apache-2.0）… `scaling-group/eve`" |
| full pin = `979065fd2cf1b3be9caf70596478fe27df7815ad` | `a0/acceptance/DERIVATIONS.md:18`, `a0/runtimes/eve/README.md:4`, `a0/verify/VERDICT.md:307` |
| the pin is the repo's HEAD → URL+commit pair is unambiguous | `git ls-remote https://github.com/scaling-group/eve HEAD` → `979065fd2cf1b3be9caf70596478fe27df7815ad` |
| **not** to be confused with the seed task repo | `a0/runtimes/eve/DECLARATIONS.md:59` — `(https://github.com/scaling-group/evolve-testbed, 6ac22c440e241b7e19d89fff91cc4f9841cc951d)` |

Re-clone (the reboot wiped `/tmp`, which is the accepted convention here):

```
git clone --no-checkout https://github.com/scaling-group/eve /tmp/eve
cd /tmp/eve && git checkout 979065fd2cf1b3be9caf70596478fe27df7815ad
git -C /tmp/eve status --porcelain     # empty → pristine, before and after this audit
```

## 1. Agent-layer inventory (all citations from `/tmp/eve` @ `979065fd`)

`src/scaling_evolve/providers/` holds exactly one provider package, `agent/`. There is
**no** `providers/agent/codex_exec.py` / `codex_tmux.py` — the drivers live one level down
in `providers/agent/drivers/`. Registered set is hard-coded at
`algorithms/eve/runtime/driver.py:24`: `_SUPPORTED_DRIVER_NAMES = ("codex_exec", "codex_tmux", "opencode")`
(registry also in `providers/agent/drivers/__init__.py`).

| lane (file) | external binary | argv the driver builds | OSS? | is it an agent lane? |
| --- | --- | --- | --- | --- |
| `drivers/codex_exec.py:76` | `codex` (default, `:83`) | `codex exec <prompt> --dangerously-bypass-approvals-and-sandbox --json -C <wt> -m <model> -c …` (`:423-441`, flag at `:434`) | CLI is Apache-2.0 (`api.github.com/repos/openai/codex` → `Apache-2.0`), but it is a client to a proprietary hosted service | yes — shipped default |
| `drivers/codex_tmux.py:178` | `codex` (`:187`) | `codex --no-alt-screen -a never -s workspace-write -C <wt> …` | as above | yes — interactive/tmux |
| `drivers/opencode.py:89` | `opencode` (default, `:95`) | `opencode run --format json --auto --dir <wt> --agent build --thinking [--session <id>] [--model p/m] <prompt>` (`:398-419`) | **MIT, `anomalyco/opencode`** — "The open source coding agent" (`api.github.com/repositories/975734319`) | **yes — a full non-codex lane** |
| `python_runtime.py:1,342` | none | writes `.agent-runtime/` python wrapper + `sitecustomize` + `python_policy.json` into the workspace | in-repo | **no — code-execution hardening, not a lane.** Imported only by `providers/agent/backend.py:39,439` (`AgentProvider`, `:78`), and the Eve algorithm does not use `AgentProvider` (`algorithms/eve/factory.py:22`: "role-specific session drivers (spawn() only — no AgentProvider, no session store)") |
| `codex_isolation.py` | none | renders the isolated Codex HOME / trust shim | in-repo | no — Codex-only helper, imported by both codex drivers (`codex_exec.py:18`, `codex_tmux.py:17`) |
| `drivers/opencode.py` — driver body | — | — | — | the lane is wired into the loop, not vestigial: `workspace/runtime_hooks.py:23` branches on `isinstance(driver, OpenCodeSessionDriver)` to project helper agents + skills |

`opencode` is a **first-class public preset**, not an experiment:

* `configs/eve/driver/opencode_max.yaml:6` (`driver: opencode`, `:12` timeout 7200) and
  `opencode_smoke.yaml:5`.
* `docs/skills/configure-eve-driver/SKILL.md:110` — "Supported backend names are
  `codex_exec`, `codex_tmux`, and `opencode`"; `:12`/`:45` give the runnable commands,
  including `--config-name=circle_packing driver=opencode_max driver.model=deepseek/deepseek-chat`.
* `README.md:63-71` — "**Codex** is the default backend… **OpenCode** supports either
  credentials saved by `opencode auth login` or an API key declared through
  `driver.model_providers.<provider>.env_key`."
* the switch is exercised by upstream tests: `tests/test_eve_opencode_config.py:26,57,74`.

**Caveat on the audit trail.** Neither the protocol §3.3.2 capability table nor our own
`a0/runtimes/eve/DECLARATIONS.md` §6 mentions `opencode` at all: `grep -n opencode` on the
protocol returns nothing, and DECLARATIONS enumerates only the two codex drivers
(`:199-205`) before concluding that closure-by-config is impossible. That conclusion is true
for `codex_exec` but was never checked against the third lane.

## 2. Execution probe (run this session; no model call, no CLI launched)

`probe_drivers.py` in this directory, run as
`cd /tmp/eve && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/eve/src <adapter venv>/python probe_drivers.py`:

```
codex_max:    keys=['budget_prompt','driver','executable','model','reasoning_effort','rollout_max_turns','timeout_seconds','web_search'] solver=CodexExecSessionDriver eval=CodexExecSessionDriver
opencode_max: keys=['budget_prompt','driver','executable','model','rollout_max_turns','timeout_seconds','variant'] solver=OpenCodeSessionDriver eval=OpenCodeSessionDriver
opencode + codex-style provider block -> SystemExit: opencode does not support Codex-specific options: `driver.model_provider`.
```

So `driver=opencode_max` composes cleanly and `build_role_drivers`
(`algorithms/eve/runtime/driver.py:114-155`) returns an `OpenCodeSessionDriver` for **both**
roles with **zero code changes**. `git status --porcelain` in `/tmp/eve` was empty before and
after (ran with `PYTHONDONTWRITEBYTECODE=1`).

## 3. Verdict: no new driver is required

The `SessionDriver` surface a replacement must satisfy is
`providers/agent/drivers/base.py:97-143` (`capabilities`, `spawn`, `fork_session`,
`migrate_session`, `fork`, `resume`, `snapshot`). But the Eve loop only ever calls `spawn`
and `resume`:

* `workflow/phase2.py:177` (`self.driver.spawn(...)`) and `:206` (`self.driver.resume(...)`,
  the boundary-repair path) — the only two call sites in the algorithm;
* `workflow/phase3.py` has no driver reference at all (pure-Python Elo scoring);
* `fork_session` / `migrate_session` are called only from `providers/agent/backend.py:789,811`
  (`AgentProvider`), which `factory.py:22` explicitly does not use;
* `snapshot` is called nowhere in `algorithms/eve/`.

And the unsupported surface is identical across all three drivers — `codex_exec.py:155,159,163,198`,
`codex_tmux.py:273,277,281,316`, `opencode.py:165,169,173,196` all raise
`NotImplementedError` for fork/migrate/snapshot. **`opencode` is therefore feature-equal to the
shipped default for every operation EvE performs**; it is not a downgrade.

**Files to add inside EvE: none. Lines of EvE code to change: none.** The switch is one
Hydra override.

## 4. What removing codex actually costs

Two separable dependencies are being conflated. The codex **CLI** is open source
(`openai/codex`, Apache-2.0) — the closed part is the hosted OpenAI account/service, and
even that is already bypassed in our runs by pointing codex at a local relay via
`driver.model_provider` + `driver.model_providers.*` → `-c model_providers.<id>.<key>=…`
(`codex_exec.py:445-476`). So if the goal is "no closed *service*", nothing more is owed.
If the goal is "no codex binary at all", the table below is the cost.

| item | work | evidence |
| --- | --- | --- |
| EvE code | none — `driver=opencode_max` | executed, §2 |
| CLI install + auth | install `opencode` (MIT) and `opencode auth login`, or supply `driver.model_providers.<provider>.env_key` | `SKILL.md:115`; **`opencode` is not installed on this host** (`which opencode` → not found; `codex`/`claude` are at `/usr/bin`) |
| version pin | EvE pins no `opencode` version (`grep opencode uv.lock pyproject.toml docs/` → only the driver/config/test references) — we must record the version ourselves for A1 reproducibility | negative grep |
| our adapter (`a0/runtimes/eve/`) | one override added in `a0_adapter/eve_runtime.py:222-224` and the stale label at `:365` (`configs/eve/driver/codex_max.yaml`); a new opencode analogue of `tools/run_one_eve_iteration.py:97-160` `codex_provider_overrides` (the codex form is rejected by the opencode lane — see the `SystemExit` in §2); `a0_adapter/closure.py:42-99` probes the codex argv only | cited lines |
| the eval/judge lane | not a cost: our adapter already disables it (`eve_runtime.py:333-346`, `_no_driver`) because A0 freezes a shell-step plan; `evaluation.steps` runs `bash` via `subprocess.Popen` and needs no CLI | `DECLARATIONS.md:44-52` |
| closure | **the real cost.** `opencode.py` contains *zero* occurrences of `sandbox` and *zero* of `permission` (`grep -c` → `0`,`0`). The lane cannot be closed by a driver knob, so it needs external isolation (the `unshare-rn` mechanism we already use for the E* lane) or opencode's own `permission` config | `grep -c` on `/tmp/eve/src/scaling_evolve/providers/agent/drivers/opencode.py` |
| closure, alternate route | opencode's config *is* injectable: `driver.py:434-441` folds `model_providers.*.env_key` into `provider_env`, and `opencode.py:437-462` parses `OPENCODE_CONFIG_CONTENT` from that env and merges it — so `model_providers.<id>.env_key=OPENCODE_CONFIG_CONTENT` would carry an arbitrary opencode config (custom `provider` with `baseURL`, `permission` block). **Read from source, not executed** — and it is a hack: it abuses an env-key slot for a config payload | cited lines; label as unverified |

Bottom line: to drop codex, EvE needs **no new driver** — one config override, plus our own
adapter/closure/trace work. The honest cost is not in EvE at all; it is the *unverified
closure posture* of the opencode lane and the fact that our adapter's codex-specific relay
injection does not translate (codex addresses the endpoint through `-c model_providers…`;
opencode addresses it through its own provider config, and EvE fails fast on the codex form).

## 5. Blockers and what would invalidate this

1. **Closure parity is unresolved, and it is the same weakness we already have.**
   `codex_exec` (the shipped default) cannot be closed by configuration either — no sandbox
   parameter, hardcoded `--dangerously-bypass-approvals-and-sandbox` (`codex_exec.py:434`,
   `DECLARATIONS.md:199-205`). Only `codex_tmux` is config-closable. So switching to
   `opencode` does not lose a property the study currently has; it also does not gain one.
   If A1 demands *config-level* closure, the only lane that offers it today is `codex_tmux`
   — i.e. codex again, or a new probe on the opencode `permission` block.
2. **Nothing about the opencode lane has been executed with a real binary here** — this is a
   source-and-host audit. Unverified: whether `opencode --auto` needs a TTY, whether its
   JSON stream parses on the version we would install, and whether a self-hosted
   OpenAI-compatible endpoint works through EvE's env-key-only provider path. Label these as
   guesses; all need one smoke run (and a model budget) after A1 unfreezes.
3. **Reproducibility of the A0 evidence.** Our real-iteration evidence (`out/run002-004`,
   `tools/run_one_eve_iteration.py:11`) is codex-only. Any post-switch comparison would use a
   different *agent*, which changes $A_t$ — this is a substrate change to be declared, not a
   drop-in replacement.
4. **Invalidation risk:** if the opencode CLI's `--auto` turns out to grant network/shell
   with no reachable restriction, an A1 run on it would be open by default, exactly like
   `codex_exec` — the study would then need external isolation (verified for the E* lane,
   `DECLARATIONS.md:214-220`) or an accept-and-declare posture.
5. **Correction to the framing, independent of the above:** calling codex a "closed-source
   CLI" is inaccurate — `openai/codex` is Apache-2.0. Claude Code's repo
   (`anthropics/claude-code`) reports no license at all, so *that* one is closed. EvE's
   dependency is a codex binary + a hosted account, and the account half is already removed
   in our setup.
