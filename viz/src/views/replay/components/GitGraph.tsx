// replay/components/GitGraph.tsx —— git 织图(泳道算法,git-log --graph 形态)。
// 经典 lane 分配(新→旧一遍) + 折线绘图。节点编码与条带一致。

import { useMemo } from 'react'
import type { ReplayCommit } from '../data'
import { hhmmss, ms, sha7 } from '../data'

interface Props { cards: ReplayCommit[]; tags: {name:string;sha:string}[]; step: number; gid: (ts:number) => void }

export default function GitGraph({cards, tags, step, gid}: Props) {
  const N = cards.length
  if (!N) return null
  // step=N means all lit. Compute end timestamp = latest commit's date at or before this step.
  // Since cards are newest-first: the most recent lit commit is the one with smallest index whose ts <= step-end.
  // For simplicity: when step >= N-1 (last), all are lit. Otherwise use step-th from end.
  const endMs = step >= N ? Infinity : ms(cards[N - 1 - step]?.date ?? '')

  // ---- lane allocation + edge rendering data (memoized)
  const graph = useMemo(() => {
    const lanes: (string|null)[] = [null]
    const laneColors: string[] = ['#475569'] // lane 0 = main
    const CYCLE = ['#b45309','#be123c','#64748b']
    let cycleI = 0
    const ROW = 24, PADL = 8, PADT = 16, PADB = 6, LW = 13
    const W = 448
    
    const grows: {c:ReplayCommit;lane:number;edges:{lane:number;parent:string}[]}[] = []

    for (let r = 0; r < N; r++) {
      const c = cards[r]
      let i = lanes.indexOf(c.sha)
      if (i < 0) {
        let k = lanes.indexOf(null); if (k < 0) { lanes.push(null); laneColors.push('#475569'); k = lanes.length-1 }
        i = k
      }
      // Close lanes expecting same sha
      for (let k = 0; k < lanes.length; k++) if (k !== i && lanes[k]===c.sha) lanes[k] = null
      
      const edges: {lane:number;parent:string}[] = []
      const ps = c.parents
      if (ps[0]) { lanes[i] = ps[0]; edges.push({lane:i,parent:ps[0]}) } else lanes[i] = null
      for (let pi = 1; pi < ps.length; pi++) {
        const p = ps[pi]; let k = lanes.indexOf(p)
        if (k < 0 || k === i) {
          k = lanes.indexOf(null); if (k < 0) { lanes.push(null); laneColors.push('#475569'); k = lanes.length-1 }
          const m = c.subject.match(/\bmerge\s+([ab])\b/)
          laneColors[k] = m ? (m[1]==='a'?'#1d4ed8':'#166534') : CYCLE[cycleI++%CYCLE.length]
          lanes[k] = p
        }
        edges.push({lane:k,parent:p})
      }
      grows.push({c,lane:i,edges})
    }

    const lanesLen = lanes.length
    const laneOf = new Map<string,number>()
    for (const g of grows) laneOf.set(g.c.sha, g.lane)
    
    const edgePath = (xc:number,yc:number,xe:number,yp:number,xp:number): string => {
      const dx = yc-yp
      if (xe===xp && dx <= ROW*1.5) return `M${xc},${yc} L${xp},${yp}`
      if (dx <= ROW*1.5) { const my=(yc+yp)/2; return `M${xc},${yc} C${xc},${my} ${xp},${my} ${xp},${yp}`}
      const y1=yc-ROW*0.8, y2=yp+ROW*0.8
      let d=`M${xc},${yc}`
      if(xe!==xc) d+=` C${xc},${yc-ROW*0.3} ${xe},${y1+ROW*0.3} ${xe},${y1}`
      else d+=` L${xe},${y1}`
      d+=` L${xe},${y2}`
      if(xe!==xp) d+=` C${xe},${y2+ROW*0.3} ${xp},${yp+ROW*0.3} ${xp},${yp}`
      else d+=` L${xp},${yp}`
      return d
    }

    const xPos = (k:number) => PADL + k*LW + LW/2
    return {grows, laneOf, laneColors, lanesLen, LW, PADL, W, H:PADT+N*ROW+PADB, ROW, PADT, xPos, edgePath, N}
  }, [cards])

  return (
    <div style={{margin:'0 0 4px'}}>
      <svg className="chart rp-git" viewBox={`0 0 ${graph.W} ${graph.H}`} role="img" aria-label="git 织图(泳道)">
        {/* Edges layer */}
        {graph.grows.map((g, ri) => {
          const yc = graph.PADT + ri * graph.ROW + graph.ROW/2
          for (const e of g.edges) {
            const parentIdx = graph.grows.findIndex(x => x.c.sha === e.parent)
            if (parentIdx < 0) continue
            const yp = graph.PADT + parentIdx * graph.ROW + graph.ROW/2
            const el = graph.xPos(e.lane)
            const pl = graph.laneOf.get(e.parent) ?? graph.xPos(g.lane)
            const pColor = graph.laneColors[e.lane] || '#475569'
            return <path key={'e'+ri+'-'+e.parent} d={graph.edgePath(graph.xPos(g.lane),yc,el,yp,pl)} fill="none" stroke={pColor} strokeWidth={1.6} strokeLinecap="round" style={{opacity:ms(g.c.date)<=endMs?1:0.2}} />
          }
          return null
        })}

        {/* Nodes + labels */}
        {graph.grows.map((g, ri) => {
          const yn = graph.PADT + ri * graph.ROW + graph.ROW/2
          const xc = graph.xPos(g.lane)
          const merge = g.c.parents.length > 1
          const tag = tags.find(t=>t.sha===g.c.sha)
          const lit = ms(g.c.date) <= endMs
          
          return (
            <g key={'n'+g.c.sha} style={{cursor:'pointer'}} onClick={()=>gid(ms(g.c.date))}>
              <title>{`${g.c.sha}\n${g.c.subject}\n${hhmmss(g.c.date,true)} · 分支 ${g.c.branches.join('/')||'\u2014'}${tag?` · tag ${tag.name}`:''}`}</title>
              {lit && <>
                {merge
                  ? <circle cx={xc} cy={yn} r={4.2} fill="#fff" stroke="#be123c" strokeWidth={2} />
                  : <circle cx={xc} cy={yn} r={3.2} fill="#475569" />}
                {tag && <circle cx={xc} cy={yn} r={7} fill="none" stroke="#1d4ed8" strokeWidth={1.6} />}
              </>}
              <text x={graph.PADL + graph.lanesLen * graph.LW + 8} y={yn+3.5} className="rp-glabel">{sha7(g.c.sha)}{String.fromCharCode(0xA0)}{g.c.subject}{tag?<tspan fill="#1d4ed8" fontWeight={600}>{` ${tag.name}`}</tspan>:''}</text>
              <text x={graph.W-8} y={yn+3.5} className="rp-gtime" textAnchor="end">{hhmmss(g.c.date)}</text>
              <rect x={0} y={yn-graph.ROW/2} width={graph.W} height={graph.ROW} style={{fill:'transparent',cursor:'pointer'}} onClick={()=>gid(ms(g.c.date))} />
            </g>
          )
        })}
      </svg>
      <p className="note">泳道色：主线(灰)=main;a 线(蓝)/b 线(绿)由 merge 提交的 `merge a/b` 副父线判定；其余按分配序。<b>◯</b>玫红实边圆=merge · <b>◯</b>蓝环=tag；点任意行跳至该提交落入的轮。</p>
    </div>
  )
}
