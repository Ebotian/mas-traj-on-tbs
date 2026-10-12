// process.ts —— 过程观测:全族已采集双 agent 跑次的前缀级只读审计(零框架手写 SVG)。
//
// 吸收自 EarlyEval(arXiv 2609.02783 v1)的观测设计:前缀化视图(把问题改写成
// 「截止到第 k 步」)、统一特征口径、决策与记账分离——但**不采用早停**:本项目研究的是
// 过程本身,这里只观测、不截断任何跑。
//
// 数据由 scripts/build_process.py 从 jobs/agent 采集包现算(src/data/process.json),
// 口径同 tasks/walkthrough/metrics.py;exp 名与 #/handoff · #/tumor · #/microarch 的
// 轨迹 bundle 同源对齐(同一批跑的两面:那边看轨迹原文,这边看跨跑统计)。
import raw from '../data/process.json'
import { COLOR } from '../lib/palette.ts'
import { axisBottom, axisLeft, fmt, linear, polyline, s, text } from '../lib/svg.ts'
import { badge, cite, clear, h, note, panel, stat, table } from '../lib/dom.ts'

type Ser = Array<number | null>

interface SideRec {
  side: string; model: string; steps: number; usage_events: number; wall_s: number | null
  unc: number; cache: number; out: number
  gap_med_s: number | null; gap_p90_s: number | null; gap_max_s: number | null
  cost: number; cost_unit: string; peak: boolean
  tail75: Record<string, number>; tail_cost: number
  deciles: number[]; series: Ser[]; job: string
}
interface Refusal { actor: string; round: number; fixed: boolean }
interface GateRec { counts: Record<string, number>; refusals: Refusal[]; blocks: Array<{ actor: string; peer: string; when: string }> }
interface RunRec {
  job: string; exp: string | null; label: string; family: string
  normal: boolean | null; rc: Array<number | null>; stop: boolean[]; abort: boolean[]
  recovered: boolean | null; mech: string; variant: string | null
  signals: Record<string, { ts: string | null; head: string }>
  recover: { wakes: Array<{ side: string; rc: number; dur_s: number; mode: string }> } | null
  gate: GateRec; sides: SideRec[]
}
interface ProcData {
  meta: { source: string; script: string; note: string }
  totals: {
    runs: number; sides: number; steps: number; out: number; unc: number; cache: number
    cost_a_usd: number; cost_b_cny: number; total_cny_1to7: number
    tail75_a_usd: number; tail75_b_cny: number; tail75_total_cny: number
  }
  families: Array<{ name: string; runs: number; sides: number; steps: number; out: number; unc: number; cache: number; cost_a_usd: number; cost_b_cny: number }>
  tails: Array<{ cut: number; out: number | null; unc: number | null; cache: number | null; wall: number | null }>
  growth: number[]
  ab: Record<string, { model: string; n: number; gap_med: number; gap_p90: number; gap_max: number; out_per_step: number; steps_med: number }>
  aborts: Array<{ job: string; exp: string | null; file: string; ts: string | null; head: string }>
  recovers: Array<{ job: string; exp: string | null; wakes: Array<{ side: string; rc: number; dur_s: number; mode: string }> }>
  gate: {
    pool_counts: Record<string, number>
    per_run: Array<{ job: string; exp: string | null; counts: Record<string, number>; refusals: Refusal[]; blocks: GateRec['blocks'] }>
    refusal_total: number; refusal_fixed: number
  }
  runs: RunRec[]
}
const D = raw as unknown as ProcData

const kt = (v: number | null | undefined): string =>
  v == null ? '—' : v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}k` : String(Math.round(v))
const pct = (v: number | null | undefined, d = 1): string => v == null ? '—' : `${v.toFixed(d)}%`
const wallf = (sec: number | null): string =>
  sec == null ? '—' : `${Math.floor(sec / 60)}m${String(Math.round(sec % 60)).padStart(2, '0')}s`
const FAM_CN: Record<string, string> = { rehearsal: '走查', tumor: 'tumor', microarch: 'microarch' }

function hbar(label: string, v: number | null, color: string): HTMLElement {
  const p = v ?? 0
  return h('div', { class: 'ratio' },
    h('div', { class: 'ratio-h' }, h('b', {}, label), h('span', { class: 'ratio-pct' }, pct(v))),
    h('div', { class: 'bar' }, h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, p))}%;background:${color}` })))
}

function growthChart(): SVGElement {
  const W = 660, H = 220, M = { l: 56, r: 14, t: 18, b: 30 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': '上下文增长:每步 prompt 中位数' })
  if (D.growth.length < 2) return g
  const ys = linear([0, Math.max(...D.growth) * 1.08], [H - M.b, M.t])
  const xs = linear([10, 100], [M.l, W - M.r])
  g.appendChild(axisLeft(ys, M.l, v => kt(v)))
  g.appendChild(axisBottom(xs, H - M.b, v => `${v}%`))
  const pts: Array<[number, number]> = D.growth.map((v, i) => [10 + i * 10, v])
  g.appendChild(s('path', { d: polyline(pts.map(p => [xs(p[0]), ys(p[1])])), fill: 'none', stroke: COLOR.frame, 'stroke-width': 2 }))
  for (const p of pts) g.appendChild(s('circle', { cx: xs(p[0]), cy: ys(p[1]), r: 2.6, fill: COLOR.frame }))
  const first = pts[0], last = pts[pts.length - 1]
  g.appendChild(text(xs(first[0]), ys(first[1]) - 8, kt(first[1]), { 'text-anchor': 'start', class: 'lbl strong' }))
  g.appendChild(text(xs(last[0]), ys(last[1]) - 8, kt(last[1]), { 'text-anchor': 'end', class: 'lbl strong' }))
  return g
}

function sideChart(sd: SideRec, kind: 'cache' | 'gap'): SVGElement {
  const W = 620, H = kind === 'cache' ? 104 : 84, M = { l: 52, r: 10, t: 16, b: 18 }
  const g = s('svg', {
    viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': `${sd.side} 侧逐步${kind === 'cache' ? '上下文 cache' : '间隔'}`,
  })
  const ev = sd.series
  if (ev.length < 2) return g
  const xs = linear([0, ev.length - 1], [M.l, W - M.r])
  if (kind === 'cache') {
    const vmax = Math.max(1, ...ev.map(e => Number(e[3] ?? 0))) * 1.05
    const ys = linear([0, vmax], [H - M.b, M.t])
    g.appendChild(axisLeft(ys, M.l, v => kt(v)))
    g.appendChild(s('path', { d: polyline(ev.map((e, i) => [xs(i), ys(Number(e[3] ?? 0))])), fill: 'none', stroke: COLOR.line, 'stroke-width': 1.6 }))
  } else {
    const vmax = Math.max(1, ...ev.map(e => Number(e[2] ?? 0))) * 1.05
    const ys = linear([0, vmax], [H - M.b, M.t])
    g.appendChild(axisLeft(ys, M.l, v => `${Math.round(v)}s`))
    const bw = Math.max(1, (W - M.l - M.r) / ev.length - 0.4)
    ev.forEach((e, i) => {
      const gap = Number(e[2] ?? 0)
      if (gap <= 0) return
      const y = ys(gap)
      g.appendChild(s('rect', {
        x: xs(i), y, width: bw, height: Math.max(0.5, H - M.b - y), rx: 0.5,
        fill: gap >= 300 ? COLOR.bad : COLOR.warn, opacity: 0.72,
      }))
    })
  }
  g.appendChild(axisBottom(xs, H - M.b, v => `#${Math.round(v) + 1}`))
  return g
}

function runDetail(run: RunRec): HTMLElement {
  const box = h('div', {})
  box.appendChild(h('div', { class: 'det-t' },
    `${run.exp ?? run.job} · ${run.label} `,
    badge(run.normal ? 'NORMAL' : 'ABNORMAL', run.normal ? COLOR.good : COLOR.bad)))
  const meta = [`rc=[${run.rc.map(String).join(',')}]`, `stop=[${run.stop.map(String).join(',')}]`,
    `abort=[${run.abort.map(String).join(',')}]`]
  if (run.mech) meta.push(run.mech)
  if (run.recovered) meta.push('recovered_run')
  if (run.variant) meta.push(`prompt=${run.variant}`)
  const rf = run.gate.refusals.map(x => `${x.actor}R${x.round}${x.fixed ? '✓' : '✗'}`).join(' ')
  if (rf) meta.push(`refs 拒绝:${rf}`)
  box.appendChild(h('p', { class: 'note' }, meta.join(' · ')))
  const grid = h('div', { class: 'grid2' })
  for (const sd of run.sides) {
    const col = h('div', {})
    col.appendChild(h('p', { class: 'note strong' },
      `${sd.side} · ${sd.model} · ${sd.steps} 步 / ${sd.usage_events} 事件 · 墙钟 ${wallf(sd.wall_s)} · `,
      sd.cost_unit === 'USD' ? `$${sd.cost.toFixed(3)}` : `¥${sd.cost.toFixed(2)}`, sd.peak ? '(峰值)' : ''))
    col.appendChild(sideChart(sd, 'cache'))
    col.appendChild(sideChart(sd, 'gap'))
    col.appendChild(h('p', { class: 'note' },
      `out ${kt(sd.out)} · uncached ${kt(sd.unc)} · cache ${kt(sd.cache)};间隔中位 ${sd.gap_med_s ?? '—'}s / p90 ${sd.gap_p90_s ?? '—'}s / 最长 ${sd.gap_max_s ?? '—'}s;尾 25%:out ${pct(100 * (sd.tail75.out ?? 0) / Math.max(1, sd.out))} · cache ${pct(100 * (sd.tail75.cache ?? 0) / Math.max(1, sd.cache))}`))
    grid.appendChild(col)
  }
  box.appendChild(grid)
  return box
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '对全族已采集双 agent 跑次的', h('b', {}, '只读'), '前缀级审计——吸收 EarlyEval 的观测设计(前缀化视图 / 决策-记账分离),但',
    h('b', {}, '不截断任何跑'), ':本项目研究的是过程本身。数字由 ', h('code', {}, 'scripts/build_process.py'),
    ' 从采集包现算,口径同 metrics.py;exp 名与轨迹页同源对齐(同一批跑的两面)。'))

  const T = D.totals
  if (!T || !D.runs.length) {
    host.appendChild(note('process.json 缺字段——重新运行 `python3 scripts/build_process.py`。'))
    return
  }

  host.appendChild(panel(`池总览 · ${T.runs} 跑 / ${T.sides} 单侧 / ${fmt.int(T.steps)} 步`,
    h('div', { class: 'stats' },
      stat(String(T.runs), '跑次(走查 16 · tumor 2 · microarch 2)'),
      stat(String(T.sides), '单侧轨迹'),
      stat(fmt.int(T.steps), '应答步(usage 事件)'),
      stat(kt(T.out), 'out tokens(candidates+thoughts)'),
      stat(`A$${T.cost_a_usd.toFixed(2)} + B¥${T.cost_b_cny.toFixed(1)}`, `≈ ¥${T.total_cny_1to7.toFixed(1)}(1 USD = 7 CNY)`, COLOR.warn)),
    h('div', { class: 'scroll' }, table(
      ['家族', '跑', '侧', '步', 'out', 'unc', 'cache', 'A$', 'B¥'],
      D.families.map(f => [
        FAM_CN[f.name] ?? f.name, String(f.runs), String(f.sides), fmt.int(f.steps),
        kt(f.out), kt(f.unc), kt(f.cache), `$${f.cost_a_usd.toFixed(2)}`, `¥${f.cost_b_cny.toFixed(1)}`,
      ]))),
    h('div', { class: 'scroll' }, table(
      ['侧', '模型', '步数·中位', 'out/步', '间隔 中位', 'p90', '最长'],
      ['a', 'b'].filter(k => D.ab[k]).map(k => {
        const r = D.ab[k]
        return [k, r.model, String(r.steps_med), String(r.out_per_step), `${r.gap_med}s`, `${r.gap_p90}s`, `${r.gap_max}s`]
      }))),
    note('费率卡 2026-10-10;A 侧峰值(周一至五 01–04 / 06–10 UTC)×2;口径同 ', cite('tasks/walkthrough/metrics.py'),
      '。未入池:walkthrough-1/2(无采集)、walkthrough-3(仅 state、无转录)、两冒烟件。')))

  const t75 = D.tails.find(t => t.cut === 75)
  host.appendChild(panel('截尾账本 · 「完美停」上限(若结局在 k% 步已知即停)',
    h('div', { class: 'scroll' }, table(
      ['停点', '省 out', '省 uncached', '省 cache', '省墙钟'],
      D.tails.map(t => [`${t.cut}%`, pct(t.out), pct(t.unc), pct(t.cache), pct(t.wall)]))),
    t75 ? h('div', {},
      hbar('75% 停 · 省 out', t75.out, COLOR.line),
      hbar('75% 停 · 省 cache(上下文)', t75.cache, COLOR.frame),
      hbar('75% 停 · 省 uncached', t75.unc, COLOR.warn),
      hbar('75% 停 · 省墙钟', t75.wall, COLOR.find)) : null,
    note('「完美停」= 上限不是承诺:真实预测头有 1–2pp 系统偏差(EarlyEval ', cite('arXiv 2609.02783 v1(其口径,未复现)'),
      ');冻结产物不得用早停值。全池最后 1/4 步承担 ≈', h('b', {}, pct(100 * T.tail75_total_cny / T.total_cny_1to7, 0)),
      ' 的成本(≈¥', T.tail75_total_cny.toFixed(1), ')。')))

  const g0 = D.growth[0] ?? 0, gN = D.growth[D.growth.length - 1] ?? 0
  host.appendChild(panel('上下文增长 · 每步可见的 prompt 中位数',
    growthChart(),
    note('10% → 100% 步:', kt(g0), ' → ', kt(gN), `(×${(gN / Math.max(1, g0)).toFixed(1)})`,
      ';后半程(50% 后)承载 ', pct(D.tails[0]?.cache ?? null), ' 的 cache 读——贵在字节、不在时间,截尾天然比截头赚。',
      cite('src/data/process.json · growth / tails'))))

  const nAbnormal = D.runs.filter(r => r.normal === false).length
  host.appendChild(panel('停 / 收口信号 × 判决(只记账,不裁决)',
    h('div', { class: 'scroll' }, table(
      ['跑', '文件', '时间', '理由(首段,原文)'],
      D.aborts.map(a => [a.exp ?? a.job, a.file, a.ts ?? '—', a.head.slice(0, 130)]))),
    h('div', { class: 'scroll' }, table(
      ['跑', 'wakes(受限唤醒)'],
      D.recovers.map(r => [r.exp ?? r.job,
        r.wakes.map(w => `${w.side} rc=${w.rc} ${w.dur_s}s ${w.mode}`).join(' · ') || '—']))),
    note('abort ', h('b', {}, `${D.aborts.length}/${D.aborts.length}`), ' 全落在 ABNORMAL;', h('b', {}, String(T.runs - nAbnormal)),
      ' 个 NORMAL 跑零 abort;recover 仅出现于 w7/w8。', h('br'),
      '环性说明:abort/stop 同时是判决的构成要件——此处只作描述,不作预测精度评估。')))

  const GA = ['refs-ok', 'fast-allow', 'refs-block', 'wait-start', 'block', 'allow-after-wait']
  host.appendChild(panel('门决策账本(gate.log 全量)',
    h('div', { class: 'stats' },
      ...GA.map(k => stat(String(D.gate.pool_counts[k] ?? 0), k)),
      stat(`${D.gate.refusal_fixed}/${D.gate.refusal_total}`, 'refs 拒绝 → 修复闭环', COLOR.good)),
    h('div', { class: 'scroll' }, table(
      ['跑', ...GA, '拒绝明细'],
      D.gate.per_run.filter(r => Object.keys(r.counts).length).map(r => [
        r.exp ?? r.job,
        ...GA.map(k => String(r.counts[k] ?? 0)),
        r.refusals.map(x => `${x.actor}R${x.round}${x.fixed ? '✓' : '✗'}`).join(' ') || '—',
      ]))),
    note('闭环 = 该次拒绝之后、同一 (actor, Round) 出现 refs-ok(修复后重提);共 ', `${D.gate.refusal_fixed}/${D.gate.refusal_total}`,
      '。屏障 block 含 w7 的 peer-dead 与 w8 的 alive-not-ready 两类;全量见 ', cite('collect/x/gate.log'), '。')))

  const ctl = h('div', { class: 'ctl' })
  const detail = h('div', {})
  const btns: HTMLButtonElement[] = []
  const select = (job: string): void => {
    for (const b of btns) b.setAttribute('aria-pressed', String(b.dataset.job === job))
    clear(detail)
    const run = D.runs.find(r => r.job === job)
    if (run) detail.appendChild(runDetail(run))
  }
  for (const fam of ['rehearsal', 'tumor', 'microarch']) {
    ctl.appendChild(h('span', { class: 'sep' }))
    for (const r of D.runs.filter(x => x.family === fam)) {
      const b = h('button', { class: 'btn', 'data-job': r.job, title: r.label, onclick: () => select(r.job) }, r.exp ?? r.job)
      btns.push(b)
      ctl.appendChild(b)
    }
  }
  host.appendChild(panel('逐跑探索(前缀级序列)',
    ctl,
    detail,
    note('上=上下文 cache/步,下=步间隔 s(红 ≥300s,即停摆窗尺度);x = usage 事件序号。',
      h('br'), '同一跑的另一面(逐轮轨迹回放)在 ', cite('#/handoff · #/tumor · #/microarch'), '(exp 名一致)。')))
  const start = D.runs.some(r => r.job === 'walkthrough-8') ? 'walkthrough-8' : (D.runs[0]?.job ?? '')
  if (start) select(start)
}
