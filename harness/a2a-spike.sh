#!/bin/bash
# A2A spike round trip v2: trust -> create agent -> issue share -> SendMessage -> poll GetTask
B=http://127.0.0.1:4170
WSP='%2Froot%2Fspike'
J="content-type: application/json"
say(){ echo; echo "== $*"; }

say "1 trust state / request"
curl -s $B/workspace/trust; echo
curl -s -X POST $B/workspace/trust/request -H "$J" -d '{"desiredState":"trusted"}'; echo
curl -s $B/workspace/trust; echo

say "2 create agent"
CREATED=$(curl -s -X POST "$B/workspaces/$WSP/agent/agents" -H "$J" -d '{"name":"spike-a","instructions":"You are a test agent. Answer briefly."}')
echo "$CREATED" | head -c 500; echo
AID=$(echo "$CREATED" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print((d.get("agent") or {}).get("id") or d.get("id") or "")')
echo "AID=$AID"

say "3 issue share"
SH=$(curl -s -X POST "$B/workspaces/$WSP/agent/agents/$AID/shares" -H "$J")
echo "$SH" | head -c 500; echo
CALLER=$(echo "$SH" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get("callerId") or "")')
SECRET=$(echo "$SH" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get("secret") or "")')
WSID=$(echo "$SH" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get("workspaceId") or "")')
echo "CALLER=$CALLER WSID=$WSID"

call(){
  curl -s -X POST $B/a2a/v1 -H "$J" -H "A2A-Version: 1.0" -H "authorization: Bearer $SECRET" -H "x-qwen-caller-id: $CALLER" -H "x-qwen-agent-id: $AID" -H "x-qwen-workspace-id: $WSID" -d "$1"
}

say "4 SendMessage"
SENT=$(call '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"role":"ROLE_USER","messageId":"msg-1","parts":[{"text":"Reply with exactly: PONG"}]}}}')
echo "$SENT" | head -c 700; echo
TID=$(echo "$SENT" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(((d.get("result") or {}).get("task") or {}).get("id") or "")')
CTX=$(echo "$SENT" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(((d.get("result") or {}).get("task") or {}).get("contextId") or "")')
echo "TID=$TID CTX=$CTX"

say "5 poll"
for i in $(seq 1 25); do
  sleep 3
  T=$(call "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"GetTask\",\"params\":{\"id\":\"$TID\"}}")
  echo "$T" | head -c 1500 > /root/.spike-final
  ST=$(echo "$T" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
r=d.get("result") or {}
print(json.dumps(r.get("status") or {}))' )
  echo "poll $i: $ST"
  echo "$ST" | grep -qiE "completed|failed|canceled|cancelled|rejected" && break
done
say "final task"
cat /root/.spike-final; echo
say "where records landed"
ls /root/.qwen/tmp/*/agents/ 2>/dev/null
find /root/.qwen/tmp -maxdepth 4 -name 'agents.json' -o -maxdepth 4 -name '*binding*' -o -maxdepth 4 -name 'squads.json' 2>/dev/null | head -8
