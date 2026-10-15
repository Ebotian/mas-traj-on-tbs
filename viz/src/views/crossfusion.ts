// crossfusion.ts —— 交叉融合:并集轨迹机械统计(数据并集 × 方法并集)的只读投影(零框架手写 SVG)。
//
// 数据由 scripts/build_crossfusion.py 从 harness/refs/crossfusion-2026-10-15/
// (features_union.jsonl + audit.json + paper_checks.json + arft.json)投影而来。
// 该实验为确定性、零模型调用管线:862 单元 = 我方 54 侧 + 8 臂 + AutoResearchEval 钉版 800 条;
// 一切数字是所收集工件的纯函数,check.py 四层全 PASS(逐字节可复现 + 不变式 + lab 对读 + 论文复算)。
// 定义与口径见 refs/README.md;我方逐轮轨迹原文回放在 #/handoff · #/tumor · #/microarch · #/tess。
import raw from '../data/crossfusion.json'
import { COLOR } from '../lib/palette.ts'
import { axisBottom, axisLeft, linear, s, text } from '../lib/svg.ts'
import { badge, cite, h, note, panel, stat, table } from '../lib/dom.ts'
import { tex, texBlock } from '../lib/tex.ts'

interface Invariant { name: string; value: number | string; want: number | string; ok: boolean }
interface CorpusRow { source: string; corpus: string; units: number; calls: number; masked: number; gaps_ok: number; p05: number }
interface FamRow {
  name: string; cn: string; units: number; calls: number; masked: number; gaps_ok: number
  ke_med: number | null; te_med: number | null; mrate_med: number | null
  mi_med: number | null; pa_med: number | null; p05: number
  kinds8: Record<string, number>
}
interface ArmRow { job: string; calls: number; masked: number; ke: number | null; te: number | null; kinds8: Record<string, number> }
interface ModelRow {
  name: string; units: number; calls: number; calls_ep: number
  ke_med: number | null; te_med: number | null; mrate_med: number | null; cache_med: number | null
  mi_med: number | null; pa_med: number | null; p05: number
  kinds8: Record<string, number>
}
interface FmtRow { source: string; format: string; units: number; gaps_basis: Record<string, number>; masked_n: number; cache_n: number; dur_n: number }
interface Pt { u: string; s: string; g: string; calls: number; ke: number; te: number; mr: number | null }
interface DecRow { u: string; s: string; g: string; calls: number; ke: number; ns: number; mi: number; p: number | null; ss: number; perm: number }
interface CalRow { u: string; s: string; g: string; calls: number; mi: number; pm: number; ex: number; mm: number | null; pri: number | null; b: number | null; mg: number | null; js: number | null }
interface DlRow { u: string; s: string; corpus: string; g: string; m: number; dla: number | null; dlb: number | null }
interface DlCorpus { n_a: number; med_a: number | null; pos_a: number; n_b: number; med_b: number | null; pos_b: number }
interface DlData {
  summary: { n_units: number; n_a: number; med_a: number | null; pos_a: number; n_b: number; med_b: number | null; pos_b: number; by_corpus: Record<string, DlCorpus> }
  pooled: { a1: number; a2: number; delta_a2: number; perm_p: number; k_perm: number }
  identity_max_diff: number
  per_unit: DlRow[]
}
interface Check { id: string; scope: string; claim: string; expected: unknown; actual: unknown; status: string; note: string }
interface Pillar { id: string; name: string; n: number; hit_sum: number; share_pct: number }
interface PatRow { id: string; name: string; stage: string; pillar: string; hit: number; pct: number }
interface CfData {
  meta: { source: string; script: string; are_revision: string; arxiv: string; note: string }
  totals: { units: number; ours_units: number; are_units: number; sides: number; arms: number; calls: number; ours_calls: number; are_calls: number; avg_are: number; hits_total: number; paper: Record<string, number>; n_above_ns: number; n_above_sm: number; n_pperm05: number; n_pa: number; mi_med: number | null; mi_max: number | null; n_p05: number; bh: number; ex_med: number | null; pm_med: number | null; mm_med: number | null; pri_med: number | null; b_med: number | null; mg_med: number | null; js_med: number | null }
  invariants: Invariant[]
  corpora: CorpusRow[]; families: FamRow[]; arms: ArmRow[]; models: ModelRow[]; format_cov: FmtRow[]
  scatter: Pt[]; decouple: DecRow[]; calib: CalRow[]; dl: DlData; checks: Check[]
  arft: { total_hits: number; pillars: Pillar[]; top: PatRow[] }
  notes: { defect_occurrences: number; nonstd: Record<string, number>; mehnet: string | null; unit_notes: { result_first: number; empty_file: number; no_calls: number } }
}
const D = raw as unknown as CfData

const KIND_ORDER = ['read', 'write', 'search', 'exec', 'wait', 'test', 'recover', 'other']
const KIND_COLOR: Record<string, string> = {
  read: COLOR.frame, write: COLOR.impl, search: COLOR.line, exec: COLOR.muted,
  wait: COLOR.warn, test: COLOR.find, recover: COLOR.ink, other: COLOR.rule,
}
const KIND_CN: Record<string, string> = {
  read: '读', write: '写', search: '检索', exec: '执行', wait: '等待', test: '测试', recover: '恢复', other: '其它',
}
const GRP_COLOR: Record<string, string> = {
  walkthrough: COLOR.line, tumor: COLOR.find, microarch: COLOR.frame, tess: COLOR.impl, arm: COLOR.ink,
}
const GRP_CN: Record<string, string> = { walkthrough: '走查', tumor: 'tumor', microarch: 'microarch', tess: 'tess', arm: '臂(单 agent)' }
const PILLAR_COLOR: Record<string, string> = { R1: COLOR.frame, R2: COLOR.line, R3: COLOR.find, R4: COLOR.warn }
const SCOPE_CN: Record<string, string> = { paper: '论文', card: '数据卡', data: '数据' }

const f2 = (v: number | null | undefined, d = 2): string => v == null ? '—' : v.toFixed(d)
const f4 = (v: number | null | undefined): string => v == null ? '—' : v.toFixed(4)
const pctf = (v: number | null | undefined, d = 1): string => v == null ? '—' : `${(v * 100).toFixed(d)}%`
const valf = (v: unknown): string => typeof v === 'string' ? v : JSON.stringify(v)

// ---- 公式卡:纯 LaTeX 源(复制按钮写入剪贴板的正是这一串;agent 可直接粘贴)----
const LATEX_KIND = 'H_{\\mathrm{kind}} = -\\sum_{k \\in \\mathcal{K}} p_k \\log_2 p_k'
const LATEX_TRANS = 'H_{\\mathrm{transition}} = -\\sum_{a \\in \\mathcal{K}} \\hat{\\pi}_a \\sum_{b \\in \\mathcal{K}} \\hat{P}_{ab} \\ln \\hat{P}_{ab}'
const LATEX_ALL = [
  '% crossfusion-2026-10-15 · 熵公式(纯 LaTeX 源)',
  '% (1) kind_entropy,单位 bit;p_k = 非首调用(c2..cn)中类别 k 的频率;K=8 类',
  LATEX_KIND,
  '% (2) transition_entropy,单位 nat;N_ab = 全链(c1→c2 … c_{n-1}→c_n)转移计数;',
  '%   pi_a = N_a / ΣN(经验边际);P_ab = (N_ab + 1) / (N_a + 8)(Dirichlet α=1,K=8)',
  LATEX_TRANS,
].join('\n')
const LATEX_H0 = 'H^{(0)}_{\\mathrm{transition}} = -\\sum_{a \\in \\mathcal{K}} \\hat{\\pi}_a \\sum_{b \\in \\mathcal{K}} \\hat{P}^{(0)}_{ab} \\ln \\hat{P}^{(0)}_{ab}, \\qquad \\hat{P}^{(0)}_{ab} = \\frac{N_{ab}}{N_a}'
const LATEX_MI = 'I_{\\mathrm{action}} = H_{\\mathrm{kind}} \\ln 2 - H^{(0)}_{\\mathrm{transition}} = I(C_t;\\, C_{t+1})'
const LATEX_PA = 'P_{\\mathrm{action}} = \\frac{I_{\\mathrm{action}}}{H_{\\mathrm{kind}} \\ln 2}'
const LATEX_SS = 'S_{\\mathrm{smooth}} = H^{(\\alpha=1)}_{\\mathrm{transition}} - H^{(0)}_{\\mathrm{transition}}'
const LATEX_DEC_ALL = [
  '% crossfusion-2026-10-15 · 解耦三量(纯 LaTeX 源)',
  '% (3) 无平滑条件转移熵,单位 nat;P0_ab = N_ab / N_a(经验条件分布,无先验)',
  LATEX_H0,
  '% (4) 经验行动互信息(一阶路径依赖强度),单位 nat',
  LATEX_MI,
  '% (5) 归一化行动可预测性,无量纲;H_kind=0(单类别流)时未定义',
  LATEX_PA,
  '% (6) 平滑敏感度,单位 nat;alpha=1 下 >= 0',
  LATEX_SS,
].join('\n')
const LATEX_EXC = 'I_{\\mathrm{excess}} = I_{\\mathrm{action}} - \\mathbb{E}_{\\mathrm{perm}}\\!\\left[\\, I(C_t;C_{t+1}) \\,\\right]'
const LATEX_MM = '\\widehat{H}_{\\mathrm{MM}} = \\widehat{H}_{\\mathrm{MLE}} + \\frac{K_{\\mathrm{obs}}-1}{2m}'
const LATEX_PRIOR = 'S_{\\max} = \\max_{a} \\frac{K\\alpha}{N_a + K\\alpha} = \\max_{a} \\frac{8}{N_a + 8}'
const LATEX_DL = '\\Delta L = L_0 - L_1, \\quad L_0 = -\\frac{1}{m_{\\mathcal{T}}}\\sum_{t \\in \\mathcal{T}} \\ln p_0(c_{t+1}), \\quad L_1 = -\\frac{1}{m_{\\mathcal{T}}}\\sum_{t \\in \\mathcal{T}} \\ln \\hat{p}_1(c_{t+1} \\mid c_t)'
const LATEX_A2 = '\\Delta A_2 = I(C_{t-1};\\, C_{t+1} \\mid C_t), \\qquad A_2 = A_1 + \\Delta A_2'
const LATEX_B = 'B = \\frac{\\sigma_\\tau - \\mu_\\tau}{\\sigma_\\tau + \\mu_\\tau}'
const LATEX_MEM = 'M = \\mathrm{Corr}(\\tau_i,\\, \\tau_{i+1})'
const LATEX_JS = 'JS(P, Q) = \\tfrac{1}{2} D_{\\mathrm{KL}}(P \\| M) + \\tfrac{1}{2} D_{\\mathrm{KL}}(Q \\| M), \\qquad M = \\tfrac{1}{2}(P + Q)'
const LATEX_CAL_ALL = [
  '% crossfusion-2026-10-15 · 校准公式(纯 LaTeX 源)',
  '% (7) 偏校正经验互信息,单位 nat;置换=固定 c1、洗牌 c2..cn,200 次',
  LATEX_EXC,
  '% (8) Miller–Madow 一阶修正,单位 nat;K_obs=c2..cn 的观测类别数,m=|c2..cn|',
  LATEX_MM,
  '% (9) alpha=1 先验质量占比上界(最稀疏转移行),无量纲',
  LATEX_PRIOR,
].join('\n')
const LATEX_PROBE_ALL = [
  '% crossfusion-2026-10-15 · 样本外与探针公式(纯 LaTeX 源)',
  '% (10) 样本外对数损失改善,单位 nat/转移;p0/p1 均 Laplace alpha=1',
  LATEX_DL,
  '% (11) 二阶主动信息存储增量(链式 A2 = A1 + ΔA2),单位 nat',
  LATEX_A2,
  '% (12) 突发性,无量纲,范围 [-1,1]',
  LATEX_B,
  '% (13) 时间记忆(相邻间隔一阶自相关),无量纲',
  LATEX_MEM,
  '% (14) Jensen–Shannon 散度(半程探针),单位 nat,上界 ln2',
  LATEX_JS,
].join('\n')

function copyBtn(latex: string, label = '复制 LaTeX'): HTMLButtonElement {
  const b = h('button', { class: 'copybtn', type: 'button' }, label)
  const flash = (t: string): void => {
    b.textContent = t
    window.setTimeout(() => { b.textContent = label }, 1400)
  }
  b.addEventListener('click', () => {
    const legacy = (): void => {
      try {
        const ta = document.createElement('textarea')
        ta.value = latex
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        const ok = document.execCommand('copy')
        document.body.removeChild(ta)
        flash(ok ? '已复制 ✓' : '复制失败')
      } catch { flash('复制失败') }
    }
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(latex).then(() => flash('已复制 ✓'), legacy)
    else legacy()
  })
  return b
}

function eqRow(num: string, latex: string): HTMLElement {
  return h('div', { class: 'eqrow' },
    h('div', { class: 'eq' }, texBlock(latex)),
    h('div', { class: 'eqtag' }, `(${num})`))
}

function latexSrc(latex: string): HTMLElement {
  return h('p', { class: 'latexsrc' }, '纯 LaTeX 源:', h('code', {}, latex), copyBtn(latex))
}

function hbar(label: string, v: number, vmax: number, color: string, sub: string): HTMLElement {
  return h('div', { class: 'ratio' },
    h('div', { class: 'ratio-h' }, h('b', {}, label), h('span', { class: 'ratio-pct' }, sub)),
    h('div', { class: 'bar' },
      h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * v / Math.max(1, vmax)))}%;background:${color}` })))
}

function kindStack(kinds: Record<string, number>): HTMLElement {
  const total = Math.max(1, KIND_ORDER.reduce((a, k) => a + (kinds[k] ?? 0), 0))
  const barDiv = h('div', { style: 'display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--rule);min-width:220px' })
  for (const k of KIND_ORDER) {
    const v = kinds[k] ?? 0
    if (!v) continue
    barDiv.appendChild(h('div', {
      style: `width:${(100 * v / total).toFixed(2)}%;background:${KIND_COLOR[k]}`,
      title: `${KIND_CN[k]}:${v}(${pctf(v / total, 1)})`,
    }))
  }
  return h('div', { style: 'flex:1 1 220px' }, barDiv)
}

function entropyScatter(): SVGElement {
  const W = 680, H = 280, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': '类别熵并集散点:边际 kind_entropy(bit) × 条件转移 transition_entropy(nat),每单元一点' })
  const xs = linear([0, 3], [M.l, W - M.r])            // 8 类理论上界 log2 8 = 3 bit
  const ys = linear([0, Math.log(8)], [H - M.b, M.t])  // ln 8 ≈ 2.079 nat
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  for (const p of D.scatter) {
    const ours = p.s === 'ours'
    g.appendChild(s('circle', {
      cx: xs(p.ke), cy: ys(p.te), r: ours ? 4.1 : 2.5,
      fill: ours ? (GRP_COLOR[p.g] ?? COLOR.muted) : COLOR.muted,
      opacity: ours ? 0.92 : 0.33,
    }, s('title', {}, `${p.u}:kind ${f4(p.ke)} bit · cond ${f4(p.te)} nat · 调用 ${p.calls}${p.mr != null ? ` · 掩蔽率 ${pctf(p.mr, 2)}` : ''}`)))
  }
  return g
}

function nsScatter(): SVGElement {
  const W = 680, H = 280, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': '无平滑散点:kind_entropy(bit) × H⁽⁰⁾(nat) 与 y=x·ln2 边界' })
  const xs = linear([0, 3], [M.l, W - M.r])
  const ys = linear([0, Math.log(8)], [H - M.b, M.t])
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  g.appendChild(s('line', { x1: xs(0), y1: ys(0), x2: xs(3), y2: ys(3 * Math.LN2),
    stroke: COLOR.bad, 'stroke-width': 1.6, 'stroke-dasharray': '6 4' }))
  g.appendChild(text(xs(2.92), ys(2.92 * Math.LN2) - 7, 'y = x·ln2(零路径依赖边界)',
    { 'text-anchor': 'end', class: 'lbl sm', fill: COLOR.bad }))
  for (const p of D.decouple) {
    const ours = p.s === 'ours'
    g.appendChild(s('circle', {
      cx: xs(p.ke), cy: ys(p.ns), r: ours ? 4.1 : 2.5,
      fill: ours ? (GRP_COLOR[p.g] ?? COLOR.muted) : COLOR.muted,
      opacity: ours ? 0.92 : 0.33,
    }, s('title', {}, `${p.u}:H_kind ${f4(p.ke)} bit · H⁽⁰⁾ ${f4(p.ns)} nat · I_action ${f4(p.mi)} nat${p.p != null ? ` · P_action ${f4(p.p)}` : ''} · perm p ${p.perm}`)))
  }
  return g
}

function paScatter(): SVGElement {
  const W = 680, H = 280, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': '长度 × 归一化可预测性:log10(调用数) × P_action' })
  const pts = D.decouple.filter(p => p.p != null)
  if (!pts.length) return g
  const xmax = Math.max(1.5, ...pts.map(p => Math.log10(p.calls))) * 1.04
  const xs = linear([Math.log10(2), xmax], [M.l, W - M.r])
  const ys = linear([0, 1], [H - M.b, M.t])
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => `10^${f2(v, 1)}`))
  for (const p of pts) {
    const ours = p.s === 'ours'
    g.appendChild(s('circle', {
      cx: xs(Math.log10(p.calls)), cy: ys(p.p as number), r: ours ? 4.1 : 2.5,
      fill: ours ? (GRP_COLOR[p.g] ?? COLOR.muted) : COLOR.muted,
      opacity: ours ? 0.92 : 0.33,
    }, s('title', {}, `${p.u}:n=${p.calls} · P_action ${f4(p.p)} · I_action ${f4(p.mi)} nat · perm p ${p.perm}${p.perm < 0.05 ? '(显著)' : ''}`)))
  }
  return g
}

function calibScatter(): SVGElement {
  const W = 680, H = 280, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': '校准:置换零均值 × 观察互信息(虚线 y=x)' })
  const vmax = Math.max(0.05, ...D.calib.map(p => Math.max(p.mi, p.pm))) * 1.08
  const xs = linear([0, vmax], [M.l, W - M.r])
  const ys = linear([0, vmax], [H - M.b, M.t])
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  g.appendChild(s('line', { x1: xs(0), y1: ys(0), x2: xs(vmax), y2: ys(vmax),
    stroke: COLOR.bad, 'stroke-width': 1.4, 'stroke-dasharray': '5 4' }))
  g.appendChild(text(xs(vmax) - 4, ys(vmax) + 12, 'y = x(零线)', { 'text-anchor': 'end', class: 'lbl sm', fill: COLOR.bad }))
  for (const p of D.calib) {
    const ours = p.s === 'ours'
    g.appendChild(s('circle', {
      cx: xs(p.pm), cy: ys(p.mi), r: ours ? 4 : 2.4,
      fill: ours ? (GRP_COLOR[p.g] ?? COLOR.muted) : COLOR.muted,
      opacity: ours ? 0.92 : 0.33,
    }, s('title', {}, `${p.u}:I_obs ${f4(p.mi)} · E[零] ${f4(p.pm)} · I_excess ${f4(p.ex)} nat · MM ${f4(p.mm)} nat · 先验占比 ${f4(p.pri)}${p.b != null ? ` · B ${f4(p.b)} · M ${f4(p.mg)} · JS ${f4(p.js)}` : ''}`)))
  }
  return g
}

function legend(): HTMLElement {
  const row = h('p', { class: 'note' }, '图例:')
  row.appendChild(h('span', { style: `display:inline-block;width:7px;height:7px;border-radius:50%;background:${COLOR.muted};opacity:.5;margin:0 4px 0 10px;vertical-align:middle` }))
  row.appendChild(h('span', {}, `are 800 条(灰,小点)`))
  for (const k of ['walkthrough', 'tumor', 'microarch', 'tess', 'arm']) {
    row.appendChild(h('span', { style: `display:inline-block;width:8px;height:8px;border-radius:50%;background:${GRP_COLOR[k]};margin:0 4px 0 10px;vertical-align:middle` }))
    row.appendChild(h('span', {}, GRP_CN[k]))
  }
  return row
}

export function render(host: HTMLElement): void {
  const T = D.totals
  host.appendChild(h('p', { class: 'lede' },
    '外部 ', h('b', {}, 'AutoResearchEval'), h('span', { class: 'cite' }, ` @${D.meta.are_revision.slice(0, 8)}`),
    '(PrentisAI,CC-BY-4.0,论文 arXiv ', cite(D.meta.arxiv), ')的 ', h('b', {}, '800 条真实轨迹'),
    '与我方 ', h('b', {}, `${T.sides} 侧 + ${T.arms} 臂`), '取', h('b', {}, '数据并集'), ',用覆盖全部单元的',
    h('b', {}, '统一机械统计'), '逐条计算(8 类工具分类 · 边际/条件熵 · 节律 · 掩蔽错误 · 缓存);同时对论文与数据卡的',
    h('b', {}, '可机核数字'), '做机械复算并登记偏差。一切数字是所收集工件的纯函数、', h('b', {}, '零模型调用'), ',由 ',
    h('code', {}, 'scripts/build_crossfusion.py'), ' 投影;实验本体在 ',
    cite('harness/refs/crossfusion-2026-10-15/'), '(check.py 四层全 PASS)。'))

  host.appendChild(panel(`概览 · ${T.units} 单元 / ${T.calls.toLocaleString('en-US')} 次工具调用`,
    h('div', { class: 'stats' },
      stat(String(T.units), `单元(${T.are_units} are + ${T.ours_units} ours:${T.sides} 侧/${T.arms} 臂)`),
      stat(T.calls.toLocaleString('en-US'), `工具调用(ours ${T.ours_calls.toLocaleString('en-US')} + are ${T.are_calls.toLocaleString('en-US')})`),
      stat(String(T.avg_are), 'are 均值调用/跑(论文「92.3」)', COLOR.frame),
      stat(T.hits_total.toLocaleString('en-US'), '论文 45 模式复算 HIT 总量(Table 12 Σ)', COLOR.find),
      stat(`PASS ${T.paper.PASS}`, `论文复算;数据卡登记偏差 ${T.paper.MISMATCH} · RECORD ${T.paper.RECORD}`, COLOR.good)),
    h('p', { class: 'note strong' }, '不变式(check.py 口径,全部独立复算):'),
    h('p', { class: 'note' }, ...D.invariants.map(inv =>
      badge(`${inv.name} = ${inv.value}${inv.ok ? '' : ` ≠ ${inv.want}`}`, inv.ok ? COLOR.good : COLOR.bad))),
    note('数据并集口径:are 钉版 revision ', cite(D.meta.are_revision.slice(0, 12)), '…(809 文件 / 721,929,474 B 逐文件核对,0 坏);',
      '数据本体不入本仓(仅派生统计);ours 侧=同一作业目录,与夜班轨迹特征实验逐字段一致。',
      '「并集」= 数据取并集、方法取并集且每个方法覆盖每个单元;格式不可得的字段记 null 并注明,不插补。')))

  host.appendChild(panel(`论文数字复算 · ${D.checks.length} 条(PASS ${T.paper.PASS} / 登记偏差 ${T.paper.MISMATCH} / RECORD ${T.paper.RECORD})`,
    h('div', { class: 'scroll' }, table(
      ['id', '范围', '声明', 'expected', 'actual', 'status'],
      D.checks.map(c => [c.id, SCOPE_CN[c.scope] ?? c.scope, c.claim, valf(c.expected), valf(c.actual),
        badge(c.status, c.status === 'PASS' ? COLOR.good : c.status === 'MISMATCH' ? COLOR.warn : COLOR.muted)]))),
    note('口径注记:Table 12 的 HIT% 列用 half-even 舍入(实测 5 处 .25 边界全下舍);逐模型 top-10 的并列名次按模式 ID 字母序',
      '(Table 14–21 与 Table 13 重算逐模型全等,8/8)。',
      h('b', {}, '登记偏差全部在数据卡侧'), ':卡片「559 / 31 tasks / 247(195 success)」vs 磁盘 560 / 30 / 240(188 success),',
      '「52 non-success」相符、卡片自数 559+247=806 ≠ 论文 800(磁盘 560+240=800 与论文一致);4 条偏差原样留档、不修卡。',
      h('b', {}, '复算边界'), ':论文的 LLM-judge 侧数字(IAA κ、Table 2)与 45 模式逐轨迹标注未发布工件,不在机械复算范围。')))

  host.appendChild(panel('类别熵 · 并集散点 边际 kind_entropy(bit) × 条件转移 transition_entropy(nat)',
    entropyScatter(),
    legend(),
    note('两轴非独立(2026-10-15 复核):去掉平滑后恒有 H⁽⁰⁾ ≤ H_kind·ln2,差值即经验互信息 I_action——正相关首先是这一数学约束;',
      '本卡为 α=1 平滑版:相对边界 y = x·ln2 越出的点有 ', h('b', {}, String(D.totals.n_above_sm)),
      ' 个(超出量 = S_smooth − I_action),单类别竖线与越界点都是平滑底噪,不是行为差异。',
      `${D.scatter.length}/${D.totals.units} 单元入图(8 个 0/1 调用单元无 c₂..cₙ,记 null)。`,
      '无平滑视角、长度维度与三量定义分别见后文散点 II、散点 III 与两张公式卡。')))

  host.appendChild(panel('散点 II · 无平滑:kind_entropy × H⁽⁰⁾(nat),互信息 = 到边界的距离',
    nsScatter(),
    legend(),
    note('无平滑版中每点必在 y = x·ln2 之下(该边界即「零路径依赖」线),到边界的竖直距离就是 I_action(经验互信息);',
      '实测越界 ', h('b', {}, String(D.totals.n_above_ns)), ' 个(恒等式保证为 0)。',
      '全 854 单元 I_action 中位 ', h('b', {}, f4(D.totals.mi_med)), ' nat、最大 ', h('b', {}, f4(D.totals.mi_max)), ' nat。',
      '与上一卡对照:同一批轨迹换无平滑口径后,「正相关」被拆成(y ≤ 边界)+(距离 = 路径依赖信息)两项。')))

  host.appendChild(panel('散点 III · 长度 × 归一化行动可预测性 log₁₀(n) × P_action',
    paScatter(),
    legend(),
    note('92 条单类别流(gpt-5-mini)H_kind = 0 ⇒ P_action 未定义、不绘(记 null 不设零);',
      '保频置换检验(200 次,crc32 定种):', h('b', {}, `${D.totals.n_pperm05}/${D.totals.n_pa}`),
      ' 个单元 p<0.05,路径依赖超过随机基线;其中 open-ended ',
      h('b', {}, String(D.corpora.find(c => c.corpus === 'open-ended')?.p05 ?? '—')), '/560、optimization ',
      h('b', {}, String(D.corpora.find(c => c.corpus === 'optimization')?.p05 ?? '—')), '/240。',
      'P_action = 1 表示下一步类别由上一步类别确定,0 表示上一步不提供信息;与 n 无单调关系。')))

  host.appendChild(panel('熵公式(论文级口径)· 式环境 + 符号 + 数据来源 + 意义',
    note('本卡是两量的定义性规格(specification);数值由管线逐单元现算并经四层验收:',
      h('code', {}, 'extract_cross.py::ring_core'), ' → ', h('code', {}, 'features_union.jsonl'), ' → ',
      h('code', {}, 'build_crossfusion.py'), ' → 本页;验收见 ', cite('crossfusion-2026-10-15/check.py'), '。'),
    h('p', { class: 'note strong' }, '式 (1) 类别边际熵 · kind_entropy(单位 bit)'),
    eqRow('1', LATEX_KIND),
    h('div', { class: 'scroll' }, table(
      ['符号', '含义', '取值与口径', '数据来源'],
      [
        [tex('\\mathcal{K}'), '工具类别集合(8 类)', 'read · write · search · exec · wait · test · recover · other', 'extract_cross.py 的 KINDS8 与各源名称映射表'],
        [tex('c_1, \\dots, c_n'), '该单元的工具调用类别序列', 'c₁ 不计入式 (1) 的样本(首调惯例=读题);n=调用总数', 'features_union.jsonl 的 kinds(7 种日志格式统一后的序列)'],
        [tex('p_k'), '类别 k 在 c₂..cₙ 中的频率', 'p_k = n_k / |c₂..cₙ|;Σ_k p_k = 1', 'ring_core() 现算;不可得字段记 null 不插补'],
        [tex('H_{\\mathrm{kind}}'), '类别边际熵(一个标量)', '熵域 [0, log₂8 = 3];单类别 ⇒ 恰为 0;8 类均匀 ⇒ 3', '落盘字段 kind_entropy(6 位小数)'],
      ])),
    latexSrc(LATEX_KIND),
    note('意义:工具多样性的边际度量——值越高,轨迹的类别构成越均匀;单类别流(如 gpt-5-mini 的纯 exec 92 条)恰为 0。',
      '口径出处:2026-10-15「类别熵更名」裁定(边际熵按数学实际命名),见 ', cite('traj-features-2026-10-14/README.md'), '。'),
    h('p', { class: 'note strong' }, '式 (2) 条件转移熵 · transition_entropy(单位 nat)'),
    eqRow('2', LATEX_TRANS),
    h('div', { class: 'scroll' }, table(
      ['符号', '含义', '取值与口径', '数据来源'],
      [
        [tex('N_{ab}'), '相邻转移 a→b 的计数', '全链含 c₁→c₂ 至 c_{n−1}→cₙ;Σ_{ab} N_{ab} = n−1', 'ring_core() 由 kinds 序列现算'],
        [tex('\\hat{\\pi}_a'), '转移位点的经验边际', 'π̂_a = N_a / Σ_b N_b,其中 N_a = Σ_b N_ab', '同上'],
        [tex('\\hat{P}_{ab}'), '平滑后的转移概率', 'P̂_ab = (N_ab + 1) / (N_a + 8);Dirichlet α=1、K=8', '同上'],
        [tex('H_{\\mathrm{transition}}'), '条件转移熵(一个标量)', '熵域 [0, ln 8 ≈ 2.079];α=1 平滑下纯单类别流仍有正底噪(随调用数 n 递减)', '落盘字段 transition_entropy(6 位小数)'],
      ])),
    latexSrc(LATEX_TRANS),
    note('意义:在类别构成之上再编码顺序结构——同一类别直方图,转移越不确定,H 越高;',
      '定义出自文档 §4.2(条件转移熵),α=1 为默认口径,见 ', cite('crossfusion-2026-10-15/README.md'), ' 与 traj-features README。'),
    h('p', { class: 'latexsrc' }, copyBtn(LATEX_ALL, '复制全部(两式 + 口径注释行)'),
      '—— 写入剪贴板的是纯 LaTeX 文本,注释行以 % 开头,粘进论文或 agent 对话均可直接编译/引用。')))

  host.appendChild(panel('解耦三量(论文级口径)· 式环境 + 符号 + 数据来源 + 意义',
    note('本卡承接式 (1)(2),把「平滑版转移熵」拆成可分别估读的三件:无平滑条件熵 H⁽⁰⁾、经验互信息 I_action、平滑敏感度 S_smooth;',
      '数值同管线逐单元现算,四层验收含解耦不变式(恒等式 / 非负 / 单类别边界 / 置换确定性)。'),
    h('p', { class: 'note strong' }, '式 (3) 无平滑条件转移熵 · trans_entropy_ns(单位 nat)'),
    eqRow('3', LATEX_H0),
    h('p', { class: 'note strong' }, '式 (4) 经验行动互信息(一阶路径依赖强度)· mi_action(单位 nat)'),
    eqRow('4', LATEX_MI),
    h('p', { class: 'note strong' }, '式 (5) 归一化行动可预测性 · p_action(无量纲,[0,1])'),
    eqRow('5', LATEX_PA),
    h('p', { class: 'note strong' }, '式 (6) 平滑敏感度 · s_smooth(单位 nat)'),
    eqRow('6', LATEX_SS),
    h('div', { class: 'scroll' }, table(
      ['符号', '含义', '取值与口径', '数据来源'],
      [
        [tex('H^{(0)}_{\\mathrm{transition}}'), '无平滑条件转移熵', 'P̂⁽⁰⁾_ab = N_ab/N_a(经验条件分布,不设先验);域 [0, ln 8]', 'ring_core() 现算(trans_entropy_ns 字段)'],
        [tex('I_{\\mathrm{action}}'), '经验行动互信息(路径依赖强度)', '= H_kind·ln2 − H⁽⁰⁾ = Î(C_t;C_{t+1});由定义恒 ≥ 0', 'mi_action 字段(恒等式独立对拍最大差 1.7e-07)'],
        [tex('P_{\\mathrm{action}}'), '归一化行动可预测性', '= I_action/(H_kind·ln2);H_kind=0(单类别流)⇒ 未定义(null),不设零', 'p_action 字段;92 个单元为 null'],
        [tex('S_{\\mathrm{smooth}}'), '平滑敏感度', '= 平滑熵 − H⁽⁰⁾;α=1 下恒 ≥ 0;越大 = 读数越依赖伪计数(短序列/尖分布)', 's_smooth 字段'],
        [tex('p_{\\mathrm{perm}}'), '保频置换检验单侧 p', 'k=200 次洗牌(保留类别频数),crc32(seq) 定种;= (1+#{I_perm ≥ I_obs})/(1+k)', 'mi_perm_p 字段;显著(p<0.05)631/762'],
        [tex('m = n - 1'), '转移位点数', '全链 c₁→c₂ … c_{n−1}→cₙ;π̂_a = N_a/m', 'calls_total − 1'],
      ])),
    latexSrc(LATEX_H0), latexSrc(LATEX_MI), latexSrc(LATEX_PA), latexSrc(LATEX_SS),
    note('意义:H⁽⁰⁾ = 「已知上一步类别后,下一步类别还剩多少不确定性」;I_action 是其相对边际 H_kind·ln2 的信息削减(统计路径依赖,非因果);',
      'P_action ∈ [0,1] 给出跨单元可比的强度;S_smooth 是测量可信度——它大而 I_action 小时,平滑版的熵读数主要是底噪。',
      '关系(由定义直接推出):H⁽⁰⁾ = H_kind·ln2 − I_action;平滑版 = H⁽⁰⁾ + S_smooth。'),
    note('口径出处:2026-10-15 外部复核建议,逐条核对后落地(', cite('crossfusion-2026-10-15/README.md'), '「解耦指标」节;',
      '对照项:纯单类别底噪 2.0432→0.0550(m=1→999)与实现逐位一致;独立联合 MI 对拍见上表)。'),
    h('p', { class: 'latexsrc' }, copyBtn(LATEX_DEC_ALL, '复制全部(式 (3)–(6) + 口径注释行)'),
      '—— 同上:纯 LaTeX 文本,可直接编译/引用。')))

  host.appendChild(panel('校准 · 观察互信息 vs 置换零分布(I_excess)',
    calibScatter(),
    legend(),
    note('横轴 = 同频重排(固定 c₁、洗牌 c₂..cₙ,200 次)的平均互信息;纵轴 = 观察值;红色虚线 y = x(零线)。',
      '点在上方 = I_excess > 0(观察高于偶然);下方 ', h('b', {}, String(D.calib.filter(p => p.ex < 0).length)),
      ' 个 = 低于偶然(合法取值,不做截断);',
      'I_excess 中位 ', h('b', {}, f4(D.totals.ex_med)), ' nat(置换零均值中位 ', f4(D.totals.pm_med), ' nat);',
      '置换显著 ', h('b', {}, `${D.totals.n_p05}/${D.calib.length}`), ',BH-FDR q=0.05 后 ', h('b', {}, `${D.totals.bh}/${D.calib.length}`), '。',
      'MM 修正中位 ', h('b', {}, f4(D.totals.mm_med)), ' nat;先验占比上界中位 ', f4(D.totals.pri_med), '(最稀疏转移行里 α=1 先验占的混合质量)。')))

  host.appendChild(panel('校准公式(论文级口径)· 式环境 + 符号 + 数据来源 + 意义',
    note('本卡承接式 (1)–(6),把「读数的可信度」写成可复算的三件:偏校正 I_excess、熵的有限样本修正 MM、平滑先验占比上界。',
      '数值同管线现算,check.py 以 854/854/854 覆盖钉数 + 逐字节复现。'),
    h('p', { class: 'note strong' }, '式 (7) 偏校正经验互信息 · mi_excess(nat)'),
    eqRow('7', LATEX_EXC),
    h('p', { class: 'note strong' }, '式 (8) Miller–Madow 一阶修正 · mm_delta_nat(nat)'),
    eqRow('8', LATEX_MM),
    h('p', { class: 'note strong' }, '式 (9) 平滑先验占比上界 · prior_share_max(无量纲)'),
    eqRow('9', LATEX_PRIOR),
    h('div', { class: 'scroll' }, table(
      ['符号', '含义', '取值与口径', '数据来源'],
      [
        [tex('I_{\\mathrm{excess}}'), '偏校正互信息', '= I_obs − E_perm[I];可为负 = 观察低于偶然;置换 = 固定 c₁、洗牌 c₂..cₙ(200 次,crc32 定种)', 'mi_excess 字段;中位 0.1475 nat'],
        [tex('K_{\\mathrm{obs}}'), '(8) 观测类别数', 'c₂..cₙ 中出现的 distinct 类数(≤ 8)', 'ring_core() 现算'],
        [tex('m'), '(8) 样本量', '= |c₂..cₙ| = 调用数 − 1', 'calls_total − 1'],
        [tex('S_{\\max}'), '最稀疏转移行的 α=1 先验质量占比', '= max_a 8/(N_a+8);→1 意味着该行读数几乎全由先验驱动', 'prior_share_max 字段;中位 0.727'],
      ])),
    latexSrc(LATEX_EXC), latexSrc(LATEX_MM), latexSrc(LATEX_PRIOR),
    note('意义:报告路径依赖用 I_excess(扣掉有限样本偶然),不用原值;',
      'MM 修正把类别熵的向下偏差补齐(本管线自己的校准列,与论文表格口径无关);',
      '先验占比直接量化「平滑依赖」——它与 S_smooth 一内(逐行)一外(全局)互相印证。'),
    h('p', { class: 'latexsrc' }, copyBtn(LATEX_CAL_ALL, '复制全部(式 (7)–(9) + 口径注释行)'),
      '—— 纯 LaTeX 文本,可直接编译/引用。')))

  host.appendChild(panel('样本外与探针 · ΔL / ΔA₂ / B / M / JS',
    h('p', { class: 'note strong' }, '样本外对数损失改善(Laplace α=1;nat/转移,>0 = 历史模型省编码):'),
    h('div', { class: 'scroll' }, table(
      ['语料', 'ΔL_a n', 'ΔL_a 中位', '>0', 'ΔL_b n', 'ΔL_b 中位', '>0'],
      [
        ['全部', String(D.dl.summary.n_a), f4(D.dl.summary.med_a), String(D.dl.summary.pos_a),
          String(D.dl.summary.n_b), f4(D.dl.summary.med_b), String(D.dl.summary.pos_b)],
        ...Object.entries(D.dl.summary.by_corpus).map(([k, r]) =>
          [k, String(r.n_a), f4(r.med_a), String(r.pos_a), String(r.n_b), f4(r.med_b), String(r.pos_b)]),
      ])),
    note('ΔL_a = 单元自身前半(train)→后半(test);ΔL_b = 只用【其他任务】的池化拟合(防同题泄漏),在本单元全部转移上测试。',
      '读法:ΔL_b 中位 ', h('b', {}, f4(D.dl.summary.med_b)), ' nat 且 ', h('b', {}, `${D.dl.summary.pos_b}/${D.dl.summary.n_b}`),
      ' >0——一阶历史在跨任务留出下普遍可迁移;ΔL_a 中位仅 ', f4(D.dl.summary.med_a), ' nat(', `${D.dl.summary.pos_a}/${D.dl.summary.n_a}`,
      ' >0)——单元内前段不足以预测后段(轨迹非平稳),两者之差本身就是「同题统计比跨题统计更乐观」的量化。'),
    h('p', { class: 'note strong' }, '池化主动信息存储(AIS;全 862 单元,Laplace α=1):'),
    h('div', { class: 'stats' },
      stat(f4(D.dl.pooled.a1), 'A₁ = I(C_t;C_{t+1})(nat)', COLOR.frame),
      stat(f4(D.dl.pooled.a2), 'A₂ = I(C_{t−1},C_t;C_{t+1})(nat)', COLOR.frame),
      stat(`+${f4(D.dl.pooled.delta_a2)}`, `ΔA₂ = A₂−A₁(保频置换 p=${D.dl.pooled.perm_p})`, COLOR.good),
      stat(`+${f2(100 * D.dl.pooled.delta_a2 / D.dl.pooled.a1)}%`, '二阶历史相对一阶的额外信息占比', COLOR.impl)),
    h('p', { class: 'note strong' }, '时间与阶段探针(含排队/采样混杂,仅口径可得者):'),
    h('div', { class: 'scroll' }, table(
      ['探针', 'n', '中位', '口径'],
      [
        ['B 突发性', String(D.calib.filter(p => p.b != null).length), f4(D.totals.b_med), '(σ−μ)/(σ+μ);≥4 个时间戳间隔;−1 = 完全规则'],
        ['M 时间记忆', String(D.calib.filter(p => p.mg != null).length), f4(D.totals.mg_med), '相邻间隔一阶自相关;>0 = 长后仍长'],
        ['JS 半程探针', String(D.calib.filter(p => p.js != null).length), f4(D.totals.js_med), '前缀半 vs 后置半类别分布差异(上界 ln2)'],
      ])),
    note('读数按「含基础设施混杂」引用(B/M 里同时有工具排队与采样间隔);JS 上界 ln2 ≈ 0.693——阶段间分布确实在变,但探针不区分「科研阶段」与「机械前后缀」。')))

  host.appendChild(panel('样本外与探针公式(论文级口径)· 式环境 + 符号 + 数据来源 + 意义',
    note('本卡定义样本外判据与三个探针;实现见 ', h('code', {}, 'dl_test.py'), ' 与 ', h('code', {}, 'ring_core()'), '。'),
    h('p', { class: 'note strong' }, '式 (10) 样本外对数损失改善 · ΔL(nat/转移)'),
    eqRow('10', LATEX_DL),
    h('p', { class: 'note strong' }, '式 (11) 二阶主动信息存储增量 · ΔA₂(nat)'),
    eqRow('11', LATEX_A2),
    h('p', { class: 'note strong' }, '式 (12) 突发性 · burstiness_b'),
    eqRow('12', LATEX_B),
    h('p', { class: 'note strong' }, '式 (13) 时间记忆 · gap_memory_m'),
    eqRow('13', LATEX_MEM),
    h('p', { class: 'note strong' }, '式 (14) 阶段探针 · js_half(nat)'),
    eqRow('14', LATEX_JS),
    h('div', { class: 'scroll' }, table(
      ['符号', '含义', '取值与口径', '数据来源'],
      [
        [tex('L_0,\\, L_1'), '(10) 两模型测试损失', 'p₀ = 训练目标边际;p̂₁ = 训练逐源行条件分布(均 α=1);𝒯 = 测试转移集', 'dl_test.py;钉数 ΔL_a n=765 / ΔL_b n=833'],
        [tex('A_1,\\, A_2'), '(11) AIS 一阶/二阶', 'A₁ = I(C_t;C_{t+1});A₂ = I(C_{t−1},C_t;C_{t+1});链式 A₂ = A₁ + ΔA₂;全单元池化,α=1', 'dl_test.py::pooled;置换 p = 0.004975'],
        [tex('\\Delta A_2'), '(11) 二阶增量', '= I(C_{t−1};C_{t+1} | C_t);>0 = 两步前行动仍含独立预测信息', '同上;+0.0529 nat'],
        [tex('\\mu_\\tau,\\, \\sigma_\\tau'), '(12/13) 间隔统计', '相邻调用时间戳间隔的均值/样本标准差(≥4 间隔才报)', 'ring_core();n = 687'],
        [tex('P,\\, Q,\\, M'), '(14) 两半类别分布', 'P/Q = 前半/后半类别频率;M = 均值分布;上界 ln2', 'ring_core();n = 839'],
      ])),
    latexSrc(LATEX_DL), latexSrc(LATEX_A2), latexSrc(LATEX_B), latexSrc(LATEX_MEM), latexSrc(LATEX_JS),
    note('意义:ΔL 回答「历史结构能否泛化到未来」——训练集版的恒等式 L₀−L₁ = Î 已在自检里钉住(差 0),所以价值全在样本外;',
      'ΔA₂ 把一阶记忆扩到二步上下文,A₂ 只在池化层面可估(单元内 8³ 上下文过稀);B/M 是时间维、JS 是阶段维的机械化探针。'),
    note('文献锚点:Gneiting & Raftery (2007, JASA)· Lizier (2014, Frontiers)· Goh & Barabási (2008, EPL)· Lin (1991, IEEE-IT);',
      '数值均已在本管线复算/核对(见 README「校准与探针」节);正式引用前按 check_citations 钉版。'),
    h('p', { class: 'latexsrc' }, copyBtn(LATEX_PROBE_ALL, '复制全部(式 (10)–(14) + 口径注释行)'),
      '—— 纯 LaTeX 文本,可直接编译/引用。')))

  const models = [...D.models].sort((a, b) => b.calls_ep - a.calls_ep)
  const vmaxA = models.length ? models[0].calls_ep : 1
  const fams = [...D.families]
  fams.forEach(f => { (f as FamRow & { per_side: number }).per_side = f.units ? f.calls / f.units : 0 })
  const vmaxB = Math.max(1, ...fams.map(f => (f as FamRow & { per_side: number }).per_side), ...D.arms.map(a => a.calls))
  host.appendChild(panel('调用强度与工具构成',
    h('p', { class: 'note strong' }, `AutoResearchEval 逐模型(每跑调用;柱右为其 8 类构成):`),
    ...models.map(m => h('div', { class: 'ratio' },
      h('div', { class: 'ratio-h' }, h('b', {}, m.name), h('span', { class: 'ratio-pct' }, `${f2(m.calls_ep)}/跑 · 共 ${m.calls.toLocaleString('en-US')}`)),
      h('div', { style: 'display:flex;gap:14px;align-items:center;flex-wrap:wrap' },
        h('div', { class: 'bar', style: 'flex:1 1 240px' },
          h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * m.calls_ep / Math.max(1, vmaxA)))}%;background:${COLOR.frame}` })),
        kindStack(m.kinds8)))),
    h('p', { class: 'note strong' }, '我方(每侧/每臂调用):'),
    ...fams.map(f => {
      const per = (f as FamRow & { per_side: number }).per_side
      return h('div', { class: 'ratio' },
        h('div', { class: 'ratio-h' }, h('b', {}, `${f.cn}(${f.units} 侧)`), h('span', { class: 'ratio-pct' }, `${f2(per)}/侧 · 共 ${f.calls.toLocaleString('en-US')} · 掩蔽 ${f.masked}`)),
        h('div', { style: 'display:flex;gap:14px;align-items:center;flex-wrap:wrap' },
          h('div', { class: 'bar', style: 'flex:1 1 240px' },
            h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * per / vmaxB))}%;background:${COLOR.impl}` })),
          kindStack(f.kinds8)))
    }),
    h('div', { class: 'scroll' }, table(
      ['臂', '调用', '掩蔽', 'kind_entropy', 'trans_entropy'],
      D.arms.map(a => [a.job, String(a.calls), String(a.masked), f4(a.ke), f4(a.te)]))),
    note('两侧口径对齐后的对照:are 逐模型 19.4–200.8 调用/跑(gpt-5-mini 最浅、minimax-m3 最深);',
      '我方家族 93.6–327.5 调用/侧(走查最浅、tess/tumor 最深),臂 68–136/条。',
      '工具构成条=各组的 8 类合计(图例同 #/features:读/写/检索/执行/等待/测试/恢复/其它)。')))

  host.appendChild(panel('格式覆盖 · 方法并集的能力矩阵(7 种日志格式 × 同一套统计)',
    h('div', { class: 'scroll' }, table(
      ['格式', '单元', 'gaps(basis)', 'masked 可判', 'cache', 'duration'],
      D.format_cov.map(f => [`${f.source}/${f.format}`, String(f.units),
        Object.keys(f.gaps_basis).length ? Object.entries(f.gaps_basis).map(([k, v]) => `${k} ${v}`).join(' · ') : '—',
        String(f.masked_n), String(f.cache_n), String(f.dur_n)]))),
    note('每个方法覆盖每个单元:调用/名表/8 类/掩蔽 7 种格式全可算;gaps 只在有时间戳的格式可算(claude result_ts/call_ts、gemini call_ts、ours call_ts/step_ts);',
      'cache 与 duration 按字段可得性(见右三列)。不可得=null,不插补——覆盖率的空白处即数据格式的边界。')))

  const A = D.arft
  host.appendChild(panel(`45 模式 × 四支柱参照(论文失败分析) · 共 ${A.total_hits.toLocaleString('en-US')} hits`,
    ...A.pillars.map(p => hbar(`${p.id} ${p.name}`, p.share_pct, Math.max(...A.pillars.map(x => x.share_pct)) * 1.06,
      PILLAR_COLOR[p.id] ?? COLOR.muted, `${p.n} 模式 · ${p.hit_sum.toLocaleString('en-US')} hits · ${f2(p.share_pct)}%`)),
    h('p', { class: 'note strong' }, 'Table 12 前 12 名(HIT / 出现率):'),
    ...A.top.map(p => hbar(`${p.id} ${p.name}`, p.hit, A.top[0].hit, PILLAR_COLOR[p.pillar] ?? COLOR.muted,
      `${p.hit} · ${f2(p.pct)}%`)),
    note('支柱归属=P表 Table 3;R1+R2+R3=92.1%(认知三支柱),R4 最高仅 C.4 第 26/45。',
      '参照表全文(45 模式 × 支柱/阶段/全量 HIT/逐模型向量)见 ', cite('arft.json'), ';',
      '本页不复现 judge 侧数字(κ/Table 2),亦不对 45 模式做 LLM 标注——模式统计只作参照坐标。')))

  const N = D.notes
  host.appendChild(panel('口径与已知问题(全部可审计)',
    h('div', { class: 'scroll' }, table(
      ['项', '值', '出路'],
      [
        ['ours 侧表外工具名(归 other,与 lab 一致)',
          Object.entries(N.nonstd).map(([k, v]) => `${k}×${v}`).join(' · '),
          'audit.ours_side_nonstandard(9 次,不影响任何统计量)'],
        ['工件名 __unparsedToolInput(claude 流,均 qwen3.7-max)',
          `${N.defect_occurrences} 处`,
          '归 other;实例路径见 audit.defect_occurrences'],
        ['gemini stats.tool_calls 对账', `27 文件,1 处数据自相矛盾:${N.mehnet ?? '—'}`,
          '文件自身 122 vs 行内 86;非适配错误,原样登记'],
        ['opus-4.8 优化集文件首行为 result 行', `${N.unit_notes.result_first} 个(其中 ${N.unit_notes.no_calls} 个单行 0 调用)`,
          'notes=result-first;仍按全文解析'],
        ['0 行空文件', `${N.unit_notes.empty_file} 个`, 'notes=empty-file;仍计为一个轨迹单元以保 800 完整'],
        ['模型目录名归并', 'sonnet-5→claude-sonnet-5 · codex-gpt5mini→gpt-5-mini',
          'meta.model_dir 保留原目录名;单元名保留磁盘路径'],
      ])),
    note('复跑:', h('code', {}, 'cd harness/refs/crossfusion-2026-10-15 && python3 check.py'),
      '(四层:逐字节复现 / 不变式 / 与夜班实验 lab 对读 / 论文复算);数据投影:',
      h('code', {}, 'python3 viz/scripts/build_crossfusion.py'), '。来源:', cite(D.meta.source), '。')))

  host.appendChild(note('本页为只读投影:全部数字由上述两脚本现算,不手抄;',
    '论文原文引用与「复算值」「判断」严格分开(复核范围声明见 refs/README.md)。'))
}
