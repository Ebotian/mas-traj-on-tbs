// tex.ts —— 数学公式渲染助手(KaTeX;2026-10-15 引入)。
//
// 零框架约定下的小工具:tex(latex) 返回一个已排版的内联 <span>,
// 可直接混入 note()/表格单元格等任何 Kid 位置。throwOnError:false ——
// 语法错误时渲染为红色错误文本,不炸页面。
import katex from 'katex'
import 'katex/dist/katex.min.css'

export function tex(src: string): HTMLSpanElement {
  const span = document.createElement('span')
  span.className = 'tex'
  span.innerHTML = katex.renderToString(src, { throwOnError: false })
  return span
}
