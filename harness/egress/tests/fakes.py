#!/usr/bin/env python3
"""Shared fakes + helpers for the gateway tests (task-independent)."""
import pathlib
import sys
from typing import Any

TESTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent))
sys.path.insert(0, str(TESTS.parent / "gateway"))
import policy as gw_policy  # noqa: E402
from surfaces import FetchError, GithubSurface, NatureSurface  # noqa: E402

CUT = "2022-01-15T00:00:00Z"
PRE = "2021-08-24T12:50:44Z"
POST = "2022-03-01T00:00:00Z"


class FakeGitHub(GithubSurface):
    """Canned GitHub API responses; no network."""

    def __init__(self, routes: dict[str, Any], cutoff_iso: str = CUT) -> None:
        super().__init__(cutoff_iso=cutoff_iso)
        self.routes = routes

    def _api_json(self, path: str) -> dict[str, Any]:
        if path not in self.routes:
            raise FetchError(f"no route: {path}")
        return self.routes[path]


class FakeNature(NatureSurface):
    """Canned publication dates; no network."""

    def __init__(self, published: str | None, cutoff_iso: str = CUT) -> None:
        super().__init__(cutoff_iso=cutoff_iso)
        self.published = published

    def resolve(self, parsed: dict[str, Any]) -> dict[str, Any]:
        if not self.published:
            raise FetchError("publication date not found (fail closed)")
        page = f"https://www.nature.com/articles/{parsed['id']}"
        return {"dates": {"published": self.published}, "t_verified": self.published,
                "resolved": {"id": parsed["id"], "url": page},
                "fetch": {"url": page, "accept": "text/html"}}


def fake_registry(
    surfaces: list[Any],
    forbidden_entries: list[str] | None = None,
    cutoff_iso: str = CUT,
    direct_hosts: set[str] | None = None,
) -> gw_policy.Registry:
    return gw_policy.Registry(
        "test", cutoff_iso, surfaces,
        forbidden=gw_policy.ForbiddenMatcher(forbidden_entries or []),
        policy_version="test",
        direct_hosts=direct_hosts,
    )
