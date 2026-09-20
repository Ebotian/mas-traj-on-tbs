# A−1 frozen evaluation contract — extracted specification

Source of truth: `/home/ebt/Downloads/typst_file/open_world_plan_review.typ` (§4.0–§4.3) and
`/home/ebt/Downloads/typst_file/open_world_plan_independent_review.typ` (audit history, cited
only where the intent of a rule needs explaining). Both files are read-only for this
workstream; every rule below carries a `file:line` pointer into them. The Chinese text is
quoted verbatim where the protocol states a rule; `plan:` = review file, `audit:` = independent
review file.

This document is what downstream agents read instead of re-parsing the protocol. Where a
binding decision had to be made that the protocol leaves open, it is marked **[decision]**.

---

## 1. Why A−1 exists

> runtime 原生的 evaluator 身份不可通约——KAPSO 是 manifest 指纹，Loreley 是
> `evaluator_name + version + campaign_program_hash`，EvE 没有同构概念。因此"要求
> `theta_E` 在三套 wrapper 间一致"在 EvE 上无定义；把 runtime 自己的 provenance schema
> 当成研究真相，也正是 D1／D16 已经暴露过的错误。

`plan:499`. Consequence `[decision]`: no comparison may ever be made between `EID_K`,
`EID_E`, `EID_L`; the only admissible statement is that each `EID_r` was *derived from* the
same `EID*`.

---

## 2. EID* — the canonical evaluator identity

> *做法*：把真相冻结在 runtime *之外*：
> ```
> EID* = H( EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition )
> ```
> 各 runtime 只做映射 `EID* -> EID_r`：adapter 负责声明并记录它如何把自己的原生身份表示
> 绑定到 `EID*`（EvE 无原生身份时就记录"由 adapter 固定注入"）。

`plan:501-507`.

The five components, and what each must pin:

| Component | What it hashes | Typical content for a task |
|---|---|---|
| `EvaluatorSource` | the evaluator program's source | the evaluator's own source tree (not the candidate's) |
| `DependencyLock` | resolved dependency versions | `uv.lock` / `requirements.txt` / `pyproject.toml` entries |
| `DataManifest` | the frozen input data | problem instance *and* the fixed candidate set `C*` |
| `Config` | the evaluator's configuration | `theta_E` defaults, epsilon, network policy, cwd policy |
| `MetricDefinition` | how the metric is defined | metric name, direction, the Outcome's field list |

### 2.1 A−1 acceptance criterion

> *A−1 的验收*：上述五项各有一个可复算的哈希，且 `EID*` 写进实验配置；任何一项变更都必须
> 产生新的 `EID*` 并记入 trace。

`plan:509`. Three separate obligations:
1. **five independently recomputable hashes** — a third party holding only the `EID*.json`
   document must be able to recompute each component digest and `EID*` itself;
2. **`EID*` is written into the experiment configuration** — the plumbing task's value lives in
   `contract/out/plumbing.EID.json` (`task`, `spec`, `EID*`), and the adapters copy it in;
3. **any single-input change yields a new `EID*` and is recorded in the trace** — every trace
   event carries `eid_star`, so a run whose identity changed mid-flight is detectable.

**[decision] canonical serialization.** The protocol does not define `H`. This contract fixes
it: `sha256`, over ASCII-only JSON with recursively stringified keys, sorted keys, `,`/`:`
separators, no NaN/Infinity, and an explicit domain-separation prefix per component
(`a0/evalcontract/v1/<Component>`), composed as `a0/evalcontract/v1/EID*` over the five
component digests. Absolute paths, mtimes, ownership, hostname, pid and traversal order are
excluded from every digest, so the same logical input gives the same digest on any machine and
from any cwd. Details and the exact payload shape are in `evalcontract.py` and README §"What is
hashed".

---

## 3. A0.1 — Evaluator Integration Conformance

> 固定候选集 $C^* = {c_1, ..., c_k}$，检验的*不是* `EID_K = EID_E = EID_L`，而是：
> ```
> 对每个 runtime r 与每个候选 c:  E_r(c; theta_E) = E*(c; theta_E) ± epsilon
> 且 EID_r 由 EID* 派生（adapter 声明 + 可复算的哈希）
> theta_E = (seed, fidelity, fraction, ...)  在三套 wrapper 间一致; 缺失参数取等价的固定值
> ```

`plan:513-519`. So the acceptance formula is exactly
`E_r(c; theta_E) = E*(c; theta_E) ± epsilon` for every runtime r and every candidate c,
`EID_r` derived from `EID*` by an adapter declaration plus a recomputable hash, and `theta_E`
identical across wrappers with missing parameters replaced by fixed equivalent values.

### 3.1 E* vs F_r — the A0.1/A0.2 split

> ```
> E*  : Candidate -> Outcome                所有系统共享的冻结最终评价器（A-1 冻结其身份）
> F_r : Outcome -> SearchSignal_r           runtime 特有的搜索信号（各系统可以不同）
> ```

`plan:524-525` (also `plan:521`). `E*` must be executed faithfully by all three wrappers; `F_r`
may differ per runtime (KAPSO consumes a scalar, EvE a PyTree, Loreley is multi-objective) but
must be **declared and frozen before the experiment** (`plan:528`).

> A1 的第一轮固定共同信息，即 `F_r(E*) = scalar(E*)`

`plan:528`. The default first-round rule, and the only one used in the contract's first round:
`F_r(E*) = scalar(E*)`. A native-`F_r` control arm is allowed later but must never be described
as part of the same "runtime comparison" (`plan:528`).

### 3.2 theta_E includes the evaluator identity

> 统一接口应是 `E(c; theta_E)`，且 `theta_E` 还必须包含 evaluator 身份。

`audit:60`, cf. `plan:518`. `theta_E = (seed, fidelity, fraction, …)` and its identity
component is `EID*`; the trace records both.

Per-system facts that constrain `theta_E` (`plan:530`):
* KAPSO passes a fixed seed by CLI (`--fidelity` / `--fraction` / `--seed`, default 1337, from
  `evaluation_maintainer.subsample_seed`, `orchestrator.py:599`); its registered-evaluation
  contract requires the fast tier to subsample deterministically with that seed
  (`evaluation_maintainer/prompts/setup_build.md:11-15`, `setup_provided.md:13-17`). The seed is
  therefore an *evaluator input*, not merely a comparability label.
  Measured on `C_STAR/c01_good_hex` at `fidelity=fast, fraction=0.15`
  (`.venv/bin/python e_star.py evaluate --candidate C_STAR/c01_good_hex --seed <S> --fidelity
  fast --fraction 0.15 --out …`): `seed=1337 → audit sample [0, 3, 12, 22]`,
  `seed=1338 → audit sample [0, 14, 18, 24]`; 4 of 26 items audited either way. The seed
  therefore selects *which* items are checked, and hence which verdicts are reachable — the
  opposite of "inapplicable". This is now encoded in the frozen `Config` component
  (`Config.value.theta_e_semantics.seed`, `theta_e_canonical.seed = 1337`), and it was the
  substantive half of the identity arbitration in `README.md` §8.
* EvE and Loreley pass **no seed** at all to their evaluator (EvE injects only
  `EVE_WORKSPACE_ROOT` / `EVE_SOLVER_ROOT` / `EVE_EVAL_LOG_ROOT` / `PYTHONDONTWRITEBYTECODE`;
  Loreley's `EvaluationContext` has no seed field — `mapelites_sampler_seed` is for sampling,
  not evaluation). Hence "the randomness must be built into the evaluator itself", and a
  missing parameter must be recorded with the fixed equivalent value actually used
  (`plan:518`, `plan:530`).

### 3.3 KAPSO's additional hard invariant (D16)

> ```
> 每条 attempt 的 (evaluator, fidelity, fraction, seed)
>   必须等于产出该分数的那个 run 的 manifest 三元组
> 等价: 授予类必须等于告知 agent 的命令类
> 处置: mode != off 且出现错配 => 该轮计为 A0.1 failure
> ```

`plan:532-539`; the stronger form is argued in `audit:206` ("复审方建议
`RegisteredMode => ManifestOfRecord != 空`。该表述必要但偏弱——它不排除'记成另一类'的错标").
Mechanism (`audit:205`): `orchestrator.py:629-643` hard-codes the command told to the agent as
`--fidelity full --fraction 1.0`, while the granted class defaults to `fast`/`0.15`
(`fidelity.py:660-666`, `:247`), so under `mode: on/auto` every probe round mismatches;
`manifest_score` returns `None` and the judge's score survives as `node.score`
(`feedback_flow.py:66-95`, `registered_evaluation.py:124-159`). Practical consequence: the
**adapter contract** requires `fidelity.mode = off` for KAPSO's first round, and a mismatching
round counts as an A0.1 failure.

Scope note, so the requirement is not mistaken for an `EID*` input: `fidelity.mode` is a KAPSO
*adapter* setting, not a property of `E*`. It is deliberately **not** part of the hashed
`Config` component — `Config` describes the frozen evaluator's own configuration (`theta_E`,
epsilon, environment policy, exit codes). The adapter declares `fidelity.mode = off` through its
own configuration and records it on the trace; `EID*` is unchanged by it, which is correct
because the same `E*` runs either way. Also note the invariant it guards is a **triple** —
`(fidelity, fraction, seed)` — because KAPSO's manifest has no evaluator field (§9.3).

### 3.4 Three hard constraints

> ```
> 1 evaluator 不得依赖 cwd 或 PATH
>     EvE 会把 agent runtime bin 前置进 PATH; 三者的候选根各不相同
>     (KAPSO 分支 worktree / EvE 的 EVE_SOLVER_ROOT / Loreley 的 context.worktree)
> 2 计数与日志不得写在会被还原的目录
>     KAPSO 的 kapso_evaluation/ 会被 git checkout 还原
> 3 E* 的输出可以是多字段; 收敛为单标量是 F_r 的职责, 不是 E* 的约束
>     (EvE 的 score.yaml 是标量, Loreley 的 metrics 是多目标 —— 由 adapter 各自收敛并声明)
> ```

`plan:544-550`.
1. **No cwd or PATH dependence.** Enforced by requiring an explicit `--candidate` argument on
   the E* CLI, by having `E*` execute the candidate as a private copy beneath its own state root
   under a fully specified child environment (`PATH=""`, `PYTHONPATH=""`, `PYTHONNOUSERSITE=1`,
   `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`, private `HOME`/`TMPDIR`/cwd — frozen as
   `Config.value.environment_policy`), and by rejecting PATH-resolved helper binaries
   (`adapter_contract.md`).
2. **Counters and logs must not live in a directory that gets restored.** KAPSO's
   `kapso_evaluation/` is restored by `git checkout`; same hazard for any per-run directory
   inside a candidate worktree. Enforced by hashing only the declared trace output root and by
   the resource-trace location rule.
3. **`E*` may return multiple fields.** Collapsing the Outcome to one scalar is `F_r`'s job, not
   `E*`'s. Enforced by the trace schema: `outcome.fields` is a map, and a `scalar` key inside it
   is rejected (`trace_validate.py`, `_FORBIDDEN_OUTCOME_FIELDS`).

### 3.5 Two false-green traps

> ```
> 假绿: EvE 的评测异常被静默映射为 failure_score(0.0), 与真实 0 分不可区分
> 假绿: Loreley 评测超时合成失败、metrics 超过 64 被截断、命中持久缓存会复用旧数
> ```

`plan:551-552` (sources: `audit:1016`, `workflow/evaluation.py:161-167` for EvE;
`config.py:29, 561`, `core/worker/evaluator.py:2304-2310` for Loreley). Both are handled by one
mechanism: every score event carries `evaluator_evidence.status`, so
`synthesized_failure` / `timeout` / `truncated_metrics` / `cache_hit` can never be mistaken for
a genuine measurement. A `cache_hit` must name `cached_from_run_id`; a synthesized failure must
carry a `detail` string (`trace_schema.md` §3.3).

---

## 4. A0.2 — Score → Search Contract

> 不能要求三套 runtime 都做全局 argmax——三者的 selection semantics 不同。检验必须连同
> *配置条件*一起冻结。

`plan:557`. The per-system checks and the condition under which each is meaningful
(`plan:559-567`):

| System | Official semantics + condition to freeze | Executable A0.2 check |
|---|---|---|
| **KAPSO** | fully deterministic: parent, deliverable and round representative are all argmax. *Condition*: `parent_policy = "best"` (the default, `strategy.py:198, 212`) | set `E(c_1) > E(c_2)`, run one round, assert the next round's parent branch is `c_1` and that the best-experiment branch returns `c_1` |
| **EvE** | score entry is rank-weighted sampling with an unseeded RNG. *Condition*: `working_optimizer` uses `RankSoftmaxSampler` (`temperature: 1.0`, `replacement_mode: auto`); `solver_examples` uses `RankExponentialSumSampler` (`features.score` weight 1.0, `temperature: 1.0`, `replacement_mode: no_replacement`, `n = 4`); `solver_prefill` is the score-independent `UniformSampler` | a **frequency** test, with expectations derived per class: `P(c_1) = 1 / (1 + e^(-1)) ≈ 0.731` only for `RankSoftmaxSampler` with `k=2`, `T=1`, one draw; the `solver_examples` class has a different sampler and `n`, so its expectation must be derived separately. The prefill segment may not be used, and one run is not enough |
| **Loreley** | QD archive: non-dominated replacement **within the same cell**; truncation over the limit is by crowding distance, not score; sampling is score-independent; no global-best-wins. *Condition*: the two candidates share descriptor/measures (same cell) | assert `c_1`'s archive result is a replacement and `c_2` is removed from the cell; then assert the reported branch points at `c_1`. Across cells, a higher score must **not** evict |

**[decision] `F_r` freeze.** For round one every runtime declares
`F_r(E*) = scalar(E*)` (`plan:528`), whatever its search machinery internally does with it.
Loreley's multi-objective archive behaviour is exercised through its `selection` trace, not by
changing `F_r`.

---

## 5. Closure — no autonomous external acquisition

> *封闭性验证（B0 前置，机制在 A0 就要跑通）*：必须用探测证明所选 runtime 没有自主外部获取，
> 而不是只在配置里关。

`plan:569`. Per-system means — **corrected against the source; the protocol's own wording is
wrong on the first two points, see §9**:

* **EvE** is closable by `codex_tmux` config (`sandbox_mode: workspace-write` +
  `allow_network: false` + `web_search: disabled`). `allow_network` exists as a real parameter
  (`providers/agent/config.py:26,31,86`; `providers/agent/python_runtime.py:20,27,332`;
  `runtime/driver.py:381-386`, where it selects `danger-full-access` when true and
  `workspace-write` when false). The trap is that the shipped full-run driver is `codex_exec`,
  which has **no sandbox parameter** and hardcodes `--dangerously-bypass-approvals-and-sandbox`
  (`providers/agent/drivers/codex_exec.py:419-436`), so a config-only closure verdict on that
  path is a false green.
* **KAPSO's** front doors (ideation `web_search`, `implementation_web`, `ideation_gates` /
  `implementation_gates`, `knowledge_search`) can be configured off. The Bash side door has a
  lane-level parameter, `agent_specific.sandbox` (`codex_agent.py:117`, default
  `"danger-full-access"`, passed as `--sandbox` at `:192-193`), but it defaults to the most
  permissive mode; the claude lane (`claude_code_agent.py:1182`) has no equivalent. KAPSO
  therefore needs the parameter set explicitly *and* isolation or a code change for the claude
  lane.
* **Loreley** has no network switch on its default path, so it needs isolation or a codex
  backend.
* Hard CLI-level guarantee: Codex CLI's `workspace-write` defaults to `network_access: false`
  (`plan:569`) — but only where a sandbox mode actually reaches the CLI.

The contract therefore requires a **probe**, not a setting: `adapter_contract.md` §6 defines the
closure-probe interface, and a runtime whose probe shows egress is excluded from `R_1`.

---

## 6. What A0 feeds downstream

`R_1 = { r ∈ {SimpleLoop, KAPSO, EvE, Loreley} : A0.1_r ∧ A0.2_r }`, and `|R_1| >= 1` is enough
to continue — one adapter's bug must not block the other experiments (`plan:490`). A0 is
candidate screening, not a collective gate.

Failure accounting that A0 must make possible (`plan:577`):

```
失败项: FailureStage 与 resolve_failed / comprehension_failed / mechanism_mismatch 计数
```

and the trajectory strata the enum is cut along (`plan:628`):

```
轨迹分层: Search -> Found -> Resolved -> Verified -> Injected -> Used -> Improved
```

The trace schema's `failure_stage` enum covers these strata plus the evaluator-side failures
(`evaluator_failed`, `timeout`, `boundary_violation`, `budget_exhausted`).

---

## 7. Budget accounting for round one

> ```
> B_hard              = ( T_wall, N_evaluatorCalls, concurrency cap )   能真正强制
> secondary telemetry = ( N_modelCalls, T_in, T_out, C_usd )            尽量采集
> ```
> *不为此先造统一 API 代理*。原则是 *measurement sophistication 正比于 decision sensitivity*

`plan:605-612`. Only quantities that can be uniformly enforced are hard constraints in round
one; token accounting is deliberately excluded because the three systems' self-reported numbers
are not comparable (KAPSO's `cost_budget` is USD and always 0 under the codex backend; EvE
records tokens and turns but never accumulates a run-level budget — `StopConditions` and
`write_run_checkpoint` are dead code; Loreley records the most, including token classes and
`cost_source`, and its `evaluation_attempts` table can separate a real run from a cache reuse).
The resource trace therefore requires `T_wall`, `N_evaluatorCalls`, `concurrency`, and records
the rest as `secondary`.

---

## 8. Gate to H1 (only the A−1/A0-relevant clauses)

> *门槛*：A−1 的 `EID*` 已冻结并写入配置；A0.1／A0.2 通过（$|R_1| >= 1$）；…

`plan:637`. `EID*` frozen and written into the configuration, A0.1 and A0.2 passed, at least one
runtime in `R_1`.

---

## 9. Where the protocol's wording does not match the code

Downstream workers read this document instead of re-parsing the protocol. Where the protocol's
wording is inaccurate, writing a test to it produces a test for something that does not exist — or
worse, a **false green**. Each item below is a correction with its evidence, and each says
explicitly whether an *earlier revision of this workstream's own notes* was wrong.

### 9.1 EvE: `allow_network` exists — the earlier "it does not exist" note was WRONG

`a0/acceptance/DERIVATIONS.md` finding **F4** states "there is no `allow_network` parameter
anywhere in EvE". **That is wrong and is corrected here.** The parameter exists and is plumbed.
(Paths in §9.1–§9.3 are relative to the runtime checkout root — for EvE
`/tmp/eve/src/scaling_evolve/`, for KAPSO `/home/ebt/kapso_ck/kapso/src/kapso/`, for Loreley
`/tmp/lor/loreley/`; all were read directly, and the same commits are pinned under
`a0/tasks/circle-packing/upstream/` where applicable.)

| Where | Evidence |
|---|---|
| policy defaults | `providers/agent/config.py:24-32` — `benchmark_safe: allow_network: False`, `open_agent: allow_network: True` |
| typed config field | `providers/agent/config.py:86` — `allow_network: bool \| None = None` |
| runtime policy object | `providers/agent/python_runtime.py:20,27` — declared and exported in the policy dict; `:332` — `if not bool(policy.get("allow_network", True)):` blocks egress |
| driver → sandbox | `algorithms/eve/runtime/driver.py:381-386` — `_sandbox_mode_from_driver_cfg` returns `danger-full-access` if `allow_network` is true, else `workspace-write` |

What **is** true, and is the actual trap: the shipped full-run driver for the circle-packing
config is `codex_exec` (`configs/eve/driver/codex_max.yaml:6,12`: `driver: codex_exec`,
`web_search: live`), and `codex_exec` has **no sandbox parameter at all** — its `__init__` has no
`sandbox_mode` (`providers/agent/drivers/codex_exec.py:79-100`) and `_argv` hardcodes
`--dangerously-bypass-approvals-and-sandbox` (`:419-436`, the flag on line 434). Feeding that
driver `driver.sandbox_mode=workspace-write` is **silently ignored**. So a closure verdict
obtained by configuration alone on EvE's default path is a **false green**; closure for EvE is
reachable only via `codex_tmux` (`providers/agent/drivers/codex_tmux.py:200-201` defaults:
`sandbox_mode="workspace-write"`, `web_search="disabled"`) or by cutting egress externally.

### 9.2 KAPSO: a lane-level sandbox parameter exists, defaulting to full access

The protocol (`plan:569`) says KAPSO's Bash side door "cannot be closed (no lane-level sandbox
parameter; the codex lane falls back to full access)". The *conclusion* is right for the default
configuration, but the *reason* is not: the parameter exists.
`execution/coding_agents/adapters/codex_agent.py:117` reads
`self._sandbox = str(spec.get("sandbox", "danger-full-access"))` and passes it to the CLI as
`--sandbox <mode>` (`:192-193`); the same adapter defaults `web_search` on (`:118`). So the codex
lane is closable by setting `agent_specific.sandbox` explicitly. The claude lane
(`claude_code_agent.py:1182`, `--dangerously-skip-permissions`) has no equivalent parameter and
does skip permissions, so for that lane the protocol's conclusion stands.

### 9.3 KAPSO: there is no evaluator field in the manifest, so the "manifest triple" is a triple

`plan:532-539` writes the invariant as `(evaluator, fidelity, fraction, seed)`. KAPSO's manifest
carries **no evaluator field**: `parse_manifest_line`
(`execution/evaluation_maintainer/maintainer.py:64-83`) requires exactly `fidelity, fraction,
seed, items, total_items`, and the accepted check
(`registered_evaluation.py:87-99`) compares `fidelity`, `fraction` (to `1e-9`) and `seed` only.
Evaluator identity is enforced out of band by (a) `registered_evaluator_id =
manifest_fingerprint(build_evaluation_manifest(kapso_evaluation/))`
(`maintainer.py:216-218`, SHA-256 over a sorted file manifest,
`evaluation_integrity.py:112-119`) and (b) `sync_registered_evaluation` overwriting the branch's
evaluation tree with the registered head before every frame run
(`registered_evaluation.py:193-200`). A test written to the protocol's four-element wording looks
for a field that does not exist. Full derivation and the three traps inside the check:
`a0/acceptance/DERIVATIONS.md` §2.3.

### 9.4 Loreley: under the default single objective the archive is a per-cell argmax

`plan:561`/`plan:567` assert that a strictly higher score does **not** guarantee selection
("无全局最优必胜"). That is true only with ≥2 objectives. The default is a **single** objective —
`config.py:916-919`: `mapelites_objectives` defaults to
`(ObjectiveSpec(name="composite_score", direction="max"),)` — so no two strictly different scores
are non-dominated, every cell front has exactly one member (`pareto_archive.py:425-451`), and the
archive is the **per-cell argmax**, with the report query
(`scheduler/main.py:876-931`) the argmax over everything evaluated. Evidence by execution of the
real class: `a0/acceptance/DERIVATIONS.md` §6 section 2d — 12 candidates in one cell with scores
0..11 leave exactly `k11`; and §6 section 2e shows crowding truncation only bites with 2
objectives. The cross-cell and epsilon-tie controls remain meaningful; the "higher score may not
be kept" claim needs a multi-objective configuration to be exercised, and `admission_policy`
must be frozen (`"pareto"` default, `config.py:928-930`).

### 9.5 EvE: the two frozen samplers are distributionally identical at the protocol's test conditions

`plan:563` warns that `solver_examples` has "a different sampler and `n`, so its expectation must
be derived separately". The `n` is the reason; the sampler class is not.
`RankSoftmaxSampler` and `RankExponentialSumSampler` with one scalar feature of equal weight and
temperature induce the **same** weight vector (`samplers/rank_softmax.py:104` vs `:181`, stated in
the module docstring `:50-51`), measured identical at `k=2, T=1, num=1` (both `0.7310586`,
`DERIVATIONS.md` §6 row 5c). A pre-registered "distinguish the two classes" frequency test at
those conditions is unfalsifiable. Detail: `DERIVATIONS.md` §1.6 finding F1.

### 9.6 EvE: the frozen configuration does not list the sampler sites that exist, and one has no RNG

`plan:561-566` freezes two score-consuming sampling sites; the config has **four**. The extra two
are `optimizer_examples` (`PerWorkerExcludeAllWorkingSampler` over
`RankSoftmaxSampler(T=1.0, no_replacement)`, `num = n_optimizer_examples_phase2 - 1 = 3`) and
`produced_optimizers` (`RankExponentialSumSampler`, `num = n_workers_phase2 = 2`) — both at
`phase2.py:553-637`. A0.2 cannot tabulate their expectations without also freezing the optimizer
population, which the protocol does not do; they are out of scope for the round-one score test
unless the study freezes that population. Also: EvE's RNG is genuinely unseeded (`populations/
base.py:40`, `factory.py:304-317`, and no seed key exists anywhere in the config tree), which is
*why* a frequency test is mandatory. Detail: `DERIVATIONS.md` §1.1 and §7 item 4.

### 9.7 The trace reference `selection.source_score_event_id` is cross-file by construction

`plan:469` asks for three traces; the trace schema requires a selection event to name the score
event that drove it. Those two obligations conflict when the traces are three separate files, and
the original validator resolved the reference *within one file*, so every selection event in a
per-kind file reported an error. Resolved by making the **run** the validation unit
(`trace_validate.py validate-run`, `adapter_contract.md` §6.3, `trace_schema.md` §1.1). Detail:
`README.md` §8.
