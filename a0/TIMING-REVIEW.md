# H_T：把"外部信息有没有价值"降为前提、只研究"何时获取"——独立审查 v2

日期：2026-09-23（v2，同日晚，吸收对 v1 的审查）· 仓库 `HEAD = 4a5f71c7` · 被审查对象：把主假设从 `H_O`（OpenWorld > ClosedWorld）换成 `H_T`（自适应获取时机 > 固定时刻获取）的提案。

**本报告的目的**：为外部复核提供可核对的证据基础 + 我的独立判断 + 提案没写但决定成败的工程事实。v2 与 v1 的差异**全部**在 `§0.2` 与 `§8.5` 列出，包括 v1 自己写错、以及 v1 的攻击清单里已经预先标记出来的两条。

**标注约定**：【反馈】= 来自对 v1 的审查（我接受）；【我的补充】= 我在其基础上加的，需要你或复核者再判断；【v1 错误】= v1 的表述被推翻，列在 `§8.5`。

---

## 0. 摘要

### 0.1 现在的结论

| # | 判断 | 一句话 |
|---|---|---|
| 1 | **方向成立，且是经典问题的一个新实例** | 这是 rational metareasoning（把"继续内部计算"与"获取信息"都当作有成本的 meta-action）在**长程、有 verified progress 的研究轨迹**上的实例。仓库里已有它的一个**静态切片**（强度曲线） |
| 2 | **三个门，不是一个**【反馈】 | `G_1` Artifact Efficacy、`G_2` Residual Headroom、`G_3` Agent Nonredundancy。`G_1`/`G_2` 对 `k=10` **已经量过**（Δ 0.116584858、ρ 0.615639328）；`G_3` 完全没测 |
| 3 | **主估计量 = 同预算下的策略价值差**【反馈】 | `Δ_T = V_B(π_adaptive) − max_{π∈Π_fixed} V_B(π)`，其中 `V_B(π) = E[J_best(B;π) − J_0]`。不引入人为的 `λ`；`Y(τ)` 升为独立的 `B0a` 阶段，而不是"诊断" |
| 4 | **不补 adaptation 配额**【反馈】 | 晚 reveal 之后剩下的时间少，这**就是** timing 的机会成本，不是 confound。改为 `τ ∈ [0, B−C_min]`、`τ/B ∈ {0,.2,.4,.6,.8}`、所有臂总预算严格等于 `B` |
| 5 | **第一代策略要比 v1 简单得多**【反馈】 | `s_t = (r̂_t, ℓ_t, b_t)`，三个量全部 harness-authoritative；`π: Retrieve iff r̂_t<θ ∧ ℓ_t>k ∧ b_t>C_min`。`D_t/F_t/S_t` 留作后续 ablation |
| 6 | **预训练通道是 manipulation failure，placebo 修不了**【反馈】 | `PriorKnowledgeProbe ≠ PlaceboControl`。流程改为"先测 `P_recover`，太强就换 packet" |
| 7 | **一个隐藏前提（v1 的承重发现，仍然成立）** | 今天 T1 的 coding lane **能直连公网**，且拟用的 packet **就在工作区里**（4 条可读路径）→ "封闭臂"当前**不存在**，机制 A 是 `B0` 的前置条件 |
| 8 | **一个 v1 没想到、我认为会决定任务选择的风险**【我的补充】 | T1 的机制空间（Max-Cut 启发式）是**预训练最密集**的那一类，`G_3` 可能在 T1 上**结构性地难以满足**。见 `§4.3` |
| 9 | **成本判断反转** | 钱不是约束（`N=136` ≈ $70–80），**墙钟是**（68 h @ `P_concurrency=1`）。`R=10/16/34` 这组功效数字**不在仓库里** |

### 0.2 v1 → v2 的修改

| v1 的位置 | v1 的说法 | v2 |
|---|---|---|
| §3.2 | "门 B（非冗余）**就是** ρ 门" | **【v1 错误】** 两者不同构。ρ 测 `(R−J_X)/(R−J_0)`，是"工件是否把 assay 吃光"；它**完全不描述** agent 能否自己发现 X。改为三门前置（`§3.2`）；v1 的攻击清单第 1 条已预先标记此风险 |
| §3.2 | "Δ=0.1166 是 agent 照抄时的**下界**" | **【v1 错误】** 它只是 `J(reference implementation of X)`。agent 可能理解不全（低于它），也可能在其上继续改进（高于它）→ 既非下界也非上界。v1 的攻击清单第 2 条已预先标记 |
| §3.1 | "`E[V]>0` 不带任务限定在本任务是**假命题**——它把可测空间吃光了" | **【v1 错误，逻辑颠倒】** 吃掉 82.6% 差距说明 `X` **非常有价值**；失败的只是它作为 timing assay 的 intervention。`ArtifactValue ≠ AssaySuitability`。修正见 `§3.1` |
| §3.3 | 主估计量写成 `VerifiedGain − λ·Cost` | 去掉 `λ`。同一硬预算下的 `J_best(B;·) − J_0` 就够（`§3.3`） |
| §3.4 | "τ 必须预留显式 post-reveal adaptation 配额" | **【v1 错误，方向反了】** 那会消掉 timing 最有意思的那部分成本。改为固定总预算 + `τ/B` 网格（`§3.4`） |
| §3.5 | "给 `s_t` 的每个分量写明 authority"，仍含 `D_t,F_t,S_t` | 更好的修法不是"规定 authority"，而是**把它们从第一代里去掉**（`§3.5`） |
| §4.2 | "加 placebo 臂 + 把预训练通道标 `UNCONTROLLED`" | 不够。`K_{τ^-} ≈ K_{τ^+}` 是 treatment manipulation failure，placebo 测不到它。改为先做 `PriorKnowledgeProbe`（`§4.2`） |
| §5 | "B0 的最小可执行形态" | 改为阶梯 `A1 → G_1/G_2/G_3 → B0a → B0b → B1`，带**失败定位**性质（`§5`） |
| §9 | 三个请求问的是 v1 的两条错误判断 | 换成三个新请求（`§9`） |

---

## 1. 方法与可靠性

- 证据由 **6 个互不相通的只读调查者**分别建立，每人只回答一个问题，每条断言都要求 `path:line` 与原文。他们只被允许读，不许改仓库、不许调 API、不许跑门或评测。
- **我亲自复核了承重条目**（`§8.2` 列出）。其余是**二手证据**（调查者的 `path:line` + 引文），在 `§8.1` 逐条标注来源；未标"我复核"的即未被我二次核对。
- 所有数字都可从仓库复现；本报告**不包含任何未执行的主张**；`§8.4` 明确列出**我没有验证**的东西。

---

## 2. 事实基础

### 2.1 A1 现在的状态（我复核过）

| 门 | dev（裁决集） | eval（诊断） |
|---|---|---|
| Δ 均值 ≥0.03 且 ≥3/4 族 ≥0.02 | 通过 0.116584858，4/4 族 | 通过 0.116426731，4/4 族 |
| ρ 中位 ≥0.30 且 ≥3/4 族 ≥0.30 | 通过 `2417/3926` = 0.615639328，4/4 族 | 通过 `709/1180` = 0.600847458，4/4 族 |

判定文件 `a0/tasks/maxcut/gates/verdict.{dev,eval}.pc_exchange_k10.json` = `ADMISSIBLE`。已废的无界正控（`positive_control/pc/`）仍在 `verdict.{dev,eval}.json` 记 `NOT_ADMISSIBLE`（ρ **0/4 族**），可用 `--pc positive_control/pc` 复现。**阈值、套件、`gate_config.json`、`E*` 均未改动**；`restamp` 报 924/924 current、0 stale，`refreeze` 报 CLEAN。第 8 项（8 个 campaign）**仍未运行**，`R_A1^main = ∅`。

### 2.2 泄漏：agent lane 今天不封闭（v1 的承重发现，仍然成立）

| 档位 | 可达 / 50 | 出站 TCP | 备注 |
|---|---|---|---|
| codex `danger-full-access` | 48/50 | **可以**（`TLSv1.3` 到 `api.deepseek.com:443`、`1.1.1.1:53`） | **T1 的 `coding_agent` 就是这一档** |
| codex `workspace-write` | 40/50 | 不可以（`PermissionError: Operation not permitted`） | 与 `read-only` **全部 50 格逐一相同** |
| codex `read-only` | 40/50 | 不可以 | 同上 |
| candidate sandbox | 5/50 | 不可以（`Network is unreachable`） | 只对**候选**有效，不是对 agent |
| 宿主（对照） | 48/50 | 可以 | — |

三档对**读**都不设限。最尖的一条：`a0/a1/epistemic-probe/REPORT.md:221` 记 `cut(assignment) = 217 ; targets.json: R=217 OPT=217 U=217 role=eval`；那个划分来自 git 历史里的 blob `9020082d`（332 B），原路径 `a0/tasks/maxcut/references/logs/partitions/G_eval_0001__BURER2002__s1337.partition.json`——**已删除、仍在历史里**。

残余：lane 内**环境变量可见**（canary key 的**名字**在所有档位含命名空间内可见）；candidate sandbox 里 `AF_UNIX` 可 `CONNECTED`（含 `/var/run/docker.sock`）、`/dev/shm` 可读且与宿主同摘要；**claude lane 在 Linux 没有 OS 沙箱**（该列 UNPROVEN）。

**T1 今天三条角色**（`a0/a1/kapso_t1/config/mode.maxcut.yaml`）：`coding_agent` `sandbox: "danger-full-access"`（:72）、`feedback_generator` 与 `evaluation_maintainer` `sandbox: "read-only"`（:81、:90），三者 `web_search: false`。

> **两条推论**：① `web_search: false` 关的是**工具**不是 TCP ⇒ **"ClosedWorld 臂"当前不存在**（既不封闭文件系统，也不封闭网络）。② 拟用的 packet 已经在工作区里。

### 2.3 拟用的 packet 已经在工作区里（4 条可读路径）

pinned 上游文件 `networkx_maxcut_b69beb2c.py`（sha256 `793419aa…`，BSD-3-Clause）在四处字节相同，其中两处被 git 跟踪：

- `a0/tasks/maxcut/positive_control/pc/pinned/`（跟踪）
- `a0/tasks/maxcut/redesign/frozen_mirror/pc/pinned/`（跟踪）
- `a0/tasks/maxcut/positive_control/e-star-state/pc_dev/candidates/d3c12b54999415a1/pinned/`（存在，gitignored）
- `a0/tasks/maxcut/redesign/out/e-star-state/l1-pc/candidates/d3c12b54999415a1/pinned/`（存在，gitignored）

### 2.4 机制 A 与机制 C 的真实成熟度

| | 机制 A（`unshare` 挂载命名空间） | 机制 C（容器） |
|---|---|---|
| 结论 | **可行**；实跑通过 | **可行**；实跑通过 |
| 封闭证据 | repo / `.git` / key / `targets.json` / `commitments.json` / `G_eval_0001.json` 全部 `FileNotFoundError`；`/home`、`/tmp` 空；git 路线 `executed:false`；**只有 meter 可达** | 21 条实验者专属路径 **0 条可开**；正对照（walk/read control、canary 可见）通过 |
| 计量证据 | 账本行 `ceq=1020`（codex）、`17399`（claude）、`397`+`424`（resume）；合计 20260；附加延迟中位 `0.051 s` | 15 行、4 metered、11 unmetered、合计 **2634 CEq** |
| 接线状态 | **只写了 diff，未接线**（`REPORT.md:17,42,230`；`git status` 干净） | 未接线；其 diff 要把**两个角色**从 `read-only` 改成 `danger-full-access`（**仍未改**） |
| 长会话 | **未跑**（实测会话 1.1–2.5 s 一轮；`REPORT.md:320` 自认只测了 invocation shape） | **未跑**（`REPORT.md:572` 自认） |
| 已知坑 | 宿主 proxy 必须清；lane 内必须 `danger-full-access`（`workspace-write` 在 netns 里开不出 socket）；**强制点在启动处的 PATH shim，不是内核** | 容器里 `bwrap` 不可用 → codex 自带沙箱崩 → 只能 `danger-full-access` |

**哪条路更短：A**——但 A 也**不是 production-ready**：强制点未证明不可绕，长会话未跑（见 `§5.4`）。

### 2.5 强度曲线：仓库里唯一的"外部工件强度"测量（我复核过，0 分歧）

`a0/tasks/maxcut/gates/strength_table.json`（用 12 份 verdict 全字段重算，**0 差异**）：

| 控制 | k | dev Δ | dev ρ | dev 族 | dev | eval Δ | eval ρ | eval 族 | eval |
|---|---|---|---|---|---|---|---|---|---|
| `pc` | ∞ | 0.247942608 | 0.158819629 | 4/4, **0/4** | NOT | 0.238448095 | 0.178715729 | 4/4, **0/4** | NOT |
| `k01` | 1 | **0.018221497** | 0.940123488 | **1/4**, 4/4 | NOT | **0.017982784** | 0.942883023 | 1/4, 4/4 | NOT |
| `k02` | 2 | 0.032882006 | 0.895644283 | 4/4, 4/4 | ADM | 0.033074123 | 0.894196025 | 4/4, 4/4 | ADM |
| `k05` | 5 | 0.069657568 | 0.775149080 | 4/4, 4/4 | ADM | 0.070199653 | 0.762308313 | 4/4, 4/4 | ADM |
| `k10` | 10 | 0.116584858 | 0.615639328 | 4/4, 4/4 | **ADM** | 0.116426731 | 0.600847458 | 4/4, 4/4 | **ADM** |
| `k25` | 25 | 0.204898135 | 0.325902583 | 4/4, 3/4 | ADM | 0.202023485 | **0.301162791** | 4/4, **2/4** | NOT |

随表两条：**已发表的 greedy 构造同样过不了 ρ**（Δ 0.22871009、ρ 0.23993558、0 族）；**提高 n 不是答案**（`ER:p080` 的 ρ 随 n 单调降到 0.1298，`n_where_rho_passes: []`；无界正控在 n≥512 超时）。

这张表被明确限定为**仪器属性**："ρ 是 assay 的属性，MUST NOT 被当作关于世界的证据"（`positive_control/PC-REVISION.md:165-166`；`a0/A1-RESULT.md:65`）。

### 2.6 "何时获取"在这个仓库里**不存在**

对 `retrieve / when to search / VOI / value of information / timing / plateau / stopping rule / SearchWorld / OpenWorld / acquisition timing / meta-reason / 何时 / 时机` 的全仓检索：所有命中都是关于**"是否"**，没有一条关于**"何时"**（`a0/A1-REQUIREMENTS.md:21,34`；`a0/STATUS.md:23`；`a0/EPISTEMIC-REVIEW.md:22,27,122,134,213`；`a0/mrc/SPEC.md:12`）。`stopping rule` 只出现在标定的统计规则里；`plateau` 只出现在一条 A0 agent 日志里；`retrieve` 只作为闭包禁令（`a0/contract/adapter_contract.md:847`）。机制 A/C 的探针只处理**可达性**。

⇒ 这是**新问题**，不是重发现；也意味着**没有现成仪器**，`§5.3` 的清单是净新增。

### 2.7 成本（我复核了 `B_hard` 与换算）

`T_wall_sec = 1800`、`CEq_max = 1966519`、`N_evaluatorCalls = 725`、`P_concurrency = 1`；实测速率 `A_simpleloop 52440.489 CEq/min`、`A_kapso 21323.491 CEq/min`；`CEq_max/q_r` = 37.50 / 92.22 min，**都晚于 30 min 墙钟** ⇒ 墙钟是设计上的主约束。

| N 个 campaign | 墙钟（顺序） | CEq @ 上限 | CEq @ simpleloop 实测 |
|---|---|---|---|
| 8 | 4 h | 15 732 152 | 12 585 717 |
| 20 | 10 h | 39 330 380 | 31 464 294 |
| 40 | 20 h | 78 660 760 | 62 928 587 |
| 80 | 40 h | 157 321 520 | 125 857 175 |
| 136 | 68 h | 267 446 584 | 213 957 197 |

按契约冻结的 Flash 高峰价格归一（`300k CEq ≈ $0.09` ⇒ `1 CEq = 3e-7 USD`）：`N=40` → **$19–24**；`N=136` → **$64–80**。

`R = 10 / 16 / 34` **不在仓库里**（正则 `\bR\s*=\s*(10|16|34)\b` 与 `git log -S` 均无命中）。它们必须先进预注册文件。仓库对 `R=4` 的唯一说法是 `a0/A1-CONTRACT-AUDIT.md:13,119`——**qualification replication，不是 inferential sample size**；且 ≥3/4 判别力很弱（真值 0.5 时通过率 5/16 = 31.25%，0.7 时 65.17%）。**为什么定 4，仓库没给功效依据。**

### 2.8 相关工作（2026-09-23 补齐。v1 只读过 FLARE 的摘要；现已读过下面全部，并**亲自抓取核对了 5 篇的页面**，其余按标注区分）

**（a）形式上的家：rational metareasoning / value of computation**

- Russell & Wefald, *Principles of metareasoning*, AIJ 49(1-3):361-395, 1991（DOI `10.1016/0004-3702(91)90015-C`，书目经 DOI 内容协商核对）。meta-level 动作按 **expected value of computation** 打分：`V(S_j) = U([S_j]) − U([α])`，即"相对默认外部动作的效用增量"。
- **已知病理**：理想的 meta-level 控制是对**含后续**的价值贪心（非 myopic）；可实现的 single-step 版本会失手，R&W 自称 **"meta-greedy barrier"**。
- **修法**：Hay, Russell, Tolpin & Shimony, *Selecting Computations: Theory and Applications*, UAI 2012（arXiv:1207.5879，摘要已核对）。myopic 策略"often stopping far too early"；改为 **blinkered policy**——时间上可非 myopic，但一次只沿一个分支看（`Q^m ≤ Q^b ≤ Q*`）。
- **对我们第一条用处**：R&W 把**外部信息获取排除在 meta-level 动作之外**（只在脚注里说"information-gathering experiments 的理性规则与 computations 同构"）。所以我们的问题不是"应用 R&W"，而是**把它的 meta-level 动作集扩到外部获取**。
- **对我们第二条用处**：`r̂<θ ∧ ℓ>k → 去查` 正是 **depth-limit-1 的 meta-greedy 策略**。这给第一代 trigger 一个**有名字的失效模式：它会低估获取的价值**。`B0b` 的 ablation（加 `D/F/S`）在文献上对应的正是"从 meta-greedy 走向 blinkered"。

**（b）何时检索：在 QA 里已经被研究过了**

| 工作 | state / trigger | 动作 | 可逆 | 测过 timing |
|---|---|---|---|---|
| FLARE（Jiang et al., EMNLP 2023） | 预测下一句的 **token 概率**（低于 θ 触发） | 检索并重写该句 | 可重复 | 只扫 θ（触发比例 30–60%），**未测早晚** |
| Self-RAG（Asai et al., arXiv:2310.11511，摘要已核对） | 模型自生成的 **reflection token**（三元 `Retrieve{No,Yes,Continue}` 属二手，我未核对） | 按段检索，可"继续用证据" | 可重复 | 只测有/无与频率 |
| DRAGIN（Su et al., ACL 2024） | token 熵 × 最大注意力 × 语义指标 | 触发检索并重建 query，**可替换**已有证据 | 可逆 | 未测 |
| SKR（Wang et al., Findings EMNLP 2023） | 模型"是否见过类似问题"的自知识 | 检索或不检索 | 可逆 | 未测 |
| Adaptive-RAG（Jeong et al., NAACL 2024） | 小分类器预测 **query 复杂度** | 无/单步/迭代检索 | 可逆 | 未测 |
| IRCoT（Trivedi et al., ACL 2023） | 每个推理步 | 每步检索 | 可逆 | 未测 |
| **ReaLM-Retrieve**（Guo et al., SIGIR 2026, arXiv:2604.26649，**摘要已核对**） | **step 级不确定性检测器** | 学习"何时注入证据最有用"的**干预策略** | 可逆 | **测了**：相对固定间隔（IRCoT）检索次数 −47%、F1 +10.1 |

⇒ **"自适应何时检索优于固定间隔"在 QA 里已经有结果**（ReaLM-Retrieve）。所以 novelty 不能再写成"首次研究何时检索"。

⇒ 两条对我们有用的先验：**Budget-Aware Active RAG**（arXiv:2607.24010，摘要已核对）把检索价值定义为"**相对 no-retrieval 答案的边际正确率变化**"——这正是我们 `g(τ)=E[Y(τ)−Y(∞)]` 的形状；并且它报 "**retrieval harm is non-negligible**"、且发现"**简单的 uncertainty / 检索分基线常常与学习型 utility router 打平**"。后者**直接支持**我们"第一代只用三个 harness 量的策略"这个选择。

**（c）agentic search-RL：学了"要不要/何时"搜，但不给搜索定价**

Search-R1、ReSearch、WebThinker、Search-o1、R1-Searcher 都含"不搜"的决定（Search-R1 的提示词允许判断"no further external knowledge needed"后直接作答），但**奖励里没有搜索成本**：Search-R1 / ReSearch 只给答案分；WebThinker 只在偏好数据里"工具调用少的优先"；R1-Searcher 在 Stage 1 **奖励去搜**（`n≥1` 得 0.5）。（以上均为调查者读全文所得，**我未核对**。）

**（d）算法发现：最近的邻居是 DeepEvolve**

- **DeepEvolve**（Liu et al., arXiv:2510.06056, 2025-10-07，**摘要已核对**）："integrates deep research with algorithm evolution, uniting **external knowledge retrieval**… under a feedback-driven iterative loop"。它的摘要还写了**我们 `r_I` 衰减前提的经验版**："Pure algorithm evolution… depends only on the internal knowledge of LLMs and **quickly plateaus** in complex domains"。它做"外部检索 on/off"的消融（所以"外部知识有没有用"在算法发现领域**也已经被量过**），但**每一轮都检索，不变化引入的时刻**。
  （该文正文自称"constrained to a 30-minute time budget and a single GPU"——这句**摘要里没有，我未核对**。）
- FunSearch / AlphaEvolve / AIDE / OpenEvolve **没有获取动作**；AlphaEvolve 把"相关文献"作为**静态 prompt 上下文**。（二手。）

**（e）结论：novelty 必须收窄成三层**

- 不是"外部知识有用"——DeepEvolve 已示，我们的强度曲线也已示（`§2.5`）。
- 不是"何时检索"本身——ReaLM-Retrieve 已在 QA 示。
- 而是：**长程算法发现中的、一次性不可逆的获取；其价值被离线量测；判据是冻结预算下的策略价值差，且 state 来自 harness 的 verified-progress trace。**

我**没有找到**同时具备这三点的先前工作（检索清单与"未找到≠不存在"的限制见 `§8.4`）。

---

## 3. 判断

### 3.1 把 `Q_1` 降为前提——理由要写对

**修正 v1 的逻辑错误。** v1 写过"完整 `one_exchange` 吃掉 82.6% 差距，所以'外部信息有价值'在本任务是假命题"。这是**颠倒**：吃掉 82.6% 说明

$$
V(X)\ \gg\ 0,
$$

失败的是它作为 **timing assay 的 intervention**（ceiling effect 太强）：

$$
\boxed{ArtifactValue(X)\ \neq\ AssaySuitability(X).}
$$

这两个量从此必须分开。于是前提可以**原样保留**，并在 `B0` 上更强——`V(X)>0` 直接成为 **intervention 的准入条件**（`G_1`），我们不再用它去证明任何东西。

**【我的补充】** 本任务的 ρ 还**低估**了 `X` 的可能价值：`references/targets.json` 里只有 42/60 图被 SCIP 认证最优（`a0/A1-RESULT.md` §1 第 3 项），其余 18 图的 `R_i` 只是下界，所以 "`J_X = R`" 在这些图上不构成 `X` 的价值上界。

`A_O` 的正确形式仍要带任务限定，否则 `B1` 的估计量又会变成条件性的（这是上一轮 `KID/EKR` 争论里的同一个洞）：

$$
A_O:\quad \exists\,\text{任务分布}\ \mathcal D,\ \exists\ \text{packet}\ X:\ E_{T\sim\mathcal D}[V(X,T)]>0 .
$$

### 3.2 三个门（【反馈】，取代表 v1 的"两个门"）

`G_1` 测工件内在有效性，`G_2` 测剩余空间，`G_3` 测 agent 级的信息处理效应：

$$
G_1:\ J_X-J_0\ \ge\ \delta_{\rm artifact}
$$

$$
G_2:\ \rho_X=\frac{R-J_X}{R-J_0}\ \ge\ \rho_{\min}
$$

$$
G_3:\ \Delta_X^{\rm agent}=E\big[Y(X@0)-Y(X@\infty)\big]\ \ge\ \delta_{\rm agent}
$$

**为什么 `G_3` 的定义优于 v1 的"内部达不到 `J_X`"**：它直接测 causal treatment。若模型已从预训练知道 `X`，或内部十分钟就重新发明它，则 `Y(X@0) ≈ Y(X@∞)`，自然 FAIL；若 packet 很好但 agent 不会读、不会适配，也 FAIL。两种原因不同，但对 timing 实验意味着同一件事：**`X` 没有形成可操纵的信息处理效应**。

准入条件是 `G_1 ∧ G_2 ∧ G_3`。

**关键事实：`G_1`/`G_2` 对 `k=10` 已经量过**（Δ 0.116584858、ρ 0.615639328、4/4 族，`§2.5`）——**它们不花钱**。真正没测的是 `G_3`。

**【我的补充 — 一个结构性问题】** 按上面的定义，`G_3 ≡ g(0)`，即它在**数值上就是 `B0a` 曲线的 0 端点**（`B0a` 的 `g(τ) = E[Y(τ) − Y(∞)]`）。所以 `G_3` 不可能既是 `B0a` 的**前置门**、又是被 `B0a` 测出来的东西。两种自洽的组织方式：

- (a) `G_3` 作为一次**便宜的两臂 pilot**（`X@0` vs `X@∞`，同一 campaign 预算），通过后再跑 `B0a` 的六点曲线；预注册必须写明 `g(0)` 复用这批数据（否则就是 harking）。
- (b) 把 `G_3` 并入 `B0a`，`B0a` 的第一条判据就是 `g(0) ≥ δ_agent`；那时 `G_1∧G_2` 是唯一的"先验准入"。

我倾向 (a)（更便宜的 kill-test），但这需要复核者确认它不构成"同一数据两次使用"的问题。

### 3.3 主估计量（【反馈】）

去掉 v1 的 `λ`。冻结的 `B_hard` 已经给了硬约束，所以最干净的主量是**同一硬预算下的最终 verified progress**：

$$
V_B(\pi)=E\big[J_{\rm best}(B;\pi)-J_0\big]
$$

$$
\boxed{\ \Delta_T\ =\ V_B(\pi_{\rm adaptive})\ -\ \max_{\pi\in\Pi_{\rm fixed}} V_B(\pi)\ }
$$

在相同 `Task, Model, Evaluator, Packet set, Budget` 下；`Π_fixed = {Retrieve@αB}` 网格。**secondary** 报告 `Cost`、`AUC[J_best(c)]`、`CostToThreshold`、`FailureRate`。这样不需要假装知道"一分算法改进值多少钱"；只有当以后真研究 `Stop` 时，才把 `(J_final, C_consumed)` 作为 Pareto outcome，或引入真实经济效用下的 `λ`。

### 3.4 不补 adaptation 配额（【反馈】，v1 方向反了）

v1 主张"晚 reveal 必须给独立 `C_adapt` 配额，否则必然输，那测的是预算不足"。**这会把 timing 最有意思的成本消掉。** 若 `B=30 min` 而我在第 29 分钟才去查，只剩 1 分钟适配——**这正是"等太久"的真实机会成本**，不是 confound。正确做法：

$$
\tau\ \in\ [0,\ B-C_{\min}],\qquad \tau/B\in\{0,\,.2,\,.4,\,.6,\,.8\}
$$

所有臂总预算严格 `= B`；`C_min` 只保证 intervention 有**最小可解释窗口**。

**【我的补充 — 两种读法不要混】** v1 那个"固定 adaptation 时间"的版本其实对应**另一个、合法的**问题：

- **主量（本报告）**：`V_B(π)`——"在硬预算下选时刻"，总预算固定，晚 reveal 自然少时间。→ 回答"策略好不好"。
- **次量（可另做）**：`VOI(τ) = E[Y(τ) − Y(∞)] | post-reveal 时间固定`——回答"信息本身在时刻 τ 值多少"。它能把"信息到得太晚"与"没有时间用它"分开。

两者**都合法但不能混**：把次量的结论当成主量的结论，就等于替 agent 把"太晚"这个错误免掉了。

**【我的补充 — placebo 必须成本匹配】** 由于读文件本身消耗预算，`Y(τ)` 里含**读取成本**；一个 worthless 的 packet 也会让 `g(τ) < 0`。所以 placebo 必须在**字节量/读取开销**上与真 packet 匹配，否则曲线被读取成本污染。

### 3.5 第一代策略：三个量就够（【反馈】）

v1 提 `s_t = (v_t,a_t,D_t,F_t,S_t,B_t)`；**太多了**，且 `S_t` 会把 agent 自报重新引进 measurement chain。第一代只用 harness 天然拥有的 score/cost trace：

$$
H_t^E=\{(c_i,J_i)\}_{i\le t}
$$

$$
\hat r_t=\frac{J^*_t-J^*_{t-k}}{c_t-c_{t-k}},\qquad
\ell_t=c_t-c_{\text{last improvement}},\qquad
b_t=B-c_t
$$

$$
\boxed{
\pi_{\theta,k}:\ Retrieve\iff \hat r_t<\theta\ \land\ \ell_t>k\ \land\ b_t>C_{\min}
}
$$

**性质：所有触发变量都是 harness-authoritative。** 没有 embedding、没有 agent 自评、没有 LLM judge。先回答一个问题：

> 仅凭内部 verified progress 的衰减，能不能比固定时钟更好地判断检索时机？

若连这个都不成立，就没有理由先做复杂 metacognition。成立后再依次加 `D_t → F_t → S_t`，本身构成 ablation chain。

**【我的补充 — 一个会让这族退化成一维的陷阱】** 若 `J*_t` 是**best-so-far**（单调不减），那么

$$
\hat r_t<\theta \quad\Longleftrightarrow\quad
\text{"最近一个窗口内没有改进（或改进 < }\theta\cdot\Delta c\text{）"}
$$

而 `ℓ_t>k` 是"最近 k 个成本单位没有改进"。**两者高度相关，`π` 近似退化成单个 plateau 检测器**，而不是"生产率衰减"检测器。要保住"衰减 vs 平台"这个区分，必须显式把**幅度**与**时间**分开：例如 `r̂` 的窗口里用**残差幅度阈值** `ε_J`（把 `< ε_J` 的改进视作噪声），并让 `ℓ_t` 只在**无任何** `≥ε_J` 改进时增长。否则 `θ` 与 `k` 只是同一个阈值的两种单位。

**【我的补充 — 参数不能从自己的结果里调】** `θ, k, C_min` 必须**预注册**；`B0a` 的 `g(τ)` 曲线是唯一允许用来**设定**它们的先验信息（例如曲线在 `.4B` 之后不再有增益，就给"太晚"一个上界），不得用 `B0b` 自己的 outcome 回调。

### 3.6 `R` 留在 measurement side

"`R` 不再是必要状态变量"对 **policy** 成立；对**实验者**不成立：没有 `R` 就无法知道任务有没有动态范围、`g(τ)` 是否可测、ρ 是否在窄带里。与仓库已写的 `evidence_scope: instrumentation` 一致。

### 3.7 `dr_E/dt > 0` 不是先验

内部解越成熟，适应的沉没成本与路径依赖越大（反例：agent 已把内部方案写进多个候选、形成局部词汇，外部方案更难并入），净 option value 可能**下降**。符号是经验问题——这加强做实验的理由，但不能写进契约正文当作趋势。

---

## 4. 决定成败的工程事实

### 4.1 "封闭臂"今天不存在

由 `§2.2`、`§2.3`：`coding_agent` 是 `danger-full-access` 且 TCP 可达；packet 有 4 条可读路径。所以"τ 之前不给看"**无法用策略表达**——它是**挂载问题**；今天的 `Retrieve@never` 臂会让 agent **在 t=0 就读到答案**。

⇒ **机制 A 是 `B0` 的前置条件**，理由有两条：① 修泄漏（A1 第 8 项本来就卡在这里）；② 提供 τ-reveal 的唯一实现。

### 4.2 预训练通道是 manipulation failure，placebo 修不了（【反馈】）

若模型权重已包含 `X`，则 `K_{\tau^-} \approx K_{\tau^+}`——**`X@τ` 根本没有改变信息集**。这不是普通 confound，而是 treatment manipulation failure。

$$
\boxed{PriorKnowledgeProbe\ \neq\ PlaceboControl}
$$

- placebo 只能回答："**突然出现一个文件 / 提示我去看东西**，本身有没有作用？"（reveal cue effect）
- 它**不能**回答："agent 是否早已知道真实 `X`？"

所以流程是：

$$
\boxed{Measure\ prior\ recoverability\ \to\ qualify\ /\ reject\ packet}
$$

在 disposable runs、完全封闭命名空间下、**不给 `X`**，让 agent 做同一任务，测

$$
P_{\rm recover}=P(\text{agent independently reconstructs an }X\text{-equivalent mechanism}).
$$

要求的是**行为/机制等价**，不是源码逐字一致。若 `P_recover > p_max`，则 `X` 不适合作为 `B0` 的 timing packet，换：新近产生的 artifact、task-specific artifact、合成但真实有效的机制、或参数化随机化到模型不可能记住的机制。placebo 仍然要保留，但职责不同。

**【我的补充 — 把它做成无 judge 的可测量】** "机制等价"很难操作化。一个不需要 judge、也不需要 embedding 的版本是**用 harness 自己的量**：

$$
P_{\rm recover}:\quad \text{在封闭且无 }X\text{ 的运行的最终 } J_{\rm best}\ \ge\ (1-\varepsilon)\,J_X
$$

即"不给 packet，agent 能不能自己走到 packet 同等的分数"。`ε` 预注册。（注意它测的是**可达性**，不区分"重新发明了同一机制"与"用了别的等价机制"——对 timing 实验这恰好是我们要的强条件。）

**【我的补充 — 它自己需要功效】** `P_recover` 是一个**比例**，`R=4` 级别的经费估不准它（真值 0.4 时四次全空一点都不稀奇）。所以要么给它独立的重复数与功效声明，要么把它当**设计筛选**并留宽裕裕度，而不是当统计判定。

### 4.3 【我的补充】T1 可能是**结构上不适合** B0 的任务

T1 的搜索空间是 **Max-Cut 启发式**：greedy、local search、tabu、multi-flip、SDP-ish relaxation……**这是语言模型预训练里最密集的一类算法知识之一**。

- 该风险在**选任务时就被写下**：T1 的评分卡把 "benchmark overfit / 模型记得 Max-Cut heuristics" 列为首要风险之一。
- 但**它没有进入任务的任何冻结工件**：我以 `memoriz` / `记忆` 检索项目自身文档，**无命中**（只有第三方插件文件命中；不排除它以别的措辞存在）。也就是说这个风险在选任务之后被**丢掉了**，而现在它成了 `G_3` 的承重项。

⇒ 结论：`G_3` 在 T1 上可能**无法通过**，且原因不是"T1 不好"，而是"T1 的机制空间与预训练先验重叠太大"。**这会把 B0 的载体推向另一个任务**——一个 `J_X` 可测、但 `X` 不在常见先验里的任务。这一条我认为与 `§4.2` 同等重要，而且比 v1 的任何判断都更能决定后面几个月的走向。

---

## 5. 实验链（【反馈】：阶梯 + 失败定位）

$$
\boxed{
\begin{array}{rcl}
A1 &:& \text{substrate qualification}\\[1mm]
G_1&:&X\ \text{intrinsically useful}\\
G_2&:&X\ \text{leaves residual headroom}\\
G_3&:&X\ \text{creates an agent-level information treatment}\\[1mm]
B0a&:&\text{Does reveal timing causally matter?}\\
B0b&:&\text{Can trajectory state predict a better reveal time?}\\
B1&:&\text{Can the agent jointly decide when + what to acquire?}
\end{array}}
$$

### 5.1 `B0a`（timing identification）

$$
\tau/B\in\{0,.2,.4,.6,.8,\infty\}
$$

随机 reveal 同一个 `X`，测 `g(τ)=E[Y(τ)−Y(∞)]`。若 `g(τ) ≈ constant`，则 adaptive timing **没有意义**，`B0b` 不启动。只有

$$
\exists\tau_1,\tau_2:\ |g(\tau_1)-g(\tau_2)|>\delta_\tau
$$

才进入 `B0b`。

### 5.2 `B0b`（state 能否预测时机）

`V_B(π_{θ,k})` vs `max_{π∈Π_fixed} V_B(π)`（`§3.3`），第一代 `s_t` 只有三个量（`§3.5`）。

### 5.3 harness 侧净新增

**已确认不存在**：reveal 机制（τ 把 `X` 物化进工作区，机制 A 下即"挂载出现"）；`r̂_t, ℓ_t` 的计算；每 campaign 记录 `(reveal 时刻, reveal 内容摘要, s_t at reveal)`；`PriorKnowledgeProbe`；任何 acquisition-cost 项进 `B_hard`。

### 5.4 下一步最小工程（【反馈】：不要宣布 A 已 ready）

$$
Mechanism\ A\ \to\ wire\ \to\ \underbrace{30\,min\ long\ session}_{\text{尚未做过}}\ \to\ \underbrace{adversarial\ bypass\ probe}_{\text{v1 §7.3 的未决项}}\ \to\ freeze
$$

只有全部通过才开 timing。**我同意不把 A 宣布为 production-ready**：它的强制点是启动处的 PATH shim，不是内核。

### 5.5 成本

`B0a` 六臂 × R 次；`B0b` 再加。以 `N=40` 计 ≈ **20 h 墙钟 / ≈ $20**；`N=136` ≈ **68 h / ≈ $70**。**墙钟是约束，钱不是。** `B0a` 的 N 应由预注册的最小可检测 `δ_τ` 反推，且这个数字必须先落成文件。

---

## 6. 逐条：提案原话 vs 我的判断（v2 更新）

| 提案/审查原话 | 我的判断 |
|---|---|
| "`A_O` 成了前提，`Q_1` 就解决了" | 只在 frozen packet 上成立；开放世界的 `Q_1` 没被回答，且答案任务相关（`§3.1`） |
| "`R` 不再是必需的 state variable" | 对 policy 成立，对实验者不成立（`§3.6`） |
| "`dr_E/dt>0`"（早期） | 未定号（`§3.7`） |
| "门 B 就是 ρ 门"（v1） | **错**，改为三门前置（`§3.2`） |
| "Δ=0.1166 是照抄下界"（v1） | **错**，它只是 reference implementation 的分数（`§3.2`） |
| "晚 reveal 要补 adaptation 配额"（v1） | **错**，方向反了（`§3.4`） |
| "placebo 臂 + 标 `UNCONTROLLED`"（v1） | 不够，需要 `PriorKnowledgeProbe`（`§4.2`） |
| "`g(τ)` 只是诊断"（v1） | 升为独立阶段 `B0a`（`§5.1`） |
| "`s_t` 要规定 authority"（v1） | 更好的做法是**删掉** `D/F/S`（`§3.5`） |

---

## 7. 最可能被推翻的地方（给复核者的攻击清单，v2）

1. **`G_3 ≡ g(0)` 的重复使用**（`§3.2`）——若复核者认为 (a) 方案是"同一数据用两次"，则 `G_3` 必须并入 `B0a`，`B0a` 变成第一条真正的判定。
2. **`r̂` 与 `ℓ` 退化成一维**（`§3.5`）——若我的分析对，第一代策略族比反馈里写的更弱；若不对，请指出幅度信息如何在不引入 embedding 的前提下进入 `s_t`。
3. **`P_recover` 的操作化**（`§4.2`）——用 `J_best ≥ (1−ε)J_X` 测"是否已知道"会把"用了别的等价机制"也算成功；对 timing 实验这偏保守，但对"packet 有效性"的解释可能有偏。
4. **T1 是否还能承载 `B0`**（`§4.3`）——若不能，`§5` 的整条阶梯要换载体，而换载体的代价（新套件、新 `E*`、新门、新标定）我在 `§5.5` 里没有计入。
5. **"机制 A 是最短路径"**——A 的强制点是 PATH shim、不是内核；绕过未被证明不存在（`§5.4`）。
6. **探针报告自身有 10 处内部不一致**（`§8.3`）——承重事实我从 JSON 复核过，但"报告 = 证据"在该目录不完全成立。
7. **所有 N-campaign 成本都是外推**——`R_A1^main = ∅`，8 个 campaign 一个都没跑过。
8. **novelty 是否仍然太宽**（`§2.8`）——DeepEvolve 已吃掉"外部知识有用"（在算法发现领域，且同样用 30 分钟预算），ReaLM-Retrieve 已吃掉"何时检索优于固定间隔"（在 QA）。若复核者知道更近的"算法发现中的获取时机"工作，本报告的三层收窄需要重写。我的检索**未穷尽**（`§8.4`），各篇的核对状态见 `§8.2`。

---

## 8. 证据附录

### 8.1 承重证据表

| 断言 | 证据路径:行 | 我复核 |
|---|---|---|
| 门判定 `ADMISSIBLE`，dev Δ 0.116584858 / ρ 0.615639328 | `a0/tasks/maxcut/gates/verdict.dev.pc_exchange_k10.json`；`a0/A1-RESULT.md` §3 | ✅ |
| eval Δ 0.116426731 / ρ 0.600847458 | `verdict.eval.pc_exchange_k10.json` | ✅ |
| 旧正控 ρ 0/4 族、`NOT_ADMISSIBLE` | `verdict.dev.json` | ✅ |
| 强度曲线全表（12 份 verdict 全字段重算 0 差异） | `gates/strength_table.json:76-568` | 二手（S4） |
| `cut=217 = R = OPT`，blob `9020082d` | `a0/a1/epistemic-probe/REPORT.md:221` + `targets.json` | ✅ |
| 三档读权限等价；`read-only` 与 `workspace-write` 50 格全同 | `epistemic-probe/agent_epistemic_probe.json` | ✅ |
| `danger-full-access` 出站 TCP 可达 | 同上（A43–A45）；`REPORT.md:262-263` | ✅ |
| T1 三角色的 `sandbox` / `web_search` | `a0/a1/kapso_t1/config/mode.maxcut.yaml:72,73,81,90` | ✅ |
| packet 的 4 条可读路径 | `positive_control/pc/pinned/`、`redesign/frozen_mirror/pc/pinned/`（跟踪）；`e-star-state/**`（gitignored） | 二手（S5） |
| 机制 A 封闭 + 账本 1020/17399/397/424，延迟 0.051 s | `epistemic-ns/evidence/{01,02,03,08,09,10}*`、`ledger_*.jsonl` | 二手（S2） |
| 机制 A 的 diff **未接线** | `epistemic-ns/REPORT.md:17,42,230`；`git status a0/a1/kapso_t1 a0/runtimes` 干净 | 二手（S2） |
| 机制 C：21 条路径 0 可开、合计 2634 CEq、bwrap 阻塞 | `epistemic-container/evidence/{20,21,26,28,41,43}*` | 二手（S3） |
| 机制 C 需改两个角色，**未改** | `epistemic-container/REPORT.md:558`；`mode.maxcut.yaml:81,90` 仍 `read-only` | 二手（S3） |
| `B_hard = (1800 s, 1966519 CEq, 725, 1)` | `a0/a1/calibration/B_hard.json:921-930` | ✅ |
| 速率 52440.489 / 21323.491 CEq/min | `B_hard.json:457,449` | 二手（S6） |
| `R=10/16/34` **不在仓库** | 全仓正则与 `git log -S` 无命中 | 二手（S6） |
| `R=4` 是 qualification、不是功效样本 | `a0/A1-CONTRACT-AUDIT.md:13,119`；31.25% / 65.17% | 二手（S6） |
| "何时获取"在仓库里不存在 | `§2.6` 检索清单 | 二手（S4） |
| 42/60 图 SCIP 认证最优（其余仅 `U` 界） | `a0/A1-RESULT.md` §1 第 3 项 | 二手 |
| FLARE 的 trigger 是 low-confidence token | `aclanthology.org/2023.emnlp-main.495/` 摘要（我抓取核对） | ✅ |
| 项目文档里没有 memorization 风险记录 | 以 `memoriz`/`记忆` 检索 `a0/**/*.md` 无项目自身命中 | ✅（措辞有限的检索） |
| 阈值/套件/`gate_config.json`/`E*` 未因修订改变 | `gates/restamp.evidence.json`（924/924 current, 0 stale）；`gate_config.json` sha256 `171c23d8…` 与 12 份 verdict 记录一致 | ✅ |

### 8.2 我亲自复核的条目

**仓库侧**：两套 verdict 的数值与判定；强度曲线的 k10/k25/∞ 三行与阈值；`cut=217=R` 与 blob 路径；三档读权限与 TCP 两列；T1 三角色配置行；`B_hard`、两臂速率、成本与美元换算；`R=10/16/34` 不在仓库；`restamp`/`refreeze` CLEAN；`memoriz`/`记忆` 检索。

**文献侧（我亲自抓取页面核对，2026-09-23）**：

| 文献 | 我核对了什么 | 结果 |
|---|---|---|
| FLARE / Jiang et al., EMNLP 2023 | 摘要（`aclanthology.org/2023.emnlp-main.495/`） | 存在；"actively decide **when and what to retrieve**"、"**low-confidence tokens**" |
| Self-RAG / arXiv:2310.11511 | 摘要 | 存在；"adaptively retrieves passages on-demand… **reflection tokens**" |
| Hay, Russell, Tolpin & Shimony, UAI 2012 / arXiv:1207.5879 | 摘要 | 存在；"counterexample to the intuitive conjecture that an optimal policy will necessarily reach a decision in all cases" |
| DeepEvolve / arXiv:2510.06056 | 摘要 | 存在（2025-10-07）；"**external knowledge retrieval**…**quickly plateaus**" |
| ReaLM-Retrieve / arXiv:2604.26649 | 摘要（首次抓取失败、重试成功） | 存在（SIGIR 2026）；"a retrieval intervention policy that learns **when**…"；相对固定间隔**检索次数 −47%** |
| Budget-Aware Active RAG / arXiv:2607.24010 | 摘要（首次抓取失败、重试成功） | 存在（KDD 2026 workshop）；"**marginal correctness change over a no-retrieval answer**"、"**retrieval harm is non-negligible**" |
| CAM-DF / arXiv:2607.27083 | 摘要 | 存在（2026-07-29）；标题即 "**Cost-Aware Stopping for Tool Acquisition**"；"a lightweight **pre-execution** plugin" |
| Russell & Wefald, AIJ 1991 | DOI `10.1016/0004-3702(91)90015-C` 的书目（内容协商） | 卷 49、期 1-3、页 361-395 一致；**全文未读**——"meta-greedy barrier" 与 `V(S_j)=U([S_j])−U([α])` 来自调查者所读作者版（二手） |

**我主动否掉的一条引用**：我给调查者的清单里写了 "Self-Route (Li et al. 2024)"。调查者在 arXiv / Semantic Scholar / Crossref / dblp 都找不到它；最接近的是 *Self-Routing RAG*（arXiv:2504.01018）与同名的**推理**工作（arXiv:2505.20664）。**不要引用我原来那条。**

**仅由调查者读全文、我未核对的**：Self-RAG 的三元 `Retrieve{No,Yes,Continue}` 与 GPT-4 标注流程；DRAGIN / SKR / Adaptive-RAG / IRCoT 的 trigger 细节；Search-R1 / ReSearch / R1-Searcher / WebThinker / Search-o1 的奖励细节与提示词原文；DeepEvolve 的"30 分钟预算 + 单卡"句；CAM-DF 的"不在执行后更新获取决策"这一限制。

### 8.3 探针与杠杆报告自身的内部不一致（值得修，不改变承重结论）

1. `epistemic-probe/REPORT.md:208` 说 A19 那格显示 `332 bytes`，artifact 里 A19 的 `bytes=3`，332 出现在 A20。
2. `REPORT.md:239-240,285` 写 `465–484` / `466` 个 pid，artifact 是 `494`（宿主 493）。
3. `REPORT.md:266` 把候选命名空间的失败一律说成 `OSError`，A43/A44 实际是 `gaierror`。
4. `REPORT.md:90` 引的 `workspace-write` profile 漏了三条 `read` 条目（`.git`、`.agents`、`.codex`）；"root 可读"这一要点不变。
5. `REPORT.md:44,245,375` 引的 `codex_agent.py` **不在本仓库**（在 `/home/ebt/kapso_ck/...`）。
6. （机制 A）`REPORT.md:41` 说 `probe_session_ns.py` 产出全部 artifact，但它只写 `01`–`10` 与 `summary.json`；`shim_receipt.json` 与 `ledger_SHIM.jsonl` 不能由 §9 的命令复现。
7. （机制 A）`REPORT.md:266-269` 说 shim 那次返回 `OK`，但 `shim_receipt.json` 里没有 stdout / `last_message`。
8. （机制 A）`REPORT.md:166` 把 `workspace-write` 的失败归因于 seccomp，而它自己 step 6 的 `base_url` 是 `http://127.0.0.1:1/v1` 且没有 relay/`--meter-port`——那一步证明的是"没有模型调用"，不是 seccomp。
9. （机制 C）`REPORT.md:16,248` 写 `4918 / 4923` 个文件，artifact 是 `4919 / 4924`。
10. （redesign）`redesign/LEVERS.md:72` 写 L2 跑在 `θ=(1337, 30 s)`，而 `strength_table.json` 每行存 `timeout_s: 10.0`；数值一致、标签漂移。

### 8.4 我**没有**验证的（明确留给复核者）

~30 分钟长会话（A 与 C 都未跑）；trajectory 级的 session/permission 等价（探针只在 `codex sandbox` 层面测过）；PATH shim 的不可绕性；`P_recover` 的实际值（这是实验问题）；placebo 与 packet 的**成本等价性**操作化；`r̂/ℓ` 的退化分析（这是推导，未做数值验证）；T1 是否真能承载 `B0`（`§4.3` 是论证，不是测量）；以及所有 N-campaign 成本（全部为外推）。

**文献检索的限制（"未找到 ≠ 不存在"）**：`§2.8(e)` 的 novelty 收窄基于三组调查的检索，而检索本身有已知缺陷——其中一组报告搜索引擎返回验证码或噪声、`export.arxiv.org` 拒绝连接、且它没有 WebSearch 工具，只能靠 arXiv 站点内检索；另外两组依赖子代理自带的检索能力。所以 `§2.8(e)` **不能**读成"不存在"，只能读成"在我能触达的范围内没找到"。若复核者知道 2026 年下半年的相关工作（尤其"算法发现中的获取时机"这一支），请直接指出：那一条会重写 `§2.8`。

### 8.5 v1 中被推翻的表述（完整清单，便于追踪）

| # | v1 原文位置 | v1 说法 | 为什么错 |
|---|---|---|---|
| 1 | §3.2 | "门 B 就是 ρ 门" | ρ 只描述"工件是否吃光 assay"，完全不描述 agent 能否自己发现 `X`。v1 自己的 `§7.1` 已预先标记此风险 |
| 2 | §3.2 | "Δ=0.1166 是 agent 照抄时的下界" | 它只是 `J(reference implementation of X)`；agent 可能低于也可能高于它。v1 的 `§7.2` 已预先标记 |
| 3 | §3.1 | "`E[V]>0` 在本任务是假命题" | **逻辑颠倒**：吃掉 82.6% 说明 `V(X) ≫ 0`；失败的是 `AssaySuitability` |
| 4 | §3.4 | "晚 reveal 必须补 adaptation 配额" | 方向反了；那会消掉 timing 最有意义的机会成本 |
| 5 | §4.2 | "placebo 臂 + 标 `UNCONTROLLED` 就够了" | 预训练污染是 manipulation failure，placebo 测不到 |
| 6 | §3.5 | "给 `s_t` 各分量规定 authority" | 更简单也更强的修法是第一代删掉 `D/F/S` |
| 7 | §5 | "沿用 T1，不换任务"（未讨论机制空间与先验重叠） | 见 `§4.3`：T1 可能是结构上不适合的任务 |
| 8 | §9 | 三个请求问的是 v1 的两条错误判断 | 已换成下面的三个新请求 |

---

## 9. 给更高智能复核者的三个新请求

1. **`G_3 ≡ g(0)` 这件事怎么处理**（`§3.2`）？把 `G_3` 做成便宜的 pilot（方案 a），还是并入 `B0a`（方案 b）？如果选 (a)，如何写预注册才不算"同一数据两次使用"？
2. **`r̂` 与 `ℓ` 是否真的退化成一维**（`§3.5`）？若是，第一代 `s_t` 的最小充分形式是什么——**在不引入 embedding、agent 自评、LLM judge 的前提下**，如何把"改进幅度"与"无改进时长"分开？
3. **T1 能否承载 `B0`**（`§4.3`）？若机制空间与预训练先验重叠太大以致 `G_3` 结构性难通过，应当换任务（代价见 `§5.5`），还是应当把 `X` 换成"新近/合成"的 packet（代价是新 packet 的 `G_1/G_2` 要重新量）？我倾向后者优先，因为前者会作废 A1 已经付出的全部仪器工作。
