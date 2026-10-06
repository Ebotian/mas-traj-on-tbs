# Agent Engineering Science：源码、测量与可辨识性独立审查报告（第二轮）

**日期**：2026-09-24
**对象**：本项目上一轮独立审查及其后续修订稿，尤其是 SILO-BENCH、Autonomous Physics Lab（APL）、“信息处理链—认识队列—决策充分状态—四对象动力学”。
**意见**：重大修改后可作为研究纲领。当前尚不能作为经验本构律或已辨识的状态空间理论。

## 摘要与审查方法

审查以可复查的 GitHub 默认分支快照为准：SILO-BENCH `e74127782ed1c42fff474249961f022c063d76f2`；APL `60f47e5ff7dae4035a8431448601fd60087b2062`。用 GitHub 文件读取接口逐一核对任务 JSON、核心评估器、汇总器、APL 升级协议与 JSON Schema；对论文内容查 ACL Anthology 原始 PDF；数学命题以反例或明确假设审查。**没有重跑原论文的大模型实验；下面涉及论文图表是否受到源码问题影响的结论均标为待核**。

最重要的新发现：先前审查沿用了 SILO 论文关于“Level III 每个 Agent 输出完整全局答案”的原文；但该仓库的 `III-21_n2.json` 明确规定各 Agent 只提交**自己的排序分段**，`II-11_n2.json` 亦只提交各自的前缀和分段，评分器比较 `per_agent_values[agent_id]`。这不仅是“评分苛刻”的问题，而是**论文复杂度解释与公开实例间的任务规格不一致**。另有核心评估器和独立汇总器的 SR 分母不同；部分正确率存在可构造的假阳性。必须对历史报告修正。

## 1. 可核验事实：论文、任务 JSON、代码

| 问题     | 独立核验及位置                                                                                                                                                                                                                                       | 审查判断                                                                                                                                                                                        |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 成功率定义  | `src/utils/metrics.py:45–94`：比较 `per_agent_values[aid]`，正确数除以 `len(per_agent)`；`src/engine.py:457–523` 将未提交者补为 `None`，并以 `success_rate == 1.0` 给出单次 task 布尔成功。                                                                                | 源码支持逐 Agent 正确率及“全员正确”的实例成功准则；不支持把此直接等同“全员完整全局答案”。                                                                                                                                          |
| 任务输出规格 | `benchmarks/II-11_n2.json` 写“Each agent submits THEIR portion”；`III-21_n2.json` 写“Each agent submits their sorted portion”；两者 `output_type=distributed`。                                                                                      | 公开 Level II、Level III 样例为**分段答案**。论文 §3.2 说 Level III 的 O(N²) 一端由“every agent must output the complete global answer”施加，与该公开排序实例字面冲突。不能凭此证明论文运行时用的正是这一 commit；需要锁定论文所用 commit、生成器版本、原始运行结果。 |
| 汇总指标口径 | `src/analyze.py:128–132` 从 `results.json` 计算 `correct / len(submissions)`；核心函数却是 `correct / num_agents`。`engine.evaluate` 补 `None` 进入记录，因此标准流程二者可能一致；缺记录、第三方结果或错误格式时可能不一致。                                                                    | **潜在口径漂移，不可断言论文表格已错。** 合约测试须覆盖 0、部分、完整提交，并强制汇总器优先读取 `metrics.S_success_rate`，遇到不一致报警。                                                                                                       |
| 部分正确率  | `src/utils/metrics.py:96–212`：Level I 容差内计满分；Level II `zip(expected,actual)` 同位计数除以完整期望长度；Level III 以真实排序序列值到位置的字典映射后求 LIS，再除以完整期望长度。                                                                                                         | `P−S` 是按任务定义的“部分得分超过严格准确率”，**不能单凭这两个数定位取得、送达还是整合失败**。跨 Level 的 `P` 也不是统一的尺度。                                                                                                                |
| APL 状态 | `docs/result-promotion-scorecard.md` 将评分 `PASS/PARTIAL/FAIL/NOT_APPLICABLE` 与结论 `SANDBOX_FOLLOWUP_ONLY` 等分开；`docs/result-promotion-protocol.md` 和 `claim.schema.json` 将 result verdict、claim status、review tier 与 validation independence 分开。 | 仓库证明有可执行的**多轴证据治理协议**；“Sandbox→RESULT→ValidatedResult→CLAIM→KNOW”是解释性概括，不是简单单调的单轴状态机。                                                                                                       |

### 1.1 两个确定性的评分反例

以 Level III 排序期望片段 `[1,2,3]` 为例，提交 `[1,2,3,999]`，源码的字典过滤忽略 `999`，位置 LIS 长度 3，得 `q=1`，而严格比较不相等、`S=0`。这代表即使 **P=1、S=0** 也可能只是冗余错误输出，并非分布式推理整合的失败。期望和提交含重复值时，`expected_pos={v:i}` 还会覆盖旧位置，损失重复项信息。Level II 期望 `[1,2,3]`，提交 `[1,2]`，`zip` 给 `q=2/3`，虽已发生截断。上述均是依据已读取的函数直接代入，不是原论文真实运行结果。

### 1.2 分母和系统规模的测量效应

若每个 Agent 的最终输出以概率 `q` 独立正确，则任务全员正确率为 `q^N`，即便单 Agent 正确率不随 N 变：例如 `q=.99,N=100` 时为约 `0.366`。因此要区分三条曲线：(i) 平均 Agent 正确率，(ii) 全员正确率，(iii) 达到任务验收所需的系统级成功率。该独立模型是说明指标行为的数学例子，不是解释 SILO 实验实际成因。实际相关性、规模增大的输入量和任务难度都可能另外改变曲线。论文中的“Level III 在 N≥50 为 0”需说明究竟对应哪条曲线与何种统计单元。

**对上一轮审查的正式更正**：上一轮据论文文字把全员完整全局答案当作公开排序实例的实际要求，此项表述过度确定。源代码样例要求全员**各自正确提交对应分段**；论文全局答案表述与代码版本关系尚需原始运行证据澄清。

## 2. 信息链：从形象分解到可识别的因果对象

拟议 `Acquire→Transmit→Recover→Understand→Integrate→Verify→Decide` 是重要的**检查清单**，不能直接视为一条 Markov 串联系统。证据可能在 Verification 后重新取得；不同证据子集能实现同一正确行动；部分成功事件不互相嵌套。若定义 `F_k` 为同一预先指定证据单元顺序通过的事件，链式概率恒等式为

`Pr(∩_{k=1}^7 F_k)=Pr(F_1)×∏_{k=2}^7 Pr(F_k|F_1,…,F_{k-1})`。

但它**不是**任务成功率公式，除非“七阶段均通过”等价于成功；相关概率也不是可从最终 `P,S` 逆推的参数。失败可以同时发生于送达与解释阶段；把失败七选一会让机制标签随诊断顺序改变。

建议预先定义任务条件 `T`、必要证据族 `𝓔*(T)`、消息时间戳、接收暴露、独立理解小测、聚合中间输出与验收谓词。冻结上游消息之后作分阶段的随机救援实验：`do(deliver)`, `do(recover)`, `do(provide_parsed_facts)`, `do(provide_joined_state)`，以配对任务的 `ΔJ_k`（含救援成本）作为**阶段可干预性**指标。注意该 `ΔJ_k` 是政策干预效应，不是从观测 trace 估计的“天然失败比例”；同一中间修复可能掩盖上下游交互。

## 3. 认识队列：区分排队稳定性、逐出与实际收益

方程 `Q_{t+1}=[Q_t+A_t-S_t]^+` 要求 A、S 同单位、服务不能超过可用积压，并应计入丢弃/超时；适合的操作定义是“待核验、已标识且未过期的原子证据请求”。若成本计量改为 tokens 或命题难度，则应加入 job size；不同请求不能靠简单计数直接比较。

负边际观测价值有一个**可构造机制**：工作集容量 `W=1`，当前唯一必要证据 `e*` 已驻留，新到达无关证据 `z` 在强制 FIFO 下逐出 `e*` 且不可检索，收益由 1 降至 0。若控制器可忽略 `z` 或无成本回取 `e*`，该负效应消失。故下一阶段要操作化 `Admission policy`、检索时延、逐出规则、时效衰减与工具调用费用，而非宣称 `R_O/R_I>1` 导致负效用。

APL 的 claim 管理可视为类似排队系统中的 qualification job，但一份 falsification 往往**提高**未来决策质量；“backlog 变短/claim 变多”均不能充当科学质量的通用目标。

## 4. 决策充分状态：精确定义、预算与预测

给定任务分布 `𝓓`、历史 H、编码器 φ、策略集合 `Π` 和可计账执行规则，定义同预算最优损失 `R_B(φ)` 并估计 `Δ_B(φ)=R_B(φ)−R_B(Id)`。需要明确 full history 是否可以内部调用 φ：若能且成本规则一致，历史策略类包含压缩策略，`Δ_B≥0`；若完整历史占窗口或编码开销在两组不同，策略类不嵌套、差值可为负，此时应明确称“**系统等预算比较**”，避免误称“纯压缩信息损失”。

单步条件分布接近不足以保证长程；更稳妥的主张是：在指定有限 horizon H 和允许动作序列下，对未来观测与回报的预测分布保持距离 ≤ε，或直接在 held-out 策略类上以决策后悔约束。它是任务族相对且策略类相对的充分性，无法推出全球最小“Agent 状态”。PSR 已把状态视为对未来行动条件下观测的预测，这一历史理论应作为前驱，而不是将“预测充分性”写成新发明（Littman, Sutton, Singh, NeurIPS 2001）。

## 5. 错误图与四对象模型：可辨识性门槛

`Σ_ij=Cov(E_i,E_j)` 是观测到的二阶错误依赖，不是错误生成机制本身。共同题目难度、同一 shard 暴露及同一模型先验都可能同时改变通信与错误；简单回归 `G_E` 对 `G_C` 无因果解释。图是离散处理变量，`∂G_E/∂G_C` 未给扰动几何时没有一般定义；建议设定边随机化、消息负载随机化及可重复的处理 contrast。

即便完全记录 `(y_t,u_t)`，潜状态 `x_t=(E_t,I_t,D_t)` 的坐标仍有**重参数化不可辨识性**：对任意可逆 `ψ`，`x'_t=ψ(x_t)`，`F'=ψ∘F∘ψ⁻¹`、`h'=h∘ψ⁻¹`，得到完全一样的输出过程；Jacobian 也随坐标变换变化。即使理论能识别观测等价类，不能未锚定地宣称发现了物理唯一的四个状态量或“跨模型可迁移的 Jacobian”。因果表征的可辨识研究同样强调干预条件与模型假设（Varici et al., AISTATS 2024）。

提议将四对象明确分角色：`u_t` 为可设定的**输入**；`I_t` 为依任务定义的信息暴露/流动摘要；`D_t` 为由独立任务重复测得的错误依赖统计量；`E_t` 为带来源和证据等级的研究记录及有限工作集。`D_t` 作为依赖大量任务重复估计的**总体参数**，一般不能与单次任务时刻的 `E_t` 同等级视为可在线观测的状态。对外报告可辨识的预测函数 `Pr(Y_{t+h}|history, do(u))` 与操作上定义的响应差分，之后再尝试低维潜态压缩。

APL 的 schema 支持这种多轴建模：result 的 verdict、review tier、验证元数据，与 claim 的 DRAFT/SUPPORTED/REFUTED/SUPERSEDED 是不同字段；负结果是可以保存且有价值的记录。APL 协议还规定“agent validation”可为同账户不同工具等，并非总等同独立外部复现。**这是证据治理系统的实现案例，而不是 Agent 工程学动力学已成立的实证。**

## 6. 数学命题审查矩阵

| 原稿关系                       | 等级           | 使其可检验所需限定                       |
| -------------------------- | ------------ | ------------------------------- |
| `N_eff=N/[1+(N−1)ρ]`       | 方差恒等式；非多数票规律 | 同方差等相关 Y_i，估计其均值；联合分布与融合器另报。    |
| `P−S = integration loss`   | 缺乏识别         | 需干预传输/解释/聚合，排除容差、截断和验证器影响。      |
| `R_O>R_I→negative utility` | 一般不成立        | 限定强制摄入、容量置换、无法丢弃、服务成本与目标函数。     |
| `G_C→G_E`                  | 潜在因果命题       | 随机化通信边/暴露，保持任务难度和证据相关性，重复采样估计。  |
| `DSS Pareto frontier`      | 合理定义框架       | 定义执行预算与策略类、编码精度、动态预测/长程后悔。      |
| `x_{t+1}=F(x_t,u_t,w_t)`   | 有用的建模模板      | 指定时钟、状态的可观测指标、扰动与干预；仅能辨识到坐标等价类。 |

## 7. 可证伪的预注册研究设计

**主问题**：在消息内容和成本固定时，增强聚合机制能否消除 SILO 类型任务里仅由送达无法解释的收益损失？

1. 在固定 commit 上重新生成和冻结可公开的 tasks/shards/ground truth；逐条核对公开 JSON 与论文叙述的任务输出契约，记录每种任务的 per-agent/global 判分函数及是否要求全员提交。
2. 采样模型、任务、协议和随机种子；设置 `N∈{2,5,10,20}`，任务实例做区组。系统性记录平均个体成功 `S_agent`、全员成功 `S_all`、端到端任务可用性 `S_task`、P、消息内容、到达、工具失败、每个 Agent 的中间解释与最终分段输出；报告前述指标的分母。
3. 冻结源 Agent 的原始输出，分别随机化 `T`: 消息送达原样/原样加可见索引；`I`: 同信息同预算弱/强聚合器；`V`: 不验证/盲化验证。设“仅收到证据”的操纵检查题，盲化真实标签。若无法冻结源输出，则报告处理改变上游行为、放弃纯阶段归因。
4. 主 estimand：`[E(J|do(T=1,I=1))−E(J|do(T=1,I=0))]−[E(J|do(T=0,I=1))−E(J|do(T=0,I=0))]`，即送达与聚合器交互，J 预先指定为“系统成功收益−归一化执行成本”。主效应和交互并报区组 bootstrap 或层级模型区间，不以 p 值单独解释机制。
5. 验证成功标准：重新算出的核心与汇总 SR 完全一致；两个部分正确率反例被测试捕获并给出修复后重算；主要交互在留出任务类别和第二模型上方向一致，且其区间不覆盖预设的实际无意义范围；对不迁移结果报告条件化规律，不宣称普适定律。
6. 报告预算与规模：先 2 个模型×至少 3 任务类×4 个 N×8 个随机化格；试点估计任务内变异后再做效能计算。由于全员成功在高 N 下可能天然极低，避免仅凭 `S_all` 估交互。

**三项阻断门槛**：① 公开任务契约与论文描述未能对齐；② 评分器与汇总器分母无法复核；③ 给不出不读取答案的证据理解/聚合中间指标。任一未通过都先停止关于“整合本构关系”的跨模型概括。

## 8. 最终学术意见

认可修订稿转向认识状态、信息流、错误依赖与元控制，其学术价值在于将下一阶段实验从“给框架起名”改为**明确干预、量化响应和检查可识别性**。否决三项强主张：(i) `P−S` 定量识别整合损失；(ii) SILO 公开排序实例均要求每人完整输出全局答案；(iii) 四潜状态及其 Jacobian 已自然确定且可直接跨模型迁移。推荐将主题定为“Agent systems 的任务条件机制辨识”，优先完成指标合约、冻结消息干预及版本一致性核查。该路线保留航空工程类比的实验精神，避免把模型坐标当作自然常数。

## 一手资料与复核路径

* SILO 论文，ACL 2026，§3.2–3.3、Figure 4、Table 3、Limitations：https://aclanthology.org/2026.acl-long.1354.pdf
* SILO `src/utils/metrics.py`，上述固定 commit：https://github.com/jwyjohn/acl26-silo-bench/blob/e74127782ed1c42fff474249961f022c063d76f2/src/utils/metrics.py
* SILO `src/engine.py`：https://github.com/jwyjohn/acl26-silo-bench/blob/e74127782ed1c42fff474249961f022c063d76f2/src/engine.py
* SILO `src/analyze.py`：https://github.com/jwyjohn/acl26-silo-bench/blob/e74127782ed1c42fff474249961f022c063d76f2/src/analyze.py
* SILO 分段任务：[II-11](https://github.com/jwyjohn/acl26-silo-bench/blob/e74127782ed1c42fff474249961f022c063d76f2/benchmarks/II-11_n2.json)、[III-21](https://github.com/jwyjohn/acl26-silo-bench/blob/e74127782ed1c42fff474249961f022c063d76f2/benchmarks/III-21_n2.json)
* APL：[协议](https://github.com/open-agent-science/autonomous-physics-lab/blob/60f47e5ff7dae4035a8431448601fd60087b2062/docs/result-promotion-protocol.md)、[评分卡](https://github.com/open-agent-science/autonomous-physics-lab/blob/60f47e5ff7dae4035a8431448601fd60087b2062/docs/result-promotion-scorecard.md)、[result schema](https://github.com/open-agent-science/autonomous-physics-lab/blob/60f47e5ff7dae4035a8431448601fd60087b2062/physics_lab/schemas/result.schema.json)、[claim schema](https://github.com/open-agent-science/autonomous-physics-lab/blob/60f47e5ff7dae4035a8431448601fd60087b2062/physics_lab/schemas/claim.schema.json)
* Littman, Sutton & Singh, *Predictive Representations of State*, NeurIPS 2001：https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf
* Varici et al., *General Identifiability and Achievability for Causal Representation Learning*, AISTATS 2024：https://proceedings.mlr.press/v238/varici24a.html

**边界**：未调用模型 API、未访问原论文私有运行记录；仅有仓库当前公开 commit 和论文 PDF，不能反推出论文生成图表时确切代码修订，也不能重新估计原论文的经验效应。
