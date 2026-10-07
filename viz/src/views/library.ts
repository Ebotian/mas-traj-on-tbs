import { BLOCKED, LADDER, LIB_NOTES, LIB_TOTALS as T, MECHANISMS, RECOVERED, ROUTE_LABEL } from '../data/library.ts'
import { COLOR } from '../lib/palette.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'
import type { Route } from '../data/library.ts'

const ROUTE_COLOR: Record<Route, string> = {
  stitch: COLOR.impl,   // 无损:拼出的文本与磁盘逐字节相同
  copy: COLOR.frame,    // 无损:剪贴板里是源码原文
  iframe: COLOR.warn,   // 有损:只剩渲染文本
}

function kbytes(n: number): string {
  return `${(n / 1024).toFixed(1)} KB`
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '账户侧还有一个 Library,里面有 ', h('b', {}, String(T.entries)), ' 份文件。',
    '这一页是 2026-10-06 的核查:哪些是仓库已有的重复件,哪些是仓库没有的,取回时各走了哪条通道,以及',
    h('b', {}, '哪一条此前的结论被这次核查推翻'), '。'))

  const bStat = (k: string) => BLOCKED.filter(b => b.status === k).length
  host.appendChild(h('div', { class: 'stats' },
    stat(String(T.entries), '库页卡片总数(懒加载到底)'),
    stat(String(T.unmatched), '按名比对后本地没有', COLOR.warn),
    stat(String(T.recovered), '本轮取回并提交', COLOR.good),
    stat(String(bStat('reason')), '取不到:原因已查明', COLOR.bad),
    stat(String(bStat('symptom')), '取不到:仅记录现象'),
    stat(String(bStat('not-taken')), '未取(是重复件)'),
    stat(String(bStat('not-attempted')), '未尝试'),
    stat(String(T.archives), '归档形态(按规则不入 git)'),
    stat(`~${T.other}`, '属于其他项目(emsx/BESS、金融、个人配置)')))

  const maxL = Math.max(...LADDER.map(l => l.lines))
  host.appendChild(panel('B 线阶梯:六版独立审查',
    h('div', { class: 'bars' }, ...LADDER.map(l => h('div', { class: 'brow' },
      h('div', { class: 'bname' }, l.v),
      h('div', { class: 'btrack' }, h('div', { class: 'bfull', style: `width:${(l.lines / maxL) * 100}%` })),
      h('div', { class: 'bnum' }, String(l.lines)),
      h('div', { class: 'bst' }, l.note)))),
    note(badge('校准点', COLOR.good), ' ',
      '磁盘上的 ', h('code', {}, 'open_world_plan_independent_review.typ'), ' 就是 v(6):',
      '取回件归一化后与它 ', h('b', {}, '逐字节相同'), '(只差一个尾部空行),六份也都单独 typst 编译通过。',
      '行数 601 → 663 → 762 → 839 → 935 → 1030 单调,像一轮轮加长的审查,不是同一份的重复上传。')))

  host.appendChild(panel('取回清单(17 份,三个提交)',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {},
        h('th', {}, '文件'), h('th', {}, '库内日期'), h('th', {}, '大小'),
        h('th', {}, '行'), h('th', {}, '通道'), h('th', {}, '校验'))),
      h('tbody', {}, ...RECOVERED.map(r => h('tr', {},
        h('td', {}, h('code', {}, r.name)),
        h('td', {}, r.date),
        h('td', {}, kbytes(r.bytes)),
        h('td', {}, String(r.lines)),
        h('td', {}, badge(ROUTE_LABEL[r.route], ROUTE_COLOR[r.route])),
        h('td', {}, r.verify))))),
    note('前五份属 B 线(09-18→09-20);中间九份是 D 线 / a0 侧 / AdaPDC C0(09-09→09-24);',
      '最后三份只有渲染文本 —— 它们是 Deep Research 报告,拿不到 markdown 原文,文件名因此带 ',
      h('code', {}, '.rendered.txt'), ' 后缀。')))

  host.appendChild(panel('三条通道,各自会骗你的地方',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, '预览器'), h('th', {}, '取法'), h('th', {}, '陷阱'))),
      h('tbody', {}, ...MECHANISMS.map(m => h('tr', {},
        h('td', {}, m.viewer), h('td', {}, m.route), h('td', {}, m.trap)))))))

  host.appendChild(panel('取不到与没取的',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, '条目'), h('th', {}, '原因'))),
      h('tbody', {}, ...BLOCKED.map(b => h('tr', {},
        h('td', {}, h('code', {}, b.name)), h('td', {}, b.why))))),
    note('这七条都不是「忘了」:两条 .typ 的预览确实不渲染,一条根本不是文本(是 zip),',
      '另两条与未跟踪的 repro zip 重复,最后两条没有尝试。')))

  host.appendChild(panel('两条机制性的坑,以及被推翻的那句话',
    h('table', { class: 'tbl' },
      h('tbody', {},
        h('tr', {}, h('td', {}, badge('被推翻', COLOR.bad)), h('td', {}, LIB_NOTES.falsified)),
        h('tr', {}, h('td', {}, badge('搜索的边界', COLOR.warn)), h('td', {}, LIB_NOTES.searchTrap)),
        h('tr', {}, h('td', {}, badge('下载已坏', COLOR.warn)), h('td', {}, LIB_NOTES.downloadDead)),
        h('tr', {}, h('td', {}, badge('重复件', COLOR.muted)), h('td', {}, LIB_NOTES.dupPolicy)))),
    note('这一页只讲「哪些文件在、怎么拿到」,不讲内容。取回的 17 份', h('b', {}, '我一行都没读'),
      ' —— 按本项目的记法,它们的阅读状态是「已取回,未读」,不是「已理解」。',
      cite('commit 900bcb0 · ef9d9b2 · 301a4be'))))
}
