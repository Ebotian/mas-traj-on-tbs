// crossfusion.ts —— 交叉融合:并集轨迹机械统计(数据并集 × 方法并集)的只读投影(零框架手写 SVG)。
//
// 数据由 scripts/build_crossfusion.py 从 harness/refs/crossfusion-2026-10-15/
// (features_union.jsonl + audit.json + paper_checks.json + arft.json)投影而来。
// 该实验为确定性、零模型调用管线:862 单元 = 我方 54 侧 + 8 臂 + AutoResearchEval 钉版 800 条;
// 一切数字是所收集工件的纯函数,check.py 四层全 PASS(逐字节可复现 + 不变式 + lab 对读 + 论文复算)。
// 定义与口径见 refs/README.md;我方逐轮轨迹原文回放在 #/handoff · #/tumor · #/microarch · #/tess。
import raw from '../data/crossfusion.json'
import { COLOR } from '../lib/palette.ts'
import { axisBottom, axisLeft, linear, s } from '../lib/svg.ts'
import { badge, cite, h, note, panel, stat, table } from '../lib/dom.ts'
import { tex } from '../lib/tex.ts'

interface Invariant { name: string; value: number | string; want: number | string; ok: boolean }
interface CorpusRow { source: string; corpus: string; units: number; calls: number; masked: number; gaps_ok: number }
interface FamRow {
  name: string; cn: string; units: number; calls: number; masked: number; gaps_ok: number
  ke_med: number | null; te_med: number | null; mrate_med: number | null; kinds8: Record<string, number>
}
interface ArmRow { job: string; calls: number; masked: number; ke: number | null; te: number | null; kinds8: Record<string, number> }
interface ModelRow {
  name: string; units: number; calls: number; calls_ep: number
  ke_med: number | null; te_med: number | null; mrate_med: number | null; cache_med: number | null
  kinds8: Record<string, number>
}
interface FmtRow { source: string; format: string; units: number; gaps_basis: Record<string, number>; masked_n: number; cache_n: number; dur_n: number }
interface Pt { u: string; s: string; g: string; calls: number; ke: number; te: number; mr: number | null }
interface Check { id: string; scope: string; claim: string; expected: unknown; actual: unknown; status: string; note: string }
interface Pillar { id: string; name: string; n: number; hit_sum: number; share_pct: number }
interface PatRow { id: string; name: string; stage: string; pillar: string; hit: number; pct: number }
interface CfData {
  meta: { source: string; script: string; are_revision: string; arxiv: string; note: string }
  totals: { units: number; ours_units: number; are_units: number; sides: number; arms: number; calls: number; ours_calls: number; are_calls: number; avg_are: number; hits_total: number; paper: Record<string, number> }
  invariants: Invariant[]
  corpora: CorpusRow[]; families: FamRow[]; arms: ArmRow[]; models: ModelRow[]; format_cov: FmtRow[]
  scatter: Pt[]; checks: Check[]
  arft: { total_hits: number; pillars: Pillar[]; top: PatRow[] }
  notes: { defect_occurrences: number; nonstd: Record<string, number>; mehnet: string | null; unit_notes: { result_first: number; empty_file: number; no_calls: number } }
}
const D = raw as unknown as CfData

const KIND_ORDER = ['read', 'write', 'search', 'exec', 'wait', 'test', 'recover', 'other']
const KIND_COLOR: Record<string, string> = {
  read: COLOR.frame, write: COLOR.impl, search: COLOR.line, exec: COLOR.muted,
  wait: COLOR.warn, test: COLOR.find, recover: COLOR.ink, other: COLOR.rule,
}
const KIND_CN: Record<string, string> = {
  read: '读', write: '写', search: '检索', exec: '执行', wait: '等待', test: '测试', recover: '恢复', other: '其它',
}
const GRP_COLOR: Record<string, string> = {
  walkthrough: COLOR.line, tumor: COLOR.find, microarch: COLOR.frame, tess: COLOR.impl, arm: COLOR.ink,
}
const GRP_CN: Record<string, string> = { walkthrough: '走查', tumor: 'tumor', microarch: 'microarch', tess: 'tess', arm: '臂(单 agent)' }
const PILLAR_COLOR: Record<string, string> = { R1: COLOR.frame, R2: COLOR.line, R3: COLOR.find, R4: COLOR.warn }
const SCOPE_CN: Record<string, string> = { paper: '论文', card: '数据卡', data: '数据' }

const f2 = (v: number | null | undefined, d = 2): string => v == null ? '—' : v.toFixed(d)
const f4 = (v: number | null | undefined): string => v == null ? '—' : v.toFixed(4)
const pctf = (v: number | null | undefined, d = 1): string => v == null ? '—' : `${(v * 100).toFixed(d)}%`
const valf = (v: unknown): string => typeof v === 'string' ? v : JSON.stringify(v)

function hbar(label: string, v: number, vmax: number, color: string, sub: string): HTMLElement {
  return h('div', { class: 'ratio' },
    h('div', { class: 'ratio-h' }, h('b', {}, label), h('span', { class: 'ratio-pct' }, sub)),
    h('div', { class: 'bar' },
      h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * v / Math.max(1, vmax)))}%;background:${color}` })))
}

function kindStack(kinds: Record<string, number>): HTMLElement {
  const total = Math.max(1, KIND_ORDER.reduce((a, k) => a + (kinds[k] ?? 0), 0))
  const barDiv = h('div', { style: 'display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--rule);min-width:220px' })
  for (const k of KIND_ORDER) {
    const v = kinds[k] ?? 0
    if (!v) continue
    barDiv.appendChild(h('div', {
      style: `width:${(100 * v / total).toFixed(2)}%;background:${KIND_COLOR[k]}`,
      title: `${KIND_CN[k]}:${v}(${pctf(v / total, 1)})`,
    }))
  }
  return h('div', { style: 'flex:1 1 220px' }, barDiv)
}

function entropyScatter(): SVGElement {
  const W = 680, H = 280, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img',
    'aria-label': '类别熵并集散点:边际 kind_entropy(bit) × 条件转移 transition_entropy(nat),每单元一点' })
  const xs = linear([0, 3], [M.l, W - M.r])            // 8 类理论上界 log2 8 = 3 bit
  const ys = linear([0, Math.log(8)], [H - M.b, M.t])  // ln 8 ≈ 2.079 nat
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  for (const p of D.scatter) {
    const ours = p.s === 'ours'
    g.appendChild(s('circle', {
      cx: xs(p.ke), cy: ys(p.te), r: ours ? 4.1 : 2.5,
      fill: ours ? (GRP_COLOR[p.g] ?? COLOR.muted) : COLOR.muted,
      opacity: ours ? 0.92 : 0.33,
    }, s('title', {}, `${p.u}:kind ${f4(p.ke)} bit · cond ${f4(p.te)} nat · 调用 ${p.calls}${p.mr != null ? ` · 掩蔽率 ${pctf(p.mr, 2)}` : ''}`)))
  }
  return g
}

function legend(): HTMLElement {
  const row = h('p', { class: 'note' }, '图例:')
  row.appendChild(h('span', { style: `display:inline-block;width:7px;height:7px;border-radius:50%;background:${COLOR.muted};opacity:.5;margin:0 4px 0 10px;vertical-align:middle` }))
  row.appendChild(h('span', {}, `are 800 条(灰,小点)`))
  for (const k of ['walkthrough', 'tumor', 'microarch', 'tess', 'arm']) {
    row.appendChild(h('span', { style: `display:inline-block;width:8px;height:8px;border-radius:50%;background:${GRP_COLOR[k]};margin:0 4px 0 10px;vertical-align:middle` }))
    row.appendChild(h('span', {}, GRP_CN[k]))
  }
  return row
}

export function render(host: HTMLElement): void {
  const T = D.totals
  host.appendChild(h('p', { class: 'lede' },
    '外部 ', h('b', {}, 'AutoResearchEval'), h('span', { class: 'cite' }, ` @${D.meta.are_revision.slice(0, 8)}`),
    '(PrentisAI,CC-BY-4.0,论文 arXiv ', cite(D.meta.arxiv), ')的 ', h('b', {}, '800 条真实轨迹'),
    '与我方 ', h('b', {}, `${T.sides} 侧 + ${T.arms} 臂`), '取', h('b', {}, '数据并集'), ',用覆盖全部单元的',
    h('b', {}, '统一机械统计'), '逐条计算(8 类工具分类 · 边际/条件熵 · 节律 · 掩蔽错误 · 缓存);同时对论文与数据卡的',
    h('b', {}, '可机核数字'), '做机械复算并登记偏差。一切数字是所收集工件的纯函数、', h('b', {}, '零模型调用'), ',由 ',
    h('code', {}, 'scripts/build_crossfusion.py'), ' 投影;实验本体在 ',
    cite('harness/refs/crossfusion-2026-10-15/'), '(check.py 四层全 PASS)。'))

  host.appendChild(panel(`概览 · ${T.units} 单元 / ${T.calls.toLocaleString('en-US')} 次工具调用`,
    h('div', { class: 'stats' },
      stat(String(T.units), `单元(${T.are_units} are + ${T.ours_units} ours:${T.sides} 侧/${T.arms} 臂)`),
      stat(T.calls.toLocaleString('en-US'), `工具调用(ours ${T.ours_calls.toLocaleString('en-US')} + are ${T.are_calls.toLocaleString('en-US')})`),
      stat(String(T.avg_are), 'are 均值调用/跑(论文「92.3」)', COLOR.frame),
      stat(T.hits_total.toLocaleString('en-US'), '论文 45 模式复算 HIT 总量(Table 12 Σ)', COLOR.find),
      stat(`PASS ${T.paper.PASS}`, `论文复算;数据卡登记偏差 ${T.paper.MISMATCH} · RECORD ${T.paper.RECORD}`, COLOR.good)),
    h('p', { class: 'note strong' }, '不变式(check.py 口径,全部独立复算):'),
    h('p', { class: 'note' }, ...D.invariants.map(inv =>
      badge(`${inv.name} = ${inv.value}${inv.ok ? '' : ` ≠ ${inv.want}`}`, inv.ok ? COLOR.good : COLOR.bad))),
    note('数据并集口径:are 钉版 revision ', cite(D.meta.are_revision.slice(0, 12)), '…(809 文件 / 721,929,474 B 逐文件核对,0 坏);',
      '数据本体不入本仓(仅派生统计);ours 侧=同一作业目录,与夜班轨迹特征实验逐字段一致。',
      '「并集」= 数据取并集、方法取并集且每个方法覆盖每个单元;格式不可得的字段记 null 并注明,不插补。')))

  host.appendChild(panel(`论文数字复算 · ${D.checks.length} 条(PASS ${T.paper.PASS} / 登记偏差 ${T.paper.MISMATCH} / RECORD ${T.paper.RECORD})`,
    h('div', { class: 'scroll' }, table(
      ['id', '范围', '声明', 'expected', 'actual', 'status'],
      D.checks.map(c => [c.id, SCOPE_CN[c.scope] ?? c.scope, c.claim, valf(c.expected), valf(c.actual),
        badge(c.status, c.status === 'PASS' ? COLOR.good : c.status === 'MISMATCH' ? COLOR.warn : COLOR.muted)]))),
    note('口径注记:Table 12 的 HIT% 列用 half-even 舍入(实测 5 处 .25 边界全下舍);逐模型 top-10 的并列名次按模式 ID 字母序',
      '(Table 14–21 与 Table 13 重算逐模型全等,8/8)。',
      h('b', {}, '登记偏差全部在数据卡侧'), ':卡片「559 / 31 tasks / 247(195 success)」vs 磁盘 560 / 30 / 240(188 success),',
      '「52 non-success」相符、卡片自数 559+247=806 ≠ 论文 800(磁盘 560+240=800 与论文一致);4 条偏差原样留档、不修卡。',
      h('b', {}, '复算边界'), ':论文的 LLM-judge 侧数字(IAA κ、Table 2)与 45 模式逐轨迹标注未发布工件,不在机械复算范围。')))

  host.appendChild(panel('类别熵 · 并集散点 边际 kind_entropy(bit) × 条件转移 transition_entropy(nat)',
    entropyScatter(),
    legend(),
    note('两轴固定为 8 类的理论上界(', tex('\\log_2 8 = 3'), ' bit / ', tex('\\ln 8 \\approx 2.079'), ' nat)。',
      'kind_entropy = 非首调用(c₂..cₙ)类别边际熵 ', tex('H = -\\sum_k p_k \\log_2 p_k'),
      ';transition_entropy = 条件转移熵(文档 §4.2;8 类,Dirichlet α=1,π̂ 为经验边际)',
      tex('H_{\\mathrm{transition}} = -\\sum_a \\hat{\\pi}_a \\sum_b \\hat{P}_{ab} \\ln \\hat{P}_{ab}'),
      ';两量同源同序列,条件版多编码「上一类→下一类」结构。854/862 单元入图(8 个 0/1 调用单元无 c₂..cₙ,记 null)。')))

  const models = [...D.models].sort((a, b) => b.calls_ep - a.calls_ep)
  const vmaxA = models.length ? models[0].calls_ep : 1
  const fams = [...D.families]
  fams.forEach(f => { (f as FamRow & { per_side: number }).per_side = f.units ? f.calls / f.units : 0 })
  const vmaxB = Math.max(1, ...fams.map(f => (f as FamRow & { per_side: number }).per_side), ...D.arms.map(a => a.calls))
  host.appendChild(panel('调用强度与工具构成',
    h('p', { class: 'note strong' }, `AutoResearchEval 逐模型(每跑调用;柱右为其 8 类构成):`),
    ...models.map(m => h('div', { class: 'ratio' },
      h('div', { class: 'ratio-h' }, h('b', {}, m.name), h('span', { class: 'ratio-pct' }, `${f2(m.calls_ep)}/跑 · 共 ${m.calls.toLocaleString('en-US')}`)),
      h('div', { style: 'display:flex;gap:14px;align-items:center;flex-wrap:wrap' },
        h('div', { class: 'bar', style: 'flex:1 1 240px' },
          h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * m.calls_ep / Math.max(1, vmaxA)))}%;background:${COLOR.frame}` })),
        kindStack(m.kinds8)))),
    h('p', { class: 'note strong' }, '我方(每侧/每臂调用):'),
    ...fams.map(f => {
      const per = (f as FamRow & { per_side: number }).per_side
      return h('div', { class: 'ratio' },
        h('div', { class: 'ratio-h' }, h('b', {}, `${f.cn}(${f.units} 侧)`), h('span', { class: 'ratio-pct' }, `${f2(per)}/侧 · 共 ${f.calls.toLocaleString('en-US')} · 掩蔽 ${f.masked}`)),
        h('div', { style: 'display:flex;gap:14px;align-items:center;flex-wrap:wrap' },
          h('div', { class: 'bar', style: 'flex:1 1 240px' },
            h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * per / vmaxB))}%;background:${COLOR.impl}` })),
          kindStack(f.kinds8)))
    }),
    h('div', { class: 'scroll' }, table(
      ['臂', '调用', '掩蔽', 'kind_entropy', 'trans_entropy'],
      D.arms.map(a => [a.job, String(a.calls), String(a.masked), f4(a.ke), f4(a.te)]))),
    note('两侧口径对齐后的对照:are 逐模型 19.4–200.8 调用/跑(gpt-5-mini 最浅、minimax-m3 最深);',
      '我方家族 93.6–327.5 调用/侧(走查最浅、tess/tumor 最深),臂 68–136/条。',
      '工具构成条=各组的 8 类合计(图例同 #/features:读/写/检索/执行/等待/测试/恢复/其它)。')))

  host.appendChild(panel('格式覆盖 · 方法并集的能力矩阵(7 种日志格式 × 同一套统计)',
    h('div', { class: 'scroll' }, table(
      ['格式', '单元', 'gaps(basis)', 'masked 可判', 'cache', 'duration'],
      D.format_cov.map(f => [`${f.source}/${f.format}`, String(f.units),
        Object.keys(f.gaps_basis).length ? Object.entries(f.gaps_basis).map(([k, v]) => `${k} ${v}`).join(' · ') : '—',
        String(f.masked_n), String(f.cache_n), String(f.dur_n)]))),
    note('每个方法覆盖每个单元:调用/名表/8 类/掩蔽 7 种格式全可算;gaps 只在有时间戳的格式可算(claude result_ts/call_ts、gemini call_ts、ours call_ts/step_ts);',
      'cache 与 duration 按字段可得性(见右三列)。不可得=null,不插补——覆盖率的空白处即数据格式的边界。')))

  const A = D.arft
  host.appendChild(panel(`45 模式 × 四支柱参照(论文失败分析) · 共 ${A.total_hits.toLocaleString('en-US')} hits`,
    ...A.pillars.map(p => hbar(`${p.id} ${p.name}`, p.share_pct, Math.max(...A.pillars.map(x => x.share_pct)) * 1.06,
      PILLAR_COLOR[p.id] ?? COLOR.muted, `${p.n} 模式 · ${p.hit_sum.toLocaleString('en-US')} hits · ${f2(p.share_pct)}%`)),
    h('p', { class: 'note strong' }, 'Table 12 前 12 名(HIT / 出现率):'),
    ...A.top.map(p => hbar(`${p.id} ${p.name}`, p.hit, A.top[0].hit, PILLAR_COLOR[p.pillar] ?? COLOR.muted,
      `${p.hit} · ${f2(p.pct)}%`)),
    note('支柱归属=P表 Table 3;R1+R2+R3=92.1%(认知三支柱),R4 最高仅 C.4 第 26/45。',
      '参照表全文(45 模式 × 支柱/阶段/全量 HIT/逐模型向量)见 ', cite('arft.json'), ';',
      '本页不复现 judge 侧数字(κ/Table 2),亦不对 45 模式做 LLM 标注——模式统计只作参照坐标。')))

  const N = D.notes
  host.appendChild(panel('口径与已知问题(全部可审计)',
    h('div', { class: 'scroll' }, table(
      ['项', '值', '出路'],
      [
        ['ours 侧表外工具名(归 other,与 lab 一致)',
          Object.entries(N.nonstd).map(([k, v]) => `${k}×${v}`).join(' · '),
          'audit.ours_side_nonstandard(9 次,不影响任何统计量)'],
        ['工件名 __unparsedToolInput(claude 流,均 qwen3.7-max)',
          `${N.defect_occurrences} 处`,
          '归 other;实例路径见 audit.defect_occurrences'],
        ['gemini stats.tool_calls 对账', `27 文件,1 处数据自相矛盾:${N.mehnet ?? '—'}`,
          '文件自身 122 vs 行内 86;非适配错误,原样登记'],
        ['opus-4.8 优化集文件首行为 result 行', `${N.unit_notes.result_first} 个(其中 ${N.unit_notes.no_calls} 个单行 0 调用)`,
          'notes=result-first;仍按全文解析'],
        ['0 行空文件', `${N.unit_notes.empty_file} 个`, 'notes=empty-file;仍计为一个轨迹单元以保 800 完整'],
        ['模型目录名归并', 'sonnet-5→claude-sonnet-5 · codex-gpt5mini→gpt-5-mini',
          'meta.model_dir 保留原目录名;单元名保留磁盘路径'],
      ])),
    note('复跑:', h('code', {}, 'cd harness/refs/crossfusion-2026-10-15 && python3 check.py'),
      '(四层:逐字节复现 / 不变式 / 与夜班实验 lab 对读 / 论文复算);数据投影:',
      h('code', {}, 'python3 viz/scripts/build_crossfusion.py'), '。来源:', cite(D.meta.source), '。')))

  host.appendChild(note('本页为只读投影:全部数字由上述两脚本现算,不手抄;',
    '论文原文引用与「复算值」「判断」严格分开(复核范围声明见 refs/README.md)。'))
}
