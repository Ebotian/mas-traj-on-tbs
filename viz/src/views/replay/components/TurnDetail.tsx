// replay/components/TurnDetail.tsx —— 本步详情:parts 原序展开(思考可折叠、工具卡+输出/原始行、系统事件、JSONL原文)。
// 折叠块用 Fold 惰性渲染:内容只在首次展开时进 DOM —— 18 万字的大思考与原始行不至于拖慢每步切换。

import { useState, type CSSProperties, type ReactNode, type SyntheticEvent } from 'react'
import type { ReplayTurn, ReplaySystem } from '../data'
import { hhmmss, dur, fmtBytes } from '../data'

interface Used { promptTokenCount?: number; candidatesTokenCount?: number; thoughtsTokenCount?: number; cachedContentTokenCount?: number }
interface Props { turn: ReplayTurn; nth: number; used?: Used; sysEvents: ReplaySystem[] }

function preBlock(str: string, soft = false) {
  return (
    <pre className="rp-pre" style={{
      whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace',
      fontSize: '11.5px', lineHeight: '1.45', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px',
      padding: '7px 9px', margin: '5px 0', maxHeight: '360px', overflow: 'auto',
      ...(soft ? { background: '#f8fafc', color: '#475569' } : {}),
    }}>{str}</pre>
  )
}

function Fold({ summary, children, style, sumStyle, cls = '' }: { summary: ReactNode; children: ReactNode; style?: CSSProperties; sumStyle?: CSSProperties; cls?: string }) {
  const [shown, setShown] = useState(false)
  return (
    <details className={`rp-toggle-details${cls ? ` ${cls}` : ''}`} style={style}
      onToggle={(e: SyntheticEvent<HTMLDetailsElement>) => { if (e.currentTarget.open) setShown(true) }}>
      <summary style={{ fontSize: '11.5px', color: '#64748b', cursor: 'pointer', ...sumStyle }}>{summary}</summary>
      {shown ? children : null}
    </details>
  )
}

export default function TurnDetail({ turn, nth, used, sysEvents }: Props) {
  const actColor = turn.actor === 'a' ? '#1d4ed8' : '#166534'

  const toggleAll = (open: boolean) => {
    document.querySelectorAll<HTMLDetailsElement>('.rp-toggle-details').forEach(el => { el.open = open })
  }

  return (
    <div>
      {/* Header */}
      <div className="rp-dhead">
        <span style={{ fontSize: '10.5px', fontWeight: 600, padding: '1px 7px', border: `1px solid ${actColor}`, borderRadius: '999px', color: actColor, whiteSpace: 'nowrap' }}>
          actor {turn.actor}{turn.model ? ` · ${turn.model}` : ''}
        </span>
        <b style={{ fontWeight: 700 }}>第 {nth} 步</b>
        {turn.t0 && (
          <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11.5px', color: '#64748b' }}>
            {hhmmss(turn.t0, true)} UTC{turn.t1 ? ` → ${hhmmss(turn.t1)}` : ''} ({dur(turn.t0, turn.t1)})
          </span>
        )}
        {used && (
          <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11.5px', color: '#64748b' }}>
            in {(used.promptTokenCount || 0).toLocaleString()}{used.cachedContentTokenCount ? `(缓存 ${used.cachedContentTokenCount.toLocaleString()})` : ''} · out {(used.candidatesTokenCount || 0).toLocaleString()} · 思考 {(used.thoughtsTokenCount || 0).toLocaleString()}
          </span>
        )}
        <span className="sp">
          <button className="btn" onClick={() => toggleAll(true)}>展开全部</button>
          <button className="btn" onClick={() => toggleAll(false)}>折叠全部</button>
        </span>
      </div>

      {/* Parts in original order */}
      {turn.parts.map((p, pi) => {
        if (p.thought) {
          const txt = String(p.text ?? '')
          const head = txt.length >= 200 ? `${txt.slice(0, 200)}… (${txt.length.toLocaleString()}字)` : `${txt} (${txt.length.toLocaleString()}字)`
          return (
            <Fold key={'th-' + pi} cls="rp-th"
              style={{ border: '1px solid #e2e8f0', borderLeft: '3px solid #475569', borderRadius: '7px', margin: '6px 0', background: '#f8fafc' }}
              sumStyle={{ fontSize: '12px', padding: '5px 9px' }}
              summary={`思考 · ${head}`}>
              {preBlock(txt)}
            </Fold>
          )
        }
        if (typeof p.text === 'string') {
          return <div key={'tx-' + pi} style={{ margin: '6px 0' }}>{preBlock(p.text)}</div>
        }
        if (p.functionCall) {
          const fc = p.functionCall
          const match = turn.calls.find(c => (c.call.id && c.call.id === fc.id) || (c.call.callId && c.call.callId === fc.id))
          const rec = match?.result ?? null
          const args = (fc.args ?? {}) as Record<string, unknown>
          const name = fc.name ?? 'tool'
          const dm = rec?.resultDisplay ?? null
          const out = dm && typeof dm.output === 'string' ? dm.output : ''
          const exit = dm && typeof dm.exitCode === 'number' ? dm.exitCode : null
          const statusTone = rec?.status === 'success' ? '#166534' : rec?.status ? '#be123c' : '#64748b'

          return (
            <div key={'call-' + pi} className="rp-call" style={{ border: '1px solid #e2e8f0', borderRadius: '8px', margin: '8px 0' }}>
              <div className="rp-call-h" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 10px', alignItems: 'center', padding: '6px 10px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: '12px' }}>
                <code style={{ fontWeight: 600 }}>{name}</code>
                {rec && <span style={{ fontSize: '10.5px', fontWeight: 600, padding: '1px 7px', border: `1px solid ${statusTone}`, borderRadius: '999px', color: statusTone }}>{rec.status ?? '?'}{exit !== null ? ` · exit ${exit}` : ''}</span>}
                {!rec && <span style={{ fontSize: '10.5px', fontWeight: 600, padding: '1px 7px', border: '1px solid #e2e8f0', borderRadius: '999px', color: '#64748b' }}>无结果记录</span>}
                {rec?.ts && <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11.5px', color: '#64748b' }}>结果 @ {hhmmss(rec.ts, true)}</span>}
              </div>
              <div style={{ padding: '8px 10px' }}>
                {typeof args.command === 'string' && <div style={{ marginTop: '8px' }}>{preBlock(args.command)}</div>}
                {typeof args.file_path === 'string' && <div style={{ marginTop: '8px' }}>{preBlock(String(args.file_path))}</div>}
                {typeof args.description === 'string' && args.description && <p style={{ fontSize: '12.5px', color: '#334155', margin: '9px 0 0' }}>{args.description}</p>}
                {Object.keys(args).length > 0 && <Fold summary="参数 JSON(完整)">{preBlock(JSON.stringify(args, null, 1))}</Fold>}
                {out && <Fold summary={`输出(${fmtBytes(out.length)}${exit !== null ? ` · exit ${exit}` : ''})`}>{preBlock(out)}</Fold>}
                {rec && dm && !dm.type && Object.keys(dm).length > 0 && <Fold summary="结果(resultDisplay)">{preBlock(JSON.stringify(dm, null, 1))}</Fold>}
                {rec?.raw && <Fold cls="rp-raw" summary="原始行(tool_result,原文)">{preBlock(rec.raw, true)}</Fold>}
              </div>
            </div>
          )
        }
        return null
      })}

      {/* Orphan results */}
      {turn.results.filter(r => !r.callId).map((r, i) => (
        <div key={'orph-' + i} className="rp-call" style={{ border: '1px solid #e2e8f0', borderRadius: '8px', margin: '8px 0' }}>
          <div className="rp-call-h" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 10px', alignItems: 'center', padding: '6px 10px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: '12px' }}>
            <code>孤立结果(未与调用配对)</code>
            {r.status && <span style={{ fontSize: '10.5px', fontWeight: 600, padding: '1px 7px', border: '1px solid #64748b', borderRadius: '999px', color: '#64748b' }}>{r.status}</span>}
          </div>
        </div>
      ))}

      {/* System events */}
      {sysEvents.length > 0 && (
        <Fold cls="rp-sys" style={{ border: '1px solid #e2e8f0', borderRadius: '7px', margin: '8px 0', padding: '6px 9px' }} sumStyle={{ fontSize: '12px' }}
          summary={`会话系统事件 ${sysEvents.length} 条(本步前,${turn.actor})`}>
          {sysEvents.map((ev, i) => (
            <Fold key={'sys-' + i} style={{ margin: '5px 0' }}
              summary={`${hhmmss(ev.ts, true)} · ${typeof ev.payload === 'object' && ev.payload ? JSON.stringify(ev.payload).slice(0, 140) : '(空)'}`}>
              {preBlock(typeof ev.payload === 'object' ? JSON.stringify(ev.payload, null, 1) : String(ev.payload))}
              {ev.raw && <Fold cls="rp-raw" summary="原始行(system,原文)">{preBlock(ev.raw, true)}</Fold>}
            </Fold>
          ))}
        </Fold>
      )}

      {/* Raw JSONL */}
      {turn.raw && <Fold cls="rp-raw" summary="本步原始 JSONL(assistant 行,原文)">{preBlock(turn.raw, true)}</Fold>}
    </div>
  )
}
