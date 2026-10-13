#!/bin/bash
# H1 treatment arm: identical to run_agent_arm.sh except for ONE addition -
# the Search-Before-Build prompt template (--ak prompt_template_path).
# Hypothesis H1: under the official open-network protocol, an explicit
# Search-Before-Build instruction improves real task performance.
# Usage: bash run_agent_arm_sbb.sh [job-name]
set -eu
JOB="${1:-agent-flash-1-sbb}"
~/.local/bin/harbor run -p /home/ebt/harbor-runs/build/task-restricted \
  -a qwen-coder -y --job-name "$JOB" -o /home/ebt/harbor-runs/jobs/agent \
  --extra-docker-compose /home/ebt/harbor-runs/config/dataset-build-overlay.yaml \
  --mounts '[{"type":"bind","source":"/home/ebt/harbor-runs/config/trial-settings.json","target":"/root/.qwen/settings.json","read_only":true}]' \
  -m deepseek-flash --ak version=0.25.1 \
  --ak prompt_template_path=/home/ebt/harbor-runs/config/search-before-build.prompt.j2 \
  --env-file /home/ebt/harbor-runs/config/agent.env \
  --agent-timeout-multiplier 0.25 \
  --ae NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
  --ae NVM_NODEJS_ORG_MIRROR=https://registry.npmmirror.com/-/binary/node \
  --ae NVM_SOURCE=https://cdn.jsdelivr.net/gh/nvm-sh/nvm@v0.40.2/nvm.sh \
  --ae NVM_INSTALL_VERSION=v0.40.2 \
  --ae QWEN_TELEMETRY_ENABLED=true \
  --ae QWEN_TELEMETRY_OUTFILE=/logs/agent/otel.json \
  --ae QWEN_TELEMETRY_LOG_PROMPTS=false \
  --ae QWEN_TELEMETRY_METRICS_INCLUDE_SESSION_ID=true
