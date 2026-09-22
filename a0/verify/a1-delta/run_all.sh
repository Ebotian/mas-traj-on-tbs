#!/bin/sh
# Every command this directory's report rests on, in order. Model-free: no campaign, no
# paid probe, no CEq. The only two artifacts outside this directory that any step rewrites
# are restored at the end by `d5_entrypoints.sh`, and the restoration is in the transcript.
#
#   sh a0/verify/a1-delta/run_all.sh          # ~8 minutes
#
set -u
HERE=$(dirname "$0")
cd "$HERE/../../.." || exit 1

run() {
    name=$1
    shift
    printf '\n===== %s =====\n' "$name"
    "$@" 2>&1
    printf '[%s exit %s]\n' "$name" "$?"
}

run d1-kapso-identity   python3 a0/verify/a1-delta/d1_kapso_identity.py
run d1-kapso-verify     python3 a0/a1/kapso_t1/verify.py
run d2-declaration      python3 a0/verify/a1-delta/d2_declaration.py
run d3-gate-restamp     python3 a0/verify/a1-delta/d3_gate_restamp.py
run d4-canary           python3 a0/verify/a1-delta/d4_canary.py
run d5-entrypoints      sh a0/verify/a1-delta/d5_entrypoints.sh
run d6-superseded       python3 a0/verify/a1-delta/d6_superseded.py

printf '\n===== tree status after the run =====\n'
git status --porcelain
