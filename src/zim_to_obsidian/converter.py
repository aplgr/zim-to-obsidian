from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ZIM_CONTENT_TYPE = "text/x-zim-wiki"


@dataclass
class ConvertResult:
    """Conversion summary."""

    pages_converted: int
    attachments_copied: int
    planned: List[str]
    warnings: List[str]


@dataclass(frozen=True)
class PageInfo:
    src_path: Path
    rel_no_ext: Path
    dst_md_rel: Path
    page_name_colon: str
    title: str


def read_text_utf8(path: Path) -> str:
    # Zim pages are typically UTF-8/ASCII. We still read with a safe fallback.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def is_zim_page_file(path: Path) -> bool:
    """Return True if the file looks like a Zim page (starts with headers)."""

    if path.suffix.lower() != ".txt":
        return False

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            first = f.readline().strip()
        return first.lower().startswith("content-type:") and (ZIM_CONTENT_TYPE in first.lower())
    except OSError:
        return False


def parse_zim_headers_and_body(raw: str) -> Tuple[Dict[str, str], str]:
    """Split Zim headers and body.

    Zim page files typically start with headers, separated from the body by
    the first empty line.
    """

    lines = raw.splitlines()
    headers: Dict[str, str] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
        else:
            break
        i += 1

    body = "\n".join(lines[i:]) if i < len(lines) else ""
    return headers, body


def yaml_escape(s: str) -> str:
    # Minimal YAML escaping for single-line strings
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def build_frontmatter(page: PageInfo, headers: Dict[str, str]) -> str:
    created = headers.get("Creation-Date") or headers.get("creation-date") or ""
    wiki_format = headers.get("Wiki-Format") or headers.get("wiki-format") or ""
    content_type = headers.get("Content-Type") or headers.get("content-type") or ""

    fm_lines = ["---"]
    fm_lines.append(f"title: {yaml_escape(page.title)}")
    fm_lines.append(f"zim_page: {yaml_escape(page.page_name_colon)}")
    fm_lines.append(f"zim_source: {yaml_escape(str(page.src_path))}")
    if created:
        fm_lines.append(f"created: {yaml_escape(created)}")
    if wiki_format:
        fm_lines.append(f"zim_wiki_format: {yaml_escape(wiki_format)}")
    if content_type:
        fm_lines.append(f"zim_content_type: {yaml_escape(content_type)}")

    if headers:
        fm_lines.append("zim_headers:")
        for k in sorted(headers.keys()):
            fm_lines.append(f"  {k}: {yaml_escape(headers[k])}")

    fm_lines.append("---")
    return "\n".join(fm_lines) + "\n\n"


def zim_heading_to_md(line: str) -> Optional[str]:
    # Zim headings: ====== Head 1 ====== ... == Head 5 ==
    m = re.match(r"^(?P<eq>={2,6})\s*(?P<title>.*?)\s*(?P=eq)\s*$", line)
    if not m:
        return None
    eq = m.group("eq")
    title = m.group("title").strip()

    # len 6 -> H1, 5 -> H2, 4 -> H3, 3 -> H4, 2 -> H5
    level = 7 - len(eq)
    level = max(1, min(level, 6))
    return ("#" * level) + " " + title


def normalize_indent(s: str) -> Tuple[str, str]:
    """Return (indent, rest), normalizing tabs to spaces."""

    m = re.match(r"^([ \t]*)(.*)$", s)
    indent = m.group(1)
    rest = m.group(2)
    indent = indent.replace("\t", "  ")
    return indent, rest


def convert_checkbox_line(line: str) -> Optional[str]:
    # Zim checkbox states: [ ] open, [*] completed, [x] not completed, [>] moved, [<] moved back
    m = re.match(r"^([ \t]*)\[(?P<state>.?)\]\s+(?P<text>.*)$", line)
    if not m:
        return None

    indent = m.group(1).replace("\t", "  ")
    state = m.group("state")
    text = m.group("text")

    if state == " ":
        return f"{indent}- [ ] {text}"
    if state == "*":
        return f"{indent}- [x] {text}"
    if state.lower() == "x":
        return f"{indent}- [ ] ~~{text}~~ <!-- zim:state=x (not completed) -->"
    if state == ">":
        return f"{indent}- [ ] {text} <!-- zim:state=> (moved) -->"
    if state == "<":
        return f"{indent}- [ ] {text} <!-- zim:state=< (moved back) -->"

    return f"{indent}- [ ] {text} <!-- zim:state={state} -->"


def convert_lists(line: str) -> str:
    indent, rest = normalize_indent(line)

    cb = convert_checkbox_line(line)
    if cb is not None:
        return cb

    # Bullet lists: "* item"
    if rest.startswith("* "):
        return indent + "- " + rest[2:]

    # Numbered lists: keep as-is
    if re.match(r"^(?:\d+|[aA])\.\s+", rest):
        return indent + rest

    return line


def convert_inline_markup(text: str) -> str:
    # Underline: __text__ -> <u>text</u>
    text = re.sub(r"__([^_\n]+)__", r"<u>\1</u>", text)

    # Verbatim: ''text'' -> `text`
    text = re.sub(r"''([^'\n]+)''", r"`\1`", text)

    # Italic: //text// -> *text* (avoid URLs like http://)
    text = re.sub(r"(?<!:)//(?!\s)(.+?)(?<!\s)//", r"*\1*", text)

    return text


def parse_image_target(raw_target: str) -> Tuple[str, Optional[str]]:
    """Return (path_without_query, width) for Zim image syntax."""

    target = raw_target.strip()
    width: Optional[str] = None

    if "?" in target:
        base, query = target.split("?", 1)
        target = base.strip()
        m = re.search(r"(?:^|&|\?)width=(\d+)", "?" + query)
        if m:
            width = m.group(1)

    return target, width


def rewrite_rel_to_page_attachment(target: str, page_stem: str) -> str:
    """Rewrite Zim's ./ paths to the conventional page subfolder."""

    if target.startswith("./"):
        rest = target[2:].lstrip("/")
        return f"./{page_stem}/{rest}"
    return target


def convert_images(line: str, page_stem: str) -> str:
    # Zim images: {{...}}
    def repl(m: re.Match) -> str:
        inner = m.group(1)
        target, width = parse_image_target(inner)
        target = rewrite_rel_to_page_attachment(target, page_stem)

        # Obsidian supports embeds: ![[path|width]]
        if width:
            return f"![[{target}|{width}]]"
        return f"![[{target}]]"

    return re.sub(r"\{\{([^}]+)\}\}", repl, line)


def is_external_link_target(t: str) -> bool:
    tl = t.lower()
    return tl.startswith("http://") or tl.startswith("https://") or tl.startswith("file://")


def convert_links(
    line: str,
    page: PageInfo,
    by_path_no_ext: Dict[str, PageInfo],
) -> str:
    """Convert Zim [[...]] links to Obsidian wikilinks or Markdown links."""

    current_dir = page.rel_no_ext.parent.as_posix()

    def resolve_internal(raw_target: str) -> str:
        # Normalize Zim namespace separators
        t = raw_target.replace(":", "/").strip()

        # Root link: [[:Foo]]
        if raw_target.startswith(":"):
            return raw_target[1:].replace(":", "/").strip("/")

        # Subpage link: [[+Foo]]
        if raw_target.startswith("+"):
            sub = raw_target[1:].replace(":", "/").strip("/")
            base = page.rel_no_ext.as_posix()
            return f"{base}/{sub}".strip("/")

        # Explicit path-like link: [[A:B:Foo]] or [[A/Foo]]
        if "/" in t:
            return t.strip("/")

        # Plain "Foo": resolve within current folder then up to root
        parents: List[str] = []
        if current_dir and current_dir != ".":
            parts = current_dir.split("/")
            for i in range(len(parts), 0, -1):
                parents.append("/".join(parts[:i]))
        parents.append("")

        for p in parents:
            cand = f"{p}/{t}".strip("/")
            if cand in by_path_no_ext:
                return cand

        # Fallback: Obsidian may still resolve by filename
        return t

    def repl(m: re.Match) -> str:
        raw_target = m.group(1).strip()
        label = m.group(2)

        # External: [[https://x|label]]
        if is_external_link_target(raw_target):
            if label:
                return f"[{label}]({raw_target})"
            return raw_target

        # File-ish links: keep as markdown
        if "/" in raw_target or raw_target.startswith("./") or raw_target.startswith("~/"):
            target = rewrite_rel_to_page_attachment(raw_target, page.rel_no_ext.name)
            shown = label if label else os.path.basename(target)
            return f"[{shown}]({target})"

        resolved = resolve_internal(raw_target)
        if label:
            return f"[[{resolved}|{label}]]"
        return f"[[{resolved}]]"
    # Do not touch Obsidian embeds: ![[...]]
    return re.sub(r"(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", repl, line)


def convert_codeblocks(lines: List[str]) -> List[str]:
    """Convert Zim code fences (''') to Markdown triple backticks."""

    out: List[str] = []
    in_block = False

    for line in lines:
        if line.strip() == "'''":
            out.append("```")
            in_block = not in_block
            continue
        out.append(line)

    # If unbalanced, close it.
    if in_block:
        out.append("```")

    return out


def convert_hr(line: str) -> str:
    if re.match(r"^-{5,}\s*$", line.strip()):
        return "---"
    return line


def convert_page_body(body: str, page: PageInfo, by_path_no_ext: Dict[str, PageInfo]) -> str:
    lines = body.splitlines()

    # Convert code blocks early to avoid aggressive inline rewrites in fences
    lines = convert_codeblocks(lines)

    out: List[str] = []
    for raw_line in lines:
        line = raw_line

        h = zim_heading_to_md(line)
        if h is not None:
            out.append(h)
            continue

        line = convert_hr(line)
        line = convert_images(line, page.rel_no_ext.name)
        line = convert_links(line, page, by_path_no_ext)
        line = convert_lists(line)
        line = convert_inline_markup(line)

        out.append(line)

    return "\n".join(out).rstrip() + "\n"


def discover_pages(src_root: Path) -> List[PageInfo]:
    pages: List[PageInfo] = []

    for p in src_root.rglob("*"):
        if not p.is_file():
            continue
        if not is_zim_page_file(p):
            continue

        rel = p.relative_to(src_root)
        rel_no_ext = rel.with_suffix("")
        dst_md_rel = rel.with_suffix(".md")

        page_name_colon = ":".join(rel_no_ext.parts)
        title = rel_no_ext.name.replace("_", " ")

        pages.append(
            PageInfo(
                src_path=p,
                rel_no_ext=rel_no_ext,
                dst_md_rel=dst_md_rel,
                page_name_colon=page_name_colon,
                title=title,
            )
        )

    return pages


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_attachments_and_nonpages(src_root: Path, dst_root: Path, pages_set: set[Path], overwrite: bool) -> int:
    """Copy everything except Zim page source files."""

    copied = 0

    for p in src_root.rglob("*"):
        if not p.is_file():
            continue

        if p in pages_set:
            continue

        rel = p.relative_to(src_root)
        dst = dst_root / rel
        ensure_parent_dir(dst)

        if dst.exists() and not overwrite:
            continue

        shutil.copy2(p, dst)
        copied += 1

    return copied


def convert(
    src_dir: str,
    output_dir: str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
    no_frontmatter: bool = False,
) -> ConvertResult:
    """Convert a Zim notebook folder into an Obsidian vault folder."""

    src_root = Path(os.path.expanduser(src_dir)).resolve()
    dst_root = Path(os.path.expanduser(output_dir)).resolve()

    if not src_root.is_dir():
        raise ValueError(f"src_dir is not a directory: {src_root}")

    pages = discover_pages(src_root)
    pages_set = {p.src_path for p in pages}

    by_path_no_ext: Dict[str, PageInfo] = {p.rel_no_ext.as_posix(): p for p in pages}

    planned: List[str] = []
    warnings: List[str] = []

    if dry_run:
        # Plan conversions, but do not touch the destination.
        for page in pages:
            planned.append(str((dst_root / page.dst_md_rel).as_posix()))
        # Attachments plan: count everything that would be copied
        att_count = 0
        for p in src_root.rglob("*"):
            if p.is_file() and p not in pages_set:
                dst = dst_root / p.relative_to(src_root)
                if dst.exists() and not overwrite:
                    continue
                att_count += 1
        return ConvertResult(
            pages_converted=len(pages),
            attachments_copied=att_count,
            planned=planned,
            warnings=warnings,
        )

    dst_root.mkdir(parents=True, exist_ok=True)

    attachments_copied = copy_attachments_and_nonpages(src_root, dst_root, pages_set, overwrite=overwrite)

    pages_converted = 0

    for page in pages:
        try:
            raw = read_text_utf8(page.src_path)
            headers, body = parse_zim_headers_and_body(raw)

            ct = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
            if ZIM_CONTENT_TYPE not in ct:
                # Not a Zim page after all; treat it as attachment
                continue

            md_body = convert_page_body(body, page, by_path_no_ext)
            frontmatter = "" if no_frontmatter else build_frontmatter(page, headers)

            out_text = frontmatter + md_body

            dst_md = dst_root / page.dst_md_rel
            ensure_parent_dir(dst_md)

            if dst_md.exists() and not overwrite:
                continue

            dst_md.write_text(out_text, encoding="utf-8", errors="strict")
            planned.append(str(dst_md.as_posix()))
            pages_converted += 1

        except Exception as e:
            warnings.append(f"{page.src_path}: {e}")

    return ConvertResult(
        pages_converted=pages_converted,
        attachments_copied=attachments_copied,
        planned=planned,
        warnings=warnings,
    )
