// Measured, not estimated. Line counts come from `git ls-files` + a line count of each
// file on disk, taken 2026-10-06 at HEAD ccae0deb. `linesRead` is my own honest accounting:
// full for files I read end to end, the section range for partial reads, zero for
// second-hand (a subagent read it and gave me path:line citations I spot-checked) and
// zero for unread. "generated" means I produced the file and read only part of it.
import type { CoverageRow, CoverageSummary } from '../types.ts'

export const COVERAGE_SUMMARY: CoverageSummary = {
 "corpusFiles": 35,
 "corpusLines": 83866,
 "corpusLinesExclTranscript": 22366,
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
  "path": "related_files/research_state_control_review_v2.tex",
  "lines": 931,
  "status": "recovered",
  "linesRead": 0
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
  "path": "related_files/research_state_control_review.tex",
  "lines": 616,
  "status": "secondhand",
  "linesRead": 0
 },
 {
  "path": "related_files/virtual_staining_open_source_sota_survey.typ",
  "lines": 588,
  "status": "unread",
  "linesRead": 0
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
  "path": "related_files/research_state_control_refs_v2.bib",
  "lines": 325,
  "status": "recovered",
  "linesRead": 0
 },
 {
  "path": "related_files/adapdc_relation_first_plan.typ",
  "lines": 279,
  "status": "secondhand",
  "linesRead": 0
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
  "path": "related_files/virtual_staining_refs.bib",
  "lines": 149,
  "status": "unread",
  "linesRead": 0
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
 }
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
