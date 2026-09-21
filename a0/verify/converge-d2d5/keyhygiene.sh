#!/usr/bin/env bash
# Independent re-run of the D5 key-hygiene search. Values are read into variables
# and never printed. Positive control: EID* (a known-present string).
set -u
REPO=/home/ebt/rsi-dev
ARCH=/home/ebt/rsi-archive
GP=~/gptapi.md

# read the four values by line (1,3,5,7), text after the first ':'
get() { sed -n "${1}p" "$GP" | sed 's/^[^:]*://'; }
K1=$(get 1); K2=$(get 3); K3=$(get 5); K4=$(get 7)
EID=664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328

names=(chagpt deepseek openrouter_openai_compatible gmi-cloud-key control_EIDstar)
vals=("$K1" "$K2" "$K3" "$K4" "$EID")

echo "== A. repo working tree (tracked+untracked, excluding .git) : grep -rIl -F =="
for i in "${!names[@]}"; do
  n=$(grep -rIl -F --exclude-dir=.git -e "${vals[$i]}" "$REPO" 2>/dev/null | wc -l)
  echo "   ${names[$i]}: file-hits=$n"
done

echo
echo "== B. git history: git grep -F over every commit of --all =="
for i in "${!names[@]}"; do
  tot=0
  for c in $(git -C "$REPO" rev-list --all); do
    h=$(git -C "$REPO" grep -F -e "${vals[$i]}" "$c" 2>/dev/null | wc -l)
    tot=$((tot+h))
  done
  echo "   ${names[$i]}: path-hits=$tot"
done

echo
echo "== C. archive decompressed trees: zstd -dc | grep -aF =="
for i in "${!names[@]}"; do
  line="   ${names[$i]}:"
  for t in "$ARCH"/trees/*.tar.zst; do
    h=$(zstd -dc "$t" 2>/dev/null | grep -aF -c -e "${vals[$i]}" 2>/dev/null)
    line="$line $(basename "$t")=$h"
  done
  echo "$line"
done

echo
echo "== D. VACUITY CHECK: grep the compressed .zst DIRECTLY (no decompression) =="
for i in "${!names[@]}"; do
  n=0
  for t in "$ARCH"/trees/*.tar.zst; do
    h=$(grep -aF -c -e "${vals[$i]}" "$t" 2>/dev/null || true)
    n=$((n+${h:-0}))
  done
  echo "   ${names[$i]} (direct-on-.zst): matches=$n"
done
