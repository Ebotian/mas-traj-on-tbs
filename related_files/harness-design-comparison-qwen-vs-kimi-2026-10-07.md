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

---

# 未解决问题(本节由本会话 2026-10-07 补入;2026-10-08 依用户裁定改写;**均未**进入登记册)

用户裁定(2026-10-08):「失败模式可以记为现存的不同实现思路.论文支撑可以补充」——
故 A1/A2 不再是"候选失败模式",而是**两个仓库各自现存的实现思路**(已在本机逐条核实,见 §0 与上面的【我复核】),
下面各配**论文支撑**与**若要判别所需的实验**。
**论文支撑的核验边界**:这里的 arXiv ID 我逐条用 arXiv API 核过存在性与标题(见第三条对话 README §3 的 15 条 + 本会话另核的 9 条);**论文内部的数字未回正文核对**。要进 `viz/src/data/corpus.ts` 的决策册/冲突册仍需用户裁定。

## A1 · 现存思路一:把判决交给另一个 LLM(抽样自 qwen-code)

**做法**:判据不在确定性代码里,而是**另开一次 side-query**,让一个模型按受约束的 JSON 输出判决。

| 项 | 内容 |
|---|---|
| 实例 | `packages/core/src/permissions/classifier.ts`(文件头自称 "AUTO approval mode LLM classifier",两阶段:stage 1 只出 `shouldBlock`/32 tokens,stage 2 出 `{thinking, shouldBlock, reason}`/4096 tokens);`packages/core/src/goals/goal-verifier.ts`(`runSideQuery` + `generateJson`,带 `proofKind` 与 `blockedPolicy` 判据文本) |
| 同一仓的对照路径 | `packages/core/src/shell-safety-rules.ts` / shell AST 路径(确定性规则) |
| 论文支撑 | **AutoHarness(2603.03329)**——自动合成**代码**型 harness 而不是让模型临场判;该方向把"判决"往确定性一侧推。**Phantom Guardrails(2607.13083)**——自检型机制会**虚构并不存在的失败**(15/60 vs 对照 0/60),且要求"无变更"必须是合法输出。**METR 的受控长程对比**(见 `related_files/conversation-openai-math-engineering-implications-2026-10-07/README.md` 的增量段第 9 轮:Claude Code 胜 ReAct 的 bootstrap 样本仅 50.7%,Codex 胜 Triframe 14.5%)——产品级 scaffold 的复杂度**不等于**更强的自主视野。**Resample or Reroute?(2607.08665)**——收益**随验证器质量下降而缩小**,即"判决者的质量"是收益的一阶变量。 |
| 若要判别(可选,不是本条的成立条件) | 一个共享的对抗命令集 + 两条路径各自的漏放计数;两者都在本机可跑 |

## A2 · 现存思路二:判据只渲染进 prompt,从不被代码求值(抽样自 kimi-code)

**做法**:判据作为**prompt 里的不变量**交付给模型自守,harness 侧不执行它。

| 项 | 内容 |
|---|---|
| 实例 | `features/goal/injection/goalInjection.ts:81` 把 `completionCriterion` 渲染成 `<untrusted_completion_criterion>`;`update_goal` 直接同步 `markComplete`(无模型调用);全仓 `completionCriterion` 无求值分支(只有渲染与状态搬移) |
| 对比其触发路径 | 触发路径上**零 judge**(这是它的强项):`REPEAT_FORCE_STOP_STREAK = 12` 等判据全在代码里 |
| 论文支撑 | **How Much of a Harness Does a Strong Agent Need?(2609.40303)**——最小 harness 已可与复杂 harness 相当 ⇒ 把判据写进 prompt 不算"缺 harness",但也不等于判据生效。**Beyond the Model(2609.32459)**——组件的有用性**依任务而变**,故"渲染即生效"不能被默认。**τ-bench(2406.12045)** 与**基于状态的校验**路线证明:判据一旦可执行,就能测 `pass^k` 这类**重复成功**;反之只能测单次自述。**PaperBench(2504.01848)** 更进一步——它**为自己的判官另建一个 benchmark**,即"判据本身也要被测"。 |
| 若要判别(可选) | 一组任务 + 两种 harness 各自的"完成"判定;或对 kimi 单臂做"骗过渲染层"的注入试验 |

## A3 · 这两个思路在同一张轴上的位置

把 A1/A2 与项目原则并排,可见**这不是"有无判据"的二分,而是两个独立的轴**:

| 轴 | 含义 | qwen | kimi | 项目原则(`TIMING-REVIEW(1).md`) |
|---|---|---|---|---|
| 判据在哪 | 由谁执行 | **harness 外的另一个 LLM** | prompt 文本(harness 不执行) | 必须在 harness 里,且不外包给 LLM |
| 判据能否执行 | 是否被代码求值 | 能(结构化输出被消费) | **不能**(只渲染) | 必须可执行 |

⇒ **两个真实 harness 都不满足"三条件同时成立"**(判据在 harness 里 · 被代码求值 · 不外包给 LLM)。
**更正(2026-10-08,外部复核指出,我核过)**:此前我写"各只满足两条/各缺一条"——那个计数**站不住**,原因有三:
① 表里 qwen 的"位置"格写的是"harness 外",按同一原则它在那条轴上就已经不满足,不止"可执行"那条;
② A1 比的是 qwen 的**安全判决**、A2 比的是 kimi 的**完成判据**,**不是同一种判据**,直接并列会串味;
③ "执行一个 JSON 判决"与"执行判据本身"不是一回事 —— 前者是消费模型的输出,后者是代码判定。
故**不给数量**,改按复核建议**逐格填表**:对**同一种**判据(先只做"完成"这一种),分别填 *位置 / 实际求值者 / 结果消费者* 三格,
再判它满足哪几条。源码不随包 ⇒ **该表在包内不可判定**,需回到固定提交的调用链上核(两个提交已记在 U3 末行)。

## U3 · 未核清单(◐)的**核法**(把 §5 与上面「我没有核的」变成可执行的检查)

| 待核项 | 怎么核(都在本机) |
|---|---|
| qwen 结果整形 25k/1k、`<persisted-output>`、200k 批量预算 | `grep -rn "25_000\|25000\|persisted-output\|200_000" packages/core/src packages/cli/src` |
| qwen 并发上限 10 与并发安全分区 | 找并发常量 + 分区函数,读它在 batch 执行前的串行准备 |
| qwen hooks:阻断面宽窄、出错不阻塞 | 读 `packages/core/src/hooks/hookRunner.ts` 的错误分支与 allow/deny/ask 出口 |
| qwen OS 沙盒(会话级一次决定) | 找 sandbox 决策点与其生命周期 |
| qwen microcompaction 两级压缩 | 找 microcompaction 模块与它是否发起模型调用 |
| kimi v1/v2 双层共存、`human/compaction/*` 是否在活路径 | 从入口(CLI/sdk)沿 import 图走到 `agent-core-v2`,看 v1 是否仍被引用 |
| kimi 审批无 handler 默认 `cancelled`;hook 出错默认 allow;Bash 未声明 accesses→事实独占 | 分别读 `permissionPolicy` 默认分支、hooks 错误分支、`ToolAccesses` 缺省语义 |
| 环境与版本 | **已记录(2026-10-07)**:qwen-code `464f486e20198f7f39623f3e95f51ab5d4f98e40`(2026-10-07,`@qwen-code/qwen-code 0.25.0`);kimi-code `21406fb4c805cc8c715e6d1f16ad3fb5f25f4fe3`(2026-09-30,`@moonshot-ai/kimi-code@2.1.1-13-g21406fb4c`)。**本文全部行号绑这两个提交**;checkout 一变即失效 |

## U4 · 与项目已有原则的关系(最要紧的未决项)

- 项目原则(`related_files/TIMING-REVIEW(1).md`):**所有触发变量都是 harness-authoritative;没有 embedding、没有 agent 自评、没有 LLM judge**。
- 现在拿到了两个真实 harness 上的**实例化样本**:qwen 在**两处**违反(AUTO 权限分类器、Goal verifier 都是 LLM judge,且开 side-query),kimi 在触发路径上守住但把完成判据降级为未求值的文本。
- **未决**:这两个样本对那条原则是
  (a) **支持**(qwen 的违反点恰好落在被判为风险的位置);
  (b) **反驳**(kimi 守住了触发路径,却退化成"有判据而不判");
  (c) **第三态** —— 两者都缺"判据可执行性"这一维,应作为新的一维登记(而非当作原则的反例)。
- 我的读法(可反驳):(c) 更可能。kimi 的样本说明"harness-authoritative"还不足够 —— 判据不仅要**在 harness 里**、不外包给 LLM,还必须有**可执行性**(被判据判、而不是被模型读)。若采纳,这一维该进的就是 `Taste ⇄ SOP ⇄ IaC` 的中间那层(SOP→IaC 的升格路径),而不是新开一条线。

