#set page(paper: "a4", margin: (x: 20mm, y: 18mm))
#set text(font: "Noto Sans CJK SC", size: 10.5pt)
#set par(justify: true, leading: 0.72em)

#align(center)[
  #text(size: 20pt, weight: "bold")[自动算法研究基础设施：货架式正交组合工程方案]
  #v(4pt)
  #text(size: 11pt)[面向算法改进（Algorithm Improvement）的 2026-09 前沿方案]
  #v(3pt)
  #text(size: 9pt)[目标：最小化基础设施自研，将工程资源集中于真实算法改进]
]

= 0. 决策摘要

本方案不以 ADA、OPL、Kimi 插件或某个 “Research OS” 为目标。一级目标定义为：

$ G_0 = "提高真实算法研究的单位资源有效进展" $

即在固定时间、算力与人工监督预算下，提高可复现、可验证的算法性能改进。基础设施仅为代理变量。

截至 2026-09 的网络与源码调查支持以下组合：

- *交互/编码宿主*：Kimi Code（现有，不重造 agent harness）。
- *长程研究控制*：DeepScientist 作为第一候选；它已原生提供 Kimi Code runner、Findings Memory、Research Map、baseline/experiment loop。
- *评价先行*：AutoSciRub；在研究执行前生成 executable rubric，研究后按 criterion 验证并定向修订。
- *大规模算法搜索*：AIRA-dojo / AIRA₂ 作为可替换的高吞吐 search backend，而非总控系统。
- *评测*：项目内 frozen evaluator + AIRS-Bench / MLE-bench 风格 hidden/consistent evaluation。
- *证据与产物*：Git + immutable experiment records；只在需要跨工具交换时导出标准 provenance，不建设自有通用 provenance 平台。
- *自研范围*：仅 glue、项目适配器、任务 evaluator，以及货架组件不能表达的稳定缺口。

核心原则：

$ "reuse" > "configure" > "compose" > "adapt" > "extend" > "build" $

= 1. 问题边界：算法改进，而非一般“自动科研”

本工程针对可计算、可重复评测的算法研究。一个研究任务形式化为：

$ T = (P, D, M, B, C) $

其中 $P$ 为问题定义，$D$ 为数据/仿真环境，$M$ 为主评价指标及辅助指标，$B$ 为 baseline，$C$ 为资源与合法性约束。

一次候选实验：

$ e_i = (h_i, delta_i, theta_i, s_i, r_i) $

其中 $h_i$ 为 hypothesis，$delta_i$ 为代码/算法改动，$theta_i$ 为配置，$s_i$ 为随机种子/数据切分，$r_i$ 为运行结果。

研究目的不是“完成报告”，而是在约束 $C$ 下寻找 Pareto frontier：

$ F = { e : not exists e' " such that " e' succ e } $

其中 dominance 应由项目声明，默认不把多指标过早压成单一 scalar。

因此基础设施必须特别优化：
1. baseline 可复现；
2. candidate 生成与实验执行解耦；
3. evaluator 独立于 candidate agent；
4. 大量失败实验可保留并影响后续搜索；
5. 统计不确定性、随机性与资源成本进入决策；
6. 禁止“指标提升但违反在线/因果/资源约束”的伪改进。

= 2. 经验证的外部前沿

== 2.1 AIRS-Bench：算法研究任务应以 problem–dataset–metric 为硬边界

AIRS-Bench 由 20 个来自 SOTA ML 论文的任务构成，覆盖 NLP、代码、数学、生化建模、时间序列等；每个任务明确给出 problem、dataset、metric 与 human SOTA，并公开 aira-dojo/MLGym task definition 与 evaluator。2026 年结果仍远未饱和，故适合作为我们设计 evaluator 与任务 contract 的外部参照。

工程吸收：项目 contract 必须把 metric/evaluator 当作独立、冻结对象，而不是 agent prompt 中的一段文字。

== 2.2 AIRA₂：当前算法改进瓶颈是 throughput、evaluation noise、operator ceiling

Meta 2026 的 AIRA₂ 将三类瓶颈实证化：
- synchronous execution 限制 search throughput；
- validation selection 的噪声会造成长程搜索错误；
- fixed single-turn operator 限制探索能力。

其方案是 asynchronous multi-GPU workers、Hidden Consistent Evaluation、ReAct operators；在 MLE-bench-30 上 24h/72h mean percentile rank 为 81.5%/83.1%，在 AIRS-Bench 20 个任务中有 6 个超过对应 human SOTA。

工程吸收：执行层应可并行；评价必须与 proposal 隔离；长程算法研究不能只靠“LLM 改代码→看一个 validation score”。

== 2.3 AutoSciRub：把成功条件前置，而不是最后让 agent 自评

AutoSciRub 先从任务、文献和可见数据构造 executable rubric；每个 criterion 明确 required analysis、evidence artifact、satisfaction condition，再进行 criterion-level verification 与 targeted revision。其公开实现是可安装 skills/plugin bundle，并有 schema、状态文件、retrieval 与测试。

工程吸收：把研究目标编译成可检查 contract。对算法改进任务，rubric 不应替代 numeric evaluator，而应覆盖 numeric evaluator 之外的合法性条件，例如：
- baseline reproduction；
- 数据泄漏检查；
- online availability；
- ablation；
- seed robustness；
- runtime/memory budget；
- method/code consistency；
- 结果产物完整性。

== 2.4 DeepScientist：Kimi 接入已经是货架能力

DeepScientist 当前公开实现包含 Codex、Claude Code、Kimi Code、OpenCode runner；Kimi 路径有独立 doctor/startup probe，并将 quest skills 与 MCP 注入隔离的 Kimi runtime。其研究循环已有 baseline、experiment rounds、Findings Memory、Research Map 与 Bayesian optimization。

工程吸收：第一阶段不写 OPL/Kimi plugin 总控。先直接把 Kimi Code 当 runner 接入 DeepScientist，观察真实算法课题缺口。

== 2.5 MLE-bench：真实算法工程评价必须按资源预算比较

MLE-bench 包含 75 个真实 Kaggle ML engineering competition，并以人类 leaderboard 为基准。2026 leaderboard 已出现约 60%+ aggregate performance 的系统，但不同系统运行预算可达 12–24h，说明“最终分数”不能脱离 compute/time budget 比较。

工程吸收：所有内部研究结果至少记录：
$ ("quality", "wall_time", "gpu_time", "tokens", "runs", "human_interventions") $。

= 3. 正交组合架构

#figure(
  rect(inset: 10pt, radius: 4pt)[
    #align(center)[
      *Research Goal / Algorithm Task* \
      $arrow.b$ \
      *AutoSciRub: executable research contract* \
      $arrow.b$ \
      *DeepScientist + Kimi Code: hypothesis / code / long-horizon control* \
      $arrow.b$ \
      *Candidate Queue* \
      $arrow.b$ \
      *Execution Backend* \
      [local | isolated env | GPU pool | AIRA-dojo] \
      $arrow.b$ \
      *Frozen / Hidden Evaluator* \
      $arrow.b$ \
      *Experiment Ledger + Findings* \
      $arrow.b$ \
      [accept / reject / replicate / ablate / branch] \
      $arrow.l$ *next iteration*
    ]
  ],
  caption: [推荐的最小正交组合]
)

关键点：这些组件不是层层“框架套框架”。只有 ownership 清晰的接口：

$ "Proposal" perp "Execution" perp "Evaluation" perp "Evidence" $

即 proposal agent 不拥有最终 evaluator；executor 不决定研究价值；research controller 不篡改历史 run；rubric 不替代真实 metric。

= 4. 工程 Contract

== 4.1 Task Contract

每个算法课题根目录只要求一个稳定的项目 contract：

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
    secondary: [runtime, memory]
```

此文件是项目事实，不是 agent memory。

== 4.2 Experiment Record

每个 run 产生不可覆盖记录：

```text
experiment_id
parent_ids
hypothesis
code_commit
config_hash
dataset_hash
environment_hash
seed
command
started_at / ended_at
exit_status
raw_metrics
normalized_metrics
constraint_checks
artifacts
agent/model
token_cost
verdict
```

其中必须区分：

$ "failed hypothesis" != "invalid experiment" $

前者是科学证据；后者是基础设施/方法失败，不得用于更新算法结论。

== 4.3 Evaluation Contract

评价分三层：

1. *Hard validity gate*：数据泄漏、未来信息、非法 API、超预算、产物缺失等。任一失败则 `INVALID`。
2. *Statistical evaluator*：固定 seed / hidden split，输出估计量与不确定性。
3. *Research rubric*：baseline、ablation、解释、复现、边界条件等是否满足。

故：

$ "Verdict"(e) = "Valid"(e) and "StatisticalEvidence"(e) and "RubricCoverage"(e) $

不得由 agent 自己用自然语言决定“成功”。

= 5. 搜索策略：从串行 agent 转为预算化实验搜索

算法研究的资源分配对象是 experiment，而不是 chat turn。

设候选集合 $H_t={h_1,...,h_n}$，实验成本 $c(h)$，预期信息/性能收益 $u(h)$。选择：

$ h^* = "argmax"_h E[u(h) | "history"] / E[c(h)] $

实际工程分三级：

- Tier 0：静态检查、单元测试、极小样本 sanity check；
- Tier 1：低成本 pilot、少 seed、缩短训练；
- Tier 2：完整实验、多 seed、hidden/frozen evaluator。

只有通过低 fidelity gate 的候选进入昂贵验证。这与 AIRA₂ 的 throughput 思路一致，也为以后接 experiment preference/ranking model 留接口，但首版无需训练自己的 preference model。

并行执行时，controller 只写 candidate queue；worker claim job；evaluator 独立读取 artifact。故 worker 数可从 1 扩至 N，而不改变研究语义。

= 6. 推荐部署方案

== 6.1 Phase 0 — 零自研基线（1–2 天）

安装并验证：
- Kimi Code；
- DeepScientist Kimi runner；
- AutoSciRub 独立 skills（若 Kimi 尚无直接 installer，则只做最薄的 skill-copy/manifest adapter）；
- 项目自身 evaluator。

验收：
- Kimi 可独立完成最小 coding task；
- `ds doctor --runner kimi` 通过；
- baseline 从 clean checkout 可一键复现；
- evaluator 不依赖 agent conversation；
- 同 commit/config/seed 的结果在容许误差内重复。

若此阶段已能可靠推进真实算法课题，则停止基础设施开发。

== 6.2 Phase 1 — 真实课题 bake-off（3–7 天）

固定模型、初始代码、预算和任务，比较：

$ S_0="Kimi" $

$ S_1="Kimi + AutoSciRub" $

$ S_2="Kimi + DeepScientist" $

$ S_3="Kimi + DeepScientist + AutoSciRub" $

至少运行多个独立 research seeds。

评价向量：

$ Q=(Delta "metric", "validity", "reproducibility", "walltime", "compute", "tokens", "human interventions") $

不提前 scalarize；画 Pareto frontier。

停止条件：若某组合在主要研究收益上不劣、同时维护/人工成本更低，则淘汰 dominated 组合。

== 6.3 Phase 2 — 只在 throughput 成为瓶颈时引入 AIRA-dojo

触发条件：
- candidate backlog 长期大于 worker capacity；
- GPU/CPU 有明显空闲；
- sequential research controller 成为 wall-clock bottleneck；
- evaluator 已稳定且可隔离运行。

此时将 AIRA-dojo 作为 execution/search backend，而非替换全部研究环境。

== 6.4 Phase 3 — 缺口驱动的最小自研

只有连续多个真实课题出现同一缺口，才创建新组件。

准入条件：

$ "frequency"("gap") >= 3 $

且

$ "expected saved research cost" > "build" + "maintenance cost" $

否则用 project-local script/skill 解决，不升级成基础设施。

= 7. 针对算法改进的安全护栏

算法 agent 最容易制造“看似改善”的错误，故以下 gate 必须机器化：

- evaluator 与训练/搜索过程隔离；
- test/hidden split 不向 proposal agent 暴露；
- baseline 与 candidate 使用同一 evaluator；
- 数据、代码、环境、seed 全部 hash；
- 禁止未声明 future information；
- timeout/OOM/NaN 不记为负科学证据，而记 `INVALID`；
- 性能提升必须保留 raw artifact；
- 关键改善必须重复运行；
- 最终 candidate 必须做 ablation；
- 对 stochastic algorithm 报告分布/置信区间，而非最佳单次 run；
- agent 不得修改 evaluator；若 evaluator 必须变更，则开启新的 evaluation epoch，旧结果不得直接比较。

= 8. 不做清单

首版明确不建设：
- 自有通用 Research IR；
- 自有 workflow engine；
- 自有 agent harness；
- 自有通用 memory/vector DB；
- 自有 plugin marketplace；
- 自有 provenance ontology；
- 自有 multi-agent framework；
- 自有研究 GUI；
- 为“架构完整”而重写 DeepScientist/AIRA/AutoSciRub。

任何上述工作都需要真实课题的重复缺口作为证据。

= 9. 第一真实课题模板

每个课题只需建立：

```text
project/
├── RESEARCH.md          # problem + scientific constraints
├── task.yaml            # machine contract
├── baseline/            # frozen reference
├── src/                 # mutable algorithm
├── eval/                # agent不可随意修改
├── experiments/         # immutable run records
├── artifacts/           # raw outputs
└── reports/             # periodic research summaries
```

研究循环：

$ "reproduce"(B) $
$ -> "induce rubric" $
$ -> "generate" H $
$ -> "cheap screen" $
$ -> "execute" $
$ -> "hidden/frozen evaluate" $
$ -> "replicate" $
$ -> "ablate" $
$ -> "update findings" $
$ -> "choose next" H $

人工角色只保留三个硬权力：
- 修改研究目标/约束；
-批准高成本或不可逆操作；
- 对 evaluator/研究 contract 做 versioned change。

= 10. 验收标准

基础设施本身不以 LOC、功能数量或“自动化程度”验收。

成功标准为：相较裸 Kimi，在相同算法研究任务与资源预算下，组合系统至少在以下某一维严格改善，且其余关键维不显著恶化：

$ Delta "research gain" > 0 $

或

$ Delta "human intervention" < 0 $

或

$ Delta "invalid experiment rate" < 0 $

或

$ Delta "time to verified improvement" < 0 $

并要求该效果跨至少三个不同算法任务重复。

若不能达到，则删除对应基础设施层，而不是继续“完善”。

= 11. 当前工程决策

首选实验栈：

$ #box(stroke: 0.6pt, inset: 4pt)[Kimi Code + DeepScientist + AutoSciRub + project-native frozen evaluator] $

AIRA-dojo 作为第二阶段高吞吐 backend；AIRS-Bench/MLE-bench 作为外部方法论与回归 benchmark，而非真实项目目标。

因此当前工程工作的优先级不是实现新框架，而是：

$ #box(stroke: 0.6pt, inset: 4pt)[把真实算法课题放入现成栈，测量缺口，再让缺口决定代码] $

这使基础设施始终从属于算法改进，而不会再次把代理目标升级为项目本身。

= 参考资料（检索于 2026-09-17）

- Meta, *AIRA₂: Overcoming Bottlenecks in AI Research Agents*, 2026.
- Meta, *AIRS-Bench*, 2026.
- OpenAI, *MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering*.
- ResearAI, *DeepScientist*.
- Wang et al., *Learning to Evaluate Before Improving: Automatic Rubric Induction for Automatic Research Agents*, 2026.
