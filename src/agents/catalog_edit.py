#!/usr/bin/env python3
"""Line-level member edits for the hand-written skill catalogue.

`agents/skills.yaml` carries curated comments, so rewrites driven by upstream
discovery must not round-trip it through YAML: dumping would drop every
comment. These helpers touch only the member lines of one group's `skills:`
list and leave the rest of the file byte-identical.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

CATALOG_REL = Path("agents") / "skills.yaml"
_GROUP_INDENT = "  "
_MEMBER_PREFIX = "      - "
_MEMBER_CONTINUATION = " " * 8
_EMPTY_LIST = "    skills: []"
_OPEN_LIST = "    skills:"


class CatalogEditError(RuntimeError):
    pass


def _group_bounds(lines: Sequence[str], group: str) -> tuple[int, int]:
    """Return the [start, end) line range of one top-level group block."""
    start = None
    for index, line in enumerate(lines):
        if not line.startswith(_GROUP_INDENT) or line.startswith(_GROUP_INDENT + " "):
            continue
        name, separator, _ = line[len(_GROUP_INDENT) :].partition(":")
        if separator and name == group:
            start = index
            break
    if start is None:
        raise CatalogEditError(f"catalog group not found: {group}")
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        if not line.startswith(" "):
            return start, index
        if line.startswith(_GROUP_INDENT) and not line.startswith(_GROUP_INDENT + " "):
            return start, index
    return start, len(lines)


def _list_start(lines: Sequence[str], start: int, end: int) -> int:
    for index in range(start, end):
        if lines[index].rstrip() in {_OPEN_LIST, _EMPTY_LIST}:
            return index
    raise CatalogEditError("group has no skills: list")


def _member_spans(lines: Sequence[str], start: int, end: int) -> list[tuple[int, int]]:
    """Half-open line spans of each member; blank and comment lines end a span."""
    first = _list_start(lines, start, end) + 1
    spans: list[tuple[int, int]] = []
    current = None
    for index in range(first, end):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if current is not None:
                spans.append((current, index))
                current = None
            continue
        if line.startswith(_MEMBER_PREFIX):
            if current is not None:
                spans.append((current, index))
            current = index
            continue
        if current is not None and line.startswith(_MEMBER_CONTINUATION):
            continue
        if current is not None:
            spans.append((current, index))
            current = None
    if current is not None:
        spans.append((current, end))
    return spans


def _member_id(lines: Sequence[str], index: int) -> str:
    body = lines[index].strip()
    if not body.startswith("- "):
        raise CatalogEditError(f"not a skills member line: {lines[index]!r}")
    body = body[2:].strip()
    if body.startswith("id:"):
        body = body[len("id:") :].strip()
    return body.strip("'\"")


def member_ids(text: str, group: str) -> list[str]:
    lines = text.splitlines()
    start, end = _group_bounds(lines, group)
    return [
        _member_id(lines, span_start)
        for span_start, _ in _member_spans(lines, start, end)
    ]


def add_optional_member(text: str, group: str, skill_id: str) -> str:
    """Append `- id: <skill_id>` + `optional: true` to one group's member list."""
    lines = text.splitlines()
    start, end = _group_bounds(lines, group)
    if skill_id in member_ids(text, group):
        raise CatalogEditError(f"group {group!r} already lists {skill_id}")
    list_line = _list_start(lines, start, end)
    if lines[list_line].rstrip() == _EMPTY_LIST:
        lines[list_line] = _OPEN_LIST
        lines[list_line + 1 : list_line + 1] = [
            _MEMBER_PREFIX + "id: " + skill_id,
            _MEMBER_CONTINUATION + "optional: true",
        ]
        return "\n".join(lines) + "\n"
    spans = _member_spans(lines, start, end)
    if not spans:
        raise CatalogEditError(f"group {group!r} has no members to append after")
    insert_at = spans[-1][1]
    lines[insert_at:insert_at] = [
        _MEMBER_PREFIX + "id: " + skill_id,
        _MEMBER_CONTINUATION + "optional: true",
    ]
    return "\n".join(lines) + "\n"


def remove_member(text: str, group: str, skill_id: str) -> str:
    lines = text.splitlines()
    start, end = _group_bounds(lines, group)
    list_line = _list_start(lines, start, end)
    spans = _member_spans(lines, start, end)
    for span_start, span_end in spans:
        if _member_id(lines, span_start) == skill_id:
            del lines[span_start:span_end]
            if len(spans) == 1:
                lines[list_line] = _EMPTY_LIST
            return "\n".join(lines) + "\n"
    raise CatalogEditError(f"group {group!r} does not list {skill_id}")
