#!/usr/bin/env python3
"""Two consequences I did not take on trust.

(1) The gate's frozen Outcomes carry `evaluator_source_sha256 4afff01f…`; the
    evaluator on disk is `dc6969ec…`. Does re-running the same (candidate, graph,
    θ) with the current E* still produce the same *number*? One dev graph, both
    roles, compared field by field.
(2) The harness-side score bound (F3's closure): what the service does with an
    override that is outside `[0, |E|]`, in both modes.

    python3 a0/verify/a1-final/v8_consequences.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MAXCUT = REPO / "a0/tasks/maxcut"
E_STAR = MAXCUT / "e_star.py"
GATES = MAXCUT / "gates"
SERVICE = REPO / "a0/a1/eval_service.py"
PY = sys.executable

results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # ---- (1) the gate's numbers against the current E* ---------------
        for role, directory in (("baseline", MAXCUT / "positive_control/baseline"),
                                ("pc", MAXCUT / "positive_control/pc")):
            stored_path = GATES / "outcomes/dev" / role / "G_dev_0001.outcome.json"
            stored = json.loads(stored_path.read_text(encoding="utf-8"))
            graph = MAXCUT / "suite/dev/G_dev_0001.json"
            out = tmp / f"{role}.outcome.json"
            proc = subprocess.run(
                [PY, str(E_STAR), "evaluate", "--candidate", str(directory), "--graph", str(graph),
                 "--seed", "1337", "--timeout", "10", "--out", str(out),
                 "--state-dir", str(tmp / f"estate-{role}")],
                cwd=str(REPO), capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                check(f"(1) {role}: E* re-ran", False, proc.stderr[-200:])
                continue
            fresh = json.loads(out.read_text(encoding="utf-8"))
            check(f"(1) {role}: the re-run books the same cut_edges",
                  fresh["cut_edges"] == stored["cut_edges"],
                  f"fresh {fresh['cut_edges']} vs frozen {stored['cut_edges']} (|E| {fresh['edges_total']})")
            check(f"(1) {role}: same status", fresh["status"] == stored["status"],
                  f"{fresh['status']} vs {stored['status']}")
            check(f"(1) {role}: same candidate_source_sha256",
                  fresh["candidate_source_sha256"] == stored["candidate_source_sha256"])
            check(f"(1) {role}: the evaluator digest differs, as recorded",
                  fresh["evaluator_source_sha256"] != stored["evaluator_source_sha256"],
                  f"fresh {fresh['evaluator_source_sha256'][:12]} vs frozen {stored['evaluator_source_sha256'][:12]}")
            differing = sorted(k for k in set(fresh) | set(stored)
                               if fresh.get(k) != stored.get(k))
            print(f"      fields differing from the frozen Outcome: {differing}")

        # ---- (2) the harness-side score bound ----------------------------
        graph = MAXCUT / "suite/dev/G_dev_0001.json"
        candidate = MAXCUT / "candidates/c02_ok_low_baseline"
        edges_total = len(json.loads(graph.read_text(encoding="utf-8"))["edges"])
        for mode, expect_value in (("bounded", None), ("labelled_implausible", 9999)):
            root = tmp / f"svc-{mode}"
            root.mkdir()
            override = root / "override.json"
            override.write_text(json.dumps({"cand_bound": 9999}), encoding="utf-8")
            request = root / "request.json"
            request.write_text(json.dumps({
                "schema": "a0.a1.eval_request/v1", "request_id": f"req-{mode}",
                "campaign_id": "C_a1final", "arm_id": "A_verify", "iteration": 1,
                "candidate_id": "cand_bound", "candidate_path": str(candidate),
                "graph_path": str(graph), "seed": 1337, "timeout_s": 10.0}, indent=1), encoding="utf-8")
            proc = subprocess.run(
                [PY, str(SERVICE), "evaluate", "--root", str(root),
                 "--override", str(override), "--override-mode", mode,
                 "--request", str(request)],
                cwd=str(REPO), capture_output=True, text=True, timeout=600)
            response = json.loads(proc.stdout or "{}")
            print(f"      [{mode}] value={response.get('value')} handed={response.get('handed_value')} "
                  f"true={response.get('true_value')} plausibility="
                  f"{json.dumps(response.get('plausibility'))[:160]}")
            if mode == "bounded":
                check("(2) bounded mode: a 9999 override on |E|=265 publishes nothing",
                      response.get("value") is None and response.get("handed_value") is None,
                      f"value={response.get('value')} handed={response.get('handed_value')}")
                check("(2) bounded mode: the true value is still recorded",
                      response.get("true_value") == 132, str(response.get("true_value")))
                check("(2) bounded mode: the refusal is named and booked",
                      (response.get("plausibility") or {}).get("verdict") == "refused_out_of_bound"
                      and response.get("override_rejected") is True
                      and response.get("status") == "error"
                      and (response.get("outcome") or {}).get("cut_edges") is None,
                      f"verdict={(response.get('plausibility') or {}).get('verdict')} "
                      f"rejected={response.get('override_rejected')} status={response.get('status')}")
            else:
                check("(2) labelled mode: the out-of-range value is published",
                      response.get("value") == 9999, f"value={response.get('value')}")
                pl = response.get("plausibility") or {}
                check("(2) labelled mode: it is labelled out-of-bound, with the true value beside it",
                      pl.get("verdict") == "accepted_labelled_out_of_bound"
                      and pl.get("within_bound") is False and pl.get("value") == 9999
                      and response.get("true_value") == 132,
                      f"verdict={pl.get('verdict')} within_bound={pl.get('within_bound')} "
                      f"true={response.get('true_value')}")

    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
