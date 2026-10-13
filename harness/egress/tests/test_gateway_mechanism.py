#!/usr/bin/env python3
"""TASK-INDEPENDENT gateway mechanism tests (positive and negative).

Run:  cd /home/ebt/harbor-runs && python3 -m unittest discover -s egress/tests -v
"""
import pathlib
import sys
import unittest

TESTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent))
sys.path.insert(0, str(TESTS.parent / "gateway"))
import policy as gw_policy  # noqa: E402
from fakes import CUT, POST, PRE, FakeGitHub, FakeNature, fake_registry  # noqa: E402


class Classification(unittest.TestCase):
    def setUp(self) -> None:
        self.g = FakeGitHub({})
        self.n = FakeNature(PRE)

    def test_github_forms_parse(self) -> None:
        cases = {
            "https://github.com/o/r": ("repo", None),
            "https://github.com/o/r/commit/abc": ("commit", "abc"),
            "https://github.com/o/r/releases/tag/v1": ("release", "v1"),
            "https://github.com/o/r/archive/v1.tar.gz": ("archive", "v1"),
            "https://raw.githubusercontent.com/o/r/sha/README.md": ("raw", "sha"),
            "https://codeload.github.com/o/r/tar.gz/sha": ("archive", "sha"),
        }
        for url, (form, ref) in cases.items():
            p = self.g.parse(url)
            self.assertIsNotNone(p, url)
            assert p is not None
            self.assertEqual(p["form"], form, url)
            if ref is not None:
                self.assertIn(ref, p.values(), url)

    def test_undeclared_forms_deny(self) -> None:
        for url in [
            "https://github.com/o/r/issues/1",
            "https://github.com/o/r/tree/main",
            "https://api.github.com/repos/o/r",
            "http://github.com/o/r",
            "https://gitlab.com/o/r",
            "https://github.com/o/r?tab=readme",
        ]:
            self.assertIsNone(self.g.parse(url), url)

    def test_nature_forms_parse(self) -> None:
        p = self.n.parse("https://www.nature.com/articles/s41586-020-2649-2")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["form"], "article")
        self.assertFalse(p["pdf"])
        p = self.n.parse("https://www.nature.com/articles/s41586-020-2649-2.pdf")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertTrue(p["pdf"])
        for url in [
            "https://www.nature.com/nature/articles/x",   # wrong shape
            "https://www.nature.com/articles/",           # empty id
            "https://www.nature.com/articles/x?q=1",      # query rejected
            "http://www.nature.com/articles/x",           # https only
        ]:
            self.assertIsNone(self.n.parse(url), url)


class Guards(unittest.TestCase):
    def test_repo_needs_created_and_pushed_before_cutoff(self) -> None:
        r = fake_registry([FakeGitHub({"/repos/o/r": {"created_at": "2020-01-01T00:00:00Z", "pushed_at": PRE}})])
        self.assertTrue(r.decide("https://github.com/o/r")["allow"])
        r = fake_registry([FakeGitHub({"/repos/o/r": {"created_at": "2020-01-01T00:00:00Z", "pushed_at": POST}})])
        self.assertFalse(r.decide("https://github.com/o/r")["allow"])

    def test_same_day_fails_closed(self) -> None:
        r = fake_registry([FakeGitHub({"/repos/o/r/commits/v1": {"sha": "a" * 40, "commit": {"committer": {"date": CUT}}}})])
        self.assertFalse(r.decide("https://github.com/o/r/commit/v1")["allow"])

    def test_unknown_date_fails_closed(self) -> None:
        r = fake_registry([FakeNature(None)])
        d = r.decide("https://www.nature.com/articles/x")
        self.assertFalse(d["allow"])
        self.assertIn("resolution failed", d["reason"])

    def test_resolution_failure_denies(self) -> None:
        d = fake_registry([FakeGitHub({})]).decide("https://github.com/o/r/commit/v1")
        self.assertFalse(d["allow"])
        self.assertIn("resolution failed", d["reason"])

    def test_undeclared_host_denies(self) -> None:
        d = fake_registry([]).decide("https://example.com/x")
        self.assertFalse(d["allow"])

    def test_fetch_url_constructed_with_resolved_sha(self) -> None:
        sha = "b" * 40
        r = fake_registry([FakeGitHub({"/repos/o/r/commits/main": {"sha": sha, "commit": {"committer": {"date": PRE}}}})])
        d = r.decide("https://raw.githubusercontent.com/o/r/main/path/to/f.py")
        self.assertTrue(d["allow"], d)
        self.assertEqual(d["fetch"]["url"], f"https://raw.githubusercontent.com/o/r/{sha}/path/to/f.py")

    def test_release_requires_both_dates(self) -> None:
        routes = {
            "/repos/o/r/git/ref/tags/v1": {"object": {"type": "commit", "sha": "c" * 40}},
            "/repos/o/r/commits/" + "c" * 40: {"sha": "c" * 40, "commit": {"committer": {"date": PRE}}},
            "/repos/o/r/releases/tags/v1": {"published_at": POST},
        }
        self.assertFalse(fake_registry([FakeGitHub(routes)]).decide("https://github.com/o/r/releases/tag/v1")["allow"])

    def test_pre_cutoff_article_allows(self) -> None:
        r = fake_registry([FakeNature(PRE)])
        d = r.decide("https://www.nature.com/articles/s41586-020-2649-2")
        self.assertTrue(d["allow"], d)
        self.assertEqual(d["t_verified"], PRE)


class ForbiddenMatcherUnit(unittest.TestCase):
    def test_extracted_patterns_match(self) -> None:
        fm = gw_policy.ForbiddenMatcher([
            "doi:10.1038/s43856-022-00197-2",
            "raw.githubusercontent.com/harbor-framework/terminal-bench-science",
            "hub.harborframework.com",
            "biorxiv content of 2022.01.15.476480 (entry, PDF, supplements)",
            "task_specific_solution_repositories  # REVIEW: lab GitHub/site",
        ])
        self.assertTrue(fm.match("https://www.nature.com/articles/s43856-022-00197-2"))
        self.assertTrue(fm.match("https://doi.org/10.1038/s43856-022-00197-2"))
        self.assertTrue(fm.match("https://raw.githubusercontent.com/harbor-framework/terminal-bench-science/main/k.csv"))
        self.assertTrue(fm.match("https://github.com/harbor-framework/terminal-bench-science"))
        self.assertTrue(fm.match("https://hub.harborframework.com/x"))
        self.assertTrue(fm.match("https://www.biorxiv.org/content/10.1101/2022.01.15.476480v1"))
        self.assertIsNone(fm.match("https://github.com/scikit-image/scikit-image"))
        self.assertIsNone(fm.match("https://www.nature.com/articles/s41586-020-2649-2"))

    def test_forbidden_wins_over_passing_dates(self) -> None:
        """The independence rule: a designated answer link denies even when the
        dates would pass (fake routes carry PRE dates)."""
        fm = gw_policy.ForbiddenMatcher(["raw.githubusercontent.com/harbor-framework/terminal-bench-science"])
        sha = "d" * 40
        r = fake_registry(
            [FakeGitHub({"/repos/harbor-framework/terminal-bench-science/commits/main":
                         {"sha": sha, "commit": {"committer": {"date": PRE}}}})],
        )
        r.forbidden = fm
        d = r.decide("https://raw.githubusercontent.com/harbor-framework/terminal-bench-science/main/file")
        self.assertFalse(d["allow"])
        self.assertIn("forbidden", d["reason"])


class DirectAllowlistHint(unittest.TestCase):
    """v3 wording: a host on the DIRECT allowlist gets a fetch-directly hint on
    the not-a-gateway-surface deny, so agents do not read it as blocked."""

    def test_hint_on_direct_allowlist_host(self) -> None:
        r = fake_registry([FakeGitHub({})], direct_hosts={"docs.scipy.org"})
        d = r.decide("https://docs.scipy.org/doc/scipy/index.html")
        self.assertFalse(d["allow"])
        self.assertIn("host is not a declared gateway surface", d["reason"])
        self.assertIn("direct allowlist", d["reason"])

    def test_no_hint_on_unknown_host(self) -> None:
        r = fake_registry([FakeGitHub({})])
        d = r.decide("https://unknown.example.org/x")
        self.assertFalse(d["allow"])
        self.assertEqual(d["reason"], "host is not a declared gateway surface")

    def test_hint_only_on_the_surface_deny_branch(self) -> None:
        r = fake_registry([FakeGitHub({})], direct_hosts={"github.com"})
        d = r.decide("https://github.com/o/r/issues/1")
        self.assertFalse(d["allow"])
        self.assertEqual(d["reason"], "unparseable or undeclared URL form")
        self.assertNotIn("direct allowlist", d["reason"])


if __name__ == "__main__":
    unittest.main()
