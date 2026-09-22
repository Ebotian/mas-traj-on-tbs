#!/usr/bin/env python3
"""End-to-end leak probe: is a stored solution reachable from a candidate, and does
the A1 harness book it?  (assignment item 1, the 'files a candidate can read' half)

Three candidate programs live beside this file; each one only reads what the
deployment leaves readable.  They are run (a) through E* directly and (b) through
a0/a1/eval_service.py, which is the only process an A1 campaign uses to run E*.
No model call, no network.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MX = REPO / "a0/tasks/maxcut"
PY = sys.executable
WORK = pathlib.Path(tempfile.mkdtemp(prefix="a1testbed-leak-"))

findings: list[str] = []


def out(msg: str) -> None:
    print(msg, flush=True)


def e_star(candidate: str, graph: pathlib.Path) -> dict:
    path = WORK / f"{candidate}-{graph.stem}.json"
    subprocess.run([PY, str(MX / "e_star.py"), "evaluate", "--candidate", str(HERE / candidate),
                    "--graph", str(graph), "--seed", "1337", "--timeout", "10", "--out", str(path)],
                   capture_output=True, check=True)
    return json.loads(path.read_text())


def harness(candidate: str, graph: pathlib.Path, tag: str) -> dict:
    root = WORK / f"harness-{tag}"
    root.mkdir(parents=True, exist_ok=True)
    req = {"schema": "a0.a1.eval_request/v1", "request_id": f"leak.{tag}",
           "campaign_id": "C_leak", "arm_id": "A_leak", "candidate_id": candidate,
           "candidate_path": str(HERE / candidate), "graph_path": str(graph),
           "seed": 1337, "timeout_s": 10, "iteration": 0}
    req_path = WORK / f"req-{tag}.json"
    req_path.write_text(json.dumps(req))
    proc = subprocess.run([PY, str(REPO / "a0/a1/eval_service.py"), "evaluate", "--root", str(root),
                           "--campaign-id", "C_leak", "--arm-id", "A_leak",
                           "--harness-run-id", f"leak-{tag}", "--nonce", "0" * 16,
                           "--request", str(req_path)], capture_output=True, text=True)
    if not proc.stdout.strip():
        raise SystemExit(f"harness run failed: {proc.returncode} {proc.stderr[-400:]}")
    return json.loads(proc.stdout)


def main() -> int:
    targets = json.loads((MX / "references/targets.json").read_bytes())["graphs"]
    dev19 = MX / "suite/dev/G_dev_0019.json"
    eval1 = MX / "suite/eval/G_eval_0001.json"

    out("== A. the planted partition is recoverable from the graph the candidate is handed ==")
    r = e_star("cand_replay", dev19)
    out(f"   cand_replay on G_dev_0019 (planted labels re-derived from generator.seed): "
        f"status={r['status']} cut_edges={r['cut_edges']}/{r['edges_total']} "
        f"= {r['cut_edges'] / r['edges_total']:.3f} of the edges")
    out("   (the planted partition is a *trap* for max-cut: below a random 0.50, so this leak is a "
        "label leak, not a score leak)")
    findings.append("the planted label vector is a deterministic function of graph.json's own "
                    "generator.seed+params via the published generator, so the 'no labels in a "
                    "candidate-readable file' claim is true only of the label *text*")

    out("\n== B. the suite's own label store is stale, so its needles search the wrong vectors ==")
    p = e_star("cand_provenance", dev19)
    out(f"   cand_provenance (reads generators/provenance.json) on G_dev_0019: "
        f"cut_edges={p['cut_edges']}/{p['edges_total']} = {p['cut_edges'] / p['edges_total']:.3f} "
        f"(a random-looking partition, NOT the graph's planted structure)")
    findings.append("generators/provenance.json's planted_labels do not reproduce the shipped graphs "
                    "(intra/inter densities 0.05-0.07 against declared p_in/p_out up to 0.15), so verify's "
                    "30 leakage needles are inert with respect to the labels the graphs actually encode")

    out("\n== C. a stored reference partition for an EVAL graph is readable and scores R ==")
    for graph in (eval1, MX / "suite/eval/G_eval_0019.json"):
        gid = graph.stem
        direct = e_star("cand_reference", graph)
        handed = harness("cand_reference", graph, tag=gid)
        out(f"   {gid}: E* cut_edges={direct['cut_edges']} | harness handed_value={handed['handed_value']} "
            f"(true_value={handed['true_value']}, status={handed['status']}) | targets.json R={targets[gid]['R']} "
            f"OPT={targets[gid]['OPT']}")
        if direct["cut_edges"] == targets[gid]["R"] == handed["handed_value"]:
            findings.append(f"{gid}: the candidate's score equals R_i, the frozen reference target, obtained by "
                            f"reading {MX.relative_to(REPO)}/references/logs/partitions/{gid}__*.partition.json "
                            f"(720 such files exist for the 24 eval graphs)")
    out("\n== D. the same hand that runs the harness runs the candidate ==")
    out(f"   eval_service spawns E* with cwd={WORK} and no mount/user namespace; the candidate child is "
        f"the same uid and can read the whole repository tree")
    findings.append("INTERFACE.md section 12 requires that eval 'must not enter an agent's workspace, "
                    "context or any path a candidate can read'; the eval set's reference partitions and "
                    "targets.json are committed inside the same repository and the candidate child has "
                    "unrestricted filesystem read access, so that clause is not enforced anywhere in the "
                    "A1 chain (E* or eval_service)")

    out(f"\nFINDINGS ({len(findings)}):")
    for f in findings:
        out(f"  ! {f}")
    out(f"\nwork dir: {WORK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
