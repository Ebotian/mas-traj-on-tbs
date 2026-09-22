#!/bin/sh
# The one command that reproduces every number in redesign/LEVERS.md.
#
#   sh gen/run_all.sh            # resumable: finished stages are skipped
#   FORCE=1 sh gen/run_all.sh    # re-run every E* measurement
#
# All of it is local CPU, no model spend, no network.  The MQLib binary must
# already exist at the pin (references/build/build_mqlib.sh); the path is
# overridable with MQLIB=.
set -eu
cd "$(dirname "$0")/.."          # -> a0/tasks/maxcut/redesign
REDESIGN="$(pwd)"
TASK="$(cd .. && pwd)"
MQLIB="${MQLIB:-/tmp/mcwork/MQLib/bin/MQLib}"
FORCE_FLAG=""
[ "${FORCE:-0}" = "1" ] && FORCE_FLAG="--force"

echo "== 1. L1 instances (n=128/256/512/1024 for RR:d4, ER:p080) =="
python3 gen/gen_l1_instances.py
python3 gen/gen_l1_instances.py --check

echo "== 2. byte-identical mirror of the frozen candidates (DEVIATIONS D-RD-1) =="
python3 gen/make_frozen_mirror.py

echo "== 3. L1 reference ensemble (6 heuristics x 5 seeds x 30 s) =="
python3 "$TASK/references/tools/run_ensemble.py" --binary "$MQLIB" \
    --manifest instances/manifest.json --suite-root instances --roles redesign-L1 \
    --outdir instances/logs --scratch /tmp/redesign-mcwork/inputs --jobs 11 --time-limit 30

echo "== 3b. L1 4x top-up on the large-n graphs (tests the 30 s reference) =="
python3 gen/l1_topup.py

echo "== 4. L1 SCIP certification attempt (120 s/graph) =="
python3 "$TASK/references/tools/scip_maxcut.py" \
    --manifest instances/manifest.json --suite-root instances --roles redesign-L1 \
    --out instances/scip --limit 120 --jobs 4

echo "== 5. L1 b_i and p_i through E* (theta: seed 1337; DEVIATIONS D-RD-2) =="
python3 gen/l1_eval.py $FORCE_FLAG

echo "== 6. L1 targets, first pass (R_i and any SCIP certificate) =="
python3 gen/l1_targets.py

echo "== 7. L1 rigorous upper bounds U_i (tiered budget; DEVIATIONS D-RD-6) =="
python3 gen/l1_ub.py --targets instances/targets_raw.json $FORCE_FLAG

echo "== 8. L1 targets, second pass (merge U_i, reduce rho(n)) =="
python3 gen/l1_targets.py --skip-build

echo "== 9. L2 weaker positive controls on the frozen dev suite =="
python3 gen/make_l2_candidates.py
python3 gen/run_l2.py $FORCE_FLAG

echo "== 10. decision table =="
python3 gen/make_lever_data.py

echo "DONE.  See LEVERS.md, lever_data.json, out/l1_results.json, out/l2_results.json."
