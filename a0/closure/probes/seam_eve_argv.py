#!/usr/bin/env python3
"""Execute EvE's real session-driver code to dump the argv each lane uses.

Run with the pinned EvE checkout on PYTHONPATH (see run_probes.sh):

    PYTHONPATH=/tmp/eve/src <venv>/bin/python seam_eve_argv.py

No model call is made: `_argv`/`_build_*_driver` are pure functions of the
driver config, so the exact commands EvE would launch are observable even
while `codex exec` cannot complete (its provider relay has no live upstream).

What it establishes:

1. `codex_tmux` does carry the closure controls the protocol section 4.3
   names (`-s <sandbox_mode>` and `-c web_search="..."`).
2. `codex_exec` -- the driver the SHIPPED full-run preset uses -- carries no
   sandbox control at all and hardcodes
   `--dangerously-bypass-approvals-and-sandbox`.
3. Setting `driver.sandbox_mode=workspace-write` for the `codex_exec` driver
   is silently ignored (not rejected), which is a false-green trap: the config
   key looks like closure and is not closure.
"""

from __future__ import annotations

import os
from pathlib import Path

from scaling_evolve.algorithms.eve.runtime.driver import (
    _build_codex_exec_driver,
    _build_codex_tmux_driver,
    _sandbox_mode_from_driver_cfg,
    _web_search_from_driver_cfg,
)
from scaling_evolve.providers.agent.drivers.codex_exec import CodexExecSessionDriver
from scaling_evolve.providers.agent.drivers.codex_tmux import CodexTmuxSessionDriver

RUN_ROOT = Path(os.environ.get("EVE_SEAM_RUN_ROOT", "/tmp/a0-closure-eve-runroot"))
WORKTREE = Path(os.environ.get("EVE_SEAM_WORKTREE", "/tmp/a0-closure-eve-worktree"))


def show(label: str, argv: list[str]) -> None:
    print(f"{label}: {argv}")


def main() -> int:
    print("### EvE seam probe: argv built by EvE's own driver code")
    try:
        import scaling_evolve

        print(f"### scaling_evolve from: {scaling_evolve.__file__}")
    except Exception:  # noqa: BLE001
        pass

    print("\n--- codex_tmux driver (the one the protocol recipe describes) ---")
    tmux = CodexTmuxSessionDriver(
        pane_id="seam-pane",
        run_root=RUN_ROOT,
        sandbox_mode="workspace-write",
        web_search="disabled",
        approval_policy="never",
    )
    show(
        "codex_tmux default-closed argv",
        tmux._argv(WORKTREE, session_id=None, instruction="PROMPT", prompt_file=None),
    )
    print(f"codex_tmux sandbox_mode={tmux.sandbox_mode!r} web_search={tmux.web_search!r}")

    print("\n--- codex_exec driver (SHIPPED full-run preset uses this) ---")
    exec_driver = CodexExecSessionDriver(run_root=RUN_ROOT, web_search="live")
    show(
        "codex_exec argv (Driver constructor has NO sandbox_mode parameter)",
        exec_driver._argv(worktree_root=WORKTREE, session_id=None, instruction="PROMPT"),
    )

    print("\n--- config-plumbing check: does driver.sandbox_mode reach codex_exec? ---")
    cfg = {
        "driver": "codex_exec",
        "sandbox_mode": "workspace-write",
        "allow_network": False,
        "web_search": "disabled",
    }
    built = _build_codex_exec_driver(cfg, role="solver", run_root=RUN_ROOT, pricing_table=None)
    has_attr = hasattr(built, "sandbox_mode")
    print(f"cfg={cfg}")
    print(f"built subtype={type(built).__name__} has sandbox_mode attr={has_attr}")
    show(
        "codex_exec argv with sandbox_mode=workspace-write in the config",
        built._argv(worktree_root=WORKTREE, session_id=None, instruction="PROMPT"),
    )
    if not has_attr:
        print(
            "FINDING: the config key `driver.sandbox_mode` is SILENTLY IGNORED by the "
            "codex_exec driver (accepted, never applied). Config-only closure for this "
            "driver is a false green."
        )

    print("\n--- helpers that translate driver config into sandbox/web-search ---")
    for probe_cfg in (
        {"sandbox_mode": "workspace-write", "allow_network": False},
        {"allow_network": False},
        {"allow_network": True},
        {},
    ):
        print(
            f"_sandbox_mode_from_driver_cfg({probe_cfg}) = "
            f"{_sandbox_mode_from_driver_cfg(probe_cfg)!r}  "
            f"web_search={_web_search_from_driver_cfg(probe_cfg)!r}"
        )

    print("\n--- tmux driver built through the same config plumbing ---")
    # A real pool would spawn a tmux session; for an argv probe a pool stub is
    # enough (the driver only reads `pane_pool.cwd` while building its config).
    class _PoolStub:
        cwd = str(WORKTREE)

    tmux_built = _build_codex_tmux_driver(
        {"driver": "codex_tmux", "sandbox_mode": "workspace-write", "allow_network": False,
         "web_search": "disabled"},
        role="solver",
        run_root=RUN_ROOT,
        pane_pool=_PoolStub(),  # type: ignore[arg-type]
        worker_slots=1,
        pricing_table=None,
    )
    print(f"tmux built from cfg: sandbox_mode={tmux_built.sandbox_mode!r} "
          f"web_search={tmux_built.web_search!r} approval_policy={tmux_built.approval_policy!r}")

    print("\n--- shipped presets, read from the pinned checkout (configs/eve/driver/) ---")
    for name in ("codex_smoke", "codex_max"):
        path = Path("/tmp/eve/configs/eve/driver") / f"{name}.yaml"
        if path.is_file():
            body = path.read_text(encoding="utf-8")
            keys = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("driver:")]
            search_line = next(
                (ln.strip() for ln in body.splitlines() if ln.strip().startswith("web_search:")),
                "<no web_search key>",
            )
            print(f"{name}.yaml: {' ; '.join(keys)} | {search_line}")
    cp = Path("/tmp/eve/configs/eve/circle_packing.yaml")
    if cp.is_file():
        driver_default = next(
            (ln.strip() for ln in cp.read_text(encoding="utf-8").splitlines()
             if "driver:" in ln and ln.strip().startswith("-")),
            "<none>",
        )
        print(f"circle_packing.yaml defaults -> {driver_default}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
