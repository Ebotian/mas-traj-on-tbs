// tumor.tsx —— tumor-1~3（双 agent 真实任务）轨迹页：同一 React 回放器，只挂 tumor1~3。
import { createRoot } from 'react-dom/client'
import App from './replay/components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App include={['tumor1', 'tumor2', 'tumor3']} />)
}
