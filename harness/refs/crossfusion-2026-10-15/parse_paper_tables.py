#!/usr/bin/env python3
"""parse_paper_tables.py — extract tables from the LaTeXML HTML of arXiv:2608.14905v3.

Input : paper.html (default /home/ebt/harbor-runs/data/papers/arxiv-2608.14905/paper.html)
Output: paper_tables.json next to this script, with provenance pinned
        (sha256 of the HTML; arXiv id pinned to v3 per check_citations.py 2026-10-15).

The tables are the paper's own numbers (Tables 3, 6, 11-21); this script only
copies them out of the HTML so later checks can assert their internal arithmetic
(sum of HIT column == 12,712, row sums == Table 12, pillar shares, ...).
"""
import hashlib
import html as H
import json
import re
import sys
from pathlib import Path

DROP = re.compile(r"<[^>]+>")


def cell_text(s: str) -> str:
    s = DROP.sub(" ", s)
    s = H.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_tables(doc: str):
    tables = []
    # LaTeXML wraps numbered tables in <figure class="ltx_table"> … </figure>
    figs = re.findall(
        r'<figure[^>]*class="[^"]*ltx_table[^"]*"[^>]*>(.*?)</figure>', doc, re.S
    )
    if not figs:  # fallback: plain tables
        figs = re.findall(r"<table[^>]*>(.*?)</table>", doc, re.S)
    for fi, fig in enumerate(figs):
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", fig, re.S)
        caption = cell_text(cap.group(1)) if cap else ""
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", fig, re.S):
            cells = [cell_text(td) for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            if cells:
                rows.append(cells)
        tables.append({"idx": fi, "caption": caption[:220], "rows": rows})
    return tables


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/home/ebt/harbor-runs/data/papers/arxiv-2608.14905/paper.html"
    )
    out = Path(__file__).parent / "paper_tables.json"
    raw = src.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    tables = parse_tables(raw.decode("utf-8", "replace"))
    doc = {
        "source": str(src),
        "sha256": sha,
        "arxiv": "2608.14905v3",
        "n_tables": len(tables),
        "tables": tables,
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    for t in tables:
        cap = t["caption"]
        head = " | ".join(t["rows"][0][:6]) if t["rows"] else ""
        print(f'#{t["idx"]:02d} rows={len(t["rows"]):3d} {cap[:78]}')
        print(f'     head: {head[:110]}')
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
