#!/usr/bin/env bash
# Closure-relevant test: run kilo's full agentic tool loop with NO external
# network at all (private user/mount/net namespace, loopback only) against a
# local fake OpenAI-compatible endpoint on 127.0.0.1.
#
# If kilo completes the loop here, then resolving and driving an
# @ai-sdk/openai-compatible provider requires ZERO network at first use: the
# provider is bundled into the 169 MB standalone binary, not npm-fetched.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PROBE=/tmp/kilo-offline
rm -rf "$PROBE"; mkdir -p "$PROBE/wt" "$PROBE/cfg" "$PROBE/data" "$PROBE/cache" "$PROBE/state"
cd "$PROBE/wt" && git init -q . && git config user.email a@b.c && git config user.name t

python3 - "$PROBE" <<'PY'
import json, sys
p = sys.argv[1]
perm = {"interactive_terminal": "deny", "plan_enter": "deny", "plan_exit": "deny",
        "question": "deny", "suggest": "deny", "task": "deny"}
tools = {"suggest": False, "task": False}
cfg = {
    "$schema": "https://app.kilo.ai/config.json",
    "agent": {"loreley-headless": {"description": "offline probe", "mode": "primary",
                                    "permission": dict(perm), "tools": dict(tools)}},
    "default_agent": "loreley-headless",
    "permission": perm,
    "tools": tools,
    "provider": {"loreley-openai-compatible": {
        "name": "offline fake",
        "npm": "@ai-sdk/openai-compatible",
        "options": {"apiKey": "{env:OFFLINE_FAKE_KEY}",
                    "baseURL": "http://127.0.0.1:18123/v1"},
        "models": {"deepseek-v4-pro": {"name": "deepseek-v4-pro"}},
    }},
    "model": "loreley-openai-compatible/deepseek-v4-pro",
}
open(f"{p}/config-content.json", "w").write(json.dumps(cfg, separators=(",", ":"), sort_keys=True))
PY

export OFFLINE_FAKE_KEY="fake-offline-key-not-a-secret"
export KILO_CONFIG_CONTENT="$(cat "$PROBE/config-content.json")"
export XDG_CONFIG_HOME="$PROBE/cfg" XDG_DATA_HOME="$PROBE/data" \
       XDG_CACHE_HOME="$PROBE/cache" XDG_STATE_HOME="$PROBE/state"

unshare -rmn bash -s <<INNER > "$PROBE/probe.log" 2>&1
set -u
ip link set lo up
echo "== netns interfaces =="; ip -brief addr
echo "== netns routes (expect empty) =="; ip route; echo "(end route table)"
timeout 3 bash -c 'exec 3<>/dev/tcp/1.1.1.1/443' 2>/dev/null \
  && echo "EGRESS OPEN (bad)" || echo "egress BLOCKED: network unreachable"
timeout 5 getent hosts registry.npmjs.org >/dev/null 2>&1 \
  && echo "DNS RESOLVED (bad)" || echo "DNS for registry.npmjs.org FAILS"

python3 $HERE/fake_openai_server.py 18123 $PROBE/requests.log &
SRV=\$!
sleep 1
cd $PROBE/wt
timeout -k 5 200 kilo run --auto --pure --dir $PROBE/wt --format json \
  --title kilo-offline-probe --agent loreley-headless \
  -m loreley-openai-compatible/deepseek-v4-pro \
  "Create a file named offline.txt containing the text kilo-offline-ok. Then stop." \
  > $PROBE/run.json 2>$PROBE/run.err
echo "KILO_EXIT=\$?"
kill \$SRV 2>/dev/null
INNER

echo "== probe.log =="
cat "$PROBE/probe.log"
echo "== produced file =="
cat "$PROBE/wt/offline.txt" 2>&1
echo "== requests the fake endpoint saw =="
cat "$PROBE/requests.log" 2>/dev/null || echo "(none)"
echo "== run.json events =="
python3 -c "
import json,sys
try: lines=open('$PROBE/run.json').read().splitlines()
except Exception as e: print('no run.json',e); sys.exit()
for l in lines:
    l=l.strip()
    if not l.startswith('{'): continue
    e=json.loads(l)
    print(e.get('type'), json.dumps(e.get('part',{}).get('tokens') or e.get('part',{}).get('tool') or '')[:160])
"
echo "== run.err tail =="
tail -5 "$PROBE/run.err" 2>/dev/null
