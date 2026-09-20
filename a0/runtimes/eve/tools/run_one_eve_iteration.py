#!/usr/bin/env python
"""One real, codex-backed EvE iteration with the frozen E* as the evaluator.

This is the experiment that converts the adapter's UNVERIFIED LLM wiring into an
end-to-end observation. It runs EvE's *own* loop (`EveFactory.from_config(...).run()`),
with real codex agents for the solver role and the adapter-generated E* evaluation step.

What is real and what is pinned:

* real `EveFactory` / `EveLoop` / `Phase2BatchRunner`, real codex driver
  (`driver: codex_exec`, model from the shipped config `gpt-5.6-sol`), real boundary check,
  real lineages and artifact stores;
* the evaluator is the *same* adapter-generated step `a0_adapter run` uses, so the score a
  produced candidate gets is `E*`'s `fields.sum_radii`;
* `application.editable.files = ["solution.py"]` and the seed solver entry carries a real
  circle-packing baseline as `solution.py`, so the agent has something scoreable to improve.
  This is a declared deviation from the repo's own `candidate.py` list, forced by the study's
  `C*` layout; it is confined to this run directory and does not touch the pinned checkout.

Budget: one iteration, one worker, bounded turns and per-turn timeout. The caller wraps this
in a wall-clock `timeout` as well.

    python tools/run_one_eve_iteration.py --run-dir out/run002 --max-seconds 900
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ADAPTER_DIR))

from a0_adapter import common  # noqa: E402
from a0_adapter.eve_runtime import (  # noqa: E402
    EVE_ROOT,
    _problem_with_retry,
    add_eve_to_path,
    eid_r_payload,
    render_step_script,
    require_pinned_eve,
)

BASELINE_CANDIDATE = common.TASK_DIR / "C_STAR" / "c02_baseline_upstream" / "solution.py"
BASELINE_REFERENCE_SCORE = 0.25  # E*(c02_baseline_upstream), from E_STAR.json


def build_run_config(run_dir: Path, step_script: Path, *, turns: int, turn_timeout: float,
                     inject_codex_provider: bool = False):
    add_eve_to_path()
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    config_dir = EVE_ROOT / "configs" / "eve"
    overrides = [
        f"run_root={run_dir}",
        "run_id=a0-eve-real-1",
        # one iteration, one worker, minimum population needs
        "loop.max_iterations=1",
        "loop.n_workers_phase2=1",
        "loop.n_parallel_phase2=1",
        "loop.n_solver_examples_phase2=1",
        "loop.n_optimizer_examples_phase2=1",
        "loop.produce_optimizer_in_phase2=1",
        "loop.enable_resume=false",
        # the adapter's frozen evaluator
        f'evaluation.steps=["{step_script}"]',
        # the study's candidate layout, declared in the run record
        'application.editable.files=["solution.py"]',
        # bounded agent budget
        f"driver.rollout_max_turns={turns}",
        f"driver.timeout_seconds={turn_timeout}",
        "+driver.overrides.solver.rollout_max_turns=" + str(turns),
        "+driver.overrides.solver.timeout_seconds=" + str(turn_timeout),
    ]
    provider_note = None
    if inject_codex_provider:
        provider_note, provider_overrides = codex_provider_overrides()
        overrides.extend(provider_overrides)
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="circle_packing", overrides=overrides)
    # no logger group: this is a measurement, not a tracked run (wandb is not configured here)
    from omegaconf import open_dict

    if "logger" in cfg:
        with open_dict(cfg):
            del cfg["logger"]
    OmegaConf.resolve(cfg)
    cfg.__dict__["_a0_provider_note"] = provider_note
    return cfg


def codex_provider_overrides() -> tuple[dict, list[str]]:
    """Re-inject the local Codex provider block from ``~/.codex/config.toml``.

    EvE isolates the agent's Codex HOME
    (`providers/agent/codex_isolation.py:42-66`): it symlinks ``auth.json`` but writes a
    *thin* ``config.toml`` rendered from `CodexLaunchConfig`, which has no
    ``model_providers`` block. The agent therefore falls back to Codex's default provider
    (``https://api.openai.com``) and its calls fail with 401 — the relay configuration in
    the user's real ``config.toml`` never reaches the agent. EvE exposes the supported fix:
    `driver.model_provider` + `driver.model_providers.*`, which the codex drivers render as
    ``-c model_providers.<id>.<key>=...`` argv overrides (codex_exec.py:466-485).

    Only structural fields are read; `requires_openai_auth` means the credential comes from
    the symlinked ``auth.json``, so no secret is read, copied or printed here.
    """
    import re

    config_path = Path.home() / ".codex" / "config.toml"
    text = config_path.read_text(encoding="utf-8")
    provider_id = re.search(r'^model_provider\s*=\s*"([^"]+)"', text, re.M)
    if not provider_id:
        return {"injected": False, "reason": "no model_provider in ~/.codex/config.toml"}, []
    pid = provider_id.group(1)
    block = re.search(
        r"^\[model_providers\." + re.escape(pid) + r"\]\s*$(.*?)(?=^\[|\Z)",
        text,
        re.M | re.S,
    )
    if not block:
        return {"injected": False, "reason": f"no [model_providers.{pid}] block"}, []
    fields: dict[str, object] = {}
    for line in block.group(1).splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$', line.strip())
        if not match:
            continue
        key, raw = match.group(1), match.group(2)
        if re.search(r"(key|token|secret|password|cookie)", key, re.I):
            continue
        if raw in ("true", "false"):
            fields[key] = raw == "true"
        elif raw.startswith('"') and raw.endswith('"'):
            fields[key] = raw[1:-1]
        else:
            try:
                fields[key] = float(raw) if "." in raw else int(raw)
            except ValueError:
                fields[key] = raw
    overrides = [f"+driver.model_provider={pid}"]
    for key, value in fields.items():
        rendered = value if isinstance(value, bool) else (value if isinstance(value, (int, float)) else str(value))
        overrides.append(f"+driver.model_providers.{pid}.{key}={rendered}")
    return (
        {
            "injected": True,
            "provider_id": pid,
            "fields": fields,
            "source": str(config_path),
            "why": (
                "EvE's isolated Codex HOME has a thin config.toml with no model_providers "
                "block (codex_isolation.py:42-66); without this injection the agent's calls go "
                "to api.openai.com and fail with 401"
            ),
        },
        overrides,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=str(ADAPTER_DIR / "out" / "run002"))
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--turn-timeout", type=float, default=420.0)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    parser.add_argument(
        "--inject-codex-provider",
        action="store_true",
        help="re-inject the local Codex provider block into the agent's isolated HOME (see "
        "codex_provider_overrides)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record: dict = {
        "schema": "a0.eve.real_round/v1",
        "run_dir": str(run_dir),
        "eve_checkout": {"root": str(EVE_ROOT), "commit": require_pinned_eve()},
        "started_at": common.utc_now(),
        "budget": {"turns": args.turns, "turn_timeout_s": args.turn_timeout,
                   "wall_cap_s": args.max_seconds},
    }

    theta = common.parse_theta("seed=none,fidelity=full,fraction=1.0")
    fr = common.load_fr(common.DEFAULT_FR)
    eid_document = common.read_eid(common.DEFAULT_EID)
    eid_star = eid_document["eid_star"]
    step = render_step_script(
        path=run_dir / "evaluator" / "eve_evaluator_step.sh",
        e_star_python=common.E_STAR_PYTHON,
        e_star_script=common.E_STAR_SCRIPT,
        state_dir=run_dir / "e-star-state",
        theta=theta,
        primary_field=fr.primary_field,
        eid_star=eid_star,
        pins_sha256=fr.spec_hash,
    )
    cfg = build_run_config(
        run_dir, step.path, turns=args.turns, turn_timeout=args.turn_timeout,
        inject_codex_provider=args.inject_codex_provider,
    )
    record["codex_provider_injection"] = cfg.__dict__.get("_a0_provider_note")
    record["config"] = {
        "driver": str(cfg.driver.driver),
        "model": str(cfg.driver.model),
        "web_search": str(cfg.driver.web_search),
        "reasoning_effort": str(cfg.driver.reasoning_effort),
        "rollout_max_turns": int(cfg.driver.rollout_max_turns),
        "timeout_seconds": float(cfg.driver.timeout_seconds),
        "application_editable_files": list(cfg.application.editable.files),
        "evaluation_steps": list(cfg.evaluation.steps),
        "loop_max_iterations": int(cfg.loop.max_iterations),
        "n_workers_phase2": int(cfg.loop.n_workers_phase2),
        "n_solver_examples_phase2": int(cfg.loop.n_solver_examples_phase2),
        "eid_star": eid_star,
        "eid_r": eid_r_payload(
            step, eid_document=eid_document, fr_spec_hash=fr.spec_hash
        )["value"],
    }

    from omegaconf import OmegaConf
    from scaling_evolve.algorithms.eve.factory import EveFactory
    from scaling_evolve.algorithms.eve.populations.entry import PopulationEntry
    from scaling_evolve.algorithms.eve.runtime.driver import build_role_drivers, load_pricing_table
    from scaling_evolve.algorithms.eve.workflow.evaluation import (
        build_evaluation_plan,
        build_solver_evaluator,
    )

    application = OmegaConf.to_container(cfg.application, resolve=True)
    problem = _problem_with_retry(
        application, cache_root=run_dir / ".repo_cache", search_root=EVE_ROOT
    )
    record["seed_repo"] = {
        "github_url": problem.github_url,
        "commit": problem.commit,
        "snapshot_root": str(problem.snapshot_root),
        "editable_files": list(problem.editable_files),
    }
    plan = build_evaluation_plan(problem, evaluation_config=cfg.evaluation, search_root=EVE_ROOT)
    failure_score = OmegaConf.to_container(cfg.evaluation.failure_score, resolve=True)
    boundary_score = OmegaConf.to_container(cfg.application.boundary_failure_score, resolve=True)

    drivers = build_role_drivers(
        OmegaConf.to_container(cfg.driver, resolve=True),
        run_root=run_dir,
        worker_slots=int(cfg.loop.n_parallel_phase2),
        pricing_table=load_pricing_table(EVE_ROOT / "configs" / "pricing.yaml"),
    )
    try:
        solver_evaluator = build_solver_evaluator(
            problem,
            evaluation_plan=plan,
            evaluation_failure_score=failure_score,
            boundary_failure_score=boundary_score,
            seed_solver_score=None,
            seed_solver_skip_evaluation=False,
            include_solver_examples=False,
            evaluation_driver_factory=drivers.eval_driver_factory,
        )
        with EveFactory.from_config(
            cfg,
            solver_evaluator,
            solver_driver=drivers.solver_driver,
            logger=None,
            task_problem=problem,
            search_root=EVE_ROOT,
        ) as factory:
            factory.seed_initial_guidance(search_root=EVE_ROOT)
            baseline_src = BASELINE_CANDIDATE.read_text(encoding="utf-8")
            seed_id = PopulationEntry.make_id("solver")
            factory.loop.solver_pop.add(
                PopulationEntry(
                    id=seed_id,
                    files={"solution.py": baseline_src},
                    score={"score": BASELINE_REFERENCE_SCORE, "sum_radii": BASELINE_REFERENCE_SCORE},
                    logs={},
                )
            )
            record["seed_solver"] = {
                "id": seed_id,
                "source": "C*/c02_baseline_upstream/solution.py",
                "declared_score": BASELINE_REFERENCE_SCORE,
            }
            record["populations_before"] = {
                "solver": [e.id for e in factory.loop.solver_pop.entries()],
                "optimizer": [e.id for e in factory.loop.optimizer_pop.entries()],
            }
            print(f"[eve-round] starting factory.run() at {common.utc_now()}", flush=True)
            factory.run(start_iteration=0)
            print(f"[eve-round] factory.run() returned at {common.utc_now()}", flush=True)
            after = factory.loop.solver_pop.entries()
            record["populations_after"] = {
                "solver": [
                    {
                        "id": e.id,
                        "score": e.score,
                        "solution_sha256": __import__("hashlib")
                        .sha256(e.files.get("solution.py", "").encode())
                        .hexdigest(),
                        "solution_bytes": len(e.files.get("solution.py", "")),
                    }
                    for e in after
                ],
                "optimizer": [e.id for e in factory.loop.optimizer_pop.entries()],
            }
            record["iterations_completed"] = int(factory.loop.iterations_completed)
    finally:
        try:
            drivers.close()
        except Exception:  # noqa: BLE001
            pass

    record["wall_seconds"] = round(time.monotonic() - started, 2)
    record["finished_at"] = common.utc_now()
    (run_dir / "real_round.json").write_text(
        json.dumps(record, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(record.get("populations_after"), indent=1, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
