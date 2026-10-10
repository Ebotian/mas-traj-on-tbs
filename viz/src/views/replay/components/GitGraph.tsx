// replay/components/GitGraph.tsx —— git 织图:git log --graph 的 SVG 版。
// 每列 = 一条连续路径(git 的 | 轨道);分叉 / 汇合是半 S 曲线,接头一律落在节点图形下方,
// 因此全图无断口、无毛刺。全部提交任何步都在场,未发生的降透明、随步点亮;
// refs = 徽章;点任意行跳至该提交落入的轮。

import { useMemo } from 'react'
import type { ReplayCommit } from '../data'
import { hhmmss, ms, sha7 } from '../data'

interface Props { cards: ReplayCommit[]; endMs: number; gid: (ts: number) => void }

const MAIN = '#475569', ACOL = '#1d4ed8', BCOL = '#166534'
const ROSE = '#be123c'
const CYCLE = ['#b45309', '#7c3aed', '#0f766e', '#9d174d']
const ROW = 24, PADT = 18, PADB = 10, PADL = 10, LW = 16, W = 448

function normRefs(refs?: string): string[] {
  if (!refs) return []
  const out: string[] = []
  for (let r of refs.split(',').map(s => s.trim()).filter(Boolean)) {
    if (r.startsWith('HEAD -> ')) r = r.slice(8)
    if (r === 'origin/HEAD' || r === 'HEAD') continue
    if (r.startsWith('origin/')) r = r.slice(7)
    if (!out.includes(r)) out.push(r)
  }
  return out
}

// 一条列生命 = 一段直线轨道,端点带半 S 进出曲线
interface Life {
  color: string
  start: { type: 'head' | 'split' | 'jog'; r: number; fromCol: number }
  y1: number
  end: null | { type: 'join' | 'jog'; r: number; toCol: number }
}
interface Col { await: string | null; color: string; dead: boolean; lives: Life[] }
interface GNode { row: number; col: number; color: string }

export default function GitGraph({ cards, endMs, gid }: Props) {
  const N = cards.length

  const graph = useMemo(() => {
    const y = (i: number) => PADT + i * ROW + ROW / 2
    const x = (k: number) => PADL + k * LW + LW / 2
    const cols: (Col | null)[] = []
    const nodes: GNode[] = []
    // 联到既有轨道上的分叉(如把旧线并入既有列)单独画一条半 S
    const connectors: { a: number; b: number; r: number; color: string }[] = []
    const pickColor = () => {
      const used = new Set((cols.filter(c => c && !c.dead) as Col[]).map(c => c.color))
      return CYCLE.find(c => !used.has(c)) || CYCLE[0]
    }
    const spawnColor = (c: ReplayCommit, isHead: boolean) => {
      if (isHead) {
        const rs = normRefs(c.refs)
        if (rs.includes('b')) return BCOL
        if (rs.includes('a')) return ACOL
        return pickColor()
      }
      const m = (c.subject || '').match(/merge\s+([ab])\b/)
      if (m) return m[1] === 'a' ? ACOL : BCOL
      return pickColor()
    }
    const findFree = (atRow: number) => {
      for (let i = 0; i < cols.length; i++) {
        const c = cols[i]
        if (!c || c.dead) return i
        if (!c.await) {
          const l = c.lives[c.lives.length - 1]
          l.y1 = y(atRow) - 7
          return i
        }
      }
      cols.push(null)
      return cols.length - 1
    }

    for (let k = 0; k < N; k++) {
      const c = cards[k]
      const inCols: number[] = []
      for (let i = 0; i < cols.length; i++) {
        const cc = cols[i]
        if (cc && !cc.dead && cc.await === c.sha) inCols.push(i)
      }
      let nodeCol: number
      if (inCols.length) {
        nodeCol = inCols[0]
        for (const j of inCols.slice(1)) {
          const cj = cols[j] as Col
          const l = cj.lives[cj.lives.length - 1]
          l.end = { type: 'join', r: k, toCol: nodeCol }
          l.y1 = y(k) - 6
          cj.dead = true
          cj.await = null
        }
      } else {
        nodeCol = findFree(k)
        const color = k === 0 ? MAIN : spawnColor(c, true)
        const prev = cols[nodeCol]
        cols[nodeCol] = {
          await: c.sha, color, dead: false,
          lives: [...(prev ? prev.lives : []), { color, start: { type: 'head', r: k, fromCol: nodeCol }, y1: y(N - 1), end: null }],
        }
      }
      const col = cols[nodeCol] as Col
      nodes.push({ row: k, col: nodeCol, color: col.color })
      const ps = c.parents || []
      col.await = ps.length ? ps[0] : null
      for (let pi = 1; pi < ps.length; pi++) {
        const p = ps[pi]
        let t = -1
        for (let i = 0; i < cols.length; i++) {
          const cc = cols[i]
          if (cc && !cc.dead && cc.await === p) { t = i; break }
        }
        if (t < 0) {
          t = findFree(k)
          const prev = cols[t]
          const priorLife = prev && prev.lives.length ? prev.lives[prev.lives.length - 1] : null
          const isJog = !!(priorLife && priorLife.end && priorLife.end.r === k && priorLife.end.type === 'join')
          if (isJog && priorLife && priorLife.end) priorLife.end.type = 'jog'
          const color = spawnColor(c, false)
          cols[t] = {
            await: p, color, dead: false,
            lives: [...(prev ? prev.lives : []), { color, start: { type: isJog ? 'jog' : 'split', r: k, fromCol: nodeCol }, y1: y(N - 1), end: null }],
          }
        } else {
          connectors.push({ a: nodeCol, b: t, r: k, color: (cols[t] as Col).color })
        }
      }
    }
    for (const cc of cols) {
      if (!cc || cc.dead) continue
      cc.lives[cc.lives.length - 1].y1 = y(N - 1)
    }

    const maxCols = nodes.length ? Math.max(...nodes.map(n => n.col)) + 1 : 1
    return { y, x, cols, nodes, connectors, maxCols, H: PADT + N * ROW + PADB, labelX: PADL + maxCols * LW + 10 }
  }, [cards])

  if (!N) return null
  const { y, x } = graph

  // 一条列生命 → 单条连续 path:半 S 进 → 直线 → 半 S 出
  const lifePath = (k: number, l: Life): string => {
    const xs = x(k)
    const parts: string[] = []
    if (l.start.type === 'head') parts.push('M ' + xs + ' ' + y(l.start.r))
    else {
      const xn = x(l.start.fromCol), yk = y(l.start.r)
      parts.push('M ' + xn + ' ' + yk + ' C ' + xn + ' ' + (yk + 8) + ' ' + xs + ' ' + (yk + 16) + ' ' + xs + ' ' + (yk + 24))
    }
    parts.push('L ' + xs + ' ' + l.y1)
    if (l.end) {
      const xn = x(l.end.toCol), yk = y(l.end.r)
      parts.push('C ' + xs + ' ' + (yk + 7) + ' ' + xn + ' ' + (yk + 7) + ' ' + xn + ' ' + yk)
    }
    return parts.join(' ')
  }
  const connPath = (cn: { a: number; b: number; r: number }): string => {
    const xa = x(cn.a), xb = x(cn.b), yk = y(cn.r)
    return 'M ' + xa + ' ' + yk + ' C ' + xa + ' ' + (yk + 8) + ' ' + xb + ' ' + (yk + 16) + ' ' + xb + ' ' + (yk + 24)
  }

  const chipCharW = 5.8, chipH = 12, chipFont = 9.5
  const curve = { fill: 'none', strokeWidth: 1.6, strokeLinecap: 'round', opacity: 0.45 } as const

  return (
    <div className="rp-gitwrap">
      <svg className="chart rp-git" viewBox={'0 0 ' + W + ' ' + graph.H} role="img" aria-label="git 织图">
        {/* 轨道(每列生命一条连续路径) */}
        {graph.cols.map((cc, i) => !cc ? null : cc.lives.map((l, li) => (
          <path key={'l' + i + '-' + li} d={lifePath(i, l)} stroke={l.color} {...curve} />
        )))}
        {/* 并入既有轨道的分叉 */}
        {graph.connectors.map((cn, i) => (
          <path key={'cn' + i} d={connPath(cn)} stroke={cn.color} {...curve} />
        ))}

        {/* 节点 + 行(标签、徽章、时间) */}
        {cards.map((c, k) => {
          const n = graph.nodes[k]
          const yn = y(k), xc = x(n.col)
          const lit = ms(c.date) <= endMs
          const isMerge = (c.parents || []).length > 1
          const refs = normRefs(c.refs)
          const tagRef = refs.find(r => r.startsWith('tag:'))
          let cx = graph.labelX + 50
          const chips = refs.map(r => {
            if (r.startsWith('tag:')) return { label: r.slice(4).trim(), tag: true, color: ACOL }
            return { label: r, tag: false, color: r === 'a' ? ACOL : r === 'b' ? BCOL : MAIN }
          })
          const chipEls = chips.map((ch, ci) => {
            const w = Math.max(18, ch.label.length * chipCharW + 9)
            const el = (
              <g key={'ch' + ci} transform={'translate(' + cx + ' ' + (yn - chipH / 2) + ')'}>
                <rect width={w} height={chipH} rx={3.5} fill={ch.tag ? '#eff6ff' : '#f1f5f9'} stroke={ch.tag ? ACOL : '#cbd5e1'} strokeWidth={0.8} />
                <text x={w / 2} y={chipH / 2 + 3.2} textAnchor="middle" fontSize={chipFont} fill={ch.tag ? ACOL : ch.color} fontWeight={600}>{ch.label}</text>
              </g>
            )
            cx += w + 4
            return el
          })
          const subX = cx + 4
          const tip = c.sha + '\n' + c.subject + '\n' + hhmmss(c.date, true) + ' · 分支 ' + ((c.branches || []).join('/') || '—')
          return (
            <g key={'row' + k}>
              <g style={{ opacity: lit ? 1 : 0.4 }}>
                {isMerge
                  ? <circle cx={xc} cy={yn} r={4.2} fill="#fff" stroke={ROSE} strokeWidth={2} />
                  : <circle cx={xc} cy={yn} r={3.4} fill={n.color} />}
                {tagRef && <circle cx={xc} cy={yn} r={6.6} fill="none" stroke={ACOL} strokeWidth={1.6} />}
                <text x={graph.labelX} y={yn + 3.5} className="rp-gsha">{sha7(c.sha)}</text>
                {chipEls}
                <text x={subX} y={yn + 3.5} className="rp-gsub">{c.subject}</text>
                <text x={W - 8} y={yn + 3.5} className="rp-gtime" textAnchor="end">{hhmmss(c.date)}</text>
              </g>
              <rect x={0} y={yn - ROW / 2} width={W} height={ROW} className="hit" onClick={() => gid(ms(c.date))}>
                <title>{tip}</title>
              </rect>
            </g>
          )
        })}
      </svg>
      <p className="note">轨道列 = 分支线(灰=main · 蓝=a · 绿=b),每列一条连续路径,分叉/汇合为半 S 曲线、接头落在节点下;徽章 = 分支/tag 所在提交;<b>◉</b> 玫红实边圆 = merge · <b>◯</b> 蓝环+名字 = tag;全部提交任何步都在场,未发生的降透明、随步点亮。点任意行跳至该提交落入的轮。</p>
    </div>
  )
}
