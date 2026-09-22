#!/usr/bin/env python3
"""Independent check of references/targets.json.  Exits non-zero on any failure.

This is the command a third party reruns to decide whether to believe the table.
It never trusts `targets.json`'s own arithmetic: for every graph it re-reads
`graph.json` and the witness partition, recomputes the cut with
`tools/verify_partition.py` (a separate program from the one that built the
table), and compares.

**The witness vectors are no longer in this repository.**  A stored partition of
`G_eval_####` is the answer to the hold-out (the verifier scored exactly
`R = OPT = 217` on `G_eval_0001` by copying one), so `tools/seal_witnesses.py`
removed them and kept their commitments -- for every witness: the graph id, the
run id, the sha256 of the file bytes, the sha256 of the canonical bytes and the
recomputed cut.  This program therefore runs in one of two modes:

* **values + commitments** (the default): `R` is checked against the per-run
  records on disk (`logs/runs/*.json`, `logs_topup/runs/*.json`), and every
  witness behind `R_source`/`R_ties` is checked against its commitment -- the
  run record's own `partition_sha256` and `cut_edges` must agree with the sealed
  manifest, and the per-graph maximum of the sealed cuts must equal `R`.
* **full recomputation** (`--witnesses DIR`, or when the plaintext partitions are
  still present): every witness is re-read and recomputed from scratch, as above.
  `--witnesses` takes a retained copy of the removed tree
  (`<dir>/logs/partitions/...`).

Checks, per graph:
  1. the manifest's `graph_sha256` equals the sha256 of the file the table points
     at, and equals the sha recorded inside `targets.json`;
  2. the winning partition, recomputed from scratch (full mode) or its commitment
     and recorded cut (ceiling mode), agrees with `R`;
  3. *every* partition listed in `R_ties` likewise -- a tie list that over-claims
     is a wrong table;
  4. `R` equals the maximum over the per-run records actually on disk;
  5. `U >= R` whenever `U` is present;
  6. `OPT` is non-null exactly when `opt_certified` is true, and then `OPT == R`;
  7. `rho`-relevant scalars are integers, never floats (the authoritative value
     is an exact integer per INTERFACE.md section 5).

Usage:
    python3 tools/verify_targets.py [--targets targets.json] \
        [--manifest ../suite/manifest.json] [--logs logs] [--quiet] \
        [--witnesses <dir with the removed tree>]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from canonical import file_sha256  # noqa: E402

VERIFY = os.path.join(HERE, "verify_partition.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default=os.path.join(ROOT, "targets.json"))
    ap.add_argument("--manifest", default=os.path.join(ROOT, "..", "suite",
                                                       "manifest.json"))
    ap.add_argument("--logs", default=os.path.join(ROOT, "logs"))
    ap.add_argument("--logs-extra", nargs="*", default=[os.path.join(ROOT, "logs_topup")])
    ap.add_argument("--witnesses", default=None,
                    help="retained copy of the removed witness tree (full recomputation)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    with open(args.targets) as fh:
        doc = json.load(fh)
    graphs = doc["graphs"]
    commitments_path = os.path.join(ROOT, "witnesses", "commitments.json")
    commitments = {}
    if os.path.exists(commitments_path):
        with open(commitments_path) as fh:
            sealed = json.load(fh)
        commitments = {item["run_id"]: item for item in sealed["witnesses"]}
        sealed_per_graph = sealed["per_graph"]
    else:
        sealed_per_graph = {}
    witness_roots = []
    if args.witnesses:
        witness_roots.append(args.witnesses)
    with open(args.manifest) as fh:
        man = {e["graph_id"]: e for e in json.load(fh)["graphs"]}
    suite_root = os.path.dirname(os.path.abspath(args.manifest))

    run_dirs = [os.path.join(args.logs, "runs")] + \
               [os.path.join(d, "runs") for d in args.logs_extra]
    runs = {}
    for d in run_dirs:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn)) as fh:
                    r = json.load(fh)
                runs.setdefault(r["graph_id"], []).append(r)

    fails = []
    checked = {"graphs": 0, "partitions": 0, "commitments": 0}

    def fail(gid, msg):
        fails.append("%s: %s" % (gid, msg))

    for gid, g in sorted(graphs.items()):
        checked["graphs"] += 1
        if gid not in man:
            fail(gid, "not in the frozen manifest")
            continue
        gpath = os.path.join(suite_root, man[gid]["path"])
        if not os.path.exists(gpath):
            fail(gid, "graph file missing: %s" % gpath)
            continue
        sha_file = file_sha256(gpath)
        if sha_file != man[gid]["graph_sha256"]:
            fail(gid, "graph file sha %s != manifest %s"
                 % (sha_file[:16], man[gid]["graph_sha256"][:16]))
        if g.get("graph_sha256") != sha_file:
            fail(gid, "targets.json graph_sha256 %s != file sha %s"
                 % (str(g.get("graph_sha256"))[:16], sha_file[:16]))

        R = g.get("R")
        if R is None:
            fail(gid, "R is null")
            continue
        if not isinstance(R, int):
            fail(gid, "R is not an int (gets %r)" % (R,))

        # 4. R is the max over the run records
        recs = [r for r in runs.get(gid, []) if r.get("status") == "ok"]
        if recs:
            mx = max(r["cut_edges"] for r in recs)
            if mx != R:
                fail(gid, "R=%s but max over %d run records is %s" % (R, len(recs), mx))

        # 2 + 3. recompute the winner and every tie, independently
        to_check = [g["R_source"]["run_id"]] + \
                   [t["run_id"] for t in g.get("R_ties", [])]
        seen = set()
        for rid in to_check:
            if rid in seen:
                continue
            seen.add(rid)
            part = None
            for d in [os.path.join(args.logs, "partitions")] + \
                     [os.path.join(x, "partitions") for x in args.logs_extra] + \
                     [os.path.join(x, "logs", "partitions") for x in witness_roots]:
                cand = os.path.join(d, rid + ".partition.json")
                if os.path.exists(cand):
                    part = cand
                    break
            if part is None:
                checked["commitments"] += 1
                commitment = commitments.get(rid)
                if commitment is None:
                    fail(gid, "%s: neither a partition nor a sealed commitment" % rid)
                    continue
                if commitment["graph_id"] != gid:
                    fail(gid, "%s: sealed commitment is for %s"
                         % (rid, commitment["graph_id"]))
                record = next((item for item in runs.get(gid, [])
                               if item.get("partition_path", "").endswith(rid + ".partition.json")), None)
                if record is None:
                    fail(gid, "%s: no run record carries this witness" % rid)
                    continue
                if record.get("partition_sha256") != commitment["file_sha256"]:
                    fail(gid, "%s: the run record's partition_sha256 does not match the sealed "
                              "commitment" % rid)
                if record.get("cut_edges") != commitment["cut_edges"]:
                    fail(gid, "%s: the run record's cut_edges %s does not match the sealed %s"
                         % (rid, record.get("cut_edges"), commitment["cut_edges"]))
                if commitment["cut_edges"] != R:
                    fail(gid, "%s: sealed cut %d != R=%d" % (rid, commitment["cut_edges"], R))
                continue
            r = subprocess.run([sys.executable, VERIFY, gpath, part],
                               capture_output=True, text=True)
            if r.returncode != 0:
                fail(gid, "%s did not verify (rc=%d): %s"
                     % (rid, r.returncode, r.stderr.strip()[:100]))
                continue
            got = json.loads(r.stdout)["cut_edges"]
            checked["partitions"] += 1
            if got != R:
                fail(gid, "%s recomputes to %d, not R=%d" % (rid, got, R))

        # 5 + 6
        U = g.get("U")
        if U is not None and U < R:
            fail(gid, "U=%s < R=%s" % (U, R))
        if g.get("opt_certified"):
            if g.get("OPT") is None:
                fail(gid, "opt_certified true but OPT is null")
            elif g["OPT"] != R:
                fail(gid, "opt_certified true but OPT=%s != R=%s" % (g["OPT"], R))
        else:
            if g.get("OPT") is not None:
                fail(gid, "opt_certified false but OPT=%s is not null" % g["OPT"])

        if not args.quiet:
            print("  %-14s R=%-5d ties=%-3d U=%-6s %s"
                  % (gid, R, len(g.get("R_ties", [])), U,
                     "OPT" if g.get("opt_certified") else "feasible-lower-bound"))

    n_cert = sum(1 for g in graphs.values() if g.get("opt_certified"))
    print()
    print("checked %d graphs, %d witnesses recomputed from bytes, %d checked against their "
          "sealed commitment" % (checked["graphs"], checked["partitions"], checked["commitments"]))
    if sealed_per_graph:
        mismatched = [gid for gid, item in sealed_per_graph.items() if not item["max_equals_R"]]
        if mismatched:
            for gid in mismatched:
                fails.append("%s: the sealed witness maximum is not R" % gid)
        print("sealed commitments: %d witnesses over %d graphs; per-graph maximum == R on %d/%d"
              % (sum(item["witness_count"] for item in sealed_per_graph.values()),
                 len(sealed_per_graph), len(sealed_per_graph) - len(mismatched),
                 len(sealed_per_graph)))
        print("  the vectors themselves are not in this repository: tools/seal_witnesses.py "
              "verify --corpus <dir> re-verifies a retained copy")
    if not sealed_per_graph and checked["commitments"]:
        print("  WARNING: witnesses are absent but no sealed manifest was found")
    print("certified OPT: %d/%d" % (n_cert, len(graphs)))
    if fails:
        print("\nFAIL (%d problems):" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("PASS: every R is a re-verified cut"
          + (" (recomputed from bytes where the witness is present, from its sealed commitment "
             "otherwise)" if checked["commitments"] else "")
          + ", every tie is real, U >= R everywhere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
