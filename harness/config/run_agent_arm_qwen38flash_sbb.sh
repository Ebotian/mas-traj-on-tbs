#!/bin/bash
# Model-axis arm (qwen3.8-flash): Token Plan qwen3.8-flash + Search-Before-Build
# template (canonical v2) on the restricted task copy, under the GATEWAY-live
# condition. Effort is pinned EXPLICITLY to xhigh = this model's top tier and
# default; a literal "max" is rank-clamped to xhigh by qwen-code 0.25.1
# (reasoning-effort.ts clampReasoningEffort: nothing at/above 'max' -> strongest
# available), so xhigh is the effective max, written out for the record.
# See related_files/2026-10-10-model-axis-config-card.md + spec §6.6.
# Usage: bash run_agent_arm_qwen38flash_sbb.sh [job-name]
set -eu
JOB="${1:-agent-qwen38flash-1-sbb-gateway}"
~/.local/bin/harbor run -p /home/ebt/harbor-runs/build/task-restricted \
  -a qwen-coder -y --job-name "$JOB" -o /home/ebt/harbor-runs/jobs/agent \
  --extra-docker-compose /home/ebt/harbor-runs/config/dataset-build-overlay.yaml \
  --mounts '[{"type":"bind","source":"/home/ebt/harbor-runs/config/trial-settings-qwen38flash.json","target":"/root/.qwen/settings.json","read_only":true}]' \
  -m qwen3.8-flash --ak version=0.25.1 \
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
