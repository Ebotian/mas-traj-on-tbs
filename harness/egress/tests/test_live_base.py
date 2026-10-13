#!/usr/bin/env python3
"""TASK-INDEPENDENT (behavioural): global surfaces probed in a live container.
Engines must be cut in the engines-off regime; the base layer must be reachable.

Skipped unless POLICY_TEST_CONTAINER names a running env-main container.
"""
import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

CONTAINER: str = os.environ.get("POLICY_TEST_CONTAINER") or ""


@unittest.skipUnless(CONTAINER, "set POLICY_TEST_CONTAINER=<running env-main container>")
class LiveBaseRules(unittest.TestCase):
    def test_engines_are_cut(self) -> None:
        bad: dict[str, str] = {}
        for url in common.ENGINE_URLS:
            res = common.probe(CONTAINER, url)
            if res.startswith(("OK", "HTTP")):
                bad[url] = res
        self.assertFalse(bad, f"engines reachable: {bad}")

    def test_example_reachable(self) -> None:
        res = common.probe(CONTAINER, "https://example.com/")
        self.assertTrue(res.startswith("OK"), res)

    def test_model_endpoint_reachable(self) -> None:
        # 401 = reachable, auth required (the endpoint answering is the point)
        res = common.probe(CONTAINER, "https://api.deepseek.com/")
        self.assertTrue(res.startswith("HTTP"), res)

    def test_gateway_endpoint_reachable(self) -> None:
        # the egress gateway is live in the policy (base 172.17.0.1): a
        # gateway-condition container must reach its /healthz.
        res = common.probe(CONTAINER, "http://172.17.0.1:8788/healthz")
        self.assertTrue(res.startswith("OK"), res)

    def test_gateway_check_answers(self) -> None:
        # the /check endpoint serves decisions to the container (body-level
        # assertions live in the host-side gateway live tests).
        res = common.probe(
            CONTAINER,
            "http://172.17.0.1:8788/check?url="
            "https%3A%2F%2Fgithub.com%2Fscikit-image%2Fscikit-image%2Fcommit%2Fv0.18.3",
        )
        self.assertTrue(res.startswith("OK"), res)


if __name__ == "__main__":
    unittest.main()
