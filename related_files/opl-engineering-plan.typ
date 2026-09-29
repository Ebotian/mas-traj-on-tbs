#set document(title: "OPL Kimi Code 插件工程计划", author: "工程研究计划", date: datetime(year: 2026, month: 9, day: 16))
#set page(paper: "a4", margin: (x: 19mm, y: 17mm), numbering: "1", header: align(right, text(size: 8pt, fill: rgb("64748b"), "OPL Kimi Code 插件工程计划")), footer: context align(center, text(size: 8pt, counter(page).display("1"))))
#set text(font: ("Noto Serif CJK SC", "Noto Sans"), size: 10pt, lang: "zh")
#set par(justify: true, leading: 0.6em, spacing: 0.9em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): set text(size: 18pt, fill: rgb("163553"))
#show heading.where(level: 2): set text(size: 12pt, fill: rgb("244969"))
#show raw: set text(font: "Noto Sans Mono", size: 7.5pt)
#show table.cell: set text(size: 8.6pt)
#text(size: 23pt, weight: "bold", fill: rgb("163553"), "OPL Kimi Code 插件工程计划")

#text("源码调研 · 独立开发 · 跨仓库契约 | v1.0 · 2026-09-16")

#heading(level: 1, "决策摘要与插件定位")
#text("目标：将 OPL 发展为 Kimi Code 的研究能力扩展，增强问题分解、工具选择、失败诊断、证据使用与经验迁移。宿主继续负责模型交互与会话；本地工具负责可执行约束。OPL 可独立用于开放问题，ADA 只是实现同一环境协议的一个项目。")

#text("版本 1.0，2026-09-16，工程设计评审稿。基线为本会话 OPL 0.6.3 安装包；包内路径无 plugin/ 前缀，真实开发仓库可能存在该前缀。未确认用户机器当前 HEAD。本文不修改插件、私钥、台账或 ADA。")

#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("OPL 保有")

],
[#text("向 ADA 委托")

],
[#text("不在本轮实现")

],
[#text("五个技能与宿主变异模式")

],
[#text("领域信息契约、冻结评价和长任务运行")

],
[#text("另造一套通用 agent runtime")

],
[#text("证书／见证／Lean 核验")

],
[#text("领域科学主张的正式采用关系")

],
[#text("自动修改宿主权限与系统提示模板")

],
[#text("候选、研究策略与操作经验")

],
[#text("数据／机制样本与统计协议")

],
[#text("在线自修改生产插件与大规模 swarm")

])

#text("必须区分优化对象：改损失函数是领域算法搜索；改 opl 的反例策略或反馈压缩是 agent 改进。两者可以用同一个优化库，但评价任务、版本谱系、预算和最终采用门必须分开。")

#text("方案保持“变异归宿主、可复核性归工具”的现有分工。外部搜索器作为显式有界作业可选启用；不默认为它授予当前 Kimi 会话的模型权限、上下文或认证。")

#v(10pt)
#heading(level: 1, "源码发现：必须先修的接口一致性")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("定位")

],
[#text("确认事实")

],
[#text("计划")

],
[#text("kimi.plugin.json")

],
[#text("五个 skills＋sessionStart；未显式声明 agents／MCP")

],
[#text("继续最小插件；新增能力按宿主实测暴露")

],
[#text("opl_evolve.py::suggest")

],
[#text("直接 all_programs 挑选；无当前评价指纹参数；缺 metric 当零")

],
[#text("共享可比较性筛选，缺值跳过")

],
[#text("suggest 的 where 分支")

],
[#text("无匹配时退回全部候选，且仍可称“当前最好”")

],
[#text("硬约束不放宽；探索父代另行标记")

],
[#text("eval_candidate")

],
[#text("首次故障在 lib.add 前返回；record(None) 无库记录")

],
[#text("候选登记与评估拆开，故障也可检索")

],
[#text("add_evaluation")

],
[#text("只要 metrics 非 None 就更新头条及来源")

],
[#text("修正文档“只有可行更新”的不一致；采用另建")

],
[#text("load_evidence")

],
[#text("签名及文件摘要校验依赖原路径")

],
[#text("新增可迁移 bundle resolver，不修改签名原件")

])

#text("本次局部复现：临时库仅有 feasible=true 候选，调用 suggest(where={feasible:false})，返回一个父代，并提示回退全部候选，why 仍为“当前最好”。实验只调用真实候选库与 suggest，不运行模型／沙箱，不修改原包。它证明筛选语义会放宽；不等同于证明所有正式 best 查询有同样缺陷。")

#text("ProgramLibrary.best 已支持 metrics_fingerprints 并跳过不可比或无来源记录；因此应复用这个比较边界，而非再写一份近似排序逻辑。不可行候选可供探索，但必须放入明确的 exploration_parents，不能与符合约束的 ranked_parents 混用。")

#v(10pt)
#heading(level: 1, "Kimi 宿主边界与兼容性关口")
#text("官方插件文档描述 kimi.plugin.json、skills、sessionStart、agents、hooks、MCP，且指出 sessionStart 只注入文本。本次取得的公开仓库快照中 src/kimi_cli/plugin/__init__.py 却定义 plugin.json、tools、inject、config_file。这是实质接口差异，不能据该源码认定当前已安装商业宿主使用相同加载器。[U8/U9]")

#text("裁决：以用户目标 Kimi 二进制上的黑盒兼容测试作为发版依据；公开源码仅用于说明差异。记录 kimi --version、二进制／安装来源、插件包摘要、启用插件清单与实际能力探测。既不宣称文档错误，也不为了迁就另一实现重写现有清单。")

#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("能力层")

],
[#text("拟采用方式")

],
[#text("必须验证")

],
[#text("入口技能")

],
[#text("短总纲＋按需加载专题技能")

],
[#text("新会话／恢复会话均能找到命令路径")

],
[#text("确定性工具")

],
[#text("现有 bin 命令；必要时窄 MCP 包装")

],
[#text("结构化返回不掺诊断文本；缺件硬失败")

],
[#text("角色化 agent")

],
[#text("后置可选 reviewer／proposer")

],
[#text("发现优先级、实际工具限制、完整交接")

],
[#text("hooks")

],
[#text("仅作为事件观测增强")

],
[#text("漏触发／宿主差异时不影响证据真源")

],
[#text("长任务")

],
[#text("RE/1 回执＋状态查询")

],
[#text("会话结束不丢任务身份，不自动重提")

])

#text("插件 runtime state 放在 lab 或显式用户状态目录，不写安装目录。升级包不覆盖研究记忆。每次运行冻结 active skill／strategy 摘要；插件 reload 只对新的受控试验生效，不能在一个配对比较中途改变组件。")

#text("环境权限约束不能仅靠技能文字。现有签名密钥同用户 shell 可读的边界继续如实说明；本轮不以插件提示词实现对用户权限的隔离。")

#v(10pt)
#heading(level: 1, "外部源码：GEPA 与 Recuris 的可取部分")
#heading(level: 2, "GEPA adapter 与 engine")
#text("采用 GEPAAdapter 的组件文本映射、逐样本 EvaluationBatch 和 make_reflective_dataset 分工；engine 已有可选 adapter 状态保存／恢复。默认 batch fallback 顺序调用，不能从接口存在推断已有并发。state 拷贝为浅拷贝，OPL checkpoint 应返回新建 JSON 树或冻结引用，避免嵌套对象继续变化。[U3/U4]")

#text("集成只依赖公开 adapter；先离线演化一个策略组件。缺模型配置、schema 错误或环境不可用属于系统故障，停止或延期本轮，不将所有任务记零分。候选确实失败才进入任务分数；完整 raw verdict 仍保留。[U3]")

#heading(level: 2, "Recuris 的两个 gate 不能混为一谈")
#text("metaagent/gate.py 接纳条件是修复改善、均值改善、回退项数限制；95% 区间仅另外报告。metaagent/gates.py::held_out_paired_gate 要求区间下界大于零并满足回退上限，按任务而非任务内重复 bootstrap；driver.py 的实际 gate 还核对配对 seed、benchmark commit、输入摘要与候选包摘要，并同时重评基线。[U5/U6/U7]")

#text("借鉴：结构化诊断、局部候选记忆、同期基线、冻结包身份。不要直接复制简易 gate 入口，也不要把其函数名称当作整个系统已经满足最终泛化验收。反复复用 dev 的选择仍需要独立确认阶段。")

#table(columns: 2, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("吸收层")

],
[#text("本轮动作")

],
[#text("GEPA")

],
[#text("可选依赖＋策略 adapter；不接替 Kimi 主循环")

],
[#text("Recuris")

],
[#text("独立实现小型经验版本／配对验收，参考其源码边界")

],
[#text("RSIAgent／ModularRSI")

],
[#text("保留快照读取与单组件变更思路；完整集成暂缓")

],
[#text("ShinkaEvolve／SkyDiscover")

],
[#text("保留搜索后端接口；另做源码与本地收益专项后再选")

])

#v(10pt)
#heading(level: 1, "候选与评估：先修事实链，再扩展搜索")
#heading(level: 2, "候选、评估、采用三层独立")
#raw("CandidateRevision {candidate_id, raw_digest, dedup_key,\n  parent_refs[], mutable_scope_ref, source_ref}\nEvaluationAttempt {attempt_id, candidate_ref, evaluator_ref,\n  problem_ref, budget_ref, execution_ref?, status, metrics_ref?}\nSelectionEvent {candidate_ref, evaluation_refs[], policy_ref, decision}", block: true)

#text("raw_digest 用真实字节作身份；现有 token code_hash 保留为去重策略键而非科学等价证明。Python 注释、行号或源码自省可能影响行为；不能将词法归一化描述成对任意 Python 的语义等价判定。是否跳过等 token 的候选由冻结去重策略决定，原始字节必须保留。")

#text("候选通过格式／可变范围检查后先登记，再创建 attempt、运行、追加结局。缺件、超时和判决冲突也有可检索记录。无效提交保存拒收回执，不占有效候选空间。新 candidate 与既有 candidate 并发命中时返回既有身份，再按评估请求幂等键裁定是否执行。")

#text("保留 metrics_evaluation_id 的来源绑定。将“最新可信评价”“当前可行最好”“正式采用”分别查询；add_evaluation 的注释与实际行为统一，不靠一列头条指标代表三个概念。")

#heading(level: 2, "文件真源与数据库索引")
#text("现有类注释称 SQLite 是派生索引，但本次检查未发现完整 rebuild 入口；不能仅据注释宣称删库无损。新增不可变候选与 attempt 清单后实现重建，再给出删索引可恢复的承诺。迁移先备份旧库并导出可得字节；缺失的失败轨迹只能标 legacy_incomplete，禁止补造。")

#text("不要把新候选状态直接塞进数学 Conjecture 的 proved／refuted。OPL 的操作经验、策略版本与形式猜想分别存储，科学采用由环境协议另行表达。")

#v(10pt)
#heading(level: 1, "研究策略与经验版本")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("组件")

],
[#text("输入")

],
[#text("输出与约束")

],
[#text("context_builder")

],
[#text("问题、状态回执、证据引用、经验版本")

],
[#text("受预算限制的上下文包＋被省略引用；事实可展开")

],
[#text("diagnoser")

],
[#text("attempt 结局、原始反馈、有效协议")

],
[#text("候选失败／环境故障／信息不足等诊断；推断标记")

],
[#text("proposal_policy")

],
[#text("上下文包、预算、候选档案")

],
[#text("实验或变异提案＋意图区别；不自行更改评价协议")

],
[#text("experience_retrieval")

],
[#text("核对过的状态特征与适用范围")

],
[#text("经验卡＋来源＋适用前提；待复核卡不作为事实")

],
[#text("experience_gate")

],
[#text("配对任务结果、版本和成本")

],
[#text("candidate／accepted／rejected／inconclusive 事件")

])

#text("首版只实现 context_builder 与 diagnoser 的窄接口，以及经验卡的候选／启用版本；不先建立多层类继承。组件按输入／输出 schema 与引用连接，替换一个组件不改变其他组件身份。组合可用性要检查前提和信息范围，而不只是字段类型。")

#text("经验卡包含 condition、action_hint、failure_modes、evidence_refs、task_scope、created_from、status；“这个求解器先归一化”是操作建议，不自动升级为科学定理。检索得到撤回依据时标记待复核；只给摘要而不保留引用的卡不得正式启用。")

#text("一次研究 run 冻结 memory_snapshot_ref。多个试验读取同一快照，产生候选 delta；提交使用 expected_parent_digest，比对失败先 rebase 并重新验证受影响组合，不最后写入者覆盖。首版本地单写者足够；不要为了将来 swarm 先建分布式记忆系统。")

#text("激活指纹只证明组件被调用，不证明它导致收益。归因要靠同模型、同预算、同期配对与消融；摘要变短、调用变少只属于中间指标。")

#v(10pt)
#heading(level: 1, "跨仓库协议 RE/1：OPL 的实现责任")
#text("以下字段与 ADA 计划保持一致。OPL 通用环境客户端消费已发布 schema，不读取 ADA PostgreSQL、不解析其内部 state 目录、不 import ADA 源码。ADA 专属字段翻译留在 ADA 发布的 endpoint／配置中。")

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

#text("拟新增 opl-env capabilities／submit／status／evidence／claims 命令组。endpoint 使用静态 argv 配置；请求文件与 stdout JSON 校验。lab 中只保存回执、引用与缓存，缓存丢失可以重新查询，不成为 ADA 正式结论真源。")

#text("客户端必须先落本地 submission intent，再提交。网络／进程中断后用同幂等键恢复；若环境返回 unsupported_operation，明确降级能力，不猜测另一私有命令。stdout 结构化错误和进程退出码矛盾时返回 UNKNOWN 并保留两者。")

#text("命令完成退出码与科学判决继续分开。历史 0–5 契约不为适配外部 HTTP／JSON 随意重定义；新增协议错误可放 reason.code，不把“受理成功”写成 verified。")

#v(10pt)
#heading(level: 1, "证据搬迁与外部搜索作业")
#heading(level: 2, "证据 bundle v2")
#text("保留已有 load_evidence 的 v1 路径语义。新增 v2 bundle：原始签名记录、签名文件、全部被引用材料、工具与环境身份、摘要到包内相对路径的 manifest。包内路径不能逃逸，符号链接和缺件显式拒绝。原签名字节不得重写路径后冒充原件。")

#text("v2 验证分两步：验证原记录的来源签名；由受约束 resolver 将逻辑引用解析到已验摘要材料。新代码仍核对 subject、kind、range、required bindings。旧 v1 只能在原路径有效时走旧验证，或在受控材料化环境复核；不凭外层 CAS 哈希声称旧 load_evidence 已能跨机器工作。")

#heading(level: 2, "GEPA 两种使用对象，分别记录")
#text("领域代码搜索：GEPA 候选为损失函数等文本，评价由 RE/1 环境完成。策略改进：GEPA 候选为一个 OPL 组件，评价运行新的 Kimi＋OPL 会话并使用冻结任务集。两个模式的候选类型、成本账户和最终采用事件不同。")

#text("首版允许有界独立 runner 与显式模型 provider；宿主交互模式仍由 Kimi 生成候选。如果没有独立模型配置，返回 capability 不可用，不能从宿主配置读取未授权凭据或假定继承会话。预算达到上限停止新提案，同时报告已承诺的在途费用。")

#text("GEPA checkpoint 保存 attempt／receipt 引用，恢复时先查已有评价；不得为补足 checkpoint 自动启动新的不同实验。adapter 的 scores 必须按固定方向变换，约束失败与环境未知分开。候选集最优只用于搜索，正式采用仍经独立 confirmation。")

#v(10pt)
#heading(level: 1, "工作包、文件落点与兼容迁移")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("工作包")

],
[#text("拟改动／新增（安装包路径）")

],
[#text("退出条件")

],
[#text("O0 宿主兼容")

],
[#text("kimi.plugin.json；兼容性测试与 capabilities")

],
[#text("实际目标 Kimi 加载／恢复／命令路径通过")

],
[#text("O1 比较修复")

],
[#text("lib/opl_evolve.py；suggest／show 薄壳")

],
[#text("过滤不回退、指标缺失不作零、旧指纹不冒充当前最好")

],
[#text("O2 候选事实链")

],
[#text("新增 opl_attempts.py；evolve 兼容包装")

],
[#text("首次故障可查询；重复请求不重复跑；索引可重建")

],
[#text("O3 环境客户端")

],
[#text("新增 opl_env.py、bin/opl-env；协议夹具")

],
[#text("无 ADA 的模拟 endpoint 可全部测试")

],
[#text("O4 证据 bundle")

],
[#text("新增 opl_bundle.py；ledger v2 resolver")

],
[#text("搬迁可验证、缺件拒绝、原签名不变")

],
[#text("O5 策略／经验")

],
[#text("新增 opl_context.py、opl_experience.py；技能更新")

],
[#text("经验版本冻结、冲突提交拒绝、诊断保留事实引用")

],
[#text("O6 可选 GEPA")

],
[#text("独立 adapter／依赖 extra；离线评估脚本")

],
[#text("单组件改进通过确认集与资源门；默认插件无新重依赖")

])

#text("路径均为拟议；落仓库时按实际 plugin/ 前缀映射，不顺手重构全部 lib。O1 优先于搜索增强；O2 为 O5/O6 提供可靠轨迹。O3 与 O4 可独立开发，用双侧 fixture 接通后再跑 ADA。")

#text("旧 evolve-init／eval／suggest 命令保留；内部委托新 candidate／attempt 层。schema version、迁移备份和 legacy 状态显式。改变 suggest 的筛选回退是有意的行为修复，应在版本说明列明。旧数学台账不批量改写，bundle v2 与 v1 并行读取。")

#text("每个工作包都输出单独审查包：源码 diff、接口与权限变化、针对性回归、实际宿主运行记录、已知边界。插件升级禁用新增可选模块即可回退；旧研究制品不删除。")

#v(10pt)
#heading(level: 1, "验收、统计与是否值得启用")
#table(columns: 3, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("编号")

],
[#text("场景")

],
[#text("期望")

],
[#text("O-T01")

],
[#text("where 无匹配／metric 缺失")

],
[#text("ranked_parents 空，不偷偷回退；探索另列")

],
[#text("O-T02")

],
[#text("改 evaluator 后调用 suggest")

],
[#text("旧指纹候选不称当前最好，排除数可见")

],
[#text("O-T03")

],
[#text("新候选首次超时／缺件")

],
[#text("保留 candidate 与 attempt；UNKNOWN 不记不可行")

],
[#text("O-T04")

],
[#text("重复评估＋故障补测")

],
[#text("幂等与显式重评区分；旧指标来源不漂移")

],
[#text("O-T05")

],
[#text("搬家／缺材料／坏签名")

],
[#text("有效 bundle 成功；其余硬失败且理由准确")

],
[#text("O-T06")

],
[#text("两分支提交同经验父版本")

],
[#text("冲突显式；不静默覆盖；复合变更重新验证")

],
[#text("O-T07")

],
[#text("Kimi 重启＋ADA 任务仍在跑")

],
[#text("读原回执继续查询；不产生新实验")

],
[#text("O-T08")

],
[#text("未配置外部模型／GEPA 缺失")

],
[#text("基线插件可用；可选搜索明确 unavailable")

])

#text("先以确定性夹具验证事实边界，再用配对真实 Kimi 任务评估策略。任务族至少覆盖反例、证明核验、算法变异和环境恢复；按族划分训练／开发／确认，避免仅在同一题的措辞变体上声称泛化。主指标选有效完成或经核实研究产出，副指标记录费用、时间和错误采用。")

#text("接纳策略拟采用：硬约束全过；主指标配对改善的 95% 区间下界大于零；无预设最小改善量；副指标使用事前声明的资源边界。未显著记 inconclusive，不等同于证明无用。若反复比较多个策略或反复查看确认集，必须调整确认方案，不能每轮独立声称 95% 保证。")

#text("与 ADA 做四组消融：旧环境／旧 OPL、新环境／旧 OPL、旧环境／新 OPL、两者均新。保持领域评价与模型预算相同，报告主效应与交互项。确认集必须由评估侧控制；策略搜索只能读开发反馈。")

#v(10pt)
#heading(level: 1, "实现顺序与不夸大的能力承诺")
#text("首轮批准范围建议为 O0–O4：先把插件兼容、候选事实链、比较语义与环境接缝做实。这些工作本身会减少重复研究和错误上下文。随后 O5 对一项明确的失败诊断／经验检索问题做配对试验，只有获得收益证据再实施 O6 的自动组件优化。")

#table(columns: 2, inset: 6pt, stroke: 0.4pt + rgb("cbd5e1"), fill: (x,y) => if y == 0 {rgb("e7edf4")} else {none},
[#text("容易误读的说法")

],
[#text("准确承诺")

],
[#text("装了技能即强制研究流程")

],
[#text("技能引导行为，工具执行确定性检查")

],
[#text("签名后证据绝对不可伪造")

],
[#text("记录来源可验；同用户密钥权限仍是边界")

],
[#text("词法 hash 相同即程序语义相同")

],
[#text("特定去重策略视作重复；真实字节另有身份")

],
[#text("GEPA 接入后 agent 自动变强")

],
[#text("只获得一个搜索机制；收益须本地配对确认")

],
[#text("索引可删除且无损")

],
[#text("只有完成可重建清单与测试后才如此承诺")

],
[#text("公开 Kimi repo 就是用户宿主")

],
[#text("已发现接口差异，以目标二进制实测裁决")

])

#text("最终交付定义：OPL 在独立夹具环境与 ADA 中都可工作；研究策略、候选评价和领域采用有各自身份；接班的 Kimi 会话可找到既有尝试、知道失败类型、展开证据并提出有区别的下一步。此时再扩展搜索规模，才能把更多算力变成可复用研究产出。")

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

#text("kimi.plugin.json")

#raw("e4619f8a3c99df17e149fad6b621c6e46d40a735591698f4f8b285d566d8a076", block: true)

#text("skills/opl-entry/SKILL.md")

#raw("22689ab0d60234b7779ed0fe0544d8183f969d0f23080aadea6bede60dee75a9", block: true)

#text("skills/opl-evolve/SKILL.md")

#raw("ddc8c3822085830f4ccd1f27a72afed10f7b51b20e246aec58b69e1aea1b50fd", block: true)

#text("lib/opl_evolve.py")

#raw("0fb3f0e5d7da7381a435015cb024edf435296fd2a53601f6ee7658a351f5df8a", block: true)

#text("lib/opl_ledger.py")

#raw("d397febbb34a94b73b8953e3853e3ed2e7e2089fa076c5b901681f22148a453a", block: true)

#text("lib/opl_sandbox.py")

#raw("0bda9ae56d7477007f3b65f37e6abcef4819190c5c5fee536ceb48edecdc6f54", block: true)

#text("bin/opl-evolve-suggest")

#raw("87eaaf57bc5c44b0414bf538402db0fb16662e09d1ff37c43abfdc3d4928d8c2", block: true)

#text("验证范围：本次执行 OPL suggest 过滤回退的临时库微型复现；未运行完整项目回归、Temporal 服务、Kimi 模型任务或本地 BESS 数据。本工程计划的 PDF 已从对应 Typst 源编译并做版面检查；文档可编译不代表软件实现已通过。")

