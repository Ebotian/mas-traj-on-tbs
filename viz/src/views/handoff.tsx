// handoff.tsx —— 交接实验(双 agent 走查/机制族)轨迹页:同一 React 回放器。
//
// 归属用**显式 include 白名单**(fail-closed):新跑不会自动落入本页,必须在下方登记 ——
// 2026-10-12 用户裁定「电气试验不应放在交接实验下」后,由 exclude 黑名单改为 include 白名单。
// 本页 = 走查系 17 跑(w4/w5 走查 + w6 机制排练 + w6-4×2 两臂 8 跑 + 2 冒烟 + w7/w8/w9/w10 v3 全链 E2E)
//      + bump-0251(0.25.1 全流程走查) + A2A spike/融合(协作传输机制验证)。
// tumor1/tumor2 → #/tumor;microarch1/2/3/4 → #/microarch。
import { createRoot } from 'react-dom/client'
import App from './replay/components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App
    include={['w4', 'w5', 'w6', 'w6n1', 'w6n2', 'w6n3', 'w6n4', 'w6np', 'w6r1', 'w6r2', 'w6r3', 'w6r4', 'w6rp', 'w7', 'w8', 'w9', 'w10', 'bump0251', 'a2aspike', 'a2afusion']}
    initial="w6" />)
}
