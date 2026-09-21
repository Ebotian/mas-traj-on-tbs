# Sourced by probe scripts. Loads the DeepSeek key into the environment only.
# The key is never written to a file and never printed.
_kimi_key() {
  awk -F: -v n="$1" '$1==n{ sub(/^[^:]*:/, ""); print; exit }' "$HOME/gptapi.md"
}

export DEEPSEEK_API_KEY="$(_kimi_key deepseek)"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"

if [ -z "$DEEPSEEK_API_KEY" ]; then
  echo "FATAL: no deepseek key found" >&2
  exit 1
fi

# Scoped runtime state: nothing touches the user's global config.
export KILO_PROBE_ROOT="${KILO_PROBE_ROOT:-/tmp/kiloDS}"
export XDG_CONFIG_HOME="$KILO_PROBE_ROOT/config"
export XDG_DATA_HOME="$KILO_PROBE_ROOT/data"
export XDG_CACHE_HOME="$KILO_PROBE_ROOT/cache"
export XDG_STATE_HOME="$KILO_PROBE_ROOT/state"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"

# Loreley-shaped headless config, config mode (kilocode_cli.py:1119-1160).
# apiKey/baseURL are env-var *references*; the literal key exists only in the
# process environment of this invocation.
build_kilo_config_content() {
  python3 -c '
import json, sys
provider_id = sys.argv[1]
model = sys.argv[2]
permissions = {
    "interactive_terminal": "deny", "plan_enter": "deny", "plan_exit": "deny",
    "question": "deny", "suggest": "deny", "task": "deny",
}
disabled_tools = {"suggest": False, "task": False}
payload = {
    "$schema": "https://app.kilo.ai/config.json",
    "agent": {"loreley-headless": {
        "description": "Non-interactive Loreley worker agent",
        "mode": "primary",
        "permission": dict(permissions),
        "tools": dict(disabled_tools),
    }},
    "default_agent": "loreley-headless",
    "permission": permissions,
    "tools": disabled_tools,
    "provider": {provider_id: {
        "name": "Loreley OpenAI-compatible gateway",
        "npm": "@ai-sdk/openai-compatible",
        "options": {
            "apiKey": "{env:DEEPSEEK_API_KEY}",
            "baseURL": "{env:DEEPSEEK_BASE_URL}",
        },
        "models": {model: {"name": model}},
    }},
    "model": f"{provider_id}/{model}",
}
print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
' "$1" "$2"
}

export KILO_PROVIDER_ID="loreley-openai-compatible"
export KILO_MODEL_ID="${KILO_MODEL_ID:-deepseek-v4-pro}"
export KILO_CONFIG_CONTENT="$(build_kilo_config_content "$KILO_PROVIDER_ID" "$KILO_MODEL_ID")"
