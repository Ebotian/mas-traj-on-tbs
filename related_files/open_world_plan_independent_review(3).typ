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
  #text(size: 9.5pt)[本报告版本：*Rev. 3*（2026-09-18）· 含三轮外部复审的核验记录]
  #v(2pt)
  #text(size: 9.5pt)[结论：*有条件推进——先做货架优先的能力对决，不先写 adapter；H1 的 A/B 仍在其后*]
  #v(2pt)
  #text(size: 9.5pt)[本报告不含对尚未存在的实验结果的评价]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 3 总评*：第三轮核验后，审查的重心第三次移动。此前的移动是"从组件理解 → 实验单位"；这次是*从实验设计 → 工程顺序*：

  #v(3pt)

  + *KAPSO 应被提升为一级货架候选*（§4.2）。它已公开实现的 API 与编排，覆盖了"开放世界检索 + 知识摄入 + 长程进化 + 预算/续跑/实验记录"，且是 MIT、可 pip 安装、当日仍在提交。按计划自己的工程顺序，*先实测它、再决定是否写自己的 adapter* 是唯一自洽的做法。
  + *但它的能力有三处被高估，缺口恰好落在我们要求的那一项上*：`Source.Repo` 只有 `(url, branch)`，摄取与 seed 两条克隆路径都不固定 commit，无 license 字段，无可执行性验证；而 `iteration_evaluator` 在源码与文档里都被明确定为*不参与搜索选择*。所谓"KAPSO 已经很接近目标"要限定为"除外部工件边界之外已经很接近"。
  + *新增 D12*：`(Open, Closed)` 用同一 seed 不构成配对实验——干预会改变控制流，状态式 PRNG 的随机流随即失同步。正确条件是 event-keyed 随机源。
  + *§4 的新颖度判断再修正一次*："运行时闭环已被占据"太粗；应分成三个层次：检索一次后进化、检索与进化交替、把检索/适配/交叉/内部进化当作一个策略来分配。前两层已占位，第三层是*部分占位*。

  #v(3pt)

  因此下一步不是写 adapter，也不是立刻上 A/B，而是 *Shelf-first capability shootout*：用同一个真实算法任务与同一个冻结 evaluator，先让 KAPSO 原生跑一次（P1），再加最小 provenance/验证补丁跑一次（P2），并用 Loreley 做独立对照（P3）；只有当它们明确不满足时才进入 P4（自建薄 adapter）。
]

= 零、审查方式与限度

== 0.1 方法

本报告由四轮构成。Rev. 0 为全文精读 + 20 个并行独立审查轴（源码级事实核实、专项反证、统计复核、构建与排版实测）。Rev. 1 为对第一轮复审意见的独立核验（+6 轴）。Rev. 2 为对第二轮复审意见的独立核验（+6 轴）。Rev. 3 为对第三轮复审意见的独立核验（+5 轴：KAPSO 的公开 API 面与闭环、KAPSO 的 provenance 与工件边界、common random numbers 与 event-keyed randomness、货架候选横向普选、决策策略层是否已被占位）。

四轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。每轮都产生了对本报告自身判断的更正（见 §6）。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行，不存在可评价的数据。
- 外部系统的核实基于 2026-09-18 的公开快照（KAPSO 为 HEAD `7d99b15` / release 0.4.7）；被审计划本身未固定版本，故任何断言都可能随上游更新失效。
- §4 的最近邻检索以 arXiv 为主要口径，未覆盖非 arXiv 正文与 GitHub 代码搜索。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S75）见附录 B。第三方源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → 1 → 2 → 3）

*Rev. 1 阶段（对第一轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R1　D1 补救措施], [注入机制文本"必须自定义 `PromptSampler`"], [*不成立*。存在现成的 per-inspiration 文本通道], [已改为 code / text_feedback / metadata 映射],
  [R2　D2 定级], ["致命"（无法归因）], [*部分成立*。H1 字面是工程效用假设，对该假设封闭 vs 开放有效], [降为"重要"，区分 H_U 与 H_M],
  [R3　获取前端], [未指出], [*成立且重要*。Man1Lab 无"问题 → 候选仓库"路径], [新增 D10],
  [R4　AgentCo-Op 能力], [`sandbox_repo` 为"真实 backend"], [*过强*。只产出 dry-run 命令规格], [已改写],
  [R5　Experiment Record], ["与 ARI 逐字相同"], [*错*。同源但字段集不同], [已更正],
  [R6　ARI 计划日期], ["（09-17）"], [*错*。mtime 为 09-18 14:32], [已更正],
  [R7　样本量], ["$n>=20$"], [*无依据且与自身表格冲突*], [已改为公式化程序],
  [R8　proxy drift], ["已经发生"（事实层）], [*证据不足*], [收窄为"治理缺陷已确认"],
  [R9　许可风险], ["许可传染"], [*过强*。漏掉 AGPL §2 条件句], [已按 §2 重写],
  [R10　行号], [`license` 在"计划:527"], [*错*。应为 533、626、1046], [已更正],
)

*Rev. 2 阶段（对第二轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R11　cross 与反馈的相邻性], [partner 的反馈"不与代码相邻"], [*错*。eval history 中与其自身 code 相邻；code 出现两次], [已更正并补两条事实],
  [R12　`text_feedback` 定位], [长期 canonical schema 之一], [*部分成立*。具评测反馈语义], [改为 MVP 捷径],
  [R13　D10 定级], ["第一跳没有实现路径"], [*过强*。已有同型流水线可借], [降为"关键集成缺口"],
  [R14　D2 的实验设计], [六臂，以"优于随机代码"为判据], [*不足*。不能识别机制迁移], [改为析因设计],
  [R15　D3 适用范围], [功效表被外推为整个设计], [*错*（部分）。表只对候选提交门有效], [已加限定，新增 D11],
  [R16　D4 的修补], [每个 Phase 都要 $Delta$ score], [*自相矛盾*], [改为两类里程碑],
  [R17　§4 新颖度], ["尚未被占位"], [*错*。已有多个最近邻], [已重写清单],
  [R18　结论含义], ["修必改后进窄切片"], [*不够*。H1 尚不可识别], [改为 Probe-0],
)

*Rev. 3 阶段（对第三轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*Rev. 2 的说法*], [*核验结果*], [*处理*],
  [R19　KAPSO 的地位], [仅作为 §4 清单中的一条先前工作], [*应提升*。它是唯一同时具备给定初始仓库、可接固定 evaluator、预算与续跑、MIT 且可 pip 安装的系统], [新增 §4.2，提为一级候选],
  [R20　KAPSO 的 KG 自动检索], [（复审方主张）evolve 会自动检索知识并注入 prompt], [*不成立*。findings 注入是纯 `str()` 拼接；KG 检索是挂给 coding agent 的 MCP 工具，调用与否由 agent 决定], [已注明，并列为 shootout 的观察点],
  [R21　`iteration_evaluator` 的角色], [（复审方主张）可把外部分数驱动进化，且我 Rev. 2 未查], [*不成立*。文档逐字说明 external metrics 不影响 idea generation、stopping、parent selection 与最终分支选择；固定 evaluator 的真实路径是 `eval_dir` 与注册评测], [已更正，并写明正确接入点],
  [R22　KAPSO 的 provenance], [（复审方主张）保存 URL/commit provenance], [*部分成立*。论文声称 URL + commit metadata、RepoStore 与 corpus manifest；代码只有 URL 级 provenance 与分支/时间戳，commit 固定、RepoStore、manifest、阈值 τ 全无], [已按"论文声称 / 代码实现"两栏列出],
  [R23　§4 的 KAPSO 行], [`research` 返回 candidate repositories 作 seeds，并带 repository provenance], [*源码不支持*。researcher 只返回 idea / implementation / report；`Source.Repo` 属 KG 摄入路径], [已降级为"论文口径，源码未证实"],
  [R24　配对条件（新 D12）], [共享同一 seed 与同一初始配置即为配对], [*不成立*。干预改变控制流会使状态式 PRNG 失同步；CRN 要求同一随机数用于对应的随机事件], [新增 D12，并改写 D11 的配对写法],
  [R25　D2 的 estimand 命名], [$E times M$，主估计量 $Y(E+M) - Y(E)$ 称为"机制迁移"], [*概念不严谨*。E 本身已编码机制，故它不是非机制臂], [改名为 $C times X$（外部代码 × 显式机制解释），并声明潜伏机制迁移不在该设计可识别范围内],
  [R26　§4 的层次判断], ["运行时开放世界获取 + 进化闭环已被占据"], [*过粗*。至少分三层：检索一次后进化、检索与进化交替、把检索/适配/交叉/内部进化作为策略分配。前两层已占位，第三层为部分占位], [已重写为三层判断],
)

== 0.6 我保留的分歧

+ *"KAPSO 已经解决了闭环，只差一个 VerifiedArtifact 边界"*：方向对，程度需限定。缺口不止 provenance 三项——`iteration_evaluator` 不参与选择意味着*用外部评测信号驱动搜索*这条路径在 KAPSO 里并非默认；且"闭环"目前是一个 E2E 示例脚本（依赖 codex 与 claude CLI、本地 Weaviate 与 Neo4j），不是产品化命令。故 P1 的实测必须按"示例脚本能否在真实任务上稳定跑通"来设定预期。
+ *CRN 的逐字引文*："same random numbers must be used for the same random events"无法确认到任何出处，建议改用可核的表述（见 D12 与 S68）。另需指出：*"同 seed 即配对"恰恰是 ML 基准领域的成文做法*（S52 逐字规定 A 与 B 复用同一 seed），故这不是"既有共识被违反"，而是*agentic 场景使该做法的前提失效*。
+ *决策策略层"已被某货架系统占位"*：按公开文献，未见任何货架系统同时把"获取外部实现／适配／交叉／继续内部进化"纳入同一学习策略；Dream-RSI 的策略作用在 discovery tree 上，ASI-Evolve 的 UCB1 属 sampler。该主张若指全层则不成立，若仅指"何时检索"或"何时选算子"则成立（D5）。
+ *目录层证据的可移植性*：沿用 Rev. 2 的处理——依赖本地目录状态，正确标注是"该证据集内不可独立复现"（自检命令见 §3.3）。
+ *TurboEvolve 的池"含人类编写的解"*：不成立（S55 的数据集定义为 run checkpoints）。
+ *EES 的 `external-source routes` 读作运行时取外部实现*：不成立（S64）。

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

第 3 步是承重点：*它假定两段都已有货架。* 四轮核验后，这个假定比计划写的更成立，也比计划写的更危险：*第一段的货架（KAPSO）比计划提到的任何组件都更接近目标*（§4.2），而计划选的组合（Man1Lab + ShinkaEvolve + AgentCo-Op）反而需要自己补上更多。第 2 步的顺序原则因此必须真的执行——这也是 Rev. 3 结论的核心。

== 1.2 我认可的部分

+ *目标层的重新收束是对的*：把"提高基础设施完整度"与"提高算法改进能力"分开。
+ *"架构可丢弃"作为硬约束有其可操作性*（计划:169）——Rev. 3 正是把它用在 ShinkaEvolve 上。
+ *多时间尺度分离*（计划:235-239）：若算法、经验、策略、harness 与评测同时变化，收益不可归因。
+ *从第一天记录轨迹以备将来 replay*（计划:581）。
+ *不继承 Man1Lab 的生成策略*（计划:474）：其 `generation_decision.py` 逐字包含 "Do not redesign algorithms or network architecture."。
+ *把外部实现交给自有 evaluator 定生死*：与 ShinkaEvolve 只接纳 `correct = 1` 的机制一致，也与 KAPSO 的 `eval_dir` hash manifest 方向一致。
+ *任务选择的阶梯*（计划:998-1004）。
+ *外部事实的可核实性*：三轮外部复审独立复检后，计划点名的系统仍无一虚构。

= 二、我的怀疑

下面十二条按后果排序。*D10、D11、D12 分别为 Rev. 1／2／3 新增，编号沿用以避免破坏交叉引用。*

== D1（重要）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（清单见计划:529-536），而 `metadata` 对 prompt 不可见，故该决策按文中所述不成立。

*证据一：metadata 不可见（快照 9912af12）*

- `sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(...)` 与可选反馈段；cross 专属段 `prompts_cross.py:57-73` 只写 partner 的 `code` 与 `perf_str(...)`。
- prompt 路径上读 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支的 `stdout_log`/`stderr_log`），不参与 mutation 与 cross。
- 更弱的第二条路径：`metadata["patch_name"]` → 元总结器 → `meta_recommendations` → 追加到系统消息，但条件为 `patch_type != "cross"`，且经 LLM 摘要。
- 计划:529-536 的六个键在仓库中*零命中*。

*证据二：正确注入面现成*

- `prompts_base.py:58-79`：每个程序在同一块内依次为 `prog.code`（:61）、其 metrics（:63-67）、`Text feedback:` + `prog.text_feedback`（:74-79）；开关默认 `False`（`core/config.py:62`）。
- `sampler.py:152-157` 把 archive 与 top-k 全部送入该函数，与 patch 类型无关；partner 的 code 在同一 message 中*出现两次*（`sampler.py:205-208`）；`CROSS_ITER_MSG` 的反馈段填的是 *parent* 的（`sampler.py:161-166`）。
- adapter 可自设该字段：`dbase.py:174`，`Database.add()` 原样落库（`849-857, 870, 890`），全仓库无 `UPDATE programs SET text_feedback`。

*映射（MVP 口径）*：

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 零改核捷径）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*三条限定*：cross 对位段无此通道；该字段属评测器语义、单字段约束（机制摘要与评测反馈竞争）；重复评测会新建一行携带评测器值（`async_runner.py:4160-4172`）。故它是 MVP 捷径，不宜在此阶段确立为长期 canonical schema。

*最小修补*：§4.3 改写为上述映射并写明三条限定。

== D12（重要，Rev. 3 新增）"同 seed"不等于配对：需要 event-keyed 随机源

*指控*：D11 建议的 `(Open_{t,r}, Closed_{t,r})` 配对若实现为"两边设置相同 seed"，*不构成配对实验*。

*证据*：

- common random numbers 的标准条件是"同一随机数用于*对应的用途/事件*"：S68 逐字为 "a specific random number used for a specific purpose in one configuration is used for exactly the same purpose in all other configurations"。
- 状态式 PRNG 在干预改变控制流时会使随机流失同步：S71 的 §1 逐字指出 CRN 的隐含假设是 "the same position in the random PRNG draw sequence corresponds to the same modeled event … across coupled scenarios"；该文给出的补救是 $U_e = g("seed", "event_id")$ 式的键控抽样（counter-based RNG）。
- 在本项目里，Open 臂天然比 Closed 臂多出检索、适配、交叉与额外评测事件，控制流必然分叉。
- *需明确的限定*：这不是"既有共识被违反"。ML 基准领域的成文做法恰恰是 A 与 B 复用同一 seed（S52 逐字："pairing A and B requires sampling seeds for each pairs, re-using the same seed for A and B in each pairs"）。正确表述是：*agentic 研究使该做法的前提失效*，因此需要更细的键控。

*可操作规则*：

+ *R1 抽样是纯函数*：$g("seed", "event_key")$，其中 `event_key` 由 task、run、事件类型、稳定实体 id 组成；使用 counter-based RNG，禁用单条顺序流；对事件键的唯一性加断言。
+ *R2 按源分流并标注可控性*：可控源（evaluator、task 划分、parent 选择、mutation 决策）跨条件键控共享；不可控源（闭源 LLM 采样、网络检索）按 `(task, run)` 记录并冻结——检索结果应在两条件间*共用同一份冻结快照*，才能在不可控源上近似 CRN。
+ *R3 不可控则放弃配对*：任一关键流不可控时，该 estimand 禁用配对检验，改 run 级独立复制并分解 $sigma_"run"$ 与 $sigma_"seed"$；键控清单与冻结清单需预注册。
+ *对照事实*：闭源 LLM 的 `seed` 参数本身不保证确定性（官方文档逐字："our system will make a best effort to sample deterministically … Determinism is not guaranteed"，建议以 `system_fingerprint` 监视后端变化，S72）。

*后果*：D11 的配对表若按"同 seed"实现，会得到*看起来配了、实际没配*的估计量——这比不配对更危险，因为它会给出偏窄的不确定性。

*最小修补*：§8 增一节"随机源清单与键控规则"，列出五条随机源（LLM／evaluator／parent／search／environment）及各自可控性；把"冻结 seed set"的表述改为"冻结事件键集合与检索快照"。

== D11（重要）统计设计把 evaluator seed 当成了实验单位

*Rev. 3 措辞修正*：Rev. 2 写的"H1 不可识别"过强（identifiability 是比这里强得多的概念），改为：*当前设计无法获得 campaign 级的重复测量不确定性估计*。Rev. 2 写的"r 常需 $>= 12$"同样是无方差依据的 magic number，已删除。

*指控*：计划 §5.1 的 `seeds: [11, 23, 47, 89, 131]`（计划:603）与 §14.2 的 `3 tasks × 3 conditions × n seeds`（计划:1342-1350）把 evaluator seed 当作 H1 的复现单位，这是 experimental unit 错位（pseudoreplication）。

*证据*：

- 随机性至少三层：`Y_{t,r,s}`（$t$ task、$r$ 完整 campaign、$s$ evaluator seed）。seed 是观测单位而非实验单位；当作复现单位会抬高自由度、降低临界阈值，制造假阳性（S48；S49 逐字 "Increasing the number of OUs does not increase the sample size"；S50 逐字 "the experimental unit is the number of subjects tested, rather than the number of observations made within each subject"）。
- *即使把同一 open-world search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`，并未估计 `E[pi_open] - E[pi_closed]`*；后者含 LLM 采样、parent 选择、检索、适配、交叉与整条轨迹的随机性。
- 两个统计问题必须分开：

```text
候选提交门  :  candidate × eval seeds    回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs   回答"开放世界的策略是否更好"
```

*分析程序*：

+ 先折叠 seed 层（每 run 取 seed 均值），再建 run 级模型 $d_{t,r} = mu + u_t + v_{t,r}$，$u_t ~ N(0, sigma_"task"^2)$，$v ~ N(0, sigma_"run"^2)$（S51）；或分层 bootstrap，按 task → run → seed 逐层重抽（S54）。
+ 条件间配对按 D12 的 event-keyed 规则实现，而不是"同 seed"。
+ task 仅 3 个时只报 task 级效应，禁止泛化到 task 总体。

*r 的规划*：$r = f(sigma_"run", "MDE", alpha, beta, "design")$；先由 pilot 估 $sigma_"run"$（取上置信限），*仍禁止用 pilot 的效应量*；嵌套设计效应 $ "DE" = 1 + (m-1)rho $，群数少须按群数取 $t$ 自由度（S53）。

*成本*：只加 seed 只作用于评测环节；重跑 campaign 则把整个研究过程乘以 r。增加*变异源*比堆同一源更省（S52 报告约 51 倍计算节省）。

*最小修补*：`statistics` 拆成 `gate` 与 `campaign` 两组；§8.1 明确分析单位是 `(task, run)`；§14.2 写出配对表与 r 的依据；预算为 r 留乘数。

== D2（重要）H1 的两种读法需要分开；析因设计只能回答其中一个

*背景*：计划的 H1 字面是工程效用假设（计划:1476-1480），对该假设 `C_open > C_closed` 本身有效。需要区分：

```text
H_U :  OpenWorld         -> UtilityGain    第一阶段可直接检验
H_M :  MechanismTransfer -> UtilityGain    需要因果识别设计
```

*Rev. 3 更正（命名与可识别范围）*：Rev. 2 的 $E times M$ 命名不严谨——*E（外部代码）本身已经编码了机制*，所以 E 不是"非机制"臂。改名为：

```text
C = External Code                     X = Explicit Mechanism Explanation
              X              not-X
C          C + X              C
not-C        X              （空）
对照：      C + X_matched  vs  C + X_shuffled      （token 匹配、同域但错配）
主估计量：  Delta_X = Y(C + X) - Y(C)
```

于是 $Delta_X$ 回答的是一个很干净的问题：*给已经看到代码的 agent 再解释"为什么这个算法有效"，有没有额外价值？* 而更宽意义上的"潜伏机制迁移"（代码中的机制被后代继承）需要程序结构或行为层面的分析，*不在本设计可识别范围内*——必须明文写出，不能用"机制迁移"一词把两者混起来。

*三点补充*：C 臂是自然干预（Shinka 默认通道即代码，D1），故主比较是 C 与 C+X，X 臂回答"代码是否必要"；$X_"shuffled"$ 必须同域且 token 匹配，否则退化为无效负对照（S29）；"adaptation diff 显示机制被使用"属中介证据——Loreley 的立场与此一致，它逐字声明 inspiration 边 "does not show that the agent used its contents or that it caused the resulting edit"（S56）。

== D3（重要）候选提交门的统计设计：数值正确，适用范围必须限定

*限定*：Rev. 0/1 的功效表*只对候选提交门有效*，外推为"整个设计的能力判断"是错的（D11）。表本身经三轮独立复算无误。

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

- 样本量由公式给出：

```text
n_gate = f(MDE, sigma_d, alpha, beta)
近似闭式: n ≈ (z_{1-alpha/2} + z_{1-beta})^2 · sigma_d^2 / MDE^2
精确解:    非中心 t，ncp = MDE·sqrt(n)/sigma_d，df = n-1，对 n 数值求根
           （闭式会低估: d_z=0.5、power=0.8 时给 31.4，精确值 34）
```

- *n=5 真正意味着什么*：该设计下最小可检测效应为 *$1.68 sigma_d$*。
- *pilot 只估 $sigma$*：用 pilot 效应量定样本量会因条件化选择而系统性高估效应（winner's curse / Type M，S42、S44；S43）。
- *非参数门恒零*：$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$。
- *多重比较*：§8.1 并列 8 个"主要指标"（计划:951-962）无单一主终点；三条件 Bonferroni 下 $n=5$、$d=1$ 功效降至 0.191。
- *confirmation 不独立*：§6.2 用"冻结 seed set"（计划:801-803），而全文唯一 seed 集是计划:603 的五个；文档未定义 pilot 的数据来源。若共用则 winner's curse 未消除（条件式）。按 D12，正确做法是冻结*事件键集合与检索快照*，不只是 seed。
- *不相交 seed 是必要非充分*：还需预注册 MDE、pilot 数据排除在最终统计外、campaign 级 FWER 与 alpha spending（S45）、分析冻结（S46）、seed 不得事后挑选。
- *α 与 lifetime 控制冲突*：§6.1 固定 per-test $alpha = 0.05$（计划:776）与 §6.2 自陈的 multiple testing 目标（计划:785）不相容。
- *SGM 名实*：被推迟的 e-value / error spending（计划:806）正是"统计门"名称的实质内容（S11）。
- *右删失*：`time to first improvement`（计划:954）无删失规则与生存分析，却规定用均值与置信区间汇总（计划:770）。

== D4（重要）护栏不可执行：两类里程碑与一致的治理

*指控（保留部分）*：§12.1（计划:1232-1242）是防止目标漂移的核心机制，但"milestone"与"Δ research capability"从未定义；计划不含工期、人力、算力预算与负责人；同目录缺少规范的决策沿革。

*Rev. 2 更正（沿用）*："每个 Phase 都要求 $Delta$ score"会重现它刚批评的自我触发问题。正确形式是两类里程碑：

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
   例: repo -> commit -> adapted candidate -> V_E 能否在限定时限/成本内稳定跑通
M_research   (研究期):     Delta verified algorithm capability
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化,
              而不是要求每个基础设施里程碑立即涨 score
```

*证据（治理部分）*：见 §3.3。要点：milestone 全文仅一次（计划:1242）；Phase 0/1 的交付按设计不产生算法能力增长；§12.1 与 §14.4 两套停止规则互不引用；无任何阶段要求"产出 verified improvement"（§8.3 反而把首版主验收定为"基础设施能否减少研究成本"，计划:1006）；全文唯一日期是版本号（计划:30）。

*最小修补*：按两类里程碑重写 §9 与 §12.1；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。

== D5（重要）H2 没有实验臂；且"决策策略层"的占位情况要分轴说

*指控*：H2（计划:1482-1496）声称存在比固定策略更高效的自适应策略，但 §8 与 §14 没有任何"自适应 vs 固定"对照。

*证据与分轴判断（Rev. 3 细化）*：Rev. 2 把"外部获取与内部进化的联合分配"整体称为"未来最有区分度的问题"，表述过宽。分层看：

+ *检索一次后进化*（`RetrieveOnce -> Evolve`）：已占位（MLE-STAR 用搜索引擎取模型构成初始解，S61）。
+ *检索与进化交替*（`Retrieve <-> Evolve`）：已占位（DeepEvolve 联网检索进入精化环，S63；MARCO 实时检索会议技术，S62）。
+ *把获取/适配/交叉/内部进化作为策略分配*：*部分占位*。"何时检索"轴在 QA／RAG 域已被充分形式化（Self-RAG、Search-R1、SEM 逐字 "teaching models to discern when to invoke search and when to rely on their internal knowledge"，S74）；"何时选算子"轴被经典自适应算子选择与近期的 LLM 进化调度占据（S75，如 RL 优化的 meta-controller 动态选择父代与变异方向）。但*把"获取外部实现"与"内部进化"纳入同一策略、且 acquisition 对象是带 provenance 的外部实现*——未见明确占位（AEL 的 Thompson Sampling 作用于 memory 检索策略，SciToolAgent-Evo 的 LinUCB 门控只针对工具获取，各占一半）。

*最小修补*：H2 首版降级为"轨迹收集目标"，明确写"本阶段不检验 H2"；未来的问题表述须分轴，并注明两个子轴已占位、只有联合层是空白：

```text
动作空间:  { ResearchExternal, RetrieveKnowledge, ContinueEvolution, RunExperiment, LearnExperience }
问题:      是否存在 pi(a_t | s_t, B_t) 使 Delta VerifiedPerformance / Cost 优于固定 pipeline
```

== D6（重要）未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（见 D10），并把 `understand` 写成管道一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）；J 的分母（计划:318）与 §12 都没有"仓库能跑但机制抽不出"的成本与失败模式。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"上网找到他人已解出的高分方案"；§8.3 却优先选"存在可搜索公开实现"的任务（计划:994）。旁证：EES 的厂商侧能力明列 web research 与 exploit discovery，同时自认"未被标记的行不等于该任务满足闭数据协议"（S64）；MLE-bench 必须明文禁止查看网上解法并用 Dolos 与 top-50 公开 notebook 比对（S24）。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046），无决策规则。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 *License Provenance Gate*：来源与依赖清单（URL + commit + hash + 许可）、指纹与相似度比对（Copilot 比对窗口约 150 字符，官方承认空文件更易命中，S32）、许可白/黑名单与义务登记、命中的派生隔离与替换重写。*Rev. 3 新证据*：TurboEvolve 把 provenance auditing 与 license verification 写在 Impact Statement 里作为未来建议（S55），而 KAPSO 连 license 字段都没有（§4.2）——说明这是全领域未做的缺口，且已有具体落点（P2 补丁）。
+ *供应链*：计划:1217-1219 只要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*` 并经加密 DNS 外传（S34）。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问，2013 年样本 38%（S33）。*Rev. 3 新证据*：KAPSO 的默认 seed 路径连 commit 都不固定（§4.2），意味着"可复现"在这一环上没有任何保障。

*最小修补*：把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12；给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离；给安装期网络与凭据策略；给外部资源快照归档。

== D10（重要）开放世界获取前端并不存在——但这是集成缺口

*指控*：计划:58 把"开放世界获取已有相当成熟的实现基础"列为第一条工程认识，并把 Man1Lab 定为 acquisition front-end（计划:421-425、456-487）。*该成熟度对 Man1Lab 不成立*：它当前没有任何"问题 → 候选仓库"的搜索路径。

*证据（快照 `5376e58d` = main HEAD；PyPI 1.3.0 同源）*：

- `src/providers/github/client.py:61` 逐字：`raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`；全包无调用点。
- `GitHubCollectionProvider` 的输入是论文分析里已存在的 URL（`collection.py:1, 46, 56-58, 124-153`），无 query 参数；官方审计文档逐字 "No Search API"、"deterministic, Search-free"。
- 全包不存在其它发现路径：默认 provider 仅 Embedded / GitHub / NoOp；gap 派生的 `ResourceNeed` 只被生成、无 provider 消费。
- 规划与实现要分开：ADR-0016:161 把 conditional search 列入 Phase 1，实作停在无搜索的 1.2 → 1.3.0 状态。

*附带的语义问题*：`verified` 被用于指两件事——$V_D$（发现层可信：仓库存在、身份、许可、归档状态）与 $V_E$（任务层可执行：在冻结 evaluator 下跑通并产生可比指标）。Man1Lab 只提供 $V_D$；只有 $V_E$ 通过者才能进入进化种群。其 ADR-0016:142 自陈 "Shallow verification does not guarantee runnable repos — Execution may still fail"。

*Rev. 2/3 的定级*：这不是"研究基础设施缺口"，而是*关键集成缺口*。直接借鉴的已发表路线：KAPSO 的 knowledge/research 面（§4.2）、AutoSOTA 从论文 PDF 抽 GitHub 链接得初始仓库（S60）、MLE-STAR 的搜索→初始解（S61）。*但要更正 Rev. 2 的一处过度解读*：计划字面没有写"Man1Lab 搜索 GitHub"，故指控限定在计划:58 的成熟度判断与 §4.1 的定位上。

*最小修补*：把 acquisition 拆成 Search（现成检索的薄封装）与 Ingest（借 schema 与 $V_D$），并写清 $V_D$ 不等于 $V_E$。

== D7（次要但影响可复核性）引用卫生

*指控*：计划声称"进行了系统调查"（计划:214）并列有参考资料附录（计划:1511），但从文档本身无法复核。

*证据*：正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名 17 个外部系统，其中 12 个无条目。FunSearch 全文 0 次出现（三轮独立 `grep -c` 核实为 0），MLE-bench、RE-Bench 亦 0 次。

*最小修补*：补引用 + 一节"相关工作与差异"，并按 §4 的清单逐条写明"谁已做到哪一步"。

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
+ *与 MetaRSI 的路线冲突未解释*：MetaRSI 为"单一循环内核 + 联合调度"（S14），与计划:231-239 的固定偏序及"evaluator anchor 原则上冻结"冲突，文档未说明为何拒绝。
+ *发现步骤的归属与验收缺失*：见 D10。
+ *Man1Lab 的接口性质被低估*：Decision Foundation 为非公开 API，Repository Adaptation 仍在 roadmap（S1、S39）；这与"六阶段与五个规则确实存在于源码"不矛盾——文档化的阶段与已交付的能力是两件事。

= 三、我的证据

== 3.1 外部系统源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。Collection → Evidence → Verification → Ranking → Selection 见架构文档；六阶段见执行规划文档；五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0，无论文。*两项能力断言不成立*：（1）无"问题 → 候选仓库"搜索路径（D10）；（2）其 `verified` 仅指 $V_D$，非 $V_E$。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive、多 provider 均为真。Apache-2.0，arXiv:2509.19349（ICLR 2026），PyPI `shinka-evolve` 0.0.7。*但 `metadata` 不是灵感通道*（D1）。*且它只做单文件程序进化*，不原生支持给定仓库（S35 组内对比）。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*；`NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约。arXiv:2605.20425。*过强的一处*：`sandbox_repo` 自述 "command builder only"，`execute_live` 分支返回 "not wired in framework phase"，即只产出 dry-run 命令规格；随包 adapter 多为 stub（外部 commit 为 `TODO_PIN`）。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
  [ASI-Evolve], [*sampler 断言为真*：`database/algorithms/` 下 random / greedy / ucb1 / island + factory。Apache-2.0，arXiv:2603.29640，无 PyPI。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline；且只做单程序进化。],
  [Dream-RSI], [*论文真实*（arXiv:2609.14858）；*代码尚未发布*（仅 README 与 release plan），故计划:368 的"完整源码尚非稳定依赖"偏保守。许可无法确认。*命名偏差*见 D8。],
)

引用的研究谱系（计划:214、§9.7、§15）10 项*全部真实存在*：

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

见 D3、D11、D12。功效采用非中心 $t$（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$），另以 $10^5$ 次蒙特卡洛验证，三轮外部复审的独立复算亦一致。$n=5$ 时最小可检测效应 $1.68 sigma_d$。

== 3.3 文档族物证

自检命令（在包含这些文件的目录下运行即可复现本报告的目录层断言）：

```text
ls -la *.typ
grep -n "seeds:" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
grep -nE "supersede|取代|废弃|作废|以本文为准" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
```

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版标注；该标注属待执行的"C0 本地落库动作"，旧版（09-09 20:13）未加标注；Makefile 通配符把两者都编成 PDF。
- `algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml 19 行中 18 行逐字相同（含 seed 列表），Experiment Record 同源而异；两份 mtime 同为 09-18 14:32（被审计划 15:25）；互不引用，均无取代声明。
- 至少三套并存的统计提交门（ADA、OPL、本计划）。
- 该族另有引用不存在文件的情况（如 `adapdc_architecture_report.typ`、`research-foundations.md`）。
- *可移植性限度*：以上第 1、2、4 条依赖本地目录状态；外部复审的证据集不含这些文件时，其正确标注是"该证据集内不可独立复现"。

== 3.4 排版与构建实测

构建：`typst 0.15.1` 下 `typst compile` 退出码 0、无 warning，输出 20 页 A4。A4 页宽 595.276pt，页边距 68.031pt，正文右边界 527.245pt。方法：`pdftotext -bbox` 逐词取框 + 解压 PDF content stream 读取每个 text run 的笔位，两法交叉一致。

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

结论：6 处显示公式溢出页边距，其中仅 *1 处*（计划:951-962 的 `Y` 指标元组）真正越出纸张被裁切——PDF 第 13 页该行只抽到 "external con" 即断。这份文档的核心主张就是一组测量指标，而它的主指标清单在纸面上被裁掉了最后两项。

= 四、与先前工作的关系

== 4.1 新颖度的三层判断（Rev. 3 重写）

Rev. 1 称"外部实现 × 反事实贡献 × provenance 尚未被占位"——*错*。Rev. 2 改称"运行时开放世界获取 + 进化闭环已被占据"——*过粗*。Rev. 3 给出分层判断：

+ *架构层*（把外部知识或外部实现接进进化循环）：*已大量占位*。
+ *检索一次后进化*（`RetrieveOnce -> Evolve`）：已占位（MLE-STAR，S61）。
+ *检索与进化交替*（`Retrieve <-> Evolve`）：已占位（DeepEvolve S63、MARCO S62）。
+ *决策策略层*（把获取/适配/交叉/内部进化当作策略分配）：*部分占位*——"何时检索"（QA 域，S74）与"何时选算子"（S75）两个子轴均已占位，但把*外部实现获取*与*内部进化*纳入同一策略、且 acquisition 对象带 provenance，未见明确占位（D5）。

#table(
  columns: (2.6cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*工作*], [*占位*], [*依据*],
  [FunSearch 等三篇], [A（弱）], [冻结 evaluator + 程序库 + 检索高分实现进 prompt；初始程序由人给出（S18、S19、S20）],
  [TurboEvolve　2604.18607], [A], [`seed-pool injection`：既有解池聚类后分配到各 island 作种子；*池来源是作者自跑 checkpoint，非人类解、非网络获取*；无 provenance、无逐 seed 归因；provenance 与 license 被列为未来建议（S55）],
  [Loreley　2608.19703], [A + B（负）], [以完整 git commit 为 evolutionary artifact、isolated worktrees、项目自带 evaluator、QD archive，并显式区分 parent 边与 inspiration 边；逐字声明 inspiration 边 "does not show that the agent used its contents or that it caused the resulting edit"；自认未做 inspiration 消融（S56）],
  [Kernel Foundry　2605.30359], [A + B], [从 KernelBook 检索 top-5 核作 few-shot 初始化 → 多岛进化；含专家初始化消融（S57）],
  [TuneNNGen　2607.05704], [A + B], [外部同族仓库代码作 prompt 指导；等预算 target-only vs source-guided；direct-copy 分解 + 负对照——*最接近"某条外部灵感是否导致改进"的已发表反事实*（S58）],
  [KAPSO　2601.21526], [A + C（论文口径）], [公开 API 有 research、learn_knowledge、evolve、learn 与 E2E 闭环示例；论文声称 URL + commit provenance（§4.2 详列，含源码未实现项）。*Rev. 3 更正 Rev. 2 的行内判断*：源码并不支持"research 返回候选仓库作 seeds"],
  [AutoSOTA　2604.05550], [A + C], [从论文 PDF 抽取 GitHub 链接并规范化为初始仓库（S60）],
  [MLE-STAR　2506.15692], [A + C + B（块级）], [用搜索引擎检索 web 上的模型构成初始解；含代码块级消融（S61）],
  [MARCO　2505.03906], [B + C], [实时检索近期会议论文的优化技术；有/无 web search 对比（S62）],
  [DeepEvolve　2510.06056], [B（通道级）+ C], [联网 PubMed/arXiv 检索进入迭代精化环；含 deep research 消融（S63）],
  [EES　2609.17590], [强基线，非先例], [validation gate + 持久记忆 + operator credit；其 `external-source routes` 指外部数据/答案查找，不是取外部实现；自认"不估计这些机制的边际收益"（S64）],
)

*由此得出的新颖度状态*：*架构层已被占据；决策策略层部分占位；单条外部灵感的 provenance 归因仍有价值，但不是唯一或最大的研究问题。* 计划当前的差异主张（§4 与附录）需要按此三层重写，而不是继续用"开放世界获取"这一笼统说法。

== 4.2 KAPSO：一级货架候选的能力与边界（Rev. 3 新增）

*为什么单列*：它是唯一同时具备（a）给定初始仓库、（b）可接固定 evaluator 的路径、（c）预算／续跑／实验记录，且 MIT、可 pip 安装（`leeroo-kapso` 0.4.7，需 Node.js 与 codex／claude CLI）、当日仍在提交的系统。按计划自己的工程顺序（计划:44-46），*先实测它、再决定是否写 adapter* 是唯一自洽的做法。

#table(
  columns: (2.9cm, 1fr, 2.3cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [开放式网络检索], [`kapso.py:434-465`；底层 `researcher.py:75-139` 仅 list 模式返回 findings，单模式返回 idea／implementation／report；检索经 codex 原生 web search（`cli_inference.py:104-119, 193-210`）], [成立，带限定],
  [三类研究目标], [`researcher.py:141-153` 校验 idea／implementation／study 三类], [成立],
  [实现条目的字段], [`types.py:96-116` 的字段为 query／source／content；`source` 只是 LLM 写在标签里的文本，解析器（`research_findings.py:101-131`）不校验 URL], [部分成立],
  [两个 API 的签名], [`kapso.py:467-476`（`learn_knowledge`）；`1129-1154`（`evolve`，含 `initial_repo`、`resume`）], [成立],
  [检索结果注入 prompt], [是，但为纯 `str()` 拼接（`kapso.py:1292-1307` → `handlers/generic.py:125-130` → `strategy.py:457`）；传 list 时得到 dataclass repr；`context` 的 docstring 写 "learn before evolving" 而实现无 learn 步骤], [成立但弱，存在文档-行为不一致],
  [知识检索是否自动], [*不成立*。两条路径均非自动注入：`initial_repo` 为空时做一次 workflow repo 搜索（top_k=1）；或挂 idea／code／kg 三个 MCP gate 交给 coding agent，*调用与否由 agent 决定*], [更正],
  [闭环的可运行入口], [`examples/ml_model_development/run_full_loop.py` 逐字含 `research -> learn_knowledge -> evolve -> learn -> evolve` 并有 "LOOP NOT CLOSED" 断言；但它是 E2E 示例脚本（依赖 codex 与 claude CLI、本地 Weaviate 与 Neo4j），CLI 无 `learn_knowledge` 动词], [成立，非产品化],
  [固定 evaluator 的接入], [真实路径是 `eval_dir` → hash manifest 与 `evaluation_integrity`（PROVIDED），另有注册评测；非默认路径，默认由 agent 生成评测目录], [成立，需显式指定],
  [外部评测回调的作用], [`iteration_evaluator`：*不成立*。官方文档逐字："External metrics are deliberately separate from Kapso's internal `node.score`. They do not affect idea generation, stopping, parent selection, or the final branch selected by default."（S67）], [更正],
  [预算／续跑／记录／记忆], [`budget.py`、`run_checkpoint.py`、`experiment_memory`、`learning/` 与 `knowledge_base/` 均在], [成立],
  [外部工件边界], [`Source.Repo` 只有 `(url, branch)`（`types.py:47-59`）；摄取克隆是 `git clone --depth 1 -b`（`repo_ingestor/utils.py:18-76`），seed 克隆是 `clone_from(url, temp_dir)`（`kapso.py:1781`，连 branch 都不传）；外部仓库*无 commit 固定、无内容哈希、无 license 字段、无可执行性验证*（"可执行"只是静态检测 `__main__`）；被记录的 provenance 仅 url／branch／时间戳], [缺口：$V_E$ 与 license 闸门],
  [论文声称与代码], [论文 §4.2 声称 "referenced by URL and commit metadata"、provenance 回链 paths 与 commits、`RepoStore` 与 corpus manifest（含 commit identifiers）、§3.4 的 `RepoRetrieve` 与阈值；代码侧 URL provenance 与快照 seed 有，commit metadata／RepoStore／manifest／阈值全无], [论文超出代码],
)

*结论*：KAPSO 已解决"开放世界检索 + 知识摄入 + 长程进化"的大部分，但它的外部工件边界恰好缺少我们要求的四项（commit 固定、内容哈希、许可、可执行性验证 $V_E$）。*这与 D6 的 License Provenance Gate 是同一个缺口*——缺口因此变得具体、可施工，而不是"造一个开放世界研究系统"。

= 五、建议与判据

== 5.1 结论

*有条件推进——先做货架优先的能力对决（shelf-first capability shootout），不先写 adapter；H1 的 A/B 仍在其后。* 理由：（a）H1 的识别设计尚未就绪（D11、D12）；（b）新颖度需要按三层重写（§4.1）；（c）而在写任何新代码之前，必须先量出现成系统离目标有多远——这是计划"架构可丢弃"原则在 ShinkaEvolve 上的直接应用。

*要避免的代理谬误已经换了一次位置*：不再是 ADA/OPL，而可能是"既然研究了 ShinkaEvolve，就默认围绕它建系统"。

== 5.2 Shelf-first capability shootout（建议的下一步）

只取一个真实算法任务与同一个冻结 evaluator，按台阶上行：

```text
P1  KAPSO 原生                    直接跑，看示例脚本能否在真实任务上稳定走通
P2  KAPSO + 最小 provenance/验证补丁   commit 固定 + 内容哈希 + license 记录 + V_E 门
P3  Loreley 原生                   唯一原生以"给定仓库 + 项目 evaluator + job 预算"为中心的系统
P4  仅当 P1–P3 明确不满足时才做       Search(薄封装) + Ingest(schema 与 V_D) + ShinkaEvolve
```

记录项（不比较算法分数）：

```text
成本: (C_setup, C_search, C_understand, C_adapt, C_eval, C_provenance, C_maintenance)
失败: FailureStage  +  search_failed / comprehension_failed / mechanism_mismatch
```

*预期与判据*：若 P2 已覆盖大部分需求，则工程计划应围绕"KAPSO extension / evaluation"而不是"Man1Lab + Shinka + 自建 adapter"；若 P1/P2 在真实任务上败在运维或语义映射，*失败位置本身就是下一步工程需求的最可靠定义*。P2 的成本之所以可能很低，是因为缺口只集中在四项边界的补齐（§4.2）。

*为什么 P3 不是冗余*：Rev. 2 的 Probe-0 隐含预选了 ShinkaEvolve 作为 runtime。KAPSO 与 Loreley 是两条彼此独立的货架路线；只测一条会重犯"锚定单组件"的错误。Loreley 的代价要如实计入：alpha 版（0.7.6a0）、需 Postgres + Redis + docker + Kilocode CLI 与 embedding 端点、单人单星，且其论文自认 48 jobs 时 QD 未胜过 Sequential Champion。

== 5.3 五项必改（在 shootout 之后、进 H1 之前）

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（需 `use_text_feedback = true`）+ `metadata` 三分；写明三条限定；`text_feedback` 定位为 MVP 捷径。],
  [*分离两套统计设计*（D3 + D11 + D12）：`statistics.gate` 与 `statistics.campaign` 两组字段；分析单位是 `(task, run)`；配对按 event-keyed 随机源实现，不可控源按 `(task, run)` 冻结；预算为 r 留乘数。],
  [*按 $C times X$ 析因重写 §8.2*（D2）：5 臂（C+X／C／X／空 + shuffled explanation），主估计量 $Delta_X$；明文写出潜伏机制迁移不在可识别范围内；若只主张 $H_U$ 则删除 §1.6／§2.2 的机制迁移措辞。],
  [*两级验证与获取归属*（D10）：acquisition = Search + Ingest，明确 $V_D$ 不等于 $V_E$；只有 $V_E$ 通过者进入种群。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$ 与 $M_"research"$ 分开，proxy guard 约束成本/能力比；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

== 5.4 建议改

+ 把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12（D6）。
+ 给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离（D6）。
+ 按 §4.1 的三层判断重写新颖度表述，并按 §4.2 的清单补参考文献（D7）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行（实测可将最宽者从 ≈701.5pt 降到边距内）。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.5 Go / No-Go 判据

*进 H1 A/B 的门槛*：shootout 已完成且 P1–P3 的失败位置已被记录；run 级配对的 `(Open_{t,r}, Closed_{t,r})` 表与 event-keyed 随机源清单存在；预注册的单一主终点与 MDE；与 Open 条件 token 匹配的负对照；confirmation 使用不相交且未事后挑选的事件键集合；外部搜索／验证／适配的开销全部计入 open 臂。

*在满足上述前提后*：若 $Delta$ 不显著，必须同时报告*搜索失败率*与*机制抽取失败率*，以区分"没找到候选"、"没读懂仓库"、"机制不可迁移"。计划现有判据（计划:1076）无法区分，这是最需要修补的单点。

== 5.6 什么会使我改变判断

+ 若 P1/P2 实测表明 KAPSO 加最小补丁即满足需求 → 本报告 §5.2 的 P4 应删除，且计划应改写为"KAPSO 扩展"。
+ 若作者指出一条四轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1 的第一部分。
+ 若作者给出文档外的定义，说明 pilot 与 confirmation 使用不相交且未事后挑选的事件键 → D3 该条降级。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级。
+ 若 Man1Lab 或其它组件在后续版本实现了"问题 → 候选仓库"的搜索 → D10 的该部分撤回（需附版本与调用点）。

= 六、我撤回或修正的判断

*Rev. 0 内部已修正（第一轮反证）*

#enum(
  [*公式越界范围*：越出*页面*被裁切的只有 1 处（计划:951-962，≈701.5pt，两侧各裁约 53pt）；其余 5 处仅溢出页边距。],
  [*灵感槽位数*：论文与 `island_small`／`island_large` preset 为 4/2，`island_medium` 与类默认（`dbase.py:63-64`）为 1/1。],
  [*SGM 的"唯一提供物"*：SGM 另含 certificate → 状态转移协议与 checkpoint / held-out 审计。],
)

*Rev. 1 阶段*

#enum(
  [*D1 的补救措施*：`Program.text_feedback` 已是现成通道，不必改核心。],
  [*archive 不变量*：仅默认路径要求 `correct=1` 且已入 archive；`best_program_id` 路径只检查 `correct`。],
  [*AgentCo-Op 的能力*：只产出 dry-run 命令规格。],
  [*Experiment Record 的同一性*：Task Contract 18/19 行相同，Experiment Record 同源而异。],
  [*ARI 计划的日期*：mtime 为 09-18 14:32。],
  [*样本量建议*：$n>=20$ 无依据，改为公式化程序。],
  [*"proxy drift 已经发生"*：修正为"治理缺陷已确认"。],
  [*"许可传染"*：按 AGPL §2 的条件式表述重写。],
  [*引用行号*：`license` 三处应为 533、626、1046。],
)

*Rev. 2 阶段*

#enum(
  [*cross 与反馈的相邻性*：partner 的反馈不出现在 dedicated crossover block 中，但在 eval history 中与其自身 code 相邻；其 code 出现两次。],
  [*`text_feedback` 的定位*：MVP 捷径，非长期 canonical schema。],
  [*D10 的定级*：改为"关键集成缺口"。],
  [*D2 的实验设计*：改为析因设计。],
  [*D3 的适用范围*：功效表只对候选提交门有效。],
  [*D4 的修补方案*：改为两类里程碑。],
  [*§4 的新颖度结论*："尚未被占位"是错的。],
  [*最终结论*：改为 Probe-0。],
)

*Rev. 3 阶段*

#enum(
  [*KAPSO 在 §4 表内的行*：Rev. 2 写"research 阶段返回 candidate repositories 作 seeds，并带 repository provenance"，*源码不支持*——researcher 只返回 idea／implementation／report，`Source.Repo` 属 KG 摄入路径。已降级为"论文口径，源码未证实"。],
  [*KAPSO 的 KG 自动检索*：Rev. 3 核验认定"自动检索并注入"不成立，已改为"MCP 工具交由 agent 自行调用"。],
  [*`iteration_evaluator` 的作用*：Rev. 2 未查证，现更正为"observational，不参与选择"；固定 evaluator 的真实接入点是 `eval_dir` 与注册评测。],
  [*KAPSO 的 provenance*：更正为"论文声称 commit metadata 与 RepoStore，代码只有 URL 级 provenance"，并按两栏列出。],
  [*配对条件*：Rev. 2 的"共享同一 seed 与同一初始配置"不成立，改为 event-keyed 随机源；"冻结 seed set"不等于 CRN。],
  [*D11 的措辞*："不可识别"过强，改为"无法获得 campaign 级的重复测量不确定性估计"；删除 $r >= 12$ 这一无依据数字。],
  [*D2 的命名*：$E times M$ 改为 $C times X$，并声明潜伏机制迁移不在该设计可识别范围内。],
  [*§4 的层次判断*："运行时闭环已被占据"过粗，改为三层判断（架构层已占位／决策策略层部分占位）。],
  [*Probe-0 的实现选择*：Rev. 2 隐含预选 ShinkaEvolve 为 runtime，已改为四台阶 shootout（P1 KAPSO／P2 KAPSO+补丁／P3 Loreley／P4 自建）。],
  [*CRN 的引文*：无法确认"same random numbers must be used for the same random events"的出处，已改用可核的表述；并更正"同 seed 不足"的强度——ML 基准领域的成文做法恰是复用同 seed。],
)

另有两项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属；KAPSO 论文所述独立知识包（corpus commit manifest 等）不在 GitHub 仓库中，其是否真含 commit identifiers 无法确认。

= 附录 A：审查覆盖范围

四轮共 37 个独立审查轴。Rev. 0（20）：五个核心系统源码级核实；Gödel machine 谱系；harness 谱系；统计与实验设计；内部一致性与可行性；与 ADA／OPL／ARI 的一致性；与 adapdc 系列的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；Typst 构建与排版实测；两轮专项反证；引用元数据三轮核实。Rev. 1（6）：`text_feedback` 通道与 inspiration 过滤不变量；Man1Lab 搜索能力（三快照）；AgentCo-Op 的 repo 执行能力；目录层治理事实；许可表述精度；样本量程序的统计陷阱。Rev. 2（6）：cross 模式 prompt 逐行核对；TurboEvolve／Loreley／EES 逐篇核实；穷尽式最近邻检索（约 40 组查询）；experimental unit 错位的方法学核实。Rev. 3（5）：KAPSO 的公开 API 面与闭环；KAPSO 的 provenance 与外层边界；common random numbers 与 event-keyed randomness；货架候选横向普选（6 系统，源码实测）；决策策略层是否已被占位（约 20 组检索）。

= 附录 B：来源清单

*核心依赖*

- [S1] Man1Lab — https://github.com/maniac1um/Man1Lab （MIT）
- [S2] Man1Lab on PyPI — `man1lab` v1.3.0
- [S3] ShinkaEvolve — https://github.com/SakanaAI/ShinkaEvolve ；arXiv:2509.19349（ICLR 2026）
- [S4] ShinkaEvolve on PyPI — `shinka-evolve` 0.0.7
- [S5] AgentCo-Op — https://github.com/ma-compbio-lab/AgentCo-Op ；arXiv:2605.20425
- [S6] ASI-Evolve — https://github.com/GAIR-NLP/ASI-Evolve ；arXiv:2603.29640
- [S7] Dream-RSI — https://github.com/zhengkid/Dream-RSI ；arXiv:2609.14858

*RSI 与 harness 谱系*

- [S8] DGM — arXiv:2505.22954
- [S9] HGM — arXiv:2510.21614
- [S10] MGM — arXiv:2608.07645
- [S11] SGM — arXiv:2510.10232
- [S12] RQGM — arXiv:2606.26294
- [S13] SE-GoS — arXiv:2609.08228
- [S14] MetaRSI — arXiv:2609.06396
- [S15] AHE — arXiv:2604.25850
- [S16] HarnessFix — arXiv:2606.06324
- [S17] RobustSGPO — arXiv:2609.09646

*先前工作、基准与理论*

- [S18] FunSearch — Nature 625, 468–475, doi:10.1038/s41586-023-06924-6
- [S19] AlphaEvolve — arXiv:2506.13131
- [S20] OpenEvolve — https://github.com/algorithmicsuperintelligence/openevolve
- [S21] The AI Scientist — arXiv:2408.06292
- [S22] AIDE — arXiv:2502.13138
- [S23] PaperBench — arXiv:2504.01848
- [S24] MLE-bench — arXiv:2410.07095
- [S25] RE-Bench — arXiv:2411.15114
- [S26] Open-endedness 议程 — PMLR 235:20597–20616 / arXiv:2406.04268
- [S27] OMNI-EPIC — arXiv:2405.15568
- [S28] POET — arXiv:1901.01753
- [S29] Min et al., *Rethinking the Role of Demonstrations* — arXiv:2202.12837

*风险论据*

- [S30] pip secure installs — https://pip.pypa.io/en/stable/topics/secure-installs/
- [S31] AGPL-3.0 §0、§2、§5(c)、§13
- [S32] GitHub Copilot code referencing（2023）
- [S33] Pew Research, *Link Rot and Digital Decay*, 2024-05-17
- [S34] PyTorch, compromised nightly dependency（torchtriton）
- [S35] 货架系统对比（源码实测 2026-09-18）：KAPSO、Loreley、OpenEvolve、ShinkaEvolve、ASI-Evolve 的许可证／安装／evaluator 接入／初始仓库／budget／provenance 对照
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`；`inspirations.py:57-128, 143-242, 342-353`；`core/config.py:62`
- [S39] Man1Lab 搜索能力（快照 `5376e58d` = main HEAD）— `src/providers/github/client.py:43, 48, 61`；`collection.py:1, 46, 56-58, 88, 124-153`；`verification.py:1, 47`；`docs/reviews/1.2_github_collection_provider/audit.md:49, 55, 171, 182`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 3, 28, 62-83, 86-130`；`core/runtime.py:118-122, 167`；`core/gates.py`；`compiler.py:206-224, 388, 405`；`integrator.py:75-90`；`core/sandbox_build.py:303-331`；`wrappers/gears/adapter.py:47`
- [S41] AGPL-3.0 §0 与 §2 原文 — https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-or-later.txt
- [S42] Zöllner & Pritchard, AJHG 80(4):605-615, 2007 — doi:10.1086/512821
- [S43] Leon, Davis & Kraemer, J Psychiatr Res 45(5):626-629, 2011 — PMID 21035130
- [S44] Gelman & Carlin, Perspect Psychol Sci 9(6):641-651, 2014 — doi:10.1177/1745691614551642
- [S45] DeMets & Lan, Stat Med 13(13-14):1341-1352, 1994 — doi:10.1002/sim.4780131308
- [S46] Nosek et al., PNAS 115(11):2600-2606, 2018 — doi:10.1073/pnas.1708274114
- [S47] R `stats::power.t.test`；Cohen 1988

*方法学（experimental unit 与嵌套设计）*

- [S48] Hurlbert, Ecol Monogr 54(2):187-211, 1984 — doi:10.2307/1942661
- [S49] Lazic, Clarke-Williams & Munafò, PLoS Biol 16(4):e2005282, 2018 — doi:10.1371/journal.pbio.2005282
- [S50] Makin & Orban de Xivry, eLife 8:e48175, 2019 — doi:10.7554/eLife.48175
- [S51] Gelman & Hill, *Data Analysis Using Regression and Multilevel/Hierarchical Models*, 2006
- [S52] Bouthillier et al., *Accounting for Variance in Machine Learning Benchmarks*, MLSys 2021 — arXiv:2103.03098（附录 C.2 Pairing：A 与 B 复用同一 seed）
- [S53] Hemming et al., BMC Med Res Methodol 11:102, 2011 — doi:10.1186/1471-2288-11-102
- [S54] Saravanan, Berman & Sober, hierarchical bootstrap — bioRxiv doi:10.1101/819334

*最近邻工作*

- [S55] TurboEvolve — arXiv:2604.18607
- [S56] Loreley — arXiv:2608.19703（代码 Apache-2.0）
- [S57] Kernel Foundry — arXiv:2605.30359
- [S58] TuneNNGen — arXiv:2607.05704
- [S59] KAPSO 论文 — arXiv:2601.21526
- [S60] AutoSOTA — arXiv:2604.05550
- [S61] MLE-STAR — arXiv:2506.15692
- [S62] MARCO — arXiv:2505.03906
- [S63] DeepEvolve — arXiv:2510.06056
- [S64] EES — arXiv:2609.17590

*Rev. 3 新增*

- [S65] KAPSO 仓库 — https://github.com/Leeroo-AI/kapso （MIT；PyPI `leeroo-kapso` 0.4.7；快照 HEAD `7d99b15`）
- [S66] KAPSO 源码路径 — `src/kapso/kapso.py:434-465, 467-476, 1129-1154, 1292-1307, 1745-1753, 1763, 1781, 1791-1825`；`src/kapso/researcher/researcher.py:75-139, 141-153, 189-192`；`src/kapso/knowledge_base/types.py:47-59, 96-116`；`src/kapso/repo_ingestor/utils.py:18-76`；`src/kapso/environment/handlers/generic.py:125-130`；`src/kapso/execution/search_strategies/generic/strategy.py:396-400, 457`；`examples/ml_model_development/run_full_loop.py`
- [S67] KAPSO 外部评测文档 — `docs/evolve/external-evaluation.mdx:14-16, 80-81`（external metrics 不影响 idea generation、stopping、parent selection 与最终分支选择）
- [S68] Botev & Ridder, *Variance reduction*, Wiley StatsRef 2017 — doi:10.1002/9781118445112.stat07975 （CRN 的"同一用途"表述）
- [S69] L'Ecuyer et al., *An object-oriented random-number package with many long streams and substreams*, Operations Research 50(6):1073, 2002
- [S70] Salmon et al., *Parallel random numbers: as easy as 1, 2, 3*, SC'11
- [S71] Buffalo, Pearson & Klein, *Realizing Common Random Numbers: Event-Keyed Hashing for Causally Valid Stochastic Models*, arXiv:2603.11084（stat.ME）
- [S72] OpenAI OpenAPI 对 `seed` 的说明（"Determinism is not guaranteed…refer to the `system_fingerprint` response parameter"）
- [S73] Loreley 运行约束 — `preflight.py:751-755` 强制 `WORKER_EVALUATOR_PLUGIN`；需 Postgres + Redis + docker + Kilocode CLI + embedding 端点
- [S74] "何时检索"轴 — Self-RAG arXiv:2310.11511；Search-R1 arXiv:2503.09516；SEM arXiv:2505.07903
- [S75] "何时选算子"轴 — AEL arXiv:2604.21725（Thompson Sampling 选择 memory 检索策略）；SciToolAgent-Evo arXiv:2607.28692（LinUCB 门控工具获取）；GAE arXiv:2607.10127（RL meta-controller 选择父代与变异方向）；TOPOFE arXiv:2607.23286

*同目录文档*

- [S36] `algorithm_research_infrastructure_plan.typ`、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
