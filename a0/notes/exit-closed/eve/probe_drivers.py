"""Read-only probe: does EvE compose + build the opencode lane without codex?

Run from /tmp/eve (the tests resolve configs relative to cwd) with
PYTHONPATH=/tmp/eve/src and PYTHONDONTWRITEBYTECODE=1.
No model calls, no installs: build_role_drivers never launches the CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

from scaling_evolve.algorithms.eve.runtime.driver import build_role_drivers
from scaling_evolve.providers.agent.drivers.codex_exec import CodexExecSessionDriver
from scaling_evolve.providers.agent.drivers.opencode import OpenCodeSessionDriver


def compose_driver(name: str, config_name: str = "circle_packing") -> dict:
    with initialize_config_dir(config_dir=str(Path("configs/eve").resolve()), version_base=None):
        cfg = compose(config_name=config_name, overrides=[f"driver={name}"])
    container = OmegaConf.to_container(cfg.driver, resolve=True)
    assert isinstance(container, dict)
    return container


def main() -> int:
    for name in ("codex_max", "opencode_max"):
        cfg = compose_driver(name)
        drivers = build_role_drivers(cfg, run_root=Path("/tmp/eve-probe-run"), worker_slots=1)
        print(
            f"{name}: keys={sorted(cfg)} "
            f"solver={type(drivers.solver_driver).__name__} "
            f"eval={type(drivers.eval_driver_factory()).__name__}"
        )
        if name == "opencode_max":
            assert isinstance(drivers.solver_driver, OpenCodeSessionDriver)
            assert isinstance(drivers.eval_driver_factory(), OpenCodeSessionDriver)
            assert drivers.solver_driver.executable == "opencode"
        else:
            assert isinstance(drivers.solver_driver, CodexExecSessionDriver)

    # Does the codex provider-relay injection our adapter uses survive an
    # opencode switch?  run_one_eve_iteration.py --inject-codex-provider adds
    # driver.model_provider / driver.model_providers.*; reproduce that shape.
    cfg = compose_driver("opencode_max")
    cfg["model_provider"] = "zjapi"
    cfg["model_providers"] = {"zjapi": {"env_key": "ZJAPI_KEY", "base_url": "http://x"}}
    try:
        build_role_drivers(cfg, run_root=Path("/tmp/eve-probe-run"), worker_slots=1)
    except SystemExit as exc:
        print(f"opencode + codex-style provider block -> SystemExit: {exc}")
    else:
        print("opencode + codex-style provider block -> ACCEPTED (unexpected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
