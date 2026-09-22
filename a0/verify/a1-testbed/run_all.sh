#!/bin/sh
# Re-derive every A1-testbed claim from scratch.  Zero model spend: nothing here
# calls a provider (the meter probes use local sockets only, the E*/harness runs
# use frozen candidates).
#
#   sh a0/verify/a1-testbed/run_all.sh
#
# NOTE: v2 and v5 run two commands that are NOT read-only outside this directory:
#   * a0/tasks/maxcut/conformance.py --check  rewrites conformance.report.json
#   * a0/a1/verify.py                         rewrites a0/a1/declarations/CID.json
# If the tree must stay as found:
#   git checkout -- a0/tasks/maxcut/conformance.report.json a0/a1/declarations/CID.json
set -eu
cd "$(dirname "$0")/../../.."
HERE=a0/verify/a1-testbed

# --- prerequisites: the pre-fix meter tree, and the before/after wire captures -------------
PREFIX=/tmp/prefix-meter
if [ ! -f "$PREFIX/a0/meter/meter_proxy.py" ]; then
  rm -rf "$PREFIX"; mkdir -p "$PREFIX"
  git archive '86987235^' a0/meter | tar -x -C "$PREFIX"
fi
echo "### 0a meter selftest, post-fix proxy"
python3 a0/meter/selftest.py --out "$HERE/meter_selftest_after" --work /tmp/meter-selftest-after \
  > "$HERE/out_selftest_after.txt" 2>&1 || true
echo "### 0b meter selftest, pre-fix proxy"
python3 a0/meter/selftest.py --out "$HERE/meter_selftest_before" --work /tmp/meter-selftest-before \
  --proxy "$PREFIX/a0/meter/meter_proxy.py" > "$HERE/out_selftest_before.txt" 2>&1 || true
echo "### 0c raw tap, post-fix proxy"
python3 a0/meter/raw_tap.py --proof --out "$HERE/tap" --work /tmp/tap-after-work --label mine_after
echo "### 0d raw tap, pre-fix proxy"
python3 a0/meter/raw_tap.py --proof --out "$HERE/tap" --work /tmp/tap-before-work --label mine_before \
  --proxy "$PREFIX/a0/meter/meter_proxy.py" || true

echo "### v1 suite (canonical/disjoint/sampling/leakage)";  python3 "$HERE/v1_suite.py"     | tee "$HERE/out_v1_suite.txt"
echo "### v1b live leak (E* + harness)";                   python3 "$HERE/v1b_leak_live.py" | tee "$HERE/out_v1b_leak_live.txt"
echo "### v2 E* (six properties, mode, pre-fix regression)"; python3 "$HERE/v2_estar.py"   | tee "$HERE/out_v2_estar.txt"
echo "### v3 reference targets";                           python3 "$HERE/v3_references.py" | tee "$HERE/out_v3_references.txt"
echo "### v4 meter (ledger, framing tap, fail-closed)";    python3 "$HERE/v4_meter.py"     | tee "$HERE/out_v4_meter.txt"
echo "### v5 wiring (+ the A1 verify command)";            python3 "$HERE/v5_wiring.py"    | tee "$HERE/out_v5_wiring.txt"
echo "### v6 gate (thresholds, rho/Delta, verdict)";       python3 "$HERE/v6_gate.py"      | tee "$HERE/out_v6_gate.txt"
echo "### done"
