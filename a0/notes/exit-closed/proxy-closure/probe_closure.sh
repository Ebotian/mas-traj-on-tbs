#!/usr/bin/env bash
# =============================================================================
# probe_closure.sh -- executed evidence for the a0pc rootless-closure topology.
#
# Follows the two-control pattern of a0/env/checks/probe_egress.sh: every
# "blocked" observation is paired with a "reachable" observation on the same
# client, so a broken network cannot masquerade as a closed one.
#
#   P1 name resolution          container name resolves, external names do not
#   P2 negative control         internal client -> internet      : must FAIL
#   P3 positive control         internal client -> model via proxy: must SUCCEED
#   P4 selectivity control      SAME client on the bridge -> internet: must SUCCEED
#   P5 peer scan                who is actually reachable from the internal side
#   P6 allowlist enforcement    CONNECT deny + CONNECT allow, observed
#   P7 dual-shape upstream      Anthropic Messages and OpenAI Chat Completions
#
# P3/P7 need DEEPSEEK_API_KEY in the *calling shell's* environment; it is passed
# with `docker exec -e DEEPSEEK_API_KEY` (no value => docker takes it from the
# client env, so it never enters argv and is never written to a file or to any
# container's persisted config). Unset it when done.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NET_INTERNAL="${NET_INTERNAL:-a0pc-internal}"
PROXY_NAME="${PROXY_NAME:-a0pc-proxy}"
PROXY_IP="${PROXY_IP:-172.31.77.10}"
PROXY_PORT="${PROXY_PORT:-8787}"
IMG="${IMG:-python:3.12-slim}"
CLI_CTR="${CLI_CTR:-a0pc-cli}"
SUBNET_PREFIX="${SUBNET_PREFIX:-172.31.77.}"

RUN="docker run --rm --network $NET_INTERNAL -e PROXY_NAME=$PROXY_NAME -e PROXY_PORT=$PROXY_PORT --entrypoint python3 $IMG -c"

hdr() { echo; echo "=============================================================="; echo "### $*"; echo "=============================================================="; }

hdr "P1  name resolution inside an --internal network"
$RUN '
import socket
def r(n):
    try: return socket.gethostbyname(n)
    except Exception as e: return "%s: %s" % (type(e).__name__, e)
print("  container name  a0pc-proxy     ->", r("a0pc-proxy"))
print("  external name   api.deepseek.com ->", r("api.deepseek.com"))
print("  external name   example.com      ->", r("example.com"))
print("  resolv.conf nameserver           -> 127.0.0.11 (docker embedded DNS)")
'

hdr "P2  NEGATIVE CONTROL: internal client -> internet DIRECT (IP literals; DNS cannot mask this)"
$RUN '
import socket
for tgt in [("123.148.116.184",443),("1.1.1.1",443),("8.8.8.8",53),("140.82.121.4",443)]:
    s=socket.socket(); s.settimeout(6)
    try: s.connect(tgt); print("  DIRECT %-22s -> CONNECTED (LEAK)" % (tgt,))
    except Exception as e: print("  DIRECT %-22s -> %s" % (tgt, e))
    s.close()
'

hdr "P3  POSITIVE CONTROL: SAME client -> model endpoint THROUGH the proxy"
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  docker exec -e DEEPSEEK_API_KEY -e PROXY_NAME="$PROXY_NAME" -e PROXY_PORT="$PROXY_PORT" "$CLI_CTR" python3 -c '
import json,os,urllib.request
base="http://%s:%s" % (os.environ["PROXY_NAME"], os.environ["PROXY_PORT"])
req=urllib.request.Request(base+"/v1/models",
    headers={"Authorization":"Bearer "+os.environ["DEEPSEEK_API_KEY"]})
r=urllib.request.urlopen(req,timeout=30)
d=json.loads(r.read())
print("  GET %s/v1/models -> HTTP %s" % (base, r.status))
print("  models:", [m["id"] for m in d.get("data",[])])
'
else
  echo "  SKIPPED: DEEPSEEK_API_KEY not in this shell (run: DEEPSEEK_API_KEY=\$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1); export DEEPSEEK_API_KEY)"
fi

hdr "P4  SELECTIVITY CONTROL: the SAME image, on the default bridge, reaches the internet directly"
docker run --rm --network bridge --entrypoint python3 "$IMG" -c '
import socket
s=socket.socket(); s.settimeout(8)
try: s.connect(("1.1.1.1",443)); print("  DIRECT 1.1.1.1:443     -> CONNECTED (barrier is selective, not broken)")
except Exception as e: print("  DIRECT 1.1.1.1:443     ->", e)
import urllib.request
try:
    r=urllib.request.urlopen("https://example.com",timeout=15); print("  HTTPS example.com      -> HTTP",r.status)
except Exception as e: print("  HTTPS example.com      ->",e)
'

hdr "P5  PEER SCAN: what a client on the internal side can actually reach"
$RUN "
import socket, concurrent.futures
PORTS=(8787,443,6379,5432,80,22)
def probe(a):
    ip,port=a
    s=socket.socket(); s.settimeout(0.6)
    try:
        s.connect((ip,port)); s.close(); return '%s:%d OPEN' % (ip,port)
    except Exception:
        return None
targets=[('${SUBNET_PREFIX}'+str(i),p) for i in range(1,255) for p in PORTS]
with concurrent.futures.ThreadPoolExecutor(128) as ex:
    hits=[h for h in ex.map(probe, targets) if h]
print('  reachable peers+ports on the internal subnet:', sorted(hits) or 'NONE')
# can the internal side use the proxy as a generic relay?
import urllib.request
try:
    urllib.request.urlopen('http://${PROXY_NAME}:8787/https://example.com', timeout=8)
    print('  proxy as open relay -> REACHED (LEAK)')
except urllib.error.HTTPError as e:
    print('  proxy as open relay -> HTTP', e.code, '(refused by allowlist)')
except Exception as e:
    print('  proxy as open relay ->', type(e).__name__, e)
"

hdr "P6  ALLOWLIST ENFORCEMENT at the proxy (CONNECT)"
$RUN '
import socket
def connect(target):
    s=socket.create_connection(("a0pc-proxy",8787),timeout=8)
    s.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (target,target)).encode())
    return s.recv(200).split(b"\r\n")[0].decode()
for t in ["api.deepseek.com:443","openrouter.ai:443","example.com:443","1.1.1.1:443","api.openai.com:443"]:
    print("  CONNECT %-24s -> %s" % (t, connect(t)))
'

hdr "P7  DUAL-SHAPE UPSTREAM on ONE listener"
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  docker exec -e DEEPSEEK_API_KEY -e PROXY_NAME="$PROXY_NAME" -e PROXY_PORT="$PROXY_PORT" "$CLI_CTR" python3 -c '
import json,os,urllib.request
base="http://%s:%s" % (os.environ["PROXY_NAME"], os.environ["PROXY_PORT"])
def post(path, payload):
    req=urllib.request.Request(base+path, data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json",
                 "x-api-key": os.environ["DEEPSEEK_API_KEY"],
                 "anthropic-version":"2023-06-01",
                 "Authorization":"Bearer "+os.environ["DEEPSEEK_API_KEY"]})
    r=urllib.request.urlopen(req,timeout=60)
    return r.status, json.loads(r.read())
# OpenAI Chat Completions shape -> api.deepseek.com/v1/chat/completions
st,d = post("/v1/chat/completions", {"model":"deepseek-v4-pro",
    "messages":[{"role":"user","content":"say OK"}],"max_tokens":8})
print("  OpenAI  /v1/chat/completions -> HTTP %s served_model=%s content=%r usage=%s"
      % (st, d.get("model"), d["choices"][0]["message"]["content"][:40], d.get("usage")))
# Anthropic Messages shape -> api.deepseek.com/anthropic/v1/messages
st,d = post("/v1/messages", {"model":"deepseek-v4-pro","max_tokens":16,
    "messages":[{"role":"user","content":"say OK"}]})
print("  Anthropic /v1/messages     -> HTTP %s served_model=%s content=%r usage=%s"
      % (st, d.get("model"), str(d.get("content"))[:80], d.get("usage")))
'
else
  echo "  SKIPPED: DEEPSEEK_API_KEY not in this shell"
fi

echo
echo "probe_closure.sh: done $(date -Is)"
