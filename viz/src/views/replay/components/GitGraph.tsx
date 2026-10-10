// replay/components/GitGraph.tsx —— git 织图:git log --graph 的 SVG 版。
// 轨道列 = 分支线(灰=main · 蓝=a · 绿=b);分叉/汇合 = 曲线;refs = 徽章(分支/tag 所在);
// 全部提交任何步都在场,未发生的降透明、随步点亮;点任意行跳至该提交落入的轮。

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

interface Col { await: string | null; color: string; y0: number; dead: boolean }
interface RailSeg { x: number; y0: number; y1: number; color: string }
interface CurveSeg { kind: 'split' | 'fuse'; a: number; b: number; y: number; color: string }
interface GNode { row: number; col: number; color: string }

export default function GitGraph({ cards, endMs, gid }: Props) {
  const N = cards.length

  const graph = useMemo(() => {
    const y = (i: number) => PADT + i * ROW + ROW / 2
    const x = (k: number) => PADL + k * LW + LW / 2
    const cols: (Col | null)[] = []
    const rails: RailSeg[] = []
    const curves: CurveSeg[] = []
    const nodes: GNode[] = []
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
    // 最左空闲列;复用一条已终结(await=null)的旧生命时,先把它的轨道补收尾
    const findFree = (atRow: number) => {
      for (let i = 0; i < cols.length; i++) {
        const c = cols[i]
        if (!c || c.dead) return i
        if (!c.await) {
          rails.push({ x: i, y0: c.y0, y1: y(atRow) - ROW * 0.3, color: c.color })
          return i
        }
      }
      cols.push(null)
      return cols.length - 1
    }

    for (let k = 0; k < N; k++) {
      const c = cards[k]
      let nodeCol = -1
      for (let i = 0; i < cols.length; i++) {
        const cc = cols[i]
        if (cc && !cc.dead && cc.await === c.sha) { nodeCol = i; break }
      }
      if (nodeCol < 0) {
        const f = findFree(k)
        cols[f] = { await: c.sha, color: k === 0 ? MAIN : spawnColor(c, true), y0: y(k), dead: false }
        nodeCol = f
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
          const f = findFree(k)
          cols[f] = { await: p, color: spawnColor(c, false), y0: y(k + 1), dead: false }
          t = f
        }
        curves.push({ kind: 'split', a: nodeCol, b: t, y: y(k), color: (cols[t] as Col).color })
      }
      // 两列同时等待同一提交 → 右列在该行之下并入左列
      let fused = true
      while (fused) {
        fused = false
        outer: for (let i = 0; i < cols.length; i++) {
          const ci = cols[i]
          if (!ci || ci.dead || !ci.await) continue
          for (let j = i + 1; j < cols.length; j++) {
            const cj = cols[j]
            if (!cj || cj.dead || cj.await !== ci.await) continue
            rails.push({ x: j, y0: cj.y0, y1: y(k) + ROW * 0.5, color: cj.color })
            curves.push({ kind: 'fuse', a: j, b: i, y: y(k), color: cj.color })
            cj.dead = true
            cj.await = null
            fused = true
            break outer
          }
        }
      }
    }
    for (let i = 0; i < cols.length; i++) {
      const c = cols[i]
      if (c && !c.dead) rails.push({ x: i, y0: c.y0, y1: y(N - 1), color: c.color })
    }
    const maxCols = nodes.length ? Math.max(...nodes.map(n => n.col)) + 1 : 1
    return { y, x, rails, curves, nodes, maxCols, H: PADT + N * ROW + PADB, labelX: PADL + maxCols * LW + 10 }
  }, [cards])

  if (!N) return null
  const { y, x } = graph

  const curvePath = (cv: CurveSeg): string => {
    const xa = x(cv.a), xb = x(cv.b)
    if (cv.kind === 'split') {
      return 'M ' + xa + ' ' + cv.y + ' C ' + xa + ' ' + (cv.y + ROW * 0.45) + ' ' + xb + ' ' + (cv.y + ROW * 0.55) + ' ' + xb + ' ' + (cv.y + ROW)
    }
    const y0 = cv.y + 8
    return 'M ' + xa + ' ' + y0 + ' C ' + xa + ' ' + (y0 + 9) + ' ' + xb + ' ' + (y0 + 3) + ' ' + xb + ' ' + (y0 + 12)
  }

  const chipCharW = 5.8, chipH = 12, chipFont = 9.5

  return (
    <div className="rp-gitwrap">
      <svg className="chart rp-git" viewBox={'0 0 ' + W + ' ' + graph.H} role="img" aria-label="git 织图">
        {/* 轨道 */}
        {graph.rails.map((r, i) => (
          <line key={'rl' + i} x1={x(r.x)} y1={r.y0} x2={x(r.x)} y2={r.y1} stroke={r.color} strokeWidth={1.6} strokeLinecap="round" opacity={0.45} />
        ))}
        {/* 分叉 / 汇合 */}
        {graph.curves.map((cv, i) => (
          <path key={'cv' + i} d={curvePath(cv)} fill="none" stroke={cv.color} strokeWidth={1.6} strokeLinecap="round" opacity={0.45} />
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
      <p className="note">轨道列 = 分支线(灰=main · 蓝=a · 绿=b),分叉/汇合为曲线;徽章 = 分支/tag 所在提交;<b>◉</b> 玫红实边圆 = merge · <b>◯</b> 蓝环+名字 = tag;全部提交任何步都在场,未发生的降透明、随步点亮。点任意行跳至该提交落入的轮。</p>
    </div>
  )
}
