#!/usr/bin/env node
/**
 * local2gpt/build_packet.mjs —— 把仓库里的登记册与框架摘录派生成一份给网页版 GPT 的包。
 *
 * 用法:  node --experimental-strip-types local2gpt/build_packet.mjs
 * 产物:  local2gpt/out/packet-<date>/            (不进 git)
 *        local2gpt/out/packet-<date>.tar.gz       (不进 git)
 *
 * 设计原则(与构想者约定):
 *   1. 选择是我的活:包里只有"判定下列主张所必需的材料",没有"别读清单";
 *   2. 主张用 v4.tex 原文对齐,我的稿子只作为**主张**出现,不作对齐依据;
 *   3. 20_INDEX.md 是唯一入口 —— 核验从"检索"变成"查表";
 *   4. 包由本脚本派生,不手写,以免"我告诉它的"与"语料里写的"分叉。
 */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '..')
const DATE = process.env.PKT_DATE || new Date().toLocaleDateString('sv-SE')  // YYYY-MM-DD(本机时区);可用 PKT_DATE 覆盖
const TAG = process.env.PKT_TAG || ''            // 有意义的后缀:<轮次>s<本次序号>,如 r2s1 = 第二轮第 1 次
// 命名规则:packet-<构建日>-<tag>-<内容指纹8>.tar.gz —— 名字自带(轮次, 内容身份),
// 于是同一份内容不会重传(守卫按指纹跳过),不同内容/不同轮次天然不撞名(避免 ChatGPT 追加 (n))。
const PKG = `packet-${DATE}${TAG ? '-' + TAG : ''}`
const OUTROOT = path.join(HERE, 'out')
const DEST = path.join(OUTROOT, PKG)

const { CONFLICTS, DECISIONS, DECISION_GROUPS, NARROWING, REVERSALS } = await import(path.join(ROOT, 'viz/src/data/corpus.ts'))
const { CORPUS_COVERAGE, COVERAGE_SUMMARY: S } = await import(path.join(ROOT, 'viz/src/data/coverage.ts'))
const { LIB_TOTALS, RECOVERED, BLOCKED, MECHANISMS, LADDER, LIB_NOTES } = await import(path.join(ROOT, 'viz/src/data/library.ts'))

/* ---------- helpers ---------- */
const cell = (v) => String(v ?? '—').replace(/\|/g, '\\|').replace(/\n+/g, ' ')
const lines = (s) => s.split('\n').length
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')
const HEAD = execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: ROOT }).toString().trim()

const V4 = path.join(ROOT, 'related_files/research_state_control_review_v4.tex')
const v4lines = fs.readFileSync(V4, 'utf8').split('\n')
const excerpt = (a, b) => `### \`v4.tex:${a}${b > a ? '-' + b : ''}\`\n\n\`\`\`\n${v4lines.slice(a - 1, b).join('\n')}\n\`\`\`\n`

const EXCERPT_RANGES = [[37, 37], [318, 322], [357, 365], [463, 463], [469, 469], [489, 489], [492, 492], [602, 602], [814, 825], [928, 928], [1225, 1267], [1546, 1565], [1585, 1601]]

const CLAIM_COUNT = [...fs.readFileSync(path.join(HERE, 'packet_source.md'), 'utf8').matchAll(/^\| C\d+ \|/gm)].length
const nopen = DECISIONS.filter((d) => d.status === 'open').length
const readPct = ((S.corpusLinesReadExclTranscript / S.corpusLinesExclTranscript) * 100).toFixed(1)

const NARROW = Object.entries(NARROWING).map(([k, v]) => {
  const got = v.measured ?? v.instrumented ?? v.rows ?? '?'
  const what = v.measuredName ?? v.row ?? (Array.isArray(v.names) ? v.names.join(' / ') : '')
  return `| ${cell(k)} | **${got} / ${v.total ?? '?'}** | ${cell(what)} | ${cell(v.cite)} |`
}).join('\n')

const CORPUS_STATS = [
  `- 语料(related_files/):**${S.corpusFiles}** 个跟踪文本 / **${S.corpusLines}** 行(含我生成的转录 ${S.corpusLines - S.corpusLinesExclTranscript} 行)`,
  `- 不含转录:**${S.corpusLinesExclTranscript}** 行,其中逐行读过 **${S.corpusLinesReadExclTranscript}** 行 = ${readPct}%`,
  `- a0/ 顶层报告:**${S.a0TopMd}** 份 / ${S.a0TopMdLines} 行,读过 ${S.a0LinesRead} 行`,
  `- 仓库跟踪文件总数:${S.repoTrackedTotal}(a0/ 占 ${S.a0TrackedTotal})`,
].join('\n')

const DEC_TABLE = ['| id | 组 | 状态 | 问题(含判据) | 我依赖的证据 | 我的建议 |', '|---|---|---|---|---|---|',
  ...DECISIONS.map((d) => `| ${d.id} | ${cell(DECISION_GROUPS[d.group])} | ${d.status} | ${cell(d.question)} | ${cell(d.cite)} | ${cell(d.recommendation)} |`)].join('\n')

const CONF = CONFLICTS.map((c) => [
  `### ${c.id} · ${c.title}  \`(${c.kind}, 证据 ${c.evidence})\``,
  `- **左 · ${cell(c.left.who)}**(${cell(c.left.cite)}):「${cell(c.left.quote)}」`,
  `- **右 · ${cell(c.right.who)}**(${cell(c.right.cite)}):「${cell(c.right.quote)}」`,
  `- 我的后果判断:${cell(c.consequence)}`,
].join('\n')).join('\n\n')

const REV = REVERSALS.map((r) => [
  `### ${r.round}  \`${r.date} · ${cell(r.source)} · 证据 ${r.evidence}\``,
  ...r.items.map((i) => `- **was** ${cell(i.was)}\n  - **now** ${cell(i.now)}\n  - 出处 ${cell(i.cite)}`),
].join('\n')).join('\n\n')

const COV_TABLE = ['| 路径 | 行 | 状态 | 已读行 | 备注 |', '|---|---|---|---|---|',
  ...CORPUS_COVERAGE.map((r) => `| \`${cell(r.path)}\` | ${r.lines} | ${r.status} | ${r.linesRead} | ${cell(r.note)} |`)].join('\n')

const LIB_BLOCK = [
  `\`chatgpt.com/library\` 共 **${LIB_TOTALS.entries}** 条;按名比对后本地没有 **${LIB_TOTALS.unmatched}** 条;`,
  `本轮取回并入库 **${LIB_TOTALS.recovered}** 份;取不到或未取 **${LIB_TOTALS.blocked}** 条` +
  `(原因已查明 ${BLOCKED.filter((b) => b.status === 'reason').length} / 仅记录现象 ${BLOCKED.filter((b) => b.status === 'symptom').length} / 未取 ${BLOCKED.filter((b) => b.status === 'not-taken').length} / 未尝试 ${BLOCKED.filter((b) => b.status === 'not-attempted').length});`,
  `名字呈归档形态 **${LIB_TOTALS.archives}** 条(按规则不入 git);约 **${LIB_TOTALS.other}** 条属其他项目。\n`,
  '三条取回通道与各自的陷阱:\n',
  ...MECHANISMS.map((m) => `- **${m.viewer}** —— 取法:${m.route};陷阱:${m.trap}`),
  '\nB 线阶梯(取回件)+ 校准点:\n',
  ...LADDER.map((l) => `- ${l.v}:${l.lines} 行 —— ${l.note}`),
  `\n_LIB_NOTES_ 下载通道已坏:${LIB_NOTES.downloadDead}`,
].join('\n')

const BLOCK_STATUS = { reason: '原因已查明', symptom: '仅记录现象(根因未查)', 'not-taken': '未取(与 zip 重复)', 'not-attempted': '未尝试(原因未查)' }
const BLOCK_TABLE = ['| 状态 | 条目 | 说明 |', '|---|---|---|', ...BLOCKED.map((b) => `| ${BLOCK_STATUS[b.status]} | \`${cell(b.name)}\` | ${cell(b.why)} |`)].join('\n')

const CLAIM_INDEX = [
  ['C1–C9', '`1_we_are_here/03_FRAMING.md`(原文)+ `3_verify/20_INDEX.md` 本节'],
  ['C10–C15', '`4_full_text/1006/memory_substrate_and_partition.typ` §2–§6'],
  ['C16, C19', '`2_claims_to_attack/13_REVERSALS.md`;`3_verify/22_PROVENANCE.md`'],
  ['C17', '`2_claims_to_attack/12_CONFLICTS.md` → search-vs-library'],
  ['C18', '`2_claims_to_attack/13_REVERSALS.md` → 项目对话计数'],
  ['C20', '`4_full_text/1006/credit_meter_calibration.typ`'],
  ['D1–D33', '`2_claims_to_attack/11_DECISIONS.md`'],
  ['全域背景', '`4_full_text/registers/*.ts`(机器可读的登记册源文件)'],
].map(([a, b]) => `| ${a} | ${b} |`).join('\n')

const SUBS = {
  '{{HEAD}}': HEAD, '{{PKT_DATE}}': DATE,
  '{{NARROWING}}': ['| 收窄项 | 已测 / 总数 | 已测的是哪个 | 出处 |', '|---|---|---|---|', NARROW].join('\n'),
  '{{CORPUS_STATS}}': CORPUS_STATS,
  '{{N_CLAIMS}}': String(CLAIM_COUNT), '{{N_DEC}}': String(DECISIONS.length), '{{N_OPEN}}': String(nopen),
  '{{N_CONF}}': String(CONFLICTS.length), '{{N_REV}}': String(REVERSALS.length),
  '{{N_CORPUS_FILES}}': String(S.corpusFiles), '{{N_CORPUS_LINES}}': String(S.corpusLines),
  '{{N_TRANSCRIPT}}': String(S.corpusLines - S.corpusLinesExclTranscript),
  '{{N_EXCL}}': String(S.corpusLinesExclTranscript), '{{N_READ}}': String(S.corpusLinesReadExclTranscript),
  '{{READ_PCT}}': readPct, '{{N_A0}}': String(S.a0TopMd), '{{N_A0_LINES}}': String(S.a0TopMdLines), '{{N_A0_READ}}': String(S.a0LinesRead),
  '{{EXCERPTS}}': EXCERPT_RANGES.map(([a, b]) => excerpt(a, b)).join('\n'),
  '{{DECISIONS_TABLE}}': DEC_TABLE, '{{CONFLICTS}}': CONF, '{{REVERSALS}}': REV,
  '{{COVERAGE_TABLE}}': COV_TABLE, '{{LIBRARY_BLOCK}}': LIB_BLOCK, '{{BLOCKED_TABLE}}': BLOCK_TABLE,
  '{{CLAIM_INDEX}}': CLAIM_INDEX, '{{MANIFEST_TABLE}}': '@@MANIFEST@@',
}

/* ---------- 1) 拆模板 ---------- */
const src = fs.readFileSync(path.join(HERE, 'packet_source.md'), 'utf8')
const parts = [...src.matchAll(/^@@@ FILE: (.+?) @@@$/gm)]
if (!parts.length) throw new Error('packet_source.md 里没有 @@@ FILE: ... @@@ 标记')
const files = new Map()
parts.forEach((m, i) => {
  const start = m.index + m[0].length
  const end = i + 1 < parts.length ? parts[i + 1].index : src.length
  let body = src.slice(start, end).replace(/^\n+/, '').replace(/\n+$/, '') + '\n'
  for (const [k, v] of Object.entries(SUBS)) body = body.split(k).join(v)
  files.set(m[1], body)
})

/* ---------- 2) 写包 ---------- */
fs.rmSync(DEST, { recursive: true, force: true })
fs.mkdirSync(DEST, { recursive: true })
for (const [name, body] of files) {
  const f = path.join(DEST, name)
  fs.mkdirSync(path.dirname(f), { recursive: true })
  fs.writeFileSync(f, body, 'utf8')
}

/* ---------- 3) 4_full_text ---------- */
const copyDir = (from, to, filter) => {
  fs.mkdirSync(to, { recursive: true })
  for (const f of fs.readdirSync(from).filter(filter).sort()) {
    fs.copyFileSync(path.join(from, f), path.join(to, f))
  }
}
copyDir(path.join(ROOT, 'related_files/1006'), path.join(DEST, '4_full_text/1006'), (f) => f.endsWith('.typ'))
copyDir(path.join(ROOT, 'viz/src/data'), path.join(DEST, '4_full_text/registers'), (f) => f.endsWith('.ts'))
fs.copyFileSync(path.join(HERE, 'build_packet.mjs'), path.join(DEST, '3_verify/25_build_packet.mjs'))

/* ---------- 4) 第二遍:清单表 + sha256 ---------- */
const walk = (d, base = d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => {
  const p = path.join(d, e.name)
  return e.isDirectory() ? walk(p, base) : [path.relative(base, p)]
})
const all = walk(DEST).filter((f) => f !== 'SHA256SUMS').sort()
const manifest = ['| 文件 | 字节 | 行 |', '|---|---|---|',
  ...all.filter((f) => f !== '3_verify/20_INDEX.md').map((f) => `| \`${f}\` | ${fs.statSync(path.join(DEST, f)).size} | ${lines(fs.readFileSync(path.join(DEST, f), 'utf8'))} |`)].join('\n')

const idx = path.join(DEST, '3_verify/20_INDEX.md')
fs.writeFileSync(idx, fs.readFileSync(idx, 'utf8').split('@@MANIFEST@@').join(manifest), 'utf8')
fs.writeFileSync(path.join(DEST, 'SHA256SUMS'), walk(DEST).filter((f) => f !== 'SHA256SUMS').sort().map((f) => `${sha(path.join(DEST, f))}  ${f}`).join('\n') + '\n')

/* ---------- 5) 打包 ---------- */
const tarTmp = path.join(OUTROOT, `${PKG}.tar.gz`)
if (fs.existsSync(tarTmp)) fs.rmSync(tarTmp)
execFileSync('tar', ['-czf', tarTmp, '-C', OUTROOT, PKG])
// 内容指纹:对包内 SHA256SUMS 取哈希 —— tar 字节含 mtime,不能当内容标识
const fp = crypto.createHash('sha256').update(fs.readFileSync(path.join(DEST, 'SHA256SUMS'))).digest('hex').slice(0, 8)
const tar = path.join(OUTROOT, `${PKG}-${fp}.tar.gz`)
if (fs.existsSync(tar)) fs.rmSync(tar)
fs.renameSync(tarTmp, tar)
fs.writeFileSync(path.join(OUTROOT, '.latest-packet'), path.basename(tar) + '\n', 'utf8')
fs.writeFileSync(path.join(OUTROOT, '.latest-fingerprint'), fp + '\n', 'utf8')

/* ---------- 6) 报告 ---------- */
const kb = (n) => (n / 1024).toFixed(1) + ' KB'
console.log(`包已生成:${path.relative(ROOT, DEST)}`)
for (const f of all) console.log(`  ${kb(fs.statSync(path.join(DEST, f)).size).padStart(9)}  ${String(lines(fs.readFileSync(path.join(DEST, f), 'utf8'))).padStart(5)} 行  ${f}`)
console.log(`\n压缩件:${path.relative(ROOT, tar)}  ${kb(fs.statSync(tar).size)}  内容指纹(manifest sha8)= ${fp}`)
console.log(`HEAD=${HEAD} · 决策 ${DECISIONS.length}(待决 ${nopen}) · 冲突 ${CONFLICTS.length} · 反转 ${REVERSALS.length} · 语料 ${S.corpusFiles} 文件`)
