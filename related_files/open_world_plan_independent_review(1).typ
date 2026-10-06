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
  #text(size: 9.5pt)[本报告版本：*Rev. 1*（2026-09-18）· 含对审查反馈的独立核验与修订记录]
  #v(2pt)
  #text(size: 9.5pt)[结论：*有条件推进（Conditional Go）*]
  #v(2pt)
  #text(size: 9.5pt)[本报告不含对尚未存在的实验结果的评价]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 1 总评*：这是一份方向正确、且经验基础罕见的计划——它点名的 17 个外部系统经源码级逐一核实，*没有一个是不存在的*，对其中五个核心依赖的特征描述基本准确。经第二轮核验（对反馈方的挑战逐条复核，不采信任何一方的转述），我的判断有两处方向相反的移动：

  #v(3pt)

  + *工程风险低于 Rev. 0 的判断*：外部灵感注入通道是存在的（`Program.text_feedback` 是现成的 per-inspiration 语义通道），不需要修改 ShinkaEvolve 核心，因此 Rev. 0 关于 D1、D2 的两条"致命"定级撤回。
  + *前提风险高于 Rev. 0 的判断*：计划的第一跳（开放世界获取）所依赖的能力不存在——Man1Lab 当前没有任何"问题 → 候选仓库"的搜索路径，而计划把"开放世界获取已有相当成熟的实现基础"列为第一条工程认识（计划:58）。这一段在 Rev. 0 中被我定级过低（见 D10）。

  #v(3pt)

  故 Rev. 1 的最重要结论不是"哪一根柱子坏了"，而是：*这份计划的可执行部分比它自己描述的更少，且最窄切片的第一跳是空的*；而它的核心实验与统计门，按现文本仍无法给出可信答案。
]

= 零、审查方式与限度

== 0.1 方法

本报告由两轮构成。第一轮（Rev. 0）为全文精读 + 20 个并行独立审查轴，核查分四类：

+ *源码级事实核实*：对被点名的外部系统，抓取其公开源码、配置与论文原文，逐条比对计划中的具体断言（阶段名、规则名、字段名、类型名、槽位数、检索机制）。
+ *反证尝试*：对本报告最要命的两条技术指控，专门指派独立核查者以"尽力推翻该结论"为目标复核。
+ *统计复核*：对统计设计独立复算（非中心 $t$ 分布 + $10^5$ 次蒙特卡洛双重验证）。
+ *构建与排版实测*：在 typst 0.15.1 下实际编译，并用 `pdftotext -bbox` 与 PDF content stream 解压两种方法交叉测量元素实际落点。

第二轮（Rev. 1）为 *对审查反馈的独立核验*：收到对 Rev. 0 的逐条挑战后，新增 6 个审查轴，对反馈方的源码判断与 Rev. 0 自身的断言重新做源码/文献核验。原则与第一轮相同：*不采信任何一方的转述，只采信可复现的出处*。核验结果与处理见 §0.5；其中反馈方有一处事实错误，已记入 §0.6。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行，不存在可评价的数据。
- 外部系统的核实基于 2026-09-18 的公开快照；被审计划本身未固定版本，故任何断言都可能随上游更新失效（这本身就是 D10 与 D9 的一部分）。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"；§4 只回答它与已知先前工作的关系。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S47）见附录 B。第三方的源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → Rev. 1）

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*Rev. 0 的说法*], [*第二轮核验结果*], [*Rev. 1 处理*],
  [R1　D1 补救措施], [要注入机制文本"必须自定义 `PromptSampler`，即修改核心路径"], [*不成立*。`prompts_base.py:74-79` 逐程序追加 `Text feedback:`；`sampler.py:147-157` 把 archive+top-k 全部送入该函数，与 patch 类型无关], [已改写：`text_feedback` 是现成的 per-inspiration 通道，不必改核心；补 cross 例外与三条限定],
  [R2　D2 定级], ["致命"（无法归因）], [*部分成立*。计划的 H1 字面是工程效用假设（计划:1476-1480），对该假设 `C_open > C_closed` 本身有效], [降为"重要"，并区分 H_U 与 H_M 两个 estimand],
  [R3　新发现：获取前端], [未指出], [*成立且重要*。Man1Lab 无任何"问题 → 候选仓库"路径，`search_repositories` 抛 `NotImplementedError`], [新增 D10，定级与 D1 同级],
  [R4　AgentCo-Op 能力], [`sandbox_repo` 为"真实 backend"], [*过强*。"command builder only"；`execute_live` 分支返回 "not wired in framework phase"], [已改写为"已接线但只产出 docker 命令规格（dry-run）"，并补真实执行路径与其 stub 事实],
  [R5　Experiment Record], ["逐字相同"], [*错*。同源但字段集不同（新增 `external_inspiration_ids` 等，命名亦不同）], [已改为"Task Contract 高度重合（18/19 行），Experiment Record 同源而异"],
  [R6　ARI 计划日期], ["（09-17）"], [*错*。该文件 mtime 为 09-18 14:32；09-17 是其文内一处检索日期], [已改为 09-18，并注明差异],
  [R7　统计样本量], ["seed 数提到 $n>=20$"], [*无依据且与 Rev. 0 自身表格冲突*（n=20、$d=0.5$ 时 power 仅 0.565）], [已改为 `"n = f(MDE, sigma_d, alpha, beta)"` 的程序化表述与 MDE 论证],
  [R8　proxy drift], ["已经发生"（事实层）], [*证据不足*。"新证据 → 改架构"本身可能正是避免目标固化], [收窄为"治理缺陷已确认；漂移迹象在 adapdc 世代"；撤回"已发生"的推断],
  [R9　许可风险表述], ["许可传染"，引 AGPL §5(c)/§13], [*过强*。漏掉 AGPL §2 的条件句与"复制/改编"事实前提], [已按 §2 重写为 License Provenance Gate],
  [R10　行号], [`license` 出现在"计划:527"等三处], [*错*。应为 533、626、1046], [已更正],
)

== 0.6 我保留的分歧

以下四项我不接受反馈方的意见，理由与证据一并列出：

+ *"目录里只有 3 份相关文档"*：事实核验为 10 份 `.typ`（含本报告；排除本报告为 9 份，其中计划类 7 份、评审/调研 2 份），`pdf/` 中 10 份 PDF 齐备。这是访问范围差异，不是存在性差异。
+ *AgentCo-Op 的 typed IR 并非"未接线的声明"*：`NodeSpec` 由 `runtime.py:118-122` 按 `node.backend` 派发执行；`GatePolicy` 由 `core/gates.py` 产出 patch 动作并在 `runtime.py:167` 累加 `gate_activations`；`EvalContract` 由 `compiler.py:206-224` 构造并挂载（388/405），被 `integrator.py:75-90` 与 `reviewer.py` 实际使用。*未接线的只有"执行外部仓库"这一条路径*。因此 §4.2 的"typed IR 值得吸收"仍然成立——被修正的是 runtime 结论，不是设计价值。
+ *D2 的降级附带条件*：若作者只主张 $H_U$，则必须删除计划中"机制迁移"式的措辞（见 D2）。
+ *`text_feedback` 通道不是免费的*：它有三条限定（见 D1 的"通道的真实代价"）。

= 一、我的认识

== 1.1 这份计划真正在说什么

剥掉术语后，它的论证链是五步，我按原意复述：

#enum(
  [*目标重述*（计划:40-49）：唯一稳定目标是"使真实算法研究更适合 AI 自动、可靠、长期地推进"，ADA、OPL、Kimi 插件、Research OS 都是可替换手段。],
  [*工程顺序*（计划:153-172）：research need → existing solution search → composition → adapter → extension → new implementation；"架构可丢弃，研究能力不变"。],
  [*缺口定位*（计划:289-301）：开放世界获取（Man1Lab）与算法进化（ShinkaEvolve）已有成熟底座，真正断裂的是 `CandidateResource → Program/Inspiration` 这一跳，即 ExternalInspiration Adapter。],
  [*最窄切片*（计划:403-413）：Discovery → ExternalInspiration → Evolution → Frozen Evaluator → Experiment Ledger，首版不建大而全基础设施。],
  [*可证伪假设*（计划:1469-1509）：H1 = 外部已验证实现作为一等进化灵感能提升改进效率；H2 = 存在比固定策略更好的自适应搜索策略；H1 不成立则无需投入 H2。],
)

第 3 步是这份计划的承重点：*它假定"开放世界获取"与"算法进化"两段都已经有货架，缺的只是中间那一跳。* 两轮核验下来，第二段（算法进化）确实成立，第一段不成立——缺口比计划描述的更大，位置也更靠前（D10）。

== 1.2 我认可的部分

这些判断我经核实后同意，且认为它们是这份文档的主要价值：

+ *目标层的重新收束是对的。* 把"提高基础设施完整度"与"提高算法改进能力"分开，并明确前者是可丢弃手段，这一步在同类计划里通常缺席。
+ *"架构可丢弃"作为硬约束有其可操作性*（计划:169）：它给后续所有组件决策提供了一个统一的否证条件。
+ *多时间尺度分离*（计划:235-239，$tau_A < tau_K <= tau_pi < tau_H < tau_E$）在归因上是必要的：若算法、经验、策略、harness 与评测同时变化，收益不可归因。
+ *从第一天记录轨迹以备将来 replay*（计划:581）：这一条是低成本、高期权价值的决策，且不依赖任何未验证假设。
+ *不继承 Man1Lab 的生成策略*（计划:474）：经源码核实为必要——其 `generation_decision.py` 的 `_STANDARD_CONSTRAINTS` 逐字包含 "Do not redesign algorithms or network architecture." 与 "Do not change training objectives."，直接继承会扼杀 improvement loop。
+ *把外部实现交给自有 evaluator 定生死*：ShinkaEvolve 的 archive 只接纳 `correct = 1` 的个体，这与计划"外部实现必须可验证"的立场天然一致（见 D1）。
+ *任务选择的阶梯*（计划:998-1004）：toy → 公开 benchmark → 真实项目 probe，顺序合理。
+ *外部事实的可核实性*：见 §3.1。一份计划点名的每个系统都真实存在且描述基本准确，这在实际审查中属于少数情况；它说明作者确实读过源码，而不是凭印象引用。

= 二、我的怀疑

下面十条按后果排序，每条给出：指控、证据、若成立的后果、最小修补。*证据*一栏只列可复现的出处；推理与判断明确标为我的判断。*D10 为 Rev. 1 新增，其重要性位列第一组，编号沿用以避免破坏交叉引用。*

== D1（重要，Rev. 0 曾定为致命）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（字段清单见计划:529-536），而 `metadata` 对 prompt 不可见，因此该工程决策按文中所述不成立。*Rev. 0 在此基础上进一步称"要注入机制文本必须改核心"，这一句是错的*——正确通道已存在。

*证据一：metadata 确实不可见（已核实，快照 9912af12）*

- 构造 prompt 的路径可枚举：`shinka/core/sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(parent.combined_score, parent.public_metrics)`，及可选 `text_feedback_section`。cross 的专属段落 `prompts_cross.py:57-73` 的 `get_cross_component()` 只写 `inspiration.code` 与 `perf_str(...)`。
- 全仓库在 prompt 路径上读取 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支读 `stdout_log`/`stderr_log`），其触发条件是无正确父本，且不参与 mutation 与 cross。
- 第二条更弱的路径：`metadata["patch_name"]` → 元总结器（`summarizer.py:249,282`）→ `meta_recommendations` → `sampler.py:118-124` 追加到系统消息，但条件是 `patch_type != "cross"`（cross 被显式排除），且内容经 LLM 摘要。
- 计划:529-536 列出的六个键在仓库中 *零命中*：既无写入者也无读取者。
- 覆盖性：全部分支（`main`、5 个 `fix/*`、9 个 `split/*`、`lean_support`，无 `dev`）的 `sampler.py` 内容一致。

*证据二：正确的注入面是现成的（Rev. 1 更正）*

- `prompts_base.py:74-79`：循环体内对*每一个*程序追加 `Text feedback:` 与其 `prog.text_feedback`；开关由 `sampler.py:156`（常规）与 `:243`（fix）传入，默认 `False`（`core/config.py:62`）。
- `sampler.py:147-157` 把 archive 与 top-k 合并后*全部*送入该函数，与 patch 类型无关——因此 cross 模式的 eval history 也带反馈。
- adapter 可以自行设置该字段：`Program` 的 `text_feedback`（`dbase.py:174`）经 `Database.add()` 原样落库（`dbase.py:849-857, 870, 890`），且全仓库*无任何* `UPDATE programs SET text_feedback`（UPDATE 只改 metadata），即 adapter 写入的值不会被评测器覆盖。

*于是正确的字段映射是*：

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*通道的真实代价*（这三条是本报告新增的限定，反馈方未提及）：

+ *cross 的对位段没有这条通道*。`get_cross_component()` 只放被选中的 crossover partner 的代码与指标；其 `text_feedback` 只能通过 eval history 的列举段出现，不与代码相邻。
+ *该字段属于评测器语义*。它的官方来源是评测脚本返回的 `metrics_val.get("text_feedback")`（`async_runner.py:1633, 1687, 4130, 4171`）。改用它承载机制描述属于语义借用，且单字段意味着"每个程序只有一条文本"——机制摘要与评测反馈只能二选一或由 adapter 自行拼接。
+ *重复评测会生成第二行*。若同一候选再走一遍 Shinka 评测流程，会新建一行携带评测器写入的值（`async_runner.py:4160-4172`），于是同一段代码有两行、字段含义不同。

*后果*：`adapter first, schema later`（计划:543）的*意图*可行，但实现方式必须从"写 metadata"改为"写 `code` + `text_feedback` + `metadata`"，并显式开启 `use_text_feedback`。更实质的一点保留自 Rev. 0：进入 prompt 的主体是"一个被 evaluator 打过分、进入 archive 的竞争者程序"，机制文本只能依附在同一行上。H1 的实验设计必须从这个真实通道重新推导。

*最小修补*：§4.3 改写为上述映射表，并写明 `use_text_feedback = true` 是前提、cross 对位段无此通道、以及"重复评测会生成第二行"的处理约定。

== D10（重要，Rev. 1 新增）开放世界获取前端并不存在，而它是整条链的第一跳

*指控*：计划:58 把"开放世界获取（open-world acquisition）已有相当成熟的实现基础"列为第一条工程认识，并在 §3.2 的架构图（计划:421-425）与 §4.1（计划:456-487）把 Man1Lab 定为 acquisition front-end。*该成熟度对 Man1Lab 不成立*：它当前没有任何"问题 → 候选仓库"的搜索路径。

*证据*（已核实，三个快照口径一致）：

- `src/providers/github/client.py:61` 逐字：`raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`。`get_repository`（:43）与 `get_readme`（:48）已实现，搜索未实现。
- 三个口径为同一状态：反驳方引用的 `5376e58d54eb` *就是当前 main HEAD*（2026-07-14T05:28:38Z，也是该仓库最新提交）；PyPI `man1lab` 1.3.0 的包内同文件同一句，经 CRLF 归一化后与 5376e58 版本逐字节相同；全包 `search_repositories` 只有该 stub 与测试断言，*无任何调用点*。
- `GitHubCollectionProvider` 的输入是论文分析里已存在的 URL：`collection.py:1,46` 自述 "resolve explicit paper GitHub repository URLs"，`collect(analysis)`（:56-58）→ `extract_github_repository_urls(analysis)`（:124-153）只从 `analysis.resources` 中抽取 github.com URL，*无 query 参数*。
- 官方审计文档逐字：`docs/reviews/1.2_github_collection_provider/audit.md:49,55,171,182` — "Only explicit paper GitHub URLs"、"No Search API"、"Search API | Out of scope for Phase 1.2"、"deterministic, Search-free"。
- 全包不存在其它发现路径：`collection_service.py:48-52` 的默认 provider 仅为 Embedded、GitHub、NoOp，Embedded 同样只吃 analysis 内嵌 URL（`embedded_resource_provider.py:1,82`）；由 gap 派生的 `ResourceNeed`（:22-36）只被生成、无 provider 消费；全包无 web search 类 provider，外部 host 仅 `api.github.com` 与 `api.deepseek.com`。
- 规划与实现要分开：ADR-0016:161 把 "conditional search" 列入 Phase 1，而实作面停在 1.2 → 1.3.0 的无搜索状态；`github-discovery-provider.md:420` 才把 "Search tuning" 放 Phase 4。准确说法是*被规划、未实现*，而非"属于后续规划"。

*附带的语义问题：`verified` 被用于指两件不同的事。* Man1Lab 的 GitHub 验证是 `verification.py:1` "deterministic checks on collected evidence only"、`:47` "no network"，其 ADR-0016:142 自陈 "Shallow verification does not guarantee runnable repos — Execution may still fail"。因此必须拆开：

#enum(
  [$V_D$ = *发现层可信*：仓库存在、身份、许可、归档状态等元数据检查。Man1Lab 提供这一级。],
  [$V_E$ = *任务层可执行*：在冻结 evaluator 下真的跑通并产生可比较的指标。只有这一级才能进入进化种群，而它必须由本项目自建。],
)

*后果*：首版最窄切片的第一跳（Discovery）没有实现路径。计划的验收"一个外部 repo 能被发现、冻结、转换、进入 Shinka mutation/cross"（计划:1055）与 Sprint A 第 4 步"从 Man1Lab 输出*或其 schema* 生成 CandidateResource"（计划:1317）都只提供"给定论文 / 给定 URL 的解析与浅验证"，不提供发现。Rev. 0 的 D9 已指出这个缺口，但定级过低——它是整条链的入口。

*同时也更正 Rev. 0 的一处过度解读*：计划字面*没有*写"Man1Lab 搜索 GitHub"，它写的是"开放世界获取已有相当成熟的实现基础"并把它设为 acquisition front-end。指控应限定在这句话与这个定位上。

*最小修补*：把 acquisition 显式拆成 *Search*（使用现成的 GitHub / Web / paper 检索，本项目只做薄封装）+ *Ingest*（借用 Man1Lab 的 schema 与 `V_D` 检查，不引入其 runtime），并在 §9.2 补上 Search 这一步的验收。

== D2（重要，Rev. 0 曾定为致命）H1 的两种读法需要分开，混用会让结论不可归因

*Rev. 1 的调整*：反馈方指出计划的 H1 字面是工程效用假设（计划:1476-1480："能够在相同 evaluator 与预算下，提高算法改进效率"），对该假设而言 `C_open > C_closed` 本身即有效证据，"更多有价值的上下文"本就属于 open-world 干预的一部分。这一点成立，我据此撤回"致命"定级。但需要区分两个 estimand，并接受随之而来的代价：

```text
H_U :  OpenWorld        -> UtilityGain        第一阶段可直接检验
H_M :  MechanismTransfer-> UtilityGain        第二阶段才可识别的因果问题
```

*保留的批评一：计划同时主张了两者，不能只保留对自己有利的那一半。* §1.6 与 §2.2 的措辞是机制性的——"关键不是简单增加 context，而是使外部实现进入可验证的研究循环"（计划:344）、"把外部已验证实现转换为可执行、可追踪、可作为 evolutionary inspiration 的研究对象"（计划:60）。若只主张 $H_U$，这些句子必须改写，否则文档承诺的仍是一个无法从 §8 设计里读出的 $H_M$。

*保留的批评二：降级到 $H_U$ 是要付代价的，代价在新颖度上。* FunSearch 与 OpenEvolve 已经在做"把历史高分实现放进 prompt"（S18、S20）。若只主张 $H_U$，本文与它们的差别仅剩"多了一段外部上下文"，而 §4 所依赖的四元组差异（外部获取 × 独立验证 × provenance × 进化灵感）恰好立在 $H_M$ 那一侧。*把 claim 缩到能测的范围，等于把贡献也缩到那一侧。* 这不是反对降级，而是要求作者显式选择。

*保留的批评三：即使只做 $H_U$，§8.2 的负对照仍然太弱。* §8.1 的"严格保持相同"清单（计划:936-946）不含上下文长度；唯一负对照"shuffled/unrelated inspiration"（计划:981）未规定长度与领域匹配。对 $H_U$ 而言这不致命，但它使"open 有效"无法排除"上下文变长即可"这一平凡解释——而随机标签的 demonstration 依然有效这一已知现象（S29）说明该解释不能被想当然地排除。

*最小修补*（两种走法，作者择一）：

#enum(
  [*走 $H_U$*：把 §8.2 的第二层判据降级为"open 是否值得"的工程决策，删除 §1.6/§2.2 的机制迁移措辞，并在相关工作一节承认与 FunSearch / OpenEvolve 的差距只剩 provenance 与 verification 两项。],
  [*走 $H_M$*：保留 Rev. 0 的六臂设计——单任务、固定 seed、冻结 evaluator，各臂灵感槽位 token 数匹配（±5%）：C0 纯内部 archive；C1 机制+代码；C2 同长度同语言随机代码；C3 仅机制描述；C4 仅代码；C5 人工预选最佳匹配作 oracle 上界。判据：C1 显著优于 C2，且 adaptation diff 显示外部机制确实进入子程序。],
)

== D3（重要）统计门名实不符，且功效结构性不足

*指控*：§6.2 自称 "SGM-style commit gate"（计划:783），但缺少使其成为统计门的那个机制；同时 §5.1 与 §6.2 的组合使 confirmation 阶段不提供新信息；整个设计在统计上没有能力检测中等效应。

*证据*：

- *功效*（已核实，非中心 $t$ 分布 + $10^5$ 次蒙特卡洛双重复算一致；检验与计划:763-764 的按 seed 配对一致；约定为*严格双侧* $alpha=0.05$，默认非严格双侧会略低）：

#table(
  columns: (auto, auto, auto, auto, auto, auto),
  inset: 4pt,
  stroke: 0.4pt,
  [*n*], [*d=0.5*], [*d=0.75*], [*d=1.0*], [*d=1.5*], [*d=2.0*],
  [5], [0.141], [0.254], [0.401], [0.711], [0.909],
  [10], [0.293], [0.562], [0.803], [0.987], [1.000],
  [20], [0.565], [0.889], [0.989], [1.000], [1.000],
)

- *样本量必须由公式给出，而不是拍一个数*（Rev. 1 更正；Rev. 0 在此处写的 $n>=20$ 无依据，且与上表自相矛盾——$n=20$、$d=0.5$ 时 power 仅 0.565）。正确形式是：

```text
n_confirm = f(MDE, sigma_d, alpha, beta)
近似闭式:  n ≈ (z_{1-alpha/2} + z_{1-beta})^2 · sigma_d^2 / MDE^2
精确解:     非中心 t，ncp = MDE·sqrt(n)/sigma_d，df = n-1，对 n 数值求根
            （闭式会低估: d_z=0.5、power=0.8 时给 31.4，精确值 34）
```

  采用的分辨标准应由领域预先指定 MDE，再由 pilot 估 $sigma_d$（配对差的标准差，不是跨 seed 的池化标准差），必要时取其置信上界以保守。
- *$n=5$ 真正意味着什么*：在该设计下（power 0.8、$alpha=0.05$）最小可检测效应为 *$1.68 sigma_d$*。这比"样本量偏小"更能说明问题——只有巨大的效应才可能被检出。
- *用 pilot 效应量定样本量是已知陷阱*：效应量的条件估计在低功效下被系统性高估（winner's curse / ascertainment bias，亦称 Type M 误差），据其定样本量几乎必然导致确认阶段功效不足（S42、S44）；pilot 的用途是估 $sigma$，不是估效应量（S43）。$sigma$ 的估计不经"是否通过阈值"的条件化，误差只经 $sigma^2$ 线性传入 $n$，取上置信限即可保守——两者的统计性质不同，不可类比。
- *非参数门恒零*：$n=5$ 时 Wilcoxon 精确符号秩检验双侧最小 $p = 0.0625 > 0.05$，即在该设计下非参数检验的 commit 概率恒为 0（独立复核结论）。
- *多重比较*：§8.1 并列 8 个"主要指标"（计划:951-962）而无单一主终点；若对 §14.2 的三个条件做 Bonferroni（$alpha/3$），$n=5$、$d=1$ 的功效降至 0.191；$d=1$ 需 $n=14$，$d=0.5$ 需 $n=45$。
- *confirmation 不独立*：§6.2 的流程是 cheap pilot → 过阈值 → "confirmation 使用冻结 seed set"（计划:801-803），而全文唯一的 seed 集是计划:603 的五个 seed，文档从未定义 pilot 的数据来源或独立确认集。*若二者共用，则 winner's curse 未消除*（条件式，因为文档字面并未写共用）。
- *不相交 seed 是必要条件、不是充分条件*：还需要（a）$n$ 按预注册 MDE 定，不得用 pilot 的效应量；（b）pilot 数据排除在最终统计之外；（c）campaign 级 FWER 控制与序贯停止的 alpha spending（S45）；（d）预注册与分析冻结，防终点/假设事后切换（S46）；（e）seed 集不得事后挑选（挑低方差的 seed 会再次引入条件化）。
- *α 与 lifetime 控制冲突*：§6.1 固定 per-test $alpha = 0.05$（计划:776），§6.2 自陈要解决长期 campaign 的 multiple testing（计划:785）——两者在数学上不相容。
- *SGM 名实*：SGM 的实际机制是 statistical improvement certificate + 轨迹级风险分配 + predictable summable error budget（$alpha_k = delta / (k (k+1))$ 一类），把"永不接受非改进更新"的概率界在 $delta$（S11）。计划把 e-value / error spending 推到"后续再引入"（计划:806）。*此处保留 Rev. 0 自我修正后的措辞*：不能说是 SGM"唯一"的提供物——它还包括 certificate → 状态转移协议、checkpoint 与 held-out 审计；准确的说法是，被推迟的那一项正是"统计门"这个名称的实质内容。
- *右删失*：`time to first improvement`（计划:954）作为主指标，预算内未改进应记为删失，但文档既无删失规则也无生存分析，却规定用均值与置信区间汇总（计划:770）。

*后果*：两面失效——既会因为功效不足而漏掉真实的中等效应，又会因为缺少 lifetime 误差预算而在长期运行中累积假接受。前者被 §9.3/§14.4 直接翻译成"停止扩展"。

*最小修补*：Task Contract 增加 `statistics.mde`、`statistics.power`、`statistics.sigma_source` 三项并预注册，$n$ 由上式求解；confirmation 使用与 pilot *不相交* 且未被事后挑选的 seed；给出 campaign 级 lifetime $alpha$ 预算与 alpha spending；把 8 个并列指标收敛为 1 个主终点 + 次要指标；时间类指标改 Kaplan–Meier / log-rank 并预注册 target。

== D4（重要，Rev. 0 曾定为致命）护栏不可执行：治理缺陷已确认，漂移推断撤回

*Rev. 1 的调整*：保留"§12.1 不可执行"；撤回"proxy drift 已经发生"这一推断。理由：新证据导致更换技术栈本身可能正是*避免*目标固化的行为，把它直接认定为漂移是越界推断。

*指控（保留部分）*：§12.1（计划:1232-1242）是这份计划防止自身目标漂移的核心机制，但它的两条关键定义——"milestone"与"Δ research capability"——全文从未定义；计划不含任何工期、人力、算力预算与负责人；且同目录缺少规范的决策沿革。

*证据*：

- "milestone" 在全文仅出现一次（计划:1242），§9 用的是 Phase + 验收；"Δ research capability" 无任何度量定义。
- 按字面执行会自我触发：Phase 0 的交付是 `GOAL.md`、schema、evaluator hash、baseline（计划:1014-1022），Phase 1 的验收是"一个外部 repo 可被追溯"（计划:1055）——两者按设计都不产生算法能力增长，因此"连续两个里程碑无增长则冻结基础设施"会在 adapter 建成*之前*生效。
- 两套停止规则并存且不同：§12.1 的冻结条件与 §14.4 的 Go 条件（计划:1375-1386）互不引用。
- 没有任何阶段的验收要求"产出 verified improvement"；§8.3 反而把首版主验收定为"基础设施能否减少真实研究成本"（计划:1006）。
- 全文唯一出现的日期是版本号（计划:30）；Sprint A–D（计划:1308-1386）无时长、无 owner、无预算。
- *同目录事实*（已逐项核验）：共 10 份 `.typ`，排除本报告为 9 份。`algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml *19 行中 18 行逐字相同*（计划:589-610 对 ARI:148-167），唯一差异是 `secondary` 的写法；seed 列表双方完全一致（计划:603 = ARI:162 = `[11, 23, 47, 89, 131]`）。两份的 Experiment Record 则*同源而异*：被审计划新增 `external_inspiration_ids`、`code_diff`、`logs`、`compute_cost`、`validity`、`statistical_decision`，命名亦不同（`started_at`/`ended_at` 对 `start_time`/`end_time`）。两份文件 mtime 同为 2026-09-18 14:32（被审计划为 15:25），*均无任何取代/被取代声明*（grep `supersede|取代|废弃|作废|替代|以本文为准` 只命中一处无关语义）。
- *`adapdc` 世代的可观测迹象*：新版 `adapdc_scaffold_implementation(1).typ`（09-09 20:37）确已声明*部分条款*取代（ADR-001 的文档效力表，`:25-31`），但它是部分取代而非整篇废弃（`:72` 明写"不整篇废弃旧文档"，`:33` 限定"本 ADR 只裁决上述主题"）；`:35` 要求旧版顶部标注"部分条款已取代"，那是待执行的"C0 本地落库动作"——旧版 `adapdc_scaffold_implementation.typ`（09-09 20:13）*未加标注*，其 `:32` 仍主张"不能同时保留相反的现行决策"，`:408` 仍写"不能让两份'现行真相'并存"。Makefile 用通配符把两者都编成 PDF（`SRC := $(wildcard *.typ)`，:17），`pdf/` 中两份并存。另有第三套并存的统计提交门（ADA、OPL、本计划）。
- *漂移推断为何撤回*：以上证据支持的是"缺少 canonical decision lineage"，不直接支持"时间被用于完善基础设施而非算法改进"。后者在 Rev. 0 中被我用 adapdc 世代的自承（无真实数据、验收项为生成元扩展测试）作为旁证，但那批文档在 09-09，距被审计划已 9 天，且计划本身正是纠偏产物。

*后果*：这是我认为*概率最高、后果最重*的失败方式，但正确的定性是*治理缺陷*而非已发生的事实。§13 的决策五问（计划:1290-1298）审的是组件，不审文档，所以它拦不住文档层面的漂移。

*最小修补*：§9 每个 Phase 前补一行可测里程碑（指标 = best verified score 相对 baseline 的 $Delta$；目标值；时限；负责人），并据此重写 §12.1；新增一节"与既有计划的关系"，逐条写明 ARI 计划被取代的部分与 schema 的真源、adapdc 旧版标注取代、evaluator 与 Experiment Record 的唯一真源仓库；并给决策加上 `Decision_t → supersedes/retains → Decision_(t-1)` 的显式字段。

== D5（重要）H2 没有对应的实验臂，且其问题已被先行工作占位

*指控*：H2（计划:1482-1496）声称存在比固定策略更高效的自适应策略，但 §8 与 §14 的条件只有 Closed / Open / Open-Unrelated（计划:1046、1348），全文没有任何"自适应策略 vs 固定策略"的对照。H2 用本计划自身的设计无法证伪。

*证据*：条件枚举见计划:1046 与 1348；H2 的表述见 1482-1496；§7.2 把 bandit 推到"真实轨迹足够后"（计划:883-899），§9.6 把 policy learning 推到 Phase 5。而 Dream-RSI（S7，arXiv:2609.14858）的问题设定与 H2 近乎同名：其摘要即称"管理与改进探索策略是瓶颈"，机制是把已完成轨迹当 replay simulator 离线优化探索策略。ASI-Evolve 亦已内置 UCB1/greedy/island sampler（S6）。

*后果*：H1 成立后若要检验 H2，需要另行设计；而在论文语境下，H2 的位置已有人站住，差异化必须收窄。

*最小修补*（采纳反馈方更锐利的表述）：H2 在首版降级为"轨迹收集目标"，明确写"本阶段不检验 H2"；未来真正有区分度的问题不是泛泛的"自适应探索"，而是*外部获取与内部进化的联合分配*：

```text
动作空间:  { SearchWorld, Acquire, Adapt, Cross, Mutate, Evaluate }
问题:      在固定预算下，如何在这六类动作间分配？
```

== D6（重要）未纳入的一等风险

计划 §11 只讲权限与安全、§12 只列四类失败模式。以下五条我判断应升为一等风险：

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（见 D10，该假定不成立），并把 `understand` 写成管道的一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 的验收只要一段 summary（计划:1050）；J 的分母（计划:318）与 §12 都没有"仓库能跑但机制抽不出"的成本与失败模式。外部基线表明这一步极难：PaperBench 上最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛中达到铜牌水平（S24）。*我的判断*：H1 若失败，最可能死在"获取 + 理解"这两步，而 §9.3 会把它误判为"开放世界收益低"并终止路线——真实原因根本没被测量。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"agent 上网找到他人已解出的高分方案"；而 §8.3 偏偏优先选择"存在可搜索公开实现"的任务（计划:994）、第二层又用公开 benchmark（计划:1002）。MLE-bench 因此必须明文禁止 agent 查看网上解法（"通常在 Kaggle 或 GitHub 上能找到"），并用 Dolos 与 top-50 公开 notebook 比对判抄袭（S24）。计划:981 的 unrelated-inspiration 对照抓不到"抄对了答案"。
+ *许可证合规未管理*（Rev. 1 按 AGPL §2 重写，撤回"许可传染"的说法）：`license` 仅为记录字段，出现在计划:533、626、1046 三处，§11 与 §12 都没有许可决策规则。准确的表述是：*若*生成产物在事实上复制或改编了 AGPL 代码（逐字片段或实质性相似），它*可能*构成 AGPL §0 下"基于该 Program 的作品"，从而须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下向远程交互者提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束，故不能因模型见过 AGPL 仓库就推定输出自动 AGPL（S31）。工程上应做的是 *License Provenance Gate*：来源与依赖清单（URL + commit + hash + 许可证）、指纹与相似度比对（Copilot 的比对窗口约 150 字符量级，且官方承认"在空白或近乎空白文件中命中要频繁得多"、命中建议少于 1%，S32）、许可证分类白/黑名单与义务登记、命中后的派生隔离与替换重写。这类闸门能覆盖可检测的复制与近似复制；不能覆盖"是否构成 derivative work"这一事实与法律判断。*关键在于计划对此没有任何检测，而它的终局产物是派生的算法代码。*
+ *供应链*：计划:1217-1219 只要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档的原话是默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*`，并经加密 DNS 外传（S34）。*计划:1219 的 secrets 规则防产出、不防安装期*。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问，其中 2013 年样本 38%（S33）。计划:1055 的"可追溯回原 commit"这一验收会随时间衰减。

*最小修补*：把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 三类单列为计数指标并纳入 §12；给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离；给安装期网络与凭据策略；给外部资源快照归档。

== D7（次要但影响可复核性）引用卫生

*指控*：计划声称"进行了系统调查"（计划:214）并列有"关键参考实现与资料"附录（计划:1511），但从文档本身无法复核。

*证据*（已核实）：正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条（Man1Lab、AgentCo-Op、ShinkaEvolve、ASI-Evolve、Dream-RSI、Kimi）；正文点名的外部系统共 17 个，其中 12 个没有任何条目。尤其：FunSearch 全文 0 次出现，MLE-bench、RE-Bench 亦 0 次——而 FunSearch 早已确立"冻结 evaluator + 程序库 + 检索历史高分实现进 prompt"这一范式（S18），正是 H1 的直接前身。

*后果*：审稿人会读出"OpenEvolve + Man1Lab + Dream-RSI 的拼装"，因为文档没有说明每一部分别人做到了哪里。

*最小修补*：补 12 条引用 + 一节"相关工作与差异"，逐条写"谁已做到哪一步、本文只往前推哪一步"。

== D8（次要）引文与命名漂移

以下为已核实的具体偏差，均不涉及虚构，但会误导读者：

#table(
  columns: (2.5cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*位置*], [*问题*],
  [计划:55、370], [`AHE / HarnessFix` 用斜杠并列，暗示为同一方法的别名；实为两个独立工作（S15 与 S16），且计划:1140-1141 本身把它们分作"harness 演化闭环"与"轨迹诊断修复"两个功能。],
  [计划:575], [`ReplayWorld` 非原文术语，Dream-RSI 原文用的是 replay simulator（S7）；且原式中 $H_t$ 是历史本身而非与 replay 并列的节点。],
  [计划:275], [字段名实为 `correct` 而非 "correctness"（S3）。],
  [计划:214], [正式题名为 "Huxley-Gödel Machine"（带连字符），S9。],
  [计划:55、1415-1416], [`SGM/RQGM` 并为一组，但按计划自己的六坐标模型，SGM 属 Commit 层、RQGM 属 Evaluator challenge 层。],
  [计划:1142、1414], [MGM 的核心机制是 comparative evolution / 跨谱系杂交（S10），"archive selection/mutation"的归类丢掉了要点。],
  [计划:214], [MGM、RQGM、SE-GoS、MetaRSI、Dream-RSI 均为 2026 年 6–9 月的 preprint，却与 AlphaEvolve、DGM 并列成"系统调查"的既定文献；仅 Dream-RSI 标注了成熟度。],
  [—], [`github.com/codelion/openevolve` 已改名并跳转至 `algorithmicsuperintelligence/openevolve`（S20），若引用旧地址需更新。],
)

== D9（次要）内部张力

+ *时间尺度与 Phase 顺序不一致*：$tau_K <= tau_pi$ 要求先经验后策略（计划:236-239），但 §9 把 Bridge Policy 放在 Phase 3/5、Skill RSI 放在 Phase 6（计划:1078、1112-1125），K 晚于 $pi$。
+ *与 MetaRSI 的路线冲突未解释*：MetaRSI 已核实为"单一循环内核 + 联合调度"——其摘要写明 data/harness/model 三类算子 "Sharing one loop kernel and artifact vocabulary"，并由 two-axis optimizer 联合决定算子顺序与提案策略（S14）。这与计划:231-239 的固定偏序、以及"evaluator anchor 原则上冻结"直接冲突，文档未说明为何拒绝这种联合调度。
+ *发现步骤的归属与验收缺失*：见 D10。§4.1 给三个未承诺选项（计划:484-486），§9.2 禁止新建搜索引擎（计划:1053），§14.1 第 4 步又允许"从 Man1Lab 输出*或其 schema*"（计划:1317）——三者合起来使"发现"这一步既无实现也无 owner。
+ *Man1Lab 的接口性质被低估*：其 Decision Foundation 官方声明为非公开 API，且仓库侧 roadmap 仍把 Repository Adaptation 列为未完成的 v1.4 项（S1，S39）。*与此并不矛盾的是*：六阶段与五个规则确实存在于源码。文档化的阶段与已交付的能力是两件事——这正是 D10 的方法论要点。

= 三、我的证据

本节是所有指控的可复核基础。原则：能给出源码位置、行号、编号或实测数字的，一律给出。

== 3.1 外部系统源码级核实（计划 §1.6、§2.3、§4、§9.7、§15 的具体断言）

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。Collection → Evidence → Verification → Ranking → Selection 见其架构文档；Strategy / Binding / Reuse / Adaptation / Generation / Risk 六阶段见执行规划文档；五个规则名 `RULE_REUSE`、`RULE_OFFICIAL_USABLE`、`RULE_COMMUNITY`、`RULE_HYBRID`、`RULE_GREENFIELD` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI 包 `man1lab` 1.3.0（2026-07-14），无论文。*但两项能力断言不成立*：（1）无"问题 → 候选仓库"搜索路径（D10）；（2）其 `verified` 仅为发现层检查（`V_D`），非任务层可执行（`V_E`）。另有：计划未锚定版本；规则逻辑属非公开 API。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive、多 provider 均为真。Apache-2.0，arXiv:2509.19349（ICLR 2026），PyPI `shinka-evolve` 0.0.7。*但 `metadata` 不是灵感通道*（D1）；正确通道为 `code` + `text_feedback`。],
  [AgentCo-Op], [*类型名与检索机制描述逐条属实*：`TaskProfile`、`NodeSpec`、`EdgeSpec`、`GatePolicy`、`EvalContract`、`MemoryPlan` 均在 `core/schema.py`，且 `NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约（`runtime.py:118-122`、`core/gates.py`、`compiler.py:206-224`）。检索确为 "keyword + tag scoring"。arXiv:2605.20425。*过强的一处*：`sandbox_repo` 是已接线到 runtime 的 backend，但其自述为 "command builder only"、`execute_live` 分支返回 "sandbox_repo live execution is not wired in framework phase"，即*只产出 docker 命令规格（dry-run），不执行*；真实容器执行只存在于 `--docker` 旁路与 `SandboxBuilder`，且随包 adapter 多为 stub（"framework stub: real GEARS not invoked"，外部 commit 为 `TODO_PIN`），*无已跑通的真外部仓库实例*。*治理风险*：根目录无 LICENSE 文件（仅 `pyproject.toml` 声明 Apache-2.0）；PyPI 包归属两次独立核实结论不一致，安装路径应视为不确定。*遗漏*：其 Case Study 3（把检索到的 workflow 作结构先验再局部修复）是 H1 最直接的经验先例，计划未引用。],
  [ASI-Evolve], [*sampler 断言为真*：`database/algorithms/` 下 random / greedy / ucb1 / island + factory，`BaseSampler.sample(nodes, n)` 对应计划:553 的抽象。Apache-2.0，arXiv:2603.29640，无 PyPI。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline，作为 policy 实验台需先剥离 pipeline。],
  [Dream-RSI], [*论文真实*（arXiv:2609.14858，2026-09-14）；*代码尚未发布*（仓库仅有 README 与 release plan），故计划:368 的"完整源码尚非稳定依赖"不仅正确、且偏保守。许可无法确认（无 LICENSE 文件）。*命名偏差*见 D8。],
)

关于引用的研究谱系（计划:214、§9.7、§15 引用的 RSI 与 harness 工作），10 项*全部真实存在*，编号如下（均为已核实）：

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

见 D3 的表与条目。方法：非中心 $t$ 分布（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$）计算，另以 $10^5$ 次蒙特卡洛独立验证，两者一致到小数点后三位。补充分位数检索给出达到 power 0.8 所需样本量与 $n=5$ 时的最小可检测效应（$1.68 sigma_d$）。Bonferroni 与 Wilcoxon 结论为独立复核者给出。

== 3.3 文档族物证（针对 D4）

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版顶部标注；该标注属待执行的"C0 本地落库动作"，旧版 `adapdc_scaffold_implementation.typ`（09-09 20:13）未加标注，其 `:32` 仍主张"不能同时保留相反的现行决策"、`:408` 仍写"不能让两份'现行真相'并存"；Makefile 通配符把两者都编成 PDF。
- `algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml 19 行中 18 行逐字相同（含 seed 列表），Experiment Record 同源而异；两份 mtime 同为 09-18 14:32（被审计划 15:25）；互不引用，均无取代声明。
- 至少三套并存的统计提交门（ADA、OPL、本计划）。
- 该族另有引用不存在文件的情况（如 `adapdc_architecture_report.typ`、`research-foundations.md`）。

== 3.4 排版与构建实测

构建：`typst 0.15.1` 下 `typst compile` 退出码 0、无 warning，输出 20 页 A4。A4 页宽 595.276pt，页边距 68.031pt，正文右边界 527.245pt，文本列宽 459.21pt。测量方法：`pdftotext -bbox` 逐词取框 + 解压 PDF content stream 读取每个 text run 的笔位，两法交叉一致。

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

结论：6 处显示公式溢出页边距，其中仅 *1 处*（计划:951-962 的 `Y` 指标元组）真正越出纸张被裁切——PDF 第 13 页该行只抽到 "external con" 即断。其余五条虽越边距但仍在页面内。

*为什么值得单独列出*：这份文档的核心主张就是一组测量指标，而它的主指标清单在纸面上被裁掉了最后两项。

= 四、与先前工作的关系

*我的判断*：H1 与 H2 都已被现有系统分别占位，计划的新颖度必须收窄到一句可辩护的话。

*已存在的部分*：

+ *冻结 evaluator + 程序库 + 检索高分实现进 prompt*：FunSearch 已确立（S18）。
+ *MAP-Elites + LLM 的开放进化，且 prompt 中已有 inspiration 机制*：OpenEvolve 自述其核心创新即在此，并带有 `num_top_programs` / `num_diverse_programs`（S20）。
+ *把外部文献与先验注入认知库*：ASI-Evolve 明确支持"upfront 注入领域知识、论文或启发式"（S6）。
+ *论文内显式 URL → 官方实现解析 → 执行规划*：Man1Lab 已实现（S1）。*Rev. 1 更正*：这不是"论文 → 官方实现发现"——它只解析论文里已写出的 URL，且不含搜索（S39）。
+ *自适应搜索策略优于固定策略*：Dream-RSI 的问题设定与 H2 近乎同名（S7）；ASI-Evolve 已内置 UCB1/greedy/island 采样器（S6）。
+ *外部 workflow 作为结构先验*：AgentCo-Op Case Study 3（S5）。
+ *开放世界与开放式进化的理论框架*：open-endedness 议程（S26）、OMNI-EPIC（S27）、POET（S28）——计划全文未引用其中任何一项，这条脉络在文档中完全缺席。

*尚未被占位的部分*（我认为这是计划真正可以主张的差异）：*外部已验证实现 × 反事实贡献度量 × commit / license / hash 级 provenance 的四元组*。即：不只是"把外部实现放进 prompt"，而是能回答"这一条外部灵感贡献了多少"，并能追溯到具体 commit、许可与内容哈希。FunSearch 与 OpenEvolve 有前者、无后者；Man1Lab 有 provenance，但其定位是复现而非改进，且只覆盖论文内已给出的资源。*注意*：这个四元组的价值主要立在 $H_M$ 一侧（见 D2），若把 claim 缩到 $H_U$，差异会大幅缩小。

= 五、建议与判据

== 5.1 结论

*有条件推进（Conditional Go）*。路线与目标层判断成立；工程风险低于 Rev. 0 的判断（注入通道存在、不需要改 ShinkaEvolve 核心），前提风险高于 Rev. 0 的判断（第一跳没有实现，两处"已验证"语义被混用）。建议先做五项必改，再按 Sprint A 的窄切片推进；在必改落地前，不建议开始 Phase 2 的 A/B。

== 5.2 五项必改

#enum(
  [*改写 §4.3 为真实通道*（D1）：`ExternalCode → Program.code`、`MechanismSummary → Program.text_feedback`（需 `use_text_feedback = true`）、`Provenance → Program.metadata`；写明 cross 对位段无此通道、字段属评测器语义、重复评测会产生第二行。],
  [*补上获取这一步并拆开两级验证*（D10）：acquisition = Search（现成 GitHub/Web/paper 检索的薄封装）+ Ingest（借 Man1Lab schema 与 `V_D`，不引其 runtime）；明确 `V_D ≠ V_E`，只有 `V_E` 通过者进入进化种群。],
  [*按作者选择重写 §8.1–8.2*（D2）：走 $H_U$ 就删掉机制迁移措辞并承认新颖度收窄；走 $H_M$ 就用六臂设计（token 匹配 ±5% 的负对照 + oracle 上界 + 机制/代码解离）。],
  [*修统计*（D3）：Task Contract 增 `mde`／`power`／`sigma_source` 并预注册，$n$ 由公式求解；confirmation 用与 pilot 不相交且未事后挑选的 seed，pilot 数据排除在最终统计外；给出 campaign 级 lifetime $alpha$ 预算。],
  [*修护栏与文档收敛*（D4）：可测里程碑表（指标 / 目标值 / 时限 / 负责人）+ 重写 §12.1；新增"与既有计划的关系"一节，指明 ARI 被取代的部分与 schema 真源、adapdc 旧版标注取代、evaluator 与 Experiment Record 的唯一真源；给决策加 `supersedes/retains` 字段。],
)

== 5.3 建议改

+ 把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12（D6）。
+ 给 evaluator 的来源黑名单与抄袭比对（D6）。
+ 加 License Provenance Gate 与 copyleft 派生代码隔离（D6）。
+ 补 12 条引用 + 一节相关工作，并把 5 个 2026 年 6–9 月的 preprint 标注成熟度（D7、D8）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行（实测可将最宽者从 ≈701.5pt 降到边距内）。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.4 建议采用的最窄系统（采纳反馈方的收缩，并补一处）

Rev. 1 认为最窄可执行系统应收缩为：

```text
ExternalSearch -> DiscoveryRecord -> Acquire/Adapt -> FrozenEvaluator
   -> ShinkaProgram(code + text_feedback + metadata) -> ShinkaEvolution
```

其中 `ExternalSearch` 用现成的 GitHub / Web / paper 检索；`DiscoveryRecord` 首版可为本项目自建的薄记录（借 Man1Lab 的 schema，不依赖其 Decision Foundation）；AgentCo-Op 只借设计（typed manifest、安全边界、`GateDescriptor` 式的 gate 语义），*不引 runtime*——因为它的 repo 执行路径是 dry-run（D 条目见 §3.1）。真正的 runtime 核心是：*ShinkaEvolve + 本项目 evaluator + 薄获取适配层*。

*本报告对此设计补一处*：把外部资源建模为状态机是好的，但每一跳都必须带代价与终止条件，否则它会变成"持续投入的理由"：

```text
R0 Retrieved -> R1 DiscoveryVerified(V_D) -> R2 FrozenArtifact
   -> R3 TaskCompatibleProgram -> R4 EvaluatorVerified(V_E) -> R5 EvolutionEligible
```

建议对 R1→R2 与 R2→R3 两跳显式记账（clone、依赖安装、适配人力/算力），并按计划 §12.3 的 integration tax 设拒绝阈值；只有 *R5* 才配称 `ExternalInspiration`。

== 5.5 Go / No-Go 判据（建议直接写入 §14.4）

*继续*的前提是四件事同时具备：一个预注册的单一主终点与 MDE；一个与 Open 条件 token 数匹配的负对照；一个使用不相交、未事后挑选 seed 的 confirmation 阶段；外部搜索/验证/适配的开销全部计入 open 臂的预算口径。

在满足上述前提后，若 C1 不显著优于 token-matched 对照，则判 *$H_M$ 不成立*（$H_U$ 另论）——但此时必须同时报告*搜索失败率*与*机制抽取失败率*，以区分三种完全不同的结论："没找到候选"、"没读懂仓库"、"机制不可迁移"。计划现有的判据（计划:1076）无法做这个区分，这是我认为最需要修补的单点。

== 5.6 什么会使我改变判断

以下任一项成立，我会相应撤回对应指控：

+ 若作者能指出一条本报告与反馈方都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1 的第一部分（但字段映射的更正仍成立）。
+ 若作者给出文档外的定义，说明 pilot 与 confirmation 使用不相交且未事后挑选的 seed → D3 的该条降为部分成立。
+ 若作者给出已被别的文档定义的 milestone 与 $Delta$ 度量 → D4 的"不可执行"部分撤回（文档并存仍需处理）。
+ 若作者给出 $n$ 与最小可检测效应的预注册值 → D3 的功效部分降级。
+ 若 Man1Lab 或其它组件在后续版本实现了"问题 → 候选仓库"的搜索 → D10 撤回（需附具体版本与调用点）。

= 六、我撤回或修正的判断

正式审查应当同样记录自己判断中未通过复核的部分。以下十项按 Rev. 0 与 Rev. 1 两轮列出。

*Rev. 0 内部已修正（第一轮反证）*

#enum(
  [*公式越界范围*：曾称"6 处数学块越界，`Y` 公式宽 600.5pt"。实测修正：越出*页面*被裁切的只有 1 处（计划:951-962，宽度 ≈701.5pt，区间 −53.13 至 ≈648.4pt，两侧各裁约 53pt）；其余 5 处仅溢出页边距。],
  [*灵感槽位数*：曾称 slot 数为 archive 4 / top-k 2。修正：论文与 `island_small`、`island_large` preset 为 4/2，而 `island_medium` 与类默认（`dbase.py:63-64`）为 1/1。],
  [*SGM 的"唯一提供物"*：修正为"被推迟的那一项正是使统计门名实相符的机制"，SGM 另含 certificate → 状态转移协议与 checkpoint / held-out 审计。],
)

*Rev. 1 新增修正（第二轮核验反馈）*

#enum(
  [*D1 的补救措施*：曾称注入机制文本"必须自定义 `PromptSampler`"。修正：`Program.text_feedback` 已是现成的 per-inspiration 通道（`prompts_base.py:74-79`），不必改核心；残留限定见 D1。],
  [*D1 的 archive 不变量*：曾称灵感"必须 `correct=1` 且已入 archive"。修正：这是*默认路径*（elites / random / top-k / 全局兜底均 `JOIN archive` 且 `correct=1`），但 `best_program_id` 路径只检查 `prog.correct`、无 archive JOIN（`inspirations.py:57-67`），fix 模式的 ancestor 亦沿 parent 链取而无此过滤。工程上仍应主动要求 `V_E` 通过且 `correct=true`。],
  [*AgentCo-Op 的能力*：曾称 `sandbox_repo` 为"真实 backend"。修正：它是真实注册且被 runtime 调用的 backend，但只产出 docker 命令规格（dry-run），不启动隔离环境。],
  [*Experiment Record 的同一性*：曾称与 ARI 计划"逐字相同"。修正：同源而异——Task Contract yaml 18/19 行相同，Experiment Record 字段集与命名均不同。],
  [*ARI 计划的日期*：曾称"（09-17）"。修正：文件 mtime 为 09-18 14:32；09-17 是其文内一处参考资料检索日期。],
  [*样本量建议*：曾建议 $n>=20$。修正：该数字无依据且与本人表格冲突，改为 `"n = f(MDE, sigma_d, alpha, beta)"` 的公式化程序，并给出 $n=5$ 时最小可检测效应 $1.68 sigma_d$ 这一更准确的论证。],
  [*"proxy drift 已经发生"*：修正为"治理缺陷已确认；漂移的可观测迹象在 adapdc 世代，换栈本身不构成漂移证据"。],
  [*"许可传染"*：修正为按 AGPL §2 的条件式表述 + License Provenance Gate。],
  [*引用行号*：`license` 三处应为 533、626、1046（曾误写 527）。],
)

另有一项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属，两次独立核实结论冲突，本报告按"安装路径不确定"处理。

= 附录 A：审查覆盖范围

两轮共 26 个独立审查轴。第一轮（20 轴）：Man1Lab、ShinkaEvolve、AgentCo-Op、ASI-Evolve、Dream-RSI 五个系统的源码级核实；Gödel machine 谱系（DGM / HGM / MGM / SGM / RQGM / SE-GoS / MetaRSI）核实；harness 谱系（AHE / HarnessFix / RobustSGPO）核实；统计与实验设计；内部一致性与可行性；与同目录三份旧计划（ADA / OPL / ARI）的一致性；与 adapdc 系列的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；Typst 构建与排版实测；针对 D1、D3 的两轮专项反证；引用元数据的三轮核实。第二轮（6 轴，对审查反馈的核验）：ShinkaEvolve 的 text_feedback 通道与 inspiration 过滤不变量；Man1Lab 的搜索能力（三快照口径）；AgentCo-Op 的 repo 执行能力；目录层文档治理事实；许可表述精度；样本量程序的统计陷阱。

= 附录 B：来源清单

*核心依赖*

- [S1] Man1Lab — https://github.com/maniac1um/Man1Lab （MIT；`docs/architecture/ARCHITECTURE.md`、`EXECUTION_PLANNING.md`；`providers/embedded/decision_foundation/strategy_decision.py`、`generation_decision.py`）
- [S2] Man1Lab on PyPI — 包名 `man1lab`，v1.3.0（2026-07-14）
- [S3] ShinkaEvolve — https://github.com/SakanaAI/ShinkaEvolve ；Lange, Imajuku, Cetin, *ShinkaEvolve: Towards Open-Ended and Sample-Efficient Program Evolution*, arXiv:2509.19349（ICLR 2026）
- [S4] ShinkaEvolve on PyPI — `shinka-evolve` 0.0.7（2026-06-02）
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

- [S18] FunSearch — Romera-Paredes et al., *Mathematical discoveries from program search with large language models*, Nature 625, 468–475, doi:10.1038/s41586-023-06924-6
- [S19] AlphaEvolve — arXiv:2506.13131
- [S20] OpenEvolve — https://github.com/algorithmicsuperintelligence/openevolve （Apache-2.0；原地址 `codelion/openevolve` 已跳转）
- [S21] The AI Scientist — arXiv:2408.06292
- [S22] AIDE — arXiv:2502.13138
- [S23] PaperBench — arXiv:2504.01848
- [S24] MLE-bench — arXiv:2410.07095
- [S25] RE-Bench — arXiv:2411.15114
- [S26] Open-endedness 议程 — PMLR 235:20597–20616 / arXiv:2406.04268（两版作者序不同，引用须标明版本）
- [S27] OMNI-EPIC — arXiv:2405.15568
- [S28] POET — arXiv:1901.01753
- [S29] Min et al., *Rethinking the Role of Demonstrations* — arXiv:2202.12837（EMNLP 2022）

*风险论据*

- [S30] pip secure installs — https://pip.pypa.io/en/stable/topics/secure-installs/
- [S31] AGPL-3.0 §0、§2、§5(c)、§13 — https://www.gnu.org/licenses/agpl-3.0 （条款文本经 SPDX 镜像逐字核对）
- [S32] GitHub Copilot code referencing（2023）— https://github.blog/news-insights/product-news/introducing-code-referencing-for-github-copilot/
- [S33] Pew Research, *Link Rot and Digital Decay on Government, News and Other Webpages*, 2024-05-17
- [S34] PyTorch, compromised nightly dependency（torchtriton）— https://pytorch.org/blog/compromised-nightly-dependency/

*第二轮新增*

- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `shinka/prompts/prompts_base.py:74-79`；`shinka/core/sampler.py:147-157, 156, 243, 256-263`；`shinka/prompts/prompts_cross.py:57-73`；`shinka/database/dbase.py:174, 849-890`；`shinka/database/inspirations.py:57-67, 69-88, 90-108, 110-127, 143-242`；`shinka/core/config.py:62`
- [S39] Man1Lab 搜索能力（快照 `5376e58d` = 当前 main HEAD；PyPI 1.3.0 同源）— `src/providers/github/client.py:43, 48, 61`；`src/providers/github/collection.py:1, 46, 56-58, 88, 124-153`；`src/providers/github/verification.py:1, 47, 49-53`；`docs/reviews/1.2_github_collection_provider/audit.md:49, 55, 171, 182`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op repo 执行能力（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 3, 28, 62-83, 86-130`；`agentcoop/backends/__init__.py:15`；`agentcoop/core/runtime.py:118-122, 167`；`agentcoop/core/gates.py`；`agentcoop/compiler.py:206-224, 388, 405`；`agentcoop/integrator.py:75-90`；`agentcoop/core/repo_collaboration.py:407-423`；`agentcoop/core/sandbox_build.py:303-331`；`agentcoop/wrappers/gears/adapter.py:47`；`configs/external_commits.yaml`（`TODO_PIN`）；`tests/unit/test_backends.py:39-58`
- [S41] AGPL-3.0 §0 与 §2 原文（`covered work` / `based on` / "output … only if"）— https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-or-later.txt
- [S42] Zöllner & Pritchard, *Overcoming the winner's curse: estimating penetrance parameters from case-control data*, AJHG 80(4):605-615, 2007 — doi:10.1086/512821
- [S43] Leon, Davis & Kraemer, *The role and interpretation of pilot studies in clinical research*, J Psychiatr Res 45(5):626-629, 2011 — PMID 21035130
- [S44] Gelman & Carlin, *Beyond power calculations: assessing Type S and Type M errors*, Perspect Psychol Sci 9(6):641-651, 2014 — doi:10.1177/1745691614551642
- [S45] DeMets & Lan, *Interim analysis: the alpha spending function approach*, Stat Med 13(13-14):1341-1352, 1994 — doi:10.1002/sim.4780131308
- [S46] Nosek et al., *The preregistration revolution*, PNAS 115(11):2600-2606, 2018 — doi:10.1073/pnas.1708274114
- [S47] R `stats::power.t.test`（非中心 $t$ 求根与 `strict` 约定）— https://stat.ethz.ch/R-manual/R-devel/library/stats/html/power.t.test.html ；Cohen, *Statistical Power Analysis*, 1988

*同目录文档*

- [S35] `algorithm_research_infrastructure_plan.typ`
- [S36] `ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
