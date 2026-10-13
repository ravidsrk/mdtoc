import re
from typing import NamedTuple

DEFAULT_MIN_LEVEL = 2
DEFAULT_MAX_LEVEL = 4

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_LIST_FENCE = re.compile(r"^ {0,3}(?:(?:[-+*]|\d{1,9}[.)])[ \t]+)+(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_DROP = re.compile(r"[^\w\- ]")
_IMAGE_OR_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_STAR_EMPHASIS = re.compile(r"\*+")
_UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(_{1,3})(?=\S)(.+?)(?<=\S)\1(?!\w)")


class Heading(NamedTuple):
    level: int
    text: str


def scan_headings(text):
    """Return ATX headings in document order, skipping fenced code blocks."""
    headings = []
    fence = None
    for line in text.splitlines():
        m = _FENCE.match(line) or (_LIST_FENCE.match(line) if fence is None else None)
        if fence is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                continue
        else:
            if (
                m
                and m.group(1)[0] == fence[0]
                and len(m.group(1)) >= len(fence)
                and not m.group(2).strip()
            ):
                fence = None
            continue
        h = _HEADING.match(line)
        if h:
            headings.append(Heading(len(h.group(1)), (h.group(2) or "").strip()))
    return headings


def plain_text(text):
    """Approximate the rendered text of inline markdown."""
    text = _CODE_SPAN.sub(lambda m: m.group(2), text)
    text = _IMAGE_OR_LINK.sub(lambda m: m.group(1), text)
    text = _STAR_EMPHASIS.sub("", text)
    return _UNDERSCORE_EMPHASIS.sub(lambda m: m.group(2), text)


def github_slug(text):
    return _DROP.sub("", text.lower()).replace(" ", "-")


def slugify_all(texts):
    """Slugs for texts in order; repeats get -1, -2, ... suffixes."""
    seen = {}
    slugs = []
    for t in texts:
        base = github_slug(plain_text(t))
        slug = base
        while slug in seen:
            seen[base] += 1
            slug = f"{base}-{seen[base]}"
        seen[slug] = 0
        slugs.append(slug)
    return slugs


def render_toc(text, min_level=DEFAULT_MIN_LEVEL, max_level=DEFAULT_MAX_LEVEL):
    """Nested markdown list of links; slugs are numbered across all headings."""
    headings = scan_headings(text)
    slugs = slugify_all(h.text for h in headings)
    return "".join(
        f"{'  ' * (h.level - min_level)}- [{h.text}](#{slug})\n"
        for h, slug in zip(headings, slugs)
        if h.text and min_level <= h.level <= max_level
    )
