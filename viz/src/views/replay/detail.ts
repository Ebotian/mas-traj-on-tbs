// replay/detail.ts —— 本步详情:一轮的完全展开。
//
// 渲染按 parts 原始顺序(思考 / 正文 / 工具调用交错),每条工具调用挂上其 tool_result
// (状态、exit、输出折叠)。末尾三块:归属到本步的系统事件、孤立结果(未配对)、本步的
// 原始 JSONL 行(raw 原文)。全部内容都在,默认状态只决定折叠与否。

import { h, badge } from '../../lib/dom.ts'
import type { ReplayBundle, ReplayFunctionCall, ReplayResult, ReplaySystem, ReplayTurn } from './data.ts'
import { actorMeta, dur, fmtBytes, hhmmss } from './data.ts'

export function pre(str: string, cls = ''): HTMLPreElement {
  return h('pre', { class: `rp-pre${cls ? ` ${cls}` : ''}` }, str)
}

export function details(summary: string, body: Node, open = false, cls = ''): HTMLDetailsElement {
  const d = h('details', { class: cls })
  if (open) d.open = true
  d.appendChild(h('summary', {}, summary))
  d.appendChild(body)
  return d
}

function statusTone(r: ReplayResult): string {
  if (r.status === 'success') return 'var(--green)'
  if (r.status) return 'var(--rose)'
  return 'var(--mut)'
}

function callBlock(fc: ReplayFunctionCall, t: ReplayTurn): HTMLElement {
  const rec = t.calls.find(c => (c.call.id && c.call.id === fc.id) || (c.call.callId && c.call.callId === fc.id))
  const r = rec?.result ?? null
  const args = (fc.args ?? {}) as Record<string, unknown>
  const box = h('div', { class: 'rp-call' })
  const hd = h('div', { class: 'rp-call-h' }, h('code', {}, fc.name ?? 'tool'))
  if (r) {
    const exit = typeof r.resultDisplay?.exitCode === 'number' ? ` · exit ${r.resultDisplay.exitCode}` : ''
    const st = r.status === 'success' ? 'success' : (r.status ?? '?')
    hd.appendChild(badge(st + exit, statusTone(r)))
    if (r.ts) hd.appendChild(h('span', { class: 'rp-now' }, `结果 @ ${hhmmss(r.ts, true)}`))
  } else {
    hd.appendChild(badge('无配对结果', 'var(--mut)'))
  }
  box.appendChild(hd)
  const body = h('div', { class: 'rp-call-b' })
  if (typeof args.command === 'string') body.appendChild(pre(args.command))
  else if (typeof args.file_path === 'string') body.appendChild(pre(String(args.file_path)))
  if (typeof args.description === 'string' && args.description) body.appendChild(h('div', { class: 'note' }, args.description))
  body.appendChild(details('参数 JSON(完整)', pre(JSON.stringify(args, null, 1)), false, 'rp-args'))
  if (r) {
    const dm = r.resultDisplay
    const out = dm && typeof dm.output === 'string' ? dm.output : ''
    if (out) {
      body.appendChild(details(`输出(${fmtBytes(out.length)}${typeof dm?.exitCode === 'number' ? ` · exit ${dm.exitCode}` : ''})`, pre(out), out.length < 600))
    } else if (r.parts.length) {
      body.appendChild(details('结果部件(完整)', pre(JSON.stringify(r.parts, null, 1)), r.parts.length < 4))
    } else if (dm) {
      body.appendChild(details(`结果(resultDisplay · ${String(dm.type ?? '未知类型')})`, pre(JSON.stringify(dm, null, 1)), true))
    }
    if (r.raw) body.appendChild(details('原始行(tool_result,原文)', pre(r.raw), false, 'rp-raw'))
  }
  box.appendChild(body)
  return box
}

function orphanBlock(r: ReplayResult): HTMLElement {
  const box = h('div', { class: 'rp-call' })
  box.appendChild(h('div', { class: 'rp-call-h' }, h('code', {}, '孤立结果(未与调用配对)'),
    badge(r.status ?? '?', statusTone(r)), r.ts ? h('span', { class: 'rp-now' }, hhmmss(r.ts, true)) : null))
  const body = h('div', { class: 'rp-call-b' })
  const dm = r.resultDisplay
  const out = dm && typeof dm.output === 'string' ? dm.output : ''
  if (out) body.appendChild(pre(out))
  else body.appendChild(pre(JSON.stringify(dm ?? r.parts, null, 1)))
  if (r.raw) body.appendChild(details('原始行(tool_result,原文)', pre(r.raw), false, 'rp-raw'))
  box.appendChild(body)
  return box
}

function snapSummary(payload: unknown): string {
  const p = payload as { snapshot?: { type?: string; promptCount?: number; surface?: string } } | null
  if (p?.snapshot) return `${p.snapshot.type ?? 'snapshot'}${p.snapshot.surface ? ` · ${p.snapshot.surface}` : ''}${typeof p.snapshot.promptCount === 'number' ? ` · promptCount ${p.snapshot.promptCount}` : ''}`
  const j = JSON.stringify(payload)
  return j ? j.slice(0, 72) : '(空)'
}

export function renderDetail(b: ReplayBundle, k: number, sysEvents: ReplaySystem[]): HTMLElement {
  const turns = b.sessions.turns
  const t = turns[k]
  const am = actorMeta(b, t.actor)
  const wrap = h('div')
  const nth = turns.slice(0, k + 1).filter(x => x.actor === t.actor).length
  const u = t.usage
  const tokenLine = u
    ? `tokens in ${(u.promptTokenCount ?? 0).toLocaleString('en-US')}${u.cachedContentTokenCount ? `(缓存 ${u.cachedContentTokenCount.toLocaleString('en-US')})` : ''} · out ${(u.candidatesTokenCount ?? 0).toLocaleString('en-US')}${u.thoughtsTokenCount ? ` · 思考 ${u.thoughtsTokenCount.toLocaleString('en-US')}` : ''}`
    : 'tokens —'

  const btnAll = h('button', { class: 'btn', onclick: () => wrap.querySelectorAll('details').forEach(d => { (d as HTMLDetailsElement).open = true }) }, '展开全部')
  const btnNone = h('button', { class: 'btn', onclick: () => wrap.querySelectorAll('details').forEach(d => { (d as HTMLDetailsElement).open = false }) }, '折叠全部')
  wrap.appendChild(h('div', { class: 'rp-dhead' },
    badge(`actor ${t.actor} · ${am.model} · ${am.effort}`, t.actor === 'a' ? 'var(--blue)' : 'var(--green)'),
    h('b', {}, `第 ${k + 1} 轮 / ${turns.length}`),
    h('span', {}, `该会话第 ${nth} 步`),
    h('span', { class: 'rp-now' }, `${hhmmss(t.t0, true)} → ${hhmmss(t.t1)} UTC(${dur(t.t0, t.t1)})`),
    h('span', { class: 'rp-now' }, tokenLine),
    h('span', { class: 'sp' }, btnAll, btnNone)))

  for (const p of t.parts) {
    if (p.thought) {
      const str = String(p.text ?? '')
      wrap.appendChild(details(`思考 · ${str.length.toLocaleString('en-US')} 字`, pre(str), false, 'rp-th'))
    } else if (typeof p.text === 'string') {
      wrap.appendChild(h('div', { class: 'rp-text' }, pre(p.text)))
    } else if (p.functionCall) {
      wrap.appendChild(callBlock(p.functionCall, t))
    }
  }
  for (const r of t.results) wrap.appendChild(orphanBlock(r))

  if (sysEvents.length) {
    const lst = h('div')
    for (const ev of sysEvents) {
      lst.appendChild(details(`${hhmmss(ev.ts, true)} · ${snapSummary(ev.payload)}`,
        h('div', {}, pre(JSON.stringify(ev.payload, null, 1)), ev.raw ? pre(ev.raw, 'soft') : h('span')), false))
    }
    wrap.appendChild(details(`会话系统事件 ${sysEvents.length} 条(本步前,actor ${t.actor})`, lst, false, 'rp-sys'))
  }

  wrap.appendChild(details('本步原始 JSONL(assistant 行,原文)', pre(t.raw ?? '(缺失)'), false, 'rp-raw'))
  return wrap
}
