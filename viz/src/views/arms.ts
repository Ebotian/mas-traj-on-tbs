/**
 * 六格手臂对比(#/arms)—— 正确率 × 成本 × 墙钟 的三角雷达 + 全量明细表。
 *
 * 数据来源:viz/src/data/arms.ts(逐格从 spec §6.6 的 verifier metrics.json /
 * trajectory final_metrics 誊录,成本在该文件里按 COST_BASIS 现算)。本视图只做
 * 归一化与绘制;归一化参数在 drawRadar 内显式计算并写入注记,不预烘焙。
 */
import { ARMS, COST_BASIS, GATE } from '../data/arms.ts'
import type { Arm } from '../data/arms.ts'
import { badge, cite, h, note, panel, stat, table } from '../lib/dom.ts'
import { COLOR } from '../lib/palette.ts'
import { fmt, s, shapePath, text } from '../lib/svg.ts'

const FAMILY_COLOR = { public: COLOR.line, restricted: COLOR.impl, qwen: COLOR.find } as const
const FAMILY_SHAPE = { public: 'circle', restricted: 'square', qwen: 'diamond' } as const
const DASH: Record<string, string> = { A: '', B: '6 3', 'A′': '', 'B′': '6 3', EO: '2 3', 'B″': '' }

interface Axis {
  key: string
  ang: number // degrees, math convention (90 = up)
  good: (v: number) => number
  val: (a: Arm) => number
  cap: string
  range: string
  dir: string
}

function drawRadar(): { svg: SVGElement; ranges: { acc: [number, number]; cost: [number, number]; wall: [number, number] } } {
  const W = 560, H = 470, cx = 280, cy = 252, R = 150
  const g = s('svg', {
    viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart',
    role: 'img', 'aria-label': '六格三角雷达:正确率 × 成本 × 墙钟,越外越优',
  })

  const accV = ARMS.map(a => a.annotation)
  const costV = ARMS.map(a => a.costOffCny)
  const wallV = ARMS.map(a => a.wallSec)
  const [accMin, accMax] = [Math.min(...accV), Math.max(...accV)]
  const [cMin, cMax] = [Math.min(...costV), Math.max(...costV)]
  const [wMin, wMax] = [Math.min(...wallV), Math.max(...wallV)]

  const goodAcc = (v: number) => (v - accMin) / (accMax - accMin)
  const goodCost = (v: number) => 1 - (Math.log10(v) - Math.log10(cMin)) / (Math.log10(cMax) - Math.log10(cMin))
  const goodWall = (v: number) => 1 - (v - wMin) / (wMax - wMin)

  const AXES: Axis[] = [
    { key: 'acc', ang: 90, good: goodAcc, val: a => a.annotation, cap: '正确率', range: `${accMin.toFixed(4)} – ${accMax.toFixed(4)}`, dir: '线性 · 越外越高' },
    { key: 'cost', ang: 210, good: goodCost, val: a => a.costOffCny, cap: '成本 ¥', range: `¥${cMin.toFixed(2)} – ¥${cMax.toFixed(2)}`, dir: 'log₁₀ · 越外越省' },
    { key: 'wall', ang: -30, good: goodWall, val: a => a.wallSec, cap: '墙钟', range: `${(wMin / 60).toFixed(1)}m – 2h 拆线`, dir: '线性 · 越外越快' },
  ]

  const pt = (angDeg: number, r: number): [number, number] =>
    [cx + r * Math.cos((angDeg * Math.PI) / 180), cy - r * Math.sin((angDeg * Math.PI) / 180)]

  for (const f of [0.25, 0.5, 0.75, 1]) {
    g.appendChild(s('circle', { cx, cy, r: R * f, fill: 'none', class: 'grid' }))
    if (f < 1) {
      const [lx, ly] = pt(90, R * f)
      g.appendChild(text(lx + 4, ly + 3, f.toFixed(2), { class: 'lbl sm', 'text-anchor': 'start' }))
    }
  }
  for (const ax of AXES) {
    const [x1, y1] = pt(ax.ang, R)
    g.appendChild(s('line', { x1: cx, y1: cy, x2: x1, y2: y1, class: 'axis-line' }))
    const [lx, ly] = pt(ax.ang, R + 44)
    g.appendChild(text(lx, ly, ax.cap, { class: 'lbl strong', 'text-anchor': 'middle' }))
    const [rx, ry] = pt(ax.ang, R + 60)
    g.appendChild(text(rx, ry, `${ax.range} · ${ax.dir}`, { class: 'lbl sm', 'text-anchor': 'middle' }))
  }

  for (const a of ARMS) {
    const color = FAMILY_COLOR[a.family]
    const pts = AXES.map(ax => pt(ax.ang, R * Math.max(0, Math.min(1, ax.good(ax.val(a))))))
    const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join('') + 'Z'
    g.appendChild(s('path', {
      d, fill: 'none', stroke: color,
      'stroke-width': a.id === 'B″' ? 2.6 : 1.8,
      'stroke-dasharray': DASH[a.id] ?? '',
    }))
    for (const p of pts) {
      const { tag, attrs } = shapePath(FAMILY_SHAPE[a.family], 3)
      g.appendChild(s('g', { transform: `translate(${p[0].toFixed(2)},${p[1].toFixed(2)})` }, s(tag, attrs)))
    }
  }

  // direct callouts: the two vertices that carry the finding
  const [ex, ey] = pt(90, R)
  g.appendChild(text(ex + 8, ey + 4, 'EO 0.8726', { class: 'lbl sm', 'text-anchor': 'start', fill: COLOR.impl }))
  // B″'s callout lives in the empty upper-left wedge, with a leader to centre
  g.appendChild(s('line', {
    x1: cx - 12, y1: cy - 8, x2: cx - 150, y2: cy - 110,
    stroke: COLOR.find, 'stroke-width': 1, 'stroke-dasharray': '2 3', opacity: 0.7,
  }))
  g.appendChild(text(cx - 152, cy - 112, 'B″ 成本 ¥16.45(贴底)', { class: 'lbl sm', 'text-anchor': 'start', fill: COLOR.find }))
  g.appendChild(text(cx - 152, cy - 98, '墙钟 7200s = 2h 拆线', { class: 'lbl sm', 'text-anchor': 'start', fill: COLOR.find }))
  g.appendChild(text(cx + 8, cy + 4, '∗', { class: 'lbl sm', 'text-anchor': 'start', fill: COLOR.find }))

  return { svg: g, ranges: { acc: [accMin, accMax], cost: [cMin, cMax], wall: [wMin, wMax] } }
}

function keyChip(a: Arm): HTMLElement {
  const sw = s('svg', { width: 34, height: 10 }, s('line', {
    x1: 1, y1: 5, x2: 22, y2: 5, stroke: FAMILY_COLOR[a.family], 'stroke-width': 2.2,
    'stroke-dasharray': DASH[a.id] ?? '',
  }))
  const { tag, attrs } = shapePath(FAMILY_SHAPE[a.family], 3.2)
  sw.appendChild(s('g', { transform: 'translate(28,5)' }, s(tag, attrs)))
  return h('span', {}, sw, ` ${a.id} · ${a.condition}`)
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '六格 = 2026-10-10 全部实验(公网两格 + 受限四格)。三角的每根轴都归一到该轴的最小/最大并统一为',
    h('b', {}, '「越外越优」'), ':正确率线性、成本因跨度 ≈13× 取 log₁₀、墙钟线性。',
    '全部 reward = 0(0.95 闸未达);', h('b', {}, 'B″ 的墙钟是 2h 拆线的上界'), '(删失;拆线时提交已完整)。'))

  host.appendChild(h('div', { class: 'stats' },
    stat('0.8726', '最高正确率(EO,全部 reward=0,闸 0.95)', COLOR.impl),
    stat('¥1.26', '最低成本(B)', COLOR.impl),
    stat('19m24s', '最短墙钟(B)'),
    stat('¥16.45', 'B″ 成本 ≈13×B(模型轴的价签)', COLOR.find),
    stat('2h 拆线', 'B″ 墙钟 = 上界(删失)', COLOR.warn),
    stat('+4.6pp', '同格模型差:B″ vs B′(0.8081 vs 0.7625)'),
  ))

  const { svg, ranges } = drawRadar()

  host.appendChild(panel('六格三角对比 —— 正确率 × 成本 × 墙钟',
    svg,
    h('div', { class: 'leg' }, ...ARMS.map(keyChip)),
    note('归一化(现算,范围如下):正确率 [', ranges.acc[0].toFixed(4), ', ', ranges.acc[1].toFixed(4), '] 线性;成本 [¥',
      ranges.cost[0].toFixed(2), ', ¥', ranges.cost[1].toFixed(2), '] 取 log₁₀;墙钟 [',
      String(ranges.wall[0]), ' s, ', String(ranges.wall[1]), ' s] 线性(7200 s = 拆线,删失上界)。',
      h('br'),
      h('b', {}, '读法:'), 'EO(受限·禁引擎·SBB)三角全面大于 A′/B′ —— 受限行内它是更好的格;B″(qwen3.8-max)正确率 0.8081 介于 B 与 EO 之间,但成本轴塌到圆心(¥16.45 ≈ 13× B)、墙钟撞 2h 拆线 ⇒ 模型轴买到的正确率带着价格与时间标签。',
      h('br'), COST_BASIS, ' ', cite('related_files/2026-10-08-first-measurement-spec.md §6.6'))))

  const rows = ARMS.map(a => [
    a.id, a.condition, a.model,
    a.annotation.toFixed(4),
    a.wallCensored ? '7200 s(2h 拆线)' : `${fmt.int(a.wallSec)} s(${Math.round(a.wallSec / 60)}m)`,
    `¥${a.costOffCny.toFixed(2)}`,
    a.costActualNote,
    `${a.steps}`,
    a.execComposite.toFixed(4),
  ])
  host.appendChild(panel('全量明细(与三角同源,arm-by-arm)',
    table(['手臂', '条件', '模型', '正确率', '墙钟', '成本 ¥(统一口径)', '实付口径', '步数', 'exec'], rows),
    note('奖励全为 0:annotation 均低于 ', h('b', {}, String(GATE)), ' 的闸;EO 的 0.8726 是系列最高。',
      ' A 行实付为峰值费率(TOU),统一口径下按 off-peak 计以消除时段错位;',
      ' B″ 走 Token Plan 积分(×¥0.005 加油档),与其余行的 CNY 费率面不同,两制不直接相加。',
      h('br'),
      badge('B″ 删失', COLOR.warn), ' 2h 上限是进程墙(`AgentTimeoutError: 7200.0s`),完成度不在判据内;其提交在拆线时已完整,分数=拆线态。',
      ' 模板 v2 已加入显式停规以消除这一类拆线。')))
}
