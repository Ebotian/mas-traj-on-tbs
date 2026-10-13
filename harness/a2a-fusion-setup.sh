#!/bin/bash
# Fusion wiring step 1: two side-by-side daemons (A=deepseek-flash on 4170, B=qwen3.8-flash on 4171),
# one agent each, mutual grants, and one round trip in each direction.
pkill -f "[q]wen serve" 2>/dev/null; sleep 1
mkdir -p /root/wt-a /root/wt-b
for d in /root/wt-a /root/wt-b; do [ -d "$d/.git" ] || git -C "$d" init -q; done

# daemon A (deepseek side)
export OPENAI_API_KEY="$A_KEY" OPENAI_BASE_URL="$A_BASE" OPENAI_MODEL="deepseek-flash"
cd /root/wt-a && nohup qwen serve --no-web --workspace /root/wt-a --port 4170 > /root/serve-a.log 2>&1 &
sleep 5
# daemon B (qwen3.8 side)
export OPENAI_API_KEY="$B_KEY" OPENAI_BASE_URL="$B_BASE" OPENAI_MODEL="qwen3.8-flash"
cd /root/wt-b && nohup qwen serve --no-web --workspace /root/wt-b --port 4171 > /root/serve-b.log 2>&1 &
sleep 6

J="content-type: application/json"
echo '== cards:'
curl -s -m 4 http://127.0.0.1:4170/.well-known/agent-card.json | head -c 140; echo
curl -s -m 4 http://127.0.0.1:4171/.well-known/agent-card.json | head -c 140; echo

echo '== create agent on A (deepseek):'
CA=$(curl -s -X POST "http://127.0.0.1:4170/workspaces/%2Froot%2Fwt-a/agent/agents" -H "$J" -d '{"name":"peer-a","model":"deepseek-flash","instructions":"You are peer A (deepseek). Answer briefly."}')
echo "$CA"
AID=$(echo "$CA" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id",""))')
echo '== create agent on B (qwen3.8):'
CB=$(curl -s -X POST "http://127.0.0.1:4171/workspaces/%2Froot%2Fwt-b/agent/agents" -H "$J" -d '{"name":"peer-b","model":"qwen3.8-flash","instructions":"You are peer B (qwen3.8). Answer briefly."}')
echo "$CB"
BID=$(echo "$CB" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id",""))')
echo "AID=$AID BID=$BID"

echo '== mutual grants (share-to-a held by B side; share-to-b held by A side):'
curl -s -X POST "http://127.0.0.1:4170/workspaces/%2Froot%2Fwt-a/agent/agents/$AID/shares" -H "$J" > /root/.share-to-a.json
head -c 140 /root/.share-to-a.json; echo
curl -s -X POST "http://127.0.0.1:4171/workspaces/%2Froot%2Fwt-b/agent/agents/$BID/shares" -H "$J" > /root/.share-to-b.json
head -c 140 /root/.share-to-b.json; echo

echo '== round trip A->B (uses share-to-b; B daemon responds):'
python3 - <<'PY'
import json, urllib.request, time
sh=json.load(open('/root/.share-to-b.json'))
def call(method, params):
    req=urllib.request.Request(sh['endpoint'], data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json","A2A-Version":"1.0","authorization":"Bearer "+sh['secret'],
                 "x-qwen-caller-id":sh['callerId'],"x-qwen-agent-id":sh['agentId'],"x-qwen-workspace-id":sh['workspaceId']})
    return json.load(urllib.request.urlopen(req, timeout=30))
r=call("SendMessage", {"message":{"role":"ROLE_USER","messageId":"rr-1","parts":[{"text":"Reply with exactly: B-ON-QWEN38"}]}})
tid=r['result']['task']['id']; print('task', tid)
json.dump(r, open('/root/.fusion-t1.json','w'))
for i in range(40):
    time.sleep(3)
    t=call("GetTask", {"id":tid})
    st=t['result']['status']['state']; json.dump(t, open('/root/.fusion-t1.json','w'))
    if st in ("TASK_STATE_COMPLETED","TASK_STATE_FAILED","TASK_STATE_CANCELED"):
        print('final', st, json.dumps(t['result'].get('artifacts') or [])[:180]); break
PY

echo '== round trip B->A (uses share-to-a; A daemon responds):'
python3 - <<'PY'
import json, urllib.request, time
sh=json.load(open('/root/.share-to-a.json'))
def call(method, params):
    req=urllib.request.Request(sh['endpoint'], data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json","A2A-Version":"1.0","authorization":"Bearer "+sh['secret'],
                 "x-qwen-caller-id":sh['callerId'],"x-qwen-agent-id":sh['agentId'],"x-qwen-workspace-id":sh['workspaceId']})
    return json.load(urllib.request.urlopen(req, timeout=30))
r=call("SendMessage", {"message":{"role":"ROLE_USER","messageId":"rr-2","parts":[{"text":"Reply with exactly: A-ON-DEEPSEEK"}]}})
tid=r['result']['task']['id']; print('task', tid)
json.dump(r, open('/root/.fusion-t2.json','w'))
for i in range(40):
    time.sleep(3)
    t=call("GetTask", {"id":tid})
    st=t['result']['status']['state']; json.dump(t, open('/root/.fusion-t2.json','w'))
    if st in ("TASK_STATE_COMPLETED","TASK_STATE_FAILED","TASK_STATE_CANCELED"):
        print('final', st, json.dumps(t['result'].get('artifacts') or [])[:180]); break
PY

echo '== model ids seen in logs:'
grep -o "qwen3.8-flash" /root/serve-b.log | wc -l
grep -o "deepseek-flash" /root/serve-a.log | wc -l
echo '== daemon tails:'; tail -2 /root/serve-a.log; tail -2 /root/serve-b.log
