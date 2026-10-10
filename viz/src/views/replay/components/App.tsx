// replay/components/App.tsx - 轨迹重建主页面(React+TS+Vite)。

import { useState, useEffect, useCallback, useMemo } from 'react'
import type { ReplayBundle, IndexEntry, ReplaySystem } from '../data'
import { loadIndex, loadBundle, hhmmss, ms, commitsAsc, mapSystems } from '../data'
import StripBar from './Strip'
import TurnDetail from './TurnDetail'
import GitGraph from './GitGraph'

type ExpState = { loading: true } | { loading: false; bundle: ReplayBundle }

export default function App() {
  const [idx, setIdx] = useState<IndexEntry[] | null>(null)
  const [expState, setExpState] = useState<ExpState>({ loading: true })
  const [stepNum, setStepNum] = useState(0)

  // Fetch index - auto-select latest
  useEffect(() => {
    loadIndex().then(data => {
      if (!data.length) return
      setIdx(data)
      loadBundle(data[data.length - 1].exp).then(b => setExpState({ loading: false, bundle: b })).catch(() => {})
    }).catch(() => {})
  }, [])

  const selectExp = useCallback((exp: string) => {
    loadBundle(exp).then(b => { setExpState({ loading: false, bundle: b }); setStepNum(0) }).catch(() => {})
  }, [])

  const bundle = ('bundle' in expState && !expState.loading) ? expState.bundle : null
  const turns = bundle ? bundle.sessions.turns : []
  const N = turns.length

  const jumpTo = useCallback((tsMs: number) => {
    if (!bundle) return
    const turnsList = bundle.sessions.turns
    for (let i = 0; i < turnsList.length; i++) if (ms(turnsList[i].t1 ?? turnsList[i].t0) >= tsMs) { setStepNum(i); return }
    setStepNum(turnsList.length - 1)
  }, [bundle])

  const prefixCalls = useMemo<number[]>(() => { let c = 0; return turns.map(t => { c += t.calls.length; return c }) }, [turns])
  const prefixThoughts = useMemo<number[]>(() => { let t = 0; return turns.map(x => { t += x.thoughts.join('').length; return t }) }, [turns])
  const totalThoughtChars = useMemo(() => turns.reduce((a, x) => a + x.thoughts.join('').length, 0), [turns])
  const gitCommits = useMemo(() => bundle ? commitsAsc(bundle) : [], [bundle])
  const sysMap = useMemo(() => bundle ? mapSystems(bundle) : new Map<number, ReplaySystem[]>(), [bundle])
  const endMs = bundle && turns[stepNum] ? ms(turns[stepNum].t1 ?? turns[stepNum].t0) : Number.POSITIVE_INFINITY

  const commitNum = useCallback((el: HTMLInputElement) => {
    const v = Number(el.value)
    if (Number.isFinite(v) && v >= 1 && v <= N) setStepNum(Math.round(v) - 1)
    else el.value = String(Math.max(stepNum + 1, 1))
  }, [N, stepNum])

  // Picker buttons
  const picker = idx?.map(e => (
    <button key={e.exp} onClick={() => selectExp(e.exp)}
      className={`btn${(bundle && bundle.exp === e.exp) ? ' act' : ''}`}
      title={`trial ${e.trial} · ${e.counts.turns}轮 / ${e.counts.calls}调用 / ${e.counts.commits}提交`}
    >{e.exp}</button>
  ))

  // Meta info
  const metaText = !bundle ? '' : (() => {
    const b = bundle
    const trial = idx?.find(x => x.exp === b.exp)?.trial || '—'
    return `${b.label} · trial ${trial} · 窗口 ${hhmmss(b.time_range.t0, true)}→${hhmmss(b.time_range.t1)} (UTC) · ${b.counts.turns}轮/${b.counts.calls}调用/${b.counts.thoughts}思考/${b.counts.commits}提交/${b.counts.gate}门/${b.counts.board}板/${b.counts.systems}系统事件 · 转录${b.sessions.raw_lines || '—'}行`
  })()

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '0 16px 40px' }}>
      <p className="lede">对指定实验的轨迹重建：按带时间戳的离散每步回放（数据=采集包原文，只折叠不删减）。<b>顶部滑块粒度 = 每个对话轮</b>，输入框可精确定位到第 N 轮；重建条标出 git 节点与工具用量，本步详情含可展开思考、工具卡与逐行原文。</p>

      {/* Card 1: controls + strip */}
      <div className="card">
        <h2>轨迹重建</h2>
        <div className="ctl">
          {picker}<span className="sep" />
          <div className="rp-range">
            <input type="range" min={1} max={Math.max(N, 1)} value={Math.max(stepNum + 1, 1)} step={1}
              onChange={e => setStepNum(Number(e.target.value) - 1)} className="rp-slider" aria-label="按轮定位" />
            <input key={`num-${stepNum}`} type="number" min={1} max={Math.max(N, 1)} defaultValue={Math.max(stepNum + 1, 1)} step={1}
              onBlur={e => commitNum(e.target as HTMLInputElement)}
              onKeyDown={e => { if (e.key === 'Enter') commitNum(e.target as HTMLInputElement) }} className="rp-num" aria-label="轮号" />
          </div>
          <span className="rp-readout">{metaText}</span>
        </div>

        {bundle && <StripBar turns={turns} bundles={bundle} step={stepNum} gid={jumpTo} />}

        {/* Legend */}
        <div className="leg">
          <span>珠=轮次(珠径∝工具调用数;上=A deepseek-flash · 下=B qwen3.8-flash)</span>
          <span>◆ 普通提交 · ◉ 玫红实边圆 = merge</span>
          <span>◯ 蓝实边环 + 小字 = tag</span>
          <span>│ 门事件(虚=等待 · 粗=允许)</span>
          <span>■ 板条目</span>
          <span>虚线竖线 = 当前步游标</span>
        </div>

        {/* Chips bar */}
        {bundle && (
          <div className="leg rp-chips">
            <span className="cite">截至第 {stepNum + 1} 轮末</span>
            <span className="cite">提交 {gitCommits.filter(c => ms(c.date) <= endMs).length}/{gitCommits.length}</span>
            <span className="cite">门 {bundle.ops.gate.filter(e => ms(e.ts) <= endMs).length}/{bundle.ops.gate.length}</span>
            <span className="cite">板 {bundle.ops.board.filter(e => e.createdAt && e.createdAt <= endMs).length}/{bundle.ops.board.length}</span>
            <span className="cite">调用 {prefixCalls[stepNum]}/{bundle.counts.calls}</span>
            <span className="cite">思考 {(prefixThoughts[stepNum] ?? 0).toLocaleString()}/{totalThoughtChars.toLocaleString()} 字</span>
          </div>
        )}

        <p className="note">Step = assistant response cycle (one assistant message + subsequent tool results); slider &amp; input use this granularity. Folding alters display only, not data — every step's original JSONL is verbatim transcript. Source: <code>node viz/scripts/build_replay.mjs</code>.</p>
      </div>

      {/* Split: detail left + ledgers right */}
      <div className="split rp-wide">
        <div style={{ minWidth: 0 }}>
          <div className="card"><h2>{bundle && turns[stepNum] ? `第 ${stepNum + 1} 轮 · actor ${turns[stepNum].actor} · ${hhmmss(turns[stepNum].t0)} UTC` : ''}</h2>
            {bundle && turns[stepNum] && (
              <TurnDetail turn={turns[stepNum]} nth={turns.slice(0, stepNum + 1).filter(t => t.actor === turns[stepNum].actor).length} used={turns[stepNum].usage || undefined} sysEvents={sysMap.get(stepNum) || []} />
            )}
          </div>
        </div>

        <div className="sidecol">
          {bundle && (
            <div className="card"><h2>{`git 织图 · ${bundle.git.commits.length} 提交(泳道 = 分支线)`}</h2>
              <div style={{ padding: '6px 10px 4px' }}>
                <GitGraph cards={bundle.git.commits} tags={bundle.git.tags} step={stepNum} gid={jumpTo} />
              </div>
            </div>
          )}

          {/* Protocol ledger: gate + board, time-sorted, dim-future */}
          {bundle && (() => {
            const evs = [
              ...bundle.ops.gate.map(e => ({ t: ms(e.ts), icon: '│', ts: e.ts, text: e.text, tag: '门' })),
              ...bundle.ops.board.map(e => ({ t: e.createdAt || 0, icon: '■', ts: e.createdAt ? new Date(e.createdAt).toISOString() : '', text: `${e.kind} · ${e.subject || ''} · by ${e.createdBy || '—'}`, tag: '板' })),
            ].sort((a, b) => a.t - b.t)
            let nowK = -1
            evs.forEach((e, i) => { if (e.t <= endMs) nowK = i })
            return (
              <div className="card"><h2>{`协议账 · 门 ${bundle.ops.gate.length} · 板 ${bundle.ops.board.length}`}</h2>
                <div className="rp-ledger" style={{ padding: '6px 12px 10px' }}>
                  {evs.map((e, i) => (
                    <div key={'e' + i} className={`rp-lrow${e.t <= endMs ? '' : ' dim'}${i === nowK ? ' now' : ''}`}>
                      <span className="g">{e.icon}</span>
                      <span className="sha">{hhmmss(e.ts)}</span>
                      <span className="sub">{e.text}</span>
                      <span className="t">{e.tag}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Seed prompts */}
          {bundle && bundle.sessions.userPrompts && bundle.sessions.userPrompts.length > 0 && (
            <div className="card"><h2>启动提示 (第 0 步)</h2>
              <div style={{ padding: '8px 12px' }}>
                {bundle.sessions.userPrompts.map((up, i) => (
                  <details key={'pp' + i} style={{ marginBottom: '8px' }}>
                    <summary style={{ fontSize: '11.5px', color: '#64748b', cursor: 'pointer' }}>{`actor ${up.actor} · ${hhmmss(up.ts || undefined, true)} · ${(up.parts?.reduce((a, p) => a + (p.text || '').length, 0) || 0).toLocaleString()} 字`}</summary>
                    <pre style={{ fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace', fontSize: '11.5px', lineHeight: '1.45', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '7px 9px', maxHeight: '360px', overflow: 'auto', margin: '5px 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                      {(up.parts?.map(p => p.text || '').join('\n') + '\n\n' + (up.raw ? up.raw : '(无原文)'))}
                    </pre>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
