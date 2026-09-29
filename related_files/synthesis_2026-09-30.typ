// Self-contained Typst source. Typst 0.15; Chinese font: Noto Sans CJK SC.
// Compile: make synthesis_2026-09-30   (or: typst compile synthesis_2026-09-30.typ)
// 本文无 \addbibresource 依赖：所有引证都是仓库内的 path:line，不是文献条目。
#set document(title: "构想梳理 v2：溯源、四条线、两处同名异义、一个已经存在的反驳", author: "rsi-dev", date: datetime(year: 2026, month: 9, day: 30))
#set page(paper: "a4", margin: (x: 22mm, y: 20mm), numbering: "1")
#set text(lang: "zh", font: ("Noto Sans CJK SC", "Noto Sans"), size: 10pt)
#set par(justify: true, leading: 0.7em, spacing: 0.75em)
#set list(indent: 1.1em, body-indent: 0.5em)
#set enum(indent: 1.1em, body-indent: 0.5em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 14.5pt)
#show heading.where(level: 2): set text(size: 11.5pt)
#show heading.where(level: 3): set text(size: 10.5pt)
#show math.equation: set text(font: "New Computer Modern Math")
#show link: set text(fill: rgb("#1f5d8f"))
#show raw.where(block: true): set block(fill: rgb("#f5f6f7"), inset: 9pt, radius: 4pt, breakable: true)
#show table: set block(breakable: true)
#set table(inset: 4.5pt, stroke: 0.35pt + luma(70%))
#let argmin = math.op("arg min", limits: true)

#align(center)[
  #text(size: 18pt, weight: "bold")[构想梳理 v2]
  #v(3pt)
  #text(size: 14pt)[溯源、四条线、两处同名异义、一个已经存在的反驳]
  #v(8pt)
  #text(size: 9.5pt)[2026-09-30 · 仓库 `HEAD = cbf6c57a`（本文提交前）· 分支 `main`（本地，*无 remote*）]
  #v(2pt)
  #text(size: 9.5pt)[被梳理对象：`related_files/` 语料（25 个跟踪文本文件）＋ `a0/` 九份报告 ＋ 一个 ChatGPT 分享链接的完整载荷]
  #v(2pt)
  #text(size: 9.5pt)[阅读方式：*§0 摘要 → §1 溯源（v2 的新增基础）→ §6 只有交叉阅读才能发现的问题 → §8 未决决策*]
]

#v(8pt)

#block(stroke: 0.5pt + luma(60%), inset: 9pt, radius: 4pt, breakable: true)[
*v1 → v2*：v1 只读了语料与 `a0/`，把 `Pasted markdown.md` 当作 D 线的最新产物。*这个归因是错的。* v2 解码了分享链接的 11 MB 载荷，发现该对话（4011 节点、09-17→09-24）产出了语料的大部分，但*没有*产出 `Pasted markdown.md`，也没有产出那份独立审查——它们来自另一条对话。v2 因此新增 §1（溯源）与 §6.2–§6.5、§6.7，并修订 §2 的 A 线定性与 §6.5 的「不可合并」结论。v1 中被推翻的部分集中列在 §6.8。

*标注约定*：【我复核】= 我亲自读了原文或亲自算过；【二手】= 只读调查者给的 `path:line`，我未逐条核对；【推断】= 我的判断，不是文档原话。完整分级见 §9。
]

= §0 摘要

+ *构想的脊柱是你的 46 个提问，不是模型产出的文档。* 四次转向都由你先说出：代理目标谬误（\#11，09-17）、「open problems must in open world」（\#18，09-18）、把 $H_O$ 降为前提改问时机（\#26–27，09-23）、三重困难分解（\#28，09-23）。文档是这些提问的沉淀物。
+ *语料有三个来源，混在一个目录里*：你自带的输入（A 线，09-09/09-14）、这条对话的产物（B/C 线与 D 线的正式报告）、以及*另一条对话*的产物（`Pasted markdown.md` ＋ 那份独立审查）。见 §1.3。
+ *审查最硬的一击，其反驳材料已经存在，但放在两个永不相遇的地方。* 审查要求「公布 Monte Carlo 生成器、种子、置信区间」；`agent_engineering_science_report.tex:415` 已经写了 seed 42、每点 150000 trials。我独立复算：该报告的 `exp1` 数据与审查自己构造的 β-二项反例模型*在 36 个格子上最大偏差 0.331 pp*（150k 样本的 SE ≈ 0.118 pp），即 *exp1 就是那个可交换模型*。而被审查的 `Pasted markdown.md` 的表在 $rho=0.7$ 三格上偏离同一模型 6.5–9.2 个 SE。⇒ *两个文档描述的是两个不同的模拟。* 见 §6.3。
+ *两处同名异义*，都只有交叉阅读才能看到：$rho$（D 线 = agent 间错误相关性；`a0/` = assay 动态范围，明文限定为仪器属性）见 §6.1；`RQ1–RQ5`（C 线 RQ1 = Recoverability、RQ2 = decision-sufficient state；D 线 RQ1 = *Decision-Sufficient State*）见 §6.2。
+ *后继文档违反了前驱文档的明文免责。* `report.tex:415`：「所有模拟均为机制示例，不应被引用为真实 LLM Agent 的性能证据」；`Pasted markdown.md:1149` 却把「我们 sandbox experiment」列为 L1 的支持证据。见 §6.4。
+ *`a0/` 侧状态未变*：门 `ADMISSIBLE`（Δ 0.116584858、$rho$ 0.615639328、4/4 族），但 $R_"A1"^"main" = emptyset$ ——一个 campaign 都没跑过；泄漏未修；机制 A 未接线。见 §4。

= §1 溯源：这个分享链接是什么

链接：#link("https://chatgpt.com/share/6ab4c8dd-40b0-83ee-bd93-3eecc4c4b97f")

== 1.1 载荷的规模与形状

`web_fetch` 因超过 10 MB 上限失败。改用 `curl --compressed` 得到 2.4 MB 传输 / 11.2 MB HTML，其中是 React Router 的 turbo-stream 载荷：一个 *148184 元素的扁平数组*，字典值 100% 是索引（427228 个，无一例外），键去重后每个只出现一次，`-5` 是唯一的 null 提示，末尾一个 `P148179` promise 占位符。解码后得到 `loaderData.routes/share.$shareId.($.serverResponse.data.mapping`，*4011 个节点*。

#table(
  columns: (auto, 1fr),
  table.header([量], [值]),
  [节点], [*4011*（根 1 个，*分叉 0 个*，链长 4011 = 全部节点，即完全线性）],
  [角色], [user 61（46 个有正文）、assistant 1305、tool 2354、system 290],
  [内容类型], [assistant/text 934、tool/text 2313、assistant/thoughts 194、assistant/code 108、reasoning_recap 51、execution_output 41、model_editable_context 18],
  [时间跨度], [*2026-09-17 08:46 → 09-24 07:36 UTC*（= 本地 16:46 → 15:36）],
  [字符串总量], [2 864 505 字符],
  [已知截断], [*6 个字符串恰为 20000 字符*——tool 输出在分享载荷里被截断到 20k],
)

== 1.2 你的 46 个轮次是构想的脊柱

#table(
  columns: (auto, auto, 1fr, 1fr),
  table.header([\#], [时间 (UTC)], [你说的], [后果]),
  [1–6], [09-17 08:46→09:35], [Kimi Code 有没有插件市场 → 三次「\@GitHub 深入调查」], [生态调查],
  [*7*], [09-17 09:35], [「终究我们是要做实际的项目，而不是基础设施……正交组合应该是最合适我们的」], [*货架式/正交组合方针*],
  [8], [09-17 09:39], [「这个工作我在 opl 那个压缩包里面 doc/sections/ 里面应该有做过」], [⇒ A 线文档是*你自带的输入*],
  [*11*], [09-17 09:48], [「你也没必要纠结于要实现或者改进 ada 或者 opl 了，*这会陷入代理谬误*……货架式方案能满足目的就尽量减少工作」], [*A 线降级由你先说出*，比 `open_world_...plan.typ:53` 的书面化早约一天],
  [12], [09-17 09:51], [「不要等待我的反馈，不要留下你的设想，尽可能验证设想……推进到当前帕累托前沿」], [自主推进方针],
  [13], [09-17 09:53], [「我们的研究方向是算法改进……使用 typst 给出正式工程方案」], [→ `algorithm_research_infrastructure_plan.typ`],
  [*17*], [09-18 02:47], [「这些框架中，有没有涉及真实研究中*搜索已有实现*的环节呢？……我们优化算法过程的搜索空间不应该只是理论构建，而应该还有互联网能触及的所有经验」], [*开放世界这条线的起点*],
  [*18*], [09-18 02:54], [「*open problems must in open world*，保证两个 open 是正确研究的关键」], [该口号是你的，不是模型的],
  [21–22], [09-18 06:05→06:16], [「仔细深入源码」→「写一个完整的工程计划……typst 格式正式计划」], [→ `open_world_algorithm_research_engineering_plan.typ` + `refs.bib`],
  [23–25], [09-18 08:09→08:45], [「你也要保持独立性思考这份审查意见」/「源码都是公开的，你应该自己去审查确认」/「修正后的审查意见，希望你给出独立审核」], [→ `open_world_plan_independent_review.typ` 共 *7 个版本*，最后 → `open_world_plan_review.typ`],
  [*26*], [09-23 02:09], [「我隐约感觉有一种矛盾，如果已知目标任务可以改善，存在上限，这个先验信息本身就是很不平凡的，从而可以驱使 agent 不依赖外部资料就优化到几乎上限……第一性原理，深入思考」], [*$H_T$ pivot 的真正起点*],
  [*27*], [09-23 06:07], [「我认为可以*直接假设，从外部获取信息是有价值的，只是这个时机的判别不好确定*」], [这就是 $H_T$，早于 `TIMING-REVIEW.md`（09-23）],
  [*28*], [09-23 07:40], [三重困难 ＋ 三类已知解法（全文见下）], [→ C 线 `research_state_control_review` v1–v4],
  [31], [09-23 08:47], [「只在……确定必须要停下等待我人类反馈的时候才停止……*第一性原理，make no mistakes*」], [⇒ `AGENTS.md` 的三条 MUST 来自你实际的提示词],
  [32–33], [09-23 09:13→09:16], [头部预测 vs 多步/结构预测的分工；「要坚持从我们的主问题出发」], [C 线的预测章节],
  [35–38], [09-23 10:57→09-24 03:02], [「\@GitHub 仔细检索 `topics/agentic-ai`……用更多次数弥补单次检索的不足」], [主题化检索轮],
  [*39–40*], [09-24 03:11→03:20], [内燃机与飞机的比喻；「有发动机的飞行器，也不一定要有翼」；*「我的本科是导弹导引控制，所以也有系统学习过航空学」*], [⇒ 全部航空工程框架（operating envelope、stall、风洞、气动导数辨识）的来源是你本人的训练],
  [41], [09-24 04:39], [「从 agent 工程学出发，你目前会得出怎样的理论框架……迫切的理论需要，工程实际？」], [→ 17657 字符的回答],
  [42–46], [09-24 04:57→07:36], [「做严谨的学术研究……最终形成 latex 报告」＋三次「继续追下去，必须要做的实验在你的沙箱里做」], [→ `agent_engineering_science_report.tex` + `.bib` + 3 个 CSV + 3 张图 → `repro_bundle.zip`],
)

表内「」是原文片段，`……` 是省略，*粗体*是我加的强调、不是原文格式；只有下面单独引出的 \#28 全文是未加强调的逐字。表中只列承重的轮次，46 个有正文的 user 轮次里其余多为「继续深入」「\@GitHub 继续追下去」一类的推进指令。

#quote(block: true)[
*轮次 \#28 全文（C 线的种子，逐字，未加任何强调）*：总的来说，我认为我们目前遇到的主要困难有三重：1.检索困难，别说整个互联网了，稍微复杂一些的带 git 的大型代码库中，要对某个不断调整的功能进行历史检索都很困难 2.时机困难：实际上包含两个子问题，即对现状的结构化判别和对未来的结构化预测建模 3.历史处理困难，对于不断增长的 agent 轨迹、调用、swarm、subagent，还有成果和 git，目前没有系统化整理，导致系统熵不断增加，强化了 1 类问题。目前已知的解决结构大概如此：1.IAC=infrastructure as code，也就是 code 化的约束，像 json、数据库之类的，能幂等执行的硬约束，2.各类 md 中的 SOP，交由 agent，但是随指令依从度和 agent 环境工具而不确定，软约束 3.人类判别，由超长程经验→理论→直觉化→改善理论这样的反馈所制造的所谓 "taste"，human in the loop 至少如今仍是不可或缺。
]

== 1.3 语料的三个来源类别

#table(
  columns: (auto, 1fr, 1fr),
  table.header([类别], [文件], [判据]),
  [*你自带的输入*（对话只读取，从未写入）], [`adapdc_*`×4、`deep-research-report*.md`×3、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`、`rule-construction-research*.md`×2、`virtual_staining_*`], [这些名字只出现在 *tool 消息*里（09-18 08:46 起），且都是被截断到 20000 字符的读取；`/mnt/data` 写入清单里*没有*它们。\#8 明确说来自「opl 那个压缩包」],
  [*这条对话的产物*], [`algorithm_research_infrastructure_plan.typ`(09-17 09:54)、`open_world_algorithm_research_engineering_plan.typ`+`refs.bib`(09-18 06:17)、`open_world_plan_independent_review.typ` 及 `(1)`–`(6)` 共 7 版(09-18 08:09→09-20 07:15)、`open_world_plan_review.typ`(09-20 07:15)、`STATUS(1).md`/`STATUS(2).md`/`CONVERGENCE-2026-09-21.md`(09-21)、`research_state_control_review{,-v2,-v3,-v4}.tex`+四份 `.bib`(09-23 08:10→09:33)、`agent_engineering_science_report.tex`+`references.bib`+3 CSV+3 图(09-24 05:02→05:04)], [*32 个不同的 `/mnt/data` 路径*，全部由 assistant/tool 写入],
  [*另一条对话的产物*], [`Pasted markdown.md`、`agent_engineering_science_independent_review_2026-09-24.md`], [四个探针全部 *0 命中*：「原报告之后的下一层问题」、「重大修改后作为研究纲领发表」、`betabinom`、`SILO-BENCH`。而 `SILO-BENCH` 是 D 线全部论证的证据基础——它在这条对话的 2 864 505 字符里一次都没出现],
)

⇒ *D 线其实是两条对话*：这条对话产出正式报告（七个理论域 $T_1$–$T_7$、RQ1–RQ5、沙箱实验 A/B/C），另一条对话产出 `Pasted markdown.md`（把 $T_1$–$T_7$ 明确贬为「仍然偏 taxonomy」，改为三层框架与 L1–L7）与那份独立审查。`Pasted markdown.md` §19 的「上一版：$T_1,…,T_7$」正是对 `report.tex` 的指涉，所以*时序是 report.tex(13:03) → Pasted markdown(15:30) → 审查(15:30)*，与三个文件的 mtime 一致。

== 1.4 语料里缺的东西（可恢复）

#table(
  columns: (1fr, 1fr, auto),
  table.header([缺], [状态], [可否恢复]),
  [`research_state_control_review_v2.tex`、`_v3.tex` + `refs_v2/v3.bib`], [对话里存在（`_v2` 20 次命中），语料只有 v1 与 v4], [*可*，从载荷提取],
  [`open_world_plan_independent_review(1)`–`(6).typ`], [语料只有 1 份，对话里有 7 版], [*可*],
  [`agent_engineering_science_report.tex`(31503 B) + `references.bib`(6642 B)], [*只存在于未跟踪的 zip 里*], [已解出],
  [`exp1/2/3_*.csv` ＋ 3 张图], [同上], [已解出],
  [`STATUS(1).md`、`STATUS(2).md`], [进了 `a0/STATUS.md`，未在 `related_files/`], [需比对],
)

⇒ *D 线唯一的实测数据（三个 CSV）在 git 里完全不存在*：zip 被 `.gitignore` 白名单排除（这是你的决定，「pdf 和 zip 都不要」）。这条排除的代价在 v1 里没被看见——被排除的不只是一个压缩包，是 D 线全部的可复现证据。

= §2 四条线（v2 修订）

#table(
  columns: (auto, 1fr, auto, 1fr),
  table.header([线], [文档], [日期], [v2 状态]),
  [*A 编排基础设施*], [`adapdc_*`、`deep-research-report*.md`、`ada-/opl-engineering-plan.typ`、`algorithm_research_infrastructure_plan.typ`], [09-09 → 09-18], [*你自带的输入 ＋ 你在 \#11 主动降级*。前几份不是你写的，是 opl 压缩包里的既有工作；只有最后一份是对话产物],
  [*B 开放世界计划*], [`open_world_..._plan.typ` + 7 版独立审查 + `open_world_plan_review.typ`], [09-18 → 09-20], [`open_world_plan_review.typ` §4 是 `a0/` 的*协议权威*（外部、只读、不在本仓库内）],
  [*C 研究状态控制*], [`research_state_control_review{,-v2,-v3,-v4}.tex`], [09-23（一天内四轮）], [第四轮*否定了自己的线名*，改为「Long-horizon research as an epistemic organization under partial observability and bounded resources」],
  [*D 多智能体信息整合*], [`agent_engineering_science_report.tex`(zip) → `Pasted markdown.md` → 独立审查], [09-24（一天内三跳，跨两条对话）], [审查裁决「重大修改后作为研究纲领发表」],
  [*— 落地实现*], [`a0/` 九份报告], [09-21 → 09-23], [测量链建成，*$R_"A1"^"main" = emptyset$*],
)

*v1 的定性错误*：v1 说 A 线「自己废弃」，并把理由归给 `open_world_algorithm_research_engineering_plan.typ:53`。该引文属实【我复核，逐字】：

#quote[本项目最初从「研究过程运行契约、Agent 长程执行、实验编排、记忆、插件、范畴论式关系建模」等基础设施问题出发，曾分别形成 ADA（环境侧）与 OPL（Kimi Code Agent/插件侧）的实现设想。随后研究逐步暴露出一个代理目标风险：若持续优化 ADA/OPL 自身，目标会从「提高真实研究能力」漂移为「提高基础设施完整度」。]

但*降级决定是你在 \#11（09-17 09:48）先做出的*，比计划文档写下它早约 20 小时。这不是措辞差别：它意味着 A 线的废弃不是文档演化出来的结论，而是一个先于文档的判断。同一条线的自我约束还有 `algorithm_research_infrastructure_plan.typ:15`「本方案不以 ADA、OPL、Kimi 插件或某个 'Research OS' 为目标」、`:318-319` 的 do-not-build 清单（含「自有通用 Research IR」「自有 workflow engine」）、`:33` 的优先级序 `reuse > configure > compose > adapt > extend > build`【二手】。

= §3 理论侧（D 线）的当前位置

== 3.1 三跳，不是两跳

#table(
  columns: (auto, 1fr, 1fr),
  table.header([跳], [产物], [结构]),
  [1], [`agent_engineering_science_report.tex`（本对话，13:03）], [标题《从 Agent 架构到 Agent 工程科学：状态、观测、资源分配、认识论动力学与系统辨识的理论框架》。*七个理论域 $T_1$–$T_7$*（观测/动力学/资源分配/认识论动力学/协调拓扑/可靠性恢复/系统辨识）＋三个中层理论（Adaptive Observability、Epistemic Stability、Agent Similarity/Regime Theory）＋Credit Assignment 与 Evaluator 两个瓶颈＋RQ1–RQ5＋「Agent Wind Tunnel」＋八行实验矩阵],
  [2], [`Pasted markdown.md`（另一对话，15:30）], [明确贬 $T_1$–$T_7$「仍然偏 taxonomy」，改为*三层*（Layer I 信息物理 / Layer II 计算动力学 / Layer III 元控制）＋*五段分解*（生成→传递→整合→验证→决策）＋ $chi = R_O / R_I$ ＋ *L1–L7* ＋ 中心对象改为 *Epistemic Bandwidth Allocation*],
  [3], [独立审查（15:30）], [七条 L *没有一条以当前形式成立*；数值不可复现；2×2×2 缺 N 因子 ⇒ $partial J / partial N$ 不可识别],
)

核心命题（第 2 跳）：*InformationAcquired $arrow.r$ InformationIntegrated*，证据是 SILO-BENCH（30 任务、54 配置、1620 次实验，Level III 在 N>50 后成功率为零）。*注意：`SILO-BENCH` 在本对话载荷里 0 命中*——D 线的整个证据基础是在另一条对话里建立的。

== 3.2 七条 L 的裁决（审查逐条）

#table(
  columns: (auto, 1fr, 1fr),
  table.header([], [命题], [裁决]),
  [L1], [$"Gain"_"ensemble" prop N_"eff" != N$], [*不成立*。等相关同方差也有不同多数票成功率。可保留为等相关*均值估计的方差恒等式*],
  [L2], [$R_O > R_I$ ⇒ 边际价值递减/为负], [*负边际价值非一般结论*。可零成本忽略且策略集含旧策略时 $V(O,"new") >= V(O)$。可改写为队列假说 $Q_(t+1) = [Q_t + A_t - S_t]^+$],
  [L3], [$C_T > C_A$ ⇒ 崩溃], [*未可操作化*。同单位/同边界/同错误准则缺失；若 $C_A$ 事后定义为「系统可解上界」则同义反复],
  [L4], [DecisionRelevantContext > RawHistory], [*表达式无定义*。RawHistory 包含由它算出的任何摘要],
  [L5], [$"Value"("Generation") = f("VerifierQuality")$], [*不可证伪*],
  [L6], [$rho_(t+1) = f(rho_t, G, C, "EvidencePolicy")$], [*无动态律*。$f$ 的形式与观测定义都缺],
  [L7], [$exists B^* < oo: U(B^*) = max_B U(B)$], [*需明确成本与目标*。若 $B$ 只是可用预算，$V(B) = "sup"_("cost" <= B) E["reward"]$ 可单调上升仅渐近逼近上界],
)

审查建议的标题：《分布式 Agent 的信息整合瓶颈：证据审查、不可识别性与系统辨识实验纲领》。

== 3.3 `report.tex` 的八行实验矩阵（本对话产物，v1 未见）

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  table.header([实验], [自变量], [因变量], [混杂控制]),
  [Context exposure], [full/summary/evidence-only/blinded], [success, error correlation, cost], [same model/task/budget],
  [*Retrieval timing*], [*never/fixed/adaptive*], [*regret, search cost, recovery*], [*frozen corpus/evaluator*],
  [Verification ratio], [$Pi_V$ sweep], [success, false acceptance, cost], [same generator pool],
  [Breadth-depth], [$Pi_"BD"$ sweep], [best score, diversity, latency], [fixed total compute],
  [Fault injection], [$lambda$ sweep], [recovery rate/time], [fixed tool semantics],
  [Stale-memory injection], [stale fraction/age], [wrong-action rate], [known ground truth],
  [False-claim propagation], [qualification policy], [$R_e$, time-to-correction], [known seeded false claims],
  [Evaluator drift], [evaluator version], [rank reversals, policy shift], [anchor suite],
)

*第 2 行就是 `a0/` 的 `B0a`/`B0b`*，而 `report.tex` 写于 09-24、`TIMING-REVIEW.md` 写于 09-23。⇒ 两条线在相隔一天、互不引用的情况下提出了同一个实验；*`a0/` 已经把它做到了「仪器就绪、campaign 未跑」的程度，而 D 线只有一行表格。* 详见 §6.5。

= §4 落地侧（`a0/`）的当前位置

状态与 v1 相同，此处只列承重项（全部【我复核】，出自 `a0/STATUS.md`、`a0/A1-RESULT.md`、`a0/TIMING-REVIEW.md`）。

- *A−1/A0.1/A0.2 完成并通过独立对抗审计*：31 条 claim = 27 ACCEPTED / 3 REJECTED / 1 UNPROVEN；被驳回的 R1 是*计算器自身的假通过漏洞*（conformance 只比 `status`、从不读 `failure.kind`，一个「status 诚实、`failure_kind` 全错」的 adapter 返回 PASS）。
- *A0.1 是三元组 `(passed, measured, total)`，不是布尔*：EvE 的 lane 把评测异常静默映射为 `failure_score 0.0`，*无法表达 `invalid`/`error`*，正确引法是 `5/14 measured`。
- *A1 门 `ADMISSIBLE`*（k=10 契约修订后）：Δ = 0.116584858、$rho$ = 2417/3926 = 0.615639328、4/4 族；阈值 0.03/0.02/0.30 一字未动。09-23 四个互不相通的验证者独立重导 12 个判定字符串与 2160 个决策叶，*0 分歧*。
- *k=10 是后验自由度，已诚实登记*：看到 $rho$ 失败之后才选定，写成显式契约修订（`positive_control/PC-REVISION.md`），且 $rho$ 被限定为 `evidence_scope: instrumentation`、「MUST NOT 被当作关于世界的证据」。
- *$R_"A1"^"main" = emptyset$*：第 8 项未运行。阻塞已从「任务未准入」变为「agent 侧隔离未接线 ＋ 未跑过一次约 30 分钟真实长会话」。
- *泄漏未修*：`coding_agent` 是 `danger-full-access` 且出站 TCP 可达；拟用 packet 在工作区有 4 条可读路径（2 条被 git 跟踪）。⇒ *`web_search: false` 关的是工具不是 TCP，「封闭臂」今天不存在*，`Retrieve@never` 臂会让 agent 在 t=0 读到答案。
- *三个门*：见下。$G_1$/$G_2$ 对 k=10 已量过、不花钱；*$G_3$ 完全没测*。
- *主估计量*（去掉了人为 $lambda$）：见下。
- *第一代策略只用三个 harness-authoritative 量*：$hat(r)_t$（窗口生产率）、$ell_t$（距上次改进的成本）、$b_t$（剩余预算）。无 embedding、无 agent 自评、无 LLM judge。
- *novelty 收窄到三层*：不是「外部知识有用」（DeepEvolve 已示），不是「何时检索」（ReaLM-Retrieve 已在 QA 示：检索 −47%、F1 +10.1），而是*长程算法发现中的一次性不可逆获取 ＋ 离线量测的 packet ＋ 冻结预算下的策略价值差 ＋ state 取自 verified-progress trace*。
- *最重的风险*（`TIMING-REVIEW.md` §4.3【我的补充】）：T1 的机制空间是 Max-Cut 启发式，*预训练最密集的一类*；该风险在选任务时被写下，却*没有进入任何冻结工件*（`memoriz`/`记忆` 检索项目自身文档无命中）。⇒ $G_3$ 可能结构性地无法通过，而*换载体的代价（新套件、新 $E^*$、新门、新标定）没有计入成本表*。
- *成本*：$B_"hard" = (1800 s, 1 966 519 "CEq", 725 "calls", P=1)$；墙钟是主约束（`CEq_max/q_r` = 37.50/92.22 min 都晚于 30 min）。$N=40$ → 20 h / ≈\$20，$N=136$ → 68 h / ≈\$70。*`R=10/16/34` 不在仓库里*；`R=4` 的 ≥3/4 判据在真值 0.5 时通过率仅 31.25%。

$ G_1: J_X - J_0 >= delta_"artifact" quad G_2: rho_X = (R - J_X) / (R - J_0) >= rho_min quad G_3: Delta_X^"agent" = E[Y_(X,0) - Y_(X,oo)] >= delta_"agent" $

$ V_B (pi) = E[J_"best" (B; pi) - J_0], quad Delta_T = V_B (pi_"adaptive") - max_(pi in Pi_"fixed") V_B (pi) $

$ pi_(theta,k): "Retrieve" <=> hat(r)_t < theta and ell_t > k and b_t > C_"min" $

= §5 交叉：概念在哪条线里存在

三个只读调查者各自 grep；`N_eff` 那一行与全部 §6 的引用我亲自复核。

#table(
  columns: (1fr, auto, auto, auto, auto, auto),
  table.header([概念], [A 编排], [B 开放世界], [C 状态控制], [D 多智能体], [`a0/` 落地]),
  [*Decision-Sufficient State*], [*命题 1*（`adapdc_theory_review.typ:198`）], [缺], [*RQ2*（`v4.tex:1550`）], [*RQ1*（`report.tex:304`）；`Pasted md` §9], [隐含于 $s_t$],
  [$H_t$ vs 工作上下文 $S_t$], [缺], [缺], [显式分层 L₀–L₄、$K_t = C(g_t, S_t, E_t, R_t, B_t, r)$（`v4.tex:1353`）], [§8 `History≠WorkingContext`], [$H_t^E = {(c_i, J_i)}$],
  [*干预时机*], [缺], [$Q_2$（`plan:80`）], [经 prescriptive process monitoring（`v4.tex:745-753`）], [§16–17；`report.tex` 矩阵第 2 行], [*主轴 $H_T$*],
  [Value of information], [缺], [缺], [VOI/VOC/VOH（`v1:290-294`、`v4:771-775,1079`）], [§17], [rational metareasoning（§2.8a）],
  [*整合效率 / `N_eff` / 相关 agent*], [*缺*], [*缺（0 命中）*], [*缺（0 命中）*], [*中心*], [*缺*],
  [*航空工程框架*（envelope/stall/风洞/气动导数）], [缺], [缺], [缺], [*`report.tex`「Agent Wind Tunnel」、`Pasted md` §21「风洞实验」*], [缺],
)

*读法一*：*DSS 是唯一贯穿四条线的概念，最早的数学形式在 A 线。* `adapdc_theory_review.typ:198`【我复核，逐字】：

#quote[命题 1（决策充分表示的有限情形充要条件）。存在仅依赖 $q_t (h)$ 的最优决策规则，当且仅当对每个非空表示纤维满足 $inter.big_(h: q_t (h) = z) A_t^star (h) != emptyset$。]

四处定义互不引用：A 线的纤维交集条件、C 线的 $Delta_B (phi) = R_B (phi) - R_B ("identity")$、D 线的 $argmin |S| "s.t." "Regret" <= epsilon$、`a0/` 的三量 $s_t$。*A 线那个是唯一被证明过的*（有限情形充要条件，附证明），而 D 线 §9 说 DSS「不再只是我们的理论猜想」时没有引它。

*读法二*：*D 线的独有概念在其他四条线里 0 命中*，而*航空工程框架只在 D 线出现*。结合 \#39–40，这个框架来自你的导弹导引控制背景，是你带进 D 线的，不是从文献里长出来的。⇒ 它是 D 线的*方法论承诺*（先做系统辨识、找 regime boundary、构造无量纲量），不是装饰。这也解释了 `report.tex` 为什么有「Agent Wind Tunnel」一节。

*读法三*：*B 线实现了「获取 vs 整合」的分裂但没用这两个词*：`rev:258-259,485-486` 的 $H_A$ vs $H_O$，`rev:641` 的 $Delta_O approx Delta_"discovery" + Delta_"resolution" + Delta_"transfer" - C_"acquisition"$【二手】。这是 D 线核心命题更早、更操作化的版本，两边都没指出。

= §6 只有交叉阅读才能发现的问题

== 6.1 $rho$ 同名异义（v1 已提，仍成立）

#table(
  columns: (auto, 1fr, 1fr),
  table.header([], [D 线的 $rho$], [`a0/` 的 $rho_X$]),
  [定义], [agent 间*错误相关性*], [$(R - J_X)/(R - J_0)$，*assay 动态范围*],
  [性质], [关于世界的量], [*仪器属性*，`evidence_scope: instrumentation`],
  [明文限制], [无], [「MUST NOT 被当作关于世界的证据」（`PC-REVISION.md:165-166`）],
)

审查最硬的数学结论针对前者，但措辞看起来像批评任何用 $rho$ 的推断。

== 6.2 `RQ1–RQ5` 同名异义【我复核，v2 新增】

#table(
  columns: (auto, 1fr, 1fr),
  table.header([], [C 线 `v4.tex:1547-1561`], [D 线 `report.tex:304-335`]),
  [RQ1], [*Recoverability*], [*Decision-Sufficient State*],
  [RQ2], [*Decision-sufficient state*], [*Adaptive Observability*],
  [RQ3], [Foresight and resource rationality], [Epistemic Stability],
  [RQ4], [Organizational learning], [Resource Allocation],
  [RQ5], [—（无）], [Similarity Laws],
  [依赖], [RQ1 → RQ2 → RQ3，RQ4 并行且纵向；RQ1 FAIL 则复杂历史结构不值得], [未声明依赖],
)

相隔一天（09-23 09:33 / 09-24 05:03），*同一个概念 DSS 在两边分别是 RQ2 和 RQ1*。任何合并写作都会产生错误的交叉引用。⇒ 建议加前缀（`SC-RQ*` / `AES-RQ*`）。

== 6.3 exp1 就是审查构造的那个反例模型【我亲自算过，v2 新增，本节最重要】

审查说原表「未给出相关 Bernoulli 联合分布的生成方法、随机种子、置信区间、原始样本或脚本」，并构造 β-二项反例（$Theta tilde Beta(a,b)$，$a = p(1/rho - 1)$、$b = (1-p)(1/rho - 1)$，条件独立）。我用 SciPy 独立复算，*逐位重现了审查表格里的每一个数*（.836920 / .992179 / .744250 / .767641 / .705736 / .707613 / .700716）——审查的算术是对的。

然后把它与 zip 里的 `exp1_correlated_ensemble.csv`（36 格，$rho in {0,.05,.1,.2,.4,.7}$ × $N in {1,3,5,9,17,33}$）对齐：

#table(
  columns: (1fr, 1fr),
  table.header([对比], [结果]),
  [CSV vs β-二项精确概率], [*最大偏差 0.331 pp*（36 格中 $N>=3$ 的最坏格）。`report.tex:415` 说每点 *150000 trials* ⇒ SE ≈ 0.118 pp ⇒ 最坏 2.8 SE，36 格下的期望最大 $|z|$ 本就约 2.5–3 ⇒ *完全一致*],
  [`N_eff` 列], [与 $N / (1 + (N-1) rho)$ 逐格吻合到 4 位小数],
  [*`Pasted markdown.md` 的表 vs 同一模型*], [$rho=0.7$：.723/.730/.732 对 .70574/.70728/.70761 ⇒ 偏 *1.73/2.27/2.44 pp*；按其自称 30000 次 ⇒ SE 0.265 pp ⇒ *6.5/8.6/9.2 个 SE，不相容*],
  [$rho$ 网格], [`Pasted md` 有 `.3` 与 `.9`，CSV *完全没有*这两行；CSV 有 `.05/.1/.2/.4`，`Pasted md` 没有],
  [重合且一致的格子], [只有 $rho=0$ 三格（.838/.961/.992 对 CSV .83735/.95943/.99259）],
)

⇒ *结论：`report.tex` 的 exp1 与 `Pasted markdown.md` 的表是两个不同的模拟。* 前者是可交换 β-二项（审查的反例模型本身），后者用了别的生成器且没有记录。审查的 5.2 pp 攻击（$rho=.3, N=33$：.820 对 .76764）*只对后者成立*——而 $rho=.3$ 那一行在 exp1 里根本不存在，所以审查打的确实是对的目标，它没有误伤。

⇒ *可执行的后果*：审查要求「公布生成器、种子、置信区间」，其中*种子与样本量已经在 `report.tex:415` 里*（NumPy RNG seed 42；A 每点 150000 trials、B 每格 25000 problems、C 每级 10000 queries），只是那份文件在*未跟踪的 zip* 里，而被审查的文档在*另一条对话*里。两者从未相遇。生成器仍未写明——但我的复算表明它是可交换 β-二项，这一点可以作为回应审查的证据提交（并需要附上脚本才完整）。

== 6.4 后继文档违反前驱文档的明文免责【我复核，v2 新增】

- `report.tex:415`：*「所有模拟均为机制示例，不应被引用为真实 LLM Agent 的性能证据。」*
- `Pasted markdown.md:1149`（L1 的支持证据）：*「已有 ensemble 理论 + 我们 sandbox experiment + debate diversity 结果支持。」*

⇒ L1 把 sandbox experiment 当作支持，而该实验的原始报告明文禁止这样引用。审查对 L1 的裁决（「不成立」）因此*比它自己给出的理由更强*：即使 `N_eff` 的数学问题能修，L1 也还缺一个合法的证据来源。

== 6.5 「不可合并」要改写成「不对称」【v2 修订 v1 的 §5.2】

v1 说两条线的 estimand 不可合并。这部分仍然对，但漏了一半：

#table(
  columns: (auto, 1fr, 1fr),
  table.header([], [`a0/` 的 `B0a`], [`report.tex` 矩阵第 2 行]),
  [因子], [$tau/B in {0,.2,.4,.6,.8,oo}$，单因子], [never/fixed/adaptive，三档],
  [agent 数], [1], [1（矩阵未涉多 agent）],
  [estimand], [$g(tau) = E[Y(tau) - Y(oo)]$], [regret, search cost, recovery],
  [混杂控制], [冻结 $E^*$、$B_"hard"$、$C^*$], [frozen corpus/evaluator],
  [*成熟度*], [*仪器就绪*：门已 `ADMISSIBLE`、$B_"hard"$ 已冻结、编排骨架 dry-run 25/25、两臂注入已实测；缺 campaign], [*一行表格*],
)

⇒ 正确的表述不是「两个独立 estimand」，而是：*D 线在 09-24 提出了八行实验矩阵，其中第 2 行正是 `a0/` 在 09-23 已经建好仪器的那一个；其余七行 `a0/` 完全没有对应能力。* 所以两条线的关系是*一行重叠、七行空白*，而不是平行。这一条 v1 完全没看到，因为 v1 不知道 `report.tex` 存在。

同时 v1 的另一个结论仍成立：D 线审查要求的四因子设计（$N in {2,5,10,20}$ × 相关 × 聚合器 × 验证）*不在*这八行矩阵里，也不在 `a0/` 里。它是第三个实验。

== 6.6 样本量推理的同类错误（v1 §5.3，仍成立，补一例）

- `a0/`：`R=10/16/34` 不在仓库里；`R=4` 的 ≥3/4 判据在真值 0.5 时通过率 31.25%；`P_recover` 是比例，`R=4` 估不准（`TIMING-REVIEW` §4.2 已自认）。
- D 线：`N_eff` 是*等相关均值方差*的等效样本数（$"Var"(bar(Y)) = p(1-p)[1+(N-1)rho]/N$），*不决定多数票胜率*。
- *v2 补充*：`report.tex` 给了 trials 数（150000/25000/10000）但*没有给置信区间*，`Pasted markdown.md` 给了 30000 也*没有给区间*——所以 §6.3 里那个 6.5–9.2 SE 的不相容，是我算出来的，两份文档都没有能力自己发现。

⇒ 同一个错误家族：*把方差尺度的量当成推断力的量，且不报区间。*

== 6.7 exp2 与 exp3 的两个缺陷【我亲自算过，v2 新增】

*exp2*（`exp2_metareasoning.csv`，5 budget × 2 policy）：

#table(
  columns: (auto, 1fr, 1fr),
  table.header([budget], [fixed_equal：regret / samples / net_util], [adaptive：regret / samples / net_util]),
  [5], [0.5224 / 5.0 / 0.5178], [0.5288 / 5.0 / 0.5119],
  [10], [0.3655 / 10.0 / *0.5476*], [0.3310 / 10.0 / *0.5866*],
  [20], [0.2300 / 20.0 / 0.4322], [0.2021 / 17.49 / 0.5131],
  [40], [0.1325 / 40.0 / 0.0237], [0.1678 / *19.69* / 0.5106],
  [80], [*0.0754* / 80.0 / *−0.9180*], [0.1663 / *19.65* / 0.5101],
)

- *L7 的形状确实在数据里*：fixed 的 net utility 在 budget 10 达峰（0.5476），到 80 变负（−0.9180）。这是「$exists B^* < oo$」的直接机制示例。
- *但 adaptive 的 `mean_samples` 在 budget ≥40 后钉死在 ≈19.7*，regret 也钉死在 ≈0.166；fixed 的 regret 一路降到 0.075。⇒ *这个 adaptive 策略对预算不敏感*：给它 4 倍预算它也不多用。所以 exp2 证明的不是「自适应更好」，而是「在成本线性计价下，早停的策略净效用更高」。审查对 L7 的要求（「需明确成本与目标」）恰好命中这一点。

*exp3*（`exp3_temporal_retrieval.csv`，6 个噪声级）：

#table(
  columns: (auto, 1fr, 1fr),
  table.header([semantic_noise], [flat_retrieval], [temporal_projection]),
  [0.05], [0.4557], [*1.0*],
  [0.1], [0.3337], [*1.0*],
  [0.2], [0.2575], [*1.0*],
  [0.3], [0.2343], [*1.0*],
  [0.5], [0.2250], [*1.0*],
  [0.8], [0.2188], [*1.0*],
)

⇒ *`temporal_projection_accuracy` 在全部六个噪声级上恰为 1.0。* 每级 10000 queries（`report.tex:415`），所以这不是运气。一个在所有条件下都完美的指标意味着任务退化、指标饱和、或投影侧能看到答案。这正是 `a0/` 整条线要消灭的*假绿*形状（对照：`a0/` 故意在 $C^*$ 里放 4 个 `invalid`、5 个 `error` 候选，就是为了防止崩溃被静默写成 `0.0`；`c05_overlapping` 的名义值陷阱同理）。⇒ exp3 目前*不能作为 L4 的证据*，需要先给出一个它能失败的对照。

== 6.8 v1 中被推翻或修订的表述（便于追踪）

#table(
  columns: (auto, 1fr, 1fr),
  table.header([v1 位置], [v1 的说法], [v2]),
  [§1 表], [D 线 = `Pasted markdown.md` + 审查，09-24], [*不完整*。D 线是三跳，第一跳 `report.tex` 在本对话里，且只存在于未跟踪的 zip],
  [§1.1], [A 线「自己废弃」，理由是 `plan.typ:53`], [*归因错误*。降级是你在 \#11（09-17 09:48）先做出的，早于文档约 20 小时],
  [§1 表], [A 线日期 09-09→09-18 是「线的活动期」], [*误导*。09-09 那批是你自带的输入，对话只在 09-18 读取它们（且被截断到 20000 字符）],
  [§5.2], [两条线「不可合并，是第二个实验」], [*修订为「一行重叠、七行空白」*。`report.tex` 矩阵第 2 行就是 `a0/` 的 `B0a`。见 §6.5],
  [§4 表], [DSS「A 线命题 1 / C 线 / D 线三处互不引用」], [*仍是四处，但 D 线那处是 `report.tex` RQ1，不是 `Pasted md` §9*；且 C 线叫它 RQ2],
  [§8], [未读清单含 `agent_engineering_science_repro_bundle.zip`（未解压）], [*已解压并读完*，产出 §6.3、§6.4、§6.7],
  [§8 第 1 项], [「图 PDF 仍可留在 zip 里」], [*错*。只提 5 个文本会得到编译不了的 `.tex`：bib 名字不对（§7.5）、三张图缺失],
)

= §7 未闭合的自我矛盾

+ *`adapdc_scaffold_implementation.typ` 双份*【二手，未复核】：`(1)` 版新增 ADR-001，要求把旧版标记为「部分条款已取代」；*该标记从未加上*，而旧版 `:32` 仍写「不能同时保留相反的现行决策」。两份现都被 git 跟踪（提交 `14edbf07`）。
+ *C 线缺 v2/v3*：一天内四轮修订，语料只留了第一轮和第四轮。中间两轮是「八处反转」的实际发生地（v1 报告列出了八处，但没有 diff）。可从载荷恢复。
+ *B 线缺 6 个审查版本*：`open_world_plan_independent_review(1)`–`(6)`，语料只有最终那一份。`rev:820-829` 的 R52–R62「审查推翻自己」的清单，其原始形态在这六版里。
+ *`a0/STATUS.md` 已陈旧*：它自称 `HEAD = 0851806`、14 个 commit、标签 `a0-audited`；本文提交前为 `cbf6c57a`。文内 §3.3 自己已加 dated 注记说明该表描述的是 D1/D3 收敛之前的状态。⇒ 需要一份新的 STATUS，或在旧文件头部加 dated 标签（仓库对别人的 dated 验证报告的做法是*不改写*，只登记）。
+ *repro bundle 打包时改坏了 bib 的引用*【我复核】：`report.tex:14` 是 `\addbibresource{references.bib}`，而包里的文件叫 `agent_engineering_science_references.bib`；`references.bib` 在包内*不存在*（`ls | grep -c '^references\.bib$'` = 0）。成因可从载荷查到：09-24 05:02–05:03 写过两个 bib——`/mnt/data/agent_engineering_report/references.bib` 与 `/mnt/data/agent_engineering_science_references.bib`——tex 期望前者，打 zip 时扁平化并统一改名，*没有同步改 tex*。⇒ 这个 bundle 按现状*编译不出 PDF*。
  另两类依赖：`tex:254,269,297` 的 `\includegraphics` 指向三个 `fig_*.pdf`（在包内，但是二进制，被 `.gitignore` 白名单排除）；`tex:1` 的 `\documentclass{ctexart}` 需要 ctex 与 CJK 字体。*三个 CSV 不是构建输入*——tex 里没有 `\input`/`\include`/`pgfplotstable`，它们只在 `:415` 的散文里被点名。包不引用 zip 自身，也不含 `/mnt/data` 路径。

= §8 未决决策清单

*由 v2 新增（优先级最高，因为它们改变结论而不只是补细节）*

+ *是否把 zip 里的 5 个纯文本文件提出来跟踪？*（`report.tex` `text/x-tex` 31503 B/433 行、`references.bib` `text/plain` 6642 B/103 行、三个 `text/csv` 1291/637/158 B；全部 UTF-8 有效。其余 3 个 `fig_*.pdf` 是 `application/pdf`。）它们当前因 zip 被排除而在 git 里不存在，而这是 D 线唯一的实测数据。v2 初稿在这里写错了（§6.8 末行）；三个处置：
  - *(a)* 提 5 个文本 ＋ 把 `tex:14` 改成实名 ＋ 接受图缺失。代价：*改写了 09-24 的历史产物*，与仓库「dated 报告不改写、只登记」的惯例（`a0/A1-RESULT.md` §8）冲突。
  - *(b)*（我倾向）提 5 个文本*原样不动*，加一份 README 登记 §7.5 的不一致，并说明图与 PDF 产物在 zip 里——与 `related_files/literature/` 同一个逻辑：不可重建的东西显式登记，不混进可重建的目录。
  - *(c)* 不提，zip 保持唯一容器。代价：D 线唯一的实测数据继续不在版本控制里。
+ *是否用 §6.3 的复算回应审查？* 我可以直接从 exp1 重算 36 格并给出与 β-二项的偏差表；但*生成器仍未写明*，需要补上脚本才算完整回应。
+ *exp3 的 1.0 是否要先修*（§6.7）？在给出一个它能失败的对照之前，L4 没有证据。
+ *`RQ1–RQ5` 与 $rho$ 是否改名*（§6.1、§6.2）？两处同名异义都会在合并写作时产生错误交叉引用。
+ *是否恢复 C 线 v2/v3 与 B 线六个审查版本*（§7.2、§7.3）？它们记录了反转的实际过程，而反转正是这个项目的核心方法。*时效*：载荷解出的中间文件在 `/tmp`，重启即失。

*理论侧（沿用 v1）*

+ L1–L7 是否降级为「带限定条件的可证伪命题」，并单列「已证明的数学事实 / 实测关联 / 机制解释 / 新假设」。
+ `IntegrationEfficiency` 是否先作*任务条件诊断指标*（分层转移概率）而非标量本体。
+ 标题是否改为审查建议的《分布式 Agent 的信息整合瓶颈……》。

*落地侧（沿用 v1）*

+ 机制 A 接线 → *30 分钟长会话*（尚未做过）→ 对抗绕过探针 → 冻结（四步一步都没走完）。
+ *T1 是否换载体*——决定后面几个月，且换载体代价未计入成本表。
+ $G_3$ 用 (a) 便宜两臂 pilot 还是 (b) 并入 `B0a`；(a) 是否构成「同一数据用两次」。
+ $theta, k, C_"min"$ 预注册；$hat(r)$ 与 $ell$ 是否退化成一维（需引入残差幅度阈值 $epsilon_J$）。
+ $tau$ 是否把 A1/标定侧统一到 10 s。
+ `PILOT-PROCEDURE.md:41` 是否走显式重冻（改一字就要连带重冻 `B_hard.json` 并重跑 pilot；已登记 `DEVIATIONS.md` D-CAL-11）。

*跨线的*

+ §6.5 的「一行重叠、七行空白」如何处置：把 `a0/` 的 `B0a` 正式认领为 `report.tex` 矩阵第 2 行的实现？其余七行由谁建仪器？
+ *四个分解如何收敛*：你的三重困难（检索/时机/历史处理，\#28）、D 线的五段（生成→传递→整合→验证→决策）与三层（信息物理/计算动力学/元控制）、`report.tex` 的七域 $T_1$–$T_7$。*四套分解，无一互相引用。* 这是比 §6.1/§6.2 更深的同名异义——它们不是符号冲突，是*本体冲突*。
+ DSS 的四处定义（A 线命题 1 已证 / C 线 $Delta_B (phi)$ / D 线 $argmin |S|$ / `a0/` 的三量 $s_t$）是否收敛成一个。*A 线那个是唯一有证明的*，应当作为起点。
+ ADA 是执行载体还是已废弃（`Pasted md` §21 仍点名它，`open_world_...plan.typ:40` 称其为「可替换的实现手段」）。
+ `rule-construction-research*.md`（09-14）与 `virtual_staining_*`（09-18）*在四条线里都不落位*，且本对话也没产出它们。它们是独立应用域，还是同一纲领的实例？——v1 就指出了这个空白，v2 仍无法回答，因为溯源排除了「对话产物」这一可能。

= §9 证据分级

*【我复核 / 我亲自算过】*

- `related_files/Pasted markdown.md`（1412 行全）、`agent_engineering_science_independent_review_2026-09-24.md`（全）
- `a0/STATUS.md`、`a0/A1-RESULT.md`（全）、`a0/TIMING-REVIEW.md` §0–§7
- 分享链接载荷：完整解码（148184 元素扁平数组 → 4011 节点 mapping），46 个 user 轮次全文，32 个 `/mnt/data` 产物路径，四个 0 命中探针
- zip 全部 8 个文件：三个 CSV 逐行读过；`report.tex` 的章节结构、`:14` 的 bib 引用、`:254/269/297` 的图引用、`:415` 复现信息节；8 个条目的逐文件 MIME 与 UTF-8 有效性
- *数值复算*：β-二项多数票概率 7 个格子逐位重现审查的表；exp1 全 36 格与 β-二项对比（最大 0.331 pp）；`Pasted md` 的 $rho=0.7$ 三格偏差 6.5–9.2 SE；exp2/exp3 的单调性与饱和
- 四处语料引用抽样：`adapdc_theory_review.typ:196-200`、`open_world_...plan.typ:50-56`、`research_state_control_review_v4.tex:1565-1572`、`N_eff` 三份文档 grep 计数——*4/4 命中*
- 两处标签冲突：`v4.tex:1547-1561` 与 `report.tex:304-335` 的 RQ 清单，均逐行 grep 确认
- 免责与引用的冲突：`report.tex:415` 与 `Pasted md:1149`，均逐行 grep 确认
- *本文自身的格式*：所用 Typst 构造先以探针文件编译通过（`inter.big`、`oo`、数学模式内的 `[ ]`、`table.header`、CJK 字体族名），再写正文；`Noto Serif CJK SC` 经 `typst fonts` 确认*不可用*，故用 `Noto Sans CJK SC`

*【二手】三个只读调查者读的，我未逐条核对*

- C 线：`research_state_control_review{,-v4}.tex` + 两份 `.bib`（含八处反转清单、4 条弱引用、6 组重复 key）
- B 线：三份 `.typ`（含 `rev:457-722` §4 全部内容、D1–D16 与 R52–R62）
- A 线：十份文件（含范畴论承重性判断、`(1)` 变体的 64 增 8 改）
- 旁证：B 线调查者自行抽样核对 14 处 `plan:N` 引用全部命中；A 线调查者用 diff 而非印象判断变体

*【我没有读】*

- `rule-construction-research{,(1)}.md`、`virtual_staining_open_source_sota_survey.typ`、四份 `.bib` 正文
- `a0/EPISTEMIC-REVIEW.md`、`a0/A1-{REQUIREMENTS,INTERIM,CONTRACT-AUDIT}.md`、`a0/CONVERGENCE-/SPRINT-2026-09-21.md`（仅在 `STATUS.md`/`A1-RESULT.md` 的转述中出现）
- `report.tex` 正文 31503 字节中，我只读了章节标题、`:14`、`:254/269/297`、`:415`；*七个理论域与三个中层理论的论证细节未读*
- 对话载荷中 771 个 assistant text/code 轮次的正文（我只全读了 46 个 user 轮次与产物清单）

= §10 给复核者的攻击清单

+ *§6.3 的「exp1 = β-二项」是否过强？* 我只证明了 36 格的最大偏差在 2.8 SE 内，与可交换 β-二项*相容*。相容不等于就是它——高斯阈值或 common shock 生成器也可能落在这个范围内。要坐实需要脚本，而脚本不在 zip 里。
+ *§6.3 是否误伤了 `Pasted markdown.md`？* 若那张表来自第三条对话、用了另一个生成器，则「两个不同的模拟」成立；但若它其实是 exp1 的*早期版本*（30000 trials、不同 $rho$ 网格），则正确的说法是「同一实验的两个阶段」，而 1.7–2.4 pp 的偏移需要另一个解释。载荷里没有它的任何痕迹，所以我无法排除后者。
+ *§6.7 对 exp3 的判定是否过严？* `temporal_projection_accuracy ≡ 1.0` 也可能是*任务构造使然*（例如投影侧拿到的就是去噪后的表示）。我没有读 `report.tex` 的实验 C 正文，所以这是从数据形状做的推断，*标为【推断】*。
+ *§6.5 的「一行重叠」是否是巧合？* `report.tex` 矩阵第 2 行的因变量是 `regret, search cost, recovery`，而 `a0/` 的主估计量是 $Delta_T$（策略价值差）。两者形状相近但不是同一个量。若复核者认为这不构成重叠，§6.5 退回 v1 的「不可合并」。
+ *§1.3 的三分类是否可靠？* 判据是「是否出现在 `/mnt/data` 写入路径里」与四个 0 命中探针。tool 输出被截断到 20000 字符，所以*若某个产物只在被截断的部分出现过写入路径，我会漏掉它*。32 这个数应视为下界。
+ *§8 的「四套分解是本体冲突」是否是真问题？* 也可以读作「同一对象在四个抽象层级上的投影」，因而不需要收敛。若如此，正确的动作是画一张映射表而不是选一个。
+ *最强的反驳*：请论证「这次梳理本身是代理目标漂移的实例」——即绘制概念地图、发现同名异义、复算别人的模拟，是在提高*基础设施完整度*而不是提高真实研究能力。你在 \#11 亲自命名过这个谬误。若反驳成立，正确的下一步不是补读 §9 的未读清单，而是直接做 §8 的落地侧两项：接机制 A，跑一次 30 分钟长会话，然后决定 T1 是否换载体。
