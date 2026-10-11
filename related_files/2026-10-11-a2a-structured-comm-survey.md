# A2A 结构化通信规范梳理（web 席粘贴稿，2026-10-11）

**来源与级据**：用户在 2026-10-11 会话中直接粘贴的 web 侧梳理文本（「主流多智能体系统认识」通道）。
本文件为**逐字存档**（【转述】级、**URL/ID 未钉版**——文中出现的 A2A v1.0.1、ANP 1.2、FIPA ACL、
AGNTCY OASF、AutoGen、PACT、Magentic-One、AG-UI、ATIF 等标识符均未按 ID 核验，入册前须钉版）。
用途：w6 两臂实验中 **R 臂（结构化交接）**的字段参考（见文末「最小 Research Message Schema」）。

用户的指令（逐字保留）：「我认为两arm的实验:n:不在上下文中规定结构/要求结构,只描述环境信息:无人类干预,
纯A2A协作,协作方式交给agent自主实现,R:参考这些设计符合我们通用实验要求的字段指定结构进行A2A(目前不实现
自动程序核验):」——其后即粘贴本文档全文。

---

# 目前的 A2A 结构化通信规范：2026 年 10 月梳理

结合你正在研究的 Qwen / DeepSeek 异构协作、Autoresearch、并发 Sandbox、ATIF 轨迹和缓存成本优化，我认为现有规范需要分成三类，否则很容易把不同层次的东西混淆：

1. 通信协议（Interoperability Protocol）：解决 Agent 如何发现彼此、发出任务、传送消息、获取结果。
2. 协作语义（Collaboration Semantics）：解决消息表示请求、提议、证据、执行结果、反对意见，还是验收结论。
3. 状态与记录规范（State / Trace Schema）：解决共享什么状态、如何引用实验产物、怎样恢复和审计。

目前第一类已经出现生产级标准，第二类有成熟的经典理论和新近实证论文，第三类则有多套互补实现，但尚未形成统一的 Autoresearch 专用规范。

## 一、值得关注的现有标准

| 标准或设计 | 结构化程度 | 主要解决的问题 | 当前状态 |
| --- | --- | --- | --- |
| Google / Linux Foundation A2A | 正式协议与数据模型 | Agent 发现、任务生命周期、消息、Artifact、流式交互 | v1.0.1 稳定发布 |
| ANP | 身份、发现、加密消息、Profile 协商 | 跨域 Agent 网络 | 1.2 规范系列；部分模块仍为草案 |
| FIPA ACL | 消息结构 + 通信行为语义 | 请求、通知、提议、接受、拒绝、协商 | 经典正式标准 |
| AGNTCY OASF | 类型化 Agent 描述 Schema | 能力、领域、身份与发现 | 持续维护 |
| AutoGen StructuredMessage | Pydantic 类型化消息 | 框架内部 A2A 消息和交接 | 已实现 |
| PACT | 行动—状态通信记录 | 降低共享历史冗余，提高后续行动有效性 | 2026 年论文与开源实现 |
| Magentic-One Ledgers | 任务和进度状态结构 | 长程协作、规划与恢复 | 已实现的架构模式 |

版本细节：原 IBM 提出的 ACP（Agent Communication Protocol）已并入 Linux Foundation 的 A2A 生态，不宜再视作与 A2A 平行竞争的独立路线。

## 二、A2A v1.0：目前最成熟的跨框架协议

A2A 于 2026-03-12 发布 v1.0，5 月发布 v1.0.1；官方 TypeScript SDK 支持 HTTP+JSON、JSON-RPC、gRPC 三种绑定。六种核心数据对象：AgentCard（身份/能力/接口/Skills/认证）、Message/Part（请求、补充信息、结构化 JSON、文件引用）、Task/TaskStatus（异步执行、工作中、完成、失败、取消、需要输入）、Artifact（正式结果与交付物）、TaskStatusUpdate/TaskArtifactUpdate（进展与增量交付）。官方建议把正式输出放入 Artifact，而不是当作普通聊天消息发送。

消息结构（简化 TypeScript 表达）：

```
interface A2AMessage {
  messageId: string;
  contextId?: string;
  taskId?: string;
  role: "ROLE_USER" | "ROLE_AGENT";
  parts: Part[];
  metadata?: Record<string, unknown>;
  extensions?: string[];
  referenceTaskIds?: string[];
}
```

`Part` 四种形式之一：`text` / `data`（结构化 JSON）/ `url`（文件引用）/ `raw`（内嵌二进制）。

符合 A2A 字段组织方式的交接示例：

```
{
  "messageId": "msg-0042",
  "role": "ROLE_USER",
  "parts": [
    {
      "data": {
        "operation": "verify_experiment",
        "artifact_id": "sha256:abc123",
        "objective": "Check spatial distance implementation",
        "acceptance": ["Validate boundary handling", "Compare independent EDT results"]
      },
      "mediaType": "application/json"
    }
  ]
}
```

注意：`operation`、`artifact_id`、`acceptance` 是自定义业务字段；A2A 只规定它们可经 `Part.data` 传送。A2A 的 `role` 是客户端/服务端角色，不是科研团队的"规划者/执行者/验证者"。

A2A 原生扩展机制：可通过 AgentCard 声明扩展，在 Message 与 Artifact 附加版本化扩展元数据（例如自定义 `Research Evidence Extension`，不改核心协议）。现实限制：官方 2026-09 路线图仍把双向流、复杂多轮协商、任务时间线列为后续增强项。

## 三、FIPA ACL：最值得重新研究的"通信语义"标准

FIPA ACL 直接回答"Agent 发出一条消息，究竟希望接收方采取什么行为"。其消息结构 2002 年标准化，含 13 字段，最重要的是 `performative`：

| Performative | 含义 | Autoresearch 场景 |
| --- | --- | --- |
| `request` | 请求执行行动 | 要求另一个 Agent 检查算法 |
| `inform` | 告知事实或结论 | 通知实验结果已产生 |
| `query-if` | 查询命题是否成立 | 询问某实现是否正确 |
| `cfp` | 征集方案 | 向多个模型征集优化路线 |
| `propose` | 提交方案 | 提供实验计划及预算 |
| `accept-proposal` | 接受提案 | 授权执行候选实验 |
| `reject-proposal` | 拒绝提案 | 拒绝收益不足的实验 |
| `failure` | 报告行动失败 | 说明无法通过验证 |
| `refuse` | 拒绝执行请求 | 资源、权限或能力不满足 |

与普通 JSON 消息的区别：FIPA 为通信行为规定了形式语义（可行性前提 Feasibility Precondition、理性效果 Rational Effect）。

FIPA 的 Contract Net Interaction Protocol：Coordinator → 多 Agent CFP（提交方案、预算、预计完成时间）→ PROPOSE → 接受/拒绝 → 执行 → 报告。可发展为异构模型任务分配协议；但 LLM 自报"90% 把握"未必校准，不能直接作为路由真值。

判断：借鉴其通信行为与协商状态机，不必采用全部历史编码体系；语义可放入 A2A 的结构化数据部分。

## 四、ANP：开放网络中的身份、发现与协议协商

ANP 关注跨域 Agent 网络：DID 身份认证与发现、Agent Description 与能力声明、消息传输/群组通信/端到端加密、协议与 Schema 协商。1.2 系列含多个已发布 Profile，但 ANP-06 Meta-Protocol 仍为草案。最值得吸收：Discover → Capabilities → Negotiate → Execute。同一 Harbor 环境内（同基础设施与信任域）不必然需要完整 DID/跨域加密，属可选研究参考。

## 五、AutoGen、PACT、Magentic-One：贴近协作内容的工程设计

- **AutoGen AgentChat**：`StructuredMessage[T]`（Pydantic）、`HandoffMessage`（source/target/content/可传递模型上下文）、`ToolCallExecutionEvent`、`TaskResult`；`BaseChatMessage` 与 `BaseAgentEvent` 分离（交互 vs 可观测事件）。注意 `HandoffMessage.context` 仍允许直接传递完整模型消息历史——对缓存/上下文/通信成本敏感的系统应视其为可选策略而非默认。
- **PACT**：公开实现要求发送三项——`Action Required / Environment State / Action Result`，并将私有推理从公共消息历史中剔除；是提示模板驱动的结构化通信约定，而非强类型 Schema 标准。研究价值在内容选择：只把接收方需要的行动、环境证据与结果放入公共状态。
- **Magentic-One**：Task Ledger（已知事实、待确认事实、猜测、当前计划）+ Progress Ledger（正在执行步骤、进度、循环检测、后续分配）。值得保留：事实/猜测/待验证命题分离，研究计划与已发生执行过程分离；Ledger 可作共享状态对象而非中央 Orchestrator 专属。
- **AGNTCY OASF**：统一属性/技能/领域描述 Agent，支持 Schema 校验与扩展；对模型路由有价值，但不决定每次交流该传哪些证据。

## 六、两类易混淆的规范

- **AG-UI**：Agent 与前端之间的事件流（STATE_SNAPSHOT / STATE_DELTA（JSON Patch）/ TOOL_CALL_* / 子 Agent 事件），适合轨迹可视化；不是 Agent 间委派协商的核心规范。
- **Harbor ATIF**：已执行行动的轨迹交换格式，适合保存工具调用、模型消息、观测与指标。

三者关系：A2A=实际通信 · ATIF=完整轨迹 · AG-UI=状态展示；可用相同 runId/taskId/messageId 关联，不应互相代替。

## 七、按四个问题比较规范

| 设计 | 能否跨 Qwen / DeepSeek | 是否规定行为语义 | 是否支持复杂研究状态 | 对当前实验的价值 |
| --- | --- | --- | --- | --- |
| A2A v1.0 | 是 | 任务生命周期层面 | 可扩展 | 很高 |
| FIPA ACL | 与模型无关 | 是，定义通信行为 | 需扩展内容模型 | 很高 |
| ANP | 是 | 协议协商层面 | 可扩展 | 中，当前可能过重 |
| AutoGen | 支持多模型适配 | 框架内约定 | 类型化消息与交接 | 高，适合参考实现 |
| PACT | 文本模型均可试用 | 行动—状态—结果 | 尚不完整 | 很高，适合消融实验 |
| Magentic-One | 支持不同模型 | 规划和进度管理 | 任务与进度 Ledger | 高 |
| AGNTCY OASF | 与模型无关 | 能力语义 | Agent 元数据 | 中 |
| ATIF / AG-UI | 与模型无关 | 执行 / 展示事件 | 轨迹或状态同步 | 高，但不负责协作语义 |

建议避免把"某模型擅长规划/验证/执行"预先固定成硬角色。

推荐组合：A2A v1.0（任务与传输层：AgentCard/Task/Message/Part/Artifact/Status）· FIPA-inspired（通信行为层：request/inform/propose/accept/reject/failure）· PACT-inspired（研究内容层：Action/State/Result + Evidence/Artifact/Acceptance）· ATIF（独立记录层）。

## 八、建议实际测试的最小 Research Message Schema

非另造协议，而是可放入 A2A `Part.data` 的实验性领域 Schema：

```
{
  "messageId": "msg-0042",
  "role": "ROLE_USER",
  "parts": [
    {
      "mediaType": "application/json",
      "data": {
        "schema": "research-handoff/0.1",
        "act": "request",
        "operation": "verify",
        "objective": "Validate signed distance implementation",
        "state": {
          "checkpoint": "cp-39",
          "artifact_refs": ["sha256:code-v3"],
          "evidence_refs": ["event-39"]
        },
        "constraints": { "deadline_ms": 60000, "max_cost_usd": 0.05 },
        "acceptance": ["Reproduce the error", "Check independent distance computation"]
      }
    }
  ]
}
```

`act` 借鉴 FIPA；`operation`/`state`/`acceptance` 为研究语义；A2A 负责实际交接；`checkpoint` 与 `artifact_refs` 必须可被接收 Agent 通过授权资源服务解析。不要求完整推理或长篇解释，但保留操作目标、证据与验收条件。进一步可做模型适配器 φ_Qwen/φ_DeepSeek 呈现同一语义对象的不同形式——需实验证明其优于直接同 JSON，不能预设。

为什么不建议第一版更复杂：已有明确可证伪问题——**A2A 类型化数据 + FIPA 行为标识 + PACT 式内容选择，是否优于自由文本消息与完整历史交接？** 可在同 Benchmark、模型组合与预算下比较（A 自由文本 / B 完整历史 / C PACT 三字段 / D 结构化 Research Handoff / E D+Artifact 引用及按需证据获取）；主要比准确率，次要比墙钟、按缓存命中计的真实账单、信息丢失率与错误传播。结构化消息并非天然更省 token——字段名、JSON 编码与额外解析都可能增加开销，其价值须由 Cache Hit/Miss 与下游行动质量验证。

标准细节：A2A v1.0 明确不能假设 `Task.history` 保存了所有消息，也不能把可能中断的流式 Message 当作关键事实的可靠存储——影响重放或评分的通信应独立写入不可变事件记录或正式 Artifact。

## 九、最终判断

- A2A v1.0：已解决跨 Agent 任务互操作；FIPA ACL：已形式化通信行为；PACT：开始实证研究应共享什么；AutoGen/Magentic-One：可借鉴的工程结构；ANP/OASF：跨域发现、身份与能力；ATIF：使通信与执行可分析可审计。
- 真正缺少：一个被大规模 Autoresearch 实验证明优于自由文本通信的、具备决策与证据语义且考虑缓存成本的统一协作 Schema。
- 对当前 Harbor + Qwen Code + DeepSeek 实验：从 A2A v1.0.1 数据模型、FIPA 少量通信行为、PACT 行动—状态内容出发做独立消融；不急于引入 ANP 完整协议栈，不预先优化为模型不可读内部编码。
- 最值得研究的目标：**最小且充分的信息传递 ⇒ 更高的正确行动概率**，而不是消息越短越好、越结构化越好、越不接近人类语言越好。
