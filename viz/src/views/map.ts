import { EDGE_STYLE, EDGES, NODES } from '../data/graph.ts'
import { COLOR, EVIDENCE_DASH, EVIDENCE_LABEL, KIND_COLOR, KIND_LABEL, KIND_SHAPE } from '../lib/palette.ts'
import { arrowMarker, s, shapePath, text } from '../lib/svg.ts'
import { badge, cite, h, note } from '../lib/dom.ts'
import type { EdgeKind, Evidence, GNode, NodeKind } from '../types.ts'

const W = 1180
const H = 940
const LAYERS = 8
/** Horizontal clearance floor between node centres on the same layer. */
const MIN_GAP = 96
const LABEL_MAX = 12

interface Sim extends GNode { x: number; y: number; vx: number; vy: number; r: number }

const layerY = (L: number) => 58 + L * ((H - 110) / (LAYERS - 1))

/** Deterministic pseudo-random so the layout is identical on every load. */
function rand(i: number): number {
  const v = Math.sin(i * 12.9898) * 43758.5453
  return v - Math.floor(v)
}

function truncate(t: string): string {
  return t.length > LABEL_MAX ? `${t.slice(0, LABEL_MAX - 1)}…` : t
}

/** CJK glyphs are ~10.5px wide at font-size 10.5, ASCII ~6.0. A fixed gap
 *  under-estimates labels that contain Chinese, which is how the first build
 *  still overlapped after the relaxation pass. */
function labelWidth(t: string): number {
  let w = 0
  for (const ch of truncate(t)) w += ch.codePointAt(0)! > 0x2e80 ? 10.5 : 6.0
  return w
}

/**
 * Force-directed with a hard vertical constraint (layer bands), then two
 * deterministic post-passes: a per-layer 1-D relaxation that enforces MIN_GAP so
 * labels never overlap, and an x-rescale that spreads the result across the whole
 * viewBox. The first build skipped both and collapsed into a vertical spine.
 */
function layout(): Sim[] {
  const deg = new Map<string, number>()
  for (const e of EDGES) {
    deg.set(e.source, (deg.get(e.source) ?? 0) + 1)
    deg.set(e.target, (deg.get(e.target) ?? 0) + 1)
  }
  const perLayer = new Map<number, number>()
  for (const n of NODES) perLayer.set(n.layer, (perLayer.get(n.layer) ?? 0) + 1)
  const seenInLayer = new Map<number, number>()
  const nodes: Sim[] = NODES.map((n, i) => {
    const k = seenInLayer.get(n.layer) ?? 0
    seenInLayer.set(n.layer, k + 1)
    const count = perLayer.get(n.layer) ?? 1
    const slot = count > 1 ? (k / (count - 1)) - 0.5 : 0
    return {
      ...n,
      x: W / 2 + slot * (W - 260) + (rand(i) - 0.5) * 40,
      y: layerY(n.layer),
      vx: 0, vy: 0,
      r: 11 + Math.min(6, (deg.get(n.id) ?? 0) * 0.55),
    }
  })
  const byId = new Map(nodes.map(n => [n.id, n]))

  for (let it = 0; it < 520; it++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j]
        const dx = b.x - a.x
        const dy = (b.y - a.y) * 0.3
        const d2 = dx * dx + dy * dy + 900
        const d = Math.sqrt(d2)
        const f = 52000 / d2
        a.vx -= (dx / d) * f
        b.vx += (dx / d) * f
        a.vy -= (dy / d) * f * 0.25
        b.vy += (dy / d) * f * 0.25
      }
    }
    for (const e of EDGES) {
      const a = byId.get(e.source), b = byId.get(e.target)
      if (!a || !b) continue
      const dx = b.x - a.x, dy = b.y - a.y
      const d = Math.sqrt(dx * dx + dy * dy) + 1e-3
      const t = (d - 150) * 0.004
      a.vx += (dx / d) * t
      b.vx -= (dx / d) * t
    }
    for (const n of nodes) {
      n.vy += (layerY(n.layer) - n.y) * 0.14
      n.x += Math.max(-16, Math.min(16, n.vx))
      n.y += Math.max(-8, Math.min(8, n.vy))
      n.vx *= 0.8; n.vy *= 0.8
    }
  }

  const groups = new Map<number, Sim[]>()
  for (const n of nodes) {
    const g = groups.get(n.layer) ?? []
    g.push(n)
    groups.set(n.layer, g)
  }
  const relax = (passes: number): void => {
    for (let pass = 0; pass < passes; pass++) {
      for (const g of groups.values()) {
        g.sort((a, b) => a.x - b.x)
        for (let i = 1; i < g.length; i++) {
          const need = Math.max(MIN_GAP, (labelWidth(g[i - 1].title) + labelWidth(g[i].title)) / 2 + 10)
          const gap = g[i].x - g[i - 1].x
          if (gap < need) {
            const push = (need - gap) / 2
            g[i - 1].x -= push
            g[i].x += push
          }
        }
      }
    }
  }
  relax(200)

  let lo = Infinity, hi = -Infinity
  for (const n of nodes) { lo = Math.min(lo, n.x); hi = Math.max(hi, n.x) }
  const span = hi - lo || 1
  for (const n of nodes) n.x = 80 + ((n.x - lo) / span) * (W - 160)
  // the rescale can compress a layer back below MIN_GAP, so relax once more in
  // final coordinates and then clamp instead of rescaling again
  relax(120)
  for (const n of nodes) {
    n.x = Math.max(46, Math.min(W - 46, n.x))
    n.y = Math.max(34, Math.min(H - 30, n.y))
  }
  return nodes
}

const NARROW_PATH = ['g0', 'capA', 'rq3', 'ht', 'gates', 'b0a', 'b0b', 'a0', 'a1', 'packet', 'stage2', 'mechA', 't1', 'kill', 'fNarrow']
const DEBT_PATH = ['debt', 'capR', 'capU', 'capL']

export function render(host: HTMLElement): void {
  const nodes = layout()
  const byId = new Map(nodes.map(n => [n.id, n]))

  host.appendChild(h('p', { class: 'lede' },
    '纵向 = 抽象层级(G₀ 在顶,未启动的阶段在底);横向由斥力与边弹簧自由排布。',
    '所以它不是树:', badge('反馈环', COLOR.find), badge('跨层同名异义', COLOR.find),
    badge('部分覆盖', COLOR.impl), badge('我自己的错误', COLOR.find),
    ' 都是横向或向上的边,层级图表达不了。'))

  const wrap = h('div', { class: 'split' })
  const left = h('div', { class: 'card' })
  const right = h('div', { class: 'sidecol' })

  /* ---- controls ---- */
  const ctl = h('div', { class: 'ctl' })
  const onKind: Record<NodeKind, boolean> = { frame: true, line: true, impl: true, find: true }
  const mode = { narrow: false, debt: false, onlyConflict: false, onlyWeak: false }
  left.appendChild(h('h2', {}, '理解结构图 · 力导 + 分层约束'))
  left.appendChild(ctl)

  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart graph', role: 'img', 'aria-label': '构想理解结构图' })
  const scroll = h('div', { class: 'scroll' }, svg)
  left.appendChild(scroll)

  const defs = s('defs', {})
  defs.appendChild(arrowMarker('arw', COLOR.muted))
  svg.appendChild(defs)
  const gE = s('g', {})
  const gN = s('g', {})
  svg.appendChild(gE); svg.appendChild(gN)

  const edgeEls: { el: SVGElement; kind: EdgeKind; a: string; b: string }[] = []
  for (const e of EDGES) {
    const a = byId.get(e.source), b = byId.get(e.target)
    if (!a || !b) continue
    const st = EDGE_STYLE[e.kind]
    const el = s('line', {
      x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: st.color, 'stroke-width': st.width,
      'stroke-dasharray': st.dash || '', opacity: 0.6, 'marker-end': 'url(#arw)',
    })
    gE.appendChild(el)
    edgeEls.push({ el, kind: e.kind, a: e.source, b: e.target })
  }

  const nodeEls = new Map<string, SVGGElement>()
  for (const n of nodes) {
    const g = s('g', { transform: `translate(${n.x},${n.y})`, class: 'node', tabindex: 0, role: 'button', 'aria-label': n.title }) as SVGGElement
    const sh = shapePath(KIND_SHAPE[n.kind], n.r)
    const mark = s(sh.tag, {
      ...sh.attrs, fill: KIND_COLOR[n.kind], 'fill-opacity': n.evidence === 'u' ? 0.42 : 0.92,
      stroke: COLOR.ink, 'stroke-width': (n.evidence === 'v' || n.evidence === 'r') ? 2 : 1.5,
      'stroke-dasharray': EVIDENCE_DASH[n.evidence] || '',
    })
    g.appendChild(mark)
    g.appendChild(s('title', {}, `${n.title} — ${EVIDENCE_LABEL[n.evidence]}`))
    g.appendChild(text(0, n.r + 13, truncate(n.title), { 'text-anchor': 'middle', class: 'lbl' }))
    gN.appendChild(g)
    nodeEls.set(n.id, g)
  }

  /* ---- detail panel ---- */
  const det = h('div', { class: 'cardbody' })
  const detCard = h('div', { class: 'card' }, h('h2', {}, '节点详情'), det)
  right.appendChild(detCard)

  function show(n: Sim): void {
    det.textContent = ''
    det.appendChild(h('p', { class: 'det-t' }, n.title))
    det.appendChild(h('div', {},
      badge(KIND_LABEL[n.kind], KIND_COLOR[n.kind]),
      badge(`证据:${EVIDENCE_LABEL[n.evidence]}`, n.evidence === 'v' || n.evidence === 'r' ? COLOR.good : n.evidence === 's' ? COLOR.warn : COLOR.muted),
      badge(`第 ${n.layer} 层`, COLOR.muted)))
    if (n.cite) det.appendChild(h('div', {}, cite(n.cite)))
    if (n.summary) det.appendChild(h('p', { class: 'note strong' }, n.summary))
    if (n.detail) det.appendChild(h('p', { class: 'note' }, n.detail))
    const ins: string[] = [], outs: string[] = []
    for (const e of EDGES) {
      const st = EDGE_STYLE[e.kind]
      if (e.target === n.id) { const o = byId.get(e.source); if (o) ins.push(`${o.title} —${st.label}→ 本节点`) }
      if (e.source === n.id) { const o = byId.get(e.target); if (o) outs.push(`本节点 —${st.label}→ ${o.title}`) }
    }
    if (ins.length || outs.length) {
      const c = h('div', { class: 'conn' })
      for (const x of ins) c.appendChild(h('div', {}, `← ${x}`))
      for (const x of outs) c.appendChild(h('div', {}, `→ ${x}`))
      det.appendChild(c)
    }
  }

  let selected: string | null = null

  function paint(): void {
    const focus = selected
    const nb = new Set<string>()
    if (focus) {
      nb.add(focus)
      for (const e of EDGES) {
        if (e.source === focus) nb.add(e.target)
        if (e.target === focus) nb.add(e.source)
      }
    }
    const pathSet = new Set<string>(mode.narrow ? NARROW_PATH : mode.debt ? DEBT_PATH : [])
    for (const n of nodes) {
      const g = nodeEls.get(n.id)
      if (!g) continue
      let vis = onKind[n.kind]
      if (mode.onlyConflict && n.kind !== 'find') vis = false
      if (mode.onlyWeak && (n.evidence === 'v' || n.evidence === 'r')) vis = false
      g.style.display = vis ? '' : 'none'
      const lit = !focus || nb.has(n.id) || pathSet.has(n.id)
      g.style.opacity = lit ? '1' : '0.12'
    }
    for (const e of edgeEls) {
      let vis = onKind[byId.get(e.a)?.kind ?? 'frame'] && onKind[byId.get(e.b)?.kind ?? 'frame']
      if (mode.onlyConflict && e.kind !== 'clash' && e.kind !== 'warn' && e.kind !== 'open') vis = false
      e.el.style.display = vis ? '' : 'none'
      const lit = !focus
        ? (pathSet.size === 0 || (pathSet.has(e.a) && pathSet.has(e.b)))
        : (e.a === focus || e.b === focus || (pathSet.has(e.a) && pathSet.has(e.b)))
      e.el.setAttribute('opacity', lit ? (focus || pathSet.size ? '0.95' : '0.6') : '0.05')
    }
  }

  function button(label: string, fn: () => void, active = false, cls = ''): HTMLButtonElement {
    const b = h('button', { class: `btn ${cls}`, 'aria-pressed': active ? 'true' : 'false', onclick: () => { fn(); b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') === 'true' ? 'false' : 'true') } }, label)
    return b
  }

  for (const k of ['frame', 'line', 'impl', 'find'] as NodeKind[]) {
    ctl.appendChild(button(KIND_LABEL[k].split(' ')[0], () => { onKind[k] = !onKind[k]; paint() }, true))
  }
  ctl.appendChild(h('span', { class: 'sep' }))
  ctl.appendChild(button('收窄链', () => { mode.narrow = !mode.narrow; mode.debt = false; paint() }, false, 'act'))
  ctl.appendChild(button('反馈环', () => { mode.debt = !mode.debt; mode.narrow = false; paint() }, false, 'act'))
  ctl.appendChild(button('只看冲突', () => { mode.onlyConflict = !mode.onlyConflict; paint() }, false, 'act'))
  ctl.appendChild(button('只看二手+未读', () => { mode.onlyWeak = !mode.onlyWeak; paint() }, false, 'act'))
  ctl.appendChild(button('重置', () => {
    mode.narrow = mode.debt = mode.onlyConflict = mode.onlyWeak = false
    onKind.frame = onKind.line = onKind.impl = onKind.find = true
    selected = null
    Array.from(ctl.querySelectorAll('button')).forEach(b => {
      const lbl = b.textContent ?? ''
      b.setAttribute('aria-pressed', ['框架层', '研究线与概念', '实现与测量', '冲突'].some(x => lbl.startsWith(x)) ? 'true' : 'false')
    })
    paint()
  }, false, 'act'))

  for (const n of nodes) {
    const g = nodeEls.get(n.id)
    if (!g) continue
    g.addEventListener('mouseenter', () => { if (!selected) { selected = null; show(n); paintHover(n.id) } })
    g.addEventListener('mouseleave', () => { if (!selected) paint() })
    g.addEventListener('click', ev => { ev.stopPropagation(); selected = n.id; show(n); paint() })
    g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); selected = n.id; show(n); paint() } })
  }
  function paintHover(id: string): void {
    const nb = new Set<string>([id])
    for (const e of EDGES) { if (e.source === id) nb.add(e.target); if (e.target === id) nb.add(e.source) }
    for (const n of nodes) { const g = nodeEls.get(n.id); if (g) g.style.opacity = nb.has(n.id) ? '1' : '0.12' }
    for (const e of edgeEls) e.el.setAttribute('opacity', (e.a === id || e.b === id) ? '0.95' : '0.05')
  }
  svg.addEventListener('click', () => { selected = null; paint() })

  /* ---- legend ---- */
  const leg = h('div', { class: 'leg' })
  for (const k of ['frame', 'line', 'impl', 'find'] as NodeKind[]) {
    const svgk = s('svg', { width: 15, height: 15, viewBox: '-9 -9 18 18' })
    const sh = shapePath(KIND_SHAPE[k], 6.5)
    svgk.appendChild(s(sh.tag, { ...sh.attrs, fill: KIND_COLOR[k], stroke: COLOR.ink, 'stroke-width': 1.3 }))
    leg.appendChild(h('span', {}, svgk, KIND_LABEL[k]))
  }
  for (const e of ['r', 'v', 's', 'u'] as Evidence[]) {
    const svgl = s('svg', { width: 22, height: 10 })
    svgl.appendChild(s('line', { x1: 1, y1: 5, x2: 21, y2: 5, stroke: COLOR.ink, 'stroke-width': 2.4, 'stroke-dasharray': EVIDENCE_DASH[e] || '' }))
    leg.appendChild(h('span', {}, svgl, EVIDENCE_LABEL[e]))
  }
  for (const k of ['kill', 'feed', 'clash', 'block', 'spec', 'inst', 'part', 'orphan'] as EdgeKind[]) {
    const st = EDGE_STYLE[k]
    const svge = s('svg', { width: 22, height: 10 })
    svge.appendChild(s('line', { x1: 1, y1: 5, x2: 21, y2: 5, stroke: st.color, 'stroke-width': st.width, 'stroke-dasharray': st.dash || '' }))
    leg.appendChild(h('span', {}, svge, st.label))
  }
  left.appendChild(leg)

  /* ---- reading guide ---- */
  right.appendChild(h('div', { class: 'card' }, h('h2', {}, '怎么读这张图'),
    h('div', { class: 'cardbody' },
      note('按「收窄链」:亮起来的是 G₀ → Allocate → RQ3 → H_T → 门 → B0a,一条穿过 8 层的细线,两侧全暗。这是「H_T 只是子问题」的可视化。'),
      note('按「只看冲突」:玫红三角形聚在第 4–5 层,即线与线的交界处,不在任何一条线内部。'),
      note(`按「只看二手+未读」:剩下 ${nodes.filter(n => n.evidence !== 'v' && n.evidence !== 'r').length} 个节点(` +
        `${nodes.filter(n => n.evidence === 's').length} 二手 + ${nodes.filter(n => n.evidence === 'u').length} 未读)。` +
        '这是给我自己的折扣清单 —— 个数从数据现算,不手写。'),
      note('节点大小 = 连接度。描边虚实 = 证据等级,与颜色无关,所以色盲下仍可读。'))))

  const first = nodes.find(n => n.id === 'g0')
  if (first) show(first)
  paint()
  wrap.appendChild(left); wrap.appendChild(right)
  host.appendChild(wrap)
}
