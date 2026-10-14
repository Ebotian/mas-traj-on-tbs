# viz 脚本 —— 轨迹重建数据流(可复用)

## 一键重生成(推荐入口)

    bash viz/scripts/refresh_replays.sh              # 全族(22 个 exp;末尾自动重跑 build_process.py)
    bash viz/scripts/refresh_replays.sh tumor2 w6    # 只重建指定 exp

清单在脚本内(`SRC`/`LABEL` 两个关联数组):exp ← 源路径(可多源)+ 标签(沿用 index)。

## 直接构建单个

    node viz/scripts/build_replay.mjs <source> [<source> ...] --exp <id> --label "<文本>" [--help]

三种 source 形态**自动判定**:

1. **harbor job 目录**(内含 `task-*__*` 实验目录)—— 完整模式:转录 + git 重放 + gate/board/state;
2. **轨迹文件目录**(含 `chats/*.jsonl` 或 `*.jsonl`)—— chats 模式:仅转录;actor 由路径名推导
   (`…/wt-a` → a;`…/wt-b` → b;`…/spike` → s;其余 s);
3. **单个 .jsonl 文件** —— chats 模式(同上)。

输出:`viz/public/replay/<exp>.json`(无损 bundle + `stats`)+ `index.json`(自动增改)。
无损:每行 JSONL 以 raw 原文 + 解析结构双份入档;视图只折叠不删减。

## stats:时间与成本统计(口径与 `walkthrough/tasks/walkthrough/metrics.py` 同源)

- 每 actor:轮数、跨度、每轮时长(中位/p90/最长;全量 `durations_ms` 在 bundle 内)、
  tokens 分布(prompt/cache/uncached/out;`out = candidates + thoughts`)、映射成本。
- 映射(费率卡 2026-10-10):
  - A(deepseek-flash)USD/M:uncached 0.15 · cache 0.003 · out 0.60;峰值(周一至五 01–04/06–10 UTC)×2;
  - B(qwen3.8-flash)CNY/M:uncached 0.8 · cache 0.1 · out 2.7;credits = ¥×200 @k=1(亦 ×144 @k=0.72);
  - 实测有效 k≈0.50(2026-10-12 计费窗标定,spec 同日条目)。
- **对账**:2026-10-12 以 microarch2 复算 — A$ 1.604306 / B¥ 5.1177116 / cr(k1) 1023.5,
  与 metrics.py 表(A$ 1.6043 / B¥ 5.118 / cr 1024)逐位一致。

## 过程观测数据(src/data/process.json)

`python3 scripts/build_process.py` —— 对 `jobs/agent` 全部已采集跑次的**只读**前缀级审计:
截尾账本(「完美停」上限)/ 上下文增长 / 停·收口信号 / gate 决策账本 / 每跑双侧逐步序列。
口径与 metrics.py 同源;exp 名与 replay bundle 对齐(同一批跑的两面)。
`refresh_replays.sh` 末尾自动调用;单独重算亦可。

## 新增一个实验(可复用流程)

1. 从 job 目录或轨迹文件目录收集源;容器内(如 A2A)的 chats 先 `docker cp` 到宿主机固定目录;
2. 在 `refresh_replays.sh` 的 `SRC`/`LABEL` 各增一行;**并在对应视图登记归属**——
   `views/*.tsx` 的 **include 白名单**(fail-closed:未登记的跑不会出现在任何页面),
   同时同步 `build_process.py` 的 `EXP`/`MECH` 映射(exp/label 与 refresh 对齐)与视图内手写计数
   (`main.ts` 的 hint 仍手写,须同批更新;`process.ts` 池总览自 2026-10-13 起为数据驱动,无需再改)。
   归属表:tumor1–3 → `#/tumor`;microarch1–5 → `#/microarch`;交接系(w4–w10 族)+ bump0251 + a2a → `#/handoff`;
3. `bash viz/scripts/refresh_replays.sh <exp>` → **`npm run check:views`**(归属守卫:孤儿/幽灵登记,见下)
   → `npm run probe` → `npm run build` → (按需)chromedriver 截图/ DOM 回读验证(见下)。

## 归属守卫(`npm run check:views`)

`scripts/check_views.mjs` 检查 **index.json ↔ 各 React 视图 include 白名单**的一致性:
- **孤儿**(轨迹在库、任何页面不可达)与**幽灵**(视图登记了、bundle 不存在)→ 退出码 1 并列出;
- 并打印每个视图的当前归属清单,便于人工核对家族正确性(该判断不自动化,归属表见上)。

## 验证方式

- `npm run build`(`tsc --noEmit` + `vite build`);`npm run probe`(8/8;React 视图不在探针内)。
- React 路由(`#/replay`、`#/handoff`、`#/tumor`)用无头 chromium + chromedriver 截图**逐张回读**
  (2026-10-12 StatsPanel 即以此验证;截图 `/tmp/viz-handoff-stats.png`、`/tmp/viz-a2afusion-stats.png`)。
- 截图流程要点:先把 `dist/` 用**确定监听的**静态服务供出
  (`python3 -m http.server 4178 --bind 127.0.0.1 --directory dist`;注意本机 shell 的
  `http_proxy=127.0.0.1:7890` 会让 curl 对 localhost 报 502/000,须 `--noproxy '*'` 校核),
  再经 chromedriver(9515)建会话导航并截图。
