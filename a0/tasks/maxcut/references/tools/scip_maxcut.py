#!/usr/bin/env python3
"""Optional exact certification attempt with SCIP (offline, already installed).

Model (standard edge formulation of Max-Cut, unit weights):

    max  sum_e y_e
    s.t. y_e <= x_u + x_v          for every edge e = (u,v)
         y_e <= 2 - x_u - x_v      for every edge e = (u,v)
         x in {0,1}^n, y in {0,1}^m

Because the objective pushes y up, y_e = 1 exactly when x_u != x_v.

This is the honest certification attempt required by the assignment.  It is NOT
expected to certify everything: n = 128 with up to 713 edges, and the LP
relaxation of this formulation is weak.  The script therefore reports three
things per graph:

  * `status`: "certified_optimal" only when SCIP closes the gap, else
    "not_certified";
  * `dual_bound`: SCIP's upper bound at the end (a rigorous-in-tolerance bound);
  * `primal_bound`: SCIP's best feasible value, cross-checked against R_i.

An optional strengthening (`--triangles`, on by default) adds the odd-cycle
inequality y_uv + y_vw + y_wu <= 2 for every triangle.  Those are valid for
Max-Cut and are the standard cheap strengthening of this formulation; on these
graphs there are at most a few hundred triangles, so they cost almost nothing.
Each log records which formulation was used.

Nothing here is used to relabel an uncertified value as optimal.

Usage:
    python3 scip_maxcut.py --manifest ../suite/manifest.json --roles dev \
        --out scip/dev --limit 120 --jobs 6 [--graphs G_dev_0001 ...]
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from canonical import (cut_edges_exact, file_sha256, load_graph,  # noqa: E402
                       write_partition)

SCIP = "/usr/bin/scip"


def write_lp(graph, path, triangles=True):
    n = graph["n"]
    edges = graph["edges"]
    idx = {(u, v): k for k, (u, v) in enumerate(edges)}
    lines = ["Maximize", " obj: " + " + ".join("y%d" % k for k in range(len(edges)))
             if edges else " obj: 0"]
    lines.append("Subject To")
    for k, (u, v) in enumerate(edges):
        lines.append(" c%d_lo: y%d - x%d - x%d <= 0" % (k, k, u, v))
        lines.append(" c%d_hi: y%d + x%d + x%d <= 2" % (k, k, u, v))
    n_tri = 0
    if triangles and edges:
        adj = {i: set() for i in range(n)}
        for u, v in edges:
            adj[u].add(v)
            adj[v].add(u)
        seen = set()
        for u, v in edges:
            common = adj[u] & adj[v]
            for w in common:
                tri = tuple(sorted((u, v, w)))
                if tri in seen:
                    continue
                seen.add(tri)
                a, b, c = tri
                ka = idx[(min(a, b), max(a, b))]
                kb = idx[(min(b, c), max(b, c))]
                kc = idx[(min(a, c), max(a, c))]
                lines.append(" t%d: y%d + y%d + y%d <= 2" % (n_tri, ka, kb, kc))
                n_tri += 1
    lines.append("Bounds")
    for i in range(n):
        lines.append(" x%d <= 1" % i)
    for k in range(len(edges)):
        lines.append(" y%d <= 1" % k)
    lines.append("Binary")
    lines.append(" " + " ".join("x%d" % i for i in range(n)))
    if edges:
        lines.append(" " + " ".join("y%d" % k for k in range(len(edges))))
    lines.append("End")
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    return n_tri


def parse_scip_log(text):
    primal = dual = gap = None
    for m in re.finditer(r"Primal Bound\s*:\s*([-\d.eE+]+)", text):
        primal = float(m.group(1))
    for m in re.finditer(r"Dual Bound\s*:\s*([-\d.eE+]+)", text):
        dual = float(m.group(1))
    for m in re.finditer(r"Gap\s*:\s*([-\d.eE+]+|infinite)", text):
        g = m.group(1)
        gap = None if g == "infinite" else float(g)
    solved = "problem is solved" in text or "optimal solution found" in text
    return primal, dual, gap, solved


def parse_scip_solution(text, n):
    """Read the 'display solution' block.  SCIP lists only nonzeros, as

        objective value:                                  224
        x0                                                  1 	(obj:0)

    so the assignment is x_i = 1 for every listed x_i, 0 otherwise.  Returns
    (objective, assignment) or (None, None).
    """
    idxs = []
    for m in re.finditer(r"^objective value:\s*([-\d.eE+]+)\s*$", text, re.M):
        obj = float(m.group(1))
        tail = text[m.end():]
        vals = {}
        for vm in re.finditer(r"^x(\d+)\s+([-\d.eE+]+)", tail, re.M):
            i = int(vm.group(1))
            if i >= n:
                break
            vals[i] = float(vm.group(2))
        if len(vals) < n:
            asm = [1 if vals.get(i, 0.0) > 0.5 else 0 for i in range(n)]
            idxs.append((obj, asm))
    return idxs[-1] if idxs else (None, None)


def run_graph(args):
    graph_path, graph_id, ref_R, outdir, limit, triangles = args
    os.makedirs(outdir, exist_ok=True)
    rec_path = os.path.join(outdir, graph_id + ".json")
    if os.path.exists(rec_path):
        try:
            with open(rec_path) as fh:
                prev = json.load(fh)
            if (prev.get("time_limit_s", 0) >= limit
                    and prev.get("graph_sha256") == file_sha256(graph_path)):
                return prev
        except Exception:
            pass
    lp = os.path.join(outdir, graph_id + ".lp")
    n_tri = write_lp(load_graph(graph_path), lp, triangles=triangles)
    log = os.path.join(outdir, graph_id + ".scip.log")
    cmds = [
        "read %s" % lp,
        "set limits time %g" % limit,
        "set display verblevel 4",
        "optimize",
        "display solution",
        "quit",
    ]
    argv = [SCIP]
    for c in cmds:
        argv += ["-c", c]
    t0 = time.time()
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=limit + 120)
    text = proc.stdout.decode("utf-8", "replace")
    with open(log, "w") as fh:
        fh.write(text)
    wall = time.time() - t0
    primal, dual, gap, solved = parse_scip_log(text)
    graph = load_graph(graph_path)
    obj, asm = parse_scip_solution(text, graph["n"])
    verified = None
    part_path = None
    part_sha = None
    if asm is not None:
        try:
            verified = cut_edges_exact(graph, asm)
            part_path = os.path.join(outdir, graph_id + ".partition.json")
            part_sha = write_partition(part_path, graph_id, asm)
        except ValueError:
            verified, part_path, part_sha = None, None, None
    rec = {
        "schema": "a0.maxcut.scip_attempt/v1",
        "graph_id": graph_id,
        "graph_path": graph_path,
        "graph_sha256": file_sha256(graph_path),
        "edges_total": len(graph["edges"]),
        "scip_version": "10.0.3 (SoPlex 8.0.3)",
        "formulation": ("edge + triangle odd-cycle inequalities" if triangles
                        else "edge only"),
        "triangle_inequalities": n_tri,
        "time_limit_s": limit,
        "wall_s": round(wall, 1),
        "primal_bound": primal,
        "dual_bound": dual,
        "gap": gap,
        "solved_to_optimality": bool(solved),
        "known_feasible_R": ref_R,
        "log_sha256": file_sha256(log),
        "primal_from_display_solution": obj,
        "primal_recomputed_cut": verified,
        "primal_recomputed_matches_scip": (verified is not None and obj is not None
                                           and abs(verified - obj) < 1e-6),
        "primal_partition_path": (os.path.relpath(part_path, os.path.dirname(outdir))
                                  if part_path else None),
        "primal_partition_sha256": part_sha,
    }
    if solved and dual is not None and primal is not None:
        # with unit weights the optimum is an integer
        opt = int(round(dual))
        rec["status"] = "certified_optimal"
        rec["OPT_scip"] = opt
        rec["agrees_with_R"] = (None if ref_R is None else bool(opt == ref_R))
    else:
        rec["status"] = "not_certified"
        rec["OPT_scip"] = None
        rec["dual_bound_floor"] = (int(math.floor(dual)) if dual is not None else None)
    with open(rec_path, "w") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--suite-root", default=None)
    ap.add_argument("--roles", nargs="*", default=["dev", "eval"])
    ap.add_argument("--graphs", nargs="*", default=None)
    ap.add_argument("--targets", default=None, help="targets.json for the R_i values")
    ap.add_argument("--out", default="scip")
    ap.add_argument("--limit", type=float, default=120.0)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--triangles", dest="triangles", action="store_true", default=True)
    ap.add_argument("--no-triangles", dest="triangles", action="store_false")
    args = ap.parse_args()

    with open(args.manifest) as fh:
        man = json.load(fh)
    root = args.suite_root or os.path.dirname(os.path.abspath(args.manifest))
    ref = {}
    if args.targets and os.path.exists(args.targets):
        with open(args.targets) as fh:
            for gid, e in json.load(fh)["graphs"].items():
                ref[gid] = e.get("R")
    entries = [e for e in man["graphs"] if e["role"] in args.roles]
    if args.graphs:
        entries = [e for e in entries if e["graph_id"] in args.graphs]
    jobs = [(os.path.join(root, e["path"]), e["graph_id"], ref.get(e["graph_id"]),
             args.out, args.limit, args.triangles) for e in entries]
    with cf.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for rec in pool.map(run_graph, jobs):
            print(json.dumps({k: rec.get(k) for k in
                              ("graph_id", "status", "dual_bound", "dual_bound_floor",
                               "primal_recomputed_cut", "wall_s",
                               "triangle_inequalities", "OPT_scip")}),
                  flush=True)


if __name__ == "__main__":
    main()
