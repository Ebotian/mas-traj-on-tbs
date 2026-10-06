import type { Conflict, Decision, Reversal, TimelineEvent } from '../types.ts'

/* ------------------------------------------------------------------ timeline */

/** Tracks: input = the user's own prior work, only ever read by the conversation.
 *  conversation = written by the decoded ChatGPT share (09-17 → 09-24 UTC).
 *  other-conversation = the D-line narrative pair, which is NOT in that payload.
 *  repo = a0/ implementation. this-session = 09-30 and 10-06 work. */
export const TIMELINE: TimelineEvent[] = [
  { date: '09-09', clock: '', label: 'adapdc_* ×4 · deep-research-report ×3', track: 'input', note: 'Relation-First / Unit Card / 范畴论 IR。10-06 复核:账户里有同期的 Document(Sep 9–10),不全是「从压缩包里读来的东西」' },
  { date: '09-14', clock: '', label: 'rule-construction-research ×2', track: 'input', note: '电价规则构建。原记「连被对话读取的记录都没有」;10-06 复核:它的结论句(「可组合规则＋多实例生成器＋结构覆盖与独立核对」)命中同日期的项目对话「对话总览与反思」' },
  { date: '09-16→18', clock: '', label: 'ada-/opl-engineering-plan · virtual_staining', track: 'input', note: '10-06 复核:两份 engineering plan 是「审查Kimi插件」(09-16)的产物 —— 对话自述「已完成两份独立工程计划,各 7 页…PDF 已编译」,不是纯输入' },
  { date: '09-17', clock: '08:46', label: '对话开始:Kimi Code 有没有插件市场', track: 'conversation' },
  { date: '09-17', clock: '09:35', label: '轮次 #7 正交组合方针', track: 'conversation', note: '「终究我们是要做实际的项目,而不是基础设施」' },
  { date: '09-17', clock: '09:48', label: '轮次 #11 用户命名代理谬误', track: 'conversation', note: 'A 线降级由用户先说出,比 plan.typ:53 把它书面化早约 20 小时' },
  { date: '09-17', clock: '09:54', label: 'algorithm_research_infrastructure_plan.typ', track: 'conversation', artifact: 'related_files/algorithm_research_infrastructure_plan.typ' },
  { date: '09-18', clock: '02:47', label: '轮次 #17 搜索已有实现', track: 'conversation', note: '开放世界这条线的起点' },
  { date: '09-18', clock: '02:54', label: '轮次 #18 open problems must in open world', track: 'conversation', note: '该口号是用户的,不是模型的' },
  { date: '09-18', clock: '06:17', label: 'open_world_algorithm_research_engineering_plan.typ + refs.bib', track: 'conversation', artifact: 'related_files/open_world_algorithm_research_engineering_plan.typ' },
  { date: '09-18→20', clock: '08:09→07:15', label: '七版独立审查', track: 'conversation', note: '(1)–(6) 永久缺失:载荷里只有截断的读取窗口,无写入操作' },
  { date: '09-20', clock: '07:15', label: 'open_world_plan_review.typ', track: 'conversation', artifact: 'related_files/open_world_plan_review.typ', note: '§4 成为 a0/ 的协议权威:外部、只读、不在本仓库内' },
  { date: '09-21', clock: '', label: 'A−1 / A0.1 / A0.2 + STATUS + CONVERGENCE + SPRINT', track: 'repo', artifact: 'a0/STATUS.md', note: '标签 a0-audited' },
  { date: '09-22', clock: '', label: 'A1-REQUIREMENTS · A1-CONTRACT-AUDIT', track: 'repo' },
  { date: '09-23', clock: '02:09', label: '轮次 #26 用户指出先验矛盾', track: 'conversation', note: 'H_T pivot 的真正起点' },
  { date: '09-23', clock: '06:07', label: '轮次 #27 「直接假设外部获取有价值,只是时机难判」', track: 'conversation', note: '这就是 H_T,早于 TIMING-REVIEW' },
  { date: '09-23', clock: '07:40', label: '轮次 #28 三重困难 + 三类解法', track: 'conversation', note: '检索 / 时机 / 历史处理;IAC 硬约束 / SOP 软约束 / 人类 taste' },
  { date: '09-23', clock: '08:10→09:34', label: 'C 线 v1 → v2 → v3 → v4(83 分钟四轮)', track: 'conversation', artifact: 'related_files/research_state_control_review_v4.tex', note: '第四轮否定了自己的线名' },
  { date: '09-23', clock: '18:01', label: 'v4.tex 的 mtime —— 对话结束后又排过版', track: 'repo', note: '多出的 337 B 全是排版;emergencystretch/allowbreak 在载荷 0 命中' },
  { date: '09-23', clock: '', label: 'A1-RESULT · EPISTEMIC-REVIEW · TIMING-REVIEW v1+v2', track: 'repo', artifact: 'a0/TIMING-REVIEW.md' },
  { date: '09-24', clock: '03:11', label: '轮次 #39–40 内燃机与飞机 · 用户本科是导弹导引控制', track: 'conversation', note: '全部航空工程框架的来源' },
  { date: '09-24', clock: '04:39', label: '轮次 #41 索取理论框架', track: 'conversation' },
  { date: '09-24', clock: '05:02→05:04', label: 'agent_engineering_science_report.tex + bib + 3 CSV + 3 图 → zip', track: 'conversation', artifact: 'related_files/agent_engineering_science_repro_bundle.zip', note: '七域 T₁–T₇、RQ1–RQ5、沙箱实验 A/B/C。zip 未被 git 跟踪' },
  { date: '09-24', clock: '15:30', label: 'Pasted markdown.md(另一条对话)', track: 'other-conversation', artifact: 'related_files/Pasted markdown.md', note: '把 T₁–T₇ 贬为「偏 taxonomy」,改为三层 + L1–L7 + Epistemic Bandwidth Allocation' },
  { date: '09-24', clock: '15:30', label: '独立学术审查(另一条对话)', track: 'other-conversation', artifact: 'related_files/agent_engineering_science_independent_review_2026-09-24.md', note: '七条 L 没有一条以当前形式成立' },
  { date: '09-30', clock: '', label: '语料整理:资料整理 → related_files,白名单 .gitignore', track: 'this-session', note: '消除 gitlink 陷阱;literature/ 存放不可重建的 PDF' },
  { date: '09-30', clock: '', label: '梳理解码载荷 → v1 → v2 → v3(Typst)', track: 'this-session', artifact: 'related_files/synthesis_2026-09-30.typ' },
  { date: '09-30', clock: '', label: '重放回收 C 线 v2/v3 + conversation/ 入库', track: 'this-session', note: '三次逐字节对拍通过' },
  { date: '10-06', clock: '', label: 'viz/ 脚手架:TS + Vite,七个视图', track: 'this-session', artifact: 'viz/' },
  { date: '10-06', clock: '', label: '账户 Library 核查:159 条 → 118 条本地没有', track: 'this-session', note: '站点搜索不索引 File:搜 open_world_plan 命中 0,而库页六版俱在 —— 这正是误判的根因' },
  { date: '10-06', clock: '', label: 'B 线六版取回:(1)–(5) 入库,v(6) 与磁盘逐字节相同', track: 'this-session', artifact: 'related_files/open_world_plan_independent_review(1).typ', note: '拼接 CodeMirror 预览;6/6 typst 编译通过。此前写在三处的「不可恢复」被推翻' },
  { date: '10-06', clock: '', label: 'D 线 / a0 侧 / AdaPDC 9 份取回(无损),另 3 份只有渲染文本(共 12)', track: 'this-session', artifact: 'related_files/TIMING-REVIEW(1).md', note: 'H_T 审查 v2、STATUS(1/2)、第二轮审计、进展稿、C0 两份、源码审查包、接口契约;范畴论三份走跨源沙盒 iframe,markdown 原文不可得。外部复核(10-06)指出原写「12 份取回」与恢复清单的 9+3 不符,已改' },
  { date: '10-06', clock: '', label: '稿 4:记忆基底即信息划分 —— 第一节是「去重表」', track: 'this-session', artifact: 'related_files/1006/memory_substrate_and_partition.typ', note: '体例变了一次:先判定哪些说法已在 v4/稿 1–3(给位置),只在四条新内容上展开:N1 机制→旋钮→特征损失、N2 触发器从容量改为矛盾密度、N3 相关性过滤的结构性盲区、N4 强制边界=工具持有者(单写者新风险);N5 = 三个裁决器 T1–T3' },
]

/* ----------------------------------------------------------------- reversals */

/** Reversal is this project's core method, so it gets its own view.
 *  `evidence` is carried per block: 'v' = I read the source table myself. */
export const REVERSALS: (Reversal & { evidence: 'v' | 's' })[] = [
  {
    round: 'TIMING-REVIEW v1 → v2', date: '2026-09-23', source: 'a0/TIMING-REVIEW.md §0.2 / §8.5', evidence: 'v',
    items: [
      { was: '「门 B(非冗余)就是 ρ 门」', now: '两者不同构。ρ 测 (R−J_X)/(R−J_0),是「工件是否把 assay 吃光」,完全不描述 agent 能否自己发现 X。改为三门前置', cite: '§3.2' },
      { was: '「Δ=0.1166 是 agent 照抄时的下界」', now: '它只是 J(reference implementation of X)。agent 可能低于它也可能在其上改进 ⇒ 既非下界也非上界', cite: '§3.2' },
      { was: '「E[V]>0 不带任务限定在本任务是假命题——它把可测空间吃光了」', now: '逻辑颠倒。吃掉 82.6% 差距说明 X 非常有价值;失败的只是它作为 timing assay 的 intervention。ArtifactValue ≠ AssaySuitability', cite: '§3.1' },
      { was: '主估计量写成 VerifiedGain − λ·Cost', now: '去掉 λ。同一硬预算下的 J_best(B;·) − J_0 就够', cite: '§3.3' },
      { was: '「τ 必须预留显式 post-reveal adaptation 配额」', now: '方向反了。那会消掉 timing 最有意思的那部分成本。改为固定总预算 + τ/B 网格', cite: '§3.4' },
      { was: '「给 s_t 的每个分量写明 authority」(仍含 D_t/F_t/S_t)', now: '更好的修法是把它们从第一代里去掉,留作 ablation chain', cite: '§3.5' },
      { was: '「加 placebo 臂 + 把预训练通道标 UNCONTROLLED」', now: '不够。K(τ⁻)≈K(τ⁺) 是 treatment manipulation failure,placebo 测不到它。改为先做 PriorKnowledgeProbe', cite: '§4.2' },
      { was: '「g(τ) 只是诊断」', now: '升为独立阶段 B0a', cite: '§5.1' },
    ],
  },
  {
    round: 'C 线 v1 → v4(一天内四轮)', date: '2026-09-23', source: 'research_state_control_review_v4.tex', evidence: 's',
    items: [
      { was: '一个 Event Log', now: '两个 ledger:「我不再建议只有一个 Event Log」', cite: 'v4:829' },
      { was: '两个 plane', now: '四个 plane', cite: 'v4:1175-1181, 1449-1455' },
      { was: 'plateau 触发器 r_I ≈ λ_t μ_t 是理论目标', now: '降级为 baseline:「B0b 的 λ̂μ̂ plateau policy 应被视为 baseline,而不是理论目标」,理由是非凸的最优信息购买', cite: 'v1:245 → v4:757, 761' },
      { was: '熵目标', now: '换成 decision-relevant loss L_DR', cite: 'v1:304-316 → v4:877-887' },
      { was: 'novelty 的宽表述', now: '两次收窄:「我们不能声称 novelty 是…」', cite: 'v1:266 → v4:781' },
      { was: '原优先级顺序', now: '「建议顺序改为」P0–P7', cite: 'v4:893' },
      { was: 'History is evidence; memory is a derived view', now: '升级为 Lossless Evidence → Versioned Derived State → Query-conditioned Views', cite: 'v1:166 → v4:710' },
      { was: '组件驱动设计', now: '明令禁止', cite: 'v4:1223' },
      { was: '线名 Research State Estimation and Control', now: '第四轮否定线名本身,改为 Long-horizon research as an epistemic organization under partial observability and bounded resources', cite: 'v4:1565-1571' },
    ],
  },
  {
    round: 'a0/ 自己承认的错误', date: '2026-09-21→23', source: 'a0/STATUS.md §8 · a0/A1-RESULT.md §9', evidence: 'v',
    items: [
      { was: '「codex 必须退役」(理由:只支持 Responses API,两家 provider 都不提供)', now: '错,而且升级前就错了。实测 POST /v1/responses → HTTP/2 200,codex 能端到端驱动含工具循环。真因是探针从没试过 /responses', cite: 'STATUS §5.3' },
      { was: '早期一次 EID* 冻结', now: '哈希错了对象(local_eval.py 而非 e_star.py);两者差 1 ULP', cite: 'STATUS §3.1' },
      { was: 'conformance 计算器', now: 'R1 高危:只比较 status、从不读 failure.kind,一个「status 诚实、failure_kind 全错」的 adapter 返回 PASS(exit 0)', cite: 'STATUS §4' },
      { was: '「LLM_USAGE_PRICING_JSON 能定价 kilo 事件」', now: '实测不能。pricing.py:69-74 在 source == "kilo_cli" 时提前返回', cite: 'STATUS §8' },
      { was: 'meter 的标签写「non-2xx」', now: '代码却判 status >= 400,于是 3xx 仍落到 2xx 用的标签。判据改为 >= 300,自检 69 → 70', cite: 'A1-RESULT §9.8' },
      { was: '计账代理剥掉 Content-Length 不补回', now: '上游收到无分帧 body ⇒ 真实 provider 每次调用都 400 且记为 unmetered,token 上限此前不可能有真实数字。它自己的 55 项自检看不见', cite: 'A1-RESULT §9.1' },
      { was: '「旧/新判定只差身份叶」', now: '被自己的验证者证伪:474 个叶不同,判定从 NOT_ADMISSIBLE 翻到 ADMISSIBLE', cite: 'A1-RESULT §3 末段' },
    ],
  },
  {
    round: '梳理 v1 → v2', date: '2026-09-30', source: 'related_files/synthesis_2026-09-30.typ §6.8', evidence: 'v',
    items: [
      { was: 'D 线 = Pasted markdown.md + 审查', now: '不完整。D 线是三跳,第一跳 report.tex 在被解码的对话里,且只存在于未跟踪的 zip', cite: '§1.3' },
      { was: 'A 线「自己废弃」,理由是 plan.typ:53', now: '归因错误。降级是用户在轮次 #11 先做出的,早约 20 小时', cite: '§1.2' },
      { was: 'A 线日期 09-09→09-18 是「线的活动期」', now: '误导。09-09 那批是用户自带的输入,对话只在 09-18 读取它们(且被截断到 20000 字符)', cite: '§1.3' },
      { was: '两条线「不可合并,是第二个实验」', now: '修订为「一行重叠、七行空白」:report.tex 矩阵第 2 行就是 a0/ 的 B0a', cite: '§6.5' },
      { was: '「图 PDF 仍可留在 zip 里」', now: '错。只提 5 个文本会得到编译不了的 .tex:bib 名字不对、三张图缺失', cite: '§7.5' },
    ],
  },
  {
    round: '梳理 v2 → v3', date: '2026-09-30', source: 'related_files/synthesis_2026-09-30.typ §11.1', evidence: 'v',
    items: [
      { was: '「32 个 /mnt/data 路径,全部由 assistant/tool 写入」', now: '错。只有 7 个留有写入操作,25 个只被读取。第一次分类还有假阳性:Path(x).read_text() 被当成写入', cite: '§1.3' },
      { was: 'C 线 v2/v3「可,从载荷提取」', now: '不是提取,是重放。v2 由 cp v1 生成再打补丁;载荷里没有整份内容', cite: '§1.4' },
      { was: 'B 线六个审查版本「可」', now: '不可恢复。六版都只有截断的读取窗口,无任何写入操作', cite: '§1.4' },
      { was: '(没有这一条)', now: '语料不是对话的纯快照:磁盘 v4.tex 多 337 B 排版修改', cite: '§7.6' },
      { was: '重放器用文本替换中和 LaTeX', now: '把 biber 改成 true 时连 heredoc 正文里的 backend=biber 一起改了 ⇒ v1 与磁盘差一行。改用 PATH 垫片后逐字节相同', cite: '§11.1' },
    ],
  },
  {
    round: '梳理 v3 → 账户库核查(10-06)', date: '2026-10-06', source: 'chatgpt.com/library 159 条 + 站点搜索 + 17 份取回件', evidence: 'v',
    items: [
      { was: 'B 线六个 open_world_plan_independent_review 版本「不可恢复:载荷里只有截断的读取窗口,无写入操作」', now: '六版都在账户 Library 里(File,09-18→09-20)。(1)–(5) 已取回入库,v(6) 与磁盘那份逐字节相同(仅差一个尾部空行)', cite: 'commit 900bcb0' },
      { was: '站点搜索可以当文件清单用 —— 搜 open_world_plan 得 0 命中,据此判定账户里也没有', now: '搜索只索引对话与文档语料,不索引 File:0 命中与「库里六版俱在」同时为真。凡断「文件是否存在」必须以 Library 页面为准', cite: '库页 vs /command search' },
      { was: '「项目」有 38 条对话', now: '12 条(面板行带日期;可访问名里写着 chat in project);其余 /c/ 链接是侧栏全局 Recents 与同一批对话的重复', cite: '项目页 + 库页两张快照' },
      { was: 'adapdc_*、deep-research-report*、ada-/opl-engineering-plan 都是「纯输入,只被读取」', now: 'adapdc_* 与 deep-research-report* 有同期账户 Document(Sep 9–10);ada-/opl-engineering-plan 是「审查Kimi插件」(09-16)的产物', cite: 'search: 审查包 / AdaPDC / rekursiv' },
      { was: '项目标签可以当相关性判据', now: '不能:产出 virtual_staining_open_source_sota_survey.typ 的那条对话不在项目里;项目内也有 BESS、气象站这类别的主题', cite: 'search: 虚拟染色 → 唯一命中非项目对话' },
    ],
  },
]

/* ------------------------------------------------------------------ conflicts */

export const CONFLICTS: Conflict[] = [
  {
    id: 'rho', title: 'ρ 同名异义', kind: 'name-collision', evidence: 'v',
    left: { who: 'D 线的 ρ', cite: 'Pasted markdown.md §2, §20 L1', quote: 'latent error correlation —— agent 间错误相关性,是关于世界的量。' },
    right: { who: 'a0/ 的 ρ_X', cite: 'positive_control/PC-REVISION.md:165-166', quote: 'ρ_X = (R − J_X)/(R − J_0),是 assay 的动态范围。「ρ 是 assay 的属性,MUST NOT 被当作关于世界的证据。」' },
    consequence: '审查最硬的数学结论针对前者,但措辞看起来像批评任何用 ρ 的推断。任何把两条线写进同一份文档的尝试都会踩这个坑。建议 a0/ 侧改名 ρ_assay 或 dyn_range。',
  },
  {
    id: 'rq', title: 'RQ1–RQ5 同名异义', kind: 'name-collision', evidence: 'v',
    left: { who: 'C 线', cite: 'research_state_control_review_v4.tex:1547-1561', quote: 'RQ1 Recoverability · RQ2 Decision-sufficient state · RQ3 Foresight and resource rationality · RQ4 Organizational learning。kill chain: RQ1→RQ2→RQ3,RQ4 并行且纵向。' },
    right: { who: 'D 线', cite: 'agent_engineering_science_report.tex:304-335', quote: 'RQ1 Decision-Sufficient State · RQ2 Adaptive Observability · RQ3 Epistemic Stability · RQ4 Resource Allocation · RQ5 Similarity Laws。未声明依赖。' },
    consequence: '相隔一天(09-23 09:33 / 09-24 05:03)。同一个概念 DSS 在两边分别是 RQ2 和 RQ1。建议加前缀 SC-RQ* / AES-RQ*。',
  },
  {
    id: 'disclaimer', title: '后继违反前驱的明文免责', kind: 'contradiction', evidence: 'v',
    left: { who: 'report.tex(前驱)', cite: 'agent_engineering_science_report.tex:415', quote: '「所有模拟均为机制示例,不应被引用为真实 LLM Agent 的性能证据。」' },
    right: { who: 'Pasted markdown.md(后继)', cite: 'Pasted markdown.md:1149', quote: 'L1 的支持证据:「已有 ensemble 理论 + 我们 sandbox experiment + debate diversity 结果支持。」' },
    consequence: '审查对 L1 的裁决(「不成立」)因此比它自己给的理由更强:即使 N_eff 的数学问题能修,L1 也还缺一个合法的证据来源。',
  },
  {
    id: 'exp3', title: 'exp3 的指标在所有条件下都完美', kind: 'false-green', evidence: 'v',
    left: { who: '数据', cite: 'exp3_temporal_retrieval.csv', quote: 'temporal_projection_accuracy 在六个噪声级(0.05→0.8)上恰为 1.0;flat_retrieval 从 0.4557 单调退化到 0.2188。每级 10000 queries。' },
    right: { who: 'a0/ 的对照做法', cite: 'a0/A1-RESULT.md §1 · C*', quote: '故意在 C* 里放 4 个 invalid、5 个 error 候选,防止崩溃被静默写成 0.0;c05_overlapping 的名义值等于最高分但它是 invalid。' },
    consequence: '一个在所有条件下都完美的指标意味着任务退化、指标饱和、或投影侧能看到答案。exp3 目前不能作为 L4 的证据,需要先给出一个它能失败的对照。【推断:我没有读 report.tex 的实验 C 正文】',
  },
  {
    id: 'snapshot', title: '语料不是对话的纯快照', kind: 'provenance', evidence: 'v',
    left: { who: '重放出的对话版 v4', cite: 'replay_state_control.py 对拍', quote: '102226 B。链条末端 refs_v4.bib 与磁盘逐字节相同,所以链条是完整的。' },
    right: { who: '磁盘上的 v4', cite: 'related_files/research_state_control_review_v4.tex', quote: '102563 B。多出的 337 B / 15 处全是排版:1 处 \\emergencystretch、2 处 \\allowbreak、29 行把 \\boxed 重排为 gathered。' },
    consequence: 'emergencystretch 与 allowbreak 在载荷 2 864 505 字符里 0 命中 ⇒ 对话结束后又排过版。含义:mtime 和内容都不能单独用来判断一份文档属于哪一轮。',
  },
  {
    id: 'bundle', title: 'repro bundle 打包时改坏了 bib 引用', kind: 'provenance', evidence: 'v',
    left: { who: 'tex 的期望', cite: 'agent_engineering_science_report.tex:14', quote: '\\addbibresource{references.bib}' },
    right: { who: '包里的实际', cite: 'unzip -l', quote: 'agent_engineering_science_references.bib —— references.bib 在包内不存在(grep -c = 0)。' },
    consequence: '成因可查:09-24 05:02–05:03 写过两个 bib,打 zip 时扁平化并统一改名,没有同步改 tex。⇒ bundle 按现状编译不出 PDF。',
  },
  {
    id: 'adr', title: 'adapdc 双份的未闭合自我矛盾', kind: 'contradiction', evidence: 's',
    left: { who: '(1) 版 ADR-001', cite: 'adapdc_scaffold_implementation(1).typ:17', quote: '要求把旧版标记为「部分条款已取代」。该标记从未加上。' },
    right: { who: '旧版', cite: 'adapdc_scaffold_implementation.typ:32', quote: '「不能同时保留相反的现行决策。」' },
    consequence: '两份现都被 git 跟踪(提交 14edbf07)。【二手:我未复核这两行】',
  },
  {
    id: 'search-vs-library', title: '同一条目,搜索说没有、库页说在', kind: 'provenance', evidence: 'v',
    left: { who: '站点搜索', cite: 'search「open_world_plan」→ 0 命中', quote: '按这条证据推论:账户里没有 B 线那六版,与载荷侧「只有读取窗口、无写入」的结论互相印证。' },
    right: { who: 'Library 页面', cite: 'chatgpt.com/library,159 条', quote: 'open_world_plan_independent_review(1)…(6).typ 六张卡片俱在,Modified 09-18→09-20。' },
    consequence: '两条证据都真:搜索只索引对话与文档语料,不索引 File。用「搜索无命中」推断「文件不存在」,让本项目在一个季度里把「B 线不可恢复」写进了三处记忆与一张反转表。凡涉及文件存在性,一律以 Library 页面为准;搜索只用来定位对话与文档。',
  },
]

/* ------------------------------------------------------------------ decisions */

export const DECISIONS: Decision[] = [
  { id: 'D1', group: 'landing', status: 'blocked', question: '机制 A 接线 → 30 分钟长会话 → 对抗绕过探针 → 冻结(四步一步都没走完)', cite: 'TIMING-REVIEW §5.4', blocks: ['D2', 'D5'] },
  { id: 'D2', group: 'landing', status: 'open', question: 'T1 是否换载体?Max-Cut 启发式是预训练最密集的一类,G₃ 可能结构性地无法通过;换载体的代价(新套件、新 E*、新门、新标定)没有计入任何成本表', cite: 'TIMING-REVIEW §4.3 §7.4', recommendation: '这一条决定后面几个月,应当先于 D5 决定' },
  { id: 'D3', group: 'landing', status: 'open', question: 'G₃ 用 (a) 便宜两臂 pilot 还是 (b) 并入 B0a?(a) 是否构成「同一数据用两次」', cite: 'TIMING-REVIEW §3.2', recommendation: 'TIMING-REVIEW 倾向 (a),但需要复核者确认' },
  { id: 'D4', group: 'landing', status: 'open', question: 'θ、k、C_min 预注册;r̂ 与 ℓ 是否退化成一维(需引入残差幅度阈值 ε_J)', cite: 'TIMING-REVIEW §3.5 §7.2' },
  { id: 'D5', group: 'landing', status: 'open', question: '是否跑 8 个 campaign(R_A1^main 目前是空集)', cite: 'A1-RESULT §7' },
  { id: 'D6', group: 'landing', status: 'open', question: 'τ 是否把 A1/标定侧也统一到 10 s(门这一侧已经是 10 s)', cite: 'A1-RESULT §10.2' },
  { id: 'D7', group: 'landing', status: 'open', question: 'PILOT-PROCEDURE.md:41 的旧判定是否走显式重冻(改一字就要连带重冻 B_hard.json 并重跑 pilot;已登记 D-CAL-11)', cite: 'A1-RESULT §10.4' },
  { id: 'D8', group: 'landing', status: 'open', question: 'C 线 v4:753 要求 timing research 吸收 PPM 的 evaluation methodology,而 TIMING-REVIEW §2.8 的四个家族里没有 PPM。补不补?', cite: 'research_state_control_review_v4.tex:753' },
  { id: 'D9', group: 'theory', status: 'open', question: 'L1–L7 是否降级为「带限定条件的可证伪命题」,并单列「已证明的数学事实 / 实测关联 / 机制解释 / 新假设」四类', cite: '独立审查 · 推荐修订标题与学术定位' },
  { id: 'D10', group: 'theory', status: 'open', question: '是否用 exp1 = β-二项的复算回应审查?种子与样本量已在 report.tex:415,但生成器仍未写明,需要补脚本才算完整回应', cite: 'synthesis §6.3 §8.2', recommendation: '这是唯一一条已经有反驳材料的批评' },
  { id: 'D11', group: 'theory', status: 'open', question: 'exp3 的 1.0 是否先修?在给出一个它能失败的对照之前,L4 没有证据', cite: 'synthesis §6.7 §8.3' },
  { id: 'D12', group: 'theory', status: 'open', question: 'IntegrationEfficiency 是否先作任务条件诊断指标(分层转移概率)而非标量本体', cite: '独立审查' },
  { id: 'D13', group: 'theory', status: 'open', question: '标题是否改为审查建议的《分布式 Agent 的信息整合瓶颈:证据审查、不可识别性与系统辨识实验纲领》', cite: '独立审查' },
  { id: 'D14', group: 'cross', status: 'open', question: 'D 线与 a0/ 线是一个研究纲领的两个 arm,还是两个独立 estimand?B0a 是单因子 τ 网格,审查要的是 N×相关×聚合器×验证四因子,两者不共享可识别性结构', cite: 'synthesis §6.5', recommendation: '正确表述是「一行重叠、七行空白」:report.tex 八行矩阵的第 2 行正是 a0/ 已建好仪器的那一个' },
  { id: 'D15', group: 'cross', status: 'open', question: 'ρ 与 RQ1–RQ5 两处同名异义是否改名', cite: 'synthesis §6.1 §6.2', blocks: ['D14'] },
  { id: 'D16', group: 'cross', status: 'open', question: '四套分解(三重困难 / 五段 / 三层 / 七域)是本体冲突,还是同一框架的不同层?有了 G₀ 之后我倾向后者,但这需要用户确认', cite: 'synthesis §8 跨线项', recommendation: '若是后者,正确的动作是画映射表而不是选一个' },
  { id: 'D17', group: 'cross', status: 'open', question: 'DSS 的四处定义(A 线命题 1 已证 / C 线 Δ_B(φ) / D 线 argmin|S| / a0 的三量 s_t)是否收敛成一个', cite: 'synthesis §5 读法一', recommendation: 'A 线那个是唯一有证明的,应当作为起点' },
  { id: 'D18', group: 'cross', status: 'open', question: 'ADA 是执行载体还是已废弃?Pasted md §21 仍点名它,open_world_...plan.typ:40 称其为「可替换的实现手段」', cite: 'synthesis §8' },
  { id: 'D19', group: 'corpus', status: 'open', question: 'zip 里 5 个纯文本(report.tex + references.bib + 三个 CSV)是否提出来跟踪?它们是 D 线唯一的实验产物(模拟/合成,非真实 agent 实测),现在 git 里不存在', cite: 'synthesis §8.1', recommendation: '(b) 原样提出 + README 登记 bib 引用被打包改坏' },
  { id: 'D20', group: 'corpus', status: 'open', question: 'agent_engineering_report/agent_engineering_science.tex(heredoc 整份写入、可完整恢复,且不同于 zip 里那份)要不要也回收?', cite: 'synthesis §1.4' },
  { id: 'D21', group: 'corpus', status: 'open', question: '回收出的 v2/v3 要不要补 v4 那次后期排版?', cite: 'synthesis §8.5', recommendation: '不补 —— 它们是历史轮次的存证,不是待发布的文档' },
  { id: 'D22', group: 'corpus', status: 'open', question: 'rule-construction ×2 与 virtual_staining 是独立应用域,还是同一纲领的实例?10-06 复核:前者的结论句命中 09-14 的项目对话「对话总览与反思」,后者仍只见于项目外的对话', cite: 'synthesis §8 跨线项 + 10-06 库核查', recommendation: '原判据「连被对话读取的记录都没有」已作废 —— 站点搜索只索引对话与文档语料,不索引 File' },
  { id: 'D23', group: 'corpus', status: 'open', question: 'related_files/synthesis_2026-09-30.html 与 viz/ 是否入 git?前者被 .gitignore:62 忽略,后者需要 node_modules 与 dist 的忽略规则', cite: '本次会话' },
  { id: 'D24', group: 'corpus', status: 'done', question: 'C 线 v2/v3 是否恢复', cite: '提交 ccae0deb', recommendation: '已执行:补丁链重放 + 三次逐字节对拍' },
  { id: 'D25', group: 'corpus', status: 'done', question: '对话记录是否入库', cite: '提交 ccae0deb', recommendation: '已执行:transcript + user_turns + 两个脚本;mapping.json 与 11 MB HTML 不入库,可由脚本 0.8 s 重建' },
  { id: 'D26', group: 'corpus', status: 'done', question: 'B 线六个独立审查版本是否可恢复', cite: '提交 900bcb0', recommendation: '已执行:从账户 Library 取回 (1)–(5) 并入库;v(6) 与磁盘那份逐字节相同' },
  { id: 'D27', group: 'corpus', status: 'open', question: '三份「范畴论」报告只拿到渲染文本(markdown 标记已被剥掉),这种降级副本是否留在语料里?', cite: '提交 301a4be', recommendation: '文件名已带 .rendered.txt;若不接受,删掉即可,内容与 literature/ 里的同线 PDF 重叠' },
  { id: 'D28', group: 'corpus', status: 'open', question: '48 个归档(adapdc-src-review-*.tar ×36、adapdc-c2-review ×3、payload.tar ×3、emsx_workspace ×5、repository-review ×1,另有 8 个 open-problem-lab zip)是否下载作恢复源?', cite: '10-06 库核查', recommendation: '归档在跟踪白名单外,入库与否是两件事;下载只解决「手里有没有」' },
  { id: 'D29', group: 'corpus', status: 'open', question: 'research-foundations.md 的正文说「研究起点:继承自 emsx 的已证结论」—— 它归本语料,还是归 emsx 那个项目?', cite: '10-06 库核查', recommendation: '已取回但未入库(留在 /tmp);归属由用户定' },
  { id: 'D30', group: 'corpus', status: 'open', question: 'adapdc_architecture_report.typ 与 adapdc_theory_review(1).typ 的预览始终不渲染,是否换通道或过些时候重试?', cite: '10-06 库核查', recommendation: '两者都是 .typ,理论上可走拼接通道;先怀疑是暂时性加载失败' },
  { id: 'D31', group: 'corpus', status: 'open', question: '把账户 Library 当定期同步的恢复源,还是只在需要时核查?', cite: '10-06 库核查', recommendation: '倾向后者:一次核查已证明「搜索会漏、下载已坏、归档不入库」,例行同步的成本高于收益' },
  { id: 'D32', group: 'cross', status: 'open', question: '记忆基底 = 信息划分的实现层(稿 4)。反向映射:机制 → 旋钮 → 特征损失 —— 八种机制没有一种「不损失」,选机制就是选放弃哪个旋钮。四条新内容:①压缩/遗忘的触发器从容量改为矛盾密度;②相关性过滤按构造无法产出 nontrivial(结构性盲区,不是概率漏检);③强制边界是工具持有者,而系统里没有 MMU ⇒ 单写者是系统级单点,且信息划分的丢失在构造上不可见;④三个裁决器 T1–T3。', cite: 'related_files/1006/memory_substrate_and_partition.typ;v4:37（底座+视图）、:322（可机械验证者提升为 code）、:469（提升须过 replay）', recommendation: 'T1–T3 只需本地语料,近零 credits;未通过前这几条只是 SOP 候选,不是 invariant;单写者是否可接受需用户裁决' },
  { id: 'D33', group: 'cross', status: 'open', question: 'society = 四元组(聚合 / 信息划分 / 反转成本 / 权威可变性)+ 宪法层,三个时间尺度(任务 / 族 / 实验);适应只在「静态 spread > 探索成本」时动手。不是「按阶段换模型」—— 要问的是该实例化哪个四元组。', cite: '1006/model_society_as_allocation.typ, society_as_learned_structure.typ, society_belief_and_law.typ(稿 1–3 的 kill 1–3 与 Step 0)', recommendation: '记忆基底决定反转成本,因而决定适应值不值得买 —— 这是 D32 与 D33 的接口;先做稿 3 §5 的静态矩阵,再谈适应' },
]

export const DECISION_GROUPS = {
  landing: '落地侧(a0/)', theory: '理论侧(D 线)', cross: '跨线', corpus: '语料与仓库',
} as const

/* ------------------------------------------------------- narrowing, quantified */

/** The point of the whole exercise: how much of G0 is actually instrumented. */
export const NARROWING = {
  capabilities: { total: 4, measured: 1, measuredName: 'Allocate', cite: 'v4.tex:1250-1263' },
  resources: {
    total: 6, measured: 1, measuredName: '检索(外部获取)',
    names: ['token', 'wall-clock', '实验', '检索', 'subagent', 'human attention'],
    cite: 'v4.tex:1254 (Allocate 的定义)',
  },
  experimentMatrix: { total: 8, instrumented: 1, row: 'Retrieval timing', cite: 'agent_engineering_science_report.tex 建议的首批真实实验矩阵' },
  killChain: { depth: 3, reached: 3, unmeasuredBelow: ['RQ1 Recoverability', 'RQ2 Decision-sufficient state'], cite: 'v4.tex:1561-1563' },
  stages: { total: 2, reached: 1, names: ['受控 exogenous packet 的因果 timing assay', 'live open-world search'], cite: 'v4.tex:463' },
  campaigns: { planned: 8, run: 0, cite: 'a0/A1-RESULT.md §7 — R_A1^main = ∅' },
}
