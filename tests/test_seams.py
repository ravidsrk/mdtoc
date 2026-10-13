import tempfile
import unittest
from pathlib import Path

from mdtoc.cli import main
from mdtoc.toc import render_toc, scan_headings, update_text

OPEN, CLOSE = "<!-- toc -->", "<!-- /toc -->"
BOM = "﻿"


class CrOnlyTests(unittest.TestCase):
    def test_insert_is_cr_only_and_idempotent(self):
        once = update_text("# T\r## A\r")
        self.assertEqual(once, f"# T\r\r{OPEN}\r- [A](#a)\r{CLOSE}\r\r## A\r")
        self.assertNotIn("\n", once)
        self.assertEqual(update_text(once), once)
        self.assertEqual(update_text(update_text(once)), once)

    def test_markers_cr_only(self):
        once = update_text(f"# T\r{OPEN}\r{CLOSE}\r## A\r")
        self.assertEqual(once, f"# T\r{OPEN}\r- [A](#a)\r{CLOSE}\r## A\r")
        self.assertEqual(update_text(once), once)

    def test_first_terminator_wins(self):
        out = update_text("# T\n## A\r\n")
        self.assertTrue(out.startswith(f"# T\n\n{OPEN}\n"))

    def test_check_exits_zero_after_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.md"
            p.write_bytes(b"# T\r## A\r")
            self.assertEqual(main([str(p)]), 0)
            first = p.read_bytes()
            self.assertEqual(main([str(p)]), 0)
            self.assertEqual(p.read_bytes(), first)
            self.assertEqual(main(["--check", str(p)]), 0)


class ExoticSeparatorTests(unittest.TestCase):
    def test_heading_with_exotic_separators_stays_one(self):
        for sep in ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", " ", " "):
            with self.subTest(sep=repr(sep)):
                text = f"# T\n## A{sep}B\n"
                self.assertEqual([h.text for h in scan_headings(text)], ["T", f"A{sep}B"])
                out = update_text(text)
                self.assertTrue(out.endswith(f"## A{sep}B\n"))
                self.assertEqual(out.count(OPEN), 1)
                self.assertEqual(update_text(out), out)

    def test_insert_never_mid_line(self):
        out = update_text("# T\x0cstill title\n## A\n")
        self.assertTrue(out.startswith(f"# T\x0cstill title\n\n{OPEN}\n"))

    def test_marker_after_exotic_separator(self):
        text = f"x\x0c\n{OPEN}\n{CLOSE}\n## A\n"
        self.assertEqual(update_text(text), f"x\x0c\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n")


class BomTests(unittest.TestCase):
    def test_bom_with_h1(self):
        out = update_text(f"{BOM}# T\n## A\n")
        self.assertEqual(out, f"{BOM}# T\n\n{OPEN}\n- [A](#a)\n{CLOSE}\n\n## A\n")
        self.assertEqual(update_text(out), out)

    def test_bom_without_h1_inserts_after_bom(self):
        out = update_text(f"{BOM}intro\n## A\n")
        self.assertEqual(out, f"{BOM}{OPEN}\n- [A](#a)\n{CLOSE}\n\nintro\n## A\n")
        self.assertEqual(out.count(BOM), 1)
        self.assertEqual(update_text(out), out)

    def test_bom_first_line_h2_in_toc(self):
        out = update_text(f"{BOM}## A\n")
        self.assertIn("- [A](#a)\n", out)
        self.assertTrue(out.startswith(BOM + OPEN))
        self.assertEqual(update_text(out), out)

    def test_bom_only_toc_region_changes(self):
        text = f"{BOM}# T\n{OPEN}\nold\n{CLOSE}\n## A\n"
        self.assertEqual(update_text(text), f"{BOM}# T\n{OPEN}\n- [A](#a)\n{CLOSE}\n## A\n")

    def test_bom_scan_and_render(self):
        self.assertEqual(scan_headings(f"{BOM}## A\n")[0].text, "A")
        self.assertEqual(render_toc(f"{BOM}## A\n"), "- [A](#a)\n")


class RelativeIndentTests(unittest.TestCase):
    def test_h4_first_at_column_zero(self):
        self.assertEqual(render_toc("#### x\n"), "- [x](#x)\n")

    def test_relative_depth_preserved(self):
        self.assertEqual(render_toc("### a\n#### b\n### c\n"), "- [a](#a)\n  - [b](#b)\n- [c](#c)\n")

    def test_base_is_shallowest_included_not_min_level(self):
        self.assertEqual(render_toc("# T\n### a\n"), "- [a](#a)\n")
