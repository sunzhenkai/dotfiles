#!/usr/bin/env python3
"""Build docs/pretty-view/index.html so generated HTML is reachable in a browser.

INDEX.md remains the human/git catalog (HTML + Markdown). index.html is the
browser entry and only lists HTML *entry points*: a flat file under a kind
directory, or a bundle's index.html. Sibling pages inside a bundle stay off
the root catalog; the bundle main file routes to them.

Invoke from anywhere; pass the pretty-view root (the folder that contains
INDEX.md):

  python3 <this-skill>/scripts/update-catalog.py docs/pretty-view
  python3 <this-skill>/scripts/update-catalog.py --check docs/pretty-view

<this-skill> is the directory that contains pretty-view's SKILL.md.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

KIND_LABELS = {
    "articles": "长文",
    "knowledge": "知识",
    "reports": "报告",
    "proposals": "方案",
    "reviews": "评审",
    "slides": "幻灯片",
}
KIND_ORDER = (
    "articles",
    "knowledge",
    "reports",
    "proposals",
    "reviews",
    "slides",
)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BODY_RE = re.compile(r"<body[^>]*>", re.IGNORECASE)
NAV_MARK = "data-pretty-view-nav"
CATALOG_NAME = "index.html"
INDEX_NAME = "INDEX.md"
SKIP_DIR_NAMES = {"_assets", ".git"}


@dataclass(frozen=True)
class Entry:
    date: str
    title: str
    kind: str
    medium: str
    relpath: str
    source: str  # "index" | "orphan"


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate pretty-view/index.html from INDEX.md + on-disk HTML."
    )
    p.add_argument(
        "root",
        type=Path,
        help="pretty-view root (contains INDEX.md), e.g. docs/pretty-view",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="validate only; do not write index.html or inject nav",
    )
    p.add_argument(
        "--no-nav",
        action="store_true",
        help="do not inject ← 目录 into reading-page HTML",
    )
    return p.parse_args(argv)


def split_row(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    cells = [c.strip() for c in s.strip("|").split("|")]
    if not cells:
        return None
    if all(set(c) <= set("-: ") and c for c in cells):
        return None
    return cells


def parse_path_cell(cell: str) -> str:
    m = MD_LINK_RE.search(cell)
    raw = m.group(2) if m else cell
    return raw.split("#", 1)[0].strip()


def normalize_relpath(raw: str) -> str:
    p = raw.replace("\\", "/").lstrip("./")
    while p.startswith("/"):
        p = p[1:]
    if p.startswith("docs/pretty-view/"):
        p = p[len("docs/pretty-view/") :]
    return p


def infer_kind(relpath: str) -> str:
    top = Path(relpath).parts[0] if Path(relpath).parts else ""
    if top in KIND_LABELS:
        return top
    return "articles"


def infer_date(relpath: str) -> str:
    name = Path(relpath).name
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    if m:
        return m.group(1)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", Path(relpath).parts[-2] if len(Path(relpath).parts) > 1 else "")
    return m.group(1) if m else ""


def infer_title(relpath: str) -> str:
    path = Path(relpath)
    if path.name.lower() == "index.html" and path.parent.name:
        slug = path.parent.name
    else:
        slug = path.stem
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
    return slug.replace("-", " ") or relpath


def is_html_medium(medium: str, relpath: str) -> bool:
    m = medium.strip().lower()
    if m in {"html", "htm"}:
        return True
    if m in {"markdown", "md"}:
        return False
    return relpath.lower().endswith(".html") or relpath.lower().endswith(".htm")


def parse_index_md(text: str) -> list[Entry]:
    entries: list[Entry] = []
    seen_header = False
    for line in text.splitlines():
        cells = split_row(line)
        if cells is None:
            continue
        joined = "".join(cells).lower()
        if not seen_header:
            if "日期" in joined or "date" in joined:
                seen_header = True
            continue
        if len(cells) < 5:
            continue
        date_s, title, kind, medium, path_cell = cells[0], cells[1], cells[2], cells[3], cells[4]
        relpath = normalize_relpath(parse_path_cell(path_cell))
        if not relpath:
            continue
        kind = kind.strip() or infer_kind(relpath)
        entries.append(
            Entry(
                date=date_s.strip(),
                title=title.strip() or infer_title(relpath),
                kind=kind,
                medium=medium.strip() or ("HTML" if is_html_medium("", relpath) else "Markdown"),
                relpath=relpath,
                source="index",
            )
        )
    return entries


def posix_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_bundle_member(relpath: str) -> bool:
    """HTML inside <kind>/<slug>/ other than that folder's index.html."""
    parts = Path(relpath).parts
    if len(parts) < 3:
        return False
    return not (len(parts) == 3 and parts[-1].lower() == "index.html")


def discover_entry_paths(root: Path) -> tuple[list[Path], list[str]]:
    """Kind-level *.html plus one-level bundle */index.html. Return (entries, notes)."""
    entries: list[Path] = []
    notes: list[str] = []
    catalog = (root / CATALOG_NAME).resolve()
    for kind_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if kind_dir.name in SKIP_DIR_NAMES or kind_dir.name.startswith("."):
            continue
        for item in sorted(kind_dir.iterdir()):
            if item.name in SKIP_DIR_NAMES or item.name.startswith("."):
                continue
            if item.is_file() and item.suffix.lower() in {".html", ".htm"}:
                if item.resolve() == catalog:
                    continue
                entries.append(item)
                continue
            if not item.is_dir():
                continue
            main = item / "index.html"
            if main.is_file():
                entries.append(main)
            else:
                notes.append(f"包目录缺少主文件 index.html: {posix_rel(item, root)}/")
    return entries, notes


def merge_entries(
    index_entries: list[Entry],
    entry_paths: list[Path],
    root: Path,
) -> tuple[list[Entry], list[str], list[str], list[str]]:
    entry_rel = {posix_rel(p, root): p for p in entry_paths}
    listed_html: list[Entry] = []
    missing: list[str] = []
    skipped_members: list[str] = []
    seen: set[str] = set()

    for e in index_entries:
        if not is_html_medium(e.medium, e.relpath):
            continue
        if is_bundle_member(e.relpath):
            skipped_members.append(e.relpath)
            continue
        seen.add(e.relpath)
        if e.relpath not in entry_rel:
            missing.append(e.relpath)
            continue
        listed_html.append(e)

    orphans: list[str] = []
    extra: list[Entry] = []
    for rel, _path in entry_rel.items():
        if rel in seen:
            continue
        orphans.append(rel)
        extra.append(
            Entry(
                date=infer_date(rel),
                title=infer_title(rel),
                kind=infer_kind(rel),
                medium="HTML",
                relpath=rel,
                source="orphan",
            )
        )
    return listed_html + extra, missing, orphans, skipped_members


def kind_sort_key(kind: str) -> tuple[int, str]:
    try:
        return KIND_ORDER.index(kind), kind
    except ValueError:
        return len(KIND_ORDER), kind


def sort_entries(entries: list[Entry]) -> list[Entry]:
    def key(e: Entry) -> tuple:
        return (kind_sort_key(e.kind), e.date == "", 0 - _date_ord(e.date), e.title)

    return sorted(entries, key=key)


def _date_ord(s: str) -> int:
    try:
        y, m, d = (int(x) for x in s.split("-", 2))
        return date(y, m, d).toordinal()
    except ValueError:
        return 0


def render_catalog(entries: list[Entry], md_count: int) -> str:
    grouped: dict[str, list[Entry]] = {}
    for e in sort_entries(entries):
        grouped.setdefault(e.kind, []).append(e)

    sections: list[str] = []
    for kind in [*KIND_ORDER, *[k for k in grouped if k not in KIND_LABELS]]:
        items = grouped.get(kind)
        if not items:
            continue
        label = KIND_LABELS.get(kind, kind)
        rows = []
        for e in items:
            href = html.escape(e.relpath, quote=True)
            title = html.escape(e.title)
            meta = html.escape(" · ".join(x for x in (e.date, kind) if x))
            orphan = ' data-orphan="1"' if e.source == "orphan" else ""
            rows.append(
                f'      <a class="item"{orphan} href="{href}">'
                f'<span class="title">{title}</span>'
                f'<span class="meta">{meta}</span></a>'
            )
        sections.append(
            f"    <h2>{html.escape(label)} · {len(items)}</h2>\n"
            f'    <div class="list">\n' + "\n".join(rows) + "\n    </div>"
        )

    lede_bits = [f"{len(entries)} 篇 HTML"]
    if md_count:
        lede_bits.append(f"另有 {md_count} 篇 Markdown，见 INDEX.md")
    lede = "。".join(lede_bits) + "。"

    body = "\n".join(sections) if sections else '    <p class="empty">暂无 HTML 文档。</p>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pretty-view</title>
<style>
  :root {{ --ink:#1c1917; --muted:#78716c; --line:#e7e5e4; --bg:#fafaf9; --accent:#1d4ed8; }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:16px/1.5 ui-sans-serif,system-ui,sans-serif; }}
  main {{ max-width:720px; margin:0 auto; padding:48px 24px 80px; }}
  h1 {{ font-size:28px; font-weight:650; letter-spacing:-.02em; margin:0 0 8px; }}
  .lede {{ color:var(--muted); margin:0 0 8px; }}
  .empty {{ color:var(--muted); }}
  h2 {{ font-size:12px; font-weight:600; letter-spacing:.12em; text-transform:uppercase;
    color:var(--muted); margin:32px 0 4px; }}
  .list {{ border-top:1px solid var(--line); }}
  a.item {{ display:flex; justify-content:space-between; align-items:baseline; gap:16px;
    padding:12px 0; border-bottom:1px solid var(--line); color:inherit; text-decoration:none; }}
  a.item:hover .title {{ color:var(--accent); }}
  .title {{ font-weight:550; }}
  .meta {{ color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  footer {{ margin-top:48px; color:var(--muted); font-size:13px; }}
</style>
</head>
<body>
  <main>
    <h1>pretty-view</h1>
    <p class="lede">{html.escape(lede)}</p>
{body}
    <footer>由 pretty-view 从 INDEX.md 生成，请勿手改。</footer>
  </main>
</body>
</html>
"""


def _relpath(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target.resolve(), start.resolve())).as_posix()


def is_slide_page(root: Path, page: Path) -> bool:
    try:
        rel = page.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return (rel.parts[0] if rel.parts else "") == "slides"


def inject_nav(page: Path, href: str) -> str:
    """Insert or refresh a back-link. Returns 'inserted' | 'updated' | 'skipped'."""
    text = page.read_text(encoding="utf-8")
    nav = (
        f'<nav {NAV_MARK}="1" style="font:13px/1.4 ui-sans-serif,system-ui,sans-serif;'
        f"padding:10px 16px;border-bottom:1px solid #e7e5e4;background:#fafaf9\">"
        f'<a href="{html.escape(href, quote=True)}" style="color:#57534e;text-decoration:none">← 目录</a>'
        f"</nav>"
    )
    if NAV_MARK in text:
        new, n = re.subn(
            rf"<nav\s+{NAV_MARK}=\"1\"[^>]*>.*?</nav>",
            nav,
            text,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if n and new != text:
            page.write_text(new, encoding="utf-8")
            return "updated"
        return "skipped"
    m = BODY_RE.search(text)
    if not m:
        return "skipped"
    new = text[: m.end()] + "\n" + nav + "\n" + text[m.end() :]
    page.write_text(new, encoding="utf-8")
    return "inserted"


def md_entry_count(index_entries: list[Entry]) -> int:
    return sum(1 for e in index_entries if not is_html_medium(e.medium, e.relpath))


def ensure_index_blurb(index_path: Path, has_html: bool, check: bool) -> str:
    """Keep a one-line pointer to index.html in INDEX.md when HTML exists."""
    if not index_path.is_file():
        return "skipped"
    text = index_path.read_text(encoding="utf-8")
    pointer = "浏览器入口：[index.html](index.html)。"
    lines = text.splitlines()
    pointer_idxs = [
        i
        for i, line in enumerate(lines)
        if "浏览器入口" in line and "index.html" in line
    ]
    if has_html:
        if pointer_idxs:
            return "skipped"
        if check:
            return "would-insert"
        insert_at = 0
        if lines and lines[0].startswith("#"):
            insert_at = 1
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines[insert_at:insert_at] = ["", pointer, ""]
        else:
            lines = [pointer, ""] + lines
        index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return "inserted"
    if not pointer_idxs:
        return "skipped"
    if check:
        return "would-remove"
    keep = [line for i, line in enumerate(lines) if i not in set(pointer_idxs)]
    # collapse extra blank lines at top after H1
    cleaned: list[str] = []
    for line in keep:
        if line.strip() == "" and cleaned and cleaned[-1].strip() == "":
            continue
        cleaned.append(line)
    index_path.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
    return "removed"


def run(root: Path, check: bool, no_nav: bool) -> int:
    root = root.expanduser().resolve()
    if not root.is_dir():
        die(f"not a directory: {root}")
    index_path = root / INDEX_NAME
    if not index_path.is_file():
        die(f"missing {INDEX_NAME} under {root}")

    index_entries = parse_index_md(index_path.read_text(encoding="utf-8"))
    entry_paths, bundle_notes = discover_entry_paths(root)
    html_entries, missing, orphans, skipped_members = merge_entries(
        index_entries, entry_paths, root
    )
    md_count = md_entry_count(index_entries)

    for note in bundle_notes:
        warn(note)
    for rel in missing:
        warn(f"INDEX.md 指向不存在的 HTML（死链）: {rel}")
    for rel in skipped_members:
        warn(f"INDEX.md 登记了包内附属页，根目录只索引主文件 index.html: {rel}")
    for rel in orphans:
        warn(f"磁盘上有入口 HTML 但 INDEX.md 未登记: {rel}")

    catalog_path = root / CATALOG_NAME
    catalog_html = render_catalog(html_entries, md_count)

    if check:
        stale = True
        if catalog_path.is_file():
            stale = catalog_path.read_text(encoding="utf-8") != catalog_html
        elif not html_entries:
            stale = False
        if stale and html_entries:
            warn(f"{CATALOG_NAME} 与 INDEX.md / 磁盘 HTML 不一致")
        elif stale and not html_entries and catalog_path.is_file():
            warn(f"没有 HTML 条目，但 {CATALOG_NAME} 仍在")
        status = 1 if missing or stale else 0
        print(
            f"check: html={len(html_entries)} md={md_count} "
            f"missing={len(missing)} orphans={len(orphans)} stale={int(stale)}"
        )
        return status

    if html_entries:
        catalog_path.write_text(catalog_html, encoding="utf-8")
        print(f"wrote {catalog_path} ({len(html_entries)} html)")
    elif catalog_path.is_file():
        catalog_path.unlink()
        print(f"removed {catalog_path} (no html entries)")
    else:
        print("no html entries; skipped index.html")

    blurb = ensure_index_blurb(index_path, bool(html_entries), check=False)
    if blurb in {"inserted", "removed"}:
        print(f"{blurb} browser entry pointer in {index_path}")

    if not no_nav:
        for e in html_entries:
            page = root / e.relpath
            if not page.is_file() or is_slide_page(root, page):
                continue
            href = _relpath(catalog_path, page.parent)
            action = inject_nav(page, href)
            if action != "skipped":
                print(f"nav {action}: {e.relpath} -> {href}")

    if missing:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(args.root, check=args.check, no_nav=args.no_nav)


if __name__ == "__main__":
    raise SystemExit(main())
