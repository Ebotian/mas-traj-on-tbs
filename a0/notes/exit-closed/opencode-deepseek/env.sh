# Source this to run opencode fully scoped to this directory.
# The DeepSeek key is read from ~/gptapi.md at run time and lives only in the
# environment of the current shell -- it is never written to any file.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DEEPSEEK_API_KEY="$(awk -F: '/^deepseek:/{print $2; exit}' "$HOME/gptapi.md" | tr -d '[:space:]')"
export XDG_CONFIG_HOME="$HERE/xdg/config"
export XDG_DATA_HOME="$HERE/xdg/data"
export XDG_CACHE_HOME="$HERE/xdg/cache"
export XDG_STATE_HOME="$HERE/xdg/state"
export OPENCODE_DISABLE_AUTOUPDATE=true
