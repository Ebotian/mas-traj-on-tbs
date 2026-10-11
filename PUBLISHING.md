# 发表准备：敏感信息审计 / 许可 / 公开仓库清单（2026-10-11）

状态：**审计完成、技术项就绪；三项内容决策待你裁定**（见 §4）。按既定规则，本仓库无远端、
未推送；建仓与 push 需你的明确批准。

## 1 · 敏感信息审计（决定性检查，非抽样）

方法：从两个密钥源（`~/gptapi.md`、`harbor-runs/walkthrough/walkthrough.env`）提取 7 个
密钥形态 token（≥24 字符、含数字与字母），对**当前全部 37,557 个跟踪文件**与**全部历史**
（27,733 个 blob，`git rev-list --objects --all` 全量 `cat-file --batch` 搜索）做子串检验；
报告只记命中数与路径，不回显 token。

- **密钥泄漏：零命中**——当前文件与全部历史都没有任何 key token。`Authorization`/`Bearer`
  串在 15 个 replay bundle（含全量对话转录与设置）中亦零命中。
- **凭据文件名扫描**（*.env/secret/key/pem 等）：无非预期命中；`secrets` 命中均为
  `secrets.token_urlsafe` 之类代码用词。
- **身份信息**：邮箱命中全部为样板/本地域（`qwen-coder@alibabacloud.com` 82 次、
  `noreply@anthropic.com` 38 次、`worker@loreley.local`、`t@t.local` 等）；
  `Ebotian`／真名／电话零命中。
- **`~/gptapi.md` 路径提及（已评审，建议保留）**：107 个文件 204 处——全部是"运行时从该文件
  读 key"的实验命令记录（key 值本身从不在库内）。它是路径不是机密；改它会篡改实验记录原文，
  **建议原样保留并在本文件留档**。
- **二进制面**：`related_files` 采用文本白名单（PDF/克隆目录默认排除）；`node_modules/`、
  `dist/`、`.qwen/tmp/`（含会话解码材料）、`local2gpt/out/` 均已 ignore，已逐一核过。

## 2 · 发布面构成（会被公开的东西）

- 37,557 个跟踪文件 / 244 个提交；`.git` 打包 43MB（体量主要来自 viz 的 15 个轨迹 bundle
  共 67MB 中的文本）。
- `related_files/` 跟踪 83 个文本文件：你自己的文档（research_state_control v1–v4、报告与
  规格）、你的 ChatGPT 会话转录（3 个 conversation 目录）、web 审阅回复（gpt-review-*）。
  **第三方论文本体（PDF）没有入库**——白名单排除；被引处为文内引用。
- `viz/public/replay/*.json`：13 个走查 + tumor-1 的**完整对话转录**（含协议提示词、
  gate/board 账、raw 逐行）。这是"结果本体"，建议连同发布。
- `a0/`：测量链的脚本与证据（含上面说的 key 路径提及）。

## 3 · 许可（建议，待你拍板）

仓库是"代码 + 文档/语料"混合体，两类激进的差异值得分开：

| 方案 | 适用 | 效果 |
|---|---|---|
| **A（推荐）双证** | 代码（viz/、local2gpt/、a0 工具）= **Apache-2.0**；文档/语料（related_files/、spec、报告）= **CC BY 4.0** | 专利授权 + 署名即可引用；符合研究仓库惯例 |
| B 单证 | 全仓 **Apache-2.0** | 最省事；文档也被附加专利条款（无碍但少见于文档） |
| C 单证 | 全仓 **MIT** | 最短最自由；无显式专利授权 |

任何方案都需附 NOTICE 章：**引用自第三方论文/页面的片段仍归其原作者**，本许可不覆盖它们。
落盘物：`LICENSE`（代码）＋ `LICENSE-docs`（如选 A）＋ 根 `README.md`（待拟）。

## 4 · 待你裁定的三项

1. **许可选择**（A / B / C 或其它）；
2. **内容范围**：三个 ChatGPT 会话转录与 13 个 replay 全量转录（含协议内部提示词）随仓库
   公开，还是移出/脱敏？（我建议随附——它们是研究对象本体；但会话里有你的原始措辞，归你定）
3. **建仓与推送**：GitHub 账号 `Ebotian`；仓库名/可见性/是否保留完整 244 提交历史——按
   既定规则，**明确的"推"字才动手**。

## 5 · 技术清单（选定后即可执行）

- [ ] `LICENSE`(+`LICENSE-docs`) 落盘、根 `README.md` 起草（定位、结构、复现命令、
      数据与轨迹说明、NOTICE 指向）
- [ ] 可选：`~/gptapi.md` 提及处不加改动（已议）；如需改名版本，另开分支做一次性替换
- [ ] `git remote add` + push（**需你说"推"**）；或先 `gh repo create --private` 演练后转公开
