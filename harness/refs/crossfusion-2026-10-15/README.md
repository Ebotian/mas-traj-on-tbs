# crossfusion-2026-10-15 — 并集轨迹机械统计(数据并集 × 方法并集)

把「我方 54 侧 + 8 臂」与外部 **AutoResearchEval**(PrentisAI, HuggingFace)的 800 条真实轨迹
取 **数据并集**,用**覆盖全部数据的统一机械统计**逐单元计算(零 LLM、确定性、逐字节可复现),
并机械复算论文(arXiv 2608.14905v3)与数据卡中全部可机核数字。

**总规模:862 单元 · 83,032 次工具调用**(ours 9,190 / are 73,842)。

## 数据并集

| source | corpus | units | calls | masked | gaps 可算 | 说明 |
|---|---|---:|---:|---:|---:|---|
| ours | 54 侧(4 族) | 54 | 8,462 | 163 | 54/54 | = traj-features-2026-10-14 同一作业目录 |
| ours | 8 臂(ATIF) | 8 | 728 | 26 | 8/8 | 臂掩蔽 26 与 lab 不变式一致 |
| are | open-ended | 560 | 29,041 | 606 | 420/560 | 70 任务 × 8 模型 |
| are | optimization | 240 | 44,801 | 625 | 205/240 | 30 任务 × 8 模型 |
| are | 合计 | 800 | 73,842 | 1,231 | 625/800 | 均 92.3025 调用/跑 |

- **are 钉版**:`PrentisAI/AutoResearchEval` @ revision `412fb4908a3a7b98dd50cfa3e5c6cd40750d2d4f`,
  809 文件 / 721,929,474 B(与 HF 列表逐文件核对,0 坏);暂存 `/home/ebt/harbor-runs/data/autoresearch-eval`,
  重取用 `fetch_are.py`(断点续传 + 重试 + 尺寸校验)。数据集为 CC-BY-4.0;**数据本体不入本仓**,
  本仓只入派生统计与复算结果。
- **ours**:`harness/refs/traj-features-2026-10-14`(同源作业目录:`/home/ebt/harbor-runs/jobs/agent/*`)。
- **论文钉版**:arXiv `2608.14905v3`(`local2gpt/check_citations.py` 复核:多版本标题一致、无 revision/retraction 旗标);
  表格文本由 `parse_paper_tables.py` 自 LaTeXML `paper.html` 提取(sha256 钉于 `paper_tables.json`)。

## 方法并集(每个方法覆盖每个单元)

7 种日志格式全部过同一套统计;该格式不可得的字段记 `null` 并在格式矩阵中注明,不做插补。

| 统计量 | 定义(实现即定义) | 覆盖 |
|---|---|---|
| calls_total / calls_by_name | 工具调用与名表 | 862/862 |
| kinds(8 类)| 读/写/检索/执行/等待/测试/恢复/其它;`run_shell` 类按命令文本细分(wait/recover/test 规则) | 862/862 |
| kind_entropy | 非首调用(c₂..cₙ)类别边际熵 `H=-Σp log₂p`(bit) | 854/862(0 或 1 调用的 8 个单元无 c₂..cₙ,记 null) |
| transition_entropy | 条件转移熵 `H_tr=-Σ_a π̂_a Σ_b P̂_ab ln P̂_ab`(文档 §4.2;8 类,Dirichlet α=1,π̂ 为经验边际;nat) | 同上 |
| gaps | 相邻时间戳间隔:中位 / CV_robust=1.4826·MAD/中位 / P600=间隔>600s 占比;basis ∈ call_ts/result_ts/step_ts | ours 62/62;are 625/800(其余格式无时间戳,记 null) |
| masked | 工具成功 ∧ 输出含 `Traceback`(静默失败);rate=masked/results_judged | 全 7 格式 799/800(1 个 0 行文件除外) |
| cache_ratio | cached/(input+cache_read+cache_creation)(终态 usage) | ours 62;are gemini_ndjson 27;其余格式无 usage 字段 |
| out_tokens / span / duration_ms | 输出 token、首末时间戳跨度、result 行时长 | 按字段可得性(见 summary.md 格式覆盖表) |

逐格式覆盖(实测,详见 `summary.md`):

| format | units | gaps(basis) | masked 可判 | cache | duration |
|---|---:|---|---:|---:|---:|
| are/claude_stream | 600 | result_ts 420 + call_ts 175 | 595 | 0 | 592 |
| are/gemini_ndjson | 30 | call_ts 30 | 30 | 27 | 27 |
| are/gemini_text | 69 | — | 69 | 0 | 0 |
| are/codex_text | 70 | — | 70 | 0 | 0 |
| are/codex_items | 30 | — | 30 | 0 | 0 |
| ours/qwen_chat(54 侧) | 54 | call_ts 54 | 54 | 54 | — |
| ours/atif(8 臂) | 8 | step_ts 8 | 8 | 8 | — |

## 口径决定(全部可审计,`audit.json` 对照)

1. **ours 侧严格沿用 lab 口径**:名字表逐名对齐 `traj-features-2026-10-14/extract.py` 的
   `NAME_KIND`(8 名 + `run_shell_command` 文本细分);表外名(`edit_file`×3、`tool_call`×3、
   `bash`、`edit_file_path`、`shell_command`,合计 9 次)按 lab 惯例归 `other`。
   ⇒ 54/54 单元 × 13 字段与 lab 逐字段相等(`check.py` 独立对读)。
2. **ours 臂**无 lab 对照,表外名按最贴近类归口(`edit_file→write`、`run_shell→SHELL` 等)。
3. **工件名 2 处**(claude 流,均 qwen3.7-max 开题集):`tool_use` 输入未解析
   (`__unparsedToolInput`)⇒ 无从按 args 细分,归 `other`,实例记 `audit.defect_occurrences`。
4. **模型名归并**:optimization 目录 `sonnet-5` / `codex-gpt5mini` → `claude-sonnet-5` / `gpt-5-mini`
   (论文 Table 11 与数据卡同此规范名);原目录名保留于 `meta.model_dir`;单元名保留磁盘路径原样。
5. **文件注记**(notes):`result-first` 15 个(opus-4.8 优化集,首行为 result 行;其中 5 个仅 1 行、0 调用)、
   `empty-file` 1 个(0 行,仍计为一个轨迹单元,以保 800 完整)、`unknown-format` 0 个。
6. **已知数据自相矛盾(非适配错误)**:`optimization/gemini-3.5-flash/mehnet_ccsdt_energy` 的
   result 行 `stats.tool_calls`=122,而行内 `tool_use`=86(27 个 gemini 文件对账中唯一一处)。
7. **时间戳缺失不插补**:gaps 不可算即 null;`claude_stream` 中 175 个优化集文件有调用时间戳(call_ts),
   420 个开题集文件用 tool_result 行时间戳回填(result_ts)。

## 解耦指标(2026-10-15 追加;外部复核建议,逐条核对后落地)

两个熵不是独立读数:**kind_entropy 的样本恰是转移的目标端**(c₂..cₙ),故无平滑时
`H_kind·ln2 = H(Y)`、`H⁽⁰⁾ = H(Y|X)`,二者之差就是经验互信息 `I(X;Y)`;α=1 平滑又把
长度相关的底噪灌进 `transition_entropy`(纯单类别流:te 随 m 从 2.0432 降到 0.0550)。因此把
平滑版拆成四个可分别估读的量,全部落盘(`features_union.jsonl`):

- `trans_entropy_ns` = H⁽⁰⁾:无平滑经验条件熵(P̂⁽⁰⁾=N_ab/N_a;nat,域 [0, ln8]);
- `mi_action` = H_kind·ln2 − H⁽⁰⁾ = Î(C_t;C_{t+1}):经验行动互信息(一阶路径依赖强度,nat,恒 ≥0);
- `p_action` = I_action/(H_kind·ln2):归一化可预测性 [0,1];H_kind=0(单类别流)⇒ null,不设零;
- `s_smooth` = 平滑熵 − H⁽⁰⁾:平滑敏感度(α=1 下恒 ≥0;越大=读数越依赖伪计数);
- `mi_perm_p`:保频置换检验单侧 p(k=200,**固定 c₁、洗牌 c₂..cₙ**——H(Y) 严格不变 ⇒ 置换量恒 ≥0;
  `crc32(seq)` 定种;p=(1+#{I_perm≥I_obs})/(1+k);修正记录见「校准与探针」节)。

核对与快照:恒等式与独立联合 MI 对拍最大差 1.7e-07;单类别底噪表逐位一致;mi 覆盖 854/862,
P_action 762(92 条单类别流未定义),置换显著(p<0.05)629/854;I_action 中位 0.2433 nat、
最大 0.8773;open-ended 路径依赖显著高于 optimization(P_action 中位 0.377 vs 0.1231)。
**读法要点**:平滑散点 825/854 个点越出 `y = x·ln2` 边界(超出量 = S_smooth − I_action),
即本语料里平滑底噪普遍大于路径依赖信息——引用平滑版 `transition_entropy` 时应同时报 H⁽⁰⁾ 与 S_smooth。

## 校准与探针(2026-10-15 追加;偏校正 / 样本外 / 时间·阶段探针)

解耦之后,读数的**可信度**与**可泛化性**分开测量,全部落盘(`features_union.jsonl` + `dl_test.json`):

| 量 | 字段 | 口径 | 覆盖 |
|---|---|---|---|
| 偏校正互信息 | `mi_excess` | = I_obs − E_perm[I];置换 = **固定 c₁、洗牌 c₂..cₙ**(k=200,`crc32` 定种 ⇒ 确定性;H(Y) 严格不变 ⇒ 置换量恒 ≥0)。可为负(观察低于偶然),不截断 | 854 |
| 置换零均值 | `mi_perm_mean` | 上述置换的 I 均值 | 854 |
| Miller–Madow 修正 | `mm_delta_nat` / `kind_entropy_mm` | +(K_obs−1)/(2m) nat(Paninski 2003;K_obs = 观测类别数,m = |c₂..cₙ|) | 854 |
| 平滑先验占比上界 | `prior_share_max` | max_a 8/(N_a+8)(最稀疏转移行的 α=1 混合质量) | 854 |
| 突发性 / 时间记忆 | `burstiness_b` / `gap_memory_m` | (σ−μ)/(σ+μ) / 相邻间隔一阶自相关;≥4 间隔;含排队/采样混杂 | 687 |
| 阶段半程探针 | `js_half` | 前缀半 vs 后置半类别分布的 JS 散度(nat,上界 ln2) | 839 |

**样本外对数损失**(`dl_test.py` → `dl_test.json/md`;Laplace α=1,两模型同口径):

- ΔL_a(单元自身前半→后半;m≥20):n=765,中位 **0.0218** nat,413/765 >0;
- ΔL_b(留一任务池化→本单元;m≥8,防同题泄漏):n=833,中位 **0.1938** nat,786/833 >0;
- 池化 AIS:A₁=0.2574、A₂=0.3103、**ΔA₂=+0.0529**(二阶历史相对一阶 +20.6%,保频置换 p=0.004975);
- 自检:每单元无平滑恒等式 L₀_train−L₁_train = Î,最大差 **0.0**。

**2026-10-15 修正记录**:置换零原为「全序列洗牌 + 固定原 H(Y)」——目标端多重集会漂移,置换统计量不干净
(14 个稀有首调单元的零均值甚至为负)。已改为固定 c₁、洗牌 c₂..cₙ;显著数 631→**629**
(BH-FDR q=0.05 后 615/854);33 个负 excess 为合法取值(低于偶然)。

## 论文数字复算(`paper_checks.py`,零 LLM)

`PASS 30 / MISMATCH 4(全部为数据卡级登记偏差)/ RECORD 3` —— 明细见 `paper_checks.md`。要点:

- **§2.2.3**「73k tool calls at an average of 92.3 steps per episode」⇒ 复算 73,842(92.3025/跑);
  同一口径下 claude result 行 `num_turns` 均值 108.260(n=592)⇒ 论文的「steps」即工具调用数,不是 num_turns。
- **§5.1 表自洽**:Table 12 ΣHIT=12,712(HIT% 列=half-even 舍入,实测 5 处 .25 边界);
  Table 13 行和=Table 12、列和=Σ 行;Table 14–21 与 Table 13 逐模型重算 top-10 全等(并列按 ID 字母序)。
- **分布声明**:R1 31.0% / R2 27.6% / R3 33.5% / R4 7.9%,R1+R2+R3=92.1%;F.4 660/800(82.5%);
  F.4+F.2+D.7=13.0%;逐模型总量 1,396(opus-4.8)–1,818(qwen3.7-max);E.2/D.4/A.5/C.1 全 8 模型 top-10、
  F.4 7/8;B.1 13–61;D.6 3–36;F.5=1、F.6=3;R4 最高仅第 26/45(C.4)——全部复算一致。
- **数据卡偏差(登记)**:卡片「559 / 31 tasks / 247(195 success)」vs 磁盘 560 / 30 / 240(188 success);
  「52 non-success」相符;卡片自数 559+247=806 ≠ 论文 800,磁盘 560+240=800 与论文一致。
- **复算边界**:论文的 LLM-judge 侧数字(IAA κ、Table 2 等)与 45 模式的逐轨迹标注**未发布工件**,
  不在机械复算范围;`arft.json` 将 45 模式 × 四支柱参照表入库(阶段/支柱/全量 HIT/逐模型向量)。

## 产物与命令

| 文件 | 内容 |
|---|---|
| `features_union.jsonl` | 862 单元 × 统一统计(排序后,`sort_keys`) |
| `audit.json` | 未映射名、缺陷工件、lab 对读、gemini 对账、格式计数 |
| `summary.md` | 人读摘要(语料/逐模型/格式覆盖/审计) |
| `paper_checks.json` / `paper_checks.md` | 逐条论文/卡片复算 |
| `arft.json` | 45 模式 × 四支柱参照表(入库参照) |
| `extract_cross.py` | 并集统计主管线(唯一写 `features_union.jsonl` 的脚本) |
| `dl_test.py` / `dl_test.json` / `dl_test.md` | 样本外 ΔL(前缀/留一任务)+ 池化 AIS ΔA₂ + 训练恒等式自检 |
| `paper_checks.py` / `check.py` | 复算层 / 验收层 |
| `fetch_are.py` · `parse_paper_tables.py` · `survey_formats.py` | 语料重取 / 表格提取 / 格式勘查 |

```bash
cd harness/refs/crossfusion-2026-10-15
python3 check.py     # 一条命令验收:逐字节复现 + 不变式 + lab 对读 + 论文复算(全绿 rc=0)
```

站点页 `#/crossfusion` 由 `viz/scripts/build_crossfusion.py` 将
`features_union.jsonl + arft.json + paper_checks.json + dl_test.json`(经 `audit.json` 补充注记)投影为
`viz/src/data/crossfusion.json`(确定性,零手抄)。

**复核范围声明**(与 AGENTS.md 一致):核对的是论文/卡片所载数字与数据的自洽与复算;
论文正文推断性结论与 judge 侧数字不在范围。本仓数据出处三分:论文原话(引号内)、
复算值(本管线产出)、判断(明确标注),互不混写。
