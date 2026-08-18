#!/usr/bin/env python3
"""taskctl — task-workflow 的机械记账。

只做 Agent 做不可靠的事：ID 分配、目录与索引的一致性、git 分支准备的 fail-closed
门禁、归档前的完成度校验。进度事实一律以 OpenSpec `tasks.md` 的 checkbox 为准，
本脚本不维护第二份进度状态。

stdout 只输出 JSON，stderr 是一行摘要。退出码：0 成功，1 硬失败，2 需要用户确认。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

STATUSES = (
    "draft",
    "exploring",
    "designed",
    "proposed",
    "in_progress",
    "blocked",
    "archived",
)
ROLE_TO_KEY = {"必须": "must", "建议": "suggested", "排除": "excluded"}
EXTERNAL_KINDS = frozenset(
    {"approval", "credential", "environment", "service", "human-validation"}
)
EXTERNAL_STABLE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BRANCH_PREFIXES = ("feat", "fix", "chore", "refactor", "docs", "test", "perf")

ID_RE = re.compile(r"^T\d{4}$")
ACTIVE_DIR_RE = re.compile(r"^(T\d{4})-(.+)$")
ARCHIVE_DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(T\d{4})-(.+)$")
DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SCOPE_HEADING = "涉及面"
OPENSPEC_HEADING = "关联 OpenSpec"
WORK_CONTEXT_HEADING = "工作上下文"
ACCEPTANCE_HEADING = "验收标准"
VERIFICATION_HEADING = "验证记录"
CHANGELOG_HEADING = "变更记录"

NON_INTERACTIVE_GIT = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}
PLACEHOLDER_MARKS = {"", "—", "-", "–", "（待补）", "（尚无）", "（无）", "（暂无）"}


class TaskError(Exception):
    def __init__(self, message: str, *, reason: str = "error", **details: Any) -> None:
        super().__init__(message)
        self.reason = reason
        self.details = details


def emit(payload: dict[str, Any], *, code: int = 0, summary: str = "") -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if summary:
        print(summary, file=sys.stderr)
    return code


def today() -> str:
    return date.today().isoformat()


# --------------------------------------------------------------------------- #
# 工作区与路径
# --------------------------------------------------------------------------- #


def find_workspace(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "tasks").is_dir():
            return candidate
    raise TaskError(
        f"no workspace with a tasks/ directory at or above {cur}",
        reason="workspace_not_found",
    )


def tasks_dir(root: Path) -> Path:
    return root / "tasks"


def archive_dir(root: Path) -> Path:
    return root / "tasks" / "archive"


def index_path(root: Path) -> Path:
    return root / "tasks" / "INDEX.md"


def notes_path(root: Path) -> Path:
    return root / ".task-workflow.md"


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_text(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_slug(slug: str) -> str:
    slug = slug.strip().lower()
    if not SLUG_RE.match(slug):
        raise TaskError(
            f"invalid slug: {slug!r}; expected lowercase kebab-case",
            reason="invalid_slug",
        )
    return slug


def normalize_id(raw: str) -> str:
    text = raw.strip().upper()
    if text.isdigit():
        text = f"T{int(text):04d}"
    if not ID_RE.match(text):
        raise TaskError(f"invalid task id: {raw!r}; expected TNNNN", reason="invalid_id")
    return text


# --------------------------------------------------------------------------- #
# Markdown 解析
# --------------------------------------------------------------------------- #


def heading_pattern(heading: str) -> re.Pattern[str]:
    """匹配任意层级的标题；标题可带全角括号后缀（如「（task-explore）」）。

    行尾只用 `[ \\t]*` 而非 `\\s*`：后者会吞掉换行，使 `match.end()` 越过空行，
    导致 replace_section 每次写入都多插空行。
    """
    return re.compile(
        rf"^(#{{2,4}})[ \t]*{re.escape(heading)}[ \t]*(?:（[^）]*）)?[ \t]*$",
        re.MULTILINE,
    )


def section_body(text: str, heading: str) -> str:
    """返回任意层级标题 `heading` 下的正文。"""
    match = heading_pattern(heading).search(text)
    if not match:
        return ""
    level = len(match.group(1))
    rest = text[match.end() :]
    stop = re.search(rf"^#{{2,{level}}}[ \t]", rest, re.MULTILINE)
    return rest[: stop.start()] if stop else rest


def is_placeholder(*cells: str) -> bool:
    """占位单元格：空、破折号，或整体被全角括号包裹的说明文字。"""

    def placeholder(cell: str) -> bool:
        value = cell.strip().strip("`").strip()
        if value in PLACEHOLDER_MARKS:
            return True
        return value.startswith("（") and value.endswith("）")

    return all(placeholder(cell) for cell in cells)


def parse_table(body: str) -> list[dict[str, str]]:
    """按表头名解析首个 markdown 表格；列顺序变化不影响结果。"""
    lines = [line.strip() for line in body.splitlines()]
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.startswith("|"):
            if header is not None:
                break
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            header = [cell.strip("` ") for cell in cells]
            continue
        if all(set(cell) <= {"-", ":", " "} for cell in cells) and cells:
            continue
        rows.append({key: value for key, value in zip(header, cells)})
    return rows


def cell(row: dict[str, str], *names: str) -> str:
    for name in names:
        for key, value in row.items():
            if key == name:
                return value.strip().strip("`").strip()
    return ""


def parse_checkboxes(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.match(r"^\s*- \[([ xX])\]\s+(.*\S)\s*$", line)
        if match:
            items.append({"done": match.group(1).lower() == "x", "text": match.group(2)})
    return items


def frontmatter_field(text: str, name: str) -> str:
    match = re.search(rf"^\*\*{re.escape(name)}：\*\*[ \t]*(.*\S)[ \t]*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def set_frontmatter_field(text: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^(\*\*{re.escape(name)}：\*\*[ \t]*).*$", re.MULTILINE)
    if not pattern.search(text):
        raise TaskError(f"README missing **{name}：** field", reason="malformed_readme")
    return pattern.sub(lambda m: f"{m.group(1)}{value}", text, count=1)


def replace_section(text: str, heading: str, body: str) -> str:
    match = heading_pattern(heading).search(text)
    if not match:
        raise TaskError(f"README missing ## {heading}", reason="malformed_readme")
    level = len(match.group(1))
    rest = text[match.end() :]
    stop = re.search(rf"^#{{2,{level}}}[ \t]", rest, re.MULTILINE)
    tail = rest[stop.start() :] if stop else ""
    head = text[: match.end()]
    return f"{head}\n\n{body.strip()}\n\n{tail}" if tail else f"{head}\n\n{body.strip()}\n"


# --------------------------------------------------------------------------- #
# Task 模型
# --------------------------------------------------------------------------- #


@dataclass
class Task:
    task_id: str
    slug: str
    title: str
    status: str
    path: Path
    created: str
    archived_on: str = ""

    @property
    def archived(self) -> bool:
        return bool(self.archived_on)

    def readme(self) -> Path:
        return self.path / "README.md"

    def text(self) -> str:
        readme = self.readme()
        if not readme.is_file():
            raise TaskError(f"task README missing: {readme}", reason="missing_readme")
        return readme.read_text(encoding="utf-8")

    def row(self, root: Path) -> dict[str, str]:
        return {
            "id": self.task_id,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "path": rel(root, self.path),
            "created": self.created,
            "archived_on": self.archived_on,
        }


def load_task(path: Path, *, task_id: str, slug: str, created: str, archived_on: str = "") -> Task:
    readme = path / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    title_match = re.search(r"^#[ \t]+(.*\S)[ \t]*$", text, re.MULTILINE)
    status = frontmatter_field(text, "status") or ("archived" if archived_on else "draft")
    return Task(
        task_id=frontmatter_field(text, "id") or task_id,
        slug=frontmatter_field(text, "slug") or slug,
        title=title_match.group(1) if title_match else slug,
        status=status if status in STATUSES else "draft",
        path=path,
        created=frontmatter_field(text, "创建时间") or created,
        archived_on=archived_on,
    )


def scan_tasks(root: Path) -> tuple[list[Task], list[Task]]:
    active: list[Task] = []
    archived: list[Task] = []
    base = tasks_dir(root)
    if not base.is_dir():
        raise TaskError(f"missing tasks/ under {root}", reason="workspace_not_found")

    for day in sorted(p for p in base.iterdir() if p.is_dir() and DATE_DIR_RE.match(p.name)):
        for entry in sorted(p for p in day.iterdir() if p.is_dir()):
            match = ACTIVE_DIR_RE.match(entry.name)
            if match:
                active.append(
                    load_task(entry, task_id=match.group(1), slug=match.group(2), created=day.name)
                )

    arch = archive_dir(root)
    if arch.is_dir():
        for entry in sorted(p for p in arch.iterdir() if p.is_dir()):
            match = ARCHIVE_DIR_RE.match(entry.name)
            if match:
                archived.append(
                    load_task(
                        entry,
                        task_id=match.group(2),
                        slug=match.group(3),
                        created=match.group(1),
                        archived_on=match.group(1),
                    )
                )

    seen: dict[str, Path] = {}
    for task in (*active, *archived):
        if task.task_id in seen:
            raise TaskError(
                f"duplicate task id {task.task_id}: {seen[task.task_id]} and {task.path}",
                reason="duplicate_id",
            )
        seen[task.task_id] = task.path
    return active, archived


def next_task_id(active: list[Task], archived: list[Task]) -> str:
    used = [int(t.task_id[1:]) for t in (*active, *archived)]
    return f"T{(max(used) + 1) if used else 1:04d}"


# --------------------------------------------------------------------------- #
# INDEX（纯派生：每次变更后重新扫描生成）
# --------------------------------------------------------------------------- #


def render_index(root: Path, active: list[Task], archived: list[Task]) -> str:
    lines = [
        "# Tasks Index",
        "",
        "由 `taskctl` 扫描 `tasks/` 生成的定位索引，勿手改；事实以各任务 `README.md` 为准。",
        "",
        "## 活跃",
        "",
        "| ID | 名称 | 路径 | status |",
        "|----|------|------|--------|",
    ]
    for task in sorted(active, key=lambda t: t.task_id):
        path = rel(root, task.path)
        lines.append(f"| {task.task_id} | {task.slug} | [{path}/](./{path.removeprefix('tasks/')}/) | {task.status} |")
    if not active:
        lines.append("| — | | | |")
    lines += ["", "## 已归档", "", "| ID | 名称 | 路径 | 归档日 |", "|----|------|------|--------|"]
    for task in sorted(archived, key=lambda t: t.task_id):
        path = rel(root, task.path)
        lines.append(
            f"| {task.task_id} | {task.slug} | [{path}/](./{path.removeprefix('tasks/')}/) | {task.archived_on} |"
        )
    if not archived:
        lines.append("| — | | | |")
    return "\n".join(lines) + "\n"


def sync_index(root: Path) -> dict[str, Any]:
    active, archived = scan_tasks(root)
    write_text(index_path(root), render_index(root, active, archived))
    return {"active": len(active), "archived": len(archived), "path": rel(root, index_path(root))}


# --------------------------------------------------------------------------- #
# README 结构
# --------------------------------------------------------------------------- #


def scaffold_readme(*, task_id: str, slug: str, title: str, created: str) -> str:
    return f"""# {title}

**id：** {task_id}
**status：** draft
**slug：** {slug}
**创建时间：** {created}

---

## 概述

（待补：要做什么、为什么做、做完什么样。信息不全的写「待确认」。）

## {SCOPE_HEADING}

角色只有三种：`必须`（会修改，apply 时切分支）、`建议`（只读参考）、`排除`。

| 逻辑库 | 路径 | 角色 | 说明 |
|--------|------|------|------|
| （待补） | | 必须 | |

## {OPENSPEC_HEADING}

| change | 路径 | 仓库 | 说明 |
|--------|------|------|------|
| — | | | （尚无） |

## {WORK_CONTEXT_HEADING}

由 `taskctl prepare-branches` 写入实际执行环境；apply 前保持「尚未准备」。

| 仓库 | 分支 | 基线 |
|------|------|------|
| （apply 前尚未准备） | | |

## {ACCEPTANCE_HEADING}

- [ ] （待补）

## {VERIFICATION_HEADING}

（apply 收尾写入实际执行的命令与结果；暂缓项连同原因也记在这里。）

## {CHANGELOG_HEADING}

| 日期 | 变更 |
|------|------|
| {created} | 创建任务，状态 draft |
"""


def parse_scope(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    body = section_body(text, SCOPE_HEADING)
    for row in parse_table(body):
        name = cell(row, "逻辑库", "仓库", "名称")
        path = cell(row, "路径", "仓库路径")
        role_label = cell(row, "角色")
        if is_placeholder(name, path):
            continue
        role = ROLE_TO_KEY.get(role_label)
        if role is None:
            raise TaskError(
                f"unknown scope role {role_label!r} for {name or path!r}; expected 必须/建议/排除",
                reason="malformed_scope",
            )
        rows.append({"name": name, "path": path, "role": role, "note": cell(row, "说明")})
    return rows


def parse_openspec(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    body = section_body(text, OPENSPEC_HEADING)
    for row in parse_table(body):
        change = cell(row, "change", "变更")
        if is_placeholder(change):
            continue
        rows.append(
            {
                "change": change,
                "path": cell(row, "路径"),
                "repo": cell(row, "仓库") or ".",
                "note": cell(row, "说明"),
            }
        )
    return rows


def parse_work_context(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    body = section_body(text, WORK_CONTEXT_HEADING)
    for row in parse_table(body):
        repo = cell(row, "仓库", "仓库路径")
        if is_placeholder(repo):
            continue
        rows.append(
            {
                "repo": repo,
                "branch": cell(row, "分支"),
                "base": cell(row, "基线"),
            }
        )
    return rows


def render_work_context(rows: list[dict[str, str]]) -> str:
    lines = [
        "由 `taskctl prepare-branches` 写入实际执行环境；apply 前保持「尚未准备」。",
        "",
        "| 仓库 | 分支 | 基线 |",
        "|------|------|------|",
    ]
    for row in rows or []:
        lines.append(f"| `{row['repo']}` | `{row['branch']}` | `{row['base']}` |")
    if not rows:
        lines.append("| （apply 前尚未准备） | | |")
    return "\n".join(lines)


def parse_acceptance(text: str) -> list[dict[str, Any]]:
    return parse_checkboxes(section_body(text, ACCEPTANCE_HEADING))


def append_changelog(text: str, entry: str) -> str:
    body = section_body(text, CHANGELOG_HEADING)
    rows = [line for line in body.splitlines() if line.strip().startswith("|")]
    if not rows:
        raise TaskError("README missing 变更记录 table", reason="malformed_readme")
    rows.append(f"| {today()} | {entry} |")
    return replace_section(text, CHANGELOG_HEADING, "\n".join(rows))


# --------------------------------------------------------------------------- #
# OpenSpec 进度（checkbox 是唯一进度真相）
# --------------------------------------------------------------------------- #


def planning_root(root: Path, repo: str) -> Path:
    repo = (repo or ".").strip().strip("`")
    return root if repo in {".", ""} else (root / repo)


def change_progress(root: Path, entry: dict[str, str]) -> dict[str, Any]:
    base = planning_root(root, entry["repo"])
    change_dir = base / "openspec" / "changes" / entry["change"]
    report: dict[str, Any] = {
        "change": entry["change"],
        "repo": entry["repo"],
        "planning_root": rel(root, base),
        "tasks_path": rel(root, change_dir / "tasks.md"),
        "readable": False,
        "total": 0,
        "complete": 0,
        "remaining": [],
    }
    tasks_file = change_dir / "tasks.md"
    state = "active"
    if not tasks_file.is_file():
        # 归档识别按 `YYYY-MM-DD-<change>` 整名匹配，避免同名后缀的他人归档被误认。
        archived = sorted(
            path
            for path in (base / "openspec" / "changes" / "archive").glob(f"*-{entry['change']}")
            if re.fullmatch(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(entry['change'])}", path.name)
        )
        if not archived:
            report["state"] = "missing"
            return report
        report["archived_as"] = [rel(root, p) for p in archived]
        state = "archived"
        tasks_file = archived[-1] / "tasks.md"
        if not tasks_file.is_file():
            report["state"] = state
            return report
    items = parse_checkboxes(tasks_file.read_text(encoding="utf-8"))
    report.update(
        readable=True,
        state=state,
        tasks_path=rel(root, tasks_file),
        total=len(items),
        complete=sum(1 for item in items if item["done"]),
        remaining=[item["text"] for item in items if not item["done"]],
    )
    return report


def openspec_reports(root: Path, text: str) -> list[dict[str, Any]]:
    return [change_progress(root, entry) for entry in parse_openspec(text)]


def checkbox_key(text: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)+)\b", text.strip())
    return match.group(1) if match else ""


def markdown_code_text(text: str) -> str:
    """还原暂缓记录中为容纳 checkbox 内部反引号而添加的转义。"""
    return re.sub(r"\\+`", "`", text).replace("\\\\", "\\")


def parse_external_identity(identity: str) -> tuple[str, str]:
    """严格验证 typed external root，不猜测或自动修正调用方意图。"""
    raw = identity.strip()
    if ":" not in raw:
        return "", "legacy_external_identity"
    kind, stable = raw.split(":", 1)
    if kind not in EXTERNAL_KINDS:
        return "", "unsupported_external_kind"
    if not stable or stable == "owner":
        return "", "generic_external_identity"
    if not EXTERNAL_STABLE_ID_RE.fullmatch(stable) or raw != f"{kind}:{stable}":
        return "", "malformed_external_identity"
    return raw, ""


def blocker_target(record: dict[str, Any]) -> tuple[str, str]:
    return record["change"], record["checkbox"]


def blocker_root(record: dict[str, Any]) -> str:
    if record.get("blocked_by"):
        return f"blocked-by {record['blocked_by']}"
    return f"external {record['external']}"


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    """公共诊断不回显仅用于摘要绑定的原始 reason。"""
    return {
        key: value
        for key, value in record.items()
        if key not in {"raw_reason", "blocker_target"}
    }


def summarize_blocker_roots(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(blocker_root(record), []).append(record)
    summaries: list[dict[str, Any]] = []
    for root, items in sorted(grouped.items()):
        summary: dict[str, Any] = {
            "root": root,
            "count": len(items),
            "sample": [
                {"change": item["change"], "checkbox": item["checkbox"]}
                for item in items[:5]
            ],
        }
        details = sorted({item.get("detail", "") for item in items if item.get("detail")})
        if details:
            summary["details"] = details
        summaries.append(summary)
    return summaries


def blocker_confirmation_digest(
    task_id: str,
    reports: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> str:
    remaining = sorted(
        [report["change"], item]
        for report in reports
        for item in report["remaining"]
    )
    mappings = sorted(
        (
            {
                "change": record["change"],
                "checkbox": record["checkbox"],
                "root": blocker_root(record),
                "reason": record.get("raw_reason", ""),
            }
            for record in records
        ),
        key=lambda item: (item["change"], item["checkbox"], item["root"]),
    )
    canonical = json.dumps(
        {"task": task_id, "remaining": remaining, "mappings": mappings},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def analyze_deferrals(root: Path, text: str, reports: list[dict[str, Any]]) -> dict[str, Any]:
    """把 README 暂缓记录与当前 remaining 精确对账，不产生第二份进度状态。"""
    remaining = {
        (report["change"], item)
        for report in reports
        for item in report["remaining"]
    }
    items_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for report in reports:
        tasks_path = Path(report["tasks_path"])
        if not tasks_path.is_absolute():
            tasks_path = root / tasks_path
        if not report["readable"] or not tasks_path.is_file():
            continue
        for item in parse_checkboxes(tasks_path.read_text(encoding="utf-8")):
            key = checkbox_key(item["text"])
            if key:
                items_by_key[(report["change"], key)] = item

    line_re = re.compile(
        r"^\s*-\s*暂缓：`(?P<change>[^`]+)`\s*/\s*`(?P<item>.+)`\s+—\s+(?P<reason>.+?)\s*$"
    )
    blocked_by_re = re.compile(
        r"^blocked-by\s+`(?P<change>[^`]+):(?P<key>[^`]+)`[；;]\s*(?P<detail>.+)$"
    )
    external_re = re.compile(
        r"^external\s+`(?P<identity>[^`]+)`[；;]\s*(?P<detail>.*)$"
    )
    accepted: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    obsolete: list[dict[str, Any]] = []
    covered: set[tuple[str, str]] = set()

    for raw in section_body(text, VERIFICATION_HEADING).splitlines():
        if "暂缓：" not in raw:
            continue
        match = line_re.match(raw)
        if not match:
            invalid.append({"reason": "malformed_deferral"})
            continue
        change = match.group("change").strip()
        item_text = markdown_code_text(match.group("item").strip())
        target = (change, item_text)
        raw_reason = match.group("reason").strip()
        record: dict[str, Any] = {
            "change": change,
            "checkbox": item_text,
            "raw_reason": raw_reason,
        }
        if target not in remaining:
            obsolete.append({"change": change, "checkbox": item_text})
            continue
        if target in covered:
            invalid.append(
                {"change": change, "checkbox": item_text, "reason": "duplicate_deferral"}
            )
            continue

        blocker = blocked_by_re.match(raw_reason)
        external = external_re.match(raw_reason)
        if blocker:
            blocker_identity = (blocker.group("change").strip(), blocker.group("key").strip())
            dependency = items_by_key.get(blocker_identity)
            record["blocked_by"] = f"{blocker_identity[0]}:{blocker_identity[1]}"
            record["detail"] = blocker.group("detail").strip()
            if blocker_identity == (change, checkbox_key(item_text)):
                invalid.append(
                    {"change": change, "checkbox": item_text, "reason": "self_dependency"}
                )
                continue
            if dependency is None:
                invalid.append(
                    {"change": change, "checkbox": item_text, "reason": "unknown_dependency"}
                )
                continue
            if dependency["done"]:
                stale.append(
                    {"change": change, "checkbox": item_text, "reason": "dependency_completed"}
                )
                continue
            record["blocker_target"] = (blocker_identity[0], dependency["text"])
        elif external:
            identity, identity_error = parse_external_identity(external.group("identity"))
            if identity_error:
                invalid.append(
                    {"change": change, "checkbox": item_text, "reason": identity_error}
                )
                continue
            detail = external.group("detail").strip()
            if not detail:
                invalid.append(
                    {"change": change, "checkbox": item_text, "reason": "missing_external_detail"}
                )
                continue
            record.update(external=identity, detail=detail)
        else:
            invalid.append(
                {"change": change, "checkbox": item_text, "reason": "missing_blocker_identity"}
            )
            continue
        covered.add(target)
        accepted.append(record)

    # 依赖必须直接：指向另一条暂缓的记录会制造传递闭包，不能算已判定。
    records: list[dict[str, Any]] = []
    claimed = set(covered)
    for record in accepted:
        target = record.pop("blocker_target", None)
        if target in claimed:
            covered.discard(blocker_target(record))
            invalid.append(
                {
                    "change": record["change"],
                    "checkbox": record["checkbox"],
                    "reason": "transitive_deferral",
                }
            )
            continue
        records.append(record)

    uncovered = [
        {"change": report["change"], "checkbox": item}
        for report in reports
        for item in report["remaining"]
        if (report["change"], item) not in covered
    ]
    return {
        "remaining": len(remaining),
        "covered": len(covered),
        "records": records,
        "uncovered": uncovered,
        "invalid": invalid,
        "stale": stale,
        "obsolete": obsolete,
        "roots": summarize_blocker_roots(records),
    }


def workflow_owned_paths(root: Path, reports: list[dict[str, Any]]) -> list[Path]:
    """归档流程自己会写的路径。

    task 台账和本次 change 的 openspec 落点都是 archive 的产物，不是没交付完的活。
    把它们算进 dirty 会让门禁每次归档必响，逼着调用方无脑放行，反而废掉门禁。
    """
    owned = [tasks_dir(root).resolve()]
    for report in reports:
        openspec = (planning_root(root, report["repo"]) / "openspec").resolve()
        change_dirs = [openspec / "changes" / report["change"]]
        change_dirs += [(root / p).resolve() for p in report.get("archived_as", [])]
        owned += change_dirs
        for change_dir in change_dirs:
            specs = change_dir / "specs"
            if not specs.is_dir():
                continue
            # 外部归档会把 delta 合进这些 capability 的主 spec。
            owned += [openspec / "specs" / cap.name for cap in specs.iterdir() if cap.is_dir()]
    return owned


# --------------------------------------------------------------------------- #
# Git
# --------------------------------------------------------------------------- #


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, **NON_INTERACTIVE_GIT},
    )


def git_toplevel(path: Path) -> Path | None:
    result = run_git(path, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def current_branch(repo: Path) -> str:
    return run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def porcelain_paths(top: Path, line: str) -> list[Path]:
    body = line[3:]
    return [
        (top / part.strip().strip('"')).resolve()
        for part in body.split(" -> ")
        if part.strip()
    ]


def dirty_entries(repo: Path, limit: int = 20, ignore: Sequence[Path] = ()) -> list[str]:
    # 有排除项时逐文件列出：git 默认把未跟踪目录折叠成父目录，折叠后的路径落不进排除范围。
    untracked = ("-uall",) if ignore else ()
    result = run_git(repo, "status", "--porcelain", *untracked)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if ignore:
        top = git_toplevel(repo) or repo
        lines = [
            line
            for line in lines
            if not all(
                any(within(path, parent) for parent in ignore)
                for path in porcelain_paths(top, line)
            )
        ]
    return lines[:limit]


def detect_base(repo: Path, preferred: str = "") -> str:
    if preferred:
        return preferred
    head = run_git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout.strip():
        return head.stdout.strip().rsplit("/", 1)[-1]
    for name in ("main", "master"):
        if run_git(repo, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{name}").returncode == 0:
            return name
    return "main"


# --------------------------------------------------------------------------- #
# 任务定位
# --------------------------------------------------------------------------- #


def match_tasks(tasks: list[Task], query: str) -> list[Task]:
    text = query.strip()
    if not text:
        return []
    try:
        wanted = normalize_id(text)
    except TaskError:
        wanted = ""
    if wanted:
        return [t for t in tasks if t.task_id == wanted]
    needle = text.lower().strip("/")
    exact = [t for t in tasks if t.slug == needle]
    if exact:
        return exact
    return [t for t in tasks if needle in t.slug or needle in t.path.name.lower() or needle in t.title.lower()]


def task_payload(root: Path, task: Task) -> dict[str, Any]:
    return {**task.row(root), "readme": rel(root, task.readme())}


def load_notes(root: Path) -> dict[str, Any]:
    path = notes_path(root)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    sections = {
        match.group(1).strip(): section_body(text, match.group(1).strip()).strip()
        for match in re.finditer(r"^##[ \t]+(.*\S)[ \t]*$", text, re.MULTILINE)
    }
    return {"path": rel(root, path), "sections": sections}


def require_task(root: Path, query: str, *, include_archived: bool = True) -> Task:
    active, archived = scan_tasks(root)
    pool = [*active, *archived] if include_archived else active
    matches = match_tasks(pool, query)
    if not matches:
        raise TaskError(f"no task matches {query!r}", reason="not_found")
    if len(matches) > 1:
        raise TaskError(
            f"{query!r} matches {len(matches)} tasks: {', '.join(t.task_id for t in matches)}",
            reason="ambiguous",
        )
    return matches[0]


# --------------------------------------------------------------------------- #
# 命令
# --------------------------------------------------------------------------- #


def cmd_new(root: Path, args: argparse.Namespace) -> int:
    title = args.title.strip()
    if not title:
        raise TaskError("--title is required", reason="usage")
    slug = validate_slug(args.slug)
    active, archived = scan_tasks(root)
    if any(t.slug == slug for t in active):
        raise TaskError(f"an active task already uses slug {slug!r}", reason="duplicate_slug")
    task_id = next_task_id(active, archived)
    created = today()
    path = tasks_dir(root) / created / f"{task_id}-{slug}"
    if path.exists():
        raise TaskError(f"task directory already exists: {path}", reason="exists")
    write_text(
        path / "README.md",
        scaffold_readme(task_id=task_id, slug=slug, title=title, created=created),
    )
    index = sync_index(root)
    task = require_task(root, task_id)
    return emit(
        {
            "ok": True,
            "result": "new",
            "task": task_payload(root, task),
            "index": index,
            "workflow_notes": load_notes(root),
            "next_action": "补全 README 概述、涉及面与验收标准；方案未定走 task-explore，范围已清走 task-propose",
        },
        summary=f"new: {task_id} at {rel(root, path)}",
    )


def cmd_list(root: Path, args: argparse.Namespace) -> int:
    active, archived = scan_tasks(root)
    payload = {
        "ok": True,
        "result": "list",
        "active": [t.row(root) for t in sorted(active, key=lambda t: t.task_id)],
    }
    if args.archived:
        payload["archived"] = [t.row(root) for t in sorted(archived, key=lambda t: t.task_id)]
    return emit(payload, summary=f"list: {len(active)} active, {len(archived)} archived")


def cmd_resolve(root: Path, args: argparse.Namespace) -> int:
    active, archived = scan_tasks(root)
    queries = [q for q in ([args.query] if args.query else []) + list(args.hint or []) if q.strip()]
    if not queries:
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "no_query",
                "candidates": [t.row(root) for t in sorted(active, key=lambda t: t.task_id)],
                "action": "让用户从 active 任务中选择，或改用 task-new 立项",
            },
            code=2,
            summary="resolve: no query; awaiting user choice",
        )

    matched: list[Task] = []
    for query in queries:
        for task in match_tasks([*active, *archived], query):
            if task not in matched:
                matched.append(task)

    if not matched:
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "not_found",
                "queries": queries,
                "candidates": [t.row(root) for t in sorted(active, key=lambda t: t.task_id)],
                "action": "确认任务编号，或改用 task-new 立项",
            },
            code=2,
            summary=f"resolve: no match for {', '.join(queries)}",
        )
    if len(matched) > 1:
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "ambiguous",
                "queries": queries,
                "candidates": [t.row(root) for t in matched],
                "action": "让用户选定唯一任务后显式传入编号",
            },
            code=2,
            summary=f"resolve: {len(matched)} candidates",
        )

    task = matched[0]
    payload = {
        "ok": True,
        "result": "resolve",
        "command": args.caller or "",
        "task": task_payload(root, task),
        "workflow_notes": load_notes(root),
    }
    if task.archived:
        payload.update(
            ok=False,
            result="needs_confirm",
            reason="archived",
            action=f"任务已归档；确认后用 `restore {task.task_id}` 恢复为 active 再继续",
        )
        return emit(payload, code=2, summary=f"resolve: {task.task_id} is archived")
    return emit(payload, summary=f"resolve: {task.task_id} ({task.status})")


def cmd_status(root: Path, args: argparse.Namespace) -> int:
    task = require_task(root, args.query)
    text = task.text()
    reports = openspec_reports(root, text)
    acceptance = parse_acceptance(text)
    total = sum(r["total"] for r in reports)
    complete = sum(r["complete"] for r in reports)
    payload = {
        "ok": True,
        "result": "status",
        "task": task_payload(root, task),
        "scope": parse_scope(text),
        "work_context": parse_work_context(text),
        "openspec": reports,
        "progress": {"total": total, "complete": complete, "remaining": total - complete},
        "acceptance": {
            "total": len(acceptance),
            "checked": sum(1 for item in acceptance if item["done"]),
            "unchecked": [item["text"] for item in acceptance if not item["done"]],
        },
        "verification": section_body(text, VERIFICATION_HEADING).strip(),
    }
    return emit(
        payload,
        summary=f"status: {task.task_id} {task.status} — checkbox {complete}/{total}",
    )


def cmd_validate_round_end(root: Path, args: argparse.Namespace) -> int:
    task = require_task(root, args.query, include_archived=False)
    text = task.text()
    reports = openspec_reports(root, text)
    analysis = analyze_deferrals(root, text, reports)
    limit = 20
    public_analysis = {
        "remaining": analysis["remaining"],
        "covered": analysis["covered"],
        "records": [public_record(record) for record in analysis["records"][:limit]],
        "record_count": len(analysis["records"]),
        "uncovered": analysis["uncovered"][:limit],
        "uncovered_count": len(analysis["uncovered"]),
        "invalid": analysis["invalid"][:limit],
        "invalid_count": len(analysis["invalid"]),
        "stale": analysis["stale"][:limit],
        "stale_count": len(analysis["stale"]),
        "obsolete_count": len(analysis["obsolete"]),
        "roots": analysis["roots"][:limit],
        "root_count": len(analysis["roots"]),
        "truncated": any(
            len(analysis[name]) > limit
            for name in ("records", "uncovered", "invalid", "stale", "roots")
        ),
    }
    payload: dict[str, Any] = {
        "ok": True,
        "result": "round_end_valid",
        "reason": args.reason,
        "task": task_payload(root, task),
        "deferrals": public_analysis,
    }

    def fail(reason: str, action: str, count: int) -> int:
        payload.update(ok=False, result="round_end_invalid", failure=reason, action=action)
        return emit(payload, code=1, summary=f"validate-round-end: {task.task_id} {reason} ({count})")

    def confirm(reason: str, digest: str) -> int:
        confirm_args = [
            "validate-round-end",
            task.task_id,
            "--root",
            str(root),
            "--reason",
            "all-deferred",
            "--confirm-blockers",
            digest,
        ]
        payload.update(
            ok=False,
            result="needs_confirm",
            failure=reason,
            affected=analysis["roots"],
            prompt=(
                f"确认这 {len(analysis['roots'])} 个 blocker root 确实位于任务范围外，"
                f"并直接阻塞全部 {analysis['remaining']} 项 remaining？任务仍未完成。"
            ),
            confirmation_digest=digest,
            confirm_args=confirm_args,
        )
        return emit(
            payload,
            code=2,
            summary=f"validate-round-end: {task.task_id} {reason} ({analysis['remaining']})",
        )

    if args.reason == "all-deferred":
        blockers = [*analysis["invalid"], *analysis["stale"], *analysis["uncovered"]]
        if blockers:
            return fail(
                "itemization_incomplete",
                "逐项修正无效/陈旧暂缓并处理 uncovered；确认不能覆盖 malformed、legacy、"
                "unknown、self、transitive 或 stale 记录",
                len(blockers),
            )
        if analysis["remaining"]:
            digest = blocker_confirmation_digest(task.task_id, reports, analysis["records"])
            if not args.confirm_blockers:
                return confirm("blocker_confirmation_required", digest)
            if args.confirm_blockers != digest:
                return confirm("blocker_confirmation_stale", digest)
            payload.update(
                ok=True,
                result="global_block_confirmed",
                confirmation_digest=digest,
                blocker_roots=analysis["roots"],
                authorized_action={"command": "set-status", "args": [task.task_id, "blocked"]},
                action=(
                    f"当前摘要绑定的 {analysis['remaining']} 项 remaining 已获用户确认；"
                    "可将 task 设置为 blocked，并逐 root 报告所需输入与解除条件。"
                    "任务仍未完成，不得使用完成模板、archive bridge 或 task-level success"
                ),
            )
            return emit(
                payload,
                summary=f"validate-round-end: {task.task_id} global_block_confirmed",
            )

    if args.reason == "budget-exhausted":
        deferred_targets = {blocker_target(record) for record in analysis["records"]}
        unjudged = [
            {"change": report["change"], "checkbox": item}
            for report in reports
            for item in report["remaining"]
            if (report["change"], item) not in deferred_targets
        ]
        payload["unjudged"] = unjudged[:limit]
        payload["unjudged_count"] = len(unjudged)
        payload["deferred_count"] = len(deferred_targets)
        warnings = [*analysis["invalid"], *analysis["stale"]]
        payload["warnings"] = warnings[:limit]
        payload["warning_count"] = len(warnings)
        payload["action"] = (
            f"如实按暂缓 {len(deferred_targets)} 项 + 未判定 {len(unjudged)} 项分开报告并给出续跑锚点"
            + ("；无效或陈旧记录已降级为未判定，下一轮必须重判" if warnings else "")
        )
    return emit(
        payload,
        summary=(
            f"validate-round-end: {task.task_id} {args.reason} — "
            f"{analysis['covered']}/{analysis['remaining']} current deferral(s)"
        ),
    )


def cmd_set_status(root: Path, args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        raise TaskError(
            f"invalid status {args.status!r}; expected one of {', '.join(STATUSES)}",
            reason="invalid_status",
        )
    if args.status == "archived":
        raise TaskError("use `archive` to archive a task", reason="usage")
    task = require_task(root, args.query, include_archived=False)
    text = set_frontmatter_field(task.text(), "status", args.status)
    text = append_changelog(text, f"状态 {task.status} → {args.status}")
    write_text(task.readme(), text)
    index = sync_index(root)
    return emit(
        {
            "ok": True,
            "result": "set_status",
            "task": {**task.row(root), "status": args.status},
            "previous_status": task.status,
            "index": index,
        },
        summary=f"set-status: {task.task_id} {task.status} → {args.status}",
    )


def cmd_prepare_branches(root: Path, args: argparse.Namespace) -> int:
    prefix = (args.prefix or "feat").strip().lower()
    if prefix not in BRANCH_PREFIXES:
        raise TaskError(
            f"invalid prefix {prefix!r}; expected one of {', '.join(BRANCH_PREFIXES)}",
            reason="invalid_prefix",
        )
    task = require_task(root, args.query, include_archived=False)
    text = task.text()
    branch = f"{prefix}-{task.slug}"
    must = [row for row in parse_scope(text) if row["role"] == "must"]
    if not must:
        raise TaskError(
            "no 必须 repository in 涉及面; fill the scope table before apply",
            reason="no_must_repo",
        )

    prepared: list[dict[str, str]] = []
    blocked: list[dict[str, Any]] = []
    for row in must:
        repo_rel = row["path"]
        repo = (root / repo_rel).resolve() if repo_rel not in {".", ""} else root
        record: dict[str, Any] = {"repo": repo_rel, "branch": branch}
        if not repo.is_dir():
            blocked.append({**record, "reason": "missing_repo", "action": f"确认路径 {repo_rel} 是否存在"})
            continue
        top = git_toplevel(repo)
        if top is None or top.resolve() != repo:
            blocked.append(
                {**record, "reason": "not_git_root", "action": f"{repo_rel} 不是 git 仓库根，修正涉及面表"}
            )
            continue

        cur = current_branch(repo)
        if cur == branch:
            base = detect_base(repo, args.base)
            prepared.append({"repo": repo_rel, "branch": branch, "base": base, "action": "reused"})
            continue

        dirty = dirty_entries(repo)
        if dirty:
            blocked.append(
                {
                    **record,
                    "reason": "dirty",
                    "current_branch": cur,
                    "dirty": dirty,
                    "action": f"由用户处理 {repo_rel} 的未提交改动后重试；不要自动 stash/reset/force",
                }
            )
            continue

        fetch = run_git(repo, "fetch", "origin", "--quiet")
        if fetch.returncode != 0:
            blocked.append(
                {
                    **record,
                    "reason": "fetch_failed",
                    "stderr": fetch.stderr.strip()[:400],
                    "action": f"确认 {repo_rel} 的 origin 可达后重试",
                }
            )
            continue

        base = detect_base(repo, args.base)
        start = f"origin/{base}" if run_git(repo, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{base}").returncode == 0 else base
        checkout = run_git(repo, "checkout", "-B", branch, start)
        if checkout.returncode != 0:
            blocked.append(
                {
                    **record,
                    "reason": "checkout_failed",
                    "stderr": checkout.stderr.strip()[:400],
                    "action": f"手动检查 {repo_rel} 后重试",
                }
            )
            continue
        prepared.append({"repo": repo_rel, "branch": branch, "base": base, "action": "switched"})

    payload = {
        "ok": not blocked,
        "result": "prepare_branches",
        "task": task.row(root),
        "branch": branch,
        "prepared": prepared,
        "blocked": blocked,
    }
    if prepared and not args.dry_run:
        merged = {row["repo"]: row for row in parse_work_context(text)}
        merged.update({row["repo"]: row for row in prepared})
        updated = replace_section(
            text, WORK_CONTEXT_HEADING, render_work_context(list(merged.values()))
        )
        if task.status in {"proposed", "draft", "exploring", "designed"}:
            updated = set_frontmatter_field(updated, "status", "in_progress")
            updated = append_changelog(updated, f"apply 准备分支 `{branch}`，状态 → in_progress")
            payload["task"] = {**task.row(root), "status": "in_progress"}
        write_text(task.readme(), updated)
        sync_index(root)

    if blocked:
        payload["action"] = "原样报告 blocked 项并等用户处理；已准备好的仓保留，可直接重试"
        return emit(payload, code=2, summary=f"prepare-branches: {len(blocked)} blocked, {len(prepared)} ready")
    return emit(payload, summary=f"prepare-branches: {branch} ready in {len(prepared)} repo(s)")


def cmd_archive(root: Path, args: argparse.Namespace) -> int:
    task = require_task(root, args.query, include_archived=False)
    text = task.text()
    reports = openspec_reports(root, text)
    acceptance = parse_acceptance(text)

    confirms: list[dict[str, Any]] = []
    remaining = [r for r in reports if r["state"] == "active" and r["remaining"]]
    if remaining:
        confirms.append(
            {
                "gate": "openspec_remaining",
                "prompt": "OpenSpec checkbox 未全部完成，是继续归档还是先补完？",
                "affected": [
                    {"change": r["change"], "remaining": r["remaining"][:10], "count": len(r["remaining"])}
                    for r in remaining
                ],
            }
        )
    unreadable = [r for r in reports if r["state"] == "missing"]
    if unreadable:
        raise TaskError(
            "openspec change not found: " + ", ".join(r["change"] for r in unreadable),
            reason="missing_openspec",
            affected=[r["tasks_path"] for r in unreadable],
        )
    unchecked = [item["text"] for item in acceptance if not item["done"]]
    if unchecked:
        confirms.append(
            {
                "gate": "unchecked_acceptance",
                "prompt": "验收标准仍有未勾项，是继续归档还是先验收？",
                "affected": unchecked,
            }
        )

    owned = workflow_owned_paths(root, reports)
    dirty_repos: list[dict[str, Any]] = []
    for row in parse_work_context(text):
        repo = (root / row["repo"]).resolve() if row["repo"] not in {".", ""} else root
        if not repo.is_dir() or git_toplevel(repo) is None:
            continue
        entries = dirty_entries(repo, ignore=owned)
        if entries:
            dirty_repos.append({"repo": row["repo"], "dirty": entries})
    if dirty_repos:
        confirms.append(
            {
                "gate": "dirty_delivery",
                "prompt": "交付仓还有未提交改动（已排除 task 台账与本次 change 的 openspec 落点），是继续归档还是先提交？",
                "affected": dirty_repos,
            }
        )

    active_changes = [r["change"] for r in reports if r["state"] == "active"]
    payload: dict[str, Any] = {
        "ok": not confirms or args.confirmed,
        "result": "archive_preflight" if args.dry_run else "archive",
        "task": task.row(root),
        "openspec": reports,
        "pending_openspec_archive": active_changes,
        "acceptance": {"total": len(acceptance), "unchecked": unchecked},
        "confirmations": confirms,
    }

    if confirms and not args.confirmed:
        payload["action"] = (
            "待确认，不是失败：把每个 gate 的 affected 原样报给用户，逐条问「继续归档还是先补完」，"
            "得到明确同意后用 confirm_command 重跑；没同意就停在这里"
        )
        payload["confirm_command"] = f"archive {task.task_id} --confirmed"
        return emit(payload, code=2, summary=f"archive: {len(confirms)} confirmation(s) required")

    if args.dry_run:
        # 落盘会重算 gate，确认过的项要继续带着 --confirmed 才不会再次卡住。
        final = f"archive {task.task_id}" + (" --confirmed" if confirms else "")
        payload["next_action"] = (
            f"按 archive.md 第 2 节在各 planning root 下用 openspec CLI 归档 "
            f"{', '.join(active_changes)}，再跑 `{final}`"
            if active_changes
            else f"可直接 `{final}` 完成归档"
        )
        return emit(payload, summary=f"archive preflight: {task.task_id} clear")

    if active_changes:
        raise TaskError(
            "openspec changes still active: " + ", ".join(active_changes),
            reason="openspec_not_archived",
            affected=active_changes,
        )

    archived_on = today()
    dest = archive_dir(root) / f"{archived_on}-{task.task_id}-{task.slug}"
    if dest.exists():
        raise TaskError(f"archive destination already exists: {dest}", reason="exists")

    overrides = [describe_override(c) for c in confirms]
    updated = set_frontmatter_field(text, "status", "archived")
    updated = append_changelog(updated, f"归档至 `{rel(root, dest)}`")
    write_text(task.readme(), updated)
    write_text(
        task.path / "changes.md",
        render_changes_md(root, task, reports, parse_work_context(text), overrides, archived_on),
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task.path), str(dest))
    prune_empty_dirs(tasks_dir(root))
    index = sync_index(root)

    payload.update(
        ok=True,
        result="archived",
        archived_path=rel(root, dest),
        overrides=overrides,
        index=index,
    )
    payload["task"] = {**task.row(root), "status": "archived", "path": rel(root, dest)}
    return emit(payload, summary=f"archive: {task.task_id} → {rel(root, dest)}")


def describe_override(confirm: dict[str, Any]) -> str:
    """`--confirmed` 不分 gate，归档记录里必须写清它实际放行了什么。"""
    gate = confirm["gate"]
    affected = confirm["affected"]
    if gate == "openspec_remaining":
        detail = "，".join(f"{item['change']} {item['count']} 项未勾" for item in affected)
    elif gate == "dirty_delivery":
        detail = "，".join(f"{item['repo']} {len(item['dirty'])} 处未提交" for item in affected)
    else:
        detail = f"{len(affected)} 项未勾"
    return f"{gate}：{detail}"


def render_changes_md(
    root: Path,
    task: Task,
    reports: list[dict[str, Any]],
    work_context: list[dict[str, str]],
    overrides: list[str],
    archived_on: str,
) -> str:
    lines = [
        f"# {task.task_id} 归档记录",
        "",
        f"**归档日：** {archived_on}",
        "",
        "## 交付仓库",
        "",
        "| 仓库 | 分支 | 基线 |",
        "|------|------|------|",
    ]
    for row in work_context or []:
        lines.append(f"| `{row['repo']}` | `{row['branch']}` | `{row['base']}` |")
    if not work_context:
        lines.append("| （无） | | |")
    lines += ["", "## OpenSpec changes", "", "| change | 仓库 | 状态 | checkbox |", "|--------|------|------|----------|"]
    for report in reports:
        lines.append(
            f"| `{report['change']}` | `{report['repo']}` | {report['state']} | {report['complete']}/{report['total']} |"
        )
    if not reports:
        lines.append("| （无） | | | |")
    lines += ["", "## 门禁覆盖", ""]
    lines.append("\n".join(f"- `{item}`" for item in overrides) if overrides else "（无）")
    return "\n".join(lines) + "\n"


def prune_empty_dirs(base: Path) -> None:
    for day in sorted(p for p in base.iterdir() if p.is_dir() and DATE_DIR_RE.match(p.name)):
        if not any(day.iterdir()):
            day.rmdir()


def cmd_restore(root: Path, args: argparse.Namespace) -> int:
    active, archived = scan_tasks(root)
    matches = match_tasks(archived, args.query)
    if len(matches) != 1:
        raise TaskError(
            f"{args.query!r} matches {len(matches)} archived tasks", reason="not_found"
        )
    task = matches[0]
    status = args.status or "in_progress"
    if status not in STATUSES or status == "archived":
        raise TaskError(f"invalid restore status {status!r}", reason="invalid_status")
    dest = tasks_dir(root) / task.created / f"{task.task_id}-{task.slug}"
    if dest.exists():
        raise TaskError(f"restore destination already exists: {dest}", reason="exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task.path), str(dest))
    text = (dest / "README.md").read_text(encoding="utf-8")
    text = set_frontmatter_field(text, "status", status)
    text = append_changelog(text, f"从归档恢复，状态 → {status}")
    write_text(dest / "README.md", text)
    index = sync_index(root)
    return emit(
        {
            "ok": True,
            "result": "restore",
            "task": {**task.row(root), "status": status, "path": rel(root, dest), "archived_on": ""},
            "index": index,
        },
        summary=f"restore: {task.task_id} → {rel(root, dest)}",
    )


def cmd_notes(root: Path, args: argparse.Namespace) -> int:
    path = notes_path(root)
    if args.set_section:
        if args.body is None:
            raise TaskError("--set-section requires --body", reason="usage")
        heading = args.set_section.strip()
        text = path.read_text(encoding="utf-8") if path.is_file() else f"# {root.name} 工作区笔记\n"
        if heading_pattern(heading).search(text):
            text = replace_section(text, heading, args.body)
        else:
            text = text.rstrip("\n") + f"\n\n## {heading}\n\n{args.body.strip()}\n"
        write_text(path, text)
        return emit(
            {"ok": True, "result": "notes_updated", "section": heading, **load_notes(root)},
            summary=f"notes: updated {heading}",
        )
    notes = load_notes(root)
    return emit(
        {"ok": True, "result": "notes", "exists": bool(notes), **notes},
        summary=f"notes: {len(notes.get('sections', {}))} section(s)",
    )


def cmd_sync_index(root: Path, args: argparse.Namespace) -> int:
    index = sync_index(root)
    return emit(
        {"ok": True, "result": "sync_index", "index": index},
        summary=f"sync-index: {index['active']} active, {index['archived']} archived",
    )


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

COMMANDS = {
    "new": cmd_new,
    "list": cmd_list,
    "resolve": cmd_resolve,
    "status": cmd_status,
    "validate-round-end": cmd_validate_round_end,
    "set-status": cmd_set_status,
    "prepare-branches": cmd_prepare_branches,
    "archive": cmd_archive,
    "restore": cmd_restore,
    "notes": cmd_notes,
    "sync-index": cmd_sync_index,
}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # noqa: ANN401
        emit({"ok": False, "result": "error", "reason": "usage", "error": message}, code=1)
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    # argparse 让子解析器的默认值覆盖父解析器的同名 dest，所以全局与子命令各用一个
    # dest，再由 resolve_root 合并；两处都给且值不同即报错。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", dest="sub_root", help="workspace root containing tasks/")

    parser = Parser(prog="taskctl", description=__doc__)
    parser.add_argument("--root", dest="global_root", help="workspace root containing tasks/")
    subs = parser.add_subparsers(dest="command", required=True)

    def add(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        return subs.add_parser(name, parents=[common], **kwargs)

    new = add("new", help="创建任务目录与 README 骨架")
    new.add_argument("--title", required=True)
    new.add_argument("--slug", required=True)

    listing = add("list", help="列出任务")
    listing.add_argument("--archived", action="store_true")

    resolve = add("resolve", help="定位唯一任务；不唯一时退出码 2")
    resolve.add_argument("query", nargs="?")
    resolve.add_argument("--hint", action="append", help="启发式关键词，可重复")
    # dest 不能叫 command：会覆盖 add_subparsers(dest="command") 写入的子命令名
    resolve.add_argument("--command", dest="caller", help="调用方 task-* 命令名")

    status = add("status", help="只读进度：README 事实 + OpenSpec checkbox 统计")
    status.add_argument("query")

    validate_round_end = add("validate-round-end", help="结束 apply 本轮前对账逐项暂缓与 remaining")
    validate_round_end.add_argument("query")
    validate_round_end.add_argument(
        "--reason",
        required=True,
        choices=("all-deferred", "budget-exhausted"),
    )
    validate_round_end.add_argument(
        "--confirm-blockers",
        metavar="SHA256",
        help="确认当前 remaining 到 blocker roots 的精确摘要；事实变化后自动失效",
    )

    set_status = add("set-status", help="手动设置 status")
    set_status.add_argument("query")
    set_status.add_argument("status")

    prepare = add("prepare-branches", help="把必须仓切到任务分支；dirty/fetch 失败即 fail closed")
    prepare.add_argument("query")
    prepare.add_argument("--prefix", default="feat", help=f"分支前缀，默认 feat；可选 {', '.join(BRANCH_PREFIXES)}")
    prepare.add_argument("--base", default="", help="基线分支，默认探测 origin/HEAD")
    prepare.add_argument("--dry-run", action="store_true")

    archive = add("archive", help="归档校验与落盘；--dry-run 只做预检")
    archive.add_argument("query")
    archive.add_argument("--dry-run", action="store_true")
    archive.add_argument(
        "--confirmed",
        action="store_true",
        help="用户已逐条确认上一次报出的全部 gate；实际放行项写入 changes.md",
    )

    restore = add("restore", help="把归档任务恢复为 active")
    restore.add_argument("query")
    restore.add_argument("--status", default="in_progress")

    notes = add("notes", help="读写工作区 .task-workflow.md")
    notes.add_argument("--set-section")
    notes.add_argument("--body")

    add("sync-index", help="按 tasks/ 实际目录重建 INDEX.md")
    return parser


def resolve_root(args: argparse.Namespace) -> Path:
    given = {
        value
        for value in (getattr(args, "global_root", None), getattr(args, "sub_root", None))
        if value
    }
    if len(given) > 1:
        raise TaskError(
            f"conflicting --root values: {', '.join(sorted(given))}", reason="usage"
        )
    if given:
        root = Path(given.pop()).expanduser().resolve()
        if not tasks_dir(root).is_dir():
            raise TaskError(f"missing tasks/ under {root}", reason="workspace_not_found")
        return root
    return find_workspace()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        return COMMANDS[args.command](resolve_root(args), args)
    except TaskError as exc:
        return emit(
            {
                "ok": False,
                "result": "error",
                "reason": exc.reason,
                "error": str(exc),
                **exc.details,
            },
            code=1,
            summary=f"{args.command}: {exc}",
        )


if __name__ == "__main__":
    raise SystemExit(main())
