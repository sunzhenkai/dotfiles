#!/usr/bin/env python3
"""Build docs/pretty-view-ppt/index.html from slide bundles."""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INDEX_NAME = "INDEX.md"
CATALOG_NAME = "index.html"


@dataclass(frozen=True)
class Deck:
    title: str
    relpath: str
    date: str = ""


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate pretty-view-ppt/index.html from slide bundles."
    )
    parser.add_argument(
        "root",
        type=Path,
        help="pretty-view-ppt root, e.g. docs/pretty-view-ppt",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate catalog without writing files",
    )
    return parser.parse_args(argv)


def normalize_path(raw: str) -> str:
    path = raw.replace("\\", "/").split("#", 1)[0].strip().lstrip("./")
    prefix = "docs/pretty-view-ppt/"
    return path[len(prefix) :] if path.startswith(prefix) else path


def parse_index(text: str) -> dict[str, Deck]:
    decks: dict[str, Deck] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or all(set(cell) <= set("-: ") for cell in cells):
            continue
        match = LINK_RE.search(cells[4])
        if not match:
            continue
        relpath = normalize_path(match.group(2))
        if not re.fullmatch(r"slides/[^/]+/index\.html", relpath):
            continue
        decks[relpath] = Deck(
            title=cells[1] or match.group(1),
            relpath=relpath,
            date=cells[0],
        )
    return decks


def discover(root: Path) -> dict[str, Path]:
    slides = root / "slides"
    if not slides.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(slides.glob("*/index.html"))
        if path.is_file()
    }


def infer_title(relpath: str) -> str:
    return Path(relpath).parent.name.replace("-", " ")


def render(decks: list[Deck]) -> str:
    rows = "\n".join(
        (
            f'      <a class="item" href="{html.escape(deck.relpath, quote=True)}">'
            f'<span class="title">{html.escape(deck.title)}</span>'
            f'<span class="meta">{html.escape(deck.date)}</span></a>'
        )
        for deck in decks
    )
    body = (
        f'    <div class="list">\n{rows}\n    </div>'
        if rows
        else '    <p class="empty">暂无演示文稿。</p>'
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pretty-view-ppt</title>
<style>
  :root {{ --ink:#171717; --muted:#737373; --line:#e5e5e5; --bg:#fafafa; --accent:#2563eb; }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 ui-sans-serif,system-ui,sans-serif; }}
  main {{ width:100%; padding:48px clamp(24px,4vw,56px) 80px; }}
  h1 {{ margin:0 0 8px; font-size:28px; letter-spacing:-.02em; }}
  .lede,.empty,.meta,footer {{ color:var(--muted); }}
  .list {{ margin-top:28px; border-top:1px solid var(--line); }}
  .item {{ display:flex; justify-content:space-between; gap:16px; padding:14px 0;
    border-bottom:1px solid var(--line); color:inherit; text-decoration:none; }}
  .item:hover .title {{ color:var(--accent); }}
  .title {{ font-weight:600; }}
  .meta {{ font-size:13px; font-variant-numeric:tabular-nums; }}
  footer {{ margin-top:48px; font-size:13px; }}
</style>
</head>
<body>
  <main>
    <h1>pretty-view-ppt</h1>
    <p class="lede">{len(decks)} 份演示文稿。</p>
{body}
    <footer>由 pretty-view-ppt 从 INDEX.md 生成，请勿手改。</footer>
  </main>
</body>
</html>
"""


def ensure_pointer(index_path: Path, check: bool) -> bool:
    text = index_path.read_text(encoding="utf-8")
    pointer = "浏览器入口：[index.html](index.html)。"
    if pointer in text:
        return False
    if check:
        return True
    lines = text.splitlines()
    insert_at = 1 if lines and lines[0].startswith("#") else 0
    lines[insert_at:insert_at] = ["", pointer, ""]
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def run(root: Path, check: bool) -> int:
    root = root.expanduser().resolve()
    if not root.is_dir():
        die(f"not a directory: {root}")
    index_path = root / INDEX_NAME
    if not index_path.is_file():
        die(f"missing {INDEX_NAME} under {root}")

    listed = parse_index(index_path.read_text(encoding="utf-8"))
    found = discover(root)
    missing = sorted(set(listed) - set(found))
    orphans = sorted(set(found) - set(listed))
    for relpath in missing:
        print(f"warning: INDEX.md 指向不存在的演示文稿: {relpath}", file=sys.stderr)
    for relpath in orphans:
        print(f"warning: 演示文稿未登记到 INDEX.md: {relpath}", file=sys.stderr)

    decks = [
        listed.get(relpath, Deck(infer_title(relpath), relpath))
        for relpath in sorted(found)
    ]
    catalog = render(decks)
    catalog_path = root / CATALOG_NAME
    stale = not catalog_path.is_file() or catalog_path.read_text(encoding="utf-8") != catalog
    pointer_stale = ensure_pointer(index_path, check=check)

    if check:
        print(
            f"check: decks={len(decks)} missing={len(missing)} "
            f"orphans={len(orphans)} stale={int(stale or pointer_stale)}"
        )
        return 1 if missing or stale or pointer_stale else 0

    catalog_path.write_text(catalog, encoding="utf-8")
    ensure_pointer(index_path, check=False)
    print(f"wrote {catalog_path} ({len(decks)} decks)")
    return 1 if missing else 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(args.root, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
