# Zim → Obsidian Migrator

[![Tests](https://github.com/aplgr/zim-to-obsidian/actions/workflows/tests.yml/badge.svg)](https://github.com/aplgr/zim-to-obsidian/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](../../pulls)

Convert **Zim** notebook **source files** (`.txt` with Zim headers) into **Obsidian-ready Markdown** (one page per `.md` file) while copying attachments.

- One page per `.md` file (same folder structure as the Zim notebook)
- Copies non-page files (attachments, images, PDFs, etc.)
- Optional YAML front matter (default) or plain Markdown (`--no-frontmatter`)
- Best-effort conversion for common Zim wiki markup (headings, lists, checkboxes, links, images)

## Requirements

- Python 3.9+

## Install

### Recommended: pipx (isolated CLI install)

Install directly from GitHub:

```bash
pipx install git+https://github.com/aplgr/zim-to-obsidian.git
```

### Alternative: pip

```bash
pip install .
```

This installs a CLI command: `zim2obsidian`.

### No install (run from source)

```bash
python3 scripts/zim2obsidian.py --help
# or
PYTHONPATH=src python3 -m zim_to_obsidian --help
```

## Quickstart

Convert a Zim notebook into an Obsidian vault:

```bash
zim2obsidian ~/Notebooks/Notes ~/Notebooks/Private
```

Dry-run (show what would be created, but write nothing):

```bash
zim2obsidian ~/Notebooks/Notes ~/Notebooks/Private --dry-run
```

Overwrite existing files in the destination:

```bash
zim2obsidian ~/Notebooks/Notes ~/Notebooks/Private --overwrite
```

Write plain Markdown without YAML front matter:

```bash
zim2obsidian ~/Notebooks/Notes ~/Notebooks/Private --no-frontmatter
```

## What gets converted

### Pages

Zim pages are `.txt` files that start with Zim headers like:

```
Content-Type: text/x-zim-wiki
Wiki-Format: zim 0.4
Creation-Date: 2012-10-05T19:09:32+02:00

...page body...
```

Those pages are converted into `.md` files with the same relative path.

### Attachments

Everything that is **not** a Zim page file is copied as-is to the destination vault.

This usually includes images and other files stored in subfolders underneath a page.

## Conversion rules (best effort)

- Headings: `====== H1 ======` → `# H1`
- Bullet lists: `* item` → `- item`
- Checkboxes: `[ ]`, `[*]`, `[x]`, `[>]`, `[<]` → Markdown tasks (+ comment for non-standard states)
- Images: `{{./image.png?width=320}}` → `![[./PageName/image.png|320]]`
- Links: `[[Page]]`, `[[:Root]]`, `[[+Subpage]]`, `[[Page|Alias]]` → Obsidian wikilinks (best-effort resolution)
- Inline markup:
  - `//italic//` → `*italic*`
  - `__underline__` → `<u>underline</u>`
  - `''verbatim''` → `` `verbatim` ``

## Limitations

- This focuses on common built-in Zim markup. Plugin-specific syntax may remain unchanged.
- Link resolution is best-effort. If you have multiple pages with the same name in different folders, Obsidian may resolve links differently than Zim.
- Underlines are rendered using HTML (`<u>...</u>`) because Markdown has no standard underline.

## Contributing

PRs and sanitized format samples are welcome.

If your notebook contains markup that is not converted correctly, open an issue with:
- your Zim version
- a **sanitized** input snippet
- the expected output

## Development

Run tests:

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
