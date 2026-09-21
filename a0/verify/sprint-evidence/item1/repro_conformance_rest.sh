#!/usr/bin/env bash
# Remaining three rows of the fixture's §2 table (omit / twin / echo).
set -u
A0=/home/ebt/rsi-dev/a0
FX=$A0/fixtures/observational-equivalence
AD=$FX/adapters/e_plus_adapter.py
EPRIME=$FX/e_prime
OUT=$A0/verify/sprint-evidence/item1/conformance
mkdir -p "$OUT"
export A0_FIXTURE_RUN_ROOT="$OUT/adapter-scratch"
run() {
  local name=$1; shift
  echo "=== $name ==="
  ( cd "$A0/conformance" && python3 conformance.py run \
      --runtimes "$name" --adapter "$name=python3 $AD $*" --no-controls \
      --out "$OUT/$name.repro.json" ) 2>&1 | tee "$OUT/$name.repro.log" | tail -3
  echo "exit=${PIPESTATUS[0]}"
}
run eplus_mut_omit --evaluator-dir "$EPRIME" --identity omit
run eplus_mut_twin --evaluator-dir "$EPRIME" --identity omit --twin-swap
run eplus_mut_echo --evaluator-dir "$EPRIME" --identity claim-e-star --echo-manifest
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
for path in sorted(Path(sys.argv[1]).glob("*.repro.json")):
    doc = json.loads(path.read_text())
    for name, entry in doc["runtimes"].items():
        rows = entry.get("rows") or []
        counts = {}
        for row in rows:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print(f"{name:<22} {entry['state']:<8} {str(entry.get('reason') or 'all checks passed'):<55} rows={counts}")
PY
