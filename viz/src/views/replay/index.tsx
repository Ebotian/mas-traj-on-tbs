// replay/index.ts —— 轨迹重建页面入口。
//
// 约定：每个视图导出 {render(host: HTMLElement): void}，主导航(#/replay)调用 mount() 时传入
// #view 宿主 div。此处创建 React 根节点并挂载 App——后续所有 UI 由 React 的声明式渲染管理。
// 探针只断言外壳文案(data层走fetch，同numbers先例)。

import { createRoot } from 'react-dom/client'
import App from './components/App'

export function render(host: HTMLElement): void {
  const root = createRoot(host)
  root.render(/*#__PURE__*/ <App />)
}
