#!/usr/bin/env bash
# End-to-end reproduction of references/ : build MQLib, run the ensemble on
# every graph of the frozen suite, attempt exact certification with SCIP, and
# assemble targets.json.
#
# Everything is local computation: no model calls, no spend.  The only network
# access is the single `git clone` of MQLib at the pinned commit in
# build/build_mqlib.sh.  Total cost is roughly 16 CPU-hours, i.e. ~85 minutes of
# wall clock at --jobs 11 on a 12-thread box.
#
#   bash tools/reproduce.sh [workdir]
#
# workdir (default /tmp/mcwork) holds the MQLib checkout and the converted
# MQLib input files; nothing is written into ../suite/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-/tmp/mcwork}"
JOBS="${JOBS:-11}"
MANIFEST="$HERE/../suite/manifest.json"
PY="${PY:-python3}"

test -f "$MANIFEST" || { echo "suite manifest missing: $MANIFEST" >&2; exit 1; }
mkdir -p "$WORK"

echo "== step 1/4: build MQLib at the pinned commit =="
bash "$HERE/build/build_mqlib.sh" "$WORK"
BIN="$WORK/MQLib/bin/MQLib"

echo "== step 2/4: ensemble (6 heuristics x 5 seeds x 30 s) =="
"$PY" "$HERE/tools/run_ensemble.py" --binary "$BIN" --manifest "$MANIFEST" \
    --roles dev eval calibration --outdir "$HERE/logs" \
    --scratch "$WORK/inputs" --jobs "$JOBS" --time-limit 30

echo "== step 3/4: exact certification attempt (SCIP, 120 s per graph) =="
"$PY" "$HERE/tools/scip_maxcut.py" --manifest "$MANIFEST" \
    --roles dev eval calibration --out "$HERE/scip" --limit 120 --jobs "$JOBS"

echo "== step 4/4: assemble targets.json =="
"$PY" "$HERE/tools/build_targets.py" --logs "$HERE/logs" --manifest "$MANIFEST" \
    --out "$HERE/targets.json"

echo "done. See $HERE/README.md section 8 for the headline numbers to compare against."
