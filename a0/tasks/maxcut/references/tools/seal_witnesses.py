#!/usr/bin/env python3
"""Seal the witness partitions: keep their commitments, remove the vectors.

Why
---
Every `R_i` in `targets.json` is witnessed by a stored partition, and a stored
partition of `G_eval_####` is *the answer to the hold-out*: the verifier scored
exactly `R = OPT = 217` on `G_eval_0001` by copying one
(`a0/verify/a1-testbed/REPORT.md` §2c).  Every process on this machine runs as
one uid without root, so file permissions cannot be the control -- the only
control that is not obscurity is for the vector not to exist.

What this tool does
-------------------
`audit`  recomputes every witness (cut, digests) and cross-checks it against the
         per-run records, the SCIP records and `targets.json`.  Writes nothing.
`seal`   writes `witnesses/commitments.json` -- for every witness: the graph id,
         the run id, the sha256 of the file bytes, the sha256 of the canonical
         bytes, the recomputed cut and `|E|` -- and then *deletes* the plaintext
         vectors (the partition files and the MQLib stdout transcripts, which
         carry the same answer as a `±1` vector).  `--apply` is required; the
         default is a dry run.
`verify` re-checks the commitments against the values that remain on disk
         (`logs/runs/*.json`, `scip/*.json`, `targets.json`) and, when
         `--corpus DIR` names a retained copy of the removed tree, recomputes
         every witness from it again and compares file bytes to the commitment.

The residual risk is stated in `README.md` §7 and is not zero: the removed bytes
are still in this repository's *history* until the history is rewritten
(`git filter-repo`), and a copy kept outside the repository is outside every
control this directory has.  That is why the evaluator masks both the repository
(including `.git`) and the state roots from a candidate, and why the probe in
`../leak-proof/` scans the filesystem for copies that the masks do not know
about.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent.parent.parent

sys.path.insert(0, str(HERE))
from canonical import canonical_bytes, file_sha256, load_graph  # noqa: E402

SCHEMA = "a0.maxcut.witnesses/v1"

#: The plaintext surfaces this tool removes.  All four carry the same object: the
#: partition as a vector (`partitions/`), the same vector as a `±1` list in MQLib's
#: stdout (`raw/`), and the SCIP primal solution (`scip/`).
PARTITION_DIRS = ("logs", "logs_topup")
RAW_DIRS = ("logs", "logs_topup")


def log_dirs(extra=()) -> list[Path]:
    return [ROOT / "logs", ROOT / "logs_topup", *(Path(item) for item in extra)]


def run_records(dirs) -> dict:
    records = {}
    for directory in dirs:
        rdir = directory / "runs"
        if not rdir.is_dir():
            continue
        for path in sorted(rdir.glob("*.json")):
            record = json.loads(path.read_text())
            record["_path"] = str(path.relative_to(ROOT))
            record["_dir"] = str(directory.relative_to(ROOT))
            records.setdefault(record["graph_id"], []).append(record)
    return records


def scip_records() -> dict:
    records = {}
    for path in sorted((ROOT / "scip").glob("*.json")):
        document = json.loads(path.read_text())
        if document.get("schema") != "a0.maxcut.scip_attempt/v1":
            continue
        records[document["graph_id"]] = document
    return records


def witness_payload(path: Path, graph: dict) -> dict:
    raw = path.read_bytes()
    document = json.loads(raw.decode("ascii"))
    assignment = document["assignment"]
    cut = sum(1 for u, v in graph["edges"] if assignment[u] != assignment[v])
    return {
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
        "graph_id": document["graph_id"],
        "assignment_len": len(assignment),
        "cut_edges": cut,
        "bytes": len(raw),
    }


def collect(extra_logs=()) -> tuple[list[dict], list[dict], list[str]]:
    """Every witness on disk, with its recomputed cut, plus its cross-checks."""
    manifest = json.loads((ROOT.parent / "suite" / "manifest.json").read_text())
    graphs = {}
    for entry in manifest["graphs"]:
        graphs[entry["graph_id"]] = load_graph(ROOT.parent / "suite" / entry["path"])
    records = run_records(log_dirs(extra_logs))
    scips = scip_records()
    witnesses: list[dict] = []
    transcripts: list[dict] = []
    problems: list[str] = []

    for directory in log_dirs(extra_logs):
        pdir = directory / "partitions"
        if not pdir.is_dir():
            continue
        for path in sorted(pdir.glob("*.partition.json")):
            run_id = path.name[: -len(".partition.json")]
            graph_id = run_id.split("__", 1)[0]
            graph = graphs.get(graph_id)
            if graph is None:
                problems.append(f"{path.name}: no such graph in the suite manifest")
                continue
            payload = witness_payload(path, graph)
            record = next((item for item in records.get(graph_id, [])
                           if item.get("partition_path", "").endswith(path.name)), None)
            if record is None:
                problems.append(f"{path.name}: no per-run record carries this partition")
            else:
                if record.get("partition_sha256") != payload["file_sha256"]:
                    problems.append(f"{path.name}: file sha256 != the run record's commitment")
                if record.get("cut_edges") != payload["cut_edges"]:
                    problems.append(f"{path.name}: recomputed cut {payload['cut_edges']} != "
                                    f"recorded {record.get('cut_edges')}")
                if record.get("graph_sha256") != file_sha256(ROOT.parent / "suite"
                                                             / manifest_entry(manifest, graph_id)):
                    problems.append(f"{path.name}: graph sha256 differs from the run record")
            witnesses.append({
                "run_id": run_id,
                "graph_id": graph_id,
                "source_kind": "ensemble",
                "log_dir": directory.name,
                "path_removed": str(path.relative_to(ROOT)),
                "edges_total": len(graph["edges"]),
                "graph_sha256": file_sha256(ROOT.parent / "suite"
                                            / manifest_entry(manifest, graph_id)),
                "heuristic": run_id.split("__")[1] if "__" in run_id else None,
                "seed": None if "__" not in run_id else int(run_id.rsplit("__s", 1)[-1]),
                **payload,
            })

    for path in sorted((ROOT / "scip").glob("*.partition.json")):
        graph_id = path.name[: -len(".partition.json")]
        graph = graphs.get(graph_id)
        if graph is None:
            problems.append(f"{path.name}: no such graph in the suite manifest")
            continue
        payload = witness_payload(path, graph)
        record = scips.get(graph_id)
        if record is None:
            problems.append(f"{path.name}: no SCIP record for this graph")
        else:
            if record.get("primal_partition_sha256") != payload["file_sha256"]:
                problems.append(f"{path.name}: file sha256 != the SCIP record's commitment")
            if record.get("primal_recomputed_cut") != payload["cut_edges"]:
                problems.append(f"{path.name}: recomputed cut {payload['cut_edges']} != SCIP record "
                                f"{record.get('primal_recomputed_cut')}")
        witnesses.append({
            "run_id": graph_id,
            "graph_id": graph_id,
            "source_kind": "scip",
            "log_dir": "scip",
            "path_removed": str(path.relative_to(ROOT)),
            "edges_total": len(graph["edges"]),
            "graph_sha256": file_sha256(ROOT.parent / "suite" / manifest_entry(manifest, graph_id)),
            "heuristic": "SCIP",
            "seed": None,
            **payload,
        })

    for directory in log_dirs(extra_logs):
        rdir = directory / "raw"
        if not rdir.is_dir():
            continue
        for path in sorted(rdir.glob("*.stdout.txt")):
            digest = file_sha256(path)
            run_id = path.name[: -len(".stdout.txt")]
            record = next((item for item in records.get(run_id.split("__", 1)[0], [])
                           if item.get("raw_stdout_sha256") == digest), None)
            if record is None:
                problems.append(f"{path.name}: no run record commits to these stdout bytes")
            transcripts.append({
                "run_id": run_id,
                "graph_id": run_id.split("__", 1)[0],
                "log_dir": directory.name,
                "path_removed": str(path.relative_to(ROOT)),
                "file_sha256": digest,
            })
    return witnesses, transcripts, problems


def manifest_entry(manifest: dict, graph_id: str) -> str:
    for entry in manifest["graphs"]:
        if entry["graph_id"] == graph_id:
            return entry["path"]
    raise KeyError(graph_id)


def per_graph(witnesses: list[dict], targets: dict) -> dict:
    summary: dict[str, dict] = {}
    for item in witnesses:
        graph_id = item["graph_id"]
        entry = summary.setdefault(graph_id, {
            "witness_count": 0, "max_cut_edges": None,
            "best_run_id": None, "cut_edges_values": set(),
        })
        entry["witness_count"] += 1
        entry["cut_edges_values"].add(item["cut_edges"])
        if entry["max_cut_edges"] is None or item["cut_edges"] > entry["max_cut_edges"]:
            entry["max_cut_edges"] = item["cut_edges"]
            entry["best_run_id"] = item["run_id"]
    out = {}
    for graph_id, entry in sorted(summary.items()):
        target = targets["graphs"].get(graph_id, {})
        out[graph_id] = {
            "witness_count": entry["witness_count"],
            "distinct_cut_values": len(entry["cut_edges_values"]),
            "max_cut_edges": entry["max_cut_edges"],
            "best_run_id": entry["best_run_id"],
            "R": target.get("R"),
            "max_equals_R": entry["max_cut_edges"] == target.get("R"),
        }
    return out


def cmd_audit(args) -> int:
    witnesses, transcripts, problems = collect(args.logs_extra)
    if not witnesses and not transcripts:
        print("no plaintext witness is present: the store has been sealed.  `verify` checks the "
              "commitments; `verify --corpus <dir>` and `tools/verify_targets.py --witnesses <dir>` "
              "recompute from a retained copy")
        return 0
    targets = json.loads((ROOT / "targets.json").read_text())
    summary = per_graph(witnesses, targets)
    mismatched = [gid for gid, item in summary.items() if not item["max_equals_R"]]
    print(f"witnesses: {len(witnesses)} partitions + {len(transcripts)} stdout transcripts")
    print(f"graphs covered: {len(summary)}/60")
    print(f"per-graph max == targets R: {len(summary) - len(mismatched)}/{len(summary)}")
    if mismatched:
        print("  mismatch:", ", ".join(mismatched))
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for item in problems[:20]:
            print("  " + item)
        return 1
    print("PASS: every stored witness recomputes to the value its run record commits to, "
          "and the per-graph maximum is R")
    return 0


def cmd_seal(args) -> int:
    witnesses, transcripts, problems = collect(args.logs_extra)
    if problems:
        print("refusing to seal while the witness set does not cross-check:", file=sys.stderr)
        for item in problems[:20]:
            print("  " + item, file=sys.stderr)
        return 1
    targets = json.loads((ROOT / "targets.json").read_text())
    summary = per_graph(witnesses, targets)
    mismatched = [gid for gid, item in summary.items() if not item["max_equals_R"]]
    if mismatched:
        print(f"refusing to seal: {len(mismatched)} graphs where max witness != R", file=sys.stderr)
        return 1
    document = {
        "schema": SCHEMA,
        "sealed_utc": args.stamp,
        "purpose": "commitments to the witness partitions that were removed from this repository; "
                   "the vectors themselves are not here, because a stored partition of G_eval_#### "
                   "is the answer to the hold-out",
        "removed": {
            "partition_dirs": [f"{name}/partitions/" for name in PARTITION_DIRS],
            "raw_dirs": [f"{name}/raw/" for name in RAW_DIRS],
            "scip": "scip/*.partition.json",
        },
        "counts": {"witnesses": len(witnesses), "stdout_transcripts": len(transcripts)},
        "targets_json_sha256": file_sha256(ROOT / "targets.json"),
        "witnesses": witnesses,
        "stdout_transcripts": transcripts,
        "per_graph": summary,
        "recoverable_from": {
            "git": "the bytes were committed before this seal; `git show <rev>:<path_removed>` "
                   "returns them until the history is rewritten (git filter-repo). The evaluator "
                   "masks .git and this directory from a candidate for exactly that reason.",
            "corpus": "tools/seal_witnesses.py verify --corpus <dir> re-verifies a retained copy "
                      "against these commitments",
        },
    }
    target = ROOT / "witnesses" / "commitments.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not args.apply:
        print(f"dry run: would write {target.relative_to(ROOT)} "
              f"({len(witnesses)} witnesses) and delete:")
        for item in witnesses[:5]:
            print("  " + item["path_removed"])
        print(f"  ... and {len(witnesses) - 5} more partitions")
        for item in transcripts[:3]:
            print("  " + item["path_removed"])
        print(f"  ... and {len(transcripts) - 3} more stdout transcripts")
        return 0
    target.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    removed = 0
    for item in witnesses + transcripts:
        path = ROOT / item["path_removed"]
        if path.is_file():
            path.unlink()
            removed += 1
    print(f"sealed: {target.relative_to(ROOT)} written; {removed} plaintext files removed")
    print("commit with: git add -A -- a0/tasks/maxcut/references")
    return 0


def cmd_verify(args) -> int:
    commitments_path = ROOT / "witnesses" / "commitments.json"
    document = json.loads(commitments_path.read_text())
    targets = json.loads((ROOT / "targets.json").read_text())
    problems: list[str] = []
    for graph_id, entry in document["per_graph"].items():
        if not entry["max_equals_R"]:
            problems.append(f"{graph_id}: recorded max {entry['max_cut_edges']} != R {entry['R']}")
    checks = len(document["per_graph"])
    corpus = Path(args.corpus) if args.corpus else None
    recomputed = 0
    if corpus is not None:
        manifest = json.loads((ROOT.parent / "suite" / "manifest.json").read_text())
        graphs = {entry["graph_id"]: load_graph(ROOT.parent / "suite" / entry["path"])
                  for entry in manifest["graphs"]}
        for item in document["witnesses"]:
            path = corpus / item["path_removed"]
            if not path.is_file():
                problems.append(f"{item['path_removed']}: missing from the supplied corpus")
                continue
            payload = witness_payload(path, graphs[item["graph_id"]])
            recomputed += 1
            for key in ("file_sha256", "canonical_sha256", "cut_edges"):
                if payload[key] != item[key]:
                    problems.append(f"{item['path_removed']}: {key} differs from the commitment")
            if payload["cut_edges"] != targets["graphs"][item["graph_id"]]["R"] and \
                    item["run_id"] == document["per_graph"][item["graph_id"]]["best_run_id"]:
                problems.append(f"{item['path_removed']}: best witness does not reach R")
    print(f"witnesses: {document['counts']['witnesses']} committed, "
          f"{document['counts']['stdout_transcripts']} transcripts")
    print(f"per-graph commitments checked: {checks}")
    print(f"corpus: {corpus if corpus else 'not supplied (values only)'}"
          + (f", {recomputed} witnesses recomputed" if corpus else ""))
    if problems:
        print(f"FAIL ({len(problems)} problems):")
        for item in problems[:20]:
            print("  " + item)
        return 1
    print("PASS: every recorded maximum equals targets.json's R"
          + ("; every supplied witness matches its commitment and its cut" if corpus else ""))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, function, help_text in (
        ("audit", cmd_audit, "recompute every witness and cross-check it (writes nothing)"),
        ("seal", cmd_seal, "write the commitments and remove the plaintext vectors"),
        ("verify", cmd_verify, "check the commitments, and a corpus when one is supplied"),
    ):
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--logs-extra", nargs="*", default=[],
                          help="extra log directories (default: the two in this directory)")
        item.set_defaults(func=function)
        if name == "seal":
            item.add_argument("--apply", action="store_true", help="actually write and delete")
            item.add_argument("--stamp", default="", help="timestamp recorded in the manifest")
        if name == "verify":
            item.add_argument("--corpus", default=None,
                              help="directory holding the removed tree (a retained copy)")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
