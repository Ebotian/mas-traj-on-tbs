#!/usr/bin/env bash
# Is a reference run reproducible?  INTERFACE.md section 6 rule 4 demands
# byte-identical output for a repeated (candidate, graph, seed) triple; MQLib is
# terminated by wall clock, so this checks what actually happens.
#
#   bash tools/check_determinism.sh [graph.json] [workdir]
#
# For each of three heuristics it runs the same (graph, heuristic, seed) twice
# at 30 s and reports separately whether the stdout is byte-identical and
# whether the printed solution line is.  The solution line is what becomes the
# partition, so it is the line that matters for R_i.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${2:-/tmp/mcwork}"
GRAPH="${1:-$HERE/../suite/dev/G_dev_0003.json}"
BIN="$WORK/MQLib/bin/MQLib"
SEED=1337
LIMIT=30

mkdir -p "$WORK/inputs"
INPUT="$WORK/inputs/$(basename "$GRAPH" .json).txt"
python3 "$HERE/tools/to_mqlib.py" "$GRAPH" "$INPUT" >/dev/null

for H in BURER2002 FESTA2002GPR DESOUSA2013; do
  for R in 1 2; do
    "$BIN" -h "$H" -fM "$INPUT" -r "$LIMIT" -s "$SEED" -ps \
      > "$WORK/det_${H}_${R}.txt" 2>&1
  done
  A="$WORK/det_${H}_1.txt"; B="$WORK/det_${H}_2.txt"
  objA=$(head -1 "$A" | cut -d, -f4); objB=$(head -1 "$B" | cut -d, -f4)
  solA=$(tail -1 "$A"); solB=$(tail -1 "$B")
  if cmp -s "$A" "$B"; then stdout_same=IDENTICAL; else stdout_same=DIFFERS; fi
  if [ "$solA" = "$solB" ]; then sol_same=IDENTICAL; else sol_same=DIFFERS; fi
  printf '%-14s seed=%s limit=%ss  objective %s/%s  stdout=%s  solution_line=%s\n' \
    "$H" "$SEED" "$LIMIT" "$objA" "$objB" "$stdout_same" "$sol_same"
done
echo
echo "stdout differs because MQLib's history field records the wall-clock second"
echo "at which each incumbent was found; the partition itself is what is compared."
