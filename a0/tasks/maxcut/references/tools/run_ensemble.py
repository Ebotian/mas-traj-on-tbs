#!/usr/bin/env python3
"""Reference-target ensemble: six diverse MQLib Max-Cut heuristics x 5 seeds.

What this produces
------------------
For every (graph, heuristic, seed) triple it runs MQLib for a fixed 30 s budget,
converts the printed +-1 assignment into a canonical a0.maxcut.partition/v1
object, and then -- this is the point -- **recomputes the cut independently**
from graph.json + partition.json with integer arithmetic.  MQLib's own reported
objective is recorded only as a cross-check, never as the authoritative value
(INTERFACE.md sections 4, 5).

The per-graph reference target R_i is the maximum recomputed cut over all runs
for that graph.

Everything is written per-run to disk before the run is considered done, so the
driver is resumable: rerunning skips any (graph, heuristic, seed) whose record
already exists with status "ok".

Usage
-----
    python3 run_ensemble.py --binary /tmp/mcwork/MQLib/bin/MQLib \
        --graphs <path-to-graph.json> [<path> ...] \
        --outdir logs --jobs 11 --time-limit 30

    # or, to take the graph list from a suite manifest:
    python3 run_ensemble.py --binary ... --manifest <manifest.json> --roles dev eval
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from canonical import (cut_edges_exact, cut_fraction_display, file_sha256,  # noqa: E402
                       load_graph, validate_graph, write_partition)

HEURISTICS = ["BURER2002", "FESTA2002GPR", "FESTA2002VNSPR",
              "DUARTE2005", "LAGUNA2009HCE", "DESOUSA2013"]
SEEDS = [1337, 2718, 31415, 4242, 65521]
TIME_LIMIT_S = 30.0


def mqlib_input_path(graph, scratch):
    return os.path.join(scratch, graph["graph_id"] + ".txt")


def ensure_mqlib_input(graph, graph_path, scratch):
    path = mqlib_input_path(graph, scratch)
    if not os.path.exists(path):
        from to_mqlib import write_mqlib_input
        write_mqlib_input(graph, path)
    return path


def parse_mqlib_stdout(text):
    """Return (reported_objective, assignment) or (None, None).

    Layout of `MQLib ... -ps` stdout:
        <runtime_limit>,<heur>,"<file>",<best>,<wall>,<history>
        <blank>
        Solution:
        <n space separated values from {1,-1}>
    """
    reported, assignment = None, None
    lines = text.splitlines()
    for ln in lines:
        parts = ln.split(",")
        if len(parts) >= 4 and parts[1].strip('"') and parts[3].strip():
            try:
                reported = float(parts[3])
            except ValueError:
                reported = None
    for i, ln in enumerate(lines):
        if ln.strip() == "Solution:" and i + 1 < len(lines):
            toks = lines[i + 1].split()
            try:
                vals = [int(t) for t in toks]
            except ValueError:
                return reported, None
            if vals and all(v in (1, -1) for v in vals):
                # +1 -> part 0, -1 -> part 1 (fixed, documented convention)
                assignment = [0 if v == 1 else 1 for v in vals]
            return reported, assignment
    return reported, None


def run_one(job):
    """Execute a single (graph, heuristic, seed) run.  Never raises."""
    (graph_path, graph_id, heuristic, seed, outdir, scratch, binary,
     time_limit, grace) = job
    run_id = "%s__%s__s%d" % (graph_id, heuristic, seed)
    rec_path = os.path.join(outdir, "runs", run_id + ".json")
    raw_path = os.path.join(outdir, "raw", run_id + ".stdout.txt")
    part_path = os.path.join(outdir, "partitions", run_id + ".partition.json")
    if os.path.exists(rec_path):
        with open(rec_path) as fh:
            prev = json.load(fh)
        if prev.get("status") == "ok":
            return rec_path, True

    graph = load_graph(graph_path)
    ensure_mqlib_input(graph, graph_path, scratch)
    tl = mqlib_input_path(graph, scratch)

    cmd = [binary, "-h", heuristic, "-fM", tl, "-r", str(time_limit),
           "-s", str(seed), "-ps"]
    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=time_limit + grace)
        out = proc.stdout.decode("utf-8", "replace")
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", "replace")
        exit_code = None
        timed_out = True
    wall_ms = int((time.time() - t0) * 1000)

    with open(raw_path + ".tmp", "w") as fh:
        fh.write(out)
    os.replace(raw_path + ".tmp", raw_path)

    reported, assignment = parse_mqlib_stdout(out)
    rec = {
        "schema": "a0.maxcut.reference.run/v1",
        "graph_id": graph_id,
        "graph_path": graph_path,
        "graph_sha256": file_sha256(graph_path),
        "heuristic": heuristic,
        "seed": seed,
        "time_limit_s": time_limit,
        "tool": "MQLib",
        "command": cmd,
        "interpreted": {"exit_code": exit_code, "wall_ms": wall_ms,
                        "timed_out": timed_out},
        "mqlib_reported_objective": reported,
        "raw_stdout_sha256": file_sha256(raw_path),
    }
    if exit_code != 0 or assignment is None or len(assignment) != graph["n"]:
        rec.update({"status": "error", "cut_edges": None, "cut_fraction": None,
                    "failure_kind": ("timeout" if timed_out else
                                     "no_solution_printed" if assignment is None
                                     else "nonzero_exit")})
    else:
        cut = cut_edges_exact(graph, assignment)
        write_partition(part_path, graph_id, assignment)
        rec.update({
            "status": "ok",
            "cut_edges": cut,
            "cut_fraction": cut_fraction_display(cut, len(graph["edges"])),
            "edges_total": len(graph["edges"]),
            "partition_path": os.path.relpath(part_path, os.path.dirname(outdir)),
            "partition_sha256": file_sha256(part_path),
            "mqlib_reported_matches_recomputed": (
                reported is not None and int(round(reported)) == cut),
        })
    with open(rec_path + ".tmp", "w") as fh:
        json.dump(rec, fh, sort_keys=True)
        fh.write("\n")
    os.replace(rec_path + ".tmp", rec_path)
    return rec_path, False


def build_jobs(graph_paths, outdir, scratch, binary, time_limit, grace,
               heuristics=None, seeds=None):
    heuristics = list(HEURISTICS if heuristics is None else heuristics)
    seeds = list(SEEDS if seeds is None else seeds)
    jobs = []
    for gp in graph_paths:
        g = load_graph(gp)
        ok, why = validate_graph(g)
        if not ok:
            raise SystemExit("graph %s is not canonical: %s" % (gp, why))
        for h in heuristics:
            for s in seeds:
                jobs.append((gp, g["graph_id"], h, s, outdir, scratch, binary,
                             time_limit, grace))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True)
    ap.add_argument("--graphs", nargs="*", default=[])
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--suite-root", default=None,
                    help="root that manifest 'path' fields are relative to")
    ap.add_argument("--roles", nargs="*", default=["dev", "eval"])
    ap.add_argument("--outdir", default="logs")
    ap.add_argument("--scratch", default="/tmp/mcwork/inputs")
    ap.add_argument("--jobs", type=int, default=11)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT_S)
    ap.add_argument("--heuristics", nargs="*", default=None,
                    help="subset of %s (default: all)" % ",".join(HEURISTICS))
    ap.add_argument("--seeds", nargs="*", type=int, default=None,
                    help="subset of %s (default: all)" % ",".join(map(str, SEEDS)))
    ap.add_argument("--grace", type=float, default=20.0)
    args = ap.parse_args()

    graph_paths = list(args.graphs)
    if args.manifest:
        with open(args.manifest) as fh:
            man = json.load(fh)
        root = args.suite_root or os.path.dirname(os.path.abspath(args.manifest))
        for e in man["graphs"]:
            if e["role"] in args.roles:
                graph_paths.append(os.path.join(root, e["path"]))
    if not graph_paths:
        raise SystemExit("no graphs given")
    graph_paths = sorted(set(graph_paths))

    outdir = os.path.abspath(args.outdir)
    for sub in ("runs", "raw", "partitions"):
        os.makedirs(os.path.join(outdir, sub), exist_ok=True)
    os.makedirs(args.scratch, exist_ok=True)

    jobs = build_jobs(graph_paths, outdir, args.scratch, os.path.abspath(args.binary),
                      args.time_limit, args.grace, args.heuristics, args.seeds)
    print("graphs=%d jobs=%d workers=%d time_limit=%.0fs"
          % (len(graph_paths), len(jobs), args.jobs, args.time_limit), flush=True)

    t0 = time.time()
    done = skipped = failed = 0
    with cf.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(run_one, j): j for j in jobs}
        for fut in cf.as_completed(futs):
            try:
                rec_path, was_skipped = fut.result()
            except Exception as exc:  # pragma: no cover - defensive
                failed += 1
                print("WORKER ERROR", futs[fut][2:4], repr(exc), flush=True)
                continue
            done += 1
            skipped += int(was_skipped)
            if done % 25 == 0 or done == len(jobs):
                el = time.time() - t0
                print("progress %d/%d (cached=%d) elapsed=%.0fs eta=%.0fs"
                      % (done, len(jobs), skipped, el,
                         el / max(done - skipped, 1) * max(len(jobs) - done, 0)),
                      flush=True)
    print("DONE jobs=%d worker_errors=%d elapsed=%.0fs" % (done, failed, time.time() - t0))


if __name__ == "__main__":
    main()
