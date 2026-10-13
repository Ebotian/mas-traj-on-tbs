#!/usr/bin/env python3
"""TASK-INDEPENDENT (static): base-layer rules, pure-rule semantics, and the
generic contract every per-task overlay must satisfy. No container needed.

Run (whole suite): cd /home/ebt/harbor-runs && python3 -m unittest discover -s egress/tests -v
"""
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import rulelib  # noqa: E402


class BaseLayerRules(unittest.TestCase):
    def test_base_required_hosts_reachable(self) -> None:
        base, overlay = rulelib.load_layers(common.ACTIVE_TASK)
        composed = set(rulelib.compose(base, overlay))
        missing = sorted(common.BASE_REQUIRED - composed)
        self.assertFalse(missing, f"base hosts missing from compose: {missing}")

    def test_compose_dedupes_preserving_order(self) -> None:
        base = {"hosts": ["a.com", "b.com"]}
        overlay = {"restricted_hosts": ["b.com", "c.com"]}
        self.assertEqual(rulelib.compose(base, overlay), ["a.com", "b.com", "c.com"])

    def test_allowed_by_date_strict_fail_closed(self) -> None:
        cut = "2022-01-15T00:00:00Z"
        self.assertTrue(rulelib.allowed_by_date("2022-01-14T23:59:59Z", cut))
        self.assertFalse(rulelib.allowed_by_date("2022-01-15T00:00:00Z", cut))  # same day
        self.assertFalse(rulelib.allowed_by_date("2022-01-16T00:00:00Z", cut))
        self.assertFalse(rulelib.allowed_by_date(None, cut))  # unknown
        # a date-only value is taken as UTC midnight (still strictly-before)
        self.assertTrue(rulelib.allowed_by_date("2022-01-14", cut))
        self.assertFalse(rulelib.allowed_by_date("2022-01-15", cut))


class EveryOverlayContract(unittest.TestCase):
    """Parametric over policies/*.yml: the contract each overlay must satisfy."""

    def test_task_id_matches_filename(self) -> None:
        for stem, ov in common.overlays():
            self.assertEqual(ov.get("task_id"), stem, f"{stem}: task_id mismatch")

    def test_fail_closed_defaults(self) -> None:
        for stem, ov in common.overlays():
            self.assertEqual(ov.get("unknown_publication_date"), "deny", stem)
            self.assertEqual(ov.get("unverified_content_revision"), "deny", stem)

    def test_cutoff_iso_parses(self) -> None:
        for stem, ov in common.overlays():
            cutoff = str(((ov.get("temporal_policy") or {}).get("cutoff", "")))
            datetime.datetime.fromisoformat(cutoff.replace("Z", "+00:00"))

    def test_forbidden_sources_nonempty(self) -> None:
        for stem, ov in common.overlays():
            self.assertTrue(ov.get("forbidden_sources"), stem)

    def test_engines_blacklist_disjoint(self) -> None:
        for stem, ov in common.overlays():
            base, _ = rulelib.load_layers(stem)
            composed = set(rulelib.compose(base, ov))
            hit = sorted(composed & common.ENGINES)
            self.assertFalse(hit, f"{stem}: engines in allowlist: {hit}")


if __name__ == "__main__":
    unittest.main()
