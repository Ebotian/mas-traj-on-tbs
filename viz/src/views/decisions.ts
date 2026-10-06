import { DECISIONS, DECISION_GROUPS } from '../data/corpus.ts'
import { COLOR } from '../lib/palette.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'
import type { Decision } from '../types.ts'

const STATUS: Record<Decision['status'], { label: string; color: string }> = {
  open: { label: '待决', color: COLOR.warn },
  done: { label: '已执行', color: COLOR.good },
  blocked: { label: '被阻塞', color: COLOR.bad },
}

export function render(host: HTMLElement): void {
  const groups = Object.keys(DECISION_GROUPS) as (keyof typeof DECISION_GROUPS)[]
  const counts = groups.map(g => DECISIONS.filter(d => d.group === g))
  const open = DECISIONS.filter(d => d.status === 'open').length
  const blocked = DECISIONS.filter(d => d.status === 'blocked')
  const gating = DECISIONS.filter(d => (d.blocks?.length ?? 0) > 0)

  host.appendChild(h('p', { class: 'lede' },
    `${DECISIONS.length} 项,其中 ${open} 项待决。`,
    '排序不是按重要性,而是按', h('b', {}, '谁挡住谁'),
    ' —— 有一项被阻塞的决策(D1 机制 A)挡住了另外两项。'))

  host.appendChild(h('div', { class: 'stats' },
    stat(String(DECISIONS.length), '决策总数'),
    stat(String(open), '待决', COLOR.warn),
    stat(String(blocked.length), '被阻塞', COLOR.bad),
    stat(String(DECISIONS.filter(d => d.status === 'done').length), '已执行', COLOR.good),
    stat(String(gating.length), '挡住别人的')))

  host.appendChild(panel('阻塞关系 · 关键路径',
    h('div', { class: 'chain' },
      h('div', { class: 'chain-n blocked' }, h('b', {}, 'D1 机制 A 接线'), h('span', {}, '四步一步都没走完')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'D5 跑 8 个 campaign'), h('span', {}, 'R_A1^main 目前是空集')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'B0a 时机是否有因果作用'), h('span', {}, '未启动')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'B0b / B1'), h('span', {}, '未启动'))),
    h('div', { class: 'chain', style: 'margin-top:10px' },
      h('div', { class: 'chain-n warn' }, h('b', {}, 'D2 T1 是否换载体'), h('span', {}, '决定后面几个月;换载体代价未计入任何成本表')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'D3 G₃ 的组织方式'), h('span', {}, '(a) 两臂 pilot 还是 (b) 并入 B0a')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'D4 θ/k/C_min 预注册'), h('span', {}, 'r̂ 与 ℓ 可能退化成一维'))),
    h('div', { class: 'chain', style: 'margin-top:10px' },
      h('div', { class: 'chain-n' }, h('b', {}, 'D15 两处同名异义改名'), h('span', {}, 'ρ 与 RQ1–RQ5')),
      h('div', { class: 'chain-a' }, '→'),
      h('div', { class: 'chain-n' }, h('b', {}, 'D14 两条线是一个纲领还是两个 estimand'), h('span', {}, '合并写作之前必须先解决'))),
    note('这三条链互相独立。D1 那条是唯一有「今天就能动手」的第一步的:',
      h('code', {}, '接线 → 30 分钟长会话 → 对抗绕过探针 → 冻结'), '。')))

  for (const g of groups) {
    const ds = counts[groups.indexOf(g)]
    host.appendChild(panel(`${DECISION_GROUPS[g]} · ${ds.length} 项`,
      h('table', { class: 'tbl dec' },
        h('thead', {}, h('tr', {},
          h('th', {}, 'id'), h('th', {}, '状态'), h('th', {}, '问题'),
          h('th', {}, '挡住'), h('th', {}, '我的建议'), h('th', {}, '出处'))),
        h('tbody', {}, ...ds.map(d => h('tr', { class: d.status },
          h('td', {}, h('b', {}, d.id)),
          h('td', {}, badge(STATUS[d.status].label, STATUS[d.status].color)),
          h('td', {}, d.question),
          h('td', {}, (d.blocks ?? []).join(', ') || '—'),
          h('td', { class: 'rec' }, d.recommendation ?? '—'),
          h('td', {}, cite(d.cite))))))))
  }

  host.appendChild(panel('一条没有被任何一版驳倒的自我攻击',
    h('blockquote', { class: 'big' },
      '请论证「这次梳理本身是代理目标漂移的实例」—— 即绘制概念地图、发现同名异义、复算别人的模拟、再把它做成一个前端工程,是在提高基础设施完整度,而不是提高真实研究能力。'),
    note('用户在轮次 #11(09-17 09:48)亲自命名过这个谬误:',
      h('blockquote', {}, '「你也没必要纠结于要实现或者改进 ada 或者 opl 了,这会陷入代理谬误……货架式方案能满足目的就尽量减少工作」'),
      h('br'),
      '若这条攻击成立,正确的下一步不是补读未读清单,也不是再加一个视图,而是直接做 ',
      h('b', {}, 'D1'), '(接机制 A、跑一次 30 分钟长会话)和 ', h('b', {}, 'D2'), '(决定 T1 是否换载体)。',
      h('br'),
      badge('这个 viz 工程本身就是该攻击的一个候选证据', COLOR.find))))
}
