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

**使用许可按条给出,不给全局放行**(2026-10-08 更正:此前这里写过"只有三处要改、其余可直接引用",那是全局放行句,与本文件自记的不可达 filecite、错路径相矛盾)。逐条:
- **可直接引用**:审计那条(39/102 · 11/140 · 411/498 · 740 任务 · 四类 GCP 机 · 9/28)—— 我逐字核过主源;
- **改后可用**:SWE-fficiency 0.23×(原文写 0.15×);LHTB 验证器 rebuild-from-artifact(原文写 replay-based);LHTB 类别 8/9 两源冲突;
- **需回主源才能用**:其余所有**论文内文数字**(本文件只核到编号与标题,未核正文数字);
- **不可用**:5 个 `filecite` 目标的实质内容(不可达);
- **特别提醒**:不能用 DeepSWE 的 70/113 去代替 LHTB 的 7/46 —— 两者是不同 benchmark、不同口径,各自核各自的。

---

# 追加:对话里提到的 GitHub 仓库的独立核对(2026-10-07 第二轮)

方法:`gh api repos/<owner>/<name>`(权威存在性 + 元数据)+ 取各仓 README/代码用 `gh search code` 比对。
**不请摘要器报数**(前一天它把 openai/math 的 162/185 报成 155/184)。

## 一、存在性(15 个全部存在)

| 仓库 | ★ | 备注 |
|---|---:|---|
| `openai/math` | 4664 | pushed 2026-10-06,1 个 commit |
| `loopx-project/loopx` | 6167 | pushed 2026-10-07 |
| `zli12321/LHTB` | 713 | — |
| `SWE-bench/SWE-bench` | 5985 | — |
| `ScalingIntelligence/KernelBench` | 1280 | — |
| `facebookresearch/kernel_bench_verified` | 15 | — |
| `swefficiency/swefficiency` | 26 | — |
| `sierra-research/tau-bench` | 1457 | — |
| `hkust-nlp/AgentBoard` | 448 | — |
| `MultiagentBench/MARBLE` | 58 | **fork=true**(上游为 `ulab-uiuc/MARBLE`) |
| `METR/RE-Bench` | 170 | — |
| `gso-bench/gso` | 92 | — |
| `ybkim95/agent-scaling` | 55 | — |
| `openai/mle-bench` | 1766 | — |
| `laude-institute/harbor` | 5876 | 已迁至 **`harbor-framework/harbor`** |

另:`facebookresearch/TUA-Bench`(120 任务,arXiv 2606.28480)真实存在 —— 对话里 "τ-bench / TUA-Bench" 的后半正是它。

## 二、断言逐条核(以**所引仓库自身**为准)

| 对话/报告的断言 | 核验 |
|---|---|
| LHTB:46 任务、稠密部分分、90 分钟、hidden verifiers | ✅ README 原文 |
| LHTB:**暴露 verifier-cheating 问题** | ✅ 但不在 README/论文正文里 —— 在仓内 `harbor/examples/prompts/cheating_agent.md.j2`("你的目标是利用任何方式 **CHEAT**…MUST use at least some cheating")。措辞是对话自己的 |
| SWE-bench 系 F2P/P2P | ✅ 术语真:README 没有,但 `swebench/types.py`、`harness/grading.py`、`docs/guides/datasets.md` 都有 `FAIL_TO_PASS` / `PASS_TO_PASS` |
| KernelBench:`fast_p` | ✅ README 4 处 |
| KernelBench-Verified:hidden 测试 / TF32 基线 / 内存指标 / input-blind | ✅ README 全部命中 |
| SWE-fficiency:相对专家、correctness-preserving | ✅(倍率见前文:0.23×,不是 0.15×) |
| METR 支出视野:性能-花费曲线、agent/human 交点 | ✅ |
| τ-bench `pass^k` + TUA-Bench `All-5` | ✅ τ-bench README 有 pass^;TUA-Bench 榜头就是 `Success Rate / Pass@1 / Pass@5 / **All-5**` |
| AgentBoard:success rate + progress rate + grounding + steps | ✅ progress rate / grounding 命中(README 用词略有差别) |
| MARBLE:milestone KPI、star/chain/tree/graph 对比 | ⚠️ **两仓 README 都没有**(fork 与上游 `ulab-uiuc/MARBLE` 一致,均无 milestone/star/chain/tree/graph)。该断言只由论文 arXiv:2503.01935 支撑 |
| LoopX:DeepSWE 五臂 heartbeat **70/113、61.9%、第 1** | ✅ **数字属实**,见下更正 |

## 三、更正我上一轮的错(重要)

我先前写「LoopX 仓库未给 DeepSWE 数字,7/46 未独立核到」——那是**继承了报告给错的路径**。报告的链接指向
`huangruiteng/loopx/benchmark/deepswe/README.md`,而那个文件自述是 "DeepSWE **practice**" 笔记,明确
"without publishing … unqualified score claims",**确实没有数字**。

数字在**另一个仓、另一条路径**:
`loopx-project/loopx/benchmark/deepswe-gptxhigh-v1/README.md` —— 标题 "DeepSWE Five-Arm Benchmark Harness (v1)",
五臂定义齐全(`plain` / `goal` / `heartbeat` / `codex-cli` / `ssh-goal`,113 个 SWE 任务),结果行:

```
| 1 | heartbeat | 70/113 | 61.9% | 0.9739 | 0.886 | 0.993 |
```

⇒ **对话的说法成立**(第 1 名、70/113、61.9%、五臂),**报告给了错路径**,**我的台账又沿用了报告的错误**。
这条同时也是「二手引用的路径错误会向下传染」的实例。

---

# 版本审计(2026-10-08,工具:`local2gpt/check_citations.py`)

**为什么加这一步**:第 8 轮外部复核抓到一条重错 —— 我引的一句话出自 `2607.08665` 的 **v2**,而该文 **v3(2026-09-02)
是"实质性的方法学重建"**,comments 明写那批主张「not retained」,且 v3 结论**方向相反**(没有控制器胜过固定重路由)。
我此前的核验只查了**编号与标题**,**没查版本**。

**审计结果**(对已入库材料里的 57 个编号):

- **27 篇是多版本**(`updated ≠ published`)—— 也就是说**近一半的引用天生带版本歧义**,而我此前一篇都没钉号。
- `comments` 出现修订/撤回类词的 **1** 篇:`2607.08665v3`(就是被抓到的那篇)。

**规则(自本条起生效)**:

1. 引用任何论文的**具体结论**前,先跑 `check_citations.py`,**钉版本号**(多版本的一律写 `vN`);
2. `comments` 出现 `retract / not retained / supersed / withdraw / revis / correct` 类词时,**必须回去读那一段**,不可沿用旧版表述;
3. 引用时区分三种来源并写清:**论文原文 / 对话转述 / 我们的判断** —— "它建议 X"必须有原文引语支撑,否则写成"我们的候选口径";
4. 先说清核验**范围**:我核到的是**编号与标题**(以及本节的版本),**不是正文数字**。
