import { A0_COVERAGE, CORPUS_COVERAGE, COVERAGE_SUMMARY as S } from '../data/coverage.ts'
import { COLOR, STATUS_COLOR, STATUS_LABEL } from '../lib/palette.ts'
import { badge, cite, h, note, panel, stat } from '../lib/dom.ts'
import type { CoverageRow, ReadStatus } from '../types.ts'

const ORDER: ReadStatus[] = ['read', 'authored', 'partial', 'secondhand', 'recovered', 'generated', 'unread']

function bars(rows: CoverageRow[], title: string, caption: string): HTMLElement {
  const max = Math.max(...rows.map(r => r.lines))
  const body = h('div', { class: 'bars' }, ...rows.map(r => {
    const pct = r.linesRead / Math.max(1, r.lines)
    return h('div', { class: 'brow' },
      h('div', { class: 'bname', title: r.path }, shortName(r.path)),
      h('div', { class: 'btrack' },
        h('div', { class: 'bfull', style: `width:${(r.lines / max) * 100}%` }),
        h('div', { class: 'bread', style: `width:${(r.lines / max) * 100 * pct}%;background:${STATUS_COLOR[r.status]}` })),
      h('div', { class: 'bnum' }, `${r.linesRead} / ${r.lines}`),
      h('div', { class: 'bst' }, badge(STATUS_LABEL[r.status], STATUS_COLOR[r.status])))
  }))
  return panel(title, body, note(caption))
}

function shortName(p: string): string {
  return p.replace('related_files/', '').replace('a0/', 'a0/')
}

export function render(host: HTMLElement): void {
  const pctAll = S.corpusLinesRead / S.corpusLines
  const pctEx = S.corpusLinesReadExclTranscript / S.corpusLinesExclTranscript
  const pctA0 = S.a0LinesRead / S.a0TopMdLines

  host.appendChild(h('p', { class: 'lede' },
    '这一页是给我自己打折用的。前面六个视图都在讲这个项目,这一页讲',
    h('b', {}, '我对它的理解有多少是一手的'), '。'))

  host.appendChild(h('div', { class: 'stats' },
    stat(`${(pctEx * 100).toFixed(1)}%`, `语料逐行读过(${S.corpusLinesReadExclTranscript} / ${S.corpusLinesExclTranscript} 行,不含我自己生成的转录)`, COLOR.bad),
    stat(`${(pctAll * 100).toFixed(1)}%`, `若把转录算作已读(${S.corpusLinesRead} / ${S.corpusLines})—— 这个数是自我美化,我不采用`, COLOR.muted),
    stat(`${(pctA0 * 100).toFixed(1)}%`, `a0/ 顶层报告(${S.a0LinesRead} / ${S.a0TopMdLines} 行)`, COLOR.warn),
    stat(`${S.a0TrackedTotal}`, 'a0/ 跟踪文件总数,我读了 3 份报告', COLOR.bad),
    stat(`${S.repoTrackedTotal}`, '仓库跟踪文件总数')))

  host.appendChild(panel('诚实说明:三档折扣',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, '档'), h('th', {}, '含义'), h('th', {}, '该怎么用'))),
      h('tbody', {},
        h('tr', {}, h('td', {}, badge('我复核', COLOR.good)), h('td', {}, '我亲自读了原文,或亲自跑命令/算数得到'), h('td', {}, '可以当作事实引用')),
        h('tr', {}, h('td', {}, badge('二手', STATUS_COLOR.secondhand)), h('td', {}, '三个只读调查者给的 path:line;我抽样复核了 4 处(4/4 命中),其余未逐条核对'), h('td', {}, '引用时标注二手;抽样命中率不能外推到全部')),
        h('tr', {}, h('td', {}, badge('我没读', COLOR.muted)), h('td', {}, '完全没有读过'), h('td', {}, '我对它说的任何话都是推测')))),
    note('transcript.md 的 61500 行是我生成并检索过的,不是逐行读的。把它算作已读会让语料覆盖率从 ',
      h('b', {}, `${(pctEx * 100).toFixed(1)}%`), ' 虚高到 ', h('b', {}, `${(pctAll * 100).toFixed(1)}%`),
      '。所以我用前者作为标题数字,并把后者标为自我美化。')))

  const counts = ORDER.map(st => ({ st, n: CORPUS_COVERAGE.filter(r => r.status === st).length, lines: CORPUS_COVERAGE.filter(r => r.status === st).reduce((a, r) => a + r.lines, 0) }))
  host.appendChild(panel('语料 35 个文件按阅读状态',
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, '状态'), h('th', {}, '文件数'), h('th', {}, '行数'), h('th', {}, '占语料行数'))),
      h('tbody', {}, ...counts.filter(c => c.n > 0).map(c => h('tr', {},
        h('td', {}, badge(STATUS_LABEL[c.st], STATUS_COLOR[c.st])),
        h('td', {}, String(c.n)),
        h('td', {}, String(c.lines)),
        h('td', {}, `${((c.lines / S.corpusLines) * 100).toFixed(1)}%`))))),
    note('「二手」占了 ', h('b', {}, String(counts.find(c => c.st === 'secondhand')?.n ?? 0)),
      ' 个文件 —— A 线十份、B 线三份、C 线两份。也就是说',
      h('b', {}, '我对三条线的理解,主要建立在调查者的转述加我的抽样复核上'), '。')))

  host.appendChild(bars(CORPUS_COVERAGE, '语料 · 逐文件行数与已读行数',
    '底灰色条 = 文件总行数,彩色条 = 我读过的行数。transcript.md 那一条灰色很长而彩色为零,这是有意的。'))
  host.appendChild(bars(A0_COVERAGE, 'a0/ 顶层报告 · 逐文件',
    'TIMING-REVIEW.md 我只读了 §0–§7(约 460 / 544 行);其余六份完全没读,只在 STATUS.md 与 A1-RESULT.md 的转述里出现。'))

  host.appendChild(panel('比例上的诚实',
    h('table', { class: 'tbl' },
      h('tbody', {},
        h('tr', {}, h('td', {}, 'a0/ 跟踪文件'), h('td', {}, `${S.a0TrackedTotal} 个`), h('td', {}, '我读了 3 份顶层报告')),
        h('tr', {}, h('td', {}, 'a0/ 顶层报告'), h('td', {}, `${S.a0TopMd} 份 / ${S.a0TopMdLines} 行`), h('td', {}, `读了 ${S.a0LinesRead} 行 = ${(pctA0 * 100).toFixed(1)}%`)),
        h('tr', {}, h('td', {}, '语料(不含转录)'), h('td', {}, `${S.corpusLinesExclTranscript} 行`), h('td', {}, `读了 ${S.corpusLinesReadExclTranscript} 行 = ${(pctEx * 100).toFixed(1)}%`)),
        h('tr', {}, h('td', {}, 'D 线正式报告'), h('td', {}, 'report.tex 31503 B / 433 行'), h('td', {}, '只读了章节标题、:14、:254/269/297、:415')),
        h('tr', {}, h('td', {}, 'zip 里的实测数据'), h('td', {}, '3 个 CSV,54 行'), h('td', {}, '逐行读过,并独立复算')))),
    note(badge('结论', COLOR.find),
      ' 我能判断这些文档之间是否自洽,不能判断这些理论是否正确。',
      '梳理里的结构性发现(同名异义、溯源、覆盖率、数值复算)是一手的;',
      '对理论实质本身的评价,大部分是二手或推测。',
      cite('synthesis_2026-09-30.typ §9'))))
}
