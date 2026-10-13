import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mdtoc.toc import github_slug, render_toc, scan_headings, slugify_all


class SlugTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(github_slug("Hello World"), "hello-world")

    def test_punctuation_dropped_hyphen_kept(self):
        self.assertEqual(github_slug("What's new? (v2.0) - API!"), "whats-new-v20---api")

    def test_underscore_kept(self):
        self.assertEqual(github_slug("snake_case name"), "snake_case-name")

    def test_unicode_letters_kept_and_lowercased(self):
        self.assertEqual(github_slug("Ünïcode Café 日本語"), "ünïcode-café-日本語")

    def test_duplicates_get_suffixes_in_order(self):
        self.assertEqual(slugify_all(["A", "B", "A", "A", "B"]), ["a", "b", "a-1", "a-2", "b-1"])


class ScanTests(unittest.TestCase):
    def test_levels_and_text(self):
        text = "# One\n## Two ##\n###### Six\n####### seven\nnot # heading\n#nospace\n"
        self.assertEqual(
            [(h.level, h.text) for h in scan_headings(text)],
            [(1, "One"), (2, "Two"), (6, "Six")],
        )

    def test_backtick_fence_excluded(self):
        text = "# A\n```\n# in code\n```\n## B\n"
        self.assertEqual([h.text for h in scan_headings(text)], ["A", "B"])

    def test_tilde_fence_excluded(self):
        text = "# A\n~~~python\n## in code\n~~~\n## B\n"
        self.assertEqual([h.text for h in scan_headings(text)], ["A", "B"])

    def test_other_fence_type_does_not_close(self):
        text = "```\n~~~\n# still code\n```\n# real\n"
        self.assertEqual([h.text for h in scan_headings(text)], ["real"])

    def test_unclosed_fence_swallows_rest(self):
        self.assertEqual([h.text for h in scan_headings("# A\n```\n# B\n")], ["A"])


class RenderTests(unittest.TestCase):
    def test_nested_list_with_duplicate_slugs(self):
        text = "# T\n## A\n### B\n## A\n"
        self.assertEqual(
            render_toc(text),
            "- [A](#a)\n  - [B](#b)\n- [A](#a-1)\n",
        )

    def test_duplicate_numbering_counts_excluded_levels(self):
        text = "# A\n## A\n"
        self.assertEqual(render_toc(text), "- [A](#a-1)\n")

    def test_default_depth_h2_to_h4(self):
        text = "# T\n## B\n#### D\n##### E\n"
        self.assertEqual(render_toc(text), "- [B](#b)\n    - [D](#d)\n")

    def test_max_depth(self):
        self.assertEqual(render_toc("## B\n### C\n", max_level=2), "- [B](#b)\n")


class StdoutTests(unittest.TestCase):
    def test_stdout_prints_toc_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.md"
            src = "# T\n## One\n```\n## no\n```\n## One\n"
            path.write_text(src, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "mdtoc", "--stdout", str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "- [One](#one)\n- [One](#one-1)\n")
            self.assertEqual(path.read_text(encoding="utf-8"), src)


if __name__ == "__main__":
    unittest.main()
