#!/usr/bin/env bash
# =============================================================================
# llm-round/run_bounded_round.sh -- ONE bounded real Loreley round via codex.
#
# Wall-clock cap: 1200 s (20 minutes), enforced by `timeout` at the call site and
# by an internal watchdog.  Everything is logged; whatever happens is the result.
#
# What it does
#   1. a separate database (loreley_llm) so the A0 evidence database is untouched
#   2. migrate, then start one worker process
#   3. one scheduler tick, capped at one job
#   4. wait for the job to reach a terminal state, or give up at the cap
#   5. dump the job / attempt / archive rows and the E* outcomes
#
# The codex lane needs WORKER_*_EXTRA_ENV={"CODEX_HOME":"~/.codex"}: the backend's
# _prepare_isolated_home() writes a fresh CODEX_HOME containing only auth.json
# (codex_cli.py:243-270), which discards the user's [model_providers.custom]
# block and sends the call to api.openai.com with a proxy-managed key (401).
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_DIR="$(cd "$HERE/.." && pwd)"
CHECKOUT="$ADAPTER_DIR/checkout"
PY="$CHECKOUT/.venv/bin/python"
SRC="$ADAPTER_DIR/src"
REPO="$HERE/repo"
WORKTREE="$HERE/worker-repo"
LOGS="$HERE/logs"
DB_NAME="${A0_LLM_DB:-loreley_llm}"
export PYTHONPATH="$SRC"

mkdir -p "$LOGS"
export CODEX_HOME_REAL="$HOME/.codex"

export APP_NAME="loreley-a0-llm"
export APP_ENV="development"
export LOG_LEVEL="INFO"
export LOGS_BASE_DIR="$LOGS"
export EXPERIMENT_ID="a0-loreley-llm-round"
export DATABASE_URL="postgresql+psycopg://loreley:loreley@127.0.0.1:5432/$DB_NAME"
export DB_AUTO_MIGRATE="true"
export TASKS_REDIS_URL="redis://127.0.0.1:6379/1"

export WORKER_REPO_REMOTE_URL="$REPO"
export WORKER_REPO_BRANCH="main"
export WORKER_REPO_WORKTREE="$WORKTREE"
export WORKER_REPO_WORKTREE_RANDOMIZE="false"
export SCHEDULER_REPO_ROOT="$REPO"
export SCHEDULER_POLL_INTERVAL_SECONDS="5"
export SCHEDULER_MAX_UNFINISHED_JOBS="1"
export SCHEDULER_MAX_TOTAL_JOBS="1"
export SCHEDULER_SCHEDULE_BATCH_SIZE="1"
export SCHEDULER_DISPATCH_BATCH_SIZE="1"
export SCHEDULER_INGEST_BATCH_SIZE="1"
export SCHEDULER_STARTUP_APPROVE="true"

export MAPELITES_EXPERIMENT_ROOT_COMMIT="b91c0906c9f676eb661990d881144909d99f2d72"
export MAPELITES_ISLANDS='["circle_packing_alpha"]'
export MAPELITES_OBJECTIVES='[{"name":"composite_score","direction":"max"}]'
export MAPELITES_ARCHIVE_CELLS_PER_DIM="8"
export MAPELITES_DIMENSION_REDUCTION_TARGET_DIMS="2"
export MAPELITES_PARETO_FRONT_MAX_SIZE="4"
export MAPELITES_SEED_POPULATION_SIZE="1"
export MAPELITES_SEED_PORTFOLIO_ENABLED="false"
export MAPELITES_CODE_EMBEDDING_MODEL="local-hash-v1"
export MAPELITES_CODE_EMBEDDING_DIMENSIONS="64"
export MAPELITES_LOCAL_HASH_EMBEDDING_ACKNOWLEDGED="true"
export MAPELITES_SAMPLER_SEED="0"
export BASELINE_BOOTSTRAP_POLICY="required"

export WORKER_PROCESSES="1"
export WORKER_PLANNING_BACKEND="loreley.core.worker.agent.backends.codex_cli:codex_planning_backend"
export WORKER_CODING_BACKEND="loreley.core.worker.agent.backends.codex_cli:codex_coding_backend"
export WORKER_PLANNING_CODEX_MODEL="gpt-5.6-terra"
export WORKER_CODING_CODEX_MODEL="gpt-5.6-terra"
export WORKER_PLANNING_TIMEOUT_SECONDS="420"
export WORKER_CODING_TIMEOUT_SECONDS="480"
export WORKER_PLANNING_EXTRA_ENV="{\"CODEX_HOME\":\"$HOME/.codex\"}"
export WORKER_CODING_EXTRA_ENV="{\"CODEX_HOME\":\"$HOME/.codex\"}"
export WORKER_PLANNING_TRAJECTORY_MAX_CHUNKS="0"

export WORKER_EVALUATOR_PLUGIN="loreley_a0_plugin:plugin"
export WORKER_EVALUATOR_PYTHON_PATHS="[\"$SRC\"]"
export WORKER_EVALUATOR_TIMEOUT_SECONDS="300"
export WORKER_EVALUATOR_MAX_METRICS="64"
export A0_E_STAR_PY="/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python"
export A0_E_STAR_SCRIPT="/home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py"
export A0_E_STAR_SEED="1337"
export A0_E_STAR_FIDELITY="full"
export A0_E_STAR_FRACTION="1.0"
export A0_E_STAR_STATE_DIR="$HERE/e-star-state"
export A0_E_STAR_OUT_DIR="$HERE/e-star-out"
export A0_EVIDENCE_DIR="$HERE/evaluator-evidence"
export A0_E_STAR_N="26"
export A0_E_STAR_RUNS="5"
export A0_FR_MODE_SCALAR="1"
export A0_FR_METRIC_NAME="composite_score"
export A0_FR_SPEC_HASH="1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0"
export CIRCLE_PACKING_RUNTIME_BUDGET_MS="250.0"
export CIRCLE_PACKING_RUNTIME_RUNS="5"

say() { printf '\n### %s\n' "$*"; }

say "database $DB_NAME"
docker exec a0-loreley-postgres psql -U loreley -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
  || docker exec a0-loreley-postgres psql -U loreley -d postgres -c "CREATE DATABASE $DB_NAME"
"$PY" -m loreley.cli db migrate >"$LOGS/migrate.log" 2>&1
echo "migrate exit=$?"; tail -3 "$LOGS/migrate.log"

say "worker up"
"$PY" -m loreley.cli worker -p 1 --no-preflight >"$LOGS/worker.log" 2>&1 &
WORKER_PID=$!
sleep 12

say "one scheduler tick"
"$PY" -m loreley.cli scheduler --once --yes --no-preflight >"$LOGS/scheduler.log" 2>&1
echo "scheduler exit=$?"; tail -5 "$LOGS/scheduler.log"
"$PY" -m loreley.cli scheduler --once --yes --no-preflight >"$LOGS/scheduler2.log" 2>&1
echo "scheduler2 exit=$?"

say "waiting for a terminal job state (watchdog)"
DEADLINE=$(( $(date +%s) + 780 ))
STATE="unknown"
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  STATE=$(docker exec a0-loreley-postgres psql -U loreley -d "$DB_NAME" -tAc \
    "SELECT coalesce(string_agg(status || ':' || count::text, ','), 'none') FROM (SELECT status, count(*) FROM evolution_jobs GROUP BY status) s" 2>/dev/null || echo 'query-failed')
  echo "t+$(( $(date +%s) - (DEADLINE - 780) ))s jobs=$STATE"
  case "$STATE" in
    *completed*|*failed*) break ;;
  esac
  sleep 20
done

say "final job rows"
docker exec a0-loreley-postgres psql -U loreley -d "$DB_NAME" -c \
  "SELECT id, status, island_id, result_commit_hash, failure_stage, failure_kind, left(coalesce(failure_summary,''),120) AS summary FROM evolution_jobs" 2>&1 | head -20

say "evaluation attempts"
docker exec a0-loreley-postgres psql -U loreley -d "$DB_NAME" -c \
  "SELECT evaluator_name, evaluator_version, protocol, outcome_kind, reuse_kind, failure_kind FROM evaluation_attempts" 2>&1 | head -20

say "archive cells"
docker exec a0-loreley-postgres psql -U loreley -d "$DB_NAME" -c \
  "SELECT island_id, cell_index, commit_hash, objective_values FROM map_elites_archive_cells" 2>&1 | head -20

say "shutting the worker down"
kill "$WORKER_PID" 2>/dev/null || true
sleep 3
kill -9 "$WORKER_PID" 2>/dev/null || true
echo "worker log tail:"; tail -25 "$LOGS/worker.log"
echo "DONE"
