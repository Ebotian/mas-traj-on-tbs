#!/usr/bin/env python3
"""Item 4b — the suite's corrected leakage claim, re-derived and then attacked.

The audit's own needles are 6 spellings over `suite/**/*.json` plus the
candidate-facing view. This probe builds **8** spellings (adding the complement,
which is the same partition and therefore the same leak) and searches three
surfaces, two of which the audit does not cover:

* A `suite/**` — **every** file, any extension (the audit scans `*.json`);
* B the candidate-facing view of all 60 graphs (`e_star.candidate_graph_document`);
* C a broad surface: `a0/tasks/maxcut/**` and `a0/a1/**`, every file.

    python3 a0/verify/a1-final/v6_labels.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TASK = REPO / "a0/tasks/maxcut"
sys.path.insert(0, str(TASK / "generators"))
sys.path.insert(0, str(TASK))
import maxcut_suite as gen  # noqa: E402
import e_star  # noqa: E402

results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def spellings(labels: list[int]) -> dict[str, str]:
    k = max(labels) + 1
    classes: dict[int, list[int]] = {c: [] for c in range(k)}
    for i, c in enumerate(labels):
        classes[c].append(i)
    bits = 0
    for i, c in enumerate(labels):
        bits |= (c & 1) << i
    comp = [1 - x for x in labels]
    return {
        "01_compact": json.dumps(labels, separators=(",", ":")),
        "01_spaced": json.dumps(labels),
        "pm1_compact": json.dumps([2 * x - 1 for x in labels], separators=(",", ":")),
        "pm1_spaced": json.dumps([2 * x - 1 for x in labels]),
        "class_lists": json.dumps(list(classes.values()), separators=(",", ":")),
        "bitmask_dec": str(bits),
        "complement_compact": json.dumps(comp, separators=(",", ":")),
        "complement_spaced": json.dumps(comp),
    }


def scan(paths, needles):
    hits = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for graph_id, per_spelling in needles.items():
            for kind, needle in per_spelling.items():
                if needle and needle in text:
                    hits.append((str(path.relative_to(REPO)), graph_id, kind))
    return hits


def main() -> int:
    prov = json.loads((TASK / "generators/provenance.json").read_text(encoding="utf-8"))
    recorded = {r["graph_id"]: r["planted_labels"] for r in prov["planted"]}

    graphs = []
    for graph_set in ("dev", "eval", "calibration"):
        graphs.extend(sorted((TASK / "suite" / graph_set).glob("*.json")))
    planted = [p for p in graphs
               if json.loads(p.read_text(encoding="utf-8")).get("family") == "Planted"]

    # -- 1. ground truth: the labels are a function of the frozen bytes -----
    needles: dict[str, dict[str, str]] = {}
    replayed = {}
    for path in planted:
        doc = json.loads(path.read_text(encoding="utf-8"))
        block = doc["generator"]
        rng = gen.SplitMix64(int(block["seed"]))
        edges, labels = gen.GENERATORS[block["name"]](int(doc["n"]), block["params"], rng)
        edges = sorted((u, v) if u < v else (v, u) for u, v in edges)
        same = [[u, v] for u, v in edges] == [list(e) for e in doc["edges"]]
        check(f"replay reproduces the frozen edge list: {doc['graph_id']}", same,
              f"{len(edges)} edges")
        replayed[doc["graph_id"]] = labels
        needles[doc["graph_id"]] = spellings(labels)
    check("provenance.json's planted_labels == the replayed labels, all 15",
          all(replayed[g] == recorded[g] for g in replayed),
          f"{sum(1 for g in replayed if replayed[g] == recorded[g])}/{len(replayed)} agree")

    # -- 2. surface A: every file under suite/, any extension ---------------
    suite_files = [p for p in (TASK / "suite").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    hits_a = scan(suite_files, needles)
    non_json = [h for h in hits_a if not h[0].endswith(".json")]
    check("surface A: no label spelling in any file under suite/** (any extension)",
          not hits_a, f"{len(suite_files)} files scanned; hits: {hits_a[:4]}")

    # -- 3. surface B: the document the evaluator hands a candidate ---------
    views = []
    for path in graphs:
        doc = json.loads(path.read_text(encoding="utf-8"))
        views.append(json.dumps(e_star.candidate_graph_document(doc), sort_keys=True,
                                separators=(",", ":"), ensure_ascii=True))
    hits_b = []
    for graph_id, per_spelling in needles.items():
        for kind, needle in per_spelling.items():
            for i, text in enumerate(views):
                if needle in text:
                    hits_b.append((graphs[i].name, graph_id, kind))
    check("surface B: no label spelling in any candidate-facing view (60 graphs)",
          not hits_b, f"60 views; hits: {hits_b[:4]}")
    keysets = {tuple(sorted(json.loads(t).keys())) for t in views}
    check("surface B: every view carries exactly schema/graph_id/family/n/edges",
          keysets == {("edges", "family", "graph_id", "n", "schema")}, str(keysets))

    # -- 4. surface C: the broad task tree, every file ----------------------
    roots = [TASK, REPO / "a0/a1"]
    broad = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            parts = path.parts
            if "__pycache__" in parts or ".git" in parts:
                continue
            if "/a0/verify/" in str(path):
                continue
            broad.append(path)
    hits_c = scan(broad, needles)
    by_file: dict[str, int] = {}
    for rel, _, _ in hits_c:
        by_file[rel] = by_file.get(rel, 0) + 1
    check("surface C (literal substring, the audit's own method): the only file in the "
          "task tree carrying a true label spelling is the label store",
          set(by_file) <= {"a0/tasks/maxcut/generators/provenance.json"},
          f"{len(broad)} files scanned; carriers: {by_file}")
    for rel, n in sorted(by_file.items()):
        print(f"      {rel}: {n} spelling hit(s)")

    # -- 5. the same scan, whitespace-normalised ---------------------------
    # The audit's needles are JSON substrings, so they only match if the file
    # spells the vector exactly as `json.dumps` does on one line. provenance.json
    # is pretty-printed and its array is wrapped, so the literal scan misses the
    # label store itself. A leak that reformats the vector is a leak the audit
    # cannot see; this pass removes the formatting dependence.
    import re as _re

    def norm(text: str) -> str:
        return _re.sub(r"\s+", "", text)

    norm_needles = {g: {k: norm(v) for k, v in per.items()} for g, per in needles.items()}
    hits_norm = []
    for path in broad:
        try:
            text = norm(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        for graph_id, per in norm_needles.items():
            for kind, needle in per.items():
                if needle and needle in text:
                    hits_norm.append((str(path.relative_to(REPO)), graph_id, kind))
    carriers = {}
    for rel, gid, kind in hits_norm:
        carriers.setdefault(rel, set()).add(gid)
    check("surface C (whitespace-normalised): the label store is the only carrier",
          set(carriers) == {"a0/tasks/maxcut/generators/provenance.json"},
          f"{len(broad)} files; carriers: {{k: len(v) graphs for k, v in ...}} -> "
          + json.dumps({k: len(v) for k, v in sorted(carriers.items())}))
    check("surface A (whitespace-normalised): suite/** is still clean",
          not [h for h in hits_norm if h[0].startswith("a0/tasks/maxcut/suite/")],
          str([h for h in hits_norm if h[0].startswith("a0/tasks/maxcut/suite/")][:3]))

    # -- 6. the blind spot, demonstrated ------------------------------------
    # A file that carries the labels in any *other* formatting is invisible to a
    # substring scan. This is a control for the method, not a claim about the tree.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "leak.json"
        gid = "G_dev_0019"
        target.write_text(
            json.dumps({"graph_id": gid, "labels": needles[gid]["01_spaced"] and None,
                        "indented": [int(x) for x in needles[gid]["01_compact"]
                                     .strip("[]").split(",")]}, indent=2) + "\n",
            encoding="utf-8")
        literal = scan([target], {gid: needles[gid]})
        normalised = [1 for g in norm_needles if norm_needles[g]["01_spaced"] in norm(target.read_text())]
        check("control: a reformatted copy of the labels is invisible to the literal scan",
              not literal and normalised == [1],
              f"literal hits={len(literal)}, normalised hits={len(normalised)}")
    return 0


if __name__ == "__main__":
    main()
    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    sys.exit(1 if bad else 0)
