# 对话记录:核对 `openai/math` 及其对 ADA/OPL 的工程启发

这份目录保存**第二条** ChatGPT 对话的文本记录。它属于 `related_files/conversation/` 那套管线的第二个实例,但主题与那条不同,故单独成目录、名字写明内容。

- 链接:https://chatgpt.com/share/6ac5e134-626c-83ee-a23f-b63a98333bce
- 标题:**「核对数学项目进展」**
- 抓取时间:2026-10-07(`related_files/conversation/decode_share.py`,HTTP 200 / 335,760 B)
- 对话跨度:**2026-10-07 02:58 → 08:42 UTC**(原四轮 02:58–05:19;2026-10-08 增量补入第 5–10 轮 06:59–08:42)
- 规模(**2026-10-08 增量后**):**567 个节点,1 个根、0 个分叉(完全线性)**;422 条消息 = 10 user + 85 assistant 正文 + 37 thoughts + 9 reasoning recap + 280 tool 输出 + 1 tool code。**首次入库时是 413 节点 / 4 user 轮**(见「增量更新」一节)

## 它为什么入库

1. **它是已入库那份报告的来源。** `related_files/deep-research-report-longhorizon-agent-eval-2026-10-07.md`
   就是本对话**第 4 轮**的产物 —— 它不是独立的外部材料。
2. **第 2、3 轮是构想的脊柱**,含构想着的原话与七条工程含义(见下),`filecite` 指向的是项目自己的 D 线报告。
3. 上游是**可撤销的分享链接**。链接一旦失效,`transcript.md` 就是唯一副本 —— 这与 `related_files/conversation/README.md` 里写的理由是同一条。

## 前四个 user 轮(逐字,不改一字;第 5–10 轮见「增量更新」)

| 轮 | 时间 | 原话 |
|---|---|---|
| 1 | 02:58 | `[$github]` 查看https\://github.com/openai/math 仔细核对和描述其每一项进展 |
| 2 | 03:24 | 对于我们的工程实践来说,重点是计算优化和agent组合优化等问题上,这会有什么帮助吗 |
| 3 | 04:24 | `[$github]` 我找到一个登顶过榜一的项目,内容其次,我们目前可能缺少的评测指标,这里给出了一些参考[https://github.com/loopx-project/loopx/](https://github.com/loopx-project/loopx/) 也许还有其他项目 |
| 4 | 05:19 | `[$deep-research]` 那么在你提到的这些关键指标上,尤其是长程任务上,其他的sota实现有哪些,他有什么参考? |

## 实体内容(首次入库时的 7 条长消息,合计 46,649 字符;增量另有 5 条)

- **第 1 轮(32,268 字符)**:逐 family 清点 `openai/math`,17 个领域、每条带 `[Lean]`/reasoning 标记。它的可核数字我全部直数复核过:**372 family(编号 001–377,缺号恰为 045/061/070/123/163)、722 manuscript、`[Lean]` 235/372、`formalization.yaml` 162 sources / 185 main-result declarations、状态 `scope: "Partial progress."` + `review: status: unchecked`、README 的十份 reasoning trace**。
- **第 2 轮(6,835 字符)**:七条工程含义 —— ①不要优化 agent 数量,而要优化"下一单位计算投向哪里";②`State —operator→ Artifact —verify→ State'`,算子集 {Explore, Optimize, Critique, Experiment, Formalize, Verify, Generalize},**"Agent 不再是系统的一等对象,research state/artifact graph 才是"**;③N_eff 与六个正交搜索算子 + `max_S E[Gain]−λC−γ·Redundancy`;④**Value of Computation 路由**(`max_a VOC<0` 即停);⑤Lean 的启示(**生成贵、验证便宜**)⇒ **Verifier Adapter Layer**;⑥**变换图搜索**(边带 Δscore/Δruntime/Δmemory/Δrobustness);⑦**reusability / fertile nodes**。
- **第 3 轮(6,259 字符)**:LoopX + 9 行「值得偷过来的指标」表(LHTB / DeepSWE·SWE-bench / KernelBench / KernelBench-Verified / SWE-fficiency / METR / τ-bench·TUA-Bench / AgentBoard / MARBLE)。
- **第 4 轮**:启动 Deep Research,即那份已入库的报告。

## 增量更新(2026-10-08)

同一条对话在首次入库后又续了 6 个 user 轮,重新分享后 **413 → 567 节点、4 → 10 user 轮**。做法:
把新链的完整记录换入本目录(`transcript.md` 2,663 → **5,500 行**;`user_turns.md` 17 → **41 行**),
旧内容**逐字保留**(见下"一处修正")。增量段的损失方式相同但更重:**337 条消息含 `redacted`**(旧段 239 条)。

**新增的六轮(逐字)**

| 轮 | 时间 | 原话 |
|---|---|---|
| 5 | 10-07 06:59 | 就LHTB这样的评测来说,对于我们关心的指标:费用,墙钟时间,通过率,目前主流的开源agent框架成绩如何?有没有相关可信结论? |
| 6 | 10-07 06:59 | (与第 5 轮**逐字相同**、同一分钟、不同节点 id ⇒ 一次重发;导出里两条都在) |
| 7 | 10-07 07:04 | 我们的场景更多关注开源的code系列,比如kimicode.qwencode(且是真开源,允许公开pr,不是像grok那样只放个只读仓库的),这方面的评测存在吗,成绩如何? |
| 8 | 10-07 07:08 | 学术前沿有没有公开可信的长程harness评测框架? |
| 9 | 10-07 07:14 | 我注意到你提及了闭源评测,那么闭源harness在我们刚才提到的方面目前前沿评测效果如何? |
| 10 | 10-07 08:42 | arixv上关于harness的前沿论文进展如何,检索梳理 |

**增量段的内容(5 条长正文,42,766 字符;我读了其中 4 条的要点与第 5 条的开头)**

- **第 5 轮(07:01)——把"harness 的经济作用"量化了,这是增量里最有价值的一段**:
  - 先拆一个坑:**LHTB 本身还不是成熟的"开源框架排行榜"**(它固定 Terminus-2、只换模型)。
  - **Scaffold Effect**(固定 Qwen 3.6 Plus / MiniMax M2.5、50 个 Terminal-Bench Pro 任务、300 次试验):Goose 通过约 38–48%、**28k–37k tokens/solved**;OpenHands-SDK 46–50%、**841k–843k**(贵约 23–30×);OpenCode 46–50%、**1.15M–1.55M**(约 41×)。而**模型层面的通过率差只有 0–8pp,多数置信区间包含 0**;平均轮数只差约 1.2× —— 成本差来自**每轮上下文膨胀、工具序列化、历史重发、空转轮**(OpenCode 每题 2.0–2.16 个 no-action turns,Goose 0.2–0.3,约 10× 的**等待税**)。
  - 它给出一句可直接引用的判断:**agent harness 目前的主要经济作用,可能不是把通过率提高很多,而是决定"为了相同的成功率,要烧多少 token、等多久、重复多少无效动作"。**
  - 并提议墙钟指标用 **`T_solved = ΣT_i / Σ1[pass_i]`**(wall-seconds per solved task),而不是简单平均每题耗时 —— 因为"15 分钟放弃、通过 20%"不能算比"50 分钟、通过 60%"更快。
  - LoopX 的 LHTB 三臂(同 GPT-5.6 Sol):Plain 0.4218 / $212.97 / **7-of-46**;Native Goal 0.4475 / $344.25 / 4-of-46;Heartbeat 0.4948 / $551.73 / **7-of-46** ⇒ mean reward +17.3% 但**严格通过数没有提升**,单题成本 $4.63 → $11.99;LoopX 自己声明这不是 equal-budget 比较。结论:**continuation 本身不是 reward,只有 continuation → verified progress 才是 reward。**
  - Harness-Bench 上的开源框架:NanoBot 81.6% / 68.7k tokens per task;Hermes 80.4% / 139.7k;Moltis 78.4% / 134.9k。
- **第 7 轮(07:05)——"真开源"的对照**:Qwen Code 最干净(framework 与模型均开源、接受外部 PR);它用 **SWE-bench Verified 500 题 × 3 次**做**框架回归测试**(固定 Qwen 3.7 Max),七个版本的平均分只有 **76.40–77.80%**、pass³ **65.8–69.2%** ⇒ 框架版本间的差别很小。Kimi Code 现为 MIT 真开源(旧 `MoonshotAI/kimi-cli` 已于 2026-09 归档),但治理更严:外部 PR 只收维护者预先批准的 bug fix,**不收外部 feature PR**。它给出一句锋利的区分:**`forkability ≠ upstreamability`** —— 想改 harness 并最终 upstream,Qwen Code 更适合当实验宿主;Kimi Code 更适合 fork 后研究。
- **第 8 轮(07:09)——学术长程 harness 评测**:还没有 SWE-bench 那样的公认标准榜;目前可信做法是拼装:**Harness-Bench**(隔离 harness)+ **LHTB / WeaveBench**(真长程任务)+ **AgentCompass / Inspect**(统一执行与记录)+ **Scaffold-Effects**(成本归因)+ horizon-residual / trajectory-attribution(机制诊断)。
- **第 9 轮(07:14)——闭源 harness 的"上限实验"**:**METR 的受控长程对比**发现,产品级 scaffold(Claude Code / Codex)对 Opus 4.5 与 GPT-5 **没有统计显著优势**(Claude Code 胜过 ReAct 的 bootstrap 样本仅 50.7%;Codex 胜过 Triframe 仅 14.5%)⇒ **`product sophistication ⇏ autonomy horizon`**;并观察到典型长程失效(过早锚定 plan、预算浪费、走到 checklist 末尾才发现路线不对却不愿回滚)。而绝对成绩上( Terminal-Bench 4.0)Claude Code + Opus 5.5 (max) 64.8%±3.1%、Sonnet 5.5 61.8%、Fable 5.1 57.9%、GPT-6 Astra + Codex 58.2%、Grok Build 37.6%。
- **第 10 轮(08:43,13,906 字符)——harness 文献综述**:主线是 `Harness matters → measure → optimize → evolve → question whether evolution generalizes`,另有一条正在汇合的线 `context management → external state → verification → recovery → long-horizon control`。**这一轮的题目与第三条已入库对话(「梳理Harness前沿论文」)的首轮逐字相同,时间早一小时** ⇒ 那条对话是**同题另开的新会话**(见 §4 去重)。

**一处修正(增量顺带修掉的)**:旧快照的最后一条消息(节点 `57850cd6`,`len=196`)把 UI 的**追问建议**(“If you want, I can: - 继续分析数论… - 列举代数与复几何… - 详细罗列理论计算机方向亮点”)**粘进了正文**;新导出里同一条是 `len=117`、没有那三行。⇒ 该节点以新导出为准,**旧快照多出的三行是导出残渣,不是对话内容**。

## 引用核验(2026-10-07)

- **仓库层**:对话点到的 15 个仓库全部存在(`gh api` 核对;`laude-institute/harbor` 已迁至 `harbor-framework/harbor`,`MultiagentBench/MARBLE` 是 **fork**)。逐条断言见 `related_files/deepresearch-citation-ledger-2026-10-07.md` 的「追加」一节;**唯一一条不受所引仓库支撑的是 MARBLE 的 star/chain/tree/graph 与 milestone KPI**(只在其论文 arXiv:2503.01935 里)。
- **filecite 层**:7 处 `filecite turn29file0` 指向项目自己的 D 线报告(在 `related_files/agent_engineering_science_repro_bundle.zip` 内的 `agent_engineering_science_report.tex`,433 行)。其行区间是**上传件**的行号(该 `.tex` 的 5–13 行只是 `\usepackage`),所以按**内容**核对:N_eff/"有效独立证据数"(该文件 :155)、七个理论域(:34)、metalevel MDP(:116)、exp2 metareasoning(:38)全部命中。

## 已知的信息损失(**与上一条对话不同,而且对溯源更糟**)

- **337 条消息含 `redacted`(首段 239 条,增量段新增 98 条,也即 280 条 tool 输出几乎全在其中),各只有 39 字符。** 也就是说,GitHub 连接器**取到的仓库原文不在分享载荷里**,只有模型的转述留存。想复核它读过什么,只能回到仓库本身(这一次我们都这么做了)。
- 上一条对话的损失方式是 **tool 输出被截到恰好 20000 字符**(6 条);本节这条**没有**任何消息正好 20000 字符,所以那种截断在这里不适用。

## 如何重建

```
python3 related_files/conversation/decode_share.py https://chatgpt.com/share/6ac5e134-626c-83ee-a23f-b63a98333bce <outdir>
```

## 这里有什么

| 文件 | 行数 | 是什么 |
|---|---:|---|
| `transcript.md` | 5,500 | 全部 413 节点按链序的文本,含角色、内容类型、时间戳、节点 id。**我读了其中 8 个实体块(4 user + 4 条长正文),计 1,306 行**;其余 334 块几乎都是 redacted 占位 |
| `user_turns.md` | 41 | 4 个 user 轮全文 |
| `README.md` | 本文件 | provenance 与核验 |

## 这里刻意没有什么

`mapping.json`(951 KB)、`outline.md`(4.8 KB)、原始 HTML(336 KB)、扁平数组(12,440 值)—— 全部可由 `decode_share.py` 从链接重建;`digest.md`(我抽长正文做的 47 KB 摘录)也可以同一规则重建。与 `related_files/conversation/README.md` 的取舍一致。

**但前提条件与那些情况不同**:上游是可撤销的分享链接,不是持久的远端。链接失效后,`transcript.md` 就是唯一副本 —— 这是它入库的理由。
