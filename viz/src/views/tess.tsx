// tess.tsx —— TESS 凌星筛选(tess-transit-vetting 第三任务族真实任务)轨迹页:同一 React 回放器,只挂 tess1。
// 2026-10-15 建成(第三任务族首跑入列;用户令「做viz补充」)。
import { createRoot } from 'react-dom/client'
import App from './replay/components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App include={['tess1']} />)
}
