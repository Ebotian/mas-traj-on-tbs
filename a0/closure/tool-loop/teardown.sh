#!/usr/bin/env bash
# teardown.sh -- remove everything setup.sh created. Touches nothing else.
# It never references the a0pc-* topology, the a0-egress-*/a0-loreley-*
# networks, or adapdc-catalog-postgres-1.
set -uo pipefail

NET_INTERNAL="${NET_INTERNAL:-a0tl-internal}"

echo "== teardown: containers named a0tl-*"
for c in $(docker ps -aq --filter 'name=^a0tl-' 2>/dev/null); do
  docker rm -f "$c" >/dev/null 2>&1 && echo "   removed container $c"
done

echo "== teardown: networks named a0tl-*"
for n in $(docker network ls --format '{{.Name}}' | grep -E '^a0tl-'); do
  docker network rm "$n" >/dev/null 2>&1 && echo "   removed network $n"
done

echo "== teardown: untouched neighbours (must still be listed)"
docker ps --filter 'name=^a0pc-' --format '   a0pc: {{.Names}} {{.Status}}'
docker ps --filter 'name=^adapdc-catalog-postgres-1$' --format '   {{.Names}} {{.Status}}'

echo "== teardown: remaining a0tl-* state (should be empty)"
docker ps -a --filter 'name=^a0tl-' --format '{{.Names}}' || true
docker network ls --format '{{.Name}}' | grep -E '^a0tl-' || echo "   (none)"
