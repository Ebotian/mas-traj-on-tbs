#!/bin/sh
# Every command this directory's report rests on, in order. Model-free; nothing
# here spends money and nothing here edits a file outside a0/verify/a1-final/.
#
#   sh a0/verify/a1-final/run_all.sh          # all of it (a few minutes)
#
# Two of the commands *read* other workstreams' directories by running their own
# entry points, which is the point: `a0/a1/verify.py`, `a0/a1/kapso_t1/verify.py`
# and `a0/a1/calibration/verify.py` are the artifacts' own re-runnable claims.
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

run v1-identity        python3 a0/verify/a1-final/v1_identity.py
run v1b-superseded     python3 a0/verify/a1-final/v1b_superseded.py
run v1-verify.py       python3 a0/a1/verify.py
run v1-kapso-t1        python3 a0/a1/kapso_t1/verify.py
run v2-closures        python3 a0/verify/a1-final/v2_closures.py
run v4-bhard           python3 a0/verify/a1-final/v4_bhard.py
run v4-calibration     python3 a0/a1/calibration/verify.py
run v5-tracebound      python3 a0/verify/a1-final/v5_tracebound.py
run v6-labels          python3 a0/verify/a1-final/v6_labels.py
run v7-staging         python3 a0/verify/a1-final/v7_staging.py
run v8-consequences    python3 a0/verify/a1-final/v8_consequences.py

printf '\n===== tree status after the run =====\n'
git status --porcelain
