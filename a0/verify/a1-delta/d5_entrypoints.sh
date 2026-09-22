#!/bin/sh
# The five entry points a third party would run, in the order the assignment lists them,
# with the artifacts each one rewrites restored afterwards and the restoration reported.
# Model-free: none of these spends CEq (kapso_t1 and calibration skip their paid arms by
# their own flags).
set -u
HERE=$(dirname "$0")
cd "$HERE/../../.." || exit 1

run() {
    name=$1
    shift
    printf '\n===== %s =====\n' "$name"
    "$@" >"$HERE/out_d5_$name.txt" 2>&1
    rc=$?
    printf '[%s exit %s]\n' "$name" "$rc"
    tail -4 "$HERE/out_d5_$name.txt"
    return 0
}

WATCHED="a0/tasks/maxcut/conformance.report.json a0/tasks/maxcut/gates/restamp.evidence.json"

run a1_verify            python3 a0/a1/verify.py
run kapso_t1_verify      python3 a0/a1/kapso_t1/verify.py
run restamp_evidence     python3 a0/tasks/maxcut/gates/restamp_evidence.py --before 7bf8a14b \
                             --out "$HERE/out_d3_restamp.evidence.json"
run conformance          python3 a0/tasks/maxcut/conformance.py --check
run calibration_verify   python3 a0/a1/calibration/verify.py --with-rehearsal

printf '\n===== artifacts rewritten by the entry points =====\n'
for path in $WATCHED; do
    if ! git diff --quiet -- "$path"; then
        printf 'rewritten by an entry point, restored: %s\n' "$path"
        git diff --stat -- "$path"
        git checkout -- "$path"
    fi
done
printf 'git status after the restores:\n'
git status --porcelain
