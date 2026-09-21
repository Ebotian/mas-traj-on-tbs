#!/usr/bin/env bash
# =============================================================================
# setup.sh -- rootless closure topology for a REMOTE model (DeepSeek).
#
# Shape (all names are a0pc-* so nothing collides with the pre-existing
# adapdc-* containers or the a0-egress-*/a0-loreley-* networks):
#
#   a0pc-internal   docker network, --internal  (no default route, no NAT)
#      |
#      +-- a0pc-proxy   the ONLY dual-homed container: also on the default
#      |                `bridge`, so it -- and only it -- has uplink.
#      |                Runs proxy/allowlist_proxy.py, a stdlib-only listener
#      |                that permits api.deepseek.com (and optionally
#      |                openrouter.ai) and refuses everything else.
#      |
#      +-- clients / candidate code: e.g.
#             docker run --rm --network a0pc-internal ... python:3.12-slim
#          Their only reachable peer that has any uplink is a0pc-proxy.
#
# The model stays remote, so unlike the retired `unshare -rn` plan this
# namespace DOES have an uplink -- it just terminates on the proxy.
#
# Idempotent: re-running rebuilds the proxy and leaves the network in place.
# Tear down with ./teardown.sh
#
# No API key is read, written or needed by this script: the proxy is a
# pass-through, so credentials only ever exist in the calling shell's
# environment for the duration of one `docker exec`.
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NET_INTERNAL="${NET_INTERNAL:-a0pc-internal}"
SUBNET="${SUBNET:-172.31.77.0/24}"
PROXY_IP="${PROXY_IP:-172.31.77.10}"
PROXY_NAME="${PROXY_NAME:-a0pc-proxy}"
PROXY_PORT="${PROXY_PORT:-8787}"
PROXY_IMAGE="${PROXY_IMAGE:-python:3.12-slim}"
EGRESS_NET="${EGRESS_NET:-bridge}"
ALLOW_CONNECT="${ALLOW_CONNECT:-api.deepseek.com,openrouter.ai}"
CLI_CTR="${CLI_CTR:-a0pc-cli}"

echo "== setup: internal network $NET_INTERNAL ($SUBNET, internal=true)"
if docker network inspect "$NET_INTERNAL" >/dev/null 2>&1; then
  echo "   exists; reusing"
else
  docker network create --internal --subnet "$SUBNET" "$NET_INTERNAL" >/dev/null
  echo "   created"
fi

echo "== setup: (re)starting proxy container $PROXY_NAME"
docker rm -f "$PROXY_NAME" >/dev/null 2>&1 || true
# Step 1: start on the egress network only. Docker will not let a container be
# created on an --internal network in the same `run` and still get uplink.
docker run -d --name "$PROXY_NAME" \
  --network "$EGRESS_NET" \
  --restart no \
  -e PROXY_PORT="$PROXY_PORT" \
  -e PROXY_ALLOW="$ALLOW_CONNECT" \
  -v "$HERE/proxy/allowlist_proxy.py:/opt/a0pc/allowlist_proxy.py:ro" \
  --entrypoint python3 \
  "$PROXY_IMAGE" /opt/a0pc/allowlist_proxy.py >/dev/null

# Step 2: attach the SAME container to the internal network at a stable IP.
docker network connect --ip "$PROXY_IP" "$NET_INTERNAL" "$PROXY_NAME"

if [ "${WITH_CLI_CTR:-1}" = 1 ]; then
  echo "== setup: (re)starting the client container $CLI_CTR (internal side only)"
  docker rm -f "$CLI_CTR" >/dev/null 2>&1 || true
  # The three CLIs are bind-mounted read-only from the host; the image already
  # present locally (python:3.12-slim, glibc 2.41) is enough to run them -- no
  # package install and no image pull.
  docker run -d --name "$CLI_CTR" --network "$NET_INTERNAL" \
    -v /opt/claude-code:/opt/claude-code:ro \
    -v /usr/lib/kilo:/usr/lib/kilo:ro \
    -v /usr/bin/opencode:/usr/local/bin/opencode:ro \
    -e HOME=/work -e XDG_DATA_HOME=/work/.local/share -e XDG_CACHE_HOME=/work/.cache \
    -e KILO_TREE_SITTER_WASM_DIR=/usr/lib/kilo/tree-sitter \
    --entrypoint sleep "$PROXY_IMAGE" infinity >/dev/null
  docker exec "$CLI_CTR" sh -c 'mkdir -p /work/wd /work/.config/opencode'
fi

if [ "${WITH_SERVICES:-0}" = 1 ]; then
  echo "== setup: (re)starting Loreley-shaped services on $NET_INTERNAL (internal-only)"
  docker rm -f a0pc-pg a0pc-redis >/dev/null 2>&1 || true
  docker run -d --name a0pc-pg --network "$NET_INTERNAL" \
    -e POSTGRES_PASSWORD=a0pc -e POSTGRES_DB=a0pc postgres:16 >/dev/null
  docker run -d --name a0pc-redis --network "$NET_INTERNAL" \
    redis:8 redis-server --save '' --appendonly no >/dev/null
fi

for _ in $(seq 1 40); do
  if docker logs "$PROXY_NAME" 2>&1 | grep -q 'event=start'; then break; fi
  sleep 0.25
done

echo "== setup: topology"
docker inspect "$PROXY_NAME" \
  --format '   {{.Name}} networks={{range $k,$v := .NetworkSettings.Networks}}{{$k}}({{$v.IPAddress}}) {{end}}'
docker network inspect "$NET_INTERNAL" \
  --format '   {{.Name}} internal={{.Internal}} subnet={{range .IPAM.Config}}{{.Subnet}}{{end}}'

echo
echo "Ready. Client containers (internal side, no uplink):"
echo "  docker run --rm -it --network $NET_INTERNAL $PROXY_IMAGE bash"
echo "Proxy listener inside that network: http://$PROXY_NAME:$PROXY_PORT  /  http://$PROXY_IP:$PROXY_PORT"
echo "Proxy log:  docker logs -f $PROXY_NAME"
echo "Teardown:   $HERE/teardown.sh"
