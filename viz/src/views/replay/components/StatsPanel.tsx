// StatsPanel.tsx —— 时间与成本统计:tokens 分布(uncached/cache/out)与映射成本。
// 口径与 walkthrough/tasks/walkthrough/metrics.py 同源(费率卡 2026-10-10;见 bundle.stats.mapping)。
import type { ReplayBundle } from '../data'

function fmtTok(n: number): string {
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'
  return String(n)
}
function fmtMs(ms: number | null): string {
  if (ms == null) return '—'
  if (ms < 1000) return ms + 'ms'
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's'
  const m = Math.floor(ms / 60000), s = Math.round((ms % 60000) / 1000)
  return `${m}m${s ? s + 's' : ''}`
}
function median(a: number[]): number | null {
  if (!a.length) return null
  const s = [...a].sort((x, y) => x - y)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2)
}
function p90(a: number[]): number | null {
  if (!a.length) return null
  const s = [...a].sort((x, y) => x - y)
  return s[Math.min(s.length - 1, Math.floor(0.9 * (s.length - 1)))]
}
const ACTCOLOR: Record<string, string> = { a: '#1d4ed8', b: '#166534', s: '#7c3aed' }

export default function StatsPanel({ bundle }: { bundle: ReplayBundle }) {
  const s = bundle.stats
  if (!s || !s.actors || !Object.keys(s.actors).length) {
    return (
      <div className="card"><h2>时间与成本统计</h2>
        <p className="note" style={{ padding: '4px 12px 10px' }}>
          此 bundle 无 stats(由 2026-10-12 之前的构建生成)。运行 <code>bash viz/scripts/refresh_replays.sh {bundle.exp}</code> 可补齐。
        </p>
      </div>
    )
  }
  const rows = Object.entries(s.actors).sort(([x], [y]) => x.localeCompare(y))
  const grand = rows.reduce((n, [, st]) => n + (st.tokens?.total || 0), 0)
  return (
    <div className="card">
      <h2>时间与成本统计</h2>
      <div style={{ padding: '4px 12px 10px' }}>
        {rows.map(([act, st]) => {
          const tok = st.tokens
          const total = tok.total || 1
          const seg = (n: number, color: string, title: string) => (
            <span title={`${title} ${n.toLocaleString()}`} style={{ display: 'inline-block', width: `${(n / total * 100).toFixed(2)}%`, height: 10, background: color }} />
          )
          const med = median(st.durations_ms), p90v = p90(st.durations_ms)
          const maxd = st.durations_ms.length ? Math.max(...st.durations_ms) : null
          const c = st.cost
          return (
            <div key={act} style={{ margin: '8px 0', borderBottom: '1px solid #f1f5f9', paddingBottom: 7 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', fontSize: '11.5px', fontFamily: 'ui-monospace,Menlo,monospace' }}>
                <span style={{ fontWeight: 600, padding: '1px 7px', border: `1px solid ${ACTCOLOR[act] || '#334155'}`, borderRadius: 999, color: ACTCOLOR[act] || '#334155', whiteSpace: 'nowrap' }}>
                  actor {act}{st.model ? ` · ${st.model}` : ''}
                </span>
                <span>轮 {st.turns}</span>
                <span>跨度 {fmtMs(st.span_s != null ? st.span_s * 1000 : null)}</span>
                <span>轮时 中位 {fmtMs(med)} · p90 {fmtMs(p90v)} · 最长 {fmtMs(maxd)}</span>
              </div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 5, fontSize: '11.5px' }}>
                <span style={{ minWidth: 86, color: '#64748b', fontFamily: 'ui-monospace,Menlo,monospace' }}>tokens {fmtTok(tok.total)}</span>
                <span style={{ flex: 1, display: 'flex', height: 10, borderRadius: 3, overflow: 'hidden', border: '1px solid #e2e8f0' }}>
                  {seg(tok.uncached, '#dc2626', 'uncached')}{seg(tok.cached, '#94a3b8', 'cache')}{seg(tok.out, '#059669', 'out')}
                </span>
                <span style={{ fontFamily: 'ui-monospace,Menlo,monospace', color: '#64748b', fontSize: '11px' }}>
                  uncached {fmtTok(tok.uncached)} · cache {fmtTok(tok.cached)} · out {fmtTok(tok.out)}(可见 {fmtTok(tok.out_visible)}/思考 {fmtTok(tok.out_thoughts)})
                </span>
              </div>
              <div style={{ marginTop: 3, fontSize: '11.5px', fontFamily: 'ui-monospace,Menlo,monospace', color: '#334155' }}>
                {c ? (c.scheme?.startsWith('A')
                  ? <>映射 A(US$): <b>{c.usd != null ? c.usd.toFixed(4) : '—'}</b>{c.peak ? ' · 峰值×2' : ''}</>
                  : <>映射 B(¥): <b>{c.cny != null ? c.cny.toFixed(3) : '—'}</b> = credits <b>{c.cr_k1 != null ? c.cr_k1.toFixed(0) : '—'}</b>(k=1) · {c.cr_k072 != null ? c.cr_k072.toFixed(0) : '—'}(k=0.72)</>)
                  : '无成本映射(模型未识别)'}
              </div>
            </div>
          )
        })}
        <div className="note" style={{ marginTop: 6, fontSize: '11px' }}>
          全族 tokens 合计 {fmtTok(grand)} · 口径与 metrics.py 同源 · {s.mapping?.version}<br />
          {s.mapping?.A};{s.mapping?.B};{s.mapping?.credits};{s.mapping?.out}
        </div>
      </div>
    </div>
  )
}
