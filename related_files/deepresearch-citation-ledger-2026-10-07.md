<!-- 配套件:为 related_files/deep-research-report-longhorizon-agent-eval-2026-10-07.md 做的引用核验台账
     方法:38 个 URL 逐条 fetch,把报告绑定的断言与目标原文对照;[我复核] = 我本人抓取核对,其余为子代理一遍核到
     结论:全部可解析;1 条数字错(0.15× → 0.23×)、1 条措辞不成立(replay-based → rebuild-from-artifact)、
          1 条源冲突(LHTB 类别 8/9);最硬的审计数字(39/102 · 11/140 · 411/498 · 740 任务 · 四类 GCP 机 · 9/28)逐字成立
-->
# Deep Research 报告引用核验台账(2026-10-07)

被核对象:`~/Downloads/deep-research-report.md`(1,196 行,58,679 B)
标题:*Long-Horizon Agent Evaluation: SOTA Systems, Metrics, and an Engineering Blueprint for ADA/OPL*
方法:逐条 `web_fetch` 引用目标,把报告绑定的断言与目标原文对照。标注 [我复核] = 我本人抓取核对;其余 = 子代理一遍核到(抽查过我复核项的一致性)。

## 结论一句话

38 个 URL **全部可解析**(3 个重定向);**1 条数字错、1 条措辞不成立、1 条源冲突**;**最硬的那条审计数字逐字成立**;5 个 filecite 目标不可达。

## 必须改的三条

| # | 位置 | 报告写的 | 主源实际 | 判定 |
|---|---|---|---|---|
| 1 | 164 行 SWE-fficiency | 「agents averaged under **0.15×** expert speedup」 | arXiv:2511.06090 摘要原句:「agents achieve less than **0.23x** the expert speedup」[我复核] | **数字错**(0.15 → 0.23) |
| 2 | 28 / 159 行 LHTB | 「hidden **replay-based** verifiers / graders」 | 仓库原句:「hidden, **rebuild-from-artifact** verifiers」;并明写「**no legacy replay baseline** or verifier diagnostics are exposed」[我复核] | **措辞不成立**(且方向相反:它恰恰明确没有 replay baseline) |
| 3 | 159 行 LHTB | 「**nine** categories」 | 仓库类别表只有 **8** 类(8+6+6+6+6+5+5+4 = 46);arXiv 摘要写 nine [我复核] | **源冲突**(取 arXiv 说法可辩护,但与仓库直接矛盾) |

## 逐字成立(所以可放心引用)

| 断言 | 主源原句 |
|---|---|
| 审计:只有 39/102 GSO、11/140 SWE-Perf、411/498 SWE-fficiency 的任务在**每次**跨机重放中满足该基准**自己**的原始有效性判据 | arXiv:2607.01211 摘要逐字 [我复核] |
| 740 个优化任务、四类 Google Cloud 机 | 「replay the official reference patches for 740 code optimization tasks across four common types of Google Cloud machines」[我复核];仓库页另给机型 n2/n2d/n4/n4d |
| 排名不稳:8 份共享提交里 28 对比较有 9 对排名相反;SWE-fficiency 计分给最差十题 58.5–82.8% 权重 | 摘要逐字 [我复核] |
| METR 支出视野,2026-07-21,把性能建模为支出的函数 | METR blog 同名帖子 ✓ |
| PaperBench 8,316 条可评分任务,且**另建一个 benchmark 评它的判官** | arXiv:2504.01848 摘要 ✓(原文用 "tasks",报告写 "components") |
| τ-bench 定义 `pass^k` 与基于状态的校验 | arXiv:2406.12045 ✓ |
| KernelBench-Verified 四项:四分布隐藏测试、TF32 基线、内存指标、input-blind 生成 | 仓库原文逐条 ✓ |
| LHTB 46 任务、稠密部分分、90 分钟预算 | 仓库与 arXiv 2607.08964 均 ✓ |
| LoopX 自述「每任务每臂一次有效试验、预算不等、非等预算因果估计」 | LoopX README 原句 ✓ |
| RE-Bench 七环境、71×8 小时、61 位专家、2/8/32 小时 | arXiv:2411.15114 ✓ |
| Agent Scaling:260 配置/六基准、工具提示算力标准化、顺序规划 −70.0% | arXiv:2512.08296 ✓ |

## 链接不足以佐证(数字只在论文里,不在仓库页)

SWE-bench 2,294 原始任务 · RE-Bench 的具体小时/专家数 · GSO「102 tasks」(仓库只说 "100+") · MARBLE 的 star/chain/tree/graph 拓扑(仓库 README 未提) · Agent Scaling 的 260/六基准(仓库未提)。
另:**所引 Google Research 博客写的是 180 configurations / four benchmarks**,与 arXiv 的 260/六基准不一致 —— 报告的 260/6 只能靠 arXiv 佐证。

## 不可达

5 个 `filecite` 目标(报告作者当时上传的本地文件):`turn3file0`(recovery loss 词汇)、`turn4file0`(LoopX hierarchical-stride RFC)、`turn5file0`(LoopX LHTB 五臂数字)、`turn6file0`(**R_project = f(quantity, quality, token cost, user-attention cost) 公式**)、`turn8file0`(KernelBench-Verified 七模型研究 / shrinkage)。
其中 LoopX README 间接提到 "quantity, quality, token cost, and user attention cost",**但没给该公式**;五臂头部数字(0.4948/0.4218/0.4475)由 README 独立佐证,7/46 未独立核到。

## 归属/命名已变(链接仍有效)

`laude-institute/harbor` → 302 → `harbor-framework/harbor`;`openai/preparedness` → 302 → `openai/frontier-evals`(PaperBench 仍在其下);Harbor 的 Zenodo 记录是 v0.24.0 changelog,未提 Terminal-Bench。

## 对使用者的实际后果

引这份报告时,**只有那三处要改**(0.15×→0.23×;删 "replay-based";「九类」改「八类(仓库)/九类(论文),两源不一致」);其余关键数字可直接引用,其中审计那条我已经逐字核过,可以当作本项目至今最硬的外部评测有效性证据。
