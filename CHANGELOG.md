# Changelog

All notable changes to this project will be documented in this file.

The format is based on *Keep a Changelog* and the project follows a pragmatic form of semantic versioning.



## [0.1.0] - 2026-01-17

### Added
- Convert Zim notebook sources (`.txt` pages) to Obsidian-ready Markdown.
- Optional YAML front matter (default) or plain Markdown (`--no-frontmatter`).
- Copy non-page files (attachments) into the destination vault.
- Best-effort conversion for common Zim markup (headings, lists, checkboxes, links, images).
- CLI options:
  - `--overwrite` to overwrite existing destination files
  - `--dry-run` to plan outputs without writing files
  - `--no-frontmatter` to disable YAML front matter
- Anonymized example notebook and pytest-based test suite.
