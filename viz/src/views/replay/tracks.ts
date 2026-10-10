// replay/tracks.ts —— 重建条带:时间比例的全景图。
//
// 四条泳道:actor a / actor b 的轮(竖条,高度 ∝ 工具调用数)、git 提交(菱形,空心 = merge,
// 环 + 小标签 = tag)、协议事件(门 = 竖线,板 = 方块)。当前步 = 虚线游标;已发生(≤ 本轮末)
// 的标记实色,未发生降透明。任何标记可点击跳转到「该标记落入的轮」(第一个 t1 ≥ 标记时刻)。
// 只折叠显示;数据不删减(完整内容在 bundle 的 raw 字段与各视图卡片里)。

import { s, text, linear } from '../../lib/svg.ts'
import { COLOR } from '../../lib/palette.ts'
import type { ReplayBundle } from './data.ts'
import { ms, hhmmss, dur } from './data.ts'

export interface StripHandle {
  el: SVGElement
  setCurrent: (k: number) => void
}

interface Mark { el: SVGElement; ts: number }

export function buildStrip(b: ReplayBundle, onJump: (k: number) => void): StripHandle {
  const turns = b.sessions.turns
  const W = 1180, H = 178
  const x0 = 44, x1 = 1168
  const t0 = ms(b.time_range.t0), t1 = ms(b.time_range.t1)
  const X = linear([t0, t1 + 1], [x0, x1])
  const svg = s('svg', { class: 'chart rp-strip', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': '轨迹重建条带' })
  const baseA = 40, baseB = 68, gitY = 96, gateY = 123, boardY = 137, axisY = 156

  const marks: Mark[] = []
  const tickEls: SVGElement[] = []

  const t1s = turns.map(t => ms(t.t1 ?? t.t0))
  function jumpTo(ts: number): void {
    let j = -1
    for (let i = 0; i < t1s.length; i++) if (t1s[i] >= ts) { j = i; break }
    if (j < 0) j = turns.length - 1
    if (j >= 0) onJump(j)
  }

  // 时间网格:在整秒/整分边界上取 ≤ 7 条
  const STEPS = [1e3, 2e3, 5e3, 10e3, 15e3, 30e3, 60e3, 120e3, 300e3, 600e3, 900e3, 1800e3, 3600e3]
  const st = STEPS.find(v => (t1 - t0) / v <= 7) ?? 3600e3
  for (let v = Math.ceil(t0 / st) * st; v <= t1; v += st) {
    const xx = X(v)
    svg.appendChild(s('line', { x1: xx, x2: xx, y1: 12, y2: axisY, class: 'grid' }))
  }

  // 泳道名(直接标签,不靠颜色区分)
  for (const [lx, ly, str] of [[8, baseA - 4, 'a'], [8, baseB - 4, 'b'], [8, gitY + 3, 'git'], [8, gateY + 3, '门'], [8, boardY + 3, '板']] as [number, number, string][]) {
    svg.appendChild(s('text', { x: lx, y: ly, class: 'lane' }, str))
  }

  // 轮:竖条,高度 ∝ min(工具数, 8)
  turns.forEach((t, i) => {
    const xx = X(ms(t.t0))
    const hgt = 6 + Math.min(t.calls.length, 8) * 1.6
    const base = t.actor === 'a' ? baseA : baseB
    const g = s('g')
    g.appendChild(s('title', {}, `第 ${i + 1} 轮 · actor ${t.actor} · ${hhmmss(t.t0, true)} · ${t.calls.length} 次工具调用 · ${dur(t.t0, t.t1)}`))
    const bar = s('rect', { x: xx - 1.5, y: base - hgt, width: 3, height: hgt, rx: 1, fill: t.actor === 'a' ? COLOR.frame : COLOR.impl })
    g.appendChild(bar)
    const hit = s('rect', { x: xx - 5, y: base - 22, width: 10, height: 24, class: 'hit' })
    hit.addEventListener('click', () => onJump(i))
    g.appendChild(hit)
    marks.push({ el: g, ts: ms(t.t0) })
    tickEls.push(bar)
    svg.appendChild(g)
  })

  // git 提交:普通 = 实心菱形;merge = 玫红实边圆(白底);tag = 蓝实边环 + 短标签。
  // 三层分开收集、按 普通 → merge → tag 的顺序统一追加:后画的普通标记不会遮住 merge/tag。
  const plainEls: SVGElement[] = []
  const mergeEls: SVGElement[] = []
  const ringEls: SVGElement[] = []
  for (const c of b.git.commits) {
    const xx = X(ms(c.date))
    const merge = c.parents.length > 1
    const tag = b.git.tags.find(t => t.sha === c.sha)
    const g = s('g', { transform: `translate(${xx},${gitY})` })
    g.appendChild(s('title', {}, `${c.sha.slice(0, 7)} ${c.subject}\n${hhmmss(c.date, true)} · 分支 ${c.branches.join('/') || '—'}${tag ? ` · tag ${tag.name}` : ''}`))
    if (merge) g.appendChild(s('circle', { r: 4.8, fill: '#fff', stroke: COLOR.find, 'stroke-width': 2.2 }))
    else g.appendChild(s('path', { d: 'M-5,0L0,-5.5L5,0L0,5.5Z', fill: COLOR.line, stroke: COLOR.line, 'stroke-width': 1.2 }))
    const hit = s('rect', { x: -6, y: -9, width: 12, height: 18, class: 'hit' })
    hit.addEventListener('click', () => jumpTo(ms(c.date)))
    g.appendChild(hit)
    marks.push({ el: g, ts: ms(c.date) })
    ;(merge ? mergeEls : plainEls).push(g)
    if (tag) {
      const tg = s('g', { transform: `translate(${xx},${gitY})` })
      tg.appendChild(s('title', {}, `${tag.name} → ${c.sha.slice(0, 7)}`))
      tg.appendChild(s('circle', { r: 9, fill: 'none', stroke: COLOR.frame, 'stroke-width': 2 }))
      tg.appendChild(s('text', { x: 0, y: -13, class: 'lbl sm', 'text-anchor': 'middle' }, tag.name.replace(/^ckpt-/, '')))
      const th = s('rect', { x: -9.5, y: -9.5, width: 19, height: 19, class: 'hit' })
      th.addEventListener('click', () => jumpTo(ms(c.date)))
      tg.appendChild(th)
      marks.push({ el: tg, ts: ms(c.date) })
      ringEls.push(tg)
    }
  }
  for (const el of [...plainEls, ...mergeEls, ...ringEls]) svg.appendChild(el)

  // 协议事件:门 = 竖线(wait-start 虚 / allow 粗 / fast 细)
  for (const e of b.ops.gate) {
    const xx = X(ms(e.ts))
    const g = s('g')
    const kind = e.text.startsWith('wait-start') ? 'start' : e.text.startsWith('allow-after-wait') ? 'allow' : 'fast'
    const extra = kind === 'start' ? { 'stroke-dasharray': '2 2', 'stroke-width': 1.2 } : kind === 'allow' ? { 'stroke-width': 2.4 } : { 'stroke-width': 1 }
    g.appendChild(s('title', {}, `门 · ${hhmmss(e.ts, true)} · ${e.text}`))
    g.appendChild(s('line', { x1: xx, x2: xx, y1: gateY - 7, y2: gateY + 7, stroke: COLOR.muted, ...extra }))
    const hit = s('rect', { x: xx - 4, y: gateY - 8, width: 8, height: 16, class: 'hit' })
    hit.addEventListener('click', () => jumpTo(ms(e.ts)))
    g.appendChild(hit)
    marks.push({ el: g, ts: ms(e.ts) })
    svg.appendChild(g)
  }

  // 协议事件:板 = 方块
  for (const e of b.ops.board) {
    const ts = e.createdAt ? new Date(e.createdAt).toISOString() : null
    const xx = X(ms(ts))
    const g = s('g')
    g.appendChild(s('title', {}, `板 · ${e.kind} · ${hhmmss(ts, true)} · ${e.subject ?? ''} · by ${e.createdBy ?? '?'}`))
    g.appendChild(s('rect', { x: xx - 3.5, y: boardY - 3.5, width: 7, height: 7, fill: COLOR.warn }))
    const hit = s('rect', { x: xx - 5, y: boardY - 6, width: 10, height: 12, class: 'hit' })
    hit.addEventListener('click', () => jumpTo(ms(ts)))
    g.appendChild(hit)
    marks.push({ el: g, ts: ms(ts) })
    svg.appendChild(g)
  }

  // 时间轴
  const axis = s('g')
  axis.appendChild(s('line', { x1: x0, x2: x1, y1: axisY, y2: axisY, class: 'axis-line' }))
  for (let v = Math.ceil(t0 / st) * st; v <= t1; v += st) {
    const xx = X(v)
    axis.appendChild(s('line', { x1: xx, x2: xx, y1: axisY, y2: axisY + 4, class: 'axis-tick' }))
    axis.appendChild(text(xx, axisY + 15, hhmmss(new Date(v).toISOString()), { 'text-anchor': 'middle', class: 'lbl sm' }))
  }
  svg.appendChild(axis)

  // 当前步游标
  const cursor = s('line', { class: 'rp-cursor', x1: x0, x2: x0, y1: 12, y2: axisY })
  const curLbl = s('text', { class: 'lbl strong', 'text-anchor': 'middle', x: x0, y: 10 })
  svg.appendChild(cursor)
  svg.appendChild(curLbl)

  function setCurrent(k: number): void {
    const t = turns[k]
    if (!t) return
    const end = ms(t.t1 ?? t.t0)
    for (const m of marks) m.el.classList.toggle('dim', !(m.ts <= end))
    tickEls.forEach((el, i) => el.classList.toggle('cur', i === k))
    const xx = Math.min(Math.max(X(ms(t.t0)), x0), x1)
    cursor.setAttribute('x1', String(xx))
    cursor.setAttribute('x2', String(xx))
    curLbl.setAttribute('x', String(Math.min(Math.max(xx, x0 + 30), x1 - 30)))
    curLbl.textContent = `第 ${k + 1} 轮`
  }

  return { el: svg, setCurrent }
}
