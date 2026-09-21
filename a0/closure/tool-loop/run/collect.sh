#!/usr/bin/env bash
# collect.sh -- copy a run's artefacts out of the worker container and record the
# proxy's decision log for that window. Usage: ./run/collect.sh <TAG> [...]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_CTR="${CLI_CTR:-a0tl-cli}"
PROXY_NAME="${PROXY_NAME:-a0tl-proxy}"

for TAG in "$@"; do
  dest="$HERE/evidence/runs/$TAG"
  mkdir -p "$dest"
  docker cp "$CLI_CTR:/work/runs/$TAG/." "$dest/in-container/" >/dev/null 2>&1 \
    && echo "collected container artefacts -> evidence/runs/$TAG/in-container/"
  docker logs "$PROXY_NAME" > "$dest/proxy-log.at-collection.txt" 2>&1
  echo "  proxy decision log      -> evidence/runs/$TAG/proxy-log.at-collection.txt"
done
