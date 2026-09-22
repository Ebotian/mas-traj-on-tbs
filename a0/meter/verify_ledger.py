#!/usr/bin/env python3
"""Independent re-derivation of a meter ledger. Exits non-zero on the first disagreement.

This is deliberately *not* part of the proxy: a ledger that only the component which wrote it can
check is not evidence. Given a ledger written by `meter_proxy.py`, this tool recomputes every
metered row's `ceq` from that row's own `usage` triple using `INTERFACE.md` §8's integer formula,
and asserts the structural invariants the interface fixes:

* every row's key set is exactly the frozen set, in the frozen order;
* a metered row has an integer `ceq` equal to `miss + floor(hit*2/100) + 4*completion`,
  a non-null three-field integer `usage`, and `reason: null`;
* an unmetered row has `ceq: null`, `usage: null`, and a non-empty `reason`.

Usage:
    python3 verify_ledger.py <ledger.jsonl> [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meter_core import ROW_KEY_ORDER, ceq, read_ledger, verify_row  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="re-derive every row of an a0 meter ledger")
    parser.add_argument("ledger")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable summary")
    args = parser.parse_args(argv)

    try:
        rows = read_ledger(args.ledger)
    except Exception as exc:  # noqa: BLE001
        print("FAIL: cannot read ledger: %s" % exc, file=sys.stderr)
        return 2

    failures = []
    metered = unmetered = 0
    total_ceq = 0
    per_campaign: dict[tuple[str, str], int] = {}
    for index, row in enumerate(rows):
        ok, detail = verify_row(row)
        if not ok:
            failures.append({"row": index, "detail": detail})
            continue
        if list(row.keys()) != list(ROW_KEY_ORDER):
            failures.append({"row": index,
                             "detail": "key order is %s" % list(row.keys())})
            continue
        if row["unmetered"]:
            unmetered += 1
        else:
            metered += 1
            total_ceq += row["ceq"]
            key = (row["campaign_id"], row["arm_id"])
            per_campaign[key] = per_campaign.get(key, 0) + row["ceq"]

    summary = {
        "ledger": os.path.abspath(args.ledger),
        "rows": len(rows),
        "metered": metered,
        "unmetered": unmetered,
        "ceq_total": total_ceq,
        "ceq_per_campaign_arm": {"%s/%s" % k: v for k, v in sorted(per_campaign.items())},
        "failures": failures,
        "formula": "ceq = miss + floor(hit*2/100) + 4*completion",
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("%s: %d rows, %d metered, %d unmetered, ceq_total=%d"
              % (os.path.basename(args.ledger), len(rows), metered, unmetered, total_ceq))
        for key, value in sorted(per_campaign.items()):
            print("  %s/%s ceq=%d" % (key[0], key[1], value))
        for bad in failures:
            print("  MISMATCH row %d: %s" % (bad["row"], bad["detail"]))
    if failures:
        return 1
    # A sanity check on the tool itself: the frozen formula must be total on the published
    # integer domain. A negative or float "usage" would be a silent budget leak.
    assert ceq(0, 0, 0) == 0
    assert ceq(1, 99, 1) == 1 + 1 + 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
