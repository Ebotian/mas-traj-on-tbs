# harbor-runs —— 实验运行区

> 仓库内登记:`rsi-dev/related_files/2026-10-08-first-measurement-spec.md` §6(接入手册 / §6.5 排练 / §6.6 agent 臂+遥测+受限协议)。
> **复跑唯一入口 = 顶层 `run_agent_arm.sh <job名>`**(引用 `config/` 下各件;指向 `build/task-restricted`、无代理 env)。**模型轴入口(2026-10-10)= `config/run_agent_arm_qwen.sh` / `config/run_agent_arm_qwen_sbb.sh`**(qwen3.8-max;凭据 `config/agent-tokenplan.env`;配置卡 `rsi-dev/related_files/2026-10-10-model-axis-config-card.md`)。
> **harbor 本地补丁(三处;`uv tool upgrade harbor` 全部覆盖,升级后须重打)**:`trial.py`(verifier 覆盖路径 → `config/verifier-build-overlay.yaml`)· `qwen_code.py`(ATIF v1.8)· `node_install.py`(nvm install.sh URL → jsdelivr,配合受限白名单不含 raw.github)。

## 目录

- `run_agent_arm.sh` — 规范 agent 臂模板(qwen-coder · deepseek-flash · effort=max · OTel · hooks 触,全部旗标)
- `config/`
  - `trial-settings.json` — 挂进容器的 settings(`model.reasoningEffort=max` + 18 事件观测 hook)
  - `agent.env`(600)— 凭据(`OPENAI_API_KEY` / `OPENAI_BASE_URL`)
  - `dataset-build-overlay.yaml` — agent 环境构建覆盖(context → `build/dataset-build`)
  - `verifier-build-overlay.yaml` — verifier 环境构建覆盖(经 harbor `trial.py` 本地补丁传递)
  - `run_agent_arm_sbb.sh` — H1 处理臂(规范脚本 + `--ak prompt_template_path`)
  - `search-before-build.prompt.j2` — H1 干预模板 **v2**(2026-10-10 定稿:环境事实先行 + 网关 check/fetch 语义 + 有界搜索/自检 + **停规**;v1 存档 `search-before-build.v1-aa5db681.prompt.j2`;v2 跑 = 新条件)
  - `agent-tokenplan.env`(600)+ `trial-settings-qwen38max.json`(effort=xhigh)+ `run_agent_arm_qwen.sh` / `run_agent_arm_qwen_sbb.sh` — 模型轴(qwen3.8-max,受限)凭据、设置变体与两臂脚本
  - `trial-settings-qwen38flash.json`(effort=xhigh = clamp 后最高档)+ `run_agent_arm_qwen38flash_sbb.sh` — qwen3.8-flash 臂(GATEWAY 条件首用;effort=max 经 rank-clamp 等效 xhigh,映射见 spec §6.6)
  - `temporal-policy` → 已迁至 `egress/policies/`(2026-10-10 分层重组;见下)
  - `check_paths.py` — 路径存在性机械检查(重组/补丁后运行;覆盖 **39 文件** = config 脚本/覆盖 + egress 组件(含 gateway、测试与模板)+ 顶层 run + 三补丁工具文件)
- `egress/` — 网络访问策略组件(分层:`policies/base.yml` 固定层〔模型端点/安装链/镜像〕+ `policies/<task>.yml` 逐题 overlay〔文档面 6 站 + 时间门 candidate;**引擎面 2026-10-10 已禁**〕;`render.py` 合成并生成 task.toml 允许表〔集合语义,默认 check,`--write`〕· `sync.py` 对运行中 sidecar 读差-整表应用〔默认 dry〕· `validate.py` 清单自检 · `rulelib.py` 纯规则 · `tests/` **TDD 规则测试**(任务无关正反测试在父级;任务相关=**正负 pair**(静态/动态两类)于 `tumor_immune_interface/`,与 `task_template/` 除 `fixtures.py` 外**逐字节一致**(`test_task_isomorphism.py` 机械强制;新任务=复制模板只填 fixtures);**类型合法性**(mypy 21 文件 0 问题,`mypy.ini`+`test_type_legality.py`);`python3 -m unittest discover -s egress/tests`;live 需 `GATEWAY_LIVE=1`/`POLICY_TEST_CONTAINER`)· `gateway/` **显式网关 v1**(github + **nature**〔日期=Crossref,内容 check-only〕;**forbidden 独立否决**已入裁决〔指定答案链接即使日期合格亦拒〕;`run.sh`;**2026-10-10 已激活**);设计稿 §7–§8)
- `data/`
  - `fetch_payload_curl.sh` — 载荷抓取器(curl 续传 + HF/hf-mirror 双线路)
  - `payload_manifest.tsv` — 161 文件清单
  - `legacy/` — 历史版本(`fetch_payload.py`、`proxy-build-overlay.yaml`)
- `build/dataset-build/` — 构建输入:`Dockerfile`(agent)· `Dockerfile.verifier` · `payload/`(376 MB,聚合摘要已双验)· `verifier-files/`
- `build/task-restricted/` — 受限任务副本(IaC:原文 `task.toml` + `network_mode="allowlist"` + **23 主机白名单**(2026-10-10 加 Token Plan 模型端点 `token-plan.cn-beijing.maas.aliyuncs.com`;原 22 条含 `api.deepseek.com`);verifier 仍 `no-network`;原始任务与下游副本不动)
- `jobs/` — 运行产物:`agent/`(agent-flash-1、agent-flash-1-sbb、冒烟轮)· `oracle/`(oracle-tii … tii6)
- `logs/` — 各轮运行日志 + atif-lens 日志
- `pricing/` — Φ_θ 成本映射:`fetch_rate_card.py`(官方定价页 → sha256 钉版费率卡)· `price_trajectory.py`(TOU 计价:O(1) 快路径 + 逐步核验)· `rate-card-2026-10-10.json` · `reports/`

## 2026-10-10 重组

仅移动与路径字符串同步;**所有数据、配置值与脚本逻辑未改**。映射:

| 旧 | 新 |
|---|---|
| `dataset-build-overlay.yaml` / `verifier-build-overlay.yaml` / `trial-settings.json` / `agent.env` | `config/` |
| `fetch_payload_curl.sh` / `payload_manifest.tsv` | `data/` |
| `fetch_payload.py` / `proxy-build-overlay.yaml` | `data/legacy/` |
| `dataset-build/` | `build/dataset-build/` |
| `jobs-agent/` / `jobs-oracle-tii/` | `jobs/agent/` / `jobs/oracle/` |
| `*.log`(14 个) | `logs/` |

**补记(2026-10-10 当日)**:同步曾**遗漏被补丁的工具文件**(harbor `trial.py` 内硬编码的 overlay 路径)→ 下一轮真跑(H1 处理臂)的判分环境创建失败(`FileNotFoundError`),已修复为 `config/` 路径并新增 `check_paths.py` 机械检查;**今后任何重组/补丁移动必须把补丁清单本身一并同步**。同日受限协议落地:`node_install.py` 成**第三补丁**(install.sh → jsdelivr,配合白名单移除 raw.github),`check_paths.py` 覆盖随之扩至 9 文件(新增顶层 run 脚本、`*.yml`、第三补丁文件)。
