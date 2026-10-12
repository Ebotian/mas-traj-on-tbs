# A2A 融合设计(2026-10-12)

已获批:「将A2A基建引入,但保留原有机制设计」。本文 = **完整融合设计 + 已验证接线与实测证据**(同日 spike + 双 daemon 接线 + 融合轮演示)。

## 0. 设计目的(逐项,均已实测)

| # | 目的 | 状态 | 证据 |
|---|---|---|---|
| 1 | A2A 基建引入并可驱动 | ✓ | 单 daemon spike 五检全过;双 daemon 接线 A→B/B→A 各 COMPLETED |
| 2 | 保留原有机制(工件/审计/屏障) | ✓ | 融合轮工件照走 git(wt-a/wt-b 各 3 提交)+ `refs-a2a.jsonl` 台账;gate/seal/wait/board 未改动 |
| 3 | 对称 peer(互发 grant,无 leader) | ✓ | `share-to-a`(A daemon 签发)/`share-to-b`(B daemon 签发),两侧 shell 各持对端凭据 |
| 4 | 异族模型 | ✓ | daemon-A=qwen/deepseek-flash@4170、daemon-B=qwen3.8-flash@4171,各自 env 凭据 |
| 5 | 等待原语 = 任务状态轮询 | ✓ | WORKING→COMPLETED 状态机;超时/失败/重试语义实测 |
| 6 | 无人值守 | ✓ | 默认审批模式无卡滞;AUTO 下工具可直接执行 |
| 7 | 恢复语义 | ✓ | 重启后 grant/任务/会话记忆存活;在飞轮→显式 FAILED("interrupted by a daemon restart; retry"),重试 12s 完成 |

## 1. 拓扑(已验证)

- 每侧一个 `qwen serve --no-web`(同容器、loopback 可信模式;folderTrust 关闭):
  daemon-A: port 4170,workspace `/root/wt-a`,env=A 侧凭据,agent `peer-a`(model deepseek-flash);
  daemon-B: port 4171,workspace `/root/wt-b`,env=B 侧凭据,agent `peer-b`(model qwen3.8-flash)。
- 互发 grant:`POST /workspaces/<ws>/agent/agents/<id>/shares`(secret 仅签发时返回一次);
  `share-to-b` 交 A 侧 shell、`share-to-a` 交 B 侧 shell(600 文件,不进 chats/collect)。
- 客户端:`walkthrough/common/a2a/a2a_client.py`(submit/wait/send-wait;退出码 0=完成、3=失败可重试、4=超时)。

## 2. 轮次协议(融合后)

- 发起:`a2a_client.py --share <对端share> send-wait "<评审请求+工件文本>" --context <轮上下文> --out rounds/rXX-task.json`
- 等待:GetTask 轮询(=等待原语);默认窗 600s;**FAILED → 同 context 重发(自动重试一次)**;二次失败按 ABNORMAL 规则保证据不自动再跑
- 落盘:发起侧写 `rounds/rXX-request.json` + `rXX-answer.json` + `refs-a2a.jsonl`(sha256_16)+ git 提交;
  应答侧写自家记录 + 提交。**append-only**:重试另起 attempt 条目(不可改写首条)
- 记忆:`contextId` = 对端 native session;跨 daemon 重启存活(实测),同一 context 跨轮复用

## 3. 与既有机制的分界(保留面)

A2A **只**承接轮次级请求/应答。工件、审计、密封、就绪屏障全部留在原层:
git 轮次分支/合并、refs 台账(sha/引文)、gate 预提交门、密封快照、`wait_peer/wait_pos`、board(pull 契约)。
双侧 daemon 与既有 `-p` 会话并存不冲突(不同进程、不同通道)。

## 4. 集成(进入正式实验的接法)

- helper 挂载:`common/a2a/` 由 run.sh 启动阶段拷贝到容器内稳定路径(如 `/root/a2a/`),两侧 shell 用绝对路径调用
- 引导:run.sh 起双侧 daemon(各自 env/模型/workspace)→ 建 agent → 互发 share 写 600 文件
- P2/P3:"评审交递"由纯 board 升级为 `send-wait` 取回 answer → 本地 `rounds/` + git;board/wait 保留用于屏障与对端活跃
- 重试:封装自动一次;二次失败保留证据按 ABNORMAL
- 清理:每跑新 grant;跑后 revoke + 清 share 文件

## 5. 注意与限制(实测)

- 单轮偶发 >120s(一次,已用重试解决);**轮询窗与重试为必备**
- folderTrust 开启则协作面不挂载(见项目记忆 `a2a-workspace-agents-in-container`)
- 在飞轮遇 daemon 重启 → FAILED(不静默丢);任务查询/记忆/grant 重启存活
- 同容器同 HOME:注册表/会话/roster 在 `~/.qwen/tmp/<projectHash>/agent-host/`
- 仅 loopback;share = 一次性明文 secret(600 文件、不进采集)

## 6. 证据索引

- 任务:A→B `sr_291a1c50`("B-ON-QWEN38");B→A `sr_f6779356`("A-ON-DEEPSEEK");r02 `sr_fdfadbee`(COMPLETED);
  r01 尝试1 `sr_8e794759`(被重启中断→FAILED)→ 尝试2 `sr_cc770692`(**12s COMPLETED**,sha16 `b17a1586c82a0764`)
- git:wt-a `6d6ed58`/`a88c446`/`4f2e460`;wt-b `0e3dfd0`/`304e59b`/`34282e3`
- 证据目录:`harbor-runs/spike-evidence/`(spike 13 件)+ `spike-evidence/fusion/`(任务 JSON×6、serve 日志×4、rounds×2、share×2、agents.json×3)
- 脚本:`harbor-runs/a2a-{spike,spike-2,spike-3,fusion-setup,fusion-round,fusion-retry}.sh`;客户端 `walkthrough/common/a2a/a2a_client.py`(发布副本同步)
