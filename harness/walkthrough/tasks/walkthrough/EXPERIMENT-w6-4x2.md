# w6 4×2 实验 — 预注册与运行记录（N/R 两臂 × 4 runs，2 waves）

设计在 wave 运行开始前固定；本文件先记设计与口径，结果数据回填。

## 问题与假设

H：结构化字段交接（R）相对"不要求结构"（N）改善**时间**与**成本**。正确性只要求合法退出
（无任务真值；每个 run 必须 NORMAL：rc 0/0 + 双 stop + consensus on main），非 NORMAL 的
run 归因后补跑。

## 设计

- 基座 = w6 配置全套（密封轨迹读取 + refs 账本 + 全程门 + M1/M2 + 7 轮 + consensus），两臂
  逐字节相同，唯一差异 = prompt 中的 "Peer handoffs" 块（`tasks/walkthrough/prompt-w6{n,r}.md`；
  与 `prompt.md` 的单块 diff 已机械核验：除该块外零差异，`diff w6n w6r` = 仅该块交换）。
  - **N 块**（原文）："no structured fields are required. Whatever you hand to @@PEER@@ — the
    cross-review document, your response to their review, the board texts — may be composed in
    any form you judge clearest; the handoff format is yours to choose."
  - **R 块**（原文）："every text @@PEER@@ is meant to read or act on — the cross-review
    document, your response to their review, the board task texts — must open with a structured
    block carrying: `schema` ("research-handoff/0.1"), `act` (request|inform|propose|accept|
    reject|failure), `operation`, `objective`, `state` {`checkpoint`, `artifact_refs`,
    `evidence_refs`}, `constraints` (optional), `acceptance`. Nothing checks these fields
    automatically; the block is a discipline, not a verified format."
    （字段集 = 已归档 A2A survey 的最小 Research Message Schema；**不做程序核验**。）
- 运行编排：每臂 1 次冒烟（pilot；验证接线与两变体，并发）→ wave1 = N×4 → wave2 = R×4；
  每 wave 4 并发（每 run 占 1 个 B 侧 session，正好顶到 Token Plan 3–4 并发条款），15 s 错峰；
  编排 `tasks/walkthrough/exp42.sh`，日志 `logs/`。
- 指标：
  - **时间**：`result.json` started_at→finished_at（墙钟）；另录 agent_execution 相。
  - **成本**：每 run 从 collected chats 的 `usageMetadata`（每响应一次、零重复，已核）求和：
    uncached = prompt − cached、cache、out = candidates + thoughts（thoughts 按输出计费；
    candidates-only 作敏感度）。换算用一手价目：A = deepseek-flash（off-peak
    0.15/0.003/0.60 $/M；本实验窗口 UTC ~11:50–13:30 全程 off-peak）；B = qwen3.8-flash
    （0.8/0.1/2.7 ¥/M；credits = ¥×200 @k=1，¥×144 @k≈0.72 假设档）。
  - **B 侧真值**：Token Plan「加油包剩余量」float（credit-read 标签页 aria-valuenow，刷新后
    读数），wave 边界各读一次；1 pp ≈ 200 cr（T0 对表）。
- **判定**：三指标（墙钟中位、A$ 中位、B¥ 中位）各有方向；R<N 计数 0/3 = 不支持、
  1–2/3 = 部分支持、3/3 = 支持；n=4，只报中位与极差，不做显著性宣称。

## 运行记录

- 2026-10-11 19:50:25 CST 冒烟 pair 起飞（w6n-pilot / w6r-pilot）。19:52 实测两容器
  `x/prompt-variant` = `prompt-w6n.md` / `prompt-w6r.md` ✓（WT_PROMPT 接线端到端实证）；
  门/refs/轮次正常推进（a/b 齐步、ckpt-m1 出现、无 block/stall）。
- 积分表：T0（10-10 19:12 CST）= 81.365989425；tumor-1 收口（10-11 ~01:40）= 62.720036125；
  本窗口首读（冒烟中段 ~11:59 UTC，刷新后）= **62.236439275**；截图 `logs/credit-20261011-2000.png`。
- 待填：冒烟结果与清理证据；wave1 读数与结果；wave2 读数与结果；指标表（`metrics.py`）；H 判定。

## 程序件

- `prompt-w6n.md` / `prompt-w6r.md`（变体）、`wave.sh`（单臂 4 并发）、`exp42.sh`（全链编排、
  冒烟 NORMAL 门、三次积分表读数）、`metrics.py`（墙钟/token/成本/臂聚合/H 判定）。

## 结果（2026-10-11 19:50–21:06 CST 全部收口）

**8/8 wave runs + 2 pilots 全 NORMAL**（rc 0/0、双 stop、consensus on main、每 run 7/7 轮）；
正常退出后镜像自动清理实测生效（cleanup 行 ×10，两种后缀全清）。

| 指标（wave only, n=4/臂） | N 中位 [min..max] | R 中位 [min..max] | 方向 |
|---|---|---|---|
| 墙钟 | 21.0 [17.8..26.9] min | 21.1 [14.9..24.3] min | R ≥ N（+0.4%；**均值口径 −6.1%，中位/均值背离**） |
| A$（deepseek） | 0.1565 [0.0953..0.1828] | 0.1376 [0.0999..0.1483] | **R < N（−12.1%）** |
| B¥（qwen3.8-flash） | 0.825 [0.759..1.003] | 0.937 [0.680..1.096] | **R > N（+13.6%；均值 +7.0%）** |

积分表（B 侧真值）：pre-wave1 61.439866325 → post-wave1 59.704678225（N 臂 Δ1.735pp≈347 cr）
→ post-wave2 57.845130625（R 臂 Δ1.860pp≈372 cr，**R +7.2%**，与 B¥ 均值口径吻合）。
冒烟 pair ≈0.80pp/2 runs。含冒烟入样（n=5）时三指标 3/3 偏 R（time −17.3%）——方向对
"验证件是否并入"敏感，n=4 下不可作强论断。

**H 判定（预注册规则、主集 = wave、n=4）：1/3 指标偏 R → H 未获支持。** 结构化交接块没有
带来时间改善（中位 ≈ 平、均值小降、两极分化），且在 qwen 侧**增加**成本（+13.6% token 中位 /
+7.2% 积分），仅 deepseek 侧下降（−12.1%）。与 survey 自警一致："结构化消息并非天然更省
token"。

**操作变量保真（面级全量核验；回应面第二版——以每跑 Round:5 提交 diff 为准、不看文件名）**：
review 面 8/8 份 9/9 字段齐（两演员四跑无例外）；**R5 回应面**：a 侧 4/4 全块（9/9/9/9），
b 侧 1/4 全块（r4；r1–r3 为散文）。**回应文件名完全自由**：b 用过 work-b-1.md / work-b-5.md /
revise-b.md，a 用过 work-a-1.md / selfreview-a.md——**16/16 回应实际都在**（13–135 行/次）；
首版表格"b 几乎无 revised 段"是按固定文件名（work-b-1.md）搜索的定位器假象。board 任务文本
部分带块（2/7/0/2）；N 臂 0 块。可视化页含全量表。

**口径注**：thoughts 按输出计费（两 provider 文档口径）；A 侧全程 off-peak；每 run 明细
`python3 metrics.py w6n1..4 w6r1..4`；保真核验 `python3 check_manipulation.py <job>…`。

**装机段机理（2026-10-11 实测分解）**：setup 25–79s 的 2–3× 差异 = 纯网络时序税——apt
update 7.5–12.3s（env 镜像无 curl，每跑必装）× node 52.4MB 包下载 3.2–25.3s（同机 6 次
实测 ~8× 抖动，主变量）× npm -g qwen-code 13 包 3–6s；同 4 并发窗口内并存 31s 与 74s、
solo 的 w6 反而最慢（79s）→ 无并发/次序信号，与墙钟、成本均无相关。**已实施（2026-10-11
裁定）**：env 镜像构建期预装 curl+node+qwen；harbor install-only 冒烟 `preinstall-smoke`
实测 env 3.7s + 安装 **0.1s**（原 25–79s）、总 15s；运行时旧链保留为回退
（`common/dual_agent.py` 以 `command -v qwen` 守卫）。
