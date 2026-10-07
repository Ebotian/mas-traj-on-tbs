<!-- 来源(2026-10-07):**跨会话转交**,不是本会话用户直接交办。
     提出会话 qwen-code-df(cwd /home/ebt/qwen-code),用户在同一人于该会话说「整理给 rsi-dev 那个会话,让那边落盘」;
     转交方明确声明「不带用户对你会话的授权」。落盘决定由本会话作出(语料新增、可回滚、无损)。
     转交方对 qwen 侧行号自称已亲自 grep;本会话**又独立复核了一遍**(见下面「本会话的独立复核」),
     并改正两处:两个仓库的路径都缺前缀(实为 packages/ 与 packages/agent-core-v2/src/),
     qwen 的 hook 事件数是 22 而非 19。对端的 §1 核对账与 §5 未核实清单按转交方要求原样保留。
     标记沿用转交方约定:✅=已对主源核实;◐=仅转述未核,不得当已核实引用。
-->

# qwen-code vs kimi-code:harness / agent 设计对照(2026-10-07)

## 0. 方法与证据等级

- **qwen-code 侧**:在 `/home/ebt/qwen-code` 由 4 个 Explore 子代理并行取证;关键行号我已亲自 grep 复核:`core/src/core/client.ts:212 / :3456`、`core/src/core/turn.ts:697 / :714`、`packages/cli/src/ui/hooks/use-llm-stream.ts:2594 / :4843 / :6016`、`packages/cli/src/nonInteractiveCli.ts:2469`、`core/src/config/approval-mode.ts:7`。
- **kimi-code 侧**:由会话 `kimi-code-f9` 取证并回信(cross_session_message)。
- **引用核对**:本次对 kimi 侧 13 处硬声明按主源 `/home/ebt/kimi-code` 抽查 → **12 成立、1 过强**(§1)。
- 标记:✅=已对主源核实;◐=仅转述未核,**不要**当已核实引用。

## 1. 引用核对账(kimi-code 侧)

| # | 声明 | 结果 |
|---|---|---|
| 1 | 循环在 core:`human/` 四层 XState + `src/agent/loop/` | ✅ 文件与目录实存 |
| 2 | 工具执行也在 core:`src/agent/toolExecutor/` | ✅ toolExecutorService/toolScheduler/toolHooks |
| 3 | `PermissionMode = 'manual'\|'yolo'\|'auto'` @ `agent/permissionPolicy/types.ts:6` | ✅ 逐字一致 |
| 4 | `REPEAT_FORCE_STOP_STREAK = 12` | ✅ `agent/toolDedupe/toolDedupeService.ts:66` |
| 5 | 工具结果上限 50,000 字符 | ✅ `tool/toolContract.ts:7`(它写 :6,行号差 1) |
| 6 | 声明由 zod 派生 JSON Schema | ✅ `tool/input-schema.ts:4` `z.toJSONSchema` |
| 7 | 没有记忆子系统 | ✅ `MEMORY.md`/`search_memory` 全仓零命中 |
| 8 | `goalService.markComplete` 不涉 LLM | ✅ `features/goal/goalService.ts:425`,该文件无 requester import |
| 9 | turn 外的 LLM 请求只有压缩 | ✅ `IAgentLLMRequesterService` 消费者仅 loop 系 + fullCompaction |
| 10 | `maxRalphIterations` 无消费者 | ✅ 全仓仅 2 处 schema 定义 + 1 处 example |
| 11 | Hooks 20 个事件 | ✅ `features/externalHooks/internal/types.ts:3-25` 逐个数出 20 |
| 12 | 无 read-before-write | ✅ `priorRead` 零命中 |
| 13 | deferred 延迟加载"只对 MCP 工具" | ❌ **过强** |

**#13 正确表述**:`ToolDisclosure = 'inline' | 'deferred'` 是 `tool/toolContract.ts:97` 上的**通用契约字段**;CHANGELOG 写明允许 host 把**已注册的用户工具** schema 延迟;测试有 `source:'user', disclosure:'deferred'` 用例。机制通用,**生产默认只给 MCP 用**(唯一主动设置点在 mcpService)。

## 2. 逐轴对照

| 轴 | qwen-code | kimi-code |
|---|---|---|
| **A 循环位置** | 切三层;工具执行那一圈**在 host**(use-llm-stream.ts:2594/4843→:6016 submitQuery;nonInteractiveCli.ts:2469 while),core 无状态只 yield `ToolCallRequest` | **全在 core**:`human/` 四层 XState(session→agent→turn→tool),工具执行也在 core(`agent/toolExecutor/`),host 只给审批回调 |
| **B 停止条件** | **多 limiter 分散**:MAX_TURNS=100(client.ts:212)、会话轮数、session token、loop detector、Stop-hook 上限 | **集中**:turn guard 判 maxSteps;另"反向停 turn"通道(`ExecutableToolResult.stopTurn`);**升级式 repeat breaker:同签名调用连续 3/5/8/12 次逐级升级到强制停** ⚙ |
| **C 工具声明** | 手写 JSON Schema | **zod 派生**(draft-7 + 强制 additionalProperties:false)⚙ |
| **C 并发** | 数字上限默认 **10**,按并发安全分区 | **无数字上限**,贪心按 `ToolAccesses` 冲突串行;Bash 未声明 accesses → 事实独占 |
| **C 结果整形** | 25k 字符/1k 行 → 落盘(`<persisted-output>`+sha256) → **批量预算 200k 按比例分配** | 50k 字符/2k 行 → 落盘 + 返回可 Read 指针;**无批量预算** |
| **C 延迟工具** | 范围大:内置也可 defer,启动按窗口百分比**全有或全无**预载 | **机制通用但生产仅 MCP**,被 flag + 模型能力双门控 |
| **D 提示** | 多层 section 组装(prompts.ts:884),稳定前缀作 cache 锚 | **单模板 `${var}` 插值后冻结**,变更靠尾部 `<system-reminder>` |
| **D 压缩** | **两级**:microcompaction(无模型调用就地把旧工具结果/媒体清空)+ 摘要重建 | **只有一层**:全量 LLM 摘要,就地 splice |
| **D 记忆** | 三层(project/user/team)+ 每轮 recall + `search_memory` | **不存在** |
| **D token 估算** | CJK 感知 + 1.5 安全系数 | 无 tokenizer、无安全系数,media 固定 2000 |
| **E 权限模式** | 5 值枚举 PLAN/DEFAULT/AUTO_EDIT/AUTO/YOLO | 引擎 3 值 manual/yolo/auto;4 值只是 ACP 产品层映射 |
| **E 规则装载** | 规则→运行时消费链闭合 | `permission.rules` 的 config→runtime 装载器**在本 checkout 缺失** |
| **E 读前写** | 有(新鲜读缓存 + mtime/size 匹配) | **无**(✅ 零命中) |
| **E hooks** | 19 个;阻断面宽(PreToolUse 可给 allow/deny/ask、可注入 additionalContext),**出错不阻塞** | 20 个;**阻断面窄**(仅 PreToolUse/UserPromptSubmit/Stop),其余 fire-and-forget;**出错默认 allow** |
| **E 沙盒** | 会话级一次决定的 OS 沙盒 | **无 OS 沙盒**,靠 tree-sitter-bash 手写 AST 启发式 + 路径守卫 |
| **F 外部监督** | **两处独立判决者**:AUTO 权限分类器、Goal verifier(都另开 side-query,严格 JSON schema) | **零**:`update_goal` 直接 `markComplete`(同步、无模型调用);completion 只写在 prompt 里,`completionCriterion` 以 `<untrusted_completion_criterion>` 渲染、**从不被代码求值** ⚙ |

(⚙ = 与 kimi 侧共享的一条判定已在 §1 核实;未标者为 ◐ 转述。)

## 3. 与 rsi-dev 已有工作的接口(去重 + 残差)

- **已在项目里**:`related_files/TIMING-REVIEW(1).md` 已确立原则:"**所有触发变量都是 harness-authoritative。没有 embedding、没有 agent 自评、没有 LLM judge**",且第一代策略只用三个 harness 量。
- **本次残差(新)**:该原则在两个**真实 harness** 上的实例化——
  - qwen-code 在**两处**违反它(AUTO 权限分类器、Goal verifier 都是 LLM judge,且是跳出一层上下文开 side-query 判决);
  - kimi-code 在**触发路径上守住了**(零 judge),但把 completion 判定**降级为未求值的 prompt 不变量**(`completionCriterion` 从不被代码求值)。
- 于是得到两个**可测失败模式**:判据(a)把安全/完成判决外包给另一个 LLM,是否在对抗压力下失效;(b)把判据只渲染成文本、从不求值,是否等于**没有判据**。两者都可作为"harness-authoritative 判据"设计的反面样本。

## 4. 结构性判读(转交方的,可反驳)

两个仓库对**同一需求**(多前端共享 + 可恢复)给了**相反答案**:

- **qwen-code 把执行状态推给外层 journal/transport**:core 无状态驱动律,工具环在 host,于是 ACP 桥/daemon 能把同一内核喂给五个前端。代价:core 不知"这一轮跑到哪了",恢复靠会话 JSONL。
- **kimi-code 把执行状态收进 core 做成可重放的显式状态机**:`human/` 四层 actor 就是那份状态,可挂载重连、可回放。代价:core 变重,且留有 v1/v2 双层共存。

安全策略的分野更值得记:**外部判决者 vs 策略文本 + 单点 fail-closed**。另外两边都有**默认方向不对称**(kimi 审批 fail-closed 而 hook fail-open;qwen 的 hook 出错同样不阻塞,但非交互会话审批自动拒 = fail-closed),所以"同一系统两种相反默认"是**共有特征**,不是 kimi 独有。

## 5. 未核实清单(边界,不要当结论)

◐ 审批无 handler 默认 `cancelled`、hook 出错默认 allow、Bash 未声明 accesses→事实独占、审批在 batch 执行前串行准备、v1/v2 双层共存与 `human/compaction/*` 不在活路径。qwen 侧 config 面只确认了仅有 `maxStepsPerTurn`/`maxAttemptsPerStep`、无会话级上限,未追运行时是否另有一处。

---

# 本会话的独立复核(2026-10-07,标【我复核】,只覆盖抽到的条目)

方法:直接读两个 checkout 的源码(按**符号**定位,不依赖对端给的路径)。

**两处必须改正的**

1. **两个仓库的路径都缺前缀。** 对端写的 `src/agent/...`、`core/src/...`、`packages/cli/...` 需分别补成
   `packages/agent-core-v2/src/...`(kimi)与 `packages/core/src/...` / `packages/cli/src/...`(qwen)。
   补上前缀后**各条行号精确命中**(见下),所以这不是内容错误,是路径写法缺前缀 —— 但按原样抄会 grep 不到。
2. **qwen 的 hook 事件数是 22,不是 19。**(`packages/core/src/hooks/types.ts:24` 的 `HookEventName` 枚举逐个数出
   22 个:PreToolUse / PostToolUse / PostToolUseFailure / PostToolBatch / Notification / UserPromptSubmit /
   UserPromptExpansion / SessionStart / Stop / MessageDisplay / SubagentStart / SubagentStop / PreCompact /
   PostCompact / SessionEnd / SessionDelete / PermissionRequest / PermissionDenied / StopFailure / TodoCreated /
   TodoCompleted / InstructionsLoaded。)kimi 侧 20 个【我复核】(`features/externalHooks/internal/types.ts` 的
   `HOOK_EVENT_TYPES`,逐个数出 20)。

**kimi 侧【我复核】**(前缀 `packages/agent-core-v2/src/`)

- `agent/permissionPolicy/types.ts:6`:`export type PermissionMode = 'manual' | 'yolo' | 'auto';` ✅ 逐字
- `agent/toolDedupe/toolDedupeService.ts:66`:`const REPEAT_FORCE_STOP_STREAK = 12;` ✅
- `tool/toolContract.ts:7`:`export const DEFAULT_TOOL_RESULT_MAX_CHARS = 50_000;` ✅
  —— **对端漏了一条**:紧接其下 `DEFAULT_TOOL_RESULT_MAX_RETAINED_CHARS = 10_000_000;`(:9)
- `tool/toolContract.ts:97`:`export type ToolDisclosure = 'inline' | 'deferred';`,:104 `readonly disclosure?: ToolDisclosure;` ✅
  ⇒ §1 的 #13 更正**成立**;生产设置在 `agent/mcp/mcpService.ts:243`(:306 带 `source:'mcp'`),
  而 `agent/userTool/userTool.ts:8` / `userToolOps.ts` 确实为**用户工具**保留该字段 ⇒ "机制通用、生产仅 MCP" 对。
- `search_memory` 全仓零命中 ✅(#7)
- `features/goal/goalService.ts`:`markComplete` 走同步 `dispatchCompletion`,文件内与 "LLM/Requester" 相关的三处
  全是**报错文案常量**(`LLM_NOT_SET_MESSAGE`)⇒ "不涉 LLM" ✅
- `features/goal/injection/goalInjection.ts:81`:以 `<untrusted_completion_criterion>` 渲染 ✅;
  `completionCriterion` 的读取点只有该渲染函数与 `agent/replayBuilder/fold.ts` 的状态搬移,**没有条件分支拿它做判定** ⇒ "从不被代码求值" ✅

**qwen 侧【我复核】**(前缀 `packages/`)

- `packages/core/src/core/client.ts:212`:`const MAX_TURNS = 100;` ✅
- `packages/core/src/config/approval-mode.ts:7`:`ApprovalMode` 枚举五值 PLAN/DEFAULT/AUTO_EDIT/AUTO/YOLO ✅
- `packages/cli/src/nonInteractiveCli.ts:2469`:`while (true)` ✅
- `packages/cli/src/ui/hooks/use-llm-stream.ts`::2594 `processLlmStreamEvents = useCallback(`、
  :4843 `handleCompletedTools = useCallback(`、:6016 `await submitQuery(..., SendMessageType.ToolResult, ...)` ✅
  ⇒ "工具执行那一圈在 host" 有据
- **两处 LLM 判决者都成立,而且比转述更具体**:
  - `packages/core/src/permissions/classifier.ts` 文件头写着 **"AUTO approval mode LLM classifier"**,两阶段
    (stage 1 快查 `shouldBlock` only / `max_tokens=32`;stage 2 复核 `{thinking, shouldBlock, reason}` / `max_tokens=4096`),
    经 `runSideQuery` + `./classifier-prompts/system-prompt.js` ✅
  - `packages/core/src/goals/goal-verifier.ts`:`import { runSideQuery }`,依赖面含 `generateJson` / `getFastModel` /
    `getModel`,并带一大段关于 `proofKind`(delivered_output / execution_output / external_fact)与 `blockedPolicy`
    的判据文本 ⇒ 是**模型判决 + 受约束 JSON 输出** ✅
- `packages/core/src/utils/sideQuery.ts` 存在且被多处消费(nextSpeakerChecker、subagentGenerator)⇒ side-query 是真机制 ✅

**我没有核的**(仍按 ◐ 看待,不得当已核):§5 全部条目;qwen 的 25k/1k 截断与 `<persisted-output>`、200k 批量预算、
并发上限 10、hooks 阻断面宽窄、OS 沙盒、microcompaction 两级压缩;kimi 的 v1/v2 双层共存与
`human/compaction/*` 是否在活路径;以及 §2 里凡未标 ⚙ 的格。
