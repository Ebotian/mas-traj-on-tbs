#!/usr/bin/env python3
"""TASK-INDEPENDENT: type annotations are legal - mypy runs as a suite member.

Targets = the test suite plus the modules it exercises (rulelib, policy,
surfaces). Config: egress/mypy.ini. Skips if mypy is absent.
"""
import pathlib
import shutil
import subprocess
import unittest

TESTS = pathlib.Path(__file__).resolve().parent
EGRESS = TESTS.parent
MYPY = shutil.which("mypy")

TARGETS = [
    str(EGRESS / "tests"),
    str(EGRESS / "rulelib.py"),
    str(EGRESS / "gateway" / "policy.py"),
    str(EGRESS / "gateway" / "surfaces.py"),
]


@unittest.skipUnless(MYPY, "mypy not on PATH")
class TypeLegality(unittest.TestCase):
    def test_mypy_clean(self) -> None:
        r = subprocess.run(
            [str(MYPY), "--config-file", str(EGRESS / "mypy.ini"), *TARGETS],
            capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(r.returncode, 0,
                         (r.stdout or "")[-4000:] + (r.stderr or "")[-1000:])


if __name__ == "__main__":
    unittest.main()
