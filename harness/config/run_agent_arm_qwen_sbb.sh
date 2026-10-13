#!/bin/bash
# Model-axis arm (B"): Token Plan qwen3.8-max + Search-Before-Build template on
# the restricted task copy - identical to run_agent_arm_qwen.sh except the ONE
# addition of --ak prompt_template_path. Effort pinned EXPLICITLY to the
# model's own default tier (xhigh) via trial-settings-qwen38max.json. See
# related_files/2026-10-10-model-axis-config-card.md.
# Usage: bash run_agent_arm_qwen_sbb.sh [job-name]
set -eu
JOB="${1:-agent-qwen38max-1-sbb-restricted}"
~/.local/bin/harbor run -p /home/ebt/harbor-runs/build/task-restricted \
  -a qwen-coder -y --job-name "$JOB" -o /home/ebt/harbor-runs/jobs/agent \
  --extra-docker-compose /home/ebt/harbor-runs/config/dataset-build-overlay.yaml \
  --mounts '[{"type":"bind","source":"/home/ebt/harbor-runs/config/trial-settings-qwen38max.json","target":"/root/.qwen/settings.json","read_only":true}]' \
  -m qwen3.8-max --ak version=0.25.1 \
  --ak prompt_template_path=/home/ebt/harbor-runs/config/search-before-build.prompt.j2 \
  --env-file /home/ebt/harbor-runs/config/agent-tokenplan.env \
  --agent-timeout-multiplier 0.25 \
  --ae NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
  --ae NVM_NODEJS_ORG_MIRROR=https://registry.npmmirror.com/-/binary/node \
  --ae NVM_SOURCE=https://cdn.jsdelivr.net/gh/nvm-sh/nvm@v0.40.2/nvm.sh \
  --ae NVM_INSTALL_VERSION=v0.40.2 \
  --ae QWEN_TELEMETRY_ENABLED=true \
  --ae QWEN_TELEMETRY_OUTFILE=/logs/agent/otel.json \
  --ae QWEN_TELEMETRY_LOG_PROMPTS=false \
  --ae QWEN_TELEMETRY_METRICS_INCLUDE_SESSION_ID=true
