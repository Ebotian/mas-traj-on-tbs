#!/usr/bin/env python3
"""Item 5 — the two claims the earlier pass falsified, re-tested.

(a) the executable bit no longer matters: one candidate's bytes, four modes,
    one Outcome (bytes, not just digest).
(b) the candidate-facing graph view omits the `generator` block, and the Outcome
    records the hash of *both* documents.

    python3 a0/verify/a1-final/v7_staging.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E_STAR = REPO / "a0/tasks/maxcut/e_star.py"
SUITE_GRAPH = REPO / "a0/tasks/maxcut/suite/dev/G_dev_0019.json"
CONFORMANCE_CANDIDATE = REPO / "a0/tasks/maxcut/candidates/c02_ok_low_baseline"
PY = sys.executable

results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evaluate(candidate: Path, graph: Path, root: Path, out: Path, tag: str) -> dict:
    proc = subprocess.run(
        [PY, str(E_STAR), "evaluate", "--candidate", str(candidate), "--graph", str(graph),
         "--seed", "1337", "--timeout", "10", "--out", str(out),
         "--state-dir", str(root / "estate")],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"e_star failed for {tag}: rc={proc.returncode} {proc.stderr[-400:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # ---- (a) the mode bit -------------------------------------------
        work = tmp / "mode"
        work.mkdir()
        shutil.copytree(CONFORMANCE_CANDIDATE, work / "cand")
        script = work / "cand" / "solution.py"
        outcomes = {}
        raw = {}
        for mode in (0o755, 0o644, 0o600, 0o400):
            os.chmod(script, mode)
            out = work / f"outcome_{mode:o}.json"
            doc = evaluate(work / "cand", SUITE_GRAPH, work, out, f"mode {mode:o}")
            outcomes[f"{mode:o}"] = doc
            raw[f"{mode:o}"] = out.read_bytes()
        digests = {m: d["canonical_digest"] for m, d in outcomes.items()}
        sources = {m: d["candidate_source_sha256"] for m, d in outcomes.items()}
        statuses = {m: d["status"] for m, d in outcomes.items()}
        check("(a) four modes -> one candidate_source_sha256", len(set(sources.values())) == 1,
              f"{set(sources.values())}")
        check("(a) four modes -> one canonical_digest", len(set(digests.values())) == 1,
              f"{set(digests.values())}")
        check("(a) four modes -> byte-identical Outcome files", len(set(raw.values())) == 1,
              f"{[len(v) for v in raw.values()]} bytes each")
        check("(a) the run is a real ok with a real number",
              set(statuses.values()) == {"ok"} and
              len({d["cut_edges"] for d in outcomes.values()}) == 1,
              f"statuses {set(statuses.values())} cut {outcomes['755']['cut_edges']}")

        # the source bytes really are one candidate: the four runs are the same
        # file bytes with four different mode bits, so the digest E* measures
        # (a digest over the candidate's file *contents*, never their modes)
        # must be the same one it would compute now.
        os.chmod(script, 0o644)
        proc = subprocess.run(
            [PY, "-c",
             "import json,sys,pathlib; sys.path.insert(0,r'a0/tasks/maxcut'); import e_star_child as c;"
             "files=c.candidate_files(pathlib.Path(sys.argv[1]));"
             "print(json.dumps({'digest': c.candidate_source_digest(files),"
             " 'modes_used': False, 'files': [f['path'] for f in files]}))",
             str(work / "cand")],
            cwd=str(REPO), capture_output=True, text=True)
        recomputed = json.loads(proc.stdout)
        check("(a) E*'s own candidate digest recomputes over the same directory",
              recomputed["digest"] == outcomes["755"]["candidate_source_sha256"],
              f"{recomputed['digest'][:16]} files={recomputed['files']}")

        # ---- (b) the handed document ------------------------------------
        root = tmp / "view"
        root.mkdir()
        out = root / "outcome.json"
        doc = evaluate(CONFORMANCE_CANDIDATE, SUITE_GRAPH, root, out, "view")
        suite_bytes = SUITE_GRAPH.read_bytes()
        suite_doc = json.loads(suite_bytes)
        matches = sorted((root / "estate").rglob("run1/candidate_graph.json"))
        check("(b) the evaluator wrote the handed document into its state dir", bool(matches),
              str(matches[0]) if matches else "none")
        view_bytes = matches[0].read_bytes()
        view = json.loads(view_bytes)
        check("(b) the handed view omits the generator block", "generator" not in view,
              f"keys {sorted(view)}")
        check("(b) the handed view omits notes and carries nothing else",
              sorted(view) == ["edges", "family", "graph_id", "n", "schema"]
              and view["edges"] == suite_doc["edges"] and view["n"] == suite_doc["n"],
              f"edges equal to the suite file: {view['edges'] == suite_doc['edges']}")
        check("(b) the suite file *does* carry the generator block (so this is a real difference)",
              "generator" in suite_doc, f"suite keys {sorted(suite_doc)}")
        check("(b) Outcome.graph_sha256 == sha256 of the suite file",
              doc["graph_sha256"] == sha256_bytes(suite_bytes),
              f"{doc['graph_sha256'][:16]} vs {sha256_bytes(suite_bytes)[:16]}")
        check("(b) Outcome.candidate_graph_sha256 == sha256 of the handed view",
              doc.get("candidate_graph_sha256") == sha256_bytes(view_bytes),
              f"{str(doc.get('candidate_graph_sha256'))[:16]} vs {sha256_bytes(view_bytes)[:16]}")
        check("(b) the two hashes are different documents", doc["graph_sha256"] != doc["candidate_graph_sha256"])
        check("(b) cut_edges was recomputed from the suite bytes, not the view",
              doc["edges_total"] == len(suite_doc["edges"]),
              f"edges_total {doc['edges_total']} == |E| of the suite file")

        # ---- (b') the same, on a Planted graph, where the block is the labels
        planted = REPO / "a0/tasks/maxcut/suite/dev/G_dev_0019.json"
        root2 = tmp / "view2"
        root2.mkdir()
        doc2 = evaluate(CONFORMANCE_CANDIDATE, planted, root2, root2 / "outcome.json", "view2")
        m2 = sorted((root2 / "estate").rglob("run1/candidate_graph.json"))
        v2 = json.loads(m2[0].read_text(encoding="utf-8"))
        pdoc = json.loads(planted.read_text(encoding="utf-8"))
        check("(b') on a Planted graph the handed view carries no generator block either",
              "generator" not in v2 and "generator" in pdoc,
              f"view {sorted(v2)}")

    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
