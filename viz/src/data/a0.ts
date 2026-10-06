import type { CostRow, LadderStep, StrengthRow } from '../types.ts'

/**
 * Every number here was read out of a0/ on 2026-10-06 at HEAD ccae0deb, not recalled.
 * Sources: a0/TIMING-REVIEW.md §2.5 §2.7 §3.2 §5, a0/A1-RESULT.md §3 §6 §7.
 */

/** The strength curve — the only measurement of "external artifact strength" in the repo.
 *  Explicitly instrument-scoped: "ρ 是 assay 的属性,MUST NOT 被当作关于世界的证据"
 *  (positive_control/PC-REVISION.md:165-166; a0/A1-RESULT.md:65). */
export const STRENGTH: StrengthRow[] = [
  { control: 'pc',  k: Infinity, kLabel: '∞', deltaDev: 0.247942608, rhoDev: 0.158819629, deltaEval: 0.238448095, rhoEval: 0.178715729, famDev: '4/4, 0/4', famEval: '4/4, 0/4', dev: 'NOT', eval_: 'NOT' },
  { control: 'k01', k: 1,  kLabel: '1',  deltaDev: 0.018221497, rhoDev: 0.940123488, deltaEval: 0.017982784, rhoEval: 0.942883023, famDev: '1/4, 4/4', famEval: '1/4, 4/4', dev: 'NOT', eval_: 'NOT' },
  { control: 'k02', k: 2,  kLabel: '2',  deltaDev: 0.032882006, rhoDev: 0.895644283, deltaEval: 0.033074123, rhoEval: 0.894196025, famDev: '4/4, 4/4', famEval: '4/4, 4/4', dev: 'ADM', eval_: 'ADM' },
  { control: 'k05', k: 5,  kLabel: '5',  deltaDev: 0.069657568, rhoDev: 0.775149080, deltaEval: 0.070199653, rhoEval: 0.762308313, famDev: '4/4, 4/4', famEval: '4/4, 4/4', dev: 'ADM', eval_: 'ADM' },
  { control: 'k10', k: 10, kLabel: '10', deltaDev: 0.116584858, rhoDev: 0.615639328, deltaEval: 0.116426731, rhoEval: 0.600847458, famDev: '4/4, 4/4', famEval: '4/4, 4/4', dev: 'ADM', eval_: 'ADM' },
  { control: 'k25', k: 25, kLabel: '25', deltaDev: 0.204898135, rhoDev: 0.325902583, deltaEval: 0.202023485, rhoEval: 0.301162791, famDev: '4/4, 3/4', famEval: '4/4, 2/4', dev: 'ADM', eval_: 'NOT' },
]

export const STRENGTH_CURRENT = 'k10'

export const GATE_THRESHOLDS = {
  deltaMeanMin: 0.03, deltaFamMin: 0.02, deltaFamNeeded: 3,
  rhoMedianMin: 0.30, rhoFamMin: 0.30, rhoFamNeeded: 3,
  cite: 'a0/A1-RESULT.md §3 — thresholds never changed',
}

/** Two facts that must travel with the strength table. */
export const STRENGTH_CAVEATS = [
  { text: '已发表的 greedy 构造同样过不了 ρ 门', value: 'Δ 0.22871009 · ρ 0.23993558 · 0/4 族', cite: 'TIMING-REVIEW §2.5' },
  { text: '提高 n 不是答案', value: 'ER:p080 的 ρ 随 n 单调降到 0.1298;n_where_rho_passes = [];无界正控在 n≥512 超时', cite: 'TIMING-REVIEW §2.5' },
]

/** B_hard, frozen from a pre-frozen procedure (PILOT-PROCEDURE.md, sha 68af1321…). */
export const B_HARD = {
  tWallSec: 1800, ceqMax: 1966519, nEvaluatorCalls: 725, pConcurrency: 1,
  sha: 'fd15d9ec…', cite: 'a0/A1-RESULT.md §6',
}

/** Measured rates on the 12-graph calibration set (explicitly not for algorithm selection). */
export const RATES = [
  { arm: 'A_simpleloop', ceqPerMin: 52440, evalsPerMin: 9.898, cv: 0.112 },
  { arm: 'A_kapso', ceqPerMin: 21323, evalsPerMin: 19.315, cv: 0.088 },
]

/** Guardrails do not bind early: CEq_max maps to 37.50 / 92.22 min, N_E,max to 73.25 / 37.54 min,
 *  all later than the 30 min wall clock. Wall clock is the design constraint, not money. */
export const COST: CostRow[] = [
  { campaigns: 8,   wallHours: 4,  ceqCap: 15732152,  ceqMeasured: 12585717 },
  { campaigns: 20,  wallHours: 10, ceqCap: 39330380,  ceqMeasured: 31464294 },
  { campaigns: 40,  wallHours: 20, ceqCap: 78660760,  ceqMeasured: 62928587 },
  { campaigns: 80,  wallHours: 40, ceqCap: 157321520, ceqMeasured: 125857175 },
  { campaigns: 136, wallHours: 68, ceqCap: 267446584, ceqMeasured: 213957197 },
]

/** 300k CEq ≈ $0.09 under the contract-frozen Flash peak price ⇒ 1 CEq = 3e-7 USD. */
export const CEQ_TO_USD = 3e-7
export const COST_NOTE = 'N=40 → $19–24;N=136 → $64–80。墙钟是约束,钱不是。R=10/16/34 不在仓库里(正则与 git log -S 均无命中);R=4 的 ≥3/4 判据在真值 0.5 时通过率仅 31.25%。'

/** The three gates. G1/G2 are already measured for k=10 and cost nothing; G3 is unmeasured. */
export const GATES = [
  { id: 'G1', name: 'Artifact Efficacy', formula: 'J_X − J_0 ≥ δ_artifact', state: 'measured' as const, value: 'Δ = 0.116584858,4/4 族', cite: 'TIMING-REVIEW §3.2' },
  { id: 'G2', name: 'Residual Headroom', formula: 'ρ_X = (R − J_X)/(R − J_0) ≥ ρ_min', state: 'measured' as const, value: 'ρ = 2417/3926 = 0.615639328,4/4 族', cite: 'TIMING-REVIEW §3.2' },
  { id: 'G3', name: 'Agent Nonredundancy', formula: 'Δ_X^agent = E[Y(X@0) − Y(X@∞)] ≥ δ_agent', state: 'unmeasured' as const, value: '完全没测。且 G₃ ≡ g(0),数值上就是 B0a 曲线的 0 端点', cite: 'TIMING-REVIEW §3.2 §7.1' },
]

export const LADDER: LadderStep[] = [
  { id: 'A-1', label: 'A−1 冻结 EvalContract', question: '评测器身份能不能被冻结?', state: 'done', note: 'EID* = 664115e0…(plumbing)/ 7ce9e72f…(T1)。五分量各有可复算哈希。', cite: 'STATUS §3.1 · A1-RESULT §2' },
  { id: 'A0.1', label: 'A0.1 Evaluator Conformance', question: '三个 adapter 是否忠实执行同一个 E*?', state: 'done', note: '记成三元组 (passed, measured, total) 而非布尔。EvE 是 5/14 measured,那 9 行是声明的合成失败。', cite: 'STATUS §3.3' },
  { id: 'A0.2', label: 'A0.2 Score→Search Contract', question: '各 runtime 是否按声称的 selection semantics 消费评价?', state: 'done', note: 'SimpleLoop 9/9、KAPSO 14/14(5 场景)、Loreley 7/7、EvE 频率检验 p̂=0.7290 (z=−0.62)。', cite: 'STATUS §3.3' },
  { id: 'audit', label: '独立对抗审计', question: '仪器自己会不会假通过?', state: 'done', note: '31 条 claim = 27 ACCEPTED / 3 REJECTED / 1 UNPROVEN。R1 是计算器自身的假通过漏洞,已修并补永久 fixture。', cite: 'STATUS §4' },
  { id: 'A1', label: 'A1 substrate qualification', question: '哪套 runtime 当后续实验的基底?', state: 'blocked', note: '门 ADMISSIBLE(k=10),但 R_A1^main = ∅ —— 第 8 项(4 block × 2 arm campaign)一个都没跑。', cite: 'A1-RESULT §7' },
  { id: 'mechA', label: '机制 A 接线', question: 'agent lane 能不能真的封闭?', state: 'not-started', note: 'unshare 挂载命名空间已实测可行,但只写了 diff、未接线;强制点是启动处的 PATH shim,不是内核。', cite: 'TIMING-REVIEW §2.4 §5.4' },
  { id: 'long', label: '30 分钟真实长会话', question: '封闭下能不能跑完一整轮?', state: 'not-started', note: '从未做过。实测会话只有 1.1–2.5 s 一轮;REPORT.md:320 自认只测了 invocation shape。', cite: 'TIMING-REVIEW §2.4 §5.4' },
  { id: 'G3', label: 'G₃ 非冗余门', question: 'packet 是否形成可操纵的信息处理效应?', state: 'unmeasured', note: 'T1 的机制空间是 Max-Cut 启发式 —— 预训练最密集的一类。该风险选任务时写下过,却没进任何冻结工件。', cite: 'TIMING-REVIEW §4.3' },
  { id: 'B0a', label: 'B0a timing identification', question: 'reveal 时机有没有因果作用?', state: 'not-started', note: 'τ/B ∈ {0,.2,.4,.6,.8,∞},测 g(τ)=E[Y(τ)−Y(∞)]。若 g(τ)≈常数则 B0b 不启动。', cite: 'TIMING-REVIEW §5.1' },
  { id: 'B0b', label: 'B0b state 能否预测时机', question: '轨迹状态能否比固定时钟判得更好?', state: 'not-started', note: '第一代只用 r̂_t、ℓ_t、b_t 三个 harness-authoritative 量。r̂ 与 ℓ 可能退化成一维。', cite: 'TIMING-REVIEW §5.2 §3.5' },
  { id: 'B1', label: 'B1 联合决定 when + what', question: 'agent 能否同时决定何时获取与获取什么?', state: 'not-started', note: '尚未设计到可执行。', cite: 'TIMING-REVIEW §5' },
  { id: 'stage2', label: 'live open-world search', question: '离开冻结 packet 之后还成立吗?', state: 'not-started', note: 'C 线 v4:463 规定的第二阶段,才是真正回答 H_O 的地方。', cite: 'research_state_control_review_v4.tex:463' },
]

/** The leak, measured. Three codex postures place no limit on reading. */
export const LEAK = [
  { posture: 'codex danger-full-access', reachable: '48/50', tcp: true, note: 'T1 的 coding_agent 就是这一档' },
  { posture: 'codex workspace-write', reachable: '40/50', tcp: false, note: '与 read-only 全部 50 格逐一相同' },
  { posture: 'codex read-only', reachable: '40/50', tcp: false, note: '同上' },
  { posture: 'candidate sandbox', reachable: '5/50', tcp: false, note: '只对候选有效,不是对 agent' },
  { posture: '宿主(对照)', reachable: '48/50', tcp: true, note: '—' },
]
export const LEAK_NOTE = 'web_search: false 关的是工具不是 TCP ⇒ 「封闭臂」今天不存在。拟用 packet 在工作区有 4 条可读路径,其中 2 条被 git 跟踪。'
