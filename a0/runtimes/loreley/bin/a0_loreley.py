#!/usr/bin/env python3
"""Absolute entry point for the A0 Loreley adapter.

The adapter needs the pinned Loreley checkout's dependencies (pydantic, SQLAlchemy,
psycopg, numpy...), which live in ``checkout/.venv``.  Discovery by a harness that
picks ``/usr/bin/python3`` therefore cannot import ``loreley``; this script pins the
interpreter instead of hoping for one on ``PATH``, and it resolves its own paths
relative to the file so it works from any cwd.

Invoked through ``bin/a0-loreley``; see ``adapter.json`` for the declared command.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ADAPTER_DIR = HERE.parents[1]
SRC = ADAPTER_DIR / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from a0_adapter.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
