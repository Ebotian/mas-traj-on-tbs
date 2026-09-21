#!/usr/bin/env bash
# window_proxy_log.sh -- slice the proxy's decision log to one run's window.
#
# The console log of a run carries "== started <local ts>" and
# "== finished <local ts>"; the proxy logs in UTC+0. This prints (and optionally
# stores) exactly the proxy lines inside that window, which is what makes the
# enforcement point's record for one run separable from its neighbours'.
#
#   ./run/window_proxy_log.sh codex-connect-unmod [snapshot-file]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_NAME="${PROXY_NAME:-a0tl-proxy}"
TAG="${1:?usage: window_proxy_log.sh <TAG> [proxy-log-snapshot]}"
SNAP="${2:-$HERE/evidence/runs/$TAG/proxy-log.at-collection.txt}"

CONSOLE=$(grep -l '^== started' "$HERE"/evidence/"$TAG"* 2>/dev/null | head -1)
[ -n "$CONSOLE" ] || { echo "no log with a '== started' stamp for $TAG" >&2; exit 2; }
if [ ! -f "$SNAP" ]; then
  mkdir -p "$HERE/evidence/runs/$TAG"
  docker logs "$PROXY_NAME" > "$SNAP" 2>&1
fi

FROM=$(sed -n 's/^== started \(.*\)$/date -d "\1" +%Y-%m-%dT%H:%M:%S%z/p' "$CONSOLE" | head -1 | sh)
TO=$(sed -n 's/^== finished \(.*\)$/date -d "\1" +%Y-%m-%dT%H:%M:%S%z/p' "$CONSOLE" | head -1 | sh)
FROM_UTC=$(date -u -d "$FROM" +%Y-%m-%dT%H:%M:%S)
TO_UTC=$(date -u -d "$TO" +%Y-%m-%dT%H:%M:%S)

echo "# run $TAG  window $FROM_UTC .. $TO_UTC (UTC)"
awk -v f="$FROM_UTC" -v t="$TO_UTC" '{ts=substr($1,1,19)} ts>=f && ts<=t' "$SNAP"
