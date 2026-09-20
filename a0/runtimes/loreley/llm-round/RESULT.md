# One bounded real Loreley round through the codex backend — outcome

Question: with the codex lane restored, can a *bounded* real round run through
Loreley's own codex backend, and does it fit in a ≤20-minute wall-clock cap?

**Answer: yes for the lane and for planning; no for a completed round inside the
cap.** The round ran for 13 m 28 s of wall clock, reached the coding stage with a
real plan from a real model, and was stopped by the round's own watchdog with the
job still `RUNNING` because the *coding* call exceeded its budget. Nothing was
faked, and no evaluation or archive write happened.

## How it was run

```bash
cd a0/runtimes/loreley
timeout 1200 ./llm-round/run_bounded_round.sh      # log: llm-round/bounded_round.log
```

Setup (all in my own directory; a separate database so the A0 evidence database is
untouched):

* candidate repository `llm-round/repo` — a copy of the pinned
  `upstream/circle-packing` checkout, HEAD `b91c0906c9f676eb661990d881144909d99f2d72`
  (also the pinned `MAPELITES_EXPERIMENT_ROOT_COMMIT`)
* `loreley_llm` database on the same Postgres container; `redis://127.0.0.1:6379/1`
  for the Dramatiq queue
* one scheduler tick (`SCHEDULER_MAX_TOTAL_JOBS=1`) + one worker process
* `WORKER_PLANNING_BACKEND` / `WORKER_CODING_BACKEND` =
  `loreley.core.worker.agent.backends.codex_cli:{codex_planning_backend,codex_coding_backend}`
* the A0 evaluator plugin (`WORKER_EVALUATOR_PLUGIN=loreley_a0_plugin:plugin`) wired
  the same way as every other command in this directory

## What happened (measured)

```
### database loreley_llm            CREATE DATABASE / migrate exit=0, schema version 23
### one scheduler tick              dispatch=0 seed_scheduled=1 unfinished=1 remaining_total=0/1
                                    "Scheduled 1 seed jobs from root b91c0906… on island
                                     circle_packing_alpha (phase=warmup …)"
18:24:45  Checked out base commit b91c0906c9f676eb661990d881144909d99f2d72
18:24:45  Planning agent requesting plan (attempt 1/2)
18:27:09  Planning agent generated plan in 144.1s (attempt 1/2)      <- real codex call, succeeded
18:27:09  Coding agent requesting execution (attempt 1/2)
18:35:09  Coding attempt 1 failed: codex exec timed out after 480s.  <- real codex call, exceeded budget
18:35:09  Coding agent requesting execution (attempt 2/2)
18:37:48  round watchdog: worker stopped (t+782s of a 1200s cap)
```

Final database state:

```
evolution_jobs           1 row,  status=RUNNING, result_commit_hash=NULL
evolution_events         job.dispatched, job.run.started,
                         planning.started, planning.finished, coding.started
evaluation_attempts      0 rows
candidate_commits        0 rows
map_elites_archive_cells 0 rows
```

`coding.started` with no `coding.finished`, and no evaluation attempt, is the
trajectory: the round stopped at the *coding* stratum, so `E*` was never invoked
inside the worker and the archive was never touched. This is consistent with — and
independent of — the A0 `failure_stage` vocabulary (`resolve_failed` territory: a
found artifact that was not resolved into a runnable candidate).

## Why the lane needs one configuration line

Loreley's codex backend isolates `CODEX_HOME`
(``codex_cli.py:243-270``): it copies **only** `auth.json` into a temp home and, for
`sandbox == read-only`, writes no `config.toml` at all; for `workspace-write` it
writes a `config.toml` containing only a `[projects."<worktree>"] trust_level`
entry. Either way the user's `~/.codex/config.toml` is **replaced, not merged**, so
`model_provider = "custom"` and `[model_providers.custom] base_url =
http://127.0.0.1:15722/v1` are lost. Codex then falls back to the default OpenAI
endpoint and the proxy-managed key is rejected:

```
$ ./checkout/.venv/bin/python llm-round/stage_a_probe.py     # no CODEX_HOME override
{"ok": false, "duration_s": 47.7,
 "error": "PlanningError: codex exec failed with exit code 1. …
           401 Unauthorized: Incorrect API key provided: PROXY_MA*AGED …
           url: wss://api.openai.com/v1/responses"}
```

The backend has an escape hatch at `codex_cli.py:252-254`
(`if "CODEX_HOME" in (self.extra_env or {}): return`), so this is configuration,
not a patch:

```
WORKER_PLANNING_EXTRA_ENV='{"CODEX_HOME":"/home/ebt/.codex"}'
WORKER_CODING_EXTRA_ENV='{"CODEX_HOME":"/home/ebt/.codex"}'
```

With that line, one bounded call completed in **66.0 s** (`stage_a2_result.json`,
model `gpt-5.6-terra`), and the round's planning stage completed in 144.1 s.

## What is missing for a completed round

Only budget, and it is a real gap rather than an unknown:

| stage | this run | checkout default | fit in 20 min? |
|---|---|---|---|
| scheduler tick + checkout + Worker startup | ~25 s | — | yes |
| planning (`codex`, gpt-5.6-terra) | **144 s** ✅ | 900 s | yes |
| coding attempt 1 (`codex`, workspace-write) | **> 480 s** ❌ | 1800 s | no |
| coding attempt 2 (retry, same budget) | started | — | no |
| commit + `E*` evaluation + archive ingestion | not reached (~1 min expected) | — | — |

Measured wall clock to the watchdog stop: **13 m 28 s**. A round that lets the
coding stage finish needs roughly 15–40 minutes of codex time on this proxy
(`model_reasoning_effort = "high"`), i.e. more than one 20-minute slot but well
inside the checkout's own default coding budget of 1800 s.

Nothing else is missing: the database, the queue, the candidate repository, the
codex lane, the evaluator plugin and the scheduler/worker wiring all worked in this
run. To finish a round, either allow ~40 minutes of wall clock (raise
`WORKER_CODING_TIMEOUT_SECONDS` and the watchdog together), or give the coding
agent a smaller task than "optimise a 26-circle packing" so one codex call fits.

## Effect on the A0 report

The evaluator lane (`E*` executed inside the runtime, A0.1, A0.2) does **not**
depend on the LLM lane: it was already verified end to end through
`Evaluator.evaluate_outcome` and the real archive. What this round adds is a real
*note* for the LLM half:

* the planning lane is **verified on real runtime code** (real `codex exec` through
  `codex_planning_backend`, plan produced, 144.1 s);
* the coding lane is **reached and shown to time out** at a 480 s budget — verified
  as motion, not as completion;
* a full round to a committed candidate and an archived elite remains
  **UNVERIFIED**, with the missing quantity being wall clock, not capability.
