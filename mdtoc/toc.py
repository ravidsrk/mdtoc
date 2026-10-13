import re
import unicodedata
from typing import NamedTuple

DEFAULT_MIN_LEVEL = 2
DEFAULT_MAX_LEVEL = 4
OPEN_MARKER = "<!-- toc -->"
CLOSE_MARKER = "<!-- /toc -->"

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_LIST_FENCE = re.compile(r"^ {0,3}(?:(?:[-+*]|\d{1,9}[.)])[ \t]+)+(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_IMAGE_OR_LINK = re.compile(r"!?\[([^\[\]]*)\]\([^)]*\)")
_AUTOLINK = re.compile(
    r"<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*|[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+)>"
)
_HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->")
_SENTINEL = re.compile("\ue000(\\d+)\ue001")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_STAR_EMPHASIS = re.compile(r"\*+")
_UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(_{1,3})(?=\S)(.+?)(?<=\S)\1(?!\w)")


class Heading(NamedTuple):
    level: int
    text: str


def _outside_fences(text):
    """Yield (line_index, line) for lines that are not fenced code or fence delimiters."""
    fence = None
    for index, line in enumerate(text.splitlines()):
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
        yield index, line


def _scan(text):
    """Yield (line_index, Heading) for ATX headings, skipping fenced code blocks."""
    for index, line in _outside_fences(text):
        h = _HEADING.match(line)
        if h:
            yield index, Heading(len(h.group(1)), (h.group(2) or "").strip())


def scan_headings(text):
    """Return ATX headings in document order, skipping fenced code blocks."""
    return [h for _, h in _scan(text)]


def plain_text(text):
    """Approximate the rendered text of inline markdown.

    Code span contents are literal: they are set aside while the rest is rendered.
    """
    spans = []

    def stash(m):
        spans.append(m.group(2))
        return f"\ue000{len(spans) - 1}\ue001"

    text = _CODE_SPAN.sub(stash, text)
    previous = None
    while previous != text:
        previous = text
        text = _IMAGE_OR_LINK.sub(lambda m: m.group(1), text)
    text = _AUTOLINK.sub(lambda m: m.group(1), text)
    text = _HTML_TAG.sub("", text)
    text = _STAR_EMPHASIS.sub("", text)
    text = _UNDERSCORE_EMPHASIS.sub(lambda m: m.group(2), text)
    return _SENTINEL.sub(lambda m: spans[int(m.group(1))], text).strip()


def github_slug(text):
    """Lowercase, keep Unicode L*/M*/N* plus _ and -, turn spaces into hyphens."""
    return "".join(
        "-" if c == " " else c
        for c in text.lower()
        if c in " _-" or unicodedata.category(c)[0] in "LMN"
    )


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
    labels = [plain_text(h.text) for h in headings]
    slugs = slugify_all(h.text for h in headings)
    return "".join(
        f"{'  ' * (h.level - min_level)}- [{label}](#{slug})\n"
        for h, label, slug in zip(headings, labels, slugs)
        if label and min_level <= h.level <= max_level
    )


def _marker_region(text):
    """Return (start, end) of the one marker pair outside fences, or None if there is none.

    Raises ValueError for any other marker state outside fences.
    """
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    hits = []
    for index, line in _outside_fences(text):
        for marker in (OPEN_MARKER, CLOSE_MARKER):
            at = line.find(marker)
            while at != -1:
                hits.append((starts[index] + at, marker))
                at = line.find(marker, at + len(marker))
    hits.sort()
    if not hits:
        return None
    if [m for _, m in hits] != [OPEN_MARKER, CLOSE_MARKER]:
        raise ValueError(f"expected exactly one {OPEN_MARKER} / {CLOSE_MARKER} marker pair")
    return hits[0][0], hits[1][0] + len(CLOSE_MARKER)


def update_text(text, min_level=DEFAULT_MIN_LEVEL, max_level=DEFAULT_MAX_LEVEL):
    """Return text with its TOC block inserted or refreshed; all else is untouched.

    Markers inside fenced code blocks are ignored. Raises ValueError unless there are
    no markers or exactly one open/close pair outside fences.
    """
    eol = "\r\n" if "\r\n" in text else "\n"
    toc = render_toc(text, min_level, max_level).replace("\n", eol)
    inner = eol + toc
    region = _marker_region(text)
    if region:
        start, end = region
        return text[:start] + OPEN_MARKER + inner + CLOSE_MARKER + text[end:]
    block = OPEN_MARKER + inner + CLOSE_MARKER + eol
    h1 = next((i for i, h in _scan(text) if h.level == 1), None)
    if h1 is None:
        head, rest = "", text
    else:
        lines = text.splitlines(keepends=True)
        head, rest = "".join(lines[: h1 + 1]), "".join(lines[h1 + 1 :])
        if not head.endswith(("\n", "\r")):
            head += eol
        head += eol
    if rest and not rest.startswith(("\n", "\r")):
        block += eol
    elif h1 is None and rest:
        block += eol
    return head + block + rest
