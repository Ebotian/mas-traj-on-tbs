#!/bin/bash
# Fusion round demo: A2A carries the request/response; git carries the artifacts (original mechanism kept).
# Round 1: A->B review; Round 2: B->A review; then both daemons restart (recovery re-check).
python3 - <<'PY'
import json, urllib.request, time, subprocess, hashlib

def call(sh, method, params):
    req=urllib.request.Request(sh['endpoint'], data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json","A2A-Version":"1.0","authorization":"Bearer "+sh['secret'],
                 "x-qwen-caller-id":sh['callerId'],"x-qwen-agent-id":sh['agentId'],"x-qwen-workspace-id":sh['workspaceId']})
    return json.load(urllib.request.urlopen(req, timeout=30))

def wait(sh, tid, out):
    for i in range(40):
        time.sleep(3)
        t=call(sh, "GetTask", {"id":tid})
        st=t['result']['status']['state']
        if st in ("TASK_STATE_COMPLETED","TASK_STATE_FAILED","TASK_STATE_CANCELED"):
            json.dump(t, open(out,'w'))
            ans=t['result'].get('artifacts') or []
            return st, (ans[0]['parts'][0]['text'] if ans else '')
    return 'TIMEOUT', ''

def commit(repo, msg):
    subprocess.run(['git','-C',repo,'add','-A'], check=True)
    subprocess.run(['git','-C',repo,'-c','user.name=a2a-fusion','-c','user.email=fusion@local','commit','-m',msg], check=True)

for d in ('/root/wt-a/rounds','/root/wt-b/rounds'):
    subprocess.run(['mkdir','-p',d],check=True)

# Round 1: A -> B
sha=json.load(open('/root/.share-to-b.json'))
text=("Review request r01 (from peer A). Artifact under review: 'The cache key is the raw input string.' "
      "Reply in one short paragraph: is this sufficient as a cache key, and what is the top risk?")
r=call(sha,"SendMessage",{"message":{"role":"ROLE_USER","messageId":"r01","parts":[{"text":text}]}})
tid=r['result']['task']['id']
st,ans=wait(sha,tid,'/tmp/r01-task.json')
h=hashlib.sha256(ans.encode()).hexdigest()[:16]
json.dump({"round":"r01","direction":"A->B","task":tid,"request":text}, open('/root/wt-a/rounds/r01-request.json','w'), indent=1)
json.dump({"round":"r01","direction":"A->B","task":tid,"answer":ans,"state":st,"answer_sha256_16":h}, open('/root/wt-a/rounds/r01-answer.json','w'), indent=1)
open('/root/wt-a/rounds/refs-a2a.jsonl','a').write(json.dumps({"round":"r01","task":tid,"sha256_16":h,"state":st})+"\n")
commit('/root/wt-a',f"r01: A->B review via A2A (task {tid})")
json.dump({"round":"r01","role":"B-side record","task":tid,"answer_sha256_16":h}, open('/root/wt-b/rounds/r01-b-record.json','w'), indent=1)
commit('/root/wt-b',f"r01: B-side record of its A2A answer (task {tid})")
print("R01", st, "task", tid, "sha16", h)

# Round 2: B -> A
sha=json.load(open('/root/.share-to-a.json'))
text=("Review request r02 (from peer B). Artifact under review: 'Retries use a fixed 3 attempts with no backoff.' "
      "Reply in one short paragraph: the main failure mode and a minimal fix.")
r=call(sha,"SendMessage",{"message":{"role":"ROLE_USER","messageId":"r02","parts":[{"text":text}]}})
tid=r['result']['task']['id']
st,ans=wait(sha,tid,'/tmp/r02-task.json')
h=hashlib.sha256(ans.encode()).hexdigest()[:16]
json.dump({"round":"r02","direction":"B->A","task":tid,"answer":ans,"state":st,"answer_sha256_16":h}, open('/root/wt-b/rounds/r02-answer.json','w'), indent=1)
open('/root/wt-b/rounds/refs-a2a.jsonl','a').write(json.dumps({"round":"r02","task":tid,"sha256_16":h,"state":st})+"\n")
commit('/root/wt-b',f"r02: B->A review via A2A (task {tid})")
json.dump({"round":"r02","role":"A-side record","task":tid,"answer_sha256_16":h}, open('/root/wt-a/rounds/r02-a-record.json','w'), indent=1)
commit('/root/wt-a',f"r02: A-side record of its A2A answer (task {tid})")
print("R02", st, "task", tid, "sha16", h)
PY

echo '== git logs:'
git -C /root/wt-a log --oneline | head -4
git -C /root/wt-b log --oneline | head -4
echo '== refs ledgers:'
cat /root/wt-a/rounds/refs-a2a.jsonl /root/wt-b/rounds/refs-a2a.jsonl

echo '== restart both daemons; grants + old tasks must survive'
pkill -f "[q]wen serve" 2>/dev/null; sleep 1
export OPENAI_API_KEY="$A_KEY" OPENAI_BASE_URL="$A_BASE" OPENAI_MODEL="deepseek-flash"
cd /root/wt-a && nohup qwen serve --no-web --workspace /root/wt-a --port 4170 > /root/serve-a2.log 2>&1 &
export OPENAI_API_KEY="$B_KEY" OPENAI_BASE_URL="$B_BASE" OPENAI_MODEL="qwen3.8-flash"
cd /root/wt-b && nohup qwen serve --no-web --workspace /root/wt-b --port 4171 > /root/serve-b2.log 2>&1 &
sleep 7
python3 - <<'PY'
import json, urllib.request
for name, f in (("B","/root/.share-to-b.json"),("A","/root/.share-to-a.json")):
    sh=json.load(open(f))
    def call(method, params):
        req=urllib.request.Request(sh['endpoint'], data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
            headers={"content-type":"application/json","A2A-Version":"1.0","authorization":"Bearer "+sh['secret'],
                     "x-qwen-caller-id":sh['callerId'],"x-qwen-agent-id":sh['agentId'],"x-qwen-workspace-id":sh['workspaceId']})
        return json.load(urllib.request.urlopen(req, timeout=30))
    t=call("ListTasks", {})
    tasks=t.get('result',{}).get('tasks',[])
    print(f"after restart, {name} daemon: grant valid, ListTasks -> {len(tasks)} tasks")
PY
