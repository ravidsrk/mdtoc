# mdtoc

Insert or update a table of contents in Markdown files. Python >= 3.11,
standard library only. The frozen specification lives in SPEC.md.

## Usage

```
python3 -m mdtoc [--check] [--stdout] [--max-depth N] FILE [FILE ...]
```

- `FILE ...` — one or more Markdown files.
- `--check` — exit 1 if the TOC is stale or missing; 0 if current.
- `--stdout` — print the result instead of writing the file.
- `--max-depth N` — deepest heading level to include (default: H2–H4).

Behavior beyond argument parsing is still being built.
