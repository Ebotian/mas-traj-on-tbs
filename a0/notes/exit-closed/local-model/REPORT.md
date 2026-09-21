# The model layer — what must replace the closed CLIs, and can this host serve it

Owner: `a0/notes/exit-closed/local-model/**`. Date of all measurements: 2026-09-21 (CST, UTC+8).
Scope: the *model transport* only. The CLI-level question (which binary, which licence, which
backend knob) is owned by the sibling reports `a0/notes/exit-closed/{kapso,eve,loreley}/REPORT.md`;
where they overlap I cross-reference instead of repeating.

Method: read the runtimes' sources at the pinned commits, read the shipped `codex` 0.154.0 binary
and its published config reference, and measure the host. **No model call, no install, no service
started.** Raw output: `evidence/host_caps.txt`, `evidence/codex_and_netns.txt`.

---

## 0. Bottom line

**The closed CLIs are replaceable. The model is not — not on this host, not at a quality that
keeps A1 meaningful.**

* Every open lane the sources expose (`opencode`, `kilo`, `aider`, `openhands`,
  `openai_compatible`) speaks an open protocol that a self-hosted server can serve. Removing the
  *CLI* dependency is a config-and-install job with no code change and no study-level cost.
* **The concrete trap is resolved and it is worse than "most servers implement Chat Completions".**
  `codex` 0.154.0 supports the Responses API **only** — `wire_api = "chat"` is rejected outright —
  so the candidate server must implement `POST /v1/responses`, not `/v1/chat/completions`.
  Chat-Completions-only servers (the entire vLLM/llama.cpp/TGI default surface) cannot back codex
  *at all*.
* **The host ceiling is the real blocker.** The only GPU is an **RTX 3050 with 6 GB VRAM, 4.6 GB of
  it free**. That fits a 4–8B Q4 model in full; anything with real agentic competence (20–30B MoE)
  must be CPU-offloaded to ~5–15 tok/s on a 6-core Ryzen. The study's own protocol calls are
  18–20k input tokens each, and EvE's rollout budget is `rollout_max_turns: 10000`,
  `timeout_seconds: 7200`.
* **A1 risk: high, and it is a false-negative risk.** A−1 and A0 stay valid (they are
  model-independent). A1 asks whether a substrate improves algorithms; if a 4–8B local model drives
  the lane, the substrate can look inert for reasons that have nothing to do with the substrate. I
  would not run A1 on a host-local model without a pre-registered positive control (§3.3).
* **Closure win is real and cheap to realise**, but the shape matters: the model and the agent CLI
  must sit in **one namespace that has no default route**, with the model on that namespace's own
  loopback. `unshare -rn` does this rootlessly, keeps the GPU, and is verified on this host
  (§4). Docker `--internal` cannot be used for a GPU model server here (no NVIDIA Container
  Toolkit) and — the counter-intuitive part — is not even needed.

Cleanest full-exit candidate: **`llama-server` (MIT)**, because it is the only server I found that
implements all three protocols the four runtimes need on one port — `/v1/responses` (codex),
`/v1/messages` + `/v1/messages/count_tokens` (claude), `/v1/chat/completions` (everything else)
(`evidence` §1.3). `ollama` covers codex and the Chat-Completions lanes but **not** claude.

---

## 1. Required API surface, per lane

Legend for the last column: "local?" = can a self-hosted open-weights server back this lane.

| Runtime | Lane (and how it is selected) | Transport it actually speaks | Needs | local? |
|---|---|---|---|---|
| **KAPSO** | `codex` — the **default for every non-embedding completion** (`inference.default.cli: codex`, `src/kapso/config.yaml:31`), via `CliInference` (`core/cli_inference.py:103-151`) | codex CLI → provider wire API | **Responses API only**, SSE streaming, tool/function calling, `model_reasoning_effort` | **Yes**, iff the server serves `POST /v1/responses` |
| **KAPSO** | `claude_code` — the **write/ideation lane** for `GENERIC` (`config.yaml:141-144`, `coding_agent.type: "claude_code"`) | claude CLI (`--dangerously-skip-permissions`, no sandbox) | Anthropic **Messages** API | **Yes**, iff the server serves `POST /v1/messages` |
| **KAPSO** | `oss_claude_code` — the documented swap-in for the lane above (`adapters/oss_claude_code_agent.py:98-110`) | claude CLI with `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`, first-party creds stripped | Anthropic Messages API | **Yes** — same requirement, and this adapter is the sanctioned seam |
| **KAPSO** | `openai_compatible` (`agents.yaml:149-168`) | `openai` SDK `chat.completions.create` (`adapters/openai_compatible_agent.py:116`) | **Chat Completions**, no streaming, **no tools** (`:39-59` rejects `tools`; `:131-134` errors on `tool_calls`) | Yes, trivially — but it is `inference_only: true` (`agents.yaml:154`), so it **can never carry a write/agentic lane** |
| **KAPSO** | `aider` (optional extra) | aider lib → litellm | Chat Completions + tools | Yes; cost = Python **<3.13** (`pyproject.toml:58-65`; host has 3.14.7) |
| **KAPSO** | `openhands` (`adapters/openhands_agent.py:59-69`) | `openhands.llm.LLM` → litellm | Chat Completions; single-shot text + code-block parsing (no sandbox, no tools) | Yes |
| **KAPSO** | `gemini` (`adapters/gemini_agent.py:61-67`) | `google-genai` SDK | Vertex/Gemini vendor API | **No** — vendor SDK, no base-url seam |
| **EvE** | `codex_exec` — the **shipped full-run driver** (`configs/eve/driver/codex_max.yaml:6`, selected by `configs/eve/circle_packing.yaml:6`) | codex CLI | Responses API | **Yes**, config-only: `driver.model_provider` + `driver.model_providers.<id>.{base_url,wire_api,env_key}` (`drivers/codex_exec.py:419-471`) |
| **EvE** | `codex_tmux` (`configs/eve/driver/codex_smoke.yaml`; the lane `a0/closure` measured) | codex CLI in tmux | Responses API | **Yes**, same injection (`drivers/codex_tmux.py:596-606`) |
| **EvE** | `opencode` — a **first-class public preset** (`configs/eve/driver/opencode_max.yaml:6`) | opencode CLI (MIT), `opencode run --format json --auto --dir <wt> --agent build --thinking` (`drivers/opencode.py:405-424`) | opencode's own provider config; Chat Completions **or** Responses, injectable via `OPENCODE_CONFIG_CONTENT` (`:504`) | **Yes** — best open lane, but it **rejects every sandbox knob** (`driver.py:272-300`), so it has no in-lane closure. See `a0/notes/exit-closed/eve/REPORT.md:113` |
| **Loreley** | `kilocode_cli` — the **default for planning, coding and seed-portfolio** (`config.py:467-473`, `:418-421`) | kilo CLI (MIT, verified `Kilo-Org/kilocode` LICENSE) | provider config with `baseURL` + `apiKey`; npm `@ai-sdk/openai-compatible` for Chat Completions, `@ai-sdk/openai` for Responses (`backends/kilocode_cli.py:1214-1218`) | **Yes**, config-only: `WORKER_KILOCODE_OPENAI_BASE_URL`, `WORKER_KILOCODE_OPENAI_API_SPEC=chat_completions`, `WORKER_KILOCODE_OPENAI_API_KEY` (`config.py:533-545`) |
| **Loreley** | `codex_cli` | codex CLI | Responses API | **Yes**, but must first defeat the backend's `CODEX_HOME` isolation — the isolated home writes a thin `config.toml` with **no `model_providers` block** (`backends/codex_cli.py:243-270`), so the provider route is discarded. Workaround already proven by a sibling workstream: `WORKER_*_EXTRA_ENV={"CODEX_HOME":"~/.codex"}`, which also *disables* isolation (`codex_cli.py:252`). See `a0/runtimes/loreley/VERIFICATION.md:500` |
| **Loreley** | `cursor_cli` (`backends/cursor_cli.py`) | `cursor-agent` CLI | — | **No** — closed, no seam. Drop it. |
| **SimpleLoop** | `CliSolver` `codex` branch — the **shipped, CLOSED** lane (`solvers.py:280-281`) | codex CLI | Responses API | **Yes**, but the solver passes **no `-c` at all** (`solvers.py:280-281`), so the only levers are the ambient `~/.codex/config.toml` or a parent-env `CODEX_HOME` |
| **SimpleLoop** | `CliSolver` `claude` branch (`solvers.py:282-285`) | claude CLI | Anthropic Messages API | Yes, via parent-env `ANTHROPIC_BASE_URL` (the solver inherits the env — `Popen` with no `env=`) |

### 1.1 The trap, resolved: codex 0.154.0 is **Responses-only**

Two independent sources, both unambiguous:

* **The vendor's own configuration reference** (`developers.openai.com/codex/config-reference`):
  `model_providers.<id>.wire_api` → *"responses — Protocol used by the provider. **responses is the
  only supported value**, and it is the default when omitted."*
* **The shipped binary's own strings** (`strings -n 6 /usr/bin/codex`):
  ```
  `wire_api = "chat"` is no longer supported.
  How to fix: set `wire_api = "responses"` in your provider config.
  `ollama-chat` is no longer supported.
  How to fix: replace `ollama-chat` with `ollama` in `model_provider`, `oss_provider`, or `--local-provider`.
  ```
  and the only request path present in the binary is `/responses` — there is **no**
  `/chat/completions` request path at all (`grep -oE '/chat/completions'` → 0 hits).

So **there is no chat-completions setting to find**. The answer to "does a chat-completions setting
exist?" is **no**, and this determines the whole design: a self-hosted server must expose the
**Responses** API to back codex. This is the fact that decides whether a local model server can
back codex at all — and for several servers, it can.

**Correction to a sibling finding.** `a0/notes/exit-closed/kapso/REPORT.md:46` records KAPSO's
codex lane as local-model-incapable ("no — Responses API + ChatGPT/auth path"). The protocol read
is right; the implication is not. Codex **can** be backed by a local model, by declaring a custom
provider:

```toml
model_provider = "local"
[model_providers.local]
base_url   = "http://127.0.0.1:11434/v1"   # or :8080/v1 for llama-server
wire_api   = "responses"                    # the only accepted value
env_key    = "LOCAL_API_KEY"                # or requires_openai_auth = false
```

This host's own `~/.codex/config.toml` already demonstrates the shape
(`[model_providers.custom] wire_api = "responses"`, `evidence/codex_and_netns.txt`), and it already
carries `disable_response_storage = true` — which is exactly the setting needed for the *stateless*
Responses implementations that ollama and llama-server provide.

### 1.2 Which servers can serve the Responses API

| Server | `/v1/responses` | `/v1/messages` (claude) | `/v1/chat/completions` | licence | note |
|---|---|---|---|---|---|
| **llama.cpp `llama-server`** | **yes**, and `/v1/responses/input_tokens` | **yes**, `/v1/messages` + `/v1/messages/count_tokens`; tools need `--jinja` | yes | MIT | the only one covering all three lanes. Its README states the Responses endpoint *"works by converting Responses request into Chat Completions request"*, and makes *"no strong claims of compatibility"* for Messages — **probe before relying on it** |
| **ollama** | **yes**, `POST /v1/responses` since **v0.13.3** — streaming + tools; explicitly **non-stateful** (no `previous_response_id`) | **no** | yes | MIT | one binary covers codex + all Chat-Completions lanes; claude needs a shim |
| vLLM | not verified | no | yes | Apache-2.0 | docs page did not resolve offline; **unverified** |
| LM Studio | codex has a **native, non-OpenAI client** for it (`lmstudio/src/client.rs` in the binary; "Local LM Studio server (default port 1234)") | no | yes | closed app | only reachable via `--oss --local-provider lmstudio` |

Sources for this table (external doc reads, used because the offline audit cannot resolve
protocol support from source): [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility),
[llama.cpp server README](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md).

### 1.3 The `--oss` escape hatch exists but **no runtime uses it**

`codex exec` accepts:
```
--oss                      Use open-source provider
--local-provider <OSS_PROVIDER>   Specify which local provider to use (lmstudio or ollama)
```
and `oss_provider: lmstudio | ollama` is a config key. **Not one of the four runtimes ever emits
`--oss`**: KAPSO builds its argv at `adapters/codex_agent.py:183-208`, EvE at
`drivers/codex_exec.py:440-471`, Loreley at `backends/codex_cli.py:146-178`, SimpleLoop at
`solvers.py:280-281`. So the local-model route for codex is **the custom-provider block**, not the
built-in OSS toggle. That is not a blocker — it is config in three of the four lanes and a
parent-env `CODEX_HOME` in the fourth.

### 1.4 One lane that a local model cannot serve at all

KAPSO's **`research` role** requires live web search. `CliInference._run_session` raises if that
role is routed to `openai_compatible` (`core/cli_inference.py:116-121`), and `preflight` emits a
hard-failing requirement for the same combination (`core/preflight.py:500-511`). A local model has
no web. **`research()` is therefore out of scope of any local-model configuration** — it needs
either a closed web-capable CLI or a separate sanctioned search tool.

---

## 2. Host capability (read-only; `evidence/host_caps.txt`)

| Probe | Command | Observed |
|---|---|---|
| GPU | `nvidia-smi --query-gpu=… --format=csv` | `NVIDIA GeForce RTX 3050, 6144 MiB total, 1052 MiB used, 4784 MiB free, compute_cap 8.6, driver 615.71.09` |
| Second GPU | `lspci \| grep -i vga` | AMD/ATI Granite Ridge **integrated Radeon** (APU iGPU, shares system RAM); `rocm-smi` sees it, ROCm 7.2.4 installed |
| RAM | `free -h` | 30 GiB total, **25 GiB available** |
| CPU | `lscpu` | Ryzen 5 9600X, 6 cores / 12 threads |
| Disk | `df -h /` | 135 GB free on `/` |
| Python | `python3 --version` | **3.14.7** (with `uv 0.12.13` available to pin 3.11/3.12) |
| Model servers | `command -v ollama vllm llama-server text-generation-launcher` | **all MISSING** |
| Open CLIs | `command -v kilo opencode aider cursor-agent` | **all MISSING** (`codex`, `claude` present at `/usr/bin`) |
| Anything listening | `ss -ltn` | `127.0.0.1:9093`, `127.0.0.1:33739`, `127.0.0.1:5433` (postgres), `*:7890`/`*:7891` (proxy), `*:1053` (dns). **No model endpoint.** |
| Docker GPU | `docker info --format '{{json .Runtimes}}'`; `ls /usr/bin/nvidia-ctk` | runtimes are **`runc` only**; `nvidia-ctk` and `nvidia-container-runtime` **absent** → **no GPU inside containers** |
| Docker daemon proxy | `/etc/docker/daemon.json` | `http-proxy = http://127.0.0.1:7890`, `no-proxy = localhost,127.0.0.1` |
| codex relay | `curl --noproxy '*' http://127.0.0.1:15722/v1/models` | **`http=000` (connection refused)** — see §2.1 |
| Install candidates | `pacman -Ss '^ollama\|^llama-cpp'` | `extra/ollama-cuda 0.34.0-1`, `extra/ollama-rocm`, `extra/llama-cpp 0.4.0-2` (**CPU-only**: deps are `ggml glibc libgcc libstdc++ openssl`) |

Also relevant and already on record: `/tmp` is a **16 GiB tmpfs backed by RAM**
(`a0/env/checks/ENV_REPORT.md:549`, `:565`). Weights staged there consume the same RAM the model
needs for CPU offload — do not stage GGUFs in `/tmp`.

### 2.1 Two host facts that are new to the study

1. **The environment audit never measured the GPU.** `a0/env/checks/ENV_REPORT.md` records RAM,
   disk and threads (`:33`) but has no GPU/VRAM line. The 6 GB ceiling is the binding constraint on
   the entire local-model question, and it was not in the evidence set.
2. **codex is currently dead again.** `~/.codex/config.toml` is back to the **direct** form
   (`base_url = "https://zjapi.com"`, no `/v1`) and **nothing listens on 15722**. This is exactly
   the failure `a0/env/cli/CLI_REPORT.md` §5 predicted ("it will not come back by itself after a
   reboot"). Any lane using codex — KAPSO, EvE, Loreley's codex backend, SimpleLoop — cannot
   complete a call until `cc-switch -a codex proxy enable && cc-switch daemon start --detach` is
   run again. I did not run it (that starts a service).

---

## 3. Model candidates and the A1 validity risk

### 3.1 What the lanes ask of a model

* KAPSO's protocol-level calls: **~18–20k input tokens**, at `model_reasoning_effort = "xhigh"`
  (`a0/env/cli/CLI_REPORT.md` §3.3 — four recorded relay calls, 18.5k/20.2k/18.5k/20.1k in-tokens).
* EvE full runs: `rollout_max_turns: 10000`, `timeout_seconds: 7200`
  (`configs/eve/driver/codex_max.yaml`). Loreley's worker budget is 1800 s per call
  (`config.py` `worker_coding_timeout_seconds`). A campaign is many such calls.
* The task is **agentic coding**: emit valid tool calls, edit files, run the evaluator, iterate.

### 3.2 What 4.6 GB of free VRAM can hold

Fully-in-VRAM at Q4, leaving room for KV at 16–32k context: a **4–8B dense** model
(e.g. a Qwen-Coder-7B/8B-class model, ~4.5–5 GB). That class is fast (~30–50 tok/s) and weak at
long-horizon tool use.

Anything with real agentic competence is bigger: a 24B dense Q4 (~14 GB) or a 30B-A3B MoE Q4
(~17 GB) fits **partly** in VRAM and must be CPU-offloaded to the remaining ~25 GB of RAM. On a
6-core/12-thread Ryzen with DDR5, that is roughly **5–15 tok/s** (order-of-magnitude estimate, not
measured — I did not install or run a server). At 15 tok/s, one 18k-token protocol call with a
2k-token answer is ~2.5 min of pure generation *before* tool round-trips, against a 900 s
`inference.default.timeout_seconds`. A useful campaign would take days.

The AMD iGPU (Granite Ridge) shares system RAM and its VRAM carve-out is small; treating it as
additional compute is not realistic for this workload. Vulkan/ROCm offload of a fraction of layers
to it is a possible marginal gain, **unverified**.

### 3.3 The study-level risk: a **false negative about the substrate**

* **A−1 and A0 are unaffected.** Freezing `EID*`, adapter conformance and selection semantics do
  not touch the model (they are already audited at `git tag a0-audited`).
* **A1 is not.** A1 asks whether a substrate can improve algorithms on a frozen evaluator. The
  substrate's only lever on the algorithm is the *quality distribution of the candidates its agent
  proposes*. A weaker model shifts that distribution down — more no-op diffs, more structurally
  invalid candidates, fewer genuine improvements.
* The study's own power analysis (`open_world_plan_review.typ` §3.4) sets the bar: at `n=5` the
  minimum detectable effect is `1.68 σ_d`. If the local model's proposals are near-random relative
  to a frontier model's, the *true* effect size of a genuine substrate improvement falls below what
  the design can see, and A1 reports **"this substrate does not improve algorithms"** — a claim
  about the substrate that the instrument, not the substrate, produced.
* **How large?** Large enough to be the default outcome, not a tail case. The gap between a 4–8B
  Q4 local model and the models these lanes currently use (`gpt-5.6-sol/terra`,
  `claude-opus-4-5`, `deepseek-v4.1-flash`) is one to two orders of magnitude in agentic task
  resolution on public benchmarks. That number is an **estimate from general knowledge, not a
  measurement in this audit** — I make no model calls. But the direction is not in doubt, and the
  study's detectable-effect floor is low.

**Signals that would detect the false negative — use these as gates, not as afterthoughts:**

1. **A pre-registered positive control with known headroom.** The study already has one: the
   circle-packing task has documented headroom — Loreley's own bounded codex round produced a
   concrete staggered-hex layout with a better radius than the diagonal baseline
   (`a0/runtimes/loreley/llm-round/logs/logs/a0-loreley-llm-round-8802660c/worker/planning/planning-b91c0906c9f6-attempt1-20260920-182709-196092.json:68`),
   and SimpleLoop's real codex runs scored 2.541/2.625 against a 0.25 baseline
   (`a0/runtimes/simpleloop/a0_adapter/solvers.py:250-252`). **If the local-model lane cannot
   reproduce any improvement over `c_0` on that same task, the instrument is broken and A1's
   negative is inadmissible.**
2. **Calibration against the closed lane, same task, same seeds, m ≥ 10 candidates.** Require
   (a) structural completion rate ≥ 90 % (a candidate that does not compile is not a data point)
   and (b) mean score not sitting below the closed lane's minimum.
3. **Cheap trace-level tripwires, every candidate:** empty `files_changed` rate, `E*` failure-stage
   distribution, and no-op-diff rate. A lane whose candidates mostly fail structurally is measuring
   its model, not its substrate.
4. **Sanity on the other end:** if the local lane *matches* the closed lane, that is itself a
   finding worth checking — it would suggest the task has no headroom for either, which would
   undermine A1 independently of the model.

### 3.4 Cheaper ways to buy validity back

* **Keep the CLI removal and the model removal separate.** Replacing closed CLIs with
  `opencode`/`kilo`/`aider`/`openhands` costs no model quality if the endpoint stays frontier-grade
  (an OpenAI-compatible or Anthropic-compatible gateway). That alone satisfies "remove the closed
  CLI dependency" for EvE and Loreley.
* **If the model must be open-weights, do not require it to be host-local.** Serving an open-weights
  model with an open-source stack (vLLM/SGLang) on rented GPUs keeps the *client* entirely open
  source and keeps A1's instrument strong. The price is that "no autonomous external acquisition"
  returns to being a network-policy problem rather than a topological fact — i.e. you trade the
  closure win for the validity win. Name which one the study wants; they are in tension.

---

## 4. The closure interaction: where a local model must sit

### 4.1 Measured facts about the two barriers

From `a0/env/checks/ENV_REPORT.md` §6.3 and `a0/closure/evidence/02_host_loopback_cut.log`:

| Barrier | External egress | Host loopback (model feed) |
|---|---|---|
| `unshare -rn` (rootless netns) | BLOCKED (canary `dns=fail tcp=fail https=fail`) | **severed** — `NETNS_RELAY_HTTP=000`; `connect(127.0.0.1:5432)` → `ENETUNREACH` |
| docker `--internal` | BLOCKED | **severed** — `INTERNAL_HOSTGW_RELAY=fail`; siblings on the same network still reachable (`local=ok` in the self-test) |
| codex `workspace-write` (config-level) | BLOCKED, measured end-to-end with a real model turn (`17_kapso_lane_closed.json`) | see §4.2 |

So both barriers do kill a host-loopback model — but for **two different reasons**, and the
distinction is what makes the fix obvious:

* `unshare -rn` gives the process a *different loopback*. The host's `127.0.0.1` is not its
  `127.0.0.1`.
* `--internal` has no route to the host at all. (The `INTERNAL_HOSTGW_RELAY=fail` measurement is
  **confounded**: the relay binds `127.0.0.1` only, so it is unreachable from *any* container
  regardless of routing. Whether `--internal` can reach a host service bound to the bridge gateway
  is **not determined** by this evidence.)

### 4.2 A new measurement: codex's sandbox blocks **all** inet sockets, including loopback

Not previously in the evidence set, and model-free (`codex sandbox` runs a command; it makes no
model call):

```console
$ python3 -c "import socket; socket.socket(); print('socket() OK')"
socket() OK

$ codex sandbox -c 'sandbox_mode="workspace-write"' -- python3 -c "import socket; socket.socket()"
PermissionError: [Errno 1] Operation not permitted
```

Inside `workspace-write`, even **constructing** an `AF_INET` socket fails. So the candidate's shell
tool cannot reach a loopback model server — nor any other TCP target. Consequence: the candidate
execution channel and the model feed are **already disjoint** under the posture the study uses, and
a model endpoint placed anywhere is *not* a hole in the candidate channel.

### 4.3 The placement that works, and why

The consumer of the model is the **agent CLI process**, not the candidate. The CLI's own HTTP client
is outside its sandbox; only the tool subprocesses are inside. So the requirement is: *the CLI must
reach the model; the tool channel must not reach anything.*

**Recommended shape — one namespace, no default route, model on that namespace's own loopback:**

```bash
unshare -rn sh -c '
  ip link set lo up                       # lo is DOWN in a fresh netns
  llama-server -m <model.gguf> --port 8080 &   # or ollama serve
  # agent CLI runs here, with base_url = http://127.0.0.1:8080/v1
  exec <runtime> <lane>
'
```

Verified on this host (`evidence/codex_and_netns.txt`):

```console
$ unshare -rn sh -c 'ip link set lo up; ip -o addr show lo; ip route show'
1: lo    inet 127.0.0.1/8 scope host lo\
--- routes ---            # empty: no default route

$ unshare -rn sh -c 'ip link set lo up; python3 -c "...connect_ex((\"127.0.0.1\",5433))"'
111                       # ECONNREFUSED, not ENETUNREACH
```

`111` rather than `101` is the load-bearing detail: the namespace's loopback is **up and
functional**, while the host's service on the same address is **invisible**. A server started
inside therefore is reachable, and nothing outside is. This makes "no autonomous external
acquisition" a property of the route table rather than of a config flag — the win the task asks
about — and it needs no root, no new package, and no NVIDIA Container Toolkit.

**Why the container shape is the wrong one here, even though it looks cleaner.** Running the model
and the agent in one container on a `--internal` network gives the same topology, and sibling
reachability is not even needed (the CLI would reach the model on the container's own `127.0.0.1`).
But **docker cannot touch the GPU on this host** — `Runtimes: runc` only, no `nvidia-ctk`, no
`nvidia-container-runtime` — so a containerised model server is CPU-only, which the model sizes in
§3.2 cannot afford. (`--device /dev/nvidia0 --device /dev/nvidiactl --device /dev/nvidia-uvm`
plus bind-mounting `libcuda.so` is the manual stand-in for the toolkit and avoids the install; it is
fragile and I did not test it.)

**What breaks, concretely:**

1. **Every other loopback dependency of the lane moves inside the namespace too.** KAPSO's
   `gated_mcp` gate server and any HTTP MCP server, Loreley's Postgres (`127.0.0.1:5433` is
   listening now) and Redis, any host-side trace sink. Subprocess-shaped services (the frozen `E*`
   evaluator, stdio MCP servers) are fine — they are children in the same namespace.
2. **The host's ambient proxy must be stripped inside.** `http_proxy`/`https_proxy` point at
   `127.0.0.1:7890`; inside the namespace that address is the namespace's own loopback, so any
   client honouring them fails or hangs. Codex exposes `respect_system_proxy` (currently
   `under development`, `false` — `a0/closure/evidence/05_codex_surface.log`) but do not rely on it:
   unset the variables.
3. **DNS dies with the route.** Use a literal `http://127.0.0.1:<port>/v1` base URL; a hostname
   resolution will not work.
4. **KAPSO's URL validator accepts this shape but not a bridge IP.**
   `core/api_endpoint.py:36-43` permits plaintext `http` **only** for literal loopback hosts;
   `http://model:8080/v1` or `http://172.17.0.1:8080/v1` is rejected. A loopback design passes
   for free; a container-network design needs TLS.
5. **Per-lane server startup.** The server must be launched inside each namespace (or by one
   long-lived supervisor that starts the server and then spawns the lanes), so a single shared
   multi-process model server is not available. For a 5–20 GB model, load time per lane is real
   cost.
6. **`unshare -r` maps your uid to root inside.** Files created inside are owned by your real uid
   outside, but tools that compare ownership may behave differently; `git` in particular has
   reported "dubious ownership" under uid-mapped namespaces.

**The cheaper variant, if a topology proof is not required.** Keep the orchestrator, model and
evaluator on host loopback and rely on the CLI's own sandbox for the candidate channel (KAPSO's
codex lane and SimpleLoop's shipped lane already do this, and it is measured closed with a live
model turn). This is a *config-level* claim, exactly what §4.3 says is not sufficient on its own —
but it is supported by a probe with a positive control, it needs no namespace, and §4.2 shows the
sandbox is not merely "no egress" but "no inet sockets at all".

**The lane this unlocks.** KAPSO's `claude_code` write lane — the `GENERIC` default — has **no CLI
sandbox at all** (`--dangerously-skip-permissions`, `capabilities.sandbox: False`), which is why
`a0/closure/VERDICTS.md` calls it the blocker. A namespace barrier around that lane closes it.
That is the strongest argument for the local-model + netns design: it is the only shape that closes
KAPSO's default lane, regardless of model quality.

---

## 5. Recommended path and its concrete cost

**Phase 1 — remove the closed CLIs (no model change, no study-level cost).**
`opencode` (MIT) for EvE, `kilo` (MIT) for Loreley — it is already the default backend — and
`openhands`/`aider` for KAPSO's write lane, with the model endpoint unchanged.

| Item | Cost |
|---|---|
| Install `opencode` (npm, MIT) | one npm install; **not installed** (verified) |
| Install `kilo` (npm, MIT) | one npm install; **not installed** (verified); this is what makes Loreley's shipped default usable at all |
| `aider` (if chosen) | pinned Python **<3.13** (`pyproject.toml:58-65`) vs host 3.14.7 → a `uv`-managed 3.12 env |
| Study validity | unchanged — same models |
| Closure | unchanged: `opencode` has zero sandbox knobs, `kilo` likewise → KAPSO's claude lane and EvE's opencode lane stay CONDITIONAL |

**Phase 2 — remove the closed model (the expensive part).**

| Item | Cost |
|---|---|
| Model server | `pacman -S extra/ollama-cuda` (0.34.0, binary) **or** build `llama.cpp` with CUDA (AUR; `extra/llama-cpp` is CPU-only) |
| Weights | 5–20 GB download, on disk not `/tmp` |
| Hardware ceiling | 4.6 GB free VRAM → 4–8B fully resident, or 20–30B MoE CPU-offloaded at an estimated 5–15 tok/s |
| Codex lanes | config only: custom `model_providers.<id>` with `wire_api = "responses"`; already in place for EvE (`a0/runtimes/eve/tools/run_one_eve_iteration.py:97-134` injects exactly this block) |
| KAPSO codex lane | config only, via `agent_specific.env_defaults.CODEX_HOME` (`adapters/codex_agent.py:127-129`, `:240-241`) or a global `~/.codex/config.toml` |
| Loreley codex lane | `WORKER_*_EXTRA_ENV={"CODEX_HOME": …}`, which also disables the backend's home isolation (`backends/codex_cli.py:252`) |
| SimpleLoop | parent-env `CODEX_HOME` only — `solvers.py:280-281` passes no `-c` |
| Claude lanes | `llama-server`'s `/v1/messages` (`--jinja` for tools) via `oss_claude_code`'s `ANTHROPIC_BASE_URL` seam, **or** a Messages-API shim in front of ollama |
| Closure | one `unshare -rn` wrapper per lane (§4.3); no root, no new package |
| **A1 validity** | **the real cost** — §3.3. Milestone: a passing positive control on a task with known headroom, or A1's negative is inadmissible |

**Phase 3 — if A1 validity cannot be bought.** Serve open weights with an open-source stack at a
rented endpoint. Client side fully open source; closure returns to a network-policy claim.

---

## 6. Blockers

1. **VRAM.** 6 GB total / 4.6 GB free is the binding constraint; no local model with credible
   agentic competence fits without CPU offload at single-digit-to-teens tok/s.
2. **No GPU in containers.** `docker` has `runc` only, `nvidia-ctk` and `nvidia-container-runtime`
   absent → the container-shaped closure design is CPU-only here.
3. **KAPSO's `research` role cannot be localised.** Web search is a hard requirement
   (`core/cli_inference.py:116-121`, `core/preflight.py:500-511`).
4. **`/tmp` is RAM-backed** (16 GiB tmpfs) — the study's accepted snapshot convention collides with
   staging large weights.
5. **codex is currently broken again** (relay down, config reverted to the failing direct form) —
   every codex-backed lane is blocked until the user re-runs the two `cc-switch` commands.
6. **Python 3.14.7** vs the lanes' own requirements (aider <3.13; EvE wants ≥3.11; KAPSO ≥3.10) —
   needs a `uv`-pinned interpreter, and vLLM/torch wheel availability on 3.14 is untested.

---

## 7. What I could not determine, and what would invalidate this

**Not determined (no install, no start, no model call):**

* Whether `codex`'s Responses client actually works against `llama-server` ("converts Responses
  request into Chat Completions request") or against ollama's non-stateful Responses. The request
  shapes codex sends — reasoning items, `include`, `prompt_cache_key`, `store`, streaming tool
  calls — may exceed what either implements. **This is the single highest-value probe to run next**
  and it costs one local call, no API budget.
* Whether Claude Code works against `llama-server`'s `/v1/messages` — the README itself declines to
  claim compatibility, and tools need `--jinja`.
* vLLM's Responses-API support (its docs page did not resolve; unverified).
* Whether docker `--internal` can reach a **host** service bound to the bridge gateway. The
  existing measurement (`INTERNAL_HOSTGW_RELAY=fail`) is confounded by the relay's `127.0.0.1`
  binding. Settle it by binding a listener to `0.0.0.0` and re-running the same probe.
* Actual token throughput of any candidate model on this host (no server installed, so no
  measurement — §3.2's 5–15 tok/s is an estimate).
* Whether the manual `--device /dev/nvidia*` + `libcuda.so` bind-mount gets a container GPU access
  without the toolkit.

**What would invalidate the conclusion:**

* If a local Responses-compatible server turns out to work with codex end to end at acceptable
  latency, the "cannot serve it" half collapses — what remains is only the model-quality/A1 risk.
  (Conversely, if codex's Responses client *fails* against both ollama and llama-server, the
  practical local route for every codex lane is gone and only the claude/opencode/kilo lanes
  survive.)
* If A1 is redefined to compare substrates **at fixed model identity**, or with the model treated
  as a declared instrument rather than a variable, the false-negative framing weakens — the
  comparison stays internally valid even at low effect size, and only the power claim suffers.
* If the study's §4.3 probe standard is read as satisfied by a *route-table* read (no default route)
  rather than by executing a canary inside the barrier, §4.3's design gets materially cheaper. If
  it demands an executed probe, the `unshare -rn` wrapper still satisfies it — the canary can be run
  inside the same namespace.
