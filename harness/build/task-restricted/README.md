# task-restricted — 受限网络条件下的 terminal-bench-science 任务副本（本仓只带"偏离件"）

上游：`harbor-framework/terminal-bench-science`（本实验钉版 `39e4923`）的 `tumor-immune-interface`。
本目录**不复制**上游任务全集；只带两件我们改过的文件 + 本说明：

- `task.toml` —— 相对上游的偏离：`[environment] network_mode="allowlist"` + 22 主机清单（见文件内
  allowed_hosts）；`[verifier]` 保持 `no-network`。
- `environment/Dockerfile` —— 三处注记偏离（文件内均有注释）：
  1) **git 进第一层 apt**（构建期自带 git，编排用提交/分支/合并做 IaC 底材）；
  2) HF payload 由构建内快照改为 **`COPY payload /root/data` + 原样聚合 digest 断言**
     （构建内取 HF 在本机不可达；payload 由 `data/fetch_payload_curl.sh` 宿主机抓取，
     161 文件，聚合 digest `babbc611…`，构建时断言，替换/残缺载荷会**响亮失败**）；
  3) **curl + node v22.9.0 + @qwen-code/qwen-code 0.25.0 构建期烘焙**（消除每跑 25–79s 的
     网络化装机抖动，配套 `walkthrough/common/dual_agent.py` 的 `command -v qwen` 守卫回退）。
- wheels 为本地闭包 + `--no-index` 安装（8 个钉版包：numpy 2.1.3 / scipy 1.14.1 / pandas 2.2.3 /
  scikit-image 0.24.0 / scikit-learn 1.5.2 / matplotlib 3.9.2 / tifffile 2024.8.30 /
  huggingface-hub 0.26.2）。

## 重建方法

1. 克隆上游 pin，取 `tumor-immune-interface` 任务目录；
2. 用本目录的 `task.toml` 与 `environment/Dockerfile` **覆盖**同名物；
3. 抓 payload 到 `environment/payload/`（`data/fetch_payload_curl.sh`）；
4. 抓 wheels 闭包到 `environment/wheels/`（`pip download` 上述 8 个钉版，python3.12 平台）；
5. `docker build environment/`（或交由 harbor 构建；digest 断言在构建内跑）。

上游的 `instruction.md` / `tests/` / `solution/` 一律**取自上游、不随本仓分发**
（评分器与答案键刻意不入包）。
