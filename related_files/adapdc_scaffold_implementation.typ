// Source deliverable. PDF is optional and is not an execution dependency.
#set document(title: "AdaPDC 可执行实验脚手架工程实施规格")
#set page(paper: "a4", margin: 22mm, numbering: "1")
#set text(font: ("Noto Serif CJK SC", "Libertinus Serif"), size: 10pt, lang: "zh")
#set par(justify: true, leading: 0.7em)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show table: block.with(breakable: false)
#set table(inset: 5pt, stroke: 0.35pt + luma(70%))
#show raw.where(block: true): set text(size: 8pt)
#align(center)[#text(size: 18pt, weight: "bold")[AdaPDC 可执行实验脚手架]\ #text(size: 14pt)[工程实施规格与最小验证实例]]

*交付性质*　本文件为可交给本地 agent 实施的规格、接口骨架和验收方案，不是已运行的软件包。自定义 CLI、DSL 和数据库接口均在本文规定实现责任；不得因代码片段出现就认定功能已实现。首轮采用 Temporal＋PostgreSQL＋TS＋Python，无真实数据、无 emsx 迁移、无科学创新结论要求。Typst 源文件是正式交付，PDF 可选。

*完成定义*　一条命令提交一个声明式合成实验，得到可手算的结果；增加分支不改 Workflow、数据库 schema 或 Python 入口；能解释执行依赖、局部重算、独立重跑、故障恢复和历史版本。数值运行成功不等于科学命题获支持。

= 已确定决策与非目标

#table(columns: (1fr, 2.5fr),
 [层], [首轮决定],
 [声明与语义], [TS 函数构图，生成纯 JSON IR；端口、连接、分组、变体均显式表示],
 [执行], [一个版本化 executePlanV1 Workflow；一组 Activity；本地单 Worker 进程，图节点先串行执行],
 [数值], [Python 标准库实现示例；构建不可变 wheel，经锁定环境执行；不依赖 catalog],
 [元数据], [独立 PostgreSQL catalog 数据库；TS 服务封装事务、登记与查询],
 [文件], [本地内容寻址存储 CAS＋执行工作目录；大对象不进 Workflow History],
 [理论], [带稳定标签的 Typst；卡片通过内容摘要引用；不要求数值执行前编译],
 [依赖], [pnpm 管 TS，uv 管 Python；选择兼容版本后锁定，后续安装不自动更新],
)

不自建 scheduler，不叠加 Nextflow／Dagster，不迁入旧代码，不建立类继承型 Experiment，不开发任意图重写或自动证明。Nx 若已存在可包装命令；空仓库首轮不因本计划新增第二套任务调度。Temporal 管控制流恢复，catalog 管研究记录，CAS 管产物内容；三个系统的事实归属不得混淆。

本计划把先前“后端后置”的建议更新为“Temporal＋PostgreSQL 直接承载示例，但功能范围保持最小”。不能同时保留相反的现行决策。架构报告标为历史讨论，新增 ADR 指向本规格。

= 最小实例：三个分支、八个节点

定义 $n=4$，生成 $x=(0,1,2,3)$；偏移轴 $b in {0,1,2}$：
$ y_i^(b)=x_i+b, quad s_b=frac(1,n) sum_(i=0)^(n-1)(y_i^(b)-x_i)^2=b^2. $ <eq-demo>
预期评分依次为 0、1、4。生成一次，三个 shift 节点，三个 score 节点，一个 aggregate，共八个数值节点。无随机种子，因为示例完全确定；不要为形式完整引入伪随机因素。

#table(columns: (1fr, 1.4fr, 1.4fr),
 [生成元], [输入／参数], [输出],
 [sequence], [n：整数，1–100], [series/v1：非空有限数数组],
 [shift], [series/v1；bias：有限数], [series/v1，同长度],
 [score], [candidate、reference：series/v1，同长度], [score/v1：非负有限 MSE],
 [aggregate], [按分支坐标绑定的 score 列表], [report/v1：有序分支评分表],
)

评分模块不调用 shift 的内部计算，自己从两个数组求差。评分检查与 Python 实现分离：集成测试在 TS 端以 $b^2$ 验证结果，不能只让模块自称正确。示例能验收基础设施，不证明未来 BESS 研究或随机计算的可靠性。

第三分支从 bias=2 改为 3，预期变成 0、1、9。允许复用 sequence、前两组 shift／score 共五个节点，重新计算第三组两个节点及 aggregate 共三个。此精确计数仅针对参数变更、相同构建与复用开启的情形。

= 物理布局与逻辑身份

下列目录仅划分维护职责，不表达实验之间的科学关系。卡片可移动，索引通过扫描注册 ID；同 ID 同版本出现不同内容必须报冲突。

```text
apps/cli/                 命令入口与命令返回 schema
apps/worker/              Temporal Worker、Workflow、Activities
packages/contracts/      Zod schemas、错误码、协议版本
packages/graph/          DSL、展开、图校验、计划编译
packages/artifacts/      CAS、快照、完成清单
packages/catalog/        PostgreSQL 事务与查询
python/demo_ops/          纯数值函数、文件任务入口、pyproject
cards/demo.ts             实验声明
notes/demo.typ            理论与 eq-demo 标签
infra/                    Compose、角色初始化、基础设施锁
migrations/               应用数据库迁移
scripts/                  doctor、bootstrap、demo、故障测试
fixtures/                 哈希测试向量、错误图、预期结果
```

运行目录、CAS、凭据和数据库卷不作为普通源码入 Git。源码、迁移、理论、协议、依赖锁及验收定义入 Git。可移植结果包通过命令显式导出；历史图和运行关系存于 catalog 并可备份，不要求人维护文件夹层级。

= 类型、声明与 IR 的精确定义

== 可序列化基础类型

```ts
type Json = null | boolean | number | string |
  Json[] | { [key: string]: Json };
type Digest = `sha256:${string}`;
type Ref = { digest: Digest; schema: string };
type Binding =
  | { kind: 'artifact'; ref: Ref }
  | { kind: 'port'; node: string; port: string };
interface NodeSpec {
  id: string;
  op: string;
  implementation: Ref;
  params: Record<string, Json>;
  inputs: Record<string, Binding | Binding[]>;
}
interface ExperimentIR {
  schema: 'adapdc.ir/v1';
  nodes: NodeSpec[];
  groups: { id: string; kind: 'sweep';
    axes: Record<string, Json[]>;
    members: { node: string; coordinate: Record<string, Json> }[];
  }[];
  exports: Record<string, Binding>;
}
```

Digest 的 TS 模板不是运行时验证：schema 要求 sha256 加 64 位小写十六进制。所有外来 JSON 再用运行时 schema 校验，拒绝额外字段、重复 node id、重复端口绑定、缺少必需输入。数组端口保留顺序，不能作为集合任意排序。

生成元签名另存为版本化记录：输入／输出 schema、语义角色、可见性、参数 schema、确定性与缓存策略。示例只有 agent-visible 数组；反向测试额外构造 evaluator-only 类型验证拒绝连接。运行 schema 校验不能证明模块语义正确，也不是文件权限隔离。

== 首张卡片（待实现 DSL）

```ts
const x = use('sequence@1', { params: { n: 4 } });
const ys = sweep('shift@1', {
  inputs: { data: x.out('data') },
  axes: { bias: [0, 1, 2] },
});
const scores = map(ys, y => use('score@1', {
  inputs: { candidate: y.out('data'), reference: x.out('data') },
}));
export default experiment({
  id: 'demo-offset',
  theory: 'theory-demo@1',
  graph: collect(scores),
});
```

DSL 返回节点／端口句柄，不返回数值结果。map 回调在构图时执行并完全展开；函数闭包不进入 IR。sweep 保留高层 axes 和 members，不只保存展开节点。节点 ID 由稳定逻辑路径和坐标产生，不能用全局数组下标导致新增分支重命名所有旧节点。collect 按明确坐标顺序建立一个 aggregate 节点并暴露其 report。

卡片中的 `@1` 仅为编辑用别名，编译时解析到具体签名和实现摘要。执行计划绝不追随别名。TS 卡片只在受信任代码范围运行；禁止隐藏的网络、时钟、随机输入是作者契约，首轮用代码审查与确定性编译测试约束，不声称 TS 是沙箱。

== 编译步骤与输出

1. 发现卡片、理论与生成元，注册逻辑 ID，冲突即失败。
2. 构图并展开有限 sweep，首轮上限 100 个节点。
3. 校验连线、参数、schema 兼容、可见性、孤立依赖与环。
4. 解析实现包、运行环境与既有输入，冻结为内容引用。
5. 按稳定 tie-break 生成拓扑序；保留完整输入边及 sweep 成员。
6. 生成 IR digest、Plan digest、研究快照 digest，写 CAS 并输出引用。

Plan 增加 interpreterVersion、runtimeRef、拓扑序及输出绑定；不包含 executionId、时间戳或本机绝对路径。研究快照额外引用理论、比较协议和父变体关系。未来节点输出尚无哈希，Plan 冻结的是生产者端口绑定；运行时再记录解析后的产物摘要。

= 规范编码、执行键与版本

规范 JSON 使用 RFC 8785 JCS 后取 SHA-256；用通过官方测试向量的库，不手写排序器。输入仅允许 I-JSON 兼容数据，拒绝 NaN、Infinity、undefined、BigInt 和不成对代理字符；超出安全整数范围的整数使用带类型 schema 的十进制字符串。RFC 不执行 Unicode 规范化，勿自行加入隐式规范化。#footnote[#link("https://www.rfc-editor.org/rfc/rfc8785.html")[RFC 8785：JSON Canonicalization Scheme。]]

摘要输入带域标记，例如：
```json
{"domain":"adapdc.plan/v1","value":{"schema":"adapdc.plan/v1"}}
```

上例只说明封装格式，不是完整 Plan。执行键由 op、实现摘要、运行环境摘要、参数、按端口有序的实际输入摘要、输出契约与执行策略组成，不包含 experimentId、nodeId、attemptId 或展示名称。否则跨变体无法复用相同计算。

复用仅对声明 deterministic-cacheable 且完成清单有效的节点启用。独立重跑跳过跨执行缓存；同一逻辑节点因 Activity 重试恢复自己的已完成输出仍允许。非确定性计算首轮不支持跨执行缓存。共享 wheel 的代码变更可能使多个生成元同时失效，这是保守且正确的版本边界；不能为追求局部重算漏锁共享代码。

规格身份、Temporal Workflow ID 和产物摘要分别维护。每次用户提交先生成 executionId，Workflow ID 为 `adapdc/<executionId>`；CLI 同一提交重试复用该 ID，用户要求独立重跑则新建。Temporal Run ID 单独记录。节点逻辑身份为 `(executionId,nodeId)`；Activity 的多次尝试不算独立科研重复。

= PostgreSQL：首轮数据库与登记语义

Temporal persistence 与 visibility 使用其官方 schema；应用 catalog 使用独立数据库、凭据和迁移。不得查询 Temporal 内部表来替代公开 API。为简化故障测试，首轮可用两个 PostgreSQL 容器：Temporal 存储与 catalog 分开，停止 catalog 不应同时停止 Temporal。

以下是应用表的最小迁移骨架；SQL 迁移是结构唯一来源，若保留 Drizzle，其映射不得另行自动修改结构。

```sql
CREATE TABLE specs (
  digest text PRIMARY KEY,
  kind text NOT NULL,
  document jsonb NOT NULL,
  CHECK (digest ~ '^sha256:[0-9a-f]{64}$')
);
CREATE TABLE executions (
  id uuid PRIMARY KEY,
  plan_digest text NOT NULL REFERENCES specs(digest),
  snapshot_digest text NOT NULL REFERENCES specs(digest),
  workflow_id text UNIQUE NOT NULL
);
CREATE TABLE artifacts (
  digest text PRIMARY KEY,
  byte_size bigint NOT NULL CHECK (byte_size >= 0)
);
CREATE TABLE node_results (
  execution_id uuid NOT NULL REFERENCES executions(id),
  node_id text NOT NULL,
  execution_key text NOT NULL,
  manifest_digest text NOT NULL REFERENCES artifacts(digest),
  origin text NOT NULL CHECK (origin IN ('computed','reused')),
  PRIMARY KEY (execution_id,node_id)
);
CREATE TABLE result_ports (
  execution_id uuid NOT NULL,
  node_id text NOT NULL,
  port text NOT NULL,
  artifact_digest text NOT NULL REFERENCES artifacts(digest),
  schema_ref text NOT NULL,
  PRIMARY KEY (execution_id,node_id,port),
  FOREIGN KEY (execution_id,node_id)
    REFERENCES node_results(execution_id,node_id)
);
CREATE TABLE execution_events (
  execution_id uuid NOT NULL REFERENCES executions(id),
  event_key text NOT NULL,
  payload jsonb NOT NULL,
  PRIMARY KEY (execution_id,event_key)
);
```

实现还需 migration 002：input_bindings（实际消费引用）、artifact_locations（digest 与 location 多对多）、cache_entries（executionKey 指向一个已验证 node_result）、assessments（命题／规则／证据引用）、spec_relations（派生或挑战）。每种表给 FK、唯一键及相应服务校验；不将所有关系塞成无法约束的任意 JSON。

JSONB 用于保存完整冻结文档；哈希计算使用 CAS 中的规范原始字节，不使用 PostgreSQL 重新输出的 JSON 文本。数据库约束保证结构完整性，不负责证明公式或校验磁盘内容。#footnote[#link("https://www.postgresql.org/docs/current/ddl-constraints.html")[PostgreSQL：Constraints。]]

同键同内容返回已有；同键异内容报冲突。不能直接 `ON CONFLICT DO NOTHING` 后忽略内容差异：事务内读回已有记录并比较摘要，不同则抛错。一次 node_result 及其端口／实际输入边原子登记。并发 cache key 冲突可选已有有效结果，但各 execution 的真实产物关系仍须保留。

首次登记若 execution 尚未入库，由提交清单补建规格和 execution，再登记 node；manifest 必须携带这些引用。数据库离线时，文件完成清单可恢复这条关联，不能只剩一个无从解释的 run id。

= CAS 与 Python：真实计算及发布

CAS 路径为 `objects/sha256/<前两位>/<剩余摘要>`；文件只读发布，位置不进入身份。写入临时文件、校验摘要、原子发布；完成清单最后提交。目标 digest 已存在则验证内容，不覆盖。目录可写者仍能破坏文件，因此每次消费检查摘要；将损坏报告为错误而非静默重算覆盖。

示例 Python 数值内核可直接按下列实现；入口负责 schema、文件和错误码，不在内核访问数据库。

```python
def sequence(n):
    return list(range(n))

def shift(data, bias):
    return [v + bias for v in data]

def score(candidate, reference):
    if not reference or len(candidate) != len(reference):
        raise ValueError("shape mismatch")
    return sum((a-b)**2 for a,b in zip(candidate, reference)) / len(reference)
```

入口为 `python -m demo_ops.task --request request.json --output result.json`。request 固定 schema、op、params、输入文件路径及摘要；result 固定输出端口、相对文件名和 schema。stdout/stderr 仅日志，不作为成功数据协议。Python 拒绝非有限数值，输出文件路径必须局限工作目录；TS 侧再次校验并计算摘要，不能信任 Python 自报摘要。

Python 包使用 uv build 构建 wheel；发布命令复制至 CAS 并登记包摘要。安装到按 runtime digest 命名的不可变环境，使用确切 wheel，不使用 editable install。锁定 Python 版本和依赖；首轮仅标准库，降低发布难度。缺失旧 wheel／环境时明确失败，不能用新版本替代。

工作目录按 execution、node、attempt 分离。数值子进程无 catalog 凭据；通过 spawn 的参数数组调用，禁用 shell 插值。首轮只绑定声明输入并校验路径，不宣称 OS 级访问隔离。正式隐藏信息实验之前另加隔离验收，不能将示例验收直接解释为“无泄漏已证明”。

= Temporal Workflow 与 Activity 实施契约

官方要求 Workflow replay 确定性，外部读写放 Activity；Activity 重试要求外部效果幂等。这里使用正式 SDK 的基本模式，但辅助函数需本地实现。#footnote[#link("https://docs.temporal.io/workflow-definition")[Temporal Workflow Definition。] #link("https://docs.temporal.io/activity-definition")[Activity Definition。]]

```ts
// workflows.ts: no fs, pg, child_process, or CAS imports
import { proxyActivities } from '@temporalio/workflow';
import type { Activities } from './activities';
const act = proxyActivities<Activities>({
  startToCloseTimeout: '2 minutes',
  retry: { maximumAttempts: 3 },
});
export async function executePlanV1(req: Submission) {
  const plan = await act.loadPlan(req.planRef);
  const results: Record<string, NodeResult> = {};
  for (const node of plan.nodes) {
    const inputs = resolveBindings(node.inputs, results);
    results[node.id] = await act.executeNode({
      executionId: req.executionId,
      node, inputs, reuse: req.reuse,
    });
  }
  return await act.commitExecution({ req, results });
}
```

Submission 含 executionId、planRef、snapshotRef 和 reuse 策略；不将执行 ID 写入 Plan。plan.nodes 已按确定拓扑排序，resolveBindings 为纯函数。首轮限制节点数和返回引用大小，单节点只是小 JSON 引用；日志和数组不进入 History。

`executeNode` 的职责顺序：

1. 检查该 execution/node 是否有可靠完成清单；有则校验并直接返回，用于 Activity 重试。
2. 开启复用时查 executionKey；命中有效产物则写本次 reuse 清单，保留来源 execution/node。
3. 否则执行 Python，校验输出，将产物及 node 完成清单可靠提交。
4. 尝试登记；catalog 不可用时返回 computed/pending-registration，不把成功计算改为失败。
5. `commitExecution` 提交整个 execution 完成清单，尝试登记，返回注册状态。

必须区分可重试的网络／临时故障与不可重试的输入损坏、schema 错误、业务断言失败。超时、心跳、取消及 Python 进程清理在单独 runtime helper 中实现。演示默认任务极短；故障测试可在外层插入等待，不修改数值算法。进程中断后未可靠提交的计算允许重做，不声称 exactly-once computation。

首轮“一台主机、一个 Worker，节点串行”是支持范围，但重试仍可能与旧子进程重叠。对 `(executionId,nodeId)` 使用本地 OS 互斥锁或等价的进程级锁，锁由执行 Activity 持有并在退出时释放；子进程随父任务取消终止，各 attempt 独立临时目录。可靠完成清单采用不覆盖提交：并发不同结果必须报冲突。多主机执行需要分布式 fencing，属于后续范围。

默认 Workflow Completed 只表示执行流程结束，catalog 可仍待补登记。`status` 命令联合输出 executionStatus 与 registrationStatus，不能用一个绿色 completed 掩盖缺失元数据。Temporal 服务、文件、catalog 无全局事务；manifest 是事后恢复依据。

= 基础设施启动与版本锁

首轮采用官方 samples-server 的 PostgreSQL Compose 方案，不使用已归档的 temporalio/docker-compose。官方指出 Compose 用于开发／测试，不视作生产部署保证。#footnote[#link("https://github.com/temporalio/samples-server/tree/main/compose")[Temporal samples-server/compose。] #link("https://github.com/temporalio/docker-compose")[旧仓库归档说明。]]

以下是现有工具命令，用于首次取样和检查，不应成为每次启动时拉取 main 的脚本：

```bash
git clone https://github.com/temporalio/samples-server.git /tmp/adapdc-temporal-upstream
git -C /tmp/adapdc-temporal-upstream rev-parse HEAD
docker compose -f /tmp/adapdc-temporal-upstream/compose/docker-compose-postgres.yml config
```

P0 将所选提交的必要 Compose、脚本及许可证复制至 infra/vendor，并记录提交 SHA。阅读其环境配置，把 server、UI、PostgreSQL 镜像锁定为验证过的 tag＋digest；记录 Node、pnpm、Python、uv、Temporal SDK 精确版本及锁文件。本文不虚构一组已测试的版本号；该锁文件与实际 smoke 结果是 P0 必交产物。

应用 overlay 增加 catalog-postgres、持久卷与只绑定 localhost 的管理端口。Temporal server 使用独立 PostgreSQL，应用 credentials 不连接其内部库。catalog schema 由独立 migrator 创建，运行服务不持 DDL 权限。默认开发凭据不得入版本库，bootstrap 生成本地配置；测试环境使用独立 Compose project 与存储根。

首轮不要求 TLS、集群、生产权限隔离；明确仅用于可信单机开发。启动后健康检查包括 PostgreSQL SQL 查询、Temporal namespace 存在与 Worker poll 成功，不仅检查容器 running。停止默认保留卷，禁止 bootstrap 或 stop 自动执行 `down -v`。

= 自定义命令：必须实现的用户入口

下面所有 `pnpm ...` 名称是脚手架交付契约，当前不宣称已有实现。根 package.json 必须逐项提供 scripts；CLI 返回结构化 JSON，错误退出非零。使用固定的 `.adapdc/demo-submission.json` 保存首次提交请求以便重试，路径仅为默认位置。

```bash
pnpm install --frozen-lockfile
pnpm infra:up
pnpm db:migrate
pnpm doctor
pnpm demo:publish
pnpm demo:compile
pnpm worker
```

另一个终端：
```bash
pnpm demo:run
pnpm demo:status
pnpm demo:verify
pnpm demo:variant
pnpm demo:run:variant
pnpm demo:verify:variant
pnpm demo:rerun
pnpm catalog:reconcile
pnpm infra:stop
```

#table(columns: (1.15fr, 2.3fr),
 [命令], [行为与退出条件],
 [infra:up / stop], [使用锁定 Compose；等待健康／保留持久卷],
 [db:migrate], [只迁移应用 catalog；重复运行不改状态，失败不继续启动],
 [doctor], [验证版本、namespace、DB schema、CAS 可写与角色权限],
 [demo:publish], [构建并发布 Python wheel、签名、理论、runtime manifest],
 [demo:compile], [生成八节点 IR／Plan／快照，返回 digest 和拓扑概要],
 [worker], [启动 executePlanV1 的 TS Worker，连接固定 namespace/task queue],
 [demo:run], [创建或复用本地 submission；启动或连接同 workflowId，等待完成],
 [demo:status], [返回 executionId、Temporal 状态、登记状态、节点计数和产物],
 [demo:verify], [要求评分 0/1/4、八个 node_result、理论与组关系可查],
 [demo:variant], [将第三分支 bias 改为 3，生成新规格及 derived-from 关系],
 [demo:verify:variant], [要求 0/1/9；在完整缓存下 computed=3、reused=5],
 [demo:rerun], [原规格新 executionId；reuse=false；实际执行八节点],
 [catalog:reconcile], [扫描可靠完成清单，幂等补登记并报告冲突／缺失],
)

补充必须提供 `plan:diff`、`catalog:query --topic demo-offset`、`test:unit`、`test:integration`、`test:replay`、`test:acceptance`。查询不靠目录名；按实验 ID 找规格、运行、sweep 坐标、产物和 theory ref。demo 命令是薄参数包装，不可包含另一份隐藏图定义。

= 可观测性与证据归属

所有日志带 executionId、nodeId、attempt、op、implementationDigest、executionKey；不记录凭据。完成清单列出实际输入绑定、输出 schema／摘要、runtime、退出状态和 computed／reused 来源。

运行时事件记录 operational 状态；assessment 单独记录评估规则、引用证据、范围与评估者。示例 assessment 为“固定输入下示例断言通过”，绝不自动写 H_S／H_A supported。一条规则的修改生成新 assessment 版本，不覆盖过去解释。

理论正文只维护公式与解释，结构化协议维护机器需要读取的参数／断言。示例中的 $b^2$ 在 TS 验收端独立实现，并引用 eq-demo；这是有意的独立核对，不通过从生产评分代码导入同一函数来伪造验收。

= 故障注入与验收矩阵

所有故障由测试环境控制，在专用 CAS／DB 内执行。注入器使用实际执行节点的生命周期钩子，不改变 IR 的数学语义；每次注入最多触发一次，避免重试永远停在同一故障。测试 hook 不进入正常发布 runtime。

#table(columns: (0.55fr, 1.9fr, 1.9fr),
 [编号], [操作], [预期／证据],
 [T01], [同卡片编译两次], [Plan 摘要相同；timestamp 与 executionId 不在哈希中],
 [T02], [调整 JSON 键顺序、加入非法 NaN], [前者摘要相同，后者解析失败；JCS 向量通过],
 [T03], [错误 schema、隐藏端口、依赖环], [编译拒绝并定位节点端口；不提交 Workflow],
 [T04], [移动卡片／理论文件并重新索引], [相同内容与 ID 得到同规格；路径不改身份],
 [T05], [正常执行原示例], [八个节点，评分 0/1/4；报告坐标顺序正确],
 [T06], [提交参数变体], [评分 0/1/9；执行 3 个、复用 5 个；原记录保留],
 [T07], [原规格独立重跑], [新 executionId，执行 8 个；产物可内容去重],
 [T08], [完成节点清单后、返回前杀 Worker], [重启返回已完成结果，不再次执行该节点数值体],
 [T09], [Python 执行中杀 Worker], [临时结果不被消费；恢复后允许重算；锁及子进程清理],
 [T10], [只停止 catalog PostgreSQL], [计算完成、登记 pending；DB 恢复 reconcile 后完整],
 [T11], [重复 reconcile，再提交同键异内容], [前者零新增，后者明确冲突；不覆盖],
 [T12], [损坏一个 CAS 文件], [读取失败并报告摘要不匹配；不静默接受缓存],
 [T13], [重启 Temporal 与 PostgreSQL 服务], [持久卷保留，执行历史与 catalog 记录仍可查],
 [T14], [同一个 submission 重试启动], [一个逻辑执行，不新增独立实验],
 [T15], [修改开发区 Python，不发布新包], [冻结计划仍使用旧 wheel，结果不漂移],
 [T16], [第三分支新增 bias=3], [十节点新图；执行器、schema、Python 入口不变],
 [T17], [导出 History 后 replay 测试], [同解释器通过；不把 Python 数值重算当 replay],
 [T18], [删除 DB 后在独立测试库恢复], [备份恢复或清单重建路径按声明通过；原库不动],
)

T16 是在原 0/1/2 基础上新增第四分支，节点数为 1＋4＋4＋1=10；T06 是替换原第三分支，两者不可混淆。T08 用数值体计数日志核对，而非只看结果相同。catalog 停机使缓存不可查时可以重新计算，但必须记录 cache-unavailable；不要把额外计算称作缓存命中。

单位测试覆盖哈希、图校验、纯计算和输入绑定；集成测试必须启动真实 Temporal 与 PostgreSQL，不能用 mocks 声称恢复成立。CI 至少分 pure tests 与 services tests 两个 job。验收结果输出 machine-readable JSON，包含 test ID、状态、软件锁摘要与证据位置。

= 实施提交顺序

#table(columns: (0.5fr, 1.8fr, 1.9fr),
 [提交], [实现边界], [必须过的关口],
 [C0], [空仓库 scaffold、ADR、依赖锁、Compose 来源锁], [infra:up、doctor，明确无旧资产依赖],
 [C1], [Python 示例、wheel 发布与文件入口], [数值单测、入口错误测试、发布后不读开发源],
 [C2], [contracts＋DSL＋IR＋compiler], [T01–T04，产物为冻结计划，尚不启动计算],
 [C3], [CAS、应用迁移、catalog 事务], [重复／冲突登记、完成清单恢复单测],
 [C4], [Temporal Workflow、Activities、本地进程 helper], [T05、T07、T14；真实服务贯通],
 [C5], [变体、缓存、实际输入 provenance], [T06、T15、T16，diff 能解释重算原因],
 [C6], [故障注入、重放、备份恢复], [T08–T13、T17–T18，不将已定义标为已验收],
 [C7], [查询、理论绑定、示例文档与全套脚本], [新用户照命令完成示例；报告支持范围],
)

每个提交说明新增文件、导出接口、错误码、验收命令、通过证据及未实现范围。agent 不得在 C2 因方便修改已发布算法，也不得在 C4 绕过 IR 在 Workflow 中写死示例偏移数组。若已有仓库状态不同，先对齐 C0 清单，不自动覆盖。

= 项目级退出条件与下一阶段

首轮完成需满足：空环境可重建；同一声明稳定编译；八节点示例得到预期值；替换和新增分支不改执行框架；冻结代码有效；重试、故障、登记和缓存语义有实际证据；Typst 定义与产物可追溯。尚未达到强隔离、多机运行、真实数据处理、科学结论验证和生产运维，不以通过示例推断这些能力。

下阶段把 BESS 任务生成为新的生成元组合；先保持现有执行协议、数据库基础结构和 Workflow。若一加入 BESS 就需要重写基础设施，应先分析缺失的是类型表达、输入协议还是执行机制。只有有具体阻碍时扩展 IR；不提前建设所有未来功能。

= 来源与执行声明

规范来源为正文链接的 Temporal 官方文档、samples-server 官方示例、RFC 8785 和 PostgreSQL 文档；核查日期 2026-09-09。SDK 具体版本、镜像 digest 和部署配置由 C0 的兼容性验证冻结，本文件不提供未经运行验证的版本组合。

本次交付是实施规划源文件；未在此环境启动 Temporal／PostgreSQL，也未宣称 T01–T18 已通过。自定义命令须由上述提交实现后才可执行。既有理论和 catalog 契约继续作为来源；出现规范冲突时通过 ADR 明确取代条款，不能让两份“现行真相”并存。
