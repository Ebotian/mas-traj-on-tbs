#!/usr/bin/env bash
# Resume / top-up the reference-target build.  Safe to interrupt and re-run.
#
# Every stage below is idempotent and writes its results to disk *before* it
# counts, so re-running this script after an interruption (or a timeout) tops up
# whatever is missing instead of restarting:
#
#   ensemble     run_ensemble.py skips any (graph, heuristic, seed) whose record
#                already exists with status "ok"          -> logs/
#   top-up       same driver, different outdir and time limit  -> logs_topup/
#   SCIP         scip_maxcut.py skips a graph whose stored attempt already ran
#                at a time limit >= the requested one     -> scip/
#   upper bounds ub_parallel.py skips a graph whose cached entry matches the
#                bound parameters and the anchored lower bound -> ub/
#   table        build_targets.py + build_coverage.py just re-read the above
#
# Usage:
#   bash tools/resume.sh [workdir] [jobs]
#
#   workdir (default /tmp/mcwork) must already contain the MQLib build; run
#   build/build_mqlib.sh to create it.  Nothing is written into ../suite/.
#
# Budget knobs (defaults are the headline budget; lower them only deliberately):
#   ENSEMBLE_TIME=30     TOPUP_TIME=300    SCIP_TIME=120
#   JOBS=11              ROLE="dev eval calibration"
# Set SKIP_TOPUP=1 / SKIP_SCIP=1 / SKIP_UB=1 to run a subset of the stages.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-/tmp/mcwork}"
JOBS="${JOBS:-11}"
BIN="$WORK/MQLib/bin/MQLib"
MANIFEST="$HERE/../suite/manifest.json"
PY="${PY:-python3}"
ENSEMBLE_TIME="${ENSEMBLE_TIME:-30}"
TOPUP_TIME="${TOPUP_TIME:-300}"
SCIP_TIME="${SCIP_TIME:-120}"
ROLES="${ROLE:-dev eval calibration}"

test -f "$MANIFEST" || { echo "suite manifest missing: $MANIFEST" >&2; exit 1; }
test -x "$BIN" || { echo "MQLib binary missing: $BIN (run build/build_mqlib.sh)" >&2; exit 1; }
cd "$HERE"

echo "== 1/6 ensemble: 6 heuristics x 5 seeds x ${ENSEMBLE_TIME}s, all 60 graphs =="
"$PY" tools/run_ensemble.py --binary "$BIN" --manifest "$MANIFEST" \
    --roles $ROLES --outdir logs --scratch "$WORK/inputs" \
    --jobs "$JOBS" --time-limit "$ENSEMBLE_TIME"

if [ "${SKIP_SCIP:-0}" != "1" ]; then
  echo "== 2/6 exact certification attempt: SCIP, ${SCIP_TIME}s per graph =="
  "$PY" tools/scip_maxcut.py --manifest "$MANIFEST" --roles $ROLES \
      --out scip --limit "$SCIP_TIME" --jobs "$JOBS"
fi

if [ "${SKIP_TOPUP:-0}" != "1" ]; then
  echo "== 3/6 assemble a provisional targets.json (the gate can start here) =="
  "$PY" tools/build_targets.py --logs logs \
      --manifest "$MANIFEST" --out targets.json --ub-cache ub

  echo "== 4/6 top-up: ${TOPUP_TIME}s runs on the graphs SCIP did not certify =="
  "$PY" - "$HERE" "$MANIFEST" <<'PYEOF' > "$WORK/uncertified.txt"
import json, os, sys
here, manifest = sys.argv[1], sys.argv[2]
root = os.path.dirname(os.path.abspath(manifest))
man = {e["graph_id"]: e for e in json.load(open(manifest))["graphs"]}
t = json.load(open(os.path.join(here, "targets.json")))
n = 0
for gid, g in sorted(t["graphs"].items()):
    if not g.get("opt_certified"):
        print(os.path.join(root, man[gid]["path"]))
        n += 1
print("uncertified graphs: %d" % n, file=sys.stderr)
PYEOF
  if [ -s "$WORK/uncertified.txt" ]; then
    # shellcheck disable=SC2046
    "$PY" tools/run_ensemble.py --binary "$BIN" \
        --graphs $(tr '\n' ' ' < "$WORK/uncertified.txt") \
        --outdir logs_topup --scratch "$WORK/inputs" --jobs "$JOBS" \
        --time-limit "$TOPUP_TIME" \
        --heuristics BURER2002 FESTA2002GPR LAGUNA2009HCE --seeds 1337 65521
  else
    echo "top-up: every graph already certified; nothing to do"
  fi
fi

if [ "${SKIP_UB:-0}" != "1" ]; then
  echo "== 5/6 rigorous upper bounds U_i =="
  "$PY" tools/ub_parallel.py --manifest "$MANIFEST" --targets targets.json \
      --out ub --roles $ROLES --jobs "$JOBS" --iters 4000
fi

echo "== 6/6 final table + coverage =="
"$PY" tools/build_targets.py --logs logs --manifest "$MANIFEST" \
    --out targets.json --ub-cache ub
"$PY" tools/build_coverage.py --manifest "$MANIFEST" --out coverage.json

echo "done: targets.json + coverage.json refreshed"
