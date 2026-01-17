from __future__ import annotations

import argparse
import sys

from . import __version__
from .converter import convert


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Convert a Zim notebook (source files) into Obsidian Markdown files.",
    )

    ap.add_argument(
        "src_dir",
        help="Zim notebook root directory (contains .txt pages)",
    )
    ap.add_argument(
        "output_dir",
        help="Destination directory (Obsidian vault folder)",
    )

    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the destination",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and plan output files but do not write anything",
    )
    ap.add_argument(
        "--no-frontmatter",
        action="store_true",
        help="Do not write YAML front matter",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = convert(
            args.src_dir,
            args.output_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            no_frontmatter=args.no_frontmatter,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            f"DRY RUN: would convert {result.pages_converted} pages and copy {result.attachments_copied} files into: {args.output_dir}"
        )
        if result.planned:
            print("Planned outputs:")
            for p in result.planned[:20]:
                print(" - " + p)
            if len(result.planned) > 20:
                print(f" ... ({len(result.planned) - 20} more)")
    else:
        print(
            f"Converted {result.pages_converted} pages and copied {result.attachments_copied} files into: {args.output_dir}"
        )

    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        for msg in result.warnings[:10]:
            print(" - " + msg)

    return 0
