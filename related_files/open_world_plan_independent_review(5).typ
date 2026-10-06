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
  #text(size: 9.5pt)[本报告版本：*Rev. 5*（2026-09-20）· 五轮外部复审的核验记录]
  #v(2pt)
  #text(size: 9.5pt)[结论：*Go to A0——先做评测一致性与管线验证，不直接进入 Runtime Shootout*]
  #v(2pt)
  #text(size: 9.5pt)[阅读提示：*§5 是操作性部分（实验协议），§0.5–0.6、§2、§6 是审计记录*]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 5 总评*：本轮的性质从"文献查漏"转为"实验协议修正"，并且产生了一条对我自己的事实更正。

  #v(3pt)

  + *D16（我错了）*：我在 §4.2 把"外部评测信号进入搜索选择"列为 KAPSO 的第五项缺口，并说"需替换排序／自定义父代选择"。事实是 KAPSO 已存在该机制：registered evaluation 路径把 evaluator manifest 的分数直接写成 `node.score`，而 `node.score` 驱动父代选择、best／deliverable 与 expansion lane。正确说法是"*非默认*，需配置块与适配脚本，且需评测器冻结治理"。
  + *D14（成立）*：Rev. 4 的 Stage A 声明要回答"哪个 runtime 最适合算法改进"，却规定"不比较算法分数"——它只能回答"哪个最容易接入"。须拆成 A0（评测一致性与管线）与 A1（runtime 效用），后者必须包含简单基线。
  + *D15（成立，且比预想更严重）*：Closed 臂未必封闭。三套系统里*只有 EvE 的 `codex_tmux` 能靠配置做到*封闭；KAPSO 的 Bash 侧门配置关不掉；Loreley 默认路径必须外部断网或改用 codex 后端。
  + *两条会直接毁掉实验的隐患*（本轮新增证据）：KAPSO 在 `fidelity` 开启时会让 LLM judge 的分数顶替机读分数*并被打上错误的可比类标签*；EvE 把评测崩溃静默映射为 0 分，与真实 0 分不可区分。故必须先做 Evaluator Conformance Test，且它有三条硬约束。

  #v(3pt)

  结论：*Go to A0*。文献调查到此为止，下一步是"能不能跑通且测得准"，而不是"哪个框架更好"。
]

= 零、审查方式与限度

== 0.1 方法

本报告由六轮构成。Rev. 0 为全文精读 + 20 个并行独立审查轴。Rev. 1 至 Rev. 4 分别为对前四轮复审意见的独立核验（+6／+6／+5／+4 轴）。Rev. 5 为对第五轮复审意见的独立核验（+5 轴：KAPSO 的 registered evaluation 路径是否驱动搜索、三套系统的评测器冻结通路、三套系统能否跑在信息封闭条件下、三套系统的成本记账口径、评测一致性测试的可行性）。

六轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。每轮都产生了对本报告自身判断的更正（见 §6）。本轮产生了一条实质的事实更正（D16）。

*范围声明*：文献调查在 Rev. 4 终止；Rev. 5 只做实验协议修正。§5 是操作性部分。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行。
- 源码核实基于 2026-09-20 的公开快照，逐系统标注 HEAD：KAPSO `7d99b152`、EvE `979065fd`、Loreley `4c375920`、ShinkaEvolve `9912af12`、Man1Lab `5376e58d`、AgentCo-Op `94c37504`。
- *货架候选的"已穷尽"断言已在 Rev. 4 明确放弃*：检索口径限于 arXiv 与公开 GitHub 仓库。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S93）见附录 B。第三方源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → 5）

*Rev. 1 阶段（对第一轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R1　D1 补救措施], [注入机制文本"必须自定义 `PromptSampler`"], [*不成立*。存在现成的 per-inspiration 文本通道], [已改为三者映射],
  [R2　D2 定级], ["致命"（无法归因）], [*部分成立*], [降为"重要"，区分 H_U 与 H_M],
  [R3　获取前端], [未指出], [*成立*。Man1Lab 无搜索路径], [新增 D10],
  [R4　AgentCo-Op 能力], [`sandbox_repo` 为"真实 backend"], [*过强*。只产出 dry-run 规格], [已改写],
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
  [R11　cross 与反馈的相邻性], ["不与代码相邻"], [*错*。与其自身 code 相邻；code 出现两次], [已更正],
  [R12　`text_feedback` 定位], [长期 canonical schema], [*部分成立*], [改为 MVP 捷径],
  [R13　D10 定级], ["第一跳没有实现路径"], [*过强*], [降为"关键集成缺口"],
  [R14　D2 的实验设计], [六臂设计], [*不足*。不能识别机制迁移], [改为析因设计],
  [R15　D3 适用范围], [功效表外推为整个设计], [*错*（部分）], [已加限定，新增 D11],
  [R16　D4 的修补], [每个 Phase 都要 $Delta$ score], [*自相矛盾*], [改为两类里程碑],
  [R17　§4 新颖度], ["尚未被占位"], [*错*], [已重写清单],
  [R18　结论含义], ["修必改后进窄切片"], [*不够*], [改为 Probe-0],
)

*Rev. 3 阶段（对第三轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R19　KAPSO 的地位], [仅作为清单中的一条], [*应提升*], [新增 §4.2],
  [R20　KAPSO 的 KG 自动检索], [evolve 会自动检索并注入], [*不成立*。MCP 工具交由 agent 自行调用], [已注明],
  [R21　`iteration_evaluator` 的角色], [可把外部分数驱动进化], [*不成立*。该 API 是观测性的], [已更正],
  [R22　KAPSO 的 provenance], [保存 URL/commit provenance], [*部分成立*。论文声称 commit metadata，代码只有 URL 级], [已按两栏列出],
  [R23　§4 的 KAPSO 行], [`research` 返回 candidate repositories], [*源码不支持*], [已降级为论文口径],
  [R24　配对条件], [共享同一 seed 即配对], [*不成立*], [新增 D12],
  [R25　D2 的 estimand 命名], [$E times M$], [*概念不严谨*], [改名为 $C times X$],
  [R26　§4 的层次判断], ["运行时闭环已被占据"], [*过粗*], [已重写为三层判断],
)

*Rev. 4 阶段（对第四轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R27　货架普选漏项], [漏了 EvE，Loreley"唯一 repository-native"不成立], [*成立*], [新增 D13；EvE 与 KAPSO 并列一级候选],
  [R28　KAPSO 的 P2 成本], [缺口不止四项 provenance 字段], [*成立，且更严重*], [§4.2 与 §5.2 一并改写],
  [R29　shootout 结构], [拆成 Stage A 与 Stage B], [*接受*], [§5.2 重写为两阶段],
  [R30　EvE 的论文题名], ["Evolutionary Ensemble of Agents"], [*错*。实为 *Evolving Ensemble of Agents*], [已按实际题名引用],
  [R31　EvE 的依赖与分发], [（未主张）], [*需更正*：无 PyPI 包；默认不需 GPU], [已在 §4.3 写明],
  [R32　KAPSO 的"两条路径"], [ImplementationText 与 Source.Repo 互不相通], [*部分成立*。脱节的是三类产物；不存在 `Source.Study`], [已按三类产物改写],
  [R33　Loreley 的版本与依赖], [0.7.6a0 与"需 Kilocode + embedding 端点"], [*过时／过宽*。HEAD 为 v0.9.0-alpha], [已更正],
  [R34　§0.1 的"6 系统"计数], [（我自己写的）], [与实际所列不符；二次查漏又有增补], [已改为"候选清单 + 放弃穷尽断言"],
)

*Rev. 5 阶段（对第五轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R35　Stage A 的设计], [它其实不是 runtime shootout，只回答"哪个最容易接入"], [*成立*。Rev. 4 自己写明"不比较算法分数"，与它声称回答的问题不符], [拆为 A0 与 A1，见 D14],
  [R36　预算的定义], ["相同 budget"未定义，迭代数不可比，应用资源向量 + anytime 曲线], [*成立*，并核出三套系统的记账能力不对称], [已定义资源向量与硬约束，见 D14],
  [R37　Stage B 的污染], [Closed 臂可能因 agent 自带联网而不封闭], [*成立，且比预想更严重*。三套系统里只有 EvE 的 `codex_tmux` 能靠配置封闭], [新增 D15，并把"封闭性验证"设为 B0 前置],
  [R38　H_A 与 H_O 的拆分], [先测 VerifiedArtifact 注入，再测完整开放世界], [*接受*。$H_A$ 是当前 H1 最干净的实验], [已写入实验链],
  [R39　KAPSO 的第五项缺口], [KAPSO 已有"固定外部 evaluator → search score"机制，我的"需替换排序"说法有误], [*成立，我错了*。见 D16：registered 路径确实把 manifest 分数写成 `node.score`], [§4.2 的第五项已重写],
  [R40　评测器冻结], [KAPSO 的 maintainer 允许 agent 请求改评测器，需 `max_change_requests=0` 并冻结 hash], [*成立*。默认上限 3；设 0 即关闭；接受变更后会对 frontier 做桥接复评], [已写入协议前置条件],
  [R41　评测一致性测试], [应加一个取固定候选集要求三套 wrapper 数值一致的测试], [*可行，但有三条硬约束*，且存在会假绿的陷阱], [已写入 A0 的验收条件],
  [R42　runtime 效用不应是单一 score], [应记录 attribution 等维度], [*接受*。$U$ 取五维：Gain／Cost／Reliability／Attribution／Operability], [已写入 A1 的记录项],
)

== 0.6 我保留的分歧

+ *"三套系统都能靠配置形成 Closed 臂"*：不成立。只有 EvE 的 `codex_tmux` 司机可以（`sandbox_mode: workspace-write` + `allow_network: false` + `web_search: disabled`）；KAPSO 的 Bash 侧门配置关不掉（无 lane 级 sandbox 参数，codex lane 落到 full-access，claude lane 用跳过权限模式），Loreley 默认路径无网络开关。反过来"都只能靠外部断网"也不成立——两者都需按系统分别处理（D15）。
+ *"简单基线也许已经够用"这一可能性*：我接受 S82 作为首要对照，但反对把它当作结论。S82 的三个域与我们的任务域不同；它确立的是*零假设的优先级*，不是零假设的成立。
+ *D13 中我写"EvE 与本项目需求贴合度最高"*：作为工程接口贴合度成立，作为 research substrate 不成立——它的 $A_t$ 与 $H_t$ 同时变化，与 $tau_A < tau_H$ 的归因前提冲突，因此必须记录 $C_"attribution"$（D14）。
+ *CRN 的逐字引文*：沿用 Rev. 4——无法确认"same random numbers must be used for the same random events"的出处，用 S68 的可核表述。
+ *决策策略层"已被某货架系统占位"*：未见任何货架系统把获取外部实现／适配／交叉／继续内部进化纳入同一学习策略（D5）。
+ *目录层证据的可移植性*：依赖本地目录状态，标注为"该证据集内不可独立复现"（自检命令见 §3.3）。
+ *TurboEvolve 的池"含人类编写的解"*：不成立（S55）。*EES 的 `external-source routes` 读作运行时取外部实现*：不成立（S64）。

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

第 3 步是承重点：*它假定两段都已有货架。* 六轮核验后这个假定比计划写的更成立，也比计划写的更危险：第一段的货架（KAPSO、EvE）比计划提到的任何组件都更接近目标（§4.2、§4.3），而计划选的组合（Man1Lab + ShinkaEvolve + AgentCo-Op）反而需要自己补上更多。第 2 步的顺序原则因此必须执行到"连 runtime 也不预先指定"。

== 1.2 我认可的部分

+ *目标层的重新收束是对的*：把"提高基础设施完整度"与"提高算法改进能力"分开。
+ *"架构可丢弃"作为硬约束*（计划:169）——Rev. 3／4 正是把它用在 ShinkaEvolve 上。
+ *多时间尺度分离*（计划:235-239）。*Rev. 5 补充*：EvE 选择把 solver 与 guidance 放在同一个共同进化环里（§4.3），说明联合调度已有可运行实现；计划若要保留固定偏序，需要更强理由，并在 A1 中记录 $C_"attribution"$。
+ *从第一天记录轨迹以备将来 replay*（计划:581）。
+ *不继承 Man1Lab 的生成策略*（计划:474）：其 `generation_decision.py` 逐字包含 "Do not redesign algorithms or network architecture."。
+ *把外部实现交给自有 evaluator 定生死*（与 ShinkaEvolve 的 `correct = 1`、EvE 的脚本分数、KAPSO 的 registered evaluation 一致）。
+ *任务选择的阶梯*（计划:998-1004）。
+ *外部事实的可核实性*：五轮外部复审独立复检后，计划点名的系统仍无一虚构。

= 二、我的怀疑

下面十六条按后果排序。*D10–D16 分别为 Rev. 1–5 新增，编号沿用以免破坏交叉引用。*

== D1（重要）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（清单见计划:529-536），而 `metadata` 对 prompt 不可见，故该决策按文中所述不成立。

*证据一：metadata 不可见（快照 9912af12）*

- `sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(...)` 与可选反馈段；cross 专属段 `prompts_cross.py:57-73` 只写 partner 的 `code` 与 `perf_str(...)`。
- prompt 路径上读 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支），不参与 mutation 与 cross。
- `metadata["patch_name"]` → 元总结器 → `meta_recommendations` → 追加到系统消息，但条件为 `patch_type != "cross"`，且经 LLM 摘要。
- 计划:529-536 的六个键在仓库中*零命中*。

*证据二：正确注入面现成*

- `prompts_base.py:58-79`：每个程序在同一块内依次为 `prog.code`（:61）、metrics（:63-67）、`Text feedback:` + `prog.text_feedback`（:74-79）；开关默认 `False`。
- `sampler.py:152-157` 把 archive 与 top-k 全部送入该函数；partner 的 code 在同一 message 中*出现两次*（`sampler.py:205-208`）；`CROSS_ITER_MSG` 的反馈段填的是 *parent* 的（`sampler.py:161-166`）。
- adapter 可自设该字段：`dbase.py:174`，`Database.add()` 原样落库，全仓库无 `UPDATE programs SET text_feedback`。

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 捷径，非长期 canonical schema）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*三条限定*：cross 对位段无此通道；该字段属评测器语义、单字段约束；重复评测会新建一行携带评测器值。

== D16（重要，Rev. 5 新增）我关于 KAPSO"第五项缺口"的判断是错的

*我原来的说法*：§4.2 与 Rev. 4 的 §5.2 把"外部评测信号进入搜索选择"列为 KAPSO 的第五项缺口，并写"需替换排序／自定义父代选择"。

*更正*：该说法*错误*。KAPSO 已存在该机制，只是非默认。

- registered evaluation 路径把 evaluator manifest 的分数*直接写成* `node.score`：`feedback_flow.py:76-93` 取 `manifest_of_record(node)`，`manifest_score = float(manifest_record["score"])`，随后 `node.score = manifest_score`（注释逐字 "the manifest is the score of record"）。
- `node.score` 确实驱动搜索：父代选择（`strategy.py:1373-1380` → `1420-1434`）、best 与 deliverable（`:1436-1477`）、expansion lane 代表（`expansion_lanes.py:111-127`）、evaluator 迁移时的桥接顺序（`orchestrator.py:755-762`）。*一项例外*：stagnation 与停止不由分数驱动，而由 judge 投票 ∧ `evaluation_valid` 决定（`feedback_flow.py:67, 106-108`）——这一点我原先说对了。
- 对比 `iteration_evaluator`：它只写 `candidate.metrics`／`primary_metric`／`external_evaluation_metadata`（`orchestrator.py:1063-1100`），*从不碰* `node.score`。故 S67 的"external metrics 不影响选择"对该 API 成立，对 registered 路径不成立。
- 开关：mode config 的 `evaluation_maintainer` 块（`orchestrator.py:576-616`），非默认（默认是 agent 自产评测，provenance 为 AGENT_GENERATED）；评测脚本须支持 `--fidelity／--fraction／--seed` 并打印 `KAPSO_EVAL_MANIFEST {...}`。

*因此五项缺口应改写为*：

```text
1 commit 固定   2 内容哈希   3 license 记录   4 V_E 可执行性验证
5 固定外部评测驱动搜索 -- 机制已存在，但非默认、需配置块与适配脚本、需评测器冻结治理
```

*冻结治理（新证据）*：`evaluation_change_request` 默认上限 3（`orchestrator.py:616`），设 0 即关闭该通路（`:874`）；一旦接受变更，E_t → E_t+1 并会对已有 frontier 做桥接复评（首个成功即停，其余旧分在新可比类下投影为 None，`orchestrator.py:751-806`）。KAPSO 也是三套系统里*唯一能证明"campaign 内评测器未变"*的：逐候选 `verify_evaluation_tree` 与 `verify_data_manifest`（`search_strategies/base.py:740-792`），resume 时校验工作区树与 registry head 一致，版本注册为 append-only 且每版一次 git commit。

== D14（重要，Rev. 5 新增）Stage A 不是 shootout；预算也未定义

*指控一*：Rev. 4 的 §5.2 声称 Stage A 回答"哪个现成 runtime 最适合真实 repository-scale 算法改进"，但同一节又规定"记录项（不比较算法分数）"。因此它最多回答"哪个 runtime 最容易接入"，不能回答"哪个最适合改进算法"。

*指控二*：`(repo@commit, evaluator, budget, objective)` 里的 "budget" 没有定义，而 `1 EvE iteration`、`1 KAPSO iteration`、`1 Loreley job` 三者不可比（EvE 一个 iteration 内有多个 solver／optimizer worker；Loreley 一个 job 内可有多轮重试）。

*必须拆成两步*：

```text
A0  Capability / Plumbing Smoke   只验证工程语义, 不比较算法价值
A1  Runtime Utility Probe         比较 verified gain per unit resource, 且必须含简单基线
```

*A0 的设计*：KAPSO／EvE／Loreley 都必须证明 `repo@commit → candidate → E(candidate) → score → selection`。不需要真实算法任务——构造两个已知候选 $c_1$、$c_2$ 使 $E(c_1) > E(c_2)$，检查三个 runtime 是否都确实偏向 $c_1$。这比"构造一个与真实质量相反的 evaluator"更干净，因为不引入第二套"真实质量"语义。

*A1 的设计*：通过 A0 的系统，在一个很小但真实的算法任务上比较*单位资源的已验证增益*，且必须包含简单基线：

```text
对照集: { SimpleIterativeAgent, KAPSO, EvE, Loreley }
```

否则会犯"在三个复杂系统里挑最好"的错误，而最优货架方案可能是"现成 CLI + evaluator + 简单循环"（S82）。*读法限定*：A1 是探针，不是假设检验。单任务、少数 run 只能分辨数量级差异；须预注册"不确定"这一结论，并按 D11 的分析单位报数。

*预算向量（替代迭代数）*：

```text
B = ( T_wall, N_modelCalls, N_tokens, N_evaluatorCalls, C_usd )
选一个作为硬约束（例如 C_usd 或 N_tokens），其余全部报告
比较 anytime 曲线:  Q(c) = max_{cost <= c} VerifiedScore
```

*记账能力不对称（本轮新证据，直接决定 A1 能否公平比较）*：

- *KAPSO*：`cost_budget` 的单位是*美元*（`budget.py:151-153`；文档逐字 "Best-effort spend budget in USD"），由 `BudgetLedger` 累加并落在 `.kapso/run_state.json`。*不记 token 与模型调用数*（claude adapter 内部有 token 字段，但只进 metadata、无落盘消费）。*致命细节*：codex adapter 自述无计费遥测，`get_cumulative_cost()` 恒为 0 —— 若用 codex，KAPSO 的美元口径直接失效。
- *EvE*：`ComputeUsage` 记 input／output／cache token、`model_cost_usd`、`evaluator_calls`、`evaluator_cpu_seconds`、wallclock、agent turns 与 tool calls，落在 sqlite 的 `nodes.budget_json` 与 `logs/optimize/token_usage.json`。但 `StopConditions` 与 `write_run_checkpoint` *从未被实例化或调用*（run 级预算既不累加也不落盘），实际可用约束是 `loop.max_iterations`、每会话 `timeout_seconds` 与 `rollout_max_turns`。
- *Loreley*：记的最全——`LLMUsageEvent` 含 input／cached／cache write／output／reasoning／total token、`cost_usd` 与 `cost_source`（provider_reported／catalog／estimated／unpriced／unavailable），并按 job 与 phase 归属。一个 job = 一条 `EvolutionJob` 行 = 一次进化迭代／一个候选（内部可有多轮重试），`SCHEDULER_MAX_TOTAL_JOBS` 统计全部 job 行。
- *评测调用计数*：KAPSO 仅在 registered 路径有（`evaluation_attempts`）；EvE 的 `evaluator_calls` 只对 agent-judge 评测置 1，shell-step 评测不写（loop 里的 `total_solver_evals` 只打日志、不落盘）；Loreley 的 `evaluation_attempts` 表用 `measurement_reused` 与 `measurement_executed` 区分"真跑"与"缓存复用"，是做 anytime 曲线时最正确的口径。

*记录项*：$U = ("Gain", "Cost", "Reliability", "Attribution", "Operability")$，其中 $C_"attribution"$ 专门记录"算法变异与 guidance／harness 变异同时发生"带来的归因难度（EvE 尤需）。

== D15（重要，Rev. 5 新增）Stage B 的对照臂可能根本不封闭

*指控*：Rev. 4 设计 `ClosedRuntime vs OpenWorld + SameRuntime`，但底层 coding agent 可能自带联网与外部工具，于是 `Closed` 臂并不封闭：

```text
ClosedRuntime --agent 自带 web--> ExternalKnowledge   =>  Closed 不属于 ClosedWorld
```

*证据（逐系统核实）*：

- *KAPSO*：驱动为 `claude_code`（默认）与 `codex`。可关的：codex 侧 `web_search`（默认 True）、`mcp_servers`；策略层的 ideation／implementation web 开关、`gates` 可摘掉 research、`knowledge_search.enabled: false`。*关不掉的*：没有 lane 级 sandbox 参数，codex lane 落到 `danger-full-access`，claude lane 用 `--dangerously-skip-permissions` 且不限制 allowedTools —— 两路都有 Bash，`curl` 即可联网。且 Researcher 路径写死 `web_search=True`（配置项被 `bool(web_search or spec.get("web_search"))` 压过），故 research 检索本身无法靠配置离线。
- *EvE*：`codex_tmux` 司机具备 `approval_policy`／`sandbox_mode`／`allow_network`／`web_search`（默认 disabled），*配置即可封闭*；`codex_exec` 硬编码 `--dangerously-bypass-approvals-and-sandbox`，不可；opencode 无 OS 沙箱。
- *Loreley*：无 web／network 配置项；默认 Kilocode 路径注入固定 config 并覆盖外部同名环境变量；唯一现成的硬封闭是改用 codex 后端（默认 workspace-write 且不传 `--search`）。
- *CLI 层面*：Codex CLI 的 `workspace-write` 默认 `network_access: false`（官方源码），故沙箱本身就是断网；claude CLI 有 `--disallowedTools`、`--strict-mcp-config`、`--restricted` 与 OS 级 Bash 沙箱可配。

*拆两个 estimand（接受复审方，且这是当前 H1 最干净的切法）*：

```text
H_A  External Artifact Value
     两臂都禁止自主外部获取; Open 臂只额外获得我们冻结好的 VerifiedArtifact
     Delta_A = Y(Runtime(repo, E, VerifiedArtifact)) - Y(Runtime(repo, E))
H_O  Open-World Research Value
     放开完整 Search -> Resolve -> Verify -> Adapt
     Delta_O = Y(Runtime_open) - Y(Runtime_closed)
顺序: H_A 先于 H_O -- 若连已知优质工件注入都无收益, 让 agent 自己花预算检索更没有理由
```

*因此 B0 之前必须加一步"封闭性验证"*：不能只在配置里关，必须用探测证明（例如给候选一个只有联网才能解的子任务，或监控进程出网）——即把"封闭"从假设变成经验事实。三套系统的达成方式不同：EvE 的 `codex_tmux` 配置即可，KAPSO 需外部断网或改码，Loreley 默认需断网或换后端。

== D12（重要）"同 seed"不等于配对：需要 event-keyed 随机源

+ common random numbers 的标准条件是"同一随机数用于*对应的用途/事件*"：S68 逐字为 "a specific random number used for a specific purpose in one configuration is used for exactly the same purpose in all other configurations"。
+ 状态式 PRNG 在干预改变控制流时会失同步：S71 的 §1 逐字指出 CRN 的隐含假设是 "the same position in the random PRNG draw sequence corresponds to the same modeled event … across coupled scenarios"；补救是 $U_e = g("seed", "event_id")$ 式键控抽样。
+ *限定*：ML 基准领域的成文做法恰是 A 与 B 复用同一 seed（S52 逐字）。正确表述是 *agentic 研究使该做法的前提失效*。
+ *R1*：抽样为纯函数 `g(seed, event_key)`，用 counter-based RNG，禁单条顺序流。
+ *R2*：按源分流——可控源（evaluator、task 划分、parent 选择、mutation 决策）跨条件键控共享；不可控源（闭源 LLM 采样、网络检索）按 `(task, run)` 冻结并在两条件间共用同一份快照。
+ *R3*：任一关键流不可控则该 estimand 禁用配对检验，改 run 级独立复制并分解 $sigma_"run"$ 与 $sigma_"seed"$。
+ *对照事实*：闭源 LLM 的 `seed` 不保证确定性（S72）。

== D11（重要）统计设计把 evaluator seed 当成了实验单位

```text
候选提交门  :  candidate × eval seeds    回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs   回答"开放世界的策略是否更好"
```

- 随机性至少三层 `Y_{t,r,s}`；seed 是观测单位而非实验单位（S48；S49 逐字 "Increasing the number of OUs does not increase the sample size"；S50 逐字 "the experimental unit is the number of subjects tested, rather than the number of observations made within each subject"）。
- 即使把同一 search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`，并未估计 `E[pi_open] - E[pi_closed]`。
- *分析程序*：先折叠 seed 层，再建 run 级模型 $d_{t,r} = mu + u_t + v_{t,r}$（S51），或分层 bootstrap（S54）；配对按 D12 实现；task 仅 3 个时只报 task 级效应。
- *r 的规划*：$r = f(sigma_"run", "MDE", alpha, beta, "design")$；pilot 只估 $sigma_"run"$ 并取上界；设计效应 $ "DE" = 1 + (m-1)rho $（S53）。
- *成本*：只加 seed 只作用于评测环节；重跑 campaign 把整个研究过程乘以 r。增加*变异源*比堆同一源更省（S52 报告约 51 倍计算节省）。

== D2（重要）H1 的两种读法需要分开；析因设计只能回答其中一个

```text
H_U :  OpenWorld         -> UtilityGain    第一阶段可直接检验
H_M :  MechanismTransfer -> UtilityGain    需要因果识别设计
```

```text
C = External Code      X = Explicit Mechanism Explanation
              X              not-X
C          C + X              C
not-C        X              （空）
对照：      C + X_matched  vs  C + X_shuffled      （token 匹配、同域但错配）
主估计量：  Delta_X = Y(C + X) - Y(C)
```

$Delta_X$ 回答：*给已经看到代码的 agent 再解释"为什么这个算法有效"，有没有额外价值？* 更宽意义上的潜伏机制迁移需要程序结构或行为层面的分析，*不在本设计可识别范围内*。

== D3（重要）候选提交门的统计设计：数值正确，适用范围必须限定

*限定*：Rev. 0/1 的功效表*只对候选提交门有效*。表本身经五轮独立复算无误。

#table(
  columns: (auto, auto, auto, auto, auto, auto),
  inset: 4pt,
  stroke: 0.4pt,
  [*n*], [*d=0.5*], [*d=0.75*], [*d=1.0*], [*d=1.5*], [*d=2.0*],
  [5], [0.141], [0.254], [0.401], [0.711], [0.909],
  [10], [0.293], [0.562], [0.803], [0.987], [1.000],
  [20], [0.565], [0.889], [0.989], [1.000], [1.000],
)

```text
n_gate = f(MDE, sigma_d, alpha, beta)
近似闭式: n ≈ (z_{1-alpha/2} + z_{1-beta})^2 · sigma_d^2 / MDE^2
精确解:    非中心 t，ncp = MDE·sqrt(n)/sigma_d，df = n-1，对 n 数值求根
           （闭式会低估: d_z=0.5、power=0.8 时给 31.4，精确值 34）
```

*其余要点*：$n=5$ 时最小可检测效应为 $1.68 sigma_d$；pilot 只估 $sigma$；$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$；三条件 Bonferroni 下 $n=5$、$d=1$ 功效降至 0.191；confirmation 与 pilot 若共用 seed 则 winner's curse 未消除，且按 D12 应冻结*事件键集合与检索快照*；§6.1 固定 per-test $alpha = 0.05$（计划:776）与 §6.2 自陈的 multiple testing 目标（计划:785）不相容；被推迟的 e-value／error spending（计划:806）正是"统计门"名称的实质内容；`time to first improvement`（计划:954）无删失规则与生存分析。

== D4（重要）护栏不可执行：两类里程碑与一致的治理

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
M_research   (研究期):     Delta verified algorithm capability
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化
```

*证据*：milestone 全文仅一次（计划:1242）；Phase 0/1 的交付按设计不产生算法能力增长；§12.1 与 §14.4 两套停止规则互不引用；无任何阶段要求"产出 verified improvement"（§8.3 把首版主验收定为"基础设施能否减少研究成本"，计划:1006）；全文唯一日期是版本号（计划:30）。治理部分见 §3.3。

== D5（重要）H2 没有实验臂；"决策策略层"的占位要分轴说

+ *检索一次后进化*：已占位（MLE-STAR，S61）。*检索与进化交替*：已占位（DeepEvolve S63、MARCO S62）。
+ *把获取/适配/交叉/内部进化作为策略分配*：*部分占位*。"何时检索"轴在 QA／RAG 域已被形式化（S74）；"何时选算子"轴被经典 AOS 与近期 LLM 进化调度占据（S75）。把*外部实现获取*与*内部进化*纳入同一策略、且 acquisition 对象带 provenance，未见明确占位。

```text
动作空间:  { ResearchExternal, RetrieveKnowledge, ContinueEvolution, RunExperiment, LearnExperience }
问题:      是否存在 pi(a_t | s_t, B_t) 使 Delta VerifiedPerformance / Cost 优于固定 pipeline
```

== D6（重要）未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（D10、D13），并把 `understand` 写成管道一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"上网找到他人已解出的高分方案"。旁证：EES 的厂商侧能力明列 web research 与 exploit discovery（S64）；MLE-bench 必须明文禁止查看网上解法并用 Dolos 与 top-50 公开 notebook 比对（S24）。*Rev. 5 补充*：这一条与 D15 同源——如果连 Closed 臂都不封闭，"开放世界"的对照就失去意义。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046），无决策规则。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 *License Provenance Gate*：来源与依赖清单、指纹与相似度比对（Copilot 比对窗口约 150 字符，官方承认空文件更易命中，S32）、许可白/黑名单与义务登记、命中的派生隔离与替换重写。旁证：TurboEvolve 把它列为未来建议（S55）、KAPSO 无 license 字段、EvE 的 `configs/` 与 `src/` 中 `license` 零命中。
+ *供应链*：计划:1217-1219 要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*` 并经加密 DNS 外传（S34）。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问（S33）。旁证：KAPSO 默认 seed 路径连 commit 都不固定（§4.2）。

== D10（重要）开放世界获取前端并不存在——但这是集成缺口

*证据（快照 `5376e58d` = main HEAD；PyPI 1.3.0 同源）*：

- `src/providers/github/client.py:61` 逐字：`raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`；全包无调用点。
- `GitHubCollectionProvider` 的输入是论文分析里已存在的 URL（`collection.py:1, 46, 56-58, 124-153`），无 query 参数；官方审计文档逐字 "No Search API"、"deterministic, Search-free"。
- 全包无其它发现路径；gap 派生的 `ResourceNeed` 只被生成、无 provider 消费。
- ADR-0016:161 把 conditional search 列入 Phase 1，实作停在无搜索的 1.2 → 1.3.0 状态。

*语义问题*：`verified` 被用于指 $V_D$（发现层可信）与 $V_E$（任务层可执行）两件事；Man1Lab 只提供 $V_D$（ADR-0016:142）。

*Rev. 4/5 的定级*：这是*关键集成缺口*。可借路线：KAPSO 的 knowledge 面（§4.2）、EvE 的 `(github_url, commit)` 契约（§4.3）、AutoSOTA（S60）、MLE-STAR（S61）。真正的缺口不是"缺 Search"，而是*缺 Search result → executable artifact 的 resolution*（§4.2）。

== D13（重要）货架候选查漏不完整，而漏掉的正是最贴合的那个

*证据（EvE 七项断言逐条核实，快照 `979065fd`）*：commit 契约（`problem/repo.py:56-57` 缺一即 `ValueError`；`repo.py:167-179` 解析后 `git archive` 造快照）；编辑边界（`repo.py:110-111`；`workflow/boundary.py:104-131, 152-200, 212-223`）；外部分数驱动选择（`evaluation.py:306-314` 执行、`:918-935` 读回、`phase2.py:544, 597-606` 采样）；共同进化（`loop.py:26-27`；`phase2.py:553-584`；`phase3.py:47-80`）；阶段对照（仅 README 与论文，仓库无开关）；可运行 smoke（`circle_packing.smoke`，纯 CPU）；`StopConditions` 未接线。

*完整性*：本报告的"货架候选已穷尽"断言*明确放弃*。二次查漏发现 CORAL（S80）、EvoX Genesis（S81）等；未覆盖类包括非 arXiv 正式论文集、闭源或仅 demo 的系统、论文无仓库的双向缺失项。

*另一条反向证据*：S82 用三域实验主张"简单基线在代码进化任务上已具竞争力"，已按 D14 写入 A1 的对照集与零假设。

== D7（次要但影响可复核性）引用卫生

正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名 17 个外部系统，其中 12 个无条目。FunSearch 全文 0 次出现（五轮独立核实为 0），MLE-bench、RE-Bench 亦 0 次。

== D8（次要）引文与命名漂移

#table(
  columns: (2.5cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*位置*], [*问题*],
  [计划:55、370], [`AHE / HarnessFix` 用斜杠并列，暗示为同一方法的别名；实为两个独立工作（S15 与 S16）。],
  [计划:575], [`ReplayWorld` 非原文术语，Dream-RSI 原文用 replay simulator（S7）。],
  [计划:275], [字段名实为 `correct` 而非 "correctness"（S3）。],
  [计划:214], [正式题名为 "Huxley-Gödel Machine"（带连字符），S9。],
  [计划:55、1415-1416], [`SGM/RQGM` 并为一组，但按计划自己的六坐标模型分属 Commit 层与 Evaluator challenge 层。],
  [计划:1142、1414], [MGM 的核心机制是 comparative evolution / 跨谱系杂交（S10）。],
  [计划:214], [MGM、RQGM、SE-GoS、MetaRSI、Dream-RSI 均为 2026 年 6–9 月的 preprint，却与 AlphaEvolve、DGM 并列成"已确立文献"。],
  [—], [`github.com/codelion/openevolve` 已改名并跳转（S20）。],
)

== D9（次要）内部张力

+ *时间尺度与 Phase 顺序不一致*：$tau_K <= tau_pi$ 要求先经验后策略（计划:236-239），但 §9 把 Bridge Policy 放在 Phase 3/5、Skill RSI 放在 Phase 6。
+ *与 MetaRSI、EvE 的路线冲突未解释*：两者都采用联合调度（S14；§4.3），计划的固定偏序需要更强理由。
+ *发现步骤的归属与验收缺失*：见 D10。
+ *Man1Lab 的接口性质被低估*：Decision Foundation 为非公开 API，Repository Adaptation 仍在 roadmap（S1、S39）。

= 三、我的证据

== 3.1 外部系统源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。Collection → Evidence → Verification → Ranking → Selection；六阶段；五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0，无论文。*两项能力断言不成立*：（1）无搜索路径（D10）；（2）其 `verified` 仅指 $V_D$。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive 均为真。Apache-2.0，arXiv:2509.19349。*但 `metadata` 不是灵感通道*（D1）；且只做单文件程序进化。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*；`NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约。*过强的一处*：`sandbox_repo` 只产出 dry-run 命令规格。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
  [ASI-Evolve], [*sampler 断言为真*。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline；且只做单程序进化。],
  [Dream-RSI], [*论文真实*；*代码尚未发布*，故计划:368 的"完整源码尚非稳定依赖"偏保守。许可无法确认。],
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

见 D3、D11、D12。非中心 $t$（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$），另以 $10^5$ 次蒙特卡洛验证，各轮外部复审的独立复算亦一致。

== 3.3 文档族物证

```text
ls -la *.typ
grep -n "seeds:" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
grep -nE "supersede|取代|废弃|作废|以本文为准" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
```

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版标注；该标注属待执行的"C0 本地落库动作"，旧版未加标注；Makefile 通配符把两者都编成 PDF。
- `algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml 19 行中 18 行逐字相同（含 seed 列表），Experiment Record 同源而异；两份 mtime 同为 09-18 14:32（被审计划 15:25）；互不引用，均无取代声明。
- 至少三套并存的统计提交门（ADA、OPL、本计划）。
- 该族另有引用不存在文件的情况（如 `adapdc_architecture_report.typ`、`research-foundations.md`）。
- *可移植性限度*：以上第 1、2、4 条依赖本地目录状态。

== 3.4 排版与构建实测

构建：`typst 0.15.1` 下 `typst compile` 退出码 0、无 warning，输出 20 页 A4。A4 页宽 595.276pt，页边距 68.031pt，正文右边界 527.245pt。方法：`pdftotext -bbox` 逐词取框 + 解压 PDF content stream 读取每个 text run 的笔位。

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

结论：6 处显示公式溢出页边距，其中仅 *1 处*（计划:951-962 的 `Y` 指标元组）真正越出纸张被裁切。

= 四、与先前工作的关系

== 4.1 新颖度的三层判断

+ *架构层*（把外部知识或外部实现接进进化循环）：*已大量占位*。
+ *检索一次后进化*（MLE-STAR，S61）；*检索与进化交替*（DeepEvolve S63、MARCO S62）：均已占位。
+ *决策策略层*（把获取/适配/交叉/内部进化当作策略分配）：*部分占位*（D5）。
+ *尚存的价值主张*：在进化 archive 内部、带 commit／license／hash provenance 的单条外部灵感的反事实归因——已被 TuneNNGen（S58）与 Kernel Foundry（S57）逼近。
+ *必须正视的反面证据*：S82（简单基线的竞争力）。

#table(
  columns: (2.6cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*工作*], [*占位*], [*依据*],
  [FunSearch 等三篇], [A（弱）], [冻结 evaluator + 程序库 + 检索高分实现进 prompt；初始程序由人给出（S18、S19、S20）],
  [TurboEvolve　2604.18607], [A], [`seed-pool injection`：既有解池聚类后分配到各 island 作种子；池来源是作者自跑 checkpoint（S55）],
  [Loreley　2608.19703], [A + B（负）], [以完整 git commit 为 evolutionary artifact、isolated worktrees、项目自带 evaluator、QD archive，并显式区分 parent 边与 inspiration 边（S56）],
  [EvE　2605.09018], [A + B（阶段对照）], [强制 `(github_url, commit)`；editable 边界检查；外部 shell evaluator 分数驱动采样与 Elo；solver 与 guidance 共同进化（S76、S77）],
  [Kernel Foundry　2605.30359], [A + B], [从 KernelBook 检索 top-5 核作 few-shot 初始化 → 多岛进化；含专家初始化消融（S57）],
  [TuneNNGen　2607.05704], [A + B], [外部同族仓库代码作 prompt 指导；等预算对照；direct-copy 分解 + 负对照（S58）],
  [KAPSO　2601.21526], [A + C（论文口径）], [公开 API 有 research、learn_knowledge、evolve、learn 与 E2E 闭环示例；registered evaluation 可让外部分数驱动搜索（S86）],
  [AutoSOTA　2604.05550], [A + C], [从论文 PDF 抽取 GitHub 链接并规范化为初始仓库（S60）],
  [MLE-STAR　2506.15692], [A + C + B（块级）], [用搜索引擎检索 web 上的模型构成初始解；含代码块级消融（S61）],
  [MARCO　2505.03906], [B + C], [实时检索近期会议论文的优化技术（S62）],
  [DeepEvolve　2510.06056], [B（通道级）+ C], [联网 PubMed/arXiv 检索进入迭代精化环（S63）],
  [EES　2609.17590], [强基线，非先例], [validation gate + 持久记忆 + operator credit（S64）],
  [CORAL　2604.01658], [未核实], [摘要含 "evaluator separation"（S80）],
  [EvoX Genesis　2608.10450], [A + C，B 未确认], [文档支持 "point it at your codebase"（S81）],
)

== 4.2 KAPSO：能力的边界与五项缺口

#table(
  columns: (2.9cm, 1fr, 2.3cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [开放式网络检索], [`kapso.py:434-465`；底层 `researcher.py:75-139` 仅 list 模式返回 findings；检索经 codex 原生 web search], [成立，带限定],
  [三类研究产物], [idea／implementation／research report；study 模式返回 `Source.ResearchReport`，不存在 `Source.Study`], [成立],
  [实现条目的字段], [`types.py:96-116` 字段为 query／source／content；解析器不校验 URL], [部分成立],
  [两个 API 的签名], [`kapso.py:467-476`；`1129-1154`（含 `initial_repo`、`resume`）], [成立],
  [检索结果注入 prompt], [是，但为纯 `str()` 拼接；`context` 的 docstring 写 "learn before evolving" 而实现无 learn 步骤], [成立但弱],
  [知识检索是否自动], [*不成立*。`initial_repo` 为空时做一次 workflow repo 搜索（top_k=1），或挂 MCP gate 交由 agent 决定], [更正],
  [闭环的可运行入口], [`run_full_loop.py` 逐字含该闭环并有 "LOOP NOT CLOSED" 断言；但是 E2E 示例脚本，CLI 无 `learn_knowledge` 动词], [成立，非产品化],
  [固定 evaluator 的接入], [registered evaluation 可让 manifest 分数成为 `node.score` 并驱动选择（`feedback_flow.py:76-93`）；须声明 `evaluation_maintainer` 块并提供按 `--fidelity／--fraction／--seed` 调用的评测脚本], [成立，非默认],
  [外部评测回调的作用], [`iteration_evaluator`：*不影响选择、停止、父代与最终分支*（S67 逐字）], [该 API 如此],
  [预算／续跑／记录／记忆], [`budget.py`、`run_checkpoint.py`、`experiment_memory`、`learning/` 与 `knowledge_base/` 均在；*但成本单位为 USD、不记 token 与模型调用、codex 路径下金额恒 0*], [成立，带重大限定],
  [外部工件边界], [`Source.Repo` 只有 `(url, branch)`；两条克隆路径都不固定 commit；*无 commit 固定、无内容哈希、无 license 字段、无可执行性验证*], [缺口],
  [research → 仓库解析], [*不存在任何路径*。研究产物只经三类摄入器；`Source.Repo` 唯一运行期构造点是命令行参数；`workflow_search.py` 消费的是 KG 中由已摄取仓库生成的页], [缺口：完全人工],
  [论文声称与代码], [论文声称 commit metadata、`RepoStore`、corpus manifest 与阈值；代码只有 URL 级 provenance 与分支／时间戳], [论文超出代码],
)

*五项缺口（Rev. 5 更正）*：

```text
1 commit 固定   2 内容哈希   3 license 记录   4 V_E 可执行性验证
5 固定外部评测驱动搜索 -- 机制已存在(registered evaluation), 但非默认、
  需配置块与适配脚本, 且默认允许 agent 请求修改评测器(max_change_requests=3)
```

```text
真正的缺口不是"缺 Search", 而是缺:
Problem -> Search -> ResearchFinding -> ResolvedArtifact -> VerifiedArtifact -> Runtime
其中 ResearchFinding -> ResolvedArtifact 目前完全人工
```

== 4.3 EvE：工程接口贴合度最高的货架候选

#table(
  columns: (2.7cm, 1fr, 2.1cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [仓库与论文], [`scaling-group/eve`，Apache-2.0，release v0.2.0；论文 arXiv:2605.09018v4，题名 *Evolving Ensemble of Agents*], [存在],
  [分发与依赖], [无 PyPI 包（`pip install eve` 装到无关项目），走 `uv sync`；默认 testbed 不需 GPU], [源码安装],
  [commit 契约], [`github_url` 与 `commit` 必须成对，缺失即 `ValueError`（`problem/repo.py:56-57`）；解析后 `git archive` 造快照，该快照即 boundary 基线。*属代码级契约*], [成立],
  [编辑边界检查], [`editable.files`／`folders` 为一等配置且不可同时为空；越界以退出码 1 拒绝并取 `boundary_failure_score`], [成立],
  [外部分数驱动选择], [`subprocess.Popen(["bash", step], cwd=...)` 执行、从 `$EVE_EVAL_LOG_ROOT/score.yaml` 读回、`phase2.py` 按 `entry.score` 采样], [成立],
  [共同进化], [`loop.py:26-27` 自述 "Explicit co-evolution loop"；solver 与 guidance 两种群互相采样，guidance 侧由 Elo 更新], [成立],
  [阶段对照], [README 与论文有 Static-Initial／Static-Final 对照；仓库无对应开关], [部分成立],
  [预算与停止], [`loop.max_iterations` 可用；`StopConditions`（wallclock／token／cost）*全仓库无实例化*，run 级预算从不累加], [部分成立],
  [最小 smoke], [`circle_packing.smoke`；纯 CPU、sqlite、无 docker／Postgres／Redis], [成立],
)

*对计划的意义*：EvE 把 $A_t$（solver／repository 状态）与 $H_t$（agent guidance）放在同一个共同进化环里，与计划:235-239 的固定偏序形成直接对照（D9），并要求在 A1 中记录 $C_"attribution"$。它的 `(github_url, commit)` 契约正好是计划 §5.2 `ExternalInspiration` 里 `source.commit` 字段所要求的语义——即*计划的一个关键字段，在货架上已经有实现*。

= 五、实验协议（操作性部分）

== 5.1 结论

*Go to A0——不直接进入 Runtime Shootout。* 理由：（a）"哪个 runtime 更好"这个问题在 A0 通过之前不可问；（b）评测器在 KAPSO 上默认允许被 agent 请求修改、且 `fidelity` 开启时存在分数标签错配的陷阱（D16）；（c）Closed 臂未必封闭（D15）。文献调查在 Rev. 4 终止，本节的目的是让下一轮产生真实数据。

== 5.2 实验链

```text
A0  Can it run?                              评测一致性 + 管线验证（不比较算法价值）
A1  Is the sophisticated runtime worth it?   简单基线 + runtime 效用探针
B0  Does a known-good artifact help?         VerifiedArtifact 注入（H_A）
B1  Is it worth searching the world?         完整开放世界获取（H_O）
H1  When should the agent search vs evolve?  campaign 级确认
```

*每一步都是前一步的停止条件*：A0 不通过则停止（先修管线）；A1 显示简单基线不劣于任何 runtime 则停止（承认 S82 的零假设）；$H_A$ 无效应则不做 $H_O$（连已知优质工件注入都无收益，让 agent 自己检索无理由）。

== 5.3 A0：评测一致性与管线验证

*A0 的目标*：证明三套 wrapper 都满足 `repo@commit → candidate → E(candidate) → score → selection`，并且三者产生的分数*是同一个数字*。

+ *两个已知候选*：构造 $c_1$、$c_2$ 使 $E(c_1) > E(c_2)$，检查三个 runtime 是否都偏向 $c_1$。不引入"真实质量"这第二套语义。
+ *Evaluator Conformance Test*：取固定候选集 $C^*$，要求三套 wrapper 在数值容差内给出相同分数。
+ *封闭性验证*（B0 前置，但机制在 A0 就要跑通）：用探测证明所选 runtime 真的没有自主外部获取（D15）。

*A0 的三条硬约束（本轮新证据）*：

```text
1 KAPSO 必须 budget.fidelity.mode: off
    否则 fraction 漂到 0.15, 且 feedback_flow.py:68-93 会让 LLM judge 分数顶替机读分数,
    并被打上 fast/0.15 的可比类标签 -- 一致性测试会得出错误的"通过"
2 evaluator 不得依赖 cwd 或 PATH
    EvE 会把 agent runtime bin 前置进 PATH; 三者的候选根各不相同
    (KAPSO 分支 worktree / EvE 的 EVE_SOLVER_ROOT / Loreley 的 context.worktree)
3 三套系统都不向 evaluator 注入 seed
    KAPSO 的 --seed 只是可比类标签; EvE 与 Loreley 根本没有 seed 参数
    => 随机源必须内建于 evaluator 自身
```

*已知的假绿风险（必须显式排除）*：EvE 的评测异常被 `except Exception:` 静默映射为 `failure_score`（默认 0.0），崩溃与真实 0 分不可区分；Loreley 评测超时（默认 900s）会合成失败结果、metrics 超过 64 会被截断、且命中持久测量缓存时会复用旧数（须用新候选或强制 fresh comparison）。

== 5.4 A1：runtime 效用探针

*输入*：通过 A0 的系统 + 简单基线，在同一真实算法任务、同一 `repo@commit`、同一 evaluator 上比较。

```text
对照集: { SimpleIterativeAgent, KAPSO, EvE, Loreley }
主指标: 单位资源的已验证增益, 以 anytime 曲线表达 Q(c) = max_{cost <= c} VerifiedScore
记录项: U = (Gain, Cost, Reliability, Attribution, Operability)
失败项: FailureStage 与 resolve_failed / comprehension_failed / mechanism_mismatch 计数
```

*预算口径（替代迭代数）*：

```text
B = ( T_wall, N_modelCalls, N_tokens, N_evaluatorCalls, C_usd )
选一个作为硬约束, 其余全部报告
```

*记账能力不对称——A1 必须据此调整*：KAPSO 的 `cost_budget` 是美元且 codex 路径下恒为 0，且不记 token 与模型调用；EvE 记 token／turn／tool call，但 run 级预算从不累加（`StopConditions` 与 `write_run_checkpoint` 是死代码），实际可用约束只有 `max_iterations` 与每会话超时；Loreley 记的最全（含 token 分类与 `cost_source`），其 `evaluation_attempts` 表还能区分"真跑"与"缓存复用"。*若 A1 使用 codex 作为 KAPSO 的后端，KAPSO 臂无法公平记账*——须换后端或接受该臂的成本缺失。

*读法限定*：A1 是探针，不是假设检验。单任务、少数 run 只能分辨数量级差异；须预注册"不确定"这一结论（D11 的分析单位在 A1 中尚未满足）。

== 5.5 B0：VerifiedArtifact 注入（$H_A$）

```text
两臂都禁止自主外部获取:
  R_closed   = Runtime(repo, E)
  R_artifact = Runtime(repo, E, VerifiedArtifact)
Delta_A = Y(R_artifact) - Y(R_closed)
```

回答：*一个经过验证的外部实现进入搜索空间本身值多少钱？* 这是当前 H1 最干净的实验，也显著降低第一轮成本。

== 5.6 B1：完整开放世界（$H_O$）

放开 `Search → Resolve → Verify → Adapt`，比较 `Runtime_closed` 与 `Runtime_open`，估计 $Delta_O$。此时还需按 D12 实现 event-keyed 配对，并按 D15 报告封闭性验证的结果。

== 5.7 五项必改（在 B0 之后、H1 之前）

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（需 `use_text_feedback = true`）+ `metadata` 三分；写明三条限定。],
  [*分离两套统计设计*（D3 + D11 + D12）：`statistics.gate` 与 `statistics.campaign` 两组字段；分析单位是 `(task, run)`；配对按 event-keyed 随机源实现；预算为 r 留乘数。],
  [*按 $C times X$ 析因重写 §8.2*（D2）：5 臂，主估计量 $Delta_X$；明文写出潜伏机制迁移不在可识别范围内；把 S82 的简单基线作为首要对照。],
  [*获取链写全*（D10 + D13 + D16）：`Search → Resolve → Verify → ExternalArtifact`；明确 $V_D$ 不等于 $V_E$；参考 EvE 的 `(github_url, commit)` 契约与 KAPSO 的五项缺口。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$ 与 $M_"research"$ 分开；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

== 5.8 建议改

+ 把 `search_failed` / `resolve_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12（D6、D13、D16）。
+ 给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离（D6）。
+ 按 §4.1 的三层判断重写新颖度表述，并补参考文献（D7）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.9 Go / No-Go 判据

*Go to A0*：可立即开始。*A0 → A1* 的门槛：三套 wrapper 都通过评测一致性测试且封闭性已用探测验证。*A1 → B0* 的门槛：至少一个 runtime 在单位资源增益上不劣于简单基线。*B0 → B1* 的门槛：$Delta_A$ 有可观测的正向迹象。*B1 → H1* 的门槛：run 级配对表与 event-keyed 随机源清单存在、主终点与 MDE 已预注册、与 Open 条件 token 匹配的负对照就位。

*在满足上述前提后*：若 $Delta$ 不显著，必须同时报告*搜索失败率*、*解析失败率*与*机制抽取失败率*，以区分"没找到候选"、"找到了但解析不出可运行工件"、"没读懂仓库"、"机制不可迁移"。

== 5.10 什么会使我改变判断

+ 若 A0 显示某套 runtime 无法通过评测一致性测试 → 该候选退出 A1。
+ 若 A1 显示简单基线不劣于全部 runtime → 接受 S82 的零假设，计划应改写为"现成 CLI + evaluator + 简单循环"。
+ 若作者指出一条六轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级。
+ 若 KAPSO 在后续版本把 registered evaluation 设为默认并默认冻结评测器 → D16 的第五项缺口可降为"工程配置"。

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
  [*KAPSO 在 §4 表内的行*：源码不支持"research 返回候选仓库作 seeds"。],
  [*KAPSO 的 KG 自动检索*：改为"MCP 工具交由 agent 自行调用"。],
  [*`iteration_evaluator` 的作用*：observational，不参与选择——*Rev. 5 补充限定*：此结论仅对该 API 成立，对 registered evaluation 不成立（D16）。],
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
  [*"Loreley 是唯一 repository-native 候选"*：撤回。EvE 在 commit 契约与外部分数驱动选择两项上更强。],
  [*KAPSO 的 P2 估计*：更正为五项，并补上 `ResearchFinding -> ResolvedArtifact` 这一完全人工的环节。],
  [*KAPSO 的"两条路径"*：与仓库解析脱节的是三类产物；不存在 `Source.Study`。],
  [*Loreley 的版本与依赖*：HEAD 为 v0.9.0-alpha；"需 Kilocode 与 embedding 端点"应限定为默认配置。],
  [*§0.1 的"6 系统"*：与实际所列不符；"已穷尽"断言已放弃。],
  [*EvE 的题名与依赖*：题名为 *Evolving Ensemble of Agents*；无 PyPI 包；默认不需 GPU。],
)

*Rev. 5 阶段*

#enum(
  [*KAPSO 的第五项缺口*：我原来写"缺外部评测信号进入搜索选择的机制，需替换排序／自定义父代选择"是*错的*。registered evaluation 路径已把 manifest 分数写成 `node.score` 并驱动父代选择与 best 更新；正确说法是"非默认、需配置块与适配脚本、需冻结治理"。],
  [*"KAPSO 不记 token"的隐含读法*：更准确的说法是"记 USD、不记 token 与模型调用，且 codex 后端下 USD 恒为 0"。],
  [*Stage A 的性质*：它只能回答"哪个最容易接入"，不能回答"哪个最适合算法改进"；已拆为 A0 与 A1。],
  [*Closed 臂的默认封闭性*：我在 Rev. 4 未检查；实际三套系统里只有 EvE 的 `codex_tmux` 能靠配置封闭。],
  [*Evaluator Conformance Test 的可行性判断*：我未提出该测试；现接受并补上三条硬约束与两个假绿陷阱。],
)

另有三项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属；KAPSO 论文所述独立知识包是否真含 commit identifiers；§4.1 清单之外是否还有非 arXiv 口径的最近邻工作（CORAL、EvoX Genesis 等仅核到元数据／摘要级）。

= 附录 A：审查覆盖范围

六轮共 46 个独立审查轴。Rev. 0（20）：五个核心系统源码级核实；谱系核实；统计与实验设计；内部一致性与可行性；与既有计划的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；排版实测；专项反证；引用元数据核实。Rev. 1（6）：`text_feedback` 通道与 inspiration 过滤不变量；Man1Lab 搜索能力；AgentCo-Op 的 repo 执行能力；目录层治理事实；许可表述精度；样本量程序的统计陷阱。Rev. 2（6）：cross 模式 prompt 逐行核对；三篇最近邻逐篇核实；穷尽式最近邻检索；experimental unit 的方法学核实。Rev. 3（5）：KAPSO 的公开 API 面与闭环；KAPSO 的 provenance 与外层边界；CRN 与 event-keyed randomness；货架候选横向普选；决策策略层的占位情况。Rev. 4（4）：EvE 的完整断言核实；KAPSO 的 research → repository 缺口；货架候选二次查漏；Stage A 三方可接入性。Rev. 5（5）：KAPSO 的 registered evaluation 是否驱动搜索；三套系统的评测器冻结通路；三套系统能否跑在信息封闭条件下；三套系统的成本记账口径；评测一致性测试的可行性。

= 附录 B：来源清单

*核心依赖*

- [S1] Man1Lab — https://github.com/maniac1um/Man1Lab （MIT）
- [S2] Man1Lab on PyPI — `man1lab` v1.3.0
- [S3] ShinkaEvolve — https://github.com/SakanaAI/ShinkaEvolve ；arXiv:2509.19349
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
- [S35] 货架系统对比（源码实测）：KAPSO、EvE、Loreley、OpenEvolve、ShinkaEvolve、ASI-Evolve 的许可证／安装／evaluator 接入／初始仓库／budget／provenance 对照。"已穷尽"断言已放弃
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`；`inspirations.py:57-128, 143-242, 342-353`
- [S39] Man1Lab 搜索能力（快照 `5376e58d`）— `src/providers/github/client.py:43, 48, 61`；`collection.py:1, 46, 56-58, 88, 124-153`；`verification.py:1, 47`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 3, 28, 62-83, 86-130`；`core/runtime.py:118-122, 167`；`compiler.py:206-224`；`integrator.py:75-90`
- [S41] AGPL-3.0 §0 与 §2 原文 — https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-or-later.txt
- [S42] Zöllner & Pritchard, AJHG 80(4):605-615, 2007 — doi:10.1086/512821
- [S43] Leon, Davis & Kraemer, J Psychiatr Res 45(5):626-629, 2011 — PMID 21035130
- [S44] Gelman & Carlin, Perspect Psychol Sci 9(6):641-651, 2014 — doi:10.1177/1745691614551642
- [S45] DeMets & Lan, Stat Med 13(13-14):1341-1352, 1994 — doi:10.1002/sim.4780131308
- [S46] Nosek et al., PNAS 115(11):2600-2606, 2018 — doi:10.1073/pnas.1708274114
- [S47] R `stats::power.t.test`；Cohen 1988

*方法学*

- [S48] Hurlbert, Ecol Monogr 54(2):187-211, 1984 — doi:10.2307/1942661
- [S49] Lazic, Clarke-Williams & Munafò, PLoS Biol 16(4):e2005282, 2018 — doi:10.1371/journal.pbio.2005282
- [S50] Makin & Orban de Xivry, eLife 8:e48175, 2019 — doi:10.7554/eLife.48175
- [S51] Gelman & Hill, *Data Analysis Using Regression and Multilevel/Hierarchical Models*, 2006
- [S52] Bouthillier et al., MLSys 2021 — arXiv:2103.03098（附录 C.2）
- [S53] Hemming et al., BMC Med Res Methodol 11:102, 2011 — doi:10.1186/1471-2288-11-102
- [S54] Saravanan, Berman & Sober, hierarchical bootstrap — bioRxiv doi:10.1101/819334

*最近邻工作*

- [S55] TurboEvolve — arXiv:2604.18607
- [S56] Loreley — arXiv:2608.19703（Apache-2.0，HEAD `4c375920`）
- [S57] Kernel Foundry — arXiv:2605.30359
- [S58] TuneNNGen — arXiv:2607.05704
- [S59] KAPSO 论文 — arXiv:2601.21526
- [S60] AutoSOTA — arXiv:2604.05550
- [S61] MLE-STAR — arXiv:2506.15692
- [S62] MARCO — arXiv:2505.03906
- [S63] DeepEvolve — arXiv:2510.06056
- [S64] EES — arXiv:2609.17590

*Rev. 3–4 新增*

- [S65] KAPSO 仓库 — https://github.com/Leeroo-AI/kapso （MIT；PyPI `leeroo-kapso` 0.4.7；快照 `7d99b152`）
- [S66] KAPSO 源码路径 — `src/kapso/kapso.py:434-465, 467-476, 1129-1154, 1292-1307, 1745-1781, 1791-1825`；`researcher/researcher.py:75-139`；`knowledge_base/types.py:47-59, 96-116, 141-183`；`repo_ingestor/utils.py:18-76`；`examples/ml_model_development/run_full_loop.py`
- [S67] KAPSO 外部评测文档 — `docs/evolve/external-evaluation.mdx:13-16, 80-95`（仅对 `iteration_evaluator` 成立）
- [S68] Botev & Ridder, *Variance reduction*, Wiley StatsRef 2017 — doi:10.1002/9781118445112.stat07975
- [S69] L'Ecuyer et al., Operations Research 50(6):1073, 2002
- [S70] Salmon et al., *Parallel random numbers: as easy as 1, 2, 3*, SC'11
- [S71] Buffalo, Pearson & Klein, arXiv:2603.11084（stat.ME）
- [S72] OpenAI OpenAPI 对 `seed` 的说明（"Determinism is not guaranteed…`system_fingerprint`"）
- [S73] Loreley 运行约束 — `preflight.py:751-755` 强制 `WORKER_EVALUATOR_PLUGIN`；`env.example:321` 的根提交
- [S74] "何时检索"轴 — Self-RAG arXiv:2310.11511；Search-R1 arXiv:2503.09516；SEM arXiv:2505.07903
- [S75] "何时选算子"轴 — AEL arXiv:2604.21725；SciToolAgent-Evo arXiv:2607.28692；GAE arXiv:2607.10127；TOPOFE arXiv:2607.23286
- [S76] EvE — https://github.com/scaling-group/eve ；arXiv:2605.09018，题名 *Evolving Ensemble of Agents*；Apache-2.0，快照 `979065fd`
- [S77] EvE 源码路径 — `problem/repo.py:46-58, 110-111, 167-179`；`workflow/boundary.py:104-131, 152-200, 212-223`；`workflow/evaluation.py:295-314, 630-631, 634-670, 918-935`；`workflow/loop.py:26-27`；`workflow/phase2.py:544, 553-584, 597-606`；`workflow/phase3.py:47-80`；`core/engine.py:224-241`；`configs/eve/circle_packing.smoke.yaml`
- [S78] KAPSO 的 research → repository 缺口路径 — `knowledge_base/types.py:141-183`；`research_ingestor/implementation_ingestor.py:17-18`；`research_ingestor/prompts/planning.md:39-42`；`knowledge_base/learners/knowledge_learner_pipeline.py:399`；`knowledge_base/search/workflow_search.py:147, 157, 204-225`；`kapso.py:1791-1815`；`repo_ingestor/utils.py:41, 56`
- [S79] KAPSO 让外部分数影响选择的路径 — `execution/orchestrator.py:576-616`；`evaluation_maintainer/maintainer.py:42-86`；`search_strategies/generic/strategy.py:1117-1135`；`config.yaml:123-183`
- [S80] CORAL — arXiv:2604.01658（https://github.com/Human-Agent-Society/CORAL ）
- [S81] EvoX Genesis — arXiv:2608.10450（https://github.com/EMI-Group/genesis ）
- [S82] *Simple Baselines are Competitive with Code Evolution* — arXiv:2602.16805
- [S83] 其余候选 — EvoGit arXiv:2506.02049；MappingEvolve arXiv:2604.26591；Live-SWE-agent arXiv:2511.13646；ParEVO arXiv:2603.02510
- [S84] Stage A 接入点对照 — EvE：`evaluation.steps` 写 `$EVE_EVAL_LOG_ROOT/score.yaml`；Loreley：`WORKER_EVALUATOR_PLUGIN` 与 `MAPELITES_EXPERIMENT_ROOT_COMMIT`；KAPSO：`initial_repo` 与 `eval_dir`
- [S85] 闭源 CLI 依赖 — KAPSO 需 codex 与 claude；EvE 需 Codex CLI 并登录；Loreley 默认 Kilocode（示例路径 codex_cli）

*Rev. 5 新增*

- [S86] KAPSO registered evaluation 驱动搜索的完整路径 — `search_strategies/generic/feedback_flow.py:67, 76-93, 106-108`；`registered_evaluation.py:105-121, 124-158, 263-274`；`strategy.py:1139-1158, 1245, 1373-1380, 1420-1434, 1436-1477`；`fidelity.py:142-153, 184`；`expansion_lanes.py:111-127`；`orchestrator.py:635-641, 755-806, 848-895`；`search_strategies/base.py:740-792`；`evaluation_integrity.py:71, 112, 122`；`evaluation_maintainer/maintainer.py:56-62, 305, 374-397, 505-525`
- [S87] KAPSO 成本与预算口径 — `budget.py:151-153`；`orchestrator.py:562-574, 619-630, 906-921, 1229, 1505-1516`；`run_checkpoint.py:62-70, 291, 313-326`；`codex_agent.py:10-12`（无计费遥测，累计成本恒 0）；`claude_code_agent.py:581-586`
- [S88] EvE 成本与预算口径 — `core/engine.py:34-47, 224, 326, 350, 356`（`StopConditions` 与 `write_run_checkpoint` 从未实例化或调用）；`storage/sqlite.py:73, 781-797, 1397`；`workflow/optimize_logs.py:24-43`；`workflow/loop.py:62, 65, 94, 115`；`runtime/driver.py:196, 230, 263`
- [S89] Loreley 用量与 job 语义 — `db/models.py:700-703, 772-773, 921-922, 1095-1102, 1201-1243`；`static/job_scheduler.py:433-436`；`scheduler/main.py:508-513`；`core/worker/evolution.py:667-750, 1651-1660, 1727-1732`；`core/worker/evaluation_runtime.py:142-164`；`api/schemas/usage.py:17-38`
- [S90] 三套系统的联网与沙箱开关 — KAPSO：`codex_agent.py:84-87, 117-121, 187-188`、`strategy.py:235-241, 328, 358, 371`、`claude_code_agent.py:1182, 1213-1214`、`config.yaml:221`；EvE：`codex_exec.py:93, 112, 434, 448`、`codex_tmux.py:201, 229, 569-570`、`runtime/driver.py:380-386`；Loreley：`config.py:483-545, 1092`、`kilocode_cli.py:963-1010, 1171-1202`、`codex_cli.py:277`
- [S91] KAPSO 评测调用方式与可比类 — `maintainer.py:56-62`（CLI 参数，不用环境变量）；`registered_evaluation.py:81-97, 186, 218-220, 303-313`；`orchestrator.py:599`（`subsample_seed` 默认 1337）；`fidelity.py:244-247, 318`
- [S92] 一致性测试的假绿风险 — EvE：`workflow/evaluation.py:161-167`（异常静默映射为 `failure_score`）；Loreley：`config.py:29, 561`（超时默认 900s）、`core/worker/evaluator.py:2304-2310`（metrics 超过 64 被截断）
- [S93] CLI 层面的网络与沙箱依据 — Codex CLI 的 `SandboxPolicy`（`workspace-write` 默认 `network_access: false`）与 `--search`；claude CLI 的 `--disallowedTools`、`--strict-mcp-config`、`--restricted` 与 OS 级 Bash 沙箱

*同目录文档*

- [S36] `algorithm_research_infrastructure_plan.typ`、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
