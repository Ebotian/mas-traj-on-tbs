#!/usr/bin/env python3
"""Pure policy rules shared by the egress tooling, the tests and the gateway.
Every rule here is pinned by a test in egress/tests/.

Rules encoded:
- compose(base, overlay): order-preserving deduped union of the two layers.
- allowed_by_date(t_verified, cutoff_iso): strictly-before; same-day fails
  closed; an unknown date (None) fails closed.
"""
import datetime
import pathlib
from typing import Any

import yaml

POLICIES = pathlib.Path("/home/ebt/harbor-runs/egress/policies")


def load_layers(task: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = yaml.safe_load((POLICIES / "base.yml").read_text())
    overlay = yaml.safe_load((POLICIES / f"{task}.yml").read_text())
    return base, overlay


def compose(base: dict[str, Any], overlay: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    hosts: list[str] = []
    for h in list(base["hosts"]) + list(overlay["restricted_hosts"]):
        if h not in seen:
            seen.add(h)
            hosts.append(h)
    return hosts


def parse_iso_z(s: str | None) -> datetime.datetime:
    """Parse an ISO-8601 timestamp; a date-only/naive value is taken as UTC
    (fail-closed stays intact: a bare cutoff-day date still fails the
    strictly-before test)."""
    dt = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def allowed_by_date(t_verified: str | None, cutoff_iso: str) -> bool:
    if t_verified is None:
        return False
    return parse_iso_z(t_verified) < parse_iso_z(cutoff_iso)
