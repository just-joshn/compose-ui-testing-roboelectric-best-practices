#!/usr/bin/env python3

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME = "compose-ui-testing-robolectric-best-practices"


class SkillCheckTest(unittest.TestCase):
    def test_rejects_packaging_defects(self):
        mutations = {
            "wrong name": ("name: " + NAME, "name: wrong-name"),
            "missing reference": ("references/setup.md", "references/missing.md"),
            "install escape": ("references/setup.md", "../outside.md"),
            "disabled activation": ("license: MIT", "license: MIT\ndisable-model-invocation: true"),
        }
        for label, (before, after) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                skill = Path(temporary) / NAME
                shutil.copytree(ROOT / NAME, skill)
                entry = skill / "SKILL.md"
                original = entry.read_text()
                self.assertIn(before, original)
                entry.write_text(original.replace(before, after))
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/check_skill.py"), str(skill)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertNotEqual(result.returncode, 0, label)
                self.assertIn("AssertionError", result.stderr)


if __name__ == "__main__":
    unittest.main()
