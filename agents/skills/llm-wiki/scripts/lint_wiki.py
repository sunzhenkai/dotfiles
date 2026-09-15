#!/usr/bin/env python3
"""Deterministic lint (and optional index rebuild) for a local LLM wiki workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

TYPED_DIRS = {
    "entities": "entity",
    "concepts": "concept",
    "sources": "source",
    "synthesis": "synthesis",
    "comparisons": "comparison",
    "queries": "query",
}
TYPE_TO_DIR = {v: k for k, v in TYPED_DIRS.items()}
SYSTEM_PAGES = {"overview.md", "index.md", "log.md"}
INDEX_HEADINGS = [
    ("entities", "实体 (entities)"),
    ("concepts", "概念 (concepts)"),
    ("sources", "源摘要 (sources)"),
    ("synthesis", "综合分析 (synthesis)"),
    ("comparisons", "对比分析 (comparisons)"),
    ("queries", "查询归档 (queries)"),
]
ABSTRACT_KEYWORDS = (
    "方法",
    "方法论",
    "模型",
    "文化",
    "框架",
    "策略",
    "机制",
    "理论",
    "范式",
    "实践",
    "流程",
    "体系",
    "method",
    "methodology",
    "model",
    "culture",
    "framework",
    "strategy",
    "mechanism",
    "theory",
    "paradigm",
    "practice",
    "process",
    "system",
)
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
MDLINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
LOG_RE = re.compile(
    r"^## \[(\d{4}-\d{2}-\d{2})\] ([^|]+?) \| (.+)$"
)
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wiki_root", type=Path, help="Workspace root containing wiki/")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report")
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="Rebuild wiki/index.md from typed pages",
    )
    return parser.parse_args(argv)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def normalize_name_key(value: str) -> str:
    chars = []
    for ch in value.strip().lower():
        if ch in {" ", "_", "-", "\u3000"}:
            continue
        chars.append(ch)
    return "".join(chars)


def title_from_filename(stem: str) -> str:
    return stem.replace("-", " ").replace("_", " ").strip()


def iter_wiki_pages(wiki_dir: Path) -> list[Path]:
    if not wiki_dir.is_dir():
        return []
    pages = [
        path
        for path in wiki_dir.rglob("*.md")
        if path.is_file() and ".git" not in path.parts
    ]
    return sorted(pages)


def rel_wiki(path: Path, wiki_dir: Path) -> str:
    return path.relative_to(wiki_dir).as_posix()


def classify(rel: str) -> str:
    if rel in SYSTEM_PAGES:
        return "system"
    parts = rel.split("/")
    if parts[0] == "templates":
        return "template"
    if len(parts) >= 2 and parts[0] in TYPED_DIRS:
        return "business"
    return "misplaced"


def load_pages(wiki_dir: Path) -> list[dict]:
    pages = []
    for path in iter_wiki_pages(wiki_dir):
        rel = rel_wiki(path, wiki_dir)
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        stem = path.stem
        title = fm.get("title") or title_from_filename(stem)
        kind = classify(rel)
        subdir = rel.split("/", 1)[0] if "/" in rel else ""
        pages.append(
            {
                "path": path,
                "rel": rel,
                "text": text,
                "fm": fm,
                "stem": stem,
                "title": title,
                "kind": kind,
                "subdir": subdir,
            }
        )
    return pages


def build_resolvers(pages: list[dict]) -> dict[str, str]:
    """Map lookup keys to page rel paths. Later pages do not override unique keys."""
    mapping: dict[str, str] = {}

    def add(key: str, rel: str) -> None:
        key = key.strip()
        if not key:
            return
        mapping.setdefault(key, rel)
        mapping.setdefault(key.lower(), rel)
        mapping.setdefault(normalize_name_key(key), rel)

    for page in pages:
        rel = page["rel"]
        add(rel, rel)
        add(rel[:-3] if rel.endswith(".md") else rel, rel)
        add(page["stem"], rel)
        add(page["title"], rel)
        add(title_from_filename(page["stem"]), rel)
        if "/" in rel:
            add(rel.split("/", 1)[1], rel)
            add(Path(rel).stem, rel)
    return mapping


def split_wikilink(raw: str) -> str:
    # GFM tables escape wikilink aliases as [[path\|Title]]
    raw = raw.replace("\\|", "|")
    target = raw.split("|", 1)[0].strip()
    target = target.split("#", 1)[0].strip()
    return target


def resolve_wikilink(target: str, mapping: dict[str, str]) -> str | None:
    if not target:
        return None
    candidates = [
        target,
        target.lower(),
        normalize_name_key(target),
        f"{target}.md",
        f"{target.lower()}.md",
    ]
    if not target.endswith(".md") and "/" in target:
        candidates.append(f"{target}.md")
    for key in candidates:
        if key in mapping:
            return mapping[key]
    return None


def resolve_md_link(source_rel: str, target: str, wiki_dir: Path) -> Path | None:
    href = target.strip()
    if not href or href.startswith(("#", "http://", "https://", "mailto:")):
        return None
    href = href.split("#", 1)[0]
    if not href:
        return None
    base = (wiki_dir / source_rel).parent
    dest = (base / href).resolve()
    try:
        dest.relative_to(wiki_dir.resolve())
    except ValueError:
        return dest
    return dest


def collect_incoming(pages: list[dict], mapping: dict[str, str], wiki_dir: Path) -> dict[str, int]:
    incoming: dict[str, int] = defaultdict(int)
    for page in pages:
        # Index/overview list many pages; counting them would hide real orphans.
        if page["kind"] in {"system", "template"}:
            continue
        seen: set[str] = set()
        for match in WIKILINK_RE.finditer(page["text"]):
            target = split_wikilink(match.group(1))
            resolved = resolve_wikilink(target, mapping)
            if resolved and resolved != page["rel"] and resolved not in seen:
                incoming[resolved] += 1
                seen.add(resolved)
        for match in MDLINK_RE.finditer(page["text"]):
            dest = resolve_md_link(page["rel"], match.group(2), wiki_dir)
            if dest is None or not dest.exists() or dest.suffix != ".md":
                continue
            try:
                rel = dest.relative_to(wiki_dir.resolve()).as_posix()
            except ValueError:
                continue
            if rel != page["rel"] and rel not in seen:
                incoming[rel] += 1
                seen.add(rel)
    return incoming


def lint_issues(pages: list[dict], wiki_dir: Path) -> list[dict]:
    mapping = build_resolvers(pages)
    incoming = collect_incoming(pages, mapping, wiki_dir)
    issues: list[dict] = []

    def add(code: str, severity: str, rel: str, message: str) -> None:
        issues.append(
            {"code": code, "severity": severity, "path": f"wiki/{rel}", "message": message}
        )

    entity_names: list[tuple[str, str]] = []
    for page in pages:
        if page["kind"] != "business" or page["subdir"] != "entities":
            continue
        for display in (page["title"], page["stem"], title_from_filename(page["stem"])):
            key = normalize_name_key(display)
            if len(key) >= 3:
                entity_names.append((display, key))

    dup_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for page in pages:
        rel = page["rel"]
        kind = page["kind"]
        fm = page["fm"]

        if kind == "misplaced":
            add(
                "misplaced_wiki_page",
                "warning",
                rel,
                "业务页不在 typed 子目录",
            )

        if kind == "business":
            missing = [field for field in ("title", "type", "date") if not fm.get(field)]
            if missing or not fm:
                add(
                    "missing_frontmatter",
                    "error",
                    rel,
                    "缺少 frontmatter 字段: " + (", ".join(missing) or "title, type, date"),
                )
            page_type = fm.get("type", "")
            expected_dir = TYPE_TO_DIR.get(page_type)
            if page_type and expected_dir and page["subdir"] != expected_dir:
                add(
                    "type_dir_mismatch",
                    "warning",
                    rel,
                    f"type={page_type} 应位于 wiki/{expected_dir}/",
                )
            if page["subdir"] in TYPED_DIRS:
                dup_groups[(page["subdir"], normalize_name_key(page["stem"]))].append(rel)

        if kind == "business" and page["subdir"] == "concepts":
            for source in (page["title"], page["stem"]):
                coupled = match_entity_concept(source, entity_names)
                if coupled:
                    entity, suffix = coupled
                    add(
                        "entity_concept_coupling",
                        "warning",
                        rel,
                        f"概念标题绑定实体 {entity!r} 与抽象后缀 {suffix!r}",
                    )
                    break

        for match in WIKILINK_RE.finditer(page["text"]):
            target = split_wikilink(match.group(1))
            if resolve_wikilink(target, mapping) is None:
                add("dead_link", "error", rel, f"死链 [[{target}]]")

        for match in MDLINK_RE.finditer(page["text"]):
            href = match.group(2).strip()
            dest = resolve_md_link(rel, href, wiki_dir)
            if dest is None:
                continue
            if not dest.exists():
                add("dead_link", "error", rel, f"死链 ({href})")

    for (subdir, key), rels in dup_groups.items():
        if key and len(rels) > 1:
            joined = ", ".join(f"wiki/{item}" for item in rels)
            for rel in rels:
                add(
                    "duplicate_page",
                    "warning",
                    rel,
                    f"{subdir}/ 下归一化重名: {joined}",
                )

    for page in pages:
        if page["kind"] != "business":
            continue
        if page["subdir"] == "sources":
            continue
        if incoming.get(page["rel"], 0) == 0:
            add("orphan_page", "warning", page["rel"], "没有来自其它 wiki 页的入链")

    log_page = next((page for page in pages if page["rel"] == "log.md"), None)
    if log_page:
        issues.extend(lint_log(log_page["text"]))

    return issues


def match_entity_concept(name: str, entities: list[tuple[str, str]]) -> tuple[str, str] | None:
    key = normalize_name_key(name)
    if not key:
        return None
    for display, entity_key in entities:
        if not key.startswith(entity_key) or len(key) <= len(entity_key):
            continue
        suffix = key[len(entity_key) :]
        lowered = suffix.lower()
        if any(normalize_name_key(word) in lowered for word in ABSTRACT_KEYWORDS):
            return display, suffix
    return None


def lint_log(text: str) -> list[dict]:
    issues: list[dict] = []
    dates: list[str] = []
    for line in text.splitlines():
        if not line.startswith("## ["):
            continue
        match = LOG_RE.match(line)
        if not match:
            issues.append(
                {
                    "code": "log_format_invalid",
                    "severity": "error",
                    "path": "wiki/log.md",
                    "message": f"日志格式无效: {line}",
                }
            )
            continue
        dates.append(match.group(1))
    for prev, curr in zip(dates, dates[1:]):
        if curr < prev:
            issues.append(
                {
                    "code": "log_date_decreasing",
                    "severity": "error",
                    "path": "wiki/log.md",
                    "message": f"日期递减: {prev} → {curr}",
                }
            )
            break
    return issues


def rebuild_index(pages: list[dict], wiki_dir: Path) -> str:
    grouped: dict[str, list[dict]] = {name: [] for name, _ in INDEX_HEADINGS}
    for page in pages:
        if page["kind"] != "business" or page["subdir"] not in grouped:
            continue
        fm = page["fm"]
        grouped[page["subdir"]].append(
            {
                "subdir": page["subdir"],
                "slug": page["stem"],
                "title": page["title"],
                "description": fm.get("description", ""),
                "date": fm.get("date", ""),
            }
        )
    for entries in grouped.values():
        entries.sort(key=lambda item: (item["title"].lower(), item["slug"]))

    today = date.today().isoformat()
    lines = [
        "---",
        "title: 内容目录",
        "type: index",
        f"date: {today}",
        "---",
        "",
        "# 内容目录",
        "",
        "> 本文件由 llm-wiki 维护，请勿手改业务行。",
        "",
    ]
    for dirname, heading in INDEX_HEADINGS:
        lines.extend(
            [
                f"## {heading}",
                "",
                "| 页面 | 标题 | 摘要 | 更新日期 |",
                "|------|------|------|----------|",
            ]
        )
        for entry in grouped[dirname]:
            title = escape_cell(entry["title"])
            link = f"[[{entry['subdir']}/{entry['slug']}\\|{title}]]"
            lines.append(
                f"| {link} | {title} | {escape_cell(entry['description'])} | {escape_cell(entry['date'])} |"
            )
        lines.append("")
    text = "\n".join(lines)
    (wiki_dir / "index.md").write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return text


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_text(issues: list[dict], page_count: int) -> str:
    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    lines = [
        f"pages: {page_count}",
        f"errors: {len(errors)}",
        f"warnings: {len(warnings)}",
    ]
    if not issues:
        lines.append("ok")
        return "\n".join(lines) + "\n"
    lines.append("")
    for item in issues:
        lines.append(f"{item['severity']}\t{item['code']}\t{item['path']}\t{item['message']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.wiki_root.expanduser().resolve()
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        print(f"missing wiki directory: {wiki_dir}", file=sys.stderr)
        return 2

    pages = load_pages(wiki_dir)
    if args.write_index:
        rebuild_index(pages, wiki_dir)
        pages = load_pages(wiki_dir)

    issues = lint_issues(pages, wiki_dir)
    payload = {
        "wiki_root": str(root),
        "pages": len(pages),
        "errors": sum(1 for item in issues if item["severity"] == "error"),
        "warnings": sum(1 for item in issues if item["severity"] == "warning"),
        "issues": issues,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(render_text(issues, len(pages)))
    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
