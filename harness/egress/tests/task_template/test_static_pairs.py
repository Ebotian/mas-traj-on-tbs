#!/usr/bin/env python3
"""Task suite — STATIC pairs (designated sources; +/- paired).

DO NOT EDIT per task: copy verbatim from task_template/. Everything
task-specific lives in fixtures.py; isomorphism is enforced by
tests/test_task_isomorphism.py.
"""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent.parent / "gateway"))
from pair_harness import StaticPairSuite  # noqa: E402

from . import fixtures  # noqa: E402


class TestStaticPairs(StaticPairSuite, unittest.TestCase):
    FIXTURES = fixtures
