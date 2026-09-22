# A1 实验契约 v1.0 审计意见

**审计对象**：《A1 实验契约 v1.0》（外部模型起草，含 D1–D7 与最终冻结对象）
**审计方**：本机研究项目（执行方）。本审计以**我方实测证据**为准绳，逐条对照契约的事实性声明与设计选择。
**回复方式**：请按本文件编号（B1–B3、M1–M4、m1–m3、Q1–Q5）逐条回应，一条一行；**拒绝我的某条时请给出反证或反例**，不要只给理由。§5 列出我明确同意的部分，请不要重开。

---

## 0. 总体判断

**框架我接受，可以落地，但需先解决 3 个阻塞项（B1–B3）与 4 个修正项（M1–M4）。**

- **接受的框架**：A1 = substrate 资格认定而非 H_A/H_O 显著性检验；不以算法分选 winner；`R=4` 声明为 qualification replication；block 随机化；`CampaignID` 绑定模型路线与工具策略；lexicographic 资格规则；`DEFERRED_NOT_EXCLUDED` 的第三方处置。
- **最关键的接受**：契约把"**身份不再由 runtime 自述**"（D7.2）提前到 A1 之前，并给出了正确的理由——**我方自建的 SimpleLoop 即使完全诚实，也可能因加载错误、旧文件、TOCTOU、适配器 bug 产生同一污染**。这比我方此前的"推迟到发布前"更正确，我接受修正。
- **最能体现专业性的一处**：正对照与 baseline **共享同一初始划分**，消掉了初始解差异这个混杂。
- **最强的一处认知**：T1 由**本地生成、只冻结 edge list**，同时压住 memorization 与"seed 不是数据"两个老问题。

---

## 1. 阻塞项（开工前必须解决）

### B1 — D7.1 与 D7.2 对 KAPSO 互相冲突（P0）

**契约的冲突**：D7.1 主张"先接 KAPSO"，理由是它的证据链最短（`E* → score → history → parent` 已验证）；D7.2 主张"A1 前把评测所有权移给 harness，runtime 只消费 Outcome"。

**为什么冲突**：KAPSO 的独特性正在于**分数记录由会话自己产生**——我方实测：实现会话在前台运行 `python kapso_evaluation/kapso_eval.py --fidelity full --fraction 1.0 --seed 1337`，再由 KAPSO 自己的 `manifest_of_record`（`registered_evaluation.py:52-102`）在 `generate_feedback` 里定分。一旦评测搬到 harness，**KAPSO 不再走它自己的注册化评测路径**——而 bridge 验证的恰恰是那条路径。

**后果**：D7.1 用来论证"选 KAPSO"的那份证据（两轮真实 campaign bridge），有**一半在 A1 中不再被行使**。若不声明，后续读者会把 bridge 当作 A1 的证据，而这在 `AID_KAPSO` 上是假的。

**请求的修法（二选一，并写进契约）**：

- **(A) 统一 harness 供给 outcome**（我与契约同侧）：所有臂由同一个 harness 供给分数，A1 因而定义为"**在给定分数供给之下比较搜索机制**"——这正是协议 §4.2.2 第一轮的既定约定（`F_r(E*) = scalar(E*)`），不是新发明。注入点走**我方适配层**（judge/feedback seam），不改 upstream（与 A4 相容）。同时在 `AID_KAPSO` 中**明写**："in-session 注册化评测在本阶段未行使；bridge 仅继承其选择部分的证据。"
- **(B) 保 KAPSO 自评**：接受其分数为 *attested* 而非 *measured*，并把它写成**声明的设计选择**（而不是未识别的混杂）。

**我的建议**：选 (A)。但请注意 (A) 的代价：D7.1 的论证因此变弱，选 KAPSO 的理由应改为"它的**选择机制**可观测性好"，而不是"它自己会算分"。

### B2 — 计量方案与我们的代理拓扑不相容（P0）

**契约要求**：`C_LLM` 由"mandatory model proxy usage ledger"作权威，并按 `CEq = N_miss + 0.02·N_cached + 4·N_output` 计量。

**实测不相容**：我方封闭拓扑的 HTTPS 路径是**CONNECT 隧道、不做 TLS 中间人**（这是刻意的安全设计）。在 CONNECT 之下代理只看到字节流，**无法解析 token，更无法解析 cache-hit**。按当前设计，`CEq` 事实上无法计量；而契约又明确"runtime 自报 telemetry 仅作诊断"，于是 `C_LLM` 无权威来源。

**请求的修法**：把计量前提**写进契约**为强制配置：

$$
\boxed{\text{CLI 的 }base\_url\text{ 必须指向代理的明文 }http\text{；}HTTPS\_PROXY\text{/CONNECT 不足以计量。}}
$$

由代理明文终结请求、再向上游发 TLS，从而读出 input/output/cached 字段（DeepSeek 两个协议面均返回这些字段）。我方已实测三个 CLI 均接受自定义 `base_url`（`claude` 经 `/anthropic`、`opencode`/`kilo` 经 OpenAI 兼容面）。这条也应进入 `AID_r`。

### B3 — 缺"天花板"，导致 saturation 无法判定、正对照没有上界（P0）

**契约的问题**：
1. D6 把 `TaskSaturatedAtBaseline` 列为任务级 NO-GO，但**冻结套件里没有任何 per-graph 参考上限**，因此"打满"无法检测。
2. `Δ_PC ≥ 0.03` 只有**下界**。若 `one_exchange` 一步吃掉大部分差距（Max-Cut 上不罕见），B0+ 就变成"注入一个几乎最优的东西，看还剩多少空间"——**通道测试变空洞**。
3. D3 的另外两个条件（`≥18/24` 改善、`Cut(p_i) ≥ Cut(b_i) ∀i`）**近乎同义反复**：`one_exchange` 只接受改进型交换并跑到局部最优，`Cut(p_i) ≥ Cut(b_i)` 本就必然成立（随机起点几乎不会是局部最优）。所以真正起作用的只有 Δ 的下界——而那正是缺上界的那一项。

**请求的修法**：
- 为**每个图**冻结一个**参考上限**（若干强启发式长时间运行的最好值；小规模可用精确解），明确标注为"参考值而非已证明最优"。
- 它同时提供三样东西：**饱和判据**、**PC 的上界 sanity**（例如要求 PC 后的剩余空间 ≥ 某比例，否则任务 NO-GO 或换套件）、以及 B0/B1 的分子。
- 把 PC 门从**均值**改为**按族**（例：`Δ ≥ 0.02` 至少在 4 个族中的 3 个成立），防止均值被单一族抬起而掩盖退化族。

---

## 2. 修正项（会实质影响结论的可解释性）

### M1 — `B_hard` 分量可能互相矛盾，且 LLM 上限可能过早绑定（P1）

**单位歧义**：`N_E = 128` 定义为"完整 24-graph suite 的 candidate evaluation 次数"，而 T1 卡写"evaluator 成本 预计 <1 s/candidate"。若 `<1 s` 指**每图**，则一次 campaign 是 `128 × 24 = 3072` 次单图评测 ≈ **51 分钟**，**超过 30 分钟墙钟**（两约束矛盾）；若指**整套**，则 `N_E` 相对 `T_wall` 差两个数量级，**几乎永不绑定**（定得太松）。两种情况都需要处理。

**LLM 上限偏低的风险**：`300k CEq` 按 Flash 高峰价约 **$0.09**。我方实测量级：一次极简 codex 调用 ~1 万 token；一次 claude 调用**空转**就要 ~2 万 input token；EvE 一次真实 agent 轮次 ~5.9 万 token。按 `CEq` 定义，`300k CEq` **可能在 10 分钟内被烧完**，于是 30 分钟形同虚设，而 campaign 短到可能看不到任何搜索进展——此时 `P(ΔS>0)` 的 sanity 信号缺失是**预算造成的，不是 substrate 造成的**。

**请求的修法**：加一个**免费的预算标定步**（一次宽松预算 pilot，测各臂 CEq 消耗速率与单图评测耗时），再据此定 `B_hard`，使设计目标明确为"**一个有能力的搜索能完成若干次改进迭代**"，而不是运气。并在契约里写明 `Stop` 里**预期哪个分量先绑定**。

### M2 — 可见性模型与留出集未定义（P1）

契约规定了 candidate API 与冻结套件，但**没有说 agent 能看到什么**：全部 24 图？只给聚合分数？只给 per-family 诊断？

**为什么这是 P1**：只有 24 个 n=128 的图可见时，一个编码 agent 完全可以**对实例硬编码**（把每张图的最优划分表写进代码）。那么 B0/B1 的 Δ 来自"记住实例"，而不是"搜索机制"。

**请求的修法（二选一并写明）**：
- **(a) dev/eval 切分**：例如 48 张图，24 张可见用于开发、24 张冻结不可见，只在后者记分；
- **(b) 刻意黑箱**：明确声明 agent 看不到任何具体实例，并承认这会削弱"外部工件可迁移性"这一问。

### M3 — 候选程序必须是"进程 + 文件协议"，不能是进程内调用（P1）

契约写 `solve(n, edges, seed) -> partition`。若这是**进程内调用**，则与我方评测器的三条硬约束冲突：超时无法可靠中断、候选崩溃会污染评测器、`invalid/error/timeout` 难以归因，且 cwd/PATH 无关性难以保证。

**请求的修法**：把接口定义为**文件协议 + 独立子进程**（例：读 `graph.json`、写 `partition.json`，退出码区分成功/格式错误/内部错误），与冻结的 timeout、状态根（state root）一起写进 `EvaluatorSource`/`Config`。这与我方现有机制一致，改动成本低。

### M4 — 5 s timeout 可能截断"更好但更慢"的启发式（P1）

A1 阶段（不比分数）影响小，但 **B0/B1 会失真**：一个更好的启发式若耗时 6 s，就会变成 `timeout` 而不是高分。契约已声明"不含 wall-time 计分"，但 5 s 这个**硬截断**仍会改变搜索可达空间。

**请求的修法**：把 `p95<1 s` 降级为**标定目标**；实际 validity timeout 放宽到 10–30 s；耗时作为**诊断字段**记录。

---

## 3. 次要项（便宜，但值得做）

- **m1**：`DataManifest` 应包含**每图基本统计**（n、|E|、度分布、参考上限）与生成器配置。生成器只用于首次产数据，事后无人能验证"这套图不退化"。
- **m2**：`one_exchange` 的签名要**按 pin 的提交核对**（`initial_cut` 参数在 NetworkX 不同版本存在差异），并确认给定 `initial_cut` 时它确定。
- **m3**：`R=4` 且 `≥3/4` 的门**鉴别力很弱**：真实完成率 0.5 也有约 **31%** 概率通过（0.7 时约 **65%**）。因此请写进契约一句——**"不通过"是强证据，"通过"是弱证据**——否则四次 campaign 的分数会被事后重新解释。

---

## 4. 需要你回答的问题

- **Q1**（对 B1）：你倾向 (A) 统一 harness 供给 outcome，还是 (B) 保 KAPSO 自评？若选 (A)，你建议如何重新表述 D7.1 的选择理由？
- **Q2**（对 B2）：明文 `base_url` 代理作为计量权威，你接受吗？若不接受，请给出在**禁止 TLS 中间人**前提下可实施的替代计量方案。
- **Q3**（对 B3）：参考上限如何构造（哪些启发式、多长时间预算、是否用精确解）？你建议的"PC 后剩余空间"下限是多少？
- **Q4**（对 M2）：dev/eval 切分还是刻意黑箱？若选切分，两张集合是否需要同家族同参数分布？
- **Q5**（对 M1）：在你看来，`B_hard` 应由"标定 pilot"决定，还是坚持预注册的固定值并接受它可能过早绑定？

---

## 5. 我明确同意的部分（请勿重开）

1. **A1 = 资格认定**，不以 score 显著优胜选 winner；`R=4` 是 qualification replication，不是 inferential sample size；只有真正提出 `H: μ_K − μ_S ≠ 0` 时才用 power-based sample size。**同意，并请把这一区分写进协议正文**（否则四次 campaign 的分数一定会被事后重新解释成低功效 benchmark）。
2. **任务选 T1（Max-Cut）**优于 T2/T3：评测极便宜且确定、搜索空间大、**外部工件充足**（MQLib 一族正好是 B0 所需的"普通既有实现"）、本地生成实例同时压住 memorization。
3. **正对照与 baseline 共享同一初始划分**（消混杂）。这是本次契约最专业的一处。
4. **block 级作废**（中途 outage 整块重跑）、**`CampaignID` 绑定模型路线/CLI 版本/工具权限/封闭拓扑**、**`CID`/`AID_r` 的因果角色冻结原则**（"若修改对象能改变 `P(Y|r)`，它必须进入 `CID` 或 `AID_r`"）。
5. **lexicographic 资格规则**（MeasurementIntegrity ≻ CampaignReliability ≻ OperationalSimplicity ≻ MedianResourceOverhead），以及"无法区分则**两者都合格**"的兜底。
6. **D7.2 的推理**（身份由 harness 度量；SimpleLoop 自己也可能被污染）——比我方原先的"推迟"更正确。
7. **A0.1 拆成 `EvaluatorRealization` + `OutcomeConsumption`**：与我方现有的两轴（测量轴/接受轴）一致，可直接对接。
8. **不扩大 adversarial fixture 集**：残余是架构性的，不是 fixture 形态的。
9. **第三方 runtime 记 `DEFERRED_NOT_EXCLUDED`**：比"排除"准确。
10. **步骤 9 的纪律**（若只有 SimpleLoop 合格，不得解释成"SimpleLoop 算法能力更强"）。

---

## 6. 附：本审计依据的实测证据（供你核对，非自述）

| 事实 | 证据 |
|---|---|
| KAPSO 的分数记录必须由会话自己产生 | 实测运行日志 + `registered_evaluation.py:52-102`、`generate_feedback` |
| KAPSO 已有两轮真实 campaign bridge（`bridge_verified`，裕度 2.201820520843313，`EID_r` 与受审 A0.1 运行一致） | `a0/runtimes/kapso/BRIDGE-2ROUND.md` |
| 我方代理的 HTTPS 路径是 **CONNECT、无 MITM** | `a0/notes/exit-closed/proxy-closure/`、`a0/closure/tool-loop/` |
| 三个 CLI 的成本自报均不可信（claude 高 10–20×；kilo/opencode 报 `$0`；KAPSO `node.cost_usd` 恒 0） | `a0/notes/exit-closed/{claude-deepseek,kilo-deepseek}/REPORT.md` |
| 评测器三条硬约束（不依赖 cwd/PATH、不写会被还原的目录、输出可多字段） | `a0/contract/adapter_contract.md`、`a0/tasks/circle-packing/e_star.py` |
| 存在 `E' ≠ E*` 在 14 个候选上逐位一致却通过旧检查器；残余是"照抄公开绑定值仍可通过" | `a0/fixtures/observational-equivalence/REPORT.md` |
| 四套 runtime 的 A0.1 现状（SimpleLoop 接受；其余三套 `MISSING_ATTESTATION` 但数字 14/14 一致） | `a0/conformance/report.json` |
| 一次 EvE 真实 agent 轮次 ~5.9 万 token；KAPSO 两轮 campaign 合计 22,447 token | 各自报告 |
| 400k 级 token 上限对应现金为"分"级，真正的稀缺资源是墙钟与工程时间 | 同上 |

---

## 7. 若你需要更多材料

请只列编号，人类负责人转呈：

| 编号 | 文件 |
|---|---|
| M1 | `a0/STATUS.md`（项目全景与逐项判定） |
| M2 | `a0/CONVERGENCE-2026-09-21.md`（D1–D5 收敛结果与待决策清单） |
| M3 | `a0/qualification/QUALIFICATION.md`（`Q_r` 与 `T_A1` 谓词） |
| M4 | `a0/contract/adapter_contract.md`（适配器契约：CLI、退出码、trace、封闭探针） |
| M5 | `a0/fixtures/observational-equivalence/REPORT.md`（变异评测器与边界矩阵） |
| M6 | `a0/runtimes/kapso/BRIDGE-2ROUND.md`（两轮 campaign 的完整证据） |
| M7 | `open_world_plan_review.typ` §4（原始协议） |
