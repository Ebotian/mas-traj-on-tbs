# task-microarch — 受限网络条件下的 terminal-bench-science 电学任务副本（本仓只带"偏离件"）

上游：`harbor-framework/terminal-bench-science`（本实验钉版 `39e4923`）的
`tasks/engineering-sciences/electrical-engineering/microarch-modeling`。
本目录**不复制**上游任务全集；只带两件我们改过的文件 + 本说明：

- `task.toml` —— 相对上游的偏离：`[environment]` 的 `network_mode="allowlist"` + 17 主机清单
  （见文件内 allowed_hosts；由 `egress/render.py` 从 base.yml + policies/microarch-modeling.yml
  生成）、`build_timeout_sec` 900→3000（烘焙 + trace 层，本机构建时长）；`[verifier]` 保持 `no-network`。
- `environment/Dockerfile` —— 三处注记偏离（文件内均有注释）：
  1) apt 层 `bash` → `bash git curl ca-certificates inotify-tools procps`——git/curl 为编排基底与
     烘焙/取件；inotify-tools+procps 为等待件（inotifywait 阻塞读）与存活判定（ps）仪表
     （slim 基座两者皆缺，2026-10-12 补，与 task-restricted 对齐）；
  2) **curl + node v22.9.0 + @qwen-code/qwen-code 0.25.1 构建期烘焙**（同 task-restricted；
     配套 `walkthrough/common/dual_agent.py` 的 `command -v qwen` 守卫回退）；
  3) traces 由构建内取回改为 **宿主机预取 `COPY traces /root/data/traces` + 上游 `fetch_traces.py`
     构建期纯 digest 断言**（构建内自 Zenodo 取件在本机不可靠）。

## 重建方法

1. 克隆上游 pin，取 `tasks/engineering-sciences/electrical-engineering/microarch-modeling` 任务目录；
2. 用本目录的 `task.toml` 与 `environment/Dockerfile` **覆盖**同名物；
3. 取 traces（4 件、320MB，不入包）：`python3 environment/fetch_traces.py environment/traces`
   （上游脚本；Zenodo record 10960004，逐件 sha256 断言、断点重试）；
4. `docker build environment/`（或交由 harbor 构建；digest 断言在构建内跑）。

上游的 `instruction.md` / `tests/` / `solution/` / `data/` / `starter/` 一律**取自上游、不随本仓分发**
（评分器与答案键刻意不入包）。
