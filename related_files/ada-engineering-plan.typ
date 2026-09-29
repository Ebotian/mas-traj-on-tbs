#set document(title: "ADA 研究环境工程计划", author: "工程研究计划", date: datetime(year: 2026, month: 9, day: 16))
#set page(paper: "a4", margin: (x: 19mm, y: 17mm), numbering: "1", header: align(right, text(size: 8pt, fill: rgb("64748b"), "ADA 研究环境工程计划")), footer: context align(center, text(size: 8pt, counter(page).display("1"))))
#set text(font: ("Noto Serif CJK SC", "Noto Sans"), size: 10pt, lang: "zh")
#set par(justify: true, leading: 0.6em, spacing: 0.9em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): set text(size: 18pt, fill: rgb("163553"))
#show heading.where(level: 2): set text(size: 12pt, fill: rgb("244969"))
#show raw: set text(font: "Noto Sans Mono", size: 7.5pt)
#show table.cell: set text(size: 8.6pt)
#text(size: 23pt, weight: "bold", fill: rgb("163553"), "ADA 研究环境工程计划")

#text("源码调研 · 独立开发 · 跨仓库契约 | v1.0 · 2026-09-16")

#heading(level: 1, "决策摘要与工作范围")
#text("目标：在保留 AdaPDC 现有 TS＋Temporal＋PostgreSQL＋Python 底座的条件下，将可追溯计算扩展为可由 Kimi＋OPL 或其他客户端使用的研究环境。ADA 负责问题语义、冻结实验、运行事实、领域证据与采用关系；不负责宿主会话、提示词演化或通用 agent 主循环。")

#heading(level: 2, "本计划的地位")
#text("版本 1.0，2026-09-16，工程设计评审稿。依据当前会话中的 adapdc-src-23be91b 源码快照与 OPL 0.6.3 安装包；目录名不是已验证的完整 Git commit。未访问用户机器上的最新工作树，也未重跑 C0–C7。本文“确认”指指定源码路径，“复现”仅指本次列明的局部实验，“拟议”指待实施方案。")

#text("本次授权是调研和编写计划，不修改项目。后续实施遵循 ADA AGENTS.md 的逐步审核与最小侵入要求；本稿不自动取代既有 ADR。计划将每个工作包做成可单独审阅、回退的提交边界。")

#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("必须保留")

],
[#text("本轮新增")

],
[#text("明确后置")

],
[#text("ResearchSnapshot／Plan 身份分离")

],
[#text("协议入口、异步回执、领域证据与主张关系")

],
[#text("全新图数据库、通用科研平台")

],
[#text("CAS 不覆盖发布与 catalog 恢复")

],
[#text("Optuna 有界参数搜索适配")

],
[#text("多个程序演化框架同时接入")

],
[#text("冻结运行环境与缓存校验")

],
[#text("跨仓库契约夹具与首次集成切片")

],
[#text("改写 Kimi runtime 或维护 agent fork")

])

#text("优先级按阻断风险安排，不预设研究算法赢家。首个完整交付是“提交一个冻结实验 → 中断客户端 → 查询完成 → 证据关联主张 → 新会话复用”。参数搜索和研究策略收益在该链路之后分别测量。")

#v(10pt)
#heading(level: 1, "源码基线与实际接缝")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("定位")

],
[#text("已确认行为")

],
[#text("工程含义")

],
[#text("contracts/src/snapshot.ts")

],
[#text("comparisonProtocol 可选；theory 与 plan 各有引用")

],
[#text("新增科学协议不应把说明文字灌入计算缓存键")

],
[#text("worker/src/client.ts::startExecution")

],
[#text("start 后 await handle.result；重复启动先比较提交清单")

],
[#text("保留一致性检查，拆出 submit 与 await 两层")

],
[#text("worker/src/workflows.ts::executePlanV1")

],
[#text("按拓扑串行；Activity 两分钟、最多三次")

],
[#text("不能直接宣称已支持小时级训练或 DAG 并发")

],
[#text("worker/src/activities.ts::executeNode")

],
[#text("独立 attempt；完成清单幂等；跨执行缓存先核对")

],
[#text("扩展新执行种类时沿用现有发布／登记边界")

],
[#text("catalog/src/status.ts::queryExecutionStatus")

],
[#text("完成、登记、完整性分别报告")

],
[#text("外部协议不得压成单一 success 布尔")

],
[#text("worker/src/runtime.ts::runPythonTask")

],
[#text("直接 spawn demo_ops.task，继承环境并清空 PYTHONPATH")

],
[#text("不是通用不可信候选运行器；不能把任意代码直接接入")

])

#text("runtime.ts 当前读取 stderr，但本次所读 spawn 段未见 stdout 消费、取消转发或子树收口；结合包内 T09 孤儿进程负结果，应在接入长任务前实测。这里不声称所有命令都存在同样问题，也不把 Temporal Activity timeout 等同于操作系统进程已终止。")

#text("catalog/src/topic.ts 已提供主题查询与共享扫描结果；扩展其输出视图比建立第二套研究索引更合适。科学主张关系需新增有语义的记录，而不是让 topic 查询猜测自然语言是否已被证明。")

#v(10pt)
#heading(level: 1, "外部源码取舍：复用什么、补什么")
#heading(level: 2, "Optuna：适合执行解耦，但不提供跨系统事务")
#text("Study.ask() 在非 optimize 循环中发现 heartbeat 配置会发出警告；_tell_with_warning() 在 skip_if_finished 为真时直接返回已有终态，不比较此次传入结果与旧结果是否一致。COMPLETE 要求值；FAIL／PRUNED 不接收显式值；sampler.after_trial 后由 finally 写入状态。因此重放、崩溃与冲突处理必须由 ADA adapter 明确定义，不能仅用 skip_if_finished 当幂等证明。[U1/U2]")

#text("采用公开 Study.ask／tell API，禁止依赖其私有 storage 字段。ADA 维护 study＋trial_number＋request_digest＋execution_id 映射，以及冻结结果摘要。未知运行状态先对账，不立即 tell FAIL；失败不作为零成本成绩回填。")

#heading(level: 2, "GEPA：共享 evaluator 契约，不把它放进 Workflow")
#text("GEPAAdapter 以组件文本映射为候选，评价返回逐样本输出、分数和可选轨迹；缺自定义批处理时顺序执行。engine 的 adapter checkpoint 只做浅字典拷贝。ADA 提供不可变领域评价和完整反馈；搜索状态由 OPL 或独立搜索作业管理。领域指标到搜索分数的变换必须版本化，不能默认把不同单位指标平均。[U3/U4]")

#heading(level: 2, "采用与暂缓")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("来源")

],
[#text("本轮策略")

],
[#text("进入实现前条件")

],
[#text("Optuna")

],
[#text("直接依赖＋窄 adapter")

],
[#text("锁定发布版本／代码摘要；对账、重复 tell 测试")

],
[#text("GEPA")

],
[#text("接受其需要的逐实例反馈结构")

],
[#text("本轮不接管搜索循环；由 OPL 实现搜索侧适配")

],
[#text("Recuris")

],
[#text("借同时重评 baseline 的设计")

],
[#text("统计单位与主张语义由本项目定义")

],
[#text("SkyDiscover／ShinkaEvolve")

],
[#text("保留外接作业接口")

],
[#text("本次未深入其 runner 源码，不批准直接替换 Temporal")

])

#text("复用收益来自减少参数优化与搜索实现，不来自减弱领域验收。外部库升级先通过 adapter 兼容测试，再更新锁定记录；不跟随 main 自动升级。")

#v(10pt)
#heading(level: 1, "领域数据模型与权威来源")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("拟新增对象")

],
[#text("必要字段")

],
[#text("权威与约束")

],
[#text("ComparisonProtocol")

],
[#text("scope、information_set、sampling、metrics、acceptance、split_ref")

],
[#text("ADA；确认集与探索集分开，方向／单位显式")

],
[#text("EvidenceEnvelope")

],
[#text("subject_ref、evaluation_ref、kind、scope、raw_refs、producer")

],
[#text("不可变 CAS 制品；签名证明来源，不证明领域命题")

],
[#text("ClaimRevision")

],
[#text("claim_id、revision、statement、assumptions、scope、evidence_refs")

],
[#text("不可变主张版本；自然语言不能自行推出机器判决")

],
[#text("AdoptionEvent")

],
[#text("claim_ref、policy_ref、decision、evidence_refs、supersedes")

],
[#text("追加事件；用明确取代关系，不靠最新时间胜出")

],
[#text("ClaimDependency")

],
[#text("from_revision、to_revision、relation、condition")

],
[#text("论证依赖；supports／contradicts／assumes／supersedes 分开")

])

#text("采用状态建议为 proposed／accepted／needs_review／withdrawn；形式证明状态仍属于证据本身。上游撤回时，下游先标记 needs_review，并保留传播路径，不自动判假、不删除旧运行、不默认重算所有后代。计算依赖仍由现有输入摘要和 Plan 管理。")

#text("先发布不可变证据与事件文件，再事务登记 PostgreSQL 派生索引。若登记失败，查询返回 unavailable／pending 状态，并由扩展 reconcile 恢复。重建索引必须只依赖声明的权威制品；不得只在 PostgreSQL 保存无法恢复的采用事实。")

#text("同一采用事件的身份由主张版本、证据摘要有序规范集合、接纳策略与决定内容导出；并发修改需 expected_revision。两个基于同一旧头的不同更新只能一个成为新头，另一个产生显式冲突。科学事件不得写进现有 node 完成状态字段。")

#v(10pt)
#heading(level: 1, "跨仓库协议 RE/1：ADA 的实现责任")
#text("RE/1 是本稿提出的最小交换契约，两份计划使用相同语义。协议规范和 JSON Schema 首版由 ADA 仓库维护并发布版本制品；OPL 消费发布制品或校验后的夹具副本，不 import ADA TypeScript 源码。涉及新版本的共同讨论不等于强制同步发版。")

#table(columns: (34%,66%), inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("对象／字段")

],
[#text("规范")

],
[#text("schema / operation")

],
[#text("research-env/1；未知主版本拒绝；操作按 capabilities 协商。")

],
[#text("request_id / idempotency_key")

],
[#text("request_id 用于日志关联；幂等键按环境与项目命名空间唯一。相同键不同请求摘要必须冲突。")

],
[#text("spec_ref / candidate_ref")

],
[#text("引用均含 digest、schema；locator 只是位置提示，不参与内容身份。解析后必须验摘要。")

],
[#text("protocol_ref / budget_ref")

],
[#text("比较协议与预算均冻结；修改评价条件产生新 evaluation identity。预算未知不得填零。")

],
[#text("receipt")

],
[#text("execution_id、request_digest、环境身份与查询方法；回执表示受理，不表示完成或科学结论成立。")

],
[#text("status")

],
[#text("execution、registration、integrity、scientific_verdict 分栏；unknown、unavailable 与 rejected 不混用。")

],
[#text("evidence / adoption")

],
[#text("证据不可变；采用是另一个追加事件，绑定主张版本、证据集合与接纳策略。")

])

#text("建议首版操作：capabilities、submit、status、evidence.get、claims.query。cancel 在完成真实子进程收口前 capability=false；不得先暴露一个仅改变数据库状态的取消接口。请求通过固定命令 argv＋请求文件传递，不把模型文本拼入 shell。")

#raw("Request = {schema, operation, project_id, request_id,\n  idempotency_key, spec_ref, candidate_ref?, protocol_ref, budget_ref}\nReceipt = {schema, request_digest, execution_id, environment_id}\nError = {code, retryable, reason, details_ref?}", block: true)

#text("未知顶层字段按版本 schema 处理；新增可选信息置于约定 extensions 容器。消费者对未知枚举不得映射为成功。领域可用性来自 capabilities 与协议，不由 OPL 根据目录名猜测。")

#v(10pt)
#heading(level: 1, "提交、恢复与进程生命周期")
#heading(level: 2, "提交入口改造")
#text("新增 submitExecution(submission) 返回回执；awaitExecution(executionId) 保留等待行为；现有 startExecution 作为两者的兼容包装。首次启动与重复启动均复用 compareSubmissionContent。请求规范摘要应在启动前持久化；收到不确定网络结果后，以同幂等键查询，而不生成新 executionId。明确独立重跑才换身份。")

#text("不要将现有 Workflow 历史直接改写。仅拆客户端不会改变 Workflow；若为长任务调整 Activity 或执行种类，采用新 Workflow 类型 executePlanV2 并保留 v1 worker，或使用 Temporal 支持的版本迁移机制。旧 T17 History replay 必须继续通过。")

#heading(level: 2, "长任务必须先补实际资源契约")
#text("新增冻结 ExecutionPolicy：wall_timeout、heartbeat_interval、memory_limit、process_limit、network_policy、runner_kind。首版仅声明已实测平台能力。每个 attempt 的 stdout／stderr 直接落文件并限定日志体积；超时、取消与 Worker 死亡需证明子树退出后才报告清理完成。租约与 heartbeat 用于发现失联，不证明进程已死。")

#text("领域可信计算继续使用现有 Python 操作协议。不可信生成程序经 OPL 独立发布的 runner／核验命令适配，或另一个满足相同契约的 runner。ADA 不复制 opl_sandbox.py；OPL 不接管整个 Temporal 工作流。单项运行只有一个生命周期管理者。")

#heading(level: 2, "精确恢复边界")
#text("若进程在完成清单前死亡，结果暂不算正式完成；若完成清单已存在但登记失败，沿用清单恢复登记，不重算。临时 attempt 不得被用作可比较成绩。运行结果、运行状态、采用状态分开恢复；取消请求与完成事件竞态按实际已发布证据报告，不撤销历史。")

#v(10pt)
#heading(level: 1, "参数搜索 adapter 与反馈契约")
#heading(level: 2, "Optuna 有界 ask–tell 作业")
#text("使用专门的搜索协调进程，默认一个 study 仅一个写入者；锁按 study 生效。建立 search_trial_events 文件事件与 catalog 映射。流程为 reserve → ask → persist trial mapping → submit → collect → persist result → tell → acknowledge。每个边界写可重放事件；每次重启先对账再继续发提案。")

#text("ask 已创建 trial 而本地映射未写的窗口不能假装不存在：启动前写 reservation，利用公开 trial user_attrs 标注关联；若仍出现无法归属的 RUNNING trial，隔离并报告 orphan_trial，不猜测对应实验。首版保持单写者与保守恢复；不宣称跨 Optuna／ADA exactly-once。")

#text("tell 前核对 frozen result digest。若 trial 已完成，读取既有状态和值，与预期规范结果对比：同内容视为重复确认，异内容返回 result_conflict。失败、被剪枝、超时与未知各有显式映射；不把业务不可行和执行故障混为一类。搜索自身 sampler 状态恢复与实验计算可复现是不同承诺。")

#heading(level: 2, "反馈必须同时服务人和 agent")
#table(columns: 2, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("反馈部分")

],
[#text("要求")

],
[#text("原始事实")

],
[#text("逐实例数值、单位、方向、预算、输入与代码摘要")

],
[#text("违规信息")

],
[#text("信息泄漏／不可行动作等硬约束，提供见证")

],
[#text("诊断摘要")

],
[#text("带依据引用；模型解释标记为 inference")

],
[#text("可比较性")

],
[#text("比较协议、样本集、重复单位和评价器一致性")

],
[#text("资源耗用")

],
[#text("已结算／在途／未知费用分栏；不把未知算零")

])

#text("研究采样与优化采样分离：优化器的自适应 trial 不代表目标机制总体。最终结论用冻结确认协议；参数空间或 evaluator 改变创建新 study lineage，不混用旧排行榜。")

#v(10pt)
#heading(level: 1, "工作包、文件落点与迁移")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("工作包")

],
[#text("拟改动／新增")

],
[#text("退出条件与回退")

],
[#text("A0 基线／协议")

],
[#text("contracts 新增 research-env.ts；发布 JSON Schema＋夹具")

],
[#text("两语言读同一例；未知版本拒绝；回退可完全不启用新入口")

],
[#text("A1 异步入口")

],
[#text("worker/client.ts；cli/commands 新增 research.ts")

],
[#text("同请求重提同回执，异内容冲突；旧 startExecution 不变")

],
[#text("A2 生命周期")

],
[#text("worker/runtime.ts；新 runner policy；v2 Workflow（若需要）")

],
[#text("长任务收口、日志、不确定状态实测；未过禁用长任务 capability")

],
[#text("A3 证据／主张")

],
[#text("contracts/evidence.ts、claim.ts；catalog/claims.ts；增量 SQL")

],
[#text("发布后登记故障可恢复；旧 schema 与旧查询继续可读")

],
[#text("A4 Optuna")

],
[#text("新增 Python adapter 包；trial 事件映射")

],
[#text("每个崩溃窗口可对账；同 trial 异结果必冲突")

],
[#text("A5 集成研究")

],
[#text("领域 evaluator、OPL 环境描述、真实切片")

],
[#text("跨会话复用成功；研究正确性由独立协议判定")

])

#text("以上新增路径是建议，不是现存文件。先确认实际 Python 包布局再落 adapter 目录，避免仅为了规划建立一套平行包层。包内现有通用构建、类型与测试工具继续复用。")

#text("依赖：A0 → A1；A1 → A2；A0 → A3；A1＋A2 → A4；A3＋A4＋OPL 对接 → A5。A3 可在 A2 开发期间独立完成，但集成前都要通过。")

#text("迁移采用增量表与新 schema。现存 ResearchSnapshot 的 comparisonProtocol 仍可缺省，查询明确 legacy_unspecified；对新科学接纳则要求协议存在。只改理论说明不得改变旧 Plan／执行键，使用 t20-theory-only 作为守护。不自动为旧结果补造科学结论。")

#text("每个工作包交付：改动清单、契约差异、局部验证原始输出、迁移／回退方式及未支持情况。实际工期取决于本地服务与 runner 平台验证；不把未经实施的天数估计当作保证。")

#v(10pt)
#heading(level: 1, "验收矩阵与首个研究切片")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("编号")

],
[#text("场景")

],
[#text("必须观察到")

],
[#text("A-T01")

],
[#text("同键同请求／异请求")

],
[#text("同 execution；异请求 registration_conflict")

],
[#text("A-T02")

],
[#text("submit 回执丢失后重连")

],
[#text("不创建第二实验、不重复扣预算")

],
[#text("A-T03")

],
[#text("清单提交后 catalog 断开")

],
[#text("计算完成与登记未知并存；恢复后仅登记")

],
[#text("A-T04")

],
[#text("长任务超时／Worker 被杀")

],
[#text("子进程及逃逸子树实测收口；失败时 capability 不可启用")

],
[#text("A-T05")

],
[#text("证据材料缺失／损坏")

],
[#text("不可采用；定位缺失引用，不返回空成功")

],
[#text("A-T06")

],
[#text("撤回前提／仅改解释")

],
[#text("论证下游需复核；计算结果与缓存不无故销毁")

],
[#text("A-T07")

],
[#text("Optuna tell 重复且异值")

],
[#text("重复同值幂等；异值 conflict")

],
[#text("A-T08")

],
[#text("旧 History 与旧 schema")

],
[#text("保留 T17 replay、t20 身份分离、C3 恢复语义")

],
[#text("A-T09")

],
[#text("OPL 不可用")

],
[#text("普通 JSON 客户端仍可调用 ADA；无强制插件依赖")

])

#heading(level: 2, "真实切片：固定 T，研究损失 ℓ")
#text("协议先冻结调度映射、信息集、机制采样、扰动方案与闭环成本。比较损失排序是否与成本排序一致，以及动作边界处的失配；此时无需先训练预测器。领域研究候选可由手工、随机、OPL 或外部搜索器提出，评价相同。")

#text("确认阶段按独立机制实例或站点／周期簇配对，不能把相关的五分钟点当独立样本。探索集用于选方案，确认集只用于冻结后的结论；反复查看确认结果需要新的确认集或事先规定的序贯校正。报告效应与至少 95% 区间；无须预设最小效应，但资源／可行性硬约束单独检查。")

#text("对账故障可用受控 fixture；BESS 数值、在线信息边界和真实费用必须在本地数据上检验。工程门通过不等于损失研究命题成立。")

#v(10pt)
#heading(level: 1, "风险裁决与评审顺序")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("风险")

],
[#text("本稿裁决")

],
[#text("仍须本地确认")

],
[#text("双重事实源")

],
[#text("文件证据／事件为真源，catalog 为索引")

],
[#text("从制品重建新主张索引的完整性")

],
[#text("宿主越过工具直接改文件")

],
[#text("协议不等于 OS 权限隔离")

],
[#text("可信边界与用户执行权限；不声称哈希可防同用户伪造")

],
[#text("签名证据搬迁")

],
[#text("不改已签字节；材料化解析另有上下文")

],
[#text("OPL v2 bundle 与旧 v1 路径兼容")

],
[#text("演化改评价器")

],
[#text("候选与评价协议分别冻结")

],
[#text("允许研究评价器时建立新协议 lineage")

],
[#text("超时重复计算")

],
[#text("已有清单优先；不确定状态显式")

],
[#text("取消、子树收口和资源租约实测")

],
[#text("未测框架直接集成")

],
[#text("SkyDiscover／ShinkaEvolve 留后续专项")

],
[#text("实际收益、许可证文件与依赖成本")

])

#text("评审顺序：先确认 RE/1 字段和权威边界；再审 A1 异步兼容实现；长任务能力必须通过 A2 实测；最后批准 A3 科学接纳与 A4 搜索适配。既有代码与 ADR 有冲突时，提交显式 ADR 变更，不用本稿日期覆盖已裁决规则。")

#text("首轮停止条件：普通客户端和 Kimi＋OPL 均可完成同一冻结研究切片，恢复不重复提交，结论可追索适用范围。此后再以数据决定是否需要更复杂的并发、检索或演化后端。")

#pagebreak()
#heading(level: 1, "外部源码索引")
#text("本附录给出实际读取的文件定位与内容摘要。全文对外部库的选择属于工程推论，不代表已复现其论文成绩。远程 SHA 为 Git blob 身份，不能冒称整个仓库 commit；含固定 commit 的链接可按该快照复核。")

#heading(level: 2, "U1 · Optuna _tell.py")
#link("https://github.com/optuna/optuna/blob/master/optuna/study/_tell.py")[#text("https://github.com/optuna/optuna/blob/master/optuna/study/_tell.py")

]
#raw("Git blob SHA: 386a8d787ab1f52bfeed6c2b0b40cd72cb898f1e", block: true)

#heading(level: 2, "U2 · Optuna Study.ask/tell")
#link("https://github.com/optuna/optuna/blob/master/optuna/study/study.py")[#text("https://github.com/optuna/optuna/blob/master/optuna/study/study.py")

]
#raw("Git blob SHA: 18ad8bb9a806d19c7531ca92dcc778b6e5a3753a", block: true)

#heading(level: 2, "U3 · GEPA adapter")
#link("https://github.com/gepa-ai/gepa/blob/main/src/gepa/core/adapter.py")[#text("https://github.com/gepa-ai/gepa/blob/main/src/gepa/core/adapter.py")

]
#raw("Git blob SHA: 6f59b20c9156eb97d9c83f688c0471931181e136", block: true)

#heading(level: 2, "U4 · GEPA engine")
#link("https://github.com/gepa-ai/gepa/blob/15ee314f9c7d34ec153b809d401f42f55c4dcd76/src/gepa/core/engine.py")[#text("https://github.com/gepa-ai/gepa/blob/15ee314f9c7d34ec153b809d401f42f55c4dcd76/src/gepa/core/engine.py")

]
#raw("Git blob SHA: cf25bf661fb59a8cb164da15e46a6557b0fea88b", block: true)

#heading(level: 2, "U5 · Recuris 简易 gate")
#link("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/gate.py")[#text("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/gate.py")

]
#raw("Git blob SHA: 99864db1e046031843359a259e50efb77f4d42fe", block: true)

#heading(level: 2, "U6 · Recuris 配对 gate")
#link("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/gates.py")[#text("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/gates.py")

]
#raw("Git blob SHA: eba16d24d753a524adac3758758ce7f6efe642cb", block: true)

#heading(level: 2, "U7 · Recuris driver gate")
#link("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/driver.py")[#text("https://github.com/Gen-Verse/Recuris/blob/7d3745ab787b1206ccd981cb1511100476097266/src/recuris/metaagent/driver.py")

]
#raw("Git blob SHA: 93faf6a0f090792a48d8cf34ea46256409274916", block: true)

#heading(level: 2, "U8 · Kimi 公开插件解析")
#link("https://github.com/MoonshotAI/kimi-cli/blob/86f136422a0aae6b217ea49e7ea1d2e8a1defcd2/src/kimi_cli/plugin/__init__.py")[#text("https://github.com/MoonshotAI/kimi-cli/blob/86f136422a0aae6b217ea49e7ea1d2e8a1defcd2/src/kimi_cli/plugin/__init__.py")

]
#raw("Git blob SHA: 7359c3c4317669b5279a2d06d690af4d6a19e863", block: true)

#heading(level: 2, "U9 · Kimi 官方插件文档")
#link("https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html")[插件清单、技能与会话加载文档]
#text("访问日期 2026-09-16；属于文档事实。目标宿主版本行为仍须本地实测。")

#pagebreak()
#heading(level: 1, "本地源码身份与验证边界")
#text("以下 SHA-256 对应本会话勘察快照；计划正文路径以各仓库根为基准。安装包与源码仓库布局不同须先映射。")

#text("packages/contracts/src/snapshot.ts")

#raw("b77e0604c610f08f4398dacf8de7050958cf6eeeecdb876b7edc12fe9452e4cf", block: true)

#text("apps/worker/src/client.ts")

#raw("c83b0cad2c927b9d68d162691dd25f7bbfb6714f8afeedd9f87ab428f686b7bf", block: true)

#text("apps/worker/src/workflows.ts")

#raw("4ab0da69bcd642ad963028b61d21de58367e216859024314d8af3ea4c69dafd9", block: true)

#text("apps/worker/src/runtime.ts")

#raw("0b78ca409a145e5bdf98abef9effbb41f8d11094a062be77a505db520bd4ddd7", block: true)

#text("apps/worker/src/activities.ts")

#raw("02c48f872bbe773d16806d7265c2fe6f1220f2f2fe2655914a079588c3c22d86", block: true)

#text("packages/catalog/src/status.ts")

#raw("8fc71b9f9100919e80ed468776fd54170f656cef5bef0e12e3a53fd0cdac1a46", block: true)

#text("packages/catalog/src/topic.ts")

#raw("4cae42cca7f076eb49e9d1ed9ef9b7c21a33915ffa4118d022b3b4ec73c07952", block: true)

#text("apps/worker/src/submission-consistency.ts")

#raw("8a951c63edb789610ca0f6789936c4bb2883184fe84c9a3cee2682a125605ffc", block: true)

#text("AGENTS.md")

#raw("ef1d93d3029f33f70f33f864440d5761a401c1b766791997ad5330742c7db01c", block: true)

#text("验证范围：本次执行 OPL suggest 过滤回退的临时库微型复现；未运行完整项目回归、Temporal 服务、Kimi 模型任务或本地 BESS 数据。本工程计划的 PDF 已从对应 Typst 源编译并做版面检查；文档可编译不代表软件实现已通过。")

