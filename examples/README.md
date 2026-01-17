# Examples

This directory contains a small sanitized Zim notebook (`sample_notebook`).

Convert it into a temporary Obsidian vault:

```bash
python3 ../scripts/zim2obsidian.py sample_notebook /tmp/Zim_Imported
```

Try variants:

```bash
python3 ../scripts/zim2obsidian.py sample_notebook /tmp/Zim_Imported --dry-run
python3 ../scripts/zim2obsidian.py sample_notebook /tmp/Zim_Imported --overwrite
python3 ../scripts/zim2obsidian.py sample_notebook /tmp/Zim_Imported --no-frontmatter
```
