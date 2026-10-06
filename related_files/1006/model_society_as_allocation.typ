// 讨论稿,不是审查报告。2026-10-06。
// 编译:make 1006/model_society_as_allocation   (或 typst compile 1006/model_society_as_allocation.typ)
// 本文无 \addbibresource:外部来源是搜索转述、未逐篇打开,做成 .bib 会声称比实际更多的核实。
// 它们以行内引证 + §5 来源表的形式出现,并逐条标等级。
#set document(title: "society是一个分配问题:六条判断、一个 kill criterion、一个第一步", author: "rsi-dev", date: datetime(year: 2026, month: 10, day: 6))
#set page(paper: "a4", margin: (x: 22mm, y: 20mm), numbering: "1")
#set text(lang: "zh", font: ("Noto Sans CJK SC", "Noto Sans"), size: 10pt)
#set par(justify: true, leading: 0.7em, spacing: 0.75em)
#set list(indent: 1.1em, body-indent: 0.5em)
#set enum(indent: 1.1em, body-indent: 0.5em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 14.5pt)
#show heading.where(level: 2): set text(size: 11.5pt)
#show math.equation: set text(font: "New Computer Modern Math")
#show link: set text(fill: rgb("#1f5d8f"))
#show table: set block(breakable: true)
#set table(inset: 4.5pt, stroke: 0.35pt + luma(70%))

#align(center)[
  #text(size: 17pt, weight: "bold")[society是一个分配问题]
  #v(3pt)
  #text(size: 13pt)[六条判断、一个 kill criterion、一个第一步]
  #v(8pt)
  #text(size: 9.5pt)[2026-10-06 · 讨论稿 · 仓库 `main` @ `2c0ae5b8`(本文提交前) · 本地无 remote]
  #v(2pt)
  #text(size: 9.5pt)[触发:token-plan 订阅在同一 API 下提供多个模型;多方实测显示不同模型在不同任务上效果各异]
]

#v(8pt)

#block(stroke: 0.5pt + luma(60%), inset: 9pt, radius: 4pt, breakable: true)[
*状态*:讨论稿。六条判断是我的,不是文献综述的复述;文献只起佐证作用。

*证据分级沿用本仓库惯例*:【我复核】= 我亲自算过或读过原文(本仓库内的工件);【二手】= 搜索转述,未逐篇打开原文;【推断】= 我的判断。§5 给出完整来源表与分级。*第一、二、三条判断不依赖任何外部数字* —— 它们依赖本仓库自己的 exp1 复算与 `a0/` 的测量。

*标注约定*:轮次编号指 `related_files/conversation/user_turns.md` 中的 user 轮次;`path:line` 指仓库内文件。

*术语*:本系列一律用 `society` 这个名词指「多个模型按任务、任务阶段与自身发挥自适应形成的协作结构」,不译作「模型社会」—— 该词是构想者自己起的英文名,译掉会把把手拆掉。中文只用于「人类社会」「人类制度史」与构想者原话里的「社会契约」。
]

= §0 一句话立场

*「模型之间如何协作」被问错了层级。该优化的不是拓扑(swarm / 投票 / 辩论),而是一个异质、有价、相关的动作空间上的分配策略;第一个该建的工件不是 society,是一张测出来的联合能力结构。*

理由浓缩成三句:可交换集成的数学在异质模型下不适用,而这套数学的失效条件本仓库已经亲自算过(§2.1);token-plan 的实际计费是一个*带拐点的多维硬约束*(credits 触顶即停、合同并发上限、账户级 RPM/TPM、时段倍率),文献的连续价格假设在这里不成立(§2.2);三种常见拓扑的天花板都在验证器那一步,而验证器是本仓库现有最强的资产(§2.3)。

= §1 层级错误:拓扑是手段,分配是问题

常见的两种协作形态 —— 主模型派发-验收-继续(swarm),与并行运行后竞价/投票 —— 都是*拓扑*。拓扑回答「谁和谁说话」,不回答「下一单位预算给谁、带什么信息、由谁验收」。后三者才是 C 线冻结的 Allocate 能力:

#quote[把下一单位有限资源分配到最高预期研究价值处。 #h(1em) `research_state_control_review_v4.tex:1254, 1579`]

而 Allocate 覆盖六种资源:token、wall-clock、实验、检索、subagent、*human attention*(`v4.tex:1254`)。模型选择与模型组合是这六种资源上的动作,不是第六种新能力。⇒ society问题*不是第五条研究线*,而是 Allocate 的动作空间扩张;因此它继承 kill chain(`RQ1 → RQ2 → RQ3`,RQ4 并行)与验证器优先的纪律,而不是另起炉灶。

这个落位有实际后果:它意味着society的第一件仪器,与 `a0/` 的第一件仪器是同一件 —— *先证明尺子准*。

= §2 六条判断

== 2.1 异质性使可交换集成的数学失效,而这套数学的失效条件本仓库算过

加权多数票的最优性(权重正比于正确率的对数几率,Nitzan & Paroush 1982)成立的前提是*条件独立 + 已知精度*。2026 年的一篇 ensemble 工作明确指出 LLM proposer 之间存在强依赖,并给出反例命题:精度优先、互信息优先、多样性优先三种启发式*都会选错最优的 proposer 组合*,因为真正起作用的是成员彼此之间、以及成员与聚合者之间的互补(团队效应)【二手,arXiv:2605.24048】。

更根本的一层在本仓库内部。exp1 的复算证明:*固定边际精度、固定两两相关 $rho$,多数票成功率仍然不被决定* —— 高阶联合结构才决定。36 格实测与可交换 β-二项模型最大偏差 0.331 pp(150000 trials 下 SE ≈ 0.118 pp,最坏 2.79σ),而被审查的那张表在 $rho=0.7$ 偏离同一模型 6.5–9.2 个 SE【我复核,`viz/src/data/experiments.json`、梳理 §6.3】。另有实测报告跨供应商错误相关性 60% 以上,同质输入下多样性项塌到零,MoA 与 Crowd Ensemble 打不过单个 CoT agent【二手,arXiv:2607.01661】。

⇒ 任何只估计「每个模型多准 + 两两一致率」的投票设计,估计的是*错误的充分统计量*。第一个仪器应该是:每个任务族上、冻结验证器下的*失败集合重叠结构*(哪些错误是共享的),加*与聚合者的互补性*。单模型排行榜回答不了这个问题。

== 2.2 计费核对:预算是带拐点的多维硬约束 —— 本节第一版是错的

*本节在用户质疑后重写。* 第一版写「token-plan 让边际 token 价格≈0(直到配额)」,没有核对平台计费规则。核对四个官方文档页(我亲自抓取,见 §5)后,结论改为:*钱没有消失;它变成一个带拐点的月度硬上限,消耗速率随模型与时段变化;并发与 RPM/TPM 是另外两条独立的合同硬上限。*

#table(
  columns: (auto, 1fr, auto),
  table.header([约束], [平台规则(官方原文要点)], [等级]),
  [Credits 月度额度], [Lite 11,500 / Essential 25,500 / Standard 45,000 / Pro 180,000;30 天周期;*未用完不结转*;续费不叠加], [我复核],
  [硬停], [「月额度触顶即暂停服务」;可购加油包 ¥100 = 20,000 Credits ⇒ *影子价格 ¥0.005 / credit*], [我复核],
  [消耗速率], [以 Credits 统一计量,*无公开的固定 token↔credit 换算*;构成因子(模型/思考模式/工具调用/系统提示词/schema/reasoning 是否计入)官方页未列,经搜索转述], [我复核(无换算)+ 二手(构成)],
  [时段倍率], [22:00–08:00 调 qwen3.8-max / qwen3.8-flash 享 4 折;deepseek-v4-pro-0813 / v4-flash-0731 / v4.1-flash 享 5 折(标「限时」)], [我复核],
  [并发], [*合同条款*:Lite 1–2、Essential 2–3、Standard 3–4、Pro 6–8 个 Agent 并发], [我复核],
  [RPM / TPM], [账户级共享(全部业务空间与 API Key);按秒突发 RPS = RPM/60、TPS = TPM/60,*瞬时突发即使分钟总量未超也限流*;429;1 分钟重置], [我复核],
)

四条推论,每条都改变设计:

+ *k 路并行被合同封顶。* ensemble 的 k 不超过档位并发数(Standard 为 3–4)。要提高 k 只能升档 —— *钱轴从并发这一项回来*,不是从 token 项。
+ *唯一公共分母是 credit。* 既然无固定换算、速率随模型变化,能力矩阵每格就不能记 pass\@1 或调用数,而要记 *verified-success per credit* 与 *per wall-clock-hour*:一个两货币前沿。平台计量器不透明(无公开换算、构成项二手),所以只能当黑盒读数:*用它测量,但任何跨月比较都要重新标定*,正如 `a0/` 对待未审计的评测器。
+ *时段是第四种可分配资源。* 夜间 4 折/5 折使同一次调用的 credit 成本差 2.5 倍;加上不结转,月末未用 credit 的边际价值为 0。⇒ 最优策略在时间上*非均匀*:breadth 重的批次放夜间与月末,延迟敏感的单调用放白天月初。没有任何拓扑讨论包含这个轴。
+ *硬停使失控集成的爆炸半径等于一个月。* 触顶即暂停,且不结转意味着本月剩余工作全停。⇒ 任何society 策略必须带*每实验冻结的 credit 预算* —— 这正是 `B_"hard"` 的纪律;没有它,一个 ensemble bug 可以吃掉整月。*这是核对计费后我认为最强的新结论。*

对照 `a0/`:$B_"hard" = (T_"wall" 1800 s, "CEq"_"max" 1966519, N_"evaluatorCalls" 725, P_"concurrency" 1)$ 的四元组,与平台给出的(墙钟、credits、RPM/TPM、并发)*同构*。所以正确的移植不是「把墙钟当唯一约束」,而是*把四元组的冻结纪律整体移植到订阅上*。

文献默认「每个 token 都有价格」,所以推 cascade(FrugalGPT 报约 98% 成本削减、RouteLLM 报约 85% 成本下保留约 95% 质量【二手,arXiv:2603.04445】)。在带拐点的月度硬上限下这个默认同样不成立:边际 credit 在额度内为 0、额度外为 ∞(暂停),*价格函数不连续*,而 cascade 的全部分析假设它连续。

== 2.3 天花板在验收/验证那一步,不在混合那一步;而验证器是现有最强的资产

swarm 的「验收」、投票的「聚合」、cascade 的「升级判据」是同一个东西:*验证器*。D 线 L5(生成价值是验证器质量的函数)被独立审查判为不可证伪,但方向正确;`a0/` 已把它做成纪律:`EID*` 冻结评测器、A0.1 记三元组 `(passed, measured, total)` 而非布尔、以及那个*在计算器自身里发现的假通过漏洞*(conformance 只比 status、从不读 `failure.kind`)【我复核,`a0/STATUS.md` §4、`a0/A1-RESULT.md` §2–§3】。

2026 年两条外部证据指向同一处:

- *校准 ≠ 控制*:把置信度的 ECE 从 0.286 校到 0.019,*控制后悔仍停在 0.415* —— 校准好的失败预测器仍可能是「该不该干预」这个控制决策的错误目标【二手,arXiv:2606.21399】。另一条工作把未校准置信度的 ECE 0.12 用一行 isotonic 校到 0.03、成本降 31%【二手,arXiv:2605.18796】。两条合读:校准值得做,但*校准不是终点*。
- *自置信不可用*:RLHF 的系统性过度自信使口头置信度在*错误输出上*最膨胀,正好把 cascade 依赖的信号反相;三级流水线里 90% 的链式置信度可塌到约 42% 真实精度【二手,tianpan.co 2026-04-20】。

⇒ 升级信号不能是模型的自置信,只能是*便宜的外部检查*。于是集成在一个有验证器的系统里的真实价值是:*通过验证的候选之并集*,即一个搜索/广度收益,上界是验证器的召回。可测,不神秘。自一致性在强模型上的收益也支持这个读法:20 条采样路径只换来 HotpotQA +0.4%、MATH-500 +1.6%,成本线性【二手,arXiv:2511.00751】。

== 2.4 三种拓扑是三个不同的 estimand;统一起来是一次测量

#table(
  columns: (auto, 1fr, 1fr),
  table.header([拓扑], [它实际在估计什么], [价值的前置条件]),
  [swarm 派发-验收-继续], [串行策略;价值全在验收规则], [验证器的召回与假阳率],
  [并行后投票/竞价], [集成;价值要求低共享错误相关], [信息不对称;同质输入下不成立],
  [cascade / routing], [分配;价值要求校准的升级信号], [外部检查,而非自置信],
)

唯一被文献证明真能买到多样性的杠杆是*设计出来的信息不对称*:把证据切成共享与私有子集(InfoDelphi)【二手,arXiv:2607.01661】。而这正是本仓库冻结 packet / frozen corpus 纪律的另一种说法 —— `v4.tex:463` 规定「使用受控 exogenous packet 做因果 timing assay……这样分离 information timing 与 query formulation/source quality」。*同一个杠杆,两条线各自独立发现了它。*

⇒ 用本仓库自己的估计量 $V_B(pi)$(冻结预算下的策略价值差)去量,拓扑之争消解成一次测量:$Delta = V_B(pi_"social") - V_B(pi_"best-single+verifier")$,在等墙钟预算下。

== 2.5 不舒服的推论:society是代理谬误的候选实例

轮次 \#11(09-17 09:48)的原话:

#quote[你也没必要纠结于要实现或者改进 ada 或者 opl 了,这会陷入代理谬误……货架式方案能满足目的就尽量减少工作]

C 线第四轮把同一条纪律写成了可证伪约束(`v4.tex:1604`):

#quote[因此,当前最合理的下一步不是继续扩张架构,而是让真实研究运行开始产生 RQ1--RQ4 所需的数据,并首先实现一个极薄的 Evidence/State prototype。若该薄层不能在真实 campaign 中降低恢复成本、重复劳动或 human load,就应当缩减甚至放弃,而不是用更大的 ontology、更多 agent 或更复杂 world model 掩盖失败。这是从 $G_0$ 出发最重要的可证伪约束。]

把「更多 agent」换成「更多模型」,这句话一字不改地适用于society。

== 2.6 kill criterion(写在建造之前)

#block(stroke: 1pt + rgb("#be123c"), inset: 10pt, radius: 4pt, breakable: true)[
在 $N$ 个任务族、冻结验证器、*等墙钟预算*下,若所有society 策略的 verified-progress-per-wall-clock-hour 都不超过「校准后的 best-single + 验证器」,则 society 不建。

该判据的测量成本约为一轮 calibration campaign;它比任何拓扑设计都便宜,且一旦通过,后面所有设计都有了共同的分母。
]

= §3 第一步:四个工件,复用现有仪器

+ *能力矩阵*:3 个已有验证器的任务族(`a0/` 算法类、带测试的代码类、带 checklist 的抽取类)× 计划内各模型。每格记三样:pass\@1 带置信区间、*失败集合*、以及 *verified-success per credit 与 per wall-clock-hour*(§2.2 推论二;credit 读数取自平台控制台,黑盒,跨月比较前重新标定)。验证器冻结、prompt 冻结、重复次数与*每实验 credit 预算*预注册(§2.2 推论四)。
+ *联合结构*:两两失败集 Jaccard + 2×2 分歧表;然后用本仓库的 β-二项机器*预测*多数票成功率并与实测对拍。预测失败 ⇒ 异质/相关结构是承重的 —— 这本身就是一条结果,且落在已有线上(它是 exp1 在异质情形下的推广)。
+ *四策略等墙钟对拍*:best-single / 校准 route / 多数票 / 验证器升级 cascade。估计量 $V_B$ per wall-clock hour。
+ *一个信息不对称臂*:证据切分(共享/私有)对同质臂。文献里唯一真有效的杠杆,也是本仓库 packet 纪律的自然延伸。

这四件加起来,是 `B0a`(reveal 时机识别)从「何时获取外部工件」平移到「哪个模型、带什么信息」的版本。它不需要新仪器:计量、冻结、假绿陷阱清单都已在 `a0/` 里。

= §4 与既有结构的落位

#table(
  columns: (1fr, 1fr, 1fr),
  table.header([本文的判断], [落在既有的哪个节点], [出处]),
  [联合能力结构是第一工件], [A−1/A0.1/A0.2「先证明尺子准」的模型版], [`a0/STATUS.md` §3],
  [异质集成数学失效], [exp1 的 β-二项复算;L1 的裁决], [梳理 §6.3;独立审查 L1],
  [墙钟是绑定货币], [Allocate 的六资源之一;`B_"hard"`], [`v4.tex:1254`;`A1-RESULT.md` §6],
  [天花板在验证器], [L5;`EID*`;A0.1 假通过漏洞], [独立审查 L5;`STATUS.md` §4],
  [信息不对称是唯一杠杆], [冻结 packet / frozen corpus], [`v4.tex:463`;`TIMING-REVIEW` §4.2],
  [society = Allocate 的动作空间扩张], [RQ3(foresight & resource rationality)], [`v4.tex:1553`],
  [kill criterion], [crystallize conservatively(第九条)], [`v4.tex:1601, 1604`],
)

⇒ 没有新线。若将来要把它画进结构图,它是 `capA`(Allocate)下的一组新动作,边类型用「实例化(收窄)」,不是「包含」。

= §5 证据分级与来源

*【我复核】(本仓库工件,亲自算过或读过)*

- exp1 与可交换 β-二项的 36 格对拍:最大偏差 0.331 pp,SE 0.1183 pp \@150000 trials,最坏 2.79σ(`ρ=0.7, N=3`);被审查表在 `ρ=0.7` 偏 6.5/8.6/9.2σ \@30000。`viz/src/data/experiments.json`、梳理 §6.3。
- `B_"hard"` 与「墙钟是约束,钱不是」:`a0/A1-RESULT.md` §6、`a0/TIMING-REVIEW.md` §2.7。
- 验证器假通过漏洞、`EID*` 冻结、A0.1 三元组:`a0/STATUS.md` §3–§4、`a0/A1-RESULT.md` §2–§3。
- Allocate 六资源、RQ3、第九条原则、1604 的可证伪约束、463 的 packet 规定:`research_state_control_review_v4.tex:1254, 1553, 1592-1601, 1604, 463`。
- 代理谬误的命名:轮次 \#11,`related_files/conversation/user_turns.md`。

*【我复核,外部官方文档,2026-10-06 亲自抓取】*

- `platform.qianwenai.com/pricing/token-plan`:四档并发 1–2 / 2–3 / 3–4 / 6–8;额度以 Lite 倍数表示(2.25× / 4× / 16×,该页无绝对值);Harness 赠送额度优先消耗、超额按量 8.8 折。
- `platform.qianwenai.com/docs/token-plan/overview`:Credits 统一计量;「月额度触顶即暂停服务,可购买加油包补充额度继续使用,或等待下一个订阅月额度重置」;「订阅月内未用完的额度不结转至下一周期」;续费不叠加。
- `platform.qianwenai.com/docs/token-plan/personal/token-plan-personal-overview`:四档绝对额度 11,500 / 25,500 / 45,000 / 180,000 Credits;加油包 ¥100/个/月 = 20,000 Credits;30 天周期;夜间 22:00–08:00 的 4 折 / 5 折模型清单。
- `platform.qianwenai.com/docs/developer-guides/administration/rate-limits`:RPM/TPM 定义;「速率限制在账户级别生效,同一账户下的所有业务空间和 API Key 共享配额」;RPS = RPM/60、TPS = TPM/60 按秒突发;三种 429 错误串;「限制在一分钟内重置」。
- *在这些页面上没有找到的*(故仍为二手):每调用 credit 的构成因子、固定 token↔credit 换算、「Token Plan 限流不可提升」的声明、抵扣顺序的显式表述。

*【二手】(2026-10-06 联网搜索转述,未逐篇打开原文)*

三次搜索中两次返回截断流;一个 OpenReview 链接是浏览器验证墙。下列编号与数字按搜索返回原样记录,§2 中凡引用处均已标【二手】。

#table(
  columns: (auto, 1fr, auto),
  table.header([来源], [本文用到的内容], [在 §]),
  [`arXiv:2605.24048`], [加权多数票最优性需条件独立;团队效应反例命题(三种启发式都选错组合)], [2.1],
  [`arXiv:2607.01661`], [跨供应商错误相关 60%+;同质输入下多样性塌缩;InfoDelphi 信息不对称], [2.1, 2.4],
  [`arXiv:2511.00751`], [自一致性在强模型上 +0.4%/+1.6% \@20 路径,成本线性], [2.3],
  [`arXiv:2603.04445`], [routing/cascade 综述;FrugalGPT ≈98%、RouteLLM ≈85% 成本削减], [2.2],
  [`arXiv:2605.18796`], [UCCI:isotonic 把 ECE 0.12→0.03,成本 −31%], [2.3],
  [`arXiv:2606.21399`], [校准 ≠ 控制:ECE 0.286→0.019 而控制后悔仍 0.415], [2.3],
  [`arXiv:2603.06616`], [RACER:风险受控的模型集合 + 弃权(分布自由的误路由界)], [2.4],
  [OpenReview `lWCLnGrHh`], [consensus ≠ correctness;多样性塌缩使一致成为共享错误的证据], [2.3, 2.4],
  [`tianpan.co` 2026-04-20], [RLHF 过度自信反相 cascade 信号;链式置信度塌缩], [2.3],
  [`aclanthology.org/2026.eacl-long.392`], [D3:对抗性多评审结构降低相关错误], [2.4],
)

*【推断】(我的判断,不来自任何文档)*

- §2.2 的「订阅计费下 breadth 便宜、depth 贵」:由 `B_"hard"` 的测量 + 订阅的边际价格结构推出,未见过直接文献。
- §2.3 的「集成价值 = 通过验证的候选之并集,上界是验证器召回」:由 L5 的方向 + 假通过漏洞的教训推出。
- §3 的四工件设计:由 `B0a` 平移而来,是设计提案不是结论。

= §6 留给讨论的问题

+ *能力矩阵的粒度*:按任务族还是按实例?按实例会过拟合到校准集,按任务族会抹掉「同一族内不同题型的最优模型不同」—— 而后者可能正是异质性的主要来源。
+ *配额是否让并发成为真上限 —— 已部分回答*:并发上限是合同条款(1–2 / 2–3 / 3–4 / 6–8,【我复核】),所以 §2.2 第一版的「breadth 便宜」确应改为「breadth 受合同并发限制」,最优 k 的上界由档位决定。*仍未测的是数值型 RPM/TPM*:官方限流页只给定义与行为,具体阈值在模型市场详情页,我没有抓到。⇒ 能力矩阵开工前先从控制台导出每个候选模型的 RPM/TPM,否则 429 会被误记为模型失败。
+ *哪个验证器便宜到能对每个候选运行*:编译/测试/conformance 是机械的、便宜的;LLM judge 不是 —— 用 judge 当验证器会把天花板问题原样搬回来(§2.3)。任务族的选择因此受「有没有机械验证器」约束,这可能比任务本身的重要性更先决定实验设计。
+ *society是否继承 kill chain*:`RQ1`(recoverability)与 `RQ2`(decision-sufficient state)未测。若society 策略的状态表示依赖跨模型的历史整合,则它隐含地假设了 RQ2;若不依赖(每轮无状态),则它放弃了长期学习(RQ4)。两种选择都该是显式的。
+ *三目标(时间-金钱-成果)在订阅下的形态 —— §2.2 核对后已部分回答*:钱轴没有塌缩,它以三种方式回来:加油包影子价格 ¥0.005/credit、升档买并发、时段倍率。*剩下要测的是一个数字:你的实际用量落在拐点的哪一侧。* 若从不买加油包且月末常有结余,则边际 credit 月内为 0、月末为负(不结转 ⇒ 结余是浪费),最优策略会主动在月末与夜间烧掉结余;若经常触顶,则边际为 ∞,一切 breadth 都要排队到下个订阅月。这一个实测数字决定 §2.2 推论三的方向,也决定「成果/钱」这一轴在该用哪个斜率。
+ *人类注意力的位置*:Allocate 的六资源里,human attention 是唯一没有仪器的。society若把更多候选推到人面前验收,它节省的机器成本可能以人类时间为代价支付 —— 而第九条要求 crystallize conservatively,即降级时保留反例。人类验收的失败反例目前没有任何记录机制。
