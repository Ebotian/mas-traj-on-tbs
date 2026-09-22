#!/usr/bin/env python3
"""Generate the truncated positive-control variants, as frozen §4 candidates.

The lever this materialises is "the same published procedure, stopped earlier".
Each variant is a byte-identical copy of `pc/solution.py` except for one line:

    MAX_SWAPS = None     ->     MAX_SWAPS = K          (K accepted improving swaps)

so the claim "the variant is the frozen PC with one line changed" is verified by
`diff`-ing against that file, not asserted in prose.  `None` is the pin (run to a
local optimum); `K` is the truncation.

Why generate rather than hand-write five near-copies: five hand-written copies
would drift.  Why one directory each rather than a shared module: §4 runs a
candidate from a private content-addressed copy with no injected files, so a
candidate's identity has to be its own bytes -- `e_star_child.candidate_files`
digests everything under the candidate directory.

    python3 make_variants.py --write     # (re)generate variants/
    python3 make_variants.py --check     # verify emitted bytes against `git diff`-free template
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PC = HERE / "pc"
VARIANTS = HERE / "variants"

K_VALUES = (1, 2, 5, 10, 25)

ANCHOR = "MAX_SWAPS = None"

PURPOSE = (
    "PC truncation variant: the pinned NetworkX one_exchange applied to b_i, stopped after "
    "{k} accepted improving swap(s). Identical to positive_control/pc/solution.py except for "
    "the MAX_SWAPS line. A *proposed* alternative to the contract's PC_i; which truncation (if "
    "any) is adopted is a contract decision -- see gates/REVISION-PROPOSAL.md."
)


def variant_name(k):
    return f"pc_exchange_k{k:02d}"


def variant_source(base_text, k):
    if base_text.count(ANCHOR) != 1:
        raise SystemExit(f"template must contain exactly one {ANCHOR!r} line")
    return base_text.replace(ANCHOR, f"MAX_SWAPS = {k}")


def metadata(k, name):
    return {
        "candidate_id": name,
        "schema": "a0.maxcut.candidate/v1",
        "kind": "ok",
        "role": "positive-control-alternative",
        "version": "1.0.0",
        "purpose": PURPOSE.format(k=k),
        "expected": {
            "status": "ok",
            "failure_kind": None,
        },
        "derived_from": {
            "template": "positive_control/pc/solution.py",
            "one_line_changed": f"MAX_SWAPS = None -> MAX_SWAPS = {k}",
            "max_swaps": k,
            "pin": {
                "repository": "https://github.com/networkx/networkx",
                "commit": "b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b",
                "pinned_file": "positive_control/pc/pinned/networkx_maxcut_b69beb2c.py",
                "maxcut_py_sha256": "793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb",
            },
        },
    }


def emit(text):
    return text if text.endswith("\n") else text + "\n"


def write():
    base = (PC / "solution.py").read_text(encoding="utf-8")
    written = []
    for k in K_VALUES:
        name = variant_name(k)
        directory = VARIANTS / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "solution.py").write_text(emit(variant_source(base, k)), encoding="utf-8")
        (directory / "candidate.json").write_text(
            json.dumps(metadata(k, name), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(name)
    return written


def check():
    base = (PC / "solution.py").read_text(encoding="utf-8")
    failures = []
    for k in K_VALUES:
        name = variant_name(k)
        directory = VARIANTS / name
        source = directory / "solution.py"
        if not source.is_file():
            failures.append(f"{name}: missing solution.py")
            continue
        expected = emit(variant_source(base, k))
        actual = source.read_text(encoding="utf-8")
        if actual != expected:
            failures.append(f"{name}: solution.py is not the template with MAX_SWAPS = {k}")
        meta = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
        if meta.get("candidate_id") != name:
            failures.append(f"{name}: candidate_id {meta.get('candidate_id')!r}")
        # the diff against pc/solution.py must be exactly the MAX_SWAPS line
        import difflib
        diff = [line for line in difflib.unified_diff(
            base.splitlines(), actual.splitlines(), lineterm="", n=0)
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        if len(diff) != 2:
            failures.append(f"{name}: diff against pc/solution.py is {len(diff)} lines, expected 2")
    print(json.dumps({
        "schema": "a0.maxcut.variants_check/v1",
        "template": "positive_control/pc/solution.py",
        "template_sha256": hashlib.sha256((PC / "solution.py").read_bytes()).hexdigest(),
        "variants": [variant_name(k) for k in K_VALUES],
        "checked": len(K_VALUES),
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }, indent=2, sort_keys=True))
    return 0 if not failures else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        print("wrote: " + ", ".join(write()))
        return 0
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
