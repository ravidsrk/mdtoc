import tempfile
import unittest
from pathlib import Path

from tests.test_update import CLOSE, OPEN, run

STALE = f"# T\n{OPEN}\n- [Old](#old)\n{CLOSE}\n## A\n"
CURRENT = f"# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n"
UPDATED = CURRENT


class MultiFileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8", newline="")
        return str(path)

    def write_bytes(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return str(path)

    def test_two_good_files_both_updated(self):
        a, b = self.write("a.md", STALE), self.write("b.md", "# T\n## A\n")
        r = run(a, b)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(a).read_text(), UPDATED)
        self.assertIn(OPEN, Path(b).read_text())

    def test_good_plus_missing_still_updates_good_exit_2(self):
        a = self.write("a.md", STALE)
        missing = str(self.dir / "nope.md")
        r = run(missing, a)
        self.assertEqual(r.returncode, 2)
        self.assertIn("nope.md: no such file", r.stderr)
        self.assertEqual(Path(a).read_text(), UPDATED)
        self.assertFalse(Path(missing).exists())

    def test_good_plus_non_utf8_exit_2_names_file(self):
        a = self.write("a.md", STALE)
        bad_data = b"# T\n\xff\xfe\n"
        bad = self.write_bytes("bad.md", bad_data)
        r = run(bad, a)
        self.assertEqual(r.returncode, 2)
        self.assertIn("bad.md: not valid UTF-8", r.stderr)
        self.assertEqual(Path(bad).read_bytes(), bad_data)
        self.assertEqual(Path(a).read_text(), UPDATED)

    def test_illegal_marker_state_does_not_stop_others(self):
        a = self.write("a.md", STALE)
        bad = self.write("bad.md", f"{OPEN}\n{OPEN}\n{CLOSE}\n")
        r = run(bad, a)
        self.assertEqual(r.returncode, 2)
        self.assertIn("bad.md", r.stderr)
        self.assertEqual(Path(a).read_text(), UPDATED)

    def test_check_one_stale_one_current_exit_1(self):
        a, b = self.write("a.md", STALE), self.write("b.md", CURRENT)
        r = run("--check", a, b)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(Path(a).read_text(), STALE)

    def test_check_all_current_exit_0(self):
        a, b = self.write("a.md", CURRENT), self.write("b.md", CURRENT)
        self.assertEqual(run("--check", a, b).returncode, 0)

    def test_check_error_plus_stale_exit_2(self):
        a = self.write("a.md", STALE)
        r = run("--check", str(self.dir / "nope.md"), a)
        self.assertEqual(r.returncode, 2)
        r = run("--check", a, str(self.dir / "nope.md"))
        self.assertEqual(r.returncode, 2)

    def test_stdout_two_files_in_order_no_write(self):
        a, b = self.write("a.md", STALE), self.write("b.md", "# U\n## B\n")
        r = run("--stdout", a, b)
        self.assertEqual(r.returncode, 0, r.stderr)
        expected_b = f"# U\n\n{OPEN}\n- [B](#b)\n{CLOSE}\n\n## B\n"
        self.assertEqual(r.stdout, UPDATED + expected_b)
        self.assertEqual(Path(a).read_text(), STALE)
        self.assertEqual(Path(b).read_text(), "# U\n## B\n")

    def test_stdout_with_error_still_prints_others(self):
        a = self.write("a.md", STALE)
        r = run("--stdout", str(self.dir / "nope.md"), a)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, UPDATED)
