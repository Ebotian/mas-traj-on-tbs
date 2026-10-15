# crossfusion-2026-10-15 — 并集轨迹机械统计(摘要)

数据并集:ours(54 侧 + 8 臂)× are(AutoResearchEval 800 条,钉版 412fb490…);方法并集:统一 8 类 taxonomy + 熵/节律/静默失败/缓存(定义见 README,实现即定义)。

## 语料
| source | corpus | units | calls | masked | gaps 可算 | 说明 |
|---|---|---:|---:|---:|---:|---|
| are | open-ended | 560 | 29041 | 606 | 420/560 | |
| are | optimization | 240 | 44801 | 625 | 205/240 | |
| ours | arm | 8 | 728 | 26 | 8/8 | |
| ours | microarch | 10 | 2998 | 105 | 10/10 | |
| ours | tess | 2 | 655 | 8 | 2/2 | |
| ours | tumor | 6 | 1438 | 49 | 6/6 | |
| ours | walkthrough | 36 | 3371 | 1 | 36/36 | |

## 逐模型(are)
| model | units | calls | calls/ep | kind_entropy 中位 | masked_rate 中位 | cache_ratio 中位 |
|---|---:|---:|---:|---:|---:|---:|
| claude-sonnet-5 | 100 | 7213 | 72.13 | 1.3922 | 0.005011 | None |
| deepseek-v4-pro | 100 | 9108 | 91.08 | 1.7657 | 0.0 | None |
| gemini-3.5-flash | 100 | 4910 | 49.10 | 1.7431 | 0.0 | 0.859 |
| glm-5.2 | 100 | 17333 | 173.33 | 1.4915 | 0.017106 | None |
| gpt-5-mini | 100 | 1938 | 19.38 | -0.0 | 0.0 | None |
| minimax-m3 | 100 | 20081 | 200.81 | 1.5343 | 0.017026 | None |
| opus-4.8 | 100 | 7356 | 73.56 | 1.5475 | 0.0 | None |
| qwen3.7-max | 100 | 5903 | 59.03 | 1.5318 | 0.0 | None |

## 格式覆盖
| format | units | gaps(basis) | masked 可判 | cache | duration |
|---|---:|---|---:|---:|---:|
| are/claude_stream | 600 | {'result_ts': 420, 'call_ts': 175} | 595 | 0 | 592 |
| are/codex_items | 30 | — | 30 | 0 | 0 |
| are/codex_text | 70 | — | 70 | 0 | 0 |
| are/gemini_ndjson | 30 | {'call_ts': 30} | 30 | 27 | 27 |
| are/gemini_text | 69 | — | 69 | 0 | 0 |
| are/unknown | 1 | — | 0 | 0 | 0 |
| ours/atif | 8 | {'step_ts': 8} | 8 | 8 | 0 |
| ours/qwen_chat | 54 | {'call_ts': 54} | 54 | 54 | 0 |

## 解耦指标(无平滑;2026-10-15 追加,据外部建议核对后落地)
H⁽⁰⁾=无平滑经验条件熵;I_action=H_kind·ln2−H⁽⁰⁾=Î(C_t;C_{t+1})(nat);P_action=I/(H_kind·ln2)(H_kind=0 ⇒ 未定义);S_smooth=平滑熵−H⁽⁰⁾;perm p=保频置换单侧 p(200 次,crc32 定种)。
| source | corpus | 单元 | I_action 中位(nat) | P_action 中位 | S_smooth 中位 | perm p<0.05 |
|---|---|---:|---:|---:|---:|---:|
| are | open-ended | 560 | 0.4047 | 0.377 | 0.838 | 443 |
| are | optimization | 240 | 0.0703 | 0.1231 | 0.4554 | 149 |
| ours | arm | 8 | 0.1093 | 0.1768 | 0.483 | 6 |
| ours | microarch | 10 | 0.13 | 0.1107 | 0.2137 | 10 |
| ours | tess | 2 | 0.0696 | 0.07 | 0.2162 | 2 |
| ours | tumor | 6 | 0.0492 | 0.0516 | 0.2675 | 3 |
| ours | walkthrough | 36 | 0.1145 | 0.1055 | 0.4868 | 18 |

## 不变式/审计
- ours 侧 vs traj-features lab 逐字段对照:54 单元,0 处不一致
- ours 侧表外工具名(按 lab 惯例归 other,合计 9 次):{'bash': 1, 'edit_file': 3, 'edit_file_path': 1, 'shell_command': 1, 'tool_call': 3}
- gemini stats.tool_calls 对账:27 文件,1 处不一致(该处为数据自身矛盾:are/optimization/gemini-3.5-flash/mehnet_ccsdt_energy)
- 未映射工具名:(无);工件名(2 处 __unparsedToolInput,归 other):['/home/ebt/harbor-runs/data/autoresearch-eval/open-ended/trajectories/qwen3.7-max/W4396723768.jsonl:?', '/home/ebt/harbor-runs/data/autoresearch-eval/open-ended/trajectories/qwen3.7-max/W7128691155.jsonl:nvidia-smi 2']
- 论文 §2.2.3 复算:论文「73k tool calls at an average of 92.3 steps per episode」;本复算 calls=73842(92.3025/跑);claude result 行 num_turns 均值 108.260(n=592) —— 与 92.3 吻合的是工具调用均值,不是 num_turns

## 备注
- 单元=一条 agent 轨迹(ours 侧/臂;are 一次 rollout);确定性、零模型调用;逐字节可复现(check.py)。
- notes 类目:result-first(opus-4.8 优化集 15 个文件首行为 result 行;其中 5 个仅 1 行、0 调用)/empty-file(1 个 0 行文件)/unknown-format —— 均在 audit.json 与单元 notes 中标注。
