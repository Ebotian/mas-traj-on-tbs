// 逐路由渲染探针 —— 替代「在浏览器里每个路由查一个已知串」的手工检查,使其可重复。
//
//   npm run probe          (从 viz/ 运行)
//
// 它做的事:给一个最小 DOM 桩,按顺序 import 每个视图并调用 render(host),断言
// (a) 不抛错、(b) 每个路由的关键串在场、(c) 已知的「从数据现算」的串与数据一致。
// 它**不**覆盖:布局、交互、CSS、以及 numbers 视图(numbers 直接 import experiments.json,
// node ESM 需要 import attribute —— 它只能靠构建期或浏览器检查)。
//
// 为什么存在:视图里的文字数字会悄悄过期(2026-10-07 就抓到 time 视图仍写「中间版本永久缺失」,
// 以及 map 视图手写的「7 个节点」而数据是 6 个)。改完视图必须重跑本脚本。

import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')

class El {
  constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.parent = null; this.style = {}; this._text = ''; this._listeners = {} }
  setAttribute(k, v) { this.attrs[k] = String(v) }
  getAttribute(k) { return this.attrs[k] ?? null }
  appendChild(c) { c.parent = this; this.children.push(c); return c }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c }
  get firstChild() { return this.children[0] ?? null }
  addEventListener(t, fn) { (this._listeners[t] ??= []).push(fn) }
  set className(v) { this.attrs.class = v } get className() { return this.attrs.class ?? '' }
  set textContent(v) { this._text = String(v); this.children = [] } get textContent() { return this.text() }
  set innerText(v) { this.textContent = v } get innerText() { return this.text() }
  set innerHTML(v) { this._text = String(v); this.children = [] } get innerHTML() { return this._text }
  querySelectorAll(sel) {
    const out = []
    const byClass = sel.startsWith('.')
    const want = byClass ? sel.slice(1) : sel
    const walk = (n) => { for (const c of n.children) { if (byClass ? (c.attrs.class ?? '').split(/\s+/).includes(want) : c.tag === sel) out.push(c); walk(c) } }
    walk(this); return out
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] ?? null }
  text() { return this.children.map(c => c.text()).join('') + (this.children.length ? '' : this._text) }
}

globalThis.document = {
  createElement: (t) => new El(t),
  createElementNS: (_ns, t) => new El(t),
  createTextNode: (s) => { const e = new El('#text'); e._text = String(s); return e },
}

const ROUTES = [
  ['overview', 'src/views/overview.ts', ['G₀', 'epistemic debt', '九条工程原则', 'Taste ⇄ SOP ⇄ IaC']],
  ['map', 'src/views/map.ts', ['只看二手+未读', '6 个节点(2 二手 + 4 未读)', '独立再证', '我复核', '二手(调查者)', '我没读']],
  ['time', 'src/views/time.ts', ['09-09 → 10-08', '外部复核 1–6 轮', 'B 线六版审查', '原判「中间版本永久缺失」已推翻', '09-30、10-06、10-07 与 10-08', '语料日(二)']],
  ['conflicts', 'src/views/conflicts.ts', ['条冲突', '条已登记的反转', '外部复核 #6 → 收口(10-07)']],
  ['decisions', 'src/views/decisions.ts', ['D33', 'D1', '代理谬误']],
  ['coverage', 'src/views/coverage.ts', ['语料 73 个文件', '105356', '8511']],
  ['library', 'src/views/library.ts', ['取不到:原因已查明', '取不到:仅记录现象', '未取(是重复件)', '未尝试', '六版独立审查']],
]

let bad = 0
for (const [name, rel, expects] of ROUTES) {
  try {
    const mod = await import(pathToFileURL(path.join(ROOT, 'viz', rel)).href)
    const host = new El('#root')
    mod.render(host)
    const txt = host.text()
    const missing = expects.filter(e => !txt.includes(e))
    const ok = missing.length === 0
    if (!ok) bad++
    console.log(`${ok ? '✓' : '✗'} ${name.padEnd(10)} 渲染 OK,文本 ${String(txt.length).padStart(6)} 字符` + (ok ? '' : ` —— 缺串: ${JSON.stringify(missing)}`))
  } catch (e) {
    bad++
    console.log(`✗ ${name.padEnd(10)} 渲染抛错: ${e && e.message}`)
  }
}
console.log(bad === 0
  ? `\n${ROUTES.length}/${ROUTES.length} 路由渲染通过且关键串在场(不含 numbers:见文件头)`
  : `\n${bad} 条路由有问题`)
process.exit(bad === 0 ? 0 : 1)
