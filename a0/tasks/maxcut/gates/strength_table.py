#!/usr/bin/env python3
"""The PC strength -> Delta/rho table, and the cross-check of `redesign/`.

Reads the gate verdicts this directory has already produced (one per positive
control per graph set) and reduces them to the table a contract decision needs:

    * how strong is the positive control, in the objective Delta it produces;
    * how much headroom rho does that leave for a substrate;
    * which gate each strength passes, overall, per family, on dev and on eval.

Nothing here re-measures anything: every number comes out of a `verdict.*.json`
produced by `gate_runner.py` through E*, so the table cannot drift from the
gate's own arithmetic.

It also re-checks `../redesign/lever_data.json` -- that workstream's independent
measurement of the same lever on the same frozen dev set -- variant by variant,
and reports the largest field difference rather than a vague "consistent".  This
is a *re-verification*, not a source: the verdicts are ours.

    python3 gates/strength_table.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAXCUT = HERE.parent
REDESIGN_LEVERS = MAXCUT / "redesign" / "lever_data.json"

#: redesign's variant name -> this directory's candidate directory name
REDESIGN_NAMES = {f"exchange_k{k}": f"pc_exchange_k{k:02d}" for k in (1, 2, 5, 10, 25)}
REDESIGN_NAMES["exchange_opt"] = "pc"

TOLERANCE = 1e-9


def pc_key(verdict):
    directory = verdict["artifacts"]["positive_control_candidate"]
    return directory.split("/")[-1]


def k_of(directory_name):
    match = re.fullmatch(r"pc_exchange_k(\d+)", directory_name)
    return int(match.group(1)) if match else None


def load_verdicts():
    out = {}
    for path in sorted(HERE.glob("verdict.*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if document.get("schema") != "a0.maxcut.gate_verdict/v1":
            continue
        out[(document["graph_set"], pc_key(document))] = (path, document)
    return out


def num(field):
    """A verdict's exact-rational field as a float, for display and comparison."""
    if field is None:
        return None
    if isinstance(field, dict) and "decimal" in field:
        return float(field["decimal"])
    return float(field)


def row(set_name, name, path, verdict):
    delta, rho = verdict["delta_gate"], verdict["rho_gate"]
    saturation = verdict["saturation_no_go"]
    return {
        "positive_control": name,
        "max_swaps": k_of(name),
        "graph_set": set_name,
        "verdict_path": str(path.relative_to(MAXCUT)),
        "delta_overall_mean": num(delta["overall_mean"]),
        "delta_overall_min": num(delta["overall_mean_min"]),
        "delta_families_passing": len(delta["families_passing"]),
        "delta_families_total": delta["families_total"],
        "delta_gate": delta["verdict"],
        "rho_global_median": num(rho.get("global_median")),
        "rho_global_min": num(rho.get("global_median_min")) if rho.get("global_median_min") else None,
        "rho_families_passing": len(rho.get("families_passing", [])),
        "rho_families_total": rho.get("families_total"),
        "rho_gate": rho["verdict"],
        "saturation": saturation["verdict"],
        "task_verdict": verdict["verdict"],
        "per_family": {
            family: {
                "mean_delta": num(delta["per_family"][family]["mean"]),
                "median_rho": num(rho.get("per_family", {}).get(family, {}).get("median")),
            }
            for family in sorted(delta["per_family"])
        },
        "pc_source_sha256": verdict["artifacts"]["pc_source_sha256"],
        "theta": verdict["theta"],
    }


def markdown(rows):
    lines = []
    lines.append("| positive control | k | set | Δ mean (≥0.03) | Δ families (≥3/4) | Δ gate "
                 "| ρ median (≥0.30) | ρ families (≥3/4) | ρ gate | task |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        k = "∞ (to local opt.)" if r["max_swaps"] is None else r["max_swaps"]
        lines.append(
            f"| `{r['positive_control']}` | {k} | {r['graph_set']} | "
            f"{r['delta_overall_mean']:.6f} | {r['delta_families_passing']}/{r['delta_families_total']} | "
            f"{r['delta_gate']} | {r['rho_global_median']:.6f} | "
            f"{r['rho_families_passing']}/{r['rho_families_total']} | {r['rho_gate']} | "
            f"{r['task_verdict']} |")
    lines.append("")
    lines.append("| positive control | set | ER | RR | BA | Planted |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        cells = []
        for family in ("ER", "RR", "BA", "Planted"):
            f = r["per_family"].get(family)
            cells.append("—" if not f or f["mean_delta"] is None
                         else f"{f['mean_delta']:.4f} / {f['median_rho']:.4f}")
        lines.append(f"| `{r['positive_control']}` | {r['graph_set']} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("(per family: mean Δ / median ρ)")
    lines.append("")
    return "\n".join(lines)


def crosscheck(rows):
    """Re-verify the other workstream's L2 numbers against ours, field by field."""
    if not REDESIGN_LEVERS.is_file():
        return {"status": "ABSENT", "path": str(REDESIGN_LEVERS)}
    document = json.loads(REDESIGN_LEVERS.read_text(encoding="utf-8"))
    theirs = document["L2_weaker_pc"]["verdict"]["variants"]
    mine = {r["positive_control"]: r for r in rows if r["graph_set"] == "dev"}
    compared, problems = [], []
    for their_name, our_name in sorted(REDESIGN_NAMES.items()):
        if their_name not in theirs:
            problems.append(f"{their_name}: absent from lever_data.json")
            continue
        if our_name not in mine:
            problems.append(f"{our_name}: no dev verdict of ours to compare")
            continue
        a, b = theirs[their_name], mine[our_name]
        fields = {
            "mean_delta": (a["mean_delta"], b["delta_overall_mean"]),
            "median_rho": (a["median_rho"], b["rho_global_median"]),
        }
        for family in sorted(a["per_family"]):
            fields[f"{family}.mean_delta"] = (a["per_family"][family]["mean_delta"],
                                              b["per_family"][family]["mean_delta"])
            fields[f"{family}.median_rho"] = (a["per_family"][family]["median_rho"],
                                              b["per_family"][family]["median_rho"])
        differences = {name: {"theirs": x, "ours": y, "abs_diff": abs(x - y)}
                       for name, (x, y) in fields.items() if abs(x - y) > TOLERANCE}
        max_diff = max(abs(x - y) for x, y in fields.values())
        worst = max(fields, key=lambda name: abs(fields[name][0] - fields[name][1]))
        counts = {
            "delta_families": (a["families_passing_delta"], b["delta_families_passing"]),
            "rho_families": (a["families_passing_rho"], b["rho_families_passing"]),
            "delta_gate": (a["delta_gate_pass"], b["delta_gate"] == "PASS"),
            "rho_gate": (a["rho_gate_pass"], b["rho_gate"] == "PASS"),
        }
        count_mismatches = {k: v for k, v in counts.items() if v[0] != v[1]}
        compared.append({
            "redesign_variant": their_name,
            "our_candidate": our_name,
            "fields_compared": len(fields),
            "max_abs_diff": max_diff,
            "largest_difference_field": worst,
            "field_differences": differences,
            "count_mismatches": count_mismatches,
            "agree": not differences and not count_mismatches,
        })
        if differences or count_mismatches:
            problems.append(f"{their_name}: {len(differences)} field diffs, "
                            f"{len(count_mismatches)} count mismatches")
    return {
        "status": "COMPARED",
        "path": str(REDESIGN_LEVERS),
        "graph_set": "dev",
        "tolerance": TOLERANCE,
        "variants_compared": len(compared),
        "agree": all(c["agree"] for c in compared),
        "max_abs_diff_across_all_fields": max((c["max_abs_diff"] for c in compared), default=None),
        "problems": problems,
        "comparison": compared,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=None)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    verdicts = load_verdicts()
    rows = [row(set_name, name, path, verdict)
            for (set_name, name), (path, verdict) in sorted(
                verdicts.items(),
                key=lambda item: (item[0][1] != "pc",
                                  k_of(item[0][1]) if k_of(item[0][1]) is not None else 0,
                                  item[0][0]))]
    check = crosscheck(rows)

    document = {
        "schema": "a0.maxcut.pc_strength_table/v1",
        "purpose": ("the measured curve a contract decision needs: how much objective a PC "
                    "produces, and how much headroom it leaves behind"),
        "authority": "a0/tasks/maxcut/INTERFACE.md; thresholds from gates/gate_config.json",
        "thresholds": {"delta_overall_mean_min": 0.03, "delta_family_mean_min": 0.02,
                       "rho_global_median_min": 0.30, "rho_family_median_min": 0.30,
                       "families_required": 3, "families_total": 4},
        "rows": rows,
        "redesign_crosscheck": check,
    }
    json_out = Path(args.json_out) if args.json_out else HERE / "strength_table.json"
    json_out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    table = markdown(rows)
    out = Path(args.out) if args.out else HERE / "strength_table.md"
    out.write_text(table, encoding="utf-8")
    print(table, end="")
    print(f"redesign cross-check: {check['status']}"
          + (f", {check.get('variants_compared')} variants, "
             f"agreement={check.get('agree')}" if check["status"] == "COMPARED" else ""),
          file=sys.stderr)
    for problem in check.get("problems", []):
        print("  " + problem, file=sys.stderr)
    print(f"wrote {out} and {json_out}", file=sys.stderr)
    return 0 if check.get("agree", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
