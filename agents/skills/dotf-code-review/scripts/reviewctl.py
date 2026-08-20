#!/usr/bin/env python3
"""Helpers for /dotf-code-review: resolve repositories, inspect change source, parse MR/PR, and write docs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    "target",
    ".tox",
}
PRIORITY_ORDER = ("P0", "P1", "P2", "P3", "P4")
GITLAB_MR = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<project>.+?)/-/?merge_requests/(?P<iid>\d+)(?:[/?#].*)?$",
    re.I,
)
GITLAB_MR_ALT = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<project>.+?)/merge_requests/(?P<iid>\d+)(?:[/?#].*)?$",
    re.I,
)
GITHUB_PR = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<iid>\d+)(?:[/?#].*)?$",
    re.I,
)
P0_RE = re.compile(
    r"(sql\s*injection|xss|rce|auth(?:entication)? bypass|越权|数据丢失|secret|凭证泄露|"
    r"任意文件|路径穿越|panic\b|segfault|生产事故|P0)",
    re.I,
)
P1_RE = re.compile(
    r"(race|deadlock|nil deref|npe|空指针|正确性|逻辑错误|并发安全|数据竞争|丢事件|"
    r"broken api|崩溃|crash|P1)",
    re.I,
)
P2_RE = re.compile(
    r"(error handling|missing test|缺少测试|可维护|资源泄露|timeout|重试|P2)",
    re.I,
)


class ReviewError(Exception):
    pass


def repo_root_from_script() -> Path:
    return Path.cwd()


def git(args: list[str], cwd: Path, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ReviewError(f"git {' '.join(args)} failed: {err}")
    return (proc.stdout or "").strip()


def iter_git_roots(codes: Path, max_depth: int = 8) -> list[Path]:
    if not codes.exists():
        return []
    start = codes.resolve()
    skip_expr: list[str] = []
    for name in sorted(SKIP_DIRS - {".git"}):
        skip_expr += ["-name", name, "-o"]
    find_cmd = [
        "find",
        str(start),
        "-maxdepth",
        str(max_depth),
        "(",
        *skip_expr[:-1],
        ")",
        "-prune",
        "-o",
        "-name",
        ".git",
        "-prune",
        "-print",
    ]
    proc = subprocess.run(find_cmd, capture_output=True, text=True, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return [Path(line).parent for line in proc.stdout.splitlines() if line.strip()]

    roots: list[Path] = []

    def walk(path: Path, depth: int) -> None:
        if (path / ".git").exists():
            roots.append(path)
        if depth >= max_depth:
            return
        try:
            entries = list(path.iterdir())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir() or entry.name in SKIP_DIRS:
                continue
            walk(entry, depth + 1)

    walk(start, 0)
    return roots


def find_git_root(path: Path) -> Path | None:
    cur = path if path.is_dir() else path.parent
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def resolve_repo(work_root: Path, raw: str) -> dict[str, Any]:
    name = raw.strip().rstrip("/")
    if not name:
        raise ReviewError("repo name is empty")

    workspace = work_root.resolve()
    if name in {"workspace", ".", str(workspace)}:
        if (workspace / ".git").exists():
            return {
                "input": name,
                "git_root": ".",
                "git_root_abs": str(workspace),
                "basename": workspace.name,
            }
        raise ReviewError("workspace root is not a Git repository; specify a repository path")

    path = Path(name).expanduser()
    if path.is_absolute():
        target = path
        if not target.exists():
            raise ReviewError(f"path does not exist: {name}")
    else:
        candidate = workspace / path
        target = candidate if candidate.exists() else None

    if target is not None:
        git_root = find_git_root(target.resolve())
        if git_root is None:
            raise ReviewError(f"no git root for: {name}")
        rel = _rel_display(work_root, git_root)
        return {
            "input": name,
            "git_root": rel,
            "git_root_abs": str(git_root),
            "basename": git_root.name,
        }

    roots = ([workspace] if (workspace / ".git").exists() else []) + iter_git_roots(workspace)
    exact = [p for p in roots if p.name == name]
    if len(exact) == 1:
        git_root = exact[0]
        return {
            "input": name,
            "git_root": _rel_display(work_root, git_root),
            "git_root_abs": str(git_root),
            "basename": git_root.name,
        }
    if len(exact) > 1:
        return {
            "input": name,
            "ambiguous": True,
            "candidates": [_rel_display(work_root, p) for p in exact],
        }

    suffix = [p for p in roots if p.as_posix().endswith("/" + name)]
    if len(suffix) == 1:
        git_root = suffix[0]
        return {
            "input": name,
            "git_root": _rel_display(work_root, git_root),
            "git_root_abs": str(git_root),
            "basename": git_root.name,
        }
    if suffix:
        return {
            "input": name,
            "ambiguous": True,
            "candidates": [_rel_display(work_root, p) for p in suffix],
        }
    raise ReviewError(f"repo not found under workspace root: {name}")


def _rel_display(work_root: Path, git_root: Path) -> str:
    try:
        rel = git_root.resolve().relative_to(work_root.resolve()).as_posix()
        return rel if rel != "." else "."
    except ValueError:
        return str(git_root)


def default_branch(git_root: Path) -> str:
    head = git(["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], git_root, check=False)
    if head:
        return head.replace("refs/remotes/origin/", "").strip()
    for name in ("main", "master", "develop"):
        exists = git(["rev-parse", "--verify", "--quiet", name], git_root, check=False)
        remote = git(["rev-parse", "--verify", "--quiet", f"origin/{name}"], git_root, check=False)
        if exists or remote:
            return name
    current = git(["rev-parse", "--abbrev-ref", "HEAD"], git_root, check=False)
    return current or "main"


def comparison_ref(git_root: Path, branch: str) -> str:
    remote = git(["rev-parse", "--verify", "--quiet", f"origin/{branch}"], git_root, check=False)
    if remote:
        return f"origin/{branch}"
    return branch


def inspect_repo(work_root: Path, raw: str) -> dict[str, Any]:
    resolved = resolve_repo(work_root, raw)
    if resolved.get("ambiguous"):
        return resolved
    git_root = Path(resolved["git_root_abs"])
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], git_root, check=False) or "HEAD"
    porcelain = git(["status", "--porcelain"], git_root, check=False)
    dirty_paths = [line[3:] for line in porcelain.splitlines() if line.strip()]
    base = default_branch(git_root)
    cmp_ref = comparison_ref(git_root, base)
    ahead = 0
    if git(["rev-parse", "--verify", "--quiet", cmp_ref], git_root, check=False):
        count = git(["rev-list", "--count", f"{cmp_ref}..HEAD"], git_root, check=False)
        ahead = int(count or "0")
    dirty = bool(dirty_paths)
    on_default = branch == base or branch == f"origin/{base}"
    if dirty and ahead:
        recommendation = "ask"
        reason = "同时存在未提交改动和相对默认分支的提交，需用户确认审查范围"
    elif dirty:
        recommendation = "uncommitted"
        reason = "工作区有未提交改动（含 untracked）"
    elif ahead:
        recommendation = "default-branch"
        reason = f"当前分支相对 {cmp_ref} 超前 {ahead} 个提交"
    else:
        recommendation = "nothing"
        reason = "工作区干净且相对默认分支没有新提交"
    return {
        **resolved,
        "branch": branch,
        "default_branch": base,
        "comparison_ref": cmp_ref,
        "on_default": on_default,
        "dirty": dirty,
        "dirty_paths": dirty_paths,
        "ahead_of_default": ahead,
        "recommendation": recommendation,
        "reason": reason,
        "needs_confirm": True,
    }


def parse_mr_url(url: str) -> dict[str, Any]:
    text = url.strip()
    m = GITLAB_MR.match(text) or GITLAB_MR_ALT.match(text)
    if m:
        project = m.group("project").strip("/")
        basename = project.rsplit("/", 1)[-1]
        return {
            "kind": "gitlab",
            "host": m.group("host"),
            "project": project,
            "iid": int(m.group("iid")),
            "repo_hint": basename,
            "url": text,
        }
    m = GITHUB_PR.match(text)
    if m:
        return {
            "kind": "github",
            "host": m.group("host"),
            "project": f"{m.group('owner')}/{m.group('repo')}",
            "iid": int(m.group("iid")),
            "repo_hint": m.group("repo"),
            "url": text,
        }
    raise ReviewError(f"unsupported merge request URL: {url}")


def slugify(text: str, max_len: int = 48) -> str:
    out = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (out or "change")[:max_len].rstrip("-")


def change_name(*, repo_basename: str, mode: str, branch: str = "", mr_iid: int | None = None, title: str = "") -> str:
    base = slugify(repo_basename, 32)
    if mode == "mr" and mr_iid is not None:
        extra = slugify(title, 24) if title else ""
        return f"{base}-mr-{mr_iid}" + (f"-{extra}" if extra else "")
    if mode == "uncommitted":
        return f"{base}-{slugify(branch or 'wip', 24)}-uncommitted"
    if mode == "default-branch":
        return f"{base}-{slugify(branch or 'branch', 24)}"
    return f"{base}-{slugify(mode or 'review', 24)}"


def classify_priority(content: str) -> str:
    if P0_RE.search(content or ""):
        return "P0"
    if P1_RE.search(content or ""):
        return "P1"
    if P2_RE.search(content or ""):
        return "P2"
    return "P3"


def _line_ref(comment: dict[str, Any]) -> str:
    start = int(comment.get("start_line") or 0)
    end = int(comment.get("end_line") or 0)
    path = comment.get("path") or "unknown"
    if start <= 0 and end <= 0:
        return path
    if end > start:
        return f"{path}:{start}-{end}"
    return f"{path}:{start or end}"


def _title(comment: dict[str, Any]) -> str:
    content = (comment.get("content") or "").strip().splitlines()
    if not content:
        return "Untitled finding"
    first = content[0].strip()
    return first[:120] + ("…" if len(first) > 120 else "")


def normalize_comments(ocr: dict[str, Any]) -> list[dict[str, Any]]:
    comments = list(ocr.get("comments") or [])
    out = []
    for item in comments:
        comment = dict(item)
        pri = str(comment.get("priority") or "").upper()
        if pri not in PRIORITY_ORDER:
            comment["priority"] = classify_priority(str(comment.get("content") or ""))
        else:
            comment["priority"] = pri
        out.append(comment)
    out.sort(key=lambda c: (PRIORITY_ORDER.index(c["priority"]), c.get("path") or "", int(c.get("start_line") or 0)))
    return out


def counts(comments: list[dict[str, Any]]) -> dict[str, int]:
    data = {k: 0 for k in PRIORITY_ORDER}
    for comment in comments:
        data[comment["priority"]] += 1
    return data


def render_full(meta: dict[str, Any], ocr: dict[str, Any], comments: list[dict[str, Any]]) -> str:
    tally = counts(comments)
    tally_line = " / ".join(f"{k}={tally[k]}" for k in PRIORITY_ORDER if tally[k] or k in ("P0", "P1", "P2", "P3"))
    lines = [
        "---",
        f"repo: {meta.get('repo', '')}",
        f"mode: {meta.get('mode', '')}",
        f"date: {meta.get('date', '')}",
        f"change_name: {meta.get('change_name', '')}",
        f"branch: {meta.get('branch', '')}",
        f"from: {meta.get('from', '')}",
        f"to: {meta.get('to', '')}",
        f"mr: {meta.get('mr_url', '')}",
        f"ocr_session: {ocr.get('session_id', '')}",
        f"ocr_status: {ocr.get('status', '')}",
        "---",
        "",
        f"# Code Review · {meta.get('change_name', '')}",
        "",
        "## Meta",
        "",
        f"- 仓库：`{meta.get('repo', '')}`",
        f"- 范围：`{meta.get('mode', '')}` `{meta.get('from', '')}` → `{meta.get('to', '')}`",
        f"- 分支：`{meta.get('branch', '')}`（默认 `{meta.get('default_branch', '')}`）",
    ]
    if meta.get("mr_url"):
        lines.append(f"- Merge Request：{meta['mr_url']}")
    summary = ocr.get("summary") or {}
    if summary:
        lines.append(
            f"- OCR：files={summary.get('files_reviewed', '?')} comments={summary.get('comments', len(comments))} "
            f"elapsed={summary.get('elapsed', '?')} session=`{ocr.get('session_id', '')}`"
        )
    if ocr.get("message"):
        lines.append(f"- OCR message：{ocr['message']}")
    lines += ["", "## 统计", "", tally_line, "", "## Findings（完整）", ""]
    if not comments:
        lines.append("No findings.")
    else:
        for pri in PRIORITY_ORDER:
            group = [c for c in comments if c["priority"] == pri]
            if not group:
                continue
            lines += [f"### {pri}", ""]
            for i, comment in enumerate(group, 1):
                lines += [
                    f"#### {i}. {_title(comment)}",
                    "",
                    f"- 位置：`{_line_ref(comment)}`",
                    f"- 优先级：{pri}",
                    "",
                    comment.get("content") or "",
                    "",
                ]
                if comment.get("existing_code"):
                    lines += ["**现有代码**", "", "```", str(comment["existing_code"]).rstrip(), "```", ""]
                if comment.get("suggestion_code"):
                    lines += ["**建议改法**", "", "```", str(comment["suggestion_code"]).rstrip(), "```", ""]
                if comment.get("thinking"):
                    lines += ["**推理**", "", str(comment["thinking"]).rstrip(), ""]
    warnings = ocr.get("warnings") or []
    if warnings:
        lines += ["## Warnings", ""]
        for item in warnings:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_summary(meta: dict[str, Any], comments: list[dict[str, Any]], doc_path: str) -> str:
    tally = counts(comments)
    tally_line = " ".join(f"{k}={tally[k]}" for k in PRIORITY_ORDER if tally[k] or k in ("P0", "P1", "P2", "P3"))
    lines = [
        f"## Review 总结 · {meta.get('change_name', '')}",
        "",
        f"范围：`{meta.get('repo', '')}` / `{meta.get('mode', '')}` `{meta.get('from', '')}` → `{meta.get('to', '')}`",
        f"结论：{tally_line}",
        f"完整文档：`{doc_path}`",
        "",
    ]
    if not comments:
        lines.append("No findings.")
        return "\n".join(lines).rstrip() + "\n"
    for pri in PRIORITY_ORDER:
        group = [c for c in comments if c["priority"] == pri]
        if not group:
            continue
        lines.append(f"### {pri}")
        lines.append("")
        for comment in group:
            lines.append(f"- [{pri}] {_title(comment)} — `{_line_ref(comment)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_index(reviews_root: Path, meta: dict[str, Any], tally: dict[str, int], doc_rel: str) -> None:
    index = reviews_root / "INDEX.md"
    header = (
        "# Code reviews\n\n"
        "| 日期 | change | 仓库 | 范围 | P0 | P1 | P2 | P3 | 文档 |\n"
        "|------|--------|------|------|----|----|----|----|------|\n"
    )
    row = (
        f"| {meta.get('date', '')} | {meta.get('change_name', '')} | `{meta.get('repo', '')}` | "
        f"{meta.get('mode', '')} | {tally.get('P0', 0)} | {tally.get('P1', 0)} | {tally.get('P2', 0)} | "
        f"{tally.get('P3', 0)} | [{meta.get('change_name', '')}]({doc_rel}) |"
    )
    if not index.exists():
        index.write_text(header + row + "\n", encoding="utf-8")
        return
    text = index.read_text(encoding="utf-8")
    lines = text.splitlines()
    key = f"| {meta.get('date', '')} | {meta.get('change_name', '')} |"
    kept = [ln for ln in lines if not ln.startswith(key)]
    if len(kept) < 3:
        index.write_text(header + row + "\n", encoding="utf-8")
        return
    kept.append(row)
    index.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


def write_review(work_root: Path, ocr: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    comments = normalize_comments(ocr)
    day = meta.get("date") or date.today().isoformat()
    name = meta.get("change_name") or change_name(
        repo_basename=Path(str(meta.get("repo") or "repo")).name,
        mode=str(meta.get("mode") or "review"),
        branch=str(meta.get("branch") or ""),
        mr_iid=meta.get("mr_iid"),
        title=str(meta.get("title") or ""),
    )
    meta = {**meta, "date": day, "change_name": name}
    out_dir = work_root / "docs" / "reviews" / day / name
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "ocr-raw.json"
    review_path = out_dir / "review.md"
    raw_path.write_text(json.dumps(ocr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review_path.write_text(render_full(meta, ocr, comments), encoding="utf-8")
    doc_rel = f"docs/reviews/{day}/{name}/review.md"
    update_index(work_root / "docs" / "reviews", meta, counts(comments), f"{day}/{name}/review.md")
    summary = render_summary(meta, comments, doc_rel)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    return {
        "out_dir": str(out_dir.relative_to(work_root)),
        "review": doc_rel,
        "raw": f"docs/reviews/{day}/{name}/ocr-raw.json",
        "summary": summary,
        "counts": counts(comments),
        "change_name": name,
        "date": day,
    }


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(payload: dict[str, Any], code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewctl")
    parser.add_argument("--root", default="", help="work workspace root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_resolve = sub.add_parser("resolve-repo")
    p_resolve.add_argument("repo")

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--repo", required=True)

    p_mr = sub.add_parser("parse-mr")
    p_mr.add_argument("--url", required=True)

    p_name = sub.add_parser("change-name")
    p_name.add_argument("--repo-basename", required=True)
    p_name.add_argument("--mode", required=True)
    p_name.add_argument("--branch", default="")
    p_name.add_argument("--mr-iid", type=int, default=None)
    p_name.add_argument("--title", default="")

    p_write = sub.add_parser("write")
    p_write.add_argument("--ocr-json", required=True)
    p_write.add_argument("--meta-json", required=True)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else repo_root_from_script()
    try:
        if args.cmd == "resolve-repo":
            payload = resolve_repo(root, args.repo)
            if payload.get("ambiguous"):
                return emit({"ok": False, **payload}, 1)
            return emit({"ok": True, **payload})
        if args.cmd == "inspect":
            payload = inspect_repo(root, args.repo)
            if payload.get("ambiguous"):
                return emit({"ok": False, **payload}, 1)
            return emit({"ok": True, **payload})
        if args.cmd == "parse-mr":
            return emit({"ok": True, **parse_mr_url(args.url)})
        if args.cmd == "change-name":
            name = change_name(
                repo_basename=args.repo_basename,
                mode=args.mode,
                branch=args.branch,
                mr_iid=args.mr_iid,
                title=args.title,
            )
            return emit({"ok": True, "change_name": name})
        if args.cmd == "write":
            result = write_review(root, _load_json(args.ocr_json), _load_json(args.meta_json))
            return emit({"ok": True, **result})
        raise ReviewError(f"unknown command: {args.cmd}")
    except ReviewError as exc:
        return emit({"ok": False, "error": str(exc)}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
