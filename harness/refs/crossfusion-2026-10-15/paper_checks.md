# paper_checks — 论文/卡片数字机械复算(零 LLM)  

论文 arXiv 2608.14905v3 · 表格 sha256 952c193fd6f7… · 结果:PASS 30 / MISMATCH 4 / RECORD 3

| id | scope | 声明 | expected | actual | status | note |
|---|---|---|---|---|---|---|
| t11.models | paper | Table 11:8 个 harness–model 组合 ⇒ 800 | {"n_models": 8, "total": 800} | {"n_models": 8, "total": 800} | PASS | 各模型 n=100 见下条 |
| t11.each100 | paper | Table 11 每个模型 n=100 | 8 | 8 | PASS |  |
| calls.avg | paper | §2.2.3「73k tool calls at an average of 92.3 steps per episode」——均值 | 92.3 | 92.3 | PASS |  |
| calls.total | paper | 同上——总数(92.3×800=73,840 的口径;±10 容差) | 73840 | 73842 | PASS | 复算 73842(与 92.3×800 差 +2;论文「73k」为约记) |
| t12.sum | paper | §5.1「12,712 hits across 800 analyses」;Table 12 ΣHIT | 12712 | 12712 | PASS |  |
| t12.pct | paper | Table 12:HIT% = HIT/800 四舍五入到 1 位小数(全 45 行) | 45 | 45 | PASS |  |
| t12.order | paper | Table 12 按 HIT 降序排列 | true | true | PASS |  |
| t12.f4 | paper | 「F.4 … appearing in 660 of 800 analyses (82.5%)」 | [660, 82.5] | [660, 82.5] | PASS |  |
| t12.top3 | paper | 「Together these three patterns account for 13.0% of all hits」(F.4+F.2+D.7) | 13.0 | 13.0 | PASS |  |
| pillar.R1.share | paper | R1 份额(正文声明见 §5.1) | 31.0 | 31.0 | PASS | Grounding & Faithfulness:12 模式,3944 hits |
| pillar.R2.share | paper | R2 份额(正文声明见 §5.1) | 27.6 | 27.6 | PASS | Cognitive Depth & Adaptability:13 模式,3510 hits |
| pillar.R3.share | paper | R3 份额(正文声明见 §5.1) | 33.5 | 33.5 | PASS | Integrity & Alignment:13 模式,4256 hits |
| pillar.R4.share | paper | R4 份额(正文声明见 §5.1) | 7.9 | 7.9 | PASS | Engineering Robustness:7 模式,1002 hits |
| pillar.trio | paper | 「together account for 92.1% of all hits」(R1+R3+R2) | 92.1 | 92.1 | PASS |  |
| pillar.coverage | paper | Table 3 的 45 个模式归属:不重不漏,且与 Table 12 同集 | [45, 45] | [45, 45] | PASS |  |
| pillar.counts | paper | R1/R2/R3/R4 模式数 = 12/13/13/7 | [12, 13, 13, 7] | [12, 13, 13, 7] | PASS |  |
| t13.rowsum | paper | Table 13:45 行「行和 = 8 列之和 = Table 12 对应 HIT」 | 45 | 45 | PASS |  |
| t13.colsum | paper | Table 13:列和 = Σ 行 | true | true | PASS | Σ 行 = ['1481', '1396', '1616', '1410', '1617', '1818', '1679', '1695'] |
| t13.range | paper | 「Total hit counts range from 1,396 (opus-4.8) to 1,818 (qwen3.7-max)」 | [1396, "opu", 1818, "qwn"] | [1396, "opu", 1818, "qwn"] | PASS |  |
| t14-21.match | paper | Appendix E(Tables 14–21)top-10 与 Table 13 列重算一致 | 8 | 8 | PASS |  |
| top10.all8 | paper | 「E.2, D.4, A.5, and C.1 appear in the top 10 of every model」 | true | true | PASS | E.2:8/8;D.4:8/8;A.5:8/8;C.1:8/8 |
| top10.f4 | paper | 「F.4 in seven of the eight」 | 7 | 7 | PASS | 缺 F.4 的模型:gem |
| diverge.b1 | paper | 「B.1 ranges from 13 hits (glm-5.2) to 61 (gpt-5-mini)」 | [13, "glm", 61, "gpt"] | [13, "glm", 61, "gpt"] | PASS |  |
| diverge.d6 | paper | 「D.6 ranges from 3 (opus-4.8 and claude-sonnet-5) to 36 (qwen3.7-max)」 | [3, ["opu", "son"], 36, "qwn"] | [3, ["opu", "son"], 36, "qwn"] | PASS |  |
| t12.f5f6 | paper | 「F.5 and F.6 … one and three hits respectively」 | [1, 3] | [1, 3] | PASS |  |
| rank.c4 | paper | 「execution faults … (C.4), places only 26th of 45」 | 26 | 26 | PASS |  |
| stage.37 | paper | Table 6 = 37 个阶段内模式;其余为 8 个跨阶段 X.n | [37, 8] | [37, 8] | PASS | 集合一致性:表6 = A–F 全集 |
| stage.pillar | paper | Table 6 十字表列归属 ≈ Table 3 支柱归属(37 个) | 37 | 37 | PASS |  |
| card.sum | card | 卡片自数:559 + 247 = 806 ≠ 论文 800;磁盘 560 + 240 = 800 | 800 | 806 | MISMATCH | 卡片两处均偏;论文与磁盘一致(见下两条) |
| card.oe | card | 卡片「70 tasks × 8 models = 559 rollouts」 | 559 | 560 | MISMATCH | 磁盘 560 = 70×8;唯一数 (task,model) 亦 560 |
| card.opt.n | card | 卡片「31 tasks × 8 models = 247 rollouts」 | [31, 247] | [30, 240] | MISMATCH | 磁盘 30 任务 × 8 = 240;论文 Table 23 亦 n=30 |
| card.opt.success | card | 卡片「195 success / 52 non-success」 | [195, 52] | [188, 52] | MISMATCH | non-success 52 相符;success 实为 188 |
| data.tasks | data | 任务清单:open-ended 70 / optimization 30(论文 Table 22/23 同) | [70, 30] | [70, 30] | PASS | tasks.jsonl 唯一 task_id:70/30 |
| data.status | data | optimization status 分布(磁盘) | null | {"success": 188, "timeout": 17, "agent_error": 23, "killed": 12} | RECORD |  |
| data.regime | data | open-ended regime_move_verified 分布(磁盘) | null | {"search": 355, "discovery": 39, "unverified_discovery_attempt": 94, "None": 42, "retrieval": 30} | RECORD |  |
| data.num_turns | data | claude 单元级 num_turns 均值(≠ 92.3;论文「steps」指工具调用数) | null | {"n": 592, "mean": 108.26} | RECORD |  |
| data.units | data | 并集单元:800 are + 62 ours 侧/臂 | [800, 62] | [800, 62] | PASS | are calls=73842 |
