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
  #text(size: 9.5pt)[本报告版本：*Rev. 6*（2026-09-20）· 六轮外部复审的核验记录 · 本轮为最后一轮协议修订]
  #v(2pt)
  #text(size: 9.5pt)[结论：*Go to A0——先做 A0.1 评测一致性与 A0.2 selection contract，两者都是候选筛选*]
  #v(2pt)
  #text(size: 9.5pt)[阅读提示：*§5 是操作性部分（实验协议），§0.5–0.6、§2、§6、附录是审计记录*]
]

#v(8pt)

#block(
  fill: rgb("#fdf3e3"),
  inset: 10pt,
  radius: 4pt,
)[
  *本文件为历史版本*：它的操作性内容已被 `open_world_plan_review.typ`（Consolidated，2026-09-20）取代。本文件保留为逐轮的原始修订记录（R1–R51 的详细版本、含每轮的完整核验过程），不再作为操作性版本；如需当前结论与实验协议，请读前者。
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *Rev. 6 总评*：本轮修的是协议语义，其中一条是我自己的事实错误、一条是与复审方的结论分歧。

  #v(3pt)

  + *KAPSO 的 `fidelity` 问题：机制描述以复审方为准，结论以我为准。* 正常顺序确实是 judge 先写、manifest 合法则覆盖；但源码核实（并用真代码执行复现）表明，`fidelity.mode` 不为 off 时，授予类（probe 默认 fast／0.15）与*告知 agent 的硬编码命令*（full／1.0）*结构性不符*，于是错配是*默认路径*而非例外，`node.score` 停留为 judge 分数、且以授予类标签入账。故"必须 off"成立；但要写成"错配时机读分数被丢弃、judge 分数上位"，并把硬不变量升级为*每条 attempt 的三元组必须等于产出该分数的 manifest 三元组*。
  + *`--seed` 那条我错了。* KAPSO 的注册评测契约逐字要求 fast 档用 `--seed` 做*确定性子采样*，所以它是 evaluator 输入，不只是可比类标签。统一接口应是 `E(c; theta_E)`，且 `theta_E` 还必须包含 evaluator 身份。
  + *A0 的语义拆分（复审方对）*：不能要求三套 runtime 都做全局 argmax——Loreley 是 QD archive，只做同 cell 内的非支配替换，采样与分数无关；EvE 的分数入口全是未播种的 rank-softmax，只能做频率检验。故 A0 拆为 A0.1（评测一致性）与 A0.2（各 runtime 自己的 score→search contract）。
  + *A1 的定位（复审方对，结构性修正）*：A1 不是项目级生死门，而是*选 substrate*。即使 `R* = SimpleLoop` 也应继续 B0——"复杂 runtime 暂无必要"推不出"外部工件没有价值"。

  #v(3pt)

  结论：*Go to A0*，但 A0 是候选筛选（`|R_1| >= 1` 即可继续），不是集体门。
]

= 零、审查方式与限度

== 0.1 方法

本报告由七轮构成。Rev. 0 为全文精读 + 20 个并行独立审查轴。Rev. 1 至 Rev. 5 分别为对前五轮复审意见的独立核验（+6／+6／+5／+4／+5 轴）。Rev. 6 为对第六轮复审意见的独立核验（+5 轴：KAPSO 的 fidelity／judge／manifest 顺序与错配触发条件、KAPSO 的 `--seed` 是否为 evaluator 输入、EvE 题名与 Loreley 仓库地址的引用卫生、三套系统的 selection semantics、外部计量层的可行性）。

七轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。每轮都产生了对本报告自身判断的更正（见 §6）。

*范围声明*：文献调查在 Rev. 4 终止；Rev. 5、Rev. 6 只做实验协议修正。§5 是操作性部分。

== 0.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== 0.3 本报告不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行。
- 源码核实基于 2026-09-20 的公开快照：KAPSO `7d99b152`（PyPI 0.4.7）、EvE `979065fd`（release v0.2.0）、Loreley `4c375920`（tag v0.10.0-alpha）、ShinkaEvolve `9912af12`、Man1Lab `5376e58d`、AgentCo-Op `94c37504`。
- *货架候选的"已穷尽"断言已在 Rev. 4 放弃*；检索口径限于 arXiv 与公开 GitHub 仓库。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。

== 0.4 行号引用约定

下文中 `计划:N` 或 `计划:N-M` 均指被审文件 `open_world_algorithm_research_engineering_plan.typ` 的第 N 行或第 N–M 行。外部来源编号（S1–S98）见附录 B。第三方源码判断一律标注其快照提交。

== 0.5 修订记录（Rev. 0 → 6）

*Rev. 1 阶段*

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

*Rev. 2 阶段*

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

*Rev. 3 阶段*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*原说法*], [*核验结果*], [*处理*],
  [R19　KAPSO 的地位], [仅作为清单中的一条], [*应提升*], [新增 §4.2],
  [R20　KAPSO 的 KG 自动检索], [evolve 会自动检索并注入], [*不成立*。MCP 工具交由 agent 自行调用], [已注明],
  [R21　`iteration_evaluator` 的角色], [可把外部分数驱动进化], [*不成立*。该 API 是观测性的], [已更正],
  [R22　KAPSO 的 provenance], [保存 URL/commit provenance], [*部分成立*], [已按两栏列出],
  [R23　§4 的 KAPSO 行], [`research` 返回 candidate repositories], [*源码不支持*], [已降级为论文口径],
  [R24　配对条件], [共享同一 seed 即配对], [*不成立*], [新增 D12],
  [R25　D2 的 estimand 命名], [$E times M$], [*概念不严谨*], [改名为 $C times X$],
  [R26　§4 的层次判断], ["运行时闭环已被占据"], [*过粗*], [已重写为三层判断],
)

*Rev. 4 阶段*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R27　货架普选漏项], [漏了 EvE，Loreley"唯一 repository-native"不成立], [*成立*], [新增 D13；EvE 与 KAPSO 并列一级候选],
  [R28　KAPSO 的 P2 成本], [缺口不止四项 provenance 字段], [*成立，且更严重*], [§4.2 与 §5.2 一并改写],
  [R29　shootout 结构], [拆成 Stage A 与 Stage B], [*接受*], [§5.2 重写为两阶段],
  [R30　EvE 的论文题名], ["Evolutionary Ensemble of Agents"], [*对当前版本不成立*；见 R51（该题名出自 v1）], [已按当前版本引用],
  [R31　EvE 的依赖与分发], [（未主张）], [*需更正*：无 PyPI 包；默认不需 GPU], [已在 §4.3 写明],
  [R32　KAPSO 的"两条路径"], [ImplementationText 与 Source.Repo 互不相通], [*部分成立*。脱节的是三类产物], [已按三类产物改写],
  [R33　Loreley 的版本与依赖], [0.7.6a0 与"需 Kilocode + embedding 端点"], [*过时／过宽*；版本另见 R51], [已更正],
  [R34　§0.1 的"6 系统"计数], [（我自己写的）], [与实际所列不符；二次查漏又有增补], [已改为"候选清单 + 放弃穷尽断言"],
)

*Rev. 5 阶段*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R35　Stage A 的设计], [它其实不是 runtime shootout], [*成立*], [拆为 A0 与 A1，见 D14],
  [R36　预算的定义], ["相同 budget"未定义，应用资源向量 + anytime 曲线], [*成立*，并核出记账能力不对称], [已定义资源向量，见 D14],
  [R37　Stage B 的污染], [Closed 臂可能因 agent 自带联网而不封闭], [*成立，且更严重*。三套里只有 EvE 的 `codex_tmux` 能靠配置封闭], [新增 D15，并把封闭性验证设为前置],
  [R38　H_A 与 H_O 的拆分], [先测注入，再测开放世界], [*接受*], [已写入实验链],
  [R39　KAPSO 的第五项缺口], [KAPSO 已有"固定外部 evaluator → search score"机制，我的"需替换排序"说法有误], [*成立，我错了*。见 D16], [§4.2 的第五项已重写],
  [R40　评测器冻结], [需 `max_change_requests=0` 并冻结 hash], [*成立*。默认上限 3；设 0 即关闭], [已写入协议前置条件],
  [R41　评测一致性测试], [应加固定候选集的数值一致测试], [*可行，但有三条硬约束*，且有会假绿的陷阱], [已写入 A0；Rev. 6 再更正 seed 一条],
  [R42　runtime 效用不应是单一 score], [应记录 attribution 等维度], [*接受*], [已写入 A1 的记录项],
)

*Rev. 6 阶段（对第六轮复审的核验）*

#table(
  columns: (auto, 1fr, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*条目*], [*复审方主张*], [*核验结果*], [*处理*],
  [R43　KAPSO 的 fidelity 风险], [正常顺序是 judge 后 manifest 覆盖；只有 mismatch 路径才有漏洞，故"必须 off"是实验简化而非规避必现 bug], [*机制描述对，结论错*。`mode` 不为 off 时，授予类（probe 默认 fast／0.15）与告知 agent 的硬编码命令（full／1.0）结构性不符，错配即默认路径；用真源码执行复现："Manifest class mismatch … no mechanical score of record" 后 `node.score` 保持 judge 值], [已保留"必须 off"，并收紧措辞、升级不变量],
  [R44　KAPSO 的 `--seed`], [它是 evaluator 输入，不只是可比类标签], [*成立，我错了*。注册契约逐字要求 fast 档用 `--seed` 做确定性子采样], [已改；统一接口含 evaluator 身份],
  [R45　A0 的判据], [不能要求三者都偏向 $c_1$；应拆 evaluated conformance 与 selection conformance], [*成立*。Loreley 只做同 cell 非支配替换、采样与分数无关；EvE 是未播种的 rank-softmax], [A0 拆为 A0.1／A0.2，并给出逐系统检验点],
  [R46　A0 的门], [A0 是 candidate filter，不是 collective gate], [*成立*，且我 §5.9 与 §5.10 原本自相矛盾], [已改为 `|R_1| >= 1` 即继续],
  [R47　A1 的定位], [A1 只决定 substrate $R^*$，不决定项目生死；即使 $R^*$ 是简单循环也应继续 B0], [*接受*。这正是"复杂 runtime 无用"与"外部工件无价值"两命题的区分], [§5.4 与 §5.9 已改写],
  [R48　SimpleLoop 需形式化], [否则可被任意调强或调弱], [*接受*], [已给出固定定义与禁止项],
  [R49　记账应由外部计量层], [不应依赖 runtime 自报], [*接受*，并核实了可行性与其代价], [已写入 A1；含三条工程限制],
  [R50　B0／B1 的轨迹分层], [应记录 Search → Found → … → Improved], [*接受*], [已写入 §5.5／§5.6],
  [R51　引用卫生], [EvE 题名是"元数据不一致"，不是简单对错，且引用 `LoreleyAI/loreley`], [*部分成立*：题名冲突是*跨版本*（v1 为 Evolutionary，v4 为 Evolving），非版本内不一致；*不成立*：`LoreleyAI/loreley` 与 `github.com/LoreleyAI` 均 404，正确地址是 `NeapolitanIcecream/loreley`。另：我写的 v0.9.0-alpha 过时，最新 tag 为 v0.10.0-alpha], [已改为版本化引用；仓库地址已核实；版本已更正],
)

== 0.6 我保留的分歧

+ *"KAPSO 的 `fidelity` 风险只是实验简化"*：不成立。`orchestrator.py:629-643` 把告知 agent 的命令*硬编码*为 `--fidelity full --fraction 1.0`，且该字符串只在 `search_strategies/base.py:735` 赋值一次、无按迭代重算；而 probe 的授予类默认是 `fast`／`0.15`（`fidelity.py:660-666`、`:247`）。于是 `mode: on/auto` 下每个 probe 轮次必然错配，`manifest_score` 返回 None，`node.score` 停留为 judge 抽取的分数，并由 `registered_evaluation.py:124-159` 以*授予类*（`fidelity=node.eval_fidelity`、`fraction=decision.eval_fraction`）入账。这不是偶发路径。另有两条：manifest 行格式坏时解析异常会逃出 `feedback_flow.py:106-109` 的 except，judge 分数同样留存。
+ *硬不变量的强度*：复审方建议 `RegisteredMode => ManifestOfRecord != 空`。该表述必要但偏弱——它不排除"记成另一类"的错标。本报告采用更强形式：*每条 attempt 的 `(evaluator, fidelity, fraction, seed)` 必须等于产出该分数的 run 的 manifest 三元组*；等价地，*授予类必须等于告知 agent 的命令类*。
+ *"EvE 元数据不一致"*：实际是跨版本改名（v1 题名 *Evolutionary Ensemble of Agents*，v4 题名 *Evolving Ensemble of Agents*），v1 与 v4 各自版本内 abs 与 PDF 一致。引用方式：以 v4 为准并注明 v1 旧题名。
+ *`LoreleyAI/loreley`*：该路径与其所属组织均为 404，本报告不采用。
+ *"三套系统都能靠配置形成 Closed 臂"*：不成立，只有 EvE 的 `codex_tmux` 可以（D15）。
+ *CRN 的逐字引文*：无法确认"same random numbers must be used for the same random events"的出处，用 S68 的可核表述。
+ *目录层证据的可移植性*：依赖本地目录状态（自检命令见 §3.3）。
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

第 3 步是承重点：*它假定两段都已有货架。* 七轮核验后这个假定比计划写的更成立，也比计划写的更危险：第一段的货架（KAPSO、EvE）比计划提到的任何组件都更接近目标（§4.2、§4.3），而计划选的组合反而需要自己补上更多。第 2 步的顺序原则因此必须执行到"连 runtime 也不预先指定"。

== 1.2 我认可的部分

+ *目标层的重新收束是对的*：把"提高基础设施完整度"与"提高算法改进能力"分开。
+ *"架构可丢弃"作为硬约束*（计划:169）。
+ *多时间尺度分离*（计划:235-239）。*补充*：EvE 选择把 solver 与 guidance 放在同一个共同进化环里（§4.3），说明联合调度已有可运行实现；计划若要保留固定偏序，需要更强理由，并在 A1 中记录 $C_"attribution"$。
+ *从第一天记录轨迹以备将来 replay*（计划:581）。
+ *不继承 Man1Lab 的生成策略*（计划:474）。
+ *把外部实现交给自有 evaluator 定生死*（与 ShinkaEvolve 的 `correct = 1`、EvE 的脚本分数、KAPSO 的注册评测一致）。
+ *任务选择的阶梯*（计划:998-1004）。
+ *外部事实的可核实性*：六轮外部复审独立复检后，计划点名的系统仍无一虚构。

= 二、我的怀疑

下面十六条按后果排序。*D10–D16 分别为 Rev. 1–5 新增，编号沿用以免破坏交叉引用。*

== D1（重要）计划的注入面写错了，但正确的注入面是存在的

*指控*：计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（清单见计划:529-536），而 `metadata` 对 prompt 不可见，故该决策按文中所述不成立。

*证据一：metadata 不可见（快照 9912af12）*

- `sampler.py:77-207` 的 `sample()` 组装的 user message 只含 `parent.code`、`perf_str(...)` 与可选反馈段；cross 专属段 `prompts_cross.py:57-73` 只写 partner 的 `code` 与 `perf_str(...)`。
- prompt 路径上读 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支），不参与 mutation 与 cross。
- `metadata["patch_name"]` → 元总结器 → `meta_recommendations` → 追加到系统消息，条件为 `patch_type != "cross"`，且经 LLM 摘要。
- 计划:529-536 的六个键在仓库中*零命中*。

*证据二：正确注入面现成*

- `prompts_base.py:58-79`：每个程序在同一块内依次为 `prog.code`、metrics、`Text feedback:` + `prog.text_feedback`；开关默认 `False`。
- `sampler.py:152-157` 把 archive 与 top-k 全部送入该函数；partner 的 code 在同一 message 中*出现两次*（`sampler.py:205-208`）。
- adapter 可自设该字段：`dbase.py:174`，`Database.add()` 原样落库，无 `UPDATE programs SET text_feedback`。

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 捷径，非长期 canonical schema）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*三条限定*：cross 对位段无此通道；该字段属评测器语义、单字段约束；重复评测会新建一行携带评测器值。

== D16（重要）KAPSO 的第五项缺口：机制已存在，但错配使其默认失效

*原说法（已更正）*：Rev. 4 曾称"缺外部评测信号进入搜索选择的机制，需替换排序／自定义父代选择"。该说法*错误*——registered evaluation 路径已把 manifest 分数写成 `node.score` 并驱动选择。但 Rev. 5 与 Rev. 6 的进一步核实发现，该机制在当前配置下*默认失效*。

*证据*：

- 赋值顺序：`feedback_flow.py:66-72` 先写 judge 分数（`node.score = feedback_result.score if evaluation_valid else None`），`:76-93` 仅在 `manifest_score is not None and node.evaluation_valid` 时用 manifest 覆盖（注释逐字 "the manifest is the score of record"）。
- manifest 合法性要求三元组与授予类全等：`registered_evaluation.py:87-91`（`fidelity`、`fraction`（容差 $10^(-9)$）、`seed`），否则打印 "Manifest class mismatch … no mechanical score of record" 并返回 None。
- *结构性错配*：告知 agent 的命令硬编码为 `--fidelity full --fraction 1.0`（`orchestrator.py:629-643`；该字符串只在 `search_strategies/base.py:735` 赋值一次、无按迭代重算），而 probe 授予类默认是 `fast`／`0.15`（`fidelity.py:660-666`、`:247`）。故 `mode: on/auto` 下每个 probe 轮次必然错配，judge 分数上位。
- 该分数以*授予类*入账：`registered_evaluation.py:124-159`（`:151` 取 `fidelity=node.eval_fidelity`、`:144-145` 取 `fraction=decision.eval_fraction`）。
- 另一条路径：manifest 行格式坏时 `parse_manifest_line` 抛异常、逃出 `:106-109` 的 except，`node.score` 同样保持 judge 值。
- `node.score` 驱动：父代选择（`strategy.py:1373-1396`）、best 与 deliverable（`:1436-1477`）、expansion lane（`expansion_lanes.py:111-127`）、evaluator 迁移桥接顺序（`orchestrator.py:755-806`）。*不驱动* stagnation 与停止（那由 judge 投票 ∧ `evaluation_valid` 决定）。

*硬不变量（采纳并加强）*：

```text
每条 attempt 的 (evaluator, fidelity, fraction, seed)
  必须等于产出该分数的那个 run 的 manifest 三元组
等价形式: 授予类必须等于告知 agent 的命令类
A0 处置: mode != off 且出现错配 => 该轮计为 A0 failure
```

*冻结治理*：`evaluation_change_request` 默认上限 3（`orchestrator.py:616`），设 0 即关闭；一旦接受变更，E_t → E_t+1 并桥接复评（首个成功即停）。KAPSO 是三套系统里*唯一能证明"campaign 内评测器未变"*的（逐候选 `verify_evaluation_tree` 与 `verify_data_manifest`、resume 校验、版本注册 append-only 且每版一次 git commit）。

== D14（重要）实验链与预算：A0 不是 shootout，A1 不是生死门

*A0 与 A1 的区分*：Rev. 4 的 Stage A 声称回答"哪个 runtime 最适合算法改进"，却规定"不比较算法分数"，故只能回答"哪个最容易接入"。拆为：

```text
A0.1  Evaluator Conformance     三套 wrapper 是否产出同一个数字（与 search policy 无关）
A0.2  Score -> Search Contract  各 runtime 自己的官方 selection contract 是否生效
A1    SimpleLoop vs QualifiedRuntimes   选出后续实验用的 substrate R*
```

*A0 是候选筛选，不是集体门*：`R_1 = { r ∈ {Simple, KAPSO, EvE, Loreley} : Conformance(r) = Pass }`，只需 $|R_1| >= 1$ 即可继续。Rev. 5 的 §5.9 与 §5.10 原本自相矛盾（前者要求三套全过，后者允许逐个淘汰），已改为后者。

*A1 的定位（结构性修正）*：A1 的输出是 `R* = argmax U(R)`，即*选择 substrate*，不是项目级生死判断。若实验显示 `SimpleLoop > {KAPSO, EvE, Loreley}`，正确的推论只是"复杂 runtime 暂无必要"，不能推出"外部工件没有价值"——此时应令 `R* = SimpleLoop` 并继续 B0。只有当*没有任何 substrate 能可靠执行算法改进*时，B0 才失去意义。

*预算向量*：

```text
B = ( T_wall, N_modelCalls, N_tokens_in, N_tokens_cached, N_tokens_out,
      N_evaluatorCalls, C_usd )
选一个能被统一强制的量作为硬约束, 其余全部报告
比较 anytime 曲线:  Q(c) = max_{cost <= c} VerifiedScore
```

*记账能力不对称（决定 A1 必须外置计量）*：KAPSO 的 `cost_budget` 是美元、不记 token 与模型调用，且 codex 后端无计费遥测、累计成本恒 0；EvE 记 token 与 turn，但 run 级预算从未累加（`StopConditions` 与 `write_run_checkpoint` 都是死代码）；Loreley 记的最全（含 token 分类与 `cost_source`），其 `evaluation_attempts` 表还能区分"真跑"与"缓存复用"。*因此跨 runtime 记账不能由 runtime 自报*。

== D15（重要）Stage B 的对照臂可能根本不封闭

*指控*：`ClosedRuntime vs OpenWorld + SameRuntime` 假设 Closed 臂封闭，但底层 coding agent 可能自带联网与外部工具，于是 `Closed` 臂并不属于封闭世界。

*证据*：KAPSO 无 lane 级 sandbox 参数，codex lane 落到 `danger-full-access`、claude lane 用跳过权限模式，两路都有 Bash，`curl` 即可联网；且 Researcher 路径写死 `web_search=True`，配置项被覆盖。EvE 的 `codex_tmux` 具备 `sandbox_mode`／`allow_network`／`web_search`，*配置即可封闭*；`codex_exec` 硬编码跳过沙箱，不可。Loreley 无网络开关，默认 Kilocode 路径还覆盖外部同名环境变量，唯一硬封闭是改用 codex 后端。CLI 层面有一条硬保证：Codex CLI 的 `workspace-write` 默认 `network_access: false`。

*两个 estimand*：

```text
H_A  External Artifact Value
     两臂都禁止自主外部获取; Open 臂只额外获得冻结好的 VerifiedArtifact
     Delta_A = Y(Runtime(repo, E, VerifiedArtifact)) - Y(Runtime(repo, E))
H_O  Open-World Research Value
     放开完整 Search -> Resolve -> Verify -> Adapt
顺序: H_A 先于 H_O
```

*B0 前置*：封闭性必须用探测证明（而非只配置），三套系统的达成方式不同（EvE 配置即可／KAPSO 需外部断网或改码／Loreley 需换后端或断网）。

== D13（重要）货架候选查漏不完整

*证据（EvE 断言逐条核实，快照 `979065fd`）*：commit 契约（`problem/repo.py:56-57` 缺一即 `ValueError`；`repo.py:167-179` 解析后 `git archive` 造快照）；编辑边界（`repo.py:110-111`；`workflow/boundary.py:104-131, 152-200, 212-223`）；外部分数驱动选择（`evaluation.py:306-314` 执行、`:918-935` 读回、`phase2.py:544, 597-606` 采样）；共同进化（`loop.py:26-27`；`phase2.py:553-584`；`phase3.py:47-80`）；`StopConditions` 未接线。

*完整性*：本报告的"已穷尽"断言*明确放弃*。二次查漏发现 CORAL（S80）、EvoX Genesis（S81）等；未覆盖类包括非 arXiv 正式论文集、闭源或仅 demo 的系统、论文无仓库的双向缺失项。

*反向证据*：S82 用三域实验主张"简单基线在代码进化任务上已具竞争力"，已按 D14 写入 A1 的对照集与零假设。

== D12（重要）"同 seed"不等于配对：需要 event-keyed 随机源

+ CRN 的标准条件是"同一随机数用于*对应的用途/事件*"（S68 逐字）。
+ 状态式 PRNG 在干预改变控制流时会失同步（S71 §1 逐字）；补救是 $U_e = g("seed", "event_id")$ 式键控抽样。
+ *限定*：ML 基准领域的成文做法恰是 A 与 B 复用同一 seed（S52 逐字）；正确表述是 *agentic 研究使该做法的前提失效*。
+ *R1* 纯函数抽样；*R2* 按源分流（可控源跨条件键控共享；不可控源按 `(task, run)` 冻结并共用同一份快照）；*R3* 关键流不可控则该 estimand 禁用配对检验，改 run 级复制并分解 $sigma_"run"$ 与 $sigma_"seed"$。
+ 闭源 LLM 的 `seed` 不保证确定性（S72 逐字）。

== D11（重要）统计设计把 evaluator seed 当成了实验单位

```text
候选提交门  :  candidate × eval seeds     回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs    回答"开放世界的策略是否更好"
```

- 随机性至少三层 `Y_{t,r,s}`；seed 是观测单位而非实验单位（S48；S49、S50 逐字）。
- 即使把同一 search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`。
- *分析程序*：先折叠 seed 层，再建 run 级模型 $d_{t,r} = mu + u_t + v_{t,r}$（S51），或分层 bootstrap（S54）；task 仅 3 个时只报 task 级效应。
- *r 的规划*：$r = f(sigma_"run", "MDE", alpha, beta, "design")$；pilot 只估 $sigma_"run"$ 并取上界；设计效应 $ "DE" = 1 + (m-1)rho $（S53）。
- 增加*变异源*比堆同一源更省（S52 报告约 51 倍计算节省）。

== D2（重要）H1 的两种读法需要分开；析因设计只能回答其中一个

```text
H_U :  OpenWorld         -> UtilityGain    第一阶段可直接检验
H_M :  MechanismTransfer -> UtilityGain    需要因果识别设计

C = External Code      X = Explicit Mechanism Explanation
对比:   C + X  vs  C  vs  X  vs  空  （4 臂）
对照:   C + X_matched  vs  C + X_shuffled   （token 匹配、同域但错配）
主估计量: Delta_X = Y(C + X) - Y(C)
```

$Delta_X$ 回答：*给已经看到代码的 agent 再解释"为什么这个算法有效"，有没有额外价值？* 潜伏机制迁移需要程序结构或行为层面的分析，*不在本设计可识别范围内*。

== D3（重要）候选提交门的统计设计：数值正确，适用范围必须限定

*限定*：功效表*只对候选提交门有效*。表本身经六轮独立复算无误。

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

*其余要点*：$n=5$ 时最小可检测效应为 $1.68 sigma_d$；pilot 只估 $sigma$；$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$；三条件 Bonferroni 下 $n=5$、$d=1$ 功效降至 0.191；confirmation 与 pilot 若共用 seed 则 winner's curse 未消除；per-test $alpha = 0.05$（计划:776）与 §6.2 自陈的 multiple testing 目标（计划:785）不相容；被推迟的 e-value／error spending（计划:806）正是"统计门"名称的实质内容；`time to first improvement`（计划:954）无删失规则与生存分析。

== D4（重要）护栏不可执行：两类里程碑与一致的治理

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
M_research   (研究期):     Delta verified algorithm capability
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化
```

*证据*：milestone 全文仅一次（计划:1242）；Phase 0/1 的交付按设计不产生算法能力增长；§12.1 与 §14.4 两套停止规则互不引用；无任何阶段要求"产出 verified improvement"（§8.3 把首版主验收定为"基础设施能否减少研究成本"，计划:1006）。治理部分见 §3.3。

== D5（重要）H2 没有实验臂；"决策策略层"的占位要分轴说

+ *检索一次后进化*：已占位（MLE-STAR，S61）。*检索与进化交替*：已占位（DeepEvolve S63、MARCO S62）。
+ *把获取/适配/交叉/内部进化作为策略分配*：*部分占位*（"何时检索"见 S74，"何时选算子"见 S75；两者联合且 acquisition 带 provenance 未见明确占位）。

```text
动作空间:  { ResearchExternal, RetrieveKnowledge, ContinueEvolution, RunExperiment, LearnExperience }
问题:      是否存在 pi(a_t | s_t, B_t) 使 Delta VerifiedPerformance / Cost 优于固定 pipeline
```

== D6（重要）未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（D10、D13），并把 `understand` 写成管道一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23），MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751）。旁证：EES 的厂商侧能力明列 web research 与 exploit discovery（S64）；MLE-bench 必须明文禁止查看网上解法并用 Dolos 比对（S24）。*与 D15 同源*：连 Closed 臂都不封闭时，"开放世界"的对照失去意义。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046）。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 License Provenance Gate：来源与依赖清单、指纹与相似度比对（Copilot 比对窗口约 150 字符，官方承认空文件更易命中，S32）、许可白/黑名单与义务登记、命中的派生隔离与替换重写。
+ *供应链*：计划:1217-1219 要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*` 并经加密 DNS 外传（S34）。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661）。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问（S33）。旁证：KAPSO 默认 seed 路径连 commit 都不固定（§4.2）。

== D10（重要）开放世界获取前端并不存在——但这是集成缺口

*证据（快照 `5376e58d` = main HEAD）*：`src/providers/github/client.py:61` 逐字 `raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`，全包无调用点；`GitHubCollectionProvider` 的输入是论文分析里已存在的 URL（`collection.py:1, 46, 56-58, 124-153`），无 query 参数，官方审计文档逐字 "No Search API"、"deterministic, Search-free"；全包无其它发现路径；ADR-0016:161 把 conditional search 列入 Phase 1，实作停在无搜索状态。

*语义问题*：`verified` 被用于指 $V_D$（发现层可信）与 $V_E$（任务层可执行）两件事；Man1Lab 只提供 $V_D$（ADR-0016:142）。

*定级*：关键集成缺口。可借路线：KAPSO 的 knowledge 面、EvE 的 `(github_url, commit)` 契约、AutoSOTA（S60）、MLE-STAR（S61）。真正的缺口不是"缺 Search"，而是*缺 Search result → executable artifact 的 resolution*。

== D7（次要但影响可复核性）引用卫生

正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名 17 个外部系统，其中 12 个无条目。FunSearch 全文 0 次出现（六轮独立核实为 0）。

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
+ *与 MetaRSI、EvE 的路线冲突未解释*：两者都采用联合调度（S14；§4.3）。
+ *发现步骤的归属与验收缺失*：见 D10。
+ *Man1Lab 的接口性质被低估*：Decision Foundation 为非公开 API，Repository Adaptation 仍在 roadmap（S1、S39）。

= 三、我的证据

== 3.1 外部系统源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*。五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0，无论文。*两项能力断言不成立*：（1）无搜索路径（D10）；（2）其 `verified` 仅指 $V_D$。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive 均为真。Apache-2.0，arXiv:2509.19349。*但 `metadata` 不是灵感通道*（D1）；且只做单文件程序进化。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*；三个契约类型是*被执行*的。*过强的一处*：`sandbox_repo` 只产出 dry-run 命令规格。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
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

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版标注；该标注属待执行动作，旧版未加标注；Makefile 通配符把两者都编成 PDF。
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
  [EvE　2605.09018], [A + B（阶段对照）], [强制 `(github_url, commit)`；editable 边界检查；外部 shell evaluator 分数进入未播种的 rank-softmax 采样与 Elo；solver 与 guidance 共同进化（S76、S77）],
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
  [固定 evaluator 的接入], [registered evaluation 可让 manifest 分数成为 `node.score` 并驱动选择；须声明 `evaluation_maintainer` 块并提供按 `--fidelity／--fraction／--seed` 调用的评测脚本], [成立，非默认],
  [该机制的默认有效性], [*默认失效*：`mode` 不为 off 时授予类（fast／0.15）与告知命令（full／1.0）结构性错配，manifest 被丢弃、judge 分数上位并标为授予类（D16）], [缺口],
  [外部评测回调的作用], [`iteration_evaluator`：*不影响选择、停止、父代与最终分支*（S67 逐字）], [该 API 如此],
  [预算／续跑／记录／记忆], [`budget.py`、`run_checkpoint.py`、`experiment_memory`、`learning/` 与 `knowledge_base/` 均在；*成本单位为 USD、不记 token 与模型调用、codex 后端下金额恒 0*], [成立，带重大限定],
  [外部工件边界], [`Source.Repo` 只有 `(url, branch)`；两条克隆路径都不固定 commit；*无 commit 固定、无内容哈希、无 license 字段、无可执行性验证*], [缺口],
  [research → 仓库解析], [*不存在任何路径*。研究产物只经三类摄入器；`Source.Repo` 唯一运行期构造点是命令行参数], [缺口：完全人工],
  [论文声称与代码], [论文声称 commit metadata、`RepoStore`、corpus manifest 与阈值；代码只有 URL 级 provenance 与分支／时间戳], [论文超出代码],
)

*五项缺口*：

```text
1 commit 固定   2 内容哈希   3 license 记录   4 V_E 可执行性验证
5 固定外部评测驱动搜索 -- 机制已存在, 但默认被错配失效(见 D16),
  需配置块与适配脚本, 且默认允许 agent 请求修改评测器
真实缺口: Problem -> Search -> ResearchFinding -> ResolvedArtifact -> VerifiedArtifact
          其中 ResearchFinding -> ResolvedArtifact 目前完全人工
```

== 4.3 EvE：工程接口贴合度最高的货架候选

#table(
  columns: (2.7cm, 1fr, 2.1cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [仓库与论文], [`scaling-group/eve`，Apache-2.0（含 NOTICE），release v0.2.0（仅 v0.1.0 与 v0.2.0 两个 tag）；论文 arXiv:2605.09018v4，题名 *Evolving Ensemble of Agents*（v1 旧题名为 *Evolutionary Ensemble of Agents*）；无 CITATION.cff，仅 README 内嵌 BibTeX], [存在],
  [分发与依赖], [无 PyPI 包（`pip install eve` 装到无关项目），走 `uv sync`；默认 testbed 不需 GPU], [源码安装],
  [commit 契约], [`github_url` 与 `commit` 必须成对，缺失即 `ValueError`（`problem/repo.py:56-57`）；解析后 `git archive` 造快照，该快照即 boundary 基线。*属代码级契约*], [成立],
  [编辑边界检查], [`editable.files`／`folders` 为一等配置且不可同时为空；越界以退出码 1 拒绝并取 `boundary_failure_score`], [成立],
  [外部分数驱动选择], [`bash step` 执行、从 `$EVE_EVAL_LOG_ROOT/score.yaml` 读回；分数进入 population 采样。*但采样是 rank-softmax 且 RNG 未播种*], [成立，非确定性],
  [共同进化], [`loop.py:26-27` 自述 "Explicit co-evolution loop"；solver 与 guidance 两种群互相采样，guidance 侧由 Elo 更新], [成立],
  [阶段对照], [README 与论文有 Static-Initial／Static-Final 对照；仓库无对应开关], [部分成立],
  [预算与停止], [`loop.max_iterations` 可用；`StopConditions`（wallclock／token／cost）*全仓库无实例化*，run 级预算从不累加], [部分成立],
  [最小 smoke], [`circle_packing.smoke`；纯 CPU、sqlite、无 docker／Postgres／Redis], [成立],
)

*对计划的意义*：EvE 把 $A_t$（solver／repository 状态）与 $H_t$（agent guidance）放在同一个共同进化环里，与计划:235-239 的固定偏序形成直接对照（D9），并要求在 A1 中记录 $C_"attribution"$。它的 `(github_url, commit)` 契约正好是计划 §5.2 `ExternalInspiration` 里 `source.commit` 字段所要求的语义——*计划的一个关键字段，在货架上已经有实现*。

= 五、实验协议（操作性部分）

== 5.1 结论

*Go to A0。* 理由：（a）"哪个 runtime 更好"这个问题在 A0 通过之前不可问；（b）KAPSO 的注册评测路径默认被错配失效（D16）；（c）Closed 臂未必封闭（D15）。文献调查在 Rev. 4 终止，本节目的是让下一轮产生真实数据。

== 5.2 实验链

```text
A0.1  Evaluator Conformance           三套 wrapper 是否产出同一个数字
A0.2  Score -> Search Contract        各 runtime 官方 selection contract 是否生效
A1    SimpleLoop vs QualifiedRuntimes 选出后续实验的 substrate R*
B0    R* vs R* + VerifiedArtifact     H_A: 外部工件本身有价值吗
B1    ClosedAcquisition vs OpenWorldAcquisition   H_O: 主动获取值得吗
H1    pi(SearchExternal, Adapt, Cross, EvolveInternal | s_t, B_t)
```

#table(
  columns: (auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*层*], [*它回答的唯一问题*],
  [A0], [测量链可信吗（评测一致 + 分数确实驱动搜索）],
  [A1], [需要多复杂的搜索机器（选出 substrate，不判生死）],
  [B0], [外部工件本身有价值吗],
  [B1], [主动获取外部工件值得吗],
  [H1], [何时获取、何时内部进化],
)

*停止规则*：A0 是候选筛选（见 §5.3）；A1 只选 substrate、不终止项目（见 §5.4）；$H_A$ 无效应则不做 $H_O$。

== 5.3 A0：评测一致性与 selection contract

== 5.3.1 A0.1 Evaluator Conformance

固定候选集 $C^* = {c_1, ..., c_k}$，要求三套 wrapper 在数值容差内给出相同分数：

```text
对每个 runtime r 与每个候选 c:  E_r(c; theta_E) = E*(c; theta_E) ± epsilon
```

*统一接口*：

```text
E(c; theta_E),  theta_E = (evaluator identity, seed, fidelity, fraction, ...)
要求:  theta_E 在三套 wrapper 间一致; 缺失参数取等价的固定值
```

*逐系统事实*：KAPSO 经 CLI 传固定 seed（`--fidelity／--fraction／--seed`，默认 1337，来自 `evaluation_maintainer.subsample_seed`，`orchestrator.py:599`），且其注册契约*逐字要求* fast 档用该 seed 做确定性子采样（`evaluation_maintainer/prompts/setup_build.md:11-15`、`setup_provided.md:13-17`），故 seed 是 evaluator 输入而非纯标签；EvE 与 Loreley 的 evaluator 接口*不传任何 seed*（EvE 只注入 `EVE_WORKSPACE_ROOT／EVE_SOLVER_ROOT／EVE_EVAL_LOG_ROOT／PYTHONDONTWRITEBYTECODE`；Loreley 的 `EvaluationContext` 无 seed 字段，其 `mapelites_sampler_seed` 用于采样而非评测）。因此"随机源必须内建在 evaluator 自身"这一结论仍成立，但 `theta_E` 必须显式包含 seed 与 evaluator 身份：KAPSO 的身份是 manifest 指纹，Loreley 是 `evaluator_name + version + campaign_program_hash`，EvE 无版本概念。

*KAPSO 的额外硬不变量（D16）*：

```text
每条 attempt 的 (evaluator, fidelity, fraction, seed)
  必须等于产出该分数的那个 run 的 manifest 三元组
等价: 授予类必须等于告知 agent 的命令类
处置: mode != off 且出现错配 => 该轮计为 A0 failure
```

*说明*：`budget.fidelity.mode: off` 仍然是实验简化；但仅关掉它并不构成充分保证——必须同时断言上述不变量，因为"记成另一类"的错标在 off 之外的配置下依然可能出现。

*A0.1 的三条硬约束与两个假绿陷阱*：

```text
1 evaluator 不得依赖 cwd 或 PATH
    EvE 会把 agent runtime bin 前置进 PATH; 三者的候选根各不相同
    (KAPSO 分支 worktree / EvE 的 EVE_SOLVER_ROOT / Loreley 的 context.worktree)
2 计数与日志不得写在会被还原的目录
    KAPSO 的 kapso_evaluation/ 会被 git checkout 还原
3 多目标或金字塔分数必须先收敛为单标量
    EvE 的 score 是 PyTree, Loreley 是多目标 Pareto
假绿: EvE 的评测异常被静默映射为 failure_score(0.0), 与真实 0 分不可区分
假绿: Loreley 评测超时合成失败、metrics 超过 64 被截断、命中缓存复用旧数
```

== 5.3.2 A0.2 Score → Search Contract（逐 runtime）

不能要求三套 runtime 都做全局 argmax——三者的 selection semantics 不同。

#table(
  columns: (1.7cm, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*官方 selection semantics*], [*A0.2 的可执行检验点*],
  [KAPSO], [全确定：父代、deliverable、轮次代表都是取最大], [置 $E(c_1) > E(c_2)$ 跑一轮，断言下一轮的父代分支为 $c_1$，且取最优实验分支返回 $c_1$],
  [EvE], [分数入口全为 rank-softmax，且 RNG 未播种；两候选时选中 $c_1$ 的概率约 0.731], [在 solver examples 与 working optimizer 上做*频率*检验（二项），不能只看一次，也不能用分数无关的 prefill 段],
  [Loreley], [QD archive：只在*同一 cell 内*做非支配替换；采样与分数无关；无全局最优必胜], [构造度量相同（同 cell）的 $c_1$、$c_2$，断言 $c_1$ 的入档结果为替换且 cell 内 $c_2$ 被移除；再断言报表分支指向 $c_1$。跨 cell 时高分*不*淘汰],
)

*封闭性验证（B0 前置，机制在 A0 就应跑通）*：用探测证明所选 runtime 没有自主外部获取（D15），而不是只在配置里关。

== 5.4 A1：substrate 选择

*目的*：选出后续实验使用的 substrate $R^*$，*不是*判断项目生死。

```text
对照集: { SimpleLoop, 合格 runtime }
主指标: 单位资源的已验证增益, 以 anytime 曲线表达 Q(c) = max_{cost <= c} VerifiedScore
记录项: U = (Gain, Cost, Reliability, Attribution, Operability)
失败项: FailureStage 与 resolve_failed / comprehension_failed / mechanism_mismatch 计数
```

*SimpleLoop 的固定定义（防止被任意调强或调弱）*：

```text
R_S = (M, P, T, E, pi_S)
M,P,T,E 与复杂 runtime 尽可能相同（同模型、同工具、同 evaluator、同 sandbox 与访问策略）
只把 search policy 简化:
  c_0 = baseline
  c_{t+1} = Agent(c_t, H_t)
  c*_t = argmax_{i <= t} E(c_i)
  parent_{t+1} = c*_t
禁止: archive/QD、演化的 harness/guidance、multi-island、学习型算子选择、
      外部检索（A1 阶段）、未声明的特殊 prompt
```

*外部计量层（因为 runtime 自报不可比）*：

```text
Runtime -> Meter -> Model/API
Runtime -> EvalWrapper -> Evaluator
统一记录 B = (T_wall, N_calls, T_in, T_cached, T_out, N_E, C_usd)
runtime 自带 telemetry 只作 cross-check
硬约束选一个能被统一强制的量（例如加权 token 总量或代理侧实际费用）
```

*计量层的三条工程限制（已核实）*：Codex CLI *没有* base URL 环境变量，只能走配置键 `openai_base_url` 或 `model_providers.<id>.base_url`，且代理必须实现 `responses` 协议；claude CLI 有 `ANTHROPIC_BASE_URL`（官方文档明示用于经代理路由）；Loreley 的 Kilocode 路径会在子进程环境中*清除* `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，必须改用它自己的 base URL 配置；此外 Loreley 的 Kilo CLI 自带 job token 预算，其耗尽被当作失败原因码，会先于外部硬约束触发并表现为"失败"。

*读法限定*：A1 是探针，不是假设检验。单任务、少数 run 只能分辨数量级差异；须预注册"不确定"这一结论（D11 的分析单位在 A1 中尚未满足）。

== 5.5 B0：VerifiedArtifact 注入（$H_A$）

```text
两臂都禁止自主外部获取:
  R_closed   = Runtime(repo, E)
  R_artifact = Runtime(repo, E, VerifiedArtifact)
Delta_A = Y(R_artifact) - Y(R_closed)
```

回答：*一个经过验证的外部实现进入搜索空间本身值多少钱？*

*轨迹分层（每跳都要记录，供 B1 分解）*：

```text
Search -> Found -> Resolved -> Verified -> Injected -> Used -> Improved
```

== 5.6 B1：完整开放世界（$H_O$）

放开 `Search → Resolve → Verify → Adapt`，比较 `Runtime_closed` 与 `Runtime_open`。$Delta_O$ 应至少按三段与一项成本报告：

```text
Delta_O ≈ Delta_discovery + Delta_resolution + Delta_transfer - C_acquisition
（不能简单线性分解, 但四者必须各自可观测）
```

并按 D12 实现 event-keyed 配对，按 D15 报告封闭性验证结果。

== 5.7 五项必改（在 B0 之后、H1 之前）

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（需 `use_text_feedback = true`）+ `metadata` 三分；写明三条限定。],
  [*分离两套统计设计*（D3 + D11 + D12）：`statistics.gate` 与 `statistics.campaign` 两组字段；分析单位是 `(task, run)`；配对按 event-keyed 随机源实现；预算为 r 留乘数。],
  [*按 $C times X$ 析因重写 §8.2*（D2）：4 臂 + shuffled 对照，主估计量 $Delta_X$；明文写出潜伏机制迁移不在可识别范围内；把 S82 的简单基线作为首要对照。],
  [*获取链写全*（D10 + D13 + D16）：`Search → Resolve → Verify → ExternalArtifact`；明确 $V_D$ 不等于 $V_E$；参考 EvE 的 `(github_url, commit)` 契约、KAPSO 的五项缺口与 manifest 不变量。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$ 与 $M_"research"$ 分开；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

== 5.8 建议改

+ 把 `search_failed` / `resolve_failed` / `comprehension_failed` / `mechanism_mismatch` 单列为计数指标并纳入 §12。
+ 给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离（D6）。
+ 按 §4.1 的三层判断重写新颖度表述，并补参考文献（D7）。
+ 修排版：在计划:951-962 等长公式内按语义位置插入强制断行。
+ 统一 `AHE / HarnessFix` 的写法，把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 5.9 Go / No-Go 判据

+ *Go to A0*：可立即开始。
+ *A0 → A1*：`|R_1| >= 1`，即至少一套候选（含 SimpleLoop）通过 A0.1 与 A0.2。*A0 是候选筛选，不是集体门*；某一套 adapter 的 bug 不应阻止其余实验。
+ *A1 → B0*：得到 $R^* = "argmax" U$，无论它是复杂 runtime 还是 SimpleLoop。*A1 的输出是 substrate 选择，不是项目级生死判断*；只有当没有任何 substrate 能可靠执行算法改进时，B0 才失去意义。
+ *B0 → B1*：$Delta_A$ 有可观测的正向迹象。
+ *B1 → H1*：run 级配对表与 event-keyed 随机源清单存在、主终点与 MDE 已预注册、与 Open 条件 token 匹配的负对照就位。

*在满足上述前提后*：若 $Delta$ 不显著，必须同时报告*搜索失败率*、*解析失败率*与*机制抽取失败率*，以区分"没找到候选"、"找到了但解析不出可运行工件"、"没读懂仓库"、"机制不可迁移"。

== 5.10 什么会使我改变判断

+ 若 A0 显示某套 runtime 无法通过评测一致性或 selection contract → 该候选退出 A1（不影响其余）。
+ 若 A1 显示 SimpleLoop 不劣于全部 runtime → 接受 S82 的零假设，令 `R* = SimpleLoop` 并继续 B0。
+ 若作者指出一条七轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级。
+ 若 KAPSO 在后续版本把注册评测算为默认，或让告知命令随授予类派生 → D16 的第五项缺口可降为"工程配置"。

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
  [*`iteration_evaluator` 的作用*：observational，不参与选择——仅对该 API 成立，对 registered evaluation 不成立（D16）。],
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
  [*Loreley 的版本与依赖*：版本已由 R51 再更正；"需 Kilocode 与 embedding 端点"应限定为默认配置。],
  [*§0.1 的"6 系统"*：与实际所列不符；"已穷尽"断言已放弃。],
  [*EvE 的题名与依赖*：题名争议见 R51（跨版本）；无 PyPI 包；默认不需 GPU。],
)

*Rev. 5 阶段*

#enum(
  [*KAPSO 的第五项缺口*：原写"缺机制、需替换排序"是错的；registered 路径已把 manifest 分数写成 `node.score`。],
  [*"KAPSO 不记 token"的隐含读法*：准确说法是"记 USD、不记 token 与模型调用，且 codex 后端下 USD 恒为 0"。],
  [*Stage A 的性质*：只能回答"哪个最容易接入"；已拆为 A0 与 A1。],
  [*Closed 臂的默认封闭性*：三套系统里只有 EvE 的 `codex_tmux` 能靠配置封闭。],
  [*Evaluator Conformance Test 的可行性*：接受，并补上硬约束与假绿陷阱。],
)

*Rev. 6 阶段*

#enum(
  [*KAPSO 的 `--seed`*：我原写"只是可比类标签"是*错的*；它是 evaluator 输入——注册契约逐字要求 fast 档用该 seed 做确定性子采样。],
  [*一致性约束的写法*：由"三套系统都不注入 seed + 随机源内建"改为"`theta_E` 必须跨 wrapper 一致，且 `theta_E` 含 evaluator 身份"。],
  [*A0 的判据*：我原写"三套 wrapper 都偏向 $c_1$"不成立——Loreley 只在同 cell 内做非支配替换、采样与分数无关；EvE 是未播种的 rank-softmax，只能做频率检验。已按系统分别给出可执行检验点。],
  [*A0 的门*：由"三套全过"改为 `|R_1| >= 1`（我 §5.9 与 §5.10 原本自相矛盾）。],
  [*A1 的定位*：由"至少要有一个 runtime 不劣于简单基线，否则停止"改为"选出 substrate $R^*$，即使它是 SimpleLoop 也继续 B0"。],
  [*fidelity 措辞*：由"judge 顶替机读分数"改为"错配时机读分数被丢弃、judge 分数上位并以授予类标签入账"，并补上"mode 不为 off 时该错配是默认路径"这一执行级复现结果。],
  [*Loreley 的版本*：v0.9.0-alpha 过时，最新 tag 为 v0.10.0-alpha（HEAD `4c375920`）。],
  [*EvE 题名的表述*：由"复审方的题名是错的"改为"题名冲突跨版本"（v1 为 Evolutionary，v4 为 Evolving），并按 v4 引用。],
)

另有三项应记为*未核实*而非结论：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属；KAPSO 论文所述独立知识包是否真含 commit identifiers；§4.1 清单之外是否还有非 arXiv 口径的最近邻工作（CORAL、EvoX Genesis 仅核到元数据级）。

= 附录 A：审查覆盖范围

七轮共 51 个独立审查轴。Rev. 0（20）：五个核心系统源码级核实；谱系核实；统计与实验设计；内部一致性与可行性；与既有计划的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；排版实测；专项反证；引用元数据核实。Rev. 1（6）：`text_feedback` 通道与过滤不变量；Man1Lab 搜索能力；AgentCo-Op 的 repo 执行能力；目录层治理事实；许可表述精度；样本量程序的统计陷阱。Rev. 2（6）：cross 模式 prompt 逐行核对；三篇最近邻逐篇核实；穷尽式最近邻检索；experimental unit 的方法学核实。Rev. 3（5）：KAPSO 的公开 API 面与闭环；KAPSO 的 provenance 与外层边界；CRN 与 event-keyed randomness；货架候选横向普选；决策策略层的占位情况。Rev. 4（4）：EvE 的完整断言核实；KAPSO 的 research → repository 缺口；货架候选二次查漏；Stage A 三方可接入性。Rev. 5（5）：KAPSO 的 registered evaluation 是否驱动搜索；评测器冻结通路；信息封闭条件；成本记账口径；评测一致性测试可行性。Rev. 6（5）：KAPSO 的 fidelity／judge／manifest 顺序与错配触发条件；`--seed` 是否为 evaluator 输入；EvE 题名与 Loreley 仓库地址的引用卫生；三套系统的 selection semantics；外部计量层的可行性。

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
- [S35] 货架系统对比（源码实测）：KAPSO、EvE、Loreley、OpenEvolve、ShinkaEvolve、ASI-Evolve。"已穷尽"断言已放弃
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`
- [S39] Man1Lab 搜索能力（快照 `5376e58d`）— `src/providers/github/client.py:61`；`collection.py:56-58, 124-153`；`verification.py:1, 47`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 28, 62-83`；`core/runtime.py:118-122`；`compiler.py:206-224`；`integrator.py:75-90`
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
- [S56] Loreley — arXiv:2608.19703（Apache-2.0；仓库 `NeapolitanIcecream/loreley`，HEAD `4c375920`，tag v0.10.0-alpha）
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
- [S66] KAPSO 源码路径 — `src/kapso/kapso.py:434-465, 467-476, 1129-1154, 1292-1307, 1745-1781`；`researcher/researcher.py:75-139`；`knowledge_base/types.py:47-59, 96-116, 141-183`；`repo_ingestor/utils.py:18-76`
- [S67] KAPSO 外部评测文档 — `docs/evolve/external-evaluation.mdx:13-16, 80-95`（仅对 `iteration_evaluator` 成立）
- [S68] Botev & Ridder, *Variance reduction*, Wiley StatsRef 2017 — doi:10.1002/9781118445112.stat07975
- [S69] L'Ecuyer et al., Operations Research 50(6):1073, 2002
- [S70] Salmon et al., *Parallel random numbers: as easy as 1, 2, 3*, SC'11
- [S71] Buffalo, Pearson & Klein, arXiv:2603.11084（stat.ME）
- [S72] OpenAI OpenAPI 对 `seed` 的说明（"Determinism is not guaranteed…`system_fingerprint`"）
- [S73] Loreley 运行约束 — `preflight.py:751-755` 强制 `WORKER_EVALUATOR_PLUGIN`；`env.example:321` 的根提交
- [S74] "何时检索"轴 — Self-RAG arXiv:2310.11511；Search-R1 arXiv:2503.09516；SEM arXiv:2505.07903
- [S75] "何时选算子"轴 — AEL arXiv:2604.21725；SciToolAgent-Evo arXiv:2607.28692；GAE arXiv:2607.10127；TOPOFE arXiv:2607.23286
- [S76] EvE — https://github.com/scaling-group/eve ；arXiv:2605.09018（当前 v4 题名 *Evolving Ensemble of Agents*；v1 题名 *Evolutionary Ensemble of Agents*）；Apache-2.0，快照 `979065fd`
- [S77] EvE 源码路径 — `problem/repo.py:46-58, 110-111, 167-179`；`workflow/boundary.py:104-131, 152-200, 212-223`；`workflow/evaluation.py:295-314, 630-631, 634-670, 918-935`；`workflow/loop.py:26-27`；`workflow/phase2.py:544, 553-584, 597-606`；`workflow/phase3.py:47-80`；`core/engine.py:224-241`
- [S78] KAPSO 的 research → repository 缺口路径 — `knowledge_base/types.py:141-183`；`research_ingestor/implementation_ingestor.py:17-18`；`knowledge_base/learners/knowledge_learner_pipeline.py:399`；`knowledge_base/search/workflow_search.py:147, 157, 204-225`；`kapso.py:1791-1815`
- [S79] KAPSO 注册评测的接入 — `execution/orchestrator.py:576-616`；`evaluation_maintainer/maintainer.py:42-86`；`search_strategies/generic/strategy.py:1117-1135`；`config.yaml:123-183`
- [S80] CORAL — arXiv:2604.01658（https://github.com/Human-Agent-Society/CORAL ）
- [S81] EvoX Genesis — arXiv:2608.10450（https://github.com/EMI-Group/genesis ）
- [S82] *Simple Baselines are Competitive with Code Evolution* — arXiv:2602.16805
- [S83] 其余候选 — EvoGit arXiv:2506.02049；MappingEvolve arXiv:2604.26591；Live-SWE-agent arXiv:2511.13646；PAR EVO arXiv:2603.02510
- [S84] Stage A 接入点对照 — EvE：`evaluation.steps` 写 `$EVE_EVAL_LOG_ROOT/score.yaml`；Loreley：`WORKER_EVALUATOR_PLUGIN` 与 `MAPELITES_EXPERIMENT_ROOT_COMMIT`；KAPSO：`initial_repo` 与 `eval_dir`
- [S85] 闭源 CLI 依赖 — KAPSO 需 codex 与 claude；EvE 需 Codex CLI 并登录；Loreley 默认 Kilocode（示例路径 codex_cli）
- [S86] KAPSO registered evaluation → 选择的完整路径 — `feedback_flow.py:66-95, 106-109`；`registered_evaluation.py:52-121, 124-159, 263-274, 296-303`；`strategy.py:1373-1396, 1420-1434, 1436-1477`；`fidelity.py:142-153, 184, 247, 660-666`；`expansion_lanes.py:111-127`；`orchestrator.py:599, 629-643, 755-806, 848-895`；`search_strategies/base.py:735, 740-792`
- [S87] KAPSO 成本与预算口径 — `budget.py:151-153`；`orchestrator.py:562-574, 619-630, 906-921, 1229, 1505-1516`；`run_checkpoint.py:62-70, 291`；`codex_agent.py:10-12`（无计费遥测）
- [S88] EvE 成本与预算口径 — `core/engine.py:34-47, 224, 326, 350, 356`（`StopConditions` 与 `write_run_checkpoint` 从未实例化）；`storage/sqlite.py:73, 781-797`；`workflow/loop.py:62, 65, 94, 115`
- [S89] Loreley 用量与 job 语义 — `db/models.py:700-703, 772-773, 921-922, 1201-1243`；`core/worker/evolution.py:667-750, 1651-1660, 1727-1732`；`core/worker/evaluation_runtime.py:125-164`；`api/schemas/usage.py:17-38`
- [S90] 三套系统的联网与沙箱开关 — KAPSO：`codex_agent.py:84-87, 117-121`、`strategy.py:235-241, 328, 358, 371`、`claude_code_agent.py:1182`、`config.yaml:221`；EvE：`codex_exec.py:93, 112, 434`、`codex_tmux.py:201, 229, 569-570`、`runtime/driver.py:380-386`；Loreley：`config.py:483-545, 1092`、`kilocode_cli.py:963-1010, 1171-1202`、`codex_cli.py:277`
- [S91] KAPSO 评测调用契约与可比类 — `evaluation_maintainer/maintainer.py:56-62, 431-435, 475-479`；`evaluation_maintainer/prompts/setup_build.md:11-15`；`evaluation_maintainer/prompts/setup_provided.md:13-17`；`fidelity.py:44-50`
- [S92] 一致性测试的假绿风险 — EvE：`workflow/evaluation.py:161-167`；Loreley：`config.py:29, 561`、`core/worker/evaluator.py:2304-2310`
- [S93] CLI 层面的网络与沙箱依据 — Codex CLI 的 `SandboxPolicy`（`workspace-write` 默认 `network_access: false`）与 `--search`；claude CLI 的 `--disallowedTools`、`--strict-mcp-config`、`--restricted` 与 OS 级 Bash 沙箱

*Rev. 6 新增*

- [S94] KAPSO 的 fidelity 错配路径（执行级复现）— `feedback_flow.py:66-95`；`registered_evaluation.py:87-91, 124-159`；`orchestrator.py:629-643`；`fidelity.py:247, 660-666`；`search_strategies/base.py:735`。实测：以生产命令（`--fidelity full --fraction 1.0`）与 fast／0.15 授予类调用，`manifest_of_record` 输出 "Manifest class mismatch … no mechanical score of record" 并返回 None，`node.score` 保持 judge 值
- [S95] Loreley 的 QD 语义与采样 — `pareto_archive.py:1, 265-277, 337, 417-444`；`sampler.py:531-559, 732, 759`；`scheduler/main.py:820-931`；ADR 0051 与 0052
- [S96] EvE 的采样语义 — `configs/eve/loop/default.yaml:22, 28, 37, 43-46, 51`；`rank_softmax.py:104, 181`；`populations/base.py:40`（RNG 未播种）；`phase2.py:566, 589, 600, 612, 629`；`evaluators/elo.py:55-100`
- [S97] 外部计量层的端点与限制 — Codex CLI 配置键 `openai_base_url` 与 `model_providers.<id>.base_url`（无环境变量端点覆盖，`wire_api` 仅支持 `responses`）；claude CLI 的 `ANTHROPIC_BASE_URL`／`ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN`；Loreley 的 `kilocode_cli.py:60-79, 546-563` 会清除 `OPENAI_API_KEY`／`OPENAI_BASE_URL`，并有自身 job token 预算（`:38-43, 1246-1257`）
- [S98] EvE 的分发与元数据 — 仅 tag v0.1.0 与 v0.2.0；无 `CITATION.cff`（仅 README 内嵌 BibTeX）；Apache-2.0 并附 NOTICE

*同目录文档*

- [S36] `algorithm_research_infrastructure_plan.typ`、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
