// features.ts —— 轨迹特征:2026-10-14 夜班「轨迹特征数值实验」的只读投影(零框架手写 SVG)。
//
// 数据由 scripts/build_traj_features.py 从 harness/refs/traj-features-2026-10-14/
// (features_sides|runs|arms.jsonl + selection_features.json)投影而来。该实验为确定性、
// 零模型调用管线:一切数字是所收集工件的纯函数,check.py 全 PASS(逐字节可复现 + 不变式)。
// 定义与口径见 refs/README.md;逐轮轨迹原文回放在 #/handoff · #/tumor · #/microarch · #/tess。
import raw from '../data/traj_features.json'
import { COLOR } from '../lib/palette.ts'
import { axisBottom, axisLeft, linear, s, text } from '../lib/svg.ts'
import { badge, cite, h, note, panel, stat, table } from '../lib/dom.ts'

interface Invariant { name: string; value: number | string | null; want: number; ok: boolean }
interface FamRec {
  name: string; runs: number; sides: number; calls: number; masked: number
  kinds: Record<string, number>; cache_med: number | null; span_med: number | null
  kind_ent_med: number | null; trans_ent_med: number | null
}
interface SideRow {
  job: string; family: string; side: string; calls: number | null; masked: number | null
  masked_rate: number | null; cache_ratio: number | null; span_s: number | null
  gap_med_s: number | null; cv: number | null; p600: number | null
  kind_entropy: number | null; transition_entropy: number | null
  kinds: Record<string, number> | null
}
interface RunRow {
  job: string; family: string; calls: number | null; masked: number | null
  cache_a: number | null; cache_b: number | null; span_a: number | null; span_b: number | null
  rounds_a: string | null; rounds_b: string | null; normal: boolean | null
  gate_ok: number | null; gate_block: number | null
}
interface ArmRow { job: string; schema: string | null; steps: number | null; calls: number | null; masked: number | null }
interface SurfRow {
  name: string; n: number; tau_min: number | null; tau_med: number | null; tau_max: number | null
  regret_pos: number | null; regret_max: number | null
}
interface BlendRec { tau_mean?: number; regret?: number; mape?: number; picked?: string; best?: string }
interface SelData {
  run: string; candidates_total: number; picked_union: string[]; emax_sigma05: number | null
  blend: Record<string, BlendRec | number>
  hidden: { ipc_mape?: number; mean_workload_kendall_tau?: number; top_1_regret?: number; true_best_design?: string; predicted_best_design?: string }
  gap: number; surfaces: SurfRow[]; pool_preds: { shape?: number[] } | null
}
interface FeatData {
  meta: { source: string; script: string; note: string }
  totals: { runs: number; sides: number; arms: number; calls: number; masked: number; arms_calls: number; arms_masked: number }
  families: FamRec[]; runs: RunRow[]; sides: SideRow[]; arms: ArmRow[]
  invariants: Invariant[]; selection: SelData
}
const D = raw as unknown as FeatData

const FAM_CN: Record<string, string> = { walkthrough: '走查', tumor: 'tumor', microarch: 'microarch', tess: 'tess' }
const FAM_COLOR: Record<string, string> = { walkthrough: COLOR.line, tumor: COLOR.find, microarch: COLOR.frame, tess: COLOR.impl }
const KIND_ORDER = ['read', 'write', 'search', 'exec', 'wait', 'test', 'recover', 'other']
const KIND_COLOR: Record<string, string> = {
  read: COLOR.frame, write: COLOR.impl, search: COLOR.line, exec: COLOR.muted,
  wait: COLOR.warn, test: COLOR.find, recover: COLOR.ink, other: COLOR.rule,
}
const KIND_CN: Record<string, string> = {
  read: '读 read_file/list_directory', write: '写 write_file/edit', search: '检索 glob/grep', exec: '执行 shell',
  wait: '等待 wait_*/inotifywait', test: '测试 pytest/check_*.py', recover: '恢复 recover', other: '其它',
}
const BLEND_CN: Record<string, string> = {
  a_full: 'a 全量拟合', a_loco: 'a LOCO', b_full: 'b 全量拟合', b_loco: 'b LOCO', blend_loco_50: '50% 混合 LOCO',
}

const pctf = (v: number | null | undefined, d = 1): string => v == null ? '—' : `${(v * 100).toFixed(d)}%`
const f2 = (v: number | null | undefined, d = 2): string => v == null ? '—' : v.toFixed(d)
const f4 = (v: number | null | undefined): string => v == null ? '—' : v.toFixed(4)
const wallf = (sec: number | null): string =>
  sec == null ? '—' : `${Math.floor(sec / 60)}m${String(Math.round(sec % 60)).padStart(2, '0')}s`
const jshort = (job: string): string => job.replace(/^agent-/, '')

function hbar(label: string, v: number, vmax: number, color: string, sub: string): HTMLElement {
  return h('div', { class: 'ratio' },
    h('div', { class: 'ratio-h' }, h('b', {}, label), h('span', { class: 'ratio-pct' }, sub)),
    h('div', { class: 'bar' },
      h('div', { class: 'fill', style: `width:${Math.max(1, Math.min(100, 100 * v / Math.max(1, vmax)))}%;background:${color}` })))
}

function kindStack(kinds: Record<string, number>): HTMLElement {
  const total = Math.max(1, KIND_ORDER.reduce((a, k) => a + (kinds[k] ?? 0), 0))
  const barDiv = h('div', { style: 'display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--rule);min-width:280px' })
  for (const k of KIND_ORDER) {
    const v = kinds[k] ?? 0
    if (!v) continue
    barDiv.appendChild(h('div', {
      style: `width:${(100 * v / total).toFixed(2)}%;background:${KIND_COLOR[k]}`,
      title: `${KIND_CN[k]}:${v}(${pctf(v / total, 1)})`,
    }))
  }
  return h('div', { style: 'flex:1 1 280px' }, barDiv)
}

function rhythmScatter(): SVGElement {
  const W = 680, H = 250, M = { l: 52, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': '节律:中位间隔(s) × CV_robust(每侧一点;◉=含 >600s 间隔)' })
  const pts = D.sides.filter(p => p.cv != null && p.gap_med_s != null)
  if (!pts.length) return g
  const xmax = Math.max(0.5, ...pts.map(p => p.cv as number)) * 1.08
  const ymax = Math.max(5, ...pts.map(p => p.gap_med_s as number)) * 1.08
  const xs = linear([0, xmax], [M.l, W - M.r])
  const ys = linear([0, ymax], [H - M.b, M.t])
  g.appendChild(axisLeft(ys, M.l, v => `${Math.round(v)}s`))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  for (const p of pts) {
    const stall = (p.p600 ?? 0) > 0
    g.appendChild(s('circle', {
      cx: xs(p.cv as number), cy: ys(p.gap_med_s as number), r: 3.8,
      fill: FAM_COLOR[p.family] ?? COLOR.muted, opacity: 0.9,
      stroke: stall ? COLOR.bad : 'none', 'stroke-width': stall ? 1.8 : 0,
    }, s('title', {}, `${p.job} · ${p.side}:中位间隔 ${f2(p.gap_med_s, 2)}s · CV ${f2(p.cv)} · P600 ${pctf(p.p600, 2)}${stall ? '(◉)' : ''} · 调用 ${p.calls ?? '—'}`)))
  }
  return g
}

function blendChart(): SVGElement {
  const B = D.selection.blend
  const get = (k: string): BlendRec | null => {
    const r = B[k]
    return r && typeof r === 'object' ? (r as BlendRec) : null
  }
  const rows: Array<[string, number, number | null]> = []
  for (const k of ['a_full', 'a_loco', 'b_full', 'b_loco', 'blend_loco_50']) {
    const r = get(k)
    if (r && r.tau_mean != null) rows.push([k, r.tau_mean, r.regret ?? null])
  }
  const W = 680, H = 26 * Math.max(1, rows.length) + 40, M = { l: 118, r: 16, t: 12, b: 26 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': 'blend 各面 LOCO τ 与 hidden 参照线' })
  const xs = linear([0, 1], [M.l, W - M.r])
  rows.forEach((r, i) => {
    const y = M.t + i * 26
    g.appendChild(text(M.l - 10, y + 13, `${BLEND_CN[r[0]] ?? r[0]} τ=${f2(r[1])}`, { 'text-anchor': 'end', class: 'lbl sm' }))
    g.appendChild(s('rect', { x: M.l, y, width: Math.max(1, xs(r[1]) - M.l), height: 16, rx: 3, fill: COLOR.frame, opacity: 0.82 }))
    if (r[2] != null) g.appendChild(text(xs(r[1]) + 7, y + 13, `regret ${f2(r[2], 3)}`, { class: 'lbl sm' }))
  })
  const ht = D.selection.hidden?.mean_workload_kendall_tau
  if (ht != null) {
    g.appendChild(s('line', { x1: xs(ht), x2: xs(ht), y1: M.t - 4, y2: H - M.b, stroke: COLOR.bad, 'stroke-dasharray': '4 3' }))
    g.appendChild(text(xs(ht), H - M.b + 14, `hidden τ=${f4(ht)}`, { 'text-anchor': 'middle', class: 'lbl sm' }))
  }
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  return g
}

function legend(): HTMLElement {
  const row = h('p', { class: 'note' }, '家族:')
  for (const f of ['walkthrough', 'tumor', 'microarch', 'tess']) {
    row.appendChild(h('span', { style: `display:inline-block;width:8px;height:8px;border-radius:50%;background:${FAM_COLOR[f]};margin:0 4px 0 10px;vertical-align:middle` }))
    row.appendChild(h('span', {}, FAM_CN[f]))
  }
  return row
}

function entropyScatter(): SVGElement {
  const W = 680, H = 250, M = { l: 56, r: 16, t: 14, b: 32 }
  const g = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'chart', role: 'img', 'aria-label': '类别熵:边际(bit) × 条件转移(nat),每侧一点' })
  const pts = D.sides.filter(p => p.kind_entropy != null && p.transition_entropy != null)
  if (!pts.length) return g
  const xs = linear([0, 3], [M.l, W - M.r])            // 8 类的理论上界:log2 8 = 3 bit
  const ys = linear([0, Math.log(8)], [H - M.b, M.t])  // ln 8 ≈ 2.079 nat
  g.appendChild(axisLeft(ys, M.l, v => f2(v, 1)))
  g.appendChild(axisBottom(xs, H - M.b, v => f2(v, 1)))
  for (const p of pts) {
    g.appendChild(s('circle', {
      cx: xs(p.kind_entropy as number), cy: ys(p.transition_entropy as number), r: 3.8,
      fill: FAM_COLOR[p.family] ?? COLOR.muted, opacity: 0.82,
    }, s('title', {}, `${p.job} · ${p.side}:kind ${f4(p.kind_entropy)} bit · cond ${f4(p.transition_entropy)} nat · 调用 ${p.calls ?? '—'}`)))
  }
  return g
}

export function render(host: HTMLElement): void {
  host.appendChild(h('p', { class: 'lede' },
    '2026-10-14 夜班', h('b', {}, '「轨迹特征数值实验」'), '的只读投影——对全族双 agent 跑次与单 agent 臂的',
    h('b', {}, '机械特征'), ':调用强度、掩蔽错误(exit=0 且含 Traceback)、工具类别构成、类别熵(边际/条件)、节律与缓存;另含 microarch-5 的',
    h('b', {}, '选择面审计'), '(v2)。一切数字是所收集工件的纯函数、', h('b', {}, '零模型调用'), ',由 ',
    h('code', {}, 'scripts/build_traj_features.py'), ' 投影;实验本体在 ',
    cite('harness/refs/traj-features-2026-10-14/'), '(check.py 全 PASS)。'))

  const T = D.totals
  host.appendChild(panel(`概览 · ${T.runs} 跑 / ${T.sides} 侧 / ${T.arms} 臂`,
    h('div', { class: 'stats' },
      stat(String(T.runs), `跑次(${D.families.map(f => `${FAM_CN[f.name] ?? f.name} ${f.runs}`).join(' · ')})`),
      stat(String(T.sides), '单侧轨迹(双 agent 语料)'),
      stat(T.calls.toLocaleString('en-US'), '工具调用(双跑语料)'),
      stat(`${T.masked}`, `掩蔽错误(${pctf(T.masked / Math.max(1, T.calls), 2)})`, COLOR.warn),
      stat(`${T.arms_calls}/${T.arms_masked}`, 'arm 调用/掩蔽(不变式)', COLOR.good)),
    h('p', { class: 'note strong' }, '不变式(check.py 口径,全部独立复算):'),
    h('p', { class: 'note' }, ...D.invariants.map(inv =>
      badge(`${inv.name} = ${inv.value}${inv.ok ? '' : ` ≠ ${inv.want}`}`, inv.ok ? COLOR.good : COLOR.bad))),
    note('臂 = 单 agent ATIF 轨迹(8 条,含 agent-flash-1 的 v1.7 与其余 v1.8);双跑语料 = 28 跑 54 侧,含走查族。',
      '「掩蔽错误」是启发式下界(只数 exit=0 且输出含 Traceback 的结果),不是失败率;定义与口径见 ', cite('refs/README.md'), '。')))

  const maxMask = Math.max(1, ...D.arms.map(a => a.masked ?? 0))
  host.appendChild(panel('掩蔽错误 · exit=0 ∧ Traceback',
    h('div', { class: 'scroll' }, table(
      ['家族', '跑', '侧', '调用', '掩蔽', '掩蔽率', '缓存比 中位', '双侧跨度 中位'],
      D.families.map(f => [FAM_CN[f.name] ?? f.name, String(f.runs), String(f.sides), String(f.calls),
        String(f.masked), pctf(f.masked / Math.max(1, f.calls), 2), f4(f.cache_med), wallf(f.span_med)]))),
    h('p', { class: 'note strong' }, '单 agent 臂分解(8 条 ATIF):'),
    ...D.arms.map(a => hbar(jshort(a.job), a.masked ?? 0, maxMask,
      a.masked ? COLOR.warn : COLOR.good, `${a.masked}/${a.calls} · ${a.schema ?? ''}`)),
    note('真实任务族(3.4–3.5%)远高于走查族(1/3,371 ≈ 0.03%):掩蔽错误几乎只出现在真实任务上;',
      '臂合计 ', h('b', {}, `${T.arms_masked}/${T.arms_calls} = 3.57%`), ',与 8 条臂的独立复算一致。')))

  host.appendChild(panel('逐跑特征表 · 双 agent 语料',
    h('div', { class: 'scroll' }, table(
      ['跑', '家族', '调用', '掩蔽', 'cache a/b', 'span a/b', '轮 a/b', 'NORMAL'],
      D.runs.map(r => [r.job, FAM_CN[r.family] ?? r.family, String(r.calls ?? '—'), String(r.masked ?? '—'),
        `${f4(r.cache_a)} / ${f4(r.cache_b)}`, `${wallf(r.span_a)} / ${wallf(r.span_b)}`,
        `${r.rounds_a ?? '—'} / ${r.rounds_b ?? '—'}`,
        r.normal == null ? '—' : (r.normal ? '✓' : '✗')])))))

  host.appendChild(panel('工具类别构成(双侧合计,按家族)',
    h('div', {}, ...D.families.map(f => h('div', { class: 'ratio' },
      h('div', { class: 'ratio-h' }, h('b', {}, `${FAM_CN[f.name] ?? f.name}(${f.sides} 侧 · ${f.calls} 调用)`)),
      kindStack(f.kinds)))),
    h('p', { class: 'note' }, '图例:', ...KIND_ORDER.map(k =>
      h('span', {}, h('span', { style: `display:inline-block;width:8px;height:8px;background:${KIND_COLOR[k]};margin:0 4px 0 10px;vertical-align:middle` }), `${KIND_CN[k].split(' ')[0]} `))),
    note('分类规则(实现即定义):read=read_file|list_directory;write=write_file|edit|notebook_edit;search=glob|grep_search|tool_search;',
      'run_shell_command 按命令文本细分 wait(wait_peer/pos/file|inotifywait)/recover/test(pytest|check_*.py)/exec;其余→other。',
      'exec 在各家族占比最高;test 集中在 microarch(123 次)。')))

  host.appendChild(panel('节律 · 中位间隔(速度) × CV_robust(不匀度;◉=含 >600s 间隔)',
    rhythmScatter(),
    legend(),
    note('y = 相邻调用间隔的中位(秒;0=同刻密集),x = CV_robust = 1.4826·MAD/中位(越右越不匀)。',
      '◉(玫红描边)=该侧存在 >600s 间隔。原纵轴用 P600 占比,但 42/54 侧为 0(非零最大 1.8%),零膨胀无区分度,故改作标记维度——',
      '绘出的 53 侧中 11 个 ◉,分散于 tumor/microarch/tess/走查各族;1 侧(walkthrough-7 a)中位间隔=0、CV 不可算,未入图。')))

  host.appendChild(panel('类别熵 · 边际 kind_entropy × 条件转移 transition_entropy(文档 §4.2)',
    entropyScatter(),
    legend(),
    h('div', { class: 'scroll' }, table(
      ['家族', '侧', 'kind_entropy 中位 (bit)', 'transition_entropy 中位 (nat)'],
      D.families.map(f => [FAM_CN[f.name] ?? f.name, String(f.sides),
        f4(f.kind_ent_med), f4(f.trans_ent_med)]))),
    note('kind_entropy = 类别边际熵——非首调用(c₂..cₙ)的类别分布香农熵(−Σp·log₂p;原实现名 transition_entropy,2026-10-15 按数学实际更名);',
      'transition_entropy = 条件转移熵(文档 §4.2)——N_ab 计数 + Dirichlet α=1 平滑,−Σ_a π̂_a Σ_b P̂_ab·ln P̂_ab;π̂=转移位点经验边际。',
      '两轴固定为 8 类的理论上界(log₂8=3 bit / ln8≈2.079 nat);两量同源同序列,条件版多编码「上一类→下一类」结构。')))

  const S = D.selection
  host.appendChild(panel(`microarch-5 选择面审计(v2 · 探索性 ${S.run})`,
    h('div', { class: 'stats' },
      stat(`${S.surfaces.length} 面 / ${S.candidates_total} 候选`, '选择面规模(多重比较暴露)'),
      stat((S.picked_union ?? []).join(' · '), 'LOCO 选中的配置并集'),
      stat(String(S.gap), 'local(0.75) → hidden(0.4728) τ 差'),
      S.emax_sigma05 != null ? stat(String(S.emax_sigma05), 'K=143 的 doc-公式 @σ=0.05(假设值,非测量)', COLOR.muted) : null),
    h('div', { class: 'scroll' }, table(
      ['选择面', '候选 n', 'τ_loco min/中位/max', 'regret>0', 'regret 最大'],
      S.surfaces.map(x => [x.name, String(x.n), `${f2(x.tau_min)} / ${f2(x.tau_med)} / ${f2(x.tau_max)}`,
        String(x.regret_pos ?? '—'), f2(x.regret_max, 3)]))),
    blendChart(),
    note('读法:同一 20 行验证面被 ',
      h('b', {}, `${S.candidates_total} 个候选`), '反复评分——这一暴露量正是「选择即过拟合」的度量;',
      'a 侧 LOCO τ=0.75 在 hidden 上掉到 ', h('b', {}, '0.4728'), '(差 ', h('b', {}, String(S.gap)), ')。',
      'm3/m4 的 bundle 无 analysis/ 材料,故此卡为 m5 单跑切片;τ 的 hidden 真值见 ', cite('verifier/test-stdout.txt'), '。')))

  host.appendChild(note('复跑:', h('code', {}, 'cd harness/refs/traj-features-2026-10-14 && python3 check.py'),
    '(逐字节可复现 + 不变式);数据投影:', h('code', {}, 'python3 viz/scripts/build_traj_features.py'),
    '。来源:', cite(D.meta.source), '。'))
}
