# 对话记录：`related_files/` 语料的来源

这份目录保存一条 ChatGPT 对话的**文本记录**，以及重建它所需的两个脚本。语料里大部分文档是这条对话的产物；`a0/SYNTHESIS-2026-09-30.typ` §1 是它的梳理。

- 链接：https://chatgpt.com/share/6ab4c8dd-40b0-83ee-bd93-3eecc4c4b97f
- 抓取时间：2026-09-30（`curl --compressed`，2.4 MB 传输 / 11.2 MB HTML，HTTP 200）
- 对话跨度：**2026-09-17 08:46 → 09-24 07:36 UTC**
- 规模：4011 个节点，**1 个根、0 个分叉**（完全线性），46 个有正文的 user 轮次、771 个 assistant text/code 轮次

## 为什么需要脚本

`web_fetch` 拒绝这个页面：HTML 超过它的 10 MB 上限。对话正文也不在标记里，而在 React Router 的 turbo-stream 载荷中，必须解码：一个 148184 元素的扁平数组，字典值全部是索引，键去重，`-5` 表示 null。`decode_share.py` 的文件头记录了完整格式。

## 如何重建

```
python3 decode_share.py <url-or-html-file> <outdir>
```

产出 `mapping.json`、`transcript.md`、`user_turns.md`、`outline.md`。从已存的 HTML 跑一次约 0.8 秒。

## 这里有什么

| 文件 | 大小 | 是什么 |
|---|---:|---|
| `transcript.md` | 1 700 093 B | 全部 4011 节点按链序的文本，含角色、内容类型、时间戳、节点 id |
| `user_turns.md` | 9 653 B | 46 个 user 轮次全文。**构想的脊柱**：四次转向都出自这里 |
| `decode_share.py` | 9 415 B | 载荷解码器 |
| `replay_state_control.py` | 6 948 B | C 线 v1→v4 补丁链的重放器与已知答案测试 |

## 这里刻意没有什么

`mapping.json`（10 MB）、`outline.md`（74 KB）、原始 HTML（11 MB）、扁平数组（10 MB）—— 全部可由 `decode_share.py` 从链接重建，所以不入库。这与仓库既有做法一致（`*.all.jsonl` 被忽略，因为校验器能重组）。

**但前提条件与那些情况不同**：上游是可撤销的分享链接，不是持久的远端。链接一旦失效，`transcript.md` 就是唯一副本。这是它入库的理由。

## 已知的信息损失（不是我造成的，是导出造成的）

- **tool 输出被截断到恰好 20000 字符**，共 6 条消息。assistant 的 text 与 code **未截断**（最长的一条 38728 字符，正是写入 `research_state_control_review.tex` 的 heredoc）。
- 因此 `transcript.md` 对**导出**是无损的，对**原始对话**不是。
- 六种 content 形状已全部处理：`text` 3598、`thoughts` 194、`code` 108、`reasoning_recap` 51、`execution_output` 41、`model_editable_context` 18。覆盖率检查：27 条消息有 content 但无文本，逐条查看**全部是真空的**（`model_set_context: ""`、`thoughts: [{summary:"",content:"",chunks:[]}]`）。

## 重放验证的结论

C 线的 `research_state_control_review` 一天内改了四轮，语料原本只有 v1 与 v4。v2/v3 不是整份写入的，而是 `cp` 加补丁链生成的，所以只能重放、不能提取。

`replay_state_control.py` 从空沙箱重放 7 个变更步骤，再与磁盘上的已知答案对拍：

| 目标 | 结果 |
|---|---|
| `research_state_control_review.tex`（v1） | **逐字节相同** `ee567fd0b038119a` |
| `research_state_control_refs.bib`（v1） | **逐字节相同** `eb9709935ce7a5d1` |
| `research_state_control_refs_v4.bib`（链条末端） | **逐字节相同** `b16cb3b0dd44b40c` |
| `research_state_control_review_v4.tex` | 差 337 B / 15 处 |

那 337 字节**不是链条缺口**。差异全在排版层：1 处 `\emergencystretch=3em`、2 处 `\allowbreak`、29 行是把 `\boxed{...}` 重排为 `\begin{gathered}` 多行、`\quad` 换成 `\\`。去掉空白后字符级相似度 0.998186，散文与论断未变。而 `emergencystretch` 与 `allowbreak` 在整个载荷的 2 864 505 字符里 **0 命中**。

⇒ **磁盘上的 `research_state_control_review_v4.tex` 在这条对话结束之后又被排过版。** 语料不是对话的纯快照。

由此回收到语料根目录的四个文件（行数单调递增 616 → 931 → 1216 → 1607，与四轮扩写吻合）：

| 文件 | 字节 | sha256（前 16） |
|---|---:|---|
| `research_state_control_review_v2.tex` | 57 600 | `88a9efaca0c29d91` |
| `research_state_control_review_v3.tex` | 78 083 | `e2754bfa0e91a0dc` |
| `research_state_control_refs_v2.bib` | 20 875 | `6a779db0333bb7f0` |
| `research_state_control_refs_v3.bib` | 29 190 | `a8b784f7c19b70c5` |

**限定**：v2/v3 没有经过那次后期排版，所以可能有 overfull hbox。它们是**内容忠实**，不是**印刷忠实**。

## 重放器的两条纪律

1. **安全扫描后才执行。** 脚本先检查网络、`subprocess`、`eval`、`unlink` 等构造；唯一的 `rm -f` 必须精确匹配删除 LaTeX 辅助文件那一条，否则拒绝运行。实测 7 个步骤：`network=0, subprocess=0, eval=0`。
2. **LaTeX 用 PATH 垫片中和，不做文本替换。** 第一版把 `biber` 替换成 `true`，结果连 heredoc 正文里的 `backend=biber` 一起改了，v1 因此与磁盘差一行。垫片不接触文档内容。

## 不可恢复的部分（记录事实，不要再追）

- `open_world_plan_independent_review(1).typ` 至 `(6).typ`：载荷里**只有截断的读取窗口**（`s[:14000]`、`sed -n '1,260p'`、`'260,620p'`、`'620,1040p'`），**没有任何写入操作**。六版都不可恢复。
- 四个 `.pdf` 构建产物：本地无 ctex，也不必要。
- `agent_engineering_science_repro_bundle.zip`：来自另一条对话，已在语料根目录，未跟踪。

## 入库前的检查

`transcript.md` 与 `user_turns.md` 按 10 类秘密模式扫描（OpenAI/Anthropic 式 key、GitHub token、AWS、Slack、Google API key、私钥块、bearer、`api_key=` 赋值、DeepSeek key、JWT）：**0 命中**。`sk-` 的四处出现全是 `task-specific`、`risk-controlled` 的子串。
