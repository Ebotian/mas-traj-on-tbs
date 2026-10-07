#!/usr/bin/env node
/**
 * local2gpt/prepare_packet.mjs —— 只准备、不发送:上传附件 + 填正文,停下等人在浏览器里 review。
 *
 * 用法: node local2gpt/prepare_packet.mjs
 * 之后: 人在浏览器里看;要发就点 Send,或跑 local2gpt/send_packet.mjs(它按 sha 对账,不会重复上传)。
 *
 * 附件判据(2026-10-07 修正):附件是 <span class="…group/resource…"> 里的**截断**标签 —— 按文本匹配会漏。
 * 改为:在 composer 的 <form> 内找「叶子元素、文本以 packet-2026 起头」的 chip,并报 chips 计数;
 * 重复上传会出现多枚 chip,所以计数必须看得见。
 */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))

const S = process.env.WB_SESSION || 'cgpt-project-index'
const LATEST = path.join(HERE, 'out/.latest-packet')
const PKT = process.argv[2] || (fs.existsSync(LATEST)
  ? path.join(HERE, 'out', fs.readFileSync(LATEST, 'utf8').trim())
  : path.join(HERE, 'out', `packet-${new Date().toLocaleDateString('sv-SE')}.tar.gz`))
const MSG = process.env.WB_MSG || '/home/ebt/rsi-dev/local2gpt/packet_msg.md'
const SEL_COMPOSER = '[contenteditable="true"]'
const CHIP_PREFIX = 'packet-2026'

const post = async (b) => (await fetch('http://127.0.0.1:10086/command', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b),
})).json()
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const ev = (c) => post({ action: 'evaluate', args: { code: c }, session: S }).then((d) => (d.data ? String(d.data.value) : ''))

const state = () => ev(`(()=>{
  // 判据(2026-10-07 修正):只有 class 含 composer-attachment 的元素才是输入框附件。
  // 之前按「composer 的 form 内文本以 packet-2026 起头」判断,会把 Sources 面板与会话正文也算进来 —— 假阳性。
  const att=[...document.querySelectorAll('[class*="composer-attachment"]')].filter(e=>!(e.parentElement&&e.parentElement.closest('[class*="composer-attachment"]'))).length;
  const ce=document.querySelector('${SEL_COMPOSER}');
  return JSON.stringify({draft:ce?ce.innerText.length:0, chips:att, head:ce?ce.innerText.slice(0,40):''});
})()`)

// 主入口守卫必须放在**任何副作用之前**:放在文件末尾等于没有(顶层流程已经跑完)。
if (import.meta.url !== pathToFileURL(process.argv[1] || '').href) {
  console.error('prepare_packet.mjs 只应被直接运行;被 import 时不执行')
  process.exit(0)
}

if (!fs.existsSync(PKT)) { console.error('包不存在:', PKT); process.exit(1) }
if (!fs.existsSync(MSG)) { console.error('正文不存在:', MSG); process.exit(1) }

const FP = fs.existsSync(path.join(path.dirname(PKT), '.latest-fingerprint'))
  ? fs.readFileSync(path.join(path.dirname(PKT), '.latest-fingerprint'), 'utf8').trim()
  : crypto.createHash('sha256').update(fs.readFileSync(PKT)).digest('hex').slice(0, 8)
console.log('包:', path.basename(PKT), fs.statSync(PKT).size, 'B · 内容指纹', FP)
const CSHA = path.join(path.dirname(PKT), '.composer-fp')
const priorSha = fs.existsSync(CSHA) ? fs.readFileSync(CSHA, 'utf8').trim() : ''
const pre = JSON.parse(await state())
let uploaded = false
if (pre.chips >= 1 && priorSha === FP) {
  console.log('composer 里已是同一份包(sha 对账通过),跳过上传 —— 防止重复堆叠')
} else {
  if (pre.chips >= 1) console.warn('composer 里有 %d 枚 chip 且 sha 与本地不同;先删干净再传会更整齐(现在仍按一次新上传处理)', pre.chips)
  const up = await post({ action: 'upload', args: { files: [PKT], selector: 'input[type=file]' }, session: S })
  console.log('upload:', JSON.stringify(up).slice(0, 200))
  if (!up.ok) { console.error('上传失败(检查扩展的「允许访问文件网址」)'); process.exit(2) }
  uploaded = true
  await sleep(6000)
}

const f = await post({ action: 'fill', args: { selector: SEL_COMPOSER, value: fs.readFileSync(MSG, 'utf8') }, session: S })
console.log('fill:', JSON.stringify(f.data || f).slice(0, 120))
await sleep(2000)

const st = JSON.parse(await state())
console.log('after:', JSON.stringify(st))
fs.writeFileSync(path.join(path.dirname(PKT), '.composer-fp'), FP + '\n', 'utf8')
if (st.chips !== 1) console.warn('注意:composer 里有 %d 枚 chip(预期 1);多于 1 枚请在浏览器里删掉多余的。', st.chips)
console.log('\n完成:附件已挂(指纹 %s)、正文 %d 字符,未发送。请在浏览器里 review。', FP, st.draft)
