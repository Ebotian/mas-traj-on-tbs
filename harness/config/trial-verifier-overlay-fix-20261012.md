# trial.py verifier-overlay fix (2026-10-12)

**Problem.** The 2026-10-09 local patch made `_separate_verifier_env` pass
`config/verifier-build-overlay.yaml` (context `build/dataset-build` =
tumor rehearsal package) to EVERY separate verifier environment. microarch-1's
verifier image was therefore built from the tumor package and ran tumor's
grader (ctrf tool `tumor-immune-interface-verifier`, reward 0.0 — invalid;
see related_files/2026-10-08-first-measurement-spec.md, 2026-10-12 entry).

**Fix.** Apply the overlay only for the restricted tumor copy
(task path basename == `task-restricted`); otherwise keep harbor's upstream
behavior (empty list → default build from the task's own `tests/` dir).

File: `/home/ebt/.local/share/uv/tools/harbor/lib/python3.14/site-packages/harbor/trial/trial.py`
(backup of the stock file: `trial.py.orig-20261009`)

Patched region in `_separate_verifier_env`:

```python
env_config = definition.config
# 2026-10-12 fix (spec 2026-10-12 entry): the rehearsal overlay is
# tumor-specific — the restricted copy's upstream tests/Dockerfile
# fetches its payload from huggingface at build time, which breaks on
# this machine, so it must build from build/dataset-build instead.
# Applying it unconditionally mis-built microarch's verifier image from
# the tumor package (its verifier ran tumor's grader). Gate on task path;
# overlay path stays literal for check_paths.py.
_task_path = Path(str(self.config.task.path or ""))
_verifier_overlay = Path(
    "/home/ebt/harbor-runs/config/verifier-build-overlay.yaml"
)
_use_rehearsal_overlay = (
    _task_path.name == "task-restricted" and _verifier_overlay.exists()
)
verifier_runtime_config = self.config.environment.model_copy(
    update={
        "extra_docker_compose": (
            [_verifier_overlay] if _use_rehearsal_overlay else []
        )
    }
)
```

**Re-check after `uv tool upgrade harbor`** (upgrade overwrites trial.py).
Guard: `python3 config/check_paths.py` (covers the overlay path reference).

**Verified 2026-10-12** — smoke trial `microarch-vfix-smoke/task-microarch__TjGqW8y`:
verifier image `/tests` = `Dockerfile, feature_schema.json, hidden_cases.csv,
test.sh, test_model.py`; ctrf `tool=pytest`, tests `test_model.py::*` — the
tumor grader is gone and microarch's own grader runs.
