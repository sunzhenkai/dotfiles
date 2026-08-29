#!/usr/bin/env python3
"""specctl — project-spec-mirror 的机械管理工作。

只做路径探测、目录骨架、git 版本、文件清单、符号提取、文件表覆盖与镜像状态。
给人读的金字塔、恢复投影与切面正文由 Agent 撰写。

stdout 只输出 JSON，stderr 是一行摘要。退出码：0 成功，1 硬失败，2 需要用户确认。
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_FILE_MARKERS = frozenset(
    {
        "go.mod",
        "package.json",
        "pyproject.toml",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "CMakeLists.txt",
        "Makefile",
        "mix.exs",
        "composer.json",
        "Gemfile",
    }
)
DETAIL_LEVELS = ("complete", "important", "lightweight")
IGNORE_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        "target",
        ".tox",
        ".idea",
        ".vscode",
        "coverage",
        ".next",
        "out",
        "bin",
        "obj",
        ".cache",
        ".gradle",
        ".mypy_cache",
        ".pytest_cache",
        ".eggs",
        "eggs",
        "bower_components",
        "jspm_packages",
        "Godeps",
    }
)
LOCK_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "go.sum",
        "poetry.lock",
        "composer.lock",
        "Gemfile.lock",
        "bun.lock",
        "bun.lockb",
    }
)
SECRET_NAME_RE = re.compile(
    r"(^\.env($|\.)|credentials|secrets|\.pem$|\.key$|"
    r"id_rsa|id_ed25519|\.p12$|\.pfx$|\.keystore$)",
    re.I,
)
BINARY_EXTS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".tgz",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".bin",
        ".class",
        ".o",
        ".a",
        ".pyc",
        ".pyo",
        ".wasm",
        ".mp3",
        ".mp4",
        ".jar",
        ".whl",
    }
)
CODE_EXTS = frozenset(
    {
        ".py",
        ".go",
        ".rs",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".kt",
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".hpp",
        ".rb",
        ".php",
        ".cs",
        ".swift",
        ".scala",
    }
)
MIRROR_VERSION = 1
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

GO_FUNC = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.M)
GO_TYPE = re.compile(r"^type\s+(\w+)\s+", re.M)
GO_VAR = re.compile(r"^(?:var|const)\s+(\w+)\b", re.M)
JS_FN = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.M
)
JS_CLASS = re.compile(r"^(?:export\s+)?class\s+(\w+)\b", re.M)
JS_CONST = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=", re.M
)
RUST_FN = re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]", re.M)
RUST_TYPE = re.compile(
    r"^(?:pub(?:\([^)]+\))?\s+)?(?:struct|enum|type|trait)\s+(\w+)\b", re.M
)
JAVA_TYPE = re.compile(
    r"^(?:public|protected|private|static|final|\s)+class\s+(\w+)\b", re.M
)
JAVA_FN = re.compile(
    r"^(?:public|protected|private|static|final|synchronized|\s)+"
    r"[\w.<>,\[\]]+\s+(\w+)\s*\(",
    re.M,
)


class SpecError(Exception):
    def __init__(self, message: str, *, reason: str = "error", **details: Any) -> None:
        super().__init__(message)
        self.reason = reason
        self.details = details


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def emit(payload: dict[str, Any], *, code: int = 0, summary: str = "") -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if summary:
        print(summary, file=sys.stderr)
    return code


def git(args: list[str], cwd: Path, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""},
    )
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise SpecError(f"git {' '.join(args)} failed: {err}", reason="git_failed")
    return (proc.stdout or "").strip()


def is_git_root(path: Path) -> bool:
    return (path / ".git").exists()


def is_project_root(path: Path) -> bool:
    if is_git_root(path):
        return True
    return any((path / name).exists() for name in PROJECT_FILE_MARKERS)


def nearest_project_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if is_project_root(candidate):
            return candidate
    return None


def project_identity(path: Path) -> Path:
    """Canonical root used to decide whether two paths are the same project."""
    path = path.resolve()
    git_root = find_git_root(path)
    if git_root is not None:
        return git_root
    if is_project_root(path):
        return path
    found = nearest_project_root(path)
    return found.resolve() if found is not None else path


def find_git_root(start: Path) -> Path | None:
    cur = start.resolve()
    if not cur.is_dir():
        cur = cur.parent
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cur,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def project_name_of(path: Path) -> str:
    name = path.resolve().name.strip().lower().replace("_", "-")
    name = re.sub(r"[^a-z0-9-]+", "-", name).strip("-")
    return name or "project"


def validate_project_name(name: str) -> str:
    slug = name.strip().lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
    if not SLUG_RE.match(slug):
        raise SpecError(
            f"invalid project name: {name!r}; expected lowercase kebab-case",
            reason="invalid_project",
        )
    return slug


def rel_to(path: Path, start: Path) -> str:
    return os.path.relpath(str(path.resolve()), str(start.resolve())).replace("\\", "/")


def mirror_path(spec_root: Path) -> Path:
    return spec_root / ".mirror.json"


def load_state(spec_root: Path) -> dict[str, Any]:
    path = mirror_path(spec_root)
    if not path.is_file():
        raise SpecError(f"missing .mirror.json under {spec_root}", reason="not_initialized")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"invalid .mirror.json: {exc}", reason="invalid_state") from exc
    if not isinstance(data, dict):
        raise SpecError("invalid .mirror.json: expected object", reason="invalid_state")
    return data


def write_state(spec_root: Path, state: dict[str, Any]) -> None:
    spec_root.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    mirror_path(spec_root).write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_source(spec_root: Path, state: dict[str, Any]) -> Path:
    raw = state.get("source") or ".."
    path = Path(raw)
    if not path.is_absolute():
        path = (spec_root / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise SpecError(f"source does not exist: {path}", reason="source_missing")
    return path


def default_branch(source: Path) -> str | None:
    if find_git_root(source) is None:
        return None
    sym = git(["symbolic-ref", "refs/remotes/origin/HEAD"], source, check=False)
    if sym:
        name = sym.rsplit("/", 1)[-1].strip()
        if name:
            return name
    for candidate in ("main", "master", "trunk"):
        out = git(["rev-parse", "--verify", candidate], source, check=False)
        if out:
            return candidate
    current = git(["rev-parse", "--abbrev-ref", "HEAD"], source, check=False)
    return current or None


def commit_of(source: Path, ref: str) -> str:
    sha = git(["rev-parse", "--verify", ref], source)
    if not sha:
        raise SpecError(f"unknown ref: {ref}", reason="unknown_ref")
    return sha


def git_info(source: Path, branch: str | None) -> dict[str, Any]:
    root = find_git_root(source)
    if root is None:
        return {"is_git": False}
    default = default_branch(source)
    use = branch or default
    head = git(["rev-parse", "--abbrev-ref", "HEAD"], source, check=False) or None
    head_sha = git(["rev-parse", "HEAD"], source, check=False) or None
    dirty = bool(git(["status", "--porcelain"], source, check=False))
    info: dict[str, Any] = {
        "is_git": True,
        "git_root": str(root),
        "default_branch": default,
        "head_branch": head,
        "head_commit": head_sha,
        "dirty": dirty,
    }
    if use:
        sha = git(["rev-parse", "--verify", use], source, check=False)
        info["branch"] = use
        info["commit"] = sha or None
        if not sha:
            info["branch_missing"] = True
    return info


def detect_layout(
    cwd: Path,
    *,
    project: str | None = None,
    source: Path | None = None,
    in_project: bool = False,
) -> dict[str, Any]:
    cwd = cwd.resolve()
    nearest = nearest_project_root(cwd)
    cwd_is_root = is_project_root(cwd)
    source_path = source.resolve() if source is not None else None
    name = validate_project_name(project) if project else None

    if in_project:
        if nearest is None:
            raise SpecError(
                " --in-project requires a project root at or above cwd",
                reason="project_root_not_found",
            )
        host = nearest
    elif cwd_is_root:
        host = cwd
    else:
        host = nearest

    foreign = False
    if source_path is not None and host is not None:
        foreign = project_identity(source_path) != project_identity(host)
    elif name is not None and host is not None:
        foreign = name != project_name_of(host)

    if source_path is None and not foreign:
        if in_project:
            source_path = nearest
        elif cwd_is_root:
            source_path = cwd
        elif nearest is not None and name is None:
            source_path = nearest

    if name is None and source_path is not None:
        name = project_name_of(source_path)

    if in_project and not foreign:
        placement = "in-project"
        placement_root = nearest
        spec_root = placement_root / "spec"
    elif cwd_is_root and not foreign:
        placement = "in-project"
        placement_root = cwd
        spec_root = placement_root / "spec"
    else:
        placement = "external"
        placement_root = cwd
        if not name:
            raise SpecError(
                "non-project directory requires --project (or --source)",
                reason="project_required",
            )
        spec_root = cwd / "spec" / name

    exists = spec_root.is_dir()
    initialized = mirror_path(spec_root).is_file()
    occupied = exists and not initialized and any(spec_root.iterdir())

    result: dict[str, Any] = {
        "cwd": str(cwd),
        "is_project_root": cwd_is_root,
        "nearest_project_root": str(nearest) if nearest else None,
        "placement": placement,
        "placement_root": str(placement_root),
        "project": name,
        "spec_root": str(spec_root),
        "source": str(source_path) if source_path else None,
        "spec_exists": exists,
        "initialized": initialized,
        "occupied": occupied,
    }
    if source_path is not None:
        result["git"] = git_info(source_path, None)
    else:
        result["git"] = {"is_git": False}
    return result


def find_spec_root(cwd: Path, spec: Path | None, project: str | None) -> Path:
    if spec is not None:
        path = spec.resolve()
        if not path.is_dir():
            raise SpecError(f"spec root does not exist: {path}", reason="spec_missing")
        return path
    cwd = cwd.resolve()
    slug = validate_project_name(project) if project else None
    named = cwd / "spec" / slug if slug else None
    if named is not None and mirror_path(named).is_file():
        return named
    in_place = cwd / "spec"
    if mirror_path(in_place).is_file():
        if slug is None:
            return in_place
        state = load_state(in_place)
        if state.get("project") == slug:
            return in_place
        raise SpecError(f"spec not initialized: {named}", reason="not_initialized")
    if named is not None:
        raise SpecError(f"spec not initialized: {named}", reason="not_initialized")
    external_dir = cwd / "spec"
    if external_dir.is_dir():
        found = [
            child
            for child in sorted(external_dir.iterdir())
            if child.is_dir() and mirror_path(child).is_file()
        ]
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise SpecError(
                "multiple spec mirrors under spec/; pass --project",
                reason="ambiguous_spec",
                candidates=[p.name for p in found],
            )
    raise SpecError(
        f"no spec mirror at or under {cwd}/spec",
        reason="not_initialized",
    )


def is_secret_name(name: str) -> bool:
    return bool(SECRET_NAME_RE.search(name))


def should_skip_file(rel: str) -> bool:
    parts = Path(rel).parts
    if any(part in IGNORE_DIR_NAMES or part == "spec" for part in parts):
        return True
    name = Path(rel).name
    if name in LOCK_NAMES or is_secret_name(name):
        return True
    if Path(rel).suffix.lower() in BINARY_EXTS:
        return True
    return False


def is_under_nested_git(source: Path, rel: str) -> bool:
    """True when rel sits inside a nested clone or submodule checkout."""
    current = source.resolve()
    root = current
    for part in Path(rel).parts:
        current = current / part
        if current != root and is_git_root(current):
            return True
    return False


def path_covered_by(rel: str, prefixes: frozenset[str]) -> bool:
    for prefix in prefixes:
        if rel == prefix or rel.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def skip_inventory_path(
    source: Path, rel: str, *, gitlinks: frozenset[str] | None = None
) -> bool:
    """Skip third-party install trees, nested repos, secrets, and build artifacts."""
    if not rel or should_skip_file(rel):
        return True
    if gitlinks and path_covered_by(rel, gitlinks):
        return True
    return is_under_nested_git(source, rel)


def parse_ls_files_stage(raw: str, prefix: str) -> tuple[list[str], frozenset[str]]:
    files: list[str] = []
    gitlinks: list[str] = []
    for entry in raw.split("\0"):
        if not entry:
            continue
        if "\t" not in entry:
            rel_root = entry.replace("\\", "/")
            mode = ""
        else:
            meta, rel_root = entry.split("\t", 1)
            mode = meta.split()[0] if meta.split() else ""
            rel_root = rel_root.replace("\\", "/")
        if prefix:
            if not rel_root.startswith(prefix):
                continue
            rel = rel_root[len(prefix) :]
        else:
            rel = rel_root
        if not rel:
            continue
        if mode == "160000":
            gitlinks.append(rel)
            continue
        files.append(rel)
    return files, frozenset(gitlinks)


def list_gitlinks(source: Path) -> frozenset[str]:
    root = find_git_root(source)
    if root is None:
        return frozenset()
    out = git(["ls-files", "-z", "--stage"], source, check=False)
    prefix = ""
    src = source.resolve()
    if src != root:
        try:
            prefix = src.relative_to(root).as_posix().rstrip("/") + "/"
        except ValueError:
            prefix = ""
    _, gitlinks = parse_ls_files_stage(out, prefix)
    return gitlinks


def looks_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:8192]
    except OSError:
        return True
    return b"\0" in chunk


def list_git_files(source: Path) -> list[str]:
    root = find_git_root(source)
    if root is None:
        return []
    out = git(["ls-files", "-z", "--stage"], source)
    prefix = ""
    src = source.resolve()
    if src != root:
        try:
            prefix = src.relative_to(root).as_posix().rstrip("/") + "/"
        except ValueError:
            prefix = ""
    staged, gitlinks = parse_ls_files_stage(out, prefix)
    return sorted(
        rel
        for rel in staged
        if not skip_inventory_path(source, rel, gitlinks=gitlinks)
    )


def walk_files(source: Path) -> list[str]:
    files: list[str] = []
    source = source.resolve()
    for dirpath, dirnames, filenames in os.walk(source):
        base = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in IGNORE_DIR_NAMES
            and name != "spec"
            and not is_git_root(base / name)
        ]
        for name in filenames:
            path = base / name
            rel = path.relative_to(source).as_posix()
            if skip_inventory_path(source, rel):
                continue
            files.append(rel)
    return sorted(files)


def inventory_files(source: Path, path_prefix: str | None = None) -> list[str]:
    files = list_git_files(source) if find_git_root(source) else walk_files(source)
    if path_prefix:
        prefix = path_prefix.strip().lstrip("./")
        files = [item for item in files if item == prefix or item.startswith(prefix.rstrip("/") + "/")]
    return files


def is_public_name(name: str) -> bool:
    return not name.startswith("_")


def extract_python(source: str, *, include_private: bool) -> list[dict[str, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[dict[str, str]] = []

    def keep(name: str) -> bool:
        return include_private or is_public_name(name)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and keep(node.name):
            found.append(
                {"kind": "function", "name": node.name, "line": str(node.lineno)}
            )
        elif isinstance(node, ast.ClassDef) and keep(node.name):
            found.append({"kind": "class", "name": node.name, "line": str(node.lineno)})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and keep(
                    child.name
                ):
                    found.append(
                        {
                            "kind": "method",
                            "name": f"{node.name}.{child.name}",
                            "line": str(child.lineno),
                        }
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and keep(target.id):
                    found.append(
                        {
                            "kind": "variable",
                            "name": target.id,
                            "line": str(node.lineno),
                        }
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if keep(node.target.id):
                found.append(
                    {
                        "kind": "variable",
                        "name": node.target.id,
                        "line": str(node.lineno),
                    }
                )
    return found


def extract_regex(source: str, ext: str, *, include_private: bool) -> list[dict[str, str]]:
    rules: list[tuple[str, re.Pattern[str]]] = []
    if ext == ".go":
        rules = [("function", GO_FUNC), ("type", GO_TYPE), ("variable", GO_VAR)]
    elif ext in {".js", ".ts", ".tsx", ".jsx"}:
        rules = [("function", JS_FN), ("class", JS_CLASS), ("variable", JS_CONST)]
    elif ext == ".rs":
        rules = [("function", RUST_FN), ("type", RUST_TYPE)]
    elif ext in {".java", ".kt"}:
        rules = [("class", JAVA_TYPE), ("function", JAVA_FN)]
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in rules:
        for match in pattern.finditer(source):
            name = match.group(1)
            if not include_private and not is_public_name(name):
                continue
            if kind == "function" and name in {
                "if",
                "for",
                "while",
                "switch",
                "catch",
                "return",
            }:
                continue
            key = (kind, name)
            if key in seen:
                continue
            seen.add(key)
            line = source.count("\n", 0, match.start()) + 1
            found.append({"kind": kind, "name": name, "line": str(line)})
    return found


def extract_symbols(path: Path, *, include_private: bool) -> list[dict[str, str]]:
    ext = path.suffix.lower()
    if ext not in CODE_EXTS:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    if ext == ".py":
        return extract_python(text, include_private=include_private)
    return extract_regex(text, ext, include_private=include_private)


def skeleton_readme(project: str, mode: str, branch: str | None) -> str:
    branch_text = branch or "（无）"
    return f"""# Spec 镜像 — {project}

给人读的孪生规格，不是源码、不是 OpenSpec。验收：只凭本镜像能重建可运行系统。

| 项 | 值 |
|----|-----|
| 粒度 | {mode} |
| 分支 | {branch_text} |
| 同步 commit | 尚未同步 |
| 源 | （见 `.mirror.json`） |

## 怎么读

1. [overview.md](overview.md)
2. [上下文](context/INDEX.md) · [表面](surface/INDEX.md) · [数据](data/INDEX.md) · [运行时](runtime/INDEX.md) · [构建](build/INDEX.md)
3. [切面](facets/INDEX.md) · [概念](concepts/INDEX.md) · [实体](entities/INDEX.md) · [处理线](flows/INDEX.md)
4. 需要看代码承载时再进 [模块](modules/INDEX.md)；看图进 [diagrams/INDEX.md](diagrams/INDEX.md)

## 地图

| 层 | 路径 | 回答什么 |
|----|------|----------|
| 总览 | overview.md | 这是什么、边界在哪 |
| 上下文 | context/ | 系统在环境里的位置 |
| 表面 | surface/ | 对外接口与配置键 |
| 数据 | data/ | 持久化与一致性 |
| 运行时 | runtime/ | 进程、部署、拓扑 |
| 构建 | build/ | 如何构建、迁移、启动 |
| 切面 | facets/ | 来源、契约、切片、如何验证与放量 |
| 概念 | concepts/ | 领域用语 |
| 实体 | entities/ | 关键对象及其关系 |
| 处理线 | flows/ | 一次业务怎么走完 |
| 模块 | modules/ | 代码如何落地 |
| 图 | diagrams/ | 结构 / 流程 / 时序 / 数据流 / 状态 |
"""


def skeleton_overview(project: str) -> str:
    return f"""# {project}

（待 build：一句话说明这个项目做什么。）

## 背景与目标

- 背景：
- 目标：
- 非目标：

## 恢复入口

- [上下文](context/INDEX.md)
- [表面](surface/INDEX.md) · [配置键](surface/config.md)
- [数据](data/INDEX.md)
- [运行时](runtime/INDEX.md)
- [构建](build/INDEX.md)

## 模块地图

| 模块 | 职责 | 入口 |
|------|------|------|

## 主处理线

（链到 `flows/`。）

## 主切片

（链到 `facets/slices/`。）

## 关键概念与实体

（链到 `concepts/` 与 `entities/`。）
"""


def skeleton_index(title: str) -> str:
    return f"""# {title}

| 名称 | 一句话 | 页 |
|------|--------|-----|
"""


def skeleton_changelog() -> str:
    return """# 镜像同步

尚未同步。
"""


def skeleton_facets_index() -> str:
    return """# 工程切面

| 切面 | 一句话 | 页 |
|------|--------|-----|
| SOURCE | 现状事实从哪来 | [source.md](source.md) |
| CONTRACT | 必须保持为真的约定 | [contracts/INDEX.md](contracts/INDEX.md) |
| SLICE | 可独立交付的垂直切口 | [slices/INDEX.md](slices/INDEX.md) |
| VERIFY | 如何对照验证 | [verify.md](verify.md) |
| TRAFFIC | 影子 / 灰度 / 切换 / 回滚 | [traffic.md](traffic.md) |
"""


def skeleton_facet_stub(title: str, hint: str) -> str:
    return f"""# {title}

（待 build：{hint}）
"""


def create_skeleton(
    spec_root: Path,
    *,
    project: str,
    placement: str,
    source: Path,
    branch: str | None,
    mode: str,
    detail_level: str,
) -> None:
    spec_root.mkdir(parents=True, exist_ok=True)
    source_rel = rel_to(source, spec_root)
    state = {
        "version": MIRROR_VERSION,
        "project": project,
        "placement": placement,
        "source": source_rel,
        "branch": branch,
        "mode": mode,
        "detail_level": detail_level,
        "scope": [],
        "hotspots": [],
        "synced_commit": None,
        "synced_at": None,
        "updated_at": utc_now(),
    }
    write_state(spec_root, state)
    write_text(spec_root / "README.md", skeleton_readme(project, mode, branch))
    write_text(spec_root / "overview.md", skeleton_overview(project))
    write_text(spec_root / "changelog.md", skeleton_changelog())
    write_text(spec_root / "concepts" / "INDEX.md", skeleton_index("概念"))
    write_text(spec_root / "entities" / "INDEX.md", skeleton_index("实体"))
    write_text(spec_root / "flows" / "INDEX.md", skeleton_index("业务处理线"))
    write_text(spec_root / "modules" / "INDEX.md", skeleton_index("模块"))
    write_text(spec_root / "facets" / "INDEX.md", skeleton_facets_index())
    write_text(
        spec_root / "facets" / "source.md",
        skeleton_facet_stub("现状来源", "代码、配置、测试、脱敏样本。"),
    )
    write_text(spec_root / "facets" / "contracts" / "INDEX.md", skeleton_index("契约"))
    write_text(spec_root / "facets" / "slices" / "INDEX.md", skeleton_index("垂直切片"))
    write_text(
        spec_root / "facets" / "verify.md",
        skeleton_facet_stub(
            "对照验证",
            "如何证明行为仍真：测试、性质、对照差分。单实现也须写测试/性质；差分没有则写无。",
        ),
    )
    write_text(
        spec_root / "facets" / "traffic.md",
        skeleton_facet_stub(
            "流量控制",
            "如何发布与回滚。无灰度也须写发布步骤与回滚；完全没有发布机制则写无。",
        ),
    )
    write_text(
        spec_root / "context" / "INDEX.md",
        skeleton_facet_stub("系统上下文", "actor、邻接系统、协议、信任边界、质量属性、安全。"),
    )
    write_text(
        spec_root / "data" / "INDEX.md",
        skeleton_facet_stub("数据面", "存储实例、与实体的差、迁移、一致性与保留。"),
    )
    write_text(
        spec_root / "surface" / "INDEX.md",
        skeleton_facet_stub("对外表面", "接口目录、版本与兼容；配置键见 config.md。"),
    )
    write_text(
        spec_root / "surface" / "config.md",
        skeleton_facet_stub("配置键", "键、语义、默认、环境差；值写 <REDACTED>。"),
    )
    write_text(
        spec_root / "runtime" / "INDEX.md",
        skeleton_facet_stub("运行时", "进程/容器/端口、启动顺序、健康检查、故障弹性。"),
    )
    write_text(
        spec_root / "build" / "INDEX.md",
        skeleton_facet_stub("构建与再生", "工具链、构建/测试/迁移/启动命令与产物。"),
    )
    write_text(spec_root / "diagrams" / "INDEX.md", skeleton_index("图表"))


def parse_name_status(text: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            path = parts[-1]
            files.append({"status": status[0], "path": path, "from": parts[1]})
        else:
            files.append({"status": status[0], "path": parts[-1]})
    return files


ROOT_HEADINGS = frozenset({"根", "roots"})
FILE_HEADINGS = frozenset({"文件", "files"})
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def first_table_cell(row: str) -> str:
    raw = row.strip()
    if not raw.startswith("|"):
        return ""
    parts = [part.strip() for part in raw.strip("|").split("|")]
    return parts[0] if parts else ""


def normalize_path_cell(cell: str) -> str:
    cell = cell.strip()
    link = re.fullmatch(r"\[([^\]]+)\]\([^)]*\)", cell)
    if link:
        cell = link.group(1).strip()
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`"):
        cell = cell[1:-1]
    return cell.strip().lstrip("./")


def parse_pipe_table(lines: list[str], start: int) -> tuple[list[str], int]:
    i = start
    header_skipped = False
    sep_skipped = False
    cells: list[str] = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        row = lines[i]
        if not header_skipped:
            header_skipped = True
            i += 1
            continue
        if not sep_skipped:
            sep_skipped = True
            i += 1
            continue
        value = normalize_path_cell(first_table_cell(row))
        if value:
            cells.append(value)
        i += 1
    return cells, i


def parse_module_readme(text: str) -> tuple[list[str], list[str]]:
    roots: list[str] = []
    files: list[str] = []
    lines = text.splitlines()
    i = 0
    current = ""
    while i < len(lines):
        match = HEADING_RE.match(lines[i])
        if match:
            current = match.group(2).strip().lower()
            i += 1
            continue
        if lines[i].lstrip().startswith("|") and current in ROOT_HEADINGS | FILE_HEADINGS:
            cells, i = parse_pipe_table(lines, i)
            if current in ROOT_HEADINGS:
                roots.extend(cells)
            else:
                files.extend(cells)
            continue
        i += 1
    return roots, files


def load_modules(spec_root: Path) -> list[dict[str, Any]]:
    modules_dir = spec_root / "modules"
    found: list[dict[str, Any]] = []
    if not modules_dir.is_dir():
        return found
    for readme in sorted(modules_dir.glob("*/README.md")):
        name = readme.parent.name
        if name.startswith("."):
            continue
        roots, files = parse_module_readme(readme.read_text(encoding="utf-8"))
        found.append(
            {
                "name": name,
                "readme": f"modules/{name}/README.md",
                "roots": roots,
                "files": files,
            }
        )
    return found


def prefix_matches(path: str, root: str) -> bool:
    root = root.strip().rstrip("/")
    if not root:
        return False
    return path == root or path.startswith(root + "/")


def normalize_scope(raw: object) -> list[str]:
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    seen: list[str] = []
    for item in raw:
        rel = str(item).strip().lstrip("./")
        if rel and rel not in seen:
            seen.append(rel)
    return seen


def in_scope(path: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    return any(prefix_matches(path, prefix) for prefix in prefixes)


def is_code_file(rel: str) -> bool:
    return Path(rel).suffix.lower() in CODE_EXTS


def collect_file_table_entries(modules: list[dict[str, Any]]) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    for module in modules:
        for rel in module.get("files") or []:
            if rel and rel not in seen:
                seen.add(rel)
                entries.append(rel)
    return entries


def collect_coverage(
    spec_root: Path,
    source: Path,
    state: dict[str, Any],
    *,
    path: str | None = None,
) -> dict[str, Any]:
    scope = normalize_scope(state.get("scope"))
    files = inventory_files(source, path)
    code_files = [item for item in files if is_code_file(item)]
    modules = load_modules(spec_root)
    entries = collect_file_table_entries(modules)
    required = [item for item in code_files if in_scope(item, scope)]
    unscoped = [item for item in code_files if item not in required]
    missing = [
        item
        for item in required
        if not any(prefix_matches(item, entry) for entry in entries)
    ]
    extra = [
        entry
        for entry in entries
        if not any(prefix_matches(item, entry) for item in files)
    ]
    mode = state.get("mode") or "concise"
    detail_level = state.get("detail_level", "important")
    if detail_level not in DETAIL_LEVELS:
        detail_level = "important"
    enforce = mode == "detailed" and detail_level in {"important", "complete"}
    ok = not (enforce and missing)
    return {
        "ok": ok,
        "result": "coverage",
        "spec_root": str(spec_root),
        "mode": mode,
        "detail_level": detail_level,
        "enforce": enforce,
        "scope": scope,
        "path": path,
        "inventory_count": len(files),
        "code_file_count": len(code_files),
        "required_count": len(required),
        "covered_count": len(required) - len(missing),
        "missing": missing,
        "extra": extra,
        "unscoped": unscoped,
        "not_built": not bool(modules),
    }


def match_file_table(path: str, modules: list[dict[str, Any]]) -> list[str]:
    return [module["name"] for module in modules if path in module["files"]]


def match_root_prefix(path: str, modules: list[dict[str, Any]]) -> list[str]:
    best_len = -1
    best: list[str] = []
    for module in modules:
        for root in module["roots"]:
            if not prefix_matches(path, root):
                continue
            length = len(root.strip().rstrip("/"))
            if length > best_len:
                best_len = length
                best = [module["name"]]
            elif length == best_len and module["name"] not in best:
                best.append(module["name"])
    return best


def match_change(
    item: dict[str, str], modules: list[dict[str, Any]]
) -> tuple[list[str], str]:
    status = item.get("status", "")
    path = item["path"]
    from_path = item.get("from")
    lookups = [from_path, path] if status == "R" and from_path else [path]
    for lookup in lookups:
        names = match_file_table(lookup, modules)
        if names:
            return names, "file-table"
    for lookup in lookups:
        names = match_root_prefix(lookup, modules)
        if names:
            return names, "root-prefix"
    return [], "unmapped"


def collect_diff_files(
    source: Path,
    state: dict[str, Any],
    *,
    branch: str | None = None,
    from_commit: str | None = None,
    to: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    info = git_info(source, branch or state.get("branch"))
    if not info.get("is_git"):
        files = inventory_files(source, path)
        return {
            "full": True,
            "from": None,
            "to": None,
            "files": [{"status": "A", "path": item} for item in files],
            "note": "non-git source; returning full inventory as added",
        }
    target = to or info.get("commit")
    if not target:
        raise SpecError("cannot resolve target commit", reason="unknown_ref")
    start = from_commit or state.get("synced_commit")
    if not start:
        files = inventory_files(source, path)
        return {
            "full": True,
            "from": None,
            "to": target,
            "files": [{"status": "A", "path": item} for item in files],
        }
    name_status = git(["diff", "--name-status", f"{start}..{target}"], source)
    files = parse_name_status(name_status)
    gitlinks = list_gitlinks(source)
    files = [
        item
        for item in files
        if not skip_inventory_path(source, item["path"], gitlinks=gitlinks)
    ]
    if path:
        prefix = path.strip().lstrip("./")
        files = [
            item
            for item in files
            if item["path"] == prefix
            or item["path"].startswith(prefix.rstrip("/") + "/")
            or item.get("from") == prefix
            or (item.get("from") or "").startswith(prefix.rstrip("/") + "/")
        ]
    return {
        "full": False,
        "from": start,
        "to": target,
        "files": files,
        "file_count": len(files),
    }



# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_detect(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    source = Path(args.source).expanduser().resolve() if args.source else None
    layout = detect_layout(
        cwd,
        project=args.project,
        source=source,
        in_project=args.in_project,
    )
    return emit(
        {"ok": True, "result": "detect", **layout},
        summary=f"detect: {layout['placement']} -> {layout['spec_root']}",
    )


def cmd_init(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    source_arg = Path(args.source).expanduser().resolve() if args.source else None
    layout = detect_layout(
        cwd,
        project=args.project,
        source=source_arg,
        in_project=args.in_project,
    )
    spec_root = Path(layout["spec_root"])
    source = Path(layout["source"]) if layout["source"] else None
    project = layout["project"]
    if source is None or not project:
        raise SpecError(
            "init needs --source and --project (or a detectable project root)",
            reason="project_required",
        )
    if layout["initialized"]:
        return emit(
            {
                "ok": True,
                "result": "init",
                "already": True,
                **layout,
            },
            summary=f"init: already initialized at {spec_root}",
        )
    if layout["occupied"]:
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "spec_dir_occupied",
                "spec_root": str(spec_root),
                "prompt": (
                    f"{spec_root} 已存在且没有 .mirror.json，可能不是本镜像目录。"
                    "确认前不会覆盖。"
                ),
                "confirm_args": None,
            },
            code=2,
            summary=f"init: occupied {spec_root}",
        )
    mode = args.mode
    detail_level = args.detail_level
    info = git_info(source, args.branch)
    branch = args.branch or (info.get("default_branch") if info.get("is_git") else None)
    if not args.confirm:
        confirm_args = ["init", "--confirm", "--cwd", str(cwd), "--mode", mode, "--detail-level", detail_level]
        if args.project:
            confirm_args.extend(["--project", args.project])
        if args.source:
            confirm_args.extend(["--source", str(source_arg)])
        if args.in_project:
            confirm_args.append("--in-project")
        if args.branch:
            confirm_args.extend(["--branch", args.branch])
        return emit(
            {
                "ok": False,
                "result": "needs_confirm",
                "reason": "create_spec_dir",
                "placement": layout["placement"],
                "spec_root": str(spec_root),
                "source": str(source),
                "project": project,
                "branch": branch,
                "mode": mode,
                "detail_level": detail_level,
                "prompt": (
                    f"将创建 spec 镜像目录 {spec_root} "
                    f"（placement={layout['placement']}，source={source}）。"
                    "确认后才会写入骨架。"
                ),
                "confirm_args": confirm_args,
            },
            code=2,
            summary=f"init: confirm create {spec_root}",
        )
    create_skeleton(
        spec_root,
        project=project,
        placement=layout["placement"],
        source=source,
        branch=branch,
        mode=mode,
        detail_level=detail_level,
    )
    return emit(
        {
            "ok": True,
            "result": "init",
            "already": False,
            "spec_root": str(spec_root),
            "source": str(source),
            "project": project,
            "placement": layout["placement"],
            "branch": branch,
            "mode": mode,
            "detail_level": detail_level,
        },
        summary=f"init: created {spec_root}",
    )


def cmd_status(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    branch = args.branch or state.get("branch")
    info = git_info(source, branch)
    synced = state.get("synced_commit")
    freshness: dict[str, Any] = {"kind": "none"}
    if info.get("is_git") and info.get("commit"):
        freshness = {
            "kind": "git",
            "synced_commit": synced,
            "target_commit": info["commit"],
            "in_sync": bool(synced) and synced == info["commit"],
        }
        if synced:
            proc = subprocess.run(
                ["git", "merge-base", "--is-ancestor", synced, info["commit"]],
                cwd=source,
                capture_output=True,
                check=False,
            )
            freshness["is_ancestor"] = proc.returncode == 0
    elif not info.get("is_git"):
        freshness = {"kind": "non-git", "note": "no commit diff; compare inventory"}
    payload = {
        "ok": True,
        "result": "status",
        "spec_root": str(spec_root),
        "state": state,
        "source": str(source),
        "git": info,
        "freshness": freshness,
    }
    return emit(
        payload,
        summary=f"status: {state.get('project')} {freshness.get('kind')}",
    )


def cmd_git_info(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    if args.source:
        source = Path(args.source).expanduser().resolve()
    else:
        spec_root = find_spec_root(
            cwd, Path(args.spec).expanduser() if args.spec else None, args.project
        )
        source = resolve_source(spec_root, load_state(spec_root))
    info = git_info(source, args.branch)
    return emit(
        {"ok": True, "result": "git-info", "source": str(source), **info},
        summary=f"git-info: git={info.get('is_git')}",
    )


def cmd_inventory(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    prefix = args.path
    files = inventory_files(source, prefix)
    code_files = [item for item in files if Path(item).suffix.lower() in CODE_EXTS]
    return emit(
        {
            "ok": True,
            "result": "inventory",
            "spec_root": str(spec_root),
            "source": str(source),
            "path": prefix,
            "file_count": len(files),
            "code_file_count": len(code_files),
            "files": files,
        },
        summary=f"inventory: {len(files)} files",
    )


def cmd_symbols(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    targets = list(args.file)
    if not targets:
        raise SpecError("symbols requires one or more --file", reason="usage")
    gitlinks = list_gitlinks(source)
    files_out: list[dict[str, Any]] = []
    for rel in targets:
        path = (source / rel).resolve()
        try:
            path.relative_to(source.resolve())
        except ValueError as exc:
            raise SpecError(f"file outside source: {rel}", reason="path_escape") from exc
        if skip_inventory_path(source, rel, gitlinks=gitlinks):
            files_out.append(
                {"path": rel, "skipped": True, "reason": "third_party", "symbols": []}
            )
            continue
        if not path.is_file():
            files_out.append({"path": rel, "missing": True, "symbols": []})
            continue
        files_out.append(
            {
                "path": rel,
                "symbols": extract_symbols(
                    path, include_private=args.private
                ),
            }
        )
    return emit(
        {
            "ok": True,
            "result": "symbols",
            "source": str(source),
            "files": files_out,
        },
        summary=f"symbols: {len(files_out)} files",
    )


def cmd_diff(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    payload = collect_diff_files(
        source,
        state,
        branch=args.branch,
        from_commit=args.from_commit,
        to=args.to,
        path=args.path,
    )
    summary = "diff: non-git full inventory" if payload.get("note") else (
        f"diff: full to {str(payload.get('to') or '')[:12]}"
        if payload.get("full")
        else f"diff: {len(payload['files'])} files {str(payload.get('from') or '')[:12]}..{str(payload.get('to') or '')[:12]}"
    )
    return emit({"ok": True, "result": "diff", **payload}, summary=summary)


def cmd_coverage(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    payload = collect_coverage(spec_root, source, state, path=args.path)
    missing_n = len(payload["missing"])
    extra_n = len(payload["extra"])
    summary = (
        f"coverage: {payload['covered_count']}/{payload['required_count']} "
        f"missing={missing_n} extra={extra_n}"
    )
    return emit(payload, code=0 if payload["ok"] else 1, summary=summary)


def cmd_route(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    diff_payload = collect_diff_files(
        source,
        state,
        branch=args.branch,
        from_commit=args.from_commit,
        to=args.to,
        path=args.path,
    )
    modules = load_modules(spec_root)
    not_built = not modules
    changes: list[dict[str, Any]] = []
    unmapped: list[str] = []
    renames: list[dict[str, Any]] = []
    hit_modules: list[str] = []
    for item in diff_payload["files"]:
        names, via = ([], "unmapped") if not_built else match_change(item, modules)
        rec: dict[str, Any] = {
            "status": item.get("status", ""),
            "path": item["path"],
            "modules": names,
            "via": via,
        }
        if item.get("from"):
            rec["from"] = item["from"]
        changes.append(rec)
        if not names:
            unmapped.append(item["path"])
        else:
            for name in names:
                if name not in hit_modules:
                    hit_modules.append(name)
        if item.get("status") == "R" and item.get("from"):
            rename_rec: dict[str, Any] = {"from": item["from"], "to": item["path"]}
            if names:
                rename_rec["module"] = names[0]
                if len(names) > 1:
                    rename_rec["modules"] = names
            renames.append(rename_rec)
    pages = [f"modules/{name}/README.md" for name in hit_modules]
    payload: dict[str, Any] = {
        "ok": True,
        "result": "route",
        "spec_root": str(spec_root),
        "from": diff_payload.get("from"),
        "to": diff_payload.get("to"),
        "full": diff_payload.get("full", False),
        "not_built": not_built,
        "modules": hit_modules,
        "pages": pages,
        "renames": renames,
        "unmapped": unmapped,
        "changes": changes,
    }
    if not_built:
        payload["note"] = "not_built"
    summary = (
        f"route: not_built {len(unmapped)} unmapped"
        if not_built
        else f"route: {len(hit_modules)} modules {len(unmapped)} unmapped"
    )
    return emit(payload, summary=summary)


def cmd_set_sync(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    if args.mode:
        if args.mode not in {"concise", "detailed"}:
            raise SpecError("mode must be concise or detailed", reason="usage")
        state["mode"] = args.mode
    if args.detail_level:
        state["detail_level"] = args.detail_level
    if args.branch:
        state["branch"] = args.branch
    if args.scope is not None:
        state["scope"] = list(args.scope)
    if args.hotspot is not None:
        seen: list[str] = []
        for item in args.hotspot:
            rel = str(item).strip().lstrip("./")
            if rel and rel not in seen:
                seen.append(rel)
        state["hotspots"] = seen
    commit = args.commit
    if commit:
        info = git_info(source, state.get("branch"))
        if info.get("is_git"):
            commit = commit_of(source, commit)
        state["synced_commit"] = commit
        state["synced_at"] = utc_now()
    elif args.commit == "":
        state["synced_commit"] = None
        state["synced_at"] = None
    state["updated_at"] = utc_now()
    write_state(spec_root, state)
    return emit(
        {"ok": True, "result": "set-sync", "spec_root": str(spec_root), "state": state},
        summary=f"set-sync: {state.get('synced_commit') or 'none'}",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    required_files = [
        "README.md",
        "overview.md",
        "changelog.md",
        "concepts/INDEX.md",
        "entities/INDEX.md",
        "flows/INDEX.md",
        "modules/INDEX.md",
        "facets/INDEX.md",
        "facets/source.md",
        "facets/contracts/INDEX.md",
        "facets/slices/INDEX.md",
        "facets/verify.md",
        "facets/traffic.md",
        "context/INDEX.md",
        "data/INDEX.md",
        "surface/INDEX.md",
        "surface/config.md",
        "runtime/INDEX.md",
        "build/INDEX.md",
        "diagrams/INDEX.md",
    ]
    missing = [rel for rel in required_files if not (spec_root / rel).is_file()]
    issues: list[str] = []
    if missing:
        issues.append("missing: " + ", ".join(missing))
    for key in ("version", "project", "placement", "source", "mode"):
        if key not in state:
            issues.append(f"state missing {key}")
    if state.get("mode") not in {None, "concise", "detailed"}:
        issues.append(f"invalid mode {state.get('mode')!r}")
    detail_level = state.get("detail_level", "important")
    if detail_level not in DETAIL_LEVELS:
        issues.append(f"invalid detail_level {detail_level!r}")
    hotspots = state.get("hotspots", [])
    if hotspots is None:
        hotspots = []
    if not isinstance(hotspots, list) or any(not isinstance(item, str) for item in hotspots):
        issues.append("hotspots must be a list of strings")
    source_ok = True
    try:
        source = resolve_source(spec_root, state)
    except SpecError as exc:
        source_ok = False
        source = None
        issues.append(str(exc))
    ok = not issues
    payload = {
        "ok": ok,
        "result": "validate",
        "spec_root": str(spec_root),
        "issues": issues,
        "source_ok": source_ok,
        "source": str(source) if source else None,
        "mode": state.get("mode"),
        "detail_level": detail_level,
    }
    return emit(
        payload,
        code=0 if ok else 1,
        summary="validate: ok" if ok else "validate: issues",
    )


COMMANDS = {
    "detect": cmd_detect,
    "init": cmd_init,
    "status": cmd_status,
    "git-info": cmd_git_info,
    "inventory": cmd_inventory,
    "symbols": cmd_symbols,
    "diff": cmd_diff,
    "coverage": cmd_coverage,
    "route": cmd_route,
    "set-sync": cmd_set_sync,
    "validate": cmd_validate,
}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # noqa: ANN401
        emit({"ok": False, "result": "error", "reason": "usage", "error": message}, code=1)
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cwd", default=None, help="working directory; default process cwd")
    common.add_argument("--spec", default=None, help="explicit spec root")
    common.add_argument("--project", default=None, help="project slug")
    common.add_argument("--source", default=None, help="path to the target project")
    common.add_argument("--branch", default=None, help="git branch to track")

    parser = Parser(prog="specctl", description=__doc__)
    parser.add_argument("--cwd", dest="global_cwd", default=None)
    parser.add_argument("--spec", dest="global_spec", default=None)
    parser.add_argument("--project", dest="global_project", default=None)
    parser.add_argument("--source", dest="global_source", default=None)
    parser.add_argument("--branch", dest="global_branch", default=None)
    subs = parser.add_subparsers(dest="command", required=True)

    def add(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        return subs.add_parser(name, parents=[common], **kwargs)

    detect = add("detect", help="判定 project 根与镜像落点")
    detect.add_argument("--in-project", action="store_true")

    init = add("init", help="创建镜像骨架；无 --confirm 时退出 2")
    init.add_argument("--in-project", action="store_true")
    init.add_argument("--confirm", action="store_true")
    init.add_argument(
        "--mode",
        choices=("concise", "detailed"),
        default="concise",
    )
    init.add_argument("--detail-level", choices=DETAIL_LEVELS, default="important")

    add("status", help="镜像状态与 git 新鲜度")
    add("git-info", help="源仓库分支与 commit")

    inventory = add("inventory", help="源文件清单")
    inventory.add_argument("--path", default=None, help="仅列出此前缀下的文件")

    symbols = add("symbols", help="提取代码符号")
    symbols.add_argument("--file", action="append", default=[], help="相对 source 的路径，可重复")
    symbols.add_argument("--private", action="store_true", help="包含 _ 前缀符号")

    diff = add("diff", help="相对已同步 commit 的文件变更")
    diff.add_argument("--from", dest="from_commit", default=None)
    diff.add_argument("--to", dest="to", default=None)
    diff.add_argument("--path", default=None)

    coverage = add("coverage", help="对照 inventory 与模块文件表")
    coverage.add_argument("--path", default=None, help="仅核对此前缀下的文件")

    route = add("route", help="把 diff 文件映射到模块 README")
    route.add_argument("--from", dest="from_commit", default=None)
    route.add_argument("--to", dest="to", default=None)
    route.add_argument("--path", default=None)

    set_sync = add("set-sync", help="回写 .mirror.json 同步指针")
    set_sync.add_argument("--commit", default=None)
    set_sync.add_argument("--mode", choices=("concise", "detailed"), default=None)
    set_sync.add_argument("--detail-level", choices=DETAIL_LEVELS, default=None)
    set_sync.add_argument("--scope", action="append", default=None)
    set_sync.add_argument(
        "--hotspot",
        action="append",
        default=None,
        help="热点源路径，可重复；本轮给出的列表整表写回",
    )

    add("validate", help="检查金字塔、恢复投影、切面骨架与状态文件")
    return parser


def merge_globals(args: argparse.Namespace) -> None:
    pairs = (
        ("cwd", "global_cwd"),
        ("spec", "global_spec"),
        ("project", "global_project"),
        ("source", "global_source"),
        ("branch", "global_branch"),
    )
    for local, gname in pairs:
        local_val = getattr(args, local, None)
        global_val = getattr(args, gname, None)
        if local_val and global_val and local_val != global_val:
            raise SpecError(
                f"conflicting --{local} values: {global_val!r} vs {local_val!r}",
                reason="usage",
            )
        if local_val is None:
            setattr(args, local, global_val)
    if not getattr(args, "cwd", None):
        args.cwd = str(Path.cwd())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        merge_globals(args)
        return COMMANDS[args.command](args)
    except SpecError as exc:
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
    except Exception as exc:  # noqa: BLE001
        return emit(
            {
                "ok": False,
                "result": "error",
                "reason": "internal",
                "error": f"{type(exc).__name__}: {exc}",
            },
            code=1,
            summary=f"{args.command}: {type(exc).__name__}: {exc}",
        )


if __name__ == "__main__":
    raise SystemExit(main())
