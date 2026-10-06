// Measured, not estimated. Line counts come from `git ls-files` + a line count of each
// file on disk, taken 2026-10-06 at HEAD ccae0deb. `linesRead` is my own honest accounting:
// full for files I read end to end, the section range for partial reads, zero for
// second-hand (a subagent read it and gave me path:line citations I spot-checked) and
// zero for unread. "generated" means I produced the file and read only part of it.
// 2026-10-06 (later same day): 17 rows added with status "fetched" — they came out of the
// account Library in three commits (900bcb0 · ef9d9b2 · 301a4be) and I have read none of them.
// Three of those are `.rendered.txt`: Deep Research reports whose markdown source is not
// obtainable, so the copy is the rendered text and the filename carries the caveat.
import type { CoverageRow, CoverageSummary } from '../types.ts'

export const COVERAGE_SUMMARY: CoverageSummary = {
 "corpusFiles": 52,
 "corpusLines": 94538,
 "corpusLinesExclTranscript": 33038,
 "a0TopMd": 9,
 "a0TopMdLines": 1920,
 "a0TrackedTotal": 37400,
 "repoTrackedTotal": 37437,
 "corpusLinesRead": 2843,
 "a0LinesRead": 893,
 "corpusLinesReadExclTranscript": 2843
}

export const CORPUS_COVERAGE: CoverageRow[] = [
 {
  "path": "related_files/conversation/transcript.md",
  "lines": 61500,
  "status": "generated",
  "linesRead": 0,
  "note": "我生成并检索过它,没有逐行读。计入已读会是自我美化。"
 },
 {
  "path": "related_files/范畴论驱动实验系统的工程落地计划与审查包.rendered.txt",
  "lines": 1763,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户 Library 取回,仅渲染文本(markdown 标记已丢)。Deep Research 报告"
 },
 {
  "path": "related_files/deep-research-report(1).md",
  "lines": 1721,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/deep-research-report.md",
  "lines": 1673,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/research_state_control_review_v4.tex",
  "lines": 1607,
  "status": "partial",
  "linesRead": 128,
  "note": "读过的区段:269-272、1215-1270、1540-1607(含九条原则与结尾的可证伪约束)。其余为二手。"
 },
 {
  "path": "related_files/deep-research-report(2).md",
  "lines": 1575,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_algorithm_research_engineering_plan.typ",
  "lines": 1513,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/Pasted markdown.md",
  "lines": 1412,
  "status": "read",
  "linesRead": 1412
 },
 {
  "path": "related_files/范畴论驱动的实验编排与工程落地-AdaPDC审查与CEC实施方案.rendered.txt",
  "lines": 1370,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上,仅渲染文本"
 },
 {
  "path": "related_files/范畴论优先的实验编排与工程落地-理论实现与路线评估.rendered.txt",
  "lines": 1271,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上,仅渲染文本"
 },
 {
  "path": "related_files/research_state_control_review_v3.tex",
  "lines": 1216,
  "status": "recovered",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_review.typ",
  "lines": 1032,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_independent_review.typ",
  "lines": 1030,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_independent_review(5).typ",
  "lines": 935,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户 Library 取回:拼接 CodeMirror 预览,typst 编译通过。B 线;此前记为不可恢复"
 },
 {
  "path": "related_files/research_state_control_review_v2.tex",
  "lines": 931,
  "status": "recovered",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_independent_review(4).typ",
  "lines": 839,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上(B 线 v(4))"
 },
 {
  "path": "related_files/open_world_plan_independent_review(3).typ",
  "lines": 762,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上(B 线 v(3))"
 },
 {
  "path": "related_files/ada-engineering-plan.typ",
  "lines": 726,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/opl-engineering-plan.typ",
  "lines": 710,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_independent_review(2).typ",
  "lines": 663,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上(B 线 v(2);该预览需先点 Try again"
 },
 {
  "path": "related_files/research_state_control_review.tex",
  "lines": 616,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/open_world_plan_independent_review(1).typ",
  "lines": 601,
  "status": "fetched",
  "linesRead": 0,
  "note": "同上(B 线 v(1))"
 },
 {
  "path": "related_files/virtual_staining_open_source_sota_survey.typ",
  "lines": 588,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "related_files/TIMING-REVIEW(1).md",
  "lines": 544,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回(Copy → 剪贴板,源码原文)。H_T 独立审查 v2;与 a0/TIMING-REVIEW.md 差 288 行"
 },
 {
  "path": "related_files/rule-construction-research(1).md",
  "lines": 530,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "related_files/research_state_control_refs_v4.bib",
  "lines": 519,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/synthesis_2026-09-30.typ",
  "lines": 488,
  "status": "authored",
  "linesRead": 488
 },
 {
  "path": "related_files/rule-construction-research.md",
  "lines": 484,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "related_files/adapdc_scaffold_implementation(1).typ",
  "lines": 464,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/research_state_control_refs_v3.bib",
  "lines": 461,
  "status": "recovered",
  "linesRead": 0
 },
 {
  "path": "related_files/adapdc_theory_review.typ",
  "lines": 430,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/adapdc_scaffold_implementation.typ",
  "lines": 408,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/algorithm_research_infrastructure_plan.typ",
  "lines": 408,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/c0-status-review.md",
  "lines": 338,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。AdaPDC C0 收尾审查(09-10)"
 },
 {
  "path": "related_files/research_state_control_refs_v2.bib",
  "lines": 325,
  "status": "recovered",
  "linesRead": 0
 },
 {
  "path": "related_files/status.md",
  "lines": 323,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。AdaPDC 现状审查,锚点 6db0d78"
 },
 {
  "path": "related_files/review-packet.md",
  "lines": 307,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。源码审查包,锚点 6db0d78"
 },
 {
  "path": "related_files/adapdc_relation_first_plan.typ",
  "lines": 279,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/STATUS(2).md",
  "lines": 251,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。A−1/A0.1/A0.2 测量链快照;与 a0/STATUS.md 差 115 行"
 },
 {
  "path": "related_files/STATUS(1).md",
  "lines": 249,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。A−1/A0.1/A0.2 测量链快照;与 a0/STATUS.md 差 117 行"
 },
 {
  "path": "related_files/conversation/decode_share.py",
  "lines": 248,
  "status": "authored",
  "linesRead": 248
 },
 {
  "path": "related_files/research_state_control_refs.bib",
  "lines": 214,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/agent_engineering_science_progress_2026-09-24.md",
  "lines": 195,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。D 线进展稿(09-24)"
 },
 {
  "path": "related_files/conversation/user_turns.md",
  "lines": 186,
  "status": "read",
  "linesRead": 186
 },
 {
  "path": "related_files/conversation/replay_state_control.py",
  "lines": 170,
  "status": "authored",
  "linesRead": 170
 },
 {
  "path": "related_files/experiment-catalog-contract.md",
  "lines": 155,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。Experiment Catalog 接口契约 v0.1"
 },
 {
  "path": "related_files/virtual_staining_refs.bib",
  "lines": 149,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "related_files/agent_engineering_independent_audit_v2_2026-09-24.md",
  "lines": 106,
  "status": "fetched",
  "linesRead": 0,
  "note": "账户取回。D 线第二轮独立审计"
 },
 {
  "path": "related_files/agent_engineering_science_independent_review_2026-09-24.md",
  "lines": 88,
  "status": "read",
  "linesRead": 88
 },
 {
  "path": "related_files/conversation/README.md",
  "lines": 84,
  "status": "authored",
  "linesRead": 84
 },
 {
  "path": "related_files/refs.bib",
  "lines": 42,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "related_files/Makefile",
  "lines": 39,
  "status": "read",
  "linesRead": 39
 },
]

export const A0_COVERAGE: CoverageRow[] = [
 {
  "path": "a0/TIMING-REVIEW.md",
  "lines": 544,
  "status": "partial",
  "linesRead": 460
 },
 {
  "path": "a0/STATUS.md",
  "lines": 244,
  "status": "read",
  "linesRead": 244
 },
 {
  "path": "a0/EPISTEMIC-REVIEW.md",
  "lines": 238,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "a0/A1-REQUIREMENTS.md",
  "lines": 230,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "a0/A1-RESULT.md",
  "lines": 189,
  "status": "read",
  "linesRead": 189
 },
 {
  "path": "a0/A1-CONTRACT-AUDIT.md",
  "lines": 160,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "a0/SPRINT-2026-09-21.md",
  "lines": 113,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "a0/A1-INTERIM.md",
  "lines": 104,
  "status": "unread",
  "linesRead": 0
 },
 {
  "path": "a0/CONVERGENCE-2026-09-21.md",
  "lines": 98,
  "status": "unread",
  "linesRead": 0
 }
]
