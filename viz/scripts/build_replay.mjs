// build_replay.mjs —— 轨迹重建数据生成器(后端/离线段)。
//
//   node scripts/build_replay.mjs <job-dir> --exp <id> --label "<文本>" \
//        [--a-model deepseek-flash --b-model qwen3.8-flash] [--a-effort max] [--b-effort xhigh]
//
// 输入 = 一次实验的 job 目录(walkthrough 布局):trial 目录下的
//   agent/chats/*.jsonl        —— 两条会话的无损转录(parts: thought/text/functionCall)
//   artifacts/root/wt/collect/{protocol.bundle, git-log.txt, boards/**, x/**, state.json}
// 输出 = viz/public/replay/<exp>.json(无损 bundle)+ 索引 viz/public/replay/index.json
//
// 无损原则:转录的每一行以 raw 原文 + 解析结构双份入档,每个 part、每条 toolCallResult 全文保留,
// 视图只折叠不删减;git 侧从 bundle 现场重放(host 侧 git,含每提交的 a/b/main 成员集),
// gate/board/state 原样收编。

import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..') // viz/
const OUTDIR = path.join(ROOT, 'public', 'replay')

function arg(name, dflt = null) {
  const i = process.argv.indexOf(`--${name}`)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt
}

const jobDir = process.argv[2]
if (!jobDir) { console.error('usage: build_replay.mjs <job-dir> --exp <id> --label <text>'); process.exit(1) }
const exp = arg('exp') ?? path.basename(jobDir)
const label = arg('label') ?? exp

const trial = readdirSync(jobDir).map(d => path.join(jobDir, d)).find(p => path.basename(p).startsWith('task-'))
if (!trial) { console.error(`no trial dir under ${jobDir}`); process.exit(1) }
const C = path.join(trial, 'artifacts', 'root', 'wt', 'collect')

// ---- sessions: uuid -> actor; actor -> model/effort (from the walkthrough wiring)
const actors = ['a', 'b'].map(a => {
  let uuid = null
  try { uuid = readFileSync(path.join(C, 'x', `session-${a}.uuid`), 'utf8').trim() } catch {}
  const model = arg(`${a}-model`, a === 'a' ? 'deepseek-flash' : 'qwen3.8-flash')
  const effort = arg(`${a}-effort`, a === 'a' ? 'max' : 'xhigh')
  return { actor: a, uuid, model, effort }
})
const byUuid = Object.fromEntries(actors.filter(a => a.uuid).map(a => [a.uuid, a.actor]))

function readChats() {
  const dir = path.join(C, 'chats')
  if (!existsSync(dir)) return { turns: [], systems: [], raw_lines: 0 }
  const lines = []
  for (const f of readdirSync(dir).filter(f => f.endsWith('.jsonl')).sort()) {
    for (const raw of readFileSync(path.join(dir, f), 'utf8').split('\n')) {
      const s = raw.trim(); if (!s) continue
      let d; try { d = JSON.parse(s) } catch { continue }
      lines.push({ d, s })
    }
  }
  lines.sort((x, y) => String(x.d.timestamp).localeCompare(String(y.d.timestamp)))
  const turns = []; const systems = []
  let cur = null
  for (const { d, s } of lines) {
    const ts = d.timestamp ?? null
    const actor = byUuid[d.sessionId] ?? d.sessionId?.slice(0, 8) ?? '?'
    if (d.type === 'assistant') {
      cur = { actor, t0: ts, t1: ts, uuid: d.uuid, parent: d.parentUuid ?? null,
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
      const target = cur?.calls.find(c => c.call?.id === tcr?.callId || c.call?.callId === tcr?.callId) ?? null
      const rec = { ts, uuid: d.uuid, parent: d.parentUuid ?? null, callId: tcr?.callId ?? null,
                    status: tcr?.status ?? null, executionStatus: tcr?.executionStatus ?? null,
                    resultDisplay: tcr?.resultDisplay ?? null,
                    parts: d.message?.parts ?? [], raw: s }
      if (target) target.result = rec; else if (cur) cur.results.push(rec)
      if (cur) cur.t1 = ts
    } else if (d.type === 'system') {
      systems.push({ actor, ts, uuid: d.uuid, parent: d.parentUuid ?? null, payload: d.systemPayload ?? null, raw: s })
    } else if (d.type === 'user') {
      cur = null // the one big prompt; kept verbatim (parsed + raw) below
    }
  }
  const userPrompts = lines.filter(x => x.d.type === 'user').map(({ d, s }) => ({
    actor: byUuid[d.sessionId] ?? '?', ts: d.timestamp ?? null, parts: d.message?.parts ?? null, raw: s }))
  return { turns, systems, userPrompts, raw_lines: lines.length }
}

// ---- git: replay the collected bundle on the host and keep the raw log too
function readGit() {
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
      // Branch membership per commit, so the view can rebuild "which branch tip stood where at time t":
      // rev-list of every ref lists all reachable commits; base commits (reachable from several) belong to several.
      const member = (name) => {
        const s = new Set()
        for (const ref of [`origin/${name}`, name]) {
          try { for (const x of execFileSync('git', ['-C', R, 'rev-list', ref], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split('\n')) if (x) s.add(x) } catch {}
        }
        return s
      }
      const brSets = { a: member('a'), b: member('b'), main: member('main') }
      commits = out.split('\n').filter(Boolean).map(l => {
        const [sha, parents, date, refs, ...rest] = l.split('\x1f')
        return { sha, parents: parents ? parents.split(' ').filter(Boolean) : [], date,
                 refs: refs ? refs.replace(/^[ (]+|[) ]+$/g, '') : '', subject: rest.join('\x1f'),
                 branches: ['a', 'b', 'main'].filter(n => brSets[n].has(sha)) }
      })
      tags = execFileSync('git', ['-C', R, 'tag', '--format=%(refname:short) %(objectname)'], { encoding: 'utf8' })
        .split('\n').filter(Boolean).map(l => { const [name, sha] = l.split(' '); return { name, sha } })
    } catch (e) { console.error('git replay failed:', String(e).slice(0, 200)) }
    finally { rmSync(tmp, { recursive: true, force: true }) }
  }
  return { commits, tags, raw }
}

// ---- ops: gate log / board / state
function readOps() {
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
      for (const f of readdirSync(kd).filter(f => f.endsWith('.json'))) {
        try { board.push({ kind: kind.slice(0, -1), ...JSON.parse(readFileSync(path.join(kd, f), 'utf8')) }) } catch {}
      }
    }
  }
  let state = null, rcs = null
  try { state = JSON.parse(readFileSync(path.join(C, 'state.json'), 'utf8')) } catch {}
  try { rcs = readFileSync(path.join(C, 'x', 'rcs'), 'utf8').trim() } catch {}
  return { gate, board, state, rcs }
}

const chats = readChats()
const git = readGit()
const ops = readOps()

const times = [ ...chats.turns.map(t => t.t0), ...git.commits.map(c => c.date),
                ...ops.gate.map(g => g.ts), ...ops.board.map(b => b.createdAt ? new Date(b.createdAt).toISOString() : null) ]
  .filter(Boolean).sort()
const bundle = {
  exp, label, generated_at: new Date().toISOString(),
  actors,
  sessions: chats,
  git,
  ops,
  time_range: { t0: times[0] ?? null, t1: times[times.length - 1] ?? null },
  counts: { turns: chats.turns.length, thoughts: chats.turns.reduce((n, t) => n + t.thoughts.length, 0),
            calls: chats.turns.reduce((n, t) => n + t.calls.length, 0),
            commits: git.commits.length, tags: git.tags.length,
            gate: ops.gate.length, board: ops.board.length, systems: chats.systems.length },
}
mkdirSync(OUTDIR, { recursive: true })
writeFileSync(path.join(OUTDIR, `${exp}.json`), JSON.stringify(bundle))
const idxPath = path.join(OUTDIR, 'index.json')
let idx = []
try { idx = JSON.parse(readFileSync(idxPath, 'utf8')) } catch {}
idx = idx.filter(e => e.exp !== exp)
idx.push({ exp, label, trial: path.basename(trial), counts: bundle.counts, time_range: bundle.time_range })
idx.sort((a, b) => String(a.exp).localeCompare(String(b.exp)))
writeFileSync(idxPath, JSON.stringify(idx, null, 1))
console.log('wrote', path.join(OUTDIR, `${exp}.json`), JSON.stringify(bundle.counts))
