/** Shared types. `verbatimModuleSyntax` is on, so import these with `import type`. */

/* ---------- concept map ---------- */

export type NodeKind = 'frame' | 'line' | 'impl' | 'find'

/** v = I read the source or computed it myself · r = that, and an independent external system re-derived it too
 *  · s = a subagent's path:line, spot-checked · u = never read. Ordering: r > v > s > u. */
export type Evidence = 'v' | 'r' | 's' | 'u'

export type EdgeKind =
  | 'has' | 'spec' | 'is' | 'kill' | 'inst' | 'part' | 'uses' | 'block'
  | 'gate' | 'then' | 'needs' | 'feed' | 'origin' | 'method' | 'note'
  | 'clash' | 'warn' | 'open' | 'orphan'

export interface GNode {
  id: string
  kind: NodeKind
  /** 0 = G0, 7 = stages not yet started */
  layer: number
  evidence: Evidence
  title: string
  cite: string
  summary?: string
  detail?: string
}

export interface Edge { source: string; target: string; kind: EdgeKind }

/* ---------- coverage ---------- */

export type ReadStatus = 'read' | 'partial' | 'secondhand' | 'unread' | 'recovered' | 'fetched' | 'authored' | 'generated'

export interface CoverageRow {
  path: string
  lines: number
  status: ReadStatus
  linesRead: number
  note?: string
}

export interface CoverageSummary {
  corpusFiles: number
  corpusLines: number
  corpusLinesExclTranscript: number
  corpusLinesRead: number
  corpusLinesReadExclTranscript: number
  a0TopMd: number
  a0TopMdLines: number
  a0LinesRead: number
  a0TrackedTotal: number
  repoTrackedTotal: number
}

/* ---------- measured numbers ---------- */

export interface StrengthRow {
  control: string
  /** accepted improving exchanges; Infinity for the retired unbounded control */
  k: number
  kLabel: string
  deltaDev: number; rhoDev: number
  deltaEval: number; rhoEval: number
  famDev: string; famEval: string
  dev: 'ADM' | 'NOT'; eval_: 'ADM' | 'NOT'
}

export interface CostRow { campaigns: number; wallHours: number; ceqCap: number; ceqMeasured: number }

export interface LadderStep {
  id: string; label: string; question: string
  state: 'done' | 'measured' | 'unmeasured' | 'blocked' | 'not-started'
  note: string; cite: string
}

/* ---------- registers ---------- */

export interface Conflict {
  id: string; title: string; kind: 'name-collision' | 'contradiction' | 'false-green' | 'provenance' | 'self-error'
  left: { who: string; cite: string; quote: string }
  right: { who: string; cite: string; quote: string }
  consequence: string
  evidence: Evidence
}

export interface Reversal {
  round: string; date: string; source: string
  items: { was: string; now: string; cite: string }[]
}

export interface Decision {
  id: string; question: string; group: 'theory' | 'landing' | 'cross' | 'corpus'
  status: 'open' | 'done' | 'blocked'
  blocks?: string[]
  recommendation?: string
  cite: string
}

export interface TimelineEvent {
  date: string
  /** UTC where the conversation is the source; local file mtime otherwise */
  clock: string
  label: string
  track: 'input' | 'conversation' | 'other-conversation' | 'repo' | 'this-session'
  artifact?: string
  note?: string
}
