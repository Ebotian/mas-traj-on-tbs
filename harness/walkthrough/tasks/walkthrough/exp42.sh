#!/bin/bash
# exp42.sh — drive the rest of the w6 4x2 experiment unattended:
#   0) wait until no run container is left (pilots finished; 60 min cap)
#   1) verify both pilots' collected state.json is NORMAL (else ABORT)
#   2) meter read -> wave1 = N x4 -> meter read
#   3) wave2 = R x4 -> meter read -> summary
# Artifacts: logs/exp42.log, logs/meter.rcs, logs/<job>.log, logs/<prefix>.rcs
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"   # harbor-runs root
W=$ROOT/walkthrough/tasks/walkthrough
L=$ROOT/logs
mkdir -p "$L"
B='http://127.0.0.1:10086/command'
JS='(async () => { const out=[]; for (const e of document.querySelectorAll("[aria-valuenow]")) { out.push(e.getAttribute("aria-valuenow")); } return JSON.stringify(out); })()'

meter() {  # $1 = label
  local label="$1" out val
  curl --noproxy '*' -s --max-time 15 -X POST "$B" -H 'Content-Type: application/json' \
    -d '{"action":"navigate","args":{"url":"https://platform.qianwenai.com/home/analytics/token-plan/individual","newTab":false},"session":"credit-read"}' >/dev/null 2>&1
  sleep 5
  out=$(curl --noproxy '*' -s --max-time 15 -X POST "$B" -H 'Content-Type: application/json' \
    -d "{\"action\":\"evaluate\",\"args\":{\"code\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$JS")},\"session\":\"credit-read\"}" 2>/dev/null)
  val=$(printf '%s' "$out" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin); arr=json.loads(d["data"]["value"])
    print(arr[1] if len(arr)>1 else (arr[0] if arr else "?"))
except Exception:
    print("read-failed")' 2>/dev/null)
  echo "$(date -u +%H:%M:%S) $label booster=$val" | tee -a "$L/meter.rcs"
}

check_normal() {  # $1 = job
  python3 - "$ROOT/jobs/agent/$1" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1])
for p in root.rglob("state.json"):
    if "collect" in str(p):
        d=json.loads(p.read_text())
        n=d.get("normal")
        if n is None:
            n=(d.get("rc_a")==0 and d.get("rc_b")==0 and d.get("stop_a")
               and d.get("stop_b") and d.get("consensus_on_main"))
        print(n); raise SystemExit
print("missing")
PY
}

echo "$(date -u) exp42 start" | tee -a "$L/exp42.log"
# 0) wait for the pilots (run containers gone)
waited=0
while docker ps --format '{{.Names}}' | grep -q env-main; do
  sleep 20; waited=$((waited+20))
  if [ "$waited" -gt 3600 ]; then echo "$(date -u) ABORT: pilot wait timeout" | tee -a "$L/exp42.log"; exit 4; fi
done
sleep 30
echo "$(date -u) pilots gone after ${waited}s" | tee -a "$L/exp42.log"
# 1) pilot verdicts
for j in w6n-pilot w6r-pilot; do
  n=$(check_normal "$j")
  echo "pilot $j normal=$n" | tee -a "$L/exp42.log"
  [ "$n" = "True" ] || { echo "$(date -u) ABORT: pilot $j not normal" | tee -a "$L/exp42.log"; exit 3; }
done
for s in oWQQG3N SnLfTz5; do
  s2=$(printf '%s' "$s" | tr 'A-Z' 'a-z')
  if docker image inspect "task-restricted__${s2}__env-main" >/dev/null 2>&1; then
    echo "pilot image ${s2} STILL PRESENT" | tee -a "$L/exp42.log"
  else
    echo "pilot image ${s2} cleaned (normal-exit cleanup ok)" | tee -a "$L/exp42.log"
  fi
done
# 2) wave 1 = N x4
meter "pre-wave1"
bash "$W/wave.sh" prompt-w6n.md w6n 4 1 2>&1 | tee -a "$L/exp42.log"
meter "post-wave1"
# 3) wave 2 = R x4
bash "$W/wave.sh" prompt-w6r.md w6r 4 1 2>&1 | tee -a "$L/exp42.log"
meter "post-wave2"
# 4) summary
echo "$(date -u) exp42 done" | tee -a "$L/exp42.log"
for f in "$L/w6n.rcs" "$L/w6r.rcs" "$L/meter.rcs"; do echo "== $f"; cat "$f" | tee -a "$L/exp42.log"; echo; done
