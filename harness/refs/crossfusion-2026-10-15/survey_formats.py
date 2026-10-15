#!/usr/bin/env python3
"""survey_formats.py — scan AutoResearchEval trajectories for schema coverage.

Reads every <model dir>/*.jsonl under the staged dataset (harbor-runs/data/autoresearch-eval),
sniffs the log format from the first rows, and aggregates per (subset, model):

  - files, format(s) seen
  - row-type counts; per-type timestamp coverage
  - usage/usageMetadata presence
  - tool-name vocabulary (claude/gemini) or item types (codex), action markers (text formats)

Output: survey.json (machine) + stdout table (human). Deterministic; zero model calls.

Usage: python3 survey_formats.py [--root DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/ebt/harbor-runs/data/autoresearch-eval")


def sniff(first_rows: list[dict]) -> str:
    for r in first_rows:
        keys = set(r.keys())
        if "item" in keys and str(r.get("type", "")).startswith("item."):
            return "codex_items"
        if "tool_name" in keys and "tool_id" in keys:
            return "gemini_ndjson"
        if "message" in keys and ("session_id" in keys or r.get("type") in ("assistant", "user", "result", "system")):
            return "claude_stream"
        if keys == {"type", "tool", "content"} or {"type", "tool", "content"} <= keys:
            return "gemini_text"
        if "raw_marker" in keys:
            return "codex_text"
    return "unknown"


def survey_file(path: Path, agg: dict) -> None:
    first: list[dict] = []
    ftype = None
    types: Counter = Counter()
    typts: dict[str, Counter] = defaultdict(Counter)  # row type -> {has_ts: n}
    tools: Counter = Counter()
    items: Counter = Counter()
    markers: Counter = Counter()
    usage_rows = 0
    rows = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                agg["bad_lines"] += 1
                continue
            if not isinstance(r, dict):
                continue
            rows += 1
            if len(first) < 5:
                first.append(r)
                if len(first) == 5 and ftype is None:
                    ftype = sniff(first)
            t = str(r.get("type"))
            types[t] += 1
            ts = r.get("timestamp")
            typts[t]["yes" if isinstance(ts, str) else "no"] += 1
            msg = r.get("message")
            has_usage = (
                isinstance(r.get("usage"), dict)
                or isinstance(r.get("usageMetadata"), dict)
                or (isinstance(msg, dict) and isinstance(msg.get("usage"), dict))
            )
            if has_usage:
                usage_rows += 1
            if "tool_name" in r:
                tools[str(r.get("tool_name"))] += 1
            if isinstance(r.get("message"), dict):
                for b in (r["message"].get("content") or []):
                    if isinstance(b, dict):
                        if b.get("type") == "tool_use":
                            tools[str(b.get("name"))] += 1
                        elif b.get("type") == "tool_result":
                            tools["<tool_result>"] += 1
            if isinstance(r.get("item"), dict):
                items[str(r["item"].get("type"))] += 1
            if "raw_marker" in r:
                markers[str(r.get("raw_marker"))] += 1
            if isinstance(r.get("tool"), str):
                tools[str(r.get("tool"))] += 1
    if ftype is None:
        ftype = sniff(first)
    agg["files"] += 1
    agg["formats"][ftype] += 1
    agg["rows"] += rows
    agg["types"].update(types)
    for t, c in typts.items():
        agg["typts"][t]["yes"] += c["yes"]
        agg["typts"][t]["no"] += c["no"]
    agg["tools"].update(tools)
    agg["items"].update(items)
    agg["markers"].update(markers)
    agg["usage_rows"] += usage_rows
    if rows and ftype in ("gemini_text", "codex_text", "codex_items"):
        agg["text_rows"] += rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default=str(Path(__file__).parent / "survey.json"))
    args = ap.parse_args()
    root = Path(args.root)

    result = {"root": str(root), "groups": {}}
    per_group_aggs: dict[str, dict] = {}
    for subset in ("open-ended", "optimization"):
        tdir = root / subset / "trajectories"
        if not tdir.is_dir():
            continue
        for mdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            key = f"{subset}/{mdir.name}"
            agg = per_group_aggs.setdefault(key, {
                "files": 0, "formats": Counter(), "rows": 0, "types": Counter(),
                "typts": defaultdict(Counter), "tools": Counter(), "items": Counter(),
                "markers": Counter(), "usage_rows": 0, "bad_lines": 0, "text_rows": 0,
            })
            for f in sorted(mdir.glob("*.jsonl")):
                survey_file(f, agg)

    for key, agg in sorted(per_group_aggs.items()):
        g = {
            "files": agg["files"],
            "formats": dict(agg["formats"]),
            "rows": agg["rows"],
            "types": dict(agg["types"].most_common()),
            "ts_coverage": {t: dict(c) for t, c in sorted(agg["typts"].items())},
            "tools_top": dict(agg["tools"].most_common(30)),
            "items_top": dict(agg["items"].most_common(30)),
            "markers": dict(agg["markers"].most_common(30)),
            "usage_rows": agg["usage_rows"],
            "bad_lines": agg["bad_lines"],
        }
        result["groups"][key] = g

    out = Path(args.out)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    for key, g in result["groups"].items():
        print(f"== {key}: files={g['files']} formats={g['formats']} rows={g['rows']} usage_rows={g['usage_rows']}")
        print(f"   types={g['types']}")
        tsc = {t: c for t, c in g["ts_coverage"].items() if t in ("assistant", "user", "tool_use", "tool_result", "result", "message")}
        print(f"   ts_coverage={tsc}")
        if g["tools_top"]:
            print(f"   tools={g['tools_top']}")
        if g["items_top"]:
            print(f"   items={g['items_top']}")
        if g["markers"]:
            print(f"   markers={g['markers']}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
