import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mdtoc.toc import Heading, github_slug, plain_text, render_toc, scan_headings, slugify_all


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

    def test_generated_suffix_checked_against_taken_slugs(self):
        self.assertEqual(slugify_all(["A", "A", "A-1", "A"]), ["a", "a-1", "a-1-1", "a-2"])

    def test_inline_markup_stripped_before_slugging(self):
        self.assertEqual(
            slugify_all(["**Bold** [l](u)", "`code` and ![img](p.png)", "*em* _it_ __st__", "snake_case_"]),
            ["bold-l", "code-and-img", "em-it-st", "snake_case_"],
        )


class RenderedTextTests(unittest.TestCase):
    def test_nested_link_resolved_innermost_first(self):
        self.assertEqual(plain_text("See [outer [inner](http://x)](http://y)"), "See outer inner")
        self.assertEqual(slugify_all(["[See [inner](http://x)](http://y)"]), ["see-inner"])

    def test_nested_image_in_link(self):
        self.assertEqual(slugify_all(["[![alt](p.png)](http://y)"]), ["alt"])

    def test_inline_html_tags_stripped(self):
        self.assertEqual(plain_text("Hello <em>World</em>"), "Hello World")
        self.assertEqual(slugify_all(["Hello <em>World</em>"]), ["hello-world"])

    def test_tag_inside_code_span_is_literal(self):
        self.assertEqual(plain_text("Use `<div>` here"), "Use <div> here")
        self.assertEqual(slugify_all(["Use `<div>` here"]), ["use-div-here"])

    def test_link_syntax_and_emphasis_inside_code_span_literal(self):
        self.assertEqual(plain_text("`[a](b)` `x*y*`"), "[a](b) x*y*")

    def test_decomposed_accent_keeps_combining_mark(self):
        self.assertEqual(github_slug("Cafe\u0301"), "cafe\u0301")
        self.assertEqual(slugify_all(["Cafe\u0301"]), ["cafe\u0301"])

    def test_precomposed_accent_unchanged(self):
        self.assertEqual(github_slug("Caf\u00e9"), "caf\u00e9")
        self.assertEqual(slugify_all(["Caf\u00e9"]), ["caf\u00e9"])

    def test_url_autolink_is_text_not_tag(self):
        self.assertEqual(plain_text("<http://example.com>"), "http://example.com")
        self.assertEqual(slugify_all(["<http://example.com>"]), ["httpexamplecom"])
        self.assertEqual(plain_text("<https://example.com/a?b=1>"), "https://example.com/a?b=1")
        self.assertEqual(plain_text("<mailto:a@b.c>"), "mailto:a@b.c")

    def test_autolink_mixed_with_text_and_tags(self):
        self.assertEqual(plain_text("See <http://x.io> and <em>more</em>"), "See http://x.io and more")

    def test_email_autolink(self):
        self.assertEqual(plain_text("<a@b.c>"), "a@b.c")
        self.assertEqual(slugify_all(["<a@b.c>"]), ["abc"])

    def test_div_still_stripped_and_code_span_literal(self):
        self.assertEqual(plain_text("<div>x</div>"), "x")
        self.assertEqual(plain_text("`<span>` <http://x.io>"), "<span> http://x.io")

    def test_autolink_heading_stays_in_toc(self):
        self.assertEqual(
            render_toc("## <http://example.com>\n"),
            "- [http://example.com](#httpexamplecom)\n",
        )

    def test_slug_keep_set(self):
        self.assertEqual(github_slug("a\u2460 b\u00b2 c\u2014d $e +f"), "a\u2460-b\u00b2-cd-e-f")


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

    def test_fence_on_list_item_line_excluded(self):
        self.assertEqual(scan_headings("- ```\n  # x\n  ```\n# y\n"), [Heading(1, "y")])

    def test_fence_on_numbered_and_nested_list_item_line_excluded(self):
        self.assertEqual(scan_headings("1. ~~~\n   # x\n   ~~~\n"), [])
        self.assertEqual(scan_headings("- - ```\n  # x\n"), [])

    def test_fence_on_own_line_inside_list_excluded(self):
        self.assertEqual(scan_headings("- item\n  ```\n  # x\n  ```\n"), [])


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

    def test_duplicate_suffix_counts_depth_filtered_headings(self):
        self.assertEqual(
            render_toc("## A\n### A\n## A\n", max_level=2),
            "- [A](#a)\n- [A](#a-2)\n",
        )

    def test_default_depth_h2_to_h4(self):
        text = "# T\n## B\n#### D\n##### E\n"
        self.assertEqual(render_toc(text), "- [B](#b)\n    - [D](#d)\n")

    def test_max_depth(self):
        self.assertEqual(render_toc("## B\n### C\n", max_level=2), "- [B](#b)\n")

    def test_markup_heading_label_and_slug_share_rendered_text(self):
        self.assertEqual(render_toc("## **Bold** [l](u)\n"), "- [Bold l](#bold-l)\n")

    def test_label_nested_link_and_html(self):
        self.assertEqual(
            render_toc("## [See [inner](http://x)](http://y)\n## Hello <em>World</em>\n"),
            "- [See inner](#see-inner)\n- [Hello World](#hello-world)\n",
        )

    def test_label_keeps_tag_in_code_span(self):
        self.assertEqual(render_toc("## Use `<div>` here\n"), "- [Use <div> here](#use-div-here)\n")

    def test_heading_with_empty_rendered_text_omitted(self):
        self.assertEqual(render_toc("## <br>\n## ![](p.png)\n## x\n"), "- [x](#x)\n")

    def test_empty_heading_not_rendered_but_consumes_slot(self):
        self.assertEqual(render_toc("## \n## b\n"), "- [b](#b)\n")
        self.assertEqual(render_toc("## \n## \n## x\n"), "- [x](#x)\n")


class StdoutTests(unittest.TestCase):
    def test_stdout_prints_updated_document_and_does_not_write(self):
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
            self.assertEqual(
                result.stdout,
                "# T\n\n<!-- toc -->\n- [One](#one)\n- [One](#one-1)\n<!-- /toc -->\n\n"
                "## One\n```\n## no\n```\n## One\n",
            )
            self.assertEqual(path.read_text(encoding="utf-8"), src)

    def test_max_depth_zero_is_argument_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "mdtoc", "--stdout", "--max-depth", "0", "x.md"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("max-depth", result.stderr)


if __name__ == "__main__":
    unittest.main()
