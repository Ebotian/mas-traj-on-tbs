// replay/index.ts —— 轨迹重建主页面。
//
// 顶部:实验选择 + 滑块(粒度 = 一个对话轮)+ 轮号输入框 → 精确到任一步。
// 条带(tracks,时间比例):轮 / 提交 / 门 / 板,点任意标记跳转。主轴:本步详情(detail)。
// 侧列:git 账(全部提交,截至本步)、协议账(门 + 板)、启动提示——折叠式,不删减。
//
// 数据在运行时从 public/replay/ fetch(生成器 viz/scripts/build_replay.mjs);
// 因此 `npm run probe` 只断言外壳文案(同 numbers 先例:探针不覆盖数据加载路径)。

import { h, panel, note, cite } from '../../lib/dom.ts'
import type { ReplayBundle, ReplayIndexEntry, ReplaySystem } from './data.ts'
import { commitsByDate, dur, hhmmss, loadBundle, loadIndex, mapSystems, ms, sha7 } from './data.ts'
import { buildStrip, type StripHandle } from './tracks.ts'
import { details, pre, renderDetail } from './detail.ts'

const LAST: { exp: string | null; step: number } = { exp: null, step: 0 }
let GEN = 0

interface Session {
  b: ReplayBundle
  strip: StripHandle
  sysMap: Map<number, ReplaySystem[]>
  commitsAsc: ReplayBundle['git']['commits']
  callsPre: number[]
  thoughtsPre: number[]
  rows: { el: HTMLElement; ts: number }[]
}

export function render(host: HTMLElement): void {
  const gen = ++GEN

  const status = h('span', { class: 'rp-readout' }, '正在加载实验索引…')
  const pickHost = h('span', { class: 'rp-pick' })
  const slider = h('input', {
    type: 'range', min: 1, max: 1, value: 1, step: 1, class: 'rp-slider', 'aria-label': '按轮定位',
    oninput: (ev: Event) => setStep(Number((ev.target as HTMLInputElement).value) - 1),
  })
  const num = h('input', {
    type: 'number', min: 1, max: 1, value: 1, step: 1, class: 'rp-num', 'aria-label': '轮号',
    onchange: (ev: Event) => { const v = Number((ev.target as HTMLInputElement).value); if (Number.isFinite(v)) setStep(v - 1) },
  })
  const readout = h('span', { class: 'rp-readout' })
  const stripHost = h('div', { class: 'rp-stripwrap' })
  const chips = h('div', { class: 'leg rp-chips' })
  const meta = h('div', { class: 'leg' })
  const legend = h('div', { class: 'leg' },
    h('span', {}, '轮 = 竖条(高 ∝ 工具调用数;上泳道 a · 下泳道 b)'),
    h('span', {}, '◆ 普通提交 · ◯ 玫红实边圆 = merge'),
    h('span', {}, '◯ 蓝实边环 + 小字 = tag'),
    h('span', {}, '│ 门事件(虚 = wait-start · 粗 = allow-after-wait)'),
    h('span', {}, '■ 板条目'),
    h('span', {}, '虚线竖线 = 当前步游标'),
    h('span', {}, '点任意标记跳至该标记落入的轮'))
  const noteLossless = note(
    '步 = 助手应答周期(一条 assistant 消息 + 其后的工具结果);滑块与输入框均按此粒度。折叠只改显示,不改数据——',
    '每步的「原始 JSONL(assistant 行)」即转录原文,工具结果、系统事件各带自己的原始行;gate、board、state 原样入档。',
    '分支尖标按最终可达集重建(轮内短命分支已删,其提交只经 main 可见)。生成器:', cite('node viz/scripts/build_replay.mjs <job-dir> --exp <id>'))
  const ctl = h('div', { class: 'ctl' },
    h('span', { class: 'rp-readout' }, '实验:'), pickHost,
    h('span', { class: 'sep' }),
    h('div', { class: 'rp-range' }, slider, num),
    readout, status)
  const card = panel('轨迹重建', ctl, stripHost, legend, chips, meta, noteLossless)
  const split = h('div', { class: 'split' })

  host.appendChild(h('p', { class: 'lede' },
    '对指定实验的轨迹重建:按带时间戳的离散每步回放(数据 = 采集包原文,只折叠不删减)。',
    h('b', {}, '顶部滑块粒度 = 每个对话轮'), ',输入框可精确定位到第 N 轮;重建条带标出 git 节点与工具用量,本步详情含可展开思考、工具卡与逐行原文。'))
  host.appendChild(card)
  host.appendChild(split)

  let S: Session | null = null
  const pick = new Map<string, HTMLButtonElement>()

  function setStep(k: number): void {
    if (!S) return
    const N = S.b.sessions.turns.length
    if (N === 0) return
    k = Math.max(0, Math.min(N - 1, Math.round(k)))
    LAST.step = k
    const t = S.b.sessions.turns[k]
    slider.value = String(k + 1)
    num.value = String(k + 1)
    readout.replaceChildren(h('b', {}, `第 ${k + 1} 轮`), ` / ${N} · actor ${t.actor} · `,
      h('span', { class: 'rp-now' }, `${hhmmss(t.t0, true)} UTC · ${dur(t.t0, t.t1)} · ${t.calls.length} 调用`))
    S.strip.setCurrent(k)

    const end = ms(t.t1 ?? t.t0)
    let lastLit = -1
    S.rows.forEach((r, i) => {
      const lit = r.ts <= end
      r.el.classList.toggle('dim', !lit)
      if (lit) lastLit = i
    })
    S.rows.forEach((r, i) => r.el.classList.toggle('now', i === lastLit))

    const spans: HTMLElement[] = []
    spans.push(h('span', { class: 'cite' }, `截至第 ${k + 1} 轮末`))
    const litCommits = S.commitsAsc.filter(c => ms(c.date) <= end)
    spans.push(h('span', { class: 'cite' }, `提交 ${litCommits.length}/${S.commitsAsc.length}`))
    for (const name of ['a', 'b', 'main']) {
      let tip: Session['commitsAsc'][number] | null = null
      for (const c of litCommits) if (c.branches.includes(name)) tip = c
      if (tip) spans.push(h('span', { class: 'cite', title: `${tip.sha}\n${tip.subject}` }, `${name}@${sha7(tip.sha)}`))
    }
    for (const tag of S.b.git.tags) {
      const c = S.commitsAsc.find(x => x.sha === tag.sha)
      const lit = c ? ms(c.date) <= end : false
      spans.push(h('span', { class: 'cite', style: lit ? '' : 'opacity:.4' }, `${lit ? '✓' : '·'} ${tag.name}`))
    }
    const gLit = S.b.ops.gate.filter(e => ms(e.ts) <= end).length
    const bLit = S.b.ops.board.filter(e => e.createdAt && e.createdAt <= end).length
    spans.push(h('span', { class: 'cite' }, `门 ${gLit}/${S.b.ops.gate.length}`))
    spans.push(h('span', { class: 'cite' }, `板 ${bLit}/${S.b.ops.board.length}`))
    spans.push(h('span', { class: 'cite' }, `调用 ${S.callsPre[k]}/${S.b.counts.calls}`))
    spans.push(h('span', { class: 'cite' }, `思考 ${S.thoughtsPre[k]}/${S.b.counts.thoughts}`))
    chips.replaceChildren(...spans)

    const dCard = split.children[0]?.children[0]
    if (dCard) {
      ;(dCard.children[0] as HTMLElement).textContent = `第 ${k + 1} 轮 · actor ${t.actor} · ${hhmmss(t.t0)} UTC`
      ;(dCard.children[1] as HTMLElement).replaceChildren(renderDetail(S.b, k, S.sysMap.get(k) ?? []))
    }
  }

  async function selectExp(exp: string, entry?: ReplayIndexEntry): Promise<void> {
    status.textContent = `加载 ${exp} …`
    const b = await loadBundle(exp)
    if (gen !== GEN) return
    LAST.exp = exp
    for (const [e2, btn] of pick) btn.setAttribute('aria-pressed', e2 === exp ? 'true' : 'false')

    const turns = b.sessions.turns
    const N = turns.length
    const callsPre: number[] = []
    const thoughtsPre: number[] = []
    let ca = 0, th = 0
    for (const t of turns) { ca += t.calls.length; th += t.thoughts.length; callsPre.push(ca); thoughtsPre.push(th) }
    const sysMap = mapSystems(b)
    const commitsAsc = commitsByDate(b)
    const strip = buildStrip(b, jump => setStep(jump))

    slider.max = String(Math.max(N, 1))
    num.max = String(Math.max(N, 1))
    num.min = '1'
    stripHost.replaceChildren(strip.el)

    const rows: Session['rows'] = []
    const gitCard = panel(`git 账 · ${commitsAsc.length} 提交(全部,按时间)`)
    const gitBody = h('div', { class: 'rp-ledger' })
    for (const c of commitsAsc) {
      const merge = c.parents.length > 1
      const tags = b.git.tags.filter(t => t.sha === c.sha)
      const row = h('div', { class: 'rp-lrow', title: `${c.sha}\n${c.subject}\n分支可达集:${c.branches.join('/') || '—'}\n${c.date}` },
        h('span', { class: 'g', style: merge ? 'color:var(--rose)' : '' }, merge ? '◆' : '●'),
        h('span', { class: 'sha' }, sha7(c.sha)),
        h('span', { class: 'sub' }, c.subject, ...tags.map(t => h('span', { class: 'tagc' }, ` [${t.name}]`))),
        h('span', { class: 't' }, hhmmss(c.date)))
      gitBody.appendChild(row)
      rows.push({ el: row, ts: ms(c.date) })
    }
    gitCard.children[1].appendChild(gitBody)

    const gate = b.ops.gate
    const board = b.ops.board
    const protoCard = panel(`协议账 · 门 ${gate.length} · 板 ${board.length}`)
    const protoBody = h('div', { class: 'rp-ledger' })
    const pevs: { ts: number; el: HTMLElement }[] = []
    for (const e of gate) pevs.push({ ts: ms(e.ts), el: h('div', { class: 'rp-lrow' },
      h('span', { class: 'g' }, '│'),
      h('span', { class: 'sha' }, hhmmss(e.ts)),
      h('span', { class: 'sub' }, e.text),
      h('span', { class: 't' }, '门')) })
    for (const e of board) {
      const ts = e.createdAt ? new Date(e.createdAt).toISOString() : null
      pevs.push({ ts: ms(ts), el: h('div', { class: 'rp-lrow' },
        h('span', { class: 'g' }, '■'),
        h('span', { class: 'sha' }, hhmmss(ts)),
        h('span', { class: 'sub' }, `${e.kind} · ${e.subject ?? ''} · by ${e.createdBy ?? '?'} · ${e.status ?? '?'}`),
        h('span', { class: 't' }, '板')) })
    }
    pevs.sort((x, y) => x.ts - y.ts)
    for (const p of pevs) { protoBody.appendChild(p.el); rows.push({ el: p.el, ts: p.ts }) }
    protoCard.children[1].appendChild(protoBody)

    const ups = b.sessions.userPrompts ?? []
    const promptCards: HTMLElement[] = []
    if (ups.length) {
      const pb = h('div')
      for (const up of ups) {
        const txt = (up.parts ?? []).map(p => p.text ?? '').join('\n')
        pb.appendChild(details(`actor ${up.actor} · ${hhmmss(up.ts, true)} · ${txt.length.toLocaleString('en-US')} 字`,
          h('div', {}, pre(txt), up.raw ? details('原始行(原文)', pre(up.raw), false, 'rp-raw') : h('span')), false))
      }
      promptCards.push(panel('启动提示(第 0 步)', pb))
    }

    const dCard = panel('本步')
    split.replaceChildren(h('div', {}, dCard), h('div', { class: 'sidecol' }, gitCard, protoCard, ...promptCards))

    meta.replaceChildren(
      h('span', {}, `${b.label} · trial ${entry?.trial ?? '—'} · 窗口 ${hhmmss(b.time_range.t0, true)} → ${hhmmss(b.time_range.t1)}(UTC) · ${b.counts.turns} 轮 / ${b.counts.calls} 调用 / ${b.counts.thoughts} 思考 / ${b.counts.commits} 提交 / ${b.counts.gate} 门 / ${b.counts.board} 板 / ${b.counts.systems} 系统事件 · 转录 ${b.sessions.raw_lines ?? '—'} 行`),
      h('span', { class: 'rp-now' }, `生成于 ${hhmmss(b.generated_at)} UTC`))
    status.textContent = ''

    S = { b, strip, sysMap, commitsAsc, callsPre, thoughtsPre, rows }
    setStep(Math.max(0, Math.min(N - 1, LAST.step)))
  }

  void (async () => {
    try {
      const idx = await loadIndex()
      if (gen !== GEN) return
      if (!idx.length) { status.textContent = '索引为空(replay/index.json 无条目)'; return }
      for (const e of idx) {
        const btn = h('button', {
          class: 'btn act', 'aria-pressed': 'false',
          title: `trial ${e.trial} · ${e.counts.turns} 轮 / ${e.counts.calls} 调用 / ${e.counts.commits} 提交`,
          onclick: () => { void selectExp(e.exp, e).catch(err => { status.textContent = `加载失败:${err instanceof Error ? err.message : String(err)}` }) },
        }, e.exp)
        pick.set(e.exp, btn)
        pickHost.appendChild(btn)
      }
      const def = LAST.exp && pick.has(LAST.exp) ? LAST.exp : idx[idx.length - 1].exp
      const entry = idx.find(e => e.exp === def)
      await selectExp(def, entry)
    } catch (e) {
      if (gen !== GEN) return
      status.textContent = `加载失败:${e instanceof Error ? e.message : String(e)}(需经 dev/preview 服务器打开;file:// 直开会拦截 fetch)`
    }
  })()
}
