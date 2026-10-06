# 仓库状态：A−1 / A0.1 / A0.2 测量链（供外部审查）

* 仓库：`/home/ebt/rsi-dev`（本地 git，**无 remote**）· 分支 `main` · HEAD `0851806`
* 里程碑标签：`a0-audited`（A−1/A0.1/A0.2 完成并通过独立审计）
* 生成时间：2026-09-21
* 本文目的：把一个**无法访问本机**的审查者所需的全部事实装进一份自足文档，并列出最希望被攻击的环节

**给审查者的最短路径**：§1 是问题与阶段，§3–§4 是已完成部分的判定与审计结论，§5 是运行环境与 lane 现状（**含一处我们自己做错又更正的结论**），§8 是承认的错误与未验证项，§10 是希望你重点攻击的十个问题。

---

## 1. 项目在做什么

研究问题是：**开放世界地获取外部工件，能否改进算法自动搜索（RSI）**。

在花预算测这件事之前，必须先证明**尺子是准的**。因此项目的第一阶段不是实验，而是造测量链：

```
A-1   冻结 canonical EvalContract     冻结"评测器身份"（五分量各一个可复算哈希）
A0.1  Evaluator Integration Conformance 三个 adapter 是否忠实执行同一个 E*
A0.2  Score -> Search Contract         各 runtime 是否按它声称的 selection semantics 消费评价
A1    SimpleLoop vs QualifiedRuntimes  选出后续实验的 substrate R*
B0+ / B0 / B1                          外部工件能否被利用、普通既有实现是否提升搜索、主动获取是否值得
```

**当前状态：A−1、A0.1、A0.2 已完成并通过独立对抗审计；A1 未开始**（其任务选择与预算口径待用户在另一窗口拍板）。

被测对象是四套 runtime：**KAPSO**（`/home/ebt/kapso_ck/kapso` @`7d99b152`，MIT）、**EvE**（`scaling-group/eve` @`979065fd`，Apache-2.0）、**Loreley**（`NeapolitanIcecream/loreley` @`4c375920`，Apache-2.0），以及我们自建的基线 **SimpleLoop**。

一条容易被忽略的协议事实：`R_1 = { r ∈ {SimpleLoop, KAPSO, EvE, Loreley} : A0.1_r ∧ A0.2_r }`，即 **SimpleLoop 也受 A0.1∧A0.2 约束**（交接方最初漏了它，我们补上了）。

## 2. 架构：单向依赖的八层

```
协议层   open_world_plan_review.typ §4      外部权威，只读，不在本仓库内
契约层   a0/contract/        EID* 方案 · 三 trace schema + 校验器 · adapter CLI 契约 · 两张 A0 级冻结表 · SPEC.md
真相层   a0/tasks/circle-packing/  E*（冻结评测器）· C*（14 个固定候选）· E_STAR.json · EID_INPUTS.json
预期层   a0/acceptance/      实验前写下的期望值、样本量功效分析、假绿陷阱清单
适配层   a0/runtimes/{kapso,eve,loreley,simpleloop}/
汇合层   a0/conformance/     跨适配器裁判——唯一能判 A0.1 的组件
封闭层   a0/closure/         探针证明"无自主外部获取"
审计层   a0/verify/          独立对手：重算，而不是重跑
前提层   a0/env/             环境核查 · 探针工具 · CLI 诊断
```

依赖单向：契约 → 真相 → 预期 → 适配器 → 汇合/封闭 → 审计；审计层不得修改他人代码。每个工作流独占一个目录，契约是唯一接口。

### 核心设计决策（附理由）

1. **真相冻结在 runtime 之外**。三套 runtime 的评测器身份不可通约（KAPSO 是 manifest 指纹，Loreley 是 `evaluator_name+version+program_hash`，EvE 没有同构概念）。要求"三种原生身份相等"在 EvE 上无定义；把某个 runtime 的 provenance schema 当研究真相是已知错误。故 `EID*` 在外部定义，adapter 只声明并**证明** `EID_r → EID*` 的映射。
2. **`E*` 与 `F_r` 分离**。`E*: Candidate→Outcome` 共享冻结；`F_r: Outcome→SearchSignal_r` runtime 特有、必须事前声明。第一轮统一 `F_r(E*) = scalar(E*)`，否则无法区分"评测口径差异"与"搜索机制差异"。
3. **在固定 `C*` 上检验映射忠实度**，并按**判定**而非数字比较：`C*` 里故意放 4 个 `invalid`、5 个 `error` 候选，防止把崩溃静默写成 `0.0`。
4. **期望值由别人先算好**（EvE 的分数入口是未播种的 rank 加权采样，只能做频率检验，样本量必须事先定死）。
5. **run 为校验单元**的三条 trace + 一张冻结的 `FailureStage` 映射表，使四套 runtime 的失败计数可相加。
6. **封闭性用探针证明**（配置里关掉不等于封闭），且必须两个对照：未拦截真的能出去、拦截真的出不去。
7. **A0 是候选筛选而非集体门**（`|R_1| ≥ 1`），一个 adapter 的 bug 不得阻断其他。
8. **独立对抗审计**：一台不会失败的仪器没有价值。

## 3. 已完成部分的判定

### 3.1 冻结的评测器身份

```
EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328
  EvaluatorSource   a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
  DependencyLock    7b02f1a71288335ff92fe68da8804349e416ba4ae9e95f8cd0c6a3b5bc372a75
  DataManifest      b21c975a51ef24cdfb2078957f0e0e4b2fb194e7c55b3a8058febb019d214a21
  Config            550ca3cdd8af04ec0895a2515bbee40a9627b805d5477611995f4cef0f4043ac
  MetricDefinition  420ab0acf24e1c7325b089e2ec4bc6c3d074119c4f3ac8aac8ed3cfa1c45bfc0
```

* `EvaluatorSource` 只覆盖 `{e_star.py, e_star_child.py}`。上游的 `scripts/local_eval.py` **不是**冻结评测器：它与 runtime 实际加载的 plugin 差 1 ULP（补偿求和 vs 循环累加），且表达不了 `invalid`/`error`。早期一次错误冻结（`fac50fc4…`，哈希了 `local_eval.py`）已被更替。
* 验收：五项各有可复算哈希；单项输入变更只改对应分量与 `EID*`；文档内无绝对路径、无 mtime 依赖；`verify`/`recompute` 均在重新冻结后的文档上通过（契约测试 83 通过 + 1 跳过）。

### 3.2 `E*` 与 `C*`

* 目标函数 `sum_radii` over `pack_circles(26)`，语义取自上游 `loreley.program.md:7-10` 与 `examples/circle_packing_env/evaluate.py:133-145`。
* `C*` 共 14 个：5 个 `ok`、4 个 `invalid`、5 个 `error`。最大—最小的可判定间隔 = **2.2019205208433132**；另含一对**位相同但内容不同**的并列候选（`c01`/`c03`）与一对近并列（Δ = 1.0000000000021e-4）。
* `E*` 已验证对 cwd / `PATH` / 文件位置不敏感，且跨重跑逐字节稳定（含在真实 git worktree 上做 `git checkout -- . && git clean -xfd` 后重跑一致）。
* 一个刻意保留的陷阱：`c05_overlapping` 的**名义** `structure.sum_radii` 等于最高分候选，但它是 `invalid` ⇒ 标量为 `null`。从 `structure` 取数会精确复现假绿。

### 3.3 A0.1 / A0.2 判定

| runtime    | A0.1                            | A0.2             | 说明                     |
| ---------- | ------------------------------- | ---------------- | ---------------------- |
| SimpleLoop | PASS 14/14                      | PASS 9/9         | 并列/近并列/顺序不变性均验         |
| KAPSO      | PASS 14/14                      | PASS 14/14（5 场景） | 含 `fast_only` tier 对照  |
| EvE        | **PASS 5/14 measured** + 9 声明合成 | PASS（频率检验）       | 见下                     |
| Loreley    | PASS 14/14                      | PASS 7/7         | 同 cell 替换 + 跨 cell 负对照 |

**A0.1 记成三元组 `(passed, measured, total)`，不是布尔。** EvE 的 lane 把任何评测异常静默映射为 `failure_score 0.0`，**根本无法表达 `invalid`/`error`**；那 9 行是适配层**声明**的合成失败（runner 标签 `SYNTHETIC_DECLARED`），不是复现。正确引法是 `A0.1 = 5/14 measured`，写成"14/14 一致"就是夸大。

**A0.2 的要点**：

* KAPSO：置 `E(c1) > E(c2)`，下一轮父代、deliverable、`checkout_to_best_experiment_branch()` 均翻到 `c1`；`fast_only` 对照显示高分 fast 候选能当父代但拿不到 deliverable（tier 优先于分数）。另记录一处**声明分歧**：KAPSO 的 tie-break 是 `node_history` 上的 `max()`（依赖提案顺序），只在"字节序最小的候选恰好先提案"时与冻结规则一致；反序探针显示分歧。**现有 A0.2 断言并没有区分两者**，不能引用它当作"建立了冻结 tie-break"。
* EvE：频率检验。`P(c1) = 1/(1+e^-1) = 0.7310585786` 仅对 `RankSoftmaxSampler`、k=2、T=1、单次抽样成立；`solver_examples` 用 `RankExponentialSumSampler`（n=4、`no_replacement`），期望须单独推导（N=4 → 0.6439143，N=3 → 0.6652409）。合并 18 000 抽得 p̂ = 0.7290（z = −0.62）；分数载荷互换对照 0.754 → 0.263（两比例 z = 31.1）。预注册样本量 46/295/515，实际重算 44/289/496，取 600+。
* Loreley：同 cell（相同 `measures`）替换成立且 `c02` 被移出；跨 cell 高分不淘汰。**协议"无全局 argmax 保证"在默认单目标下不成立**——每个 cell 前沿恒为 1，archive 就是 per-cell argmax；跨 cell 负对照需要多目标配置才有区分力。

### 3.4 可记账性

四套 runtime 现在声明**同一张**冻结映射表，`FailureStage` 计数可相加，均等于
`{none:5, verify_failed:5, resolve_failed:1, evaluator_failed:2, timeout:1}`（14 单元，一候选一单元）。
合并流 `<runtime>.<run_id>.all.jsonl` 是校验单元（旧的按文件校验有缺陷，会让每条 selection 事件报错）。

Trace 路径（注意 KAPSO 没有顶层 `traces/`）：

```
a0/runtimes/kapso/runs/a0-01/a01/traces/kapso.a0-01-a01.{score,resource}.jsonl
a0/runtimes/kapso/runs/a0-01/a02/traces/kapso.a0-01.{score,selection,resource}.jsonl
a0/runtimes/eve/out/run001/traces/eve.eve-a0-run001.{score,selection,resource}.jsonl
a0/runtimes/loreley/out/run-a0/traces/loreley.lor-a0.{score,selection,resource}.jsonl
a0/runtimes/simpleloop/out/main/traces/simpleloop.main.{score,selection,resource}.jsonl
```

### 3.5 汇合层

`a0/conformance/` 是唯一能判 A0.1 的组件：以冻结 CLI 驱动每个 adapter，先校验 `solution_sha256`，再对 `E*` 冻结表比较，并比较 `status` **+ `failure.kind` + 派生的 `failure_stage`**。共 **19 个注入故障 + 1 个诚实对照**。四套均 PASS，`failure_stage_accounting.matches_frozen_map = true`（各 14 单元）。

## 4. 独立对抗审计的结论

`a0/verify/`（审计者用**自己重写的** `EID*` 实现、自己重跑 conformance、自己伪造说谎 adapter）首轮 31 条 claim：**27 ACCEPTED / 3 REJECTED / 1 UNPROVEN**。

三条被驳回、现已修复并复核：

1. **R1（高危）计算器本身有假通过漏洞**：conformance 只比较候选 `status`，从不读 `failure.kind`。审计者造了一个"status 诚实、`failure_kind` 全错"的 adapter，runner 竟返回 `PASS: all checks passed`（exit 0）。而契约 §4.5 明确要求 `status` + `failure.kind` + 派生阶段三者一致——否则"每个失败都归错类"的 runtime 能通过 A0.1，其计数还会污染 §4.4 的失败记账。修复后同一 adapter 返回 FAIL（`FG-FAILURE-KIND`）；补了 2 个永久 fixture（含"漏报 `failure.kind` 也算失败"，这条由我本人复现：`FG-FAILURE-KIND-UNDECLARED`，exit 3）。
2. **R2**：SimpleLoop 的文档声称契约文档仍带着被替换的 `EID*`——不实（契约自 16:57 起就是 `664115e0…`）。已更正，并确认任何机器可读产物从未携带该错值。
3. **R3**：EvE 的 `EID_r` 只是**它自己生成脚本的 sha256**，没有任何东西强制它从 `EID*` 派生——一个完全忽略 `EID*` 的脚本也能同样复算。已改为把 `eid_star` 作为哈希入参，并给出四路变异证据（改一位 nibble 即变值、字节被改则拒算）。

另有 2 条 finding（KAPSO `theta_E` 里一个误导性的 identity key；runner 对 KAPSO 的 manifest echo 误报为不可用）也已修复。

链上真实模型轮次的证据（端到端，非机制级）：KAPSO 一轮已验证（分数 `2.451820520843313`，与独立 `E*` 一致）；SimpleLoop 两轮（`2.6251746109048`、`2.5414213562373096`，冠军因真实分数而改变）；EvE 走到真实模型对话并产出被 `E*` 测为 `2.6168716968517516` 的工件，但未完成写回；Loreley 规划阶段已验证、编码阶段在 480 s 预算内超时。

## 5. 运行环境与 lane 现状（含一处我们做错又更正的结论）

### 5.1 环境（**软件已更新，版本是新的**）

| 组件                          | 版本                                  |
| --------------------------- | ----------------------------------- |
| claude                      | **2.1.278**（本审计开始时是 2.1.260）        |
| codex                       | **0.155.1**（原 0.154.0）              |
| opencode                    | v2.0.11                             |
| kilo                        | 7.7.5                               |
| node / python / docker / uv | v26.8.2 / 3.14.7 / 29.8.0 / 0.12.13 |

GPU：RTX 3050，6 GB 显存（4.8 GB 空闲）；**容器内无 GPU**（仅 `runc`，无 nvidia-container-runtime）。这条决定"本地模型"路线的上限，而它此前**不在我们的环境证据集里**（已补）。

### 5.2 模型接入（决定：`deepseek-flash` 为主，允许混合使用 `deepseek-v4-pro`，**OpenRouter 不使用**）

DeepSeek 同时提供两种协议面：

* OpenAI 兼容 `https://api.deepseek.com`（`/models` → `deepseek-flash`、`deepseek-v4-pro`）
* Anthropic 兼容 `https://api.deepseek.com/anthropic/v1/messages`（返回标准 Messages 结构，**tool use 可用**）

### 5.3 一处必须更正的错误结论

我们曾判定 **codex 必须退役**，理由是"codex 只支持 OpenAI Responses API（`wire_api=\"chat\"` 已移除），而两家可用 provider 都不提供 Responses"。

**这个结论是错的，而且升级前就已经错了。** 实测：`POST https://api.deepseek.com/v1/responses` → **HTTP/2 200**，返回完整的 response 对象（`object:"response"`、`status:"completed"`、`output[]`、`usage.input_tokens_details`）。codex 能端到端驱动它：最小调用、含 `apply_patch`+shell 的**工具循环**（文件系统已验证）、EvE 风格的 `-c model_providers…` 注入 + 空 `CODEX_HOME`、`resume --last` 全部 exit 0。对 0.154.0 做同样实测**也能用**——所以上一轮的错判不是版本问题，而是**探针从没试过 `/responses`**（只试了 `/models` 与 `/chat/completions`）。

保留的正确部分：`wire_api = "chat"` 确实仍被硬拒；0.155.1 的 `--help` 与 0.154.0 逐字节相同；codex 只提供 `responses` 一个合法值。

**这条更正改变了方案**：codex 重新可用意味着 KAPSO 的 **codex lane**（它是**唯一**带 lane 级 sandbox 参数的通道，`agent_specific.sandbox`）与 EvE 的**出厂 driver**（`codex_exec`/`codex_tmux`）重新成为首选，而 opencode 那条"需要改 EvE 三处代码"的路降为备选。

### 5.4 四条可用通路

| runtime    | 通路                                                      | 改动量                   | 关键前提 / 已知代价                                                                                                                |
| ---------- | ------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| KAPSO      | `claude_code`/`oss_claude_code` → DeepSeek `/anthropic` | **纯配置**               | 必须 `CLAUDE_CONFIG_DIR` 隔离；块里必须显式 `type:`；pin `deepseek-flash`                                                              |
| KAPSO      | `codex` lane → DeepSeek `/v1`                           | **纯配置**               | 唯一带 sandbox knob 的通道；每次调用有 `Model metadata for deepseek-flash not found` 警告                                                |
| EvE        | `codex_exec` / `codex_tmux`                             | **零改动**               | `codex_exec` 硬编码 `--dangerously-bypass-approvals-and-sandbox`，不可配置封闭；`codex_tmux` 可以（实测 `workspace-write` 连 `socket()` 都禁） |
| EvE        | `opencode`（MIT，随附）                                      | **需改 EvE**（3 处）       | v2.0.11 拒绝 `--dir`；JSON 流字段变了（`part.id` 与终止 reason `tool-calls`）；守护进程端口固定 49374 会顶掉并发                                      |
| Loreley    | `kilo`（MIT，其默认后端）                                       | 配置级 **+ 15 行 pin 补丁** | 种子组合的模型名检查在**两处**（`preflight.py:397`、`scheduler/seed_portfolios.py:147`）                                                   |
| Loreley    | `codex_cli`                                             | 配置级                   | 会替换 `CODEX_HOME`，需显式补 `model_provider`                                                                                     |
| SimpleLoop | 可插拔                                                     | 我们自己的代码               |                                                                                                                            |

**KAPSO 的 claude 配方（2.1.278 上逐条复验成立）**：`~/.claude/settings.json` 的优先级**高于**进程环境（实测：进程环境指向 mock，CLI 完全无视，真实调用打到 settings 文件里的端点），`--model` 又高于 settings；`CLAUDE_CONFIG_DIR` 能整体搬迁配置与状态，且空目录启动无需 onboarding。KAPSO 从不设这两个变量，所以必须由启动方导出。另有一个陷阱：`preflight.resolve_cli` 是 `"claude_code" if model.startswith("claude") else "codex"`，所以 `model: deepseek-*` 不写显式 `type:` 会**回退到 codex lane**。

### 5.5 封闭性：从"依赖 CLI sandbox"升级为"拓扑构造"

模型在远端，所以早先"把本地模型塞进 `unshare -rn`"的办法失效（该命名空间**没有上行链路**）。现方案：`docker network create --internal` + **双宿主白名单代理**（同挂 internal 与 bridge），agent 与候选代码都在 internal 侧。

实测结果：

* 两对照均执行：internal 侧访问公网 IP 全部 `Network is unreachable`、访问代理名 `HTTP 200`；bridge 侧 OPEN（证明屏障**选择性**存在，不是网络坏了）
* Docker 内嵌 DNS 在 `--internal` 网络内**能解析容器名**（只有向外部转发才 `gaierror`）
* **三套 CLI 都在封闭网络里完成了真实 DeepSeek 轮次**
* 一个监听同时转发 Anthropic Messages 与 OpenAI Chat 两种上游形状；建议主控用"`base_url` 指向代理的明文 http"（显式、失败报错清楚、key 不必下发到客户端），`HTTPS_PROXY` 作纵深

残余缺口（不掩饰）：代理是**可信软件**（白名单是 Python，不是内核规则）；宿主可直连容器 IP 绕过；只验了文本轮次，未验完整工具轮；Loreley 的 worker 目前跑在宿主用发布端口，要搬进网络才能让它那条通道也关上（PG/Redis 同网络按容器名寻址已验证可行）。另外：现在 codex 可用了，CLI 自身 sandbox 重新成为**第二条**可用机制，两者互补。

## 6. 仓库状态

* `main`，14 个 commit，标签 `a0-audited`，工作区干净（未提交 0）
* **20,025 个跟踪文件 / 156.9 MB 内容 / `.git` 11 MB**（EvE 频率检验的 trace 占大头，压缩比约 17×）
* 无 remote —— 这份历史只在本机；要长期留存需 `git bundle` 或推远端
* 历史是**按里程碑分组重建**的（当时是多个并行 agent 各占目录，逐文件时间交织不可还原），不是过程实时捕获
* 忽略项（已验证规则）：venv/缓存/`__pycache__`；固定的上游检出（`tasks/circle-packing/upstream/`、`runtimes/loreley/checkout/`，版本 pin 记录在 `EID_INPUTS.json`）；合并流 `*.all.jsonl`（校验器可重组）；物化工作树 `workspace/`、`worktree/`、`.repo_cache/`；审计者的逐字节副本；探针遗留的 `*-work/` 临时仓库

关键文件（均已跟踪）：
`contract/out/plumbing.EID.json`（25 KB）· `contract/SPEC.md`（25 KB）· `contract/adapter_contract.md`（59 KB）· `tasks/circle-packing/e_star.py`（35 KB）· `C_STAR/manifest.json` · `E_STAR.json`（161 KB）· `conformance/report.json`（226 KB）· `closure/VERDICTS.md`（24 KB）· `verify/VERDICT.md`（41 KB）· `verify/verdicts.json`（70 KB）

## 7. 成本与归因

* 三个 CLI 报的成本**都不可信**：claude 的 `total_cost_usd` 对 DeepSeek 用 Anthropic 价目表，实测高约 10–20×（报 $0.651，实际 $0.058）；kilo/opencode 一律报 `$0`/`unpriced`（Loreley 的 `pricing.py:69-74` 在 `source == "kilo_cli"` 时提前返回，`LLM_USAGE_PRICING_JSON` **无法**补救）。→ 只能按 token 数配 DeepSeek 价目表自己算。
* **模型身份存在一个未解决的不一致**：Anthropic 面回报的服务模型是 `deepseek-v4-flash`，而 OpenAI 兼容面**回声请求里的 id**。也就是说**回声 ≠ 证明谁在回答**。每个 lane 的实际模型身份必须单独记录并冻结（与 `EID*` 同级），否则 A1 的 Δ 无法归因。
* 本轮全部验证花费约 $0.5。

## 8. 承认的错误与未验证项（诚实清单）

**已承认并更正的错误**

1. `codex` 退役判定 —— 如上，探针漏试 `/responses`，结论错。
2. 早期一次 `EID*` 冻结错了对象（哈希 `local_eval.py` 而非 `e_star.py`）。
3. 审计者首轮驳回的三条（§4），其中一条是**计算器本身的假通过漏洞**。
4. `LLM_USAGE_PRICING_JSON` 能定价 kilo 事件的假设 —— 实测不能。
5. 种子组合 pin 只在 `preflight` 一处 —— 实际两处，只补一处会让 campaign 中途死掉。
6. 我们的 `ENV_REPORT` 从未测量 GPU，因此漏掉了决定"本地模型"可行性的 6 GB 上限。
7. 一个 agent 曾把配置备份里的 `sk-…` 片段打进自己的工具输出（已告知用户轮换）。

**未验证 / 只做到部分**

* A0.1/A0.2 的核心判定是在模型 lane 不可用时用**文档化 seam**完成的；文档化的分界是"机制级已验证"与"端到端未验证"。
* 端到端（真 LLM）：KAPSO 一轮、SimpleLoop 两轮已验证；EvE/Loreley 未跑完一整轮写回。
* 审计者的"无 mock 替换"检查是**词法级**的，非穷尽。
* Loreley 的 `EvolutionWorker` 缓存编排、KAPSO 的无 seam campaign 循环、EvE 的 provider 侧 `web_search` 均未验证。
* 两条 `EID_r` 复算在 conformance 里是 `declared_prose` 而非可执行复算（EvE、SimpleLoop；KAPSO/Loreley 是独立重算）。
* codex 侧：`resume` 打印了**新的** session id，跨轮上下文保持**未验证**；只测过极小请求，18–20k token 的长 prompt 与长 campaign 未测。

## 9. 待决策项

1. **模型 pin**：`deepseek-flash` 为主已定；`deepseek-v4-pro` 作为校准/对照臂的触发条件待定。
2. **EvE 走哪条**：codex 已可用 ⇒ 出厂 driver 零改动（但 `codex_exec` 不可配置封闭）；或走 opencode（需改 3 处，但 driver 不提供 sandbox）。
3. **Loreley 的 15 行 pin 补丁**是否落地（不做就避开种子组合 lane）。
4. **封闭性拓扑是否固化进 `a0/env/`** 并重测三套 lane（把 CONDITIONAL 换成构造性封闭）。
5. **A1 的任务选择与预算口径**（`B_hard = (T_wall, N_evaluatorCalls, concurrency cap)`），以及正对照（复用于检测"模型太弱导致 substrate 看起来无效"的假阴性）。
6. **清理**：`~/.claude/settings.json` 仍含明文 key 与一个自称过期的模型别名（我们未改）；`~/gptapi.md` 的明文 key 已进入会话记录；探针遗留容器 `a0pc-{proxy,cli,pg,redis}` 与网络 `a0pc-internal` 仍在运行（附 `teardown.sh`）。

## 10. 请重点审查的十个问题

1. **`EID*` 的设计是否足以冻结"评测器身份"？** 五分量（源码树、依赖锁、数据清单、配置、指标定义）是对的吗？有没有"改了却哈希不到"的输入（例如运行时实际加载的 plugin 与哈希的源码树不一致）？
2. **A0.1 记成 `(passed, measured, total)` 是否为正确的弱化？** 把 EvE 那 9 行"声明合成"纳入 PASS 并标注 `5/14 measured`，是否仍然高估了它？是否应该直接判 EvE 在这一项 FAIL？
3. **EvE 的 A0.2 统计是否站得住？** sampler 的 RNG 未播种，把 18 000 次抽样合并跨轮是否合法？"位置 0 频率"作为选择语义的可观测替代物是否有效？预注册样本量（46/295/515 vs 重算 44/289/496）是否够？
4. **KAPSO 的 A0.2 有多少建立在 seam 上？** 5 个场景跑在真实 KAPSO 工作区里，但候选与分数的注入是接缝；只有一轮真实 LLM 端到端。这足以支撑 A0.2 的结论吗？
5. **封闭性判定是否达标？** 协议要求"用探针证明"；我们的答案是一个**可信的 Python 白名单代理**，且宿主可绕过。这算不算把"配置级封闭"换成了"软件级封闭"？
6. **假绿目录是否还有缺口？** 已覆盖：EvE 静默 `0.0`、Loreley 超时/64 指标截断/缓存复用、KAPSO 的（伪）manifest 三元组、`c05` 名义值陷阱。有没有一种失败是**分数天然一致**因而永远通过 A0.1 的？
7. **归因是否可成立？** 在"回声 ≠ 证明模型身份"、lane 可配置、seam 存在的前提下，要让 A1 的 Δ 可归因，必须冻结哪些东西？（我们目前冻结了 `EID*`、`F_r`、`C*`、trace 契约与每轮的 adapter 源码摘要。）
8. **`|R_1| ≥ 1` 这个"候选筛选而非集体门"的框架，有没有在我们的结论里被滥用？** 例如以"其余三套通过"为由淡化 EvE 的 measured 缺口。
9. **别人能否从仓库独立复现？** 上游版本 pin 记录在 `EID_INPUTS.json`，但源码快照本身不在仓库内（按约定放 `/tmp`，会被重启清空）。这对可复现性是可接受的取舍吗？
10. **最强的反驳**：请给出"整轮 A0 是不必要的或规格有误"的最有力论证——如果 A0 的产物对 A1 的判断其实不构成约束，我们该怎么重新设计这一步？
