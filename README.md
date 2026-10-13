# mdtoc

Insert or update a table of contents in Markdown files. Python >= 3.11,
standard library only. The frozen specification lives in SPEC.md.

## Usage

```
python3 -m mdtoc [--check] [--stdout] [--max-depth N] FILE [FILE ...]
```

- `FILE ...` — one or more Markdown files, each processed independently.
- default — update each file in place; running it again changes nothing.
- `--check` — write nothing; report files whose TOC is stale or missing on stderr.
  Cannot be combined with `--stdout`.
- `--stdout` — write nothing; print each file's full updated document to stdout,
  in argument order.
- `--max-depth N` — deepest heading level to include, 1..6 (default: H2–H4, so
  the default is the same as `--max-depth 4`).

### Multiple files and exit codes

A problem with one file never stops the others. Each error is reported on stderr
as `mdtoc: FILE: message`, and nothing is written for that file. Errors are a
missing file, a file that is not valid UTF-8, and an illegal marker state.

| Code | Meaning |
|---|---|
| 0 | every file processed; with `--check`, all TOCs current |
| 1 | `--check` found at least one stale or missing TOC, and no file errored |
| 2 | at least one file errored (takes precedence over 1) |

### Markers

The TOC lives between `<!-- toc -->` and `<!-- /toc -->`.

- With markers, only the text between them is replaced.
- Without markers, a marker pair holding the TOC is inserted after the first H1,
  or at the top of the file if there is no H1.
- A file must contain no markers or exactly one open/close pair, in that order.
  Anything else (a lone marker, a duplicate pair, close before open) is an error
  for that file.
- Fenced code blocks (``` or ~~~) are skipped: headings in them are not listed,
  and markers in them are ignored.
- Links use GitHub anchor slugs; duplicate headings get `-1`, `-2`, … suffixes.
