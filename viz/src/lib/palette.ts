import type { Evidence, NodeKind, ReadStatus } from '../types.ts'

/**
 * Validated with the bundled dataviz palette checker against a light surface.
 * Six hues WARNed as confusable under protanopia/deuteranopia/tritanopia, so this
 * is cut to three chromatic + one neutral, and hue is never the only channel:
 * every kind also has its own shape, every node carries a direct label, and
 * evidence grade rides on stroke dash rather than colour.
 */
export const COLOR = {
  frame: '#1d4ed8', // blue   — goal, dynamics, capability, RQ
  line: '#475569',  // slate  — research lines and concepts
  impl: '#166534',  // green  — implementation and measurement (a0/)
  find: '#be123c',  // rose   — conflict, finding, open decision
  ink: '#0f172a',
  muted: '#64748b',
  rule: '#e2e8f0',
  soft: '#f8fafc',
  good: '#166534',
  warn: '#b45309',
  bad: '#be123c',
} as const

export const KIND_COLOR: Record<NodeKind, string> = {
  frame: COLOR.frame, line: COLOR.line, impl: COLOR.impl, find: COLOR.find,
}

export const KIND_LABEL: Record<NodeKind, string> = {
  frame: '框架层 · 目标 / 动力学 / 能力 / RQ',
  line: '研究线与概念',
  impl: '实现与测量 (a0/)',
  find: '冲突 · 发现 · 未决',
}

export type Shape = 'circle' | 'square' | 'diamond' | 'tri'

export const KIND_SHAPE: Record<NodeKind, Shape> = {
  frame: 'circle', line: 'square', impl: 'diamond', find: 'tri',
}

/** Stroke dash by evidence grade. Solid = I verified it myself. */
export const EVIDENCE_DASH: Record<Evidence, string> = { v: '', s: '5 3', u: '2 3' }

export const EVIDENCE_LABEL: Record<Evidence, string> = {
  v: '我复核', s: '二手(调查者)', u: '我没读',
}

export const EVIDENCE_COLOR: Record<Evidence, string> = {
  v: COLOR.good, s: COLOR.warn, u: COLOR.muted,
}

export const STATUS_LABEL: Record<ReadStatus, string> = {
  read: '逐行读完',
  partial: '只读了一部分',
  secondhand: '二手(调查者读,我抽样复核)',
  unread: '完全没读',
  recovered: '重放回收,未读',
  fetched: '从账户库取回,未读',
  authored: '我写的',
  generated: '我生成并检索过,未逐行读',
}

export const STATUS_COLOR: Record<ReadStatus, string> = {
  read: COLOR.good,
  partial: COLOR.warn,
  secondhand: COLOR.frame,
  unread: COLOR.bad,
  recovered: COLOR.muted,
  fetched: COLOR.line,
  authored: COLOR.line,
  generated: COLOR.muted,
}
