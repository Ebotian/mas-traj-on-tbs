// microarch.tsx —— 电气试验(microarch 代理题真实任务)轨迹页:同一 React 回放器,只挂 microarch1/microarch2。
// 2026-10-12 用户裁定「电气试验不应放在交接实验下」,自 #/handoff 独立成页。
import { createRoot } from 'react-dom/client'
import App from './replay/components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App include={['microarch1', 'microarch2']} />)
}
