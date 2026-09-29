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
  #text(size: 12pt)[Independent Review Report · Consolidated Edition 2]
  #v(10pt)
  #text(size: 9.5pt)[审查对象：`open_world_algorithm_research_engineering_plan.typ` v1.0（2026-09-18，1513 行）]
  #v(2pt)
  #text(size: 9.5pt)[版本：*Consolidated 3（2026-09-20）*· 汇总 Rev. 0–6 的七轮审查 + 执行前修订 + A0 执行结果]
  #v(2pt)
  #text(size: 9.5pt)[结论：*A0 已由 rsi-dev 窗口执行完毕（R_1 = 四套全过）；下一步是 A1——选 substrate，再进 B0+*]
  #v(2pt)
  #text(size: 9.5pt)[阅读方式：*§1–§5 是正文（结论、判断、证据、实验协议、先前工作）；附录 A–D 是审计记录*]
]

#v(10pt)

#block(
  fill: rgb("#eef3f6"),
  inset: 12pt,
  radius: 5pt,
)[
  *本文件与旧文件的关系*：本文件是 `open_world_plan_independent_review.typ`（Rev. 0–6）的*清理重写版*，其首屏已标注被本文件取代。正文只保留操作性内容与结论；逐轮修订记录（R1–R58）、我对自身判断的更正清单、来源清单与审查覆盖范围移入附录。

  #v(4pt)

  *总评*：这份计划的方向与目标层判断成立，且它点名的外部系统经七轮源码级核实*没有一个是不存在的*。但它的四处事实性表述写错了（注入通道、开放世界获取前端、货架候选清单、KAPSO 的评测驱动），它的核心实验按现设计*无法识别*（分析单位错位），它的唯一护栏*无法执行*，而货架上已有比它所选组合更接近目标的现成系统。因此结论不是否定该路线，而是：*先冻结评测契约（A−1），再证明测量链可信（A0），再决定用多复杂的搜索机器（A1），然后才谈外部工件与开放世界是否值得（B0+／B0／B1）*。
]

= 一、结论

== 1.1 一句话结论

*有条件推进，且第一步是冻结评测契约（A−1），不是任何 adapter。* 计划的"架构可丢弃"原则应当执行到底——这一次执行到"连 runtime 也不预先指定"。

== 1.2 分层结论

#table(
  columns: (auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*层*], [*它回答的唯一问题，以及当前的答案状态*],
  [A−1], [评测契约冻结了吗（评测器源码、依赖锁、数据清单、配置、指标定义各有一个哈希）——尚未存在，须由我们创作],
  [A0.1], [测量链可信吗（三个 adapter 是否忠实执行同一个 $E^*$）——未验证，且已发现两处会假绿的陷阱],
  [A0.2], [各 runtime 的分数是否真的驱动搜索——三套语义不同，需按各自配置分别验证],
  [A1], [需要多复杂的搜索机器——选出后续实验的 substrate，*不判项目生死*],
  [B0+], [外部工件能被这个 substrate 利用吗（positive control）——未验证],
  [B0], [普通的外部既有实现是否提升搜索（$H_A$）——未验证],
  [B1], [主动获取外部工件值得吗（$H_O$）——未验证，且 Closed 臂未必封闭],
  [H1], [何时获取、何时内部进化——最外层问题，其分析单位在计划中尚未定义],
)

== 1.3 十六条怀疑的评级

#table(
  columns: (auto, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*编号*], [*等级*], [*一句话*],
  [D1], [重要], [计划的注入面写错：`metadata` 对 prompt 不可见，正确通道是 `code` + `text_feedback` + `metadata` 三分],
  [D2], [重要], [H1 的两种读法（$H_U$ / $H_M$）未分开；析因设计只能回答显式解释的增量],
  [D3], [重要], [统计门名实不符；功效只对候选提交门有效，且计划无功效分析],
  [D4], [重要], [唯一护栏不可执行；缺里程碑、工期、负责人；同目录缺决策沿革],
  [D5], [重要], [H2 没有实验臂；"决策策略层"仅部分占位],
  [D6], [重要], [五条未纳入的一等风险：理解成本、benchmark 污染、许可证、供应链、链接失效],
  [D7], [次要], [点名 17 个系统、正文引用 0 处、`refs.bib` 仅 6 条],
  [D8], [次要], [八处引文与命名漂移],
  [D9], [次要], [四组内部张力（时间尺度与 Phase 顺序、联合调度、发现步骤归属、Man1Lab 接口性质）],
  [D10], [重要], [开放世界获取前端不存在：Man1Lab 无搜索路径，且 `verified` 混用了 $V_D$ 与 $V_E$],
  [D11], [重要], [实验单位错位：把 evaluator seed 当成 H1 的复现单位],
  [D12], [重要], [同 seed 不等于配对：需要 event-keyed 随机源],
  [D13], [重要], [货架候选查漏：EvE 被漏掉，且它是最贴合的那个],
  [D14], [重要], [A0 不是 shootout；预算未定义；三套系统的记账能力不对称],
  [D15], [重要], [Closed 臂未必封闭；须拆 $H_A$ 与 $H_O$，并用探测验证封闭性],
  [D16], [重要], [KAPSO 的第五项缺口：机制已存在，但 *fidelity 开启后的 probe 路径存在结构性错配*],
)

= 二、对计划的判断

== 2.1 它在说什么，以及我认可的部分

计划的论证链是五步：目标重述（计划:40-49）→ 工程顺序"货架 → 组合 → 适配 → 扩展 → 自研"（计划:153-172）→ 缺口定位为 `CandidateResource → Program/Inspiration`（计划:289-301）→ 最窄切片（计划:403-413）→ 可证伪假设 H1／H2（计划:1469-1509）。

我认可并核实过的部分：

+ *目标层的重新收束*：把"提高基础设施完整度"与"提高算法改进能力"分开，并明确前者是可丢弃手段。
+ *"架构可丢弃"作为硬约束*（计划:169）——本报告正是把它用在 runtime 选择上。
+ *多时间尺度分离*（计划:235-239）。*补充*：EvE 把 solver 与 guidance 放在同一个共同进化环里，说明联合调度已有可运行实现；计划若要保留固定偏序，需要更强理由。
+ *从第一天记录轨迹以备将来 replay*（计划:581）。
+ *不继承 Man1Lab 的生成策略*（计划:474）：其 `generation_decision.py` 逐字包含 "Do not redesign algorithms or network architecture."。
+ *把外部实现交给自有 evaluator 定生死*：与 ShinkaEvolve 的 `correct = 1`、EvE 的脚本分数、KAPSO 的注册评测一致。
+ *任务选择的阶梯*（计划:998-1004）。
+ *外部事实的可核实性*：七轮核验后，计划点名的系统仍无一虚构。

== 2.2 四处事实性错误

== 2.2.1 D1：注入面写错了，但正确通道是现成的

计划 §4.3（计划:511-544）把外部灵感写入 `Program.metadata`（清单见计划:529-536）。该做法不成立：`metadata` 对 prompt 不可见。

- `sampler.py:77-207` 组装的 user message 只含 `parent.code`、`perf_str(...)` 与可选反馈段；cross 专属段 `prompts_cross.py:57-73` 只写 partner 的 `code` 与 `perf_str(...)`。
- prompt 路径上读 `metadata` 的位置只有 `sampler.py:256-263`（fix 分支），不参与 mutation 与 cross。
- 计划:529-536 的六个键在仓库中*零命中*。

*正确通道*：`prompts_base.py:58-79` 对每个程序在同一块内依次写 `prog.code`、metrics、`Text feedback:` + `prog.text_feedback`；`sampler.py:152-157` 把 archive 与 top-k 全部送入该函数；adapter 可自设该字段（`dbase.py:174`，`Database.add()` 原样落库，全仓无 `UPDATE programs SET text_feedback`）。

```text
ExternalCode      -> Program.code
MechanismSummary  -> Program.text_feedback     （MVP 捷径，非长期 canonical schema）
Provenance        -> Program.metadata
EvaluatorResult   -> (correct, score, public_metrics)
```

*三条限定*：cross 对位段无此通道；该字段属评测器语义且为单字段（机制摘要与评测反馈竞争）；重复评测会新建一行携带评测器值。另：partner 的 code 在同一 message 中*出现两次*（`sampler.py:205-208`）。

== 2.2.2 D10：开放世界获取前端并不存在

计划:58 把"开放世界获取已有相当成熟的实现基础"列为第一条工程认识，并把 Man1Lab 定为 acquisition front-end（计划:421-425、456-487）。*该成熟度对 Man1Lab 不成立*：

- `src/providers/github/client.py:61` 逐字 `raise NotImplementedError("GitHub search transport is not implemented in Phase 1.2")`，全包无调用点。
- `GitHubCollectionProvider` 的输入是论文分析里已存在的 URL（`collection.py:1, 46, 56-58, 124-153`），无 query 参数；官方审计文档逐字 "No Search API"、"deterministic, Search-free"。
- 全包无其它发现路径；ADR-0016:161 把 conditional search 列入 Phase 1，实作停在无搜索状态。

*附带的语义问题*：`verified` 被用于指两件事——$V_D$（发现层可信：仓库存在、身份、许可、归档状态）与 $V_E$（任务层可执行：在冻结 evaluator 下跑通并产生可比指标）。Man1Lab 只提供 $V_D$（ADR-0016:142 自陈 "Shallow verification does not guarantee runnable repos — Execution may still fail"）；只有 $V_E$ 通过者才能进入进化种群。

*定级*：这是*关键集成缺口*，不是研究基础设施缺口。可借路线：KAPSO 的 knowledge 面、EvE 的 `(github_url, commit)` 契约、AutoSOTA（S60）、MLE-STAR（S61）。真正的缺口不是"缺 Search"，而是*缺 Search result → executable artifact 的 resolution*。

*一处自我限定*：计划字面没有写"Man1Lab 搜索 GitHub"，故指控限定在计划:58 的成熟度判断与 §4.1 的定位上。

== 2.2.3 D13：货架候选查漏，漏掉的正是最贴合的那个

EvE（`scaling-group/eve`，arXiv:2605.09018）是本次所核系统里*唯一把 `(github_url, commit)` 写进 application contract*、并且*让外部 evaluator 的分数真的进入选择*的系统。逐条核实见 §3.3.2。

*完整性声明*：本报告*放弃*"货架候选已穷尽"这一断言。检索口径限于 arXiv 与公开 GitHub 仓库；二次查漏又发现 CORAL（S80）、EvoX Genesis（S81）等，未覆盖类包括非 arXiv 正式论文集、闭源或仅 demo 的系统、论文无仓库的双向缺失项。

== 2.2.4 D16：机制已存在，但 fidelity 开启后的 probe 路径存在结构性错配

*措辞更正（本轮）*：本报告早期把它写成"KAPSO 的注册评测默认失效"——*不准确*。`FidelitySpec.mode` 的默认值就是 `"off"`（`src/kapso/execution/fidelity.py:244`），此时 `FULL_PASSTHROUGH` 授予 full／1.0（`:318-324`），与告知 agent 的命令一致，*不会*错配。错配只发生在 fidelity 被开启之后：

```text
fidelity enabled probe path  =>  structural class mismatch
grant = (fast, eval_fast_fraction, seed)      而 agent 被告知运行 (full, 1.0, seed)
```

机制本身确实存在，只是在一个默认关闭的功能被打开时失效。

- 赋值顺序：`feedback_flow.py:66-72` 先写 judge 分数，`:76-93` 仅在 `manifest_score is not None and node.evaluation_valid` 时用 manifest 覆盖（注释逐字 "the manifest is the score of record"）。
- manifest 合法性要求三元组与授予类全等（`registered_evaluation.py:87-91`：`fidelity`、`fraction`（容差 $10^(-9)$）、`seed`），否则打印 "Manifest class mismatch … no mechanical score of record" 并返回 None。
- *结构性错配*：告知 agent 的命令被硬编码为 `--fidelity full --fraction 1.0`（`orchestrator.py:629-643`；该字符串只在 `search_strategies/base.py:735` 赋值一次、无按迭代重算），而 probe 的授予类是 `fast`／`eval_fast_fraction`（`fidelity.py:660-666`、`:247`，默认 0.15）。于是 `mode` 为 `on`／`auto` 时，*每个 probe 轮次必然错配*，judge 分数上位。
- 该分数以*授予类*标签入账：`registered_evaluation.py:124-159`（`:151` 取 `fidelity=node.eval_fidelity`、`:144-145` 取 `fraction=decision.eval_fraction`）。
- 第三条路径：manifest 行格式坏时解析异常逃出 `feedback_flow.py:106-109` 的 except，judge 分数同样留存。
- `node.score` 驱动：父代选择（`strategy.py:1373-1396`）、best 与 deliverable（`:1436-1477`）、expansion lane（`expansion_lanes.py:111-127`）、evaluator 迁移桥接顺序（`orchestrator.py:755-806`）。*不驱动* stagnation 与停止。

*硬不变量*：

```text
每条 attempt 的 (evaluator, fidelity, fraction, seed)
  必须等于产出该分数的那个 run 的 manifest 三元组
等价形式: 授予类必须等于告知 agent 的命令类
处置: mode != off 且出现错配 => 该轮计为 A0.1 failure
```

*冻结治理*：`evaluation_change_request` 默认上限 3（`orchestrator.py:616`），设 0 即关闭；一旦接受变更，E_t → E_t+1 并桥接复评（首个成功即停）。KAPSO 是三套系统里*唯一能证明"campaign 内评测器未变"*的（逐候选 `verify_evaluation_tree` 与 `verify_data_manifest`、resume 校验、版本注册 append-only 且每版一次 git commit）。

== 2.3 实验与统计缺陷

== 2.3.1 D11 + D12：分析单位与配对条件

```text
候选提交门  :  candidate × eval seeds     回答"这个候选是否真的更好"
研究系统 A/B :  task × independent runs    回答"开放世界的策略是否更好"
```

- 随机性至少三层 `Y_{t,r,s}`（$t$ task、$r$ 完整 campaign、$s$ evaluator seed）；seed 是观测单位而非实验单位（S48；S49 逐字 "Increasing the number of OUs does not increase the sample size"；S50 逐字 "the experimental unit is the number of subjects tested, rather than the number of observations made within each subject"）。
- 即使把同一 search 产出的最终候选测 34 个 seed，也只精确估计了 `Performance(A_candidate)`，并未估计 $E[pi_"open"] - E[pi_"closed"]$。
- *分析程序*：先折叠 seed 层（每 run 取均值），再建 run 级模型 $d_{t,r} = mu + u_t + v_{t,r}$（S51），或分层 bootstrap（S54）；task 仅 3 个时只报 task 级效应，禁止泛化到 task 总体。
- *r 的规划*：$r = f(sigma_"run", "MDE", alpha, beta, "design")$；由 pilot 估 $sigma_"run"$ 并取上界，*禁用 pilot 的效应量*；设计效应 $ "DE" = 1 + (m-1)rho $（S53）。
- *配对条件*：`(Open_{t,r}, Closed_{t,r})` 若实现为"两边设置相同 seed"，*不构成配对实验*。CRN 的标准条件是"同一随机数用于对应的用途/事件"（S68 逐字）；状态式 PRNG 在干预改变控制流时会失同步（S71 §1 逐字）。正确做法是 event-keyed：抽样为纯函数 `g(seed, event_key)`、用 counter-based RNG；不可控源（闭源 LLM 采样、网络检索）按 `(task, run)` 记录并冻结、两条件共用同一份快照。
- *限定*：ML 基准领域的成文做法恰是 A 与 B 复用同一 seed（S52 逐字）；正确表述是*agentic 研究使该做法的前提失效*。闭源 LLM 的 `seed` 本身不保证确定性（S72 逐字）。

== 2.3.2 D3：统计门名实不符，功效只对提交门有效

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

*要点*：$n=5$（计划:603 的 `[11, 23, 47, 89, 131]`）时最小可检测效应为 $1.68 sigma_d$；pilot 只估 $sigma$（用 pilot 效应量会因条件化选择而高估，S42、S43、S44）；$n=5$ 时 Wilcoxon 精确符号秩双侧最小 $p = 0.0625 > 0.05$，即非参数门恒零；三条件 Bonferroni 下 $n=5$、$d=1$ 功效降至 0.191；§8.1 并列 8 个"主要指标"（计划:951-962）而无单一主终点；confirmation 与 pilot 若共用 seed 则 winner's curse 未消除；per-test $alpha = 0.05$（计划:776）与 §6.2 自陈的 multiple testing 目标（计划:785）不相容；被推迟的 e-value／error spending（计划:806）正是"统计门"名称的实质内容；`time to first improvement`（计划:954）无删失规则与生存分析。

== 2.3.3 D2：H1 的两种读法未分开

```text
H_U :  OpenWorld         -> UtilityGain    第一阶段可直接检验（计划:1476-1480 的字面）
H_M :  MechanismTransfer -> UtilityGain    需要因果识别设计（§1.6／§2.2 的措辞）

C = External Code      X = Explicit Mechanism Explanation
四臂:  C + X ／ C ／ X ／ 空
对照:  C + X_matched  vs  C + X_shuffled   （token 匹配、同域但错配）
主估计量: Delta_X = Y(C + X) - Y(C)
```

- $Delta_X$ 回答：*给已经看到代码的 agent 再解释"为什么这个算法有效"，有没有额外价值？*
- 更宽意义上的潜伏机制迁移需要程序结构或行为层面的分析，*不在本设计可识别范围内*，必须明文写出。
- 若只主张 $H_U$，则计划 §1.6 与 §2.2 的机制迁移措辞（计划:344、:60）必须删除；而缩到 $H_U$ 的代价是新意进一步缩小（FunSearch 与 OpenEvolve 已在做"把历史高分放进 prompt"）。
- "adaptation diff 显示机制被使用"属*中介证据*，不能替代因果识别——Loreley 的立场与此一致（S56 逐字声明 inspiration 边 "does not show that the agent used its contents or that it caused the resulting edit"）。

== 2.3.4 D14 + D15：实验顺序与对照臂的封闭性

*A0 不是 shootout*：只要记录项规定"不比较算法分数"，它就只能回答"哪个最容易接入"。须拆成 A−1、A0.1、A0.2 与 A1（见 §4）。

*预算未定义*：`1 EvE iteration`、`1 KAPSO iteration`、`1 Loreley job` 三者不可比（EvE 一个 iteration 内有多个 solver／optimizer worker；Loreley 一个 job 内可有多轮重试）。须用资源向量。

*Closed 臂未必封闭*：

```text
ClosedRuntime --agent 自带 web--> ExternalKnowledge   =>  Closed 不属于 ClosedWorld
```

逐系统事实见 §4.3。KAPSO 的门尤其多：ideation 的 `web_search`、`implementation_web`（*默认 True*，对应 claude 的 WebSearch/WebFetch 与 codex 的 `--search`，且与 ideation 开关相互独立）、`ideation_gates`／`implementation_gates`、`knowledge_search.enabled`；但没有任何 lane 级 sandbox 参数，Bash 侧门无法用配置关闭。三套系统里只有 EvE 的 `codex_tmux` 能靠配置做到封闭。

*两个 estimand*：

```text
H_A  External Artifact Value   两臂都禁止自主外部获取; Open 臂只额外获得冻结好的 VerifiedArtifact
H_O  Open-World Research Value 放开完整 Search -> Resolve -> Verify -> Adapt
顺序: 先 B0+（positive control）与 B0（普通既有实现）, 再 B1
```

== 2.3.5 D4：护栏不可执行，治理缺沿革

```text
M_capability (基础设施期): 二元验收 + 时限 + 成本上限
M_research   (研究期):     Delta verified algorithm capability
Proxy guard:  约束 C_infrastructure / Delta ResearchCapability 长期不恶化
```

- "milestone" 在全文仅出现一次（计划:1242），§9 用的是 Phase + 验收；"Δ research capability" 无任何度量定义。
- 按字面执行会自我触发：Phase 0 的交付（`GOAL.md`、schema、evaluator hash、baseline，计划:1014-1022）与 Phase 1 的验收（"一个外部 repo 可被追溯"，计划:1055）按设计都不产生算法能力增长。
- §12.1 的冻结条件与 §14.4 的 Go 条件（计划:1375-1386）互不引用。
- 没有任何阶段的验收要求"产出 verified improvement"；§8.3 反而把首版主验收定为"基础设施能否减少真实研究成本"（计划:1006）。
- 全文唯一出现的日期是版本号（计划:30）；Sprint A–D 无时长、无 owner、无预算。
- *同目录物证（详见 §3.5）*：`adapdc_scaffold_implementation(1).typ` 声明*部分条款*取代并要求旧版标注，该动作未执行、旧版仍主张"不能同时保留相反的现行决策"，而 Makefile 把两者都编成 PDF；`algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract 高度重合却互不引用；至少三套并存的统计提交门。

*定性*：这是*治理缺陷*，不是"已经发生的事实"。新证据导致更换技术栈本身可能正是避免目标固化的行为。

== 2.3.6 D5：H2 没有实验臂

计划 §8 与 §14 的条件只有 Closed／Open／Open-Unrelated（计划:1046、1348），没有任何"自适应策略 vs 固定策略"的对照，故 H2 用本计划自身的设计无法证伪。占位情况须分轴说：

+ *检索一次后进化*：已占位（MLE-STAR，S61）。*检索与进化交替*：已占位（DeepEvolve S63、MARCO S62）。
+ *决策策略层*（把获取/适配/交叉/内部进化当作策略分配）：*部分占位*——"何时检索"（QA 域，S74）与"何时选算子"（S75）两个子轴均已占位；把*外部实现获取*与*内部进化*纳入同一策略、且 acquisition 对象带 provenance，未见明确占位。

```text
动作空间:  { ResearchExternal, RetrieveKnowledge, ContinueEvolution, RunExperiment, LearnExperience }
问题:      是否存在 pi(a_t | s_t, B_t) 使 Delta VerifiedPerformance / Cost 优于固定 pipeline
```

== 2.4 D6：五条未纳入的一等风险

+ *获取与理解被当成免费输入*：计划:58 假定获取已成熟（D10、D13），并把 `understand` 写成管道一环（计划:349）、把 `mechanism_summary` 当成应填字段（计划:639）、Phase 1 验收只要一段 summary（计划:1050）；J 的分母（计划:318）与 §12 都没有"仓库能跑但机制抽不出"的成本与失败模式。外部基线：PaperBench 最佳 agent 平均复现分 21.0%（S23）；MLE-bench 上 o1-preview + AIDE 在 16.9% 的比赛达铜牌（S24）。
+ *benchmark 污染的搜索路径*：§6.1 的"数据泄漏"只覆盖候选与 evaluator 之间（计划:751），不覆盖"上网找到他人已解出的高分方案"；而 §8.3 优先选"存在可搜索公开实现"的任务（计划:994）、第二层用公开 benchmark（计划:1002）。旁证：EES 的厂商侧能力明列 web research 与 exploit discovery，同时自认"未被标记的行不等于该任务满足闭数据协议"（S64）；MLE-bench 必须明文禁止查看网上解法并用 Dolos 与 top-50 公开 notebook 比对（S24）。*与 D15 同源*。
+ *许可证合规未管理*：`license` 仅为记录字段（计划:533、626、1046），无决策规则。准确表述：*若*生成产物在事实上复制或改编了 AGPL 代码，它*可能*构成 AGPL §0 下"基于该 Program 的作品"，须依 §5(c) 对"整个作品"作 AGPL 授权、并在 §13 条件下向远程交互者提供 Corresponding Source；但 §2 明定输出仅当"其内容本身构成 covered work"时才受约束（S31、S41）。工程上应做 License Provenance Gate：来源与依赖清单（URL + commit + hash + 许可）、指纹与相似度比对（Copilot 比对窗口约 150 字符，官方承认空文件更易命中，S32）、许可白/黑名单与义务登记、命中的派生隔离与替换重写。
+ *供应链*：计划:1217-1219 要求 clone 需显式 stage、依赖装入隔离环境、secrets 不进入 artifact，同节却允许 discovery 联网，全程无出网与凭据策略。pip 官方文档原话：默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"（S30）；torchtriton 事件中恶意依赖在 `import` 时读取 `/etc/hosts`、`/etc/passwd`、`$HOME` 下前 1000 个文件、`$HOME/.gitconfig`、`$HOME/.ssh/*` 并经加密 DNS 外传（S34）。
+ *链接与 commit 的长期可用性*：只记 URL + commit SHA（计划:1044-1045）与 hash（计划:661），无归档或镜像策略。Pew 测得 2013–2023 年网页到 2023 年 10 月已有 25% 不可访问（S33）。旁证：KAPSO 默认 seed 路径连 commit 都不固定（§3.3.1）。

== 2.5 D7 / D8 / D9：引用、命名与内部张力

*引用卫生*：正文 `@cite` 出现 0 次；`refs.bib` 仅 6 条；正文点名 17 个外部系统，其中 12 个无条目；FunSearch 全文 0 次出现（七轮独立核实为 0），MLE-bench、RE-Bench 亦 0 次。

*命名与引文漂移*：

#table(
  columns: (2.5cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*位置*], [*问题*],
  [计划:55、370], [`AHE / HarnessFix` 用斜杠并列，暗示为同一方法的别名；实为两个独立工作（S15 与 S16），且计划:1140-1141 本身把它们分作两个功能。],
  [计划:575], [`ReplayWorld` 非原文术语，Dream-RSI 原文用 replay simulator（S7）。],
  [计划:275], [字段名实为 `correct` 而非 "correctness"（S3）。],
  [计划:214], [正式题名为 "Huxley-Gödel Machine"（带连字符），S9。],
  [计划:55、1415-1416], [`SGM/RQGM` 并为一组，但按计划自己的六坐标模型分属 Commit 层与 Evaluator challenge 层。],
  [计划:1142、1414], [MGM 的核心机制是 comparative evolution / 跨谱系杂交（S10），"archive selection/mutation" 的归类丢掉了要点。],
  [计划:214], [MGM、RQGM、SE-GoS、MetaRSI、Dream-RSI 均为 2026 年 6–9 月的 preprint，却与 AlphaEvolve、DGM 并列成"系统调查"的既定文献；仅 Dream-RSI 标注了成熟度。],
  [—], [`github.com/codelion/openevolve` 已改名并跳转（S20），若引用旧地址需更新。],
)

*内部张力*：$tau_K <= tau_pi$ 要求先经验后策略（计划:236-239），但 §9 把 Bridge Policy 放在 Phase 3/5、Skill RSI 放在 Phase 6，K 晚于 $pi$；MetaRSI 与 EvE 都采用联合调度，计划的固定偏序需要更强理由；§4.1 的三个未承诺选项（计划:484-486）、§9.2 的"不实现新搜索引擎"（计划:1053）与 §14.1 的"从 Man1Lab 输出或其 schema"（计划:1317）合起来使"发现"这一步既无实现也无 owner；Man1Lab 的 Decision Foundation 为非公开 API、Repository Adaptation 仍在 roadmap。

= 三、证据

== 3.1 五个核心依赖的源码级核实

#table(
  columns: (2.9cm, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*核实结论*],
  [Man1Lab], [*阶段与规则断言为真*：Collection → Evidence → Verification → Ranking → Selection 见架构文档；六个执行阶段见执行规划文档；五个 `RULE_*` 逐字存在于 `strategy_decision.py` 并被真实用于分支；"限制算法重设计"逐字存在于 `generation_decision.py`。MIT，PyPI `man1lab` 1.3.0，无论文。*两项能力断言不成立*：（1）无"问题 → 候选仓库"搜索路径（D10）；（2）其 `verified` 仅指 $V_D$。*缺口*：计划未锚定版本；规则逻辑属非公开 API。],
  [ShinkaEvolve], [*字段清单为真*（仅 `correct` 非 "correctness"）；islands、异步评估、SQLite archive、多 provider 均为真。Apache-2.0，arXiv:2509.19349（ICLR 2026），PyPI `shinka-evolve` 0.0.7。*但 `metadata` 不是灵感通道*（D1）；且它只做单文件程序进化，不原生支持给定仓库。],
  [AgentCo-Op], [*类型名与检索机制逐条属实*：六个类型均在 `core/schema.py`，其中 `NodeSpec`／`GatePolicy`／`EvalContract` 是*被执行*的契约（`runtime.py:118-122`、`core/gates.py`、`compiler.py:206-224`）。检索确为 keyword + tag scoring。arXiv:2605.20425。*过强的一处*：`sandbox_repo` 自述 "command builder only"，只产出 docker 命令规格（dry-run），随包 adapter 多为 stub。*治理风险*：根目录无 LICENSE 文件；PyPI 包归属两次核实结论不一致。],
  [ASI-Evolve], [*sampler 断言为真*：`database/algorithms/` 下 random／greedy／ucb1／island + factory。Apache-2.0，arXiv:2603.29640，无 PyPI。*判断偏差*：计划:367 称其"结构简单"，但整库是三 agent + FAISS cognition store + 并行 worker 的完整 pipeline，作为 policy 实验台需先剥离；且只做单程序进化。],
  [Dream-RSI], [*论文真实*（arXiv:2609.14858）；*代码尚未发布*（仓库仅有 README 与 release plan），故计划:368 的"完整源码尚非稳定依赖"不仅正确、且偏保守。许可无法确认。*命名偏差*见 §2.5。],
)

== 3.2 引用的研究谱系

计划:214、§9.7、§15 引用的 10 项*全部真实存在*，编号如下（均为已核实）：

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
  [MetaRSI], [2609.06396], [有], [单内核联合调度，见 §2.5],
  [AHE], [2604.25850], [有], [可证伪的 harness 修改；仓库亦公开],
  [HarnessFix], [2606.06324], [有], [轨迹诊断与修复],
  [RobustSGPO], [2609.09646], [无官方], [权限调度],
)

== 3.3 三个货架候选的能力与边界

== 3.3.1 KAPSO（快照 `7d99b152`，MIT，PyPI `leeroo-kapso` 0.4.7）

#table(
  columns: (2.9cm, 1fr, 2.3cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [开放式网络检索], [`kapso.py:434-465`；底层 `researcher.py:75-139` 仅 list 模式返回 findings；检索经 codex 原生 web search], [成立，带限定],
  [三类研究产物], [idea／implementation／research report；study 模式返回 `Source.ResearchReport`，不存在 `Source.Study`], [成立],
  [实现条目的字段], [`types.py:96-116` 字段为 query／source／content；解析器不校验 URL], [部分成立],
  [两个 API 的签名], [`kapso.py:467-476`（`learn_knowledge`）；`1129-1154`（`evolve`，含 `initial_repo`、`resume`）], [成立],
  [检索结果注入 prompt], [是，但为纯 `str()` 拼接；`context` 的 docstring 写 "learn before evolving" 而实现无 learn 步骤], [成立但弱],
  [知识检索是否自动], [*不成立*。`initial_repo` 为空时做一次 workflow repo 搜索（top_k=1），或挂 MCP gate 交由 agent 决定], [更正],
  [闭环的可运行入口], [`run_full_loop.py` 逐字含 `research -> learn_knowledge -> evolve -> learn -> evolve` 并有 "LOOP NOT CLOSED" 断言；但是 E2E 示例脚本（依赖 codex 与 claude CLI、本地 Weaviate 与 Neo4j），CLI 无 `learn_knowledge` 动词], [成立，非产品化],
  [固定 evaluator 的接入], [registered evaluation 可让 manifest 分数成为 `node.score` 并驱动选择；须声明 `evaluation_maintainer` 块并提供按 `--fidelity`／`--fraction`／`--seed` 调用的评测脚本], [成立，非默认],
  [该机制的适用条件], [*fidelity 开启（`mode` 为 on／auto）后，probe 路径存在结构性错配*：授予类 fast／0.15 与告知命令 full／1.0 不符，manifest 被丢弃、judge 分数以授予类标签上位（D16）。`mode` 默认为 `off`（`execution/fidelity.py:244`），此时授予 full／1.0 与命令一致、不会错配], [缺口仅在该路径],
  [外部评测回调的作用], [`iteration_evaluator`：*不影响选择、停止、父代与最终分支*（S67 逐字）], [该 API 如此],
  [预算／续跑／记录／记忆], [`budget.py`、`run_checkpoint.py`、`experiment_memory`、`learning/` 与 `knowledge_base/` 均在；*成本单位为 USD、不记 token 与模型调用、codex 后端下金额恒 0*], [成立，带重大限定],
  [外部工件边界], [`Source.Repo` 只有 `(url, branch)`；两条克隆路径都不固定 commit；*无 commit 固定、无内容哈希、无 license 字段、无可执行性验证*], [缺口],
  [research → 仓库解析], [*不存在任何路径*。研究产物只经三类摄入器（页型限定为 Principle／Implementation／Environment／Heuristic，不产 URL、不 clone）；`Source.Repo` 唯一运行期构造点是命令行参数；`workflow_search.py` 消费的是 KG 中由已摄取仓库生成的页], [缺口：完全人工],
  [论文声称与代码], [论文 §4.2 声称 commit metadata、`RepoStore`、corpus manifest（含 commit identifiers）与阈值；代码只有 URL 级 provenance 与分支／时间戳], [论文超出代码],
)

*五项缺口*：

```text
1 commit 固定   2 内容哈希   3 license 记录   4 V_E 可执行性验证
5 固定外部评测驱动搜索 -- 机制已存在, 但 fidelity 开启后的 probe 路径存在结构性错配(D16),
  需配置块与适配脚本, 且默认允许 agent 请求修改评测器(max_change_requests=3)

真实缺口: Problem -> Search -> ResearchFinding -> ResolvedArtifact -> VerifiedArtifact
          其中 ResearchFinding -> ResolvedArtifact 目前完全人工
```

== 3.3.2 EvE（快照 `979065fd`，Apache-2.0）

#table(
  columns: (2.7cm, 1fr, 2.1cm),
  inset: 4pt,
  stroke: 0.4pt,
  [*断言*], [*源码核实*], [*判定*],
  [仓库与论文], [`scaling-group/eve`，Apache-2.0（含 NOTICE）；tag 仅 v0.1.0 与 v0.2.0；论文 arXiv:2605.09018，当前 v4 题名 *Evolving Ensemble of Agents*（v1 旧题名 *Evolutionary Ensemble of Agents*）；无 `CITATION.cff`，仅 README 内嵌 BibTeX], [存在],
  [分发与依赖], [无 PyPI 包（`pip install eve` 装到无关项目），走 `uv sync`；默认 testbed 不需 GPU，仅 ICON 示例需 2×GPU], [源码安装],
  [commit 契约], [`github_url` 与 `commit` 必须成对，缺失即 `ValueError`（`problem/repo.py:56-57`）；`repo.py:167-179` 解析后 `git archive` 造快照，该快照即 boundary 基线。*属代码级契约，论文正文无此约定*], [成立],
  [编辑边界检查], [`editable.files`／`folders` 为一等配置且不可同时为空（`repo.py:110-111`）；检查器在 `workflow/boundary.py:104-131, 152-200, 212-223`，越界以退出码 1 拒绝并取 `boundary_failure_score`], [成立],
  [外部分数驱动选择], [`subprocess.Popen(["bash", step], cwd=...)` 执行、分数从 `$EVE_EVAL_LOG_ROOT/score.yaml` 读回（`evaluation.py:306-314, 918-935`）；`phase2.py:544, 597-606` 按 `entry.score` 采样。*但采样是 rank-softmax 且 RNG 未播种*], [成立，非确定性],
  [共同进化], [`workflow/loop.py:26-27` 自述 "Explicit co-evolution loop"；solver 与 guidance 两种群互相采样（`phase2.py:553-584`），guidance 侧由 Elo 更新（`phase3.py:47-56, 71-80`）], [成立],
  [阶段对照], [README 与论文有 Static-Initial／Static-Final 对照；仓库无对应开关，只能用 `produce_optimizer_in_phase2=0` 近似], [部分成立],
  [预算与停止], [`loop.max_iterations`（默认 25）可用；`core/engine.py:224-241` 的 `StopConditions`（wallclock／token／cost）*全仓库无实例化*，run 级预算从不累加], [部分成立],
  [最小 smoke], [`circle_packing.smoke`；纯 CPU、sqlite、无 docker／Postgres／Redis，但需 Codex CLI 与登录态], [成立],
)

*对计划的意义*：EvE 把 $A_t$（solver／repository 状态）与 $H_t$（agent guidance）放在同一个共同进化环里，与计划:235-239 的固定偏序形成直接对照；它的 `(github_url, commit)` 契约正好是计划 §5.2 `ExternalInspiration` 里 `source.commit` 字段所要求的语义——*计划的一个关键字段，在货架上已经有实现*。其代价是归因更难（见 §4.4 的 $C_"attribution"$）。

== 3.3.3 Loreley（Apache-2.0，审计快照 `4c375920`，tag v0.10.0-alpha）

仓库 `github.com/NeapolitanIcecream/loreley`（arXiv:2608.19703）。原生以"给定仓库根提交 + 项目自带 evaluator + job 预算"为中心：`MAPELITES_EXPERIMENT_ROOT_COMMIT` 指定根提交，`WORKER_EVALUATOR_PLUGIN` 提供评测插件，`SCHEDULER_MAX_TOTAL_JOBS` 限制 job 数。其 archive 是 *Quality-Diversity*：行为网格 + 每格一个有界 Pareto front，入档裁决只在*同一 cell 内*做非支配过滤（`pareto_archive.py:417-444`），超限按拥挤距离截断（不按分数），采样与分数无关（先均匀选 cell、再均匀选 front 成员）。

*代价与限度*：需要 Postgres、Redis、docker 与 worktree，且要自行编写 evaluator plugin；论文自认在 48 jobs 时其 QD 并未胜过 Sequential Champion——这不是它的弱点，而是一个有用的先例：*复杂进化机制不自动等于端点改进*。

== 3.4 统计复核

功效采用非中心 $t$ 分布（$"df" = n-1$，$"ncp" = d sqrt(n)$，*严格*双侧 $alpha=0.05$），另以 $10^5$ 次蒙特卡洛验证，各轮外部复审的独立复算亦一致。$n=5$ 时最小可检测效应 $1.68 sigma_d$；达到 power 0.8 所需样本量：$d=1$ 需 $n=10$，$d=0.5$ 需 $n=34$。

== 3.5 文档族物证与排版实测

```text
ls -la *.typ
grep -n "seeds:" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
grep -nE "supersede|取代|废弃|作废|以本文为准" algorithm_research_infrastructure_plan.typ open_world_algorithm_research_engineering_plan.typ
```

- `adapdc_scaffold_implementation(1).typ`（09-09 20:37）声明*部分条款*取代并要求旧版顶部标注"部分条款已取代"；该标注属待执行动作，旧版（09-09 20:13）未加标注，其 `:32` 仍主张"不能同时保留相反的现行决策"、`:408` 仍写"不能让两份'现行真相'并存"；Makefile 通配符把两者都编成 PDF。
- `algorithm_research_infrastructure_plan.typ` 与被审计划的 Task Contract yaml *19 行中 18 行逐字相同*（含 seed 列表 `[11, 23, 47, 89, 131]`），Experiment Record 同源而异（被审计划新增 `external_inspiration_ids`、`code_diff`、`logs`、`compute_cost`、`validity`、`statistical_decision`，命名亦不同）；两份 mtime 同为 09-18 14:32（被审计划 15:25）；互不引用，均无取代声明。
- 至少三套并存的统计提交门（ADA 的 95% 区间 + 序贯校正、OPL 的配对下界、本计划的 confidence 0.95）。
- 该族另有引用不存在文件的情况（如 `adapdc_architecture_report.typ`、`research-foundations.md`）。
- *可移植性限度*：以上第 1、2、4 条依赖本地目录状态；他处证据集不含这些文件时，其正确标注是"该证据集内不可独立复现"。

*排版实测*：`typst 0.15.1` 编译退出码 0、无 warning，输出 20 页 A4。A4 页宽 595.276pt，页边距 68.031pt，正文右边界 527.245pt。方法：`pdftotext -bbox` 逐词取框 + 解压 PDF content stream 读取每个 text run 的笔位，两法交叉一致。

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

= 四、实验协议（操作性核心）

== 4.0 执行前提与本机现状（2026-09-20 实测）

*可用的工具链*：codex-cli 0.154.0、claude 2.1.260、docker 29.8.0（守护进程在跑）、uv、node v26.8.2、python 3.14.7、typst 0.15.1。

*已核实的本地源码副本*：

+ KAPSO — `/home/ebt/kapso_ck/kapso`，HEAD `7d99b152`，与审计快照逐字相同。
+ EvE — `/tmp/eve`，HEAD `979065fd`，与审计快照相同；*项目目录内另有一份冗余副本 `./eve/`（同一提交），属早期核查留下的拷贝，可清理。*
+ Loreley — `/tmp/lor/loreley` 存在，但*不是 git checkout*（`_version.py` 只读已安装发行版的元数据），无法确认其版本 → 执行 A0 前须按 `4c375920` 重新 clone 并固定。

*尚未存在、必须由我们创作的工件*：canonical `EvalContract`（A−1 的产物，见 §4.2）；三个 runtime 的 evaluator 适配层；trace 规格（score trace／selection trace／resource trace）。

*环境前提与风险*：

+ python 3.14.7 比两个项目的声明更新（KAPSO 要求 ≥3.10、EvE 要求 ≥3.11），可能缺少依赖的预编译 wheel；建议用 uv 固定解释器（3.11 或 3.12）而不是系统 python。
+ Loreley 需要自备 Postgres 与 Redis；本机已有一个无关的 `postgres:16` 容器在跑，Redis 未运行（可用 docker 起）。
+ KAPSO 需要 codex 与 claude 两个 CLI 且已登录；EvE 需要 Codex CLI 并登录。*登录态无法由审查侧验证，须由执行者确认。*

== 4.1 实验链与停止规则

```text
A-1   Freeze Canonical EvalContract   冻结评测器身份（源码/依赖/数据/配置/指标定义各一个哈希）
A0.1  Evaluator Integration Conformance  三个 adapter 是否忠实执行同一个 E*
A0.2  Score -> Search Contract           各 runtime 是否按自己声称的 selection semantics 消费评价
A1    SimpleLoop vs QualifiedRuntimes    选出后续实验的 substrate R*
B0+   R* vs R* + PositiveControlArtifact 外部工件能被这个 substrate 利用吗（通道存在性）
B0    R* vs R* + VerifiedPriorArt        普通的外部既有实现是否提升搜索（H_A）
B1    ClosedAcquisition vs OpenWorldAcquisition  主动获取值得吗（H_O）
H1    pi(SearchExternal, Acquire, Adapt, Cross, EvolveInternal | s_t, B_t)
```

- *A0 是候选筛选，不是集体门*：`R_1 = { r ∈ {SimpleLoop, KAPSO, EvE, Loreley} : A0.1_r ∧ A0.2_r }`，只需 $|R_1| >= 1$ 即可继续。某一套 adapter 的 bug 不应阻止其余实验。
- *A1 只选 substrate，不判项目生死*：输出是 $R^*$（规则见 §4.4）。若 `SimpleLoop` 胜出，正确的推论只是"复杂 runtime 暂无必要"，不能推出"外部工件没有价值"——此时令 $R^* = "SimpleLoop"$ 并继续 B0+／B0。只有当*没有任何 substrate 能可靠执行算法改进*时，后续步骤才失去意义。
- *B0+ 先于 B0*：B0+ 用一个人为选定、我们*已有证据*知道能改善该任务的工件（positive control），检验"外部工件 → 被 substrate 利用 → 改进"这条通道是否存在。只有 B0+ 失败，才说明注入／迁移通道本身有问题。
- *B0 阴性不否定 B1*：一个高质量工件不等于它对该任务可迁移；`Delta_A ≈ 0` 只说明*这个*工件没有迁移价值，不能推出 $max_(a in Omega_"external") "TransferValue"(a) <= 0$——而开放世界检索要解决的恰恰是"找到那个真正匹配的 $a^*$"。因此 B0 阴性只降低 B1 的先验，不构成取消 B1 的理由。

== 4.2 A−1 与 A0.1：冻结评测契约，再验证适配忠实度

== 4.2.1 A−1：冻结 canonical EvalContract

*问题*：runtime 原生的 evaluator 身份不可通约——KAPSO 是 manifest 指纹，Loreley 是 `evaluator_name + version + campaign_program_hash`，EvE 没有同构概念。因此"要求 `theta_E` 在三套 wrapper 间一致"在 EvE 上无定义；把 runtime 自己的 provenance schema 当成研究真相，也正是 D1／D16 已经暴露过的错误。

*做法*：把真相冻结在 runtime *之外*：

```text
EID* = H( EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition )
```

各 runtime 只做映射 `EID* -> EID_r`：adapter 负责声明并记录它如何把自己的原生身份表示绑定到 `EID*`（EvE 无原生身份时就记录"由 adapter 固定注入"）。

*A−1 的验收*：上述五项各有一个可复算的哈希，且 `EID*` 写进实验配置；任何一项变更都必须产生新的 `EID*` 并记入 trace。

== 4.2.2 A0.1：Evaluator Integration Conformance

固定候选集 $C^* = {c_1, ..., c_k}$，检验的*不是* `EID_K = EID_E = EID_L`，而是：

```text
对每个 runtime r 与每个候选 c:  E_r(c; theta_E) = E*(c; theta_E) ± epsilon
且 EID_r 由 EID* 派生（adapter 声明 + 可复算的哈希）
theta_E = (seed, fidelity, fraction, ...)  在三套 wrapper 间一致; 缺失参数取等价的固定值

判定是三元组 (passed, measured, total), 不是布尔:
  lane 表达不了的候选（例如某 runtime 无法表示 invalid／error）记为合成失败并计入 total;
  报告里必须写 measured 而不是 total; measured 不足不得算通过。
```

*区分最终评价与 runtime 内部反馈*（A0.1 与 A0.2 的分界）：

```text
E*  : Candidate -> Outcome                所有系统共享的冻结最终评价器（A-1 冻结其身份）
F_r : Outcome -> SearchSignal_r           runtime 特有的搜索信号（各系统可以不同）
```

A0.1 只保证 `E*` 被忠实执行。`F_r` 可以不同（KAPSO 取标量、EvE 消费 PyTree、Loreley 是多目标），但必须在实验前*声明并冻结*。A1 的第一轮固定共同信息，即 `F_r(E*) = scalar(E*)`，以便比较*纯 search machinery*；允许 native adapter 的对照留待后续——两者不能混称"runtime comparison"。

*逐系统事实*：KAPSO 经 CLI 传固定 seed（`--fidelity`／`--fraction`／`--seed`，默认 1337，来自 `evaluation_maintainer.subsample_seed`，`orchestrator.py:599`），且其注册契约*逐字要求* fast 档用该 seed 做确定性子采样（`evaluation_maintainer/prompts/setup_build.md:11-15`、`setup_provided.md:13-17`）——故 seed 是 evaluator 输入，不只是可比类标签；EvE 与 Loreley 的 evaluator 接口*不传任何 seed*（EvE 只注入 `EVE_WORKSPACE_ROOT`／`EVE_SOLVER_ROOT`／`EVE_EVAL_LOG_ROOT`／`PYTHONDONTWRITEBYTECODE`；Loreley 的 `EvaluationContext` 无 seed 字段，其 `mapelites_sampler_seed` 用于采样而非评测）。因此"随机源必须内建在 evaluator 自身"仍成立。

*KAPSO 的额外硬不变量（见 D16）*：

```text
每条 attempt 的三元组 (fidelity, fraction, seed)
  必须等于产出该分数的那个 run 的 manifest 三元组
  注: manifest 里没有 evaluator 字段 —— 评测器身份由树哈希 + re-sync 在带外保证
等价: 授予类必须等于告知 agent 的命令类
处置: mode != off 且出现错配 => 该轮计为 A0.1 failure
```

*三条硬约束与两个假绿陷阱*：

```text
1 evaluator 不得依赖 cwd 或 PATH
    EvE 会把 agent runtime bin 前置进 PATH; 三者的候选根各不相同
    (KAPSO 分支 worktree / EvE 的 EVE_SOLVER_ROOT / Loreley 的 context.worktree)
2 计数与日志不得写在会被还原的目录
    KAPSO 的 kapso_evaluation/ 会被 git checkout 还原
3 E* 的输出可以是多字段; 收敛为单标量是 F_r 的职责, 不是 E* 的约束
    (EvE 的 score.yaml 是标量, Loreley 的 metrics 是多目标 —— 由 adapter 各自收敛并声明)
假绿: EvE 的评测异常被静默映射为 failure_score(0.0), 与真实 0 分不可区分
假绿: Loreley 评测超时合成失败、metrics 超过 64 被截断、命中持久缓存会复用旧数
```

== 4.3 A0.2：Score → Search Contract

不能要求三套 runtime 都做全局 argmax——三者的 selection semantics 不同。检验必须连同*配置条件*一起冻结。

#table(
  columns: (1.7cm, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*系统*], [*官方 selection semantics 与必须冻结的配置*], [*A0.2 的可执行检验点*],
  [KAPSO], [全确定：父代、deliverable、轮次代表都是取最大。*条件*：`parent_policy = "best"`（默认值，`strategy.py:198, 212`）], [置 $E(c_1) > E(c_2)$ 跑一轮，断言下一轮的父代分支为 $c_1$，且取最优实验分支返回 $c_1$],
  [EvE], [分数入口为 rank 加权采样，RNG 未播种。*条件*：`working_optimizer` 用 `RankSoftmaxSampler`（`temperature: 1.0`，`replacement_mode: auto`）；`solver_examples` 用 `RankExponentialSumSampler`（`features.score` 权重 1.0、`temperature: 1.0`、`replacement_mode: no_replacement`，`n = 4`）；`solver_prefill` 是分数无关的 `UniformSampler`], [*频率*检验，且须按类分别推导期望：$P(c_1) = 1 / (1 + e^(-1)) ≈ 0.731$ *仅当* 用 `RankSoftmaxSampler`、$k=2$、$T=1$、抽一个；`solver_examples` 的类与取样数不同，期望须单独推导。不能用 prefill 段，不能只跑一次],
  [Loreley], [QD archive：只在*同一 cell 内*做非支配替换，超限按拥挤距离截断；采样与分数无关；无全局最优必胜。*条件*：两个候选的 descriptor／measures 相同（同 cell）], [断言 $c_1$ 的入档结果为替换且 cell 内 $c_2$ 被移除；再断言报表分支指向 $c_1$。跨 cell 时高分*不*淘汰],
)

*封闭性验证（B0 前置，机制在 A0 就要跑通）*：必须用探测证明所选 runtime 没有自主外部获取，而不是只在配置里关。*A0 实测的裁决*（`a0/closure/VERDICTS.md`）：*没有任何 runtime 是无条件 CLOSED*——SimpleLoop 出厂即 CLOSED（其 solver lane 本来就走 `codex exec --sandbox workspace-write`），其余三套均为 CONDITIONAL，且条件各不相同：

+ *EvE*：只有 `codex_tmux` 可封闭（`-s workspace-write -a never -c web_search="disabled"`）。*出厂的全量运行路径用 `codex_exec`，其 argv 硬编码 `--dangerously-bypass-approvals-and-sandbox`（`providers/agent/drivers/codex_exec.py:434`），喂它 `sandbox_mode=workspace-write` 会被静默忽略* —— 在错误的 driver 上做"配置级封闭"就是假绿。
+ *KAPSO*：codex lane 只需一个键——`agent_specific.sandbox=workspace-write`（默认 `danger-full-access`），实测端到端：shell 网络关闭而模型调用仍通。claude lane 没有 CLI 沙箱，只能外部断网或换 lane；"禁用 Bash"虽能关掉该 lane，但那等于删掉它存在的能力。
+ *Loreley*：默认 `kilo` 后端的 argv 里根本没有 sandbox／network／search 字段；要封闭必须把 worker backend 换成 `codex_cli`，或外部断网。
+ *证法*：判据不是读配置，而是*在 lane 内用 canary 实测* —— 真实模型回合 `rc=0` 且 lane 内 shell 的 `egress=BLOCKED`，同一提示在 unsandboxed 下 `egress=OPEN`（正对照）。CLI 层面的硬保证仍是 Codex CLI 的 `workspace-write` 默认 `network_access: false`。

== 4.4 A1：substrate 选择

```text
对照集: { SimpleLoop, 合格 runtime }
主指标: 单位资源的已验证增益, 以 anytime 曲线表达 Q(c) = max_{cost <= c} VerifiedScore
记录项: U = (Gain, Cost, Reliability, Attribution, Operability)
失败项: FailureStage 与 resolve_failed / comprehension_failed / mechanism_mismatch 计数
```

*$R^*$ 的选择规则（预注册，避免事后自由度）*：

```text
R* = argmax_R  E[ VerifiedGain_R(B) ]
     subject to   Reliability_R >= r_min
tie-break: Cost（同增益下取更低成本）
Attribution 与 Operability 第一轮只作描述指标, 不参与选择
```

理由：$U$ 是向量、没有自然全序，直接写 "$"argmax" U$" 会给事后解释留下空间。约束式比人为加权五个指标更干净。

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

*第一轮的预算口径（从简）*：

```text
B_hard              = ( T_wall, N_evaluatorCalls, concurrency cap )   能真正强制
secondary telemetry = ( N_modelCalls, T_in, T_out, C_usd )            尽量采集
```

*不为此先造统一 API 代理*。原则是 *measurement sophistication 正比于 decision sensitivity*：只有当结论确实取决于 token 记账时，才建设完整计量层（其可行性与四条工程限制见 S97）。三套系统自报的记账不可比是事实——KAPSO 的 `cost_budget` 是美元、不记 token 与模型调用，codex 后端下金额恒 0；EvE 记 token 与 turn，但 run 级预算从未累加（`StopConditions` 与 `write_run_checkpoint` 都是死代码）；Loreley 记的最全（含 token 分类与 `cost_source`），其 `evaluation_attempts` 表还能区分"真跑"与"缓存复用"——正因如此，第一轮只用能统一强制的量作为硬约束，其余作为参考。

*读法限定*：A1 是探针，不是假设检验。单任务、少数 run 只能分辨数量级差异；须预注册"不确定"这一结论（D11 的分析单位在 A1 中尚未满足）。

== 4.5 B0+、B0 与 B1

```text
B0+: 用 positive control 检验通道
     R* vs R* + PositiveControlArtifact   （该工件是我们已有证据认为能改善此任务的）
     若失败: 定位在 Injected / Used / Improved 哪一层失效, 说明注入或迁移通道有问题

B0:  用普通既有实现检验价值
     两臂都禁止自主外部获取
     R_closed   = Runtime(repo, E)
     R_artifact = Runtime(repo, E, VerifiedArtifact)
     Delta_A = Y(R_artifact) - Y(R_closed)
     轨迹分层: Search -> Found -> Resolved -> Verified -> Injected -> Used -> Improved

B1:  放开 Search -> Resolve -> Verify -> Adapt
     Delta_O ≈ Delta_discovery + Delta_resolution + Delta_transfer - C_acquisition
     （不能简单线性分解, 但四者必须各自可观测）
```

== 4.6 进 H1 的门槛与五项必改

*门槛*：A−1 的 `EID*` 已冻结并写入配置；A0.1／A0.2 通过（$|R_1| >= 1$）；A1 已给出 $R^*$；B0+ 已证明通道可用；run 级配对的 `(Open_{t,r}, Closed_{t,r})` 表与 event-keyed 随机源清单存在；预注册的单一主终点与 MDE；与 Open 条件 token 匹配的负对照；confirmation 使用不相交且未事后挑选的事件键集合；外部搜索／解析／验证／适配的开销全部计入 open 臂。

*若结果不显著*：必须同时报告*搜索失败率*、*解析失败率*与*机制抽取失败率*，以区分"没找到候选"、"找到了但解析不出可运行工件"、"没读懂仓库"、"机制不可迁移"。计划现有判据（计划:1076）无法区分，这是最需要修补的单点。

*五项必改*：

#enum(
  [*改写 §4.3 为真实通道*（D1）：`code` + `text_feedback`（需 `use_text_feedback = true`）+ `metadata` 三分；写明三条限定；`text_feedback` 定位为 MVP 捷径。],
  [*分离两套统计设计*（D3 + D11 + D12）：`statistics.gate` 与 `statistics.campaign` 两组字段；分析单位是 `(task, run)`；配对按 event-keyed 随机源实现，不可控源按 `(task, run)` 冻结；预算为 r 留乘数。],
  [*按 $C times X$ 析因重写 §8.2*（D2）：四臂 + shuffled 对照，主估计量 $Delta_X$；明文写出潜伏机制迁移不在可识别范围内；把 S82 的简单基线作为首要对照。],
  [*获取链写全*（D10 + D13 + D16）：`Search → Resolve → Verify → ExternalArtifact`；明确 $V_D$ 不等于 $V_E$；参考 EvE 的 `(github_url, commit)` 契约、KAPSO 的五项缺口与 manifest 不变量。],
  [*两类里程碑与文档收敛*（D4）：$M_"capability"$ 与 $M_"research"$ 分开，proxy guard 约束成本/能力比；新增"与既有计划的关系"一节与 `supersedes/retains` 字段。],
)

*其他建议*：把 `search_failed`／`resolve_failed`／`comprehension_failed`／`mechanism_mismatch` 单列为计数指标；给 evaluator 的来源黑名单与抄袭比对；加 License Provenance Gate 与派生代码隔离；按 §5.1 的三层判断重写新颖度表述并补参考文献；在计划:951-962 等长公式内插入强制断行；统一 `AHE / HarnessFix` 的写法、把 `ReplayWorld` 改为原文术语或注明为自拟名。

== 4.7 什么会使我改变判断

+ 若 A0 显示某套 runtime 无法通过评测一致性或 selection contract → 该候选退出 A1（不影响其余）。
+ 若 A1 显示 SimpleLoop 不劣于全部 runtime → 接受 S82 的零假设，令 `R* = SimpleLoop` 并继续 B0+。
+ 若 B0+ 失败 → 按 `Injected`／`Used`／`Improved` 三层定位失效点，而不是直接跳到"外部工件没有价值"。
+ 若 B0 阴性 → 只降低 B1 的先验；不得据此取消 B1（见 §4.1）。
+ 若作者指出一条七轮核验都遗漏的、把 `metadata` 文本送入 mutation/cross prompt 的代码路径 → 重新评估 D1。
+ 若作者给出 `(task, run)` 级配对表与 r 的取值依据 → D11 降级。
+ 若作者给出已被别的文档定义的 milestone 与 $Delta$ 度量 → D4 的"不可执行"部分撤回。
+ 若 KAPSO 把注册评测算为默认、或让告知命令随授予类派生 → D16 的第五项缺口可降为"工程配置"。
+ 若 §5.2 的最近邻清单中某条被证明与本计划的差异主张无关，或又出现新的最近邻工作 → 相应收窄或补充。

== 4.8 A0 执行记录（2026-09-20，由 rsi-dev 窗口执行）

*执行者与边界*：本节的数字来自 rsi-dev 窗口（产物在 `/home/ebt/rsi-dev/a0/`），按 §4.1–§4.3 的协议执行 A−1 + A0.1 + A0.2，四套 runtime（含 SimpleLoop —— §4.1 的链里有它，但本报告的交接文本早期漏列）。所有路径与命令可在该目录复现。

#table(
  columns: (2.2cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*runtime*], [*A0.1*], [*A0.2*],
  [SimpleLoop], [PASS 14/14], [PASS 9/9],
  [KAPSO], [PASS 14/14], [PASS 14/14（5 场景）],
  [EvE], [*PASS 5/14 measured* + 9 合成], [PASS（频率检验）],
  [Loreley], [PASS 14/14], [PASS 7/7],
)

无 FAIL、无 BLOCKED，*R_1 = 四套全过*（§4.1 只需 $|R_1| >= 1$）。三条必须随数字一起引用的限定：

+ *EvE 的 A0.1 不是 14/14*：只有 5 个候选是实测复现，其余 9 个是它的 lane 无法表达 invalid／error、由适配层声明为合成失败（`{score:0.0,"evaluation failed"}`）—— 正是 §4.2 点名的假绿陷阱。正确引法：`A0.1 = 5/14 measured`。
+ *A0.1 的判定是三元组 (passed, measured, total)*，不是布尔；measured 不足不得算通过。
+ *KAPSO 的 tie-break 与冻结规则不等价*：它是 node_history 上的 `max()`（含提案顺序），只在"字节序最小的那个恰好先提案"时才与冻结规则一致；现有 A0.2 断言没有区分两者（`runtimes/kapso/runs/tie-order-probe/` 显示反序即分歧）。不得把 A0.2 的 tie_break 场景读成"已建立冻结 tie-break"。

*冻结契约*：`EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`（`contract/out/plumbing.EID.json`，schema `a0.evalcontract/v1`，task `circle-packing-plumbing`；五项分项 = EvaluatorSource `a3d6534b` / DependencyLock `7b02f1a7` / DataManifest `b21c975a` / Config `550ca3cd` / MetricDefinition `420ab0ac`，已由审查侧独立复算一致）。冻结的 $E^*$ 是 `tasks/circle-packing/e_star.py`，*不是*上游 `local_eval.py`（两者差 1 ULP，且后者表达不了 invalid／error）。

*"外部分数真的改变了选择"的证据*（这正是 A0.2 的判据）：KAPSO 注入分后下一轮父代与 deliverable 都翻到高分者、且 runtime 分 == 独立 $E^*$ 分；EvE 只换分数载荷 → 位置 0 的频率由 0.754 变为 0.263（两比例 $z = 31.1$），marginal 情形 $hat(p) = 0.7290$（18000 抽）对理论 0.7310586（$z = -0.62$，即与理论一致）；Loreley `score_decides: true`（互换高分归属即互换存活者）；SimpleLoop champion 由 c01 变为 c02。

*FailureStage 与 trace*：四个 runtime 共用同一张冻结映射表，计数可合并且等于 `{none:5, verify_failed:5, resolve_failed:1, evaluator_failed:2, timeout:1}`（14 单元）；*校验单元是合并流* `<runtime>.<run_id>.all.jsonl`（按单文件校验有缺陷，会让每条 selection 事件报错）。KAPSO 的实际布局比其回报文本所写多一层 `a01`／`a02`：

```text
kapso      a0/runtimes/kapso/runs/a0-01/a01/traces/kapso.a0-01-a01.{score,selection,resource}.jsonl
           a0/runtimes/kapso/runs/a0-01/a02/traces/kapso.a0-01.{score,selection,resource}.jsonl
eve        a0/runtimes/eve/out/run001/traces/eve.eve-a0-run001.{score,selection,resource}.jsonl
loreley    a0/runtimes/loreley/out/run-a0/traces/loreley.lor-a0.{score,selection,resource}.jsonl
simpleloop a0/runtimes/simpleloop/out/main/traces/simpleloop.main.{score,selection,resource}.jsonl
```

*对本报告四条断言的更正*（§4.2 与 §4.3 已就地改写，另附录 A 新增 R59–R62）：

#enum(
  [*§4.3 的 EvE 封闭配方不完整*：出厂全量路径用 `codex_exec`（argv 硬编码 bypass 沙箱），只有 `codex_tmux` 可封闭；在错误的 driver 上做配置级封闭是假绿。],
  [*"KAPSO 没有 lane 级 sandbox 参数"不准确*：codex lane 有 `agent_specific.sandbox`（默认 danger-full-access；设 workspace-write 即实测封闭而模型调用仍通）；claude lane 才没有。],
  [*KAPSO 的 manifest 三元组没有 evaluator 字段*：它是 (fidelity, fraction, seed)；评测器身份由树哈希 + re-sync 在带外保证。],
  [*Loreley 默认单目标下"无全局最优保证"不成立*：每 cell 的前沿恒为 1，archive 就是 per-cell argmax；跨 cell 的负对照需要多目标配置才有区分力。],
)

*未做完的部分（如实记录）*：端到端（真 LLM）只做到 KAPSO 一轮与 SimpleLoop 两轮已验证；EvE 与 Loreley 的 agent lane 走到了真实模型对话，但没有"写回完成的一轮"。*A1 尚未开始。*

*环境两则*：codex 的 15722 端口是 CC Switch 的本地代理，此前未起；`cc-switch -a codex proxy enable && cc-switch daemon start --detach` 可恢复，而 `daemon stop` 会把配置改回坏的直连形态且没有 systemd 单元或开机自启 —— *这一步需要人工做*。Loreley 的 Postgres／Redis 容器仍在跑（5432／6379），用 `infra/net.sh down --networks` 收尾；5433 上那个无关容器全程未动。

= 五、与先前工作的关系

== 5.1 新颖度的三层判断

+ *架构层*（把外部知识或外部实现接进进化循环）：*已大量占位*。
+ *检索一次后进化*（MLE-STAR，S61）与*检索与进化交替*（DeepEvolve S63、MARCO S62）：均已占位。
+ *决策策略层*（把获取/适配/交叉/内部进化当作策略分配）：*部分占位*（§2.3.6）。
+ *尚存的价值主张*：在进化 archive 内部、带 commit／license／hash provenance 的单条外部灵感的反事实归因——已被 TuneNNGen（S58）与 Kernel Foundry（S57）逼近。
+ *必须正视的反面证据*：S82 用三域实验主张"简单基线在代码进化任务上已具竞争力"。它提高的是*零假设的优先级*，而非零假设的成立，应作为首要对照。

== 5.2 最近邻清单

#table(
  columns: (2.6cm, auto, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*工作*], [*占位*], [*依据*],
  [FunSearch 等三篇], [A（弱）], [冻结 evaluator + 程序库 + 检索高分实现进 prompt；初始程序由人给出（S18、S19、S20）],
  [TurboEvolve　2604.18607], [A], [`seed-pool injection`：既有解池聚类后分配到各 island 作种子；*池来源是作者自跑 checkpoint，非人类解、非网络获取*；无 provenance、无逐 seed 归因（S55）],
  [Loreley　2608.19703], [A + B（负）], [以完整 git commit 为 evolutionary artifact、isolated worktrees、项目自带 evaluator、QD archive，并显式区分 parent 边与 inspiration 边；逐字声明 inspiration 边 "does not show that the agent used its contents or that it caused the resulting edit"；自认未做 inspiration 消融（S56）],
  [EvE　2605.09018], [A + B（阶段对照）], [强制 `(github_url, commit)`；editable 边界检查；外部 shell evaluator 分数进入未播种的 rank-softmax 采样与 Elo；solver 与 guidance 共同进化（S76、S77）],
  [Kernel Foundry　2605.30359], [A + B], [从 KernelBook 检索 top-5 核作 few-shot 初始化 → 多岛进化；含专家初始化消融（S57）],
  [TuneNNGen　2607.05704], [A + B], [外部同族仓库代码作 prompt 指导；等预算 target-only vs source-guided；direct-copy 分解 + 负对照——*最接近"某条外部灵感是否导致改进"的已发表反事实*（S58）],
  [KAPSO　2601.21526], [A + C（论文口径）], [公开 API 有 research、learn_knowledge、evolve、learn 与 E2E 闭环示例；registered evaluation 可让外部分数驱动搜索（S65、S86）],
  [AutoSOTA　2604.05550], [A + C], [从论文 PDF 抽取 GitHub 链接并规范化为初始仓库（S60）],
  [MLE-STAR　2506.15692], [A + C + B（块级）], [用搜索引擎检索 web 上的模型构成初始解；含代码块级消融（S61）],
  [MARCO　2505.03906], [B + C], [实时检索近期会议论文的优化技术；有/无 web search 对比（S62）],
  [DeepEvolve　2510.06056], [B（通道级）+ C], [联网 PubMed/arXiv 检索进入迭代精化环；含 deep research 消融（S63）],
  [EES　2609.17590], [强基线，非先例], [validation gate + 持久记忆 + operator credit；其 `external-source routes` 指外部数据/答案查找，不是取外部实现；自认"不估计这些机制的边际收益"（S64）],
  [CORAL　2604.01658], [未核实], [摘要含 "evaluator separation"；仅核到元数据／摘要级（S80）],
  [EvoX Genesis　2608.10450], [A + C，B 未确认], [文档支持 "point it at your codebase and enter your objective"；未见外部 evaluator 配置项（S81）],
)

*完整性声明*：本清单*不宣称穷尽*。检索口径限于 arXiv 与公开 GitHub 仓库；未覆盖非 arXiv 正式论文集、闭源或仅 demo 的系统、以及论文无仓库的双向缺失项。

= 附录 A：逐轮修订记录（R1–R58）

本附录是本报告自身的审计轨迹：每一轮收到的复审意见、核验结论与处理。*正文的对应章节优先于本表的简写。*

#table(
  columns: (auto, 1fr, 1fr),
  inset: 4pt,
  stroke: 0.4pt,
  [*编号*], [*原说法或复审主张*], [*核验结论与处理*],
  [R1], [注入机制文本"必须自定义 `PromptSampler`"], [*不成立*。`Program.text_feedback` 已是现成的 per-inspiration 通道（`prompts_base.py:74-79`）；见 §2.2.1],
  [R2], [D2 定级"致命"（无法归因）], [*部分成立*。计划的 H1 字面是工程效用假设，对该假设封闭 vs 开放本身有效；降为"重要"，区分 $H_U$ 与 $H_M$；见 §2.3.3],
  [R3], [获取前端问题（原本未指出）], [*成立*。Man1Lab 无搜索路径；新增 D10；见 §2.2.2],
  [R4], [`sandbox_repo` 为"真实 backend"], [*过强*。自述 "command builder only"，只产出 dry-run 命令规格；已改写；见 §3.1],
  [R5], [与 ARI 计划的 Experiment Record"逐字相同"], [*错*。Task Contract 18/19 行相同，Experiment Record 同源而异；见 §3.5],
  [R6], [ARI 计划日期"09-17"], [*错*。文件 mtime 为 09-18 14:32；见 §3.5],
  [R7], [seed 数提到 $n>=20$], [*无依据且与自身表格冲突*。改为公式化程序；见 §2.3.2],
  [R8], ["proxy drift 已经发生"（事实层）], [*证据不足*。收窄为"治理缺陷已确认"；见 §2.3.5],
  [R9], ["许可传染"], [*过强*。漏掉 AGPL §2 的条件句；已按条件式重写；见 §2.4],
  [R10], [`license` 出现在"计划:527"等三处], [*错*。应为 533、626、1046],
  [R11], [partner 的 `text_feedback`"不与代码相邻"], [*错*。它不出现在 dedicated crossover block 中，但在 eval history 中与其自身 code 相邻；其 code 出现两次；见 §2.2.1],
  [R12], [`text_feedback` 作为长期 canonical schema], [*部分成立*。具评测反馈语义、单字段约束、重复评测产生第二行；改为 MVP 捷径],
  [R13], [D10 定级"第一跳没有实现路径"], [*过强*。已有同型流水线可借；降为"关键集成缺口"；见 §2.2.2],
  [R14], [六臂设计足以识别机制迁移], [*不足*。改为析因设计；见 §2.3.3],
  [R15], [功效表外推为"整个设计"的能力判断], [*错*（部分）。表只对候选提交门有效；加限定并新增 D11；见 §2.3.1],
  [R16], [每个 Phase 都补 $Delta$ score 里程碑], [*自相矛盾*。会重现自我触发问题；改为两类里程碑；见 §2.3.5],
  [R17], [§4"外部实现 × 反事实 × provenance 尚未被占位"], [*错*。已有多个最近邻；清单见 §5.2],
  [R18], [结论"修五项必改后进入窄切片"], [*不够*。改为 Probe-0 路线],
  [R19], [KAPSO 仅作为清单中的一条先前工作], [*应提升*。它是同时具备给定初始仓库、可接固定 evaluator、预算与续跑的系统；见 §3.3.1],
  [R20], [evolve 会自动检索 KG 并注入 prompt], [*不成立*。findings 注入是纯 `str()` 拼接；KG 检索是挂给 agent 的 MCP 工具，调用与否由 agent 决定；见 §3.3.1],
  [R21], [`iteration_evaluator` 可把外部分数驱动进化], [*不成立*。该 API 是观测性的；但 registered evaluation 路径成立（见 D16）],
  [R22], [KAPSO 保存 URL/commit provenance], [*部分成立*。论文声称 commit metadata 与 `RepoStore`，代码只有 URL 级 provenance；见 §3.3.1],
  [R23], [`research` 返回 candidate repositories 作 seeds], [*源码不支持*。researcher 只返回 idea／implementation／report；已降级为论文口径],
  [R24], [共享同一 seed 即配对], [*不成立*。新增 D12；见 §2.3.1],
  [R25], [D2 的 estimand 命名 $E times M$], [*概念不严谨*。$C$ 本身已编码机制；改名为 $C times X$；见 §2.3.3],
  [R26], ["运行时开放世界闭环已被占据"], [*过粗*。改为三层判断；见 §5.1],
  [R27], [货架普选漏了 EvE；Loreley"唯一 repository-native"不成立], [*成立*。新增 D13；EvE 与 KAPSO 并列一级候选；见 §3.3.2],
  [R28], [KAPSO 的 P2 缺口不止四项 provenance 字段], [*成立，且更严重*。缺口是五项；见 §3.3.1],
  [R29], [shootout 应拆成 Stage A 与 Stage B], [*接受*。§4 据此重写],
  [R30], [EvE 题名 "Evolutionary Ensemble of Agents"], [*对当前版本不成立*；该题名出自 v1（见 R51）],
  [R31], [EvE 可从包管理器安装／需 GPU], [*需更正*。无 PyPI 包（`pip install eve` 装到无关项目）；默认 testbed 不需 GPU；见 §3.3.2],
  [R32], [KAPSO 的"两条路径"（ImplementationText 与 Source.Repo）], [*部分成立*。与仓库解析脱节的是 idea／implementation／research report *三类*产物；不存在 `Source.Study`；见 §3.3.1],
  [R33], [Loreley 版本 0.7.6a0 与"需 Kilocode + embedding 端点"], [*过时／过宽*。版本见 R51；"需 Kilocode 与 embedding 端点"应限定为默认配置；见 §3.3.3],
  [R34], [§0.1 的"6 系统"计数（我自己写的）], [与实际所列不符；本轮二次查漏又增补候选；已放弃"已穷尽"断言；见 §5.2],
  [R35], [Stage A 其实不是 runtime shootout], [*成立*。拆为 A0 与 A1；见 §4.1],
  [R36], ["相同 budget"未定义，应用资源向量 + anytime 曲线], [*成立*，并核出记账能力不对称；见 §4.4],
  [R37], [Closed 臂可能因 agent 自带联网而不封闭], [*成立，且更严重*。三套里只有 EvE 的 `codex_tmux` 能靠配置封闭；见 §4.3],
  [R38], [$H_A$ 与 $H_O$ 应拆分；先测注入再测开放世界], [*接受*。见 §4.5],
  [R39], [KAPSO 已有"固定外部 evaluator → search score"机制，我的"需替换排序"说法有误], [*成立，我错了*。registered 路径确实把 manifest 分数写成 `node.score`；见 §2.2.4],
  [R40], [需 `max_change_requests=0` 并冻结 hash], [*成立*。默认上限 3，设 0 即关闭；接受变更后会对 frontier 做桥接复评；见 §2.2.4],
  [R41], [应加固定候选集的评测一致性测试], [*可行，但有三条硬约束*，并有两个假绿陷阱；见 §4.2],
  [R42], [runtime 效用不应是单一 score], [*接受*。$U$ 取五维（Gain／Cost／Reliability／Attribution／Operability）；见 §4.4],
  [R43], [KAPSO 的 fidelity 风险只是实验简化，不是规避必现 bug], [*机制描述对，结论错*。`mode` 不为 off 时授予类与告知命令结构性错配（用真源码执行复现）；"必须 off"成立；见 §2.2.4],
  [R44], [KAPSO 的 `--seed` 是 evaluator 输入，不只是可比类标签], [*成立，我错了*。注册契约逐字要求 fast 档用该 seed 做确定性子采样；见 §4.2],
  [R45], [A0 不能要求三者都偏向 $c_1$；应拆评测一致性与 selection contract], [*成立*。Loreley 只做同 cell 非支配替换、采样与分数无关；EvE 是未播种的 rank-softmax；见 §4.3],
  [R46], [A0 是 candidate filter，不是 collective gate], [*成立*。改为 $|R_1| >= 1$；见 §4.1],
  [R47], [A1 只决定 substrate $R^*$，不决定项目生死], [*接受*。即使 $R^*$ 是 SimpleLoop 也应继续 B0；见 §4.1],
  [R48], [SimpleLoop 需形式化，否则可被任意调强或调弱], [*接受*。已给出固定定义与禁止项；见 §4.4],
  [R49], [记账应由外部计量层，不依赖 runtime 自报], [*接受*，并核实了可行性与其四条工程限制；见 §4.4],
  [R50], [B0／B1 应记录 Search → Found → … → Improved 的轨迹分层], [*接受*。见 §4.5],
  [R51], [EvE 题名是"元数据不一致"；Loreley 引用 `LoreleyAI/loreley`], [*部分成立*：题名冲突是跨版本（v1 为 Evolutionary，v4 为 Evolving），非版本内不一致；*不成立*：`LoreleyAI/loreley` 与 `github.com/LoreleyAI` 均 404，正确地址是 `NeapolitanIcecream/loreley`。另：v0.9.0-alpha 过时，最新 tag 为 v0.10.0-alpha],
  [R52], ["KAPSO 的注册评测默认失效"（我自己的措辞）], [*不准确*。`FidelitySpec.mode` 默认为 `"off"`（`execution/fidelity.py:244`），此时授予 full／1.0 与告知命令一致，不会错配；错配只发生在 fidelity 被开启后的 probe 路径。已改为"`fidelity` enabled probe path ⇒ structural class mismatch"；见 §2.2.4],
  [R53], [要求 `theta_E` 在三套 wrapper 间一致（我自己的写法）], [*与事实冲突*。EvE 没有同构的 evaluator 身份概念，该要求无定义。改为冻结 runtime 之外的 `EID*`，各 adapter 声明 `EID* -> EID_r` 的映射（新增 A−1）；见 §4.2],
  [R54], [A0.1 与 A0.2 未区分"最终评价"与"runtime 内部反馈"（我自己的写法）], [*成立*。新增 $E^*$ 与 $F_r$ 的区分；A1 第一轮固定 `F_r(E*) = scalar(E*)` 以比较纯 search machinery；见 §4.2],
  [R55], [EvE 的 $P(c_1) ≈ 0.731$ 被当作一般常数（我自己的写法）], [*条件不足*。该值*仅当* `RankSoftmaxSampler`、$k=2$、$T=1$、抽一个；而 `solver_examples` 用的是 `RankExponentialSumSampler` 且 `n = 4`、`no_replacement`，期望须单独推导。已把配置条件写进 contract；见 §4.3],
  [R56], [$R^* = "argmax" U$（我自己的写法）], [*未定义*。向量无自然全序；改为预注册的约束式规则：`argmax E[VerifiedGain]` subject to `Reliability >= r_min`，Cost 作 tie-break；见 §4.4],
  [R57], ["B0 阴性 ⇒ B1 没理由做"（我自己的推断）], [*过强*。高质量不等于对该任务可迁移；B0 阴性只降低 B1 的先验。新增 B0+ positive control 在前；见 §4.1、§4.5],
  [R58], [为精确记账先建统一 API 代理], [*不必要*。第一轮改用能统一强制的 `B_hard = (T_wall, N_evaluatorCalls, concurrency cap)`，token 与费用作 secondary telemetry；原则是 measurement sophistication 正比于 decision sensitivity；见 §4.4],
  [R59], [§4.3 的 EvE 封闭配方（我自己的写法）], [*不完整*。出厂全量路径用 `codex_exec`，其 argv 硬编码 `--dangerously-bypass-approvals-and-sandbox`（`providers/agent/drivers/codex_exec.py:434`），喂它 `sandbox_mode=workspace-write` 会被静默忽略——在错误的 driver 上做配置级封闭是假绿；只有 `codex_tmux` 可封闭，已用 lane 内 egress canary 实测。见 §4.3、§4.8],
  [R60], ["KAPSO 没有 lane 级 sandbox 参数"（我自己的写法）], [*不准确*。codex lane 有 `agent_specific.sandbox`（默认 `danger-full-access`；设 `workspace-write` 即实测封闭而模型调用仍通）；只有 claude lane 没有 CLI 沙箱。见 §4.3],
  [R61], [KAPSO 的不变量写作"每条 attempt 的 (evaluator, fidelity, fraction, seed) 等于 manifest 三元组"（我自己的写法）], [*自相矛盾*。manifest 只有 (fidelity, fraction, seed) 三个字段，没有 evaluator；评测器身份由树哈希 + re-sync 在带外保证。§4.2 的不变量已改写],
  [R62], [Loreley"无全局最优必胜"（我自己的写法）], [*在该配置下不成立*。默认单目标时每个 cell 的前沿恒为 1，archive 就是 per-cell argmax；跨 cell 的负对照需要多目标配置才有区分力。见 §4.8],
)

= 附录 B：我对自身判断的更正

本附录汇总七轮中被推翻或收窄的*我自己的*判断（不含对计划的指控）。列为审计记录，便于读者判断本报告的可信区间。

#enum(
  [*公式越界范围*：曾称"6 处越界、`Y` 公式宽 600.5pt"。实测只有 1 处越出*页面*（计划:951-962，≈701.5pt，两侧各裁约 53pt），其余 5 处仅溢出页边距。],
  [*灵感槽位数*：论文与 `island_small`／`island_large` preset 为 4/2，`island_medium` 与类默认（`dbase.py:63-64`）为 1/1——引用必须写明出处配置。],
  [*SGM 的"唯一提供物"*：它另含 certificate → 状态转移协议与 checkpoint／held-out 审计。],
  [*D1 的补救措施*：曾称注入机制文本"必须自定义 `PromptSampler`"——错误，通道现成（R1）。],
  [*archive 不变量*：曾称"灵感必须 `correct=1` 且入 archive"——仅默认路径成立；`best_program_id` 路径只检查 `correct`，fix 的 ancestor 亦无此过滤。],
  [*AgentCo-Op 的能力*：曾称 `sandbox_repo` 为"真实 backend"——过强（R4）。],
  [*Experiment Record 的同一性*：曾称与 ARI"逐字相同"——错（R5）。],
  [*ARI 计划的日期*：曾称 09-17——错（R6）。],
  [*样本量建议*：曾建议 $n>=20$——无依据（R7）。],
  [*"proxy drift 已经发生"*：修正为"治理缺陷已确认"（R8）。],
  [*"许可传染"*：改为 AGPL §2 的条件式表述 + License Provenance Gate（R9）。],
  [*引用行号*：`license` 三处应为 533、626、1046。],
  [*cross 与反馈的相邻性*：曾称"不与代码相邻"——错（R11）。],
  [*`text_feedback` 的定位*：由"长期 canonical schema"改为"MVP 捷径"（R12）。],
  [*D10 的定级*：由"前提风险／第一跳没有实现路径"改为"关键集成缺口"（R13）。],
  [*D2 的实验设计*：由六臂改为析因设计；命名由 $E times M$ 改为 $C times X$（R14、R25）。],
  [*D3 的适用范围*：功效表只对候选提交门有效，曾外推为"整个设计"——错（R15）。],
  [*D4 的修补方案*：由"每个 Phase 都要 $Delta$ score"改为两类里程碑（R16）。],
  [*§4 的新颖度结论*：由"尚未被占位"改为分层判断（R17、R26）。],
  [*Probe-0 的实现选择*：曾隐含预选 ShinkaEvolve 为 runtime——已改为货架优先的实验链（R18）。],
  [*KAPSO 的第五项缺口*：曾称"缺机制、需替换排序／自定义父代选择"——错（R39）；该机制默认可用，只在 fidelity 开启后失效（R43、R52）。],
  [*"KAPSO 不记 token"的隐含读法*：准确说法是"记 USD、不记 token 与模型调用，且 codex 后端下 USD 恒为 0"。],
  [*Stage A 的性质*：曾称它回答"哪个 runtime 最适合算法改进"——它只能回答"哪个最容易接入"（R35）。],
  [*Closed 臂的默认封闭性*：曾未检查；三套里只有 EvE 的 `codex_tmux` 能靠配置封闭（R37、§2.3.4）。],
  [*Evaluator Conformance Test*：曾未提出；接受并补三条硬约束与两个假绿陷阱（R41），本轮再修正第三条为"收敛为单标量是 $F_r$ 的职责"（R54）。],
  [*KAPSO 的 `--seed`*：曾称"只是可比类标签"——错，它是 evaluator 输入（R44）。],
  [*A0 的判据*：曾写"三套 wrapper 都偏向 $c_1$"——不成立，已按系统分别给出检验点并补齐配置条件（R45、R55）。],
  [*A0 的门*：曾写"三套全过"——与另一处"逐个淘汰"自相矛盾，已改为 $|R_1| >= 1$（R46）。],
  [*A1 的定位*：曾写"至少要有一个 runtime 不劣于简单基线，否则停止"——已改为"选 substrate，即使它是 SimpleLoop 也继续 B0"（R47）。],
  [*fidelity 措辞*：由"judge 顶替机读分数"改为"错配时机读分数被丢弃、judge 分数上位并以授予类标签入账"（R43）；再由本轮收窄为只作用于 fidelity 开启后的 probe 路径（R52）。],
  [*Loreley 的版本*：v0.9.0-alpha 过时，最新 tag 为 v0.10.0-alpha（R51）。],
  [*EvE 题名的表述*：由"复审方的题名是错的"改为"题名冲突跨版本"（v1 为 Evolutionary，v4 为 Evolving）（R51）。],
  [*`theta_E` 一致性的要求*：曾要求三套 wrapper 的 evaluator 身份一致——在 EvE 上无定义，已改为 `EID* -> EID_r` 的映射（R53）。],
  [*$R^*$ 的选择*：曾写 $"argmax" U$——向量无自然全序，已改为预注册的约束式规则（R56）。],
  [*B0 → B1 的推论*：曾写"B0 阴性则 B1 没理由做"——过强，已补 B0+ 并把推论降为"降低先验"（R57）。],
  [*计量层*：曾把外置计量层作为 A1 的前置——已降为"按需建设"（R58）。],
)

*另有三项应记为"未核实"而非结论*：AgentCo-Op 在 PyPI 上 `agentcoop` 包的归属（两次独立核实结论冲突）；KAPSO 论文所述独立知识包是否真含 commit identifiers；§5.2 清单之外是否还有非 arXiv 口径的最近邻工作（CORAL、EvoX Genesis 仅核到元数据／摘要级）。

= 附录 C：来源清单

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
- [S20] OpenEvolve — https://github.com/algorithmicsuperintelligence/openevolve （Apache-2.0；原地址 `codelion/openevolve` 已跳转）
- [S21] The AI Scientist — arXiv:2408.06292
- [S22] AIDE — arXiv:2502.13138
- [S23] PaperBench — arXiv:2504.01848（最佳 agent 平均复现分 21.0%）
- [S24] MLE-bench — arXiv:2410.07095（o1-preview + AIDE 在 16.9% 的比赛达铜牌；禁止查看网上解法并用 Dolos 比对）
- [S25] RE-Bench — arXiv:2411.15114
- [S26] Open-endedness 议程 — PMLR 235:20597–20616 / arXiv:2406.04268（两版作者序不同，引用须标明版本）
- [S27] OMNI-EPIC — arXiv:2405.15568
- [S28] POET — arXiv:1901.01753
- [S29] Min et al., *Rethinking the Role of Demonstrations* — arXiv:2202.12837（EMNLP 2022）

*风险论据*

- [S30] pip secure installs — https://pip.pypa.io/en/stable/topics/secure-installs/ （默认"不执行任何防篡改检查，并涉及运行发行版中的任意代码"）
- [S31] AGPL-3.0 §0、§2、§5(c)、§13
- [S32] GitHub Copilot code referencing（2023）— 命中建议少于 1%，"在空白或近乎空白文件中命中要频繁得多"，比对窗口约 150 字符
- [S33] Pew Research, *Link Rot and Digital Decay on Government, News and Other Webpages*, 2024-05-17
- [S34] PyTorch, compromised nightly dependency（torchtriton）
- [S35] 货架系统对比（源码实测）：KAPSO、EvE、Loreley、OpenEvolve、ShinkaEvolve、ASI-Evolve 的许可证／安装／evaluator 接入／初始仓库／budget／provenance 对照。"已穷尽"断言已放弃
- [S36] 同目录 `algorithm_research_infrastructure_plan.typ`、`ada-engineering-plan.typ`、`opl-engineering-plan.typ`
- [S37] 同目录 `adapdc_relation_first_plan.typ`、`adapdc_scaffold_implementation.typ`、`adapdc_scaffold_implementation(1).typ`、`adapdc_theory_review.typ`
- [S38] ShinkaEvolve prompt 构造路径（快照 `9912af12`）— `prompts_base.py:58-79`；`sampler.py:147-157, 161-166, 205-208, 243, 256-263`；`prompts_cross.py:57-73`；`dbase.py:174, 849-890`
- [S39] Man1Lab 搜索能力（快照 `5376e58d` = main HEAD）— `src/providers/github/client.py:61`；`collection.py:1, 46, 56-58, 124-153`；`verification.py:1, 47`；`docs/reviews/1.2_github_collection_provider/audit.md:49, 55, 171, 182`；`docs/adr/ADR-0016-GitHub-Discovery-Provider.md:90, 119, 142, 161`
- [S40] AgentCo-Op（快照 `94c37504`）— `agentcoop/backends/repo_sandbox.py:1, 3, 28, 62-83, 86-130`；`core/runtime.py:118-122, 167`；`core/gates.py`；`compiler.py:206-224, 388, 405`；`integrator.py:75-90`
- [S41] AGPL-3.0 §0 与 §2 原文 — https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-or-later.txt
- [S42] Zöllner & Pritchard, AJHG 80(4):605-615, 2007 — doi:10.1086/512821（winner's curse / ascertainment bias）
- [S43] Leon, Davis & Kraemer, J Psychiatr Res 45(5):626-629, 2011 — PMID 21035130（pilot 只用于估 $sigma$）
- [S44] Gelman & Carlin, Perspect Psychol Sci 9(6):641-651, 2014 — doi:10.1177/1745691614551642（Type S／M 误差）
- [S45] DeMets & Lan, Stat Med 13(13-14):1341-1352, 1994 — doi:10.1002/sim.4780131308（alpha spending）
- [S46] Nosek et al., PNAS 115(11):2600-2606, 2018 — doi:10.1073/pnas.1708274114（预注册）
- [S47] R `stats::power.t.test`（非中心 $t$ 求根与 `strict` 约定）；Cohen 1988
- [S48] Hurlbert, Ecol Monogr 54(2):187-211, 1984 — doi:10.2307/1942661（pseudoreplication）
- [S49] Lazic, Clarke-Williams & Munafò, PLoS Biol 16(4):e2005282, 2018 — doi:10.1371/journal.pbio.2005282（"Increasing the number of OUs does not increase the sample size"）
- [S50] Makin & Orban de Xivry, eLife 8:e48175, 2019 — doi:10.7554/eLife.48175
- [S51] Gelman & Hill, *Data Analysis Using Regression and Multilevel/Hierarchical Models*, 2006
- [S52] Bouthillier et al., MLSys 2021 — arXiv:2103.03098（附录 C.2：A 与 B 复用同一 seed；增加变异源约 51 倍计算节省）
- [S53] Hemming et al., BMC Med Res Methodol 11:102, 2011 — doi:10.1186/1471-2288-11-102（设计效应）
- [S54] Saravanan, Berman & Sober, hierarchical bootstrap — bioRxiv doi:10.1101/819334

*最近邻工作*

- [S55] TurboEvolve — arXiv:2604.18607（`seed-pool injection`；池来源为 run checkpoints；provenance 与 license 被列为未来建议）
- [S56] Loreley — arXiv:2608.19703（Apache-2.0；`github.com/NeapolitanIcecream/loreley`，审计快照 `4c375920`，tag v0.10.0-alpha）
- [S57] Kernel Foundry — arXiv:2605.30359（KernelBook 检索 top-5 核作 few-shot 初始化 + 专家初始化消融）
- [S58] TuneNNGen — arXiv:2607.05704（外部同族仓库代码指导 + 等预算对照 + direct-copy 分解 + 负对照）
- [S59] KAPSO 论文 — arXiv:2601.21526
- [S60] AutoSOTA — arXiv:2604.05550（从论文 PDF 抽 GitHub 链接 → 初始仓库）
- [S61] MLE-STAR — arXiv:2506.15692（搜索引擎检索 web 模型构成初始解 + 块级消融）
- [S62] MARCO — arXiv:2505.03906（实时检索会议论文技术 + 有/无 web search 对比）
- [S63] DeepEvolve — arXiv:2510.06056（联网 PubMed/arXiv 检索进入精化环 + deep research 消融）
- [S64] EES — arXiv:2609.17590（validation gate + 持久记忆 + operator credit；`external-source routes` 指外部数据／答案查找）
- [S65] KAPSO 仓库 — https://github.com/Leeroo-AI/kapso （MIT；PyPI `leeroo-kapso` 0.4.7；快照 `7d99b152`）
- [S66] KAPSO 源码路径 — `src/kapso/kapso.py:434-465, 467-476, 1129-1154, 1292-1307, 1745-1781, 1791-1825`；`researcher/researcher.py:75-139`；`knowledge_base/types.py:47-59, 96-116, 141-183`；`repo_ingestor/utils.py:18-76`
- [S67] KAPSO 外部评测文档 — `docs/evolve/external-evaluation.mdx:13-16, 80-95`（仅对 `iteration_evaluator` 成立）
- [S68] Botev & Ridder, *Variance reduction*, Wiley StatsRef 2017 — doi:10.1002/9781118445112.stat07975（CRN 的"同一用途"表述）
- [S69] L'Ecuyer et al., Operations Research 50(6):1073, 2002（独立随机流）
- [S70] Salmon et al., *Parallel random numbers: as easy as 1, 2, 3*, SC'11（counter-based RNG）
- [S71] Buffalo, Pearson & Klein, arXiv:2603.11084（stat.ME；event-keyed hashing）
- [S72] OpenAI OpenAPI 对 `seed` 的说明（"Determinism is not guaranteed…`system_fingerprint`"）
- [S73] Loreley 运行约束 — `preflight.py:751-755` 强制 `WORKER_EVALUATOR_PLUGIN`；`env.example:321` 的根提交
- [S74] "何时检索"轴 — Self-RAG arXiv:2310.11511；Search-R1 arXiv:2503.09516；SEM arXiv:2505.07903
- [S75] "何时选算子"轴 — AEL arXiv:2604.21725；SciToolAgent-Evo arXiv:2607.28692；GAE arXiv:2607.10127；TOPOFE arXiv:2607.23286
- [S76] EvE — https://github.com/scaling-group/eve ；arXiv:2605.09018（当前 v4 题名 *Evolving Ensemble of Agents*；v1 题名 *Evolutionary Ensemble of Agents*）；Apache-2.0（含 NOTICE），快照 `979065fd`
- [S77] EvE 源码路径 — `src/scaling_evolve/algorithms/eve/problem/repo.py:46-58, 110-111, 167-179`；`workflow/boundary.py:104-131, 152-200, 212-223`；`workflow/evaluation.py:295-314, 630-631, 634-670, 918-935`；`workflow/loop.py:26-27`；`workflow/phase2.py:544, 553-584, 597-606`；`workflow/phase3.py:47-80`；`core/engine.py:224-241`
- [S78] KAPSO 的 research → repository 缺口路径 — `knowledge_base/types.py:141-183`；`research_ingestor/implementation_ingestor.py:17-18`；`research_ingestor/prompts/planning.md:39-42`；`knowledge_base/learners/knowledge_learner_pipeline.py:399`；`knowledge_base/search/workflow_search.py:147, 157, 204-225`
- [S79] KAPSO 注册评测的接入 — `execution/orchestrator.py:576-616`；`evaluation_maintainer/maintainer.py:42-86`；`search_strategies/generic/strategy.py:1117-1135`；`config.yaml:123-183`
- [S80] CORAL — arXiv:2604.01658（https://github.com/Human-Agent-Society/CORAL ；Apache-2.0）
- [S81] EvoX Genesis — arXiv:2608.10450（https://github.com/EMI-Group/genesis ；AGPL-3.0）
- [S82] *Simple Baselines are Competitive with Code Evolution* — arXiv:2602.16805（反面证据，应作为 §4.4 的首要对照与零假设）
- [S83] 其余候选 — EvoGit arXiv:2506.02049（已被 Genesis 取代）；MappingEvolve arXiv:2604.26591；Live-SWE-agent arXiv:2511.13646；ParEVO arXiv:2603.02510
- [S84] 阶段接入点对照 — EvE：`evaluation.steps` 指 shell 脚本并写 `$EVE_EVAL_LOG_ROOT/score.yaml`；Loreley：`WORKER_EVALUATOR_PLUGIN` 与 `MAPELITES_EXPERIMENT_ROOT_COMMIT`；KAPSO：`initial_repo` 与 `eval_dir`
- [S85] 闭源 CLI 依赖 — KAPSO 需 codex 与 claude；EvE 需 Codex CLI 并登录；Loreley 默认 Kilocode（示例路径 codex_cli）
- [S86] KAPSO registered evaluation → 选择的完整路径 — `search_strategies/generic/feedback_flow.py:66-95, 106-109`；`registered_evaluation.py:52-121, 124-159`；`strategy.py:1373-1396, 1420-1434, 1436-1477`；`extension`；`expansion_lanes.py:111-127`；`orchestrator.py:755-806`
- [S87] KAPSO 成本与预算口径 — `budget.py:151-153`；`orchestrator.py:562-574, 619-630, 906-921, 1229, 1505-1516`；`run_checkpoint.py:62-70, 291`；`codex_agent.py:10-12`（无计费遥测，累计成本恒 0）；`claude_code_agent.py:581-586`
- [S88] EvE 成本与预算口径 — `core/engine.py:34-47, 224, 326, 350, 356`（`StopConditions` 与 `write_run_checkpoint` 从未实例化或调用）；`storage/sqlite.py:73, 781-797`；`workflow/optimize_logs.py:24-43`；`workflow/loop.py:62, 65, 94, 115`
- [S89] Loreley 用量与 job 语义 — `db/models.py:700-703, 772-773, 921-922, 1095-1102, 1201-1243`；`static/job_scheduler.py:433-436`；`scheduler/main.py:508-513`；`core/worker/evolution.py:667-750, 1651-1660, 1727-1732`；`core/worker/evaluation_runtime.py:125-164`；`api/schemas/usage.py:17-38`
- [S90] 三套系统的联网与沙箱开关 — KAPSO：`codex_agent.py:84-87, 117-121, 187-188`、`strategy.py:198, 212, 235-241, 328, 358, 371`、`claude_code_agent.py:1182, 1213-1214`、`config.yaml:221`；EvE：`codex_exec.py:93, 112, 434, 448`、`codex_tmux.py:201, 229, 569-570`、`runtime/driver.py:380-386`；Loreley：`config.py:483-545, 1092`、`kilocode_cli.py:963-1010, 1171-1202`、`codex_cli.py:277`
- [S91] KAPSO 评测调用契约与可比类 — `evaluation_maintainer/maintainer.py:56-62, 431-435, 475-479`；`evaluation_maintainer/prompts/setup_build.md:11-15`；`evaluation_maintainer/prompts/setup_provided.md:13-17`；`execution/fidelity.py:44-50`；`orchestrator.py:599`（`subsample_seed` 默认 1337）
- [S92] 一致性测试的假绿风险 — EvE：`workflow/evaluation.py:161-167`（异常静默映射为 `failure_score`）；Loreley：`config.py:29, 561`（超时默认 900s）、`core/worker/evaluator.py:2304-2310`（metrics 超过 64 被截断）
- [S93] CLI 层面的网络与沙箱依据 — Codex CLI 的 `SandboxPolicy`（`workspace-write` 默认 `network_access: false`）与 `--search`；claude CLI 的 `--disallowedTools`、`--strict-mcp-config`、`--restricted` 与 OS 级 Bash 沙箱
- [S94] KAPSO 的 fidelity 错配路径（执行级复现）— `execution/search_strategies/generic/feedback_flow.py:66-95`；`registered_evaluation.py:87-91, 124-159`；`orchestrator.py:629-643`；`execution/fidelity.py:241-247, 318-324, 660-666`；`search_strategies/base.py:735`。实测：以生产命令（`--fidelity full --fraction 1.0`）与 fast／0.15 授予类调用，`manifest_of_record` 输出 "Manifest class mismatch … no mechanical score of record" 并返回 None，`node.score` 保持 judge 值
- [S95] Loreley 的 QD 语义与采样 — `pareto_archive.py:1, 265-277, 337, 417-444`；`sampler.py:531-559, 732, 759`；`scheduler/main.py:820-931`；ADR 0051 与 0052
- [S96] EvE 的采样语义与默认配置 — `configs/eve/loop/default.yaml:5, 9-11, 19-37`（`working_optimizer` 为 `RankSoftmaxSampler` with `temperature: 1.0`；`solver_examples` 为 `RankExponentialSumSampler`，`weight 1.0`、`temperature: 1.0`、`no_replacement`、`n = 4`；`solver_prefill` 为 `UniformSampler`）；`populations/samplers/rank_softmax.py:72, 104, 181`；`populations/base.py:40`（RNG 未播种）；`phase2.py:566, 589, 600, 612, 629`；`evaluators/elo.py:55-100`
- [S97] 外部计量层的端点与限制 — Codex CLI 的 `openai_base_url` 与 `model_providers.<id>.base_url`（无环境变量端点覆盖；`wire_api` 仅支持 `responses`）；claude CLI 的 `ANTHROPIC_BASE_URL`／`ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN`；Loreley 的 `kilocode_cli.py:60-79, 546-563` 会清除 `OPENAI_API_KEY`／`OPENAI_BASE_URL`，并有自身 job token 预算（`:38-43, 1246-1257`）
- [S98] EvE 的分发与元数据 — tag 仅 v0.1.0 与 v0.2.0；无 `CITATION.cff`（仅 README 内嵌 BibTeX）；Apache-2.0 并附 NOTICE
- [S99] KAPSO 的 fidelity 默认与三档 — `src/kapso/execution/fidelity.py:241-247`（`FidelitySpec.mode: str = "off"`）、`:316-324`（`FULL_PASSTHROUGH`，reason 逐字 "fidelity off: every experiment runs full-size"）、`:490-492`（mode 分支）
- [S100] KAPSO 的 parent_policy 默认 — `search_strategies/generic/strategy.py:198`（docstring 逐字 "Parent branch selection: best or baseline (default: best)"）、`:212`（`.get("parent_policy", "best")`）、`:1375`（`baseline` 分支）
- [S101] 本机执行前提实测（2026-09-20）— codex-cli 0.154.0、claude 2.1.260、docker 29.8.0（守护进程运行）、uv、node v26.8.2、python 3.14.7、typst 0.15.1；KAPSO 本地副本 `/home/ebt/kapso_ck/kapso` HEAD `7d99b152`；EvE 本地副本 `/tmp/eve` HEAD `979065fd`（项目目录内另有同一提交的冗余副本）；Loreley 本地副本 `/tmp/lor/loreley` 非 git checkout，须按 `4c375920` 重新 clone

= 附录 D：审查方法与覆盖范围

== D.1 方法

本报告汇总七轮工作。Rev. 0 为全文精读 + 20 个并行独立审查轴；Rev. 1 至 Rev. 6 分别为对六轮外部复审意见的独立核验，每轮新增 4–6 个审查轴，共 51 轴；Consolidated 2 追加一轮执行前修订（本机现状与配置默认值实测）。

每轮共同的原则：*不采信任何一方的转述，包括不采信本报告自己的旧结论*。核验方式包括：抓取公开源码逐行比对（含用真代码执行关键路径）、在本地固定快照上复核配置默认值、独立复算统计数字（非中心 $t$ + $10^5$ 次蒙特卡洛）、以及用 `pdftotext -bbox` 与 PDF content stream 两种方法交叉测量排版落点。

== D.2 证据强度分级

- *已核实*：可由公开源码、论文原文或实测数字直接复现。
- *高度可能*：多个独立来源一致，但无单一权威出处。
- *未核实*：仅有文档自述或无法从公开渠道确认，报告中一律标注。

== D.3 覆盖的审查轴

*Rev. 0（20 轴）*：五个核心系统源码级核实；Gödel machine 谱系；harness 谱系；统计与实验设计；内部一致性与可行性；与 ADA／OPL／ARI 的一致性；与 adapdc 系列的一致性；遗漏风险；先前工作与新颖度；H1 的机制与零假设；失败模式与最强反驳；Typst 构建与排版实测；两轮专项反证；引用元数据三轮核实。

*Rev. 1（6 轴）*：`text_feedback` 通道与 inspiration 过滤不变量；Man1Lab 搜索能力（三快照口径）；AgentCo-Op 的 repo 执行能力；目录层文档治理事实；许可表述精度；样本量程序的统计陷阱。

*Rev. 2（6 轴）*：cross 模式 prompt 逐行核对；TurboEvolve／Loreley／EES 逐篇核实；穷尽式最近邻检索（约 40 组查询）；experimental unit 错位的方法学核实。

*Rev. 3（5 轴）*：KAPSO 的公开 API 面与闭环；KAPSO 的 provenance 与外层边界；common random numbers 与 event-keyed randomness；货架候选横向普选；决策策略层的占位情况。

*Rev. 4（4 轴）*：EvE 的完整断言核实；KAPSO 的 research → repository 缺口；货架候选二次查漏；Stage A 三方可接入性。

*Rev. 5（5 轴）*：KAPSO 的 registered evaluation 是否驱动搜索；三套系统的评测器冻结通路；三套系统能否跑在信息封闭条件下；三套系统的成本记账口径；评测一致性测试的可行性。

*Rev. 6（5 轴）*：KAPSO 的 fidelity／judge／manifest 顺序与错配触发条件；`--seed` 是否为 evaluator 输入；EvE 题名与 Loreley 仓库地址的引用卫生；三套系统的 selection semantics；外部计量层的可行性。

*执行前修订（本版）*：在本地固定快照上复核 `FidelitySpec.mode` 与 `parent_policy` 的默认值；实测本机工具链与三套源码副本的状态；据此修正 D16 的适用范围并补入 A−1 与 B0+。

== D.4 不覆盖的范围

- 不对任何实验*结论*作评价——这些实验尚未运行，不存在可评价的数据。
- 源码核实基于 2026-09-20 的公开快照，逐系统标注 HEAD；被审计划本身未固定版本。
- "货架候选已穷尽"这一断言已放弃（见 §5.2）。
- 未评价计划的研究价值主张是否"足够新颖到值得发表"。
- 未评价计划所依赖的外部系统的长期维护风险（除已注明的许可证与活跃度事实外）。
