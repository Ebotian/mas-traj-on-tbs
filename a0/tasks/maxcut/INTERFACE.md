# T1（Frozen Max-Cut Heuristic Search）冻结接口 v1

本文件是 A1 的**唯一接口权威**。任何并行工作流都按此实现；若实现需要偏离，必须先在 `a0/A1-DEVIATIONS.md` 记录并说明理由，不得静默偏离。

**第一性原理约束（每一条接口都服务于其中之一）**
(i) 目标由冻结且可复算身份的评测器测量 → `EID*` 与 `evaluator_source_sha256`
(ii) 评测实现由 harness 拥有 → 候选**不得自报分数**，分数由 harness 从 graph+partition 重算
(iii) 分数可观测地进入选择 → Outcome 必须带可得 join 的身份与聚合摘要
(iv) 预算可强制 → CEq 由代理账本计量，runtime 自报仅诊断
(v) 改进须在未见实例上成立 → dev/eval 严格分离，eval 只在最后评一次

---

## 1. 目录布局

```
a0/tasks/maxcut/
  INTERFACE.md            本文件
  generators/             生成器脚本 + 参数配置（provenance 用，非数据身份）
  suite/                  ★冻结数据
    dev/       G_dev_0001.json … G_dev_0024.json
    eval/      G_eval_0001.json … G_eval_0024.json
    calibration/ C_0001.json … （只用于标定资源速率，不得用于任何选择）
    manifest.json          每图的 sha256、family、n、|E|、统计
  e_star.py               ★harness-owned 评测器（T1 的 E*）
  e_star_child.py         候选子进程装载器（沙箱、超时、四态）
  candidates/             ★C*(T1)：固定候选集，用于一致性检验（含 invalid/error/timeout）
  references/             ★参考目标 R_i / OPT_i / U_i + 构建日志
a0/meter/                 明文计账代理 + ledger 格式
a0/a1/                    A1 编排：CID/AID、block、预算强制、资格判定
```

## 2. 图文件 `graph.json`（只读输入）

```json
{
  "schema": "a0.maxcut.graph/v1",
  "graph_id": "G_dev_0001",
  "family": "ER|RR|BA|Planted",
  "n": 128,
  "edges": [[0,17],[0,42], ...],
  "generator": {"name": "...", "version": "...", "params": {...}, "seed": 20260922},
  "notes": ""
}
```

规范（**canonical form**，用于 sha256）：
- `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True)` + 单个结尾换行；
- 节点编号 `0..n-1`，**无自环**、**无重边**，每条边写作 `[u,v]` 且 `u < v`；
- `edges` 按字典序升序排序；
- 权值固定为 1（不出现 weight 字段）；
- 允许孤立点，但 `manifest.json` 必须记录每图孤立点数量。

**数据身份 = 该文件的 sha256**。生成器仅作 provenance；`generator.seed` 不参与身份，也不得被任何判定引用。

## 3. 候选产物 `partition.json`（候选写出）

```json
{"schema":"a0.maxcut.partition/v1","graph_id":"G_dev_0001","assignment":[0,1,0,...]}
```

- `assignment` 长度**必须**等于该图的 `n`，元素只能是整数 `0` 或 `1`；
- 规范形式同上（排序键、紧凑分隔符、结尾换行）；
- 越界长度、非 0/1、缺字段 → **`invalid`**（不是 error）。

## 4. 候选 ABI（子进程 + 文件协议）

```
argv:  <entry> --graph <abs graph.json> --out <abs partition.json> --seed <int>
cwd:   候选私有 scratch 目录（harness 创建）
env:   PATH 最小集、PYTHONDONTWRITEBYTECODE=1、HOME=<scratch>、LANG=C.UTF-8；
       清空 http_proxy/https_proxy/no_proxy；不注入网络；不注入任何密钥
```

**退出码语义（冻结）**

| 退出码 | 含义 |
|---|---|
| `0` | 候选认为自己成功（是否真的 ok 仍由 harness 判定 §6） |
| `20` | 候选主动声明产出非法（格式/不可行） |
| `30` | 候选内部错误（异常/崩溃） |
| `40` | 候选主动拒绝（例如拒绝在没有网络时运行） |
| 其他非零 | 记为 `error`（保留原始码） |

- **超时不是退出码**：harness 在 `τ` 到达时对进程组 `SIGKILL`，并把该图记为 `timeout`。
- 候选**不得依赖 cwd、PATH、外部文件、网络**（要求由其自身保证，违反会在一致性检验里被 C*(T1) 的 cwd/PATH 探针抓到）。
- 候选**不得自报分数**：Outcome 里的数值一律由 harness 从 `graph.json` 与 `partition.json` 重算。

## 5. 每图 Outcome（多字段）

```json
{
  "schema": "a0.maxcut.outcome/v1",
  "graph_id": "G_dev_0001",
  "graph_sha256": "…",
  "candidate_id": "…",
  "candidate_source_sha256": "…",
  "status": "ok|invalid|error|timeout",
  "cut_edges": 317,
  "cut_fraction": "0.6191406250000000000",
  "edges_total": 512,
  "failure": {"kind": "…|null", "detail": "…"},
  "interpreted": {"exit_code": 0, "wall_ms": 41},
  "interpreter": {"implementation":"cpython","version":"3.12.11","executable":"…"},
  "evaluator_source_sha256": "…",
  "theta": {"seed": 1337, "timeout_s": 30},
  "canonical_digest": "…"
}
```

**数值权威（关键，避免 1 ULP 之争）**
- `cut_edges`（整数）是**唯一权威数值**；任何比较、聚合、门判定都基于整数精确运算。
- `cut_fraction` 是十进制**展示字段**，由整数按确定规则格式化，**任何判定不得引用它**。
- `ok` 时 `cut_edges` 必有值；`invalid`/`error`/`timeout` 时 `cut_edges` 必须为 `null`，**绝不允许写成 0**。
- `failure.kind` 必须与 `status` 一致且非空（`invalid_configuration` / `malformed_partition` / `candidate_import_failed` / `candidate_call_raised` / `non_deterministic` / `runtime_budget_exceeded` / …）。

**聚合（一个候选在一组图上的结果）**

```json
{
  "schema": "a0.maxcut.aggregate/v1",
  "candidate_id": "…", "graph_set": "dev|eval|calibration",
  "counts": {"ok":24,"invalid":0,"error":0,"timeout":0},
  "score_exact": {"numerator": 7441, "denominator": 12288},
  "per_family_exact": {"ER":{"numerator":…,"denominator":…}, "RR":{…}, "BA":{…}, "Planted":{…}},
  "outcome_digests": ["…", "…"]
}
```

- `score_exact = (Σ_i cut_edges_i) / (Π_i |E_i| 的精确分数累加)` 的**约分结果**；用 `fractions.Fraction` 语义实现，**不得用浮点**。
- `per_family_exact` 只作诊断，**A1 资格判定不得据此重新加权**。

## 6. harness 判定规则（冻结）

1. 候选退出码非 0 → 按 §4 映射；若退出码 0，继续。
2. `partition.json` 不存在 / JSON 非法 / schema 不符 / 长度不符 / 元素非 0/1 → `invalid`。
3. 否则 harness 重算 `cut_edges` → `ok`。
4. 同一个（候选字节, 图字节, seed）跑两次，`partition.json` 的规范字节必须**逐字节相同**；否则记 `non_deterministic`（`error`）。
5. 任何 `status != ok` **绝不得**贡献分数或折算为 0。

## 7. 超时策略

- `τ = min(30s, max(10s, 10 × p99))`，`p99` 由 §9 的标定实测得出，冻结进 `theta.timeout_s`。
- `p95 < 1s` 仅作**标定目标**，不是及格线。
- 候选墙钟时间单独记录（`interpreted.wall_ms`）作为**诊断与资源消耗**，不进算法分。

## 8. CEq 与计账账本（`a0/meter/`）

```json
{"schema":"a0.meter.call/v1","campaign_id":"…","arm_id":"…","ts":"…",
 "provider":"deepseek","endpoint":"…","model_requested":"deepseek-flash","model_reported":"…",
 "provider_request_id":"…","stream":true,
 "usage":{"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":20065,"completion_tokens":312},
 "ceq": 21313, "unmetered": false, "reason": null}
```

> **示例自洽性（v1.1 修正）**：`0 + floor(0×2/100) + 4×312 = 1248`，故 `miss` 必须是 `20065` 才能得到 `ceq = 21313`。本文件 v1 初稿写的是 `miss=20153`，与自己的公式不符——该错误由 `a0/meter/` 的实现者发现，已修正，并在 `a0/meter/tests/test_meter_core.py` 留下一条钉住此自洽性的测试。**凡本文档给出的示例数值，若与公式不符，以实现公式为准。**

- `CEq = prompt_cache_miss_tokens + 0.02 × prompt_cache_hit_tokens + 4 × completion_tokens`（整数化：`ceq = miss + floor(hit×2/100) + 4×completion`）。
- **成功响应缺少 usage → `unmetered: true` 且 `ceq: null`**；不得估算，不得按 token 数猜。
- 代理**必须**以明文 HTTP 终结（CLI 的 `base_url` 指向本机），再向 `https://api.deepseek.com` 发 TLS；`HTTPS_PROXY`/CONNECT 不作为计量权威。
- 计量前提写进 `AID_r`：`meter.mode=plaintext_base_url`、`meter.allowlist=[api.deepseek.com]`。
- 每个 campaign 的 `ceq` 总和由账本求和，**runtime 自报的 cost/token 只作诊断**。

## 9. 标定与预注册映射

- 标定集 `suite/calibration/**` 与 dev/eval **不重叠**，且不用于任何算法选择。
- 标定只测资源速率：每 arm 的 `q_r = CEq/min`、`e_r = Eval/min`、候选延迟分布（得到 `p99` → `τ`）。
- 预注册映射 `f(telemetry) → B_hard`：**单调、有上界**，且必须报告 pilot 自身方差。默认：
  `T_wall = 30 min`（设计上的主约束）；`CEq_max = 1.25 × max_r(30 分钟正常消耗)`；`N_E,max = 1.25 × max_r(观测套件评测次数)`。
- 冻结后写入 `A1Contract`，**不得在 campaign 中途调整**。

## 10. C*(T1)：固定候选集（用于一致性检验，不是 A1 的臂）

至少覆盖：`ok` 但低分；`ok` 且高分（用 PC 结果）；两个数值相同但字节不同的 `ok`（并列对）；`invalid`（长度错）；`invalid`（元素非 0/1）；`invalid`（JSON 损坏）；`error`（抛异常）；`error`（非确定性：用未播种随机）；`error`（不写文件）；`timeout`（故意长睡）；`error`（试图联网——在封闭拓扑下必须失败）。每个候选须有冻结的 `solution` 字节与 sha256，并用于 §6 全部规则的回归。

## 11. 与既有仪器的复用关系（不要重新发明）

- **行为投影 / 执行环境拆分（D1）**：沿用 `a0/envelope/` 的 `behaviour_digest`（排除 `interpreter` 与 `canonical_digest`）与允许执行集合；T1 只需新增自己的 `EvaluatorSource` 记录。
- **harness-owned outcome（D3）**：沿用 `a0/envelope/` 的 OID 令牌机制；T1 的 Outcome 作为被注入对象。
- **trace 契约**：沿用 `a0/contract/trace_schema.md` 的三条 trace（score/selection/resource）与 `validate-run` 的 run 级校验。
- **失败阶段映射表**：沿用 `a0/contract/selection/simpleloop.selection.json` 里那张冻结表，T1 的新 `failure.kind` 必须映射到它或显式声明扩展。

## 12. 明确禁止

- 放宽任何预注册门（PC 按族 Δ、ρ、饱和 NO-GO）；不过就重造套件并记录。
- 用浮点做分数比较；用候选自报的分数；把 `status != ok` 折算成 0。
- 让 eval 集进入 agent 的工作区、上下文或任何可见路径。
- 修改上游 runtime 源码。
