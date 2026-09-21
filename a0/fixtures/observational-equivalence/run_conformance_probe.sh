#!/usr/bin/env bash
# Direction 1 of the experiment: run the *unmodified* A0.1 checker
# (a0/conformance/conformance.py) against the mutant adapter in every mode, plus
# two controls that say whether the experiment means anything:
#
#   eplus_control        real E*, identity reported honestly  -> must PASS
#   eplus_control_py314  real E* executed by python3.14       -> see REPORT.md (false red)
#   eplus_mut_own        E', its own identity                 -> FAIL (identity, not behaviour)
#   eplus_mut_claim      E', claiming E*'s identity material   -> PASS   <- the gap
#   eplus_mut_omit       E', no identity material at all       -> PASS   <- omitted fields are silently tolerated
#   eplus_mut_twin       E', c01 answered from the c03 file    -> PASS   <- bit-identical value twin
#   eplus_mut_echo       E', claiming E* + echoing its own manifest -> FAIL (only voluntary channel)
#
# Side effect, disclosed in REPORT.md: the runner writes its per-runtime
# artifacts under its own tree (a0/conformance/out/adapters/<name>.* and
# a0/conformance/out/runs/a01-<name>-*).  Names are prefixed with `eplus_` so
# nothing of the study's four runtimes is touched.
set -u
A0=/home/ebt/rsi-dev/a0
FX=$A0/fixtures/observational-equivalence
AD=$FX/adapters/e_plus_adapter.py
EPRIME=$FX/e_prime
ESTAR=$A0/tasks/circle-packing
OUT=$FX/out/conformance
mkdir -p "$OUT"

echo "adapter revision: $(sha256sum "$AD" | cut -d' ' -f1)"
echo "mutant E' revision: $(sha256sum "$EPRIME/e_star.py" | cut -d' ' -f1)"

run() {
  local name=$1; shift
  echo "=== $name ==="
  ( cd "$A0/conformance" && python3 conformance.py run \
      --runtimes "$name" --adapter "$name=python3 $AD $*" --no-controls \
      --out "$OUT/$name.json" ) 2>&1 | tee "$OUT/$name.log" | tail -3
}

run eplus_control       --evaluator-dir "$ESTAR"  --identity own
run eplus_control_py314 --evaluator-dir "$ESTAR"  --identity own --python /usr/bin/python3.14
run eplus_mut_own       --evaluator-dir "$EPRIME" --identity own
run eplus_mut_claim     --evaluator-dir "$EPRIME" --identity claim-e-star
run eplus_mut_omit      --evaluator-dir "$EPRIME" --identity omit
run eplus_mut_twin      --evaluator-dir "$EPRIME" --identity omit --twin-swap
run eplus_mut_echo      --evaluator-dir "$EPRIME" --identity claim-e-star --echo-manifest

echo
echo "=== verdicts ==="
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
for path in sorted(Path(sys.argv[1]).glob("eplus_*.json")):
    doc = json.loads(path.read_text())
    for name, entry in doc["runtimes"].items():
        rows = entry.get("rows") or []
        counts = {}
        for row in rows:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print(f"{name:<22} {entry['state']:<8} {entry.get('reason') or 'all checks passed':<55} rows={counts}")
PY
