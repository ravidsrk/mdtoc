import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SmokeTests(unittest.TestCase):
    def test_package_imports_with_version(self):
        import mdtoc

        self.assertIsInstance(mdtoc.__version__, str)

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "mdtoc", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        for flag in ("--check", "--stdout", "--max-depth"):
            self.assertIn(flag, result.stdout)

    def test_no_files_is_usage_error(self):
        from mdtoc.cli import main

        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 2)

    def test_existing_utf8_file_exits_zero(self):
        from mdtoc.cli import main

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.md"
            path.write_text("# Title\n", encoding="utf-8")
            self.assertEqual(main([str(path)]), 0)

    def test_missing_file_exits_two(self):
        from mdtoc.cli import main

        self.assertEqual(main(["/nonexistent/none.md"]), 2)


if __name__ == "__main__":
    unittest.main()
