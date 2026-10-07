/** 账户侧 Library 的核查与取回台账。
 *
 *  数据来自 2026-10-06 的一次会话:库页 `chatgpt.com/library` 经懒加载滚到 159 张卡片,
 *  每张卡片的 aria-label 给出带扩展名的真名。取回分三条通道,校验方式各不相同,见 MECHANISMS。
 *  这一层此前不在任何视图里 —— 语料的来源只有「分享链接」与「两条支线对话」两种说法。
 */

export interface LibTotals {
  entries: number      // 库页卡片总数(懒加载到底)
  unmatched: number    // 按名比对后,仓库里没有对应物的
  recovered: number    // 本轮取回并提交的
  blocked: number      // 取不到**或未取**,状态逐条列出(见 BLOCKED[].status)
  archives: number     // 归档形态条目(按规则不入 git):48 个由名字判出(`.tar`),另 8 个 open-problem-lab `.zip` 由对话框标题露出
  other: number        // 属于其他项目(emsx/BESS、金融、个人配置等),约数
}

export const LIB_TOTALS: LibTotals = {
  entries: 159,
  unmatched: 118,
  recovered: 17,
  blocked: 7,
  archives: 56,
  other: 46,
}

export type Route = 'stitch' | 'copy' | 'iframe'

export const ROUTE_LABEL: Record<Route, string> = {
  stitch: 'CodeMirror 拼接',
  copy: 'Copy → 剪贴板',
  iframe: '沙盒 iframe 全选',
}

export interface RecoveryRow {
  name: string
  date: string
  bytes: number
  lines: number
  route: Route
  verify: string
  commit?: string
}

/** 17 份取回件。前五份是 B 线;再九份是 D 线 / a0 侧 / AdaPDC C0;最后三份只有渲染文本。 */
export const RECOVERED: RecoveryRow[] = [
  { name: 'open_world_plan_independent_review(1).typ', date: '09-18', bytes: 64412, lines: 601, route: 'stitch', verify: 'typst 编译通过', commit: '900bcb0' },
  { name: 'open_world_plan_independent_review(2).typ', date: '09-18', bytes: 61012, lines: 663, route: 'stitch', verify: 'typst 编译通过', commit: '900bcb0' },
  { name: 'open_world_plan_independent_review(3).typ', date: '09-20', bytes: 67680, lines: 762, route: 'stitch', verify: 'typst 编译通过', commit: '900bcb0' },
  { name: 'open_world_plan_independent_review(4).typ', date: '09-20', bytes: 72812, lines: 839, route: 'stitch', verify: 'typst 编译通过', commit: '900bcb0' },
  { name: 'open_world_plan_independent_review(5).typ', date: '09-20', bytes: 76012, lines: 935, route: 'stitch', verify: 'typst 编译通过', commit: '900bcb0' },
  { name: 'agent_engineering_independent_audit_v2_2026-09-24.md', date: '09-24', bytes: 18668, lines: 106, route: 'copy', verify: '源码原文(含 markdown 标记)', commit: 'ef9d9b2' },
  { name: 'agent_engineering_science_progress_2026-09-24.md', date: '09-24', bytes: 26774, lines: 195, route: 'copy', verify: '源码原文', commit: 'ef9d9b2' },
  { name: 'STATUS(1).md', date: '09-21', bytes: 26251, lines: 249, route: 'copy', verify: '源码原文;与 a0/STATUS.md 差 117 行', commit: 'ef9d9b2' },
  { name: 'STATUS(2).md', date: '09-21', bytes: 27029, lines: 251, route: 'copy', verify: '源码原文;与 a0/STATUS.md 差 115 行', commit: 'ef9d9b2' },
  { name: 'TIMING-REVIEW(1).md', date: '09-23', bytes: 55097, lines: 544, route: 'copy', verify: 'H_T 独立审查 v2;与 a0/TIMING-REVIEW.md 差 288 行', commit: 'ef9d9b2' },
  { name: 'c0-status-review.md', date: '09-10', bytes: 30231, lines: 338, route: 'copy', verify: '源码原文', commit: 'ef9d9b2' },
  { name: 'status.md', date: '09-10', bytes: 28524, lines: 323, route: 'copy', verify: '源码原文', commit: 'ef9d9b2' },
  { name: 'review-packet.md', date: '09-10', bytes: 22760, lines: 307, route: 'copy', verify: '源码原文(锚点 6db0d78)', commit: '301a4be' },
  { name: 'experiment-catalog-contract.md', date: '09-09', bytes: 7554, lines: 155, route: 'copy', verify: '源码原文', commit: '301a4be' },
  { name: '范畴论驱动实验系统的工程落地计划与审查包.rendered.txt', date: '09-10', bytes: 49426, lines: 1763, route: 'iframe', verify: '仅渲染文本:markdown 标记已被剥掉', commit: '301a4be' },
  { name: '范畴论驱动的实验编排与工程落地-AdaPDC审查与CEC实施方案.rendered.txt', date: '09-10', bytes: 47955, lines: 1370, route: 'iframe', verify: '仅渲染文本', commit: '301a4be' },
  { name: '范畴论优先的实验编排与工程落地-理论实现与路线评估.rendered.txt', date: '09-10', bytes: 48519, lines: 1271, route: 'iframe', verify: '仅渲染文本', commit: '301a4be' },
]

/** 磁盘上那份 v(6) 与取回件的对拍结果:这是整条抽取管线的校准点。 */
export const LADDER: { v: string; lines: number; note: string }[] = [
  { v: 'v(1)', lines: 601, note: '库里 File · 09-18' },
  { v: 'v(2)', lines: 663, note: '库里 File · 09-18' },
  { v: 'v(3)', lines: 762, note: '库里 File · 09-20' },
  { v: 'v(4)', lines: 839, note: '库里 File · 09-20' },
  { v: 'v(5)', lines: 935, note: '库里 File · 09-20' },
  { v: 'v(6)', lines: 1030, note: '= 磁盘上的 open_world_plan_independent_review.typ' },
]

export interface BlockedRow { name: string; why: string; status: 'reason' | 'symptom' | 'not-taken' | 'not-attempted' }

export const BLOCKED: BlockedRow[] = [
  { name: 'adapdc_architecture_report.typ', why: '观察到 >14 s 内没有 CodeMirror、也没有 Try again 按钮 —— 这是现象,不是根因(需请求响应或诊断日志)', status: 'symptom' },
  { name: 'adapdc_theory_review(1).typ', why: '同上:同一次观察,根因未查', status: 'symptom' },
  { name: 'agent_engineering_science_v1', why: '对话框标题露出真名 agent_engineering_science_v1.**zip** —— 是归档,不是文本', status: 'reason' },
  { name: 'agent_engineering_science_report.tex', why: '与未跟踪的 repro zip 内容重复(不是取不到)', status: 'not-taken' },
  { name: 'agent_engineering_science_references.bib', why: '同上', status: 'not-taken' },
  { name: 'analytic_closed_loop_loss_study', why: '未尝试,原因未查', status: 'not-attempted' },
  { name: 'Deep Research report', why: '未尝试,原因未查', status: 'not-attempted' },
]

export interface Mechanism { viewer: string; route: string; trap: string }

export const MECHANISMS: Mechanism[] = [
  {
    viewer: '代码类 .typ/.tex/.bib → CodeMirror',
    route: '滚轮滚动编辑器,把每个 .cm-line 与同行 top 的行号元素配对后拼接',
    trap: '按数组下标配对会被隐藏的「999」占位元素与折行打乱;scrollTop 直接赋值无效,只有真滚轮事件能滚',
  },
  {
    viewer: 'markdown / 文档 → HTML 渲染',
    route: '点 Copy(必须 CDP 真实点击),再 wl-paste -t text/plain 取原文',
    trap: '默认剪贴板风味可能是空 HTML 壳;按钮先出现、内容后加载,不等就绪会复制到空壳',
  },
  {
    viewer: 'Deep Research 报告 → 跨源沙盒 iframe',
    route: '在 iframe 内点击聚焦,再 Ctrl+A / Ctrl+C',
    trap: '没有 Copy 按钮;父页 DOM 里搜不到正文;iframe 是 OOPIF,Page.getFrameTree 不列它,Target 域被拒 —— 只能拿到渲染文本',
  },
]

export const LIB_NOTES = {
  falsified: '「B 线六版不可恢复」此前写进了三个地方(分享链接溯源、可重建性、账户清单)。' +
    '本轮在库页看到六张卡片并全部取回;v(6) 与磁盘那份归一化后逐字节相同(唯一差异是一个尾部空行)。',
  searchTrap: '同一次核查里,站点搜索对 open_world_plan 返回 0 命中,而库页有六版 ⇒ 搜索对 File 类至少漏过六项;' +
    '索引的真实范围未测(不能推广为「不索引 File」)。' +
    '用「搜索无命中」推断「文件不存在」正是当初误判的根因。',
  downloadDead: '卡片的 Download 不可用:/api/library/files/<id>/download → estuary 带签名链,服务端回 ' +
    '{"detail":"File link not found."}(33 字节,被浏览器记为中断下载)。',
  dupPolicy: '库里的多数条目是仓库已有文件的重复上传(带 (1)(2) 后缀);按名比对后跳过,未逐个 sha256。',
}
