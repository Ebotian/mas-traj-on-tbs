#!/usr/bin/env bash
# Independent reproduction of the fixture's §2 checker rows.
# Differences from the author's run_conformance_probe.sh:
#   * report JSON goes into THIS directory (never overwrite the fixture's out/)
#   * only the four rows this assignment needs are run
# The runner still writes its own per-runtime artifacts under a0/conformance/out/
# (disclosed by the author); that is snapshotted before/after.
set -u
A0=/home/ebt/rsi-dev/a0
FX=$A0/fixtures/observational-equivalence
AD=$FX/adapters/e_plus_adapter.py
EPRIME=$FX/e_prime
ESTAR=$A0/tasks/circle-packing
OUT=$A0/verify/sprint-evidence/item1/conformance
mkdir -p "$OUT"
export A0_FIXTURE_RUN_ROOT="$OUT/adapter-scratch"

echo "adapter revision: $(sha256sum "$AD" | cut -d' ' -f1)"
echo "mutant E' revision: $(sha256sum "$EPRIME/e_star.py" | cut -d' ' -f1)"
echo "conformance.py revision: $(sha256sum "$A0/conformance/conformance.py" | cut -d' ' -f1)"
echo "host python3: $(python3 --version 2>&1)"
echo "frozen E* python: $($ESTAR/.venv/bin/python --version 2>&1)"

run() {
  local name=$1; shift
  echo "=== $name ==="
  ( cd "$A0/conformance" && python3 conformance.py run \
      --runtimes "$name" --adapter "$name=python3 $AD $*" --no-controls \
      --out "$OUT/$name.repro.json" ) 2>&1 | tee "$OUT/$name.repro.log" | tail -3
  echo "exit=${PIPESTATUS[0]}"
}

run eplus_control       --evaluator-dir "$ESTAR"  --identity own
run eplus_control_py314 --evaluator-dir "$ESTAR"  --identity own --python /usr/bin/python3.14
run eplus_mut_own       --evaluator-dir "$EPRIME" --identity own
run eplus_mut_claim     --evaluator-dir "$EPRIME" --identity claim-e-star

echo
echo "=== verdicts ==="
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
