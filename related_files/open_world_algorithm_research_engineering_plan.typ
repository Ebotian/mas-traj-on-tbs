
#set page(
  paper: "a4",
  margin: (x: 24mm, y: 22mm),
  numbering: "1",
)
#set text(
  lang: "zh",
  font: ("Noto Sans CJK SC", "Noto Sans"),
  size: 10.5pt,
)
#set par(justify: true, leading: 0.72em)
#set list(indent: 1.2em, body-indent: 0.55em)
#set enum(indent: 1.2em, body-indent: 0.55em)
#show link: set text(fill: rgb("#1f5d8f"))
#show raw.where(block: true): set block(
  fill: rgb("#f5f6f7"),
  inset: 9pt,
  radius: 4pt,
  breakable: true,
)

#align(center)[
  #text(size: 22pt, weight: "bold")[开放世界算法自动改进基础设施]
  #v(5pt)
  #text(size: 15pt, weight: "semibold")[工程与研究计划]
  #v(7pt)
  #text(size: 10pt)[Open-World Infrastructure for Automated Algorithm Improvement]
  #v(12pt)
  #text(size: 9.5pt)[版本：v1.0 · 2026-09-18]
]

#v(12pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *计划定位*：本计划不是 ADA、OPL、Kimi 插件或某一“Research OS”的建设计划。上述对象均视为可替换的实现手段。唯一稳定目标为：

  $ G_0 = "使真实算法研究更适合 AI/Agent 自动、可靠、长期地推进，并持续产生可验证的算法改进。" $

  工程决策遵循：

  $ "research need" -> "existing solution search" -> "composition" -> "adapter/configuration" -> "extension" -> "new implementation". $

  即：优先货架式方案；架构可丢弃，研究能力保持不变。
]

= 执行摘要

本项目最初从“研究过程运行契约、Agent 长程执行、实验编排、记忆、插件、范畴论式关系建模”等基础设施问题出发，曾分别形成 ADA（环境侧）与 OPL（Kimi Code Agent/插件侧）的实现设想。随后研究逐步暴露出一个代理目标风险：若持续优化 ADA/OPL 自身，目标会从“提高真实研究能力”漂移为“提高基础设施完整度”。

因此，本计划重新以“自动化算法改进”为中心，并将已有系统拆解为可替换能力组件。经过对 Kimi Code 插件机制、AgentCo-Op、Man1Lab、ShinkaEvolve、ASI-Evolve，以及 Dream-RSI、DGM/HGM/MGM、AHE/HarnessFix、SGM/RQGM 等 RSI 方向的调研，当前最重要的工程认识为：

#enum(
  [*开放世界获取（open-world acquisition）已有相当成熟的实现基础。* Man1Lab 当前源码已实现 Collection → Evidence → Verification → Ranking → Selection，并进一步实现 Strategy → Binding → Reuse → Adaptation → Generation → Risk。],
  [*算法进化（algorithm evolution）已有成熟底座。* ShinkaEvolve 已具备 program lineage、archive inspiration、top-k inspiration、islands、异步评估、SQLite archive、多模型 provider 等机制。],
  [*真正缺失的不是一个新的 Research OS，而是二者之间的桥。* 即把“外部已验证实现”转换为“可执行、可追踪、可作为 evolutionary inspiration 的研究对象”。],
  [*第二个真正开放的问题是策略问题。* 当内部进化停滞时，Agent 何时应搜索开放世界？何时直接复用？何时 cross/adapt？何时继续内部 evolution？],
  [*RSI 不应从第一天就全开。* 应先积累真实算法研究轨迹，再逐步优化 skill retrieval、search policy、harness 与 evaluator challenge。]
)

故第一阶段不建设“大而全基础设施”，而验证一个最窄、可证伪的垂直切片：

$
"Discovery"
-> "ExternalInspiration"
-> "Evolution"
-> "Frozen Evaluator".
$

核心研究问题为：

$ Q_1: "Can verified external implementations become first-class evolutionary inspirations?" $

以及第二阶段：

$ Q_2: "When should an algorithm research agent search the world rather than continue evolving internally?" $

= 一、探索历程与问题收敛

== 1.1 初始阶段：研究基础设施问题

早期目标是支持长流程 AI4Sci / algorithm research，关注：

- 研究过程运行契约（runtime contract）；
- Agent 长程自主执行；
- 实验单元的程序化编排；
- durable memory / provenance；
- 工具、环境、权限与事实能力的显式建模；
- 多 Agent / swarm 候选探索；
- 研究过程中的验证、审查、失败恢复；
- 关系优先、category-first 的实验组织方式。

工程上曾形成：

$
"ADA" approx "environment/infrastructure layer",
$

$
"OPL" approx "Kimi Code agent/plugin layer".
$

二者被设想为解耦仓库，通过稳定接口通信。

== 1.2 关系优先与 OOE 反思

实验组织曾考虑 object-oriented experiments（OOE）。但经典 OOP 长期实践中的问题——继承膨胀、超级对象、依赖链耦合、隐式生命周期——在实验系统中同样可能发生。

因此逐步形成：

$
"Experiment" != "large mutable object",
$

而更偏向：

$
"Research state" = "typed entities" + "typed relations" + "transformations".
$

分析上形成双图：

$
G_E = (V_E, E_E)
$

表示 epistemic graph：Question / Hypothesis / Claim / Evidence / Observation；

$
G_O = (V_O, E_O)
$

表示 operational graph：Experiment / Task / Tool / Run / Artifact。

二者通过 typed bridges 连接，例如：

$
"hypothesis" ->^"testedBy" "experiment",
$

$
"run" ->^"produces" "observation".
$

此模型仍保留为分析工具，但不再要求实现一个统一巨型 Research IR。

== 1.3 Search-before-Build 原则形成

对 CWL、WorkflowHub、PROV、RO-Crate、Workflow Run RO-Crate、插件生态等已有基础设施的调查显示，大量“看似需要自己实现”的能力已经存在。

因此形成稳定工程顺序：

$
r
-> "existing solution search"
-> "composition"
-> "adapter"
-> "extension"
-> "new implementation".
$

同时确立：

$
"Architecture is disposable; research capability is invariant."
$

这是本计划最重要的约束之一。

== 1.4 从一般自动科研收敛到算法改进

进一步明确研究对象不是“自动写论文”或一般 autonomous science，而是：

$
A_t -> A_(t+1),
$

其中每次改进必须经过真实 evaluator。

算法研究任务表示为：

$
T = (P, D, M, B, C),
$

其中：

- $P$：问题（problem）；
- $D$：数据/环境（data/environment）；
- $M$：指标（metrics）；
- $B$：baseline；
- $C$：硬约束（constraints）。

单次候选实验：

$
e_i = (h_i, delta_i, theta_i, s_i, r_i),
$

分别表示 hypothesis、algorithm/code delta、configuration、seed/split、result。

优化目标不是“完成报告”，而是：

$
"maximize verified Pareto improvement under constraints".
$

== 1.5 RSI 调研带来的第二次修正

随后对 AlphaEvolve / ShinkaEvolve / OpenEvolve、Dream-RSI、Darwin Gödel Machine、Huxley Gödel Machine、Mendel Gödel Machine、AHE、HarnessFix、RobustSGPO、Statistical Gödel Machine、Red Queen Gödel Machine、SE-GoS、MetaRSI 等方向进行了系统调查。

由此形成多坐标 RSI 视图：

$
X_t = (A_t, pi_t, H_t, K_t, E_t, T_t),
$

其中：

- $A_t$：目标算法；
- $pi_t$：研究/搜索策略；
- $H_t$：Agent harness；
- $K_t$：skills / experience；
- $E_t$：evaluation system；
- $T_t$：trajectory/archive。

重要结论：这些坐标不能同时快速变化，否则无法归因。

故采用多时间尺度：

$
tau_A < tau_K <= tau_pi < tau_H < tau_E.
$

即优先改算法；积累轨迹后再改检索与搜索策略；再后才改 harness；evaluator anchor 原则上冻结。

== 1.6 最新源码下钻：问题进一步缩小

最新源码级检查带来关键收敛。

*Man1Lab* 已实际实现：

$
"Collection"
-> "Evidence"
-> "Verification"
-> "Ranking"
-> "Selection",
$

以及：

$
"Strategy"
-> "Binding"
-> "Reuse"
-> "Adaptation"
-> "Generation"
-> "Risk".
$

其规则已经显式包含：

`RULE_REUSE`, `RULE_OFFICIAL_USABLE`, `RULE_COMMUNITY`, `RULE_HYBRID`, `RULE_GREENFIELD`。

因此 Search-before-Build 不需要重新发明。

*ShinkaEvolve* 的 `Program` 已包含：

- `parent_id`；
- `archive_inspiration_ids`；
- `top_k_inspiration_ids`；
- `island_idx`；
- `generation`；
- `code_diff`；
- public/private metrics；
- correctness；
- complexity；
- embedding；
- metadata；
- archive status。

故 evolutionary substrate 也不需要重新发明。

真正断裂点为：

$
"CandidateResource"
-> ?
-> "Program / Inspiration".
$

由此得到当前核心工程对象：

$
#box(stroke: 0.6pt, inset: 4pt)[ExternalInspiration Adapter].
$

= 二、现今问题模型

== 2.1 总体目标

定义系统能力：

$
G_0 =
"在固定 evaluator 与资源约束下，以尽可能低的研究成本持续发现、验证并积累算法改进。"
$

效用近似：

$
J =
frac(Delta "VerifiedAlgorithmCapability", "compute" + "LLM cost" + "wall time" + "human intervention" + "maintenance").
$

任何基础设施工作必须能说明其对 $J$ 的正向作用。

== 2.2 Closed-world 与 Open-world

传统 evolutionary research：

$
Omega_t = {A_0, A_1, ..., A_t}.
$

Agent 只能利用自己的历史候选。

开放世界后：

$
Omega'_t =
Omega_t
union
R_t,
$

其中 $R_t$ 为从论文、GitHub、文档、已有实现、算法组件等获取的外部知识与实现。

关键不是简单增加 context，而是使外部实现进入可验证的研究循环：

$
R
-> "verify"
-> "understand"
-> "adapt/cross/reuse"
-> "evaluate"
-> "archive".
$

== 2.3 当前核心缺口

现有能力可粗略分为：

#table(
  columns: (1.2fr, 1.5fr, 2.5fr),
  inset: 5pt,
  stroke: 0.4pt,
  [*能力*], [*主要现成实现*], [*当前判断*],
  [开放世界资源发现], [Man1Lab], [已有较完整实现，应复用],
  [外部仓库可执行包装], [AgentCo-Op / sandbox adapter 思路], [可借其 typed executable component 设计],
  [算法进化], [ShinkaEvolve], [成熟，首选实际实验底座],
  [搜索策略实验], [ASI-Evolve], [结构简单，适合研究 policy],
  [trajectory replay / policy RSI], [Dream-RSI], [机制重要，但完整源码尚非稳定依赖],
  [统计提交门], [SGM 思路], [应尽早吸收],
  [harness diagnosis/evolution], [HarnessFix / AHE], [待真实轨迹积累后使用],
)

故当前真正缺失：

$
pi_"bridge":
"ResearchState"
->
{
"SearchExternal",
"ReuseExternal",
"CrossExternalInternal",
"ContinueInternalEvolution"
}.
$

= 三、目标系统边界

== 3.1 非目标

首版明确不做：

- 不建设新的通用 workflow engine；
- 不建设新的 provenance 标准；
- 不建设新的 vector database；
- 不重写 ShinkaEvolve；
- 不重写 Man1Lab Discovery；
- 不追求统一所有 research objects；
- 不在第一阶段实现 full RSI；
- 不把 ADA/OPL 完整度作为里程碑；
- 不因“架构漂亮”而引入组件。

== 3.2 第一阶段系统边界

首版只实现：

$
"OpenWorldDiscovery"
-> "ExternalInspiration"
-> "EvolutionarySearch"
-> "Evaluator"
-> "ExperimentLedger".
$

逻辑图：

```text
                 OPEN WORLD
                     |
                     v
          +----------------------+
          | Discovery / Verify   |
          | (Man1Lab-oriented)   |
          +----------+-----------+
                     |
              CandidateResource
                     |
                     v
          +----------------------+
          | ExternalInspiration  |
          | Adapter              |
          +----------+-----------+
                     |
            +--------+--------+
            |                 |
            v                 v
        direct reuse       inspiration
            |                 |
            |                 v
            |       +-------------------+
            |       | ShinkaEvolve      |
            |       | archive/islands   |
            |       | mutation/cross    |
            |       +---------+---------+
            |                 |
            +--------+--------+
                     v
               Frozen Evaluator
                     |
                     v
              Experiment Ledger
```

= 四、组件工程决策

== 4.1 Man1Lab：开放世界 acquisition front-end

采用其已有阶段模型：

$
C -> E -> V -> R -> S
$

即 Collection、Evidence、Verification、Ranking、Selection。

进一步借用其：

$
"Reuse" > "Adapt" > "Generate"
$

决策思想。

但必须保持边界：Man1Lab 原始目标偏向 paper reproduction，其 generation policy 有意限制 algorithm redesign；本项目不能把该限制直接继承到 improvement loop。

因此定位为：

$
#box(stroke: 0.6pt, inset: 4pt)[Man1Lab = acquisition/reference implementation, not research optimizer].
$

首版优先方式：

1. 直接复用其 schema/decision ideas；
2. 若依赖成本合理，直接调用其 discovery 输出；
3. 若耦合过重，则只写薄 adapter，不 fork 其内部架构。

== 4.2 AgentCo-Op：typed executable component 参考

AgentCo-Op 当前 generic skill retrieval 本身较简单，主要为 keyword/tag scoring；不将其作为主 Discovery engine。

但其 typed IR 值得吸收：

- TaskProfile；
- NodeSpec；
- EdgeSpec；
- GatePolicy；
- EvalContract；
- MemoryPlan；
- `sandbox_repo` backend。

尤其保留：

$
"external repository"
-> "typed executable node".
$

是否实际引入 AgentCo-Op dependency，以首批外部仓库的包装复杂度决定。

== 4.3 ShinkaEvolve：首选 evolutionary substrate

首版直接使用其：

- Program archive；
- lineage；
- island model；
- parent selection；
- archive/top-k inspiration；
- async evaluation；
- model providers；
- metadata；
- SQLite persistence。

不修改核心算法，优先从 adapter 注入 external inspiration。

首版允许：

```text
Program.metadata.external_sources
Program.metadata.discovery_id
Program.metadata.source_commit
Program.metadata.license
Program.metadata.external_mechanisms
Program.metadata.adaptation_record
```

若实验验证 external inspiration 确有价值，再考虑把 `external_inspiration_ids` 升为一等字段。

原则：

$
#box(stroke: 0.6pt, inset: 4pt)[adapter first, schema later].
$

== 4.4 ASI-Evolve：policy research substrate

不进入首版 production path。

其价值在于 sampler 明确模块化：

$
"Sampler": "Nodes" -> "SelectedNodes".
$

已有 Random / Greedy / UCB1 / Island，可用于第二阶段把动作空间扩成：

$
A =
{
"Search",
"Reuse",
"Cross",
"Evolve"
}.
$

== 4.5 Dream-RSI：未来 meta-policy 层

吸收其思想：

$
pi_t
-> H_t
-> "ReplayWorld"
-> pi_(t+1).
$

但在稳定公开源码与接口成熟前，不作为首版依赖。

本项目从第一天开始保留 replay 所需轨迹，避免未来无法重放。

= 五、核心数据契约

== 5.1 Task Contract

每个算法任务必须先冻结：

```yaml
task:
  problem: ...
  baseline:
    command: ...
    expected_metric: ...
  evaluator:
    command: ...
    direction: maximize
  constraints:
    online_information_only: true
    max_wall_time_s: ...
    max_memory_mb: ...
  statistics:
    seeds: [11, 23, 47, 89, 131]
    confidence: 0.95
  objectives:
    primary: score
    secondary:
      - runtime
      - memory
```

Task Contract 一经 campaign 开始，不允许 Agent 静默修改。

== 5.2 ExternalInspiration

首版 canonical adapter object：

```text
ExternalInspiration {
  id

  source {
    uri
    repository
    commit
    license
    discovered_at
    discovery_id
  }

  evidence {
    official
    verified
    verification_records[]
    confidence
  }

  semantics {
    mechanism_summary
    assumptions[]
    relevant_files[]
    reusable_components[]
  }

  execution {
    runnable
    wrapper
    dependencies
    expected_inputs
    expected_outputs
  }

  adaptation {
    compatibility
    estimated_cost
    required_changes[]
    forbidden_changes[]
  }

  provenance {
    evidence_refs[]
    content_hashes[]
  }
}
```

其职责不是保存整个 GitHub，而是：

$
"Resource"
-> "minimal verified actionable representation".
$

== 5.3 Experiment Record

```text
ExperimentRecord {
  experiment_id
  parent_ids[]
  external_inspiration_ids[]

  hypothesis
  code_commit
  code_diff
  config_hash
  dataset_hash
  environment_hash

  seed
  command
  start_time
  end_time
  exit_status

  raw_metrics
  normalized_metrics
  constraint_checks

  artifacts[]
  logs

  agent
  model
  token_cost
  compute_cost

  validity
  statistical_decision
  verdict
}
```

关键语义：

$
"failed hypothesis" != "invalid experiment".
$

失败但有效的实验必须进入 archive。

== 5.4 Trajectory Event

为未来 Dream-RSI / HGM / MGM / AHE 保留：

```text
TrajectoryEvent {
  timestamp
  state_summary
  action_type
  action_input
  action_output
  cost
  observed_reward
  evaluator_result
  causal_parent_event_ids[]
}
```

其中 `action_type` 至少包括：

`SEARCH_EXTERNAL`, `SELECT_EXTERNAL`, `ADAPT`, `CROSS`, `MUTATE`, `EVALUATE`, `REJECT`, `COMMIT`。

= 六、Evaluator 与统计门

== 6.1 三层评价

第一层：Hard Validity Gate。

检查：

- 数据泄漏；
- future information；
- 非法 API；
- 超资源预算；
- evaluator 被修改；
- 缺失 artifact；
- 非确定性环境异常。

第二层：Statistical Evaluator。

对多 seed / split：

$
Delta_i = M(A_"candidate", s_i) - M(A_"baseline", s_i).
$

输出：

$
hat(mu)_Delta, quad "CI"_(1-alpha).
$

默认：

$
alpha = 0.05.
$

第三层：Research Evidence。

记录机制、假设、改动与结果之间的关系，不允许仅凭自然语言“感觉更好”提交。

== 6.2 SGM-style commit gate

长期自动优化会产生 multiple testing 问题。

故不是：

$
"best observed score" > "baseline" => "commit".
$

而应：

$
"statistical certificate" => "commit".
$

首版可先实现简单 sequential confirmation：

1. cheap pilot；
2. candidate 达阈值才进入 confirmation；
3. confirmation 使用冻结 seed set；
4. 只有 confidence 满足 Task Contract 才进入 accepted archive。

后续再引入 e-value / error spending 等更严格的 lifetime false-acceptance 控制。

== 6.3 Evaluator 不完全可变

采用：

$
E = E_"anchor" + E_"challenge"(t).
$

首版：

$
E_"anchor" = "immutable".
$

未来仅允许 adversarial cases、stress tests、counterexamples 等 challenge layer 演化，避免 Goodhart，同时保持跨代可比性。

== 6.4 删失规则与生存分析

`time to first improvement` 与 `time to target` 是时间型指标：「预算内事件没发生」不是数值，而是*右删失*。§6.1 第二层只规定了

$
hat(mu)_Delta, quad "CI"_(1-alpha),
$

没有说删失怎么记 —— 而对删失数据只用均值与置信区间汇总，会系统性低估事件时间。

这一处不是偏好，是*未修的缺陷*，且有两个互不相干的来源：B 线审查的五个版本（同一份审查的不同长度，故只算一个来源）各自点出「'time to first improvement'（'计划':954）无删失规则与生存分析，却规定用均值与置信区间汇总（'计划':770）」；2026-10-07 的一份外部研究导出（长程 Agent 评测）独立要求同一件事：未跨过阈值的运行应记右删失，而不是记成「成本 = 预算上限」。

规则：

+ 事件在预算 $B$ 内发生：记观测时间 $t$；
+ 未发生：记右删失 $t^+ = B$；删失标记与观测值分开存，既不得回填成 $t = B$ 当作真观测，也不得丢弃该 run；
+ 汇总：先报达事件比例（k/n），再报事件发生者的分布（中位数与分位数；可用 Kaplan--Meier 生存曲线）。有删失时不得只对观测到的时间求均值；
+ $B$ 预注册：事后不得因删失比例高而延长预算，否则删失规则形同虚设。

首版只实现前三条：报 k/n、删失数与比例，以及事件发生者的分位数，并注明删失者不在分位数内。

= 七、Open-World Bridge Policy

== 7.1 第一版：确定性规则

暂不使用 RL。

状态：

$
x_t =
(
"best score",
"stagnation",
"diversity",
"budget",
"external candidates",
"verification quality",
"adaptation cost",
"recent mutation yield"
).
$

动作：

$
a_t in {S,R,C,E},
$

其中：

- $S$：SearchExternal；
- $R$：ReuseExternal；
- $C$：CrossExternalInternal；
- $E$：ContinueEvolution。

初始策略示例：

```text
if no verified baseline:
    search_external

elif stagnation >= threshold
     and external_search_budget_available:
    search_external

elif verified_candidate
     and adaptation_cost is low:
    reuse_or_cross

elif external_candidate is novel
     and compatible:
    cross

else:
    continue_internal_evolution
```

规则必须写入版本化 policy 文件，并进入 trajectory。

== 7.2 第二版：bandit

真实轨迹足够后：

$
r_t =
frac(Delta "VerifiedPerformance", "cost").
$

使用 UCB / contextual bandit：

$
a_t =
"argmax"_a E[r_t | x_t,a].
$

ASI-Evolve 的 sampler abstraction 可作为实验参考。

== 7.3 第三版：policy RSI

当 replay 数据足够：

$
"TrajectoryArchive"
-> "ReplayEnvironment"
-> "PolicyCandidates"
-> "OfflineEvaluation"
-> pi_(t+1).
$

此时再考虑 Dream-RSI 类机制。

= 八、实验计划

== 8.1 核心可证伪实验

比较：

$
C_0 = "Closed-world ShinkaEvolve",
$

与：

$
C_1 =
"Open-world discovery"
+
"ExternalInspiration"
+
"ShinkaEvolve".
$

严格保持：

$
"Evaluator",
"Model",
"Budget",
"InitialProblem",
"SeedPolicy"
$

相同。

主要指标：

$
Y =
(
"best verified score",
"time to first improvement",
"time to target",
"LLM calls",
"experiment count",
"compute cost",
"external reuse rate",
"external contribution"
).
$

== 8.2 External Contribution 定义

不能把“用了外部代码”直接算成功。

定义某 external inspiration $r$ 的贡献：

$
C(r) =
"counterfactual performance difference"
$

的近似。

工程上至少做 ablation：

- with external inspiration；
- without external inspiration；
- shuffled/unrelated inspiration；
- direct reuse；
- cross/adaptation。

若外部信息仅增加 token/context 而不改善 verified performance，则判为无有效贡献。

== 8.3 任务选择

首批任务应满足：

- evaluator 清晰；
- baseline 可复现；
- 单次实验成本低；
- 存在可搜索的公开实现；
- 算法空间存在真实改进余地；
- 不依赖昂贵大规模训练。

建议任务层次：

#enum(
  [*Toy / synthetic*：验证 adapter、ledger、统计门正确性。],
  [*公开 algorithm benchmark*：验证 open-world contribution。],
  [*真实项目 probe*：选择一个已有长期实验历史的算法问题，验证系统在非玩具环境中的研究价值。]
)

首版不以“benchmark 排名”作为唯一目标，而以基础设施能否减少真实研究成本为主要验收。

= 九、实施阶段

== 9.1 Phase 0：冻结边界与基线

目标：避免再次发生 proxy drift。

交付：

- `GOAL.md`：唯一目标与非目标；
- Task Contract schema；
- Experiment Record schema；
- evaluator hash / environment hash；
- closed-world Shinka baseline；
- 统一 cost accounting。

验收：

$
"same commit + same seed + same environment"
=> "reproducible result within tolerance".
$

== 9.2 Phase 1：ExternalInspiration Adapter

实现最小链：

$
"CandidateResource"
-> "ExternalInspiration"
-> "Shinka Program metadata/inspiration".
$

只支持 GitHub repository 即可。

必须记录：

- source URL；
- commit SHA；
- license；
- verification；
- relevant files；
- mechanism summary；
- adaptation diff；
- provenance hashes。

不实现新的搜索引擎。

验收：一个外部 repo 能被发现、冻结、转换、进入 Shinka mutation/cross，并可追溯回原 commit。

== 9.3 Phase 2：Open-vs-Closed A/B

至少选择 3 类算法任务。

每类运行：

- Closed；
- Open；
- Open + unrelated inspiration control。

重复多 seed。

验收不是要求 Open 必胜，而是能回答：

$
H_1:
E[J_"open"] > E[J_"closed"] ?
$

若没有证据支持，则停止扩展 open-world infrastructure，分析失败原因。

== 9.4 Phase 3：Bridge Policy v1

加入版本化规则 policy。

记录每次：

$
("state", "action", "reason", "cost", "result").
$

研究：

- stagnation threshold；
- search budget；
- adaptation cost；
- novelty；
- verification confidence。

验收：策略行为可重放、可解释、可做 ablation。

== 9.5 Phase 4：Statistical Commit Gate

加入 confirmation queue 与 sequential evidence。

所有 accepted improvement 必须满足：

- hard validity；
- multi-seed confirmation；
- confidence contract；
- no evaluator mutation；
- provenance complete。

验收：随机 lucky candidate 不得轻易污染主 lineage。

== 9.6 Phase 5：Policy Learning

轨迹数量足够后才进入。

依次：

$
"rule"
-> "UCB"
-> "contextual bandit"
-> "replay policy optimization".
$

禁止直接跳到复杂 RSI。

== 9.7 Phase 6：Harness / Skill RSI

只有出现明确 evidence：

$
"algorithm search bottleneck"
approx
"harness bottleneck"
$

时，才引入：

- SE-GoS-style skill graph；
- HarnessFix-style trace diagnosis；
- AHE-style falsifiable harness modification；
- HGM/MGM-style archive selection/mutation；
- RobustSGPO-style mutation permission schedule。

每次 harness change 需：

$
"Prediction"
+
"Intervention"
+
"Outcome".
$

= 十、工程目录建议

不强制 ADA/OPL 形式。首版甚至可以是一个独立实验仓库：

```text
open-world-algorithm-research/
├── contracts/
│   ├── task.schema.json
│   ├── external_inspiration.schema.json
│   └── experiment_record.schema.json
├── adapters/
│   ├── man1lab/
│   └── shinka/
├── policies/
│   └── bridge-v0.yaml
├── evaluators/
│   └── <task>/
├── experiments/
│   └── <campaign-id>/
├── ledger/
│   ├── experiments.jsonl
│   └── trajectories.jsonl
├── scripts/
│   ├── run_closed
│   ├── run_open
│   ├── confirm
│   └── replay
├── tests/
└── docs/
    ├── GOAL.md
    ├── decisions/
    └── results/
```

若后续发现某部分自然属于 ADA/OPL，再移动；不提前绑定。

= 十一、权限与安全模型

用户长期观察到：

$
"nominal permission" != "actual permission".
$

因此每个 action 同时记录：

$
"Capability" =
("declared", "discovered", "available", "verified").
$

只有：

$
"verified capability"
$

可以进入自动策略。

外部仓库默认：

- discovery 可联网；
- clone 需显式 execution stage；
- dependency install 进入隔离环境；
- 不允许修改 host 全局配置；
- secrets 不进入 artifact；
- evaluator 与 hidden tests 对 mutation agent 只读；
- destructive operation 必须显式授权。

权限同时作为搜索正则化：

$
"SearchState" = ("candidate", "mutation permissions").
$

= 十二、失败模式与停止条件

== 12.1 Proxy-goal drift

症状：大量时间用于完善 schema、UI、插件系统，但 verified algorithm improvement 没有增加。

停止规则：

$
Delta "research capability" approx 0
$

连续两个 milestone，则冻结基础设施开发。

== 12.2 Open-world noise

症状：搜索返回大量相似、低质量或不可执行 repo。

处理顺序：

$
"better verification"
-> "better selection"
-> "better query"
$

而不是立即上复杂 RAG。

== 12.3 Integration tax

若：

$
"adaptation cost" > "expected research value",
$

则 external resource 应被拒绝。

== 12.4 Evaluator gaming

任何 candidate 若只提升 challenge-specific proxy 而损害 anchor，则不得 commit。

== 12.5 Infrastructure self-evolution too early

若轨迹不足，禁止优化：

$
pi,\ H,\ E
$

的复杂机制。

先积累：

$
T = {"trajectory"_1,...,"trajectory"_n}.
$

= 十三、决策日志原则

所有重要架构变化必须回答五个问题：

#enum(
  [解决了哪个真实研究 bottleneck？],
  [已有货架方案为什么不够？],
  [新增维护成本是多少？],
  [如何通过实验判断它有效？],
  [若无效，能否低成本删除？]
)

因此优先：

$
"reversible decisions" > "deep coupling".
$

= 十四、近期具体执行计划

== 14.1 Sprint A：1 个垂直切片

目标：跑通一个 repo → inspiration → evolution。

工作：

1. 选择低成本 algorithm benchmark；
2. 固定 evaluator；
3. 跑 closed-world Shinka baseline；
4. 从 Man1Lab 输出或其 schema 生成一个真实 CandidateResource；
5. 实现 `ExternalInspiration`；
6. 将其注入 Shinka；
7. 运行一次 cross/adapt；
8. 完整写入 Experiment Record。

完成定义：

$
"source"
-> "commit"
-> "inspiration"
-> "child program"
-> "evaluation"
-> "provenance"
$

全链可追溯。

== 14.2 Sprint B：最小 A/B

目标：回答 open-world 是否值得。

至少：

$
3 " tasks" times 3 " conditions" times n " seeds".
$

conditions：

- Closed；
- Open；
- Open-Unrelated control。

输出：

- verified score；
- cost；
- time；
- calls；
- external contribution；
- failure taxonomy。

== 14.3 Sprint C：Bridge Policy 数据化

在 A/B 后加入规则 policy。

不优化 policy，只收集：

$
(x_t,a_t,r_t).
$

目标是形成可用于后续 UCB/contextual bandit/replay 的真实数据。

== 14.4 Sprint D：决定是否继续

Go 条件：

- 至少一类真实任务显示稳定 open-world benefit；
- external contribution 可通过 ablation 观察；
- integration tax 可接受；
- provenance 与 evaluator 没有失控。

否则：

- 不继续扩大系统；
- 复盘是 retrieval、verification、adaptation 还是“open world 本身收益低”；
- 必要时终止该路线。

= 十五、中期路线图

若 Phase 1–4 被实验证实：

$
"Algorithm"
-> "Experience"
-> "Policy"
-> "Harness"
-> "EvaluatorChallenge".
$

而非反过来。

可能路线：

#table(
  columns: (1fr, 1.7fr, 2.4fr),
  inset: 5pt,
  stroke: 0.4pt,
  [*层*], [*触发条件*], [*候选方法*],
  [Algorithm], [始终], [ShinkaEvolve / task-specific mutation],
  [Experience], [轨迹开始积累], [structured archive / comparative trajectories],
  [Policy], [规则策略出现明显机会成本], [UCB / contextual bandit / Dream-RSI],
  [Skill], [retrieval 成为瓶颈], [SE-GoS-style graph],
  [Harness], [trace 显示 harness failure], [HarnessFix + AHE],
  [Search lineage], [archive 很大且局部最优明显], [HGM / MGM],
  [Commit], [长期 repeated testing], [SGM-style statistical gate],
  [Evaluator challenge], [Goodhart 迹象], [RQGM-style co-evolving challenge layer],
)

= 十六、当前架构结论

截至本计划版本，最合理的中心不是：

$
"Kimi + one giant research framework".
$

而是：

$
#box(stroke: 0.6pt, inset: 4pt)[
  Frozen Evaluator
  \+
  Evolutionary Algorithm Search
  \+
  Immutable Experiment/Trajectory Archive
  \+
  Open-World Acquisition Adapter
].
$

Kimi、DeepSeek、GPT 等模型只是：

$
"mutation / reasoning operators".
$

Man1Lab、ShinkaEvolve、AgentCo-Op、ASI-Evolve 等只是：

$
"replaceable capability providers".
$

真正长期稳定的对象是：

$
#box(stroke: 0.6pt, inset: 4pt)[
  Task Contract
  \+
  Evaluator
  \+
  Evidence
  \+
  Trajectory
  \+
  Verified Improvement
].
$

= 十七、最终研究假设

本项目当前不再试图证明“一个通用自动科研系统应如何设计”，而检验两个更窄、更强、可证伪的假设。

*H1 — Open-world evolutionary inspiration*

$
"Verified external implementations"
-> "first-class evolutionary inspirations"
$

能够在相同 evaluator 与预算下，提高算法改进效率。

*H2 — Adaptive world-search policy*

存在策略：

$
pi_"bridge"(x_t)
$

使 Agent 能根据 stagnation、diversity、cost、verification、external novelty 等状态，在：

$
{"Search", "Reuse", "Cross", "Evolve"}
$

之间做出比固定策略更高效的选择。

若 H1 不成立，则无需投入 H2。

若 H1 成立，才逐步研究：

$
"Rule"
-> "Bandit"
-> "Replay"
-> "RSI".
$

这构成下一阶段全部工作的逻辑主线。

= 附录 A：关键参考实现与资料

#bibliography("refs.bib", full: true)
