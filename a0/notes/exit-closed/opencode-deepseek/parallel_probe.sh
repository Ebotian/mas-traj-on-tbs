#!/usr/bin/env bash
# Two concurrent opencode runs, each with a private EvE-style HOME/XDG tree
# (this is what EvE's driver does per rollout) and NO explicit service port.
# Both therefore inherit opencode's fixed default service port 49374.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY="$(awk -F: '/^deepseek:/{print $2; exit}' "$HOME/gptapi.md" | tr -d '[:space:]')"
ROOT="$HERE/logs/parallel"
rm -rf "$ROOT"; mkdir -p "$ROOT"

prepare() { # $1 = name
  local base="$ROOT/$1"
  mkdir -p "$base/.config/opencode" "$base/.local/state" "$base/.local/share" "$base/.cache"
  cat > "$base/.config/opencode/opencode.json" <<JSON
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    "deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "DeepSeek (direct)",
      "options": {
        "baseURL": "https://api.deepseek.com/v1",
        "apiKey": "{env:DEEPSEEK_API_KEY}"
      },
      "models": { "deepseek-v4-pro": { "name": "deepseek-v4-pro" } }
    }
  },
  "permission": { "shell": "ask", "edit": "ask", "webfetch": "deny" }
}
JSON
  mkdir -p "$ROOT/$1-work"; ( cd "$ROOT/$1-work" && git init -q . )
}

run_one() { # $1 = name
  local base="$ROOT/$1"
  ( cd "$ROOT/$1-work" && \
    HOME="$base" \
    XDG_CONFIG_HOME="$base/.config" \
    XDG_DATA_HOME="$base/.local/share" \
    XDG_STATE_HOME="$base/.local/state" \
    XDG_CACHE_HOME="$base/.cache" \
    DEEPSEEK_API_KEY="$KEY" \
    OPENCODE_DISABLE_AUTOUPDATE=true \
    timeout 180 opencode run --format json --auto --agent build \
      --model deepseek/deepseek-v4-pro "Reply with exactly: ok" \
      > "$ROOT/$1.json" 2> "$ROOT/$1.err" ; echo "EXIT_$1=$?" > "$ROOT/$1.exit" )
}

prepare a; prepare b
run_one a & run_one b &
wait
echo "--- exits ---"; cat "$ROOT"/*.exit
echo "--- stderr a ---"; head -5 "$ROOT/a.err"
echo "--- stderr b ---"; head -5 "$ROOT/b.err"
echo "--- text a ---"; jq -r 'select(.type=="text").part.text' "$ROOT/a.json" 2>/dev/null
echo "--- text b ---"; jq -r 'select(.type=="text").part.text' "$ROOT/b.json" 2>/dev/null
