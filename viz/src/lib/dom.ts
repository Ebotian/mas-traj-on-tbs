type Handler = (ev: Event) => void
type Attrs = Record<string, string | number | boolean | Handler | undefined | null>
/** Kids may be null/undefined/false so a caller can write `cond ? node : null` inline. */
type Kid = Node | string | null | undefined | false

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K, attrs: Attrs = {}, ...kids: Kid[]
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue
    if (k === 'class') e.className = String(v)
    else if (k === 'html') e.innerHTML = String(v)
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v)
    else e.setAttribute(k, String(v))
  }
  append(e, kids)
  return e
}

function append(parent: Element, kids: Kid[]): void {
  for (const k of kids) {
    if (k === null || k === undefined || k === false) continue
    parent.appendChild(typeof k === 'string' ? document.createTextNode(k) : k)
  }
}

export function clear(el: Element): void { while (el.firstChild) el.removeChild(el.firstChild) }

/** Escape user-facing text that goes through innerHTML (quotes contain markup chars). */
export function esc(v: string): string {
  return v.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string))
}

export function table(headers: string[], rows: (string | Node)[][], cls: string[] = []): HTMLTableElement {
  const t = h('table', { class: 'tbl' })
  const thead = h('thead')
  const hr = h('tr')
  headers.forEach(x => hr.appendChild(h('th', {}, x)))
  thead.appendChild(hr)
  t.appendChild(thead)
  const tb = h('tbody')
  rows.forEach((r, i) => {
    const tr = h('tr', { class: cls[i] ?? '' })
    r.forEach(c => tr.appendChild(h('td', {}, ...(typeof c === 'string' ? [c] : [c]))))
    tb.appendChild(tr)
  })
  t.appendChild(tb)
  return t
}

export function cite(v: string): HTMLSpanElement {
  return h('span', { class: 'cite' }, v)
}

export function badge(label: string, color: string): HTMLSpanElement {
  return h('span', { class: 'badge', style: `color:${color};border-color:${color}` }, label)
}

/** Small stat tile. `tone` drives the left rule colour, nothing else. */
export function stat(value: string, label: string, tone = 'var(--rule)'): HTMLDivElement {
  return h('div', { class: 'stat', style: `border-left-color:${tone}` },
    h('b', {}, value), h('span', {}, label))
}

export function panel(title: string, ...body: Kid[]): HTMLElement {
  const c = h('section', { class: 'card' })
  c.appendChild(h('h2', {}, title))
  const b = h('div', { class: 'cardbody' })
  append(b, body)
  c.appendChild(b)
  return c
}

export function note(...kids: Kid[]): HTMLParagraphElement {
  return h('p', { class: 'note' }, ...kids)
}
