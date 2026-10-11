#!/bin/bash
# wave.sh — launch K concurrent runs of the walkthrough task with ONE prompt variant.
# Usage: bash wave.sh <prompt-variant> <job-prefix> <K> [start-index]
#   e.g. bash wave.sh prompt-w6n.md w6n 4 1   -> jobs w6n1..w6n4, 15 s apart
# Per-run launcher output: logs/<job>.log ; rc lines appended to logs/<prefix>.rcs
set -eu
VAR="${1:?prompt variant name in this task dir, e.g. prompt-w6n.md}"
PFX="${2:?job prefix, e.g. w6n}"
K="${3:?number of runs}"
START="${4:-1}"
HERE=$(cd "$(dirname "$0")" && pwd)
LOGS="$(cd "$(dirname "$0")/../../.." && pwd)/logs"
mkdir -p "$LOGS"
RC="$LOGS/${PFX}.rcs"; : > "$RC"
for i in $(seq "$START" $((START + K - 1))); do
  JOB="${PFX}${i}"
  ( EXTRA_AE="WT_PROMPT=${VAR}" bash "$HERE/launch.sh" "$JOB" \
      > "$LOGS/$JOB.log" 2>&1
    echo "$JOB rc=$?" >> "$RC" ) &
  sleep 15
done
wait
echo "wave complete ($PFX):"; cat "$RC"
