"""CLI must load its own rules/allowlist while scanning paths relative to the caller."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"

class ConfigurationLocationTests(unittest.TestCase):
    def invoke(self, allowlisted):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backend = root / "backend"
            backend.mkdir()
            for filename in ("cli.py", "scanner.py"):
                shutil.copyfile(BACKEND / filename, backend / filename)
            (backend / "rules.yml").write_text(
                "- id: PROJECT_SENTINEL\n  pattern: 'DEMO_SECRET_[0-9]{6}'\n  severity: High\n",
                encoding="utf-8")
            (backend / "allowlist.yml").write_text(
                "patterns: ['DEMO_SECRET_123456']\n" if allowlisted else "patterns: []\n",
                encoding="utf-8")
            (root / "sample.txt").write_text("DEMO_SECRET_123456\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(backend / "cli.py"), "--entropy-threshold", "99", "--files", "sample.txt"],
                cwd=root, capture_output=True, text=True, check=False)

    def test_project_rule_loaded_from_root(self):
        result = self.invoke(False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PROJECT_SENTINEL", result.stderr)

    def test_project_allowlist_loaded_from_root(self):
        result = self.invoke(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

if __name__ == "__main__":
    unittest.main()
