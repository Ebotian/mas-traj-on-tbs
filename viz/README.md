# viz/ · 构想结构可视化

对 `related_files/` 语料 + `a0/` 测量链 + 一条 ChatGPT 对话的**系统化可视化**。
七个视图,TypeScript + Vite,无运行时依赖(图表是手写的 SVG,不是图表库)。

```
pnpm install
pnpm dev        # http://localhost:5178
pnpm build      # tsc --noEmit && vite build
pnpm preview    # http://localhost:4178  (服务 dist/)
pnpm derive     # 重新派生 src/data/experiments.json
```

## 七个视图

| 路由 | 内容 |
|---|---|
| `#/overview` | G₀、收窄倍率(1/4 能力、1/6 资源、1/8 实验行、0/8 campaign)、epistemic debt 正反馈环、四能力、Taste⇄SOP⇄IaC、九条原则 |
| `#/map` | 50 节点 / 67 边的分层力导图。纵向 = 抽象层;形状+颜色 = 节点类别;描边虚实 = 证据等级;8 种线型 = 关系类别 |
| `#/numbers` | 五组实测数据的真图表:exp1(CSV vs β-二项)、Pasted md 的偏离(σ)、exp2、exp3、a0/ 强度曲线与成本曲线 |
| `#/time` | 09-09 → 10-06 时间轴,五条来源轨道;四次转向与文档写下它的时间差 |
| `#/conflicts` | 冲突登记(两侧原文并排)+ 反转登记(was/now 表) |
| `#/decisions` | 25 项决策,按阻塞关系排;含「这次梳理本身可能是代理目标漂移」的自我攻击 |
| `#/coverage` | 我自己的阅读覆盖率:逐文件行数与已读行数,三档折扣 |

## 数据从哪来(以及哪些是我的推断)

- `src/data/experiments.json` —— 由 `scripts/derive_experiments.py` 从
  `related_files/agent_engineering_science_repro_bundle.zip` 派生,**检查入库**。
  zip 未被 git 跟踪(语料白名单排除 `.zip`),所以这份 JSON 是 D 线实测数据在 git 里唯一的副本。
  派生时额外计算了可交换 β-二项的精确多数票概率(审查构造的反例模型)、标准误与 z 距离。
- `src/data/graph.ts` —— 从 `related_files/synthesis_2026-09-30.html`(2026-09-30)机械移植:
  脚本 eval 出其中的 N/E/ET 字面量再发射成 TS,所以两者不会因手抄而漂移。
- `src/data/coverage.ts` —— 2026-10-06 在 HEAD `ccae0deb` 上实测:`git ls-files` + 逐文件行数。
  `linesRead` 是我自己的诚实记账(逐行读完 / 只读某几节 / 二手 / 没读)。
  `transcript.md` 的 61500 行记为 0:我生成并检索过它,没有逐行读。
- `src/data/a0.ts`、`src/data/corpus.ts` —— 从被引文件逐条誊录,每条带 `path:line`。

**标为【推断】的内容不来自任何文档**,目前有三处:
1. `#/overview` 的「八行实验矩阵 × 四能力」映射。八行出自 `agent_engineering_science_report.tex`,
   四能力出自 `research_state_control_review_v4.tex:1250-1263`,没有任何源把两者连起来。
2. `#/conflicts` 里 exp3 的假绿判定(我没读 `report.tex` 的实验 C 正文)。
3. `#/time` 里部分事件的轨道归属(输入 vs 对话产物)依据是载荷里有无写入操作,
   而写入操作的判定对相对路径写入不可见,所以「7 写 / 25 只读」是下界。

## 验证方式(不是「看起来对」)

- `tsc --noEmit` 在 TS 7.0.2 下 0 错误(strict)。
- `vite build` 0 警告。
- 无头 chromium 对七个路由各截一张图,**逐张目视**;并解析 `#/map` 的 DOM,
  按「CJK ≈10.5px / ASCII ≈6.0px @10.5pt」估算标签包围盒,**50 个标签 0 重叠**,x 铺满 80–1113 / 1180。
- 调色板经 dataviz 校验器:6 色方案在色盲模拟下多组可混,故降为 3 彩色 + 1 中性;
  颜色从不单独承载信息(形状、直接标签、线型、描边虚实各自独立编码一个维度)。

## 已知的视觉折中

- 结构图标签截断到 12 字符,完整标题在悬浮 `<title>` 与右侧详情面板里。
- 图表固定 640×300(应力图 1180×940),窄容器下等比缩小。
- 未做拖拽:布局是确定性的(固定种子),刷新不变,便于引用截图。
