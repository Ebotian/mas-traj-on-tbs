// check_views.mjs —— React 视图归属检查(2026-10-12「电气试验误挂交接实验」后的机制性预防)。
//
// 规则:public/replay/index.json 里的每个 exp 必须至少被一个 React 视图的 include 白名单登记
//   (防「孤儿」——轨迹在库但任何页面都不可达);
//   反过来,include 里的名字必须都在 index.json(防「幽灵」——名字登记了但 bundle 不存在)。
// 覆盖面:「登记一致性」这一类。**不覆盖**「归属是否属于该视图的家族」(人工判断;归属表见
//   scripts/README.md —— 新增实验时必须按表登记)。
//
//   npm run check:views
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const idx = JSON.parse(readFileSync(path.join(ROOT, 'public', 'replay', 'index.json'), 'utf8'))
const indexExps = new Set(idx.map((e) => e.exp))

const VIEW_FILES = ['views/handoff.tsx', 'views/tumor.tsx', 'views/microarch.tsx', 'views/tess.tsx', 'views/replay/index.tsx']
const views = {}
for (const f of VIEW_FILES) {
  const src = readFileSync(path.join(ROOT, 'src', f), 'utf8')
  const m = src.match(/include=\{\[([\s\S]*?)\]\}/)
  views[f] = m ? [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]) : []
}

let bad = 0
const union = new Set(Object.values(views).flat())
for (const e of [...indexExps].sort()) {
  if (!union.has(e)) { console.log('ORPHAN: index 有而所有视图 include 均未登记 ->', e); bad++ }
}
for (const [f, list] of Object.entries(views)) {
  for (const x of list) if (!indexExps.has(x)) { console.log('GHOST: 视图登记而 index 无此 bundle ->', f, x); bad++ }
}

console.log('\n视图归属:')
for (const [f, list] of Object.entries(views)) {
  console.log(' ', path.basename(f).padEnd(14), String(list.length).padStart(2), '项:', [...list].sort().join(', '))
}
console.log(bad ? `\nFAIL: ${bad} 处归属不一致` : `\nOK: index 的 ${indexExps.size} 个 exp 全部有视图归属,且无幽灵登记`)
process.exit(bad ? 1 : 0)
