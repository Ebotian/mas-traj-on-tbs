#!/usr/bin/env node
/**
 * local2gpt/send_packet.mjs —— 把包发给网页版 GPT,并把答复落盘。
 *
 * 用法:  node local2gpt/send_packet.mjs [packet.tar.gz]
 * 前置:  项目会话已在会话组某标签打开、Work 模式选中、Kimi 扩展已开「允许访问文件网址」。
 *
 * 本脚本修掉了首轮发送暴露的四个错:
 *   1. 轮询预算 900 s > 单命令上限 600 s ⇒ 压到 150 s;
 *   2. 只在结束才写文件,中断全丢 ⇒ 每次轮询都覆写;
 *   3. 该会话视图不用 [data-message-author-role] ⇒ 改用 main.innerText 分段取;
 *   4. 该视图不用任何 data-testid,发送键是 button[aria-label="Send"] ⇒ 两者兼取。
 * 另加主入口守卫:被 import(而非直接运行)时不执行 —— 首轮我用 import 做"语法检查",
 * 结果真跑了一遍并重复上传;守卫让这个错误不可能再发生。
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const S = process.env.WB_SESSION || 'cgpt-project-index'
const PACKET = process.argv[2] || path.join(HERE, 'out/packet-2026-10-06.tar.gz')
const MSG = process.env.WB_MSG || '/tmp/packet_msg.md'
const OUT = process.env.WB_OUT || path.join(HERE, 'out/reply-2026-10-06.md')
const POLL_MS = 6000
const DEADLINE_MS = 150000
const SEL_INPUT = 'input[type=file]'
const SEL_COMPOSER = '[contenteditable="true"]'
const SEL_SENDS = ['button[aria-label="Send"]', '[data-testid="send-button"]']

const post = async (b) => (await fetch('http://127.0.0.1:10086/command', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b),
})).json()
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const ev = (code) => post({ action: 'evaluate', args: { code }, session: S }).then((d) => (d.data ? String(d.data.value) : ''))
const clickAt = async (x, y) => {
  await post({ action: 'cdp', args: { method: 'Input.dispatchMouseEvent', params: { type: 'mouseMoved', x, y } }, session: S })
  await sleep(200)
  for (const t of ['mousePressed', 'mouseReleased']) {
    await post({ action: 'cdp', args: { method: 'Input.dispatchMouseEvent', params: { type: t, x, y, button: 'left', clickCount: 1 } }, session: S })
    await sleep(140)
  }
}

/** 分段取 main.innerText,避开工具输出截断。 */
async function harvest() {
  const first = JSON.parse(await ev(`(()=>{const m=document.querySelector('main')||document.body;const t=m.innerText||'';return JSON.stringify({total:t.length,part:t.slice(0,12000)})})()`))
  let text = first.part
  for (let off = 12000; off < first.total; off += 12000) {
    const n = JSON.parse(await ev(`(()=>{const m=document.querySelector('main')||document.body;return JSON.stringify({part:(m.innerText||'').slice(${off},${off + 12000})})})()`))
    text += n.part
  }
  return text
}

/** 幂等:已是"附件 + 草稿"状态就不再重复上传/填充。 */
async function composerState() {
  return JSON.parse(await ev(`(()=>{
    const ce=document.querySelector('${SEL_COMPOSER}');
    const t=document.body.innerText||'';
    return JSON.stringify({draft:ce?ce.innerText.length:0, attached:t.indexOf(${JSON.stringify(path.basename(PACKET).split('.')[0])})>=0});
  })()`))
}

async function main() {
  if (!fs.existsSync(PACKET)) { console.error('包不存在:', PACKET); process.exit(1) }
  if (!fs.existsSync(MSG)) { console.error('正文文件不存在:', MSG); process.exit(1) }
  const msg = fs.readFileSync(MSG, 'utf8')

  const st = await composerState()
  console.log('composer 现状:', JSON.stringify(st))
  if (st.attached && st.draft > 200) {
    console.log('已是「附件 + 草稿」状态,跳过上传与填充(幂等)')
  } else {
    const up = await post({ action: 'upload', args: { files: [PACKET], selector: SEL_INPUT }, session: S })
    console.log('upload:', JSON.stringify(up).slice(0, 200))
    if (!up.ok) { console.error('上传失败 —— 检查扩展的「允许访问文件网址」;未发送任何消息'); process.exit(2) }
    await sleep(5000)
    const f = await post({ action: 'fill', args: { selector: SEL_COMPOSER, value: msg }, session: S })
    console.log('fill:', JSON.stringify(f.data || f).slice(0, 120))
    await sleep(1500)
  }

  let b = { found: false }
  for (const sel of SEL_SENDS) {
    const r = JSON.parse(await ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return JSON.stringify({found:false});const r=el.getBoundingClientRect();return JSON.stringify({found:true,sel:${JSON.stringify(sel)},x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)})})()`))
    if (r.found) { b = r; break }
  }
  if (!b.found) { console.error('找不到发送键(尝试过 %s);正文已填但未发送', SEL_SENDS.join(' , ')); process.exit(3) }
  console.log('发送键:', b.sel)
  await clickAt(b.x, b.y)

  const t0 = Date.now()
  let prev = '', stable = 0, text = ''
  while (Date.now() - t0 < DEADLINE_MS) {
    await sleep(POLL_MS)
    text = await harvest()
    fs.writeFileSync(OUT, `<!-- harvested ${new Date().toISOString()} -->\n\n${text}\n`, 'utf8')
    stable = text.length === prev.length && text.length > 0 ? stable + 1 : 0
    prev = text
    console.log(`  t=${((Date.now() - t0) / 1000).toFixed(0)}s len=${text.length} stable=${stable}`)
    if (stable >= 3) break
  }
  console.log(`\n完成:${text.length} 字符 → ${OUT}`)
  if (stable < 3) console.log('注意:未达稳定条件;文件已按当前内容落盘,可稍后重跑本脚本再抓一次。')
}

if (import.meta.url === pathToFileURL(process.argv[1] || '').href) main()
