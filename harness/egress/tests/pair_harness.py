#!/usr/bin/env python3
"""Generic task-suite bases: every rule as a positive/negative PAIR.

Pairs (they must occur in pairs, differing in exactly one variable):
- STATIC pairs (task-designated sources): a designated link denies via the
  task's forbidden list while its closest NON-designated counterpart allows —
  only the designation differs. Offline-checkable: the forbidden clause fires
  before any resolution.
- DYNAMIC pairs (time window, not pre-determined): a pre-cutoff object allows,
  its post-cutoff counterpart denies — only time differs. The fixtures carry
  the resolved dates so the cutoff semantics are also testable offline.

A task folder = fixtures.py (the ONLY per-task file) + byte-identical copies
of the three test files from task_template/; isomorphism is enforced by
tests/test_task_isomorphism.py.
"""
import os
import pathlib
import subprocess
import sys
import unittest
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

TESTS = pathlib.Path(__file__).resolve().parent
EGRESS = TESTS.parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(EGRESS))
sys.path.insert(0, str(EGRESS / "gateway"))
import common  # noqa: E402
import rulelib  # noqa: E402
import policy as gw_policy  # noqa: E402

LIVE = os.environ.get("GATEWAY_LIVE") == "1"
CONTAINER: str = os.environ.get("POLICY_TEST_CONTAINER") or ""

if TYPE_CHECKING:
    # Type-check time: the mixin IS a TestCase, so assertion methods and
    # skipTest resolve and the MRO is consistent.
    _Base = unittest.TestCase
else:
    # Runtime: a plain object, so discovery can never collect the mixin (or
    # duplicate it through the importing task modules).
    _Base = object


class StaticPair(TypedDict):
    name: str
    deny: str
    allow: str
    deny_reason: NotRequired[str]


class DynamicPair(TypedDict):
    name: str
    allow: str
    allow_t: str
    deny: str
    deny_t: str
    deny_reason: NotRequired[str]
    allow_fetch_none: NotRequired[bool]


class _Guarded(_Base):
    """Mixin: a plain object at runtime (never collected on its own), a
    TestCase to the type checker (so asserts and skipTest resolve)."""

    FIXTURES: Any = None

    def setUp(self) -> None:
        if not getattr(self.FIXTURES, "TASK", ""):
            self.skipTest("fixtures missing TASK")
        if str(self.FIXTURES.TASK).startswith("REPLACE"):
            self.skipTest("template fixtures not filled")


def decide_retry(r: Any, url: str, tries: int = 3) -> dict[str, Any]:
    """Absorb host-network transients (this machine's SSL-EOF class) for LIVE
    assertions: retried only while the decision reads 'resolution failed';
    a decision carrying a policy reason (post-cutoff / forbidden / ...) is
    returned immediately, so deny-side reason assertions stay meaningful."""
    d: dict[str, Any] = {}
    for _ in range(tries):
        d = r.decide(url)
        if "resolution failed" not in str(d.get("reason", "")):
            return d
    return d


class StaticPairSuite(_Guarded):
    def test_static_pairs_offline(self) -> None:
        # designation alone decides: the forbidden clause fires before
        # resolution, so no network is needed for either side.
        _, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        fm = gw_policy.ForbiddenMatcher(overlay["forbidden_sources"])
        for pair in self.FIXTURES.STATIC_PAIRS:
            self.assertIsNotNone(fm.match(pair["deny"]), pair["name"])
            self.assertIsNone(fm.match(pair["allow"]), pair["name"])

    @unittest.skipUnless(LIVE, "set GATEWAY_LIVE=1")
    def test_static_pairs_live(self) -> None:
        r = gw_policy.Registry.from_task(
            self.FIXTURES.TASK, token=os.environ.get("GITHUB_TOKEN") or None
        )
        for pair in self.FIXTURES.STATIC_PAIRS:
            d = decide_retry(r, pair["deny"])
            self.assertFalse(d["allow"], (pair["name"], "deny side allowed", d))
            self.assertIn(pair.get("deny_reason", "forbidden"), d["reason"], pair["name"])
            a = decide_retry(r, pair["allow"])
            self.assertTrue(a["allow"], (pair["name"], "allow side denied", a))


class DynamicPairSuite(_Guarded):
    def test_dynamic_pairs_offline(self) -> None:
        # the fixture dates must sit on opposite sides of this task's cutoff
        for pair in self.FIXTURES.DYNAMIC_PAIRS:
            self.assertTrue(
                rulelib.allowed_by_date(pair["allow_t"], self.FIXTURES.CUTOFF),
                (pair["name"], "allow_t fails the cutoff"),
            )
            self.assertFalse(
                rulelib.allowed_by_date(pair["deny_t"], self.FIXTURES.CUTOFF),
                (pair["name"], "deny_t passes the cutoff"),
            )

    @unittest.skipUnless(LIVE, "set GATEWAY_LIVE=1")
    def test_dynamic_pairs_live(self) -> None:
        r = gw_policy.Registry.from_task(
            self.FIXTURES.TASK, token=os.environ.get("GITHUB_TOKEN") or None
        )
        for pair in self.FIXTURES.DYNAMIC_PAIRS:
            a = decide_retry(r, pair["allow"])
            self.assertTrue(a["allow"], (pair["name"], "allow side denied", a))
            if pair.get("allow_t"):
                self.assertEqual(a["t_verified"][:10], pair["allow_t"], pair["name"])
            if pair.get("allow_fetch_none"):
                self.assertIsNone(a["fetch"], pair["name"])
            d = decide_retry(r, pair["deny"])
            self.assertFalse(d["allow"], (pair["name"], "deny side allowed", d))
            self.assertIn(pair.get("deny_reason", "post-cutoff"), d["reason"], pair["name"])


class TaskConfigSuite(_Guarded):
    def test_cutoff_value(self) -> None:
        _, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        self.assertEqual(overlay["temporal_policy"]["cutoff"], self.FIXTURES.CUTOFF)

    def test_docs_present(self) -> None:
        base, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        composed = set(rulelib.compose(base, overlay))
        missing = sorted(set(self.FIXTURES.DOC_SITES) - composed)
        self.assertFalse(missing, missing)

    def test_catalog_and_surfaces(self) -> None:
        base, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        catalog = set((base.get("gateway") or {}).get("adapters") or [])
        kinds = {s.get("kind") for s in (overlay.get("gateway") or {}).get("surfaces", [])}
        self.assertTrue(set(self.FIXTURES.SURFACE_KINDS) <= catalog, catalog)
        self.assertTrue(set(self.FIXTURES.SURFACE_KINDS) <= kinds, kinds)

    def test_answer_hosts_never_allowlisted(self) -> None:
        base, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        composed = set(rulelib.compose(base, overlay))
        hit = sorted(composed & set(self.FIXTURES.ANSWER_HOSTS))
        self.assertFalse(hit, hit)

    def test_gateway_surfaces_not_directly_allowlisted(self) -> None:
        base, overlay = rulelib.load_layers(self.FIXTURES.TASK)
        composed = set(rulelib.compose(base, overlay))
        for s in (overlay.get("gateway") or {}).get("surfaces", []):
            for h in s.get("hosts", []):
                self.assertNotIn(h, composed, h)

    def test_render_matches_active_task_copy(self) -> None:
        r = subprocess.run(
            [sys.executable, str(EGRESS / "render.py"), "--task", self.FIXTURES.TASK],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(LIVE, "set GATEWAY_LIVE=1")
    def test_fetch_roundtrip(self) -> None:
        spec = getattr(self.FIXTURES, "FETCH_ROUNDTRIP", None)
        if not spec:
            self.skipTest("no FETCH_ROUNDTRIP fixture")
        r = gw_policy.Registry.from_task(
            self.FIXTURES.TASK, token=os.environ.get("GITHUB_TOKEN") or None
        )
        d = decide_retry(r, spec["url"])
        self.assertTrue(d["allow"], d)
        self.assertGreater(len(r.fetch(d)), spec.get("min_bytes", 1))

    @unittest.skipUnless(CONTAINER, "set POLICY_TEST_CONTAINER=<running env-main container>")
    def test_container_posture(self) -> None:
        bad: dict[str, str] = {}
        for url in self.FIXTURES.CONTAINER_DENY_URLS:
            res = common.probe(CONTAINER, url)
            if res.startswith(("OK", "HTTP")):
                bad[url] = res
        self.assertFalse(bad, f"must be cut in-container: {bad}")
        bad = {}
        for url in self.FIXTURES.CONTAINER_ALLOW_URLS:
            res = common.probe(CONTAINER, url)
            if not res.startswith("OK"):
                bad[url] = res
        self.assertFalse(bad, f"must reach in-container: {bad}")
