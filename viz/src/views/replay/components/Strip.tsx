// replay/components/Strip.tsx —— 珠链时间条(重设计 v2)。
//
// 第一性原理:回放的核心是"两个 agent 在时间轴上的工作节律"。用两条珠链表达:
//   A/deepseek-flash 珠链(上)、B/qwen3.8-flash 珠链(下) —— 珠径 ∝ 工具调用数,
//   细线串珠;中脊是 git 里程碑(菱形=普通 · 玫红实边圆=merge · 蓝环=tag);
//   下沿是协议事件(门=刻度, 板=方块)。当前步游标;点珠/标记跳转。
//
// 与旧版的区别:去掉了竖条柱状(读不出节律)、去掉五泳道堆叠(拥挤),
// 改为双珠链 + 单中脊,呼吸感来自留白和圆角。

import { useMemo } from 'react'
import { scaleTime } from 'd3-scale'
import type { ReplayTurn, ReplayBundle } from '../data'
import { ms, hhmmss } from '../data'

interface Props { turns: ReplayTurn[]; bundles: ReplayBundle; step: number; gid: (ts: number) => void }

const W = 1180, H = 216
const A_Y = 48, B_Y = 100         // 珠链基线的 y
const GIT_Y = 132                   // git 中脊
const GATE_Y = 156, BOARD_Y = 172  // 协议事件刻度的 y
const AXIS_Y = 192                  // 时间轴

const laneColor = (actor: string) => actor === 'a' ? '#1d4ed8' : '#166534'
const laneName = (actor: string) => actor === 'a' ? 'A · deepseek-flash' : 'B · qwen3.8-flash'

export default function StripBar({ turns, bundles, step, gid }: Props) {
  const N = turns.length

  const x = useMemo(() => {
    const t0 = bundles.time_range.t0 ? ms(bundles.time_range.t0) : 0
    const t1 = bundles.time_range.t1 ? ms(bundles.time_range.t1) : t0 + 1
    return scaleTime().domain([new Date(t0), new Date(t1)]).range([56, W - 24]).clamp(true)
  }, [bundles])

  const ticks = useMemo(() => x.ticks(6), [x])

  const beads = useMemo(() => turns.map((t, i) => ({
    i,
    actor: t.actor,
    xp: Number.isFinite(ms(t.t0)) ? x(new Date(ms(t.t0))) : 56,
    endTs: ms(t.t1 ?? t.t0),
    calls: t.calls.length,
    t0raw: t.t0,
    thoughts: t.thoughts.join('').length,
  })), [turns, x])

  if (!N) return null

  const curEnd = ms(turns[step]?.t1 ?? turns[step]?.t0)
  const curX = x(new Date(curEnd))

  // 珠链折线:同一 actor 的珠按时间串起,lit=已发生段(os=已过当前步的部分)
  const threads = useMemo(() => {
    const build = (actor: string) => {
      const all = beads.filter(b => b.actor === actor)
      const lit = all.filter(b => b.endTs <= curEnd)
      return {
        allPts: all.map(b => `${b.xp.toFixed(1)},${(actor === 'a' ? A_Y : B_Y)}`).join(' '),
        litPts: lit.length >= 1 ? lit.map(b => `${b.xp.toFixed(1)},${(actor === 'a' ? A_Y : B_Y)}`).join(' ') : '',
        color: laneColor(actor),
      }
    }
    return { a: build('a'), b: build('b') }
  }, [beads, curEnd])

  const fmtTick = (d: Date) => hhmmss(d.toISOString())

  return (
    <div className="rp-stripwrap">
      <svg className="chart rp-strip" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="轨迹重建珠链时间条">
        {/* 两条 actor 泳道的底纹(呼吸感) */}
        <rect className="rp-band a" x={40} y={28} width={W - 64} height={42} rx={10} />
        <rect className="rp-band b" x={40} y={80} width={W - 64} height={42} rx={10} />

        {/* 纵向网格 */}
        {ticks.map((v, i) => (
          <line key={'g' + i} className="rp-grid" x1={x(v)} y1={20} x2={x(v)} y2={AXIS_Y} />
        ))}

        {/* 泳道标签(泳道带内左上角) */}
        <text className="rp-lanelbl a" x={48} y={A_Y - 13} >{laneName('a')}</text>
        <text className="rp-lanelbl b" x={48} y={B_Y - 13}>{laneName('b')}</text>

        {/* 珠链:底色线 + 已发生的亮线 */}
        {(['a', 'b'] as const).map(actor => (
          <g key={actor}>
            {threads[actor].allPts && <polyline className="rp-thread" points={threads[actor].allPts} stroke={threads[actor].color} />}
            {threads[actor].litPts && <polyline className="rp-thread lit" points={threads[actor].litPts} stroke={threads[actor].color} />}
          </g>
        ))}

        {/* 珠子 */}
        {beads.map(b => {
          const r = 3.4 + Math.min(b.calls, 8) * 0.7
          const lit = b.endTs <= curEnd
          const cur = b.i === step
          const y = b.actor === 'a' ? A_Y : B_Y
          return (
            <g key={b.i} className={`rp-bead${lit ? ' lit' : ''}${cur ? ' cur' : ''} ${b.actor}`} onClick={() => gid(ms(b.t0raw))} style={{ cursor: 'pointer' }}>
              <title>{`第 ${b.i + 1} 轮 · ${b.actor} · ${hhmmss(b.t0raw, true)} · ${b.calls} 次工具 · ${b.thoughts.toLocaleString()} 思考字符`}</title>
              {cur && <circle className="halo" cx={b.xp} cy={y} r={r + 5} />}
              <circle className="dot" cx={b.xp} cy={y} r={r} />
            </g>
          )
        })}

        {/* git 中脊 */}
        <line className="rp-spine" x1={56} x2={W - 24} y1={GIT_Y} y2={GIT_Y} />
        {bundles.git.commits.map(c => {
          const xx = x(new Date(ms(c.date)))
          const merge = c.parents.length > 1
          const tag = bundles.git.tags.find(t => t.sha === c.sha)
          const lit = ms(c.date) <= curEnd
          return (
            <g key={c.sha} className={`rp-milestone${lit ? '' : ' future'}`} transform={`translate(${xx},${GIT_Y})`} style={{ cursor: 'pointer' }} onClick={() => gid(ms(c.date))}>
              <title>{`${c.sha.slice(0, 7)} ${c.subject}\n${hhmmss(c.date, true)} · 分支 ${c.branches.join('/') || '\u2014'}${tag ? ' · tag ' + tag.name : ''}`}</title>
              {merge
                ? <circle className="ms-merge" cx={0} cy={0} r={4.6} />
                : <path className="ms-commit" d="M0,-4.4L4.4,0L0,4.4L-4.4,0Z" />}
              {tag && <>
                <circle className="ms-tagring" cx={0} cy={0} r={8.4} />
                <text className="ms-taglabel" x={0} y={-12.5} textAnchor="middle">{tag.name.replace(/^ckpt-/, '')}</text>
              </>}
              <rect x={-7} y={-9} width={14} height={18} style={{ fill: 'transparent' }} />
            </g>
          )
        })}

        {/* 协议事件:门 */}
        {bundles.ops.gate.map((e, i) => {
          const kind = e.text.startsWith('wait-start') ? 'wait' : e.text.startsWith('allow-after-wait') ? 'allow' : 'fast'
          const lit = ms(e.ts) <= curEnd
          return (
            <g key={'gate' + i} className={`rp-op ${kind}${lit ? '' : ' future'}`} transform={`translate(${x(new Date(ms(e.ts)))},0)`} style={{ cursor: 'pointer' }} onClick={() => gid(ms(e.ts))}>
              <title>{`门 · ${hhmmss(e.ts, true)} · ${e.text}`}</title>
              <line className="op-tick" x1={0} y1={GATE_Y - 7} x2={0} y2={GATE_Y + 7} />
              <rect x={-4} y={GATE_Y - 8} width={8} height={16} style={{ fill: 'transparent' }} />
            </g>
          )
        })}

        {/* 协议事件:板 */}
        {bundles.ops.board.map((e, i) => {
          const tsv = e.createdAt ? e.createdAt : 0
          const lit = tsv <= curEnd
          return (
            <g key={'board' + i} className={`rp-op board${lit ? '' : ' future'}`} transform={`translate(${x(new Date(tsv))},0)`} style={{ cursor: 'pointer' }} onClick={() => gid(tsv)}>
              <title>{`板 · ${e.kind} · ${e.subject ?? ''} · by ${e.createdBy ?? '?'}`}</title>
              <rect className="op-square" x={-3.5} y={BOARD_Y - 3.5} width={7} height={7} rx={1.5} />
              <rect x={-5} y={BOARD_Y - 6} width={10} height={12} style={{ fill: 'transparent' }} />
            </g>
          )
        })}

        {/* 时间轴 */}
        <line className="rp-axis" x1={56} x2={W - 24} y1={AXIS_Y} y2={AXIS_Y} />
        {ticks.map((v, i) => (
          <g key={'t' + i}>
            <line className="rp-axis-tick" x1={x(v)} x2={x(v)} y1={AXIS_Y} y2={AXIS_Y + 4} />
            <text className="rp-axis-label" x={x(v)} y={AXIS_Y + 15} textAnchor="middle">{fmtTick(v)}</text>
          </g>
        ))}

        {/* 当前步游标 + 胶囊标签(顶部独享一行,不与泳道标签碰撞) */}
        <line className="rp-cur" x1={curX} x2={curX} y1={16} y2={AXIS_Y} />
        <g transform={`translate(${Math.min(Math.max(curX, 70), W - 70)},10)`}>
          <rect className="rp-curchip" x={-26} y={-10} width={52} height={15} rx={7.5} />
          <text className="rp-curtext" x={0} y={1.5} textAnchor="middle">{`第 ${step + 1} 轮`}</text>
        </g>
      </svg>
    </div>
  )
}
