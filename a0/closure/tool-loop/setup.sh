#!/usr/bin/env bash
# =============================================================================
# setup.sh -- the tool-loop closure topology for THIS workstream.
#
# Owns a0/closure/tool-loop/**. Read-only uses of a0/notes/exit-closed/
# proxy-closure/** (its proxies are copied here, never edited).
#
# Shape (all names are a0tl-* so nothing collides with the a0pc-* topology):
#
#   a0tl-internal  docker network --internal, 172.31.78.0/24, no default route
#      |
#      +-- a0tl-proxy   the ONLY dual-homed container (also on `bridge`).
#      |                Runs proxy/$PROXY_SCRIPT, the allowlist listener copied
#      |                from the proxy-closure workstream.
#      |
#      +-- a0tl-cli     the WORKER: codex 0.155.1 + the repo + the pinned
#                       interpreters, on the internal network only.
#
# PROXY_SCRIPT selects the proxy build, so the same topology runs the
# unmodified allowlist and this workstream's variant:
#
#   PROXY_SCRIPT=allowlist_proxy.py            (byte-identical to theirs)
#   PROXY_SCRIPT=allowlist_proxy.responses.py  (default; adds /v1/responses)
#
# Idempotent: re-running rebuilds the proxy and the worker. Tear down with
# ./teardown.sh. No key is read, written or needed here.
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NET_INTERNAL="${NET_INTERNAL:-a0tl-internal}"
SUBNET="${SUBNET:-172.31.78.0/24}"
PROXY_IP="${PROXY_IP:-172.31.78.10}"
PROXY_NAME="${PROXY_NAME:-a0tl-proxy}"
PROXY_PORT="${PROXY_PORT:-8787}"
PROXY_IMAGE="${PROXY_IMAGE:-python:3.12-slim}"
EGRESS_NET="${EGRESS_NET:-bridge}"
ALLOW_CONNECT="${ALLOW_CONNECT:-api.deepseek.com,openrouter.ai}"
PROXY_SCRIPT="${PROXY_SCRIPT:-allowlist_proxy.responses.py}"
CLI_CTR="${CLI_CTR:-a0tl-cli}"
WORK_ROOT="${WORK_ROOT:-/home/ebt/rsi-dev}"

echo "== setup: internal network $NET_INTERNAL ($SUBNET, internal=true)"
if docker network inspect "$NET_INTERNAL" >/dev/null 2>&1; then
  echo "   exists; reusing"
else
  docker network create --internal --subnet "$SUBNET" "$NET_INTERNAL" >/dev/null
  echo "   created"
fi

echo "== setup: (re)starting proxy $PROXY_NAME with $PROXY_SCRIPT"
docker rm -f "$PROXY_NAME" >/dev/null 2>&1 || true
docker run -d --name "$PROXY_NAME" \
  --network "$EGRESS_NET" \
  --restart no \
  -e PROXY_PORT="$PROXY_PORT" \
  -e PROXY_ALLOW="$ALLOW_CONNECT" \
  -v "$HERE/proxy:/opt/a0tl:ro" \
  --entrypoint python3 \
  "$PROXY_IMAGE" "/opt/a0tl/$PROXY_SCRIPT" >/dev/null
docker network connect --ip "$PROXY_IP" "$NET_INTERNAL" "$PROXY_NAME"

echo "== setup: (re)starting the worker container $CLI_CTR (internal side only)"
docker rm -f "$CLI_CTR" >/dev/null 2>&1 || true
# codex is bind-mounted from the host, exactly as the a0pc-* topology mounts the
# other CLIs. The image is Debian trixie (glibc 2.41); the only shared libraries
# codex needs that the image lacks are libonig and (for its own sandbox) libcap,
# so those two files are mounted too.
#
# bwrap is mounted because codex's `--sandbox workspace-write` -- the posture
# SimpleLoop's shipped solver lane uses -- launches the shell tool inside
# bubblewrap and *panics* without it: "bubblewrap is unavailable: no system bwrap
# was found on PATH". A closed deployment of that lane needs bwrap present; with
# it absent the lane cannot execute a tool at all, which is a different finding
# from "the network is closed" and is recorded separately.
#
# The repo is mounted READ-ONLY at its own path: the adapter's --work-root
# defaults and the pinned .venv symlinks then resolve unchanged, and nothing the
# container does can write into the repository.
#
# CAP_SYS_ADMIN + seccomp=unconfined are here ONLY so that bubblewrap can create
# the namespaces codex's sandbox needs (measured: without them,
# "bwrap: Creating new namespace failed: Operation not permitted"; with
# seccomp=unconfined alone, the same). --privileged is added because those two
# are still not enough for the sandbox's procfs mount inside a container:
# measured on this host/kernel,
#   bwrap --unshare-user --unshare-pid ... --proc /proc  -> Operation not permitted
# with --cap-add=SYS_ADMIN + seccomp=unconfined, and the same command succeeds
# under --privileged. This is a deviation from the a0pc-* defaults and is listed
# in the report's residuals.
#
# It is a *privilege* relaxation, not a network one, and that is measured rather
# than asserted: the in-lane probe (evidence/inlane_privileged_probe.json) was
# run in this container with --privileged in force and still recorded
# ENETUNREACH for every address and a proxy DENY for every non-allowlisted host.
docker run -d --name "$CLI_CTR" --network "$NET_INTERNAL" \
  --privileged \
  -v /usr/bin/codex:/usr/local/bin/codex:ro \
  -v /usr/bin/bwrap:/usr/bin/bwrap:ro \
  -v /usr/lib/libonig.so.5:/opt/hostlibs/libonig.so.5:ro \
  -v /usr/lib/libcap.so.2:/opt/hostlibs/libcap.so.2:ro \
  -v "$WORK_ROOT":"$WORK_ROOT":ro \
  -v /home/ebt/.local/share/uv/python:/home/ebt/.local/share/uv/python:ro \
  -v "$HERE:/opt/a0tl:ro" \
  -e LD_LIBRARY_PATH=/opt/hostlibs \
  -e HOME=/work/home \
  -e UV_PYTHON_DOWNLOADS=never \
  --entrypoint sleep "$PROXY_IMAGE" infinity >/dev/null
docker exec "$CLI_CTR" sh -c 'mkdir -p /work/home /work/run /work/wd'

for _ in $(seq 1 40); do
  if docker logs "$PROXY_NAME" 2>&1 | grep -q 'event=start'; then break; fi
  sleep 0.25
done

echo "== setup: topology"
docker inspect "$PROXY_NAME" \
  --format '   {{.Name}} networks={{range $k,$v := .NetworkSettings.Networks}}{{$k}}({{$v.IPAddress}}) {{end}}'
docker inspect "$CLI_CTR" \
  --format '   {{.Name}} networks={{range $k,$v := .NetworkSettings.Networks}}{{$k}}({{$v.IPAddress}}) {{end}}'
docker network inspect "$NET_INTERNAL" \
  --format '   {{.Name}} internal={{.Internal}} subnet={{range .IPAM.Config}}{{.Subnet}}{{end}}'

echo
echo "Worker inside the network (no uplink of its own):"
echo "  docker exec -it $CLI_CTR bash"
echo "Proxy listener: http://$PROXY_NAME:$PROXY_PORT  /  http://$PROXY_IP:$PROXY_PORT"
echo "Proxy log:  docker logs -f $PROXY_NAME"
echo "Teardown:   $HERE/teardown.sh"
