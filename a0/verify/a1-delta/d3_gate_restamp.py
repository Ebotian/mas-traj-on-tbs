#!/usr/bin/env python3
"""Item 3 — did the gate re-stamp move a decision leaf, or soften a threshold?

My own leaf walker (not `restamp_evidence.py`'s, which is the artifact under test),
applied to every stamped document the re-stamp touched: the 576 stored Outcomes, the
14 `values/` documents and the 12 verdicts.  Every differing leaf is classified
identity / decision by name, and the classification is the whole output — a decision
leaf that moved is reported, not summarised away.

    python3 a0/verify/a1-delta/d3_gate_restamp.py [--before 7bf8a14b]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GATES = REPO / "a0/tasks/maxcut/gates"

#: the identity leaves a re-stamp is allowed to move: the E* stamp, the digest over
#: canonical bytes (which contains it), and the four fields of the redacted candidate
#: view `baf13884` introduced.
IDENTITY_LEAVES = {
    "evaluator_source_sha256", "canonical_digest", "candidate_graph_bytes",
    "candidate_graph_keys", "candidate_graph_schema", "candidate_graph_sha256",
}

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, bool(ok), detail))
    print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(ok)


def git_show(revision: str, relative: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(REPO), "show", f"{revision}:{relative}"],
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def walk(before, after, path=""):
    """Every (leaf path, before, after) that differs. Lists are compared element-wise."""
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            yield from walk(before.get(key), after.get(key), f"{path}.{key}")
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield path + ".length", len(before), len(after)
        for index, (b, a) in enumerate(zip(before, after)):
            yield from walk(b, a, f"{path}[{index}]")
    elif before != after:
        yield path, before, after


def diff_group(relative_paths: list[str], before: str) -> dict:
    leaves: Counter = Counter()
    decision = []
    differing = 0
    for relative in relative_paths:
        raw = git_show(before, relative)
        if raw is None:
            continue
        try:
            old = json.loads(raw)
        except json.JSONDecodeError:
            continue
        new = json.loads((REPO / relative).read_text(encoding="utf-8"))
        changes = list(walk(old, new))
        if changes:
            differing += 1
        for path, b, a in changes:
            leaf = path.rsplit(".", 1)[-1]
            leaves[leaf] += 1
            if leaf not in IDENTITY_LEAVES:
                decision.append({"file": relative, "field": path,
                                 "before": str(b)[:80], "after": str(a)[:80]})
    return {"records": len(relative_paths), "differing": differing,
            "leaf_names": dict(sorted(leaves.items())), "non_identity": decision}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default="7bf8a14b")
    args = parser.parse_args()
    before = args.before

    groups = {
        "outcomes": sorted(str(p.relative_to(REPO)) for p in
                           (GATES / "outcomes").glob("**/*.outcome.json")),
        "values": sorted(str(p.relative_to(REPO)) for p in (GATES / "values").glob("*.json")),
        "verdicts": sorted(str(p.relative_to(REPO)) for p in GATES.glob("verdict.*.json")),
    }

    # ------------------------------------------------ the leaf-by-leaf re-stamp diff
    print(f"== every stamped document, HEAD vs {before}, leaf by leaf ==")
    results = {}
    for name, paths in groups.items():
        results[name] = diff_group(paths, before)
        r = results[name]
        print(f"  {name}: {r['differing']}/{r['records']} differ; leaves moved {r['leaf_names']}; "
              f"non-identity leaves {len(r['non_identity'])}")
        for row in r["non_identity"][:12]:
            print(f"      MOVED {row['file']} {row['field']}: {row['before']} -> {row['after']}")
    check("no decision/input leaf moved in any stored Outcome",
          not results["outcomes"]["non_identity"])
    check("no decision/input leaf moved in any values/ document",
          not results["values"]["non_identity"])
    check("no decision/input leaf moved in any verdict",
          not results["verdicts"]["non_identity"])
    check("the Outcomes' moved leaves are exactly the six identity fields",
          set(results["outcomes"]["leaf_names"]) <= IDENTITY_LEAVES,
          str(sorted(results["outcomes"]["leaf_names"])))
    check("every verdict's moved leaf is the E* stamp alone",
          set(results["verdicts"]["leaf_names"]) <= {"evaluator_source_sha256"},
          str(sorted(results["verdicts"]["leaf_names"])))

    # ------------------------------------------------------------- the thresholds
    print("\n== the pre-registered thresholds, current vs the pre-restamp revision ==")
    config_bytes = (GATES / "gate_config.json").read_bytes()
    config = json.loads(config_bytes)
    old_config = json.loads(git_show(before, "a0/tasks/maxcut/gates/gate_config.json"))
    check("gate_config.json is byte-identical to the pre-restamp revision",
          old_config == config)
    dg, rg, sg = config["gates"]["delta_gate"], config["gates"]["rho_gate"], config["gates"]["saturation_no_go"]
    check("delta: overall mean >= 3/100 (0.03)",
          dg["overall_mean_min"] == {"numerator": 3, "denominator": 100},
          str(dg["overall_mean_min"]))
    check("delta: per-family mean >= 2/100 (0.02) in >= 3 of 4 families",
          dg["per_family_mean_min"] == {"numerator": 2, "denominator": 100}
          and dg["families_required"] == 3 and dg["families_total"] == 4,
          f"{dg['per_family_mean_min']} {dg['families_required']}/{dg['families_total']}")
    check("rho: global median >= 3/10 (0.30) and per-family median >= 3/10 in >= 3/4",
          rg["global_median_min"] == {"numerator": 3, "denominator": 10}
          and rg["per_family_median_min"] == {"numerator": 3, "denominator": 10}
          and rg["families_required"] == 3 and rg["families_total"] == 4)
    check("saturation is a veto at headroom median >= 1/20 and T_i == b_i",
          sg["baseline_headroom_median_min"] == {"numerator": 1, "denominator": 20}
          and "T_i == b_i" in sg["also_fails_if"])

    # ------------------------------------------------- the verdicts, side by side
    print("\n== each verdict: decision numbers before vs after ==")
    def decision_view(document: dict) -> dict:
        return {k: document.get(k) for k in
                ("verdict", "graph_set", "counts", "delta_gate", "rho_gate",
                 "saturation_no_go", "gate_config_sha256", "gate_config_status")}

    for relative in groups["verdicts"]:
        old_raw = git_show(before, relative)
        if old_raw is None:
            continue
        old = json.loads(old_raw)
        new = json.loads((REPO / relative).read_text())
        same = decision_view(old) == decision_view(new)
        moved = [p for p, _, _ in walk(decision_view(old), decision_view(new))]
        tag = "same decisions" if same else f"DECISION MOVED: {moved}"
        print(f"  {Path(relative).name}: {old['verdict']} -> {new['verdict']}; {tag}")
    check("every verdict keeps its top-level decision fields",
          all(decision_view(json.loads(git_show(before, r))) ==
              decision_view(json.loads((REPO / r).read_text()))
              for r in groups["verdicts"] if git_show(before, r)))

    live = subprocess.run([sys.executable, "a0/tasks/maxcut/e_star.py", "digest", "--value-only"],
                          cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    dev = json.loads((GATES / "verdict.dev.json").read_text())
    check("the dev gate verdict is still NOT_ADMISSIBLE",
          dev["verdict"] == "NOT_ADMISSIBLE", dev["verdict"])
    check("the dev gate's failing gate is the rho gate, not the delta gate",
          dev["delta_gate"]["verdict"] == "PASS" and dev["rho_gate"]["verdict"] == "FAIL"
          and not dev["saturation_no_go"]["no_go"])
    check("the dev numbers still fail the pre-registered rho demand as measured",
          dev["rho_gate"]["global_median"]["denominator"] == 3016
          and dev["rho_gate"]["global_median"]["numerator"] == 479)
    check("every verdict names the live E*",
          all(json.loads((REPO / r).read_text())["artifacts"]["evaluator_source_sha256"] == live
              for r in groups["verdicts"]))
    check("every stored Outcome names the live E*",
          all(json.loads((REPO / r).read_text()).get("evaluator_source_sha256") == live
              for r in groups["outcomes"]))

    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks ok"
          + (f"; FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
