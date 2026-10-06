import { CONFLICTS, REVERSALS } from '../data/corpus.ts'
import { COLOR, EVIDENCE_COLOR, EVIDENCE_LABEL } from '../lib/palette.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'
import type { Conflict } from '../types.ts'

const KIND_LABEL: Record<Conflict['kind'], string> = {
  'name-collision': '同名异义',
  'contradiction': '直接矛盾',
  'false-green': '假绿形状',
  'provenance': '溯源',
  'self-error': '我自己的错误',
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '这一页是全部「只有交叉阅读才能看到」的东西。',
    '每一条都同时给出两边的原文与出处 —— 冲突只有在两侧都被引用时才是可核查的,否则就只是我的印象。'))

  const counts = CONFLICTS.reduce<Record<string, number>>((a, c) => { a[c.kind] = (a[c.kind] ?? 0) + 1; return a }, {})
  host.appendChild(h('div', { class: 'stats' },
    stat(String(CONFLICTS.length), '条冲突'),
    ...Object.entries(counts).map(([k, v]) => stat(String(v), KIND_LABEL[k as Conflict['kind']])),
    stat(String(REVERSALS.reduce((a, r) => a + r.items.length, 0)), '条已登记的反转'),
  ))

  host.appendChild(panel('冲突登记 · 两侧并排',
    h('div', { class: 'conflicts' },
      ...CONFLICTS.map(c => h('article', { class: 'conflict' },
        h('header', {},
          h('h3', {}, c.title),
          badge(KIND_LABEL[c.kind], COLOR.find),
          badge(`证据:${EVIDENCE_LABEL[c.evidence]}`, EVIDENCE_COLOR[c.evidence])),
        h('div', { class: 'sides' },
          h('div', { class: 'side' },
            h('div', { class: 'side-h' }, c.left.who),
            h('blockquote', {}, c.left.quote),
            cite(c.left.cite)),
          h('div', { class: 'vs' }, '⇄'),
          h('div', { class: 'side' },
            h('div', { class: 'side-h' }, c.right.who),
            h('blockquote', {}, c.right.quote),
            cite(c.right.cite))),
        h('p', { class: 'conseq' }, h('b', {}, '后果:'), c.consequence))))))

  host.appendChild(panel('反转登记 · 这个项目的方法是自我推翻,所以反转本身是数据',
    note('按轮次分组。「was」是被推翻的说法,「now」是取代它的说法。',
      badge('v = 我读过那张表', COLOR.good), badge('s = 二手', COLOR.warn)),
    h('div', { class: 'reversals' },
      ...REVERSALS.map(r => h('section', { class: 'rev' },
        h('h3', {}, r.round, h('span', { class: 'rev-meta' }, `${r.date} · ${r.items.length} 条`)),
        cite(r.source),
        badge(`证据:${r.evidence === 'v' ? '我复核' : '二手'}`, r.evidence === 'v' ? COLOR.good : COLOR.warn),
        h('table', { class: 'tbl rev-t' },
          h('thead', {}, h('tr', {}, h('th', {}, '被推翻'), h('th', {}, '取代为'), h('th', {}, '出处'))),
          h('tbody', {}, ...r.items.map(it => h('tr', {},
            h('td', { class: 'was' }, it.was),
            h('td', { class: 'now' }, it.now),
            h('td', {}, cite(it.cite)))))))))))

  host.appendChild(panel('两处同名异义的具体对照',
    h('div', { class: 'grid2' },
      h('div', {},
        h('h4', {}, 'ρ'),
        h('table', { class: 'tbl' },
          h('tbody', {},
            h('tr', {}, h('td', {}, 'D 线'), h('td', {}, 'agent 间错误相关性(latent error correlation)')),
            h('tr', {}, h('td', {}, 'a0/'), h('td', {}, '(R − J_X)/(R − J_0) = assay 的动态范围')),
            h('tr', {}, h('td', {}, '性质'), h('td', {}, '关于世界的量 vs 仪器属性')),
            h('tr', {}, h('td', {}, '明文限制'), h('td', {}, 'a0/ 侧:「MUST NOT 被当作关于世界的证据」;D 线侧:无')))),
        cite('PC-REVISION.md:165-166')),
      h('div', {},
        h('h4', {}, 'RQ1–RQ5'),
        h('table', { class: 'tbl' },
          h('thead', {}, h('tr', {}, h('th', {}, ''), h('th', {}, 'C 线 (09-23)'), h('th', {}, 'D 线 (09-24)'))),
          h('tbody', {},
            h('tr', {}, h('td', {}, 'RQ1'), h('td', {}, 'Recoverability'), h('td', { class: 'part' }, 'Decision-Sufficient State')),
            h('tr', {}, h('td', {}, 'RQ2'), h('td', { class: 'part' }, 'Decision-sufficient state'), h('td', {}, 'Adaptive Observability')),
            h('tr', {}, h('td', {}, 'RQ3'), h('td', {}, 'Foresight & resource rationality'), h('td', {}, 'Epistemic Stability')),
            h('tr', {}, h('td', {}, 'RQ4'), h('td', {}, 'Organizational learning'), h('td', {}, 'Resource Allocation')),
            h('tr', {}, h('td', {}, 'RQ5'), h('td', {}, '—'), h('td', {}, 'Similarity Laws')))),
        cite('v4.tex:1547-1561'), cite('report.tex:304-335'))),
    note('相隔一天。同一个概念 DSS 在两边分别是 RQ2 和 RQ1。',
      '⇒ 任何合并写作都会产生错误的交叉引用。建议加前缀 SC-RQ* / AES-RQ*。')))
}
