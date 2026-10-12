# EarlyEval 接入调研(2026-10-12)

**状态:调研完成,未做任何实现**(纯只读研究 + 两项本机实测,零 API 花费)。目的(用户原话):「研究 inphotoo/earlyeval 在本项目中的接入方法,只做调研不实现,目的是**组合优化时间-成本-成功率**」。

## 0. 对象与版本钉扎

- **仓库**:`https://github.com/inphotoo/earlyeval` @ `7fd1a8e`("Build the smoke fixture from real SWE-bench Verified results",main HEAD,浅克隆 30 深);MIT license;发行自述 "This is a **code-only release**"。
- **论文**:arXiv **`2609.02783`** *v1*(published 2026-09-02 = updated 2026-09-02,单版本;`comments` = "Code and data available at https://github.com/inphotoo/earlyeval",无修订/撤回类词)。标题:*EarlyEval: Cheaper Agent Evaluation via Early Outcome Prediction*。作者机构:SJTU/SMU/ECNU(见 CITATION.cff)。
- **引用纪律**(全文):〔论文原话〕= 逐字引;〔仓库〕= 读码/文档核实的仓库行为;〔实测〕= 本机亲自跑出;〔判断〕= 我方设计与判断。快照:`harbor-runs/refs/earlyeval-arxiv.xml`;克隆与探针产物见 §5。

## 1. 机制(读码 + 实测,全部 pin 到上述 commit)

### 1.1 论文原话(abstract,v1,逐字)

> "...we introduce early outcome prediction, a complementary axis of efficiency that instead cuts cost within each task. Our key insight is that an agent's final outcome is often evident from its intermediate behavior well before execution completes. We instantiate this idea in EarlyEval, a lightweight framework that trains a pair of LightGBM success and failure classifiers over behavioral, textual, and reference-solution features, and halts an agent run the moment either classifier crosses a calibrated confidence threshold, adding negligible per-step overhead. Across three benchmarks, SWE-bench Verified, TerminalBench, and Toolathlon, EarlyEval can eliminate 13%-26% of agent steps and up to 44.1% input tokens and 29.4% output tokens at 89%-97% prediction accuracy, while perturbing per-agent resolve rates by only one to two percentage points on average."

另一句定位:〔论文原话〕"Prior efforts, centered on benchmark distillation, reduce the number of evaluation tasks but leave the cost of executing each retained task untouched." ⇒ EarlyEval 的轴 = **不动任务集,砍单个任务内的执行尾部**;与本项目"短化任务集"方向正交,可叠加。

### 1.2 决策引擎〔仓库〕

- `policies/safe_stop.py::decide_dual`:逐轨迹按 `prefix_step_idx` 扫描;success 头 `p₊≥s` 或 failure 头 `p₋≥f` 即停;双头同越→按阈值余量取方向;`consecutive=k` 连续确认防单点突刺;`min_step` 设最早可停步。
- 预设 `current_safe_stop`(configs/policy_presets.yaml):`I_LightGBM_Dense_AF` / `calibrated` / dual / `s=f=0.95` / `min_step=0` / `k=1`。
- 记账(`apply_policy`):coverage、decision accuracy、双头 precision、**adjusted resolve rate**(被停者按预测计:预测成功一律计 resolved;未停者按原标签)、Δpp=原率−调整率、saved steps=决策步之后的前缀数。⇒ **"省多少步 / 偏多少点"是一等公民输出**,正是时间-成本-成功率的兑换账。

### 1.3 输入契约〔仓库〕

- 轨迹契约 `TrajectoryRecord`:`benchmark, instance_id, traj_id, model_id, resolved, messages[{role,content,tools,observation}], patch, metadata`。
- 训练前缀表列契约(configs/earlyeval.yaml `required_columns`):`task_prompt_text, prefix_action_text, prefix_feedback_text, last_action_text, last_feedback_text, prefix_thought_text, last_thought_text, n_steps_total_for_weighting`(+可选 `gold_has_answer`=参考族)。
- 预测表契约(策略应用所必需列):`traj_id, label, prefix_step_idx, prob_cal_safe_success__<P>, prob_cal_safe_failure__<P>`;CLI:`policy apply --preset current_safe_stop --predictions <path> --output-dir <dir>`。
- 特征族:behavioral(活动计数/最后步/事件计时/工作节奏/错误与测试状态,~115 维)+ textual(TF-IDF→SVD 分块)+ reference(可选);〔仓库〕README FAQ:无参考基准时**失败头单独更强**("Failure signals — stalling, repeated errors, unchanging feedback — are intrinsic to the trajectory and transfer well")。

### 1.4 发行边界〔仓库,重要〕

- **训练器与特征工程未随发行**:`models/dual_head_lightgbm.py` 与 `core/prefix.py` 均委托外部 "answer-aware source module root"(路径由 configs/paths 指);feature engineer pickle、前缀表、数据、模型全为 output,不提交。⇒ **发行可独立跑的是:契约 normalize、策略应用/记账、报表**;训练路径需自备部件。
- 冒烟夹具的概率列是演示曲线,examples/README 原话:**"Do not read them as measurements, cite them, or compare them against the paper."**

### 1.5 本机实测(2026-10-12,零 API 花费)〔实测〕

1. **策略引擎 smoke 通过**:`refs/ee-venv`(仅 pandas+pyyaml)下 `python -m earlyeval.cli pipeline current-safe-stop --mode smoke` → RC=0,产出 4 件(policy_decisions/summary/per_agent + metadata);9 条夹具轨迹:coverage 66.7%(6/9)、decision accuracy 100%、省 88/269=32.7% 步(此三数字只证"引擎可跑",概率列为演示曲线,不作测量引用)。
2. **我方转录→契约映射可行**:取 w7 b 侧真实 chat.jsonl 全量(370 事件)构造 generic 记录 → 57 条 assistant 步("应答周期"=assistant 消息+随后工具结果) → `data normalize --benchmark generic` → audit = `1 轨迹 / 1 实例 / 1 模型 / 0 空消息` ⇒ 步骤粒度与该契约直接同构。

## 2. 本项目接入面(设计,未实现)

### 2.1 可映射的现状资产

| 契约位 | 本项目来源 |
|---|---|
| 步 / prefix | 应答周期(chat.jsonl;与 traj_index 行模型、viz 滑块粒度同构) |
| task_prompt_text | `prompt-a.txt / prompt-b.txt`(含 front-phase 段) |
| prefix_action / last_action | 工具调用序列(含 git 提交/board/等待原语) |
| prefix_feedback / last_feedback | 工具结果(含错误、测试输出、门拒绝文本) |
| prefix_thought / last_thought | thinking 块(deepseek/qwen 双侧全场皆有) |
| label | ①任务判分(tumor annotation、microarch 三判据)②协议终态(NORMAL/ABNORMAL/exit)③结构门/恢复标记(可组合) |
| model_id | 侧模型(deepseek-flash-max、qwen3.8-flash-xhigh)×侧角色 |
| 成本/时间 | metrics.py(USD/credits/墙钟)+ OTel 逐步遥测 + SESSION_WALL |

### 2.2 映射决策(待裁的设计点,先记录)

- `traj_id` = `<run>::<side>`;`instance_id` = 任务族(tumor-immune-interface / microarch-modeling / walkthrough)。
- label 语义:pair 级结果**广播给两侧** vs 单侧职责完成度——w7 已证单侧 rc 与对侧强耦合(一侧死→对侧 abort),建议初期用 pair 级 + 单侧职责旗标做辅助标签〔判断〕。
- 参考族(gold):verifier 侧答案(hidden_cases、annotation key)在运行时对 agent 不可见,入在线特征=泄漏;**离线事后变体**可另做〔判断〕。

### 2.3 双体(H2)耦合风险〔判断〕

- 单侧早停改变对侧协议条件(wait_peer 停摆判定、merge duty、收口)——w7 的 a 死即例。⇒ 早停必须**配对级**(任一头触发→成对停)或与既有 stop/abort 语义融合(触发方写 `earlystop-<side>`+理由,收口照走 recover 职责)。
- **轨迹=研究对象的条件跑**(w6n/w6r 类协议结构实验)不能早停(早停改变被测量对象);早停只适用**答题面为主**的跑(tumor/microarch 的解题相),或以**专门新条件臂**的形式出现,不与既有条件混淆。
- 与我们已有词汇区分:现有 `peer-stalled` 早停(spec E1)= **活性阀门**(对侧死/停摆);EarlyEval = **结果预测阀门**(轨迹前缀→最终结果)。两者是**组合**关系,不互相替代。

## 3. 组合优化:时间-成本-成功率(设计)

### 3.1 兑换旋钮

- 阈值 `(s,f)` 即显式旋钮:〔仓库〕README 扫参表 0.75→省 63.4% 步、Δ4.1pp;0.90→省 42.7%、Δ2.3pp;0.95→省 26.0%、Δ1.1pp(均为其自测口径,**我方未复核**)。目标函数"以可控的成功率偏差预算买时间与成本"。
- 我方成本结构使然:长尾(上下文膨胀)每步最贵 ⇒ 输入 token 省幅 ≥ 步数省幅(论文同断言,头部各基准一致)〔论文原话见 §1.1 / 仓库表〕。

### 3.2 分层控制器(与既有机制组合)

```
L0 质量阀:gate/refs(提交级,已运行)      —— 保"不烂尾"
L1 活性阀:wait_peer 停摆×3窗/会话墙(已运行) —— 保"不傻等"
L2 结果预测阀:EarlyEval 式前缀预测(候选) —— 省"注定结局的尾巴"
L3 收口阀:recover 职责审计+受限唤醒(已运行) —— 保"结构终态"
```

优化目标:时间↓(截尾 + 槽位早释放)、成本↓(tail 即 token)、成功率=受控(偏差预算内,冻结件仍只用全程跑)。

### 3.3 预算分配器(wave 调度)

w6-4×2 已示范 pilot→wave×4 的并发编排;接入早期信号后:pilot 的末段预测分布 → 决定后续复制数与臂重分配("组合优化"的 portfolio 面)。输入=早期信号,输出=按预算的臂选择〔判断,未实现〕。

### 3.4 路线(仅调研结论)

- **M1 契约层数据准备**(零 API 成本):把历史双侧转录+标签批量过 `normalize` 契约存档 ⇒ 为任何未来预测源备料;同时喂 viz/stats(增益复用)。
- **M2 离线策略评估**:一旦有概率源(任务族内训练/跨族迁移;失败头优先),用 `policy apply` 记账在真实跑上算"若在步 k 停"的省/偏账。**冷启动诚实评估**:现存量级为双侧转录合计 ~40 条(walkthrough 系为主;tumor 4、microarch 4,族内 n 极小),远低于可训练量;〔论文原话〕"it does not apply to the first-ever evaluation of a brand-new benchmark"(无历史跑的基准不适用)⇒ **先数据、不先模型**。
- **M3 在线**(远期):钩点=应答周期边界;必须遵守 **60s 钩子墙**(项目记忆 `qwen-code-pretooluse-60s-wall`);配对级 halt;标记 `early_stopped` 与预测值,冻结 verdict 明示模式。
- **M4 调度**:§3.3 的分配器。

## 4. 风险与开放问题

- 任务族差异:其基准=代码/CLI 任务;本项目=科学任务(tumor 注释、microarch 回归),特征可移植性**未验**。
- 训练器/特征工程不在发行内 ⇒ 自研或等上游;冒烟概率列不可当测量。
- 早停值**禁入**冻结产物(verdict/spec/对账),1-2pp 系统偏差是其自述。
- harbor 判分在跑后链路,online halt 与判分/采集顺序需另行设计(未做)。

## 5. 验证范围声明

- **已核**:repo 存在/HEAD(7fd1a8e)/MIT;论文编号、标题、**版本 v1**、comments 字段(无修订旗;`local2gpt/check_citations.py` 复核 1 编号/0 MULTI-VERSION/0 COMMENT-FLAG);本机两项实测(§1.5);契约字段(读码,pin 7fd1a8e)。
- **未核**:论文与 README 中**一切数字**(未复现);训练/特征/在线通路(发行不含或未跑)。
- **产物索引**:克隆 `harbor-runs/refs/earlyeval/`;arXiv 快照 `harbor-runs/refs/earlyeval-arxiv.xml`;venv `harbor-runs/refs/ee-venv/`;smoke 输出 `refs/earlyeval/outputs/current_safe_stop_smoke/`;generic 探针 `/tmp/ee_probe/`。
