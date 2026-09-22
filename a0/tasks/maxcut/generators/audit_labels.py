#!/usr/bin/env python3
"""The Planted-label audit: make the suite's leakage claim check something true.

The problem this replaces
-------------------------
`suite/README.md` §5 and `maxcut_suite.py verify`'s `leakage_*` counters searched
`suite/**/*.json` for the label vectors recorded in `generators/provenance.json`.
Those vectors were **stale**: they were produced by an earlier revision of the
seed derivation and match none of the 15 shipped Planted graphs (their seeds
differ from the graphs' `generator.seed`, and their intra/inter edge densities
show no community structure at all).  A green check that searches for vectors no
shipped graph contains proves nothing -- the verifier's finding F4.

What is true, and what this tool checks
--------------------------------------
1. **The labels are a function of the frozen bytes.**  Each Planted graph's
   `generator` block regenerates its edge list exactly, and the same stream
   produces the planted label vector.  So `provenance.json` is now written *from
   the shipped files* (`refresh`), never from a build-time variable: the recorded
   labels are the labels of the graph that is on disk, or the tool fails.
2. **The labels are in no JSON file a candidate is given.**  The needles are the
   true labels -- 0/1 and `±1` spellings, the class-membership lists, and the
   bitmask -- searched over `suite/**/*.json` (the frozen data) and over the
   *candidate-facing view* of every graph (`e_star.py::candidate_graph_document`).
3. **The view is the object a candidate sees.**  The suite file itself cannot be
   made label-free: §2 keeps the `generator` block, and the block plus the
   frozen generator *is* the label vector.  So the check that matters is on the
   handed bytes, and the audit asserts that they carry exactly
   `{schema, graph_id, family, n, edges}` and no `generator`/`notes`.

`maxcut_suite.py` is left byte-identical on purpose: `suite/manifest.json`
records the generator source's sha256, so editing it would break
`verify`'s `generator_revision` check and move the suite's frozen identity.  This
tool is additive; `generators/DEVIATIONS.md` records that.

Usage
-----
    python3 generators/audit_labels.py verify          # the audit (exit 0/1)
    python3 generators/audit_labels.py refresh --apply # rewrite provenance.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
SUITE = TASK / "suite"
PROVENANCE = HERE / "provenance.json"
REPO = TASK.parent.parent.parent

sys.path.insert(0, str(HERE))
import maxcut_suite as suite_generator  # noqa: E402
sys.path.insert(0, str(TASK))
import e_star  # noqa: E402

PLANTED_GENERATOR = "planted_partition"
ROLE_DIRS = ("dev", "eval", "calibration")


def shipped_graphs() -> list[tuple[str, str, Path]]:
    """(role, graph_id, path) for every graph in the frozen suite."""
    found = []
    for role in ROLE_DIRS:
        for path in sorted((SUITE / role).glob("*.json")):
            found.append((role, path.stem, path))
    return found


def planted_truth(path: Path) -> tuple[dict, list[int], list[int]] | None:
    """Regenerate a Planted graph's edges and labels from its own generator block.

    Returns `(document, edges, labels)`, or None when the graph is not Planted.
    Raises when the regeneration does not reproduce the frozen edge list: that is
    the failure that would make every label claim below meaningless.
    """
    document = json.loads(path.read_text())
    if document.get("family") != "Planted":
        return None
    record = document["generator"]
    if record["name"] != PLANTED_GENERATOR:
        raise SystemExit(f"{path}: Planted graph does not use {PLANTED_GENERATOR}")
    rng = suite_generator.SplitMix64(int(record["seed"]))
    edges, labels = suite_generator.gen_planted_partition(
        int(document["n"]), record["params"], rng)
    edges = sorted((u, v) if u < v else (v, u) for u, v in edges)
    if [list(edge) for edge in edges] != document["edges"]:
        raise SystemExit(
            f"{path}: regeneration from (generator, params, seed) does not reproduce the frozen "
            "edge list, so no label vector can be attributed to this file")
    return document, edges, list(labels)


def needles_for(labels: list[int]) -> dict[str, str]:
    """Every spelling of a label vector an adversary or a grep could use."""
    values = list(labels)
    classes = sorted(set(values))
    class_membership = [[index for index, value in enumerate(values) if value == klass]
                        for klass in classes]
    needles = {
        "compact 0/1 vector": json.dumps(values, separators=(",", ":")),
        "spaced 0/1 vector": json.dumps(values),
        "compact +-1 vector": json.dumps([1 if value else -1 for value in values],
                                         separators=(",", ":")),
        "spaced +-1 vector": " ".join("1" if value else "-1" for value in values),
        "class membership lists": json.dumps(class_membership, separators=(",", ":")),
    }
    if set(values) <= {0, 1}:
        needles["decimal bitmask"] = str(int("".join(str(value) for value in values), 2))
    else:
        needles["per-class bitmasks"] = json.dumps(
            [int("".join("1" if value == klass else "0" for value in values), 2) for klass in classes],
            separators=(",", ":"))
    return needles


def load_provenance() -> dict:
    return json.loads(PROVENANCE.read_text())


def cmd_refresh(args) -> int:
    """Rewrite `provenance.json` from the frozen suite (never from a build variable)."""
    master = json.loads((HERE / "config.json").read_text())["master_seed"]
    planted = []
    for role, graph_id, path in shipped_graphs():
        truth = planted_truth(path)
        if truth is None:
            continue
        document, _edges, labels = truth
        planted.append({
            "graph_id": graph_id,
            "role": role,
            "family": "Planted",
            "stratum": stratum_of(graph_id),
            "seed": int(document["generator"]["seed"]),
            "planted_labels": labels,
            "planted_community_sizes": list(document["generator"]["params"]["community_sizes"]),
        })
    document = {
        "schema": "a0.maxcut.suite.provenance/v1",
        "generator": {"name": "generators/maxcut_suite.py",
                      "version": suite_generator.GENERATOR_VERSION},
        "master_seed": master,
        "role_seed_stream": "generators/maxcut_suite.py::derive_seed — sha256 of "
                            "'a0.maxcut.suite/v1|master=<m>|role=<r>|family=<f>|stratum=<s>|rep=<i>|"
                            "graph_id=<id>'; every graph draws from its own stream",
        "note": [
            "Solution provenance. `planted_labels` is the community label of every node of a",
            "Planted graph, and it is a *function of the frozen bytes*: the graph's own",
            "`generator.params` + `generator.seed` reproduce both its edge list and this vector.",
            "It is kept OUT of suite/** as text, but that is not secrecy: a reader of",
            "suite/<role>/<graph_id>.json plus generators/maxcut_suite.py can recompute it.",
            "The property the study actually needs is therefore not 'the labels are absent from",
            "the suite' but 'the labels are absent from what a candidate is handed', and that is",
            "what is now checked: `e_star.py` hands over `candidate_graph_document()`",
            "(schema/graph_id/family/n/edges only), and generators/audit_labels.py searches the",
            "handed bytes for every spelling of the true labels. The suite files themselves are",
            "frozen and keep their generator block, because that block is what makes regeneration",
            "a check.",
        ],
        "planted": planted,
    }
    text = json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    if not args.apply:
        print(f"dry run: would write {PROVENANCE} with {len(planted)} planted records "
              f"({len(text)} bytes)")
        return 0
    PROVENANCE.write_text(text)
    print(f"wrote {PROVENANCE} with {len(planted)} planted records, "
          f"sha256={hashlib.sha256(text.encode()).hexdigest()}")
    return 0


def stratum_of(graph_id: str) -> str:
    manifest = json.loads((SUITE / "manifest.json").read_text())
    for entry in manifest["graphs"]:
        if entry["graph_id"] == graph_id:
            return str(entry["stratum"])
    raise KeyError(graph_id)


def cmd_verify(args) -> int:
    problems: list[str] = []
    provenance = load_provenance()
    recorded = {item["graph_id"]: item for item in provenance["planted"]}

    shipped = {graph_id: path for _role, graph_id, path in shipped_graphs()}
    truth: dict[str, list[int]] = {}
    for graph_id, path in sorted(shipped.items()):
        result = planted_truth(path)
        if result is None:
            continue
        _document, _edges, labels = result
        truth[graph_id] = labels
        item = recorded.get(graph_id)
        if item is None:
            problems.append(f"{graph_id}: Planted graph has no provenance record")
            continue
        if item["planted_labels"] != labels:
            problems.append(f"{graph_id}: recorded labels are not the labels of the frozen graph "
                            "(stale provenance — this is finding F4)")
        if int(item.get("seed", -1)) != int(json.loads(path.read_text())["generator"]["seed"]):
            problems.append(f"{graph_id}: recorded seed is not the graph's generator.seed")

    # (2) no spelling of a true label vector occurs in the frozen data
    suite_text = {path: path.read_text() for path in sorted(SUITE.rglob("*.json")) if path.is_file()}
    hits = 0
    for graph_id, labels in sorted(truth.items()):
        for spelling, needle in needles_for(labels).items():
            for path, text in suite_text.items():
                if needle and needle in text:
                    hits += 1
                    problems.append(f"{graph_id}: {spelling} found in {path.relative_to(REPO)}")

    # (3) the candidate-facing view: exactly five keys, and no needle in it
    view_checks = 0
    for graph_id, path in sorted(shipped.items()):
        graph = e_star.read_graph(path)
        document = e_star.candidate_graph_document(graph)
        if sorted(document) != sorted(e_star.CANDIDATE_GRAPH_KEYS):
            problems.append(f"{graph_id}: candidate-facing view keys are {sorted(document)}")
        for forbidden in ("generator", "notes", "seed", "params"):
            if forbidden in document:
                problems.append(f"{graph_id}: candidate-facing view carries {forbidden!r}")
        text = e_star.canonical_json(document)
        for spelling, needle in needles_for(truth[graph_id]).items() if graph_id in truth else ():
            if needle and needle in text:
                problems.append(f"{graph_id}: {spelling} appears in the candidate-facing view")
        view_checks += 1

    print(f"planted graphs: {len(truth)}")
    print(f"provenance records: {len(recorded)}")
    print(f"suite JSON files scanned with {len(truth)} x 6 label spellings: {len(suite_text)}, "
          f"hits: {hits}")
    print(f"candidate-facing views checked: {view_checks} "
          f"(keys == {list(e_star.CANDIDATE_GRAPH_KEYS)})")
    if problems:
        print(f"FAIL ({len(problems)} problems):")
        for item in problems[:20]:
            print("  " + item)
        return 1
    print("PASS: the recorded labels are the labels of the frozen graphs, no spelling of them "
          "appears in suite/**/*.json, and the candidate-facing view carries only "
          "schema/graph_id/family/n/edges")
    print("NOTE: the suite file itself still reproduces the labels (that is what makes regeneration "
          "a check); the evaluator masks suite/** from a candidate and hands the view instead")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="the audit")
    verify.set_defaults(func=cmd_verify)
    refresh = sub.add_parser("refresh", help="rewrite provenance.json from the frozen suite")
    refresh.add_argument("--apply", action="store_true")
    refresh.set_defaults(func=cmd_refresh)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
