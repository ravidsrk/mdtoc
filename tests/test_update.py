import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mdtoc.toc import update_text

OPEN, CLOSE = "<!-- toc -->", "<!-- /toc -->"


def run(*args):
    return subprocess.run([sys.executable, "-m", "mdtoc", *args], capture_output=True, text=True)


class UpdateTextTests(unittest.TestCase):
    def test_fills_empty_marker_pair(self):
        text = f"# T\n{OPEN}\n{CLOSE}\n## A\n"
        self.assertEqual(update_text(text), f"# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n")

    def test_replaces_stale_content_between_markers(self):
        text = f"# T\n{OPEN}\n- [Old](#old)\n{CLOSE}\n## A\n\ntail"
        self.assertEqual(update_text(text), f"# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n\ntail")

    def test_idempotent_with_markers(self):
        once = update_text(f"intro\n{OPEN}\n{CLOSE}\n## A\n### B\n")
        self.assertEqual(update_text(once), once)

    def test_no_markers_inserts_after_first_h1(self):
        out = update_text("# T\n\n## A\n")
        self.assertEqual(out, f"# T\n\n{OPEN}\n- [A](#a)\n{CLOSE}\n\n## A\n")

    def test_no_markers_h1_directly_followed_by_heading(self):
        out = update_text("# T\n## A\n")
        self.assertEqual(out, f"# T\n\n{OPEN}\n- [A](#a)\n{CLOSE}\n\n## A\n")

    def test_no_markers_inserts_after_first_h1_only(self):
        out = update_text("# T\n\n## A\n# U\n")
        self.assertTrue(out.startswith(f"# T\n\n{OPEN}\n"))
        self.assertEqual(out.count(OPEN), 1)

    def test_h1_in_fence_is_not_the_anchor(self):
        out = update_text("```\n# no\n```\n## A\n")
        self.assertTrue(out.startswith(f"{OPEN}\n- [A](#a)\n{CLOSE}\n\n```\n"))

    def test_no_markers_no_h1_inserts_at_top(self):
        out = update_text("intro\n\n## A\n")
        self.assertEqual(out, f"{OPEN}\n- [A](#a)\n{CLOSE}\n\nintro\n\n## A\n")

    def test_inserted_markers_make_second_run_in_place(self):
        for src in ("# T\n\n## A\n", "## A\n", "# T"):
            once = update_text(src)
            self.assertEqual(update_text(once), once)

    def test_h1_without_trailing_newline(self):
        out = update_text("# T")
        self.assertEqual(out, f"# T\n\n{OPEN}\n{CLOSE}\n")

    def test_empty_file(self):
        self.assertEqual(update_text(""), f"{OPEN}\n{CLOSE}\n")

    def test_crlf_preserved(self):
        out = update_text("# T\r\n## A\r\n")
        self.assertNotIn("\n", out.replace("\r\n", ""))
        self.assertEqual(update_text(out), out)

    def test_bytes_outside_region_preserved(self):
        pre, post = "# T\n\n  weird \t \n\n", "\n## A\n\ttrailing   \n\n\n"
        out = update_text(f"{pre}{OPEN}\nold\n{CLOSE}{post}")
        self.assertTrue(out.startswith(pre + OPEN))
        self.assertTrue(out.endswith(CLOSE + post))

    def test_no_final_newline_preserved(self):
        out = update_text(f"{OPEN}\n{CLOSE}\n## A")
        self.assertTrue(out.endswith("## A"))

    def test_toc_respects_max_level(self):
        out = update_text(f"{OPEN}\n{CLOSE}\n## A\n### B\n", max_level=2)
        self.assertIn("- [A](#a)\n", out)
        self.assertNotIn("[B]", out)

    def test_unclosed_open_marker_is_an_error(self):
        with self.assertRaises(ValueError):
            update_text(f"# T\n{OPEN}\n## A\n")


class CliFileTests(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.path = Path(self._d.name) / "a.md"

    def write(self, text):
        self.path.write_bytes(text.encode("utf-8"))

    def read(self):
        return self.path.read_bytes()

    def test_default_mode_updates_in_place(self):
        self.write(f"# T\n{OPEN}\n{CLOSE}\n## A\n")
        self.assertEqual(run(str(self.path)).returncode, 0)
        self.assertEqual(self.read(), f"# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n".encode())

    def test_twice_is_byte_identical(self):
        self.write("# T\n\n## A\n### B\n## A\n")
        run(str(self.path))
        first = self.read()
        self.assertIn(OPEN.encode(), first)
        run(str(self.path))
        self.assertEqual(self.read(), first)

    def test_crlf_file_stays_crlf(self):
        self.write("# T\r\n## A\r\n")
        run(str(self.path))
        data = self.read()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        run(str(self.path))
        self.assertEqual(self.read(), data)

    def test_up_to_date_file_not_rewritten(self):
        self.write("# T\n## A\n")
        run(str(self.path))
        before = self.path.stat().st_mtime_ns
        run(str(self.path))
        self.assertEqual(self.path.stat().st_mtime_ns, before)

    def test_check_missing_toc_exits_1_without_writing(self):
        src = "# T\n## A\n"
        self.write(src)
        self.assertEqual(run("--check", str(self.path)).returncode, 1)
        self.assertEqual(self.read(), src.encode())

    def test_check_stale_exits_1_without_writing(self):
        src = f"# T\n{OPEN}\n- [Old](#old)\n{CLOSE}\n## A\n"
        self.write(src)
        self.assertEqual(run("--check", str(self.path)).returncode, 1)
        self.assertEqual(self.read(), src.encode())

    def test_check_current_exits_0(self):
        self.write("# T\n## A\n")
        run(str(self.path))
        before = self.read()
        self.assertEqual(run("--check", str(self.path)).returncode, 0)
        self.assertEqual(self.read(), before)

    def test_check_respects_max_depth(self):
        self.write("# T\n## A\n### B\n")
        run("--max-depth", "2", str(self.path))
        self.assertEqual(run("--check", "--max-depth", "2", str(self.path)).returncode, 0)
        self.assertEqual(run("--check", str(self.path)).returncode, 1)

    def test_stdout_never_writes(self):
        src = "# T\n## A\n"
        self.write(src)
        self.assertEqual(run("--stdout", str(self.path)).returncode, 0)
        self.assertEqual(self.read(), src.encode())

    def test_stdout_on_file_with_markers_prints_full_document(self):
        src = f"intro\n{OPEN}\n- [Old](#old)\n{CLOSE}\n## A\n"
        self.write(src)
        r = run("--stdout", str(self.path))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, f"intro\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n")
        self.assertEqual(self.read(), src.encode())

    def test_check_with_stdout_is_argparse_error(self):
        self.write("# T\n## A\n")
        r = run("--check", "--stdout", str(self.path))
        self.assertEqual(r.returncode, 2)
        self.assertIn("--check", r.stderr)

    def test_lone_close_marker_exits_2_without_writing(self):
        src = f"# T\n{CLOSE}\n## A\n"
        self.write(src)
        self.assertEqual(run(str(self.path)).returncode, 2)
        self.assertEqual(self.read(), src.encode())

    def test_h1_only_with_trailing_newline(self):
        out = update_text("# T\n")
        self.assertEqual(out, f"# T\n\n{OPEN}\n{CLOSE}\n")
        self.assertEqual(update_text(out), out)

    def test_fenced_marker_example_is_untouched(self):
        fenced = f"```\n{OPEN}\n- [x](#x)\n{CLOSE}\n```\n"
        text = f"{fenced}# T\n{OPEN}\n{CLOSE}\n## A\n"
        self.assertEqual(update_text(text), f"{fenced}# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n")

    def test_only_fenced_markers_means_insert_real_pair(self):
        fenced = f"```\n{OPEN}\n{CLOSE}\n```\n"
        out = update_text(f"# T\n{fenced}## A\n")
        self.assertTrue(out.startswith(f"# T\n\n{OPEN}\n- [A](#a)\n{CLOSE}\n"))
        self.assertIn(fenced, out)

    def test_duplicate_pairs_are_an_error(self):
        text = f"# T\n{OPEN}\n{CLOSE}\n{OPEN}\nold\n{CLOSE}\n## A\n"
        with self.assertRaises(ValueError):
            update_text(text)

    def test_stray_markers_outside_fences_are_errors(self):
        pair = f"{OPEN}\n{CLOSE}\n"
        for text in (f"{pair}{CLOSE}\n", f"{CLOSE}\n{pair}", f"{pair}{OPEN}\n", f"{CLOSE}\n{OPEN}\n"):
            with self.assertRaises(ValueError, msg=text):
                update_text(text)

    def test_duplicate_pairs_exit_2_for_write_and_check(self):
        src = f"# T\n{OPEN}\n{CLOSE}\n{OPEN}\nold\n{CLOSE}\n## A\n"
        self.write(src)
        for args in ((), ("--check",)):
            self.assertEqual(run(*args, str(self.path)).returncode, 2, args)
            self.assertEqual(self.read(), src.encode())

    def test_default_depth_h2_to_h4(self):
        self.write("# T\n## B\n### C\n#### D\n##### E\n")
        run(str(self.path))
        out = self.read().decode()
        self.assertIn("[D](#d)", out)
        self.assertNotIn("[E](#e)", out.split(CLOSE)[0])
        self.assertNotIn("[T](#t)", out.split(CLOSE)[0])

    def test_max_depth_limits_levels(self):
        self.write("# T\n## B\n### C\n")
        run("--max-depth", "2", str(self.path))
        toc = self.read().decode().split(CLOSE)[0]
        self.assertIn("[B]", toc)
        self.assertNotIn("[C]", toc)

    def test_max_depth_above_default_includes_deeper(self):
        self.write("# T\n##### E\n")
        run("--max-depth", "6", str(self.path))
        self.assertIn("[E](#e)", self.read().decode())

    def test_max_depth_out_of_range_is_argparse_error(self):
        for bad in ("0", "7", "-1", "x"):
            r = run("--max-depth", bad, str(self.path))
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("max-depth", r.stderr)

    def test_max_depth_bounds_accepted(self):
        self.write("# T\n")
        for ok in ("1", "6"):
            self.assertEqual(run("--max-depth", ok, str(self.path)).returncode, 0)

    def test_unclosed_marker_exits_2_without_writing(self):
        src = f"# T\n{OPEN}\n## A\n"
        self.write(src)
        r = run(str(self.path))
        self.assertEqual(r.returncode, 2)
        self.assertIn("toc", r.stderr)
        self.assertEqual(self.read(), src.encode())

    def test_missing_file_still_exit_2(self):
        self.assertEqual(run(str(self.path)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
