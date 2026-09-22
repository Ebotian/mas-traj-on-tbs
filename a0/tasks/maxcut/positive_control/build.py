#!/usr/bin/env python3
"""Freeze, and re-verify, the two artifacts this directory owns.

    b_i  =  `baseline/`   one seeded uniform random bisection
    PC_i =  `pc/`         NetworkX `one_exchange(G_i, initial_cut=b_i, seed=s_i)`

Both are candidates in INTERFACE.md §4's sense, so both are frozen the way
`C*(T1)`'s 21 candidates are: every byte in the directory is listed with its
sha256, and the whole candidate is reduced to one content digest by *E*'s own*
`candidate_files` / `candidate_source_digest` (`../e_star_child.py`), which is
the digest E* will stamp into every Outcome as `candidate_source_sha256`.  This
script computes that number with that function rather than re-deriving it, so
the frozen manifest and the evaluator cannot disagree.

    python3 build.py --freeze     # write/refresh manifest.json
    python3 build.py --check      # verify the tree still reproduces; exit 1 if not

`--check` also runs the cross-check that makes `b_i` trustworthy as *the*
baseline: through the real §4 ABI, `b_i` must emit byte-identical partitions to
`C*(T1)`'s `c02_ok_low_baseline` on all 60 frozen graphs.  Two independently
written programs, one answer, on the whole suite.
"""

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
sys.path.insert(0, str(MAXCUT))

import e_star_child  # noqa: E402  (E*'s own resolver: the identity authority)

GRAPH_SETS = ("dev", "eval", "calibration")
MANIFEST = HERE / "manifest.json"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite_graphs():
    manifest = json.loads((MAXCUT / "suite" / "manifest.json").read_text(encoding="utf-8"))
    return [(e["graph_id"], str(MAXCUT / "suite" / e["path"])) for e in manifest["graphs"]]


def describe(candidate_dir):
    spec = e_star_child.resolve_candidate(candidate_dir)
    return {
        "candidate_id": spec["candidate_id"],
        "dir": Path(candidate_dir).name,
        "entry": spec["entry"],
        "source_sha256": spec["source_sha256"],
        "files": spec["source_files"],
    }


def freeze():
    document = {
        "schema": "a0.maxcut.positive_control.manifest/v1",
        "task": "a0/tasks/maxcut",
        "authority": "a0/tasks/maxcut/INTERFACE.md",
        "identity_note": (
            "source_sha256 is e_star_child.candidate_source_digest over files[], "
            "i.e. exactly the candidate_source_sha256 E* stamps into every Outcome"
        ),
        "candidates": [describe(HERE / "baseline"), describe(HERE / "pc")],
    }
    MANIFEST.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def check():
    failures = []
    identity_failures = []
    if not MANIFEST.is_file():
        print("manifest.json missing: run --freeze", file=sys.stderr)
        return 1
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_dir = {entry["dir"]: entry for entry in frozen["candidates"]}

    for name in ("baseline", "pc"):
        live = describe(HERE / name)
        old = by_dir.get(name)
        if old is None:
            identity_failures.append(f"{name}: not in the frozen manifest")
            continue
        if live["source_sha256"] != old["source_sha256"]:
            identity_failures.append(
                f"{name}: source_sha256 {live['source_sha256']} != frozen {old['source_sha256']}")
        if {f["path"]: f["sha256"] for f in live["files"]} != {f["path"]: f["sha256"] for f in old["files"]}:
            identity_failures.append(f"{name}: file set or per-file sha256 changed")

    # ---- b_i == C*(T1)'s c02, through the real ABI ---------------------------
    baseline_spec = e_star_child.resolve_candidate(HERE / "baseline")
    c02_spec = e_star_child.resolve_candidate(MAXCUT / "candidates" / "c02_ok_low_baseline")
    scratch_root = Path(tempfile.mkdtemp(prefix="pc-build-"))
    graphs = suite_graphs()
    mismatches = []
    try:
        for graph_id, graph_path in graphs:
            digests = {}
            for label, spec in (("b_i", baseline_spec), ("c02", c02_spec)):
                scratch = scratch_root / label / graph_id
                scratch.mkdir(parents=True, exist_ok=True)
                out = scratch / "partition.json"
                e_star_child.run_invocation(
                    spec=spec, graph_path=Path(graph_path), out_path=out,
                    seed=1337, timeout_s=30.0, scratch=scratch,
                )
                digests[label] = sha256_file(out)
            if digests["b_i"] != digests["c02"]:
                mismatches.append({"graph_id": graph_id, **digests})
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)
    if mismatches:
        failures.append(f"b_i differs from C*(T1) c02 on {len(mismatches)} graphs: {mismatches[:3]}")

    report = {
        "schema": "a0.maxcut.positive_control.check/v1",
        "manifest_matches_live_tree": not identity_failures,
        "suite_graphs_compared_through_abi": len(graphs),
        "b_i_equals_c02_on_every_graph": not mismatches,
        "candidates": frozen["candidates"],
        "failures": identity_failures + failures,
    }
    report["verdict"] = "PASS" if not report["failures"] else "FAIL"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["failures"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        document = freeze()
        print(json.dumps({"frozen": [c["candidate_id"] for c in document["candidates"]],
                          "manifest": str(MANIFEST),
                          "manifest_sha256": sha256_file(MANIFEST)}, indent=2, sort_keys=True))
        return 0
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
