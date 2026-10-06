# 源码审查包（本轮）

> **代码锚点：`6db0d78`**（本轮 4 个提交全部落在此提交或之前；提交本文件只增加文档，不改变任何被审查的代码）。
> 本文是**快照**：效力冲突以明确的取代关系和 ADR 为准，**不以时间新旧裁定**；实现事实以该提交的代码与
> 这里的运行证据为准。
>
> **未包含**（按审查要求）：`infra/.env`、任何凭据、未脱敏的完整 Compose 渲染结果。
> Compose 部分只保留镜像引用 / 端口 / 挂载源 / 名称，**凭据字段一律未采集**。
>
> 定位：报告只列**本轮变更、验收证据、剩余阻塞**，不重复评价文档质量。

---

## 1. 本轮变更（4 个提交，对应你的 5 条意见）

| 提交        | 内容                                       | 对应意见                            |
| --------- | ---------------------------------------- | ------------------------------- |
| `ba28f22` | 取消「按 git 时间裁定规范冲突」约定（5 处文档）              | 意见 1                            |
| `afaa85f` | 逐服务就绪判据 + 就绪判据回归测试 + 命名随 project 隔离      | 意见 2（启动检查）、意见 3（固定名）            |
| `9021b21` | doctor 固定输出 schema（两种形状）+ scope + 可测直连调用 | 意见 2（doctor 范围）、意见 4（schema/调用） |
| `6db0d78` | C1：四个示例操作 + 文件任务协议 + wheel 隔离运行验证        | 意见 5（C1 边界澄清）                   |

**未做**（按你的决定）：不重开选型讨论；不换依赖版本；不为 `pnpm doctor` 改名；C3 的状态转换与恢复设计未预先限定列结构（见 §4）。

---

## 2. 源码清单（审查范围）

### 2.1 工作区配置

| 文件                                        | 状态     | 职责                                                                |
| ----------------------------------------- | ------ | ----------------------------------------------------------------- |
| `package.json`                            | 改      | scripts 新增 `test:infra` / `python:test` / `python:wheel`；依赖仍为精确版本 |
| `pnpm-workspace.yaml`                     | 未改     | workspace + `allowBuilds` + `minimumReleaseAgeExclude`（见 §3.8）    |
| `tsconfig.base.json` / `vitest.config.ts` | 未改     | 类型与测试配置                                                           |
| `python/pyproject.toml`                   | **新增** | 仅标准库；`requires-python = ">=3.14,<3.15"`；hatchling 构建              |
| `python/.python-version`                  | **新增** | 固定 `3.14.6`                                                       |
| `python/uv.lock`                          | **新增** | 已入库（1 个包：本工程自身）                                                   |

### 2.2 contracts（通用签名契约最小版）

| 文件                                                                   | 状态 | 职责                                                                                          |
| -------------------------------------------------------------------- | -- | ------------------------------------------------------------------------------------------- |
| `packages/contracts/src/{version,primitives,generator-signature}.ts` | 未改 | 协议版本、Digest/Ref（strictObject 拒额外字段）、生成元签名记录                                                 |
| `packages/contracts/src/errors.ts`                                   | 改  | **新增 `internal_error`**（不可重试），用于「实现撞到未预期情况」——不冒充业务失败；与 Python 侧 `protocol.ERROR_CODES` 同名对账 |
| `packages/contracts/test/*`                                          | 未改 | 19 个单测                                                                                      |

### 2.3 启动与 doctor

| 文件                                  | 状态     | 职责                                                                   |
| ----------------------------------- | ------ | -------------------------------------------------------------------- |
| `scripts/lib.sh`                    | 改      | compose 调用（project 唯一来源）、容器状态/等待、一次性服务、PG SQL、HTTP、namespace 查询      |
| `scripts/infra-up.sh`               | 改      | **逐服务判据**编排（见 §3.1）                                                  |
| `scripts/infra-stop.sh`             | 未改     | 只 stop、保留卷、不用 `down`                                                 |
| `scripts/bootstrap.sh`              | 改      | 生成凭据；**删除生成的 `COMPOSE_PROJECT_NAME`**（project 名唯一来源改到 lib.sh，避免两个真相） |
| `scripts/tests/wait-health.test.sh` | **新增** | 就绪判据回归（真实容器，5 用例）                                                    |
| `apps/cli/src/report.ts`            | **新增** | 两种固定输出 schema + `workerCheck(scope)`                                 |
| `apps/cli/src/index.ts`             | 改      | 命令分发、`--scope`、退出码、stdout 只输出 JSON                                   |
| `apps/cli/src/commands/doctor.ts`   | 改      | 五项检查 + `workerCheck(scope)`；失败诊断走 stderr                             |
| `apps/cli/src/workspace.ts`         | 改      | 新增 `ADAPDC_ROOT` 测试接缝                                                |

### 2.4 overlay 与角色初始化

| 文件                                         | 状态 | 职责                                                                               |
| ------------------------------------------ | -- | -------------------------------------------------------------------------------- |
| `infra/compose/docker-compose.overlay.yml` | 改  | **用 `!reset` 去掉全部固定 `container_name` 与网络 `name`**；端口/环境/卷仍用 `!override`/`!reset` |
| `infra/compose/initdb/00-catalog-roles.sh` | 改  | 首次建两角色并划清 DDL 边界；注释改为「删除数据卷不是维护手段」                                               |
| `infra/vendor/samples-server/**`           | 未改 | 上游逐字副本 + `SOURCE.md`（提交 SHA、逐文件 sha256）                                          |

### 2.5 Python 制品

| 文件                                             | 状态     | 职责                            |
| ---------------------------------------------- | ------ | ----------------------------- |
| `python/src/demo_ops/kernel.py`                | **新增** | 四个纯数值操作                       |
| `python/src/demo_ops/protocol.py`              | **新增** | request/result 校验、错误码、摘要、路径约束 |
| `python/src/demo_ops/task.py`                  | **新增** | 文件任务入口                        |
| `python/tests/test_kernel.py` / `test_task.py` | **新增** | 29 个 unittest                 |
| `scripts/python-test.sh` / `python-wheel.sh`   | **新增** | 测试与制品验证入口                     |

### 2.6 版本锁

`infra/lock/images.env`（tag+索引摘要）、`infra/lock/toolchain.json`（doctor 比对源）、`infra/lock/versions.md`：本轮**未改**。

---

## 3. 验收证据（脱敏原始输出）

### 3.1 `pnpm infra:up` —— 逐服务判据

```
--- 初始化任务 ---
  temporal-admin-tools (adapdc-temporal-admin-tools-1): exit=0
  temporal-create-namespace (adapdc-temporal-create-namespace-1): exit=0
--- PostgreSQL（Temporal 存储）：连接与 SQL ---
  postgresql (adapdc-postgresql-1): healthy
  db temporal 的表数 = 40
--- catalog PostgreSQL：连接、SQL 与角色 ---
  catalog-postgres (adapdc-catalog-postgres-1): healthy
  catalog 角色数（期望 2） = 2
--- Temporal：healthcheck + 目标 namespace 可查询 ---
  temporal (adapdc-temporal-1): healthy
  namespace default: state=Registered
--- UI：HTTP 可达 ---
  temporal-ui (adapdc-temporal-ui-1): running
  http://127.0.0.1:8080/ → 200
```

落地的判据与你的表一致：PostgreSQL = 连接 + 真实 SQL；Temporal = healthcheck + 目标 namespace 可查询
（用**临时 admin-tools 容器**查询，独立于 UI、也独立于本项目 TS 代码）；初始化任务 = 退出码 0
（效果由上面的 SQL/namespace 间接核对）；UI = HTTP 200，**不再以进程存活当就绪**；Worker = C0 不适用，
C4 后必须检查（§3.3）。

### 3.2 `doctor --scope=c0`（exit 0）

```json
{
  "schema": "adapdc.doctor-report/v1",
  "command": "doctor",
  "scope": "c0",
  "ok": true,
  "failed": [],
  "checks": [
    { "id": "versions", "status": "pass",
      "detail": { "source": "infra/lock/toolchain.json",
        "expected": { "node": "26.7.0", "pnpm": "12.3.4", "python3": "3.14.6", "uv": "0.12.3", "docker": "29.7.2", "dockerCompose": "5.5.1" },
        "measured": { "node": "26.7.0", "pnpm": "12.3.4", "python3": "3.14.6", "uv": "0.12.3", "docker": "29.7.2", "dockerCompose": "5.5.1" },
        "mismatched": [] } },
    { "id": "temporal-namespace", "status": "pass",
      "detail": { "address": "127.0.0.1:7233", "required": "default", "found": ["temporal-system", "default"] } },
    { "id": "catalog-db", "status": "pass",
      "detail": { "endpoint": "127.0.0.1:5433", "database": "adapdc_catalog", "user": "adapdc_catalog" } },
    { "id": "catalog-roles", "status": "pass",
      "detail": { "migratorCanDdl": true, "appCanDdl": false,
        "appError": "permission denied for database adapdc_catalog",
        "expectation": "migrator 可 DDL，运行角色不可 DDL（规格：schema 由 migrator 创建）" } },
    { "id": "cas-writable", "status": "pass",
      "detail": { "casDir": "/home/ebt/Downloads/adapdc/.adapdc/cas", "probe": "…/.doctor-probe-160615", "roundTrip": true } },
    { "id": "worker-poll", "status": "not_applicable",
      "detail": { "reason": "C0 范围不含 Worker；Worker 属 C4", "requiredFrom": "C4" } }
  ],
  "scopeNote": "scope=C0：只证明基础设施与凭据布局（版本、namespace、catalog 库、CAS 可写、角色权限）。不证明数值计算、登记语义或任何科学结论，也不证明 T01–T20；Worker 检查属 C4，本项目前不适用。"
}
```

**关于「运行角色不持 DDL」的准确措辞**（按你的修正）：以上**只证明数据库级 `CREATE` 被拒**
（`permission denied for database adapdc_catalog`）。它**不覆盖** PostgreSQL 的对象修改/删除能力与
**所有权及其角色继承**（例如对象属主、`ALTER`/`DROP` 的授权路径）。schema、对象所有权与角色继承的检查
排在 **C3**（建 schema 之时）。

### 3.3 `doctor --scope=c4`（exit 1；缺 Worker 必须失败）

```
stderr: doctor 未通过：worker-poll
stdout: {"schema":"adapdc.doctor-report/v1","scope":"c4","ok":false,"failed":["worker-poll"], …}
```

`worker-poll` 的 `detail.reason`：`scope=c4 要求 Worker 可 poll；Worker 存活检查尚未实现（C0b 未建 Worker）。
缺失即失败，不降级为 not_applicable。`  —— fail-closed，**不会永久「不适用」**。

### 3.4 就绪判据回归 `pnpm test:infra`（真实容器，5/5）

```
--- 用例 1：healthcheck 永远不通过 → 必须失败，不得放行 ---
  ✓ 状态解析为 'unhealthy'（不是 running）—— 有 healthcheck 的容器不会退化为进程状态
  ✓ 未通过 healthcheck 的容器被拒绝（等待函数返回非零）
--- 用例 2：healthcheck 会通过 → 必须放行 ---
  ✓ 通过 healthcheck 的容器被放行（状态 'healthy'）
--- 用例 3：无 healthcheck → 运行中即放行（这是弱判据，调用方必须另加服务级检查） ---
  ✓ 无 healthcheck 时状态解析为 'running'（预期如此）
  ✓ 运行中的无 healthcheck 容器被放行

就绪判据回归：通过 5 / 失败 0
```

**关于你点名的那个风险**：`.State.Health` 存在时模板只返回 `starting/healthy/unhealthy`，
**不可能返回 `running`**——所以此前"已配置 healthcheck 却未健康"不会被放行。
但此前这只是模板细节的副作用，现已改为**显式 fail-closed**：`adapdc_wait_container` 若对
「有 healthcheck 的容器」解析出 `running`，直接判为判据异常并失败。上述用例 1 钉住了这条性质。

### 3.5 证伪测试（自检不是「永远通过」）

| 反例                                                                           | 实测                                                                                           |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 改坏 `CATALOG_APP_PASSWORD`（**先证改动生效**：文件 sha256 由 `ebf571ad…` 变为 `705f4c26…`） | exit 1，`failed=["catalog-roles"]`，详情报 `password authentication failed for user "adapdc_app"` |
| 移走 `infra/.env`                                                              | exit 1，输出为 **cli-error** 形状（`code=io_error`，**无 `checks` 字段**）                               |
| 还原后重跑                                                                        | exit 0，`ok=true`、`failed=[]`；`.env` sha256 回到 `ebf571ad…`                                    |

**过程如实说明**：我第一次跑「改坏密码」时得到 `ok=true`，差点当成"检查没生效"。复核发现是**我的替换根本没生效**
（用了字面量而非正则），于是重做并要求**先证明文件确实变了**（比对 sha256）——改后立刻复现失败。
这条已经写进 `docs/c0-status-review.md` 的 §5.3：凡「比较两个东西是否相同」的检查，都可能因为前提没发生而假通过。

### 3.6 C1 制品：`pnpm python:test`（29/29）与 `pnpm python:wheel`

```
Ran 29 tests in 0.446s
OK
```

```
--- 1. 构建 wheel ---
  ✓ wheel: demo_ops-0.1.0-py3-none-any.whl
    sha256: sha256:ee93536fff8e3f6cef3caad0f859cb1aea58e7486161a914f39a070a2ee92346
    bytes : 8706
--- 2. 存入内容寻址的制品目录（测试用，非正式 CAS） ---
  ✓ 制品已存在且内容相符（未覆盖）
  ✓ 清单: wheels/manifests/ee93536fff…json
--- 3. 隔离环境安装（具名暂存 + 仅本地 wheel + --no-index） ---
 + demo-ops==0.1.0 (from file:///tmp/tmp.LetDfk5HEq/demo_ops-0.1.0-py3-none-any.whl)
--- 4. 依赖来源：隔离环境里应只有 demo-ops ---
    demo-ops 0.1.0
  ✓ 依赖来源可交代：仅 demo-ops（无第三方依赖）
--- 5. 脱离源码运行（工作目录在仓库之外，且不带 PYTHONPATH） ---
    产物 series = [0, 1, 2, 3]
    结果 digest = sha256:f2f991d74dfbb2edf7f4475dcb7d82989de00a71e44bb11d4a6fbb49442577b6
    demo_ops 来自: …/venvs/3.14.6-ee93536…/lib/python3.14/site-packages/demo_ops/__init__.py
  ✓ 模块来自隔离环境（不是源码树）
  ✓ 未从源码树加载

Python 制品验证通过：wheel sha256:ee93536fff8e3f6c… / 隔离环境 1 个发行版 / 脱离源码运行成功
提醒：正式 CAS 发布与 catalog 登记尚未接通（C3），本轮不声明 demo:publish 可用。
```

**C1 边界（按你的澄清）**：只做 wheel 构建、摘要清单、隔离安装、脱离源码运行验证；
**制品存在测试用目录** `(.adapdc/python-artifacts/，gitignore)` 并按摘要引用；
**正式 CAS 发布与 catalog 登记在 C3 接入**；根 `package.json` 未声明 `demo:publish`。
另有 `test_demo_chain_matches_b_squared`：用文件协议跑完整条链（sequence → shift×3 → score×3 → aggregate），
判据 **0/1/4**。

### 3.7 命名隔离（脱敏 Compose 解析；凭据字段未采集）

```
    image: postgres:16@sha256:f1c3376c…            host_ip: 127.0.0.1   published: "5433"   source: catalog-pg-data
    image: postgres:16@sha256:f1c3376c…            （Temporal 自有 PG：无端口）              source: temporal-pg-data
    image: temporalio/server:1.31.0@sha256:b021b3… host_ip: 127.0.0.1   published: "7233"
    image: temporalio/admin-tools:1.31.0@sha256:…  （两处，均无端口）
    image: temporalio/ui:2.49.1@sha256:a066bd…     host_ip: 127.0.0.1   published: "8080"
    name: adapdc_temporal-network
    name: adapdc_catalog-pg-data
    name: adapdc_temporal-pg-data
```

* **解析结果里没有任何 `container_name`**（全部被 `!reset` 去掉，容器名由 project 派生为 `adapdc-*-1`）。
* 网络名与卷名均以 project 为前缀 → 无跨项目共享的固定名称。
* project 名唯一来源是 `scripts/lib.sh` 的 `ADAPDC_COMPOSE_PROJECT`；`ADAPDC_ENV_FILE` 可指向另一份
  环境文件，第二实例换端口即可（**双实例端到端验证按你的要求排在服务测试之前**，本轮只做上述解析检查）。
* **数据保留是实证的**：改名前在 catalog 库留标记 `before-name-reset`，改名后（`down` **不带 `-v`** → `up`）
  标记仍在，卷名未变。
* 改动过程中 `infra:up` 立刻失败过一次：脚本里还硬编码着旧容器名 `temporal-postgresql`。
  **判据失败而非静默通过**，已改为按 compose 标签查找。

### 3.8 定点豁免的确切配置与理由（供你判断）

`pnpm-workspace.yaml` 中的**全部**相关配置：

```yaml
allowBuilds:
  esbuild: true
  protobufjs: true

minimumReleaseAgeExclude:
  - '@rolldown/binding-openharmony-arm64'
```

* **豁免对象**：`@rolldown/binding-openharmony-arm64`（**精确包名，无通配**）。
* **是谁引入的**：不是直接依赖，由 `vitest@5.0.0` 传递引入。
* **命中的策略**：pnpm 12 默认 `minimumReleaseAge`（24 小时新鲜度）。该条目发布距当时不足 24 小时，
  导致 `pnpm install --frozen-lockfile` 直接失败。
* **理由**：它是 **openharmony-arm64** 平台的预编译绑定，本机（linux/x64）**不会执行**其中的二进制；
  且我们无法选择它的版本（由 vitest 的依赖图决定）。
* **为此没有做什么**：**没有**放宽全局 `minimumReleaseAge`；两个**直接**依赖改为满 24 小时的等价版本
  （`zod` 4.6.1→4.5.4、`@types/node` 26.5.1→26.5.0）。
* **我没有验证的**：该包的内容本身（未审计其二进制）；豁免的依据是"平台不匹配 + 非直接依赖 + 无法选版"，
  **不是**"已确认无害"。若你要收紧，可改为对该传递依赖做版本/来源约束或锁到不含它的 vitest 版本。

---

## 4. 剩余阻塞与未闭合

| 项                               | 状态             | 说明                                                                                                                                                                                                                                              |
| ------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **C3 前的状态转换与恢复设计**（意见 4）        | **未开始，属下一道关口** | 事实来源必须分开：可靠完成清单（证明产物已提交）/ catalog 登记记录（证明已纳入目录）/ 状态查询（结合两者报告 computed、pending-registration、registered、conflict）。数据库离线时**无法**靠库内 `registration_status=pending` 记录登记失败——这一点已在差异表缺口 **G1** 记录。C3 可采用状态列、事件表或投影，但须解释**事实来源与恢复路径**；**不预先限定**为「两个字段」。 |
| Worker 存活检查                     | 未实现（C4）        | 现行是 fail-closed：`scope=c4` 必然失败，不会静默通过                                                                                                                                                                                                          |
| C1 制品 → 正式 CAS / catalog 登记     | 未接通（C3）        | 本轮不声明 `demo:publish`                                                                                                                                                                                                                            |
| DDL 深度检查（schema / 对象所有权 / 角色继承） | 未做（C3）         | 见 §3.2 的措辞修正                                                                                                                                                                                                                                    |
| 双实例端到端验证                        | 未做             | 排期：服务测试之前；本轮只做命名解析检查（§3.7）                                                                                                                                                                                                                      |
| `pnpm doctor` 命令名冲突             | 已按你的决定处理       | 保留脚本名 `doctor`，文档统一 `pnpm run doctor`；机器可读用 `node apps/cli/src/index.ts doctor --scope=c0`                                                                                                                                                      |
| T01–T20                         | 一个都没跑          | 本文不声称任何一项通过                                                                                                                                                                                                                                     |

**一处仍需你判定的口径**：「无旧资产依赖」已按你的要求理解为「**无旧研究代码与数据的执行依赖**」
（继承研究认识本来就允许）。若你的本意更窄/更宽，请指出——文档措辞会随之改。

---

## 5. 复现方式

```bash
pnpm install --frozen-lockfile
pnpm bootstrap
pnpm infra:up                      # 逐服务判据
node apps/cli/src/index.ts doctor --scope=c0   # 机器可读（纯 JSON）
node apps/cli/src/index.ts doctor --scope=c4   # 应 exit 1（缺 Worker）
pnpm test:infra pnpm test:unit pnpm python:test pnpm python:wheel
pnpm -r typecheck
pnpm infra:stop                    # 保留持久卷
```

证伪（§3.5）请**先证明改动生效**再判定，否则会得到与"检查失效"无法区分的假通过。
