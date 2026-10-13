#!/bin/bash
# Retry the restart-interrupted r01 round; record attempt-2 artifacts and commits.
python3 - <<'PY'
import json, urllib.request, time, subprocess, hashlib, datetime

def call(sh, method, params):
    req=urllib.request.Request(sh['endpoint'], data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json","A2A-Version":"1.0","authorization":"Bearer "+sh['secret'],
                 "x-qwen-caller-id":sh['callerId'],"x-qwen-agent-id":sh['agentId'],"x-qwen-workspace-id":sh['workspaceId']})
    return json.load(urllib.request.urlopen(req, timeout=30))

sh=json.load(open('/root/.share-to-b.json'))
t0=datetime.datetime.utcnow().isoformat()
msg={"role":"ROLE_USER","messageId":"r01-retry","contextId":"c4c61d98-d721-4914-8718-90d241af8495",
     "parts":[{"text":"Retry of review request r01 (the previous attempt was interrupted by a restart). Artifact under review: 'The cache key is the raw input string.' Reply in one short paragraph: is this sufficient as a cache key, and what is the top risk?"}]}
r=call(sh,"SendMessage",{"message":msg})
tid=r['result']['task']['id']
print("retry task", tid, "start", t0)
json.dump(r, open('/root/.fusion-r01-retry-send.json','w'))
st=''; ans=''; i=-1
for i in range(100):
    time.sleep(3)
    t=call(sh,"GetTask",{"id":tid})
    st=t['result']['status']['state']
    if st in ("TASK_STATE_COMPLETED","TASK_STATE_FAILED","TASK_STATE_CANCELED"):
        json.dump(t, open('/root/.fusion-r01-retry.json','w'))
        a=t['result'].get('artifacts') or []
        ans=a[0]['parts'][0]['text'] if a else ''
        break
t1=datetime.datetime.utcnow().isoformat()
h=hashlib.sha256(ans.encode()).hexdigest()[:16]
print("retry", st, "end", t1, "window_s", (i+1)*3, "sha16", h)
print("answer:", ans[:400])

def commit(repo, msg_):
    subprocess.run(['git','-C',repo,'add','-A'], check=True)
    subprocess.run(['git','-C',repo,'-c','user.name=a2a-fusion','-c','user.email=fusion@local','commit','-m',msg_], check=True)

if st=='TASK_STATE_COMPLETED':
    json.dump({"round":"r01","attempt":2,"task":tid,"answer":ans,"state":st,"answer_sha256_16":h,"window_s":(i+1)*3},
              open('/root/wt-a/rounds/r01-answer-retry.json','w'), indent=1)
    open('/root/wt-a/rounds/refs-a2a.jsonl','a').write(json.dumps({"round":"r01","attempt":2,"task":tid,"sha256_16":h,"state":st})+"\n")
    commit('/root/wt-a', f"r01: answer after retry (task {tid}); attempt-1 interruption recorded")
    json.dump({"round":"r01","attempt":2,"role":"B-side record","task":tid,"answer_sha256_16":h},
              open('/root/wt-b/rounds/r01-b-record-retry.json','w'), indent=1)
    commit('/root/wt-b', f"r01: B-side retry record (task {tid})")
PY
echo '== git logs after retry:'
git -C /root/wt-a log --oneline | head -5
git -C /root/wt-b log --oneline | head -5
echo '== refs ledgers:'
cat /root/wt-a/rounds/refs-a2a.jsonl
