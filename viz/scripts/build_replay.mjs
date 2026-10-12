// build_replay.mjs v2 —— 轨迹重建数据生成器(可复用入口)。
//
//   node scripts/build_replay.mjs <source> [<source> ...] --exp <id> --label "<text>" \
//        [--a-model deepseek-flash] [--b-model qwen3.8-flash] [--a-effort max] [--b-effort xhigh]
//
// source 三种形态自动判定:
//   1) harbor job 目录(内含 task-*__* 实验目录) —— 完整模式:转录 + git + gate/board/state
//   2) 轨迹文件目录(内含 chats/*.jsonl 或 *.jsonl) —— chats 模式:仅转录;actor 由来源目录名推导
//      (路径含 wt-a → a;wt-b → b;含 spike → s;否则 s)
//   3) 单个 .jsonl 轨迹文件 —— chats 模式(同上)
//
// 输出 = viz/public/replay/<exp>.json(无损 bundle + stats)+ 索引 viz/public/replay/index.json
// stats = 时间与成本统计:每 actor 的轮数/时长分布/tokens 分布(prompt-cache-out)/映射成本
//         —— 口径与 walkthrough/tasks/walkthrough/metrics.py 同源(费率卡 2026-10-10):
//         A(deepseek-flash) USD/M: uncached .15 · cache .003 · out .60,峰值(周一至五 01-04/06-10 UTC)×2
//         B(qwen3.8-flash)  CNY/M: uncached .8 · cache .1 · out 2.7;credits = ¥×200 @k=1(亦 ×144 @k=0.72)
//         out = candidates + thoughts;uncached = max(prompt - cache, 0)
//
// 无损原则:转录的每一行以 raw 原文 + 解析结构双份入档;git 侧从 bundle 现场重放;
// gate/board/state 原样收编(仅 job 模式)。

import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync, existsSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..') // viz/
const OUTDIR = path.join(ROOT, 'public', 'replay')

const argv = process.argv.slice(2)
if (!argv.length || argv.includes('--help')) {
  console.log(`usage: build_replay.mjs <source> [<source> ...] --exp <id> --label "<text>" [--a-model ..] [--b-model ..] [--a-effort ..] [--b-effort ..]

  source = harbor job 目录 | 轨迹文件目录(chats/*.jsonl) | 单个 .jsonl
  例:
    node scripts/build_replay.mjs /home/ebt/harbor-runs/jobs/agent/tumor-2 --exp tumor2 --label "tumor-2"
    node scripts/build_replay.mjs /path/chats-a /path/chats-b --exp a2afusion --label "A2A 融合"`)
  process.exit(argv.length ? 0 : 1)
}
const flags = {}
const sources = []
for (let i = 0; i < argv.length; i++) {
  const a = argv[i]
  if (a.startsWith('--')) { flags[a.slice(2)] = argv[i + 1]; i++ } else sources.push(a)
}
const arg = (n, d) => (n in flags ? flags[n] : d)
const exp = arg('exp') ?? (sources.length ? path.basename(sources[0]) : 'unknown')
const label = arg('label') ?? exp

// ---------- source 模式判定 ----------
const isHarborJob = (p) => {
  try { return existsSync(p) && statSync(p).isDirectory() && readdirSync(p).some((d) => d.startsWith('task-')) } catch { return false }
}
const harborSrc = sources.find(isHarborJob) ?? null
const mode = harborSrc ? 'harbor' : 'chats'

// ---------- 转录解析(共享) ----------
function readTranscriptFiles(files) {
  const lines = []
  for (const { file, actor } of files) {
    for (const raw of readFileSync(file, 'utf8').split('\n')) {
      const s = raw.trim(); if (!s) continue
      let d; try { d = JSON.parse(s) } catch { continue }
      lines.push({ d, s, actor })
    }
  }
  lines.sort((x, y) => String(x.d.timestamp).localeCompare(String(y.d.timestamp)))
  const actorOf = (rec) => (typeof rec.actor === 'function' ? rec.actor(rec.d) : rec.actor)
  const turns = []; const systems = []
  let cur = null
  for (const { d, s, actor } of lines) {
    const ts = d.timestamp ?? null
    if (d.type === 'assistant') {
      cur = { actor: actorOf({ d, actor }), t0: ts, t1: ts, uuid: d.uuid, parent: d.parentUuid ?? null,
              model: d.model ?? null, usage: d.usageMetadata ?? null,
              parts: d.message?.parts ?? [], calls: [], texts: [], thoughts: [], results: [], raw: s }
      for (const p of cur.parts) {
        if (p?.thought) cur.thoughts.push(p.text ?? '')
        else if (typeof p?.text === 'string') cur.texts.push(p.text)
        else if (p?.functionCall) cur.calls.push({ call: p.functionCall, result: null })
      }
      turns.push(cur)
    } else if (d.type === 'tool_result') {
      const tcr = d.toolCallResult ?? null
      const target = cur?.calls.find((c) => c.call?.id === tcr?.callId || c.call?.callId === tcr?.callId) ?? null
      const rec = { ts, uuid: d.uuid, parent: d.parentUuid ?? null, callId: tcr?.callId ?? null,
                    status: tcr?.status ?? null, executionStatus: tcr?.executionStatus ?? null,
                    resultDisplay: tcr?.resultDisplay ?? null,
                    parts: d.message?.parts ?? [], raw: s }
      if (target) target.result = rec; else if (cur) cur.results.push(rec)
      if (cur) cur.t1 = ts
    } else if (d.type === 'system') {
      systems.push({ actor: actorOf({ d, actor }), ts, uuid: d.uuid, parent: d.parentUuid ?? null, payload: d.systemPayload ?? null, raw: s })
    } else if (d.type === 'user') {
      cur = null // the one big prompt; kept verbatim (parsed + raw) below
    }
  }
  const userPrompts = lines.filter((x) => x.d.type === 'user').map(({ d, s, actor }) => ({
    actor: actorOf({ d, actor }), ts: d.timestamp ?? null, parts: d.message?.parts ?? null, raw: s }))
  return { turns, systems, userPrompts, raw_lines: lines.length }
}

// ---------- job 模式:转录 + git + ops ----------
function harborSessions(C, byUuid) {
  const dir = path.join(C, 'chats')
  const files = []
  if (existsSync(dir)) {
    for (const f of readdirSync(dir).filter((f) => f.endsWith('.jsonl') && !f.endsWith('.ledger.jsonl')).sort()) {
      files.push({ file: path.join(dir, f), actor: (d) => byUuid[d.sessionId] ?? d.sessionId?.slice(0, 8) ?? '?' })
    }
  }
  return readTranscriptFiles(files)
}
function readGit(C) {
  const bundle = path.join(C, 'protocol.bundle')
  let commits = [], tags = [], raw = ''
  try { raw = readFileSync(path.join(C, 'git-log.txt'), 'utf8') } catch {}
  if (existsSync(bundle)) {
    const tmp = mkdtempSync(path.join(tmpdir(), 'wtreplay-'))
    try {
      execFileSync('git', ['clone', '-q', bundle, path.join(tmp, 'r')])
      const R = path.join(tmp, 'r')
      const fmt = '%H%x1f%P%x1f%ad%x1f%d%x1f%s'
      const out = execFileSync('git', ['-C', R, 'log', '--all', '--date=iso-strict', `--format=${fmt}`], { encoding: 'utf8' })
      const member = (name) => {
        const s = new Set()
        for (const ref of [`origin/${name}`, name]) {
          try { for (const x of execFileSync('git', ['-C', R, 'rev-list', ref], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split('\n')) if (x) s.add(x) } catch {}
        }
        return s
      }
      const brSets = { a: member('a'), b: member('b'), main: member('main') }
      commits = out.split('\n').filter(Boolean).map((l) => {
        const [sha, parents, date, refs, ...rest] = l.split('\x1f')
        return { sha, parents: parents ? parents.split(' ').filter(Boolean) : [], date,
                 refs: refs ? refs.replace(/^[ (]+|[) ]+$/g, '') : '', subject: rest.join('\x1f'),
                 branches: ['a', 'b', 'main'].filter((n) => brSets[n].has(sha)) }
      })
      tags = execFileSync('git', ['-C', R, 'tag', '--format=%(refname:short) %(objectname)'], { encoding: 'utf8' })
        .split('\n').filter(Boolean).map((l) => { const [name, sha] = l.split(' '); return { name, sha } })
    } catch (e) { console.error('git replay failed:', String(e).slice(0, 200)) }
    finally { rmSync(tmp, { recursive: true, force: true }) }
  }
  return { commits, tags, raw }
}
function readOps(C) {
  const gate = []
  try {
    const day = (() => { try { return JSON.parse(readFileSync(path.join(C, 'state.json'), 'utf8')).finished_at.slice(0, 10) } catch { return '1970-01-01' } })()
    for (const l of readFileSync(path.join(C, 'x', 'gate.log'), 'utf8').split('\n')) {
      const m = l.match(/^(\d\d:\d\d:\d\d)\s+(.*)$/)
      if (m) gate.push({ ts: `${day}T${m[1]}Z`, text: m[2] })
    }
  } catch {}
  const board = []
  const bdir = path.join(C, 'boards')
  if (existsSync(bdir)) {
    for (const kind of ['tasks', 'asks']) {
      const kd = path.join(bdir, kind)
      if (!existsSync(kd)) continue
      for (const f of readdirSync(kd).filter((f) => f.endsWith('.json'))) {
        try { board.push({ kind: kind.slice(0, -1), ...JSON.parse(readFileSync(path.join(kd, f), 'utf8')) }) } catch {}
      }
    }
  }
  let state = null, rcs = null
  try { state = JSON.parse(readFileSync(path.join(C, 'state.json'), 'utf8')) } catch {}
  try { rcs = readFileSync(path.join(C, 'x', 'rcs'), 'utf8').trim() } catch {}
  return { gate, board, state, rcs }
}

// ---------- chats 模式:轨迹文件目录 / 单文件 ----------
function tagOf(p) {
  const segs = p.split(path.sep)
  for (const s of segs) { const m = s.match(/wt-([ab])$/); if (m) return m[1] }
  if (segs.some((s) => /spike/i.test(s))) return 's'
  return 's'
}
function collectJsonl(src) {
  const out = []
  const st = statSync(src)
  if (st.isFile()) {
    if (src.endsWith('.jsonl') && !src.endsWith('.ledger.jsonl')) out.push({ file: src, tag: tagOf(src) })
    return out
  }
  const walk = (d) => {
    for (const f of readdirSync(d).sort()) {
      const p = path.join(d, f)
      if (statSync(p).isDirectory()) walk(p)
      else if (f.endsWith('.jsonl') && !f.endsWith('.ledger.jsonl')) out.push({ file: p, tag: tagOf(p) })
    }
  }
  walk(src)
  return out
}

// ---------- stats:时间与成本(口径同 metrics.py) ----------
const MAPPING = {
  version: 'rate-cards-2026-10-10 (口径与 walkthrough/tasks/walkthrough/metrics.py 同源)',
  A: 'deepseek-flash USD/M: uncached 0.15 · cache 0.003 · out 0.60;峰值(周一至五 01-04/06-10 UTC)×2',
  B: 'qwen3.8-flash CNY/M: uncached 0.8 · cache 0.1 · out 2.7',
  credits: 'credits = ¥×200 @k=1(亦 ×144 @k=0.72);实测有效 k≈0.50(2026-10-12 计费窗标定)',
  out: 'out = candidates + thoughts;uncached = max(prompt - cache, 0)',
}
const isPeak = (iso) => {
  if (!iso) return false
  const t = new Date(iso)
  const h = t.getUTCHours(); const wd = t.getUTCDay()
  return wd >= 1 && wd <= 5 && ((h >= 1 && h < 4) || (h >= 6 && h < 10))
}
function computeStats(turns, actorsMeta) {
  const byActor = {}
  for (const t of turns) {
    const e = (byActor[t.actor] ??= { turns: 0, durations_ms: [], prompt: 0, cached: 0, cand: 0, th: 0, models: new Set(), t0: null, t1: null })
    e.turns++
    if (t.t0 && t.t1) { const d = Date.parse(t.t1) - Date.parse(t.t0); if (!Number.isNaN(d)) e.durations_ms.push(Math.max(d, 0)) }
    const u = t.usage || {}
    e.prompt += u.promptTokenCount || 0
    e.cached += u.cachedContentTokenCount || 0
    e.cand += u.candidatesTokenCount || 0
    e.th += u.thoughtsTokenCount || 0
    if (t.model) e.models.add(t.model)
    if (t.t0 && (!e.t0 || t.t0 < e.t0)) e.t0 = t.t0
    if (t.t1 && (!e.t1 || t.t1 > e.t1)) e.t1 = t.t1
  }
  const actors = {}
  for (const [a, e] of Object.entries(byActor)) {
    const uncached = Math.max(e.prompt - e.cached, 0)
    const outTok = e.cand + e.th
    const meta = (actorsMeta || []).find((m) => m.actor === a)
    const model = [...e.models][0] || meta?.model || null
    let cost = null
    if (model && /deepseek/i.test(model)) {
      const peak = isPeak(e.t0); const rate = peak ? 2 : 1
      cost = { scheme: 'A-deepseek', currency: 'USD', peak, rate, usd: (uncached * 0.15 + e.cached * 0.003 + outTok * 0.60) * rate / 1e6 }
    } else if (model && /qwen3\.8/i.test(model)) {
      const cny = (uncached * 0.8 + e.cached * 0.1 + outTok * 2.7) / 1e6
      cost = { scheme: 'B-qwen3.8', currency: 'CNY', cny, cr_k1: cny * 200, cr_k072: cny * 144 }
    }
    actors[a] = {
      turns: e.turns, model, models: [...e.models],
      span_s: e.t0 && e.t1 ? Math.round((Date.parse(e.t1) - Date.parse(e.t0)) / 1000) : null,
      durations_ms: e.durations_ms,
      tokens: { prompt: e.prompt, cached: e.cached, uncached, out: outTok, out_visible: e.cand, out_thoughts: e.th, total: e.prompt + outTok },
      cost,
    }
  }
  return { actors, mapping: MAPPING }
}

// ---------- 组装 ----------
let sessions, git, ops, actors
if (mode === 'harbor') {
  const jobDir = harborSrc
  const trial = readdirSync(jobDir).map((d) => path.join(jobDir, d)).find((p) => path.basename(p).startsWith('task-'))
  if (!trial) { console.error(`no trial dir under ${jobDir}`); process.exit(1) }
  const C = path.join(trial, 'artifacts', 'root', 'wt', 'collect')
  actors = ['a', 'b'].map((a) => {
    let uuid = null
    try { uuid = readFileSync(path.join(C, 'x', `session-${a}.uuid`), 'utf8').trim() } catch {}
    const model = arg(`${a}-model`, a === 'a' ? 'deepseek-flash' : 'qwen3.8-flash')
    const effort = arg(`${a}-effort`, a === 'a' ? 'max' : 'xhigh')
    return { actor: a, uuid, model, effort }
  })
  const byUuid = Object.fromEntries(actors.filter((a) => a.uuid).map((a) => [a.uuid, a.actor]))
  sessions = harborSessions(C, byUuid)
  git = readGit(C)
  ops = readOps(C)
} else {
  const files = sources.flatMap(collectJsonl)
  if (!files.length) { console.error(`no .jsonl trajectory files under: ${sources.join(', ')}`); process.exit(1) }
  const tags = [...new Set(files.map((f) => f.tag))]
  actors = tags.map((t) => ({ actor: t, uuid: null, model: arg(`${t}-model`, null), effort: null }))
  sessions = readTranscriptFiles(files.map((f) => ({ file: f.file, actor: f.tag, tag: f.tag })))
  git = { commits: [], tags: [], raw: '' }
  ops = { gate: [], board: [], state: null, rcs: null }
}
const stats = computeStats(sessions.turns, actors)

const times = [ ...sessions.turns.map((t) => t.t0), ...git.commits.map((c) => c.date),
                ...ops.gate.map((g) => g.ts), ...ops.board.map((b) => b.createdAt ? new Date(b.createdAt).toISOString() : null) ]
  .filter(Boolean).sort()
const bundle = {
  exp, label, generated_at: new Date().toISOString(),
  mode, sources,
  actors,
  sessions,
  git,
  ops,
  stats,
  time_range: { t0: times[0] ?? null, t1: times[times.length - 1] ?? null },
  counts: { turns: sessions.turns.length, thoughts: sessions.turns.reduce((n, t) => n + t.thoughts.length, 0),
            calls: sessions.turns.reduce((n, t) => n + t.calls.length, 0),
            commits: git.commits.length, tags: git.tags.length,
            gate: ops.gate.length, board: ops.board.length, systems: sessions.systems.length },
}
mkdirSync(OUTDIR, { recursive: true })
writeFileSync(path.join(OUTDIR, `${exp}.json`), JSON.stringify(bundle))
const idxPath = path.join(OUTDIR, 'index.json')
let idx = []
try { idx = JSON.parse(readFileSync(idxPath, 'utf8')) } catch {}
idx = idx.filter((e) => e.exp !== exp)
const tokens_total = Object.values(stats.actors).reduce((n, a) => n + a.tokens.total, 0)
const costs = {}
for (const [a, st] of Object.entries(stats.actors)) if (st.cost) costs[a] = st.cost
idx.push({ exp, label, trial: mode === 'harbor' ? path.basename(harborSrc) : sources.map((s) => path.basename(s)).join('+'), counts: bundle.counts, time_range: bundle.time_range, mode, tokens_total, costs })
idx.sort((a, b) => String(a.exp).localeCompare(String(b.exp)))
writeFileSync(idxPath, JSON.stringify(idx, null, 1))
console.log('wrote', path.join(OUTDIR, `${exp}.json`), JSON.stringify(bundle.counts), 'tokens_total=' + tokens_total, JSON.stringify(costs).slice(0, 200))
