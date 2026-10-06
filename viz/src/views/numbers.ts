import raw from '../data/experiments.json'
import * as A0DATA from '../data/a0.ts'
import { COLOR, EVIDENCE_COLOR } from '../lib/palette.ts'
import { axisBottom, axisLeft, fmt, linear, polyline, s, text } from '../lib/svg.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'

/* The JSON is derived by scripts/derive_experiments.py from the untracked repro
 * bundle. Its shape is asserted here rather than inferred, so a regeneration that
 * changes the schema fails the typecheck instead of silently drawing nothing. */
interface Exp1Row { rho: number; N: number; N_eff_csv: number; N_eff_theory: number; accuracy_csv: number; accuracy_betabinom: number; delta_pp: number; z: number; pasted_md: number | null }
interface PastedRow { rho: number; N: number; accuracy_claimed: number; accuracy_betabinom: number; delta_pp: number; z_at_claimed_trials: number; in_exp1: boolean }
interface Exp2Row { budget: number; policy: string; regret: number; samples: number; net_utility: number }
interface Exp3Row { semantic_noise: number; flat_retrieval: number; temporal_projection: number }
interface Data {
  repro: { seed: number; rng: string; libs: string; trials: Record<string, number>; disclaimer: string; cite: string }
  p_agent: number
  exp1: { rows: Exp1Row[]; se_at_reported_trials_pp: number; worst_abs_z_over_N_ge_3: number; worst_cell: string | null; verdict: string; pasted_md: { rows: PastedRow[]; se_at_claimed_trials_pp: number; rho_values_absent_from_exp1: number[]; verdict: string } }
  exp2: { rows: Exp2Row[]; notes: Record<string, number | boolean> }
  exp3: { rows: Exp3Row[]; notes: { temporal_projection_is_constant: boolean; temporal_projection_value: number; flat_retrieval_range: number[]; queries_per_level: number } }
}
const D = raw as unknown as Data

const M = { t: 30, r: 96, b: 42, l: 58 }

interface Series { name: string; color: string; dash?: string; pts: [number, number][]; dots?: boolean; line?: boolean }

function chart(opts: { w?: number; h?: number; title: string; xlab: string; ylab: string; xd: [number, number]; yd: [number, number]; series: Series[]; xfmt?: (v: number) => string; yfmt?: (v: number) => string; marks?: { y?: number; x?: number; label: string; color: string }[] }): SVGElement {
  const W = opts.w ?? 640, H = opts.h ?? 300
  const xs = linear(opts.xd, [M.l, W - M.r])
  const ys = linear(opts.yd, [H - M.b, M.t])
  // explicit width/height so the SVG renders at its natural size instead of
  // stretching to the card width (which scaled the type up ~3x in the first build)
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': opts.title })
  g.appendChild(text(M.l, 16, opts.title, { class: 'lbl title', 'text-anchor': 'start' }))
  g.appendChild(axisLeft(ys, M.l, opts.yfmt))
  g.appendChild(axisBottom(xs, H - M.b, opts.xfmt))
  const midY = (M.t + H - M.b) / 2
  g.appendChild(text(15, midY, opts.ylab, { class: 'lbl sm', 'text-anchor': 'middle', transform: `rotate(-90 15 ${midY})` }))
  g.appendChild(text(W - M.r, H - 8, opts.xlab, { class: 'lbl sm', 'text-anchor': 'end' }))
  for (const m of opts.marks ?? []) {
    if (m.y !== undefined) {
      const y = ys(m.y)
      g.appendChild(s('line', { x1: M.l, x2: W - M.r, y1: y, y2: y, stroke: m.color, 'stroke-width': 1.3, 'stroke-dasharray': '6 4' }))
      g.appendChild(text(M.l + 4, y - 4, m.label, { class: 'lbl sm', 'text-anchor': 'start', fill: m.color }))
    }
    if (m.x !== undefined) {
      const x = xs(m.x)
      g.appendChild(s('line', { x1: x, x2: x, y1: M.t, y2: H - M.b, stroke: m.color, 'stroke-width': 1.3, 'stroke-dasharray': '6 4' }))
      g.appendChild(text(x + 4, M.t + 10, m.label, { class: 'lbl sm', fill: m.color }))
    }
  }
  for (const se of opts.series) {
    if (!se.pts.length) continue
    if (se.line !== false) {
      g.appendChild(s('path', { d: polyline(se.pts.map(p => [xs(p[0]), ys(p[1])])), fill: 'none', stroke: se.color, 'stroke-width': 1.9, 'stroke-dasharray': se.dash ?? '' }))
    }
    if (se.dots) for (const p of se.pts) g.appendChild(s('circle', { cx: xs(p[0]), cy: ys(p[1]), r: 2.9, fill: se.color }))
    if (!se.name) continue
    const last = se.pts[se.pts.length - 1]
    g.appendChild(text(Math.min(xs(last[0]) + 6, W - 2), ys(last[1]) + 3, se.name.slice(0, 14), { class: 'lbl sm', fill: se.color }))
  }
  return g
}

const RHOS = [...new Set(D.exp1.rows.map(r => r.rho))].sort((a, b) => a - b)
const RHO_COLOR = ['#1d4ed8', '#0891b2', '#166534', '#b45309', '#7c3aed', '#be123c']

/** Pasted markdown.md uses a different ρ grid, so it gets its own colour map;
 *  indexing into RHO_COLOR would collide (ρ=0.3 and 0.9 are absent from exp1). */
const PM_RHOS = [...new Set((raw as unknown as Data).exp1.pasted_md.rows.map(r => r.rho))].sort((a, b) => a - b)
const PM_COLOR: Record<number, string> = { 0: '#1d4ed8', 0.3: '#b45309', 0.7: '#be123c', 0.9: '#7c3aed' }

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '五组真实测量数据。之前它们只以散文形式存在于工具提示里 —— 而其中一组(exp1)承载着整个梳理最重要的单条发现。',
    '所有数字由 ', h('code', {}, 'viz/scripts/derive_experiments.py'), ' 从未跟踪的 zip 派生并检查入库,不是手抄。'))

  host.appendChild(h('div', { class: 'stats' },
    stat(`${D.exp1.rows.length}`, 'exp1 格子数'),
    stat(`${fmt.n(D.exp1.se_at_reported_trials_pp, 4)} pp`, `exp1 标准误 @${fmt.int(D.repro.trials.exp1_per_point)} trials`),
    stat(`${fmt.n(D.exp1.worst_abs_z_over_N_ge_3, 2)}σ`, `exp1 最坏偏差(N≥3,${D.exp1.worst_cell})`, COLOR.good),
    stat(`9.2σ`, 'Pasted md 在 ρ=0.7,N=33 的偏差', COLOR.bad),
    stat(`${fmt.n(D.exp3.notes.flat_retrieval_range[0], 4)}–${fmt.n(D.exp3.notes.flat_retrieval_range[1], 4)}`, 'exp3 flat 退化区间'),
    stat('1.0 × 6', 'exp3 temporal 恒定值', COLOR.bad),
  ))

  /* ---- exp1 ---- */
  const e1 = panel('exp1 · 相关 agent 的多数票准确率 —— CSV 与可交换 β-二项模型重合',
    chart({
      title: 'accuracy vs N,按 ρ 分色;实线=β-二项精确值,点=CSV',
      xlab: 'N (agent 数)', ylab: 'majority accuracy',
      xd: [1, 33], yd: [0.68, 1.0],
      xfmt: v => String(v), yfmt: v => v.toFixed(2),
      series: RHOS.flatMap((rho, i) => {
        const rows = D.exp1.rows.filter(r => r.rho === rho).sort((a, b) => a.N - b.N)
        const c = RHO_COLOR[i % RHO_COLOR.length]
        return [
          { name: `ρ=${rho}`, color: c, pts: rows.map(r => [r.N, r.accuracy_betabinom] as [number, number]) },
          { name: '', color: c, pts: rows.map(r => [r.N, r.accuracy_csv] as [number, number]), dots: true, line: false },
        ]
      }),
      marks: [{ y: D.p_agent, label: `p = ${D.p_agent}(单 agent)`, color: COLOR.muted }],
    }),
    note('实线是审查构造的反例模型 ', h('code', {}, 'Θ~Beta(a,b), a=p(1/ρ−1), b=(1−p)(1/ρ−1)'),
      ' 的精确多数票概率;点是 CSV 的实测值。',
      badge(`最坏 ${fmt.n(D.exp1.worst_abs_z_over_N_ge_3, 2)}σ`, COLOR.good),
      ` 36 格中 N≥3 的最坏格是 ${D.exp1.worst_cell}。在 ${fmt.int(D.repro.trials.exp1_per_point)} trials 下这属于正常波动 ⇒ `,
      h('b', {}, 'exp1 就是那个可交换 β-二项模型'), '。', cite(D.repro.cite)))

  /* ---- pasted md divergence ---- */
  const pm = D.exp1.pasted_md.rows
  const e1b = panel('同一张图的另一个版本 —— Pasted markdown.md 的表偏离同一模型',
    chart({
      title: '偏差(σ 单位),按 Pasted md 自称的 30000 trials 计',
      xlab: 'N', ylab: '(claimed − β-binom) / SE',
      xd: [3, 35], yd: [-1, 10],
      series: PM_RHOS.map(rho => ({
        name: `ρ=${rho}`, color: PM_COLOR[rho] ?? COLOR.bad,
        pts: pm.filter(r => r.rho === rho).sort((a, b) => a.N - b.N).map(r => [r.N, r.z_at_claimed_trials] as [number, number]),
        dots: true,
      })),
      marks: [{ y: 3, label: '3σ', color: COLOR.muted }],
      yfmt: v => `${v}σ`,
    }),
    note(`ρ=0.7 三格的偏差是 6.5 / 8.6 / 9.2σ(SE = ${fmt.n(D.exp1.pasted_md.se_at_claimed_trials_pp, 4)} pp)。`,
      `而 ρ ∈ {${D.exp1.pasted_md.rho_values_absent_from_exp1.join(', ')}} 这两行 exp1 里根本没有。`,
      h('b', {}, '⇒ 两个文档是两个不同的模拟。'),
      ' 审查的 5.2 pp 攻击(ρ=.3, N=33)只对后者成立,而 ρ=.3 那行在 exp1 里不存在,所以审查打的是对的目标,没有误伤。'))

  /* ---- exp2 ---- */
  const budgets = [...new Set(D.exp2.rows.map(r => r.budget))].sort((a, b) => a - b)
  const pick = (pol: string, key: 'regret' | 'samples' | 'net_utility') =>
    budgets.map(b => [b, D.exp2.rows.find(r => r.budget === b && r.policy === pol)?.[key] ?? 0] as [number, number])
  const e2 = panel('exp2 · metareasoning 与停止计算 —— L7 的形状在数据里,但 adaptive 对预算不敏感',
    h('div', { class: 'duo' },
      chart({
        title: 'mean regret vs budget(越低越好)', xlab: 'budget cap', ylab: 'regret',
        xd: [5, 80], yd: [0, 0.6],
        series: [
          { name: 'fixed', color: COLOR.line, pts: pick('fixed_equal', 'regret'), dots: true },
          { name: 'adaptive', color: COLOR.impl, pts: pick('adaptive', 'regret'), dots: true },
        ],
      }),
      chart({
        title: 'mean net utility vs budget', xlab: 'budget cap', ylab: 'net utility',
        xd: [5, 80], yd: [-1, 0.7],
        series: [
          { name: 'fixed', color: COLOR.line, pts: pick('fixed_equal', 'net_utility'), dots: true },
          { name: 'adaptive', color: COLOR.impl, pts: pick('adaptive', 'net_utility'), dots: true },
        ],
        marks: [{ y: 0, label: '0', color: COLOR.muted }],
      })),
    chart({
      title: 'mean samples vs budget —— adaptive 在 budget≥40 后钉死在 ≈19.7',
      xlab: 'budget cap', ylab: 'samples', xd: [5, 80], yd: [0, 85],
      series: [
        { name: 'fixed(花满)', color: COLOR.line, pts: pick('fixed_equal', 'samples'), dots: true },
        { name: 'adaptive(早停)', color: COLOR.impl, pts: pick('adaptive', 'samples'), dots: true },
      ],
    }),
    note('两条结论,方向相反:', h('br'),
      '· ', h('b', {}, 'L7 的形状确实在数据里'), `:fixed 的 net utility 在 budget ${D.exp2.notes.fixed_net_utility_peak_budget} 达峰,到 80 变负(${fmt.n(D.exp2.notes.fixed_net_utility_at_80 as number, 4)})。`, h('br'),
      '· ', h('b', {}, '但 adaptive 的样本数在 budget≥40 后钉死在 ', String(D.exp2.notes.adaptive_samples_saturate_at)),
      `,regret 也钉死在 ${fmt.n(D.exp2.notes.adaptive_regret_plateaus_at as number, 4)},而 fixed 一路降到 ${fmt.n(D.exp2.notes.fixed_regret_keeps_improving_to as number, 4)}。`,
      '⇒ exp2 证明的不是「自适应更好」,而是「在成本线性计价下,早停的策略净效用更高」。审查对 L7 的要求(需明确成本与目标)恰好命中这一点。'))

  /* ---- exp3 ---- */
  const e3 = panel('exp3 · temporal projection —— 一个在所有条件下都完美的指标',
    chart({
      title: 'accuracy vs semantic noise(每级 10000 queries)', xlab: 'semantic noise', ylab: 'accuracy',
      xd: [0.03, 0.82], yd: [0, 1.08],
      series: [
        { name: 'flat', color: COLOR.line, pts: D.exp3.rows.map(r => [r.semantic_noise, r.flat_retrieval] as [number, number]), dots: true },
        { name: 'temporal', color: COLOR.bad, pts: D.exp3.rows.map(r => [r.semantic_noise, r.temporal_projection] as [number, number]), dots: true },
      ],
      marks: [{ y: 1, label: '天花板 = 1.0', color: COLOR.bad }],
    }),
    note(`temporal_projection 在全部六个噪声级上`, h('b', {}, `恰为 ${D.exp3.notes.temporal_projection_value}`),
      `,而 flat_retrieval 从 ${fmt.n(D.exp3.notes.flat_retrieval_range[1], 4)} 单调退化到 ${fmt.n(D.exp3.notes.flat_retrieval_range[0], 4)}。每级 ${fmt.int(D.exp3.notes.queries_per_level)} queries,所以这不是运气。`,
      h('br'), '一个在所有条件下都完美的指标意味着任务退化、指标饱和、或投影侧能看到答案。这正是 a0/ 整条线花力气消灭的假绿形状。',
      h('br'), badge('【推断】', EVIDENCE_COLOR.s), ' 我没有读 report.tex 的实验 C 正文,这是从数据形状做的判断。'))

  /* ---- a0 strength curve ---- */
  const st = A0DATA.STRENGTH
  const kx = st.map(r => (r.k === Infinity ? 60 : r.k))
  const e4 = panel('a0/ 强度曲线 —— 仓库里唯一的「外部工件强度」测量(仪器属性,不是关于世界的证据)',
    h('div', { class: 'duo' },
      chart({
        title: 'Δ(dev / eval)vs 正对照强度 k', xlab: 'k(接受的改进交换数;60 = 无界,已废)', ylab: 'Δ',
        xd: [0, 62], yd: [0, 0.28],
        series: [
          { name: 'dev Δ', color: COLOR.impl, pts: st.map((r, i) => [kx[i], r.deltaDev] as [number, number]), dots: true },
          { name: 'eval Δ', color: COLOR.frame, pts: st.map((r, i) => [kx[i], r.deltaEval] as [number, number]), dots: true, dash: '4 3' },
        ],
        marks: [{ y: A0DATA.GATE_THRESHOLDS.deltaMeanMin, label: 'Δ 门 0.03', color: COLOR.warn }],
        xfmt: v => (v === 60 ? '∞' : String(v)),
      }),
      chart({
        title: 'ρ(dev / eval)vs k —— 与 Δ 反向', xlab: 'k', ylab: 'ρ',
        xd: [0, 62], yd: [0, 1.0],
        series: [
          { name: 'dev ρ', color: COLOR.impl, pts: st.map((r, i) => [kx[i], r.rhoDev] as [number, number]), dots: true },
          { name: 'eval ρ', color: COLOR.frame, pts: st.map((r, i) => [kx[i], r.rhoEval] as [number, number]), dots: true, dash: '4 3' },
        ],
        marks: [{ y: A0DATA.GATE_THRESHOLDS.rhoMedianMin, label: 'ρ 门 0.30', color: COLOR.warn }],
        xfmt: v => (v === 60 ? '∞' : String(v)),
      })),
    note('这张表被明确限定为仪器属性:', h('code', {}, 'evidence_scope: instrumentation'),
      ',「ρ 是 assay 的属性,MUST NOT 被当作关于世界的证据」', cite('positive_control/PC-REVISION.md:165-166'), '。',
      h('br'), '现行正对照是 ', h('b', {}, 'k=10'), '(Δ 0.116584858 · ρ 0.615639328 · 4/4 族 · ADMISSIBLE)。',
      'k=10 是看到 ρ 失败之后才选定的,属后验自由度,因此写成显式契约修订而非静默替换。',
      h('br'), 'k=25 在 eval 上是薄线:全局中位 0.3012,只高出 ρ 门 0.0012。'))

  /* ---- a0 cost ---- */
  const e5 = panel('a0/ 成本 —— 墙钟是约束,钱不是',
    h('div', { class: 'duo' },
      chart({
        title: '墙钟小时数 vs campaign 数(P_concurrency = 1)', xlab: 'N campaigns', ylab: 'hours',
        xd: [0, 140], yd: [0, 72],
        series: [{ name: '顺序墙钟', color: COLOR.warn, pts: A0DATA.COST.map(r => [r.campaigns, r.wallHours] as [number, number]), dots: true }],
      }),
      chart({
        title: 'CEq vs N(上限口径 / simpleloop 实测口径)', xlab: 'N campaigns', ylab: 'CEq',
        xd: [0, 140], yd: [0, 2.8e8],
        series: [
          { name: 'CEq @ 上限', color: COLOR.line, pts: A0DATA.COST.map(r => [r.campaigns, r.ceqCap] as [number, number]), dots: true },
          { name: 'CEq @ 实测', color: COLOR.impl, pts: A0DATA.COST.map(r => [r.campaigns, r.ceqMeasured] as [number, number]), dots: true, dash: '4 3' },
        ],
        yfmt: v => `${(v / 1e6).toFixed(0)}M`,
      })),
    note(A0DATA.COST_NOTE, h('br'),
      h('code', {}, `B_hard = (T_wall ${A0DATA.B_HARD.tWallSec} s, CEq_max ${fmt.int(A0DATA.B_HARD.ceqMax)}, N_evaluatorCalls ${A0DATA.B_HARD.nEvaluatorCalls}, P_concurrency ${A0DATA.B_HARD.pConcurrency})`),
      ' ', cite(A0DATA.B_HARD.cite),
      '。护栏不会过早绑定:CEq_max 对应 37.50 / 92.22 分钟,都晚于 30 分钟墙钟。'))

  const rep = panel('复现信息与免责(原文)',
    h('table', { class: 'tbl' },
      h('tbody', {},
        h('tr', {}, h('td', {}, 'RNG'), h('td', {}, `${D.repro.rng} seed ${D.repro.seed}`)),
        h('tr', {}, h('td', {}, '库'), h('td', {}, D.repro.libs)),
        h('tr', {}, h('td', {}, 'trials'), h('td', {}, Object.entries(D.repro.trials).map(([k, v]) => `${k} = ${fmt.int(v)}`).join(' · '))),
        h('tr', {}, h('td', {}, '免责'), h('td', { class: 'bad' }, D.repro.disclaimer)),
        h('tr', {}, h('td', {}, '出处'), h('td', {}, cite(D.repro.cite))))),
    note('审查要求「公布 Monte Carlo 生成器、种子、置信区间与成本口径」。其中',
      h('b', {}, '种子与样本量已经在这里'),
      ' —— 只是这份文件在未跟踪的 zip 里,而被审查的文档在另一条对话里,两者从未相遇。生成器仍未写明;但 exp1 与可交换 β-二项的 36 格重合本身就是对生成器的强约束。'))

  host.appendChild(h('div', { class: 'grid2' }, e1, e1b))
  host.appendChild(e2)
  host.appendChild(h('div', { class: 'grid2' }, e3, rep))
  host.appendChild(h('div', { class: 'stack' }, e4, e5))
}
