#!/usr/bin/env bash
# =============================================================================
# infra/net.sh -- Loreley's service + isolation infrastructure for A0
#
# One Postgres (5432) and one Redis (6379) for the pinned Loreley checkout, on a
# docker network that doubles as the closure mechanism:
#
#   up        start postgres + redis, published on 127.0.0.1:5432 / :6379, on the
#             functional bridge network *and* attached to the internal network
#   close     detach the services from the functional bridge, leaving them only on
#             the --internal network: the candidate-execution channel then has no
#             route out
#   open      re-attach the functional bridge (host publishing comes back)
#   status    what is running and which networks each container is on
#   down      remove the containers (and, with --networks, the networks)
#
# Never touches 5433 / adapdc-catalog-postgres-1 (an unrelated pre-existing
# postgres:16 container).
#
# Caveat, measured, not assumed: docker's --internal removes the container's
# route to the host too, so host loopback is cut along with external egress. The
# orchestrator (this adapter) therefore cannot be placed behind the barrier; only
# the candidate-execution channel is.
# =============================================================================
set -uo pipefail

BRIDGE_NET="${BRIDGE_NET:-a0-loreley-net}"
INTERNAL_NET="${INTERNAL_NET:-a0-loreley-internal}"
POSTGRES="${POSTGRES:-a0-loreley-postgres}"
REDIS="${REDIS:-a0-loreley-redis}"
PG_IMAGE="${PG_IMAGE:-postgres:18}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:8}"
PG_USER="${PG_USER:-loreley}"
PG_PASSWORD="${PG_PASSWORD:-loreley}"
PG_DB="${PG_DB:-loreley}"

die() { echo "net.sh: ERROR: $*" >&2; exit 2; }
say() { echo "$*"; }

ensure_networks() {
  docker network inspect "$BRIDGE_NET" >/dev/null 2>&1 \
    || docker network create "$BRIDGE_NET" >/dev/null || die "cannot create $BRIDGE_NET"
  docker network inspect "$INTERNAL_NET" >/dev/null 2>&1 \
    || docker network create --internal "$INTERNAL_NET" >/dev/null \
    || die "cannot create $INTERNAL_NET"
}

cmd_up() {
  ensure_networks
  if ! docker container inspect "$POSTGRES" >/dev/null 2>&1; then
    docker run -d --name "$POSTGRES" --network "$BRIDGE_NET" \
      -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_DB" \
      -p 127.0.0.1:5432:5432 "$PG_IMAGE" >/dev/null || die "cannot start postgres"
  else
    docker start "$POSTGRES" >/dev/null
  fi
  if ! docker container inspect "$REDIS" >/dev/null 2>&1; then
    docker run -d --name "$REDIS" --network "$BRIDGE_NET" \
      -p 127.0.0.1:6379:6379 "$REDIS_IMAGE" redis-server --appendonly yes >/dev/null \
      || die "cannot start redis"
  else
    docker start "$REDIS" >/dev/null
  fi
  docker network connect "$INTERNAL_NET" "$POSTGRES" 2>/dev/null || true
  docker network connect "$INTERNAL_NET" "$REDIS" 2>/dev/null || true
  sleep 4
  docker exec "$POSTGRES" pg_isready -U "$PG_USER" -d "$PG_DB" || true
  docker exec "$REDIS" redis-cli ping || true
  cmd_status
}

cmd_close() {
  # The services stay reachable from inside the internal network; the runtime's
  # candidate-execution channel is what must be placed there.
  docker network disconnect "$BRIDGE_NET" "$POSTGRES" 2>/dev/null || true
  docker network disconnect "$BRIDGE_NET" "$REDIS" 2>/dev/null || true
  say "closed: $POSTGRES and $REDIS are only on $INTERNAL_NET (host publishing is gone)"
  cmd_status
}

cmd_open() {
  ensure_networks
  docker network connect "$BRIDGE_NET" "$POSTGRES" 2>/dev/null || true
  docker network connect "$BRIDGE_NET" "$REDIS" 2>/dev/null || true
  say "open: $POSTGRES and $REDIS are back on $BRIDGE_NET with host publishing"
  cmd_status
}

cmd_status() {
  docker ps -a --filter "name=^/${POSTGRES}$" --filter "name=^/${REDIS}$" \
    --format 'container {{.Names}}  {{.Status}}  {{.Ports}}'
  for name in "$POSTGRES" "$REDIS"; do
    if docker container inspect "$name" >/dev/null 2>&1; then
      nets=$(docker inspect "$name" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}')
      say "networks[$name] $nets"
    fi
  done
  say "untouched: adapdc-catalog-postgres-1 (5433)"
}

cmd_down() {
  docker rm -f "$POSTGRES" "$REDIS" >/dev/null 2>&1 || true
  if [ "${1:-}" = "--networks" ]; then
    docker network rm "$BRIDGE_NET" "$INTERNAL_NET" >/dev/null 2>&1 || true
  fi
  say "down: containers removed${1:+ (networks with --networks)}"
}

case "${1:-status}" in
  up)     cmd_up ;;
  close)  cmd_close ;;
  open)   cmd_open ;;
  status) cmd_status ;;
  down)   shift; cmd_down "${1:-}" ;;
  *)      die "usage: net.sh {up|close|open|status|down [--networks]}" ;;
esac
