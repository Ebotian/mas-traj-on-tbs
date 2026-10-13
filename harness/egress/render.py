#!/usr/bin/env python3
"""Compose the layered egress policy and (optionally) render the restricted
task copy's allowed_hosts from it.

Layer 1: egress/policies/base.yml      (fixed infrastructure)
Layer 2: egress/policies/<task>.yml    (task overlay: restricted_hosts)

Default run is a check: report the composed list and whether
build/task-restricted/task.toml already matches (exit 1 on drift).
--write regenerates the allowed_hosts block (canonical formatting; the
manifests are the comment home).

Run: python3 /home/ebt/harbor-runs/egress/render.py --task tumor-immune-interface [--write] [--toml <path>]
"""
import argparse
import pathlib
import re
import sys

import tomllib

ROOT = pathlib.Path("/home/ebt/harbor-runs")
TASK_TOML = ROOT / "build" / "task-restricted" / "task.toml"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rulelib  # noqa: E402


def render_block(hosts):
    lines = ["allowed_hosts = ["]
    lines += [f'    "{h}",' for h in hosts]
    lines.append("]")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--toml", default=str(TASK_TOML),
                    help="task copy's task.toml to check/render "
                         "(default: the active build/task-restricted copy)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    toml_path = pathlib.Path(args.toml)

    composed = rulelib.compose(*rulelib.load_layers(args.task))
    have = tomllib.loads(toml_path.read_text())["environment"]["allowed_hosts"]
    same = set(have) == set(composed)
    order_note = " (order differs; not load-bearing)" if same and have != composed else ""
    print(
        f"composed: {len(composed)} hosts | task.toml: {len(have)} hosts | match: {same}{order_note}"
    )
    if not same:
        print("  only in composed:", [h for h in composed if h not in have])
        print("  only in task.toml:", [h for h in have if h not in composed])

    if args.write:
        text = toml_path.read_text()
        m = re.search(r"allowed_hosts = \[.*?\]", text, re.S)
        if not m:
            sys.exit("allowed_hosts block not found in task.toml")
        toml_path.write_text(text[: m.start()] + render_block(composed) + text[m.end():])
        tomllib.loads(toml_path.read_text())  # parse check
        ok = tomllib.loads(toml_path.read_text())["environment"]["allowed_hosts"] == composed
        print("written; re-check:", ok)
        sys.exit(0 if ok else 1)

    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
