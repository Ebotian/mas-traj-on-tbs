#!/usr/bin/env python3
"""TASK FIXTURES — the ONLY per-task data file.

Migration: copy task_template/ to <task_slug>/ (underscored name), then edit
ONLY this file. Every rule is a (+/-) pair differing in exactly one variable.

STATIC pairs (designated sources — 指定仓库/链接):
    {"name": ..., "deny": <designated link>,
     "allow": <closest NON-designated counterpart>, "deny_reason": "forbidden"}

DYNAMIC pairs (time window, not pre-determined — 按时间):
    {"name": ..., "allow": <pre-cutoff url>, "allow_t": "YYYY-MM-DD",
     "deny": <post-cutoff counterpart>, "deny_t": "YYYY-MM-DD",
     "deny_reason": "post-cutoff"}

Optional per-pair keys: "allow_fetch_none": True (a check-only surface).

Leave TASK = "REPLACE-ME": the suites skip this folder until it is filled.
"""

from typing import Any

from pair_harness import DynamicPair, StaticPair

TASK = "REPLACE-ME"
CUTOFF = "YYYY-MM-DDTHH:MM:SSZ"

STATIC_PAIRS: list[StaticPair] = []
DYNAMIC_PAIRS: list[DynamicPair] = []

FETCH_ROUNDTRIP: dict[str, Any] | None = None   # {"url": ..., "min_bytes": 100}

DOC_SITES: list[str] = []                 # task-stack documentation hosts
ANSWER_HOSTS: list[str] = []              # hosts that must never be directly allowlisted
SURFACE_KINDS: list[str] = []             # gateway surface kinds this task enables
CONTAINER_DENY_URLS: list[str] = []       # must be cut in a trial container
CONTAINER_ALLOW_URLS: list[str] = []      # must be reachable in a trial container
