# mas-traj-on-tbs

在 terminal-bench-science 上的双 agent 协作研究：测量链、记录册与**无损轨迹回放**。
Dual-agent research on terminal-bench-science: measurement chain, registers, and lossless trajectory replay.

## 仓库里有什么

| 路径 | 内容 |
|---|---|
| `viz/` | 交互可视化（Vite + TypeScript；12 个视图）。三条轨迹页：`#/replay`（w4/w5 走查）、`#/handoff`（走查全族 13 包）、`#/tumor`（tumor-1 双 agent，422 轮 / 430 调用 / 28 提交） |
| `viz/public/replay/` | 15 个轨迹 bundle：会话转录逐行 **raw + 解析**双份、git 从采集 bundle 现场重放、gate/board 账原样收编；折叠只改显示 |
| `a0/` | 测量链与记录：容器/计时实验、conformance、报告与证据（体量大，脚本与证据兼有） |
| `related_files/` | 语料与文档：研究综述（state control v1–v4）、工程规格、外部审阅往来、会话转录（仅文本；第三方论文 PDF 不入库） |
| `local2gpt/` | 与外部 web 席位往来的打包/发送工具（`out/` 与 tar 产物不入库） |

## 快速看

```bash
cd viz
npm install
npm run dev        # 打开 #/tumor、#/handoff、#/replay
npm run probe      # 8 视图渲染探针
```

轨迹 bundle 再生成（job 目录在库外）：

```bash
node viz/scripts/build_replay.mjs <job-dir> --exp <id> --label "…"
```

## 许可

- **代码**（`viz/`、`local2gpt/`、`a0/` 下脚本）：Apache-2.0 —— 见 `LICENSE`
- **文档、语料与轨迹数据**（`related_files/`、`viz/public/replay/`、报告与记录）：CC BY 4.0 —— 见 `LICENSE-docs`
- 署名：*mas-traj-on-tbs*，Ebotian，2026
- 第三方引用段落不因本许可改变归属（见 `NOTICE`）。轨迹包为自有实验转录，含 agent 提示词与原始事件行。

## 基准与上游（第三方，不随本库发布）

- 实验任务：**terminal-bench-science**（`harbor-framework/terminal-bench-science`，本地钉版 `39e4923`）的 `tumor-immune-interface` 任务；`#/tumor` 的 tumor-1 即该任务上的双 agent 运行记录。
- 运行框架：**harbor**（`harbor-framework/harbor`，原 `laude-institute/harbor`）。
- 上游基准与框架按各自许可分发、**不包含在本库中**；本库的 Apache-2.0 / CC BY 4.0 不覆盖它们（受限网络任务副本、评分器与题目数据均来自上游）。

## 备注

- 库内路径含作者机器路径（`/home/ebt/…`）；实验记录按原文保留，不做改写。
