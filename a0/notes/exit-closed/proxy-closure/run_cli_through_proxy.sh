#!/usr/bin/env bash
# =============================================================================
# run_cli_through_proxy.sh -- the runnable answer to requirement 3.
#
# Runs the three agent CLIs INSIDE the internal network, once per routing
# strategy, and prints what each tool itself reports (served model, tokens,
# cost). Nothing leaves this box except the model calls.
#
#   claude   2.1.260  Anthropic Messages   -> proxy listener /v1/messages
#   opencode v2.0.11  OpenAI Chat Compl.   -> proxy listener /v1/chat/completions
#   kilo     7.7.5    OpenAI Chat Compl.   -> proxy listener /v1/chat/completions
#
# The proxy terminates both upstream shapes on ONE plaintext port, so a single
# allowlisted listener serves all three.
#
# Credentials: DEEPSEEK_API_KEY is read from the calling shell's environment and
# handed to containers with `docker exec -e DEEPSEEK_API_KEY` (no value form =
# docker copies it from the client env). It never enters argv, a config file, or
# a container's persisted config. Export it before running, unset it after.
#
# Usage:  DEEPSEEK_API_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
#         export DEEPSEEK_API_KEY; ./run_cli_through_proxy.sh; unset DEEPSEEK_API_KEY
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_CTR="${CLI_CTR:-a0pc-cli}"
PROXY_HOST="${PROXY_HOST:-a0pc-proxy}"
PROXY_PORT="${PROXY_PORT:-8787}"
PROXY="http://$PROXY_HOST:$PROXY_PORT"
MODEL="${MODEL:-deepseek-flash}"

[ -n "${DEEPSEEK_API_KEY:-}" ] || { echo "ERROR: export DEEPSEEK_API_KEY first" >&2; exit 2; }

# --- client-side config, written INSIDE the container ------------------------
# The key is referenced as {env:DEEPSEEK_API_KEY}, never stored.
docker exec "$CLI_CTR" sh -c "cat > /work/a0pc-opencode-direct.json <<EOF
{\"\$schema\":\"https://opencode.ai/config.json\",\"provider\":{\"a0pc\":{\"npm\":\"@ai-sdk/openai-compatible\",\"name\":\"a0pc-direct\",
 \"options\":{\"baseURL\":\"$PROXY/v1\",\"apiKey\":\"{env:DEEPSEEK_API_KEY}\"},
 \"models\":{\"$MODEL\":{\"name\":\"$MODEL\"}}}}}
EOF
cat > /work/a0pc-opencode-upstream.json <<EOF
{\"\$schema\":\"https://opencode.ai/config.json\",\"provider\":{\"a0pc\":{\"npm\":\"@ai-sdk/openai-compatible\",\"name\":\"a0pc-upstream\",
 \"options\":{\"baseURL\":\"https://api.deepseek.com/v1\",\"apiKey\":\"{env:DEEPSEEK_API_KEY}\"},
 \"models\":{\"$MODEL\":{\"name\":\"$MODEL\"}}}}}
EOF"
KILO_DIRECT="{\"provider\":{\"a0pc\":{\"npm\":\"@ai-sdk/openai-compatible\",\"name\":\"a0pc-direct\",\"options\":{\"baseURL\":\"$PROXY/v1\",\"apiKey\":\"{env:DEEPSEEK_API_KEY}\"},\"models\":{\"$MODEL\":{}}}}}"
KILO_UPSTREAM="{\"provider\":{\"a0pc\":{\"npm\":\"@ai-sdk/openai-compatible\",\"name\":\"a0pc-upstream\",\"options\":{\"baseURL\":\"https://api.deepseek.com/v1\",\"apiKey\":\"{env:DEEPSEEK_API_KEY}\"},\"models\":{\"$MODEL\":{}}}}}"
PROXY_ENV=(-e HTTPS_PROXY="$PROXY" -e https_proxy="$PROXY" -e HTTP_PROXY="$PROXY" -e NO_PROXY=localhost,127.0.0.1)
NOCHATTER=(-e DISABLE_TELEMETRY=1 -e DISABLE_ERROR_REPORTING=1 -e DISABLE_AUTOUPDATER=1 -e DISABLE_UPDATES=1
           -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 -e KILO_DISABLE_AUTOUPDATE=1)

banner() { echo; echo "----------------------------------------------------------------"; echo "## $*"; echo "----------------------------------------------------------------"; }

# ---------------------------------------------------------------- claude -----
# Claude Code appends /v1/messages to ANTHROPIC_BASE_URL, which the proxy maps
# to https://api.deepseek.com/anthropic/v1/messages.
banner "claude 2.1.260 -- route (a) plaintext base_url"
time docker exec -e DEEPSEEK_API_KEY -e ANTHROPIC_BASE_URL="$PROXY" \
  -e ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" -e ANTHROPIC_MODEL="$MODEL" "${NOCHATTER[@]}" \
  -w /work/wd "$CLI_CTR" /opt/claude-code/bin/claude -p "Reply with exactly: PROXY-OK" --output-format json 2>&1 | tail -3

banner "claude 2.1.260 -- route (b) HTTPS_PROXY, real https base_url"
time docker exec -e DEEPSEEK_API_KEY -e ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
  -e ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" -e ANTHROPIC_MODEL="$MODEL" \
  "${PROXY_ENV[@]}" "${NOCHATTER[@]}" \
  -w /work/wd "$CLI_CTR" /opt/claude-code/bin/claude -p "Reply with exactly: HTTPS-PROXY-OK" --output-format json 2>&1 | tail -3

# ------------------------------------------------------------- opencode -----
# NOTE: opencode v2 runs a BACKGROUND SERVICE by default; env vars passed to
# `docker exec` do not reach it and the provider call comes back 401. It must be
# run with --standalone so the server inherits this process's environment.
banner "opencode v2.0.11 -- route (a) plaintext baseURL (OPENCODE_CONFIG=<path>)"
time docker exec -e DEEPSEEK_API_KEY -e OPENCODE_CONFIG=/work/a0pc-opencode-direct.json \
  -w /work/wd "$CLI_CTR" /usr/local/bin/opencode run --standalone --model "a0pc/$MODEL" \
  --format json -- "Reply with exactly: PROXY-OK" 2>&1 | tail -2

banner "opencode v2.0.11 -- route (b) HTTPS_PROXY, real https baseURL"
time docker exec -e DEEPSEEK_API_KEY -e OPENCODE_CONFIG=/work/a0pc-opencode-upstream.json \
  "${PROXY_ENV[@]}" -w /work/wd "$CLI_CTR" /usr/local/bin/opencode run --standalone \
  --model "a0pc/$MODEL" --format json -- "Reply with exactly: HTTPS-PROXY-OK" 2>&1 | tail -2

# ----------------------------------------------------------------- kilo -----
banner "kilo 7.7.5 -- route (a) plaintext baseURL (KILO_CONFIG_CONTENT)"
time docker exec -e DEEPSEEK_API_KEY -e KILO_CONFIG_CONTENT="$KILO_DIRECT" "${NOCHATTER[@]}" \
  -w /work/wd "$CLI_CTR" /usr/lib/kilo/kilo run --format json --model "a0pc/$MODEL" \
  -- "Reply with exactly: KILO-PROXY-OK" 2>&1 | tail -2

banner "kilo 7.7.5 -- route (b) HTTPS_PROXY, real https baseURL"
time docker exec -e DEEPSEEK_API_KEY -e KILO_CONFIG_CONTENT="$KILO_UPSTREAM" \
  "${PROXY_ENV[@]}" "${NOCHATTER[@]}" \
  -w /work/wd "$CLI_CTR" /usr/lib/kilo/kilo run --format json --model "a0pc/$MODEL" \
  -- "Reply with exactly: KILO-HTTPS-PROXY-OK" 2>&1 | tail -2

# ------------------------------------------- allowlist negative control -----
banner "NEGATIVE CONTROL: claude left on its default provider, only HTTPS_PROXY set"
echo "(api.anthropic.com is not on the allowlist; expect a 403 from the proxy, not a model answer)"
time docker exec -e DEEPSEEK_API_KEY -e ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" \
  "${PROXY_ENV[@]}" "${NOCHATTER[@]}" \
  -w /work/wd "$CLI_CTR" /opt/claude-code/bin/claude -p "hi" --output-format json 2>&1 | tail -2

echo
echo "## proxy log tail (allow / deny decisions)"
docker logs "$PROXY_HOST" 2>&1 | tail -20
