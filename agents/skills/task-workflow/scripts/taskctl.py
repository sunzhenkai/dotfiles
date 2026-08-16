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
  python3 scripts/taskctl.py execution-context T0002
  python3 scripts/taskctl.py advance T0002 --phase implementing
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
import difflib
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
import time
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
LOCK_DIR_ENV = "TASKCTL_LOCK_DIR"
LOCK_TIMEOUT_ENV = "TASKCTL_LOCK_TIMEOUT"
DEFAULT_LOCK_TIMEOUT = 30.0
LOCK_POLL_SECONDS = 0.2
LOCK_STALE_SECONDS = 7 * 24 * 3600
GIT_TIMEOUT_ENV = "TASKCTL_GIT_TIMEOUT"
DEFAULT_GIT_TIMEOUT = 15.0
DEFAULT_GIT_NETWORK_TIMEOUT = 60.0
GIT_TIMEOUT_RETURNCODE = 124
NON_INTERACTIVE_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "true",
    "SSH_ASKPASS": "true",
    "SSH_ASKPASS_REQUIRE": "never",
    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
    "GCM_INTERACTIVE": "never",
}
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
ARCHIVE_TASK_DIR_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})-(T\d{4}-.+)$", re.IGNORECASE
)
APPLY_STATE_FILENAME = ".task-apply-state.json"
APPLY_STATE_VERSION = 1
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
STATUS_LINE_RE = re.compile(
    r"^(\*\*(?:status|状态)[：:]\*\*\s*)([A-Za-z_]+)(\s*)$",
    re.MULTILINE,
)
CHECKBOX_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s+(.+?)\s*$", re.MULTILINE)
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
    def __init__(
        self,
        message: str,
        code: int = 1,
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reason = reason
        self.details = details or {}


def rollback_or_raise(
    primary_error: Exception,
    actions: list[tuple[str, Any]],
    *,
    affected_paths: list[Path | str],
) -> None:
    """Run every rollback action and make restoration failures machine-visible."""
    rollback_errors: list[str] = []
    for label, action in actions:
        try:
            action()
        except Exception as exc:
            rollback_errors.append(f"{label}: {type(exc).__name__}: {exc}")
    if rollback_errors:
        paths = [str(path) for path in affected_paths]
        raise TaskError(
            f"mutation failed: {primary_error}; rollback_failed: "
            + "; ".join(rollback_errors),
            reason="rollback_failed",
            details={
                "primary_error": f"{type(primary_error).__name__}: {primary_error}",
                "rollback_errors": rollback_errors,
                "affected_paths": paths,
                "recovery_hint": "inspect affected paths and restore them from the pre-call state",
            },
        ) from primary_error
    raise primary_error


def taskctl_script_path() -> Path:
    return Path(__file__).resolve()


def taskctl_command(*args: str) -> str:
    """Render a hint the caller can paste and run.

    There is no `taskctl` executable on PATH, so every emitted command must use
    the script invocation form.
    """
    return " ".join(["python3", str(taskctl_script_path()), *args])


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
        raise TaskError(
            "cannot infer slug from title (non-ASCII title?); "
            "pass --slug with a short English kebab-case name"
        )
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


def positive_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise TaskError(f"invalid {name}: {raw}; expected a positive number") from None
    if value <= 0:
        raise TaskError(f"{name} must be > 0: {raw}")
    return value


def lock_dir() -> Path:
    override = os.environ.get(LOCK_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    cache_home = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
    return base / "taskctl" / "locks"


def prune_stale_locks(directory: Path, keep: Path) -> None:
    """Best-effort cleanup so long-lived machines stop accumulating lock files."""
    cutoff = time.time() - LOCK_STALE_SECONDS
    try:
        entries = list(directory.glob("taskctl-*.lock"))
    except OSError:
        return
    for entry in entries:
        if entry == keep:
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


@contextlib.contextmanager
def index_lock(root: Path):
    """Serialize task id allocation and archive index transitions.

    Acquisition polls a non-blocking lock under a bounded wall clock so a stuck
    holder surfaces a structured error with the holder pid instead of hanging
    the caller forever.
    """
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
    directory = lock_dir()
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / f"taskctl-{digest}.lock"
    prune_stale_locks(directory, lock_path)
    timeout = positive_float_env(LOCK_TIMEOUT_ENV, DEFAULT_LOCK_TIMEOUT)
    with lock_path.open("a+", encoding="utf-8") as lock:
        started = time.monotonic()
        while True:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                waited = time.monotonic() - started
                if waited >= timeout:
                    raise TaskError(
                        f"could not acquire taskctl workspace lock within {timeout:g}s",
                        reason="lock_timeout",
                        details={
                            "lock_path": str(lock_path),
                            "waited_seconds": round(waited, 2),
                            "holder": read_lock_holder(lock),
                            "recovery_hint": (
                                "another taskctl process holds this workspace lock; "
                                "inspect the holder pid and retry, or raise "
                                f"{LOCK_TIMEOUT_ENV}"
                            ),
                        },
                    ) from None
                time.sleep(min(LOCK_POLL_SECONDS, timeout - waited))
        write_lock_holder(lock)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_lock_holder(lock: io.TextIOWrapper) -> str:
    try:
        lock.seek(0)
        return lock.read().strip()
    except OSError:
        return ""


def write_lock_holder(lock: io.TextIOWrapper) -> None:
    try:
        lock.seek(0)
        lock.truncate()
        lock.write(f"pid={os.getpid()} acquired={today_str()}\n")
        lock.flush()
    except OSError:
        pass


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


def operational_error(section: str, line_no: int, line: str, detail: str) -> TaskError:
    return TaskError(
        f"malformed {section} at line {line_no}: {detail}: {line.strip()}",
        reason="malformed_operational_table",
        details={
            "diagnostic": {
                "section": section,
                "line": line_no,
                "source": line.strip()[:240],
                "detail": detail,
            }
        },
    )


def _find_section_start(lines: list[str], pattern: str) -> int | None:
    for i, line in enumerate(lines):
        if re.match(pattern, line, re.IGNORECASE):
            return i + 1
    return None


def parse_openspec(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = _find_section_start(lines, r"^#{2,3}\s*关联\s*OpenSpec")
    if start is None:
        return []
    rows: list[dict[str, str]] = []
    in_table = False
    header: list[str] = []
    for i in range(start, len(lines)):
        line = lines[i]
        if re.match(r"^#{2,3}\s+", line):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() in {"change", "名称", "name"}:
            in_table = True
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= {"-", ":"} for c in cells):
            in_table = True
            continue
        if not in_table:
            continue
        if len(cells) < 2:
            raise operational_error(
                "关联 OpenSpec", i + 1, line, "expected at least change and path columns"
            )
        name = strip_md_link(cells[0]).strip("`")
        if name in {"", "—", "-", "（尚无）"}:
            continue
        path = strip_md_link(cells[1]).strip("`")
        repo_idx = next((j for j, value in enumerate(header) if value in {"仓库", "repo"}), None)
        store_idx = next((j for j, value in enumerate(header) if value == "store"), None)
        order_idx = next(
            (j for j, value in enumerate(header) if value in {"顺序", "order"}), None
        )
        repo = strip_md_link(cells[repo_idx]).strip("`") if repo_idx is not None and repo_idx < len(cells) else ""
        store = strip_md_link(cells[store_idx]).strip("`") if store_idx is not None and store_idx < len(cells) else ""
        store = "" if store in {"—", "-"} else store
        if store:
            # Rejected where the association is recorded, not later during apply.
            raise TaskError(
                f"unsupported OpenSpec store for {name}: {store}",
                reason="unsupported_openspec_store",
                details={
                    "change": name,
                    "store": store,
                    "line": str(i + 1),
                    "diagnostic": {
                        "section": "关联 OpenSpec",
                        "line": i + 1,
                        "source": line.strip()[:240],
                        "detail": "standalone OpenSpec stores are not supported",
                    },
                },
            )
        order_raw = (
            strip_md_link(cells[order_idx]).strip("`")
            if order_idx is not None and order_idx < len(cells)
            else ""
        )
        rows.append(
            {
                "name": name,
                "path": path,
                "repo": normalize_repo_path(repo) if repo and repo not in {"—", "-"} else "",
                "store": store,
                "order": order_raw if order_raw not in {"—", "-"} else "",
                "line": str(i + 1),
            }
        )
    return rows


def parse_work_context(text: str) -> list[dict[str, Any]]:
    """Parse README 工作上下文 and reject malformed operational rows."""
    lines = text.splitlines()
    start = _find_section_start(lines, r"^##\s*工作上下文\s*$")
    if start is None:
        return []
    rows: list[dict[str, Any]] = []
    in_table = False
    for i in range(start, len(lines)):
        line = lines[i]
        if re.match(r"^#{2,3}\s+", line):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(set(c) <= {"-", ":"} for c in cells):
            continue
        if cells[0].lower() in {"仓库", "repo"}:
            in_table = True
            continue
        if cells[0] in _SCOPE_SKIP_NAMES or "apply 前" in cells[0]:
            continue
        if len(cells) >= 6:
            name, canonical, checkout, wt_raw, branch, base = cells[:6]
        elif len(cells) >= 5:
            name, canonical, wt_raw, branch, base = cells[:5]
            checkout = canonical
        else:
            if in_table:
                raise operational_error("工作上下文", i + 1, line, "expected five or six columns")
            continue
        canonical = strip_md_link(canonical).strip("`")
        checkout = strip_md_link(checkout).strip("`")
        if not canonical:
            raise operational_error("工作上下文", i + 1, line, "canonical repository is required")
        rows.append(
            {
                "name": name.strip("`"),
                "repo": normalize_repo_path(canonical),
                "checkout": checkout or canonical,
                "is_worktree": wt_raw.strip().lower() in {"是", "yes", "true", "linked", "worktree"},
                "branch": branch.strip("`"),
                "base": base.strip("`"),
                "line": i + 1,
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
    if name in _SCOPE_SKIP_NAMES or path in _SCOPE_SKIP_NAMES:
        return True
    if "path/to" in path or "或" in path:
        return True
    if "必须" in role and "建议" in role:
        return True
    return False


def parse_scope(text: str) -> dict[str, Any]:
    """Parse scope strictly. Unknown roles never become delivery repositories."""
    scope = empty_scope()
    lines = text.splitlines()
    start = _find_section_start(lines, r"^#{2,3}\s*(?:默认)?涉及面")
    if start is None:
        return scope
    in_table = False
    seen_checkout: set[str] = set()
    for i in range(start, len(lines)):
        line = lines[i]
        if re.match(r"^#{2,3}\s+", line):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        head = cells[0].lower()
        if all(set(c) <= {"-", ":"} for c in cells) or head in {"逻辑库", "仓库", "库", "name", "repo"}:
            in_table = True
            continue
        if not in_table:
            continue
        if len(cells) < 3:
            raise operational_error("涉及面", i + 1, line, "expected name, path, and role columns")
        name = strip_md_link(cells[0]).strip("`")
        path = strip_md_link(cells[1]).strip("`")
        role_raw = cells[2]
        if _is_placeholder_scope_row(name, path, role_raw):
            continue
        role = normalize_scope_role(role_raw)
        if role is None:
            raise operational_error("涉及面", i + 1, line, f"unknown scope role {role_raw!r}")
        logical = normalize_repo_path(path) if path else ""
        if not logical:
            raise operational_error("涉及面", i + 1, line, "repository path is required")
        row = {"name": name, "path": logical, "role": role, "line": i + 1}
        scope[role].append(row)
        if role == "must" and logical not in seen_checkout:
            seen_checkout.add(logical)
            scope["checkout"].append(logical)
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
    active = list(reconcile_task_catalog(root)["active"])
    infos: list[TaskInfo] = []
    for row in active:
        info = enrich_row(root, row)
        if info:
            infos.append(info)
    return infos


def scan_archived_tasks(root: Path) -> list[TaskRow]:
    archive_dir = root / "tasks" / "archive"
    rows: list[TaskRow] = []
    if not archive_dir.is_dir():
        return rows
    for readme in sorted(archive_dir.glob("*/README.md")):
        task_root = readme.parent
        text = readme.read_text(encoding="utf-8")
        tid = parse_id_from_readme(text)
        if not tid or not ID_RE.match(tid):
            continue
        archive_match = ARCHIVE_TASK_DIR_RE.match(task_root.name)
        original_name = archive_match.group(2) if archive_match else task_root.name
        rows.append(
            TaskRow(
                task_id=normalize_id(tid),
                name=slug_from_dirname(original_name),
                path=rel_posix(root, task_root) + "/",
                status="archived",
                archived_on=archive_match.group(1) if archive_match else "",
                section="archived",
            )
        )
    return rows


def reconcile_task_catalog(root: Path) -> dict[str, Any]:
    """Merge INDEX and task directories, reporting identity conflicts without mutation."""
    next_id, indexed_active, indexed_archived = parse_index(root)
    scanned_active = scan_active_tasks(root)
    scanned_archived = scan_archived_tasks(root)
    diagnostics: list[dict[str, Any]] = []

    def add(reason: str, **details: Any) -> None:
        diagnostics.append({"reason": reason, **details})

    scanned = [*scanned_active, *scanned_archived]
    by_id: dict[str, list[TaskRow]] = {}
    for row in scanned:
        if ID_RE.match(row.task_id):
            by_id.setdefault(normalize_id(row.task_id), []).append(row)
        readme = root / row.path.rstrip("/") / "README.md"
        text = readme.read_text(encoding="utf-8")
        readme_id = parse_id_from_readme(text)
        dirname = readme.parent.name
        archive_match = ARCHIVE_TASK_DIR_RE.match(dirname)
        identity_name = archive_match.group(2) if archive_match else dirname
        dirname_id = id_from_dirname(identity_name)
        if readme_id is None:
            add("missing_readme_id", path=row.path)
        if readme_id and dirname_id and readme_id != dirname_id:
            add("readme_dir_id_mismatch", path=row.path, readme_id=readme_id, dirname_id=dirname_id)
        parsed_status = parse_status_from_readme(text)
        if parsed_status not in VALID_STATUSES:
            add("invalid_readme_status", path=row.path, status=parsed_status)
        try:
            parse_scope(text)
            parse_work_context(text)
            parse_openspec(text)
        except TaskError as exc:
            add(
                exc.reason or "malformed_operational_table",
                path=row.path,
                **exc.details,
            )
    for task_id, rows in by_id.items():
        if len(rows) > 1:
            sections = {row.section for row in rows}
            add(
                "active_archive_id_conflict" if len(sections) > 1 else "duplicate_task_id",
                task_id=task_id,
                paths=[row.path for row in rows],
            )

    indexed = [*indexed_active, *indexed_archived]
    indexed_paths: set[str] = set()
    for row in indexed:
        path = row.path.rstrip("/")
        if path in indexed_paths:
            add("duplicate_index_path", path=row.path)
        indexed_paths.add(path)
        if not (root / path / "README.md").is_file():
            add("missing_indexed_path", task_id=row.task_id, path=row.path)

    scan_keys = {(row.task_id, row.path.rstrip("/"), row.section) for row in scanned}
    index_keys = {(row.task_id, row.path.rstrip("/"), row.section) for row in indexed}
    missing_rows = [asdict(row) for row in scanned if (row.task_id, row.path.rstrip("/"), row.section) not in index_keys]
    stale_rows = [asdict(row) for row in indexed if (row.task_id, row.path.rstrip("/"), row.section) not in scan_keys]
    numbers = [int(row.task_id[1:]) for row in scanned if ID_RE.match(row.task_id)]
    reconciled_next = max([next_id, *((number + 1) for number in numbers)])
    return {
        "next_id": reconciled_next,
        "active": scanned_active,
        "archived": scanned_archived,
        "diagnostics": diagnostics,
        "blocking": diagnostics,
        "missing_index_rows": missing_rows,
        "stale_index_rows": stale_rows,
        "repair_needed": bool(missing_rows or stale_rows or next_id != reconciled_next),
        "max_id": max(numbers, default=0),
    }


def catalog_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "next_id": catalog["next_id"],
        "max_id": catalog["max_id"],
        "diagnostics": catalog["diagnostics"],
        "missing_index_rows": catalog["missing_index_rows"],
        "stale_index_rows": catalog["stale_index_rows"],
        "repair_needed": catalog["repair_needed"],
    }


def require_catalog(root: Path, *, repair: bool) -> dict[str, Any]:
    catalog = reconcile_task_catalog(root)
    if catalog["blocking"]:
        raise TaskError(
            "task catalog has blocking identity/path diagnostics",
            reason="task_catalog_conflict",
            details={"catalog": catalog_payload(catalog)},
        )
    if repair and catalog["repair_needed"]:
        write_index(root, catalog["next_id"], list(catalog["active"]), list(catalog["archived"]))
        catalog = reconcile_task_catalog(root)
    return catalog


def enrich_archived_row(root: Path, row: TaskRow) -> TaskInfo | None:
    task_root = resolve_task_root(root, row)
    readme = task_root / "README.md"
    if not task_root.is_dir() or not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8")
    tid = parse_id_from_readme(text) or row.task_id
    if ID_RE.match(tid):
        tid = normalize_id(tid)
    archive_match = ARCHIVE_TASK_DIR_RE.match(task_root.name)
    original_name = archive_match.group(2) if archive_match else task_root.name
    slug = slug_from_dirname(original_name)
    return TaskInfo(
        task_id=tid,
        task_root=rel_posix(root, task_root) + "/",
        slug=slug,
        name=row.name or slug,
        status="archived",
        readme=rel_posix(root, readme),
        openspec=parse_openspec(text),
        scope=parse_scope(text),
        checkouts=parse_work_context(text),
        index_path=rel_posix(root, index_path(root)) if index_path(root).exists() else "",
        updated=row.archived_on,
    )


def list_archived_infos(root: Path) -> list[TaskInfo]:
    rows = list(reconcile_task_catalog(root)["archived"])
    infos: list[TaskInfo] = []
    for row in rows:
        info = enrich_archived_row(root, row)
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


def archived_match_markdown(matches: list[TaskInfo]) -> str:
    lines = [
        "## 任务已归档",
        "",
        "指定任务不在活跃任务集合中，不能直接执行 apply。",
        "",
        "**归档匹配：**",
    ]
    for info in matches:
        lines.append(f"- {info.task_id} — {info.task_root}")
    lines.extend(
        [
            "",
            "如需继续实施，请先恢复：",
            (
                f"- `{taskctl_command('restore', matches[0].task_id)}`"
                if len(matches) == 1
                else f"- `{taskctl_command('restore', '<TNNNN>')}`"
            ),
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

| change | 路径 | 仓库 | 顺序 | 说明 |
|--------|------|------|------|------|
| — | | | | （尚无） |

### 设计文档

| 文档 | 类型 | 归档落点 |
|------|------|----------|
| — | | （无；复杂任务经 task-design 写入 `design/`） |

## 方案笔记

由 task-explore 写入：备选方案、取舍、否决理由与未决问题；无探索时保持「（暂无）」。

（暂无）

## 工作上下文

apply 前保持「尚未准备」；task-apply Checkout Gate 后再记录实际执行环境。涉及面是计划范围；本节是实际执行环境。

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| （apply 前尚未准备） | | | 未使用 | | |

## 验收标准

- [ ] （待补）

## 变更记录

| 日期 | 变更 |
|------|------|
| {created} | 创建任务，状态 draft |
"""


def run_git(
    repo: Path,
    *git_args: str,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git non-interactively under a bounded wall clock.

    Credential and host-key prompts are disabled so an unreachable remote fails
    fast instead of blocking on stdin, and a timeout degrades to a non-zero
    result the existing callers already treat as a blocked step.
    """
    limit = positive_float_env(
        GIT_TIMEOUT_ENV, DEFAULT_GIT_TIMEOUT if timeout is None else timeout
    )
    argv = ["git", "-C", str(repo), *git_args]
    try:
        return subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
            env={**os.environ, **NON_INTERACTIVE_GIT_ENV},
            timeout=limit,
        )
    except subprocess.TimeoutExpired as exc:
        message = f"git {' '.join(git_args)} timed out after {limit:g}s in {repo}"
        if check:
            raise TaskError(
                message,
                reason="git_timeout",
                details={
                    "repo": str(repo),
                    "git_args": list(git_args),
                    "timeout_seconds": limit,
                    "recovery_hint": (
                        "check remote reachability and credentials, or raise "
                        f"{GIT_TIMEOUT_ENV}"
                    ),
                },
            ) from exc
        return subprocess.CompletedProcess(
            args=argv,
            returncode=GIT_TIMEOUT_RETURNCODE,
            stdout="",
            stderr=message,
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


def delivery_repo_keys(info: TaskInfo) -> list[str]:
    keys: list[str] = []
    for row in info.scope.get("must", []):
        key = normalize_repo_path(str(row.get("path") or ""))
        if key and key not in keys:
            keys.append(key)
    for row in info.checkouts:
        key = normalize_repo_path(str(row.get("repo") or ""))
        if key and key not in keys:
            keys.append(key)
    return keys


def validate_checkout_binding(root: Path, info: TaskInfo, repo_key: str) -> dict[str, Any]:
    repo_key = normalize_repo_path(repo_key)
    base: dict[str, Any] = {"repo": repo_key, "ok": False}
    binding = binding_for_repo(info, repo_key)
    if binding is None:
        return {**base, "reason": "checkout_not_prepared", "checkout": None}
    expected = str(binding.get("branch") or "").strip()
    checkout_raw = str(binding.get("checkout") or "").strip()
    base.update({"binding": binding, "expected_branch": expected, "checkout": checkout_raw or None})
    if not checkout_raw or not expected:
        return {**base, "reason": "checkout_not_prepared"}
    try:
        canonical = Path(resolve_repo(root, repo_key)["git_root_abs"])
    except TaskError as exc:
        return {**base, "reason": "canonical_repository_unavailable", "detail": str(exc)}
    checkout = resolve_checkout_path(root, checkout_raw)
    base["checkout"] = display_checkout_path(root, checkout)
    if not checkout.is_dir():
        return {**base, "reason": "checkout_missing"}
    if not same_git_repository(canonical, checkout):
        return {**base, "reason": "wrong_repository"}
    actual = current_branch(checkout)
    base["actual_branch"] = actual or None
    if not actual:
        return {**base, "reason": "detached_head"}
    if actual != expected:
        return {**base, "reason": "branch_mismatch"}
    return {**base, "ok": True, "reason": "ok", "checkout_abs": str(checkout), "actual_branch": actual}


def evaluate_delivery_checkout_bindings(root: Path, info: TaskInfo) -> dict[str, Any]:
    bindings = [validate_checkout_binding(root, info, key) for key in delivery_repo_keys(info)]
    return {"ok": all(row["ok"] for row in bindings), "bindings": bindings, "blocking": [row for row in bindings if not row["ok"]]}


def checkout_gate_failure(gate: dict[str, Any]) -> TaskError:
    first = gate["blocking"][0]
    return TaskError(
        f"delivery checkout binding failed for {first['repo']}: {first['reason']}",
        reason=str(first["reason"]),
        details={"checkout_gate": gate},
    )


def format_work_context(rows: list[dict[str, Any]]) -> str:
    lines = [
        "apply 前保持「尚未准备」；task-apply Checkout Gate 后再记录实际执行环境。涉及面是计划范围；本节是实际执行环境。",
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


PORCELAIN_RENAME_RE = re.compile(r"^(?P<orig>.+?) -> (?P<dest>.+)$")


def porcelain_entry_paths(entry: str) -> list[str]:
    """Repo-relative paths named by one `git status --porcelain` line."""
    body = entry[3:] if len(entry) > 3 else ""
    if not body.strip():
        return []
    match = PORCELAIN_RENAME_RE.match(body)
    parts = [match.group("orig"), match.group("dest")] if match else [body]
    return [part.strip().strip('"') for part in parts if part.strip()]


def classify_dirty_paths(
    repo: Path, planning_roots: list[Path], *, limit: int = 20
) -> dict[str, Any]:
    """Attribute uncommitted changes to the planning or the delivery role.

    Only changes fully contained in a planning root are planning-role; anything
    else, including an entry whose ownership cannot be decided, is delivery-role
    and keeps failing closed.
    """
    porcelain = dirty_porcelain(repo, limit=limit)
    roots = [Path(os.path.normpath(str(item))) for item in planning_roots]
    planning: list[str] = []
    delivery: list[str] = []
    for entry in porcelain:
        paths = porcelain_entry_paths(entry)
        owned_by_planning = bool(paths) and bool(roots)
        for raw in paths:
            absolute = Path(os.path.normpath(str(repo / raw)))
            if not any(absolute.is_relative_to(item) for item in roots):
                owned_by_planning = False
                break
        (planning if owned_by_planning else delivery).append(entry)
    if not porcelain:
        role = "clean"
    elif delivery:
        role = "delivery"
    else:
        role = "planning"
    return {
        "role": role,
        "porcelain": porcelain,
        "planning": planning,
        "delivery": delivery,
        "planning_roots": [str(item) for item in roots],
    }


def planning_dirty_action(ownership: dict[str, Any]) -> str:
    roots = ", ".join(ownership["planning_roots"]) or "the canonical planning root"
    return (
        f"uncommitted planning artifacts under {roots} stay at the canonical planning "
        "root and do not travel with the delivery branch; commit them there when "
        "convenient — delivery preparation continues"
    )


def blocked_dirty_entry(entry: dict[str, Any], repo: Path) -> dict[str, Any]:
    entry["action"] = "blocked_dirty"
    entry["dirty"] = True
    entry["dirty_role"] = "delivery"
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


def cmd_prepare_branches(root: Path, args: argparse.Namespace) -> int:
    if args.from_task and not args.dry_run:
        with index_lock(root):
            require_catalog(root, repair=True)
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
    planning_roots = task_planning_roots(root, task_info)

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
                ownership = classify_dirty_paths(repo, planning_roots)
                if ownership["role"] != "clean":
                    entry["dirty"] = True
                    entry["dirty_role"] = ownership["role"]
                    entry["planning_dirty"] = ownership["planning"]
                results.append(entry)
                continue

            if not create_worktree:
                ownership = classify_dirty_paths(repo, planning_roots)
                if ownership["role"] == "delivery":
                    errors.append(blocked_dirty_entry(entry, repo))
                    continue
                if ownership["role"] == "planning":
                    # Planning artifacts are not delivery WIP; they stay at the
                    # canonical planning root while the branch is prepared.
                    entry["dirty"] = True
                    entry["dirty_role"] = "planning"
                    entry["planning_dirty"] = ownership["planning"]
                    entry["planning_action"] = planning_dirty_action(ownership)

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
                fetch = run_git(
                    canonical_repo,
                    "fetch",
                    "origin",
                    timeout=DEFAULT_GIT_NETWORK_TIMEOUT,
                )
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


def summarize_delivery_checkout(
    root: Path,
    repo_key: str,
    checkout: Path,
    binding: dict[str, Any] | None,
    *,
    max_commits: int = 30,
    max_files: int = 100,
) -> dict[str, Any]:
    """Collect committed, staged, working-tree and untracked delivery changes."""
    branch = str((binding or {}).get("branch") or current_branch(checkout))
    summary: dict[str, Any] = {
        "repo": repo_key,
        "checkout": display_checkout_path(root, checkout),
        "is_worktree": inspect_git_checkout(root, checkout)["is_worktree"],
        "branch": branch,
        "current_branch": current_branch(checkout),
        "dirty": is_dirty(checkout),
        "commits": [],
        "files": [],
        "stat": "",
    }
    try:
        base = detect_base_branch(
            checkout, str((binding or {}).get("base") or "") or None
        )
    except TaskError as exc:
        summary["error"] = str(exc)
        return summary
    range_spec = f"{base}...{branch}"
    if run_git(checkout, "rev-parse", "--verify", f"origin/{base}").returncode == 0:
        range_spec = f"origin/{base}...{branch}"
    summary["base"] = base
    summary["range"] = range_spec

    log = run_git(
        checkout, "log", "--oneline", f"--max-count={max_commits}", range_spec
    )
    if log.returncode == 0:
        for line in log.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            sha, _, subject = line.partition(" ")
            summary["commits"].append({"sha": sha, "subject": subject})

    seen_paths: set[str] = set()

    def add_name_status(output: str, source: str) -> None:
        for line in output.splitlines():
            parts = line.split("	")
            if len(parts) < 2:
                continue
            status, path = parts[0], parts[-1]
            if path in seen_paths or len(summary["files"]) >= max_files:
                continue
            seen_paths.add(path)
            summary["files"].append(
                {
                    "status": status,
                    "path": path,
                    "repo_path": repo_display_path(repo_key, path),
                    "source": source,
                }
            )

    committed = run_git(checkout, "diff", "--name-status", range_spec)
    if committed.returncode == 0:
        add_name_status(committed.stdout, "committed")
    working = run_git(checkout, "diff", "--name-status")
    if working.returncode == 0:
        add_name_status(working.stdout, "working_tree")
    staged = run_git(checkout, "diff", "--cached", "--name-status")
    if staged.returncode == 0:
        add_name_status(staged.stdout, "staged")
    porcelain = run_git(checkout, "status", "--porcelain")
    if porcelain.returncode == 0:
        for line in porcelain.stdout.splitlines():
            if len(line) < 4 or len(summary["files"]) >= max_files:
                continue
            status = line[:2].strip() or "M"
            path = line[3:].strip()
            if path in seen_paths:
                continue
            seen_paths.add(path)
            summary["files"].append(
                {
                    "status": status,
                    "path": path,
                    "repo_path": repo_display_path(repo_key, path),
                    "source": "untracked" if status == "??" else "working_tree",
                }
            )
    stat = run_git(checkout, "diff", "--stat", range_spec)
    if stat.returncode == 0:
        summary["stat"] = stat.stdout.strip()
    return summary


def resolve_change_target(root: Path, change: dict[str, str]) -> dict[str, Any]:
    """Locate an OpenSpec change at its canonical planning root.

    Planning artifacts belong to the canonical repository and are archived by
    `openspec archive`; they never travel with a delivery branch or worktree, so
    no delivery checkout binding participates in this resolution.
    """
    store = str(change.get("store") or "").strip()
    if store:
        raise TaskError(
            f"unsupported OpenSpec store for {change.get('name')}: {store}",
            reason="unsupported_openspec_store",
            details={"change": change.get("name"), "store": store, "line": change.get("line")},
        )
    raw_repo = (change.get("repo") or "").strip()
    repo_key = normalize_repo_path(raw_repo) if raw_repo else ""
    canonical = (
        Path(resolve_repo(root, repo_key)["git_root_abs"]) if repo_key else root.resolve()
    )
    raw_path = (change.get("path") or "").strip().strip("`").rstrip("/")
    if raw_path and Path(raw_path).is_absolute():
        raise TaskError(f"OpenSpec path must be canonical-repo/workspace relative: {raw_path}")
    relative = raw_path
    if repo_key and relative:
        normalized = normalize_repo_path(relative)
        if normalized == repo_key:
            relative = ""
        elif normalized.startswith(repo_key.rstrip("/") + "/"):
            relative = normalized[len(repo_key.rstrip("/")) + 1 :]
    change_root = (canonical / relative).resolve() if relative else canonical
    try:
        change_root.relative_to(canonical)
    except ValueError as exc:
        raise TaskError(
            f"OpenSpec path escapes the canonical repository: {raw_path}"
        ) from exc
    planning_root = change_root
    for candidate in [change_root, *change_root.parents]:
        if candidate.name == "changes" and candidate.parent.name == "openspec":
            planning_root = candidate.parent
            break
        if candidate.name == "openspec":
            planning_root = candidate
            break
    target = {
        **change,
        "repo": repo_key,
        "canonical_repo": display_checkout_path(root, canonical),
        "canonical_repo_abs": str(canonical),
        "change_root": str(change_root),
        "planning_root": str(planning_root),
    }
    target["openspec_schema"] = assert_openspec_schema(target)
    return target


SUPPORTED_OPENSPEC_SCHEMA = "spec-driven"
OPENSPEC_SCHEMA_RE = re.compile(r"^\s*schema\s*:\s*(?P<schema>[^#\s]+)", re.MULTILINE)


def read_openspec_schema(planning_root: Path) -> str:
    """Read the declared schema without depending on a YAML parser."""
    config = planning_root / "config.yaml"
    if not config.is_file():
        return SUPPORTED_OPENSPEC_SCHEMA
    try:
        text = config.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return SUPPORTED_OPENSPEC_SCHEMA
    match = OPENSPEC_SCHEMA_RE.search(text)
    if not match:
        return SUPPORTED_OPENSPEC_SCHEMA
    return match.group("schema").strip().strip("\"'")


def assert_openspec_schema(target: dict[str, Any]) -> str:
    """Fail with a named schema instead of letting artifact names silently miss."""
    planning_root = Path(target["planning_root"])
    schema = read_openspec_schema(planning_root)
    if schema != SUPPORTED_OPENSPEC_SCHEMA:
        raise TaskError(
            f"unsupported OpenSpec schema {schema!r} at {planning_root}; "
            f"only {SUPPORTED_OPENSPEC_SCHEMA} is supported",
            reason="unsupported_openspec_schema",
            details={
                "change": target.get("name"),
                "schema": schema,
                "planning_root": str(planning_root),
            },
        )
    return schema


def resolve_change_targets(root: Path, info: TaskInfo) -> list[dict[str, Any]]:
    return [resolve_change_target(root, row) for row in info.openspec]


def task_planning_roots(root: Path, info: TaskInfo | None) -> list[Path]:
    """Canonical planning roots of a task, used for dirty-path ownership."""
    if info is None:
        return []
    roots: list[Path] = []
    for row in info.openspec:
        try:
            target = resolve_change_target(root, row)
        except TaskError:
            continue
        planning_root = Path(target["planning_root"])
        if planning_root not in roots:
            roots.append(planning_root)
    return roots


def parse_openspec_checkboxes(text: str) -> list[dict[str, Any]]:
    """Report checkbox facts only.

    Whether a leftover item is "just verification" or real implementation is a
    semantic call: it belongs to the Agent (who reads the item and explains it)
    and the user (who decides), never to a keyword table here.
    """
    items: list[dict[str, Any]] = []
    for match in CHECKBOX_ITEM_RE.finditer(text):
        items.append(
            {
                "text": match.group(2).strip(),
                "done": match.group(1).lower() == "x",
            }
        )
    return items


def remaining_state_of(items: list[dict[str, Any]]) -> str:
    return "remaining" if any(not item["done"] for item in items) else "none"


def aggregate_remaining_state(reports: list[dict[str, Any]]) -> str:
    states = {str(report.get("remaining_state") or "none") for report in reports}
    return "remaining" if "remaining" in states else "none"


def empty_openspec_report() -> dict[str, Any]:
    return {
        "total": 0,
        "complete": 0,
        "remaining": 0,
        "remaining_state": "none",
        "remaining_items": [],
        "items": [],
    }


def openspec_task_report(target: dict[str, Any]) -> dict[str, Any]:
    change_root = Path(target["change_root"])
    tasks = change_root / "tasks.md"
    availability = "active"
    unavailable_reason = ""
    if not tasks.is_file():
        archived_paths = archived_change_paths(target)
        if len(archived_paths) == 1 and (archived_paths[0] / "tasks.md").is_file():
            tasks = archived_paths[0] / "tasks.md"
            availability = "archived"
            unavailable_reason = (
                f"OpenSpec change is archived at {archived_paths[0]}; "
                "restore or create a follow-up change before apply"
            )
        elif len(archived_paths) > 1:
            unavailable_reason = (
                "multiple archived OpenSpec changes match; select and restore one: "
                + ", ".join(str(path) for path in archived_paths)
            )
            return {
                "total": 1,
                "complete": 0,
                "remaining": 1,
                "remaining_state": "remaining",
                "remaining_items": [
                    {"text": "OpenSpec change archive match is ambiguous", "done": False}
                ],
                "items": [],
                "availability": "ambiguous_archived",
                "unavailable_reason": unavailable_reason,
            }
        else:
            planning_root = target.get("planning_root") or str(change_root)
            unavailable_reason = (
                f"OpenSpec change is unreadable at canonical planning root {planning_root} "
                f"(expected {change_root / 'tasks.md'}); re-run task-propose for "
                f"{target.get('name') or 'this change'} or correct the 关联 OpenSpec row"
            )
            return {
                "total": 1,
                "complete": 0,
                "remaining": 1,
                "remaining_state": "remaining",
                "remaining_items": [
                    {"text": "OpenSpec tasks.md is missing", "done": False}
                ],
                "items": [],
                "availability": "missing",
                "unavailable_reason": unavailable_reason,
                "planning_root": planning_root,
            }
    items = parse_openspec_checkboxes(tasks.read_text(encoding="utf-8"))
    remaining_items = [item for item in items if not item["done"]]
    complete = sum(1 for item in items if item["done"])
    return {
        "total": len(items),
        "complete": complete,
        "remaining": len(remaining_items),
        "remaining_state": remaining_state_of(items),
        "remaining_items": remaining_items,
        "items": items,
        "availability": availability,
        "unavailable_reason": unavailable_reason,
        "tasks_path": str(tasks),
        "planning_root": target.get("planning_root") or str(change_root),
    }


def openspec_checkbox_progress(target: dict[str, Any]) -> dict[str, Any]:
    return openspec_task_report(target)


def inspect_change_remainder(target: dict[str, Any]) -> dict[str, Any]:
    """Classify the actual OpenSpec target state for resumable archive.

    Active and archived locations are inspected together.  More than one real
    location is ambiguous rather than silently preferring the recorded active
    path or the newest archive directory.
    """
    name = str(target.get("name") or "")
    change_root = Path(target["change_root"])
    archived_paths = archived_change_paths(target)
    active_paths = [change_root] if change_root.is_dir() else []
    locations = [*active_paths, *archived_paths]
    archive_root = Path(target["planning_root"]) / "changes" / "archive"

    if not locations:
        return {
            "name": name,
            "state": "missing",
            "path": str(change_root),
            "paths": [],
            "message": (
                f"{name} (recorded path missing and no archived change found "
                f"under {archive_root})"
            ),
            **empty_openspec_report(),
            "status_available": False,
        }
    if len(locations) > 1:
        return {
            "name": name,
            "state": "ambiguous",
            "path": "",
            "paths": [str(path) for path in locations],
            "message": (
                f"{name} has multiple active/archive matches: "
                + ", ".join(str(path) for path in locations)
            ),
            **empty_openspec_report(),
            "status_available": False,
        }

    actual_path = locations[0]
    report = openspec_task_report({**target, "change_root": str(actual_path)})
    status_available = str(report.get("availability") or "") not in {
        "missing",
        "ambiguous_archived",
    }
    if active_paths:
        state = "active"
        message = (
            f"{name} (active at {actual_path}, remaining={report['remaining']})"
        )
    elif report["remaining"]:
        state = "archived_incomplete"
        message = (
            f"{name} (archived at {actual_path} with remaining={report['remaining']})"
        )
    else:
        state = "uniquely_archived"
        message = f"{name} (uniquely archived at {actual_path})"
    return {
        "name": name,
        "state": state,
        "path": str(actual_path),
        "paths": [str(actual_path)],
        "message": message,
        **report,
        "status_available": status_available,
    }


def remaining_confirm_markdown(task_id: str, leftovers: list[dict[str, Any]]) -> str:
    lines = [
        "## OpenSpec 仍有未完成项，确认是否继续归档",
        "",
        f"{task_id} 的 OpenSpec 尚未全部完成。剩余项原文如下：",
        "",
    ]
    for row in leftovers:
        lines.append(f"- `{row['name']}` {row['complete']}/{row['total']}")
        for item in row.get("remaining_items") or []:
            lines.append(f"  - {item['text']}")
        if not (row.get("remaining_items") or []):
            lines.append(f"  - {row.get('message') or '无法读取 tasks.md 明细'}")
    lines.extend(
        [
            "",
            "**Agent**：逐条说明剩余项是什么性质（只差验证，还是功能未完成），"
            "给出判断依据，交用户裁决；**不得**自行认定「只剩测试」并归档。",
            "",
            "**请选择：**",
            "- 继续归档（强行合并）："
            f"`{taskctl_command('archive', task_id, '--force-merge')}`",
            "- 先做完剩余项再归档",
            "- 中止",
            "",
            "未确认前 **不得** 继续 archive。",
            "",
        ]
    )
    return "\n".join(lines)


def archived_change_paths(target: dict[str, Any]) -> list[Path]:
    """Match `YYYY-MM-DD-<name>` exactly.

    A suffix match would classify another change's archive as this change's own
    and silently skip the real archive action.
    """
    archive_root = Path(target["planning_root"]) / "changes" / "archive"
    name = str(target.get("name") or "")
    if not name or not archive_root.is_dir():
        return []
    dated = re.compile(r"\d{4}-\d{2}-\d{2}-" + re.escape(name) + r"$")
    return sorted(
        p for p in archive_root.iterdir() if p.is_dir() and dated.fullmatch(p.name)
    )


def apply_state_path(root: Path, info: TaskInfo) -> Path:
    return root / info.task_root.rstrip("/") / APPLY_STATE_FILENAME


FINAL_VERIFICATION_HEADING = "最终验证快照"
FINAL_SNAPSHOT_RE = re.compile(
    r"^- repo=`(?P<repo>[^`]*)` checkout=`(?P<checkout>[^`]*)` "
    r"branch=`(?P<branch>[^`]*)` head=`(?P<head>[^`]*)`$",
    re.MULTILINE,
)


def git_head(repo: Path) -> str:
    result = run_git(repo, "rev-parse", "HEAD")
    if result.returncode != 0 or not result.stdout.strip():
        raise TaskError(f"cannot read HEAD for checkout: {repo}")
    return result.stdout.strip()


def collect_delivery_snapshots(root: Path, info: TaskInfo) -> list[dict[str, Any]]:
    gate = evaluate_delivery_checkout_bindings(root, info)
    if not gate["ok"]:
        raise checkout_gate_failure(gate)
    planning_roots = task_planning_roots(root, info)
    snapshots: list[dict[str, Any]] = []
    for checked in gate["bindings"]:
        checkout = Path(checked["checkout_abs"])
        ownership = classify_dirty_paths(checkout, planning_roots)
        snapshots.append(
            {
                "repo": checked["repo"],
                "checkout": checked["checkout"],
                "branch": checked["actual_branch"],
                "head": git_head(checkout),
                "dirty": ownership["role"] != "clean",
                "dirty_role": ownership["role"],
                "delivery_dirty": ownership["role"] == "delivery",
                "dirty_porcelain": ownership["porcelain"],
            }
        )
    return snapshots


def parse_final_verification(text: str) -> dict[str, Any]:
    body = next(
        (
            section["body"]
            for section in parse_markdown_sections(text)
            if normalize_heading(section["heading"])
            == normalize_heading(FINAL_VERIFICATION_HEADING)
        ),
        "",
    )
    status_match = re.search(r"^- 状态：`([^`]+)`\s*$", body, re.MULTILINE)
    reason_match = re.search(r"^- 说明：(.+?)\s*$", body, re.MULTILINE)
    return {
        "status": status_match.group(1) if status_match else "missing",
        "reason": reason_match.group(1).strip() if reason_match else "",
        "snapshots": [match.groupdict() for match in FINAL_SNAPSHOT_RE.finditer(body)],
    }


def render_final_verification(final: dict[str, Any]) -> list[str]:
    lines = ["", f"## {FINAL_VERIFICATION_HEADING}", "", f"- 状态：`{final['status']}`"]
    if final.get("reason"):
        lines.append(f"- 说明：{final['reason']}")
    for snap in final.get("snapshots") or []:
        lines.append(
            f"- repo=`{snap['repo']}` checkout=`{snap['checkout']}` "
            f"branch=`{snap['branch']}` head=`{snap['head']}`"
        )
    return lines


def validate_final_verification(root: Path, info: TaskInfo, text: str) -> dict[str, Any]:
    recorded = parse_final_verification(text)
    if recorded["status"] != "fresh":
        return {"ok": False, "reason": "stale_verification", "recorded": recorded, "current": []}
    current = collect_delivery_snapshots(root, info)

    def comparable(rows: list[dict[str, Any]]) -> list[tuple[str, str, str, str]]:
        return sorted(
            (
                str(row.get("repo") or ""),
                str(row.get("checkout") or ""),
                str(row.get("branch") or ""),
                str(row.get("head") or ""),
            )
            for row in rows
        )

    ok = not any(row["delivery_dirty"] for row in current) and comparable(
        recorded["snapshots"]
    ) == comparable(current)
    return {
        "ok": ok,
        "reason": "ok" if ok else "stale_verification",
        "recorded": recorded,
        "current": current,
    }


def load_deferred_items(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskError(f"invalid apply state {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskError(f"invalid apply state schema: {path}")
    if payload.get("version") != APPLY_STATE_VERSION or not isinstance(
        payload.get("deferred"), list
    ):
        raise TaskError(f"invalid apply state schema: {path}")
    deferred: list[dict[str, str]] = []
    for row in payload["deferred"]:
        if not isinstance(row, dict):
            raise TaskError(f"invalid deferred item in apply state: {path}")
        change = str(row.get("change") or "").strip()
        task = str(row.get("task") or "").strip()
        reason = str(row.get("reason") or "").strip()
        if not change or not task or not reason:
            raise TaskError(f"incomplete deferred item in apply state: {path}")
        deferred.append(
            {
                "change": change,
                "task": task,
                "reason": reason,
                "updated": str(row.get("updated") or ""),
            }
        )
    return deferred


def change_order_value(target: dict[str, Any], row_index: int) -> int:
    """Explicit order column wins; otherwise the recorded row order applies."""
    raw = str(target.get("order") or "").strip()
    try:
        return int(raw)
    except ValueError:
        return row_index


def closest_texts(pool: list[str], text: str, *, limit: int = 3) -> list[str]:
    """Return verbatim candidates so an exact-match miss costs one retry, not many."""
    if not pool:
        return []
    hits = difflib.get_close_matches(text, pool, n=limit, cutoff=0.4)
    return hits or pool[:limit]


def build_apply_schedule(
    targets: list[dict[str, Any]], deferred: list[dict[str, str]]
) -> dict[str, Any]:
    for target in targets:
        progress = openspec_checkbox_progress(target)
        target["progress"] = progress
        target["remaining_state"] = progress["remaining_state"]
        target["remaining_items"] = progress["remaining_items"]
    scheduled = sorted(
        enumerate(targets),
        key=lambda pair: (change_order_value(pair[1], pair[0]), pair[0]),
    )
    for position, (row_index, target) in enumerate(scheduled):
        target["order_key"] = change_order_value(target, row_index)
        target["order_position"] = position
    remaining: list[dict[str, Any]] = []
    for _, target in scheduled:
        progress = target["progress"]
        change = str(target.get("name") or "")
        availability = str(progress.get("availability") or "active")
        unavailable_reason = str(progress.get("unavailable_reason") or "")
        for item in progress["remaining_items"]:
            remaining.append(
                {
                    "change": change,
                    **item,
                    "available": availability == "active",
                    "availability": availability,
                    "unavailable_reason": unavailable_reason,
                }
            )
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for row in remaining:
        key = (row["change"], row["text"])
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    if duplicates:
        rendered = "; ".join(
            f"{change}: {text}" for change, text in sorted(duplicates)
        )
        raise TaskError(
            "duplicate remaining OpenSpec checkbox text cannot be scheduled safely; "
            "add unique task ids/text: " + rendered
        )
    valid = seen
    reconciled = [
        row for row in deferred if (row["change"], row["task"]) in valid
    ]
    explicit_keys = {(row["change"], row["task"]) for row in reconciled}
    unavailable = [
        {
            "change": row["change"],
            "task": row["text"],
            "reason": row["unavailable_reason"]
            or f"OpenSpec change is unavailable ({row['availability']})",
            "updated": "",
            "automatic": True,
        }
        for row in remaining
        if not row["available"]
    ]
    unavailable_keys = {(row["change"], row["task"]) for row in unavailable}
    deferred_keys = explicit_keys | unavailable_keys
    candidates = [
        row
        for row in remaining
        if row["available"]
        and (row["change"], row["text"]) not in deferred_keys
    ]
    state = "done" if not remaining else ("candidates" if candidates else "deferred_only")
    all_deferred = [*reconciled, *unavailable]
    groups = [
        {
            "change": str(target.get("name") or ""),
            "order_key": target["order_key"],
            "planning_root": target.get("planning_root"),
            "progress": {
                key: target["progress"][key]
                for key in ("complete", "total", "remaining")
            },
            "candidates": [
                row for row in candidates if row["change"] == str(target.get("name") or "")
            ],
            "deferred": [
                row
                for row in all_deferred
                if row["change"] == str(target.get("name") or "")
            ],
        }
        for _, target in scheduled
    ]
    return {
        "state": state,
        "remaining": remaining,
        "persisted_deferred": reconciled,
        "unavailable": unavailable,
        "deferred": all_deferred,
        "candidates": candidates,
        "groups": groups,
        "next": candidates[0] if candidates else None,
    }


PROGRESS_PHASE_RE = re.compile(r"^- 阶段：`(?P<value>[^`]*)`\s*$", re.MULTILINE)
PROGRESS_CHANGE_RE = re.compile(r"^- 当前 change：`(?P<value>[^`]*)`\s*$", re.MULTILINE)
PROGRESS_TASK_RE = re.compile(r"^- 当前任务：(?P<value>.+?)\s*$", re.MULTILINE)
PROGRESS_PLACEHOLDERS = {"", "—", "-", "（无）", "（尚无）"}


def parse_progress_resume_facts(text: str) -> dict[str, Any]:
    """Read the last recorded round back out of the rendered progress artifact.

    Only fields the renderer already writes are parsed, and an unparsable or
    older artifact degrades to `unknown` instead of blocking the resume path.
    """
    if not text.strip():
        return {"phase": "unknown", "change": "", "task": "", "parsed": False}

    def value_of(pattern: re.Pattern[str]) -> str:
        match = pattern.search(text)
        if not match:
            return ""
        raw = match.group("value").strip()
        return "" if raw in PROGRESS_PLACEHOLDERS else raw

    phase = value_of(PROGRESS_PHASE_RE)
    return {
        "phase": phase or "unknown",
        "change": value_of(PROGRESS_CHANGE_RE),
        "task": value_of(PROGRESS_TASK_RE),
        "parsed": bool(phase),
    }


def classify_last_item_state(
    last_item: dict[str, str], targets: list[dict[str, Any]], uncommitted: list[dict[str, Any]]
) -> tuple[str, str]:
    """Never default an unresolvable item to `not_started`; re-doing it would
    duplicate or overwrite half-finished work."""
    change = last_item.get("change") or ""
    task = last_item.get("task") or ""
    if not change or not task:
        return "unknown", "progress artifact does not name a previously handled item"
    matched = [
        item
        for target in targets
        if str(target.get("name") or "") == change
        for item in (target.get("progress") or {}).get("items", [])
        if item["text"] == task
    ]
    if len(matched) != 1:
        return (
            "unknown",
            f"{change}: {task} does not match exactly one current checkbox",
        )
    if matched[0]["done"]:
        return "completed", "OpenSpec checkbox is checked"
    dirty = [row for row in uncommitted if row["delivery_dirty"]]
    if dirty:
        repos = ", ".join(str(row["repo"]) for row in dirty)
        return "in_flight", f"checkbox is unchecked and {repos} has uncommitted changes"
    return "not_started", "checkbox is unchecked and every delivery checkout is clean"


def build_resume_facts(
    root: Path,
    info: TaskInfo,
    targets: list[dict[str, Any]],
    schedule: dict[str, Any],
    progress_text: str,
    checkout_gate: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate every fact a resumed apply needs into one call."""
    recorded = parse_progress_resume_facts(progress_text)
    prepare_required = not checkout_gate["ok"]
    uncommitted: list[dict[str, Any]] = []
    verification = "unknown"
    if not prepare_required:
        for snapshot in collect_delivery_snapshots(root, info):
            uncommitted.append(
                {
                    "repo": snapshot["repo"],
                    "checkout": snapshot["checkout"],
                    "branch": snapshot["branch"],
                    "dirty_role": snapshot["dirty_role"],
                    "delivery_dirty": snapshot["delivery_dirty"],
                    "porcelain": snapshot["dirty_porcelain"],
                }
            )
        status = parse_final_verification(progress_text)["status"]
        if status == "missing":
            verification = "absent"
        elif status == "fresh":
            verification = (
                "fresh"
                if validate_final_verification(root, info, progress_text)["ok"]
                else "stale"
            )
        else:
            verification = status
    last_item = {"change": recorded["change"], "task": recorded["task"]}
    if prepare_required:
        state, reason = "unknown", "delivery checkout preparation is still required"
    else:
        state, reason = classify_last_item_state(last_item, targets, uncommitted)
    return {
        "phase": recorded["phase"],
        "progress_parsed": recorded["parsed"],
        "last_item": last_item,
        "last_item_state": state,
        "last_item_reason": reason,
        "prepare_required": prepare_required,
        "uncommitted": uncommitted,
        "verification": verification,
        "deferred": schedule["deferred"],
        "next": schedule["next"],
        "candidates": schedule["candidates"],
    }


def describe_openspec_locations(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report where each change actually lives and whether it can be read there."""
    rows: list[dict[str, Any]] = []
    for target in targets:
        progress = target.get("progress") or openspec_checkbox_progress(target)
        availability = str(progress.get("availability") or "active")
        rows.append(
            {
                "change": target.get("name"),
                "canonical_repo": target.get("canonical_repo"),
                "planning_root": target.get("planning_root"),
                "change_root": target.get("change_root"),
                "availability": availability,
                "readable": availability in {"active", "archived"},
                "action": str(progress.get("unavailable_reason") or ""),
            }
        )
    return rows


def cmd_execution_context(root: Path, args: argparse.Namespace) -> int:
    catalog = require_catalog(root, repair=False)
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
    checkout_gate = evaluate_delivery_checkout_bindings(root, info)
    progress_path = root / info.task_root.rstrip("/") / "progress.md"
    progress_text = (
        progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
    )
    if not checkout_gate["ok"]:
        failure = checkout_gate_failure(checkout_gate)
        failure.details["resume"] = {
            **parse_progress_resume_facts(progress_text),
            "prepare_required": True,
            "last_item_state": "unknown",
        }
        raise failure
    targets = resolve_change_targets(root, info)
    schedule = build_apply_schedule(
        targets, load_deferred_items(apply_state_path(root, info))
    )
    complete = sum(int(t["progress"]["complete"]) for t in targets)
    total = sum(int(t["progress"]["total"]) for t in targets)
    return emit(
        {
            "ok": True,
            "result": "execution_context",
            "task": asdict(info),
            "catalog": catalog_payload(catalog),
            "checkout_gate": checkout_gate,
            "scope": info.scope,
            "targets": targets,
            "openspec_locations": describe_openspec_locations(targets),
            "openspec_remaining": {
                "state": aggregate_remaining_state(targets),
                "complete": complete,
                "total": total,
                "remaining": total - complete,
                "items": schedule["remaining"],
            },
            "apply_schedule": schedule,
            "resume": build_resume_facts(
                root, info, targets, schedule, progress_text, checkout_gate
            ),
            "progress_path": rel_posix(root, progress_path),
            "progress_exists": progress_path.is_file(),
            "progress_markdown": progress_text,
        }
    )


def _cmd_advance_unlocked(root: Path, args: argparse.Namespace) -> int:
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
    checkout_gate = evaluate_delivery_checkout_bindings(root, info)
    if not checkout_gate["ok"]:
        raise checkout_gate_failure(checkout_gate)
    phase = args.phase
    status = "blocked" if phase == "blocked" else "in_progress"
    task_readme = root / info.readme
    original_readme = task_readme.read_text(encoding="utf-8")
    task_index = index_path(root)
    original_index = task_index.read_text(encoding="utf-8") if task_index.is_file() else None
    targets = resolve_change_targets(root, info)
    progress_path = root / info.task_root.rstrip("/") / "progress.md"
    previous_text = progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
    progress_existed = progress_path.is_file()
    state_path = apply_state_path(root, info)
    state_existed = state_path.is_file()
    original_state = state_path.read_text(encoding="utf-8") if state_existed else ""
    deferred = load_deferred_items(state_path)

    if (args.resume_current or args.defer_current is not None) and phase != "implementing":
        raise TaskError(
            "--defer-current/--resume-current require --phase implementing",
            reason="defer_requires_implementing",
            details={
                "exact_action": (
                    'advance <id> --phase implementing --change "<change>" '
                    '--current-task "<checkbox 原文>" --defer-current "<原因>" '
                    '[--blocker "<阻塞事实>"]'
                ),
                "recovery_hint": (
                    "--blocker 可与 implementing + --defer-current 同时使用；"
                    "--phase blocked 只用于全局故障或需要用户决策"
                ),
            },
        )
    if args.resume_current:
        if not args.change or not args.current_task:
            raise TaskError("--resume-current requires --change and --current-task")
        current_key = (args.change, args.current_task)
        if not any((row["change"], row["task"]) == current_key for row in deferred):
            raise TaskError(
                "current task is not deferred: " + args.current_task,
                reason="resume_target_not_deferred",
                details={
                    "change": args.change,
                    "closest": closest_texts(
                        [row["task"] for row in deferred if row["change"] == args.change],
                        args.current_task,
                    ),
                    "recovery_hint": (
                        "copy closest[0] verbatim (backticks and punctuation included) "
                        "into --current-task"
                    ),
                },
            )
        deferred = [row for row in deferred if (row["change"], row["task"]) != current_key]
    if args.defer_current is not None:
        if not args.change or not args.current_task:
            raise TaskError("--defer-current requires --change and --current-task")
        defer_reason = args.defer_current.strip()
        if not defer_reason:
            raise TaskError("--defer-current reason must not be blank")
        current_key = (args.change, args.current_task)
        deferred = [row for row in deferred if (row["change"], row["task"]) != current_key]
        deferred.append(
            {
                "change": args.change,
                "task": args.current_task,
                "reason": defer_reason,
                "updated": args.date or today_str(),
            }
        )
    schedule = build_apply_schedule(targets, deferred)
    if args.defer_current is not None and not any(
        row["change"] == args.change and row["task"] == args.current_task
        for row in schedule["persisted_deferred"]
    ):
        raise TaskError(
            "deferred current task is not an exact remaining OpenSpec checkbox: " + args.current_task,
            reason="defer_target_not_exact",
            details={
                "change": args.change,
                "closest": closest_texts(
                    [
                        row["text"]
                        for row in schedule["remaining"]
                        if row["change"] == args.change
                    ],
                    args.current_task,
                ),
                "recovery_hint": (
                    "copy closest[0] verbatim (backticks and punctuation included) "
                    "into --current-task"
                ),
            },
        )
    deferred = schedule["persisted_deferred"]
    if phase == "testing" and schedule["state"] != "done":
        raise TaskError(
            "--phase testing requires all OpenSpec checkboxes complete",
            reason="checkboxes_remaining",
        )
    if phase == "testing" and not (args.verification or []):
        raise TaskError(
            "--phase testing requires new --verification evidence",
            reason="verification_evidence_required",
        )
    if phase == "done" and schedule["state"] != "done":
        raise TaskError("--phase done requires all OpenSpec checkboxes complete")
    if phase == "done":
        verification_gate = validate_final_verification(root, info, previous_text)
        if not verification_gate["ok"]:
            raise TaskError(
                "--phase done requires fresh final verification for current delivery HEADs",
                reason="stale_verification",
                details={"verification_gate": verification_gate},
            )

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
            match.group(1).strip()
            for match in re.finditer(r"^\s*-\s+(.+?)\s*$", body, re.MULTILINE)
            if match.group(1).strip() not in {"（无）", "（尚无）"}
        ]

    completed_items = list(dict.fromkeys([*previous_items("本轮完成"), *(args.completed or [])]))
    verification_items = list(dict.fromkeys([*previous_items("验证证据"), *(args.verification or [])]))
    snapshots = collect_delivery_snapshots(root, info)
    previous_final = parse_final_verification(previous_text)
    final_verification = previous_final
    if phase == "implementing":
        final_verification = {
            **previous_final,
            "status": "stale" if previous_final["status"] == "fresh" else previous_final["status"],
            "reason": (
                "implementation resumed after final verification; re-run testing"
                if previous_final["status"] == "fresh"
                else previous_final.get("reason", "")
            ),
        }
    elif phase == "testing":
        dirty = [snapshot for snapshot in snapshots if snapshot["delivery_dirty"]]
        final_verification = {
            "status": "provisional" if dirty else "fresh",
            "reason": (
                "delivery checkout has uncommitted code changes; evidence is provisional"
                if dirty
                else "final verification matches clean delivery branch/HEAD snapshots"
            ),
            "snapshots": snapshots,
        }

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
        "| 顺序 | change | 完成 | 总数 | 剩余 | planning root |",
        "|------|--------|------|------|------|---------------|",
    ]
    schedule_groups = schedule["groups"]
    for group in schedule_groups:
        progress = group["progress"]
        lines.append(
            f"| {group['order_key']} | `{group['change']}` | {progress['complete']} | "
            f"{progress['total']} | {progress['remaining']} | `{group['planning_root']}` |"
        )
    total_complete = sum(int(g["progress"]["complete"]) for g in schedule_groups)
    total_all = sum(int(g["progress"]["total"]) for g in schedule_groups)
    lines.append(
        f"| — | **合计** | {total_complete} | {total_all} | "
        f"{total_all - total_complete} | |"
    )
    lines.extend(["", "## 本轮完成", ""])
    lines.extend(f"- {item}" for item in completed_items)
    if not completed_items:
        lines.append("- （无）")
    lines.extend(["", "## 验证证据", ""])
    lines.extend(f"- {item}" for item in verification_items)
    if not verification_items:
        lines.append("- （尚无）")
    lines.extend(["", "## 暂缓项", ""])
    if schedule["deferred"]:
        for group in schedule_groups:
            if not group["deferred"]:
                continue
            lines.append(f"- `{group['change']}`（{len(group['deferred'])}）")
            for row in group["deferred"]:
                lines.append(f"  - {row['task']}（{row['reason']}）")
    else:
        lines.append("- （无）")
    lines.extend(["", "## 候选项", ""])
    if schedule["candidates"]:
        for group in schedule_groups:
            if not group["candidates"]:
                continue
            lines.append(f"- `{group['change']}`（{len(group['candidates'])}）")
            for row in group["candidates"]:
                lines.append(f"  - {row['text']}")
    else:
        lines.append("- （无）")
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
    for snapshot in snapshots:
        lines.append(
            f"- `{snapshot['repo']}` checkout=`{snapshot['checkout']}` "
            f"branch=`{snapshot['branch']}` head=`{snapshot['head']}` "
            f"dirty={'yes' if snapshot['dirty'] else 'no'}"
        )
        for dirty_line in snapshot["dirty_porcelain"]:
            lines.append(f"  - `{dirty_line}`")
    lines.extend(render_final_verification(final_verification))

    try:
        atomic_write_text(
            state_path,
            json.dumps({"version": APPLY_STATE_VERSION, "deferred": deferred}, ensure_ascii=False, indent=2) + "\n",
        )
        atomic_write_text(progress_path, "\n".join(lines).rstrip() + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            status_code = _cmd_set_status_unlocked(
                root, argparse.Namespace(query=info.task_id, status=status, date=args.date)
            )
        if status_code != 0:
            raise TaskError(f"failed to persist checkpoint status for {info.task_id}")
    except Exception as primary_error:
        def restore_index() -> None:
            if original_index is None:
                task_index.unlink(missing_ok=True)
            else:
                atomic_write_text(task_index, original_index)

        def restore_progress() -> None:
            if progress_existed:
                atomic_write_text(progress_path, previous_text)
            else:
                progress_path.unlink(missing_ok=True)

        def restore_state() -> None:
            if state_existed:
                atomic_write_text(state_path, original_state)
            else:
                state_path.unlink(missing_ok=True)

        rollback_or_raise(
            primary_error,
            [
                ("README restore", lambda: atomic_write_text(task_readme, original_readme)),
                ("INDEX restore", restore_index),
                ("progress restore", restore_progress),
                ("apply state restore", restore_state),
            ],
            affected_paths=[task_readme, task_index, progress_path, state_path],
        )

    if phase == "blocked":
        result, next_item = "blocked", None
    elif phase == "implementing":
        result = (
            "validation_required"
            if schedule["state"] == "done"
            else "deferred_only"
            if schedule["state"] == "deferred_only"
            else "next"
        )
        next_item = schedule["next"] if result == "next" else None
    elif phase == "testing":
        result = "validation_recorded" if final_verification["status"] == "fresh" else "validation_required"
        next_item = None
    else:
        result, next_item = "done", None
    checkpoint = {
        "phase": phase,
        "status": status,
        "progress_path": rel_posix(root, progress_path),
        "apply_state_path": rel_posix(root, state_path),
    }
    return emit(
        {
            "ok": True,
            "result": result,
            "task_id": info.task_id,
            "checkpoint": checkpoint,
            **checkpoint,
            "apply_schedule": schedule,
            "next": next_item,
            "targets": targets,
            "verification": final_verification,
            "checkout_gate": checkout_gate,
        }
    )


def cmd_advance(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        require_catalog(root, repair=True)
        return _cmd_advance_unlocked(root, args)


def cmd_list(root: Path, args: argparse.Namespace) -> int:
    catalog = require_catalog(root, repair=False)
    infos = list_active_infos(root)
    if args.archived:
        archived = catalog["archived"]
        payload = {
            "ok": True,
            "result": "archived",
            "tasks": [asdict(r) for r in archived],
            "catalog": catalog_payload(catalog),
        }
        return emit(payload)
    payload = {
        "ok": True,
        "result": "active",
        "tasks": [asdict(i) for i in infos],
        "catalog": catalog_payload(catalog),
    }
    return emit(payload)


def cmd_resolve(root: Path, args: argparse.Namespace) -> int:
    catalog = require_catalog(root, repair=False)
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
                        "catalog": catalog_payload(catalog),
                    },
                )
            )
        result = "zero" if not matches else "multi"
        archived_matches = (
            match_query(list_archived_infos(root), query) if result == "zero" else []
        )
        if archived_matches:
            payload = with_workflow_notes(
                root,
                {
                    "ok": False,
                    "result": (
                        "archived_match"
                        if len(archived_matches) == 1
                        else "archived_multi"
                    ),
                    "reason": "task_archived",
                    "confidence": "deterministic",
                    "matches": [asdict(m) for m in archived_matches],
                    "archived_match": (
                        asdict(archived_matches[0])
                        if len(archived_matches) == 1
                        else None
                    ),
                    "active": [asdict(i) for i in infos],
                    "restore_command": (
                        taskctl_command("restore", archived_matches[0].task_id)
                        if len(archived_matches) == 1
                        else ""
                    ),
                    "exit_markdown": archived_match_markdown(archived_matches),
                },
            )
            return emit(payload, code=2)
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
        require_catalog(root, repair=True)
        return _cmd_set_status_unlocked(root, args)


def _cmd_restore_unlocked(root: Path, args: argparse.Namespace) -> int:
    status = args.status.strip().lower()
    if status not in VALID_STATUSES or status == "archived":
        raise TaskError(
            "invalid restore status: "
            + status
            + "; expected draft|exploring|designed|proposed|in_progress|blocked"
        )
    matches = match_query(list_archived_infos(root), args.query)
    if len(matches) != 1:
        return emit(
            {
                "ok": False,
                "result": "zero" if not matches else "multi",
                "matches": [asdict(m) for m in matches],
                "exit_markdown": (
                    archived_match_markdown(matches)
                    if matches
                    else "## 未找到归档任务\n\n请指定归档任务编号或路径。"
                ),
            },
            code=2,
        )
    info = matches[0]
    src = root / info.task_root.rstrip("/")
    archive_match = ARCHIVE_TASK_DIR_RE.match(src.name)
    if not archive_match:
        raise TaskError(
            f"cannot derive original task location from archive path: {info.task_root}"
        )
    created, original_name = archive_match.groups()
    if not DIR_ID_SLUG_RE.match(original_name):
        original_name = f"{info.task_id}-{info.slug}"
    dest = root / "tasks" / created / original_name
    rel_dest = rel_posix(root, dest) + "/"
    if dest.exists():
        raise TaskError(f"restore destination exists: {rel_dest}")
    active_infos = list_active_infos(root)
    active_conflicts = [i for i in active_infos if i.task_id == info.task_id]
    if active_conflicts:
        raise TaskError(f"active task id already exists: {info.task_id}")
    slug_conflicts = [i for i in active_infos if i.slug == info.slug]
    if slug_conflicts:
        raise TaskError(
            f"active task slug already exists: {info.slug} ({slug_conflicts[0].task_id})"
        )
    if args.dry_run:
        return emit(
            {
                "ok": True,
                "result": "dry_run",
                "taskId": info.task_id,
                "from": info.task_root,
                "to": rel_dest,
                "status": status,
            }
        )

    readme = src / "README.md"
    original_readme = readme.read_text(encoding="utf-8")
    task_index = index_path(root)
    original_index = (
        task_index.read_text(encoding="utf-8") if task_index.is_file() else None
    )
    updated = args.date or today_str()
    next_id, active, archived = parse_index(root)
    known_archived_rows = {
        (row.task_id, row.path.rstrip("/")) for row in archived
    }
    for row in scan_archived_tasks(root):
        key = (row.task_id, row.path.rstrip("/"))
        if key not in known_archived_rows:
            archived.append(row)
            known_archived_rows.add(key)
    known_ids = [
        row.task_id for row in [*active, *archived]
    ] + [archived_info.task_id for archived_info in list_archived_infos(root)]
    known_numbers = [
        int(task_id[1:]) for task_id in known_ids if ID_RE.match(task_id)
    ]
    if known_numbers:
        next_id = max(next_id, max(known_numbers) + 1)
    try:
        restored_readme = set_readme_status(original_readme, status)
        atomic_write_text(
            readme, restored_readme if restored_readme.endswith("\n") else restored_readme + "\n"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        if any(row.task_id == info.task_id for row in active):
            raise TaskError(f"active task id already exists in INDEX: {info.task_id}")
        archived = [row for row in archived if row.task_id != info.task_id]
        active.append(
            TaskRow(
                task_id=info.task_id,
                name=info.name or info.slug,
                path=rel_dest,
                status=status,
                updated=updated,
                section="active",
            )
        )
        write_index(root, next_id, active, archived)
    except Exception as primary_error:
        def move_back() -> None:
            if dest.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(src))

        def restore_readme() -> None:
            location = src / "README.md" if src.exists() else dest / "README.md"
            if location.exists():
                atomic_write_text(location, original_readme)

        def restore_index() -> None:
            if original_index is None:
                task_index.unlink(missing_ok=True)
            else:
                atomic_write_text(task_index, original_index)

        rollback_or_raise(
            primary_error,
            [("move-back", move_back), ("README restore", restore_readme), ("INDEX restore", restore_index)],
            affected_paths=[src, dest, task_index],
        )

    print(f"已恢复：{info.task_id} → {rel_dest} ({status})", file=sys.stderr)
    return emit(
        {
            "ok": True,
            "result": "restored",
            "taskId": info.task_id,
            "from": info.task_root,
            "to": rel_dest,
            "status": status,
        }
    )


def cmd_restore(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        require_catalog(root, repair=True)
        return _cmd_restore_unlocked(root, args)


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
    except Exception as primary_error:
        rollback_or_raise(
            primary_error,
            [("task directory cleanup", lambda: shutil.rmtree(task_root) if task_root.exists() else None)],
            affected_paths=[task_root, index_path(root)],
        )
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
        require_catalog(root, repair=True)
        return _cmd_new_unlocked(root, args)


def collect_archive_repository_uses(
    root: Path, info: TaskInfo, resolved_targets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Derive per-task repository roles without treating planning stores as delivery repos."""
    uses: dict[str, dict[str, Any]] = {}

    def add(raw_repo: str, role: str, source: str) -> None:
        repo_key = normalize_repo_path(raw_repo)
        row = uses.setdefault(
            repo_key,
            {"repo": repo_key, "roles": set(), "sources": set()},
        )
        row["roles"].add(role)
        row["sources"].add(source)

    for row in info.scope.get("must", []):
        if row.get("path"):
            add(str(row["path"]), "delivery", "scope.must")
    for scope_role in ("suggested", "excluded"):
        for row in info.scope.get(scope_role, []):
            if row.get("path"):
                add(str(row["path"]), "reference", f"scope.{scope_role}")
    for binding in info.checkouts:
        if binding.get("repo"):
            add(str(binding["repo"]), "delivery", "work_context")
    for target in resolved_targets:
        repo_key = str(target.get("repo") or "")
        if repo_key:
            add(repo_key, "planning", "openspec")
        else:
            workspace_git = find_git_root(root)
            if workspace_git is not None and workspace_git.resolve() == root.resolve():
                add(".", "planning", "openspec")

    workspace_git = find_git_root(root)
    if workspace_git is not None and workspace_git.resolve() == root.resolve():
        add(".", "task_store", "workspace_root")

    return [
        {
            "repo": row["repo"],
            "roles": sorted(row["roles"]),
            "sources": sorted(row["sources"]),
        }
        for row in sorted(uses.values(), key=lambda item: str(item["repo"]))
    ]


def archive_status_porcelain(
    repo: Path, *, limit: int = 20
) -> tuple[list[str], str | None]:
    try:
        result = run_git(repo, "status", "--porcelain")
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        return [], f"{type(error).__name__}: {error}"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        return [], detail or f"git status exited with {result.returncode}"
    return [line for line in result.stdout.splitlines() if line.strip()][:limit], None


def evaluate_archive_repository_gate(
    root: Path, info: TaskInfo, resolved_targets: list[dict[str, Any]]
) -> dict[str, Any]:
    repository_uses = collect_archive_repository_uses(root, info, resolved_targets)
    planning_roots = [
        Path(str(target["planning_root"]))
        for target in resolved_targets
        if target.get("planning_root")
    ]
    missing_delivery: list[dict[str, Any]] = []
    unavailable_delivery_status: list[dict[str, Any]] = []
    dirty_delivery: list[dict[str, Any]] = []
    non_blocking_dirty: list[dict[str, Any]] = []
    non_blocking_diagnostics: list[dict[str, Any]] = []
    delivery_summaries: list[dict[str, Any]] = []

    for use in repository_uses:
        repo_key = str(use["repo"])
        roles = set(use["roles"])
        if roles == {"reference"}:
            continue
        canonical = Path(resolve_repo(root, repo_key)["git_root_abs"])
        if "delivery" in roles:
            checked = validate_checkout_binding(root, info, repo_key)
            binding = checked.get("binding")
            checkout = (
                Path(checked["checkout_abs"])
                if checked.get("ok")
                else resolve_checkout_path(root, str(checked.get("checkout") or repo_key))
            )
            base = {
                **use,
                "checkout": display_checkout_path(root, checkout),
                "expected_branch": checked.get("expected_branch"),
                "actual_branch": checked.get("actual_branch"),
            }
            if not checked.get("ok"):
                missing_delivery.append({**base, "reason": checked["reason"]})
                continue
            porcelain, status_error = archive_status_porcelain(checkout)
            if status_error:
                unavailable_delivery_status.append(
                    {
                        **base,
                        "reason": "delivery_status_unavailable",
                        "detail": status_error,
                    }
                )
            else:
                delivery_summaries.append(
                    summarize_delivery_checkout(root, repo_key, checkout, binding)
                )
                if porcelain:
                    ownership = classify_dirty_paths(checkout, planning_roots)
                    if ownership["role"] == "planning":
                        non_blocking_dirty.append(
                            {
                                **base,
                                "reason": "planning_artifacts_only",
                                "dirty_porcelain": ownership["planning"],
                            }
                        )
                    else:
                        dirty_delivery.append(
                            {
                                **base,
                                "reason": "dirty_delivery_checkout",
                                "dirty_porcelain": porcelain,
                            }
                        )
            continue

        if roles.intersection({"planning", "task_store"}):
            porcelain, status_error = archive_status_porcelain(canonical)
            if status_error:
                non_blocking_diagnostics.append(
                    {
                        **use,
                        "checkout": display_checkout_path(root, canonical),
                        "reason": "non_delivery_status_unavailable",
                        "detail": status_error,
                    }
                )
            elif porcelain:
                non_blocking_dirty.append(
                    {
                        **use,
                        "checkout": display_checkout_path(root, canonical),
                        "reason": "not_a_delivery_checkout",
                        "dirty_porcelain": porcelain,
                    }
                )

    return {
        "repository_uses": repository_uses,
        "delivery_summaries": delivery_summaries,
        "blocking": [],
        "missing_delivery_checkouts": missing_delivery,
        "unavailable_delivery_status": unavailable_delivery_status,
        "dirty_delivery_checkouts": dirty_delivery,
        "non_blocking_dirty": non_blocking_dirty,
        "non_blocking_diagnostics": non_blocking_diagnostics,
        "overridden": [],
    }


def parse_acceptance_section(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    headings = [i for i, line in enumerate(lines) if re.match(r"^#{2,3}\s*验收标准\s*$", line)]
    if len(headings) != 1:
        line_no = headings[0] + 1 if headings else 0
        source = lines[headings[0]] if headings else "<missing 验收标准>"
        raise TaskError(
            "final archive requires exactly one 验收标准 section",
            reason="invalid_acceptance_structure",
            details={
                "diagnostic": {
                    "section": "验收标准",
                    "line": line_no,
                    "source": source,
                    "detail": f"expected one section, found {len(headings)}",
                }
            },
        )
    start = headings[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^#{2,3}\s+", lines[i]):
            end = i
            break
    body = "\n".join(lines[start + 1 : end])
    items = parse_openspec_checkboxes(body)
    if not items:
        raise TaskError(
            "final archive requires at least one acceptance checkbox",
            reason="invalid_acceptance_structure",
            details={
                "diagnostic": {
                    "section": "验收标准",
                    "line": start + 1,
                    "source": lines[start],
                    "detail": "no acceptance checkbox found",
                }
            },
        )
    return items


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

    readme = src / "README.md"
    original_text = readme.read_text(encoding="utf-8")
    acceptance_items = parse_acceptance_section(original_text)
    changes = src / "changes.md"
    original_changes_text = changes.read_text(encoding="utf-8") if changes.is_file() else None
    task_index = index_path(root)
    original_index = task_index.read_text(encoding="utf-8") if task_index.is_file() else None

    resolved_targets: list[dict[str, Any]] = []
    target_states: list[dict[str, Any]] = []
    for change in info.openspec:
        target = resolve_change_target(root, change)
        resolved_targets.append(target)
        target_states.append(inspect_change_remainder(target))

    missing_or_ambiguous = [
        row for row in target_states if row["state"] in {"missing", "ambiguous"}
    ]
    if missing_or_ambiguous:
        reason = (
            "openspec_target_ambiguous"
            if any(row["state"] == "ambiguous" for row in missing_or_ambiguous)
            else "openspec_target_missing"
        )
        raise TaskError(
            "; ".join(row["message"] for row in missing_or_ambiguous),
            reason=reason,
            details={"target_states": target_states},
        )
    unavailable_status = [
        row for row in target_states if not row.get("status_available", False)
    ]
    if unavailable_status:
        raise TaskError(
            "OpenSpec target status unavailable: "
            + "; ".join(row["message"] for row in unavailable_status),
            reason="openspec_status_unavailable",
            details={"target_states": target_states},
        )

    archive_gate = evaluate_archive_repository_gate(root, info, resolved_targets)
    missing_delivery = archive_gate["missing_delivery_checkouts"]
    if missing_delivery:
        archive_gate["blocking"] = missing_delivery
        rendered = ", ".join(
            f"{row['repo']} -> {row['checkout']}" for row in missing_delivery
        )
        return emit(
            {
                "ok": False,
                "error": (
                    "missing/invalid task checkout(s) (delivery): "
                    + rendered
                    + "; restore the recorded delivery checkout"
                ),
                "reason": missing_delivery[0]["reason"],
                "archive_gate": archive_gate,
                "target_states": target_states,
            },
            code=1,
        )

    unavailable_delivery_status = archive_gate["unavailable_delivery_status"]
    if unavailable_delivery_status:
        archive_gate["blocking"] = unavailable_delivery_status
        rendered = ", ".join(
            f"{row['repo']} ({row['checkout']}): {row['detail']}"
            for row in unavailable_delivery_status
        )
        return emit(
            {
                "ok": False,
                "error": "cannot inspect delivery checkout status: " + rendered,
                "reason": "delivery_status_unavailable",
                "archive_gate": archive_gate,
                "target_states": target_states,
            },
            code=1,
        )

    external_actions: list[dict[str, Any]] = []
    for row in target_states:
        external_actions.append(
            {
                "action": "archive_openspec",
                "change": row["name"],
                "state": "pending" if row["state"] == "active" else "completed",
                "target_state": row["state"],
                "path": row["path"],
                "planning_root": next(
                    target["planning_root"]
                    for target in resolved_targets
                    if str(target.get("name") or "") == row["name"]
                ),
            }
        )
    design_root = src / "design"
    if design_root.is_dir():
        external_actions.append(
            {
                "action": "promote_design",
                "state": "pending",
                "source": rel_posix(root, design_root),
                "files": [
                    rel_posix(root, path)
                    for path in sorted(design_root.rglob("*"))
                    if path.is_file()
                ],
            }
        )
    if not changes.is_file():
        external_actions.append(
            {
                "action": "write_changes",
                "state": "pending",
                "path": rel_posix(root, changes),
            }
        )

    if not args.dry_run and not changes.is_file():
        raise TaskError(
            "final preflight requires changes.md",
            reason="missing_changes_summary",
            details={"external_actions": external_actions},
        )

    override_audit: list[dict[str, Any]] = []
    remaining_rows = [row for row in target_states if int(row.get("remaining") or 0) > 0]
    if remaining_rows and not args.force_merge:
        print(
            f"OpenSpec 未完成：{info.task_id} — 列出剩余项，等用户裁决",
            file=sys.stderr,
        )
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "openspec_remaining",
                "condition": "remaining_openspec_checkboxes",
                "taskId": info.task_id,
                "affected": remaining_rows,
                "remaining": remaining_rows,
                "exact_action": taskctl_command("archive", info.task_id, "--force-merge"),
                "exit_markdown": remaining_confirm_markdown(info.task_id, remaining_rows),
                "user_actions": [
                    {
                        "id": "force_merge",
                        "label": "继续归档（强行合并）："
                        + taskctl_command("archive", info.task_id, "--force-merge"),
                    },
                    {"id": "finish_remaining", "label": "先做完剩余项再归档"},
                    {"id": "abort", "label": "中止"},
                ],
                "archive_gate": archive_gate,
                "target_states": target_states,
                "external_actions": external_actions,
            },
            code=2,
        )
    if remaining_rows:
        override_audit.append(
            {
                "condition": "remaining_openspec_checkboxes",
                "authorization": "--force-merge",
                "affected": [
                    {
                        "change": row["name"],
                        "items": [item["text"] for item in row.get("remaining_items") or []],
                    }
                    for row in remaining_rows
                ],
            }
        )

    if not args.dry_run and any(row["state"] == "active" for row in target_states):
        raise TaskError(
            "OpenSpec external archive actions are still pending; run initial preflight, "
            "perform the listed external actions, then rerun final preflight",
            reason="openspec_external_actions_pending",
            details={
                "target_states": target_states,
                "external_actions": external_actions,
            },
        )

    unchecked_items = [item["text"] for item in acceptance_items if not item["done"]]
    if unchecked_items and not args.allow_unchecked_acceptance:
        action = taskctl_command(
            "archive", info.task_id, "--allow-unchecked-acceptance"
        )
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "unchecked_acceptance",
                "condition": "unchecked_acceptance",
                "affected": unchecked_items,
                "exact_action": action,
                "user_actions": [
                    {"id": "allow_unchecked_acceptance", "label": action},
                    {"id": "abort", "label": "中止"},
                ],
                "archive_gate": archive_gate,
                "target_states": target_states,
                "external_actions": external_actions,
            },
            code=2,
        )
    if unchecked_items:
        override_audit.append(
            {
                "condition": "unchecked_acceptance",
                "authorization": "--allow-unchecked-acceptance",
                "affected": unchecked_items,
            }
        )

    allowed_repos = {
        normalize_repo_path(str(repo))
        for repo in (getattr(args, "allow_dirty_checkouts", None) or [])
    }
    dirty_by_repo = {
        str(row["repo"]): row for row in archive_gate["dirty_delivery_checkouts"]
    }
    unknown_dirty_overrides = sorted(allowed_repos - set(dirty_by_repo))
    if unknown_dirty_overrides:
        raise TaskError(
            "dirty override does not match a currently dirty delivery repository: "
            + ", ".join(unknown_dirty_overrides),
            reason="invalid_dirty_override_target",
            details={
                "authorized_repositories": sorted(allowed_repos),
                "dirty_repositories": sorted(dirty_by_repo),
                "archive_gate": archive_gate,
            },
        )
    blocked_dirty = [
        row for repo, row in dirty_by_repo.items() if repo not in allowed_repos
    ]
    overridden_dirty = [
        row for repo, row in dirty_by_repo.items() if repo in allowed_repos
    ]
    archive_gate["blocking"] = blocked_dirty
    archive_gate["overridden"] = overridden_dirty
    if blocked_dirty:
        exact_actions = [
            taskctl_command(
                "archive", info.task_id, "--allow-dirty-checkout", str(row["repo"])
            )
            for row in blocked_dirty
        ]
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "dirty_delivery_checkout",
                "condition": "dirty_delivery_checkout",
                "affected": blocked_dirty,
                "exact_action": exact_actions[0] if len(exact_actions) == 1 else exact_actions,
                "user_actions": [
                    {"id": "allow_dirty_checkout", "label": action}
                    for action in exact_actions
                ]
                + [{"id": "abort", "label": "中止"}],
                "archive_gate": archive_gate,
                "target_states": target_states,
                "external_actions": external_actions,
            },
            code=2,
        )
    for row in overridden_dirty:
        override_audit.append(
            {
                "condition": "dirty_delivery_checkout",
                "authorization": f"--allow-dirty-checkout {row['repo']}",
                "affected": {
                    "repo": row["repo"],
                    "checkout": row["checkout"],
                    "dirty_porcelain": row["dirty_porcelain"],
                },
            }
        )


    progress_path = src / "progress.md"
    verification_ok = False
    verification_gate: dict[str, Any] = {"ok": False, "reason": "stale_verification"}
    if progress_path.is_file():
        progress_text = progress_path.read_text(encoding="utf-8")
        verification = next(
            (
                section["body"]
                for section in parse_markdown_sections(progress_text)
                if normalize_heading(section["heading"]) == "验证证据"
            ),
            "",
        )
        has_evidence = bool(
            verification
            and "（尚无）" not in verification
            and re.search(r"^\s*-\s+\S", verification, re.MULTILINE)
        )
        verification_gate = validate_final_verification(root, info, progress_text)
        verification_ok = has_evidence and verification_gate["ok"]
    if not verification_ok and not args.allow_missing_verification:
        action = taskctl_command(
            "archive", info.task_id, "--allow-missing-verification"
        )
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "stale_verification",
                "condition": "missing_or_stale_final_verification",
                "affected": verification_gate,
                "exact_action": action,
                "user_actions": [
                    {"id": "allow_missing_verification", "label": action},
                    {"id": "rerun_verification", "label": "重新执行并记录最终验证"},
                    {"id": "abort", "label": "中止"},
                ],
                "archive_gate": archive_gate,
                "target_states": target_states,
                "external_actions": external_actions,
            },
            code=2,
        )
    if not verification_ok:
        override_audit.append(
            {
                "condition": "missing_or_stale_final_verification",
                "authorization": "--allow-missing-verification",
                "affected": verification_gate,
            }
        )

    create_date = src.parent.name
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", create_date):
        create_date = args.date or today_str()
    dirname = src.name
    if not DIR_ID_SLUG_RE.match(dirname) and ID_RE.match(info.task_id):
        dirname = f"{info.task_id}-{info.slug}"
    dest = root / "tasks" / "archive" / f"{create_date}-{dirname}"
    rel_dest = rel_posix(root, dest) + "/"
    if dest.exists():
        raise TaskError(f"archive destination exists: {rel_dest}")
    archived_on = args.date or today_str()

    initial = any(row["state"] == "active" for row in target_states) or not changes.is_file()
    if args.dry_run:
        return emit(
            {
                "ok": True,
                "result": "initial_preflight" if initial else "final_preflight",
                "preflight": "initial" if initial else "final",
                "from": info.task_root,
                "to": rel_dest,
                "archived_on": archived_on,
                "archive_gate": archive_gate,
                "target_states": target_states,
                "external_actions": external_actions,
                "gate_overrides": override_audit,
            }
        )

    if override_audit:
        changes_text = changes.read_text(encoding="utf-8").rstrip()
        changes_text += "\n\n## Gate Overrides\n\n"
        for entry in override_audit:
            affected = json.dumps(entry["affected"], ensure_ascii=False, sort_keys=True)
            changes_text += (
                f"- condition=`{entry['condition']}`; "
                f"authorization=`{entry['authorization']}`; affected={affected}\n"
            )
        atomic_write_text(changes, changes_text)

    archived_text = set_readme_status(original_text, "archived") + (
        "" if original_text.endswith("\n") else "\n"
    )
    try:
        atomic_write_text(readme, archived_text)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        parent = src.parent
        if parent.is_dir() and parent.name != "tasks" and not any(parent.iterdir()):
            parent.rmdir()

        next_id, active, archived = parse_index(root)
        active = [row for row in active if row.task_id != info.task_id]
        archived = [row for row in archived if row.task_id != info.task_id]
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
    except Exception as primary_error:
        def move_back() -> None:
            if dest.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(src))

        def restore_files() -> None:
            if src.exists():
                atomic_write_text(src / "README.md", original_text)
                if original_changes_text is not None:
                    atomic_write_text(src / "changes.md", original_changes_text)
                elif (src / "changes.md").exists():
                    (src / "changes.md").unlink()

        def restore_index() -> None:
            if original_index is None:
                task_index.unlink(missing_ok=True)
            else:
                atomic_write_text(task_index, original_index)

        rollback_or_raise(
            primary_error,
            [
                ("move-back", move_back),
                ("task files restore", restore_files),
                ("INDEX restore", restore_index),
            ],
            affected_paths=[src, dest, task_index, changes],
        )

    print(f"已归档：{info.task_id} → {rel_dest}", file=sys.stderr)
    return emit(
        {
            "ok": True,
            "result": "archived",
            "taskId": info.task_id,
            "from": info.task_root,
            "to": rel_dest,
            "archived_on": archived_on,
            "archive_gate": archive_gate,
            "target_states": target_states,
            "external_actions": external_actions,
            "gate_overrides": override_audit,
        }
    )


def cmd_archive(root: Path, args: argparse.Namespace) -> int:
    with index_lock(root):
        require_catalog(root, repair=True)
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
        help=(
            "task identifiers in play (TNNNN / tasks path / slug) plus a short "
            "intent summary; only identifiers are read, no NLU, no verbatim dump"
        ),
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
        "--force-merge",
        action="store_true",
        help="authorize the exact remaining OpenSpec checkbox set reported by preflight",
    )
    arch_p.add_argument("--allow-unchecked-acceptance", action="store_true")
    arch_p.add_argument("--allow-missing-verification", action="store_true")
    arch_p.add_argument(
        "--allow-dirty-checkout",
        dest="allow_dirty_checkouts",
        action="append",
        default=None,
        metavar="REPO",
        help="allow one dirty delivery checkout; repeatable",
    )
    arch_p.set_defaults(func=cmd_archive)

    restore_p = sub.add_parser(
        "restore", help="restore an archived task to its original active date directory"
    )
    restore_p.add_argument("query", help="archived TNNNN / slug / path")
    restore_p.add_argument(
        "--status",
        default="in_progress",
        help="active status after restore (default: in_progress)",
    )
    restore_p.add_argument("--date", help="updated date YYYY-MM-DD (default: today)")
    restore_p.add_argument("--dry-run", action="store_true")
    restore_p.set_defaults(func=cmd_restore)

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
        "--include-excluded",
        action="store_true",
        help="allow roots matching default exclude markers (none by default)",
    )
    prep_p.set_defaults(func=cmd_prepare_branches)

    context_p = sub.add_parser(
        "execution-context",
        help="resolve persisted checkout/worktree and OpenSpec execution targets",
    )
    context_p.add_argument("query", help="TNNNN / slug / path")
    context_p.set_defaults(func=cmd_execution_context)

    advance_p = sub.add_parser(
        "advance",
        help="atomically persist apply progress and return the next candidate item",
    )
    advance_p.add_argument("query", help="TNNNN / slug / path")
    advance_p.add_argument(
        "--phase",
        required=True,
        choices=("implementing", "testing", "blocked", "done"),
    )
    advance_p.add_argument("--change", default="")
    advance_p.add_argument("--current-task", default="")
    advance_p.add_argument("--completed", action="append", default=[])
    advance_p.add_argument("--verification", action="append", default=[])
    advance_p.add_argument("--blocker", default="")
    defer_group = advance_p.add_mutually_exclusive_group()
    defer_group.add_argument(
        "--defer-current",
        default=None,
        metavar="REASON",
        help="defer the exact --change/--current-task while other candidate items continue",
    )
    defer_group.add_argument(
        "--resume-current",
        action="store_true",
        help="remove the exact --change/--current-task from deferred state",
    )
    advance_p.add_argument("--next", dest="next_step", default="")
    advance_p.add_argument("--date", default=None)
    advance_p.set_defaults(func=cmd_advance)

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
        payload = {"ok": False, "error": str(e), **e.details}
        if e.reason:
            payload["reason"] = e.reason
        return emit(payload, code=e.code)
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
