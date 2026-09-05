#!/usr/bin/env python3
"""specctl — project-spec-mirror 的机械管理工作。

只做路径探测、目录骨架、git 新鲜度、diff 路由与 finalize 门禁。
briefing 与 agent spec 正文由 Agent 撰写。

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
import tempfile
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
MODES = ("briefing", "reconstructable")
REQUIREMENT_RE = re.compile(r"^#{2,4}\s+Requirement\b", re.I | re.M)
SCENARIO_RE = re.compile(r"^#{2,4}\s+Scenario\b", re.I | re.M)
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
        ".ex",
        ".exs",
        ".erl",
        ".lua",
        ".zig",
        ".m",
        ".mm",
        ".vue",
        ".svelte",
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


CURRENT_LAYOUT_FILES = (
    "briefing/overview.md",
    "agent/INDEX.md",
    "evidence/source-map.md",
)


def mirror_layout(spec_root: Path) -> str:
    if not mirror_path(spec_root).is_file():
        return "none"
    if all((spec_root / rel).is_file() for rel in CURRENT_LAYOUT_FILES):
        return "current"
    return "legacy"


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
    layout = mirror_layout(spec_root) if initialized else "none"

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
        "layout": layout,
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
    if b"\0" in chunk:
        return True
    if not chunk:
        return False
    allowed_controls = {8, 9, 10, 12, 13, 27}
    controls = sum(
        1 for byte in chunk if byte < 32 and byte not in allowed_controls
    )
    return controls / len(chunk) > 0.05


def ignored_paths(source: Path, paths: list[str]) -> frozenset[str]:
    if not paths:
        return frozenset()
    payload = "\0".join(paths) + "\0"
    root = find_git_root(source)
    temp: tempfile.TemporaryDirectory[str] | None = None
    if root is not None:
        command = ["git", "check-ignore", "--no-index", "-z", "--stdin"]
        cwd = source
    else:
        temp = tempfile.TemporaryDirectory(prefix="specctl-ignore-")
        git_dir = Path(temp.name) / "repo.git"
        init = subprocess.run(
            ["git", "init", "--bare", "-q", str(git_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if init.returncode != 0:
            temp.cleanup()
            raise SpecError(
                f"cannot initialize temporary ignore matcher: {init.stderr.strip()}",
                reason="gitignore_failed",
            )
        command = [
            "git",
            f"--git-dir={git_dir}",
            f"--work-tree={source.resolve()}",
            "check-ignore",
            "--no-index",
            "-z",
            "--stdin",
        ]
        cwd = source
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if proc.returncode not in {0, 1}:
            raise SpecError(
                f"git check-ignore failed: {proc.stderr.strip()}",
                reason="gitignore_failed",
            )
        return frozenset(
            item.replace("\\", "/").lstrip("./")
            for item in proc.stdout.split("\0")
            if item
        )
    finally:
        if temp is not None:
            temp.cleanup()


def text_path(source: Path, rel: str, *, allow_missing: bool = False) -> bool:
    path = source / rel
    if not path.exists():
        return allow_missing and Path(rel).suffix.lower() not in BINARY_EXTS
    return path.is_file() and not looks_binary(path)


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
    candidates = [
        rel for rel in staged if not skip_inventory_path(source, rel, gitlinks=gitlinks)
    ]
    ignored = ignored_paths(source, candidates)
    return sorted(
        rel
        for rel in candidates
        if rel not in ignored and text_path(source, rel)
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
    ignored = ignored_paths(source, files)
    return sorted(
        rel
        for rel in files
        if rel not in ignored and text_path(source, rel)
    )


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
    return f"""# {project}

从这里读这个项目：人走 briefing，Agent 走能力 spec。

| 项 | 值 |
|----|-----|
| 粒度 | {mode} |
| 分支 | {branch_text} |
| 同步 commit | 尚未同步 |
| 源 | （见 `.mirror.json`） |

## 怎么读

1. 人：[总览](briefing/overview.md) · [架构](briefing/architecture.md) · [处理线](briefing/flows/INDEX.md) · [图](briefing/diagrams/INDEX.md)
2. Agent：[能力](agent/INDEX.md) · [模型](agent/model/INDEX.md) · [表面](agent/surface/INDEX.md) · [数据](agent/data/INDEX.md)

## 地图

| 层 | 路径 | 给谁 | 回答什么 |
|----|------|------|----------|
| 总览 | briefing/overview.md | 人 | 这是什么、边界在哪 |
| 架构 | briefing/architecture.md | 人 | 邻接、信任、能力如何拼在一起 |
| 处理线 | briefing/flows/ | 人 | 一次业务怎么走完 |
| 概念 | briefing/concepts/ | 人 | 领域用语 |
| 图 | briefing/diagrams/ | 人 | 结构 / 流程 / 状态 |
| 能力 | agent/specs/ | Agent | 可验证、可复现的功能契约 |
| 模型 | agent/model/ | Agent | 实体、不变式、状态机 |
| 表面 | agent/surface/ | Agent | 对外行为必须对上什么 |
| 数据 | agent/data/ | Agent | 逻辑持久化与一致性 |
"""


def skeleton_overview(project: str) -> str:
    return f"""# {project}

（待 build：一句话说明这个项目做什么。）

## 背景与目标

- 背景：
- 目标：
- 非目标：

## 能力地图

| 能力 | 一句话 | 页 |
|------|--------|-----|

## 主处理线

（链到 `briefing/flows/`。）
"""


def skeleton_architecture() -> str:
    return """# 架构

（待 build：系统对谁负责、邻接与信任边界。）

## 使用者

## 邻接系统

| 邻接 | 方向 | 协议 | 责任切在哪 |
|------|------|------|------------|

## 信任边界
"""


def skeleton_index(title: str) -> str:
    return f"""# {title}

| 名称 | 一句话 | 页 |
|------|--------|-----|
"""


def skeleton_capability_index() -> str:
    return """# 能力

| 能力 | 一句话 | 状态 | 页 |
|------|--------|------|-----|

## 未指定

| 路径 | 原因 |
|------|------|
"""


def skeleton_source_map() -> str:
    return """# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
"""


def skeleton_changelog() -> str:
    return """# 镜像同步

尚未同步。
"""


def skeleton_stub(title: str, hint: str) -> str:
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
        "build_status": "skeleton",
        "built_at": None,
        "synced_commit": None,
        "synced_at": None,
        "updated_at": utc_now(),
    }
    write_state(spec_root, state)
    write_text(spec_root / "README.md", skeleton_readme(project, mode, branch))
    write_text(spec_root / "changelog.md", skeleton_changelog())
    write_text(spec_root / "briefing" / "overview.md", skeleton_overview(project))
    write_text(spec_root / "briefing" / "architecture.md", skeleton_architecture())
    write_text(spec_root / "briefing" / "concepts" / "INDEX.md", skeleton_index("概念"))
    write_text(spec_root / "briefing" / "flows" / "INDEX.md", skeleton_index("业务处理线"))
    write_text(spec_root / "briefing" / "diagrams" / "INDEX.md", skeleton_index("图表"))
    write_text(spec_root / "agent" / "INDEX.md", skeleton_capability_index())
    write_text(
        spec_root / "agent" / "model" / "INDEX.md",
        skeleton_stub("模型", "实体、不变式、状态机。"),
    )
    write_text(
        spec_root / "agent" / "surface" / "INDEX.md",
        skeleton_stub("对外表面", "接口目录、版本与错误分类。"),
    )
    write_text(
        spec_root / "agent" / "data" / "INDEX.md",
        skeleton_stub("数据", "逻辑存储、一致性与保留。"),
    )
    write_text(spec_root / "evidence" / "source-map.md", skeleton_source_map())


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


CAPABILITY_HEADERS = frozenset({"能力", "capability"})
UNSPECIFIED_HEADERS = frozenset({"未指定", "路径", "path", "unspecified"})
CAPABILITY_STATUSES = frozenset({"draft", "ready"})
LEAK_COMPLETE_LOGIC = re.compile(r"完整逻辑|full logic|complete logic", re.I)
LEAK_FILE_HEADING = re.compile(r"^#{1,3}\s+(文件|files)\s*$", re.I | re.M)
LEAK_TOOLCHAIN = re.compile(
    r"(go\.mod|package\.json|Cargo\.toml|pyproject\.toml|"
    r"composer\.json|Gemfile|pom\.xml|mix\.exs).{0,80}\d+\.\d+",
    re.I,
)
STUB_RE = re.compile(r"待 build|to be built|\(TODO:\s*describe", re.I)


def table_cells(row: str) -> list[str]:
    raw = row.strip()
    if not raw.startswith("|"):
        return []
    return [part.strip() for part in raw.strip("|").split("|")]


def normalize_path_cell(cell: str) -> str:
    cell = cell.strip()
    link = re.fullmatch(r"\[([^\]]+)\]\([^)]*\)", cell)
    if link:
        cell = link.group(1).strip()
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`"):
        cell = cell[1:-1]
    return cell.strip().lstrip("./")


def header_name(cell: str) -> str:
    return normalize_path_cell(cell).lower()


def parse_markdown_table(
    lines: list[str], start: int
) -> tuple[list[str], list[list[str]], int]:
    i = start
    headers: list[str] = []
    rows: list[list[str]] = []
    if i < len(lines) and lines[i].lstrip().startswith("|"):
        headers = table_cells(lines[i])
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("|"):
        i += 1
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = table_cells(lines[i])
        if any(cell.strip() for cell in cells):
            rows.append(cells)
        i += 1
    return headers, rows, i


def iter_markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    tables: list[tuple[list[str], list[list[str]]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            headers, rows, i = parse_markdown_table(lines, i)
            if headers:
                tables.append((headers, rows))
            continue
        i += 1
    return tables


def load_capabilities(spec_root: Path) -> list[dict[str, Any]]:
    index = spec_root / "agent" / "INDEX.md"
    if not index.is_file():
        return []
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for headers, rows in iter_markdown_tables(index.read_text(encoding="utf-8")):
        if not headers or header_name(headers[0]) not in CAPABILITY_HEADERS:
            continue
        for row in rows:
            name = normalize_path_cell(row[0]) if row else ""
            if not name or name in seen:
                continue
            seen.add(name)
            status = row[2].strip() if len(row) > 2 else ""
            found.append({"name": name, "status": status})
    return found


def load_unspecified(spec_root: Path) -> list[str]:
    index = spec_root / "agent" / "INDEX.md"
    if not index.is_file():
        return []
    found: list[str] = []
    seen: set[str] = set()
    for headers, rows in iter_markdown_tables(index.read_text(encoding="utf-8")):
        if not headers or header_name(headers[0]) not in UNSPECIFIED_HEADERS:
            continue
        for row in rows:
            path = normalize_path_cell(row[0]) if row else ""
            if not path or path in seen:
                continue
            seen.add(path)
            found.append(path)
    return found


def load_source_map(spec_root: Path) -> list[dict[str, Any]]:
    path = spec_root / "evidence" / "source-map.md"
    if not path.is_file():
        return []
    found: list[dict[str, Any]] = []
    for headers, rows in iter_markdown_tables(path.read_text(encoding="utf-8")):
        del headers
        for row in rows:
            if len(row) < 2:
                continue
            name = normalize_path_cell(row[0])
            source_path = normalize_path_cell(row[1])
            if not name or not source_path:
                continue
            spec = ""
            if len(row) > 2:
                spec = row[2].strip()
            found.append({"name": name, "path": source_path, "spec": spec})
    return found


def prefix_matches(path: str, root: str) -> bool:
    root = root.strip().rstrip("/")
    if not root:
        return False
    return path == root or path.startswith(root + "/")


def path_accounted(path: str, prefixes: list[str]) -> bool:
    return any(prefix_matches(path, prefix) for prefix in prefixes if prefix)


def is_code_file(rel: str) -> bool:
    return Path(rel).suffix.lower() in CODE_EXTS


def capability_spec_rel(name: str) -> str:
    return f"agent/specs/{name}/spec.md"


def count_flows(spec_root: Path) -> int:
    flows = spec_root / "briefing" / "flows"
    if not flows.is_dir():
        return 0
    extra = [p for p in flows.glob("*.md") if p.name != "INDEX.md"]
    rows = 0
    index = flows / "INDEX.md"
    if index.is_file():
        for _headers, data in iter_markdown_tables(index.read_text(encoding="utf-8")):
            rows += len(data)
    return max(rows, len(extra))


def overview_is_stub(spec_root: Path) -> bool:
    path = spec_root / "briefing" / "overview.md"
    if not path.is_file():
        return True
    return bool(STUB_RE.search(path.read_text(encoding="utf-8")))


def source_map_empty(mapping: list[dict[str, Any]]) -> bool:
    return not mapping


def unmapped_code_files(spec_root: Path, source: Path) -> list[str]:
    mapping = load_source_map(spec_root)
    prefixes = [item["path"] for item in mapping] + load_unspecified(spec_root)
    found: list[str] = []
    for rel in inventory_files(source):
        if not is_code_file(rel):
            continue
        if path_accounted(rel, prefixes):
            continue
        found.append(rel)
    return found


def gone_map_paths(spec_root: Path, source: Path) -> list[str]:
    files = inventory_files(source)
    gone: list[str] = []
    seen: set[str] = set()
    for item in load_source_map(spec_root):
        prefix = item["path"]
        if prefix in seen:
            continue
        seen.add(prefix)
        if any(prefix_matches(rel, prefix) for rel in files):
            continue
        gone.append(prefix)
    return gone


def briefing_leaks(spec_root: Path) -> list[str]:
    briefing = spec_root / "briefing"
    if not briefing.is_dir():
        return []
    leaks: list[str] = []
    for path in sorted(briefing.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        rel = rel_to(path, spec_root)
        if LEAK_COMPLETE_LOGIC.search(text):
            leaks.append(f"{rel}:完整逻辑")
        if LEAK_FILE_HEADING.search(text):
            leaks.append(f"{rel}:文件表")
        if LEAK_TOOLCHAIN.search(text):
            leaks.append(f"{rel}:工具链版本")
    return leaks


def apply_source_map_renames(spec_root: Path, renames: list[dict[str, Any]]) -> int:
    path = spec_root / "evidence" / "source-map.md"
    if not path.is_file() or not renames:
        return 0
    text = path.read_text(encoding="utf-8")
    changed = 0
    for rec in renames:
        old = rec.get("from") or ""
        new = rec.get("to") or ""
        if not old or not new:
            continue
        needle = f"`{old}`"
        if needle in text:
            text = text.replace(needle, f"`{new}`")
            changed += 1
    if changed:
        write_text(path, text)
    return changed


def collect_coverage(
    spec_root: Path,
    source: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    capabilities = load_capabilities(spec_root)
    mapping = load_source_map(spec_root)
    mapped = {item["name"] for item in mapping}
    missing: list[str] = []
    if overview_is_stub(spec_root):
        missing.append("overview:stub")
    if count_flows(spec_root) < 1:
        missing.append("flows:none")
    if not capabilities:
        missing.append("<no capabilities identified>")
    if source_map_empty(mapping):
        missing.append("source-map:empty")
    for item in capabilities:
        name = item["name"]
        status = item.get("status") or ""
        if status not in CAPABILITY_STATUSES:
            missing.append(f"{name}:status")
        spec_file = spec_root / "agent" / "specs" / name / "spec.md"
        if not spec_file.is_file():
            missing.append(f"{name}:spec")
        if name not in mapped:
            missing.append(f"{name}:source-map")
    extra = sorted(
        name for name in mapped if name not in {item["name"] for item in capabilities}
    )
    unmapped = unmapped_code_files(spec_root, source)
    mode = state.get("mode") or "briefing"
    enforce = mode == "reconstructable"
    if enforce:
        for item in capabilities:
            spec_file = spec_root / "agent" / "specs" / item["name"] / "spec.md"
            if not spec_file.is_file():
                continue
            text = spec_file.read_text(encoding="utf-8")
            if not REQUIREMENT_RE.search(text):
                missing.append(f"{item['name']}:Requirement")
            if not SCENARIO_RE.search(text):
                missing.append(f"{item['name']}:Scenario")
        for rel in unmapped:
            missing.append(f"unmapped:{rel}")
        for name in extra:
            missing.append(f"ghost:{name}")
    named_missing = {
        item.split(":", 1)[0]
        for item in missing
        if item not in {"overview:stub", "flows:none", "source-map:empty", "<no capabilities identified>"}
        and not item.startswith("unmapped:")
        and not item.startswith("ghost:")
    }
    covered = max(0, len(capabilities) - len(named_missing & {item["name"] for item in capabilities}))
    ok = not missing
    return {
        "ok": ok,
        "result": "coverage",
        "spec_root": str(spec_root),
        "mode": mode,
        "enforce": enforce,
        "required_count": len(capabilities),
        "covered_count": covered,
        "missing": missing,
        "extra": extra,
        "unmapped_files": unmapped,
        "not_built": not bool(mapping),
        "capabilities": [item["name"] for item in capabilities],
    }


def match_source_map(path: str, mapping: list[dict[str, Any]]) -> list[str]:
    exact = [item["name"] for item in mapping if item["path"] == path]
    if exact:
        seen: list[str] = []
        for name in exact:
            if name not in seen:
                seen.append(name)
        return seen
    best_len = -1
    best: list[str] = []
    for item in mapping:
        if not prefix_matches(path, item["path"]):
            continue
        length = len(item["path"].strip().rstrip("/"))
        if length > best_len:
            best_len = length
            best = [item["name"]]
        elif length == best_len and item["name"] not in best:
            best.append(item["name"])
    return best


def match_change(
    item: dict[str, str], mapping: list[dict[str, Any]]
) -> tuple[list[str], str]:
    status = item.get("status", "")
    path = item["path"]
    from_path = item.get("from")
    lookups = [from_path, path] if status == "R" and from_path else [path]
    for lookup in lookups:
        if lookup is None:
            continue
        names = match_source_map(lookup, mapping)
        if names:
            via = (
                "source-map"
                if any(row["path"] == lookup for row in mapping)
                else "source-prefix"
            )
            return names, via
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
    candidates = [
        item
        for item in files
        if not skip_inventory_path(source, item["path"], gitlinks=gitlinks)
    ]
    ignored = ignored_paths(
        source,
        [item["path"] for item in candidates],
    )
    files = [
        item
        for item in candidates
        if item["path"] not in ignored
        and text_path(source, item["path"], allow_missing=item.get("status") == "D")
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
    info = git_info(source, args.branch)
    branch = args.branch or (info.get("default_branch") if info.get("is_git") else None)
    if not args.confirm:
        confirm_args = ["init", "--confirm", "--cwd", str(cwd), "--mode", mode]
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
        },
        summary=f"init: created {spec_root}",
    )


def infer_phase(spec_root: Path, state: dict[str, Any]) -> str:
    layout = mirror_layout(spec_root)
    if layout == "legacy":
        return "rebuild"
    if layout == "none":
        return "init"
    if effective_build_status(state) == "built":
        return "update"
    return "build"


def inspect_symbols(
    source: Path, rel: str, *, include_private: bool = False
) -> dict[str, Any]:
    path = (source / rel).resolve()
    try:
        path.relative_to(source.resolve())
    except ValueError as exc:
        raise SpecError(f"file outside source: {rel}", reason="path_escape") from exc
    gitlinks = list_gitlinks(source)
    ignored = ignored_paths(source, [rel])
    if rel in ignored:
        return {"path": rel, "skipped": True, "reason": "ignored", "symbols": []}
    if skip_inventory_path(source, rel, gitlinks=gitlinks):
        return {"path": rel, "skipped": True, "reason": "third_party", "symbols": []}
    if not text_path(source, rel):
        return {"path": rel, "skipped": True, "reason": "non_text", "symbols": []}
    if not path.is_file():
        return {"path": rel, "missing": True, "symbols": []}
    return {
        "path": rel,
        "symbols": extract_symbols(path, include_private=include_private),
    }


def cmd_status(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    branch = args.branch or state.get("branch")
    info = git_info(source, branch)
    build_status = effective_build_status(state)
    layout = mirror_layout(spec_root)
    phase = infer_phase(spec_root, state)
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
        unmapped = unmapped_code_files(spec_root, source)
        gone = gone_map_paths(spec_root, source)
        freshness = {
            "kind": "non-git",
            "in_sync": build_status == "built" and not unmapped and not gone,
            "unmapped": unmapped,
            "gone": gone,
            "note": "no commit diff; compare inventory vs source-map",
        }
    payload = {
        "ok": True,
        "result": "status",
        "spec_root": str(spec_root),
        "state": state,
        "build_status": build_status,
        "layout": layout,
        "phase": phase,
        "source": str(source),
        "git": info,
        "freshness": freshness,
    }
    return emit(
        payload,
        summary=f"status: {state.get('project')} {layout} {phase}",
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


def collect_route(
    spec_root: Path,
    source: Path,
    state: dict[str, Any],
    *,
    branch: str | None = None,
    from_commit: str | None = None,
    to: str | None = None,
    path: str | None = None,
    apply_renames: bool = False,
) -> dict[str, Any]:
    diff_payload = collect_diff_files(
        source,
        state,
        branch=branch,
        from_commit=from_commit,
        to=to,
        path=path,
    )
    mapping = load_source_map(spec_root)
    not_built = not mapping
    unspecified = load_unspecified(spec_root)
    changes: list[dict[str, Any]] = []
    unmapped: list[str] = []
    renames: list[dict[str, Any]] = []
    hit_caps: list[str] = []
    for item in diff_payload["files"]:
        names, via = ([], "unmapped") if not_built else match_change(item, mapping)
        rec: dict[str, Any] = {
            "status": item.get("status", ""),
            "path": item["path"],
            "capabilities": names,
            "via": via,
        }
        if item.get("from"):
            rec["from"] = item["from"]
        changes.append(rec)
        if not names:
            if not path_accounted(item["path"], unspecified):
                unmapped.append(item["path"])
        else:
            for name in names:
                if name not in hit_caps:
                    hit_caps.append(name)
        if item.get("status") == "R" and item.get("from"):
            rename_rec: dict[str, Any] = {"from": item["from"], "to": item["path"]}
            if names:
                rename_rec["capability"] = names[0]
                if len(names) > 1:
                    rename_rec["capabilities"] = names
            renames.append(rename_rec)
    applied = apply_source_map_renames(spec_root, renames) if apply_renames else 0
    pages = [capability_spec_rel(name) for name in hit_caps]
    payload: dict[str, Any] = {
        "ok": True,
        "result": "route",
        "spec_root": str(spec_root),
        "from": diff_payload.get("from"),
        "to": diff_payload.get("to"),
        "full": diff_payload.get("full", False),
        "not_built": not_built,
        "capabilities": hit_caps,
        "pages": pages,
        "renames": renames,
        "renames_applied": applied,
        "unmapped": unmapped,
        "changes": changes,
    }
    if not_built:
        payload["note"] = "not_built"
    return payload


def cmd_route(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    state = load_state(spec_root)
    source = resolve_source(spec_root, state)
    payload = collect_route(
        spec_root,
        source,
        state,
        branch=args.branch,
        from_commit=args.from_commit,
        to=args.to,
        path=args.path,
        apply_renames=True,
    )
    unmapped = payload["unmapped"]
    summary = (
        f"route: not_built {len(unmapped)} unmapped"
        if payload.get("not_built")
        else f"route: {len(payload['capabilities'])} capabilities {len(unmapped)} unmapped"
    )
    return emit(payload, summary=summary)


REQUIRED_MIRROR_FILES = (
    "README.md",
    "changelog.md",
    "briefing/overview.md",
    "briefing/architecture.md",
    "briefing/concepts/INDEX.md",
    "briefing/flows/INDEX.md",
    "briefing/diagrams/INDEX.md",
    "agent/INDEX.md",
    "agent/model/INDEX.md",
    "agent/surface/INDEX.md",
    "agent/data/INDEX.md",
    "evidence/source-map.md",
)


def effective_build_status(state: dict[str, Any]) -> str:
    value = state.get("build_status")
    if value in {"skeleton", "built"}:
        return value
    return "built" if state.get("synced_commit") else "skeleton"


def render_readme_metadata(text: str, state: dict[str, Any]) -> str:
    mode = state.get("mode")
    branch = state.get("branch") or "（无）"
    commit = state.get("synced_commit")
    commit_text = f"`{commit[:12]}`" if commit else "尚未同步"
    replacements = {
        "粒度": str(mode),
        "分支": str(branch),
        "同步 commit": commit_text,
    }
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] not in replacements:
            continue
        key = cells[0]
        lines[index] = f"| {key} | {replacements[key]} |"
    return "\n".join(lines) + "\n"


def readme_metadata(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] in {"粒度", "分支", "同步 commit"}:
            result[cells[0]] = cells[1].strip("`")
    return result


def normalize_source_path(value: str, label: str) -> str:
    raw = str(value).strip().replace("\\", "/")
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        raise SpecError(f"invalid {label} path: {value!r}", reason="invalid_source_path")
    while raw.startswith("./"):
        raw = raw[2:]
    if not raw or ".." in Path(raw).parts:
        raise SpecError(f"invalid {label} path: {value!r}", reason="invalid_source_path")
    return raw


def normalize_source_paths(values: list[str], label: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        rel = normalize_source_path(value, label)
        if rel not in normalized:
            normalized.append(rel)
    return normalized


def validation_issues(
    spec_root: Path,
    state: dict[str, Any],
    *,
    readme_text: str | None = None,
) -> list[str]:
    missing = [rel for rel in REQUIRED_MIRROR_FILES if not (spec_root / rel).is_file()]
    issues = ["missing: " + ", ".join(missing)] if missing else []
    for key in ("version", "project", "placement", "source", "mode"):
        if key not in state:
            issues.append(f"state missing {key}")
    mode = state.get("mode")
    if mode not in MODES:
        issues.append(f"invalid mode {mode!r}")
    explicit_build_status = state.get("build_status")
    if explicit_build_status is not None and explicit_build_status not in {"skeleton", "built"}:
        issues.append(f"invalid build_status {explicit_build_status!r}")
    if (
        mode == "reconstructable"
        and effective_build_status(state) == "built"
    ):
        for item in load_capabilities(spec_root):
            spec_file = spec_root / "agent" / "specs" / item["name"] / "spec.md"
            if not spec_file.is_file():
                issues.append(f"missing spec for {item['name']}")
                continue
            text = spec_file.read_text(encoding="utf-8")
            if not REQUIREMENT_RE.search(text):
                issues.append(f"{item['name']} spec missing Requirement")
            if not SCENARIO_RE.search(text):
                issues.append(f"{item['name']} spec missing Scenario")
    if readme_text is None and (spec_root / "README.md").is_file():
        readme_text = (spec_root / "README.md").read_text(encoding="utf-8")
    if readme_text is not None:
        metadata = readme_metadata(readme_text)
        expected = {
            "粒度": str(mode),
            "分支": str(state.get("branch") or "（无）"),
            "同步 commit": str(state.get("synced_commit") or "尚未同步")[:12],
        }
        for key, value in expected.items():
            if key in metadata and metadata[key] != value:
                issues.append(f"README {key} mismatch: {metadata[key]!r} != {value!r}")
    return issues


def sync_state(
    spec_root: Path,
    *,
    commit: str | None = None,
    mode: str | None = None,
    branch: str | None = None,
) -> dict[str, Any]:
    """回写 built / commit。写盘前校验骨架，失败则抛错不推进。"""
    current = load_state(spec_root)
    source = resolve_source(spec_root, current)
    state = dict(current)
    if mode:
        state["mode"] = mode
    if branch:
        state["branch"] = branch
    state.pop("scope", None)
    state.pop("detail_level", None)
    state.pop("important_paths", None)
    state.pop("hotspots", None)
    info = git_info(source, state.get("branch"))
    if info.get("is_git"):
        if commit is None:
            raise SpecError(
                "Git source requires --commit",
                reason="commit_required",
            )
        if commit == "":
            raise SpecError(
                "Git source requires --commit",
                reason="commit_required",
            )
        state["synced_commit"] = commit_of(source, commit)
        state["synced_at"] = utc_now()
    else:
        if commit not in {None, ""}:
            raise SpecError(
                "non-Git source cannot record a commit",
                reason="commit_not_supported",
            )
        state["synced_commit"] = None
        state["synced_at"] = None
    state["build_status"] = "built"
    state["built_at"] = utc_now()
    state["updated_at"] = utc_now()
    readme_path = spec_root / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    rendered_readme = render_readme_metadata(readme, state)
    issues = validation_issues(spec_root, state, readme_text=rendered_readme)
    if issues:
        raise SpecError(
            "mirror validation failed before finalize",
            reason="invalid_mirror",
            issues=issues,
        )
    write_text(readme_path, rendered_readme)
    write_state(spec_root, state)
    return state


def cmd_finalize(args: argparse.Namespace) -> int:
    """唯一能标 built 的对外命令：layout → unmapped → coverage → leak → 回写。"""
    cwd = Path(args.cwd).expanduser().resolve()
    spec_root = find_spec_root(
        cwd, Path(args.spec).expanduser() if args.spec else None, args.project
    )
    if mirror_layout(spec_root) == "legacy":
        return emit(
            {
                "ok": False,
                "result": "finalize",
                "stage": "layout",
                "reason": "legacy_layout",
                "layout": "legacy",
                "spec_root": str(spec_root),
            },
            code=1,
            summary="finalize: legacy layout; rebuild current tree first",
        )
    probe = dict(load_state(spec_root))
    if args.mode:
        probe["mode"] = args.mode
    source = resolve_source(spec_root, probe)
    if probe.get("synced_commit"):
        routed = collect_route(
            spec_root,
            source,
            probe,
            branch=args.branch or probe.get("branch"),
            apply_renames=True,
        )
        if routed["unmapped"]:
            return emit(
                {
                    "ok": False,
                    "result": "finalize",
                    "stage": "route",
                    "reason": "unmapped_pending",
                    "spec_root": str(spec_root),
                    "unmapped": routed["unmapped"],
                },
                code=1,
                summary=f"finalize: unmapped={len(routed['unmapped'])}",
            )
    coverage = collect_coverage(spec_root, source, probe)
    if not coverage["ok"]:
        return emit(
            {
                "ok": False,
                "result": "finalize",
                "stage": "coverage",
                "reason": "coverage_missing",
                "spec_root": str(spec_root),
                "coverage": coverage,
            },
            code=1,
            summary=f"finalize: coverage missing={len(coverage['missing'])}",
        )
    leaks = briefing_leaks(spec_root)
    if leaks:
        return emit(
            {
                "ok": False,
                "result": "finalize",
                "stage": "leak",
                "reason": "briefing_leak",
                "spec_root": str(spec_root),
                "leaks": leaks,
            },
            code=1,
            summary=f"finalize: briefing leak={len(leaks)}",
        )
    state = sync_state(
        spec_root,
        commit=args.commit,
        mode=args.mode,
        branch=args.branch,
    )
    issues = validation_issues(spec_root, state)
    ok = not issues
    return emit(
        {
            "ok": ok,
            "result": "finalize",
            "stage": "done" if ok else "validate",
            "spec_root": str(spec_root),
            "coverage": {
                "enforce": coverage["enforce"],
                "required_count": coverage["required_count"],
                "covered_count": coverage["covered_count"],
                "extra": coverage["extra"],
                "unmapped_files": coverage["unmapped_files"],
            },
            "issues": issues,
            "state": state,
        },
        code=0 if ok else 1,
        summary=(
            f"finalize: {state.get('synced_commit') or 'none'}"
            if ok
            else "finalize: validate issues"
        ),
    )


COMMANDS = {
    "detect": cmd_detect,
    "init": cmd_init,
    "status": cmd_status,
    "diff": cmd_diff,
    "route": cmd_route,
    "finalize": cmd_finalize,
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
        choices=MODES,
        default="briefing",
    )

    add("status", help="阶段、layout、git 新鲜度")

    diff = add("diff", help="相对已同步 commit 的文件变更")
    diff.add_argument("--from", dest="from_commit", default=None)
    diff.add_argument("--to", dest="to", default=None)
    diff.add_argument("--path", default=None)

    route = add("route", help="把 diff 文件映射到能力 spec；rename 回写 source-map")
    route.add_argument("--from", dest="from_commit", default=None)
    route.add_argument("--to", dest="to", default=None)
    route.add_argument("--path", default=None)

    finalize = add("finalize", help="唯一收尾：门禁后回写 built / commit")
    finalize.add_argument("--commit", default=None)
    finalize.add_argument("--mode", choices=MODES, default=None)
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
