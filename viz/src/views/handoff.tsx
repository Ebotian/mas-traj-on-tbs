// handoff.tsx —— 交接实验（双 agent 走查）轨迹页：同一 React 回放器，过滤出走查全族。
//
// 全族 = w4/w5（既有）+ w6 机制排练 + w6-4×2 两臂 8 跑 + 2 冒烟；tumor1 归 #/tumor。
import { createRoot } from 'react-dom/client'
import App from './replay/components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App exclude={['tumor1']} initial="w6" />)
}
