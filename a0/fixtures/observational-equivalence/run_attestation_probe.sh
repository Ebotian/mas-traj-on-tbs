#!/usr/bin/env bash
# TOCTOU probe for the attestation half, with the study's usual two controls:
# an experiment whose negative control is *shown to fail* before the positive
# control is trusted.
#
#   --no-stage  the attestor hashes the path and then executes the path.  A
#               modification of the evaluator between hashing and execution
#               changes what runs.  Control NEGATIVE: expect a REJECT, because
#               each outcome self-reports the source digest of the bytes that
#               really ran (the cross-check), not because the record noticed the
#               file change.
#   --stage     (default) the attestor copies the declared source files and
#               executes the copies.  The same modification of the original has
#               no effect on what runs.  Control POSITIVE: expect an ACCEPT, and
#               the outcomes must equal the frozen E* numbers.
#
# Nothing here touches a0/tasks/circle-packing: the evaluator under the swap is a
# copy inside this fixture's own out/ tree.
set -u
FX=/home/ebt/rsi-dev/a0/fixtures/observational-equivalence
TASK=/home/ebt/rsi-dev/a0/tasks/circle-packing
W=$FX/out/toctou
rm -rf "$W"; mkdir -p "$W/live" "$W/evil"
cp "$TASK/e_star.py" "$TASK/e_star_child.py" "$W/live/"
python3 - "$TASK/e_star.py" "$W/evil/e_star.py" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
text = text.replace('E_STAR_VERSION = "1.0.0"', 'E_STAR_VERSION = "1.0.0-evil-swap"')
text = text.replace("sum_radii = sum(r for _, _, r in circles)",
                    "sum_radii = sum(r for _, _, r in circles) + 1e-3")
assert "evil-swap" in text and "+ 1e-3" in text
open(dst, "w").write(text)
PY
cp "$TASK/e_star_child.py" "$W/evil/"
echo "live e_star.py   sha256 $(sha256sum "$W/live/e_star.py" | cut -d' ' -f1)   (clean E*)"
echo "evil e_star.py   sha256 $(sha256sum "$W/evil/e_star.py" | cut -d' ' -f1)   (sum_radii + 1e-3)"

echo
echo "############ CONTROL NEGATIVE: --no-stage, evaluator swapped mid-run ############"
( sleep 6; cp "$W/evil/e_star.py" "$W/live/e_star.py"; echo "[swap] $W/live/e_star.py <- evil" ) &
python3 "$FX/attest.py" attest --evaluator-dir "$W/live" --no-stage --delay-before-exec 10 \
    --label toctou_nostage --out "$FX/out/attestation/toctou.nostage.json" 2>&1 | tail -14
echo "exit=$?"
wait

echo
echo "############ CONTROL POSITIVE: --stage (default), same swap ############"
rm -rf "$W/live2"; mkdir -p "$W/live2"
cp "$TASK/e_star.py" "$TASK/e_star_child.py" "$W/live2/"
( sleep 6; cp "$W/evil/e_star.py" "$W/live2/e_star.py"; echo "[swap] $W/live2/e_star.py <- evil" ) &
python3 "$FX/attest.py" attest --evaluator-dir "$W/live2" --stage --delay-before-exec 10 \
    --label toctou_stage --out "$FX/out/attestation/toctou.stage.json" 2>&1 | tail -14
echo "exit=$?"
wait

echo
echo "############ what the two records say ############"
python3 - "$FX/out/attestation/toctou.nostage.json" "$FX/out/attestation/toctou.stage.json" <<'PY'
import json, sys
for path in sys.argv[1:]:
    d = json.load(open(path))
    print(f"{d['label']}:")
    print(f"  staged={d['staged']}  measured e_star.py sha256={d['measured_records'][0]['sha256']}")
    print(f"  outcomes self-report the launched digest: {d['outcome_self_reports_match_launched_bytes']}")
    print(f"  objective of c01 in the attested run: "
          f"{[r['objective_value'] for r in d['rows'] if r['candidate_id'] == 'c01_good_hex'][0]!r}")
    print(f"  outcome self-reported e_star_version-source sha256: "
          f"{[r['outcome_self_reported_source_sha256'] for r in d['rows']][0]}")
    print(f"  VERDICT: {d['verdict']}")
PY
