我按“原报告之后的下一层问题”继续追了，而不是重新做一轮宽泛综述。这一轮出现了一个很重要的修正：**我们之前把 multi-agent 的主要问题理解成相关性/冗余，还不够；2026 年公开实验已经开始表明，更根本的问题可能是 information integration。**

## 1. SILO-BENCH 给了一个很强的反例：会通信 ≠ 会协作

我下钻了 [SILO-BENCH GitHub](https://github.com/jwyjohn/acl26-silo-bench?utm_source=chatgpt.com) 的源码/实验设计，并和 ACL 2026 论文交叉核验。

它刻意去掉 `Manager / Worker / Reviewer` 等角色先验，让每个 agent 只看到自己的 private shard，再自行发现通信策略。30 个算法任务被按理论通信结构分成：

```math
\begin{array}{ccl}
L_I &:& O(N),\quad aggregation\\
L_{II}&:& O(N),\quad local/mesh\\
L_{III}&:& O(N\log N)\sim O(N^2),\quad global\ shuffle.
\end{array}
```

然后系统改变：

```math
N\in\{2,5,10,20,50,100\}
```

和 P2P / Broadcast / Shared File 三种通信机制，总计 1,620 次实验。关键结果并不是“agents 不交流”，而是：

```math
\boxed{
InformationAcquired
\not\Rightarrow
InformationIntegrated.
}
```

论文称之为 **Communication–Reasoning Gap**：agents 会主动形成看起来合理的通信结构，也能获得信息，却无法把 distributed state 正确综合；复杂任务随着规模扩大反而崩溃，Level III 在超过 50 agents 后达到零成功率。

这对我们前面的理论是一次很好的纠偏。

我们原来重点研究：

```math
N_{\rm eff}
```

和：

```math
Corr(A_i,A_j).
```

现在至少还需要一个独立变量：

```math
\boxed{\eta_I=\text{IntegrationEfficiency}.}
```

因此 multi-agent scaling 更可能是：

```math
U_N
=
f(
N_{\rm eff},
I_{\rm distributed},
\eta_I,
C_{\rm communication},
C_{\rm synthesis}
).
```

不是简单：

```math
U_N=f(N).
```

---

## 2. 我在沙箱里重新验证了“相关性瓶颈”，结论依然成立，但现在知道它只解释了一半

我重新做了一个 correlated-agent Monte Carlo。

设每个 agent marginal accuracy：

```math
p=0.7,
```

latent error correlation 为：

```math
\rho,
```

采用 majority aggregation。

30,000 次 Monte Carlo/配置得到：

| `N\rhoN_{\rm eff}`majority accuracy |    |       |      |
| ----------------------------------- | -- | ----- | ---- |
| 5                                   | 0  | 5.00  | .838 |
| 17                                  | 0  | 17.00 | .961 |
| 33                                  | 0  | 33.00 | .992 |
| 5                                   | .3 | 2.27  | .773 |
| 17                                  | .3 | 2.93  | .812 |
| 33                                  | .3 | 3.11  | .820 |
| 5                                   | .7 | 1.32  | .723 |
| 17                                  | .7 | 1.39  | .730 |
| 33                                  | .7 | 1.41  | .732 |
| 33                                  | .9 | 1.11  | .708 |

所以：

```math
N:5\rightarrow33
```

在 `\rho=.7` 时几乎没得到什么：

```math
.723\rightarrow.732.
```

这很好地支持：

```math
\boxed{
N_{\rm agents}
\text{ 不是合理的 scaling variable；}
N_{\rm eff}
\text{ 更接近。}
}
```

但 SILO-BENCH 又告诉我们：

> 即使 information diversity 很高，`\eta_I` 仍然可能很低。

所以现在更好的 scaling decomposition 是：

```math
\boxed{
\underbrace{GenerateDiversity}_{N_{\rm eff}}
\rightarrow
\underbrace{Transmit}_{C_{\rm comm}}
\rightarrow
\underbrace{Integrate}_{\eta_I}
\rightarrow
\underbrace{Verify}_{V}
\rightarrow Outcome.
}
```

这比我们上一版报告中的“独立样本数”模型更完整。

---

# 3. 一个正在浮现的 Agent 工程定律：Coordination Capacity

SILO-BENCH 还有一个很值得理论化的现象：

任务本身具有 communication complexity：

```math
C_T.
```

Agent system 则具有某种有效 coordination capacity：

```math
C_A.
```

那么可能存在 regime transition：

```math
\boxed{
C_T<C_A
\Rightarrow scalable,
}
```

而：

```math
\boxed{
C_T>C_A
\Rightarrow coordination\ collapse.
}
```

这非常像工程里的 envelope/bifurcation 思想。

于是：

```math
N\uparrow
```

并不保证 capacity 增加，因为同时：

```math
C_{\rm coordination}(N)\uparrow.
```

甚至可能：

```math
\frac{dC_A}{dN}
<
\frac{dC_T}{dN}.
```

最终出现：

```math
\boxed{\text{Agent coordination envelope}.}
```

这比“multi-agent 是否优于 single-agent”这个问题高级得多。

---

# 4. 另一个 ACL 2026 实验恰好支持这个解释

MAS-BENCH 专门让 agents 做 distributed sorting——算法本身很简单，困难来自 distributed coordination。

实验发现 agent 数增加后，失败集中在：

-  shared state； 
-  convention alignment； 
-  termination consistency。 

他们加入 CAMOC：early global metadata exchange + collaboration-aware sharing + single-commit verification 后，协调显著改善。

所以：

```math
\boxed{
IndividualIntelligence
\neq
CollectiveComputability.
}
```

这句话我现在认为非常重要。

一个系统即使每个 node 都足够聪明：

```math
I(A_i)\gg0,
```

仍然可能：

```math
I(A_1,\ldots,A_N)
```

随着 `N` 增加而恶化。

这开始像真正的 distributed systems theory，而不是“角色扮演”。

---

# 5. 这也说明我们之前的 Exposure Graph 应该扩展成 Information-Flow Graph

原来：

```math
G=(V,E,C)
```

主要描述谁看到谁的信息。

现在需要：

```math
\boxed{
G_I=
(V,E,
Capacity,
Latency,
Loss,
Compression,
Correlation,
Authority).
}
```

一个 edge 不只是：

```math
A\to B.
```

而应该带：

```math
e_{ij}=
(
bandwidth,
delay,
compression,
provenance,
exposure,
authority
).
```

这样才能描述：

```math
A\xrightarrow{\text{summary}}B
```

和：

```math
A\xrightarrow{\text{raw evidence}}B
```

实际上是两个完全不同的 channel。

---

# 6. ExtAgents 给了另一个非常有意思的正例

我继续读了 [ExtAgents GitHub](https://github.com/THUNLP-MT/ExtAgents?utm_source=chatgpt.com)。

它解决的不是“多 agent 辩论”，而是：

```math
|Knowledge|\gg ContextWindow.
```

多个 fixed-context agents 分布式读取大量知识，然后：

```math
\boxed{
GlobalKnowledgeSynchronization
+
SharedRanking
+
KnowledgeAccumulation.
}
```

ACL 2026 实验表明，在相同 external knowledge input 下，它能比现有 non-training 方法更好利用超 context-window 的知识，同时保持较高并行性。

这与 SILO-BENCH 放在一起非常有意思：

```math
\boxed{
MultiAgent
\text{ 可以扩展 observation bandwidth，}
}
```

但：

```math
\boxed{
MultiAgent
\text{ 不自动扩展 integration capacity。}
}
```

于是出现两个不同容量：

```math
B_O=\text{ObservationBandwidth}
```

和：

```math
B_I=\text{IntegrationBandwidth}.
```

若：

```math
B_O\gg B_I,
```

增加 agent 只会产生：

```math
\boxed{\text{information congestion}.}
```

我认为这是一个非常值得正式研究的新概念。

---

# 7. 因而可以提出一个“Agent 信息瓶颈模型”

令：

```math
R_O=\text{information acquired/time},
```

```math
R_I=\text{information integrated/time}.
```

定义：

```math
\boxed{
\chi=
\frac{R_O}{R_I}.
}
```

若：

```math
\chi\ll1,
```

system observation-limited。

若：

```math
\chi\approx1,
```

balanced。

若：

```math
\chi\gg1,
```

integration-limited。

这很可能解释：

-  blind agent → retrieval 有益； 
-  moderate context → multi-agent 有益； 
-  massive parallel retrieval → synthesis collapse。 

也就是说性能曲线可能不是单调的：

```math
J(R_O)
=
\uparrow
\quad\text{then}\quad
\rightarrow
\quad\text{甚至}\quad
\downarrow.
```

这可以直接实验。

---

# 8. Context engineering 这一侧也出现了非常强的独立证据

ACL 2026 的 COMPASS 把 long-horizon failure 的核心问题明确定位为 **context management**：历史越来越长以后，agent 会漏掉关键 evidence、被无关信息干扰，并失去 replanning/reflection 能力。

它拆成：

```math
MainAgent
+
MetaThinker
+
ContextManager.
```

Context Manager 不保留完整历史给 Main Agent，而是维护 stage-specific concise progress briefs。

三个 benchmark：

```math
GAIA,\ BrowseComp,\ HLE
```

上相对 single/multi-agent baseline 提升最高约 20%。

这很好地支持我们一直坚持的：

```math
\boxed{
History\neq WorkingContext.
}
```

更准确：

```math
H_t
\xrightarrow{Projection}
S_t
\xrightarrow{ContextAssembly}
K_t.
```

而不是：

```math
H_t\to Prompt.
```

---

# 9. 所以 Decision-Sufficient State 现在不再只是我们的理论猜想

现有工程开始从不同方向逼近同一个对象：

ExtAgents：

```math
HugeKnowledge\to DistributedSummary.
```

COMPASS：

```math
LongHistory\to StageBrief.
```

ReSum：

```math
Trajectory\to RestartableState.
```

Graphiti：

```math
Episodes\to TemporalFacts.
```

我们的对象比它们再抽象一级：

```math
\boxed{
S_t^*
=
\arg\min_S |S|
\quad
s.t.
\quad
Regret(\pi(S))
\le\epsilon.
}
```

这就是我认为可以真正立成理论问题的：

```math
\boxed{\textbf{Decision-Sufficient State (DSS)}.}
```

关键是**不是 summary quality**。

而是：

```math
\boxed{\text{decision regret}.}
```

两个 summary BLEU/LLM-judge 差很多，只要：

```math
\pi(S_1)=\pi(S_2)
```

且 action 正确，它们在控制意义上可能等价。

---

# 10. 这给出了一个我们可以真正做的新 benchmark

我会设计：

```math
H\to S\to Decision.
```

提供完整 trajectory `H`，然后逐渐压缩：

```math
|S|/|H|
=
1,.5,.25,.1,.05,.01.
```

测：

```math
R(S)=
V(a^*)-V(\pi(S)).
```

得到：

```math
\boxed{\text{State Compression–Regret Curve}.}
```

不同 projection：

```math
\begin{aligned}
&LastK\\
&LLMSummary\\
&EvidenceOnly\\
&TypedState\\
&TemporalGraph\\
&ReSumLike
\end{aligned}
```

比较：

```math
AUC_{SCR}.
```

这比现在大多数 memory benchmark 更接近真正 Agent Engineering。

---

# 11. Multi-agent scaling 的公开实验现在也开始出现可重复规律

ACL 2026 对 self-consistency、self-refinement、multi-agent debate、mixture-of-agents 做了 34 种 configuration、100+ evaluations。

最高预算约：

```math
20\times CoT
```

时，MMLU-Pro accuracy 可增加最高 7.1 percentage points；在 equal-compute 条件下，他们报告 debate 和 mixture-of-agents 分别比 self-consistency 高约 1.3 和 2.7 points。

更有意思的是：

```math
\boxed{
\#parallel\ generations
>
\#sequential\ aggregations
}
```

是他们得到的一个经验 efficiency guideline。

这和我们之前的：

```math
B_{\rm breadth}/B_{\rm depth}
```

非常接近。

所以这个 ratio 值得保留：

```math
\boxed{
\Pi_{BD}
=
\frac{B_{\rm breadth}}
{B_{\rm depth}}.
}
```

它现在已经不是纯想象的“Agent Reynolds number”，而是有初步实验依据的 candidate regime variable。

---

# 12. 但 SILO-BENCH 又告诉我们：这个规律不能无限外推

reasoning benchmark 中：

```math
breadth\uparrow
```

可以提高 diversity。

distributed coordination 中：

```math
N\uparrow
```

最终会 coordination collapse。

所以真正规律可能是：

```math
\boxed{
U(N)
=
DiversityGain(N)
-
IntegrationCost(N).
}
```

若近似：

```math
D(N)=a(1-e^{-bN}),
```

而：

```math
C_I(N)=cN^\alpha,
\qquad\alpha\ge1,
```

则必然存在：

```math
N^*<\infty.
```

因此：

```math
\boxed{
OptimalAgentCount
\text{ 应该是 state/task dependent。}
}
```

这直接把 multi-agent orchestration 重新变成一个 control problem。

---

# 13. Belief dynamics 这条线也出现了重要实证

TACL 2026 的 DReaMAD 专门研究 multi-agent debate 的 **belief entrenchment**。

它把失败分成：

```math
\boxed{
StaticPriorBias
+
HomogenizedDebateDynamics.
}
```

也就是说，agents 不只是“错误相关”。

interaction 本身会：

```math
\rho_{t+1}>\rho_t.
```

标准 debate 可能形成：

```math
WrongMajority
\to
Communication
\to
HigherConsensus
\to
StrongerWrongMajority.
```

他们通过 prior knowledge elicitation + enforced perspective diversity 减轻这个问题，并报告相对 ReAct +9.5% accuracy，以及相对标准 MAD +19% win rate。

这几乎就是我们之前猜测的：

```math
\boxed{\text{epistemic positive feedback instability}.}
```

现在已经有公开实验支持这种现象。

---

# 14. 因而 Agent Stability 可以开始写一个最小动力学模型

令：

```math
b_i(t)
```

表示 agent `i` 对某 claim 的 belief。

一种粗模型：

```math
b_i(t+1)
=
(1-\alpha)b_i(t)
+
\alpha
\sum_jW_{ij}b_j(t)
+
\beta e_i(t).
```

如果 communication gain 太强：

```math
\alpha\uparrow,
```

而 independent evidence：

```math
\beta e_i
```

太弱，那么：

```math
b_i-b_j\to0.
```

即：

```math
Consensus\uparrow.
```

但：

```math
TruthAccuracy
```

未必上升。

所以必须区分：

```math
\boxed{
ConsensusStability
\neq
EpistemicStability.
}
```

这可能成为 Agent engineering 非常基础的一条原则。

---

# 15. 我现在甚至会重新定义 multi-agent diversity

不是：

```math
D=\text{不同答案数量}.
```

而是：

```math
\boxed{
D_E=
H(
Hypothesis
\mid
IndependentEvidencePaths
).
}
```

也就是 diversity 必须结合 provenance/exposure。

否则让 10 个 agent：

> “请从不同角度回答”

可能只是：

```math
SurfaceDiversity
```

而不是：

```math
EpistemicDiversity.
```

这再次说明我们之前引入 Exposure provenance 是必要的。

---

# 16. ATTS 的源码/配置则进一步确认：test-time scaling 已经在走向 policy problem

我继续读了 [Scaling Test-time Compute for LLM Agents 的官方实现](https://github.com/kangreen0210/ATTS?utm_source=chatgpt.com)。

其 GAIA 实验直接暴露几个 policy parameter：

```math
n_{\rm rollouts},
```

```math
reflection\_threshold,
```

```math
verify\_type,
```

```math
result\_merging\_type.
```

官方实验结论包括：

-  test-time compute 能改善 agent； 
- **when to reflect matters**； 
-  list-wise verification/merging 表现最好； 
-  rollout diversification 有正收益。 

这非常关键，因为：

```math
reflection\_threshold
```

其实就是一个人为设置的 controller。

今天：

```
```

```
if failure_count >= 2:
    reflect()
```

未来应该变成：

```math
\boxed{
Reflect
\iff
E[VOReflection\mid S_t]>C_{reflection}.
}
```

---

# 17. 现在我对 Agent metareasoning 的理论对象更确定了

不是笼统：

> “Agent 应该学会思考多久。”

而是：

```math
\boxed{
\mathcal A_M=
\{
Continue,
Reflect,
Retrieve,
Search,
Verify,
Branch,
Spawn,
AskHuman,
Stop
\}.
}
```

每一个 action 都改变：

```math
Belief
```

或：

```math
CapabilitySurface.
```

于是：

```math
a_t^*
=
\arg\max_a
E[
V(S_{t+1})-V(S_t)-C(a)
].
```

这就是统一的：

```math
\boxed{\textbf{Epistemic Control}.}
```

现在我越来越认为它可能是 Agent Engineering 的“飞行动力学 + 制导律”接口层。

---

# 18. 一个值得注意的负结果：Multi-agent 并不是普遍更经济

ACL 2026 针对 <10B small models 的大规模实验发现：

```math
Base
\to SingleAgent+Tools
```

收益明显；

但：

```math
SingleAgent
\to RoutingMultiAgent
```

增加 coordination overhead，而收益有限。

在其测试条件下，single-agent 给出了最好的 performance/cost balance。

这进一步否定：

```math
\boxed{MultiAgent>SingeAgent}
```

这种架构主义命题。

正确问题始终是：

```math
\boxed{
\text{在当前 operating regime 下，
哪个 computational topology 的 marginal utility 最大？}
}
```

---

# 19. 因此我现在会把“Agent Engineering”理论框架从七块进一步压缩成三个层次

上一版：

```math
T_1,\ldots,T_7.
```

仍然偏 taxonomy。

经过这轮，我觉得更基本的是：

### Layer I — Information Physics

研究：

```math
\boxed{
Observe,\ Store,\ Transmit,\ Integrate.
}
```

核心量：

```math
B_O,\ B_I,\ \rho,\ D_E,\ Freshness,\ Provenance.
```

---

### Layer II — Computational Dynamics

研究：

```math
\boxed{
Search,\ Branch,\ Verify,\ Recover,\ Coordinate.
}
```

核心量：

```math
N_{\rm eff},
B/D,
RecoveryProbability,
VerificationStrength,
CoordinationCapacity.
```

---

### Layer III — Metacontrol

研究：

```math
\boxed{
什么时候改变 Layer I/II 的配置？
}
```

即：

```math
\pi_M:
S_t
\to
(
ObservationPolicy,
ComputePolicy,
TopologyPolicy,
ContextPolicy
).
```

我认为这比“Memory / Planner / Multi-agent / Tool”更接近未来稳定的理论划分。

---

# 20. 现在开始出现一些 candidate engineering laws

我会非常谨慎地称它们为 **hypotheses / proto-laws**，还不是定律。

### `L_1` Effective Diversity Law

```math
Gain_{\rm ensemble}
\propto
N_{\rm eff}
\neq N.
```

已有 ensemble 理论 + 我们 sandbox experiment + debate diversity 结果支持。

### `L_2` Integration Bottleneck Law

```math
R_O>R_I
\Rightarrow
\text{additional observation has diminishing/negative value}.
```

ExtAgents + SILO-BENCH 给出互补证据。

### `L_3` Coordination Complexity Law

```math
C_T>C_A
\Rightarrow
\text{collective performance collapses}.
```

SILO-BENCH / MAS-BENCH 强烈提示。

### `L_4` Context Projection Law

```math
DecisionRelevantContext
>
RawHistory
```

在 long-horizon control 中。

COMPASS/ReSum 等支持。

### `L_5` Verification Coupling Law

```math
Value(Generation)
=
f(VerifierQuality).
```

不能只扩 generation。

### `L_6` Epistemic Feedback Law

```math
Interaction
```

可以降低也可以提高 correlated error：

```math
\rho_{t+1}
=
f(\rho_t,G,C,EvidencePolicy).
```

DReaMAD 给出了直接实证。

### `L_7` Finite Optimal Compute Law

有 action cost 时：

```math
\exists B^*<\infty:
U(B^*)=\max_B U(B).
```

这其实来自 metareasoning，比 LLM 本身更一般。

---

# 21. 这里已经能设计一套真正值得 ADA 做的“风洞实验”

下一阶段我不建议先跑昂贵大 benchmark。

先做最小系统辨识矩阵：

```math
\boxed{
X=
(
ObservationLoad,
Correlation,
Topology,
IntegrationCapacity,
Verification,
Budget
).
}
```

输出：

```math
Y=
(
Success,
Regret,
Cost,
Recovery,
Calibration,
Diversity
).
```

然后局部估计：

```math
J_X
=
\frac{\partial Y}{\partial X}.
```

以及：

```math
H_X
=
\frac{\partial^2Y}{\partial X^2}.
```

寻找：

-  saturation； 
-  interaction； 
-  threshold； 
-  bifurcation； 
-  regime boundary。 

这才真正类似“气动导数辨识”。

---

# 22. 我现在最想先做的真实实验不是 N-agent benchmark，而是 2×2×2

例如：

```math
Correlation\in\{low,high\},
```

```math
Integration\in\{weak,strong\},
```

```math
Verification\in\{off,on\}.
```

得到八个 regime。

然后看：

```math
\frac{\partial J}{\partial N}
```

在八种 regime 是否符号不同。

我的理论预测是：

```math
\boxed{
\frac{\partial J}{\partial N}>0
}
```

只在：

```math
Diversity
\times
Integration
\times
Verification
```

都达到一定水平时稳定成立。

换言之：

```math
\boxed{
MultiAgentGain
\approx
D\times I\times V-C.
}
```

如果其中任一：

```math
\approx0,
```

增加 agent 都可能主要增加 cost。

这是非常容易证伪、而且工程价值很高的假说。

---

# 23. 相比上一轮，我认为最重要的新认识已经变了

上一轮我最关注：

```math
\boxed{Decision-Sufficient State.}
```

它仍然重要。

但现在我认为真正的中心对象可能是：

```math
\boxed{\textbf{Epistemic Bandwidth Allocation}.}
```

Agent 每一步都在决定：

> 获取多少信息？

> 从哪里获取？

> 让谁获取？

> 谁能看到？

> 如何压缩？

> 谁来整合？

> 是否验证？

> 还值得继续买吗？

因此整个系统其实是在管理：

```math
\boxed{
\text{information flow under bounded compute}.
}
```

这把：

```math
Context,
Memory,
Retrieval,
MultiAgent,
Search,
Human,
WorldModel
```

第一次真正放到了一个共同数学对象下面。

---

而且这轮有一个我觉得非常符合你“航空工程”直觉的结果：我们还没有 Navier–Stokes 式的 Agent 基础理论，但已经开始看到类似 **stall、saturation、coupling、capacity、operating envelope、feedback instability** 的重复实验现象了。

所以接下来最值得做的已经不是继续给 Agent 组件命名，而是开始系统地**测这些曲线、寻找 regime boundary、构造无量纲变量、做跨模型/跨任务复现实验**。如果其中哪怕两三个关系能跨模型稳定存在，Agent Engineering 就开始真正拥有自己的工程理论了。