#!/usr/bin/env bash
# Direction 1b: what the measurement token (D3) actually closes, and what it does not.
#
# All four rows run under the checker's own command shape with the envelope REQUIRED
# (`--envelope required`, the default), so every row needs the harness token.  What varies is
# what the lane attests about the identity behind that token:
#
#   eplus_d3_control         real E*; attests what it really executed        -> must PASS
#                            (the control that says the wiring, not the verdict, is what differs)
#   eplus_d3_claim_measured  E'; echoes the harness token, attests E''s own   -> must FAIL (the checker
#                            real evaluator/candidate/behaviour bytes           names this the "claim attack")
#   eplus_d3_claim_copy      E'; echoes the harness token and copies the      -> the "consistent liar" of
#                            token's own binding values verbatim                 a0/envelope/README.md §5
#   eplus_d3_twin_measured   E'; c01 answered from the c03 file, attesting    -> must FAIL (attested
#                            the bytes it really read                           candidate_sha256 != the token's)
#
# Reports land in out/conformance.envelope_required_attested/.
set -u
A0=/home/ebt/rsi-dev/a0
FX=$A0/fixtures/observational-equivalence
AD=$FX/adapters/e_plus_adapter.py
EPRIME=$FX/e_prime
ESTAR=$A0/tasks/circle-packing
OUT=$FX/out/conformance.envelope_required_attested
mkdir -p "$OUT"

echo "checker revision: $(sha256sum $A0/conformance/conformance.py | cut -d' ' -f1)"
echo "adapter revision: $(sha256sum "$AD" | cut -d' ' -f1)"

run() {
  local name=$1; shift
  echo "=== $name ==="
  ( cd "$A0/conformance" && python3 conformance.py run \
      --runtimes "$name" --adapter "$name=python3 $AD $*" --no-controls \
      --out "$OUT/$name.json" ) 2>&1 | tee "$OUT/$name.log" | tail -3
}

run eplus_d3_control        --evaluator-dir "$ESTAR"  --identity own          --attestation measured
run eplus_d3_claim_measured --evaluator-dir "$EPRIME" --identity claim-e-star --attestation measured
run eplus_d3_claim_copy     --evaluator-dir "$EPRIME" --identity claim-e-star --attestation copy
run eplus_d3_twin_measured  --evaluator-dir "$EPRIME" --identity omit         --attestation measured --twin-swap

echo
echo "=== verdicts ==="
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
for path in sorted(Path(sys.argv[1]).glob("eplus_d3_*.json")):
    doc = json.loads(path.read_text())
    for name, entry in doc["runtimes"].items():
        rows = entry.get("rows") or []
        counts = {}
        for row in rows:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        checks = {c["check_id"]: c["ok"] for c in entry.get("checks") or []
                  if c["check_id"] in ("measurement-attestation", "E-r-equals-E-star",
                                       "behaviour-vs-execution-env")}
        print(f"{name:<26} {entry['state']:<6} rows={counts}")
        print(f"      {checks}")
        print(f"      reason: {(entry.get('reason') or 'all checks passed')[:150]}")
PY
