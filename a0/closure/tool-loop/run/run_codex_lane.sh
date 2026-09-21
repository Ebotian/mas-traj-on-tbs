#!/usr/bin/env bash
# =============================================================================
# run_codex_lane.sh -- drive the codex lane AS AN AGENT inside the closed network.
#
# The container a0tl-cli has no uplink of its own: its only reachable network is
# a0tl-internal, whose sole dual-homed peer is the allowlist proxy a0tl-proxy.
#
#   A0TL_ROUTE=plaintext  base_url = http://a0tl-proxy:8787/v1   (needs the
#                         /v1/responses route: proxy/allowlist_proxy.responses.py)
#   A0TL_ROUTE=connect    base_url = https://api.deepseek.com/v1 with HTTPS_PROXY
#                         = http://a0tl-proxy:8787 -- the proxy then sees only
#                         CONNECT api.deepseek.com:443, which the UNMODIFIED
#                         allowlist already permits.
#
# A0TL_SANDBOX is passed straight to `codex exec --sandbox`. `danger-full-access`
# is the run that isolates the NETWORK barrier (the agent's own sandbox is not
# the thing under test); `workspace-write` is the posture SimpleLoop's shipped
# solver lane uses and is recorded separately.
#
# Credentials: DEEPSEEK_API_KEY must be exported by the caller; it is handed to
# the container with `docker exec -e DEEPSEEK_API_KEY` (no value form = docker
# copies it from the calling shell), so it never enters argv or any config file.
#
# Usage:
#   export DEEPSEEK_API_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
#   A0TL_TAG=codex-plaintext A0TL_ROUTE=plaintext run/run_codex_lane.sh
#   unset DEEPSEEK_API_KEY
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_CTR="${CLI_CTR:-a0tl-cli}"
PROXY="${A0TL_PROXY:-http://a0tl-proxy:8787}"
MODEL="${MODEL:-deepseek-flash}"
TAG="${A0TL_TAG:?set A0TL_TAG}"
ROUTE="${A0TL_ROUTE:-plaintext}"
SANDBOX="${A0TL_SANDBOX:-danger-full-access}"
PROMPT_FILE="${A0TL_PROMPT:-$HERE/prompts/codex_toolloop.md}"

[ -n "${DEEPSEEK_API_KEY:-}" ] || { echo "ERROR: export DEEPSEEK_API_KEY first" >&2; exit 2; }
[ -f "$PROMPT_FILE" ] || { echo "ERROR: no prompt file $PROMPT_FILE" >&2; exit 2; }

case "$ROUTE" in
  plaintext) BASE_URL="$PROXY/v1";                   PROXY_ENV=() ;;
  connect)   BASE_URL="https://api.deepseek.com/v1"; PROXY_ENV=(-e HTTPS_PROXY="$PROXY" -e https_proxy="$PROXY") ;;
  *) echo "ERROR: A0TL_ROUTE must be plaintext|connect" >&2; exit 2 ;;
esac

RUN_DIR="/work/runs/$TAG"
mkdir -p "$HERE/evidence"
PROMPT_HOST="$HERE/evidence/${TAG}.prompt.md"
sed "s|__TAG__|$TAG|g" "$PROMPT_FILE" > "$PROMPT_HOST"
PROMPT="$(cat "$PROMPT_HOST")"

docker exec "$CLI_CTR" sh -c "rm -rf '$RUN_DIR' && mkdir -p '$RUN_DIR/home' '$RUN_DIR/wd'"
docker cp "$PROMPT_HOST" "$CLI_CTR:$RUN_DIR/prompt.md" >/dev/null

echo "== codex lane: tag=$TAG route=$ROUTE sandbox=$SANDBOX base_url=$BASE_URL"
date "+== started %Y-%m-%dT%H:%M:%S%z"
docker exec \
  -e DEEPSEEK_API_KEY \
  -e CODEX_HOME="$RUN_DIR/home" \
  -e HOME=/work/home \
  "${PROXY_ENV[@]}" \
  -w "$RUN_DIR/wd" \
  "$CLI_CTR" codex exec --skip-git-repo-check --sandbox "$SANDBOX" \
    -c model="$MODEL" \
    -c model_provider="ds" \
    -c model_providers.ds.name="DeepSeek" \
    -c model_providers.ds.base_url="$BASE_URL" \
    -c model_providers.ds.env_key="DEEPSEEK_API_KEY" \
    -c model_providers.ds.wire_api="responses" \
    "$PROMPT" 2>&1 | tee "$HERE/evidence/${TAG}.codex.stdout.txt"
rc=${PIPESTATUS[0]}
date "+== finished %Y-%m-%dT%H:%M:%S%z"
echo "== codex exec exit code: $rc (124 = the outer timeout fired)"
echo "== artefacts inside the container under $RUN_DIR:"
docker exec "$CLI_CTR" find "$RUN_DIR" -type f -printf '   %s\t%p\n' 2>/dev/null | sort -k2
exit "$rc"
