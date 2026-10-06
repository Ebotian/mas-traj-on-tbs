# AdaPDC 现状审查（C0 阶段收尾）

> **文档性质：快照，不随演进更新。**
> 锚点：commit `67eead4`（2026-09-10）。之后的变化以代码 + 最近提交为准，
> 冲突按仓库约定「git 时间就近」裁定；本文件不覆盖 `docs/README.md` 登记的其他文档的效力。
>
> **目的**：让审查者在有限时间内判断「当前状态是否可信」，并能**独立复核**本文每一条结论。
> 因此本文只写可被命令复现的事实；凡属判断的地方都标出「这是判断」，并写明若不同意应改哪里。

---

## 0. 给审查者的三条路径

| 你有的时间 | 建议做什么                                                                     |
| ----- | ------------------------------------------------------------------------- |
| 5 分钟  | 读 §1、§6、§9。§9 是我主动列出的、最可能有问题的地方。                                          |
| 30 分钟 | 加读 §2（关口证据）与 §4（关键决定），按 §2.3 的复核清单自己跑一遍。                                  |
| 深查    | 按 §2.4 的「判据强弱」逐条检查判据是否配得上结论；读 §3.2 的文件清单，逐个文件确认职责；重点看 §5.3 那个我自己差点放过的假证据。 |

---

## 1. 一句话结论

**C0 关口已过：基础设施起得来、停得掉、重复起不漂移，依赖与镜像版本已锁死，且每一项都有命令级证据。**
数值计算、执行框架、领域契约、科学结论**一概尚未实现**——本文不声称其中任何一项。

现在真能做的事（在仓库根）：

```bash
pnpm install --frozen-lockfile    # 依赖锁定可复现
pnpm bootstrap                    # 生成本地凭据（幂等，已存在则不动）
pnpm infra:up                     # 起 Temporal + PostgreSQL(×2)，等就绪
pnpm run doctor                   # 逐项自检，输出 JSON，失败非零退出
pnpm infra:stop                   # 停服务，保留持久卷
pnpm -r typecheck && pnpm test:unit
```

现在**不能**做的事：跑任何实验、提交任何实验规格、得到任何数值结果。`db:migrate`、
`demo:*`、`worker` 这些命令**尚未在 `package.json` 中声明**（见 §7），
`experiments/` 为空。

---

## 2. C0 关口与证据

### 2.1 关口是怎么定义的

规格 `docs/adapdc_scaffold_implementation.typ`（含 ADR-001）把 C0 的实现边界定为
「文档效力表、ADR、通用签名契约、scaffold、依赖与 Compose 来源锁」，
关口是 **`infra:up` 与 `doctor`**，并要求「明确无旧资产依赖」。
本次拆成两步执行：**C0a**（文档治理 + 只读勘察，4 个提交）、**C0b**（脚手架落地，4 个提交）。

### 2.2 实测证据

| #   | 判据           | 命令                                                 | 实际结果                                                                                                                                                                               |
| --- | ------------ | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E1  | 基础设施起得来且真的就绪 | `pnpm infra:up`                                    | exit 0；`temporal-postgresql` healthy、`adapdc-catalog-postgresql` healthy、`temporal` healthy、`temporal-ui` running；`temporal-admin-tools` exit=0、`temporal-create-namespace` exit=0 |
| E2  | 自检全项通过       | `pnpm run doctor`                                  | exit 0；`ok=true`、`failed=[]`；五项 pass + 一项 `not_applicable`（见 §6.2）                                                                                                                 |
| E3  | 依赖可复现        | `pnpm install --frozen-lockfile`                   | 通过；输出含 `Lockfile passes supply-chain policies`；不改锁文件                                                                                                                               |
| E4  | 类型检查         | `pnpm -r typecheck`                                | exit 0；对 `packages/contracts` 用 `--listFiles` 确认其 8 个源/测试文件**确实被检查**（不是空跑）                                                                                                         |
| E5  | 单元测试         | `pnpm test:unit`                                   | 3 个文件 / 19 个测试全通过                                                                                                                                                                  |
| E6  | 重复启动不漂移      | 连续两次 `pnpm infra:up` 后比对容器 ID                      | 六个容器 ID **逐一不变**（不是「容器数不变」这种弱判据）                                                                                                                                                   |
| E7  | 停止保留数据       | 建标记 → `infra:stop` → `infra:up` → 查标记              | 标记仍在（1 行，时间戳早于 stop）；卷 `adapdc_temporal-pg-data`、`adapdc_catalog-pg-data` 始终存在                                                                                                     |
| E8  | 端口不对外        | `docker compose config` + `docker ps`              | 5433 / 7233 / 8080 均绑 `127.0.0.1`；Temporal 自有 PG **不发布任何宿主端口**                                                                                                                     |
| E9  | 凭据不入库        | `git check-ignore infra/.env`；脚本比对渲染后的 environment | `infra/.env` 被忽略且未入库；各服务凭据值**逐项命中** bootstrap 生成的 `.env`，上游硬编码的 `temporal` 字样不出现在渲染结果中                                                                                             |
| E10 | vendor 逐字    | `diff` 对上游 5 个文件                                   | 5 个文件全部逐字一致（sha256 记在 `infra/vendor/samples-server/SOURCE.md`）                                                                                                                     |
| E11 | 无旧资产依赖       | `git ls-files` 全量检视                                | 53 个受控文件，无一来自 emsx（历史仓库）；本阶段未引入任何旧资产                                                                                                                                               |

### 2.3 复核清单（审查者自己跑）

```bash
cd <repo>
git log --oneline -8                    # 应看到 C0a/C0b 的 8 个提交（§3.1）
pnpm install --frozen-lockfile
pnpm bootstrap                          # 连跑两次：第二次必须不改 infra/.env（比 sha256）
pnpm infra:up
pnpm run doctor                         # 注意：不是 pnpm doctor，见 §6.1
# 直接手敲 compose 时须自己导出该变量，否则 overlay 插值会明确报错（见 D6）
ADAPDC_CATALOG_INITDB_DIR="$PWD/infra/compose/initdb" \
docker compose --project-name adapdc \
  --env-file infra/lock/images.env --env-file infra/.env \
  -f infra/vendor/samples-server/compose/docker-compose-postgres.yml \
  -f infra/compose/docker-compose.overlay.yml config | grep -E 'image:|host_ip'
pnpm infra:stop && docker volume ls      # 卷必须仍在
```

**反例检查（建议做，本次已实跑）**：

| 反例                            | 实测结果                                                                                                                  |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 把 `infra/.env` 移走             | **exit 1**，输出为顶层错误形态 `{"ok":false,"error":{"code":"io_error",...}}`——注意此时**没有** `checks` / `failed` 数组：配置缺失会在逐项检查之前短路 |
| 把 `CATALOG_APP_PASSWORD` 改成错值 | **exit 1**，`ok=false`、`failed=["catalog-roles"]`，详情报 `password authentication failed for user "adapdc_app"`           |
| 还原后重跑                         | `ok=true`、`failed=[]`                                                                                                 |

一个「永远通过」的自检等于没有自检——上面两条是它的证伪测试，都已通过。

**由此暴露的一处行为不一致（已记录，未改）**：`doctor` 正常运行时输出「逐项报告」形态，
但配置缺失时会退化为「顶层错误」形态。两种都是结构化 JSON、都非零退出，但**形状不同**，
机器消费方需同时处理。候选修法是把配置读取包进检查项，使其始终返回逐项报告——本次未做。

### 2.4 判据强弱（哪些结论有多硬）

诚实标注，避免读者高估：

| 结论           | 判据强度                                                                                                                                            |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 容器就绪         | **强**：按 healthcheck 逐服务等待，一次性服务核对退出码；不是「容器在跑」                                                                                                   |
| 幂等           | **强**：容器 ID 级比对                                                                                                                                 |
| 卷保留          | **强**：数据标记存活，且该标记**无法**由任何启动脚本重建（initdb 只在空卷运行）                                                                                                 |
| 镜像锁定         | **中**：digest 来自首次实际拉取后的 `RepoDigests`；**未**验证镜像内容签名或来源证明                                                                                        |
| 运行角色「不持 DDL」 | **中**：实测 `CREATE SCHEMA` 被拒（`permission denied for database adapdc_catalog`）。这只证明**库级** CREATE 缺失；表级/未来 schema 内的权限要等 C3 建 schema 时另行验证（见 §9.4） |
| CAS 可写       | **弱**：只证明一个目录能写读删；**内容寻址语义**属 C3，此处不含                                                                                                           |
| 「无旧资产依赖」     | **中**：证据是「仓库里没有」，不是「代码里查不到引用」——本阶段无代码可查，结论适用但会随代码增长失效                                                                                           |
| doctor 覆盖范围  | **有限**：见 §6.2 与 §8.4，它不证明数值计算、登记语义与任何科学结论                                                                                                       |

---

## 3. 交付物

### 3.1 提交时间线（本阶段 8 个提交）

| #   | 提交        | 内容                                                                     |
| --- | --------- | ---------------------------------------------------------------------- |
| C0a | `a3c1191` | ADR-001 逐字摘录落库 `docs/adr/001-scaffold-baseline.md`（附来源提交 + 源文件 sha256） |
| C0a | `a0b8f2a` | catalog 契约 × 实施基线**逐条差异表** + 契约顶部取代声明 + 文档索引登记                         |
| C0a | `638c71d` | 只读勘察记录：Temporal 来源 SHA、镜像候选、工具链版本、C0b 风险项                              |
| C0a | `2cf6cda` | 补装 compose 后重跑校验通过，解除 C0b 阻塞（保留首次失败的原始报错）                              |
| C0b | `ca2e3ca` | 工作区骨架 + 依赖锁 + 通用签名契约最小版                                                |
| C0b | `531bdd3` | vendor 上游 Compose + overlay + bootstrap/infra 脚本                       |
| C0b | `84a8367` | `doctor` 命令 + 起容器，C0 关口通过                                              |
| C0b | `67eead4` | 版本锁记录 + README/AGENTS/调研同步                                             |

### 3.2 受控文件清单（53 个）与职责

**研究层（C0a 之前已存在，本次未改内容）**

| 文件                                        | 角色                                   |
| ----------------------------------------- | ------------------------------------ |
| `docs/research-foundations.md`            | 研究起点：继承自 emsx 的已证结论 / 候选 / 已否证教训     |
| `docs/adapdc_theory_review.typ`           | 理论综述：主命题 H_S/H_A、五个命题、文献             |
| `docs/experiment-catalog-contract.md`     | 实验目录语义契约 + §11 执行状态表（本阶段仅在其顶部加了取代声明） |
| `docs/adapdc_architecture_report.typ`     | 分层架构、编排与数据库裁决                        |
| `docs/adapdc_scaffold_implementation.typ` | **实施基线**（含 ADR-001、T01–T20、C0–C7）    |

**新增的治理文档**

| 文件                                  | 角色                                      |
| ----------------------------------- | --------------------------------------- |
| `docs/adr/001-scaffold-baseline.md` | ADR-001 的逐字摘录，含来源提交 + 源文件 sha256（可机械核对） |
| `docs/catalog-contract-diff.md`     | 契约 × 基线的逐条差异表（一致/细化/取代/顺延）+ 缺口 G1–G4    |
| `docs/dev/c0-version-survey.md`     | 勘察当日快照（含未勘察项与 C0b 结果回填）                 |
| `docs/README.md`                    | 文档索引（新增文档均已登记）                          |

**工程层（C0b 新增）**

| 路径                                                                                            | 职责                                                    | 状态           |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------ |
| `apps/cli/src/index.ts`                                                                       | 命令分发，输出结构化 JSON，未知命令 exit 2                           | 完成（仅 doctor） |
| `apps/cli/src/commands/doctor.ts`                                                             | 五项检查 + 一项 not_applicable                              | 完成           |
| `apps/cli/src/exec.ts` / `workspace.ts`                                                       | 参数数组调用外部命令；定位仓库根、读 `.env`                             | 完成           |
| `packages/contracts/src/{version,errors,primitives,generator-signature}.ts`                   | 协议版本、错误码与可重试分类、Digest/Ref（strictObject 拒额外字段）、生成元签名记录 | **最小可冻结版**   |
| `packages/contracts/test/*.test.ts`                                                           | 19 个单测                                                | 完成           |
| `infra/vendor/samples-server/**`                                                              | 上游 Compose 逐字副本 + `SOURCE.md`（提交 SHA、逐文件 sha256）      | 完成（5 文件逐字一致） |
| `infra/compose/docker-compose.overlay.yml`                                                    | overlay：catalog-postgres、持久卷、localhost 端口、凭据注入        | 完成           |
| `infra/compose/initdb/00-catalog-roles.sh`                                                    | 建 migrator / 运行角色并划清 DDL 权限（**不建表**）                  | 完成           |
| `infra/lock/{images.env,toolchain.json,versions.md}`                                          | 镜像 tag+digest、工具链期望值（doctor 比对源）、版本锁说明                | 完成           |
| `scripts/{bootstrap,infra-up,infra-stop,lib}.sh`                                              | 凭据生成（幂等）、起停、就绪等待、一次性服务核对                              | 完成           |
| `package.json` `pnpm-workspace.yaml` `tsconfig.base.json` `vitest.config.ts` `pnpm-lock.yaml` | 工作区、精确依赖、类型与测试配置、锁文件                                  | 完成           |

**未入库（按设计）**：`infra/.env`（凭据）、`.adapdc/`（运行目录与 CAS 根）、
`node_modules/`、Docker 卷与容器。`.gitignore` 已覆盖，`git check-ignore` 逐项验证过。

---

## 4. 关键决定与理由（审查重点）

每条都给出：决定 / 理由 / 代价 / **若不同意应改哪里**。

**D1 · vendor 逐字副本与 overlay 分离**
决定：`infra/vendor/` 只放上游逐字副本（含 sha256 清单），本仓库的改动用 `infra/compose/` 的 overlay 通过 compose 原生 `-f` 合并实现。
理由：可核对来源，且不把我们的改动混进上游副本。
代价：overlay 需要 `!override` / `!reset` 标签处理合并语义（见 D4）。
若不同意：改为维护一份「派生部署文件 + 改动清单」，但会失去「与上游逐字节比对」的能力。

**D2 · 凭据由 bootstrap 生成，不入库**
决定：`scripts/bootstrap.sh` 生成随机凭据写入 `infra/.env`（权限 600，幂等不覆盖）。
理由：规格明令「默认开发凭据不得入版本库，bootstrap 生成本地配置」。上游 compose 硬编码的 `POSTGRES_PASSWORD: temporal` 保留在 vendor 副本中（否则无法核对 SHA），但**被 overlay 整体覆盖**。
代价：`infra/.env` 是本地状态；换机器需重跑 bootstrap。**移动仓库位置不会有问题**（见 D6 的路径处理）。

**D3 · catalog 独立容器、独立库、独立凭据；角色权限预先划清**
决定：`catalog-postgres` 与 Temporal 自有 PG 完全分开（不同容器、凭据、库）；initdb 建两个角色——migrator 有 `CREATE ON DATABASE`，运行角色只有 CONNECT/USAGE。
理由：规格要求「独立数据库、凭据、迁移」+「停止 catalog 不应同时停止 Temporal」（故障测试前提）+「schema 由独立 migrator 创建，运行服务不持 DDL 权限」。
代价：本机多一个容器，端口多一个（127.0.0.1:5433）。
若不同意：这是规格的硬要求，改它需要先改 ADR-001。

**D4 · 端口只绑 localhost；Temporal 自有 PG 完全不暴露**
决定：catalog 5433、Temporal gRPC 7233、UI 8080 都绑 `127.0.0.1`；Temporal 自己的 PostgreSQL 用 `!reset []` **不发布任何宿主端口**。
理由：规格要求「只绑定 localhost 的管理端口」；Temporal 存储不需要从宿主访问，不暴露比暴露更安全。
实现注意：overlay 用 `!override`/`!reset` 而**不是**依赖 compose 的序列合并，避免「两个端口都生效」这类隐患。

**D5 · 版本锁 = tag + 索引摘要**
决定：`infra/lock/images.env` 写成 `16@sha256:…` 形式，通过上游 compose 的 `${POSTGRESQL_VERSION}` 插值生效。
理由：tag 可读、digest 保证内容不可被重新推送替换（规格要求「锁定为验证过的 tag＋digest」）。
代价（**设计气味，供审查**）：变量名仍是「VERSION」，却承载 digest；读文件的人可能意外。已在文件内注释说明。
若不同意：改成独立的 `*_IMAGE` 变量并在 overlay 覆盖 `image:`——更清晰，但会与上游插值写法脱钩。

**D6 · overlay 里不放相对路径**
决定：catalog 的 initdb 挂载用 `${ADAPDC_CATALOG_INITDB_DIR}`，由 `scripts/lib.sh` 按当前 checkout 位置导出绝对路径。
理由：实测发现 compose 以**第一个 `-f` 文件**所在目录为项目目录解析相对路径，`./initdb` 会被解析到 vendor 目录下的同名路径（不存在）。这是实测结论，不是推测。
代价：多一个由脚本导出的环境变量；直接从 compose 命令手敲会缺这个变量（会明确报错，不静默）。

**D7 · 根 `package.json` 只声明本步实现的 scripts**
决定：目前只有 `bootstrap` / `infra:up` / `infra:stop` / `doctor` / `typecheck` / `test:unit`。`db:migrate`、`demo:*`、`worker` **不声明**。
理由：规格禁止「不通过空壳运行冒充已实现」；声明一个必然失败的入口是误导。
代价：与规格 §「自定义命令」的完整清单暂时不一致——**这是有意的阶段性差异**，各命令由其对应提交加入。

**D8 · 通用签名契约只做最小版**
决定：`packages/contracts` 只含协议版本、错误码、Digest/Ref、生成元签名记录；**不含** IR / Plan / DSL / compiler。
理由：规格里 C2 = 「contracts＋DSL＋IR＋compiler」，而 C0 边界含「通用签名契约」，G1 说明「C0 的通用签名只是最小可冻结版本，C2 完成实际编译校验」。
代价：**这是本次最需要审查者判断的一处**——我在 C0 / C2 之间划了线，若你认为「契约」在 C0 就该完整，这一条要推翻。

---

## 5. 执行中发现并修复的缺陷

**这些都是执行中实测暴露的，不是预先设计好的。**

### 5.1 `docker compose up --wait` 与一次性服务不兼容（首次 `infra:up` exit 1）

首次 `infra:up` 以 exit 1 结束，但**栈其实完全起来了**（网络、卷、四个长期服务全部健康）。
原因是 compose 把一次性服务 `temporal-create-namespace` 的正常退出（0）判为失败。
修法：改为显式就绪判据——长期服务等 healthcheck，一次性服务核对退出码为 0，容器按 compose 标签查找（不依赖写死名）。
**审查提示**：请确认这次修改是**收紧**而不是放宽判据。我的理由是：原来是「compose 的粗判据且误报失败」，现在是「逐服务明确判据」，且新增了原来没有的一次性服务退出码核对。

### 5.2 `temporal-ui` 没有 healthcheck，等待函数死等到超时

等待函数最初只认 `healthy`，而 `temporal-ui` 上游没定义 healthcheck，状态只会是 `running`，于是死等。
修法：`healthy | running` 都算就绪并注明原因。
**审查提示**：这意味着「running 也算就绪」——对无 healthcheck 的服务，我们没有更强的判据可用（短期答案）。

### 5.3 我自己写的幂等检查是**无效的**（差点让假证据过关）

我第一次写的是 `docker ps --format '{{.Names}}={{.Id}}'`——`docker ps` 的模板里**没有 `.Id` 字段**，两次都拿到空串，md5 相同，于是脚本报告「幂等成立」。**这是假证据。**
我察觉后改用 `docker inspect -f '{{.Id}}'` 重做，六个容器 ID 逐一比对。
**审查提示**：请把这条当作对本次其他证据的提醒——凡「比较两个东西是否相同」的检查，都可能因为两边都为空而假通过。§2.3 的反例检查就是为这类问题准备的。

### 5.4 compose 相对路径解析（见 D6）

`docker compose config` 通过 ≠ 路径正确。首次 `config` 通过时，`./initdb` 被解析到 `infra/vendor/samples-server/compose/initdb`（不存在）。
修法见 D6。**审查提示**：这条说明「config exit 0」不足以证明挂载正确，必须读解析后的 source 路径。

---

## 6. 与规格的偏差与未闭合项

### 6.1 `pnpm doctor` 被 pnpm 内置命令遮蔽（偏差，未自行改判）

pnpm 12 有**内置** `doctor`（`Run diagnostics on the pnpm installation and environment`），
会接手同名命令，因此 `pnpm doctor` 跑的是 pnpm 自己的诊断。
本项目的自检须用 **`pnpm run doctor`**（或直接 `tsx apps/cli/src/index.ts doctor`）。
我保留了规格要求的脚本名 `doctor`，未改名规避——
**审查提示**：若你认为「用户照规格敲 `pnpm doctor` 必须得到本项目的自检」，那就必须改名（例如 `doctor:adapdc`），这是你的决定。

另外：`pnpm run doctor` 会混入 pnpm 自身的横幅行，输出不再是纯 JSON。
要机器可读的纯 JSON，请直接调用 CLI（`tsx apps/cli/src/index.ts doctor`）。

### 6.2 `worker-poll` 未做（有意留白）

规格把「Worker poll 成功」列为启动健康检查的一部分，但 Worker 属 C4。
`doctor` 该项标 `not_applicable` 并在 `reason` 里写明「Worker 属 C4，本次不假装该项通过」。
**审查提示**：这是「如实留白」，不是「检查通过」。§1 与 doctor 的 `scopeNote` 都重复了这一点。

### 6.3 差异表缺口 G1–G4 状态未变

`docs/catalog-contract-diff.md` 记录的四个缺口，本阶段**一个也没有关闭**（它们分属 C1/C3/R1/R2）。
其中 **G1 是唯一的实质性发现**：契约要求 `computed ≠ registered` 的强制手段是「两个独立字段/时间戳」，
但 migration 001 的 `executions` 表没有登记状态列——**C3 落地表结构时必须解决**，否则契约 §3 的不变量无处落脚。
**审查提示**：G1 是本阶段「发现但按边界没修」的东西，建议在批 C3 之前先确认它的处置方案。

### 6.4 固定容器名与网络名的冲突面（未处理）

上游 compose 写死了 `container_name`（`temporal`、`temporal-postgresql`…）与网络名 `temporal-network`。
同机若有其他 compose 项目用同名，会冲突。我保留了上游写法（未用 `!reset` 改名），因为改名属于对上游结构的改动，超出本步范围。
**审查提示**：若你本机已有同名容器，`infra:up` 会失败——届时需决定是改名还是接受约束。

---

## 7. 尚未实现（与 C1–C7 的对应）

| 阶段 | 内容                                           | 现状                           | 入口是否已声明 |
| -- | -------------------------------------------- | ---------------------------- | ------- |
| C1 | Python 示例、wheel 发布、文件任务入口                    | **未开始**                      | 否       |
| C2 | contracts 补全 + DSL + IR + compiler           | **未开始**（仅签名契约最小版）            | 否       |
| C3 | CAS、应用迁移（migration 001/002）、catalog 事务       | **未开始**（G1 待此解决）             | 否       |
| C4 | Temporal Workflow / Activities / 本地进程 helper | **未开始**（worker-poll 检查同属此阶段） | 否       |
| C5 | 变体、缓存、实际输入 provenance                        | 未开始                          | 否       |
| C6 | 故障注入、重放、备份恢复（T08–T13、T17–T18）                | 未开始                          | 否       |
| C7 | 新生成元扩展、查询、理论绑定（T19–T20）                      | 未开始                          | 否       |

**T01–T20 一个都没有运行过，本文不声称任何一项通过。**
`docs/adapdc_scaffold_implementation.typ` 的 C0–C7 是交付依赖顺序，不是工期承诺。

---

## 8. 已知风险与限制

1. **仅适用于可信单机开发**：无 TLS、无集群、无生产权限隔离（规格同此定位）。端口虽只绑 localhost，但同机进程可访问。
2. **依赖版本很新**：TypeScript 7.0.2（Go 端口的大版本）、Zod 4.5.4、Vitest 5.0.0、Node 26。本次实测可用，但生态兼容面未穷尽；升级须重新走一遍关口。
3. **供应链策略影响选版**：pnpm 12 的 `minimumReleaseAge`（24h）导致 `zod` 与 `@types/node` 各降一个小版本；另有一个平台绑定包被定点豁免。理由写在 `pnpm-workspace.yaml` 注释与 `infra/lock/versions.md`。
   **审查提示**：定点豁免是安全护栏上的一个洞，请确认理由可接受。
4. **`doctor` 的边界**：它证明的是「环境与凭据布局正确」，**不证明**数值计算、登记语义、幂等登记、恢复语义或任何科学结论。`scopeNote` 已写在输出里。
5. **initdb 只在空数据卷运行一次**：需要重建角色时，必须先显式删除 catalog 卷；脚本不会自动补建。
6. **无 CI**：所有验证都是在开发机手动跑的命令。规格要求 CI 至少分 pure / services 两个 job——属后续阶段，本次未建。
7. **首次拉镜像依赖网络**：本次拉取耗时数分钟（网络较慢）。镜像已按 digest 锁定，重拉不会漂移。

---

## 9. 我主动列出的、最该被质疑的五点

1. **C0 关口是否被放宽了？** 关键是 §5.1 那次修改。请确认「逐服务显式判据」强于原来的 `up --wait`，而不是为了过关而放宽。
2. **`packages/contracts` 是否提前做了 C2 的活？** 见 D8。C0/C2 的界线是我划的。
3. **`minimumReleaseAge` 的定点豁免是否可接受？** 见 §8.3。它没有放宽全局策略，但确实开了一个口子。
4. **`catalog-roles` 的检查是否配得上「运行服务不持 DDL 权限」这个说法？** 见 §2.4：它只证明**库级** CREATE 缺失；C3 建 schema 后需要追加表级验证。
5. **「无旧资产依赖」的证据强度**：目前是「仓库里没有」，不是「代码里没有引用」。本阶段没有代码可引用，所以结论成立；但它会随代码增长失效。

---

## 10. 下一步与审核点

按规格，下一步是 **C1**（Python 数值内核 + wheel 发布 + 文件任务入口），关口是「数值单测、入口错误测试、发布后不读开发源」。

建议的审核顺序：

1. 先决定 §9 的五点是否需要改动（尤其第 1、2 点）。
2. 再确认 C1 的范围（是否与 `python/demo_ops` 一并引入 `uv.lock`）。
3. 通过后再开始实施——按仓库准则，实施前需你确认。

**本文件是快照**：C1 开始后，请以代码与最近提交为准，不要把本文当作持续真相。
