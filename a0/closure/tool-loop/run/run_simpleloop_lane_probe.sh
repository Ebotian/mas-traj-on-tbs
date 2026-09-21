#!/usr/bin/env bash
# =============================================================================
# run_simpleloop_lane_probe.sh -- the SimpleLoop SOLVER LANE as a real tool loop
# inside the closed network.
#
# It runs the substrate's own shipped argv (built by CliSolver._command, not
# retyped) with a closure-probe prompt, so the four attempts land inside the
# tool loop of the lane SimpleLoop actually ships. `workspace-write` is that
# lane's posture -- recorded as-is, not overridden, because the posture is part
# of what is being measured.
#
# Usage:
#   export DEEPSEEK_API_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
#   A0TL_TAG=sl-lane-workspace-write run/run_simpleloop_lane_probe.sh
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_CTR="${CLI_CTR:-a0tl-cli}"
PROXY="${A0TL_PROXY:-http://a0tl-proxy:8787}"
MODEL="${MODEL:-deepseek-flash}"
TAG="${A0TL_TAG:?set A0TL_TAG}"
PROMPT_FILE="${A0TL_PROMPT:-$HERE/prompts/simpleloop_lane_toolloop.md}"

[ -n "${DEEPSEEK_API_KEY:-}" ] || { echo "ERROR: export DEEPSEEK_API_KEY first" >&2; exit 2; }

RUN_DIR="/work/runs/$TAG"
mkdir -p "$HERE/evidence"
sed "s|__TAG__|$TAG|g" "$PROMPT_FILE" > "$HERE/evidence/${TAG}.prompt.md"

docker exec "$CLI_CTR" sh -c "rm -rf '$RUN_DIR' && mkdir -p '$RUN_DIR/codex-home' '$RUN_DIR/wd'"
docker cp "$HERE/evidence/${TAG}.prompt.md" "$CLI_CTR:$RUN_DIR/prompt.md" >/dev/null
# The lane takes its endpoint from the ambient environment, exactly as it does in
# a deployment: CODEX_HOME here, no credential in the file (env_key names a var).
docker exec "$CLI_CTR" sh -c "cat > '$RUN_DIR/codex-home/config.toml' <<EOF
model = \"$MODEL\"
model_provider = \"ds\"

[model_providers.ds]
name = \"DeepSeek\"
base_url = \"$PROXY/v1\"
env_key = \"DEEPSEEK_API_KEY\"
wire_api = \"responses\"
EOF"

echo "== SimpleLoop solver lane: tag=$TAG (shipped argv, workspace-write)"
date "+== started %Y-%m-%dT%H:%M:%S%z"
docker exec -e DEEPSEEK_API_KEY -e CODEX_HOME="$RUN_DIR/codex-home" -e HOME=/work/home \
  "$CLI_CTR" python3 /opt/a0tl/run/simpleloop_lane_probe.py \
    --tag "$TAG" --prompt "$RUN_DIR/prompt.md" --timeout 420 \
  2>&1 | tee "$HERE/evidence/${TAG}.lane.console.txt"
rc=${PIPESTATUS[0]}
date "+== finished %Y-%m-%dT%H:%M:%S%z"
echo "== lane exit code: $rc"
exit "$rc"
