# 复现方法（完整实验套件）

本目录 = 带完整实验套件的 harbor-runs 根**同构**布局（脚本全部按位置推导路径，可整体搬迁）。
大件不入包：payload（376MB）与 wheels（122MB）只给**取回脚本 + 清单 + 构建期 digest 断言**；
job 产物、密钥、评分器与答案键均不入库。

## 构成

| 路径 | 内容 |
|---|---|
| `walkthrough/common/` | 任务无关层：通用启动器 `launch.sh`（含"正常退出→清当次镜像"策略）、agent 适配器 `dual_agent.py`、门禁 `gate.py`、等待件 `wait_*.sh`、轨迹索引/读取 `traj_index.py`/`traj.py`、引用账本 `refs.py`、TDD 套件与夹具（布局细节见 `walkthrough/README.md`） |
| `walkthrough/tasks/walkthrough/` | 走查排练任务：`run.sh` 容器内包装、提示词（v2 `prompt.md` + v1 存档 + N/R 变体）、`agent.py`、单臂 4 并发 `wave.sh`、全链编排 `exp42.sh`、指标 `metrics.py`、保真核验 `check_manipulation.py`、实验记录 `EXPERIMENT-w6-4x2.md` |
| `walkthrough/tasks/tumor/` | 真实任务包装：`instruction.md` + `protocol-tumor.md`、`run.sh`、`monitor_tumor.sh` |
| `walkthrough/tasks/microarch/` | 电学任务包装（`microarch-modeling`）：`run.sh`、`protocol.md`、`agent.py`、薄 `launch.sh`；提示词 = 上游 instruction（去 canary 副本）+ 协议 |
| `walkthrough/verify/` | 验收脚本（NORMAL/ACCEPTED 判据） |
| `build/task-restricted/` | 任务偏离件（`task.toml` + `environment/Dockerfile`），见其 README |
| `build/task-microarch/` | 电学任务偏离件（`task.toml` + `environment/Dockerfile`），见其 README；traces（320MB）不入包，用上游 `fetch_traces.py` 取回 |
| `data/` | payload 抓取脚本 + 161 文件清单（名称+字节数） |

## 依赖

- **harbor**（`harbor-framework/harbor`）——本实验用 uv tool 安装；注意两处**本地已知偏离**见下。
- **terminal-bench-science** 钉版 `39e4923`（任务 `tumor-immune-interface`）。
- docker / node / python3。

## 步骤

1. 上游任务目录就位，用 `build/task-restricted/`（肿瘤）与 `build/task-microarch/`（电学）各两文件覆盖（电学另需先取回 traces，见其 README）；
2. 取大件（不入包）：
   - payload：`bash data/fetch_payload_curl.sh`（写到 `build/task-restricted/environment/payload/`；
     双路由 huggingface.co / hf-mirror.com 交替重试、断点续传；本机默认走本地代理 7890，
     `export PROXY=` 可置空直连）；
   - wheels：`pip download -d build/task-restricted/environment/wheels \
     numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 scikit-image==0.24.0 scikit-learn==1.5.2 \
     matplotlib==3.9.2 tifffile==2024.8.30 huggingface-hub==0.26.2`；
3. 密钥：`cp walkthrough/walkthrough.env.example walkthrough/walkthrough.env`，填 A/B 两组
   （A=deepseek 侧、B=Token Plan 侧；`OPENAI_*` 为兼容名）；
4. 空目录：`mkdir -p jobs/agent logs`；
5. 冒烟：先用 harbor `--install-only` 跑一次（零模型费用；预期 env≈4s + 安装≈0.1s——烘焙生效），
   再跑整轮：
   `bash walkthrough/tasks/walkthrough/launch.sh repro-1`（约 20 分钟/轮）；
   肿瘤任务同法：`bash walkthrough/run_tumor_launch.sh repro-tumor`（默认 0.5×轨）；
6. 4×2 编排：变体经 `EXTRA_AE="WT_PROMPT=prompt-w6n.md"`（或 `prompt-w6r.md`）注入；
   全链（含 token-plan 积分表读数，需相应桥）`bash walkthrough/tasks/walkthrough/exp42.sh`；
7. 指标与保真：`python3 walkthrough/tasks/walkthrough/metrics.py <job>…`、
   `python3 walkthrough/tasks/walkthrough/check_manipulation.py <job>…`；
8. 回放：`cd ../viz && npm install && npm run dev`（`#/handoff`、`#/tumor`），
   或 `node viz/scripts/build_replay.mjs <job-dir> --exp <id> --label "…"` 生成新 bundle。

## 已知偏离（复现须知情）

- **harbor 本地补丁**：verifier 独立环境不携带 compose overlay（上游缺口；本机以 `trial.py` 补丁
  **仅对 `task-restricted`** 透传 `verifier-build-overlay.yaml`，备份 `.orig` 同置；2026-10-12 修——
  此前无条件透传曾把 tumor 包叠进 microarch 的 verifier 镜像、错跑 tumor 判分器，已按任务路径门控并冒烟复核）。
  上游修复前需自行打补丁或等价处理。
- **env Dockerfile 三处偏离**：见 `build/task-restricted/README.md`（git / payload COPY / node&qwen 烘焙）。
- **本机网络特性**：大传输易断——payload 脚本已内建重试；git 推送 github.com 需要的
  `http.postBuffer/HTTP1.1` 修法见仓库根 `PUBLISHING.md`。
- **夹具**：`walkthrough/common/fixtures/dual-{a,b}.jsonl`（8MB，真实双 agent 转录）随包，
  让 traj/refs/gate 三套测试离线自足；它们同时是已发布轨迹 bundle 的原始素材。
- **验收脚本的判据**以本包内的 `verify/` 与 `walkthrough/tasks/*/run.sh` 的 NORMAL 定义为准；
  实验结论与口径见 `walkthrough/tasks/walkthrough/EXPERIMENT-w6-4x2.md` 与仓库根 `PUBLISHING.md`。
