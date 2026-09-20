#!/usr/bin/env bash
# Dependency-resolution matrix for the A0 environment audit.
# Read-only wrt the upstream projects: writes only under a0/env/checks/.
set -u
CHECKS=/home/ebt/rsi-dev/a0/env/checks
export UV_CACHE_DIR="$CHECKS/.uvcache"
export PYTHONDONTWRITEBYTECODE=1
KAPSO=/home/ebt/kapso_ck/kapso
EVE=/tmp/eve
LOG="$CHECKS/logs/dep_matrix.log"
mkdir -p "$CHECKS/logs" "$CHECKS/kapso" "$CHECKS/eve"
: > "$LOG"

run() { # run <label> <cmd...>
  local label="$1"; shift
  { echo; echo "==================================================================="
    echo "### CASE: $label"
    echo "### DATE: $(date -Is)"
    echo "### CMD : $*"
    echo "--- output ---"
    "$@" 2>&1
    local rc=$?
    echo "--- RC=$rc ---"
  } | tee -a "$LOG"
  return 0
}

echo "### note: http_proxy/https_proxy are UNSET for this whole matrix (host direct egress used)" | tee -a "$LOG"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

# ---- helper: extract KAPSO core deps from pyproject (no optional extras) ----
python3 - "$KAPSO/pyproject.toml" > "$CHECKS/kapso/core-reqs.txt" <<'PY'
import sys, tomllib
d = tomllib.load(open(sys.argv[1],'rb'))
for dep in d['project']['dependencies']:
    print(dep)
PY
run "kapso: extracted core deps from pyproject.toml" cat "$CHECKS/kapso/core-reqs.txt"

# ---- venvs ----
for v in 3.11 3.12; do
  t=${v/./}
  run "uv venv kapso/venv$t (python $v)" uv venv --python "$v" "$CHECKS/kapso/venv$t"
done
for v in 3.11 3.12; do
  t=${v/./}
  run "uv venv eve/venv$t (python $v)" uv venv --python "$v" "$CHECKS/eve/venv$t"
done

# ---- KAPSO ----
run "KAPSO requirements.txt @3.11" uv pip install --python "$CHECKS/kapso/venv311" -r "$KAPSO/requirements.txt"
run "KAPSO requirements.txt @3.12" uv pip install --python "$CHECKS/kapso/venv312" -r "$KAPSO/requirements.txt"
run "KAPSO pyproject core deps @3.11" uv pip install --python "$CHECKS/kapso/venv311" -r "$CHECKS/kapso/core-reqs.txt"
run "KAPSO pyproject core deps @3.12" uv pip install --python "$CHECKS/kapso/venv312" -r "$CHECKS/kapso/core-reqs.txt"

# ---- EvE (locked) ----
run "eve: uv export --frozen (read-only, from uv.lock)" bash -c \
  "cd $EVE && uv export --frozen --no-emit-project --format requirements-txt -o $CHECKS/eve/locked-reqs.txt && wc -l $CHECKS/eve/locked-reqs.txt"
run "EvE locked set @3.11" uv pip install --python "$CHECKS/eve/venv311" -r "$CHECKS/eve/locked-reqs.txt"
run "EvE locked set @3.12" uv pip install --python "$CHECKS/eve/venv312" -r "$CHECKS/eve/locked-reqs.txt"
run "EvE uv sync --dry-run --frozen @3.11" bash -c \
  "cd $EVE && UV_PROJECT_ENVIRONMENT=$CHECKS/eve/venv311 uv sync --dry-run --frozen --python 3.11"

echo; echo "### MATRIX COMPLETE $(date -Is)" | tee -a "$LOG"
