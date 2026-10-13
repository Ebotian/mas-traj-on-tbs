#!/usr/bin/env python3
"""TASK-INDEPENDENT: the task-suite shape is isomorphic and migratable.

Every task folder must contain exactly the canonical file set, and every file
except fixtures.py must be byte-identical to task_template/. Migration to a
new task = copy the template, rename the folder, fill fixtures.py — nothing
else may differ, and that is checked here mechanically.
"""
import pathlib
import sys
import unittest

TESTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent))

CANONICAL = {
    "__init__.py",
    "fixtures.py",
    "test_static_pairs.py",
    "test_dynamic_pairs.py",
    "test_task_config.py",
}


class TaskSuiteIsomorphism(unittest.TestCase):
    def test_canonical_files_and_byte_identity(self) -> None:
        template = TESTS / "task_template"
        self.assertTrue((template / "fixtures.py").exists(), "task_template missing")
        task_dirs = sorted(
            p for p in TESTS.iterdir()
            if p.is_dir() and (p / "fixtures.py").exists() and p.name != "__pycache__"
        )
        self.assertIn(template, task_dirs, "template must itself match the canonical shape")
        for d in task_dirs:
            have = {p.name for p in d.iterdir() if p.suffix == ".py"}
            self.assertEqual(have, CANONICAL,
                             f"{d.name}: file set differs from the canonical shape")
            for name in sorted(CANONICAL - {"fixtures.py"}):
                self.assertEqual(
                    (template / name).read_bytes(), (d / name).read_bytes(),
                    f"{d.name}/{name} must be byte-identical to task_template/{name}",
                )


if __name__ == "__main__":
    unittest.main()
