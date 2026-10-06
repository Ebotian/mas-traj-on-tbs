export const NS = 'http://www.w3.org/2000/svg'

type Attrs = Record<string, string | number | undefined | null>

export function s(tag: string, attrs: Attrs = {}, ...kids: (Node | string)[]): SVGElement {
  const e = document.createElementNS(NS, tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null) continue
    e.setAttribute(k, String(v))
  }
  for (const k of kids) e.appendChild(typeof k === 'string' ? document.createTextNode(k) : k)
  return e
}

export function text(x: number, y: number, str: string, attrs: Attrs = {}): SVGElement {
  return s('text', { x, y, class: 'lbl', ...attrs }, str)
}

export interface Scale {
  (v: number): number
  domain: [number, number]
  range: [number, number]
  invert(px: number): number
  ticks(n?: number): number[]
}

/** Linear scale. `ticks` returns human-friendly round numbers, not raw steps. */
export function linear(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain
  const [r0, r1] = range
  const span = d1 - d0 || 1
  const f = ((v: number) => r0 + ((v - d0) / span) * (r1 - r0)) as Scale
  f.domain = domain
  f.range = range
  f.invert = (px: number) => d0 + ((px - r0) / ((r1 - r0) || 1)) * span
  f.ticks = (n = 5) => {
    const raw = span / Math.max(1, n)
    const mag = Math.pow(10, Math.floor(Math.log10(raw)))
    const norm = raw / mag
    const step = (norm >= 7.5 ? 10 : norm >= 3.5 ? 5 : norm >= 1.5 ? 2 : 1) * mag
    const out: number[] = []
    for (let v = Math.ceil(d0 / step) * step; v <= d1 + step * 1e-9; v += step) {
      out.push(Math.abs(v) < step * 1e-9 ? 0 : Number(v.toPrecision(12)))
    }
    return out
  }
  return f
}

export function axisBottom(sc: Scale, y: number, fmt: (v: number) => string = String): SVGElement {
  const g = s('g', { class: 'axis' })
  g.appendChild(s('line', { x1: sc.range[0], x2: sc.range[1], y1: y, y2: y, class: 'axis-line' }))
  for (const t of sc.ticks(6)) {
    const x = sc(t)
    g.appendChild(s('line', { x1: x, x2: x, y1: y, y2: y + 5, class: 'axis-tick' }))
    g.appendChild(text(x, y + 17, fmt(t), { 'text-anchor': 'middle', class: 'lbl sm' }))
  }
  return g
}

export function axisLeft(sc: Scale, x: number, fmt: (v: number) => string = String): SVGElement {
  const g = s('g', { class: 'axis' })
  g.appendChild(s('line', { x1: x, x2: x, y1: sc.range[0], y2: sc.range[1], class: 'axis-line' }))
  for (const t of sc.ticks(5)) {
    const y = sc(t)
    g.appendChild(s('line', { x1: x - 5, x2: x, y1: y, y2: y, class: 'axis-tick' }))
    g.appendChild(s('line', { x1: x, x2: sc.range[1], y1: y, y2: y, class: 'grid' }))
    g.appendChild(text(x - 8, y + 3.5, fmt(t), { 'text-anchor': 'end', class: 'lbl sm' }))
  }
  return g
}

export function polyline(pts: [number, number][]): string {
  return pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join('')
}

/** Arrowhead marker; `id` must be unique per document. */
export function arrowMarker(id: string, color: string): SVGElement {
  return s('marker', {
    id, viewBox: '0 0 10 10', refX: 9, refY: 5,
    markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse',
  }, s('path', { d: 'M0,0L10,5L0,10z', fill: color }))
}

export function shapePath(shape: 'circle' | 'square' | 'diamond' | 'tri', r: number): { tag: string; attrs: Attrs } {
  if (shape === 'circle') return { tag: 'circle', attrs: { r } }
  if (shape === 'square') return { tag: 'rect', attrs: { x: -r * 0.86, y: -r * 0.86, width: r * 1.72, height: r * 1.72, rx: 2 } }
  if (shape === 'diamond') {
    const q = r * 1.18
    return { tag: 'path', attrs: { d: `M0,${-q}L${q},0L0,${q}L${-q},0Z` } }
  }
  const q = r * 1.2
  return { tag: 'path', attrs: { d: `M0,${-q}L${r * 1.12},${r * 0.92}L${-r * 1.12},${r * 0.92}Z` } }
}

export const fmt = {
  n: (v: number, d = 2) => v.toFixed(d),
  pp: (v: number, d = 2) => `${v.toFixed(d)} pp`,
  pct: (v: number, d = 1) => `${(v * 100).toFixed(d)}%`,
  int: (v: number) => v.toLocaleString('en-US'),
  z: (v: number) => `${v > 0 ? '' : '−'}${Math.abs(v).toFixed(1)}σ`,
}
