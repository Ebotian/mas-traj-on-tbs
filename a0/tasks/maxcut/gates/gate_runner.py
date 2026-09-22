#!/usr/bin/env python3
"""The pre-registered admissibility gate for the T1 max-cut task.

What this decides
-----------------
The task is only admissible if a **known-effective external artifact**
demonstrably improves the frozen baseline, and if, after that artifact is
applied, **enough headroom remains**.  The artifact is the contract's positive
control

    PC_i = networkx.algorithms.approximation.one_exchange(G_i, initial_cut=b_i, seed=s_i)

(see `../positive_control/`, which also owns the frozen baseline `b_i`).

Everything below is measured through E* (`../e_star.py`), the harness-owned
evaluator: this runner never computes a cut itself and never reads a number a
candidate produced (`INTERFACE.md` §5, §6).  It runs E* once per (candidate,
graph), keeps the Outcome files under `outcomes/` as evidence, and reduces them
with exact rational arithmetic — no float decides anything.

The three parts of the gate, and where each comes from
------------------------------------------------------
1. **Δ gate** — is there a real improvement?  `Δ_i = (p_i - b_i)/|E_i|`, overall
   mean ≥ 0.03 **and** ≥ 0.02 in at least 3 of the 4 families.  Per-family, so
   one easy family cannot carry the mean.
2. **ρ gate** — is there headroom left afterwards?  `ρ_i = (T_i - p_i)/(T_i - b_i)`
   with `T_i = OPT_i` if certified else the feasible reference `R_i`; global
   median ≥ 0.30 and family median ≥ 0.30 in at least 3 of 4 families.
   Needs `../references/targets.json`; when it is absent this half is reported
   as `PENDING` with the exact command that completes it, and the task verdict
   is `PENDING` — never `PASS`.
3. **Saturation NO-GO** — if the *baseline* is already at/near the reference
   there is nothing to improve and the task fails regardless of 1 and 2.

If a gate fails, this runner does not relax it: it reports which path failed and
what the minimal suite change would be.  That is the pre-registered branch.

Usage
-----
    python3 gates/gate_runner.py                       # decide the gate on dev
    python3 gates/gate_runner.py --set eval            # diagnostic only
    python3 gates/gate_runner.py --targets PATH        # when targets.json lands
"""

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
sys.path.insert(0, str(MAXCUT))

import e_star_child  # noqa: E402  (E*'s own candidate resolver, for cache validation)

E_STAR = MAXCUT / "e_star.py"
SUITE = MAXCUT / "suite"
DEFAULT_TARGETS = MAXCUT / "references" / "targets.json"
CONFIG = HERE / "gate_config.json"

BASELINE = MAXCUT / "positive_control" / "baseline"
DEFAULT_PC = MAXCUT / "positive_control" / "pc"

CANDIDATE_LABEL = {"baseline": "b_i", "pc": "p_i"}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frac(doc):
    return Fraction(int(doc["numerator"]), int(doc["denominator"]))


def frac_json(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def decimal(value, digits=9):
    return format(value, "." + str(digits) + "f")


def mean(values):
    values = list(values)
    return sum(values, Fraction(0)) / len(values) if values else None


def median(values):
    """Exact median.  Even counts average the two central order statistics."""
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def suite_graphs(graph_set):
    manifest = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
    entries = [e for e in manifest["graphs"] if e["role"] == graph_set or e["path"].startswith(graph_set + "/")]
    if not entries:
        entries = [e for e in manifest["graphs"] if e.get("role") == graph_set]
    return [
        {
            "graph_id": e["graph_id"],
            "family": e["family"],
            "stratum": e.get("stratum"),
            "path": str(SUITE / e["path"]),
            "graph_sha256": e["graph_sha256"],
            "edges": int(e["edges"]),
        }
        for e in entries
    ]


# --------------------------------------------------------------------------- #
# measurement: one E* invocation per (candidate, graph), cached on disk
# --------------------------------------------------------------------------- #

def outcome_path(candidate, graph_set, graph_id, tag=""):
    middle = [graph_set] + ([tag] if tag else [])
    return HERE / "outcomes" / Path(*middle) / candidate / f"{graph_id}.outcome.json"


def current_evaluator_digest():
    """E*'s own `evaluator_source_sha256` (§5), asked of E* rather than assumed."""
    proc = subprocess.run([sys.executable, str(E_STAR), "digest", "--value-only"],
                          capture_output=True, text=True)
    digest = proc.stdout.strip()
    if not digest or len(digest) != 64:
        raise SystemExit("could not read E*'s digest")
    return digest


def cache_is_current(outcome, seed, timeout_s, evaluator_digest, candidate_digest=None):
    """A cached Outcome is evidence only if it was produced by *this* E*, from
    *these* candidate bytes, at *this* theta.

    The cache path is keyed by (graph set, candidate, graph), which is right for
    re-reading a frozen measurement and wrong for noticing that a dependency
    moved.  On 2026-09-22 the evaluator's source digest changed (the D-T1-10
    launch fix) and every stored Outcome's `canonical_digest` with it, which made
    the committed verdicts stale until they were re-run by hand.  Checking these
    fields turns that into an automatic re-run.
    """
    theta = outcome.get("theta") or {}
    if int(theta.get("seed", -1)) != int(seed):
        return False
    if float(theta.get("timeout_s", -1.0)) != float(timeout_s):
        return False
    if outcome.get("evaluator_source_sha256") != evaluator_digest:
        return False
    if candidate_digest is not None and outcome.get("candidate_source_sha256") != candidate_digest:
        return False
    return True


def evaluate(candidate_name, candidate_dir, graph_set, graph, seed, timeout_s, force, tag="",
             evaluator_digest=None, candidate_digest=None):
    """Return E*'s Outcome for one (candidate, graph).

    Cached unless `--force`, or unless the cached record was produced by a
    different evaluator, from different candidate bytes, or at a different theta
    (`cache_is_current`).

    `candidate_name` is the candidate directory's own name, so a run with the
    default PC and a run with a truncation variant share the `baseline/` Outcomes
    instead of recomputing them -- and cannot accidentally use two different
    baselines.
    """
    path = outcome_path(candidate_name, graph_set, graph["graph_id"], tag)
    if path.is_file() and not force:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if evaluator_digest is None or cache_is_current(cached, seed, timeout_s, evaluator_digest,
                                                        candidate_digest):
            return cached
        print(f"cache stale ({candidate_name} {graph['graph_id']}): re-running E*",
              file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    state_tag = f"{graph_set}-{tag}-{candidate_name}" if tag else f"{graph_set}-{candidate_name}"
    command = [
        sys.executable, str(E_STAR), "evaluate",
        "--candidate", str(candidate_dir),
        "--graph", graph["path"],
        "--seed", str(seed),
        "--timeout", str(timeout_s),
        "--out", str(path),
        "--state-dir", str(HERE / "e-star-state" / state_tag),
    ]
    subprocess.run(command, capture_output=True, text=True)
    if not path.is_file():
        raise SystemExit(f"E* wrote no Outcome for {candidate_name} {graph['graph_id']}")
    return json.loads(path.read_text(encoding="utf-8"))


def collect(graph_set, seed, timeout_s, force, pc_dir=None, tag=""):
    """One Outcome per (role, graph).  Roles are `baseline` and `pc`; `pc` is
    whatever directory `--pc` names."""
    pc_dir = Path(pc_dir) if pc_dir else DEFAULT_PC
    evaluator_digest = current_evaluator_digest()
    roles = {"baseline": BASELINE, "pc": pc_dir}
    digests = {role: e_star_child.resolve_candidate(directory)["source_sha256"]
               for role, directory in roles.items()}
    graphs = suite_graphs(graph_set)
    outcomes = {role: {} for role in roles}
    for graph in graphs:
        for role, directory in roles.items():
            outcomes[role][graph["graph_id"]] = evaluate(
                directory.name, directory, graph_set, graph, seed, timeout_s, force, tag,
                evaluator_digest, digests[role])
    return graphs, outcomes


# --------------------------------------------------------------------------- #
# the gates
# --------------------------------------------------------------------------- #

def delta_rows(graphs, outcomes, targets_by_graph):
    rows = []
    for graph in graphs:
        graph_id = graph["graph_id"]
        b = outcomes["baseline"][graph_id]
        p = outcomes["pc"][graph_id]
        row = {
            "graph_id": graph_id,
            "family": graph["family"],
            "stratum": graph.get("stratum"),
            "graph_sha256": graph["graph_sha256"],
            "edges": graph["edges"],
            "baseline_status": b["status"],
            "pc_status": p["status"],
            "b": b.get("cut_edges"),
            "p": p.get("cut_edges"),
        }
        if b["status"] != "ok" or p["status"] != "ok":
            row["scored"] = False
            row["reason"] = "unscored: a non-ok Outcome is never folded in as 0"
            row["delta"] = None
        else:
            delta = Fraction(int(p["cut_edges"]) - int(b["cut_edges"]), graph["edges"])
            row["scored"] = True
            row["delta"] = delta
            row["delta_exact"] = f"{delta.numerator}/{delta.denominator}"
            row["delta_display"] = decimal(delta)
            row["b_cut_fraction"] = decimal(Fraction(int(b["cut_edges"]), graph["edges"]))
            row["p_cut_fraction"] = decimal(Fraction(int(p["cut_edges"]), graph["edges"]))
        target = targets_by_graph.get(graph_id)
        if target is not None and row["scored"]:
            T = target_value(target)
            if T is not None:
                row["T"] = int(T)
                row["T_source"] = "OPT_certified" if target.get("opt_certified") else "R_feasible_reference"
                gap = int(T) - int(b["cut_edges"])
                row["rho"] = Fraction(int(T) - int(p["cut_edges"]), gap) if gap != 0 else None
                row["headroom_closed"] = Fraction(int(p["cut_edges"]) - int(b["cut_edges"]), gap) \
                    if gap != 0 else None
                row["baseline_headroom"] = Fraction(int(T) - int(b["cut_edges"]), int(T)) if int(T) else None
                if row["rho"] is not None:
                    row["rho_exact"] = f"{row['rho'].numerator}/{row['rho'].denominator}"
                    row["rho_display"] = decimal(row["rho"])
                if row["headroom_closed"] is not None:
                    row["headroom_closed_exact"] = (f"{row['headroom_closed'].numerator}/"
                                                    f"{row['headroom_closed'].denominator}")
                    row["headroom_closed_display"] = decimal(row["headroom_closed"])
                if row["baseline_headroom"] is not None:
                    row["baseline_headroom_display"] = decimal(row["baseline_headroom"])
        rows.append(row)
    return rows


def target_value(target):
    """OPT_i when optimality is certified, else the feasible reference R_i."""
    if target.get("opt_certified") and target.get("OPT") is not None:
        return target["OPT"]
    if target.get("R") is not None:
        return target["R"]
    return None


def families(rows):
    return sorted({row["family"] for row in rows})


def delta_gate(rows, config):
    gate = config["gates"]["delta_gate"]
    scored = [row for row in rows if row["scored"]]
    unscored = [row for row in rows if not row["scored"]]
    overall = mean([row["delta"] for row in scored])
    per_family = {}
    for family in families(rows):
        values = [row["delta"] for row in scored if row["family"] == family]
        per_family[family] = {
            "graphs": len(values),
            "scored": len(values),
            "mean": mean(values),
        }
    passing = [f for f, v in per_family.items()
               if v["mean"] is not None and v["mean"] >= frac(gate["per_family_mean_min"])]
    overall_ok = overall is not None and overall >= frac(gate["overall_mean_min"])
    families_ok = len(passing) >= int(gate["families_required"])
    by_stratum = {}
    for row in scored:
        by_stratum.setdefault(f"{row['family']}:{row.get('stratum')}", []).append(row["delta"])
    per_stratum = {key: {"graphs": len(values), "mean": mean(values)}
                   for key, values in sorted(by_stratum.items())}
    return {
        "overall_mean": overall,
        "overall_mean_min": frac(gate["overall_mean_min"]),
        "overall_pass": bool(overall_ok),
        "per_family": per_family,
        "per_stratum": per_stratum,
        "per_family_mean_min": frac(gate["per_family_mean_min"]),
        "families_passing": sorted(passing),
        "families_required": int(gate["families_required"]),
        "families_total": int(gate["families_total"]),
        "families_pass": bool(families_ok),
        "unscored": [row["graph_id"] for row in unscored],
        "verdict": "PASS" if (overall_ok and families_ok) else "FAIL",
    }


def rho_gate(rows, config):
    gate = config["gates"]["rho_gate"]
    scored = [row for row in rows if row.get("rho") is not None]
    if not scored:
        return {"verdict": "PENDING", "reason": "no graph carries both a target and scored b_i/p_i"}
    global_median = median([row["rho"] for row in scored])
    per_family = {}
    for family in families(rows):
        values = [row["rho"] for row in rows if row["family"] == family and row.get("rho") is not None]
        per_family[family] = {"graphs": len(values), "median": median(values)}
    per_stratum = {}
    for row in rows:
        if row.get("rho") is None:
            continue
        key = f"{row['family']}:{row.get('stratum')}"
        per_stratum.setdefault(key, []).append(row["rho"])
    per_stratum = {key: {"graphs": len(values), "median": median(values)}
                   for key, values in sorted(per_stratum.items())}
    passing = [f for f, v in per_family.items()
               if v["median"] is not None and v["median"] >= frac(gate["per_family_median_min"])]
    global_ok = global_median >= frac(gate["global_median_min"])
    families_ok = len(passing) >= int(gate["families_required"])
    return {
        "global_median": global_median,
        "global_median_min": frac(gate["global_median_min"]),
        "global_pass": bool(global_ok),
        "per_family": per_family,
        "per_stratum": per_stratum,
        "per_family_median_min": frac(gate["per_family_median_min"]),
        "families_passing": sorted(passing),
        "families_required": int(gate["families_required"]),
        "families_total": int(gate["families_total"]),
        "families_pass": bool(families_ok),
        "graphs_scored": len(scored),
        "verdict": "PASS" if (global_ok and families_ok) else "FAIL",
    }


def saturation_gate(rows, config):
    gate = config["gates"]["saturation_no_go"]
    values = [row["baseline_headroom"] for row in rows if row.get("baseline_headroom") is not None]
    if not values:
        return {"verdict": "PENDING", "reason": "no targets: baseline headroom is not measurable"}
    closed = [row["graph_id"] for row in rows
              if row.get("baseline_headroom") is not None and row["baseline_headroom"] <= 0]
    med = median(values)
    floor = frac(gate["baseline_headroom_median_min"])
    no_go = bool(closed) or med < floor
    return {
        "baseline_headroom_median": med,
        "baseline_headroom_min": min(values),
        "baseline_headroom_median_min": floor,
        "graphs_with_zero_headroom": closed,
        "no_go": no_go,
        "verdict": "NO_GO" if no_go else "PASS",
    }


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #

def jsonify(value):
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator,
                "decimal": decimal(value)}
    if isinstance(value, dict):
        return {k: jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify(v) for v in value]
    return value


def emit_values(graph_set, outcomes, graphs, pc_name="pc"):
    """Write the two value files in the shape `references/recompute_rho.py` accepts.

    The sibling workstream already owns an implementation of the rho definition
    (`../references/recompute_rho.py`, `--baseline` / `--positive-control`).  Its
    accepted input is a document with an `outcomes` list of INTERFACE.md §5
    records, so emitting from here costs nothing and lets the gate be
    cross-checked by that script instead of only by this one.

    The default PC keeps the historical file name (`<set>.positive-control.json`);
    a variant is written under its own directory name so two PCs never overwrite
    each other's values.
    """
    written = {}
    pc_label = "positive-control" if pc_name == "pc" else pc_name
    for role, label in (("baseline", "baseline"), ("pc", pc_label)):
        records = [outcomes[role][graph["graph_id"]] for graph in graphs]
        path = HERE / "values" / f"{graph_set}.{label}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "a0.maxcut.values/v1",
            "graph_set": graph_set,
            "role": CANDIDATE_LABEL[role],
            "candidate_dir_name": pc_name if role == "pc" else "baseline",
            "candidate_source_sha256": records[0].get("candidate_source_sha256"),
            "source": "E* Outcomes, a0/tasks/maxcut/gates/outcomes/%s/<candidate dir>/*.outcome.json"
                      % graph_set,
            "outcomes": records,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[label] = str(path)
    return written


def human_table(verdict, rows):
    lines = []
    lines.append(f"# gate report — set `{verdict['graph_set']}`, "
                 f"positive control `{verdict['artifacts']['positive_control_candidate']}`, "
                 f"seed {verdict['theta']['seed']}, tau {verdict['theta']['timeout_s']} s")
    lines.append("")
    lines.append("| gate | verdict | detail |")
    lines.append("|---|---|---|")
    d = verdict["delta_gate"]
    lines.append(f"| Δ (improvement) | **{d['verdict']}** | overall mean "
                 f"{decimal(d['overall_mean']) if d['overall_mean'] is not None else 'n/a'} "
                 f"(need ≥ {decimal(d['overall_mean_min'])}); families passing "
                 f"{len(d['families_passing'])}/{d['families_total']} (need {d['families_required']}) |")
    r = verdict["rho_gate"]
    rho_detail = r.get("reason") if r["verdict"] == "PENDING" else (
        f"median {decimal(r['global_median'])} (need ≥ {decimal(r['global_median_min'])}); "
        f"families passing {len(r['families_passing'])}/{r['families_total']}")
    lines.append(f"| ρ (headroom left) | **{r['verdict']}** | {rho_detail} |")
    closed = [row["headroom_closed"] for row in rows if row.get("headroom_closed") is not None]
    if closed:
        lines.append(f"| — for scale — | | the PC closes {decimal(mean(closed))} of the "
                     f"baseline-to-target gap on average (Δ + ρ would be 1 under the other "
                     f"reading of Δ; see DEVIATIONS.md D-GATE-1) |")
    s = verdict["saturation_no_go"]
    sat_detail = s.get("reason") if s["verdict"] == "PENDING" else (
        f"baseline headroom median "
        f"{decimal(s['baseline_headroom_median'])} (no-go below "
        f"{decimal(s['baseline_headroom_median_min'])})")
    lines.append(f"| saturation NO-GO | **{s['verdict']}** | {sat_detail} |")
    lines.append("")
    lines.append(f"**Task admissibility: `{verdict['verdict']}`**")
    lines.append("")
    lines.append("## per graph")
    lines.append("")
    lines.append("| graph | family | \\|E\\| | b_i | p_i | Δ_i | Δ exact |"
                 + (" T_i | ρ_i |" if any(row.get("T") is not None for row in rows) else ""))
    lines.append("|---|---|---|---|---|---|---|" + ("---|---|---|" if any(row.get("T") is not None for row in rows) else ""))
    for row in rows:
        cells = [
            row["graph_id"], row["family"], str(row["edges"]),
            str(row["b"]) if row["scored"] else f"({row['baseline_status']})",
            str(row["p"]) if row["scored"] else f"({row['pc_status']})",
            row.get("delta_display", "—"), row.get("delta_exact", "—"),
        ]
        if any(r.get("T") is not None for r in rows):
            cells += [str(row.get("T", "—")), row.get("rho_display", "—")]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## per family")
    lines.append("")
    lines.append("| family | graphs | mean Δ | median ρ |")
    lines.append("|---|---|---|---|")
    for family in families(rows):
        dm = d["per_family"].get(family, {}).get("mean")
        rm = verdict["rho_gate"].get("per_family", {}).get(family, {}).get("median")
        lines.append(f"| {family} | {verdict['delta_gate']['per_family'][family]['graphs']} | "
                     f"{decimal(dm) if dm is not None else '—'} | "
                     f"{decimal(rm) if rm is not None else '—'} |")
    lines.append("")
    lines.append("## per stratum")
    lines.append("")
    lines.append("| family:stratum | graphs | mean Δ | median ρ |")
    lines.append("|---|---|---|---|")
    strata = sorted(set(verdict["delta_gate"].get("per_stratum", {}))
                    | set(verdict["rho_gate"].get("per_stratum", {})))
    for key in strata:
        dm = verdict["delta_gate"].get("per_stratum", {}).get(key, {}).get("mean")
        rm = verdict["rho_gate"].get("per_stratum", {}).get(key, {}).get("median")
        count = (verdict["delta_gate"].get("per_stratum", {}).get(key, {}).get("graphs")
                 or verdict["rho_gate"].get("per_stratum", {}).get(key, {}).get("graphs"))
        lines.append(f"| {key} | {count} | {decimal(dm) if dm is not None else '—'} | "
                     f"{decimal(rm) if rm is not None else '—'} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def proposed_repair(verdict):
    """The pre-registered branch when a gate fails: name the failing path and the
    minimal suite change, and say what would have to be re-frozen."""
    out = {}
    if verdict["delta_gate"]["verdict"] == "FAIL":
        weak = [f for f, v in verdict["delta_gate"]["per_family"].items()
                if v["mean"] is None or v["mean"] < verdict["delta_gate"]["per_family_mean_min"]]
        out["delta_gate"] = {
            "failing_families": weak,
            "proposal": ("re-draw only these families' strata so that the PC has more room to "
                         "move: raise density/sparseness contrast within the family, or add a "
                         "stratum the artifact is known to help on. Do not touch the families "
                         "that already pass."),
            "requires_re_freezing": ["the affected graph files and suite/manifest.json",
                                     "references/targets.json for those graphs",
                                     "any C*(T1) row whose expected cut_edges is graph-specific"],
        }
    if verdict["rho_gate"]["verdict"] == "FAIL":
        tight = [f for f, v in verdict["rho_gate"]["per_family"].items()
                 if v["median"] is None or v["median"] < verdict["rho_gate"]["per_family_median_min"]]
        out["rho_gate"] = {
            "failing_families": tight,
            "proposal": ("the PC is closing too much of the gap on these families, so the "
                         "substrate has nothing left to earn: re-draw those strata at a density "
                         "where the reference ensemble and the PC separate (sparser graphs leave "
                         "comparatively more for local search to miss)."),
            "requires_re_freezing": ["the affected graph files and suite/manifest.json",
                                     "references/targets.json for those graphs",
                                     "the reference ensemble run, since R_i is per graph"],
        }
    if verdict["saturation_no_go"]["verdict"] == "NO_GO":
        out["saturation_no_go"] = {
            "failing_path": "the baseline already sits at the reference",
            "proposal": ("the suite is too easy at the baseline for this baseline definition; the "
                         "minimal change is to re-draw the strata at lower density (where a random "
                         "bisection is furthest from the reference), not to weaken the baseline."),
            "requires_re_freezing": ["the affected graph files and suite/manifest.json",
                                     "references/targets.json", "the C*(T1) graph-specific rows"],
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", dest="graph_set", default=None,
                        help="graph set to decide on (default: gate_config.sets.gate)")
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--pc", default=None,
                        help="candidate directory to use as the positive control "
                             "(default: positive_control/pc).  Its name selects the "
                             "Outcome and verdict file names, so variants never "
                             "overwrite the contract PC's frozen verdicts.")
    parser.add_argument("--force", action="store_true", help="re-run E* instead of using cached Outcomes")
    parser.add_argument("--out", default=None)
    parser.add_argument("--table-out", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    graph_set = args.graph_set or config["sets"]["gate"]
    seed = int(config["theta"]["seed"])
    timeout_s = float(config["theta"]["timeout_s"])
    pc_dir = Path(args.pc).resolve() if args.pc else DEFAULT_PC
    pc_name = pc_dir.name
    pc_key = f".{pc_name}" if pc_name != "pc" else ""

    targets_path = Path(args.targets)
    targets_by_graph = {}
    targets_status = "ABSENT"
    targets_sha = None
    if targets_path.is_file():
        document = json.loads(targets_path.read_text(encoding="utf-8"))
        targets_by_graph = document.get("graphs", document)
        targets_status = "PRESENT"
        targets_sha = sha256_file(targets_path)

    graphs, outcomes = collect(graph_set, seed, timeout_s, args.force, pc_dir)
    values = emit_values(graph_set, outcomes, graphs, pc_name)
    rows = delta_rows(graphs, outcomes, targets_by_graph)

    delta = delta_gate(rows, config)
    rho = rho_gate(rows, config)
    saturation = saturation_gate(rows, config)

    if delta["verdict"] != "PASS":
        overall = "NOT_ADMISSIBLE"
    elif rho["verdict"] == "PENDING" or saturation["verdict"] == "PENDING":
        overall = "PENDING"
    elif rho["verdict"] == "PASS" and saturation["verdict"] == "PASS":
        overall = "ADMISSIBLE"
    else:
        overall = "NOT_ADMISSIBLE"

    verdict = {
        "schema": "a0.maxcut.gate_verdict/v1",
        "task": "a0/tasks/maxcut",
        "graph_set": graph_set,
        "role_of_set": "gate" if graph_set == config["sets"]["gate"] else "diagnostic",
        "theta": {"seed": seed, "timeout_s": timeout_s},
        "gate_config_sha256": sha256_file(CONFIG),
        "gate_config_status": config["status"],
        "artifacts": {
            "baseline_candidate": "positive_control/baseline",
            "positive_control_candidate": str(pc_dir.relative_to(MAXCUT))
            if str(pc_dir).startswith(str(MAXCUT)) else str(pc_dir),
            "evaluator_source_sha256": outcomes["pc"][graphs[0]["graph_id"]].get("evaluator_source_sha256"),
            "baseline_source_sha256": outcomes["baseline"][graphs[0]["graph_id"]].get("candidate_source_sha256"),
            "pc_source_sha256": outcomes["pc"][graphs[0]["graph_id"]].get("candidate_source_sha256"),
            "positive_control_identity_report": "positive_control/pc_identity_report.json",
        },
        "targets": {"path": str(targets_path), "status": targets_status, "sha256": targets_sha},
        "values_emitted_for_recompute_rho": values,
        "counts": {
            "graphs": len(rows),
            "scored": sum(1 for row in rows if row["scored"]),
            "unscored": sum(1 for row in rows if not row["scored"]),
        },
        "delta_gate": delta,
        "rho_gate": rho,
        "saturation_no_go": saturation,
        "verdict": overall,
        "pending_command": None if targets_status == "PRESENT" else (
            f"python3 gates/gate_runner.py --set {graph_set}"
            f"{' --pc ' + str(pc_dir) if pc_name != 'pc' else ''} "
            f"--targets {DEFAULT_TARGETS}"),
        "proposed_repair": proposed_repair({"delta_gate": delta, "rho_gate": rho,
                                            "saturation_no_go": saturation}),
        "rows": rows,
    }
    document = jsonify(verdict)
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out_path = Path(args.out) if args.out else HERE / f"verdict.{graph_set}{pc_key}.json"
    out_path.write_text(text, encoding="utf-8")
    table = human_table(verdict, rows)
    table_path = Path(args.table_out) if args.table_out else HERE / f"verdict.{graph_set}{pc_key}.md"
    table_path.write_text(table, encoding="utf-8")

    if not args.quiet:
        print(table, end="")
        print(f"wrote {out_path} and {table_path}", file=sys.stderr)
        if verdict["pending_command"]:
            print(f"rho half PENDING: {verdict['pending_command']}", file=sys.stderr)
    return {"ADMISSIBLE": 0, "PENDING": 2}.get(overall, 1)


if __name__ == "__main__":
    raise SystemExit(main())
