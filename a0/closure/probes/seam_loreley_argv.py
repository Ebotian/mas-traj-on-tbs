#!/usr/bin/env python3
"""Execute Loreley's real agent backends to dump the argv each backend uses.

Run from the pinned Loreley checkout with its own venv (see run_probes.sh):

    cd a0/tasks/circle-packing/upstream/loreley && ./.venv/bin/python .../seam_loreley_argv.py

No DB, no Redis and no model call: `_build_command` and the settings object are
enough. What it establishes:

1. The DEFAULT backends (kilocode) launch `kilo run --auto` with no sandbox,
   no network and no web-search flag: the default path has no closure switch
   at all.
2. The alternative codex backend launches
   `codex -a never --sandbox workspace-write exec ...` -- i.e. it inherits the
   Codex CLI's own sandbox, which `cli_sandbox_probe.sh` proves blocks egress.
   Switching backends is therefore a real closure mechanism (with the caveat
   that it also changes M/P/T, see VERDICTS.md).
"""

from __future__ import annotations

from pathlib import Path

from loreley.config import Settings
from loreley.core.worker.agent.backends.codex_cli import (
    CodexCliBackend,
    codex_coding_backend,
    codex_planning_backend,
)
from loreley.core.worker.agent.backends.kilocode_cli import KilocodeCliBackend

KILO = "kilo"


def main() -> int:
    print("### Loreley seam probe: argv built by Loreley's own backends")

    settings = Settings()
    print("\n--- default backend selection (Settings defaults, env-overridable) ---")
    print(f"worker_planning_backend = {settings.worker_planning_backend!r}")
    print(f"worker_coding_backend   = {settings.worker_coding_backend!r}")
    print(f"worker_seed_portfolio_backend = {settings.worker_seed_portfolio_backend!r}")

    print("\n--- kilocode backend (the default) ---")
    kilo = KilocodeCliBackend()
    print(f"kilo argv with defaults   : {kilo._build_command('PROMPT', title='t')}")
    print(f"kilo argv pure=true       : {kilo._build_command('PROMPT', title='t') if not kilo.pure else ''}")
    print(
        "kilo closure switches     : none -- the backend dataclass exposes no sandbox, "
        "no network and no web-search field (kilocode_cli.py:455-470)"
    )

    print("\n--- codex backend (opt-in alternative) ---")
    for label, factory in (("planning", codex_planning_backend), ("coding", codex_coding_backend)):
        try:
            backend = factory()
            argv = backend._build_command(output_last_message_path=None)
            print(f"codex {label} backend: sandbox={backend._requested_sandbox()!r} argv={argv}")
        except Exception as exc:  # noqa: BLE001 - report, do not abort the probe
            print(f"codex {label} backend: could not build ({type(exc).__name__}: {exc})")

    print("\n--- explicit backend construction, both postures ---")
    closed = CodexCliBackend(bin="codex", timeout_seconds=60, extra_env={},
                             error_cls=RuntimeError, full_auto=True, sandbox="workspace-write")
    read_only = CodexCliBackend(bin="codex", timeout_seconds=60, extra_env={},
                                error_cls=RuntimeError, full_auto=False, sandbox="read-only")
    print(f"coding  (workspace-write): {closed._build_command(output_last_message_path=None)}")
    print(f"planning(read-only)      : {read_only._build_command(output_last_message_path=None)}")

    print("\n--- is the kilocode binary even present on this host? ---")
    import shutil

    print(f"shutil.which('{KILO}') = {shutil.which(KILO)!r}")
    print(f"codex binary: {shutil.which('codex')!r}")

    print("\n--- resulting probe command for the codex backend's sandbox ---")
    print(
        "codex sandbox -c 'sandbox_mode=\"workspace-write\"' -- <canary>   "
        "# see cli_sandbox_probe.sh, executed as the Loreley-codex-backend evidence"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
