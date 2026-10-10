// replay/data.ts —— 轨迹重建的数据契约与加载器。
//
// bundle 由 viz/scripts/build_replay.mjs 生成(public/replay/<exp>.json;索引 index.json)。
// 无损口径:每个转录行存 raw 原文 + 解析结构双份;视图只折叠,不删减。时间戳一律 ISO-8601 UTC。

export interface ReplayResult {
  ts: string | null
  uuid?: string
  parent?: string | null
  callId: string | null
  status: string | null
  executionStatus: string | null
  resultDisplay: { type?: string; exitCode?: number | null; output?: string; [k: string]: unknown } | null
  parts: unknown[]
  raw?: string
}

export interface ReplayFunctionCall { id?: string; callId?: string; name?: string; args?: Record<string, unknown> }

export interface ReplayCall { call: ReplayFunctionCall; result: ReplayResult | null }

export interface ReplayUsage {
  promptTokenCount?: number
  candidatesTokenCount?: number
  thoughtsTokenCount?: number
  cachedContentTokenCount?: number
  totalTokenCount?: number
}

export interface ReplayPart { thought?: boolean; text?: string; functionCall?: ReplayFunctionCall }

export interface ReplayTurn {
  actor: string
  t0: string | null
  t1: string | null
  uuid?: string
  parent?: string | null
  model: string | null
  usage: ReplayUsage | null
  parts: ReplayPart[]
  calls: ReplayCall[]
  texts: string[]
  thoughts: string[]
  results: ReplayResult[]
  raw?: string
}

export interface ReplaySystem { actor: string; ts: string | null; uuid?: string; parent?: string | null; payload: unknown; raw?: string }

export interface ReplayUserPrompt { actor: string; ts: string | null; parts: { text?: string }[] | null; raw?: string }

export interface ReplayCommit { sha: string; parents: string[]; date: string; refs: string; subject: string; branches: string[] }

export interface ReplayTag { name: string; sha: string }

export interface ReplayGate { ts: string; text: string }

export interface ReplayBoardItem { kind: string; id?: string; subject?: string; createdBy?: string; status?: string; createdAt?: number; notes?: unknown[] }

export interface ReplayBundle {
  exp: string
  label: string
  generated_at: string
  actors: { actor: string; uuid: string | null; model: string; effort: string }[]
  sessions: { turns: ReplayTurn[]; systems: ReplaySystem[]; userPrompts?: ReplayUserPrompt[]; raw_lines?: number }
  git: { commits: ReplayCommit[]; tags: ReplayTag[]; raw: string }
  ops: { gate: ReplayGate[]; board: ReplayBoardItem[]; state: Record<string, unknown> | null; rcs: string | null }
  time_range: { t0: string | null; t1: string | null }
  counts: { turns: number; thoughts: number; calls: number; commits: number; tags: number; gate: number; board: number; systems: number }
}

export interface ReplayIndexEntry { exp: string; label: string; trial: string; counts: ReplayBundle['counts']; time_range: { t0: string | null; t1: string | null } }

const indexCache: { v: ReplayIndexEntry[] | null } = { v: null }
const bundleCache = new Map<string, ReplayBundle>()

export async function loadIndex(): Promise<ReplayIndexEntry[]> {
  if (indexCache.v) return indexCache.v
  const r = await fetch('replay/index.json')
  if (!r.ok) throw new Error(`HTTP ${r.status} · replay/index.json`)
  indexCache.v = await r.json() as ReplayIndexEntry[]
  return indexCache.v
}

export async function loadBundle(exp: string): Promise<ReplayBundle> {
  const hit = bundleCache.get(exp)
  if (hit) return hit
  const r = await fetch(`replay/${exp}.json`)
  if (!r.ok) throw new Error(`HTTP ${r.status} · replay/${exp}.json`)
  const b = await r.json() as ReplayBundle
  bundleCache.set(exp, b)
  return b
}

// ---- 时间与格式工具(页面统一显示 UTC,与采集记录一致)

export function ms(v: string | null | undefined): number {
  return v ? Date.parse(v) : NaN
}

export function hhmmss(iso: string | null | undefined, sub = false): string {
  const t = ms(iso)
  if (Number.isNaN(t)) return '—'
  const d = new Date(t)
  const base = [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()].map(x => String(x).padStart(2, '0')).join(':')
  return sub ? `${base}.${String(d.getUTCMilliseconds()).padStart(3, '0')}` : base
}

export function dur(a: string | null | undefined, b: string | null | undefined): string {
  const d = ms(b) - ms(a)
  if (Number.isNaN(d)) return '—'
  const ad = Math.abs(d)
  if (ad < 1000) return `${ad}ms`
  if (ad < 60000) return `${(ad / 1000).toFixed(1)}s`
  const m = Math.floor(ad / 60000)
  const s = Math.round((ad % 60000) / 1000)
  return `${m}m${s ? `${s}s` : ''}`
}

export function fmtBytes(n: number): string {
  return n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(2)} MB`
}

export function actorMeta(b: ReplayBundle, actor: string): { model: string; effort: string } {
  const a = b.actors.find(x => x.actor === actor)
  return { model: a?.model ?? '?', effort: a?.effort ?? '?' }
}

export function sha7(sha: string): string {
  return sha.slice(0, 7)
}

/** 提交的时光序:直接用 git log 的序列反转。
 *  commit 时间戳只有秒精度,同秒提交的真实先后只由 log 的拓扑序决定(父先于子);
 *  按日期重排会破坏它,故此处只反转、不重排序。 */
export function commitsByDate(b: ReplayBundle): ReplayCommit[] {
  return [...b.git.commits].reverse()
}

/** 系统事件 → 归属轮:同会话最早一轮 t0 ≥ 事件时间;越界则归该会话最后一轮。 */
export function mapSystems(b: ReplayBundle): Map<number, ReplaySystem[]> {
  const m = new Map<number, ReplaySystem[]>()
  const turns = b.sessions.turns
  for (const ev of b.sessions.systems) {
    let target = -1
    for (let i = 0; i < turns.length; i++) {
      if (turns[i].actor === ev.actor && ms(turns[i].t0) >= ms(ev.ts)) { target = i; break }
    }
    if (target < 0) for (let i = turns.length - 1; i >= 0; i--) {
      if (turns[i].actor === ev.actor) { target = i; break }
    }
    if (target < 0) continue
    let arr = m.get(target)
    if (!arr) { arr = []; m.set(target, arr) }
    arr.push(ev)
  }
  return m
}
