from __future__ import annotations

from pathlib import Path

import pytest

from zim_to_obsidian.cli import main as cli_main
from zim_to_obsidian.converter import convert


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sample_notebook_path() -> Path:
    return repo_root() / "examples" / "sample_notebook"


def test_convert_writes_pages_and_attachments(tmp_path: Path) -> None:
    out_dir = tmp_path / "vault"
    result = convert(str(sample_notebook_path()), str(out_dir), overwrite=True)

    assert result.pages_converted == 5
    assert result.attachments_copied == 4

    md_files = list(out_dir.rglob("*.md"))
    assert len(md_files) == 5

    # Ensure attachments were copied
    assert (out_dir / "Home" / "manual.pdf").exists()
    assert (out_dir / "Demo" / "image.png").exists()


def test_demo_page_contains_expected_conversions(tmp_path: Path) -> None:
    out_dir = tmp_path / "vault"
    convert(str(sample_notebook_path()), str(out_dir), overwrite=True)

    demo_md = out_dir / "Demo.md"
    text = demo_md.read_text(encoding="utf-8")

    assert text.startswith("---")
    assert "# Demo" in text
    assert "- [ ] open task" in text
    assert "- [x] completed task" in text
    assert "![[./Demo/image.png|320]]" in text
    assert "```" in text


def test_no_frontmatter(tmp_path: Path) -> None:
    out_dir = tmp_path / "vault"
    convert(str(sample_notebook_path()), str(out_dir), overwrite=True, no_frontmatter=True)

    home_md = out_dir / "Home.md"
    text = home_md.read_text(encoding="utf-8")
    assert not text.startswith("---")
    assert "# Home" in text


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    out_dir = tmp_path / "vault"
    result = convert(str(sample_notebook_path()), str(out_dir), dry_run=True)

    assert result.pages_converted == 5
    assert result.attachments_copied == 4
    assert len(result.planned) == 5
    assert not out_dir.exists()


def test_cli_dry_run_exit_code_and_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out_dir = tmp_path / "vault"
    code = cli_main([str(sample_notebook_path()), str(out_dir), "--dry-run"])
    captured = capsys.readouterr()

    assert code == 0
    assert "DRY RUN" in captured.out
    assert not out_dir.exists()
