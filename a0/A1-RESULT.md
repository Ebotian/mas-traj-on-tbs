# A1 结果报告（T1 Frozen Max-Cut Heuristic Search）

日期：2026-09-22 · 仓库：`/home/ebt/rsi-dev` · 本报告覆盖目标八项，逐项给出判定、执行的命令、真实输出与证据路径。

**结论摘要**：A1 的测量链**已建成并在两条臂上跑通真实会话**（第 1–5 项）；预注册的**任务准入门未通过**（第 6 项），原因是"已知有效的外部工件"几乎把任务解完，可测空间不足；门**没有被放宽**；第 7 项（标定 → 冻结 `B_hard`）已完成；第 8 项（8 个 campaign → 资格结论）因此**未运行**。一处契约修订（把正对照换成有界轮次的 `one_exchange`）已完成**测量与提案**，等待用户拍板。

---

## 1. 八项逐条

| # | 项 | 判定 | 关键证据 |
|---|---|---|---|
| 1 | 48 图 dev/eval 套件 + calibration + DataManifest | **完成** | `a0/tasks/maxcut/suite/`（60 图：24 dev / 24 eval / 12 calibration）；canonical 60/60；可重生成；答案已封出树外 |
| 2 | T1 的 `E*` + `EID*` + `C*(T1)` | **完成** | `e_star.py`＋`e_star_child.py`；`EID* = 7ce9e72f…`；21 个冻结候选，一致性 **PASS / 无漂移** |
| 3 | 参考目标 `R_i` + `OPT_i`/`U_i` | **完成** | `references/targets.json`：60/60，**42/60 经 SCIP 认证最优**，其余带 `U` 界 |
| 4 | 明文 MeterProxy（CEq、UNMETERED_CALL） | **完成**（修了一个真 bug） | `a0/meter/`：**65 项**自检 + 线上原始抓包前后对照 |
| 5 | harness-owned 接线（两臂）+ live 探针 | **完成** | `a0/a1/`：SimpleLoop **9/9**、KAPSO **11/11**（plumbing）与 T1 树 **16/16**；次序问题已闭合 |
| 6 | 预注册门实测 | **未通过：`NOT_ADMISSIBLE`** | `gates/verdict.{dev,eval}.json`；见 §3 |
| 7 | 标定 pilot → 冻结 `B_hard` | **完成** | `a0/a1/calibration/B_hard.json`（sha256 `fd15d9ec…`）；见 §6 |
| 8 | 4 block × 2 arm campaign → 资格结论 | **未运行**（被第 6 项阻塞） | `R_A1^main = ∅`；见 §7 |

---

## 2. 冻结身份

```
EID* (T1) = 7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec
  EvaluatorSource   1bfee868…
  DependencyLock    e7ac2476…
  DataManifest      042db1cc…
  Config            178b47c7…
  MetricDefinition  0ba2145a…
E* 自身 digest（authoritative） = dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00
KAPSO 注册评测树 EID_r = manifest:63a9a83c…
```

- `EID*` 的漂移史与理由全部记为历史（`cddfa64e… → eccd859c… → 7ce9e72f…`，均由 `E*` 的依赖变更引起，非方案变更）。
- `CID` = **14 个因子**；`AID_r` 含 `A_runtime.registered_evaluation_tree(+_files)`（由声明方从**树的字节**重算并与 `binding.json` 交叉核对）。
- 复跑：`python3 a0/a1/verify.py` → **6/6, rc 0**。

---

## 3. 政策门：Δ 通过、ρ 未通过

| 门 | 判据（未改动） | dev（24 图） | eval（24 图） |
|---|---|---|---|
| Δ | 均值 ≥ 0.03 且 ≥3/4 族 ≥0.02 | **通过** 0.247942608，4/4 族 | 通过 0.238448095，4/4 族 |
| ρ | 中位 ≥ 0.30 且 ≥3/4 族 ≥0.30 | **未通过** 479/3016 = 0.158819629，**0/4 族** | 未通过 2477/13860 = 0.178715729，0/4 族 |
| 饱和否决 | 基线临近参考即 NO-GO | 未触发（0.384381172） | 未触发（0.361056711） |

**判定：`NOT_ADMISSIBLE`**（`gates/verdict.dev.json`、`verdict.eval.json`；`gate_runner.py` exit 1）。
**原因（实测）**：契约指定的正对照 `one_exchange` 跑到局部最优时达到参考目标的 **94.3%**，吃掉基线→目标差距的 **82.6%**。一个几乎把任务解完的"已知有效工件"让后续 B0+ 无空间可测。

**已完成的重造诊断**（`redesign/LEVERS.md`、`gates/REVISION-PROPOSAL.md`）：

| 正对照强度 | Δ dev / eval | ρ dev / eval | Δ 门 | ρ 门 | dev | eval |
|---|---|---|---|---|---|---|
| k=1 | 0.0182 / 0.0180 | 0.9401 / 0.9429 | **FAIL** | pass | NOT | NOT |
| k=2 | 0.0329 / 0.0331 | 0.8956 / 0.8942 | pass | pass | ADM | ADM |
| k=5 | 0.0697 / 0.0702 | 0.7751 / 0.7623 | pass | pass | ADM | ADM |
| **k=10** | 0.1166 / 0.1164 | **0.6156 / 0.6008** | pass | **pass 4/4** | **ADM** | **ADM** |
| k=25 | 0.2049 / 0.2020 | 0.3259 / **0.3012** | pass | dev 3/4、**eval 2/4** | ADM | **NOT** |
| ∞（现行） | 0.2479 / 0.2384 | 0.1588 / 0.1787 | pass | FAIL 0/4 | NOT | NOT |

两条必须随表一起读的事实：**已发表的 greedy 构造同样过不了 ρ**（0.2287 / 0.2399，0/4 族）——说明不是"某个启发式太强"的偶然；**提高 n 不是答案**（`ER:p080` 的 ρ 随 n 平坦甚至下降，且冻结正对照在 n≥512 超时）。**任一选择都会改变契约内容（正对照定义），因此属于用户决策，本报告不代决。** 阈值（0.30 / 0.03 / 0.02）一个字未动。

---

## 4. 计账（真实 ledger 片段）

`a0/a1/calibration/ledger.jsonl` 与各次 live 探针的账本，全部由 `a0/meter/verify_ledger.py` 从每行自己的 `usage` 重导：

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_calib_A_simpleloop","arm_id":"A_simpleloop",
 "provider":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions",
 "model_requested":"deepseek-flash","model_reported":"deepseek-flash",
 "provider_request_id":"538d25c2-b511-4f36-9583-5ffe820064cd","stream":false,
 "usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":1112,"completion_tokens":2048},
 "ceq":9304,"unmetered":false,"reason":null}
```

**构造的 `UNMETERED_CALL` 证据**:一个成功响应缺 `usage` 的调用（故意触发的 401）被记为
`{"ceq": null, "unmetered": true, "reason": "upstream_http_401_no_usage"}`，并让 `BudgetEnforcer` 以
`budget_exhausted:unmetered_model_call` **停止**——即"缺账即停"，不估算。

计账的**前置条件**也已被强制：CLI 的 `base_url` 必须指向本机明文端点；`HTTPS_PROXY`/CONNECT 不作为计量权威（这在拓扑上被证明：CONNECT 之下代理看不到 token）。迄今全部真实花费约 **52,100 CEq**（`deepseek-flash`，几分钱量级），其中标定 pilot **423,941 CEq**、两臂 live 探针 9,484 CEq、T1 树 live 探针 1,116 CEq。

---

## 5. harness-owned 注入（两臂，真实会话）

| 证据 | 判定 |
|---|---|
| 同一候选字节 → 同一 Outcome → 同一选择（SimpleLoop） | **9/9** |
| harness 供一个"`E*` 不可能产生"的数，选择跟随 **harness 的数**（证明是消费不是度量） | 已验 |
| runtime 无法自报分数（无 harness 身份 → 适配器 exit 3；服务中途停止 → 候选记 `error/harness_outcome_missing`） | 已验 |
| KAPSO：记录分 = harness 供的值；会话自己打印的 manifest 行**无法覆盖** | **11/11**（plumbing）、**16/16**（T1 树）；会话声称 777777，记录分为 harness 的值 |
| 类三元组**从 runtime 推导**（硬编码 `full/1.0/1337` 会被静默丢弃，已复现该失败模式并消除） | 已验 |
| 候选通道：网络阻断、答案不可读、凭据不可达、诚实路径仍给分 | 敌意候选 **13/13** |
| 分数合理性上界 `0 ≤ cut ≤ |E|`（越界默认**拒绝**，仅在显式标注模式下可发布） | **7/7** |

次序问题的答案（此前唯一未闭合的技术口子）：KAPSO 的 `node.evaluation_output` 里最终保留**最后一行**，harness 的行在**会话结束之后**写入，因此成为唯一作者；没有任何认证机制——次序是唯一的机制，这一点已明写。

---

## 6. 冻结的 `B_hard`

```
B_hard = ( T_wall 1800 s, CEq_max 1_966_519, N_evaluatorCalls 725, P_concurrency 1 )
```
由**先冻结**的流程（`PILOT-PROCEDURE.md`，doc sha256 `68af1321…`，每次运行复核）＋**机械应用**的映射 `f` 得到；`B_hard.json` sha256 `fd15d9ec…`，**可从已提交证据逐字节重现**。

实测速率（标定集，仅 12 图，明确不用于任何算法选择）：

| 臂 | CEq/min | 评测/min | 变异系数 |
|---|---|---|---|
| A_simpleloop | 52,440 | 9.898 | 0.112 |
| A_kapso | 21,323 | 19.315 | 0.088 |

**护栏不会过早绑定**：`CEq_max` 对应 37.50 / 92.22 分钟，`N_E,max` 对应 73.25 / 37.54 分钟，都晚于 30 分钟的墙钟主约束。`τ = 10 s` 由标定实测 p99（133–147 ms）按 §7 公式得出（下限生效），与门的运行一致。

---

## 7. 第 8 项：campaign **未运行**（`R_A1^main = ∅`）

**未运行的理由**：任务未通过准入（§3），而 campaign 的意义正是"在合格任务上比较 substrate 如何消费可信 Outcome 并推进搜索"。在不合格任务上跑 8 个 campaign 会产出不可解释的数字，且违反"预注册门不得放宽"的边界。

**已经就绪的部分**（一旦任务合格即可运行，无需新的设计决策）：编排骨架（`CampaignID`、RCBD 调度、block 级作废、预算执行器）dry-run **25/25**；`CID` 14 因子与两条 `AID_r` 已冻结；标定流程与 `B_hard` 已冻结；两条臂的注入已实测。

**`R_A1^main` 的最终成员：空集**——没有任何 substrate 被认定合格，因为**任务本身**尚未合格。这不是"某条臂失败"，而是筛选在第一步就正确地停了下来。

---

## 8. 独立验证

| 轮次 | 范围 | 结论 |
|---|---|---|
| `a0/verify/a1-testbed/REPORT.md` | 第 1–5 项 + 门 | 六项通过；**四个真缺陷**（见 §9） |
| `a0/verify/a1-final/REPORT.md` | 最终修订的身份链、闭包、标定、两处新修 | 七项 ACCEPTED；**一项 REJECTED**（`kapso_t1` 身份漂移）→ 已修复并复验 5/5 |
| `a0/verify/a1-delta/REPORT.md` | 四处修复本身 | 绝大多数 ACCEPTED；两项 REJECTED（审计不查树因子一致性；286 处未标注摘要）→ 已修复，且**验证者自己的反例脚本现已失败**（即缺口真的被关闭） |
| `a0/verify/a1-hygiene/*` | 历史标注 | `run_all.sh` → PASS 5/5，工作区干净 |

诚实说明：最后一次修复**尚未经过全新的独立复核轮**；关闭它们的证据是"验证者自己的探针现在通过/失败于正确方向"，而不是新一轮外部复核。

---

## 9. 这一阶段共修掉的缺陷（仪器确实在工作）

1. **计账代理的 framing 缺陷**：`Content-Length` 被当作 hop-by-hop 剥掉且未补回 → 上游收到无分帧 body → **真实 provider 的每次调用都 400 且记为 `unmetered`**，即 token 上限此前**不可能有真实数字**；它自己的 55 项自检看不见（mock 读到的 body 长度为 0）。修后 65 项自检 + 原始抓包前后对照。
2. **`E*` 装载丢掉可执行位**：按一个文件的 mode 决定启动方式、却执行只带内容的副本 → 一次 `chmod +x` 让两个冻结候选无法评测、门无法重现自己的判决。改为无条件解释器前缀（与门当初实际调用一致）。
3. **Outcome 缓存会读陈旧记录**：现按 (θ, E\* 摘要, 候选摘要) 校验，陈旧记录被重跑。
4. **答案泄漏**：候选可读到参考划分并照抄得 `R = OPT`（验证者实测 217 = R 在 `G_eval_0001`）；`graph.json` 的 `generator.seed` 还能重建 Planted 族的解。已封：候选侧改为**去 `generator` 的视图**（同时记录套件哈希与交付字节哈希），划分向量封出树外（只留承诺哈希），并以敌意候选逐路径证明。
5. **候选通道未隔离**：`--net-isolate` **单独不够**（实测：候选可直连 API，而 key 对该 uid 可读）。现由 harness 在 user+mount+net+PID 命名空间里运行 `E*` 与候选，仓库被 tmpfs 遮蔽；并修掉了一个**真 bug**：本机 `/tmp` 是 tmpfs，旧 `_hide` 把它当成"已隐藏"，于是候选能看到宿主 `/tmp`。
6. **身份漂移**（三次）：每次都由"先改 `E*`、后忘了重冻"引起；现在有了 `t1_eid.py check` 与"删/改后必须重冻"的纪律，且 `CID` 与 `AID_r` 的一致性由审计交叉核对（此前可静默重现，现已关闭）。
7. **未标注的旧摘要**（该阶段共 299 文件 / 518 行）：全部加历史标注或改为当前值；标量阈值从未改动。

---

## 10. 待用户决策（三件）与残余

1. **是否采纳契约修订（正对照强度 k）**——建议 **k=10**（两套集合 4/4 族、两项都 ≥2× 余量）；必须同时声明这是**看到 ρ 之后**才做的选择（后验自由度），以显式修订预注册，而非静默替换。备选 k=5（空间更大、正对照更弱）；不建议 k=2。若坚持"正对照必须是完整的 `one_exchange`"，则等价替代是**换任务族**，成本高一个量级。
2. **`τ` 是否任务级改为 10 s**（标定实测支持；推广需重跑以 τ=30 存过 Outcome 的地方，判决不变、摘要会变）。
3. **是否顺带重画套件**——我的判断是不必（§3 的两条事实）。

**残余（不影响任何判定数字）**：`positive_control/e-star-state/**`（gitignored 原始运行状态，48 个 Outcome 带旧摘要）；`calibration/pilot_arm.json` 内嵌旧沙箱模块摘要（已在 D-A1-14 标注）；`A1-INTERIM.md` 的一行旧身份已在本轮更正；依赖单一 uid、无 root 的隔离仍有已量化的残余（内核共享、无 cgroup 限制、harness 进程本身未沙箱）。

**边界**：未修改任何上游 runtime；未改任何门阈值；未做服务商侧操作；8 个 campaign 未运行。
