# viz 脚本 —— 轨迹重建数据流(可复用)

## 一键重生成(推荐入口)

    bash viz/scripts/refresh_replays.sh              # 全族(20 个 exp)
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

## 新增一个实验(可复用流程)

1. 从 job 目录或轨迹文件目录收集源;容器内(如 A2A)的 chats 先 `docker cp` 到宿主机固定目录;
2. 在 `refresh_replays.sh` 的 `SRC`/`LABEL` 各增一行;
3. `bash viz/scripts/refresh_replays.sh <exp>` → `npm run build` → (按需)探针/截图验证。

## 验证方式

- `npm run build`(`tsc --noEmit` + `vite build`);`npm run probe`(8/8;React 视图不在探针内)。
- React 路由(`#/replay`、`#/handoff`、`#/tumor`)用无头 chromium + chromedriver 截图**逐张回读**
  (2026-10-12 StatsPanel 即以此验证;截图 `/tmp/viz-handoff-stats.png`、`/tmp/viz-a2afusion-stats.png`)。
- 截图流程要点:先把 `dist/` 用**确定监听的**静态服务供出
  (`python3 -m http.server 4178 --bind 127.0.0.1 --directory dist`;注意本机 shell 的
  `http_proxy=127.0.0.1:7890` 会让 curl 对 localhost 报 502/000,须 `--noproxy '*'` 校核),
  再经 chromedriver(9515)建会话导航并截图。
