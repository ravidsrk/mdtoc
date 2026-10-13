import argparse
import sys
from pathlib import Path

from mdtoc import __version__
from mdtoc.toc import DEFAULT_MAX_LEVEL, render_toc, update_text


def _depth(value):
    try:
        depth = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from None
    if not 1 <= depth <= 6:
        raise argparse.ArgumentTypeError(f"must be between 1 and 6, got {depth}")
    return depth


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
        type=_depth,
        metavar="N",
        help="deepest heading level to include",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    max_level = DEFAULT_MAX_LEVEL if args.max_depth is None else args.max_depth
    status = 0
    for name in args.files:
        path = Path(name)
        try:
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
            if args.check:
                if update_text(text, max_level=max_level) != text:
                    print(f"mdtoc: {name}: table of contents is stale or missing", file=sys.stderr)
                    status = max(status, 1)
            elif args.stdout:
                sys.stdout.write(render_toc(text, max_level=max_level))
            else:
                new = update_text(text, max_level=max_level)
                if new != text:
                    with open(path, "w", encoding="utf-8", newline="") as f:
                        f.write(new)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            print(f"mdtoc: {name}: {exc}", file=sys.stderr)
            status = 2
    return status
