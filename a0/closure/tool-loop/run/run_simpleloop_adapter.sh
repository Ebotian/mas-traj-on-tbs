#!/usr/bin/env bash
# =============================================================================
# run_simpleloop_adapter.sh -- a FULL SimpleLoop run inside the closed network.
#
# This is the substrate, not a probe: `python -m a0_adapter run --solver codex`
# with the shipped policy, so c_0 = C* baseline, c_{t+1} = Agent(c_t, H_t) via the
# shipped CliSolver argv, every candidate scored by E* (which spawns the candidate
# in a child process of its own), then the frozen selection fold and the three
# traces validated by a0/contract/trace_validate.py.
#
# Only two things are supplied from outside the container: the repo (read-only,
# at its own path) and the solver's endpoint, which lives in CODEX_HOME and
# points at the allowlist proxy.
#
# Usage:
#   export DEEPSEEK_API_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
#   A0TL_TAG=sl-run-1 A0TL_MAX_ITERATIONS=2 run/run_simpleloop_adapter.sh
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_CTR="${CLI_CTR:-a0tl-cli}"
PROXY="${A0TL_PROXY:-http://a0tl-proxy:8787}"
MODEL="${MODEL:-deepseek-flash}"
TAG="${A0TL_TAG:?set A0TL_TAG}"
MAX_IT="${A0TL_MAX_ITERATIONS:-2}"
SOLVER_TIMEOUT="${A0TL_SOLVER_TIMEOUT:-420}"
RUN_DIR="/work/runs/$TAG"
ADAPTER_DIR=/home/ebt/rsi-dev/a0/runtimes/simpleloop

[ -n "${DEEPSEEK_API_KEY:-}" ] || { echo "ERROR: export DEEPSEEK_API_KEY first" >&2; exit 2; }

docker exec "$CLI_CTR" sh -c "rm -rf '$RUN_DIR' && mkdir -p '$RUN_DIR/codex-home' '$RUN_DIR/wd'"
docker exec "$CLI_CTR" sh -c "cat > '$RUN_DIR/codex-home/config.toml' <<EOF
model = \"$MODEL\"
model_provider = \"ds\"

[model_providers.ds]
name = \"DeepSeek\"
base_url = \"$PROXY/v1\"
env_key = \"DEEPSEEK_API_KEY\"
wire_api = \"responses\"
EOF"

echo "== SimpleLoop full run: tag=$TAG max_iterations=$MAX_IT solver=codex (shipped argv)"
date "+== started %Y-%m-%dT%H:%M:%S%z"
docker exec -e DEEPSEEK_API_KEY -e CODEX_HOME="$RUN_DIR/codex-home" -e HOME=/work/home \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -w "$ADAPTER_DIR" "$CLI_CTR" \
  python3 -m a0_adapter run \
    --solver codex --solver-timeout "$SOLVER_TIMEOUT" \
    --run-dir "$RUN_DIR/simpleloop-run" --run-id "$TAG" \
    --max-iterations "$MAX_IT" \
  2>&1 | tee "$HERE/evidence/${TAG}.adapter.console.txt"
rc=${PIPESTATUS[0]}
date "+== finished %Y-%m-%dT%H:%M:%S%z"
echo "== adapter exit code: $rc (0 ok, 8 solver_failed, 5 trace validation)"
exit "$rc"
