#!/bin/sh
# The one command that re-checks this pass's hygiene claims, model-free (~1 min).
#
#   sh a0/verify/a1-hygiene/run_all.sh
#
# It runs **nothing of the lever study**: `gen/run_l2.py` without `--force` reuses
# the stored Outcomes rather than re-invoking `E*`, and both reductions are compared
# byte-for-byte with the committed files, so a drift is reported instead of written.
# Exit 0 iff every check passes; raw output lands in a0/verify/a1-hygiene/out/.
set -u
cd "$(dirname "$0")/../../.." || exit 1       # -> repository root (this file is 3 levels down)
HERE=a0/verify/a1-hygiene
OUT="$HERE/out"
REDESIGN=a0/tasks/maxcut/redesign
mkdir -p "$OUT"
fail=0
report() { printf '\n== %s ==\n' "$1"; }

report "1. every stale digest in a0/a1/** and redesign/** is labelled, or a named exception"
python3 "$HERE/h1_history.py" > "$OUT/out_h1_history.txt" 2>&1
rc=$?
grep -E '^(A\.|   [0-9]+ tracked files)' "$OUT/out_h1_history.txt"
printf '   labelled/exception files: %s\n' "$(grep -cE '^   (labelled|exception)' "$OUT/out_h1_history.txt")"
tail -1 "$OUT/out_h1_history.txt"
[ "$rc" -eq 0 ] || { echo "   FAIL rc=$rc"; fail=1; }

report "2. the L1 instances re-derive byte-identically (read-only)"
python3 "$REDESIGN/gen/gen_l1_instances.py" --check > "$OUT/out_h2_instances.txt" 2>&1
rc=$?
tail -1 "$OUT/out_h2_instances.txt"
[ "$rc" -eq 0 ] || { echo "   FAIL rc=$rc"; fail=1; }

report "3. the L2 table re-reduces from the stored Outcomes (no E* re-run)"
cp "$REDESIGN/out/l2_results.json" "$OUT/.l2.before"
python3 "$REDESIGN/gen/run_l2.py" > "$OUT/out_h3_l2.txt" 2>&1
rc=$?
grep -E '^(exchange_k10 |exchange_opt|OK: exchange_opt)' "$OUT/out_h3_l2.txt"
if cmp -s "$REDESIGN/out/l2_results.json" "$OUT/.l2.before"; then
    echo "   out/l2_results.json: byte-identical"
else
    echo "   out/l2_results.json: DRIFT — restoring the committed bytes"
    cp "$OUT/.l2.before" "$REDESIGN/out/l2_results.json"
    fail=1
fi
rm -f "$OUT/.l2.before"
[ "$rc" -eq 0 ] || { echo "   FAIL rc=$rc"; fail=1; }

report "4. the decision table re-reduces from the two results files"
cp "$REDESIGN/lever_data.json" "$OUT/.lever.before"
python3 "$REDESIGN/gen/make_lever_data.py" > "$OUT/out_h4_lever.txt" 2>&1
rc=$?
if cmp -s "$REDESIGN/lever_data.json" "$OUT/.lever.before"; then
    echo "   lever_data.json: byte-identical"
else
    echo "   lever_data.json: DRIFT — restoring the committed bytes"
    cp "$OUT/.lever.before" "$REDESIGN/lever_data.json"
    fail=1
fi
rm -f "$OUT/.lever.before"
[ "$rc" -eq 0 ] || { echo "   FAIL rc=$rc"; fail=1; }

report "5. every commit the hostile probe's evidence cites is reachable from HEAD"
python3 a0/a1/probes/hostile_candidate.py \
    --check-citations a0/a1/evidence/hostile_candidate.json > "$OUT/out_h5_citations.json" 2>&1
rc=$?
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("   citations checked:",
  d["citations_checked"], " dangling:", d["dangling"], " verdict:", d["verdict"])' "$OUT/out_h5_citations.json"
[ "$rc" -eq 0 ] || { echo "   FAIL rc=$rc"; fail=1; }

printf '\n'
if [ "$fail" -eq 0 ]; then
    echo "a1-hygiene: PASS (5/5) — the tree is left as it was"
else
    echo "a1-hygiene: FAIL — see the steps above"
fi
exit "$fail"
