#!/usr/bin/env python3
"""引用审计:抓每个 arXiv 编号的元数据,标出两类**必须**处理的条目。

为什么需要它:2026-10-08 第 8 轮外部复核抓到一条重错 —— 我引的一句话出自 `2607.08665` 的 **v2**,
而该文 **v3 是"实质性的方法学重建"**,明写那批主张「not retained」。我此前的核验只查了**编号与标题**,
没查**版本**。这个脚本把"版本"变成机械可查的一列。

用法:
    python3 local2gpt/check_citations.py <file> [<file> ...]

输出两类 flagged 条目:
    MULTI-VERSION  该编号有多个版本(updated != published)⇒ 引用前**必须钉版本**
    COMMENT-FLAG   comments 字段出现修订/撤回类词 ⇒ **必须回去读那一段**
"""
import re
import sys
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

API = "https://export.arxiv.org/api/query?id_list={ids}&max_results=100"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
FLAG_WORDS = re.compile(r"retract|not retained|supersed|withdraw|revis|reconstruct|correct|errata", re.I)


def ids_in(files):
    pat = re.compile(r"\b(2[0-9]{3})\.(\d{4,5})\b")
    out = []
    for f in files:
        for a, b in pat.findall(pathlib.Path(f).read_text(encoding="utf-8")):
            i = f"{a}.{b}"
            if i not in out:
                out.append(i)
    return out


def fetch(ids):
    url = API.format(ids=",".join(ids))
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read()


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    rows = []
    for e in root.findall("a:entry", NS):
        aid = e.find("a:id", NS).text.rsplit("/abs/", 1)[-1]
        title = " ".join(e.find("a:title", NS).text.split())
        published = e.find("a:published", NS).text[:10]
        updated = e.find("a:updated", NS).text[:10]
        c = e.find("arxiv:comment", NS)
        comment = " ".join(c.text.split()) if c is not None and c.text else ""
        rows.append((aid, title, published, updated, comment))
    return rows


def main(files):
    ids = ids_in(files)
    print(f"输入 {len(files)} 个文件,去重得 {len(ids)} 个 arXiv 编号\n")
    rows = []
    for i in range(0, len(ids), 20):
        rows.extend(parse(fetch(ids[i:i + 20])))
    got = {r[0].split("v")[0] for r in rows}
    missing = [i for i in ids if i not in got]
    multi = [r for r in rows if r[2] != r[3]]
    flagged = [r for r in rows if r[4] and FLAG_WORDS.search(r[4])]
    print(f"返回 {len(rows)} 条 | 未返回 {len(missing)} 条 {missing if missing else ''}\n")
    print(f"=== MULTI-VERSION({len(multi)} 条:引用前必须钉版本)===")
    for a, t, p, u, c in multi:
        print(f"  {a:<12} {p} → {u}  {t[:60]}")
    print(f"\n=== COMMENT-FLAG({len(flagged)} 条:必须回去读那一段)===")
    for a, t, p, u, c in flagged:
        print(f"  {a:<12} {c[:150]}")
    if not flagged:
        print("  (无)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["related_files/economics-of-agent-systems-2026-10-08.md"]))
