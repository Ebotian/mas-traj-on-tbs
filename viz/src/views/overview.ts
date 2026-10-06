import { NARROWING } from '../data/corpus.ts'
import { COLOR } from '../lib/palette.ts'
import { arrowMarker, s, text } from '../lib/svg.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'

const G0 = '使开放世界中的真实算法研究更适合 Agent 自动、可靠、长期地推进。'
const REAL6 = [
  '任务和知识边界持续变化',
  '代码库、数据、依赖和模型版本会漂移',
  '研究存在失败、回滚、分叉、合并和人类介入',
  '外部网络和 Git 历史是可用资源',
  '预算是有限的',
  '系统必须在数小时到数周的时间尺度上可恢复,而非仅在一次 prompt 内完成',
]
const NON_GOALS = ['构造 Research OS', '构造统一知识图谱', '训练统一 world model', '最大化 agent autonomy']

const CAPS = [
  { name: 'Recover', rq: 'RQ1 Recoverability', def: '以低成本恢复与当前决策有关的过去', state: 'unmeasured', cite: 'v4.tex:1252, 1547, 1577' },
  { name: 'Understand', rq: 'RQ2 Decision-sufficient state', def: '形成可追溯、可失效、可更新的当前研究状态', state: 'unmeasured', cite: 'v4.tex:1253, 1550, 1578' },
  { name: 'Allocate', rq: 'RQ3 Foresight & resource rationality', def: '把下一单位有限资源分配到最高预期研究价值处', state: 'partial', cite: 'v4.tex:1254, 1553, 1579' },
  { name: 'Learn', rq: 'RQ4 Organizational learning', def: '把重复经验转化为可复用 evidence/procedure/invariant', state: 'unmeasured', cite: 'v4.tex:1255, 1556, 1581' },
]

const RESOURCES = ['token', 'wall-clock', '实验', '检索', 'subagent', 'human attention']

function ratioBar(label: string, got: number, total: number, names: string[], gotName: string, citeStr: string): HTMLElement {
  const pct = total ? got / total : 0
  const cells = names.map(n => h('div', { class: `cell ${n === gotName ? 'on' : ''}`, title: n }, n))
  return h('div', { class: 'ratio' },
    h('div', { class: 'ratio-h' },
      h('b', {}, label),
      h('span', { class: 'ratio-n' }, `${got} / ${total}`),
      h('span', { class: 'ratio-pct', style: `color:${pct >= 0.5 ? COLOR.good : COLOR.bad}` }, `${(pct * 100).toFixed(0)}%`)),
    h('div', { class: 'bar' },
      h('div', { class: 'fill', style: `width:${Math.max(2, pct * 100)}%;background:${pct >= 0.5 ? COLOR.good : COLOR.bad}` })),
    h('div', { class: 'cells' }, ...cells),
    cite(citeStr))
}

function debtCycle(): SVGElement {
  const W = 340, H = 270
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': 'epistemic debt 正反馈环' })
  const defs = s('defs', {}); defs.appendChild(arrowMarker('ahd', COLOR.find)); g.appendChild(defs)
  const N = [
    { id: 'eH', t: 'εₕ', sub: '历史组织误差', x: W / 2, y: 48 },
    { id: 'eR', t: 'εᵣ', sub: '检索误差', x: W - 62, y: H / 2 + 6 },
    { id: 'eS', t: 'εₛ', sub: '状态/控制误差', x: W / 2, y: H - 46 },
    { id: 'w', t: 'waste', sub: '浪费的动作', x: 62, y: H / 2 + 6 },
  ]
  const by = new Map(N.map(n => [n.id, n]))
  for (const [a, b] of [['eH', 'eR'], ['eR', 'eS'], ['eS', 'w'], ['w', 'eH']] as [string, string][]) {
    const p = by.get(a)!, q = by.get(b)!
    const dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy)
    const ux = dx / d, uy = dy / d
    const mx = (p.x + q.x) / 2 + uy * 30, my = (p.y + q.y) / 2 - ux * 30
    g.appendChild(s('path', {
      d: `M${p.x + ux * 34},${p.y + uy * 34}Q${mx},${my} ${q.x - ux * 34},${q.y - uy * 34}`,
      stroke: COLOR.find, 'stroke-width': 2, fill: 'none', 'marker-end': 'url(#ahd)', opacity: 0.85,
    }))
  }
  for (const n of N) {
    const gg = s('g', { transform: `translate(${n.x},${n.y})` })
    gg.appendChild(s('circle', { r: 33, fill: '#fff1f2', stroke: COLOR.find, 'stroke-width': 1.7 }))
    gg.appendChild(text(0, -1, n.t, { 'text-anchor': 'middle', class: 'lbl strong' }))
    gg.appendChild(text(0, 13, n.sub, { 'text-anchor': 'middle', class: 'lbl sm' }))
    g.appendChild(gg)
  }
  g.appendChild(text(W / 2, H - 6, '正反馈:任一项变差都会绕回来放大自己', { 'text-anchor': 'middle', class: 'lbl sm', fill: COLOR.find }))
  return g
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '上位问题是 ', h('b', {}, 'G₀'), ',不是 H_T。H_T 是 Allocate 这一个能力、六种资源里的一种、D 线八行实验矩阵里的一行。',
    '这一页把收窄的倍率量化出来 —— 之前的单文件版只写了四个数字,没有写出分母是什么。'))

  host.appendChild(panel('G₀ · 冻结的唯一上位目标',
    h('p', { class: 'g0' }, G0),
    h('div', { class: 'kv' },
      h('div', {}, h('b', {}, '「真实」的六个条件'),
        h('ul', {}, ...REAL6.map(x => h('li', {}, x)))),
      h('div', {}, h('b', {}, '明确的非目标'),
        h('ul', { class: 'no' }, ...NON_GOALS.map(x => h('li', {}, x))),
        h('p', { class: 'note' }, '准入判据:任何组件 c 只有在 ', h('code', {}, 'ΔG₀(c) > 0'),
          ' 且其收益不能由更成熟、更廉价的 shelf solution 获得时,才进入原创实现范围。'))),
    cite('research_state_control_review_v4.tex:1225-1233')))

  host.appendChild(h('div', { class: 'grid2' },
    panel('收窄倍率 · 从 G₀ 到已被测量的东西',
      h('div', { class: 'stats' },
        stat(`${NARROWING.campaigns.run} / ${NARROWING.campaigns.planned}`, 'campaign 已运行', COLOR.bad),
        stat(`${NARROWING.capabilities.measured} / ${NARROWING.capabilities.total}`, '能力被测(Allocate)'),
        stat(`${NARROWING.resources.measured} / ${NARROWING.resources.total}`, '资源被测(检索)'),
        stat(`${NARROWING.experimentMatrix.instrumented} / ${NARROWING.experimentMatrix.total}`, 'D 线矩阵有仪器'),
        stat(`${NARROWING.stages.reached} / ${NARROWING.stages.total}`, '阶段(冻结 packet → live search)'),
        stat(`第 ${NARROWING.killChain.reached} / ${NARROWING.killChain.depth} 层`, 'kill chain:a0/ 在 RQ3,而 RQ1/RQ2 未测', COLOR.warn),
      ),
      ratioBar('四能力', NARROWING.capabilities.measured, NARROWING.capabilities.total, CAPS.map(c => c.name), 'Allocate', NARROWING.capabilities.cite),
      ratioBar('Allocate 覆盖的资源', NARROWING.resources.measured, NARROWING.resources.total, RESOURCES, '检索', NARROWING.resources.cite),
      ratioBar('D 线八行实验矩阵', NARROWING.experimentMatrix.instrumented, NARROWING.experimentMatrix.total,
        ['Context exposure', 'Retrieval timing', 'Verification ratio', 'Breadth-depth', 'Fault injection', 'Stale-memory', 'False-claim', 'Evaluator drift'],
        'Retrieval timing', NARROWING.experimentMatrix.cite),
      ratioBar('C 线规定的两阶段', NARROWING.stages.reached, NARROWING.stages.total, NARROWING.stages.names, NARROWING.stages.names[0], NARROWING.stages.cite),
      note('分母都来自文档,不是我的估计。', cite(NARROWING.capabilities.cite), cite(NARROWING.resources.cite), cite(NARROWING.experimentMatrix.cite), cite(NARROWING.stages.cite))),
    panel('epistemic debt · 为什么这是一个系统问题而不是三个问题',
      debtCycle(),
      note('三类误差不是独立加性噪声,而是正反馈:', h('br'),
        h('code', {}, 'ε_H↑ ⇒ ε_R↑ ⇒ ε_S↑ ⇒ P(a_t 浪费)↑ ⇒ ε_H↑'), h('br'),
        '这比「context 太长」更一般。累积的、使未来系统越来越难恢复证据、重建状态和作出正确研究决策的负担,称为 epistemic debt。',
        cite('v4.tex:1237-1247')))))

  host.appendChild(panel('四能力 = 控制面(不是九个孤立模块)',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, '能力'), h('th', {}, '定义(原文)'), h('th', {}, '对应 RQ'), h('th', {}, '测量状态'), h('th', {}, '出处'))),
      h('tbody', {}, ...CAPS.map(c => h('tr', {},
        h('td', {}, h('b', {}, c.name)),
        h('td', {}, c.def),
        h('td', {}, c.rq),
        h('td', { class: c.state === 'partial' ? 'part' : 'miss' }, c.state === 'partial' ? '部分:a0/ 测了「检索」这一种资源' : '未测'),
        h('td', {}, cite(c.cite)))))),
    note('原文:「Retrieval、event abstraction、context assembly、forecasting、swarm scheduling、SOP、human deferral 均只是实现这四项能力的手段。」',
      cite('v4.tex:1263'), h('br'),
      'kill chain:', h('code', {}, 'RQ1 → RQ2 → RQ3'), ',RQ4 并行且纵向。',
      h('b', {}, ' a0/ 直接做第 3 层。'),
      '它没有违法:它的状态 s_t = (r̂_t, ℓ_t, b_t) 全部来自 harness 的 verified score trace,是刻意最薄的状态,不需要 RQ1/RQ2 先解决。',
      '代价是:如果薄状态就赢了,你学不到「更厚的、被恢复出来的历史会不会赢得更多」。而 TIMING-REVIEW §3.5 把 D_t→F_t→S_t 留作后续 ablation —— 那正是 RQ1/RQ2 重新进入的地方。',
      cite('v4.tex:1561-1563'))))

  host.appendChild(h('div', { class: 'grid2' },
    panel('Taste ⇄ SOP ⇄ IaC · 成熟度轴,不是三个存储层',
      h('div', { class: 'axis3' },
        h('div', { class: 'a3' }, h('b', {}, 'Taste'), h('span', {}, '开放、依赖经验的 judgment;人类作为 open-set residual controller')),
        h('div', { class: 'a3arr' }, '⇄'),
        h('div', { class: 'a3' }, h('b', {}, 'SOP'), h('span', {}, '可描述的 procedure;交由 agent 执行,依从度随环境与工具而不确定(软约束)')),
        h('div', { class: 'a3arr' }, '⇄'),
        h('div', { class: 'a3' }, h('b', {}, 'IaC / Invariant'), h('span', {}, '可机械执行的硬约束;幂等,code 化(json、数据库)'))),
      note('人类介入的位置:novel / high-impact / low-confidence / conflict / irreversible 状态;并让每次介入成为可校准、可结晶的数据。',
        cite('v4.tex:1585-1589'), h('br'),
        badge('这是用户轮次 #28 里「人类判别」的正式版本', COLOR.frame))),
    panel('九条工程原则(我只读到第八条)',
      h('ol', { class: 'prin' },
        ...['Goal-first:任何组件必须证明其与 G₀ 的关系',
          'Evidence-first:重要动作产生 artifact + evidence + provenance',
          'Facts immutable, views disposable:历史不被 summary 替代',
          'Object-centric:研究是多对象共同演化,而非单 trajectory',
          'Storage ≠ retrieval ≠ context:三者分别优化',
          'Prediction serves allocation:forecast 以 decision value 而非单纯 accuracy 评价',
          'Shelf-first:telemetry、workflow、database、generic provenance 不重造',
          'Field ↔ Lab:field 发现失效模式,lab 识别因果'].map(x => h('li', {}, x)),
        h('li', { class: 'miss' }, '第九条 —— 我没读到(v4.tex:1600 之后)')),
      cite('v4.tex:1592-1600'),
      note(badge('二手 / 部分', COLOR.warn), ' 这一节我只 sed 出了 1580–1600 行,第九条缺失。'))))
}
