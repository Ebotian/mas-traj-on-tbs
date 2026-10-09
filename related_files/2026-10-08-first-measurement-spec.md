<!-- 2026-10-08 由本会话整理。依据:第 7 轮的状态级答复(先验证仪器)、第 8 轮的更正(试跑指向最终评分器)、
     第 9 轮的可借件(TwinRouterBench 双轨、share-matched 对照),以及项目约束(墙钟是约束;钱=meter-before-money)。
     这是**规格**,不是结论:跑完必须把结果写成反转段或冲突行,由用户裁定是否进登记册。 -->

# 首个测量规格(2026-10-08)

## 0. 为什么是这两个测量,而不是先比 harness

- **第 7 轮状态级答复**:先验证**仪器** —— 判据能不能拒绝假进展;比多个 harness 之前先做它。
- **第 8 轮更正**:试跑指向**最终评分器**与宿主的"完成/继续"决策;理由**不是**"仪器不灵则所有比较都不可读"(运行中验证器差,仍可由独立可靠的最终评分器读出退化)。
- **第 9 轮可借件**:`TwinRouterBench 2605.18859v4` 的**双轨**(静态轨:给前缀判该步需要什么档位;动态轨:真执行、按是否解决 + 实际支出评分)+ **share-matched 对照**;`2607.08665v3` 把"有恢复机会 / 有动作差异支持 / 能事前选对"**分开检验**。
- **项目约束**:墙钟是约束;钱是 `m` 上的派生量(三量**分报**);kill chain 让 **RQ1 先行**。

## 1. M0 · 判据能否拒绝假进展(仪器检查,先做这一个)

**★ 两源合流(2026-10-08)**:包会话第 11 轮(构想着自己问的)换回的答复,**独立**把「方向 1」排在第一位,理由与本规格一致 ——
「这一步会告诉我们,当前瓶颈究竟是**判据、接线还是生成能力**」。它还给 M0 补了三条我们没写的:
①**三个结果标签分开**(产物正确 / 相对基线改善 / 任务完成),避免一个 `pass` 同时承担三种意思;
②除**误接受**外还要测**误拒绝**与**自述诱导**;
③交付物定为**一个启动命令 + 一组固定样本 + 一张逐运行结果表**,并保存失败、超时、原始计量与产物哈希。

**冻结**:任务 · 环境 · 预算(token 与墙钟)**· 判据**。

**注入三类产物**(同一任务、同一环境):

| # | 产物 | 期望 |
|---|---|---|
| ① | **已知正确**(真修好了) | 判据接受 |
| ② | **无改善**(等价重构,行为不变) | 识别为"无改善",而不是当成功 |
| ③ | **错误但自称完成**(破坏测试却声明完成) | **判据拒绝** |

**读的数**:对 ③ 的**误接受率**(头号数字);对 ② 是否区分;对 ① 是否接受。**保留**:每次运行的原始计量(token / 墙钟 / 工具调用次数)。

**杀死条件**:若 ③ 被接受 ⇒ **仪器不可判别** ⇒ 先修仪器,**任何比较都不做**。
**要证伪的预测**:③ 的误接受率**非零**(即:现有判据会把"自称完成"当真)。

## 2. M1 · share-matched 对照(只在 M0 通过后)

两臂**动作份额相同**:（i）任务匹配路由;（ii）**内容无关**(把同一份额打乱分配到任务上);另加（iii）单模型基线(全弱 / 全强)。

**分报**:成功率 · 真实费用 · 墙钟 —— 先分报,**再**讨论如何合成。
**双轨**:先静态(给某一步之前可见的前缀,判该步需要什么档位),再动态(真执行并计费)。
**杀死条件**:若 share-matched == task-matched ⇒ 路由**不含任务针对性信息**,任何增益只是"多用了强模型"。

## 2b. M2 · 机制比较(构想着已在包会话里做出 v2 协议)

他的第 13–17 轮把方案推进到 **v2**:三臂(**MasRouter `2502.11133v1`** / **EvoRoute `2601.02695v1`** / 接入千问决策模型),
四问(动态选模 vs 固定配置;角色与协作结构是否另有价值;专门决策模型是否改善选模;收益能否覆盖训练与在线开销),
三档数据集(接线 HumanEval+/MBPP+ ≈40 题 → 主实验 DS-1000 → 迁移 SWE-bench Verified 子集),**第 17 轮后修正为 LHTB 优先**。
两条我们**必须先钉住**的边界(来自该协议自身与我方复核):
- 它自警:「完整 MasRouter 与完整 EvoRoute 的比较属于**系统比较**,不能解释成任务级与逐步路由的纯粹差异」⇒ **M1 的 share-matched 对照正是解这条的**;
- 顺序:**M0 → M1 → M2**;M2 直接开跑等于在没有可读仪器的情况下比较机制,正是第 7 轮状态级答复点出的自欺。

## 3. 宿主与接线(第一个事实已确认)

- **首选宿主 qwen-code**(第 9 轮之外的理由见 `04_EXISTING_AGENTS.md`:接受外部 PR + 自跑 SWE-bench 回归)。
- **已确认的接线事实**:存在无头入口 **`-p/--prompt`**(另有 `--approval-mode`、`--model`);完成判据在 `packages/core/src/goals/goal-verifier.ts`(模型判决 + 受约束 JSON);计量在 usage/telemetry 侧。
- **接线探针(按此顺序,一行一行做)**:
  1. ~~用 `-p` 跑一个固定产物,确认能无头驱动~~ **已完成(2026-10-08)**:`qwen -p "Reply with exactly: ok"` → stdout `ok`、exit 0、干净无 TUI。**同一跑还暴露一条必须冻结的默认**:无头默认 **`--yolo` + 无沙盒**(它自己打印警告),⇒ 试验必须显式钉 `--sandbox` 与 approval mode,否则不可复现。
  2. **计量通道已找到**:`--telemetry-outfile <file>`(「Redirect all telemetry output to the specified file」—— token/用量从这里出);另有 `--telemetry-target local|gcp`、`--telemetry-log-prompts`;沙盒另可用 `-s/--sandbox`(true/false/docker/podman/sandbox-exec)与 `qwen sandbox <cmd>`(可先探后端)。
  3. **仍需截获**:完成判据的调用与返回(`packages/core/src/goals/goal-verifier.ts` 的那次 side-query 请求/响应)。
  4. 写最小补丁:把三量 + 判据记录接到一次可重复的跑批上。
- **不变量**:**不花额度的先做完**(读码、写探针);**第一次真跑只跑一个最小任务**,并在跑之前把预算写死。

## 4. 与登记册的关系(跑完后才动)

- M0 对应冲突 **`bench-validity`**(判据有效性)与 **C40**(三条件只是项目约束,不是普遍定理)。
- M1 对应 **D33**(society)与 **C26/C35**(多模型的条件优势、质量估计能力)。
- 结果若推翻本项目某条主张 ⇒ 写成反转段;若暴露新矛盾 ⇒ 写成冲突行。**两件都要用户裁定。**

## 5. 数据集候选:Terminal-Bench-Science(2026-10-09,构想着指出;我只读看过本地 checkout)

**来源**:`harbor-framework/terminal-bench-science`(科学工作流的终端 agent 评测);本地 checkout `/home/ebt/terminal-bench-science`,HEAD `39e4923`,工作树干净。
**我实测的事实**(不是转述):`tasks/` 下 **5 个领域 × 4 个子域、约 70 个 `task.toml`**;每个任务目录 = `instruction.md · environment · solution · tests · task.toml`(+`authoring`)。
以 `tasks/earth-sciences/geosciences/stereo-dem-icesat2/` 为例:`tests/` 里有 `test.sh` + `test_outputs.py`,并**把留出数据烘进 verifier**(`holdout_icesat2.parquet`)—— **agent 看不到**;`task.toml` 的 `artifacts = [...]` 是 **agent→verifier 的接口**;`[verifier] environment_mode = "separate"`、`network_mode = "no-network"`(verifier 在干净容器里**只拿到 artifacts + `tests/Dockerfile` 烘进去的东西**);资源信封原生:`[environment] cpus=4 / memory_mb=16384 / storage_mb=30720 / build_timeout_sec=3600`。

**★ 更正(2026-10-09;我先前写反了,致预算差 48 倍)**:`[agent] timeout_sec` 全 70 任务**一律 28800(8 h)**;`[verifier] timeout_sec` 值域 **120–12000、中位 600**(我自己按段头重读并全量统计)。**错因**:我按 grep 输出的**邻近行**归属,没读段头 —— 教训与此前"读版本"同类:**归属要读段头,不读邻行**。
**`tests/` 命名不统一**(我实测):`test.sh` **70**、`test_outputs.py` **37**、`holdout_*` **20** ⇒ 不可按单一样本外推。
**许可 Apache-2.0**;带 **canary GUID**(防污染)。

### 为什么它对我们价值高(三条)

1. **它把我们 E1 要建的判据形状**已经标准化了:**在容器外、由代码执行、带留出数据、只经 `artifacts` 与 agent 交互**。
   ⇒ E1 的"判据控制入账"可以直接落在这一格式上,不必自造。
2. **"冻结环境与预算"有原生表示**:cpus/memory/storage + 两级 timeout ⇒ M0 的冻结清单不需自定义。
3. **跨领域 + 专家策展**(5 领域 20 子域,科学工作流):正是 LHTB 被看重的"跨任务类型 + 长程"性质,而且**落在本项目的领域**(科研工作流)。

### 与 v2 数据集选择的关系

v2 的三档(接线 HumanEval+/MBPP+ → 主实验 DS-1000 → 迁移 SWE-bench 子集)是**代码/函数级**的;第 17 轮已把优先级修正为 **LHTB 优先**(跨任务类型 + 长程)。
⇒ 本数据集与 LHTB 同类但**多出两件**:①判据与留出数据**已外置**(我们要的正是这个);②**科学领域**(与项目同域)。**建议:把它列为 M0 的判据来源候选,并与 LHTB 比较后再定**(LHTB 的判据形态待核)。

### ★ 该仓**已有**的现成机制:正好是 E1 的三类产物(2026-10-09,与 `terminal-bench-science-b1` 会话通信后逐条复核)

| E1 要的东西 | 该仓的对应物 | 我的核验 |
|---|---|---|
| ① **已知正确** | `/validate` 的 oracle 臂(reward 1.0) | 转述(其机制说明见下条) |
| ② **无改善** | `/validate` 的 nop 臂(reward 0.0) | 同上 |
| ③ **错误但自称完成** | `/cheat` 试验线;`ci_checks/test-tasks/`(**我数 85 个条目**)的 fail-* 回归任务,每个 pin 一个检查的**抓取率**(即误接受率) | 条目数与目录都已实测 |
| **判据输出如何被消费** | `ci_checks/check-binary-reward.py`:强制 reward 恰为 0 或 1 —— 因为 harbor 按 `reward >= 1.0` 判过,**分数型 reward 只是"读起来像通过"**,其部分信用会被下游静默丢弃;且 **`reward.json` 优先于 `reward.txt`** | **已读其文档头原文** |
| **判据的攻击面词表** | `rubrics/trial-analysis.toml`(含 `verifier_correctness` · `boundary_fairness` · **`unearned_credit`**…) | 已见 7 条 `[[criteria]]`(其说 8 条) |

⇒ **E1 不必从零造夹具**:① ② 由 `/validate` 的两点给出,③ 有 `test-tasks` 的 fail-* 线;**而 `check-binary-reward.py` 直接给出"入账"的硬约束**(二值),这比我们自己定的"控制入账"更具体。

**三处"文档有、实际没有"(已核,避免踩)**:`TASK_IMPLEMENTATION_RUBRIC.toml` **不存在**(AGENTS.md 的 Repo Structure 列着它);`docs/EXAMPLES.md` **0 字节**;`CLAUDE.md` 是指向 `AGENTS.md` 的**符号链接**(不是第二份文件)。
**浅克隆警告**(转述 + 可核):本地 clone 仅 2 个 commit(grafted)、**未配置 `template` 远端** ⇒ 文档里的 `git fetch template && git merge template/main` **在此 clone 里跑不了**。

### 待核(已向该仓的会话发问,2026-10-09)

①它当前状态(clone 到哪、跑没跑过 harbor runner);②**最便宜**的任务是哪个 slug、其 `tests/` 是否**纯确定性**(不含 LLM judge);③`lite/` 只有一个 README —— 上游是否有更小可运行集;④能否**只替换/包裹 verifier**(保留任务与 env)而不必按它的 `test.sh` 跑。
**边界**:以上均为**我读仓库所得**;这套任务的**实际可运行性**(harbor runner、容器、8 h verifier)我**未实测**。
