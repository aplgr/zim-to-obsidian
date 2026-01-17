#!/usr/bin/env python3
"""Run the converter without installation.

This wrapper makes the src-layout importable.

Usage:
  python3 scripts/zim2obsidian.py <src_dir> <output_dir> [options]
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    sys.path.insert(0, str(src))

    from zim_to_obsidian.cli import main as real_main

    return real_main()


if __name__ == "__main__":
    raise SystemExit(main())
