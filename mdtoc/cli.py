import argparse
import sys
from pathlib import Path

from mdtoc import __version__
from mdtoc.toc import DEFAULT_MAX_LEVEL, render_toc


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mdtoc",
        description="Insert or update a table of contents in Markdown files.",
    )
    parser.add_argument("files", nargs="+", metavar="FILE", help="Markdown files")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if a TOC is stale or missing; do not write",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the result instead of writing the file",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        metavar="N",
        help="deepest heading level to include",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_depth is not None and args.max_depth < 1:
        parser.error("--max-depth must be at least 1")
    status = 0
    for name in args.files:
        try:
            text = Path(name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"mdtoc: {name}: {exc}", file=sys.stderr)
            status = 2
            continue
        if args.stdout:
            sys.stdout.write(render_toc(text, max_level=DEFAULT_MAX_LEVEL if args.max_depth is None else args.max_depth))
    return status
