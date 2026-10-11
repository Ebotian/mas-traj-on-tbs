import { h } from './lib/dom.ts'
import * as overview from './views/overview.ts'
import * as map from './views/map.ts'
import * as numbers from './views/numbers.ts'
import * as arms from './views/arms.ts'
import * as time from './views/time.ts'
import * as conflicts from './views/conflicts.ts'
import * as decisions from './views/decisions.ts'
import * as coverage from './views/coverage.ts'
import * as library from './views/library.ts'
import * as replay from './views/replay/index.tsx'
import * as handoff from './views/handoff.tsx'
import * as tumor from './views/tumor.tsx'
import './style.css'

interface View { id: string; label: string; hint: string; render: (host: HTMLElement) => void }

const VIEWS: View[] = [
  { id: 'overview', label: '总览', hint: 'G₀、收窄倍率、epistemic debt、四能力', render: overview.render },
  { id: 'map', label: '结构图', hint: '54 节点 / 72 边,分层力导', render: map.render },
  { id: 'numbers', label: '实测数字', hint: 'exp1–exp3、强度曲线、成本', render: numbers.render },
  { id: 'arms', label: '手臂对比', hint: '六格雷达:正确率 × 成本 × 墙钟(2026-10-10)', render: arms.render },
  { id: 'time', label: '时间轴', hint: '09-09 → 10-06,五次来源', render: time.render },
  { id: 'conflicts', label: '冲突与反转', hint: '两侧并排 + 反转登记', render: conflicts.render },
  { id: 'decisions', label: '决策', hint: '33 项,按阻塞关系排', render: decisions.render },
  { id: 'coverage', label: '我的覆盖率', hint: '一手 / 二手 / 没读', render: coverage.render },
  { id: 'library', label: '账户库', hint: '159 条 · 取回 17 份 · 一处结论被推翻', render: library.render },
  { id: 'replay', label: '轨迹重建', hint: 'w4/w5 逐步回放:滑块 × 轮 · git 节点 · 工具与思考可展开', render: replay.render },
  { id: 'handoff', label: '交接实验', hint: '走查全族 13 跑逐步回放:w4/w5/w6/4×2', render: handoff.render },
  { id: 'tumor', label: 'tumor 双agent', hint: 'tumor-1 真实任务:422 轮 / 430 调用 / 28 提交', render: tumor.render },
]

function currentId(): string {
  const h0 = location.hash.replace(/^#\/?/, '')
  return VIEWS.some(v => v.id === h0) ? h0 : 'overview'
}

function mount(): void {
  const host = document.getElementById('view')
  const hint = document.getElementById('hint')
  if (!host || !hint) return
  const id = currentId()
  const view = VIEWS.find(v => v.id === id) ?? VIEWS[0]
  host.textContent = ''
  hint.textContent = view.hint
  for (const b of document.querySelectorAll<HTMLButtonElement>('nav button')) {
    b.setAttribute('aria-current', b.dataset.id === view.id ? 'true' : 'false')
  }
  document.title = `rsi-dev · ${view.label}`
  view.render(host)
  host.scrollIntoView({ block: 'start' })
}

const app = document.getElementById('app')
if (app) {
  app.appendChild(h('header', { class: 'top' },
    h('div', { class: 'top-t' },
      h('h1', {}, '构想结构可视化'),
      h('p', {}, 'G₀ 到 H_T 的收窄链、实测数字、反转史、冲突登记,梳理者自己的阅读覆盖率,以及账户库的核查台账。',
        h('span', { class: 'top-meta' }, '仓库 rsi-dev · main @ 301a4be · 本地无 remote · 数据核对于 2026-10-06(含当日账户库核查)'))),
    h('nav', {}, ...VIEWS.map(v => h('button', {
      'data-id': v.id,
      onclick: () => { location.hash = `#/${v.id}` },
    }, v.label)))))
  app.appendChild(h('main', { id: 'view' }))
  app.appendChild(h('div', { class: 'hintbar' }, h('span', { id: 'hint' })))
  app.appendChild(h('footer', {},
    '颜色从不单独承载信息:形状、直接标签、线型、描边虚实各自独立编码一个维度。',
    '调色板经 dataviz 校验器检查(3 彩色 + 1 中性;6 色方案在色盲模拟下多组可混,已放弃)。',
    '标为【推断】的内容不来自任何文档。'))
  window.addEventListener('hashchange', mount)
  mount()
}
