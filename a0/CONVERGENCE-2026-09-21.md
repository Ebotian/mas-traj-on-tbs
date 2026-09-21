# A0 收敛报告（D1–D5，2026-09-21）

对象：外部审查拍板的 D1–D5 中**无需用户再决策**的部分。方法：4 条并行工作流 + 3 个收尾工作流 + 2 名独立验证者（重导，不重读）逐项复核。
仓库：`/home/ebt/rsi-dev`。每一项都有可复跑命令；验证者结论见 `a0/verify/converge-d1d3/VERDICT.md` 与 `a0/verify/converge-d2d5/REPORT.md`。

---

## 0. 结论摘要

- **七项全部落地，独立验证全部 ACCEPTED**（其中两项带保留、无 REJECTED/UNPROVEN）。
- **D3 生效并产生了预期的结构性后果**：`kapso`/`eve`/`loreley` 现在**不接受**（`MISSING_ATTESTATION`），而它们的**数字仍然 14/14 一致**——"证据缺失"与"度量错误"被分开了。`r_1_a0_1_only = ["simpleloop"]`，`R_A1^main = ["simpleloop"]`。
- **D1 修掉了假红**：真实 `E*` 在 `python3.14` 下现在报 `EXECUTION_ENV_DRIFT`（14/14 行为一致），不再是 `MISMATCH_DIGEST`。
- **D5 的清理完成**：8 个容器、5 个网络、2 个卷已删除；密钥自检在**解压后**的归档上重做且非空转；需你在服务商侧轮换的清单已产出。
- **验证者找到两处比自述更严重的问题**（§3），其中一处改变了 D3 的残余评价。
- 冻结**未打 tag**（按指示）：`freeze.py gates` 报 6/8，红的两条一条是测量（三套未接线）、一条是**决策**（接线还是排除）。

## 1. 七项逐条

| # | 项 | 交付 | 判定 |
|---|---|---|---|
| 1 | **D1** 行为摘要与执行环境拆分 | `a0/envelope/`、`a0/conformance/` | ACCEPTED |
| 2 | **D3** 身份由 harness 度量 + 缺失即不接受 | `a0/envelope/`、`a0/conformance/`、SimpleLoop 已接线 | ACCEPTED |
| 3 | **D2** `T_A1` 谓词 + `T_exploratory` 改名 + 可核查冻结机制 | `a0/qualification/` | ACCEPTED（2 处保留） |
| 4 | **D5** 清理 + 本地配置 + 密钥自检 + 轮换清单 | `a0/env/cleanup/` | ACCEPTED |
| 5 | MRC 覆盖面枚举补全 | `a0/mrc/` | ACCEPTED |
| 6 | 适配器路径独立性 | 四套适配器 + `adapter.json` | ACCEPTED |
| 7 | **D4** EvE RNG 注入面查清 | `a0/notes/exit-closed/eve-rng/` | ACCEPTED |

## 2. 关键结果

### 2.1 D1：拆分在 checker 侧完成，`e_star.py` 与 `EID*` 未被触碰

`canonical_digest` 原先同时在干两件事。现在：

- `behaviour_digest(outcome)` = 域分隔 sha256 over Outcome 载荷**去掉 `canonical_digest` 与 `interpreter`**；`interpreter` 块单独与声明的**允许执行集合**（`a0/envelope/execution-set.json`：pinned `cpython 3.12.11`、sanctioned `cpython 3.14.7`）比较。
- 判定分层：行为一致 + pinned → 原判定；行为一致 + sanctioned → **`EXECUTION_ENV_DRIFT`（接受）**；行为一致 + 集合外 → `MISMATCH_EXECUTION_ENV`（不接受）；行为不同 → `MISMATCH_DIGEST`（不接受）。
- **验证者手工重算**了行为摘要（自己的实现）→ 14/14 与工具报值一致；并确认 `evaluator_source_sha256` 被**故意保留**在行为载荷内（所以"忠实但重新实现"的评测器仍在行为上被拒）。
- **反方向也验了**：变异评测器在 `--envelope off` 下仍 `14 × MISMATCH_DIGEST`——D1 **没有**救活变异体。
- 允许执行集合的成员资格是**测量**而非声明：把 3.14.7 的 interpreter 块代回 pinned 载荷，能复现 3.14.7 那次运行的 `canonical_digest` 14/14。

### 2.2 D3：令牌由 harness 签发，缺失即不接受

harness 从**自己**的 sweep 签发每候选一个 OID 令牌（绑定 `candidate_sha256 / EID* / theta_E / behaviour_digest / canonical_digest / interpreter / evaluator_source_sha256 / harness_run_id / nonce`），写入自己的 state root。四个不接受码：`MISSING_ATTESTATION`（无令牌）/ `MISMATCH_ATTESTATION`（令牌不对或身份与 harness 测量矛盾）/ `MISSING_IDENTITY`（有令牌无身份）/ `MISMATCH_EXECUTION_ENV`。**验证者独立重算了 OID**（自己的实现）→ 14/14 与存档一致，且 14 个 OID 互异。

**四套 runtime 的 A0.1 现状（取自 `report.json` 的机器可读字段）**：

| runtime | 测量轴 | 接受 | 判定 |
|---|---|---|---|
| SimpleLoop | 14/14 一致 | PASS（14/14 回显 harness 令牌） | 接受 |
| KAPSO | 14/14 一致 | FAIL | `MISSING_ATTESTATION` |
| EvE | 5/14 measured + 9 声明合成 | FAIL | `MISSING_ATTESTATION` |
| Loreley | 14/14 一致 | FAIL | `MISSING_ATTESTATION` |

验证者从 `report.json` 确认：三套的数字是 **14/14 一致、零行非零 delta**，不接受的原因**只**是缺令牌——这正是"证据缺失 ≠ 度量错误"该有的样子。

### 2.3 D2：谓词与冻结机制

`T_A1` = 测量充分 + **harness 已证明** + A0.2 机制 PASS + A0.2 bridge PASS + 封闭性 PASS + MRC FROZEN；`T_exploratory`（原 `T_literal`）明确限定于 pilot/integration/debug。规则以数据形式存放，并有自测断言"任何向量不得把 `FAIL` 放进任何 `*_allowed` 集合"。

当前：`R_A1^main = ["simpleloop"]`，`R_exploratory = ["simpleloop"]`。三套真实 runtime 从"未证"变成"**被拒**"，因此连 exploratory 也不含它们——这是 fail-closed 的刻意结果，不是疏漏（若要让 pilot 跑不合规 lane，那是阈值数据改动）。

冻结机制：`freeze.py check` 对 **48 件产物 + 28 个分量**做逐字节比对，自测证明单字节改动、分量改动、文件删除、文档篡改四种情况都能被抓到；冻结 id 只覆盖状态、可稳定重算。**未打 tag**；`freeze` 在任一 gate 红时退出 2。

### 2.4 D5：清理与轮换清单

删除了 8 个容器、5 个网络、2 个探针卷；`adapdc-catalog-postgres-1` 前后逐字段一致（ID/StartedAt/RestartCount/网络均未变）。密钥自检在 **解压后的**归档树与全部 16 个提交上重做（验证者确认：直接 grep `.zst` 对任何字符串都返回 0，所以"解压"这一步是必需的，他们做了），四个 key 全零命中，正对照 `EID*` 命中 993 文件 / 759,646 路径 / 50,635 次。

**一处简报前提被更正**：`~/.codex/config.toml` 并不指向 15722 中继，而是指向 `https://zjapi.com` **缺 `/v1`**，所以裸 `codex` 调用失败于路径而非中继。已按最小改动补上 `/v1`（有备份，`diff` 确认只有这一行），实测 `codex exec` 返回 `OK`、exit 0；端点侧无认证探测：`/responses`→404、`/v1/responses`→401，两处对照吻合。

### 2.5 两项小项与 D4

- **MRC 覆盖面**：枚举已补全并核实（kapso 11/3344、eve 12/1167、loreley 14/5278、simpleloop 14/5463）。承重结论：**EvE 的评测步脚本、Loreley 的评测插件、KAPSO 的 mode config、SimpleLoop 的 policy 都在任何冻结摘要之外**，而它们各自决定分数——A1 的一条臂可以改掉它们而 `MRC*` 不动。
- **路径独立性**：四套适配器改为"环境变量覆盖优先、否则从 `__file__` 推导"；`adapter.json` 的两个清单（只有 kapso/loreley 有）改为相对路径。验证者复现：复制树后四套都解析到副本、副本内运行 exit 0、隐藏副本 EID 时报错路径是**副本的**（决定性对照）、原树 `find -newermt` 为 0/0。
- **D4**：EvE 的 rng 只有**调用期参数**可注入，配置面不存在（`_target_` 只选类；实例属性只有 `replacement_mode`；把 `seed`/`rng` 塞进配置会被 `**_ignored_kwargs` 吞掉）。所以"配置注入"不可用、patch 被禁且也修不了模型流的可复现性 → **campaign replication 是 A1 的正确答案**，与"固定 seed 只是 replay 能力"一致。

## 3. 验证者找到的问题——两处比自述更严重

1. **（最重要）令牌拷贝不是必需的，因为绑定值本身是公开的。** 变异 fixture 自己测出 `eplus_d3_claim_copy` 通过；但验证者进一步指出：`E_STAR.json` 的 `candidates[].outcome` 里就有完整 `E*` 载荷（含 `evaluator_source_sha256`、`interpreter`、`canonical_digest`），他**用公开文件重算出的行为摘要恰好等于信封里的绑定值**。所以那条"拷贝令牌"的 lane 其实连信封都不需要——只需要每次运行的那个 OID。结论：**没有任何更便宜且稳健的关闭方式，残余就是 harness-owned measurement**；fixture 的表述反而**低估**了残余。
2. **冻结机制不覆盖决定分数的仪器。** 对 `a0/runtimes/eve/steps/eve_evaluator_step.sh.tmpl` 追加 1 字节，`freeze.py check` 仍报 `MATCHES_ARMED`（而对已登记的产物追加同样 1 字节会正确报 DRIFTED）。这把 MRC §7 的发现延伸到了冻结自身：**"A0 已冻结"目前不等于"决定分数的仪器被冻结"**。
3. **D2 的谓词对结构畸形向量过宽**：`a0_1_measured={value:"FAIL",state:"PASS"}` 会被判 eligible；`a0_1_adapted` 缺 `adapted` 字段时 `int_of` 默认 0 也会 eligible。六个 `*_DOMAIN` 常量目前是死代码。**经 `build_qualification.py` 不可达**，故今天的 `R_A1^main` 不受影响。
4. **两处命名仍在折叠两根轴**：`E-r-equals-E-star.ok` 对三套返回 `false`（尽管 `measurement_agreeing=14`），只有 detail 文本在消歧；`G1_d1_landed` 是子串测试却标着 `kind=measurement`。
5. 若干文档夸张：`conformance.py:row_attestation` 的 docstring 与实现不符；`run_envelope_probe.sh` 只覆盖 6 行矩阵中的 4 行；信封是**按 sweep** 而非按运行签发；fixture 的 README 标题"只有 `eplus_mut_own` 保持判定"不精确（另两行也保持 FAIL 状态，只是理由变了）；D5 报告说"四个 `adapdc-*`"实为五个；MRC 报告一处行号引用（`runtime.py:37` 实为 `:79`）。
6. **pin 1（`45cc4e90…`）在 git 历史里不可恢复**（那是一次仅存在于工作树的修订），该链路目前依赖保留的报告副本。

## 4. 需要你决策

- **D6（真正的前置）**：A1 experiment contract——任务选择、`B_hard`（含 `C_LLM`，且必须在**代理层**计量，因为三个 CLI 的成本口径都不可信）、预注册正对照、replicate 数 R 与功效、各臂随机交错顺序。**这是唯一挡在 A1 前面的东西。**
- **G6（冻结门的决策）**：`kapso`/`eve`/`loreley` 是**接线**（各自在运行时自己的评测路径里产出并回显证明书；KAPSO 的必须在会话内部产生），还是在冻结文档里**明确排除**并写明理由？两种答案都能让冻结门变绿。
- **R5 的残余**：是否采纳"**A0.1 行由 harness 拥有评测调用**"（即 adapter 不再自己评测，只消费 harness 产出的 outcome）？这是第 3.1 节唯一剩下的关闭方式，且审查文本已认可这个语义转变（"runtime integration 是否忠实消费 harness 产出的 outcome"）；代价是**改变 A0.1 对三套真实 runtime 所测的东西**，并需要重跑。
- **冻结覆盖面**：是否把决定分数的仪器（EvE 评测步、Loreley 插件、KAPSO mode config、SimpleLoop policy）纳入冻结产物集合？
- **接受 1 成员主臂**：`R_A1^main = {SimpleLoop}` 是否足够开 A1 pilot（审查已说过"集合不必包含四套"），还是先投资接线。
- **D5 的剩余**：服务商侧 key 轮换；`~/.claude/settings.json`（明文 key，且其优先级**高于**进程环境）与 `~/.cc-switch/cc-switch.db` 必须同步更新，否则会静默失效；`~/.kimi-code/config.toml` 里那个已死的 `ccswitch-codex` provider。

## 5. 本报告的边界

- 未做 A1 设计；未打冻结 tag；未修改任何上游 runtime 源码；未做服务商侧轮换。
- 上面第 3 节的问题**未被修复**——验证者是只读的，而其中 3.1/3.2 属决策，3.3–3.6 属可机械修但尚未排期。
- `a0/STATUS.md` 的 §3.3 表描述的是 D1/D3 **之前**的状态，已在上方加注指向本报告。
