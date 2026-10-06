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
  #text(size: 9.5pt)[本报告版本：*Rev. 4*（2026-09-20）· 四轮外部复审的核验记录 · 本轮为最后一轮文献修订]
  #v(2pt)
  #text(size: 9.5pt)[结论：*先做 Runtime Shootout（Stage A），再做开放世界增强（Stage B）；不先写 adapter*]
  #v(2pt)
  #text(size: 9.5pt)[本报告不含对尚未存在的实验结果的评价]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 4 总评*：第四轮核验只改了三处，但其中一处会改变 §5.2 的整体设计。

  #v(3pt)

  + *货架候选查漏又漏了一个，而且分量很重*：EvE（arXiv:2605.09018，仓库 `scaling-group/eve`）是本次所核系统里*唯一把 `(github_url, commit)` 写进 application contract*、并且*让外部 evaluator 的分数真的驱动采样与 Elo* 的系统。我此前"Loreley 是唯一以给定仓库与项目 evaluator 为中心的系统"的说法撤回。
  + *KAPSO 的 P2 估计与我自己已核实的证据自相矛盾*（这一条是文档内部就能推出的）。真正的缺口是*五项*：除 commit 固定、内容哈希、许可、$V_E$ 四项边界之外，还缺"外部评测信号进入搜索选择"——KAPSO 默认*不*用外部指标改变父代选择、停止或最终分支。更根本地，从"网页研究报告"到"可克隆的仓库（含 commit）"这一步，KAPSO 目前是*完全人工*。
  + *因此 §5.2 拆成两阶段*：先 Stage A（只测 evolution substrate，三套系统吃同一组 `(repo@commit, evaluator, budget, objective)`），再 Stage B（在胜出 runtime 上加开放世界获取）。这样 *open-world 效应与 runtime 效应解耦*——这是 Rev. 3 的四台阶方案做不到的。

  #v(3pt)

  *本报告在此终止文献审查*：继续纯阅读的边际收益已明显下降，下一步应是拿一个真实算法仓库，把三个候选各跑一次最小 smoke campaign。
]

= 零、审查方式与限度

== 0.1 方法

本报告由五轮构成。Rev. 0 为全文精读 + 20 个并行独立审查轴（源码级事实核实、专项反证、统计复核、构建与排版实测）。Rev. 1 为对第一轮复审意见的独立核验（+6 轴）。Rev. 2 为对第二轮复审意见的独立核验（+6 轴）。Rev. 3 为对第三轮复审意见的独立核验（+5 轴）。Rev. 4 为对第四轮复审意见的独立核验（+4 轴：EvE 的完整断言核实、KAPSO 的 research → repository resolution 缺口、货架候选二次查漏、Stage A 三方可接入性）。

五轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。每轮都产生了对本报告自身判断的更正（见 §6）。

*终止条件*：Rev. 4 是最后一轮文献修订。理由有二：（a）本轮的二次查漏虽然又找到若干候选（CORAL、EvoX Genesis 等），但均已不再改变工程决策的顺序；（b）更有价值的信息现在只能来自实测——三个候选各自的最小 smoke campaign。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行，不存在可评价的数据。
- 源码核实基于 2026-09-20 的公开快照，逐系统标注 HEAD：KAPSO `7d99b152`、EvE `979065fd`、Loreley `4c375920`、ShinkaEvolve `9912af12`、Man1Lab `5376e58d`、AgentCo-Op `94c37504`；被审计划本身未固定版本。
- *货架候选的"已穷尽"断言在全报告中被明确放弃*。检索口径限于 arXiv 与公开 GitHub 仓库；未覆盖非 arXiv 正式论文集、闭源或仅 demo 的系统、以及论文无仓库的双向缺失项。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S85）见附录 B。第三方源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → 1 → 2 → 3 → 4）

*Rev. 1 阶段（对第一轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R1　D1 补救措施], [注入机制文本"必须自定义 `PromptSampler`"], [*不成立*。存在现成的 per-inspiration 文本通道], [已改为 code / text_feedback / metadata 映射],
  [R2　D2 定级], ["致命"（无法归因）], [*部分成立*。对该假设封闭 vs 开放有效], [降为"重要"，区分 H_U 与 H_M],
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
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R19　KAPSO 的地位], [仅作为 §4 清单中的一条先前工作], [*应提升*。它同时具备给定初始仓库、可接固定 evaluator 的路径、预算与续跑], [新增 §4.2，提为一级候选],
  [R20　KAPSO 的 KG 自动检索], [evolve 会自动检索知识并注入 prompt], [*不成立*。findings 注入是纯 `str()` 拼接；KG 检索是挂给 coding agent 的 MCP 工具], [已注明],
  [R21　`iteration_evaluator` 的角色], [可把外部分数驱动进化，且我 Rev. 2 未查], [*不成立*。文档逐字说明 external metrics 不影响选择], [已更正],
  [R22　KAPSO 的 provenance], [保存 URL/commit provenance], [*部分成立*。论文声称 commit metadata 与 `RepoStore`，代码只有 URL 级 provenance], [已按两栏列出],
  [R23　§4 的 KAPSO 行], [`research` 返回 candidate repositories 作 seeds], [*源码不支持*], [已降级为"论文口径，源码未证实"],
  [R24　配对条件（新 D12）], [共享同一 seed 即配对], [*不成立*。干预改变控制流会使状态式 PRNG 失同步], [新增 D12],
  [R25　D2 的 estimand 命名], [$E times M$], [*概念不严谨*。C 本身已编码机制], [改名为 $C times X$],
  [R26　§4 的层次判断], ["运行时闭环已被占据"], [*过粗*。至少分三层], [已重写为三层判断],
)

*Rev. 4 阶段（对第四轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R27　货架普选漏项], [漏了 EvE，且 Loreley"唯一 repository-native"不成立], [*成立，且分量很重*。见 D13：EvE 是所核系统中唯一把 `(github_url, commit)` 写进 application contract、并让外部 evaluator 分数驱动采样与 Elo 的系统], [新增 D13；撤回"唯一"说法；EvE 与 KAPSO 并列为一级候选],
  [R28　KAPSO 的 P2 成本], [缺口不止四项 provenance 字段，还缺 `ResearchFinding -> ResolvedArtifact`], [*成立，且比此更严重*。缺口是*五项*：第四项之外还缺"外部评测信号进入搜索选择"；且 research → 可克隆仓库目前完全人工], [§4.2 结论与 §5.2 一并改写],
  [R29　shootout 结构], [拆成 Stage A（只测 substrate）与 Stage B（开放世界增强）], [*接受*。这是让 open-world 效应与 runtime 效应解耦的唯一办法], [§5.2 重写为两阶段],
  [R30　EvE 的论文题名], ["Evolutionary Ensemble of Agents"], [*错*。实际题名为 *Evolving Ensemble of Agents*（arXiv:2605.09018v4）], [已按实际题名引用],
  [R31　EvE 的依赖与分发], [（未主张），我据此推断可类比其它系统], [*需更正*：EvE 无 PyPI 包（`pip install eve` 会装到无关项目），走 `uv sync` 源码安装；默认 testbed 不需 GPU，仅 ICON 示例需 2×GPU], [已在 §4.3 写明],
  [R32　KAPSO 的"两条路径"], [ImplementationText 与 Source.Repo 互不相通], [*部分成立*。与仓库解析脱节的是 idea／implementation／research report *三类*产物；且不存在 `Source.Study`（study 模式返回 `Source.ResearchReport`）], [已按三类产物改写],
  [R33　Loreley 的版本与依赖], [（沿用我 Rev. 3 的 0.7.6a0 与"需 Kilocode + embedding 端点"）], [*过时／过宽*。HEAD 发布说明为 v0.9.0-alpha；示例路径用 codex_cli 与 local-hash，不需 embedding 端点], [已更正],
  [R34　§0.1 的"6 系统"计数], [（我自己写的）], [与 S35 实际所列不符（5 个）；本轮二次查漏又增补若干候选], [已改为"候选清单 + 明确放弃穷尽断言"],
)

== 0.6 我保留的分歧

+ *EvE 的论文题名*：引用须用 *Evolving Ensemble of Agents*（S76）；用它做 Stage A 时必须注意 `(github_url, commit)` 的成对强制是*代码级契约*（论文正文无此约定，仅附录 A.3 提到 repository snapshot）。
+ *CRN 的逐字引文*："same random numbers must be used for the same random events" 无法确认到任何出处，用 S68 的可核表述。"同 seed 即配对"是 ML 基准领域的成文做法（S52 逐字规定 A 与 B 复用同一 seed），故正确表述是*agentic 场景使该前提失效*。
+ *决策策略层"已被某货架系统占位"*：未见任何货架系统同时把获取外部实现／适配／交叉／继续内部进化纳入同一学习策略（D5）。
+ *目录层证据的可移植性*：依赖本地目录状态；外部证据集不含这些文件时，正确标注是"该证据集内不可独立复现"（自检命令见 §3.3）。
+ *TurboEvolve 的池"含人类编写的解"*：不成立（S55 的数据集定义为 run checkpoints）。
+ *EES 的 `external-source routes` 读作运行时取外部实现*：不成立（S64）。
+ *KAPSO 是"最贴合的候选"*：Rev. 3 的这一表述已被 R27 取代——EvE 在 commit 契约与外部分数驱动选择两项上强于 KAPSO。

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

第 3 步是承重点：*它假定两段都已有货架。* 五轮核验后这个假定比计划写的更成立，也比计划写的更危险：第一段的货架（KAPSO、EvE）比计划提到的任何组件都更接近目标（§4.2、§4.3），而计划选的组合（Man1Lab + ShinkaEvolve + AgentCo-Op）反而需要自己补上更多。第 2 步的顺序原则因此必须真的执行——这一次要执行到"连 runtime 也不预先指定"。

== 1.2 我认可的部分

+ *目标层的重新收束是对的*：把"提高基础设施完整度"与"提高算法改进能力"分开。
+ *"架构可丢弃"作为硬约束*（计划:169）——Rev. 3／4 正是把它用在 ShinkaEvolve 上。
+ *多时间尺度分离*（计划:235-239）。
+ *从第一天记录轨迹以备将来 replay*（计划:581）。
+ *不继承 Man1Lab 的生成策略*（计划:474）：其 `generation_decision.py` 逐字包含 "Do not redesign algorithms or network architecture."。
+ *把外部实现交给自有 evaluator 定生死*：与 ShinkaEvolve 只接纳 `correct = 1`、与 EvE 把外部脚本分数接进采样一致。
+ *任务选择的阶梯*（计划:998-1004）。
+ *外部事实的可核实性*：四轮外部复审独立复检后，计划点名的系统仍无一虚构。

= 二、我的怀疑

下面十三条按后果排序。*D10、D11、D12、D13 分别为 Rev. 1／2／3／4 新增，编号沿用以避免破坏交叉引用。*

== D1（重要）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（清单见计划:529-536），而 `metadata` 对 prompt 不可见，故该决策按文中所述不成立。

*证据一：metadata 不可见（快照 9912af12）*

- `sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(...)` 与可选反馈段；cross 专属段 `prompts_cross.py:57-73` 只写 partner 的 `code` 与 `perf_str(...)`。
- prompt 路径上读 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支的 `stdout_log`/`stderr_log`），不参与 mutation 与 cross。
- 更弱的第二条路径：`metadata["patch_name"]` → 元总结器 → `meta_recommendations` → 追加到系统消息，条件为 `patch_type != "cross"`，且经 LLM 摘要。
- 计划:529-536 的六个键在仓库中*零命中*。

*证据二：正确注入面现成*

- `prompts_base.py:58-79`：每个程序在同一块内依次为 `prog.code`（:61）、metrics（:63-67）、`Text feedback:` + `prog.text_feedback`（:74-79）；开关默认 `False`（`core/config.py:62`）。
- `sampler.py:152-157` 把 archive 与 top-k 全部送入该函数，与 patch 类型无关；partner 的 code 在同一 message 中*出现两次*（`sampler.py:205-208`）；`CROSS_ITER_MSG` 的反馈段填的是 *parent* 的（`sampler.py:161-166`）。
- adapter 可自设该字段：`dbase.py:174`，`Database.add()` 原样落库（`849-857, 870, 890`），全仓库无 `UPDATE programs SET text_feedback`。

*映射（MVP 口径）*：

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 零改核捷径，非长期 canonical schema）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*三条限定*：cross 对位段无此通道；该字段属评测器语义、单字段约束；重复评测会新建一行携带评测器值（`async_runner.py:4160-4172`）。

== D13（重要，Rev. 4 新增）货架候选查漏不完整，而漏掉的正是最贴合的那个

*指控*：Rev. 3 的"货架候选横向普选"漏掉了 EvE，并且任何"已穷尽"的暗示都不成立。

*证据（EvE 七项断言逐条核实，快照 main @ `979065fd`）*：

+ *存在性*：仓库 `scaling-group/eve`（Apache-2.0，release v0.2.0，59 star，Python≥3.11），论文 arXiv:2605.09018v4，题名 *Evolving Ensemble of Agents*，作者 Zongmin Yu、Liu Yang。无 PyPI 包（`pip install eve` 装到无关项目），安装走 `uv sync`。
+ *commit 契约*：`github_url` 与 `commit` 必须成对，缺失即 `ValueError`（`problem/repo.py:56-57`），与 `path` 互斥；`repo.py:167-179` 用 `git rev-parse` 解析后 `git archive` 造快照，该快照即 boundary 基线。*这是代码级契约，论文正文无此约定。*
+ *编辑边界*：`editable.files`／`editable.folders` 为一等配置且不可同时为空（`repo.py:110-111`）；检查器在 `workflow/boundary.py:104-131, 152-200, 212-223`，越界以退出码 1 拒绝并取 `boundary_failure_score`。
+ *评测驱动选择*：shell evaluator 经 `subprocess.Popen(["bash", step], cwd=..., env={EVE_SOLVER_ROOT: ...})` 执行（`workflow/evaluation.py:306-314`），分数从 `$EVE_EVAL_LOG_ROOT/score.yaml` 读回（`:918-935`）；分数确实进入选择——`phase2.py:544` 写入种群、`:597-606` 按 `entry.score` 采样。*需精确化一处*：评测的 cwd 不是 agent 写码的 workspace，而是重建的只读评测工作区（`evaluation.py:634-670`）。
+ *共同进化*：`workflow/loop.py:26-27` 自述 "Explicit co-evolution loop"；solver 与 guidance 两个种群互相采样（`phase2.py:553-584`），guidance 侧由 solver 分数与两两胜负的 Elo 更新（`phase3.py:47-56, 71-80`）。
+ *阶段对照*：README 与论文有 Static-Initial／Static-Final 对照，核心主张是阶段相关的 agent 适配；但仓库无对应开关，只能用 `produce_optimizer_in_phase2=0` 近似。
+ *可运行性*：`uv run python -m scaling_evolve.algorithms.eve.runner --config-name=circle_packing.smoke`；纯 CPU、sqlite、无 docker/Postgres/Redis/Node，但需 Codex CLI 与登录态。*注意*：`core/engine.py:224-241` 的 `StopConditions`（wallclock／token／cost）在全仓库（含 tests）*无任何实例化*，即未接线，用量仅记账。

*为什么这个漏项分量重*：在所核系统里，EvE 是*唯一*同时满足"`(github_url, commit)` 成对强制"与"外部脚本分数驱动采样"的系统。按计划自己的工程顺序，它应当与 KAPSO 并列进入 Stage A。

*完整性*：本报告的"货架候选已穷尽"断言*明确放弃*。本轮二次查漏又发现（均未逐行核实到与 EvE 同等强度）：CORAL（arXiv:2604.01658，摘要含 "evaluator separation"，Apache-2.0）、EvoX Genesis（arXiv:2608.10450，AGPL-3.0，2026-09-17 仍在提交）、AHE 的仓库形态、EvoGit（arXiv:2506.02049，已被 Genesis 取代）、MappingEvolve、Live-SWE-agent、ParEVO。未覆盖类：非 arXiv 正式论文集、闭源或仅 demo 的系统、论文无仓库的双向缺失项。

*另需纳入的一条反向证据*：arXiv:2602.16805 *Simple Baselines are Competitive with Code Evolution* 直接用三域实验否定代码进化管线的边际价值（S82）。这是计划核心赌注的反面证据，应进入 §4.1 的新颖度讨论与 §8 的对照设计——它恰好就是"简单基线是否已经够用"这个对照。

== D12（重要）"同 seed"不等于配对：需要 event-keyed 随机源

*指控*：D11 建议的 `(Open_{t,r}, Closed_{t,r})` 配对若实现为"两边设置相同 seed"，*不构成配对实验*。

*证据与规则*：

+ common random numbers 的标准条件是"同一随机数用于*对应的用途/事件*"：S68 逐字为 "a specific random number used for a specific purpose in one configuration is used for exactly the same purpose in all other configurations"。
+ 状态式 PRNG 在干预改变控制流时会使随机流失同步：S71 的 §1 逐字指出 CRN 的隐含假设是 "the same position in the random PRNG draw sequence corresponds to the same modeled event … across coupled scenarios"；补救是 $U_e = g("seed", "event_id")$ 式键控抽样。
+ *限定*：ML 基准领域的成文做法恰是 A 与 B 复用同一 seed（S52 逐字："pairing A and B requires sampling seeds for each pairs, re-using the same seed for A and B in each pairs"）。正确表述是 *agentic 研究使该做法的前提失效*。
+ *R1 纯函数抽样*：`g(seed, event_key)`，`event_key` 由 task、run、事件类型与稳定实体 id 组成；用 counter-based RNG，禁单条顺序流，并对事件键唯一性加断言。
+ *R2 按源分流*：可控源（evaluator、task 划分、parent 选择、mutation 决策）跨条件键控共享；不可控源（闭源 LLM 采样、网络检索）按 `(task, run)` 记录并冻结，检索结果在两条件间*共用同一份冻结快照*以近似 CRN。
+ *R3 不可控则放弃配对*：任一关键流不可控时该 estimand 禁用配对检验，改 run 级独立复制并分解 $sigma_"run"$ 与 $sigma_"seed"$；键控清单与冻结清单需预注册。
+ *对照事实*：闭源 LLM 的 `seed` 不保证确定性（S72 逐字："our system will make a best effort to sample deterministically … Determinism is not guaranteed"）。

== D11（重要）统计设计把 evaluator seed 当成了实验单位

*措辞*：不是"H1 不可识别"，而是*当前设计无法获得 campaign 级的重复测量不确定性估计*；r 的取值由公式给出，不设 magic number。

*证据*：

- 随机性至少三层：`Y_{t,r,s}`（$t$ task、$r$ 完整 campaign、$s$ evaluator seed）；seed 是观测单位而非实验单位（S48；S49 逐字 "Increasing the number of OUs does not increase the sample size"；S50 逐字 "the experimental unit is the number of subjects tested, rather than the number of observations made within each subject"）。
- 即使把同一 open-world search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`，并未估计 `E[pi_open] - E[pi_closed]`。

```text
候选提交门  :  candidate × eval seeds    回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs   回答"开放世界的策略是否更好"
```

*分析程序*：先折叠 seed 层（每 run 取均值），再建 run 级模型 $d_{t,r} = mu + u_t + v_{t,r}$，$u_t ~ N(0, sigma_"task"^2)$，$v ~ N(0, sigma_"run"^2)$（S51）；或分层 bootstrap（S54）；配对按 D12 的 event-keyed 规则实现；task 仅 3 个时只报 task 级效应。

*r 的规划*：$r = f(sigma_"run", "MDE", alpha, beta, "design")$；由 pilot 估 $sigma_"run"$ 并取上界，禁用 pilot 效应量；设计效应 $ "DE" = 1 + (m-1)rho $，群数少须按群数取自由度（S53）。

*成本*：只加 seed 只作用于评测环节；重跑 campaign 把整个研究过程乘以 r。增加*变异源*比堆同一源更省（S52 报告约 51 倍计算节省）。

== D2（重要）H1 的两种读法需要分开；析因设计只能回答其中一个

```text
H_U :  OpenWorld         -> UtilityGain    第一阶段可直接检验
H_M :  MechanismTransfer -> UtilityGain    需要因果识别设计
```

*命名（Rev. 3 沿用）*：$C$ = 外部代码，$X$ = 显式机制解释。因 $C$ 本身已编码机制，$C$ 不是"非机制"臂：

```text
              X              not-X
C          C + X              C
not-C        X              （空）
对照：      C + X_matched  vs  C + X_shuffled      （token 匹配、同域但错配）
主估计量：  Delta_X = Y(C + X) - Y(C)
```

$Delta_X$ 回答：*给已经看到代码的 agent 再解释"为什么这个算法有效"，有没有额外价值？* 更宽意义上的潜伏机制迁移需要程序结构或行为层面的分析，*不在本设计可识别范围内*，必须明文写出。

*三点补充*：C 臂是自然干预（Shinka 默认通道即代码，D1）；$X_"shuffled"$ 必须同域且 token 匹配，否则退化为无效负对照（S29）；"adaptation diff 显示机制被使用"属中介证据——Loreley 逐字声明 inspiration 边 "does not show that the agent used its contents or that it caused the resulting edit"（S56）。

== D3（重要）候选提交门的统计设计：数值正确，适用范围必须限定

*限定*：Rev. 0/1 的功效表*只对候选提交门有效*。表本身经四轮独立复算无误。

#table(
  columns: (auto, auto, auto, auto, auto, auto),
  inset: 4pt,
  stroke: 0.4pt,
  [*n*], [*d=0.5*], [*d=0.75*], [*d=1.0*], [*d=1.5*], [*d=2.0*],
  [5], [0.141], [0.254], [0.401], [0.711], [0.909],
  [10], [0.293], [0.562], [0.803], [0.987], [1.000],
  [20], [0.565], [0.889], [0.989], [1.000], [1.000],
)

由公式给出样本量，而不是拍一个数：

```text
n_gate = f(MDE, sigma_d, alpha, beta)
近似闭式: n ≈ (z_{1-alpha/2} + z_{1-beta})^2 · sigma_d^2 / MDE^2
精确解:    非中心 t，ncp = MDE·sqrt(n)/sigma_d，df = n-1，对 n 数值求根
           （闭式会低估: d_z=0.5、power=0.8 时给 31.4，精确值 34）
```

*其余要点*：$n=5$ 时最小可检测效应为 $1.68 sigma_d$；pilot 只估 $sigma$（用 pilot 效应量会因条件化选择而高估，S42、S44、S43）；$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$；三条件 Bonferroni 下 $n=5$、$d=1$ 功效降至 0.191；confirmation 与 pilot 若共用 seed 则 winner's curse 未消除，且按 D12 正确做法是冻结*事件键集合与检索快照*；§6.1 固定 per-test $alpha = 0.05$（计划:776）与 §6.2 自陈的 multiple testing 目标（计划:785）不相容；被推迟的 e-value／error spending（计划:806）正是"统计门"名称的实质内容（S11）；`time to first improvement`（计划:954）无删失规则与生存分析。

== D4（重要）护栏不可执行：两类里程碑与一致的治理

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
   例: repo -> commit -> adapted candidate -> V_E 能否在限定时限/成本内稳定跑通
M_research   (研究期):     Delta verified algorithm capability
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化,
              而不是要求每个基础设施里程碑立即涨 score
```

*证据*：milestone 全文仅一次（计划:1242）；Phase 0/1 的交付按设计不产生算法能力增长；§12.1 与 §14.4 两套停止规则互不引用；无任何阶段要求"产出 verified improvement"（§8.3 反而把首版主验收定为"基础设施能否减少研究成本"，计划:1006）；全文唯一日期是版本号（计划:30）。治理部分见 §3.3。

*最小修补*：按两类里程碑重写 §9 与 §12.1；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。

== D5（重要）H2 没有实验臂；"决策策略层"的占位要分轴说

+ *检索一次后进化*：已占位（MLE-STAR，S61）。
+ *检索与进化交替*：已占位（DeepEvolve S63、MARCO S62）。
+ *把获取/适配/交叉/内部进化作为策略分配*：*部分占位*。"何时检索"轴在 QA／RAG 域已被形式化（S74）；"何时选算子"轴被经典自适应算子选择与近期 LLM 进化调度占据（S75）。但把*外部实现获取*与*内部进化*纳入同一策略、且 acquisition 对象带 provenance，未见明确占位。

*最小修补*：H2 首版降级为"轨迹收集目标"；未来问题须分轴表述，并注明两个子轴已占位：

```text
动作空间:  { ResearchExternal, RetrieveKnowledge, ContinueEvolution, RunExperiment, LearnExperience }
问题:      是否存在 pi(a_t | s_t, B_t) 使 Delta VerifiedPerformance / Cost 优于固定 pipeline
```

== D6（重要）未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（D10、D13），并把 `understand` 写成管道一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）；J 的分母（计划:318）与 §12 都没有"仓库能跑但机制抽不出"的成本与失败模式。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"上网找到他人已解出的高分方案"；§8.3 却优先选"存在可搜索公开实现"的任务（计划:994）。旁证：EES 的厂商侧能力明列 web research 与 exploit discovery，同时自认"未被标记的行不等于该任务满足闭数据协议"（S64）；MLE-bench 必须明文禁止查看网上解法并用 Dolos 与 top-50 公开 notebook 比对（S24）。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046），无决策规则。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 *License Provenance Gate*：来源与依赖清单（URL + commit + hash + 许可）、指纹与相似度比对（Copilot 比对窗口约 150 字符，官方承认空文件更易命中，S32）、许可白/黑名单与义务登记、命中的派生隔离与替换重写。*旁证*：TurboEvolve 把 provenance auditing 与 license verification 列为未来建议（S55），KAPSO 无 license 字段，EvE 的 `configs/` 与 `src/` 中 `license` 零命中——全领域未做的缺口，且已有具体落点。
+ *供应链*：计划:1217-1219 只要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*` 并经加密 DNS 外传（S34）。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问，2013 年样本 38%（S33）。*旁证*：KAPSO 默认 seed 路径连 commit 都不固定（§4.2）。

*最小修补*：把 `search_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12；给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离；给安装期网络与凭据策略；给外部资源快照归档。

== D10（重要）开放世界获取前端并不存在——但这是集成缺口

*指控*：计划:58 把"开放世界获取已有相当成熟的实现基础"列为第一条工程认识，并把 Man1Lab 定为 acquisition front-end（计划:421-425、456-487）。*该成熟度对 Man1Lab 不成立*：它当前没有任何"问题 → 候选仓库"的搜索路径。

*证据（快照 `5376e58d` = main HEAD；PyPI 1.3.0 同源）*：

- `src/providers/github/client.py:61` 逐字：`raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`；全包无调用点。
- `GitHubCollectionProvider` 的输入是论文分析里已存在的 URL（`collection.py:1, 46, 56-58, 124-153`），无 query 参数；官方审计文档逐字 "No Search API"、"deterministic, Search-free"。
- 全包无其它发现路径：默认 provider 仅 Embedded／GitHub／NoOp；gap 派生的 `ResourceNeed` 只被生成、无 provider 消费。
- ADR-0016:161 把 conditional search 列入 Phase 1，实作停在无搜索的 1.2 → 1.3.0 状态。

*附带的语义问题*：`verified` 被用于指 $V_D$（发现层可信）与 $V_E$（任务层可执行）两件事；Man1Lab 只提供 $V_D$（ADR-0016:142 自陈 "Shallow verification does not guarantee runnable repos — Execution may still fail"），只有 $V_E$ 通过者才能进入进化种群。

*定级与依赖*：这是*关键集成缺口*，不是研究基础设施缺口。可借路线：KAPSO 的 knowledge 面（§4.2）、EvE 的 `(github_url, commit)` 契约（§4.3）、AutoSOTA（S60）、MLE-STAR（S61）。*计划字面没有写"Man1Lab 搜索 GitHub"*，故指控限定在计划:58 的成熟度判断与 §4.1 的定位上。

*Rev. 4 补充*：真正的缺口不是"缺 Search"，而是*缺 Search result → executable artifact 的 resolution*（见 §4.2 对 KAPSO 的五项缺口分析）。

== D7（次要但影响可复核性）引用卫生

*指控*：计划声称"进行了系统调查"（计划:214）并列有参考资料附录（计划:1511），但从文档本身无法复核。

*证据*：正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名 17 个外部系统，其中 12 个无条目。FunSearch 全文 0 次出现（四轮独立 `grep -c` 核实为 0），MLE-bench、RE-Bench 亦 0 次。

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
+ *与 MetaRSI 的路线冲突未解释*：MetaRSI 为"单一循环内核 + 联合调度"（S14），与计划:231-239 的固定偏序及"evaluator anchor 原则上冻结"冲突，文档未说明为何拒绝。*Rev. 4 补充*：EvE 选择了把 solver 与 guidance 放在同一个共同进化环里（§4.3），说明"联合调度"在工程上已有可运行实现，计划的固定偏序需要给出更强的理由。
+ *发现步骤的归属与验收缺失*：见 D10。
+ *Man1Lab 的接口性质被低估*：Decision Foundation 为非公开 API，Repository Adaptation 仍在 roadmap（S1、S39）；这与"六阶段与五个规则确实存在于源码"不矛盾。

= 三、我的证据

== 3.1 外部系统源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。Collection → Evidence → Verification → Ranking → Selection 见架构文档；六阶段见执行规划文档；五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0，无论文。*两项能力断言不成立*：（1）无"问题 → 候选仓库"搜索路径（D10）；（2）其 `verified` 仅指 $V_D$。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive、多 provider 均为真。Apache-2.0，arXiv:2509.19349，PyPI `shinka-evolve` 0.0.7。*但 `metadata` 不是灵感通道*（D1）；*且只做单文件程序进化*，不原生支持给定仓库。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*；`NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约。arXiv:2605.20425。*过强的一处*：`sandbox_repo` 自述 "command builder only"，只产出 dry-run 命令规格；随包 adapter 多为 stub。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
  [ASI-Evolve], [*sampler 断言为真*：random／greedy／ucb1／island + factory。Apache-2.0，arXiv:2603.29640，无 PyPI。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline；且只做单程序进化。],
  [Dream-RSI], [*论文真实*（arXiv:2609.14858）；*代码尚未发布*（仅 README 与 release plan），故计划:368 的"完整源码尚非稳定依赖"偏保守。许可无法确认。],
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
  [AHE], [2604.25850], [有], [可证伪的 harness 修改；仓库亦公开],
  [HarnessFix], [2606.06324], [有], [轨迹诊断与修复],
  [RobustSGPO], [2609.09646], [无官方], [权限调度],
)

== 3.2 统计复核数字

见 D3、D11、D12。功效采用非中心 $t$（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$），另以 $10^5$ 次蒙特卡洛验证，四轮外部复审的独立复算亦一致。$n=5$ 时最小可检测效应 $1.68 sigma_d$。

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
- *可移植性限度*：以上第 1、2、4 条依赖本地目录状态；外部复审的证据集不含这些文件时，正确标注是"该证据集内不可独立复现"。

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

结论：6 处显示公式溢出页边距，其中仅 *1 处*（计划:951-962 的 `Y` 指标元组）真正越出纸张被裁切。这份文档的核心主张就是一组测量指标，而它的主指标清单在纸面上被裁掉了最后两项。

= 四、与先前工作的关系

== 4.1 新颖度的三层判断

+ *架构层*（把外部知识或外部实现接进进化循环）：*已大量占位*。
+ *检索一次后进化*（MLE-STAR，S61）；*检索与进化交替*（DeepEvolve S63、MARCO S62）：均已占位。
+ *决策策略层*（把获取/适配/交叉/内部进化当作策略分配）：*部分占位*（D5）。
+ *尚存的价值主张*：在进化 archive 内部、带 commit／license／hash provenance 的单条外部灵感的反事实归因——但它已被 TuneNNGen（S58）与 Kernel Foundry（S57）逼近。
+ *必须正视的反面证据*：S82 用三域实验主张"简单基线在代码进化任务上已具竞争力"。计划的核心赌注应当把这条作为首要对照，而不是只对照封闭世界进化。

#table(
  columns: (2.6cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*工作*], [*占位*], [*依据*],
  [FunSearch 等三篇], [A（弱）], [冻结 evaluator + 程序库 + 检索高分实现进 prompt；初始程序由人给出（S18、S19、S20）],
  [TurboEvolve　2604.18607], [A], [`seed-pool injection`：既有解池聚类后分配到各 island 作种子；池来源是作者自跑 checkpoint；无 provenance、无逐 seed 归因（S55）],
  [Loreley　2608.19703], [A + B（负）], [以完整 git commit 为 evolutionary artifact、isolated worktrees、项目自带 evaluator、QD archive，并显式区分 parent 边与 inspiration 边；自认未做 inspiration 消融（S56）],
  [EvE　2605.09018], [A + B（阶段对照）], [repository 为工作对象且强制 `(github_url, commit)`；editable 边界检查；外部 shell evaluator 分数驱动采样与 Elo；solver 与 guidance 共同进化；Static-Initial／Static-Final 对照主张阶段相关适配（S76、S77）],
  [Kernel Foundry　2605.30359], [A + B], [从 KernelBook 检索 top-5 核作 few-shot 初始化 → 多岛进化；含专家初始化消融（S57）],
  [TuneNNGen　2607.05704], [A + B], [外部同族仓库代码作 prompt 指导；等预算 target-only vs source-guided；direct-copy 分解 + 负对照（S58）],
  [KAPSO　2601.21526], [A + C（论文口径）], [公开 API 有 research、learn_knowledge、evolve、learn 与 E2E 闭环示例；论文声称 URL + commit provenance（§4.2 详列）。源码不支持"research 返回候选仓库作 seeds"],
  [AutoSOTA　2604.05550], [A + C], [从论文 PDF 抽取 GitHub 链接并规范化为初始仓库（S60）],
  [MLE-STAR　2506.15692], [A + C + B（块级）], [用搜索引擎检索 web 上的模型构成初始解；含代码块级消融（S61）],
  [MARCO　2505.03906], [B + C], [实时检索近期会议论文的优化技术；有/无 web search 对比（S62）],
  [DeepEvolve　2510.06056], [B（通道级）+ C], [联网 PubMed/arXiv 检索进入迭代精化环；含 deep research 消融（S63）],
  [EES　2609.17590], [强基线，非先例], [validation gate + 持久记忆 + operator credit；其 `external-source routes` 指外部数据/答案查找（S64）],
  [CORAL　2604.01658], [未核实], [摘要含 "evaluator separation"；仅核到元数据／摘要级（S80）],
  [EvoX Genesis　2608.10450], [A + C，B 未确认], [文档支持 "point it at your codebase and enter your objective"；未见外部 evaluator 配置项（S81）],
)

== 4.2 KAPSO：能力的边界与五项缺口

*定位（Rev. 4 更正）*：Rev. 3 曾称 KAPSO 是"唯一同时具备给定初始仓库、可接固定 evaluator、预算与续跑的系统"——该说法已被 R27 取代。EvE 同样具备，且在 commit 契约与外部分数驱动选择两项上更强。KAPSO 的独特性在于*知识摄入 + 长程实验编排*这一侧。

#table(
  columns: (2.9cm, 1fr, 2.3cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [开放式网络检索], [`kapso.py:434-465`；底层 `researcher.py:75-139` 仅 list 模式返回 findings；检索经 codex 原生 web search（`cli_inference.py:104-119, 193-210`）], [成立，带限定],
  [三类研究产物], [idea／implementation／research report；study 模式返回 `Source.ResearchReport`，*不存在 `Source.Study`*], [成立],
  [实现条目的字段], [`types.py:96-116` 字段为 query／source／content；`source` 只是 LLM 写在标签里的文本，解析器不校验 URL], [部分成立],
  [两个 API 的签名], [`kapso.py:467-476`；`1129-1154`（含 `initial_repo`、`resume`）], [成立],
  [检索结果注入 prompt], [是，但为纯 `str()` 拼接（`kapso.py:1292-1307` → `handlers/generic.py:125-130` → `strategy.py:457`）；`context` 的 docstring 写 "learn before evolving" 而实现无 learn 步骤], [成立但弱],
  [知识检索是否自动], [*不成立*。`initial_repo` 为空时做一次 workflow repo 搜索（top_k=1），或挂 MCP gate 交由 agent 决定], [更正],
  [闭环的可运行入口], [`run_full_loop.py` 逐字含该闭环并有 "LOOP NOT CLOSED" 断言；但是 E2E 示例脚本（依赖 codex 与 claude CLI、本地 Weaviate 与 Neo4j），CLI 无 `learn_knowledge` 动词], [成立，非产品化],
  [固定 evaluator 的接入], [默认路径由 agent 生成评测目录；要让我们自己的评测驱动搜索，须走 `evaluation_maintainer` 路径（`orchestrator.py:579-616`；`maintainer.py:42-86`），把 eval_dir 改写成 `kapso_eval.py` 并打印 `KAPSO_EVAL_MANIFEST {...score}`], [成立，需改写入口],
  [外部评测回调的作用], [`iteration_evaluator`：*不影响搜索选择、停止、父代与最终分支*（S67 逐字）], [更正],
  [预算／续跑／记录／记忆], [`budget.py`、`run_checkpoint.py`、`experiment_memory`、`learning/` 与 `knowledge_base/` 均在], [成立],
  [外部工件边界], [`Source.Repo` 只有 `(url, branch)`；摄取克隆是 `git clone --depth 1 -b`，seed 克隆是 `clone_from(url, temp_dir)`（连 branch 都不传）；外部仓库*无 commit 固定、无内容哈希、无 license 字段、无可执行性验证*], [缺口],
  [research → 仓库解析], [*不存在任何路径*。研究产物只经 idea／implementation／report 三类摄入器（Planner 页型限定为 Principle／Implementation／Environment／Heuristic，不产 URL、不 clone）；`Source.Repo` 唯一运行期构造点是命令行参数（`knowledge_learner_pipeline.py:399`）；`workflow_search.py` 消费的是 KG 中由*已摄取仓库*生成的 Workflow 页], [缺口：完全人工],
  [论文声称与代码], [论文 §4.2 声称 commit metadata、`RepoStore`、corpus manifest（含 commit identifiers）与阈值 τ；代码只有 URL 级 provenance 与分支／时间戳], [论文超出代码],
)

*五项缺口（Rev. 4 更正）*：Rev. 3 说"缺口只集中在四项边界的补齐"，与我自己的 §4.2 证据（external metrics 不影响选择、闭环只是依赖闭源 CLI 与 Neo4j／Weaviate 的脚本）自相矛盾。真正的 KAPSO P2 是*五项*：

```text
1 commit 固定        2 内容哈希        3 license 记录        4 V_E 可执行性验证
5 外部评测信号进入搜索选择（默认不经此路径，需替换排序 / 自定义父代选择）
```

其中第 1 项还要求把仓库先自行 checkout 再以本地路径传入（URL + commit 不被支持）。而第 5 项属*搜索策略层接管*，不是字段补丁。

```text
真正的缺口不是"缺 Search", 而是缺:
Problem -> Search -> ResearchFinding -> ResolvedArtifact -> VerifiedArtifact -> Runtime
其中 ResearchFinding -> ResolvedArtifact 目前完全人工
```

== 4.3 EvE：与本项目需求贴合度最高的货架候选（Rev. 4 新增）

#table(
  columns: (2.7cm, 1fr, 2.1cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [仓库与论文], [`scaling-group/eve`，Apache-2.0，release v0.2.0，59 star；论文 arXiv:2605.09018v4，题名 *Evolving Ensemble of Agents*，作者 Zongmin Yu 与 Liu Yang], [存在],
  [分发与依赖], [无 PyPI 包（`pip install eve` 装到无关项目），走 `uv sync`；默认 testbed 不需 GPU，仅 ICON 示例需 2×GPU；需 Codex CLI 与登录态], [源码安装],
  [commit 契约], [`github_url` 与 `commit` 必须成对，缺失即 `ValueError`（`problem/repo.py:56-57`）；`repo.py:167-179` 解析后 `git archive` 造快照，该快照即 boundary 基线。*属代码级契约，论文正文无此约定*], [成立],
  [编辑边界检查], [`editable.files`／`folders` 为一等配置且不可同时为空（`repo.py:110-111`）；检查器在 `workflow/boundary.py:104-131, 152-200, 212-223`，越界以退出码 1 拒绝并取 `boundary_failure_score`], [成立],
  [外部分数驱动选择], [`subprocess.Popen(["bash", step], cwd=..., env={EVE_SOLVER_ROOT: ...})`（`evaluation.py:306-314`），分数从 `$EVE_EVAL_LOG_ROOT/score.yaml` 读回（`:918-935`）；`phase2.py:544` 写入种群、`:597-606` 按 `entry.score` 采样], [成立],
  [共同进化], [`workflow/loop.py:26-27` 自述 "Explicit co-evolution loop"；solver 与 guidance 两种群互相采样（`phase2.py:553-584`），guidance 侧由 Elo 更新（`phase3.py:47-56, 71-80`）], [成立],
  [阶段对照], [README 与论文有 Static-Initial／Static-Final 对照；仓库无对应开关，只能用 `produce_optimizer_in_phase2=0` 近似], [部分成立],
  [预算与停止], [`loop.max_iterations` 可用；`engine.py:224-241` 的 `StopConditions`（wallclock／token／cost）*全仓库无实例化*，即未接线], [部分成立],
  [最小 smoke], [`uv run python -m scaling_evolve.algorithms.eve.runner --config-name=circle_packing.smoke`；纯 CPU、sqlite、无 docker／Postgres／Redis], [成立],
)

*对计划的意义*：EvE 把 $A_t$（solver／repository 状态）与 $H_t$（agent guidance）放在*同一个*共同进化环里（§4.1 的 multi-timescale 视图中的两条轴），这与计划:235-239 的固定偏序形成直接对照（D9）。它的 `(github_url, commit)` 契约也正好是计划 §5.2 `ExternalInspiration` 里 `source.commit` 字段所要求的语义——即*计划的一个关键字段，在货架上已经有实现*。

= 五、建议与判据

== 5.1 结论

*先 Stage A，再 Stage B；在 Stage A 结果出来之前不写任何 adapter。* 理由：（a）H1 的识别设计尚未就绪（D11、D12）；（b）新颖度需要按三层重写（§4.1）；（c）而在写新代码之前，必须先量出现成 runtime 离目标有多远。*要避免的代理谬误已经换过一次位置*：不再是 ADA／OPL，也不是"围绕 ShinkaEvolve 建系统"，而是"预设某个候选最合适"。

== 5.2 Stage A：Runtime Shootout（只测 evolution substrate）

给三套系统*完全相同*的输入：

```text
(repo@commit, evaluator, budget, objective)
候选: KAPSO / EvE / Loreley
```

回答：*哪个现成 runtime 最适合真实 repository-scale 的算法改进？* 这里*不应*先补 KAPSO 的 provenance——仓库已由我们冻结后喂给三者。

*语义前提（必须写进协议）*：三方对比要求"同一个 evaluator 必须真正驱动选择"。只有 EvE 与 Loreley 天然如此；KAPSO 默认不是（S67），必须走 `evaluation_maintainer` 路径（把 eval_dir 改写成 `kapso_eval.py`、按 `--fidelity/--fraction/--seed` 调用、打印 `KAPSO_EVAL_MANIFEST {...score}`）。否则 KAPSO 臂答不了计划的核心问题。

#table(
  columns: (2.1cm, 1fr, 1.7cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*接入改造量与依赖*], [*量级*],
  [EvE], [`uv sync` + Codex 登录；写 4 个 yaml 与 1 个 `evaluation.sh`（脚本写 `$EVE_EVAL_LOG_ROOT/score.yaml`）；CPU + sqlite；commit 与 editable 边界开箱即用；注意 `StopConditions` 未接线，预算只能靠 `max_iterations` 与 driver 超时], [配置即可],
  [KAPSO], [`pip install leeroo-kapso` + Node≥18 + codex 与 claude 两个 CLI；需走 `evaluation_maintainer` 才能让外部分数影响选择；commit 锁只能自行 checkout 后传本地路径；docker 仅用于 KG，无 Postgres／Redis／GPU], [配置 + 适配脚本，必要时改写评测入口],
  [Loreley], [`docker compose` 起 Postgres 与 Redis + 写 evaluator plugin（`WORKER_EVALUATOR_PLUGIN=module:attr`，返回 `EvalPass(metrics)`）+ worktree + Kilocode 或其它 backend；候选仓库是 submodule，需 `--recurse-submodules`；示例路径用 codex_cli 与 local-hash，不需 embedding 端点], [写插件 + 全套运维，最高],
)

*记录项*（不比较算法分数）：`(C_setup, C_adapt, C_eval, C_provenance, C_maintenance)` 与 `FailureStage`。*Stage A 的判据*：外部分数是否真的改变了选择（用一次刻意构造的"分数与真实质量相反"的评测来验），以及是否能在单机跑完一个最小 campaign。

== 5.3 Stage B：Open-World Augmentation（在胜出 runtime 上加开放世界）

固定 Stage A 胜出的 runtime，增加：

```text
Problem -> Search -> Resolve -> Verify -> ExternalArtifact -> Runtime
对比:  ClosedRuntime  vs  OpenWorld + SameRuntime
```

*这样做的关键好处*：*open-world 效应与 runtime 效应解耦*。Rev. 3 的 P1／P2／P3 阶梯同时改变 runtime 与 acquisition／provenance，虽然失败位置有工程意义，却难以判断该选哪个 substrate。

```text
OurOwnedCode 缩小到可能只有一个边界:
ExternalWorld --phi--> VerifiedArtifact(source, commit, snapshot, license, mechanism, V_D, V_E)
VerifiedArtifact --seed/inspiration--> ExistingEvolutionRuntime
```

若 Stage A 显示 EvE 已解决"`repo@commit` + 外部 evaluator + 进化"，而 KAPSO 已解决"web research + knowledge"，则我们的定制部分可能只剩：

```text
Resolution + Verification + BridgePolicy
```

这比 Rev. 3 的"KAPSO extension"更保持架构中立，也正是计划"架构可丢弃"原则的彻底应用。

== 5.4 五项必改（在 Stage B 之前、进 H1 之前）

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（需 `use_text_feedback = true`）+ `metadata` 三分；写明三条限定；`text_feedback` 定位为 MVP 捷径。],
  [*分离两套统计设计*（D3 + D11 + D12）：`statistics.gate` 与 `statistics.campaign` 两组字段；分析单位是 `(task, run)`；配对按 event-keyed 随机源实现，不可控源按 `(task, run)` 冻结；预算为 r 留乘数。],
  [*按 $C times X$ 析因重写 §8.2*（D2）：5 臂（C+X／C／X／空 + shuffled explanation），主估计量 $Delta_X$；明文写出潜伏机制迁移不在可识别范围内；把 S82 的"简单基线"作为首要对照。],
  [*获取链写全*（D10 + D13）：`Search → Resolve → Verify → ExternalArtifact`，其中 Resolve 与 Verify 是能力而非字段；明确 $V_D$ 不等于 $V_E$；参考 EvE 的 `(github_url, commit)` 契约与 KAPSO 的五项缺口。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$ 与 $M_"research"$ 分开，proxy guard 约束成本/能力比；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

== 5.5 建议改

+ 把 `search_failed` / `resolve_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12（D6、D13）。
+ 给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离（D6）。
+ 按 §4.1 的三层判断重写新颖度表述，并补 §4.1 表内清单的参考文献（D7）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.6 Go / No-Go 判据

*进 Stage B 的门槛*：Stage A 已完成且失败位置已记录；胜出 runtime 的"外部分数真的驱动选择"已验证。

*进 H1 A/B 的门槛*：run 级配对的 `(Open_{t,r}, Closed_{t,r})` 表与 event-keyed 随机源清单存在；预注册的单一主终点与 MDE；与 Open 条件 token 匹配的负对照；confirmation 使用不相交且未事后挑选的事件键集合；外部搜索／解析／验证／适配的开销全部计入 open 臂。

*在满足上述前提后*：若 $Delta$ 不显著，必须同时报告*搜索失败率*、*解析失败率*与*机制抽取失败率*，以区分"没找到候选"、"找到了但解析不出可运行工件"、"没读懂仓库"、"机制不可迁移"。计划现有判据（计划:1076）无法区分，这是最需要修补的单点。

== 5.7 什么会使我改变判断

+ 若 Stage A 显示某个 runtime 即配置即可满足需求 → 本报告 §5.3 的自建部分应删除，计划改写为"该 runtime 的扩展"。
+ 若作者指出一条五轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级。
+ 若 Man1Lab 或其它组件在后续版本实现了"问题 → 候选仓库"的搜索 → D10 的该部分撤回（需附版本与调用点）。
+ 若 §4.1 清单中某条被证明与计划的差异主张无关，或又出现新的最近邻工作 → 相应收窄或补充（详见 D13 的完整性声明）。

= 六、我撤回或修正的判断

*Rev. 0 内部已修正*：公式越界范围（只有 1 处越页）；灵感槽位数（4/2 与 1/1 需分配置）；SGM 的"唯一提供物"。

*Rev. 1 阶段*

#enum(
  [*D1 的补救措施*：`Program.text_feedback` 已是现成通道，不必改核心。],
  [*archive 不变量*：仅默认路径要求 `correct=1` 且已入 archive。],
  [*AgentCo-Op 的能力*：只产出 dry-run 命令规格。],
  [*Experiment Record 的同一性*：Task Contract 18/19 行相同，Experiment Record 同源而异。],
  [*ARI 计划的日期*：mtime 为 09-18 14:32。],
  [*样本量建议*：$n>=20$ 无依据，改为公式化程序。],
  [*proxy drift*：修正为"治理缺陷已确认"。],
  [*许可传染*：按 AGPL §2 的条件式表述重写。],
  [*引用行号*：`license` 三处应为 533、626、1046。],
)

*Rev. 2 阶段*

#enum(
  [*cross 与反馈的相邻性*：partner 的反馈不出现在 dedicated crossover block 中，但在 eval history 中与其自身 code 相邻；其 code 出现两次。],
  [*`text_feedback` 的定位*：MVP 捷径，非长期 canonical schema。],
  [*D10 的定级*：关键集成缺口。],
  [*D2 的实验设计*：改为析因设计。],
  [*D3 的适用范围*：功效表只对候选提交门有效。],
  [*D4 的修补方案*：改为两类里程碑。],
  [*§4 的新颖度结论*："尚未被占位"是错的。],
  [*最终结论*：改为 Probe-0。],
)

*Rev. 3 阶段*

#enum(
  [*KAPSO 在 §4 表内的行*：源码不支持"research 返回候选仓库作 seeds"，已降级为论文口径。],
  [*KAPSO 的 KG 自动检索*：改为"MCP 工具交由 agent 自行调用"。],
  [*`iteration_evaluator` 的作用*：observational，不参与选择。],
  [*KAPSO 的 provenance*：论文声称 commit metadata 与 `RepoStore`，代码只有 URL 级 provenance。],
  [*配对条件*：改为 event-keyed 随机源。],
  [*D11 的措辞*："不可识别"过强；删除 $r >= 12$。],
  [*D2 的命名*：$E times M$ 改为 $C times X$。],
  [*§4 的层次判断*：改为三层判断。],
  [*Probe-0 的实现选择*：改为四台阶 shootout。],
  [*CRN 的引文*：改用可核表述。],
)

*Rev. 4 阶段*

#enum(
  [*"Loreley 是唯一 repository-native 候选"*：*撤回*。EvE 同样原生以仓库为工作对象，且在 commit 契约与外部分数驱动选择两项上更强（D13）。],
  [*KAPSO 的 P2 估计*：Rev. 3 说"缺口只集中在四项边界的补齐"与我自己的 §4.2 证据自相矛盾，更正为*五项*（含"外部分数进入搜索选择"），并补上 `ResearchFinding -> ResolvedArtifact` 这一完全人工的环节。],
  [*KAPSO 的"两条路径"*：与仓库解析脱节的是 idea／implementation／research report *三类*产物；不存在 `Source.Study`。],
  [*Loreley 的版本与依赖*：0.7.6a0 已过时，HEAD 为 v0.9.0-alpha；"需 Kilocode 与 embedding 端点"应限定为默认配置，示例路径用 codex_cli 与 local-hash。],
  [*§0.1 的"6 系统"*：与实际所列不符，且本轮二次查漏又增补候选；"已穷尽"断言已明确放弃。],
  [*EvE 的题名与依赖*：题名为 *Evolving Ensemble of Agents*；无 PyPI 包；默认不需 GPU。],
)

另有三项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属；KAPSO 论文所述独立知识包是否真含 commit identifiers；§4.1 清单之外是否还有非 arXiv 口径的最近邻工作（CORAL、EvoX Genesis 等目前仅核到元数据／摘要级）。

= 附录 A：审查覆盖范围

五轮共 41 个独立审查轴。Rev. 0（20）：五个核心系统源码级核实；Gödel machine 谱系；harness 谱系；统计与实验设计；内部一致性与可行性；与 ADA／OPL／ARI 的一致性；与 adapdc 系列的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；Typst 构建与排版实测；两轮专项反证；引用元数据三轮核实。Rev. 1（6）：`text_feedback` 通道与 inspiration 过滤不变量；Man1Lab 搜索能力；AgentCo-Op 的 repo 执行能力；目录层治理事实；许可表述精度；样本量程序的统计陷阱。Rev. 2（6）：cross 模式 prompt 逐行核对；TurboEvolve／Loreley／EES 逐篇核实；穷尽式最近邻检索；experimental unit 错位的方法学核实。Rev. 3（5）：KAPSO 的公开 API 面与闭环；KAPSO 的 provenance 与外层边界；common random numbers 与 event-keyed randomness；货架候选横向普选；决策策略层的占位情况。Rev. 4（4）：EvE 的完整断言核实；KAPSO 的 research → repository resolution 缺口；货架候选二次查漏；Stage A 三方可接入性。

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
- [S35] 货架系统对比（源码实测）：KAPSO、EvE、Loreley、OpenEvolve、ShinkaEvolve、ASI-Evolve 的许可证／安装／evaluator 接入／初始仓库／budget／provenance 对照。*Rev. 4 更正*：本清单在 Rev. 3 中只列 5 个系统且漏 EvE；"已穷尽"断言已放弃
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`；`inspirations.py:57-128, 143-242, 342-353`；`core/config.py:62`
- [S39] Man1Lab 搜索能力（快照 `5376e58d`）— `src/providers/github/client.py:43, 48, 61`；`collection.py:1, 46, 56-58, 88, 124-153`；`verification.py:1, 47`；`docs/reviews/1.2_github_collection_provider/audit.md:49, 55, 171, 182`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
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
- [S52] Bouthillier et al., MLSys 2021 — arXiv:2103.03098（附录 C.2：A 与 B 复用同一 seed）
- [S53] Hemming et al., BMC Med Res Methodol 11:102, 2011 — doi:10.1186/1471-2288-11-102
- [S54] Saravanan, Berman & Sober, hierarchical bootstrap — bioRxiv doi:10.1101/819334

*最近邻工作*

- [S55] TurboEvolve — arXiv:2604.18607
- [S56] Loreley — arXiv:2608.19703（Apache-2.0，HEAD `4c375920`，发布说明 v0.9.0-alpha）
- [S57] Kernel Foundry — arXiv:2605.30359
- [S58] TuneNNGen — arXiv:2607.05704
- [S59] KAPSO 论文 — arXiv:2601.21526
- [S60] AutoSOTA — arXiv:2604.05550
- [S61] MLE-STAR — arXiv:2506.15692
- [S62] MARCO — arXiv:2505.03906
- [S63] DeepEvolve — arXiv:2510.06056
- [S64] EES — arXiv:2609.17590

*Rev. 3 新增*

- [S65] KAPSO 仓库 — https://github.com/Leeroo-AI/kapso （MIT；PyPI `leeroo-kapso` 0.4.7；快照 `7d99b152`）
- [S66] KAPSO 源码路径 — `src/kapso/kapso.py:434-465, 467-476, 1129-1154, 1292-1307, 1745-1753, 1763, 1781, 1791-1825`；`researcher/researcher.py:75-139, 141-153, 189-192`；`knowledge_base/types.py:47-59, 96-116, 141-183`；`repo_ingestor/utils.py:18-76`；`environment/handlers/generic.py:125-130`；`execution/search_strategies/generic/strategy.py:396-400, 457`；`examples/ml_model_development/run_full_loop.py`
- [S67] KAPSO 外部评测文档 — `docs/evolve/external-evaluation.mdx:13-16, 80-95`（external metrics 不影响选择）
- [S68] Botev & Ridder, *Variance reduction*, Wiley StatsRef 2017 — doi:10.1002/9781118445112.stat07975
- [S69] L'Ecuyer et al., Operations Research 50(6):1073, 2002
- [S70] Salmon et al., *Parallel random numbers: as easy as 1, 2, 3*, SC'11
- [S71] Buffalo, Pearson & Klein, arXiv:2603.11084（stat.ME）
- [S72] OpenAI OpenAPI 对 `seed` 的说明（"Determinism is not guaranteed…`system_fingerprint`"）
- [S73] Loreley 运行约束 — `preflight.py:751-755` 强制 `WORKER_EVALUATOR_PLUGIN`；`env.example:321` 的根提交；需 Postgres 与 Redis（示例路径用 codex_cli 与 local-hash）
- [S74] "何时检索"轴 — Self-RAG arXiv:2310.11511；Search-R1 arXiv:2503.09516；SEM arXiv:2505.07903
- [S75] "何时选算子"轴 — AEL arXiv:2604.21725；SciToolAgent-Evo arXiv:2607.28692；GAE arXiv:2607.10127；TOPOFE arXiv:2607.23286

*Rev. 4 新增*

- [S76] EvE — https://github.com/scaling-group/eve ；arXiv:2605.09018，题名 *Evolving Ensemble of Agents*（Zongmin Yu, Liu Yang；v4 2026-08-17）；Apache-2.0，快照 `979065fd`
- [S77] EvE 源码路径 — `src/scaling_evolve/algorithms/eve/problem/repo.py:46-58, 110-111, 167-179`；`workflow/boundary.py:104-131, 152-200, 212-223`；`workflow/evaluation.py:295-314, 630-631, 634-670, 918-935`；`workflow/loop.py:26-27`；`workflow/phase2.py:544, 553-584, 597-606`；`workflow/phase3.py:47-80`；`core/engine.py:224-241`（`StopConditions` 无实例化）；`configs/eve/circle_packing.smoke.yaml`
- [S78] KAPSO 的 research → repository 缺口路径 — `knowledge_base/types.py:141-183`；`research_ingestor/implementation_ingestor.py:17-18`；`research_ingestor/prompts/planning.md:39-42`；`knowledge_base/learners/knowledge_learner_pipeline.py:399`；`knowledge_base/search/workflow_search.py:147, 157, 204-225`；`kapso.py:1791-1815`；`repo_ingestor/utils.py:41, 56`
- [S79] KAPSO 让外部分数影响选择的唯一路径 — `execution/orchestrator.py:579-616`；`evaluation_maintainer/maintainer.py:42-86`；`search_strategies/generic/strategy.py:1117-1135`；`config.yaml:123-183`
- [S80] CORAL — arXiv:2604.01658（https://github.com/Human-Agent-Society/CORAL ，Apache-2.0）
- [S81] EvoX Genesis — arXiv:2608.10450（https://github.com/EMI-Group/genesis ，AGPL-3.0）
- [S82] *Simple Baselines are Competitive with Code Evolution* — arXiv:2602.16805（反面证据，应纳入 §4.1 与 §8 的对照设计）
- [S83] 其余候选 — EvoGit arXiv:2506.02049；MappingEvolve arXiv:2604.26591；Live-SWE-agent arXiv:2511.13646；ParEVO arXiv:2603.02510
- [S84] Stage A 接入点对照 — EvE：`evaluation.steps` 指 shell 脚本并写 `$EVE_EVAL_LOG_ROOT/score.yaml`；Loreley：`WORKER_EVALUATOR_PLUGIN` 返回 `EvalPass(metrics)`、`MAPELITES_EXPERIMENT_ROOT_COMMIT`；KAPSO：`initial_repo` 与 `eval_dir`／`evaluation_maintainer`
- [S85] 闭源 CLI 依赖 — KAPSO 需 codex 与 claude；EvE 需 Codex CLI 并登录；Loreley 默认 Kilocode（示例路径 codex_cli）

*同目录文档*

- [S36] `algorithm_research_infrastructure_plan.typ`、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
