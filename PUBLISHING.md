# 发表准备：敏感信息审计 / 许可 / 公开仓库清单（2026-10-11）

状态：**审计完成、技术项就绪；三项内容决策待你裁定**（见 §4）。按既定规则，本仓库无远端、
未推送；建仓与 push 需你的明确批准。

## 1 · 敏感信息审计（决定性检查，非抽样）

方法：从两个密钥源（`~/gptapi.md`、`harbor-runs/walkthrough/walkthrough.env`）提取 7 个
密钥形态 token（≥24 字符、含数字与字母），对**当前全部 37,557 个跟踪文件**与**全部历史**
（27,733 个 blob，`git rev-list --objects --all` 全量 `cat-file --batch` 搜索）做子串检验；
报告只记命中数与路径，不回显 token。

- **密钥泄漏：零命中**——当前文件与全部历史都没有任何 key token。`Authorization`/`Bearer`
  串在 15 个 replay bundle（含全量对话转录与设置）中亦零命中。
- **凭据文件名扫描**（*.env/secret/key/pem 等）：无非预期命中；`secrets` 命中均为
  `secrets.token_urlsafe` 之类代码用词。
- **身份信息**：邮箱命中全部为样板/本地域（`qwen-coder@alibabacloud.com` 82 次、
  `noreply@anthropic.com` 38 次、`worker@loreley.local`、`t@t.local` 等）；
  `Ebotian`／真名／电话零命中。
- **`~/gptapi.md` 路径提及（已评审，建议保留）**：107 个文件 204 处——全部是"运行时从该文件
  读 key"的实验命令记录（key 值本身从不在库内）。它是路径不是机密；改它会篡改实验记录原文，
  **建议原样保留并在本文件留档**。
- **二进制面**：`related_files` 采用文本白名单（PDF/克隆目录默认排除）；`node_modules/`、
  `dist/`、`.qwen/tmp/`（含会话解码材料）、`local2gpt/out/` 均已 ignore，已逐一核过。

## 2 · 发布面构成（会被公开的东西）

- 37,557 个跟踪文件 / 244 个提交；`.git` 打包 43MB（体量主要来自 viz 的 15 个轨迹 bundle
  共 67MB 中的文本）。
- `related_files/` 跟踪 83 个文本文件：你自己的文档（research_state_control v1–v4、报告与
  规格）、你的 ChatGPT 会话转录（3 个 conversation 目录）、web 审阅回复（gpt-review-*）。
  **第三方论文本体（PDF）没有入库**——白名单排除；被引处为文内引用。
- `viz/public/replay/*.json`：13 个走查 + tumor-1 的**完整对话转录**（含协议提示词、
  gate/board 账、raw 逐行）。这是"结果本体"，建议连同发布。
- `a0/`：测量链的脚本与证据（含上面说的 key 路径提及）。

## 3 · 许可（建议，待你拍板）

仓库是"代码 + 文档/语料"混合体，两类激进的差异值得分开：

| 方案 | 适用 | 效果 |
|---|---|---|
| **A（推荐）双证** | 代码（viz/、local2gpt/、a0 工具）= **Apache-2.0**；文档/语料（related_files/、spec、报告）= **CC BY 4.0** | 专利授权 + 署名即可引用；符合研究仓库惯例 |
| B 单证 | 全仓 **Apache-2.0** | 最省事；文档也被附加专利条款（无碍但少见于文档） |
| C 单证 | 全仓 **MIT** | 最短最自由；无显式专利授权 |

任何方案都需附 NOTICE 章：**引用自第三方论文/页面的片段仍归其原作者**，本许可不覆盖它们。
落盘物：`LICENSE`（代码）＋ `LICENSE-docs`（如选 A）＋ 根 `README.md`（待拟）。

## 4 · 决策记录（2026-10-11，用户裁定）

1. **许可 = A（双证）**：代码 Apache-2.0 + 文档/语料 CC BY 4.0。落盘由生成器产出：
   `LICENSE` 取自 GitHub license API（apache-2.0 正文，11,358B）；`LICENSE-docs` 取自 SPDX
   canonical（CC-BY-4.0，17,022B）；`NOTICE` 记署名与第三方边界。
2. **内容范围 = 全部包括**（含三个会话转录与 13+2 个 replay 全量 bundle）。
3. **仓库 = `Ebotian/mas-traj-on-tbs`，public**（用户在应答本清单时指定）。

## 5 · 清单

- [x] `LICENSE` / `LICENSE-docs` / `NOTICE` / 根 `README.md` 落盘
- [x] 密钥审计（当前+全史）与内容范围复核
- [x] 建仓与推送授权：用户应答本清单时给出仓库名与可见性（2026-10-11），据此执行
      `gh repo create Ebotian/mas-traj-on-tbs --public` + `git push -u origin main`
- [x] **已公开**：https://github.com/Ebotian/mas-traj-on-tbs （2026-10-11）。首推遭遇本机对 github
      的大上传断连（TLS reset / rpc post data），本地 git 配置 `http.postBuffer=512M` +
      `http.version=HTTP/1.1` + lowSpeed 阈值后一次通过；该配置已持久化于本仓 `.git/config`。
- [x] 仓库 About 已按最终形态设置（2026-10-11）：描述含"完整套件+复现"与双许可；topics =
      llm-agents / multi-agent / agent-evaluation / terminal-bench-science / trajectory-replay / agent-harness。
- [x] 2026-10-11 追加：**完整实验套件入仓 `harness/`**（与运行根同构、路径位置推导；大 payload/wheels
      只给取回方法与构建期 digest 断言；复现文档 `harness/REPRODUCE.md`；任务偏离件+notes 在
      `harness/build/task-restricted/`；评分器与答案键刻意不入包）。
- [x] 2026-10-13 补推：此前仅存于本地、从未推送的两处引用已推送 origin —— 注解 tag `a0-audited`
      （2026-09-20，指向已在远程历史内的提交）与 `refs/notes/ai-attribution`（9 条逐提交 AI 归属
      统计 note）。main 本已最新（push 回 Everything up-to-date）；推送前已核：两引用的
      tagger/committer 与公开历史（272 条提交）同一身份、无新增暴露，notes 内容扫描 0 敏感命中。
- [x] 2026-10-13 追加：harbor-runs 运行区其余装置补齐入仓 `harness/`（161 文件）——refs 证据（canary
      验证 / traj-stats-v2 复核 / 早停审计 / EarlyEval）、config 臂件与模板（prompt v2+v1 存档、
      trial-settings 变体、覆盖件、`check_paths.py`）、`egress/` 分层策略组件、`pricing/`、A2A 与
      hook-wall 探针证据、`e1-probe/`、根 `README.md` 与 `run_agent_arm.sh`、`data/legacy/`。排除照旧
      （`*.env` 密钥、venv、第三方 checkout、otel 遥测、缓存），`.gitignore` 增防漏规则。8 件暂缓、
      本地保留、2026-10-13 已裁（保持排除、本地持有，见下条）：`e1-probe/oai-log/` 3 件（本机记忆库
      内容）与含 A2A 测试密钥字面量的 5 件（`a2a-spike-2/3.sh`、`fusion/share-to-a/b.json`、`workspace.json`）。
- [x] 2026-10-13 裁定：上款 8 件**保持排除、本地持有**（用户选 a——不进公开仓；不采纳脱敏折算）。
      拦截层不变（本地 `.git/info/exclude` 6 行，私人文件不在仓内）；行前复核：HEAD 与索引零命中，
      两脚本各 1 条 43 字符 SECRET 字面量、share 凭据 expiresAt 2026-10-19、workspace.json 3×64-hex、
      `oai-log/` 3 件含本机记忆库内容。此后除非另行提出，清单与现状不再变动。
