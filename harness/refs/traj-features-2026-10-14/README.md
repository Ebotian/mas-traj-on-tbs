# traj-features-2026-10-14 — 轨迹特征数值实验 v1

确定性、零模型调用:所有数值 = 所收集工件的纯函数(重跑逐字节一致,见 check.py)。
本版对应「从轨迹特征可解释性到实际影响性」的①解释性层里**机械可算(A 档)**的部分;
语义推断类(S 档,如 D_source / R_consensus / F_falsify 的语义判定)不在本版内——
那类量需要先在证据根映射上冻结口径,否则就是拿语义冒充计数。

## 输入

- 双跑语料:`/home/ebt/harbor-runs/jobs/agent/<job>/<trial>/artifacts/root/wt/collect`
  - `chats/<uuid>.jsonl` — 两侧转录;uuid 经 `x/session-a.uuid`、`x/session-b.uuid` 映射到 a/b
  - `x/` — rcs、ready-*.round、pos-*、stop/abort、divergence.json、gate.log、stats/
  - `state.json`(NORMAL 判定字段)、`verifier/`(metrics.json 等)
- 单 agent 臂:`…/**/agent/trajectory.json`(ATIF;8 条)

## 输出

- `features_sides.jsonl` — 每侧一条:调用数、工具名分布、8 类工具、间隔统计(CV_robust/P600)、
  掩蔽错误、token 三件套、缓存比、转移熵、时长
- `features_runs.jsonl` — 每跑一条:family、NORMAL、rounds、gate 计数、stats、verifier、聚合
- `features_arms.jsonl` — 每条臂:schema_version、steps、calls、masked、final_metrics
- `summary.md` — 语料表、不变式、逐跑特征表

## 特征定义(实现即定义;extract.py 为准)

- tool kinds:read=`read_file|list_directory`;write=`write_file|edit|notebook_edit`;
  search=`glob|grep_search|tool_search`;`run_shell_command` 按命令文本细分
  wait(`wait_peer|wait_pos|wait_file|inotifywait`)/ recover / test(`pytest|check_*.py`)/ exec;其余→other
- masked = tool_result 且 `resultDisplay.exitCode==0` 且 output 含 `Traceback`(启发式下界,非失败率)
- gaps:相邻 functionCall 时间戳间隔;CV_robust = 1.4826·MAD/median;P600 = 占比 >600s
- cache_ratio:末条 usageMetadata 的 `cachedContentTokenCount/promptTokenCount`
- transition_entropy:工具类别序列的 next-kind 分布熵(bit)
- gate.log 计数:`refs-ok` / `refs-block` / `wait-start` / `block` 行数

## 运行

- `python3 extract.py [--root …] [--out …]`
- `python3 check.py` — 重跑 + 逐字节对比 + 不变式(arms 728/26;tumor-1 430)

## 不变式与已核事实

- arms:calls=728、masked=26(与机制归因提案的复核口径一致)
- tumor-1:calls=430(提案 442 vs 本地 430 的口径差)
- 语料:27 跑 / 52 侧(含 rehearsal 家族;w3 为收集前老跑,无转录)

## 边界

- 不含语义推断特征与任何模型调用;不含成本读数复算(成本在 job 侧读数)
- 时代差异(v1/v2/v3/v4 配置)在同一表中并置,解释时注意
