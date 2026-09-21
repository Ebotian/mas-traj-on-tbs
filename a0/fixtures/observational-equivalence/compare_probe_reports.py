#!/usr/bin/env python3
"""Compare two `conformance.py run` report sets runtime by runtime, row by row.

Used to answer one question with evidence rather than expectation: after
`a0/conformance/conformance.py` was renamed (`adapter_declared_verdict` ->
`adapter_claim__untrusted`, no verdict logic touched), do the seven probe rows
still produce the same verdicts?

    python3 compare_probe_reports.py --before out/conformance.pin45cc4e90 \
                                     --after  out/conformance \
                                     --out out/conformance/reprocheck.json

Exit 0 when every compared field is identical, 3 otherwise.  Volatile fields
(timestamps, run ids, durations, paths containing run ids) are excluded; the
compared set is exactly what the report quotes: state, reason, per-check `ok`,
per-row verdicts, per-row values/statuses/kinds, deltas and finding ids.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RUNTIME_PREFIX = "eplus_"


def load_reports(root: Path) -> dict:
    out = {}
    for path in sorted(root.glob(f"{RUNTIME_PREFIX}*.json")):
        doc = json.loads(path.read_text())
        for name, entry in (doc.get("runtimes") or {}).items():
            out[name] = {"report": path.name, "entry": entry}
    return out


def scrub(value):
    """Drop run ids / timestamps that legitimately differ between runs."""
    if isinstance(value, str):
        value = re.sub(r"a01-[A-Za-z0-9_.-]+-\d{8}T\d{6}", "a01-<run>", value)
        value = re.sub(r"\d{8}T\d{6}", "<ts>", value)
        value = re.sub(r"a0-conformance-controls-\w+", "<tmp>", value)
        value = re.sub(r"a0-fixture-runs-\w+", "<tmp>", value)
        return value
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def summarise(entry: dict) -> dict:
    rows = {}
    for row in entry.get("rows") or []:
        rows[row["candidate_id"]] = {
            "verdict": row.get("verdict"),
            "e_r_status": row.get("e_r_status"),
            "e_r_value": row.get("e_r_value"),
            "e_r_failure_kind": row.get("e_r_failure_kind"),
            "delta": row.get("delta"),
            "notes": scrub(row.get("notes") or []),
        }
    return {
        "state": entry.get("state"),
        "reason": entry.get("reason"),
        "checks": {c["check_id"]: bool(c["ok"]) for c in entry.get("checks") or []},
        "check_details_failed": {
            c["check_id"]: scrub(c.get("detail")) for c in entry.get("checks") or [] if not c["ok"]
        },
        "rows": rows,
        "finding_ids": sorted({f["finding_id"] for f in entry.get("false_green_findings") or []}),
        "adapter_declared": scrub(entry.get("adapter_declared")),
        "claim_field_present": "adapter_claim__untrusted" in entry,
        "claim_field_value": entry.get("adapter_claim__untrusted", "<absent>"),
        "legacy_claim_field_present": "adapter_declared_verdict" in entry,
    }


def diff_runtime(name: str, before: dict, after: dict) -> list[str]:
    problems = []
    for key in ("state", "reason"):
        if before[key] != after[key]:
            problems.append(f"{name}: {key} {before[key]!r} -> {after[key]!r}")
    if before["checks"] != after["checks"]:
        problems.append(f"{name}: per-check ok flags changed "
                        f"{ {k: (before['checks'].get(k), after['checks'].get(k)) for k in set(before['checks']) | set(after['checks']) if before['checks'].get(k) != after['checks'].get(k)} }")
    if before["check_details_failed"] != after["check_details_failed"]:
        problems.append(f"{name}: a failing check's detail changed")
    if before["finding_ids"] != after["finding_ids"]:
        problems.append(f"{name}: finding ids {before['finding_ids']} -> {after['finding_ids']}")
    if before["rows"].keys() != after["rows"].keys():
        problems.append(f"{name}: row set changed")
    for cid in before["rows"]:
        a, b = before["rows"][cid], after["rows"].get(cid)
        if a != b:
            problems.append(f"{name}: row {cid} changed: {a} -> {b}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label-before", default=None)
    parser.add_argument("--label-after", default=None)
    args = parser.parse_args(argv)

    before = load_reports(Path(args.before))
    after = load_reports(Path(args.after))
    names = sorted(set(before) | set(after))
    problems, results = [], []
    for name in names:
        if name not in before or name not in after:
            problems.append(f"{name}: present on only one side")
            continue
        b, a = summarise(before[name]["entry"]), summarise(after[name]["entry"])
        row_problems = diff_runtime(name, b, a)
        results.append({
            "runtime": name,
            "before": {k: b[k] for k in ("state", "reason", "checks", "finding_ids",
                                         "claim_field_present", "legacy_claim_field_present",
                                         "claim_field_value")},
            "after": {k: a[k] for k in ("state", "reason", "checks", "finding_ids",
                                        "claim_field_present", "legacy_claim_field_present",
                                        "claim_field_value")},
            "rows_before": b["rows"],
            "rows_after": a["rows"],
            "identical": not row_problems,
            "problems": row_problems,
        })
        problems.extend(row_problems)

    doc = {
        "schema": "a0.fixture.observational-equivalence.probe-reprocheck/v1",
        "before": {"dir": str(args.before), "label": args.label_before},
        "after": {"dir": str(args.after), "label": args.label_after},
        "runtimes_compared": len(results),
        "identical": not problems,
        "problems": problems,
        "results": results,
    }
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n")

    print(f"{'runtime':<22} {'state before':<10} {'state after':<10} {'rows':<8} identical")
    for r in results:
        print(f"  {r['runtime']:<20} {str(r['before']['state']):<10} {str(r['after']['state']):<10} "
              f"{len(r['rows_after']):<8} {r['identical']}")
        print(f"      claim field: before={'adapter_declared_verdict' if r['before']['legacy_claim_field_present'] else '<none>'}"
              f" after={'adapter_claim__untrusted' if r['after']['claim_field_present'] else '<none>'}"
              f" value={r['after']['claim_field_value']!r}")
    for problem in problems:
        print(f"  !! {problem}")
    print(f"identical: {not problems}")
    print(f"written: {args.out}")
    return 3 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
