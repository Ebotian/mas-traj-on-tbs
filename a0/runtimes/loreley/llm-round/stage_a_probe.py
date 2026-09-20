"""Stage A of the codex-lane question: one real planning call through Loreley's own backend.

This does not touch the archive or the database.  It asks the narrow question that
gates any LLM round: can the pinned checkout's ``codex_planning_backend()``
(``loreley/core/worker/agent/backends/codex_cli.py:280-297``) complete a real model
call on this host, where until now ``codex`` could not.

Everything is bounded: one call, one timeout, one throwaway worktree.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER_DIR = HERE.parent
CHECKOUT = ADAPTER_DIR / "checkout"
REPO = HERE / "repo"
sys.path.insert(0, str(CHECKOUT))

ENV = {
    "APP_NAME": "loreley-a0-llm",
    "APP_ENV": "development",
    "LOG_LEVEL": "INFO",
    "EXPERIMENT_ID": "a0-loreley-llm-round",
    "DATABASE_URL": "postgresql+psycopg://loreley:loreley@127.0.0.1:5432/loreley",
    "DB_AUTO_MIGRATE": "true",
    "TASKS_REDIS_URL": "redis://127.0.0.1:6379/0",
    "MAPELITES_EXPERIMENT_ROOT_COMMIT": "b91c0906c9f676eb661990d881144909d99f2d72",
    "WORKER_REPO_REMOTE_URL": str(REPO),
    "WORKER_REPO_BRANCH": "main",
    "WORKER_PLANNING_BACKEND": "loreley.core.worker.agent.backends.codex_cli:codex_planning_backend",
    "WORKER_CODING_BACKEND": "loreley.core.worker.agent.backends.codex_cli:codex_coding_backend",
    "WORKER_PLANNING_CODEX_MODEL": os.environ.get("A0_LLM_MODEL", "gpt-5.6-terra"),
    "WORKER_CODING_CODEX_MODEL": os.environ.get("A0_LLM_MODEL", "gpt-5.6-terra"),
    "WORKER_PLANNING_TIMEOUT_SECONDS": os.environ.get("A0_LLM_TIMEOUT", "240"),
    "WORKER_PLANNING_TRAJECTORY_MAX_CHUNKS": "0",
    "LLM_USAGE_TRACKING_ENABLED": "true",
}

PROMPT = (
    "You are planning a small change to a circle-packing solution repository.\n"
    "Read solution.py and pack_circles().\n"
    "Do NOT modify any file.\n"
    "Reply with a short plan (at most 8 lines) describing one concrete, small change "
    "that would increase the sum of radii for pack_circles(26), and state the single "
    "file you would edit.\n"
)


def main() -> int:
    for key, value in ENV.items():
        os.environ[key] = value

    from loreley.core.worker.agent.contracts import AgentTask
    from loreley.core.worker.agent.backends.codex_cli import codex_planning_backend

    print(json.dumps({"probe": "codex planning backend", "repo": str(REPO),
                      "model": ENV["WORKER_PLANNING_CODEX_MODEL"],
                      "timeout_s": ENV["WORKER_PLANNING_TIMEOUT_SECONDS"]}))
    backend = codex_planning_backend()
    print(json.dumps({"backend": type(backend).__name__, "bin": backend.bin,
                      "sandbox": backend.sandbox, "isolate_home": backend.isolate_home}))

    started = time.monotonic()
    record: dict[str, object] = {}
    try:
        invocation = backend.run(
            AgentTask(name="a0-codex-lane-probe", prompt=PROMPT), working_dir=REPO
        )
        record["ok"] = True
        record["duration_s"] = round(time.monotonic() - started, 1)
        for attribute in ("summary", "text", "output", "last_message"):
            value = getattr(invocation, attribute, None)
            if isinstance(value, str) and value.strip():
                record[attribute] = value.strip()[:1200]
        record["invocation_fields"] = sorted(
            name for name in dir(invocation) if not name.startswith("_")
        )
    except Exception as exc:  # noqa: BLE001 - the failure mode is the measurement
        record["ok"] = False
        record["duration_s"] = round(time.monotonic() - started, 1)
        record["error"] = f"{type(exc).__name__}: {exc}"[:1500]
    print(json.dumps(record, indent=1))
    (HERE / "stage_a_result.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if record.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
