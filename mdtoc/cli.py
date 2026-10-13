import argparse
import sys
from pathlib import Path

from mdtoc import __version__


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
    args = build_parser().parse_args(argv)
    status = 0
    for name in args.files:
        try:
            Path(name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"mdtoc: {name}: {exc}", file=sys.stderr)
            status = 2
    return status
