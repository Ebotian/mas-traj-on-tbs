conversation title: 梳理Harness前沿论文



===== [user/text] 10-07 09:44 node=73ef0096 len=29 =====
arixv上关于harness的前沿论文进展如何,检索梳理


===== [assistant/thoughts] 10-07 09:44 node=88e388f9 len=6 =====
Worked


===== [assistant/text] 10-07 09:44 node=8b2bdfeb len=92 =====
我会按 agent harness（智能体的运行、工具、记忆、反馈与评估机制）来检索 arXiv，区分直接研究 harness 的论文与相关机制研究，再梳理对 ada／opl 的启发。


===== [assistant/thoughts] 10-07 09:44 node=31f1cc06 len=16 =====
Searched the web


===== [tool/text] 10-07 09:44 node=4ae157b0 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:44 node=6837c4ab len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:45 node=463a3bdc len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:45 node=4c39d138 len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-07 09:45 node=8f80f01c len=114 =====
检索到的直接相关研究已经形成一条主线：自动修改 harness、在有限预算下搜索模块组合，以及独立评估这些修改是否有效。还有一类很值得注意的反面结果：优化器可能虚构失败，再加入无用规则。我会把增益证据和这类失效机制放在一起比较。


===== [assistant/thoughts] 10-07 09:45 node=8235959f len=16 =====
Searched the web


===== [tool/text] 10-07 09:45 node=4778f3cb len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:45 node=09b6c8c5 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:45 node=3476ad6f len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:45 node=5e412a6b len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-07 09:45 node=121ffdff len=17 =====
Worked for 1m 24s


===== [assistant/text] 10-07 09:45 node=d31a0be5 len=6446 =====
**截至 2026 年 10 月 7 日，arXiv 上的 agent harness 研究，已经从“手工设计运行框架”发展到“自动优化可执行代码、复用插件、按任务适配，并独立测量改进是否真实”。但最新实证也明确表明：复杂 harness 的收益依赖模型、任务与预算，尚不存在通用最优架构。**

本轮检索以 **agent harness、harness optimization、recursive self-improvement、context engineering** 为主，重点核对了 2026 年尤其是 9 月下旬至 10 月初的论文。下面是筛选式梳理，不是穷尽目录；数字均为论文作者报告，本轮未复现实验。

这里的 **harness** 指围绕模型的可执行运行机制：上下文构造、状态与记忆、工具接口、控制流、验证、重试、预算及调度。

**一、研究主线：从优化提示词，到优化整个运行程序**

| 论文 | 核心进展 | 应如何理解 |
|---|---|---|
| [ACE — Agentic Context Engineering](https://arxiv.org/abs/2510.04618)，2025-10 | 将上下文视为持续更新的策略手册，通过生成、反思、整理进行增量更新 | 代表“优化上下文与经验”的路线，主要针对反复摘要造成的信息丢失。genui{"citation":{"ref":"turn2academia0"}} |
| [AutoHarness](https://arxiv.org/abs/2603.03329)，2026 | 利用环境反馈自动生成动作验证代码，进一步生成完整代码策略 | 在所测 145 个 TextArena 游戏中消除非法动作；说明明确规则适合转成可执行约束，但不能直接外推到开放研究任务。genui{"citation":{"ref":"turn5view3"}} |
| [Meta-Harness](https://arxiv.org/abs/2603.28052)，03-30 | 外层 agent 直接搜索 harness 源码，可访问历史候选的代码、分数及完整执行轨迹 | 数学检索任务上，一个发现的 harness 在五个未参与优化的模型上平均提高 4.7 个百分点。关键在于保留可追溯的优化历史。genui{"citation":{"ref":"turn1academia0"}} |
| [Self-Harness](https://arxiv.org/abs/2606.09498)，06-08；08-20 更新 v3 | 同一模型完成“弱点挖掘—最小修改提案—回归验证” | v3 扩展至三个模型、三个基准，九种组合的最终 harness 均提升。它强调针对模型具体弱点改动。genui{"citation":{"ref":"turn1view1"}} |

这几篇形成了一个实用的演进关系：

**经验文本可优化 → 运行代码可优化 → 优化过程需要完整证据 → 改动必须经过回归验证。**

需要注意版本差异：Self-Harness 的检索摘要仍可能显示早期单一 Terminal-Bench 实验；当前 v3 已经扩展到 SWE-bench Verified 和 AppWorld。

**二、最新前沿：插件组合、预算分配和实例适配**

**1. PluginRSI：把改进积累为可复用插件**

[PluginRSI: Recursive Improvement of Agent Harnesses with Reusable Plugins](https://arxiv.org/html/2609.32423v1)，**09-26**。

它针对整体重写的两个问题：多个机制耦合，难以独立探索；新版本可能覆盖旧版本中的有效机制。其做法是进行插件变异与 harness 重组，插件分为 **roles、tools、skills、memory**。

一个影响实验解释的细节是：它的种子库已有 **75 个插件**，初始运行 harness 只装配其中四个。因此，它研究的是在已有组件资产上继续演化，不能理解成从零自动发明整个系统。genui{"citation":{"ref":"turn6view4"}}

**我的判断：这篇与插件式 agent 开发最贴近。** 值得借鉴的是组件独立版本化、保留有效局部机制，以及重组不同迭代产生的成果。

**2. MESH-Harness：把 harness 优化明确变成有限预算下的组合搜索**

[MESH-Harness](https://arxiv.org/abs/2610.05300)，**10-04**，是本轮检索中最值得关注的新方法之一。

它使用：

- 固定接口的功能槽位，每个槽位维护多个候选实现；
- 共享模块表示与 **LinUCB**，同时考虑预测收益和探索价值；
- 多起点坐标上升，避免枚举全部组合；
- 执行轨迹指导局部代码变异，再加入候选池。

作者在四类任务上报告，相比 Meta-Harness 提升 **2.00—7.01 个百分点**；在所报告配置中，含搜索的总成本低 **14.6%**。这些结果采用匹配的候选评估预算，不能直接解释成所有成本口径都完全相同。genui{"citation":{"ref":"turn3view0"}}

**它最有价值的转变是：候选生成与候选评估分开设计。** 生成很多改法相对容易，真正昂贵的是决定哪些组合值得运行完整实验。

**3. Turbo Harness：从全局一个 harness，到按任务实例生成补丁**

[Turbo Harness: Instance-Adaptive Harness Optimization](https://arxiv.org/abs/2609.40330)，**09-30**。

它将先前全局优化产生的材料整理成 playbook，训练一个 harness editor，在推理时根据具体任务生成针对性补丁。作者在七个基准上报告优于所比较的 harness 优化基线。genui{"citation":{"ref":"turn4view1"}}

这条路线对应：

\[
H^\star \quad\longrightarrow\quad H(x),
\]

其中 \(x\) 是任务实例。需要额外核对的成本，是 editor 的训练、补丁生成及执行验证开销。

**4. Raven：把“模型＋harness”当成组合单元**

[Raven: The Harness of Harnesses for Composable Agentic Intelligence](https://arxiv.org/abs/2609.33439)，**09-27**。

它将特定模型与专用 harness 组成可执行单元，由 Host Agent 分解目标、选择专用 agent、协调依赖并整合结果，还包含跨任务经验与技能复用。论文给出组合扩大可靠任务覆盖范围的充分条件。genui{"citation":{"ref":"turn5view1"}}

这是跨域多 agent 的系统路线。**充分条件下的覆盖扩展，不等于任意增加 agent 都会提高能力**；其价值需要结合调度开销、接口正确性和共享预算判断。

**三、评估本身正在成为独立研究问题**

| 论文 | 解决的问题 | 关键发现或设计 |
|---|---|---|
| [VeRO](https://arxiv.org/abs/2602.22480)，02-25 | 如何可复现地研究“agent 优化 agent” | 版本化快照、预算受控评估、结构化执行轨迹。genui{"citation":{"ref":"turn1academia3"}} |
| [HarnessOpt-Bench](https://arxiv.org/abs/2608.06301)，08-06 | 如何评价优化器，而非只评价最终 agent | 固定目标评估预算，搜索期间隔离测试集；在五个优化模型、四类任务、111 次计分运行中，原生 harness 并非始终更好。genui{"citation":{"ref":"turn1academia1"}} |
| [Evo-Bench](https://arxiv.org/abs/2608.09096)，08-10 | 如何区分 harness 演化、模型强度与任务过拟合 | 覆盖 Search、Office、General；收益具有领域差异，并观察到早期饱和。genui{"citation":{"ref":"turn1academia2"}} |

这里需要区分两种能力：

- **执行能力**：给定 harness 后，agent 能否完成任务？
- **优化能力**：给定有限实验预算，agent 能否找到在未见任务上更好的 harness？

一个模型擅长完成任务，并不自动证明它擅长诊断和改善自己的运行机制。

**四、必须与正向成果一起读的反面证据**

**1. 强模型未必需要复杂编排**

[How Much of a Harness Does a Strong Agent Need for Autonomous ML Engineering?](https://arxiv.org/abs/2609.40303)，**09-30**。

在相同前沿模型、相同时间预算下，作者发现所比较的开源先进 MLE harness，没有胜过单会话、最小 harness 的 coding agent 基线。论文据此质疑当前 MLE 基准中复杂人工编排的边际回报。genui{"citation":{"ref":"turn4view4"}}

它与算法优化任务很相关，但结论范围是**所测模型、基准与预算**，不能扩成“harness 一概无用”。

**2. 哪种组件有用，取决于任务类型**

[Beyond the Model: Demystifying Harness Effects in Software Engineering Agents](https://arxiv.org/abs/2609.32459)，**09-26**。

论文比较两个 harness、十个模型及三个基准，再对工具、压缩、规划、子 agent、skills 做组件分析。结果包括：

- 在 issue 修复中，模型增强后复杂 harness 的边际收益下降；
- 更开放的仓库级任务仍可能受益；
- 结构化工具与任务专用子 agent 的收益较稳定；
- 上下文压缩和通用子 agent 可能损害仓库生成表现。genui{"citation":{"ref":"turn4view3"}}

它解释了为什么不同论文会得出看似相反的结论：**模型与任务的交互作用不能忽略。**

**3. 自改进可能制造不存在的问题**

[Phantom Guardrails](https://arxiv.org/abs/2607.13083)，**07-13**。

在正确行为应是“不改动”的确定性实验中，优化器会将合法输入中的规则状模式误判为失败，并添加无用防护。作者在一组条件下观察到 **15/60** 次虚构失败，而无此模式的对照为 **0/60**。genui{"citation":{"ref":"turn0academia23"}}

这直接支持一个工程要求：**修改提案必须引用可验证的失败证据，且“不改动”应是合法输出。**

**4. 得分提高可能只是修复了评估缺陷**

[What Does a Harness Repair?](https://arxiv.org/abs/2610.05533)，**10-04**。

这项预注册研究区分了解析失败、输出截断、弱基线与评估缺陷。其 GEPA 搜索修复了损坏的初始配置，但选出的 harness 没有超过所设的关闭 thinking 基线；某些缺陷还会被同一流水线的复现实验重复出来。genui{"citation":{"ref":"turn5view2"}}

它提醒我们：**同一评估程序重复得到增益，仍不足以证明增益来源正确。**

**五、两条值得继续追踪的扩展方向**

- **harness 与权重联合优化**：[SIA](https://arxiv.org/abs/2605.27276) 同时修改运行框架和模型权重，在法律分类、GPU kernel 优化及单细胞去噪上报告收益。它涉及训练资源，和仅调用模型 API 的方案属于不同成本条件。genui{"citation":{"ref":"turn0academia20"}}
- **harness 与任务生成共同演化**：[Recursive Harness Self-Improvement for Frontier Reasoning Data Synthesis](https://arxiv.org/abs/2610.03548)，10-02，将求解失败转成技能，逐批修改生成流程，同时固定验证标准；目标是生成更难且有效的训练任务。它为自动构造实验挑战集提供了参考。genui{"citation":{"ref":"turn4view2"}}

**对工程实践，我更看重以下研究问题**

以下是基于上述文献的归纳与建议，并非论文已经共同证明的定律。

首先，把 harness 看成有成本的实验对象：

\[
\max_H\ \mathbb E_{x\sim D_{\mathrm{test}}}[R(M,H,x)]
\quad
\text{s.t.}\quad
C_{\mathrm{search}}+\mathbb E[C_{\mathrm{run}}]\le B.
\]

这里同时计入搜索成本与部署运行成本，才能比较“复杂框架”“多次简单尝试”和“换更强模型”。

其次，最值得优先验证的机制是：

| 工程问题 | 可借鉴路线 | 需要验证的核心假设 |
|---|---|---|
| 有效改进在反复重写中丢失 | PluginRSI | 独立插件与重组能否保留跨迭代收益？ |
| 完整实验太贵 | MESH-Harness | 代理模型引导是否优于同预算随机搜索？ |
| 同一流程不适合所有任务 | Turbo Harness | 实例适配的收益是否覆盖新增成本？ |
| 失败诊断缺乏证据 | Meta-Harness、Self-Harness | 完整轨迹是否改善修改质量与泛化？ |
| 框架复杂度持续膨胀 | 最小 harness 基线、Phantom Guardrails | 删除组件或保持不变是否同样有效？ |
| 优化结果可能过拟合 | HarnessOpt-Bench、VeRO | 隔离测试、版本记录与预算约束是否充分？ |

**若只精读五组，我建议按这个顺序：Meta-Harness → PluginRSI → MESH-Harness → HarnessOpt-Bench → 两篇“复杂 harness 是否必要”的实证论文。** 这样既能理解自动优化方法，也能建立判断这些方法是否值得投入的对照标准。


===== [user/text] 10-07 09:48 node=e36fb87e len=38 =====
目前我比较关注在墙钟时间-成本-通过率三方的联合优化,或者评估,寻找相关研究


===== [assistant/thoughts] 10-07 09:48 node=7bd86509 len=6 =====
Worked


===== [assistant/text] 10-07 09:48 node=7dca4906 len=79 =====
我会围绕“墙钟时间—实际成本—通过率”的联合评估检索，重点找三目标 Pareto 前沿、预算约束下的调度与并行策略，以及是否把失败、重试和搜索开销计入的方法。


===== [assistant/thoughts] 10-07 09:48 node=e0d9f439 len=16 =====
Searched the web


===== [tool/text] 10-07 09:48 node=3d257ed3 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:49 node=133cda40 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:49 node=10744bfc len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-07 09:49 node=5b7c5be5 len=116 =====
找到两篇非常贴合你的目标：MCPP 直接优化“在截止时间和预算内完成整个工作流的概率”；MoFlow 则搜索多目标工作流的 Pareto 前沿。我正在核对它们的时间口径——实测墙钟时间、模拟执行时间和 token 代理不能混为一谈。


===== [assistant/thoughts] 10-07 09:49 node=76ac96af len=16 =====
Searched the web


===== [tool/text] 10-07 09:49 node=283c8c60 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:49 node=fe443df1 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:49 node=843daabd len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:50 node=0cf4265a len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-07 09:50 node=80066e6a len=17 =====
Worked for 1m 22s


===== [assistant/text] 10-07 09:50 node=43269fdc len=4671 =====
**有，而且这个问题已有直接对应的研究。对你的关注点，最值得优先看的是 MCPP、EvoRoute、cua-speedrun；MoFlow 的多目标搜索方法也相关，但它用“串行调用次数”代替墙钟时间，不能直接当作三方联合优化的实证。**

截至 **2026-10-07**，本轮检索可以分成三类：**运行时资源分配、离线工作流搜索、三维评估**。这三类解决的问题不同，应分别比较。

**1．MCPP：最贴近“限时、限钱，提高通过率”**

[On Time, Within Budget: Constraint-Driven Online Resource Allocation for Agentic Workflows](https://arxiv.org/abs/2605.06110)，2026-05，代码：[WangXinglin/MCPP](https://github.com/WangXinglin/MCPP)。

其目标可写成：

\[
\max_{\pi}\Pr_{\pi}
\bigl(\text{任务成功},\ T\le D,\ C\le B\bigr),
\]

其中 \(\pi\) 是执行策略，\(D\) 是截止时间，\(B\) 是预算。

给定任务依赖图，它动态决定：当前可执行节点用哪个模型、各采样多少条并行候选，并根据结果和剩余资源重新规划。方法是 **Monte Carlo Portfolio Planning**：模拟不同资源分配的后续执行，选择约束内完成概率较高的方案。genui{"citation":{"ref":"turn10view1"}}

**与你的需求高度重合，但要注意三个边界：**

- 工作流结构预先给定，重点是执行调度。
- 需要每个“子任务—模型”的成功率和执行长度估计。
- 建模采用独立采样假设，时间由吞吐等执行模型估算；实验使用包含实测墙钟时间的离线 rollout 数据。它不等于已验证任意在线 API 的限流、排队和相关失败情形。genui{"citation":{"refs":["turn12view3","turn13view0"]}}

**我会把它作为运行时调度的首要参考。** 其问题定义比“质量减去成本惩罚”更贴近有明确期限的长程任务。

**2．EvoRoute：直接研究通过率—货币成本—墙钟时间**

[EvoRoute: Experience-Driven Self-Routing LLM Agent Systems](https://arxiv.org/abs/2601.02695)，2026-01。

它在 agent 每一步检索历史执行经验，筛选三维非支配的模型候选，再选择模型。论文明确将 delay 定义为 **total wall-clock execution time**，并记录每一步的费用、耗时及执行结果。genui{"citation":{"ref":"turn13view4"}}

它适合回答：

> 哪些步骤值得调用强模型，哪些步骤交给便宜、快速模型，能够改善整个任务的三维表现？

作者在 GAIA、BrowseComp+ 等任务上报告改进，但摘要中的最大节省比例不应当作所有场景的平均效果。例如其一组汇总结果是：性能 **74.27% → 74.60%**，费用 **521.61 → 138.40 美元**，汇总延迟 **123.00 → 92.23 小时**。genui{"citation":{"ref":"turn12view5"}}

**它与 MCPP 的区别**：EvoRoute 主要做逐步模型路由；MCPP 同时考虑依赖图中多个就绪节点的模型与并行采样分配。复用 EvoRoute 时，还应单列冷启动经验收集和路由器本身的开销。

**3．cua-speedrun：最值得借鉴的墙钟评估方法**

[cua-speedrun: Standardized Benchmarking of the Speed of Computer-Use Agents](https://arxiv.org/abs/2609.40284)，**2026-09-30**；项目：[cuaspeedrun.com](https://cuaspeedrun.com)。

它统一虚拟机、执行流水线和 agent 接口，在四个计算机操作基准上比较性能、速度和费用，并研究 reasoning effort、harness 和环境延迟的影响。

两个结果尤其相关：

- 某些模型增加 reasoning effort，反而能缩短整个任务时间。
- 更快的环境 I/O，有时反而导致更慢的任务完成。

这说明单次调用速度或工具延迟，不能替代端到端完成时间。论文还研究缩小评估任务集、同时尽量保持统计检验能力的方法。genui{"citation":{"ref":"turn11view0"}}

**虽然任务域是 GUI，它的受控计时方法比具体排行榜更值得迁移到 coding agent。**

**4．MoFlow：真正的多目标搜索，但时间与成本使用代理指标**

[MoFlow: Multi-Objective Agentic Workflow Generation](https://arxiv.org/abs/2609.38294)，**2026-09-29**；代码：[yining610/MoFlow](https://github.com/yining610/MoFlow)。

它把工作流生成建模成多目标决策过程，用带集合值回传的 **Convex-Hull MCTS** 保存多个权衡方案。一次搜索后，可以根据不同偏好选择工作流，作者用 **hypervolume（超体积）** 评价所得前沿。genui{"citation":{"ref":"turn11view2"}}

但核对正文后，需要明确降一级看待它对你问题的实证支持：

| 你关心的量 | MoFlow 实际使用的量 |
|---|---|
| 实际费用 | 总 token 数 |
| 墙钟时间 | 串行 LLM 调用轮数 |
| 通过率 | 按具体基准评分，部分任务采用连续分数 |

论文明确说明，没有采用墙钟时间，因为它受服务商、硬件和负载影响。测试集规模也较小：AIME 为 20 道，其余基准各 50 道。genui{"citation":{"ref":"turn13view2"}}

**适合借鉴前沿搜索算法；若用于你的研究，必须换成真实计费与端到端计时重新验证。**

**5．DolphinBench：现成的三维报告范例**

[DolphinBench: Mapping the Pareto Frontier of Agent Memory](https://arxiv.org/abs/2609.24971)，**2026-09-21**。

它通过需要历史信息的实际任务评估记忆系统，包含三个角色、共 600 个任务，强制同时报告准确率、成本和延迟。官网还提供 median 与 p95 latency，并将记忆摄取与测试处理纳入费用。genui{"citation":{"refs":["turn7academia12","turn7search3"]}}

值得借鉴的是**把前置构建成本计入**。但记忆领域的结果不能直接代表仓库重构或算法研究；总费用与在线延迟的统计边界也应分别读清。

**6．两篇补充文献**

| 论文 | 与你的问题的关系 |
|---|---|
| [Latency and Token-Aware Test-Time Compute](https://arxiv.org/abs/2509.09864)，2025-09 | 联合考虑 token 成本与墙钟延迟，按问题选择 best-of-N、beam search 等策略及计算预算；适合研究“并行多试几次，还是串行深入推理”。genui{"citation":{"ref":"turn13academia0"}} |
| [AI Agents That Matter](https://arxiv.org/abs/2407.01502)，2024-07 | 成本—准确率联合评价的基础文献，讨论过度复杂的 agent、弱留出集和不可复现评估；它主要是双目标，不能冒充完整三目标方案。genui{"citation":{"ref":"turn8academia28"}} |

**对于你的研究，我建议用“两种互补视角”组织评估**

下面是我的方法建议。

第一种是配置的三维 Pareto 前沿：

\[
\bigl(p_{\mathrm{pass}},\ \mathbb E[C],\ Q_{0.95}(T)\bigr).
\]

它适合比较不同模型、harness、并行度和重试策略，保留不同权衡。时间同时报告 median、p95 和均值，避免只看某一个汇总量。

第二种是**预算—期限—通过率曲面**：

\[
S_\pi(B,D)=
\Pr_\pi\!\left(
Y=1,\ C\le B,\ T\le D
\right).
\]

其中 \(Y=1\) 表示最终交付通过独立验证。改变 \(B,D\)，就能看到一种策略在哪些资源区域占优。

这比只报“平均花费、平均耗时、最终通过率”更有判别力：两套系统可能三个均值近似，却有完全不同的尾部失败与超时行为。**三维前沿用于发现选择，\(S_\pi(B,D)\) 用于回答具体预算下能否交付。**

实施时，有五个口径尤其关键：

| 项目 | 建议口径 |
|---|---|
| 时间 | 从任务提交到最终交付；包括排队、工具、验证、重试和协调 |
| 成本 | 所有尝试的总费用，包括失败分支、验证器和取消前已产生的费用 |
| 成功 | 最终被系统选中并交付的结果通过验证；“候选中存在正确答案”另报 |
| 并行资源 | 固定或明确列出并发上限、API 配额和硬件，否则前沿不可比较 |
| 搜索投入 | 单列 harness／路由训练成本，并按预计使用次数报告摊销结果 |

最后一个区别很重要：**pass@k 通常不能直接当作可交付通过率**。若系统无法识别哪个候选正确，或识别过程很慢、很贵，候选覆盖率提高不一定带来最终三维收益。

对于算法优化，还可以把“通过”参数化为预先指定的质量阈值 \(q\)：

\[
S_\pi(B,D;q)=
\Pr_\pi\!\left(
\text{正确性通过},\
\text{优化质量}\ge q,\
C\le B,\
T\le D
\right).
\]

这样可以比较“多久、花多少钱，达到多大改进”，同时避免把极小改进和重大改进都压成同一个成功标签。

**优先阅读顺序：MCPP 的目标与执行模型 → cua-speedrun 的计时协议 → EvoRoute 的路由与费用记录 → MoFlow 的多目标搜索。** 这四篇分别覆盖你需要的决策目标、测量方法、在线策略与离线搜索，但目前还需要把它们组合成统一实验协议。


===== [user/text] 10-07 09:55 node=a0ba6f9e len=65 =====
我们的目的是开发在这三维指标上都优化的,模型无关优先,最好任务类型也无关的harness,这些是否足够,不足够的话,你是否能补充?


===== [assistant/thoughts] 10-07 09:55 node=84e9a63f len=6 =====
Worked


===== [assistant/text] 10-07 09:55 node=9cf41fb0 len=70 =====
我会按“能否支撑通用 harness 的设计与验证”来重新筛选：重点补查跨模型、跨任务迁移，以及不依赖任务成功率先验的调度、并行和停止机制。


===== [assistant/thoughts] 10-07 09:55 node=0d4188be len=16 =====
Searched the web


===== [tool/text] 10-07 09:56 node=13537770 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:56 node=9c166518 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 09:56 node=33b19195 len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-07 09:56 node=2c9109e0 len=14 =====
Worked for 45s


===== [assistant/text] 10-07 09:56 node=a81dde1e len=4539 =====
**还不够。已有文献足以确定评估目标和若干优化算法，但不足以支撑“模型无关、尽量任务无关、在时间—成本—通过率上共同改进”的完整 harness。** 上一轮偏重路由、资源分配与评测，漏掉了几个更接近通用运行时的研究方向。本轮补查后，我认为应补齐：**执行编排、上下文管理、验证与恢复、跨模型／跨任务泛化实验。**

而且需要明确：**支持替换模型，和优化收益能迁移到新模型，是两件事。** 后者才是我们需要证明的性质。

**一、先把目标定义准确**

我建议将“模型无关、任务无关”具体化为：

| 层面 | 可检验要求 |
|---|---|
| 模型接口 | 不要求权重、梯度或 logits；通过普通模型调用即可工作 |
| 模型迁移 | 换模型后，核心代码与控制策略不需重新人工设计；允许明确计费的少量校准 |
| 任务迁移 | 不硬编码题型、基准答案或专用工作流；工具与验证器通过接口接入 |
| 优化收益 | 在未参与开发的模型、任务类别上，仍改善三维表现，而非只在总体平均上获益 |

**“任务无关”可以做到控制机制通用，但不能意味着完全不需要任务语义。** 判断代码正确、证明成立、文档满足要求，必然需要不同证据。合理边界是：统一验证接口，允许任务提供验证器；没有可靠验证器时，控制器必须承认不确定性。

同时，将目标分成两项，避免混淆：

- **共同改进**：相对同模型基线，通过率不降低，同时费用和墙钟时间下降。
- **前沿扩展**：在不同预算、期限下，提供更好的可选配置。

第二项不能自动证明第一项；也不应承诺每个任务都三项同时改善。

**二、需要补充的研究，按机制价值排序**

**1．执行编译与工具合并：最适合成为通用底层**

[An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511) 将函数调用拆成规划、任务派发和并行执行，支持开源与闭源模型。它提供了一个重要设计基础：把依赖关系暴露给运行时，由执行器调度独立工具调用。genui{"citation":{"ref":"turn15search0"}}

[Optimizing Agentic Workflows using Meta-tools](https://arxiv.org/abs/2601.22037)，2026-01，则从轨迹中发现重复工具序列，合成确定性的复合工具。作者报告最多减少 11.9% 的模型调用，同时提高最多 4.2 个百分点的任务成功率。genui{"citation":{"ref":"turn9academia1"}}

这两条路线可能产生三方共同收益：减少不必要的模型往返，缩短串行路径，并减少中间决策出错机会。

**我们的可借鉴点：动态依赖图＋工具组合执行。** 但只有确定不需要新语义判断的步骤才适合合并；遇到未预见结果，应恢复模型决策。

**2．协程式代码执行：让一次模型决策跨越多个工具往返**

[Policy as Code: A Coroutine-Bridge Harness for Fast-Reasoning Reliability on CAR-bench](https://arxiv.org/abs/2609.29251)，2026-09-24。

模型输出可暂停、恢复的 Python 程序，工具调用返回后继续执行程序，避免每次工具结果都触发一次模型调用。论文报告同一 harness 在两个模型上使用，并取得低延迟表现。genui{"citation":{"ref":"turn14academia1"}}

**架构值得参考，但其可靠性收益部分来自把 CAR-bench 的确定性政策直接编码进工具层。** 因而它是“可迁移执行机制”的证据，尚不是“任务无关收益”的证明。

我们可以借鉴执行机制，把领域规则留在外部工具契约中。

**3．推测执行：补足墙钟时间优化，但不能默认省钱**

[Speculative Actions](https://arxiv.org/abs/2510.04371) 用快速模型预测未来动作，提前执行，并在条件满足时接受推测结果。论文覆盖游戏、电商和搜索等环境；操作系统环境使用的是有损扩展。genui{"citation":{"ref":"turn15search1"}}

更新的 [TomasuLLM](https://arxiv.org/abs/2609.38201)，2026-09，10-01 更新，使用隔离的写时复制环境、依赖与副作用追踪，以及验证后的顺序提交。作者在三个代码相关基准上报告约 **1.27—1.35 倍**加速。genui{"citation":{"ref":"turn16view0"}}

这很适合工具运行较慢的工作流。但：

- 加速可能来自额外计算，费用未必下降；
- 需要环境支持隔离、验证或延迟提交；
- 通过率保持，不能仅凭有限次提交中“未见错误”作普遍保证。

**因此它应是按收益启用的优化选项。** 对不支持隔离的环境，仍可采用普通异步并行。

**4．上下文管理：必须加入简单、跨模型的强基线**

[The Complexity Trap: Simple Observation Masking Is as Efficient as LLM Summarization for Agent Context Management](https://arxiv.org/abs/2508.21433)。

在 SWE-agent、SWE-bench Verified 和五种模型配置中，简单遮蔽旧观察就能显著降低成本，并达到与模型摘要相近的通过率。genui{"citation":{"ref":"turn16academia0"}}

对我们最有用的并非“遮蔽永远优于摘要”，而是：

> 上下文优化不一定要额外调用模型；确定性的裁剪、外置存储与按需取回，应先成为比较对象。

可以比较三个可替换策略：原始上下文、保留引用的观察遮蔽、增量摘要。不要预先假定哪个跨任务最优。

**5．验证频率与检查点：此前遗漏的理论方向**

[Harnessing LLMs as Agents: What Does It Cost?](https://arxiv.org/abs/2610.02488)，**2026-10-01**。

它提出资源受限的 Language Model Agent Machine，分别讨论上下文—记忆通信、存储与重算、采样可靠性、不完美验证，以及类似 Young–Daly 的检查点规律。genui{"citation":{"ref":"turn16view1"}}

这篇值得深入核对，因为它直接触及：

- 每一步都验证，是否过贵？
- 检查太晚，失败后要重做多少？
- 保存什么状态，能减少重复推理？

**目前我只核对了摘要与论文信息，尚未审查定理假设。** 它是理论候选，不能据此宣称已有通用最优验证间隔。

**三、已有方法应当放在哪一层**

补充这些工作后，原先文献的用途更清楚了：

| 层 | 可借鉴研究 | 仍需解决的问题 |
|---|---|---|
| 执行机制 | LLMCompiler、Meta-tools、协程执行 | 动态依赖、异常恢复、工具语义 |
| 隐藏等待时间 | Speculative Actions、TomasuLLM | 额外成本与推测正确性 |
| 上下文与状态 | Observation Masking、ACE | 信息丢失与长期任务迁移 |
| 运行时资源决策 | MCPP、EvoRoute | 冷启动、估计误差、相关失败 |
| 离线配置搜索 | MoFlow、MESH-Harness | 实测三维目标、搜索成本、泛化 |
| 验证与恢复 | LAM 理论方向、任务验证器 | 不完美反馈、验证频率与停止 |
| 评估 | cua-speedrun、HarnessOpt-Bench | 同模型对照及跨域留出 |

**单模型改进应该先单独成立，多模型路由再作为扩展。** 否则系统收益可能主要来自换用了更合适的模型，而非 harness 本身更好。

**四、我建议的核心架构：通用执行器＋可校准控制器**

下面是设计建议，尚未经过实验验证。

通用执行器管理工具、状态、异步任务、费用、截止时间、检查点和结果证据。控制器只决定：

\[
a_t\in
\{\text{继续、批处理、并行、取回上下文、验证、重试、停止}\}.
\]

控制器观察的状态包括：

\[
s_t=
(\text{当前进展、剩余预算、剩余时间、在途任务、证据、历史结果}).
\]

模型特定信息——例如费用、延迟分布、输出格式能力——作为配置或观测输入，而不是散落在控制逻辑里的型号判断。任务特定信息通过工具与验证器进入。

关键是保留三个能力：

1. **退回简单执行路径。** 新机制没有足够收益证据时，可以不启用。
2. **记录机制开销。** 包括规划、检索、摘要、推测失败、验证和取消后的费用。
3. **区分确定性优化与语义性优化。** 缓存有效性、依赖正确性可以做程序检查；摘要、推测与提前停止可能改变结果，需要统计评估。

还有一个尚未被前述文献充分解决的问题：**开放任务中如何估计“再做一步”的收益？** 硬预算停止很容易实现；在不损害通过率的前提下提前停止，依赖可靠反馈。没有跨任务校准的证据，不能把模型自报“已经完成”当作通用答案。

**五、证明通用性，需要比常规 benchmark 更严格的实验**

我建议至少区分四种测试：

| 测试条件 | 回答的问题 |
|---|---|
| 已见模型＋已见任务类的留出实例 | 是否在熟悉分布上有效？ |
| 未见模型＋已见任务类 | 收益能否跨模型迁移？ |
| 已见模型＋未见任务类 | 控制机制能否跨任务迁移？ |
| 未见模型＋未见任务类 | 是否具有联合泛化能力？ |

每种条件都应分别报告：

- **冻结策略、零校准**；
- **固定小预算校准**，费用和时间计入；
- 同模型简单 harness 基线；
- 各机制消融及总体组合；
- 通过率、全量费用、墙钟分布和预算—期限成功率曲面。

还需要把并发、缓存状态、模型服务时段交错安排，减少基础设施波动造成的假收益。通过率采用配对任务比较和不确定性区间；“没有显著下降”不等于已经证明不劣。

**因此，文献已经足够启动一个有针对性的原型，但还不足以认定方案已完整。** 当前最值得做出的贡献，是将这些机制纳入同一套真实计时、真实计费、可插拔验证的运行时，并证明：**在不重新人工设计控制逻辑的情况下，三维收益能够迁移到未见模型与未见任务。**


===== [assistant/thoughts] 10-07 09:56 node=b30ff991 len=6 =====
Worked


===== [user/text] 10-07 10:00 node=5edd1662 len=105 =====
有一个重要前提,或者猜想需要你寻找可能的证明:harness设计是否默认单模型/单供应商模型?多模型/多供应商组合(先不论组合形式)能否在多数情况下比前一种情况都更占优?如果没有证明,也尽量找到置信度更高的方向


===== [assistant/thoughts] 10-07 10:00 node=492446ab len=6 =====
Worked


===== [assistant/text] 10-07 10:00 node=645ba662 len=93 =====
我会区分三个命题来查证：harness 是否通常假定单模型；扩大模型候选集是否有理论上的“不劣”保证；以及计入路由、协调和学习成本后，多模型是否在多数任务上仍有优势。后两者不能混为一谈。


===== [assistant/thoughts] 10-07 10:01 node=05dcda37 len=16 =====
Searched the web


===== [tool/text] 10-07 10:01 node=5f43e8d3 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 10:01 node=c760b8e1 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 10:01 node=c6a6e2da len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 10:01 node=1f101384 len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-07 10:01 node=c755c5ad len=127 =====
找到了一篇直接反驳“异构模型天然更好”的实证：Self-MoA 在多个基准上胜过混合不同模型的 MoA。另一方面，路由理论支持有条件的优势——关键是能否识别模型各自擅长的请求。接下来我会把“候选集扩大带来的理论上限”和“实际可实现的净收益”分开给出判断。


===== [assistant/thoughts] 10-07 10:01 node=6127bccb len=61 =====
Searching research on LLM routing and multi-agent limitations


===== [tool/text] 10-07 10:01 node=6c103af9 len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-07 10:01 node=ac0ef04e len=14 =====
Worked for 56s


===== [assistant/text] 10-07 10:01 node=03cf2782 len=4604 =====
**这个猜想有合理基础，但目前只能支持“有条件的优势”，不能支持“多模型／多供应商在多数情况下三维都更优”。** 本轮找到的理论与实证，支持把多模型能力纳入设计空间；同时，也找到了直接反对“异构组合天然更好”的结果。

我会把我们的前提修正为：

> **允许调用多个模型、多个供应商，并保留低开销的单模型执行路径；只有互补收益超过选择、验证和切换开销时，才实际使用组合。**

这不是保守措辞，而是目前证据最支持的设计方向。

**1．harness 是否默认单模型／单供应商？**

**不是定义上的要求，也不是现有研究的共同前提。** 前面讨论的 Self-Harness、Meta-Harness 等工作，常在给定执行模型下优化或比较 harness；EvoRoute、MCPP 则直接把模型选择作为运行时决策变量。不能从前一类实验设置推断整个领域默认单模型。genui{"citation":{"refs":["turn1view1","turn1academia0","turn10view1","turn13view4"]}}

还要分清三个维度：

| 维度 | 含义 |
|---|---|
| 多 agent | 可以全部调用同一模型 |
| 多模型 | 可以来自同一供应商 |
| 多供应商 | 可以托管相同开放权重模型，也可以提供不同模型 |

因此，“多供应商”的额外价值可能来自容量、价格、可用性和延迟差异；**不能直接视作推理错误更独立的证明。**

已有专门面向多模型、多供应商的系统，例如 [vLLM Semantic Router](https://arxiv.org/abs/2603.04444)。它证明这种架构已有工程实现，但不是三维优势的普遍证明。genui{"citation":{"ref":"turn20academia2"}}

**2．确实存在一个可证明的弱命题，但不能过度解读**

下面是一个简单的集合包含推导，不依赖具体组合形式。

设 \(\Pi_1\) 是所有允许的单模型策略，\(\Pi_+\) 是允许使用模型池的策略。若后者可以原样执行前者，且不增加强制开销，则：

\[
\Pi_1\subseteq\Pi_+.
\]

定义预算和期限下的最优成功概率：

\[
V_\Pi(B,D)
=
\sup_{\pi\in\Pi}
\Pr_\pi(Y=1,\ C\le B,\ T\le D).
\]

立即有：

\[
V_{\Pi_+}(B,D)\ge V_{\Pi_1}(B,D).
\]

**证毕：大集合上的最优值不低于其子集上的最优值。**

但这只说明：

- 扩大可选策略集合，理论上限不会变差；
- 最优策略可能仍然只用一个模型；
- 不保证严格提高；
- 不保证有限数据、有限搜索预算下能找到更好的策略；
- 如果强制增加路由、状态转换等开销，“原样包含”条件就不再成立。

因此，**“多模型可选”有不劣的理论依据，“实际使用多个模型”没有无条件不劣保证。**

**3．更强的理论支持，来自“可识别的条件优势”**

最值得读的是：

[A Unified Approach to Routing and Cascading for LLMs](https://arxiv.org/abs/2410.10347)，ETH Zurich，2024，2025 更新。

它给出路由、级联及二者结合的最优策略分析，核心结论是：**质量估计能力决定这些方法能否有效。** 路由需要调用前预测某模型是否合适；级联需要调用后判断答案是否足够好。理论优化针对其定义的质量与成本估计，不能自动变成真实环境中的最优保证。genui{"citation":{"ref":"turn20view0"}}

可以用下面这个自行推导的式子理解机会来源。固定权重，令

\[
u_m(x)=p_m(x)-\lambda c_m(x)-\mu t_m(x).
\]

理想路由的收益空间是：

\[
G=
\mathbb E_x\!\left[\max_m u_m(x)\right]
-
\max_m\mathbb E_x[u_m(x)]
\ge 0.
\]

若不同输入上，最优模型确实不同，且没有一个固定模型几乎处处最优，则 \(G>0\)。

现实中还要扣除：

\[
\text{净收益}
=
G-\text{选择误差损失}-\text{执行额外开销}
-\text{摊销学习成本}.
\]

**这给出了比“模型多样性有益”更精确的条件：优势必须互补、可预测，而且值得付出识别成本。** 这里是固定效用下的分析，不等于三项指标分别都改善。

**4．实证既支持，也反对：必须一起看**

| 研究 | 支持什么 | 不能推出什么 |
|---|---|---|
| [FrugalGPT](https://arxiv.org/abs/2305.05176) | 学习模型级联，可以在所测任务上降低成本、保持或提高准确率 | 没有由此证明墙钟时间也同时降低。genui{"citation":{"ref":"turn18search0"}} |
| [RouteLLM](https://arxiv.org/abs/2406.18665) | 强弱模型路由能改善成本—质量权衡，并展示更换模型后的迁移能力 | 主要是请求级实验，不是通用长程 harness 的三维结论。genui{"citation":{"ref":"turn18search1"}} |
| [EvoRoute](https://arxiv.org/abs/2601.02695) | 在 agent 工作流内逐步选择模型，直接评估性能、费用和墙钟时间 | 支持若干工作负载的可行性，不证明多数任务或供应商组合均占优。genui{"citation":{"ref":"turn13view4"}} |
| [Rethinking Mixture-of-Agents / Self-MoA](https://arxiv.org/abs/2502.00674) | 同一强模型多次生成再聚合，在多个场景胜过混合不同模型 | 直接否定“换成异构候选自然更强”的简单前提。genui{"citation":{"ref":"turn18search2"}} |

Self-MoA 尤其重要：它发现模型输出质量下降，可能抵消多样性收益。**单模型并不等于单次采样；同一个模型也能通过采样、提示与策略变化产生候选多样性。**

因此，我们的对照必须包含“同一模型多次尝试”，否则可能把增加计算的收益误认为异构模型的收益。

**5．最新、最贴近这个猜想的两篇补充**

**[Resample or Reroute? Budget-Aware Test-Time Model Selection](https://arxiv.org/abs/2607.08665)，2026-07。**

它直接比较：剩余预算应该继续采样当前模型，还是转向另一模型？在 11 个开放权重模型、四个基准的回放实验中，作者报告成本—质量前沿改善；收益在异质性更强的基准上较大，并随着验证器质量下降而缩小。**这非常贴近我们的研究，但属于回放证据，也没有完整解决墙钟时间目标。**genui{"citation":{"ref":"turn21academia2"}}

**[FlexRouter: Learning Complementary Model Sets](https://arxiv.org/abs/2609.38585)，2026-09-29。**

它显式建模模型间冗余与互补，优化“候选集合中至少有一个正确答案”的覆盖率，并报告域内、域外收益。局限也明确：**覆盖率是上游能力，最终交付还依赖验证器或用户选择。**genui{"citation":{"ref":"turn17academia2"}}

这两篇共同把问题推进到了：

> **新增模型能解决哪些当前模型多次采样仍难解决的情况，以及系统能否识别那些正确结果？**

**6．对多供应商，需要单独验证另一种互补**

多供应商可能提供的是**服务层互补**，而非能力互补。

例如，令 \(F_A,F_B\) 表示两个端点无法在期限内完成请求。联合失败概率为：

\[
\Pr(F_A\cap F_B).
\]

只有在独立假设下，它才等于 \(\Pr(F_A)\Pr(F_B)\)。共享云基础设施、网络路径、上游模型服务或限流机制，都可能造成相关性。因此不能仅凭公司名称不同，就代入独立公式。

[ContinuityBench](https://arxiv.org/abs/2607.15899) 专门研究多供应商故障转移，指出 API 可用性恢复不代表对话状态连续，并测量状态保留与切换延迟。它提供了工程参考，但不证明多供应商普遍改善三维表现。genui{"citation":{"ref":"turn20academia1"}}

对我们的 harness，合理的选择单元应是：

\[
(\text{模型},\ \text{服务端点},\ \text{调用配置}),
\]

分别估计能力、价格、延迟与服务失败，而不是把它们混成一个“模型评分”。

**7．我认为置信度更高的方向**

以下是证据强度判断，不是统计后验概率：

| 判断 | 当前可信程度 |
|---|---|
| 允许多模型，并保留单模型路径，值得作为架构能力 | 高 |
| 对难度混合的任务分布，低开销路由能改善成本—通过率权衡 | 较高，有多项研究支持 |
| 对模型存在条件优势、且有可靠验证的任务，异构尝试能扩展前沿 | 较高，但须与同模型重采样比较 |
| 多供应商可改善受限流、故障或拥塞影响的完成率与尾延迟 | 条件成立时有依据，须实测相关性与切换开销 |
| 多模型在多数任务上同时更快、更便宜、通过率更高 | **证据不足** |
| 任意增加不同供应商模型都能提高结果质量 | **不成立** |

要证明“多数情况下”，还必须先指定“情况”的分布：按任务实例、任务类别、预算区间，还是供应商运行状态计数？没有这个定义，“多数”无法检验。

**我建议把项目的核心猜想写成：**

> **在预先定义的任务与服务状态分布上，若模型／端点存在可学习的条件互补性，则允许动态选择和按需组合、保留单模型回退的 harness，能够在计入学习与协调成本后，扩展单模型策略的时间—成本—通过率前沿。**

验证它时，至少保留四组对照：

1. 单模型完整策略，包括同模型重采样；
2. 同供应商多模型；
3. 跨供应商多模型；
4. 同一模型跨端点——若条件允许，用于分离服务层收益。

先测模型池的潜在互补，再测实际选择器能兑现多少，最后计入全部费用与时间。**这能把“多模型看起来更强”转化成可证伪、可归因的研究命题，也避免提前把异构组合写成必然正确的架构前提。**


===== [assistant/thoughts] 10-07 10:02 node=5f02fd65 len=6 =====
Worked


===== [user/text] 10-07 10:49 node=4b459e83 len=46 =====
只要采用了存在多模型可能性的设计,那么就必须引入路由以及判断路由机制.你的对照机制设计我认可


===== [assistant/thoughts] 10-07 10:49 node=a0213cd5 len=6 =====
Worked


===== [assistant/text] 10-07 10:49 node=1053d759 len=663 =====
对。**只要允许多模型，模型选择就成为 harness 的内生决策，路由及其判断成本必须纳入系统。** 我前面“保留单模型路径，因此理论不劣”的说法，需要严格限定：它成立于策略集合的抽象包含关系，不能直接保证具体实现不劣。

即使最后决定“继续用当前模型”，系统也可能已经支付了观测、判断和维护状态的成本。若采用静态绑定，这些成本可以主要发生在配置阶段；若采用动态选择，则进入运行时。**低开销不等于零开销。**

因此，我们认可的四组对照应保留，并额外区分两种单模型基线：

| 对照 | 作用 |
|---|---|
| **原生单模型 harness**：没有路由组件 | 测量多模型架构的完整净收益 |
| **同架构固定单模型**：保留通用封装，固定模型选择 | 分离通用封装开销与动态选择的影响 |
| 同供应商多模型 | 测量模型组合的实际收益 |
| 跨供应商多模型 | 测量扩大候选池后的净收益 |
| 同模型跨端点，条件允许时 | 分离服务层与模型能力的收益 |

其中，原生单模型基线也应允许重试、并行采样和其他优化，避免刻意弱化它。

我们的研究问题据此可以更准确地写成：

> **在计入路由判断、状态维护、校准、切换及协调的全部开销后，多模型 harness 能否相对充分优化的单模型 harness，扩展墙钟时间—成本—通过率前沿？其成立条件是什么？**

接下来应当把**“采用多模型架构是否值得”本身作为待验证假设**，而不是把它当成免费扩大的设计空间。你认可的对照机制，正好能检验这个前提。


===== [user/text] 10-07 10:50 node=de11ed7b len=28 =====
现在没有完整工作给出我们想要的这个结论吗?或者部分结论?


===== [assistant/thoughts] 10-07 10:50 node=80775f59 len=6 =====
Worked


===== [assistant/text] 10-07 10:50 node=cd6be844 len=86 =====
我会再核对最接近的论文，重点看它们是否同时包含：真实墙钟时间与费用、充分优化的单模型对照、路由全部开销，以及跨模型和跨任务验证。然后区分已有完整结论、部分结论和仍缺的证据。


===== [assistant/thoughts] 10-07 10:50 node=fb64b8e6 len=16 =====
Searched the web


===== [tool/text] 10-07 10:50 node=e3f86261 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 10:50 node=2f8eca22 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-07 10:50 node=537ca66e len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-07 10:50 node=3c28b627 len=14 =====
Worked for 32s


===== [assistant/text] 10-07 10:50 node=5d33e39a len=2238 =====
**有部分结论，而且已有工作相当接近；不能说这个方向尚无证据。** 我前面把“尚未证明普遍占优”强调得过多，容易让你误以为需要从零验证可行性。更准确地说：

> **多模型系统在具体任务上同时提高通过率、降低费用和墙钟时间，已有实证；但计入全部开销后，相对充分优化的单模型，在广泛未见任务上仍普遍占优，我尚未找到完整证明。**

**最接近我们目标的是 EvoRoute，而且它提供了直接的三维结果。**

我重新核对了 [EvoRoute](https://arxiv.org/abs/2601.02695) 的结果表。以相同 CK-Pro 框架、GAIA 全集为例：

| 配置 | 通过率 ↑ | 费用 ↓ | 报告的累计延迟 ↓ |
|---|---:|---:|---:|
| 固定 Claude-4 | 58.28% | $359.32 | 45.14 h |
| 固定 GPT-4.1 | 48.48% | $61.84 | 23.04 h |
| EvoRoute | **63.19%** | **$85.40** | **38.75 h** |

它**三维同时优于固定 Claude-4**；相对 GPT-4.1，则提高通过率，但更贵、更慢。因此这里已经有“共同改进”的实例，也有明确的权衡。genui{"citation":{"ref":"turn24view0"}}

此外，作者并非完全忽略初始化：附录报告冷启动用了 **$28.8、约 3.6 小时**。但我还不能确认主表是否完整涵盖每一类路由开销；也没有看到我们要求的“同模型重采样充分优化＋跨供应商因素分离＋未见模型和任务联合留出”的完整对照。genui{"citation":{"ref":"turn23view2"}}

所以对它应作的判断是：**直接的、局部三维优势证据，值得复现；不是普遍优势定理。**

其余工作提供了几个可直接采用的部分结论：

| 工作 | 已有结论 | 与我们目标之间的缺口 |
|---|---|---|
| [A Unified Approach to Routing and Cascading](https://arxiv.org/abs/2410.10347) | 在其数学设定下推导最优路由／级联；指出质量估计是成败关键 | 主要是质量—成本优化；估计目标最优不等于真实三维最优。genui{"citation":{"ref":"turn20view0"}} |
| [RouteLLM](https://arxiv.org/abs/2406.18665) | 降低成本并保持质量；展示更换强弱模型后的迁移能力 | 对模型迁移已有支持，但不是长程 harness 的墙钟三目标验证。genui{"citation":{"ref":"turn18search1"}} |
| [MCPP](https://arxiv.org/abs/2605.06110) | 在预算和期限约束下，动态模型与并行采样分配提高工作流完成概率 | 依赖预先给定的工作流和执行统计，不能直接推广到任意开放任务。genui{"citation":{"ref":"turn10view1"}} |
| [Resample or Reroute?](https://arxiv.org/abs/2607.08665) | 将“同模型再试”和“换模型”作为竞争决策；回放结果支持成本—质量前沿改善 | 尚缺真实墙钟目标；验证器变差时收益缩小。genui{"citation":{"ref":"turn21academia2"}} |
| [Self-MoA](https://arxiv.org/abs/2502.00674) | 多个场景中，同一强模型的多次输出聚合优于异构模型聚合 | 说明异构性本身不能作为优势依据，必须保留强同构对照。genui{"citation":{"ref":"turn18search2"}} |

**因此，我们现在可以接受哪些研究前提？**

我认为已有证据足以接受：

1. **多模型的实际净收益可以为正，三维同时改善是可实现的。** 这不是纯猜想。
2. **收益取决于任务分布、模型互补、质量判断和执行开销。** 已有理论和正反实验都支持这种条件性。
3. **同模型重采样与换模型必须共同优化。** 直接固定使用异构组合，证据更弱。
4. **跨模型迁移有部分证据，广泛跨任务迁移仍需验证。**

尚不能接受的是：

> “只要构建一个足够好的通用多模型 harness，就能在多数任务上三维胜过充分优化的单模型。”

这里欠缺的不是“再发明一种组合方法”，而是**对优势范围与失效边界的系统辨识**。已有论文的组合起来的证据，也不能替代一套统一协议下的验证。

**对我们的下一步，这意味着无需先证明多模型可行。** 可以将 EvoRoute 作为最接近的正向参考，将 Self-MoA／同模型重采样作为强对照，再检验三个具体问题：

- 把全部路由和初始化开销计入后，优势剩多少？
- 换模型、换任务类别后，优势还能保留多少？
- 哪些可观测条件能预测“换模型值得”，哪些条件应继续使用当前模型？

**这些部分结论已经足够支撑开展工程研究；不足以支撑预先承诺一个普遍占优的最终架构。**


===== [assistant/thoughts] 10-07 10:51 node=af194ec1 len=6 =====
Worked


===== [user/text] 10-08 01:27 node=04b0fe3d len=75 =====
仔细阅读这个:[https://arxiv.org/abs/2610.01618](https://arxiv.org/abs/2610.01618)


===== [assistant/thoughts] 10-08 01:27 node=9139443e len=6 =====
Worked


===== [assistant/text] 10-08 01:27 node=8ce753f9 len=52 =====
我会读正文、实验和附录，重点核对它对我们讨论的多模型 harness、三维优化及对照设计能提供什么证据。


===== [assistant/thoughts] 10-08 01:27 node=ec6f1b6b len=16 =====
Searched the web


===== [tool/text] 10-08 01:27 node=c8b9a3ec len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:28 node=72740ece len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:28 node=d3107a12 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:29 node=71a16d11 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:29 node=ba21f576 len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-08 01:29 node=2d38fcd7 len=17 =====
Worked for 1m 56s


===== [assistant/text] 10-08 01:29 node=1a1d0367 len=2484 =====
读完正文和相关实验附录后，我的判断是：**这篇论文给出了我们需要的部分证据，而且值得据此修改研究设计；但它没有证明“多模型／多供应商 harness 通常在时间、成本、通过率上优于单模型”。**

如果此前把相关研究概括成“还没有系统性工作”，这个说法需要收窄：**已有系统性的 harness 因素评估，尚缺的是我们设想的、计入完整开销的多模型优势验证。**

**论文真正提供的证据**

[《Agents Are Systems, Not Models: Rethinking Agentic Evaluation》](https://arxiv.org/abs/2610.01618)研究的是单个主控模型使用专业模型资源，围绕信息、推理、验证、预算和主控模型做因素实验；范围是四项科学任务。它并非跨供应商路由系统的对照研究。genui{"citation":{"ref":"turn29view0"}}

对我们最关键的是以下四点：

| 发现 | 应如何理解 |
|---|---|
| 主实验中，提供有效操作信息可以提高得分，同时降低运行时间和估算成本 | 支持“改善系统设计存在三维同向收益”，但得分不等于通过率 |
| 信息因素的重要性会随模型变化；Sonnet 的预算因素排名更高 | 同一配置的收益不能直接迁移到其他模型 |
| 天文学问答中，99.8% 的运行使用了较弱专业模型；平均准确率为 68.5%，主控直接回答为 96.7% | 增加可用模型并不保证系统会正确选择 |
| 提供参考答案评分的 oracle 验证提高了结果质量，也增加了时间和成本 | 有效验证仍然可能只是改变取舍，未形成三维支配 |

这些分别见正文结论、跨模型实验、附录 A.13 和 oracle 消融。genui{"citation":{"refs":["turn29view0","turn28view0","turn29view2","turn29view1"]}}

还有两处口径必须保留：**成本主要按 token 和标价估算，并非完整实际运行成本；部分得分分析只覆盖完成的运行。**因此不能直接把这些结果当作端到端“实际花费—墙钟时间—全部任务通过率”的结论。genui{"citation":{"refs":["turn29view1","turn28view1"]}}

**它怎样改变我们的判断**

以下是我针对我们项目的推论，而非作者已经证明的结论。

**1. “多模型可用”与“多模型获益”之间，缺的是可靠的选择能力。**

那个使用较弱专业模型的结果尤其重要。我们原来的假设可以拆成三个命题：

- 不同模型之间存在能力或成本互补。
- harness 能识别当前任务是否值得利用这种互补。
- 利用互补所得的收益，超过判断、调用、协调和验证的开销。

第一条成立，不能推出后两条。我们的研究核心应当是后两条。

因此，路由的动作空间必须包含 **“继续使用当前模型”“不调用专业模型”“立即结束”**。只研究“额外调用哪个模型”，会预先排除一个可能最优的选择。

**2. 需要把“信息优势”与“模型组合优势”分开。**

我建议在我们已认可的单模型／同供应商多模型／跨供应商多模型对照之外，再交叉设置一条轴：

| 对照 | 主要回答的问题 |
|---|---|
| 相同文档、接口描述、任务知识，不同模型组合 | 收益是否来自模型组合？ |
| 相同模型组合，不同信息提供机制 | 收益是否来自信息获取与组织？ |

否则，多模型系统如果拿到了更完整的模型说明、任务流程和验证规则，最终赢了，也不能把增益全部归因于多模型。

尤其需要区分：**预先知道正确流程的配置**，与**运行时自行找到正确流程的机制**。后者才接近任务无关 harness 的目标；检索、试探和学习流程的花费必须计入。

**3. “模型无关”应当指接口和控制机制可迁移，而非所有模型共用固定策略。**

我建议把目标定义为：

> 同一个控制框架可以接入新模型，并以有限校准成本适应其能力、价格、速度和失败模式。

这样允许策略随模型改变，同时仍然具有模型无关性。更强的“换模型后完全无需校准仍然最优”，应该作为单独的迁移实验，而不是默认前提。

任务无关也类似：可以要求控制器通用，但任务的成功判定仍需由环境或评估接口提供。

**4. 三维目标足够作为主目标，但需要更严格的统计定义。**

我建议主评估采用：

\[
S_\pi(t,c)=
\Pr\!\left(
\text{任务通过}\ \land\
T_{\mathrm{端到端}}\le t\ \land\
C_{\mathrm{完整}}\le c
\right)
\]

即：**策略 \(\pi\) 在时间和成本双预算内的成功概率。**

这样可以直接比较不同预算区间，而不必任意把三项指标压成一个加权分数。超时、崩溃和未提交都进入分母，路由及验证开销也进入预算。

再补充平均成本、时间分位数和重复运行置信区间，解释成功概率背后的代价。通用性、稳定性可以作为分层评估和约束，无须立即扩展成五六个平行优化目标。

**对我们研究定位的具体建议**

这篇论文之后，我不建议把贡献写成“发现 harness 很重要”，也不建议先承诺“多模型普遍优于单模型”。

更值得验证的命题是：

> **在信息条件公平、允许拒绝额外调用、计入决策与执行完整开销的条件下，自适应多模型 harness 能否在跨任务、跨模型测试中，扩大优于充分调优单模型基线的时间—成本预算区域？**

这里还应把优势拆成两种：

- **相同通过率下，同时更快、更便宜**：强证据。
- **某些预算区间更优，另一些区间退化**：仍有价值，但应报告适用边界。

这篇论文最有价值的作用，是让我们的核心问题更精确：**资源互补什么时候能转化成净收益，控制器又能否在收益不足时及时拒绝使用额外资源。**


===== [user/text] 10-08 01:34 node=9661b6c7 len=92 =====
详读这一篇,不只是机制,还有具体实现,相关引文:[https://arxiv.org/abs/2601.02695](https://arxiv.org/abs/2601.02695)


===== [assistant/thoughts] 10-08 01:34 node=65ac94e5 len=6 =====
Worked


===== [assistant/text] 10-08 01:34 node=10733df9 len=69 =====
我会核对正文、附录和公开代码，沿关键引文追查方法来源，重点看算法如何实现、实验支持哪些结论，以及能否用于我们的三维优化 harness。



===== [assistant/thoughts] 10-08 01:34 node=10772430 len=6 =====
Worked


===== [assistant/thoughts] 10-08 01:34 node=7cfeb096 len=16 =====
Searched the web


===== [tool/text] 10-08 01:34 node=47a10d92 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:34 node=bfa55a86 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:34 node=131320b8 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:34 node=3ab723cd len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-08 01:34 node=a4edfc33 len=101 =====
这篇确实直接研究三维目标。初读发现两个需要细核的地方：摘要提到“轻量决策模型”，正文实际采用统计采样；表格中的部分结果是三维同时改善，部分仍是取舍。我正在对照正式发表版和代码，确认这些差异及开销口径。



===== [assistant/thoughts] 10-08 01:35 node=6e22130a len=59 =====
Searched the web, ⁨ran⁩ ⁨⁨2⁩ commands⁩, and ⁨used⁩ ⁨GitHub⁩


===== [tool/text] 10-08 01:35 node=9158bc35 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:35 node=c04ce1b5 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:35 node=2fb345db len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:35 node=17597ec6 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:36 node=2099383c len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-08 01:36 node=d7b24112 len=130 =====
作者给出的 EvoRoute 仓库目前返回 404，所以我无法做源码级核验，会明确区分论文写明的实现与需要补齐的细节。另一个重要发现是：它先按历史均值裁掉被支配模型，再做 Thompson sampling；这一步可能提前排除证据不足的新模型，影响后续探索。



===== [assistant/thoughts] 10-08 01:36 node=f881d646 len=36 =====
⁨Used⁩ ⁨GitHub⁩ and searched the web


===== [tool/text] 10-08 01:36 node=3a60a8f8 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:36 node=bba6f374 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:36 node=5a62d8b8 len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-08 01:37 node=5812a5a5 len=13 =====
Worked for 3m


===== [assistant/text] 10-08 01:37 node=1a0ac8b0 len=9188 =====
**EvoRoute 与我们的目标直接对齐：它明确优化“任务表现—货币成本—墙钟时间”，并给出了多模型逐步路由优于若干固定模型配置的实验结果。**但详读后，我会把它定位为：**值得复现的研究原型，而非已经证明普适优势、可以直接移植的成熟实现。**

本次核对了 arXiv 正文和附录、ACL 2026 正式版，以及关键引文。实现核查有一个明确限制：作者提供的 [bingreeky/evo-route](https://github.com/bingreeky/evo-route) 仓库目前返回 **404**，因此下面区分“论文明确规定的算法”“实现缺口”和“我的推导”。正式发表版仍给出同一代码地址。genui{"citation":{"refs":["turn33view4","turn35view2"]}}

**一、它究竟优化什么：已有工作流中的模型分配**

EvoRoute 的输入是一个已经存在的 agent 系统：角色、工具、调度流程基本由原框架提供。它改变的是：

\[
\underbrace{\phi(i)}_{\text{角色 }i\text{ 固定使用某模型}}
\quad\longrightarrow\quad
\underbrace{\rho(i_t,q_t,\mathcal K)}_{\text{当前步骤根据经验选择模型}} .
\]

因此，它主要研究**逐步骤模型路由（step-level model routing）**，没有同时搜索工作流拓扑、提示词、并行度或验证机制。它的“自进化”主要指经验库不断更新，使后续选择改变，不要求微调执行模型。genui{"citation":{"ref":"turn30view1"}}

这也纠正了我们最初的一个前提：**“静态配置”不等于“单模型”。**固定让规划角色使用 A、搜索角色使用 B，本身已经是多模型系统。EvoRoute 主要挑战的是固定分配，而非仅仅证明模型数量从一增加到多的价值。

其目标写成：

\[
\max_\rho
\left(
\mathbb E[P(\tau)],
-\mathbb E[C(\tau)],
-\mathbb E[D(\tau)]
\right).
\]

这里的多目标最优应理解为寻找 Pareto 解，而不是存在一个策略同时达到三个指标各自的独立最优值。论文没有证明“Agent System Trilemma”是不可能性定理；它是对经验取舍的命名。genui{"citation":{"ref":"turn30view1"}}

**二、按实际执行顺序，把算法展开**

**1. 先建立经验库**

每个历史步骤保存：

\[
R_t=
\langle
i_t,l_t,q_t,e_t,T_t,c_t,d_t,\sigma_t,P(\tau)
\rangle .
\]

| 字段 | 含义 |
|---|---|
| \(i_t,l_t\) | 角色、实际使用的模型 |
| \(q_t,e_t\) | 子任务指令及其向量表示 |
| \(T_t\) | 实际调用的工具集合 |
| \(c_t,d_t\) | 该步骤的成本、耗时 |
| \(\sigma_t\) | 步骤执行是否成功，如工具调用是否报错 |
| \(P(\tau)\) | 整条任务轨迹的最终表现 |

由于最终结果要到任务结束才知道，完整记录需要在轨迹完成后回填。**工具调用成功与任务回答正确，是两个不同信号。**genui{"citation":{"ref":"turn31view0"}}

冷启动采用 TaskCraft 中的 **50 个任务**，分别运行 Smolagents 和 CK-Pro，每一步从模型池均匀随机选择模型。作者报告得到约 **480 条步骤记录**，花费 **28.8 美元、3.6 小时**。genui{"citation":{"ref":"turn31view2"}}

有一处实现描述不充分：引言说优化阶段采用“树状探索、多轨迹采样”，但附录具体交代的是上述随机模型选择流程，没有给出完整的分支、回滚、扩展与停止算法。**不能据此把它当成已经明确实现的 MCTS 或其他树搜索。**genui{"citation":{"refs":["turn30view1","turn31view2"]}}

**2. 当前步骤到来后，做三路检索**

\[
\mathcal K_{\rm cand}
=
\mathcal K_{\rm role}
\cup
\mathcal K_{\rm semantic}
\cup
\mathcal K_{\rm tool}.
\]

注意是**并集**：

- 角色相同，就纳入；
- 子任务语义相近，就纳入；
- 工具使用有交集，也纳入。

语义表示使用 MiniLM，余弦相似度阈值为 **0.85**。工具预测先做关键词匹配；没有命中时，调用 **Qwen3-14B** 判断可能需要哪些工具。genui{"citation":{"refs":["turn31view0","turn31view2","turn33view1"]}}

我的实现判断：并集提高了召回率，但也可能让“同一个宽泛角色”的大量旧记录淹没真正相似的任务。论文给出的统计公式没有按相似度、时间或任务难度加权。

此外，MiniLM 的**确切 checkpoint、池化方式、截断方式**没有在这些参数说明中明确。仅知道“MiniLM＋0.85”，还不足以严格复现检索集合。

**3. 按模型聚合历史表现，再做 Pareto 筛选**

对候选模型 \(l\)，计算：

\[
\hat P_l=\frac1{n_l}\sum_{r\in\mathcal K_{\rm cand}(l)}
P(\tau_r)\sigma_r,\qquad
\hat C_l=\frac1{n_l}\sum_r c_r,\qquad
\hat D_l=\frac1{n_l}\sum_r d_r.
\]

删除那些在三维均值上被其他模型支配的候选，留下经验 Pareto 集。genui{"citation":{"ref":"turn33view0"}}

这里的“Pareto-optimal”有严格的适用范围：**它是检索样本中、按当前估计得到的模型集合，不是完整任务策略的真实 Pareto 前沿。**

**4. 最终选择由统计采样完成**

正文 §4.3 的最终选择并不是再让一个 LLM 判断。它为每个模型的三个指标分别构造 Normal–Inverse-Gamma，简称 **NIG**，再采样效用：

\[
U_l=\tilde P_l-0.1\tilde C_l-0.05\tilde D_l,
\qquad
l^*=\arg\max_l U_l.
\]

因此可以把实现还原为以下流程；这是依据论文重述的伪代码，并非作者源码：

```text
接收当前角色与子任务
→ 预测工具、计算语义向量
→ 合并三路检索结果
→ 按模型统计表现、成本、耗时
→ 删除经验均值上被支配的模型
→ 构造分布并采样效用
→ 调用选中模型执行
→ 记录步骤结果
→ 任务结束后回填最终表现，更新经验库
```

模型池包含 Qwen3-14B、GPT-4o、GPT-4.1、Claude 4 Sonnet，以及 Gemini 2.5 Flash/Pro。genui{"citation":{"refs":["turn32view1","turn33view1"]}}

**三、数学与实现上，最值得核查的五处**

以下是我的独立分析，不应误读为作者已经确认的问题。

**第一，式（11）与标准 Thompson sampling 存在实质区别。**

标准 TS 的思路是：采样未知模型参数，再选择该参数下**期望效用**最大的动作。它所引用的 Russo 等人的教程也如此定义。genui{"citation":{"ref":"turn41view1"}}

EvoRoute 写的是：

\[
(\tilde\mu,\tilde\sigma^2)\sim {\rm NIG},
\qquad
\tilde x\sim \mathcal N(\tilde\mu,\tilde\sigma^2),
\]

然后用 \(\tilde x\) 比较效用。也就是在采样参数之后，**又采样了一次未来观测结果**。genui{"citation":{"ref":"turn32view1"}}

区别在于：

\[
\operatorname{Var}(X\mid\mathcal D)
=
\underbrace{\operatorname{Var}(\mu\mid\mathcal D)}_{\text{认知不确定性}}
+
\underbrace{\mathbb E[\sigma^2\mid\mathcal D]}_{\text{结果自身的随机性}}.
\]

数据增加后，第一项可以收缩，第二项通常不会。因此按论文公式执行，**即使已充分了解候选模型，选择仍会受结果噪声影响**。不能直接套用标准 TS 的收敛或遗憾保证。

这是值得单独消融的实现差异：比较“采样均值后决策”和“采样预测结果后决策”。

**第二，NIG 参数需要补充边界处理。**

正文给出：

\[
\nu_n=n,\quad
\alpha_n=n/2,\quad
\beta_n=(n-1)s^2/2,
\]

但参数设置又给出 \(\alpha_0=0.5\)。在通常的 NIG 参数化下，后验形状参数应包含：

\[
\alpha_n=\alpha_0+n/2.
\]

另外，单条记录时样本方差无法正常估计；记录全为成功或全为失败时，性能方差可能为零，造成 \(\beta_n=0\) 的退化。论文没有充分交代这些分支。genui{"citation":{"refs":["turn33view0","turn33view1"]}}

这不等于实际代码必然报错，但意味着**不能直接照公式写完，就声称复现了作者实现**。

**第三，先裁剪、后探索，可能阻断探索。**

如果一个模型因为早期少量坏样本被均值 Pareto 筛选剔除，后面的 TS 根本没有机会选中它。对于没有检索记录的新模型，候选集合构造本身也不会自动纳入它。

因此，“采用 TS”并不足以保证新模型能得到有效探索。工程上需要额外规定未知模型入口、最低探索概率，或基于不确定性的支配判断。

**第四，终局奖励回填不等于解决信用分配。**

用 \(P(\tau)\sigma_t\) 给步骤赋分，便于实现，却不能直接识别某个模型的因果贡献：

- 前面的规划错了，后面的正确执行也可能拿零分；
- 强模型负责困难步骤，历史均值可能更低；
- 同一轨迹的多条记录共享终局奖励，样本并非相互独立。

所以它估计的是**历史分配策略下的关联表现**，不一定是“此刻换成该模型后的反事实收益”。

**第五，效用的量纲与未来代价不够明确。**

固定权重 \(1,0.1,0.05\) 只有在性能、美元、时间单位及归一化规则固定后才有明确意义；秒改成小时就会改变选择。论文参数说明没有充分明确决策阶段的尺度处理。genui{"citation":{"ref":"turn33view1"}}

更深一层：便宜的一步可能导致后面多次重试。我们真正关心的是从当前状态出发的**剩余任务总代价**，而不是仅比较当前步骤历史耗时的均值。这是局部路由与端到端优化之间的缺口。

**四、实验确实有三维同向收益，但不应概括成普遍支配**

以下均取论文表格；成本和小时数是实验表中的汇总量，不是单任务报价。

| 框架／任务 | 固定模型基线：表现／成本／时间 | EvoRoute：表现／成本／时间 | 判断 |
|---|---|---|---|
| CK-Pro／GAIA | Claude：58.28%／\$359.32／45.14 h | 63.19%／\$85.40／38.75 h | 三维改善 |
| Smolagents／GAIA | Claude：46.06%／\$76.90／29.10 h | 56.36%／\$15.60／8.90 h | 三维改善 |
| ReAct／DS-1000 | Gemini Pro：54.30%／\$68.33／16.17 h | 56.50%／\$23.50／11.20 h | 三维改善 |
| ReAct／DDXPlus | Gemini Pro：81.10%／\$109.85／27.65 h | 79.50%／\$65.80／20.53 h | 更快更便宜，但表现下降 |
| Smolagents／GAIA | GPT-4.1：39.39%／\$18.10／7.90 h | 56.36%／\$15.60／8.90 h | 表现和成本改善，但更慢 |

这些结果足以支持“**存在有价值的三维改善配置**”，也直接显示“对所有固定模型均三维占优”不成立。genui{"citation":{"refs":["turn33view0","turn33view1"]}}

有三项实验口径需要特别注意：

- **汇总平均会掩盖任务间取舍。**表 2 的表现栏是三项任务的平均值，成本与时间栏则是三项任务之和。平均表现略高，不代表每个任务都更好。
- **初始化与运行期费用要分账。**冷启动单独报告，论文没有提供足够细的账本来核对所有实验是否包含初始化、工具预测回退、检索及其他工具开销。
- **统计证据仍不足。**主结果没有提供足以判断小幅差异的重复运行置信区间，不能把平均表现 74.60% 对 74.27% 当作已确证的提升。genui{"citation":{"refs":["turn33view1","turn31view2"]}}

我还做了一个算术核对：按附录给出的 GAIA 各级样本数 \(53,86,26\)，CK-Pro＋EvoRoute 的分级表现应合成为：

\[
\frac{53(83.02)+86(59.30)+26(33.33)}{165}
\approx62.83\%,
\]

与表中的 **63.19%** 不一致。我也检查了正式 PDF 表格，排除了 HTML 抽取错列的解释。**这需要样本清单或运行日志说明；目前不能判断是汇总口径、实际子集还是排版错误。**genui{"citation":{"refs":["turn40view0","turn31view2"]}}

消融中，去掉冷启动、三路检索、TS、Pareto 筛选，性能分别下降 **13.21、11.22、6.52、1.52 个百分点**。按报告值看，**经验覆盖和检索比 Pareto 裁剪更值得优先复核**，但没有误差区间，不能把这些差值当成稳定的重要性排名。genui{"citation":{"ref":"turn31view1"}}

**五、沿引文追下去，最相关的是这些工作**

**1. LLMSelector：回答“为什么异构分配可能优于统一模型”**

[Optimizing Model Selection for Compound AI Systems，2502.14815](https://arxiv.org/abs/2502.14815)

它研究固定模块系统中的模型分配，采用逐模块搜索与 LLM 诊断器。理论结果依赖模块表现的单调性等条件，并非任意 agent 系统的普遍保证，也没有给出三维联合支配定理。它比 EvoRoute 更直接讨论**异构模块分配的性能价值**。genui{"citation":{"ref":"turn37view0"}}

我核读了其公开 [`optimizer.py`](https://github.com/LLMSELECTOR/LLMSELECTOR/blob/29e22f35b800c085b0fc6f520f03f8060739c5c0/llmselector/llmselector/compoundai/optimizer.py)：包含全搜索、手工分配和诊断器辅助优化，逐次替换模块模型并评估候选。它可以帮助我们构造一个关键基线：**先离线优化固定多模型配置，再检验在线路由是否还值得。**

**2. MasRouter：选择空间比 EvoRoute 更宽**

[MasRouter，2502.11133](https://arxiv.org/abs/2502.11133)

它联合选择协作方式、角色和模型，采用级联控制网络。genui{"citation":{"ref":"turn36view1"}}

公开 [`mas_router.py`](https://github.com/yanweiyue/masrouter/blob/e005f7696fe0c0412563f6cd67f4cd3712fa2822/MAR/MasRouter/mas_router.py) 中可以直接看到 `TaskClassifier`、`CollabDeterminer`、`NumDeterminer`、`RoleAllocation`、`LLMRouter`，最后构造执行图。

二者的区别很具体：

- MasRouter 主要决定**这次请求构造什么系统**；
- EvoRoute 在已有系统执行中决定**这一步使用什么模型**。

这提示我们应分开评估“工作流选择收益”和“步骤路由收益”。

**3. Thompson sampling 教程：应当回到原定义核查**

[A Tutorial on Thompson Sampling，1707.02038](https://arxiv.org/abs/1707.02038)

除了前述参数采样与结果采样的区别，教程还讨论非平稳环境、约束和序贯任务。它特别说明：在某些序贯问题中，逐步重新采样与整段轨迹保持一致的探索策略，效果可能差异很大。**引用 TS 不等于自动获得适用于长流程 agent 的保证。**genui{"citation":{"ref":"turn41view1"}}

**4. Optimas：补上局部指标与最终结果之间的关系**

[Optimas，2507.03041](https://arxiv.org/abs/2507.03041)

它为组件学习与全局表现对齐的局部奖励，并随着系统配置变化更新奖励模型；配置更新还要经过小规模全局验证。genui{"citation":{"ref":"turn41view3"}}

对我们最有用的不是立即引入额外训练，而是它提出的问题：**凭什么相信某一步局部分数提高，会改善最终任务？**这正是 EvoRoute 简单奖励回填尚未充分解决的部分。

**5. StreamBench 与 BrowseComp-Plus：决定评估是否可信**

[StreamBench，2406.08747](https://arxiv.org/abs/2406.08747)明确采用“先预测、再获得反馈、再更新”的在线协议，并测试不同任务顺序。它有助于区分合法的在线学习与预先接触评测反馈。genui{"citation":{"ref":"turn38view5"}}

[BrowseComp-Plus，2508.06600](https://arxiv.org/abs/2508.06600)的重要贡献是固定检索语料、人工核验支持文档，从而控制检索环境。**它不只是修正几个错误题目。**复现 EvoRoute 时，必须明确到底使用固定语料检索还是实时网页搜索，以及检索器配置。genui{"citation":{"ref":"turn39view2"}}

另外核查了一个容易误判的引文：EvoRoute 将 PromptLLM 和 GraphRouter 都引到 Feng 等人，并不必然是错引；GraphRouter 原文确实定义了一个名为 **Prompt LLM** 的提示式路由基线。genui{"citation":{"ref":"turn41view2"}}

**六、对我们的直接价值与复现边界**

我建议把 EvoRoute 作为**必须纳入的基线**。可以直接吸收三项设计：逐步骤观测记录、用历史经验辅助选择、把时间纳入决策。暂时不应直接继承其“最优”或“持续改善”的表述。

若要实现可审查的版本，至少需要补齐：

| 模块 | 必须明确的实现决定 |
|---|---|
| 经验记录 | 任务／步骤 ID、模型版本、供应商与端点、上下文规模、重试、反馈来源 |
| 检索 | 确切编码器、去重、条数上限、无匹配回退、旧经验失效规则 |
| 统计选择 | 小样本先验、零方差处理、指标尺度、未知模型探索 |
| 执行适配 | 工具 schema、消息格式、上下文和多模态兼容性 |
| 费用与计时 | 路由、检索、回退调用、失败重试、冷启动全部计入 |
| 在线评估 | 预测后才反馈；固定经验库与在线更新分别测试 |

**优先实验应是三个相互独立的比较：**

1. **异构性是否有价值：**充分调优的单模型，对比离线优化的固定多模型分配。
2. **动态性是否有价值：**固定多模型分配，对比每步动态路由，计入判断开销。
3. **EvoRoute 的具体机制是否有价值：**简单统计路由，对比三路检索、均值 Pareto 裁剪及两种采样方式。

这样即使最后 EvoRoute 的完整算法没有赢，我们仍能知道：收益究竟来自模型互补、动态适应、经验检索，还是某个实验配置。**这篇论文最值得继承的是可检验的算法骨架；它留下的关键工作，是把这条骨架变成计量完整、统计可靠、能处理新模型与新任务的实现。**


===== [user/text] 10-08 01:41 node=2f7512d7 len=118 =====
[https://github.com/bingreeky?tab=repositories](https://github.com/bingreeky?tab=repositories)虽然仓库丢失,但是也许作者的其他仓库会有可参考?


===== [assistant/thoughts] 10-08 01:41 node=47f9ff18 len=6 =====
Worked


===== [assistant/text] 10-08 01:41 node=3584ab2d len=49 =====
我会检查作者的公开仓库，重点找路由、经验库和评估代码，并区分可直接借鉴的实现与仅主题相关的项目。



===== [assistant/thoughts] 10-08 01:41 node=4484e9a3 len=36 =====
⁨Used⁩ ⁨GitHub⁩ and searched the web


===== [tool/text] 10-08 01:41 node=59e76248 len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-08 01:42 node=ff1ef0dd len=133 =====
已经找到几个相关项目，而且能读到源码：JIT 提供可替换的 harness 模块和执行内核，GMemory 提供经验检索，MaAS 提供工作流选择器，OPD-Evolver 提供经验使用日志和成本监控。我会再检查这些模块的调用方式和评估口径，判断哪些适合直接借鉴。



===== [assistant/thoughts] 10-08 01:42 node=54cf16e6 len=36 =====
⁨Used⁩ ⁨GitHub⁩ and searched the web


===== [tool/text] 10-08 01:42 node=03213619 len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-08 01:44 node=8938509f len=127 =====
又找到一个更直接的线索：MemEvolve 的源码确实实现了“成功率—token 消耗—执行时间”的三目标 Pareto 筛选。不过它优化的是记忆系统，成本用 token 数代替，而且该模式默认关闭。我会把这类已有实现与我们仍需验证的多模型收益分开说明。


===== [assistant/thoughts] 10-08 01:44 node=532e4ca1 len=6 =====
Worked


===== [assistant/reasoning_recap] 10-08 01:44 node=28981482 len=17 =====
Worked for 3m 23s


===== [assistant/text] 10-08 01:44 node=15942cee len=4704 =====
**有，而且找到了比“同作者的相关项目”更有用的东西：可复用的 harness 内核，以及已经实现的三目标 Pareto 筛选。** 最值得关注的是 **JIT、MemEvolve、MaAS、OPD-Evolver、GMemory**。

先校正一个表述：EvoRoute 仓库目前返回 404，只能确定公开地址不可访问，不能确定已删除。下面这些仓库也不能直接视为 EvoRoute 的源码替代品。我检查了它们的说明和核心文件，以下属于**源码静态分析，尚未运行复现**。

**按对我们目标的参考价值排序**

| 项目 | 我们可以借鉴什么 | 与我们目标的距离 |
|---|---|---|
| [JIT](https://github.com/bingreeky/JIT) | 模块化 harness 接口、执行内核、候选 harness 选择、统一评估 | 最接近整体框架；不等于多供应商动态路由 |
| [MemEvolve](https://github.com/bingreeky/MemEvolve) | **成功率、token 消耗、执行时间的三目标 Pareto 筛选**；可替换记忆系统 | 最接近优化目标；搜索对象主要是记忆架构 |
| [MaAS](https://github.com/bingreeky/MaAS) | 根据任务选择操作模块、组合工作流、提前停止的轻量控制器 | 可借鉴路由机制；主要选择工作流，不是跨供应商模型 |
| [OPD-Evolver](https://github.com/bingreeky/opd-evolver) | 分层经验库、候选/选中经验的使用记录、按模型计费 | 部分机制涉及模型训练，公开实现也有明确缺项 |
| [GMemory](https://github.com/bingreeky/GMemory) | 成功/失败经验分开检索、任务图、角色相关经验投影 | 适合参考经验层；成本统计不能直接沿用 |

**1. MemEvolve：最重要的新发现——三目标筛选确实已经写进源码**

在 [`auto_evolver.py`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/MemEvolve/core/auto_evolver.py) 中，`_pareto_select_top()` 明确使用：

\[
\max \mathrm{accuracy},\qquad
\min \mathrm{total\_tokens},\qquad
\min \mathrm{execution\_time}.
\]

实现不是只在 README 写“多目标”：

- 按三维支配关系进行非支配排序，生成 Pareto 层级。
- 同层候选再按加权分数排序：准确率权重 `0.6`、token 效率 `0.25`、时间效率 `0.15`。
- 当前系统与新生成系统在同一批任务上竞争；入围系统再接受包含新任务的评估。
- 最终选出的记忆系统成为下一轮演化的起点。

**这足以修正一个研究判断：不能把“对 agent 外部机制进行成功率—资源—时间三目标优化”本身当作空白。这里已有直接的工程先例。**

但它还没有覆盖我们完整的问题，源码里有几个重要边界：

| 实现细节 | 对我们的影响 |
|---|---|
| `use_pareto_selection=False` 是默认值 | 默认流程按准确率优先、token 次优排序；不能据此断言论文所有实验都采用三目标模式 |
| 成本指标是总 token 数 | 不适合直接比较不同模型、供应商、缓存价格 |
| 时间读取日志中的 `metrics.elapsed_time`，取有效记录平均值 | 还要追踪计时边界，确认是否含检索、维护、重试等完整开销 |
| 时间缺失时返回 `0.0` | 缺日志候选可能被误认为最快；用于我们的评估前必须修正 |
| 搜索对象是记忆系统 | 不能直接证明多模型组合优于单模型 |

它的 [`BaseMemoryProvider`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/EvolveLab/base_memory.py) 也值得参考，核心接口只有初始化、提供记忆、吸收轨迹。这种接口适合让经验机制独立于执行模型。

**我的判断：MemEvolve 应提升为我们下一篇重点精读的论文与代码，而不只是补充引用。** 对应论文是 [2512.18746](https://arxiv.org/abs/2512.18746)。

**2. JIT：最适合参考整体 harness 的接口和实验组织**

JIT 的价值在于，它把 harness 分解成可以替换的实现模块。在 [`protocols.py`](https://github.com/bingreeky/JIT/blob/main/scripts/kernel/protocols.py) 中可以看到：

- `BaseMemory`：上下文和记忆更新。
- `BasePlanning`：计划初始化、重规划和执行指令。
- `BaseAction`：持有执行主循环。
- `BaseToolPolicy`：工具选择和技能提示。

这对我们尤其有用：**模型选择可以放进执行流程，但记忆、计划、工具策略可以独立替换和做消融。**

它还区分生成 harness 的模型、执行模型和评判模型。这说明至少这套系统的设计**并不要求所有职责使用同一个模型**。不过，职责可以配置不同模型，与根据运行状态动态跨模型路由，仍是不同的能力。

候选选择代码 [`selector.py`](https://github.com/bingreeky/JIT/blob/main/jit/selector.py) 提供两条路径：

- 用候选代码的 logprob 评分。
- 用 judge 模型根据任务和候选代码选择。

这里能借鉴“生成候选→选择→只执行选中者”的组织方式，但评分还不是我们需要的联合效用估计。特别是，**代码似然不是经过校准的任务成功概率，也没有直接纳入实际时间和金额**。

还有一个非常实际的评估问题：[`metrics.py`](https://github.com/bingreeky/JIT/blob/main/scripts/eval/metrics.py) 把 `budget exceeded`、上下文超限、部分超时标记为可重跑的基础设施失败。

对我们的固定预算对照实验，预算耗尽可能正是策略失败，应该计入失败率及已消耗资源。**接口可借鉴，但评估口径需要重新定义。** 这只是代码行为与我们目标的差异，不代表其论文结果有问题。

**3. MaAS：值得借鉴的是“控制器选动作”，而不只是“分类器选模型”**

在 [`controller.py`](https://github.com/bingreeky/MaAS/blob/main/maas/ext/maas/models/controller.py) 中，任务和操作模块的嵌入经过投影、匹配和 softmax，控制器逐层选择模块，并支持 `EarlyStop`。

这为我们的路由动作空间提供了一个具体实现参考：

\[
a_t \in
\{\text{模型选择、继续执行、验证、重试、停止、切换工作流}\}.
\]

上式是**我们的扩展建议**，不是 MaAS 已经实现的完整动作集。

它的意义是：即便模型池固定，也可以通过改变执行结构减少时间和成本；多模型只是可选动作的一部分。因此，后续实验应该避免把“更好的工作流控制”带来的提升全部归因于模型多样性。

但当前控制器有固定层数、操作集合和编码方式等约束，不能直接当作任务无关的通用路由器。

**4. OPD-Evolver 与 GMemory：补经验和观测能力，但不要整套照搬**

OPD-Evolver 有两部分特别适合拆出来参考：

- [`cost_monitor.py`](https://github.com/bingreeky/opd-evolver/blob/main/opd_evolver/base/engine/cost_monitor.py)：利用上下文作用域收集调用的模型、输入/输出 token 和金额，并按模型汇总。可以作为多模型账本的起点，但还要补每次调用的时间和供应商信息。
- [`scoring.py`](https://github.com/bingreeky/opd-evolver/blob/main/opd_evolver/memory/scoring.py)：区分经验是否进入候选集、是否实际被选择，再结合任务奖励估算贡献。比仅保存最终成功轨迹更有分析价值。

不过，贡献分数是观察性统计，**不能当作经验产生收益的因果证明**。此外，该文件虽然计算了时间衰减，随后又把 `recency` 覆盖为 `1.0`，所以当前实现实际上没有应用该衰减。README 也明确说明完整训练流程尚未全部公开。

GMemory 的 [`GMemory.py`](https://github.com/bingreeky/GMemory/blob/main/mas/memory/mas_memory/GMemory.py) 则展示了：

- 成功经验与失败经验分别检索。
- 结合任务图和语义相似性扩展候选。
- 用模型做重排、经验提取与角色适配。

它可以帮助实现“利用经验判断当前该采取什么策略”。但这些检索后的处理本身会增加模型调用，必须进入总成本与总耗时。

另外，[`llm.py`](https://github.com/bingreeky/GMemory/blob/main/mas/llm.py) 的价格计算硬编码了输入、输出单价，无法直接用于多模型比较；还存在打印 API key 的代码，移植时应删除。

**这些发现怎样改变我们的研究定位？**

现在可以更明确地说：**作者其他仓库提供了相当完整的组件参考，但目前读到的这些实现，仍没有给出“多模型/多供应商在多数情况下三维都优于单模型”的统一证明。**

它们分别覆盖：

| 我们需要的能力 | 最值得参考 |
|---|---|
| 可替换、可做消融的 harness 内核 | JIT |
| 三目标候选筛选与外层搜索 | MemEvolve |
| 任务相关的工作流选择和停止 | MaAS |
| 经验使用日志与模型成本账本 | OPD-Evolver |
| 成功/失败经验检索 | GMemory |

**更有价值的研究目标，是在这些已有机制之上验证：加入跨模型选择后，在完整计入路由、验证、重试和经验维护开销的条件下，能否稳定扩展最优单模型基线的三维 Pareto 前沿。**

这比“用了多模型，所以整体更优”更可检验，也更能区分收益究竟来自模型互补、控制策略，还是更多计算预算。优先阅读顺序我建议调整为：**MemEvolve 的三目标评估 → JIT 的执行内核 → MaAS 的控制器**。


===== [user/text] 10-08 01:47 node=33643265 len=157 =====
同样精读[https://arxiv.org/abs/2512.18746](https://arxiv.org/abs/2512.18746)以及我找到的另一篇也许和判别有关的[https://arxiv.org/abs/2609.15309](https://arxiv.org/abs/2609.15309)


===== [assistant/thoughts] 10-08 01:47 node=403b40ae len=6 =====
Worked


===== [assistant/text] 10-08 01:47 node=d7a10f9d len=93 =====
我会分别读正文、附录和公开实现，重点核对 MemEvolve 的三目标优化究竟落实到哪些实验，以及第二篇的“判别”能否用于路由、验证或停止决策。也会检查上一轮源码判断与论文表述是否一致。


===== [assistant/thoughts] 10-08 01:47 node=284dd26d len=56 =====
Searched the web, ⁨ran⁩ ⁨1 command⁩, and ⁨used⁩ ⁨GitHub⁩


===== [tool/text] 10-08 01:47 node=b22d7f5c len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:47 node=9172f3e0 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:47 node=b98b2593 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:48 node=c7d5bfdb len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:48 node=1dc739d7 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:48 node=6610f19b len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:48 node=4dcf2142 len=39 =====
The output of this plugin was redacted.


===== [assistant/text] 10-08 01:48 node=23325157 len=143 =====
正文里有两点会改变我们的判断：MemEvolve 表 3 的通过率提高、API 成本略降，但三个基准的耗时都增加了，因此它不是三维同时改善的证据。第二篇则直接研究“继续当前会话，还是把预算分给独立会话”；它提供了条件性定理，但并没有训练一个通用判别器。我正在核对定理假设和公开评估代码。


===== [assistant/thoughts] 10-08 01:48 node=6e1d6185 len=53 =====
⁨Used⁩ ⁨GitHub⁩, searched the web, and explored files


===== [tool/text] 10-08 01:48 node=27e3ca67 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:49 node=d8f6cb93 len=39 =====
The output of this plugin was redacted.


===== [tool/text] 10-08 01:49 node=92823f70 len=39 =====
The output of this plugin was redacted.


===== [assistant/reasoning_recap] 10-08 01:49 node=b84590fd len=17 =====
Worked for 2m 20s


===== [assistant/text] 10-08 01:49 node=1340d82e len=7703 =====
这两篇都值得纳入我们的核心文献，但作用不同：

- **MemEvolve：提供“自动改造记忆机制”的外层优化器。**
- **When Agents Slow Down：提供“继续投入是否值得”的测量方法和条件性理论。**

第二篇与你说的“判别”确实有关，尤其是**继续、分叉、重启、停止的决策**；它本身没有训练一个通用判别模型。

我核对了正文、附录，以及两者公开仓库的关键实现。下面区分论文证据、代码行为和我的推导；没有运行昂贵的实验复现。

**一、MemEvolve：首先修正上一轮对“三目标优化”的理解**

论文确实把性能、资源消耗、延迟放进架构选择，但**采用多目标优化，不等于最后三项同时改善**。其表 3 相对无记忆基线的结果是：

| 基准 | 通过率 | 每任务 API 成本 | 平均耗时 |
|---|---:|---:|---:|
| GAIA | 69.09% → 73.33% | $0.086 → $0.085 | 505.46 → 693.33 秒 |
| xBench | 69.00% → 74.00% | $0.141 → $0.136 | 523.05 → 773.06 秒 |
| WebWalkerQA | 71.18% → 74.71% | $0.048 → $0.040 | 251.57 → 332.49 秒 |

所以，这组证据支持**提高通过率、保持或降低费用，但增加延迟**，不支持三维支配。其跨模型、跨基准迁移有积极结果，但不能据此证明任意任务上的通用性。genui{"citation":{"ref":"turn46view1"}}

按表中数值计算，三个基准的耗时分别增加约 **37.2%、47.8%、32.2%**。这对我们的目标非常关键：记忆减少执行模型的无效探索，也可能引入串行检索、提炼和维护调用，最终更省钱却更慢。

**1．它到底在优化什么？**

可以把系统分成两个状态：

\[
M：\text{记忆内容},\qquad
\Omega：\text{处理记忆的程序}.
\]

普通记忆系统固定 \(\Omega\)，只更新 \(M\)。MemEvolve 还搜索新的 \(\Omega\)。其公开实现把这一过程组织成：

```text
执行任务并记录轨迹
→ 分析记忆机制的问题
→ 生成候选设计
→ 生成实现代码
→ 验证候选
→ 在任务上比较
→ 保留候选进入下一轮
```

这不是微调执行模型，而是修改模型外部的程序。代码入口是 [`memory_evolver.py`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/MemEvolve/core/memory_evolver.py) 的 `analyze / generate / create / validate`。

**对我们最有价值的抽象：让 harness 的某些机制成为可搜索的程序，同时固定它们与执行环境之间的接口。**

不过，接口固定只保证可接入，不保证跨任务有效；候选还必须经过不同任务上的验证。

**2．“四模块抽象”与真实接口不是一回事**

概念上是编码、存储、检索、管理四部分。实际 [`BaseMemoryProvider`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/EvolveLab/base_memory.py) 主要暴露：

| 接口 | 实际职责 |
|---|---|
| `initialize()` | 初始化存储和索引 |
| `provide_memory(request)` | 返回当前任务需要的记忆 |
| `take_in_memory(trajectory)` | 从轨迹提炼并写入经验 |

编码与存储合并在写入操作里；管理没有独立的强制抽象方法。

因此，如果我们需要**逐模块消融、独立计费、异步维护、限制维护预算**，就应该进一步拆分接口，不能直接认为这份代码已经提供了这些隔离能力。

**3．进化得到的记忆具体怎样运行？**

我下钻了 [`lightweight_memory_provider.py`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/EvolveLab/providers/lightweight_memory_provider.py)：

- 任务开始时，检索并合成长程指导，控制为一次提供。
- 执行过程中，从新增上下文提取短期信息。
- 按步数间隔返回短期记忆，避免每步都注入。
- 结束后提炼战略性、操作性经验。
- 记录使用情况，并提供裁剪机制。

这里值得借鉴的不是“多存一点历史”，而是**按任务阶段决定提供何种记忆、何时提供、提供多少**。

但函数调用显示，选择、合成、提取等环节会调用模型。于是“记忆有效”必须进一步分解：

\[
\text{净收益}
=
\text{执行阶段节省}
-
\text{记忆读取、提炼、维护开销}.
\]

这解释了为什么不能仅根据执行步数减少来推断墙钟时间下降。

**4．论文与代码之间有一处重要差异**

论文描述同一 Pareto 层内优先按性能排序；当前公开代码则使用加权分数。这需要在复现时明确版本和配置。genui{"citation":{"ref":"turn44view0"}}

[`auto_evolver.py`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/MemEvolve/core/auto_evolver.py) 的实际行为是：

| 项目 | 当前代码 |
|---|---|
| Pareto 模式 | 默认关闭 |
| 开启后的三维指标 | accuracy、总 token、平均执行时间 |
| 同层排序 | `0.6×accuracy + 0.25×token效率 + 0.15×时间效率` |
| 时间记录缺失 | 返回 `0.0` |
| 默认选择模式 | 准确率优先，token 次优 |

所以，**搜索时的“成本”是 token，结果表中的“成本”是美元，两者应当分开描述**。跨供应商后，这种区别会更加显著。

计时边界也有具体发现：在 [`run_flash_searcher_mm_gaia.py`](https://github.com/bingreeky/MemEvolve/blob/main/Flash-Searcher-main/run_flash_searcher_mm_gaia.py) 中，计时开始于 provider 加载之后，结束于答案判断和记忆吸收之后。因此，该入口的耗时含部分任务后处理，却不含 provider 初始化；它也不是整个架构搜索成本。

**对我们的采用意见：借鉴其接口、候选生成和评估循环；重新实现资源账本、缺失值处理和预算约束。**

---

**二、When Agents Slow Down：它最有价值的是测量“边际计算收益”**

论文研究开放式任务，提出 Elo 随 token 预算变化的分析，并给出独立采样的理论参考线。在 Polyomino Packing 上，100M token 分成三个会话，相比一个会话提高 264 Elo；但附录中的另一任务上，一、二、三个会话统计上难以区分。其理论依赖独立性、连续得分、等成本及相容的评分尺度等条件，并非普遍最优路由定理。genui{"citation":{"ref":"turn46view0"}}

**1．先弄清“判别”的三个不同层次**

| 层次 | 判断什么 | 这篇工作的覆盖 |
|---|---|---|
| 解的判别 | 哪个候选结果更好 | 主要依靠任务自带评测器 |
| 策略的判别 | 哪种预算分配更有效 | Elo 曲线与分配实验 |
| 在线动作判别 | 此刻继续、切模型还是重启 | 可提供依据，但没有直接交付通用控制器 |

因此，它更接近**决策所需的测量和诊断层**，而不是可以直接放进 harness 的 verifier。

**2．公开实现怎样把轨迹变成 Elo？**

[代码仓库](https://github.com/agent-tts/Agent-TTS-Code) 的主要数据流是：

1. agent 在执行中多次提交候选。
2. 评测器返回分数，日志记录累计 token。
3. 每个预算检查点取历史最佳分数。
4. 在同一任务内比较不同系统、会话和预算的结果。
5. 用 Bradley–Terry 模型拟合等级分。

设会话 \(\tau\) 在预算 \(b\) 前的最佳成绩为

\[
S_\tau(b)=\max_{i:b_i\le b}s_i.
\]

比较产生胜、平、负，再拟合

\[
\Pr(A>B)
=
\frac{1}{1+10^{-(r_A-r_B)/400}}.
\]

这里 **Elo-per-token 不是 \(r/b\) 的简单比值**，而是研究 \(r(b)\) 的曲线及其斜率。

代码上应优先读 [`export_selfelo_ci.py`](https://github.com/agent-tts/Agent-TTS-Code/blob/main/analysis/export_selfelo_ci.py)，而不是只照搬早期 `elo_fit.py` 的分桶示例：

- Self-Elo 排除同一会话不同检查点之间的比较。
- 加入对称伪比赛，避免全胜、全败导致无穷估计。
- 按完整会话 bootstrap，保留轨迹内部依赖。
- 每个系统独立拟合的 Self-Elo 不能直接比较绝对高低。

排除同会话比较尤其合理：历史最优值天然不下降，用后面的自己击败前面的自己，会制造额外的上升信号。

**3．为什么独立采样会出现“每十倍预算 400 Elo”？**

下面用交换性直接重推。

设两组分别有 \(n,m\) 个独立同分布的连续得分，取各组最大值 \(M_n,M_m\)。连续性保证总共 \(n+m\) 个样本的最大值几乎必然唯一；交换性使它落入第一组的概率为

\[
\Pr(M_n>M_m)=\frac{n}{n+m}.
\]

代入 Elo 的胜率变换：

\[
r_n-r_m
=
400\log_{10}
\frac{\Pr(M_n>M_m)}{1-\Pr(M_n>M_m)}
=
400\log_{10}\frac nm.
\]

若每次尝试成本相同，样本数正比于预算，便得到参考斜率。

**这个结果强在不依赖具体连续分布，弱在它仍然需要独立同分布、等成本，以及可靠取到最优候选。** “400”来自 Elo 的刻度约定，不是自然界的计算常数。

**4．为什么这还不能直接成为我们的停止规则？**

有四个需要补齐的环节。

**第一，曲线是跨会话统计量，当前会话的状态价值可能不同。**

离线曲线下降，不意味着一个刚获得关键突破的会话也应该立刻停止。真正的控制器需要估计：

\[
V(a\mid h_t,B_C,B_T),
\]

其中 \(h_t\) 是当前历史，\(B_C,B_T\) 是剩余金额和时间；动作 \(a\) 可以是继续、分叉、重启、换模型或验证。

**第二，斜率交叉点不自动等于有限预算全局最优点。**

若额外假设评分尺度相容，可以构造一个近似分配目标：

\[
R_B(b)\approx r(b)+400\log_{10}\frac{B}{b}.
\]

其内部驻点满足

\[
\frac{\mathrm dr(b)}{\mathrm d\log_{10}b}=400.
\]

但若曲线多次交叉、有启动成本、会话不独立，或者预算很小，就要比较所有候选点与边界。**交叉条件只是这个近似模型的必要条件，不是无条件最优性证明。**

**第三，我们关注的通过率不满足连续得分假设。**

若每次尝试以概率 \(p\) 通过，独立尝试 \(n\) 次的通过率是

\[
P_n=1-(1-p)^n.
\]

它会饱和。比较两组二元结果、平局记半分，期望比赛得分为

\[
W_{n,m}
=\frac12+\frac12\bigl(P_n-P_m\bigr).
\]

当两组通过率都趋于 1，\(W_{n,m}\to \tfrac12\)，并不会一直保持上述连续得分的 400 参考斜率。

因此，**开放式算法优化可以采用 Elo 曲线；二元任务仍应保留通过率和达到目标通过率所需资源的曲线。**

**第四，最优候选必须真的可以识别和交付。**

代码采用历史最佳提交，而真实任务未必有可靠评测器。如果候选选择会出错，就必须测量

\[
P(\text{最终选中结果通过}),
\]

而不能用“候选中至少一个通过”的 oracle pass@\(k\) 替代。判别调用的金额和等待时间，也必须计入总预算。

**5．公开工程实现有哪些可直接参考、哪些尚不能复现？**

| 实现 | 可借鉴点 | 我们需要处理的边界 |
|---|---|---|
| Harbor + 独立评测服务 | 执行与评测隔离；中间提交可观测 | 评测服务排队和运行时间必须计入墙钟 |
| continuation/watchdog | 长会话恢复、预算控制 | 强制继续后的表现不等于原 agent 的自主停止策略 |
| 检查点分析 | 不同预算下统一比较 | token 不能代替跨供应商美元成本 |
| Session bootstrap | 保留会话相关性 | 固定任务集合的区间不代表跨任务泛化区间 |

还发现两个会影响复现的具体问题：

- [`export_selfelo_ci.py`](https://github.com/agent-tts/Agent-TTS-Code/blob/main/analysis/export_selfelo_ci.py) 会对提前结束的会话延续最后成绩，并记录 `alive_frac`。这可能使曲线变平；分析时要区分真正停止改善与未继续观测。
- [README](https://github.com/agent-tts/Agent-TTS-Code#data) 说明原始轨迹和聚合数据另行发布；当前公开 CLI 适配器的 `cost_usd` 为 `None`。因此，这份发布可以参考和重跑，但不能据此直接复核全部已报告曲线或完成美元成本比较。

---

**三、合起来看，对我们的多模型猜想有什么实质推进？**

**它们最直接支持的是“应当优化计算的组织方式”，还没有证明“多模型一定比单模型更优”。**

可以把原来的对照进一步明确为：

| 对照 | 要隔离的收益 |
|---|---|
| 单模型、单会话 | 基础性能 |
| 同模型、多会话 | 独立探索及预算分配收益 |
| 多模型、多会话 | 模型异质性在独立探索之外的增益 |
| 多模型、动态切换 | 状态相关路由的额外收益 |

每一项都应匹配**总费用和墙钟预算**，并计入相同的候选判别机制。否则，多模型系统的提升可能只是来自多启动了几个会话。

这里还有一个可以直接推导的有用边界。设独立会话使用模型 \(m\)、预算 \(b\) 时的得分分布为 \(F_m(y\mid b)\)，且能够准确选出最好结果，则

\[
\Pr\!\left(\max_iY_i\le y\right)
=
\prod_i F_{m_i}(y\mid b_i).
\]

若在相同资源条件下，一个模型对其他模型处处具有一阶随机支配，即

\[
F_A(y\mid b)\le F_B(y\mid b)\quad\forall y,
\]

那么把 \(A\) 的会话换成 \(B\)，不会改善最大值的分布。**这已经说明：多样性本身不足以保证收益。**

更值得寻找的条件是：

- 不同模型在不同任务或状态上各有优势。
- 它们的失败相关性不同。
- 成本、速度、限流和缓存结构不同。
- 控制器能以足够低的开销识别并利用这些差异。

因此，我们的核心判别对象最好从“哪个模型更强”推进到：

> **在当前状态和剩余预算下，把下一份资源分给哪个动作，能获得最大的可验证增益？**

MemEvolve 可为这类决策提供可演化的经验处理机制；EloScaling 可为其提供轨迹级测量。但两者之间的**在线价值估计与预算控制**仍需单独构造和验证。

**四、相关引文里，哪篇最接近你说的“判别”？**

我沿第二篇的参考文献核对了三篇：

| 文献 | 对我们的价值 |
|---|---|
| [OpenDeepThink，2605.15177](https://arxiv.org/abs/2605.15177) | 用模型进行候选两两比较，再用 Bradley–Terry 聚合排名；比 EloScaling 更直接涉及在线候选判别 |
| [Scaling Test-time Compute for LLM Agents，2506.12928](https://arxiv.org/abs/2506.12928) | 系统比较并行采样、顺序修订、验证/合并及轨迹多样化 |
| [EdgeBench，2607.05155](https://arxiv.org/abs/2607.05155) | 补充长程真实任务和墙钟时间维度的测量 |

OpenDeepThink 尤其值得下一步精读：其候选比较会产生批评意见，用于后续变异；不过作者也报告收益在不同领域并不一致，不能把成对判别当作普遍可靠的评分器。genui{"citation":{"ref":"turn53view0"}} 另外两篇分别补齐策略比较和长程环境评估。genui{"citation":{"refs":["turn53view2","turn53view1"]}}

**当前最值得采用的研究组合是：可替换的记忆与控制机制、完整资源账本、独立会话基线、可审计的候选判别，以及状态相关的资源分配实验。** 其中同模型多会话基线必须先进入对照，否则无法识别多模型组合本身的贡献。
