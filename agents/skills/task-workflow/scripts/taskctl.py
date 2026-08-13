#!/usr/bin/env python3
"""Deterministic helpers for task-* bookkeeping (Gate / INDEX / scaffold / archive / git).

Invoke from this skill directory (the folder that contains SKILL.md), not the project root:

  python3 scripts/taskctl.py list
  python3 scripts/taskctl.py resolve T0002 --command task-apply
  python3 scripts/taskctl.py resolve --infer --command task-apply --hint "继续 T0002"
  python3 scripts/taskctl.py set-status T0002 exploring
  python3 scripts/taskctl.py new --slug my-feature --title "标题"
  python3 scripts/taskctl.py archive T0002
  python3 scripts/taskctl.py prepare-branches --slug my-feature --repo .
  python3 scripts/taskctl.py git-summary --repo . --branch feat-my-feature

`--root` defaults to the nearest ancestor that contains `tasks/`.
`--repo` is a workspace-relative path to a git root (`.` for a single-repo workspace).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
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
        "label": "中止，稍后再执行 task-apply",
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


@dataclass
class TaskInfo:
    task_id: str
    task_root: str
    slug: str
    name: str
    status: str
    readme: str
    openspec: list[dict[str, str]] = field(default_factory=list)
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


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "tasks" / "INDEX.md").is_file() or (p / "tasks").is_dir():
            return p
    raise TaskError("cannot locate workspace root (need tasks/)")


def index_path(root: Path) -> Path:
    return root / "tasks" / "INDEX.md"


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
    for line in lines[start:]:
        if re.match(r"^#{2,3}\s+", line):
            break
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells:
                continue
            if set(cells[0]) <= {"-", ":"} or cells[0].lower() in {"change", "名称", "name"}:
                in_table = True
                continue
            if not in_table:
                continue
            name = strip_md_link(cells[0]).strip("`")
            path = strip_md_link(cells[1]).strip("`") if len(cells) > 1 else ""
            if name and name not in {"—", "-", "（尚无）"}:
                rows.append({"name": name, "path": path})
        elif in_table and line.strip() == "":
            break
    return rows


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_index(next_id, active, archived), encoding="utf-8")


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
) -> str:
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

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| （待补） | `.` 或 `path/to/repo` | 必须 / 建议 / 排除 |

### 关联 OpenSpec

| change | 路径 | 说明 |
|--------|------|------|
| — | | （尚无） |

### 设计文档

| 文档 | 类型 | 归档落点 |
|------|------|----------|
| — | | （无；复杂任务经 task-design 写入 `design/`） |

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

    return {
        "input": logical,
        "git_root": git_rel_out,
        "git_root_abs": str(git_root),
        "excluded_by_default": any(m in rel_parts for m in DEFAULT_EXCLUDE_REPO_MARKERS),
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

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in args.repos:
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

        repo = Path(info["git_root_abs"])
        entry: dict[str, Any] = {
            "input": raw,
            "git_root": info["git_root"],
            "branch": branch,
            "action": "pending",
        }
        try:
            if is_dirty(repo):
                if args.skip_dirty:
                    entry["action"] = "skipped_dirty"
                    entry["dirty"] = True
                    entry["dirty_porcelain"] = dirty_porcelain(repo)
                    results.append(entry)
                    continue
                errors.append(blocked_dirty_entry(entry, repo))
                continue

            cur = current_branch(repo)
            entry["current_branch"] = cur
            if cur == branch:
                entry["action"] = "already_on_branch"
                results.append(entry)
                continue

            # Detect default branch before mutating (may be develop/trunk/…).
            base = detect_base_branch(repo, args.base)
            entry["base"] = base
            entry["base_source"] = "explicit" if args.base else "default_branch"

            if args.dry_run:
                entry["action"] = "would_create"
                entry["plan"] = [
                    "fetch origin",
                    f"checkout {base}",
                    f"pull --ff-only origin {base}",
                    f"checkout -b {branch}",
                ]
                results.append(entry)
                continue

            # Always refresh from remote default before creating the feature branch.
            fetch = run_git(repo, "fetch", "origin")
            entry["fetch_ok"] = fetch.returncode == 0
            if fetch.returncode != 0:
                tail = (fetch.stderr or "").strip().splitlines()
                if tail:
                    entry["fetch_stderr"] = tail[-1]

            # Re-detect after fetch so origin/HEAD is current.
            if not args.base:
                base = detect_base_branch(repo, None)
                entry["base"] = base

            has_origin_base = (
                run_git(repo, "rev-parse", "--verify", f"origin/{base}").returncode == 0
            )
            co = run_git(repo, "checkout", base)
            if co.returncode != 0 and has_origin_base:
                co = run_git(repo, "checkout", "-B", base, f"origin/{base}")
            if co.returncode != 0:
                raise TaskError((co.stderr or co.stdout or "checkout default branch failed").strip())

            if has_origin_base or entry.get("fetch_ok"):
                pull = run_git(repo, "pull", "--ff-only", "origin", base)
                entry["pull_ok"] = pull.returncode == 0
                if pull.returncode != 0:
                    # Local-only repos often fail pull; only block when origin/base exists.
                    if has_origin_base:
                        tail = (pull.stderr or "").strip().splitlines()
                        err = blocked_pull_entry(entry, tail[-1] if tail else pull.stderr)
                        errors.append(err)
                        continue
                    tail = (pull.stderr or "").strip().splitlines()
                    if tail:
                        entry["pull_stderr"] = tail[-1]
            else:
                entry["pull_ok"] = False
                entry["pull_skipped"] = "no origin/<base>"

            exists = run_git(repo, "rev-parse", "--verify", f"refs/heads/{branch}")
            if exists.returncode == 0:
                sw = run_git(repo, "checkout", branch)
                if sw.returncode != 0:
                    raise TaskError((sw.stderr or "checkout existing branch failed").strip())
                entry["action"] = "checked_out_existing"
            else:
                created = run_git(repo, "checkout", "-b", branch)
                if created.returncode != 0:
                    raise TaskError((created.stderr or "checkout -b failed").strip())
                entry["action"] = "created"

            entry["current_branch"] = current_branch(repo)
            results.append(entry)
        except TaskError as e:
            entry["action"] = "error"
            entry["error"] = str(e)
            entry["needs_user_confirm"] = True
            errors.append(entry)

    ok = not errors
    needs_confirm = any(e.get("needs_user_confirm") for e in errors)
    confirm_lines = [
        "## 分支准备需要你确认",
        "",
        "写代码前须先基于**远端默认分支**拉最新并检出新分支；下列仓库被阻断：",
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

        repo = Path(info["git_root_abs"])
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
                    }
                )
                if len(files) >= max_files:
                    break

        stat = run_git(repo, "diff", "--stat", range_spec)
        stat_text = stat.stdout.strip() if stat.returncode == 0 else ""

        entry = {
            "input": raw,
            "git_root": key,
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
                md_parts.append(f"- `{f['status']}` `{f['repo_path']}`")
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
                {
                    "ok": True,
                    "result": "unique",
                    "confidence": "deterministic",
                    "reason": "explicit_query",
                    "task": asdict(info),
                }
            )
        result = "zero" if not matches else "multi"
        payload = {
            "ok": False,
            "result": result,
            "confidence": "deterministic",
            "matches": [asdict(m) for m in matches],
            "active": [asdict(i) for i in infos],
            "exit_markdown": exit_markdown(infos if result == "zero" else matches, command),
        }
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
        return emit(inferred)

    # needs_confirm / zero
    print("任务推断需要确认", file=sys.stderr)
    return emit(inferred, code=2)


def cmd_set_status(root: Path, args: argparse.Namespace) -> int:
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
        readme.write_text(new_text if new_text.endswith("\n") else new_text + "\n", encoding="utf-8")
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


def cmd_new(root: Path, args: argparse.Namespace) -> int:
    slug = validate_slug(args.slug)
    title = (args.title or slug).strip()
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

    if args.dry_run:
        return emit(
            {
                "ok": True,
                "result": "dry_run",
                "taskId": task_id,
                "taskRoot": rel,
                "next_id_after": next_id + 1,
            }
        )

    task_root.mkdir(parents=True, exist_ok=False)
    readme = task_root / "README.md"
    readme.write_text(
        scaffold_readme(task_id=task_id, slug=slug, title=title, created=created),
        encoding="utf-8",
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
    return emit({"ok": True, "result": "created", "task": asdict(info)})


def cmd_archive(root: Path, args: argparse.Namespace) -> int:
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

    readme = src / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(set_readme_status(text, "archived") + ("" if text.endswith("\n") else "\n"), encoding="utf-8")

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
    new_p.add_argument("--slug", required=True)
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
    arch_p.set_defaults(func=cmd_archive)

    roots_p = sub.add_parser("repo-roots", help="resolve workspace-relative paths to unique git roots")
    roots_p.add_argument("repos", nargs="+", help="workspace-relative git path (`.` = workspace)")
    roots_p.add_argument(
        "--include-excluded",
        action="store_true",
        help="allow roots matching default exclude markers (none by default)",
    )
    roots_p.set_defaults(func=cmd_repo_roots)

    prep_p = sub.add_parser(
        "prepare-branches",
        help="git safety check + create/checkout <prefix>-<slug> on target git repos",
    )
    prep_p.add_argument("--slug", required=True, help="task slug (not TNNNN dirname)")
    prep_p.add_argument(
        "--repo",
        dest="repos",
        action="append",
        required=True,
        help="workspace-relative git path; repeatable (`.` = workspace)",
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


if __name__ == "__main__":
    raise SystemExit(main())
