#!/usr/bin/env python3
"""Compute the per-graph headroom measure rho and the aggregate gain.

Definition (INTERFACE.md section 9 / the reference-table contract):

    rho_i = (T_i - p_i) / (T_i - b_i)          "headroom still left after the PC"

where
    b_i   = baseline value           (the substrate without the injected solver)
    p_i   = positive-control value   (the substrate with the injected solver)
    T_i   = OPT_i when optimality is certified, otherwise the feasible
            reference R_i -- and in that case it is a LOWER bound on the
            optimum, so rho is an estimate and is labelled as such.

Because T_i, p_i and b_i are all integer cut values, rho is an exact rational:
this script uses fractions.Fraction end to end and never decides anything in
floating point.  The decimal printed alongside each rho is a display field only.

Inputs accepted for --baseline / --positive-control (auto-detected):

    {"G_dev_0001": 300, "G_dev_0002": 291, ...}                  plain map
    {"outcomes": [{"graph_id": "...", "cut_edges": 300, "status": "ok"}, ...]}
                                                                 INTERFACE.md section 5
    [{"graph_id": "...", "cut_edges": 300, "status": "ok"}, ...]

A record whose status is not "ok" is treated as *unscored*, never as 0
(INTERFACE.md section 6 rule 5).

Usage:
    python3 recompute_rho.py --targets targets.json \
        --baseline baseline.json --positive-control pc.json [--out rho.json]
"""
import argparse
import json
import sys
from fractions import Fraction


def load_values(path):
    with open(path) as fh:
        doc = json.load(fh)
    out = {}
    if isinstance(doc, dict) and isinstance(doc.get("outcomes"), list):
        items = doc["outcomes"]
    elif isinstance(doc, list):
        items = doc
    elif isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, dict):
                if v.get("status", "ok") == "ok" and v.get("cut_edges") is not None:
                    out[k] = int(v["cut_edges"])
            elif isinstance(v, int) and not isinstance(v, bool):
                out[k] = v
            elif v is None:
                continue
            else:
                raise SystemExit("cannot read value for %s in %s" % (k, path))
        return out
    else:
        raise SystemExit("unrecognised document in %s" % path)
    for rec in items:
        gid = rec.get("graph_id") or rec.get("id")
        if gid is None:
            raise SystemExit("outcome without graph_id in %s" % path)
        if rec.get("status", "ok") != "ok":
            continue
        if rec.get("cut_edges") is None:
            continue
        out[gid] = int(rec["cut_edges"])
    return out


def decimal(frac, digits=9):
    return format(frac, "." + str(digits) + "f")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--positive-control", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--saturation-rho", type=float, default=None,
                    help="optional: report graphs with rho below this (display only)")
    args = ap.parse_args()

    with open(args.targets) as fh:
        targets = json.load(fh)
    per_graph = targets.get("graphs", targets)
    base = load_values(args.baseline)
    pc = load_values(args.positive_control)

    rows = []
    for gid, t in sorted(per_graph.items()):
        if gid not in base or gid not in pc:
            rows.append({"graph_id": gid, "rho": None, "reason": "missing_b_or_p"})
            continue
        b, p = base[gid], pc[gid]
        certified = bool(t.get("opt_certified")) and t.get("OPT") is not None
        T = int(t["OPT"]) if certified else int(t["R"])
        notes = []
        if p > T:
            notes.append("p_i > T_i: impossible if T_i is a valid target "
                         "(T_i is a relaxation/feasible reference) -- check the inputs")
        if b > p:
            notes.append("p_i < b_i: the positive control is worse than the baseline")
        denom = T - b
        if denom == 0:
            rows.append({"graph_id": gid, "T": T, "b": b, "p": p,
                         "target_source": "OPT_certified" if certified else "R_feasible_reference",
                         "rho": None, "headroom_closed": None,
                         "reason": "T_i == b_i: no headroom at the baseline "
                                   "(saturation at baseline; NO-GO per D6)",
                         "T_is_lower_bound_on_opt": not certified, "notes": notes})
            continue
        rho = Fraction(T - p, denom)
        closed = Fraction(p - b, denom)
        # Bias direction when T_i is only a lower bound on the optimum.
        #   f(T) = (T-p)/(T-b)  =>  f'(T) = (p-b)/(T-b)^2
        # so the reported rho is a lower bound on the true one exactly when
        # p_i > b_i, and an upper bound when the positive control is worse than
        # the baseline.  U_i brackets the optimum, so it also brackets rho.
        if p > b:
            direction = ("lower_bound_on_true_rho" if not certified else "exact")
        elif p < b:
            direction = ("upper_bound_on_true_rho" if not certified else "exact")
        else:
            direction = "exact_rho_is_1"
        row = {
            "graph_id": gid,
            "family": t.get("family"),
            "target_source": "OPT_certified" if certified else "R_feasible_reference",
            "T_is_lower_bound_on_opt": not certified,
            "T": T, "b": b, "p": p,
            "rho_exact": "%d/%d" % (rho.numerator, rho.denominator),
            "rho": float(rho),
            "rho_display": decimal(rho),
            "headroom_closed_exact": "%d/%d" % (closed.numerator, closed.denominator),
            "headroom_closed": float(closed),
            "rho_bias_direction": direction,
            "notes": notes,
        }
        U = t.get("U")
        if not certified and U is not None and U > T and (U - b) != 0:
            rho_hi = Fraction(U - p, U - b)
            row["rho_interval_from_U"] = {
                "low": float(min(rho, rho_hi)),
                "high": float(max(rho, rho_hi)),
                "low_exact": ("%d/%d" % (min(rho, rho_hi).numerator,
                                         min(rho, rho_hi).denominator)),
                "high_exact": ("%d/%d" % (max(rho, rho_hi).numerator,
                                          max(rho, rho_hi).denominator)),
                "note": "OPT_i is in [R_i, U_i], so the true rho lies in this "
                        "interval; the reported rho is the endpoint at R_i",
            }
        rows.append(row)

    scored = [r for r in rows if r.get("rho") is not None]
    summary = {
        "schema": "a0.maxcut.rho/v1",
        "definition": "rho_i = (T_i - p_i)/(T_i - b_i); T_i = OPT_i iff certified, else R_i (a lower bound on the optimum)",
        "counts": {"graphs": len(rows), "scored": len(scored),
                   "unscored": len(rows) - len(scored)},
        "mean_rho_display_only": (sum(r["rho"] for r in scored) / len(scored)) if scored else None,
        "mean_headroom_closed_display_only": (sum(r["headroom_closed"] for r in scored) / len(scored)) if scored else None,
        "rho_caveat": "exact per graph (integer inputs); the means are floats and are DISPLAY ONLY",
        "saturation_warnings": [
            {"graph_id": r["graph_id"], "reason": r.get("reason"),
             "note": ("headroom collapsed at the baseline"
                      if r.get("reason", "").startswith("T_i == b_i")
                      else "not scored; not treated as 0 (INTERFACE.md section 6 rule 5)")}
            for r in rows if r.get("rho") is None],
    }
    doc = {"summary": summary, "graphs": rows}
    text = json.dumps(doc, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    for r in rows:
        if r.get("rho") is None:
            print("UNSCORED %s: %s" % (r["graph_id"], r.get("reason")), file=sys.stderr)
    if args.saturation_rho is not None:
        for r in scored:
            if r["rho"] < args.saturation_rho:
                print("below saturation-rho %.3f: %s rho=%s"
                      % (args.saturation_rho, r["graph_id"], r["rho_display"]), file=sys.stderr)


if __name__ == "__main__":
    main()
