import { TIMELINE } from '../data/corpus.ts'
import { COLOR } from '../lib/palette.ts'
import { badge, cite, h, note, panel } from '../lib/dom.ts'

const TRACK: Record<string, { label: string; color: string; note: string }> = {
  'input': { label: '用户自带的输入', color: COLOR.line, note: '对话只读取,从未写入;来自「opl 那个压缩包」' },
  'conversation': { label: '被解码的那条对话', color: COLOR.frame, note: '09-17 08:46 → 09-24 07:36 UTC,4011 节点,完全线性' },
  'other-conversation': { label: '另一条对话', color: COLOR.find, note: 'D 线的叙事文档;SILO-BENCH 在被解码的对话里 0 命中' },
  'repo': { label: '仓库实现 (a0/)', color: COLOR.impl, note: '测量链' },
  'this-session': { label: '本次整理', color: COLOR.warn, note: '09-30、10-06 与 10-07' },
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '时间是这个语料里最被低估的一个维度:',
    h('b', {}, 'C 线的四轮修订发生在 83 分钟内'), ',而 ',
    h('b', {}, 'D 线的三跳跨了两条不同的对话'),
    '。层级图看不出这两件事,时间轴可以。'))

  const tracks = Object.keys(TRACK)
  host.appendChild(h('div', { class: 'stats' },
    ...tracks.map(t => stat2(TIMELINE.filter(e => e.track === t).length, TRACK[t].label, TRACK[t].color))))
  host.appendChild(note(...tracks.flatMap((t, i) => [
    i ? ' · ' : '',
    h('b', { style: `color:${TRACK[t].color}` }, TRACK[t].label), ' = ', TRACK[t].note,
  ])))

  const rows = TIMELINE.map(e => {
    const tr = TRACK[e.track]
    return h('div', { class: 'tl-row' },
      h('div', { class: 'tl-when' },
        h('b', {}, e.date),
        e.clock ? h('span', { class: 'tl-clock' }, e.clock) : null),
      h('div', { class: 'tl-spine' }, h('span', { class: 'tl-dot', style: `background:${tr.color}` })),
      h('div', { class: 'tl-what' },
        h('div', { class: 'tl-label' }, e.label),
        h('div', { class: 'tl-meta' },
          badge(tr.label, tr.color),
          e.artifact ? cite(e.artifact) : null),
        e.note ? h('p', { class: 'note' }, e.note) : null))
  })

  host.appendChild(panel('时间轴 · 09-09 → 10-07', h('div', { class: 'tl' }, ...rows)))

  host.appendChild(h('div', { class: 'grid2' },
    panel('四次转向都由用户先说出',
      h('table', { class: 'tbl' },
        h('thead', {}, h('tr', {}, h('th', {}, '轮次'), h('th', {}, '时间 UTC'), h('th', {}, '转向'), h('th', {}, '文档何时才写下它'))),
        h('tbody', {},
          h('tr', {}, h('td', {}, '#11'), h('td', {}, '09-17 09:48'), h('td', {}, '命名为代理谬误,A 线降级'), h('td', {}, 'plan.typ:53,晚约 20 小时')),
          h('tr', {}, h('td', {}, '#17–18'), h('td', {}, '09-18 02:47 / 02:54'), h('td', {}, 'open problems must in open world'), h('td', {}, '同日的工程计划')),
          h('tr', {}, h('td', {}, '#26–27'), h('td', {}, '09-23 02:09 / 06:07'), h('td', {}, 'H_O 降为前提,主假设换成 H_T'), h('td', {}, 'TIMING-REVIEW(09-23)')),
          h('tr', {}, h('td', {}, '#28'), h('td', {}, '09-23 07:40'), h('td', {}, '三重困难 + 三类解法'), h('td', {}, 'C 线 v1–v4(同日 08:10→09:34)')))),
      note('⇒ 构想的脊柱是提问,不是文档。文档是这些提问的沉淀物。', cite('related_files/conversation/user_turns.md'))),
    panel('三个时间尺度上的压缩',
      h('table', { class: 'tbl' },
        h('thead', {}, h('tr', {}, h('th', {}, '事件'), h('th', {}, '跨度'), h('th', {}, '含义'))),
        h('tbody', {},
          h('tr', {}, h('td', {}, 'C 线 v1 → v4'), h('td', {}, '83 分钟'), h('td', {}, '四轮修订,第四轮否定了自己的线名')),
          h('tr', {}, h('td', {}, 'D 线 report.tex → Pasted md → 审查'), h('td', {}, '约 2.5 小时'), h('td', {}, '三跳,且跨两条对话')),
          h('tr', {}, h('td', {}, 'B 线六版审查'), h('td', {}, '09-18 → 09-20'), h('td', {}, 'v(1)–(5) 已从账户库取回,v(6) = 磁盘那份 —— 原判「中间版本永久缺失」已推翻')),
          h('tr', {}, h('td', {}, 'a0/ 测量链'), h('td', {}, '09-20 → 09-23'), h('td', {}, '仪器建成,campaign 仍为 0')))),
      note(badge('注意', COLOR.find),
        ' 理论侧的迭代速度(小时级)与落地侧的迭代速度(天级)差一个数量级,而落地侧的产出是零个数据点。',
        '这不是效率问题,是「先证明尺子准」这条纪律的代价。'))))
}

function stat2(value: number, label: string, color: string): HTMLElement {
  return h('div', { class: 'stat', style: `border-left-color:${color}` }, h('b', {}, String(value)), h('span', {}, label))
}
