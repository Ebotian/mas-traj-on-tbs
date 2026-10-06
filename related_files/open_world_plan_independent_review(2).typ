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
  #text(size: 20pt, weight: "bold")[《开放世界算法自动改进基础设施》]
  #v(3pt)
  #text(size: 20pt, weight: "bold")[独立审查报告]
  #v(7pt)
  #text(size: 12pt)[Independent Review Report]
  #v(10pt)
  #text(size: 9.5pt)[审查对象：`open_world_algorithm_research_engineering_plan.typ` v1.0（2026-09-18，1513 行）]
  #v(2pt)
  #text(size: 9.5pt)[本报告版本：*Rev. 2*（2026-09-18）· 含两轮外部复审的核验记录]
  #v(2pt)
  #text(size: 9.5pt)[结论：*有条件推进——推进到能力探针，尚不到 H1 的 A/B 实验*]
  #v(2pt)
  #text(size: 9.5pt)[本报告不含对尚未存在的实验结果的评价]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 2 总评*：经过两轮外部复审的核验，源码层面的判断已基本稳定（Rev. 0/1 对系统能力的核实与更正均已复核通过），但审查的重心发生了转移。Rev. 2 有三个必须记录的变化：

  #v(3pt)

  + *新增 D11（本次最重要的补充）*：计划的统计设计把 evaluator seed 当作 H1 的独立实验单位，这是 experimental unit 错位；即使把 seed 从 5 加到 34，也解决不了 H1 的识别问题。H1 现在*不可识别*，因为 §14.2 里根本没有 run 级复制。
  + *§4 的新颖度结论撤回*："外部实现 × 反事实贡献 × provenance"这一差异*已被占位或逼近*。Rev. 1 的结论建立在没有做完最近邻检索之上，现已补齐检索清单。
  + *D10 重新定级*：从"前提风险"降为"关键集成缺口"——Man1Lab 没有 Search 不等于 Search 能力不存在，而现成路线已有 KAPSO、AutoSOTA、MLE-STAR 等可直接借鉴的同型流水线。

  #v(3pt)

  因此结论从 Rev. 1 的"修五项必改再进 Phase 2"改为：*先做一个 Probe-0 能力探针*，用一条真实外部实现把整条链走通并记账；若这一步就昂贵、脆弱或语义映射失败，H1 的实验设计没有意义。
]

= 零、审查方式与限度

== 0.1 方法

本报告由三轮构成。Rev. 0 为全文精读 + 20 个并行独立审查轴（源码级事实核实、专项反证、统计复核、构建与排版实测）。Rev. 1 为对第一轮复审意见的独立核验（新增 6 轴）。Rev. 2 为对第二轮复审意见的独立核验（新增 6 轴：cross 模式 prompt 构成的逐行核对、三篇被指认的最近邻工作、一轮穷尽式最近邻检索、以及 experimental unit 的方法学核实）。

三轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。每轮都产生了对本报告自身判断的更正（见 §6）。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行，不存在可评价的数据。
- 外部系统的核实基于 2026-09-18 的公开快照；被审计划本身未固定版本，故任何断言都可能随上游更新失效。
- §4 的最近邻检索以 arXiv 为主要口径（约 40 组查询 + 逐篇 HTML 核对），未覆盖非 arXiv 的 ACL / NeurIPS 正文与 GitHub 代码搜索，故"已穷尽"应读作"arXiv 口径下已穷尽"。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S64）见附录 B。第三方源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → Rev. 1 → Rev. 2）

*Rev. 1 阶段（对第一轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R1　D1 补救措施], [注入机制文本"必须自定义 `PromptSampler`"], [*不成立*。`prompts_base.py:74-79` 逐程序追加 `Text feedback:`；`sampler.py:147-157` 把 archive+top-k 全部送入], [已改写为 code / text_feedback / metadata 三者映射],
  [R2　D2 定级], ["致命"（无法归因）], [*部分成立*。计划 H1 字面是工程效用假设，对该假设封闭 vs 开放本身有效], [降为"重要"，并区分 H_U 与 H_M],
  [R3　获取前端], [未指出], [*成立且重要*。Man1Lab 无"问题 → 候选仓库"路径], [新增 D10],
  [R4　AgentCo-Op 能力], [`sandbox_repo` 为"真实 backend"], [*过强*。其为 "command builder only"，只产出 dry-run 命令规格], [已改写，并补真实执行路径与其 stub 事实],
  [R5　Experiment Record], ["与 ARI 逐字相同"], [*错*。同源但字段集不同], [已改为"Task Contract 高度重合（18/19 行），Experiment Record 同源而异"],
  [R6　ARI 计划日期], ["（09-17）"], [*错*。文件 mtime 为 09-18 14:32], [已更正],
  [R7　样本量], ["seed 数提到 $n>=20$"], [*无依据且与自身表格冲突*], [已改为公式化程序与 MDE 论证],
  [R8　proxy drift], ["已经发生"（事实层）], [*证据不足*（见 R16）], [已收窄为"治理缺陷已确认"],
  [R9　许可风险表述], ["许可传染"], [*过强*。漏掉 AGPL §2 的条件句], [已按 §2 重写为 License Provenance Gate],
  [R10　行号], [`license` 在"计划:527"等三处], [*错*。应为 533、626、1046], [已更正],
)

*Rev. 2 阶段（对第二轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*Rev. 1 的说法*], [*核验结果*], [*处理*],
  [R11　cross 段与反馈的相邻性], [partner 的 `text_feedback` "不与代码相邻"], [*错*。`prompts_base.py:58-79` 在同一 per-program 块内按 code → metrics → feedback 排列，partner 必然在列（`prompts_cross.py:67`）；其 code 在同一 message 中出现*两次*（`sampler.py:205-208`）], [已改为"不出现在 dedicated crossover block 中，但在 eval history 中与其自身 code 相邻"；并补"code 重复一次"这一事实],
  [R12　`text_feedback` 的定位], [作为长期 canonical schema 的映射之一], [*部分成立*。工程上可行，但该字段具评测反馈语义], [改为"MVP 零改核捷径"，长期是否增设独立机制通道留待首轮实验后决定],
  [R13　D10 定级], ["第一跳没有实现路径"（前提风险）], [*过强*。Man1Lab 无 Search ≠ Search 能力不存在；同型流水线已有 KAPSO / AutoSOTA / MLE-STAR], [降为"关键集成缺口"，并列出可直接借鉴的已发表路线],
  [R14　D2 的实验设计], [六臂 C0–C5，以 C1 优于 token-matched 随机代码为判据], [*不足*。这只说明"相关信息优于随机信息"，不能识别机制迁移], [改为 E × M 的二因素设计 + shuffled mechanism 对位，见 D2],
  [R15　D3 的适用范围], [功效表被外推为"整个设计"的能力判断], [*错*（部分成立）。表本身正确，但只对候选提交门有效], [已加限定，并新增 D11 处理系统级单位问题],
  [R16　D4 的修补方案], [每个 Phase 都补 `Delta bestVerifiedScore` 里程碑], [*逻辑自相矛盾*。这会把 Rev. 1 刚批评的自我触发问题重新引入], [改为两类里程碑（能力 / 研究），见 D4],
  [R17　§4 新颖度], ["外部实现 × 反事实贡献 × provenance 尚未被占位"], [*错*。最近邻检索显示该差异已被占位或逼近（TurboEvolve、Loreley、Kernel Foundry、TuneNNGen、KAPSO、AutoSOTA、MLE-STAR、MARCO、DeepEvolve、EES）], [§4 整体重写，"未被占位"结论撤回],
  [R18　最终结论的含义], ["修五项必改后进入窄切片"], [*不够*。H1 目前不可识别（D11）], [改为"推进到 Probe-0 能力探针，尚不到 H1 的 A/B 实验"],
)

== 0.6 我保留的分歧

以下五项我不接受复审方的意见，理由与证据一并列出：

+ *TurboEvolve 的解池"含人类编写的解"*：不成立。该数据集 README 逐字为 "This dataset keeps the top 100 programs per task from TurboEvolve run checkpoints"，`summary.json` 的 `source_dataset` 为 `TurboEvolve_checkpoint_dataset`（各任务 5–16 个 run、数千至数十万 unique program），即作者自跑 checkpoint 的离线策展语料；全文 `human` 仅出现一次且在 Impact Statement。*seed-pool injection 本身成立*，但池的来源不是人类解、也不是运行时网络获取（S55）。
+ *把 EES 的 `external-source routes` 读作"运行时取外部实现"*：不成立。该表述指四个 Kaggle 任务的外部数据/答案查找（外部目标查找、ImageNet 语料恢复标签、Gutenberg 语料、历史最优查找），§5.2 首句即列出这四项（S64）。EES 的外源是测量污点披露，不是研究资产。
+ *"目录里只有 3–4 份 `.typ`"*：目录事实为 10 份 `.typ`（含本报告；排除后 9 份，其中计划类 7 份、评审/调研 2 份），`pdf/` 中 10 份 PDF 齐备。这属于访问范围差异。*但复审方的处置方式我接受*：该证据依赖本地目录状态、非可移植，正确标注是"本轮证据集内不可独立复现"（见 §3.3 开头给出的单命令自检）。
+ *D2 的降级附带条件*：若只主张 $H_U$，计划 §1.6 与 §2.2 的机制迁移措辞必须删除——两者不能同时存在。
+ *新颖度的替代猜测*：复审方猜测"真正有机会的是运行时开放世界 acquisition 与 evolutionary search 的闭环"。我不同意——该闭环已被 KAPSO、AutoSOTA、MLE-STAR 占据（§4）。反而更可能存活的是"进化 archive 内部、带 provenance 的单条外部灵感归因"。

= 一、我的认识

== 1.1 这份计划真正在说什么

剥掉术语后，它的论证链是五步：

#enum(
  [*目标重述*（计划:40-49）：唯一稳定目标是"使真实算法研究更适合 AI 自动、可靠、长期地推进"，ADA、OPL、Kimi 插件、Research OS 都是可替换手段。],
  [*工程顺序*（计划:153-172）：research need → existing solution search → composition → adapter → extension → new implementation；"架构可丢弃，研究能力不变"。],
  [*缺口定位*（计划:289-301）：开放世界获取与算法进化已有成熟底座，真正断裂的是 `CandidateResource → Program/Inspiration` 这一跳。],
  [*最窄切片*（计划:403-413）：Discovery → ExternalInspiration → Evolution → Frozen Evaluator → Experiment Ledger。],
  [*可证伪假设*（计划:1469-1509）：H1 = 外部已验证实现作为一等进化灵感能提升改进效率；H2 = 存在比固定策略更好的自适应搜索策略；H1 不成立则无需投入 H2。],
)

第 3 步是承重点：*它假定两段都已有货架，缺的只是中间那一跳。* 两轮核验下来：第二段成立，第一段的缺口比计划描述更靠前（D10），而第一跳的*统计设计*比缺口本身更成问题（D11）。

== 1.2 我认可的部分

+ *目标层的重新收束是对的。* 把"提高基础设施完整度"与"提高算法改进能力"分开，并明确前者是可丢弃手段。
+ *"架构可丢弃"作为硬约束有其可操作性*（计划:169）。
+ *多时间尺度分离*（计划:235-239）：若算法、经验、策略、harness 与评测同时变化，收益不可归因。
+ *从第一天记录轨迹以备将来 replay*（计划:581）：低成本、高期权价值。
+ *不继承 Man1Lab 的生成策略*（计划:474）：其 `generation_decision.py` 逐字包含 "Do not redesign algorithms or network architecture."，直接继承会扼杀 improvement loop。
+ *把外部实现交给自有 evaluator 定生死*：ShinkaEvolve 的 archive 只接纳 `correct = 1` 的个体，与计划"外部实现必须可验证"的立场天然一致。
+ *任务选择的阶梯*（计划:998-1004）：toy → 公开 benchmark → 真实项目 probe，顺序合理。
+ *外部事实的可核实性*：见 §3.1。两轮复审独立检查后，计划点名的系统仍无一虚构，特征描述基本准确。

= 二、我的怀疑

下面十一条按后果排序。*D10、D11 分别由 Rev. 1 与 Rev. 2 新增，编号沿用以避免破坏交叉引用。*

== D1（重要）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（字段清单见计划:529-536），而 `metadata` 对 prompt 不可见，因此该工程决策按文中所述不成立。

*证据一：metadata 确实不可见（快照 9912af12）*

- `shinka/core/sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(...)` 及可选 `text_feedback_section`；cross 的专属段落 `prompts_cross.py:57-73` 的 `get_cross_component()` 只写 `inspiration.code` 与 `perf_str(...)`。
- prompt 路径上读取 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支读 `stdout_log`/`stderr_log`），不参与 mutation 与 cross。
- 更弱的第二条路径：`metadata["patch_name"]` → 元总结器（`summarizer.py:249,282`）→ `meta_recommendations` → `sampler.py:118-124` 追加到系统消息，但条件是 `patch_type != "cross"`，且内容经 LLM 摘要。
- 计划:529-536 列出的六个键在仓库中*零命中*：既无写入者也无读取者。
- 覆盖性：全部分支（`main`、5 个 `fix/*`、9 个 `split/*`、`lean_support`）的 `sampler.py` 内容一致。

*证据二：正确的注入面是现成的*

- `prompts_base.py:58-79`：对*每一个*程序在同一个块内依次追加 `prog.code`（:61）、其 metrics（:63-67）、再追加 `Text feedback:` + `prog.text_feedback`（:74-79）。开关由 `sampler.py:156`（常规）与 `:243`（fix）传入，默认 `False`（`core/config.py:62`）。
- `sampler.py:152-157` 把 archive 与 top-k 合并后*全部*送入该函数，与 patch 类型无关。
- adapter 可自行设置该字段：`Program.text_feedback`（`dbase.py:174`）经 `Database.add()` 原样落库（`dbase.py:849-857, 870, 890`），全仓库*无任何* `UPDATE programs SET text_feedback`。

*正确的字段映射（MVP 口径）*：

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 零改核捷径）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*通道的真实代价*（Rev. 2 更正后）：

+ *cross 的对位段没有这条通道，但反馈并未与代码分离*。`get_cross_component()` 只放 partner 的 code + metrics（`prompts_cross.py:57-73`）；partner 的 `text_feedback` 只出现在 eval history 里（`prompts_base.py:58-79`），且与其自身 code 相邻（同块内仅隔其自身 metrics）。因此同一 partner 的 code 在同一 message 中*出现两次*：eval history 一次、`# Crossover Inspiration Programs` 一次（`sampler.py:205-208`）。`CROSS_ITER_MSG` 里的 `text_feedback_section` 填的是 *parent* 的反馈，不是 partner 的（`sampler.py:161-166`）。
+ *该字段属评测器语义*。其官方来源是评测脚本返回的 `metrics_val.get("text_feedback")`。把它用于机制描述属于语义借用，且单字段意味着"每个程序只有一条文本"——机制摘要与评测反馈只能二选一或由 adapter 拼接。*故它是很好的 MVP 捷径，但不宜在此阶段确立为长期 canonical schema*；首轮实验成功后再决定是否增设独立的 `mechanism_summary` prompt 通道。
+ *重复评测会生成第二行*。同一候选再走一遍 Shinka 评测流程会新建一行携带评测器值（`async_runner.py:4160-4172`），出现"同 code 两行、字段含义不同"。

*后果*：`adapter first, schema later`（计划:543）的*意图*可行，实现方式必须改写。且进入 prompt 的主体是"一个被 evaluator 打过分、进入 archive 的竞争者程序"，机制文本依附在同一行上——H1 的实验设计必须从这个真实通道重新推导。

*最小修补*：§4.3 改写为上述映射，写明 `use_text_feedback = true` 是前提、cross 对位段无此通道、code 会重复出现、以及重复评测的第二行问题。

== D11（重要，Rev. 2 新增）统计设计把 evaluator seed 当成了实验单位

*指控*：计划的 H1 是"开放世界研究系统 vs 封闭世界研究系统"，但 §5.1 的 `seeds: [11, 23, 47, 89, 131]`（计划:603）与 §14.2 的 `3 tasks × 3 conditions × n seeds`（计划:1342-1350）把 *evaluator seed* 当作 H1 的复现单位。这是 experimental unit 错位（pseudoreplication）。

*证据*：

- 随机性至少有三层：`Y_{t,r,s}`，其中 $t$ = task、$r$ = 一次完整的 research/evolution run、$s$ = evaluator seed。evaluator seed 是*观测单位*而非*实验单位*；把它当作复现单位会抬高自由度、降低临界阈值，从而制造假阳性（S48 的 pseudoreplication 定义；S49 逐字："Increasing the number of OUs does not increase the sample size"；S50 逐字："the experimental unit is the number of subjects tested, rather than the number of observations made within each subject"）。
- 因此：*即使把同一个 open-world search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`，并未估计 `E[pi_open] - E[pi_closed]`*；后者还包含 LLM 采样、parent 选择、检索结果、适配、cross 与整条进化轨迹的随机性。
- 由此必须把两个统计问题彻底分开：

```text
候选提交门  :  candidate × eval seeds      回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs     回答"开放世界的策略是否更好"
```

- *H1 现在不可识别*：§14.2 没有任何 run 级复制，`(Open_{t,r}, Closed_{t,r})` 这样的配对根本不存在。

*分析程序（建议直接写入 §8）*：

+ 先把 seed 层折叠（每个 run 取 seed 均值），再做 run 级分析：$d_{t,r} = mu + u_t + v_{t,r}$，$u_t ~ N(0, sigma_"task"^2)$，$v ~ N(0, sigma_"run"^2)$（S51）；或分层 bootstrap，按 task → run → seed 逐层有放回重抽（S54 显示传统 t 检验在嵌套结构下假阳性可 >45%）。
+ 条件间配对使用公共随机数（S52 附录 C.2），即 `(Open_{t,r}, Closed_{t,r})` 共享同一 seed 与同一初始任务配置。
+ task 仅 3 个时，只报 task 级效应，禁止泛化到 task 总体。

*r 的规划*：决定 r 的是 run 级 SD $sigma_"run"$，seed 再多也不缩小它；嵌套设计效应 $ "DE" = 1 + (m-1)rho $，群数少须用 $t$ 且自由度按群数算（S53）。$sigma_"run"$ 未知时用 pilot 估计并取上界，*仍禁止用 pilot 的效应量*（同 D3）。实践上 r 常需 $>= 12$，而 3 个 task 是更紧的约束。

*成本*：只加 seed 只作用于评测环节（5→34 约 6.8 倍）；重跑 campaign 则把整个研究过程乘以 r——多出一个数量级。而增加*变异源*比堆同一源更划算：S52 报告用前者可在约 51 倍计算节省下逼近理想估计量。*这也意味着 §8.3 的任务数与 §14.2 的 run 数是预算问题，不是"多跑几遍"的问题。*

*最小修补*：Task Contract 的 `statistics` 块拆成两组（`gate`：MDE / power / confidence，作用于候选提交门；`campaign`：r / 配对结构 / 分析模型，作用于 H1）；§8.1 明确分析单位是 `(task, run)`；§14.2 写出 `(Open_{t,r}, Closed_{t,r})` 的配对表与 r 的取值依据；预算中为 r 留出乘数。

== D2（重要）H1 的两种读法需要分开，六臂设计不足以识别机制迁移

*背景（Rev. 1 已接受的降级）*：计划的 H1 字面是工程效用假设（计划:1476-1480），对该假设 `C_open > C_closed` 本身有效，故不构成"致命"。但需要区分两个 estimand：

```text
H_U :  OpenWorld         -> UtilityGain     第一阶段可直接检验
H_M :  MechanismTransfer -> UtilityGain     需要因果识别设计
```

*Rev. 2 的更正*：Rev. 1 提出的六臂设计（以 C1 = 机制+代码 优于 C2 = 同长度随机代码 为判据）*不足以识别 $H_M$*——$C_1 > C_2$ 最多说明"相关信息优于随机信息"，而不是"机制迁移导致改进"。正确形式是接近析因设计：

```text
              Mechanism        not-Mechanism
ExternalCode     E + M                E
no Code            M                  (空)
对照：           E + M_matched   vs   E + M_shuffled   （token 匹配、同域但错配）
主估计量：       Delta_M = Y(E+M) - Y(E)
交互项：         Delta_{E x M}
```

*三点补充判断*：

+ *E 臂是"自然"的干预*：Shinka 的默认通道就是 code（D1），所以 E 臂无需任何改造即真实存在；M 臂（只给机制描述、不给代码）是人为构造的。因此*主比较应是 E 与 E+M*，M 臂用于回答"代码是否必要"这一更强的问题。
+ *`M_shuffled` 必须同域且 token 匹配*：否则它会退化为 Rev. 0 已指出的那个无效负对照（随机标签的 demonstration 依然有效，S29）。
+ *adaptation diff 不是识别*："改动看起来用了外部机制"属于中介证据（mediation evidence），不能替代因果识别；这一点与 Loreley 的立场一致——它逐字声明 inspiration 边只表示"上下文被重新提供"，"does not show that the agent used its contents or that it caused the resulting edit"（S56）。

*最小修补*：§8 采用上表的 4 + 1 臂；把"adaptation diff 显示机制被使用"降级为辅助证据；并在 §8.2 明确 $H_M$ 的主估计量是 $Delta_M$ 而非任何"open 优于 closed"的总效应。

== D3（重要）候选提交门的统计设计：数值正确，但适用范围必须限定

*Rev. 2 的限定*：Rev. 0/1 的功效表*只对候选提交门有效*（即"这个候选相对 baseline 是否真的更好"），把它外推为"整个设计的能力判断"是错的（见 D11）。表本身经两轮独立复算无误。

*证据*：

- 非中心 $t$（严格双侧 $alpha=0.05$）：

#table(
  columns: (auto, auto, auto, auto, auto, auto),
  inset: 4pt,
  stroke: 0.4pt,
  [*n*], [*d=0.5*], [*d=0.75*], [*d=1.0*], [*d=1.5*], [*d=2.0*],
  [5], [0.141], [0.254], [0.401], [0.711], [0.909],
  [10], [0.293], [0.562], [0.803], [0.987], [1.000],
  [20], [0.565], [0.889], [0.989], [1.000], [1.000],
)

- 样本量必须由公式给出：

```text
n_gate = f(MDE, sigma_d, alpha, beta)
近似闭式: n ≈ (z_{1-alpha/2} + z_{1-beta})^2 · sigma_d^2 / MDE^2
精确解:    非中心 t，ncp = MDE·sqrt(n)/sigma_d，df = n-1，对 n 数值求根
           （闭式会低估: d_z=0.5、power=0.8 时给 31.4，精确值 34）
```

  由领域预先指定 MDE；由 pilot 估 $sigma_d$（配对差的标准差，不是跨 seed 的池化标准差），必要时取置信上界。
- *n=5 真正意味着什么*：该设计下（power 0.8、$alpha=0.05$）最小可检测效应为 *$1.68 sigma_d$*。
- *用 pilot 效应量定样本量是已知陷阱*：效应量的条件估计在低功效下被系统性高估（winner's curse / Type M），据其定样本量几乎必然导致确认阶段功效不足（S42、S44）；pilot 的用途是估 $sigma$（S43）。
- *非参数门恒零*：$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$。
- *多重比较*：§8.1 并列 8 个"主要指标"（计划:951-962）而无单一主终点；若对三条件做 Bonferroni，$n=5$、$d=1$ 的功效降至 0.191。
- *confirmation 不独立*：§6.2 的流程（计划:801-803）使用"冻结 seed set"，而全文唯一的 seed 集是计划:603 的五个 seed；文档从未定义 pilot 的数据来源。*若二者共用，则 winner's curse 未消除*（条件式）。
- *不相交 seed 是必要条件、非充分条件*：还需（a）$n$ 按预注册 MDE 定；（b）pilot 数据排除在最终统计之外；（c）campaign 级 FWER 控制与 alpha spending（S45）；（d）预注册与分析冻结（S46）；（e）seed 集不得事后挑选。
- *α 与 lifetime 控制冲突*：§6.1 固定 per-test $alpha = 0.05$（计划:776），§6.2 自陈要解决 long-campaign 的 multiple testing（计划:785），二者不相容。
- *SGM 名实*：SGM 的机制是 certificate + 轨迹级风险分配 + predictable summable error budget（S11），计划把 e-value / error spending 推到"后续"（计划:806）；准确说法是，被推迟的那一项正是"统计门"名称的实质内容。
- *右删失*：`time to first improvement`（计划:954）无删失规则亦无生存分析，却规定用均值与置信区间汇总（计划:770）。

*最小修补*：`statistics.gate` 增 `mde` / `power` / `sigma_source` 并预注册；confirmation 用与 pilot 不相交且未事后挑选的 seed；给出 campaign 级 lifetime $alpha$ 预算；8 个并列指标收敛为 1 主 + 次要；时间类指标改 Kaplan–Meier / log-rank。

== D4（重要）护栏不可执行：两类里程碑与一致的治理

*指控（保留部分）*：§12.1（计划:1232-1242）是防止目标漂移的核心机制，但"milestone"与"Δ research capability"从未定义；计划不含工期、人力、算力预算与负责人；同目录缺少规范的决策沿革。

*Rev. 2 的更正*：Rev. 1 建议"每个 Phase 都补 `Delta bestVerifiedScore` 里程碑"——这*重现了它刚批评的问题*。Phase 0 的交付是冻结 schema 与 evaluator、Phase 1 是跑通 acquisition adapter，它们本来就不应要求产生算法改进。正确形式是两类里程碑：

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
   例: repo -> commit -> adapted candidate -> V_E 能否在限定时限/成本内稳定跑通
M_research   (研究期):     Delta verified algorithm capability
   例: best verified score 相对 baseline 的正向变化
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化,
              而不是要求每个基础设施里程碑立即涨 score
```

*证据（治理部分）*：

- "milestone" 全文仅出现一次（计划:1242），§9 用的是 Phase + 验收；"Δ research capability" 无度量定义。
- 按字面执行会自我触发：Phase 0 / Phase 1 的交付按设计都不产生算法能力增长。
- 两套停止规则并存且不同：§12.1 与 §14.4 的 Go 条件（计划:1375-1386）互不引用。
- 没有任何阶段的验收要求"产出 verified improvement"；§8.3 把首版主验收定为"基础设施能否减少真实研究成本"（计划:1006）。
- 全文唯一出现的日期是版本号（计划:30）；Sprint A–D 无时长、无 owner、无预算。
- *同目录事实*（见 §3.3）：共 10 份 `.typ`（排除本报告 9 份）。`algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml *19 行中 18 行逐字相同*，seed 列表完全一致；两份的 Experiment Record 同源而异；两份 mtime 同为 2026-09-18 14:32（被审计划 15:25）；*均无任何取代声明*。
- *`adapdc` 世代*：新版声明*部分条款*取代（ADR-001 文档效力表，非整篇废弃），并要求旧版顶部标注"部分条款已取代"——该动作未执行，旧版 `:32` 仍主张"不能同时保留相反的现行决策"、`:408` 仍写"不能让两份'现行真相'并存"；Makefile 通配符把两者都编成 PDF。另有第三套并存的统计提交门（ADA、OPL、本计划）。

*后果*：这仍是我判断*概率最高、后果最重*的失败方式，但定性是*治理缺陷*而非已发生的事实。

*最小修补*：按上文两类里程碑重写 §9 与 §12.1；新增"与既有计划的关系"一节，逐条写明 ARI 计划被取代的部分与 schema 真源、adapdc 旧版标注、evaluator 与 Experiment Record 的唯一真源；给决策加 `Decision_t → supersedes/retains → Decision_(t-1)` 字段。

== D5（重要）H2 没有对应的实验臂，且其问题已被先行工作占位

*指控*：H2（计划:1482-1496）声称存在比固定策略更高效的自适应策略，但 §8 与 §14 的条件只有 Closed / Open / Open-Unrelated，没有任何"自适应策略 vs 固定策略"的对照。H2 用本计划自身的设计无法证伪。

*证据*：条件枚举见计划:1046 与 1348；§7.2 把 bandit 推到"真实轨迹足够后"（计划:883-899），§9.6 把 policy learning 推到 Phase 5。Dream-RSI（S7）的问题设定与 H2 近乎同名；ASI-Evolve 已内置 UCB1/greedy/island sampler（S6）；EES 亦含 adaptive operator credit（S64）。

*最小修补*：H2 首版降级为"轨迹收集目标"，明确写"本阶段不检验 H2"；未来真正有区分度的问题是*外部获取与内部进化的联合分配*：

```text
动作空间:  { SearchWorld, Acquire, Adapt, Cross, Mutate, Evaluate }
问题:      在固定预算下如何在这六类动作间分配？
```

== D6（重要）未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（见 D10），并把 `understand` 写成管道的一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）；J 的分母（计划:318）与 §12 都没有"仓库能跑但机制抽不出"的成本与失败模式。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。*我的判断*：H1 若失败最可能死在"获取 + 理解"，而 §9.3 会误判为"开放世界收益低"。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"agent 上网找到他人已解出的高分方案"；§8.3 却优先选"存在可搜索公开实现"的任务（计划:994）、第二层用公开 benchmark（计划:1002）。旁证：EES 的厂商侧产品能力明列 "public external data, web research, pretrained models, and exploit discovery"，同时论文自认"未被标记的行不等于该任务满足闭数据协议"（S64）；其四项 `external-source routes` 被当作测量污点披露。MLE-bench 则必须明文禁止查看网上解法并用 Dolos 与 top-50 公开 notebook 比对（S24）。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046），无许可决策规则。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下向远程交互者提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 *License Provenance Gate*：来源与依赖清单（URL + commit + hash + 许可）、指纹与相似度比对（Copilot 的比对窗口约 150 字符量级，官方承认"在空白或近乎空白文件中命中要频繁得多"，S32）、许可分类白/黑名单与义务登记、命中的派生隔离与替换重写。旁证：TurboEvolve 在 Impact Statement 里把 provenance auditing 与 license verification 列为*未来建议*而非已实现能力（S55）——说明这是该领域普遍未做的缺口，不是本计划独有的疏忽。
+ *供应链*：计划:1217-1219 要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*`，经加密 DNS 外传（S34）。*计划:1219 的 secrets 规则防产出、不防安装期*。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问，2013 年样本 38%（S33）。

*最小修补*：把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12；给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离；给安装期网络与凭据策略；给外部资源快照归档。

== D7（次要但影响可复核性）引用卫生

*指控*：计划声称"进行了系统调查"（计划:214）并列有"关键参考实现与资料"附录（计划:1511），但从文档本身无法复核。

*证据*：正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名的外部系统共 17 个，其中 12 个没有任何条目。FunSearch 全文 0 次出现（经两轮独立 `grep -c` 核实为 0），MLE-bench、RE-Bench 亦 0 次。

*最小修补*：补 12 条引用 + 一节"相关工作与差异"，并按 §4 的清单逐条写明"谁已做到哪一步"。

== D8（次要）引文与命名漂移

#table(
  columns: (2.5cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*位置*], [*问题*],
  [计划:55、370], [`AHE / HarnessFix` 用斜杠并列，暗示为同一方法的别名；实为两个独立工作（S15 与 S16），且计划:1140-1141 本身把它们分作两个功能。],
  [计划:575], [`ReplayWorld` 非原文术语，Dream-RSI 原文用 replay simulator（S7）。],
  [计划:275], [字段名实为 `correct` 而非 "correctness"（S3）。],
  [计划:214], [正式题名为 "Huxley-Gödel Machine"（带连字符），S9。],
  [计划:55、1415-1416], [`SGM/RQGM` 并为一组，但按计划自己的六坐标模型，SGM 属 Commit 层、RQGM 属 Evaluator challenge 层。],
  [计划:1142、1414], [MGM 的核心机制是 comparative evolution / 跨谱系杂交（S10），"archive selection/mutation" 的归类丢掉了要点。],
  [计划:214], [MGM、RQGM、SE-GoS、MetaRSI、Dream-RSI 均为 2026 年 6–9 月的 preprint，却与 AlphaEvolve、DGM 并列成"系统调查"的既定文献；仅 Dream-RSI 标注了成熟度。],
  [—], [`github.com/codelion/openevolve` 已改名并跳转（S20），若引用旧地址需更新。],
)

== D9（次要）内部张力

+ *时间尺度与 Phase 顺序不一致*：$tau_K <= tau_pi$ 要求先经验后策略（计划:236-239），但 §9 把 Bridge Policy 放在 Phase 3/5、Skill RSI 放在 Phase 6，K 晚于 $pi$。
+ *与 MetaRSI 的路线冲突未解释*：MetaRSI 为"单一循环内核 + 联合调度"（三类算子 "Sharing one loop kernel and artifact vocabulary"，two-axis optimizer 联合决定算子顺序与提案策略，S14），与计划:231-239 的固定偏序及"evaluator anchor 原则上冻结"冲突，文档未说明为何拒绝。
+ *发现步骤的归属与验收缺失*：见 D10。
+ *Man1Lab 的接口性质被低估*：其 Decision Foundation 为非公开 API，Repository Adaptation 仍在 roadmap（S1、S39）；但这与"六阶段与五个规则确实存在于源码"不矛盾——文档化的阶段与已交付的能力是两件事。

= 三、我的证据

== 3.1 外部系统源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。Collection → Evidence → Verification → Ranking → Selection 见架构文档；六阶段见执行规划文档；五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0（2026-07-14），无论文。*两项能力断言不成立*：（1）无"问题 → 候选仓库"搜索路径（D10）；（2）其 `verified` 仅指发现层检查（$V_D$），非任务层可执行（$V_E$）。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive、多 provider 均为真。Apache-2.0，arXiv:2509.19349（ICLR 2026），PyPI `shinka-evolve` 0.0.7。*但 `metadata` 不是灵感通道*（D1）；正确通道为 `code` + `text_feedback`。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*：六个类型均在 `core/schema.py`，其中 `NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约（`runtime.py:118-122`、`core/gates.py`、`compiler.py:206-224`）。检索确为 "keyword + tag scoring"。arXiv:2605.20425。*过强的一处*：`sandbox_repo` 已接线到 runtime，但自述 "command builder only"、`execute_live` 分支返回 "not wired in framework phase"，即*只产出 docker 命令规格（dry-run）*；真实容器执行只在 `--docker` 旁路与 `SandboxBuilder`，且随包 adapter 多为 stub（外部 commit 为 `TODO_PIN`），*无已跑通的真外部仓库实例*。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
  [ASI-Evolve], [*sampler 断言为真*：`database/algorithms/` 下 random / greedy / ucb1 / island + factory。Apache-2.0，arXiv:2603.29640，无 PyPI。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline。],
  [Dream-RSI], [*论文真实*（arXiv:2609.14858）；*代码尚未发布*（仅 README 与 release plan），故计划:368 的"完整源码尚非稳定依赖"偏保守。许可无法确认。*命名偏差*见 D8。],
)

引用的研究谱系（计划:214、§9.7、§15）10 项*全部真实存在*，编号如下（均为已核实）：

#table(
  columns: (auto, auto, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*编号*], [*代码*], [*备注*],
  [DGM], [2505.22954], [有], [—],
  [HGM], [2510.21614], [有], [题名带连字符],
  [MGM], [2608.07645], [有], [核心为跨谱系杂交],
  [SGM], [2510.10232], [有（匿名仓）], [v2 至 2026-09-17；含可求和误差预算],
  [RQGM], [2606.26294], [无官方], [仅第三方非官方复现],
  [SE-GoS], [2609.08228], [无官方], [skill graph，动机为检索瓶颈],
  [MetaRSI], [2609.06396], [有], [单内核联合调度，见 D9],
  [AHE], [2604.25850], [有], [可证伪的 harness 修改],
  [HarnessFix], [2606.06324], [有], [轨迹诊断与修复],
  [RobustSGPO], [2609.09646], [无官方], [权限调度],
)

== 3.2 统计复核数字

见 D3 与 D11。功效采用非中心 $t$（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$），另以 $10^5$ 次蒙特卡洛独立验证，两者一致到小数点后三位；两轮外部复审的独立复算亦得到相同数值。$n=5$ 时最小可检测效应 $1.68 sigma_d$。

== 3.3 文档族物证

自检命令（在包含这些文件的目录下运行即可复现本报告的全部目录层断言）：

```text
ls -la *.typ
grep -n "seeds:" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
grep -nE "supersede|取代|废弃|作废|以本文为准" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
```

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版标注；该标注属待执行的"C0 本地落库动作"，旧版（09-09 20:13）未加标注；Makefile 通配符把两者都编成 PDF。
- `algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml 19 行中 18 行逐字相同（含 seed 列表），Experiment Record 同源而异；两份 mtime 同为 09-18 14:32（被审计划 15:25）；互不引用，均无取代声明。
- 至少三套并存的统计提交门（ADA、OPL、本计划）。
- 该族另有引用不存在文件的情况（如 `adapdc_architecture_report.typ`、`research-foundations.md`）。
- *可移植性限度*：以上第 1、2、4 条依赖本地目录状态，本轮外部复审的证据集中不含这些文件，故其正确标注是"该证据集内不可独立复现"，而非"不成立"。第 3 条可从计划文本本身复核。

== 3.4 排版与构建实测

构建：`typst 0.15.1` 下 `typst compile` 退出码 0、无 warning，输出 20 页 A4。A4 页宽 595.276pt，页边距 68.031pt，正文右边界 527.245pt。测量方法：`pdftotext -bbox` 逐词取框 + 解压 PDF content stream 读取每个 text run 的笔位，两法交叉一致。

#table(
  columns: (auto, auto, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*源行*], [*宽度*], [*区间*], [*判定*],
  [46], [545.6pt], [24.83–570.44], [溢出页边距 43.2pt/侧，未越页],
  [80], [486.0pt], [54.65–540.62], [溢出 13.4pt/侧],
  [376-385], [505.2pt], [45.04–550.24], [溢出 23.0pt/侧],
  [408-413], [476.2pt], [59.54–535.74], [溢出 8.5pt/侧],
  [833-844], [577.9pt], [8.71–586.57], [溢出 59.3pt/侧，距页边 8.7pt],
  [951-962], [≈701.5pt], [−53.13 至 ≈648.4], [*越页宽约 106pt，两侧各裁约 53pt*],
)

结论：6 处显示公式溢出页边距，其中仅 *1 处*（计划:951-962 的 `Y` 指标元组）真正越出纸张被裁切——PDF 第 13 页该行只抽到 "external con" 即断。其余五条虽越边距但仍在页面内。这份文档的核心主张就是一组测量指标，而它的主指标清单在纸面上被裁掉了最后两项。

= 四、与先前工作的关系（Rev. 2 整体重写）

*Rev. 2 撤回 Rev. 1 的结论*。Rev. 1 称"外部已验证实现 × 反事实贡献度量 × commit/license/hash 级 provenance 尚未被占位"。经一轮 arXiv 口径的穷尽检索（约 40 组查询 + 逐篇 HTML 核对），该结论*不成立*。清单如下（A = 外部实现进入种子/灵感/archive；B = 对单条灵感做消融或反事实归因；C = 运行时从网络获取并进入循环）：

#table(
  columns: (2.6cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*工作*], [*占位*], [*依据*],
  [FunSearch 等三篇], [A（弱）], [冻结 evaluator + 程序库 + 检索高分实现进 prompt；初始程序由人给出（S18、S19、S20）],
  [TurboEvolve　2604.18607], [A], [`seed-pool injection`：把既有解池聚类后分配到各 island 作种子（含 copy-and-mix 扰动与精英保留）；*池的来源是作者自跑 checkpoint，非人类解、非网络获取*；无 provenance，逐 seed 归因缺失；provenance/license 被列为未来建议（S55）],
  [Loreley　2608.19703], [A + B（负）], [以完整 git commit 为 evolutionary artifact、isolated worktrees、项目自带 evaluator、QD archive，并显式区分 parent 边与 inspiration 边；逐字声明 inspiration 边"does not show that the agent used its contents or that it caused the resulting edit"；并自认未做 inspiration 消融（S56）],
  [Kernel Foundry　2605.30359], [A + B], [从 KernelBook 检索 top-5 核作 few-shot 初始化 → 多岛进化；含专家初始化消融（S57）],
  [TuneNNGen　2607.05704], [A + B], [外部同族仓库代码作 prompt 指导；等预算的 target-only vs source-guided；direct-copy 分解 + 负对照——*目前最接近"某条外部灵感是否导致改进"的已发表反事实*（S58）],
  [KAPSO　2601.21526], [A + C], [research 阶段返回 candidate repositories 作 seeds，并带 repository provenance（S59）],
  [AutoSOTA　2604.05550], [A + C], [从论文 PDF 抽取 GitHub 链接并规范化为初始仓库（S60）],
  [MLE-STAR　2506.15692], [A + C + B（块级）], [用搜索引擎检索 web 上的模型构成初始解；含代码块级消融（S61）],
  [MARCO　2505.03906], [B + C], [实时检索近期会议论文的优化技术；有/无 web search 对比（S62）],
  [DeepEvolve　2510.06056], [B（通道级）+ C], [联网 PubMed/arXiv 检索进入迭代精化环；含 deep research 消融（S63）],
  [EES　2609.17590], [强基线，非先例], [validation gate + 持久记忆 + operator credit；其 `external-source routes` 实为外部数据/答案查找，不是取外部实现；自认"不估计这些机制的边际收益"（S64）],
)

*由该清单得出的判定*：

+ *"运行时开放世界获取 + 进化闭环"已被占据*（KAPSO、AutoSOTA、MLE-STAR；知识侧由 MARCO、DeepEvolve 占据）。故 Rev. 1 与复审方各自的猜测都需要修正。
+ *"外部实现 × 反事实贡献"已被占据到相当程度*（Kernel Foundry 的初始化消融、TuneNNGen 的等预算对照与 direct-copy 分解）。
+ *真正可能尚未被占位的只剩一项*：*在进化 archive 内部、带 commit/license/hash provenance 的单条外部灵感的反事实归因*。即便这一项，也已被 TuneNNGen 与 Kernel Foundry 逼近（它们没有 provenance，也不是 archive 内的逐灵感归因）。
+ 因此新颖度状态应记为 *未决（unresolved）*：需先按上表逐一做源码/论文级比对，再决定差异表述。计划当前 §1.6/§2.2/§1511 的"系统调查"措辞与 §4 的差异主张都还没有完成这一步。

= 五、建议与判据

== 5.1 结论

*有条件推进——推进到能力探针（Probe-0），尚不到 H1 的 A/B 实验。* 理由：源码层判断已稳定；但（a）H1 现在不可识别（D11），（b）新颖度未决（§4），（c）最窄切片的第一跳尚无 owner（D10）。在这三项明确之前启动 Phase 2 的 A/B，等于用一个不知道能不能测的东西去测一个不知道是否新的东西。

== 5.2 Probe-0：能力探针（建议的下一步）

```text
Problem -> Search -> Source@Commit -> Snapshot -> Adapt -> V_E -> Shinka -> Child
记录: (C_search, C_understand, C_adapt, C_evaluate)   四项成本 + 三项失败计数
失败计数: search_failed / comprehension_failed / mechanism_mismatch
```

判定标准（不检验 H1、不需复杂统计）：*一条真实外部实现能否完整穿过这条链*，以及四项成本是否落在可接受范围。若这一步就昂贵、脆弱或语义映射失败，则 H1 的实验设计没有意义；若顺畅，再进入真正 campaign 级的 A/B。

== 5.3 五项必改（在 Probe-0 之前或同时完成）

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（`use_text_feedback = true`）+ `metadata` 三分；写明 cross 对位段无此通道、partner 的 code 会重复出现、重复评测产生第二行；`text_feedback` 定位为 MVP 捷径而非 canonical schema。],
  [*拆开两级验证并补上获取*（D10）：acquisition = Search（现成 GitHub/Web/paper 检索的薄封装，可借 KAPSO／AutoSOTA／MLE-STAR 的形态）+ Ingest（借 Man1Lab schema 与 $V_D$，不引其 runtime）；明确 $V_D$ 不等于 $V_E$，只有 $V_E$ 通过者进入种群。],
  [*分离两套统计设计*（D3 + D11）：`statistics.gate`（MDE／power／confidence，作用于候选提交门）与 `statistics.campaign`（r／配对结构／分析模型，作用于 H1）分开；§8.1 明确分析单位是 `(task, run)`；§14.2 写出 `(Open_{t,r}, Closed_{t,r})` 的配对表与 r 的依据；预算里为 r 留乘数。],
  [*按 E × M 析因重写 §8.2*（D2）：4 + 1 臂（E+M／E／M／空 + shuffled mechanism 对位），主估计量 $Delta_M$；"adaptation diff 显示机制被使用"降级为中介证据；若只主张 $H_U$，则删除 §1.6／§2.2 的机制迁移措辞。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$（二元验收 + 时限 + 成本上限）与 $M_"research"$（$Delta$ verified capability）分开，proxy guard 约束成本/能力比长期不恶化；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

== 5.4 建议改

+ 把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12（D6）。
+ 给 evaluator 的来源黑名单与抄袭比对（D6）。
+ 加 License Provenance Gate 与 copyleft 派生代码隔离（D6）。
+ 按 §4 的清单补参考文献（D7），并把 5 个 2026 年 6–9 月的 preprint 标注成熟度（D8）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行（实测可将最宽者从 ≈701.5pt 降到边距内）。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.5 Go / No-Go 判据

*Probe-0 → H1 A/B 的门槛*：一条真实外部实现完整走通全链且三项失败计数与四项成本可接受。

*H1 A/B 的前提*：run 级复制的配对表存在（D11）；一个预注册的单一主终点与 MDE；一个与 Open 条件 token 数匹配的负对照（D2）；confirmation 使用不相交、未事后挑选的 seed（D3）；外部搜索/验证/适配的开销全部计入 open 臂。

*在满足上述前提后*：若 `Delta` 不显著，必须同时报告*搜索失败率*与*机制抽取失败率*，以区分三种结论——"没找到候选"、"没读懂仓库"、"机制不可迁移"。计划现有判据（计划:1076）无法区分，这是最需要修补的单点。

== 5.6 什么会使我改变判断

+ 若作者指出一条三轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1 的第一部分。
+ 若作者给出文档外的定义，说明 pilot 与 confirmation 使用不相交且未事后挑选的 seed → D3 该条降为部分成立。
+ 若作者给出已被别的文档定义的里程碑与 $Delta$ 度量 → D4 的"不可执行"部分撤回。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级；但在此之前 H1 不可识别这一判断不变。
+ 若 Man1Lab 或其它组件在后续版本实现了"问题 → 候选仓库"的搜索 → D10 的该部分撤回（需附版本与调用点）。
+ 若 §4 清单中的某条被证明与计划的差异主张无关 → 相应收窄。

= 六、我撤回或修正的判断

*Rev. 0 内部已修正（第一轮反证）*

#enum(
  [*公式越界范围*：实测越出*页面*被裁切的只有 1 处（计划:951-962，≈701.5pt，两侧各裁约 53pt）；其余 5 处仅溢出页边距。],
  [*灵感槽位数*：论文与 `island_small`／`island_large` preset 为 4/2，`island_medium` 与类默认（`dbase.py:63-64`）为 1/1。],
  [*SGM 的"唯一提供物"*：SGM 另含 certificate → 状态转移协议与 checkpoint / held-out 审计；被推迟的那一项才是使统计门名实相符的机制。],
)

*Rev. 1 阶段（对第一轮复审的核验）*

#enum(
  [*D1 的补救措施*：`Program.text_feedback` 已是现成的 per-inspiration 通道，不必改核心；但见 Rev. 2 的相邻性更正。],
  [*archive 不变量*：灵感"必须 `correct=1` 且已入 archive"仅对默认路径成立；`best_program_id` 路径只检查 `prog.correct`（`inspirations.py:57-67`），fix 的 ancestor 亦无此过滤。],
  [*AgentCo-Op 的能力*：`sandbox_repo` 只产出 docker 命令规格（dry-run），不启动隔离环境。],
  [*Experiment Record 的同一性*：与 ARI 计划"逐字相同"是错的——Task Contract 18/19 行相同，Experiment Record 同源而异。],
  [*ARI 计划的日期*：文件 mtime 为 09-18 14:32，不是 09-17。],
  [*样本量建议*：$n>=20$ 无依据且与自身表格冲突，改为公式化程序。],
  [*"proxy drift 已经发生"*：修正为"治理缺陷已确认"。],
  [*"许可传染"*：按 AGPL §2 的条件式表述重写。],
  [*引用行号*：`license` 三处应为 533、626、1046。],
)

*Rev. 2 阶段（对第二轮复审的核验）*

#enum(
  [*cross 段与反馈的相邻性*："partner 的 `text_feedback` 不与代码相邻"是错的：它不出现在 dedicated crossover block 中，但在 eval history 中与其自身 code 相邻；partner 的 code 在同一 message 中出现两次；`CROSS_ITER_MSG` 的反馈段填的是 parent 的反馈。],
  [*`text_feedback` 的定位*：作为 MVP 零改核捷径成立，作为长期 canonical schema 不成立——它有评测反馈语义、单字段约束与重复评测第二行问题。],
  [*D10 的定级*："第一跳没有实现路径"过强，改为"关键集成缺口"：Man1Lab 无 Search 不等于 Search 能力不存在，且已有可直接借鉴的已发表同型流水线。],
  [*D2 的实验设计*：六臂设计不足以识别 $H_M$，改为 E × M 析因 + shuffled mechanism 对位。],
  [*D3 的适用范围*：功效表只对候选提交门有效，之前把它外推为"整个设计"的能力判断是错的。],
  [*D4 的修补方案*："每个 Phase 都要求 $Delta$ score"会把自我触发问题重新引入，改为 $M_"capability"$ 与 $M_"research"$ 两类里程碑。],
  [*§4 的新颖度结论*："外部实现 × 反事实贡献 × provenance 尚未被占位"是错的，已按最近邻清单重写。],
  [*最终结论的含义*：从"修五项必改后进入窄切片"改为"推进到 Probe-0 能力探针，尚不到 H1 的 A/B 实验"。],
)

另有两项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属（两次独立核实结论冲突，按"安装路径不确定"处理）；§4 清单之外是否还有非 arXiv 口径的最近邻工作。

= 附录 A：审查覆盖范围

三轮共 32 个独立审查轴。Rev. 0（20 轴）：五个核心系统源码级核实；Gödel machine 谱系；harness 谱系；统计与实验设计；内部一致性与可行性；与 ADA／OPL／ARI 的一致性；与 adapdc 系列的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；Typst 构建与排版实测；两轮专项反证；引用元数据三轮核实。Rev. 1（6 轴）：ShinkaEvolve 的 `text_feedback` 通道与 inspiration 过滤不变量；Man1Lab 搜索能力（三快照口径）；AgentCo-Op 的 repo 执行能力；目录层文档治理事实；许可表述精度；样本量程序的统计陷阱。Rev. 2（6 轴）：cross 模式 prompt 构成的逐行核对；TurboEvolve、Loreley、EES 三篇的逐篇核实；一轮穷尽式最近邻检索（约 40 组 arXiv 查询）；experimental unit 错位的方法学核实。

= 附录 B：来源清单

*核心依赖*

- [S1] Man1Lab — https://github.com/maniac1um/Man1Lab （MIT）
- [S2] Man1Lab on PyPI — `man1lab` v1.3.0（2026-07-14）
- [S3] ShinkaEvolve — https://github.com/SakanaAI/ShinkaEvolve ；arXiv:2509.19349（ICLR 2026）
- [S4] ShinkaEvolve on PyPI — `shinka-evolve` 0.0.7
- [S5] AgentCo-Op — https://github.com/ma-compbio-lab/AgentCo-Op ；arXiv:2605.20425
- [S6] ASI-Evolve — https://github.com/GAIR-NLP/ASI-Evolve ；arXiv:2603.29640
- [S7] Dream-RSI — https://github.com/zhengkid/Dream-RSI ；arXiv:2609.14858

*RSI 与 harness 谱系*

- [S8] Darwin Gödel Machine — arXiv:2505.22954
- [S9] Huxley-Gödel Machine — arXiv:2510.21614
- [S10] Mendel Gödel Machine — arXiv:2608.07645
- [S11] Statistical Gödel Machine — arXiv:2510.10232
- [S12] Red Queen Gödel Machine — arXiv:2606.26294
- [S13] SE-GoS — arXiv:2609.08228
- [S14] MetaRSI — arXiv:2609.06396
- [S15] AHE — arXiv:2604.25850
- [S16] HarnessFix — arXiv:2606.06324
- [S17] RobustSGPO — arXiv:2609.09646

*先前工作、基准与理论*

- [S18] FunSearch — Nature 625, 468–475, doi:10.1038/s41586-023-06924-6
- [S19] AlphaEvolve — arXiv:2506.13131
- [S20] OpenEvolve — https://github.com/algorithmicsuperintelligence/openevolve （Apache-2.0）
- [S21] The AI Scientist — arXiv:2408.06292
- [S22] AIDE — arXiv:2502.13138
- [S23] PaperBench — arXiv:2504.01848
- [S24] MLE-bench — arXiv:2410.07095
- [S25] RE-Bench — arXiv:2411.15114
- [S26] Open-endedness 议程 — PMLR 235:20597–20616 / arXiv:2406.04268（两版作者序不同）
- [S27] OMNI-EPIC — arXiv:2405.15568
- [S28] POET — arXiv:1901.01753
- [S29] Min et al., *Rethinking the Role of Demonstrations* — arXiv:2202.12837（EMNLP 2022）

*风险论据*

- [S30] pip secure installs — https://pip.pypa.io/en/stable/topics/secure-installs/
- [S31] AGPL-3.0 §0、§2、§5(c)、§13 — https://www.gnu.org/licenses/agpl-3.0
- [S32] GitHub Copilot code referencing（2023）
- [S33] Pew Research, *Link Rot and Digital Decay*, 2024-05-17
- [S34] PyTorch, compromised nightly dependency（torchtriton）
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`；`inspirations.py:57-67, 69-88, 90-108, 110-127, 143-242, 342-353`；`core/config.py:62`
- [S39] Man1Lab 搜索能力（快照 `5376e58d` = main HEAD；PyPI 1.3.0 同源）— `src/providers/github/client.py:43, 48, 61`；`src/providers/github/collection.py:1, 46, 56-58, 88, 124-153`；`src/providers/github/verification.py:1, 47`；`docs/reviews/1.2_github_collection_provider/audit.md:49, 55, 171, 182`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op repo 执行能力（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 3, 28, 62-83, 86-130`；`agentcoop/backends/__init__.py:15`；`agentcoop/core/runtime.py:118-122, 167`；`agentcoop/core/gates.py`；`agentcoop/compiler.py:206-224, 388, 405`；`agentcoop/integrator.py:75-90`；`agentcoop/core/repo_collaboration.py:407-423`；`agentcoop/core/sandbox_build.py:303-331`；`agentcoop/wrappers/gears/adapter.py:47`
- [S41] AGPL-3.0 §0 与 §2 原文（`covered work` / "output … only if"）— https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-or-later.txt
- [S42] Zöllner & Pritchard, AJHG 80(4):605-615, 2007 — doi:10.1086/512821
- [S43] Leon, Davis & Kraemer, J Psychiatr Res 45(5):626-629, 2011 — PMID 21035130
- [S44] Gelman & Carlin, Perspect Psychol Sci 9(6):641-651, 2014 — doi:10.1177/1745691614551642
- [S45] DeMets & Lan, Stat Med 13(13-14):1341-1352, 1994 — doi:10.1002/sim.4780131308
- [S46] Nosek et al., PNAS 115(11):2600-2606, 2018 — doi:10.1073/pnas.1708274114
- [S47] R `stats::power.t.test`（非中心 $t$ 求根与 `strict` 约定）；Cohen 1988

*Rev. 2 新增：方法学（experimental unit 与嵌套设计）*

- [S48] Hurlbert, *Pseudoreplication and the design of ecological field experiments*, Ecol Monogr 54(2):187-211, 1984 — doi:10.2307/1942661
- [S49] Lazic, Clarke-Williams & Munafò, *What exactly is 'N' in cell culture and animal experiments?*, PLoS Biol 16(4):e2005282, 2018 — doi:10.1371/journal.pbio.2005282
- [S50] Makin & Orban de Xivry, *Ten common statistical mistakes to watch out for*, eLife 8:e48175, 2019 — doi:10.7554/eLife.48175
- [S51] Gelman & Hill, *Data Analysis Using Regression and Multilevel/Hierarchical Models*, 2006 — doi:10.1017/CBO9780511790942
- [S52] Bouthillier et al., *Accounting for Variance in Machine Learning Benchmarks*, MLSys 2021 — arXiv:2103.03098（附录 C.2 Pairing）
- [S53] Hemming et al., *Sample size calculations for cluster randomised controlled trials*, BMC Med Res Methodol 11:102, 2011 — doi:10.1186/1471-2288-11-102
- [S54] Saravanan, Berman & Sober, *Application of the hierarchical bootstrap to multi-level data* — bioRxiv doi:10.1101/819334

*Rev. 2 新增：最近邻工作（§4 的清单）*

- [S55] TurboEvolve — arXiv:2604.18607（`seed-pool injection`；池来源为 run checkpoints）
- [S56] Loreley — arXiv:2608.19703（commit 级 artifact、parent/inspiration 分边、engagement 与因果的显式区分；Apache-2.0 代码公开）
- [S57] Kernel Foundry — arXiv:2605.30359（KernelBook 检索 top-5 核作 few-shot 初始化 + 专家初始化消融）
- [S58] TuneNNGen — arXiv:2607.05704（外部同族仓库代码指导 + 等预算对照 + direct-copy 分解）
- [S59] KAPSO — arXiv:2601.21526（research 返回 candidate repositories 作 seeds，带 repository provenance）
- [S60] AutoSOTA — arXiv:2604.05550（从论文 PDF 抽 GitHub 链接 → 初始仓库）
- [S61] MLE-STAR — arXiv:2506.15692（搜索引擎检索 web 模型构成初始解 + 块级消融）
- [S62] MARCO — arXiv:2505.03906（实时检索会议论文技术 + 有/无 web search 对比）
- [S63] DeepEvolve — arXiv:2510.06056（联网 PubMed/arXiv 检索进入精化环 + deep research 消融）
- [S64] Evolutionary Ensemble Search — arXiv:2609.17590（validation gate + 持久记忆 + operator credit；`external-source routes` 指外部数据/答案查找）

*同目录文档*

- [S35] `algorithm_research_infrastructure_plan.typ`
- [S36] `ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
