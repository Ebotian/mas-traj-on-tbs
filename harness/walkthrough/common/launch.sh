#!/bin/bash
# common/launch.sh — task-INDEPENDENT harbor launcher for the dual-agent runs.
# Everything experiments share lives here: task dir, mount, env-file, npm/node
# mirrors, PYTHONPATH for the agent module, artifact collection, --no-delete, and the
# cleanup policy (2026-10-11 ruling): a run whose collected state.json carries
# "normal": true has its two Docker images removed
# (task-restricted__<suffix>__env-main + __verifier__trial-main); anything else
# keeps them for forensics.
#
# Usage: launch.sh <job-name> <agent-spec> <timeout-multiplier>
#   agent-spec: "module:Class" (task launchers pass "agent:<Class>"; the module
#   lives in the task dir named by WT_AGENT_DIR, resolved via PYTHONPATH)
# Env:  WT_AGENT_DIR — task dir holding the agent module (set by task launcher)
#       EXTRA_AE="K=V K=V" — extra --ae pairs for the container (e.g. WT_PROMPT)
set -eu
JOB="${1:?usage: launch.sh <job-name> <agent-spec> <timeout-multiplier>}"
AGENT_SPEC="${2:?agent spec module:Class (e.g. agent:WalkthroughAgent)}"
MULT="${3:?timeout multiplier for harbor --agent-timeout-multiplier}"
: "${WT_AGENT_DIR:?WT_AGENT_DIR missing — call via tasks/<task>/launch.sh}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # harbor-runs root; this file lives at <root>/walkthrough/common/
export PYTHONPATH="$ROOT/walkthrough/common:$WT_AGENT_DIR${PYTHONPATH:+:$PYTHONPATH}"
AE_ARGS=()
for kv in ${EXTRA_AE:-}; do AE_ARGS+=(--ae "$kv"); done
set +e
~/.local/bin/harbor run -p "$ROOT/build/task-restricted" \
  -a "$AGENT_SPEC" -y --job-name "$JOB" -o "$ROOT/jobs/agent" \
  --mounts "[{\"type\":\"bind\",\"source\":\"$ROOT/walkthrough\",\"target\":\"/root/wt-src\",\"read_only\":true}]" \
  -m deepseek-flash --ak version=0.25.1 \
  --env-file "$ROOT/walkthrough/walkthrough.env" \
  --agent-timeout-multiplier "$MULT" \
  --artifact /root/wt/collect \
  --no-delete \
  --ae NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
  --ae NVM_NODEJS_ORG_MIRROR=https://registry.npmmirror.com/-/binary/node \
  --ae NVM_SOURCE=https://cdn.jsdelivr.net/gh/nvm-sh/nvm@v0.40.2/nvm.sh \
  --ae NVM_INSTALL_VERSION=v0.40.2 \
  "${AE_ARGS[@]}"
RC=$?
set -e
# Cleanup policy: normal verdict -> remove this run's images; else keep them.
JOBDIR="$ROOT/jobs/agent/$JOB"
TRIAL=$(find "$JOBDIR" -maxdepth 2 -type d -name 'task-restricted__*' 2>/dev/null | head -1 || true)
VERDICT=$(python3 - "${TRIAL:-/nonexistent}" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]) / "artifacts/root/wt/collect/state.json"
try:
    s = json.loads(p.read_text())
    print("normal" if s.get("normal") else "abnormal")
except Exception:
    print("missing")
PY
)
if [ "$VERDICT" = normal ] && [ -n "${TRIAL:-}" ]; then
  SUF=$(basename "$TRIAL"); SUF=$(printf '%s' "${SUF#task-restricted__}" | tr 'A-Z' 'a-z')
  if docker image inspect "task-restricted__${SUF}__env-main" >/dev/null 2>&1 \
  || docker image inspect "task-restricted__${SUF}__verifier__trial-main" >/dev/null 2>&1; then
    docker image rm "task-restricted__${SUF}__env-main" \
                    "task-restricted__${SUF}__verifier__trial-main" >/dev/null 2>&1 || true
    echo "cleanup[$JOB]: run NORMAL - removed images task-restricted__${SUF}__{env-main,verifier__trial-main}"
  else
    echo "cleanup[$JOB]: run NORMAL - no images found for suffix ${SUF}"
  fi
else
  echo "cleanup[$JOB]: images kept (verdict=$VERDICT, harbor rc=$RC)"
fi
exit "$RC"
