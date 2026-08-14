#!/usr/bin/env python3
"""Deterministic helpers for task-* bookkeeping (Gate / INDEX / scaffold / archive / git).

Invoke from this skill directory (the folder that contains SKILL.md), not the project root:

  python3 scripts/taskctl.py list
  python3 scripts/taskctl.py resolve T0002 --command task-apply
  python3 scripts/taskctl.py resolve --infer --command task-apply --hint "继续 T0002"
  python3 scripts/taskctl.py set-status T0002 exploring
  python3 scripts/taskctl.py new --slug my-feature --title "标题"
  python3 scripts/taskctl.py new --title "Optimize providers from model.dev"
  python3 scripts/taskctl.py archive T0002
  python3 scripts/taskctl.py prepare-branches --slug my-feature --from-task T0002
  python3 scripts/taskctl.py prepare-branches --slug my-feature --repo path/to/target
  python3 scripts/taskctl.py git-summary --repo path/to/target --branch feat-my-feature
  python3 scripts/taskctl.py notes
  python3 scripts/taskctl.py notes --init
  python3 scripts/taskctl.py notes --set-section 特殊要求 --body "验收必须带回归清单"

`--root` defaults to the nearest ancestor that contains `tasks/`.
`--repo` is a workspace-relative path to a git root that this task will modify.
Do not pass cwd or `.` unless the workspace git root itself is a must-modify target.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

VALID_STATUSES = (
    "draft",
    "exploring",
    "designed",
    "proposed",
    "in_progress",
    "blocked",
    "archived",
)

VALID_BRANCH_PREFIXES = ("feat", "fix", "chore", "refactor")
DEFAULT_EXCLUDE_REPO_MARKERS: tuple[str, ...] = ()
BRANCH_SLUG_RE = re.compile(r"^(?:feat|fix|chore|refactor)-(.+)$")
HINT_ID_RE = re.compile(r"\b[Tt](\d{1,4})\b")
HINT_PATH_RE = re.compile(
    r"(tasks/(?:archive/)?\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+/?)"
)
WORKFLOW_NOTES_REL = ".task-workflow.md"
HEADING_LINE_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
DIRTY_USER_ACTIONS = (
    {
        "id": "commit",
        "label": "提交或清理该仓改动后重试 prepare-branches",
    },
    {
        "id": "skip_dirty",
        "label": "确认跳过该脏仓（其余仓继续）：prepare-branches ... --skip-dirty",
    },
    {
        "id": "abort",
        "label": "中止，稍后再执行本命令",
    },
)
COMMAND_STATUS_PREFER: dict[str, tuple[str, ...]] = {
    "task-apply": ("in_progress", "blocked", "proposed"),
    "task-archive": ("in_progress", "blocked", "proposed", "designed"),
    "task-propose": ("designed", "exploring", "draft", "proposed"),
    "task-design": ("exploring", "draft", "designed"),
    "task-explore": ("exploring", "draft", "designed", "in_progress", "proposed"),
}

ID_RE = re.compile(r"^T(\d{1,4})$", re.IGNORECASE)
ID_SLUG_RE = re.compile(r"^T(\d{1,4})-(.+)$", re.IGNORECASE)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DIR_ID_SLUG_RE = re.compile(r"^(T\d{4})-(.+)$", re.IGNORECASE)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
STATUS_LINE_RE = re.compile(
    r"^(\*\*(?:status|状态)[：:]\*\*\s*)([A-Za-z_]+)(\s*)$",
    re.MULTILINE,
)
CHECKBOX_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s+(.+?)\s*$", re.MULTILINE)
VERIFICATION_ITEM_RE = re.compile(
    r"(验证|测试|回归|冒烟|healthcheck|healthy|smoke|e2e|"
    r"\bqa\b|\btest\b|verify|validation|lint|typecheck)",
    re.IGNORECASE,
)
FM_STATUS_RE = re.compile(r"^(status:\s*)(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
FM_ID_RE = re.compile(r"^(id:\s*)(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
META_ID_RE = re.compile(r"^\*\*id[：:]\*\*\s*(T\d{4})\s*$", re.MULTILINE | re.IGNORECASE)


@dataclass
class TaskRow:
    task_id: str
    name: str
    path: str  # relative posix, usually tasks/.../
    status: str = "draft"
    updated: str = ""
    archived_on: str = ""
    section: str = "active"  # active | archived


def empty_scope() -> dict[str, Any]:
    return {"must": [], "suggested": [], "excluded": [], "checkout": []}


@dataclass
class TaskInfo:
    task_id: str
    task_root: str
    slug: str
    name: str
    status: str
    readme: str
    openspec: list[dict[str, str]] = field(default_factory=list)
    scope: dict[str, Any] = field(default_factory=empty_scope)
    checkouts: list[dict[str, Any]] = field(default_factory=list)
    index_path: str = ""
    updated: str = ""


class TaskError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def emit(payload: dict[str, Any], *, code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def today_str() -> str:
    return date.today().isoformat()


def normalize_id(raw: str) -> str:
    m = ID_RE.match(raw.strip())
    if not m:
        raise TaskError(f"invalid task id: {raw}")
    return f"T{int(m.group(1)):04d}"


def validate_slug(slug: str) -> str:
    s = slug.strip().lower()
    if not SLUG_RE.match(s):
        raise TaskError(f"invalid slug (kebab-case required): {slug}")
    return s


_SLUG_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "from",
        "for",
        "with",
        "in",
        "on",
        "at",
        "by",
        "as",
        "is",
        "be",
        "this",
        "that",
        "it",
    }
)


def slugify_from_text(text: str, *, max_parts: int = 6) -> str:
    raw = re.sub(r"[._/:+]+", " ", (text or "").strip().lower())
    parts: list[str] = []
    seen: set[str] = set()
    for tok in re.findall(r"[a-z0-9]+", raw):
        if tok in _SLUG_STOP or tok in seen:
            continue
        if len(tok) == 1 and tok.isalpha():
            continue
        seen.add(tok)
        parts.append(tok)
        if len(parts) >= max_parts:
            break
    slug = "-".join(parts)
    if not SLUG_RE.match(slug):
        raise TaskError("cannot infer slug from text; pass --slug")
    return slug


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "tasks" / "INDEX.md").is_file() or (p / "tasks").is_dir():
            return p
    raise TaskError("cannot locate workspace root (need tasks/)")


def index_path(root: Path) -> Path:
    return root / "tasks" / "INDEX.md"


def workflow_notes_path(root: Path) -> Path:
    return root / WORKFLOW_NOTES_REL


def normalize_heading(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().lstrip("#").strip()).lower()


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace a UTF-8 text file in its current directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


@contextlib.contextmanager
def index_lock(root: Path):
    """Serialize task id allocation and archive index transitions."""
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
    lock_path = Path(tempfile.gettempdir()) / f"taskctl-{digest}.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def parse_markdown_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    starts: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = HEADING_LINE_RE.match(line)
        if m:
            starts.append((i, len(m.group(1)), m.group(2).strip()))
    sections: list[dict[str, Any]] = []
    for idx, (i, level, title) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = "\n".join(lines[i + 1 : end]).strip()
        sections.append({"heading": title, "level": level, "body": body})
    return sections


def scaffold_workflow_notes(workspace_name: str) -> str:
    return f"""# 任务工作流 — {workspace_name}

跨任务仍有效的特殊要求、规格说明与默认涉及面。单次任务的概述/验收写在对应 task README，不要把一次性需求写进本文件。

## 概览

- （待补：本工作区如何走 task-*）

## 特殊要求

- （待补：分支前缀、验收习惯、保密、落盘位置等）

## 规格说明

- （待补：OpenSpec 落点、change 命名、设计晋升路径等）

## 默认涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| — | | （尚无） |

## 约定

- （待补）

## 手帐

- （尚无）

## 踩坑

- （尚无）
"""


def read_workflow_notes(root: Path) -> dict[str, Any]:
    path = workflow_notes_path(root)
    if not path.is_file():
        return {
            "exists": False,
            "path": WORKFLOW_NOTES_REL,
            "markdown": "",
            "sections": [],
            "scope": empty_scope(),
        }
    text = path.read_text(encoding="utf-8")
    return {
        "exists": True,
        "path": WORKFLOW_NOTES_REL,
        "markdown": text,
        "sections": parse_markdown_sections(text),
        "scope": parse_scope(text),
    }


def write_workflow_notes(root: Path, markdown: str) -> Path:
    path = workflow_notes_path(root)
    atomic_write_text(path, ensure_trailing_newline(markdown))
    return path


def upsert_markdown_section(text: str, heading: str, body: str) -> str:
    body = body.strip()
    lines = text.splitlines()
    target = normalize_heading(heading)
    start = None
    level = 2
    for i, line in enumerate(lines):
        m = HEADING_LINE_RE.match(line)
        if m and normalize_heading(m.group(2)) == target:
            start = i
            level = len(m.group(1))
            break
    if start is None:
        base = ensure_trailing_newline(text.rstrip() + "\n") if text.strip() else ""
        return base + f"## {heading}\n\n{body}\n"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = HEADING_LINE_RE.match(lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    block = [lines[start], ""]
    if body:
        block.extend(body.splitlines())
        block.append("")
    return ensure_trailing_newline("\n".join(lines[:start] + block + lines[end:]).rstrip() + "\n")


def with_workflow_notes(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    payload["workflow_notes"] = read_workflow_notes(root)
    return payload


def format_scope_table(scope: dict[str, Any] | None = None) -> str:
    header = "| 逻辑库 | 路径 | 角色 |\n|--------|------|------|"
    rows: list[str] = []
    role_zh = {"must": "必须", "suggested": "建议", "excluded": "排除"}
    if scope:
        for role in ("must", "suggested", "excluded"):
            for item in scope.get(role, []):
                name = item.get("name") or item.get("path") or ""
                path = item.get("path") or ""
                rows.append(f"| {name} | `{path}` | {role_zh[role]} |")
    if not rows:
        return (
            f"{header}\n"
            "| （待补） | `path/to/repo`（仅工作区自身是目标时才写 `.`） | 必须 / 建议 / 排除 |"
        )
    return header + "\n" + "\n".join(rows)


def scope_has_rows(scope: dict[str, Any] | None) -> bool:
    if not scope:
        return False
    return bool(scope.get("must") or scope.get("suggested") or scope.get("excluded"))


def rel_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def strip_md_link(cell: str) -> str:
    cell = cell.strip()
    m = MD_LINK_RE.fullmatch(cell)
    if m:
        return m.group(2).strip()
    return cell


def normalize_task_path(raw: str) -> str:
    p = strip_md_link(raw).strip().strip("`")
    if p.startswith("./"):
        p = "tasks/" + p[2:]
    p = p.rstrip("/")
    if p.startswith("tasks/"):
        return p + "/"
    if re.match(r"^\d{4}-\d{2}-\d{2}/", p):
        return "tasks/" + p.rstrip("/") + "/"
    return p.rstrip("/") + "/"


def dirname_of_task_path(path: str) -> str:
    return Path(path.rstrip("/")).name


def slug_from_dirname(dirname: str) -> str:
    m = DIR_ID_SLUG_RE.match(dirname)
    if m:
        return m.group(2).lower()
    return dirname.lower()


def id_from_dirname(dirname: str) -> str | None:
    m = DIR_ID_SLUG_RE.match(dirname)
    if m:
        return normalize_id(m.group(1))
    return None


def parse_status_from_readme(text: str) -> str:
    m = FM_STATUS_RE.search(text)
    if m:
        return m.group(2).strip().lower()
    m = STATUS_LINE_RE.search(text)
    if m:
        return m.group(2).strip().lower()
    return "draft"


def parse_id_from_readme(text: str) -> str | None:
    m = FM_ID_RE.search(text)
    if m:
        raw = m.group(2).strip()
        if ID_RE.match(raw):
            return normalize_id(raw)
    m = META_ID_RE.search(text)
    if m:
        return normalize_id(m.group(1))
    return None


def parse_openspec(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s*关联\s*OpenSpec", line, re.IGNORECASE):
            start = i + 1
            break
    if start is None:
        return []
    rows: list[dict[str, str]] = []
    in_table = False
    table_header: list[str] = []
    for line in lines[start:]:
        if re.match(r"^#{2,3}\s+", line):
            break
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells:
                continue
            if cells[0].lower() in {"change", "名称", "name"}:
                in_table = True
                table_header = [c.lower() for c in cells]
                continue
            if set(cells[0]) <= {"-", ":"}:
                in_table = True
                continue
            if not in_table:
                continue
            name = strip_md_link(cells[0]).strip("`")
            path = strip_md_link(cells[1]).strip("`") if len(cells) > 1 else ""
            if name and name not in {"—", "-", "（尚无）"}:
                repo_idx = next(
                    (i for i, h in enumerate(table_header) if h in {"仓库", "repo"}),
                    None,
                )
                store_idx = next(
                    (i for i, h in enumerate(table_header) if h == "store"),
                    None,
                )
                repo = (
                    strip_md_link(cells[repo_idx]).strip("`")
                    if repo_idx is not None and repo_idx < len(cells)
                    else ""
                )
                store = (
                    strip_md_link(cells[store_idx]).strip("`")
                    if store_idx is not None and store_idx < len(cells)
                    else ""
                )
                rows.append(
                    {
                        "name": name,
                        "path": path,
                        "repo": normalize_repo_path(repo) if repo and repo not in {"—", "-"} else "",
                        "store": store if store not in {"—", "-"} else "",
                    }
                )
        elif in_table and line.strip() == "":
            break
    return rows


def parse_work_context(text: str) -> list[dict[str, Any]]:
    """Parse README 工作上下文, accepting both legacy and current tables."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s*工作上下文\s*$", line):
            start = i + 1
            break
    if start is None:
        return []
    rows: list[dict[str, Any]] = []
    header: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(set(c) <= {"-", ":"} for c in cells):
            continue
        if cells[0] in {"仓库", "repo"}:
            header = cells
            continue
        if cells[0] in _SCOPE_SKIP_NAMES:
            continue
        # Current: repo | canonical | checkout | worktree | branch | base.
        # Legacy:  repo | path      | worktree | branch   | base.
        if len(cells) >= 6:
            name, canonical, checkout, wt_raw, branch, base = cells[:6]
        elif len(cells) >= 5:
            name, canonical, wt_raw, branch, base = cells[:5]
            checkout = canonical
        else:
            continue
        canonical = strip_md_link(canonical).strip("`")
        checkout = strip_md_link(checkout).strip("`")
        if not canonical:
            continue
        rows.append(
            {
                "name": name.strip("`"),
                "repo": normalize_repo_path(canonical),
                "checkout": checkout or canonical,
                "is_worktree": wt_raw.strip().lower()
                in {"是", "yes", "true", "linked", "worktree"},
                "branch": branch.strip("`"),
                "base": base.strip("`"),
            }
        )
    return rows


_SCOPE_SKIP_NAMES = {"", "—", "-", "（待补）", "(待补)", "待补", "（尚无）"}
_SCOPE_ROLE_MUST = {"必须", "must", "required", "target"}
_SCOPE_ROLE_SUGGESTED = {"建议", "suggested", "optional"}
_SCOPE_ROLE_EXCLUDED = {"排除", "exclude", "excluded"}


def normalize_scope_role(raw: str) -> str | None:
    key = raw.strip().strip("`")
    low = key.lower()
    if key in _SCOPE_ROLE_MUST or low in _SCOPE_ROLE_MUST:
        return "must"
    if key in _SCOPE_ROLE_SUGGESTED or low in _SCOPE_ROLE_SUGGESTED:
        return "suggested"
    if key in _SCOPE_ROLE_EXCLUDED or low in _SCOPE_ROLE_EXCLUDED:
        return "excluded"
    return None


def _is_placeholder_scope_row(name: str, path: str, role: str) -> bool:
    if name in _SCOPE_SKIP_NAMES:
        return True
    if path in _SCOPE_SKIP_NAMES:
        return True
    if "path/to" in path or "或" in path:
        return True
    if "必须" in role and "建议" in role:
        return True
    return False


def parse_scope(text: str) -> dict[str, Any]:
    """Parse README 「涉及面」 or notes 「默认涉及面」 table. checkout = must only."""
    scope = empty_scope()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s*(?:默认)?涉及面", line):
            start = i + 1
            break
    if start is None:
        return scope
    in_table = False
    seen_checkout: set[str] = set()
    for line in lines[start:]:
        if re.match(r"^#{2,3}\s+", line):
            break
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells:
                continue
            head = cells[0].lower()
            if set(cells[0]) <= {"-", ":"} or head in {"逻辑库", "仓库", "库", "name", "repo"}:
                in_table = True
                continue
            if not in_table:
                continue
            name = strip_md_link(cells[0]).strip("`")
            path = strip_md_link(cells[1]).strip("`") if len(cells) > 1 else ""
            role_raw = cells[2] if len(cells) > 2 else "必须"
            if _is_placeholder_scope_row(name, path, role_raw):
                continue
            role = normalize_scope_role(role_raw) or "must"
            logical = normalize_repo_path(path) if path else ""
            if not logical:
                continue
            row = {"name": name, "path": logical, "role": role}
            scope[role].append(row)
            if role == "must" and logical not in seen_checkout:
                seen_checkout.add(logical)
                scope["checkout"].append(logical)
        elif in_table and line.strip() == "":
            break
    return scope


def read_readme_info(root: Path, task_root: Path) -> tuple[str, str, list[dict[str, str]]]:
    readme = task_root / "README.md"
    if not readme.is_file():
        raise TaskError(f"missing README.md under {rel_posix(root, task_root)}")
    text = readme.read_text(encoding="utf-8")
    status = parse_status_from_readme(text)
    task_id = parse_id_from_readme(text) or id_from_dirname(task_root.name) or ""
    return task_id, status, parse_openspec(text)


def scan_active_tasks(root: Path) -> list[TaskRow]:
    tasks_dir = root / "tasks"
    rows: list[TaskRow] = []
    if not tasks_dir.is_dir():
        return rows
    for readme in sorted(tasks_dir.glob("*/*/README.md")):
        if "archive" in readme.parts:
            continue
        task_root = readme.parent
        rel = rel_posix(root, task_root) + "/"
        text = readme.read_text(encoding="utf-8")
        status = parse_status_from_readme(text)
        if status == "archived":
            continue
        tid = parse_id_from_readme(text) or id_from_dirname(task_root.name)
        if not tid:
            # legacy unscanned id — skip allocating; use placeholder for listing only
            tid = f"LEGACY-{task_root.name}"
        rows.append(
            TaskRow(
                task_id=tid,
                name=slug_from_dirname(task_root.name),
                path=rel,
                status=status,
                updated="",
                section="active",
            )
        )
    return rows


def _parse_table_section(text: str, heading: str) -> list[list[str]]:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(rf"^##\s*{re.escape(heading)}\s*$", line):
            start = i + 1
            break
    if start is None:
        return []
    rows: list[list[str]] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() in {"id", "—"} or set(cells[0]) <= {"-", ":"}:
            # header or separator or empty placeholder row starting with —
            if cells[0] == "—" or cells[0] == "-":
                continue
            if cells[0].lower() == "id":
                continue
            if set(cells[0]) <= {"-", ":"}:
                continue
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        rows.append(cells)
    return rows


def parse_index(root: Path) -> tuple[int, list[TaskRow], list[TaskRow]]:
    path = index_path(root)
    if not path.is_file():
        active = scan_active_tasks(root)
        return 1, active, []

    text = path.read_text(encoding="utf-8")
    next_id = 1
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if fm:
        m = re.search(r"^next_id:\s*(\d+)\s*$", fm.group(1), re.MULTILINE)
        if m:
            next_id = int(m.group(1))

    active_rows: list[TaskRow] = []
    for cells in _parse_table_section(text, "活跃"):
        if len(cells) < 3:
            continue
        tid_raw = cells[0]
        if not ID_RE.match(tid_raw):
            continue
        tid = normalize_id(tid_raw)
        name = cells[1]
        path_cell = normalize_task_path(cells[2])
        status = cells[3].strip().lower() if len(cells) > 3 and cells[3] else "draft"
        updated = cells[4] if len(cells) > 4 else ""
        active_rows.append(
            TaskRow(
                task_id=tid,
                name=name,
                path=path_cell,
                status=status or "draft",
                updated=updated,
                section="active",
            )
        )

    archived_rows: list[TaskRow] = []
    for cells in _parse_table_section(text, "已归档"):
        if len(cells) < 3:
            continue
        tid_raw = cells[0]
        if tid_raw in {"—", "-", "（尚无）"} or not ID_RE.match(tid_raw):
            continue
        tid = normalize_id(tid_raw)
        name = cells[1]
        path_cell = normalize_task_path(cells[2])
        archived_on = cells[3] if len(cells) > 3 else ""
        archived_rows.append(
            TaskRow(
                task_id=tid,
                name=name,
                path=path_cell,
                status="archived",
                archived_on=archived_on,
                section="archived",
            )
        )

    return next_id, active_rows, archived_rows


def render_index(next_id: int, active: list[TaskRow], archived: list[TaskRow]) -> str:
    lines = [
        "---",
        f"next_id: {next_id}",
        "---",
        "",
        "# Tasks Index",
        "",
        "L0 路由。`task-*` 用任务编号（`TNNNN`）快捷指定；详情见各任务 `README.md`。"
        "约定见 `task-workflow` skill。",
        "",
        "## 活跃",
        "",
        "| ID | 名称 | 路径 | status | 更新 |",
        "|----|------|------|--------|------|",
    ]
    if active:
        for r in sorted(active, key=lambda x: x.task_id):
            link = f"[{r.path}](./{r.path.removeprefix('tasks/')})"
            lines.append(
                f"| {r.task_id} | {r.name} | {link} | {r.status or 'draft'} | {r.updated} |"
            )
    else:
        lines.append("| — | （尚无） | | | |")

    lines.extend(
        [
            "",
            "## 已归档",
            "",
            "| ID | 名称 | 路径 | 归档日 |",
            "|----|------|------|--------|",
        ]
    )
    if archived:
        for r in sorted(archived, key=lambda x: x.task_id):
            link = f"[{r.path}](./{r.path.removeprefix('tasks/')})"
            lines.append(f"| {r.task_id} | {r.name} | {link} | {r.archived_on} |")
    else:
        lines.append("| — | （尚无） | | |")

    lines.append("")
    return "\n".join(lines)


def write_index(root: Path, next_id: int, active: list[TaskRow], archived: list[TaskRow]) -> None:
    path = index_path(root)
    atomic_write_text(path, render_index(next_id, active, archived))


def resolve_task_root(root: Path, row: TaskRow) -> Path:
    rel = row.path.rstrip("/")
    path = root / rel
    if not path.is_dir():
        # try link target from INDEX relative form
        alt = root / "tasks" / rel.removeprefix("tasks/")
        if alt.is_dir():
            path = alt
    return path


def enrich_row(root: Path, row: TaskRow) -> TaskInfo | None:
    task_root = resolve_task_root(root, row)
    if not task_root.is_dir():
        return None
    readme = task_root / "README.md"
    if not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8")
    status = parse_status_from_readme(text) or row.status or "draft"
    if status == "archived" or "archive" in task_root.parts:
        return None
    tid = parse_id_from_readme(text) or row.task_id
    if ID_RE.match(tid):
        tid = normalize_id(tid)
    slug = slug_from_dirname(task_root.name)
    return TaskInfo(
        task_id=tid,
        task_root=rel_posix(root, task_root) + "/",
        slug=slug,
        name=row.name or slug,
        status=status,
        readme=rel_posix(root, readme),
        openspec=parse_openspec(text),
        scope=parse_scope(text),
        checkouts=parse_work_context(text),
        index_path=rel_posix(root, index_path(root)) if index_path(root).exists() else "",
        updated=row.updated,
    )


def list_active_infos(root: Path) -> list[TaskInfo]:
    _, active, _ = parse_index(root)
    if not active:
        active = scan_active_tasks(root)
    infos: list[TaskInfo] = []
    for row in active:
        info = enrich_row(root, row)
        if info:
            infos.append(info)
    return infos


def match_query(infos: list[TaskInfo], query: str) -> list[TaskInfo]:
    q = query.strip().rstrip("/")
    if not q:
        return []

    # bare id
    if ID_RE.match(q):
        tid = normalize_id(q)
        return [i for i in infos if i.task_id == tid]

    # TNNNN-slug
    m = ID_SLUG_RE.match(q)
    if m:
        tid = normalize_id(m.group(1))
        slug = m.group(2).lower()
        return [i for i in infos if i.task_id == tid or i.slug == slug]

    # path forms
    path_q = q
    if path_q.startswith("./"):
        path_q = path_q[2:]
    if not path_q.startswith("tasks/") and re.search(r"\d{4}-\d{2}-\d{2}/", path_q):
        path_q = "tasks/" + path_q
    path_q = path_q.rstrip("/") + "/"
    path_hits = [i for i in infos if i.task_root.rstrip("/") == path_q.rstrip("/") or i.task_root.endswith("/" + Path(q).name + "/")]
    if path_hits:
        return path_hits

    # dirname or slug
    name = Path(q).name
    m2 = DIR_ID_SLUG_RE.match(name)
    if m2:
        tid = normalize_id(m2.group(1))
        slug = m2.group(2).lower()
        return [i for i in infos if i.task_id == tid or i.slug == slug]

    slug = name.lower()
    return [i for i in infos if i.slug == slug or Path(i.task_root.rstrip("/")).name.lower() == slug]


def exit_markdown(infos: list[TaskInfo], command: str = "task-explore") -> str:
    lines = [
        "## 无法确定当前任务",
        "",
        "未找到唯一对应的活跃任务。请先指定任务编号或路径再继续。",
        "",
        "**活跃任务：**",
    ]
    if infos:
        for i in infos:
            lines.append(f"- {i.task_id} — {i.task_root}  (status: {i.status})")
    else:
        lines.append("- （尚无）")
    lines.extend(
        [
            "",
            "**请指定方式：**",
            f"- `/{command} T0001`",
            "- `/task-propose T0001`",
            "- `/task-apply T0001`",
            "- `/task-archive T0001`",
            "",
            "尚无任务？先执行 `/task-new <描述>`。",
            "",
        ]
    )
    return "\n".join(lines)


def confirm_markdown(
    candidates: list[dict[str, Any]],
    command: str,
    *,
    title: str = "请确认当前任务",
) -> str:
    lines = [
        f"## {title}",
        "",
        "未指定唯一 Task ID/名称；以下为自动推断候选，**请选择其一后再继续**（勿猜测）。",
        "",
        "**候选：**",
    ]
    if not candidates:
        lines.append("- （无）")
    for c in candidates:
        task = c["task"]
        reasons = ", ".join(c.get("reasons") or [])
        conf = c.get("confidence", "heuristic")
        lines.append(
            f"- `{task['task_id']}` — {task['task_root']}  "
            f"(status: {task['status']}; confidence: {conf}; reasons: {reasons})"
        )
    lines.extend(
        [
            "",
            "**确认方式：**",
            f"- `/{command} <TNNNN>`",
            "",
            "或回复任务编号（如 `T0002`）。",
            "",
        ]
    )
    return "\n".join(lines)


def task_created_date(info: TaskInfo) -> str:
    parts = info.task_root.strip("/").split("/")
    # tasks/YYYY-MM-DD/...
    if len(parts) >= 2 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[1]):
        return parts[1]
    return info.updated or ""


def slug_from_git_branch(branch: str) -> str | None:
    b = branch.strip()
    m = BRANCH_SLUG_RE.match(b)
    if not m:
        return None
    return m.group(1).lower()


def extract_hint_queries(hint: str) -> list[str]:
    found: list[str] = []
    for m in HINT_ID_RE.finditer(hint or ""):
        found.append(f"T{int(m.group(1)):04d}")
    for m in HINT_PATH_RE.finditer(hint or ""):
        found.append(m.group(1).rstrip("/") + "/")
    # de-dupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for q in found:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def task_from_cwd(root: Path, cwd: Path | None) -> TaskInfo | None:
    if cwd is None:
        return None
    try:
        rel = cwd.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    parts = rel.split("/")
    if len(parts) < 3 or parts[0] != "tasks" or parts[1] == "archive":
        return None
    # tasks/<date>/<dirname>/...
    task_rel = "/".join(parts[:3]) + "/"
    infos = list_active_infos(root)
    hits = [i for i in infos if i.task_root.rstrip("/") == task_rel.rstrip("/")]
    if len(hits) == 1:
        return hits[0]
    # also match by dirname alone under that date
    dirname = parts[2]
    hits = [
        i
        for i in infos
        if Path(i.task_root.rstrip("/")).name == dirname
    ]
    return hits[0] if len(hits) == 1 else None


def candidate_dict(
    info: TaskInfo,
    *,
    confidence: str,
    reasons: list[str],
    score: int = 0,
) -> dict[str, Any]:
    return {
        "task": asdict(info),
        "confidence": confidence,
        "reasons": reasons,
        "score": score,
    }


def infer_task(
    root: Path,
    infos: list[TaskInfo],
    *,
    command: str,
    hint: str = "",
    cwd: Path | None = None,
    git_branch: str | None = None,
) -> dict[str, Any]:
    """Infer current task when query omitted.

    Deterministic → result unique (ok).
    Heuristic → needs_confirm (always ask user).
    """
    if not infos:
        return {
            "ok": False,
            "result": "zero",
            "confidence": "none",
            "candidates": [],
            "exit_markdown": exit_markdown([], command),
        }

    if len(infos) == 1:
        info = infos[0]
        return {
            "ok": True,
            "result": "unique",
            "confidence": "deterministic",
            "reason": "sole_active",
            "task": asdict(info),
            "candidates": [candidate_dict(info, confidence="deterministic", reasons=["sole_active"])],
        }

    # --- deterministic context ---
    for q in extract_hint_queries(hint):
        hits = match_query(infos, q)
        if len(hits) == 1:
            info = hits[0]
            reason = "hint_id" if ID_RE.match(q) else "hint_path"
            return {
                "ok": True,
                "result": "unique",
                "confidence": "deterministic",
                "reason": reason,
                "task": asdict(info),
                "candidates": [candidate_dict(info, confidence="deterministic", reasons=[reason])],
            }
        if len(hits) > 1:
            cands = [
                candidate_dict(h, confidence="deterministic", reasons=["hint_ambiguous"])
                for h in hits
            ]
            return {
                "ok": False,
                "result": "needs_confirm",
                "confidence": "deterministic",
                "reason": "hint_ambiguous",
                "candidates": cands,
                "exit_markdown": confirm_markdown(cands, command, title="提示命中多个任务"),
            }

    cwd_hit = task_from_cwd(root, cwd)
    if cwd_hit is not None:
        return {
            "ok": True,
            "result": "unique",
            "confidence": "deterministic",
            "reason": "cwd_task",
            "task": asdict(cwd_hit),
            "candidates": [
                candidate_dict(cwd_hit, confidence="deterministic", reasons=["cwd_task"])
            ],
        }

    if git_branch:
        slug = slug_from_git_branch(git_branch)
        if slug:
            hits = [i for i in infos if i.slug == slug]
            if len(hits) == 1:
                info = hits[0]
                return {
                    "ok": True,
                    "result": "unique",
                    "confidence": "deterministic",
                    "reason": "git_branch",
                    "task": asdict(info),
                    "candidates": [
                        candidate_dict(
                            info,
                            confidence="deterministic",
                            reasons=[f"git_branch:{git_branch}"],
                        )
                    ],
                }
            if len(hits) > 1:
                cands = [
                    candidate_dict(
                        h,
                        confidence="deterministic",
                        reasons=[f"git_branch:{git_branch}"],
                    )
                    for h in hits
                ]
                return {
                    "ok": False,
                    "result": "needs_confirm",
                    "confidence": "deterministic",
                    "reason": "git_branch_ambiguous",
                    "candidates": cands,
                    "exit_markdown": confirm_markdown(cands, command),
                }

    # --- non-deterministic heuristics (always confirm) ---
    prefer = COMMAND_STATUS_PREFER.get(command, ())
    ranked: list[dict[str, Any]] = []
    for info in infos:
        score = 0
        reasons: list[str] = []
        if info.status in prefer:
            # higher rank for earlier prefer entries
            rank = prefer.index(info.status)
            score += 1000 - rank * 10
            reasons.append(f"status:{info.status}")
        created = task_created_date(info)
        if created:
            # newer created date → higher
            try:
                score += int(created.replace("-", ""))
            except ValueError:
                pass
            reasons.append(f"created:{created}")
        if info.updated:
            reasons.append(f"updated:{info.updated}")
        if not reasons:
            reasons.append("active")
        ranked.append(
            candidate_dict(
                info,
                confidence="heuristic",
                reasons=reasons,
                score=score,
            )
        )

    ranked.sort(
        key=lambda c: (
            c["score"],
            c["task"]["updated"],
            c["task"]["task_id"],
        ),
        reverse=True,
    )

    # Prefer highlighting status-matching + latest at top; keep all for choice
    status_hits = [c for c in ranked if any(r.startswith("status:") for r in c["reasons"])]
    if status_hits:
        primary_reason = "status_prefer"
        status_ids = {c["task"]["task_id"] for c in status_hits}
        rest = [c for c in ranked if c["task"]["task_id"] not in status_ids]
        ordered = status_hits + rest
    else:
        primary_reason = "latest_created"
        ordered = ranked

    return {
        "ok": False,
        "result": "needs_confirm",
        "confidence": "heuristic",
        "reason": primary_reason,
        "candidates": ordered,
        "exit_markdown": confirm_markdown(ordered, command),
    }


def set_readme_status(text: str, status: str) -> str:
    if FM_STATUS_RE.search(text):
        return FM_STATUS_RE.sub(rf"\g<1>{status}", text, count=1)
    if STATUS_LINE_RE.search(text):
        return STATUS_LINE_RE.sub(rf"\g<1>{status}\g<3>", text, count=1)
    # insert after title or at top
    lines = text.splitlines()
    insert_at = 0
    if lines and lines[0].startswith("#"):
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, f"**status：** {status}")
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return f"**status：** {status}\n\n" + text


def update_active_index_row(
    root: Path,
    task_id: str,
    *,
    status: str | None = None,
    updated: str | None = None,
    name: str | None = None,
    path: str | None = None,
) -> None:
    next_id, active, archived = parse_index(root)
    found = False
    for row in active:
        if row.task_id == task_id:
            if status is not None:
                row.status = status
            if updated is not None:
                row.updated = updated
            if name is not None:
                row.name = name
            if path is not None:
                row.path = normalize_task_path(path)
            found = True
            break
    if not found:
        raise TaskError(f"task {task_id} not in INDEX active table")
    write_index(root, next_id, active, archived)


def scaffold_readme(
    *,
    task_id: str,
    slug: str,
    title: str,
    created: str,
    scope: dict[str, Any] | None = None,
) -> str:
    scope_table = format_scope_table(scope)
    return f"""# {title}

**id：** {task_id}
**status：** draft
**slug：** {slug}
**创建时间：** {created}

---

## 概述

（待补）

## 背景

（待补）

## 目标

1. （待补）

## 现状缺口

对照目标，写清「已有」与「仍缺」。未知项标「待确认」；无缺口时写「暂无（目标范围内现状已齐）」。

| # | 缺口 | 类型 | 说明 | 建议补齐 |
|---|------|------|------|----------|
| 1 | （待补） | 信息 / 实现 / 资产 / 配置 / 依赖确认 | （待补） | 追问 / explore / 调研 |

## 需求说明

### 涉及面

{scope_table}

### 关联 OpenSpec

| change | 路径 | 仓库 | store | 说明 |
|--------|------|------|-------|------|
| — | | | | （尚无） |

### 设计文档

| 文档 | 类型 | 归档落点 |
|------|------|----------|
| — | | （无；复杂任务经 task-design 写入 `design/`） |

## 工作上下文

事实一出现或变化就立刻改这里，不要等 archive。涉及面是计划范围；本节是实际执行环境。

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| （待补） | | | 未使用 | | |

## 验收标准

- [ ] （待补）

## 变更记录

| 日期 | 变更 |
|------|------|
| {created} | 创建任务，状态 draft |
"""


def run_git(repo: Path, *git_args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *git_args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def find_git_root(start: Path) -> Path | None:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return None


def inspect_git_checkout(root: Path, repo: Path) -> dict[str, Any]:
    """Detect a linked git worktree (`.git` file / git-dir ≠ common-dir)."""
    git_dir_r = run_git(repo, "rev-parse", "--absolute-git-dir")
    common_r = run_git(repo, "rev-parse", "--git-common-dir")
    git_dir = None
    if git_dir_r.returncode == 0 and git_dir_r.stdout.strip():
        git_dir = Path(git_dir_r.stdout.strip()).resolve()
    common = None
    common_raw = common_r.stdout.strip()
    if common_r.returncode == 0 and common_raw:
        common = Path(common_raw)
        if not common.is_absolute():
            common = (repo / common).resolve()
        else:
            common = common.resolve()
    is_worktree = bool(git_dir and common and git_dir != common)
    main_rel = None
    if is_worktree and common is not None:
        main_abs = common.parent if common.name == ".git" else common
        try:
            main_rel = rel_posix(root, main_abs)
            if main_rel in ("", "."):
                main_rel = "."
        except ValueError:
            main_rel = str(main_abs)
    return {"is_worktree": is_worktree, "main_worktree": main_rel}


def git_common_dir(repo: Path) -> Path | None:
    r = run_git(repo, "rev-parse", "--git-common-dir")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    path = Path(r.stdout.strip())
    return (path if path.is_absolute() else repo / path).resolve()


def same_git_repository(left: Path, right: Path) -> bool:
    left_common = git_common_dir(left)
    right_common = git_common_dir(right)
    return bool(left_common and right_common and left_common == right_common)


def resolve_checkout_path(root: Path, raw: str) -> Path:
    """Resolve a recorded checkout path; unlike canonical repos it may be outside root."""
    value = raw.strip().strip("`")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def display_checkout_path(root: Path, path: Path) -> str:
    try:
        rel = rel_posix(root, path)
        return "." if rel in {"", "."} else rel
    except ValueError:
        return str(path.resolve())


def list_worktrees(repo: Path) -> list[dict[str, str]]:
    r = run_git(repo, "worktree", "list", "--porcelain")
    if r.returncode != 0:
        return []
    out: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*r.stdout.splitlines(), ""]:
        if not line.strip():
            if current.get("path"):
                out.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "HEAD":
            current["head"] = value
        elif key == "bare":
            current["bare"] = "true"
    return out


def find_worktree_for_branch(repo: Path, branch: str) -> Path | None:
    for item in list_worktrees(repo):
        if item.get("branch") == branch and item.get("path"):
            path = Path(item["path"]).resolve()
            if path.is_dir():
                return path
    return None


def binding_for_repo(info: TaskInfo | None, repo_path: str) -> dict[str, Any] | None:
    if info is None:
        return None
    key = normalize_repo_path(repo_path)
    for binding in info.checkouts:
        if normalize_repo_path(str(binding.get("repo") or "")) == key:
            return binding
    return None


def format_work_context(rows: list[dict[str, Any]]) -> str:
    lines = [
        "事实一出现或变化就立刻改这里，不要等 archive。涉及面是计划范围；本节是实际执行环境。",
        "",
        "| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |",
        "|------|----------|---------------|----------|------|------|",
    ]
    if not rows:
        lines.append("| — | | | 未使用 | | |")
        return "\n".join(lines)
    for row in rows:
        lines.append(
            "| {name} | `{repo}` | `{checkout}` | {worktree} | `{branch}` | `{base}` |".format(
                name=row.get("name") or row.get("repo") or "repo",
                repo=row.get("repo") or "",
                checkout=row.get("checkout") or row.get("repo") or "",
                worktree="是" if row.get("is_worktree") else "否",
                branch=row.get("branch") or "",
                base=row.get("base") or "",
            )
        )
    return "\n".join(lines)


def _persist_work_context_unlocked(
    root: Path, task_id: str, updates: list[dict[str, Any]]
) -> None:
    infos = list_active_infos(root)
    matches = match_query(infos, task_id)
    if len(matches) != 1:
        raise TaskError(f"cannot persist work context: task not unique: {task_id}")
    info = matches[0]
    merged = {normalize_repo_path(str(r.get("repo") or "")): dict(r) for r in info.checkouts}
    for row in updates:
        key = normalize_repo_path(str(row.get("repo") or ""))
        if key:
            merged[key] = {**merged.get(key, {}), **row}
    readme = root / info.readme
    text = readme.read_text(encoding="utf-8")
    updated = upsert_markdown_section(text, "工作上下文", format_work_context(list(merged.values())))
    atomic_write_text(readme, updated)


def persist_work_context(root: Path, task_id: str, updates: list[dict[str, Any]]) -> None:
    with index_lock(root):
        _persist_work_context_unlocked(root, task_id, updates)


def normalize_repo_path(raw: str) -> str:
    p = raw.strip().strip("`").rstrip("/")
    if p.startswith("./"):
        p = p[2:]
    if p in ("", "."):
        return "."
    return p


def resolve_repo(root: Path, raw: str) -> dict[str, Any]:
    """Map a workspace-relative path to its git root (`.` = workspace itself)."""
    logical = normalize_repo_path(raw)
    root_res = root.resolve()
    if Path(logical).is_absolute():
        raise TaskError(f"repo path must be workspace-relative: {raw}")

    abs_path = (root_res / logical).resolve()
    try:
        abs_path.relative_to(root_res)
    except ValueError as e:
        raise TaskError(f"path is outside workspace: {raw}") from e
    if not abs_path.exists():
        raise TaskError(f"path does not exist: {logical}")

    git_root = find_git_root(abs_path if abs_path.is_dir() else abs_path.parent)
    if git_root is None:
        raise TaskError(f"no .git found for: {logical}")
    try:
        git_root.relative_to(root_res)
    except ValueError as e:
        raise TaskError(f"git root escapes workspace: {logical}") from e

    git_rel = rel_posix(root_res, git_root)
    git_rel_out = "./" if git_rel == "." else git_rel.rstrip("/") + "/"
    rel_parts = git_rel_out.strip("./").split("/") if git_rel_out not in {".", "./"} else []

    checkout = inspect_git_checkout(root_res, git_root)
    return {
        "input": logical,
        "git_root": git_rel_out,
        "git_root_abs": str(git_root),
        "excluded_by_default": any(m in rel_parts for m in DEFAULT_EXCLUDE_REPO_MARKERS),
        "is_worktree": checkout["is_worktree"],
        "main_worktree": checkout["main_worktree"],
    }


def detect_base_branch(repo: Path, preferred: str | None = None) -> str:
    """Resolve the repo default branch — often not main/master."""
    if preferred:
        return preferred

    # Refresh origin/HEAD when remote available (best-effort).
    run_git(repo, "remote", "set-head", "origin", "-a")

    sym = run_git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if sym.returncode == 0:
        ref = sym.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref.removeprefix("refs/remotes/origin/")

    show = run_git(repo, "remote", "show", "origin")
    if show.returncode == 0:
        for line in show.stdout.splitlines():
            m = re.search(r"HEAD branch:\s*(\S+)", line)
            if m and m.group(1) not in {"(unknown)", "N/A"}:
                return m.group(1)

    for name in ("main", "master", "develop", "trunk"):
        if run_git(repo, "rev-parse", "--verify", f"refs/remotes/origin/{name}").returncode == 0:
            return name
        if run_git(repo, "rev-parse", "--verify", f"refs/heads/{name}").returncode == 0:
            return name

    raise TaskError(f"cannot detect default/base branch in {repo}")


def current_branch(repo: Path) -> str:
    r = run_git(repo, "branch", "--show-current")
    return r.stdout.strip()


def dirty_porcelain(repo: Path, *, limit: int = 20) -> list[str]:
    r = run_git(repo, "status", "--porcelain")
    return [ln for ln in r.stdout.splitlines() if ln.strip()][:limit]


def is_dirty(repo: Path) -> bool:
    return bool(dirty_porcelain(repo, limit=1))


def blocked_dirty_entry(entry: dict[str, Any], repo: Path) -> dict[str, Any]:
    entry["action"] = "blocked_dirty"
    entry["dirty"] = True
    entry["needs_user_confirm"] = True
    entry["dirty_porcelain"] = dirty_porcelain(repo)
    entry["error"] = "working tree has uncommitted changes; stop for user confirmation"
    entry["user_actions"] = list(DIRTY_USER_ACTIONS)
    return entry


def blocked_pull_entry(entry: dict[str, Any], stderr: str) -> dict[str, Any]:
    entry["action"] = "blocked_pull"
    entry["needs_user_confirm"] = True
    entry["error"] = f"failed to ff-only pull default branch: {stderr or 'unknown'}"
    entry["user_actions"] = [
        {
            "id": "manual_align",
            "label": "在该仓手动对齐默认分支后重试（禁止 agent 擅自 stash/reset --hard）",
        },
        {"id": "abort", "label": "中止本次 task-apply"},
    ]
    return entry


def repo_display_path(git_root_rel: str, file_path: str) -> str:
    """Prefix in-repo file paths with the git root relative path for changes.md."""
    base = git_root_rel.rstrip("/")
    fp = file_path.strip().lstrip("./")
    if base in ("", "."):
        return fp or "."
    if not fp:
        return base
    return f"{base}/{fp}"


def cwd_checkout_report(
    root: Path,
    cwd: Path | None,
    target_abs: set[str],
) -> dict[str, Any]:
    """Report whether the current working repo is in the checkout set.

    Unrelated cwd git roots must stay untouched.
    """
    start = (cwd or Path.cwd()).resolve()
    git = find_git_root(start)
    report: dict[str, Any] = {
        "cwd": str(start),
        "cwd_git_root": None,
        "cwd_in_targets": False,
        "cwd_untouched": True,
    }
    if git is None:
        return report
    git_abs = str(git.resolve())
    try:
        rel = rel_posix(root, git)
        report["cwd_git_root"] = "." if rel in ("", ".") else rel
    except ValueError:
        report["cwd_git_root"] = git_abs
    in_targets = git_abs in target_abs
    report["cwd_in_targets"] = in_targets
    report["cwd_untouched"] = not in_targets
    return report


def collect_prepare_repo_inputs(
    root: Path, args: argparse.Namespace
) -> tuple[list[str], dict[str, Any] | None]:
    """`--from-task` supplies must-repos; `--repo` is explicit extra/override paths.

    Never infers cwd or `.`. Empty checkout is a successful skip.
    """
    extras: dict[str, Any] = {}
    raw: list[str] = list(args.repos or [])
    if args.from_task:
        infos = list_active_infos(root)
        matches = match_query(infos, args.from_task)
        if len(matches) != 1:
            payload = {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(
                    infos if not matches else matches, "prepare-branches"
                ),
            }
            return [], payload
        extras["from_task"] = matches[0].task_id
        extras["from_task_checkout"] = list(matches[0].scope.get("checkout") or [])
        raw.extend(extras["from_task_checkout"])
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        key = normalize_repo_path(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out, extras if extras else None


def cmd_scope_repos(root: Path, args: argparse.Namespace) -> int:
    infos = list_active_infos(root)
    matches = match_query(infos, args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(
                    infos if not matches else matches, "scope-repos"
                ),
            },
            code=2,
        )
    info = matches[0]
    checkout = list(info.scope.get("checkout") or [])
    target_abs: set[str] = set()
    resolved = []
    errors = []
    for raw in checkout:
        try:
            repo_info = resolve_repo(root, raw)
            target_abs.add(str(Path(repo_info["git_root_abs"]).resolve()))
            resolved.append(repo_info)
        except TaskError as e:
            errors.append({"input": raw, "error": str(e)})
    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    report = cwd_checkout_report(root, cwd, target_abs)
    print(
        f"scope-repos: {info.task_id} checkout={len(checkout)} cwd_untouched={report['cwd_untouched']}",
        file=sys.stderr,
    )
    return emit(
        {
            "ok": not errors,
            "result": "scope_repos",
            "task": asdict(info),
            "scope": info.scope,
            "checkout": checkout,
            "repos": resolved,
            "errors": errors,
            **report,
        },
        code=0 if not errors else 1,
    )


def cmd_repo_roots(root: Path, args: argparse.Namespace) -> int:
    repos = []
    errors = []
    seen: set[str] = set()
    for raw in args.repos:
        try:
            info = resolve_repo(root, raw)
            key = info["git_root"]
            if key in seen:
                continue
            seen.add(key)
            if info["excluded_by_default"] and not args.include_excluded:
                errors.append({"input": raw, "error": f"excluded by default ({key}); pass --include-excluded"})
                continue
            repos.append(info)
        except TaskError as e:
            errors.append({"input": raw, "error": str(e)})
    ok = not errors
    return emit({"ok": ok, "result": "repo_roots", "repos": repos, "errors": errors}, code=0 if ok else 1)


def cmd_prepare_branches(root: Path, args: argparse.Namespace) -> int:
    slug = validate_slug(args.slug)
    prefix = (args.prefix or "feat").strip().lower()
    if prefix not in VALID_BRANCH_PREFIXES:
        raise TaskError(f"invalid prefix: {prefix}; expected one of {', '.join(VALID_BRANCH_PREFIXES)}")
    branch = f"{prefix}-{slug}"
    explicit_worktrees: dict[str, str] = {}
    for raw_mapping in getattr(args, "worktrees", None) or []:
        repo_key, sep, checkout = raw_mapping.partition("=")
        if not sep or not repo_key.strip() or not checkout.strip():
            raise TaskError("--worktree expects REPO=CHECKOUT_PATH")
        explicit_worktrees[normalize_repo_path(repo_key)] = checkout.strip()

    raw_repos, extra = collect_prepare_repo_inputs(root, args)
    if extra and extra.get("ok") is False:
        return emit(extra, code=2)
    if not raw_repos:
        if not args.from_task:
            raise TaskError(
                "pass --repo for each must-modify git root, or --from-task; "
                "do not default to cwd or `.`"
            )
        cwd = Path(args.cwd) if getattr(args, "cwd", None) else Path.cwd()
        report = cwd_checkout_report(root, cwd, set())
        print(
            f"prepare-branches: {branch} — skipped (no must-modify repos)",
            file=sys.stderr,
        )
        payload = {
            "ok": True,
            "result": "prepare_branches",
            "branch": branch,
            "prefix": prefix,
            "slug": slug,
            "dry_run": bool(args.dry_run),
            "skipped": "no_target_repos",
            "repos": [],
            "errors": [],
            "needs_user_confirm": False,
            **(extra or {}),
            **report,
        }
        return emit(payload)

    task_info: TaskInfo | None = None
    if args.from_task:
        matches = match_query(list_active_infos(root), args.from_task)
        if len(matches) == 1:
            task_info = matches[0]

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    target_abs: set[str] = set()

    for raw in raw_repos:
        try:
            info = resolve_repo(root, raw)
        except TaskError as e:
            errors.append({"input": raw, "error": str(e), "action": "error"})
            continue
        if info["excluded_by_default"] and not args.include_excluded:
            errors.append(
                {
                    "input": raw,
                    "git_root": info["git_root"],
                    "error": "excluded by default; pass --include-excluded",
                    "action": "excluded",
                }
            )
            continue
        key = info["git_root"]
        if key in seen:
            continue
        seen.add(key)
        target_abs.add(str(Path(info["git_root_abs"]).resolve()))

        canonical_repo = Path(info["git_root_abs"])
        canonical_key = normalize_repo_path(info["git_root"].rstrip("/"))
        recorded = binding_for_repo(task_info, canonical_key)
        explicit_checkout = explicit_worktrees.get(normalize_repo_path(raw))
        if explicit_checkout is None:
            explicit_checkout = explicit_worktrees.get(canonical_key)
        create_worktree = False
        selected_repo = canonical_repo
        if explicit_checkout:
            selected_repo = resolve_checkout_path(root, explicit_checkout)
            create_worktree = not selected_repo.exists()
        elif recorded and recorded.get("checkout"):
            candidate = resolve_checkout_path(root, str(recorded["checkout"]))
            if candidate.is_dir() and same_git_repository(canonical_repo, candidate):
                selected_repo = candidate
        else:
            branch_worktree = find_worktree_for_branch(canonical_repo, branch)
            if branch_worktree is not None:
                selected_repo = branch_worktree
        target_abs.add(str(selected_repo.resolve()))

        entry: dict[str, Any] = {
            "input": raw,
            "git_root": info["git_root"],
            "branch": branch,
            "action": "pending",
            "checkout": display_checkout_path(root, selected_repo),
            "checkout_abs": str(selected_repo),
        }
        try:
            if selected_repo.exists() and not same_git_repository(canonical_repo, selected_repo):
                raise TaskError(
                    f"checkout does not belong to canonical repo {info['git_root']}: {selected_repo}"
                )
            checkout_info = (
                inspect_git_checkout(root, selected_repo)
                if selected_repo.exists()
                else {"is_worktree": True, "main_worktree": info["git_root"].rstrip("/")}
            )
            entry.update(checkout_info)
            repo = selected_repo
            if create_worktree:
                # Branch and remote preparation happen below against canonical_repo.
                cur = ""
            else:
                cur = current_branch(repo)
            entry["current_branch"] = cur
            if cur == branch:
                # Continuing on the task branch: dirty WIP is expected.
                entry["action"] = "already_on_branch"
                entry["base"] = (recorded or {}).get("base") or args.base or ""
                if is_dirty(repo):
                    entry["dirty"] = True
                results.append(entry)
                continue

            if not create_worktree and is_dirty(repo):
                if args.skip_dirty:
                    entry["action"] = "skipped_dirty"
                    entry["dirty"] = True
                    entry["dirty_porcelain"] = dirty_porcelain(repo)
                    results.append(entry)
                    continue
                errors.append(blocked_dirty_entry(entry, repo))
                continue

            # Detect and refresh the canonical repository before mutating a checkout.
            base = detect_base_branch(canonical_repo, args.base)
            entry["base"] = base
            entry["base_source"] = "explicit" if args.base else "default_branch"

            if args.dry_run:
                entry["action"] = "would_create"
                entry["plan"] = [
                    "fetch origin (when configured)",
                    (
                        f"git worktree add -b {branch} {selected_repo} origin/{base}"
                        if create_worktree
                        else f"switch/create {branch} from origin/{base}"
                    ),
                ]
                results.append(entry)
                continue

            remotes = run_git(canonical_repo, "remote").stdout.split()
            has_origin = "origin" in remotes
            if has_origin:
                fetch = run_git(canonical_repo, "fetch", "origin")
                entry["fetch_ok"] = fetch.returncode == 0
                if fetch.returncode != 0:
                    tail = (fetch.stderr or "").strip().splitlines()
                    entry["action"] = "blocked_fetch"
                    entry["error"] = (
                        "failed to refresh configured origin: "
                        + (tail[-1] if tail else "unknown")
                    )
                    entry["needs_user_confirm"] = True
                    errors.append(entry)
                    continue
                if not args.base:
                    base = detect_base_branch(canonical_repo, None)
                    entry["base"] = base
            has_origin_base = (
                has_origin
                and run_git(
                    canonical_repo, "rev-parse", "--verify", f"origin/{base}"
                ).returncode
                == 0
            )
            start_ref = f"origin/{base}" if has_origin_base else base
            if (
                run_git(canonical_repo, "rev-parse", "--verify", start_ref).returncode
                != 0
            ):
                raise TaskError(f"base ref not found: {start_ref}")

            exists = (
                run_git(canonical_repo, "rev-parse", "--verify", f"refs/heads/{branch}")
                .returncode
                == 0
            )
            if create_worktree:
                selected_repo.parent.mkdir(parents=True, exist_ok=True)
                wt_args = ["worktree", "add"]
                if not exists:
                    wt_args.extend(["-b", branch])
                wt_args.extend([str(selected_repo), branch if exists else start_ref])
                created = run_git(canonical_repo, *wt_args)
                if created.returncode != 0:
                    raise TaskError(
                        (created.stderr or created.stdout or "git worktree add failed").strip()
                    )
                repo = selected_repo
                entry["action"] = "created_worktree"
                entry.update(inspect_git_checkout(root, repo))
            elif exists:
                occupied = find_worktree_for_branch(canonical_repo, branch)
                if occupied is not None and occupied.resolve() != repo.resolve():
                    # Route to the checkout that already owns the branch.
                    repo = occupied
                    entry["checkout"] = display_checkout_path(root, repo)
                    entry["checkout_abs"] = str(repo)
                    entry.update(inspect_git_checkout(root, repo))
                    entry["action"] = "routed_existing_worktree"
                else:
                    sw = run_git(repo, "switch", branch)
                    if sw.returncode != 0:
                        raise TaskError((sw.stderr or "switch existing branch failed").strip())
                    entry["action"] = "checked_out_existing"
            else:
                sw = run_git(repo, "switch", "-c", branch, start_ref)
                if sw.returncode != 0:
                    raise TaskError((sw.stderr or "switch -c failed").strip())
                entry["action"] = "created"

            entry["current_branch"] = current_branch(repo)
            results.append(entry)
        except TaskError as e:
            entry["action"] = "error"
            entry["error"] = str(e)
            entry["needs_user_confirm"] = True
            errors.append(entry)

    if args.from_task and results and not args.dry_run:
        persist_work_context(
            root,
            args.from_task,
            [
                {
                    "name": row.get("git_root", "").rstrip("/") or "workspace",
                    "repo": normalize_repo_path(row.get("git_root", "").rstrip("/")),
                    "checkout": row.get("checkout") or row.get("git_root", "").rstrip("/"),
                    "is_worktree": bool(row.get("is_worktree")),
                    "branch": row.get("branch") or "",
                    "base": row.get("base") or "",
                }
                for row in results
            ],
        )

    ok = not errors
    needs_confirm = any(e.get("needs_user_confirm") for e in errors)
    confirm_lines = [
        "## 分支准备需要你确认",
        "",
        "继续本任务前须先基于**远端默认分支**拉最新并检出 task 分支；下列仓库被阻断：",
        "",
    ]
    for e in errors:
        confirm_lines.append(
            f"- `{e.get('git_root', e.get('input'))}` — {e.get('action')}: {e.get('error', '')}"
        )
        for act in e.get("user_actions") or []:
            confirm_lines.append(f"  - [{act.get('id')}] {act.get('label')}")
        for line in e.get("dirty_porcelain") or []:
            confirm_lines.append(f"  - `{line}`")
    confirm_lines.extend(
        [
            "",
            "Agent **不得**擅自 `stash` / `reset --hard` / `checkout -f`；等你明确指示后再继续。",
            "",
        ]
    )

    print(
        f"prepare-branches: {branch} — ok={len(results)} blocked={len(errors)}"
        + (" (dry-run)" if args.dry_run else ""),
        file=sys.stderr,
    )
    cwd = Path(args.cwd) if getattr(args, "cwd", None) else Path.cwd()
    report = cwd_checkout_report(root, cwd, target_abs)
    payload: dict[str, Any] = {
        "ok": ok,
        "result": "prepare_branches",
        "branch": branch,
        "prefix": prefix,
        "slug": slug,
        "dry_run": bool(args.dry_run),
        "repos": results,
        "errors": errors,
        "needs_user_confirm": needs_confirm,
        **(extra or {}),
        **report,
    }
    if needs_confirm:
        payload["exit_markdown"] = "\n".join(confirm_lines)
    return emit(payload, code=0 if ok else 1)


def cmd_git_summary(root: Path, args: argparse.Namespace) -> int:
    max_commits = max(1, int(args.max_commits))
    max_files = max(1, int(args.max_files))
    repos_out: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    md_parts: list[str] = ["## 代码变更摘要（taskctl 生成，请人工核对）", ""]
    checkout_map: dict[str, str] = {}
    for raw_mapping in getattr(args, "checkouts", None) or []:
        repo_key, sep, checkout = raw_mapping.partition("=")
        if not sep:
            raise TaskError("--checkout expects REPO=CHECKOUT_PATH")
        checkout_map[normalize_repo_path(repo_key)] = checkout

    for raw in args.repos:
        try:
            info = resolve_repo(root, raw)
        except TaskError as e:
            errors.append({"input": raw, "error": str(e)})
            continue
        if info["excluded_by_default"] and not args.include_excluded:
            errors.append({"input": raw, "error": f"excluded by default ({info['git_root']})"})
            continue
        key = info["git_root"]
        if key in seen:
            continue
        seen.add(key)

        canonical_repo = Path(info["git_root_abs"])
        canonical_key = normalize_repo_path(key.rstrip("/"))
        repo = canonical_repo
        checkout_raw = checkout_map.get(normalize_repo_path(raw)) or checkout_map.get(
            canonical_key
        )
        if checkout_raw:
            repo = resolve_checkout_path(root, checkout_raw)
            if not repo.is_dir() or not same_git_repository(canonical_repo, repo):
                errors.append(
                    {
                        "input": raw,
                        "git_root": key,
                        "error": f"invalid checkout for canonical repo: {checkout_raw}",
                    }
                )
                continue
        cur = current_branch(repo)
        branch = args.branch or cur
        try:
            base = detect_base_branch(repo, args.base)
        except TaskError as e:
            errors.append({"input": raw, "git_root": key, "error": str(e)})
            continue

        range_spec = f"{base}...{branch}"
        # Prefer origin/base for range when available
        if run_git(repo, "rev-parse", "--verify", f"origin/{base}").returncode == 0:
            range_spec = f"origin/{base}...{branch}"

        log = run_git(
            repo,
            "log",
            "--oneline",
            f"--max-count={max_commits}",
            range_spec,
        )
        commits: list[dict[str, str]] = []
        if log.returncode == 0:
            for line in log.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                sha, _, subject = line.partition(" ")
                commits.append({"sha": sha, "subject": subject})
        else:
            # branch may not exist yet — fall back empty
            commits = []

        name_status = run_git(
            repo,
            "diff",
            "--name-status",
            range_spec,
        )
        files: list[dict[str, str]] = []
        seen_files: set[tuple[str, str]] = set()
        if name_status.returncode == 0:
            for line in name_status.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                status = parts[0]
                path = parts[-1]
                files.append(
                    {
                        "status": status,
                        "path": path,
                        "repo_path": repo_display_path(key, path),
                        "source": "committed",
                    }
                )
                seen_files.add((status, path))
                if len(files) >= max_files:
                    break

        for diff_args, source in (
            (("diff", "--name-status"), "working_tree"),
            (("diff", "--cached", "--name-status"), "staged"),
        ):
            dirty_names = run_git(repo, *diff_args)
            if dirty_names.returncode != 0:
                continue
            for line in dirty_names.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                status, path = parts[0], parts[-1]
                if (status, path) in seen_files:
                    continue
                files.append(
                    {
                        "status": status,
                        "path": path,
                        "repo_path": repo_display_path(key, path),
                        "source": source,
                    }
                )
                seen_files.add((status, path))
                if len(files) >= max_files:
                    break
        status_out = run_git(repo, "status", "--porcelain")
        if status_out.returncode == 0:
            for line in status_out.stdout.splitlines():
                if len(line) < 4:
                    continue
                status = line[:2].strip() or "M"
                path = line[3:].strip()
                if (status, path) in seen_files or any(
                    existing["path"] == path for existing in files
                ):
                    continue
                files.append(
                    {
                        "status": status,
                        "path": path,
                        "repo_path": repo_display_path(key, path),
                        "source": "untracked" if status == "??" else "working_tree",
                    }
                )
                if len(files) >= max_files:
                    break

        stat = run_git(repo, "diff", "--stat", range_spec)
        stat_text = stat.stdout.strip() if stat.returncode == 0 else ""

        entry = {
            "input": raw,
            "git_root": key,
            "checkout": display_checkout_path(root, repo),
            "is_worktree": inspect_git_checkout(root, repo)["is_worktree"],
            "branch": branch,
            "base": base,
            "range": range_spec,
            "current_branch": cur,
            "dirty": is_dirty(repo),
            "commits": commits,
            "files": files,
            "stat": stat_text,
        }
        repos_out.append(entry)

        md_parts.append(f"### `{key.rstrip('/')}`")
        md_parts.append("")
        md_parts.append(f"- branch: `{branch}`")
        md_parts.append(f"- base range: `{range_spec}`")
        if entry["dirty"]:
            md_parts.append("- dirty: yes（只读摘要，未 stash/reset）")
        md_parts.append("")
        md_parts.append("#### Commits")
        md_parts.append("")
        if commits:
            for c in commits:
                md_parts.append(f"- `{c['sha']}` {c['subject']}")
        else:
            md_parts.append("- （无提交或无法解析 range — 待核对）")
        md_parts.append("")
        md_parts.append("#### Files")
        md_parts.append("")
        if files:
            for f in files:
                md_parts.append(
                    f"- `{f['status']}` `{f['repo_path']}` ({f.get('source', 'committed')})"
                )
        else:
            md_parts.append("- （无文件变更或无法解析 range — 待核对）")
        md_parts.append("")
        if stat_text:
            md_parts.append("```")
            md_parts.append(stat_text)
            md_parts.append("```")
            md_parts.append("")

    ok = not errors and bool(repos_out)
    if not repos_out and not errors:
        raise TaskError("no --repo provided")
    return emit(
        {
            "ok": ok,
            "result": "git_summary",
            "repos": repos_out,
            "errors": errors,
            "markdown": "\n".join(md_parts).rstrip() + "\n",
        },
        code=0 if ok else 1,
    )


def resolve_change_target(
    root: Path, info: TaskInfo, change: dict[str, str]
) -> dict[str, Any]:
    raw_repo = (change.get("repo") or "").strip()
    repo_key = normalize_repo_path(raw_repo) if raw_repo else ""
    binding = binding_for_repo(info, repo_key) if repo_key else None
    if repo_key:
        canonical_info = resolve_repo(root, repo_key)
        canonical_repo = Path(canonical_info["git_root_abs"])
        if binding and binding.get("checkout"):
            checkout = resolve_checkout_path(root, str(binding["checkout"]))
            if not checkout.is_dir():
                raise TaskError(
                    f"recorded checkout missing for {repo_key}: {checkout}"
                )
            if not same_git_repository(canonical_repo, checkout):
                raise TaskError(
                    f"recorded checkout is not the canonical repository {repo_key}: "
                    f"{checkout}"
                )
        else:
            checkout = canonical_repo
    else:
        checkout = root
    raw_path = (change.get("path") or "").strip().strip("`").rstrip("/")
    if raw_path and Path(raw_path).is_absolute():
        raise TaskError(
            f"OpenSpec path must be canonical-repo/workspace relative: {raw_path}"
        )
    relative = raw_path
    if repo_key and relative:
        normalized = normalize_repo_path(relative)
        if normalized == repo_key:
            relative = ""
        elif normalized.startswith(repo_key.rstrip("/") + "/"):
            relative = normalized[len(repo_key.rstrip("/")) + 1 :]
    change_root = (checkout / relative).resolve() if relative else checkout
    try:
        change_root.relative_to(checkout.resolve())
    except ValueError as e:
        raise TaskError(f"OpenSpec path escapes checkout: {raw_path}") from e
    planning_root = change_root
    for candidate in [change_root, *change_root.parents]:
        if candidate.name == "changes" and candidate.parent.name == "openspec":
            planning_root = candidate.parent
            break
        if candidate.name == "openspec":
            planning_root = candidate
            break
    return {
        **change,
        "repo": repo_key,
        "checkout": display_checkout_path(root, checkout),
        "checkout_abs": str(checkout),
        "change_root": str(change_root),
        "planning_root": str(planning_root),
    }


def classify_checkbox_item(text: str) -> str:
    return "verification" if VERIFICATION_ITEM_RE.search(text) else "implementation"


def parse_openspec_checkboxes(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for match in CHECKBOX_ITEM_RE.finditer(text):
        title = match.group(2).strip()
        items.append(
            {
                "text": title,
                "done": match.group(1).lower() == "x",
                "kind": classify_checkbox_item(title),
            }
        )
    return items


def remaining_kind_of(items: list[dict[str, Any]]) -> str:
    remaining = [item for item in items if not item["done"]]
    if not remaining:
        return "none"
    if all(item["kind"] == "verification" for item in remaining):
        return "verification_only"
    return "implementation"


def aggregate_remaining_kind(reports: list[dict[str, Any]]) -> str:
    kinds = {str(report.get("remaining_kind") or "none") for report in reports}
    kinds.discard("none")
    if "implementation" in kinds:
        return "implementation"
    if "verification_only" in kinds:
        return "verification_only"
    return "none"


def empty_openspec_report() -> dict[str, Any]:
    return {
        "total": 0,
        "complete": 0,
        "remaining": 0,
        "remaining_kind": "none",
        "remaining_items": [],
    }


def openspec_task_report(target: dict[str, Any]) -> dict[str, Any]:
    change_root = Path(target["change_root"])
    tasks = change_root / "tasks.md"
    if not tasks.is_file():
        return empty_openspec_report()
    items = parse_openspec_checkboxes(tasks.read_text(encoding="utf-8"))
    remaining_items = [item for item in items if not item["done"]]
    complete = sum(1 for item in items if item["done"])
    return {
        "total": len(items),
        "complete": complete,
        "remaining": len(remaining_items),
        "remaining_kind": remaining_kind_of(items),
        "remaining_items": remaining_items,
    }


def openspec_checkbox_progress(target: dict[str, Any]) -> dict[str, Any]:
    return openspec_task_report(target)


def inspect_change_remainder(target: dict[str, Any]) -> dict[str, Any]:
    name = str(target.get("name") or "")
    change_root = Path(target["change_root"])
    if change_root.exists():
        report = openspec_task_report(target)
        return {
            "name": name,
            "state": "active",
            "path": str(change_root),
            "message": (
                f"{name} (active path exists: {change_root}, "
                f"remaining={report['remaining']})"
            ),
            **report,
        }
    archived_paths = archived_change_paths(target)
    archive_root = Path(target["planning_root"]) / "changes" / "archive"
    if not archived_paths:
        return {
            "name": name,
            "state": "missing",
            "path": str(archive_root),
            "message": (
                f"{name} (recorded path missing and no archived change found "
                f"under {archive_root})"
            ),
            "total": 0,
            "complete": 0,
            "remaining": 1,
            "remaining_kind": "implementation",
            "remaining_items": [],
        }
    last_report = empty_openspec_report()
    for archived_path in archived_paths:
        report = openspec_task_report({**target, "change_root": str(archived_path)})
        last_report = report
        if report["remaining"]:
            return {
                "name": name,
                "state": "archived_incomplete",
                "path": str(archived_path),
                "message": (
                    f"{name} (archived at {archived_path} with "
                    f"remaining={report['remaining']})"
                ),
                **report,
            }
    return {
        "name": name,
        "state": "archived",
        "path": str(archived_paths[-1]),
        "message": "",
        **last_report,
    }


def verification_only_confirm_markdown(
    task_id: str, leftovers: list[dict[str, Any]]
) -> str:
    lines = [
        "## 只剩测试/验证，确认是否继续归档",
        "",
        f"{task_id} 的 OpenSpec 仍有未完成 checkbox，但全部判定为测试/验证。",
        "",
        "**剩余项：**",
    ]
    for row in leftovers:
        lines.append(f"- `{row['name']}` {row['complete']}/{row['total']}")
        for item in row.get("remaining_items") or []:
            lines.append(f"  - {item['text']}")
    lines.extend(
        [
            "",
            "**请选择：**",
            f"- 继续归档（强行合并）：`taskctl archive {task_id} --force-merge`",
            "- 先做完验证再归档",
            "- 中止",
            "",
            "未确认前 **不得** 继续 archive。",
            "",
        ]
    )
    return "\n".join(lines)


def archived_change_paths(target: dict[str, Any]) -> list[Path]:
    archive_root = Path(target["planning_root"]) / "changes" / "archive"
    if not archive_root.is_dir():
        return []
    name = str(target.get("name") or "")
    return sorted(
        p for p in archive_root.iterdir() if p.is_dir() and p.name.endswith(f"-{name}")
    )


def cmd_execution_context(root: Path, args: argparse.Namespace) -> int:
    matches = match_query(list_active_infos(root), args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(matches, "task-apply"),
            },
            code=2,
        )
    info = matches[0]
    targets = [resolve_change_target(root, info, row) for row in info.openspec]
    remaining_items: list[dict[str, Any]] = []
    for target in targets:
        progress = openspec_checkbox_progress(target)
        target["progress"] = progress
        target["remaining_kind"] = progress["remaining_kind"]
        target["remaining_items"] = progress["remaining_items"]
        for item in progress["remaining_items"]:
            remaining_items.append({"change": target.get("name") or "", **item})
    progress_path = root / info.task_root.rstrip("/") / "progress.md"
    complete = sum(int(t["progress"]["complete"]) for t in targets)
    total = sum(int(t["progress"]["total"]) for t in targets)
    return emit(
        {
            "ok": True,
            "result": "execution_context",
            "task": asdict(info),
            "targets": targets,
            "openspec_remaining": {
                "kind": aggregate_remaining_kind(targets),
                "complete": complete,
                "total": total,
                "remaining": total - complete,
                "items": remaining_items,
            },
            "progress_path": rel_posix(root, progress_path),
            "progress_exists": progress_path.is_file(),
            "progress_markdown": (
                progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
            ),
        }
    )


def _cmd_checkpoint_unlocked(root: Path, args: argparse.Namespace) -> int:
    matches = match_query(list_active_infos(root), args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(matches, "task-apply"),
            },
            code=2,
        )
    info = matches[0]
    phase = args.phase
    status = "blocked" if phase == "blocked" else "in_progress"
    task_readme = root / info.readme
    original_readme = task_readme.read_text(encoding="utf-8")
    task_index = index_path(root)
    original_index = (
        task_index.read_text(encoding="utf-8") if task_index.is_file() else None
    )
    targets = [resolve_change_target(root, info, row) for row in info.openspec]
    progress_path = root / info.task_root.rstrip("/") / "progress.md"
    previous_text = (
        progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
    )
    progress_existed = progress_path.is_file()

    def previous_items(heading: str) -> list[str]:
        body = next(
            (
                section["body"]
                for section in parse_markdown_sections(previous_text)
                if normalize_heading(section["heading"]) == normalize_heading(heading)
            ),
            "",
        )
        return [
            m.group(1).strip()
            for m in re.finditer(r"^\s*-\s+(.+?)\s*$", body, re.MULTILINE)
            if m.group(1).strip() not in {"（无）", "（尚无）"}
        ]

    completed_items = list(
        dict.fromkeys([*previous_items("本轮完成"), *(args.completed or [])])
    )
    verification_items = list(
        dict.fromkeys([*previous_items("验证证据"), *(args.verification or [])])
    )
    snapshots: list[dict[str, Any]] = []
    for binding in info.checkouts:
        canonical = Path(
            resolve_repo(root, str(binding["repo"]))["git_root_abs"]
        )
        checkout = resolve_checkout_path(root, str(binding.get("checkout") or binding["repo"]))
        if not checkout.is_dir() or not same_git_repository(canonical, checkout):
            raise TaskError(
                f"missing/invalid recorded checkout for {binding['repo']}: {checkout}"
            )
        snapshots.append(
            {
                **binding,
                "current_branch": current_branch(checkout),
                "dirty": is_dirty(checkout),
                "dirty_porcelain": dirty_porcelain(checkout),
            }
        )
    lines = [
        f"# {info.task_id} 实施进度",
        "",
        f"- 更新：{args.date or today_str()}",
        f"- 阶段：`{phase}`",
        f"- 当前 change：`{args.change or '—'}`",
        f"- 当前任务：{args.current_task or '—'}",
        "",
        "## OpenSpec 进度",
        "",
        "| change | 完成 | 总数 | 剩余 | planning root |",
        "|--------|------|------|------|---------------|",
    ]
    for target in targets:
        progress = openspec_checkbox_progress(target)
        lines.append(
            f"| `{target['name']}` | {progress['complete']} | {progress['total']} | "
            f"{progress['remaining']} | `{target['planning_root']}` |"
        )
    lines.extend(["", "## 本轮完成", ""])
    lines.extend(f"- {item}" for item in completed_items)
    if not completed_items:
        lines.append("- （无）")
    lines.extend(["", "## 验证证据", ""])
    lines.extend(f"- {item}" for item in verification_items)
    if not verification_items:
        lines.append("- （尚无）")
    lines.extend(
        [
            "",
            "## 阻塞",
            "",
            f"- {args.blocker or '无'}",
            "",
            "## 下一步",
            "",
            f"- {args.next_step or '继续下一个未完成 OpenSpec task'}",
            "",
            "## Git 快照",
            "",
        ]
    )
    for snap in snapshots:
        lines.append(
            f"- `{snap.get('repo')}` checkout=`{snap.get('checkout')}` "
            f"branch=`{snap.get('current_branch', snap.get('branch', ''))}` "
            f"dirty={'yes' if snap.get('dirty') else 'no'}"
        )
        for dirty in snap.get("dirty_porcelain") or []:
            lines.append(f"  - `{dirty}`")
    try:
        atomic_write_text(progress_path, "\n".join(lines).rstrip() + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            status_code = _cmd_set_status_unlocked(
                root,
                argparse.Namespace(query=info.task_id, status=status, date=args.date),
            )
        if status_code != 0:
            raise TaskError(f"failed to persist checkpoint status for {info.task_id}")
    except Exception:
        with contextlib.suppress(Exception):
            atomic_write_text(task_readme, original_readme)
            if original_index is None:
                task_index.unlink(missing_ok=True)
            else:
                atomic_write_text(task_index, original_index)
            if progress_existed:
                atomic_write_text(progress_path, previous_text)
            else:
                progress_path.unlink(missing_ok=True)
        raise
    return emit(
        {
            "ok": True,
            "result": "checkpointed",
            "task_id": info.task_id,
            "phase": phase,
            "status": status,
            "progress_path": rel_posix(root, progress_path),
            "targets": targets,
        }
    )


def cmd_checkpoint(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        return _cmd_checkpoint_unlocked(root, args)


def cmd_list(root: Path, args: argparse.Namespace) -> int:
    infos = list_active_infos(root)
    if args.archived:
        _, _, archived = parse_index(root)
        payload = {
            "ok": True,
            "result": "archived",
            "tasks": [asdict(r) for r in archived],
        }
        return emit(payload)
    payload = {
        "ok": True,
        "result": "active",
        "tasks": [asdict(i) for i in infos],
    }
    return emit(payload)


def cmd_resolve(root: Path, args: argparse.Namespace) -> int:
    infos = list_active_infos(root)
    command = args.command
    query = (args.query or "").strip()

    # Explicit query path (deterministic when unique).
    if query:
        matches = match_query(infos, query)
        if len(matches) == 1:
            info = matches[0]
            print(f"当前任务：{info.task_id} — {info.task_root}", file=sys.stderr)
            return emit(
                with_workflow_notes(
                    root,
                    {
                        "ok": True,
                        "result": "unique",
                        "confidence": "deterministic",
                        "reason": "explicit_query",
                        "task": asdict(info),
                    },
                )
            )
        result = "zero" if not matches else "multi"
        payload = with_workflow_notes(
            root,
            {
                "ok": False,
                "result": result,
                "confidence": "deterministic",
                "matches": [asdict(m) for m in matches],
                "active": [asdict(i) for i in infos],
                "exit_markdown": exit_markdown(infos if result == "zero" else matches, command),
            },
        )
        return emit(payload, code=2)

    # No query: auto-infer (optional --infer is implied when query omitted).
    cwd = Path(args.cwd).resolve() if getattr(args, "cwd", None) else None
    inferred = infer_task(
        root,
        infos,
        command=command,
        hint=getattr(args, "hint", "") or "",
        cwd=cwd,
        git_branch=getattr(args, "git_branch", None),
    )
    if inferred.get("ok") and inferred.get("result") == "unique":
        task = inferred["task"]
        print(
            f"当前任务：{task['task_id']} — {task['task_root']} "
            f"(infer:{inferred.get('reason')})",
            file=sys.stderr,
        )
        return emit(with_workflow_notes(root, inferred))

    # needs_confirm / zero
    print("任务推断需要确认", file=sys.stderr)
    return emit(with_workflow_notes(root, inferred), code=2)


def _cmd_set_status_unlocked(root: Path, args: argparse.Namespace) -> int:
    status = args.status.strip().lower()
    if status not in VALID_STATUSES:
        raise TaskError(f"invalid status: {status}; expected one of {', '.join(VALID_STATUSES)}")
    if status == "archived":
        raise TaskError("use `archive` subcommand to set archived (moves directory)")

    infos = list_active_infos(root)
    matches = match_query(infos, args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(infos if not matches else matches, "task-explore"),
            },
            code=2,
        )
    info = matches[0]
    readme = root / info.readme
    text = readme.read_text(encoding="utf-8")
    new_text = set_readme_status(text, status)
    if new_text != text:
        atomic_write_text(readme, new_text if new_text.endswith("\n") else new_text + "\n")
    updated = args.date or today_str()
    try:
        update_active_index_row(root, info.task_id, status=status, updated=updated)
    except TaskError:
        # INDEX missing row: append
        next_id, active, archived = parse_index(root)
        active.append(
            TaskRow(
                task_id=info.task_id,
                name=info.name,
                path=info.task_root,
                status=status,
                updated=updated,
            )
        )
        write_index(root, next_id, active, archived)

    info.status = status
    info.updated = updated
    print(f"已更新状态：{info.task_id} → {status}", file=sys.stderr)
    return emit({"ok": True, "result": "updated", "task": asdict(info)})


def cmd_set_status(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        return _cmd_set_status_unlocked(root, args)


def _cmd_new_unlocked(root: Path, args: argparse.Namespace) -> int:
    title = (args.title or "").strip()
    slug_arg = (getattr(args, "slug", None) or "").strip()
    if slug_arg:
        slug = validate_slug(slug_arg)
    elif title:
        slug = slugify_from_text(title)
    else:
        raise TaskError("new requires --slug or --title")
    if not title:
        title = slug
    created = args.date or today_str()
    next_id, active, archived = parse_index(root)

    # ensure legacy scanned tasks are registered when creating INDEX from scratch
    if not index_path(root).is_file():
        scanned = scan_active_tasks(root)
        known = {r.task_id for r in active}
        for row in scanned:
            if row.task_id.startswith("LEGACY-"):
                continue
            if row.task_id not in known:
                active.append(row)
                known.add(row.task_id)
        # bump next_id above max existing
        nums = [int(r.task_id[1:]) for r in active if ID_RE.match(r.task_id)]
        if nums:
            next_id = max(next_id, max(nums) + 1)

    task_id = f"T{next_id:04d}"
    dirname = f"{task_id}-{slug}"
    task_root = root / "tasks" / created / dirname
    rel = rel_posix(root, task_root) + "/"

    if any(r.task_id == task_id for r in active + archived):
        raise TaskError(f"task id already exists: {task_id}")
    if any(slug_from_dirname(Path(r.path.rstrip("/")).name) == slug for r in active):
        raise TaskError(f"active slug already exists: {slug}")
    if task_root.exists():
        raise TaskError(f"directory already exists: {rel}")

    notes = read_workflow_notes(root)
    scope = notes["scope"] if scope_has_rows(notes.get("scope")) else None

    if args.dry_run:
        return emit(
            with_workflow_notes(
                root,
                {
                    "ok": True,
                    "result": "dry_run",
                    "taskId": task_id,
                    "taskRoot": rel,
                    "next_id_after": next_id + 1,
                },
            )
        )

    task_root.mkdir(parents=True, exist_ok=False)
    readme = task_root / "README.md"
    try:
        atomic_write_text(
            readme,
            scaffold_readme(
                task_id=task_id,
                slug=slug,
                title=title,
                created=created,
                scope=scope,
            ),
        )
        active.append(
            TaskRow(
                task_id=task_id,
                name=slug,
                path=rel,
                status="draft",
                updated=created,
            )
        )
        write_index(root, next_id + 1, active, archived)
    except Exception:
        shutil.rmtree(task_root, ignore_errors=True)
        raise
    print(f"已创建任务：{task_id} — {rel}", file=sys.stderr)
    info = TaskInfo(
        task_id=task_id,
        task_root=rel,
        slug=slug,
        name=slug,
        status="draft",
        readme=rel_posix(root, readme),
        openspec=[],
        updated=created,
    )
    return emit(with_workflow_notes(root, {"ok": True, "result": "created", "task": asdict(info)}))


def cmd_new(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        return _cmd_new_unlocked(root, args)


def _cmd_archive_unlocked(root: Path, args: argparse.Namespace) -> int:
    infos = list_active_infos(root)
    matches = match_query(infos, args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "exit_markdown": exit_markdown(infos if not matches else matches, "task-archive"),
            },
            code=2,
        )
    info = matches[0]
    src = root / info.task_root.rstrip("/")
    if not src.is_dir():
        raise TaskError(f"task directory missing: {info.task_root}")

    changes = src / "changes.md"
    if not changes.is_file() and not args.allow_missing_changes:
        raise TaskError("missing changes.md; write it first or pass --allow-missing-changes")
    original_changes_text = (
        changes.read_text(encoding="utf-8") if changes.is_file() else None
    )

    override_notes: list[str] = []
    allow_remaining_openspec = bool(
        getattr(args, "allow_active_openspec", False)
        or getattr(args, "force_merge", False)
    )
    resolved_targets: list[dict[str, Any]] = []
    remainder_rows: list[dict[str, Any]] = []
    for change in info.openspec:
        target = resolve_change_target(root, info, change)
        resolved_targets.append(target)
        remainder_rows.append(inspect_change_remainder(target))
    blocking_rows = [
        row
        for row in remainder_rows
        if row["state"] in {"active", "missing", "archived_incomplete"}
    ]
    active_or_incomplete = [row["message"] for row in blocking_rows if row.get("message")]
    incomplete_rows = [
        row
        for row in blocking_rows
        if row["state"] == "missing" or row["remaining"] > 0
    ]
    verification_only = bool(incomplete_rows) and all(
        row["state"] != "missing" and row["remaining_kind"] == "verification_only"
        for row in incomplete_rows
    )
    if active_or_incomplete and not allow_remaining_openspec:
        if verification_only:
            print(
                f"只剩测试/验证：{info.task_id} — 确认是否强行合并归档",
                file=sys.stderr,
            )
            return emit(
                {
                    "ok": False,
                    "result": "needs_confirm",
                    "reason": "verification_only_remaining",
                    "taskId": info.task_id,
                    "remaining": incomplete_rows,
                    "exit_markdown": verification_only_confirm_markdown(
                        info.task_id, incomplete_rows
                    ),
                    "user_actions": [
                        {
                            "id": "force_merge",
                            "label": (
                                f"继续归档（强行合并）："
                                f"taskctl archive {info.task_id} --force-merge"
                            ),
                        },
                        {
                            "id": "finish_verification",
                            "label": "先做完验证再归档",
                        },
                        {"id": "abort", "label": "中止"},
                    ],
                },
                code=2,
            )
        raise TaskError(
            "active/incomplete OpenSpec changes remain: "
            + "; ".join(active_or_incomplete)
            + "; archive them first or pass --allow-active-openspec / --force-merge"
        )
    if active_or_incomplete:
        note_prefix = (
            "强行合并：" if getattr(args, "force_merge", False) else "允许遗留 OpenSpec："
        )
        override_notes.append(note_prefix + "; ".join(active_or_incomplete))

    readme = src / "README.md"
    original_text = readme.read_text(encoding="utf-8")
    acceptance = next(
        (
            s["body"]
            for s in parse_markdown_sections(original_text)
            if normalize_heading(s["heading"]) == "验收标准"
        ),
        "",
    )
    unchecked = len(re.findall(r"^\s*-\s*\[\s\]", acceptance, re.MULTILINE))
    if unchecked and not args.allow_unchecked_acceptance:
        raise TaskError(
            f"{unchecked} acceptance item(s) unchecked; complete them or pass "
            "--allow-unchecked-acceptance"
        )
    if unchecked:
        override_notes.append(f"允许 {unchecked} 项验收未勾选")

    progress_path = src / "progress.md"
    verification_ok = False
    if progress_path.is_file():
        progress_text = progress_path.read_text(encoding="utf-8")
        verification = next(
            (
                s["body"]
                for s in parse_markdown_sections(progress_text)
                if normalize_heading(s["heading"]) == "验证证据"
            ),
            "",
        )
        verification_ok = bool(
            verification
            and "（尚无）" not in verification
            and re.search(r"^\s*-\s+\S", verification, re.MULTILINE)
        )
    if not verification_ok and not args.allow_missing_verification:
        raise TaskError(
            "missing verification evidence in progress.md; checkpoint testing evidence "
            "or pass --allow-missing-verification"
        )
    if not verification_ok:
        override_notes.append("允许缺少验证证据")

    dirty_bindings: list[str] = []
    missing_bindings: list[str] = []
    repo_keys = {
        normalize_repo_path(str(row.get("path") or ""))
        for row in info.scope.get("must", [])
        if row.get("path")
    }
    repo_keys.update(
        normalize_repo_path(str(binding.get("repo") or ""))
        for binding in info.checkouts
        if binding.get("repo")
    )
    repo_keys.update(
        normalize_repo_path(str(target.get("repo") or ""))
        for target in resolved_targets
        if target.get("repo")
    )
    if any(not target.get("repo") for target in resolved_targets):
        workspace_git = find_git_root(root)
        if workspace_git is not None and workspace_git.resolve() == root.resolve():
            repo_keys.add(".")
    for repo_key in sorted(repo_keys):
        canonical = Path(resolve_repo(root, repo_key)["git_root_abs"])
        binding = binding_for_repo(info, repo_key)
        checkout = (
            resolve_checkout_path(root, str(binding.get("checkout")))
            if binding and binding.get("checkout")
            else canonical
        )
        if not checkout.is_dir() or not same_git_repository(canonical, checkout):
            missing_bindings.append(f"{repo_key} -> {checkout}")
            continue
        if is_dirty(checkout):
            dirty_bindings.append(display_checkout_path(root, checkout))
    if missing_bindings and not args.allow_dirty:
        raise TaskError(
            "missing/invalid task checkout(s): "
            + ", ".join(missing_bindings)
            + "; restore bindings or pass --allow-dirty"
        )
    if missing_bindings:
        override_notes.append(
            "允许缺失 checkout：" + ", ".join(missing_bindings)
        )
    if dirty_bindings and not args.allow_dirty:
        raise TaskError(
            "dirty task checkout(s): "
            + ", ".join(dirty_bindings)
            + "; commit/clean them or pass --allow-dirty"
        )
    if dirty_bindings:
        override_notes.append("允许 dirty checkout：" + ", ".join(dirty_bindings))

    create_date = src.parent.name
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", create_date):
        create_date = args.date or today_str()
    dirname = src.name
    # ensure archive name has id prefix when possible
    if not DIR_ID_SLUG_RE.match(dirname) and ID_RE.match(info.task_id):
        dirname = f"{info.task_id}-{info.slug}"
    dest = root / "tasks" / "archive" / f"{create_date}-{dirname}"
    rel_dest = rel_posix(root, dest) + "/"

    if dest.exists():
        raise TaskError(f"archive destination exists: {rel_dest}")

    archived_on = args.date or today_str()

    if args.dry_run:
        return emit(
            {
                "ok": True,
                "result": "dry_run",
                "from": info.task_root,
                "to": rel_dest,
                "archived_on": archived_on,
            }
        )

    if override_notes and changes.is_file():
        changes_text = changes.read_text(encoding="utf-8").rstrip()
        changes_text += "\n\n## 归档门禁覆盖\n\n"
        changes_text += "\n".join(f"- {note}" for note in override_notes) + "\n"
        atomic_write_text(changes, changes_text)

    readme = src / "README.md"
    text = original_text
    archived_text = set_readme_status(text, "archived") + ("" if text.endswith("\n") else "\n")
    try:
        atomic_write_text(readme, archived_text)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        # prune empty date dir
        parent = src.parent
        if parent.is_dir() and parent.name != "tasks" and not any(parent.iterdir()):
            parent.rmdir()

        next_id, active, archived = parse_index(root)
        active = [r for r in active if r.task_id != info.task_id]
        archived = [r for r in archived if r.task_id != info.task_id]
        archived.append(
            TaskRow(
                task_id=info.task_id,
                name=info.name,
                path=rel_dest,
                status="archived",
                archived_on=archived_on,
                section="archived",
            )
        )
        write_index(root, next_id, active, archived)
    except Exception:
        with contextlib.suppress(Exception):
            if dest.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(src))
            if src.exists():
                atomic_write_text(src / "README.md", text)
                if original_changes_text is not None:
                    atomic_write_text(src / "changes.md", original_changes_text)
        raise
    print(f"已归档：{info.task_id} → {rel_dest}", file=sys.stderr)
    return emit(
        {
            "ok": True,
            "result": "archived",
            "taskId": info.task_id,
            "from": info.task_root,
            "to": rel_dest,
            "archived_on": archived_on,
        }
    )


def cmd_archive(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        return _cmd_archive_unlocked(root, args)


def cmd_notes(root: Path, args: argparse.Namespace) -> int:
    init = bool(getattr(args, "init", False))
    from_file = getattr(args, "from_file", None)
    set_section = getattr(args, "set_section", None)
    dry_run = bool(getattr(args, "dry_run", False))

    if sum(bool(x) for x in (init, from_file, set_section)) > 1:
        raise TaskError("use only one of --init / --from-file / --set-section")

    if init:
        current = read_workflow_notes(root)
        if current["exists"]:
            print("工作区笔记已存在，未覆盖", file=sys.stderr)
            return emit({"ok": True, "result": "exists", **current})
        markdown = scaffold_workflow_notes(root.name)
        if dry_run:
            return emit(
                {
                    "ok": True,
                    "result": "dry_run",
                    "action": "init",
                    "path": WORKFLOW_NOTES_REL,
                    "markdown": markdown,
                }
            )
        write_workflow_notes(root, markdown)
        print(f"已创建工作区笔记：{WORKFLOW_NOTES_REL}", file=sys.stderr)
        return emit({"ok": True, "result": "created", **read_workflow_notes(root)})

    if from_file:
        src = Path(from_file)
        if not src.is_file():
            raise TaskError(f"file not found: {from_file}")
        markdown = src.read_text(encoding="utf-8")
        if dry_run:
            return emit(
                {
                    "ok": True,
                    "result": "dry_run",
                    "action": "write",
                    "path": WORKFLOW_NOTES_REL,
                    "markdown": markdown,
                }
            )
        write_workflow_notes(root, markdown)
        print(f"已写入工作区笔记：{WORKFLOW_NOTES_REL}", file=sys.stderr)
        return emit({"ok": True, "result": "updated", **read_workflow_notes(root)})

    if set_section:
        body = (getattr(args, "body", None) or "").strip()
        body_file = getattr(args, "body_file", None)
        if body_file:
            bp = Path(body_file)
            if not bp.is_file():
                raise TaskError(f"file not found: {body_file}")
            body = bp.read_text(encoding="utf-8").strip()
        if not body:
            raise TaskError("--set-section requires --body or --body-file")
        current = read_workflow_notes(root)
        base = current["markdown"] if current["exists"] else scaffold_workflow_notes(root.name)
        markdown = upsert_markdown_section(base, set_section, body)
        created = not current["exists"]
        if dry_run:
            return emit(
                {
                    "ok": True,
                    "result": "dry_run",
                    "action": "set_section",
                    "created": created,
                    "path": WORKFLOW_NOTES_REL,
                    "heading": set_section,
                    "markdown": markdown,
                }
            )
        write_workflow_notes(root, markdown)
        print(
            f"{'已创建并写入' if created else '已更新'}工作区笔记：{WORKFLOW_NOTES_REL} / {set_section}",
            file=sys.stderr,
        )
        return emit(
            {
                "ok": True,
                "result": "created" if created else "updated",
                "heading": set_section,
                **read_workflow_notes(root),
            }
        )

    notes = read_workflow_notes(root)
    if notes["exists"]:
        print(f"已加载工作区笔记：{WORKFLOW_NOTES_REL}", file=sys.stderr)
    else:
        print("工作区尚无 .task-workflow.md", file=sys.stderr)
    return emit({"ok": True, "result": "missing" if not notes["exists"] else "loaded", **notes})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="workspace root containing tasks/ (default: auto-detect from cwd)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    list_p = sub.add_parser("list", help="list active (or archived) tasks as JSON")
    list_p.add_argument("--archived", action="store_true", help="list archived INDEX rows")
    list_p.set_defaults(func=cmd_list)

    resolve_p = sub.add_parser(
        "resolve",
        help="Task Resolution Gate (optional query → auto-infer)",
    )
    resolve_p.add_argument(
        "query",
        nargs="?",
        default="",
        help="TNNNN / slug / path; omit to auto-infer",
    )
    resolve_p.add_argument(
        "--command",
        default="task-explore",
        help="command name for status prefer + exit_markdown",
    )
    resolve_p.add_argument(
        "--hint",
        default="",
        help="user message / context text for deterministic hint extract",
    )
    resolve_p.add_argument(
        "--cwd",
        default=None,
        help="filesystem cwd for tasks/... path inference",
    )
    resolve_p.add_argument(
        "--git-branch",
        default=None,
        help="current git branch (feat-<slug>) for deterministic match",
    )
    resolve_p.add_argument(
        "--infer",
        action="store_true",
        help="accepted for clarity; inference runs whenever query is omitted",
    )
    resolve_p.set_defaults(func=cmd_resolve)

    status_p = sub.add_parser("set-status", help="update README + INDEX status")
    status_p.add_argument("query", help="TNNNN / slug / path")
    status_p.add_argument(
        "status", help="draft|exploring|designed|proposed|in_progress|blocked"
    )
    status_p.add_argument("--date", help="updated date YYYY-MM-DD (default: today)")
    status_p.set_defaults(func=cmd_set_status)

    new_p = sub.add_parser("new", help="allocate id, scaffold task dir, update INDEX")
    new_p.add_argument(
        "--slug",
        default="",
        help="kebab-case; omit to infer from --title (ASCII tokens)",
    )
    new_p.add_argument("--title", default="")
    new_p.add_argument("--date", help="create date YYYY-MM-DD (default: today)")
    new_p.add_argument("--dry-run", action="store_true")
    new_p.set_defaults(func=cmd_new)

    arch_p = sub.add_parser("archive", help="move task to archive/ and update INDEX")
    arch_p.add_argument("query", help="TNNNN / slug / path")
    arch_p.add_argument("--date", help="archived_on date YYYY-MM-DD (default: today)")
    arch_p.add_argument("--dry-run", action="store_true")
    arch_p.add_argument(
        "--allow-missing-changes",
        action="store_true",
        help="allow archive without changes.md",
    )
    arch_p.add_argument("--allow-active-openspec", action="store_true")
    arch_p.add_argument(
        "--force-merge",
        action="store_true",
        help="force-archive despite remaining OpenSpec tasks (强行合并)",
    )
    arch_p.add_argument("--allow-unchecked-acceptance", action="store_true")
    arch_p.add_argument("--allow-missing-verification", action="store_true")
    arch_p.add_argument("--allow-dirty", action="store_true")
    arch_p.set_defaults(func=cmd_archive)

    roots_p = sub.add_parser("repo-roots", help="resolve workspace-relative paths to unique git roots")
    roots_p.add_argument("repos", nargs="+", help="workspace-relative git path (`.` = workspace itself, only if it is a target)")
    roots_p.add_argument(
        "--include-excluded",
        action="store_true",
        help="allow roots matching default exclude markers (none by default)",
    )
    roots_p.set_defaults(func=cmd_repo_roots)

    scope_p = sub.add_parser(
        "scope-repos",
        help="list 涉及面 repos; checkout = 必须 only (never cwd)",
    )
    scope_p.add_argument("query", help="TNNNN / slug / path")
    scope_p.add_argument(
        "--cwd",
        default=None,
        help="path whose git root is reported; not added to checkout",
    )
    scope_p.set_defaults(func=cmd_scope_repos)

    prep_p = sub.add_parser(
        "prepare-branches",
        help="git safety check + create/checkout <prefix>-<slug> on must-modify git repos only",
    )
    prep_p.add_argument("--slug", required=True, help="task slug (not TNNNN dirname)")
    prep_p.add_argument(
        "--repo",
        dest="repos",
        action="append",
        default=None,
        help="must-modify git root (workspace-relative); repeatable. Do not pass cwd or `.` unless the workspace itself is a target",
    )
    prep_p.add_argument(
        "--worktree",
        dest="worktrees",
        action="append",
        default=None,
        metavar="REPO=CHECKOUT",
        help="explicit checkout/worktree for a canonical repo; creates it when missing",
    )
    prep_p.add_argument(
        "--from-task",
        default=None,
        help="load checkout list from task README 涉及面 (role=必须 only); skip if empty",
    )
    prep_p.add_argument(
        "--cwd",
        default=None,
        help="path whose git root is reported as cwd; never auto-checked-out",
    )
    prep_p.add_argument("--prefix", default="feat", help="feat|fix|chore|refactor")
    prep_p.add_argument("--base", default=None, help="base branch (default: origin/HEAD or main)")
    prep_p.add_argument("--dry-run", action="store_true")
    prep_p.add_argument(
        "--skip-dirty",
        action="store_true",
        help="skip dirty repos instead of failing them",
    )
    prep_p.add_argument(
        "--include-excluded",
        action="store_true",
        help="allow roots matching default exclude markers (none by default)",
    )
    prep_p.set_defaults(func=cmd_prepare_branches)

    sum_p = sub.add_parser(
        "git-summary",
        help="read-only git log/diff summary for changes.md scaffolding",
    )
    sum_p.add_argument(
        "--repo",
        dest="repos",
        action="append",
        required=True,
        help="workspace-relative git path; repeatable (`.` = workspace)",
    )
    sum_p.add_argument(
        "--checkout",
        dest="checkouts",
        action="append",
        default=None,
        metavar="REPO=CHECKOUT",
        help="actual checkout/worktree to summarize for a canonical repo",
    )
    sum_p.add_argument("--branch", default=None, help="feature branch (default: current)")
    sum_p.add_argument("--base", default=None, help="base branch name (default: detected)")
    sum_p.add_argument("--max-commits", type=int, default=30)
    sum_p.add_argument("--max-files", type=int, default=100)
    sum_p.add_argument(
        "--include-excluded",
        action="store_true",
        help="allow roots matching default exclude markers (none by default)",
    )
    sum_p.set_defaults(func=cmd_git_summary)

    context_p = sub.add_parser(
        "execution-context",
        help="resolve persisted checkout/worktree and OpenSpec execution targets",
    )
    context_p.add_argument("query", help="TNNNN / slug / path")
    context_p.set_defaults(func=cmd_execution_context)

    checkpoint_p = sub.add_parser(
        "checkpoint",
        help="persist task-apply phase, progress, blockers, next step, and git snapshot",
    )
    checkpoint_p.add_argument("query", help="TNNNN / slug / path")
    checkpoint_p.add_argument(
        "--phase",
        required=True,
        choices=("implementing", "testing", "blocked", "done"),
    )
    checkpoint_p.add_argument("--change", default="")
    checkpoint_p.add_argument("--current-task", default="")
    checkpoint_p.add_argument("--completed", action="append", default=[])
    checkpoint_p.add_argument("--verification", action="append", default=[])
    checkpoint_p.add_argument("--blocker", default="")
    checkpoint_p.add_argument("--next", dest="next_step", default="")
    checkpoint_p.add_argument("--date", default=None)
    checkpoint_p.set_defaults(func=cmd_checkpoint)

    notes_p = sub.add_parser(
        "notes",
        help="read/write workspace .task-workflow.md (standing requirements / specs)",
    )
    notes_p.add_argument(
        "--init",
        action="store_true",
        help="create skeleton if missing; never overwrite an existing file",
    )
    notes_p.add_argument(
        "--from-file",
        dest="from_file",
        help="replace the whole file with this markdown",
    )
    notes_p.add_argument(
        "--set-section",
        dest="set_section",
        help="upsert a ## / ### section (creates skeleton if file is missing)",
    )
    notes_p.add_argument("--body", default="", help="section body for --set-section")
    notes_p.add_argument(
        "--body-file",
        dest="body_file",
        help="read --set-section body from a file",
    )
    notes_p.add_argument("--dry-run", action="store_true")
    notes_p.set_defaults(func=cmd_notes)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = (args.root or find_repo_root()).resolve()
        if not (root / "tasks").exists():
            raise TaskError(f"tasks/ not found under {root}")
        return args.func(root, args)
    except TaskError as e:
        return emit({"ok": False, "error": str(e)}, code=e.code)
    except (OSError, UnicodeError, subprocess.SubprocessError) as e:
        return emit(
            {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "error_type": "io_or_process_error",
            },
            code=1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
