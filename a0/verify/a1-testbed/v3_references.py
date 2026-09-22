#!/usr/bin/env python3
"""Adversarial re-derivation of references/targets.json (assignment item 3).

No MQLib is run: this verifies what is *stored*.  Every R_i is recomputed from
the stored partitions with an independent cut routine, U ≥ R is checked, and
OPT is checked against the certification rule the file itself declares.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from collections import Counter
from fractions import Fraction

REPO = pathlib.Path(__file__).resolve().parents[3]
MX = REPO / "a0/tasks/maxcut"
REF = MX / "references"
SUITE = MX / "suite"

problems: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        problems.append(msg)


def cut_edges(edges, assignment) -> int:
    return sum(1 for u, v in edges if assignment[u] != assignment[v])


def main() -> int:
    targets = json.loads((REF / "targets.json").read_bytes())["graphs"]
    manifest = json.loads((SUITE / "manifest.json").read_bytes())
    by_id = {g["graph_id"]: g for g in manifest["graphs"]}
    print(f"graphs in targets.json: {len(targets)}")

    print("\n== A. every R_i recomputed from the stored partitions ==")
    stats = Counter()
    for gid, entry in sorted(targets.items()):
        meta = by_id[gid]
        graph = json.loads((SUITE / meta["path"]).read_bytes())
        edges = [tuple(e) for e in graph["edges"]]
        check_sha = hashlib.sha256((SUITE / meta["path"]).read_bytes()).hexdigest()
        if entry["graph_sha256"] != check_sha or entry["graph_sha256"] != meta["graph_sha256"]:
            # report once per graph, but do not spam the log
            problems.append(f"{gid}: graph_sha256 does not join to manifest/disk")
        check(entry["edges_total"] == len(edges), f"{gid}: edges_total {entry['edges_total']} == |E| {len(edges)}")
        check(entry["n"] == graph["n"] and entry["family"] == graph["family"],
              f"{gid}: n/family agree with the graph file")

        # every stored partition for this graph, recomputed here
        files = sorted((REF / "logs" / "partitions").glob(f"{gid}__*.partition.json"))
        files += sorted((REF / "logs_topup" / "partitions").glob(f"{gid}__*.partition.json"))
        cuts = {}
        for path in files:
            doc = json.loads(path.read_bytes())
            cuts[path.name] = cut_edges(edges, doc["assignment"])
        best = max(cuts.values()) if cuts else None
        stats["stored part files"] += len(files)
        if best is None:
            problems.append(f"{gid}: no stored partition")
            continue
        check(best == entry["R"], f"{gid}: max over {len(files)} stored partitions = {best} == R={entry['R']}")
        check(entry["R_ensemble"] == entry["R"], f"{gid}: R_ensemble == R")
        # the partition R names as its source, by digest and by value
        src = entry["R_source"]
        src_path = REF / src["log_dir"] / "partitions" / f"{src['run_id']}.partition.json"
        if not src_path.is_file():
            problems.append(f"{gid}: R_source partition {src_path} missing")
            continue
        raw = src_path.read_bytes()
        check(hashlib.sha256(raw).hexdigest() == src["partition_sha256"],
              f"{gid}: R_source partition_sha256 matches the file bytes")
        r_from_source = cut_edges(edges, json.loads(raw)["assignment"])
        check(r_from_source == entry["R"], f"{gid}: R_source partition recomputes to R ({r_from_source})")
        # the declared exact fraction is R/|E|, reduced
        frac = Fraction(entry["R"], entry["edges_total"])
        check(f"{frac.numerator}/{frac.denominator}" == entry["R_fraction_exact"],
              f"{gid}: R_fraction_exact == R/|E| reduced ({entry['R_fraction_exact']})")

        print(f"    {gid}: R={entry['R']} U={entry['U']} OPT={entry['OPT']} "
              f"from {len(files)} stored partitions, best={best}")

    print("\n== B. U ≥ R, and the certified/uncertified split ==")
    bad_ur = [g for g, e in targets.items() if not Fraction(e["U"]) >= Fraction(e["R"])]
    check(not bad_ur, f"U_i ≥ R_i for all {len(targets)} graphs (failures: {bad_ur})")
    cert = [g for g, e in targets.items() if e["OPT"] is not None]
    uncert = [g for g, e in targets.items() if e["OPT"] is None]
    print(f"    OPT non-null: {len(cert)}  OPT null: {len(uncert)}")
    check(len(cert) == 42, f"42 graphs certified (found {len(cert)})")
    check(all(targets[g]["OPT"] == targets[g]["R"] for g in cert), "OPT == R whenever OPT is non-null")
    check(all(targets[g]["U"] == targets[g]["R"] for g in cert),
          "every certified graph has U == R (the gap closes)")
    check(all(targets[g]["U"] > targets[g]["R"] for g in uncert),
          "every uncertified graph has U > R")
    check(all(targets[g]["opt_certified"] is (targets[g]["OPT"] is not None) for g in targets),
          "opt_certified == (OPT is not null)")
    # R_is_optimal is tri-state: True when certified, null (not False) when unknown
    check(all((targets[g]["R_is_optimal"] is True) == (targets[g]["U"] == targets[g]["R"]) for g in targets),
          "R_is_optimal is True exactly when U == R")
    check(all(targets[g]["R_is_optimal"] is None for g in uncert),
          "R_is_optimal is null (unknown), never a bare False, on the 18 uncertified graphs")
    check(all(targets[g]["U_consistent_with_R"] is (targets[g]["U"] >= targets[g]["R"]) for g in targets),
          "U_consistent_with_R == (U >= R)")

    print("\n== C. one certified case against the SCIP log on disk ==")
    sample = "G_dev_0001"
    entry = targets[sample]
    log = REF / "scip" / f"{sample}.scip.log"
    rec = json.loads((REF / "scip" / f"{sample}.json").read_bytes())
    text = log.read_text()
    check("problem is solved [optimal solution found]" in text, f"{sample}: SCIP log says optimal solution found")
    primal = float(re.search(r"Primal Bound\s*:\s*\+?([0-9.eE+-]+)", text).group(1))
    dual = float(re.search(r"Dual Bound\s*:\s*\+?([0-9.eE+-]+)", text).group(1))
    obj = int(re.search(r"objective value:\s+(\d+)", text).group(1))
    check(primal == dual == entry["R"], f"{sample}: log bounds {primal}/{dual} == R={entry['R']}")
    check(obj == entry["R"], f"{sample}: log objective value {obj} == R")
    check(rec["log_sha256"] == hashlib.sha256(log.read_bytes()).hexdigest(),
          f"{sample}: the SCIP record's log_sha256 matches the log bytes")
    # the SCIP primal partition, recomputed here
    graph = json.loads((SUITE / by_id[sample]["path"]).read_bytes())
    edges = [tuple(e) for e in graph["edges"]]
    primal_path = REF / "scip" / f"{sample}.partition.json"
    check(hashlib.sha256(primal_path.read_bytes()).hexdigest() == entry["scip"]["primal_partition_sha256"],
          f"{sample}: SCIP primal partition digest matches the record")
    recomputed = cut_edges(edges, json.loads(primal_path.read_bytes())["assignment"])
    check(recomputed == entry["R"], f"{sample}: SCIP primal partition recomputes to {recomputed} == R")
    # the LP file: one y variable per edge, objective = sum of y (the cut)
    lp = (REF / "scip" / f"{sample}.lp").read_text()
    yvars = set(re.findall(r"\by(\d+)\b", lp))
    xvars = set(re.findall(r"\bx(\d+)\b", lp))
    check(len(yvars) == len(edges), f"{sample}: LP has {len(yvars)} y-variables == |E|={len(edges)}")
    check(len(xvars) == graph["n"], f"{sample}: LP has {len(xvars)} x-variables == n={graph['n']}")

    print("\n== D. an uncertified case is not quietly claiming a bound ==")
    sample2 = "G_dev_0019"
    e2 = targets[sample2]
    check(e2["OPT"] is None and e2["U"] > e2["R"],
          f"{sample2}: OPT=null with U={e2['U']} > R={e2['R']} (a lower bound is not an upper bound)")
    print(f"    {sample2}: R={e2['R']} U={e2['U']} U_minus_R={e2['U_minus_R']} "
          f"U_sources={list(e2['U_sources'].keys()) if isinstance(e2['U_sources'], dict) else e2['U_sources']}")

    print(f"\nPROBLEMS: {len(problems)}")
    for p in problems[:20]:
        print("  -", p)
    print(f"stored partition files recomputed: {stats['stored part files']}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
