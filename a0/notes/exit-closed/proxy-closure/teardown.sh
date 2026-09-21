#!/usr/bin/env bash
# teardown.sh -- remove everything setup.sh created. Touches nothing else.
# It never references, stops or removes adapdc-catalog-postgres-1 or any
# a0-egress-*/a0-loreley-* resource.
set -uo pipefail

NET_INTERNAL="${NET_INTERNAL:-a0pc-internal}"
PROXY_NAME="${PROXY_NAME:-a0pc-proxy}"

echo "== teardown: containers named a0pc-*"
for c in $(docker ps -aq --filter 'name=^a0pc-' 2>/dev/null); do
  docker rm -f "$c" >/dev/null 2>&1 && echo "   removed container $c"
done

echo "== teardown: networks named a0pc-*"
for n in $(docker network ls --format '{{.Name}}' | grep -E '^a0pc-'); do
  docker network rm "$n" >/dev/null 2>&1 && echo "   removed network $n"
done

echo "== teardown: verifying the pre-existing container is untouched"
docker ps --filter 'name=^adapdc-catalog-postgres-1$' --format '   {{.Names}} {{.Status}}'

echo "== teardown: remaining a0pc-* state (should be empty)"
docker ps -a --filter 'name=^a0pc-' --format '{{.Names}}' || true
docker network ls --format '{{.Name}}' | grep -E '^a0pc-' || echo "   (none)"
