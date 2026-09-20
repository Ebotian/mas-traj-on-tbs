"""Stage A2: the same backend, a minimal prompt, a 300 s budget.

Stage A1 answered the reachability question (401 with the backend's isolated
CODEX_HOME, timeout with the real one).  This asks the remaining one: can one real
call *complete* inside a budget a bounded round could afford?
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "checkout"))

os.environ.update({
    "APP_NAME": "loreley-a0-llm", "APP_ENV": "development", "LOG_LEVEL": "INFO",
    "EXPERIMENT_ID": "a0-loreley-llm-round",
    "DATABASE_URL": "postgresql+psycopg://loreley:loreley@127.0.0.1:5432/loreley",
    "TASKS_REDIS_URL": "redis://127.0.0.1:6379/0",
    "MAPELITES_EXPERIMENT_ROOT_COMMIT": "b91c0906c9f676eb661990d881144909d99f2d72",
    "WORKER_REPO_REMOTE_URL": str(HERE / "repo"),
    "WORKER_REPO_BRANCH": "main",
    "WORKER_PLANNING_BACKEND": "loreley.core.worker.agent.backends.codex_cli:codex_planning_backend",
    "WORKER_CODING_BACKEND": "loreley.core.worker.agent.backends.codex_cli:codex_coding_backend",
    "WORKER_PLANNING_CODEX_MODEL": "gpt-5.6-terra",
    "WORKER_CODING_CODEX_MODEL": "gpt-5.6-terra",
    "WORKER_PLANNING_TIMEOUT_SECONDS": os.environ.get("A0_LLM_TIMEOUT", "300"),
    "WORKER_PLANNING_EXTRA_ENV": '{"CODEX_HOME":"/home/ebt/.codex"}',
    "WORKER_CODING_EXTRA_ENV": '{"CODEX_HOME":"/home/ebt/.codex"}',
    "WORKER_PLANNING_TRAJECTORY_MAX_CHUNKS": "0",
})

from loreley.core.worker.agent.contracts import AgentTask  # noqa: E402
from loreley.core.worker.agent.backends.codex_cli import codex_planning_backend  # noqa: E402


def main() -> int:
    backend = codex_planning_backend()
    started = time.monotonic()
    record: dict[str, object] = {
        "backend": type(backend).__name__,
        "bin": backend.bin,
        "model": backend.model,
        "timeout_s": backend.timeout_seconds,
        "extra_env": dict(backend.extra_env or {}),
    }
    try:
        invocation = backend.run(
            AgentTask(name="a0-codex-lane-probe-2", prompt="Reply with exactly: ok"),
            working_dir=HERE / "repo",
        )
        record["ok"] = True
        record["duration_s"] = round(time.monotonic() - started, 1)
        for attribute in ("summary", "output", "last_message", "text"):
            value = getattr(invocation, attribute, None)
            if isinstance(value, str) and value.strip():
                record.setdefault("output_text", value.strip()[:400])
        record["fields"] = sorted(n for n in dir(invocation) if not n.startswith("_"))
    except Exception as exc:  # noqa: BLE001
        record["ok"] = False
        record["duration_s"] = round(time.monotonic() - started, 1)
        record["error"] = f"{type(exc).__name__}: {exc}"[:800]
    print(json.dumps(record, indent=1))
    (HERE / "stage_a2_result.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if record.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
