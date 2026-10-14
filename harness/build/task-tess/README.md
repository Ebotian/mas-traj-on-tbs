# task-tess — 受限网络条件下的 terminal-bench-science TESS 掩星筛选任务副本（本仓只带"偏离件"）

上游：`harbor-framework/terminal-bench-science`（本实验钉版 `39e4923`）的
`tasks/physical-sciences/astronomy/tess-transit-vetting`。
本目录**不复制**上游任务全集；只带两件我们改过的文件 + 本说明：

- `task.toml` —— 相对上游的偏离：`[environment]` 的 `network_mode="allowlist"` + 17 主机清单
  （见文件内 allowed_hosts；由 `egress/render.py` 从 base.yml + policies/tess-transit-vetting.yml
  生成）、`build_timeout_sec` 900→3000（node/qwen 烘焙层，本机构建时长）；`[verifier]` 保持 `no-network`。
- `environment/Dockerfile` —— 追加偏离（文件内均有注释）：apt 层 `bash git curl ca-certificates
  inotify-tools procps`（git/curl 为编排基底与烘焙取件；inotify-tools+procps 为等待件
  （inotifywait 阻塞读）与存活判定（ps）仪表）+ **node v22.9.0 / @qwen-code/qwen-code 0.25.1
  构建期烘焙**（同 task-microarch / task-restricted）。

## 重建方法

1. 克隆上游 pin，取 `tasks/physical-sciences/astronomy/tess-transit-vetting` 任务目录；
2. 用本目录的 `task.toml` 与 `environment/Dockerfile` **覆盖**同名物；
3. `docker build environment/`（或交由 harbor 构建；构建期 `sha256sum -c` 断言公开包数据）。

上游的 `instruction.md` / `tests/` / `solution/` / `environment/data/` / `environment/vetter/`
一律**取自上游、不随本仓分发**（评分器与答案键刻意不入包）。
