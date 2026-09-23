# H_T：把"外部信息有没有价值"降为前提、只研究"何时获取"——独立审查

日期：2026-09-23 · 仓库 `HEAD = 9863c148` · 被审查对象：把主假设从 `H_O`（OpenWorld > ClosedWorld）换成 `H_T`（自适应获取时机 > 固定时刻获取）的提案。

**本报告的目的**：为一次外部复核提供可核对的证据基础，并给出我的独立判断（赞成什么、修正什么、反对什么），以及提案里没有写、但决定成败的工程事实。

---

## 0. 摘要（先给结论）

| # | 判断 | 一句话 |
|---|---|---|
| 1 | **赞成方向** | `Q_1` 降为前提是对的，而且仓库里已有它的**静态切片**（强度曲线），不必从零开始 |
| 2 | **提案缺两个预注册门** | `B0` 必须同时门控"非退化"（packet 确有效）与"非冗余"（内部搜不到）；后者**就是** ρ 门 |
| 3 | **主估计量写错了** | 主估计量应是**策略价值差**（同一预算下 `adaptive` vs `fixed`），`Y(τ)` 只是解释它的诊断曲线 |
| 4 | **一个隐藏前提** | 今天 T1 的 coding lane **能直连公网**，且 `X*` **就在工作区里**（4 条可读路径）→ "封闭臂"当前**不存在**，`B0` 在机制 A 之前不可跑 |
| 5 | **一个无法用命名空间关掉的通道** | 预训练记忆。`X*` 若取"人类已知算法"，封闭臂不封闭；需要 placebo 臂与"近期/合成"packet 规则 |
| 6 | **成本判断反转** | 钱不是约束（最贵的读法 ≈ 80 美元），**墙钟是**（`N=136` → 68 h） |
| 7 | **一处降级我不接受** | "所以 `R` 不再是必需状态变量"——对 policy 成立，对**实验者**不成立 |

---

## 1. 方法与可靠性

- 证据由 **6 个互不相通的只读调查者**分别建立，每人只回答一个问题，每条断言都要求给出 `path:line` 与原文。他们只被允许读，不许改仓库、不许调 API、不许跑门或评测。
- **我亲自复核了承重条目**（`§8.2` 列出）：门的新判定与数值、`cut=217=R` 那一条、三种 codex 档位的读权限等价、coding lane 的 `sandbox` 与 `web_search` 值、`B_hard` 与成本换算。
- 其余条目是**二手证据**（调查者的 `path:line` + 引文），在 `§8.1` 表里逐条标注来源，未标注"我复核"的即未被我二次核对。
- 所有数字都可从仓库复现；本报告**不包含任何未执行的主张**。

---

## 2. 事实基础

### 2.1 A1 现在的状态（我复核过）

任务 `T1` 的预注册门在契约修订后通过：

| 门 | dev（裁决集） | eval（诊断） |
|---|---|---|
| Δ 均值 ≥0.03 且 ≥3/4 族 ≥0.02 | 通过 0.116584858，4/4 族 | 通过 0.116426731，4/4 族 |
| ρ 中位 ≥0.30 且 ≥3/4 族 ≥0.30 | 通过 `2417/3926` = 0.615639328，4/4 族 | 通过 `709/1180` = 0.600847458，4/4 族 |

判定文件 `a0/tasks/maxcut/gates/verdict.{dev,eval}.pc_exchange_k10.json` = `ADMISSIBLE`。已废的无界正控（`positive_control/pc/`）仍在 `verdict.{dev,eval}.json` 里记 `NOT_ADMISSIBLE`（ρ 0/4 族），可用 `--pc positive_control/pc` 复现。**阈值、套件、`gate_config.json`、`E*` 均未改动**；身份变化只落在正控的字节上，`restamp_evidence.py` 报 924/924 current、0 stale，`refreeze_evidence.py` 报 CLEAN。

第 8 项（8 个 campaign）**仍未运行**，`R_A1^main = ∅`。

### 2.2 泄漏：agent lane 今天不封闭（这是最重要的一条）

`a0/a1/epistemic-probe/` 的实测矩阵（我复核了档位与 TCP 两列）：

| 档位 | 可达 / 50 | 出站 TCP | 备注 |
|---|---|---|---|
| codex `danger-full-access` | 48/50 | **可以**（`TLSv1.3` 到 `api.deepseek.com:443`、`1.1.1.1:53`） | **T1 的 `coding_agent` 就是这一档** |
| codex `workspace-write` | 40/50 | 不可以（`PermissionError: Operation not permitted`） | 与 `read-only` **全部 50 格逐一相同** |
| codex `read-only` | 40/50 | 不可以 | 同上 |
| candidate sandbox | 5/50 | 不可以（`Network is unreachable`） | 只对**候选**有效，不是对 agent |
| 宿主（对照） | 48/50 | 可以 | — |

三档对**读**都不设限。最尖的一条：`a0/a1/epistemic-probe/REPORT.md:221` 记 `cut(assignment) = 217 ; targets.json: R=217 OPT=217 U=217 role=eval`；那个划分来自 git 历史里的 blob `9020082d`（332 B），其原路径是 `a0/tasks/maxcut/references/logs/partitions/G_eval_0001__BURER2002__s1337.partition.json`——**已删除、仍在历史里**。也就是说隐藏答案既不在工作区、也不在能靠"文件不给看"关掉的地方。

残余（同样实测）：lane 内**环境变量可见**（canary key 的**名字**在所有档位含命名空间内可见，`codex_agent.py` 复制 `os.environ`）；`candidate sandbox` 里 `AF_UNIX` 可 `CONNECTED`（含 `/var/run/docker.sock`）且 `/dev/shm` 可读、与宿主同摘要；**claude lane 在 Linux 没有 OS 沙箱**（`available:false`），那一列是 UNPROVEN。

**而 T1 今天的三条角色配置是**（`a0/a1/kapso_t1/config/mode.maxcut.yaml`）：`coding_agent` `sandbox: "danger-full-access"`（:72）、`feedback_generator` 与 `evaluation_maintainer` `sandbox: "read-only"`（:81、:90），三者都是 `web_search: false`。

> **两条推论，都是决定性的**：
> ① `web_search: false` 关掉的是**工具**，不是 TCP。coding lane 今天能直连公网。
> ⇒ **"ClosedWorld 臂"在今天的实现里不存在**：它既不封闭文件系统，也不封闭网络。
> ② 我们打算当作 `X*` 的那个东西（pinned `one_exchange`）**已经在工作区里**。

### 2.3 `X*` 已经在工作区里（4 条可读路径）

pinned 上游文件 `networkx_maxcut_b69beb2c.py`（sha256 `793419aa…`，BSD-3-Clause）在四处**字节相同**，且其中两处在 git 跟踪范围内：

- `a0/tasks/maxcut/positive_control/pc/pinned/`（跟踪）
- `a0/tasks/maxcut/redesign/frozen_mirror/pc/pinned/`（跟踪）
- `a0/tasks/maxcut/positive_control/e-star-state/pc_dev/candidates/d3c12b54999415a1/pinned/`（存在，gitignored）
- `a0/tasks/maxcut/redesign/out/e-star-state/l1-pc/candidates/d3c12b54999415a1/pinned/`（存在，gitignored）

它的转写（`one_exchange(n, edges, initial_cut, seed, max_swaps=None)`）在 `positive_control/pc/solution.py:117`、`variants/pc_exchange_k10/solution.py:117` 以及 `redesign/candidates/exchange_*/solution.py`。

### 2.4 机制 A 与机制 C 的真实成熟度

| | 机制 A（`unshare` 挂载命名空间） | 机制 C（容器） |
|---|---|---|
| 结论 | **可行**；实跑通过 | **可行**；实跑通过 |
| 封闭证据 | repo / `.git` / key / `targets.json` / `commitments.json` / `G_eval_0001.json` 全部 `FileNotFoundError`；`/home`、`/tmp` 空；git 路线 `executed:false`；**只有 meter 可达** | 21 条实验者专属路径 **0 条可开**；正对照（walk/read control、canary 可见）通过 |
| 计量证据 | 账本行 `ceq=1020`（codex）、`17399`（claude）、`397`+`424`（resume）；合计 20260；附加延迟中位 `0.051 s` | 15 行、4 metered、11 unmetered、**合计 2634 CEq** |
| 接线状态 | **只写了 diff，未接线**（`REPORT.md:17,42,230`；`git status` 干净） | 未接线；且其 diff 要把**两个角色**从 `read-only` 改成 `danger-full-access`（:81/:90 **仍未改**） |
| 长会话 | **未跑**（实测会话 1.1–2.5 s 一轮；`REPORT.md:320` 自认"只测了 invocation shape"） | **未跑**（`REPORT.md:572` 自认） |
| 已知坑 | 宿主 proxy 变量必须清；lane 内必须 `danger-full-access`（`workspace-write` 在 netns 里开不出 socket）；**强制点在启动处的 PATH shim，不是内核** | 容器里 `bwrap` 不可用 → codex 自带沙箱崩 → 只能 `danger-full-access` |

**哪条路更短：A。** C 需要改冻结的 mode 配置 + 容器工具链，A 只需把已写好的 diff 接上。

### 2.5 强度曲线：仓库里唯一的"外部工件强度"测量（我复核过，0 分歧）

`a0/tasks/maxcut/gates/strength_table.json`（已用 12 份 verdict 全字段重算，**0 差异**）：

| 控制 | k | dev Δ | dev ρ | dev 族 | dev | eval Δ | eval ρ | eval 族 | eval |
|---|---|---|---|---|---|---|---|---|---|
| `pc` | ∞ | 0.247942608 | 0.158819629 | 4/4, **0/4** | NOT | 0.238448095 | 0.178715729 | 4/4, **0/4** | NOT |
| `k01` | 1 | **0.018221497** | 0.940123488 | **1/4**, 4/4 | NOT | **0.017982784** | 0.942883023 | 1/4, 4/4 | NOT |
| `k02` | 2 | 0.032882006 | 0.895644283 | 4/4, 4/4 | ADM | 0.033074123 | 0.894196025 | 4/4, 4/4 | ADM |
| `k05` | 5 | 0.069657568 | 0.775149080 | 4/4, 4/4 | ADM | 0.070199653 | 0.762308313 | 4/4, 4/4 | ADM |
| `k10` | 10 | 0.116584858 | 0.615639328 | 4/4, 4/4 | **ADM** | 0.116426731 | 0.600847458 | 4/4, 4/4 | **ADM** |
| `k25` | 25 | 0.204898135 | 0.325902583 | 4/4, 3/4 | ADM | 0.202023485 | **0.301162791** | 4/4, **2/4** | NOT |

随表的两条：**已发表的 greedy 构造同样过不了 ρ**（`redesign/lever_data.json`：Δ 0.22871009、ρ 0.23993558、0 族）；**提高 n 不是答案**（`ER:p080` 的 ρ 随 n 单调下降到 0.1298，`n_where_rho_passes: []`；无界正控在 n≥512 超时）。

这张表在语言上被明确限定为**仪器属性**："ρ 是 assay 的属性，MUST NOT 被当作关于世界的证据"（`positive_control/PC-REVISION.md:165-166`；`a0/A1-RESULT.md:65`）。

### 2.6 "何时获取"在这个仓库里**不存在**

对 `retrieve / when to search / VOI / value of information / timing / plateau / stopping rule / SearchWorld / OpenWorld / acquisition timing / meta-reason / 何时 / 时机` 的全仓检索结论：

- 所有命中都是关于**"是否"**，没有一条是关于**"何时"**：`a0/A1-REQUIREMENTS.md:21`（`H_O`：主动检索比固定资料更值吗）、`:34`；`a0/STATUS.md:23`；`a0/EPISTEMIC-REVIEW.md:22,27,122,134,213`；`a0/mrc/SPEC.md:12`。
- `stopping rule` 只出现在标定的统计规则（`a0/a1/calibration/PILOT-PROCEDURE.md:9,221`）；`plateau` 只出现在一条 A0 agent 的运行日志里；`retrieve` 只作为闭包禁令（`a0/contract/adapter_contract.md:847`）。
- 机制 A/C 的探针只处理**可达性**，不处理**获取时机**。

⇒ 这个转向是**新问题**，不是重发现；同时也意味着**没有现成仪器可复用**，`§5` 的清单是净新增。

### 2.7 成本（我复核了 `B_hard` 与换算）

冻结向量：`T_wall_sec = 1800`、`CEq_max = 1966519`、`N_evaluatorCalls = 725`、`P_concurrency = 1`；实测速率 `A_simpleloop 52440.489 CEq/min`、`A_kapso 21323.491 CEq/min`；两个臂的 `CEq_max/q_r` 分别是 37.50 / 92.22 min，**都晚于 30 min 墙钟**，所以墙钟是设计上的主约束。

| N 个 campaign | 墙钟（顺序） | CEq @ 上限 | CEq @ simpleloop 实测 |
|---|---|---|---|
| 8 | 4 h | 15 732 152 | 12 585 717 |
| 20 | 10 h | 39 330 380 | 31 464 294 |
| 40 | 20 h | 78 660 760 | 62 928 587 |
| 80 | 40 h | 157 321 520 | 125 857 175 |
| 136 | 68 h | 267 446 584 | 213 957 197 |

按契约冻结的 Flash 高峰价格归一（`300k CEq ≈ $0.09`，故 `1 CEq = 3e-7 USD`）：`N=40` → **$19–24**，`N=136` → **$64–80**。

**并且**：`R = 10 / 16 / 34` 这组功效数字**不在仓库里**（检索 `\bR\s*=\s*(10|16|34)\b`、`git log -S`，均无命中；唯一相近的是历史提交里 `R=1682` 的巧合）。它们是提案文本里的数字，进入契约前必须先落成预注册文件。仓库对 `R=4` 的说法只有一条：`a0/A1-CONTRACT-AUDIT.md:13,119`——**qualification replication，不是 inferential sample size**；且 ≥3/4 的判别力很弱（真值 0.5 时通过率 5/16 = 31.25%，0.7 时 65.17%）。**为什么定 4，仓库没有给功效依据（UNPROVEN）。**

---

## 3. 我对提案的独立判断

### 3.1 赞成：把 `Q_1` 降为前提是对的，且理由不是"它显然为真"

仓库里已经量过 `Q_1` 的一个静态切片，结果是**任务相关**的：同一个工件在 `k=∞` 时把差距吃掉 82.6%（ρ 0/4 族，任务 NO-GO），在 `k=10` 时刚好（ρ 0.6156）。也就是说 `E[V] > 0` 这句话不带任务限定就是**假的**（它在 n=128 的四族图上、对"完整 `one_exchange`"这个工件，是假命题——它把可测空间吃光了）。

我仍然赞成把 `Q_1` 降为前提，但**降法要改**：

$$
A_O:\quad \exists\,\text{任务分布}\ \mathcal D,\ \exists\ \text{packet}\ X:\ E_{T\sim\mathcal D}[V(X,T)]>0
$$

而不是任务无关的"外部世界有价值"。否则 `B1` 的估计量又会变成条件性的——这正是上一轮 `KID/EKR` 争论里的同一个洞（按"已知有 headroom / 已知网上有货"挑任务，结论只能带条件）。

### 3.2 修正一：`B0` 需要**两个**预注册门，不是一个

- **门 A（非退化）**：存在某个 τ 使 `Y(τ) > δ_gain`。否则 `Y(τ) ≡ 0` 是构造性的，实验空转。
  *好消息*：`X*` 的"值"我们**已经量过**——取 `k=10` 强度的工件，Δ = 0.1166 是"被逐字照抄时的下界"（`positive_control/variants/pc_exchange_k10/` 就在仓库里）。这给门 A 一个非空的锚点。
- **门 B（非冗余）**：只做内部搜索的臂**不能**自己达到 packet 的值。

关键点：**门 B 就是 ρ 门**。"内部能不能自己找到/顶到"正是 ρ 要测的东西在**时间维**上的镜像。ρ 门失败的原因是 `r_E` 太大（外部工件太强）；门 B 失败的原因会是 `r_I` 太大（内部自己就够）。两者是同一个窄带问题的两面，而这个窄带**必须先测出来才谈得上时机**——`k=1` 是"太弱"（Δ 过不了），`k=∞` 是"太强"（ρ 0/4），`k=10` 是当前唯一被批准的窗口。

### 3.3 修正二：主估计量应是**策略价值差**，`Y(τ)` 只作诊断

提案里的 `Y(τ)` 曲线（reveal 时刻响应曲线）**很漂亮但不能作为主假设的检验**：它容易变成"把一条曲线拟出来"，而没有任何策略被检验。建议改成：

$$
H_T:\quad
\max_{\pi\in\Pi_{\rm adaptive}} E[\text{VerifiedGain} - \lambda\,\text{Cost}\mid \pi]
>
\max_{\pi\in\Pi_{\rm fixed}} E[\text{VerifiedGain} - \lambda\,\text{Cost}\mid \pi]
$$

在**相同** `Task, Model, Evaluator, Packet set, Budget` 下，`Π_fixed` = `{Retrieve@αB}` 网格，`Π_adaptive` = 由 harness 计算信号触发的策略。`Y(τ)` 作为**解释该差值的诊断**保留（它回答"为什么 adaptive 赢/输"），并进入报告的 diagnostic 部分而不是判定部分。

这样做还顺带解决一个识别问题：`Y(τ)` 在 τ 之间的差异混合了"信息早到 → 有 adaptation 时间"与"内部搜索已经在 τ 之前自己发现了 packet 的内容"。前者是 timing，后者是 redundancy。策略比较把它们一起计入**价值**，这是我们要的量；而单独看曲线会把两者混成一个数。

### 3.4 修正三：τ 必须按**剩余预算**归一化，并为 adaptation 预留

你的 §9 直觉（最优点可能早于 plateau）是对的，形式化后果是：`Retrieve@τ` **自身要消耗预算**。若不预留 adaptation，晚 reveal 的臂会因为 `B_t < C_E` 而**必然**输——那测到的是预算不足，不是时机。

⇒ 冻结的必须是：`τ/B` 的比例网格 + 每个臂的**显式 post-reveal allowance**（例如 reveal 后保证 `C_adapt` 的独立配额）。否则第一个实验一定会得出"越早越好"，而那是算术，不是发现。

### 3.5 修正四：`s_t` 的每个分量必须由 harness 计算

`v_t, a_t, D_t, F_t, S_t` 里最危险的是 `S_t`（预测-实际偏离）：若 agent 自己估 `Ĵ`，它同时是**被测量者**和**测量者**。这不是猜想，是本项目已经付过代价的教训：`a0/A1-RESULT.md` §5 记录 KAPSO 的会话声称 `777777`，而**记录分是 harness 供的值**，runtime 自报的字节被丢弃——这正是 D3（harness-owned outcome）存在的理由。

⇒ 在标定/契约阶段就要像 `B_hard` 的四个资源一样，给 `s_t` 的每个分量写明 **authority**（harness 计算 / runtime 自报但仅诊断 / 不可得）。这个活很小，但漏了它，整条 timing 结论会被自报污染。

### 3.6 修正五：`R` 不能从实验者那一侧拿掉

"`R` 不再是必要状态变量"对 **policy** 成立（策略不需要知道上限）。对**实验者**不成立：没有 `R` 就无法知道任务有没有动态范围、`Y(τ)` 是否可测、ρ 是否在窄带里。`R` 留在 measurement side，与仓库已写的 `evidence_scope: instrumentation` 一致。

### 3.7 修正六：`dr_E/dt > 0` 不是先验

内部解越成熟，适应的沉没成本与路径依赖越大（反例：agent 已经把内部方案写进多个候选、形成局部词汇，外部方案反而更难并入），净 option value 可能**下降**。符号是经验问题——这加强做实验的理由，但不能写进契约正文当作趋势。

---

## 4. 提案没写、但决定成败的两件工程事实

### 4.1 "封闭臂"今天不存在，而且 `X*` 已经在工作区里

由 `§2.2`、`§2.3`：`coding_agent` 是 `danger-full-access` 且 TCP 可达；pinned `one_exchange` 有 4 条可读路径。所以

- "τ 之前不给看"**无法用策略表达**——它不是提示词问题，是**挂载问题**；
- 今天的 `Retrieve@never` 臂会让 agent **在 t=0 就读到答案**。

⇒ **机制 A 是 `B0` 的前置条件，不是可选项。** 它的优先级现在有**两条独立理由**支撑：① 修泄漏（A1 的第 8 项本来就卡在这里）；② 提供 τ-reveal 的唯一实现（`unshare -rmnpf` + tmpfs 遮蔽已经能表达"该路径在 τ 之前不存在"）。

### 4.2 有一个命名空间关不掉的通道：预训练

`X*` 若取"人类已知算法"（pinned `one_exchange` 恰好在 NetworkX 里、在 GitHub 上、且在无数教科书里），那么一个**真正封闭**的 agent 仍可能**已经知道它**。命名空间能藏文件与 socket，**藏不住权重**。

这有两个直接后果：

1. `X*` 的选择规则必须纳入这个通道：要么用**近期/合成**的工件（不在常见先验里），要么把这个通道**测出来**。
2. 必须加一条 **placebo 臂**：在同一个 τ 揭示一个"看起来合理、实际无用"的工件。若 placebo 也让 `Y` 上升，那么效应来自"被告知可以去看"（注意力/策略切换），不是信息本身。

一个可用的说法：这个通道在 KID 的三种强制类别里是 **`UNCONTROLLED`**（`a0/EPISTEMIC-REVIEW.md` 已有这套词汇）。这正是 KID 在 timing 实验里的用处——它不必制造"纯净 agent"，只需要**精确标注哪一分信息是拥有的、哪一分必须花钱获取**。

---

## 5. `B0` 的最小可执行形态（供你拍板，我不代决）

**沿用 T1，不换任务**（省掉套件、`E*`、门、meter、`B_hard` 的全部重造）：

- **packet**：`X*` = 仓库里那个已量测的 `one_exchange` 转写（Δ 0.1166 是可照抄下界）。**但**由 `§4.2`，若要用它，placebo 臂与"预训练通道"的讨论必须同时进契约。
- **臂**（全部最终拿到同一个 `X*`，只差时刻/真假）：`never`（负对照）· `packet@0` · `packet@harness-plateau` · `packet@half-budget` · `placebo@τ*`。
- **harness 侧新增**（`§2.4` 已确认这些**不存在**）：reveal 机制（τ 把 `X*` 物化进工作区，机制 A 下即"挂载出现"）；`s_t` 的计算（`v_t`、`a_t`，都由 harness 从 score trace 算）；每个 campaign 记录 `(reveal 时刻, reveal 内容摘要, s_t at reveal)`。
- **前置**：机制 A 接线（A 的路径最短）+ 一次 ~30 分钟长会话验证（**A 与 C 都还没跑过**）。
- **门**：门 A（非退化）与门 B（非冗余）在 pilot 上先测；不过就**改 packet 强度或换任务**，不得放宽。
- **预注册**：`δ_gain`、`δ_red`、`τ/B` 网格、`C_adapt` 配额、以及 `H_T` 的最小可检测效应（这决定 N；功效数字必须落成文件，不能停留在对话里）。
- **成本**：`N=40` ≈ 20 h 墙钟 / ≈ $20；`N=136` ≈ 68 h / ≈ $70。**墙钟是约束，钱不是。**

---

## 6. 我不同意的表述（逐条）

| 提案原话 | 我的判断 |
|---|---|
| "`A_O` 成了前提，`Q_1` 就解决了" | 只在 **frozen packet** 上成立；开放世界的 `Q_1` 没被回答，且答案任务相关（`§3.1`） |
| "`R` 不再是必需的 state variable" | 对 policy 成立，对实验者不成立（`§3.6`） |
| "`dr_E/dt > 0`"（早期） | 未定号；路径依赖与沉没成本可能反号（`§3.7`） |
| "`Y(τ)` 直接给出信息时机响应曲线" | 可以给出，但**不能当主检验**；主检验是策略价值差（`§3.3`） |
| "触发点 = 内部饱和" | 不是最优点的刻画；最优点可能在 plateau **之前**（你自己也说了），所以 τ 必须按剩余预算归一化并预留 adaptation（`§3.4`） |

---

## 7. 我认为最可能被推翻的地方（给复核者的攻击清单）

1. **"门 B 就是 ρ 门"**——它可能只是**类比**而非同一测量。ρ 是"工件吃掉多少差距"，门 B 是"内部搜索能否达到该值"，两者的分母/参照不同（一个用 `R_i`，一个用 packet 的实测值）。若这条类比不成立，`§3.2` 的论证结构需要重建。
2. **`k=10` 的 Δ 可当作 packet 值的锚点**——未必。那个 Δ 是**我们写的候选**逐字采用该算法得到的，不是 agent 在预算内把它"消化"出来的。它给出的是**可达上界**还是**不该期待的乐观值**，需要先做一次 calibration 才能说。
3. **"机制 A 是最短路径"**——A 的强制点是**启动处的 PATH shim**，不是内核（`§2.4`）。绕过 shim 的路径未被证明不存在；C 的强制点更强但代价更高。若"沙箱强度"是 `B0` 的承重项，这个结论要重估。
4. **探针报告本身有 5 处内部不一致**（见 `§8.3`）。承重事实（48/50、danger-full-access 的 TCP、`217 = R`）我从 JSON 复核过；但"报告=证据"这个等式在该目录里并不完全成立。
5. **`placebo 臂`的设计**——若 placebo 与 packet 在"看起来可用"上不等价，placebo 会引入自己的偏差；等价性的操作化还没写。
6. **成本表的墙钟假设**——`P_concurrency = 1` 且 `T_wall = 1800 s` 是**预测**；8 个 campaign 一个都没跑过（`R_A1^main = ∅`）。所有 N 的成本都是外推。

---

## 8. 证据附录

### 8.1 承重证据表

| 断言 | 证据路径:行 | 我复核 |
|---|---|---|
| 门判定 `ADMISSIBLE`，dev Δ 0.116584858 / ρ 0.615639328 | `a0/tasks/maxcut/gates/verdict.dev.pc_exchange_k10.json`；`a0/A1-RESULT.md` §3 | ✅ |
| eval Δ 0.116426731 / ρ 0.600847458 | `a0/tasks/maxcut/gates/verdict.eval.pc_exchange_k10.json` | ✅ |
| 旧正控 ρ 0/4 族、`NOT_ADMISSIBLE` | `a0/tasks/maxcut/gates/verdict.dev.json` | ✅ |
| 强度曲线全表（12 份 verdict 全字段重算 0 差异） | `a0/tasks/maxcut/gates/strength_table.json:76-568` | 二手（S4） |
| `cut=217 = R = OPT`，blob `9020082d` | `a0/a1/epistemic-probe/REPORT.md:221`；`targets.json` | ✅ |
| 三档读权限等价；`read-only` 与 `workspace-write` 50 格全同 | `a0/a1/epistemic-probe/agent_epistemic_probe.json` | ✅ |
| `danger-full-access` 出站 TCP 可达 | 同上（A43–A45）；`REPORT.md:262-263` | ✅ |
| T1 三角色的 `sandbox` / `web_search` | `a0/a1/kapso_t1/config/mode.maxcut.yaml:72,73,81,90` | ✅ |
| pinned `one_exchange` 四条可读路径 | `positive_control/pc/pinned/`、`redesign/frozen_mirror/pc/pinned/`（跟踪）；`e-star-state/**`（gitignored） | 二手（S5） |
| 机制 A 封闭 + 账本 1020/17399/397/424，延迟 0.051 s | `a0/a1/epistemic-ns/evidence/{01,02,03,08,09,10}*`、`ledger_*.jsonl` | 二手（S2） |
| 机制 A 的 diff **未接线** | `a0/a1/epistemic-ns/REPORT.md:17,42,230`；`git status a0/a1/kapso_t1 a0/runtimes` 干净 | 二手（S2） |
| 机制 C：21 条路径 0 可开、合计 2634 CEq、bwrap 阻塞 | `a0/a1/epistemic-container/evidence/{20,21,26,28,41,43}*` | 二手（S3） |
| 机制 C 需改两个角色，**未改** | `a0/a1/epistemic-container/REPORT.md:558`；`mode.maxcut.yaml:81,90` 仍 `read-only` | 二手（S3） |
| `B_hard = (1800 s, 1966519 CEq, 725, 1)` | `a0/a1/calibration/B_hard.json:921-930` | ✅ |
| 速率 52440.489 / 21323.491 CEq/min | `B_hard.json:457,449` | 二手（S6） |
| `R=10/16/34` **不在仓库** | 全仓正则与 `git log -S` 无命中 | 二手（S6） |
| `R=4` 是 qualification、不是功效样本 | `a0/A1-CONTRACT-AUDIT.md:13,119`；31.25% / 65.17% 通过率 | 二手（S6） |
| "何时获取"在仓库里不存在 | `§2.6` 的检索清单 | 二手（S4） |

### 8.2 我亲自复核的条目

门的两套 verdict 数值与判定；强度曲线的 k10/k25/∞ 三行与阈值；`cut=217=R` 与 blob 路径；三档读权限与 TCP 两列；T1 三角色的配置行；`B_hard` 与两臂速率、成本换算与美元换算；`R=10/16/34` 不在仓库；`restamp`/`refreeze` 的 CLEAN。

### 8.3 调查者发现的**探针报告自身**的不一致（值得修，但不改变承重结论）

1. `epistemic-probe/REPORT.md:208` 说 A19 那格显示 `332 bytes`，而 artifact 里 A19 的 `bytes=3`（"332" 这三个字符的长度），332 出现在 A20。
2. `REPORT.md:239-240,285` 写 `465–484` / `466` 个 pid，artifact 是 `494`（宿主 493）。
3. `REPORT.md:266` 把候选命名空间的失败一律说成 `OSError`，A43/A44 实际是 `gaierror`。
4. `REPORT.md:90` 引的 `workspace-write` profile 漏了三条 `read` 条目（`.git`、`.agents`、`.codex`）；"root 可读"这个要点不变。
5. `REPORT.md:44,245,375` 引的 `codex_agent.py` **不在本仓库**（在 `/home/ebt/kapso_ck/...`），仓库内无法核对。
6. （机制 A）`REPORT.md:41` 说 `probe_session_ns.py` 产出全部 artifact，但它只写 `01`–`10` 与 `summary.json`；`shim_receipt.json` 与 `ledger_SHIM.jsonl` 不能由 §9 的命令复现。
7. （机制 A）`REPORT.md:266-269` 说 shim 那次返回 `OK`，但 `shim_receipt.json` 里没有 stdout / `last_message`。
8. （机制 A）`REPORT.md:166` 把 `workspace-write` 的失败归因于 seccomp，而它自己 step 6 的 `base_url` 是 `http://127.0.0.1:1/v1` 且没有 relay/`--meter-port`——那一步证明的是"没有模型调用"，不是 seccomp。
9. （机制 C）`REPORT.md:16,248` 写 `4918 / 4923` 个文件，artifact 是 `4919 / 4924`。
10. （redesign）`redesign/LEVERS.md:72` 写 L2 跑在 `θ = (1337, 30 s)`，而 `strength_table.json` 每行存 `timeout_s: 10.0`；数值一致、标签漂移。

### 8.4 我**没有**验证的（明确留给复核者）

~30 分钟长会话（**A 与 C 都未跑**）；trajectory 级的 session/permission 等价（探针只在 `codex sandbox` 层面测过）；PATH shim 的不可绕性；`X*` 的预训练可达性（这是一个**实验**问题，不是文献问题）；placebo 臂的等价性操作化；以及所有 N-campaign 成本（`R_A1^main = ∅`，全部为外推）。

---

## 9. 给更高智能复核者的三个具体请求

1. **门 B（非冗余）是否与 ρ 门同构**（`§3.2`、`§7.1`）？若不同构，请指出正确的形式。
2. **主估计量应当是策略价值差还是 τ 曲线**（`§3.3`）？若你同意价值差，请指出 `Π_adaptive` 的最小充分族（我给的 `{v_t, a_t, D_t, F_t, S_t, B_t}` 是否多余或不足）。
3. **`X*` 的预训练通道应当被"排除"还是被"测量"**（`§4.2`）？我倾向测量（placebo 臂 + KID 里记为 `UNCONTROLLED`），但这会让 `A_O` 的前提带上"该通道已量化"的附加条件。
