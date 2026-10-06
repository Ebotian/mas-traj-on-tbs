# AdaPDC 当前状态（供审查）

> **快照锚点：代码锚点 `6db0d78`**（2026-09-10；其后为文档提交，不改变任何代码）。
> 文件与文档计数按**本文件所在提交**统计（含本文件本身）。
> 本文件是**快照**：实现事实以该代码提交与运行证据为准；**效力冲突以明确的取代关系和 ADR 为准，
> 不以时间新旧裁定**。相关文件见文末 §11。
>
> **目的**：在一份文件里看清「项目当前处于什么状态、凭什么这么说、还差什么、该怎么自己复核」。
> 凡属判断的地方都标出「这是判断」；凡未验证的地方都写「未验证」。

---

## 0. 一页速览

| 层                              | 状态                         | 证据入口                                                                |
| ------------------------------ | -------------------------- | ------------------------------------------------------------------- |
| 研究层（问题与命题）                     | **已定义，未检验**                | `docs/research-foundations.md`、`docs/adapdc_theory_review.typ`      |
| 文档效力与记账口径                      | **已裁决**（ADR-001 + 逐条差异表）   | `docs/adr/001-scaffold-baseline.md`、`docs/catalog-contract-diff.md` |
| 工程底座（基础设施）                     | **C0 关口已过**，逐服务判据为真        | `pnpm infra:up`、`pnpm run doctor`                                   |
| 数值内核与文件协议                      | **C1 已实现**，可在隔离环境脱离源码运行    | `pnpm python:test`、`pnpm python:wheel`                              |
| 执行框架（IR/DSL/compiler/Workflow） | **未实现**（C2–C4）             | —                                                                   |
| 登记与恢复（CAS/catalog/迁移）          | **未实现**（C3）；缺口的处置设计**未提交** | —                                                                   |
| 领域合成闭环 / 真实数据                  | **未开始**（R1 / R2）           | —                                                                   |

**现在真能做的事**（仓库根，逐条实测过）：

```bash
pnpm install --frozen-lockfile          # 依赖可复现；锁文件通过供应链策略校验
pnpm bootstrap                          # 生成本地凭据（幂等，不覆盖）
pnpm infra:up                           # 起 6 个服务，按逐服务判据确认就绪
node apps/cli/src/index.ts doctor --scope=c0   # 自检，stdout 为纯 JSON
pnpm infra:stop                         # 停止，保留持久卷
pnpm test:unit && pnpm python:test && pnpm test:infra && pnpm -r typecheck
pnpm python:wheel                       # 建 wheel → 隔离环境安装 → 脱离源码运行
```

**现在不能做的事**：跑任何实验、提交实验规格、得到闭环成本、登记任何产物。
`db:migrate`、`demo:*`、`worker` **尚未在 `package.json` 声明**（未实现前不留空壳）；
`experiments/` 为空。**T01–T20 一个都没跑过，本文不声称任何一项通过。**

---

## 1. 研究层状态

### 1.1 问题与命题（已定义，未检验）

* **主问题**：为了做出低成本调度，系统究竟需要从少量历史中**辨别哪些机制差异**？
* **两个可证伪主命题**：**H_S**（结构：存在较紧凑的 $b$ 使 $\Delta_m$ 小）、**H_A**（适应：$b$ 能利用
  部署时少量观测更新、改善预算匹配基线的闭环成本）。细节与五个命题见 `adapdc_theory_review.typ`。
* **本阶段产出的科学结论：无。** 工程建设（C0/C1）不构成对 H_S/H_A 的任何支持或否定。
  `doctor` 的输出里也明写这一点（`scopeNote`）。

### 1.2 文档效力结构（已裁决）

| 关系   | 内容                                                                                                                   |
| ---- | -------------------------------------------------------------------------------------------------------------------- |
| 权威裁决 | `docs/adapdc_scaffold_implementation.typ` 中的 **ADR-001**（落库摘录见 `docs/adr/001-scaffold-baseline.md`，附来源提交与源文件 sha256） |
| 记账口径 | `docs/experiment-catalog-contract.md`（语义契约）+ `docs/catalog-contract-diff.md`（**逐条差异表**：一致 / 细化 / 取代 / 顺延）            |
| 效力规则 | 冲突以**明确的取代关系与 ADR** 为准；时间较新不构成取代理由（已写入 `AGENTS.md` 工作准则第 3 条）                                                        |
| 登记约定 | 未被 `docs/README.md` 登记的文件不构成「现行真相」                                                                                   |

### 1.3 仍未裁决的开放性（需人工决定，未自行推进）

| 项                             | 现状                                                   |
| ----------------------------- | ---------------------------------------------------- |
| **任务族 $\Pi_{\mathcal R}$ 成员** | 未定（候选：需量费 / 能量 / 力调）                                 |
| **信息契约落地形式**                  | 未定（已知规则 / 隐藏参数 / 外生过程 / 累积状态 四类需分开）                  |
| **TS 与 Python 的职责边界**         | 底座已定（ADR-001），但**具体任务上的切法**未定                        |
| **基线实现**                      | 未定（读已知参数 / 滚动重训 / 显式辨识 / 学习式适应器，及「知道真实机制但不知未来扰动」的参照） |

---

## 2. 工程层状态

### 2.1 已实现的端到端能力（实测）

| 能力        | 实测结果                                                                         |
| --------- | ---------------------------------------------------------------------------- |
| 基础设施起停    | `infra:up` exit 0；6 个服务，长期服务就绪判据为真、一次性服务退出码 0                                |
| 自检        | `doctor --scope=c0` exit 0、`ok=true`、`failed=[]`；五项 pass + `worker-poll` 不适用 |
| 幂等        | 连续 `infra:up` 后容器 ID **逐一不变**；`bootstrap` 二次运行不改 `.env`（比 sha256）            |
| 数据保留      | 改名前留标记 → `down`（不带 `-v`）→ `up` 后标记仍在；卷名未变                                    |
| 命名隔离      | 解析结果中**无 `container_name`**；网络/卷均以 project 前缀                                |
| 就绪判据正确性   | `test:infra` 5/5（含「有 healthcheck 却不健康**必须被拒**」）                              |
| 数值内核      | `python:test` 29/29，含文件协议跑完整条链得 **0 / 1 / 4**                                |
| Python 制品 | wheel 可在**独立 venv + 无索引 + 仓库外工作目录**下运行，且模块确实来自 venv                          |
| TS 单测     | `test:unit` 31/31（含 CLI 两种输出形状与 scope 判定）                                    |

### 2.2 组件清单（72 个受控文件，按目录）

**`apps/cli/`（9 个文件）** —— 命令入口

* `src/index.ts`：分发、`--scope`、退出码（0 成功 / 1 失败 / 2 用法错误）；**stdout 只输出 JSON**。
* `src/report.ts`：两种固定输出 schema（`adapdc.doctor-report/v1` / `adapdc.cli-error/v1`）+ `workerCheck(scope)`。
* `src/commands/doctor.ts`：五项检查（versions / temporal-namespace / catalog-db / catalog-roles / cas-writable）。
* `src/workspace.ts`：定位仓库根（`ADAPDC_ROOT` 为测试接缝）、读 `.env`；`src/exec.ts`：参数数组调用外部命令。
* `test/`：12 个测试（形状、scope、子进程用法错误、配置失败）。

**`packages/contracts/`（10 个文件）** —— **通用签名契约最小版**（不是完整 contracts，见 §3.2）

* `version.ts`（协议版本）、`errors.ts`（错误码 + 可重试分类）、`primitives.ts`（Digest/Ref，拒额外字段）、
  `generator-signature.ts`（签名记录：端口、参数、语义角色、可见性、确定性/缓存策略）。
* `test/`：19 个测试。

**`python/`（10 个文件）** —— C1 数值内核与文件入口

* `src/demo_ops/kernel.py`：`sequence` / `shift` / `score` / `aggregate`，**纯数值**（无 I/O、无路径、无数据库）。
* `src/demo_ops/protocol.py`：request/result 校验、错误码、摘要、路径约束（逃逸即拒）。
* `src/demo_ops/task.py`：`python -m demo_ops.task --request … --output …`；**日志走 stderr，stdout 空**。
* `tests/`：29 个测试（内核 + 端到端 + 失败路径）。`pyproject.toml` / `uv.lock` / `.python-version` 已入库。

**`infra/`（11 个文件）**

* `vendor/samples-server/`：上游 Compose 的**逐字副本** + `SOURCE.md`（提交 SHA `ca1106b6`、逐文件 sha256、未纳入项）。
* `compose/docker-compose.overlay.yml`：catalog-postgres、命名随 project、端口只绑 localhost、`!reset` 去固定名。
* `compose/initdb/00-catalog-roles.sh`：首次建两角色并划清 DDL 边界（**不建表**）。
* `lock/`：`images.env`（tag+索引摘要）、`toolchain.json`（doctor 比对源）、`versions.md`。

**`scripts/`（7 个文件）**：`lib.sh`（compose 调用与就绪判据）、`infra-up.sh`、`infra-stop.sh`、`bootstrap.sh`、
`python-test.sh`、`python-wheel.sh`、`tests/wait-health.test.sh`。

**`docs/`（17 个文件）**：研究文档、契约、ADR、差异表、审查材料（见 §11）。

### 2.3 基础设施（当前实际形态）

| 项               | 值                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------- |
| Compose project | `adapdc`（唯一来源 `scripts/lib.sh` 的 `ADAPDC_COMPOSE_PROJECT`）                                              |
| 容器              | `adapdc-postgresql-1`、`adapdc-catalog-postgres-1`、`adapdc-temporal-1`、`adapdc-temporal-ui-1`（+ 两个一次性服务） |
| 网络 / 卷          | `adapdc_temporal-network` / `adapdc_catalog-pg-data`、`adapdc_temporal-pg-data`                          |
| 端口              | **只绑 `127.0.0.1`**：catalog PG 5433、Temporal gRPC 7233、UI 8080；Temporal 自有 PG **不发布任何宿主端口**              |
| 凭据              | 由 `bootstrap` 生成到 `infra/.env`（权限 600，gitignore）；仓库内不存任何本项目凭据                                           |
| Temporal 存储     | 同一 PG 实例内的 `temporal` 与 `temporal_visibility` 两库（上游脚本行为）                                                |
| 应用 catalog      | **独立容器 + 独立库 + 独立角色**，与 Temporal 存储分开（「只停 catalog 不停 Temporal」可用于故障测试）                                  |

### 2.4 版本锁（摘要）

工具链：node 26.7.0 / pnpm 12.3.4 / python 3.14.6 / uv 0.12.3 / docker 29.7.2 / compose 5.5.1。
依赖（精确版本）：typescript 7.0.2、zod 4.5.4、vitest 5.0.0、@types/node 26.5.0、tsx 4.23.13、
@temporalio/client 1.23.0、pg 8.23.0。
镜像（tag + **索引摘要**）：`postgres:16`、`temporalio/server:1.31.0`、`admin-tools:1.31.0`、`ui:2.49.1`。
完整值与采集命令见 `infra/lock/versions.md`。

---

## 3. 在效的决定（决策台账）

### 3.1 ADR-001 基线（权威）

采用 TS＋Temporal＋PostgreSQL＋Python；不建 scheduler、不叠加 Nextflow/Dagster、不迁入旧代码、
不建类继承 Experiment；首轮用合成数据验证基础设施，不含真实数据、emsx 迁移与科学结论。
**出处**：`docs/adapdc_scaffold_implementation.typ` / `docs/adr/001-scaffold-baseline.md`。

### 3.2 阶段边界（**判断**，请审）

| 边界      | 内容                                                                                      | 依据                                                                        |
| ------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| C0 / C2 | C0 只做**通用签名契约最小版**（版本、错误码、Digest/Ref、签名记录）；**IR / DSL / compiler 属 C2**                 | 规格里 C2 = 「contracts＋DSL＋IR＋compiler」，G1 说明「C0 的通用签名只是最小可冻结版本」。**这条线是我划的** |
| C1 / C3 | C1 只做 wheel 构建、摘要清单、隔离安装、脱离源码运行；**正式 CAS 发布与 catalog 登记属 C3**                           | 上一轮审查的澄清；因此**未声明** `demo:publish`                                         |
| C0 / C4 | Worker 与 Workflow 属 C4；C0 的 `doctor` 对 Worker 标 `not_applicable`，`--scope=c4` 时**必须失败** | 审查意见 2                                                                    |
| 未实现不留空壳 | 未实现的命令不在 `package.json` 声明                                                              | 规格禁止「空壳运行冒充已实现」                                                           |

### 3.3 工程决定（本轮在效）

| #  | 决定                                                    | 理由 / 代价                                                         |
| -- | ----------------------------------------------------- | --------------------------------------------------------------- |
| D1 | vendor 逐字副本 + overlay 分离                              | 可核对来源；代价是 overlay 需处理合并语义                                       |
| D2 | 凭据由 bootstrap 生成、不入库                                  | 规格要求；上游硬编码的 `temporal` 仍在 vendor 副本中但被 overlay 覆盖               |
| D3 | catalog 独立容器/库/凭据 + 角色预划 DDL 边界                       | 规格要求；代价是多一个容器与端口                                                |
| D4 | 端口只绑 localhost；Temporal PG 完全不暴露                      | 规格 + 最小暴露面                                                      |
| D5 | 镜像 tag＋**索引摘要**（经 `RepoDigests`，本机无 buildx）           | 规格要求「验证过的 tag＋digest」                                           |
| D6 | overlay 不用相对路径（由 `lib.sh` 导出绝对路径）                     | 实测：compose 以**第一个 `-f` 文件**所在目录解析相对路径，会把 `./initdb` 指到 vendor 下 |
| D7 | 就绪判据**逐服务**，且对「有 healthcheck 却解析出 running」fail-closed | 审查意见 2；回归测试钉住                                                   |
| D8 | 命名一律随 Compose project 派生（`!reset` 去固定名）               | 审查意见 3；双实例可用 `ADAPDC_COMPOSE_PROJECT` + `ADAPDC_ENV_FILE`       |
| D9 | 供应链：`minimumReleaseAge` 不全局放宽，两处直接依赖降级 + 一处定点豁免       | 见 §3.4                                                          |

### 3.4 供应链豁免（**需你判断**）

`pnpm-workspace.yaml` 全文相关配置：`allowBuilds: {esbuild, protobufjs}`；
`minimumReleaseAgeExclude: ['@rolldown/binding-openharmony-arm64']`（**精确包名，无通配**）。
该包由 `vitest@5.0.0` 传递引入、平台为 openharmony-arm64（本机不执行其二进制）、无法选版。
为此把两个**直接**依赖改为满 24 小时的等价版本（zod 4.6.1→4.5.4、@types/node 26.5.1→26.5.0）。
**未验证**：该包内容本身（未审计二进制）；依据是「平台不匹配 + 非直接依赖 + 无法选版」，**不是**「已确认无害」。

---

## 4. 验证矩阵（判据强度）

延续「不把弱证据说成强证据」的做法：

| 结论                       | 判据                                                              | 强度                                 |
| ------------------------ | --------------------------------------------------------------- | ---------------------------------- |
| 容器就绪                     | 逐服务：PG 走真实 SQL、Temporal 走 namespace 查询、UI 走 HTTP 200、一次性服务核对退出码 | **强**                              |
| 「有 healthcheck 却未健康」不会放行 | 真实容器回归（`test:infra` 用例 1）+ 代码层 fail-closed                      | **强**                              |
| 重复启动不漂移                  | 容器 ID 逐一比对                                                      | **强**                              |
| 停止保留数据                   | 标记跨 `down`（不带 `-v`）→`up` 存活                                     | **强**                              |
| 命名无跨项目共享                 | 解析结果无 `container_name`、网络/卷带 project 前缀                         | **中**（双实例端到端**未做**）                |
| 镜像锁定                     | tag + 从 `RepoDigests` 取的索引摘要                                    | **中**（未验证镜像签名/来源证明）                |
| 运行角色「不持 DDL」             | 库级 `CREATE` 被拒（`permission denied for database adapdc_catalog`） | **中**：**仅库级**；对象所有权与角色继承**未验**（C3） |
| 数值内核正确                   | 29 个测试含 `s_b = b²` 判据与失败路径                                      | **强**（对已实现的操作）                     |
| 制品脱离源码运行                 | 仓库外 cwd、无 `PYTHONPATH`、断言 `demo_ops.__file__` 在 venv            | **强**                              |
| 隔离环境依赖来源                 | `--no-index` 安装 + 环境内仅 1 个发行版                                   | **中**（未审计该发行版内容）                   |
| CAS 可写                   | 目录写—读—删探针                                                       | **弱**：内容寻址语义属 C3                   |
| 无旧研究代码与数据的**执行依赖**       | 72 个受控文件全量检视，无 emsx 制品与引用                                       | **中**：证据是「仓库里没有」；会随代码增长需重新取证       |
| 复现性                      | `--frozen-lockfile` 通过 + 锁文件入库                                  | **中**：未在**空机器**上从零重建（**未做**）       |

---

## 5. 尚未实现（阶段对照）

| 阶段      | 内容                                                     | 状态              | 入口是否已声明                      |
| ------- | ------------------------------------------------------ | --------------- | ---------------------------- |
| C1      | Python 内核 / 文件协议 / wheel 与隔离运行                         | **已实现**（正式发布除外） | `python:test`、`python:wheel` |
| C2      | contracts 补全 + DSL + IR + compiler                     | 未开始             | 否                            |
| C3      | CAS、应用迁移（001/002）、catalog 事务、**G1 处置**                 | 未开始             | 否（`db:migrate` 未声明）          |
| C4      | Temporal Workflow / Activities / 进程 helper / Worker 检查 | 未开始             | 否                            |
| C5      | 变体、缓存、实际输入 provenance                                  | 未开始             | 否                            |
| C6      | 故障注入、重放、备份恢复（T08–T13、T17–T18）                          | 未开始             | 否                            |
| C7      | 新生成元扩展、查询、理论绑定（T19–T20）                                | 未开始             | 否                            |
| R1 / R2 | 领域合成闭环 / 真实数据与旧成果接入                                    | 未开始             | —                            |

**未声称**：T01–T20 任一通过；G1 已闭环；可可靠复现全部历史；任何科学结论。

---

## 6. 已知缺口与阻塞

| 编号     | 缺口                                                                                                                                                 | 何时必须解决                                                          |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **G1** | 契约要求 `computed ≠ registered` 的强制手段是「两个独立字段/时间戳」，但 migration 001 的 `executions` **没有登记状态列**；且数据库离线时**无法**靠库内 `registration_status=pending` 记录“登记失败” | **C3 开始前**须提交事实来源与恢复设计（完成清单 / 登记记录 / 状态查询三者分开），**不预先限定**为某组数据库列 |
| G2     | `resolveDatasetVersion`（→R2）与信息契约引用（→R1）在首轮无对等实体                                                                                                   | 接入时回填差异表                                                        |
| G3     | `findDependentRuns` 与「待复核」标记无实现                                                                                                                    | migration 002 之后                                                |
| G4     | 契约 §11 状态表承诺「DDL 落地时改为已强制清单」                                                                                                                       | C3 落地后回头改写                                                      |
| —      | Worker 存活检查未实现                                                                                                                                     | C4（现行 fail-closed）                                              |
| —      | DDL 深度检查：schema、对象所有权、角色继承                                                                                                                         | C3                                                              |
| —      | 双实例端到端验证                                                                                                                                           | **服务测试之前**（本轮只做命名解析检查）                                          |
| —      | 无 CI（规格要求 pure / services 两个 job）                                                                                                                  | 后续阶段                                                            |
| —      | 空机器从零重建未验证                                                                                                                                         | 未排期（建议纳入 C6）                                                    |

---

## 7. 风险与限制

1. **仅适用于可信单机开发**：无 TLS、无集群、无生产权限隔离；端口虽只绑 localhost，同机进程仍可访问。
2. **依赖版本很新**：TypeScript 7.0.2（Go 端口大版本）、Zod 4.5.4、Vitest 5.0.0、Node 26。本次实测可用，
   但生态兼容面未穷尽；升级须重走关口。
3. **供应链策略留有定点豁免**（§3.4）——安全护栏上的一个洞，理由明确、范围精确，但仍需你确认。
4. **`doctor` 的边界**：只证明「环境与凭据布局」，不证明数值计算、登记语义、幂等登记或任何科学结论
   （`scopeNote` 已写在输出里）。
5. **首次 `python:wheel` 需网络**（构建后端 hatchling）；首次 `infra:up` 需拉镜像（本次数分钟）。
6. **Temporal 存储与应用 catalog 的独立性**：两者分容器、分凭据、分库（设计目标：停 catalog 不影响 Temporal）。
   **本轮的验证边界要说清**：我做了「全栈 stop 后卷保留」的实证，但**没有**做「只停 catalog、
   同时确认 Temporal 仍可服务」的故障注入——那属 C6 的 T10。因此该独立性目前是**设计结论，不是实测结论**。
7. **`pnpm doctor` 会被 pnpm 12 内置命令接管**：本项目命令须写 `pnpm run doctor`
   （或直连 `node apps/cli/src/index.ts doctor --scope=c0`）。

---

## 8. 审查者最该质疑的点（更新版）

1. **C0/C2 与 C1/C3 的边界是我划的**（§3.2）。若你认为契约在 C0 就该完整、或 wheel 就应走正式 CAS，这两条要推翻。
2. **`infra:up` 的判据是否够强？** 尤其：UI 只查 HTTP 200、PostgreSQL 只查「表数 > 0」。
3. **`test:infra` 用的是本地 `postgres:16` 镜像造探针容器**，不是本项目栈本身——它验证的是等待函数，不是栈。
4. **供应链豁免**（§3.4）的依据是否可接受；以及我**未审计该包内容**这一点是否可容忍。
5. **「无旧研究代码与数据的执行依赖」的证据强度**（§4 末行）：目前是「仓库里没有」。
6. **数据保留的证明方式**：我用的是「标记 + 卷名不变」，不是「备份/恢复演练」——后者属 C6。

---

## 9. 复现与复核清单

```bash
# 0) 只读核对
git log --oneline | head -30          # 提交序列
git ls-files | wc -l                  # 72（含本文件）

# 1) 依赖与凭据
pnpm install --frozen-lockfile
pnpm bootstrap && pnpm bootstrap      # 第二次必须不改 infra/.env

# 2) 基础设施（首次需网络拉镜像）
pnpm infra:up                         # 逐服务判据；应 exit 0
node apps/cli/src/index.ts doctor --scope=c0    # ok=true
node apps/cli/src/index.ts doctor --scope=c4    # 应 exit 1（缺 Worker）

# 3) 测试
pnpm test:unit          # 31
pnpm python:test        # 29
pnpm test:infra         # 5（就绪判据回归，需 Docker）
pnpm -r typecheck

# 4) 制品与隔离运行
pnpm python:wheel

# 5) 证伪（务必先证明改动生效，否则会得到与「检查失效」无法区分的假通过）
#    改坏 CATALOG_APP_PASSWORD → doctor 应 exit 1 且 failed=["catalog-roles"]
#    移走 infra/.env          → doctor 应 exit 1 且输出 cli-error 形状

# 6) 收尾
pnpm infra:stop && docker volume ls   # 卷必须仍在
```

---

## 10. 下一步

1. **C2**（contracts 补全 + DSL + IR + compiler）——按 C0–C7 顺序。
2. **进入 C3 之前**，先提交「计算完成 / 登记完成 / 登记冲突」的**事实来源与恢复设计**
   （不预先限定为某组数据库列）——这是 G1 的处置，也是上一轮审查明确要求的关口。
3. 其余顺序项：双实例端到端验证（服务测试前）、DDL 深度检查（C3）、Worker 检查（C4）。

以上均须经你确认后再实施。

---

## 11. 与其他文档的关系

| 文件                                        | 关系                                                                                           |
| ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| `docs/c0-status-review.md`                | `67eead4` 时点的快照；其若干说法已被本轮取代（该文头部已列出取代清单）                                                     |
| `docs/review-packet.md`                   | 本轮（`6db0d78`）的**变更级**审查包，含**脱敏原始输出**：逐服务判据、doctor 两种形状、就绪判据回归、证伪测试、C1 制品、命名隔离、豁免配置。需要原始输出时看它 |
| `docs/README.md`                          | 文档索引与阅读顺序；未登记的文件不构成「现行真相」                                                                    |
| `docs/adapdc_scaffold_implementation.typ` | 实施基线（含 ADR-001、T01–T20、C0–C7），本文件不复写其规范内容                                                    |
